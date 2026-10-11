"""K2 classification rules, the fitness gate, the K2 report and the K2-C list."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from harness.q2_mutation import analysis, campaign
from harness.q2_mutation_k2 import candidates, report, rules

ROOT = Path(__file__).resolve().parents[1]
RELEASED = ROOT / "program/evidence/2026-10-08/q2-mutation-confirm/results/released"
K2C = ROOT / "program/evidence/2026-10-11/q2-mutation-k2/k2c-candidates-confirm.jsonl"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


def test_the_explanations_are_the_parents_frozen_four() -> None:
    assert rules.K2_EXPLANATIONS == analysis.K2_EXPLANATIONS
    assert rules.outcome({"passes": False}, [])["label"] == analysis.K2_UNVERIFIED


def test_checker_family_matches_the_campaign() -> None:
    for funcs in (
        ["compare_table"],
        ["compare_pptx_files", "compare_pptx_files"],
        ["compare_table", "compare_csv"],
    ):
        assert report.checker_family(funcs) == campaign.checker_family(funcs)


def scored(verdict: str, *, late: bool = False, attempt: int = 1) -> dict[str, Any]:
    record: dict[str, Any] = {
        "status": "scored",
        "verdict": verdict,
        "attempt": attempt,
        "save_paths": {"/f.xlsx": "postconfig_save"},
    }
    if late:
        record.update(unsaved_at_read=["/f.xlsx"], late_write={"/f.xlsx": {"changed": True}})
    return record


def infra(cause: str = rules.VM_INFRA, attempt: int = 1) -> dict[str, Any]:
    return {"status": "infrastructure", "exclusion": cause, "attempt": attempt}


def test_run_reading_takes_the_scored_attempt_and_names_the_exclusion() -> None:
    assert rules.run_reading([infra(), scored("pass", attempt=2)])["verdict"] == "pass"
    both = rules.run_reading([infra(rules.HASH_MISMATCH), infra(attempt=2)])
    assert both == {"state": "excluded", "cause": rules.HASH_MISMATCH, "attempts": 2}
    assert rules.run_reading([])["state"] == "missing"
    assert rules.run_reading([{"status": "cap_truncated"}])["state"] == "missing"
    with pytest.raises(rules.RuleError):
        rules.run_reading([{"status": "infrastructure", "exclusion": "operator_error"}])


@pytest.mark.parametrize(
    ("runs", "offline", "unstable", "state", "explanation"),
    [
        ([scored("pass"), scored("pass")], "pass", False, "agree", None),
        ([scored("pass"), infra()], "pass", False, "agree", None),
        ([infra(), infra()], "pass", False, "excluded", rules.VM_INFRA),
        ([infra(rules.HASH_MISMATCH), infra()], "pass", False, "excluded", rules.HASH_MISMATCH),
        (
            [scored("fail", late=True), scored("fail", late=True)],
            "pass",
            False,
            "differ",
            rules.SAVE_LATE,
        ),
        ([scored("fail", late=True), scored("fail")], "pass", False, "differ", rules.UNEXPLAINED),
        ([scored("fail"), scored("pass")], "pass", False, "differ", rules.NONDETERMINISTIC),
        ([scored("fail"), scored("fail")], "pass", True, "differ", rules.NONDETERMINISTIC),
        ([scored("fail"), scored("fail")], "pass", False, "differ", rules.UNEXPLAINED),
        ([scored("error"), scored("error")], "fail", False, "differ", rules.UNEXPLAINED),
    ],
)
def test_pair_rules(runs: list, offline: str, unstable: bool, state: str, explanation: Any) -> None:
    readings = [rules.run_reading([r]) for r in runs]
    pair = rules.classify_pair(readings, offline, unstable)
    assert (pair["state"], pair["explanation"]) == (state, explanation)


def test_gate_and_outcome() -> None:
    def pairs(excluded: int, unexplained: int) -> list[dict[str, Any]]:
        out = [
            {"state": "excluded", "explanation": rules.VM_INFRA, "checker_family": "x"}
        ] * excluded
        out += [
            {
                "state": "differ",
                "explanation": rules.UNEXPLAINED,
                "checker_family": "compare_pptx_files",
            }
        ] * unexplained
        out += [
            {"state": "differ", "explanation": rules.SAVE_LATE, "checker_family": "compare_table"}
        ]
        out += [{"state": "agree", "explanation": None, "checker_family": "y"}] * (80 - len(out))
        return out

    ok = rules.gate(pairs(8, 0))
    assert ok["passes"] and ok["excluded"] == 8
    assert rules.outcome(ok, pairs(8, 0))["outcome"] == "VERIFIED"
    dropped = rules.outcome(ok, pairs(8, 2))
    assert dropped["outcome"] == "FAMILIES_DROPPED"
    assert dropped["families_dropped"] == ["compare_pptx_files"]
    bad = rules.gate(pairs(9, 0))
    assert not bad["passes"]
    incomplete = rules.outcome(bad, pairs(9, 0))
    assert incomplete["outcome"] == "INCOMPLETE" and not incomplete["write_analysis_report"]
    with pytest.raises(rules.RuleError):
        rules.gate(pairs(0, 0)[:79])


def synthetic(n: int = 80) -> dict[str, Any]:
    sample = [
        {
            "job_id": f"t{i}__op__{i}",
            "mutant_id": f"t{i}__op__{i}",
            "task_id": f"t{i}",
            "kind": "mutant",
            "candidate_sha256": f"{i:064x}",
        }
        for i in range(n)
    ]
    verdicts = [
        {
            "mutant_id": s["job_id"],
            "candidate_sha256": s["candidate_sha256"],
            "verdict": "pass",
            "checker_funcs": ["compare_table"],
        }
        for s in sample
    ]
    verdicts[0]["checker_funcs"] = ["compare_pptx_files"]
    records = []
    for i, s in enumerate(sample):
        for run in (1, 2):
            base = {
                "set": "k2",
                "pair": i,
                "run": run,
                "attempt": 1,
                "purpose": "k2",
                "slot": f"k2:{i:03d}:r{run}",
                "candidate_sha256": s["candidate_sha256"],
            }
            records.append({**base, **scored("pass")})
    receipt = {
        "purpose": "k2",
        "identity": {"executor_commit": "a" * 40, "vm_image_id": "sha256:" + "f" * 64},
    }
    return {
        "records": records,
        "receipts": [receipt],
        "sample": sample,
        "k2c": [],
        "verdicts": verdicts,
        "nondeterministic": [],
    }


def test_report_feeds_the_parents_analysis_and_its_family_drop() -> None:
    inputs = synthetic()
    # Pair 0 (compare_pptx_files) fails in both runs: an unexplained difference.
    for record in inputs["records"]:
        if record["pair"] == 0:
            record["verdict"] = "fail"
    result = report.build(**inputs)
    k2 = result["analysis_report"]
    assert k2["pairs"] == 80 and k2["compared"] == 80 and k2["agree"] == 79
    assert k2["executor_commit"] == "a" * 40
    assert k2["outcome"] == "FAMILIES_DROPPED"
    exclusions = analysis.headline_exclusions(None, k2)
    assert exclusions["k2"]["families_dropped"] == ["compare_pptx_files"]
    assert exclusions["k2"]["label"] == "VM fidelity checked (K2)"


def test_report_is_withheld_when_the_gate_fails_or_for_development() -> None:
    inputs = synthetic()
    for record in inputs["records"]:
        if record["pair"] < 9:
            record.update(status="infrastructure", exclusion=rules.VM_INFRA, verdict=None)
    result = report.build(**inputs)
    assert result["outcome"]["outcome"] == "INCOMPLETE"
    assert "analysis_report" not in result
    dev = synthetic(10)
    for row in dev["records"] + dev["receipts"]:
        row["purpose"] = "development"
    dev_result = report.build(**dev)
    assert "analysis_report" not in dev_result and dev_result["gate"]["max_excluded"] == 1
    picked = {**dev, "records": [r for r in dev["records"] if r["pair"] in (1, 3)]}
    subset = report.build(**picked, only=["k2:001", "k2:003"])
    assert [p["pair"] for p in subset["pairs"]] == [1, 3]
    with pytest.raises(report.ReportError, match="every registered pair"):
        report.build(**synthetic(), only=["k2:001"])


def test_report_refuses_inconsistent_records() -> None:
    inputs = synthetic()
    inputs["records"][0]["candidate_sha256"] = "e" * 64
    with pytest.raises(report.ReportError, match="candidate differs"):
        report.build(**inputs)
    inputs = synthetic()
    inputs["records"].append({**inputs["records"][0]})
    with pytest.raises(report.ReportError, match="recorded twice"):
        report.build(**inputs)
    inputs = synthetic()
    inputs["records"].append({**inputs["records"][0], "pair": 99})
    with pytest.raises(report.ReportError, match="outside the sample"):
        report.build(**inputs)
    inputs = synthetic(79)
    with pytest.raises(report.ReportError, match="not 80"):
        report.build(**inputs)


@pytest.mark.parametrize(
    "name",
    [
        "audit/audit-summary/adjudication-pool.jsonl",
        "adjudications.jsonl",
        "audit/audit-summary/decisions.jsonl",
        "released/confirm-audit-v1/spot-check.jsonl",
        "audit/claude-isolated/calls.jsonl",
        "released/confirm-audit-v1/sample.jsonl",
    ],
)
def test_the_report_never_reads_audit_or_adjudication_files(tmp_path: Path, name: str) -> None:
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{}\n")
    with pytest.raises(report.ReportError, match="never reads"):
        report.check_input(path)
    ok = tmp_path / "k2" / "k2-sample.jsonl"
    ok.parent.mkdir(parents=True, exist_ok=True)
    ok.write_text("{}\n")
    assert report.check_input(ok) == ok


def test_no_k2_module_imports_the_audit_or_the_raters() -> None:
    for path in (ROOT / "harness" / "q2_mutation_k2").rglob("*.py"):
        text = path.read_text()
        for name in ("audit", "raters", "rater_runner", "packets"):
            assert f"q2_mutation.{name}" not in text, f"{path} imports {name}"
            assert f"import {name}" not in text, f"{path} imports {name}"


def test_k2c_list_is_every_reported_candidate_and_only_them() -> None:
    outcomes = read_jsonl(RELEASED / "confirm-mutants-v1/outcomes.jsonl")
    verdicts = read_jsonl(RELEASED / "confirm-mutants-v1/verdicts-lock.jsonl")
    rows = candidates.k2c_candidates(outcomes, verdicts)
    assert rows == read_jsonl(K2C)
    assert len(rows) == 41
    assert sum(r["event"] == "FN" for r in rows) == 36
    assert sum(r["event"] == "FP_R" for r in rows) == 5
    # The registered analysis lists the same mutants (ids only are read here).
    result = json.loads((RELEASED.parent / "analysis.json").read_text())["checker_candidates"]
    listed = {
        c["mutant_id"]
        for key in ("false_negative", "false_positive")
        for c in result[key]["events"]
    }
    assert listed == {r["mutant_id"] for r in rows}


def test_the_frozen_sample_is_the_registered_one() -> None:
    sample = RELEASED / "k2/k2-sample.jsonl"
    assert report.sha256_file(sample) == report.REGISTERED_INPUTS["sample"]
    summary = json.loads(
        (
            ROOT / "program/evidence/2026-10-08/q2-mutation-confirm/mutants-confirm-v1/score/"
            "k2-sample.summary.json"
        ).read_text()
    )
    assert summary["sample_sha256"] == report.REGISTERED_INPUTS["sample"]
    assert summary["pairs"] == 80 and summary["tasks"] == 41
    assert (
        report.sha256_file(RELEASED / "confirm-mutants-v1/verdicts-lock.jsonl")
        == (report.REGISTERED_INPUTS["verdicts"])
    )
    assert (
        report.sha256_file(RELEASED / "confirm-mutants-v1/notes-summary.json")
        == (report.REGISTERED_INPUTS["notes_summary"])
    )
