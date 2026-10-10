#!/usr/bin/env python3
"""E4 gate repair (D60), CPU check S1v2: the registered v2 estimator on a linear surrogate.

This replaces nothing: wave 1's S1 (`../oracle-class-semantics.py`) is kept as it
was. Wave 1 found that S1 did not implement the registered estimator (S1 fitted a
full-rank family constant on all 16 probes, the v1 registration a rank-8 constant
on 4 probes per episode), and that under the registered one a constant teacher
passed the guard and gradient-form teachers read GAP. This script implements the
v2 registration's estimator exactly, as one function (`estimate_family`) that the
decision code reads, and runs it on synthetic teachers whose answer is known.

Surrogate (not a model run; it says nothing about the 1.3B teacher):
  residual h in R^128; interface width 32 (the gate's is 64); affine read
  x~ = [P h; 1]; student output change G M x~ (G fixed, 64 outputs); squared error
  stands in for KL. A family's probe and key reads share a template mean and vary
  in a d_task-dimensional subspace (d_task is the scenario axis the instrument
  gates I1 and I2 depend on). In-context keys are the site's reads of each
  demonstration inside the 8-shot prompt: h_i + 0.5 h_(i-1) + c_e (c_e an episode
  context vector).

Registered v2 estimator, per family (decision code below mirrors registration v2):
  C_f   full-rank affine 32 x 33 state, fitted on every fitting probe of all 46
        episodes (the gate: 48), never on scoring probes.
  S_shift  C_f + b_e e_c^T (a free per-episode probe-independent shift: label prior).
  S_span   C_f + b_e e_c^T + U_e Z_e^T (x - mu), Z_e = span of the mapped keys. Key sets:
           alone keys, in-context keys, or S B [S^T K_alone; S^T K_ctx] with S the family's
           probe-read subspace (99% of the centred development read energy, r dims) and
           B (r x 2r) shared by all episodes, fitted like C_f on the fitting probes of every
           episode (penalty toward [I/2, I/2]); the key set is chosen per family by
           development held-out error.
  S_free   C_f + b_e e_c^T + A_e G_e^T (rank 8, read side on the 32 read coordinates).
  S_resample  C_f + b_e (the episode's own shift) + the probe-dependent part of the
           next evaluation episode's S_free (cyclic).
  E_X = 1 - sum KL_X / sum KL_shift;  D_span(e) = (KL_span - KL_free)/mean KL_shift;
  Delta_res(e) = (KL_resample - KL_free)/mean KL_shift (the placebo contrast).
  Decisions per family: I0 (C_f adequacy: the leave-one-out mean of the fitted
  episode parts may remove at most 0.05 of C_f's held-out divergence), the
  label-prior guard (KL_shift >= 0.10 KL_LD, KL_LD = teacher GOLD vs SHUF
  divergence on the scoring probes), the placebo test (one-sided 95% lower bound
  of mean Delta_res > 0.10, else EPISODE_CONSTANT), capacity (E_free lower bound
  >= 0.50 CAP_OK; upper < 0.50 CAP_LOW), I1 per family (median centred
  scoring-read energy outside the chosen key span >= 0.25, else SPAN_VACUOUS),
  span (TIE: upper bound of D_span <= 0.05; GAP: D_span >= 0.10 and lower bound
  > 0.02). Planted gates I2 (free and span recovery >= 0.90), I3 (planted
  out-of-span D_span >= 0.30, planted span <= 0.03), I5 (fixed preconditioner,
  planted on every episode with B refitted as registered, 8 scored episodes) and
  I6 (keys from a permuted-order context, 8 planted episodes), each passing when
  the planted writer would not meet the family GAP rule, and I7
  (a planted per-episode shift must read EPISODE_CONSTANT) run on development
  episodes, as registered.

The v1 estimator (rank-8 C_f on the first 4 fitting probes, no shift class, KL_S0
guard, report-only placebo, alone keys) is run beside it on the teachers wave 1
named, so the repair is shown against the failure it repairs.

Fitting is closed-form or alternating least squares; every linear system has
Kronecker structure (sum_q z_q z_q^T kron G^T G) and is solved through two small
eigendecompositions, as in wave 1's S1. The gate itself fits by Adam on KL; this
surrogate checks estimator semantics, not the optimiser.

Usage: python oracle-estimator-v2.py <out.json> [processes] [--grid]
All randomness is seeded from scenario keys; process count does not change results.
"""

from __future__ import annotations

import hashlib
import json
import sys
import zlib

import numpy as np

D_B, W, M_OUT = 128, 32, 64
N_DEMO, N_SCORE, RANK = 8, 8, 8
N_DEV, N_EVAL = 14, 32
RIDGE = 1e-3
NOISE = 0.02
SEEDS = (42, 43, 44)
N_FAM = 2
T_CRIT_31 = 1.6955  # one-sided 95% t, df 31 (32 evaluation episodes)


def rng_for(*key: object) -> np.random.Generator:
    return np.random.default_rng(zlib.crc32(repr(key).encode()))


def tcrit(n: int) -> float:
    from math import isfinite
    table = {7: 1.8946, 15: 1.7531, 31: 1.6955, 47: 1.6779}
    return table.get(n - 1, 1.6955)


def bounds(v: np.ndarray) -> tuple[float, float, float]:
    m = float(np.mean(v))
    se = float(np.std(v, ddof=1) / np.sqrt(len(v)))
    t = tcrit(len(v))
    return m, m - t * se, m + t * se


# ---------------------------------------------------------------- linear algebra
def solve_kron(gtg_eig, z: np.ndarray, rhs: np.ndarray) -> np.ndarray:
    """argmin_U sum_q ||G U z_q - r_q||^2 + ridge; rhs = G^T R^T Z (W x k). U is W x k."""
    e1, v1 = gtg_eig
    zz = z.T @ z
    e2, v2 = np.linalg.eigh(zz)
    lam = RIDGE * float(np.mean(e1)) * float(np.mean(np.abs(e2))) + 1e-12
    r = v1.T @ rhs @ v2
    return v1 @ (r / (np.outer(e1, e2) + lam)) @ v2.T


