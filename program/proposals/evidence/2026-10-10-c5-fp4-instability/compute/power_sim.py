#!/usr/bin/env python3
"""S1: operating characteristics of the registered Phase 1 decision rules (Monte Carlo).

Simulates the whole sequential design, including per-configuration learning-rate tuning:

  Stage 1a: BF16, MX-like (E2M1/S1) and NV-like (E2M1/S3); 5-point LR sweep (factor 2,
            one sweep seed, one extension point if the best is at an edge), quadratic
            refinement, then 3 fresh seeds at the tuned LR.
  Gate G1:  PASS iff L90(C_anchor) > 0 and C_anchor_hat >= 2.5 * sigma_hat
            (RCBD on the two FP4 configurations x 3 seeds plus BF16, residual df 4).
  Stage 1b: six more FP4 cells; 3-point sweep centred on the reference configuration's
            tuned LR (E8M0 cells on MX-like, UE4M3/BF16-scale cells on NV-like), up to
            two extension points, quadratic refinement, 3 fresh seeds.
  Verdicts on the 8 FP4 cells x 3 seeds (RCBD, residual df 14), precedence in this order:
     WITHIN_NOISE      omnibus F-test of the 8 cell means, p > 0.10
     GRID_OR_INTERACTION  INTERACTION_PRESENT (3-df grid x scale interaction F-test p < 0.05
                       and max |I_hat| >= 0.5 |C_fmt_hat|) or GRID_COMPARABLE (U90(D1) < 0)
     PRIOR_SURVIVES    SCALE_DOMINATES (L90(D1) > 0) and SMALL_INTERACTION (every interaction
                       contrast has U90(|I|) < C_fmt_hat) and not INTERACTION_PRESENT
     SCALE_DOMINATES_INTERACTION_UNRESOLVED  L90(D1) > 0 otherwise
     INDETERMINATE     otherwise
     (D1 = C_fmt - 2 Delta_G; contrasts as in doe.py; an earlier draft of these rules read the
     three interaction contrasts without the omnibus gate and had a false GRID_OR_INTERACTION
     rate near 0.3 under the null, and required interaction CIs inside +-0.5 C_fmt, which no
     scenario with sigma >= 0.004 could meet; both are recorded in the proposal)
  Separate registered predictions (Holm across the two, one-sided alpha 0.05):
     P_int_fmt: I_fmt > 0 and P_int_blk: I_blk > 0 (numerics-predicted INT4 penalty from
     power-of-two scales). CONFIRMED if the Holm-adjusted one-sided test rejects; REFUTED if
     U90 < 0; else UNRESOLVED.

Per-run final loss = mu_cell + tuning bias + seed block + residual. Tuning bias
= a * (x_chosen - x_opt)^2 in log2(LR) units; x_opt differs by configuration (SD 0.5
grid steps). Every distribution and effect size is an ASSUMPTION, anchored where possible:
sigma 0.002 is the recomputed seed SD of arXiv 2505.19115 Table 4 (125M, 30B tokens);
the block-size delta at 8B is 0.0151 (arXiv 2609.02846 Table 10, one seed).

Usage: python power_sim.py <out.json>     (seeds 42, 43, 44; about 1 minute)
"""

from __future__ import annotations

import itertools
import json
import sys

import numpy as np
from scipy import stats

CELLS = [f"{g}/{s}" for g in ("E2M1", "INT4") for s in ("S1", "S2", "S3", "S5")]
REF = {
    "E2M1/S1": "MX",
    "E2M1/S3": "NV",
    "E2M1/S2": "MX",
    "INT4/S1": "MX",
    "INT4/S2": "MX",
    "E2M1/S5": "NV",
    "INT4/S3": "NV",
    "INT4/S5": "NV",
}


