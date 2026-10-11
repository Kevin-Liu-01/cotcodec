"""The generative model of S1a-shaped data, for arbitrary designs (seeded, CPU).

For size z, task t, harness h (0 = H-OSW-fixed, 1 = H-GA), session s and rerun r:

    logit p_zths = eta0_tz + (h - 1/2) * beta_tz + g_zs + k_zhs + e_tzs + f_tzhs
    y_zthsr ~ Bernoulli(p_zths), independently over the R within-session reruns

* task: (eta0_t4B, eta0_t9B) ~ BVN((mu_4B, mu_9B), (sigma_a_4B, sigma_a_9B), rho_a);
* task x harness: the harness contrast (beta_t4B, beta_t9B) ~ BVN((c_4B, c_9B),
  (sigma_b_4B, sigma_b_9B), rho_b), independent of the task effect; c_z is the harness
  main effect on the logit scale (H-GA minus H-OSW-fixed);
* session: g_zs ~ N(0, sigma_g^2) common to both harnesses; harness x session k_zhs ~
  N(0, sigma_k^2) per harness, common to the session's tasks (the registration's kappa);
  sessions are separate per size (the sizes run one after the other);
* task x session e_tzs ~ N(0, sigma_e^2); task x harness x session f_tzhs ~ N(0, sigma_f^2);
* rerun: the Bernoulli draw given p (greedy decoding: the rerun variation S1a measures).

This is the registration's own operating-characteristics model (section 10.2,
``sim_s1a_v2.py``) with the components fitted to S1a's records (``fit``). Two task
sources: ``parametric`` draws new tasks from the fitted population; ``pool`` draws S1a's
113 eligible tasks with their task-level effects sampled from their posterior given S1a's
records (``fit.posterior_bank``), so the pool's real difficulty mix is kept. Two session
sources for a two-session design: ``random`` draws new sessions; ``realized`` holds S1a's
two sessions at their fitted fixed effects (omega: S2 - S1 shift, kappa: S2 - S1 change of
the harness effect), which is how every S1a estimand is defined (conditional on the
realized sessions).
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field, replace
from typing import Any

import numpy as np

SIZES = ("4B", "9B")
GH_X, GH_W = np.polynomial.hermite_e.hermegauss(40)
GH_W = GH_W / GH_W.sum()


def expit(x: np.ndarray) -> np.ndarray:
    return 0.5 * (1.0 + np.tanh(0.5 * np.asarray(x, dtype=float)))


@dataclass(frozen=True)
class SizeParams:
    """Per-size components on the logit scale (fitted, or set by a scenario)."""

    mu: float  # mean task logit (harness-averaged, at the average session)
    sigma_a: float  # task SD
    c: float  # harness main effect, H-GA minus H-OSW-fixed
    sigma_b: float  # SD of the per-task harness contrast (task x harness)
    sigma_e: float  # task x session SD
    sigma_f: float  # task x harness x session SD
    omega: float = 0.0  # realized sessions: S2 - S1 shift (fixed effect)
    kappa: float = 0.0  # realized sessions: S2 - S1 change of the harness effect
    sigma_g: float = 0.0  # new sessions: session SD (common to harnesses)
    sigma_k: float = 0.0  # new sessions: harness x session SD, per harness


@dataclass(frozen=True)
class Params:
    sizes: dict[str, SizeParams]
    rho_a: float  # task-effect correlation across sizes
    rho_b: float  # harness-contrast correlation across sizes
    # Share of harness-sensitive tasks (spike-and-slab contrast; 1 = the normal model): with
    # probability 1 - w_b a task's contrast is c_z in both sizes, else c_z plus the BVN slab.
    w_b: float = 1.0

    def to_json(self) -> dict[str, Any]:
        return {"sizes": {z: asdict(p) for z, p in self.sizes.items()},
                "rho_a": self.rho_a, "rho_b": self.rho_b, "w_b": self.w_b}  # fmt: skip

    @staticmethod
    def from_json(obj: dict[str, Any]) -> Params:
        return Params(
            sizes={z: SizeParams(**v) for z, v in obj["sizes"].items()},
            rho_a=float(obj["rho_a"]),
            rho_b=float(obj["rho_b"]),
            w_b=float(obj.get("w_b", 1.0)),
        )


@dataclass(frozen=True)
class Scenario:
    """Harness-effect scenario on top of fitted nuisance components.

    The simulated contrast is beta_sim = c_z + lam * (beta_fit - c_fit_z): ``c`` replaces the
    main effect per size (None keeps the fit's), ``lam`` scales the task-specific part
    (0 removes it), and ``kappa_scale`` scales the realized harness x session effect and
    sigma_k. ``harness_null()`` is the world with no harness effect of any kind.
    """

    name: str = "fitted"
    c: dict[str, float] | None = None
    lam: float = 1.0
    kappa_scale: float = 1.0
    session_scale: float = 1.0  # scales sigma_g, sigma_k (new sessions only)
    sigma_e: dict[str, float] | None = None  # replaces the fit's task x session SD
    sigma_f: dict[str, float] | None = None  # replaces the fit's task x harness x session SD

    @staticmethod
    def harness_null() -> Scenario:
        return Scenario(name="harness-null", c={z: 0.0 for z in SIZES}, lam=0.0, kappa_scale=0.0)

    def apply(self, params: Params) -> tuple[Params, dict[str, float]]:
        """The scenario's parameters and the fitted main effects (needed to re-centre a
        pool-posterior draw of beta)."""
        c_fit = {z: p.c for z, p in params.sizes.items()}
        sizes = {}
        for z, p in params.sizes.items():
            sizes[z] = replace(
                p,
                c=p.c if self.c is None else float(self.c[z]),
                sigma_b=p.sigma_b * self.lam,
                kappa=p.kappa * self.kappa_scale,
                sigma_k=p.sigma_k * self.kappa_scale * self.session_scale,
                sigma_g=p.sigma_g * self.session_scale,
                sigma_e=p.sigma_e if self.sigma_e is None else float(self.sigma_e[z]),
                sigma_f=p.sigma_f if self.sigma_f is None else float(self.sigma_f[z]),
            )
        return replace(params, sizes=sizes), c_fit


@dataclass(frozen=True)
class Design:
    """A successor design: sizes, tasks, sessions per size and within-session reruns.

    ``tasks`` says how the K tasks come from the 113-task eligible pool: ``base`` (S1a's 32
    base tasks; K = 32), ``extend`` (the base, then the registered extension order),
    ``srs`` (K at random without replacement) or ``stratified`` (the registered
    largest-remainder apportionment over domains, at random within each domain).
    """

    K: int = 32
    S: int = 2
    R: int = 2
    sizes: tuple[str, ...] = SIZES
    tasks: str = "base"
    name: str = field(default="")

    def __post_init__(self) -> None:
        if not set(self.sizes) <= set(SIZES) or list(self.sizes) != sorted(
            self.sizes, key=SIZES.index
        ):
            raise ValueError("sizes must be an ordered subset of (4B, 9B)")
        if self.S < 1 or self.R < 1 or self.K < 2:
            raise ValueError("need K >= 2, S >= 1, R >= 1")
        if self.tasks not in ("base", "extend", "srs", "stratified"):
            raise ValueError("tasks must be base, extend, srs or stratified")
        if self.tasks == "base" and self.K != 32:
            raise ValueError("tasks='base' is S1a's 32 base tasks")

    @property
    def episodes(self) -> int:
        return len(self.sizes) * self.K * 2 * self.S * self.R


S1A_DESIGN = Design(K=32, S=2, R=2, sizes=SIZES, tasks="base", name="S1a")


# --------------------------------------------------------------------------- task sources


def apportion(counts: dict[str, int], k: int) -> dict[str, int]:
    """Plain largest-remainder apportionment of k over domains, ties by domain name
    (``plan.draw_tasks``' allocation rule)."""
    total = sum(counts.values())
    quota = {d: k * n / total for d, n in counts.items()}
    alloc = {d: int(math.floor(q)) for d, q in quota.items()}
    rest = k - sum(alloc.values())
    order = sorted(counts, key=lambda d: (-(quota[d] - alloc[d]), d))
    for d in order[:rest]:
        alloc[d] += 1
    return alloc


def select_pool_tasks(
    design: Design,
    pool: tuple[str, ...],
    n_base: int,
    domains: dict[str, str],
    rng: np.random.Generator,
    nsim: int,
) -> np.ndarray:
    """Pool indices (nsim, K) of the tasks each simulated data set uses."""
    n = len(pool)
    if n < design.K:
        raise ValueError(f"K = {design.K} exceeds the {n}-task pool")
    if design.tasks == "base":
        return np.tile(np.arange(n_base), (nsim, 1))
    if design.tasks == "extend":
        return np.tile(np.arange(design.K), (nsim, 1))
    if design.tasks == "srs":
        return np.argsort(rng.random((nsim, n)), axis=1)[:, : design.K]
    by_dom: dict[str, list[int]] = {}
    for i, t in enumerate(pool):
        by_dom.setdefault(domains[t], []).append(i)
    alloc = apportion({d: len(v) for d, v in by_dom.items()}, design.K)
    out = np.empty((nsim, design.K), dtype=int)
    col = 0
    for d in sorted(by_dom):
        m = alloc[d]
        if not m:
            continue
        idx = np.asarray(by_dom[d])
        pick = np.argsort(rng.random((nsim, len(idx))), axis=1)[:, :m]
        out[:, col : col + m] = idx[pick]
        col += m
    return out


def _bvn(rng: np.random.Generator, shape: tuple[int, ...], sd: tuple[float, float], rho: float):
    z1 = rng.standard_normal(shape)
    z2 = rng.standard_normal(shape)
    return np.stack(
        [sd[0] * z1, sd[1] * (rho * z1 + math.sqrt(max(0.0, 1 - rho * rho)) * z2)], axis=-1
    )


def task_effects(
    params: Params,
    c_fit: dict[str, float],
    design: Design,
    nsim: int,
    rng: np.random.Generator,
    source: str,
    bank: dict[str, Any] | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray | None]:
    """eta0 and beta, each (nsim, K, 2 sizes in SIZES order); and the pool indices used."""
    sp = [params.sizes[z] for z in SIZES]
    if source == "parametric":
        a = _bvn(rng, (nsim, design.K), (sp[0].sigma_a, sp[1].sigma_a), params.rho_a)
        b = _bvn(rng, (nsim, design.K), (sp[0].sigma_b, sp[1].sigma_b), params.rho_b)
        if params.w_b < 1.0:  # spike-and-slab; no extra draw for the normal model
            b = b * (rng.random((nsim, design.K, 1)) < params.w_b)
        eta0 = a + np.array([p.mu for p in sp])
        beta = b + np.array([p.c for p in sp])
        return eta0, beta, None
    if source != "pool" or bank is None:
        raise ValueError("source must be 'parametric', or 'pool' with a posterior bank")
    idx = select_pool_tasks(
        design, tuple(bank["pool"]), int(bank["n_base"]), bank["domains"], rng, nsim
    )
    n_draws = bank["eta0"].shape[1]
    d = rng.integers(0, n_draws, size=idx.shape)
    eta0 = bank["eta0"][idx, d]  # (nsim, K, 2)
    beta_fit = bank["beta"][idx, d]
    cf = np.array([c_fit[z] for z in SIZES])
    lam = np.array([sp[i].sigma_b / bank["sigma_b"][i] if bank["sigma_b"][i] > 0 else 0.0
                    for i in range(2)])  # fmt: skip
    beta = np.array([p.c for p in sp]) + lam * (beta_fit - cf)
    return eta0, beta, idx


# --------------------------------------------------------------------------- simulation


def simulate(
    params: Params,
    design: Design,
    nsim: int,
    rng: np.random.Generator,
    *,
    source: str = "parametric",
    sessions: str = "random",
    scenario: Scenario | None = None,
    bank: dict[str, Any] | None = None,
) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """nsim data sets of shape (Z, K, 2, S, R) in the registered array convention, and the
    realized truth of each (the cell probabilities' contrasts the estimands target)."""
    scenario = scenario or Scenario()
    par, c_fit = scenario.apply(params)
    if sessions not in ("random", "realized"):
        raise ValueError("sessions must be 'random' or 'realized'")
    if sessions == "realized" and design.S != 2:
        raise ValueError("realized sessions exist only for a two-session design")
    eta0, beta, idx = task_effects(par, c_fit, design, nsim, rng, source, bank)
    zi = [SIZES.index(z) for z in design.sizes]
    eta0, beta = eta0[..., zi], beta[..., zi]  # (nsim, K, Z)
    Z, K, S, R = len(zi), design.K, design.S, design.R
    sp = [par.sizes[z] for z in design.sizes]
    hh = np.array([-0.5, 0.5])
    # (nsim, Z, K, H, S)
    lin = (np.moveaxis(eta0, -1, 1)[..., None, None]
           + np.moveaxis(beta, -1, 1)[..., None, None] * hh[:, None])  # fmt: skip
    if sessions == "realized":
        ss = np.array([-0.5, 0.5])
        om = np.array([p.omega for p in sp]).reshape(1, Z, 1, 1, 1)
        ka = np.array([p.kappa for p in sp]).reshape(1, Z, 1, 1, 1)
        lin = lin + om * ss + ka * hh[:, None] * ss
    else:
        sg = np.array([p.sigma_g for p in sp]).reshape(1, Z, 1, 1, 1)
        sk = np.array([p.sigma_k for p in sp]).reshape(1, Z, 1, 1, 1)
        lin = lin + sg * rng.standard_normal((nsim, Z, 1, 1, S))
        lin = lin + sk * rng.standard_normal((nsim, Z, 1, 2, S))
    se = np.array([p.sigma_e for p in sp]).reshape(1, Z, 1, 1, 1)
    sf = np.array([p.sigma_f for p in sp]).reshape(1, Z, 1, 1, 1)
    if np.any(se > 0):
        lin = lin + se * rng.standard_normal((nsim, Z, K, 1, S))
    if np.any(sf > 0):
        lin = lin + sf * rng.standard_normal((nsim, Z, K, 2, S))
    p = expit(lin)
    y = (rng.random((nsim, Z, K, 2, S, R)) < p[..., None]).astype(float)
    truth = {
        # The realized-session harness effect: what the registered delta targets.
        "delta_realized": (p[:, :, :, 1] - p[:, :, :, 0]).mean(axis=(1, 2, 3)),
        "success_realized": p.mean(axis=(2, 4)),  # (nsim, Z, H)
    }
    if idx is not None:
        truth["pool_index"] = idx
    return y, truth


# --------------------------------------------------------------------------- population truth


def session_marginal(eta: np.ndarray, sd: float) -> np.ndarray:
    """E over a N(0, sd^2) logit shift of expit(eta + shift)."""
    if sd <= 0:
        return expit(eta)
    return (expit(np.asarray(eta)[..., None] + sd * GH_X) * GH_W).sum(-1)


def population(
    params: Params,
    scenario: Scenario | None = None,
    *,
    source: str = "parametric",
    bank: dict[str, Any] | None = None,
    n_tasks: int = 200_000,
    seed: int = 42,
) -> dict[str, Any]:
    """The population quantities the registered estimands target (section 9 item 4).

    mu_th averages over new sessions (g, k, e and f, total logit SD sqrt of the sum of their
    variances), X = E_t[(mu_t,GA - mu_t,OSW)^2], D_b = E_t,h[2 mu_th (1 - mu_th)] and
    pi = (X/4) / (X/4 + D_b/2); delta = E_t[mu_t,GA - mu_t,OSW]. Over the fitted population
    (parametric) or over the 113-task pool and its posterior draws (pool).
    """
    scenario = scenario or Scenario()
    par, c_fit = scenario.apply(params)
    rng = np.random.default_rng(seed)
    if source == "parametric":
        des = Design(K=n_tasks, S=1, R=1, tasks="srs")
        eta0, beta, _ = task_effects(par, c_fit, des, 1, rng, "parametric")
        eta0, beta = eta0[0], beta[0]
    else:
        n_pool, n_draws = bank["eta0"].shape[:2]
        sp = [par.sizes[z] for z in SIZES]
        cf = np.array([c_fit[z] for z in SIZES])
        lam = np.array([sp[i].sigma_b / bank["sigma_b"][i] if bank["sigma_b"][i] > 0 else 0.0
                        for i in range(2)])  # fmt: skip
        eta0 = bank["eta0"].reshape(-1, 2)
        beta = (np.array([p.c for p in sp]) + lam * (bank["beta"] - cf)).reshape(-1, 2)
    out: dict[str, Any] = {}
    pis = []
    for i, z in enumerate(SIZES):
        p = par.sizes[z]
        sd = math.sqrt(p.sigma_g**2 + p.sigma_k**2 + p.sigma_e**2 + p.sigma_f**2)
        m_osw = session_marginal(eta0[:, i] - beta[:, i] / 2, sd)
        m_ga = session_marginal(eta0[:, i] + beta[:, i] / 2, sd)
        x = float(np.mean((m_ga - m_osw) ** 2))
        db = float(np.mean(m_osw * (1 - m_osw) + m_ga * (1 - m_ga)))  # mean of 2 m (1 - m)
        pi = (x / 4) / (x / 4 + db / 2) if x + db > 0 else 0.0
        pis.append(pi)
        out[z] = {
            "success": [float(m_osw.mean()), float(m_ga.mean())],
            "delta": float(np.mean(m_ga - m_osw)),
            "X": x,
            "D_b": db,
            "pi": pi,
            "session_logit_sd": sd,
        }
    out["pi_small"] = float(np.mean(pis))
    out["delta_pooled"] = float(np.mean([out[z]["delta"] for z in SIZES]))
    return out


def lam_for_pi(
    params: Params,
    target: float,
    base: Scenario | None = None,
    *,
    key: str = "pi_small",
    source: str = "parametric",
    bank: dict[str, Any] | None = None,
    n_tasks: int = 100_000,
) -> float:
    """The scale lam of the task-specific harness effect at which the population share
    ``key`` (``pi_small`` or a size's ``pi``, e.g. ``9B``) equals ``target``, holding the
    rest of ``base`` (bisection; the share rises with lam)."""
    base = base or Scenario()

    def share(lam: float) -> float:
        pop = population(params, replace(base, lam=lam), source=source, bank=bank,
                         n_tasks=n_tasks)  # fmt: skip
        return pop[key] if key == "pi_small" else pop[key]["pi"]

    lo, hi = 0.0, 1.0
    while share(hi) < target:
        hi *= 2
        if hi > 64:
            raise ValueError(f"share {target} not reached")
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if share(mid) < target else (lo, mid)
    return 0.5 * (lo + hi)


def prob_scale_components(
    params: Params, *, n_tasks: int = 4000, n_sessions: int = 400, seed: int = 42
) -> dict[str, Any]:
    """A functional ANOVA of p on the probability scale, per size, by Monte Carlo.

    A balanced draw of tasks x 2 harnesses x new sessions from the fitted model; the
    variance of p splits into task, harness, session and their interactions (balanced
    random-effects sums of squares), and the rerun (Bernoulli) residual is E[p (1 - p)].
    The components add up to Var(y) = pbar (1 - pbar).
    """
    rng = np.random.default_rng(seed)
    des = Design(K=n_tasks, S=n_sessions, R=1, tasks="srs")
    out: dict[str, Any] = {}
    eta0, beta, _ = task_effects(params, {z: params.sizes[z].c for z in SIZES}, des, 1, rng,
                                 "parametric")  # fmt: skip
    for i, z in enumerate(SIZES):
        p_ = params.sizes[z]
        lin = (
            eta0[0, :, i][:, None, None]
            + beta[0, :, i][:, None, None] * np.array([-0.5, 0.5])[None, :, None]
        )
        lin = lin + p_.sigma_g * rng.standard_normal((1, 1, n_sessions))
        lin = lin + p_.sigma_k * rng.standard_normal((1, 2, n_sessions))
        lin = lin + p_.sigma_e * rng.standard_normal((n_tasks, 1, n_sessions))
        lin = lin + p_.sigma_f * rng.standard_normal((n_tasks, 2, n_sessions))
        p = expit(lin)  # (T, H, S)
        m = p.mean()
        mt, mh, ms = p.mean((1, 2)), p.mean((0, 2)), p.mean((0, 1))
        mth, mts, mhs = p.mean(2), p.mean(1), p.mean(0)
        comp = {
            "task": float(np.var(mt)),
            "harness": float(np.var(mh)),
            "session": float(np.var(ms)),
            "task_x_harness": float(np.mean((mth - mt[:, None] - mh[None, :] + m) ** 2)),
            "task_x_session": float(np.mean((mts - mt[:, None] - ms[None, :] + m) ** 2)),
            "harness_x_session": float(np.mean((mhs - mh[:, None] - ms[None, :] + m) ** 2)),
        }
        resid = (p - mth[:, :, None] - mts[:, None, :] - mhs[None, :, :]
                 + mt[:, None, None] + mh[None, :, None] + ms[None, None, :] - m)  # fmt: skip
        comp["task_x_harness_x_session"] = float(np.mean(resid**2))
        comp["rerun"] = float(np.mean(p * (1 - p)))
        total = float(m * (1 - m))
        out[z] = {
            "mean_success": float(m),
            "var_y": total,
            "components": comp,
            "shares": {k: v / total for k, v in comp.items()},
        }
    return out
