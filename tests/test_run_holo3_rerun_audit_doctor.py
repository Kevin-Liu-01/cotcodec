from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import http.client
import io
import json
import tarfile
import zlib
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest
import scipy

from harness import holo3_rerun_audit as audit
from harness import holo3_v2 as v2
from harness import remote_zip
from scripts import orx_run, preregister
from scripts import run_holo3_rerun_audit_doctor as doctor
from tests import _holo3_world as world_mod

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FAST = ["--sign-flip-draws", "2000", "--model-draws", "2000", "--power-sims-a", "5"]


@pytest.fixture
def synthetic(monkeypatch: pytest.MonkeyPatch):
    world = world_mod.build_world()
    monkeypatch.setattr(
        doctor,
        "load_leaderboard",
        lambda cache_dir: (world_mod.leaderboard_rows(), {"url": "synthetic"}),
    )

    def load_configs(commit, universe, cache_dir):
        info = {"commit": commit, "configs": len(universe)}
        info["config_blob_manifest_sha256"] = world.config_manifest
        return world_mod.configs(world), info

    world.config_manifest = v2.V1_CONFIG_BLOB_MANIFEST

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


def freeze_v2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch | None = None) -> Path:
    """Freeze v2 into the scratch ledger the runs use.

    With ``monkeypatch``, also freeze it into a stand-in for the repository
    ledger and point the doctor's freeze gate there, as after the real freeze.
    The runs still name the scratch ledger, so they stay NON-CONFIRMATORY.
    """
    ledger = tmp_path / "ledger.jsonl"
    draft = PROJECT_ROOT / doctor.V2_PREREG
    preregister.freeze(draft, v2.V2_EXPERIMENT_ID, ledger=ledger, root=PROJECT_ROOT)
    if monkeypatch is not None:
        repository = tmp_path / "repository" / "ledger.jsonl"
        preregister.freeze(draft, v2.V2_EXPERIMENT_ID, ledger=repository, root=PROJECT_ROOT)
        monkeypatch.setattr(doctor, "REPOSITORY_LEDGER", repository)
    return ledger


def synthetic_matrix(world):
    ctx = audit.FetchContext(world_mod.opener(world), cache=None, max_workers=2)
    pkg = audit.load_verified_package(ctx)
    web = {t: audit.web_dependent(c) for t, c in world_mod.configs(world).items()}
    m = audit.build_v1_matrix(pkg, web)
    features: dict[str, dict[str, v2.TrajectoryFeatures]] = collections.defaultdict(dict)

    def on_actions(tag, task, entries):
        item = v2.TrajectoryFeatures(task)
        v2.parse_actions(item, entries)
        features[tag][task] = item

    h = audit.load_h_runs(ctx, pkg.universe, with_steps=True, on_actions=on_actions)
    return m, h, dict(features)


def synthetic_h_reference(world) -> dict:
    m, h, features = synthetic_matrix(world)
    pooled = v2.h_reference(features, h.rewards, doctor.clean_tasks(m))["pooled"]
    return {key: pooled[key] for key in ("tasks", "environment", "agent_side", "classes")}


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
    assert receipt["results"]["v1"]["h_steps"]
    assert "v2_design" not in receipt["results"]  # moved to the v2-design stage
    assert "confirmatory_checks" not in receipt
    rows = list(csv.DictReader(matrix.open()))
    assert len(rows) == 361 and receipt["outputs"]["holo3_matrix_rows"] == 361