def scenario(name: str, m: float) -> dict[str, float]:
    """True cell means at the optimal LR, relative to E2M1/S3 (nats)."""
    e = {"S1": 0.0, "S2": 0.0, "S3": 0.0, "S5": 0.0}
    i = dict(e)
    if name == "null":
        pass
    elif name == "prior_additive":  # scale dominates, small additive grid effect
        e = {"S1": 0.020, "S2": 0.012, "S3": 0.0, "S5": 0.004}
        i = {k: v + 0.003 for k, v in e.items()}
    elif (
        name == "qsnr_interaction"
    ):  # numerics-predicted: INT4 penalised by power-of-two scales only
        e = {"S1": 0.012, "S2": 0.009, "S3": 0.0, "S5": 0.002}
        i = {"S1": 0.030, "S2": 0.020, "S3": -0.003, "S5": 0.000}
    elif name == "grid_additive":  # grid effect comparable to scale, additive
        e = {"S1": 0.010, "S2": 0.006, "S3": 0.0, "S5": 0.002}
        i = {k: v + 0.010 for k, v in e.items()}
    else:
        raise ValueError(name)
    return {
        **{f"E2M1/{k}": m * v for k, v in e.items()},
        **{f"INT4/{k}": m * v for k, v in i.items()},
    }


def tune(rng, R, x_opt, center, npts, a, sig_sweep, max_ext):
    """Vectorised LR sweep over R replicates; returns the chosen log2 LR (continuous)."""
    half = (npts - 1) // 2
    offs = np.arange(-half, half + 1, dtype=float)
    grid = center[:, None] + offs[None, :]
    loss = a * (grid - x_opt[:, None]) ** 2 + rng.normal(0, sig_sweep, grid.shape)
    for _ in range(max_ext):  # extend on the side where the best point sits at an edge
        b = loss.argmin(axis=1)
        lo_edge, hi_edge = b == 0, b == grid.shape[1] - 1
        new_lo = grid[:, 0] - 1
        new_hi = grid[:, -1] + 1
        nl = a * (new_lo - x_opt) ** 2 + rng.normal(0, sig_sweep, R)
        nh = a * (new_hi - x_opt) ** 2 + rng.normal(0, sig_sweep, R)
        grid = np.column_stack(
            [np.where(lo_edge, new_lo, np.nan), grid, np.where(hi_edge, new_hi, np.nan)]
        )
        loss = np.column_stack([np.where(lo_edge, nl, np.inf), loss, np.where(hi_edge, nh, np.inf)])
    b = np.nanargmin(np.where(np.isnan(grid), np.inf, loss), axis=1)
    rows = np.arange(R)
    xb = grid[rows, b]
    # quadratic refinement through the best point and its two neighbours (if both exist)
    bl = np.clip(b - 1, 0, grid.shape[1] - 1)
    bh = np.clip(b + 1, 0, grid.shape[1] - 1)
    yl, y0, yh = loss[rows, bl], loss[rows, b], loss[rows, bh]
    ok = (bl != b) & (bh != b) & np.isfinite(yl) & np.isfinite(yh)
    denom = yl - 2 * y0 + yh
    shift = np.where(ok & (denom > 0), 0.5 * (yl - yh) / np.where(denom == 0, 1, denom), 0.0)
    return xb + np.clip(shift, -0.5, 0.5)


def rcbd(y: np.ndarray):
    """y: (R, C, S). Returns cell means (R, C), residual SD (R,), residual df, F p-value (R,)."""
    R, C, S = y.shape
    gm = y.mean(axis=(1, 2), keepdims=True)
    cm = y.mean(axis=2, keepdims=True)
    sm = y.mean(axis=1, keepdims=True)
    resid = y - cm - sm + gm
    df = (C - 1) * (S - 1)
    ss_res = (resid**2).sum(axis=(1, 2))
    sigma = np.sqrt(ss_res / df)
    ss_c = S * ((cm - gm) ** 2).sum(axis=(1, 2))
    F = (ss_c / (C - 1)) / (ss_res / df)
    p = stats.f.sf(F, C - 1, df)
    return cm[..., 0], sigma, df, p