def fit_rowspace(g, gtg_eig, x, r, zdirs, shift: bool) -> np.ndarray:
    """Episode part with a fixed row space (orthonormalised zdirs, W x k) plus an optional free shift.

    Returns the episode part as a W x (W+1) affine matrix."""
    q = np.linalg.qr(zdirs)[0] if zdirs.shape[1] else zdirs
    z = x @ q
    if shift:
        z = np.concatenate([z, np.ones((x.shape[0], 1))], axis=1)
    u = solve_kron(gtg_eig, z, g.T @ r.T @ z)
    part = np.zeros((W, W + 1))
    k = q.shape[1]
    part[:, :W] = u[:, :k] @ q.T
    if shift:
        part[:, W] = u[:, k]
    return part


def fit_shift(g, gtg_eig, x, r) -> np.ndarray:
    return fit_rowspace(g, gtg_eig, x, r, np.zeros((W, 0)), True)


def fit_free(g, gtg_eig, x, r, init: np.ndarray, shift: bool, iters: int = 10) -> np.ndarray:
    """Rank-RANK read side (free) plus optional shift, by alternating least squares from a seeded init."""
    gm = np.linalg.qr(init)[0]
    part = None
    for _ in range(iters):
        part = fit_rowspace(g, gtg_eig, x, r, gm, shift)
        a_mat = part[:, :W] @ gm  # W x RANK write side
        resid = r - (part[:, W][None, :] @ g.T if shift else 0.0)
        phi = g @ a_mat  # M_OUT x RANK
        # resid_q = phi gm^T x_q: solve gm (W x RANK) by the same Kronecker trick with roles swapped
        pe = np.linalg.eigh(phi.T @ phi)
        xx_e = np.linalg.eigh(x.T @ x)
        rhs = x.T @ resid @ phi  # W x RANK
        lam = RIDGE * float(np.mean(np.abs(pe[0]))) * float(np.mean(np.abs(xx_e[0]))) + 1e-12
        rr = xx_e[1].T @ rhs @ pe[1]
        gm_new = xx_e[1] @ (rr / (np.outer(xx_e[0], pe[0]) + lam)) @ pe[1].T
        if not np.all(np.isfinite(gm_new)) or np.linalg.norm(gm_new) < 1e-12:
            break
        gm = np.linalg.qr(gm_new)[0]
    return fit_rowspace(g, gtg_eig, x, r, gm, shift)


CF_RIDGE = {"value": 1e-7}  # relative ridge of the family constant
CF_MISFIT = {"scale": 1.0, "c_true_scale": 1.0}  # the misfit scenario under-fits C_f on purpose


def fit_const_full(g, gtg_eig, xs, ts) -> np.ndarray:
    """Full-rank affine family constant, fitted with a free shift per episode (fixed effects).

    The per-episode shifts are nuisance parameters of the fit: the linear part is identified from
    within-episode variation, so episode-level label priors do not leak into it through chance
    correlation with the reads. The constant column is the mean over episodes. The gate fits the same
    model by minibatch Adam on KL (registration v2, "Classes")."""
    xc = np.concatenate([x[:, :W] - x[:, :W].mean(0) for x in xs])
    tc = np.concatenate([t - t.mean(0) for t in ts])
    e1, v1 = gtg_eig
    e2, v2 = np.linalg.eigh(xc.T @ xc)
    lam = CF_RIDGE["value"] * float(np.mean(e1)) * float(np.mean(np.abs(e2))) + 1e-12
    r = v1.T @ (g.T @ tc.T @ xc) @ v2
    lin = v1 @ (r / (np.outer(e1, e2) + lam)) @ v2.T  # W x W
    x_all = np.concatenate([x[:, :W] for x in xs])
    t_all = np.concatenate(ts)
    resid_mean = (t_all - x_all @ lin.T @ g.T).mean(0)
    c0 = np.linalg.lstsq(g, resid_mean, rcond=None)[0]
    return np.concatenate([CF_MISFIT["scale"] * lin, c0[:, None]], axis=1)  # W x (W+1)


def to_raw(part: np.ndarray, mu: np.ndarray) -> np.ndarray:
    """An episode part fitted on centred reads (x - mu) written as an affine matrix on raw reads."""
    out = part.copy()
    out[:, W] = part[:, W] - part[:, :W] @ mu
    return out


def sse(g, m, x, t) -> float:
    return float(np.sum((x @ m.T @ g.T - t) ** 2))


def aug(xr: np.ndarray) -> np.ndarray:
    return np.concatenate([xr, np.ones((xr.shape[0], 1))], axis=1)


# ---------------------------------------------------------------- surrogate world
def residual_cov(rng):
    q, _ = np.linalg.qr(rng.standard_normal((D_B, D_B)))
    spec = 1.0 / (1.0 + np.arange(D_B)) ** 0.6
    spec[0] = 25.0
    return (q * spec) @ q.T


def make_port(rng, cov, degenerate: bool):
    evals, evecs = np.linalg.eigh(cov)
    whiten = (evecs / np.sqrt(evals)) @ evecs.T
    if degenerate:
        return rng.standard_normal((W, RANK)) @ rng.standard_normal((RANK, D_B)) @ whiten / np.sqrt(D_B)
    basis, _ = np.linalg.qr(rng.standard_normal((D_B, W)))
    return basis.T @ whiten


TEACHERS = ["constant", "generic_nonlinear", "prior_shift", "first_order", "fo_prior", "fo_ctx", "fo_ctx_mis",
            "rls", "preconditioned", "lookup", "retrieval", "value_directed"]


