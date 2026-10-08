"""Q1 audit-metric study (D41 ii), part 1: F1 characterised from stored journals only.

Reads the stored audit journals of Q1 jobs 474, 518, 548, 713 and 752 (byte copies
of the host files; SHA-256 recorded), applies the D28 filter, and for every
admissible A1-A3 draw that survives reports the registered metric's ingredients
and verdicts under both TF32 policies:

* the reference errors that set T (``e_r32_device``, ``e_r32_cpu``,
  ``e_r32_tf32``) and T itself;
* the analytic scores of destroyed outputs under the registered metric
  ``e(x) = max_i |x_i - r_i| / (|r_i| + kappa ||r||_inf)``: for any finite, nonzero
  reference, ``e(0) = 1 / (1 + kappa)`` and ``e(-r) = 2 / (1 + kappa)`` exactly
  (attained at the largest |r_i|), so a draw *admits zeros* when T >= 1/(1+kappa)
  and *admits negation* when T >= 2/(1+kappa);
* the stored scores of correct kernels (S1 substrates, reference-identity
  controls) and of every stored mutant and adversarial control;
* per problem and policy: whether the audit (A1, A2, A3 together, as tiers N and
  G conjoin them) can reject an all-zeros or a negated output at all.

D28 filter (hard rule). A row is kept only if its problem is in the S1 calibration
half, its kernel is not an evaluation unit, and its problem hosts no S2 substrate,
so no evaluation unit of any tier lives on it ("tier 1"). Revision 2 drops the
first pass's tier 2 (job 752's KernelBench adversarial controls on L1/1): L1/1
hosts the FlagGems mm evaluation substrate, its stored draw thresholds are the ones
that would judge that unit, and the first pass already dropped L1/95's identity
control on the same ground. Every dropped row is counted with its reason.

Revision 2 also reports (both reviews of the first pass): determinacy per stored
reference realization across both arms and every job, not per draw from the inline
arm alone; strict-fp32 false rejects as distinct kernel-draws; every arm's mutant
rows; the correct-versus-zeros separation over all correct kernels and arms; which
correct-kernel rows equal a yardstick member bitwise; and the fp32 correct kernels'
error over the deployment strict yardstick (device fp32, x86 CPU fp32).

Usage: python stored_characterisation.py --journals <dir with j474/ j518/ j548/ j713/ j752/>
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO))

from harness.q1 import analysis  # noqa: E402
from harness.q1.substrates import s2_catalog  # noqa: E402

KAPPA = 1e-3
E_ZEROS = 1.0 / (1.0 + KAPPA)
E_NEG = 2.0 / (1.0 + KAPPA)
MULTIPLIER = 16
POLICIES = ("tf32-admissible", "strict-fp32")
JOURNALS = {
    "474/smoke": ("j474/smoke-journal.jsonl", "~/cotcodec-runs/stage0/q1-gates/pilot/runs/474/q1/smoke/journal.jsonl"),
    "518/smoke": ("j518/smoke-journal.jsonl", "~/cotcodec-runs/stage0/q1-gates/pilot/runs/518/q1/smoke/journal.jsonl"),
    "518/calibration": ("j518/calibration-journal.jsonl", "~/cotcodec-runs/stage0/q1-gates/pilot/runs/518/q1/calibration/journal.jsonl"),
    "518/scoring": ("j518/scoring-journal.jsonl", "~/cotcodec-runs/stage0/q1-gates/pilot/runs/518/q1/scoring/journal.jsonl"),
    "548/scoring": ("j548/scoring-journal.jsonl", "~/cotcodec-runs/stage0/q1-gates/pilot/runs/548/q1/scoring/journal.jsonl"),
    "713/repilot": ("j713/journal.jsonl", "~/cotcodec-runs/stage0/q1-engineering-d31/runs/713/q1/repilot/journal.jsonl"),
    "752/validation": ("j752/journal.jsonl", "~/cotcodec-runs/stage0/q1-exec2-validation/runs/752/q1/validation/journal.jsonl"),
}
#: op class of each problem (from the problem source; the TF32 switch applies to all)
OP_CLASS = {
    "L1/10": "matmul (3D x 2D)",
    "L1/18": "matmul (transposed)",
    "L1/15": "matmul + tril",
    "L1/47": "sum reduction (no matmul)",
    "L1/1": "matmul (square)",
    "L2/59": "linear + swish + scale",
    "L2/95": "linear + add + swish + tanh + gelu + hardtanh",
    "L2/77": "conv_transpose3d + scale + batchnorm(train) + global avg pool",
    "L2/100": "conv_transpose3d + clamp + divide",
    "L2/87": "conv2d (Cin 8) + subtract x2 + mish",
    "L2/46": "conv2d + subtract + tanh + subtract + avgpool",
    "L2/52": "conv2d + softplus-tanh gate + batchnorm(train)",
    "L2/60": "conv_transpose3d + swish + groupnorm + hardswish",
}


def short(problem_id: str) -> str:
    return problem_id.split("_")[0]


def problem_of(kernel_id: str) -> str:
    m = re.search(r"(L[12])-(\d+)", kernel_id)
    return f"{m.group(1)}/{m.group(2)}"


def kind_of(kernel_id: str) -> str:
    k = kernel_id.removesuffix(".store").removesuffix(".inline")
    if k.startswith("ctl-identity"):
        return "identity"
    if k.startswith("ctl-kernelbench"):
        return "adversarial-control"
    if ".hack." in k:
        return "hack-control"
    if re.search(r"\.[a-z0-9-]+\.L\d+C\d+$", k):
        return "mutant"
    if k.startswith("s2-"):
        return "s2-substrate"
    return "substrate"


def arm_of(kernel_id: str, job: str) -> str:
    if kernel_id.endswith(".store"):
        return "store"
    if kernel_id.endswith(".inline"):
        return "inline"
    # job 752 ran the re-pilot kernels through the store only; adversarial controls
    # have a ".inline" twin and their bare id is the store arm
    if job.startswith("752"):
        return "store"
    return "inline"


def frame() -> dict[str, Any]:
    split = analysis.s1_split()
    cal = {short(p): p for p in split["calibration"]}
    ev = {short(p): p for p in split["evaluation"]}
    s2 = {short(e.problem_id) for e in s2_catalog.CATALOG}
    exposed = json.loads((REPO / "harness/q1/data/pilot_exposed.json").read_text())
    eval_kernels = {e["kernel_id"] for e in exposed["evaluation_substrates"]}
    eval_kernels |= {m["kernel_id"] for m in exposed["mutants"] if m.get("parent") in eval_kernels}
    return {"cal": cal, "eval": ev, "s2": s2, "eval_kernels": eval_kernels, "split_sha256": split["sha256"]}


def classify(row: dict[str, Any], job: str, fr: dict[str, Any]) -> tuple[str, str]:
    kid = row["kernel_id"]
    base = kid.removesuffix(".store").removesuffix(".inline")
    p = problem_of(kid)
    kind = kind_of(kid)
    if p in fr["eval"]:
        return "drop", f"problem {p} is in S1-eval"
    if p not in fr["cal"]:
        return "drop", f"problem {p} not in the S1 split"
    if base in fr["eval_kernels"] or kind == "s2-substrate":
        return "drop", "evaluation unit (pilot_exposed evaluation substrate or its mutant, or an S2 substrate)"
    if p in fr["s2"]:
        return "drop", f"S1-cal problem {p} hosts an S2 evaluation substrate; all rows dropped"
    return "tier1", "S1-cal problem without an S2 substrate"


def threshold_parts(d: dict[str, Any]) -> dict[str, Any]:
    e_dev, e_cpu, e_tf32 = d.get("e_r32_device"), d.get("e_r32_cpu"), d.get("e_r32_tf32")
    strict_E = max(e for e in (e_dev, e_cpu) if e is not None and math.isfinite(e))
    setter = "tf32" if (d.get("tf32-admissible") or {}).get("tf32_applied") and e_tf32 is not None and e_tf32 > strict_E else ("device" if (e_dev or 0) >= (e_cpu or 0) else "cpu")
    return {"e_dev": e_dev, "e_cpu": e_cpu, "e_tf32": e_tf32, "strict_E": strict_E, "tf32_setter": setter}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--journals", required=True)
    ap.add_argument("--out", default=str(HERE / "stored-characterisation.json"))
    a = ap.parse_args()
    root = Path(a.journals)
    fr = frame()
    inputs, kept, dropped = {}, collections.Counter(), collections.Counter()
    drop_reasons = collections.Counter()
    rows: list[dict[str, Any]] = []
    other_rows: list[dict[str, Any]] = []
    for job, (rel, host) in JOURNALS.items():
        raw = (root / rel).read_bytes()
        inputs[job] = {"host_path": host, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
        for line in raw.decode().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            tier, why = classify(row, job, fr)
            if tier == "drop":
                dropped[job] += 1
                drop_reasons[f"{job}: {why}"] += 1
                continue
            kept[(job, tier)] += 1
            gate = row["gate"]
            if gate not in ("A1", "A2", "A3"):
                other_rows.append({"job": job, "tier": tier, "kernel_id": row["kernel_id"], "gate": gate, "config_id": row["config_id"], "verdict": row["verdict"], "tf32_policy": row.get("tf32_policy")})
                continue
            d = row.get("details") or {}
            cfg = row["config_id"]
            if "aggregate" in cfg:
                other_rows.append({"job": job, "tier": tier, "kernel_id": row["kernel_id"], "gate": gate, "config_id": cfg, "verdict": row["verdict"], "tf32_policy": row.get("tf32_policy"), "counts": d.get("counts")})
                continue
            if "e_r32_device" not in d:
                other_rows.append({"job": job, "tier": tier, "kernel_id": row["kernel_id"], "gate": gate, "config_id": cfg, "verdict": row["verdict"], "reason": (d.get("reason") or d.get("validity_reasons") or "")})
                continue
            p = problem_of(row["kernel_id"])
            ta, st = d.get("tf32-admissible") or {}, d.get("strict-fp32") or {}
            rows.append({
                "problem": p, "op_class": OP_CLASS.get(p), "channel": gate, "config": cfg.split("/seed")[0],
                "seed": d.get("seed"), "tier": tier, "job": job, "kernel_id": row["kernel_id"],
                "kind": kind_of(row["kernel_id"]), "arm": arm_of(row["kernel_id"], job), "attempt": row.get("attempt"),
                "base_kernel": row["kernel_id"].removesuffix(".store").removesuffix(".inline"),
                "item_final": d.get("item_final") is not False, "infra_failure_kind": d.get("infra_failure_kind"),
                "admissible": d.get("admissible"), "validity_reasons": d.get("validity_reasons") or [],
                "matmul_or_conv": d.get("matmul_or_conv"), "outcome": d.get("outcome"), "verdict_primary": row["verdict"],
                **threshold_parts(d),
                "T": {"tf32-admissible": ta.get("T"), "strict-fp32": st.get("T")},
                "e": {"tf32-admissible": ta.get("e"), "strict-fp32": st.get("e")},
                "passed": {"tf32-admissible": ta.get("passed"), "strict-fp32": st.get("passed")},
            })
    # per row: the analytic destroyed outputs against that row's own threshold
    for r in rows:
        r["admits_zeros"] = {pol: (t is not None and t >= E_ZEROS) for pol, t in r["T"].items()}
        r["admits_negation"] = {pol: (t is not None and t >= E_NEG) for pol, t in r["T"].items()}
        # the device used TF32 in this realization if its TF32-policy reference is at least
        # twice as far from the oracle as both fp32 references (TF32 error is ~2^13 times fp32's;
        # a non-TF32 cuDNN algorithm can differ from the fp32 run in the last bits only)
        r["device_used_tf32"] = r["e_tf32"] is not None and r["e_tf32"] >= 2 * max(x for x in (r["e_dev"], r["e_cpu"]) if x is not None)
    # per draw: every stored reference realization (each row carries its own reference
    # errors and T; cuDNN's algorithm and TF32 use are chosen per process, so one draw can
    # be determinate in one realization and vacuous in another)
    draws: dict[tuple, dict[str, Any]] = {}
    for r in rows:
        key = (r["problem"], r["channel"], r["config"], r["seed"])
        dr = draws.setdefault(key, {"problem": r["problem"], "op_class": r["op_class"], "channel": r["channel"], "config": r["config"], "seed": r["seed"], "tier": r["tier"], "rows": 0, "admissible_rows": 0, "realizations": {}, "T": {pol: [] for pol in POLICIES}, "T_inline": {pol: [] for pol in POLICIES}, "admissible_votes": []})
        dr["rows"] += 1
        if r["admissible"] is not None:
            dr["admissible_votes"].append(bool(r["admissible"]))
        real = dr["realizations"].setdefault((r["e_dev"], r["e_cpu"], r["e_tf32"]), {
            "e_dev": r["e_dev"], "e_cpu": r["e_cpu"], "e_tf32": r["e_tf32"], "device_used_tf32": r["device_used_tf32"],
            "T": {pol: r["T"][pol] for pol in POLICIES}, "rows": []})
        real["rows"].append(f"{r['job']} {r['arm']} {r['kind']}{'' if r['item_final'] else ' non-final'}")
        for pol in POLICIES:
            if real["T"][pol] is None and r["T"][pol] is not None:
                real["T"][pol] = r["T"][pol]
        if r["admissible"]:
            dr["admissible_rows"] += 1
            for pol in POLICIES:
                t = r["T"][pol]
                if t is not None:
                    dr["T"][pol].append(t)
                    if r["arm"] == "inline":
                        dr["T_inline"][pol].append(t)
    for dr in draws.values():
        reals = list(dr.pop("realizations").values())
        dr["reference_realizations"] = len(reals)
        dr["realizations"] = reals
        votes = dr.pop("admissible_votes")
        dr["admissible"] = (sum(votes) * 2 >= len(votes)) if votes else None
        for which in ("T", "T_inline"):
            dr[which] = {pol: ([min(v), max(v)] if v else None) for pol, v in dr[which].items()}
        dr["nondeterministic_T"] = {pol: bool(v and v[1] > 1.5 * v[0]) for pol, v in dr["T"].items()}
        dr["inline_admits_zeros_every_row"] = {pol: (v is not None and v[0] >= E_ZEROS) for pol, v in dr["T_inline"].items()}
        dr["inline_admits_negation_every_row"] = {pol: (v is not None and v[0] >= E_NEG) for pol, v in dr["T_inline"].items()}
        ts = {pol: [x["T"][pol] for x in reals if x["T"][pol] is not None] for pol in POLICIES}
        dr["zeros_rejectable"] = {
            pol: ("no T" if not v else "every realization" if max(v) < E_ZEROS else "some realizations" if min(v) < E_ZEROS else "none")
            for pol, v in ts.items()
        }
        dr["device_used_tf32_realizations"] = [x["device_used_tf32"] for x in reals]
    # per problem and policy: admissible draws by whether some or every stored realization
    # can reject zeros (all arms and jobs; the first pass read the inline arm only)
    determinacy: dict[str, Any] = {}
    for dr in draws.values():
        if not dr["admissible"]:
            continue
        for pol in POLICIES:
            c = determinacy.setdefault(dr["problem"], {}).setdefault(pol, {"draws": 0, "every_realization": [], "some_realizations": [], "none": []})
            z = dr["zeros_rejectable"][pol]
            if z == "no T":
                continue
            c["draws"] += 1
            c[z.replace(" ", "_")].append(f"{dr['config']} T={','.join('%.3g' % x['T'][pol] for x in dr['realizations'] if x['T'][pol] is not None)}")
    # per problem and policy, inline arm and every arm (rows)
    problems: dict[str, Any] = {}
    for arm_sel in ("inline", "all"):
        for pol in POLICIES:
            per = collections.defaultdict(lambda: {"admissible_rows": 0, "rows_admitting_zeros": 0, "rows_admitting_negation": 0, "T": [], "channels": collections.defaultdict(lambda: {"rows": 0, "admit_zeros": 0, "admit_negation": 0, "T": [], "rejecting_rows": []})})
            for r in rows:
                if not r["admissible"] or r["T"][pol] is None or (arm_sel == "inline" and r["arm"] != "inline"):
                    continue
                t = r["T"][pol]
                pp = per[r["problem"]]
                pp["admissible_rows"] += 1
                pp["rows_admitting_zeros"] += t >= E_ZEROS
                pp["rows_admitting_negation"] += t >= E_NEG
                pp["T"].append(t)
                ch = pp["channels"][r["channel"]]
                ch["rows"] += 1
                ch["admit_zeros"] += t >= E_ZEROS
                ch["admit_negation"] += t >= E_NEG
                ch["T"].append(t)
                if t < E_ZEROS:
                    ch["rejecting_rows"].append(f"{r['config']} {r['kind']} {r['job']} {r['arm']}{'' if r['item_final'] else ' non-final'} T={t:.3g}")
            for p, pp in per.items():
                chans = {}
                for c, ch in pp["channels"].items():
                    chans[c] = {"rows": ch["rows"], "admit_zeros": ch["admit_zeros"], "admit_negation": ch["admit_negation"],
                                "T_range": [min(ch["T"]), max(ch["T"])], "zeros_rejected_on": sorted(set(ch["rejecting_rows"]))}
                problems.setdefault(p, {"op_class": OP_CLASS.get(p), "tier": None, "by_arm": {}})
                problems[p]["by_arm"].setdefault(arm_sel, {})[pol] = {
                    "admissible_rows": pp["admissible_rows"], "rows_admitting_zeros": pp["rows_admitting_zeros"],
                    "rows_admitting_negation": pp["rows_admitting_negation"], "T_range": [min(pp["T"]), max(pp["T"])],
                    "channels": chans,
                    "zeros_rejected_somewhere": pp["rows_admitting_zeros"] < pp["admissible_rows"],
                    "A1_rejects_zeros_somewhere": "A1" in chans and chans["A1"]["admit_zeros"] < chans["A1"]["rows"],
                }
    for r in rows:
        if r["problem"] in problems:
            problems[r["problem"]]["tier"] = r["tier"]
            problems[r["problem"]]["determinacy_by_realization"] = determinacy.get(r["problem"])
    # stored mutant rows, every arm
    witnesses = [
        {k: r[k] for k in ("problem", "channel", "config", "seed", "admissible", "kernel_id", "base_kernel", "kind", "arm", "job", "item_final", "outcome", "e", "T", "passed")}
        | {"e_is_zeros_like": r["e"]["tf32-admissible"] is not None and abs(r["e"]["tf32-admissible"] - E_ZEROS) < 2e-3}
        for r in sorted(rows, key=lambda x: (x["problem"], x["channel"], x["config"], x["kernel_id"]))
        if r["kind"] in ("mutant", "adversarial-control")
    ]
    mutants: dict[str, Any] = {}
    for w in witnesses:
        m = mutants.setdefault(w["base_kernel"], {"problem": w["problem"], "admissible_numeric_rows": 0, "by_arm": {}, "zeros_like_passes": [], "passes_with_e_ge_0.5": []})
        t, e = w["T"]["tf32-admissible"], w["e"]["tf32-admissible"]
        if w["admissible"] and t is not None:
            m["admissible_numeric_rows"] += 1
        arm_counts = m["by_arm"].setdefault(w["arm"], collections.Counter())
        arm_counts[f"{w['outcome']}{'' if w['admissible'] else ' (inadmissible)'}"] += 1
        tag = f"{w['config']} seed {w['seed']} {w['arm']} {w['job']}: e={e if e is None else '%.4g' % e} T={t if t is None else '%.3g' % t}"
        if w["admissible"] and w["passed"]["tf32-admissible"] and w["e_is_zeros_like"]:
            m["zeros_like_passes"].append(tag)
        if w["admissible"] and w["passed"]["tf32-admissible"] and e is not None and e >= 0.5:
            m["passes_with_e_ge_0.5"].append(tag)
    for m in mutants.values():
        m["by_arm"] = {k: dict(v) for k, v in m["by_arm"].items()}
    # correct kernels (S1 substrates, identity controls)
    def member_match(r: dict[str, Any]) -> str:
        e = r["e"]["strict-fp32"] if r["e"]["strict-fp32"] is not None else r["e"]["tf32-admissible"]
        mem = [x for x in (r["e_dev"], r["e_cpu"], r["e_tf32"]) if x is not None]
        if e is None or not mem:
            return "no e"
        if e in mem:
            return "bitwise equal to a yardstick member"
        if any(abs(e - m_) <= 1e-3 * m_ for m_ in mem):
            return "within 0.1% of a yardstick member"
        return "differs"
    correct = [
        {k: r[k] for k in ("problem", "channel", "config", "seed", "admissible", "kernel_id", "base_kernel", "kind", "arm", "job", "item_final", "outcome", "e_dev", "e_cpu", "e_tf32", "device_used_tf32")}
        | {"e_over_T": {pol: (r["e"][pol] / r["T"][pol]) if r["e"][pol] is not None and r["T"][pol] else None for pol in POLICIES},
           "e_equals_e_tf32": r["e"]["tf32-admissible"] is not None and r["e_tf32"] is not None and r["e"]["tf32-admissible"] == r["e_tf32"],
           "e_tf32_policy": r["e"]["tf32-admissible"],
           "yardstick_match": member_match(r)}
        for r in rows if r["kind"] in ("substrate", "identity")
    ]
    match_counts = collections.Counter((c["kind"], c["yardstick_match"]) for c in correct if c["e_tf32_policy"] is not None)
    strict_false_rejects = [c for c in correct if c["admissible"] and c["e_over_T"]["strict-fp32"] is not None and c["e_over_T"]["strict-fp32"] > 1]
    def kd(c: dict[str, Any]) -> tuple:
        return (c["base_kernel"], c["problem"], c["config"], c["seed"])
    strict_fr_summary = {
        "rows": len(strict_false_rejects),
        "distinct_kernel_draws": len({kd(c) for c in strict_false_rejects}),
        "distinct_kernel_draws_inline_arm": len({kd(c) for c in strict_false_rejects if c["arm"] == "inline"}),
        "by_problem_distinct": dict(collections.Counter(p for p, *_ in {(c["problem"], *kd(c)) for c in strict_false_rejects})),
        "note": "a kernel-draw scored by both arms, or by jobs 713 and 752, is one kernel-draw",
    }
    # fp32 correct kernels against the deployment strict yardstick (device fp32, x86 CPU fp32):
    # rows whose error is not TF32-sized and not a yardstick member
    deploy = []
    for c in correct:
        e = c["e_tf32_policy"]
        if e is None or not c["admissible"] or c["yardstick_match"] != "differs":
            continue
        strict_e = max(x for x in (c["e_dev"], c["e_cpu"]) if x is not None)
        if c["device_used_tf32"] and e >= 0.25 * c["e_tf32"]:
            continue  # the kernel itself ran in TF32 (cuDNN default): a strict-fp32 false reject, counted above
        if strict_e <= 0:
            continue
        deploy.append({"problem": c["problem"], "config": c["config"], "seed": c["seed"], "kind": c["kind"], "arm": c["arm"], "job": c["job"],
                       "e": e, "e_dev": c["e_dev"], "e_cpu_x86": c["e_cpu"], "e_over_strict_yardstick": e / strict_e,
                       "e_over_T_strict": c["e_over_T"]["strict-fp32"]})
    deploy.sort(key=lambda x: -x["e_over_strict_yardstick"])
    # separation of correct kernels from zeros under the registered metric (same draw),
    # all correct kernels and arms, one entry per kernel-draw
    sep_all: dict[tuple, dict[str, Any]] = {}
    for c in correct:
        e = c["e_tf32_policy"]
        if c["admissible"] and e:
            k = (c["problem"], c["config"], c["seed"], c["kind"])
            cur = sep_all.get(k)
            if cur is None or e > cur["e_correct"]:
                sep_all[k] = {"problem": c["problem"], "config": c["config"], "seed": c["seed"], "kind": c["kind"], "arm": c["arm"], "job": c["job"], "e_correct": e, "e_zeros_over_e_correct": E_ZEROS / e}
    sep = sorted(sep_all.values(), key=lambda x: x["e_zeros_over_e_correct"])
    # registered calibration rule on the stored S1-cal substrates (A1, primary policy), every arm
    calib = {}
    for r in rows:
        if r["channel"] != "A1" or r["kind"] != "substrate":
            continue
        e, t = r["e"]["tf32-admissible"], r["T"]["tf32-admissible"]
        if e is None or t is None:
            continue
        E = t / MULTIPLIER
        req = 0.0 if e <= 2**-20 else (e / E if E > 0 else math.inf)
        c = calib.setdefault(r["problem"], {"required_multiplier": 0.0, "rows": 0})
        c["required_multiplier"] = max(c["required_multiplier"], req)
        c["rows"] += 1
    result = {
        "schema": "q1-audit-metric-study/stored/2",
        "inputs": inputs,
        "d28_filter": {
            "rule": "keep a row only if its problem is S1-cal, hosts no S2 substrate, and its kernel is not an evaluation unit (tier1); every other row is dropped, including job 752's adversarial controls on L1/1 (L1/1 hosts the FlagGems mm evaluation substrate)",
            "split_sha256": fr["split_sha256"],
            "kept_rows": {f"{j}/{t}": n for (j, t), n in sorted(kept.items())},
            "kept_total": sum(kept.values()),
            "dropped_rows": dict(sorted(dropped.items())),
            "dropped_total": sum(dropped.values()),
            "dropped_reasons": dict(sorted(drop_reasons.items())),
        },
        "constants": {"kappa": KAPPA, "e_zeros": E_ZEROS, "e_negation": E_NEG, "multiplier": MULTIPLIER},
        "problems": problems,
        "draws": sorted(draws.values(), key=lambda r: (r["tier"], r["problem"], r["channel"], r["config"])),
        "rows": rows,
        "mutant_and_control_rows": witnesses,
        "mutants": mutants,
        "correct_kernel_rows": correct,
        "correct_kernel_yardstick_match": {f"{k} / {m}": n for (k, m), n in sorted(match_counts.items())},
        "strict_policy_false_rejects_of_correct_kernels": strict_false_rejects,
        "strict_policy_false_rejects_summary": strict_fr_summary,
        "fp32_correct_kernels_over_deployment_strict_yardstick": deploy,
        "registered_metric_separation_correct_vs_zeros": sep[:15],
        "calibration_required_multiplier_A1": calib,
        "non_numeric_rows": other_rows,
    }
    Path(a.out).write_text(json.dumps(result, indent=1, sort_keys=True, default=lambda o: None if (isinstance(o, float) and not math.isfinite(o)) else o))
    print(json.dumps({k: v for k, v in result["d28_filter"].items() if k != "dropped_reasons"}, indent=1))
    for p in sorted(problems):
        for pol in POLICIES:
            dd = (problems[p].get("determinacy_by_realization") or {}).get(pol)
            pp = problems[p]["by_arm"].get("all", {}).get(pol)
            if pp and dd:
                print(p, pol[:6], "adm rows (all arms)", pp["admissible_rows"], "admit zeros", pp["rows_admitting_zeros"], "negation", pp["rows_admitting_negation"],
                      "T %.3g-%.3g" % tuple(pp["T_range"]), "| adm draws", dd["draws"], "zeros rejectable: every realization", [x.split()[0] for x in dd["every_realization"]],
                      "some", [x.split()[0] for x in dd["some_realizations"]])
    print("closest correct-vs-zeros separations:", [(x["problem"], x["config"], x["kind"], round(x["e_zeros_over_e_correct"], 2)) for x in sep[:6]])
    print("strict false rejects of correct kernels:", strict_fr_summary)
    print("correct-kernel rows vs yardstick members:", dict(match_counts))
    print("fp32 correct kernels over the deployment strict yardstick (max 6):", [(x["problem"], x["config"], x["arm"], round(x["e_over_strict_yardstick"], 2)) for x in deploy[:6]])
    for k, m in mutants.items():
        print("mutant", k.split(".", 1)[1] if "." in k else k, m["problem"], "admissible numeric rows", m["admissible_numeric_rows"], m["by_arm"], "zeros-like passes", m["zeros_like_passes"])


if __name__ == "__main__":
    main()
