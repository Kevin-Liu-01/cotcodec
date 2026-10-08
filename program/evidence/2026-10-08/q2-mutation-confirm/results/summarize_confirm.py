"""Aggregates of the registered confirm outputs (descriptive; counts only).

Reads only committed files: ``analysis.json`` (the registered analysis),
the audit summary, its decisions and pool, and the released sample and
spot-check list. It adds tables, never a decision: each item's decision is
``raters.final_decision`` as ``audit summarize`` wrote it, and the ranges
under Kevin's pending adjudication are the arithmetic bounds of the
registered rules (every pool item answered one way or the other), not
answers.

    python summarize_confirm.py   # from this directory
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
AUDIT = HERE.parent / "audit"


def jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def main() -> None:
    analysis = json.loads((HERE / "analysis.json").read_text())
    summary = json.loads((AUDIT / "audit-summary/audit-summary.json").read_text())
    decisions = {row["key"]: row for row in jsonl(AUDIT / "audit-summary/decisions.jsonl")}
    pool = {row["item_id"] for row in jsonl(AUDIT / "audit-summary/adjudication-pool.jsonl")}
    sample = jsonl(AUDIT / "released/confirm-audit-v1/sample.jsonl")
    spot = {row["item_id"] for row in jsonl(AUDIT / "released/confirm-audit-v1/spot-check.jsonl")}

    def group(row: dict) -> str:
        return f"sham_{row['sham']}" if row.get("sham") else str(row["stratum"])

    table: dict[str, Counter] = defaultdict(Counter)
    per_rater: dict[str, dict[str, Counter]] = {"anthropic": defaultdict(Counter), "open_weight": defaultdict(Counter)}
    for row in sample:
        d = decisions[row["mutant_id"]]
        table[group(row)][f"{d['first']}/{d['second']} -> {d['decision']}"] += 1
        per_rater["anthropic"][group(row)][d["first"]] += 1
        per_rater["open_weight"][group(row)][d["second"]] += 1
    real = [r for r in sample if not r.get("sham")]
    agree = sum(1 for r in real if decisions[r["mutant_id"]]["first"] == decisions[r["mutant_id"]]["second"])
    by_id = {r["item_id"]: r for r in sample}
    # Section 9: ambiguous labels are reported as counts per witness rule and
    # verdict, never as rates (lock-exact venv, status ambiguous).
    ambiguous: Counter[str] = Counter()
    for row in jsonl(HERE / "released/confirm-mutants-v1/outcomes.jsonl"):
        if row.get("lock_status") == "ambiguous":
            ambiguous[f"{row.get('witness_rule')}|{row.get('lock_verdict')}"] += 1

    fn = analysis["checker_candidates"]["false_negative"]
    fp = analysis["checker_candidates"]["false_positive"]
    alt = analysis["audit_gate"]["P2_alt_decisions"]
    fn_reading = fn["counts"]["by_audit_reading"]
    fp_reading = fp["counts"]["by_audit_reading"]
    k3 = summary["k3"]
    out = {
        "schema": "q2m-confirm-results-summary-v1",
        "role": "descriptive (D35); P2-P5 exploratory under D34 (i); the human spot check and Kevin's adjudication are pending",
        "kappa_real_items": summary["kappa"],
        "raw_agreement_real_items": {"agree": agree, "n": len(real), "share": agree / len(real)},
        "sham_accuracy": summary["sham_accuracy"],
        "answer_status": summary["answer_status"],
        "decisions_by_group": {k: dict(v) for k, v in sorted(table.items())},
        "answers_by_rater_and_group": {
            rater: {k: dict(v) for k, v in sorted(groups.items())} for rater, groups in per_rater.items()
        },
        "unresolved_real_items": {"n": summary["n_unresolved"], "of": summary["n_items"]},
        "ambiguous_by_witness_rule_and_lock_verdict": dict(sorted(ambiguous.items())),
        "adjudication": {
            "pool": len(pool),
            "by_reason": summary["adjudication"]["pool_by_reason"],
            "by_group": dict(Counter(group(by_id[i]) for i in pool)),
            "spot_check": len(spot),
            "spot_check_by_group": dict(Counter(group(by_id[i]) for i in spot)),
            "spot_check_also_in_pool": len(pool & spot),
            "union_items": len(pool | spot),
        },
        "pending_ranges": {
            "rule": "each pool item answered accept or reject by Kevin (D34, D38); kappa never changes",
            "false_negative_confirmed": {
                "now": fn_reading.get("confirmed", 0),
                "min": fn_reading.get("confirmed", 0),
                "max": fn_reading.get("confirmed", 0) + fn_reading.get("unresolved", 0),
                "of": fn["counts"]["events"],
            },
            "false_positive_confirmed": {
                "now": fp_reading.get("confirmed", 0),
                "min": fp_reading.get("confirmed", 0),
                "max": fp_reading.get("confirmed", 0) + fp_reading.get("label_contradicted", 0),
                "of": fp["counts"]["events"],
            },
            "alt_solutions_entering_P2": {
                "now": alt.get("accept", 0),
                "min": alt.get("accept", 0),
                "max": alt.get("accept", 0) + alt.get("unresolved", 0) + alt.get("reject", 0),
                "of": sum(alt.values()),
            },
            "gold_defect_tasks": {
                "now": len(summary["gold_defects"]["tasks"]),
                "max": summary["adjudication"]["pool_by_reason"].get("gold_sham_split", 0),
            },
            "k3_equivalence_label_error": {
                "now": k3["should_pass_equiv"]["estimate"],
                "min": 0.0,
                "note": "unresolved items count as errors until adjudicated; a gold-defect task's equivalence items leave the group",
            },
            "k3_violation_label_error": {"now": k3["should_fail_violation"]["estimate"], "min": 0.0},
            "unchanged_by_adjudication": [
                "kappa",
                "P1 (no P1 flip is in the pool)",
                "P3, P5 (checker events, no audit gate)",
                "P4 (no passed extra change outside probe-touched cells)",
                "candidate shares (the confirmed shares change)",
            ],
        },
    }
    (HERE / "summary.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(json.dumps(out, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