class World:
    """One family: port, output map, template read distribution, true constant, latent tasks."""

    def __init__(self, teacher, seed, fam, d_task, n_fit, mean_share=0.5, degenerate=False):
        rng = rng_for("world", teacher, seed, fam, d_task, n_fit, degenerate)
        self.teacher, self.d_task, self.n_fit = teacher, d_task, n_fit
        cov = residual_cov(rng)
        self.port = make_port(rng, cov, degenerate)
        self.g = rng.standard_normal((M_OUT, W)) / np.sqrt(W)
        self.gtg_eig = np.linalg.eigh(self.g.T @ self.g)
        # template read distribution in whitened interface coordinates: mean + d_task-dim variation
        pinv = np.linalg.pinv(self.port)
        basis = np.linalg.qr(rng.standard_normal((W, d_task)))[0] if d_task < W else np.eye(W)
        spec = np.ones(basis.shape[1])
        mu_dir = rng.standard_normal(W)
        mu_dir /= np.linalg.norm(mu_dir)
        var_total = float(np.sum(spec))
        mu_norm = np.sqrt(mean_share / (1 - mean_share) * var_total) if mean_share > 0 else 0.0
        self.mu_h = pinv @ (mu_norm * mu_dir)
        self.l_h = pinv @ (basis * np.sqrt(spec))
        self.eps_scale = 0.05
        self.chol = np.linalg.cholesky(cov + 1e-9 * np.eye(D_B))
        self.c_true = rng.standard_normal((W, W + 1)) * 0.3 / np.sqrt(W) * CF_MISFIT["c_true_scale"]
        self.tasks = [rng.standard_normal((W, W)) / np.sqrt(W) for _ in range(4)]
        self.b_star = np.linalg.qr(rng.standard_normal((W, W)))[0] @ np.diag(np.linspace(0.3, 3.0, W))
        self.nonlin = rng.standard_normal((W, W)) / np.sqrt(W)

    def sample_h(self, rng, n):
        z = rng.standard_normal((n, self.l_h.shape[1]))
        return self.mu_h + z @ self.l_h.T + self.eps_scale * rng.standard_normal((n, D_B)) @ self.chol.T

    def read(self, h):
        return h @ self.port.T


def episode_part(world: World, teacher: str, erng, keys_a, keys_c, demo_h, shuffled: bool):
    """Teacher's episode part (W x (W+1)) from its own keys and values; shuffled = deranged labels."""
    perm = np.roll(np.arange(N_DEMO), 1) if shuffled else np.arange(N_DEMO)  # a derangement
    part = np.zeros((W, W + 1))
    u = erng.standard_normal((W, N_DEMO)) / np.sqrt(N_DEMO)
    b = erng.standard_normal(W) * 0.6
    if teacher in ("constant", "generic_nonlinear"):
        return part
    if teacher == "prior_shift":  # a per-episode label prior: probe-independent; label multiset unchanged by SHUF
        part[:, W] = b
        return part
    if teacher in ("first_order", "fo_prior"):
        part[:, :W] = u[:, perm] @ keys_a / np.sqrt(W)
        if teacher == "fo_prior":
            part[:, W] = b
        return part
    if teacher == "fo_ctx":  # gradient-form on the site's in-context reads
        part[:, :W] = u[:, perm] @ keys_c / np.sqrt(W)
        return part
    if teacher == "fo_ctx_mis":  # gradient-form on keys contextualised differently from the site's reads
        prev = np.concatenate([np.zeros((1, D_B)), demo_h[:-1]])
        k_mis = world.read(demo_h + 0.3 * prev + 0.7 * world.ctx_vec) + 0.05 * erng.standard_normal((N_DEMO, W))
        part[:, :W] = u[:, perm] @ k_mis / np.sqrt(W)
        return part
    if teacher == "rls":
        kk = keys_a.T @ keys_a
        pre = np.linalg.solve(kk + 0.5 * np.trace(kk) / W * np.eye(W), keys_a.T).T
        part[:, :W] = u[:, perm] @ pre * np.sqrt(W) / 8
        return part
    if teacher == "preconditioned":
        part[:, :W] = u[:, perm] @ (keys_a @ world.b_star.T) / np.sqrt(W)
        return part
    if teacher == "lookup":
        vals = erng.standard_normal((N_DEMO, M_OUT))[perm]
        coef = np.linalg.lstsq(keys_a @ keys_a.T + 1e-6 * np.eye(N_DEMO), np.eye(N_DEMO), rcond=None)[0]
        part[:, :W] = np.linalg.pinv(world.g) @ vals.T @ coef @ keys_a
        return part
    if teacher == "retrieval":
        j = int(erng.integers(4))
        labels = keys_a @ world.tasks[j].T + 0.3 * erng.standard_normal((N_DEMO, W))
        labels = labels[perm]
        logp = np.array([-np.sum((labels - keys_a @ tk.T) ** 2) / (2 * 0.09) for tk in world.tasks])
        post = np.exp(logp - logp.max())
        post /= post.sum()
        part[:, :W] = sum(p * tk for p, tk in zip(post, world.tasks))
        return part
    if teacher == "value_directed":
        vals = erng.standard_normal((N_DEMO, W))
        part[:, :W] = u @ vals[perm] / np.sqrt(W)
        return part
    raise ValueError(teacher)


