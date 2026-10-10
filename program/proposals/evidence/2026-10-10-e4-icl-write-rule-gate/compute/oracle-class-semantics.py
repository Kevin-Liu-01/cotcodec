#!/usr/bin/env python3
"""E4 gate, CPU check S1: semantics of the nested oracle state classes.

A linear surrogate of the read path, not a model run. It answers three
questions about the instrument, never about the 1.3B teacher:

1. KILL A (kill-shot cell, 2026-10-09): with the legacy rank-8 factorised
   port P, every key and every probe read lies in one 8-d subspace, so the
   key-span state class and the free state class give identical reads for
   any teacher. Expected: D_span = 0 for every synthetic teacher.
2. The repair (full-rank P; 32-d here for CPU time): the span constraint is non-vacuous, and the
   nested classes recover the generating teacher type (a model-recovery
   check at the oracle level): a family-constant teacher gives ES ~ 0; key-span
   teachers (first-order, fixed-preconditioned, recursive least squares,
   lookup) give D_span(B) ~ 0; retrieval and value-directed teachers give
   D_span(B) > 0.
3. span(I) versus span(B): a teacher that writes along a fixed preconditioner
   B* k is out of span(I) but inside span(B) once B is fitted on other
   episodes. B is fitted with a ridge penalty toward I and then chosen between
   I and the fitted B by held-out error on the development episodes, as the
   registration specifies; D_span_B uses the chosen B.

Surrogate: student output change G M P h(q) with G (m x w) fixed; squared
error stands in for KL. Oracles are fitted on 16 fit probes per episode and
scored on 8 held-out probes (lookup: the 8 bound names under a third
template, i.e. jittered demonstration inputs; fitting uses two others). All
randomness is seeded from the scenario key; output is deterministic.

Usage: python oracle-class-semantics.py <out.json> [processes]
"""

from __future__ import annotations

import hashlib
import json
import sys
import zlib

import numpy as np

D_B = 128  # residual width of the surrogate (the pilot's is 2048)
W = 32  # interface width (the pilot's is 64; reduced for CPU time)
M_OUT = 64  # output directions (stand-in for the vocabulary logits)
N_DEMO = 8
N_FIT = 16
N_EVAL = 8
RANK = 8
N_EP = 12  # episodes per family (6 B-fit, 6 evaluation)
N_FAM = 2
RIDGE = 1e-3
NOISE = 0.02


def rng_for(*key: object) -> np.random.Generator:
    return np.random.default_rng(zlib.crc32(repr(key).encode()))


def residual_cov(rng: np.random.Generator) -> np.ndarray:
    """Anisotropic residual covariance with one outlier direction."""
    q, _ = np.linalg.qr(rng.standard_normal((D_B, D_B)))
    spec = 1.0 / (1.0 + np.arange(D_B)) ** 0.6
    spec[0] = 25.0  # the transformer outlier principal direction
    return (q * spec) @ q.T


def make_port(rng: np.random.Generator, cov: np.ndarray, degenerate: bool) -> np.ndarray:
    """P (W x D_B): whitened full-rank 64-d map, or the legacy rank-8 factorised map."""
    evals, evecs = np.linalg.eigh(cov)
    whiten = (evecs / np.sqrt(evals)) @ evecs.T
    if degenerate:
        a = rng.standard_normal((W, RANK))
        b = rng.standard_normal((RANK, D_B))
        return a @ b @ whiten / np.sqrt(D_B)
    basis, _ = np.linalg.qr(rng.standard_normal((D_B, W)))
    return basis.T @ whiten


def ridge_solve(a: np.ndarray, b: np.ndarray, lam: float = RIDGE) -> np.ndarray:
    """Ridge with the penalty scaled to the design (lam times the mean diagonal of A^T A)."""
    ata = a.T @ a
    scale = lam * float(np.trace(ata)) / ata.shape[0] + 1e-12
    return np.linalg.solve(ata + scale * np.eye(a.shape[1]), a.T @ b)


def fit_const(g, xs, ts):
    """M (W x W) minimising sum ||G M x - t||^2 over all (x, t)."""
    x = np.concatenate(xs)  # (n, W)
    t = np.concatenate(ts)  # (n, M_OUT)
    # vec trick: G M x = (x^T kron G) vec(M); solve via normal equations in M
    gtg = g.T @ g
    xtx = x.T @ x
    rhs = g.T @ t.T @ x  # (W, W)
    # solve gtg M xtx + lam M = rhs (Sylvester-like), eigen-decompose both
    e1, v1 = np.linalg.eigh(gtg)
    e2, v2 = np.linalg.eigh(xtx)
    r = v1.T @ rhs @ v2
    m = r / (np.outer(e1, e2) + RIDGE)
    return v1 @ m @ v2.T


