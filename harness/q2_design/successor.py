"""Successor-design comparison after the attack on the design study (CPU only, seeded).

    python -m harness.q2_design.successor ppc --fit F [--set-param sigma_b_4B=0 ...] \
        --source pool --seed 42 --nsim 150 --out DIR/ppc-....json
    python -m harness.q2_design.successor merge-ppc --out DIR/ppc-NAME.json FILES...
    python -m harness.q2_design.successor designs --fit F [--set-param ...] --source pool \
        --designs C-K113-S2R2 ... --scenarios fitted null ... --seed 42 --nsim 150 --out ...
    python -m harness.q2_design.successor merge-designs --out DIR/designs-NAME.json FILES...
    python -m harness.q2_design.successor cost-draws --out DIR/cost-draws.json

A calibration is a committed fit plus optional overrides of its parameters (``--set-param``:
``sigma_b_4B=0`` removes 4B's task-specific harness effect, ``sigma_f_9B=1.0`` sets 9B's
task x harness x session SD, ``sigma_k=0.95`` sets the new-session harness x session SD in
both sizes). With ``--source pool`` the tasks are S1a's 113 pool tasks with their effects
drawn from their posterior given S1a's records (``fit.posterior_bank`` at the fit's
estimate); an override of sigma_b rescales the bank's task-specific harness part
(``model.task_effects``).

The posterior-predictive check (``ppc``) simulates S1a's own two runs with the realized
sessions, the registered secondary set (K113: base plus the 11 extension blocks) and the
primary base (K32), and the 81 extension tasks alone (EXT81; parametric source: new tasks
from the fitted population, out of sample for a fit on the base), and ranks S1a's observed
statistics among the simulated ones. Its acceptance criteria (``PPC_CRITERIA``) extend the
study's width criteria with the location and structure statistics the attack named; they
were written after the attack's report and before any refitted calibration was checked.

Every analysis is the registered one (``fast.analyse``, equal to ``analyse.analyse``; 10,000
resamples, seed 42; 10,000 sign flips). Streams: data [seed, 11, crc32(design)], sign flips
[seed, 12, crc32(design)], per-size diagnostic flips [seed, 13, target], so a design sees the
same random numbers under every scenario and calibration (common random numbers).
"""

from __future__ import annotations

import argparse
import json
import math
import time
import zlib
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
from scipy import optimize

from harness.q2_design import analyse as AN
from harness.q2_design import cost as C
from harness.q2_design import data as D
from harness.q2_design import fast as FA
from harness.q2_design import model as M
from harness.q2_design import study as ST

SIZE_FIELDS = ("mu", "sigma_a", "c", "sigma_b", "sigma_e", "sigma_f", "omega", "kappa",
               "sigma_g", "sigma_k")  # fmt: skip

PPC_CRITERIA = {
    "targets": ("K113", "K32"),
    "decision_stats": (
        "X_4B",
        "X_9B",
        "p_x",
        "pi_small",
        "pi_small_ub",
        "pi_small_lb",
        "ci90_width",
    ),  # fmt: skip
    "decision_rank_range": (0.05, 0.95),
    "structure_stats": (
        "D_b_4B",
        "D_b_9B",
        "D_w_4B",
        "D_w_9B",
        "nonconst_4B",
        "nonconst_9B",
        "both_nonzero_4B",
        "both_nonzero_9B",
        "qpos_4B",
        "qneg_4B",
        "qpos_9B",
        "qneg_9B",
        "p_x_4B",
        "p_x_9B",
    ),  # fmt: skip
    "structure_rank_range": (0.01, 0.99),
    "min_outcome_probability": 0.10,
    "rank": "mid-rank: P(sim < obs) + P(sim = obs) / 2",
}

DESIGNS = {
    "A-K32-S2R2": M.Design(K=32, S=2, R=2, tasks="base"),
    "A6-K32-S6R2": M.Design(K=32, S=6, R=2, tasks="base"),
    "B-K113-S2R1": M.Design(K=113, S=2, R=1, tasks="extend"),
    "C-K113-S2R2": M.Design(K=113, S=2, R=2, tasks="extend"),
    "D-K113-S3R1": M.Design(K=113, S=3, R=1, tasks="extend"),
    "E-K113-S4R1": M.Design(K=113, S=4, R=1, tasks="extend"),
    "F-K94-S3R2": M.Design(K=94, S=3, R=2, tasks="stratified"),
    "F5-K105-S5R1": M.Design(K=105, S=5, R=1, tasks="stratified"),
    "J2-9B-K113-S2R2": M.Design(K=113, S=2, R=2, sizes=("9B",), tasks="extend"),
    "J-9B-K113-S4R2": M.Design(K=113, S=4, R=2, sizes=("9B",), tasks="extend"),
    "J3-9B-K113-S3R3": M.Design(K=113, S=3, R=3, sizes=("9B",), tasks="extend"),
}
SCENARIOS = ("fitted", "delta0", "piM", "null", "pi2M")
STORE = ("delta", "p_delta", "ci90_low", "ci90_high", "p_x", "pi_small", "pi_small_lb",
         "pi_small_ub", "pi_small_ci95_low", "pi_small_ci95_high", "delta_boot_low",
         "delta_boot_high", "D_b", "excess_ub", "drop_4b", "dr2", "dr5")  # fmt: skip


