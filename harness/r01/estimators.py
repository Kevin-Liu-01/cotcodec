"""The registered Stage B estimator and readings (draft registration v2, sections 7.4 and 10).

Unit: a request pair (a reference request and the cell's other request, both answered); cluster:
the task (113). A cell's hazard at the text level is the share of pairs whose reply texts differ
(SHA-256 of the full reply, thinking included); at the IR level, the share whose parsed IR
differs (S1a's ``ir_sha256``). Interval: task-cluster percentile bootstrap of the pooled share,
2,000 resamples, ``numpy.random.default_rng(42)``. The same functions run inside the operating-
characteristic simulations (``bounds_many``), so the rules and their simulations share code.

Readings (step 1 primary, step 2 secondary):

* text: SUFFICIENT if the lower bound > 0.20; INERT if the upper bound < 0.05; else PARTIAL;
* IR (relative to S1a's natural step-1 IR onset, 79 of 226 = 0.350): MAJOR if the lower bound
  > 0.175 (half of it); MINOR if the upper bound < 0.117 (a third of it); else PARTIAL;
* DET on the replica cell (n pairs): DET_OK at 0 differing; DET_UNATTAINABLE if the one-sided
  95% Clopper-Pearson lower bound exceeds 1%; DET_NEAR between. Under DET_NEAR the det cells are
  read on h - h_floor, paired by request;
* the joint text reading over the three single-source cells (s, c, o): REDUNDANT if at least two
  are SUFFICIENT; SINGLE_SOURCE if exactly one is SUFFICIENT and the other two INERT; NEITHER if
  all three are INERT; MIXED otherwise (reported, no attribution);
* VAL, the request-level replay against S1a's closed loop: the all-sources live cell X_s against
  S1a's within-session step-1 counts (205 of 226 text, 79 of 226 IR), the difference's interval
  from independent task-cluster bootstraps of both: VAL_PASS if, at both levels, the 95% interval
  lies inside +-0.15; VAL_FAIL if at either level it excludes 0 and the point difference exceeds
  0.10 in magnitude; VAL_UNRESOLVED otherwise.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
from scipy import stats

BOOT = 2000
SEED = 42
TEXT_SUFFICIENT, TEXT_INERT = 0.20, 0.05
NATURAL_IR = 79 / 226
IR_MAJOR, IR_MINOR = NATURAL_IR / 2, NATURAL_IR / 3
S1A_TEXT, S1A_IR, S1A_N = 205, 79, 226
VAL_MARGIN, VAL_FAIL_DIFF = 0.15, 0.10
MISSING_VOID = 0.05


def task_sums(task_ids: Sequence[str], values: Sequence[float]) -> tuple[np.ndarray, np.ndarray]:
    order = sorted(set(task_ids))
    index = {t: i for i, t in enumerate(order)}
    sums = np.zeros(len(order))
    counts = np.zeros(len(order))
    for t, v in zip(task_ids, values, strict=True):
        sums[index[t]] += v
        counts[index[t]] += 1
    return sums, counts


def bounds(
    task_ids: Sequence[str], values: Sequence[float], boot: int = BOOT, seed: int = SEED
) -> dict[str, float]:
    sums, counts = task_sums(task_ids, values)
    est, lo, hi = bounds_many(sums[None, :], counts[None, :], boot=boot, seed=seed)
    return {
        "estimate": float(est[0]),
        "lo": float(lo[0]),
        "hi": float(hi[0]),
        "n": int(counts.sum()),
        "tasks": len(sums),
    }


def bounds_many(
    sums: np.ndarray, counts: np.ndarray, boot: int = BOOT, seed: int = SEED, chunk: int = 50
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Pooled share and percentile 95% bounds for each row (replicate) of per-task sums."""
    rng = np.random.default_rng(seed)
    reps, tasks = sums.shape
    est = sums.sum(axis=1) / counts.sum(axis=1)
    lo, hi = np.empty(reps), np.empty(reps)
    for r0 in range(0, reps, chunk):
        r1 = min(reps, r0 + chunk)
        idx = rng.integers(0, tasks, size=(boot, tasks))
        s = sums[r0:r1][:, idx].sum(axis=2)
        c = counts[r0:r1][:, idx].sum(axis=2)
        means = s / np.maximum(c, 1)
        lo[r0:r1] = np.quantile(means, 0.025, axis=1)
        hi[r0:r1] = np.quantile(means, 0.975, axis=1)
    return est, lo, hi


def read_text(lo: float, hi: float) -> str:
    if lo > TEXT_SUFFICIENT:
        return "SUFFICIENT"
    if hi < TEXT_INERT:
        return "INERT"
    return "PARTIAL"


def read_ir(lo: float, hi: float) -> str:
    if lo > IR_MAJOR:
        return "MAJOR"
    if hi < IR_MINOR:
        return "MINOR"
    return "PARTIAL"