def fit_span(g, x_fit, r_fit, z_dirs):
    """Episode part U (BK)^T: U (W x RANK) free, row space fixed by z_dirs (W x RANK).

    The row space is re-expressed in an orthonormal basis (QR) first, as the
    registration specifies, so conditioning does not depend on the keys' Gram matrix.
    """
    z_dirs, _ = np.linalg.qr(z_dirs)
    z = x_fit @ z_dirs  # (n, RANK): coordinates of probe reads on the write directions
    # G U z_q = (z_q^T kron G) vec(U)
    a = np.einsum("nr,mw->nmrw", z, g).reshape(z.shape[0] * M_OUT, RANK * W)
    u = ridge_solve(a, r_fit.reshape(-1)).reshape(RANK, W).T
    return u @ z_dirs.T


def fit_free(g, x_fit, r_fit, init_dirs, iters=8):
    """Rank-RANK episode part A Gm^T by alternating least squares from init_dirs.

    init_dirs is a seeded random matrix (the registration starts S_free with no
    knowledge of the keys); directions are re-orthonormalised every iteration.
    """
    gm = np.linalg.qr(init_dirs)[0]
    for _ in range(iters):
        delta = fit_span(g, x_fit, r_fit, gm)  # best A given row directions gm
        a_mat = delta @ np.linalg.pinv(gm.T)
        # best row directions given A: G A (gm^T x) -> linear in gm
        ga = g @ a_mat  # (M_OUT, RANK)
        design = np.einsum("mr,nw->nmrw", ga, x_fit).reshape(x_fit.shape[0] * M_OUT, RANK * W)
        gm = np.linalg.qr(ridge_solve(design, r_fit.reshape(-1)).reshape(RANK, W).T)[0]
    return fit_span(g, x_fit, r_fit, gm)


def sse(g, m, x, t):
    return float(np.sum((x @ m.T @ g.T - t) ** 2))


