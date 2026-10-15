#!/usr/bin/env python3
"""AM3 (EXPLORATORY, development split only): does abstention-aware keep selection hold for a
second reader and under the second judge? (D117.)

``am1-keepset-search-v1`` confirmed H-C with the Qwen3-8B reader and the Qwen3-32B judge: the
best-BM25-ranked 4-subset whose reply does not abstain (AM1d's rule and its four abstention
patterns, digest ``031bee27...``) is more accurate than BM25 top 4. AM3 reruns that comparison on
the AM1 development pilot's 63 questions (both pool arms) with new reader passes:

* the anchor, Qwen3-8B in AM1's eager batch-invariant engine, whose labels are checked against the
  pilot's committed tables at the same masks;
* a reader of another family (OLMo-2-1124-7B-Instruct) and Qwen3.5-9B;

each answering, per pool, the 70 4-subsets and the full pool of 8 (71 requests) with AM1's prompt,
greedy, 64 tokens, in its own chat template; and both judges (Qwen3-32B, Qwen3-8B) with
LongMemEval's official answer-check prompt on every distinct (question, reply).

Config: ``experiments/am3/am3-reader-replication-v1.yaml``. The prompt, pools, judges and judge
validation items come unchanged from the pilot's config (SHA-256 pinned).

Subcommands:

* ``plan --evidence A``: requests per reader and in all (CPU).
* ``selftest --evidence A [--model-root M]``: CPU only, no engine. Renders every request with every
  reader's tokenizer and chat template and the judge items with both judges'; checks lengths,
  thinking-off markers and stop tokens; checks that vLLM resolves every reader architecture.
* ``run --seeds 42 43 44 --output-dir D --allocation-minutes M --evidence A
  --expected-evidence-sha256 S``: the GPU job. Verifies every model against its receipt, then
  runs the config's steps one after another on GPU 0, each a fresh worker process.
* ``worker --step ID ...``: one step (a reader or judge pass).
* ``extract --run-dir R --evidence A --private-dir P [--pilot-run-dir ...
  --pilot-eager-run-dir ...]`` (host only; reads reply texts): joins every reader request to both
  judges' labels, flags abstentions, and compares the anchor with the pilot's committed tables and
  raw passes. Writes text-free per-pool features to the host-only private directory.
* ``analyze --features F --output-dir O``: the outcomes, text-free (``results.json``,
  ``per-table.json.gz``, ``tables.md``).

Every path that names held-out data is refused.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import signal
import subprocess
import sys
import threading
import time
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for _path in (PROJECT_ROOT, PROJECT_ROOT / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import memcredit_cost_curve as cc  # noqa: E402  (committed-table decoding)
import memcredit_keepset_search as ks  # noqa: E402  (McNemar, paired readings, reads summary)
import memcredit_label_free as lf  # noqa: E402  (abstention patterns, BM25 order)
import memcredit_step0 as s0  # noqa: E402  (engine streaming, pass files, GPU sampler)

from harness import g2_pilot as lane  # noqa: E402
from harness import memcredit as mc  # noqa: E402
from harness import memcredit_study as ms  # noqa: E402

EXPERIMENT = "am3-reader-replication-v1"
CONFIG_PATH = PROJECT_ROOT / "experiments" / "am3" / "am3-reader-replication-v1.yaml"
MODEL_ROOT = lane.MODEL_ROOT
K = 8
BUDGET = 4
FULL = (1 << K) - 1
FOUR_SETS: tuple[int, ...] = lf.FOUR_SETS
#: The masks each pool is read at, in request order: the 70 4-subsets ascending, then all 8.
REQUEST_MASKS: tuple[int, ...] = (*sorted(FOUR_SETS), FULL)
ARMS = ("retrieved", "gold")
JUDGES = ("primary", "secondary")
JUDGE_STEP = {"primary": "judge32", "secondary": "judge8"}
SMOKE_REQUESTS = 16
SMOKE_FAILED_EXIT = 4
#: Path parts that mark held-out data or runs; AM3 never opens a path containing one.
FORBIDDEN_PARTS = ("am1-confirmatory", "am1-memory-credit-v1", "am1-keepset-search-v1")
READINGS = ("HELPS", "HURTS", "NOT_SEPARATED")


class Am3Error(ValueError):
    """The AM3 config, its inputs or its outputs are invalid."""


# --------------------------------------------------------------------------- config and inputs


def check_path(path: Path | str) -> None:
    """Refuse held-out data before anything is opened (symlinks resolved)."""

    for candidate in (str(path), str(Path(path).resolve())):
        for part in FORBIDDEN_PARTS:
            if part in candidate:
                raise Am3Error(f"AM3 reads development data only; refusing {path}")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(config, dict) or config.get("experiment_id") != EXPERIMENT:
        raise Am3Error(f"not an {EXPERIMENT} config")
    if config.get("claim_level") != "exploratory":
        raise Am3Error("AM3 is exploratory")
    if config.get("seeds") != [42, 43, 44]:
        raise Am3Error("seeds must be [42, 43, 44]")
    req = config["requests"]
    if int(req["pool_size"]) != K or int(req["budget"]) != BUDGET:
        raise Am3Error("AM3 reads 4-subsets of pools of 8")
    pilot = load_pilot_config(config)
    readers = config["readers"]
    ids = [r["id"] for r in readers]
    if len(set(ids)) != len(ids):
        raise Am3Error("reader ids must be unique")
    anchors = [r for r in readers if r.get("role") == "anchor"]
    if len(anchors) != 1 or anchors[0]["model_id"] != pilot["reader"]["model_id"]:
        raise Am3Error("exactly one anchor reader, the pilot's reader")
    anchor = anchors[0]
    if (
        anchor["engine"] != pilot["reader"]["engine"]
        or anchor["revision"] != pilot["reader"]["revision"]
    ):
        raise Am3Error("the anchor's engine and revision must be the pilot reader's")
    if config["reader_sampling"] != pilot["reader"]["sampling"]:
        raise Am3Error("reader sampling must be the pilot reader's (greedy, 64 tokens)")
    for r in readers:
        for key in ("model_id", "revision", "receipt_root", "stop_token", "engine"):
            if not r.get(key):
                raise Am3Error(f"reader {r['id']}: {key} is required")
        if not isinstance(r.get("enable_thinking"), bool):
            raise Am3Error(f"reader {r['id']}: enable_thinking must be a boolean")
    steps = config["job"]["steps"]
    step_ids = [s["id"] for s in steps]
    if len(set(step_ids)) != len(step_ids):
        raise Am3Error("step ids must be unique")
    if int(config["job"]["gpus"]) != 1:
        raise Am3Error("the AM3 job runs on one GPU")
    seen: list[str] = []
    for s in steps:
        if s["kind"] == "reader":
            if s["reader"] not in ids:
                raise Am3Error(f"{s['id']}: unknown reader")
        elif s["kind"] == "judge":
            if s["judge"] not in JUDGES:
                raise Am3Error(f"{s['id']}: judge must be primary or secondary")
            if s["id"] != JUDGE_STEP[s["judge"]]:
                raise Am3Error(
                    f"{s['id']}: the {s['judge']} judge's step is {JUDGE_STEP[s['judge']]}"
                )
        else:
            raise Am3Error(f"{s['id']}: unknown step kind")
        for key in ("batch_invariant", "enforce_eager"):
            if not isinstance(s.get(key), bool):
                raise Am3Error(f"{s['id']}: {key} must be a boolean")
        other = s.get("only_if_incomplete")
        if other is not None:
            prior = next((p for p in steps if p["id"] == other), None)
            if other not in seen or prior is None or prior.get("reader") != s.get("reader"):
                raise Am3Error(f"{s['id']}: only_if_incomplete names no earlier step of its reader")
        seen.append(s["id"])
    if anchor["id"] not in {s.get("reader") for s in steps}:
        raise Am3Error("the anchor reader has no step")
    for s in steps:
        if s.get("reader") == anchor["id"] and not (s["batch_invariant"] and s["enforce_eager"]):
            raise Am3Error("the anchor runs eager and batch-invariant only")
    return config


def load_pilot_config(config: dict[str, Any]) -> dict[str, Any]:
    spec = config["pilot"]
    path = PROJECT_ROOT / spec["config"]
    if sha256_file(path) != spec["config_sha256"]:
        raise Am3Error("the pilot config differs from its pinned SHA-256")
    pilot = ms.load_config(path)
    if pilot["experiment_id"] != ms.EXPERIMENT_ID or pilot["claim_level"] != "exploratory":
        raise Am3Error("AM3 takes its prompt and judges from the development pilot's config")
    if tuple(pilot["pools"]["arms"]) != ARMS:
        raise Am3Error("the pilot's arms are retrieved and gold")
    return pilot


def load_artifact(
    path: Path, expected_sha256: str | None, config: dict[str, Any], pilot: dict[str, Any]
) -> dict[str, Any]:
    """The pilot's development study artifact, and only it."""

    check_path(path)
    raw = path.read_bytes()
    digest = mc.sha256_bytes(raw)
    if digest != config["pilot"]["study_artifact_sha256"]:
        raise Am3Error("the study artifact is not the development pilot's")
    if expected_sha256 is not None and digest != expected_sha256:
        raise Am3Error("the study artifact differs from the expected SHA-256")
    artifact = json.loads(raw)
    if artifact.get("experiment_id") != ms.EXPERIMENT_ID or artifact.get("split") != "development":
        raise Am3Error("AM3 runs the development split only")
    for q in artifact["questions"]:
        for arm in ARMS:
            if len(q["pools"][arm]) != K:
                raise Am3Error(f"{q['question_id']}:{arm}: not a pool of {K}")
    return artifact


