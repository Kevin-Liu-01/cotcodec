"""Command line for the Q2 design study (CPU only; run from the repository root).

    python -m harness.q2_design.study fit --set base --out DIR/fit-base.json
    python -m harness.q2_design.study profile --fit DIR/fit-base.json --out DIR/profile-base.json
    python -m harness.q2_design.study validate --fit DIR/fit-base.json --seed 42 --nsim 200 \
        --out DIR/validation-base-seed42.json
    python -m harness.q2_design.study merge-validation --out DIR/validation-base.json FILES...
    python -m harness.q2_design.study recovery --fit DIR/fit-base.json --truth fitted \
        --seed 42 --out DIR/recovery-fitted-seed42.json
    python -m harness.q2_design.study design --fit DIR/fit-base.json --K 113 --S 2 --R 2 \
        --tasks extend --scenario pi=0.13 --seed 42 --nsim 200 --out DIR/design-....json
    python -m harness.q2_design.study cost --out DIR/cost-model.json
    python -m harness.q2_design.study summary --dir DIR --out DIR/summary.json

Seeds: the fit is deterministic (a fixed grid, no random draws); every random stream is
numpy's PCG64 seeded from [seed, stream] with seed in [42, 43, 44]; the posterior bank uses
seed 42; the registered bootstrap uses seed 42 for every data set, as the report does.
Every output file is written once and never overwritten.
"""

from __future__ import annotations

import argparse
import json
import math
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import scipy

from harness.q2_design import analyse as AN
from harness.q2_design import cost as C
from harness.q2_design import data as D
from harness.q2_design import fit as F
from harness.q2_design import model as M

MODES = {
    # name: (task source, sessions, task selection)
    "parametric_realized": ("parametric", "realized", "base"),
    "parametric_random": ("parametric", "random", "base"),
    "pool_base_realized": ("pool", "realized", "base"),
    "pool_stratified_realized": ("pool", "realized", "stratified"),
}
BANK_DRAWS = 2000
BANK_SEED = 42
# Acceptance criteria, fixed before any validation run. At S1a's own design (K = 32 base
# tasks, two sessions, two reruns, both sizes) the simulator reproduces S1a if, in the
# primary mode (fitted parametric tasks, the realized sessions):
# - each of S1a's interval widths (delta's 90% t interval and 95% bootstrap interval,
#   pi_small's one-sided bound gap and 95% interval) lies within the simulated 5th-95th
#   percentile range, and the simulated median width is within 25% of S1a's;
# - S1a's observed DR2 class and DR5 outcome each have simulated probability >= 0.10.
CRITERIA = {
    "mode": "parametric_realized",
    "widths": (
        "delta_ci90_width",
        "delta_boot95_width",
        "pi_small_bound_width",
        "pi_small_ci95_width",
    ),
    "rank_range": (0.05, 0.95),
    "median_rel_tol": 0.25,
    "min_outcome_probability": 0.10,
}


def _json(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): _json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return _json(obj.tolist())
    if isinstance(obj, (np.floating, float)):
        f = float(obj)
        return None if not math.isfinite(f) else round(f, 6)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    return obj


def _write(path: Path, obj: Any) -> None:
    if path.exists():
        raise SystemExit(f"{path} exists; outputs are never overwritten")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_json(obj), indent=1, sort_keys=True) + "\n", encoding="utf-8")


def provenance() -> dict[str, Any]:
    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                              check=True).stdout.strip()  # fmt: skip
        dirty = bool(subprocess.run(["git", "status", "--porcelain", "harness/"],
                                    capture_output=True, text=True).stdout.strip())  # fmt: skip
    except (OSError, subprocess.CalledProcessError):
        head, dirty = None, None
    return {"git_head": head, "harness_dirty": dirty, "python": platform.python_version(),
            "numpy": np.__version__, "scipy": scipy.__version__,
            "argv": sys.argv}  # fmt: skip


def log(msg: dict[str, Any]) -> None:
    print(json.dumps(_json(msg)), flush=True)


# --------------------------------------------------------------------------- fit


def _interior(x: np.ndarray, coord: int, tol: float = 1e-3) -> bool:
    lo, hi = F.bounds()[coord]
    return lo + tol < x[coord] < hi - tol


