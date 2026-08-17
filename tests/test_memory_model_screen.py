from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import pytest

from harness.memory_trials import (
    DenseBGERetrievalMemorySystem,
    DenseEmbeddingIdentity,
    FrozenMemorySystem,
    GeneratedMemoryTaskSource,
    InProcessDenseEmbeddingClient,
    ReplayableMemoryWorld,
    task_manifest_sha256,
)
from harness.memory_trials.schema import canonical_json, sha256_text
from scripts.compile_memory_public_docker_job import CONTROL_SYSTEMS
from scripts.freeze_memory_control_matrix import freeze_control_matrix
from scripts.run_memory_model_screen import (
    PUBLICATION_BATCH_SCRIPT,
    _load_publication_admission,
    aa_repeatability,
    run_screen,
)


class _DenseEncoder:
    dimensions = 384
    maximum_tokens = 512
    pooling_strategy = "cls-l2-normalized-v1"

    def embed(self, texts: Sequence[str]) -> tuple[list[list[float]], int]:
        return [[1.0, *([0.0] * 383)] for _ in texts], len(texts)


def _dense_system() -> DenseBGERetrievalMemorySystem:
    identity = DenseEmbeddingIdentity(
        artifact_root_sha256="1" * 64,
        model_receipt_sha256="2" * 64,
    )
    return DenseBGERetrievalMemorySystem(
        InProcessDenseEmbeddingClient(_DenseEncoder(), identity)
    )


def test_model_screen_aa_repeatability_ignores_receipt_timing() -> None:
    source = GeneratedMemoryTaskSource(seed=7, episode_count=4)
    report = aa_repeatability(ReplayableMemoryWorld(source), source.ids())
    assert report["trials"] == 4
    assert report["exact_rate"] == 1.0
    assert all(row["match"] for row in report["rows"])


def test_model_screen_summary_reports_every_memory_stratum(tmp_path) -> None:
    from harness.causal_memory_trials import TrialPlan
    from harness.memory_trials import collect_resumable
    from scripts.run_memory_model_screen import summarize_screen
    from scripts.run_memory_trials import ALLOWED_FEATURES, audit_ids

    source = GeneratedMemoryTaskSource(seed=7, episode_count=80)
    trial_ids = source.ids()
    plan = TrialPlan(
        study_id="stratum-summary",
        trial_ids=trial_ids,
        allowed_features=ALLOWED_FEATURES,
        paired_audit_ids=audit_ids(trial_ids, assignment_seed=42, fraction=0.25),
        propensity=0.5,
        assignment_seed=42,
        minimum_effective_sample_size=2,
        minimum_arm_effective_sample_size=1,
    )
    collection = collect_resumable(
        plan,
        ReplayableMemoryWorld(source),
        tmp_path / "run",
    )
    assert collection.bundle is not None
    metrics = summarize_screen(collection.bundle)
    assert set(metrics["by_stratum"]) == {
        "active_core",
        "inactive_archive",
        "temporal_graph",
        "proactive_tool",
    }
    assert all(cell["episodes"] == 20 for cell in metrics["by_stratum"].values())


def test_model_transport_requires_registered_explicit_model(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="requires an explicit model id"):
        run_screen(
            Path("experiments/memory/stage1-model-transport.yaml"),
            tmp_path / "screen",
        )


def test_full_prefix_budget_requires_diagnostic_evaluation(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="requires diagnostic-ceiling"):
        run_screen(
            Path("experiments/memory/stage1-model-transport.yaml"),
            tmp_path / "screen",
            model_id_override="qwen3.5-4b",
            memory_bundle=tmp_path / "not-opened.json",
            memory_budget_profile="full-prefix-diagnostic",
            evaluation_mode="matrix-cell",
        )