def reader_spec(config: dict[str, Any], reader_id: str) -> dict[str, Any]:
    for r in config["readers"]:
        if r["id"] == reader_id:
            return r
    raise Am3Error(f"unknown reader {reader_id}")


def step_spec(config: dict[str, Any], step_id: str) -> dict[str, Any]:
    for s in config["job"]["steps"]:
        if s["id"] == step_id:
            return s
    raise Am3Error(f"unknown step {step_id}")


def model_spec(config: dict[str, Any], pilot: dict[str, Any], step: dict[str, Any]) -> dict:
    """model_id, revision, receipt_root, engine and the chat settings of a step's model."""

    if step["kind"] == "reader":
        r = reader_spec(config, step["reader"])
        return {
            "model_id": r["model_id"],
            "revision": r["revision"],
            "receipt_root": r["receipt_root"],
            "engine": r["engine"],
            "enable_thinking": bool(r["enable_thinking"]),
            "stop_token": r["stop_token"],
            "sampling": config["reader_sampling"],
        }
    j = pilot["judge"][step["judge"]]
    return {
        "model_id": j["model_id"],
        "revision": j["revision"],
        "receipt_root": j["receipt_root"],
        "engine": j["engine"],
        "enable_thinking": bool(pilot["judge"]["enable_thinking"]),
        "stop_token": s0.END_OF_TURN,
        "sampling": pilot["judge"]["sampling"],
    }


# --------------------------------------------------------------------------- requests


