#!/usr/bin/env python3
"""AM1b (exploratory, CPU only): keep-set regret against reader calls for cheaper memory-credit
rules, simulated from AM1's committed development tables (D112).

Each committed table holds the judged utility u(S) of all 2^8 subsets of one pool. A rule reads
u through a memoized oracle: a call is one distinct subset, and the empty and full sets count when
a rule reads them. A credit rule keeps the top B memories by its credit, and its regret is the
exact optimum OPT_B minus u(keep set), averaged over every keep set its ties allow
(``harness.memcredit.keep_set_regret_range``, ``mean``; AM1's convention). The search procedures
(greedy forward and backward selection, direct search over random B-subsets) return one keep set,
scored by the same harness function on that set's indicator.

Every rule queries the oracle judged utility, as AM1's rules do: the curve measures attribution
quality per question, not a keep policy that runs without answer labels.

Usage, from the repository root (about a minute on a laptop CPU):

    python scripts/memcredit_cost_curve.py \\
        --tables program/evidence/2026-10-15/am1-dev-pilot/analysis/tables.json.gz \\
        --h2 program/evidence/2026-10-15/am1-dev-pilot/analysis/h2.json \\
        --output-dir program/evidence/2026-10-15/am1b-cost-curve

It reads the 126 development tables only (63 questions x 2 arms) and refuses any path under the
confirmatory evidence. It first checks the decoding against the committed credits, regrets and
bootstrap intervals and stops on any difference (``--validate-only`` stops there). It then writes
``results.json`` (aggregates), ``per-table.json.gz`` (per-table regrets and calls) and
``tables.md`` (the regret-against-calls tables).
"""

from __future__ import annotations

