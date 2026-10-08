#!/usr/bin/env python3
"""D31 review fix pass: the Stage 0 projection recomputed under the corrected design.

CPU only; no GPU job ran for it. Recorded beside its output
(``projection-fixpass.json``) as the evidence for preregistration section 18.9.

Inputs (hashes recorded in the output):
- the committed D31 cost card (``../cost-card-d31.json``): the pilot's per-gate
  size model, the job-548 paired factors, the large-problem anchors, the compile
  survival and the fixed phases (1.229 GPU-h spent included);
- the host-only Stage 0 planning counts (``stage0-counts-v2.json``, written by
  ``scripts/q1_stage0_counts.py``; the same file every earlier card used);
- the re-pilot's run directory (Slurm 713, ``<run>/q1``): its store pairs and
  reference items, and its inline items for the transfer check.

What it computes, through bucket P3 (the D31 criterion), central and high:

1. The registered table of section 18.8, item 7, recomputed with this code
   (a reproduction check).
2. The store without gate (a) (finding 3): consumer gates c, A1, A2, A3 and A5,
   their reference items only.
3. The memory-aware execution policy ``q1-stage0-exec/2`` (``harness.q1.memory``):
   each in-scope item at ``floor(12 / units)`` per GPU, its GPU-seconds from
   ``cost_card.concurrency_multiplier`` (the job-548 factor at 12 per GPU, the
   size model at 4, an upper bound below 4). Model-based: no job has run under
   the policy.
4. The transfer check (finding 2): the size model with the job-548 factors
   against the re-pilot's own final inline items, overall and without the three
   problems that ran out of memory.
5. Scope reductions that act on P1-P3 (finding 7).

"High" follows the card's convention: fixed part plus the scoring through the
bucket times the scale (bootstrap 97.5% point over central) of the matching
registered scenario; scenarios with no registered match reuse the no-store scale
and are labelled so.

    python program/evidence/2026-10-07/q1-engineering-d31/fixpass/projection_fixpass.py \\
        --counts stage0-counts-v2.json --repilot-run RUN713/q1 --out projection-fixpass.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
sys.path.insert(0, str(ROOT))

from harness.q1 import cost_card as cc  # noqa: E402
from harness.q1 import memory, pilot, trim  # noqa: E402

CARD = HERE.parent / "cost-card-d31.json"
OOM_PROBLEMS = (
    "L2/59_Matmul_Swish_Scaling",
    "L2/87_Conv2d_Subtract_Subtract_Mish",
    "L2/100_ConvTranspose3d_Clamp_Min_Divide",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def through(projection: dict[str, Any], bucket: str = "P3") -> float:
    return sum(v for k, v in projection["gpu_hours_by_priority"].items() if k <= bucket)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--counts", type=Path, required=True)
    parser.add_argument("--repilot-run", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    card = json.loads(CARD.read_text())
    counts = json.loads(args.counts.read_text())
    fits, factors = card["size_model"], card["paired_concurrency"]["factors"]
    anchors, survival = card["large_problem_anchors"], card["compile_filter"]["survival"]
    exposed = trim.load_exposed(trim.PILOT_EXPOSED_PATH)
    scenarios = {t["name"]: t for t in card["trimmed"]}

    def registered(name: str) -> dict[str, float]:
        t = scenarios[name]
        p3 = next(x for x in t["priority_cumulative_with_reserve"] if x["through"] == "P3")
        return {
            "fixed": round(sum(t["fixed_gpu_hours"].values()), 3),
            "scale": t["scoring_gpu_hours_95"]["high"] / t["gpu_hours"],
            "P3_central": p3["total_central"],
            "P3_high": p3["total_high"],
        }

    job = cc.load_job(args.repilot_run)
    items = job["items"]
    pairs = cc.repilot_pairs(items)
    refs = cc.reference_items(items)

    def project(rule: dict[str, Any] = cc.TRIM_RULE, **kw: Any) -> dict[str, Any]:
        return cc.project_trimmed(
            counts,
            fits,
            survival=survival,
            rule=rule,
            factors=factors,
            anchors=anchors,
            exposed=exposed,
            **kw,
        )

    def units_of(problem: str, gate: str) -> int:
        return trim.item_units(problem, gate)[0]

    def row(label: str, projection: dict, match: str, *, note: str = "") -> dict[str, Any]:
        reg = registered(match)
        scoring = through(projection)
        return {
            "scenario": label,
            "P3_scoring_central": round(scoring, 3),
            "P3_central": round(reg["fixed"] + scoring, 2),
            "P3_high": round(reg["fixed"] + reg["scale"] * scoring, 2),
            "high_scale_from": match,
            "note": note,
        }

    def store(mode: str, *, consumers: tuple[str, ...], free: bool = False) -> cc.StoreModel:
        return cc.fit_store_model(
            pairs, refs, ratio_mode=mode, free_references=free, consumers=consumers
        )

    old = cc.STORE_CONSUMER_GATES_REPILOT
    new = cc.STORE_CONSUMER_GATES
    out: dict[str, Any] = {
        "inputs": {
            "cost_card_sha256": sha256(CARD),
            "counts_sha256": sha256(args.counts),
            "repilot_journal_sha256": sha256(args.repilot_run / "repilot" / "journal.jsonl"),
            "memory_table_sha256": sha256(memory.TABLE_PATH),
            "execution_policy": memory.POLICY_VERSION,
        }
    }

    # 1. Registered table (18.8, item 7), recomputed.
    reproduction = []
    for label, match, kw in (
        ("no store", "trim2-paired-concurrency", {}),
        (
            "store, linear (pre-specified), per bucket",
            "trim2-store-per-bucket-paired-concurrency",
            {"store": store("linear", consumers=old), "store_mode": "per-bucket"},
        ),
        (
            "store, linear (pre-specified), per job",
            "trim2-store-per-job-paired-concurrency",
            {"store": store("linear", consumers=old), "store_mode": "per-job"},
        ),
        (
            "store, constant (post hoc), per bucket",
            "trim2-store-constant-per-bucket-paired-concurrency",
            {"store": store("constant", consumers=old), "store_mode": "per-bucket"},
        ),
        (
            "store, constant (post hoc), per job",
            "trim2-store-constant-per-job-paired-concurrency",
            {"store": store("constant", consumers=old), "store_mode": "per-job"},
        ),
        (
            "references-free bound (post hoc ratio), per job",
            "trim2-store-free-references-per-job-paired-concurrency",
            {"store": store("constant", consumers=old, free=True), "store_mode": "per-job"},
        ),
    ):
        r = row(label, project(**kw), match)
        reg = registered(match)
        r["registered_P3_central"], r["registered_P3_high"] = reg["P3_central"], reg["P3_high"]
        reproduction.append(r)
    out["1_registered_reproduced"] = reproduction

    # The pre-specified ratio with free references (the review's 9.08).
    out["1b_references_free_with_prespecified_ratio"] = row(
        "references-free, linear (pre-specified) ratio, per job",
        project(store=store("linear", consumers=old, free=True), store_mode="per-job"),
        "trim2-store-free-references-per-job-paired-concurrency",
    )

    # 2. The store without gate (a).
    without_a = []
    for label, match, model in (
        (
            "store without gate (a), linear (pre-specified), per job",
            "trim2-store-per-job-paired-concurrency",
            store("linear", consumers=new),
        ),
        (
            "store without gate (a), constant (post hoc), per job",
            "trim2-store-constant-per-job-paired-concurrency",
            store("constant", consumers=new),
        ),
        (
            "references-free bound without gate (a) (post hoc ratio), per job",
            "trim2-store-free-references-per-job-paired-concurrency",
            store("constant", consumers=new, free=True),
        ),
    ):
        without_a.append(row(label, project(store=model, store_mode="per-job"), match))
    out["2_store_without_gate_a"] = without_a

    # 3. The memory-aware execution policy.
    in_scope = [
        r
        for r in counts["evaluation_substrates"]
        if int(r.get("native_input_bytes") or 0) < int(cc.TRIM_RULE["scope_bytes"])
    ]
    unit_rows = {
        r["substrate_id"]: {g: units_of(r["problem_id"], g) for g in trim.SCORING_GATES}
        for r in in_scope
    }
    out["3_policy_units"] = {
        "in_scope_substrates": len(in_scope),
        "substrates_with_more_than_one_unit_somewhere": sum(
            1 for v in unit_rows.values() if max(v.values()) > 1
        ),
        "items_per_gpu_histogram_over_gate_items": {
            str(k): sum(1 for v in unit_rows.values() for u in v.values() if 12 // u == k)
            for k in sorted({12 // u for v in unit_rows.values() for u in v.values()})
        },
        "per_substrate_units": unit_rows,
    }
    policy = []
    for label, match, kw in (
        ("exec/2, no store", "trim2-paired-concurrency", {}),
        (
            "exec/2, store without gate (a), linear (pre-specified), per job",
            "trim2-store-per-job-paired-concurrency",
            {"store": store("linear", consumers=new), "store_mode": "per-job"},
        ),
        (
            "exec/2, store without gate (a), constant (post hoc), per job",
            "trim2-store-constant-per-job-paired-concurrency",
            {"store": store("constant", consumers=new), "store_mode": "per-job"},
        ),
        (
            "exec/2, references-free bound without gate (a) (post hoc ratio)",
            "trim2-store-free-references-per-job-paired-concurrency",
            {"store": store("constant", consumers=new, free=True), "store_mode": "per-job"},
        ),
    ):
        policy.append(
            row(
                label,
                project(units_of=units_of, **kw),
                match,
                note="model-based: no job has run under q1-stage0-exec/2; below 4 per GPU "
                "the multiplier is an upper bound",
            )
        )
    out["3_memory_aware_policy"] = policy

    # 4. Transfer check of the size model (job-548 factors) on the re-pilot.
    def transfer(
        select: Callable[[dict], bool],
        size: Callable[[str], float] | None = None,
        policy_units: bool = False,
    ) -> dict[str, Any]:
        predicted = measured = 0.0
        n = 0
        for i in items:
            if i["kernel_id"].endswith(".store") or i["gate"].startswith("ref_"):
                continue
            if not i["final"] or i["gpu_seconds"] is None or i["gate"] not in fits:
                continue
            if not select(i):
                continue
            gb = (
                size(i["problem_id"])
                if size
                else (pilot.native_input_bytes(i["problem_id"]) or 0) / 1e9
            )
            fit = fits[i["gate"]]
            x = fit["alpha"] + fit["beta"] * gb
            if (pilot.native_input_bytes(i["problem_id"]) or 0) < 600_000_000 and i[
                "gate"
            ] in factors:
                if policy_units:
                    x *= cc.concurrency_multiplier(
                        units_of(i["problem_id"], i["gate"]), factors[i["gate"]]
                    )
                else:
                    x *= factors[i["gate"]]
            predicted += x
            measured += i["gpu_seconds"]
            n += 1
        return {
            "items": n,
            "predicted_gpu_seconds": round(predicted, 1),
            "measured_gpu_seconds": round(measured, 1),
            "measured_over_predicted": round(measured / predicted, 3) if predicted else None,
        }

    table = memory.table()["problems"]

    def memory_gb(problem: str) -> float:
        e = table[problem]
        return (
            e["params_bytes"] + e["native"]["input_bytes"] + (e["native"]["output_bytes"] or 0)
        ) / 1e9

    checks = {
        "input_sized_all": transfer(lambda i: True),
        "input_sized_without_oom_problems": transfer(lambda i: i["problem_id"] not in OOM_PROBLEMS),
        "input_sized_oom_problems_only": transfer(lambda i: i["problem_id"] in OOM_PROBLEMS),
        "exec2_units_oom_problems_only": transfer(
            lambda i: i["problem_id"] in OOM_PROBLEMS, policy_units=True
        ),
        "exec2_units_all": transfer(lambda i: True, policy_units=True),
        "memory_sized_all": transfer(lambda i: True, memory_gb),
        "memory_sized_without_oom_problems": transfer(
            lambda i: i["problem_id"] not in OOM_PROBLEMS, memory_gb
        ),
    }
    size_of = {
        r["substrate_id"]: (pilot.native_input_bytes(r["problem_id"]) or 0) / 1e9 for r in in_scope
    }
    per_substrate = {
        r["substrate_id"]: cc.kernel_replicate_seconds(fits, r["problem_id"], factors=factors)
        for r in in_scope
    }
    support = {}
    for gate in trim.SCORING_GATES:
        sizes = [
            (pilot.native_input_bytes(p["problem_id"]) or 0) / 1e9
            for p in pairs
            if p["problem_id"] and p["gate"] == gate
        ]
        largest = max(sizes, default=0.0)
        above = [s for s, g in size_of.items() if g > largest + 1e-9]
        support[gate] = {
            "largest_paired_gb": round(largest, 4),
            "in_scope_substrates_above": len(above),
            "their_share_of_per_substrate_model_cost": round(
                sum(per_substrate[s] for s in above) / sum(per_substrate.values()), 3
            ),
        }
    checks["paired_support_per_gate"] = support
    out["4_transfer_check"] = checks
    # exec/1 (the registered card): the size model under-predicts the re-pilot's own
    # items, so its scoring part is scaled by the transfer ratio as a sensitivity. The
    # exec/2 model over-predicts them (exec2_units_all), so it is not scaled.
    ratio = checks["input_sized_all"]["measured_over_predicted"]
    base = reproduction[0]
    sensitivity = [
        {
            "scenario": base["scenario"] + f", exec/1, scoring x{ratio} (transfer ratio)",
            "P3_central": round(base["P3_central"] + (ratio - 1) * base["P3_scoring_central"], 2),
            "P3_high": round(
                base["P3_high"]
                + (ratio - 1) * (base["P3_high"] - registered("trim2-paired-concurrency")["fixed"]),
                2,
            ),
        }
    ]
    out["4b_transfer_sensitivity"] = sensitivity

    # 5. Scope reductions that act on P1-P3 (finding 7), no store, exec/1 and exec/2.
    reductions = []
    for label, rule, match in (
        (
            "q30 test quota (30 per family)",
            {**cc.TRIM_RULE, "family_quota_test": 30, "family_quota_dev": 8},
            "trim2-q30-paired-concurrency",
        ),
        (
            "no FRR margin (acts on P4 only)",
            {**cc.TRIM_RULE, "frr_margin_units": 0},
            "trim2-no-margin-paired-concurrency",
        ),
    ):
        reductions.append(row(label + ", exec/1", project(rule=rule), match))
        reductions.append(
            row(
                label + ", exec/2", project(rule=rule, units_of=units_of), match, note="model-based"
            )
        )
    out["5_scope_reductions"] = reductions

    args.out.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    for key in (
        "1_registered_reproduced",
        "2_store_without_gate_a",
        "3_memory_aware_policy",
        "5_scope_reductions",
    ):
        for r in out[key]:
            print(f"{r['scenario']:78s} P3 {r['P3_central']:6.2f} / {r['P3_high']:6.2f}")
    print(json.dumps({k: v for k, v in checks.items()}, indent=1))
    print(json.dumps(out["1b_references_free_with_prespecified_ratio"]))
    print(json.dumps(sensitivity))
    print(
        json.dumps({k: v for k, v in out["3_policy_units"].items() if k != "per_substrate_units"})
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
