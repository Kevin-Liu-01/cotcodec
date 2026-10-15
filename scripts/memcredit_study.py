#!/usr/bin/env python3
"""AM1 study, development-set pilot (EXPLORATORY): the GPU job.

Config: experiments/am1/memcredit-study-v1.yaml. Runs inside the digest-pinned cotcodec-vllm cu129
overlay (vLLM 0.31.0, transformers, torch) on the docker-research lane with 2 H100; the pools and
placebos come from scripts/memcredit_study_prepare.py as the hash-bound study artifact (the
development split only; this driver refuses any other split).

Subcommands:

* ``plan --evidence A``: requests per pool and in all (CPU).
* ``selftest --evidence A [--expected-evidence-sha256 S] [--model-root M]``: CPU only, no engine.
  Renders every reader request with the Qwen3-8B chat template and the judge's validation items
  with the Qwen3-32B one, checks lengths and the memory spans, runs the attention-signal code on
  CPU with Qwen3-0.6B-Base (eager attention) on one pool, and hashes the cited vLLM files.
* ``run --seeds 42 43 44 --output-dir D --allocation-minutes M --evidence A
  --expected-evidence-sha256 S``: the job. Verifies the models, then runs the config's phases in
  order; each phase's workers run concurrently, one per GPU (``CUDA_VISIBLE_DEVICES``), each a
  fresh process. Between the reader and judge phases it writes the judge items from the GPU-0
  reader pass. Ends with the A/A identity summaries.
* ``worker --worker ID ...``: one worker (reader, judge or attention).
"""

from __future__ import annotations

