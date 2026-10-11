"""K2 classification rules, the fitness gate, the K2 report and the K2-C list."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from harness.q2_mutation import analysis, campaign
from harness.q2_mutation_k2 import candidates, lane, report, rules

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
    assert result["summary"]["families_not_covered_by_k2"] == []
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


def test_the_summary_reports_each_set_by_family_verdict_and_save_path() -> None:
    inputs = synthetic(80)
    inputs["k2c"] = [dict(inputs["sample"][0])]
    for record in inputs["records"]:
        if record["pair"] in (1, 2):
            record["save_paths"] = {"/f.docx": "agent_save"}
        if record["pair"] == 3:
            record["save_paths"] = {"/f.docx": "agent_save", "/g.xlsx": "no_save"}
        if record["pair"] == 2:
            record["verdict"] = "fail"  # an unexplained difference on an agent save
        record["observations"] = {"calls": 3, "retried": 1, "slow": 0, "undelivered": 0,
                                  "unusual": [], "max_s": 0.2}  # fmt: skip
    for run in (1, 2):
        inputs["records"].append(
            {
                **scored("pass"),
                "set": "k2c",
                "pair": 0,
                "run": run,
                "attempt": 1,
                "purpose": "k2",
                "slot": f"k2c:000:r{run}",
                "candidate_sha256": inputs["sample"][0]["candidate_sha256"],
                "timings": {"run_s": 100.0 + run},
            }
        )
    inputs["records"].append(
        {
            "status": "infrastructure",
            "exclusion": rules.VM_INFRA,
            "set": "k2",
            "pair": 4,
            "run": 1,
            "attempt": 2,
            "purpose": "k2",
            "slot": "k2:004:r1",
            "infrastructure_type": "executor:upload",
            "candidate_sha256": inputs["sample"][4]["candidate_sha256"],
        }
    )
    result = report.build(**inputs)
    rows = {(r["set"], r["pair"]): r for r in result["pairs"]}
    assert rows[("k2", 0)]["save_path"] == "postconfig_save"
    assert rows[("k2", 3)]["save_path"] == "agent_save+no_save"
    summary = result["summary"]
    k2 = summary["k2"]
    assert k2["by_save_path"]["agent_save"] == {
        "pairs": 2,
        "agree": 1,
        "differ": 1,
        "excluded": 0,
        "explanations": {rules.UNEXPLAINED: 1},
    }
    assert k2["by_save_path"]["postconfig_save"]["pairs"] == 77
    assert set(k2["by_offline_verdict"]) == {"pass"}
    assert k2["runs"]["attempts"] == 161 and summary["k2c"]["runs"]["attempts"] == 2
    assert k2["runs"]["infrastructure_types"] == {"executor:upload": 1}
    assert summary["k2c"]["runs"]["infrastructure_types"] == {}
    assert k2["runs"]["observations"] == {
        "runs": 160,
        "calls": 480,
        "retried": 160,
        "slow": 0,
        "undelivered": 0,
        "unusual": 0,
        "max_s": 0.2,
    }
    assert summary["k2c"]["runs"]["run_s"]["n"] == 2
    assert summary["k2c"]["by_save_path"] == {
        "postconfig_save": {"pairs": 1, "agree": 1, "differ": 0, "excluded": 0, "explanations": {}},
    }
    assert summary["runs"]["attempts"] == 163  # pooled over both sets
    # Agreement is per set only (section 8): no table pools K2 with K2-C.
    for key in ("by_family", "by_offline_verdict", "by_save_path", "agree", "pairs"):
        assert key not in summary, key
    assert summary["blind_warning"] == report.BLIND_WARNING
    assert rows[("k2", 4)]["save_path"] == "postconfig_save"  # its scored attempts recorded it
    bare = synthetic(10)
    for record in bare["records"]:
        if record["pair"] == 0:
            record.update(status="infrastructure", exclusion=rules.VM_INFRA, verdict=None)
            record.pop("save_paths")
    for row in bare["records"] + bare["receipts"]:
        row["purpose"] = "development"
    assert report.build(**bare)["pairs"][0]["save_path"] == report.NOT_RECORDED


def test_the_receipt_summary_names_jobs_seen_in_the_host_snapshots() -> None:
    snapshots = [
        {"block": "start", "squeue_foreign": []},
        {"block": "k2-r1", "squeue_foreign": []},
        {"block": "end", "squeue_foreign": [["1132", "u", "RUNNING", "32", "N/A", "pilot-cpu"]]},
    ]
    assert report.host_overlap(snapshots) == {
        "snapshots": 3,
        "with_foreign_jobs": ["end"],
        "foreign_jobs": {"1132": {"cpus": "32", "name": "pilot-cpu"}},
    }
    inputs = synthetic()
    inputs["receipts"][0]["snapshots"] = snapshots
    summary = report.build(**inputs)["summary"]
    assert summary["receipts"][0]["host_overlap"]["with_foreign_jobs"] == ["end"]


# --------------------------------------------------------------------------- the k2 report CLI


def git(repo: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid",
         "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", *args],
        capture_output=True, text=True, check=True,
    )  # fmt: skip
    return done.stdout.strip()


def frozen_repo(tmp_path: Path, *, extra_in_freeze: bool = False) -> dict[str, Any]:
    """A scratch repository: a commit holding the registration (git_head_at_freeze), then the
    freeze commit adding only its ledger row (the real ledger is never touched)."""
    repo = tmp_path / "repo"
    registration = repo / lane.REGISTRATION
    registration.parent.mkdir(parents=True)
    registration.write_text(
        f"# test registration\n\nK2-C list SHA-256: `{report.sha256_file(K2C)}`\n"
    )
    (repo / "harness" / "q2_mutation_k2").mkdir(parents=True)  # the code the export runs
    (repo / "harness" / "q2_mutation_k2" / "lane.py").write_text("RUN = 'k2'\n")
    git(repo, "init", "-q")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "registration")
    parent = git(repo, "rev-parse", "HEAD")
    sys.path.insert(0, str(ROOT / "scripts"))
    import preregister

    row = preregister.freeze(registration, lane.EXPERIMENT_ID, ledger=repo / lane.LEDGER, root=repo)
    if extra_in_freeze:
        (repo / "other.txt").write_text("not the ledger\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "freeze")
    return {
        "repo": repo,
        "parent": parent,
        "freeze": git(repo, "rev-parse", "HEAD"),
        "row": row,
        "tree": lane.tree_sha256(repo),  # what the lane records for an export of either commit
    }


def registered_run(
    tmp_path: Path, frozen: dict[str, Any], commit: str, name: str = "run", tree: str | None = None
) -> Path:
    """A k2 run directory whose runs all give the offline verdict (the real registered inputs)."""
    sample = read_jsonl(RELEASED / "k2/k2-sample.jsonl")
    k2c = read_jsonl(K2C)
    offline = {
        v["mutant_id"]: v["verdict"]
        for v in read_jsonl(RELEASED / "confirm-mutants-v1/verdicts-lock.jsonl")
    }
    records = []
    for set_name, rows in (("k2", sample), ("k2c", k2c)):
        for i, row in enumerate(rows):
            for run in (1, 2):
                records.append(
                    {
                        **scored(offline[row["job_id"]]),
                        "set": set_name,
                        "pair": i,
                        "run": run,
                        "purpose": "k2",
                        "slot": f"{set_name}:{i:03d}:r{run}",
                        "candidate_sha256": row["candidate_sha256"],
                    }
                )
    run_dir = tmp_path / name
    run_dir.mkdir()
    (run_dir / "k2-runs.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records))
    receipt = {
        "purpose": "k2",
        "job_id": "1300",
        "identity": {
            "executor_commit": commit,
            "git_head_at_freeze": frozen["row"]["git_head_at_freeze"],
            "ledger_row_hash": frozen["row"]["hash"],
            "source_tree_sha256": tree or frozen.get("tree"),
            "vm_image_id": lane.VM_PINS["image_id"],
        },
    }
    (run_dir / "lane-receipt.json").write_text(json.dumps(receipt))
    return run_dir


def report_argv(run_dirs: list[Path], repo: Path, out: Path) -> list[str]:
    argv = []
    for run_dir in run_dirs:
        argv += ["--run-dir", str(run_dir)]
    return [
        *argv,
        "--repo",
        str(repo),
        "--sample",
        str(RELEASED / "k2/k2-sample.jsonl"),
        "--k2c",
        str(K2C),
        "--verdicts",
        str(RELEASED / "confirm-mutants-v1/verdicts-lock.jsonl"),
        "--notes-summary",
        str(RELEASED / "confirm-mutants-v1/notes-summary.json"),
        "--out-dir",
        str(out),
    ]


@pytest.mark.skipif(shutil.which("git") is None, reason="needs git")
def test_the_k2_report_checks_the_freeze_commit_and_reads_one_job(tmp_path: Path) -> None:
    frozen = frozen_repo(tmp_path)
    assert frozen["row"]["git_head_at_freeze"] == frozen["parent"]
    run_dir = registered_run(tmp_path, frozen, frozen["freeze"])
    out = tmp_path / "out"
    assert report.main(report_argv([run_dir], frozen["repo"], out)) == 0
    k2 = json.loads((out / "k2-report.json").read_text())
    assert k2["outcome"] == "VERIFIED" and k2["executor_commit"] == frozen["freeze"]
    assert k2["freeze"]["git_head_at_freeze"] == frozen["parent"]
    assert k2["freeze"]["changed"] == [lane.LEDGER]
    assert k2["freeze"]["source_tree_sha256"] == frozen["tree"]
    assert k2["blind_warning"] == report.BLIND_WARNING
    summary = json.loads((out / "k2-summary.json").read_text())
    assert summary["blind_warning"] == report.BLIND_WARNING
    assert summary["freeze"]["ledger_row_hash"] == frozen["row"]["hash"]
    assert summary["k2"]["pairs"] == 80 and summary["k2c"]["pairs"] == 41
    # An export of git_head_at_freeze (the parent) is not the executor of record.
    parent_run = registered_run(tmp_path, frozen, frozen["parent"], name="parent-run")
    with pytest.raises(report.ReportError, match="not the freeze commit"):
        report.main(report_argv([parent_run], frozen["repo"], tmp_path / "o2"))
    # One job: a second run directory is refused.
    second = registered_run(tmp_path, frozen, frozen["freeze"], name="second")
    with pytest.raises(report.ReportError, match="exactly one run directory"):
        report.main(report_argv([run_dir, second], frozen["repo"], tmp_path / "o3"))
    # The K2-C digest comes from the frozen registration, never from an argument.
    with pytest.raises(SystemExit):
        report.main([*report_argv([run_dir], frozen["repo"], tmp_path / "o4"),
                     "--k2c-sha256", "0" * 64])  # fmt: skip
    # A receipt whose ledger row is not the checkout's row is refused.
    receipt = json.loads((run_dir / "lane-receipt.json").read_text())
    receipt["identity"]["ledger_row_hash"] = "0" * 64
    (run_dir / "lane-receipt.json").write_text(json.dumps(receipt))
    with pytest.raises(report.ReportError, match="not the frozen row"):
        report.main(report_argv([run_dir], frozen["repo"], tmp_path / "o5"))
    # An export whose .git_sha names the freeze commit but whose harness/ tree is not that
    # commit's (the receipt records the digest of the tree that ran) is refused.
    other = registered_run(tmp_path, frozen, frozen["freeze"], name="other-tree", tree="d" * 64)
    with pytest.raises(report.ReportError, match="source tree digest"):
        report.main(report_argv([other], frozen["repo"], tmp_path / "o6"))


@pytest.mark.skipif(shutil.which("git") is None, reason="needs git")
def test_the_commit_tree_digest_is_the_lanes_source_tree_digest(tmp_path: Path) -> None:
    """``report.commit_tree_sha256`` (from ``git archive``) equals the digest the batch file
    checks and the lane receipt records (``harness.q2.vm.manifest.source_tree_sha256``)."""
    repo = tmp_path / "repo"
    (repo / "harness" / "sub").mkdir(parents=True)
    (repo / "harness" / "a.py").write_text("A = 1\n")
    (repo / "harness" / "sub" / "b.txt").write_bytes(b"\x00binary\n")
    (repo / "other.txt").write_text("outside harness/\n")
    git(repo, "init", "-q")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "tree")
    (repo / "harness" / "__pycache__").mkdir()  # bytecode the lane may leave in an export
    (repo / "harness" / "__pycache__" / "a.cpython-310.pyc").write_bytes(b"pyc")
    assert report.commit_tree_sha256(repo, "HEAD") == lane.tree_sha256(repo)
    (repo / "harness" / "a.py").write_text("A = 2\n")  # the export differs from the commit
    assert report.commit_tree_sha256(repo, "HEAD") != lane.tree_sha256(repo)
    with pytest.raises(report.ReportError, match="git archive"):
        report.commit_tree_sha256(repo, "0" * 40)


@pytest.mark.skipif(shutil.which("git") is None, reason="needs git")
def test_the_k2_report_refuses_a_freeze_commit_that_changes_more_than_the_ledger(
    tmp_path: Path,
) -> None:
    frozen = frozen_repo(tmp_path, extra_in_freeze=True)
    run_dir = registered_run(tmp_path, frozen, frozen["freeze"])
    with pytest.raises(report.ReportError, match="more than the ledger"):
        report.main(report_argv([run_dir], frozen["repo"], tmp_path / "out"))


def test_the_k2_report_needs_the_frozen_registration(tmp_path: Path) -> None:
    repo = tmp_path / "unfrozen"
    (repo / lane.REGISTRATION).parent.mkdir(parents=True)
    (repo / lane.REGISTRATION).write_text(f"K2-C list SHA-256: `{report.sha256_file(K2C)}`\n")
    frozen = {"row": {"git_head_at_freeze": "a" * 40, "hash": "b" * 64}}
    run_dir = registered_run(tmp_path, frozen, "c" * 40)
    with pytest.raises(report.ReportError, match="not frozen"):
        report.main(report_argv([run_dir], repo, tmp_path / "out"))