def make_episode(world: World, teacher: str, tag, ep: int, plant=None, base_c=None):
    erng = rng_for("episode", teacher, tag, ep)
    world.ctx_vec = 0.8 * erng.standard_normal(D_B) @ world.chol.T * 0.3 + 0.5 * world.mu_h
    demo_h = world.sample_h(erng, N_DEMO)
    keys_a = world.read(demo_h)
    prev = np.concatenate([np.zeros((1, D_B)), demo_h[:-1]])
    keys_c = world.read(demo_h + 0.5 * prev + world.ctx_vec)
    perm_ctx = erng.permutation(N_DEMO)
    prev_p = np.concatenate([np.zeros((1, D_B)), demo_h[perm_ctx][:-1]])[np.argsort(perm_ctx)]
    keys_c_perm = world.read(demo_h + 0.5 * prev_p + world.ctx_vec)
    n_probe = world.n_fit + N_SCORE
    if teacher == "lookup":  # the 8 bound names under several templates (fit templates, held-out template)
        reps = int(np.ceil(n_probe / N_DEMO))
        probe_h = np.concatenate([demo_h] * reps)[:n_probe] + 0.1 * erng.standard_normal((n_probe, D_B)) @ world.chol.T * 0.3
        # scoring probes = the held-out template: the last N_SCORE rows are one full pass over the names
        probe_h[-N_SCORE:] = demo_h + 0.1 * erng.standard_normal((N_DEMO, D_B)) @ world.chol.T * 0.3
    else:
        probe_h = world.sample_h(erng, n_probe)
    x = aug(world.read(probe_h))
    if plant is not None:
        part, part_shuf = plant(erng, keys_a, keys_c, keys_c_perm, x), None
    else:
        part = episode_part(world, teacher, rng_for("part", teacher, tag, ep), keys_a, keys_c, demo_h, False)
        part_shuf = episode_part(world, teacher, rng_for("part", teacher, tag, ep), keys_a, keys_c, demo_h, True)
    noise = NOISE * erng.standard_normal((n_probe, M_OUT))
    base = x @ (world.c_true if base_c is None else base_c).T  # planted episodes: the fitted C_f is the base
    if teacher == "generic_nonlinear":  # family-level behaviour no linear state can express (constant misfit)
        base = base + 0.5 * np.tanh(2.0 * x[:, :W] @ world.nonlin.T)
    t = (base + x @ part.T) @ world.g.T + noise
    t_shuf = None if part_shuf is None else (base + x @ part_shuf.T) @ world.g.T + noise
    return {"keys_a": keys_a, "keys_c": keys_c, "keys_c_perm": keys_c_perm, "x": x, "t": t, "t_shuf": t_shuf,
            "true_part": part}


# ---------------------------------------------------------------- B (joint key map) fit
def read_subspace(dev, mu, nf, frac=0.99):
    """Orthonormal basis (W x r) of the subspace holding `frac` of the centred development probe-read energy."""
    xr = np.concatenate([e["x"][:nf, :W] for e in dev]) - mu
    _, sv, vt = np.linalg.svd(xr, full_matrices=False)
    cum = np.cumsum(sv ** 2) / np.sum(sv ** 2)
    r = int(min(W, max(RANK, np.searchsorted(cum, frac) + 1)))
    return vt[:r].T


def fit_joint_b(world: World, eps, c, b_prior, mu, sub, iters: int = 8):
    """B (r x 2r) maps the keys' coordinates in the read subspace sub (W x r); rows z = sub B [sub^T k_a; sub^T k_c]."""
    g, nf = world.g, world.n_fit
    r_dim = sub.shape[1]
    b = b_prior.copy()
    gtg_eig = world.gtg_eig
    for _ in range(iters):
        ata = np.zeros((r_dim * 2 * r_dim, r_dim * 2 * r_dim))
        aty = np.zeros((r_dim, 2 * r_dim))
        for e in eps:
            xf, tf = e["x"][:nf], e["t"][:nf]
            r = tf - xf @ c.T @ g.T
            kj = np.concatenate([e["keys_a"] @ sub, e["keys_c"] @ sub], axis=1)  # 8 x 2r
            zd = sub @ (kj @ b.T).T  # W x 8
            xc = (xf[:, :W] - mu) @ sub  # n x r
            xfull = xf[:, :W] - mu
            part = fit_rowspace(g, gtg_eig, xfull, r, zd, True)
            u = part[:, :W] @ np.linalg.pinv(zd.T)
            resid = r - part[:, W][None, :] @ g.T
            phi = g @ u @ kj  # M_OUT x 2r: output = phi B^T (sub^T x_c)
            xx = xc.T @ xc
            ata += np.kron(xx, phi.T @ phi)
            aty += xc.T @ resid @ phi
        lam = 1e-3 * float(np.trace(ata)) / ata.shape[0]
        vec = np.linalg.solve(ata + lam * np.eye(ata.shape[0]), aty.reshape(-1) + lam * b_prior.reshape(-1))
        b = vec.reshape(r_dim, 2 * r_dim)
    return b


def keyset_dirs(e, choice, b_fit):
    if choice == "alone":
        return e["keys_a"].T
    if choice == "ctx":
        return e["keys_c"].T
    b, sub = b_fit
    kj = np.concatenate([e["keys_a"] @ sub, e["keys_c"] @ sub], axis=1)
    return sub @ (kj @ b.T).T


