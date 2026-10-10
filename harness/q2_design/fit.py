"""Maximum marginal likelihood fit of the model's components to S1a's records (CPU).

The model is ``model``'s, fitted on S1a's two realized sessions per size. With two sessions
a session variance has one degree of freedom per size, so the fit holds the realized
sessions as fixed effects (omega_z: the S2 - S1 shift; kappa_z: the S2 - S1 change of the
harness effect), as every S1a estimand is defined conditional on them, and the variances
for new sessions (sigma_g, sigma_k) are moment estimates from those fixed effects
(``session_variances``), with wide upper bounds.

Likelihood. Per task, the random effects are the task logits (eta0_4B, eta0_9B), the harness
contrasts (beta_4B, beta_9B), the task x session effects e_tzs and the task x harness x
session effects f_tzhs. f is integrated per cell by Gauss-Hermite into a table of
G_{y,n}(eta) = E_f[p^y (1 - p)^(n - y)]; e, common to a (size, session)'s two harness
cells, is a discretised convolution along the eta0 axis (bin probabilities on the grid's
step) of the product of the two cells' G values; the task-level effects are summed
on a fixed grid (eta0: -50..50, beta - c: -25..25, step 0.25), with the bivariate normal
priors discretised by exact bin probabilities (edge bins hold the tails). The four-
dimensional sum factorises as sum_{ik} L4[i,k] (A L9 B^T)[i,k], where A and B are the
discretised priors over (eta0_4B, eta0_9B) and (beta_4B, beta_9B). Binomial coefficients
are omitted (constant). Optimiser: L-BFGS-B on transformed parameters with finite
differences; each size's grids are cached on that size's cell-level parameters.
"""

from __future__ import annotations

import math
import time
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy import ndimage, optimize
from scipy.special import ndtr

from harness.q2_design.model import SIZES, Params, SizeParams, expit

GH_F_X, GH_F_W = np.polynomial.hermite_e.hermegauss(32)
GH_F_W = GH_F_W / GH_F_W.sum()
ETA_STEP = 0.01
ETA_TAB = np.arange(-95.0, 95.0 + 1e-9, ETA_STEP)

# Per-size parameter vector (transformed) and its bounds.
SIZE_KEYS = ("mu", "log_sigma_a", "c", "log_sigma_b", "omega", "kappa", "sigma_e", "sigma_f")
SIZE_BOUNDS = {
    "mu": (-25.0, 25.0),
    "log_sigma_a": (math.log(0.1), math.log(12.0)),
    "c": (-8.0, 8.0),
    "log_sigma_b": (math.log(0.02), math.log(8.0)),
    "omega": (-6.0, 6.0),
    "kappa": (-6.0, 6.0),
    "sigma_e": (0.0, 5.0),
    "sigma_f": (0.0, 5.0),
}
RHO_BOUNDS = (math.atanh(-0.99), math.atanh(0.995))
# Spike-and-slab harness contrast (coordinate 18, logit of w): a share w of tasks is
# harness-sensitive in both sizes (slab: the BVN with the sigma_b SDs), the rest has no
# task-specific harness effect (spike at beta = c). Without coordinate 18, w = 1 (normal).
W_BOUNDS = (-6.0, 6.0)
CELL_KEYS = ("c", "omega", "kappa", "sigma_e", "sigma_f")  # enter the per-size grids


@dataclass(frozen=True)
class Grid:
    u: np.ndarray
    v: np.ndarray

    @staticmethod
    def default(step: float = 0.25) -> Grid:
        return Grid(u=np.arange(-50.0, 50.0 + 1e-9, step), v=np.arange(-25.0, 25.0 + 1e-9, step))


def bin_probs(grid: np.ndarray, mean: np.ndarray | float, sd: float) -> np.ndarray:
    """P(x in bin_i) for x ~ N(mean, sd^2); bins split at grid midpoints, edges to +-inf.

    ``mean`` may be an array (one row per mean)."""
    edges = np.concatenate([[-np.inf], (grid[1:] + grid[:-1]) / 2, [np.inf]])
    sd = max(float(sd), 1e-9)
    m = np.asarray(mean, dtype=float)[..., None]
    cdf = ndtr((edges - m) / sd)
    return np.diff(cdf, axis=-1)


