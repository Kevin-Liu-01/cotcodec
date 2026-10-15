#!/usr/bin/env python3
"""AM1 study (CPU): analysis of the development-set pilot and the power simulation.

Subcommands:

* ``analyze --run-dir D --evidence A --output-dir O [--hand-labels H] [--private-dir P]``: reads
  the job's passes (reader, judges, attention), joins every request to its judged label and
  writes text-free JSON: the A/A identities, the judge's validation and agreement, every table's
  set-function summary and structure class, every estimator's credits and keep-set regret
  against the exact optimum, H1 and H2 aggregates with question-clustered bootstrap intervals,
  AM2's placebo analysis, AM6's internal-signal analysis and the kill criteria. ``--private-dir``
  (host only) receives the joined rows with reply texts.
* ``hand-sample --run-dir D --evidence A --output F``: the seeded, blind hand-check sample of
  judged reader items (host only: it holds LongMemEval text and replies).
* ``power --analysis-dir O --output F [--heldout N]``: simulates the registration's decision
  rules at the held-out size by resampling the development questions.
"""

from __future__ import annotations

import argparse
import gzip
import json
import math
import random
import sys
from collections import Counter, defaultdict
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for _path in (PROJECT_ROOT, PROJECT_ROOT / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from harness import memcredit as mc  # noqa: E402
from harness import memcredit_study as ms  # noqa: E402

READER, READER_AA = "reader-gpu0", "reader-gpu1"
JUDGE, JUDGE_AA, JUDGE2 = "judge32-gpu0", "judge32-gpu1", "judge8-gpu0"
ATTENTION = "attention-gpu1"
#: Estimators whose keep-set regret H2 reports, in table order. Exact ones first.
ESTIMATORS = (
    "shapley_exact",
    "banzhaf_exact",
    "loo",
    "leave_one_in",
    "perm_shapley_4",
    "perm_shapley_16",
    "snipw_64",
    "deletion_placebo",
    "swap_mean",
    "retrieval_rank",
    "attention_raw",
    "attention_xfit",
    "lexical_question",
    "reply_overlap",
    "length",
)
#: Reader calls each estimator needs per pool (the exact table has 2^8 = 256).
CALLS = {
    "shapley_exact": 256,
    "banzhaf_exact": 256,
    "loo": 9,
    "leave_one_in": 9,
    "perm_shapley_4": "<= 33",
    "perm_shapley_16": "<= 129",
    "snipw_64": 64,
    "deletion_placebo": 27,
    "swap_mean": 17,
    "retrieval_rank": 0,
    "attention_raw": "1 + 1 forward",
    "attention_xfit": "1 + 1 forward",
    "lexical_question": 0,
    "reply_overlap": 1,
    "length": 0,
}
STOCHASTIC = {"perm_shapley_4": 4, "perm_shapley_16": 16, "snipw_64": 64}
SIGNALS = (
    "attention_raw",
    "attention_xfit",
    "retrieval_rank",
    "lexical_question",
    "reply_overlap",
    "length",
)


# --------------------------------------------------------------------------- loading


def load_artifact(path: Path, config: dict[str, Any] | None = None) -> dict[str, Any]:
    artifact = json.loads(path.read_bytes())
    experiment, split = ms.artifact_rule(config or ms.load_config())
    if artifact.get("experiment_id") != experiment or artifact.get("split") != split:
        raise ms.StudyError("the study artifact belongs to another experiment or split")
    return artifact


def load_pass(run_dir: Path, worker: str, name: str = "all") -> dict[str, Any] | None:
    import memcredit_study as driver

    directory = run_dir / "sessions" / worker
    if not (directory / f"{name}.json").is_file():
        return None
    return driver.load_pass(directory, name)


def labels_from_pass(passed: dict[str, Any] | None) -> dict[int, dict[str, Any]]:
    if passed is None:
        return {}
    out = {}
    for index, row in passed["rows"].items():
        if row["finish"] not in ("stop", "length") or row["text"] is None:
            continue
        label, well_formed = ms.parse_judgment(row["text"])
        out[index] = {"label": label, "well_formed": well_formed, "text": row["text"]}
    return out


def gpu_of(run_dir: Path, worker: str) -> dict[str, Any] | None:
    path = run_dir / "sessions" / worker / "session.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8")).get("gpu")
    path = run_dir / "sessions" / worker / "attention.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8")).get("gpu")
    return None


# --------------------------------------------------------------------------- identity


def identity(run_dir: Path, a: str, b: str) -> dict[str, Any]:
    import memcredit_step0 as s0

    ref, other = load_pass(run_dir, a), load_pass(run_dir, b)
    if ref is None or other is None:
        return {"ref": a, "other": b, "missing": True}
    result = s0.compare(ref, other, {})
    result.pop("clusters", None)
    result.pop("clusters_all_identical", None)
    return {
        "ref": a,
        "other": b,
        "gpu_ref": gpu_of(run_dir, a),
        "gpu_other": gpu_of(run_dir, b),
        "requests_ref": len(ref["rows"]),
        "requests_other": len(other["rows"]),
    } | result


# --------------------------------------------------------------------------- joining


def join_rows(
    run_dir: Path, config: dict[str, Any], artifact: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[int, Any], dict[int, Any]]:
    """Every reader request with its reply and labels; the judge items with their labels."""

    reader = load_pass(run_dir, READER)
    if reader is None:
        raise ms.StudyError("the GPU-0 reader pass is missing")
    items = json.loads((run_dir / "judge-items.json").read_text(encoding="utf-8"))
    primary = labels_from_pass(load_pass(run_dir, JUDGE))
    secondary = labels_from_pass(load_pass(run_dir, JUDGE2))
    key_to_item = {
        (i["question_index"], i["response"]): i["index"] for i in items if i["source"] == "reader"
    }
    rows = []
    for request in ms.request_table(artifact, config["pools"]["arms"]):
        row = reader["rows"].get(request["index"])
        text = row["text"] if row and row["finish"] in ("stop", "length") else None
        q = artifact["questions"][request["question_index"]]
        entry = dict(request, reply=text, finish=row["finish"] if row else None)
        if text is not None:
            item = key_to_item.get((request["question_index"], text.strip()))
            entry["item"] = item
            entry["u"] = primary.get(item, {}).get("label") if item is not None else None
            entry["u_secondary"] = (
                secondary.get(item, {}).get("label") if item is not None else None
            )
            entry["u_contains"] = mc.contains_answer(text, q["answer"])
        else:
            entry.update(item=None, u=None, u_secondary=None, u_contains=None)
        rows.append(entry)
    return rows, items, primary, secondary


