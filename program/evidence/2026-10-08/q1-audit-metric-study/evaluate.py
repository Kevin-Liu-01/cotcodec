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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stored", default=str(HERE / "stored-characterisation.json"))
    ap.add_argument("--cpu", required=True)
    ap.add_argument("--out", default=str(HERE / "results.json"))
    a = ap.parse_args()
    stored_doc = json.loads(Path(a.stored).read_text())
    # per draw: the stored reference realizations (inline rows first), admissibility
    stored: dict[tuple, dict[str, Any]] = {}
    for row in sorted(stored_doc["rows"], key=lambda x: (x["arm"] != "inline", x["job"])):
        key = (row["problem"], row["channel"], row["config"], row["seed"])
        st = stored.setdefault(key, {"realizations": [], "admissible_votes": []})
        real = (row["e_dev"], row["e_cpu"], row["e_tf32"], row["arm"], row["job"])
        if real[:3] not in [x[:3] for x in st["realizations"]]:
            st["realizations"].append(real)
        if row["admissible"] is not None:
            st["admissible_votes"].append(bool(row["admissible"]))
    for st in stored.values():
        st["admissible"] = (sum(st["admissible_votes"]) * 2 >= len(st["admissible_votes"])) if st["admissible_votes"] else None
        st["e_dev"], st["e_cpu"], st["e_tf32"] = st["realizations"][0][:3]
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
        device_used_tf32 = st["e_tf32"] != st["e_dev"]
        other_realizations = [{"e_dev": x[0], "e_cpu": x[1], "e_tf32": x[2], "arm": x[3], "job": x[4]} for x in st["realizations"][1:]]
        bitwise_inputs = not any(t in r["config_id"] for t in ("randn", "constrows"))
        val_rows.append({
            "problem": r["problem"], "config": r["config_id"], "bitwise_inputs": bitwise_inputs,
            "device_used_tf32": device_used_tf32,
            "stored_e_tf32": st["e_tf32"], "cpu_e_tf32_rne": c["tf32_rne"]["e_reg"], "cpu_e_tf32_rz": c["tf32_rz"]["e_reg"],
            "rne_over_stored": c["tf32_rne"]["e_reg"] / st["e_tf32"] if st["e_tf32"] else None,
            "stored_e_device": st["e_dev"], "stored_e_cpu_x86": st["e_cpu"], "cpu_e_fp32_arm": c["fp32"]["e_reg"],
            "fp32_arm_over_device": c["fp32"]["e_reg"] / st["e_dev"] if st["e_dev"] else None,
            "batch": r.get("batch"), "other_stored_realizations": other_realizations,
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
    for margin in (1.0, 4.0):
        per_problem: dict[str, Any] = {}
        for row in stored_doc["rows"]:
            if row["arm"] != "inline" or not row["admissible"] or row["tier"] != "tier1":
                continue
            for pol, t in row["T"].items():
                if t is None:
                    continue
                c = per_problem.setdefault(row["problem"], {}).setdefault(pol, collections.Counter())
                c[f"{row['channel']}_rows"] += 1
                c[f"{row['channel']}_determinate"] += t * margin < E_ZEROS
        restriction[f"zeros_margin_{margin:g}"] = {p: {pol: dict(c) for pol, c in v.items()} for p, v in sorted(per_problem.items())}
    result = {
        "schema": "q1-audit-metric-study/results/1",
        "inputs": {"stored": Path(a.stored).name, "cpu_records": len(recs), "cpu_admissible_records": len(adm),
                   "problems": sorted({r["problem"] for r in recs}),
                   "records_per_problem": dict(collections.Counter(r["problem"] for r in recs))},
        "emulation_validation": emulation,
        "characterisation": char,
        "candidates": cand,
        "recommended_rule": recommended,
        "per_draw_table": table,
        "restriction": restriction,
    }
    Path(a.out).write_text(json.dumps(result, indent=1, sort_keys=True, default=lambda o: None))
    # console summary
    print("records", len(recs), "admissible", len(adm))
    for subset, rr in recommended.items():
        for policy, x in rr.items():
            print("RECOMMENDED", subset, policy, x["thetas"], "draws", x["draws"], "indeterminate", x["indeterminate"], "FR", x["false_rejects"], "escapes", x["escapes_by_class"], "of", x["cases_by_class"])
    print("emulation rne/stored", emulation["rne_over_stored_tf32_where_device_used_tf32"])
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