def simulate(teacher: str, degenerate: bool, seed: int) -> dict:
    rng = rng_for("setup", teacher, degenerate, seed)
    cov = residual_cov(rng)
    chol = np.linalg.cholesky(cov + 1e-9 * np.eye(D_B))
    port = make_port(rng, cov, degenerate)
    g = rng.standard_normal((M_OUT, W)) / np.sqrt(W)
    b_star = np.linalg.qr(rng.standard_normal((W, W)))[0] @ np.diag(np.linspace(0.3, 3.0, W))
    out = {"teacher": teacher, "degenerate_port": degenerate, "seed": seed, "families": []}
    for fam in range(N_FAM):
        frng = rng_for("family", teacher, degenerate, seed, fam)
        m_const = frng.standard_normal((W, W)) * 0.3 / np.sqrt(W)
        tasks = [frng.standard_normal((W, W)) / np.sqrt(W) for _ in range(4)]
        episodes = []
        for ep in range(N_EP):
            erng = rng_for("episode", teacher, degenerate, seed, fam, ep)
            demo_h = erng.standard_normal((N_DEMO, D_B)) @ chol.T
            keys = demo_h @ port.T  # (8, W)
            if teacher == "lookup":  # the 8 bound names under three templates (two fit, one held out)
                jitter = 0.1 * erng.standard_normal((3 * N_DEMO, D_B)) @ chol.T
                probe_h = np.concatenate([demo_h, demo_h, demo_h]) + jitter
            else:
                probe_h = erng.standard_normal((N_FIT + N_EVAL, D_B)) @ chol.T
            x = probe_h @ port.T  # probe reads (16, W)
            if teacher == "constant":
                m_ep = np.zeros((W, W))
            elif teacher == "first_order":  # LMS / one GD step: rows along keys
                u = erng.standard_normal((W, N_DEMO)) / np.sqrt(N_DEMO)
                m_ep = u @ keys / np.sqrt(W)
            elif teacher == "preconditioned":  # fixed preconditioner B*: rows along B* k
                u = erng.standard_normal((W, N_DEMO)) / np.sqrt(N_DEMO)
                m_ep = u @ (keys @ b_star.T) / np.sqrt(W)
            elif teacher == "rls":  # recursive least squares: rows along (KK^T + l)^-1 k
                u = erng.standard_normal((W, N_DEMO)) / np.sqrt(N_DEMO)
                kk = keys.T @ keys
                pre = np.linalg.solve(kk + 0.5 * np.trace(kk) / W * np.eye(W), keys.T).T
                m_ep = u @ pre * np.sqrt(W)
            elif teacher == "lookup":  # per-episode binding queried at the demo inputs
                vals = erng.standard_normal((N_DEMO, M_OUT))
                coef = np.linalg.lstsq(keys @ keys.T + 1e-6 * np.eye(N_DEMO), np.eye(N_DEMO), rcond=None)[0]
                g_pinv = np.linalg.pinv(g)
                m_ep = g_pinv @ vals.T @ coef @ keys  # reads only through the key span
            elif teacher == "retrieval":  # posterior-mean over the family's latent tasks
                j = int(erng.integers(4))
                labels = keys @ tasks[j].T + 0.3 * erng.standard_normal((N_DEMO, W))
                logp = np.array([-np.sum((labels - keys @ tk.T) ** 2) / (2 * 0.09) for tk in tasks])
                post = np.exp(logp - logp.max())
                post /= post.sum()
                m_ep = sum(p * tk for p, tk in zip(post, tasks))
            elif teacher == "value_directed":  # write direction from the value, not the key
                vals = erng.standard_normal((N_DEMO, W))
                u = erng.standard_normal((W, N_DEMO)) / np.sqrt(N_DEMO)
                m_ep = u @ vals / np.sqrt(W)
            else:
                raise ValueError(teacher)
            t = x @ (m_const + m_ep).T @ g.T + NOISE * erng.standard_normal((x.shape[0], M_OUT))
            episodes.append({"keys": keys, "x": x, "t": t})
        fit_idx = slice(0, N_FIT)
        eval_idx = slice(N_FIT, N_FIT + N_EVAL)
        c = fit_const(g, [e["x"][fit_idx] for e in episodes], [e["t"][fit_idx] for e in episodes])
        # shared preconditioner B fitted on the first half of the episodes (ALS over B and U_e)
        bfit = episodes[: N_EP // 2]
        b = np.eye(W)
        for _ in range(4):
            us = []
            for e in bfit:
                r = e["t"][fit_idx] - e["x"][fit_idx] @ c.T @ g.T
                z_dirs = (e["keys"] @ b.T).T
                delta = fit_span(g, e["x"][fit_idx], r, z_dirs)
                us.append(delta @ np.linalg.pinv(z_dirs.T))
            rows, rhs = [], []
            for e, u in zip(bfit, us):
                r = e["t"][fit_idx] - e["x"][fit_idx] @ c.T @ g.T
                gu = g @ u  # (M_OUT, RANK); output = gu K B^T x
                rows.append(np.einsum("mr,rw,nv->nmwv", gu, e["keys"], e["x"][fit_idx]).reshape(-1, W * W))
                rhs.append(r.reshape(-1))
            # the solved coefficient multiplies K[r, w] x[v], i.e. B[v, w]; transpose into B.
            # Ridge toward the identity (the registration's prior for B), not toward zero.
            a_mat = np.concatenate(rows)
            r_vec = np.concatenate(rhs)
            ata = a_mat.T @ a_mat
            lam = 1e-2 * float(np.trace(ata)) / ata.shape[0]
            prior = np.eye(W).reshape(-1)
            b = np.linalg.solve(ata + lam * np.eye(W * W), a_mat.T @ r_vec + lam * prior).reshape(W, W).T
        # choose B in {I, fitted B} by held-out error on the B-fit (development) episodes
        dev_err = {}
        for name, cand in (("I", np.eye(W)), ("fitted", b)):
            err = 0.0
            for e in bfit:
                r = e["t"][fit_idx] - e["x"][fit_idx] @ c.T @ g.T
                part = fit_span(g, e["x"][fit_idx], r, (e["keys"] @ cand.T).T)
                err += sse(g, c + part, e["x"][N_FIT:N_FIT + N_EVAL], e["t"][N_FIT:N_FIT + N_EVAL])
            dev_err[name] = err
        b_used = b if dev_err["fitted"] < dev_err["I"] else np.eye(W)
        res = {"sse0": 0.0, "const": 0.0, "span_I": 0.0, "span_B": 0.0, "free": 0.0}
        out_frac = []
        for e in episodes[N_EP // 2 :]:
            xf, tf = e["x"][fit_idx], e["t"][fit_idx]
            xe, te = e["x"][eval_idx], e["t"][eval_idx]
            r_fit = tf - xf @ c.T @ g.T
            dirs_i = e["keys"].T
            dirs_b = (e["keys"] @ b_used.T).T
            span_i = fit_span(g, xf, r_fit, dirs_i)
            span_b = fit_span(g, xf, r_fit, dirs_b)
            free = fit_free(g, xf, r_fit, rng_for("free-init", teacher, degenerate, seed, fam).standard_normal((W, RANK)))
            res["sse0"] += sse(g, np.zeros((W, W)), xe, te)
            res["const"] += sse(g, c, xe, te)
            res["span_I"] += sse(g, c + span_i, xe, te)
            res["span_B"] += sse(g, c + span_b, xe, te)
            res["free"] += sse(g, c + free, xe, te)
            q, _ = np.linalg.qr(dirs_i)
            proj = xe @ q @ q.T
            out_frac.append(float(np.sum((xe - proj) ** 2) / np.sum(xe**2)))
        rec = {k: 1.0 - res[k] / res["sse0"] for k in ("const", "span_I", "span_B", "free")}
        # the registration's guard: E and D_span are defined only when the family constant
        # leaves at least 0.20 of the zero-shot divergence (otherwise EPISODE_CONSTANT)
        episode_specific = res["const"] / res["sse0"] >= 0.20
        epi = ({k: 1.0 - res[k] / res["const"] for k in ("span_I", "span_B", "free")}
               if episode_specific else {k: float("nan") for k in ("span_I", "span_B", "free")})
        out["families"].append(
            {
                "R": rec,
                "E": epi,
                "episode_specific": bool(episode_specific),
                "B_selected": "fitted" if b_used is b else "I",
                "ES": rec["free"] - rec["const"],
                "D_span_B": epi["free"] - epi["span_B"],
                "D_span_I": epi["free"] - epi["span_I"],
                "probe_energy_outside_key_span_median": float(np.median(out_frac)),
            }
        )
    fams = out["families"]
    out["summary"] = {
        k: float(np.nanmean([f[k] for f in fams])) if any(np.isfinite(f[k]) for f in fams) else None
        for k in ("ES", "D_span_B", "D_span_I", "probe_energy_outside_key_span_median")
    }
    e_free = [f["E"]["free"] for f in fams]
    out["summary"]["E_free"] = float(np.nanmean(e_free)) if any(np.isfinite(e_free)) else None
    out["summary"]["R_const"] = float(np.mean([f["R"]["const"] for f in fams]))
    out["summary"]["R_free"] = float(np.mean([f["R"]["free"] for f in fams]))
    out["summary"]["episode_specific_families"] = int(sum(f["episode_specific"] for f in fams))
    out["summary"]["families_selecting_fitted_B"] = int(sum(f["B_selected"] == "fitted" for f in fams))
    return out


def main() -> int:
    teachers = ["constant", "first_order", "preconditioned", "rls", "lookup", "retrieval", "value_directed"]
    jobs = [(t, d, s) for d in (True, False) for t in teachers for s in (42, 43, 44)]
    n_proc = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    if n_proc > 1:  # results are seeded per scenario, so process count does not change them
        import multiprocessing as mp
        with mp.get_context("spawn").Pool(n_proc) as pool:
            results = pool.starmap(simulate, jobs)
    else:
        results = [simulate(*job) for job in jobs]
    table = {}
    for degenerate in (True, False):
        for teacher in teachers:
            rows = [r["summary"] for r in results if r["teacher"] == teacher and r["degenerate_port"] == degenerate]
            key = f"{'rank8_port' if degenerate else 'fullrank_port'}/{teacher}"
            table[key] = {k: [None if r[k] is None else round(r[k], 4) for r in rows] for k in rows[0]}
    payload = {
        "check": "E4 gate S1: oracle state-class semantics (linear surrogate)",
        "claim_boundary": "instrument semantics in a synthetic linear surrogate; no model, no teacher, no data",
        "config": {"D_B": D_B, "W": W, "M_OUT": M_OUT, "N_DEMO": N_DEMO, "N_FIT": N_FIT, "N_EVAL": N_EVAL,
                   "RANK": RANK, "N_EP": N_EP, "N_FAM": N_FAM, "RIDGE": RIDGE, "NOISE": NOISE,
                   "seeds": [42, 43, 44], "numpy": np.__version__},
        "summary_by_port_and_teacher": table,
    }
    text = json.dumps(payload, indent=1, sort_keys=True)
    payload["payload_sha256"] = hashlib.sha256(text.encode()).hexdigest()
    with open(sys.argv[1], "w") as fh:
        json.dump(payload, fh, indent=1, sort_keys=True)
        fh.write("\n")
    for key, row in table.items():
        print(key, {k: v for k, v in row.items()})
    return 0


if __name__ == "__main__":
    sys.exit(main())
