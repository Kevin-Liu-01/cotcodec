#!/usr/bin/env python3
"""LM1 host smoke test: load each GGUF candidate in stock llama.cpp and record what it costs.

D125 prepares the H100 host for LM1 (does a 1T-class model at about 1.8 bits beat smaller models
near native precision at a matched memory cap of about 128 GB?). This driver runs inside the
program's lane, in an overlay of the stock llama.cpp CUDA image, on the GPUs Slurm allocated. For
each model of a committed plan it:

1. checks the model's receipt in the lane's receipt root against the plan (receipt SHA-256,
   revision, artifact root recomputed from the receipt's file list, every file present at its
   recorded size; the full SHA-256 re-hash runs in a CPU job before this one);
2. starts ``llama-server`` with every layer on the GPUs (``-ngl all --split-mode layer``,
   ``-fit off`` so nothing is adjusted behind the plan's back) and times the load until
   ``/health`` answers;
3. sends three fixed greedy requests: a long prompt with one generated token (prefill speed), a
   short prompt with a fixed number of generated tokens (decode speed and the output), and one
   chat turn through the model's own template (a template check, not scored);
4. polls ``nvidia-smi`` throughout and keeps the peak memory of every visible GPU;
5. stops the server and writes one text-free row: timings, peaks, the server's offload lines, and
   a short SHA-256 of each output. The output text stays in the run directory on the host.

The rows are an infrastructure smoke test. Single greedy samples say whether a file loads, how
fast it runs on this hardware and whether its text looks broken; they say nothing about quality.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.fetch_open_model import (  # noqa: E402
    DEFAULT_REGISTRY,
    artifact_root,
    load_registry,
)

SHA_RE = re.compile(r"^[0-9a-f]{64}$")
GPU_UUID_RE = re.compile(r"^GPU-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
MODEL_ID_RE = re.compile(r"^[a-z0-9][a-z0-9.-]{0,79}$")
REL_PATH_RE = re.compile(r"^[A-Za-z0-9._][A-Za-z0-9._/-]{0,254}$")
# The server flags the plan may not set itself: the driver owns placement, the port and threads.
RESERVED_FLAGS = frozenset(
    {
        "-m",
        "--model",
        "--host",
        "--port",
        "-t",
        "--threads",
        "-ngl",
        "--gpu-layers",
        "--n-gpu-layers",
        "-sm",
        "--split-mode",
        "-fit",
        "--fit",
        "-dev",
        "--device",
    }
)
FIXED_SERVER_ARGS = ("-ngl", "all", "--split-mode", "layer", "-fit", "off")
OFFLOAD_RE = re.compile(r"offloaded (\d+)/(\d+) layers to GPU")
BUFFER_RE = re.compile(r"(\S+) (model|KV|compute) buffer size = +([0-9.]+) MiB")
CPU_FALLBACK_RE = re.compile(r"using CPU instead")


class SmokeError(ValueError):
    """Raised when the plan, a receipt or an argument violates the contract."""


class _NotReady(Exception):
    """The server exited or timed out before /health answered."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def short_hash(text: str) -> str:
    """The first 16 hex characters of the SHA-256 of the UTF-8 text."""

    return sha256_bytes(text.encode("utf-8"))[:16]


# --- Plan --------------------------------------------------------------------------------------


