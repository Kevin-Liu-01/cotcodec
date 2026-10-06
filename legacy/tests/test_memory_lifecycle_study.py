from __future__ import annotations

import copy
import hashlib
from collections import Counter
from pathlib import Path

import pytest

from harness.memory_trials.lifecycle import (
    LifecycleFeedback,
    ReferenceLifecyclePort,
    run_lifecycle_plan,
)
from harness.memory_trials.lifecycle_study import (
    LIFECYCLE_FAMILIES,
    MemoryLifecycleStudyError,
    compile_lifecycle_matrix,
    compile_restore_plan,
    evaluate_lifecycle_case,
)
from harness.memory_trials.schema import canonical_json, sha256_text
from scripts import run_memory_lifecycle_contract as runner
from scripts.validate_memory_lifecycle_experiment import EXPECTED_CONTRACT


def test_registered_matrix_is_deterministic_balanced_and_task_blind() -> None:
    first = compile_lifecycle_matrix()
    second = compile_lifecycle_matrix()
    assert len(first) == 192
    assert [case.case_sha256 for case in first] == [case.case_sha256 for case in second]
    assert Counter(case.active_slots for case in first) == {4: 64, 2: 64, 8: 64}
    assert Counter(case.family for case in first) == {
        family: 48 for family in LIFECYCLE_FAMILIES
    }
    for case in first:
        assert sum(command.kind == "query" for command in case.plan.commands) == 2
        plan_text = canonical_json(case.plan.model_dump(mode="json"))
        assert '"oracle"' not in plan_text
        assert '"expected_first_record_ids"' not in plan_text
        assert '"expected_second_record_ids"' not in plan_text
        assert '"expected_first_prior_residency"' not in plan_text
        assert '"expected_second_prior_residency"' not in plan_text
        assert '"required_second_lineage"' not in plan_text
        assert '"deleted_record_id"' not in plan_text
        assert '"rewarded_record_id"' not in plan_text
        assert '"future_' not in plan_text


@pytest.mark.parametrize("active_slots", [2, 4, 8])
def test_every_family_passes_oracle_and_fresh_reference_restore(
    active_slots: int,
) -> None:
    cases = compile_lifecycle_matrix(
        episodes_per_slot_cell=4,
        active_slot_cells=(active_slots,),
    )
    for case in cases:
        trace = run_lifecycle_plan(
            ReferenceLifecyclePort(active_slots=active_slots), case.plan
        )
        restore_plan = compile_restore_plan(case, trace)
        restored = run_lifecycle_plan(
            ReferenceLifecyclePort(active_slots=active_slots), restore_plan
        )
        result = evaluate_lifecycle_case(case, trace, restored_trace=restored)
        assert all(result["gates"].values())


def test_restore_from_another_case_cannot_satisfy_suffix_gate() -> None:
    cases = compile_lifecycle_matrix(episodes_per_slot_cell=8, active_slot_cells=(4,))
    first, second = cases[0], cases[1]
    first_trace = run_lifecycle_plan(ReferenceLifecyclePort(active_slots=4), first.plan)
    second_trace = run_lifecycle_plan(ReferenceLifecyclePort(active_slots=4), second.plan)
    with pytest.raises(MemoryLifecycleStudyError, match="fresh_process_restore_exact"):
        evaluate_lifecycle_case(first, first_trace, restored_trace=second_trace)


def test_feedback_requires_nonempty_unique_used_records() -> None:
    common = {
        "feedback_id": "feedback-test",
        "step": 1,
        "outcome_receipt_sha256": sha256_text("outcome"),
        "reward": 1.0,
    }
    with pytest.raises(ValueError, match="at least one"):
        LifecycleFeedback(**common, used_record_ids=())
    with pytest.raises(ValueError, match="must be unique"):
        LifecycleFeedback(**common, used_record_ids=("record-a", "record-a"))


def test_sealed_output_recomputes_and_rejects_roster_or_byte_tamper(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mini_contract = copy.deepcopy(EXPECTED_CONTRACT)
    mini_contract["source"]["episodes_per_active_slot_cell"] = 4
    mini_contract["source"]["total_trace_count"] = 4
    mini_contract["source"]["cases_per_family_per_cell"] = 1
    mini_contract["budget"]["diagnostic_active_slots"] = []
    experiment_path = tmp_path / "mini-lifecycle.yaml"
    experiment_bytes = b"mini lifecycle contract fixture\n"
    experiment_path.write_bytes(experiment_bytes)

    def load_mini(path: Path) -> tuple[dict[str, object], str]:
        encoded = path.read_bytes()
        return mini_contract, hashlib.sha256(encoded).hexdigest()

    monkeypatch.setattr(runner, "load_and_validate_experiment", load_mini)
    result = runner.run_contract(experiment_path)
    output = tmp_path / "sealed"
    sealed = runner.seal_output(output, result)
    assert sealed["status"] == "SEALED_LIFECYCLE_REFERENCE_CONTRACT"
    assert runner.load_and_validate_output(output)["manifest_sha256"] == sealed[
        "manifest_sha256"
    ]
    with pytest.raises(runner.LifecycleRunError, match="must not already exist"):
        runner.seal_output(output, result)

    extra = output / "unregistered.txt"
    extra.write_text("not evidence\n")
    with pytest.raises(runner.LifecycleRunError, match="file roster drifted"):
        runner.load_and_validate_output(output)
    extra.unlink()
    runner.load_and_validate_output(output)

    report = output / "report.json"
    report.write_text("{}\n")
    with pytest.raises(runner.LifecycleRunError, match="does not bind current bytes"):
        runner.load_and_validate_output(output)
