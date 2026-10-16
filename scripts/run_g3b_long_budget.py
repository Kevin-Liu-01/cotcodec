#!/usr/bin/env python3
"""g3b-long-budget-v1 (EXPLORATORY): Qwen3.5-4B math with a float32 or bfloat16 GDN state at
the model card's 81,920-token budget, with no preemption, on the 51 questions that had a capped
rollout in G3.

Runs inside the digest-pinned cotcodec-vllm cu129 overlay on the docker-research lane. Config:
experiments/g3/g3b-long-budget-v1.yaml. G3's engine loop (``scripts/run_g3_accuracy.py``
``run_requests``) and G2b's worker pieces (engine record, metric sampler, supervisor, signals)
are reused unchanged.

Subcommands:

* ``plan --phase P``: the resolved plan. CPU only.
* ``selftest``: CPU only, no engine: config, the pinned questions, prompt rendering and lengths
  with the tokenizer, the fit of the longest prompt, EngineArgs for every arm, SamplingParams,
  the fit check against G3's recorded block pools, the metrics parser and the truncated
  decoding.
* ``run --phase P --model M --arm A --seeds 42 43 44 --output-dir O --allocation-minutes N``: one
  GPU, one arm: the math worker (one engine, every request submitted at once, FCFS admission at
  ``max_num_seqs`` running).
* ``worker``: the subprocess ``run`` supervises. After the engine starts it checks that
  ``max_num_seqs`` sequences of ``max_model_len`` tokens fit the engine's block pool, and stops
  before submitting anything if they do not.

Model outputs (texts and token ids) are written under the run directory on the host. Each
rollout's text is stored in full and, for every rescoring cap it exceeds, as the decoding of its
first ``cap`` tokens. The per-request records (``records.json``) carry no text.
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import signal
import sys
import threading
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness import g2_pilot as g2  # noqa: E402
from harness import g2b_state_dtype as gb  # noqa: E402
from harness import g3_state_precision as g3  # noqa: E402
from harness import g3b_long_budget as g3b  # noqa: E402
from scripts import run_g2_rollouts as base  # noqa: E402
from scripts import run_g2b_rollouts as rb  # noqa: E402
from scripts import run_g3_accuracy as r3  # noqa: E402

END_OF_TURN = base.END_OF_TURN
#: Exit code of a worker whose engine's block pool cannot hold max_num_seqs full sequences.
EXIT_NO_FIT = 4


def build_plan(config: dict[str, Any], phase: str) -> dict[str, Any]:
    plan = g3b.phase_plan(config, phase)
    reqs = g3b.math_requests(plan)
    return {
        "experiment_id": config["experiment_id"],
        "claim_level": config["claim_level"],
        "phase": plan,
        "math_requests": len(reqs),
        "first_requests": [r["request_id"] for r in reqs[:3]],
        "engine_kwargs": {
            arm: g3b.engine_kwargs(config, g3b.MODEL_ROOT / g3b.MODEL_ID, arm)
            for arm in plan["arms"]
        },
        "sampling": config["tasks"][g3b.TASK]["sampling"],
        "rescore_caps": config["tasks"][g3b.TASK]["rescore_caps"],
    }


# --------------------------------------------------------------------------- worker


def worker_main(args: argparse.Namespace) -> int:
    import numpy as np
    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams
    from vllm.inputs import TokensPrompt

    config = g3b.load_config()
    view = g3b.g3_view(config)
    plan = g3b.phase_plan(config, args.phase)
    model_id, arm = args.model, args.arm
    model_dir = g3b.MODEL_ROOT / model_id
    out = Path(args.output_dir) / f"{model_id}-{arm}-math"
    out.mkdir(parents=True, exist_ok=True)
    flag = base.StopFlag()
    signal.signal(signal.SIGTERM, flag.handler)
    signal.signal(signal.SIGUSR1, flag.handler)
    log_path = out / "worker-progress.jsonl"

    def log(event: str, **fields: Any) -> None:
        record = {"utc": g2.utc_now(), "event": event, "model": model_id, "arm": arm, **fields}
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(rb.jsonable(record), sort_keys=True) + "\n")
        print(json.dumps(rb.jsonable(record), sort_keys=True), flush=True)

    def finish(code: int) -> None:
        g2.write_json(out / "done.json", {"exit": code, "utc": g2.utc_now()})

    tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
    spec = config["tasks"][g3b.TASK]
    caps = [int(c) for c in spec["rescore_caps"]]
    prompts = g3.load_math_prompts(view)
    requests = g3b.math_requests(plan)
    prompt_ids = {
        q: base.render_prompt_ids(tokenizer, g3.math_user_message(prompts[q], view), True)
        for q in plan["math_questions"]
    }
    end_of_turn = tokenizer.convert_tokens_to_ids(END_OF_TURN)
    kwargs = g3b.engine_kwargs(config, model_dir, arm)
    longest = max(len(v) for v in prompt_ids.values())
    log("render-done", requests=len(requests), prompt_len_max=longest)
    if longest + int(spec["sampling"]["max_tokens"]) > int(spec["max_model_len"]):
        log("no-fit", reason="a prompt plus max_tokens exceeds max_model_len")
        finish(EXIT_NO_FIT)
        sys.stdout.flush()
        os._exit(EXIT_NO_FIT)
    log("engine-start", engine_kwargs=kwargs, end_of_turn_id=end_of_turn)
    t0 = time.time()
    llm = LLM(**kwargs)
    info = rb.engine_info(llm)
    info["init_s"] = round(time.time() - t0, 1)
    cci = info.get("cache_config_info") or {}
    concurrency = cci.get("kv_cache_max_concurrency")
    fit = g3b.fit_report(
        int(info["num_gpu_blocks"]),
        int(info["block_size"]),
        int(info["max_model_len"]),
        int(info["max_num_seqs"]),
        int(config["engine"]["gdn_groups"]),
        float(concurrency) if concurrency not in (None, "None") else None,
    )
    info["fit"] = fit
    g2.write_json(out / "engine.json", info)
    log("engine-ready", **info)
    if not fit["ok"]:
        log("no-fit", reason="max_num_seqs full-length sequences do not fit the block pool")
        finish(EXIT_NO_FIT)
        closer = threading.Thread(target=lambda: llm.llm_engine.engine_core.shutdown(), daemon=True)
        closer.start()
        closer.join(timeout=15)
        sys.stdout.flush()
        os._exit(EXIT_NO_FIT)
    items = []
    for req in requests:
        params = SamplingParams(**g3b.sampling_kwargs(config, req["request_seed"], end_of_turn))
        items.append(
            (
                req["request_id"],
                TokensPrompt(prompt_token_ids=prompt_ids[req["question_index"]]),
                params,
            )
        )
    gen_seconds = float(plan["math_gen_seconds"])
    stop_at = min(args.deadline - args.reserve_s, time.time() + gen_seconds)
    log("phase-start", requests=len(items), gen_seconds=gen_seconds)
    state, steps, sampler, rinfo = r3.run_requests(
        llm, items, stop_at, flag, float(config["stats_interval_s"])
    )
    rinfo["drain_steps"] = rb.drain(llm)
    rb.save_stats(out / "phase-stats.npz", steps, sampler)
    output_tokens = sum(len(st["token_ids"]) for st in state.values())
    prompt_tokens = sum(len(prompt_ids[r["question_index"]]) for r in requests)
    phase = gb.summarize_phase(
        steps, sampler.samples, len(items), rinfo["finished"], output_tokens, rinfo["wall_s"]
    )
    phase |= {
        "info": rinfo,
        "gen_seconds": gen_seconds,
        "prompt_tokens": prompt_tokens,
        "prompt_tok_per_s": prompt_tokens / rinfo["wall_s"] if rinfo["wall_s"] > 0 else None,
        "peak_running_sampled": max((s.get("running", 0) for s in sampler.samples), default=0),
    }
    log("phase-done", **{k: v for k, v in phase.items() if k != "info"}, info=rinfo)
    rows = []
    offsets = [0]
    for req in requests:
        st = state[req["request_id"]]
        offsets.append(offsets[-1] + len(st["token_ids"]))
        rows.append(
            {
                **req,
                "prompt_len": len(prompt_ids[req["question_index"]]),
                "completion_len": len(st["token_ids"]),
                "finish_reason": st["finish_reason"] if st["finished"] else "cut_at_time_budget",
                "stop_reason": st["stop_reason"],
                "sum_logp": round(st["sum_logp"], 6),
                "missing_logprobs": st["missing_logprobs"],
                "first_token_s": st["first_token_s"],
                "finished_s": st["finished_s"],
            }
        )
    np.savez_compressed(
        out / "tokens.npz",
        offsets=np.asarray(offsets, dtype=np.int64),
        token_ids=np.concatenate(
            [np.frombuffer(state[r["request_id"]]["token_ids"], dtype=np.int32) for r in requests]
        )
        if offsets[-1]
        else np.zeros(0, dtype=np.int32),
        prompt_len=np.asarray([row["prompt_len"] for row in rows], dtype=np.int32),
    )
    with gzip.open(out / "texts.jsonl.gz", "wt", encoding="utf-8") as handle:
        for req in requests:
            ids = list(state[req["request_id"]]["token_ids"])
            entry: dict[str, Any] = {
                "request_id": req["request_id"],
                "text": tokenizer.decode(ids, skip_special_tokens=False),
            }
            for cap in caps:
                if len(ids) > cap:
                    entry[f"text_at_{cap}"] = tokenizer.decode(ids[:cap], skip_special_tokens=False)
            handle.write(json.dumps(entry) + "\n")
    g2.write_json(
        out / "records.json",
        {
            "experiment_id": config["experiment_id"],
            "phase": args.phase,
            "model_id": model_id,
            "arm": arm,
            "task": g3b.TASK,
            "state_dtype_setting": config["arms"][arm],
            "engine_kwargs": kwargs,
            "sampling": spec["sampling"],
            "rescore_caps": caps,
            "enable_thinking": True,
            "end_of_turn_id": end_of_turn,
            "source_sha256": spec["prompts"]["sha256"],
            "questions_sha256": config["questions"]["indices_sha256"],
            "requests": rows,
        },
    )
    summary = {
        "model": model_id,
        "arm": arm,
        "task": g3b.TASK,
        "phase_name": args.phase,
        "engine": info,
        "phase": phase,
        "tokens_npz_sha256": g2.sha256_file(out / "tokens.npz"),
        "texts_sha256": g2.sha256_file(out / "texts.jsonl.gz"),
        "records_sha256": g2.sha256_file(out / "records.json"),
    }
    g2.write_json(out / "summary.json", summary)
    complete = rinfo["finished"] == len(items) and rinfo["unmatched"] == 0
    code = 0 if complete else 3
    log("saved", requests=len(rows), output_tokens=output_tokens, exit=code)
    finish(code)
    closer = threading.Thread(target=lambda: llm.llm_engine.engine_core.shutdown(), daemon=True)
    closer.start()
    closer.join(timeout=15)
    sys.stdout.flush()
    os._exit(code)


# --------------------------------------------------------------------------- driver


def run_main(args: argparse.Namespace) -> int:
    config = g3b.load_config()
    if list(args.seeds) != config["seeds"]:
        raise g3b.G3bConfigError("--seeds must equal the config's declared seeds")
    if args.model not in config["models"]:
        raise g3b.G3bConfigError(f"unknown model {args.model}")
    plan = g3b.phase_plan(config, args.phase)
    if args.arm not in plan["arms"]:
        raise g3b.G3bConfigError(f"arm {args.arm} is not in phase {args.phase}")
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    stop_at, source = g2.deadline(args.allocation_minutes)
    summary: dict[str, Any] = {
        "experiment_id": config["experiment_id"],
        "claim_level": "exploratory",
        "job": "long-budget",
        "phase": args.phase,
        "model": args.model,
        "arm": args.arm,
        "started_at": g2.utc_now(),
        "allocation_minutes": args.allocation_minutes,
        "deadline_source": source,
        "deadline_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(stop_at)),
        "plan": plan,
        "workers": {},
    }
    g2.write_json(out / "summary.json", summary)
    base.record_environment(out)
    state: dict[str, Any] = {"child": None, "signal": None, "signal_at": None}
    rb.install_signals(state)
    summary["verification"] = g2.verify_model(
        args.model, config["models"][args.model]["receipt_root"]
    )
    env = rb.child_env(out)
    argv = [
        sys.executable,
        str(Path(__file__).resolve()),
        "worker",
        "--phase",
        args.phase,
        "--model",
        args.model,
        "--arm",
        args.arm,
        "--output-dir",
        str(out),
        "--deadline",
        f"{stop_at:.3f}",
    ]
    worker_dir = out / f"{args.model}-{args.arm}-math"
    worker_dir.mkdir(parents=True, exist_ok=True)
    record = rb.supervise(
        argv, env, out / f"worker-{args.model}-{args.arm}-math.log", worker_dir / "done.json",
        stop_at, state,
    )  # fmt: skip
    done = record.get("worker_done") or {}
    record["status"] = "complete" if done.get("exit") == 0 else "partial" if done else "failed"
    summary["workers"]["math"] = record
    summary["finished_at"] = g2.utc_now()
    summary["signal"] = state["signal"]
    g2.write_json(out / "summary.json", summary)
    if state["signal"]:
        g2.write_checkpoint_marker(
            "SIGUSR1" if state["signal"] == "SIGUSR1" else "SIGTERM",
            "g3b: the rollouts sampled so far are saved; no resume (a rerun is a new job)",
        )
    return 0 if record["status"] == "complete" else 3


# --------------------------------------------------------------------------- selftest


#: G3's recorded block pools for Qwen3.5-4B at gpu_memory_utilization 0.90 (engine.json of jobs
#: 1523 and 1527): (num_gpu_blocks, block_size) per state dtype.
G3_POOLS = {"fp32": (3733, 528), "bf16": (7248, 272)}


def selftest_main(args: argparse.Namespace) -> int:
    """CPU only: everything the jobs construct before an engine starts."""

    import typing

    from transformers import AutoTokenizer
    from vllm import SamplingParams
    from vllm.config.cache import MambaDType
    from vllm.engine.arg_utils import EngineArgs
    from vllm.v1.metrics import reader

    config = g3b.load_config()
    view = g3b.g3_view(config)
    root = Path(args.model_root)
    phases = [p for p in g3b.PHASES if p in config]
    report: dict[str, Any] = {"plans": {p: build_plan(config, p) for p in phases}, "checks": {}}
    literal = list(typing.get_args(MambaDType))
    ok = all(v in literal for v in config["arms"].values())
    report["checks"]["mamba_dtype_literal"] = literal
    spec = config["tasks"][g3b.TASK]
    prompts = g3.load_math_prompts(view)
    tokenizer = AutoTokenizer.from_pretrained(str(root / g3b.MODEL_ID))
    lens = {
        q: len(base.render_prompt_ids(tokenizer, g3.math_user_message(prompts[q], view), True))
        for q in config["questions"]["indices"]
    }
    longest = max(lens.values())
    report["checks"]["prompt_len_max"] = longest
    report["checks"]["prompt_fits"] = (
        longest + spec["sampling"]["max_tokens"] <= spec["max_model_len"]
    )
    ok = ok and report["checks"]["prompt_fits"]
    tail = tokenizer.decode(base.render_prompt_ids(tokenizer, "x", True)[-6:])
    report["checks"]["math_prompt_tail"] = tail
    ok = ok and "<think>" in tail
    end = tokenizer.convert_tokens_to_ids(END_OF_TURN)
    for arm in g3b.ARM_DTYPES:
        kwargs = g3b.engine_kwargs(config, root / g3b.MODEL_ID, arm)
        engine_args = EngineArgs(**kwargs)
        report["checks"][f"engine_args_{arm}"] = {
            "mamba_ssm_cache_dtype": engine_args.mamba_ssm_cache_dtype,
            "max_model_len": engine_args.max_model_len,
            "max_num_seqs": engine_args.max_num_seqs,
            "block_size": engine_args.block_size,
            "enable_prefix_caching": engine_args.enable_prefix_caching,
        }
        ok = ok and engine_args.mamba_ssm_cache_dtype == config["arms"][arm]
        ok = ok and engine_args.block_size is None
        ok = ok and engine_args.max_num_seqs == config["engine"]["max_num_seqs"]
    for arm, (blocks, size) in G3_POOLS.items():
        fit = g3b.fit_report(
            blocks, size, spec["max_model_len"], config["engine"]["max_num_seqs"],
            config["engine"]["gdn_groups"],
        )  # fmt: skip
        report["checks"][f"fit_at_g3_pool_{arm}"] = fit
        ok = ok and fit["ok"]
    params = SamplingParams(**g3b.sampling_kwargs(config, 4200009, end))
    report["checks"]["sampling"] = {
        "top_k": params.top_k,
        "top_p": params.top_p,
        "presence_penalty": params.presence_penalty,
        "max_tokens": params.max_tokens,
        "seed": params.seed,
    }
    ok = ok and params.max_tokens == spec["sampling"]["max_tokens"]
    synthetic = [
        reader.Gauge(name="vllm:num_requests_running", labels={}, value=7.0),
        reader.Counter(name="vllm:num_preemptions", labels={}, value=3),
        reader.Gauge(name="vllm:kv_cache_usage_perc", labels={}, value=0.5),
    ]
    parsed = gb.parse_metrics(synthetic)
    ok = ok and parsed == {"running": 7.0, "preemptions": 3.0, "kv_usage": 0.5}
    report["checks"]["metrics_parser"] = parsed
    # Truncated decoding: the first cap tokens of a rollout decode to a prefix of its text.
    ids = base.render_prompt_ids(tokenizer, "Compute 1+1. \\boxed{2}", True)
    head = tokenizer.decode(ids[:5], skip_special_tokens=False)
    full = tokenizer.decode(ids, skip_special_tokens=False)
    report["checks"]["truncated_decode_is_prefix"] = full.startswith(head)
    ok = ok and full.startswith(head)
    ok = ok and g3.math_equiv("\\frac{9}{5}", "1\\frac{4}{5}") and not g3.math_equiv("2", "3")
    report["ok"] = bool(ok)
    print(json.dumps(rb.jsonable(report), indent=2, sort_keys=True))
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    sub = parser.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan", allow_abbrev=False)
    plan.add_argument("--phase", choices=g3b.PHASES, required=True)
    selftest = sub.add_parser("selftest", allow_abbrev=False)
    selftest.add_argument("--model-root", default=str(g3b.MODEL_ROOT))
    run = sub.add_parser("run", allow_abbrev=False)
    run.add_argument("--phase", choices=g3b.PHASES, required=True)
    run.add_argument("--model", required=True)
    run.add_argument("--arm", choices=tuple(g3b.ARM_DTYPES), required=True)
    run.add_argument("--seeds", type=int, nargs="+", required=True)
    run.add_argument("--output-dir", required=True)
    run.add_argument("--allocation-minutes", type=float, required=True)
    worker = sub.add_parser("worker", allow_abbrev=False)
    worker.add_argument("--phase", choices=g3b.PHASES, required=True)
    worker.add_argument("--model", required=True)
    worker.add_argument("--arm", choices=tuple(g3b.ARM_DTYPES), required=True)
    worker.add_argument("--output-dir", required=True)
    worker.add_argument("--deadline", type=float, required=True)
    worker.add_argument("--reserve-s", type=float, default=45.0)
    args = parser.parse_args()
    if args.command == "plan":
        print(
            json.dumps(
                rb.jsonable(build_plan(g3b.load_config(), args.phase)), indent=2, sort_keys=True
            )
        )
        return 0
    handlers = {"selftest": selftest_main, "run": run_main, "worker": worker_main}
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
