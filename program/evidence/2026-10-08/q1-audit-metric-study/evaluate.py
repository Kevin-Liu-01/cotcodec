"""Q1 audit-metric study (D41 ii), part 3: combine stored and CPU results.

Inputs: ``stored-characterisation.json`` (stored_characterisation.py) and the
per-draw records of cpu_study.py (``--cpu`` directory, S1-cal problems only).
Output: ``results.json`` with

1. ``emulation_validation``: the CPU TF32 emulation's registered error against
   the stored GPU TF32 reference error on the same draw;
2. ``characterisation``: per problem and draw, the registered threshold, the
   vacuity flags, and the conditioning that explains them;
3. ``candidates``: each candidate metric's calibrated threshold (smallest power
   of two at or above every correct realization's statistic on S1-cal, as the
   registered M rule does), leave-one-problem-out false-reject checks, and the
   detection of every destroyed output class, per policy;
4. ``restriction``: the registered metric restricted to determinate draws.

Revision 2 (after the replication and the critique):

* the emulation check compares with the stored realizations in which the device used
  TF32 (at least twice the fp32 error), over every arm and job; the first pass took the
  first stored realization and mislabelled three L2/100 draws;
* ``held_out_informativeness``: how many held-out correct realizations differ from
  every yardstick member at all (the first pass's "0 false rejects" was partly
  by construction);
* rule ``q1-audit-metric/1`` is re-evaluated with the absolute floor (2^-24 of the
  oracle's max-abs and rms block norm), exactly for ``rho_inf`` and with conservative
  bounds for ``rho_block`` where the floor binds;
* ``alt_algorithms``: correct outputs of algorithms that are not yardstick members
  (K-blocked sequential accumulation in fp32 and TF32, Winograd F(2x2,3x3) and
  F(4x4,3x3), sequential sums, more stochastic-rounding seeds; ``alt_algorithms.py``),
  scored with the oracle decoy battery on the same draws;
* ``rule2``: the three-valued rule ``q1-audit-metric/2`` (accept, precision-ambiguous,
  reject), evaluated on both record sets.

All thresholds here are fitted on the same S1-cal draws they are evaluated on
(the registered calibration does the same); the leave-one-problem-out check is
the out-of-sample number.
"""

from __future__ import annotations

import argparse
import collections
import glob
import json
import math
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
KAPPA = 1e-3
E_ZEROS = 1 / (1 + KAPPA)
MULT = 16
T_FLOOR = 2.0**-20
YARDSTICKS = {
    "strict": ["fp32"],
    "tf32_reg": ["fp32", "tf32_rne"],
    # the registered tl.dot switch: candidates that do not call tl.dot are held to the RNE
    # yardstick; the truncating realization is then not an admissible candidate
    "tf32_rne_no_tl_dot": ["fp32", "tf32_rne"],
    "tf32_ext": ["fp32", "tf32_rne", "tf32_rz"],
}
#: which of cpu_study's stored M2 yardsticks a policy uses
M2_SOURCE = {"strict": "strict", "tf32_reg": "tf32_reg", "tf32_rne_no_tl_dot": "tf32_reg", "tf32_ext": "tf32_ext"}
#: correct realizations that are not yardstick members, per yardstick (leave-one-out FRR)
HELD_OUT = {"strict": ["fp32_nnpack"], "tf32_reg": ["tf32_rz", "tf32_sr", "fp32_nnpack"], "tf32_rne_no_tl_dot": ["tf32_sr", "fp32_nnpack"], "tf32_ext": ["tf32_sr", "fp32_nnpack"]}
#: every realization that is correct under a policy (M3 has no yardstick)
CORRECT_UNDER = {"strict": ["fp32", "fp32_nnpack"], "tf32_reg": ["fp32", "fp32_nnpack", "tf32_rne", "tf32_rz", "tf32_sr"], "tf32_rne_no_tl_dot": ["fp32", "fp32_nnpack", "tf32_rne", "tf32_sr"], "tf32_ext": ["fp32", "fp32_nnpack", "tf32_rne", "tf32_rz", "tf32_sr"]}
CLASSES = {
    "gross": ["zeros", "negation", "constant_mean", "shuffled", "tile_missing_1of64", "last_row_zero", "sparse_1e-3_zeroed", "single_max_zeroed"],
    "mutant_family_emulations": ["bias_sign", "add_value_sign", "drop_last_k", "load_offset_off1", "acc_fp16"],
    "subtle_1e-2": ["gain_1e-2", "noise_1e-2"],
    "precision_boundary": ["gain_1e-3", "store_fp16", "store_scale_nudge_1e-4"],
}
FAMILY = {
    "zeros": "boundary (mask-drop, lt2gt), semantic (sentinel-zero)",
    "negation": "semantic (acc-minus), arithmetic (negate-store)",
    "constant_mean": "semantic (acc-overwrite)",
    "shuffled": "indexing (program-id-axis-swap, stride/dim swaps)",
    "tile_missing_1of64": "boundary (lt2gt, grid bound) / indexing (block-size-to-num-programs)",
    "last_row_zero": "boundary (mask-bound-minus1 on rows)",
    "sparse_1e-3_zeroed": "boundary/indexing, scattered",
    "single_max_zeroed": "boundary, one element",
    "bias_sign": "arithmetic (plus2minus on the bias add)",
    "add_value_sign": "arithmetic (plus2minus on the parameter add)",
    "drop_last_k": "boundary (mask-bound-minus1, loop-bound-minus1 on the reduction)",
    "load_offset_off1": "indexing (load-offset-off1)",
    "acc_fp16": "precision (acc-fp16)",
    "gain_1e-2": "precision (constant perturbation, 1e-2)",
    "noise_1e-2": "generic 1% noise",
    "gain_1e-3": "precision (named-constant-perturb, 1e-3)",
    "store_fp16": "precision (store-fp16)",
    "store_scale_nudge_1e-4": "precision (store-scale-nudge, 0.9999)",
}
METRICS = ("REG", "M1_l2", "M1_linf", "M2_phi0.25", "M2_phi1", "M3_gauge", "M6_gauge_floor")


def pow2_ceil(x: float) -> float:
    if not math.isfinite(x) or x <= 0:
        return x
    return 2.0 ** math.ceil(math.log2(x))


def load_cpu(cpu_dir: Path) -> list[dict[str, Any]]:
    recs = []
    for f in sorted(glob.glob(str(cpu_dir / "*.json"))):
        recs.append(json.loads(Path(f).read_text()))
    return recs


