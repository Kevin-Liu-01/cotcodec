#!/usr/bin/env python3
"""G2 exploratory pilot, job 1: vLLM rollouts and the vLLM prefill recompute (R5).

EXPLORATORY (experiments/g2/g2-pilot-v1.yaml). Runs inside the digest-pinned cotcodec-vllm cu129
overlay (vLLM 0.31.0) on the docker-research lane.

Subcommands:

* ``plan``: print the resolved plan (models, requests, engine arguments). CPU only.
* ``selftest``: CPU only, no engine. Renders every prompt with each model's chat template
  (model cache under ``--model-root``) and checks the output parsers on synthetic objects.
* ``run --seeds 42 43 44 --output-dir D --allocation-minutes M``: the job. For each model in
  config order it re-verifies the snapshot, then runs ``worker`` in a subprocess, waits for the
  GPU to be released, and finally writes ``tf-input.json`` (the token sequences the
  teacher-forcing job reads as its hash-bound study artifact).
* ``worker --model X --output-dir D --deadline T``: one vLLM engine. It samples every
  (seed, prompt) request with the sampled-token log-prob (decode path), then feeds every
  completed sequence back as a prompt with ``prompt_logprobs=0`` (prefill path), and saves
  ``tokens.npz``, ``sequences.json`` and ``texts.jsonl.gz``. Requests go through
  ``LLMEngine.add_request``/``step`` so that the worker can stop at its deadline and keep
  every finished sequence.

Per-token outputs for each completion token t of a sequence: the token id, the decode-time
log-prob vLLM sampled it with, and the prefill-time log-prob of the same token.
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

from harness import g2_pilot as g2  # noqa: E402

#: Cache and runtime directories for vLLM, Triton, Inductor and FlashInfer, under the run dir.
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


# --------------------------------------------------------------------------- plan


def engine_kwargs(config: dict[str, Any], model_id: str, model_dir: Path) -> dict[str, Any]:
    engine = config["engine"]
    kwargs: dict[str, Any] = {
        "model": str(model_dir),
        "tokenizer": str(model_dir),
        "trust_remote_code": False,
        "dtype": engine["dtype"],
        "seed": config["seeds"][0],
        "max_model_len": engine["max_model_len"],
        "gpu_memory_utilization": engine["gpu_memory_utilization"],
        "max_num_seqs": engine["max_num_seqs"],
        "max_num_batched_tokens": engine["max_num_batched_tokens"],
        "enable_prefix_caching": engine["enable_prefix_caching"],
        "logprobs_mode": engine["logprobs_mode"],
    }
    kwargs.update(config["models"][model_id].get("vllm_extra", {}))
    return kwargs


def build_plan(config: dict[str, Any]) -> dict[str, Any]:
    prompts = g2.load_prompts(config)
    requests = g2.rollout_plan(config, prompts)
    return {
        "experiment_id": config["experiment_id"],
        "claim_level": config["claim_level"],
        "seeds": config["seeds"],
        "models": {
            model_id: {
                "rollout_seeds": model["rollout_seeds"],
                "requests": sum(1 for r in requests if r["model_id"] == model_id),
                "engine_kwargs": engine_kwargs(config, model_id, g2.MODEL_ROOT / model_id),
            }
            for model_id, model in config["models"].items()
        },
        "sampling": config["sampling"],
        "prefill_arm": config["prefill_arm"],
        "requests": len(requests),
    }


# --------------------------------------------------------------------------- prompts and parsers


def render_prompt_ids(tokenizer: Any, message: str, enable_thinking: bool) -> list[int]:
    text = tokenizer.apply_chat_template(
        [{"role": "user", "content": message}],
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=enable_thinking,
    )
    ids = tokenizer(text, add_special_tokens=False)["input_ids"]
    return [int(i) for i in ids]


def sampled_logprobs(token_ids: list[int], logprobs: Any) -> list[float]:
    """The log-prob of each sampled token from vLLM's per-position logprob dicts."""

    if logprobs is None or len(logprobs) != len(token_ids):
        raise ValueError("logprobs missing or not aligned with the sampled tokens")
    return [float(logprobs[t][tok].logprob) for t, tok in enumerate(token_ids)]