def _ses(like: F.Likelihood, x: np.ndarray) -> tuple[list[dict], dict]:
    """Per-size SEs from the observed information over that size's interior coordinates
    (conditional on the other size's parameters), on the natural scale."""
    out, info = [], {}
    for zi in range(2):
        coords = [8 * zi + j for j in range(8) if _interior(x, 8 * zi + j)]
        H = F.hessian_block(like, x, coords)
        try:
            cov = np.linalg.inv(H)
            ok = bool(np.all(np.linalg.eigvalsh(H) > 0))
        except np.linalg.LinAlgError:
            cov, ok = np.full_like(H, np.nan), False
        se: dict[str, float] = {}
        for a, c in enumerate(coords):
            key = F.SIZE_KEYS[c - 8 * zi]
            s = math.sqrt(cov[a, a]) if cov[a, a] > 0 else float("nan")
            if key.startswith("log_"):
                se[key[4:]] = s * math.exp(x[c])  # delta method
            else:
                se[key] = s
        for key in ("omega", "kappa"):
            se.setdefault(key, float("nan"))
        out.append(se)
        info[M.SIZES[zi]] = {"coords": [F.SIZE_KEYS[c - 8 * zi] for c in coords],
                             "positive_definite": ok}  # fmt: skip
    return out, info


def task_count_histogram(y: np.ndarray) -> np.ndarray:
    """Per size, the number of tasks with 0..H*S*R successes; y is (..., Z, K, H, S, R)."""
    tot = np.nansum(y, axis=(-3, -2, -1)).astype(int)  # (..., Z, K)
    n = y.shape[-3] * y.shape[-2] * y.shape[-1]
    return np.stack([(tot == c).sum(axis=-1) for c in range(n + 1)], axis=-1)


FIX_NAMES = {f"{k}_{z}": 8 * zi + j for zi, z in enumerate(M.SIZES)
             for j, k in enumerate(F.SIZE_KEYS)}  # fmt: skip
FIX_NAMES.update(rho_a=16, rho_b=17)


def parse_fix(specs: list[str] | None) -> dict[int, float]:
    """``NAME=VALUE`` pairs on the natural scale (``rho_b=0``, ``sigma_b_4B=0.02``) as fixed
    coordinates of the transformed parameter vector (``fit.fit``'s ``fixed``)."""
    out: dict[int, float] = {}
    for spec in specs or []:
        name, _, val = spec.partition("=")
        key = name.replace("sigma_a", "log_sigma_a").replace("sigma_b", "log_sigma_b")
        if key not in FIX_NAMES or not val:
            raise SystemExit(f"cannot fix {spec!r}; names: sigma_b_4B, rho_b, c_9B, ...")
        v = float(val)
        if key.startswith("log_"):
            v = math.log(v)
        elif key.startswith("rho_"):
            v = math.atanh(v)
        lo, hi = F.bounds()[FIX_NAMES[key]]
        if not lo - 1e-12 <= v <= hi + 1e-12:
            raise SystemExit(f"{spec}: outside the parameter's bounds")
        out[FIX_NAMES[key]] = v
    return out


def cmd_fit(args: argparse.Namespace) -> int:
    s1a = D.load()
    y = s1a.y_base if args.set == "base" else s1a.y_pool
    t0 = time.time()
    fixed = parse_fix(args.fix)
    ref = json.loads(Path(args.warm).read_text(encoding="utf-8")) if args.warm else None
    if ref is not None and (ref["set"] != args.set or ref.get("harness") != args.harness):
        raise SystemExit("--warm must be a fit of the same set and harness model")
    x0 = None
    if ref is not None:  # warm start: the joint stage only, from the reference estimate
        x0 = np.array(ref["x"], dtype=float)
        for i, v in fixed.items():
            x0[i] = v
    res = F.fit(y, harness=args.harness, fixed=fixed, x0=x0, log=log)
    x, like = res["x"], res["likelihood"]
    sizes, rho_a, rho_b = F.unpack(x)
    se, se_info = _ses(like, x)
    sess = F.session_variances(sizes, se)
    params = F.to_params(x, sess)
    # Grid check: the log-likelihood at the estimate on a finer grid.
    fine = F.Likelihood(y, F.Grid.default(0.125)).loglik(x)
    pool_like = F.Likelihood(s1a.y_pool)
    bank = F.posterior_bank(pool_like, x, BANK_DRAWS, BANK_SEED)
    bank.update(pool=s1a.pool, n_base=len(s1a.base), domains=s1a.domains)
    out = {
        "set": args.set,
        "harness": args.harness,
        "tasks": int(y.shape[1]),
        "episodes": int(np.isfinite(y).sum()),
        "method": F.__doc__.strip(),
        "loglik": res["loglik"],
        "loglik_grid_0125": fine,
        "converged": res["converged"],
        "optimizer_message": res["message"],
        "x": x,
        "estimates": {
            "sizes": dict(zip(M.SIZES, sizes, strict=True)),
            "rho_a": rho_a,
            "rho_b": rho_b,
            "w_b": F.w_of(x),
        },  # fmt: skip
        "se": dict(zip(M.SIZES, se, strict=True)),
        "se_info": se_info,
        "session_variances": sess,
        "params": params.to_json(),
        "observed": {
            "success_by_size_harness": np.nanmean(y, axis=(1, 3, 4)),
            "task_count_histogram": task_count_histogram(y),
        },
        "population_parametric": M.population(params),
        "population_pool_posterior": M.population(params, source="pool", bank=bank),
        "prob_scale_components": M.prob_scale_components(params),
        "seconds": time.time() - t0,
        "inputs": s1a.digests,
        "provenance": provenance(),
    }
    if fixed:
        out["fixed"] = {n.replace("log_", ""): F.unpack_value(i, x[i])
                        for n, i in FIX_NAMES.items() if i in fixed}  # fmt: skip
    if ref is not None:
        out["warm_start"] = args.warm
        out["reference_loglik"] = ref["loglik"]
        out["lr_vs_reference"] = 2 * (ref["loglik"] - res["loglik"])
    _write(Path(args.out), out)
    log({"wrote": args.out, "seconds": out["seconds"]})
    return 0


