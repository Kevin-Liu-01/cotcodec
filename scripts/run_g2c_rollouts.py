#!/usr/bin/env python3
"""g2c-precision-layout-v1 (EXPLORATORY): vLLM rollouts, a saturation wave and the prefill for
the fp16 and bf16_b528 GDN-state arms.

Runs inside the digest-pinned cotcodec-vllm cu129 overlay (vLLM 0.31.0) on the docker-research
lane. Config: experiments/g2/g2c-precision-layout-v1.yaml, which is G2b's settings plus two arms:
``fp16`` (``mamba_ssm_cache_dtype=float16``, vLLM's own block size) and ``bf16_b528``
(``mamba_ssm_cache_dtype=bfloat16``, ``block_size=528``, the fp32 arm's block). G2b's own
rollout worker is reused piece by piece (``scripts/run_g2b_rollouts.py``: the phase runner,
metrics sampler, engine record, supervisor), so phase R, the wave and the prefill are G2b's.

Subcommands:

* ``plan``: the resolved plan. CPU only.
* ``selftest``: CPU only, no engine: config, prompt rendering with each model's tokenizer,
  EngineArgs and CacheConfig for every engine (the forced block is recorded as user-specified),
  the block-size rule against G2b's resolved blocks, SamplingParams, the parsers.
* ``run --model M --seeds 42 43 44 --output-dir O --allocation-minutes N [--smoke] [--probe]``:
  one GPU, the two arms in turn. Per arm: a rollout worker (phase R, then one saturation wave
  per saturation seed), then a prefill worker (a fresh engine with G2b's prefill settings and
  the arm's state dtype and block size) on that arm's rollouts. ``--probe`` (smoke only) first
  starts a dummy-weight eager engine with the fp32 state and block_size 272 and records what
  vLLM resolves. Writes tf-input.json with both arms' rollouts.
* ``worker``, ``prefill-worker``, ``probe-worker``: the subprocesses ``run`` supervises.
"""

from __future__ import annotations

import argparse
import contextlib
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
from harness import g2c_precision_layout as gc  # noqa: E402
from scripts import run_g2_rollouts as base  # noqa: E402
from scripts import run_g2b_rollouts as rb  # noqa: E402

END_OF_TURN = base.END_OF_TURN
#: Seconds an arm needs beyond its phase-R budget (engine start, wave, prefill, shutdown).
ARM_OVERHEAD_S = 300.0
SMOKE_ARM_OVERHEAD_S = 200.0


# --------------------------------------------------------------------------- plan


def engine_kwargs(
    config: dict[str, Any], model_id: str, model_dir: Path, arm: str, prefill: bool = False
) -> dict[str, Any]:
    """G2b's engine kwargs for this arm's state dtype, plus its block size when forced."""

    kwargs = rb.engine_kwargs(
        config, model_id, model_dir, gc.arm_state_dtype(config, arm), prefill=prefill
    )
    block = gc.arm_block_size(config, arm)
    if block is not None:
        kwargs["block_size"] = block
    return kwargs


def probe_kwargs(config: dict[str, Any], model_id: str, model_dir: Path) -> dict[str, Any]:
    probe = config["probe"]
    kwargs = rb.engine_kwargs(config, model_id, model_dir, probe["mamba_ssm_cache_dtype"])
    kwargs.update(
        block_size=int(probe["block_size"]),
        load_format=probe["load_format"],
        enforce_eager=bool(probe["enforce_eager"]),
    )
    return kwargs


def smoke_config(config: dict[str, Any]) -> dict[str, Any]:
    """G2b's smoke shape (4 prompts x 3 seeds, 768 tokens, 40 s; one 128-token request per
    prompt in the wave), recorded as smoke, not data."""

    return rb.smoke_config(config)