def test_v2_design_stage_uses_already_inspected_data_only(tmp_path, synthetic, monkeypatch) -> None:
    world, factory = synthetic
    monkeypatch.setattr(v2, "REGISTERED_H_REFERENCE", synthetic_h_reference(world))
    code, receipt = run(tmp_path, factory, "--stage", "v2-design")
    assert code == 0, receipt
    assert receipt["cases"]["rule_b_h_reference_matches_registration"]["status"] == "PASS"
    assert receipt["label"] == "DESIGN" and receipt["evidence_grade"].startswith("DESIGN")
    results = receipt["results"]
    assert "evaluator_classes" not in results and "v2" not in results
    assert "opencua_turn_totals_match_leaderboard" not in receipt["cases"]
    design = results["v2_design"]
    strata = design["url_strata_known_before_registration"]
    assert set(strata) == {"web", "offline"}
    assert sum(s["tasks"] for s in strata.values()) == design["clean_tasks"]
    assert design["net_flips_all"] == sum(s["run1_only"] - s["run2_only"] for s in strata.values())
    sized = [r for r in design["rule_d_power_exact"] if r["odds_ratio"] == 1.0]
    assert sized and all(r["power_test_alone"] <= v2.ALPHA_D for r in sized)
    assert {r["fraction_of_tasks_shifted"] for r in design["rule_a_power"]} >= {1.0, 0.3}
    rule_b = design["rule_b"]
    pooled = rule_b["reference_primary"]["pooled"]
    expected = synthetic_h_reference(world)
    assert {k: pooled[k] for k in expected} == expected
    assert set(rule_b["null_check_each_h_run_vs_other_two"]) == {"primary", "step_cap_first"}
    assert design["unique_failures"]["run2"] == rule_b["run2_unique_failures"]
    # Added after the pre-freeze audit.
    counts = design["clean_outcome_counts"]
    assert sum(counts.values()) == design["clean_tasks"]
    assert counts["run1_only"] == sum(s["run1_only"] for s in strata.values())
    by_outcome = design["rule_a_power_by_outcome"]
    assert {r["run2_step_factor"] for r in by_outcome} >= {1.0, 1.1, round(1 / 1.1, 4)}
    assert all("power_mean_concordant_tasks" in r and "mean_m" in r for r in by_outcome)
    size = design["rule_d_size_all_allocations"]
    assert size["allocations"] == (strata["web"]["tasks"] + 1) * (strata["offline"]["tasks"] + 1)
    assert size["max_size"] < v2.ALPHA_D
    power_b = design["rule_b_power"]["rows"]
    assert {r["class"] for r in power_b} == {"environment", "agent_side"}
    assert any(r["at_reference_share"] for r in power_b)
    env = receipt["environment"]
    assert env["scipy"] == scipy.__version__ and env["numpy"] == np.__version__
    assert env["python"].count(".") == 2


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


def test_a_truncated_reply_is_an_infrastructure_error(tmp_path, synthetic, monkeypatch) -> None:
    """Regression (review finding 7): IncompleteRead used to crash with no receipt."""
    _, factory = synthetic

    def truncated(args, ctx, receipt):
        raise http.client.IncompleteRead(b"", 100)

    monkeypatch.setitem(doctor.STAGES, "v1", truncated)
    code, receipt = run(tmp_path, factory, "--skip-opencua")
    assert code == 2 and receipt["status"] == "INFRA_ERROR"
    assert receipt["error"]["type"] == "IncompleteRead"


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
    assert receipt["label"] == "v2 NON-CONFIRMATORY" and "confirmatory_checks" not in receipt
    other = tmp_path / "second"
    other.mkdir()
    code, receipt = run(other, factory, "--stage", "v2-tarball", "--tarball-dir", str(other))
    assert code == 3 and receipt["status"] == "REFUSED"


def test_v2_refuses_to_skip_the_opencua_control(tmp_path, synthetic, monkeypatch) -> None:
    """Regression (review finding 6): --skip-opencua used to drop a registered control."""
    _, factory = synthetic
    freeze_v2(tmp_path, monkeypatch)
    code, receipt = run(tmp_path, factory, "--stage", "v2", "--skip-opencua")
    assert code == 3 and receipt["status"] == "REFUSED"
    assert "skip-opencua" in receipt["error"]


def feature_file(world, tmp_path: Path, *, probed: set[str], capped: set[str]) -> Path:
    features = {}
    for run, scores in (("run1", world.run1), ("run2", world.run2), ("repair", world.run1)):
        for t, score in scores.items():
            if score is None:
                continue
            trajectory = world_mod.trajectory_id(t, run)
            steps = 100 if (run == "run2" and t in capped) else 12
            features[trajectory] = {
                "trajectory_id": trajectory,
                "steps": steps,
                "final_tool": "answer",
                "tools": {},
                "env_text_hits": {},
                "tool_error_entries": 0,
                "parsed": True,
                "images": steps,
                "max_identical_screenshot_run": 1,
                "compressed_offset": 1_000 if t in probed else 300_000_000,
            }
    path = tmp_path / "features.json"
    path.write_text(json.dumps({"features": features}))
    return path


