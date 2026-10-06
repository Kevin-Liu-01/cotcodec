from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from harness.memory_trials.procedural_bank import (
    ProceduralSplitManifest,
    ProceduralTaskRef,
    seal_procedural_split_manifest,
)
from harness.memory_trials.procedural_induction import (
    CorrectnessDecision,
    CorrectnessReceipt,
    DeterministicGenerationConfig,
    ProcedureGenerationReceipt,
    ProcedureGenerationResponse,
    TrainTrajectoryRecord,
    TrajectoryEvent,
    canonical_jsonl,
    compile_procedural_induction,
    load_canonical_jsonl,
)
from harness.memory_trials.schema import canonical_json, sha256_text
from scripts.compile_reasoningbank_induction import main as compile_main


def _split() -> ProceduralSplitManifest:
    return seal_procedural_split_manifest(
        train=(
            ProceduralTaskRef(
                task_id="train-database-rotate",
                workflow_family_id="database-credential-rotation",
            ),
            ProceduralTaskRef(
                task_id="train-object-recover",
                workflow_family_id="object-version-recovery",
            ),
        ),
        dev=(
            ProceduralTaskRef(
                task_id="dev-certificate-renew",
                workflow_family_id="certificate-renewal",
            ),
        ),
        test=(
            ProceduralTaskRef(
                task_id="test-document-recover",
                workflow_family_id="document-history-recovery",
            ),
        ),
    )


def _correctness(
    *,
    task_id: str,
    trajectory_sha256: str,
    outcome: str,
    evaluator_id: str = "deterministic-fixture-evaluator-v1",
) -> CorrectnessReceipt:
    decision = CorrectnessDecision(
        outcome=outcome,
        score=1.0 if outcome == "success" else 0.0,
        details="sealed deterministic fixture decision",
    )
    unsigned = {
        "schema_version": "procedural-correctness-receipt-v1",
        "task_id": task_id,
        "trajectory_sha256": trajectory_sha256,
        "evaluator_id": evaluator_id,
        "evaluator_revision_sha256": "1" * 64,
        "evaluator_input_sha256": sha256_text(
            canonical_json(
                {"task_id": task_id, "trajectory_sha256": trajectory_sha256}
            )
        ),
        "decision": decision.model_dump(mode="json"),
        "evaluator_output_sha256": sha256_text(
            canonical_json(decision.model_dump(mode="json"))
        ),
    }
    return CorrectnessReceipt.model_validate(
        {**unsigned, "receipt_sha256": sha256_text(canonical_json(unsigned))}
    )


def _trajectory(
    task_id: str,
    family_id: str,
    *,
    query: str,
    outcome: str = "success",
    source_dataset_id: str = "sealed-fixture-v1",
    evaluator_id: str = "deterministic-fixture-evaluator-v1",
) -> TrainTrajectoryRecord:
    events = (
        TrajectoryEvent(sequence=0, kind="observation", content="task opened"),
        TrajectoryEvent(sequence=1, kind="action", content="performed safe action"),
        TrajectoryEvent(
            sequence=2, kind="final_response", content="verified final state"
        ),
    )
    trajectory_payload = {
        "schema_version": "procedural-train-trajectory-v1",
        "split": "train",
        "source_dataset_id": source_dataset_id,
        "source_dataset_revision": "fixture-revision-1",
        "source_dataset_receipt_sha256": "0" * 64,
        "task_id": task_id,
        "workflow_family_id": family_id,
        "query": query,
        "events": [event.model_dump(mode="json") for event in events],
        "outcome": outcome,
    }
    trajectory_sha256 = sha256_text(canonical_json(trajectory_payload))
    correctness = _correctness(
        task_id=task_id,
        trajectory_sha256=trajectory_sha256,
        outcome=outcome,
        evaluator_id=evaluator_id,
    )
    unsigned = {
        **trajectory_payload,
        "trajectory_sha256": trajectory_sha256,
        "correctness_receipt": correctness.model_dump(mode="json"),
    }
    return TrainTrajectoryRecord.model_validate(
        {**unsigned, "record_sha256": sha256_text(canonical_json(unsigned))}
    )


