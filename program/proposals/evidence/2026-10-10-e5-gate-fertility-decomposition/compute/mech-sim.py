#!/usr/bin/env python3
"""S1: does the per-word decay clamp identify the decay share where the r = 2 rescale cannot?

A NumPy gated delta-rule memory (the GDN transition S_t = a_t S_{t-1}(I - b_t k_t k_t^T)
+ b_t v_t k_t^T, one head, d_k = d_v = 48) stores K facts, then reads a canonical
retention span of N = 128 tokens, then answers a 4-way forced choice from S k_target.
Re-segmentation to fertility f splits each span token into m pieces (random refinement,
total round(f N)). Six worlds set how pieces behave:

  lambda  piece log-decay g_piece = g_token / m**lambda  (0: per-token clock; 1: gates
          self-normalise, so the pieces of a token decay exactly like the token)
  rho     piece key/value = normalise(rho * parent + sqrt(1 - rho**2) * noise)
          (1: duplicates of the parent write; 0: independent new writes)
  wnorm   piece write strength 1 - (1 - b)**(1/m) (m duplicate writes equal one write)
          instead of b

Arms per episode (paired, same random draws): CAN (f = 1), NAT(f), CLAMP(f) (piece
log-decays rescaled so each token's pieces sum to the token's canonical log-decay, the
registered clamp), and R2 (every log-decay halved, the dossier's r = 2) at f = 1 and 2.7.

What the simulation can show: whether NIE = Y(clamp) - Y(native) is about TE in a
pure-clock world, exactly 0 in a world whose gates self-normalise, and whether the r = 2
contrast dG(f) = G(f) - G(1), G = Y(r = 2) - Y(r = 1), is 0 in a world with no decay
share. Effect magnitudes are not calibrated to any real checkpoint; only signs and zeros
are evidence. Seeds 42, 43 and 44 give three independent replicates of n = 600
episodes per load.

Usage: python mech-sim.py <out.json>
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import estimator as est  # noqa: E402

D = 48
N_SPAN = 128
N_EPI = 600
SEEDS = (42, 43, 44)
FS = (1.5, 2.0, 2.7)
LOADS = (1, 4)
MEAN_G = 0.7 / N_SPAN  # canonical span keeps about exp(-0.7) of a fact
FACT_BETA = 0.95
FACT_G = 0.001
NOISE = 0.10
TEMP = 0.1

WORLDS = {
    "W1_per_token_clock": dict(lam=0.0, rho=1.0, wnorm=True),
    "W2_pure_interference": dict(lam=1.0, rho=0.0, wnorm=False),
    "W3_clock_and_interference": dict(lam=0.0, rho=0.0, wnorm=False),
    "W4_null": dict(lam=1.0, rho=1.0, wnorm=True),
    "W5_legacy_duplicates": dict(lam=0.0, rho=1.0, wnorm=False),
    "W6_partial": dict(lam=0.5, rho=0.5, wnorm=False),
}


def unit(x: np.ndarray) -> np.ndarray:
    return x / np.linalg.norm(x, axis=-1, keepdims=True)


def scan(keys, vals, beta, logdecay):
    """keys/vals [B, T, D], beta/logdecay [B, T] -> final state [B, D, D]."""
    b, t, _ = keys.shape
    keys, vals = keys.astype(np.float32), vals.astype(np.float32)
    beta, alpha = beta.astype(np.float32), np.exp(logdecay).astype(np.float32)
    s = np.zeros((b, D, D), dtype=np.float32)
    for i in range(t):
        k, v = keys[:, i], vals[:, i]
        sk = np.matmul(s, k[:, :, None])  # [B, D, 1]
        bi, ai = beta[:, i, None, None], alpha[:, i, None, None]
        s = ai * (s - bi * sk * k[:, None, :]) + bi * v[:, :, None] * k[:, None, :]
    return s.astype(np.float64)


def refine_counts(rng, n_epi: int, n_tok: int, f: float) -> np.ndarray:
    extra = round(f * n_tok) - n_tok
    m = np.ones((n_epi, n_tok), dtype=int)
    for e in range(n_epi):
        np.add.at(m[e], rng.integers(0, n_tok, extra), 1)
    return m


def episode_bank(rng, k_facts: int):
    fk = unit(rng.standard_normal((N_EPI, k_facts, D)))
    fv = unit(rng.standard_normal((N_EPI, k_facts, D)))
    tk = unit(rng.standard_normal((N_EPI, N_SPAN, D)))
    tv = unit(rng.standard_normal((N_EPI, N_SPAN, D)))
    tb = rng.uniform(0.1, 0.4, (N_EPI, N_SPAN))
    tg = -rng.exponential(MEAN_G, (N_EPI, N_SPAN))
    target = rng.integers(0, k_facts, N_EPI)
    foils = unit(rng.standard_normal((N_EPI, 3, D)))  # fresh foils for K = 1
    noise = rng.standard_normal((N_EPI, 4))
    return dict(fk=fk, fv=fv, tk=tk, tv=tv, tb=tb, tg=tg, target=target, foils=foils, noise=noise)


def build_span(rng, bank, m, world, mode):
    """Return keys, vals, beta, logdecay for the span; mode in native|clamp."""
    n_epi = m.shape[0]
    total = m.sum(axis=1)
    assert np.all(total == total[0])
    t = int(total[0])
    lam, rho, wnorm = world["lam"], world["rho"], world["wnorm"]
    parent = np.repeat(np.arange(N_SPAN)[None, :], n_epi, 0)
    idx = np.stack([np.repeat(np.arange(N_SPAN), m[e]) for e in range(n_epi)])
    mm = np.take_along_axis(m, idx, 1)
    pk = np.take_along_axis(bank["tk"], idx[..., None], 1)
    pv = np.take_along_axis(bank["tv"], idx[..., None], 1)
    if rho < 1.0:
        nz_k = unit(rng.standard_normal((n_epi, t, D)))
        nz_v = unit(rng.standard_normal((n_epi, t, D)))
        single = (mm == 1)[..., None]  # an unsplit token keeps its canonical write
        pk = np.where(single, pk, unit(rho * pk + math.sqrt(1 - rho ** 2) * nz_k))
        pv = np.where(single, pv, unit(rho * pv + math.sqrt(1 - rho ** 2) * nz_v))
    b = np.take_along_axis(bank["tb"], idx, 1)
    if wnorm:
        b = 1 - (1 - b) ** (1.0 / mm)
    g_tok = np.take_along_axis(bank["tg"], idx, 1)
    g = g_tok / mm ** lam
    if mode == "clamp":
        g = g_tok / mm  # registered clamp: pieces of a token sum to the token's canonical log-decay
    del parent
    return pk, pv, b, g


def run_arm(rng_pieces, bank, k_facts, m, world, mode, r):
    n_epi = bank["fk"].shape[0]
    if m is None:
        sk, sv, sb, sg = bank["tk"], bank["tv"], bank["tb"], bank["tg"]
    else:
        sk, sv, sb, sg = build_span(rng_pieces, bank, m, world, mode)
    keys = np.concatenate([bank["fk"], sk], 1)
    vals = np.concatenate([bank["fv"], sv], 1)
    beta = np.concatenate([np.full((n_epi, k_facts), FACT_BETA), sb], 1)
    logd = np.concatenate([np.full((n_epi, k_facts), -FACT_G), sg], 1) / r
    s = scan(keys, vals, beta, logd)
    q = bank["fk"][np.arange(n_epi), bank["target"]]
    o = np.einsum("bvk,bk->bv", s, q)
    tv = bank["fv"][np.arange(n_epi), bank["target"]]
    if k_facts >= 4:
        others = np.stack([np.delete(bank["fv"][e], bank["target"][e], 0)[:3] for e in range(n_epi)])
    else:
        others = bank["foils"]
    cands = np.concatenate([tv[:, None], others], 1)
    scores = np.einsum("bcv,bv->bc", cands, o) + NOISE * bank["noise"]
    correct = (scores.argmax(1) == 0).astype(float) * 100.0
    z = scores / TEMP
    logp = z[:, 0] - np.log(np.exp(z - z.max(1, keepdims=True)).sum(1)) - z.max(1)
    return correct, logp


def main() -> int:
    out_path = Path(sys.argv[1])
    t0 = time.time()
    res = {"params": dict(D=D, N_SPAN=N_SPAN, N_EPI=N_EPI, SEEDS=SEEDS, FS=FS, LOADS=LOADS, MEAN_G=MEAN_G,
                          FACT_BETA=FACT_BETA, FACT_G=FACT_G, NOISE=NOISE, TEMP=TEMP, worlds=WORLDS),
           "worlds": {}}
    for wname, world in WORLDS.items():
        wres = {}
        for seed in SEEDS:
            rng = np.random.default_rng([seed, 7])
            seed_res = {}
            per_k_nie = {f: [] for f in FS}
            per_k_te = {f: [] for f in FS}
            for k_facts in LOADS:
                bank = episode_bank(rng, k_facts)
                can, can_lp = run_arm(None, bank, k_facts, None, world, "native", 1.0)
                can_r2, _ = run_arm(None, bank, k_facts, None, world, "native", 2.0)
                cells = {"CAN": can.mean(), "CAN_r2": can_r2.mean(), "by_f": {}}
                for f in FS:
                    m = refine_counts(np.random.default_rng([seed, int(f * 10), k_facts]), N_EPI, N_SPAN, f)
                    piece_seed = [seed, int(f * 10), k_facts, 99]
                    nat, nat_lp = run_arm(np.random.default_rng(piece_seed), bank, k_facts, m, world, "native", 1.0)
                    clm, clm_lp = run_arm(np.random.default_rng(piece_seed), bank, k_facts, m, world, "clamp", 1.0)
                    r2 = None
                    if f == 2.7:  # the dossier's r = 2 contrast is computed at the primary f only
                        r2, _ = run_arm(np.random.default_rng(piece_seed), bank, k_facts, m, world, "native", 2.0)
                    te, nie = can - nat, clm - nat
                    per_k_nie[f].append(nie)
                    per_k_te[f].append(te)
                    cells["by_f"][str(f)] = {
                        "NAT": nat.mean(), "CLAMP": clm.mean(), "R2": None if r2 is None else r2.mean(),
                        "TE": te.mean(), "NIE": nie.mean(), "NDE": (can - clm).mean(),
                        "share": (nie.mean() / te.mean()) if abs(te.mean()) > 1e-9 else None,
                        "dG_r2": None if r2 is None else (r2.mean() - nat.mean()) - (can_r2.mean() - can.mean()),
                        "TE_logp": float((can_lp - nat_lp).mean()), "NIE_logp": float((clm_lp - nat_lp).mean()),
                        "discordance_clamp": float((nie != 0).mean()),
                    }
                seed_res[f"K{k_facts}"] = cells
            # registered primary reading at f_p = 2.7 (each episode its own cluster in the simulation)
            fp = 2.7
            nie_pool = [np.array([(a + b) / 2.0 / math.log(fp)]) for a, b in zip(*per_k_nie[fp])]
            te_pool = [np.array([(a + b) / 2.0 / math.log(fp)]) for a, b in zip(*per_k_te[fp])]
            beta = est.cluster_normal(nie_pool)
            te_i = est.cluster_normal(te_pool)
            reading = "NO_COST" if est.no_cost(te_i) else est.decide_subject(beta)
            seed_res["primary"] = {"beta": beta.__dict__, "te_per_logf": te_i.__dict__, "reading": reading,
                                   "share_at_2.7": (beta.point / te_i.point) if abs(te_i.point) > 1e-9 else None}
            wres[str(seed)] = seed_res
        res["worlds"][wname] = wres
        p = [wres[str(s)]["primary"] for s in SEEDS]
        print(wname, [(round(x["beta"]["point"], 2), round(x["te_per_logf"]["point"], 2), x["reading"]) for x in p],
              "dG_r2(2.7,K4):", [round(wres[str(s)]["K4"]["by_f"]["2.7"]["dG_r2"], 2) for s in SEEDS],
              "CAN K4:", [round(wres[str(s)]["K4"]["CAN"], 1) for s in SEEDS], flush=True)
    res["elapsed_s"] = round(time.time() - t0, 1)
    out_path.write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
