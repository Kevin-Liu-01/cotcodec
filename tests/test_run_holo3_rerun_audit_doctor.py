from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from harness import holo3_rerun_audit as audit
from harness import remote_zip
from scripts import orx_run, preregister
from scripts import run_holo3_rerun_audit_doctor as doctor
from tests import _holo3_world as world_mod

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FAST = [
    "--sign-flip-draws",
    "2000",
    "--model-draws",
    "2000",
    "--power-sims-d",
    "20",
    "--power-sims-a",
    "5",
]


@pytest.fixture
def synthetic(monkeypatch: pytest.MonkeyPatch):
    world = world_mod.build_world()
    monkeypatch.setattr(
        doctor,
        "load_leaderboard",
        lambda cache_dir: (world_mod.leaderboard_rows(), {"url": "synthetic"}),
    )

    def load_configs(commit, universe, cache_dir):
        return world_mod.configs(world), {"commit": commit, "configs": len(universe)}

    monkeypatch.setattr(doctor, "load_configs", load_configs)

    def factory(args):
        ctx = audit.FetchContext(
            world_mod.opener(world),
            cache=remote_zip.MemberCache(args.cache_dir / "members"),
            max_workers=2,
        )
        return ctx, remote_zip.TransferStats()

    return world, factory


def run(tmp_path: Path, factory, *extra: str) -> tuple[int, dict]:
    output = tmp_path / "receipt.json"
    code = doctor.main(
        [
            "--output",
            str(output),
            "--cache-dir",
            str(tmp_path / "cache"),
            "--ledger",
            str(tmp_path / "ledger.jsonl"),
            *FAST,
            *extra,
        ],
        context_factory=factory,
    )
    return code, json.loads(output.read_text())


def test_v1_stage_passes_on_synthetic_archives_and_writes_public_safe_outputs(
    tmp_path, synthetic
) -> None:
    world, factory = synthetic
    matrix = tmp_path / "matrix.csv"
    code, receipt = run(tmp_path, factory, "--h-steps", "--matrix-output", str(matrix))
    assert code == 0, receipt
    assert receipt["status"] == "PASS" and receipt["label"] == "POST-HOC"
    cases = receipt["cases"]
    for name in (
        "holo3_leaderboard_domain_cells",
        "leaderboard_constants_match_pinned_sheet",
        "verified_members_match_sha256sums",
        "package_summaries_agree_with_per_task_files",
        "opencua_turn_totals_match_leaderboard",
        "receipt_public_safety",
    ):
        assert cases[name]["status"] == "PASS", name
    assert "v1_recorded_numbers_reproduced" not in cases  # only at the registered draw counts
    text = (tmp_path / "receipt.json").read_text()
    assert world_mod.FAKE_PRIVATE_IP not in text and "devtools" not in text
    assert receipt["preregistrations"]["v2"]["ledger"]["frozen"] is False
    assert receipt["results"]["external_reference"]["label"].startswith("EXPLORATORY")
    assert receipt["results"]["v2_design"]["rule_a_power"]
    rows = list(csv.DictReader(matrix.open()))
    assert len(rows) == 361 and receipt["outputs"]["holo3_matrix_rows"] == 361


def test_flipped_score_fails_with_exit_1(tmp_path, synthetic) -> None:
    world, factory = synthetic
    victim = next(t for t in world.universe["os"] if world.run1[t] == 1.0)
    world.run1[victim] = 0.0
    code, receipt = run(tmp_path, factory, "--skip-opencua")
    assert code == 1 and receipt["status"] == "FAIL"
    assert receipt["cases"]["holo3_leaderboard_domain_cells"]["status"] == "FAIL"


def test_missing_member_is_an_infrastructure_error(tmp_path, synthetic) -> None:
    world, factory = synthetic
    world.drop = {"evaluation_examples/test_nogdrive.json"}
    code, receipt = run(tmp_path, factory, "--skip-opencua")
    assert code == 2 and receipt["status"] == "INFRA_ERROR"
    assert receipt["error"]["type"] == "MissingMemberError"


