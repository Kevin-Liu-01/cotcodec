"""Operating characteristics of the registered audit sample and K3 rule.

Synthetic confirm-scale candidate pools go through the registered sampler
(``raters.draw_audit_sample``, seed 42) and the registered summary
(``raters.summarize``: Hajek label error, ``stats.label_error_bound``, kappa,
K3 and K4). Nothing here reads a task, a mutant or a verdict of the real
campaign: the pool sizes are the expected evaluable counts of section 6 of the
preregistration (equivalence 59 tasks x 4.0 mutants, alternative solution
20 x 5.6, violation 17 x 5.2, extra change 9 x 3.0) and the violation task
count is swept over 8, 13, 17, 24 and 40.

Per replicate: per-task mutant counts are drawn around the dev means; the
checker verdict disagrees with the label with probability 0.10 (equivalence,
alternative, violation) or 0.20 (extra change); each mutant's a-priori label
is wrong with probability ``e`` (independently). Raters:

* ``perfect``: both raters answer the truth;
* ``noisy``: each rater answers the truth with probability 0.90, the opposite
  with 0.05 and ``unsure`` with 0.05, independently (so about 19% of items
  are split and go to Kevin); Kevin answers the truth on every split item
  (``noisy_adjudicated``) or adjudicates nothing (``noisy_unadjudicated``).

Reported per scenario (``audit-oc.json``): mean audited items and Kish
effective size per K3 group, P(the group is insufficiently audited),
P(K3 fires for the group without the kappa rule), P(kappa below 0.6),
P(K4), and the mean number of items Kevin adjudicates. ``design``: the
registered sampler (violation census stratum) or the second draft's
(violations shared with the other classes in the disagreement and
agreement strata), for comparison.

Usage (repository root): python program/evidence/q2-mutation/integration/
audit-design-v1/sim_audit_oc.py out.json [reps] [n_boot] [workers]
"""

from __future__ import annotations

import json
import random
import sys
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))

from harness.q2_mutation import raters  # noqa: E402
from harness.q2_mutation.stats import kish_effective_n  # noqa: E402

COUNTS = {"should_pass_equiv": [2, 3, 4, 4, 5, 6], "should_pass_alt_solution": [3, 5, 6, 6, 8]}
COUNTS["should_fail_violation"] = [3, 4, 5, 6, 8]
COUNTS["should_fail_extra_change"] = [2, 3, 4]
TASKS = {
    "should_pass_equiv": 59,
    "should_pass_alt_solution": 20,
    "should_fail_violation": 17,
    "should_fail_extra_change": 9,
}
DISAGREE = {
    "should_pass_equiv": 0.10,
    "should_pass_alt_solution": 0.10,
    "should_fail_violation": 0.10,
    "should_fail_extra_change": 0.20,
}


def old_stratum_of(candidate: raters.Candidate) -> str | None:
    """The second draft's strata: violations share disagreement and agreement."""
    if candidate.verdict == "error" or candidate.label == "ambiguous":
        return None
    if candidate.label == "should_pass_alt_solution":
        return "alt_solution"
    passes = candidate.verdict == "pass"
    if (candidate.label in raters.SHOULD_PASS_LABELS and not passes) or (
        candidate.label in raters.SHOULD_FAIL_LABELS and passes
    ):
        return "disagreement"
    return "agreement"


def pool(rng: random.Random, tasks: dict[str, int]) -> tuple[list[raters.Candidate], dict]:
    ids = [f"t{n:03d}" for n in range(80)]
    cands, truth = [], {}
    for label, n_tasks in tasks.items():
        for task in rng.sample(ids, n_tasks):
            for k in range(rng.choice(COUNTS[label])):
                mid = f"{task}__{label}__{k}"
                should_pass = label in raters.SHOULD_PASS_LABELS
                disagree = rng.random() < DISAGREE[label]
                verdict = "pass" if should_pass != disagree else "fail"
                cands.append(raters.Candidate(mid, task, label, verdict))
                truth[mid] = should_pass
    return cands, truth


def rate(rng: random.Random, correct: str, model: str) -> str:
    if model == "perfect":
        return correct
    x = rng.random()
    if x < 0.90:
        return correct
    if x < 0.95:
        return "reject" if correct == "accept" else "accept"
    return "unsure"