def run(scn, m, sigma, rho, a, R, rng):
    sb, se = sigma * np.sqrt(rho), sigma * np.sqrt(1 - rho)
    mu = scenario(scn, m)
    x_base = np.zeros(R)
    x_opt = {c: x_base + rng.normal(0, 0.5, R) for c in CELLS}
    # Stage 1a tuning (5 points centred on the BF16-informed centre 0; one extension)
    chosen = {}
    for c in ("E2M1/S1", "E2M1/S3"):
        chosen[c] = tune(rng, R, x_opt[c], x_base, 5, a, sigma, 1)
    seed_eff = rng.normal(0, sb, (R, 3))
    y = {}
    for c in ("E2M1/S1", "E2M1/S3"):
        bias = a * (chosen[c] - x_opt[c]) ** 2
        y[c] = mu[c] + bias[:, None] + seed_eff + rng.normal(0, se, (R, 3))
    y_bf = seed_eff + rng.normal(0, se, (R, 3)) - 0.05  # BF16 baseline (level irrelevant)
    ya = np.stack([y["E2M1/S1"], y["E2M1/S3"], y_bf], axis=1)
    cm, s_hat, df_a, _ = rcbd(ya)
    c_anchor = cm[:, 0] - cm[:, 1]
    se_anchor = s_hat * np.sqrt(2 / 3)
    t_a = stats.t.ppf(0.95, df_a)
    g1 = (c_anchor - t_a * se_anchor > 0) & (c_anchor >= 2.5 * s_hat)
    # Stage 1b
    for c in CELLS:
        if c in chosen:
            continue
        center = chosen["E2M1/S1"] if REF[c] == "MX" else chosen["E2M1/S3"]
        chosen[c] = tune(rng, R, x_opt[c], center, 3, a, sigma, 2)
        bias = a * (chosen[c] - x_opt[c]) ** 2
        y[c] = mu[c] + bias[:, None] + seed_eff + rng.normal(0, se, (R, 3))
    yb = np.stack([y[c] for c in CELLS], axis=1)
    cm, s_hat, df_b, p_f = rcbd(yb)
    t_b = stats.t.ppf(0.95, df_b)
    k = {c: i for i, c in enumerate(CELLS)}

    def g(c):
        return cm[:, k[c]]

    dG = np.mean([g(f"INT4/{s}") - g(f"E2M1/{s}") for s in ("S1", "S2", "S3", "S5")], axis=0)
    cfmt = 0.5 * (g("E2M1/S2") + g("INT4/S2") - g("E2M1/S3") - g("INT4/S3"))
    d1 = cfmt - 2 * dG
    se_d1 = s_hat * 1.0
    inter = {
        "I_blk": (g("INT4/S1") - g("INT4/S2")) - (g("E2M1/S1") - g("E2M1/S2")),
        "I_fmt": (g("INT4/S2") - g("INT4/S3")) - (g("E2M1/S2") - g("E2M1/S3")),
        "I_iso": (g("INT4/S5") - g("INT4/S3")) - (g("E2M1/S5") - g("E2M1/S3")),
    }
    se_i = s_hat * np.sqrt(4 / 3)
    noise = p_f > 0.10
    # 3-df grid x scale interaction F-test (2 x 4 factorial inside the RCBD)
    mg = np.stack(
        [cm[:, [k[f"{gg}/{s}"] for s in ("S1", "S2", "S3", "S5")]] for gg in ("E2M1", "INT4")],
        axis=1,
    )  # (R,2,4)
    gmn = mg.mean(axis=(1, 2), keepdims=True)
    ss_int = 3 * (
        (mg - mg.mean(axis=2, keepdims=True) - mg.mean(axis=1, keepdims=True) + gmn) ** 2
    ).sum(axis=(1, 2))
    f_int = (ss_int / 3) / s_hat**2
    p_int = stats.f.sf(f_int, 3, df_b)
    max_i = np.max(np.abs(np.stack(list(inter.values()))), axis=0)
    interaction_present = (p_int < 0.05) & (max_i >= 0.5 * np.abs(cfmt))
    small_int = cfmt > 0
    for v in inter.values():
        small_int &= (np.abs(v) + t_b * se_i) < cfmt
    grid_comparable = d1 + t_b * se_d1 < 0
    scale_dom = d1 - t_b * se_d1 > 0
    grid_v = ~noise & (interaction_present | grid_comparable)
    prior_v = ~noise & ~grid_v & scale_dom & small_int
    sdiu = ~noise & ~grid_v & ~prior_v & scale_dom
    indet = ~noise & ~grid_v & ~prior_v & ~sdiu
    t1 = stats.t.ppf(0.95, df_b)
    t2 = stats.t.ppf(0.975, df_b)
    preds = {}
    for name in ("I_fmt", "I_blk"):
        v = inter[name]
        preds[name] = {"z": v / se_i, "lo90": v - t1 * se_i, "hi90": v + t1 * se_i}
    # Holm across the two one-sided tests at alpha 0.05: smaller p tested at 0.025, larger at 0.05
    z1, z2 = preds["I_fmt"]["z"], preds["I_blk"]["z"]
    first_is_fmt = z1 >= z2
    rej_first = np.where(first_is_fmt, z1, z2) > t2
    rej_second = rej_first & (np.where(first_is_fmt, z2, z1) > t1)
    conf_fmt = np.where(first_is_fmt, rej_first, rej_second)
    conf_blk = np.where(first_is_fmt, rej_second, rej_first)
    ref_fmt = preds["I_fmt"]["hi90"] < 0
    ref_blk = preds["I_blk"]["hi90"] < 0
    tb_all = np.concatenate([a * (chosen[c] - x_opt[c]) ** 2 for c in CELLS])
    return {
        "P_G1_pass": float(g1.mean()),
        "stage1b_given_G1": {
            name: (float(arr[g1].mean()) if g1.any() else None)
            for name, arr in (
                ("WITHIN_NOISE", noise),
                ("GRID_OR_INTERACTION", grid_v),
                ("PRIOR_SURVIVES", prior_v),
                ("SCALE_DOMINATES_INTERACTION_UNRESOLVED", sdiu),
                ("INDETERMINATE", indet),
            )
        },
        "stage1b_unconditional_if_run": {
            "WITHIN_NOISE": float(noise.mean()),
            "GRID_OR_INTERACTION": float(grid_v.mean()),
            "PRIOR_SURVIVES": float(prior_v.mean()),
            "SCALE_DOMINATES_INTERACTION_UNRESOLVED": float(sdiu.mean()),
            "INDETERMINATE": float(indet.mean()),
        },
        "P_int_fmt": {
            "CONFIRMED": float(conf_fmt.mean()),
            "REFUTED": float(ref_fmt.mean()),
            "true_I_fmt": round(mu["INT4/S2"] - mu["INT4/S3"] - mu["E2M1/S2"] + mu["E2M1/S3"], 4),
        },
        "P_int_blk": {
            "CONFIRMED": float(conf_blk.mean()),
            "REFUTED": float(ref_blk.mean()),
            "true_I_blk": round(mu["INT4/S1"] - mu["INT4/S2"] - mu["E2M1/S1"] + mu["E2M1/S2"], 4),
        },
        "tuning_bias_nats": {"mean": float(tb_all.mean()), "p95": float(np.quantile(tb_all, 0.95))},
        "true_C_anchor": round(mu["E2M1/S1"] - mu["E2M1/S3"], 4),
    }