def _generation(
    trajectory: TrainTrajectoryRecord,
    procedures: tuple[str, ...],
    *,
    prompt_template_sha256: str = "2" * 64,
) -> ProcedureGenerationReceipt:
    decoding = DeterministicGenerationConfig(
        do_sample=False,
        temperature=0.0,
        top_p=1.0,
        seed=42,
        max_new_tokens=256,
    )
    response = ProcedureGenerationResponse(procedural_items=procedures)
    request_payload = {
        "task_id": trajectory.task_id,
        "trajectory_sha256": trajectory.trajectory_sha256,
        "prompt_template_sha256": prompt_template_sha256,
        "generator_model_receipt_sha256": "3" * 64,
        "generator_code_sha256": "4" * 64,
        "execution_kind": "contained-pinned-local-model",
        "decoding": decoding.model_dump(mode="json"),
    }
    response_sha256 = sha256_text(canonical_json(response.model_dump(mode="json")))
    unsigned = {
        "schema_version": "procedural-generation-receipt-v1",
        **request_payload,
        "request_sha256": sha256_text(canonical_json(request_payload)),
        "response": response.model_dump(mode="json"),
        "response_sha256": response_sha256,
        "repeat_response": response.model_dump(mode="json"),
        "repeat_response_sha256": response_sha256,
        "generation_attempts": 2,
        "api_calls": 0,
        "input_tokens": 80,
        "output_tokens": 20,
        "repeat_output_tokens": 20,
    }
    return ProcedureGenerationReceipt.model_validate(
        {**unsigned, "receipt_sha256": sha256_text(canonical_json(unsigned))}
    )


def _inputs() -> tuple[
    ProceduralSplitManifest,
    tuple[TrainTrajectoryRecord, ...],
    tuple[ProcedureGenerationReceipt, ...],
]:
    split = _split()
    trajectories = (
        _trajectory(
            "train-database-rotate",
            "database-credential-rotation",
            query="rotate a database credential safely",
        ),
        _trajectory(
            "train-object-recover",
            "object-version-recovery",
            query="recover an object from version history",
            outcome="failure",
        ),
    )
    generations = (
        _generation(
            trajectories[0],
            (
                "Confirm the role, rotate once, then verify a fresh login.",
                "Do not report success until the replacement credential is tested.",
            ),
        ),
        _generation(
            trajectories[1],
            ("Inspect version history before restoring a recovery copy.",),
        ),
    )
    return split, trajectories, generations


def _write_inputs(
    root: Path,
) -> tuple[ProceduralSplitManifest, Path, Path, tuple[TrainTrajectoryRecord, ...]]:
    split, trajectories, generations = _inputs()
    trajectory_path = root / "trajectories.jsonl"
    generation_path = root / "generations.jsonl"
    trajectory_path.write_bytes(canonical_jsonl(trajectories))
    generation_path.write_bytes(canonical_jsonl(generations))
    return split, trajectory_path, generation_path, trajectories


def test_compile_requires_exact_train_roster_and_is_deterministic(tmp_path: Path) -> None:
    split, trajectory_path, generation_path, _ = _write_inputs(tmp_path)
    first = compile_procedural_induction(
        trajectory_jsonl=trajectory_path,
        generation_jsonl=generation_path,
        split_manifest=split,
        expected_split_manifest_sha256=split.manifest_sha256,
    )
    second = compile_procedural_induction(
        trajectory_jsonl=trajectory_path,
        generation_jsonl=generation_path,
        split_manifest=split,
        expected_split_manifest_sha256=split.manifest_sha256,
    )
    assert first == second
    assert first.trajectory_count == 2
    assert first.generation_count == 2
    assert first.procedure_count == 3
    assert first.train_task_ids == (
        "train-database-rotate",
        "train-object-recover",
    )
    assert all(item.source_task_id.startswith("train-") for item in first.items)
    assert first.items[0].generator_receipt_sha256
    with pytest.raises(ValueError, match="externally registered digest"):
        compile_procedural_induction(
            trajectory_jsonl=trajectory_path,
            generation_jsonl=generation_path,
            split_manifest=split,
            expected_split_manifest_sha256="f" * 64,
        )


def test_compiler_rejects_missing_or_evaluation_task_rows(tmp_path: Path) -> None:
    split, trajectories, generations = _inputs()
    trajectory_path = tmp_path / "trajectories.jsonl"
    generation_path = tmp_path / "generations.jsonl"
    trajectory_path.write_bytes(canonical_jsonl(trajectories[:1]))
    generation_path.write_bytes(canonical_jsonl(generations))
    with pytest.raises(ValueError, match="exact TRAIN task roster"):
        compile_procedural_induction(
            trajectory_jsonl=trajectory_path,
            generation_jsonl=generation_path,
            split_manifest=split,
            expected_split_manifest_sha256=split.manifest_sha256,
        )

    evaluation = trajectories[0].model_dump(mode="json")
    evaluation["task_id"] = "dev-certificate-renew"
    evaluation["workflow_family_id"] = "certificate-renewal"
    evaluation["split"] = "dev"
    trajectory_path.write_text(canonical_json(evaluation) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="record failed validation"):
        load_canonical_jsonl(trajectory_path, TrainTrajectoryRecord)


