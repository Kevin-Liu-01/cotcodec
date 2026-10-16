#!/usr/bin/env python3
"""g3-state-precision-accuracy-v1 (EXPLORATORY): task accuracy of the Qwen3.5 hybrids with a
float32, float16 or bfloat16 GDN recurrent state in vLLM 0.31.0.

Runs inside the digest-pinned cotcodec-vllm cu129 overlay on the docker-research lane. Config:
experiments/g3/g3-state-precision-accuracy-v1.yaml. G2b's rollout worker pieces are reused
(``scripts/run_g2b_rollouts.py``: engine record, metric sampler, supervisor, signals).

Subcommands:

* ``plan --phase P``: the resolved plan. CPU only.
* ``selftest``: CPU only, no engine: config, prompt rendering and lengths with each model's
  tokenizer (math and every long-context question in the selection order), EngineArgs for every
  arm and task, SamplingParams, the judge prompt with the judge's tokenizer, the parsers.
* ``run --phase P --model M --arm A --seeds 42 43 44 --output-dir O --allocation-minutes N``: one
  GPU, one arm: a math worker (one engine, every math request at once), then a long-context
  worker (a second engine with the task's max_model_len).
* ``worker``: the subprocess ``run`` supervises (one task, one engine).
* ``judge --evidence /inputs/study-artifact.json ...``: AM1's primary judge on the long-context
  replies (one engine, greedy).

Model outputs (texts and token ids) are written under the run directory on the host; the
per-request records (``records.json``) carry no text.
"""

from __future__ import annotations

import argparse
import array
import gzip
import json
import math
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
from scripts import run_g2_rollouts as base  # noqa: E402
from scripts import run_g2b_rollouts as rb  # noqa: E402

END_OF_TURN = base.END_OF_TURN
#: Seconds a worker needs beyond its generation budget (engine start, saving, shutdown).
WORKER_OVERHEAD_S = 240.0


# --------------------------------------------------------------------------- plan


def build_plan(config: dict[str, Any], phase: str) -> dict[str, Any]:
    plan = g3.phase_plan(config, phase)
    prompts = g3.load_math_prompts(config)
    math_reqs = g3.math_requests(config, plan)
    models = {}
    for model_id in config["models"]:
        models[model_id] = {
            arm: {
                task: g3.engine_kwargs(config, model_id, g3.MODEL_ROOT / model_id, arm, task)
                for task in g3.TASKS
            }
            for arm in plan["arms"]
        }
    return {
        "experiment_id": config["experiment_id"],
        "claim_level": config["claim_level"],
        "phase": plan,
        "math_requests": len(math_reqs),
        "math_prompts": len(prompts),
        "lme_requests": plan["lme_questions"] * len(plan["lme_seeds"]),
        "engine_kwargs": models,
        "sampling": {t: config["tasks"][t]["sampling"] for t in g3.TASKS},
    }


def worker_budget(plan: dict[str, Any], task: str) -> float:
    return float(plan[f"{task}_gen_seconds"]) + WORKER_OVERHEAD_S


# --------------------------------------------------------------------------- engine loop