def bvn_matrix(grid: np.ndarray, mean: tuple[float, float], sd: tuple[float, float], rho: float):
    """Discretised BVN: P(x1 in bin_i) * P(x2 in bin_j | x1 = grid_i), shape (n, n)."""
    p1 = bin_probs(grid, mean[0], sd[0])
    cond_mean = mean[1] + rho * sd[1] / max(sd[0], 1e-9) * (grid - mean[0])
    cond_sd = sd[1] * math.sqrt(max(1e-12, 1 - rho * rho))
    return p1[:, None] * bin_probs(grid, cond_mean, cond_sd)


def g_tables(sigma_f: float, n_max: int) -> dict[tuple[int, int], np.ndarray]:
    """G_{y,n}(eta) = E_f[expit(eta + f)^y (1 - expit(eta + f))^(n - y)], f ~ N(0, sigma_f^2)."""
    if sigma_f > 0:
        p = expit(ETA_TAB[:, None] + sigma_f * GH_F_X)
        w = GH_F_W
    else:
        p = expit(ETA_TAB)[:, None]
        w = np.ones(1)
    q = 1.0 - p
    out = {}
    for n in range(n_max + 1):
        for y in range(n + 1):
            out[(y, n)] = (p**y * q ** (n - y)) @ w
    return out


def patterns(y: np.ndarray) -> tuple[list[tuple], np.ndarray]:
    """Unique per-(size, task) cell patterns and each task's pattern index per size.

    ``y`` is (Z, K, 2, 2, R). A pattern is ((y_hs), (n_hs)) over (h, s) in row order.
    Returns the pattern list and an index array (Z, K)."""
    counts = np.nansum(y, axis=-1).astype(int)
    n = np.sum(np.isfinite(y), axis=-1).astype(int)
    uniq: dict[tuple, int] = {}
    index = np.empty(y.shape[:2], dtype=int)
    for z in range(y.shape[0]):
        for k in range(y.shape[1]):
            key = (tuple(counts[z, k].ravel()), tuple(n[z, k].ravel()))
            index[z, k] = uniq.setdefault(key, len(uniq))
    return list(uniq), index


def interp(x: np.ndarray, table: np.ndarray) -> np.ndarray:
    """Linear interpolation of a table on ETA_TAB (uniform), clamped at the ends."""
    q = (x - ETA_TAB[0]) / ETA_STEP
    i = np.clip(q.astype(np.int64), 0, table.size - 2)
    f = np.clip(q - i, 0.0, 1.0)
    return table[i] * (1.0 - f) + table[i + 1] * f


def e_kernel(sigma_e: float, step: float) -> np.ndarray | None:
    """The task x session effect discretised on the eta0 grid's step (bin probabilities)."""
    if sigma_e <= 0:
        return None
    half = int(math.ceil(6 * sigma_e / step))
    centres = np.arange(-half, half + 1) * step
    edges = np.concatenate([centres - step / 2, [centres[-1] + step / 2]])
    w = np.diff(ndtr(edges / sigma_e))
    return w / w.sum()


