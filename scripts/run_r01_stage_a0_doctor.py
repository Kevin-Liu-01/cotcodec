#!/usr/bin/env python3
"""R01 Stage A0 doctor: the records-only census of S1a's greedy rerun disagreement.

CPU only, standard library only, model-free. It reads two committed files, checks their
SHA-256 against the values pinned below, and recomputes the census that the draft
registration ``program/preregistrations/r01-rerun-noise-sources-v1.md`` (section A0) names:

* A0.1 step-1 input identity of rerun pairs (processed screenshot, request digest);
* A0.2 natural replays: within-session pairs whose step-k requests are byte-identical and
  whose earlier steps were identical; how often the greedy reply text and the parsed IR differ
  under S1a's serving (batched, prefix cache on, V = 20);
* A0.3 step-1 reply and IR divergence with identical against different step-1 inputs;
* A0.4 per-step survival of identical requests, replies and IR, and the label of the first
  reply-text divergence (identical input: "serving"; different screenshot: "observation";
  different earlier reply: "downstream");
* A0.5 outcome discordance for identical-start pairs against the rest;
* A0.6 pairs with identical IR sequences: verdict, checker-input and state-digest agreement
  (a natural open-loop replay);
* A0.7 the estimated wall-clock minute of the step-1 capture (the top-bar clock) against
  step-1 screenshot identity;
* A0.8 the rerun spacing of within-session pairs.

Outcomes are the registered binarized raw verdicts (y = 1 iff score == 1.0). Every interval is
a Wilson 95% interval unless named otherwise; zero-event bounds are exact one-sided 95%
(1 - 0.05^(1/n)) per pair and per distinct (size, task). Nothing here is a decision rule; the
census feeds the design.

Usage::

    python3 scripts/run_r01_stage_a0_doctor.py --output OUT.json
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIGESTS = ROOT / "program/evidence/2026-10-11/r01-stage-a0/s1a-step-digests.jsonl.gz"
A1 = ROOT / "program/evidence/2026-10-10/q2-stage1-analysis/a1.jsonl"
DIGESTS_SHA256 = "91f848432df45be3fe79f4175f4ab8b4f8103f4a646d2e800f6eca30a92d01df"
A1_SHA256 = "4af798f5908e48aaf84d116682c813311b5ae48096e3b7ed2299c1530c08c6c0"
PLAN = ROOT / "program/evidence/2026-10-09/q2-stage1-prefreeze/plan/plan-a0a.json"
PLAN_SHA256 = "a5f0aadce1208d9d9ab31ff572ca93e624dbd87e1b50dd194987ff8cc46e1806"
SCHEMA = "r01-stage-a0-census-v1"
SAME_MINUTE_MARGIN_S = 5.0  # both estimated captures at least this far from a minute boundary


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def wilson(k: int, n: int, z: float = 1.959964) -> list[float | None]:
    if n == 0:
        return [None, None]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(max(0.0, c - h), 4), round(min(1.0, c + h), 4)]


def prop(k: int, n: int) -> dict:
    return {"k": k, "n": n, "share": round(k / n, 4) if n else None, "wilson95": wilson(k, n)}


def zero_ub(n: int) -> float | None:
    return round(1 - 0.05 ** (1 / n), 4) if n else None


def fisher_one_sided(a: int, b: int, c: int, d: int) -> float:
    """P(X <= a) for the hypergeometric table [[a, b], [c, d]] (a small in the first row)."""
    n1, n2, m = a + b, c + d, a + c
    tot = n1 + n2

    def pmf(x: int) -> float:
        return math.comb(n1, x) * math.comb(n2, m - x) / math.comb(tot, m)

    lo = max(0, m - n2)
    return round(sum(pmf(x) for x in range(lo, a + 1)), 6)


def y(rec: dict) -> int:
    return 1 if rec.get("score") is not None and float(rec["score"]) == 1.0 else 0


def t_step1(rec: dict) -> float | None:
    """Estimated host time of the step-1 screenshot (driver order: t_start, boot wait, setup,
    keyboard warm-up, the 60 s settle, then the first observation)."""
    t = rec.get("timings") or {}
    parts = [
        t.get("boot_wait_s"),
        t.get("setup_s"),
        t.get("warmup_s"),
        t.get("settle_after_reset_s"),
    ]
    if rec.get("t_start") is None or any(p is None for p in parts):
        return None
    return float(rec["t_start"]) + sum(float(p) for p in parts)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    checks = {
        "digests_sha256": sha(DIGESTS) == DIGESTS_SHA256,
        "a1_jsonl_sha256": sha(A1) == A1_SHA256,
        "plan_sha256": sha(PLAN) == PLAN_SHA256,
    }
    if not all(checks.values()):
        print(json.dumps({"status": "FAIL", "checks": checks}))
        return 1
    with gzip.open(DIGESTS, "rt") as fh:
        rows = [json.loads(x) for x in fh if x.strip()]
    recs = [json.loads(x) for x in A1.read_text().splitlines() if x.strip()]
    domains = json.loads(PLAN.read_text())["task_domains"]
    key = lambda r: (r["size"], r["harness"], r["session"], r["task_id"], r["rerun"])  # noqa: E731
    D = {key(r): r for r in rows}
    R = {key(r): r for r in recs}
    checks["rows_1808"] = len(rows) == 1808 and len(D) == 1808
    checks["records_match_rows"] = set(D) == set(R)
    checks["all_scored"] = all(r["status"] == "scored" for r in recs)

    tasks = sorted({r["task_id"] for r in recs})
    within = []  # (size, harness, session, task)
    for z in ("4B", "9B"):
        for h in ("H-OSW-fixed", "H-GA"):
            for s in ("S1", "S2"):
                for t in tasks:
                    if (z, h, s, t, 1) in D and (z, h, s, t, 2) in D:
                        within.append(((z, h, s, t, 1), (z, h, s, t, 2)))
    between = []
    for z in ("4B", "9B"):
        for h in ("H-OSW-fixed", "H-GA"):
            for t in tasks:
                for i in (1, 2):
                    for j in (1, 2):
                        a, b = (z, h, "S1", t, i), (z, h, "S2", t, j)
                        if a in D and b in D:
                            between.append((a, b))
    checks["within_pairs_904"] = len(within) == 904
    checks["between_pairs_1808"] = len(between) == 1808

    def steps(k):
        return D[k]["steps"]

    out: dict = {
        "schema": SCHEMA,
        "checks": checks,
        "inputs": {
            "digests": str(DIGESTS.relative_to(ROOT)),
            "digests_sha256": DIGESTS_SHA256,
            "a1_jsonl": str(A1.relative_to(ROOT)),
            "a1_jsonl_sha256": A1_SHA256,
            "plan": str(PLAN.relative_to(ROOT)),
            "plan_sha256": PLAN_SHA256,
            "episodes": len(rows),
            "steps": sum(len(r["steps"]) for r in rows),
            "tasks": len(tasks),
        },
        "labels": [
            "not externally anchored",
            "S1a's realized sessions on this host",
            "binarized raw verdicts (y = 1 iff score == 1.0)",
        ],
    }

    # A0.1 step-1 input identity
    def s1(pairs):
        obs = sum(steps(a)[0]["obs"] == steps(b)[0]["obs"] for a, b in pairs)
        req = sum(steps(a)[0]["req"] == steps(b)[0]["req"] for a, b in pairs)
        msg = sum(steps(a)[0]["msg"] == steps(b)[0]["msg"] for a, b in pairs)
        return {
            "pairs": len(pairs),
            "processed_screenshot_equal": obs,
            "request_equal": req,
            "messages_equal": msg,
        }

    out["A0_1_step1_input_identity"] = {
        "within_session": s1(within),
        "between_session": s1(between),
        "within_by_size_harness": {
            f"{z}/{h}": s1([p for p in within if p[0][0] == z and p[0][1] == h])
            for z in ("4B", "9B")
            for h in ("H-OSW-fixed", "H-GA")
        },
    }

    # A0.2 natural replays (within-session; walk while the request digest is equal)
    nat = []
    for a, b in within:
        for sa, sb in zip(steps(a), steps(b), strict=False):
            if sa["req"] is None or sa["req"] != sb["req"]:
                break
            nat.append(
                {
                    "size": a[0],
                    "harness": a[1],
                    "step": sa["k"],
                    "rep_eq": sa["rep"] == sb["rep"],
                    "ir_eq": sa["ir"] == sb["ir"],
                    "pair": (a, b),
                }
            )
            if sa["rep"] != sb["rep"]:
                break
    n_nat = len(nat)
    out["A0_2_natural_replays"] = {
        "definition": (
            "within-session pairs; step k counted when its request digest (full body, images "
            "included) is equal and every earlier step's request and reply were equal"
        ),
        "identical_requests": n_nat,
        "distinct_pairs": len({x["pair"] for x in nat}),
        "by_step": dict(sorted(Counter(x["step"] for x in nat).items())),
        "reply_text_differs": prop(sum(not x["rep_eq"] for x in nat), n_nat),
        "ir_differs": prop(sum(not x["ir_eq"] for x in nat), n_nat),
        "step1_reply_text_differs": prop(
            sum(not x["rep_eq"] for x in nat if x["step"] == 1), sum(x["step"] == 1 for x in nat)
        ),
        "step1_ir_differs": prop(
            sum(not x["ir_eq"] for x in nat if x["step"] == 1), sum(x["step"] == 1 for x in nat)
        ),
        "by_size": {
            z: {
                "n": sum(x["size"] == z for x in nat),
                "reply_text_differs": sum(not x["rep_eq"] for x in nat if x["size"] == z),
                "ir_differs": sum(not x["ir_eq"] for x in nat if x["size"] == z),
            }
            for z in ("4B", "9B")
        },
        "by_harness": {
            h: {
                "n": sum(x["harness"] == h for x in nat),
                "reply_text_differs": sum(not x["rep_eq"] for x in nat if x["harness"] == h),
            }
            for h in ("H-OSW-fixed", "H-GA")
        },
    }
    # implied per-token flip hazard under a constant-hazard model (descriptive)
    toks = [steps(x["pair"][0])[x["step"] - 1]["ctok"] for x in nat]
    mean_tok = sum(toks) / len(toks) if toks else None
    pdiff = sum(not x["rep_eq"] for x in nat) / n_nat if n_nat else None
    out["A0_2_natural_replays"]["mean_completion_tokens"] = round(mean_tok, 1) if mean_tok else None
    out["A0_2_natural_replays"]["implied_per_token_flip_hazard"] = (
        round(1 - (1 - pdiff) ** (1 / mean_tok), 5) if pdiff is not None and mean_tok else None
    )

    # A0.3 step-1 divergence by step-1 input identity
    same_in = [(a, b) for a, b in within if steps(a)[0]["req"] == steps(b)[0]["req"]]
    diff_in = [(a, b) for a, b in within if steps(a)[0]["req"] != steps(b)[0]["req"]]

    def s1_div(pairs):
        rep = sum(steps(a)[0]["rep"] != steps(b)[0]["rep"] for a, b in pairs)
        ir = sum(steps(a)[0]["ir"] != steps(b)[0]["ir"] for a, b in pairs)
        return {
            "pairs": len(pairs),
            "reply_text_differs": prop(rep, len(pairs)),
            "ir_differs": prop(ir, len(pairs)),
        }

    a3s, a3d = s1_div(same_in), s1_div(diff_in)
    out["A0_3_step1_divergence_by_input"] = {
        "identical_step1_request": a3s,
        "different_step1_request": a3d,
        "fisher_one_sided_p_reply": fisher_one_sided(
            a3s["reply_text_differs"]["k"],
            len(same_in) - a3s["reply_text_differs"]["k"],
            a3d["reply_text_differs"]["k"],
            len(diff_in) - a3d["reply_text_differs"]["k"],
        ),
        "fisher_one_sided_p_ir": fisher_one_sided(
            a3s["ir_differs"]["k"],
            len(same_in) - a3s["ir_differs"]["k"],
            a3d["ir_differs"]["k"],
            len(diff_in) - a3d["ir_differs"]["k"],
        ),
        "note": "not randomized: identical step-1 inputs arise from near-simultaneous dispatch",
    }

    # A0.4 survival and first-divergence labels (within-session)
    def first(pairs, field):
        res = []
        for a, b in pairs:
            sa, sb = steps(a), steps(b)
            k = None
            for x, y_ in zip(sa, sb, strict=False):
                if x[field] != y_[field]:
                    k = x["k"]
                    break
            if k is None and len(sa) != len(sb):
                k = min(len(sa), len(sb)) + 1
            res.append(k)
        return res

    surv = {}
    for field in ("req", "rep", "ir"):
        f = first(within, field)
        surv[field] = {
            str(k): round(sum(1 for v in f if v is None or v > k) / len(f), 4) for k in range(1, 16)
        }
        surv[field]["never"] = sum(1 for v in f if v is None)
    labels = Counter()
    for a, b in within:
        sa, sb = steps(a), steps(b)
        lab = "identical"
        for x, y_ in zip(sa, sb, strict=False):
            if x["obs"] != y_["obs"] and x["k"] == 1:
                lab = "observation_at_step1"
                break
            if x["req"] != y_["req"]:
                lab = "observation_later" if x["obs"] != y_["obs"] else "request_other"
                break
            if x["rep"] != y_["rep"]:
                lab = "serving_identical_input"
                break
        else:
            if len(sa) != len(sb):
                lab = "length"
        labels[lab] += 1
    out["A0_4_survival_within"] = {
        "share_identical_through_step_k": surv,
        "first_reply_divergence_label": dict(labels),
        "note": (
            "'observation_at_step1' pairs cannot be attributed: the screenshot already differs, so "
            "whether identical inputs would have given identical replies is not observed for them"
        ),
    }

    # A0.5 outcome discordance (binarized) by step-1 identity, and the 4B H-OSW-fixed floor
    def disc(pairs):
        k = sum(y(R[a]) != y(R[b]) for a, b in pairs)
        return prop(k, len(pairs))

    ir_seq_eq = lambda a, b: [s["ir"] for s in steps(a)] == [s["ir"] for s in steps(b)]  # noqa: E731
    out["A0_5_outcome_discordance"] = {
        "within_all": disc(within),
        "within_identical_step1_request": disc(same_in),
        "within_different_step1_request": disc(diff_in),
        "within_identical_step1_never_ir_divergent": sum(ir_seq_eq(a, b) for a, b in same_in),
        "D_w_4B_H_OSW_fixed": disc(
            [p for p in within if p[0][0] == "4B" and p[0][1] == "H-OSW-fixed"]
        ),
        "D_w_4B_pooled_harness": disc([p for p in within if p[0][0] == "4B"]),
        "D_b_4B_H_OSW_fixed": disc(
            [p for p in between if p[0][0] == "4B" and p[0][1] == "H-OSW-fixed"]
        ),
    }

    # A0.6 identical-IR-sequence pairs: natural open-loop replay
    def irpairs(pairs, label):
        eq = [(a, b) for a, b in pairs if ir_seq_eq(a, b)]
        vd = sum(y(R[a]) != y(R[b]) for a, b in eq)
        sd = sum(float(R[a]["score"]) != float(R[b]["score"]) for a, b in eq)
        units = {(a[0], a[3]) for a, b in eq}
        chk = sum(
            R[a].get("checker_input_sha256") != R[b].get("checker_input_sha256") for a, b in eq
        )
        st = sum(R[a].get("state_sha256") != R[b].get("state_sha256") for a, b in eq)
        ended = Counter(R[a].get("ended") for a, b in eq)
        nsteps = [len(steps(a)) for a, b in eq]
        return {
            "set": label,
            "pairs": len(eq),
            "distinct_size_task_units": len(units),
            "verdict_discordant": vd,
            "score_unequal": sd,
            "exact_upper95_per_pair": zero_ub(len(eq)) if vd == 0 else None,
            "exact_upper95_per_size_task_unit": zero_ub(len(units)) if vd == 0 else None,
            "checker_input_digest_differs": chk,
            "state_digest_differs": st,
            "ended": dict(ended),
            "mean_steps": round(sum(nsteps) / len(nsteps), 2) if nsteps else None,
            "pairs_with_10_or_more_steps": sum(1 for n in nsteps if n >= 10),
            "success_share": round(sum(y(R[a]) for a, b in eq) / len(eq), 4) if eq else None,
        }

    out["A0_6_identical_ir_pairs"] = {
        "within": irpairs(within, "within-session"),
        "between": irpairs(between, "between-session"),
        "all": irpairs(within + between, "within and between"),
        "note": (
            "selected subset: pairs whose closed-loop trajectories happened to coincide; "
            "skewed to short, successful episodes. Saved-file and registry digests differ in "
            "most of them (the guest clock reaches saved artifacts), so state digests cannot "
            "serve as a determinism checksum without normalization"
        ),
    }

    # A0.7 estimated capture minute against step-1 screenshot identity (within-session)
    rows7 = []
    for a, b in within:
        ta, tb = t_step1(R[a]), t_step1(R[b])
        if ta is None or tb is None:
            continue
        same_min = math.floor(ta / 60) == math.floor(tb / 60)
        margin = min(ta % 60, 60 - ta % 60, tb % 60, 60 - tb % 60)
        rows7.append(
            {
                "same_min": same_min,
                "margin": margin,
                "gap": abs(ta - tb),
                "obs_eq": steps(a)[0]["obs"] == steps(b)[0]["obs"],
                "domain": domains.get(a[3], "?"),
            }
        )
    clear_same = [r for r in rows7 if r["same_min"] and r["margin"] >= SAME_MINUTE_MARGIN_S]
    diff_min = [r for r in rows7 if not r["same_min"]]
    out["A0_7_capture_minute"] = {
        "estimate": (
            "t_start + boot_wait_s + setup_s + warmup_s + settle_after_reset_s (host clock)"
        ),
        "pairs_with_estimate": len(rows7),
        "same_minute_any": {
            "pairs": sum(r["same_min"] for r in rows7),
            "screenshot_equal": sum(r["same_min"] and r["obs_eq"] for r in rows7),
        },
        "same_minute_clear": {
            "margin_s": SAME_MINUTE_MARGIN_S,
            "pairs": len(clear_same),
            "screenshot_differs": prop(sum(not r["obs_eq"] for r in clear_same), len(clear_same)),
        },
        "different_minute": {
            "pairs": len(diff_min),
            "screenshot_equal": sum(r["obs_eq"] for r in diff_min),
        },
        "screenshot_equal_pairs_all_same_minute": all(r["same_min"] for r in rows7 if r["obs_eq"]),
        "same_minute_clear_by_domain": {
            d: {
                "pairs": sum(r["domain"] == d for r in clear_same),
                "screenshot_differs": sum(r["domain"] == d and not r["obs_eq"] for r in clear_same),
            }
            for d in sorted({r["domain"] for r in clear_same})
        },
        "note": (
            "same-minute pairs whose screenshots differ show a varying region other than the "
            "clock (caret, animation, loading state, or a clock read error of the estimate); "
            "hashes cannot locate it, so the pixel census needs fresh captures"
        ),
    }

    # A0.8 rerun spacing (within-session; step-1 capture estimates)
    gaps = sorted(r["gap"] for r in rows7)
    out["A0_8_rerun_spacing"] = {
        "pairs": len(gaps),
        "gap_s_quantiles": {
            q: round(gaps[min(len(gaps) - 1, int(q * len(gaps)))], 1)
            for q in (0.1, 0.25, 0.5, 0.75, 0.9)
        }
        if gaps
        else {},
        "under_60s": sum(1 for g in gaps if g < 60),
        "under_300s": sum(1 for g in gaps if g < 300),
    }

    out["status"] = "PASS" if all(checks.values()) else "FAIL"
    out["doctor"] = "r01-stage-a0"
    out["evidence_grade"] = (
        "records-only census of S1a (descriptive design input; enters no registered decision rule)"
    )
    out["cases"] = {name: ("PASS" if ok else "FAIL") for name, ok in checks.items()}
    text = json.dumps(out, indent=1, sort_keys=True, default=str)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text + "\n")
    summary = {
        "status": out["status"],
        "natural_identical_requests": n_nat,
        "reply_text_differs": out["A0_2_natural_replays"]["reply_text_differs"],
        "ir_differs": out["A0_2_natural_replays"]["ir_differs"],
        "identical_ir_pairs": out["A0_6_identical_ir_pairs"]["all"]["pairs"],
        "identical_ir_pairs_verdict_discordant": out["A0_6_identical_ir_pairs"]["all"][
            "verdict_discordant"
        ],
        "same_minute_clear_screenshot_differs": out["A0_7_capture_minute"]["same_minute_clear"][
            "screenshot_differs"
        ],
    }
    print("R01_A0_SUMMARY " + json.dumps(summary, sort_keys=True))
    return 0 if out["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