def main() -> None:
    R = 2000
    out = {
        "script": "power_sim.py",
        "replicates_per_combo": R,
        "seeds": [42, 43, 44],
        "assumptions": __doc__,
        "grid": [],
    }
    combos = list(
        itertools.product(
            ["null", "prior_additive", "qsnr_interaction", "grid_additive"],
            [0.5, 1.0, 2.0],
            [0.002, 0.004, 0.008],
            [0.0, 0.5],
            [0.005, 0.02],
        )
    )
    for j, (scn, m, sigma, rho, a) in enumerate(combos):
        if scn == "null" and m != 1.0:
            continue
        rng = np.random.default_rng([42, 43, 44, j])
        res = run(scn, m, sigma, rho, a, R, rng)
        out["grid"].append(
            {
                "scenario": scn,
                "effect_multiplier": m,
                "sigma": sigma,
                "rho_seed": rho,
                "lr_curvature_a": a,
                **res,
            }
        )
    # analytic: SR unbiasedness test (registered Phase 0 PG4)
    V, K = 4096, 2**16
    out["sr_unbiasedness_test"] = {
        "values_per_grid": V,
        "draws_per_value": K,
        "per_value_SE_max_ulp": 0.5 / np.sqrt(K),
        "aggregate_SE_max_ulp": 0.5 / np.sqrt(V * K),
        "aggregate_threshold_ulp": 1e-3,
        "detectable_bias_ulp_at_power_0.999": round(
            float((stats.norm.ppf(0.9995) + stats.norm.ppf(0.999)) * 0.5 / np.sqrt(V * K)), 6
        ),
        "few_bit_bias_examples_ulp": {"2-bit SRFastest": 0.124, "3-bit, BF16 inputs": 0.047},
        "per_value_bonferroni_alpha": 0.001 / V,
    }
    # exact null distribution of Spearman's rho for n = 8 cells (registered prediction P7)
    perms = np.array(list(itertools.permutations(range(8))))
    d2 = ((perms - np.arange(8)) ** 2).sum(axis=1)
    rho = 1 - 6 * d2 / (8 * (64 - 1))
    crit = {}
    for alpha in (0.05, 0.025):
        for c in sorted(set(np.round(rho, 6))):
            if (rho >= c - 1e-9).mean() <= alpha:
                crit[f"one_sided_{alpha}"] = {
                    "rho_critical": float(c),
                    "exact_p": float((rho >= c - 1e-9).mean()),
                }
                break
    out["spearman_n8_exact"] = {"n_permutations": int(len(rho)), **crit}
    with open(sys.argv[1], "w") as fh:
        json.dump(out, fh, indent=1)
    print("spearman n=8:", out["spearman_n8_exact"])
    for r in out["grid"]:
        if r["rho_seed"] == 0.5 and r["lr_curvature_a"] == 0.02:
            s = r["stage1b_given_G1"]
            print(
                f"{r['scenario']:17s} m={r['effect_multiplier']:.1f} sigma={r['sigma']:.3f} G1={r['P_G1_pass']:.2f} | "
                f"noise {s['WITHIN_NOISE'] if s['WITHIN_NOISE'] is None else round(s['WITHIN_NOISE'], 2)} "
                f"grid {s['GRID_OR_INTERACTION'] if s['GRID_OR_INTERACTION'] is None else round(s['GRID_OR_INTERACTION'], 2)} "
                f"prior {s['PRIOR_SURVIVES'] if s['PRIOR_SURVIVES'] is None else round(s['PRIOR_SURVIVES'], 2)} | "
                f"sdiu {s['SCALE_DOMINATES_INTERACTION_UNRESOLVED'] if s['SCALE_DOMINATES_INTERACTION_UNRESOLVED'] is None else round(s['SCALE_DOMINATES_INTERACTION_UNRESOLVED'], 2)} | "
                f"Pfmt {r['P_int_fmt']['CONFIRMED']:.2f}/{r['P_int_fmt']['REFUTED']:.2f} Pblk {r['P_int_blk']['CONFIRMED']:.2f} | "
                f"U-run noise {r['stage1b_unconditional_if_run']['WITHIN_NOISE']:.2f} grid {r['stage1b_unconditional_if_run']['GRID_OR_INTERACTION']:.2f}"
            )


if __name__ == "__main__":
    main()