def test_jsonl_loader_rejects_noncanonical_duplicate_keys_and_symlink(
    tmp_path: Path,
) -> None:
    _, trajectories, _ = _inputs()
    path = tmp_path / "trajectories.jsonl"
    payload = trajectories[0].model_dump(mode="json")
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="not canonical JSON"):
        load_canonical_jsonl(path, TrainTrajectoryRecord)

    path.write_text('{"task_id":"a","task_id":"b"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="invalid JSON"):
        load_canonical_jsonl(path, TrainTrajectoryRecord)

    path.write_bytes(canonical_jsonl(trajectories))
    link = tmp_path / "linked.jsonl"
    link.symlink_to(path)
    with pytest.raises(ValueError, match="cannot open JSONL input"):
        load_canonical_jsonl(link, TrainTrajectoryRecord)


def test_generation_receipt_rejects_stochastic_or_changed_replay() -> None:
    _, trajectories, generations = _inputs()
    payload = generations[0].model_dump(mode="json")
    payload["decoding"]["do_sample"] = True
    with pytest.raises(ValueError):
        ProcedureGenerationReceipt.model_validate(payload)

    payload = generations[0].model_dump(mode="json")
    payload["repeat_response"]["procedural_items"] = ["different replay output"]
    payload["repeat_response_sha256"] = sha256_text(
        canonical_json(payload["repeat_response"])
    )
    unsigned = {key: value for key, value in payload.items() if key != "receipt_sha256"}
    payload["receipt_sha256"] = sha256_text(canonical_json(unsigned))
    with pytest.raises(ValueError, match="replay drifted"):
        ProcedureGenerationReceipt.model_validate(payload)

    changed = _trajectory(
        trajectories[0].task_id,
        trajectories[0].workflow_family_id,
        query="a changed source query",
    )
    assert changed.trajectory_sha256 != trajectories[0].trajectory_sha256
    assert generations[0].trajectory_sha256 != changed.trajectory_sha256


def test_compiler_rejects_mixed_source_evaluator_and_generator_contracts(
    tmp_path: Path,
) -> None:
    split, trajectories, generations = _inputs()
    trajectory_path = tmp_path / "trajectories.jsonl"
    generation_path = tmp_path / "generations.jsonl"

    mixed_source = (
        trajectories[0],
        _trajectory(
            "train-object-recover",
            "object-version-recovery",
            query="recover an object from version history",
            outcome="failure",
            source_dataset_id="different-source",
        ),
    )
    trajectory_path.write_bytes(canonical_jsonl(mixed_source))
    rebound_generations = (
        generations[0],
        _generation(
            mixed_source[1],
            ("Inspect version history before restoring a recovery copy.",),
        ),
    )
    generation_path.write_bytes(canonical_jsonl(rebound_generations))
    with pytest.raises(ValueError, match="mixes source dataset contracts"):
        compile_procedural_induction(
            trajectory_jsonl=trajectory_path,
            generation_jsonl=generation_path,
            split_manifest=split,
            expected_split_manifest_sha256=split.manifest_sha256,
        )

    mixed_evaluator = (
        trajectories[0],
        _trajectory(
            "train-object-recover",
            "object-version-recovery",
            query="recover an object from version history",
            outcome="failure",
            evaluator_id="different-evaluator",
        ),
    )
    trajectory_path.write_bytes(canonical_jsonl(mixed_evaluator))
    generation_path.write_bytes(
        canonical_jsonl(
            (
                generations[0],
                _generation(
                    mixed_evaluator[1],
                    ("Inspect version history before restoring a recovery copy.",),
                ),
            )
        )
    )
    with pytest.raises(ValueError, match="mixes correctness evaluator contracts"):
        compile_procedural_induction(
            trajectory_jsonl=trajectory_path,
            generation_jsonl=generation_path,
            split_manifest=split,
            expected_split_manifest_sha256=split.manifest_sha256,
        )

    trajectory_path.write_bytes(canonical_jsonl(trajectories))
    generation_path.write_bytes(
        canonical_jsonl(
            (
                generations[0],
                _generation(
                    trajectories[1],
                    ("Inspect version history before restoring a recovery copy.",),
                    prompt_template_sha256="9" * 64,
                ),
            )
        )
    )
    with pytest.raises(ValueError, match="mixes generator contracts"):
        compile_procedural_induction(
            trajectory_jsonl=trajectory_path,
            generation_jsonl=generation_path,
            split_manifest=split,
            expected_split_manifest_sha256=split.manifest_sha256,
        )


def test_cli_compiles_once_and_refuses_overwrite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    split, trajectory_path, generation_path, _ = _write_inputs(tmp_path)
    split_path = tmp_path / "split.json"
    split_path.write_text(
        json.dumps(split.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    output = tmp_path / "induction.json"
    argv = [
        "compile_reasoningbank_induction.py",
        "--split-manifest",
        str(split_path),
        "--expected-split-manifest-sha256",
        split.manifest_sha256,
        "--trajectories",
        str(trajectory_path),
        "--generations",
        str(generation_path),
        "--output",
        str(output),
    ]
    monkeypatch.setattr(sys, "argv", argv)
    assert compile_main() == 0
    compiled = json.loads(output.read_text(encoding="utf-8"))
    assert compiled["procedure_count"] == 3
    with pytest.raises(FileExistsError):
        compile_main()
