#!/usr/bin/env python3
"""Run the vLLM serving-throughput probe (experiment serving-throughput-probe-v1).

Subcommands:

* ``plan``: resolve the contract for one job and print it (CPU only, no vLLM).
* ``run``: execute one job inside the vLLM overlay image under the docker
  research lane: gates G0.0-G0.8, engine lifecycle, the job's points in their
  preregistered priority order, stop rules, and atomic per-point JSON.
* ``cuda-doctor``: internal child process for gates G0.2-G0.4.
* ``project``: apply the preregistered budget rules to finished job outputs.

The workload is PID 1 in its container: it installs its own USR1/TERM handlers
and reaps orphaned children. ``COTCODEC_CHECKPOINT_MARKER`` is the lane's
signal-checkpoint marker: it is written only after a USR1 or TERM, only after
the progress it describes is on disk, and it carries the lane's
``trigger=SIG<name>`` line; a run that receives no signal never writes it.
Generated text is never executed or stored.
Exit codes: 0 finished, 1 crash, 2 pre-result (a gate failed), 3 interrupted.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import hashlib
import json
import math
import os
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import httpx  # noqa: E402
import numpy as np  # noqa: E402

from harness.serving_probe import budget as budget_rules  # noqa: E402
from harness.serving_probe.client import (  # noqa: E402
    ChatRequest,
    EpisodePlan,
    RequestResult,
    StopToken,
    aa_agreement,
    run_aa,
    run_open_loop,
    run_replay,
    summarize_replay,
    summarize_requests,
)
from harness.serving_probe.config import (  # noqa: E402
    EngineSpec,
    JobSpec,
    PhaseSpec,
    PointSpec,
    ProbeConfig,
    ProbeConfigError,
    bind_seeds,
    check_pins,
    load_config,
    parse_weight_pins,
)
from harness.serving_probe.images import data_url, make_image  # noqa: E402
from harness.serving_probe.metrics import (  # noqa: E402
    GpuSample,
    GpuSampler,
    baseline_verdict,
    check_counters,
    cpu_percent,
    metrics_from_offline,
    orphan_zombies,
    parse_engine_log,
    parse_prometheus,
    point_counter_deltas,
    process_tree,
    read_cpu_ticks,
    summarize_gpu,
    tmp_mapped_files,
)
from harness.serving_probe.prompts import (  # noqa: E402
    allowed_token_ids,
    h1_messages,
    h2_messages,
    image_seed,
    open_loop_messages,
    random_text,
    random_token_ids,
    text_rng,
)

DEFAULT_CONFIG = PROJECT_ROOT / "experiments" / "serving" / "serving-throughput-probe-v1.yaml"
EXIT_OK, EXIT_CRASH, EXIT_PRE_RESULT, EXIT_INTERRUPTED = 0, 1, 2, 3
TERMINAL_STATUSES = {"valid", "valid-flagged", "invalid", "truncated"}
RERUNNABLE_STATUSES = {"interrupted", "failed-infra", "not-run"}
ACCEPTED_JOB_STATUSES = {"complete", "complete-with-cuts"}
MEMORY_RELEASED_MIB = 1024.0
#: Gates recorded once per phase (the others are recorded once per job).
PHASE_GATES = ("G0.5", "G0.6", "G0.7", "G0.8")
#: Job-level gates an accepted job must have recorded as passed.
JOB_GATES = ("G0.0", "G0.1", "G0.2", "G0.3", "G0.4")
#: G0.2 demands exactly one visible H100, whatever GPU count the lane's environment
#: carries (the probe is TP=1 everywhere; preregistration section 4).
EXPECTED_GPUS = 1
#: The code whose digest the preregistration names: every module of the probe
#: package and this driver. Any change to them after freezing is a new experiment.
PROBE_CODE_GLOBS = ("harness/serving_probe/*.py", "scripts/run_vllm_throughput_probe.py")

#: Every JIT, compile and scratch location is redirected under <output>/cache, because
#: the lane's /tmp tmpfs is noexec in the default container profile.
CACHE_DIRS = {
    "HOME": "home",
    "XDG_CACHE_HOME": "xdg-cache",
    "XDG_CONFIG_HOME": "xdg-config",
    "VLLM_CACHE_ROOT": "vllm",
    "VLLM_CONFIG_ROOT": "vllm-config",
    "VLLM_RPC_BASE_PATH": "rpc",
    "TRITON_CACHE_DIR": "triton",
    "TRITON_HOME": "triton-home",
    "TORCHINDUCTOR_CACHE_DIR": "inductor",
    "TORCH_HOME": "torch",
    "CUDA_CACHE_PATH": "cuda",
    "FLASHINFER_WORKSPACE_BASE": "flashinfer",
    "VLLM_FLASHINFER_AUTOTUNE_CACHE_DIR": "flashinfer-autotune",
    "DG_JIT_CACHE_DIR": "deepgemm",
    "HF_HOME": "hf",
    "MPLCONFIGDIR": "matplotlib",
    "TMPDIR": "tmp",
}
FIXED_ENV = {
    "VLLM_NO_USAGE_STATS": "1",
    "DO_NOT_TRACK": "1",
    "VLLM_DO_NOT_TRACK": "1",
    "VLLM_HOST_IP": "127.0.0.1",
    "VLLM_SERVER_DEV_MODE": "1",
    "HF_HUB_OFFLINE": "1",
    "TRANSFORMERS_OFFLINE": "1",
    "PYTHONUNBUFFERED": "1",
    "VLLM_LOGGING_LEVEL": "INFO",
}


class GateFailure(RuntimeError):
    """A step-0 gate failed; the job outcome is a pre-result."""


class ProbeInterrupted(BaseException):
    """Raised inside a blocking offline call when USR1/TERM arrives."""


class ProbeDeadline(BaseException):
    """Raised inside a blocking offline call when the point deadline passes."""


def utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write_text(path: Path, text: str) -> None:
    """Write ``text`` to a temporary file beside ``path``, fsync it, then rename it over."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def atomic_write_json(path: Path, payload: Any) -> None:
    atomic_write_text(path, json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n")


def probe_code_digest(root: Path = PROJECT_ROOT) -> dict[str, Any]:
    """SHA-256 over the sorted (path, SHA-256) list of the probe's code files."""
    files = sorted(
        {path for pattern in PROBE_CODE_GLOBS for path in root.glob(pattern) if path.is_file()}
    )
    if not files:
        raise ProbeConfigError(f"no probe code files under {root}")
    listing = [[path.relative_to(root).as_posix(), sha256_file(path)] for path in files]
    digest = hashlib.sha256(json.dumps(listing, separators=(",", ":")).encode("utf-8")).hexdigest()
    return {"digest": digest, "files": dict(listing)}


def git_revision(root: Path = PROJECT_ROOT) -> dict[str, Any]:
    """HEAD and whether the probe code or contract differ from it (None outside git)."""

    def git(*args: str) -> str | None:
        try:
            completed = subprocess.run(
                ["git", "-C", str(root), *args],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        return completed.stdout.strip()

    head = git("rev-parse", "HEAD")
    status = git("status", "--porcelain", "--", *PROBE_CODE_GLOBS, "experiments/serving")
    return {"head": head, "probe_files_modified": None if status is None else bool(status)}


def cache_environment(output_dir: Path, variant_env: Mapping[str, str]) -> dict[str, str]:
    cache = output_dir / "cache"
    env = {key: str(cache / sub) for key, sub in CACHE_DIRS.items()}
    env.update(FIXED_ENV)
    env.update(variant_env)
    return env


def allocation_start_perf(job_env: Path, *, now_wall: float, now_perf: float) -> tuple[float, str]:
    """Anchor the allocation clock at the lane's ``started_at`` (written before the container)."""
    try:
        for line in job_env.read_text(encoding="utf-8").splitlines():
            key, _, value = line.partition("=")
            if key == "started_at":
                started = datetime.strptime(value.strip(), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
                lag = max(0.0, now_wall - started.timestamp())
                return now_perf - lag, "job.env started_at"
    except (OSError, ValueError):
        pass
    return now_perf, "driver start (job.env unavailable)"


class Deadlines:
    """Soft (no new point), phase (reserve for later phases) and hard (truncate) deadlines."""

    def __init__(
        self,
        *,
        start: float,
        allocation_minutes: float,
        soft_fraction: float,
        hard_margin_minutes: float,
        reserves_after: Sequence[float],
    ) -> None:
        self.start = start
        self.soft = start + soft_fraction * allocation_minutes * 60.0
        self.hard = start + (allocation_minutes - hard_margin_minutes) * 60.0
        self.reserves_after = list(reserves_after)

    def phase_launch_deadline(self, index: int) -> float:
        return self.soft - 60.0 * self.reserves_after[index]

    def phase_hard_deadline(self, index: int) -> float:
        if self.reserves_after[index] > 0:
            return self.phase_launch_deadline(index)
        return self.hard

    def describe(self) -> dict[str, Any]:
        return {
            "soft_after_start_s": self.soft - self.start,
            "hard_after_start_s": self.hard - self.start,
            "phase_reserves_after_minutes": self.reserves_after,
        }


# ---------------------------------------------------------------------------
# Engines
# ---------------------------------------------------------------------------


class ServerEngine:
    """``vllm serve`` in its own session; the driver is its only client."""

    mode = "server"

    def __init__(
        self,
        spec: EngineSpec,
        model_dir: str,
        config: ProbeConfig,
        env: Mapping[str, str],
        log_path: Path,
    ) -> None:
        server = config.section("server")
        self.spec = spec
        self.model_dir = model_dir
        self.host = str(server["host"])
        self.port = int(server["port"])
        self.served_name = str(server["served_model_name"])
        self.env = {**os.environ, **env}
        self.log_path = log_path
        self.base_url = f"http://{self.host}:{self.port}"
        self.process: subprocess.Popen[bytes] | None = None
        self._log_handle: Any = None

    def argv(self, eager: bool) -> list[str]:
        argv = self.spec.server_argv(
            self.model_dir, host=self.host, port=self.port, served_name=self.served_name
        )
        return [*argv, "--enforce-eager"] if eager else argv

    @property
    def pid(self) -> int | None:
        return None if self.process is None else self.process.pid

    def start(self, eager: bool) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._log_handle = self.log_path.open("ab")
        self.process = subprocess.Popen(
            self.argv(eager),
            stdout=self._log_handle,
            stderr=subprocess.STDOUT,
            env=self.env,
            start_new_session=True,
            cwd=self.env.get("TMPDIR"),
        )

    def alive(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def wait_ready(self, timeout_s: float, should_stop: Callable[[], bool] | None = None) -> bool:
        end = time.perf_counter() + timeout_s
        with httpx.Client(base_url=self.base_url, timeout=5.0, trust_env=False) as client:
            while time.perf_counter() < end:
                if not self.alive() or (should_stop is not None and should_stop()):
                    return False
                with contextlib.suppress(httpx.HTTPError):
                    if client.get("/health").status_code == 200:
                        return True
                time.sleep(2.0)
        return False

    def metrics(self) -> dict[str, float]:
        with httpx.Client(base_url=self.base_url, timeout=30.0, trust_env=False) as client:
            response = client.get("/metrics")
            response.raise_for_status()
            return parse_prometheus(response.text)

    def reset_caches(self) -> dict[str, Any]:
        outcome: dict[str, Any] = {"prefix": False, "attempts": 0}
        with httpx.Client(base_url=self.base_url, timeout=30.0, trust_env=False) as client:
            for attempt in range(1, 31):
                outcome["attempts"] = attempt
                response = client.post("/reset_prefix_cache")
                if response.status_code == 200 and response.json().get("success") is True:
                    outcome["prefix"] = True
                    break
                time.sleep(1.0)
            outcome["mm"] = client.post("/reset_mm_cache").status_code == 200
            outcome["encoder"] = client.post("/reset_encoder_cache").status_code == 200
        return outcome

    def async_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.base_url,
            timeout=None,
            trust_env=False,
            limits=httpx.Limits(max_connections=512, max_keepalive_connections=512),
        )

    def log_text(self) -> str:
        try:
            return self.log_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""

    def tmp_maps(self) -> dict[str, list[str]]:
        if self.pid is None:
            return {}
        maps = {str(pid): tmp_mapped_files(pid) for pid in process_tree(self.pid)}
        return {pid: paths for pid, paths in maps.items() if paths}

    def stop(self, timeout_s: float = 30.0) -> dict[str, Any]:
        outcome: dict[str, Any] = {"returncode": None, "killed": False}
        if self.process is not None:
            if self.process.poll() is None:
                with contextlib.suppress(ProcessLookupError):
                    os.killpg(self.process.pid, signal.SIGTERM)
                try:
                    self.process.wait(timeout=timeout_s)
                except subprocess.TimeoutExpired:
                    with contextlib.suppress(ProcessLookupError):
                        os.killpg(self.process.pid, signal.SIGKILL)
                    self.process.wait(timeout=30)
                    outcome["killed"] = True
            outcome["returncode"] = self.process.returncode
        if self._log_handle is not None:
            self._log_handle.close()
        return outcome


class OfflineEngine:
    """In-process ``vllm.LLM``; stdout/stderr (and the EngineCore child) go to the engine log."""

    mode = "offline"
    served_name = "offline"

    def __init__(
        self,
        spec: EngineSpec,
        model_dir: str,
        config: ProbeConfig,
        env: Mapping[str, str],
        log_path: Path,
    ) -> None:
        self.spec = spec
        self.model_dir = model_dir
        self.env = dict(env)
        self.log_path = log_path
        self.llm: Any = None
        self._saved_fds: tuple[int, int] | None = None
        #: External request ids of the generate() call in progress (vLLM numbers them
        #: from LLM.request_counter), so an interrupted call can be aborted.
        self._call_ids: list[str] = []
        #: Set when requests could not be cleared after an interrupted call; the
        #: engine then reports itself dead and the phase stops.
        self.poisoned = False

    @property
    def pid(self) -> int:
        return os.getpid()

    def _redirect(self) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        log_fd = os.open(self.log_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o640)
        self._saved_fds = (os.dup(1), os.dup(2))
        sys.stdout.flush()
        sys.stderr.flush()
        os.dup2(log_fd, 1)
        os.dup2(log_fd, 2)
        os.close(log_fd)

    def _restore(self) -> None:
        if self._saved_fds is not None:
            sys.stdout.flush()
            sys.stderr.flush()
            os.dup2(self._saved_fds[0], 1)
            os.dup2(self._saved_fds[1], 2)
            os.close(self._saved_fds[0])
            os.close(self._saved_fds[1])
            self._saved_fds = None

    def start(self, eager: bool) -> None:
        os.environ.update(self.env)
        self._redirect()
        from vllm import LLM

        kwargs = self.spec.offline_kwargs()
        kwargs["enforce_eager"] = eager
        self.llm = LLM(model=self.model_dir, tokenizer=self.model_dir, **kwargs)

    def alive(self) -> bool:
        return self.llm is not None and not self.poisoned

    def wait_ready(self, timeout_s: float, should_stop: Callable[[], bool] | None = None) -> bool:
        return self.llm is not None

    def tokenizer(self) -> Any:
        return self.llm.get_tokenizer()

    def metrics(self) -> dict[str, float]:
        return metrics_from_offline(self.llm.get_metrics())

    def reset_caches(self) -> dict[str, Any]:
        return {"prefix": bool(self.llm.reset_prefix_cache())}

    def generate(
        self,
        prompt_ids: Sequence[Sequence[int]],
        *,
        n: int,
        temperature: float,
        top_p: float,
        max_tokens: int,
    ) -> list[list[int]]:
        from vllm import SamplingParams
        from vllm.inputs import TokensPrompt

        prompts = [TokensPrompt(prompt_token_ids=list(ids)) for ids in prompt_ids]
        params = SamplingParams(
            n=n,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            min_tokens=max_tokens,
            ignore_eos=True,
        )
        first = int(self.llm.request_counter.counter)
        self._call_ids = [str(first + index) for index in range(len(prompts))]
        outputs = self.llm.generate(prompts, params, use_tqdm=False)
        own = set(self._call_ids)
        self._call_ids = []
        # LLM._run_engine drains every unfinished request, so keep only this call's.
        return [
            [len(choice.token_ids) for choice in output.outputs]
            for output in outputs
            if output.request_id in own
        ]

    def abort_unfinished(self) -> dict[str, Any]:
        """Abort the interrupted call's requests; poison the engine if any remain.

        ``LLM.generate`` leaves requests in the engine when an exception (here a
        deadline or a signal) leaves its loop, and the next call would finish them
        and return their outputs with its own.
        """
        engine = self.llm.llm_engine
        ids, self._call_ids = list(self._call_ids), []
        if ids:
            engine.abort_request(ids, internal=False)
        remaining = bool(engine.has_unfinished_requests())
        self.poisoned = remaining
        return {"aborted_request_ids": len(ids), "unfinished_after_abort": remaining}

    def log_text(self) -> str:
        try:
            return self.log_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""

    def tmp_maps(self) -> dict[str, list[str]]:
        maps = {str(pid): tmp_mapped_files(pid) for pid in process_tree(os.getpid())}
        return {pid: paths for pid, paths in maps.items() if paths}

    def stop(self, timeout_s: float = 30.0) -> dict[str, Any]:
        outcome: dict[str, Any] = {"returncode": 0}
        if self.llm is not None:
            with contextlib.suppress(Exception):
                self.llm.llm_engine.engine_core.shutdown()
            self.llm = None
        import gc

        gc.collect()
        self._restore()
        return outcome


# ---------------------------------------------------------------------------
# Request builders
# ---------------------------------------------------------------------------


def _images(
    kind: str, width: int, height: int, seeds: Sequence[tuple[int, ...]], pool: ThreadPoolExecutor
) -> list[str]:
    return [
        data_url(blob) for blob in pool.map(lambda s: make_image(kind, width, height, s), seeds)
    ]


def build_open_loop_requests(
    point: PointSpec,
    tokenizer: Any,
    allowed: np.ndarray,
    size: tuple[int, int],
    pool: ThreadPoolExecutor,
    collect_token_ids: bool = False,
) -> list[ChatRequest]:
    """Shared prefix per point; per-request body and images; text never depends on images."""
    width, height = size
    prefix = random_text(tokenizer, allowed, text_rng(point.seed), int(point["prefix_tokens"]))
    count, images = int(point["requests"]), int(point["images"])
    seeds = [image_seed(point.seed, index, k) for index in range(count) for k in range(images)]
    all_urls = _images(str(point["image_kind"]), width, height, seeds, pool)
    requests = []
    for index in range(count):
        body = random_text(
            tokenizer, allowed, text_rng(point.seed, index), int(point["body_tokens"])
        )
        urls = all_urls[index * images : (index + 1) * images]
        requests.append(
            ChatRequest(
                messages=open_loop_messages(prefix, body, urls),
                max_tokens=int(point["output_tokens"]),
                thinking=bool(point["thinking"]),
                tag=(index,),
                collect_token_ids=collect_token_ids,
            )
        )
    return requests


def build_smoke_requests(
    point: PointSpec,
    tokenizer: Any,
    allowed: np.ndarray,
    size: tuple[int, int],
    pool: ThreadPoolExecutor,
) -> list[ChatRequest]:
    """Request 0 has no image and request 1 the same text with one image (G0.6 differential)."""
    requests = build_open_loop_requests(point, tokenizer, allowed, size, pool)
    if len(requests) < 2:
        raise ProbeConfigError("the smoke needs at least two requests")
    with_image = requests[1]
    text_only = [message for message in with_image.messages]
    user = dict(text_only[-1])
    user["content"] = [part for part in user["content"] if part.get("type") == "text"]
    text_only[-1] = user
    requests[0] = ChatRequest(text_only, with_image.max_tokens, with_image.thinking, (0,))
    return requests


def build_replay_plans(
    point: PointSpec,
    tokenizer: Any,
    allowed: np.ndarray,
    size: tuple[int, int],
    pool: ThreadPoolExecutor,
) -> list[EpisodePlan]:
    width, height = size
    params = point.params
    episodes = int(params["episodes"])
    depth = int(params["start_depth"])
    total = depth + int(params["steps"])
    measured = list(range(depth + 1, total + 1))
    system = random_text(tokenizer, allowed, text_rng(point.seed), int(params["system_tokens"]))
    all_screens = _images(
        "png-rendered",
        width,
        height,
        [image_seed(point.seed, e, step) for e in range(episodes) for step in range(1, total + 1)],
        pool,
    )
    plans: list[EpisodePlan] = []
    for episode in range(episodes):
        task = random_text(
            tokenizer, allowed, text_rng(point.seed, episode, 0), int(params["task_tokens"])
        )
        screens = all_screens[episode * total : (episode + 1) * total]
        actions = [
            random_text(
                tokenizer,
                allowed,
                text_rng(point.seed, episode, 1, step),
                int(params["action_tokens"]),
            )
            for step in range(1, total + 1)
        ]
        a11y = (
            {
                step: random_text(
                    tokenizer,
                    allowed,
                    text_rng(point.seed, episode, 2, step),
                    int(params["a11y_tokens"]),
                )
                for step in measured
            }
            if int(params["a11y_tokens"]) > 0
            else {}
        )
        prebuilt = [
            random_text(
                tokenizer,
                allowed,
                text_rng(point.seed, episode, 3, step),
                int(params["prebuilt_response_tokens"]),
            )
            for step in range(1, depth + 1)
        ]

        def build(
            step: int,
            responses: list[str],
            *,
            _screens=screens,
            _actions=actions,
            _a11y=a11y,
            _task=task,
        ) -> list[dict[str, Any]]:
            common = {
                "system": system,
                "task": _task,
                "screenshots": _screens[:step],
                "responses": responses[: step - 1],
                "actions": _actions[: step - 1],
                "history_n": int(params["history_n"]),
                "a11y": _a11y.get(step, ""),
            }
            if params["harness"] == "h1":
                return h1_messages(**common)
            return h2_messages(
                **common, image_max=int(params["image_max"]), fold_size=int(params["fold_size"])
            )

        plans.append(
            EpisodePlan(
                episode=episode,
                start_offset_s=float(params["stagger_s"]) * episode / episodes,
                steps=measured,
                prebuilt_responses=prebuilt,
                build=build,
                output_tokens=int(params["output_tokens"]),
                thinking=bool(params["thinking"]),
                t_env_s=float(params["t_env_s"]),
            )
        )
    return plans


def build_offline_prompts(point: PointSpec, allowed: np.ndarray) -> list[list[int]]:
    return [
        random_token_ids(allowed, text_rng(point.seed, index), int(point["input_tokens"]))
        for index in range(int(point["prompts"]))
    ]


# ---------------------------------------------------------------------------
# Assessment
# ---------------------------------------------------------------------------


def caches_reset(outcomes: Sequence[Mapping[str, Any]], *, server: bool) -> bool:
    """Every reset before (and, for the A/A point, between) a point's requests succeeded."""
    keys = ("prefix", "mm", "encoder") if server else ("prefix",)
    return bool(outcomes) and all(outcome.get(key) is True for outcome in outcomes for key in keys)


def min_gpu_samples(duration_s: float, interval_ms: float, fraction: float) -> int:
    """Samples a point needs: ``fraction`` of those its wall time implies, and at least one."""
    expected = max(0.0, duration_s) * 1000.0 / interval_ms
    return max(1, math.floor(fraction * expected))


def assess_point(
    result: Mapping[str, Any],
    *,
    counters: Mapping[str, Any],
    gpu: Mapping[str, Any],
    reservation_mib: float | None,
    reservation_required: bool,
    margin_mib: float,
    api_cpu_pct: float | None,
    client_cpu_pct: float | None,
    flag_pct: float,
    stop_reason: str | None,
    ran_to_end: bool,
    caches_ok: bool,
    min_samples: int,
) -> tuple[str, list[str], dict[str, bool]]:
    """Status of one attempt (section 7 of the preregistration).

    ``interrupted`` needs a signal and ``truncated`` a deadline (with no request
    error); a point that ends early for any other reason, such as a replay whose
    episode stopped at a failed request, goes through the validity checks and is
    ``invalid``. The device checks fail closed: no samples, or no reservation
    where one is required, is never a pass.
    """
    peak = gpu.get("peak_memory_used_mib")
    samples = int(gpu.get("samples") or 0)
    checks = {
        "no_failures": result["failed"] == 0,
        "all_completed": result["completed"] == result["planned"],
        "fixed_output_lengths": result.get("short_outputs", 0) == 0,
        "counters_match": bool(counters.get("pass")),
        "caches_reset": caches_ok,
        "gpu_sampled": samples >= min_samples and peak is not None,
    }
    if reservation_required:
        checks["no_contamination"] = (
            reservation_mib is not None
            and peak is not None
            and peak <= reservation_mib + margin_mib
        )
    flags = []
    if api_cpu_pct is not None and api_cpu_pct >= flag_pct:
        flags.append("front-end-bound")
    if client_cpu_pct is not None and client_cpu_pct >= flag_pct:
        flags.append("client-bound")
    if not ran_to_end and stop_reason == "signal":
        return "interrupted", flags, checks
    if not ran_to_end and stop_reason == "deadline" and int(result.get("request_errors", 0)) == 0:
        return "truncated", flags, checks
    if ran_to_end and all(checks.values()):
        return ("valid-flagged" if flags else "valid"), flags, checks
    return "invalid", flags, checks


def image_differential(
    results: Sequence[RequestResult], expected: int, tolerance: float
) -> dict[str, Any]:
    by_tag = {result.tag: result for result in results if result.ok}
    text_only, with_image = by_tag.get((0,)), by_tag.get((1,))
    if text_only is None or with_image is None:
        return {"pass": False, "reason": "differential pair did not complete"}
    delta = with_image.prompt_tokens - text_only.prompt_tokens
    return {
        "pass": abs(delta - expected) <= tolerance * expected,
        "image_tokens": delta,
        "expected": expected,
        "relative_tolerance": tolerance,
    }


# ---------------------------------------------------------------------------
# Lane and receipt checks (G0.0, G0.1)
# ---------------------------------------------------------------------------


def verify_preregistration(
    config: ProbeConfig, ledger: Path | None = None, root: Path = PROJECT_ROOT
) -> dict[str, Any]:
    """G0.0: the preregistration is frozen and names this contract and this probe code.

    The ledger freezes the preregistration's bytes; the preregistration names the
    contract's SHA-256 and the probe code digest. Requiring both here binds the
    frozen rules to the contract and the code that produce and read the data.
    """
    from scripts.preregister import DEFAULT_LEDGER, PreregistrationError, verify

    try:
        row = verify(config.experiment_id, ledger=ledger or DEFAULT_LEDGER, root=root)
    except PreregistrationError as exc:
        raise GateFailure(f"G0.0 preregistration is not frozen: {exc}") from exc
    if row.get("path") != config.preregistration:
        raise GateFailure("G0.0 the frozen preregistration path differs from the contract")
    text = (root / str(row["path"])).read_text(encoding="utf-8")
    if config.sha256 not in text:
        raise GateFailure(
            f"G0.0 the frozen preregistration does not name contract SHA-256 {config.sha256}"
        )
    code = probe_code_digest(root)
    if code["digest"] not in text:
        raise GateFailure(
            f"G0.0 the frozen preregistration does not name probe code digest {code['digest']}"
        )
    return {
        **dict(row),
        "contract_sha256": config.sha256,
        "probe_code_digest": code["digest"],
        "probe_code_files": code["files"],
    }


def check_lane_outputs(outputs_root: Path, config: ProbeConfig, job: JobSpec) -> dict[str, Any]:
    """G0.1: the lane's provenance, container doctor and bound-model verification passed."""
    report: dict[str, Any] = {}
    try:
        provenance = json.loads(
            (outputs_root / "provenance-verification.txt").read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise GateFailure(f"G0.1 provenance verification is unreadable: {exc}") from exc
    if provenance.get("status") != "PASS":
        raise GateFailure("G0.1 provenance verification did not pass")
    report["provenance"] = provenance
    try:
        doctor = (outputs_root / "container-doctor.txt").read_text(encoding="utf-8")
    except OSError as exc:
        raise GateFailure(f"G0.1 container doctor output is unreadable: {exc}") from exc
    if "STATUS PASS" not in doctor:
        raise GateFailure("G0.1 container doctor did not pass")
    try:
        verification = json.loads(
            (outputs_root / "model-verification.txt").read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise GateFailure(f"G0.1 model verification is unreadable: {exc}") from exc
    pinned = config.models[job.lane_model]
    expected = {
        "model_id": job.lane_model,
        "revision": pinned["revision"],
        "artifact_root_sha256": pinned["artifact_root_sha256"],
        "mode": "full",
    }
    for key, value in expected.items():
        if verification.get(key) != value:
            raise GateFailure(f"G0.1 lane-verified model field {key} is {verification.get(key)!r}")
    if os.environ.get("COTCODEC_MODEL_ID", job.lane_model) != job.lane_model:
        raise GateFailure("G0.1 the lane bound a different model than the contract names")
    report["lane_model"] = verification
    return report


def verify_metadata_pin(
    model_id: str, pin: tuple[str, str], config: ProbeConfig, model_root: Path, receipt_root: Path
) -> dict[str, Any]:
    """G0.1 for dummy-weight configs: the lane mounts but never verifies these snapshots."""
    from scripts.fetch_open_model import ModelRegistryError, load_registry, verify_receipt

    receipt_sha, root_sha = pin
    path = receipt_root / f"{model_id}.json"
    if not path.is_file() or path.is_symlink():
        raise GateFailure(f"G0.1 metadata receipt for {model_id} is missing")
    actual = sha256_file(path)
    if actual != receipt_sha:
        raise GateFailure(f"G0.1 metadata receipt digest for {model_id} is {actual}")
    receipt = json.loads(path.read_text(encoding="utf-8"))
    entry = config.models[model_id]
    if receipt.get("mode") != "metadata":
        raise GateFailure(f"G0.1 {model_id} receipt mode is {receipt.get('mode')!r}, not metadata")
    if receipt.get("revision") != entry["revision"] or receipt.get("repo_id") != entry["repo_id"]:
        raise GateFailure(f"G0.1 {model_id} receipt identity differs from the contract")
    if receipt.get("artifact_root_sha256") != root_sha:
        raise GateFailure(f"G0.1 {model_id} artifact root differs from the pin")
    registry = load_registry()
    if model_id not in registry["models"]:
        raise GateFailure(f"G0.1 {model_id} is not in the registry")
    try:
        verify_receipt(model_id, registry["models"][model_id], model_root, receipt_root)
    except ModelRegistryError as exc:
        raise GateFailure(f"G0.1 {model_id} snapshot does not match its receipt: {exc}") from exc
    return {
        "model_id": model_id,
        "receipt_sha256": actual,
        "artifact_root_sha256": root_sha,
        "total_bytes": receipt.get("total_bytes"),
        "files": len(receipt.get("files", [])),
    }


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


EngineFactory = Callable[[PhaseSpec, str, Path], Any]


class ProbeRunner:
    """Owns one job: gates, engine lifecycle, the point loop, stop rules and persistence."""

    def __init__(
        self,
        *,
        config: ProbeConfig,
        job: JobSpec,
        output_dir: Path,
        outputs_root: Path,
        model_root: Path,
        receipt_root: Path,
        pins: Mapping[str, tuple[str, str]],
        image_variant: str,
        seeds: Sequence[int],
        argv: Sequence[str],
        engine_factory: EngineFactory | None = None,
        sampler_factory: Callable[[Path], Any] | None = None,
        doctor: Callable[[Path, Mapping[str, str]], dict[str, Any]] | None = None,
        tokenizer_loader: Callable[[str], Any] | None = None,
        prereg_check: Callable[[ProbeConfig], dict[str, Any]] | None = None,
        marker_path: Path | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.config = config
        self.job = job
        self.output_dir = output_dir
        self.outputs_root = outputs_root
        self.model_root = model_root
        self.receipt_root = receipt_root
        self.pins = dict(pins)
        self.variant = image_variant
        self.seeds = list(seeds)
        self.argv = list(argv)
        variants = config.section("vllm")["image_variants"]
        if image_variant not in variants:
            raise ProbeConfigError(f"unknown image variant {image_variant!r}")
        self.env = cache_environment(output_dir, variants[image_variant]["env"])
        interval = int(config.section("sampling")["gpu_interval_ms"])
        self.engine_factory = engine_factory or self._default_engine
        self.sampler_factory = sampler_factory or (lambda path: GpuSampler(path, interval))
        self.doctor = doctor or self._default_doctor
        self.tokenizer_loader = tokenizer_loader or self._default_tokenizer
        self.prereg_check = prereg_check or verify_preregistration
        self.marker_path = marker_path
        self.sleep = sleep
        self.stop_event = threading.Event()
        self.signal_name: str | None = None
        self.blocking = False
        self.eager = False
        self.points_dir = output_dir / "points"
        self.summary: dict[str, Any] = {}
        self.point_status: dict[str, str] = {}
        self.sampler: Any = None
        self.deadlines: Deadlines | None = None
        self._console_fd: int | None = None
        self._reaper_stop = threading.Event()
        self._reaper_paused = threading.Event()
        self._tracked: set[int] = set()
        #: Every signal received, in order; the marker acknowledges each one once.
        self.signals_received: list[str] = []
        self._signals_acknowledged = 0

    # -- infrastructure -------------------------------------------------

    def log(self, message: str) -> None:
        line = f"[{utc_now()}] {message}\n"
        with (self.output_dir / "driver.log").open("a", encoding="utf-8") as handle:
            handle.write(line)
        if self._console_fd is not None:
            with contextlib.suppress(OSError):
                os.write(self._console_fd, line.encode())

    def _default_engine(self, phase: PhaseSpec, model_dir: str, log_path: Path) -> Any:
        engine_class = ServerEngine if phase.engine.mode == "server" else OfflineEngine
        return engine_class(phase.engine, model_dir, self.config, self.env, log_path)

    def _default_doctor(self, output: Path, env: Mapping[str, str]) -> dict[str, Any]:
        gates = self.config.section("gates")
        vllm = self.config.section("vllm")
        command = [
            sys.executable,
            str(Path(__file__).resolve()),
            "cuda-doctor",
            "--output",
            str(output),
            "--matmul-size",
            str(gates["matmul_size"]),
            "--max-error",
            str(gates["matmul_max_normalized_error"]),
            "--expected-gpus",
            str(EXPECTED_GPUS),
            "--expected-vllm-version",
            str(vllm["version"]),
            "--expected-vllm-commit",
            str(vllm["commit"]),
            "--cache-root",
            str(self.output_dir / "cache"),
        ]
        with (output.parent / "cuda-doctor.log").open("ab") as log:
            process = subprocess.Popen(
                command, env={**os.environ, **env}, stdout=log, stderr=subprocess.STDOUT
            )
            self._tracked.add(process.pid)
            end = time.perf_counter() + float(gates["doctor_timeout_s"])
            # Poll rather than block, so a USR1/TERM is checkpointed without waiting
            # for the doctor to finish.
            while process.poll() is None:
                if self.stop_event.is_set() or time.perf_counter() >= end:
                    process.kill()
                    process.wait()
                    if self.stop_event.is_set():
                        raise ProbeInterrupted(self.signal_name or "signal")
                    return {"pass": False, "error": "cuda doctor timed out"}
                time.sleep(0.5)
            returncode = process.returncode
        try:
            report = json.loads(output.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            report = {"pass": False, "error": "cuda doctor wrote no report"}
        report["returncode"] = returncode
        return report

    @staticmethod
    def _default_tokenizer(model_dir: str) -> Any:
        from transformers import AutoTokenizer

        return AutoTokenizer.from_pretrained(model_dir)

    def _install_signals(self) -> None:
        def handle(signum: int, _frame: Any) -> None:
            self.note_signal(signal.Signals(signum).name)
            if self.blocking:
                raise ProbeInterrupted(self.signal_name)

        def alarm(_signum: int, _frame: Any) -> None:
            if self.blocking:
                raise ProbeDeadline("point deadline")

        for name in ("SIGUSR1", "SIGTERM", "SIGINT"):
            signal.signal(getattr(signal, name), handle)
        signal.signal(signal.SIGALRM, alarm)

    def note_signal(self, name: str) -> None:
        """Record a stop signal (the handler's bookkeeping; no I/O)."""
        self.signal_name = name
        self.signals_received.append(name)
        self.stop_event.set()

    def _reap_once(self) -> None:
        for pid in orphan_zombies(os.getpid(), self._tracked):
            with contextlib.suppress(ChildProcessError, OSError):
                os.waitpid(pid, os.WNOHANG)

    def _reaper(self) -> None:
        while not self._reaper_stop.wait(2.0):
            if not self._reaper_paused.is_set():
                self._reap_once()

    def _write_progress(self, state: str) -> None:
        atomic_write_json(
            self.output_dir / "progress.json",
            {
                "state": state,
                "updated_at": utc_now(),
                "points": dict(self.point_status),
                "config_sha256": self.config.sha256,
                "job": self.job.job_id,
                "signal": self.signal_name,
            },
        )

    def _write_marker(self, triggers: Sequence[str]) -> None:
        """Write the lane's signal-checkpoint marker (docs/operations.md).

        Plain text, written atomically in the marker's directory. The first lines
        are ``trigger=SIG<name>``, one per signal this save answers (the lane reads
        the first 4,096 bytes); the rest describe the saved progress.
        """
        if self.marker_path is None:
            return
        progress = self.output_dir / "progress.json"
        lines = [f"trigger={name}" for name in dict.fromkeys(triggers)]
        lines += [
            f"written_at={utc_now()}",
            f"experiment_id={self.config.experiment_id}",
            f"job={self.job.job_id}",
            f"progress_sha256={sha256_file(progress) if progress.is_file() else 'none'}",
        ]
        lines += [f"point.{name}={status}" for name, status in sorted(self.point_status.items())]
        atomic_write_text(self.marker_path, "\n".join(lines) + "\n")

    def _checkpoint_after_signal(self, state: str = "signal-checkpoint") -> None:
        """After USR1/TERM: persist progress first, then (and only then) the marker.

        Runs at every checkpoint opportunity (after an interrupted point, when an
        engine stops, at exit); it writes nothing unless a signal arrived that no
        marker has acknowledged yet.
        """
        pending = self.signals_received[self._signals_acknowledged :]
        if not pending:
            return
        self._write_progress(state)
        self._write_marker(pending)
        self._signals_acknowledged += len(pending)
        self.log(f"signal {', '.join(pending)}: progress saved, checkpoint marker written")

    def _record(self, point: PointSpec, record: dict[str, Any]) -> None:
        atomic_write_json(self.points_dir / f"{point.point_id}.json", record)
        self.point_status[point.point_id] = record["status"]
        self._write_progress("running")

    # -- resume ---------------------------------------------------------

    def _load_existing(self) -> dict[str, dict[str, Any]]:
        existing: dict[str, dict[str, Any]] = {}
        if not self.points_dir.is_dir():
            return existing
        for path in sorted(self.points_dir.glob("*.json")):
            record = json.loads(path.read_text(encoding="utf-8"))
            if record.get("config_sha256") != self.config.sha256:
                raise GateFailure(f"resume refused: {path.name} was produced by another contract")
            if record.get("job") != self.job.job_id:
                raise GateFailure(f"resume refused: {path.name} belongs to job {record.get('job')}")
            existing[record["point_id"]] = record
        return existing

    # -- gates ----------------------------------------------------------

    def _baseline(self) -> dict[str, Any]:
        gates = self.config.section("gates")
        self.sleep(float(gates["baseline_settle_s"]))
        start = time.perf_counter()
        self.sleep(float(gates["baseline_duration_s"]))
        samples = self.sampler.window(start, time.perf_counter())
        return baseline_verdict(
            samples,
            max_memory_mib=float(gates["baseline_max_memory_used_mib"]),
            max_utilization_pct=float(gates["baseline_max_utilization_pct"]),
        )

    def _wait_memory_released(self) -> dict[str, Any]:
        timeout = float(self.config.section("gates")["gpu_release_timeout_s"])
        end = time.perf_counter() + timeout
        latest: GpuSample | None = None
        while time.perf_counter() < end and not self.stop_event.is_set():
            now = time.perf_counter()
            window = self.sampler.window(now - 2.0, now)
            if window:
                latest = window[-1]
                if latest.memory_used_mib < MEMORY_RELEASED_MIB:
                    return {"released": True, "memory_used_mib": latest.memory_used_mib}
            self.sleep(1.0)
        return {
            "released": False,
            "memory_used_mib": None if latest is None else latest.memory_used_mib,
        }

    # -- main -----------------------------------------------------------

    def run(self) -> int:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        for sub in ("points", "engines", "doctor", "samples"):
            (self.output_dir / sub).mkdir(exist_ok=True)
        for path in self.env.values():
            if path.startswith(str(self.output_dir)):
                Path(path).mkdir(parents=True, exist_ok=True)
        self._console_fd = os.dup(2)
        self._install_signals()
        if os.getpid() == 1:
            threading.Thread(target=self._reaper, name="reaper", daemon=True).start()
        self.summary = {
            "experiment_id": self.config.experiment_id,
            "job": self.job.job_id,
            "config_path": _display_path(self.config.path),
            "config_sha256": self.config.sha256,
            "argv": self.argv,
            "seeds": self.seeds,
            "image_variant": self.variant,
            "started_at": utc_now(),
            "gates": {},
            "phases": {},
            "eager": False,
        }
        atomic_write_json(
            self.output_dir / "plan.json",
            {
                **plan_payload(self.config, self.job, str(self.model_root)),
                "env": self.env,
                "argv": self.argv,
                "pins": self.pins,
            },
        )
        exit_code, status = EXIT_CRASH, "crashed"
        try:
            exit_code, status = self._run_job()
        except GateFailure as exc:
            self.log(f"pre-result: {exc}")
            self.summary["pre_result_reason"] = str(exc)
            exit_code, status = EXIT_PRE_RESULT, "pre-result"
        except ProbeInterrupted:
            exit_code, status = EXIT_INTERRUPTED, "interrupted"
        except Exception as exc:  # noqa: BLE001 - recorded in the summary, exit code 1
            self.log(f"crash: {type(exc).__name__}: {exc}")
            self.summary["crash"] = f"{type(exc).__name__}: {exc}"[:2000]
            exit_code, status = EXIT_CRASH, "crashed"
        finally:
            if self.stop_event.is_set() and status != "pre-result":
                exit_code, status = EXIT_INTERRUPTED, "interrupted"
            self._finalize(status, exit_code)
        return exit_code

    def _run_job(self) -> tuple[int, str]:
        self.summary["gates"]["G0.0"] = {"pass": True, "ledger_row": self.prereg_check(self.config)}
        existing = self._load_existing()
        for point_id, record in existing.items():
            self.point_status[point_id] = record["status"]
        self.summary["resumed_terminal_points"] = sorted(
            point for point, record in existing.items() if record["status"] in TERMINAL_STATUSES
        )
        lane = check_lane_outputs(self.outputs_root, self.config, self.job)
        check_pins(self.job, self.pins)
        lane["metadata_pins"] = [
            verify_metadata_pin(
                model, self.pins[model], self.config, self.model_root, self.receipt_root
            )
            for model in self.job.pinned_models()
        ]
        self.summary["gates"]["G0.1"] = {"pass": True, **lane}

        now_perf = time.perf_counter()
        start, anchor = allocation_start_perf(
            self.outputs_root / "job.env", now_wall=time.time(), now_perf=now_perf
        )
        stop = self.config.section("stop")
        reserves = [
            sum(phase.reserve_minutes for phase in self.job.phases[index + 1 :])
            for index in range(len(self.job.phases))
        ]
        self.deadlines = Deadlines(
            start=start,
            allocation_minutes=self.job.allocation_minutes,
            soft_fraction=float(stop["soft_fraction"]),
            hard_margin_minutes=float(stop["hard_margin_minutes"]),
            reserves_after=reserves,
        )
        self.summary["deadlines"] = {
            "anchor": anchor,
            "elapsed_at_driver_start_s": now_perf - start,
            **self.deadlines.describe(),
        }
        self._write_progress("gates")

        doctor_report = self.doctor(self.output_dir / "doctor" / "cuda-doctor.json", self.env)
        for gate in ("G0.2", "G0.3", "G0.4"):
            self.summary["gates"][gate] = doctor_report.get(gate, {"pass": False})
        if not doctor_report.get("pass"):
            raise GateFailure("G0.2-G0.4 CUDA doctor failed; see doctor/cuda-doctor.json")

        self.sampler = self.sampler_factory(self.output_dir / "samples" / "nvidia-smi.csv")
        self.sampler.start()
        process = getattr(self.sampler, "_process", None)
        if process is not None and getattr(process, "pid", None):
            self._tracked.add(int(process.pid))
        cut = False
        for index, phase in enumerate(self.job.phases):
            if self.stop_event.is_set():
                break
            outcome = self._run_phase(index, phase, existing)
            self.summary["phases"][phase.phase_id] = outcome
            cut = cut or bool(outcome.get("cut"))
            if self.stop_event.is_set():
                break
            gate = outcome.get("gate_failed")
            if gate and (phase.role == "primary" or len(self.job.phases) == 1):
                raise GateFailure(f"{gate} failed in phase {phase.phase_id}")
        return EXIT_OK, ("complete-with-cuts" if cut else "complete")

    def _start_engine(
        self, phase: PhaseSpec, engine_dir: Path, launch_deadline: float
    ) -> tuple[Any, list[dict[str, Any]], str | None]:
        """G0.5: default compile + CUDA-graph mode first, one eager fallback, then sticky eager.

        Each ready wait is capped by the gate timeout and by the phase launch deadline.
        Before the eager retry the device must release the failed engine's memory and
        pass G0.8 again. Returns the engine (or None), the attempts, and the gate that
        stopped the start ("G0.8" when the retry's baseline failed, else None).
        """
        model_dir = str(self.model_root / phase.engine.model)
        gate_timeout = float(self.config.section("gates")["engine_ready_timeout_s"])
        attempts: list[dict[str, Any]] = []
        for eager in [True] if self.eager else [False, True]:
            attempt: dict[str, Any] = {"eager": eager, "ready": False}
            if attempts:
                attempt["memory_release"] = self._wait_memory_released()
                if self.stop_event.is_set():
                    break
                baseline = self._baseline()
                attempt["G0.8"] = baseline
                self.summary["gates"].setdefault("G0.8", {})[f"{phase.phase_id}/eager-retry"] = (
                    baseline
                )
                if not baseline["pass"]:
                    attempt["error"] = "G0.8 device baseline failed before the eager retry"
                    attempts.append(attempt)
                    return None, attempts, "G0.8"
            timeout = min(gate_timeout, max(1.0, launch_deadline - time.perf_counter()))
            suffix = "-eager" if eager else ""
            engine = self.engine_factory(phase, model_dir, engine_dir / f"engine{suffix}.log")
            if engine.mode == "server":
                attempt["argv"] = engine.argv(eager)
            started = time.perf_counter()
            offline = engine.mode == "offline"
            if offline:
                self._reaper_paused.set()
            try:
                self.blocking = offline
                if offline:
                    signal.setitimer(signal.ITIMER_REAL, timeout)
                engine.start(eager)
                attempt["ready"] = bool(engine.wait_ready(timeout, self.stop_event.is_set))
                attempt["ready_timeout_s"] = timeout
            except ProbeDeadline:
                attempt["error"] = "engine start exceeded the ready timeout"
            except ProbeInterrupted:
                self._checkpoint_after_signal()
                engine.stop()
                raise
            except Exception as exc:  # noqa: BLE001 - a failed start is a G0.5 outcome
                attempt["error"] = f"{type(exc).__name__}: {exc}"[:500]
            finally:
                signal.setitimer(signal.ITIMER_REAL, 0)
                self.blocking = False
            attempt["seconds"] = time.perf_counter() - started
            pid = getattr(engine, "pid", None)
            if pid and engine.mode == "server":
                self._tracked.add(int(pid))
            attempts.append(attempt)
            if attempt["ready"]:
                return engine, attempts, None
            self._checkpoint_after_signal()
            engine.stop()
            self._reaper_paused.clear()
            if self.stop_event.is_set() or time.perf_counter() >= launch_deadline:
                break
        return None, attempts, None

    def _run_phase(
        self, index: int, phase: PhaseSpec, existing: Mapping[str, dict[str, Any]]
    ) -> dict[str, Any]:
        assert self.deadlines is not None
        outcome: dict[str, Any] = {"engine": phase.engine.engine_id, "role": phase.role}
        smoke_kinds = {"smoke-server", "smoke-offline"}
        pending = [
            point
            for point in phase.points
            if point.kind not in smoke_kinds
            and existing.get(point.point_id, {}).get("status") not in TERMINAL_STATUSES
        ]
        if not pending:
            outcome["skipped"] = "every point is already terminal (resume)"
            return outcome
        launch_deadline = self.deadlines.phase_launch_deadline(index)
        hard_deadline = self.deadlines.phase_hard_deadline(index)
        if time.perf_counter() >= launch_deadline:
            self._mark_not_run(phase.points, "stop rule: phase deadline passed before start")
            outcome.update({"cut": True, "skipped": "phase deadline passed before start"})
            return outcome

        if self.stop_event.is_set():
            return outcome
        baseline = self._baseline()
        outcome["G0.8"] = baseline
        self.summary["gates"].setdefault("G0.8", {})[phase.phase_id] = baseline
        if not baseline["pass"]:
            self._mark_not_run(phase.points, "G0.8 device baseline failed")
            outcome["gate_failed"] = "G0.8"
            return outcome

        if self.stop_event.is_set():
            return outcome
        engine_dir = self.output_dir / "engines" / phase.phase_id
        engine_dir.mkdir(parents=True, exist_ok=True)
        engine, attempts, stopped_by = self._start_engine(phase, engine_dir, launch_deadline)
        default_mode = engine is not None and not any(
            a.get("eager") for a in attempts if a["ready"]
        )
        verdict = {
            "pass": bool(default_mode),
            "eager_fallback": engine is not None and not default_mode,
            "attempts": attempts,
        }
        outcome["G0.5"] = verdict
        self.summary["gates"].setdefault("G0.5", {})[phase.phase_id] = verdict
        if engine is None:
            gate = stopped_by or "G0.5"
            self._mark_not_run(phase.points, f"{gate} failed while starting the engine")
            outcome["gate_failed"] = gate
            if not self.stop_event.is_set():
                outcome["memory_release"] = self._wait_memory_released()
            return outcome
        if not default_mode:
            self.eager = True
            self.summary["eager"] = True
        facts = parse_engine_log(engine.log_text())
        facts["tmp_mapped_files"] = engine.tmp_maps()
        outcome["engine_facts"] = facts
        try:
            outcome.update(
                self._run_points(phase, engine, existing, launch_deadline, hard_deadline)
            )
        finally:
            self._checkpoint_after_signal()
            outcome["engine_facts_final"] = parse_engine_log(engine.log_text())
            outcome["engine_stop"] = engine.stop()
            self._reaper_paused.clear()
            if not self.stop_event.is_set():
                outcome["memory_release"] = self._wait_memory_released()
        return outcome

    def _fail_gate(
        self, phase: PhaseSpec, gate: str, verdict: dict[str, Any], outcome: dict[str, Any]
    ) -> None:
        """Record a failed phase gate in the summary and the phase outcome."""
        self.summary["gates"].setdefault(gate, {})[phase.phase_id] = verdict
        outcome[gate] = verdict
        outcome["gate_failed"] = gate

    def _mark_not_run(self, points: Sequence[PointSpec], reason: str) -> None:
        for point in points:
            if self.point_status.get(point.point_id) in TERMINAL_STATUSES:
                continue
            record = self._base_record(point, attempt=0)
            record.update({"status": "not-run", "reason": reason})
            self._record(point, record)

    def _base_record(self, point: PointSpec, attempt: int) -> dict[str, Any]:
        return {
            "experiment_id": self.config.experiment_id,
            "config_sha256": self.config.sha256,
            "job": self.job.job_id,
            "point_id": point.point_id,
            "kind": point.kind,
            "seed": point.seed,
            "params": dict(point.params),
            "attempt": attempt,
            "eager": self.eager,
        }

    def _run_points(
        self,
        phase: PhaseSpec,
        engine: Any,
        existing: Mapping[str, dict[str, Any]],
        launch_deadline: float,
        hard_deadline: float,
    ) -> dict[str, Any]:
        outcome: dict[str, Any] = {"cut": False}
        validity = self.config.section("validity")
        screenshot = self.config.section("screenshot")
        size = (int(screenshot["width"]), int(screenshot["height"]))
        if engine.mode == "offline":
            tokenizer = engine.tokenizer()
        else:
            tokenizer = self.tokenizer_loader(engine.model_dir)
        allowed = allowed_token_ids(tokenizer)
        reservation: float | None = None
        reruns = int(validity["reruns_per_invalid_point"])
        with ThreadPoolExecutor(max_workers=8) as pool:
            for point in phase.points:
                smoke = point.kind in {"smoke-server", "smoke-offline"}
                if (
                    existing.get(point.point_id, {}).get("status") in TERMINAL_STATUSES
                    and not smoke
                ):
                    continue
                if self.stop_event.is_set():
                    break
                if time.perf_counter() >= launch_deadline:
                    left = [
                        p
                        for p in phase.points
                        if self.point_status.get(p.point_id) not in TERMINAL_STATUSES
                    ]
                    self._mark_not_run(left, "stop rule: launch deadline")
                    outcome["cut"] = True
                    break
                attempts: list[dict[str, Any]] = []
                superseded: list[dict[str, Any]] = []
                record: dict[str, Any] = {}
                for attempt in range(1, 2 + reruns):
                    if attempt > 1 and (
                        time.perf_counter() >= launch_deadline
                        or self.stop_event.is_set()
                        or not engine.alive()
                    ):
                        break
                    if record:
                        superseded.append(record)
                    deadline = min(time.perf_counter() + 60.0 * point.max_minutes, hard_deadline)
                    record = self._execute(
                        point,
                        attempt,
                        engine,
                        tokenizer,
                        allowed,
                        size,
                        pool,
                        deadline,
                        reservation,
                    )
                    attempts.append(
                        {key: record.get(key) for key in ("attempt", "status", "checks", "error")}
                    )
                    if record["status"] != "invalid":
                        break
                record["attempts"] = attempts
                # Earlier attempts are kept in full (metrics included); the last one stands.
                record["superseded_attempts"] = superseded
                self._record(point, record)
                self.log(f"{phase.phase_id}/{point.point_id}: {record['status']}")
                if record["status"] == "interrupted" or self.stop_event.is_set():
                    self._checkpoint_after_signal()
                    break
                if record["status"] == "failed-infra" or not engine.alive():
                    left = [
                        p
                        for p in phase.points
                        if self.point_status.get(p.point_id) not in TERMINAL_STATUSES
                        and p.point_id != point.point_id
                    ]
                    self._mark_not_run(left, "engine failed")
                    outcome["engine_failed"] = True
                    if smoke:
                        reason = f"smoke {record['status']}: {record.get('error')}"
                        self._fail_gate(phase, "G0.6", {"pass": False, "reason": reason}, outcome)
                    break
                if smoke:
                    gates = record.get("gates", {})
                    outcome.update(gates)
                    for gate, verdict in gates.items():
                        self.summary["gates"].setdefault(gate, {})[phase.phase_id] = verdict
                    if record["status"] not in {"valid", "valid-flagged"}:
                        failed = [g for g, v in gates.items() if not v.get("pass")]
                        if not failed:
                            # The gates' own checks held but the smoke point is not
                            # valid (cache resets, device samples): G0.6 fails.
                            bad = sorted(k for k, ok in record.get("checks", {}).items() if not ok)
                            verdict = {
                                **gates.get("G0.6", {}),
                                "pass": False,
                                "reason": f"smoke {record['status']}; failed checks {bad}",
                            }
                            self._fail_gate(phase, "G0.6", verdict, outcome)
                            failed = ["G0.6"]
                        outcome["gate_failed"] = failed[0]
                        rest = [p for p in phase.points if p is not point]
                        self._mark_not_run(rest, f"{outcome['gate_failed']} failed in the smoke")
                        break
                    window_s = float(validity["reservation_window_s"])
                    self.sleep(window_s)
                    now = time.perf_counter()
                    window = self.sampler.window(now - window_s, now)
                    reservation = max((s.memory_used_mib for s in window), default=None)
                    outcome["reservation_mib"] = reservation
                    outcome["reservation_samples"] = len(window)
                    if reservation is None:
                        # No device sample after the smoke: the contamination check
                        # could never hold, so the phase stops here (G0.8, sampling).
                        verdict = {
                            "pass": False,
                            "reason": "no device sample in the reservation window after the smoke",
                        }
                        self.summary["gates"].setdefault("G0.8", {})[
                            f"{phase.phase_id}/reservation"
                        ] = verdict
                        outcome["G0.8 reservation"] = verdict
                        outcome["gate_failed"] = "G0.8"
                        rest = [p for p in phase.points if p is not point]
                        self._mark_not_run(rest, "G0.8 no engine reservation was measured")
                        break
        return outcome

    def _execute(
        self,
        point: PointSpec,
        attempt: int,
        engine: Any,
        tokenizer: Any,
        allowed: np.ndarray,
        size: tuple[int, int],
        pool: ThreadPoolExecutor,
        deadline: float,
        reservation: float | None,
    ) -> dict[str, Any]:
        record = self._base_record(point, attempt)
        record["started_at"] = utc_now()
        try:
            if engine.mode == "server":
                body = self._server_point(point, engine, tokenizer, allowed, size, pool, deadline)
            else:
                body = self._offline_point(point, engine, allowed, deadline)
        except ProbeInterrupted:
            record.update({"status": "interrupted", "reason": self.signal_name})
            return record
        except (httpx.HTTPError, OSError, RuntimeError, ValueError, KeyError) as exc:
            record.update({"status": "failed-infra", "error": f"{type(exc).__name__}: {exc}"[:500]})
            return record
        record.update(body)
        validity = self.config.section("validity")
        smoke = point.kind in {"smoke-server", "smoke-offline"}
        resets = [body["cache_reset"], *body.get("cache_reset_between_arms", [])]
        status, flags, checks = assess_point(
            body["result"],
            counters=body["counter_check"],
            gpu=body["gpu"],
            reservation_mib=reservation,
            reservation_required=not smoke,
            margin_mib=float(validity["contamination_margin_mib"]),
            api_cpu_pct=body.get("api_server_cpu_pct"),
            client_cpu_pct=body.get("client_cpu_pct"),
            flag_pct=float(validity["frontend_cpu_flag_pct"]),
            stop_reason=body.get("stop_reason"),
            ran_to_end=body["ran_to_end"],
            caches_ok=caches_reset(resets, server=engine.mode == "server"),
            min_samples=min_gpu_samples(
                float(body["result"].get("duration_s") or 0.0),
                float(self.config.section("sampling")["gpu_interval_ms"]),
                float(validity["min_gpu_sample_fraction"]),
            ),
        )
        gates = body.get("gates")
        gates_failed = gates and not all(verdict.get("pass") for verdict in gates.values())
        if gates_failed and status in {"valid", "valid-flagged"}:
            status = "invalid"
        record.update(
            {"status": status, "flags": flags, "checks": checks, "finished_at": utc_now()}
        )
        return record

    # -- server points ----------------------------------------------------

    def _server_point(
        self,
        point: PointSpec,
        engine: Any,
        tokenizer: Any,
        allowed: np.ndarray,
        size: tuple[int, int],
        pool: ThreadPoolExecutor,
        deadline: float,
    ) -> dict[str, Any]:
        timeout_s = float(self.config.section("server")["request_timeout_s"])
        gates_cfg = self.config.section("gates")
        prep_start = time.perf_counter()
        payload: Any
        if point.kind == "replay":
            payload = build_replay_plans(point, tokenizer, allowed, size, pool)
        elif point.kind == "smoke-server":
            payload = build_smoke_requests(point, tokenizer, allowed, size, pool)
        else:
            payload = build_open_loop_requests(
                point, tokenizer, allowed, size, pool, collect_token_ids=point.kind == "aa"
            )
        prep_s = time.perf_counter() - prep_start
        reset = engine.reset_caches()
        before = engine.metrics()
        api_start = read_cpu_ticks(engine.pid) if engine.pid else None
        me_start = read_cpu_ticks(os.getpid())
        stop = StopToken(
            deadline=max(deadline, time.perf_counter() + 1.0),
            external=self.stop_event,
            grace_s=float(self.config.section("stop")["in_flight_grace_s"]),
        )
        kv: list[tuple[float, float | None, float | None, float | None]] = []
        started = time.perf_counter()
        body = asyncio.run(self._server_coroutine(point, engine, payload, stop, kv, timeout_s))
        finished = time.perf_counter()
        after = engine.metrics()
        wall = finished - started
        api_end = read_cpu_ticks(engine.pid) if engine.pid else None
        result = body["result"]
        deltas = point_counter_deltas(before, after)
        counters = check_counters(
            deltas,
            client_prompt_tokens=int(result["prompt_tokens"]),
            client_output_tokens=int(result["output_tokens"]),
            prompt_tolerance=float(gates_cfg["prompt_counter_relative_tolerance"]),
        )
        self._write_kv_trace(point.point_id, kv)
        out: dict[str, Any] = {
            "prep_s": prep_s,
            "cache_reset": reset,
            "result": result,
            "counters": deltas,
            "counter_check": counters,
            "gpu": summarize_gpu(self.sampler.window(started, finished)),
            "api_server_cpu_pct": cpu_percent(api_start, api_end, wall),
            "client_cpu_pct": cpu_percent(me_start, read_cpu_ticks(os.getpid()), wall),
            "kv_cache_usage_peak": max((r[1] for r in kv if r[1] is not None), default=None),
            "num_requests_waiting_peak": max((r[3] for r in kv if r[3] is not None), default=None),
            "ran_to_end": body["ran_to_end"],
            "stop_reason": body["stop_reason"],
        }
        if "agreement" in body:
            out["agreement"] = body["agreement"]
            out["cache_reset_between_arms"] = body["cache_reset_between_arms"]
        if point.kind == "smoke-server":
            differential = image_differential(
                body["results"],
                int(gates_cfg["image_tokens_expected"]),
                float(gates_cfg["image_tokens_relative_tolerance"]),
            )
            smoke_ok = (
                result["failed"] == 0
                and result["completed"] == result["planned"]
                and result["short_outputs"] == 0
            )
            out["gates"] = {
                "G0.6": {
                    "pass": bool(smoke_ok and differential["pass"]),
                    "smoke_ok": smoke_ok,
                    "image_differential": differential,
                },
                "G0.7": counters,
            }
        return out

    async def _server_coroutine(
        self,
        point: PointSpec,
        engine: Any,
        payload: Any,
        stop: StopToken,
        kv: list[Any],
        timeout_s: float,
    ) -> dict[str, Any]:
        done = asyncio.Event()
        interval = float(self.config.section("sampling")["kv_poll_interval_s"])

        async def poll(client: httpx.AsyncClient) -> None:
            while not done.is_set():
                with contextlib.suppress(httpx.HTTPError):
                    snapshot = parse_prometheus((await client.get("/metrics")).text)
                    kv.append(
                        (
                            time.perf_counter(),
                            snapshot.get("vllm:kv_cache_usage_perc"),
                            snapshot.get("vllm:num_requests_running"),
                            snapshot.get("vllm:num_requests_waiting"),
                        )
                    )
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(done.wait(), timeout=interval)

        output_tokens = int(point["output_tokens"])
        async with engine.async_client() as client:
            poller = asyncio.create_task(poll(client))
            try:
                if point.kind == "replay":
                    records, start, end, spans = await run_replay(
                        client, payload, model=engine.served_name, timeout_s=timeout_s, stop=stop
                    )
                    planned_steps = payload[0].steps if payload else []
                    result = summarize_replay(
                        records,
                        episodes=len(payload),
                        planned_steps=planned_steps,
                        start=start,
                        end=end,
                        spans=spans,
                        expected_output=output_tokens,
                    )
                    ran_to_end = len(records) == len(payload) * len(planned_steps)
                    return {
                        "result": result,
                        "ran_to_end": ran_to_end,
                        "stop_reason": None if ran_to_end else stop.reason(),
                    }
                if point.kind == "aa":
                    between_resets: list[dict[str, Any]] = []

                    async def between() -> None:
                        between_resets.append(await asyncio.to_thread(engine.reset_caches))

                    started = stop.clock()
                    arms = await run_aa(
                        client,
                        payload,
                        arms=point["arms"],
                        model=engine.served_name,
                        timeout_s=timeout_s,
                        stop=stop,
                        between_arms=between,
                    )
                    flat = [result for arm in arms for result in arm]
                    planned = len(payload) * len(point["arms"])
                    result = summarize_requests(
                        flat,
                        planned=planned,
                        start=started,
                        end=stop.clock(),
                        expected_output=output_tokens,
                    )
                    ran_to_end = len(flat) == planned
                    return {
                        "result": result,
                        "agreement": aa_agreement(arms),
                        "cache_reset_between_arms": between_resets,
                        "ran_to_end": ran_to_end,
                        "stop_reason": None if ran_to_end else stop.reason(),
                    }
                results, start, end, unlaunched = await run_open_loop(
                    client,
                    payload,
                    concurrency=int(point["concurrency"]),
                    model=engine.served_name,
                    timeout_s=timeout_s,
                    stop=stop,
                )
                result = summarize_requests(
                    results,
                    planned=len(payload),
                    start=start,
                    end=end,
                    expected_output=output_tokens,
                )
                ran_to_end = unlaunched == 0 and len(results) == len(payload)
                return {
                    "result": result,
                    "results": results,
                    "ran_to_end": ran_to_end,
                    "stop_reason": None if ran_to_end else stop.reason(),
                }
            finally:
                done.set()
                await poller

    def _write_kv_trace(self, point_id: str, rows: Sequence[Any]) -> None:
        path = self.output_dir / "samples" / f"kv-{point_id}.csv"
        with path.open("w", encoding="utf-8") as handle:
            handle.write("t,kv_cache_usage_perc,num_requests_running,num_requests_waiting\n")
            for row in rows:
                handle.write(",".join("" if value is None else f"{value}" for value in row) + "\n")

    # -- offline points ---------------------------------------------------

    def _offline_point(
        self, point: PointSpec, engine: Any, allowed: np.ndarray, deadline: float
    ) -> dict[str, Any]:
        prep_start = time.perf_counter()
        prompts = build_offline_prompts(point, allowed)
        prep_s = time.perf_counter() - prep_start
        n = int(point["n"])
        output_tokens = int(point["output_tokens"])
        input_tokens = int(point["input_tokens"])
        planned = len(prompts) * n
        reset = engine.reset_caches()
        before = engine.metrics()
        started = time.perf_counter()
        lengths: list[list[int]] = []
        stop_reason = None
        self.blocking = True
        signal.setitimer(signal.ITIMER_REAL, max(1.0, deadline - started))
        try:
            lengths = engine.generate(
                prompts,
                n=n,
                temperature=float(point["temperature"]),
                top_p=float(point.get("top_p", 1.0)),
                max_tokens=output_tokens,
            )
        except ProbeDeadline:
            stop_reason = "deadline"
        except ProbeInterrupted:
            stop_reason = "signal"
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            self.blocking = False
        finished = time.perf_counter()
        abort: dict[str, Any] | None = None
        if stop_reason is not None:
            # The interrupted call's requests are still in the engine; the next
            # point's generate() would finish them and count them as its own.
            abort = engine.abort_unfinished()
            self.log(f"{point.point_id}: stopped by {stop_reason}; abort {abort}")
            if stop_reason == "signal":
                raise ProbeInterrupted(self.signal_name or "signal")
        after = engine.metrics()
        completions = sum(len(choice) for choice in lengths)
        generated = sum(sum(choice) for choice in lengths)
        duration = finished - started
        result = {
            "planned": planned,
            "completed": completions,
            "completions": completions,
            "failed": planned - completions,
            "duration_s": duration,
            "prompt_tokens": len(prompts) * input_tokens,
            "output_tokens": generated,
            "short_outputs": sum(1 for c in lengths for length in c if length != output_tokens),
            "output_throughput": generated / duration if duration > 0 else None,
            "completions_per_s": completions / duration if duration > 0 else None,
            "gpu_s_per_completion": duration / completions if completions else None,
        }
        deltas = point_counter_deltas(before, after)
        counters = check_counters(
            deltas,
            client_prompt_tokens=len(prompts) * input_tokens,
            client_output_tokens=generated,
            prompt_tolerance=float(
                self.config.section("gates")["prompt_counter_relative_tolerance"]
            ),
            alternative_prompt_tokens=[len(prompts) * n * input_tokens],
        )
        ran_to_end = stop_reason is None and completions == planned
        out: dict[str, Any] = {
            "prep_s": prep_s,
            "cache_reset": reset,
            "result": result,
            "counters": deltas,
            "counter_check": counters,
            "gpu": summarize_gpu(self.sampler.window(started, finished)),
            "ran_to_end": ran_to_end,
            "stop_reason": stop_reason,
            "abort": abort,
        }
        if point.kind == "smoke-offline":
            smoke_ok = completions == planned and result["short_outputs"] == 0
            out["gates"] = {"G0.6": {"pass": smoke_ok, "smoke_ok": smoke_ok}, "G0.7": counters}
        return out

    # -- finalize -----------------------------------------------------------

    def _finalize(self, status: str, exit_code: int) -> None:
        with contextlib.suppress(Exception):
            if self.sampler is not None:
                self.sampler.stop()
        points: dict[str, dict[str, Any]] = {}
        point_sha256: dict[str, str] = {}
        if self.points_dir.is_dir():
            for path in sorted(self.points_dir.glob("*.json")):
                record = json.loads(path.read_text(encoding="utf-8"))
                points[record["point_id"]] = record
                point_sha256[path.stem] = sha256_file(path)
        self.summary["points"] = {name: record.get("status") for name, record in points.items()}
        # The projection admits this job's points only if the files on disk are
        # exactly these (a later, unfinished resubmission cannot slip points in).
        self.summary["point_sha256"] = point_sha256
        validity = self.config.section("validity")
        limit = float(validity["unstable_relative_range"])
        if self.job.job_id == "a":
            self.summary["x1"] = budget_rules.evaluate_x1(
                points,
                max_relative_delta=float(
                    self.config.section("dummy_admissibility")["max_relative_delta"]
                ),
            )
            self.summary["a1_stability"] = budget_rules.stability(
                points, ("a1a", "a1b", "a1c"), limit
            )
            agreement = points.get("d8", {}).get("agreement")
            if agreement:
                self.summary["aa_agreement_rate"] = agreement.get("agreement_rate")
        if self.job.job_id == "b":
            self.summary["b1_stability"] = budget_rules.stability(
                points, ("b1a", "b1b", "b1c"), limit, metric="completions_per_s"
            )
        self.summary.update(
            {
                "status": status,
                "exit_code": exit_code,
                "finished_at": utc_now(),
                "signal": self.signal_name,
                "signals_received": list(self.signals_received),
            }
        )
        self.summary["acceptance"] = job_acceptance(self.summary)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self.output_dir / "summary.json", self.summary)
        self._write_progress(status)
        # The marker answers signals only; a run that received none never writes it.
        self._checkpoint_after_signal(state=status)
        self._reaper_stop.set()
        if os.getpid() == 1:
            self._reap_once()


def job_acceptance(summary: Mapping[str, Any]) -> dict[str, Any]:
    """Whether a finished job's points may enter a budget (preregistration section 5).

    Accepted: status complete or complete-with-cuts and every job-level gate (G0.0
    to G0.4) recorded as passed; a gate that was never recorded counts as failed.
    G0.5 not passed with the eager fallback labels the job eager. A phase whose
    gate failed has all its points not-run; it is listed, and only blocks
    acceptance when it is the primary phase (which ends the job as a pre-result).
    The projection additionally requires exit code 0 and the recorded point files
    (:func:`job_admission`).
    """
    gates = summary.get("gates", {})
    job_gate_failures = sorted(
        {gate for gate in JOB_GATES if not (gates.get(gate) or {}).get("pass")}
        | {
            gate
            for gate, verdict in gates.items()
            if gate not in PHASE_GATES and not verdict.get("pass")
        }
    )
    phase_failures: dict[str, list[str]] = {}
    eager_phases = []
    for gate in PHASE_GATES:
        for phase, verdict in gates.get(gate, {}).items():
            if verdict.get("pass"):
                continue
            if gate == "G0.5" and verdict.get("eager_fallback"):
                eager_phases.append(phase)
                continue
            phase_failures.setdefault(phase.split("/", 1)[0], []).append(gate)
    status = summary.get("status")
    accepted = status in ACCEPTED_JOB_STATUSES and not job_gate_failures
    return {
        "accepted": bool(accepted),
        "status": status,
        "eager": bool(eager_phases),
        "eager_phases": sorted(eager_phases),
        "job_gate_failures": job_gate_failures,
        "phase_gate_failures": {phase: sorted(set(g)) for phase, g in phase_failures.items()},
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def resolve_config_path(path: Path) -> Path:
    """Absolute paths as given; relative ones from the working directory, else the repo root."""
    if path.is_absolute():
        return path
    candidate = Path.cwd() / path
    return candidate.resolve() if candidate.exists() else (PROJECT_ROOT / path).resolve()


def _display_path(path: Path) -> str:
    resolved = path.resolve()
    if resolved.is_relative_to(PROJECT_ROOT):
        return resolved.relative_to(PROJECT_ROOT).as_posix()
    return str(resolved)


PARSED_FLAG_CHECKS = (
    "load_format",
    "max_model_len",
    "gpu_memory_utilization",
    "max_num_seqs",
    "max_num_batched_tokens",
    "enable_prefix_caching",
    "generation_config",
    "tensor_parallel_size",
    "seed",
    "dtype",
)


def compare_parsed_flags(engine: EngineSpec, parsed: Mapping[str, Any]) -> list[str]:
    """Differences between the contract and what vLLM's own parser produced."""
    expected = {**dict(engine.flags), "load_format": engine.load_format}
    problems = [
        f"{key}: contract {expected[key]!r} parsed {parsed.get(key)!r}"
        for key in PARSED_FLAG_CHECKS
        if key in expected and parsed.get(key) != expected[key]
    ]
    if parsed.get("speculative_config") not in (None, {}):
        problems.append("speculative decoding is configured")
    if parsed.get("enforce_eager"):
        problems.append("eager mode is forced")
    return problems


def vllm_args_doctor(config: ProbeConfig) -> dict[str, Any]:
    """CPU-only build check: vLLM's parsers accept every engine flag and request payload.

    Pins vLLM's CPU platform so argument parsing needs no GPU; nothing is executed
    on a device and no model is loaded.
    """
    import vllm.platforms
    from vllm.platforms.cpu import CpuPlatform

    vllm.platforms._current_platform = CpuPlatform()  # parse-only; see docstring
    from vllm.engine.arg_utils import EngineArgs
    from vllm.entrypoints.launchers.cli_args import make_arg_parser, validate_parsed_serve_args
    from vllm.entrypoints.openai.chat_completion.protocol import ChatCompletionRequest
    from vllm.utils.argparse_utils import FlexibleArgumentParser

    from harness.serving_probe.client import build_payload

    server = config.section("server")
    report: dict[str, Any] = {"engines": {}, "pass": True}
    for engine_id, engine in config.engines.items():
        if engine.mode == "server":
            argv = engine.server_argv(
                f"/model-cache/cotcodec-models/{engine.model}",
                host=str(server["host"]),
                port=int(server["port"]),
                served_name=str(server["served_model_name"]),
            )
            parsed = make_arg_parser(FlexibleArgumentParser()).parse_args(argv[2:])
            validate_parsed_serve_args(parsed)
            problems = compare_parsed_flags(engine, vars(parsed))
        else:
            kwargs = engine.offline_kwargs()
            kwargs.pop("disable_log_stats", None)
            parsed = EngineArgs(model=f"/model-cache/cotcodec-models/{engine.model}", **kwargs)
            problems = compare_parsed_flags(engine, vars(parsed))
        report["engines"][engine_id] = {"problems": problems}
        report["pass"] = report["pass"] and not problems
    image = {"type": "image_url", "image_url": {"url": "data:image/png;base64,AA=="}}
    message = [{"role": "user", "content": [{"type": "text", "text": "x"}, image]}]
    for thinking in (False, True):
        payload = build_payload(
            ChatRequest(message, 300, thinking, collect_token_ids=True), model="m"
        )
        request = ChatCompletionRequest(**payload)
        ok = (
            request.ignore_eos is True
            and request.min_tokens == 300
            and request.return_token_ids is True
            and request.chat_template_kwargs == {"enable_thinking": thinking}
            and request.stream is True
        )
        report[f"payload_thinking_{thinking}"] = ok
        report["pass"] = report["pass"] and ok
    return report


def plan_payload(config: ProbeConfig, job: JobSpec, model_root: str) -> dict[str, Any]:
    server = config.section("server")
    phases = []
    for phase in job.phases:
        model_dir = f"{model_root}/{phase.engine.model}"
        entry: dict[str, Any] = {
            "phase": phase.phase_id,
            "engine": phase.engine.engine_id,
            "mode": phase.engine.mode,
            "model": phase.engine.model,
            "load_format": phase.engine.load_format,
            "reserve_minutes": phase.reserve_minutes,
            "points": [
                {
                    "point_id": p.point_id,
                    "kind": p.kind,
                    "seed": p.seed,
                    "max_minutes": p.max_minutes,
                    **dict(p.params),
                }
                for p in phase.points
            ],
        }
        if phase.engine.mode == "server":
            entry["argv"] = phase.engine.server_argv(
                model_dir,
                host=str(server["host"]),
                port=int(server["port"]),
                served_name=str(server["served_model_name"]),
            )
        else:
            entry["llm_kwargs"] = phase.engine.offline_kwargs()
        phases.append(entry)
    return {
        "experiment_id": config.experiment_id,
        "config_sha256": config.sha256,
        "job": job.job_id,
        "title": job.title,
        "allocation_minutes": job.allocation_minutes,
        "lane_model": job.lane_model,
        "pinned_models": job.pinned_models(),
        "primary_seeds": list(config.primary_seeds),
        "phases": phases,
        "cache_env": sorted(CACHE_DIRS),
    }


class ProjectionError(RuntimeError):
    """A job directory does not belong to this contract, job or experiment."""


def load_job_points(directory: Path, config: ProbeConfig, job_id: str) -> dict[str, dict[str, Any]]:
    """Point files of one job, refusing any written under another contract, job or experiment."""
    job = config.job(job_id)
    expected = {point.point_id for phase in job.phases for point in phase.points}
    points: dict[str, dict[str, Any]] = {}
    for path in sorted((directory / "points").glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        problems = []
        if record.get("experiment_id") != config.experiment_id:
            problems.append(f"experiment {record.get('experiment_id')!r}")
        if record.get("config_sha256") != config.sha256:
            problems.append(f"contract {record.get('config_sha256')!r}")
        if record.get("job") != job_id:
            problems.append(f"job {record.get('job')!r}")
        if record.get("point_id") not in expected or path.stem != record.get("point_id"):
            problems.append(f"point {record.get('point_id')!r}")
        if problems:
            raise ProjectionError(
                f"{path} is not a job-{job_id} point of this contract: {problems}"
            )
        points[record["point_id"]] = record
    return points


def job_admission(directory: Path, config: ProbeConfig, job_id: str) -> dict[str, Any]:
    """Whether a job's points may enter a budget (preregistration sections 5 and 8).

    Admitted (``accepted``) only when summary.json exists and belongs to this
    experiment, contract and job; records ``acceptance.accepted: true``; the
    acceptance recomputed from its own status and gates agrees; the driver's exit
    code is 0; and it lists the SHA-256 of exactly the point files on disk. A job
    that fails any of these is reported with its reasons, and none of its points
    enters a budget.
    """
    path = directory / "summary.json"
    if not path.is_file():
        return {
            "summary": None,
            "accepted": False,
            "reasons": ["no summary.json (the driver did not finish)"],
        }
    summary = json.loads(path.read_text(encoding="utf-8"))
    if (
        summary.get("experiment_id") != config.experiment_id
        or summary.get("config_sha256") != config.sha256
        or summary.get("job") != job_id
    ):
        raise ProjectionError(f"{path} belongs to another experiment, contract or job")
    reasons: list[str] = []
    recorded = summary.get("acceptance") or {}
    if recorded.get("accepted") is not True:
        reasons.append(
            f"summary records acceptance.accepted {recorded.get('accepted')!r} "
            f"(status {summary.get('status')!r})"
        )
    recomputed = job_acceptance(summary)
    if not recomputed["accepted"]:
        reasons.append(
            f"acceptance recomputed from the summary is false (status "
            f"{summary.get('status')!r}, job gate failures {recomputed['job_gate_failures']})"
        )
    if summary.get("exit_code") != EXIT_OK:
        reasons.append(f"driver exit code {summary.get('exit_code')!r}")
    on_disk = {p.stem: sha256_file(p) for p in sorted((directory / "points").glob("*.json"))}
    listed = summary.get("point_sha256")
    if not isinstance(listed, Mapping):
        reasons.append("summary lists no point SHA-256s")
    elif dict(listed) != on_disk:
        changed = sorted(
            name for name in set(listed) | set(on_disk) if listed.get(name) != on_disk.get(name)
        )
        reasons.append(f"point files differ from those the summary lists: {changed}")
    return {
        "summary_sha256": sha256_file(path),
        "status": summary.get("status"),
        "exit_code": summary.get("exit_code"),
        "acceptance": recorded,
        "eager": summary.get("eager"),
        "image_variant": summary.get("image_variant"),
        "accepted": not reasons,
        "reasons": reasons,
    }


def _x1(config: ProbeConfig, points: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    return budget_rules.evaluate_x1(
        points,
        max_relative_delta=float(config.section("dummy_admissibility")["max_relative_delta"]),
    )


def job_c_gate(config: ProbeConfig, job_a: Path) -> dict[str, Any]:
    """Job C is submitted only after an accepted job A whose control X1 passed.

    The manifest renderer calls this before it renders job C (design decision 33).
    """
    points = load_job_points(job_a, config, "a")
    admission = job_admission(job_a, config, "a")
    x1 = _x1(config, points if admission["accepted"] else {})
    return {
        "job_a": admission,
        "x1": x1,
        "submit": bool(admission["accepted"] and x1["outcome"] == "pass"),
    }


def project(
    config: ProbeConfig,
    *,
    job_a: Path,
    job_b: Path | None,
    job_c: Path | None,
    prereg_check: Callable[[ProbeConfig], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Apply the preregistered budget rules to finished job outputs.

    Refuses unless the frozen preregistration names this contract and this probe
    code (the G0.0 check), and refuses point files from another contract, job or
    experiment. Only an admitted job's points enter a budget (:func:`job_admission`):
    job A not admitted gives X1 not-run and no Q2 budget, job B not admitted (or not
    given) no Q1 budget, and job C not admitted is treated as not run. The output
    records the ledger row, the code digest and git HEAD.
    """
    try:
        prereg = (prereg_check or verify_preregistration)(config)
    except GateFailure as exc:
        raise ProjectionError(f"projection refused: {exc}") from exc
    budget = config.section("budget")
    limit = float(config.section("validity")["unstable_relative_range"])
    directories = {
        name: directory
        for name, directory in (("a", job_a), ("b", job_b), ("c", job_c))
        if directory is not None
    }
    # Foreign point files are refused whether or not the job is admitted.
    loaded = {
        name: load_job_points(directory, config, name) for name, directory in directories.items()
    }
    jobs = {name: job_admission(directory, config, name) for name, directory in directories.items()}
    used = {name: points for name, points in loaded.items() if jobs[name]["accepted"]}
    inputs: dict[str, str] = {}
    for name in ("a", "b", "c"):
        if name not in jobs:
            inputs[name] = "not supplied"
        elif jobs[name]["accepted"]:
            inputs[name] = "used"
        else:
            inputs[name] = "not accepted, points reported only: " + "; ".join(jobs[name]["reasons"])
    if "c" in jobs and "c" not in used:
        inputs["c"] += " (treated as not run: the active-parameter rule applies)"
    points_a = used.get("a")
    x1 = _x1(config, points_a or {})
    if points_a is None:
        x1["reason"] = "job a is not accepted; its points enter no budget"
    out: dict[str, Any] = {
        "experiment_id": config.experiment_id,
        "config_sha256": config.sha256,
        "preregistration": prereg,
        "code": {**probe_code_digest(), "git": git_revision()},
        "jobs": jobs,
        "budget_inputs": inputs,
        "x1": x1,
        "a1_stability": (
            None
            if points_a is None
            else budget_rules.stability(points_a, ("a1a", "a1b", "a1c"), limit)
        ),
    }
    max_model_len = max(
        int(config.engines[phase.engine.engine_id].flags["max_model_len"])
        for phase in config.job("a").phases
    )
    if points_a is None:
        out["q2"] = {"decision": "incomplete-re-probe", "reason": f"job a is {inputs['a']}"}
    else:
        try:
            out["q2"] = budget_rules.project_q2(
                budget,
                job_a=points_a,
                job_c=used.get("c"),
                x1_outcome=x1["outcome"],
                unstable_limit=limit,
                max_model_len=max_model_len,
            )
        except budget_rules.BudgetError as exc:
            out["q2"] = {"decision": "incomplete-re-probe", "reason": str(exc)}
    points_b = used.get("b")
    out["b1_stability"] = (
        None
        if points_b is None
        else budget_rules.stability(
            points_b, ("b1a", "b1b", "b1c"), limit, metric="completions_per_s"
        )
    )
    if points_b is None:
        out["q1"] = {"decision": "incomplete-re-probe", "reason": f"job b is {inputs['b']}"}
    else:
        try:
            out["q1"] = budget_rules.project_q1(
                budget, job_b=points_b, x1_outcome=x1["outcome"], unstable_limit=limit
            )
        except budget_rules.BudgetError as exc:
            out["q1"] = {"decision": "incomplete-re-probe", "reason": str(exc)}
    return out


def build_parser() -> argparse.ArgumentParser:
    # allow_abbrev=False everywhere: the lane's seed binding assumes no option can be
    # reached by an abbreviation (docs/operations.md, seed_binding).
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    commands = parser.add_subparsers(dest="command", required=True)

    plan = commands.add_parser("plan", allow_abbrev=False)
    plan.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    plan.add_argument("--job", required=True)
    plan.add_argument("--model-root", default="/model-cache/cotcodec-models")

    run = commands.add_parser("run", allow_abbrev=False)
    run.add_argument("--config", type=Path, required=True)
    run.add_argument("--job", required=True)
    run.add_argument("--output-dir", type=Path, required=True)
    run.add_argument("--model-root", type=Path, default=Path("/model-cache/cotcodec-models"))
    run.add_argument("--receipt-root", type=Path, default=Path("/model-cache/cotcodec-receipts"))
    run.add_argument("--allocation-minutes", type=int, required=True)
    run.add_argument("--image-variant", default="cu129")
    run.add_argument("--weights-pin", action="append", default=[])
    run.add_argument("--seeds", type=int, nargs="+", required=True)

    doctor = commands.add_parser("cuda-doctor", allow_abbrev=False)
    doctor.add_argument("--output", type=Path, required=True)
    doctor.add_argument("--matmul-size", type=int, required=True)
    doctor.add_argument("--max-error", type=float, required=True)
    doctor.add_argument("--seed", type=int, default=42)
    doctor.add_argument("--expected-gpus", type=int, default=1)
    doctor.add_argument("--expected-vllm-version", required=True)
    doctor.add_argument("--expected-vllm-commit", required=True)
    doctor.add_argument("--cache-root", type=Path, required=True)

    args_doctor = commands.add_parser("vllm-args-doctor", allow_abbrev=False)
    args_doctor.add_argument("--config", type=Path, default=DEFAULT_CONFIG)

    proj = commands.add_parser("project", allow_abbrev=False)
    proj.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    proj.add_argument("--job-a", type=Path, required=True)
    proj.add_argument("--job-b", type=Path)
    proj.add_argument("--job-c", type=Path)
    proj.add_argument("--output", type=Path, required=True)

    commands.add_parser("digest", allow_abbrev=False).add_argument(
        "--config", type=Path, default=DEFAULT_CONFIG
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "cuda-doctor":
        from harness.serving_probe.cuda_doctor import run_cuda_doctor

        report = run_cuda_doctor(
            output=args.output,
            matmul_size=args.matmul_size,
            max_error=args.max_error,
            seed=args.seed,
            expected_gpus=args.expected_gpus,
            expected_vllm_version=args.expected_vllm_version,
            expected_vllm_commit=args.expected_vllm_commit,
            cache_root=args.cache_root,
        )
        return 0 if report["pass"] else EXIT_PRE_RESULT
    config = load_config(resolve_config_path(args.config))
    if args.command == "vllm-args-doctor":
        report = vllm_args_doctor(config)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["pass"] else EXIT_PRE_RESULT
    if args.command == "plan":
        print(
            json.dumps(
                plan_payload(config, config.job(args.job), args.model_root),
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if args.command == "digest":
        print(
            json.dumps(
                {"contract_sha256": config.sha256, **probe_code_digest()},
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if args.command == "project":
        if args.output.exists():
            raise SystemExit(f"refusing to overwrite {args.output}")
        try:
            payload = project(config, job_a=args.job_a, job_b=args.job_b, job_c=args.job_c)
        except ProjectionError as exc:
            print(f"refused: {exc}", file=sys.stderr)
            return EXIT_PRE_RESULT
        atomic_write_json(args.output, payload)
        print(
            json.dumps(
                {
                    "q2": payload.get("q2", {}).get("decision"),
                    "q1": payload.get("q1", {}).get("decision"),
                    "x1": payload["x1"]["outcome"],
                },
                sort_keys=True,
            )
        )
        return 0
    try:
        job = config.job(args.job)
        seeds = bind_seeds(config, args.seeds)
        if args.allocation_minutes != job.allocation_minutes:
            raise ProbeConfigError(
                f"--allocation-minutes {args.allocation_minutes} differs from the contract's "
                f"{job.allocation_minutes}"
            )
        pins = parse_weight_pins(args.weights_pin)
        check_pins(job, pins)
    except ProbeConfigError as exc:
        print(f"pre-result: {exc}", file=sys.stderr)
        return EXIT_PRE_RESULT
    marker = os.environ.get("COTCODEC_CHECKPOINT_MARKER")
    outputs_root = Path(os.environ.get("COTCODEC_OUTPUT_DIR", str(args.output_dir.parent)))
    runner = ProbeRunner(
        config=config,
        job=job,
        output_dir=args.output_dir,
        outputs_root=outputs_root,
        model_root=args.model_root,
        receipt_root=args.receipt_root,
        pins=pins,
        image_variant=args.image_variant,
        seeds=seeds,
        argv=list(argv) if argv is not None else list(sys.argv),
        marker_path=Path(marker) if marker else None,
    )
    return runner.run()


if __name__ == "__main__":
    raise SystemExit(main())