def load_fit(path: Path) -> tuple[dict[str, Any], M.Params]:
    fit = json.loads(path.read_text(encoding="utf-8"))
    return fit, M.Params.from_json(fit["params"])


def build_bank(fit: dict[str, Any], s1a: D.S1aData) -> dict[str, Any]:
    bank = F.posterior_bank(F.Likelihood(s1a.y_pool), np.array(fit["x"]), BANK_DRAWS, BANK_SEED)
    bank.update(pool=s1a.pool, n_base=len(s1a.base), domains=s1a.domains)
    return bank


# --------------------------------------------------------------------------- profile


def cmd_profile(args: argparse.Namespace) -> int:
    """Per-size profile likelihoods (the size's own likelihood, its other seven parameters
    re-optimised; the cross-size correlations do not enter) for the components a design
    study varies: sigma_e, sigma_f, sigma_b and c."""
    s1a = D.load()
    fit, _ = load_fit(Path(args.fit))
    y = s1a.y_base if fit["set"] == "base" else s1a.y_pool
    like = F.Likelihood(y)
    x = np.array(fit["x"])
    grids = {
        "sigma_e": [0.0, 0.25, 0.5, 1.0, 1.5, 2.0, 3.0],
        "sigma_f": [0.0, 0.25, 0.5, 1.0, 1.5, 2.0, 3.0],
        "log_sigma_b": [math.log(v) for v in (0.05, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0)],
        "c": [-3.0, -2.0, -1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0],
    }
    out: dict[str, Any] = {"method": cmd_profile.__doc__.strip(), "sizes": {}}
    for zi, z in enumerate(M.SIZES):
        xs = x[8 * zi : 8 * zi + 8]
        bnds = F.bounds()[:8]
        res0 = F._minimize(lambda v, zi=zi: -like.size_loglik(zi, v), xs, bnds)
        ll0, xs0 = -float(res0.fun), res0.x
        rows: dict[str, list] = {}
        for key, values in grids.items():
            j = F.SIZE_KEYS.index(key)
            free = [i for i in range(8) if i != j]
            cur = xs0.copy()
            rows[key] = []
            for v in values:

                def f(w: np.ndarray, j=j, v=v, free=free, cur=cur, zi=zi) -> float:
                    full = cur.copy()
                    full[free] = w
                    full[j] = v
                    return -like.size_loglik(zi, full)

                r = F._minimize(f, cur[free], [bnds[i] for i in free])
                cur[free] = r.x
                cur[j] = v
                row = {"value": math.exp(v) if key.startswith("log_") else v,
                       "loglik": -float(r.fun), "lr": 2 * (ll0 + float(r.fun))}  # fmt: skip
                rows[key].append(row)
                log({"size": z, "param": key, **row})
        out["sizes"][z] = {"size_loglik_max": ll0, "size_estimate": xs0, "profiles": rows}
    out["provenance"] = provenance()
    _write(Path(args.out), out)
    return 0


# --------------------------------------------------------------------------- validate


