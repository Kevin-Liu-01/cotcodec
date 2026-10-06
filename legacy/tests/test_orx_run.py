import json
from pathlib import Path

import pytest
import yaml

from scripts import orx_run


def write_node(tmp_path: Path, node: dict) -> Path:
    path = tmp_path / "node.yaml"
    path.write_text(yaml.safe_dump(node))
    return path


def test_default_node_contract_is_valid() -> None:
    node = orx_run.load_node()
    assert node["kind"] == "cpu-doctor"
    assert node["doctor"].startswith("scripts/run_") and node["doctor"].endswith("_doctor.py")


def test_rejects_unknown_kind_and_unregistered_doctor(tmp_path: Path) -> None:
    with pytest.raises(orx_run.NodeContractError):
        orx_run.load_node(write_node(tmp_path, {"kind": "shell", "direction": "x"}))
    with pytest.raises(orx_run.NodeContractError):
        orx_run.load_node(
            write_node(
                tmp_path,
                {"kind": "cpu-doctor", "direction": "x", "doctor": "scripts/run_missing_doctor.py"},
            )
        )
    with pytest.raises(orx_run.NodeContractError):
        orx_run.load_node(
            write_node(
                tmp_path,
                {
                    "kind": "cpu-doctor",
                    "direction": "x",
                    "doctor": "scripts/../etc/run_x_doctor.py",
                },
            )
        )


def test_rejects_args_that_hijack_output(tmp_path: Path) -> None:
    with pytest.raises(orx_run.NodeContractError):
        orx_run.load_node(
            write_node(
                tmp_path,
                {
                    "kind": "cpu-doctor",
                    "direction": "x",
                    "doctor": "scripts/run_semantic_clock_gate_parity_doctor.py",
                    "args": ["--output", "/tmp/evil.json"],
                },
            )
        )


def test_slurm_manifest_requires_committed_experiments_yaml(tmp_path: Path) -> None:
    node = orx_run.load_node(
        write_node(
            tmp_path,
            {
                "kind": "slurm-manifest",
                "direction": "x",
                "manifest": "experiments/architectures/semantic-clock-gate-parity.yaml",
            },
        )
    )
    argv = orx_run.submitter_argv(node, "--dry-run")
    assert argv[1].endswith("scripts/submit_docker_research_job.py") and argv[-1] == "--dry-run"
    with pytest.raises(orx_run.NodeContractError):
        orx_run.load_node(
            write_node(
                tmp_path, {"kind": "slurm-manifest", "direction": "x", "manifest": "/etc/passwd"}
            )
        )


def test_dry_run_prints_plan(capsys) -> None:
    assert orx_run.main(["--dry-run"]) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["node"]["kind"] == "cpu-doctor"
    assert "--output" in plan["plan_argv"]


def test_receipt_summary_counts_status_pass_cases() -> None:
    receipt = {
        "status": "PHASE0_DOCTOR_PASS",
        "cases": [{"status": "PASS"}, {"status": "FAIL"}, {"status": "skipped"}],
    }
    assert orx_run.summarize_receipt(receipt)["cases"] == {"total": 3, "passed": 1}
    mapping = {"cases": {"a": "PASS", "b": {"status": "pass"}, "c": {"passed": False}}}
    assert orx_run.summarize_receipt(mapping)["cases"] == {"total": 3, "passed": 2}


def test_receipt_summary_counts_cases() -> None:
    receipt = {
        "status": "PASS",
        "cases": [{"passed": True}, {"passed": False}],
        "evidence_grade": "SYNTHETIC",
    }
    assert orx_run.summarize_receipt(receipt)["cases"] == {"total": 2, "passed": 1}


def test_parse_job_id() -> None:
    assert orx_run.parse_job_id("Submitted batch job 361\n") == "361"
    assert orx_run.parse_job_id("nothing here") is None


def test_parse_slurm_terminal_fails_closed() -> None:
    completed = "JobId=361 JobState=COMPLETED ExitCode=0:0 NodeList=fal-h100-01"
    failed = "JobId=362 JobState=FAILED Reason=NonZeroExitCode ExitCode=1:0"
    assert orx_run.parse_slurm_terminal(completed) == ("COMPLETED", "0:0")
    assert orx_run.parse_slurm_terminal(failed) == ("FAILED", "1:0")
    assert orx_run.parse_slurm_terminal("") == ("UNKNOWN", "UNKNOWN")
    assert orx_run.slurm_succeeded("COMPLETED", "0:0") is True
    assert orx_run.slurm_succeeded("FAILED", "1:0") is False
    assert orx_run.slurm_succeeded("UNAVAILABLE", "UNAVAILABLE") is False