def test_publication_admission_binds_matrix_cell_and_resume_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = GeneratedMemoryTaskSource(seed=7, episode_count=4)
    matrix_root = tmp_path / "matrix"
    matrix = freeze_control_matrix(
        matrix_root,
        source=source,
        system_ids=CONTROL_SYSTEMS,
        dense_system=_dense_system(),
    )
    control = next(row for row in matrix["controls"] if row["control_id"] == "bm25")
    frozen = FrozenMemorySystem(matrix_root / control["bundle_path"])
    capsule_unsigned = {
        "schema_version": 2,
        "status": "SEALED_PUBLICATION_CAPSULE_CANDIDATE",
        "publication_ready": False,
        "publication_gate": "administrator signature required",
        "source": {
            "git_sha": "a" * 40,
            "archive_sha256": "b" * 64,
        },
        "image": {"image_id": "sha256:" + "c" * 64},
        "sbom": {"sha256": "d" * 64},
        "runtime": {
            "batch_script_sha256": __import__("hashlib")
            .sha256(PUBLICATION_BATCH_SCRIPT.read_bytes())
            .hexdigest()
        },
    }
    capsule = {
        **capsule_unsigned,
        "capsule_sha256": sha256_text(canonical_json(capsule_unsigned)),
    }
    capsule_path = tmp_path / "capsule.json"
    capsule_path.write_text(json.dumps(capsule), encoding="utf-8")
    attestation_receipt = {
        "schema_version": 2,
        "status": "PUBLICATION_CLAIM_ATTESTATION_VERIFIED",
        "bindings": {},
        "attestation_file_sha256": "1" * 64,
        "trust_store_sha256": "2" * 64,
        "key_id": "publication-ci-1",
    }
    monkeypatch.setattr(
        "scripts.run_memory_model_screen.verify_publication_claim_attestation",
        lambda **_kwargs: attestation_receipt,
    )
    registered_actor_contract = {"dtype": "bfloat16", "decoding": {"max": 64}}
    wave_unsigned = {
        "schema_version": 2,
        "scope": "test",
        "publication_capsule_sha256": capsule["capsule_sha256"],
        "publication_capsule_file_sha256": __import__("hashlib")
        .sha256(capsule_path.read_bytes())
        .hexdigest(),
        "publication_trust_store_sha256": "2" * 64,
        "control_matrix_sha256": matrix["matrix_sha256"],
        "control_matrix_file_sha256": __import__("hashlib")
        .sha256((matrix_root / "manifest.json").read_bytes())
        .hexdigest(),
        "experiment_sha256": __import__("hashlib")
        .sha256(Path("experiments/memory/stage1-longmemeval-screen.yaml").read_bytes())
        .hexdigest(),
        "batch_script_sha256": __import__("hashlib")
        .sha256(PUBLICATION_BATCH_SCRIPT.read_bytes())
        .hexdigest(),
        "model_id": "test-model",
        "model_revision": "3" * 40,
        "model_receipt_sha256": "4" * 64,
        "model_artifact_root_sha256": "5" * 64,
        "registered_actor_contract": registered_actor_contract,
        "command_schema": "longmemeval-publication-actor-all-serve-v2",
        "eligible_controls": [
            {
                "control_id": row["control_id"],
                "system_id": row["system_id"],
                "bundle_semantic_sha256": row["bundle_semantic_sha256"],
                "bundle_file_sha256": row["bundle_file_sha256"],
            }
            for row in sorted(matrix["controls"], key=lambda item: item["control_id"])
            if row["eligible_for_primary"] is True
        ],
    }
    wave = {
        **wave_unsigned,
        "wave_sha256": sha256_text(canonical_json(wave_unsigned)),
    }
    wave_path = tmp_path / "wave.json"
    wave_path.write_text(json.dumps(wave), encoding="utf-8")
    admission = _load_publication_admission(
        capsule_path=capsule_path,
        attestation_path=tmp_path / "attestation.json",
        trust_store_path=tmp_path / "trust.json",
        expected_trust_store_sha256="2" * 64,
        matrix_path=matrix_root / "manifest.json",
        experiment_path=Path("experiments/memory/stage1-longmemeval-screen.yaml"),
        wave_path=wave_path,
        expected_wave_sha256=wave["wave_sha256"],
        expected_control_id="bm25",
        expected_system_id=control["system_id"],
        frozen_memory=frozen,
        exact_task_manifest_sha256=task_manifest_sha256(source),
        model_id="test-model",
        model_revision="3" * 40,
        model_receipt_sha256="4" * 64,
        model_artifact_root_sha256="5" * 64,
        registered_actor_contract=registered_actor_contract,
    )
    assert admission["matrix_sha256"] == matrix["matrix_sha256"]
    assert admission["memory_bundle_semantic_sha256"] == frozen.bundle_sha256

    drifted = dict(matrix)
    drifted["controls"] = [
        {
            **control,
            "bundle_sha256": "0" * 64,
            "bundle_semantic_sha256": "0" * 64,
        }
    ]
    unsigned = {key: value for key, value in drifted.items() if key != "matrix_sha256"}
    drifted["matrix_sha256"] = sha256_text(canonical_json(unsigned))
    drifted_path = tmp_path / "matrix-drifted.json"
    drifted_path.write_text(json.dumps(drifted), encoding="utf-8")
    with pytest.raises(
        ValueError,
        match=(
            "publication wave provenance differs|differs from its primary matrix cell|"
            "roster is incomplete"
        ),
    ):
        _load_publication_admission(
            capsule_path=capsule_path,
            attestation_path=tmp_path / "attestation.json",
            trust_store_path=tmp_path / "trust.json",
            expected_trust_store_sha256="2" * 64,
            matrix_path=drifted_path,
            experiment_path=Path("experiments/memory/stage1-longmemeval-screen.yaml"),
            wave_path=wave_path,
            expected_wave_sha256=wave["wave_sha256"],
            expected_control_id="bm25",
            expected_system_id=control["system_id"],
            frozen_memory=frozen,
            exact_task_manifest_sha256=task_manifest_sha256(source),
            model_id="test-model",
            model_revision="3" * 40,
            model_receipt_sha256="4" * 64,
            model_artifact_root_sha256="5" * 64,
            registered_actor_contract=registered_actor_contract,
        )