def run_requests(
    llm: Any,
    items: list[tuple[str, Any, Any]],
    stop_at: float,
    flag: base.StopFlag,
    interval: float,
) -> tuple[dict[str, dict[str, Any]], list[tuple[float, int, int]], rb.Sampler, dict[str, Any]]:
    """Add every request under our own id at once, step until done, the stop time or a signal,
    then abort what is left. DELTA outputs: a request cut at the stop keeps what it sampled."""

    from vllm.sampling_params import RequestOutputKind

    engine = llm.llm_engine
    sampler = rb.Sampler(llm, interval)
    sampler.take(force=True)
    state: dict[str, dict[str, Any]] = {}
    for ours, prompt, params in items:
        params.output_kind = RequestOutputKind.DELTA
        engine.add_request(ours, prompt, params)
        state[ours] = {
            "token_ids": array.array("i"),
            "sum_logp": 0.0,
            "missing_logprobs": 0,
            "finish_reason": None,
            "stop_reason": None,
            "finished": False,
            "first_token_s": None,
            "finished_s": None,
        }
    steps: list[tuple[float, int, int]] = []
    info: dict[str, Any] = {"aborted": 0, "stopped_by": None, "unmatched": 0}
    started = time.time()
    while engine.has_unfinished_requests():
        if time.time() >= stop_at or flag.event.is_set():
            info["stopped_by"] = flag.reason or "time budget"
            left = [ours for ours, st in state.items() if not st["finished"]]
            info["aborted"] = len(left)
            try:
                engine.abort_request(left, internal=False)
            except Exception as exc:  # noqa: BLE001 - recorded
                info["abort_error"] = repr(exc)
            break
        outputs = engine.step()
        now = round(time.time() - started, 3)
        n_out = n_tok = 0
        for output in outputs:
            st = state.get(str(output.request_id))
            if st is None:
                info["unmatched"] += 1
                continue
            if output.outputs:
                completion = output.outputs[0]
                ids = [int(t) for t in completion.token_ids]
                if ids:
                    n_out += 1
                    n_tok += len(ids)
                    if st["first_token_s"] is None:
                        st["first_token_s"] = now
                    values, missing = base.delta_logprobs(ids, completion.logprobs)
                    st["token_ids"].extend(ids)
                    st["sum_logp"] += sum(v for v in values if math.isfinite(v))
                    st["missing_logprobs"] += missing
                if output.finished:
                    st["finish_reason"] = completion.finish_reason
                    st["stop_reason"] = completion.stop_reason
            if output.finished:
                st["finished"] = True
                st["finished_s"] = now
        steps.append((round(time.time() - started, 4), n_out, n_tok))
        sampler.take()
    sampler.take(force=True)
    info["wall_s"] = round(time.time() - started, 3)
    info["finished"] = sum(1 for st in state.values() if st["finished"])
    info["metric_errors"] = sampler.errors
    return state, steps, sampler, info


# --------------------------------------------------------------------------- worker


