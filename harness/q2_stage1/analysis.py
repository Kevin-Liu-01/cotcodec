"""The registered S1a report: from episode records to every estimand, test and rule.

Usage (CPU, after the last A1 job)::

    python -m harness.q2_stage1.analysis --records a1.jsonl --plan plan.json \
        [--costs costs.json] [--anchor anc.jsonl --public public.json] --out report.json

``plan.json`` is the frozen plan (``scripts/render_q2_stage1_plan.py``): base tasks,
extension blocks, flagged tasks, task domains and the anchor tasks; ``costs.json`` holds
each A1 job's realized GPU-h per episode and V from its receipt (DR4). The primary analysis
set is the base, fixed at the freeze; base plus the extension blocks completed in all four
A1 jobs is the registered secondary (the fill rule's block count depends on episode
lengths, so on outcomes).
"""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np

from harness.q2_stage1 import estimators as E
from harness.q2_stage1 import records as R
from harness.q2_stage1 import rules

N_BOOT = 10_000
N_RANDOMIZATION = 10_000
SEED = 42


def _f(x: Any) -> Any:
    if isinstance(x, np.ndarray):
        return _f(x.item()) if x.ndim == 0 else [_f(v) for v in x.tolist()]
    if isinstance(x, (list, tuple)):
        return [_f(v) for v in x]
    if isinstance(x, (float, np.floating)):
        return None if not math.isfinite(float(x)) else round(float(x), 6)
    if isinstance(x, np.integer):
        return int(x)
    return x


def statistics(y: np.ndarray) -> dict[str, np.ndarray]:
    """Every bootstrapped estimand of section 9 for one or many data sets."""
    db, dw = E.d_between(y), E.d_within(y)
    x = E.x_by_size(y)
    pis = E.pi_share(x, db)
    return {
        "delta": E.delta(y),
        "delta_4B": E.delta_by_size(y)[..., 0],
        "delta_9B": E.delta_by_size(y)[..., 1],
        "scale_screen_delta": E.delta_by_size(y)[..., 0] - E.delta_by_size(y)[..., 1],
        "D_b_4B": db[..., 0],
        "D_b_9B": db[..., 1],
        "D_b": np.nanmean(db, axis=-1),
        "D_w_4B": dw[..., 0],
        "D_w_9B": dw[..., 1],
        "D_w": np.nanmean(dw, axis=-1),
        "excess_4B": (db - dw)[..., 0],
        "excess_9B": (db - dw)[..., 1],
        "excess": np.nanmean(db - dw, axis=-1),
        "D_b_same_block": np.nanmean(E.d_between_same_block(y), axis=-1),
        "D_b_cross_block": np.nanmean(E.d_between_cross_block(y), axis=-1),
        "X_4B": x[..., 0],
        "X_9B": x[..., 1],
        "X": np.nanmean(x, axis=-1),
        "X_centred_4B": E.x_centred_by_size(y)[..., 0],
        "X_centred_9B": E.x_centred_by_size(y)[..., 1],
        "X_bernoulli": np.nanmean(E.x_bernoulli_by_size(y), axis=-1),
        "pi_4B": pis[..., 0],
        "pi_9B": pis[..., 1],
        "pi_small": np.nanmean(pis, axis=-1),
        "scale_screen_pi": pis[..., 0] - pis[..., 1],
        "session_shift_4B": E.session_shift(y)[..., 0],
        "session_shift_9B": E.session_shift(y)[..., 1],
    }