def pattern_likelihood(
    pattern: tuple, cell: dict[str, float], grid: Grid, tables: dict
) -> np.ndarray:
    """L(eta0, beta - c) on the grid for one size's cell pattern (two harnesses, two sessions).

    Per session, the two harness cells' G values multiply; the task x session effect e,
    common to both cells, is a convolution along the eta0 axis with e's discretised
    density (edge values extended: the cells are deterministic there)."""
    ys, ns = np.array(pattern[0]).reshape(2, 2), np.array(pattern[1]).reshape(2, 2)
    U, V = grid.u[:, None], grid.v[None, :]
    kern = e_kernel(cell["sigma_e"], float(grid.u[1] - grid.u[0]))
    lik = np.ones((grid.u.size, grid.v.size))
    for s in range(2):
        ss = s - 0.5
        prod = np.ones_like(lik)
        for h in range(2):
            if ns[h, s] == 0:
                continue
            arg = U + ((h - 0.5) * (cell["c"] + V + ss * cell["kappa"]) + ss * cell["omega"])
            prod *= interp(arg, tables[(int(ys[h, s]), int(ns[h, s]))])
        if kern is not None:
            prod = ndimage.convolve1d(prod, kern[::-1], axis=0, mode="nearest")
        lik *= prod
    return lik


def unpack(x: np.ndarray) -> tuple[list[dict[str, float]], float, float]:
    sizes = []
    for zi in range(2):
        v = dict(zip(SIZE_KEYS, x[8 * zi : 8 * zi + 8], strict=True))
        sizes.append(
            {
                "mu": v["mu"],
                "sigma_a": math.exp(v["log_sigma_a"]),
                "c": v["c"],
                "sigma_b": math.exp(v["log_sigma_b"]),
                "omega": v["omega"],
                "kappa": v["kappa"],
                "sigma_e": v["sigma_e"],
                "sigma_f": v["sigma_f"],
            }
        )
    return sizes, math.tanh(x[16]), math.tanh(x[17])


def pack(sizes: Sequence[dict[str, float]], rho_a: float, rho_b: float) -> np.ndarray:
    x = []
    for s in sizes:
        x += [s["mu"], math.log(s["sigma_a"]), s["c"], math.log(s["sigma_b"]), s["omega"],
              s["kappa"], s["sigma_e"], s["sigma_f"]]  # fmt: skip
    return np.array(x + [math.atanh(rho_a), math.atanh(rho_b)])


def bounds(n: int = 18) -> list[tuple[float, float]]:
    out = [SIZE_BOUNDS[k] for k in SIZE_KEYS] * 2 + [RHO_BOUNDS, RHO_BOUNDS]
    return out + [W_BOUNDS] if n == 19 else out


def w_of(x: np.ndarray) -> float:
    """The harness-sensitive share w (1 for the normal model)."""
    return float(1 / (1 + math.exp(-x[18]))) if len(x) > 18 else 1.0


def harness_matrix(
    v: np.ndarray, sizes: Sequence[dict[str, float]], rho_b: float, w: float
) -> np.ndarray:
    """The discretised prior of (beta_4B - c_4B, beta_9B - c_9B): the BVN slab, mixed with
    a spike at 0 in both sizes when w < 1."""
    B = bvn_matrix(v, (0.0, 0.0), (sizes[0]["sigma_b"], sizes[1]["sigma_b"]), rho_b)
    if w < 1.0:
        i0 = int(np.argmin(np.abs(v)))
        B = w * B
        B[i0, i0] += 1.0 - w
    return B