def build_plan(config: dict[str, Any]) -> dict[str, Any]:
    prompts = g2.load_prompts(config)
    models: dict[str, Any] = {}
    for model_id in config["models"]:
        arms = {}
        for arm in gc.ARM_NAMES:
            rollouts = gc.rollout_requests(config, prompts, model_id, arm)
            arms[arm] = {
                "state_dtype": gc.arm_state_dtype(config, arm),
                "block_size": gc.arm_block_size(config, arm),
                "engine_kwargs": engine_kwargs(config, model_id, g2.MODEL_ROOT / model_id, arm),
                "prefill_engine_kwargs": engine_kwargs(
                    config, model_id, g2.MODEL_ROOT / model_id, arm, prefill=True
                ),
                "rollout_requests": len(rollouts),
                "rollout_max_tokens": rollouts[0]["max_tokens"],
                "saturation_requests_per_wave": {
                    s: len(gb.saturation_requests(config, prompts, model_id, s))
                    for s in config["saturation"]["seeds"]
                },
            }
        models[model_id] = {
            "arms": arms,
            "gen_seconds": config["rollouts"]["gen_seconds"][model_id],
            "probe_engine_kwargs": probe_kwargs(config, model_id, g2.MODEL_ROOT / model_id),
        }
    return {
        "experiment_id": config["experiment_id"],
        "claim_level": config["claim_level"],
        "base_experiment_id": config["base_experiment_id"],
        "seeds": config["seeds"],
        "saturation_seeds": config["saturation"]["seeds"],
        "models": models,
    }


def nonfinite(values: list[float]) -> int:
    return sum(1 for v in values if not math.isfinite(v))


# --------------------------------------------------------------------------- rollout worker


