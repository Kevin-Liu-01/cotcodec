"""The two-stage onset model and the D_w predictions under each removal (registration v2, 3.3).

Wave 1's step-kick model compounded an identical-history IR hazard per step, which contradicts
the mechanism: replies (thinking included) are passed back, so the first reply-text difference
makes every later request differ. This model has two stages per within-session pair:

1. **Text onset** at step T: with identical histories through step k-1, the reply texts differ
   at step k with hazard kappa_k (the per-source sufficiency hazards Stage B measures at step 1,
   and at step 2 as a secondary). Absorbing.
2. **Action divergence** at step U >= T: at the onset step the IR differs with probability pi;
   at each later step, while the IR is still identical, with the post-onset rate rho (a property
   of the policy and the tasks, estimated on S1a; assumed the same whatever source started the
   onset). An IR-identical pair ends together at step k with probability tau_k (both terminate;
   estimated on S1a); the step cap ends every pair at 15.

N = P(U never occurs) and D_w = (1 - N) q + e, with q the verdict discordance of IR-diverged
pairs (S1a: 0 of 227 IR-identical pairs were discordant) and e the environment term (Stage C).

``fit`` estimates kappa_k, pi, rho (constant) and tau_k from a group's pairs by event counts;
``survival`` runs the forward recursion; ``validate`` compares the model's IR-identity curve,
N and D_w with S1a's observed ones (in sample, and leave-one-group-out for rho and pi).
``predict`` turns Stage B's measured hazards for a removal arm into its predicted D_w: kappa_1
and pi from the arm's step-1 cell, kappa_k for k >= 2 from its step-2 cell (stationarity is
assumed; the bracket kappa_k>=3 in [kappa_2 lower, 1] is reported).
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

STEP_CAP = 15


@dataclass(frozen=True)
class Pair:
    task: str
    t: int | None  # first step whose reply text differs (None: never)
    u: int | None  # first step whose IR differs (None: never)
    end: int  # last step of an IR-identical pair (joint end), or the longer length otherwise
    discordant: int


def first_diff(
    sa: Sequence[Mapping[str, Any]], sb: Sequence[Mapping[str, Any]], field: str
) -> int | None:
    """The A0 doctor's rule: the first step whose ``field`` differs; if all shared steps agree
    but the lengths differ, the step after the shorter episode."""
    for x, y in zip(sa, sb, strict=False):
        if x[field] != y[field]:
            return int(x["k"])
    if len(sa) != len(sb):
        return min(len(sa), len(sb)) + 1
    return None


def pairs_from(
    rows: Sequence[Mapping[str, Any]], records: Sequence[Mapping[str, Any]], size: str, harness: str
) -> list[Pair]:
    """Within-session pairs of one size and harness from the A0 digest table and a1.jsonl."""
    key = lambda r: (r["size"], r["harness"], r["session"], r["task_id"], r["rerun"])  # noqa: E731
    d = {key(r): r for r in rows}
    y = {key(r): int(r.get("score") is not None and float(r["score"]) == 1.0) for r in records}
    tasks = sorted({r["task_id"] for r in records})
    out = []
    for s in ("S1", "S2"):
        for t in tasks:
            a, b = (size, harness, s, t, 1), (size, harness, s, t, 2)
            if a not in d or b not in d:
                continue
            sa, sb = d[a]["steps"], d[b]["steps"]
            text = first_diff(sa, sb, "rep")
            ir = first_diff(sa, sb, "ir")
            out.append(
                Pair(task=t, t=text, u=ir, end=max(len(sa), len(sb)), discordant=int(y[a] != y[b]))
            )
    return out


@dataclass
class Params:
    kappa: list[float]  # kappa[k-1] for k = 1..15 (text onset hazard)
    pi: float
    rho: float
    tau: list[float]  # tau[k-1]: joint end of an IR-identical pair at step k

    def as_dict(self) -> dict[str, Any]:
        return {
            "kappa": [round(x, 4) for x in self.kappa],
            "pi": round(self.pi, 4),
            "rho": round(self.rho, 4),
            "tau": [round(x, 4) for x in self.tau],
        }


def fit(pairs: Sequence[Pair], pool_kappa_from: int = 3) -> tuple[Params, dict[str, Any]]:
    """Event-count estimates. kappa_k is pooled for k >= ``pool_kappa_from`` (few pairs remain)."""
    on_n = [0] * STEP_CAP
    on_e = [0] * STEP_CAP
    pi_n = pi_e = 0
    rho_n = rho_e = 0
    tau_n = [0] * STEP_CAP
    tau_e = [0] * STEP_CAP
    for p in pairs:
        u = p.u if p.u is not None else math.inf
        t = p.t if p.t is not None else math.inf
        for k in range(1, STEP_CAP + 1):
            if k > u:
                break
            # an IR-identical pair still running at step k
            if k <= t:
                on_n[k - 1] += 1
                if k == t:
                    on_e[k - 1] += 1
                    pi_n += 1
                    pi_e += int(u == k)
            else:
                rho_n += 1
                rho_e += int(u == k)
            if u == k:
                break
            # identical through k: did both end here?
            tau_n[k - 1] += 1
            if p.u is None and p.end == k:
                tau_e[k - 1] += 1
                break
    kappa = []
    pooled_n = sum(on_n[pool_kappa_from - 1 :])
    pooled_e = sum(on_e[pool_kappa_from - 1 :])
    for k in range(1, STEP_CAP + 1):
        if k < pool_kappa_from:
            kappa.append(on_e[k - 1] / on_n[k - 1] if on_n[k - 1] else 0.0)
        else:
            kappa.append(pooled_e / pooled_n if pooled_n else 0.0)
    tau = [tau_e[k] / tau_n[k] if tau_n[k] else 0.0 for k in range(STEP_CAP)]
    tau[STEP_CAP - 1] = 1.0
    params = Params(
        kappa=kappa, pi=pi_e / pi_n if pi_n else 0.0, rho=rho_e / rho_n if rho_n else 0.0, tau=tau
    )
    counts = {
        "onset_at_risk": on_n,
        "onset_events": on_e,
        "pi": [pi_e, pi_n],
        "rho": [rho_e, rho_n],
        "tau_at_risk": tau_n,
        "tau_events": tau_e,
    }
    return params, counts


def survival(params: Params) -> dict[str, Any]:
    """Forward recursion: P(IR identical through step k) for k = 1..15, and N."""
    same, div, ended = (
        1.0,
        0.0,
        0.0,
    )  # IR-identical & text-identical / text-diverged; ended together
    curve = []
    for k in range(1, STEP_CAP + 1):
        kap = params.kappa[k - 1]
        onset = same * kap
        same_next = same * (1 - kap)
        div_next = div * (1 - params.rho) + onset * (1 - params.pi)
        alive = same_next + div_next
        end_k = alive * params.tau[k - 1]
        frac_same = same_next / alive if alive > 0 else 0.0
        same = (alive - end_k) * frac_same
        div = (alive - end_k) * (1 - frac_same)
        ended += end_k
        curve.append(same + div + ended)
    return {"identical_through": curve, "N": ended + same + div}


def discordance_q(pairs: Sequence[Pair]) -> float:
    diverged = [p for p in pairs if p.u is not None]
    return sum(p.discordant for p in diverged) / len(diverged) if diverged else 0.0


def observed_curve(pairs: Sequence[Pair]) -> list[float]:
    n = len(pairs)
    return [sum(1 for p in pairs if p.u is None or p.u > k) / n for k in range(1, STEP_CAP + 1)]


def validate(groups: Mapping[str, Sequence[Pair]], target: str) -> dict[str, Any]:
    """In-sample fit on ``target`` and a leave-one-group-out check: rho and pi from the other
    groups, kappa and tau from the target's own pairs."""
    pairs = groups[target]
    params, counts = fit(pairs)
    model = survival(params)
    obs = observed_curve(pairs)
    q = discordance_q(pairs)
    others = [p for g, ps in groups.items() if g != target for p in ps]
    p_other, _ = fit(others)
    loo = Params(kappa=params.kappa, pi=p_other.pi, rho=p_other.rho, tau=params.tau)
    loo_model = survival(loo)
    n_obs = sum(1 for p in pairs if p.u is None) / len(pairs)
    dw_obs = sum(p.discordant for p in pairs) / len(pairs)
    return {
        "group": target,
        "pairs": len(pairs),
        "params": params.as_dict(),
        "counts": counts,
        "observed_identical_through": [round(x, 4) for x in obs],
        "model_identical_through": [round(x, 4) for x in model["identical_through"]],
        "max_abs_gap": round(
            max(abs(a - b) for a, b in zip(obs, model["identical_through"], strict=True)), 4
        ),
        "N_observed": round(n_obs, 4),
        "N_model": round(model["N"], 4),
        "q": round(q, 4),
        "D_w_observed": round(dw_obs, 4),
        "D_w_model": round((1 - model["N"]) * q, 4),
        "leave_one_group_out": {
            "rho_pi_from": [g for g in groups if g != target],
            "rho": round(p_other.rho, 4),
            "pi": round(p_other.pi, 4),
            "model_identical_through": [round(x, 4) for x in loo_model["identical_through"]],
            "max_abs_gap": round(
                max(abs(a - b) for a, b in zip(obs, loo_model["identical_through"], strict=True)), 4
            ),
            "N_model": round(loo_model["N"], 4),
            "D_w_model": round((1 - loo_model["N"]) * q, 4),
        },
    }