class Likelihood:
    """The joint (two-size) marginal log-likelihood of one outcome array."""

    def __init__(self, y: np.ndarray, grid: Grid | None = None):
        if y.ndim != 5 or y.shape[0] != 2 or y.shape[2:4] != (2, 2):
            raise ValueError("the fit takes S1a-shaped data: (2 sizes, K, 2, 2 sessions, R)")
        self.y = y
        self.grid = grid or Grid.default()
        self.pats, self.index = patterns(y)
        self.n_max = int(np.max(np.sum(np.isfinite(y), axis=-1)))
        self._cache: dict[tuple, dict[int, np.ndarray]] = {}
        self._tables: dict[float, dict] = {}
        self.evaluations = 0

    def grids(self, zi: int, cell: dict[str, float]) -> dict[int, np.ndarray]:
        """The pattern likelihoods of size zi at its cell-level parameters (cached)."""
        key = (zi,) + tuple(round(cell[k], 12) for k in CELL_KEYS)
        if key not in self._cache:
            sf = round(cell["sigma_f"], 12)
            if sf not in self._tables:
                if len(self._tables) > 8:
                    self._tables.clear()
                self._tables[sf] = g_tables(sf, self.n_max)
            need = sorted(set(self.index[zi]))
            if len(self._cache) > 64:
                self._cache.clear()
            self._cache[key] = {
                p: pattern_likelihood(self.pats[p], cell, self.grid, self._tables[sf]) for p in need
            }
        return self._cache[key]

    def task_likelihoods(self, x: np.ndarray) -> np.ndarray:
        sizes, rho_a, rho_b = unpack(x)
        L4 = self.grids(0, sizes[0])
        L9 = self.grids(1, sizes[1])
        A = bvn_matrix(self.grid.u, (sizes[0]["mu"], sizes[1]["mu"]),
                       (sizes[0]["sigma_a"], sizes[1]["sigma_a"]), rho_a)  # fmt: skip
        B = harness_matrix(self.grid.v, sizes, rho_b, w_of(x))
        M = {q: A @ L9[q] @ B.T for q in sorted(set(self.index[1]))}
        lik = np.array(
            [np.sum(L4[self.index[0, k]] * M[self.index[1, k]]) for k in range(self.y.shape[1])]
        )
        self.evaluations += 1
        return lik

    def loglik(self, x: np.ndarray) -> float:
        lik = self.task_likelihoods(x)
        return float(np.sum(np.log(np.maximum(lik, 1e-300))))

    def size_loglik(self, zi: int, xs: np.ndarray) -> float:
        """One size alone (no cross-size terms): xs is that size's 8-vector."""
        s, _, _ = unpack(np.concatenate([xs, xs, [0.0, 0.0]]))
        cell = s[0]
        L = self.grids(zi, cell)
        a = bin_probs(self.grid.u, cell["mu"], cell["sigma_a"])
        b = bin_probs(self.grid.v, 0.0, cell["sigma_b"])
        lik = np.array([a @ L[self.index[zi, k]] @ b for k in range(self.y.shape[1])])
        return float(np.sum(np.log(np.maximum(lik, 1e-300))))


def start_values(y: np.ndarray) -> list[dict[str, float]]:
    out = []
    for zi in range(2):
        p = float(np.nanmean(y[zi]))
        out.append({"mu": math.log(p / (1 - p)) - 1.0, "sigma_a": 4.0, "c": 0.0, "sigma_b": 1.0,
                    "omega": 0.0, "kappa": 0.0, "sigma_e": 0.3, "sigma_f": 0.3})  # fmt: skip
    return out


def _minimize(fun, x0, bnds, maxiter: int = 400):
    return optimize.minimize(
        fun, x0, method="L-BFGS-B", bounds=bnds,
        options={"maxiter": maxiter, "ftol": 1e-10, "gtol": 1e-6, "eps": 1e-5},
    )  # fmt: skip