def observed_reading(s1a: D.S1aData) -> dict[str, Any]:
    """S1a's registered readings recomputed by the wrapper (10,000 resamples and flips,
    generator seeded 42 as in analyse_array) and checked against the committed report."""
    res = AN.analyse(s1a.y_base[None], M.SIZES, rng=np.random.default_rng(42))
    rep = json.loads(Path(D.REPORT).read_text(encoding="utf-8"))["primary"]
    obs = {k: (v[0] if not isinstance(v[0], str) else v[0]) for k, v in res.items()}
    checks = {
        "p_x": obs["p_x"] == rep["tests"]["x_signflip_p"],
        "p_delta": abs(obs["p_delta"] - rep["tests"]["delta_paired_t"]["p"]) < 1e-6,
        "ci90": np.allclose(
            [obs["ci90_low"], obs["ci90_high"]], rep["tests"]["delta_paired_t"]["ci90_t"], atol=1e-6
        ),  # fmt: skip
        "pi_small_bounds": [obs["pi_small_lb"], obs["pi_small_ub"]]
        == rep["estimates"]["pi_small"]["one_sided_95"],
        "delta_boot95": np.allclose(
            [obs["delta_boot_low"], obs["delta_boot_high"]],
            rep["estimates"]["delta"]["ci95"],
            atol=1e-6,
        ),  # fmt: skip
        "DR2": obs["dr2"] == rep["DR2"]["class"],
        "DR5": obs["dr5"] == rep["DR5"]["outcome"],
    }
    widths = {
        "delta_ci90_width": obs["ci90_high"] - obs["ci90_low"],
        "delta_boot95_width": obs["delta_boot_high"] - obs["delta_boot_low"],
        "pi_small_bound_width": obs["pi_small_ub"] - obs["pi_small_lb"],
        "pi_small_ci95_width": obs["pi_small_ci95_high"] - obs["pi_small_ci95_low"],
        "pi_small_ub": obs["pi_small_ub"],
        "D_b": obs["D_b"],
    }
    return {"reading": obs, "widths": widths, "matches_committed_report": checks,
            "task_count_histogram": task_count_histogram(s1a.y_base)}  # fmt: skip


def cmd_validate(args: argparse.Namespace) -> int:
    s1a = D.load()
    fit, params = load_fit(Path(args.fit))
    bank = build_bank(fit, s1a)
    obs = observed_reading(s1a) if args.seed == 42 else None
    out: dict[str, Any] = {"fit": args.fit, "seed": args.seed, "nsim": args.nsim,
                           "n_boot": args.n_boot, "n_flip": args.n_flip, "modes": {}}  # fmt: skip
    if obs is not None:
        out["observed"] = obs
    for mi, (name, (source, sessions, tasks)) in enumerate(MODES.items()):
        if args.modes and name not in args.modes:
            continue
        t0 = time.time()
        design = M.Design(K=32, S=2, R=2, tasks=tasks)
        rng = np.random.default_rng([args.seed, mi])
        y, truth = M.simulate(params, design, args.nsim, rng, source=source,
                              sessions=sessions, bank=bank)  # fmt: skip
        res = AN.analyse(y, M.SIZES, n_boot=args.n_boot, n_flip=args.n_flip,
                         rng=np.random.default_rng([args.seed, 100 + mi]))  # fmt: skip
        out["modes"][name] = {
            "source": source, "sessions": sessions, "tasks": tasks,
            "per_set": {k: v for k, v in res.items()},
            "delta_realized": truth["delta_realized"],
            "task_count_histogram_mean": task_count_histogram(y).mean(axis=0),
            "seconds": time.time() - t0,
        }  # fmt: skip
        log({"mode": name, "seed": args.seed, "summary": AN.summarise(res),
             "seconds": time.time() - t0})  # fmt: skip
    out["provenance"] = provenance()
    _write(Path(args.out), out)
    return 0


def _rank(sim: np.ndarray, value: float) -> float:
    sim = np.asarray(sim, dtype=float)
    sim = sim[np.isfinite(sim)]
    return float(np.mean(sim <= value + 1e-12)) if sim.size else float("nan")