def prefill_logprobs(
    prompt_len: int, completion_ids: list[int], prompt_logprobs: Any
) -> list[float]:
    """Prefill-time log-probs of the completion tokens from a full-sequence prompt request."""

    total = prompt_len + len(completion_ids)
    if prompt_logprobs is None or len(prompt_logprobs) != total:
        raise ValueError("prompt_logprobs missing or not aligned with the sequence")
    return [
        float(prompt_logprobs[prompt_len + t][tok].logprob) for t, tok in enumerate(completion_ids)
    ]


# --------------------------------------------------------------------------- worker


class StopFlag:
    def __init__(self) -> None:
        self.event = threading.Event()
        self.reason: str | None = None

    def handler(self, signum: int, _frame: Any) -> None:
        self.reason = signal.Signals(signum).name
        self.event.set()


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


def stream_requests(
    llm: Any, items: list[tuple[str, Any, Any]], stop_at: float, flag: StopFlag, delta: bool
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Add every request under our own id (LLMEngine.add_request), step the engine until done,
    the stop time or a signal, then abort what is left. With ``delta`` the engine streams each
    step's new tokens and log-probs, so a request cut at the stop time keeps what it sampled."""

    from vllm.sampling_params import RequestOutputKind

    engine = llm.llm_engine
    state: dict[str, dict[str, Any]] = {}
    for ours, prompt, params in items:
        params.output_kind = RequestOutputKind.DELTA if delta else RequestOutputKind.FINAL_ONLY
        engine.add_request(ours, prompt, params)
        state[ours] = {
            "token_ids": [],
            "logp": [],
            "text": [],
            "finish_reason": None,
            "stop_reason": None,
            "finished": False,
            "prompt_logprobs": None,
            "missing_logprobs": 0,
        }
    info: dict[str, Any] = {"aborted": 0, "steps": 0, "stopped_by": None, "unmatched": 0}
    started = time.time()
    while engine.has_unfinished_requests():
        if time.time() >= stop_at or flag.event.is_set():
            info["stopped_by"] = flag.reason or "time budget"
            left = [ours for ours, st in state.items() if not st["finished"]]
            info["aborted"] = len(left)
            try:
                engine.abort_request(left, internal=False)
            except Exception as exc:  # noqa: BLE001 - recorded; the worker saves and exits
                info["abort_error"] = repr(exc)
            break
        for output in engine.step():
            st = state.get(str(output.request_id))
            if st is None:
                info["unmatched"] += 1
                continue
            if output.prompt_logprobs is not None and st["prompt_logprobs"] is None:
                st["prompt_logprobs"] = output.prompt_logprobs
            if output.outputs:
                completion = output.outputs[0]
                ids = [int(t) for t in completion.token_ids]
                if delta:
                    values, missing = delta_logprobs(ids, completion.logprobs)
                    st["token_ids"].extend(ids)
                    st["logp"].extend(values)
                    st["missing_logprobs"] += missing
                    st["text"].append(completion.text or "")
                else:
                    st["token_ids"] = ids
                if output.finished:
                    st["finish_reason"] = completion.finish_reason
                    st["stop_reason"] = completion.stop_reason
            if output.finished:
                st["finished"] = True
        info["steps"] += 1
    info["wall_s"] = round(time.time() - started, 2)
    info["finished"] = sum(1 for st in state.values() if st["finished"])
    return state, info


def worker_main(args: argparse.Namespace) -> int:
    import numpy as np
    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams
    from vllm.inputs import TokensPrompt

    config = g2.load_config()
    prompts = g2.load_prompts(config)
    model_id = args.model
    model = config["models"][model_id]
    model_dir = g2.MODEL_ROOT / model_id
    out = Path(args.output_dir) / model_id
    out.mkdir(parents=True, exist_ok=True)
    flag = StopFlag()
    signal.signal(signal.SIGTERM, flag.handler)
    signal.signal(signal.SIGUSR1, flag.handler)
    log_path = out / "worker-progress.jsonl"

    def log(event: str, **fields: Any) -> None:
        record = {"utc": g2.utc_now(), "event": event, "model": model_id, **fields}
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        print(json.dumps(record, sort_keys=True), flush=True)

    tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
    enable_thinking = bool(config["prompts"]["enable_thinking"])
    prompt_ids = {
        row["prompt_index"]: render_prompt_ids(
            tokenizer, g2.user_message(row, config), enable_thinking
        )
        for row in prompts
    }
    end_of_turn = tokenizer.convert_tokens_to_ids(END_OF_TURN)
    kwargs = engine_kwargs(config, model_id, model_dir)
    log("engine-start", engine_kwargs=kwargs, end_of_turn_id=end_of_turn)
    t0 = time.time()
    llm = LLM(**kwargs)
    log("engine-ready", init_s=round(time.time() - t0, 1))

    sampling = config["sampling"]
    items = []
    meta: dict[str, dict[str, Any]] = {}
    subset = g2.prompt_subset(prompts, args.prompt_count)
    for seed in model["rollout_seeds"]:
        for row in subset:
            seq_id = g2.sequence_id(model_id, row["prompt_index"], seed)
            params = SamplingParams(
                n=1,
                temperature=sampling["temperature"],
                top_p=sampling["top_p"],
                top_k=sampling["top_k"],
                max_tokens=sampling["max_tokens"],
                logprobs=sampling["logprobs"],
                seed=seed,
                stop_token_ids=[end_of_turn],
            )
            items.append(
                (seq_id, TokensPrompt(prompt_token_ids=prompt_ids[row["prompt_index"]]), params)
            )
            meta[seq_id] = {"prompt_index": row["prompt_index"], "seed": seed}
    log("rollouts-start", requests=len(items), gen_seconds=args.gen_seconds)
    gen_stop = min(args.deadline, time.time() + args.gen_seconds)
    state, info = stream_requests(llm, items, gen_stop, flag, delta=True)
    log("rollouts-done", **info)

    sequences = []
    for seq_id, _, _ in items:
        st = state[seq_id]
        if not st["token_ids"]:
            continue
        sequences.append(
            {
                "sequence_id": seq_id,
                **meta[seq_id],
                "prompt_ids": prompt_ids[meta[seq_id]["prompt_index"]],
                "completion_ids": st["token_ids"],
                "logp_decode": st["logp"],
                "finish_reason": st["finish_reason"] if st["finished"] else "cut_at_time_budget",
                "stop_reason": st["stop_reason"],
                "missing_logprobs": st["missing_logprobs"],
                "text": "".join(st["text"]),
            }
        )

    # R5: prefill recompute of every saved sequence, unless skipped or out of time.
    prefill: dict[str, list[float]] = {}
    remaining = args.deadline - time.time()
    if args.skip_prefill:
        log("prefill-skipped", reason="--skip-prefill")
    elif sequences and remaining > args.prefill_reserve_s and not flag.event.is_set():
        pre_items = [
            (
                "prefill/" + s["sequence_id"],
                TokensPrompt(prompt_token_ids=s["prompt_ids"] + s["completion_ids"]),
                SamplingParams(
                    max_tokens=1,
                    temperature=sampling["temperature"],
                    prompt_logprobs=config["prefill_arm"]["prompt_logprobs"],
                    seed=config["seeds"][0],
                    detokenize=False,
                ),
            )
            for s in sequences
        ]
        log("prefill-start", requests=len(pre_items))
        pre_state, pre_info = stream_requests(llm, pre_items, args.deadline, flag, delta=False)
        log("prefill-done", **pre_info)
        for s in sequences:
            pst = pre_state["prefill/" + s["sequence_id"]]
            if pst["finished"] and pst["prompt_logprobs"] is not None:
                prefill[s["sequence_id"]] = prefill_logprobs(
                    len(s["prompt_ids"]), s["completion_ids"], pst["prompt_logprobs"]
                )
    else:
        log("prefill-skipped", remaining_s=round(remaining, 1), signal=flag.reason)

    # Save: per-token arrays, per-sequence metadata, texts.
    offsets = [0]
    for s in sequences:
        offsets.append(offsets[-1] + len(s["completion_ids"]))
    nan = float("nan")
    np.savez_compressed(
        out / "tokens.npz",
        offsets=np.asarray(offsets, dtype=np.int64),
        prompt_len=np.asarray([len(s["prompt_ids"]) for s in sequences], dtype=np.int32),
        token_ids=np.asarray([t for s in sequences for t in s["completion_ids"]], dtype=np.int32),
        logp_decode=np.asarray([v for s in sequences for v in s["logp_decode"]], dtype=np.float32),
        logp_prefill=np.asarray(
            [
                v
                for s in sequences
                for v in prefill.get(s["sequence_id"], [nan] * len(s["completion_ids"]))
            ],
            dtype=np.float32,
        ),
    )
    with gzip.open(out / "texts.jsonl.gz", "wt", encoding="utf-8") as handle:
        for s in sequences:
            handle.write(json.dumps({"sequence_id": s["sequence_id"], "text": s["text"]}) + "\n")
    g2.write_json(
        out / "sequences.json",
        {
            "model_id": model_id,
            "engine_kwargs": kwargs,
            "sampling": sampling,
            "end_of_turn_id": end_of_turn,
            "sequence_order": [s["sequence_id"] for s in sequences],
            "sequences": [
                {
                    key: s[key]
                    for key in (
                        "sequence_id",
                        "prompt_index",
                        "seed",
                        "finish_reason",
                        "stop_reason",
                        "missing_logprobs",
                    )
                }
                | {
                    "prompt_len": len(s["prompt_ids"]),
                    "completion_len": len(s["completion_ids"]),
                    "has_prefill": s["sequence_id"] in prefill,
                }
                for s in sequences
            ],
            "rollout_info": info,
            "requests": len(items),
        },
    )
    # The token sequences for the teacher-forcing job.
    g2.write_json(
        out / "tf-sequences.json",
        [
            {
                "sequence_id": s["sequence_id"],
                "model_id": model_id,
                "prompt_index": s["prompt_index"],
                "seed": s["seed"],
                "prompt_ids": s["prompt_ids"],
                "completion_ids": s["completion_ids"],
            }
            for s in sequences
        ],
    )
    log("saved", sequences=len(sequences), prefilled=len(prefill), tokens=offsets[-1])
    code = 0 if len(sequences) == len(items) else 3
    g2.write_json(out / "done.json", {"exit": code, "utc": g2.utc_now()})
    # vLLM's exit can hang (job 1337): shut the engine core down with a bounded wait, then
    # leave without interpreter teardown. The driver also kills the process group if needed.
    closer = threading.Thread(target=lambda: llm.llm_engine.engine_core.shutdown(), daemon=True)
    closer.start()
    closer.join(timeout=15)
    sys.stdout.flush()
    os._exit(code)


# --------------------------------------------------------------------------- driver


def gpu_memory_used_mib() -> list[int]:
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        return [int(x) for x in result.stdout.split()]
    except (OSError, ValueError, subprocess.SubprocessError):
        return []


def record_environment(out: Path) -> None:
    info: dict[str, Any] = {"utc": g2.utc_now(), "python": sys.version}
    try:
        import torch
        import transformers
        import vllm

        info.update(
            vllm=vllm.__version__,
            torch=torch.__version__,
            torch_cuda=torch.version.cuda,
            transformers=transformers.__version__,
        )
    except Exception as exc:  # noqa: BLE001 - recorded
        info["import_error"] = repr(exc)
    try:
        info["nvidia_smi"] = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,uuid,driver_version,memory.total,clocks.max.sm",
             "--format=csv"],
            capture_output=True, text=True, timeout=30, check=False,
        ).stdout  # fmt: skip
    except (OSError, subprocess.SubprocessError) as exc:
        info["nvidia_smi_error"] = repr(exc)
    info["lane"] = {
        k: os.environ.get(k)
        for k in ("COTCODEC_GIT_SHA", "COTCODEC_SOURCE_SHA256", "COTCODEC_MODEL_ID",
                  "CUDA_VISIBLE_DEVICES")
    }  # fmt: skip
    g2.write_json(out / "environment.json", info)