def stream(name: str) -> int:
    return zlib.crc32(name.encode()) & 0xFFFFFFFF


# --------------------------------------------------------------------------- calibrations


def override(params: M.Params, specs: list[str] | None) -> M.Params:
    """``field_size=value`` (one size) or ``field=value`` (both sizes) on SizeParams."""
    sizes = dict(params.sizes)
    for spec in specs or []:
        name, _, val = spec.partition("=")
        field, _, size = name.rpartition("_") if name.endswith(M.SIZES) else (name, "", "")
        if field not in SIZE_FIELDS or not val:
            raise SystemExit(f"cannot set {spec!r}")
        for z in [size] if size else M.SIZES:
            sizes[z] = replace(sizes[z], **{field: float(val)})
    return replace(params, sizes=sizes)


def load_calibration(fit_path: str, specs: list[str] | None, s1a: D.S1aData):
    fit, params = ST.load_fit(Path(fit_path))
    params = override(params, specs)
    bank = ST.build_bank(fit, s1a)
    return fit, params, bank


def delta0_scenario(params: M.Params, source: str, bank: dict | None) -> M.Scenario:
    """The main effect c_z solved per size so the population delta_z is 0, keeping the
    task-specific part as calibrated."""
    c = {}
    for z in M.SIZES:

        def gap(v: float, z=z) -> float:
            cc = {zz: params.sizes[zz].c for zz in M.SIZES}
            cc[z] = v
            pop = M.population(params, M.Scenario(c=cc), source=source, bank=bank,
                               n_tasks=100_000)  # fmt: skip
            return pop[z]["delta"]

        c[z] = float(optimize.brentq(gap, -6.0, 6.0, xtol=1e-6))
    return M.Scenario(name="delta0", c=c)


def resolve(spec: str, design: M.Design, params: M.Params, source: str, bank, cache: dict):
    """A scenario name for a design; piM / pi2M target pi_small at M = 0.13 and 2M (pi_9B at
    0.18 and 0.36 for a 9B-only design, the registered DR1 reading)."""
    nine = design.sizes == ("9B",)
    key = (spec, nine)
    if key in cache:
        return cache[key]
    if spec == "fitted":
        sc = M.Scenario()
    elif spec == "null":
        sc = M.Scenario.harness_null()
    elif spec == "delta0":
        sc = delta0_scenario(params, source, bank)
    elif spec in ("piM", "pi2M"):
        target = (0.18 if nine else 0.13) * (2 if spec == "pi2M" else 1)
        lam = M.lam_for_pi(params, target, key="9B" if nine else "pi_small", source=source,
                           bank=bank)  # fmt: skip
        sc = M.Scenario(name=spec, lam=lam)
    else:
        raise SystemExit(f"unknown scenario {spec}")
    cache[key] = sc
    return sc


# --------------------------------------------------------------------------- statistics


def reading(y: np.ndarray, sizes, rng_flip, rng_size, n_flip: int = 10_000) -> dict[str, Any]:
    o = FA.analyse(y, sizes, rng=rng_flip, n_flip=n_flip, diagnostics=True)
    o.update(FA.size_signflip_p(y, sizes, 2000, rng_size))
    o["ci90_width"] = o["ci90_high"] - o["ci90_low"]
    return o


def mid_rank(sim: np.ndarray, obs: float) -> float:
    sim = np.asarray(sim, dtype=float)
    sim = sim[np.isfinite(sim)]
    if not sim.size or not math.isfinite(obs):
        return float("nan")
    return float(np.mean(sim < obs - 1e-12) + 0.5 * np.mean(np.abs(sim - obs) <= 1e-12))


