from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

from harness.memory_trials import (
    FrozenMemoryBundleError,
    FrozenMemorySystem,
    GeneratedMemoryTaskSource,
    LongMemEvalTaskSource,
    NoMemorySystem,
    PersistentSubprocessMemorySystem,
    ReferenceMemorySystem,
    run_memory_system,
    task_manifest_sha256,
)
from harness.memory_trials.schema import canonical_json
from scripts.freeze_memory_system_outputs import (
    _make_system,
    compile_bundle,
    write_validated_bundle,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _bundle(tmp_path):
    source = GeneratedMemoryTaskSource(seed=7, episode_count=4)
    payload = compile_bundle(
        ReferenceMemorySystem(),
        source,
        treatment_modes=("storage_and_service", "serve_only"),
    )
    path = tmp_path / "frozen.json"
    frozen = write_validated_bundle(
        path,
        payload,
        source=source,
        treatment_modes=("storage_and_service", "serve_only"),
    )
    return source, path, frozen


def test_freezer_can_reuse_one_persistent_sidecar_process() -> None:
    command = json.dumps(
        [sys.executable, str(PROJECT_ROOT / "scripts/run_reference_memory_sidecar.py")]
    )
    system = _make_system(None, command, {}, persistent_sidecar=True)
    try:
        assert isinstance(system, PersistentSubprocessMemorySystem)
        assert system.is_running
    finally:
        system.close()


def test_freezer_purges_persistent_state_before_each_counterfactual() -> None:
    source = GeneratedMemoryTaskSource(seed=7, episode_count=1)
    reference = ReferenceMemorySystem()

    class StateIsolatedSystem:
        receipt = reference.receipt

        def __init__(self) -> None:
            self.active_scope = None
            self.purged: list[str] = []

        def purge(self, session_scope: str) -> None:
            self.active_scope = None
            self.purged.append(session_scope)

        def select(self, request):
            if self.active_scope is not None:
                raise AssertionError("counterfactual request inherited sidecar state")
            self.active_scope = request.session_scope
            return reference.select(request)

    system = StateIsolatedSystem()
    payload = compile_bundle(
        system,
        source,
        treatment_modes=("storage_and_service", "serve_only"),
    )
    assert len(payload["entries"]) == 2
    # Two unique requests are isolated, followed by one final cleanup purge.
    assert system.purged == [source.load(source.ids()[0]).session_id] * 3


def test_frozen_bundle_replays_exact_native_selection(tmp_path) -> None:
    source, _path, frozen = _bundle(tmp_path)
    assert frozen.metadata["selection_count"] == 8
    assert frozen.receipt.implementation_kind == "frozen_selection_bundle"
    frozen.require_compatible(
        source_provenance=source.provenance,
        budget=source.budget.model_dump(mode="json"),
        treatment_mode="storage_and_service",
        exact_task_manifest_sha256=task_manifest_sha256(source),
    )

    task = source.load("memory-000001")
    first = run_memory_system(
        frozen,
        task,
        visibility="serve",
        treatment_mode="storage_and_service",
    )
    repeated = run_memory_system(
        frozen,
        task,
        visibility="serve",
        treatment_mode="storage_and_service",
    )
    assert first == repeated
    assert first.receipt.configuration_sha256 == frozen.receipt.configuration_sha256


def test_frozen_bundle_rejects_tampering(tmp_path) -> None:
    _source, path, _frozen = _bundle(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["entries"][0]["selection"]["evidence"][0]["text"] = "tampered"
    path.write_text(canonical_json(payload) + "\n", encoding="utf-8")
    with pytest.raises(FrozenMemoryBundleError, match="digest mismatch"):
        FrozenMemorySystem(path)


def test_frozen_bundle_rejects_source_or_mode_drift(tmp_path) -> None:
    source, _path, frozen = _bundle(tmp_path)
    with pytest.raises(FrozenMemoryBundleError, match="treatment mode"):
        frozen.require_compatible(
            source_provenance=source.provenance,
            budget=source.budget.model_dump(mode="json"),
            treatment_mode="unknown",
            exact_task_manifest_sha256=task_manifest_sha256(source),
        )
    changed_source = {**source.provenance, "seed": 8}
    with pytest.raises(FrozenMemoryBundleError, match="differs at field: seed"):
        frozen.require_compatible(
            source_provenance=changed_source,
            budget=source.budget.model_dump(mode="json"),
            treatment_mode="serve_only",
            exact_task_manifest_sha256=task_manifest_sha256(source),
        )
    with pytest.raises(FrozenMemoryBundleError, match="task manifest"):
        frozen.require_compatible(
            source_provenance=source.provenance,
            budget=source.budget.model_dump(mode="json"),
            treatment_mode="serve_only",
            exact_task_manifest_sha256="0" * 64,
        )


def test_frozen_bundle_rejects_symlinked_output_root(tmp_path: Path) -> None:
    source = GeneratedMemoryTaskSource(seed=7, episode_count=1)
    payload = compile_bundle(
        NoMemorySystem(), source, treatment_modes=("storage_and_service",)
    )
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError, match="symbolic links"):
        write_validated_bundle(
            link / "bundle.json",
            payload,
            source=source,
            treatment_modes=("storage_and_service",),
        )


def test_frozen_bundle_supports_content_addressed_public_source(tmp_path) -> None:
    rows = [
        {
            "question_id": "public-freeze-001",
            "question_type": "multi-session",
            "question": "What city was mentioned?",
            "answer": "Princeton",
            "question_date": "2026/01/02 (Fri) 10:00",
            "haystack_session_ids": ["session-1"],
            "haystack_dates": ["2026/01/01 (Thu) 10:00"],
            "haystack_sessions": [
                [
                    {"role": "user", "content": "I moved to Princeton."},
                    {"role": "assistant", "content": "Noted."},
                ]
            ],
            "answer_session_ids": ["session-1"],
        }
    ]
    encoded = json.dumps(rows, sort_keys=True).encode()
    dataset = tmp_path / "longmemeval.json"
    dataset.write_bytes(encoded)
    source = LongMemEvalTaskSource(
        dataset,
        expected_sha256=hashlib.sha256(encoded).hexdigest(),
        expected_size=len(encoded),
        dataset_revision="1" * 40,
    )
    payload = compile_bundle(
        NoMemorySystem(),
        source,
        treatment_modes=("storage_and_service",),
    )
    frozen = write_validated_bundle(
        tmp_path / "public-frozen.json",
        payload,
        source=source,
        treatment_modes=("storage_and_service",),
    )
    frozen.require_compatible(
        source_provenance=source.provenance,
        budget=source.budget.model_dump(mode="json"),
        treatment_mode="storage_and_service",
        exact_task_manifest_sha256=task_manifest_sha256(source),
    )
    assert frozen.metadata["selection_count"] == 2