# ---------------------------------------------------------------- the registered estimator (v2)
def estimate_family(world: World, dev, ev, teacher_tag, plant_checks: bool = True) -> dict:
    g, gtg_eig, nf = world.g, world.gtg_eig, world.n_fit
    fit, sco = slice(0, nf), slice(nf, nf + N_SCORE)
    allep = dev + ev
    c = fit_const_full(g, gtg_eig, [e["x"][fit] for e in allep], [e["t"][fit] for e in allep])
    mu = np.mean(np.concatenate([q["x"][fit][:, :W] for q in dev]), axis=0)  # centring vector (development only)
    sub = read_subspace(dev, mu, nf)  # the family's probe-read subspace (99% of centred development read energy)
    rr = sub.shape[1]
    b_prior = np.concatenate([0.5 * np.eye(rr), 0.5 * np.eye(rr)], axis=1)
    # B is a family-level parameter like C_f: fitted on the fitting probes of every episode, never on scoring probes
    b_fit = (fit_joint_b(world, allep, c, b_prior, mu, sub), sub)
    # key-set choice on development held-out error
    dev_err = {}
    for choice in ("alone", "ctx", "fitted"):
        err = 0.0
        for e in dev:
            r = e["t"][fit] - e["x"][fit] @ c.T @ g.T
            part = to_raw(fit_rowspace(g, gtg_eig, e["x"][fit][:, :W] - mu, r, keyset_dirs(e, choice, b_fit), True), mu)
            err += sse(g, c + part, e["x"][sco], e["t"][sco])
        dev_err[choice] = err
    choice = min(dev_err, key=dev_err.get)
    rows = []
    free_parts = []
    for j, e in enumerate(ev):
        xf, tf, xs, ts = e["x"][fit], e["t"][fit], e["x"][sco], e["t"][sco]
        r = tf - xf @ c.T @ g.T
        xfc = xf[:, :W] - mu
        shift = to_raw(fit_shift(g, gtg_eig, xfc, r), mu)
        span = to_raw(fit_rowspace(g, gtg_eig, xfc, r, keyset_dirs(e, choice, b_fit), True), mu)
        span_a = to_raw(fit_rowspace(g, gtg_eig, xfc, r, e["keys_a"].T, True), mu)
        span_c = to_raw(fit_rowspace(g, gtg_eig, xfc, r, e["keys_c"].T, True), mu)
        free_c = fit_free(g, gtg_eig, xfc, r, rng_for("free-init", teacher_tag, j).standard_normal((W, RANK)), True)
        free = to_raw(free_c, mu)
        free_parts.append(free_c)
        # I1: centred scoring-read energy outside the chosen key span
        xc = xs[:, :W] - mu
        qk = np.linalg.qr(keyset_dirs(e, choice, b_fit))[0]
        out_frac = float(np.sum((xc - xc @ qk @ qk.T) ** 2) / np.sum(xc ** 2))
        rows.append({"s0": sse(g, np.zeros((W, W + 1)), xs, ts), "const": sse(g, c, xs, ts),
                     "shift": sse(g, c + shift, xs, ts), "span": sse(g, c + span, xs, ts),
                     "span_alone": sse(g, c + span_a, xs, ts), "span_ctx": sse(g, c + span_c, xs, ts),
                     "free": sse(g, c + free, xs, ts),
                     "ld": float(np.sum((ts - e["t_shuf"][sco]) ** 2)) if e["t_shuf"] is not None else float("nan"),
                     "shift_part": shift, "out_frac": out_frac})
    n = len(ev)
    for j, e in enumerate(ev):  # resample placebo: own shift + next episode's probe-dependent free part
        other = free_parts[(j + 1) % n].copy()
        other[:, W] = 0.0
        other = to_raw(other, mu)
        other[:, W] += rows[j]["shift_part"][:, W]
        rows[j]["resample"] = sse(g, c + other, e["x"][sco], e["t"][sco])
        loo = np.mean([free_parts[k] for k in range(n) if k != j], axis=0)  # I0: leave-one-out mean probe-dependent part
        loo[:, W] = 0.0
        loo = to_raw(loo, mu)
        loo[:, W] += rows[j]["shift_part"][:, W]
        rows[j]["shift_plus_mean"] = sse(g, c + loo, e["x"][sco], e["t"][sco])
    get = lambda k: np.array([rw[k] for rw in rows])
    kl_shift_mean = float(np.mean(get("shift")))
    e_free = 1 - get("free").sum() / get("shift").sum()
    e_span = 1 - get("span").sum() / get("shift").sum()
    d_span_ep = (get("span") - get("free")) / kl_shift_mean
    d_res_ep = (get("resample") - get("free")) / kl_shift_mean
    e_free_ep = 1 - get("free") / kl_shift_mean  # episode terms whose mean is the ratio-of-means up to weights
    i0 = 1 - get("shift_plus_mean").sum() / get("shift").sum()
    guard_ratio = float(get("shift").sum() / get("ld").sum()) if np.all(np.isfinite(get("ld"))) else float("nan")
    m_res, lo_res, _ = bounds(d_res_ep)
    m_free, lo_free, hi_free = bounds(e_free_ep)
    m_span, lo_span, hi_span = bounds(d_span_ep)
    i1 = float(np.median(get("out_frac")))
    verdict = {}
    verdict["I0_pass"] = bool(i0 <= 0.05)
    verdict["label_prior_guard_pass"] = bool(not np.isfinite(guard_ratio) or guard_ratio >= 0.10)
    verdict["placebo_pass"] = bool(lo_res > 0.10)
    if not verdict["I0_pass"]:
        fam = "INSTRUMENT_FAIL_I0"
    elif not (verdict["placebo_pass"] and verdict["label_prior_guard_pass"]):
        fam = "EPISODE_CONSTANT"
    elif lo_free >= 0.50:
        if i1 < 0.25:
            fam = "CAP_OK/SPAN_VACUOUS"
        elif hi_span <= 0.05:
            fam = "CAP_OK/TIE"
        elif m_span >= 0.10 and lo_span > 0.02:
            fam = "CAP_OK/GAP"
        else:
            fam = "CAP_OK/SPAN_UNDECIDED"
    elif hi_free < 0.50:
        fam = "CAP_LOW"
    else:
        fam = "CAP_UNDECIDED"
    out = {"key_set": choice, "I0_mean_part_gain": round(float(i0), 4), "label_prior_guard_ratio": round(guard_ratio, 4),
           "R_const": round(float(1 - get("const").sum() / get("s0").sum()), 4),
           "R_shift": round(float(1 - get("shift").sum() / get("s0").sum()), 4),
           "E_free": round(float(e_free), 4), "E_free_lo": round(lo_free, 4), "E_span": round(float(e_span), 4),
           "E_span_alone": round(float(1 - get("span_alone").sum() / get("shift").sum()), 4),
           "E_span_ctx": round(float(1 - get("span_ctx").sum() / get("shift").sum()), 4),
           "E_resample": round(float(1 - get("resample").sum() / get("shift").sum()), 4),
           "Delta_res": round(m_res, 4), "Delta_res_lo": round(lo_res, 4),
           "D_span": round(m_span, 4), "D_span_lo": round(lo_span, 4), "D_span_hi": round(hi_span, 4),
           "I1_out_of_span_energy": round(i1, 4), "verdict": fam, **verdict}
    if plant_checks:
        out["planted"] = planted_gates(world, c, b_fit, choice, teacher_tag, mu)
    return out