PPC_TARGETS = {
    "K113": (M.Design(K=113, S=2, R=2, tasks="extend"), "pool"),
    "K32": (M.Design(K=32, S=2, R=2, tasks="base"), "pool"),
    "EXT81": (M.Design(K=81, S=2, R=2, tasks="srs"), "parametric"),
}


def cmd_ppc(args: argparse.Namespace) -> int:
    s1a = D.load()
    fit, params, bank = load_calibration(args.fit, args.set_param, s1a)
    observed = {"K113": s1a.y_pool, "K32": s1a.y_base, "EXT81": s1a.y_pool[:, 32:]}
    out: dict[str, Any] = {"fit": args.fit, "set_param": args.set_param or [],
                           "params": params.to_json(), "seed": args.seed, "nsim": args.nsim,
                           "targets": {}}  # fmt: skip
    for ti, name in enumerate(args.targets):
        design, source = PPC_TARGETS[name]
        t0 = time.time()
        obs = reading(observed[name][None], M.SIZES, np.random.default_rng(42),
                      np.random.default_rng([42, 13, ti]))  # fmt: skip
        rng = np.random.default_rng([args.seed, 21, ti])
        y, _ = M.simulate(params, design, args.nsim, rng, source=source, sessions="realized",
                          bank=bank if source == "pool" else None)  # fmt: skip
        sim = reading(y, M.SIZES, np.random.default_rng([args.seed, 22, ti]),
                      np.random.default_rng([args.seed, 13, ti]))  # fmt: skip
        out["targets"][name] = {
            "source": source,
            "observed": {k: (v[0] if v.dtype == object else float(v[0])) for k, v in obs.items()},
            "per_set": {k: v for k, v in sim.items()},
            "seconds": time.time() - t0,
        }
        ST.log({"target": name, "seed": args.seed, "seconds": time.time() - t0})
    out["population_pool"] = M.population(params, source="pool", bank=bank)
    out["provenance"] = ST.provenance()
    ST._write(Path(args.out), out)
    return 0


def evaluate_ppc(targets: dict[str, Any]) -> dict[str, Any]:
    checks, ok = {}, True
    for name in PPC_CRITERIA["targets"]:
        if name not in targets:
            continue
        t = targets[name]
        for group in ("decision", "structure"):
            lo, hi = PPC_CRITERIA[f"{group}_rank_range"]
            for st in PPC_CRITERIA[f"{group}_stats"]:
                r = t["ranks"][st]
                good = bool(lo <= r <= hi) if math.isfinite(r) else True
                checks[f"{name}:{st}"] = {"rank": r, "ok": good, "group": group}
                ok &= good
        pmin = PPC_CRITERIA["min_outcome_probability"]
        for rule in ("DR2", "DR5"):
            p = t[f"P_observed_{rule}"]
            checks[f"{name}:P_observed_{rule}"] = {"p": p, "ok": bool(p >= pmin)}
            ok &= p >= pmin
    failed = [k for k, v in checks.items() if not v["ok"]]
    return {"pass": bool(ok), "failed": failed, "checks": checks}


def cmd_merge_ppc(args: argparse.Namespace) -> int:
    parts = [json.loads(Path(p).read_text(encoding="utf-8")) for p in args.files]
    out: dict[str, Any] = {"files": args.files, "seeds": [p["seed"] for p in parts],
                           "fit": parts[0]["fit"], "set_param": parts[0]["set_param"],
                           "params": parts[0]["params"],
                           "population_pool": parts[0]["population_pool"],
                           "targets": {}}  # fmt: skip
    for name in parts[0]["targets"]:
        obs = parts[0]["targets"][name]["observed"]
        per = [p["targets"][name]["per_set"] for p in parts]
        pooled = {
            k: np.concatenate(
                [np.asarray(q[k], dtype=object if k in ("dr2", "dr5") else float) for q in per]
            )
            for k in per[0]
        }
        t: dict[str, Any] = {"n": len(pooled["dr2"]), "observed": obs, "ranks": {},
                             "sim": {}}  # fmt: skip
        for k, v in pooled.items():
            if k in ("dr2", "dr5") or not isinstance(obs.get(k), (int, float)):
                continue
            v = v.astype(float)
            t["ranks"][k] = mid_rank(v, float(obs[k]))
            fin = v[np.isfinite(v)]
            if fin.size:
                t["sim"][k] = {"median": float(np.median(fin)), "p05": float(np.percentile(fin, 5)),
                               "p95": float(np.percentile(fin, 95))}  # fmt: skip
        t["P_observed_DR2"] = float(np.mean(pooled["dr2"] == obs["dr2"]))
        t["P_observed_DR5"] = float(np.mean(pooled["dr5"] == obs["dr5"]))
        t["P_DR2"] = {c: float(np.mean(pooled["dr2"] == c))
                      for c in ("Present", "Near-equivalent", "Inconclusive")}  # fmt: skip
        t["P_DR5"] = {c: float(np.mean(pooled["dr5"] == c))
                      for c in ("GO", "NO-GO", "INCONCLUSIVE")}  # fmt: skip
        out["targets"][name] = t
    out["criteria"] = PPC_CRITERIA
    out["verdict"] = evaluate_ppc(out["targets"])
    if "EXT81" in out["targets"]:
        ext = out["targets"]["EXT81"]
        out["out_of_sample_EXT81"] = {
            k: ext["ranks"][k]
            for k in PPC_CRITERIA["decision_stats"] + PPC_CRITERIA["structure_stats"]
            if k in ext["ranks"]
        }
    out["provenance"] = ST.provenance()
    ST._write(Path(args.out), out)
    ST.log({"verdict": out["verdict"]["pass"], "failed": out["verdict"]["failed"]})
    return 0