def analyse_array(
    y: np.ndarray,
    *,
    n_boot: int = N_BOOT,
    n_rand: int = N_RANDOMIZATION,
    seed: int = SEED,
    label_permutation: bool = True,
) -> dict[str, Any]:
    """Estimates, 95% bootstrap intervals, one-sided bounds, tests and DR1/DR2/DR5."""
    point = statistics(y)
    names = list(point)

    def stacked(yy: np.ndarray) -> np.ndarray:
        values = statistics(yy)
        return np.stack([values[name] for name in names], axis=-1)

    draws = E.bootstrap(y, stacked, n_boot, seed)
    boot = {name: draws[:, i] for i, name in enumerate(names)}
    est: dict[str, Any] = {}
    for name in names:
        lo95, hi95 = E.percentile_interval(boot[name], 0.95)
        lb, ub = E.one_sided_bounds(boot[name], 0.95)
        est[name] = {
            "estimate": _f(point[name]),
            "ci95": [_f(lo95), _f(hi95)],
            "one_sided_95": [_f(lb), _f(ub)],
        }
    rng = np.random.default_rng(seed)
    dbar = E.task_delta(y)
    t = E.paired_t(dbar, level=0.90)
    t_by_size = [E.paired_t(np.nanmean(E.harness_diff(y)[z], axis=-1)) for z in range(2)]
    p_x = float(E.x_signflip_p(y, n_rand, rng))
    p_x_label = float(E.x_label_permutation_p(y, n_rand, rng)) if label_permutation else None
    p_session = E.session_signflip_p(y, n_rand, rng)
    het = E.delta_session_heterogeneity(y)
    common = E.session_common_share(y)
    succ = E.success(y)
    drop_4b = rules.dr1(list(succ[0]))
    dr2 = rules.dr2(
        float(t["p"]),
        p_x,
        (float(t["ci_low"]), float(t["ci_high"])),
        est["pi_small"]["one_sided_95"][1],
    )
    share = "pi_9B" if drop_4b else "pi_small"
    dr5 = rules.dr5(est[share]["one_sided_95"][0], est[share]["one_sided_95"][1], drop_4b)
    return {
        "tasks": int(y.shape[1]),
        "success_by_size_harness": _f(succ),
        "estimates": est,
        "tests": {
            "delta_paired_t": {
                "p": _f(t["p"]),
                "estimate": _f(t["estimate"]),
                "ci90_t": [_f(t["ci_low"]), _f(t["ci_high"])],
            },
            "delta_paired_t_by_size": [
                {"p": _f(tt["p"]), "estimate": _f(tt["estimate"])} for tt in t_by_size
            ],
            "x_signflip_p": p_x,
            "x_label_permutation_p_sensitivity": p_x_label,
            "session_signflip_p": _f(p_session),
        },
        "delta_session_heterogeneity": {k: _f(v) for k, v in het.items()},
        "session_common_share": {k: _f(v) for k, v in common.items()},
        "DR1_drop_4B": drop_4b,
        "DR2": dr2,
        "DR5": dr5,
    }


# --------------------------------------------------------------------------- records


def _flags_counts(finals: Mapping[R.SlotKey, Mapping[str, Any]]) -> dict[str, Any]:
    per_cell: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for (z, _s, _t, h, _r), rec in finals.items():
        cell = per_cell[f"{z}/{h}"]
        cell["episodes"] += 1
        cell[f"status_{rec['status']}"] += 1
        if rec["status"] == "infrastructure":
            cell[f"infra_{rec['infrastructure_type']}"] += 1
        for key in R.COUNTS:
            cell[key] += int(rec.get(key, 0))
        cell["metric_exceptions"] += int(bool(rec.get("metric_exception")))
        cell["fractional_scores"] += int(rec["status"] == "scored" and 0 < float(rec["score"]) < 1)
    return {k: dict(v) for k, v in sorted(per_cell.items())}


def truncation_labels(finals: Mapping[R.SlotKey, Mapping[str, Any]]) -> dict[str, Any]:
    """Share of steps ending at 2,048 tokens without a complete tool call, per (size,
    harness); a size whose share exceeds 20% under either harness has its delta labelled
    truncation-confounded."""
    steps: dict[tuple[str, str], int] = defaultdict(int)
    trunc: dict[tuple[str, str], int] = defaultdict(int)
    for (z, _s, _t, h, _r), rec in finals.items():
        steps[(z, h)] += int(rec.get("steps", 0))
        trunc[(z, h)] += int(rec.get("truncated_steps", 0))
    share = {f"{z}/{h}": (trunc[(z, h)] / steps[(z, h)] if steps[(z, h)] else None)
             for (z, h) in sorted(steps)}  # fmt: skip
    labelled = sorted({k.split("/")[0] for k, v in share.items() if v is not None and v > 0.20})
    return {"share": share, "truncation_confounded_sizes": labelled}


def exposure_strata(
    finals: Mapping[R.SlotKey, Mapping[str, Any]], tasks: Sequence[str]
) -> dict[str, list[str]]:
    """Tasks with and without any uncertified key action in any of their episodes."""
    exposed = {k[2] for k, rec in finals.items() if rec.get("uncertified_key_actions", 0)}
    return {
        "exposed": [t for t in tasks if t in exposed],
        "unexposed": [t for t in tasks if t not in exposed],
    }