def run_main(args: argparse.Namespace) -> int:
    config = g2.load_config()
    if list(args.seeds) != config["seeds"]:
        raise g2.G2ConfigError("--seeds must equal the config's declared seeds")
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    stop_at, source = g2.deadline(args.allocation_minutes)
    env = dict(os.environ)
    for key, sub in CACHE_DIRS.items():
        path = out / "cache" / sub
        path.mkdir(parents=True, exist_ok=True)
        env[key] = str(path)
    env.update(FIXED_ENV)
    summary: dict[str, Any] = {
        "experiment_id": config["experiment_id"],
        "claim_level": "exploratory",
        "job": "rollouts",
        "started_at": g2.utc_now(),
        "allocation_minutes": args.allocation_minutes,
        "deadline_source": source,
        "deadline_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(stop_at)),
        "plan": build_plan(config),
        "models": {},
    }
    g2.write_json(out / "summary.json", summary)
    record_environment(out)
    state: dict[str, Any] = {"child": None, "signal": None, "signal_at": None}

    def on_signal(signum: int, _frame: Any) -> None:
        state["signal"] = signal.Signals(signum).name
        state["signal_at"] = time.time()
        child = state["child"]
        if child is not None and child.poll() is None:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(child.pid, signal.SIGTERM)

    signal.signal(signal.SIGUSR1, on_signal)
    signal.signal(signal.SIGTERM, on_signal)

    selected = list(args.models or config["models"])
    unknown = sorted(set(selected) - set(config["models"]))
    if unknown:
        raise g2.G2ConfigError(f"--models names models outside the config: {unknown}")
    summary["selected_models"] = selected
    summary["prompt_count"] = args.prompt_count
    summary["gen_seconds"] = args.gen_seconds
    summary["skip_prefill"] = args.skip_prefill
    verifications: dict[str, Any] = {}

    def verify(model_id: str) -> None:
        try:
            verifications[model_id] = g2.verify_model(
                model_id, config["models"][model_id]["receipt_root"]
            )
        except Exception as exc:  # noqa: BLE001 - recorded, the model is skipped
            verifications[model_id] = {"error": repr(exc)}

    threads = {m: threading.Thread(target=verify, args=(m,), daemon=True) for m in selected}
    for thread in threads.values():
        thread.start()
    for index, model_id in enumerate(selected):
        record: dict[str, Any] = {}
        summary["models"][model_id] = record
        remaining = stop_at - time.time()
        minimum = args.min_model_s if index else 0.0
        if state["signal"] or remaining < minimum:
            record["status"] = "skipped"
            record["reason"] = state["signal"] or f"remaining {remaining:.0f} s < {minimum:.0f} s"
            continue
        threads[model_id].join()
        record["verification"] = verifications.get(model_id)
        if "error" in (record["verification"] or {"error": "missing"}):
            record["status"] = "verification-failed"
            continue
        argv = [
            sys.executable,
            str(Path(__file__).resolve()),
            "worker",
            "--model",
            model_id,
            "--output-dir",
            str(out),
            "--deadline",
            f"{stop_at:.3f}",
            "--gen-seconds",
            f"{args.gen_seconds:.0f}",
            "--prompt-count",
            str(args.prompt_count),
        ]
        if args.skip_prefill:
            argv.append("--skip-prefill")
        record["argv"] = argv
        record["started_at"] = g2.utc_now()
        started = time.time()
        with (out / f"worker-{model_id}.log").open("w", encoding="utf-8") as logfile:
            child = subprocess.Popen(
                argv, env=env, stdout=logfile, stderr=subprocess.STDOUT, start_new_session=True
            )
            state["child"] = child
            done_marker = out / model_id / "done.json"
            done_seen: float | None = None
            while child.poll() is None:
                now = time.time()
                if done_seen is None and done_marker.is_file():
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
            # Leftover engine processes of the worker's session, if any.
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.killpg(child.pid, signal.SIGKILL)
        record["exit"] = child.returncode
        record["wall_s"] = round(time.time() - started, 1)
        done = out / model_id / "done.json"
        saved = json.loads(done.read_text()) if done.is_file() else None
        record["worker_done"] = saved
        record["status"] = (
            "failed" if saved is None else {0: "complete", 3: "partial"}.get(saved["exit"], "failed")
        )
        release_until = time.time() + 120
        while time.time() < release_until:
            used = gpu_memory_used_mib()
            if not used or max(used) < 1024:
                break
            time.sleep(2.0)
        record["gpu_memory_after_mib"] = gpu_memory_used_mib()
        g2.write_json(out / "summary.json", summary)

    # The teacher-forcing input: every saved sequence of every model, in model order.
    merged = []
    for model_id in selected:
        path = out / model_id / "tf-sequences.json"
        if path.is_file():
            merged.extend(json.loads(path.read_text(encoding="utf-8")))
    tf_input = {
        "experiment_id": config["experiment_id"],
        "git_sha": os.environ.get("COTCODEC_GIT_SHA"),
        "sequences": merged,
    }
    g2.write_json(out / "tf-input.json", tf_input)
    summary["tf_input_sha256"] = g2.sha256_file(out / "tf-input.json")
    summary["tf_input_sequences"] = len(merged)
    summary["finished_at"] = g2.utc_now()
    summary["signal"] = state["signal"]
    g2.write_json(out / "summary.json", summary)
    if state["signal"]:
        g2.write_checkpoint_marker(
            "SIGUSR1" if state["signal"] == "SIGUSR1" else "SIGTERM",
            "rollouts: every finished model saved; no resume (a rerun is a new job)",
        )
    statuses = [m.get("status") for m in summary["models"].values()]
    return 0 if all(s == "complete" for s in statuses) else 3