# --------------------------------------------------------------------------- designs


def caps_over_draws(model: C.CostModel, design: M.Design, pool, idx: np.ndarray | None):
    if idx is None or design.tasks != "stratified":
        return None
    caps = np.array([model.design(design, [pool[i] for i in row])["caps_min"] for row in idx])
    return {"median": float(np.median(caps)), "max": int(caps.max()),
            "P_over_478": float(np.mean(caps > C.CAP_TOTAL_MIN))}  # fmt: skip


def cmd_designs(args: argparse.Namespace) -> int:
    s1a = D.load()
    fit, params, bank = load_calibration(args.fit, args.set_param, s1a)
    model, _ = C.build(Path("."), s1a)
    cache: dict = {}
    out: dict[str, Any] = {"fit": args.fit, "set_param": args.set_param or [],
                           "params": params.to_json(), "source": args.source,
                           "seed": args.seed, "nsim": args.nsim, "cells": {}}  # fmt: skip
    for dname in args.designs:
        design = replace(DESIGNS[dname], name=dname)
        cost = model.design(design)
        for sname in args.scenarios:
            t0 = time.time()
            scen = resolve(sname, design, params, args.source, bank, cache)
            rng = np.random.default_rng([args.seed, 11, stream(dname)])
            y, truth = M.simulate(params, design, args.nsim, rng, source=args.source,
                                  sessions="random", scenario=scen,
                                  bank=bank if args.source == "pool" else None)  # fmt: skip
            res = FA.analyse(
                y, design.sizes, rng=np.random.default_rng([args.seed, 12, stream(dname)])
            )
            pop = M.population(params, scen, source=args.source,
                               bank=bank if args.source == "pool" else None)  # fmt: skip
            out["cells"][f"{dname}|{sname}"] = {
                "design": dname, "scenario": sname, "scenario_spec": scen.__dict__,
                "truth": {"pi_small": pop["pi_small"], "pi_4B": pop["4B"]["pi"],
                          "pi_9B": pop["9B"]["pi"], "delta_pooled": pop["delta_pooled"],
                          "delta_4B": pop["4B"]["delta"], "delta_9B": pop["9B"]["delta"]},
                "per_set": {k: res[k] for k in STORE},
                "cost": {k: cost[k] for k in ("episodes", "jobs", "physical_gpu_h", "caps_min",
                                              "caps_gpu_h", "vm_h", "wall_h_sequential")},
                "caps_over_draws": caps_over_draws(model, design, s1a.pool,
                                                   truth.get("pool_index")),
                "seconds": time.time() - t0,
            }  # fmt: skip
            summ = AN.summarise(res)
            ST.log({"cell": f"{dname}|{sname}", "seed": args.seed,
                    "P_DR2": summ["DR2"], "P_DR5": summ["DR5"],
                    "seconds": round(time.time() - t0, 1)})  # fmt: skip
    out["provenance"] = ST.provenance()
    ST._write(Path(args.out), out)
    return 0


def summarise_cell(per: dict[str, np.ndarray]) -> dict[str, Any]:
    s = AN.summarise(per)
    n = s["n"]
    lo, hi = per["ci90_low"], per["ci90_high"]
    s["P_px_le_0025"] = float(np.mean(per["p_x"] <= 0.025))
    s["P_pdelta_le_0025"] = float(np.mean(per["p_delta"] <= 0.025))
    s["P_ci90_within_7.5pp"] = float(np.mean((lo >= -0.075) & (hi <= 0.075)))
    s["P_pi_ub_below_0.12"] = float(np.mean(per["pi_small_ub"] < 0.12))
    s["mcse_max"] = float(0.5 / math.sqrt(n))
    return s


