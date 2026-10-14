#!/usr/bin/env python3
"""g2b-state-dtype-v1 (EXPLORATORY): vLLM rollouts, saturation waves and the paired prefill.

Runs inside the digest-pinned cotcodec-vllm cu129 overlay (vLLM 0.31.0) on the docker-research
lane. Config: experiments/g2/g2b-state-dtype-v1.yaml. The GDN recurrent-state dtype is vLLM's
``mamba_ssm_cache_dtype`` (CacheConfig, MambaDType; --mamba-ssm-cache-dtype): "auto" (the
checkpoint's float32) or "bfloat16".

Subcommands:

* ``plan``: the resolved plan. CPU only.
* ``selftest``: CPU only, no engine: config, prompt rendering with each model's tokenizer,
  EngineArgs and SamplingParams construction for every engine and request type, the output and
  metrics parsers.
* ``run --model M --state-dtype D --seeds 42 43 44 --output-dir O --allocation-minutes N``: one
  engine (a worker subprocess). Phase R: long reasoning rollouts, all submitted at once, with
  streamed sampled-token log-probs; phase S: one fixed-length saturation wave per seed. Both
  phases sample the engine's own metrics (running, waiting, KV usage, preemptions).
* ``merge --inputs A B --output F``: the two arms' tf-input.json files as one (CPU).
* ``prefill --evidence F --expected-evidence-sha256 H --model M --output-dir O
  --allocation-minutes N``: every sequence of F re-scored by vLLM prefill (prompt_logprobs),
  once per state dtype, each in a fresh engine.
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
from harness import g2b_state_dtype as gb  # noqa: E402
from scripts import run_g2_rollouts as base  # noqa: E402

END_OF_TURN = base.END_OF_TURN


# --------------------------------------------------------------------------- plan


def engine_kwargs(
    config: dict[str, Any], model_id: str, model_dir: Path, state_dtype: str, prefill: bool = False
) -> dict[str, Any]:
    if state_dtype not in gb.VLLM_MAMBA_DTYPES:
        raise gb.G2bConfigError(f"{state_dtype!r} is not a vLLM MambaDType")
    s = gb.engine_settings(config, model_id, prefill)
    return {
        "model": str(model_dir),
        "tokenizer": str(model_dir),
        "trust_remote_code": False,
        "dtype": s["dtype"],
        "seed": config["seeds"][0],
        "max_model_len": s["max_model_len"],
        "gpu_memory_utilization": s["gpu_memory_utilization"],
        "max_num_seqs": s["max_num_seqs"],
        "max_num_batched_tokens": s["max_num_batched_tokens"],
        "enable_prefix_caching": s["enable_prefix_caching"],
        "logprobs_mode": s["logprobs_mode"],
        "limit_mm_per_prompt": dict(s["limit_mm_per_prompt"]),
        "disable_log_stats": bool(s["disable_log_stats"]),
        "mamba_ssm_cache_dtype": state_dtype,
    }


def smoke_config(config: dict[str, Any]) -> dict[str, Any]:
    """A tiny version of the plan for the end-to-end smoke job (recorded as smoke, not data)."""

    smoke = json.loads(json.dumps(config))
    smoke["rollouts"]["prompt_count"] = 4
    smoke["rollouts"]["moe_prompt_count"] = 4
    smoke["rollouts"]["sampling"]["max_tokens"] = 768
    smoke["rollouts"]["moe_max_tokens"] = 768
    smoke["rollouts"]["gen_seconds"] = {m: 40 for m in config["models"]}
    smoke["saturation"]["requests_per_prompt"] = {m: 1 for m in config["models"]}
    smoke["saturation"]["output_tokens"] = {m: 128 for m in config["models"]}
    smoke["saturation"]["wave_timeout_s"] = 60
    return smoke


def build_plan(config: dict[str, Any]) -> dict[str, Any]:
    prompts = g2.load_prompts(config)
    models: dict[str, Any] = {}
    for model_id in config["models"]:
        arms = {}
        for arm in gb.ARM_NAMES:
            dtype = gb.vllm_state_dtype(config, arm)
            rollouts = gb.rollout_requests(config, prompts, model_id, arm)
            waves = {
                s: len(gb.saturation_requests(config, prompts, model_id, s))
                for s in config["seeds"]
            }
            arms[arm] = {
                "state_dtype": dtype,
                "engine_kwargs": engine_kwargs(config, model_id, g2.MODEL_ROOT / model_id, dtype),
                "rollout_requests": len(rollouts),
                "rollout_max_tokens": rollouts[0]["max_tokens"],
                "saturation_requests_per_wave": waves,
            }
        models[model_id] = {
            "arms": arms,
            "gen_seconds": config["rollouts"]["gen_seconds"][model_id],
        }
    return {
        "experiment_id": config["experiment_id"],
        "claim_level": config["claim_level"],
        "seeds": config["seeds"],
        "models": models,
    }


# --------------------------------------------------------------------------- engine helpers


def jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    return str(value)


def engine_info(llm: Any) -> dict[str, Any]:
    vc = llm.llm_engine.vllm_config
    cc = vc.cache_config
    info: dict[str, Any] = {
        key: jsonable(getattr(cc, key, None))
        for key in (
            "block_size",
            "num_gpu_blocks",
            "mamba_ssm_cache_dtype",
            "mamba_cache_dtype",
            "mamba_page_size_padded",
            "mamba_block_size",
            "mamba_cache_mode",
            "cache_dtype",
            "gpu_memory_utilization",
            "enable_prefix_caching",
        )
    }
    info["model_dtype"] = str(vc.model_config.dtype)
    info["max_num_seqs"] = vc.scheduler_config.max_num_seqs
    info["max_num_batched_tokens"] = vc.scheduler_config.max_num_batched_tokens
    info["max_model_len"] = vc.model_config.max_model_len
    try:
        info["cache_config_info"] = gb.cache_config_info(llm.get_metrics())
    except Exception as exc:  # noqa: BLE001 - recorded
        info["cache_config_info_error"] = repr(exc)
    return info


class Sampler:
    """Metric snapshots from LLM.get_metrics() at most every ``interval`` seconds."""

    def __init__(self, llm: Any, interval: float) -> None:
        self.llm = llm
        self.interval = interval
        self.samples: list[dict[str, float]] = []
        self.errors = 0
        self.t0 = time.time()
        self.last = -1e9

    def take(self, force: bool = False) -> None:
        now = time.time()
        if not force and now - self.last < self.interval:
            return
        self.last = now
        try:
            values = gb.parse_metrics(self.llm.get_metrics())
        except Exception:  # noqa: BLE001 - counted; the phase goes on
            self.errors += 1
            return
        values["t"] = round(now - self.t0, 4)
        self.samples.append(values)


def run_phase(
    llm: Any,
    items: list[tuple[str, Any, Any]],
    stop_at: float,
    flag: base.StopFlag,
    interval: float,
    keep_tokens: bool,
) -> tuple[dict[str, dict[str, Any]], list[tuple[float, int, int]], Sampler, dict[str, Any]]:
    """Add every request under our own id, step until done, the stop time or a signal, then
    abort what is left. DELTA outputs: a request cut at the stop keeps what it sampled."""

    from vllm.sampling_params import RequestOutputKind

    engine = llm.llm_engine
    sampler = Sampler(llm, interval)
    sampler.take(force=True)
    state: dict[str, dict[str, Any]] = {}
    for ours, prompt, params in items:
        params.output_kind = RequestOutputKind.DELTA
        engine.add_request(ours, prompt, params)
        state[ours] = {
            "token_ids": [],
            "logp": [],
            "count": 0,
            "finish_reason": None,
            "stop_reason": None,
            "finished": False,
            "missing_logprobs": 0,
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
                    st["count"] += len(ids)
                    if keep_tokens:
                        values, missing = base.delta_logprobs(ids, completion.logprobs)
                        st["token_ids"].extend(ids)
                        st["logp"].extend(values)
                        st["missing_logprobs"] += missing
                if output.finished:
                    st["finish_reason"] = completion.finish_reason
                    st["stop_reason"] = completion.stop_reason
            if output.finished:
                st["finished"] = True
        steps.append((round(time.time() - started, 4), n_out, n_tok))
        sampler.take()
    sampler.take(force=True)
    info["wall_s"] = round(time.time() - started, 3)
    info["finished"] = sum(1 for st in state.values() if st["finished"])
    info["metric_errors"] = sampler.errors
    return state, steps, sampler, info


def drain(llm: Any, seconds: float = 20.0) -> int:
    """Step until the engine reports no unfinished request (after an abort), bounded."""

    engine = llm.llm_engine
    stop = time.time() + seconds
    steps = 0
    while engine.has_unfinished_requests() and time.time() < stop:
        engine.step()
        steps += 1
    return steps


def save_stats(path: Path, steps: list[tuple[float, int, int]], sampler: Sampler) -> None:
    import numpy as np

    path.parent.mkdir(parents=True, exist_ok=True)
    arr = np.asarray(steps, dtype=np.float64).reshape(-1, 3)
    np.savez_compressed(
        path, t=arr[:, 0], outputs=arr[:, 1].astype(np.int32), tokens=arr[:, 2].astype(np.int32)
    )
    with (path.with_suffix(".metrics.jsonl")).open("w", encoding="utf-8") as handle:
        for sample in sampler.samples:
            handle.write(json.dumps(sample, sort_keys=True) + "\n")


# --------------------------------------------------------------------------- rollout worker


def worker_main(args: argparse.Namespace) -> int:
    import numpy as np
    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams
    from vllm.inputs import TokensPrompt

    config = gb.load_config()
    if args.smoke:
        config = smoke_config(config)
    prompts = g2.load_prompts(config)
    model_id = args.model
    arm = gb.arm_for_state_dtype(config, args.state_dtype)
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
    kwargs = engine_kwargs(config, model_id, model_dir, args.state_dtype)
    log("engine-start", engine_kwargs=kwargs, end_of_turn_id=end_of_turn, smoke=args.smoke)
    t0 = time.time()
    llm = LLM(**kwargs)
    info = engine_info(llm)
    info["init_s"] = round(time.time() - t0, 1)
    g2.write_json(out / "engine.json", info)
    log("engine-ready", **info)
    summary: dict[str, Any] = {
        "model": model_id,
        "arm": arm,
        "state_dtype": args.state_dtype,
        "smoke": args.smoke,
        "engine": info,
        "phases": {},
    }
    interval = float(config["rollouts"]["stats_interval_s"])
    sampling = config["rollouts"]["sampling"]

    # Phase R: long reasoning rollouts.
    requests = gb.rollout_requests(config, prompts, model_id, arm)
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
    state, steps, sampler, rinfo = run_phase(llm, items, r_stop, flag, interval, keep_tokens=True)
    rinfo["drain_steps"] = drain(llm)
    save_stats(out / "phase-R-stats.npz", steps, sampler)
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
    g2.write_json(
        out / "sequences.json",
        {
            "model_id": model_id,
            "arm": arm,
            "state_dtype": args.state_dtype,
            "engine_kwargs": kwargs,
            "sampling": sampling,
            "end_of_turn_id": end_of_turn,
            "sequence_order": [s["sequence_id"] for s in sequences],
            "sequences": [
                {
                    k: s[k]
                    for k in (
                        "sequence_id",
                        "prompt_index",
                        "seed",
                        "max_tokens",
                        "finish_reason",
                        "stop_reason",
                        "missing_logprobs",
                    )
                }
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
    log("phase-R-saved", sequences=len(sequences), tokens=offsets[-1])
    del state, items, sequences

    # Phase S: one fixed-length saturation wave per seed.
    sat = config["saturation"]
    previous = 0.0
    for seed in config["seeds"]:
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
        wstate, wsteps, wsampler, winfo = run_phase(
            llm, witems, s_stop, flag, interval, keep_tokens=False
        )
        winfo["drain_steps"] = drain(llm)
        save_stats(out / f"phase-{name}-stats.npz", wsteps, wsampler)
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

    config = gb.load_config()
    model_id = args.model
    arm = gb.arm_for_state_dtype(config, args.state_dtype)
    out = Path(args.output_dir)
    flag = base.StopFlag()
    signal.signal(signal.SIGTERM, flag.handler)
    signal.signal(signal.SIGUSR1, flag.handler)
    tf_input = json.loads(Path(args.evidence).read_text(encoding="utf-8"))
    seqs = [s for s in tf_input["sequences"] if s["model_id"] == model_id]
    kwargs = engine_kwargs(
        config, model_id, g2.MODEL_ROOT / model_id, args.state_dtype, prefill=True
    )
    progress = out / f"prefill-{arm}-progress.jsonl"

    def log(event: str, **fields: Any) -> None:
        record = {"utc": g2.utc_now(), "event": event, "model": model_id, "arm": arm, **fields}
        with progress.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        print(json.dumps(record, sort_keys=True), flush=True)

    log("engine-start", engine_kwargs=kwargs, sequences=len(seqs))
    t0 = time.time()
    llm = LLM(**kwargs)
    info = engine_info(llm)
    info["init_s"] = round(time.time() - t0, 1)
    log("engine-ready", **info)
    items = []
    for s in seqs:
        params = SamplingParams(
            max_tokens=1,
            temperature=1.0,
            seed=config["seeds"][0],
            prompt_logprobs=config["prefill"]["prompt_logprobs"],
            detokenize=False,
        )
        items.append(
            (
                "P/" + s["sequence_id"],
                TokensPrompt(prompt_token_ids=s["prompt_ids"] + s["completion_ids"]),
                params,
            )
        )
    from vllm.sampling_params import RequestOutputKind

    engine = llm.llm_engine
    for ours, prompt, params in items:
        params.output_kind = RequestOutputKind.FINAL_ONLY
        engine.add_request(ours, prompt, params)
    index = {"P/" + s["sequence_id"]: i for i, s in enumerate(seqs)}
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
        "state_dtype": args.state_dtype,
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


# --------------------------------------------------------------------------- drivers


def child_env(out: Path) -> dict[str, str]:
    env = dict(os.environ)
    for key, sub in base.CACHE_DIRS.items():
        path = out / "cache" / sub
        path.mkdir(parents=True, exist_ok=True)
        env[key] = str(path)
    env.update(base.FIXED_ENV)
    return env


def supervise(
    argv: list[str],
    env: dict[str, str],
    log_path: Path,
    done_marker: Path,
    stop_at: float,
    state: dict[str, Any],
) -> dict[str, Any]:
    """Run one worker in its own session; kill it if it hangs after its done marker, runs
    90 s past the stop time, or outlives a signal by 40 s. Then wait for the GPU to be free."""

    record: dict[str, Any] = {"argv": argv, "started_at": g2.utc_now()}
    started = time.time()
    with log_path.open("w", encoding="utf-8") as logfile:
        child = subprocess.Popen(
            argv, env=env, stdout=logfile, stderr=subprocess.STDOUT, start_new_session=True
        )
        state["child"] = child
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
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.killpg(child.pid, signal.SIGKILL)
    record["exit"] = child.returncode
    record["wall_s"] = round(time.time() - started, 1)
    record["worker_done"] = json.loads(done_marker.read_text()) if done_marker.is_file() else None
    release_until = time.time() + 120
    while time.time() < release_until:
        used = base.gpu_memory_used_mib()
        if not used or max(used) < 1024:
            break
        time.sleep(2.0)
    record["gpu_memory_after_mib"] = base.gpu_memory_used_mib()
    return record


def install_signals(state: dict[str, Any]) -> None:
    def on_signal(signum: int, _frame: Any) -> None:
        state["signal"] = signal.Signals(signum).name
        state["signal_at"] = time.time()
        child = state["child"]
        if child is not None and child.poll() is None:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(child.pid, signal.SIGTERM)

    signal.signal(signal.SIGUSR1, on_signal)
    signal.signal(signal.SIGTERM, on_signal)


def run_main(args: argparse.Namespace) -> int:
    config = gb.load_config()
    if list(args.seeds) != config["seeds"]:
        raise gb.G2bConfigError("--seeds must equal the config's declared seeds")
    if args.model not in config["models"]:
        raise gb.G2bConfigError(f"unknown model {args.model}")
    arm = gb.arm_for_state_dtype(config, args.state_dtype)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    stop_at, source = g2.deadline(args.allocation_minutes)
    summary: dict[str, Any] = {
        "experiment_id": config["experiment_id"],
        "claim_level": "exploratory",
        "job": "rollouts",
        "model": args.model,
        "arm": arm,
        "state_dtype": args.state_dtype,
        "smoke": args.smoke,
        "started_at": g2.utc_now(),
        "allocation_minutes": args.allocation_minutes,
        "deadline_source": source,
        "deadline_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(stop_at)),
        "plan": build_plan(smoke_config(config) if args.smoke else config)["models"][args.model][
            "arms"
        ][arm],
    }
    g2.write_json(out / "summary.json", summary)
    base.record_environment(out)
    state: dict[str, Any] = {"child": None, "signal": None, "signal_at": None}
    install_signals(state)
    summary["verification"] = g2.verify_model(
        args.model, config["models"][args.model]["receipt_root"]
    )
    argv = [
        sys.executable,
        str(Path(__file__).resolve()),
        "worker",
        "--model",
        args.model,
        "--state-dtype",
        args.state_dtype,
        "--output-dir",
        str(out),
        "--deadline",
        f"{stop_at:.3f}",
    ] + (["--smoke"] if args.smoke else [])
    worker_dir = out / f"{args.model}-{arm}"
    worker_dir.mkdir(parents=True, exist_ok=True)
    summary["worker"] = supervise(
        argv,
        child_env(out),
        out / f"worker-{args.model}-{arm}.log",
        worker_dir / "done.json",
        stop_at,
        state,
    )
    tf_path = worker_dir / "tf-sequences.json"
    sequences = json.loads(tf_path.read_text(encoding="utf-8")) if tf_path.is_file() else []
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
            "g2b rollouts: finished phases saved; no resume (a rerun is a new job)",
        )
    done = summary["worker"].get("worker_done") or {}
    return 0 if done.get("exit") == 0 else 3


def merge_inputs(parts: list[dict[str, Any]], experiment_id: str) -> dict[str, Any]:
    sequences: list[dict[str, Any]] = []
    seen: set[str] = set()
    sources = []
    for part in parts:
        if part.get("experiment_id") != experiment_id:
            raise gb.G2bConfigError("a tf-input belongs to another experiment")
        for seq in part["sequences"]:
            if seq["sequence_id"] in seen:
                raise gb.G2bConfigError(f"duplicate sequence {seq['sequence_id']}")
            seen.add(seq["sequence_id"])
            sequences.append(seq)
        sources.append(
            {
                "git_sha": part.get("git_sha"),
                "sequences": len(part["sequences"]),
                "sha256": part.get("_sha256"),
            }
        )
    models = {s["model_id"] for s in sequences}
    if len(models) > 1:
        raise gb.G2bConfigError(f"a merged input holds one model, got {sorted(models)}")
    return {"experiment_id": experiment_id, "sources": sources, "sequences": sequences}


def merge_main(args: argparse.Namespace) -> int:
    config = gb.load_config()
    parts = []
    for path in args.inputs:
        raw = Path(path).read_bytes()
        part = json.loads(raw)
        part["_sha256"] = g2.sha256_bytes(raw)
        parts.append(part)
    merged = merge_inputs(parts, config["experiment_id"])
    out = Path(args.output)
    if out.exists():
        raise gb.G2bConfigError("refusing to overwrite the merged tf-input")
    g2.write_json(out, merged)
    print(
        json.dumps(
            {
                "sequences": len(merged["sequences"]),
                "sha256": g2.sha256_file(out),
                "sources": merged["sources"],
            },
            sort_keys=True,
        )
    )
    return 0


def prefill_main(args: argparse.Namespace) -> int:
    config = gb.load_config()
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    stop_at, source = g2.deadline(args.allocation_minutes)
    evidence = Path(args.evidence)
    if g2.sha256_file(evidence) != args.expected_evidence_sha256:
        raise gb.G2bConfigError("study artifact digest differs from --expected-evidence-sha256")
    tf_input = json.loads(evidence.read_text(encoding="utf-8"))
    if tf_input.get("experiment_id") != config["experiment_id"]:
        raise gb.G2bConfigError("study artifact is not this experiment's tf-input")
    summary: dict[str, Any] = {
        "experiment_id": config["experiment_id"],
        "claim_level": "exploratory",
        "job": "prefill",
        "model": args.model,
        "evidence_sha256": args.expected_evidence_sha256,
        "sequences": sum(1 for s in tf_input["sequences"] if s["model_id"] == args.model),
        "started_at": g2.utc_now(),
        "deadline_source": source,
        "deadline_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(stop_at)),
        "arms": {},
    }
    g2.write_json(out / "summary.json", summary)
    base.record_environment(out)
    state: dict[str, Any] = {"child": None, "signal": None, "signal_at": None}
    install_signals(state)
    summary["verification"] = g2.verify_model(
        args.model, config["models"][args.model]["receipt_root"]
    )
    env = child_env(out)
    for index, arm in enumerate(gb.ARM_NAMES):
        dtype = gb.vllm_state_dtype(config, arm)
        remaining = stop_at - time.time()
        if state["signal"] or (index and remaining < args.min_arm_s):
            summary["arms"][arm] = {
                "status": "skipped",
                "remaining_s": round(remaining, 1),
                "signal": state["signal"],
            }
            continue
        argv = [
            sys.executable,
            str(Path(__file__).resolve()),
            "prefill-worker",
            "--model",
            args.model,
            "--state-dtype",
            dtype,
            "--evidence",
            str(evidence),
            "--output-dir",
            str(out),
            "--deadline",
            f"{stop_at:.3f}",
        ]
        record = supervise(
            argv,
            env,
            out / f"worker-prefill-{arm}.log",
            out / f"prefill-{arm}-done.json",
            stop_at,
            state,
        )
        done = record.get("worker_done") or {}
        record["status"] = "complete" if done.get("exit") == 0 else "partial" if done else "failed"
        summary["arms"][arm] = record
        g2.write_json(out / "summary.json", summary)
    summary["finished_at"] = g2.utc_now()
    summary["signal"] = state["signal"]
    g2.write_json(out / "summary.json", summary)
    if state["signal"]:
        g2.write_checkpoint_marker(
            "SIGUSR1" if state["signal"] == "SIGUSR1" else "SIGTERM",
            "g2b prefill: finished arms saved; no resume (a rerun is a new job)",
        )
    return 0 if all(a.get("status") == "complete" for a in summary["arms"].values()) else 3


# --------------------------------------------------------------------------- selftest


def selftest_main(args: argparse.Namespace) -> int:
    """CPU only: everything the jobs construct before the engine starts."""

    import typing

    from transformers import AutoTokenizer
    from vllm import SamplingParams
    from vllm.config.cache import MambaDType
    from vllm.engine.arg_utils import EngineArgs
    from vllm.v1.metrics import reader

    config = gb.load_config()
    prompts = g2.load_prompts(config)
    report: dict[str, Any] = {"plan": build_plan(config), "models": {}, "checks": {}}
    report["checks"]["mamba_dtype_literal"] = list(typing.get_args(MambaDType))
    ok = set(config["state_dtypes"].values()) <= set(typing.get_args(MambaDType))
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
        record: dict[str, Any] = {
            "prompt_len_max": max(lengths),
            "prompt_len_min": min(lengths),
            "end_of_turn_id": tokenizer.convert_tokens_to_ids(END_OF_TURN),
        }
        reqs = gb.rollout_requests(config, prompts, model_id, "fp32")
        record["fits"] = (
            max(lengths) + reqs[0]["max_tokens"] + 1 <= config["engine"]["max_model_len"]
        )
        for arm in gb.ARM_NAMES:
            dtype = gb.vllm_state_dtype(config, arm)
            for prefill in (False, True):
                kwargs = engine_kwargs(config, model_id, root / model_id, dtype, prefill)
                engine_args = EngineArgs(**kwargs)
                record[f"engine_args_{arm}{'_prefill' if prefill else ''}"] = {
                    "mamba_ssm_cache_dtype": engine_args.mamba_ssm_cache_dtype,
                    "disable_log_stats": engine_args.disable_log_stats,
                    "gpu_memory_utilization": engine_args.gpu_memory_utilization,
                }
        ok = ok and record["fits"]
        report["models"][model_id] = record
    params = [
        SamplingParams(
            n=1,
            temperature=1.0,
            top_p=1.0,
            top_k=0,
            max_tokens=32768,
            logprobs=0,
            seed=42,
            stop_token_ids=[1],
            detokenize=False,
        ),
        SamplingParams(
            n=1,
            temperature=1.0,
            top_p=1.0,
            top_k=0,
            max_tokens=2048,
            ignore_eos=True,
            logprobs=0,
            seed=gb.saturation_seed(44, 63, 7),
            detokenize=False,
        ),
        SamplingParams(max_tokens=1, temperature=1.0, seed=42, prompt_logprobs=0, detokenize=False),
    ]
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
    prompt = [
        None,
        {1: base._Lp(-3.0)},
        {5: base._Lp(-0.25)},
        {7: base._Lp(-0.75)},
        {9: base._Lp(-1.5)},
    ]
    ok = ok and values == [-0.5, -1.0, -2.0] and missing == 0
    ok = ok and base.prefill_logprobs(2, tokens, prompt) == [-0.25, -0.75, -1.5]
    report["ok"] = bool(ok)
    print(json.dumps(jsonable(report), indent=2, sort_keys=True))
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("plan")
    selftest = sub.add_parser("selftest", allow_abbrev=False)
    selftest.add_argument("--model-root", default=str(g2.MODEL_ROOT))
    run = sub.add_parser("run", allow_abbrev=False)
    run.add_argument("--model", required=True)
    run.add_argument("--state-dtype", required=True, choices=gb.VLLM_MAMBA_DTYPES)
    run.add_argument("--seeds", type=int, nargs="+", required=True)
    run.add_argument("--output-dir", required=True)
    run.add_argument("--allocation-minutes", type=float, required=True)
    run.add_argument("--smoke", action="store_true")
    worker = sub.add_parser("worker", allow_abbrev=False)
    worker.add_argument("--model", required=True)
    worker.add_argument("--state-dtype", required=True, choices=gb.VLLM_MAMBA_DTYPES)
    worker.add_argument("--output-dir", required=True)
    worker.add_argument("--deadline", type=float, required=True)
    worker.add_argument("--reserve-s", type=float, default=30.0)
    worker.add_argument("--smoke", action="store_true")
    merge = sub.add_parser("merge", allow_abbrev=False)
    merge.add_argument("--inputs", nargs="+", required=True)
    merge.add_argument("--output", required=True)
    prefill = sub.add_parser("prefill", allow_abbrev=False)
    prefill.add_argument("--evidence", required=True)
    prefill.add_argument("--expected-evidence-sha256", required=True)
    prefill.add_argument("--model", required=True)
    prefill.add_argument("--output-dir", required=True)
    prefill.add_argument("--allocation-minutes", type=float, required=True)
    prefill.add_argument("--min-arm-s", type=float, default=150.0)
    pworker = sub.add_parser("prefill-worker", allow_abbrev=False)
    pworker.add_argument("--model", required=True)
    pworker.add_argument("--state-dtype", required=True, choices=gb.VLLM_MAMBA_DTYPES)
    pworker.add_argument("--evidence", required=True)
    pworker.add_argument("--output-dir", required=True)
    pworker.add_argument("--deadline", type=float, required=True)
    args = parser.parse_args()
    if args.command == "plan":
        print(json.dumps(jsonable(build_plan(gb.load_config())), indent=2, sort_keys=True))
        return 0
    handlers = {
        "selftest": selftest_main,
        "run": run_main,
        "worker": worker_main,
        "merge": merge_main,
        "prefill": prefill_main,
        "prefill-worker": prefill_worker_main,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
