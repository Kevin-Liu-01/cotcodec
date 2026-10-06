from __future__ import annotations

import base64
import hashlib
import json
from collections.abc import Sequence
from pathlib import Path

import pytest
import yaml
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from harness.memory_trials import (
    DenseBGERetrievalMemorySystem,
    DenseEmbeddingIdentity,
    GeneratedMemoryTaskSource,
    InProcessDenseEmbeddingClient,
)
from harness.memory_trials.schema import canonical_json, sha256_text
from harness.publication_attestation import (
    publication_claim_bindings,
    publication_claim_message,
)
from scripts.compile_memory_public_docker_job import CONTROL_SYSTEMS
from scripts.compile_memory_publication_wave import (
    compile_publication_wave,
    preview_publication_wave,
)
from scripts.freeze_memory_control_matrix import freeze_control_matrix
from scripts.submit_docker_research_job import BATCH_SCRIPT, validate_manifest


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def _inputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    tmp_path.mkdir(parents=True, exist_ok=True)
    capsule_unsigned = {
        "schema_version": 2,
        "status": "SEALED_PUBLICATION_CAPSULE_CANDIDATE",
        "publication_ready": False,
        "publication_gate": "administrator signature required",
        "source": {
            "git_sha": "b" * 40,
            "archive_sha256": "c" * 64,
        },
        "image": {
            "image_id": "sha256:" + "a" * 64,
            "repo_digests": ["registry/cotcodec@sha256:" + "d" * 64],
        },
        "sbom": {"sha256": "e" * 64},
        "runtime": {"batch_script_sha256": _sha(BATCH_SCRIPT)},
    }
    capsule = {
        **capsule_unsigned,
        "capsule_sha256": sha256_text(canonical_json(capsule_unsigned)),
    }
    capsule_path = tmp_path / "capsule.json"
    capsule_path.write_text(json.dumps(capsule), encoding="utf-8")
    trust_root = tmp_path / "protected-trust"
    trust_root.mkdir()
    trust_store = trust_root / "publication-attestors.json"
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    trust_store.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "status": "TRUSTED_PUBLICATION_ATTESTORS",
                "keys": [
                    {
                        "key_id": "publication-ci-1",
                        "algorithm": "ed25519",
                        "roles": ["publication-claim"],
                        "public_key_base64": base64.b64encode(public).decode(),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    trust_store.chmod(0o600)
    monkeypatch.setattr("harness.publication_attestation.PUBLICATION_TRUST_ROOT", trust_root)
    monkeypatch.setattr("harness.publication_attestation.os.geteuid", lambda: -1)
    matrix_root = tmp_path / "matrix"
    matrix = freeze_control_matrix(
        matrix_root,
        source=GeneratedMemoryTaskSource(seed=7, episode_count=500),
        system_ids=CONTROL_SYSTEMS,
        dense_system=_dense_system(),
    )
    matrix["task_source"] = {
        "dataset_revision": "98d7416c24c778c2fee6e6f3006e7a073259d48f",
        "dataset_sha256": "d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442",
        "dataset_size": 277_383_467,
        "dataset_license": "MIT",
        "adapter_version": "longmemeval-full-haystack-retrieval-v3",
        "artifact_role": "full-haystack-retrieval",
        "candidate_seed": 42,
        "task_count": 500,
        "task_selection": "all-tasks",
        "task_manifest_sha256": (
            "0c5a55a7aeeb492410031560ef71585e83a6f594fffdef1bd7a9b59ce1119c9d"
        ),
        "budget": {
            "active_slots": 4,
            "max_archive_reads": 1,
            "retrieval_top_k": 4,
            "max_injected_tokens": 256,
        },
    }
    matrix["event_kind_counts"] = {}
    for control in matrix["controls"]:
        if control["control_id"] == "lru":
            control["eligible_for_primary"] = False
            control["ineligibility_reason"] = "benchmark-has-no-explicit-access-events"
    matrix_unsigned = {key: value for key, value in matrix.items() if key != "matrix_sha256"}
    matrix["matrix_sha256"] = sha256_text(canonical_json(matrix_unsigned))
    (matrix_root / "manifest.json").write_text(json.dumps(matrix), encoding="utf-8")
    preview = preview_publication_wave(
        publication_capsule_path=capsule_path,
        control_matrix_dir=matrix_root,
        model_receipt_sha256="f" * 64,
        model_artifact_root="0" * 64,
        publication_trust_store_sha256=_sha(trust_store),
    )
    bindings = publication_claim_bindings(
        capsule_path=capsule_path,
        matrix_path=matrix_root / "manifest.json",
        experiment_path=Path("experiments/memory/stage1-longmemeval-screen.yaml"),
        wave=preview,
        batch_script_path=BATCH_SCRIPT,
    )
    signature = private.sign(publication_claim_message(bindings))
    attestation = tmp_path / "claim-attestation.json"
    attestation.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "status": "PUBLICATION_CLAIM_ATTESTED",
                "algorithm": "ed25519",
                "key_id": "publication-ci-1",
                "bindings": bindings,
                "signature_base64": base64.b64encode(signature).decode(),
            }
        ),
        encoding="utf-8",
    )
    return {
        "publication_capsule_path": capsule_path,
        "publication_attestation_path": attestation,
        "publication_trust_store_path": trust_store,
        "publication_trust_store_sha256": _sha(trust_store),
        "control_matrix_dir": matrix_root,
        "output_dir": tmp_path / "wave",
        "run_root": "/shared/cotcodec/publication-runs",
        "model_cache_host": "/shared/cotcodec/model-cache",
        "model_receipt_sha256": "f" * 64,
        "model_artifact_root": "0" * 64,
        "public_benchmark_path": "/shared/cotcodec/inputs/longmemeval_s_cleaned.json",
    }


