#!/usr/bin/env python3
"""AM1 Step 0 (EXPLORATORY): batch-invariant A/A replay, its throughput cost, and the demo of
the exact 2^8-subset outcome table, with the Qwen3-8B reader in vLLM 0.31.0.

Config: experiments/am1/memcredit-step0-v1.yaml. Runs inside the digest-pinned cotcodec-vllm
cu129 overlay on the docker-research lane; the pools come from scripts/memcredit_prepare.py as
the hash-bound study artifact.

Subcommands:

* ``plan``: the resolved sessions, passes and request counts (CPU).
* ``selftest --evidence A``: CPU only, no engine. Renders every request with the Qwen3-8B chat
  template (tokenizer files only), checks lengths, the output parsers, the pass sets, and runs the
  analysis on a synthetic run; reports the SHA-256 of the cited vLLM source files in the image.
* ``run --seeds 42 43 44 --output-dir D --allocation-minutes M --evidence A
  --expected-evidence-sha256 S``: the job. Verifies the reader snapshot, then runs one ``worker``
  subprocess per engine session in config order (each one a fresh engine; batch-invariant
  sessions get ``VLLM_BATCH_INVARIANT=1``), samples nvidia-smi throughout, and ends with
  ``analyze``.
* ``worker --session X ...``: one vLLM engine; runs the session's passes and saves each pass.
* ``analyze --run-dir D --output-dir O --evidence A``: CPU. Identity rates with exact intervals,
  throughput and the cost per question, the demo tables' set-function analysis.
"""

from __future__ import annotations

import argparse
import contextlib
import gzip
import json
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness import g2_pilot as lane  # noqa: E402  (deadline, marker, write_json, verify_model)
from harness import memcredit as mc  # noqa: E402

MODEL_ROOT = lane.MODEL_ROOT
#: Cache and runtime directories, one tree per mode (batch-invariant, default), under the run dir.
CACHE_DIRS = {
    "XDG_CACHE_HOME": "xdg-cache",
    "VLLM_CACHE_ROOT": "vllm",
    "VLLM_CONFIG_ROOT": "vllm-config",
    "VLLM_RPC_BASE_PATH": "rpc",
    "TRITON_CACHE_DIR": "triton",
    "TORCHINDUCTOR_CACHE_DIR": "inductor",
    "CUDA_CACHE_PATH": "cuda",
    "FLASHINFER_WORKSPACE_BASE": "flashinfer",
    "TMPDIR": "tmp",
}
FIXED_ENV = {
    "VLLM_NO_USAGE_STATS": "1",
    "DO_NOT_TRACK": "1",
    "VLLM_DO_NOT_TRACK": "1",
    "VLLM_HOST_IP": "127.0.0.1",
    "VLLM_ENABLE_CUDA_COMPATIBILITY": "0",
    "HF_HUB_OFFLINE": "1",
    "TRANSFORMERS_OFFLINE": "1",
    "PYTHONUNBUFFERED": "1",
}
END_OF_TURN = "<|im_end|>"
SMOKE_FAILED_EXIT = 4
#: The vLLM v0.31.0 files the README cites for how batch invariance is enabled.
VLLM_CITED_FILES = (
    "envs.py",
    "model_executor/determinism/batch_invariant.py",
    "model_executor/determinism/batch_invariant_configs.py",
    "v1/attention/backends/flash_attn.py",
    "model_executor/layers/attention/attention.py",
    "config/vllm.py",
    "v1/worker/gpu_worker.py",
    "sampling_params.py",
    "engine/arg_utils.py",
)
#: Engine log lines kept by the analysis (substring match, case-insensitive).
LOG_MARKERS = (
    "batch_invariant",
    "batch invariance",
    "breakable",
    "cascade attention",
    "flashattention version",
    "attention backend",
    "using flash",
    "cudagraph",
    "cuda graph",
    "torch.compile",
    "compilation",
    "prefix caching",
    "kv cache",
    "maximum concurrency",
)


# --------------------------------------------------------------------------- plan


def load_artifact(path: Path, expected_sha256: str | None) -> dict[str, Any]:
    raw = path.read_bytes()
    if expected_sha256 is not None and mc.sha256_bytes(raw) != expected_sha256:
        raise mc.MemcreditError("the study artifact differs from the expected SHA-256")
    artifact = json.loads(raw)
    if artifact.get("experiment_id") != mc.EXPERIMENT_ID:
        raise mc.MemcreditError("the study artifact belongs to another experiment")
    return artifact


def session_by_id(config: dict[str, Any], session_id: str) -> dict[str, Any]:
    for session in config["sessions"]:
        if session["id"] == session_id:
            return session
    raise mc.MemcreditError(f"unknown session {session_id}")