def checker_noise(finals: Mapping[R.SlotKey, Mapping[str, Any]]) -> dict[str, int]:
    """Discordant rerun pairs whose checker inputs hash identically (checker or live-state
    noise, not agent noise), and live versus offline-rescored verdict mismatches."""
    by_cell: dict[tuple[str, str, str], list[Mapping[str, Any]]] = defaultdict(list)
    mismatches = 0
    for (z, _s, t, h, _r), rec in finals.items():
        if rec["status"] != "scored":
            continue
        by_cell[(z, t, h)].append(rec)
        off = rec.get("offline_score")
        if off is not None and float(off) != float(rec["score"]):
            mismatches += 1
    same_hash_discordant = 0
    discordant = 0
    for recs in by_cell.values():
        for i in range(len(recs)):
            for j in range(i + 1, len(recs)):
                a, b = recs[i], recs[j]
                if (float(a["score"]) == 1.0) != (float(b["score"]) == 1.0):
                    discordant += 1
                    ha, hb = a.get("checker_input_sha256"), b.get("checker_input_sha256")
                    if ha and ha == hb:
                        same_hash_discordant += 1
    return {
        "discordant_pairs": discordant,
        "discordant_pairs_identical_checker_inputs": same_hash_discordant,
        "live_vs_offline_mismatches": mismatches,
    }


def corrected_flips(
    finals: Mapping[R.SlotKey, Mapping[str, Any]], tasks: Sequence[str]
) -> dict[str, int]:
    """Per task, scored episodes whose corrected verdict differs from the raw one."""
    out: dict[str, int] = {}
    for (_z, _s, t, _h, _r), rec in finals.items():
        if t not in tasks or rec["status"] != "scored":
            continue
        corrected = rec.get("corrected_score")
        if corrected is not None and (float(corrected) == 1.0) != (float(rec["score"]) == 1.0):
            out[t] = out.get(t, 0) + 1
    return dict(sorted(out.items()))


def per_domain(
    finals: Mapping[R.SlotKey, Mapping[str, Any]],
    tasks: Sequence[str],
    domains: Mapping[str, str],
) -> dict[str, Any]:
    """Descriptive: tasks, success by size and harness, and delta per domain."""
    out: dict[str, Any] = {}
    for domain in sorted({domains[t] for t in tasks}):
        ts = [t for t in tasks if domains[t] == domain]
        y = R.outcome_array(finals, ts)
        out[domain] = {
            "tasks": len(ts),
            "success_by_size_harness": _f(E.success(y)),
            "delta": _f(E.delta(y)),
        }
    return out


def anchor_report(
    records: Iterable[Mapping[str, Any]],
    order: Sequence[str],
    public: Mapping[str, Sequence[float]],
    *,
    excluded: Sequence[str] = (),
) -> dict[str, Any]:
    """DR-A and the anchor's comparison on the reading set (section 5.7).

    ``order`` is the dispatched prefix of the anchor order (the first n tasks);
    ``public`` maps a task to the three public runs' scores; tasks in ``excluded``
    (changed config or evaluator, G0 item 9.6) leave the reading.
    """
    recs = list(records)
    finals = R.anchor_finals(recs)
    first, lost = R.anchor_first_attempt_losses(recs)
    read, lost_in_prefix = rules.anchor_reading_set(order, finals)
    read = [t for t in read if t not in set(excluded)]
    ours = [float(finals[t]["score"]) for t in read]
    pub = [[float(public[t][i]) for t in read] for i in range(3)]
    out = rules.dr_anchor(ours, pub, first_attempts=first, infrastructure_losses=lost)
    if read:
        o = np.asarray(ours) == 1.0
        p = np.asarray(pub) == 1.0
        out["discordance_ours_vs_public"] = [float(np.mean(o != p[i])) for i in range(3)]
        out["discordance_public_vs_public"] = float(
            np.mean([np.mean(p[i] != p[j]) for i in range(3) for j in range(i + 1, 3)])
        )
    out["lost_in_prefix"] = lost_in_prefix
    out["excluded"] = list(excluded)
    return out


def divergence_summary(step_logs: Mapping[R.SlotKey, Sequence[Mapping[str, Any]]]) -> dict:
    """First-divergence kinds per pair type (within or between sessions)."""
    groups: dict[tuple[str, str, str], list[tuple[str, int, Sequence]]] = defaultdict(list)
    for (z, s, t, h, r), steps in step_logs.items():
        groups[(z, t, h)].append((s, r, steps))
    out: dict[str, dict[str, int]] = {"within": defaultdict(int), "between": defaultdict(int)}
    for eps in groups.values():
        for i in range(len(eps)):
            for j in range(i + 1, len(eps)):
                kind = "within" if eps[i][0] == eps[j][0] else "between"
                out[kind][R.first_divergence(eps[i][2], eps[j][2])["kind"]] += 1
    return {k: dict(v) for k, v in out.items()}