def cmd_merge_designs(args: argparse.Namespace) -> int:
    parts = [json.loads(Path(p).read_text(encoding="utf-8")) for p in args.files]
    out: dict[str, Any] = {"files": args.files, "seeds": [p["seed"] for p in parts],
                           "fit": parts[0]["fit"], "set_param": parts[0]["set_param"],
                           "params": parts[0]["params"], "source": parts[0]["source"],
                           "cells": {}}  # fmt: skip
    for key in parts[0]["cells"]:
        cells = [p["cells"][key] for p in parts if key in p["cells"]]
        per = {
            k: np.concatenate(
                [
                    np.asarray(c["per_set"][k], dtype=object if k in ("dr2", "dr5") else float)
                    for c in cells
                ]
            )
            for k in STORE
        }
        summ = summarise_cell(per)
        per_seed = {}
        for p, c in zip(parts, cells, strict=False):
            pc = {k: np.asarray(c["per_set"][k], dtype=object if k in ("dr2", "dr5") else float)
                  for k in STORE}  # fmt: skip
            ss = AN.summarise(pc)
            per_seed[str(p["seed"])] = {"P_DR2_decisive": ss["P_DR2_decisive"],
                                        "P_DR5_decisive": ss["P_DR5_decisive"]}  # fmt: skip
        draws = [c["caps_over_draws"] for c in cells if c["caps_over_draws"]]
        out["cells"][key] = {
            "design": cells[0]["design"], "scenario": cells[0]["scenario"],
            "truth": cells[0]["truth"], "cost": cells[0]["cost"],
            "caps_over_draws": {"median": float(np.median([d["median"] for d in draws])),
                                "max": max(d["max"] for d in draws),
                                "P_over_478": float(np.mean([d["P_over_478"] for d in draws]))}
            if draws else None,
            "summary": summ, "per_seed": per_seed,
        }  # fmt: skip
    out["provenance"] = ST.provenance()
    ST._write(Path(args.out), out)
    return 0


def cmd_cost_draws(args: argparse.Namespace) -> int:
    """Cap totals of every design over 2,000 registered stratified draws (stream [42, 99])."""
    s1a = D.load()
    model, _ = C.build(Path("."), s1a)
    rng = np.random.default_rng([42, 99])
    out: dict[str, Any] = {"cap_total_min": C.CAP_TOTAL_MIN, "designs": {}}
    for name, des in DESIGNS.items():
        row: dict[str, Any] = {"pool_mean": model.design(des)}
        row["pool_mean"].pop("per_job")
        if des.tasks == "stratified":
            idx = M.select_pool_tasks(des, s1a.pool, len(s1a.base), s1a.domains, rng, 2000)
            row["draws"] = caps_over_draws(model, des, s1a.pool, idx)
        out["designs"][name] = row
    out["provenance"] = ST.provenance()
    ST._write(Path(args.out), out)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Q2 successor-design comparison (CPU)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("ppc", "designs"):
        p = sub.add_parser(name)
        p.add_argument("--fit", required=True)
        p.add_argument("--set-param", nargs="*", dest="set_param")
        p.add_argument("--seed", type=int, choices=(42, 43, 44), required=True)
        p.add_argument("--nsim", type=int, default=150)
        p.add_argument("--out", required=True)
    sub.choices["ppc"].add_argument("--targets", nargs="+", default=["K113", "K32"],
                                    choices=tuple(PPC_TARGETS))  # fmt: skip
    p = sub.choices["designs"]
    p.add_argument("--source", default="pool", choices=("pool", "parametric"))
    p.add_argument("--designs", nargs="+", default=list(DESIGNS), choices=tuple(DESIGNS))
    p.add_argument("--scenarios", nargs="+", default=list(SCENARIOS), choices=SCENARIOS)
    for name in ("merge-ppc", "merge-designs"):
        p = sub.add_parser(name)
        p.add_argument("--out", required=True)
        p.add_argument("files", nargs="+")
    p = sub.add_parser("cost-draws")
    p.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    return {
        "ppc": cmd_ppc,
        "merge-ppc": cmd_merge_ppc,
        "designs": cmd_designs,
        "merge-designs": cmd_merge_designs,
        "cost-draws": cmd_cost_draws,
    }[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