def det_threshold(n: int, alpha: float = 0.05, floor: float = 0.01) -> int:
    for k in range(1, n + 1):
        if float(stats.beta.ppf(alpha, k, n - k + 1)) > floor:
            return k
    return n + 1


def read_det(k: int, n: int) -> dict[str, Any]:
    kstar = det_threshold(n)
    label = "DET_OK" if k == 0 else ("DET_UNATTAINABLE" if k >= kstar else "DET_NEAR")
    return {
        "k": k,
        "n": n,
        "k_star": kstar,
        "reading": label,
        "upper95_at_zero": round(1 - 0.05 ** (1 / n), 5),
    }


def joint_text(readings: Mapping[str, str]) -> str:
    vals = list(readings.values())
    suff, inert = vals.count("SUFFICIENT"), vals.count("INERT")
    if suff >= 2:
        return "REDUNDANT"
    if suff == 1 and inert == len(vals) - 1:
        return "SINGLE_SOURCE"
    if inert == len(vals):
        return "NEITHER"
    return "MIXED"


def compare(
    ref: Sequence[Mapping[str, Any]],
    other: Sequence[Mapping[str, Any]],
    key: Any = lambda r: (r["task"], r["pair"], r["step"]),
) -> dict[str, Any]:
    """Pair a reference cell's replies with another cell's by (task, pair, step)."""
    a = {key(r): r for r in ref if "error" not in r}
    b = {key(r): r for r in other if "error" not in r}
    keys = sorted(set(a) | set(b))
    both = [k for k in keys if k in a and k in b]
    missing = len(keys) - len(both)
    return {
        "tasks": [k[0] for k in both],
        "text": [int(a[k]["content_sha256"] != b[k]["content_sha256"]) for k in both],
        "ir": [int(a[k]["ir_sha256"] != b[k]["ir_sha256"]) for k in both],
        "missing": missing,
        "n": len(both),
        "void": len(keys) > 0 and missing / len(keys) > MISSING_VOID,
    }


def cell_reading(cmp: Mapping[str, Any], floor: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Text and IR readings of one cell (net of the paired floor when ``floor`` is given)."""
    out: dict[str, Any] = {"n": cmp["n"], "missing": cmp["missing"], "void": cmp["void"]}
    for level, reader in (("text", read_text), ("ir", read_ir)):
        values = np.asarray(cmp[level], dtype=float)
        if floor is not None:
            values = values - np.asarray(floor[level], dtype=float)
        b = bounds(cmp["tasks"], values)
        out[level] = {**b, "reading": "VOID" if cmp["void"] else reader(b["lo"], b["hi"])}
    return out


def validation(
    xs_tasks: Sequence[str],
    xs_text: Sequence[int],
    xs_ir: Sequence[int],
    s1a_tasks: Sequence[str],
    s1a_text: Sequence[int],
    s1a_ir: Sequence[int],
    boot: int = BOOT,
    seed: int = SEED,
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    flags = []
    for level, xv, sv in (("text", xs_text, s1a_text), ("ir", xs_ir, s1a_ir)):
        bs, bc = task_sums(xs_tasks, xv)
        ss, sc = task_sums(s1a_tasks, sv)
        d_lo, d_hi, d = diff_bounds(bs, bc, ss, sc, boot, seed)
        out[level] = {
            "stage_b": float(bs.sum() / bc.sum()),
            "s1a": float(ss.sum() / sc.sum()),
            "difference": d,
            "lo": d_lo,
            "hi": d_hi,
        }
        flags.append((d_lo, d_hi, d))
    if all(lo > -VAL_MARGIN and hi < VAL_MARGIN for lo, hi, _ in flags):
        out["reading"] = "VAL_PASS"
    elif any((lo > 0 or hi < 0) and abs(d) > VAL_FAIL_DIFF for lo, hi, d in flags):
        out["reading"] = "VAL_FAIL"
    else:
        out["reading"] = "VAL_UNRESOLVED"
    return out


def diff_bounds(
    bs: np.ndarray,
    bc: np.ndarray,
    ss: np.ndarray,
    sc: np.ndarray,
    boot: int = BOOT,
    seed: int = SEED,
) -> tuple[float, float, float]:
    rng = np.random.default_rng(seed)
    i = rng.integers(0, len(bs), size=(boot, len(bs)))
    j = rng.integers(0, len(ss), size=(boot, len(ss)))
    db = bs[i].sum(1) / bc[i].sum(1) - ss[j].sum(1) / sc[j].sum(1)
    d = float(bs.sum() / bc.sum() - ss.sum() / sc.sum())
    return float(np.quantile(db, 0.025)), float(np.quantile(db, 0.975)), d


def interaction(h_ab: float, h_a: float, h_b: float) -> float:
    """Observed joint hazard minus the independence prediction 1 - (1 - h_a)(1 - h_b)."""
    return h_ab - (1 - (1 - h_a) * (1 - h_b))
