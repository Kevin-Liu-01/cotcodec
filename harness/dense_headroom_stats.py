"""Statistics and decision rules of the Q3 dense headroom pre-check (torch-free).

Registered in ``program/preregistrations/q3-dense-headroom-precheck-v1.md``.
Every interval is a 99 percent percentile passage-cluster bootstrap
(B = 10,000, NumPy seed 42, macro over pairs inside each replicate), the
construction K1 v1 registered for its dense gates
(``harness.sparse_indexer_k1_stats.macro_mean_interval``); statistics with a
seed term (the null selectors) use K1 v1's combined seed-plus-cluster interval
(``xi_interval``, ``xi_rel_interval``). No statistic reads an indexer: there is
none. The pre-check is measurement-only; its decisions say which K1 v3 designs
the measured headroom supports, never whether cross-script recall loss exists.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray
from scipy import stats as sstats

from harness import dense_headroom_data as dhd
from harness import sparse_indexer_k1_stats as k1s

BOOTSTRAP_SEED = k1s.BOOTSTRAP_SEED
REPLICATES = k1s.BOOTSTRAP_REPLICATES
TARGETS = ("hs", "mp")
DESCRIPTIVE_TARGETS = ("hs", "mp", "hm")
# Geometric, ratio about sqrt(2), so that for an English ML loss that grows
# smoothly with sigma some scale lands between half of V1's tolerance and V1's
# tolerance (null_verdict's reach rule).
SIGMAS: tuple[float, ...] = (0.25, 0.35, 0.5, 0.7, 1.0, 1.4, 2.0, 2.8, 4.0)
BASE_SELECTORS = ("T:hs", "T:mp", "T:hm", "U", "Uk", "rand", "LEX")
FIXED_SELECTORS = ("T:hs@fixed", "T:mp@fixed", "rand@fixed")

# Registered thresholds (preregistration "Decision rules").
H1_INTERPRET_POINTS = k1s.H1_INTERPRET_POINTS  # 10, inherited from K1 v1
H1_NEGATIVE_POINTS = k1s.H1_NEGATIVE_POINTS  # 20, inherited from K1 v1
H1_NEGATIVE_LOWER_POINTS = 10.0
H2A_ACCURACY_POINTS = k1s.H2A_ACCURACY_POINTS  # 30
H2B_POINTS = k1s.H2B_POINTS  # 5
NULL_XI_POINTS = 2.0
NULL_XI_REL = 0.10
NULL_REACH_POINTS = k1s.V1_TOLERANCE_POINTS / 2  # 2.5: half of V1's 5-point tolerance
LEX_XI_REL = 0.10
FLOOR_G = 0.50
FLOOR_HEADROOM_POINTS = 10.0
CONTROL_SHARE_MIN = 0.30
V1_TOLERANCE_POINTS = k1s.V1_TOLERANCE_POINTS  # 5
MIN_SUBSET_CLUSTERS = 3
FERTILITY_STRONG_RHO = 0.75
SMOKE_452 = {"T:hs": 26.45064085306866, "T:mp": 26.080629028925404,
             "T:hm": 26.2663184737321, "rand": 12.480333709716797,
             "U": 66.54043501870973, "Uk": 9.745942328254959}
SMOKE_452_TOLERANCE_POINTS = 0.5
SMOKE_452_GATED = ("T:hs", "T:mp", "T:hm", "rand")


class DenseStatsError(ValueError):
    """The results do not cover the registered units (an integrity failure, exit 3)."""


def null_names(seeds: Sequence[int]) -> list[str]:
    return [f"N:{target}:{sigma:g}:{seed}" for target in TARGETS for sigma in SIGMAS
            for seed in seeds]


def selector_names(seeds: Sequence[int]) -> list[str]:
    """Registered selector columns, in order."""

    return [*BASE_SELECTORS, *FIXED_SELECTORS, *null_names(seeds)]


# --------------------------------------------------------------------------- #
# Tables
# --------------------------------------------------------------------------- #


@dataclass
class Results:
    """Per-unit outputs keyed by unit id."""

    selectors: list[str]
    units: dict[str, dict[str, Any]]

    def recall(self, unit: str, name: str) -> float:
        row = self.units[unit]["recall"]
        values = row[:, self.selectors.index(name)]
        if not np.isfinite(values).all():
            raise DenseStatsError(f"unit {unit}: non-finite recall for {name}")
        return float(values.mean())

    def per_layer(self, unit: str, name: str) -> NDArray[np.float64]:
        return np.asarray(self.units[unit]["recall"][:, self.selectors.index(name)],
                          dtype=np.float64)

    def correct(self, unit: str) -> float:
        scores = self.units[unit]["mc_scores"]
        answer = int(self.units[unit]["mc_correct"])
        if answer < 0 or not np.isfinite(scores).all():
            raise DenseStatsError(f"unit {unit}: missing multiple-choice scores")
        return 100.0 * float(int(np.argmax(scores)) == answer)


def check_coverage(units: Sequence[dhd.Unit], results: Results, k_token_limits: Mapping[str, int]
                   ) -> dict[str, Any]:
    """Every planned unit exactly once, finite where measured, within its budget."""

    planned = {u.unit_id: u for u in units}
    missing = sorted(set(planned) - set(results.units))
    extra = sorted(set(results.units) - set(planned))
    if missing or extra:
        raise DenseStatsError(f"{len(missing)} planned units missing, {len(extra)} unplanned")
    over = 0
    for unit_id, unit in planned.items():
        row = results.units[unit_id]
        if unit.select:
            if not np.isfinite(row["recall"]).all():
                raise DenseStatsError(f"unit {unit_id}: non-finite recall")
            if int(row["max_selected"]) > k_token_limits[unit_id]:
                over += 1
        if unit.mc and (int(row["mc_correct"]) < 0 or not np.isfinite(row["mc_scores"]).all()):
            raise DenseStatsError(f"unit {unit_id}: missing multiple-choice scores")
    if over:
        raise DenseStatsError(f"{over} unit(s) selected more than the budget allows")
    return {"units": len(planned), "selection_units": sum(u.select for u in units),
            "mc_units": sum(u.mc for u in units), "within_budget": True}


@dataclass(frozen=True)
class Group:
    """Prompts of one role and condition, labelled by pair and passage cluster."""

    prompts: list[Mapping[str, Any]]
    pair: NDArray[np.int64]
    cluster: NDArray[np.int64]
    pair_names: list[str]

    @classmethod
    def of(cls, prompts: Sequence[Mapping[str, Any]]) -> Group:
        pair_names = sorted({p["pair"] for p in prompts})
        clusters = sorted({p["cluster"] for p in prompts})
        return cls(list(prompts), np.asarray([pair_names.index(p["pair"]) for p in prompts],
                                             dtype=np.int64),
                   np.asarray([clusters.index(p["cluster"]) for p in prompts], dtype=np.int64),
                   pair_names)

    @property
    def n_clusters(self) -> int:
        return len({p["cluster"] for p in self.prompts})


def _interval(values: Sequence[float], group: Group, replicates: int) -> dict[str, Any]:
    if not group.prompts:
        return {"evaluable": False, "reason": "no prompts"}
    if group.n_clusters < MIN_SUBSET_CLUSTERS:
        return {"evaluable": False, "reason": f"{group.n_clusters} passage clusters",
                "point": float(np.mean(values))}
    return k1s.macro_mean_interval(np.asarray(values, dtype=np.float64), group.pair,
                                   group.cluster, replicates, BOOTSTRAP_SEED).as_dict()


def prompts_where(prompts: Sequence[Mapping[str, Any]], *, role: str,
                  condition: str | None = None, questions: set[str] | None = None
                  ) -> list[Mapping[str, Any]]:
    out = []
    for p in prompts:
        if p["role"] != role or (condition is not None and p["condition"] != condition):
            continue
        if questions is not None and f"{p['cluster']}|{p['question_number']}" not in questions:
            continue
        out.append(p)
    return out


def families(prompts: Sequence[Mapping[str, Any]], questions: set[str] | None = None
             ) -> list[tuple[Mapping[str, Any], Mapping[str, Any]]]:
    """(MN, CX) prompt pairs of the ``dev`` role, ordered by family id."""

    grouped: dict[str, dict[str, Mapping[str, Any]]] = {}
    for p in prompts_where(prompts, role="dev", questions=questions):
        grouped.setdefault(p["family_id"], {})[p["condition"]] = p
    out = []
    for family_id in sorted(grouped):
        members = grouped[family_id]
        if set(members) != {"MN", "CX"}:
            raise DenseStatsError(f"family {family_id} is incomplete")
        out.append((members["MN"], members["CX"]))
    return out


def family_table(fams: Sequence[tuple[Mapping[str, Any], Mapping[str, Any]]], results: Results,
                 indexer_names: Sequence[str], target: str) -> k1s.FamilyTable:
    """K1 v1's family table with a dense reference selector in the indexer slot."""

    pair_names = sorted({mn["pair"] for mn, _ in fams})
    clusters = sorted({mn["cluster"] for mn, _ in fams})

    def recall(prompt: Mapping[str, Any], name: str) -> float:
        return results.recall(dhd.unit_of(prompt), name)

    return k1s.FamilyTable(
        pair=np.asarray([pair_names.index(mn["pair"]) for mn, _ in fams]),
        cluster=np.asarray([clusters.index(mn["cluster"]) for mn, _ in fams]),
        ind_mn=np.asarray([[recall(mn, n) for mn, _ in fams] for n in indexer_names]),
        ind_cx=np.asarray([[recall(cx, n) for _, cx in fams] for n in indexer_names]),
        tgt_mn=np.asarray([recall(mn, f"T:{target}") for mn, _ in fams]),
        tgt_cx=np.asarray([recall(cx, f"T:{target}") for _, cx in fams]),
        rand_mn=np.asarray([recall(mn, "rand") for mn, _ in fams]),
        rand_cx=np.asarray([recall(cx, "rand") for _, cx in fams]))