def worker_main(args: argparse.Namespace) -> int:
    import numpy as np
    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams
    from vllm.inputs import TokensPrompt

    config = gc.load_config()
    if args.smoke:
        config = smoke_config(config)
    prompts = g2.load_prompts(config)
    model_id, arm = args.model, args.arm
    model_dir = g2.MODEL_ROOT / model_id
    out = Path(args.output_dir) / f"{model_id}-{arm}"
    out.mkdir(parents=True, exist_ok=True)
    flag = base.StopFlag()
    signal.signal(signal.SIGTERM, flag.handler)
    signal.signal(signal.SIGUSR1, flag.handler)
    log_path = out / "worker-progress.jsonl"

    def log(event: str, **fields: Any) -> None:
        record = {"utc": g2.utc_now(), "event": event, "model": model_id, "arm": arm, **fields}
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        print(json.dumps(record, sort_keys=True), flush=True)

    tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
    thinking = bool(config["prompts"]["enable_thinking"])
    prompt_ids = {
        row["prompt_index"]: base.render_prompt_ids(
            tokenizer, g2.user_message(row, config), thinking
        )
        for row in prompts
    }
    end_of_turn = tokenizer.convert_tokens_to_ids(END_OF_TURN)
    kwargs = engine_kwargs(config, model_id, model_dir, arm)
    log("engine-start", engine_kwargs=kwargs, end_of_turn_id=end_of_turn, smoke=args.smoke)
    t0 = time.time()
    llm = LLM(**kwargs)
    info = rb.engine_info(llm)
    info["init_s"] = round(time.time() - t0, 1)
    g2.write_json(out / "engine.json", info)
    log("engine-ready", **info)
    summary: dict[str, Any] = {
        "model": model_id,
        "arm": arm,
        "state_dtype": gc.arm_state_dtype(config, arm),
        "block_size_setting": gc.arm_block_size(config, arm),
        "smoke": args.smoke,
        "engine": info,
        "phases": {},
    }
    interval = float(config["rollouts"]["stats_interval_s"])
    sampling = config["rollouts"]["sampling"]

    # Phase R: long reasoning rollouts (G2b's requests, sampling and time budget).
    requests = gc.rollout_requests(config, prompts, model_id, arm)
    items = []
    for req in requests:
        params = SamplingParams(
            n=1,
            temperature=sampling["temperature"],
            top_p=sampling["top_p"],
            top_k=sampling["top_k"],
            max_tokens=req["max_tokens"],
            logprobs=sampling["logprobs"],
            seed=req["seed"],
            stop_token_ids=[end_of_turn],
            detokenize=False,
        )
        items.append(
            (
                req["sequence_id"],
                TokensPrompt(prompt_token_ids=prompt_ids[req["prompt_index"]]),
                params,
            )
        )
    gen_seconds = float(config["rollouts"]["gen_seconds"][model_id])
    log("phase-R-start", requests=len(items), gen_seconds=gen_seconds)
    r_stop = min(args.deadline - args.reserve_s, time.time() + gen_seconds)
    state, steps, sampler, rinfo = rb.run_phase(
        llm, items, r_stop, flag, interval, keep_tokens=True
    )
    rinfo["drain_steps"] = rb.drain(llm)
    rb.save_stats(out / "phase-R-stats.npz", steps, sampler)
    total = sum(st["count"] for st in state.values())
    summary["phases"]["R"] = gb.summarize_phase(
        steps, sampler.samples, len(items), rinfo["finished"], total, rinfo["wall_s"]
    ) | {"info": rinfo, "gen_seconds": gen_seconds}
    log("phase-R-done", **summary["phases"]["R"])
    sequences = []
    for req in requests:
        st = state[req["sequence_id"]]
        if not st["token_ids"]:
            continue
        sequences.append(
            req
            | {
                "prompt_ids": prompt_ids[req["prompt_index"]],
                "completion_ids": st["token_ids"],
                "logp_decode": st["logp"],
                "finish_reason": st["finish_reason"] if st["finished"] else "cut_at_time_budget",
                "stop_reason": st["stop_reason"],
                "missing_logprobs": st["missing_logprobs"],
                "nonfinite_logprobs": nonfinite(st["logp"]),
            }
        )
    offsets = [0]
    for s in sequences:
        offsets.append(offsets[-1] + len(s["completion_ids"]))
    np.savez_compressed(
        out / "tokens.npz",
        offsets=np.asarray(offsets, dtype=np.int64),
        prompt_len=np.asarray([len(s["prompt_ids"]) for s in sequences], dtype=np.int32),
        token_ids=np.asarray([t for s in sequences for t in s["completion_ids"]], dtype=np.int32),
        logp_decode=np.asarray([v for s in sequences for v in s["logp_decode"]], dtype=np.float32),
    )
    with gzip.open(out / "texts.jsonl.gz", "wt", encoding="utf-8") as handle:
        for s in sequences:
            text = tokenizer.decode(s["completion_ids"], skip_special_tokens=False)
            handle.write(json.dumps({"sequence_id": s["sequence_id"], "text": text}) + "\n")
    keys = (
        "sequence_id",
        "prompt_index",
        "seed",
        "max_tokens",
        "finish_reason",
        "stop_reason",
        "missing_logprobs",
        "nonfinite_logprobs",
    )
    g2.write_json(
        out / "sequences.json",
        {
            "model_id": model_id,
            "arm": arm,
            "state_dtype": gc.arm_state_dtype(config, arm),
            "block_size_setting": gc.arm_block_size(config, arm),
            "engine_kwargs": kwargs,
            "sampling": sampling,
            "end_of_turn_id": end_of_turn,
            "sequence_order": [s["sequence_id"] for s in sequences],
            "sequences": [
                {k: s[k] for k in keys}
                | {"prompt_len": len(s["prompt_ids"]), "completion_len": len(s["completion_ids"])}
                for s in sequences
            ],
            "requests": len(items),
        },
    )
    g2.write_json(
        out / "tf-sequences.json",
        [
            {
                "sequence_id": s["sequence_id"],
                "model_id": model_id,
                "arm": arm,
                "prompt_index": s["prompt_index"],
                "seed": s["seed"],
                "prompt_ids": s["prompt_ids"],
                "completion_ids": s["completion_ids"],
            }
            for s in sequences
        ],
    )
    log(
        "phase-R-saved",
        sequences=len(sequences),
        tokens=offsets[-1],
        nonfinite=sum(s["nonfinite_logprobs"] for s in sequences),
    )
    del state, items, sequences

    # Phase S: one fixed-length saturation wave per saturation seed (G2b's wave shape).
    sat = config["saturation"]
    previous = 0.0
    for seed in sat["seeds"]:
        name = f"S{seed}"
        needed = max(previous * 1.3, 60.0) + args.reserve_s
        if flag.event.is_set() or args.deadline - time.time() < needed:
            summary["phases"][name] = {
                "status": "skipped",
                "remaining_s": round(args.deadline - time.time(), 1),
                "needed_s": round(needed, 1),
                "signal": flag.reason,
            }
            log("phase-S-skipped", seed=seed, **summary["phases"][name])
            continue
        wave = gb.saturation_requests(config, prompts, model_id, seed)
        witems = []
        for req in wave:
            params = SamplingParams(
                n=1,
                temperature=sat["temperature"],
                top_p=1.0,
                top_k=0,
                max_tokens=req["output_tokens"],
                ignore_eos=True,
                logprobs=sat["logprobs"],
                seed=req["seed"],
                detokenize=False,
            )
            witems.append(
                (
                    req["request_id"],
                    TokensPrompt(prompt_token_ids=prompt_ids[req["prompt_index"]]),
                    params,
                )
            )
        log("phase-S-start", seed=seed, requests=len(witems))
        s_stop = min(args.deadline - args.reserve_s, time.time() + float(sat["wave_timeout_s"]))
        wstate, wsteps, wsampler, winfo = rb.run_phase(
            llm, witems, s_stop, flag, interval, keep_tokens=False
        )
        winfo["drain_steps"] = rb.drain(llm)
        rb.save_stats(out / f"phase-{name}-stats.npz", wsteps, wsampler)
        produced = sum(st["count"] for st in wstate.values())
        expected = sum(req["output_tokens"] for req in wave)
        summary["phases"][name] = gb.summarize_phase(
            wsteps, wsampler.samples, len(witems), winfo["finished"], produced, winfo["wall_s"]
        ) | {
            "info": winfo,
            "expected_output_tokens": expected,
            "complete": winfo["finished"] == len(witems) and produced == expected,
            "status": "complete" if winfo["finished"] == len(witems) else "partial",
        }
        previous = winfo["wall_s"]
        log(
            "phase-S-done",
            seed=seed,
            **{k: v for k, v in summary["phases"][name].items() if k != "info"},
        )
    g2.write_json(out / "summary.json", summary)
    complete = all(
        p.get("status", "complete") == "complete" for k, p in summary["phases"].items() if k != "R"
    )
    code = 0 if complete and rinfo["unmatched"] == 0 else 3
    g2.write_json(out / "done.json", {"exit": code, "utc": g2.utc_now()})
    closer = threading.Thread(target=lambda: llm.llm_engine.engine_core.shutdown(), daemon=True)
    closer.start()
    closer.join(timeout=15)
    sys.stdout.flush()
    os._exit(code)