def cmd_merge_validation(args: argparse.Namespace) -> int:
    parts = [json.loads(Path(p).read_text(encoding="utf-8")) for p in args.files]
    obs = next(p["observed"] for p in parts if "observed" in p)
    out: dict[str, Any] = {"files": args.files, "seeds": [p["seed"] for p in parts],
                           "observed": obs, "modes": {}}  # fmt: skip
    for name in parts[0]["modes"]:
        per_seed, pooled = {}, None
        for p in parts:
            m = p["modes"].get(name)
            if m is None:
                continue
            res = {k: np.array(v, dtype=object if k in ("dr2", "dr5") else float)
                   for k, v in m["per_set"].items()}  # fmt: skip
            per_seed[str(p["seed"])] = AN.summarise(res)
            pooled = res if pooled is None else {k: np.concatenate([pooled[k], res[k]])
                                                 for k in res}  # fmt: skip
        summ = AN.summarise(pooled)
        w = obs["widths"]
        ranks = {
            "delta_ci90_width": _rank(pooled["ci90_high"] - pooled["ci90_low"],
                                      w["delta_ci90_width"]),
            "delta_boot95_width": _rank(pooled["delta_boot_high"] - pooled["delta_boot_low"],
                                        w["delta_boot95_width"]),
            "pi_small_bound_width": _rank(pooled["pi_small_ub"] - pooled["pi_small_lb"],
                                          w["pi_small_bound_width"]),
            "pi_small_ci95_width": _rank(
                pooled["pi_small_ci95_high"] - pooled["pi_small_ci95_low"],
                w["pi_small_ci95_width"]),
            "pi_small_ub": _rank(pooled["pi_small_ub"], w["pi_small_ub"]),
            "D_b": _rank(pooled["D_b"], w["D_b"]),
        }  # fmt: skip
        hist = np.mean([p["modes"][name]["task_count_histogram_mean"] for p in parts
                        if name in p["modes"]], axis=0)  # fmt: skip
        out["modes"][name] = {
            "pooled": summ,
            "per_seed": per_seed,
            "observed_percentile_rank": ranks,
            "P_observed_DR2": summ["DR2"][obs["reading"]["dr2"]],
            "P_observed_DR5": summ["DR5"][obs["reading"]["dr5"]],
            "P_observed_both": summ["P_both_inconclusive"],
            "task_count_histogram_expected": hist,
            "task_count_histogram_observed": obs["task_count_histogram"],
        }
    out["criteria"] = dict(CRITERIA)
    out["verdict"] = {name: evaluate(out["modes"][name], obs) for name in out["modes"]}
    out["provenance"] = provenance()
    _write(Path(args.out), out)
    return 0


def evaluate(mode: dict[str, Any], obs: dict[str, Any]) -> dict[str, Any]:
    """The acceptance criteria (CRITERIA) applied to one mode's pooled simulations."""
    lo, hi = CRITERIA["rank_range"]
    checks: dict[str, Any] = {}
    for w in CRITERIA["widths"]:
        rank = mode["observed_percentile_rank"][w]
        med = mode["pooled"][w]["median"]
        val = obs["widths"][w]
        rel = abs(med - val) / val if val else float("inf")
        checks[w] = {"observed": val, "sim_median": med, "rank": rank,
                     "rank_ok": lo <= rank <= hi,
                     "median_ok": rel <= CRITERIA["median_rel_tol"]}  # fmt: skip
    pmin = CRITERIA["min_outcome_probability"]
    checks["DR2_observed_probability_ok"] = mode["P_observed_DR2"] >= pmin
    checks["DR5_observed_probability_ok"] = mode["P_observed_DR5"] >= pmin
    passed = all(v["rank_ok"] and v["median_ok"] for k, v in checks.items()
                 if isinstance(v, dict)) and checks["DR2_observed_probability_ok"] and checks[
        "DR5_observed_probability_ok"]  # fmt: skip
    return {"checks": checks, "pass": bool(passed)}


# --------------------------------------------------------------------------- designs


def scenario_from(spec: str, params: M.Params, source: str, bank: dict | None) -> M.Scenario:
    """``fitted``, ``harness-null``, ``main-only`` (the fitted c, no task-specific part) or
    ``pi=<v>`` (the fitted c, the task-specific part scaled so the population pi_small is v;
    ``pi9B=<v>`` targets pi_9B)."""
    if spec == "fitted":
        return M.Scenario()
    if spec == "harness-null":
        return M.Scenario.harness_null()
    if spec == "main-only":
        return M.Scenario(name="main-only", lam=0.0)
    key, _, val = spec.partition("=")
    if key in ("pi", "pi9B") and val:
        lam = M.lam_for_pi(params, float(val), key="pi_small" if key == "pi" else "9B",
                           source=source, bank=bank)  # fmt: skip
        return M.Scenario(name=spec, lam=lam)
    raise SystemExit(f"unknown scenario {spec}")