def request_table(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    """Every (question, arm, mask) request in canonical order: question, arm (retrieved, gold),
    then the 70 4-subset masks ascending and the full pool."""

    table: list[dict[str, Any]] = []
    for q_index, question in enumerate(artifact["questions"]):
        for arm in ARMS:
            for mask in REQUEST_MASKS:
                table.append(
                    {"index": len(table), "question_index": q_index,
                     "question_id": question["question_id"], "arm": arm, "kind": "table",
                     "mask": mask}
                )  # fmt: skip
    return table


def reader_messages(pilot: dict[str, Any], artifact: dict[str, Any]) -> list[str]:
    return [ms.request_message(artifact, r, pilot["prompt"]) for r in request_table(artifact)]


def reader_steps_complete(summary: dict[str, Any]) -> list[str]:
    """The reader steps whose passes completed, in step order."""

    return [
        sid
        for sid, rec in summary.get("steps", {}).items()
        if rec.get("kind") == "reader" and rec.get("status") == "complete"
    ]


def judge_items(
    artifact: dict[str, Any],
    pilot: dict[str, Any],
    passes: dict[str, dict[int, str]],
) -> list[dict[str, Any]]:
    """Every distinct (question, stripped reply) over the given reader passes (step id -> request
    index -> reply text), then the pilot's validation items, in the pilot's canonical order."""

    requests = request_table(artifact)
    n = len(requests)
    replies: dict[int, str] = {}
    extended: list[dict[str, Any]] = []
    for k, step_id in enumerate(sorted(passes)):
        for index, text in passes[step_id].items():
            replies[k * n + index] = text
        extended += [dict(r, index=k * n + r["index"]) for r in requests]
    validation = ms.validation_items(artifact, pilot["judge"]["validation"])
    return ms.judge_item_table(artifact, replies, extended, validation)


def completed_replies(passed: dict[str, Any]) -> dict[int, str]:
    return {
        i: row["text"]
        for i, row in passed["rows"].items()
        if row["finish"] in ("stop", "length") and row["text"] is not None
    }


def load_pass(session_dir: Path, name: str = "all") -> dict[str, Any]:
    import memcredit_study as driver

    check_path(session_dir)
    return driver.load_pass(session_dir, name)


# --------------------------------------------------------------------------- vLLM worker


def engine_kwargs(spec: dict[str, Any], seed: int, enforce_eager: bool) -> dict[str, Any]:
    model_dir = MODEL_ROOT / spec["model_id"]
    engine = spec["engine"]
    kwargs: dict[str, Any] = {"enforce_eager": True} if enforce_eager else {}
    kwargs |= {
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
    if "limit_mm_per_prompt" in engine:
        kwargs["limit_mm_per_prompt"] = dict(engine["limit_mm_per_prompt"])
    return kwargs


def stop_token_id(tokenizer: Any, token: str) -> int:
    """The single id of a stop token; refuses an unknown or split token."""

    ids = tokenizer(token, add_special_tokens=False)["input_ids"]
    if len(ids) != 1 or tokenizer.convert_ids_to_tokens(int(ids[0])) != token:
        raise Am3Error(f"{token!r} is not a single token of this tokenizer")
    return int(ids[0])


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


def vllm_worker(args: argparse.Namespace) -> int:
    import vllm.envs as vllm_envs
    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams
    from vllm.inputs import TokensPrompt

    config = load_config(Path(args.config))
    pilot = load_pilot_config(config)
    artifact = load_artifact(Path(args.evidence), args.expected_evidence_sha256, config, pilot)
    step = step_spec(config, args.step)
    out = Path(args.output_dir) / "sessions" / step["id"]
    out.mkdir(parents=True, exist_ok=True)
    flag = s0.StopFlag()
    signal.signal(signal.SIGTERM, flag.handler)
    signal.signal(signal.SIGUSR1, flag.handler)
    log_path = out / "worker-progress.jsonl"

    def log(event: str, **fields: Any) -> None:
        record = {"utc": lane.utc_now(), "event": event, "step": step["id"], **fields}
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        print(json.dumps(record, sort_keys=True), flush=True)

    def finish(code: int, **record: Any) -> None:
        lane.write_json(out / "session.json", {"step": step, "exit": code, **record})
        lane.write_json(out / "done.json", {"exit": code, "utc": lane.utc_now()})
        sys.stdout.flush()

    spec = model_spec(config, pilot, step)
    model_dir = MODEL_ROOT / spec["model_id"]
    tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
    if step["kind"] == "reader":
        messages = reader_messages(pilot, artifact)
    else:
        items = json.loads((Path(args.output_dir) / "judge-items.json").read_text("utf-8"))
        messages = [ms.judge_message(artifact, item) for item in items]
    prompt_ids = [s0.render_prompt_ids(tokenizer, m, spec["enable_thinking"]) for m in messages]
    prompt_lens = [len(p) for p in prompt_ids]
    stop_id = stop_token_id(tokenizer, spec["stop_token"])
    kwargs = engine_kwargs(spec, int(config["seeds"][0]), bool(step["enforce_eager"]))
    want_bi = bool(step["batch_invariant"])
    log("engine-start", engine_kwargs=kwargs, gpu=gpu_identity(), model_id=spec["model_id"],
        env_batch_invariant=os.environ.get("VLLM_BATCH_INVARIANT"),
        vllm_envs_batch_invariant=bool(vllm_envs.VLLM_BATCH_INVARIANT),
        prompt_ids_sha256=s0.prompt_digest(prompt_ids), requests=len(prompt_ids),
        prompt_len_min=min(prompt_lens), prompt_len_max=max(prompt_lens),
        prompt_tokens_total=sum(prompt_lens), stop_token_id=stop_id)  # fmt: skip
    if bool(vllm_envs.VLLM_BATCH_INVARIANT) != want_bi:
        log("mode-mismatch", wanted_batch_invariant=want_bi)
        finish(2, reason="mode mismatch")
        os._exit(2)
    t0 = time.time()
    try:
        llm = LLM(**kwargs)
    except Exception as exc:  # noqa: BLE001 - recorded; the driver may run a fallback step
        log("engine-failed", error=repr(exc)[:2000], init_s=round(time.time() - t0, 1))
        finish(5, reason="engine failed", error=repr(exc)[:2000], engine_kwargs=kwargs)
        os._exit(5)
    init_s = round(time.time() - t0, 1)
    log("engine-ready", init_s=init_s)
    engine = llm.llm_engine
    base = {"n": 1, "temperature": spec["sampling"]["temperature"],
            "max_tokens": spec["sampling"]["max_tokens"],
            "logprobs": spec["sampling"]["logprobs"]}  # fmt: skip
    order = list(range(len(prompt_ids)))
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
        ids = [f"{step['id']}/{name}/{i}" for i in indices]
        batch = [
            (ours, TokensPrompt(prompt_token_ids=prompt_ids[i]),
             SamplingParams(**base, stop_token_ids=[stop_id]))
            for ours, i in zip(ids, indices, strict=True)
        ]  # fmt: skip
        log("pass-start", name=name, requests=len(batch), prefix_cache_reset=reset)
        stop_at = min(args.deadline, time.time() + float(step["max_s"]))
        state, info = s0.stream_requests(engine, batch, stop_at, flag, None)
        record = {
            "session": step["id"],
            "name": name,
            "batch_invariant": want_bi,
            "enforce_eager": bool(step["enforce_eager"]),
            "kind": step["kind"],
            "model_id": spec["model_id"],
            "sampling": "greedy",
            "sampling_kwargs": base,
            "stop_token_id": stop_id,
            "order": "canonical",
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
    finish(code, engine_kwargs=kwargs, init_s=init_s, passes=passes,
           prompt_ids_sha256=s0.prompt_digest(prompt_ids), gpu=gpu_identity())  # fmt: skip
    closer = threading.Thread(target=lambda: engine.engine_core.shutdown(), daemon=True)
    closer.start()
    closer.join(timeout=15)
    sys.stdout.flush()
    os._exit(code)


# --------------------------------------------------------------------------- driver


def worker_env(base: dict[str, str], out: Path, step: dict[str, Any]) -> dict[str, str]:
    env = dict(base)
    for key, sub in s0.CACHE_DIRS.items():
        path = out / "cache" / step["id"] / sub
        path.mkdir(parents=True, exist_ok=True)
        env[key] = str(path)
    env.update(s0.FIXED_ENV)
    env["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
    env["CUDA_VISIBLE_DEVICES"] = "0"
    env.pop("VLLM_BATCH_INVARIANT", None)
    if step["batch_invariant"]:
        env["VLLM_BATCH_INVARIANT"] = "1"
    return env


def run_step(
    step: dict[str, Any], args: argparse.Namespace, out: Path, stop_at: float,
    state: dict[str, Any],
) -> dict[str, Any]:  # fmt: skip
    """Start one worker, wait for it, kill it when hung or late; return its record."""

    argv = [sys.executable, str(Path(__file__).resolve()), "worker", "--step", step["id"],
            "--config", args.config, "--output-dir", str(out), "--deadline", f"{stop_at:.3f}",
            "--evidence", args.evidence, "--expected-evidence-sha256",
            args.expected_evidence_sha256]  # fmt: skip
    env = worker_env(dict(os.environ), out, step)
    record: dict[str, Any] = {"kind": step["kind"], "argv": argv, "started_at": lane.utc_now(),
                              "batch_invariant": step["batch_invariant"],
                              "enforce_eager": step["enforce_eager"]}  # fmt: skip
    if step["kind"] == "reader":
        record["reader"] = step["reader"]
    t0 = time.time()
    with (out / f"worker-{step['id']}.log").open("w", encoding="utf-8") as handle:
        child = subprocess.Popen(
            argv, env=env, stdout=handle, stderr=subprocess.STDOUT, start_new_session=True
        )
        state["children"] = [child]
        done = out / "sessions" / step["id"] / "done.json"
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
            time.sleep(1.0)
        state["children"] = []
    with contextlib.suppress(ProcessLookupError, PermissionError):
        os.killpg(child.pid, signal.SIGKILL)
    record["exit"] = child.returncode
    record["wall_s"] = round(time.time() - t0, 1)
    saved = json.loads(done.read_text()) if done.is_file() else None
    record["worker_done"] = saved
    outcome = {0: "complete", 3: "partial", SMOKE_FAILED_EXIT: "smoke-failed", 5: "engine-failed"}
    record["status"] = "failed" if saved is None else outcome.get(saved["exit"], "failed")
    release_until = time.time() + 120
    while time.time() < release_until:
        used = s0.gpu_memory_used_mib()
        if not used or max(used) < 1024:
            break
        time.sleep(2.0)
    return record


def driver_gpu_list() -> str:
    import memcredit_study as driver

    return driver.gpu_list()


def run_main(args: argparse.Namespace) -> int:
    config = load_config(Path(args.config))
    pilot = load_pilot_config(config)
    if list(args.seeds) != config["seeds"]:
        raise Am3Error("--seeds must equal the config's declared seeds")
    artifact = load_artifact(Path(args.evidence), args.expected_evidence_sha256, config, pilot)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    stop_at, source = lane.deadline(args.allocation_minutes)
    summary: dict[str, Any] = {
        "experiment_id": config["experiment_id"],
        "claim_level": config["claim_level"],
        "split": artifact["split"],
        "started_at": lane.utc_now(),
        "allocation_minutes": args.allocation_minutes,
        "deadline_source": source,
        "deadline_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(stop_at)),
        "evidence_sha256": args.expected_evidence_sha256,
        "questions": len(artifact["questions"]),
        "reader_requests_per_reader": len(request_table(artifact)),
        "gpus": driver_gpu_list(),
        "steps": {},
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
    verified: dict[str, Any] = {}
    specs = [model_spec(config, pilot, s) for s in config["job"]["steps"]]
    for spec in sorted(specs, key=lambda s: s["model_id"] != pilot["judge"]["primary"]["model_id"]):
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
        if verified[key].get("revision") != spec["revision"]:
            summary["model_verification"] = verified | {key: {"error": "revision differs"}}
            lane.write_json(out / "summary.json", summary)
            return 2
        verified[key]["wall_s"] = round(time.time() - started, 1)
    summary["model_verification"] = verified
    lane.write_json(out / "summary.json", summary)
    sampler = s0.start_gpu_sampler(out)
    for step in config["job"]["steps"]:
        record: dict[str, Any] = {"kind": step["kind"]}
        summary["steps"][step["id"]] = record
        prior = step.get("only_if_incomplete")
        remaining = stop_at - time.time()
        if prior is not None and summary["steps"].get(prior, {}).get("status") == "complete":
            record.update(status="not-needed", reason=f"{prior} completed")
            continue
        if state["signal"] or remaining < float(step["min_start_s"]):
            record.update(
                status="skipped", reason=state["signal"] or f"remaining {remaining:.0f} s"
            )
            continue
        if step["kind"] == "judge":
            sources = reader_steps_complete(summary)
            if not sources:
                record.update(status="skipped", reason="no reader pass completed")
                continue
            if not (out / "judge-items.json").is_file():
                passes = {
                    sid: completed_replies(load_pass(out / "sessions" / sid)) for sid in sources
                }
                items = judge_items(artifact, pilot, passes)
                lane.write_json(out / "judge-items.json", items)
                summary["judge_items"] = {
                    "from": sources,
                    "total": len(items),
                    "reader": sum(1 for i in items if i["source"] == "reader"),
                    "validation": sum(1 for i in items if i["source"] != "reader"),
                }
        record.update(run_step(step, args, out, stop_at, state))
        lane.write_json(out / "summary.json", summary)
    if sampler is not None:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(sampler.pid, signal.SIGTERM)
    summary["finished_at"] = lane.utc_now()
    summary["signal"] = state["signal"]
    lane.write_json(out / "summary.json", summary)
    if state["signal"]:
        lane.write_checkpoint_marker(
            "SIGUSR1" if state["signal"] == "SIGUSR1" else "SIGTERM",
            "memcredit AM3: every finished pass saved; no resume (a rerun is a new job)",
        )
    readers_done = {summary["steps"][s].get("reader") for s in reader_steps_complete(summary)}
    judges_done = all(
        summary["steps"].get(JUDGE_STEP[j], {}).get("status") == "complete" for j in JUDGES
    )
    all_readers = {r["id"] for r in config["readers"]}
    return 0 if readers_done == all_readers and judges_done else 3


# --------------------------------------------------------------------------- plan and selftest


def build_plan(config: dict[str, Any], artifact: dict[str, Any]) -> dict[str, Any]:
    n = len(request_table(artifact))
    return {
        "experiment_id": config["experiment_id"],
        "split": artifact["split"],
        "questions": len(artifact["questions"]),
        "pools": len(artifact["questions"]) * len(ARMS),
        "requests_per_pool": len(REQUEST_MASKS),
        "requests_per_reader": n,
        "readers": [r["id"] for r in config["readers"]],
        "steps": [s["id"] for s in config["job"]["steps"]],
    }


def selftest_main(args: argparse.Namespace) -> int:
    from transformers import AutoTokenizer

    config = load_config(Path(args.config))
    pilot = load_pilot_config(config)
    artifact = load_artifact(Path(args.evidence), args.expected_evidence_sha256, config, pilot)
    root = Path(args.model_root)
    report: dict[str, Any] = {"plan": build_plan(config, artifact), "readers": {}}
    messages = reader_messages(pilot, artifact)
    limit_tokens = config["reader_sampling"]["max_tokens"]
    ok = True
    for r in config["readers"]:
        tok = AutoTokenizer.from_pretrained(str(root / r["model_id"]))
        ids = [s0.render_prompt_ids(tok, m, bool(r["enable_thinking"])) for m in messages]
        lengths = [len(x) for x in ids]
        probe = tok.decode(s0.render_prompt_ids(tok, "x", bool(r["enable_thinking"])))
        marker = r.get("thinking_marker")
        try:
            stop = stop_token_id(tok, r["stop_token"])
            stop_error = None
        except Am3Error as exc:
            stop, stop_error = None, str(exc)
        model_config = json.loads((root / r["model_id"] / "config.json").read_text("utf-8"))
        entry = {
            "requests": len(ids),
            "len_min": min(lengths),
            "len_max": max(lengths),
            "len_mean": sum(lengths) / len(lengths),
            "tokens_total": sum(lengths),
            "fits": max(lengths) <= r["engine"]["max_model_len"] - limit_tokens,
            "thinking_marker_ok": marker is None or marker in probe,
            "no_think_tag_when_unmarked": marker is not None or "<think>" not in probe,
            "stop_token_id": stop,
            "stop_token_error": stop_error,
            "prompt_ids_sha256": s0.prompt_digest(ids),
            "architectures": model_config.get("architectures"),
            "probe_prefix_tokens": ids[0][:8],
        }
        entry["ok"] = bool(
            entry["fits"]
            and entry["thinking_marker_ok"]
            and entry["no_think_tag_when_unmarked"]
            and stop is not None
        )
        ok &= entry["ok"]
        report["readers"][r["id"]] = entry
    fake_passes = {
        "selftest": {
            r["index"]: "I don't know." for r in request_table(artifact) if r["mask"] == FULL
        }
    }
    items = judge_items(artifact, pilot, fake_passes)
    report["judges"] = {}
    for which in JUDGES:
        spec = pilot["judge"][which]
        tok = AutoTokenizer.from_pretrained(str(root / spec["model_id"]))
        lengths = [len(s0.render_prompt_ids(tok, ms.judge_message(artifact, i), False))
                   for i in items]  # fmt: skip
        fits = (
            max(lengths)
            <= spec["engine"]["max_model_len"] - pilot["judge"]["sampling"]["max_tokens"]
        )
        report["judges"][which] = {"model_id": spec["model_id"], "items": len(items),
                                   "len_max": max(lengths), "fits": fits}  # fmt: skip
        ok &= fits
    try:
        import transformers
        import vllm
        from vllm.model_executor.models import registry as vreg

        report["vllm_version"] = vllm.__version__
        report["transformers_version"] = transformers.__version__
        supported = set(vreg.ModelRegistry.get_supported_archs())
        transformers_backend = set(getattr(vreg, "_TRANSFORMERS_SUPPORTED_MODELS", {}))
        archs = {}
        for rid, entry in report["readers"].items():
            for arch in entry["architectures"] or []:
                archs[arch] = {
                    "reader": rid,
                    "supported": arch in supported,
                    "transformers_backend": arch in transformers_backend,
                    "in_transformers": hasattr(transformers, arch),
                }
        report["architectures"] = archs
        ok &= all(a["supported"] for a in archs.values())
        ok &= all(a["in_transformers"] for a in archs.values() if a["transformers_backend"])
        report["vllm_cited_files_sha256"] = s0.vllm_file_digests(Path(vllm.__file__).parent)
    except Exception as exc:  # noqa: BLE001 - recorded
        report["vllm_import_error"] = repr(exc)
        ok = False
    report["ok"] = bool(ok)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if ok else 1


# --------------------------------------------------------------------------- extract (host)


def labels_from_pass(passed: dict[str, Any] | None) -> dict[int, int]:
    if passed is None:
        return {}
    out = {}
    for index, row in passed["rows"].items():
        if row["finish"] in ("stop", "length") and row["text"] is not None:
            out[index] = ms.parse_judgment(row["text"])[0]
    return out


def pool_records(
    artifact: dict[str, Any],
    reader_rows: dict[int, dict[str, Any]],
    item_of: dict[tuple[int, str], int],
    labels: dict[str, dict[int, int]],
) -> list[dict[str, Any]]:
    """Per pool of one reader pass: per requested mask the judged labels, the abstention flag and
    pattern, the finish reason, the token count and the normalized reply's SHA-256. No text."""

    pools: dict[tuple[int, str], dict[str, Any]] = {}
    for r in request_table(artifact):
        key = (int(r["question_index"]), r["arm"])
        q = artifact["questions"][key[0]]
        if key not in pools:
            pool = q["pools"][r["arm"]]
            pools[key] = {
                "question_id": q["question_id"],
                "question_type": q["question_type"],
                "arm": r["arm"],
                "bm25_rank": [int(m["bm25_rank"]) for m in pool],
                "gold_mask": sum(1 << i for i, m in enumerate(pool) if m["is_gold"]),
                "masks": {},
            }
        row = reader_rows.get(r["index"])
        text = row["text"] if row and row["finish"] in ("stop", "length") else None
        cell: dict[str, Any] = {"finish": row["finish"] if row else None}
        if text is None:
            cell.update(u={j: None for j in JUDGES}, abstain=None, pattern=None, digest=None)
        else:
            item = item_of.get((key[0], text.strip()))
            cell["u"] = {j: (labels[j].get(item) if item is not None else None) for j in JUDGES}
            cell["abstain"], cell["pattern"] = lf.abstention(text)
            normalized = mc.normalize_answer(text.strip())
            cell["digest"] = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
            cell["n_tokens"] = len(row["tokens"])
        pools[key]["masks"][int(r["mask"])] = cell
    return [pools[k] for k in sorted(pools)]


def complete_pool(pool: dict[str, Any]) -> bool:
    return sorted(pool["masks"]) == sorted(REQUEST_MASKS) and all(
        c["abstain"] is not None and all(c["u"][j] is not None for j in JUDGES)
        for c in pool["masks"].values()
    )


def anchor_vs_tables(
    pools: Sequence[dict[str, Any]], tables: Sequence[dict[str, Any]]
) -> dict[str, Any]:
    """The anchor's primary-judge labels against the pilot's committed tables (values_hex, bit m
    is u(mask m)) at the 71 requested masks."""

    by_key = {(t["question_id"], t["arm"]): cc.decode_values(t["values_hex"]) for t in tables}
    cells = same = 0
    tables_any = 0
    per_arm: dict[str, dict[str, int]] = {a: {"cells": 0, "same": 0, "tables_any": 0} for a in ARMS}
    differ_masks: list[dict[str, Any]] = []
    for p in pools:
        values = by_key[(p["question_id"], p["arm"])]
        any_diff = False
        for mask in REQUEST_MASKS:
            u = p["masks"][mask]["u"]["primary"]
            cells += 1
            per_arm[p["arm"]]["cells"] += 1
            if u is not None and float(u) == values[mask]:
                same += 1
                per_arm[p["arm"]]["same"] += 1
            else:
                any_diff = True
                differ_masks.append({"question_id": p["question_id"], "arm": p["arm"],
                                     "mask": mask, "pilot": values[mask], "anchor": u})  # fmt: skip
        tables_any += any_diff
        per_arm[p["arm"]]["tables_any"] += any_diff
    return {
        "pools": len(pools),
        "cells": cells,
        "cells_same_label": same,
        "agreement": same / cells if cells else None,
        "ci95": list(mc.clopper_pearson(same, cells)) if cells else None,
        "tables_with_any_difference": tables_any,
        "per_arm": per_arm,
        "differing_cells": differ_masks,
    }


def anchor_vs_pass(
    artifact: dict[str, Any],
    anchor_rows: dict[int, dict[str, Any]],
    anchor_labels: dict[str, dict[int, int]],
    anchor_item_of: dict[tuple[int, str], int],
    pilot_rows: dict[int, dict[str, Any]],
    pilot_labels: dict[str, dict[int, int]],
    pilot_item_of: dict[tuple[int, str], int],
    question_limit: int | None = None,
) -> dict[str, Any]:
    """Request by request at the same (question, arm, mask): identical reply tokens, identical
    tokens and log-prob bits, identical text; and, per judge, label agreement over all cells and
    over the cells whose replies are identical (the judges' own replay)."""

    pilot_index = {
        (r["question_index"], r["arm"], r["mask"]): r["index"]
        for r in ms.request_table(artifact, ARMS)
        if r["kind"] == "table"
    }
    out: dict[str, Any] = {"compared": 0, "identical_tokens": 0, "identical_bits": 0,
                           "identical_text": 0}  # fmt: skip
    for j in JUDGES:
        out[f"label_same_{j}"] = 0
        out[f"label_compared_{j}"] = 0
        out[f"label_same_identical_reply_{j}"] = 0
        out[f"label_compared_identical_reply_{j}"] = 0
    for r in request_table(artifact):
        if question_limit is not None and r["question_index"] >= question_limit:
            continue
        a = anchor_rows.get(r["index"])
        b = pilot_rows.get(pilot_index[(r["question_index"], r["arm"], r["mask"])])
        done = ("stop", "length")
        if a is None or b is None or a["finish"] not in done or b["finish"] not in done:
            continue
        out["compared"] += 1
        same_tok = a["tokens"] == b["tokens"] and a["finish"] == b["finish"]
        out["identical_tokens"] += same_tok
        out["identical_bits"] += same_tok and a["bits"] == b["bits"]
        same_text = a["text"] == b["text"]
        out["identical_text"] += same_text
        for j in JUDGES:
            if pilot_labels.get(j) is None:
                continue
            la = anchor_labels[j].get(anchor_item_of.get((r["question_index"], a["text"].strip())))
            lb = pilot_labels[j].get(pilot_item_of.get((r["question_index"], b["text"].strip())))
            if la is None or lb is None:
                continue
            out[f"label_compared_{j}"] += 1
            out[f"label_same_{j}"] += la == lb
            if same_text:
                out[f"label_compared_identical_reply_{j}"] += 1
                out[f"label_same_identical_reply_{j}"] += la == lb
    return out


def item_index(items: Sequence[dict[str, Any]]) -> dict[tuple[int, str], int]:
    return {
        (i["question_index"], i["response"]): i["index"] for i in items if i["source"] == "reader"
    }


def validation_summary(
    items: Sequence[dict[str, Any]], labels: dict[str, dict[int, int]]
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for j in JUDGES:
        cell: dict[str, Any] = {}
        for source in ("validation:reference", "validation:idk", "validation:other-answer"):
            chosen = [i for i in items if i["source"] == source]
            if source == "validation:reference":
                chosen = [i for i in chosen if i["question_type"] != "single-session-preference"]
            got = [labels[j].get(i["index"]) for i in chosen]
            cell[source] = {"items": len(chosen), "yes": sum(1 for g in got if g == 1),
                            "missing": sum(1 for g in got if g is None)}  # fmt: skip
        out[j] = cell
    return out


def cmd_extract(args: argparse.Namespace) -> dict[str, Any]:
    import memcredit_analyze as ma

    for p in (args.run_dir, args.evidence, args.private_dir, args.pilot_run_dir,
              args.pilot_eager_run_dir):  # fmt: skip
        if p is not None:
            check_path(p)
    config = load_config(Path(args.config))
    pilot = load_pilot_config(config)
    artifact = load_artifact(Path(args.evidence), None, config, pilot)
    run_dir = Path(args.run_dir)
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    items = json.loads((run_dir / "judge-items.json").read_text(encoding="utf-8"))
    labels = {j: labels_from_pass(load_pass(run_dir / "sessions" / JUDGE_STEP[j])) for j in JUDGES}
    item_of = item_index(items)
    readers: dict[str, Any] = {}
    rows_of: dict[str, dict[int, dict[str, Any]]] = {}
    for sid in reader_steps_complete(summary):
        reader_id = summary["steps"][sid]["reader"]
        if reader_id in readers:
            raise Am3Error(f"two completed passes of {reader_id}")
        passed = load_pass(run_dir / "sessions" / sid)
        rows_of[reader_id] = passed["rows"]
        pools = pool_records(artifact, passed["rows"], item_of, labels)
        finish = Counter(c["finish"] for p in pools for c in p["masks"].values())
        readers[reader_id] = {
            "step": sid,
            "batch_invariant": summary["steps"][sid]["batch_invariant"],
            "enforce_eager": summary["steps"][sid]["enforce_eager"],
            "pass_sha256": {
                f"sessions/{sid}/{f}": sha256_file(run_dir / "sessions" / sid / f)
                for f in ("all.json", "all.npz", "all.texts.jsonl.gz")
            },
            "requests": len(passed["rows"]),
            "finish": dict(sorted(finish.items(), key=lambda kv: str(kv[0]))),
            "missing_logprobs": passed["meta"].get("missing_logprobs"),
            "pools_complete": sum(complete_pool(p) for p in pools),
            "pools": pools,
        }
    validation = {
        "judge_items": len(items),
        "judge_items_reader": sum(1 for i in items if i["source"] == "reader"),
        "labelled": {j: len(labels[j]) for j in JUDGES},
        "judge_validation": validation_summary(items, labels),
        "judge_pass_sha256": {
            f"sessions/{JUDGE_STEP[j]}/{f}": sha256_file(run_dir / "sessions" / JUDGE_STEP[j] / f)
            for j in JUDGES
            for f in ("all.json", "all.npz", "all.texts.jsonl.gz")
        },
        "judge_items_sha256": sha256_file(run_dir / "judge-items.json"),
    }
    anchor = next(r for r in config["readers"] if r.get("role") == "anchor")["id"]
    comparisons: dict[str, Any] = {}
    if anchor in readers:
        tables_path = PROJECT_ROOT / config["pilot"]["tables"]
        tables = cc.load_tables(tables_path, config["pilot"]["tables_sha256"])
        comparisons["tables"] = anchor_vs_tables(readers[anchor]["pools"], tables)
        if args.pilot_run_dir:
            p_dir = Path(args.pilot_run_dir)
            ks.check_digests(p_dir, lf.MAIN_PASS["sha256"])
            p_reader = load_pass(p_dir / "sessions" / lf.MAIN_PASS["reader"])
            p_items = json.loads((p_dir / "judge-items.json").read_text(encoding="utf-8"))
            p_labels = {
                "primary": labels_from_pass(load_pass(p_dir / "sessions" / "judge32-gpu0")),
                "secondary": labels_from_pass(load_pass(p_dir / "sessions" / "judge8-gpu0")),
            }
            comparisons["pass_1411"] = anchor_vs_pass(
                artifact, rows_of[anchor], labels, item_of, p_reader["rows"], p_labels,
                item_index(p_items),
            )  # fmt: skip
            # The join that built the committed tables, unchanged: the pilot labels used above
            # must be its labels at every table request.
            rows_ma, _, _, _ = ma.join_rows(p_dir, pilot, artifact)
            p_item_of = item_index(p_items)
            same = compared = 0
            for row in rows_ma:
                if row["kind"] != "table" or row["reply"] is None:
                    continue
                item = p_item_of.get((row["question_index"], row["reply"].strip()))
                compared += 1
                same += (
                    p_labels["primary"].get(item) == row["u"]
                    and p_labels["secondary"].get(item) == row["u_secondary"]
                )
            if same != compared:
                raise Am3Error("the pilot labels differ from memcredit_analyze.join_rows")
            comparisons["pass_1411"]["join_rows_table_requests_agree"] = same
        if args.pilot_eager_run_dir:
            e_dir = Path(args.pilot_eager_run_dir)
            ks.check_digests(e_dir, lf.EAGER_PASS["sha256"])
            e_reader = load_pass(e_dir / "sessions" / lf.EAGER_PASS["reader"])
            e_items = json.loads((e_dir / "judge-items.json").read_text(encoding="utf-8"))
            e_labels = {
                "primary": labels_from_pass(load_pass(e_dir / "sessions" / lf.EAGER_PASS["judge"]))
            }
            comparisons["pass_1441_eager"] = anchor_vs_pass(
                artifact, rows_of[anchor], labels, item_of, e_reader["rows"], e_labels,
                item_index(e_items), question_limit=int(lf.EAGER_PASS["questions"]),
            )  # fmt: skip
    payload = {
        "experiment": EXPERIMENT,
        "run": {
            "summary_steps": {
                sid: {
                    k: rec.get(k)
                    for k in (
                        "kind",
                        "reader",
                        "status",
                        "batch_invariant",
                        "enforce_eager",
                        "exit",
                        "wall_s",
                    )
                }
                for sid, rec in summary.get("steps", {}).items()
            },
            "judge_items": summary.get("judge_items"),
            "model_verification": {
                k: {
                    f: v.get(f)
                    for f in (
                        "repo_id",
                        "revision",
                        "artifact_root_sha256",
                        "receipt_sha256",
                        "verified_by",
                    )
                }
                for k, v in summary.get("model_verification", {}).items()
            },
        },
        "study_artifact_sha256": config["pilot"]["study_artifact_sha256"],
        "abstention_patterns_sha256": lf.patterns_sha256(),
        "anchor": anchor,
        "validation": validation,
        "anchor_comparisons": comparisons,
        "readers": readers,
    }
    if lf.patterns_sha256() != lf.ABSTENTION_PATTERNS_SHA256:
        raise Am3Error("the abstention patterns differ from AM1d's")
    private = Path(args.private_dir)
    private.mkdir(parents=True, exist_ok=True)
    lf.write_gz_json(private / "features.json.gz", payload)
    brief = {
        "readers": {r: {k: v for k, v in d.items() if k != "pools"} for r, d in readers.items()},
        "validation": validation,
        "anchor_comparisons": {
            k: {f: v for f, v in c.items() if f != "differing_cells"}
            for k, c in comparisons.items()
        },
        "features_sha256": sha256_file(private / "features.json.gz"),
    }
    return brief


# --------------------------------------------------------------------------- analysis


def bm25_order(ranks: Sequence[int]) -> list[int]:
    """The 70 4-subsets in BM25 order (``memcredit_label_free.rank_key``, best first)."""

    return sorted(FOUR_SETS, key=lambda m: lf.rank_key(m, ranks), reverse=True)


def nonabstain_bm25(pool: dict[str, Any]) -> dict[str, Any]:
    """AM1d's rule (H-C of am1-keepset-search-v1): read 4-subsets in BM25 order and keep the
    first whose reply does not abstain; keep BM25 top 4 when every 4-subset abstains."""

    order = bm25_order(pool["bm25_rank"])
    if order[0] != lf.bm25_top_mask(pool["bm25_rank"]):
        raise Am3Error("BM25 order does not start at BM25 top 4")
    position = next((i + 1 for i, m in enumerate(order) if not pool["masks"][m]["abstain"]), None)
    chosen = order[position - 1] if position else order[0]
    return {
        "mask": chosen,
        "first_answer_position": position,
        "reads": position if position else len(order),
    }


def table_record(pool: dict[str, Any]) -> dict[str, Any]:
    """One pool's choices and outcomes under both judges (no text)."""

    top4 = lf.bm25_top_mask(pool["bm25_rank"])
    rule = nonabstain_bm25(pool)
    record: dict[str, Any] = {
        "question_id": pool["question_id"],
        "question_type": pool["question_type"],
        "arm": pool["arm"],
        "bm25_top4_mask": top4,
        "nonabstain_mask": rule["mask"],
        "first_answer_position": rule["first_answer_position"],
        "reads": rule["reads"],
        "four_subset_abstain": sum(bool(pool["masks"][m]["abstain"]) for m in FOUR_SETS),
        "bm25_top4_abstains": bool(pool["masks"][top4]["abstain"]),
        "all_8_abstains": bool(pool["masks"][FULL]["abstain"]),
        "u": {},
    }
    for j in JUDGES:
        u4 = {m: int(pool["masks"][m]["u"][j]) for m in FOUR_SETS}
        record["u"][j] = {
            "bm25_top4": u4[top4],
            "nonabstain_bm25": u4[rule["mask"]],
            "all_8": int(pool["masks"][FULL]["u"][j]),
            "oracle_best4": max(u4.values()),
            "four_subset_correct": sum(u4.values()),
            "four_subset_abstain_correct": sum(
                u4[m] for m in FOUR_SETS if pool["masks"][m]["abstain"]
            ),
            "four_subset_nonabstain_correct": sum(
                u4[m] for m in FOUR_SETS if not pool["masks"][m]["abstain"]
            ),
            "all_8_abstain_correct": int(
                pool["masks"][FULL]["abstain"] and pool["masks"][FULL]["u"][j] == 1
            ),
        }
    return record


def reading(entry: dict[str, Any], alpha: float) -> str:
    b, c, p = (
        entry["rule_right_base_wrong"],
        entry["rule_wrong_base_right"],
        entry["p_exact_mcnemar"],
    )
    if p <= alpha and b > c:
        return "HELPS"
    if p <= alpha and b < c:
        return "HURTS"
    return "NOT_SEPARATED"


def cell_summary(
    records: Sequence[dict[str, Any]], judge: str, resamples: int, seed: int, alpha: float
) -> dict[str, Any]:
    """Accuracy of the four rules, the paired comparisons and the abstention and reads summaries
    over one reader x judge x arm cell."""

    def outcome(rule: str) -> dict[str, float]:
        return {r["question_id"]: float(r["u"][judge][rule]) for r in records}

    def boot(values: dict[str, float]) -> dict[str, Any]:
        b = ms.cluster_bootstrap({q: [v] for q, v in values.items()}, resamples, seed, 0.05)
        return {"mean": b["mean"], "ci95": b["ci"], "questions": b["units"]}

    rules = ("bm25_top4", "nonabstain_bm25", "all_8", "oracle_best4")
    cell: dict[str, Any] = {"questions": len(records),
                            "accuracy": {rule: boot(outcome(rule)) for rule in rules}}  # fmt: skip
    pairs = {
        "nonabstain_bm25_vs_bm25_top4": ("nonabstain_bm25", "bm25_top4"),
        "nonabstain_bm25_vs_all_8": ("nonabstain_bm25", "all_8"),
        "bm25_top4_vs_all_8": ("bm25_top4", "all_8"),
    }
    cell["paired"] = {}
    for name, (rule, base) in pairs.items():
        entry = ks.paired_reading(outcome(rule), outcome(base), READINGS, resamples, seed,
                                  alpha=alpha, label_key="description")  # fmt: skip
        entry["description"] = reading(entry, alpha)
        cell["paired"][name] = entry
    n4 = len(FOUR_SETS) * len(records)
    abstain = sum(r["four_subset_abstain"] for r in records)
    cell["abstention"] = {
        "four_subset_replies": n4,
        "four_subset_abstain": abstain,
        "four_subset_abstain_rate": abstain / n4 if n4 else None,
        "four_subset_abstain_judged_correct": sum(
            r["u"][judge]["four_subset_abstain_correct"] for r in records
        ),
        "four_subset_nonabstain_judged_correct": sum(
            r["u"][judge]["four_subset_nonabstain_correct"] for r in records
        ),
        "bm25_top4_abstains": sum(r["bm25_top4_abstains"] for r in records),
        "all_8_abstains": sum(r["all_8_abstains"] for r in records),
        "all_8_abstain_judged_correct": sum(
            r["u"][judge]["all_8_abstain_correct"] for r in records
        ),
        "pools_every_4_subset_abstains": sum(r["first_answer_position"] is None for r in records),
        "rule_switches_from_top4": sum(
            r["nonabstain_mask"] != r["bm25_top4_mask"] for r in records
        ),
    }
    cell["stop_rule_reads"] = ks.reads_summary([r["reads"] for r in records])
    return cell


def analyze(features: dict[str, Any], resamples: int, seed: int, alpha: float) -> dict[str, Any]:
    if features.get("abstention_patterns_sha256") != lf.ABSTENTION_PATTERNS_SHA256:
        raise Am3Error("features were flagged with other abstention patterns")
    per_table: list[dict[str, Any]] = []
    cells: dict[str, Any] = {}
    for reader in features["readers"].values():
        for pool in reader["pools"]:
            pool["masks"] = {int(m): cell for m, cell in pool["masks"].items()}
    for reader_id, reader in features["readers"].items():
        incomplete = [p for p in reader["pools"] if not complete_pool(p)]
        if incomplete:
            raise Am3Error(f"{reader_id}: {len(incomplete)} incomplete pools")
        records = [table_record(p) for p in reader["pools"]]
        for r in records:
            per_table.append({"reader": reader_id} | r)
        cells[reader_id] = {}
        for j in JUDGES:
            cells[reader_id][j] = {}
            for arm in ARMS:
                arm_rows = [r for r in records if r["arm"] == arm]
                cells[reader_id][j][arm] = cell_summary(arm_rows, j, resamples, seed, alpha)
    headline = []
    for reader_id, by_judge in cells.items():
        for j, by_arm in by_judge.items():
            for arm, cell in by_arm.items():
                hc = cell["paired"]["nonabstain_bm25_vs_bm25_top4"]
                h8 = cell["paired"]["nonabstain_bm25_vs_all_8"]
                headline.append({
                    "reader": reader_id, "judge": j, "arm": arm,
                    "acc_bm25_top4": cell["accuracy"]["bm25_top4"]["mean"],
                    "acc_nonabstain_bm25": cell["accuracy"]["nonabstain_bm25"]["mean"],
                    "acc_all_8": cell["accuracy"]["all_8"]["mean"],
                    "acc_oracle_best4": cell["accuracy"]["oracle_best4"]["mean"],
                    "vs_top4_b": hc["rule_right_base_wrong"],
                    "vs_top4_c": hc["rule_wrong_base_right"],
                    "vs_top4_p": hc["p_exact_mcnemar"], "vs_top4": hc["description"],
                    "vs_all8_b": h8["rule_right_base_wrong"],
                    "vs_all8_c": h8["rule_wrong_base_right"],
                    "vs_all8_p": h8["p_exact_mcnemar"], "vs_all8": h8["description"],
                    "abstain_rate_4subsets": cell["abstention"]["four_subset_abstain_rate"],
                    "reads_median": cell["stop_rule_reads"]["median"],
                    "reads_mean": cell["stop_rule_reads"]["mean"],
                })  # fmt: skip
    return {
        "experiment": EXPERIMENT,
        "claim_level": "exploratory",
        "split": "development",
        "config": {
            "bootstrap_resamples": resamples,
            "bootstrap_seed": seed,
            "alpha": alpha,
            "abstention_patterns_sha256": lf.ABSTENTION_PATTERNS_SHA256,
            "requests_per_pool": len(REQUEST_MASKS),
            "descriptions": "HELPS when p <= alpha and b > c; HURTS when p <= alpha and b < c; "
            "else NOT_SEPARATED (exploratory; nothing is decided)",
        },
        "inputs": {
            "study_artifact_sha256": features["study_artifact_sha256"],
            "run": features["run"],
            "readers": {
                r: {
                    k: d[k]
                    for k in (
                        "step",
                        "batch_invariant",
                        "enforce_eager",
                        "pass_sha256",
                        "requests",
                        "finish",
                        "missing_logprobs",
                        "pools_complete",
                    )
                }
                for r, d in features["readers"].items()
            },
        },
        "validation": features["validation"],
        "anchor": features["anchor"],
        "anchor_comparisons": features["anchor_comparisons"],
        "cells": cells,
        "headline": headline,
    }, per_table


def _f(x: float | None, digits: int = 3) -> str:
    return "n/a" if x is None else f"{x:.{digits}f}"


def _p(x: float) -> str:
    return f"{x:.2g}" if x < 0.001 else f"{x:.3f}"


def render_markdown(results: dict[str, Any]) -> str:
    lines = [
        "# AM3 tables (EXPLORATORY, development split only)",
        "",
        "Generated by `scripts/memcredit_am3.py analyze`. Accuracy is over all 63 development",
        "questions per arm. b: rule right, base wrong; c: rule wrong, base right; p: exact",
        "two-sided McNemar. Descriptions: HELPS / HURTS when p <= 0.05, else NOT_SEPARATED.",
        "",
        "## Main table",
        "",
        "| Reader | Judge | Arm | BM25 top 4 | nonabstain-BM25 | all 8 | oracle best 4 | "
        "vs top 4: b, c, p | vs all 8: b, c, p | 4-subset abstain rate | reads median (mean) |",
        "|---|---|---|---:|---:|---:|---:|---|---|---:|---|",
    ]
    names = {"primary": "Qwen3-32B", "secondary": "Qwen3-8B"}
    for h in results["headline"]:
        lines.append(
            f"| {h['reader']} | {names[h['judge']]} | {h['arm']} | {_f(h['acc_bm25_top4'])} | "
            f"{_f(h['acc_nonabstain_bm25'])} | {_f(h['acc_all_8'])} | "
            f"{_f(h['acc_oracle_best4'])} | "
            f"{h['vs_top4_b']}, {h['vs_top4_c']}, {_p(h['vs_top4_p'])} ({h['vs_top4']}) | "
            f"{h['vs_all8_b']}, {h['vs_all8_c']}, {_p(h['vs_all8_p'])} ({h['vs_all8']}) | "
            f"{_f(h['abstain_rate_4subsets'])} | {_f(h['reads_median'], 0)} "
            f"({_f(h['reads_mean'], 2)}) |"
        )
    lines += ["", "## Accuracy with 95% question bootstrap intervals", ""]
    lines += ["| Reader | Judge | Arm | Rule | Accuracy | 95% CI |", "|---|---|---|---|---:|---|"]
    for reader_id, by_judge in results["cells"].items():
        for j, by_arm in by_judge.items():
            for arm, cell in by_arm.items():
                for rule, acc in cell["accuracy"].items():
                    lines.append(
                        f"| {reader_id} | {names[j]} | {arm} | {rule} | {_f(acc['mean'])} | "
                        f"[{_f(acc['ci95'][0])}, {_f(acc['ci95'][1])}] |"
                    )
    lines += ["", "## Paired differences", ""]
    lines += [
        "| Reader | Judge | Arm | Comparison | Difference | 95% bootstrap | exact conditional "
        "95% | b | c | p | Description |",
        "|---|---|---|---|---:|---|---|---:|---:|---:|---|",
    ]
    for reader_id, by_judge in results["cells"].items():
        for j, by_arm in by_judge.items():
            for arm, cell in by_arm.items():
                for name, e in cell["paired"].items():
                    lines.append(
                        f"| {reader_id} | {names[j]} | {arm} | {name} | {e['difference']:+.3f} | "
                        f"[{e['ci95_bootstrap'][0]:+.3f}, {e['ci95_bootstrap'][1]:+.3f}] | "
                        f"[{e['ci95_exact_conditional'][0]:+.3f}, "
                        f"{e['ci95_exact_conditional'][1]:+.3f}] | {e['rule_right_base_wrong']} | "
                        f"{e['rule_wrong_base_right']} | {_p(e['p_exact_mcnemar'])} | "
                        f"{e['description']} |"
                    )
    lines += ["", "## Abstention and the stop rule's reads", ""]
    lines += [
        "| Reader | Judge | Arm | 4-subset replies abstaining | judged correct among them | "
        "BM25 top 4 abstains | all 8 abstains (judged correct) | every 4-subset abstains | "
        "rule switches from top 4 | reads: median, mean, p90, at 1, max |",
        "|---|---|---|---|---:|---:|---|---:|---:|---|",
    ]
    for reader_id, by_judge in results["cells"].items():
        for j, by_arm in by_judge.items():
            for arm, cell in by_arm.items():
                a, rd = cell["abstention"], cell["stop_rule_reads"]
                lines.append(
                    f"| {reader_id} | {names[j]} | {arm} | {a['four_subset_abstain']} of "
                    f"{a['four_subset_replies']} ({_f(a['four_subset_abstain_rate'])}) | "
                    f"{a['four_subset_abstain_judged_correct']} | {a['bm25_top4_abstains']} | "
                    f"{a['all_8_abstains']} ({a['all_8_abstain_judged_correct']}) | "
                    f"{a['pools_every_4_subset_abstains']} | {a['rule_switches_from_top4']} | "
                    f"{_f(rd['median'], 0)}, {_f(rd['mean'], 2)}, {rd['p90']}, {rd['at_1']}, "
                    f"{rd['max']} |"
                )
    comps = results["anchor_comparisons"]
    lines += ["", f"## Anchor validation ({results['anchor']})", ""]
    if "tables" in comps:
        t = comps["tables"]
        lines.append(
            f"- Against the pilot's committed tables (Qwen3-32B labels, compiled pass 1411): "
            f"{t['cells_same_label']} of {t['cells']} cells agree ({_f(t['agreement'], 4)}); "
            f"{t['tables_with_any_difference']} of {t['pools']} tables have any difference."
        )
    for key, label in (("pass_1411", "pass 1411 (compiled, GPU 0)"),
                       ("pass_1441_eager", "pass 1441 (eager, first 16 questions)")):  # fmt: skip
        if key in comps:
            c = comps[key]
            text = (
                f"- Against {label}: {c['identical_tokens']} of {c['compared']} replies identical "
                f"in tokens, {c['identical_bits']} also in log-prob bits"
            )
            for j in JUDGES:
                if c.get(f"label_compared_{j}"):
                    text += (
                        f"; {names[j]} labels {c[f'label_same_{j}']} of "
                        f"{c[f'label_compared_{j}']} agree ({c[f'label_same_identical_reply_{j}']}"
                        f" of {c[f'label_compared_identical_reply_{j}']} on identical replies)"
                    )
            lines.append(text + ".")
    lines += ["", "## Judge validation items", ""]
    lines += ["| Judge | reference answer, yes | \"I don't know.\", yes | another answer, yes |",
              "|---|---|---|---|"]  # fmt: skip
    for j, v in results["validation"]["judge_validation"].items():
        ref, idk, oth = (v["validation:reference"], v["validation:idk"],
                         v["validation:other-answer"])  # fmt: skip
        lines.append(
            f"| {names[j]} | {ref['yes']} of {ref['items']} | {idk['yes']} of {idk['items']} | "
            f"{oth['yes']} of {oth['items']} |"
        )
    return "\n".join(lines) + "\n"


def cmd_analyze(args: argparse.Namespace) -> dict[str, Any]:
    for p in (args.features, args.output_dir):
        check_path(p)
    config = load_config(Path(args.config))
    features = lf.read_gz_json(Path(args.features))
    spec = config["analysis"]
    results, per_table = analyze(
        features, int(spec["bootstrap"]["resamples"]), int(spec["bootstrap"]["seed"]),
        float(spec["alpha"]),
    )  # fmt: skip
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    results["inputs"]["features_sha256"] = sha256_file(Path(args.features))
    lane.write_json(out / "results.json", results)
    lf.write_gz_json(out / "per-table.json.gz", per_table)
    (out / "tables.md").write_text(render_markdown(results), encoding="utf-8")
    return {f: sha256_file(out / f) for f in ("results.json", "per-table.json.gz", "tables.md")}


# --------------------------------------------------------------------------- main


def main(argv: Sequence[str] | None = None) -> int:
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
    worker.add_argument("--step", required=True)
    worker.add_argument("--output-dir", required=True)
    worker.add_argument("--deadline", type=float, required=True)
    worker.add_argument("--evidence", required=True)
    worker.add_argument("--expected-evidence-sha256", required=True)
    extract = sub.add_parser("extract", allow_abbrev=False)
    extract.add_argument("--run-dir", required=True)
    extract.add_argument("--evidence", required=True)
    extract.add_argument("--private-dir", required=True)
    extract.add_argument("--pilot-run-dir", default=None)
    extract.add_argument("--pilot-eager-run-dir", default=None)
    analyze_p = sub.add_parser("analyze", allow_abbrev=False)
    analyze_p.add_argument("--features", required=True)
    analyze_p.add_argument("--output-dir", required=True)
    for sp in sub.choices.values():
        sp.add_argument("--config", default=str(CONFIG_PATH))
    args = parser.parse_args(argv)
    if args.command == "plan":
        config = load_config(Path(args.config))
        pilot = load_pilot_config(config)
        artifact = load_artifact(Path(args.evidence), None, config, pilot)
        print(json.dumps(build_plan(config, artifact), indent=2))
        return 0
    if args.command == "selftest":
        return selftest_main(args)
    if args.command == "run":
        return run_main(args)
    if args.command == "worker":
        return vllm_worker(args)
    if args.command == "extract":
        print(json.dumps(cmd_extract(args), indent=2, sort_keys=True))
        return 0
    print(json.dumps(cmd_analyze(args), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