def planted_gates(world: World, c, b_fit, choice, tag, mu) -> dict:
    """I2, I3, I5, I6, I7 on planted development episodes (targets = frozen read path under C_f + planted part)."""
    g, gtg_eig, nf = world.g, world.gtg_eig, world.n_fit
    fit, sco = slice(0, nf), slice(nf, nf + N_SCORE)
    ref = [make_episode(world, "constant", ("plantref", tag), k) for k in range(4)]
    xr = np.concatenate([e["x"][fit][:, :W] for e in ref]) - mu
    _, sv, vt = np.linalg.svd(xr, full_matrices=False)
    cum = np.cumsum(sv ** 2) / np.sum(sv ** 2)
    d90 = int(np.searchsorted(cum, 0.90) + 1)
    sub = vt[:d90].T  # W x d90: the subspace holding 90% of the centred probe-read energy
    scale = 0.6

    def rows_from(dirs, erng, k):
        q = np.linalg.qr(dirs)[0][:, :k]
        part = np.zeros((W, W + 1))
        part[:, :W] = erng.standard_normal((W, q.shape[1])) @ q.T * scale / np.sqrt(RANK)
        return part

    def planted_free(erng, ka, kc, kcp, x):  # I2: random rank-8 read side in the probe-read subspace, plus a shift
        part = rows_from(sub @ erng.standard_normal((d90, RANK)), erng, RANK)
        part[:, W] = erng.standard_normal(W) * 0.3
        return part

    def planted_out(erng, ka, kc, kcp, x):  # I3a: read side in the probe-read subspace, orthogonal to the key span
        qk = np.linalg.qr(keyset_dirs({"keys_a": ka, "keys_c": kc}, choice, b_fit))[0]
        d = sub @ erng.standard_normal((d90, RANK))
        d = d - qk @ (qk.T @ d)
        k = max(1, min(RANK, int(np.linalg.matrix_rank(d, tol=1e-6))))
        return rows_from(d, erng, k)

    def planted_span(erng, ka, kc, kcp, x):  # I2/I3b: read side in the chosen key span
        return rows_from(keyset_dirs({"keys_a": ka, "keys_c": kc}, choice, b_fit), erng, RANK)

    def planted_ctx_perm(erng, ka, kc, kcp, x):  # I6: gradient-form on keys from a permuted-order context
        part = np.zeros((W, W + 1))
        part[:, :W] = erng.standard_normal((W, N_DEMO)) / np.sqrt(N_DEMO) @ kcp / np.sqrt(W)
        return part

    def planted_pre(erng, ka, kc, kcp, x):  # I5: fixed preconditioner on alone keys
        part = np.zeros((W, W + 1))
        part[:, :W] = erng.standard_normal((W, N_DEMO)) / np.sqrt(N_DEMO) @ (ka @ world.b_star.T) / np.sqrt(W)
        return part

    def planted_shift(erng, ka, kc, kcp, x):  # I7: a per-episode label prior only
        part = np.zeros((W, W + 1))
        part[:, W] = erng.standard_normal(W) * 0.6
        return part

    def score(e, part_fit):
        tgt = e["x"][sco] @ (c + e["true_part"]).T @ g.T
        return float(np.sum((e["x"][sco] @ (c + part_fit).T @ g.T - tgt) ** 2))

    def fits(e, k, name, b_use=None, keyset=None):
        r = e["t"][fit] - e["x"][fit] @ c.T @ g.T
        xfc = e["x"][fit][:, :W] - mu
        best = None
        for rs in (42, 43, 44):  # best of 3 restarts by fitting loss, as registered
            cand = fit_free(g, gtg_eig, xfc, r, rng_for("pl-init", name, tag, k, rs).standard_normal((W, RANK)), True)
            loss = sse(g, cand, np.concatenate([xfc, np.ones((xfc.shape[0], 1))], axis=1), r)
            if best is None or loss < best[0]:
                best = (loss, cand)
        fr = to_raw(best[1], mu)
        sp = to_raw(fit_rowspace(g, gtg_eig, xfc, r, keyset_dirs(e, keyset or choice, b_fit if b_use is None else b_use), True), mu)
        base = score(e, np.zeros((W, W + 1)))
        return fr, sp, base

    res = {"probe_read_d90": d90}
    for name, fn in (("free", planted_free), ("out_of_span", planted_out), ("span", planted_span), ("ctx_perm", planted_ctx_perm)):
        recs, dsp = [], []
        for k in range(8 if name == "ctx_perm" else 6):
            e = make_episode(world, "constant", ("plant", name, tag), k, plant=fn, base_c=c)
            fr, sp, base = fits(e, k, name)
            kl_f, kl_s = score(e, fr), score(e, sp)
            recs.append(1 - (kl_s if name == "span" else kl_f) / base)
            dsp.append((kl_s - kl_f) / base)
        res[name] = {"recovery": [round(v, 3) for v in recs], "D_span_pl": [round(v, 3) for v in dsp]}
    frac = lambda v, f: float(np.mean([f(x) for x in v]))
    res["I2_pass"] = bool(frac(res["free"]["recovery"], lambda x: x >= 0.90) >= 0.9 and
                          frac(res["span"]["recovery"], lambda x: x >= 0.90) >= 0.9)
    res["I3_pass"] = bool(frac(res["out_of_span"]["D_span_pl"], lambda x: x >= 0.30) >= 0.9 and
                          frac(res["span"]["D_span_pl"], lambda x: x <= 0.03) >= 0.9)
    def not_gap(v):  # the planted writer must not meet the family GAP rule (mean >= 0.10 and lower bound > 0.02)
        m, lo, _ = bounds(np.array(v))
        return bool(not (m >= 0.10 and lo > 0.02))
    res["I6_pass"] = not_gap(res["ctx_perm"]["D_span_pl"])
    # I5: the preconditioned writer planted on as many episodes as the family has (46 here, 48 in the gate);
    # B refitted on their fitting probes by the registered procedure, scored on 4 more planted episodes
    n_all = N_DEV + N_EVAL
    pe = [make_episode(world, "constant", ("plant-pre", tag), k, plant=planted_pre, base_c=c) for k in range(n_all + 8)]
    sub = b_fit[1]
    rr = sub.shape[1]
    b_pre = (fit_joint_b(world, pe[:n_all], c, np.concatenate([0.5 * np.eye(rr), 0.5 * np.eye(rr)], axis=1), mu, sub), sub)
    d5 = []
    for k, e in enumerate(pe[n_all:]):
        fr, sp, base = fits(e, k, "pre", b_use=b_pre, keyset="fitted")
        d5.append((score(e, sp) - score(e, fr)) / base)
    res["I5"] = {"D_span_pl": [round(v, 3) for v in d5]}
    res["I5_pass"] = not_gap(d5)
    # I7: planted per-episode shift; the placebo contrast must not pass
    se = [make_episode(world, "constant", ("plant-shift", tag), k, plant=planted_shift, base_c=c) for k in range(8)]
    frees, shifts = [], []
    for k, e in enumerate(se):
        r = e["t"][fit] - e["x"][fit] @ c.T @ g.T
        xfc = e["x"][fit][:, :W] - mu
        shifts.append(to_raw(fit_shift(g, gtg_eig, xfc, r), mu))
        frees.append(fit_free(g, gtg_eig, xfc, r, rng_for("i7-init", tag, k).standard_normal((W, RANK)), True))
    rows = []
    for k, e in enumerate(se):
        other = frees[(k + 1) % len(se)].copy()
        other[:, W] = 0.0
        other = to_raw(other, mu)
        other[:, W] += shifts[k][:, W]
        tgt = e["t"][sco]
        rows.append((sse(g, c + other, e["x"][sco], tgt), sse(g, c + to_raw(frees[k], mu), e["x"][sco], tgt),
                     sse(g, c + shifts[k], e["x"][sco], tgt)))
    rows = np.array(rows)
    dres = (rows[:, 0] - rows[:, 1]) / rows[:, 2].mean()
    m, lo, _ = bounds(dres)
    res["I7"] = {"Delta_res": round(m, 3), "Delta_res_lo": round(lo, 3)}
    res["I7_pass"] = bool(lo <= 0.10)
    return res