def one(args: tuple) -> dict:
    design, v_tasks, error, model, rep, n_boot = args
    rng = random.Random(f"oc:{design}:{v_tasks}:{error}:{model}:{rep}")
    tasks = {**TASKS, "should_fail_violation": v_tasks}
    cands, should_pass = pool(rng, tasks)
    saved = raters.stratum_of
    if design == "second_draft":
        raters.stratum_of = old_stratum_of
    try:
        sample = raters.draw_audit_sample(cands, seed=42)
    finally:
        raters.stratum_of = saved
    labels = {c.mutant_id: c.label for c in cands}
    ratings, adjudicated = {}, {}
    for s in sample:
        if s.sham is not None:
            correct = "accept" if s.sham == "gold" else "reject"
        else:
            label_ok = rng.random() >= error
            passes = should_pass[s.mutant_id] == label_ok
            correct = "accept" if passes else "reject"
        model_r = "perfect" if model == "perfect" else "noisy"
        pair = (rate(rng, correct, model_r), rate(rng, correct, model_r))
        ratings[s.mutant_id] = pair
        if model == "noisy_adjudicated" and raters.consensus(*pair) == "unresolved":
            adjudicated[s.mutant_id] = correct
    summary = raters.summarize(
        sample, labels, ratings, adjudicated=adjudicated, n_boot=n_boot, seed=42
    )
    out = {"adjudicated": summary.n_adjudicated, "unresolved": summary.n_unresolved}
    out["kappa_fires"] = summary.kappa_fires
    out["k4"] = summary.k4_fires
    out["items"] = len(sample)
    for group in raters.K3_GROUPS:
        bound = summary.k3[group]
        weights = [1 / s.inclusion_probability for s in sample if labels.get(s.mutant_id) == group]
        out[group] = {
            "n": bound.n_items if bound else 0,
            "kish": kish_effective_n(weights) if weights else 0.0,
            "insufficient": (bound is None) or (not bound.sufficient),
            "fires_without_kappa": (bound is None)
            or (not bound.sufficient)
            or bound.upper > raters.K3_THRESHOLD,
        }
    return out


def scenario(design: str, v_tasks: int, error: float, model: str, reps: int, n_boot: int, pool_):
    rows = pool_.map(one, [(design, v_tasks, error, model, r, n_boot) for r in range(reps)])
    mean = lambda xs: sum(xs) / len(xs)  # noqa: E731
    res = {
        "design": design,
        "violation_tasks": v_tasks,
        "true_label_error": error,
        "raters": model,
        "reps": reps,
        "mean_items": mean([r["items"] for r in rows]),
        "p_kappa_below_0_6": mean([r["kappa_fires"] for r in rows]),
        "p_k4": mean([r["k4"] for r in rows]),
        "mean_split_items": mean([r["unresolved"] for r in rows]),
        "mean_adjudicated_by_kevin": mean([r["adjudicated"] for r in rows]),
    }
    for group in raters.K3_GROUPS:
        res[group] = {
            "mean_n": mean([r[group]["n"] for r in rows]),
            "mean_kish": mean([r[group]["kish"] for r in rows]),
            "min_kish": min(r[group]["kish"] for r in rows),
            "p_insufficient": mean([r[group]["insufficient"] for r in rows]),
            "p_k3_fires_without_kappa": mean([r[group]["fires_without_kappa"] for r in rows]),
        }
    return res


def main() -> None:
    out_path = Path(sys.argv[1])
    reps = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    n_boot = int(sys.argv[3]) if len(sys.argv) > 3 else 1000
    workers = int(sys.argv[4]) if len(sys.argv) > 4 else 8
    plan = []
    for v_tasks in (8, 13, 17, 24, 40):
        for error in (0.0, 0.01, 0.02, 0.05, 0.10, 0.15):
            plan.append(("registered", v_tasks, error, "perfect"))
    for error in (0.0, 0.01, 0.02, 0.05):
        plan.append(("second_draft", 17, error, "perfect"))
    for model in ("noisy_adjudicated", "noisy_unadjudicated"):
        for error in (0.0, 0.02, 0.05, 0.10):
            plan.append(("registered", 17, error, model))
    results = []
    with Pool(workers) as pool_:
        for design, v_tasks, error, model in plan:
            res = scenario(design, v_tasks, error, model, reps, n_boot, pool_)
            results.append(res)
            print(json.dumps(res, sort_keys=True), flush=True)
    out_path.write_text(
        json.dumps(
            {
                "schema": "q2m-audit-oc-v1",
                "sampler": "raters.draw_audit_sample (seed 42), registered strata and caps",
                "summary": "raters.summarize (K3 bound: stats.label_error_bound)",
                "reps": reps,
                "n_boot": n_boot,
                "note": "n_boot is reduced from the registered 10,000 for run time; the "
                "exact Clopper-Pearson part of the bound does not depend on it",
                "expected_tasks": TASKS,
                "per_task_counts": COUNTS,
                "verdict_disagreement": DISAGREE,
                "scenarios": results,
            },
            indent=1,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