def requests_for(config: dict[str, Any], artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return mc.request_table(artifact, config["pools"]["arms"])


def pass_indices(config: dict[str, Any], n_requests: int, item: dict[str, Any]) -> list[int]:
    chosen = mc.request_set(n_requests, config["request_sets"][item["set"]])
    return mc.pass_order(chosen, item.get("order", "canonical"), int(config["shuffle_seed"]))


def engine_kwargs(config: dict[str, Any], session: dict[str, Any]) -> dict[str, Any]:
    engine = config["engine"]
    model_dir = MODEL_ROOT / config["model"]["id"]
    return {
        "model": str(model_dir),
        "tokenizer": str(model_dir),
        "trust_remote_code": False,
        "dtype": engine["dtype"],
        "seed": config["seeds"][0],
        "max_model_len": engine["max_model_len"],
        "gpu_memory_utilization": engine["gpu_memory_utilization"],
        "max_num_seqs": session["max_num_seqs"],
        "max_num_batched_tokens": session["max_num_batched_tokens"],
        "enable_prefix_caching": session["prefix_caching"],
        "logprobs_mode": engine["logprobs_mode"],
    }


def sampling_kwargs(config: dict[str, Any], name: str) -> dict[str, Any]:
    spec = dict(config["sampling"][name])
    kwargs = {
        "n": 1,
        "temperature": spec["temperature"],
        "max_tokens": spec["max_tokens"],
        "logprobs": spec["logprobs"],
    }
    for key in ("top_p", "top_k", "seed"):
        if key in spec:
            kwargs[key] = spec[key]
    return kwargs


def session_env(base: dict[str, str], out: Path, batch_invariant: bool) -> dict[str, str]:
    env = dict(base)
    mode = "bi" if batch_invariant else "default"
    for key, sub in CACHE_DIRS.items():
        path = out / "cache" / mode / sub
        path.mkdir(parents=True, exist_ok=True)
        env[key] = str(path)
    env.update(FIXED_ENV)
    env.pop("VLLM_BATCH_INVARIANT", None)
    if batch_invariant:
        env["VLLM_BATCH_INVARIANT"] = "1"
    return env


def build_plan(config: dict[str, Any], artifact: dict[str, Any] | None = None) -> dict[str, Any]:
    if artifact is None:
        k = int(config["pools"]["size"])
        n = sum(config["selection"]["types"].values()) * len(config["pools"]["arms"]) * (1 << k)
    else:
        n = len(requests_for(config, artifact))
    sessions = []
    for session in config["sessions"]:
        passes = [
            {
                "name": item["name"],
                "requests": len(pass_indices(config, n, item)),
                "sampling": item["sampling"],
                "order": item.get("order", "canonical"),
                "max_inflight": item.get("max_inflight"),
                "reset_prefix_cache": item.get("reset_prefix_cache", True),
                "max_s": item["max_s"],
            }
            for item in session["passes"]
        ]
        sessions.append(
            {
                "id": session["id"],
                "batch_invariant": session["batch_invariant"],
                "engine_kwargs": engine_kwargs(config, session),
                "passes": passes,
                "requests": sum(p["requests"] for p in passes),
            }
        )
    return {
        "experiment_id": config["experiment_id"],
        "claim_level": config["claim_level"],
        "seeds": config["seeds"],
        "requests_in_table": n,
        "sessions": sessions,
        "sampling": config["sampling"],
    }


# --------------------------------------------------------------------------- prompts and parsers


def render_prompt_ids(tokenizer: Any, message: str, enable_thinking: bool) -> list[int]:
    text = tokenizer.apply_chat_template(
        [{"role": "user", "content": message}],
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=enable_thinking,
    )
    return [int(i) for i in tokenizer(text, add_special_tokens=False)["input_ids"]]


def prompt_digest(prompt_ids: list[list[int]]) -> str:
    return mc.sha256_bytes(json.dumps(prompt_ids, separators=(",", ":")).encode())


def delta_logprobs(token_ids: list[int], logprobs: Any) -> tuple[list[float], int]:
    """Sampled-token log-probs of a streamed delta; NaN (counted) where vLLM gave none."""

    if not token_ids:
        return [], 0
    if logprobs is None or len(logprobs) != len(token_ids):
        return [float("nan")] * len(token_ids), len(token_ids)
    values, missing = [], 0
    for position, token in enumerate(token_ids):
        entry = logprobs[position].get(token) if logprobs[position] is not None else None
        if entry is None:
            values.append(float("nan"))
            missing += 1
        else:
            values.append(float(entry.logprob))
    return values, missing


class StopFlag:
    def __init__(self) -> None:
        self.event = threading.Event()
        self.reason: str | None = None

    def handler(self, signum: int, _frame: Any) -> None:
        self.reason = signal.Signals(signum).name
        self.event.set()


def new_state() -> dict[str, Any]:
    return {
        "token_ids": [],
        "logp": [],
        "text": [],
        "finish_reason": None,
        "finished": False,
        "added": False,
        "missing_logprobs": 0,
        "num_cached_tokens": None,
    }


def stream_requests(
    engine: Any,
    items: list[tuple[str, Any, Any]],
    stop_at: float,
    flag: StopFlag,
    max_inflight: int | None = None,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Add requests under our own ids (LLMEngine.add_request) with DELTA output, keep at most
    ``max_inflight`` unfinished (all at once when None), step until done, the stop time or a
    signal, then abort what is left. ``engine`` is ``llm.llm_engine``."""

    from vllm.sampling_params import RequestOutputKind

    state = {ours: new_state() for ours, _, _ in items}
    limit = len(items) if not max_inflight else int(max_inflight)
    info: dict[str, Any] = {"aborted": 0, "not_started": 0, "steps": 0, "stopped_by": None,
                            "unmatched": 0, "max_inflight": max_inflight}  # fmt: skip
    pointer = 0
    inflight = 0

    def refill() -> None:
        nonlocal pointer, inflight
        while pointer < len(items) and inflight < limit:
            ours, prompt, params = items[pointer]
            params.output_kind = RequestOutputKind.DELTA
            engine.add_request(ours, prompt, params)
            state[ours]["added"] = True
            pointer += 1
            inflight += 1

    started = time.time()
    refill()
    info["add_s"] = round(time.time() - started, 3)
    while pointer < len(items) or engine.has_unfinished_requests():
        if time.time() >= stop_at or flag.event.is_set():
            info["stopped_by"] = flag.reason or "time budget"
            left = [o for o, st in state.items() if st["added"] and not st["finished"]]
            info["aborted"] = len(left)
            info["not_started"] = len(items) - pointer
            try:
                engine.abort_request(left, internal=False)
            except Exception as exc:  # noqa: BLE001 - recorded; the pass is saved as partial
                info["abort_error"] = repr(exc)
            break
        for output in engine.step():
            st = state.get(str(output.request_id))
            if st is None:
                info["unmatched"] += 1
                continue
            cached = getattr(output, "num_cached_tokens", None)
            if cached is not None:
                st["num_cached_tokens"] = max(int(cached), st["num_cached_tokens"] or 0)
            if output.outputs:
                completion = output.outputs[0]
                ids = [int(t) for t in completion.token_ids]
                values, missing = delta_logprobs(ids, completion.logprobs)
                st["token_ids"].extend(ids)
                st["logp"].extend(values)
                st["missing_logprobs"] += missing
                st["text"].append(completion.text or "")
                if output.finished:
                    st["finish_reason"] = completion.finish_reason
            if output.finished and not st["finished"]:
                st["finished"] = True
                inflight -= 1
        refill()
        info["steps"] += 1
    info["wall_s"] = round(time.time() - started, 3)
    info["finished"] = sum(1 for st in state.values() if st["finished"])
    return state, info


def save_pass(
    out: Path,
    name: str,
    indices: list[int],
    ids: list[str],
    state: dict[str, dict[str, Any]],
    prompt_lens: list[int],
    record: dict[str, Any],
) -> dict[str, Any]:
    import numpy as np

    offsets = [0]
    tokens: list[int] = []
    logps: list[float] = []
    for ours in ids:
        tokens.extend(state[ours]["token_ids"])
        logps.extend(state[ours]["logp"])
        offsets.append(len(tokens))
    np.savez_compressed(
        out / f"{name}.npz",
        request_index=np.asarray(indices, dtype=np.int32),
        offsets=np.asarray(offsets, dtype=np.int64),
        token_ids=np.asarray(tokens, dtype=np.int32),
        logprobs=np.asarray(logps, dtype=np.float32),
        num_cached=np.asarray(
            [-1 if state[o]["num_cached_tokens"] is None else state[o]["num_cached_tokens"]
             for o in ids], dtype=np.int32),
        prompt_len=np.asarray([prompt_lens[i] for i in indices], dtype=np.int32),
        finished=np.asarray([state[o]["finished"] for o in ids], dtype=bool),
    )  # fmt: skip
    with gzip.open(out / f"{name}.texts.jsonl.gz", "wt", encoding="utf-8") as handle:
        for index, ours in zip(indices, ids, strict=True):
            handle.write(json.dumps({"request_index": index, "text": "".join(state[ours]["text"])}))
            handle.write("\n")
    record = dict(record)
    record["finish_reasons"] = [
        state[o]["finish_reason"] if state[o]["finished"] else "not-finished" for o in ids
    ]
    record["missing_logprobs"] = sum(state[o]["missing_logprobs"] for o in ids)
    record["output_tokens"] = len(tokens)
    record["prompt_tokens"] = sum(prompt_lens[i] for i in indices)
    record["cached_tokens"] = sum(max(0, state[o]["num_cached_tokens"] or 0) for o in ids)
    lane.write_json(out / f"{name}.json", record)
    return record


def smoke_ok(record: dict[str, Any], state: dict[str, dict[str, Any]]) -> tuple[bool, str]:
    if record["info"]["finished"] != record["requests"]:
        return False, "not every smoke request finished"
    if record["info"]["unmatched"]:
        return False, "outputs not matched to request ids"
    if record["missing_logprobs"]:
        return False, "missing sampled-token log-probs"
    if any(not st["token_ids"] for st in state.values()):
        return False, "an empty reply"
    if any(st["finish_reason"] not in ("stop", "length") for st in state.values()):
        return False, "unexpected finish reason"
    return True, "ok"


# --------------------------------------------------------------------------- worker


def worker_main(args: argparse.Namespace) -> int:
    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams
    from vllm.inputs import TokensPrompt

    config = mc.load_config()
    session = session_by_id(config, args.session)
    artifact = load_artifact(Path(args.evidence), args.expected_evidence_sha256)
    requests = requests_for(config, artifact)
    out = Path(args.output_dir) / "sessions" / session["id"]
    out.mkdir(parents=True, exist_ok=True)
    flag = StopFlag()
    signal.signal(signal.SIGTERM, flag.handler)
    signal.signal(signal.SIGUSR1, flag.handler)
    log_path = out / "worker-progress.jsonl"

    def log(event: str, **fields: Any) -> None:
        record = {"utc": lane.utc_now(), "event": event, "session": session["id"], **fields}
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        print(json.dumps(record, sort_keys=True), flush=True)

    import vllm.envs as vllm_envs

    model_dir = MODEL_ROOT / config["model"]["id"]
    tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
    enable_thinking = bool(config["prompt"]["enable_thinking"])
    prompt_ids = [
        render_prompt_ids(
            tokenizer, mc.request_message(artifact, r, config["prompt"]), enable_thinking
        )
        for r in requests
    ]
    prompt_lens = [len(p) for p in prompt_ids]
    end_of_turn = tokenizer.convert_tokens_to_ids(END_OF_TURN)
    kwargs = engine_kwargs(config, session)
    log(
        "engine-start",
        engine_kwargs=kwargs,
        env_batch_invariant=os.environ.get("VLLM_BATCH_INVARIANT"),
        vllm_envs_batch_invariant=bool(vllm_envs.VLLM_BATCH_INVARIANT),
        env_breakable_cudagraph=os.environ.get("VLLM_USE_BREAKABLE_CUDAGRAPH"),
        prompt_ids_sha256=prompt_digest(prompt_ids),
        requests=len(requests),
        prompt_len_min=min(prompt_lens),
        prompt_len_max=max(prompt_lens),
        prompt_tokens_total=sum(prompt_lens),
        end_of_turn_id=end_of_turn,
    )
    if bool(vllm_envs.VLLM_BATCH_INVARIANT) != bool(session["batch_invariant"]):
        log("mode-mismatch")
        lane.write_json(out / "done.json", {"exit": 2, "utc": lane.utc_now()})
        sys.stdout.flush()
        os._exit(2)
    t0 = time.time()
    llm = LLM(**kwargs)
    init_s = round(time.time() - t0, 1)
    log("engine-ready", init_s=init_s)
    engine = llm.llm_engine
    passes: list[dict[str, Any]] = []
    code = 0
    for item in session["passes"]:
        name = item["name"]
        remaining = args.deadline - time.time()
        if flag.event.is_set() or remaining < 30:
            passes.append({"name": name, "status": "skipped",
                           "reason": flag.reason or f"remaining {remaining:.0f} s"})  # fmt: skip
            code = 3
            continue
        indices = pass_indices(config, len(requests), item)
        reset = None
        if item.get("reset_prefix_cache", True) and session["prefix_caching"]:
            reset = bool(llm.reset_prefix_cache())
        base = sampling_kwargs(config, item["sampling"])
        ids = [f"{session['id']}/{name}/{i}" for i in indices]
        items = [
            (ours, TokensPrompt(prompt_token_ids=prompt_ids[i]),
             SamplingParams(**base, stop_token_ids=[end_of_turn]))
            for ours, i in zip(ids, indices, strict=True)
        ]  # fmt: skip
        log("pass-start", name=name, requests=len(items), prefix_cache_reset=reset)
        stop_at = min(args.deadline, time.time() + float(item["max_s"]))
        state, info = stream_requests(engine, items, stop_at, flag, item.get("max_inflight"))
        record = {
            "session": session["id"],
            "name": name,
            "batch_invariant": session["batch_invariant"],
            "sampling": item["sampling"],
            "sampling_kwargs": base,
            "order": item.get("order", "canonical"),
            "set": item["set"],
            "requests": len(items),
            "prefix_cache_reset": reset,
            "info": info,
            "status": "complete" if info["finished"] == len(items) else "partial",
        }
        record = save_pass(out, name, indices, ids, state, prompt_lens, record)
        passes.append({k: record[k] for k in ("name", "status", "requests")} | {"info": info})
        log("pass-done", name=name, status=record["status"], **info)
        if record["status"] != "complete":
            code = 3
        if item.get("smoke"):
            ok, why = smoke_ok(record, state)
            log("smoke-check", ok=ok, reason=why)
            if not ok:
                code = SMOKE_FAILED_EXIT
                break
    lane.write_json(
        out / "session.json",
        {"session": session, "engine_kwargs": kwargs, "init_s": init_s, "passes": passes,
         "prompt_ids_sha256": prompt_digest(prompt_ids), "exit": code},
    )  # fmt: skip
    lane.write_json(out / "done.json", {"exit": code, "utc": lane.utc_now()})
    # vLLM's exit can hang (G2 job 1337): bounded engine shutdown, then no interpreter teardown.
    closer = threading.Thread(target=lambda: engine.engine_core.shutdown(), daemon=True)
    closer.start()
    closer.join(timeout=15)
    sys.stdout.flush()
    os._exit(code)


# --------------------------------------------------------------------------- driver


def gpu_memory_used_mib() -> list[int]:
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=30, check=False,
        )  # fmt: skip
        return [int(x) for x in result.stdout.split()]
    except (OSError, ValueError, subprocess.SubprocessError):
        return []


def start_gpu_sampler(out: Path) -> subprocess.Popen[bytes] | None:
    query = ("timestamp,index,power.draw,clocks.sm,clocks.mem,utilization.gpu,memory.used,"
             "temperature.gpu")  # fmt: skip
    try:
        handle = (out / "gpu-samples.csv").open("wb")
        return subprocess.Popen(
            ["nvidia-smi", f"--query-gpu={query}", "--format=csv,nounits", "-lms", "1000"],
            stdout=handle, stderr=subprocess.STDOUT, start_new_session=True,
        )  # fmt: skip
    except OSError:
        return None


def record_environment(out: Path) -> None:
    info: dict[str, Any] = {"utc": lane.utc_now(), "python": sys.version}
    try:
        import torch
        import transformers
        import vllm

        info.update(vllm=vllm.__version__, torch=torch.__version__, torch_cuda=torch.version.cuda,
                    transformers=transformers.__version__)  # fmt: skip
        info["vllm_cited_files_sha256"] = vllm_file_digests(Path(vllm.__file__).parent)
    except Exception as exc:  # noqa: BLE001 - recorded
        info["import_error"] = repr(exc)
    try:
        info["nvidia_smi"] = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,uuid,driver_version,memory.total,clocks.max.sm,"
             "power.limit", "--format=csv"],
            capture_output=True, text=True, timeout=30, check=False,
        ).stdout  # fmt: skip
    except (OSError, subprocess.SubprocessError) as exc:
        info["nvidia_smi_error"] = repr(exc)
    keys = ("COTCODEC_GIT_SHA", "COTCODEC_SOURCE_SHA256", "COTCODEC_MODEL_ID",
            "CUDA_VISIBLE_DEVICES")  # fmt: skip
    info["lane"] = {k: os.environ.get(k) for k in keys}
    lane.write_json(out / "environment.json", info)


def vllm_file_digests(root: Path) -> dict[str, str | None]:
    out: dict[str, str | None] = {}
    for rel in VLLM_CITED_FILES:
        path = root / rel
        out[rel] = lane.sha256_file(path) if path.is_file() else None
    return out


def run_main(args: argparse.Namespace) -> int:
    config = mc.load_config()
    if list(args.seeds) != config["seeds"]:
        raise mc.MemcreditError("--seeds must equal the config's declared seeds")
    artifact = load_artifact(Path(args.evidence), args.expected_evidence_sha256)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    stop_at, source = lane.deadline(args.allocation_minutes)
    summary: dict[str, Any] = {
        "experiment_id": config["experiment_id"],
        "claim_level": "exploratory",
        "started_at": lane.utc_now(),
        "allocation_minutes": args.allocation_minutes,
        "deadline_source": source,
        "deadline_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(stop_at)),
        "evidence_sha256": args.expected_evidence_sha256,
        "plan": build_plan(config, artifact),
        "sessions": {},
    }
    lane.write_json(out / "summary.json", summary)
    record_environment(out)
    state: dict[str, Any] = {"child": None, "signal": None, "signal_at": None}

    def on_signal(signum: int, _frame: Any) -> None:
        state["signal"] = signal.Signals(signum).name
        state["signal_at"] = time.time()
        child = state["child"]
        if child is not None and child.poll() is None:
            # The worker only (not its group): it stops its pass, saves it and shuts its engine
            # down; the group is killed after a grace period if it has not exited.
            with contextlib.suppress(ProcessLookupError):
                os.kill(child.pid, signal.SIGTERM)

    signal.signal(signal.SIGUSR1, on_signal)
    signal.signal(signal.SIGTERM, on_signal)
    started = time.time()
    try:
        summary["model_verification"] = lane.verify_model(
            config["model"]["id"], config["model"]["receipt_root"]
        )
    except Exception as exc:  # noqa: BLE001 - recorded; nothing runs on an unverified model
        summary["model_verification"] = {"error": repr(exc)}
        lane.write_json(out / "summary.json", summary)
        return 2
    summary["model_verification_s"] = round(time.time() - started, 1)
    sampler = start_gpu_sampler(out)
    aborted = False
    for session in config["sessions"]:
        record: dict[str, Any] = {"batch_invariant": session["batch_invariant"]}
        summary["sessions"][session["id"]] = record
        remaining = stop_at - time.time()
        if aborted or state["signal"] or remaining < float(session["min_start_s"]):
            record["status"] = "skipped"
            short = f"remaining {remaining:.0f} s < {session['min_start_s']} s"
            record["reason"] = "smoke failed earlier" if aborted else state["signal"] or short
            continue
        argv = [sys.executable, str(Path(__file__).resolve()), "worker", "--session",
                session["id"], "--output-dir", str(out), "--deadline", f"{stop_at:.3f}",
                "--evidence", args.evidence, "--expected-evidence-sha256",
                args.expected_evidence_sha256]  # fmt: skip
        env = session_env(dict(os.environ), out, bool(session["batch_invariant"]))
        record["argv"] = argv
        record["started_at"] = lane.utc_now()
        t0 = time.time()
        log_file = out / f"worker-{session['id']}.log"
        with log_file.open("w", encoding="utf-8") as handle:
            child = subprocess.Popen(argv, env=env, stdout=handle, stderr=subprocess.STDOUT,
                                     start_new_session=True)  # fmt: skip
            state["child"] = child
            done = out / "sessions" / session["id"] / "done.json"
            done_seen: float | None = None
            while child.poll() is None:
                now = time.time()
                if done_seen is None and done.is_file():
                    done_seen = now
                hung = done_seen is not None and now - done_seen > 25
                late = now > stop_at + 90
                after_signal = state["signal_at"] is not None and now - state["signal_at"] > 40
                if hung or late or after_signal:
                    record["killed"] = "hung after done" if hung else "late" if late else "signal"
                    with contextlib.suppress(ProcessLookupError):
                        os.killpg(child.pid, signal.SIGKILL)
                    child.wait(timeout=30)
                    break
                time.sleep(1.0)
            state["child"] = None
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.killpg(child.pid, signal.SIGKILL)
        record["exit"] = child.returncode
        record["wall_s"] = round(time.time() - t0, 1)
        saved = json.loads(done.read_text()) if done.is_file() else None
        record["worker_done"] = saved
        outcome = {0: "complete", 3: "partial", SMOKE_FAILED_EXIT: "smoke-failed"}
        record["status"] = "failed" if saved is None else outcome.get(saved["exit"], "failed")
        if record["status"] in ("smoke-failed", "failed"):
            aborted = True
        release_until = time.time() + 120
        while time.time() < release_until:
            used = gpu_memory_used_mib()
            if not used or max(used) < 1024:
                break
            time.sleep(2.0)
        record["gpu_memory_after_mib"] = gpu_memory_used_mib()
        lane.write_json(out / "summary.json", summary)
    if sampler is not None:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(sampler.pid, signal.SIGTERM)
    try:
        summary["analysis"] = analyze_run(out, config, artifact, out / "analysis")["headline"]
    except Exception as exc:  # noqa: BLE001 - recorded; the raw passes are kept
        summary["analysis_error"] = repr(exc)
    summary["finished_at"] = lane.utc_now()
    summary["signal"] = state["signal"]
    lane.write_json(out / "summary.json", summary)
    if state["signal"]:
        lane.write_checkpoint_marker(
            "SIGUSR1" if state["signal"] == "SIGUSR1" else "SIGTERM",
            "memcredit step 0: every finished pass saved; no resume (a rerun is a new job)",
        )
    statuses = [s.get("status") for s in summary["sessions"].values()]
    return 0 if all(s == "complete" for s in statuses) else 3


# --------------------------------------------------------------------------- analysis


def load_passes(run_dir: Path) -> dict[tuple[str, str], dict[str, Any]]:
    """Every saved pass: request index -> (token tuple, float32 log-prob bits, finish reason)."""

    import numpy as np

    passes: dict[tuple[str, str], dict[str, Any]] = {}
    root = run_dir / "sessions"
    if not root.is_dir():
        return passes
    for session_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        for meta_path in sorted(session_dir.glob("*.json")):
            if meta_path.name in ("session.json", "done.json"):
                continue
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            data = np.load(session_dir / f"{meta['name']}.npz")
            offsets = data["offsets"]
            tokens = data["token_ids"]
            logps = data["logprobs"]
            rows: dict[int, dict[str, Any]] = {}
            texts: dict[int, str] = {}
            text_path = session_dir / f"{meta['name']}.texts.jsonl.gz"
            if text_path.is_file():
                with gzip.open(text_path, "rt", encoding="utf-8") as handle:
                    for line in handle:
                        row = json.loads(line)
                        texts[int(row["request_index"])] = row["text"]
            for j, index in enumerate(data["request_index"].tolist()):
                a, b = int(offsets[j]), int(offsets[j + 1])
                rows[int(index)] = {
                    "tokens": tuple(int(t) for t in tokens[a:b]),
                    "bits": logps[a:b].astype("<f4").tobytes(),
                    "finish": meta["finish_reasons"][j],
                    "cached": int(data["num_cached"][j]),
                    "text": texts.get(int(index)),
                }
            passes[(meta["session"], meta["name"])] = {"meta": meta, "rows": rows}
    return passes


def compare(
    ref: dict[str, Any], other: dict[str, Any], cluster_of: dict[int, str]
) -> dict[str, Any]:
    done = ("stop", "length")
    common = sorted(
        i for i in ref["rows"]
        if i in other["rows"] and ref["rows"][i]["finish"] in done
        and other["rows"][i]["finish"] in done
    )  # fmt: skip
    same_tokens = same_bits = 0
    differing = []
    clusters: dict[str, list[bool]] = {}
    for i in common:
        a, b = ref["rows"][i], other["rows"][i]
        tok = a["tokens"] == b["tokens"] and a["finish"] == b["finish"]
        bits = tok and a["bits"] == b["bits"]
        same_tokens += tok
        same_bits += bits
        clusters.setdefault(cluster_of.get(i, "?"), []).append(tok)
        if not tok:
            differing.append(
                {"request_index": i, "first_diff": mc.first_difference(a["tokens"], b["tokens"]),
                 "ref_len": len(a["tokens"]), "other_len": len(b["tokens"]),
                 "text_differs": a["text"] != b["text"]}
            )  # fmt: skip
    n = len(common)
    result: dict[str, Any] = {"n_common": n, "identical_tokens": same_tokens,
                              "identical_tokens_and_logprob_bits": same_bits}  # fmt: skip
    if n:
        result["rate_tokens"] = same_tokens / n
        result["ci95_tokens"] = list(mc.clopper_pearson(same_tokens, n))
        result["rate_bits"] = same_bits / n
        result["ci95_bits"] = list(mc.clopper_pearson(same_bits, n))
    result["clusters"] = len(clusters)
    result["clusters_all_identical"] = sum(all(v) for v in clusters.values())
    result["differing_examples"] = differing[:20]
    result["differing_total"] = len(differing)
    result["text_differs_total"] = sum(d["text_differs"] for d in differing)
    return result


def identity_tables(
    passes: dict[tuple[str, str], dict[str, Any]],
    config: dict[str, Any],
    cluster_of: dict[int, str],
) -> list[dict[str, Any]]:
    modes = {s["id"]: ("batch_invariant" if s["batch_invariant"] else "default")
             for s in config["sessions"]}  # fmt: skip
    refs = config["analysis"]["references"]
    ref_pass = config["analysis"]["reference_pass"]
    rows = []
    for mode, ref_session in refs.items():
        for sampling, pass_name in ref_pass.items():
            key = (ref_session, pass_name)
            if key not in passes:
                continue
            for other_key, other in sorted(passes.items()):
                if other_key == key or modes.get(other_key[0]) != mode:
                    continue
                if other["meta"]["sampling"] != sampling:
                    continue
                head = {"mode": mode, "sampling": sampling, "ref": list(key),
                        "other": list(other_key)}  # fmt: skip
                rows.append(head | compare(passes[key], other, cluster_of))
    for sampling, pass_name in ref_pass.items():
        a = (refs["batch_invariant"], pass_name)
        b = (refs["default"], pass_name)
        if a in passes and b in passes:
            rows.append({"mode": "cross-mode", "sampling": sampling, "ref": list(a),
                         "other": list(b)} | compare(passes[a], passes[b], cluster_of))  # fmt: skip
    return rows


def throughput_tables(
    passes: dict[tuple[str, str], dict[str, Any]], config: dict[str, Any], run_dir: Path
) -> dict[str, Any]:
    per_pass = []
    for (session, name), item in sorted(passes.items()):
        meta = item["meta"]
        wall = float(meta["info"]["wall_s"])
        finished = int(meta["info"]["finished"])
        computed = meta["prompt_tokens"] - meta["cached_tokens"]
        per_pass.append({
            "session": session, "pass": name, "batch_invariant": meta["batch_invariant"],
            "status": meta["status"], "requests": meta["requests"], "finished": finished,
            "wall_s": wall, "requests_per_s": finished / wall if wall else None,
            "prompt_tokens": meta["prompt_tokens"], "cached_tokens": meta["cached_tokens"],
            "computed_prompt_tokens": computed, "output_tokens": meta["output_tokens"],
            "computed_prompt_tokens_per_s": computed / wall if wall else None,
            "output_tokens_per_s": meta["output_tokens"] / wall if wall else None,
        })  # fmt: skip
    index = {(r["session"], r["pass"]): r for r in per_pass}
    pairs = []
    for bi, default in config["analysis"]["throughput_pairs"]:
        for (session, name), row in sorted(index.items()):
            if session != bi or name == "smoke" or (default, name) not in index:
                continue
            other = index[(default, name)]
            if row["status"] != "complete" or other["status"] != "complete":
                continue
            pairs.append({"bi": bi, "default": default, "pass": name,
                          "wall_ratio_bi_over_default": row["wall_s"] / other["wall_s"],
                          "bi_wall_s": row["wall_s"], "default_wall_s": other["wall_s"],
                          "bi_requests_per_s": row["requests_per_s"],
                          "default_requests_per_s": other["requests_per_s"]})  # fmt: skip
    init = {}
    for session in config["sessions"]:
        path = run_dir / "sessions" / session["id"] / "session.json"
        if path.is_file():
            init[session["id"]] = json.loads(path.read_text(encoding="utf-8")).get("init_s")
    return {"passes": per_pass, "pairs": pairs, "engine_init_s": init}


def demo_tables(
    passes: dict[tuple[str, str], dict[str, Any]],
    config: dict[str, Any],
    artifact: dict[str, Any],
) -> dict[str, Any]:
    key = (config["analysis"]["references"]["batch_invariant"],
           config["analysis"]["reference_pass"]["greedy"])  # fmt: skip
    if key not in passes:
        return {"tables": [], "note": "reference pass missing"}
    rows = passes[key]["rows"]
    requests = requests_for(config, artifact)
    budget = int(config["analysis"]["keep_budget"])
    k = int(config["pools"]["size"])
    tables = []
    table_rows = []
    for q_index, question in enumerate(artifact["questions"]):
        for arm in config["pools"]["arms"]:
            reqs = [r for r in requests if r["question_index"] == q_index and r["arm"] == arm]
            texts = [rows.get(r["index"], {}).get("text") for r in reqs]
            complete = all(t is not None for t in texts) and len(reqs) == 1 << k
            utility = [mc.contains_answer(t or "", question["answer"]) for t in texts]
            gold = sum(1 for m in question["pools"][arm] if m["is_gold"])
            entry: dict[str, Any] = {
                "question_id": question["question_id"],
                "question_type": question["question_type"],
                "arm": arm,
                "gold_in_pool": gold,
                "complete": complete,
                "distinct_replies": len({t for t in texts if t is not None}),
                "utility_mean": sum(utility) / len(utility) if utility else None,
                "utility_full": utility[-1] if utility else None,
                "utility_empty": utility[0] if utility else None,
                "utility_constant": len(set(utility)) <= 1,
            }
            if complete:
                spectrum = mc.fourier_order_shares(utility)
                entry["fourier_share_order_2_plus"] = spectrum["share_order_2_plus"]
                entry["fourier_shares"] = spectrum["shares"]
                entry["and_or_baseline"] = mc.and_or_baseline(gold)
                dividends = mc.moebius(utility)
                entry["moebius_nonzero_by_order"] = [
                    sum(
                        1 for t, v in enumerate(dividends) if mc.popcount(t) == o and abs(v) > 1e-12
                    )
                    for o in range(k + 1)
                ]
                if not entry["utility_constant"]:
                    best, best_sets = mc.best_keep_sets(utility, budget)
                    loo = mc.loo_credit(utility)
                    phi = mc.shapley(utility)
                    entry["best_keep_value"] = best
                    entry["best_keep_sets"] = len(best_sets)
                    entry["loo_credit"] = loo
                    entry["shapley_credit"] = phi
                    entry["loo_regret"] = mc.keep_set_regret_range(utility, loo, budget)
                    entry["shapley_regret"] = mc.keep_set_regret_range(utility, phi, budget)
            tables.append(entry)
            for r, text, u in zip(reqs, texts, utility, strict=True):
                row = {"question_id": question["question_id"], "arm": arm, "mask": r["mask"],
                       "reply": text, "utility_contains": u}  # fmt: skip
                table_rows.append(row)
    return {"tables": tables, "rows": table_rows}


def engine_log_lines(run_dir: Path) -> dict[str, list[str]]:
    lines: dict[str, list[str]] = {}
    for path in sorted(run_dir.glob("worker-*.log")):
        kept: list[str] = []
        seen: set[str] = set()
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            low = line.lower()
            if any(marker in low for marker in LOG_MARKERS):
                body = line.split("] ", 1)[-1][:300]
                if body not in seen:
                    seen.add(body)
                    kept.append(body)
        lines[path.stem.removeprefix("worker-")] = kept[:80]
    return lines


def cost_summary(throughput: dict[str, Any], config: dict[str, Any], n_questions: int) -> dict:
    out: dict[str, Any] = {}
    arms = len(config["pools"]["arms"])
    k = int(config["pools"]["size"])
    for row in throughput["passes"]:
        if row["pass"] != "greedy-all-canonical" or row["status"] != "complete":
            continue
        per_question = row["wall_s"] / n_questions
        full_q = int(config["analysis"]["full_study_questions"])
        out[row["session"]] = {
            "batch_invariant": row["batch_invariant"],
            "wall_s": row["wall_s"],
            "questions": n_questions,
            "requests_per_question": arms * (1 << k),
            "gpu_s_per_question_both_arms": per_question,
            "gpu_s_per_table": per_question / arms,
            "full_study_gpu_h_both_arms": full_q * per_question / 3600.0,
        }
    return out


def analyze_run(
    run_dir: Path, config: dict[str, Any], artifact: dict[str, Any], out_dir: Path
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    passes = load_passes(run_dir)
    requests = requests_for(config, artifact)
    cluster_of = {r["index"]: f"{r['question_id']}/{r['arm']}" for r in requests}
    identity = identity_tables(passes, config, cluster_of)
    throughput = throughput_tables(passes, config, run_dir)
    demo = demo_tables(passes, config, artifact)
    cost = cost_summary(throughput, config, len(artifact["questions"]))
    logs = engine_log_lines(run_dir)
    lane.write_json(out_dir / "identity.json", identity)
    lane.write_json(out_dir / "throughput.json", throughput)
    lane.write_json(out_dir / "cost.json", cost)
    lane.write_json(out_dir / "demo-tables.json", demo["tables"])
    lane.write_json(out_dir / "engine-log-lines.json", logs)
    with gzip.open(out_dir / "demo-table-rows.jsonl.gz", "wt", encoding="utf-8") as handle:
        for row in demo.get("rows", []):
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    headline = {
        "identity": [
            {k: r.get(k) for k in ("mode", "sampling", "ref", "other", "n_common",
                                   "identical_tokens", "identical_tokens_and_logprob_bits",
                                   "ci95_tokens")}
            for r in identity
        ],
        "throughput_pairs": throughput["pairs"],
        "cost": cost,
    }  # fmt: skip
    lane.write_json(out_dir / "headline.json", headline)
    return {"headline": headline, "identity": identity, "throughput": throughput, "demo": demo}


def analyze_main(args: argparse.Namespace) -> int:
    config = mc.load_config()
    artifact = load_artifact(Path(args.evidence), args.expected_evidence_sha256)
    result = analyze_run(Path(args.run_dir), config, artifact, Path(args.output_dir))
    print(json.dumps(result["headline"], indent=2, sort_keys=True))
    return 0


# --------------------------------------------------------------------------- selftest


class _Lp:
    def __init__(self, value: float) -> None:
        self.logprob = value


def synthetic_run(run_dir: Path, n_requests: int) -> None:
    """A fake run directory (two greedy passes per mode, one differing request) for selftests."""

    for session_id, name, flip in (("bi-a", "greedy-all-canonical", None),
                                   ("bi-a", "greedy-all-shuffled", None),
                                   ("default-a", "greedy-all-canonical", None),
                                   ("default-a", "greedy-all-shuffled", 3)):  # fmt: skip
        out = run_dir / "sessions" / session_id
        out.mkdir(parents=True, exist_ok=True)
        indices = list(range(n_requests))
        ids = [f"{session_id}/{name}/{i}" for i in indices]
        state = {}
        for ours, i in zip(ids, indices, strict=True):
            st = new_state()
            st["token_ids"] = [1000 + i, 7, 9] if i != flip else [1000 + i, 8]
            st["logp"] = [-0.5, -0.25, -0.125] if i != flip else [-0.5, -1.0]
            st["text"] = [f"reply {i}" if i != flip else "other"]
            st["finished"] = True
            st["finish_reason"] = "stop"
            st["num_cached_tokens"] = 16
            state[ours] = st
        record = {"session": session_id, "name": name,
                  "batch_invariant": session_id.startswith("bi"), "sampling": "greedy",
                  "order": "canonical", "set": "all", "requests": n_requests,
                  "info": {"wall_s": 2.0, "finished": n_requests, "unmatched": 0},
                  "status": "complete"}  # fmt: skip
        save_pass(out, name, indices, ids, state, [100] * n_requests, record)
        lane.write_json(out / "session.json", {"init_s": 1.0})


def selftest_main(args: argparse.Namespace) -> int:
    import tempfile

    from transformers import AutoTokenizer

    config = mc.load_config()
    artifact = load_artifact(Path(args.evidence), args.expected_evidence_sha256)
    requests = requests_for(config, artifact)
    report: dict[str, Any] = {"plan": build_plan(config, artifact)}
    tokenizer = AutoTokenizer.from_pretrained(str(Path(args.model_root) / config["model"]["id"]))
    enable_thinking = bool(config["prompt"]["enable_thinking"])
    lengths = []
    for r in requests:
        ids = render_prompt_ids(
            tokenizer, mc.request_message(artifact, r, config["prompt"]), enable_thinking
        )
        lengths.append(len(ids))
    first = render_prompt_ids(
        tokenizer, mc.request_message(artifact, requests[-1], config["prompt"]), enable_thinking
    )
    tail = tokenizer.decode(first[-12:])
    max_tokens = max(s["max_tokens"] for s in config["sampling"].values())
    report["prompts"] = {
        "requests": len(requests),
        "len_min": min(lengths),
        "len_max": max(lengths),
        "len_mean": sum(lengths) / len(lengths),
        "tokens_total": sum(lengths),
        "fits": max(lengths) + max_tokens <= config["engine"]["max_model_len"],
        "end_of_turn_id": tokenizer.convert_tokens_to_ids(END_OF_TURN),
        "last_prompt_tail": tail,
        "thinking_disabled": "<think>\n\n</think>" in tokenizer.decode(first),
    }
    values, missing = delta_logprobs([5, 7], [{5: _Lp(-0.5)}, {3: _Lp(-0.1)}])
    assert values[0] == -0.5 and missing == 1
    report["parsers"] = "ok"
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp)
        synthetic_run(run_dir, 8)
        result = analyze_run(run_dir, config, artifact, run_dir / "analysis")
        identity = {(r["mode"], tuple(r["other"])): r for r in result["identity"]}
        bi = identity[("batch_invariant", ("bi-a", "greedy-all-shuffled"))]
        default = identity[("default", ("default-a", "greedy-all-shuffled"))]
        assert bi["identical_tokens"] == bi["n_common"] == 8
        assert default["identical_tokens"] == 7 and default["differing_total"] == 1
        report["analysis_selftest"] = "ok"
    try:
        import vllm

        report["vllm_version"] = vllm.__version__
        report["vllm_cited_files_sha256"] = vllm_file_digests(Path(vllm.__file__).parent)
    except Exception as exc:  # noqa: BLE001 - recorded
        report["vllm_import_error"] = repr(exc)
    report["ok"] = report["prompts"]["fits"] and report["prompts"]["thinking_disabled"]
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    sub = parser.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan", allow_abbrev=False)
    plan.add_argument("--evidence", default=None)
    selftest = sub.add_parser("selftest", allow_abbrev=False)
    selftest.add_argument("--model-root", default=str(MODEL_ROOT))
    selftest.add_argument("--evidence", required=True)
    selftest.add_argument("--expected-evidence-sha256", default=None)
    run = sub.add_parser("run", allow_abbrev=False)
    run.add_argument("--seeds", type=int, nargs="+", required=True)
    run.add_argument("--output-dir", required=True)
    run.add_argument("--allocation-minutes", type=float, required=True)
    run.add_argument("--evidence", required=True)
    run.add_argument("--expected-evidence-sha256", required=True)
    worker = sub.add_parser("worker", allow_abbrev=False)
    worker.add_argument("--session", required=True)
    worker.add_argument("--output-dir", required=True)
    worker.add_argument("--deadline", type=float, required=True)
    worker.add_argument("--evidence", required=True)
    worker.add_argument("--expected-evidence-sha256", required=True)
    analyze = sub.add_parser("analyze", allow_abbrev=False)
    analyze.add_argument("--run-dir", required=True)
    analyze.add_argument("--output-dir", required=True)
    analyze.add_argument("--evidence", required=True)
    analyze.add_argument("--expected-evidence-sha256", default=None)
    args = parser.parse_args()
    if args.command == "plan":
        config = mc.load_config()
        artifact = load_artifact(Path(args.evidence), None) if args.evidence else None
        print(json.dumps(build_plan(config, artifact), indent=2, sort_keys=True))
        return 0
    if args.command == "selftest":
        return selftest_main(args)
    if args.command == "run":
        return run_main(args)
    if args.command == "analyze":
        return analyze_main(args)
    return worker_main(args)


if __name__ == "__main__":
    sys.exit(main())