# ---------------------------------------------------------------- the v1 estimator (wave-1 registration)
def estimate_family_v1(world: World, dev, ev, tag) -> dict:
    """Rank-8 C_f on the first 4 fitting probes of every episode, no shift class, alone keys, KL_S0 guard
    at 0.20, placebo report-only (wave-1 registration lines 149-189). B = I here: the v1 B fit is omitted
    (the identification refuter's replication showed the flip with either B)."""
    g, gtg_eig, nf = world.g, world.gtg_eig, world.n_fit
    fit, sco = slice(0, nf), slice(nf, nf + N_SCORE)
    allep = dev + ev
    x4 = np.concatenate([e["x"][:4] for e in allep])
    t4 = np.concatenate([e["t"][:4] for e in allep])
    # rank-8 affine constant by ALS on the concatenated 4-probe sets (read side over all 33 coordinates)
    gm = np.linalg.qr(rng_for("v1c", tag).standard_normal((W + 1, RANK)))[0]
    for _ in range(10):
        z = x4 @ gm
        u = solve_kron(gtg_eig, z, g.T @ t4.T @ z)
        phi = g @ u
        pe = np.linalg.eigh(phi.T @ phi)
        xx = np.linalg.eigh(x4.T @ x4)
        rhs = x4.T @ t4 @ phi
        lam = RIDGE * float(np.mean(np.abs(pe[0]))) * float(np.mean(np.abs(xx[0]))) + 1e-12
        gm = np.linalg.qr(xx[1] @ ((xx[1].T @ rhs @ pe[1]) / (np.outer(xx[0], pe[0]) + lam)) @ pe[1].T)[0]
    z = x4 @ gm
    c = solve_kron(gtg_eig, z, g.T @ t4.T @ z) @ gm.T
    rows, frees = [], []
    for j, e in enumerate(ev):
        xf, tf, xs, ts = e["x"][fit], e["t"][fit], e["x"][sco], e["t"][sco]
        r = tf - xf @ c.T @ g.T
        span = fit_rowspace(g, gtg_eig, xf[:, :W], r, e["keys_a"].T, False)
        free = fit_free(g, gtg_eig, xf[:, :W], r, rng_for("v1-free", tag, j).standard_normal((W, RANK)), False)
        frees.append(free)
        rows.append([sse(g, np.zeros((W, W + 1)), xs, ts), sse(g, c, xs, ts), sse(g, c + span, xs, ts), sse(g, c + free, xs, ts)])
    for j, e in enumerate(ev):
        rows[j].append(sse(g, c + frees[(j + 1) % len(ev)], e["x"][sco], e["t"][sco]))
    a = np.array(rows)
    guard = a[:, 1].sum() / a[:, 0].sum()
    e_free = 1 - a[:, 3].sum() / a[:, 1].sum()
    e_span = 1 - a[:, 2].sum() / a[:, 1].sum()
    e_res = 1 - a[:, 4].sum() / a[:, 1].sum()
    d = (a[:, 2] - a[:, 3]) / a[:, 1].mean()
    m, lo, hi = bounds(d)
    if guard < 0.20:
        v = "EPISODE_CONSTANT"
    elif hi <= 0.05:
        v = "TIE"
    elif m >= 0.10 and lo > 0.02:
        v = "GAP"
    else:
        v = "UNDECIDED"
    return {"guard_KLconst_over_KLS0": round(float(guard), 4), "E_free": round(float(e_free), 4),
            "E_span": round(float(e_span), 4), "E_resample": round(float(e_res), 4), "D_span": round(m, 4),
            "span_verdict_ignoring_capacity": v}