def evaluate_design(
    params: M.Params,
    design: M.Design,
    scenario: M.Scenario,
    *,
    nsim: int,
    seed: int,
    source: str = "parametric",
    sessions: str = "random",
    bank: dict | None = None,
    n_boot: int = 10_000,
    n_flip: int = 10_000,
) -> dict[str, Any]:
    """P(DR2 class), P(DR5 outcome) and interval widths for one design and scenario, with
    the scenario's population truth; the registered analysis on every simulated data set."""
    rng = np.random.default_rng([seed, 11])
    y, truth = M.simulate(params, design, nsim, rng, source=source, sessions=sessions,
                          scenario=scenario, bank=bank)  # fmt: skip
    res = AN.analyse(y, design.sizes, n_boot=n_boot, n_flip=n_flip,
                     rng=np.random.default_rng([seed, 12]))  # fmt: skip
    return {
        "design": design.__dict__, "scenario": scenario.__dict__, "source": source,
        "sessions": sessions, "seed": seed, "nsim": nsim, "n_boot": n_boot, "n_flip": n_flip,
        "population": M.population(params, scenario, source=source, bank=bank),
        "summary": AN.summarise(res),
        "delta_realized_mean": float(np.mean(truth["delta_realized"])),
    }  # fmt: skip


def cmd_design(args: argparse.Namespace) -> int:
    s1a = D.load()
    fit, params = load_fit(Path(args.fit))
    bank = build_bank(fit, s1a) if args.source == "pool" else None
    design = M.Design(K=args.K, S=args.S, R=args.R, sizes=tuple(args.sizes), tasks=args.tasks)
    scen = scenario_from(args.scenario, params, args.source, bank)
    out = evaluate_design(params, design, scen, nsim=args.nsim, seed=args.seed,
                          source=args.source, sessions=args.sessions, bank=bank,
                          n_boot=args.n_boot, n_flip=args.n_flip)  # fmt: skip
    model, _ = C.build(Path("."), s1a)
    out["cost"] = model.design(design)
    out["fit"] = args.fit
    out["provenance"] = provenance()
    _write(Path(args.out), out)
    log({"design": design.__dict__, "scenario": args.scenario, "summary": out["summary"]})
    return 0


# --------------------------------------------------------------------------- recovery


def cmd_recovery(args: argparse.Namespace) -> int:
    """Parameter recovery of the fitting method at S1a's design: one data set simulated from
    known parameters (fitted parametric tasks, the realized sessions, K = 32, two reruns),
    refitted by ``fit.fit``. ``--truth fitted`` uses the fit's parameters; ``--truth
    session-noise`` sets sigma_e = sigma_f = 1.0 in both sizes, to show whether the fit can
    see task x session noise at S1a's size."""
    fit, params = load_fit(Path(args.fit))
    scen = M.Scenario()
    if args.truth == "session-noise":
        scen = M.Scenario(name="session-noise", sigma_e={"4B": 1.0, "9B": 1.0},
                          sigma_f={"4B": 1.0, "9B": 1.0})  # fmt: skip
    truth, _ = scen.apply(params)
    rng = np.random.default_rng([args.seed, 7])
    y, _ = M.simulate(params, M.Design(K=32, tasks="srs"), 1, rng, sessions="realized",
                      scenario=scen)  # fmt: skip
    res = F.fit(y[0], log=log)
    sizes, rho_a, rho_b = F.unpack(res["x"])
    out = {
        "fit": args.fit, "truth_name": args.truth, "seed": args.seed,
        "truth": truth.to_json(),
        "estimate": {"sizes": dict(zip(M.SIZES, sizes, strict=True)), "rho_a": rho_a,
                     "rho_b": rho_b, "w_b": F.w_of(res["x"])},
        "loglik": res["loglik"], "converged": res["converged"],
        "observed_success": np.nanmean(y[0], axis=(1, 3, 4)),
        "provenance": provenance(),
    }  # fmt: skip
    _write(Path(args.out), out)
    return 0


# --------------------------------------------------------------------------- summary


def profile_bounds(rows: list[dict[str, float]], estimate: float) -> dict[str, Any]:
    """Profile-likelihood limits by linear interpolation of the LR curve: the one-sided 95%
    limits (LR 2.71, the reading for a parameter at a boundary) and the two-sided 95% limits
    (LR 3.84), below and above the estimate; None where the grid does not reach the line."""
    rows = sorted(rows, key=lambda r: r["value"])
    out: dict[str, Any] = {}
    for name, line in (("one_sided_95", 2.705543), ("two_sided_95", 3.841459)):
        lo = hi = None
        for a, b in zip(rows, rows[1:], strict=False):
            for side in ("lo", "hi"):
                cross = (a["lr"] - line) * (b["lr"] - line) <= 0 and a["lr"] != b["lr"]
                if not cross:
                    continue
                v = a["value"] + (line - a["lr"]) / (b["lr"] - a["lr"]) * (b["value"] - a["value"])
                if side == "lo" and v <= estimate:
                    lo = v
                if side == "hi" and v >= estimate and hi is None:
                    hi = v
        out[name] = [lo, hi]
    return out