def admissible_cpu(rec: dict[str, Any], stored: dict[tuple, dict[str, Any]]) -> bool:
    key = (rec["problem"], rec["channel"], "/".join(rec["config_id"].split("/")[:2]), rec["facts"]["seed"])
    st = stored.get(key)
    if st is not None and st.get("admissible") is not None:
        return bool(st["admissible"])
    if rec["channel"] == "A1":
        return True
    # no stored row: the audit validity gate's fp32 ceiling, on the CPU fp32 reference
    return rec["out"]["correct"]["fp32"]["e_reg"] <= 1e-3


def ratios(rec: dict[str, Any], policy: str) -> dict[str, dict[str, dict[str, float]]]:
    """metric -> group -> output name -> statistic / yardstick (M3: raw statistic)."""
    out = rec["out"]
    ys = [y for y in YARDSTICKS[policy] if y in out["correct"]]
    gauge = "s" if policy == "strict" else "t"
    T = max(MULT * max(out["correct"][y]["e_reg"] for y in ys), T_FLOOR)
    N2 = max(out["correct"][y]["l2"] for y in ys)
    Ninf = max(out["correct"][y]["linf"] for y in ys)
    T6 = max(MULT * max(out["correct"][y][f"m6_{gauge}"] for y in ys), T_FLOOR)
    res: dict[str, dict[str, dict[str, float]]] = {m: {"correct": {}, "destroyed": {}} for m in METRICS}
    for group in ("correct", "destroyed"):
        for name, s in out[group].items():
            def div(a: float, b: float) -> float:
                if b == 0:
                    return 0.0 if a == 0 else math.inf
                return a / b
            res["REG"][group][name] = div(s["e_reg"], T)
            res["M1_l2"][group][name] = div(s["l2"], N2)
            res["M1_linf"][group][name] = div(s["linf"], Ninf)
            m2 = out["m2"][M2_SOURCE[policy]][group].get(name, {})
            res["M2_phi0.25"][group][name] = m2.get("phi_0.25", math.nan)
            res["M2_phi1"][group][name] = m2.get("phi_1.0", math.nan)
            res["M3_gauge"][group][name] = s[f"m3_{gauge}"]
            res["M6_gauge_floor"][group][name] = div(s[f"m6_{gauge}"], T6)
    return res


def physical(rec: dict[str, Any], realization: str) -> bool:
    """Stochastic rounding is an ensemble device, not a hardware TF32 mode: it rounds
    equal values differently. On A2/constrows (rows of one repeated value) every real
    TF32 unit (RNE or truncation, as cuBLAS, cuDNN and tl.dot do) rounds a repeated
    value identically, so the stochastic member there is excluded from calibration and
    false-reject counts and reported apart (``sr_on_constrows``)."""
    return not (realization == "tf32_sr" and "/constrows/" in rec["config_id"])


def effective(rec: dict[str, Any], name: str) -> bool:
    """A decoy counts only if it differs from the oracle by more than 16x the CPU fp32
    reference's own error (otherwise it is equivalent within fp32 noise, e.g. a bias
    whose sign is flipped before a training-mode batch norm, which cancels it)."""
    d = rec["out"]["destroyed"][name]
    return d["l2"] > MULT * rec["out"]["correct"]["fp32"]["l2"] or not d["finite"]