def _string(mapping: dict[str, Any], key: str, where: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value:
        raise SmokeError(f"{where}: {key} must be a non-empty string")
    return value


def _positive_int(mapping: dict[str, Any], key: str, where: str, maximum: int) -> int:
    value = mapping.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= maximum:
        raise SmokeError(f"{where}: {key} must be an integer in [1, {maximum}]")
    return value


def validate_plan(plan: Any, registry: dict[str, Any] | None = None) -> dict[str, Any]:
    """Validate a smoke plan and return it unchanged.

    With a registry, every model must be registered, run on llama.cpp, carry no remote code and
    list the plan's GGUF entry file among its required files.
    """

    if not isinstance(plan, dict) or plan.get("schema_version") != 1:
        raise SmokeError("plan must be a schema_version: 1 mapping")
    _string(plan, "experiment", "plan")
    server = _string(plan, "llama_server", "plan")
    if not server.startswith("/"):
        raise SmokeError("plan: llama_server must be an absolute path")
    args = plan.get("server_args")
    if not isinstance(args, list) or not all(isinstance(a, str) and a for a in args):
        raise SmokeError("plan: server_args must be a string list")
    reserved = sorted(set(args) & RESERVED_FLAGS)
    if reserved:
        raise SmokeError(f"plan: server_args may not set {reserved}; the driver owns them")
    requests = plan.get("requests")
    if not isinstance(requests, dict):
        raise SmokeError("plan: requests must be a mapping")
    _string(requests, "prefill_prompt", "requests")
    _string(requests, "completion_prompt", "requests")
    _string(requests, "chat_message", "requests")
    _positive_int(requests, "completion_tokens", "requests", 4096)
    _positive_int(requests, "chat_tokens", "requests", 4096)
    _positive_int(requests, "request_timeout_s", "requests", 3600)
    seed = requests.get("seed")
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise SmokeError("requests: seed must be an integer")
    refused = plan.get("refuse_gpu_uuids", [])
    if not isinstance(refused, list) or not all(
        isinstance(u, str) and GPU_UUID_RE.fullmatch(u) for u in refused
    ):
        raise SmokeError("plan: refuse_gpu_uuids must be a list of GPU UUIDs")
    models = plan.get("models")
    if not isinstance(models, list) or not models:
        raise SmokeError("plan: models must be a non-empty list")
    seen: set[str] = set()
    registered = (registry or {}).get("models", {})
    for index, model in enumerate(models):
        where = f"models[{index}]"
        if not isinstance(model, dict):
            raise SmokeError(f"{where} must be a mapping")
        model_id = _string(model, "model_id", where)
        if not MODEL_ID_RE.fullmatch(model_id) or model_id in seen:
            raise SmokeError(f"{where}: model_id is unsafe or repeated")
        seen.add(model_id)
        gguf = _string(model, "gguf", where)
        if (
            not REL_PATH_RE.fullmatch(gguf)
            or ".." in Path(gguf).parts
            or not gguf.endswith(".gguf")
        ):
            raise SmokeError(f"{where}: gguf must be a safe relative .gguf path")
        for key in ("receipt_sha256", "artifact_root_sha256"):
            if not SHA_RE.fullmatch(str(model.get(key, ""))):
                raise SmokeError(f"{where}: {key} must be 64 lowercase hex characters")
        _positive_int(model, "load_timeout_s", where, 3600)
        extra = model.get("extra_args", [])
        if not isinstance(extra, list) or not all(isinstance(a, str) and a for a in extra):
            raise SmokeError(f"{where}: extra_args must be a string list")
        if set(extra) & RESERVED_FLAGS:
            raise SmokeError(f"{where}: extra_args may not set driver-owned flags")
        if registry is not None:
            entry = registered.get(model_id)
            if entry is None:
                raise SmokeError(f"{where}: {model_id} is not in models/registry.yaml")
            if entry.get("runtime") != "llama.cpp" or entry.get("trust_remote_code") is not False:
                raise SmokeError(
                    f"{where}: {model_id} is not a llama.cpp entry without remote code"
                )
            if gguf not in entry.get("required_files", []):
                raise SmokeError(f"{where}: {gguf} is not a required file of {model_id}")
    return plan


def load_plan(path: Path, expected_sha256: str | None, registry: dict[str, Any]) -> dict[str, Any]:
    raw = path.read_bytes()
    if expected_sha256 is not None and sha256_bytes(raw) != expected_sha256:
        raise SmokeError("plan SHA-256 differs from the expected digest")
    return validate_plan(json.loads(raw), registry)


# --- Receipts ----------------------------------------------------------------------------------


def check_receipt(
    model: dict[str, Any],
    entry: dict[str, Any],
    model_root: Path,
    receipt_root: Path,
) -> dict[str, Any]:
    """Cheap receipt check: identity, digests and file sizes; no re-hash of the weights."""

    model_id = model["model_id"]
    path = receipt_root / f"{model_id}.json"
    if not path.is_file() or path.is_symlink():
        raise SmokeError(f"{model_id}: receipt missing at {path}")
    raw = path.read_bytes()
    if sha256_bytes(raw) != model["receipt_sha256"]:
        raise SmokeError(f"{model_id}: receipt SHA-256 differs from the plan")
    receipt = json.loads(raw)
    expected = {
        "model_id": model_id,
        "backend": "huggingface",
        "repo_id": entry["repo_id"],
        "revision": entry["revision"],
        "mode": "full",
        "trust_remote_code": False,
    }
    for key, value in expected.items():
        if receipt.get(key) != value:
            raise SmokeError(f"{model_id}: receipt field {key} is {receipt.get(key)!r}")
    files = receipt.get("files")
    if not isinstance(files, list) or not files:
        raise SmokeError(f"{model_id}: receipt lists no files")
    if (
        artifact_root(files) != receipt.get("artifact_root_sha256")
        or receipt.get("artifact_root_sha256") != model["artifact_root_sha256"]
    ):
        raise SmokeError(f"{model_id}: artifact root does not recompute to the plan's")
    snapshot = model_root / model_id
    listed = {item["path"] for item in files}
    missing_required = sorted(set(entry["required_files"]) - listed)
    if missing_required:
        raise SmokeError(f"{model_id}: receipt misses required files {missing_required}")
    for item in files:
        local = snapshot / item["path"]
        if not local.is_file() or local.stat().st_size != item["bytes"]:
            raise SmokeError(f"{model_id}: {item['path']} is missing or not {item['bytes']} bytes")
    gguf_bytes = sum(item["bytes"] for item in files if item["path"].endswith(".gguf"))
    return {
        "receipt_sha256": model["receipt_sha256"],
        "artifact_root_sha256": receipt["artifact_root_sha256"],
        "revision": receipt["revision"],
        "files": len(files),
        "total_bytes": receipt.get("total_bytes"),
        "gguf_bytes": gguf_bytes,
        "sizes_match": True,
    }


# --- GPU memory --------------------------------------------------------------------------------


def parse_gpu_rows(text: str) -> dict[str, dict[str, Any]]:
    """Parse ``nvidia-smi --query-gpu=index,uuid,memory.used,memory.total`` CSV (nounits)."""

    rows: dict[str, dict[str, Any]] = {}
    for line in text.strip().splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) != 4:
            raise SmokeError(f"unparseable nvidia-smi row: {line!r}")
        index, uuid, used, total = parts
        rows[uuid] = {"index": int(index), "used_mib": int(used), "total_mib": int(total)}
    return rows