def cmd_summary(args: argparse.Namespace) -> int:
    """One machine-readable index of the study's headline numbers (no new computation
    beyond reading the committed outputs and interpolating the profile curves)."""
    E_ = Path(args.dir)
    fit = json.loads((E_ / "fit-base.json").read_text())
    out: dict[str, Any] = {"fit_base": {k: fit[k] for k in (
        "estimates", "se", "session_variances", "loglik", "loglik_grid_0125", "converged",
        "population_parametric", "population_pool_posterior")}}  # fmt: skip
    out["fit_base"]["prob_scale_shares"] = {
        z: v["shares"] for z, v in fit["prob_scale_components"].items()
    }
    ss = E_ / "fit-base-spikeslab.json"
    if ss.exists():
        fs = json.loads(ss.read_text())
        out["fit_base_spikeslab"] = {k: fs[k] for k in (
            "estimates", "se", "session_variances", "loglik", "population_parametric",
            "population_pool_posterior")}  # fmt: skip
        out["fit_base_spikeslab"]["lr_vs_normal"] = 2 * (fs["loglik"] - fit["loglik"])
    pool = E_ / "fit-pool.json"
    if pool.exists():
        fp = json.loads(pool.read_text())
        out["fit_pool"] = {k: fp[k] for k in ("estimates", "se", "session_variances", "loglik",
                                               "population_parametric")}  # fmt: skip
    prof = E_ / "profile-base.json"
    if prof.exists():
        pr = json.loads(prof.read_text())
        out["profile_base"] = {}
        for z, v in pr["sizes"].items():
            est = dict(zip(F.SIZE_KEYS, v["size_estimate"], strict=True))
            est["log_sigma_b"] = math.exp(est["log_sigma_b"])
            out["profile_base"][z] = {  # log_sigma_b rows hold sigma_b values
                k.replace("log_", ""): {"size_estimate": est[k], **profile_bounds(rows, est[k])}
                for k, rows in v["profiles"].items()
            }
    for key, name in (("validation", "validation-base.json"),
                      ("validation_spikeslab", "validation-spikeslab.json")):  # fmt: skip
        val = E_ / name
        if not val.exists():
            continue
        vv = json.loads(val.read_text())
        out[key] = {
            "observed": vv["observed"]["widths"],
            "observed_readings": {k: vv["observed"]["reading"][k] for k in ("dr2", "dr5")},
            "matches_committed_report": vv["observed"]["matches_committed_report"],
            "verdict": vv["verdict"],
            "modes": {m: {"DR2": d["pooled"]["DR2"], "DR5": d["pooled"]["DR5"],
                          "P_both_inconclusive": d["P_observed_both"],
                          "ranks": d["observed_percentile_rank"],
                          "medians": {w: d["pooled"][w]["median"] for w in CRITERIA["widths"]}}
                      for m, d in vv["modes"].items()},
        }  # fmt: skip
    rec = sorted(E_.glob("recovery-*.json"))
    if rec:
        out["recovery"] = []
        for path in rec:
            r = json.loads(path.read_text())
            out["recovery"].append({"file": path.name, "truth": r["truth"],
                                    "estimate": r["estimate"]})  # fmt: skip
    cost = json.loads((E_ / "cost-model.json").read_text())
    out["cost"] = {k: cost[k] for k in (
        "by_size", "overhead_per_job_gpu_h", "marginal_gpu_h_per_episode_pool_mean",
        "planning_gpu_h_per_episode_pool_mean", "episodes_per_8_gpu_h_physical",
        "structures_within_478_cap_minutes", "cpu", "s1a_base_design_repriced")}  # fmt: skip
    out["provenance"] = provenance()
    _write(Path(args.out), out)
    return 0


# --------------------------------------------------------------------------- compare

IGNORED = ("provenance", "seconds", "argv")


def differences(a: Any, b: Any, path: str = "") -> list[str]:
    """Paths where ``b`` differs from ``a``; keys only ``b`` has (fields added by later code)
    and run metadata (provenance, timings) are ignored."""
    if isinstance(a, dict) and isinstance(b, dict):
        out = []
        for k, v in a.items():
            if k in IGNORED:
                continue
            if k not in b:
                out.append(f"{path}/{k} (missing)")
            else:
                out += differences(v, b[k], f"{path}/{k}")
        return out
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return [f"{path} (length)"]
        return [d for i, (x, y) in enumerate(zip(a, b, strict=True))
                for d in differences(x, y, f"{path}/{i}")]  # fmt: skip
    return [] if a == b else [path]