def eval_candidates(records: list[dict[str, Any]]) -> dict[str, Any]:
    cand: dict[str, Any] = {}
    for policy in YARDSTICKS:
        per_draw = [(r, ratios(r, policy)) for r in records]
        pol: dict[str, Any] = {}
        for m in METRICS:
            corr_names = CORRECT_UNDER[policy] if m == "M3_gauge" else HELD_OUT[policy] + YARDSTICKS[policy]
            corr_vals = []
            by_problem = collections.defaultdict(list)
            excluded = []
            for r, rt in per_draw:
                for n in corr_names:
                    v = rt[m]["correct"].get(n)
                    if v is None or not math.isfinite(v):
                        continue
                    if not physical(r, n):
                        excluded.append(v)
                        continue
                    corr_vals.append((v, r["problem"], r["config_id"], n))
                    by_problem[r["problem"]].append(v)
            if not corr_vals:
                continue
            worst = max(corr_vals)
            floor1 = m != "M3_gauge"
            theta = max(pow2_ceil(worst[0]), 1.0) if floor1 else pow2_ceil(worst[0])
            theta_m2 = max(pow2_ceil(2 * worst[0]), 1.0) if floor1 else pow2_ceil(2 * worst[0])
            lopo = {}
            for p, vals in by_problem.items():
                others = [v for v, pp, _, _ in corr_vals if pp != p]
                th = (max(pow2_ceil(max(others)), 1.0) if floor1 else pow2_ceil(max(others))) if others else math.nan
                lopo[p] = {"theta_without": th, "max_correct": max(vals), "false_rejects": sum(v > th for v in vals), "n": len(vals)}
            pol[m] = {
                "theta": theta,
                "theta_with_x2_margin": theta_m2,
                "worst_correct": {"value": worst[0], "problem": worst[1], "config": worst[2], "realization": worst[3]},
                "leave_one_problem_out": lopo,
                "sr_on_constrows": {"n": len(excluded), "max": max(excluded) if excluded else None,
                                    "theta_if_included": (max(pow2_ceil(max(max(excluded), worst[0])), 1.0) if floor1 else pow2_ceil(max(max(excluded), worst[0]))) if excluded else theta},
                "lopo_false_reject_problems": sorted(p for p, d in lopo.items() if d["false_rejects"]),
            }
            for label, th in (("at_theta", theta), ("at_theta_x2", theta_m2)):
                det: dict[str, Any] = {}
                vac = collections.defaultdict(list)
                equivalent = 0
                for cls, names in CLASSES.items():
                    for n in names:
                        vals = []
                        for r, rt in per_draw:
                            if n not in rt[m]["destroyed"]:
                                continue
                            if not effective(r, n):
                                equivalent += 1
                                continue
                            v = rt[m]["destroyed"][n]
                            vals.append((math.inf if math.isnan(v) else v, r["problem"], r["config_id"]))
                        if not vals:
                            continue
                        esc = [(p, cfg, v) for v, p, cfg in vals if v <= th]
                        size = {(r["problem"], r["config_id"]): rt["M1_l2"]["destroyed"][n] for r, rt in per_draw if n in rt["M1_l2"]["destroyed"]}
                        sub_noise = [x for x in esc if size.get((x[0], x[1]), math.inf) < 1.0]
                        bands = collections.Counter()
                        for x in esc:
                            z = size.get((x[0], x[1]), math.inf)
                            bands["size<1x" if z < 1 else "1x<=size<4x" if z < 4 else "size>=4x"] += 1
                        det[n] = {
                            "class": cls, "family": FAMILY[n], "draws": len(vals), "escapes": len(esc),
                            "escapes_below_yardstick_noise": len(sub_noise),
                            "escapes_by_size_vs_yardstick_l2": dict(bands),
                            "min_ratio_over_theta": min(v for v, _, _ in vals) / th,
                            "median_ratio_over_theta": sorted(v for v, _, _ in vals)[len(vals) // 2] / th,
                            "escaped": sorted({f"{p} {cfg}" for p, cfg, _ in esc})[:25],
                        }
                        if n in ("zeros", "negation"):
                            vac[n] = [f"{p} {cfg}" for p, cfg, _ in esc]
                pol[m][label] = {
                    "destroyed": det,
                    "equivalent_decoys_skipped": equivalent,
                    "gross_min_margin": min((d["min_ratio_over_theta"] for d in det.values() if d["class"] == "gross"), default=math.nan),
                    "draws_admitting_zeros": vac.get("zeros", []),
                    "draws_admitting_negation": vac.get("negation", []),
                    "escapes_by_class": {cls: sum(d["escapes"] for d in det.values() if d["class"] == cls) for cls in CLASSES},
                    "escapes_above_noise_by_class": {cls: sum(d["escapes"] - d["escapes_below_yardstick_noise"] for d in det.values() if d["class"] == cls) for cls in CLASSES},
                    "escapes_size_ge_4x_by_class": {cls: sum(d["escapes_by_size_vs_yardstick_l2"].get("size>=4x", 0) for d in det.values() if d["class"] == cls) for cls in CLASSES},
                    "cases_by_class": {cls: sum(d["draws"] for d in det.values() if d["class"] == cls) for cls in CLASSES},
                }
        # conjunction: reject if M1_linf or M2 (phi 1) rejects, each at its own theta
        if "M1_linf" in pol and "M2_phi1" in pol:
            t1, t2 = pol["M1_linf"]["theta"], pol["M2_phi1"]["theta"]
            conj = collections.Counter()
            cases = collections.Counter()
            escaped = []
            fr = 0
            for r, rt in per_draw:
                for n in HELD_OUT[policy] + YARDSTICKS[policy]:
                    if n in rt["M1_linf"]["correct"] and physical(r, n) and (rt["M1_linf"]["correct"][n] > t1 or rt["M2_phi1"]["correct"][n] > t2):
                        fr += 1
                for cls, names in CLASSES.items():
                    for n in names:
                        if n not in rt["M1_linf"]["destroyed"] or not effective(r, n):
                            continue
                        cases[cls] += 1
                        if rt["M1_linf"]["destroyed"][n] <= t1 and rt["M2_phi1"]["destroyed"][n] <= t2:
                            conj[cls] += 1
                            escaped.append(f"{r['problem']} {r['config_id']} {n} size={rt['M1_l2']['destroyed'][n]:.2f}")
            pol["M1_linf_or_M2_phi1"] = {"thetas": [t1, t2], "correct_false_rejects": fr, "escapes_by_class": dict(conj), "cases_by_class": dict(cases), "escaped_excluding_precision_boundary": [e for e in escaped if not any(t in e for t in CLASSES["precision_boundary"])]}
        # determinacy gate (three-valued verdict): a draw is determinate under a metric only if
        # every battery decoy (computable from the oracle alone) scores at least 4 theta
        battery = ("zeros", "negation", "tile_missing_1of64", "single_max_zeroed")
        for m in METRICS:
            if m not in pol:
                continue
            th = pol[m]["theta"]
            indet = []
            for r, rt in per_draw:
                worst = min(rt[m]["destroyed"][n] for n in battery if n in rt[m]["destroyed"])
                if not worst >= 4 * th:
                    indet.append({"problem": r["problem"], "config": r["config_id"], "battery_min_over_theta": worst / th})
            pol[m]["determinacy_gate_4theta"] = {"draws": len(per_draw), "indeterminate": len(indet), "indeterminate_draws": indet[:25]}
        cand[policy] = pol
        reg_exact = {}
        for cls, names in CLASSES.items():
            for n in names:
                vals = [(rt["REG"]["destroyed"][n], r["problem"], r["config_id"]) for r, rt in per_draw if n in rt["REG"]["destroyed"] and effective(r, n)]
                if vals:
                    reg_exact[n] = {"class": cls, "draws": len(vals), "escapes": sum(v <= 1 for v, _, _ in vals), "escaped_problems": sorted({p for v, p, _ in vals if v <= 1})}
        corr = [(rt["REG"]["correct"][n], r["problem"], r["config_id"], n) for r, rt in per_draw for n in HELD_OUT[policy] if n in rt["REG"]["correct"] and physical(r, n)]
        cand[policy]["REG_as_registered"] = {
            "rule": "pass if e <= T = 16 max e(yardstick member); a held-out correct realization above T is a false reject",
            "destroyed": reg_exact,
            "escapes_by_class": {cls: sum(d["escapes"] for d in reg_exact.values() if d["class"] == cls) for cls in CLASSES},
            "cases_by_class": {cls: sum(d["draws"] for d in reg_exact.values() if d["class"] == cls) for cls in CLASSES},
            "held_out_correct_false_rejects": [{"problem": p, "config": cfg, "realization": n, "e_over_T": v} for v, p, cfg, n in corr if v > 1],
            "held_out_correct_cases": len(corr),
        }
    return cand


#: the recommended rule's pre-specified thresholds (theta_linf, theta_M2): the in-sample
#: calibration rounded up to a power of two, then doubled (strict M2 also covers NNPACK
#: Winograd on A2/spiky, an inadmissible draw under the registered validity gate)
RECOMMENDED = {"strict": (4.0, 16.0), "tf32_rne_no_tl_dot": (4.0, 8.0), "tf32_ext": (4.0, 8.0)}
BATTERY = ("zeros", "negation", "tile_missing_1of64", "single_max_zeroed")


def recommended_rule(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Reject iff M1_linf > theta_linf or M2 (phi 1) > theta_M2; a draw is determinate only if
    every battery decoy is rejected with both statistics' combined margin >= 4 (max of the two
    ratios over theta >= 4); indeterminate draws are excluded and reported."""
    out: dict[str, Any] = {}
    for policy, (t1, t2) in RECOMMENDED.items():
        per_problem: dict[str, Any] = collections.defaultdict(lambda: {"draws": 0, "indeterminate": [], "false_rejects": [], "escapes": collections.Counter(), "cases": collections.Counter(), "escaped": []})
        for r in records:
            rt = ratios(r, policy)
            pp = per_problem[r["problem"]]
            pp["draws"] += 1

            def score(group: str, n: str) -> float:
                return max(rt["M1_linf"][group][n] / t1, rt["M2_phi1"][group][n] / t2)

            battery = min(score("destroyed", n) for n in BATTERY if n in rt["M1_linf"]["destroyed"])
            if battery < 4:
                pp["indeterminate"].append(f"{r['config_id']} battery={battery:.2f}")
                continue
            for n in HELD_OUT[policy] + YARDSTICKS[policy]:
                if n in rt["M1_linf"]["correct"] and physical(r, n) and score("correct", n) > 1:
                    pp["false_rejects"].append(f"{r['config_id']} {n} {score('correct', n):.2f}")
            for cls, names in CLASSES.items():
                for n in names:
                    if n not in rt["M1_linf"]["destroyed"] or not effective(r, n):
                        continue
                    pp["cases"][cls] += 1
                    if score("destroyed", n) <= 1:
                        size = rt["M1_l2"]["destroyed"][n]
                        pp["escapes"][cls] += 1
                        pp["escaped"].append(f"{r['config_id']} {n} size={size:.2f}")
        tot_c, tot_e = collections.Counter(), collections.Counter()
        for pp in per_problem.values():
            tot_c.update(pp["cases"])
            tot_e.update(pp["escapes"])
        out[policy] = {
            "thetas": {"M1_linf": t1, "M2_phi1": t2},
            "draws": sum(pp["draws"] for pp in per_problem.values()),
            "indeterminate": sum(len(pp["indeterminate"]) for pp in per_problem.values()),
            "false_rejects": sum(len(pp["false_rejects"]) for pp in per_problem.values()),
            "escapes_by_class": dict(tot_e),
            "cases_by_class": dict(tot_c),
            "per_problem": {p: {**pp, "escapes": dict(pp["escapes"]), "cases": dict(pp["cases"])} for p, pp in sorted(per_problem.items())},
        }
    return out


# --- revision 2 -----------------------------------------------------------------------------

FLOOR_REL = 2.0**-24
BLOCK = 4096


def floor_terms(rec: dict[str, Any], policy: str) -> dict[str, float]:
    """The absolute floor of rule q1-audit-metric/2 for one draw and policy: F_inf = 2^-24
    ||r||_inf and F_b = 2^-24 (rms block norm of r), against the yardstick's max-abs error
    and rms block noise."""
    out, cond = rec["out"], rec["conditioning"]
    ys = [y for y in YARDSTICKS[policy] if y in out["correct"]]
    nblocks = -(-cond["numel"] // BLOCK)
    return {
        "ninf": max(out["correct"][y]["linf"] for y in ys),
        "f_inf": FLOOR_REL * cond["r_inf"],
        "rms": out["m2"][M2_SOURCE[policy]]["rms_block_noise_l2"],
        "f_b": FLOOR_REL * cond["r_l2"] / math.sqrt(nblocks),
    }


def floored(rec: dict[str, Any], policy: str, group: str, name: str) -> tuple[float, float, bool]:
    """(rho_inf, rho_block, exact) with the floor. rho_inf is exact. rho_block is exact where the
    floor does not bind (rms block noise >= F_b); where it binds, a correct output gets its
    unfloored value (an upper bound) and a destroyed output the lower bound M2 x rms / F_b."""
    ft = floor_terms(rec, policy)
    s = rec["out"][group][name]
    rho_inf = s["linf"] / max(ft["ninf"], ft["f_inf"]) if max(ft["ninf"], ft["f_inf"]) > 0 else (0.0 if s["linf"] == 0 else math.inf)
    if not s.get("finite", True):
        rho_inf = math.inf
    m2 = rec["out"]["m2"][M2_SOURCE[policy]][group].get(name, {}).get("phi_1.0", math.nan)
    if ft["rms"] >= ft["f_b"]:
        return rho_inf, m2, True
    if group == "correct":
        return rho_inf, m2, False
    return rho_inf, (m2 * ft["rms"] / ft["f_b"]) if ft["rms"] > 0 else 0.0, False


def recommended_rule_floored(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Rule q1-audit-metric/1 (thresholds as recommended) with the floor added."""
    out: dict[str, Any] = {}
    for policy, (t1, t2) in RECOMMENDED.items():
        draws = indet = fr = 0
        esc, cases = collections.Counter(), collections.Counter()
        binding = set()
        escaped: list[str] = []
        for r in records:
            draws += 1
            ft = floor_terms(r, policy)
            if ft["ninf"] < ft["f_inf"] or ft["rms"] < ft["f_b"]:
                binding.add(f"{r['problem']} {r['config_id']}")

            def sc(group: str, n: str) -> float:
                ri, rb, _ = floored(r, policy, group, n)
                return max(ri / t1, rb / t2)

            if min(sc("destroyed", n) for n in BATTERY if n in r["out"]["destroyed"]) < 4:
                indet += 1
                continue
            for n in HELD_OUT[policy] + YARDSTICKS[policy]:
                if n in r["out"]["correct"] and physical(r, n) and sc("correct", n) > 1:
                    fr += 1
            for cls, names in CLASSES.items():
                for n in names:
                    if n not in r["out"]["destroyed"] or not effective(r, n):
                        continue
                    cases[cls] += 1
                    if sc("destroyed", n) <= 1:
                        esc[cls] += 1
                        if cls != "precision_boundary":
                            escaped.append(f"{r['problem']} {r['config_id']} {n}")
        out[policy] = {"thetas": {"M1_linf": t1, "M2_phi1": t2}, "draws": draws, "indeterminate": indet, "false_rejects": fr,
                       "escapes_by_class": dict(esc), "cases_by_class": dict(cases), "escaped_excluding_precision_boundary": escaped,
                       "draws_where_floor_binds": sorted(binding)}
    return out


def held_out_informativeness(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Per policy: held-out correct realizations, and how many differ from every yardstick
    member at all (same max-abs and L2 error = bitwise the same output, in practice)."""
    out: dict[str, Any] = {}
    for policy in ("strict", "tf32_rne_no_tl_dot", "tf32_ext"):
        c = collections.defaultdict(lambda: {"cases": 0, "identical_to_a_yardstick_member": 0, "problems": set()})
        for r in records:
            ys = [r["out"]["correct"][y] for y in YARDSTICKS[policy] if y in r["out"]["correct"]]
            for n in HELD_OUT[policy]:
                if n not in r["out"]["correct"] or not physical(r, n):
                    continue
                s = r["out"]["correct"][n]
                d = c[n]
                d["cases"] += 1
                d["problems"].add(r["problem"])
                if any(s["linf"] == y["linf"] and s["l2"] == y["l2"] for y in ys):
                    d["identical_to_a_yardstick_member"] += 1
        out[policy] = {n: {**v, "problems": sorted(v["problems"])} for n, v in c.items()}
    return out


# --- rule q1-audit-metric/2 (three-valued) ------------------------------------------------

#: policy -> yardstick key in the CPU records and alt records; thresholds
#: (accept if rho_inf <= a_inf and rho_block <= a_blk; reject if rho_inf > R_inf or
#: rho_block > R_blk; otherwise precision-ambiguous). The accept band is rule /1's. The
#: reject thresholds were chosen after the critique's Winograd numbers and the first
#: alternative-algorithm records were seen: in-sample, like every threshold in this study.
RULE2: dict[str, dict[str, Any]] = {
    "strict": {"cpu_yardstick": "strict", "alt_yardstick": "strict", "accept": (4.0, 16.0), "reject": (256.0, 256.0)},
    "tf32": {"cpu_yardstick": "tf32_ext", "alt_yardstick": "tf32_ext", "accept": (4.0, 8.0), "reject": (64.0, 128.0)},
    "tf32_rne_only": {"cpu_yardstick": "tf32_rne_no_tl_dot", "alt_yardstick": "tf32_rne", "accept": (4.0, 8.0), "reject": (64.0, 128.0)},
    # sensitivity: reject thresholds doubled (2x margin over the worst valid algorithm seen)
    "tf32_wide": {"cpu_yardstick": "tf32_ext", "alt_yardstick": "tf32_ext", "accept": (4.0, 8.0), "reject": (128.0, 256.0)},
    "tf32_rne_only_wide": {"cpu_yardstick": "tf32_rne_no_tl_dot", "alt_yardstick": "tf32_rne", "accept": (4.0, 8.0), "reject": (128.0, 256.0)},
}
RULE2_GATE = 2.0  # a draw is determinate if every battery decoy scores >= 2x the reject threshold


def verdict2(ri: float, rb: float, pol: dict[str, Any]) -> str:
    (a1, a2), (r1, r2) = pol["accept"], pol["reject"]
    if ri > r1 or rb > r2:
        return "reject"
    if ri <= a1 and rb <= a2:
        return "accept"
    return "ambiguous"


def reject_score(ri: float, rb: float, pol: dict[str, Any]) -> float:
    r1, r2 = pol["reject"]
    return max(ri / r1, rb / r2)


def rule2(records: list[dict[str, Any]], alt: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name, pol in RULE2.items():
        ypol = pol["cpu_yardstick"]
        corr_names = HELD_OUT[ypol] + YARDSTICKS[ypol]
        res: dict[str, Any] = {"thresholds": {"accept": pol["accept"], "reject": pol["reject"], "gate": RULE2_GATE},
                               "cpu_draws": 0, "cpu_indeterminate": [], "correct": collections.Counter(), "correct_not_accepted": [],
                               "destroyed": collections.defaultdict(collections.Counter), "battery_min_reject_score": math.inf,
                               "alt_draws": 0, "alt_indeterminate": [], "alt_correct": collections.defaultdict(collections.Counter),
                               "alt_correct_not_accepted": [], "alt_decoys": collections.defaultdict(collections.Counter),
                               "alt_max": collections.defaultdict(lambda: [0.0, 0.0])}
        for r in records:
            res["cpu_draws"] += 1
            bat = []
            for n in BATTERY:
                if n in r["out"]["destroyed"]:
                    ri, rb, _ = floored(r, ypol, "destroyed", n)
                    bat.append(reject_score(ri, rb, pol))
            bmin = min(bat)
            res["battery_min_reject_score"] = min(res["battery_min_reject_score"], bmin)
            if bmin < RULE2_GATE:
                res["cpu_indeterminate"].append(f"{r['problem']} {r['config_id']} battery={bmin:.2f}")
                continue
            for n in corr_names:
                if n in r["out"]["correct"] and physical(r, n):
                    ri, rb, _ = floored(r, ypol, "correct", n)
                    v = verdict2(ri, rb, pol)
                    res["correct"][v] += 1
                    if v != "accept":
                        res["correct_not_accepted"].append(f"{r['problem']} {r['config_id']} {n} {v} rho_inf={ri:.2f} rho_block={rb:.2f}")
            for cls, names in CLASSES.items():
                for n in names:
                    if n in r["out"]["destroyed"] and effective(r, n):
                        ri, rb, _ = floored(r, ypol, "destroyed", n)
                        res["destroyed"][cls][verdict2(ri, rb, pol)] += 1
        for a in alt:
            res["alt_draws"] += 1
            ap = pol["alt_yardstick"]
            bmin = min(reject_score(a["decoys"][n]["scores"][ap]["rho_inf"], a["decoys"][n]["scores"][ap]["rho_block"], pol) for n in BATTERY if n in a["decoys"])
            if bmin < RULE2_GATE:
                res["alt_indeterminate"].append(f"{a['problem']} {a['config_id']} battery={bmin:.2f}")
                continue
            for n, v in a["alternatives"].items():
                if ap not in v["correct_under"] and not (name.startswith("tf32_rne_only") and "rz" in n):
                    continue
                if not alt_physical(a, n):
                    continue
                sc = v["scores"][ap]
                vd = verdict2(sc["rho_inf"], sc["rho_block"], pol)
                cls = alt_class(n)
                res["alt_correct"][cls][vd] += 1
                mx = res["alt_max"][cls]
                mx[0], mx[1] = max(mx[0], sc["rho_inf"]), max(mx[1], sc["rho_block"])
                if vd != "accept":
                    res["alt_correct_not_accepted"].append(f"{a['problem']} {a['config_id']} {n} {vd} rho_inf={sc['rho_inf']:.2f} rho_block={sc['rho_block']:.2f}")
            for n, v in a["decoys"].items():
                sc = v["scores"][ap]
                res["alt_decoys"][n][verdict2(sc["rho_inf"], sc["rho_block"], pol)] += 1
        res["correct"] = dict(res["correct"])
        res["destroyed"] = {k: dict(v) for k, v in res["destroyed"].items()}
        res["alt_correct"] = {k: dict(v) for k, v in res["alt_correct"].items()}
        res["alt_decoys"] = {k: dict(v) for k, v in res["alt_decoys"].items()}
        res["alt_max"] = {k: {"rho_inf": v[0], "rho_block": v[1]} for k, v in res["alt_max"].items()}
        out[name] = res
    return out


def alt_physical(a: dict[str, Any], name: str) -> bool:
    """As ``physical``: stochastic rounding on A2/constrows is not a hardware TF32 mode."""
    return not (name.startswith("tf32_sr") and "/constrows/" in a["config_id"])


def alt_class(name: str) -> str:
    for k in ("wino43", "wino23", "seq1", "kblock32", "kblock", "tf32_sr"):
        if name.startswith(k):
            return name.rsplit("_s", 1)[0] if k == "tf32_sr" else name
    return name


def alt_summary(alt: list[dict[str, Any]]) -> dict[str, Any]:
    """Per yardstick and alternative: the largest rho_inf / rho_block of the valid alternative
    algorithms, admissible draws and all draws, and how many exceed the q1-audit-metric/1
    thresholds; and the decoy battery's smallest raw ratios on the same draws."""
    out: dict[str, Any] = {}
    for yp in ("strict", "tf32_rne", "tf32_ext"):
        t1, t2 = (4.0, 16.0) if yp == "strict" else (4.0, 8.0)
        per: dict[str, Any] = {}
        for a in alt:
            for n, v in a["alternatives"].items():
                sc = v["scores"][yp]
                if not alt_physical(a, n):
                    d = per.setdefault("tf32_sr_on_constrows (excluded)", {}).setdefault("all", {"draws": 0, "max_rho_inf": 0.0, "max_rho_block": 0.0})
                    d["draws"] += 1
                    d["max_rho_inf"] = max(d["max_rho_inf"], sc["rho_inf"])
                    d["max_rho_block"] = max(d["max_rho_block"], sc["rho_block"])
                    continue
                for sub in ("all", "admissible") if a.get("admissible") else ("all",):
                    d = per.setdefault(n, {}).setdefault(sub, {"draws": 0, "max_rho_inf": 0.0, "max_rho_block": 0.0, "worst": None, "over_rule1": 0, "over_rule1_draws": [], "problems": set(), "correct_under_this_yardstick": yp in v["correct_under"]})
                    d["draws"] += 1
                    d["problems"].add(a["problem"])
                    if sc["rho_inf"] > d["max_rho_inf"]:
                        d["worst"] = f"{a['problem']} {a['config_id']}"
                    d["max_rho_inf"] = max(d["max_rho_inf"], sc["rho_inf"])
                    d["max_rho_block"] = max(d["max_rho_block"], sc["rho_block"])
                    if sc["rho_inf"] > t1 or sc["rho_block"] > t2:
                        d["over_rule1"] += 1
                        d["over_rule1_draws"].append(f"{a['problem']} {a['config_id'].rsplit('/', 1)[0]} {sc['rho_inf']:.1f}/{sc['rho_block']:.1f}")
        for n in per:
            for sub in per[n]:
                if "problems" in per[n][sub]:
                    per[n][sub]["problems"] = sorted(per[n][sub]["problems"])
        dec: dict[str, Any] = {}
        for a in alt:
            for n, v in a["decoys"].items():
                sc = v["scores"][yp]
                d = dec.setdefault(n, {"min_rho_inf": math.inf, "min_rho_block": math.inf, "min_max_over_rule1": math.inf, "at": None})
                d["min_rho_inf"] = min(d["min_rho_inf"], sc["rho_inf"])
                d["min_rho_block"] = min(d["min_rho_block"], sc["rho_block"])
                m = max(sc["rho_inf"] / t1, sc["rho_block"] / t2)
                if m < d["min_max_over_rule1"]:
                    d["min_max_over_rule1"], d["at"] = m, f"{a['problem']} {a['config_id']}"
        out[yp] = {"alternatives": per, "decoys": dec, "rule1_thresholds": [t1, t2]}
    return out


def load_alt(alt_dir: Path, stored: dict[tuple, dict[str, Any]], cpu_adm: dict[tuple, bool]) -> list[dict[str, Any]]:
    recs = []
    for f in sorted(glob.glob(str(alt_dir / "*.json"))):
        a = json.loads(Path(f).read_text())
        key = (a["problem"], a["config_id"])
        if key in cpu_adm:
            a["admissible"] = cpu_adm[key]
        else:
            st = stored.get((a["problem"], a["channel"], "/".join(a["config_id"].split("/")[:2]), int(a["config_id"].rsplit("seed-", 1)[1])))
            a["admissible"] = bool(st["admissible"]) if st and st.get("admissible") is not None else a["channel"] == "A1"
        recs.append(a)
    return recs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stored", default=str(HERE / "stored-characterisation.json"))
    ap.add_argument("--cpu", required=True)
    ap.add_argument("--alt", default=str(HERE / "alt"))
    ap.add_argument("--out", default=str(HERE / "results.json"))
    a = ap.parse_args()
    stored_doc = json.loads(Path(a.stored).read_text())
    # per draw: the stored reference realizations (inline rows first), admissibility
    stored: dict[tuple, dict[str, Any]] = {}
    for row in sorted(stored_doc["rows"], key=lambda x: (x["arm"] != "inline", x["job"])):
        key = (row["problem"], row["channel"], row["config"], row["seed"])
        st = stored.setdefault(key, {"realizations": [], "admissible_votes": []})
        real = (row["e_dev"], row["e_cpu"], row["e_tf32"], row["arm"], row["job"], row["device_used_tf32"])
        if real[:3] not in [x[:3] for x in st["realizations"]]:
            st["realizations"].append(real)
        if row["admissible"] is not None:
            st["admissible_votes"].append(bool(row["admissible"]))
    for st in stored.values():
        st["admissible"] = (sum(st["admissible_votes"]) * 2 >= len(st["admissible_votes"])) if st["admissible_votes"] else None
        st["e_dev"], st["e_cpu"], st["e_tf32"] = st["realizations"][0][:3]
        tf = sorted(x[2] for x in st["realizations"] if x[5])
        st["tf32_realizations_e"] = tf
        st["device_used_tf32"] = bool(tf)
        st["e_tf32_used"] = tf[len(tf) // 2] if tf else None
    recs = load_cpu(Path(a.cpu))
    for r in recs:
        r["admissible"] = admissible_cpu(r, stored)

    # 1. emulation validation -------------------------------------------------------------
    val_rows = []
    for r in recs:
        key = (r["problem"], r["channel"], "/".join(r["config_id"].split("/")[:2]), r["facts"]["seed"])
        st = stored.get(key)
        if st is None or st.get("e_tf32") is None:
            continue
        c = r["out"]["correct"]
        # compare with the stored realizations in which the device used TF32 (median if
        # several); a draw where no stored realization used TF32 is reported, not compared
        device_used_tf32 = st["device_used_tf32"]
        stored_e = st["e_tf32_used"] if device_used_tf32 else st["e_tf32"]
        other_realizations = [{"e_dev": x[0], "e_cpu": x[1], "e_tf32": x[2], "arm": x[3], "job": x[4], "device_used_tf32": x[5]} for x in st["realizations"]]
        bitwise_inputs = not any(t in r["config_id"] for t in ("randn", "constrows"))
        val_rows.append({
            "problem": r["problem"], "config": r["config_id"], "bitwise_inputs": bitwise_inputs,
            "device_used_tf32": device_used_tf32, "stored_tf32_realizations_e": st["tf32_realizations_e"],
            "stored_e_tf32": stored_e, "cpu_e_tf32_rne": c["tf32_rne"]["e_reg"], "cpu_e_tf32_rz": c["tf32_rz"]["e_reg"],
            "rne_over_stored": c["tf32_rne"]["e_reg"] / stored_e if stored_e else None,
            "stored_e_device": st["e_dev"], "stored_e_cpu_x86": st["e_cpu"], "cpu_e_fp32_arm": c["fp32"]["e_reg"],
            "fp32_arm_over_device": c["fp32"]["e_reg"] / st["e_dev"] if st["e_dev"] else None,
            "batch": r.get("batch"), "stored_realizations": other_realizations,
        })
    full = [v for v in val_rows if not v["batch"] or v["batch"]["evaluated"] == v["batch"]["full"]]
    used = [v["rne_over_stored"] for v in full if v["device_used_tf32"] and v["rne_over_stored"]]
    used_bw = [v["rne_over_stored"] for v in full if v["device_used_tf32"] and v["bitwise_inputs"] and v["rne_over_stored"]]
    subset = [v["rne_over_stored"] for v in val_rows if v not in full and v["device_used_tf32"] and v["rne_over_stored"]]
    fp = [v["fp32_arm_over_device"] for v in full if v["fp32_arm_over_device"]]

    def qs(xs: list[float]) -> dict[str, Any]:
        xs = sorted(xs)
        if not xs:
            return {"n": 0}
        return {"n": len(xs), "min": xs[0], "median": xs[len(xs) // 2], "max": xs[-1], "within_x1.5": sum(1 / 1.5 <= x <= 1.5 for x in xs), "within_x2": sum(0.5 <= x <= 2 for x in xs)}

    emulation = {
        "rows": val_rows,
        "rne_over_stored_tf32_where_device_used_tf32": qs(used),
        "same_but_bitwise_identical_inputs_only": qs(used_bw),
        "batch_subset_draws_rne_over_stored_full_batch": qs(subset),
        "cpu_fp32_over_stored_device_fp32": qs(fp),
        "device_did_not_use_tf32": sorted({(v["problem"], v["config"]) for v in val_rows if not v["device_used_tf32"]}),
    }

    # 2. characterisation (CPU conditioning joined to stored vacuity) ------------------------
    char = []
    for r in recs:
        key = (r["problem"], r["channel"], "/".join(r["config_id"].split("/")[:2]), r["facts"]["seed"])
        st = stored.get(key) or {}
        c, cond = r["out"]["correct"], r["conditioning"]
        T_pred = {
            "strict-fp32": max(MULT * c["fp32"]["e_reg"], T_FLOOR),
            "tf32-admissible(emulated cuBLAS/cuDNN RNE)": max(MULT * max(c["fp32"]["e_reg"], c["tf32_rne"]["e_reg"]), T_FLOOR),
        }
        char.append({
            "problem": r["problem"], "channel": r["channel"], "config": r["config_id"], "admissible": r["admissible"],
            "stored_reference_realizations": st.get("realizations"),
            "cpu_T_pred": T_pred,
            "cpu_pred_admits_zeros": {k: v >= E_ZEROS for k, v in T_pred.items()},
            "reduction_length": cond["reduction_length"], "numel": cond["numel"],
            "input_negative_fraction": cond["input_negative_fraction"],
            "operand_negative_fractions": cond["operand_negative_fractions"],
            "linear_cancellation_q": cond["linear_cancellation_q"],
            "G_inf_over_z_inf": cond["G_inf_over_z_inf"],
            "delta_t_inf_over_r_inf": cond["delta_t_inf_over_r_inf"],
            "delta_t_rms_over_r_rms": cond["delta_t_rms_over_r_rms"],
            "frac_r_below_kappa_rinf": cond["frac_r_below_kappa_rinf"],
            "reg_argmax_rne": cond["reg_argmax_rne"],
            "relative_l2_error": cond["relative_l2_error"],
            "chain_reproduces_module_max_abs": cond["chain_reproduces_module_max_abs"],
        })

    # 3. candidate metrics -------------------------------------------------------------------
    adm = [r for r in recs if r["admissible"]]
    cand = {"admissible_draws": eval_candidates(adm), "all_draws": eval_candidates(recs)}
    recommended = {"admissible_draws": recommended_rule(adm), "all_draws": recommended_rule(recs)}
    recommended_floor = {"admissible_draws": recommended_rule_floored(adm), "all_draws": recommended_rule_floored(recs)}
    informativeness = {"admissible_draws": held_out_informativeness(adm), "all_draws": held_out_informativeness(recs)}
    cpu_adm = {(r["problem"], r["config_id"]): bool(r["admissible"]) for r in recs}
    alt = load_alt(Path(a.alt), stored, cpu_adm)
    alt_adm = [x for x in alt if x["admissible"]]
    alt_res = {"records": len(alt), "admissible_records": len(alt_adm), "problems": dict(collections.Counter(x["problem"] for x in alt)),
               "summary": alt_summary(alt)}
    rule2_res = {"all_draws": rule2(recs, alt), "admissible_draws": rule2(adm, alt_adm)}
    # per-draw table of the main candidates (compact)
    table = []
    for r in adm:
        row = {"problem": r["problem"], "config": r["config_id"]}
        for policy in ("strict", "tf32_ext"):
            rt = ratios(r, policy)
            row[policy] = {
                m: {
                    "correct_max": max((v for n, v in rt[m]["correct"].items() if n in (CORRECT_UNDER[policy] if m == "M3_gauge" else HELD_OUT[policy] + YARDSTICKS[policy]) and math.isfinite(v)), default=None),
                    "zeros": rt[m]["destroyed"].get("zeros"),
                    "gain_1e-2": rt[m]["destroyed"].get("gain_1e-2"),
                    "single_max_zeroed": rt[m]["destroyed"].get("single_max_zeroed"),
                    "bias_sign": rt[m]["destroyed"].get("bias_sign"),
                    "drop_last_k": rt[m]["destroyed"].get("drop_last_k"),
                }
                for m in ("REG", "M1_l2", "M2_phi0.25", "M3_gauge")
            }
        table.append(row)

    # 4. restriction of the registered metric (stored inline rows): a draw row is determinate
    # only if the all-zeros output fails it with margin m (T * m < e(0) = 1/(1+kappa))
    restriction: dict[str, Any] = {}
    for arm_sel in ("inline", "all_arms"):
        for margin in (1.0, 4.0):
            per_problem: dict[str, Any] = {}
            for row in stored_doc["rows"]:
                if (arm_sel == "inline" and row["arm"] != "inline") or not row["admissible"] or row["tier"] != "tier1":
                    continue
                for pol, t in row["T"].items():
                    if t is None:
                        continue
                    c = per_problem.setdefault(row["problem"], {}).setdefault(pol, collections.Counter())
                    c[f"{row['channel']}_rows"] += 1
                    c[f"{row['channel']}_determinate"] += t * margin < E_ZEROS
            restriction[f"{arm_sel}_zeros_margin_{margin:g}"] = {p: {pol: dict(c) for pol, c in v.items()} for p, v in sorted(per_problem.items())}
    result = {
        "schema": "q1-audit-metric-study/results/2",
        "inputs": {"stored": Path(a.stored).name, "cpu_records": len(recs), "cpu_admissible_records": len(adm),
                   "problems": sorted({r["problem"] for r in recs}),
                   "records_per_problem": dict(collections.Counter(r["problem"] for r in recs))},
        "emulation_validation": emulation,
        "characterisation": char,
        "candidates": cand,
        "recommended_rule": recommended,
        "recommended_rule_with_floor": recommended_floor,
        "held_out_informativeness": informativeness,
        "alt_algorithms": alt_res,
        "rule2": rule2_res,
        "per_draw_table": table,
        "restriction": restriction,
    }
    Path(a.out).write_text(json.dumps(result, indent=1, sort_keys=True, default=lambda o: None))
    # console summary
    print("records", len(recs), "admissible", len(adm))
    for subset, rr in recommended.items():
        for policy, x in rr.items():
            print("RECOMMENDED", subset, policy, x["thetas"], "draws", x["draws"], "indeterminate", x["indeterminate"], "FR", x["false_rejects"], "escapes", x["escapes_by_class"], "of", x["cases_by_class"])
    for subset, rr in recommended_floor.items():
        for policy, x in rr.items():
            print("RULE1+FLOOR", subset, policy, "indeterminate", x["indeterminate"], "FR", x["false_rejects"], "escapes", x["escapes_by_class"], "floor binds on", len(x["draws_where_floor_binds"]))
    print("emulation rne/stored", emulation["rne_over_stored_tf32_where_device_used_tf32"])
    print("emulation batch-subset", emulation["batch_subset_draws_rne_over_stored_full_batch"])
    for pol, v in informativeness["admissible_draws"].items():
        print("held-out informativeness", pol, {n: (d["cases"], d["identical_to_a_yardstick_member"]) for n, d in v.items()})
    for subset, rr in rule2_res.items():
        for name, x in rr.items():
            print("RULE2", subset, name, "cpu draws", x["cpu_draws"], "indet", len(x["cpu_indeterminate"]), "correct", x["correct"], "| destroyed", x["destroyed"],
                  "| battery min reject score %.2f" % x["battery_min_reject_score"], "| alt draws", x["alt_draws"], "indet", len(x["alt_indeterminate"]), "alt correct", x["alt_correct"])
    for subset, cs in cand.items():
        print("==", subset)
        for policy, pol in cs.items():
            reg = pol["REG_as_registered"]
            print(policy.ljust(9), "REG as registered".ljust(15), "escapes", reg["escapes_by_class"], "of", reg["cases_by_class"], "| held-out correct FR", len(reg["held_out_correct_false_rejects"]), "/", reg["held_out_correct_cases"])
            if "M1_linf_or_M2_phi1" in pol:
                c = pol["M1_linf_or_M2_phi1"]
                print(policy.ljust(9), "M1_linf|M2_phi1", "thetas", c["thetas"], "| correct FR", c["correct_false_rejects"], "| escapes", c["escapes_by_class"], "of", c["cases_by_class"])
            for m in METRICS:
                if m not in pol:
                    continue
                d = pol[m]
                x = d["at_theta"]
                print(policy.ljust(9), m.ljust(15), "theta", "%-6.3g" % d["theta"], "worst correct %.3g (%s %s %s)" % (d["worst_correct"]["value"], d["worst_correct"]["problem"], d["worst_correct"]["config"][:18], d["worst_correct"]["realization"]),
                      "| escapes size>=4x", x["escapes_size_ge_4x_by_class"], "| gross min margin %.3g" % x["gross_min_margin"], "| LOPO FR", d["lopo_false_reject_problems"], "| indet", d["determinacy_gate_4theta"]["indeterminate"], "/", d["determinacy_gate_4theta"]["draws"])


if __name__ == "__main__":
    main()