@dataclass
class GpuPoller:
    """Poll nvidia-smi in a thread; keep the per-GPU peak of memory.used since the last reset."""

    query: Callable[[], str]
    interval_s: float = 0.5
    peaks: dict[str, int] = field(default_factory=dict)
    latest: dict[str, dict[str, Any]] = field(default_factory=dict)
    samples: int = 0
    errors: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _stop: threading.Event = field(default_factory=threading.Event)
    _thread: threading.Thread | None = None

    def sample(self) -> None:
        try:
            rows = parse_gpu_rows(self.query())
        except (OSError, subprocess.SubprocessError, SmokeError, ValueError):
            with self._lock:
                self.errors += 1
            return
        with self._lock:
            self.latest = rows
            self.samples += 1
            for uuid, row in rows.items():
                self.peaks[uuid] = max(self.peaks.get(uuid, 0), row["used_mib"])

    def reset(self) -> dict[str, dict[str, Any]]:
        self.sample()
        with self._lock:
            self.peaks = {uuid: row["used_mib"] for uuid, row in self.latest.items()}
            self.samples = 0
            return {uuid: dict(row) for uuid, row in self.latest.items()}

    def snapshot(self) -> tuple[dict[str, int], int]:
        with self._lock:
            return dict(self.peaks), self.samples

    def start(self) -> None:
        def loop() -> None:
            while not self._stop.wait(self.interval_s):
                self.sample()

        self._thread = threading.Thread(target=loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)


def nvidia_smi_query() -> str:
    return subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=index,uuid,memory.used,memory.total",
            "--format=csv,noheader,nounits",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=20,
    ).stdout


# --- Text and log summaries --------------------------------------------------------------------