def cmd_compare(args: argparse.Namespace) -> int:
    """Reproduction check: a committed output against a re-run from a committed tree."""
    a = json.loads(Path(args.a).read_text(encoding="utf-8"))
    b = json.loads(Path(args.b).read_text(encoding="utf-8"))
    if args.mode:
        a = {"modes": {args.mode: a["modes"][args.mode]}}
        b = {"modes": {args.mode: b["modes"][args.mode]}}
    diffs = differences(a, b)
    rerun = json.loads(Path(args.b).read_text(encoding="utf-8")).get("provenance", {})
    out = {"committed": args.a, "rerun": args.b, "mode": args.mode, "identical": not diffs,
           "differences": diffs[:50], "rerun_provenance": rerun}  # fmt: skip
    _write(Path(args.out), out)
    log({"identical": not diffs, "n_differences": len(diffs)})
    return 0


# --------------------------------------------------------------------------- cost


def cmd_cost(args: argparse.Namespace) -> int:
    s1a = D.load()
    model, timing = C.build(Path("."), s1a)
    out = C.summary(model, timing, s1a)
    out["method"] = C.__doc__.strip()
    out["inputs"] = s1a.digests
    out["provenance"] = provenance()
    _write(Path(args.out), out)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Q2 design study (CPU)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("fit")
    p.add_argument("--set", choices=("base", "pool"), required=True)
    p.add_argument("--harness", choices=("normal", "spike-slab"), default="normal")
    p.add_argument("--fix", nargs="*", help="hold parameters: rho_b=0 sigma_b_4B=0.02 ...")
    p.add_argument("--warm", help="warm-start from this fit (same set and harness model)")
    p.add_argument("--out", required=True)
    p = sub.add_parser("profile")
    p.add_argument("--fit", required=True)
    p.add_argument("--out", required=True)
    p = sub.add_parser("validate")
    p.add_argument("--fit", required=True)
    p.add_argument("--seed", type=int, choices=(42, 43, 44), required=True)
    p.add_argument("--nsim", type=int, default=200)
    p.add_argument("--n-boot", type=int, default=10_000)
    p.add_argument("--n-flip", type=int, default=10_000)
    p.add_argument("--modes", nargs="*")
    p.add_argument("--out", required=True)
    p = sub.add_parser("merge-validation")
    p.add_argument("--out", required=True)
    p.add_argument("files", nargs="+")
    p = sub.add_parser("design")
    p.add_argument("--fit", required=True)
    p.add_argument("--K", type=int, required=True)
    p.add_argument("--S", type=int, required=True)
    p.add_argument("--R", type=int, required=True)
    p.add_argument("--sizes", nargs="+", default=list(M.SIZES))
    p.add_argument("--tasks", default="srs", choices=("base", "extend", "srs", "stratified"))
    p.add_argument("--scenario", default="fitted")
    p.add_argument("--source", default="parametric", choices=("parametric", "pool"))
    p.add_argument("--sessions", default="random", choices=("random", "realized"))
    p.add_argument("--seed", type=int, choices=(42, 43, 44), required=True)
    p.add_argument("--nsim", type=int, default=200)
    p.add_argument("--n-boot", type=int, default=10_000)
    p.add_argument("--n-flip", type=int, default=10_000)
    p.add_argument("--out", required=True)
    p = sub.add_parser("recovery")
    p.add_argument("--fit", required=True)
    p.add_argument("--truth", choices=("fitted", "session-noise"), required=True)
    p.add_argument("--seed", type=int, choices=(42, 43, 44), required=True)
    p.add_argument("--out", required=True)
    p = sub.add_parser("cost")
    p.add_argument("--out", required=True)
    p = sub.add_parser("compare")
    p.add_argument("--a", required=True, help="the committed output")
    p.add_argument("--b", required=True, help="the re-run")
    p.add_argument("--mode", help="compare one validation mode only")
    p.add_argument("--out", required=True)
    p = sub.add_parser("summary")
    p.add_argument("--dir", required=True)
    p.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    commands = {
        "fit": cmd_fit,
        "profile": cmd_profile,
        "validate": cmd_validate,
        "merge-validation": cmd_merge_validation,
        "recovery": cmd_recovery,
        "design": cmd_design,
        "cost": cmd_cost,
        "summary": cmd_summary,
        "compare": cmd_compare,
    }
    return commands[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