def report(
    a1_records: Iterable[Mapping[str, Any]],
    plan: Mapping[str, Any],
    *,
    n_boot: int = N_BOOT,
    n_rand: int = N_RANDOMIZATION,
    step_logs: Mapping[R.SlotKey, Sequence[Mapping[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Primary (base, raw verdicts), sensitivities and the registered secondary set."""
    recs = [R.validate(r) for r in a1_records]
    finals = R.final_records(recs)
    base = list(plan["base"])
    blocks = {int(k): v for k, v in plan.get("extension_blocks", {}).items()}
    done = R.completed_extension_blocks(recs, blocks)
    secondary_tasks = base + [t for b in done for t in blocks[b]]
    flagged = list(plan.get("flagged_tasks", []))

    def run(tasks: Sequence[str], **kw: Any) -> dict[str, Any]:
        y = R.outcome_array(finals, tasks, **kw)
        return analyse_array(y, n_boot=n_boot, n_rand=n_rand)

    out: dict[str, Any] = {
        "primary": run(base),
        "sensitivity_metric_exception_missing": run(base, metric_exception_missing=True),
        "sensitivity_flagged_tasks_excluded": run([t for t in base if t not in flagged]),
        "secondary_base_plus_completed_extension": {
            "blocks": done,
            **run(secondary_tasks),
        },
        "fractional_score": _f(E.delta(R.outcome_array(finals, base, value="score"))),
        "cells": _flags_counts(finals),
        "truncation": truncation_labels(finals),
        "uncertified_exposure": exposure_strata(finals, base),
        "checker_noise": checker_noise(finals),
    }
    strata = out["uncertified_exposure"]
    out["delta_by_exposure_stratum"] = {
        name: (_f(E.delta(R.outcome_array(finals, tasks))) if tasks else None)
        for name, tasks in strata.items()
    }
    out["checker_corrected"] = {
        **run(base, value="corrected"),
        "flips_per_task": corrected_flips(finals, base),
    }
    mediator = R.outcome_array(finals, base, drop_truncated=True)
    out["truncation"]["delta_without_truncated_episodes_mediator_description"] = _f(
        E.delta(mediator)
    )
    if "task_domains" in plan:
        out["per_domain"] = per_domain(finals, base, plan["task_domains"])
    if step_logs is not None:
        out["first_divergence"] = divergence_summary(step_logs)
    costs = plan.get("realized_costs")
    exceeds = False
    if costs:
        dr4 = rules.dr4({job: (c["gpu_h_per_episode"], c["V"]) for job, c in costs.items()})
        out["DR4"] = dr4
        exceeds = dr4["exceeds_high"]
    prim = out["primary"]
    est = prim["estimates"]
    out["predictions"] = rules.predictions(
        excess_ub95=est["excess"]["one_sided_95"][1],
        db_ci95=tuple(est["D_b"]["ci95"]),
        dr2_class=prim["DR2"]["class"],
        dr1_fires=prim["DR1_drop_4B"],
        dr4_exceeds=exceeds,
    )
    out["conditional_on"] = "the realized sessions (tasks resampled, sessions fixed)"
    return out


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument(
        "--costs", type=Path, help="job -> {gpu_h_per_episode, V} from the job receipts (DR4)"
    )
    parser.add_argument("--anchor", type=Path, help="ANC episode records (JSONL)")
    parser.add_argument("--public", type=Path, help="task id -> three public scores (JSON)")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.out.exists():
        raise SystemExit(f"{args.out} exists; reports are never overwritten")
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    if args.costs:
        plan = {**plan, "realized_costs": json.loads(args.costs.read_text(encoding="utf-8"))}
    result = report(R.read_jsonl(args.records), plan, n_boot=N_BOOT, n_rand=N_RANDOMIZATION)
    if args.anchor and args.public:
        anchor = [
            json.loads(line)
            for line in args.anchor.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        public = json.loads(args.public.read_text(encoding="utf-8"))
        result["anchor"] = anchor_report(
            anchor,
            plan["anchor_tasks"],
            public,
            excluded=plan.get("anchor_excluded_tasks", []),
        )
    args.out.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