def test_publication_wave_emits_every_eligible_control_and_binds_roots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs = _inputs(tmp_path, monkeypatch)
    index = compile_publication_wave(**inputs)
    expected = sorted(set(CONTROL_SYSTEMS) - {"lru", "reference"})
    assert [row["control_id"] for row in index["cells"]] == expected
    assert index["status"] == "COMPILED_PUBLICATION_WAVE"
    for row in index["cells"]:
        raw = yaml.safe_load((inputs["output_dir"] / row["manifest"]).read_text())
        manifest = validate_manifest(raw)
        assert manifest["claim_admission"]["wave"]["control_id"] == row["control_id"]
        assert manifest["claim_admission"]["wave"]["wave_sha256"] == index["wave_sha256"]
        assert manifest["randomness_contract"] == "deterministic-all-serve"


def test_publication_wave_rejects_incomplete_roster_or_bundle_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs = _inputs(tmp_path, monkeypatch)
    manifest_path = inputs["control_matrix_dir"] / "manifest.json"
    matrix = json.loads(manifest_path.read_text())
    matrix["controls"].pop()
    unsigned = {key: value for key, value in matrix.items() if key != "matrix_sha256"}
    matrix["matrix_sha256"] = sha256_text(canonical_json(unsigned))
    manifest_path.write_text(json.dumps(matrix), encoding="utf-8")
    with pytest.raises(ValueError, match="complete registered roster"):
        compile_publication_wave(**inputs)

    inputs = _inputs(tmp_path / "drift", monkeypatch)
    (inputs["control_matrix_dir"] / "bundles" / "bm25.json").write_text("drift")
    with pytest.raises(ValueError, match="cannot read frozen bundle|bm25 digest drifted"):
        compile_publication_wave(**inputs)

    inputs = _inputs(tmp_path / "cherry-pick", monkeypatch)
    manifest_path = inputs["control_matrix_dir"] / "manifest.json"
    matrix = json.loads(manifest_path.read_text())
    for control in matrix["controls"]:
        if control["control_id"] not in {"bm25", "lru", "reference"}:
            control["eligible_for_primary"] = False
            control["ineligibility_reason"] = "fabricated"
    unsigned = {key: value for key, value in matrix.items() if key != "matrix_sha256"}
    matrix["matrix_sha256"] = sha256_text(canonical_json(unsigned))
    manifest_path.write_text(json.dumps(matrix), encoding="utf-8")
    with pytest.raises(ValueError, match="eligibility drifted"):
        compile_publication_wave(**inputs)


def test_publication_wave_refuses_existing_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inputs = _inputs(tmp_path, monkeypatch)
    inputs["output_dir"].mkdir()
    with pytest.raises(ValueError, match="refusing to overwrite"):
        compile_publication_wave(**inputs)


def test_publication_wave_rejects_unsigned_or_self_minted_capsule(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inputs = _inputs(tmp_path, monkeypatch)
    attestation = json.loads(inputs["publication_attestation_path"].read_text())
    attestation["signature_base64"] = base64.b64encode(b"0" * 64).decode()
    inputs["publication_attestation_path"].write_text(json.dumps(attestation))
    with pytest.raises(ValueError, match="invalid Ed25519"):
        compile_publication_wave(**inputs)


def test_publication_claim_signature_covers_wave_model_and_every_bundle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inputs = _inputs(tmp_path, monkeypatch)
    inputs["model_receipt_sha256"] = "9" * 64
    with pytest.raises(ValueError, match="does not bind the complete claim wave"):
        compile_publication_wave(**inputs)


def test_publication_claim_rejects_post_capsule_batch_substitution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inputs = _inputs(tmp_path, monkeypatch)
    preview = preview_publication_wave(
        publication_capsule_path=inputs["publication_capsule_path"],
        control_matrix_dir=inputs["control_matrix_dir"],
        model_receipt_sha256=inputs["model_receipt_sha256"],
        model_artifact_root=inputs["model_artifact_root"],
        publication_trust_store_sha256=inputs["publication_trust_store_sha256"],
    )
    substituted = tmp_path / "substituted.sbatch"
    substituted.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    with pytest.raises(ValueError, match="differs from the signed source capsule"):
        publication_claim_bindings(
            capsule_path=inputs["publication_capsule_path"],
            matrix_path=inputs["control_matrix_dir"] / "manifest.json",
            experiment_path=Path("experiments/memory/stage1-longmemeval-screen.yaml"),
            wave=preview,
            batch_script_path=substituted,
        )