import argparse
import contextlib
import gzip
import json
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for _path in (PROJECT_ROOT, PROJECT_ROOT / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import memcredit_step0 as s0  # noqa: E402  (engine streaming, pass files, GPU sampler)

from harness import g2_pilot as lane  # noqa: E402
from harness import memcredit as mc  # noqa: E402
from harness import memcredit_study as ms  # noqa: E402

MODEL_ROOT = lane.MODEL_ROOT
SMOKE_REQUESTS = 16
SMOKE_FAILED_EXIT = 4
SELFTEST_MODEL = "qwen3-0.6b-base"


# --------------------------------------------------------------------------- inputs


def load_artifact(path: Path, expected_sha256: str | None) -> dict[str, Any]:
    raw = path.read_bytes()
    if expected_sha256 is not None and mc.sha256_bytes(raw) != expected_sha256:
        raise ms.StudyError("the study artifact differs from the expected SHA-256")
    artifact = json.loads(raw)
    if artifact.get("experiment_id") != ms.EXPERIMENT_ID:
        raise ms.StudyError("the study artifact belongs to another experiment")
    if artifact.get("split") != "development":
        raise ms.StudyError("the development pilot runs on the development split only")
    return artifact


def worker_spec(config: dict[str, Any], worker_id: str) -> dict[str, Any]:
    for phase in config["job"]["phases"]:
        for worker in phase["workers"]:
            if worker["id"] == worker_id:
                return dict(worker, phase=phase["id"])
    raise ms.StudyError(f"unknown worker {worker_id}")


def model_spec(config: dict[str, Any], worker: dict[str, Any]) -> dict[str, Any]:
    if worker["kind"] == "reader":
        return config["reader"]
    if worker["kind"] == "judge":
        return config["judge"][worker["judge"]]
    raise ms.StudyError(f"{worker['id']} has no vLLM model")


def engine_kwargs(spec: dict[str, Any], seed: int, enforce_eager: bool = False) -> dict[str, Any]:
    model_dir = MODEL_ROOT / spec["model_id"]
    engine = spec["engine"]
    extra = {"enforce_eager": True} if enforce_eager else {}
    return extra | {
        "model": str(model_dir),
        "tokenizer": str(model_dir),
        "trust_remote_code": False,
        "dtype": engine["dtype"],
        "seed": seed,
        "max_model_len": engine["max_model_len"],
        "gpu_memory_utilization": engine["gpu_memory_utilization"],
        "max_num_seqs": engine["max_num_seqs"],
        "max_num_batched_tokens": engine["max_num_batched_tokens"],
        "enable_prefix_caching": engine["enable_prefix_caching"],
        "logprobs_mode": engine["logprobs_mode"],
    }


def sampling_kwargs(spec: dict[str, Any]) -> dict[str, Any]:
    return {"n": 1, "temperature": spec["temperature"], "max_tokens": spec["max_tokens"],
            "logprobs": spec["logprobs"]}  # fmt: skip


def order_indices(n: int, order: str, seed: int) -> list[int]:
    return ms.shuffled(range(n), seed) if order == "shuffled" else list(range(n))


def reader_messages(config: dict[str, Any], artifact: dict[str, Any]) -> list[str]:
    requests = ms.request_table(artifact, config["pools"]["arms"])
    return [ms.request_message(artifact, r, config["prompt"]) for r in requests]


def load_pass(session_dir: Path, name: str) -> dict[str, Any]:
    """One saved pass: request index -> tokens, float32 log-prob bits, finish reason, text."""

    import numpy as np

    meta = json.loads((session_dir / f"{name}.json").read_text(encoding="utf-8"))
    data = np.load(session_dir / f"{name}.npz")
    texts: dict[int, str] = {}
    with gzip.open(session_dir / f"{name}.texts.jsonl.gz", "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            texts[int(row["request_index"])] = row["text"]
    # Read each array once: an NpzFile decompresses the member again on every subscript.
    offsets = data["offsets"].tolist()
    token_ids = data["token_ids"].tolist()
    logprobs = data["logprobs"].astype("<f4")
    num_cached = data["num_cached"].tolist()
    rows: dict[int, dict[str, Any]] = {}
    for j, index in enumerate(data["request_index"].tolist()):
        a, b = offsets[j], offsets[j + 1]
        rows[int(index)] = {
            "tokens": tuple(token_ids[a:b]),
            "bits": logprobs[a:b].tobytes(),
            "finish": meta["finish_reasons"][j],
            "cached": int(num_cached[j]),
            "text": texts.get(int(index)),
        }
    return {"meta": meta, "rows": rows}


def completed_replies(passed: dict[str, Any]) -> dict[int, str]:
    return {
        i: row["text"]
        for i, row in passed["rows"].items()
        if row["finish"] in ("stop", "length") and row["text"] is not None
    }


def write_judge_items(
    config: dict[str, Any], artifact: dict[str, Any], out: Path, readers: list[str]
) -> list[dict[str, Any]]:
    """Every distinct (question, reply) of the listed readers' passes, then the validation."""

    requests = ms.request_table(artifact, config["pools"]["arms"])
    n = len(requests)
    replies: dict[int, str] = {}
    extended: list[dict[str, Any]] = []
    for k, reader in enumerate(readers):
        passed = load_pass(out / "sessions" / reader, "all")
        for index, text in completed_replies(passed).items():
            replies[k * n + index] = text
        extended += [dict(r, index=k * n + r["index"]) for r in requests]
    validation = ms.validation_items(artifact, config["judge"]["validation"])
    items = ms.judge_item_table(artifact, replies, extended, validation)
    lane.write_json(out / "judge-items.json", items)
    return items


def phase_readers(phase: dict[str, Any]) -> list[str]:
    """The reader passes a phase needs: its judge items' sources, or the GPU-0 reader."""

    kinds = {w["kind"] for w in phase["workers"]}
    if kinds == {"reader"}:
        return []
    return list(phase.get("judge_items_from", ["reader-gpu0"]))


# --------------------------------------------------------------------------- vLLM workers


def gpu_identity() -> dict[str, Any]:
    info: dict[str, Any] = {"CUDA_VISIBLE_DEVICES": os.environ.get("CUDA_VISIBLE_DEVICES")}
    try:
        import torch

        props = torch.cuda.get_device_properties(0)
        info.update(name=props.name, uuid=str(getattr(props, "uuid", "")),
                    pci_bus_id=getattr(props, "pci_bus_id", None))  # fmt: skip
    except Exception as exc:  # noqa: BLE001 - recorded
        info["error"] = repr(exc)
    return info


def vllm_worker(args: argparse.Namespace, worker: dict[str, Any]) -> int:
    import vllm.envs as vllm_envs
    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams
    from vllm.inputs import TokensPrompt

    config = ms.load_config(Path(args.config))
    artifact = load_artifact(Path(args.evidence), args.expected_evidence_sha256)
    out = Path(args.output_dir) / "sessions" / worker["id"]
    out.mkdir(parents=True, exist_ok=True)
    flag = s0.StopFlag()
    signal.signal(signal.SIGTERM, flag.handler)
    signal.signal(signal.SIGUSR1, flag.handler)
    log_path = out / "worker-progress.jsonl"

    def log(event: str, **fields: Any) -> None:
        record = {"utc": lane.utc_now(), "event": event, "worker": worker["id"], **fields}
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        print(json.dumps(record, sort_keys=True), flush=True)

    spec = model_spec(config, worker)
    model_dir = MODEL_ROOT / spec["model_id"]
    tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
    if worker["kind"] == "reader":
        messages = reader_messages(config, artifact)
        thinking = bool(config["prompt"]["enable_thinking"])
        sampling = config["reader"]["sampling"]
    else:
        items = json.loads((Path(args.output_dir) / "judge-items.json").read_text("utf-8"))
        messages = [ms.judge_message(artifact, item) for item in items]
        thinking = bool(config["judge"]["enable_thinking"])
        sampling = config["judge"]["sampling"]
    prompt_ids = [s0.render_prompt_ids(tokenizer, m, thinking) for m in messages]
    prompt_lens = [len(p) for p in prompt_ids]
    end_of_turn = tokenizer.convert_tokens_to_ids(s0.END_OF_TURN)
    kwargs = engine_kwargs(spec, int(config["seeds"][0]), bool(worker.get("enforce_eager")))
    log("engine-start", engine_kwargs=kwargs, gpu=gpu_identity(),
        env_batch_invariant=os.environ.get("VLLM_BATCH_INVARIANT"),
        vllm_envs_batch_invariant=bool(vllm_envs.VLLM_BATCH_INVARIANT),
        prompt_ids_sha256=s0.prompt_digest(prompt_ids), requests=len(prompt_ids),
        prompt_len_min=min(prompt_lens), prompt_len_max=max(prompt_lens),
        prompt_tokens_total=sum(prompt_lens), end_of_turn_id=end_of_turn)  # fmt: skip
    if not bool(vllm_envs.VLLM_BATCH_INVARIANT):
        log("mode-mismatch")
        lane.write_json(out / "done.json", {"exit": 2, "utc": lane.utc_now()})
        sys.stdout.flush()
        os._exit(2)
    t0 = time.time()
    llm = LLM(**kwargs)
    init_s = round(time.time() - t0, 1)
    log("engine-ready", init_s=init_s)
    engine = llm.llm_engine
    base = sampling_kwargs(sampling)
    order = order_indices(len(prompt_ids), worker.get("order", "canonical"),
                          int(config["job"]["shuffle_seed"]))  # fmt: skip
    if worker["kind"] == "reader" and worker.get("questions") is not None:
        keep = {r["index"] for r in ms.request_table(artifact, config["pools"]["arms"])
                if r["question_index"] < int(worker["questions"])}  # fmt: skip
        order = [i for i in order if i in keep]
    plan = [("smoke", order[:SMOKE_REQUESTS], True), ("all", order, False)]
    passes: list[dict[str, Any]] = []
    code = 0
    for name, indices, smoke in plan:
        remaining = args.deadline - time.time()
        if flag.event.is_set() or remaining < 30:
            passes.append({"name": name, "status": "skipped",
                           "reason": flag.reason or f"remaining {remaining:.0f} s"})  # fmt: skip
            code = 3
            continue
        reset = bool(llm.reset_prefix_cache())
        ids = [f"{worker['id']}/{name}/{i}" for i in indices]
        batch = [
            (ours, TokensPrompt(prompt_token_ids=prompt_ids[i]),
             SamplingParams(**base, stop_token_ids=[end_of_turn]))
            for ours, i in zip(ids, indices, strict=True)
        ]  # fmt: skip
        log("pass-start", name=name, requests=len(batch), prefix_cache_reset=reset)
        stop_at = min(args.deadline, time.time() + float(worker["max_s"]))
        state, info = s0.stream_requests(engine, batch, stop_at, flag, None)
        record = {
            "session": worker["id"],
            "name": name,
            "batch_invariant": True,
            "kind": worker["kind"],
            "model_id": spec["model_id"],
            "sampling": "greedy",
            "sampling_kwargs": base,
            "order": worker.get("order", "canonical"),
            "set": name,
            "requests": len(batch),
            "prefix_cache_reset": reset,
            "info": info,
            "status": "complete" if info["finished"] == len(batch) else "partial",
        }
        record = s0.save_pass(out, name, indices, ids, state, prompt_lens, record)
        passes.append({k: record[k] for k in ("name", "status", "requests")} | {"info": info})
        log("pass-done", name=name, status=record["status"], **info)
        if record["status"] != "complete":
            code = 3
        if smoke:
            ok, why = s0.smoke_ok(record, state)
            log("smoke-check", ok=ok, reason=why)
            if not ok:
                code = SMOKE_FAILED_EXIT
                break
    lane.write_json(out / "session.json",
                    {"worker": worker, "engine_kwargs": kwargs, "init_s": init_s,
                     "passes": passes, "prompt_ids_sha256": s0.prompt_digest(prompt_ids),
                     "gpu": gpu_identity(), "exit": code})  # fmt: skip
    lane.write_json(out / "done.json", {"exit": code, "utc": lane.utc_now()})
    closer = threading.Thread(target=lambda: engine.engine_core.shutdown(), daemon=True)
    closer.start()
    closer.join(timeout=15)
    sys.stdout.flush()
    os._exit(code)


# --------------------------------------------------------------------------- attention (AM6)


def memory_token_spans(
    rendered: str, offsets: list[tuple[int, int]], memories: list[dict[str, Any]]
) -> list[tuple[int, int]]:
    """Token index spans [a, b) of each memory line in the rendered chat prompt."""

    spans = []
    cursor = 0
    for memory in memories:
        line = ms.memory_line(memory)
        start = rendered.find(line, cursor)
        if start < 0:
            raise ms.StudyError("a memory line is missing from the rendered prompt")
        end = start + len(line)
        cursor = end
        tokens = [t for t, (a, b) in enumerate(offsets) if b > start and a < end and b > a]
        if not tokens:
            raise ms.StudyError("a memory line has no tokens")
        spans.append((tokens[0], tokens[-1] + 1))
    return spans


def full_pool_inputs(
    tokenizer: Any, config: dict[str, Any], artifact: dict[str, Any], q_index: int, arm: str
) -> tuple[list[int], list[tuple[int, int]]]:
    question = artifact["questions"][q_index]
    pool = question["pools"][arm]
    message = mc.user_message(question, pool, config["prompt"])
    rendered = tokenizer.apply_chat_template(
        [{"role": "user", "content": message}], tokenize=False, add_generation_prompt=True,
        enable_thinking=bool(config["prompt"]["enable_thinking"]),
    )  # fmt: skip
    encoded = tokenizer(rendered, add_special_tokens=False, return_offsets_mapping=True)
    ids = [int(i) for i in encoded["input_ids"]]
    offsets = [(int(a), int(b)) for a, b in encoded["offset_mapping"]]
    if ids != s0.render_prompt_ids(tokenizer, message, bool(config["prompt"]["enable_thinking"])):
        raise ms.StudyError("offset tokenization differs from the reader's prompt ids")
    return ids, memory_token_spans(rendered, offsets, pool)


class AttentionProbe:
    """Forward hooks on every layer's self-attention that reduce the eager attention weights to
    the mean mass, per head, from the query positions onto each span."""

    def __init__(self, model: Any) -> None:
        self.layers = list(model.model.layers)
        self.query: Any = None
        self.spans: list[tuple[int, int]] = []
        self.captured: dict[int, Any] = {}
        self.handles = [
            layer.self_attn.register_forward_hook(self._hook(i))
            for i, layer in enumerate(self.layers)
        ]

    def _hook(self, index: int) -> Any:
        def hook(_module: Any, _inputs: Any, output: Any) -> None:
            import torch

            weights = output[1] if isinstance(output, tuple) and len(output) > 1 else None
            if weights is None:
                raise ms.StudyError("no attention weights: the model is not in eager attention")
            rows = weights[0].index_select(1, self.query).float()  # [heads, queries, keys]
            masses = [rows[:, :, a:b].sum(-1).mean(-1) for a, b in self.spans]
            self.captured[index] = torch.stack(masses, -1).cpu()

        return hook

    def run(
        self, model: Any, input_ids: list[int], queries: list[int], spans: list[tuple[int, int]]
    ) -> Any:
        import numpy as np
        import torch

        device = next(model.parameters()).device
        self.query = torch.tensor(queries, device=device, dtype=torch.long)
        self.spans = spans
        self.captured = {}
        with torch.no_grad():
            model(input_ids=torch.tensor([input_ids], device=device), use_cache=False)
        if sorted(self.captured) != list(range(len(self.layers))):
            raise ms.StudyError("not every layer reported attention weights")
        return np.stack([self.captured[i].numpy() for i in range(len(self.layers))])

    def close(self) -> None:
        for handle in self.handles:
            handle.remove()


def load_hf_model(model_id: str, dtype_name: str, device: str, model_root: Path = MODEL_ROOT):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    path = model_root / model_id
    dtype = {"bfloat16": torch.bfloat16, "float32": torch.float32}[dtype_name]
    model = AutoModelForCausalLM.from_pretrained(
        str(path), dtype=dtype, attn_implementation="eager", trust_remote_code=False
    )
    model.to(device)
    model.eval()
    return model, AutoTokenizer.from_pretrained(str(path))


def attention_worker(args: argparse.Namespace, worker: dict[str, Any]) -> int:
    import numpy as np

    config = ms.load_config(Path(args.config))
    artifact = load_artifact(Path(args.evidence), args.expected_evidence_sha256)
    out = Path(args.output_dir) / "sessions" / worker["id"]
    out.mkdir(parents=True, exist_ok=True)
    log_path = out / "worker-progress.jsonl"

    def log(event: str, **fields: Any) -> None:
        record = {"utc": lane.utc_now(), "event": event, "worker": worker["id"], **fields}
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        print(json.dumps(record, sort_keys=True), flush=True)

    spec = config["internal"]
    reader = load_pass(Path(args.output_dir) / "sessions" / "reader-gpu0", "all")
    requests = ms.request_table(artifact, config["pools"]["arms"])
    full_index = {
        (r["question_index"], r["arm"]): r["index"]
        for r in requests
        if r["kind"] == "table" and r["mask"] == (1 << len(
            artifact["questions"][r["question_index"]]["pools"][r["arm"]])) - 1
    }  # fmt: skip
    t0 = time.time()
    model, tokenizer = load_hf_model(spec["model_id"], spec["dtype"], "cuda")
    log("model-ready", load_s=round(time.time() - t0, 1), gpu=gpu_identity(),
        attn_implementation=getattr(model.config, "_attn_implementation", None))  # fmt: skip
    probe = AttentionProbe(model)
    masses = []
    meta = []
    code = 0
    for (q_index, arm), request_index in sorted(full_index.items()):
        if time.time() > args.deadline:
            code = 3
            meta.append({"question_index": q_index, "arm": arm, "status": "skipped"})
            continue
        row = reader["rows"].get(request_index)
        ids, spans = full_pool_inputs(tokenizer, config, artifact, q_index, arm)
        reply = list(row["tokens"]) if row else []
        if not reply:
            code = 3
            meta.append({"question_index": q_index, "arm": arm, "status": "no reply"})
            continue
        inputs = ids + reply[:-1]
        queries = list(range(len(ids) - 1, len(ids) - 1 + len(reply)))
        try:
            mass = probe.run(model, inputs, queries, spans)
        except Exception as exc:  # noqa: BLE001 - recorded per pool
            code = 3
            meta.append({"question_index": q_index, "arm": arm, "status": "error",
                         "error": repr(exc)[:500]})  # fmt: skip
            continue
        masses.append(mass.astype(np.float32))
        meta.append({"question_index": q_index, "arm": arm, "status": "ok",
                     "question_id": artifact["questions"][q_index]["question_id"],
                     "request_index": request_index, "prompt_tokens": len(ids),
                     "reply_tokens": len(reply), "spans": spans})  # fmt: skip
    probe.close()
    np.savez_compressed(out / "attention.npz", masses=np.stack(masses) if masses else np.zeros(0))
    lane.write_json(out / "attention.json",
                    {"pools": meta, "model_id": spec["model_id"], "dtype": spec["dtype"],
                     "attn_implementation": spec["attn_implementation"],
                     "shape": list(np.stack(masses).shape) if masses else None,
                     "wall_s": round(time.time() - t0, 1), "gpu": gpu_identity()})  # fmt: skip
    lane.write_json(out / "done.json", {"exit": code, "utc": lane.utc_now()})
    log("done", exit=code, pools=len(masses))
    sys.stdout.flush()
    os._exit(code)


def worker_main(args: argparse.Namespace) -> int:
    config = ms.load_config(Path(args.config))
    worker = worker_spec(config, args.worker)
    if worker["kind"] == "attention":
        return attention_worker(args, worker)
    return vllm_worker(args, worker)


# --------------------------------------------------------------------------- driver


def copy_cache(out: Path, source: str, target: str) -> dict[str, Any]:
    """Copy one worker's compile caches (vLLM, inductor, Triton, CUDA, FlashInfer) to another
    worker's cache root before it starts, so both run the same compiled kernels."""

    src = out / "cache" / source
    dst = out / "cache" / target
    if dst.exists():
        raise ms.StudyError(f"{target}: cache directory exists already")
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("rpc", "tmp"), symlinks=True)
    files = [p for p in dst.rglob("*") if p.is_file()]
    return {"from": source, "files": len(files), "bytes": sum(p.stat().st_size for p in files)}


def worker_env(base: dict[str, str], out: Path, worker: dict[str, Any]) -> dict[str, str]:
    env = dict(base)
    for key, sub in s0.CACHE_DIRS.items():
        path = out / "cache" / worker["id"] / sub
        path.mkdir(parents=True, exist_ok=True)
        env[key] = str(path)
    env.update(s0.FIXED_ENV)
    env["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
    env["CUDA_VISIBLE_DEVICES"] = str(int(worker["gpu"]))
    env.pop("VLLM_BATCH_INVARIANT", None)
    if worker["kind"] in ("reader", "judge"):
        env["VLLM_BATCH_INVARIANT"] = "1"
    return env


def gpu_list() -> str:
    try:
        return subprocess.run(
            ["nvidia-smi", "--query-gpu=index,uuid,pci.bus_id,name", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=30, check=False,
        ).stdout  # fmt: skip
    except (OSError, subprocess.SubprocessError) as exc:
        return repr(exc)


def run_phase(
    phase: dict[str, Any],
    args: argparse.Namespace,
    out: Path,
    stop_at: float,
    state: dict[str, Any],
) -> dict[str, Any]:
    """Start every worker of the phase, wait for all, kill stragglers; return their records."""

    records: dict[str, Any] = {}
    children: dict[str, subprocess.Popen[bytes]] = {}
    handles = []
    for worker in phase["workers"]:
        argv = [sys.executable, str(Path(__file__).resolve()), "worker", "--worker",
                worker["id"], "--config", args.config, "--output-dir", str(out), "--deadline",
                f"{stop_at:.3f}", "--evidence", args.evidence, "--expected-evidence-sha256",
                args.expected_evidence_sha256]  # fmt: skip
        copied = None
        if worker.get("cache_from"):
            copied = copy_cache(out, worker["cache_from"], worker["id"])
        env = worker_env(dict(os.environ), out, worker)
        handle = (out / f"worker-{worker['id']}.log").open("w", encoding="utf-8")
        handles.append(handle)
        children[worker["id"]] = subprocess.Popen(
            argv, env=env, stdout=handle, stderr=subprocess.STDOUT, start_new_session=True
        )
        records[worker["id"]] = {"argv": argv, "gpu": worker["gpu"], "started_at": lane.utc_now(),
                                 "t0": time.time(), "cache_copied": copied}  # fmt: skip
    state["children"] = list(children.values())
    done_seen: dict[str, float] = {}
    while any(c.poll() is None for c in children.values()):
        now = time.time()
        for wid, child in children.items():
            if child.poll() is not None:
                continue
            done = out / "sessions" / wid / "done.json"
            if wid not in done_seen and done.is_file():
                done_seen[wid] = now
            hung = wid in done_seen and now - done_seen[wid] > 25
            late = now > stop_at + 90
            after_signal = state["signal_at"] is not None and now - state["signal_at"] > 40
            if hung or late or after_signal:
                records[wid]["killed"] = "hung after done" if hung else "late" if late else "signal"
                with contextlib.suppress(ProcessLookupError):
                    os.killpg(child.pid, signal.SIGKILL)
                child.wait(timeout=30)
        time.sleep(1.0)
    state["children"] = []
    for handle in handles:
        handle.close()
    for wid, child in children.items():
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.killpg(child.pid, signal.SIGKILL)
        record = records[wid]
        record["exit"] = child.returncode
        record["wall_s"] = round(time.time() - record.pop("t0"), 1)
        done = out / "sessions" / wid / "done.json"
        saved = json.loads(done.read_text()) if done.is_file() else None
        record["worker_done"] = saved
        outcome = {0: "complete", 3: "partial", SMOKE_FAILED_EXIT: "smoke-failed"}
        record["status"] = "failed" if saved is None else outcome.get(saved["exit"], "failed")
    release_until = time.time() + 120
    while time.time() < release_until:
        used = s0.gpu_memory_used_mib()
        if not used or max(used) < 1024:
            break
        time.sleep(2.0)
    return records


def identity_summary(out: Path, a: str, b: str) -> dict[str, Any]:
    try:
        ref = load_pass(out / "sessions" / a, "all")
        other = load_pass(out / "sessions" / b, "all")
    except (OSError, ValueError, KeyError) as exc:
        return {"error": repr(exc)}
    result = s0.compare(ref, other, {})
    result.pop("clusters", None)
    result.pop("clusters_all_identical", None)
    return {"ref": a, "other": b} | result


def run_main(args: argparse.Namespace) -> int:
    config = ms.load_config(Path(args.config))
    if list(args.seeds) != config["seeds"]:
        raise ms.StudyError("--seeds must equal the config's declared seeds")
    artifact = load_artifact(Path(args.evidence), args.expected_evidence_sha256)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    stop_at, source = lane.deadline(args.allocation_minutes)
    requests = ms.request_table(artifact, config["pools"]["arms"])
    summary: dict[str, Any] = {
        "experiment_id": config["experiment_id"],
        "claim_level": "exploratory",
        "split": artifact["split"],
        "started_at": lane.utc_now(),
        "allocation_minutes": args.allocation_minutes,
        "deadline_source": source,
        "deadline_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(stop_at)),
        "evidence_sha256": args.expected_evidence_sha256,
        "questions": len(artifact["questions"]),
        "reader_requests": len(requests),
        "gpus": gpu_list(),
        "phases": {},
    }
    lane.write_json(out / "summary.json", summary)
    s0.record_environment(out)
    state: dict[str, Any] = {"children": [], "signal": None, "signal_at": None}

    def on_signal(signum: int, _frame: Any) -> None:
        state["signal"] = signal.Signals(signum).name
        state["signal_at"] = time.time()
        for child in state["children"]:
            if child.poll() is None:
                with contextlib.suppress(ProcessLookupError):
                    os.kill(child.pid, signal.SIGTERM)

    signal.signal(signal.SIGUSR1, on_signal)
    signal.signal(signal.SIGTERM, on_signal)
    verified = {}
    for spec in (config["judge"]["primary"], config["reader"]):
        key = spec["model_id"]
        if key in verified:
            continue
        started = time.time()
        try:
            verified[key] = lane.verify_model(key, spec["receipt_root"])
        except Exception as exc:  # noqa: BLE001 - recorded; nothing runs on an unverified model
            summary["model_verification"] = verified | {key: {"error": repr(exc)}}
            lane.write_json(out / "summary.json", summary)
            return 2
        verified[key]["wall_s"] = round(time.time() - started, 1)
    summary["model_verification"] = verified
    sampler = s0.start_gpu_sampler(out)
    for phase in config["job"]["phases"]:
        remaining = stop_at - time.time()
        record: dict[str, Any] = {}
        summary["phases"][phase["id"]] = record
        done = {
            wid: w.get("status")
            for p in summary["phases"].values()
            for wid, w in p.get("workers", {}).items()
        }
        needed = phase_readers(phase)
        if state["signal"] or remaining < float(phase["min_start_s"]):
            record["status"] = "skipped"
            record["reason"] = state["signal"] or f"remaining {remaining:.0f} s"
            continue
        if any(done.get(r) != "complete" for r in needed):
            record["status"] = "skipped"
            record["reason"] = f"a reader pass it needs is not complete: {needed}"
            continue
        if any(w["kind"] == "judge" for w in phase["workers"]):
            items = write_judge_items(config, artifact, out, needed)
            summary["judge_items"] = {
                "total": len(items),
                "reader": sum(1 for i in items if i["source"] == "reader"),
                "validation": sum(1 for i in items if i["source"] != "reader"),
            }
        record["started_at"] = lane.utc_now()
        record["workers"] = run_phase(phase, args, out, stop_at, state)
        record["status"] = (
            "complete"
            if all(w["status"] == "complete" for w in record["workers"].values())
            else "incomplete"
        )
        lane.write_json(out / "summary.json", summary)
    if sampler is not None:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(sampler.pid, signal.SIGTERM)
    summary["identity"] = {}
    for kind in ("reader", "judge"):
        ids = [w["id"] for p in config["job"]["phases"] for w in p["workers"] if w["kind"] == kind]
        for i, a in enumerate(ids):
            for b in ids[i + 1 :]:
                if kind == "judge" and model_spec(config, worker_spec(config, a)) is not \
                        model_spec(config, worker_spec(config, b)):  # fmt: skip
                    continue
                summary["identity"][f"{a}|{b}"] = identity_summary(out, a, b)
    summary["finished_at"] = lane.utc_now()
    summary["signal"] = state["signal"]
    lane.write_json(out / "summary.json", summary)
    if state["signal"]:
        lane.write_checkpoint_marker(
            "SIGUSR1" if state["signal"] == "SIGUSR1" else "SIGTERM",
            "memcredit study: every finished pass saved; no resume (a rerun is a new job)",
        )
    statuses = [p.get("status") for p in summary["phases"].values()]
    return 0 if all(s == "complete" for s in statuses) else 3


# --------------------------------------------------------------------------- plan and selftest


def build_plan(config: dict[str, Any], artifact: dict[str, Any]) -> dict[str, Any]:
    requests = ms.request_table(artifact, config["pools"]["arms"])
    kinds: dict[str, int] = {}
    for r in requests:
        kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
    return {
        "experiment_id": config["experiment_id"],
        "split": artifact["split"],
        "questions": len(artifact["questions"]),
        "pools": len(artifact["questions"]) * len(config["pools"]["arms"]),
        "reader_requests": len(requests),
        "by_kind": kinds,
        "validation_items": len(ms.validation_items(artifact, config["judge"]["validation"])),
        "phases": [
            {"id": p["id"], "workers": [w["id"] for w in p["workers"]]}
            for p in config["job"]["phases"]
        ],  # fmt: skip
    }


def selftest_main(args: argparse.Namespace) -> int:
    from transformers import AutoTokenizer

    config = ms.load_config(Path(args.config))
    artifact = load_artifact(Path(args.evidence), args.expected_evidence_sha256)
    root = Path(args.model_root)
    report: dict[str, Any] = {"plan": build_plan(config, artifact)}
    reader_tok = AutoTokenizer.from_pretrained(str(root / config["reader"]["model_id"]))
    thinking = bool(config["prompt"]["enable_thinking"])
    lengths = [len(s0.render_prompt_ids(reader_tok, m, thinking))
               for m in reader_messages(config, artifact)]  # fmt: skip
    limit = config["reader"]["engine"]["max_model_len"] - config["reader"]["sampling"]["max_tokens"]
    report["reader_prompts"] = {
        "requests": len(lengths), "len_min": min(lengths), "len_max": max(lengths),
        "len_mean": sum(lengths) / len(lengths), "tokens_total": sum(lengths),
        "fits": max(lengths) <= limit,
        "thinking_disabled": "<think>\n\n</think>" in reader_tok.decode(
            s0.render_prompt_ids(reader_tok, "x", thinking)),
    }  # fmt: skip
    spans_ok = 0
    pools = 0
    for q_index, question in enumerate(artifact["questions"]):
        for arm in config["pools"]["arms"]:
            ids, spans = full_pool_inputs(reader_tok, config, artifact, q_index, arm)
            pools += 1
            ordered = all(a < b for a, b in spans) and all(
                spans[i][1] <= spans[i + 1][0] for i in range(len(spans) - 1)
            )
            spans_ok += int(ordered and len(spans) == len(question["pools"][arm]))
    report["memory_spans"] = {"pools": pools, "ordered_and_complete": spans_ok}
    validation = ms.validation_items(artifact, config["judge"]["validation"])
    fake = {r["index"]: "I don't know." for r in ms.request_table(artifact, config["pools"]["arms"])
            if r["kind"] == "table" and r["mask"] == 0}  # fmt: skip
    items = ms.judge_item_table(artifact, fake, ms.request_table(artifact, config["pools"]["arms"]),
                                validation)  # fmt: skip
    judge_report = {}
    for which in ("primary", "secondary"):
        spec = config["judge"][which]
        tok = AutoTokenizer.from_pretrained(str(root / spec["model_id"]))
        jl = [len(s0.render_prompt_ids(tok, ms.judge_message(artifact, i), False)) for i in items]
        judge_report[which] = {"model_id": spec["model_id"], "items": len(items),
                               "len_max": max(jl), "len_mean": sum(jl) / len(jl),
                               "fits": max(jl) <= spec["engine"]["max_model_len"] - 10}  # fmt: skip
    report["judge_prompts"] = judge_report
    report["parse_judgment"] = [ms.parse_judgment(x) for x in ("yes", "No.", "Yes, it is.")]
    # Attention code on CPU with the smallest Qwen3 (same layer code path, eager attention).
    started = time.time()
    model, tok = load_hf_model(SELFTEST_MODEL, "float32", "cpu", root)
    best = min(
        ((q, a) for q in range(len(artifact["questions"])) for a in config["pools"]["arms"]),
        key=lambda qa: len(full_pool_inputs(tok, config, artifact, qa[0], qa[1])[0]),
    )
    ids, spans = full_pool_inputs(tok, config, artifact, best[0], best[1])
    reply = tok("I don't know.", add_special_tokens=False)["input_ids"]
    probe = AttentionProbe(model)
    mass = probe.run(model, ids + reply[:-1], list(range(len(ids) - 1, len(ids) - 1 + len(reply))),
                     spans)  # fmt: skip
    probe.close()
    total = mass.sum(-1)
    report["attention_selftest"] = {
        "model": SELFTEST_MODEL, "pool": list(best), "prompt_tokens": len(ids),
        "shape": list(mass.shape), "layers": len(model.model.layers),
        "mass_min": float(mass.min()), "mass_max_total": float(total.max()),
        "ok": bool(mass.shape[0] == len(model.model.layers) and mass.min() >= 0
                   and total.max() <= 1.0 + 1e-4 and mass.shape[-1] == len(spans)),
        "wall_s": round(time.time() - started, 1),
    }  # fmt: skip
    try:
        import vllm

        report["vllm_version"] = vllm.__version__
        report["vllm_cited_files_sha256"] = s0.vllm_file_digests(Path(vllm.__file__).parent)
    except Exception as exc:  # noqa: BLE001 - recorded
        report["vllm_import_error"] = repr(exc)
    report["ok"] = bool(
        report["reader_prompts"]["fits"] and report["reader_prompts"]["thinking_disabled"]
        and spans_ok == pools and all(v["fits"] for v in judge_report.values())
        and report["attention_selftest"]["ok"]
    )  # fmt: skip
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    sub = parser.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan", allow_abbrev=False)
    plan.add_argument("--evidence", required=True)
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
    worker.add_argument("--worker", required=True)
    worker.add_argument("--output-dir", required=True)
    worker.add_argument("--deadline", type=float, required=True)
    worker.add_argument("--evidence", required=True)
    worker.add_argument("--expected-evidence-sha256", required=True)
    for sp in sub.choices.values():
        sp.add_argument("--config", default=str(ms.CONFIG_PATH))
    args = parser.parse_args()
    if args.command == "plan":
        config = ms.load_config(Path(args.config))
        print(json.dumps(build_plan(config, load_artifact(Path(args.evidence), None)), indent=2))
        return 0
    if args.command == "selftest":
        return selftest_main(args)
    if args.command == "run":
        return run_main(args)
    return worker_main(args)


if __name__ == "__main__":
    sys.exit(main())
