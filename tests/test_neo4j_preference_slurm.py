from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BATCH = (
    PROJECT_ROOT
    / "infra/slurm/host-single-node/neo4j-preference-lifecycle.sbatch"
)


def test_neo4j_confirmation_is_h100_slurm_without_container_gpu() -> None:
    content = BATCH.read_text(encoding="utf-8")
    assert "#SBATCH --gres=gpu:h100:1" in content
    assert "--lane cluster-amd64-slurm" in content
    assert "nvidia-smi" in content
    assert "--gpus" not in content
    assert "sudo" not in content
    assert "neo4j:5.26.29-community@sha256:" in content
    assert "anchore/syft@sha256:" in content


def test_neo4j_confirmation_binds_archived_batch_and_source() -> None:
    content = BATCH.read_text(encoding="utf-8")
    assert "COTCODEC_SOURCE_ARCHIVE" in content
    assert "COTCODEC_SOURCE_RECEIPT" in content
    assert "COTCODEC_SOURCE_EXTRACTOR_SHA256" in content
    assert "COTCODEC_CLIENT_IMAGE_ARCHIVE_SHA256" in content
    assert "COTCODEC_CLIENT_IMAGE_ID" in content
    assert 'sha256sum "$archived_batch"' in content
    assert 'sha256sum "$archived_extractor"' in content
    assert 'docker image load --input "$client_image_archive"' in content
    assert '--prebuilt-client-image "$client_image"' in content
    assert '--expected-client-image-id "$expected_client_image_id"' in content
    assert 'docker image save --output "$client_archive"' in content
    assert 'client_sbom_sha256' in content