# --------------------------------------------------------------------------- prefill worker


def prefill_worker_main(args: argparse.Namespace) -> int:
    import numpy as np
    from vllm import LLM, SamplingParams
    from vllm.inputs import TokensPrompt
    from vllm.sampling_params import RequestOutputKind

    config = gc.load_config()
    model_id, arm = args.model, args.arm
    out = Path(args.output_dir)
    flag = base.StopFlag()
    signal.signal(signal.SIGTERM, flag.handler)
    signal.signal(signal.SIGUSR1, flag.handler)
    seqs = [
        s
        for s in json.loads(Path(args.input).read_text(encoding="utf-8"))
        if s["model_id"] == model_id and s["arm"] == arm
    ]
    kwargs = engine_kwargs(config, model_id, g2.MODEL_ROOT / model_id, arm, prefill=True)
    progress = out / f"prefill-{arm}-progress.jsonl"

    def log(event: str, **fields: Any) -> None:
        record = {"utc": g2.utc_now(), "event": event, "model": model_id, "arm": arm, **fields}
        with progress.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        print(json.dumps(record, sort_keys=True), flush=True)

    log("engine-start", engine_kwargs=kwargs, sequences=len(seqs))
    t0 = time.time()
    llm = LLM(**kwargs)
    info = rb.engine_info(llm)
    info["init_s"] = round(time.time() - t0, 1)
    log("engine-ready", **info)
    engine = llm.llm_engine
    index = {}
    for i, s in enumerate(seqs):
        params = SamplingParams(
            max_tokens=1,
            temperature=1.0,
            seed=config["seeds"][0],
            prompt_logprobs=config["prefill"]["prompt_logprobs"],
            detokenize=False,
        )
        params.output_kind = RequestOutputKind.FINAL_ONLY
        ours = "P/" + s["sequence_id"]
        engine.add_request(
            ours, TokensPrompt(prompt_token_ids=s["prompt_ids"] + s["completion_ids"]), params
        )
        index[ours] = i
    results: dict[int, list[float]] = {}
    started = time.time()
    stopped = None
    while engine.has_unfinished_requests():
        if time.time() >= args.deadline or flag.event.is_set():
            stopped = flag.reason or "deadline"
            with contextlib.suppress(Exception):
                engine.abort_request(
                    [k for k, i in index.items() if i not in results], internal=False
                )
            break
        for output in engine.step():
            i = index.get(str(output.request_id))
            if i is None or not output.finished or output.prompt_logprobs is None:
                continue
            s = seqs[i]
            results[i] = base.prefill_logprobs(
                len(s["prompt_ids"]), s["completion_ids"], output.prompt_logprobs
            )
    wall = time.time() - started
    lengths = [len(s["completion_ids"]) for s in seqs]
    offsets = np.concatenate([[0], np.cumsum(lengths)]).astype(np.int64)
    logp = np.full(int(offsets[-1]), np.nan, dtype=np.float32)
    for i, values in results.items():
        logp[offsets[i] : offsets[i + 1]] = values
    np.savez_compressed(out / f"prefill-{arm}.npz", offsets=offsets, logp_prefill=logp)
    record = {
        "model": model_id,
        "arm": arm,
        "state_dtype": gc.arm_state_dtype(config, arm),
        "block_size_setting": gc.arm_block_size(config, arm),
        "engine": info,
        "sequences": len(seqs),
        "scored": len(results),
        "stopped": stopped,
        "wall_s": round(wall, 2),
        "prompt_tokens": int(sum(len(s["prompt_ids"]) + len(s["completion_ids"]) for s in seqs)),
        "sequence_order": [s["sequence_id"] for s in seqs],
    }
    record["prompt_tok_per_s"] = record["prompt_tokens"] / wall if wall > 0 else None
    g2.write_json(out / f"prefill-{arm}.json", record)
    code = 0 if len(results) == len(seqs) else 3
    log(
        "prefill-done", **{k: v for k, v in record.items() if k not in ("sequence_order", "engine")}
    )
    g2.write_json(out / f"prefill-{arm}-done.json", {"exit": code, "utc": g2.utc_now()})
    closer = threading.Thread(target=lambda: llm.llm_engine.engine_core.shutdown(), daemon=True)
    closer.start()
    closer.join(timeout=15)
    sys.stdout.flush()
    os._exit(code)