# ---------------------------------------------------------------- drivers
def run_teacher(teacher: str, seed: int, d_task: int, n_fit: int, with_v1: bool, plant: bool,
                mean_share: float = 0.5, scenario: str = "central") -> dict:
    """teacher may carry '@cfmisfit': the family's true constant is 5x larger and the estimator keeps only half
    of the fitted constant's linear part, a deliberate constant misfit that I0 must catch before any reading."""
    base_teacher, _, flag = teacher.partition("@")
    CF_MISFIT["scale"], CF_MISFIT["c_true_scale"] = (0.5, 5.0) if flag == "cfmisfit" else (1.0, 1.0)
    out = {"teacher": teacher, "seed": seed, "d_task": d_task, "n_fit": n_fit, "mean_share": mean_share,
           "scenario": scenario, "families": []}
    teacher = base_teacher
    for fam in range(N_FAM):
        world = World(teacher, seed, fam, d_task, n_fit, mean_share=mean_share)
        tag = (teacher, seed, fam, d_task, n_fit)
        dev = [make_episode(world, teacher, ("dev",) + tag, k) for k in range(N_DEV)]
        ev = [make_episode(world, teacher, ("eval",) + tag, k) for k in range(N_EVAL)]
        rec = {"v2": estimate_family(world, dev, ev, tag, plant_checks=plant)}
        if with_v1:
            rec["v1"] = estimate_family_v1(world, dev, ev, tag)
        out["families"].append(rec)
    return out


def main() -> int:
    out_path = sys.argv[1]
    n_proc = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 1
    grid = "--grid" in sys.argv
    if grid:
        # identifiability grid: seed 42, 2 families per cell; planted gates on the first-order cells
        jobs = [(t, 42, d, nf, False, t == "first_order") for t in ("first_order", "value_directed")
                for d in (6, 8, 12, 16, 24, 32) for nf in (16, 24, 32)]
    else:
        v1_teachers = {"constant", "first_order", "rls"}
        jobs = [(t, s, 12, 24, t in v1_teachers, t in ("constant", "first_order")) for t in TEACHERS for s in SEEDS]
        jobs += [("first_order@cfmisfit", s, 12, 24, False, False) for s in SEEDS]
        # wave 1's S1 regime: isotropic reads over the whole 32-d interface, no template mean, 16 fitting probes
        jobs += [(t, s, 32, 16, True, False, 0.0, "wave1_regime") for t in ("constant", "first_order", "rls") for s in SEEDS]
    if n_proc > 1:
        import multiprocessing as mp
        with mp.get_context("spawn").Pool(n_proc) as pool:
            results = pool.starmap(run_teacher, jobs)
    else:
        results = [run_teacher(*j) for j in jobs]
    payload = {"check": "E4 gate repair S1v2: registered v2 estimator on a linear surrogate" + (" (identifiability grid)" if grid else ""),
               "claim_boundary": "estimator semantics in a synthetic linear surrogate; no model, no teacher, no data",
               "config": {"D_B": D_B, "W": W, "M_OUT": M_OUT, "N_DEMO": N_DEMO, "N_SCORE": N_SCORE, "RANK": RANK,
                          "N_DEV": N_DEV, "N_EVAL": N_EVAL, "N_FAM": N_FAM, "RIDGE": RIDGE, "NOISE": NOISE,
                          "seeds": list(SEEDS), "numpy": np.__version__},
               "results": results}
    text = json.dumps(payload, indent=1, sort_keys=True)
    payload["payload_sha256"] = hashlib.sha256(text.encode()).hexdigest()
    with open(out_path, "w") as fh:
        json.dump(payload, fh, indent=1, sort_keys=True)
        fh.write("\n")
    for r in results:
        for f in r["families"]:
            v2 = f["v2"]
            line = (f'{r["teacher"]:22s} {r["scenario"][:6]} s{r["seed"]} d{r["d_task"]} n{r["n_fit"]} | {v2["verdict"]:22s} keys={v2["key_set"]:6s} '
                    f'E_free={v2["E_free"]:.2f} lo={v2["E_free_lo"]:.2f} Dres_lo={v2["Delta_res_lo"]:.2f} D_span={v2["D_span"]:.2f} '
                    f'[{v2["D_span_lo"]:.2f},{v2["D_span_hi"]:.2f}] I0={v2["I0_mean_part_gain"]:.3f} I1={v2["I1_out_of_span_energy"]:.2f} '
                    f'guard={v2["label_prior_guard_ratio"]:.2f}')
            if "planted" in v2:
                p = v2["planted"]
                line += f' | d90={p["probe_read_d90"]} I2={p["I2_pass"]} I3={p["I3_pass"]} I5={p["I5_pass"]} I6={p["I6_pass"]} I7={p["I7_pass"]}'
            if "v1" in f:
                line += f' || v1: {f["v1"]["span_verdict_ignoring_capacity"]} guard={f["v1"]["guard_KLconst_over_KLS0"]:.2f} D={f["v1"]["D_span"]:.2f}'
            print(line, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