# --------------------------------------------------------------------------- #
# Headroom (H1) and answering headroom (H2)
# --------------------------------------------------------------------------- #


def headroom_block(prompts: Sequence[Mapping[str, Any]], results: Results, replicates: int,
                   questions: set[str] | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {}
    groups = {"MN": prompts_where(prompts, role="dev", condition="MN", questions=questions),
              "CX": prompts_where(prompts, role="dev", condition="CX", questions=questions),
              "ML": prompts_where(prompts, role=dhd.LITERAL_ROLE, questions=questions)}
    for condition, members in groups.items():
        group = Group.of(members)
        block: dict[str, Any] = {"prompts": len(members), "clusters": group.n_clusters}
        for target in DESCRIPTIVE_TARGETS:
            values = [results.recall(dhd.unit_of(p), f"T:{target}")
                      - results.recall(dhd.unit_of(p), "rand") for p in members]
            block[target] = _interval(values, group, replicates) if members else {
                "evaluable": False, "reason": "no prompts"}
        block["mean_recall"] = {name: (float(np.mean([results.recall(dhd.unit_of(p), name)
                                                      for p in members])) if members else None)
                                for name in BASE_SELECTORS}
        out[condition] = block
    fams = families(prompts, questions)
    if fams:
        group = Group.of([mn for mn, _ in fams])
        out["delta_mn_cx"] = {
            target: _interval([results.recall(dhd.unit_of(mn), f"T:{target}")
                               - results.recall(dhd.unit_of(cx), f"T:{target}")
                               for mn, cx in fams], group, replicates) for target in TARGETS}
    points = {t: out["CX"][t].get("point", float("nan")) for t in TARGETS}
    finite = {t: v for t, v in points.items() if v is not None and math.isfinite(v)}
    if finite:
        best = max(sorted(finite), key=lambda t: finite[t])
        out["h1_cx_points"] = finite[best]
        out["h1_cx_target"] = best
        out["h1_cx_lower"] = out["CX"][best].get("lower")
    return out


def answering_block(prompts: Sequence[Mapping[str, Any]], results: Results, replicates: int,
                    questions: set[str] | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for condition in ("CX", "MN"):
        members = prompts_where(prompts, role="dev", condition=condition, questions=questions)
        out[f"accuracy_{condition}"] = _interval(
            [results.correct(dhd.unit_of(p)) for p in members], Group.of(members), replicates)
    out["h2a"] = out["accuracy_CX"]
    present = {p["family_id"]: p for p in prompts_where(prompts, role="dev", condition="CX",
                                                        questions=questions)}
    absent = prompts_where(prompts, role="dev-absent", questions=questions)
    diffs, clusters = [], []
    for p in absent:
        twin = present.get(p["family_id"])
        if twin is None:
            if questions is None:
                raise DenseStatsError(f"needle-absent cell {p['prompt_id']} has no twin")
            continue
        diffs.append(results.correct(dhd.unit_of(twin)) - results.correct(dhd.unit_of(p)))
        clusters.append(p["cluster"])
    names = sorted(set(clusters))
    if len(names) >= MIN_SUBSET_CLUSTERS:
        out["h2b"] = k1s.macro_mean_interval(
            np.asarray(diffs, dtype=np.float64), np.zeros(len(diffs), dtype=np.int64),
            np.asarray([names.index(c) for c in clusters]), replicates,
            BOOTSTRAP_SEED).as_dict()
    else:
        out["h2b"] = {"evaluable": False, "reason": f"{len(names)} passage clusters"}
    out["absent_accuracy"] = (float(np.mean([results.correct(dhd.unit_of(p)) for p in absent]))
                              if absent else None)
    nohay = prompts_where(prompts, role="dev-nohaystack", questions=questions)
    out["nohaystack_accuracy"] = (float(np.mean([results.correct(dhd.unit_of(p))
                                                 for p in nohay])) if nohay else None)
    return out


def h2_status(answering: Mapping[str, Any]) -> str:
    """PASS: K1 v1's registered H2a and H2b rules hold on the development read.
    POINT_ONLY: both points meet the thresholds but a bound does not (the
    development read has about 19 passage clusters). FAIL: otherwise."""

    h2a, h2b = answering["h2a"], answering["h2b"]
    if not (h2a.get("evaluable") and h2b.get("evaluable")):
        return "FAIL"
    if (h2a["lower"] > H2A_ACCURACY_POINTS and h2b["lower"] > 0.0
            and h2b["point"] >= H2B_POINTS):
        return "PASS"
    if h2a["point"] > H2A_ACCURACY_POINTS and h2b["point"] >= H2B_POINTS:
        return "POINT_ONLY"
    return "FAIL"


def k1_v1_prestep(headroom: Mapping[str, Any], answering: Mapping[str, Any]) -> dict[str, Any]:
    """K1 v1's registered development pre-step rule, applied unchanged (continuity)."""

    h1 = headroom.get("h1_cx_points", float("nan"))
    h2a, h2b = answering["h2a"], answering["h2b"]
    proceed = (math.isfinite(h1) and h1 >= H1_INTERPRET_POINTS and bool(h2a.get("evaluable"))
               and bool(h2b.get("evaluable")) and h2a["lower"] > H2A_ACCURACY_POINTS
               and h2b["lower"] > 0.0 and h2b["point"] >= H2B_POINTS)
    return {"decision": "PROCEED_TO_K1" if proceed else "ESCALATE_OR_STOP",
            "h1_negative_ready": bool(math.isfinite(h1) and h1 >= H1_NEGATIVE_POINTS)}


# --------------------------------------------------------------------------- #
# Ratio retention G (floor) and the reference selectors
# --------------------------------------------------------------------------- #


def _cluster_weights(n_clusters: int, replicates: int, seed: int) -> NDArray[np.float64]:
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, n_clusters, size=(replicates, n_clusters))
    weights = np.zeros((replicates, n_clusters))
    np.add.at(weights, (np.repeat(np.arange(replicates), n_clusters), draws.ravel()), 1.0)
    return weights


def retention_interval(ind: Sequence[float], tgt: Sequence[float], rnd: Sequence[float],
                       group: Group, replicates: int) -> dict[str, Any]:
    """Macro over pairs of ``G = (R_X - R_rand) / (R_T - R_rand)`` on pair means.

    Not evaluable when a pair's point target headroom is 1 point or less (K1
    v1's rule for xi_rel); replicates floor the denominator at 1 point.
    """

    if group.n_clusters < MIN_SUBSET_CLUSTERS:
        return {"evaluable": False, "reason": f"{group.n_clusters} passage clusters"}
    ind, tgt, rnd = (np.asarray(v, dtype=np.float64) for v in (ind, tgt, rnd))
    n_pairs = len(group.pair_names)
    n_clusters = int(group.cluster.max()) + 1
    sums = {name: np.zeros((n_clusters, n_pairs)) for name in ("ind", "tgt", "rnd", "n")}
    for name, values in (("ind", ind), ("tgt", tgt), ("rnd", rnd),
                         ("n", np.ones_like(ind))):
        np.add.at(sums[name], (group.cluster, group.pair), values)

    def g_of(weights: NDArray[np.float64] | None, clip: bool) -> NDArray[np.float64]:
        if weights is None:
            means = {k: v.sum(axis=0) / sums["n"].sum(axis=0) for k, v in sums.items()
                     if k != "n"}
        else:
            with np.errstate(invalid="ignore", divide="ignore"):
                means = {k: (weights @ v) / (weights @ sums["n"]) for k, v in sums.items()
                         if k != "n"}
        headroom = means["tgt"] - means["rnd"]
        with np.errstate(invalid="ignore", divide="ignore"):
            if clip:
                g = (means["ind"] - means["rnd"]) / np.maximum(headroom, 1.0)
            else:
                g = np.where(headroom > 1.0, (means["ind"] - means["rnd"]) / headroom, np.nan)
        return g

    point_pairs = g_of(None, clip=False)
    if np.isnan(point_pairs).any():
        return {"evaluable": False, "reason": "a pair has 1 point of target headroom or less",
                "pairs": dict(zip(group.pair_names, point_pairs.tolist(), strict=True))}
    point = float(point_pairs.mean())
    boot = g_of(_cluster_weights(n_clusters, replicates, BOOTSTRAP_SEED), clip=True)
    with np.errstate(invalid="ignore"):
        boot = np.nanmean(boot, axis=-1)
    lower, upper = (float(v) for v in np.percentile(boot, [0.5, 99.5]))
    return {"evaluable": True, "point": point, "lower": lower, "upper": upper,
            "se_cluster": float(np.std(boot, ddof=1)), "replicates": int(replicates),
            "pairs": dict(zip(group.pair_names, point_pairs.tolist(), strict=True))}


def retention_of(prompts: Sequence[Mapping[str, Any]], results: Results, names: Sequence[str],
                 target: str, replicates: int) -> dict[str, Any]:
    """G of the (seed-mean of the) ``names`` selectors relative to target ``target``."""

    group = Group.of(prompts)
    if not prompts:
        return {"evaluable": False, "reason": "no prompts"}
    ind = [float(np.mean([results.recall(dhd.unit_of(p), n) for n in names])) for p in prompts]
    tgt = [results.recall(dhd.unit_of(p), f"T:{target}") for p in prompts]
    rnd = [results.recall(dhd.unit_of(p), "rand") for p in prompts]
    return retention_interval(ind, tgt, rnd, group, replicates)


def literal_selector_block(prompts: Sequence[Mapping[str, Any]], results: Results,
                           replicates: int, subsets: Mapping[str, set[str] | None]
                           ) -> dict[str, Any]:
    """The literal (lexical) selector against each target: xi and xi_rel on the
    MN/CX families, i.e. what a selector that matches only shared tokens would
    read under K1's statistics with no cross-lingual matching error at all."""

    out: dict[str, Any] = {}
    for subset, questions in subsets.items():
        fams = families(prompts, questions)
        block: dict[str, Any] = {"families": len(fams)}
        clusters = len({mn["cluster"] for mn, _ in fams})
        for target in TARGETS:
            if clusters < MIN_SUBSET_CLUSTERS:
                block[target] = {"evaluable": False, "reason": f"{clusters} passage clusters"}
                continue
            table = family_table(fams, results, ["LEX"], target)
            block[target] = {"xi": k1s.xi_interval(table, replicates).as_dict(),
                             "xi_rel": k1s.xi_rel_interval(table, replicates).as_dict()}
        out[subset] = block
    return out


# --------------------------------------------------------------------------- #
# Block-score null (target plus language-agnostic noise)
# --------------------------------------------------------------------------- #


def null_block(prompts: Sequence[Mapping[str, Any]], results: Results, seeds: Sequence[int],
               replicates: int, controlled: set[str] | None) -> dict[str, Any]:
    """For each target and noise scale: xi and xi_rel of a selector equal to the
    target's log block scores plus N(0, sigma^2) noise, identical in law on the
    MN and CX legs (the identification refuter's null, on the measured score
    shapes), its English ML adequacy against K1 v1's V1 rule, and its G(MN)."""

    fams = families(prompts)
    en_ml = [p for p in prompts_where(prompts, role=dhd.LITERAL_ROLE) if p["pair"] == "en>en"]
    mn_controlled = prompts_where(prompts, role="dev", condition="MN", questions=controlled)
    out: dict[str, Any] = {}
    for target in TARGETS:
        per_sigma: dict[str, Any] = {}
        for sigma in SIGMAS:
            names = [f"N:{target}:{sigma:g}:{seed}" for seed in seeds]
            table = family_table(fams, results, names, target)
            xi = k1s.xi_interval(table, replicates).as_dict()
            xi_rel = k1s.xi_rel_interval(table, replicates).as_dict()
            target_ml = float(np.mean([results.recall(dhd.unit_of(p), f"T:{target}")
                                       for p in en_ml])) if en_ml else float("nan")
            ml_by_seed = [float(np.mean([results.recall(dhd.unit_of(p), n) for p in en_ml]))
                          if en_ml else float("nan") for n in names]
            v1_pass = bool(en_ml) and all(v >= target_ml - V1_TOLERANCE_POINTS
                                          for v in ml_by_seed)
            loss_by_seed = [target_ml - v for v in ml_by_seed]
            per_sigma[f"{sigma:g}"] = {
                "xi": xi, "xi_rel": xi_rel,
                "english_ml": {"target": target_ml, "null_by_seed": ml_by_seed,
                               "loss_by_seed": loss_by_seed,
                               "loss_seed_mean": (float(np.mean(loss_by_seed)) if en_ml
                                                  else float("nan")),
                               "v1_pass": v1_pass},
                "g_mn_controlled": retention_of(mn_controlled, results, names, target,
                                                replicates),
            }
        out[target] = {"sigmas": per_sigma, "verdict": null_verdict(per_sigma)}
    return out


def reaching_sigmas(per_sigma: Mapping[str, Any]) -> list[str]:
    """The reach rule (decision 8): noise scales whose null passes V1 at every
    seed and whose seed-mean English ML loss is at least 2.5 points, half of
    V1's tolerance, i.e. realistically imperfect V1-adequate copies of the
    target rather than near-exact ones. Shared by ``null_verdict`` and the floor
    candidate's condition (c) (``floor_block``, decision 10 as amended in D32)."""

    reaching = []
    for sigma, block in per_sigma.items():
        english = block["english_ml"]
        loss = english.get("loss_seed_mean")
        if (english["v1_pass"] and loss is not None and math.isfinite(loss)
                and loss >= NULL_REACH_POINTS):
            reaching.append(sigma)
    return reaching


def null_verdict(per_sigma: Mapping[str, Any]) -> dict[str, Any]:
    """CENTRED: at every noise scale whose null passes V1 at every seed, |xi| <= 2
    points and |xi_rel| <= 0.10 (seed-mean points), and at least one of those
    scales reaches toward the V1 boundary: its seed-mean English ML loss is at
    least 2.5 points, half of V1's tolerance (otherwise only near-exact copies
    of the target were tested and centring would be vacuous). NOT_CENTRED: a
    V1-adequate scale breaks either limit. NOT_EVALUABLE: no scale passes V1,
    xi_rel is not evaluable at one that does, or every V1-adequate scale is
    within the limits but none reaches 2.5 points."""

    adequate = [s for s, block in per_sigma.items() if block["english_ml"]["v1_pass"]]
    losses = {s: block["english_ml"].get("loss_seed_mean") for s, block in per_sigma.items()}
    if not adequate:
        return {"verdict": "NOT_EVALUABLE", "reason": "no noise scale passes V1",
                "adequate_sigmas": [], "english_ml_loss": losses}
    worst_xi, worst_rel = 0.0, 0.0
    for sigma in adequate:
        xi = per_sigma[sigma]["xi"]["point"]
        rel = per_sigma[sigma]["xi_rel"]
        if not (rel.get("evaluable") and math.isfinite(rel["point"])):
            return {"verdict": "NOT_EVALUABLE", "reason": f"xi_rel not evaluable at {sigma}",
                    "adequate_sigmas": adequate, "english_ml_loss": losses}
        worst_xi = max(worst_xi, abs(float(xi)))
        worst_rel = max(worst_rel, abs(float(rel["point"])))
    reaching = reaching_sigmas(per_sigma)
    read = {"adequate_sigmas": adequate, "reaching_sigmas": reaching,
            "english_ml_loss": losses, "max_abs_xi": worst_xi, "max_abs_xi_rel": worst_rel}
    if worst_xi > NULL_XI_POINTS or worst_rel > NULL_XI_REL:
        return {"verdict": "NOT_CENTRED", **read}
    if not reaching:
        return {"verdict": "NOT_EVALUABLE",
                "reason": (f"no V1-adequate noise scale loses at least {NULL_REACH_POINTS:g} "
                           "points of English ML recall"), **read}
    return {"verdict": "CENTRED", **read}


# --------------------------------------------------------------------------- #
# Entity anchors, the floor candidate and fertility
# --------------------------------------------------------------------------- #


def wilson(successes: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = successes / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (centre - half, centre + half)


def question_sets(features: Mapping[str, Any]) -> dict[str, set[str]]:
    flags = features["questions"]
    return {"anchored": {q for q, f in flags.items() if f["anchored"]},
            "controlled": {q for q, f in flags.items() if not f["anchored"]}}


def overlap_block(prompts: Sequence[Mapping[str, Any]], features: Mapping[str, Any]
                  ) -> dict[str, Any]:
    """Share of a query's content tokens found in the needle, by pair and condition."""

    overlap = features["prompt_overlap"]
    table: dict[str, dict[str, list[float]]] = {}
    for p in prompts:
        if p["prompt_id"] not in overlap:
            continue
        table.setdefault(p["pair"], {}).setdefault(p["condition"], []).append(
            float(overlap[p["prompt_id"]]["share"]))
    by_pair = {pair: {c: float(np.mean(v)) for c, v in conds.items()}
               for pair, conds in sorted(table.items())}
    diffs = [v["MN"] - v["CX"] for v in by_pair.values() if "MN" in v and "CX" in v]
    return {"by_pair": by_pair,
            "macro_mn_minus_cx": float(np.mean(diffs)) if diffs else None}


def entity_block(prompts: Sequence[Mapping[str, Any]], results: Results,
                 features: Mapping[str, Any], replicates: int) -> dict[str, Any]:
    sets = question_sets(features)
    n = len(features["questions"])
    anchored = len(sets["anchored"])
    out: dict[str, Any] = {
        "questions": n, "anchored": anchored,
        "anchored_share": anchored / n if n else float("nan"),
        "anchored_share_wilson95": wilson(anchored, n),
        "controlled_share": (n - anchored) / n if n else float("nan"),
        "overlap": overlap_block(prompts, features),
        "anchors": {q: f["anchors"] for q, f in sorted(features["questions"].items())},
    }
    for name in ("controlled", "anchored"):
        out[name] = {"headroom": headroom_block(prompts, results, replicates, sets[name]),
                     "answering": answering_block(prompts, results, replicates, sets[name])}
    out["literal_selector"] = literal_selector_block(
        prompts, results, replicates,
        {"all": None, "controlled": sets["controlled"], "anchored": sets["anchored"]})
    return out


def entity_flags(entity: Mapping[str, Any]) -> dict[str, Any]:
    """lexical_confound PRESENT: the literal selector alone reads xi_rel >= 0.10
    (for either target, all families), the NEGATIVE limit of K1 v1. The literal
    selector matches every shared token, so this is a lexical-overlap confound
    (entity anchors are one source of it, paraphrase overlap another); it is not
    attributed to entities. entity_control SUFFICIENT: at least 30 percent of
    questions are unanchored and on them the literal selector's xi_rel is below
    0.10 for both targets, i.e. removing the anchored questions removes the
    lexical confound in K1's units. Neither flag ever removes a requirement of a
    K1 v3 (``combined_recommendation``)."""

    lexical = entity["literal_selector"]

    def rel(subset: str, target: str) -> float | None:
        block = lexical[subset].get(target, {})
        value = block.get("xi_rel", {}) if isinstance(block, Mapping) else {}
        if not value.get("evaluable"):
            return None
        return float(value["point"])

    all_rel = [rel("all", t) for t in TARGETS]
    if any(v is None for v in all_rel):
        confound = "NOT_EVALUABLE"
    else:
        confound = "PRESENT" if max(all_rel) >= LEX_XI_REL else "ABSENT"
    ctrl_rel = [rel("controlled", t) for t in TARGETS]
    if any(v is None for v in ctrl_rel):
        control = "NOT_EVALUABLE"
    elif entity["controlled_share"] >= CONTROL_SHARE_MIN and max(ctrl_rel) < LEX_XI_REL:
        control = "SUFFICIENT"
    else:
        control = "INSUFFICIENT"
    return {"lexical_confound": confound, "entity_control": control,
            "literal_xi_rel_all": all_rel, "literal_xi_rel_controlled": ctrl_rel}


def floor_block(prompts: Sequence[Mapping[str, Any]], results: Results,
                features: Mapping[str, Any], null: Mapping[str, Any], target: str,
                replicates: int) -> dict[str, Any]:
    """The candidate non-literal adequacy floor for K1 v3: an indexer's 99
    percent lower bound of G(MN) on entity-controlled MN families at least 0.5.

    VIABLE when (a) the target's controlled-MN headroom is at least 10 points,
    (b) the literal selector's controlled G(MN) point is below 0.5 (a
    literal-only selector fails the floor, with its point and not only its
    lower bound below it) and (c) some noise scale that meets decision 8's
    reach rule (``reaching_sigmas``: its null passes V1 and its seed-mean
    English ML loss is at least 2.5 points) has a controlled G(MN) whose 99
    percent lower bound is at least 0.5: a realistically imperfect, V1-adequate
    noisy copy of the target passes the floor exactly as an indexer would be
    judged, not only the near-exact copy at the smallest scale (decision 10 as
    amended in D32). Points and bounds of every reference are reported.
    """

    controlled = question_sets(features)["controlled"]
    members = prompts_where(prompts, role="dev", condition="MN", questions=controlled)
    every = prompts_where(prompts, role="dev", condition="MN")
    references = {name: {"controlled": retention_of(members, results, [name], target,
                                                    replicates),
                         "all": retention_of(every, results, [name], target, replicates)}
                  for name in ("LEX", "Uk", "U", "T:hm")}
    headroom = headroom_block(prompts, results, replicates, controlled)["MN"].get(target, {})
    reasons = []
    if not headroom.get("evaluable"):
        return {"candidate_g": FLOOR_G, "target": target, "verdict": "NOT_EVALUABLE",
                "reasons": ["controlled MN headroom not evaluable"], "references": references}
    if headroom["point"] < FLOOR_HEADROOM_POINTS:
        reasons.append("controlled MN headroom below 10 points")
    lex = references["LEX"]["controlled"]
    if not lex.get("evaluable"):
        reasons.append("literal selector G not evaluable")
    elif lex["point"] >= FLOOR_G:
        reasons.append("the literal selector passes the floor")
    sigmas = null[target]["sigmas"]
    reaching = reaching_sigmas(sigmas)
    adequate_pass = [s for s in reaching if sigmas[s]["g_mn_controlled"].get("evaluable")
                     and sigmas[s]["g_mn_controlled"]["lower"] >= FLOOR_G]
    if not adequate_pass:
        reasons.append(f"no V1-adequate null that loses at least {NULL_REACH_POINTS:g} points "
                       "of English ML recall has a 99 percent lower bound of G(MN) of at "
                       "least 0.5")
    nulls = {s: {key: block["g_mn_controlled"].get(key)
                 for key in ("evaluable", "point", "lower", "upper")}
             | {"v1_pass": block["english_ml"]["v1_pass"],
                "english_ml_loss": block["english_ml"].get("loss_seed_mean")}
             for s, block in sigmas.items()}
    return {"candidate_g": FLOOR_G, "target": target,
            "controlled_mn_headroom": headroom, "references": references,
            "null_g_mn_controlled": nulls,
            "reaching_sigmas": reaching,
            "adequate_nulls_passing": adequate_pass,
            "verdict": "VIABLE" if not reasons else "NOT_VIABLE", "reasons": reasons}


def _spearman(x: Sequence[float], y: Sequence[float]) -> float | None:
    if len(x) < 3 or len(set(x)) < 2 or len(set(y)) < 2:
        return None
    return float(sstats.spearmanr(x, y).statistic)


def fertility_block(prompts: Sequence[Mapping[str, Any]], results: Results,
                    artifact: Mapping[str, Any], target: str, replicates: int
                    ) -> dict[str, Any]:
    """Recall headroom by tokenizer fertility (descriptive).

    Fertility of language L on a question = tokens of the L passage (or
    question) / tokens of the parallel English one, in the base's tokenizer.
    Language-level fertility is collinear with script and with being held out
    of indexer training in K1; with seven held-out scripts the association is
    descriptive and cannot separate them (a K1 v3 needs a seen-script leg).
    """

    counts = artifact["features"]["token_counts"]
    languages = sorted({p["needle_language"] for p in prompts if p["role"] == "dev"})
    per_language: dict[str, Any] = {}
    needle_fert: dict[str, float] = {}
    query_fert: dict[str, float] = {}
    for language in languages:
        ratios_p, ratios_q, passage = [], [], []
        for key, n in counts["passage"].items():
            lang, link, qnum = key.split("|")
            if lang != language:
                continue
            passage.append(n)
            ratios_p.append(n / counts["passage"][f"en|{link}|{qnum}"])
            q = counts["question"].get(f"{language}|{link}|{qnum}")
            q_en = counts["question"].get(f"en|{link}|{qnum}")
            if q and q_en:
                ratios_q.append(q / q_en)
        needle_fert[language] = float(np.mean(ratios_p))
        query_fert[language] = float(np.mean(ratios_q)) if ratios_q else float("nan")
        over = 0
        needles = [c for c in artifact["contexts"] if c["kind"] == "needle"
                   and c["needle_language"] == language]
        for c in needles:
            k_tokens = dhd.budget_blocks(c["length"]) * dhd.BLOCK_SIZE
            over += int(c["needle_end"] - c["needle_start"] > k_tokens)
        per_language[language] = {"passage_tokens_mean": float(np.mean(passage)),
                                  "passage_fertility_vs_en": needle_fert[language],
                                  "question_fertility_vs_en": query_fert[language],
                                  "needles_over_budget_share": over / len(needles)
                                  if needles else None}
    headroom_by_pair: dict[str, dict[str, float]] = {}
    for condition in ("MN", "CX"):
        for p in prompts_where(prompts, role="dev", condition=condition):
            value = (results.recall(dhd.unit_of(p), f"T:{target}")
                     - results.recall(dhd.unit_of(p), "rand"))
            headroom_by_pair.setdefault(p["pair"], {}).setdefault(condition, []).append(value)
    by_pair = {pair: {c: float(np.mean(v)) for c, v in conds.items()}
               for pair, conds in sorted(headroom_by_pair.items())}
    held = [x for x in languages if x != "en"]
    x_needle = [f"{x}>en" for x in held if f"{x}>en" in by_pair]
    en_needle = [f"en>{x}" for x in held if f"en>{x}" in by_pair]
    rho_needle_cx = _spearman([needle_fert[p.split(">")[0]] for p in x_needle],
                              [by_pair[p]["CX"] for p in x_needle])
    rho_needle_mn = _spearman([needle_fert[p.split(">")[0]] for p in x_needle],
                              [by_pair[p]["MN"] for p in x_needle])
    rho_query_cx = _spearman([query_fert[p.split(">")[1]] for p in en_needle],
                             [by_pair[p]["CX"] for p in en_needle])
    association = ("STRONG" if rho_needle_cx is not None
                   and abs(rho_needle_cx) >= FERTILITY_STRONG_RHO else "WEAK")
    return {"target": target, "per_language": per_language, "headroom_by_pair": by_pair,
            "spearman": {"needle_fertility_vs_cx_headroom_x_needle": rho_needle_cx,
                         "needle_fertility_vs_mn_headroom_x_needle": rho_needle_mn,
                         "query_fertility_vs_cx_headroom_en_needle": rho_query_cx},
            "association": association,
            "seen_script_condition": "not in the K1 bundle's development partition (its "
                                     "development prompts cover only the seven held-out "
                                     "scripts); a K1 v3 must build it"}


# --------------------------------------------------------------------------- #
# Descriptive tables, the K1 smoke reproduction, classification
# --------------------------------------------------------------------------- #


def descriptive_block(prompts: Sequence[Mapping[str, Any]], results: Results,
                      artifact: Mapping[str, Any]) -> dict[str, Any]:
    by_pair: dict[str, dict[str, Any]] = {}
    per_layer: dict[str, dict[str, list[float]]] = {}
    by_depth: dict[str, dict[str, list[float]]] = {}
    contexts = artifact["contexts"]
    shown = [*BASE_SELECTORS, *FIXED_SELECTORS]
    for p in prompts:
        if p["role"] not in ("dev", dhd.LITERAL_ROLE):
            continue
        unit = dhd.unit_of(p)
        key = f"{p['pair']}|{p['condition']}"
        bucket = by_pair.setdefault(key, {"n": 0, "sum": np.zeros(len(shown))})
        bucket["n"] += 1
        bucket["sum"] += np.asarray([results.recall(unit, n) for n in shown])
        layer_bucket = per_layer.setdefault(p["condition"], {})
        for name in ("T:hs", "T:mp", "rand", "LEX", "U"):
            layer_bucket.setdefault(name, []).append(results.per_layer(unit, name))
        depth = contexts[p["context_index"]]["depth"]
        by_depth.setdefault(f"{p['condition']}|depth={depth:g}", {}).setdefault(
            "T:hs-rand", []).append(results.recall(unit, "T:hs") - results.recall(unit, "rand"))
    ties = {name: int(sum(int(row["ties"][i]) for row in results.units.values()))
            for i, name in enumerate(results.selectors)}
    return {
        "by_pair_condition": {k: {"n": v["n"], "mean_recall": dict(zip(
            shown, (v["sum"] / v["n"]).tolist(), strict=True))}
            for k, v in sorted(by_pair.items())},
        "per_layer": {c: {n: np.mean(np.stack(v), axis=0).tolist() for n, v in layers.items()}
                      for c, layers in sorted(per_layer.items())},
        "by_depth": {k: {n: float(np.mean(v)) for n, v in d.items()}
                     for k, d in sorted(by_depth.items())},
        "tie_counts": ties,
        "k_blocks": sorted({int(row["k_blocks"]) for row in results.units.values()
                            if int(row["k_blocks"]) > 0}),
    }


def smoke_452_reproduction(artifact: Mapping[str, Any], results: Results) -> dict[str, Any]:
    """K1 v1 smoke 452's dense recall on its 20 development units, recomputed.

    Registered for the Qwen3-0.6B-Base lane only (same tokens, same capture
    path, the K1 v2 bank's selection code): each gated selector within 0.5
    points of the smoke's receipt, or the lane read is INVALID.
    """

    wanted = set(artifact["source"]["k1_smoke_units"])
    units = sorted({dhd.unit_of(p) for p in artifact["prompts"]
                    if p.get("source_unit") in wanted})
    if len(units) != len(wanted):
        return {"status": "NOT_REPRODUCED", "reason": "smoke units missing", "units": len(units)}
    means = {name: float(np.mean([results.recall(u, name) for u in units]))
             for name in SMOKE_452}
    gaps = {name: means[name] - SMOKE_452[name] for name in SMOKE_452}
    ok = all(abs(gaps[n]) <= SMOKE_452_TOLERANCE_POINTS for n in SMOKE_452_GATED)
    return {"status": "REPRODUCED" if ok else "NOT_REPRODUCED", "units": len(units),
            "recomputed": means, "smoke_452": SMOKE_452, "gaps": gaps,
            "tolerance_points": SMOKE_452_TOLERANCE_POINTS, "gated": list(SMOKE_452_GATED)}


def classify_lane(headroom: Mapping[str, Any], answering: Mapping[str, Any],
                  reproduction: Mapping[str, Any] | None) -> dict[str, Any]:
    """NEGATIVE_CAPABLE: H1_CX at least 20 with its 99 percent lower bound at
    least 10, and H2 not FAIL. GO_ONLY_CAPABLE: H1_CX at least 10 and H2 not
    FAIL. NOT_VIABLE: otherwise. INVALID: the K1 smoke reproduction failed."""

    status = h2_status(answering)
    h1 = headroom.get("h1_cx_points", float("nan"))
    lower = headroom.get("h1_cx_lower")
    if reproduction is not None and reproduction["status"] != "REPRODUCED":
        verdict = "INVALID"
    elif (math.isfinite(h1) and h1 >= H1_NEGATIVE_POINTS and lower is not None
          and lower >= H1_NEGATIVE_LOWER_POINTS and status != "FAIL"):
        verdict = "NEGATIVE_CAPABLE"
    elif math.isfinite(h1) and h1 >= H1_INTERPRET_POINTS and status != "FAIL":
        verdict = "GO_ONLY_CAPABLE"
    else:
        verdict = "NOT_VIABLE"
    return {"lane_class": verdict, "h2_status": status, "h1_cx_points": h1,
            "h1_cx_lower": lower, "h1_cx_target": headroom.get("h1_cx_target")}


def analyse(artifact: Mapping[str, Any], results: Results, *, seeds: Sequence[int],
            replicates: int = REPLICATES, reproduce_smoke: bool = False) -> dict[str, Any]:
    """The lane read: every registered statistic and the lane's decisions."""

    prompts = artifact["prompts"]
    features = artifact["features"]
    headroom = headroom_block(prompts, results, replicates)
    answering = answering_block(prompts, results, replicates)
    target = headroom.get("h1_cx_target", "hs")
    controlled = question_sets(features)["controlled"]
    entity = entity_block(prompts, results, features, replicates)
    null = null_block(prompts, results, seeds, replicates, controlled)
    floor = floor_block(prompts, results, features, null, target, replicates)
    fertility = fertility_block(prompts, results, artifact, target, replicates)
    reproduction = smoke_452_reproduction(artifact, results) if reproduce_smoke else None
    classification = classify_lane(headroom, answering, reproduction)
    flags = entity_flags(entity)
    return {
        "headroom": headroom,
        "answering": answering,
        "k1_v1_prestep": k1_v1_prestep(headroom, answering),
        "entity": entity,
        "null": null,
        "floor": floor,
        "fertility": fertility,
        "descriptive": descriptive_block(prompts, results, artifact),
        "smoke_452_reproduction": reproduction,
        "decisions": {
            **classification,
            **flags,
            "null_calibration": {t: null[t]["verdict"]["verdict"] for t in TARGETS},
            "floor_candidate": floor["verdict"],
            "fertility_association": fertility["association"],
        },
        "replicates": replicates,
        "bootstrap_seed": BOOTSTRAP_SEED,
    }


# --------------------------------------------------------------------------- #
# Combined read of the two lanes
# --------------------------------------------------------------------------- #


def combined_recommendation(decisions: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """Which K1 v3 designs the two lane reads support.

    INVALID first: a lane whose K1 smoke reproduction failed shows that the
    shared selection code path does not reproduce K1 v1's measurement, so no
    lane's read is a result (the 4B lane runs the same code) and no base, design
    or stop is read. Then INCOMPLETE when a lane has no completed receipt. Base:
    the first lane, in the registered order (Qwen3-0.6B-Base, then
    Qwen3.5-4B-Base), that is NEGATIVE_CAPABLE; otherwise the first that is
    GO_ONLY_CAPABLE (a v3 on it cannot register a NEGATIVE); otherwise none, and
    no K1 v3 is designed on these bases.

    Requirements: program decision D26's four are always required (a seen-script
    cross-script condition, an entity-controlled question set, a non-literal
    adequacy floor, a new id and the gauntlet). The chosen base's flags only
    add requirements; no measurement here removes one.
    """

    invalid = [lane for lane in dhd.REGISTERED_ORDER
               if lane in decisions and decisions[lane]["lane_class"] == "INVALID"]
    if invalid:
        return {"design": "INVALID", "base": None, "invalid_lanes": invalid,
                "lane_classes": {lane: decisions[lane]["lane_class"]
                                 for lane in dhd.REGISTERED_ORDER if lane in decisions},
                "reason": "the K1 smoke reproduction failed: the shared selection code path "
                          "does not reproduce K1 v1's measurement, so neither lane's read is "
                          "a result; a repair is a new experiment id",
                "requirements": []}
    missing = [lane for lane in dhd.REGISTERED_ORDER if lane not in decisions]
    if missing:
        return {"design": "INCOMPLETE", "base": None, "missing_lanes": missing,
                "requirements": []}
    chosen, design = None, "NO_K1_V3"
    for wanted, label in (("NEGATIVE_CAPABLE", "NEGATIVE_CAPABLE_V3"),
                          ("GO_ONLY_CAPABLE", "GO_ONLY_V3")):
        for lane in dhd.REGISTERED_ORDER:
            if decisions[lane]["lane_class"] == wanted:
                chosen, design = lane, label
                break
        if chosen:
            break
    requirements: list[str] = []
    if chosen:
        d = decisions[chosen]
        requirements = [
            "a seen-script cross-script condition (D26; not measurable here)",
            "an entity-controlled question set (D26)",
            "a new experiment id and the research gauntlet (D26)",
        ]
        if d["floor_candidate"] == "VIABLE":
            requirements.append("the non-literal floor (D26): 99 percent lower bound of G(MN) "
                                "on entity-controlled families at least 0.5")
        else:
            requirements.append("a non-literal adequacy floor (D26), redesigned: the candidate "
                                f"here is {d['floor_candidate']}")
        if d["lexical_confound"] != "ABSENT":
            requirements.append("the GO and NEGATIVE statistics computed on the entity-"
                                "controlled set, not only reported beside it (lexical confound "
                                f"{d['lexical_confound']})")
        if d["entity_control"] != "SUFFICIENT":
            requirements.append("anchor masking or a lexical-overlap covariate (entity control "
                                f"{d['entity_control']})")
        if any(v != "CENTRED" for v in d["null_calibration"].values()):
            requirements.append("a null-calibrated statistic (block-score null "
                                f"{d['null_calibration']})")
        if d.get("h2_status") != "PASS":
            requirements.append("H2 re-tested under K1's bounds on the v3 audit read (the "
                                f"development read's H2 is {d.get('h2_status')})")
    return {"design": design, "base": chosen,
            "lane_classes": {lane: decisions[lane]["lane_class"]
                             for lane in dhd.REGISTERED_ORDER},
            "requirements": requirements}


__all__ = [
    "BASE_SELECTORS",
    "FIXED_SELECTORS",
    "SIGMAS",
    "SMOKE_452",
    "TARGETS",
    "DenseStatsError",
    "Group",
    "Results",
    "analyse",
    "check_coverage",
    "classify_lane",
    "combined_recommendation",
    "entity_flags",
    "families",
    "h2_status",
    "null_names",
    "null_verdict",
    "reaching_sigmas",
    "retention_interval",
    "selector_names",
    "wilson",
]