def pool_views(
    rows: Sequence[dict[str, Any]], artifact: dict[str, Any], key: str = "u"
) -> dict[tuple[int, str], dict[str, Any]]:
    """Per pool: the 2^k table, the swap and reorder utilities, and the full-pool reply."""

    views: dict[tuple[int, str], dict[str, Any]] = {}
    for r in rows:
        pool = (int(r["question_index"]), r["arm"])
        view = views.setdefault(pool, {"table": {}, "swap": {}, "reorder": {}, "replies": {}})
        if r["kind"] == "table":
            view["table"][int(r["mask"])] = r[key]
            view["replies"][int(r["mask"])] = r["reply"]
        elif r["kind"] == "swap":
            view["swap"][(int(r["slot"]), int(r["variant"]))] = r[key]
        else:
            view["reorder"][int(r["variant"])] = r[key]
    for (q_index, arm), view in views.items():
        k = len(artifact["questions"][q_index]["pools"][arm])
        complete = len(view["table"]) == 1 << k and all(
            v is not None for v in view["table"].values()
        )
        view["k"] = k
        view["complete"] = complete
        view["values"] = [float(view["table"][m]) for m in range(1 << k)] if complete else None
    return views


# --------------------------------------------------------------------------- credits


def lexical(text: str) -> set[str]:
    return set(mc.bm25_tokens(text))


def overlap(source: str, memory: str) -> float:
    a = lexical(source)
    return len(a & lexical(memory)) / len(a) if a else 0.0


def placebo_credit(view: dict[str, Any], k: int, variants: int) -> dict[str, Any]:
    """Deletion labels, swap effects and the placebo-filtered deletion credit of one pool."""

    values = view["values"]
    full = values[-1]
    loo = mc.loo_credit(values)
    swaps = [[view["swap"].get((i, v)) for v in range(variants)] for i in range(k)]
    reorders = [view["reorder"].get(v) for v in sorted(view["reorder"])]
    swap_effect = [[None if s is None else full - float(s) for s in slot] for slot in swaps]
    reorder_ok = all(r is not None and float(r) == full for r in reorders)
    filtered = []
    survives = []
    for i in range(k):
        effects = swap_effect[i]
        same = all(e is not None and e == loo[i] for e in effects)
        keep = loo[i] != 0 and reorder_ok and same
        survives.append(bool(keep) if loo[i] != 0 else None)
        filtered.append(loo[i] if keep else 0.0)
    swap_mean = [
        sum(e for e in effects if e is not None) / max(1, sum(e is not None for e in effects))
        for effects in swap_effect
    ]
    return {
        "loo": loo,
        "swap_effect": swap_effect,
        "swap_mean": swap_mean,
        "reorder_flips": [r is not None and float(r) != full for r in reorders],
        "reorder_ok": reorder_ok,
        "deletion_placebo": filtered,
        "survives": survives,
    }


