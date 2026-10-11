"""P0: the bitwise self-test and the timing gate (draft registration v2, section 10.1).

P0 runs before any J job, on one H100, in two engine sessions:

1. **E-det** (``--max-num-seqs 1 --no-enable-prefix-caching``): the probe items (40 step-1 and
   20 step-2 requests built from frames that are not in the corpus) three times with
   log-probabilities and once without, at batch 1 with the encoder cache reset before every
   request (``replay.run_batch1``). The self-test compares, per item, the reply text and the
   completion token ids of passes 2 and 3 with pass 1 (bitwise), and pass 4's text with pass 1's.
2. **E-s1a** (S1a's argv): one loaded pass of the same items (``replay.run_loaded_pass``), which
   gives the loaded latency the J3 and J4 caps rest on.

``decide`` reads the self-test:

* any text or token-id difference among the 2 x n replica comparisons: P0' is run (E-det with
  ``VLLM_BATCH_INVARIANT=1``); J1 uses whichever reference shows none, else E-det, and the J1
  DET reading labels every det cell;
* a difference between the log-probability passes and pass 4: Stage B drops log-probabilities
  in every arm (margins are then not reported);
* the engine logs' Mamba cache mode for each configuration is recorded (prefix caching switches
  Qwen3.5's hybrid layers to ``align``; E-det runs with it off), as is the encoder-cache route's
  answer.

``timing_gate`` projects each J job's work at P0's measured prices: batch-1 work as the
measured 95th-percentile per-request time by step times the job's request count; loaded work
as the 95th percentile of ``caps.simulate_loaded`` with latencies resampled from P0's loaded
pass. A job whose projection (with lead, engine starts and the 1.2 x 1.05 factors) exceeds its
registered cap is not submitted; the registration is amended first. Caps are never exceeded.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np

from harness.r01 import caps as capsmod
from harness.r01 import replay
from harness.r01.requests import without_logprobs

MAMBA_RE = re.compile(r"Mamba cache mode is set to '([A-Za-z_]+)'")


def run_det(
    transport: str, items: Sequence[Mapping[str, Any]], out: Path, seed: int = 43, passes: int = 3
) -> dict[str, Any]:
    """Section 10.1 step 1 on an engine already started as E-det (or E-det-BI for P0')."""
    for p in range(1, passes + 1):
        replay.run_batch1(transport, items, label=f"det-p{p}", seed=seed + p - 1, out=out)
    replay.run_batch1(
        transport, items, label="det-nolp", seed=seed + passes, out=out, body_fn=without_logprobs
    )
    return self_test(replay.read_jsonl(out), [it["id"] for it in items], passes)


def self_test(
    rows: Sequence[Mapping[str, Any]], item_ids: Sequence[str], passes: int = 3
) -> dict[str, Any]:
    by: dict[tuple[str, str], Mapping[str, Any]] = {}
    for r in rows:
        if "error" not in r:
            by[(r["label"], r["item"])] = r
    text_diff, ids_diff, missing, nolp_diff = [], [], [], []
    for item in item_ids:
        ref = by.get(("det-p1", item))
        if ref is None:
            missing.append(item)
            continue
        for p in range(2, passes + 1):
            other = by.get((f"det-p{p}", item))
            if other is None:
                missing.append(item)
                continue
            if other["content_sha256"] != ref["content_sha256"]:
                text_diff.append((item, p))
            if other.get("completion_ids_sha256") != ref.get("completion_ids_sha256"):
                ids_diff.append((item, p))
        nolp = by.get(("det-nolp", item))
        if nolp is None:
            missing.append(item)
        elif nolp["content_sha256"] != ref["content_sha256"]:
            nolp_diff.append(item)
    comparisons = len(item_ids) * (passes - 1)
    return {
        "items": len(item_ids),
        "replica_comparisons": comparisons,
        "text_differences": len(text_diff),
        "token_id_differences": len(ids_diff),
        "logprob_pass_differences": len(nolp_diff),
        "missing": sorted(set(missing)),
        "examples": {"text": text_diff[:5], "token_ids": ids_diff[:5], "nolp": nolp_diff[:5]},
    }


def mamba_mode(engine_log: str) -> str:
    match = MAMBA_RE.search(engine_log)
    return match.group(1) if match else "not logged (prefix caching off: no align)"


def decide(test: Mapping[str, Any], engine_logs: Mapping[str, str] | None = None) -> dict[str, Any]:
    bitwise = (
        test["text_differences"] == 0 and test["token_id_differences"] == 0 and not test["missing"]
    )
    return {
        "det_bitwise": bitwise,
        "run_p0_prime": not bitwise,
        "drop_logprobs": test["logprob_pass_differences"] > 0,
        "incomplete": bool(test["missing"]),
        "mamba_cache_mode": {k: mamba_mode(v) for k, v in (engine_logs or {}).items()},
    }


def measured_prices(
    rows: Sequence[Mapping[str, Any]],
    steps_of: Mapping[str, int],
    labels: Sequence[str] = ("det-p1", "det-p2", "det-p3", "det-nolp"),
) -> dict[int, dict[str, float]]:
    """Per-step batch-1 time per request (mean and 95th percentile) from the E-det passes."""
    out: dict[int, dict[str, float]] = {}
    for step in sorted(set(steps_of.values())):
        lat = [
            r["latency_s"]
            for r in rows
            if r.get("label") in labels
            and "error" not in r
            and steps_of.get(r["item"]) == step
            and r.get("latency_s") is not None
        ]
        if lat:
            out[step] = {
                "mean_s": float(np.mean(lat)),
                "p95_s": float(np.quantile(lat, 0.95)),
                "n": len(lat),
            }
    return out


def timing_gate(
    jobs: Sequence[capsmod.Job],
    registered_caps: Mapping[str, int],
    batch1_price: Mapping[int, Mapping[str, float]],
    loaded_latencies: Mapping[int, Sequence[float]],
) -> dict[str, Any]:
    """Section 10.1's rule, per job: submit only if the projection fits the registered cap."""
    out = {}
    for job in jobs:
        b1 = sum((batch1_price[k]["p95_s"] + capsmod.RESET_S) * n for k, n in job.batch1.items())
        wm = sum(batch1_price[k]["p95_s"] * n for k, n in job.warm.items())
        loaded = 0.0
        if job.loaded_passes:
            fake_costs = {
                k: capsmod.StepCost(
                    k, 0.0, float(np.mean(v)), float(np.quantile(v, 0.95)), tuple(v)
                )
                for k, v in loaded_latencies.items()
            }
            sim = capsmod.simulate_loaded(
                fake_costs, job.loaded_counts, job.loaded_passes, draws=4000
            )
            loaded = float(np.quantile(sim, 0.95))
        work = b1 + wm + loaded
        projected = math.ceil(
            capsmod.LEAD_MIN
            + capsmod.ENGINE_START_MIN * job.engine_starts
            + work / 60.0 * capsmod.F_DR4 * capsmod.F_REQ
        )
        cap = registered_caps[job.name]
        out[job.name] = {
            "projected_min": projected,
            "cap_min": cap,
            "submit": projected <= cap,
            "work_min": round(work / 60, 2),
        }
    return out


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="P0 E-det session: bitwise self-test")
    ap.add_argument("--transport", required=True)
    ap.add_argument(
        "--corpus", type=Path, required=True, help="the probe corpus (not the main corpus)"
    )
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--engine-log", type=Path, default=None)
    ap.add_argument("--label", default="E-det")
    args = ap.parse_args(list(argv) if argv is not None else None)
    items = replay.load_items(args.corpus)
    test = run_det(args.transport, items, args.out)
    logs = {args.label: args.engine_log.read_text()} if args.engine_log else {}
    print(json.dumps({"self_test": test, "decision": decide(test, logs)}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