import argparse
import ast
import gzip
import hashlib
import json
import math
import random
import sys
from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for _path in (PROJECT_ROOT, PROJECT_ROOT / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import memcredit_analyze as ma  # noqa: E402

from harness import memcredit as mc  # noqa: E402
from harness import memcredit_study as ms  # noqa: E402

EXPERIMENT = "am1b-cost-curve"
DEV_DIR = Path("program/evidence/2026-10-15/am1-dev-pilot/analysis")
DEV_TABLES = DEV_DIR / "tables.json.gz"
DEV_TABLES_SHA256 = "839542c65332b908e1c80e9b5e9c09d9c23088e2dec4a54bf2e37dde4f0105d3"
DEV_H2 = DEV_DIR / "h2.json"
DEV_H2_SHA256 = "89fc5f14ff73143a5aeafa83fa9c6164e901ef8bb0bcf6edbb9130e796bc99c2"
#: Path parts that mark held-out evidence; AM1b never opens a path containing one.
FORBIDDEN_PARTS = ("am1-confirmatory",)

K = 8
BUDGETS = (1, 2, 3, 4)
ARMS = ("retrieved", "gold")
HEADLINE = ("retrieved", 4)
#: Stochastic rules run seeds SEED_BASE .. SEED_BASE + N_SEEDS - 1, each with
#: random.Random(f"{seed}:{question_id}:{arm}:{rule}"), AM1's scheme. Seeds 42, 43 and 44 of
#: perm_shapley_4, perm_shapley_16 and snipw_64 are therefore AM1's own draws.
SEED_BASE = 42
N_SEEDS = 20
BOOTSTRAP_RESAMPLES = 10_000
BOOTSTRAP_SEED = 42
#: AM1's committed rules and the seeds of its committed draws (validation only).
COMMITTED_SEEDS = (42, 43, 44)
COMMITTED_SEEDED = {"perm_shapley_4": 4, "perm_shapley_16": 16, "snipw_64": 64}
AM1_BOOTSTRAP = {"resamples": 4000, "seed": 42}
#: Estimator sizes: permutations, i.i.d. exposures, distinct subsets, kernel samples.
PERMUTATIONS = (1, 2, 4, 8, 16, 32, 64)
SNIPW_EXPOSURES = (8, 16, 32, 64, 128, 256, 512)
MSR_SUBSETS = (8, 16, 32, 64, 128, 192, 256)
KERNEL_SAMPLES = (8, 16, 32, 64, 128, 256, 512)
KERNEL_RIDGE = 1e-6
#: KernelSHAP credits are rounded to this many decimals so that float noise does not break
#: ties that are exact in the least-squares solution.
CREDIT_DIGITS = 9
#: Direct-search sizes listed in the markdown curve (every size is in results.json).
DIRECT_LISTED = (1, 4, 8, 9, 16, 18, 26, 32, 48, 64)


class CostCurveError(ValueError):
    """An input, a decoding or a validation check failed."""


# --------------------------------------------------------------------------- loading


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def check_path(path: Path) -> None:
    """Refuse held-out evidence before anything is opened."""

    for part in FORBIDDEN_PARTS:
        if part in str(path):
            raise CostCurveError(f"AM1b reads development tables only; refusing {path}")


def _field(value: Any) -> Any:
    """Committed fields are dicts; stringified Python dicts are accepted too."""

    return ast.literal_eval(value) if isinstance(value, str) else value


def load_tables(path: Path, expected_sha256: str | None) -> list[dict[str, Any]]:
    check_path(path)
    if expected_sha256 is not None and sha256_file(path) != expected_sha256:
        raise CostCurveError(f"{path}: SHA-256 is not {expected_sha256}")
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        tables = json.load(handle)
    for t in tables:
        for key in ("regret", "credits", "credits_seeded", "summary", "placebo"):
            if key in t:
                t[key] = _field(t[key])
    return tables


# --------------------------------------------------------------------------- decoding


def decode_values(values_hex: str, k: int = K) -> list[float]:
    """values[m] = bit m of the hex integer: the inverse of ``memcredit_analyze.analyze``'s
    ``format(int("".join(str(int(v)) for v in reversed(values)), 2), "064x")``, so bit i of a
    mask keeps memory i (pool order)."""

    n = int(values_hex, 16)
    if n >> (1 << k):
        raise CostCurveError("values_hex has more than 2^k bits")
    return [float(n >> m & 1) for m in range(1 << k)]


def decode_values_reversed(values_hex: str, k: int = K) -> list[float]:
    """The other bit order (mask m read from bit 2^k - 1 - m); used only to show that the
    committed regrets identify the decoding."""

    forward = decode_values(values_hex, k)
    return list(reversed(forward))


def encode_values(values: Sequence[float]) -> str:
    """``memcredit_analyze.analyze``'s encoding, verbatim."""

    return format(int("".join(str(int(v)) for v in reversed(values)), 2), "064x")


# --------------------------------------------------------------------------- memoized oracle


class CountingTable(Sequence):
    """A set-function table that records each distinct subset read: one call per mask."""

    def __init__(self, values: Sequence[float]) -> None:
        self._values = list(values)
        self.seen: set[int] = set()

    def __len__(self) -> int:
        return len(self._values)

    def __getitem__(self, mask: Any) -> float:  # type: ignore[override]
        if isinstance(mask, slice):
            raise TypeError("CountingTable does not slice")
        mask = int(mask)
        if mask < 0:
            mask += len(self._values)
        value = self._values[mask]  # IndexError ends iteration before the mask is counted
        self.seen.add(mask)
        return value

    @property
    def calls(self) -> int:
        return len(self.seen)


# --------------------------------------------------------------------------- estimators


def indicator(mask: int, k: int) -> list[float]:
    return [1.0 if mask >> i & 1 else 0.0 for i in range(k)]


def set_regret(values: Sequence[float], mask: int, budget: int) -> float:
    """Regret of one keep set, through the harness (its indicator is a credit with one top-B
    set)."""

    k = mc.check_table(values)
    if mc.popcount(mask) != budget:
        raise CostCurveError("keep set size differs from the budget")
    return float(mc.keep_set_regret_range(values, indicator(mask, k), budget)["mean"])


def loo_plus_loi(values: Sequence[float]) -> list[float]:
    """Leave-one-out plus leave-one-in credit (both 9-call rules; 18 distinct subsets)."""

    return [a + b for a, b in zip(mc.loo_credit(values), ms.leave_one_in(values), strict=True)]


def msr_banzhaf(values: Sequence[float], subsets: int, rng: random.Random) -> list[float]:
    """Banzhaf by maximum sample reuse over ``subsets`` distinct uniform subsets (drawn without
    replacement): mean u over the drawn sets with i minus mean u over those without i; 0 where a
    side is empty (the SNIPW convention). Exact rational arithmetic, so equal credits tie. Over
    all 2^k subsets it is exact Banzhaf."""

    k = mc.check_table(values)
    masks = rng.sample(range(1 << k), subsets)
    drawn = [(m, Fraction(float(values[m]))) for m in masks]
    out = []
    for i in range(k):
        bit = 1 << i
        inside = [v for m, v in drawn if m & bit]
        outside = [v for m, v in drawn if not m & bit]
        if not inside or not outside:
            out.append(0.0)
        else:
            out.append(float(sum(inside) / len(inside) - sum(outside) / len(outside)))
    return out


def shapley_kernel_size_weights(k: int) -> list[float]:
    """P(|S| = s) under the Shapley kernel, s = 1..k-1: proportional to (k-1)/(s(k-s))."""

    raw = [(k - 1) / (s * (k - s)) for s in range(1, k)]
    total = sum(raw)
    return [r / total for r in raw]


def kernel_solve(
    values: Sequence[float], weighted: dict[int, float], ridge: float = KERNEL_RIDGE
) -> list[float]:
    """Constrained weighted least squares of KernelSHAP: minimize sum_S w_S (u(S) - u(empty) -
    sum_{i in S} phi_i)^2 + ridge |phi|^2 subject to sum_i phi_i = u(full) - u(empty). The
    weights are normalized; with the exact Shapley-kernel weights over every coalition and no
    ridge the solution is exact Shapley. Credits are rounded to ``CREDIT_DIGITS``."""

    import numpy as np

    k = mc.check_table(values)
    full = (1 << k) - 1
    v0, v_full = float(values[0]), float(values[full])
    masks = sorted(weighted)
    z = np.array([[float(m >> i & 1) for i in range(k)] for m in masks])
    w = np.array([float(weighted[m]) for m in masks])
    w = w / w.sum()
    y = np.array([float(values[m]) for m in masks]) - v0
    a = (z * w[:, None]).T @ z + ridge * np.eye(k)
    b = (z * w[:, None]).T @ y
    ones = np.ones(k)
    a_inv_b = np.linalg.solve(a, b)
    a_inv_1 = np.linalg.solve(a, ones)
    nu = (ones @ a_inv_b - (v_full - v0)) / (ones @ a_inv_1)
    phi = a_inv_b - nu * a_inv_1
    return [round(float(p), CREDIT_DIGITS) + 0.0 for p in phi]


def kernel_shap(values: Sequence[float], samples: int, rng: random.Random) -> list[float]:
    """KernelSHAP with paired sampling: ``samples // 2`` coalitions drawn from the Shapley
    kernel (size s with probability proportional to (k-1)/(s(k-s)), then a uniform set of that
    size), each with its complement; every draw has weight 1 (duplicates add up); the empty and
    full sets are read for the efficiency constraint."""

    k = mc.check_table(values)
    full = (1 << k) - 1
    sizes = list(range(1, k))
    probs = shapley_kernel_size_weights(k)
    weighted: dict[int, float] = defaultdict(float)
    for _ in range(max(1, samples // 2)):
        size = rng.choices(sizes, weights=probs)[0]
        mask = sum(1 << i for i in rng.sample(range(k), size))
        weighted[mask] += 1.0
        weighted[full ^ mask] += 1.0
    return kernel_solve(values, dict(weighted))


def greedy_forward(values: Sequence[float], budget: int, priority: Sequence[float]) -> int:
    """Add, B times, the memory whose addition gives the highest u; ties go to the memory with
    the higher ``priority`` (here the BM25 retrieval credit, -rank). Reads sum_{j<B} (k - j)
    sets of sizes 1..B."""

    k = mc.check_table(values)
    mask = 0
    for _ in range(budget):
        cands = [i for i in range(k) if not mask >> i & 1]
        best = max(cands, key=lambda i: (float(values[mask | 1 << i]), priority[i]))
        mask |= 1 << best
    return mask


def greedy_backward(values: Sequence[float], budget: int, priority: Sequence[float]) -> int:
    """Remove, k - B times, the memory whose removal leaves the highest u; ties remove the
    memory with the lower ``priority``. Reads sets of sizes k-1..B (not the full set)."""

    k = mc.check_table(values)
    mask = (1 << k) - 1
    for _ in range(k - budget):
        cands = [i for i in range(k) if mask >> i & 1]
        drop = max(cands, key=lambda i: (float(values[mask & ~(1 << i)]), -priority[i]))
        mask &= ~(1 << drop)
    return mask


def greedy_calls(k: int, budget: int, forward: bool) -> int:
    steps = budget if forward else k - budget
    return sum(k - j for j in range(steps))


def greedy_tie_distribution(
    values: Sequence[float], budget: int, forward: bool
) -> dict[int, Fraction]:
    """The distribution of greedy's keep set when every tie is broken uniformly at random
    (exact). Every path reads the same number of sets, ``greedy_calls``."""

    k = mc.check_table(values)
    full = (1 << k) - 1
    states: dict[int, Fraction] = {0 if forward else full: Fraction(1)}
    for _ in range(budget if forward else k - budget):
        nxt: dict[int, Fraction] = defaultdict(Fraction)
        for mask, p in states.items():
            if forward:
                children = [mask | 1 << i for i in range(k) if not mask >> i & 1]
            else:
                children = [mask & ~(1 << i) for i in range(k) if mask >> i & 1]
            best = max(float(values[c]) for c in children)
            tied = [c for c in children if float(values[c]) == best]
            for c in tied:
                nxt[c] += p / len(tied)
        states = dict(nxt)
    return states


def greedy_tie_mean_regret(values: Sequence[float], budget: int, forward: bool) -> float:
    dist = greedy_tie_distribution(values, budget, forward)
    return float(sum(p * Fraction(set_regret(values, m, budget)) for m, p in dist.items()))


def direct_search_curve(values: Sequence[float], budget: int) -> list[float]:
    """Expected regret of direct search: read m distinct uniformly random B-subsets and keep the
    best read (m calls), for m = 1..C(k, B); entry m - 1. Every best-read set has the same u, so
    ties cannot change the regret. Exact: with the B-subsets in descending order of u, the best
    read is the j-th with probability C(N - j, m - 1) / C(N, m)."""

    k = mc.check_table(values)
    sets = ms.all_budget_sets(k, budget)
    regrets = sorted(Fraction(set_regret(values, s, budget)) for s in sets)
    n = len(sets)
    out = []
    for m in range(1, n + 1):
        total = sum(
            (r * math.comb(n - j, m - 1) for j, r in enumerate(regrets, start=1)), Fraction(0)
        )
        out.append(float(total / math.comb(n, m)))
    return out


def direct_search_simulated(
    values: Sequence[float], budget: int, m: int, rng: random.Random
) -> float:
    """One draw of direct search (for tests of ``direct_search_curve``)."""

    k = mc.check_table(values)
    sets = rng.sample(ms.all_budget_sets(k, budget), m)
    best = max(sets, key=lambda s: float(values[s]))
    return set_regret(values, best, budget)


def matched_direct(curve: list[float], calls: int, random_regret: float) -> float:
    """Direct search's expected regret with the same number of calls (0 calls: a random keep
    set; more calls than B-subsets: the exhaustive search, regret 0)."""

    if calls <= 0:
        return random_regret
    return curve[min(calls, len(curve)) - 1]


# --------------------------------------------------------------------------- rule registry


@dataclass(frozen=True)
class Rule:
    name: str
    family: str
    kind: str  # "credit" | "search" | "anchor"
    size: int | None
    stochastic: bool
    describe: str
    credit: Callable[[Sequence[float], random.Random | None], list[float]] | None = None


def credit_rules() -> list[Rule]:
    rules = [
        Rule("loo", "leave-one-out / leave-one-in", "credit", None, False,
             "leave-one-out u(N) - u(N - i); full set + 8", lambda v, r: mc.loo_credit(v)),
        Rule("leave_one_in", "leave-one-out / leave-one-in", "credit", None, False,
             "leave-one-in u({i}) - u(empty); empty set + 8", lambda v, r: ms.leave_one_in(v)),
        Rule("loo_plus_loi", "leave-one-out / leave-one-in", "credit", None, False,
             "leave-one-out + leave-one-in (sum)", lambda v, r: loo_plus_loi(v)),
    ]  # fmt: skip
    for p in PERMUTATIONS:
        rules.append(Rule(
            f"perm_shapley_{p}", "permutation Shapley", "credit", p, True,
            f"permutation Shapley, {p} uniform orders (harness)",
            lambda v, r, p=p: ms.permutation_shapley(v, p, r)[0],
        ))  # fmt: skip
    for e in SNIPW_EXPOSURES:
        rules.append(Rule(
            f"snipw_{e}", "SNIPW (i.i.d. exposures)", "credit", e, True,
            f"SNIPW over {e} i.i.d. exposures, propensity 1/2 (harness)",
            lambda v, r, e=e: ms.snipw(v, e, r)[0],
        ))  # fmt: skip
    for s in MSR_SUBSETS:
        rules.append(Rule(
            f"msr_banzhaf_{s}", "MSR Banzhaf (distinct subsets)", "credit", s, s < 1 << K,
            f"Banzhaf by maximum sample reuse over {s} distinct uniform subsets",
            lambda v, r, s=s: msr_banzhaf(v, s, r if r is not None else random.Random(0)),
        ))  # fmt: skip
    for n in KERNEL_SAMPLES:
        rules.append(Rule(
            f"kernelshap_{n}", "KernelSHAP (paired)", "credit", n, True,
            f"KernelSHAP, {n} paired kernel samples, ridge {KERNEL_RIDGE:g}, efficiency",
            lambda v, r, n=n: kernel_shap(v, n, r),
        ))  # fmt: skip
    rules += [
        Rule("shapley_exact", "exact references", "credit", None, False,
             "exact Shapley (all 256 subsets)", lambda v, r: mc.shapley(v)),
        Rule("banzhaf_exact", "exact references", "credit", None, False,
             "exact Banzhaf (all 256 subsets)", lambda v, r: ms.banzhaf(v)),
    ]  # fmt: skip
    return rules


SEARCH_RULES = (
    Rule("greedy_forward", "greedy selection (search)", "search", None, False,
         "greedy forward selection; ties to the better BM25 rank"),
    Rule("greedy_backward", "greedy selection (search)", "search", None, False,
         "greedy backward elimination; ties drop the worse BM25 rank"),
    Rule("greedy_forward_tiemean", "greedy selection (search)", "search", None, False,
         "greedy forward, expected regret over uniform random tie-breaks"),
    Rule("greedy_backward_tiemean", "greedy selection (search)", "search", None, False,
         "greedy backward, expected regret over uniform random tie-breaks"),
)  # fmt: skip
ANCHOR_RULES = (
    Rule("random_keep_set", "anchors (0 calls)", "anchor", None, False,
         "a uniformly random keep set (expected regret)"),
    Rule("retrieval_rank", "anchors (0 calls)", "anchor", None, False,
         "BM25 retrieval rank (the committed credit)"),
)  # fmt: skip


def seeds(n_seeds: int, seed_base: int) -> list[int]:
    return [seed_base + j for j in range(n_seeds)]


def rule_rng(seed: int, question_id: str, arm: str, name: str) -> random.Random:
    return random.Random(f"{seed}:{question_id}:{arm}:{name}")


# --------------------------------------------------------------------------- validation


def _regret_dict_equal(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return all(float(a[key]) == float(b[key]) for key in ("min", "mean", "max", "sets"))


def validate(tables: list[dict[str, Any]], h2: dict[str, Any] | None) -> dict[str, Any]:
    """Step 1: decoding, credits, regrets, seeded draws and the bootstrap against the committed
    record. Raises CostCurveError on any difference."""

    out: dict[str, Any] = {"tables": len(tables)}
    failures: list[str] = []
    counts: dict[str, int] = defaultdict(int)
    reversed_regret_matches = 0
    reversed_checked = 0
    budgets = [str(b) for b in BUDGETS]
    for t in tables:
        tag = f"{t['question_id']}:{t['arm']}"
        if not t.get("complete"):
            failures.append(f"{tag}: incomplete table")
            continue
        values = decode_values(t["values_hex"])
        s = t["summary"]
        if encode_values(values) != t["values_hex"]:
            failures.append(f"{tag}: re-encoding differs")
        counts["round_trip"] += 1
        best = {str(b): mc.best_keep_sets(values, b)[0] for b in range(1, K)}
        if not (
            s["k"] == K
            and float(s["u_full"]) == values[-1]
            and float(s["u_empty"]) == values[0]
            and bool(s["constant"]) == (len(set(values)) == 1)
            and all(float(s["best_by_budget"][b]) == best[b] for b in best)
            and float(s["mean"]) == sum(values) / len(values)
        ):
            failures.append(f"{tag}: summary differs")
        counts["summary"] += 1
        recomputed = {
            "shapley_exact": mc.shapley(values),
            "banzhaf_exact": ms.banzhaf(values),
            "loo": mc.loo_credit(values),
            "leave_one_in": ms.leave_one_in(values),
        }
        for name, credit in recomputed.items():
            if [float(x) for x in t["credits"][name]] != credit:
                failures.append(f"{tag}: {name} credit differs")
        if [float(x) for x in t["placebo"]["loo"]] != recomputed["loo"]:
            failures.append(f"{tag}: placebo loo differs")
        counts["credits"] += 1
        for name, draws in COMMITTED_SEEDED.items():
            for seed in COMMITTED_SEEDS:
                rng = rule_rng(seed, t["question_id"], t["arm"], name)
                table = CountingTable(values)
                if name.startswith("perm"):
                    credit, calls = ms.permutation_shapley(table, draws, rng)
                else:
                    credit, calls = ms.snipw(table, draws, rng)
                committed = t["credits_seeded"][name][str(seed)]
                if credit != [float(x) for x in committed["credit"]]:
                    failures.append(f"{tag}: {name} seed {seed} credit differs")
                if calls != int(committed["calls"]) or table.calls != calls:
                    failures.append(f"{tag}: {name} seed {seed} calls differ")
                counts["seeded_draws"] += 1
        constant = len(set(values)) == 1
        if constant != ("regret" not in t):
            failures.append(f"{tag}: regret present iff non-constant fails")
        if constant:
            continue
        counts["nonconstant"] += 1
        regret = t["regret"]
        # the required check: recomputed exact Shapley and leave-one-out regret at B = 1..4
        for name in ("shapley_exact", "loo"):
            for b in budgets:
                mine = mc.keep_set_regret_range(values, recomputed[name], int(b))
                if not _regret_dict_equal(mine, regret[name][b]):
                    failures.append(f"{tag}: {name} B={b} regret differs")
                counts[f"regret_{name}"] += 1
        # every other committed rule, from its committed (or redrawn) credit
        for name, per_budget in regret.items():
            if name in ("shapley_exact", "loo"):
                continue
            for b in budgets:
                if name == "random":
                    if ms.random_regret(values, int(b)) != float(per_budget[b]["mean"]):
                        failures.append(f"{tag}: random B={b} differs")
                    continue
                if name in COMMITTED_SEEDED:
                    per_seed = [
                        mc.keep_set_regret_range(
                            values, t["credits_seeded"][name][str(sd)]["credit"], int(b)
                        )["mean"]
                        for sd in COMMITTED_SEEDS
                    ]
                    if sum(per_seed) / len(per_seed) != float(per_budget[b]["mean"]):
                        failures.append(f"{tag}: {name} B={b} seed-mean regret differs")
                    continue
                mine = mc.keep_set_regret_range(values, t["credits"][name], int(b))
                if not _regret_dict_equal(mine, per_budget[b]):
                    failures.append(f"{tag}: {name} B={b} regret differs")
            counts["regret_other_rules"] += 1
        # the other bit order: does it also reproduce the committed regrets?
        alt = decode_values_reversed(t["values_hex"])
        reversed_checked += 1
        ok = all(
            _regret_dict_equal(
                mc.keep_set_regret_range(alt, credit_fn(alt), int(b)), regret[name][b]
            )
            for name, credit_fn in (("shapley_exact", mc.shapley), ("loo", mc.loo_credit))
            for b in budgets
        )
        reversed_regret_matches += int(ok)
    out["checks"] = dict(sorted(counts.items()))
    out["reversed_bit_order"] = {
        "nonconstant_tables": reversed_checked,
        "reproduce_shapley_and_loo_regrets": reversed_regret_matches,
    }
    if h2 is not None:
        out["am1_bootstrap"] = _validate_bootstrap(tables, h2, failures)
    out["failures"] = failures
    out["passed"] = not failures
    if failures:
        raise CostCurveError(f"validation failed ({len(failures)}): {failures[:10]}")
    return out


def _validate_bootstrap(
    tables: list[dict[str, Any]], h2: dict[str, Any], failures: list[str]
) -> dict[str, Any]:
    """AM1's aggregate rows from the recomputed per-table regrets with AM1's bootstrap (4,000
    resamples, seed 42): the same non-constant set and the same interval code."""

    checked = []
    for arm in ARMS:
        for b in (str(x) for x in BUDGETS):
            for name in ("loo", "shapley_exact", "perm_shapley_16", "snipw_64"):
                clusters: dict[str, list[float]] = defaultdict(list)
                for t in tables:
                    if t["arm"] != arm or "regret" not in t:
                        continue
                    values = decode_values(t["values_hex"])
                    if name in COMMITTED_SEEDED:
                        reg = [
                            mc.keep_set_regret_range(
                                values, t["credits_seeded"][name][str(sd)]["credit"], int(b)
                            )["mean"]
                            for sd in COMMITTED_SEEDS
                        ]
                        clusters[t["question_id"]].append(sum(reg) / len(reg))
                    else:
                        credit = (
                            mc.shapley(values)
                            if name == "shapley_exact"
                            else (mc.loo_credit(values))
                        )
                        clusters[t["question_id"]].append(
                            mc.keep_set_regret_range(values, credit, int(b))["mean"]
                        )
                for key, alpha in (("mean_regret", 0.05), ("mean_regret_99", 0.01)):
                    mine = ms.cluster_bootstrap(
                        clusters, AM1_BOOTSTRAP["resamples"], AM1_BOOTSTRAP["seed"], alpha
                    )
                    theirs = h2[arm][b][name][key]
                    same = mine["mean"] == theirs["mean"] and mine["ci"] == theirs["ci"]
                    if not same:
                        failures.append(f"h2 {arm} B={b} {name} {key} differs")
                    checked.append(same)
    return {"rows_checked": len(checked), "rows_identical": sum(checked)}


# --------------------------------------------------------------------------- the curve


def table_curve(t: dict[str, Any], rules: list[Rule], seed_list: list[int]) -> dict[str, Any]:
    """Per-table regret (mean over seeds) at B = 1..4, mean calls, and direct search at the same
    calls, for every rule, plus the direct-search curve."""

    values = decode_values(t["values_hex"])
    qid, arm = t["question_id"], t["arm"]
    priority = [float(x) for x in t["credits"]["retrieval_rank"]]
    direct = {b: direct_search_curve(values, b) for b in BUDGETS}
    rand = {b: ms.random_regret(values, b) for b in BUDGETS}
    out: dict[str, Any] = {"question_id": qid, "arm": arm, "rules": {}}
    for rule in rules:
        runs = seed_list if rule.stochastic else [None]
        regrets = {b: [] for b in BUDGETS}
        matched = {b: [] for b in BUDGETS}
        calls_list = []
        for seed in runs:
            rng = rule_rng(seed, qid, arm, rule.name) if seed is not None else None
            table = CountingTable(values)
            assert rule.credit is not None
            credit = rule.credit(table, rng)
            calls_list.append(table.calls)
            for b in BUDGETS:
                regrets[b].append(mc.keep_set_regret_range(values, credit, b)["mean"])
                matched[b].append(matched_direct(direct[b], table.calls, rand[b]))
        out["rules"][rule.name] = _cell(regrets, matched, {b: calls_list for b in BUDGETS})
    for forward, name in ((True, "greedy_forward"), (False, "greedy_backward")):
        regrets, matched, calls = {}, {}, {}
        tie_regrets, tie_matched = {}, {}
        for b in BUDGETS:
            table = CountingTable(values)
            fn = greedy_forward if forward else greedy_backward
            mask = fn(table, b, priority)
            if table.calls != greedy_calls(K, b, forward):
                raise CostCurveError(f"{name}: calls {table.calls} differ from the formula")
            calls[b] = [table.calls]
            regrets[b] = [set_regret(values, mask, b)]
            matched[b] = [matched_direct(direct[b], table.calls, rand[b])]
            tie_regrets[b] = [greedy_tie_mean_regret(values, b, forward)]
            tie_matched[b] = matched[b]
        out["rules"][name] = _cell(regrets, matched, calls)
        out["rules"][f"{name}_tiemean"] = _cell(tie_regrets, tie_matched, calls)
    out["rules"]["random_keep_set"] = _cell(
        {b: [rand[b]] for b in BUDGETS}, {b: [rand[b]] for b in BUDGETS}, {b: [0] for b in BUDGETS}
    )
    rank_credit = [float(x) for x in t["credits"]["retrieval_rank"]]
    out["rules"]["retrieval_rank"] = _cell(
        {b: [mc.keep_set_regret_range(values, rank_credit, b)["mean"]] for b in BUDGETS},
        {b: [rand[b]] for b in BUDGETS},
        {b: [0] for b in BUDGETS},
    )
    out["direct_search"] = {str(b): direct[b] for b in BUDGETS}
    return out


def _cell(
    regrets: dict[int, list[float]], matched: dict[int, list[float]], calls: dict[int, list[int]]
) -> dict[str, Any]:
    out = {}
    for b in BUDGETS:
        cell = {
            "regret": sum(regrets[b]) / len(regrets[b]),
            "direct_matched": sum(matched[b]) / len(matched[b]),
            "calls": sum(calls[b]) / len(calls[b]),
            "calls_min": min(calls[b]),
            "calls_max": max(calls[b]),
        }
        if len(regrets[b]) > 1:
            cell["regret_by_seed"] = list(regrets[b])
        out[str(b)] = cell
    return out


def _interval(clusters: dict[str, list[float]], resamples: int, seed: int) -> dict[str, Any]:
    ci95 = ms.cluster_bootstrap(clusters, resamples, seed, 0.05)
    ci99 = ms.cluster_bootstrap(clusters, resamples, seed, 0.01)
    return {"ci95": ci95, "ci99": ci99}


def aggregate(
    per_table: list[dict[str, Any]], rule_names: list[str], resamples: int, seed: int
) -> dict[str, Any]:
    curve: dict[str, Any] = {}
    direct_curve: dict[str, Any] = {}
    for arm in ARMS:
        rows = [p for p in per_table if p["arm"] == arm]
        curve[arm] = {}
        direct_curve[arm] = {}
        for b in (str(x) for x in BUDGETS):
            cells: dict[str, Any] = {}
            for name in rule_names:
                reg: dict[str, list[float]] = defaultdict(list)
                diff: dict[str, list[float]] = defaultdict(list)
                calls, cmin, cmax = [], [], []
                for p in rows:
                    c = p["rules"][name][b]
                    reg[p["question_id"]].append(c["regret"])
                    diff[p["question_id"]].append(c["regret"] - c["direct_matched"])
                    calls.append(c["calls"])
                    cmin.append(c["calls_min"])
                    cmax.append(c["calls_max"])
                iv = _interval(reg, resamples, seed)
                row = {
                    "tables": iv["ci95"]["units"],
                    "mean_regret": iv["ci95"],
                    "mean_regret_99": iv["ci99"],
                }
                verdict = ma.h2_verdict(row)["verdict"]
                d95 = ms.cluster_bootstrap(diff, resamples, seed, 0.05)
                by_seed = [p["rules"][name][b].get("regret_by_seed") for p in rows]
                mc_se = None
                if all(by_seed):
                    n_seeds = len(by_seed[0])
                    seed_means = [sum(s[j] for s in by_seed) / len(rows) for j in range(n_seeds)]
                    centre = sum(seed_means) / n_seeds
                    var = sum((x - centre) ** 2 for x in seed_means) / (n_seeds - 1)
                    mc_se = math.sqrt(var / n_seeds)
                cells[name] = {
                    "tables": row["tables"],
                    "calls_mean": sum(calls) / len(calls),
                    "calls_min": min(cmin),
                    "calls_max": max(cmax),
                    "mean_regret": iv["ci95"]["mean"],
                    "ci95": iv["ci95"]["ci"],
                    "ci99": iv["ci99"]["ci"],
                    "label": verdict,
                    "seed_mc_se": mc_se,
                    "direct_matched_mean": sum(p["rules"][name][b]["direct_matched"] for p in rows)
                    / len(rows),
                    "minus_direct_matched": {"mean": d95["mean"], "ci95": d95["ci"]},
                }
            curve[arm][b] = cells
            n_sets = len(rows[0]["direct_search"][b])
            points = []
            for m in range(1, n_sets + 1):
                reg = defaultdict(list)
                for p in rows:
                    reg[p["question_id"]].append(p["direct_search"][b][m - 1])
                iv = _interval(reg, resamples, seed)
                row = {"tables": iv["ci95"]["units"], "mean_regret": iv["ci95"],
                       "mean_regret_99": iv["ci99"]}  # fmt: skip
                points.append({
                    "calls": m,
                    "mean_regret": iv["ci95"]["mean"],
                    "ci95": iv["ci95"]["ci"],
                    "ci99": iv["ci99"]["ci"],
                    "label": ma.h2_verdict(row)["verdict"],
                })  # fmt: skip
            direct_curve[arm][b] = points
    return {"curve": curve, "direct_search": direct_curve}


def answers(agg: dict[str, Any], rules: dict[str, Rule]) -> dict[str, Any]:
    """The headline questions on the retrieved arm at B = 4, ordered by mean calls."""

    arm, b = HEADLINE
    cells = agg["curve"][arm][str(b)]

    def cheapest(kinds: tuple[str, ...], pred: Callable[[dict[str, Any]], bool]) -> Any:
        hits = [
            (c["calls_mean"], name)
            for name, c in cells.items()
            if rules[name].kind in kinds and pred(c)
        ]
        if not hits:
            return None
        calls, name = min(hits)
        c = cells[name]
        return {"rule": name, "calls_mean": calls, "mean_regret": c["mean_regret"],
                "ci95": c["ci95"], "ci99": c["ci99"], "label": c["label"],
                "minus_direct_matched": c["minus_direct_matched"]}  # fmt: skip

    out = {}
    for label, kinds in (("credit_rules", ("credit",)), ("search_rules", ("search",))):
        out[label] = {
            "cheapest_not_misspecified": cheapest(kinds, lambda c: c["label"] != "MISSPECIFIED"),
            "cheapest_ci99_upper_at_most_0.05": cheapest(kinds, lambda c: c["ci99"][1] <= 0.05),
            "cheapest_adequate": cheapest(kinds, lambda c: c["label"] == "ADEQUATE"),
            "cheapest_beating_direct_search_point": cheapest(
                kinds, lambda c: c["minus_direct_matched"]["mean"] < 0
            ),
            "cheapest_beating_direct_search_ci95": cheapest(
                kinds, lambda c: c["minus_direct_matched"]["ci95"][1] < 0
            ),
        }
    direct = agg["direct_search"][arm][str(b)]
    out["direct_search"] = {
        "cheapest_not_misspecified": next(
            (p for p in direct if p["label"] != "MISSPECIFIED"), None
        ),
        "cheapest_ci99_upper_at_most_0.05": next((p for p in direct if p["ci99"][1] <= 0.05), None),
        "exhaustive_calls": len(direct),
    }
    return out


# --------------------------------------------------------------------------- markdown


def _f(x: float | None, digits: int = 3) -> str:
    return "n/a" if x is None else f"{x:.{digits}f}"


def _ci(ci: list[float | None]) -> str:
    return f"[{_f(ci[0])}, {_f(ci[1])}]"


def _calls(c: dict[str, Any]) -> str:
    if c["calls_min"] == c["calls_max"]:
        return str(c["calls_min"])
    return f"{c['calls_mean']:.1f} ({c['calls_min']}-{c['calls_max']})"


def render_markdown(results: dict[str, Any], rules: dict[str, Rule]) -> str:
    lines = [
        "# AM1b cost curve: regret against reader calls (generated)",
        "",
        "Generated by `scripts/memcredit_cost_curve.py` from the development tables only. "
        "EXPLORATORY. Mean keep-set regret over the non-constant tables of each arm; intervals are "
        "question-clustered percentile bootstraps "
        f"({results['config']['bootstrap']['resamples']:,} resamples, seed "
        f"{results['config']['bootstrap']['seed']}). Labels apply AM1's section 7 "
        "rule to the 99% interval, descriptively. Calls: distinct subsets read per pool (mean, "
        "with range over tables and seeds). Direct = direct search over random B-subsets at the "
        "same calls (exact expectation); rule - direct is paired by table. se: Monte Carlo "
        "standard error of a stochastic rule's mean over its seeds.",
        "",
    ]
    order = sorted(rules.values(), key=lambda r: list(rules).index(r.name))
    short = {"MISSPECIFIED": "M", "INCONCLUSIVE": "I", "ADEQUATE": "A", None: "?"}
    cols = [(arm, str(b)) for arm in ARMS for b in BUDGETS]
    lines += [
        "## Summary: mean regret and label (M, I, A) in every cell",
        "",
        "Calls are those at B = 4; greedy calls depend on B (forward 8, 15, 21, 26; backward "
        "35, 33, 30, 26 at B = 1, 2, 3, 4).",
        "",
        "| Rule | Calls (B = 4) | " + " | ".join(f"{a[:3]} B={b}" for a, b in cols) + " |",
        "|---|---:|" + "---:|" * len(cols),
    ]
    for rule in order:
        c4 = results["curve"][HEADLINE[0]][str(HEADLINE[1])][rule.name]
        cells_txt = [
            f"{_f(results['curve'][a][b][rule.name]['mean_regret'])} "
            f"{short[results['curve'][a][b][rule.name]['label']]}"
            for a, b in cols
        ]
        lines.append(f"| {rule.name} | {_calls(c4)} | " + " | ".join(cells_txt) + " |")
    lines += [
        "",
        "Direct search at selected calls (exhaustive at C(8, B) = 8, 28, 56, 70 calls):",
        "",
        "| Calls | " + " | ".join(f"{a[:3]} B={b}" for a, b in cols) + " |",
        "|---:|" + "---:|" * len(cols),
    ]
    for m in DIRECT_LISTED:
        row = []
        for a, b in cols:
            points = results["direct_search"][a][b]
            p = points[min(m, len(points)) - 1]
            row.append(f"{_f(p['mean_regret'])} {short[p['label']]}")
        lines.append(f"| {m} | " + " | ".join(row) + " |")
    lines.append("")
    for arm in ARMS:
        for b in (str(x) for x in reversed(BUDGETS)):
            cells = results["curve"][arm][b]
            n = next(iter(cells.values()))["tables"]
            primary = " (primary cell)" if (arm, int(b)) == HEADLINE else ""
            lines += [
                f"## {arm} arm, B = {b}{primary}: {n} non-constant tables",
                "",
                "| Rule | Calls | Mean regret | 95% CI | 99% CI | Label | Direct, same calls "
                "| Rule - direct [95% CI] |",
                "|---|---:|---:|---|---|---|---:|---|",
            ]
            family = None
            for rule in order:
                c = cells[rule.name]
                if rule.family != family:
                    family = rule.family
                    lines.append(f"| *{family}* | | | | | | | |")
                d = c["minus_direct_matched"]
                se = c.get("seed_mc_se")
                mean = _f(c["mean_regret"]) + ("" if se is None else f" (se {se:.3f})")
                lines.append(
                    f"| {rule.name} | {_calls(c)} | {mean} | {_ci(c['ci95'])} | "
                    f"{_ci(c['ci99'])} | {c['label']} | {_f(c['direct_matched_mean'])} | "
                    f"{_f(d['mean'], 3)} {_ci(d['ci95'])} |"
                )
            points = results["direct_search"][arm][b]
            listed = sorted({m for m in DIRECT_LISTED if m <= len(points)} | {len(points)})
            lines += [
                "",
                f"Direct search (a search baseline, not a credit rule), {arm}, B = {b}:",
                "",
                "| Calls | Mean regret | 95% CI | 99% CI | Label |",
                "|---:|---:|---|---|---|",
            ]
            for m in listed:
                p = points[m - 1]
                lines.append(
                    f"| {m} | {_f(p['mean_regret'])} | {_ci(p['ci95'])} | {_ci(p['ci99'])} | "
                    f"{p['label']} |"
                )
            lines.append("")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- main


def run(args: argparse.Namespace) -> dict[str, Any]:
    tables_path = Path(args.tables)
    tables = load_tables(tables_path, args.expected_sha256)
    h2 = None
    if args.h2:
        h2_path = Path(args.h2)
        check_path(h2_path)
        if sha256_file(h2_path) != args.expected_h2_sha256:
            raise CostCurveError(f"{h2_path}: SHA-256 is not {args.expected_h2_sha256}")
        h2 = json.loads(h2_path.read_text(encoding="utf-8"))
    validation = validate(tables, h2)
    print(f"validation passed: {validation['checks']}", file=sys.stderr)
    if args.validate_only:
        return {"validation": validation}
    seed_list = seeds(args.seeds, args.seed_base)
    crules = credit_rules()
    all_rules = {r.name: r for r in (*ANCHOR_RULES, *crules, *SEARCH_RULES)}
    per_table = []
    for t in tables:
        if t["arm"] in ARMS and "regret" in t:
            per_table.append(table_curve(t, crules, seed_list))
    per_table.sort(key=lambda p: (p["arm"], p["question_id"]))
    agg = aggregate(per_table, list(all_rules), args.resamples, args.bootstrap_seed)
    import numpy as np

    results = {
        "experiment": EXPERIMENT,
        "status": "EXPLORATORY",
        "decision": "D112",
        "inputs": {
            "tables": {
                "path": str(DEV_TABLES),
                "sha256": sha256_file(tables_path),
                "tables": len(tables),
                "questions": len({t["question_id"] for t in tables}),
            },  # fmt: skip
            "h2": {"path": str(DEV_H2), "sha256": args.expected_h2_sha256} if h2 else None,
            "confirmatory_tables_opened": False,
        },
        "config": {
            "k": K,
            "budgets": list(BUDGETS),
            "arms": list(ARMS),
            "headline": {"arm": HEADLINE[0], "budget": HEADLINE[1]},
            "nonconstant_rule": "a table counts when its 256 values are not all equal (AM1's "
            "summary.constant is False; exactly the tables with a committed regret field)",
            "regret": "harness.memcredit.keep_set_regret_range mean (uniform over tie sets); "
            "search rules through their keep set's indicator",
            "call": "one distinct subset read per pool (memoized); empty and full sets count "
            "when read",
            "seeds": {
                "base": args.seed_base,
                "count": args.seeds,
                "list": seed_list,
                "rng": "random.Random(f'{seed}:{question_id}:{arm}:{rule}')",
            },  # fmt: skip
            "bootstrap": {
                "resamples": args.resamples,
                "seed": args.bootstrap_seed,
                "code": "harness.memcredit_study.cluster_bootstrap",
                "levels": [0.95, 0.99],
            },  # fmt: skip
            "labels": "memcredit_analyze.h2_verdict: MISSPECIFIED if the 99% lower bound > 0.05, "
            "ADEQUATE if the 99% upper bound < 0.02, else INCONCLUSIVE (descriptive here)",
            "sizes": {
                "permutations": list(PERMUTATIONS),
                "snipw_exposures": list(SNIPW_EXPOSURES),
                "msr_subsets": list(MSR_SUBSETS),
                "kernel_samples": list(KERNEL_SAMPLES),
            },
            "kernel_ridge": KERNEL_RIDGE,
            "kernel_credit_digits": CREDIT_DIGITS,
            "greedy_ties": "BM25 retrieval rank (credits.retrieval_rank, -rank): forward adds "
            "the better-ranked memory, backward drops the worse-ranked one; the *_tiemean rows "
            "average over uniform random tie-breaks instead. Pool bit order is chronological.",
        },  # fmt: skip
        "rules": {
            name: {
                "family": r.family,
                "kind": r.kind,
                "size": r.size,
                "stochastic": r.stochastic,
                "describe": r.describe,
            }  # fmt: skip
            for name, r in all_rules.items()
        },
        "validation": validation,
        "curve": agg["curve"],
        "direct_search": agg["direct_search"],
        "answers": answers(agg, all_rules),
        "environment": {"python": sys.version.split()[0], "numpy": np.__version__},
    }
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "results.json").write_text(
        json.dumps(results, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    blob = json.dumps(per_table, sort_keys=True, separators=(",", ":")).encode("utf-8")
    (out_dir / "per-table.json.gz").write_bytes(gzip.compress(blob, mtime=0))
    (out_dir / "tables.md").write_text(render_markdown(results, all_rules), encoding="utf-8")
    return results


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--tables", default=str(DEV_TABLES))
    parser.add_argument("--expected-sha256", default=DEV_TABLES_SHA256)
    parser.add_argument("--h2", default=str(DEV_H2), help="AM1's committed pilot h2.json")
    parser.add_argument("--expected-h2-sha256", default=DEV_H2_SHA256)
    parser.add_argument("--output-dir", default="program/evidence/2026-10-15/am1b-cost-curve")
    parser.add_argument("--seeds", type=int, default=N_SEEDS)
    parser.add_argument("--seed-base", type=int, default=SEED_BASE)
    parser.add_argument("--resamples", type=int, default=BOOTSTRAP_RESAMPLES)
    parser.add_argument("--bootstrap-seed", type=int, default=BOOTSTRAP_SEED)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        results = run(args)
    except CostCurveError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if "answers" in results:
        print(json.dumps(results["answers"], indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