# --------------------------------------------------------------------------- probe worker


def probe_worker_main(args: argparse.Namespace) -> int:
    """Start a dummy-weight eager engine with the fp32 state and the bf16 arm's block size and
    record what vLLM resolves (a config probe, not data)."""

    from vllm import LLM

    config = gc.load_config()
    out = Path(args.output_dir)
    kwargs = probe_kwargs(config, args.model, g2.MODEL_ROOT / args.model)
    record: dict[str, Any] = {"model": args.model, "engine_kwargs": kwargs, "utc": g2.utc_now()}
    code = 0
    try:
        t0 = time.time()
        llm = LLM(**kwargs)
        record["engine"] = rb.engine_info(llm)
        record["init_s"] = round(time.time() - t0, 1)
    except Exception as exc:  # noqa: BLE001 - the refusal is itself the record
        record["error"] = repr(exc)[:4000]
        code = 3
        llm = None
    g2.write_json(out / "probe.json", record)
    g2.write_json(out / "probe-done.json", {"exit": code, "utc": g2.utc_now()})
    if llm is not None:
        closer = threading.Thread(target=lambda: llm.llm_engine.engine_core.shutdown(), daemon=True)
        closer.start()
        closer.join(timeout=15)
    sys.stdout.flush()
    os._exit(code)


# --------------------------------------------------------------------------- driver


def arm_needed_s(config: dict[str, Any], model_id: str, smoke: bool) -> float:
    gen = float(config["rollouts"]["gen_seconds"][model_id])
    return gen + (SMOKE_ARM_OVERHEAD_S if smoke else ARM_OVERHEAD_S)