def fit(
    y: np.ndarray,
    *,
    starts: Sequence[dict[str, float]] | None = None,
    grid: Grid | None = None,
    fixed: dict[int, float] | None = None,
    x0: np.ndarray | None = None,
    harness: str = "normal",
    log=print,
) -> dict[str, Any]:
    """ML fit: per-size fits from the start values, then the joint fit with rho_a, rho_b.

    ``fixed`` maps coordinates of the 18-vector to held values (for profile likelihoods);
    ``x0`` warm-starts the joint fit and skips the per-size stage.
    """
    like = Likelihood(y, grid)
    t0 = time.time()
    fixed = dict(fixed or {})
    bnds = bounds()
    if x0 is None:
        starts = list(starts or start_values(y))
        per_size = []
        for zi in range(2):
            xs0 = pack([starts[zi], starts[zi]], 0.0, 0.0)[:8]
            res = _minimize(lambda v, zi=zi: -like.size_loglik(zi, v), xs0, bnds[:8])
            per_size.append(res.x)
            log({"stage": "per-size", "size": SIZES[zi], "loglik": -res.fun, "nit": res.nit,
                 "seconds": round(time.time() - t0, 1)})  # fmt: skip
        x0 = np.concatenate(per_size + [np.array([math.atanh(0.8), math.atanh(0.5)])])
        if harness == "spike-slab":
            x0[[3, 11]] += math.log(math.sqrt(2.0))  # slab SDs start wider than the normal's
            x0 = np.concatenate([x0, [0.0]])  # w = 0.5
    x0 = np.array(x0, dtype=float)
    bnds = bounds(len(x0))
    free = [i for i in range(len(x0)) if i not in fixed]

    def full(v: np.ndarray) -> np.ndarray:
        x = x0.copy()
        x[free] = v
        for i, val in fixed.items():
            x[i] = val
        return x

    res = _minimize(lambda v: -like.loglik(full(v)), x0[free], [bnds[i] for i in free])
    x = full(res.x)
    log({"stage": "joint", "loglik": -res.fun, "nit": res.nit, "message": str(res.message),
         "evaluations": like.evaluations, "seconds": round(time.time() - t0, 1)})  # fmt: skip
    return {"x": x, "loglik": -float(res.fun), "converged": bool(res.success),
            "message": str(res.message), "nit": int(res.nit), "likelihood": like}  # fmt: skip


def hessian_block(like: Likelihood, x: np.ndarray, idx: Sequence[int], h: float = 1e-3):
    """Observed information over the coordinates ``idx`` (central differences)."""
    n = len(idx)
    H = np.zeros((n, n))
    f0 = like.loglik(x)

    def f(d: dict[int, float]) -> float:
        xx = x.copy()
        for i, v in d.items():
            xx[i] += v
        return like.loglik(xx)

    for a in range(n):
        i = idx[a]
        H[a, a] = (f({i: h}) - 2 * f0 + f({i: -h})) / h**2
        for b in range(a + 1, n):
            j = idx[b]
            H[a, b] = H[b, a] = (
                f({i: h, j: h}) - f({i: h, j: -h}) - f({i: -h, j: h}) + f({i: -h, j: -h})
            ) / (4 * h * h)
    return -H


def session_variances(est: list[dict[str, float]], se: list[dict[str, float]]) -> dict[str, Any]:
    """Moment estimates of the new-session SDs from the realized sessions' fixed effects.

    With k_zhs ~ N(0, sigma_k^2) per harness and g_zs ~ N(0, sigma_g^2):
    Var(kappa_z) = 4 sigma_k^2 and Var(omega_z) = 2 sigma_g^2 + sigma_k^2. Pooled over the
    two sizes (two degrees of freedom), each estimate corrects for the fixed effect's own
    sampling variance (its SE^2) and is truncated at 0. Upper bounds are one-sided 95%
    from chi-square(2): sum_z est_z^2 / chi2_{0.05,2} minus the mean SE^2.
    """
    chi2_05_2 = 0.10259
    k2 = np.mean([e["kappa"] ** 2 - s["kappa"] ** 2 for e, s in zip(est, se, strict=True)])
    o2 = np.mean([e["omega"] ** 2 - s["omega"] ** 2 for e, s in zip(est, se, strict=True)])
    sk2 = max(0.0, k2 / 4)
    sg2 = max(0.0, (o2 - sk2) / 2)
    k2_up = sum(e["kappa"] ** 2 for e in est) / chi2_05_2 - np.mean([s["kappa"] ** 2 for s in se])
    o2_up = sum(e["omega"] ** 2 for e in est) / chi2_05_2 - np.mean([s["omega"] ** 2 for s in se])
    sk2_up = max(0.0, k2_up / 4)
    sg2_up = max(0.0, (o2_up - 0.0) / 2)  # sigma_k taken as 0 for the sigma_g bound
    return {
        "sigma_g": math.sqrt(sg2),
        "sigma_k": math.sqrt(sk2),
        "sigma_g_upper95": math.sqrt(sg2_up),
        "sigma_k_upper95": math.sqrt(sk2_up),
        "method": "moments of the fixed effects, pooled over sizes (2 df), SE-corrected",
    }