def test_receipt_with_an_infrastructure_identifier_is_withheld(
    tmp_path, synthetic, monkeypatch
) -> None:
    _, factory = synthetic
    monkeypatch.setattr(audit, "error_class", lambda text: text or "none")  # leak raw error strings
    code, receipt = run(tmp_path, factory, "--skip-opencua")
    assert code == 1
    assert receipt["cases"] == {"receipt_public_safety": receipt["cases"]["receipt_public_safety"]}
    assert receipt["cases"]["receipt_public_safety"]["status"] == "FAIL"
    assert world_mod.FAKE_PRIVATE_IP not in (tmp_path / "receipt.json").read_text()


def test_v2_stages_refuse_until_v2_is_frozen(tmp_path, synthetic) -> None:
    _, factory = synthetic
    code, receipt = run(tmp_path, factory, "--stage", "v2")
    assert code == 3 and receipt["status"] == "REFUSED"
    other = tmp_path / "second"
    other.mkdir()
    code, receipt = run(other, factory, "--stage", "v2-tarball", "--tarball-dir", str(other))
    assert code == 3 and receipt["status"] == "REFUSED"


def test_v2_stage_runs_against_a_frozen_draft_in_a_scratch_ledger(tmp_path, synthetic) -> None:
    world, factory = synthetic
    ledger = tmp_path / "ledger.jsonl"
    draft = PROJECT_ROOT / doctor.V2_PREREG
    preregister.freeze(draft, "q2-holo3-rerun-audit-v2", ledger=ledger, root=PROJECT_ROOT)
    features = {}
    for scores in (world.run1, world.run2):
        for t in scores:
            trajectory = t.replace("0000-4000", "1111-4111")
            features[trajectory] = {
                "trajectory_id": trajectory,
                "steps": 12,
                "final_tool": "answer",
                "tools": {},
                "env_text_hits": {},
                "tool_error_entries": 0,
                "parsed": True,
                "images": 12,
                "max_identical_screenshot_run": 1,
                "compressed_offset": 300_000_000,
            }
    feature_file = tmp_path / "features.json"
    feature_file.write_text(json.dumps({"features": features}))
    code, receipt = run(
        tmp_path, factory, "--stage", "v2", "--trajectory-features", str(feature_file)
    )
    assert code == 0, receipt
    v2_result = receipt["results"]["v2"]
    assert set(receipt["results"]["evaluator_classes"]["counts_all"]) <= {"L", "W", "O"}
    assert v2_result["decisions"]["holm_family"] == ["a", "d"]
    assert v2_result["rules_abc"]["rule_c_coverage"]["coverage_ok"] is True
    assert receipt["preregistrations"]["v2"]["ledger"]["frozen"] is True
    probe = receipt["results"]["v2_probe_sensitivity"]
    assert probe["trajectories_in_probed_region"] == 0
    assert all(probe["robust"].values())


def test_refuses_to_overwrite_output(tmp_path, synthetic) -> None:
    _, factory = synthetic
    (tmp_path / "receipt.json").write_text("{}")
    with pytest.raises(SystemExit):
        run(tmp_path, factory)


def test_preregistrations_pass_the_freeze_lint_and_the_node_is_admitted(tmp_path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    for experiment_id, rel in (
        (doctor.V1_EXPERIMENT_ID, doctor.V1_PREREG),
        ("q2-holo3-rerun-audit-v2", doctor.V2_PREREG),
    ):
        row = preregister.freeze(
            PROJECT_ROOT / rel, experiment_id, ledger=ledger, root=PROJECT_ROOT
        )
        assert row["path"] == rel
    node = orx_run.load_node(
        PROJECT_ROOT / "experiments" / "q2-holo3-rerun-audit" / "orx-node.yaml"
    )
    assert node["doctor"] == "scripts/run_holo3_rerun_audit_doctor.py"
    assert "--output" not in node["args"]