def predict(
    kappa1: float,
    ir1: float,
    kappa2: float,
    *,
    rho: float,
    tau: Sequence[float],
    q: float,
    e: float = 0.0,
    kappa3: float | None = None,
) -> dict[str, float]:
    """Predicted N and D_w for a removal arm from its Stage B hazards: ``kappa1`` (text, step 1),
    ``ir1`` (IR, step 1; pi = ir1 / kappa1), ``kappa2`` (text, step 2; used for every k >= 2
    unless ``kappa3`` is given for k >= 3)."""
    pi = min(1.0, ir1 / kappa1) if kappa1 > 0 else 0.0
    k3 = kappa2 if kappa3 is None else kappa3
    kappa = [kappa1, kappa2] + [k3] * (STEP_CAP - 2)
    model = survival(Params(kappa=kappa, pi=pi, rho=rho, tau=list(tau)))
    return {
        "N": model["N"],
        "D_w": (1 - model["N"]) * q + e,
        "pi": pi,
        "identical_through_1": model["identical_through"][0],
    }


def predict_bracket(
    kappa1: float, ir1: float, kappa2: float, kappa2_lo: float, kappa2_hi: float, **kw: Any
) -> dict[str, Any]:
    """The prediction and its bracket over kappa_k>=3 in the step-2 interval [kappa2_lo, kappa2_hi]
    (stationarity beyond step 2 is an assumption; the bracket shows what it carries)."""
    mid = predict(kappa1, ir1, kappa2, **kw)
    a = predict(kappa1, ir1, kappa2, kappa3=kappa2_lo, **kw)
    b = predict(kappa1, ir1, kappa2, kappa3=kappa2_hi, **kw)
    return {
        "D_w": round(mid["D_w"], 4),
        "N": round(mid["N"], 4),
        "D_w_bracket": [round(min(a["D_w"], b["D_w"]), 4), round(max(a["D_w"], b["D_w"]), 4)],
    }