def merge_tf_inputs(parts: list[dict[str, Any]], experiment_id: str) -> dict[str, Any]:
    """One teacher-forcing input from several rollout jobs' tf-input.json files (CPU)."""

    sequences: list[dict[str, Any]] = []
    seen: set[str] = set()
    sources = []
    for part in parts:
        if part.get("experiment_id") != experiment_id:
            raise g2.G2ConfigError("a tf-input belongs to another experiment")
        for seq in part["sequences"]:
            if seq["sequence_id"] in seen:
                raise g2.G2ConfigError(f"duplicate sequence {seq['sequence_id']}")
            seen.add(seq["sequence_id"])
            sequences.append(seq)
        sources.append({"git_sha": part.get("git_sha"), "sequences": len(part["sequences"])})
    return {"experiment_id": experiment_id, "git_sha": sources[0]["git_sha"], "sources": sources,
            "sequences": sequences}  # fmt: skip


def merge_main(args: argparse.Namespace) -> int:
    config = g2.load_config()
    parts = []
    for path in args.inputs:
        raw = Path(path).read_bytes()
        part = json.loads(raw)
        part["_sha256"] = g2.sha256_bytes(raw)
        parts.append(part)
    merged = merge_tf_inputs(parts, config["experiment_id"])
    for source, part in zip(merged["sources"], parts, strict=True):
        source["sha256"] = part["_sha256"]
    out = Path(args.output)
    if out.exists():
        raise g2.G2ConfigError("refusing to overwrite the merged tf-input")
    g2.write_json(out, merged)
    print(json.dumps({"sequences": len(merged["sequences"]), "sha256": g2.sha256_file(out),
                      "sources": merged["sources"]}, sort_keys=True))  # fmt: skip
    return 0