def worker_main(args: argparse.Namespace) -> int:
    import numpy as np
    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams
    from vllm.inputs import TokensPrompt

    config = g3.load_config()
    plan = g3.phase_plan(config, args.phase)
    model_id, arm, task = args.model, args.arm, args.task
    model_dir = g3.MODEL_ROOT / model_id
    out = Path(args.output_dir) / f"{model_id}-{arm}-{task}"
    out.mkdir(parents=True, exist_ok=True)
    flag = base.StopFlag()
    signal.signal(signal.SIGTERM, flag.handler)
    signal.signal(signal.SIGUSR1, flag.handler)
    log_path = out / "worker-progress.jsonl"

    def log(event: str, **fields: Any) -> None:
        record = {
            "utc": g2.utc_now(),
            "event": event,
            "model": model_id,
            "arm": arm,
            "task": task,
            **fields,
        }
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(rb.jsonable(record), sort_keys=True) + "\n")
        print(json.dumps(rb.jsonable(record), sort_keys=True), flush=True)

    tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
    spec = config["tasks"][task]
    thinking = bool(spec["enable_thinking"])
    t_render = time.time()
    if task == "math":
        prompts = g3.load_math_prompts(config)
        requests = g3.math_requests(config, plan)
        messages = {
            r["question_index"]: g3.math_user_message(prompts[r["question_index"]], config)
            for r in requests
        }
        source_digest = config["tasks"]["math"]["prompts"]["sha256"]
    else:
        records = g3.load_lme(Path(args.longmemeval_path), config)
        by_id = {str(r["question_id"]): r for r in records}
        order = g3.lme_order(records, int(spec["selection_seed"]))
        requests = g3.lme_requests(config, plan, order)
        messages = {
            r["question_index"]: g3.lme_message(by_id[r["question_id"]], config) for r in requests
        }
        source_digest = spec["source"]["sha256"]
        del records
    prompt_ids = {q: base.render_prompt_ids(tokenizer, m, thinking) for q, m in messages.items()}
    end_of_turn = tokenizer.convert_tokens_to_ids(END_OF_TURN)
    kwargs = g3.engine_kwargs(config, model_id, model_dir, arm, task)
    log(
        "render-done",
        requests=len(requests),
        render_s=round(time.time() - t_render, 1),
        prompt_len_max=max(len(v) for v in prompt_ids.values()),
        source_sha256=source_digest,
    )
    log("engine-start", engine_kwargs=kwargs, end_of_turn_id=end_of_turn)
    t0 = time.time()
    llm = LLM(**kwargs)
    info = rb.engine_info(llm)
    info["init_s"] = round(time.time() - t0, 1)
    g2.write_json(out / "engine.json", info)
    log("engine-ready", **info)
    items = []
    for req in requests:
        params = SamplingParams(
            **g3.sampling_kwargs(config, task, req["request_seed"], end_of_turn)
        )
        items.append(
            (
                req["request_id"],
                TokensPrompt(prompt_token_ids=prompt_ids[req["question_index"]]),
                params,
            )
        )
    gen_seconds = float(plan[f"{task}_gen_seconds"])
    stop_at = min(args.deadline - args.reserve_s, time.time() + gen_seconds)
    log("phase-start", requests=len(items), gen_seconds=gen_seconds)
    state, steps, sampler, rinfo = run_requests(
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
            text = tokenizer.decode(ids, skip_special_tokens=False)
            handle.write(json.dumps({"request_id": req["request_id"], "text": text}) + "\n")
    g2.write_json(
        out / "records.json",
        {
            "experiment_id": config["experiment_id"],
            "phase": args.phase,
            "model_id": model_id,
            "arm": arm,
            "task": task,
            "state_dtype_setting": config["arms"][arm],
            "engine_kwargs": kwargs,
            "sampling": spec["sampling"],
            "enable_thinking": thinking,
            "end_of_turn_id": end_of_turn,
            "source_sha256": source_digest,
            "requests": rows,
        },
    )
    summary = {
        "model": model_id,
        "arm": arm,
        "task": task,
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
    g2.write_json(out / "done.json", {"exit": code, "utc": g2.utc_now()})
    closer = threading.Thread(target=lambda: llm.llm_engine.engine_core.shutdown(), daemon=True)
    closer.start()
    closer.join(timeout=15)
    sys.stdout.flush()
    os._exit(code)


# --------------------------------------------------------------------------- driver


def run_main(args: argparse.Namespace) -> int:
    config = g3.load_config()
    if list(args.seeds) != config["seeds"]:
        raise g3.G3ConfigError("--seeds must equal the config's declared seeds")
    if args.model not in config["models"]:
        raise g3.G3ConfigError(f"unknown model {args.model}")
    plan = g3.phase_plan(config, args.phase)
    if args.arm not in plan["arms"]:
        raise g3.G3ConfigError(f"arm {args.arm} is not in phase {args.phase}")
    tasks = list(args.tasks or (g3.TASKS if plan["math_questions"] else ("lme",)))
    if "math" in tasks and not plan["math_questions"]:
        raise g3.G3ConfigError(f"phase {args.phase} has no math task")
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    stop_at, source = g2.deadline(args.allocation_minutes)
    summary: dict[str, Any] = {
        "experiment_id": config["experiment_id"],
        "claim_level": "exploratory",
        "job": "accuracy",
        "phase": args.phase,
        "model": args.model,
        "arm": args.arm,
        "tasks": tasks,
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
    script = str(Path(__file__).resolve())
    for position, task in enumerate(tasks):
        later = sum(worker_budget(plan, t) for t in tasks[position + 1 :])
        remaining = stop_at - time.time()
        if state["signal"] or remaining < 300:
            summary["workers"][task] = {
                "status": "skipped",
                "remaining_s": round(remaining, 1),
                "signal": state["signal"],
            }
            g2.write_json(out / "summary.json", summary)
            continue
        worker_stop = stop_at - later
        argv = [
            sys.executable,
            script,
            "worker",
            "--phase",
            args.phase,
            "--model",
            args.model,
            "--arm",
            args.arm,
            "--task",
            task,
            "--output-dir",
            str(out),
            "--deadline",
            f"{worker_stop:.3f}",
            "--longmemeval-path",
            args.longmemeval_path,
        ]
        worker_dir = out / f"{args.model}-{args.arm}-{task}"
        worker_dir.mkdir(parents=True, exist_ok=True)
        record = rb.supervise(
            argv,
            env,
            out / f"worker-{args.model}-{args.arm}-{task}.log",
            worker_dir / "done.json",
            worker_stop,
            state,
        )
        done = record.get("worker_done") or {}
        record["status"] = "complete" if done.get("exit") == 0 else "partial" if done else "failed"
        summary["workers"][task] = record
        g2.write_json(out / "summary.json", summary)
    summary["finished_at"] = g2.utc_now()
    summary["signal"] = state["signal"]
    g2.write_json(out / "summary.json", summary)
    if state["signal"]:
        g2.write_checkpoint_marker(
            "SIGUSR1" if state["signal"] == "SIGUSR1" else "SIGTERM",
            "g3 accuracy: finished tasks saved; no resume (a rerun is a new job)",
        )
    ok = all(summary["workers"].get(t, {}).get("status") == "complete" for t in tasks)
    return 0 if ok else 3


# --------------------------------------------------------------------------- judge


def judge_main(args: argparse.Namespace) -> int:
    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams
    from vllm.inputs import TokensPrompt

    config = g3.load_config()
    raw = Path(args.evidence).read_bytes()
    if g3.sha256_bytes(raw) != args.expected_evidence_sha256:
        raise g3.G3ConfigError("judge input digest differs from --expected-evidence-sha256")
    artifact = json.loads(raw)
    if artifact.get("experiment_id") != config["experiment_id"]:
        raise g3.G3ConfigError("judge input belongs to another experiment")
    spec = config["judge"]
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    stop_at, source = g2.deadline(args.allocation_minutes)
    base.record_environment(out)
    summary: dict[str, Any] = {
        "experiment_id": config["experiment_id"],
        "job": "judge",
        "started_at": g2.utc_now(),
        "deadline_source": source,
        "input_sha256": args.expected_evidence_sha256,
        "items": len(artifact["items"]),
        "verification": g2.verify_model(spec["model_id"], spec["receipt_root"]),
    }
    g2.write_json(out / "summary.json", summary)
    model_dir = g3.MODEL_ROOT / spec["model_id"]
    tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
    questions = artifact["questions"]
    prompts = []
    longest = 0
    for item in artifact["items"]:
        message = g3.judge_message(questions[item["question_id"]], item["response"])
        ids = base.render_prompt_ids(tokenizer, message, bool(spec["enable_thinking"]))
        longest = max(longest, len(ids))
        prompts.append(TokensPrompt(prompt_token_ids=ids))
    e = spec["engine"]
    kwargs = {
        "model": str(model_dir),
        "tokenizer": str(model_dir),
        "trust_remote_code": False,
        "dtype": e["dtype"],
        "seed": config["seeds"][0],
        "max_model_len": e["max_model_len"],
        "gpu_memory_utilization": e["gpu_memory_utilization"],
        "max_num_seqs": e["max_num_seqs"],
        "max_num_batched_tokens": e["max_num_batched_tokens"],
        "enable_prefix_caching": e["enable_prefix_caching"],
        "logprobs_mode": e["logprobs_mode"],
    }
    summary["engine_kwargs"] = kwargs
    summary["prompt_len_max"] = longest
    if longest + spec["sampling"]["max_tokens"] > e["max_model_len"]:
        raise g3.G3ConfigError("a judge prompt does not fit max_model_len")
    t0 = time.time()
    llm = LLM(**kwargs)
    summary["engine"] = rb.engine_info(llm)
    summary["engine"]["init_s"] = round(time.time() - t0, 1)
    params = SamplingParams(
        temperature=float(spec["sampling"]["temperature"]),
        max_tokens=int(spec["sampling"]["max_tokens"]),
        logprobs=spec["sampling"]["logprobs"],
        seed=config["seeds"][0],
    )
    t1 = time.time()
    outputs = llm.generate(prompts, params, use_tqdm=False)
    summary["generate_s"] = round(time.time() - t1, 1)
    labels, texts = [], []
    for item, output in zip(artifact["items"], outputs, strict=True):
        reply = output.outputs[0].text
        label, well_formed = g3.parse_judgment(reply)
        labels.append({"index": item["index"], "label": label, "well_formed": well_formed})
        texts.append({"index": item["index"], "reply": reply})
    g2.write_json(
        out / "labels.json", {"input_sha256": args.expected_evidence_sha256, "labels": labels}
    )
    with gzip.open(out / "judge-texts.jsonl.gz", "wt", encoding="utf-8") as handle:
        for row in texts:
            handle.write(json.dumps(row) + "\n")
    validation = [
        (it, lab) for it, lab in zip(artifact["items"], labels, strict=True) if "expected" in it
    ]
    summary["validation"] = {
        "items": len(validation),
        "agree": sum(1 for it, lab in validation if lab["label"] == it["expected"]),
        "malformed": sum(1 for lab in labels if not lab["well_formed"]),
    }
    summary["finished_at"] = g2.utc_now()
    summary["labels_sha256"] = g2.sha256_file(out / "labels.json")
    g2.write_json(out / "summary.json", summary)
    if time.time() > stop_at:
        summary["late"] = True
    closer = threading.Thread(target=lambda: llm.llm_engine.engine_core.shutdown(), daemon=True)
    closer.start()
    closer.join(timeout=15)
    sys.stdout.flush()
    os._exit(0)


# --------------------------------------------------------------------------- selftest


def selftest_main(args: argparse.Namespace) -> int:
    """CPU only: everything the jobs construct before an engine starts."""

    import typing

    from transformers import AutoTokenizer
    from vllm import SamplingParams
    from vllm.config.cache import MambaDType
    from vllm.engine.arg_utils import EngineArgs
    from vllm.v1.metrics import reader

    config = g3.load_config()
    root = Path(args.model_root)
    phases = [p for p in g3.PHASES if p in config]
    report: dict[str, Any] = {
        "plans": {p: build_plan(config, p) for p in phases},
        "models": {},
        "checks": {},
    }
    literal = list(typing.get_args(MambaDType))
    ok = all(config["arms"][a] in literal for a in g3.ARM_NAMES)
    report["checks"]["mamba_dtype_literal"] = literal
    prompts = g3.load_math_prompts(config)
    lme_path = Path(args.lme) if args.lme else g3.LME_CONTAINER_PATH
    records = g3.load_lme(lme_path, config)
    by_id = {str(r["question_id"]): r for r in records}
    order = g3.lme_order(records, int(config["tasks"]["lme"]["selection_seed"]))
    report["checks"]["lme_order"] = {
        "questions": len(order),
        "order_sha256": g3.sha256_bytes("\n".join(order).encode()),
    }
    count = args.lme_count or len(order)
    for model_id in config["models"]:
        tokenizer = AutoTokenizer.from_pretrained(str(root / model_id))
        math_lens = [
            len(base.render_prompt_ids(tokenizer, g3.math_user_message(r, config), True))
            for r in prompts
        ]
        lme_lens = {}
        for qid in order[:count]:
            ids = base.render_prompt_ids(tokenizer, g3.lme_message(by_id[qid], config), False)
            lme_lens[qid] = len(ids)
        end = tokenizer.convert_tokens_to_ids(END_OF_TURN)
        # The thinking switch: the math prompt opens a thinking block, the long-context one
        # carries a closed empty block.
        sample_math = tokenizer.decode(base.render_prompt_ids(tokenizer, "x", True)[-6:])
        sample_lme = tokenizer.decode(base.render_prompt_ids(tokenizer, "x", False)[-8:])
        record: dict[str, Any] = {
            "math_prompt_len_max": max(math_lens),
            "lme_prompt_len": {
                "n": len(lme_lens),
                "min": min(lme_lens.values()),
                "max": max(lme_lens.values()),
                "sum": sum(lme_lens.values()),
            },
            "lme_prompt_len_by_order": [lme_lens[q] for q in order[:count]],
            "end_of_turn_id": end,
            "math_prompt_tail": sample_math,
            "lme_prompt_tail": sample_lme,
        }
        ok = ok and "<think>" in sample_math and "</think>" in sample_lme
        for task in g3.TASKS:
            spec = config["tasks"][task]
            longest = (
                record["math_prompt_len_max"] if task == "math" else record["lme_prompt_len"]["max"]
            )
            record[f"{task}_fits"] = (
                longest + spec["sampling"]["max_tokens"] <= spec["max_model_len"]
            )
            ok = ok and record[f"{task}_fits"]
            for arm in g3.ARM_NAMES:
                kwargs = g3.engine_kwargs(config, model_id, root / model_id, arm, task)
                engine_args = EngineArgs(**kwargs)
                record[f"engine_args_{arm}_{task}"] = {
                    "mamba_ssm_cache_dtype": engine_args.mamba_ssm_cache_dtype,
                    "max_model_len": engine_args.max_model_len,
                    "block_size": engine_args.block_size,
                    "enable_prefix_caching": engine_args.enable_prefix_caching,
                }
                ok = ok and engine_args.mamba_ssm_cache_dtype == config["arms"][arm]
                ok = ok and engine_args.block_size is None
            params = SamplingParams(**g3.sampling_kwargs(config, task, 4200007, end))
            record[f"sampling_{task}"] = {
                "top_k": params.top_k,
                "top_p": params.top_p,
                "presence_penalty": params.presence_penalty,
                "max_tokens": params.max_tokens,
                "seed": params.seed,
            }
        report["models"][model_id] = record
    judge = config["judge"]
    jtok = AutoTokenizer.from_pretrained(str(root / judge["model_id"]))
    q = by_id[order[0]]
    jmsg = g3.judge_message(q, "I don't know.")
    jids = base.render_prompt_ids(jtok, jmsg, bool(judge["enable_thinking"]))
    report["checks"]["judge_prompt_len"] = len(jids)
    report["checks"]["judge_tail"] = jtok.decode(jids[-8:])
    synthetic = [
        reader.Gauge(name="vllm:num_requests_running", labels={}, value=7.0),
        reader.Counter(name="vllm:num_preemptions", labels={}, value=3),
        reader.Gauge(name="vllm:kv_cache_usage_perc", labels={}, value=0.5),
    ]
    parsed = gb.parse_metrics(synthetic)
    ok = ok and parsed == {"running": 7.0, "preemptions": 3.0, "kv_usage": 0.5}
    report["checks"]["metrics_parser"] = parsed
    ok = ok and g3.math_equiv("\\frac{9}{5}", "1\\frac{4}{5}") and not g3.math_equiv("2", "3")
    report["ok"] = bool(ok)
    print(json.dumps(rb.jsonable(report), indent=2, sort_keys=True))
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    sub = parser.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan", allow_abbrev=False)
    plan.add_argument("--phase", choices=g3.PHASES, required=True)
    selftest = sub.add_parser("selftest", allow_abbrev=False)
    selftest.add_argument("--model-root", default=str(g3.MODEL_ROOT))
    selftest.add_argument("--lme", default=None)
    selftest.add_argument("--lme-count", type=int, default=None)
    run = sub.add_parser("run", allow_abbrev=False)
    run.add_argument("--phase", choices=g3.PHASES, required=True)
    run.add_argument("--model", required=True)
    run.add_argument("--arm", choices=g3.ARM_NAMES, required=True)
    run.add_argument("--tasks", nargs="+", choices=g3.TASKS, default=None)
    run.add_argument("--seeds", type=int, nargs="+", required=True)
    run.add_argument("--output-dir", required=True)
    run.add_argument("--allocation-minutes", type=float, required=True)
    run.add_argument("--longmemeval-path", default=str(g3.LME_CONTAINER_PATH))
    worker = sub.add_parser("worker", allow_abbrev=False)
    worker.add_argument("--phase", choices=g3.PHASES, required=True)
    worker.add_argument("--model", required=True)
    worker.add_argument("--arm", choices=g3.ARM_NAMES, required=True)
    worker.add_argument("--task", choices=g3.TASKS, required=True)
    worker.add_argument("--output-dir", required=True)
    worker.add_argument("--deadline", type=float, required=True)
    worker.add_argument("--reserve-s", type=float, default=45.0)
    worker.add_argument("--longmemeval-path", default=str(g3.LME_CONTAINER_PATH))
    judge = sub.add_parser("judge", allow_abbrev=False)
    judge.add_argument("--evidence", required=True)
    judge.add_argument("--expected-evidence-sha256", required=True)
    judge.add_argument("--output-dir", required=True)
    judge.add_argument("--allocation-minutes", type=float, required=True)
    args = parser.parse_args()
    if args.command == "plan":
        print(
            json.dumps(
                rb.jsonable(build_plan(g3.load_config(), args.phase)), indent=2, sort_keys=True
            )
        )
        return 0
    handlers = {
        "selftest": selftest_main,
        "run": run_main,
        "worker": worker_main,
        "judge": judge_main,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