def run_main(args: argparse.Namespace) -> int:
    config = gc.load_config()
    if list(args.seeds) != config["seeds"]:
        raise gc.G2cConfigError("--seeds must equal the config's declared seeds")
    if args.model not in config["models"]:
        raise gc.G2cConfigError(f"unknown model {args.model}")
    if args.probe and not args.smoke:
        raise gc.G2cConfigError("the probe runs in the smoke job only")
    plan_config = smoke_config(config) if args.smoke else config
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    stop_at, source = g2.deadline(args.allocation_minutes)
    summary: dict[str, Any] = {
        "experiment_id": config["experiment_id"],
        "claim_level": "exploratory",
        "job": "rollouts",
        "model": args.model,
        "smoke": args.smoke,
        "started_at": g2.utc_now(),
        "allocation_minutes": args.allocation_minutes,
        "deadline_source": source,
        "deadline_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(stop_at)),
        "plan": build_plan(plan_config)["models"][args.model],
        "arms": {},
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
    deadline = ["--deadline", f"{stop_at:.3f}"]
    if args.probe:
        argv = [sys.executable, script, "probe-worker", "--model", args.model, "--output-dir"]
        record = rb.supervise(
            argv + [str(out)],
            env,
            out / f"worker-probe-{args.model}.log",
            out / "probe-done.json",
            min(stop_at, time.time() + 300),
            state,
        )
        probe_path = out / "probe.json"
        record["probe"] = (
            json.loads(probe_path.read_text(encoding="utf-8")) if probe_path.is_file() else None
        )
        summary["probe"] = record
        g2.write_json(out / "summary.json", summary)
    sequences: list[dict[str, Any]] = []
    for arm in gc.ARM_NAMES:
        remaining = stop_at - time.time()
        needed = arm_needed_s(plan_config, args.model, args.smoke)
        if state["signal"] or remaining < needed:
            summary["arms"][arm] = {
                "status": "skipped",
                "remaining_s": round(remaining, 1),
                "needed_s": needed,
                "signal": state["signal"],
            }
            g2.write_json(out / "summary.json", summary)
            continue
        worker_dir = out / f"{args.model}-{arm}"
        worker_dir.mkdir(parents=True, exist_ok=True)
        argv = [sys.executable, script, "worker", "--model", args.model, "--arm", arm]
        argv += ["--output-dir", str(out), *deadline] + (["--smoke"] if args.smoke else [])
        rollout = rb.supervise(
            argv,
            env,
            out / f"worker-{args.model}-{arm}.log",
            worker_dir / "done.json",
            stop_at,
            state,
        )
        done = rollout.get("worker_done") or {}
        rollout["status"] = "complete" if done.get("exit") == 0 else "partial" if done else "failed"
        arm_record: dict[str, Any] = {"rollouts": rollout}
        tf_path = worker_dir / "tf-sequences.json"
        arm_sequences = json.loads(tf_path.read_text(encoding="utf-8")) if tf_path.is_file() else []
        sequences.extend(arm_sequences)
        if arm_sequences and not state["signal"]:
            argv = [sys.executable, script, "prefill-worker", "--model", args.model, "--arm", arm]
            argv += ["--input", str(tf_path), "--output-dir", str(out), *deadline]
            prefill = rb.supervise(
                argv,
                env,
                out / f"worker-prefill-{args.model}-{arm}.log",
                out / f"prefill-{arm}-done.json",
                stop_at,
                state,
            )
            pdone = prefill.get("worker_done") or {}
            prefill["status"] = (
                "complete" if pdone.get("exit") == 0 else "partial" if pdone else "failed"
            )
            arm_record["prefill"] = prefill
        arm_record["sequences"] = len(arm_sequences)
        summary["arms"][arm] = arm_record
        g2.write_json(out / "summary.json", summary)
    g2.write_json(
        out / "tf-input.json",
        {
            "experiment_id": config["experiment_id"],
            "git_sha": os.environ.get("COTCODEC_GIT_SHA"),
            "sequences": sequences,
        },
    )
    summary["tf_input_sha256"] = g2.sha256_file(out / "tf-input.json")
    summary["tf_input_sequences"] = len(sequences)
    summary["finished_at"] = g2.utc_now()
    summary["signal"] = state["signal"]
    g2.write_json(out / "summary.json", summary)
    if state["signal"]:
        g2.write_checkpoint_marker(
            "SIGUSR1" if state["signal"] == "SIGUSR1" else "SIGTERM",
            "g2c rollouts: finished arms saved; no resume (a rerun is a new job)",
        )
    ok = all(
        a.get("rollouts", {}).get("status") == "complete"
        and a.get("prefill", {}).get("status") == "complete"
        for a in summary["arms"].values()
    ) and len(summary["arms"]) == len(gc.ARM_NAMES)
    return 0 if ok else 3


# --------------------------------------------------------------------------- selftest


def attention_page_per_token(model_dir: Path) -> int:
    """K and V bytes per token per attention layer from the checkpoint's config.json (bf16)."""

    cfg = json.loads((model_dir / "config.json").read_text(encoding="utf-8"))
    text = cfg.get("text_config", cfg)
    heads = int(text["num_key_value_heads"])
    head_dim = int(text.get("head_dim") or text["hidden_size"] // text["num_attention_heads"])
    return gc.attention_page_bytes_per_token(heads, head_dim)


def selftest_main(args: argparse.Namespace) -> int:
    """CPU only: everything the jobs construct before an engine starts."""

    import typing

    from transformers import AutoTokenizer
    from vllm import SamplingParams
    from vllm.config.cache import CacheConfig, MambaDType
    from vllm.engine.arg_utils import EngineArgs
    from vllm.v1.metrics import reader

    config = gc.load_config()
    prompts = g2.load_prompts(config)
    report: dict[str, Any] = {"plan": build_plan(config), "models": {}, "checks": {}}
    literal = list(typing.get_args(MambaDType))
    report["checks"]["mamba_dtype_literal"] = literal
    ok = all(gc.arm_state_dtype(config, a) in literal for a in gc.ARM_NAMES)
    root = Path(args.model_root)
    for model_id in config["models"]:
        tokenizer = AutoTokenizer.from_pretrained(str(root / model_id))
        lengths = [
            len(
                base.render_prompt_ids(
                    tokenizer, g2.user_message(r, config), config["prompts"]["enable_thinking"]
                )
            )
            for r in prompts
        ]
        reqs = gc.rollout_requests(config, prompts, model_id, "fp16")
        record: dict[str, Any] = {
            "prompt_len_max": max(lengths),
            "end_of_turn_id": tokenizer.convert_tokens_to_ids(END_OF_TURN),
            "fits": max(lengths) + reqs[0]["max_tokens"] + 1 <= config["engine"]["max_model_len"],
            "rollout_requests": len(reqs),
        }
        for arm in gc.ARM_NAMES:
            for prefill in (False, True):
                kwargs = engine_kwargs(config, model_id, root / model_id, arm, prefill)
                engine_args = EngineArgs(**kwargs)
                cache = CacheConfig(
                    block_size=engine_args.block_size,
                    mamba_ssm_cache_dtype=engine_args.mamba_ssm_cache_dtype,
                )
                record[f"engine_args_{arm}{'_prefill' if prefill else ''}"] = {
                    "mamba_ssm_cache_dtype": engine_args.mamba_ssm_cache_dtype,
                    "block_size": engine_args.block_size,
                    "cache_config_block_size": cache.block_size,
                    "user_specified_block_size": cache.user_specified_block_size,
                    "gpu_memory_utilization": engine_args.gpu_memory_utilization,
                    "max_num_batched_tokens": engine_args.max_num_batched_tokens,
                }
        forced = record["engine_args_bf16_b528"]
        ok = ok and forced["cache_config_block_size"] == 528 and forced["user_specified_block_size"]
        ok = ok and record["engine_args_fp16"]["block_size"] is None
        attn = attention_page_per_token(root / model_id)
        rule = {}
        for name, dtype, user in (
            ("fp32", "float32", None),
            ("bf16", "bfloat16", None),
            ("fp16", "float16", None),
            ("bf16_b528", "bfloat16", 528),
            ("fp32_b272", "float32", 272),
        ):
            page = gb.gdn_page_bytes(config, dtype)
            block = gc.resolved_block_tokens(page, attn, user)
            rule[name] = {
                "gdn_page_bytes": page,
                "block_tokens": block,
                "mamba_padding_pct": round(gc.mamba_padding_pct(page, attn, block), 2),
            }
        record["attention_page_bytes_per_token"] = attn
        record["block_rule"] = rule
        ok = ok and record["fits"]
        # G2b's engines resolved 528 (fp32) and 272 (bf16), with 0.76% and 1.49% padding.
        ok = ok and rule["fp32"]["block_tokens"] == 528 and rule["bf16"]["block_tokens"] == 272
        ok = ok and rule["fp32"]["mamba_padding_pct"] == 0.76
        ok = ok and rule["bf16"]["mamba_padding_pct"] == 1.49
        ok = ok and rule["fp16"]["block_tokens"] == 272 and rule["bf16_b528"]["block_tokens"] == 528
        report["models"][model_id] = record
    probe = probe_kwargs(config, "qwen3.5-4b", root / "qwen3.5-4b")
    probe_args = EngineArgs(**probe)
    report["checks"]["probe_engine_args"] = {
        "block_size": probe_args.block_size,
        "mamba_ssm_cache_dtype": probe_args.mamba_ssm_cache_dtype,
        "load_format": str(probe_args.load_format),
        "enforce_eager": probe_args.enforce_eager,
    }
    ok = ok and probe_args.block_size == 272 and probe_args.enforce_eager
    params = [
        SamplingParams(
            n=1, temperature=1.0, top_p=1.0, top_k=0, max_tokens=32768, logprobs=0, seed=42,
            stop_token_ids=[1], detokenize=False,
        ),
        SamplingParams(
            n=1, temperature=1.0, top_p=1.0, top_k=0, max_tokens=2048, ignore_eos=True,
            logprobs=0, seed=gb.saturation_seed(42, 63, 7), detokenize=False,
        ),
        SamplingParams(max_tokens=1, temperature=1.0, seed=42, prompt_logprobs=0, detokenize=False),
    ]  # fmt: skip
    report["checks"]["sampling_params"] = [p.max_tokens for p in params]
    synthetic = [
        reader.Gauge(name="vllm:num_requests_running", labels={}, value=7.0),
        reader.Counter(name="vllm:num_preemptions", labels={}, value=3),
        reader.Gauge(name="vllm:kv_cache_usage_perc", labels={}, value=0.5),
    ]
    parsed = gb.parse_metrics(synthetic)
    report["checks"]["metrics_parser"] = parsed
    ok = ok and parsed == {"running": 7.0, "preemptions": 3.0, "kv_usage": 0.5}
    tokens = [5, 7, 9]
    decode = [{5: base._Lp(-0.5)}, {7: base._Lp(-1.0)}, {9: base._Lp(-2.0)}]
    values, missing = base.delta_logprobs(tokens, decode)
    ok = ok and values == [-0.5, -1.0, -2.0] and missing == 0
    ok = ok and nonfinite([1.0, float("nan"), float("-inf")]) == 2
    report["ok"] = bool(ok)
    print(json.dumps(rb.jsonable(report), indent=2, sort_keys=True))
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("plan")
    selftest = sub.add_parser("selftest", allow_abbrev=False)
    selftest.add_argument("--model-root", default=str(g2.MODEL_ROOT))
    run = sub.add_parser("run", allow_abbrev=False)
    run.add_argument("--model", required=True)
    run.add_argument("--seeds", type=int, nargs="+", required=True)
    run.add_argument("--output-dir", required=True)
    run.add_argument("--allocation-minutes", type=float, required=True)
    run.add_argument("--smoke", action="store_true")
    run.add_argument("--probe", action="store_true")
    worker = sub.add_parser("worker", allow_abbrev=False)
    worker.add_argument("--model", required=True)
    worker.add_argument("--arm", required=True, choices=gc.ARM_NAMES)
    worker.add_argument("--output-dir", required=True)
    worker.add_argument("--deadline", type=float, required=True)
    worker.add_argument("--reserve-s", type=float, default=30.0)
    worker.add_argument("--smoke", action="store_true")
    pworker = sub.add_parser("prefill-worker", allow_abbrev=False)
    pworker.add_argument("--model", required=True)
    pworker.add_argument("--arm", required=True, choices=gc.ARM_NAMES)
    pworker.add_argument("--input", required=True)
    pworker.add_argument("--output-dir", required=True)
    pworker.add_argument("--deadline", type=float, required=True)
    probe = sub.add_parser("probe-worker", allow_abbrev=False)
    probe.add_argument("--model", required=True)
    probe.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    if args.command == "plan":
        print(json.dumps(rb.jsonable(build_plan(gc.load_config())), indent=2, sort_keys=True))
        return 0
    handlers = {
        "selftest": selftest_main,
        "run": run_main,
        "worker": worker_main,
        "prefill-worker": prefill_worker_main,
        "probe-worker": probe_worker_main,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