def text_stats(text: str) -> dict[str, Any]:
    """Text-free heuristics for an operator's coherence read (not a quality measure)."""

    words = re.findall(r"[A-Za-z']+", text)
    grams = [tuple(words[i : i + 4]) for i in range(max(0, len(words) - 3))]
    counts: dict[tuple[str, ...], int] = {}
    for gram in grams:
        counts[gram] = counts.get(gram, 0) + 1
    printable = sum(1 for ch in text if ch.isprintable() or ch in "\n\t")
    return {
        "chars": len(text),
        "words": len(words),
        "distinct_word_ratio": round(len({w.lower() for w in words}) / len(words), 3)
        if words
        else 0.0,
        "printable_ratio": round(printable / len(text), 3) if text else 0.0,
        "ascii_letter_ratio": round(
            sum(ch.isascii() and ch.isalpha() for ch in text) / len(text), 3
        )
        if text
        else 0.0,
        "max_4gram_repeats": max(counts.values()) if counts else 0,
    }


def summarize_server_log(text: str) -> dict[str, Any]:
    offload = OFFLOAD_RE.findall(text)
    buffers = [
        {"buffer": name, "kind": kind, "mib": float(mib)}
        for name, kind, mib in BUFFER_RE.findall(text)
    ]
    return {
        "offloaded_layers": [f"{a}/{b}" for a, b in offload],
        "all_layers_offloaded": bool(offload) and all(a == b for a, b in offload),
        "buffers": buffers,
        "cpu_fallback_lines": len(CPU_FALLBACK_RE.findall(text)),
    }


# --- HTTP --------------------------------------------------------------------------------------


def http_json(url: str, payload: dict[str, Any] | None, timeout_s: float) -> tuple[int, Any]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="GET" if data is None else "POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            return response.status, json.loads(response.read() or b"null")
    except urllib.error.HTTPError as exc:
        body = exc.read()
        try:
            return exc.code, json.loads(body or b"null")
        except json.JSONDecodeError:
            return exc.code, {"raw_sha256_16": sha256_bytes(body)[:16]}


def timings_of(body: Any) -> dict[str, Any]:
    timings = body.get("timings") if isinstance(body, dict) else None
    if not isinstance(timings, dict):
        return {}
    keys = (
        "prompt_n",
        "prompt_ms",
        "prompt_per_second",
        "predicted_n",
        "predicted_ms",
        "predicted_per_second",
        "cache_n",
    )
    return {key: timings[key] for key in keys if key in timings}


# --- One model ---------------------------------------------------------------------------------


def server_argv(
    plan: dict[str, Any], model: dict[str, Any], gguf_path: Path, port: int, threads: int
) -> list[str]:
    return [
        plan["llama_server"],
        "-m",
        str(gguf_path),
        *FIXED_SERVER_ARGS,
        *plan["server_args"],
        *model.get("extra_args", []),
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "-t",
        str(threads),
    ]


def stop_process(process: subprocess.Popen[bytes], grace_s: float = 30.0) -> int | None:
    if process.poll() is None:
        process.send_signal(signal.SIGTERM)
        try:
            process.wait(timeout=grace_s)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)
    return process.returncode