def refit_draws(
    pairs: Sequence[Pair], draws: int, seed: int = 42
) -> list[tuple[float, list[float], float]]:
    """(rho, tau, q) refitted on task-cluster bootstrap resamples of S1a's pairs."""
    import numpy as np

    rng = np.random.default_rng(seed)
    by_task: dict[str, list[Pair]] = {}
    for p in pairs:
        by_task.setdefault(p.task, []).append(p)
    tasks = sorted(by_task)
    out = []
    for _ in range(draws):
        pick = rng.integers(0, len(tasks), size=len(tasks))
        sample = [p for i in pick for p in by_task[tasks[i]]]
        params, _ = fit(sample)
        out.append((params.rho, params.tau, discordance_q(sample)))
    return out


def predict_interval(
    k1: Sequence[float],
    ir1: Sequence[float],
    k2: Sequence[float],
    s1a: Sequence[tuple[float, list[float], float]],
    e: float = 0.0,
) -> dict[str, float]:
    """Registered prediction interval: one prediction per bootstrap draw, pairing Stage B's
    resampled cell hazards (tasks resampled jointly across cells) with an independent S1a refit."""
    import numpy as np

    values = []
    for a, b, c, (rho, tau, q) in zip(k1, ir1, k2, s1a, strict=False):
        values.append(predict(a, b, c, rho=rho, tau=tau, q=q, e=e)["D_w"])
    arr = np.asarray(values)
    return {
        "median": float(np.median(arr)),
        "lo": float(np.quantile(arr, 0.025)),
        "hi": float(np.quantile(arr, 0.975)),
        "draws": len(arr),
    }