def table_credits(
    view: dict[str, Any],
    question: dict[str, Any],
    arm: str,
    config: dict[str, Any],
    attention: dict[str, list[float]] | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Every estimator's credit vector (seeded ones per seed) and the placebo record."""

    values = view["values"]
    k = view["k"]
    pool = question["pools"][arm]
    variants = int(config["placebo"]["swap_variants"])
    plc = placebo_credit(view, k, variants)
    full_reply = view["replies"].get((1 << k) - 1) or ""
    credits: dict[str, Any] = {
        "shapley_exact": mc.shapley(values),
        "banzhaf_exact": ms.banzhaf(values),
        "loo": plc["loo"],
        "leave_one_in": ms.leave_one_in(values),
        "deletion_placebo": plc["deletion_placebo"],
        "swap_mean": plc["swap_mean"],
        "retrieval_rank": [-float(m["bm25_rank"]) for m in pool],
        "lexical_question": [overlap(question["question"], m["text"]) for m in pool],
        "reply_overlap": [overlap(full_reply, m["text"]) for m in pool],
        "length": [float(len(m["text"])) for m in pool],
    }
    if attention is not None:
        credits.update(attention)
    qid = question["question_id"]
    for name, draws in STOCHASTIC.items():
        per_seed = {}
        for seed in config["analysis"]["estimator_seeds"]:
            rng = random.Random(f"{seed}:{qid}:{arm}:{name}")
            if name.startswith("perm"):
                credit, calls = ms.permutation_shapley(values, draws, rng)
            else:
                credit, calls = ms.snipw(values, draws, rng)
            per_seed[str(seed)] = {"credit": credit, "calls": calls}
        credits[name] = per_seed
    return credits, plc


def regrets(values: Sequence[float], credits: dict[str, Any], budgets: Sequence[int]) -> dict:
    out: dict[str, Any] = {}
    for name, credit in credits.items():
        per_budget = {}
        for b in budgets:
            if isinstance(credit, dict):
                seeds = {
                    s: mc.keep_set_regret_range(values, c["credit"], b) for s, c in credit.items()
                }
                per_budget[str(b)] = {
                    "mean": sum(r["mean"] for r in seeds.values()) / len(seeds),
                    "min": sum(r["min"] for r in seeds.values()) / len(seeds),
                    "max": sum(r["max"] for r in seeds.values()) / len(seeds),
                    "per_seed": seeds,
                }
            else:
                per_budget[str(b)] = mc.keep_set_regret_range(values, credit, b)
        out[name] = per_budget
    out["random"] = {str(b): {"mean": ms.random_regret(values, b)} for b in budgets}
    return out


# --------------------------------------------------------------------------- attention (AM6)


def load_attention(run_dir: Path) -> tuple[dict[tuple[int, str], Any], dict[str, Any]]:
    import numpy as np

    directory = run_dir / "sessions" / ATTENTION
    if not (directory / "attention.json").is_file():
        return {}, {"missing": True}
    meta = json.loads((directory / "attention.json").read_text(encoding="utf-8"))
    masses = np.load(directory / "attention.npz")["masses"]
    ok = [p for p in meta["pools"] if p["status"] == "ok"]
    if len(ok) != len(masses):
        raise ms.StudyError("attention metadata and arrays differ in length")
    return {(p["question_index"], p["arm"]): masses[j] for j, p in enumerate(ok)}, meta


def xfit_heads(
    masses: dict[tuple[int, str], Any],
    targets: dict[tuple[int, str], list[float]],
    questions: Sequence[str],
    n_heads: int,
    seed: int,
) -> tuple[dict[tuple[int, str], list[float]], dict[str, Any]]:
    """Two-fold cross-fitting by question: heads ranked by mean per-table Spearman with exact
    Shapley on one fold score the other fold's tables (mean mass over the chosen heads)."""

    import numpy as np

    ids = sorted(set(questions))
    random.Random(seed).shuffle(ids)
    fold = {q: i % 2 for i, q in enumerate(ids)}
    credit: dict[tuple[int, str], list[float]] = {}
    chosen: dict[str, Any] = {}
    shape = next(iter(masses.values())).shape if masses else None
    for f in (0, 1):
        train = [key for key in targets if key in masses and fold[questions[key[0]]] != f]
        if not train or shape is None:
            continue
        layers, heads = shape[0], shape[1]
        score = np.zeros((layers, heads))
        count = np.zeros((layers, heads))
        for key in train:
            target = targets[key]
            for layer in range(layers):
                for head in range(heads):
                    rho = ms.spearman(list(masses[key][layer, head]), target)
                    if rho is not None:
                        score[layer, head] += rho
                        count[layer, head] += 1
        mean = np.where(count > 0, score / np.maximum(count, 1), -np.inf)
        flat = np.argsort(-mean, axis=None)[:n_heads]
        picks = [(int(i // heads), int(i % heads)) for i in flat]
        chosen[str(f)] = {
            "heads": picks,
            "train_tables": len(train),
            "mean_rho": [float(mean[p]) for p in picks],
        }
        for key, mass in masses.items():
            if fold[questions[key[0]]] == f:
                credit[key] = [
                    float(np.mean([mass[layer, head, j] for layer, head in picks]))
                    for j in range(mass.shape[-1])
                ]
    return credit, {"folds": chosen, "fold_of": fold}


# --------------------------------------------------------------------------- aggregation


def bootstrap_stat(
    clusters: dict[str, list[Any]],
    stat: Callable[[list[Any]], float | None],
    resamples: int,
    seed: int,
) -> dict[str, Any]:
    keys = sorted(k for k, v in clusters.items() if v)
    units = [x for k in keys for x in clusters[k]]
    point = stat(units) if units else None
    if point is None:
        return {"value": None, "ci": [None, None], "clusters": len(keys), "units": len(units)}
    rng = random.Random(seed)
    stats = []
    for _ in range(resamples):
        sample = [x for _ in keys for x in clusters[keys[rng.randrange(len(keys))]]]
        value = stat(sample)
        if value is not None:
            stats.append(value)
    stats.sort()
    lo = stats[int(math.floor(0.025 * (len(stats) - 1)))] if stats else None
    hi = stats[int(math.ceil(0.975 * (len(stats) - 1)))] if stats else None
    return {"value": point, "ci": [lo, hi], "clusters": len(keys), "units": len(units)}


def mean_or_none(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def ci_mean(
    clusters: dict[str, list[float]], config: dict[str, Any], alpha: float = 0.05
) -> dict[str, Any]:
    spec = config["analysis"]["bootstrap"]
    return ms.cluster_bootstrap(clusters, int(spec["resamples"]), int(spec["seed"]), alpha)


def h1_summary(tables: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for arm in ("retrieved", "gold", "both"):
        chosen = [
            t
            for t in tables
            if t["complete"] and not t["summary"]["constant"] and (arm == "both" or t["arm"] == arm)
        ]
        share = defaultdict(list)
        excess = defaultdict(list)
        excess_rel = defaultdict(list)
        above = defaultdict(list)
        for t in chosen:
            s = t["summary"]
            q = t["question_id"]
            share[q].append(s["fourier_share_order_2_plus"])
            if s["and_or_baseline"] is not None:
                excess[q].append(s["fourier_share_order_2_plus"] - s["and_or_baseline"])
                above[q].append(
                    float(s["fourier_share_order_2_plus"] > s["and_or_baseline"] + 1e-9)
                )
            rel = mc.and_or_baseline(len(s["relevant"])) if s["relevant"] else None
            if rel is not None:
                excess_rel[q].append(s["fourier_share_order_2_plus"] - rel)
        out[arm] = {
            "tables": len(chosen),
            "share_order_2_plus": ci_mean(share, config),
            "excess_over_gold_count_baseline": ci_mean(excess, config),
            "share_above_gold_count_baseline": ci_mean(above, config),
            "excess_over_relevant_count_baseline": ci_mean(excess_rel, config),
            "by_structure": {
                cls: mean_or_none(
                    [
                        t["summary"]["fourier_share_order_2_plus"]
                        for t in chosen
                        if t["summary"]["structure"] == cls
                    ]
                )
                for cls in sorted({t["summary"]["structure"] for t in chosen})
            },
        }
    return out


def h2_summary(tables: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    budgets = [str(b) for b in config["analysis"]["keep_budgets"]]
    out: dict[str, Any] = {}
    for arm in ("retrieved", "gold", "both"):
        chosen = [t for t in tables if t.get("regret") and (arm == "both" or t["arm"] == arm)]
        per_arm: dict[str, Any] = {
            "tables": len(chosen),
            "questions": len({t["question_id"] for t in chosen}),
        }
        for b in budgets:
            rows: dict[str, Any] = {}
            binding = [t for t in chosen if t["regret"]["random"][b]["mean"] > 0]
            rows["tables_where_budget_binds"] = len(binding)
            for name in (*ESTIMATORS, "random"):
                clusters: dict[str, list[float]] = defaultdict(list)
                worst: dict[str, list[float]] = defaultdict(list)
                subopt: dict[str, list[float]] = defaultdict(list)
                paired: dict[str, list[float]] = defaultdict(list)
                for t in chosen:
                    r = t["regret"].get(name, {}).get(b)
                    if r is None:
                        continue
                    clusters[t["question_id"]].append(r["mean"])
                    if "max" in r:
                        worst[t["question_id"]].append(r["max"])
                    subopt[t["question_id"]].append(float(r["mean"] > 1e-12))
                    paired[t["question_id"]].append(
                        r["mean"] - t["regret"]["shapley_exact"][b]["mean"]
                    )
                if not clusters:
                    continue
                rows[name] = {
                    "mean_regret": ci_mean(clusters, config),
                    "mean_regret_99": ci_mean(clusters, config, 0.01),
                    "worst_tie_regret": ci_mean(worst, config) if worst else None,
                    "suboptimal_rate": ci_mean(subopt, config),
                    "minus_exact_shapley": ci_mean(paired, config),
                }
            per_arm[b] = rows
        out[arm] = per_arm
    return out


def placebo_summary(tables: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for arm in ("retrieved", "gold", "both"):
        chosen = [t for t in tables if t.get("placebo") and (arm == "both" or t["arm"] == arm)]
        per: dict[str, Any] = {"pools": len(chosen)}
        for cls in ("gold", "nongold"):
            deletion: dict[str, list[float]] = defaultdict(list)
            swap: dict[str, list[float]] = defaultdict(list)
            swap_when_null: dict[str, list[float]] = defaultdict(list)
            survive: dict[str, list[float]] = defaultdict(list)
            for t in chosen:
                p = t["placebo"]
                gold_mask = t["summary"]["gold_mask"]
                for i in range(t["summary"]["k"]):
                    if bool(gold_mask >> i & 1) != (cls == "gold"):
                        continue
                    q = t["question_id"]
                    flip = float(p["loo"][i] != 0)
                    deletion[q].append(flip)
                    effects = [e for e in p["swap_effect"][i] if e is not None]
                    swap[q].extend(float(e != 0) for e in effects)
                    if p["loo"][i] == 0:
                        swap_when_null[q].extend(float(e != 0) for e in effects)
                    if p["survives"][i] is not None:
                        survive[q].append(float(p["survives"][i]))
            dele = ci_mean(deletion, config)
            sw = ci_mean(swap, config)
            ratio = (sw["mean"] / dele["mean"]) if dele["mean"] else None
            per[cls] = {
                "deletion_flip_rate": dele,
                "swap_flip_rate": sw,
                "swap_flip_rate_where_deletion_null": ci_mean(swap_when_null, config),
                "deletion_label_survival": ci_mean(survive, config),
                "swap_to_deletion_ratio": ratio,
            }
        reorder: dict[str, list[float]] = defaultdict(list)
        for t in chosen:
            reorder[t["question_id"]].extend(float(f) for f in t["placebo"]["reorder_flips"])
        per["reorder_flip_rate"] = ci_mean(reorder, config)
        out[arm] = per
    return out


def internal_summary(
    tables: list[dict[str, Any]], config: dict[str, Any], meta: dict[str, Any]
) -> dict[str, Any]:
    spec = config["analysis"]["bootstrap"]
    out: dict[str, Any] = {"attention_meta": {k: v for k, v in meta.items() if k not in ("pools",)}}
    for arm in ("retrieved", "gold", "both"):
        chosen = [t for t in tables if t.get("credits") and (arm == "both" or t["arm"] == arm)]
        per: dict[str, Any] = {}
        for name in SIGNALS:
            units: dict[str, list[tuple[float, int]]] = defaultdict(list)
            rhos: dict[str, list[float]] = defaultdict(list)
            for t in chosen:
                credit = t["credits"].get(name)
                if credit is None:
                    continue
                if t["summary"]["u_full"] == 1.0:
                    for c, d in zip(credit, t["credits"]["loo"], strict=True):
                        units[t["question_id"]].append((float(c), int(d > 0)))
                rho = ms.spearman(credit, t["credits"]["shapley_exact"])
                if rho is not None:
                    rhos[t["question_id"]].append(rho)

            def auc(sample: list[tuple[float, int]]) -> float | None:
                return ms.auroc([s for s, _ in sample], [y for _, y in sample])

            per[name] = {
                "necessity_auroc": bootstrap_stat(
                    units, auc, int(spec["resamples"]) // 4, int(spec["seed"])
                ),
                "spearman_with_shapley": ci_mean(rhos, config),
            }
        out[arm] = per
    return out


def kill_criteria(
    tables: list[dict[str, Any]],
    identity_rows: dict[str, Any],
    h2: dict[str, Any],
    placebo: dict[str, Any],
    internal: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    b = str(config["analysis"]["headline_budget"])
    reader = identity_rows["reader_cross_gpu"]
    k1 = reader.get("differing_total", 1) > 0 or reader.get("missing", False)
    by_question: dict[str, list[bool]] = defaultdict(list)
    for t in tables:
        if t["complete"]:
            by_question[t["question_id"]].append(t["summary"]["constant"])
    constant_q = sum(all(v) for v in by_question.values())
    nonconst = [t for t in tables if t["complete"] and not t["summary"]["constant"]]
    order1 = [1.0 - t["summary"]["fourier_share_order_2_plus"] for t in nonconst]
    frac_order1 = (sum(o >= 0.9 for o in order1) / len(order1)) if order1 else None
    both = h2.get("both", {}).get(b, {})

    def optimal_rate(name: str) -> float | None:
        row = both.get(name)
        return None if row is None else 1.0 - row["suboptimal_rate"]["mean"]

    loo_opt, shap_opt = optimal_rate("loo"), optimal_rate("shapley_exact")
    k3 = (
        frac_order1 is not None
        and frac_order1 >= 0.9
        and loo_opt is not None
        and shap_opt is not None
        and loo_opt >= 0.95
        and shap_opt >= 0.95
    )
    ng = placebo.get("both", {}).get("nongold", {})
    am2_k2 = (ng.get("deletion_flip_rate", {}).get("mean") or 0) < 0.01 and (
        ng.get("swap_flip_rate", {}).get("mean") or 0
    ) < 0.01
    am6 = internal.get("both", {})
    aucs = {n: (am6.get(n, {}).get("necessity_auroc", {}) or {}).get("value") for n in SIGNALS}
    internal_best = max(
        (v for n, v in aucs.items() if n.startswith("attention") and v is not None), default=None
    )
    cheap_best = max(
        (v for n, v in aucs.items() if not n.startswith("attention") and v is not None),
        default=None,
    )
    return {
        "k1_aa_differs": k1,
        "k2_constant_questions": {
            "constant": constant_q,
            "questions": len(by_question),
            "share": constant_q / len(by_question) if by_question else None,
            "fires": bool(by_question) and constant_q / len(by_question) > 0.6,
        },
        "k3_interactions_do_not_matter": {
            "share_nonconstant_order1_ge_0.9": frac_order1,
            "loo_optimal_rate": loo_opt,
            "shapley_optimal_rate": shap_opt,
            "fires": k3,
        },
        "am2_k2_flip_rates_below_1pct": am2_k2,
        "am6": {
            "best_internal_auroc": internal_best,
            "best_cheap_auroc": cheap_best,
            "k1_cheap_within_0.03": None
            if internal_best is None or cheap_best is None
            else cheap_best >= internal_best - 0.03,
            "k2_all_below_0.65": None
            if not [v for v in aucs.values() if v is not None]
            else all(v < 0.65 for v in aucs.values() if v is not None),
        },
    }


# --------------------------------------------------------------------------- judge


def judge_summary(
    rows: list[dict[str, Any]],
    items: list[dict[str, Any]],
    primary: dict[int, Any],
    secondary: dict[int, Any],
    hand: list[dict[str, Any]] | None,
    artifact: dict[str, Any],
) -> dict[str, Any]:
    out: dict[str, Any] = {"items": len(items)}
    validation: dict[str, Any] = {}
    for source in ("validation:reference", "validation:idk", "validation:other-answer"):
        chosen = [i for i in items if i["source"] == source]
        for name, labels in (("primary", primary), ("secondary", secondary)):
            hits = [
                labels[i["index"]]["label"] == i["expected"] for i in chosen if i["index"] in labels
            ]
            by_type: dict[str, list[int]] = defaultdict(list)
            for i in chosen:
                if i["index"] in labels:
                    by_type[i["question_type"]].append(
                        int(labels[i["index"]]["label"] == i["expected"])
                    )
            validation.setdefault(source, {})[name] = {
                "n": len(hits),
                "correct": sum(hits),
                "accuracy": sum(hits) / len(hits) if hits else None,
                "ci95": list(mc.clopper_pearson(sum(hits), len(hits))) if hits else None,
                "by_type": {t: f"{sum(v)}/{len(v)}" for t, v in sorted(by_type.items())},
            }
    out["validation"] = validation
    reader_items = [i for i in items if i["source"] == "reader"]
    both = [i for i in reader_items if i["index"] in primary and i["index"] in secondary]
    a = [primary[i["index"]]["label"] for i in both]
    b = [secondary[i["index"]]["label"] for i in both]
    contains = [
        mc.contains_answer(i["response"], artifact["questions"][i["question_index"]]["answer"])
        for i in both
    ]
    out["reader_items"] = {
        "n": len(reader_items),
        "primary_yes": sum(
            primary[i["index"]]["label"] for i in reader_items if i["index"] in primary
        ),
        "primary_well_formed": sum(
            primary[i["index"]]["well_formed"] for i in reader_items if i["index"] in primary
        ),
        "secondary_well_formed": sum(
            secondary[i["index"]]["well_formed"] for i in reader_items if i["index"] in secondary
        ),
        "primary_vs_secondary": {
            "n": len(both),
            "agree": sum(x == y for x, y in zip(a, b, strict=True)),
            "kappa": ms.cohen_kappa(a, b),
        },
        "primary_vs_containment": {
            "n": len(both),
            "agree": sum(x == y for x, y in zip(a, contains, strict=True)),
            "kappa": ms.cohen_kappa(a, contains),
        },
    }
    cells = [r for r in rows if r["u"] is not None]
    out["table_cells"] = {
        "n": len(cells),
        "primary_vs_secondary_agree": sum(
            r["u"] == r["u_secondary"] for r in cells if r["u_secondary"] is not None
        ),
        "primary_vs_secondary_n": sum(r["u_secondary"] is not None for r in cells),
        "primary_vs_containment_agree": sum(r["u"] == r["u_contains"] for r in cells),
    }
    if hand:
        joined = [h for h in hand if h["item_index"] in primary]
        labels = [int(h["label"]) for h in joined]
        result: dict[str, Any] = {"n": len(joined)}
        for name, source in (("primary", primary), ("secondary", secondary)):
            pred = [source[h["item_index"]]["label"] for h in joined if h["item_index"] in source]
            if len(pred) != len(labels):
                continue
            agree = sum(x == y for x, y in zip(pred, labels, strict=True))
            result[name] = {
                "agree": agree,
                "accuracy": agree / len(labels),
                "ci95": list(mc.clopper_pearson(agree, len(labels))),
                "kappa": ms.cohen_kappa(pred, labels),
                "false_yes": sum(p == 1 and y == 0 for p, y in zip(pred, labels, strict=True)),
                "false_no": sum(p == 0 and y == 1 for p, y in zip(pred, labels, strict=True)),
            }
        cont = [
            mc.contains_answer(
                items[h["item_index"]]["response"],
                artifact["questions"][items[h["item_index"]]["question_index"]]["answer"],
            )
            for h in joined
        ]
        agree = sum(x == y for x, y in zip(cont, labels, strict=True))
        result["containment"] = {
            "agree": agree,
            "accuracy": agree / len(labels) if labels else None,
            "kappa": ms.cohen_kappa(cont, labels),
        }
        out["hand_check"] = result
    return out


# --------------------------------------------------------------------------- analyze


def analyze(
    run_dir: Path,
    config: dict[str, Any],
    artifact: dict[str, Any],
    out_dir: Path,
    hand: list[dict[str, Any]] | None = None,
    private_dir: Path | None = None,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    identity_rows = {
        "reader_cross_gpu": identity(run_dir, READER, READER_AA),
        "judge_cross_gpu": identity(run_dir, JUDGE, JUDGE_AA),
    }
    rows, items, primary, secondary = join_rows(run_dir, config, artifact)
    views = pool_views(rows, artifact)
    masses, attention_meta = load_attention(run_dir)
    budgets = [int(b) for b in config["analysis"]["keep_budgets"]]
    tables: list[dict[str, Any]] = []
    raw_attention: dict[tuple[int, str], list[float]] = {}
    for key, mass in masses.items():
        raw_attention[key] = [float(x) for x in mass.mean(axis=(0, 1))]
    shapley_targets = {}
    for key, view in views.items():
        if view["complete"] and len(set(view["values"])) > 1:
            shapley_targets[key] = mc.shapley(view["values"])
    questions = [q["question_id"] for q in artifact["questions"]]
    xfit, xfit_meta = xfit_heads(
        masses,
        shapley_targets,
        questions,
        int(config["internal"]["xfit_heads"]),
        int(config["internal"]["xfit_seed"]),
    )
    for (q_index, arm), view in sorted(views.items()):
        question = artifact["questions"][q_index]
        pool = question["pools"][arm]
        gold_mask = sum(1 << i for i, m in enumerate(pool) if m["is_gold"])
        entry: dict[str, Any] = {
            "question_id": question["question_id"],
            "question_type": question["question_type"],
            "arm": arm,
            "complete": view["complete"],
        }
        if view["complete"]:
            entry["values_hex"] = format(
                int("".join(str(int(v)) for v in reversed(view["values"])), 2), "064x"
            )
            entry["summary"] = ms.table_summary(view["values"], gold_mask)
            entry["distinct_replies"] = len({t for t in view["replies"].values() if t})
            attention = None
            if (q_index, arm) in raw_attention:
                attention = {"attention_raw": raw_attention[(q_index, arm)]}
                if (q_index, arm) in xfit:
                    attention["attention_xfit"] = xfit[(q_index, arm)]
            credits, plc = table_credits(view, question, arm, config, attention)
            entry["placebo"] = plc
            entry["credits"] = {k: v for k, v in credits.items() if not isinstance(v, dict)}
            entry["credits_seeded"] = {k: v for k, v in credits.items() if isinstance(v, dict)}
            if not entry["summary"]["constant"]:
                entry["regret"] = regrets(view["values"], credits, budgets)
        tables.append(entry)
    h1 = h1_summary(tables, config)
    h2 = h2_summary(tables, config)
    placebo = placebo_summary(tables, config)
    internal = internal_summary(tables, config, attention_meta)
    judge = judge_summary(rows, items, primary, secondary, hand, artifact)
    kill = kill_criteria(tables, identity_rows, h2, placebo, internal, config)
    census: dict[str, Any] = {}
    for arm in ("retrieved", "gold"):
        chosen = [t for t in tables if t["arm"] == arm and t["complete"]]
        census[arm] = {
            "tables": len(chosen),
            "structure": dict(Counter(t["summary"]["structure"] for t in chosen).most_common()),
            "u_full_rate": mean_or_none([t["summary"]["u_full"] for t in chosen]),
            "u_empty_rate": mean_or_none([t["summary"]["u_empty"] for t in chosen]),
            "nonconstant": sum(not t["summary"]["constant"] for t in chosen),
            "nongold_relevant": sum(bool(t["summary"]["relevant_nongold"]) for t in chosen),
            "by_type": {
                qt: dict(
                    Counter(t["summary"]["structure"] for t in chosen if t["question_type"] == qt)
                )
                for qt in sorted({t["question_type"] for t in chosen})
            },
            "gold_in_pool": dict(
                sorted(Counter(t["summary"]["gold_in_pool"] for t in chosen).items())
            ),
        }
    headline = {
        "experiment_id": config["experiment_id"],
        "claim_level": "exploratory",
        "split": artifact["split"],
        "questions": len(artifact["questions"]),
        "identity": {
            k: {
                x: v.get(x)
                for x in (
                    "n_common",
                    "identical_tokens",
                    "identical_tokens_and_logprob_bits",
                    "ci95_tokens",
                    "differing_total",
                    "gpu_ref",
                    "gpu_other",
                )
            }
            for k, v in identity_rows.items()
        },
        "census": census,
        "kill": kill,
    }
    write = {
        "identity.json": identity_rows,
        "judge.json": judge,
        "tables.json": tables,
        "h1.json": h1,
        "h2.json": h2,
        "placebo.json": placebo,
        "internal.json": internal,
        "xfit.json": {"folds": xfit_meta["folds"]},
        "headline.json": headline,
    }
    for name, payload in write.items():
        (out_dir / name).write_bytes(mc.canonical_json(payload))
    (out_dir / "tables.md").write_text(
        render_markdown(headline, h1, h2, placebo, internal, judge, config), encoding="utf-8"
    )
    if private_dir is not None:
        private_dir.mkdir(parents=True, exist_ok=True)
        with gzip.open(private_dir / "rows.jsonl.gz", "wt", encoding="utf-8") as handle:
            for r in rows:
                handle.write(json.dumps(r, ensure_ascii=False) + "\n")
    return {"headline": headline, "h2": h2}


def _fmt(value: Any, digits: int = 3) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _ci(row: dict[str, Any] | None, digits: int = 3) -> str:
    if not row or row.get("mean", row.get("value")) is None:
        return ""
    point = row.get("mean", row.get("value"))
    lo, hi = row["ci"]
    return f"{point:.{digits}f} [{_fmt(lo, digits)}, {_fmt(hi, digits)}]"


def render_markdown(
    headline: dict[str, Any],
    h1: dict[str, Any],
    h2: dict[str, Any],
    placebo: dict[str, Any],
    internal: dict[str, Any],
    judge: dict[str, Any],
    config: dict[str, Any],
) -> str:
    lines = ["# AM1 development pilot (EXPLORATORY): tables", ""]
    lines += [
        "## Census",
        "",
        "| Arm | Tables | Non-constant | u(full) | u(empty) | Structures | Non-gold relevant |",
        "|---|---:|---:|---:|---:|---|---:|",
    ]
    for arm, c in headline["census"].items():
        lines.append(
            f"| {arm} | {c['tables']} | {c['nonconstant']} | {_fmt(c['u_full_rate'])} "
            f"| {_fmt(c['u_empty_rate'])} | {c['structure']} | {c['nongold_relevant']} |"
        )
    lines += [
        "",
        "## H1 (order >= 2 Fourier share, non-constant tables)",
        "",
        "| Arm | Tables | Share | Excess over gold-count AND/OR | Share above baseline "
        "| Excess over relevant-count AND/OR |",
        "|---|---:|---|---|---|---|",
    ]
    for arm, h in h1.items():
        lines.append(
            f"| {arm} | {h['tables']} | {_ci(h['share_order_2_plus'])} "
            f"| {_ci(h['excess_over_gold_count_baseline'])} "
            f"| {_ci(h['share_above_gold_count_baseline'])} "
            f"| {_ci(h['excess_over_relevant_count_baseline'])} |"
        )
    for b in [str(x) for x in config["analysis"]["keep_budgets"]]:
        lines += [
            "",
            f"## H2 keep-set regret at B = {b} (mean over tie-breaks; question-clustered"
            " 95% bootstrap)",
            "",
            "| Estimator | Calls | retrieved regret | retrieved "
            "suboptimal | gold regret | gold suboptimal |",
            "|---|---|---|---|---|---|",
        ]
        for name in (*ESTIMATORS, "random"):
            cells = []
            for arm in ("retrieved", "gold"):
                row = h2.get(arm, {}).get(b, {}).get(name)
                cells += [
                    _ci(row["mean_regret"]) if row else "",
                    _ci(row["suboptimal_rate"]) if row else "",
                ]
            lines.append(f"| {name} | {CALLS.get(name, '')} | " + " | ".join(cells) + " |")
    lines += [
        "",
        "## AM2 placebo arms (both arms pooled)",
        "",
        "| Class | Deletion flip | Swap flip | Swap flip where deletion null "
        "| Deletion-label survival |",
        "|---|---|---|---|---|",
    ]
    for cls in ("gold", "nongold"):
        p = placebo.get("both", {}).get(cls, {})
        lines.append(
            f"| {cls} | {_ci(p.get('deletion_flip_rate'))} | {_ci(p.get('swap_flip_rate'))}"
            f" | {_ci(p.get('swap_flip_rate_where_deletion_null'))} "
            f"| {_ci(p.get('deletion_label_survival'))} |"
        )
    lines.append(
        f"\nReorder flip rate (both arms): {_ci(placebo.get('both', {}).get('reorder_flip_rate'))}"
    )
    lines += [
        "",
        "## AM6 signals (both arms pooled)",
        "",
        "| Signal | Necessity AUROC (u(full) = 1) | Spearman with exact Shapley |",
        "|---|---|---|",
    ]
    for name in SIGNALS:
        row = internal.get("both", {}).get(name, {})
        lines.append(
            f"| {name} | {_ci(row.get('necessity_auroc'))} "
            f"| {_ci(row.get('spearman_with_shapley'))} |"
        )
    lines += [
        "",
        "## Judge",
        "",
        "```",
        json.dumps({k: v for k, v in judge.items() if k != "validation"}, indent=1),
        "```",
    ]
    lines += ["", "## Kill criteria", "", "```", json.dumps(headline["kill"], indent=1), "```"]
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- hand sample


def hand_sample(
    run_dir: Path, config: dict[str, Any], artifact: dict[str, Any]
) -> list[dict[str, Any]]:
    """Seeded sample of judged reader items: half judged yes, half judged no (all of a side if it
    has fewer), shuffled, without the judges' labels."""

    items = json.loads((run_dir / "judge-items.json").read_text(encoding="utf-8"))
    primary = labels_from_pass(load_pass(run_dir, JUDGE))
    spec = config["judge"]["hand_check"]
    rng = random.Random(int(spec["seed"]))
    reader = [i for i in items if i["source"] == "reader" and i["index"] in primary]
    yes = sorted(i["index"] for i in reader if primary[i["index"]]["label"] == 1)
    no = sorted(i["index"] for i in reader if primary[i["index"]]["label"] == 0)
    half = int(spec["size"]) // 2
    take_yes = min(len(yes), half)
    take_no = min(len(no), int(spec["size"]) - take_yes)
    chosen = rng.sample(yes, take_yes) + rng.sample(no, take_no)
    rng.shuffle(chosen)
    out = []
    for index in chosen:
        item = items[index]
        q = artifact["questions"][item["question_index"]]
        out.append(
            {
                "item_index": index,
                "question_id": q["question_id"],
                "question_type": q["question_type"],
                "question": q["question"],
                "reference_answer": str(q["answer"]),
                "reply": item["response"],
                "reply_sha256": mc.sha256_text(item["response"]),
            }
        )
    return out


# --------------------------------------------------------------------------- power


#: The registration's primary H2 family (retrieved arm, B = 4) and its decision thresholds.
PRIMARY_FAMILY = ("loo", "perm_shapley_16", "snipw_64", "retrieval_rank", "attention_raw")
MATERIAL_REGRET = 0.05
ADEQUATE_REGRET = 0.02
SCALES = (1.0, 0.5, 0.25)


def power(analysis_dir: Path, config: dict[str, Any], heldout: int) -> dict[str, Any]:
    """Resample development questions to the held-out size and apply the registration's rules.

    For every statistic (a per-question value: one table per question and arm), each simulation
    draws the held-out number of units (held-out questions times the development rate of
    non-constant tables) with replacement from the development values, optionally scaled by
    0.5 or 0.25 (a smaller true effect with the same shape), and computes the mean and its
    question-bootstrap interval: 99% (Bonferroni over the five primary estimators) for H2 and
    95% for H1. It reports how often H2's rules fire: MISSPECIFIED when the 99% lower bound
    exceeds 0.05, ADEQUATE when the 99% upper bound is below 0.02, else INCONCLUSIVE.
    """

    import numpy as np

    tables = json.loads((analysis_dir / "tables.json").read_text(encoding="utf-8"))
    spec = config["analysis"]["power"]
    rng = np.random.default_rng(int(spec["seed"]))
    sims = int(spec["simulations"])
    inner = 1000
    b = str(config["analysis"]["headline_budget"])
    questions = sorted({t["question_id"] for t in tables})
    by_q: dict[str, dict[str, Any]] = {q: {} for q in questions}
    for t in tables:
        by_q[t["question_id"]][t["arm"]] = t

    def per_question(arm: str, fn: Callable[[dict[str, Any]], float | None]) -> list[float | None]:
        return [fn(by_q[q][arm]) if arm in by_q[q] else None for q in questions]

    def regret_fn(name: str, budget: str) -> Callable[[dict[str, Any]], float | None]:
        def fn(t: dict[str, Any]) -> float | None:
            if not t.get("regret") or name not in t["regret"]:
                return None  # constant table (no keep-set decision) or estimator missing
            return t["regret"][name][budget]["mean"]

        return fn

    def excess_fn(t: dict[str, Any]) -> float | None:
        s = t.get("summary")
        if not s or s["constant"] or s["and_or_baseline"] is None:
            return None
        return s["fourier_share_order_2_plus"] - s["and_or_baseline"]

    stats: dict[str, tuple[list[float | None], float, bool]] = {}
    for arm in ("retrieved", "gold"):
        for name in (*PRIMARY_FAMILY, "shapley_exact", "random"):
            stats[f"h2:{arm}:{name}:B{b}"] = (per_question(arm, regret_fn(name, b)), 0.01, True)
        stats[f"h1:{arm}:excess"] = (per_question(arm, excess_fn), 0.05, False)
    result: dict[str, Any] = {
        "heldout_questions": heldout, "simulations": sims, "inner_bootstrap": inner,
        "development_questions": len(questions), "material_regret": MATERIAL_REGRET,
        "adequate_regret": ADEQUATE_REGRET, "scales": list(SCALES), "statistics": {},
    }  # fmt: skip
    for key, (values, alpha, is_h2) in stats.items():
        present = np.array([v for v in values if v is not None], dtype=float)
        if len(present) < 2:
            continue
        rate = len(present) / len(values)
        n_units = max(2, int(round(heldout * rate)))
        row: dict[str, Any] = {
            "development_units": int(len(present)), "development_mean": float(present.mean()),
            "development_sd": float(present.std(ddof=1)), "unit_rate": rate,
            "expected_heldout_units": n_units, "interval": 1 - alpha, "by_scale": {},
        }  # fmt: skip
        for scale in SCALES if is_h2 else (1.0,):
            base = present * scale
            means = np.empty(sims)
            los = np.empty(sims)
            his = np.empty(sims)
            for s in range(sims):
                sample = base[rng.integers(0, len(base), n_units)]
                boot = sample[rng.integers(0, n_units, (inner, n_units))].mean(axis=1)
                means[s] = sample.mean()
                los[s], his[s] = np.quantile(boot, [alpha / 2, 1 - alpha / 2])
            entry = {"true_mean": float(base.mean()), "median_halfwidth": float(np.median(
                (his - los) / 2)), "p_lower_above_0": float(np.mean(los > 0))}  # fmt: skip
            if is_h2:
                material = los > MATERIAL_REGRET
                adequate = his < ADEQUATE_REGRET
                entry.update(p_misspecified=float(np.mean(material)),
                             p_adequate=float(np.mean(adequate)),
                             p_inconclusive=float(np.mean(~material & ~adequate)))  # fmt: skip
            row["by_scale"][str(scale)] = entry
        result["statistics"][key] = row
    return result


# --------------------------------------------------------------------------- A/A diagnostic


def judged_labels(runs: dict[str, Path]) -> dict[tuple[int, str], set[int]]:
    """(question index, stripped reply) -> the primary judge's labels over every run's items."""

    labels: dict[tuple[int, str], set[int]] = defaultdict(set)
    for run_dir in runs.values():
        path = run_dir / "judge-items.json"
        if not path.is_file():
            continue
        items = json.loads(path.read_text(encoding="utf-8"))
        primary = labels_from_pass(load_pass(run_dir, JUDGE))
        for item in items:
            if item["source"] == "reader" and item["index"] in primary:
                labels[(item["question_index"], item["response"])].add(
                    primary[item["index"]]["label"]
                )
    return labels


def aa_pair(
    runs: dict[str, Path],
    a: str,
    b: str,
    labels: dict[tuple[int, str], set[int]],
    requests: list[dict[str, Any]],
) -> dict[str, Any]:
    import memcredit_step0 as s0

    (run_a, worker_a, name_a), (run_b, worker_b, name_b) = (
        (x.split(":") + ["all"])[:3] for x in (a, b)
    )
    pa = load_pass(runs[run_a], worker_a, name_a)
    pb = load_pass(runs[run_b], worker_b, name_b)
    if pa is None or pb is None:
        return {"a": a, "b": b, "missing": True}
    common = sorted(set(pa["rows"]) & set(pb["rows"]))
    sub_a = {"rows": {i: pa["rows"][i] for i in common}}
    sub_b = {"rows": {i: pb["rows"][i] for i in common}}
    result = s0.compare(sub_a, sub_b, {})
    result.pop("clusters", None)
    result.pop("clusters_all_identical", None)
    result.pop("differing_examples", None)
    covered = flips = 0
    pools_flipped: set[tuple[int, str]] = set()
    pools_seen: set[tuple[int, str]] = set()
    for i in common:
        ta, tb = pa["rows"][i]["text"], pb["rows"][i]["text"]
        if ta is None or tb is None:
            continue
        q = requests[i]["question_index"]
        pools_seen.add((q, requests[i]["arm"]))
        la, lb = labels.get((q, ta.strip())), labels.get((q, tb.strip()))
        if not la or not lb or len(la) != 1 or len(lb) != 1:
            continue
        covered += 1
        if la != lb:
            flips += 1
            pools_flipped.add((q, requests[i]["arm"]))
    return {
        "a": a,
        "b": b,
        "gpu_a": gpu_of(runs[run_a], worker_a),
        "gpu_b": gpu_of(runs[run_b], worker_b),
        **result,
        "utility_covered": covered,
        "utility_flips": flips,
        "utility_flip_rate": flips / covered if covered else None,
        "utility_flip_ci95": list(mc.clopper_pearson(flips, covered)) if covered else None,
        "pools": len(pools_seen),
        "pools_with_a_utility_flip": len(pools_flipped),
    }


def aa_report(
    runs: dict[str, Path],
    pairs: list[tuple[str, str]],
    config: dict[str, Any],
    artifact: dict[str, Any],
) -> dict[str, Any]:
    requests = ms.request_table(artifact, config["pools"]["arms"])
    labels = judged_labels(runs)
    conflicting = sum(1 for v in labels.values() if len(v) > 1)
    return {
        "runs": {k: str(v) for k, v in runs.items()},
        "judged_replies": len(labels),
        "judged_replies_with_conflicting_labels": conflicting,
        "pairs": [aa_pair(runs, a, b, labels, requests) for a, b in pairs],
    }


# --------------------------------------------------------------------------- main


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    sub = parser.add_subparsers(dest="command", required=True)
    analyze_p = sub.add_parser("analyze", allow_abbrev=False)
    analyze_p.add_argument("--run-dir", required=True)
    analyze_p.add_argument("--evidence", required=True)
    analyze_p.add_argument("--output-dir", required=True)
    analyze_p.add_argument("--hand-labels", default=None)
    analyze_p.add_argument("--private-dir", default=None)
    sample_p = sub.add_parser("hand-sample", allow_abbrev=False)
    sample_p.add_argument("--run-dir", required=True)
    sample_p.add_argument("--evidence", required=True)
    sample_p.add_argument("--output", required=True)
    aa_p = sub.add_parser("aa", allow_abbrev=False)
    aa_p.add_argument("--run", action="append", required=True, help="name=run_dir")
    aa_p.add_argument("--pair", action="append", required=True, help="run:worker,run:worker")
    aa_p.add_argument("--evidence", required=True)
    aa_p.add_argument("--output", required=True)
    power_p = sub.add_parser("power", allow_abbrev=False)
    power_p.add_argument("--analysis-dir", required=True)
    power_p.add_argument("--output", required=True)
    power_p.add_argument("--heldout", type=int, default=None)
    for sp in sub.choices.values():
        sp.add_argument("--config", default=str(ms.CONFIG_PATH))
    args = parser.parse_args()
    config = ms.load_config(Path(args.config))
    if args.command == "analyze":
        artifact = load_artifact(Path(args.evidence), config)
        hand = None
        if args.hand_labels:
            hand = [
                json.loads(line)
                for line in Path(args.hand_labels).read_text().splitlines()
                if line.strip()
            ]
        result = analyze(
            Path(args.run_dir),
            config,
            artifact,
            Path(args.output_dir),
            hand,
            Path(args.private_dir) if args.private_dir else None,
        )
        print(json.dumps(result["headline"], indent=2, sort_keys=True))
        return 0
    if args.command == "hand-sample":
        artifact = load_artifact(Path(args.evidence), config)
        sample = hand_sample(Path(args.run_dir), config, artifact)
        out = Path(args.output)
        if out.exists():
            raise ms.StudyError(f"refusing to overwrite {out}")
        out.write_text("".join(json.dumps(s, ensure_ascii=False) + "\n" for s in sample))
        print(json.dumps({"items": len(sample)}))
        return 0
    if args.command == "aa":
        artifact = load_artifact(Path(args.evidence), config)
        runs = dict(item.split("=", 1) for item in args.run)
        pairs = [tuple(p.split(",", 1)) for p in args.pair]
        report = aa_report({k: Path(v) for k, v in runs.items()}, pairs, config, artifact)
        Path(args.output).write_bytes(mc.canonical_json(report))
        for row in report["pairs"]:
            print(
                json.dumps(
                    {
                        k: row.get(k)
                        for k in (
                            "a",
                            "b",
                            "n_common",
                            "identical_tokens",
                            "identical_tokens_and_logprob_bits",
                            "utility_covered",
                            "utility_flips",
                        )
                    }
                )
            )
        return 0
    split = json.loads((PROJECT_ROOT / config["split"]["path"]).read_text(encoding="utf-8"))
    heldout = args.heldout or int(split["counts"]["heldout"])
    result = power(Path(args.analysis_dir), config, heldout)
    Path(args.output).write_bytes(mc.canonical_json(result))
    print(json.dumps({k: v for k, v in result.items() if k != "statistics"}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