def run_model(
    plan: dict[str, Any],
    model: dict[str, Any],
    entry: dict[str, Any],
    *,
    model_root: Path,
    receipt_root: Path,
    out_dir: Path,
    port: int,
    threads: int,
    poller: GpuPoller,
    deadline: float,
    state: dict[str, Any],
) -> dict[str, Any]:
    model_id = model["model_id"]
    requests = plan["requests"]
    row: dict[str, Any] = {"model_id": model_id, "gguf": model["gguf"], "status": "started"}
    work = out_dir / model_id
    work.mkdir(parents=True, exist_ok=True)
    try:
        row["receipt"] = check_receipt(model, entry, model_root, receipt_root)
    except SmokeError as exc:
        row.update(status="receipt_failed", error=str(exc))
        return row
    need = model["load_timeout_s"] + requests["request_timeout_s"] // 2 + 30
    remaining = deadline - time.monotonic()
    if remaining < need:
        row.update(status="skipped_time", remaining_s=round(remaining, 1), needed_s=need)
        return row

    gguf_path = model_root / model_id / model["gguf"]
    argv = server_argv(plan, model, gguf_path, port, threads)
    row["server_argv"] = [
        arg if arg != str(gguf_path) else f"<snapshot>/{model['gguf']}" for arg in argv
    ]
    baseline = poller.reset()
    row["gpus"] = [
        {"uuid": uuid, "index": item["index"], "total_mib": item["total_mib"]}
        for uuid, item in sorted(baseline.items(), key=lambda kv: kv[1]["index"])
    ]
    row["baseline_mib"] = {uuid: item["used_mib"] for uuid, item in baseline.items()}
    log_path = work / "server.log"
    started = time.monotonic()
    row["started_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with log_path.open("wb") as log:
        process = subprocess.Popen(
            argv, stdout=log, stderr=subprocess.STDOUT, start_new_session=True
        )
        state["process"] = process
        try:
            base = f"http://127.0.0.1:{port}"
            ready = False
            while time.monotonic() - started < model["load_timeout_s"]:
                if process.poll() is not None:
                    break
                try:
                    status, body = http_json(f"{base}/health", None, 5)
                    if status == 200 and isinstance(body, dict) and body.get("status") == "ok":
                        ready = True
                        break
                except (urllib.error.URLError, OSError, json.JSONDecodeError):
                    pass
                time.sleep(0.5)
            row["load_s"] = round(time.monotonic() - started, 2)
            if not ready:
                row["status"] = "load_failed" if process.poll() is not None else "load_timeout"
                raise _NotReady
            timeout = requests["request_timeout_s"]
            common = {
                "temperature": 0.0,
                "top_k": 1,
                "top_p": 1.0,
                "min_p": 0.0,
                "seed": requests["seed"],
                "cache_prompt": False,
            }
            status, body = http_json(
                f"{base}/completion",
                {"prompt": requests["prefill_prompt"], "n_predict": 1, **common},
                timeout,
            )
            row["prefill"] = {"http_status": status, **timings_of(body)}
            status, body = http_json(
                f"{base}/completion",
                {
                    "prompt": requests["completion_prompt"],
                    "n_predict": requests["completion_tokens"],
                    **common,
                },
                timeout,
            )
            content = body.get("content", "") if isinstance(body, dict) else ""
            (work / "completion.txt").write_text(content, encoding="utf-8")
            row["decode"] = {
                "http_status": status,
                **timings_of(body),
                "stop_type": body.get("stop_type") if isinstance(body, dict) else None,
                "output_sha256_16": short_hash(content),
                **text_stats(content),
            }
            status, body = http_json(
                f"{base}/v1/chat/completions",
                {
                    "messages": [{"role": "user", "content": requests["chat_message"]}],
                    "max_tokens": requests["chat_tokens"],
                    **common,
                },
                timeout,
            )
            chat: dict[str, Any] = {"http_status": status}
            if status == 200 and isinstance(body, dict) and body.get("choices"):
                choice = body["choices"][0]
                message = choice.get("message", {})
                text = message.get("content") or ""
                reasoning = message.get("reasoning_content") or ""
                (work / "chat.txt").write_text(
                    json.dumps({"content": text, "reasoning_content": reasoning}), encoding="utf-8"
                )
                chat.update(
                    finish_reason=choice.get("finish_reason"),
                    content_chars=len(text),
                    reasoning_chars=len(reasoning),
                    content_sha256_16=short_hash(text),
                    reasoning_sha256_16=short_hash(reasoning),
                    **timings_of(body),
                )
            else:
                chat["error_sha256_16"] = short_hash(json.dumps(body, sort_keys=True))
            row["chat"] = chat
            ok = (
                row["prefill"].get("http_status") == 200
                and row["decode"].get("http_status") == 200
                and row["decode"].get("predicted_n", 0) > 0
            )
            row["status"] = "ok" if ok else "request_failed"
        except _NotReady:
            pass
        except (urllib.error.URLError, OSError, TimeoutError, ValueError) as exc:
            row.update(status="request_failed", error=f"{type(exc).__name__}: {exc}")
        finally:
            peaks, samples = poller.snapshot()
            row["peak_mib"] = peaks
            row["peak_minus_baseline_mib"] = {
                uuid: peaks.get(uuid, 0) - row["baseline_mib"].get(uuid, 0) for uuid in peaks
            }
            row["vram_samples"] = samples
            row["server_exit_code"] = stop_process(process)
            state["process"] = None
            row["wall_s"] = round(time.monotonic() - started, 2)
    log_text = log_path.read_text(encoding="utf-8", errors="replace")
    row["server_log"] = {"sha256": sha256_file(log_path), **summarize_server_log(log_text)}
    # Let the GPUs drain before the next model's baseline.
    for _ in range(40):
        poller.sample()
        if all(
            row_["used_mib"] <= row["baseline_mib"].get(uuid, 0) + 64
            for uuid, row_ in poller.latest.items()
        ):
            break
        time.sleep(0.5)
    return row


# --- Entry points ------------------------------------------------------------------------------


def run(args: argparse.Namespace) -> int:
    started = time.monotonic()
    deadline = started + args.allocation_minutes * 60 - args.reserve_s
    registry = load_registry(DEFAULT_REGISTRY)
    plan = load_plan(args.plan, args.expected_plan_sha256, registry)
    out_dir = args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    results_path = out_dir / "results.jsonl"
    threads = (
        len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else os.cpu_count() or 8
    )
    poller = GpuPoller(nvidia_smi_query)
    poller.sample()
    visible = sorted(poller.latest)
    refused = sorted(set(visible) & set(plan.get("refuse_gpu_uuids", [])))
    if not visible or refused:
        # A GPU this plan must never use (another project's) is in the allocation: stop before any
        # model loads.
        (out_dir / "summary.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "experiment": plan["experiment"],
                    "refused": True,
                    "visible_gpus": visible,
                    "refused_gpus": refused,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )
        print(f"refusing to run: visible GPUs {visible}, refused {refused}", file=sys.stderr)
        return 3
    poller.start()
    state: dict[str, Any] = {"process": None, "stopping": False}

    def on_signal(signum: int, _frame: Any) -> None:
        state["stopping"] = True
        process = state.get("process")
        if process is not None:
            stop_process(process, grace_s=10)
        raise SystemExit(128 + signum)

    for sig in (signal.SIGTERM, signal.SIGUSR1, signal.SIGINT):
        signal.signal(sig, on_signal)
    rows: list[dict[str, Any]] = []
    try:
        for index, model in enumerate(plan["models"]):
            row = run_model(
                plan,
                model,
                registry["models"][model["model_id"]],
                model_root=args.model_root,
                receipt_root=args.receipt_root,
                out_dir=out_dir,
                port=args.base_port + index,
                threads=threads,
                poller=poller,
                deadline=deadline,
                state=state,
            )
            rows.append(row)
            with results_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, sort_keys=True) + "\n")
            print(
                json.dumps({k: row.get(k) for k in ("model_id", "status", "load_s", "wall_s")}),
                flush=True,
            )
    finally:
        poller.stop()
        summary = {
            "schema_version": 1,
            "experiment": plan["experiment"],
            "plan_sha256": sha256_file(args.plan),
            "models": len(plan["models"]),
            "statuses": {row["model_id"]: row["status"] for row in rows},
            "elapsed_s": round(time.monotonic() - started, 1),
            "threads": threads,
            "poller_errors": poller.errors,
            "interrupted": state["stopping"],
        }
        (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return 0 if rows and all(row["status"] == "ok" for row in rows) else 1


def check_plan(args: argparse.Namespace) -> int:
    registry = load_registry(DEFAULT_REGISTRY)
    plan = load_plan(args.plan, args.expected_plan_sha256, registry)
    print(
        json.dumps(
            {
                "status": "PASS",
                "experiment": plan["experiment"],
                "models": [m["model_id"] for m in plan["models"]],
                "plan_sha256": sha256_file(args.plan),
            },
            sort_keys=True,
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("check-plan", "run"):
        p = sub.add_parser(name)
        p.add_argument("--plan", type=Path, required=True)
        p.add_argument("--expected-plan-sha256")
    run_parser = sub.choices["run"]
    run_parser.add_argument("--model-root", type=Path, default=Path("/model-cache/cotcodec-models"))
    run_parser.add_argument(
        "--receipt-root", type=Path, default=Path("/model-cache/cotcodec-receipts")
    )
    run_parser.add_argument("--output-dir", type=Path, required=True)
    run_parser.add_argument("--allocation-minutes", type=float, required=True)
    run_parser.add_argument("--reserve-s", type=float, default=45.0)
    run_parser.add_argument("--base-port", type=int, default=18931)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.expected_plan_sha256 is not None and not SHA_RE.fullmatch(args.expected_plan_sha256):
        raise SmokeError("--expected-plan-sha256 must be 64 lowercase hex characters")
    if args.command == "check-plan":
        return check_plan(args)
    return run(args)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SmokeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)