def to_params(x: np.ndarray, sess: dict[str, Any]) -> Params:
    sizes, rho_a, rho_b = unpack(x)
    return Params(
        sizes={
            z: SizeParams(**sizes[zi], sigma_g=sess["sigma_g"], sigma_k=sess["sigma_k"])
            for zi, z in enumerate(SIZES)
        },
        rho_a=rho_a,
        rho_b=rho_b,
        w_b=w_of(x),
    )


def profile(
    y: np.ndarray, x_hat: np.ndarray, ll_hat: float, coord: int, values: Sequence[float], log=print
) -> list[dict[str, float]]:
    """Profile log-likelihood of one coordinate (others re-optimised, warm-started)."""
    out = []
    x = x_hat.copy()
    for v in values:
        r = fit(y, fixed={coord: v}, x0=x, log=lambda _m: None)
        x = r["x"]
        row = {"value": float(v), "loglik": r["loglik"], "lr": 2 * (ll_hat - r["loglik"])}
        out.append(row)
        log({"profile": coord, **row})
    return out


def posterior_bank(
    like: Likelihood, x: np.ndarray, n_draws: int, seed: int
) -> dict[str, np.ndarray]:
    """Posterior draws of each task's (eta0_4B, eta0_9B) and (beta_4B, beta_9B) given its
    records, at the fitted parameters: (K, n_draws, 2) each.

    Sequential sampling on the grid: (i, k) from L4 * (A L9 B^T); j | i, k from
    A[i, :] * (L9 B^T)[:, k]; l | j, k from B[k, :] * L9[j, :]; then a uniform jitter
    within the grid cell."""
    rng = np.random.default_rng(seed)
    sizes, rho_a, rho_b = unpack(x)
    g = like.grid
    L4, L9 = like.grids(0, sizes[0]), like.grids(1, sizes[1])
    A = bvn_matrix(g.u, (sizes[0]["mu"], sizes[1]["mu"]),
                   (sizes[0]["sigma_a"], sizes[1]["sigma_a"]), rho_a)  # fmt: skip
    B = harness_matrix(g.v, sizes, rho_b, w_of(x))
    du, dv = g.u[1] - g.u[0], g.v[1] - g.v[0]
    K = like.y.shape[1]
    eta0 = np.empty((K, n_draws, 2))
    beta = np.empty((K, n_draws, 2))

    def draw(prob: np.ndarray) -> np.ndarray:
        """One categorical draw per row of ``prob`` (rows need not be normalised)."""
        c = np.cumsum(prob, axis=-1)
        u = rng.random(prob.shape[:-1] + (1,)) * c[..., -1:]
        return np.minimum((c < u).sum(axis=-1), prob.shape[-1] - 1)

    for k in range(K):
        l4, l9 = L4[like.index[0, k]], L9[like.index[1, k]]
        W = l9 @ B.T  # (nu, nv): sum over l of L9[j, l] B[k', l]
        cm = np.cumsum((l4 * (A @ W)).ravel())
        ik = np.searchsorted(cm, rng.random(n_draws) * cm[-1], side="right")
        i, kk = np.divmod(np.minimum(ik, cm.size - 1), g.v.size)
        j = draw(A[i, :] * W[:, kk].T)
        ll = draw(B[kk, :] * l9[j, :])
        jit = rng.random((n_draws, 4)) - 0.5
        eta0[k, :, 0] = g.u[i] + jit[:, 0] * du
        eta0[k, :, 1] = g.u[j] + jit[:, 1] * du
        beta[k, :, 0] = sizes[0]["c"] + g.v[kk] + jit[:, 2] * dv
        beta[k, :, 1] = sizes[1]["c"] + g.v[ll] + jit[:, 3] * dv
    return {
        "eta0": eta0,
        "beta": beta,
        "sigma_b": np.array([sizes[0]["sigma_b"], sizes[1]["sigma_b"]]),
    }