def test_v2_stage_end_to_end_on_a_scratch_ledger(tmp_path, synthetic, monkeypatch) -> None:
    world, factory = synthetic
    monkeypatch.setattr(v2, "REGISTERED_H_REFERENCE", synthetic_h_reference(world))
    freeze_v2(tmp_path, monkeypatch)
    m, _, _ = synthetic_matrix(world)
    clean = doctor.clean_tasks(m)
    run1_only = [t for t in world_mod.run1_only_tasks(world) if t in clean]
    probed = set(clean[:5])
    capped = set(run1_only[: max(1, len(run1_only) // 2 + 1)])
    path = feature_file(world, tmp_path, probed=probed, capped=capped)
    code, receipt = run(tmp_path, factory, "--stage", "v2", "--trajectory-features", str(path))
    assert code == 0, receipt["cases"]
    assert receipt["cases"]["rule_b_h_reference_matches_registration"]["status"] == "PASS"
    assert receipt["cases"]["opencua_turn_totals_match_leaderboard"]["status"] == "PASS"
    # A scratch ledger is never the registered result (review finding 6).
    assert receipt["label"] == "v2 NON-CONFIRMATORY"
    assert receipt["confirmatory_checks"]["repository_ledger"] is False
    assert receipt["ledger"]["is_repository_ledger"] is False
    assert str(tmp_path) not in json.dumps(receipt)

    classes = receipt["results"]["evaluator_classes"]
    assert classes["counts_all"]["L"] > 0 and classes["narrow_L_count_all"] > 0
    result = receipt["results"]["v2"]
    d = result["rule_d"]
    live = set(world_mod.run1_only_tasks(world)[::2]) & set(clean)
    in_l = d["strata"]["web"]["run1_only_in_L"] + d["strata"]["offline"]["run1_only_in_L"]
    assert live and in_l >= len(live)
    assert d["stratified_exact_one_sided_p"] < v2.ALPHA_D
    assert result["decisions"]["rule_d"] == v2.rule_d_decision(d)
    assert "rule_d_narrow_L_sensitivity" in result["decisions"]
    abc = result["rules_abc"]
    assert abc["rule_c_coverage"]["coverage_ok"] is True
    primary = abc["rule_b_primary"]["run2_unique_failures"]
    assert primary["classes"].get("step_cap", 0) >= 1
    probe = receipt["results"]["v2_probe_sensitivity"]
    expected_probed = sum(
        1
        for t in probed
        for run, scores in (("run1", world.run1), ("run2", world.run2), ("repair", world.run1))
        if scores[t] is not None
    )
    assert probe["trajectories_in_probed_region"] == expected_probed
    assert probe["clean_tasks_kept"] == len(clean) - len(probed)
    assert probe["rules_abc"]["rule_a_steps"]["n_pairs"] == len(clean) - len(probed)


def test_v2_stage_fails_a_control_on_an_unregistered_h_reference(
    tmp_path, synthetic, monkeypatch
) -> None:
    world, factory = synthetic
    wrong = dict(synthetic_h_reference(world), tasks=999)
    monkeypatch.setattr(v2, "REGISTERED_H_REFERENCE", wrong)
    freeze_v2(tmp_path, monkeypatch)
    code, receipt = run(tmp_path, factory, "--stage", "v2")
    assert code == 1 and receipt["status"] == "FAIL"
    assert receipt["cases"]["rule_b_h_reference_matches_registration"]["status"] == "FAIL"


def test_v2_is_confirmatory_only_when_every_run_condition_holds(
    tmp_path, synthetic, monkeypatch
) -> None:
    world, factory = synthetic
    monkeypatch.setattr(v2, "REGISTERED_H_REFERENCE", synthetic_h_reference(world))
    freeze_v2(tmp_path, monkeypatch)
    seen = {}

    def all_pass(args, state, *, uses_trajectories):
        seen["uses_trajectories"] = uses_trajectories
        return {"repository_ledger": True, "code_unchanged_since_freeze": True}

    monkeypatch.setattr(doctor, "confirmatory_checks", all_pass)
    code, receipt = run(tmp_path, factory, "--stage", "v2")
    assert code == 0 and receipt["label"] == "v2 CONFIRMATORY"
    assert receipt["evidence_grade"].startswith("v2 CONFIRMATORY")
    assert seen["uses_trajectories"] is False


def test_confirmatory_checks(tmp_path, monkeypatch) -> None:
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text("")
    calls: list[tuple[str, ...]] = []

    def git_ok(*command: str) -> bool:
        calls.append(command)
        return not (command[0] == "diff" and command[2] == "bad")

    monkeypatch.setattr(doctor, "_git_ok", git_ok)
    monkeypatch.setattr(doctor, "REPOSITORY_LEDGER", PROJECT_ROOT / "program" / "x.jsonl")
    args = argparse.Namespace(ledger=PROJECT_ROOT / "program" / "x.jsonl")
    fresh = datetime.now(UTC).isoformat()
    state = {"ledger": {"frozen": True, "frozen_at": fresh, "git_head_at_freeze": "a" * 40}}
    checks = doctor.confirmatory_checks(args, state, uses_trajectories=True)
    assert checks == {
        "repository_ledger": True,
        "ledger_committed_and_unmodified": True,
        "code_unchanged_since_freeze": True,
        "within_14_days_of_freeze": True,
    }
    assert ("diff", "--quiet", "a" * 40, "--", *doctor.CODE_FILES) in calls
    late = (datetime.now(UTC) - timedelta(days=15)).isoformat()
    state = {"ledger": {"frozen_at": late, "git_head_at_freeze": "bad"}}
    checks = doctor.confirmatory_checks(args, state, uses_trajectories=True)
    assert checks["within_14_days_of_freeze"] is False
    assert checks["code_unchanged_since_freeze"] is False
    no_head = doctor.confirmatory_checks(
        args, {"ledger": {"frozen_at": fresh}}, uses_trajectories=False
    )
    assert no_head["code_unchanged_since_freeze"] is False
    assert "within_14_days_of_freeze" not in no_head
    other = doctor.confirmatory_checks(
        argparse.Namespace(ledger=ledger), {"ledger": {}}, uses_trajectories=False
    )
    assert other["repository_ledger"] is False
    assert other["ledger_committed_and_unmodified"] is False


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


# --------------------------------------------------------------------------- #
# Pre-freeze audit (2026-10-07)
# --------------------------------------------------------------------------- #


def test_a_freeze_in_a_scratch_ledger_alone_is_refused(tmp_path, synthetic, monkeypatch) -> None:
    """Audit blocking defect 1: the gate read whatever --ledger named, so a
    scratch-ledger freeze let v2 classify evaluators and v2-tarball download."""
    world, factory = synthetic
    monkeypatch.setattr(v2, "REGISTERED_H_REFERENCE", synthetic_h_reference(world))
    monkeypatch.setattr(doctor, "REPOSITORY_LEDGER", tmp_path / "repository" / "ledger.jsonl")
    freeze_v2(tmp_path)  # the scratch ledger only
    code, receipt = run(tmp_path, factory, "--stage", "v2")
    assert code == 3 and receipt["status"] == "REFUSED", receipt.get("status")
    assert "repository ledger" in receipt["error"]
    assert receipt["freeze_gate"] == {"repository_ledger_frozen": False, "run_ledger_frozen": True}
    assert "evaluator_classes" not in receipt["results"] and "v2" not in receipt["results"]
    other = tmp_path / "second"
    other.mkdir()
    freeze_v2(other)
    tar_dir = other / "tar"
    code, receipt = run(
        other,
        factory,
        "--stage",
        "v2-tarball",
        "--allow-large-download",
        "--tarball-dir",
        str(tar_dir),
    )
    assert code == 3 and receipt["status"] == "REFUSED"
    assert "tarball" not in receipt["results"] and not tar_dir.exists()


def _scan_receipt(features: Path, row_hash: str, **changes) -> dict:
    receipt = {
        "doctor": doctor.DOCTOR_NAME,
        "stage": "v2-tarball",
        "status": "PASS",
        "label": "v2 CONFIRMATORY",
        "confirmatory_checks": {"repository_ledger": True, "within_14_days_of_freeze": True},
        "code": {"files_sha256": doctor.code_file_hashes()},
        "preregistrations": {"v2": {"ledger": {"frozen": True, "row_hash": row_hash}}},
        "results": {
            "tarball": {"sha256": v2.TARBALL_SHA256},
            "tarball_scan": {
                "feature_file_sha256": hashlib.sha256(features.read_bytes()).hexdigest()
            },
        },
    }
    for path, value in changes.items():
        *parents, leaf = path.split("__")
        node = receipt
        for key in parents:
            node = node[key]
        node[leaf] = value
    return receipt


def test_trajectory_features_need_the_confirmatory_scan_that_wrote_them(
    tmp_path, monkeypatch
) -> None:
    """Audit blocking defect 2: any JSON passed as --trajectory-features could
    yield a CONFIRMATORY v2 receipt."""
    monkeypatch.setattr(doctor, "_git_ok", lambda *command: True)
    monkeypatch.setattr(doctor, "REPOSITORY_LEDGER", PROJECT_ROOT / "program" / "x.jsonl")
    features = tmp_path / "features.json"
    features.write_text('{"features": {}}')
    row_hash = "r" * 64
    state = {
        "ledger": {
            "frozen": True,
            "frozen_at": datetime.now(UTC).isoformat(),
            "git_head_at_freeze": "a" * 40,
            "row_hash": row_hash,
        }
    }

    def check(receipt: dict | None, **args) -> bool:
        path = None
        if receipt is not None:
            path = tmp_path / f"scan-{len(list(tmp_path.iterdir()))}.json"
            path.write_text(json.dumps(receipt))
        namespace = argparse.Namespace(
            ledger=PROJECT_ROOT / "program" / "x.jsonl",
            stage="v2",
            trajectory_features=features,
            tarball_receipt=path,
            **args,
        )
        checks = doctor.confirmatory_checks(namespace, state, uses_trajectories=True)
        return checks["trajectory_features_from_confirmatory_scan"]

    assert check(_scan_receipt(features, row_hash)) is True
    assert check(None) is False
    for change in (
        {"label": "v2 NON-CONFIRMATORY"},
        {"stage": "v2"},
        {"status": "FAIL"},
        {"doctor": "other"},
        {"confirmatory_checks__within_14_days_of_freeze": False},
        {"confirmatory_checks": {}},
        {"code__files_sha256": {"scripts/run_holo3_rerun_audit_doctor.py": "0" * 64}},
        {"preregistrations__v2__ledger__row_hash": "s" * 64},
        {"results__tarball__sha256": "0" * 64},
        {"results__tarball_scan__feature_file_sha256": "0" * 64},
    ):
        assert check(_scan_receipt(features, row_hash, **change)) is False, change
    del_scan = _scan_receipt(features, row_hash)
    del del_scan["results"]["tarball_scan"]
    assert check(del_scan) is False
    garbage = tmp_path / "garbage.json"
    garbage.write_text("not json")
    namespace = argparse.Namespace(
        ledger=PROJECT_ROOT / "program" / "x.jsonl",
        stage="v2",
        trajectory_features=features,
        tarball_receipt=garbage,
    )
    checks = doctor.confirmatory_checks(namespace, state, uses_trajectories=True)
    assert checks["trajectory_features_from_confirmatory_scan"] is False
    # No feature file, or another stage: no provenance condition.
    namespace.trajectory_features = None
    assert "trajectory_features_from_confirmatory_scan" not in doctor.confirmatory_checks(
        namespace, state, uses_trajectories=False
    )


def _repository_conditions_hold(monkeypatch) -> None:
    """Make the repository-only run conditions true; leave provenance computed."""
    real = doctor.confirmatory_checks

    def checks(args, state, *, uses_trajectories):
        out = real(args, state, uses_trajectories=uses_trajectories)
        for key in (
            "repository_ledger",
            "ledger_committed_and_unmodified",
            "code_unchanged_since_freeze",
            "within_14_days_of_freeze",
        ):
            if key in out:
                out[key] = True
        return out

    monkeypatch.setattr(doctor, "confirmatory_checks", checks)


def test_a_forged_feature_file_does_not_yield_a_confirmatory_receipt(
    tmp_path, synthetic, monkeypatch
) -> None:
    world, factory = synthetic
    monkeypatch.setattr(v2, "REGISTERED_H_REFERENCE", synthetic_h_reference(world))
    freeze_v2(tmp_path, monkeypatch)
    _repository_conditions_hold(monkeypatch)
    m, _, _ = synthetic_matrix(world)
    clean = doctor.clean_tasks(m)
    forged = feature_file(world, tmp_path, probed=set(), capped=set(clean))  # every run2 at 100
    code, receipt = run(tmp_path, factory, "--stage", "v2", "--trajectory-features", str(forged))
    assert code == 0, receipt["cases"]
    assert receipt["confirmatory_checks"]["trajectory_features_from_confirmatory_scan"] is False
    assert receipt["label"] == "v2 NON-CONFIRMATORY"


def _synthetic_tarball(world) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:

        def add(name: str, data: bytes) -> None:
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))

        for run, scores in (("run1", world.run1), ("run2", world.run2), ("repair", world.run1)):
            for t, score in scores.items():
                if score is None:
                    continue
                trajectory = world_mod.trajectory_id(t, run)
                base = f"fsx/person/trajectories_x/{trajectory}"
                entries = []
                for i in range(12):
                    entries.append({"image": f"images/{i:04d}.png"})
                    entries.append({"reasoning": "r", "action": {"tool_name": "click"}})
                add(f"{base}/actions.json", json.dumps(entries).encode())
                for i in range(2):
                    add(f"{base}/images/{i:04d}.png", bytes([i]) * 8)
        add("fsx/person/README.txt", b"ignore")
    return buffer.getvalue()


def _register_synthetic_tarball(world, monkeypatch) -> None:
    world.tarball = _synthetic_tarball(world)
    monkeypatch.setattr(v2, "TARBALL_SIZE", len(world.tarball))
    monkeypatch.setattr(v2, "TARBALL_CRC32", zlib.crc32(world.tarball) & 0xFFFFFFFF)
    monkeypatch.setattr(v2, "TARBALL_SHA256", hashlib.sha256(world.tarball).hexdigest())


def test_v2_tarball_checks_the_registered_literals_before_downloading(
    tmp_path, synthetic, monkeypatch
) -> None:
    """Audit note: section 1's size, CRC-32 and SHA-256 were not asserted in code."""
    _, factory = synthetic
    freeze_v2(tmp_path, monkeypatch)
    tar_dir = tmp_path / "tar"
    code, receipt = run(
        tmp_path,
        factory,
        "--stage",
        "v2-tarball",
        "--allow-large-download",
        "--tarball-dir",
        str(tar_dir),
    )
    assert code == 2 and receipt["status"] == "INFRA_ERROR"
    assert receipt["error"]["type"] == "ZipIntegrityError"
    assert "registered literals" in receipt["error"]["message"]
    assert not tar_dir.exists()  # nothing fetched


def test_the_confirmatory_chain_from_tarball_scan_to_v2(tmp_path, synthetic, monkeypatch) -> None:
    world, factory = synthetic
    monkeypatch.setattr(v2, "REGISTERED_H_REFERENCE", synthetic_h_reference(world))
    _register_synthetic_tarball(world, monkeypatch)
    freeze_v2(tmp_path, monkeypatch)
    _repository_conditions_hold(monkeypatch)
    tar_dir = tmp_path / "tar"
    scan_out = tmp_path / "scan"
    scan_out.mkdir()
    (scan_out / "ledger.jsonl").write_bytes((tmp_path / "ledger.jsonl").read_bytes())
    code, scan = run(
        scan_out,
        factory,
        "--stage",
        "v2-tarball",
        "--allow-large-download",
        "--tarball-dir",
        str(tar_dir),
    )
    assert code == 0, scan
    assert scan["label"] == "v2 CONFIRMATORY"
    assert scan["cases"]["feature_file_public_safety"]["status"] == "PASS"
    layout = scan["results"]["tarball_scan"]["layout"]
    assert layout["actions_members"] == layout["trajectories_with_actions"] > 700
    assert layout["image_members"] == 2 * layout["actions_members"]
    assert layout["other_file_members"] == 1
    features = tar_dir / "trajectory_features.json"
    text = features.read_text()
    assert "fsx" not in text and "person" not in text
    digest = hashlib.sha256(features.read_bytes()).hexdigest()
    assert scan["results"]["tarball_scan"]["feature_file_sha256"] == digest

    code, receipt = run(
        tmp_path,
        factory,
        "--stage",
        "v2",
        "--trajectory-features",
        str(features),
        "--tarball-receipt",
        str(scan_out / "receipt.json"),
    )
    assert code == 0, receipt["cases"]
    assert receipt["confirmatory_checks"]["trajectory_features_from_confirmatory_scan"] is True
    assert receipt["label"] == "v2 CONFIRMATORY"
    abc = receipt["results"]["v2"]["rules_abc"]
    assert abc["rule_c_coverage"]["coverage_ok"] is True
    assert abc["rule_b_screenshots"]["joined_episodes_with_screenshots"] > 700
    decisions = receipt["results"]["v2"]["decisions"]
    assert decisions["rule_d_blinding"] == v2.RULE_D_BLINDING_NOTE
    assert decisions["rule_d_evidence"] in ("CONFIRMATORY",) or decisions[
        "rule_d_evidence"
    ].startswith("EXPLORATORY")
    assert "rule_a_robust_to_concordant_tasks" in decisions
    assert (
        receipt["inputs"]["tarball_receipt_sha256"]
        == hashlib.sha256((scan_out / "receipt.json").read_bytes()).hexdigest()
    )


def test_a_feature_file_that_fails_public_safety_is_not_written(
    tmp_path, synthetic, monkeypatch
) -> None:
    """Audit note: tool names come from the data, so the feature file is scanned too."""
    world, factory = synthetic
    _register_synthetic_tarball(world, monkeypatch)
    freeze_v2(tmp_path, monkeypatch)
    real = v2.TrajectoryFeatures.public

    def leaky(self):
        out = real(self)
        out["tools"] = {f"ws://{world_mod.FAKE_PRIVATE_IP}:9222": 1}
        return out

    monkeypatch.setattr(v2.TrajectoryFeatures, "public", leaky)
    tar_dir = tmp_path / "tar"
    code, receipt = run(
        tmp_path,
        factory,
        "--stage",
        "v2-tarball",
        "--allow-large-download",
        "--tarball-dir",
        str(tar_dir),
    )
    assert code == 1 and receipt["status"] == "FAIL"
    assert receipt["cases"]["feature_file_public_safety"]["status"] == "FAIL"
    assert not (tar_dir / "trajectory_features.json").exists()
    assert world_mod.FAKE_PRIVATE_IP not in (tmp_path / "receipt.json").read_text()


def test_v2_fails_a_control_when_its_configs_differ_from_v1s(
    tmp_path, synthetic, monkeypatch
) -> None:
    """Design decision 13: v2 reads configs at f7230379 because they equal v1's."""
    world, factory = synthetic
    monkeypatch.setattr(v2, "REGISTERED_H_REFERENCE", synthetic_h_reference(world))
    world.config_manifest = "0" * 64
    freeze_v2(tmp_path, monkeypatch)
    code, receipt = run(tmp_path, factory, "--stage", "v2")
    assert code == 1 and receipt["status"] == "FAIL"
    assert receipt["cases"]["v2_config_blobs_equal_v1"]["status"] == "FAIL"


def test_the_sha256sums_case_is_computed_not_asserted(tmp_path, synthetic, monkeypatch) -> None:
    """Audit finding: the SHA256SUMS case was hard-coded PASS."""
    _, factory = synthetic
    real = audit.load_verified_package

    def tampered(ctx):
        pkg = real(ctx)
        rel = next(iter(pkg.member_sha256))
        pkg.member_sha256[rel] = "0" * 64
        return pkg

    monkeypatch.setattr(audit, "load_verified_package", tampered)
    code, receipt = run(tmp_path, factory, "--skip-opencua")
    assert code == 1
    case = receipt["cases"]["verified_members_match_sha256sums"]
    assert case["status"] == "FAIL" and case["mismatched"] == 1