# --------------------------------------------------------------------------- selftest


class _Lp:
    def __init__(self, value: float) -> None:
        self.logprob = value


def selftest_main(args: argparse.Namespace) -> int:
    from transformers import AutoTokenizer

    config = g2.load_config()
    prompts = g2.load_prompts(config)
    report: dict[str, Any] = {"plan": build_plan(config), "models": {}}
    root = Path(args.model_root)
    for model_id in config["models"]:
        tokenizer = AutoTokenizer.from_pretrained(str(root / model_id))
        lengths = []
        for row in prompts:
            ids = render_prompt_ids(
                tokenizer, g2.user_message(row, config), config["prompts"]["enable_thinking"]
            )
            lengths.append(len(ids))
        first = render_prompt_ids(
            tokenizer, g2.user_message(prompts[0], config), config["prompts"]["enable_thinking"]
        )
        report["models"][model_id] = {
            "prompt_len_min": min(lengths),
            "prompt_len_max": max(lengths),
            "end_of_turn_id": tokenizer.convert_tokens_to_ids(END_OF_TURN),
            "first_prompt_tail": tokenizer.decode(first[-12:]),
            "fits": max(lengths) + config["sampling"]["max_tokens"] + 1
            <= config["engine"]["max_model_len"],
        }
    tokens = [5, 7, 9]
    decode = [{5: _Lp(-0.5)}, {7: _Lp(-1.0), 3: _Lp(-0.1)}, {9: _Lp(-2.0)}]
    assert sampled_logprobs(tokens, decode) == [-0.5, -1.0, -2.0]
    prompt = [None, {1: _Lp(-3.0)}, {5: _Lp(-0.25)}, {7: _Lp(-0.75)}, {9: _Lp(-1.5)}]
    assert prefill_logprobs(2, tokens, prompt) == [-0.25, -0.75, -1.5]
    report["parsers"] = "ok"
    report["ok"] = all(m["fits"] for m in report["models"].values())
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("plan")
    selftest = sub.add_parser("selftest", allow_abbrev=False)
    selftest.add_argument("--model-root", default=str(g2.MODEL_ROOT))
    run = sub.add_parser("run", allow_abbrev=False)
    run.add_argument("--seeds", type=int, nargs="+", required=True)
    run.add_argument("--output-dir", required=True)
    run.add_argument("--allocation-minutes", type=float, required=True)
    run.add_argument("--min-model-s", type=float, default=240.0)
    run.add_argument("--models", nargs="+", default=None)
    run.add_argument("--prompt-count", type=int, default=64)
    run.add_argument("--gen-seconds", type=float, default=1e9)
    run.add_argument("--skip-prefill", action="store_true")
    merge = sub.add_parser("merge", allow_abbrev=False)
    merge.add_argument("--inputs", nargs="+", required=True)
    merge.add_argument("--output", required=True)
    worker = sub.add_parser("worker", allow_abbrev=False)
    worker.add_argument("--model", required=True)
    worker.add_argument("--output-dir", required=True)
    worker.add_argument("--deadline", type=float, required=True)
    worker.add_argument("--prefill-reserve-s", type=float, default=60.0)
    worker.add_argument("--gen-seconds", type=float, default=1e9)
    worker.add_argument("--prompt-count", type=int, default=64)
    worker.add_argument("--skip-prefill", action="store_true")
    args = parser.parse_args()
    if args.command == "plan":
        print(json.dumps(build_plan(g2.load_config()), indent=2, sort_keys=True))
        return 0
    if args.command == "selftest":
        return selftest_main(args)
    if args.command == "run":
        return run_main(args)
    if args.command == "merge":
        return merge_main(args)
    return worker_main(args)


if __name__ == "__main__":
    sys.exit(main())
