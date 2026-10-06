from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from scripts.create_source_archive import create_archive
from scripts.seal_publication_capsule import seal_publication_capsule


def _run(root: Path, *args: str) -> None:
    subprocess.run(args, cwd=root, check=True, capture_output=True)


def _fixture(tmp_path: Path) -> dict[str, Any]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    repository = tmp_path / "repo"
    repository.mkdir()
    _run(repository, "git", "init", "-q")
    _run(repository, "git", "config", "user.email", "test@example.com")
    _run(repository, "git", "config", "user.name", "Test")
    uv_lock = repository / "uv.lock"
    uv_lock.write_text("version = 1\n", encoding="utf-8")
    batch = repository / "infra" / "batch.sbatch"
    batch.parent.mkdir()
    batch.write_text("#!/bin/bash\n", encoding="utf-8")
    dockerfile = repository / "infra" / "Dockerfile"
    dockerfile.write_text("FROM scratch\n", encoding="utf-8")
    _run(repository, "git", "add", ".")
    _run(repository, "git", "commit", "-qm", "publication")
    archive = tmp_path / "source.tar.gz"
    receipt = create_archive(repository, archive, mode="publication")
    receipt_path = tmp_path / "source-receipt.json"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    image_id = "sha256:" + "4" * 64
    repo_digest = "registry.example/cotcodec@sha256:" + "5" * 64
    inspect = {
        "Id": image_id,
        "RepoDigests": [repo_digest],
        "Os": "linux",
        "Architecture": "amd64",
        "RootFS": {"Layers": ["sha256:" + "6" * 64]},
        "Config": {
            "Labels": {
                "org.opencontainers.image.revision": receipt["git_sha"],
                "org.opencontainers.image.source-tree-sha256": receipt["archive_sha256"],
                "org.opencontainers.image.cotcodec-dev-dependencies": "false",
                "org.opencontainers.image.cotcodec-runtime-profile": "memory",
            }
        },
    }
    sbom = {
        "spdxVersion": "SPDX-2.3",
        "name": "cotcodec-image-sbom",
        "documentNamespace": "https://example.invalid/cotcodec",
        "documentDescribes": ["SPDXRef-container"],
        "creationInfo": {"creators": ["Organization: Anchore, Inc", "Tool: syft-1.20.0"]},
        "cotcodecScan": {
            "scanner": "syft",
            "scanner_version": "1.20.0",
            "target_repo_digest": repo_digest,
            "target_image_id": image_id,
            "argv": ["syft", repo_digest, "--output", "spdx-json"],
        },
        "packages": [
            {
                "name": image_id,
                "SPDXID": "SPDXRef-container",
                "externalRefs": [
                    {
                        "referenceCategory": "PACKAGE-MANAGER",
                        "referenceType": "purl",
                        "referenceLocator": f"pkg:oci/{repo_digest}",
                    }
                ],
            }
        ],
    }
    sbom_path = tmp_path / "sbom.spdx.json"
    sbom_path.write_text(json.dumps(sbom), encoding="utf-8")
    return {
        "source_receipt_path": receipt_path,
        "repository_path": repository,
        "image_reference": image_id,
        "sbom_path": sbom_path,
        "uv_lock_path": uv_lock,
        "batch_script_path": batch,
        "dockerfile_path": dockerfile,
        "output_path": tmp_path / "capsule.json",
        "image_inspector": lambda _reference: inspect,
    }


def test_capsule_binds_clean_git_live_image_sbom_and_runtime(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    capsule = seal_publication_capsule(**paths)
    assert capsule["status"] == "SEALED_PUBLICATION_CAPSULE_CANDIDATE"
    assert capsule["publication_ready"] is False
    assert "administrator signature" in capsule["publication_gate"]
    assert capsule["image"]["image_id"] == "sha256:" + "4" * 64
    assert capsule["sbom"]["item_count"] == 1
    assert len(capsule["capsule_sha256"]) == 64
    assert json.loads(paths["output_path"].read_text()) == capsule


def test_capsule_rejects_image_label_source_drift(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    valid_inspect = paths["image_inspector"](paths["image_reference"])
    valid_inspect["Config"]["Labels"]["org.opencontainers.image.source-tree-sha256"] = "9" * 64
    paths["image_inspector"] = lambda _reference: valid_inspect
    with pytest.raises(ValueError, match="differs from clean source"):
        seal_publication_capsule(**paths)


def test_capsule_rejects_sbom_id_in_unrelated_comment(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    sbom = json.loads(paths["sbom_path"].read_text())
    sbom["comment"] = paths["image_reference"]
    sbom["packages"][0]["name"] = "unrelated"
    paths["sbom_path"].write_text(json.dumps(sbom), encoding="utf-8")
    with pytest.raises(ValueError, match="SBOM subject does not bind"):
        seal_publication_capsule(**paths)


def test_capsule_rejects_fake_locator_or_unbound_scanner_invocation(
    tmp_path: Path,
) -> None:
    paths = _fixture(tmp_path / "locator")
    sbom = json.loads(paths["sbom_path"].read_text())
    sbom["packages"][0]["externalRefs"][0]["referenceCategory"] = "OTHER"
    paths["sbom_path"].write_text(json.dumps(sbom), encoding="utf-8")
    with pytest.raises(ValueError, match="SBOM subject does not bind"):
        seal_publication_capsule(**paths)

    paths = _fixture(tmp_path / "scanner")
    sbom = json.loads(paths["sbom_path"].read_text())
    sbom["cotcodecScan"]["target_repo_digest"] = "registry.example/unrelated@sha256:" + "7" * 64
    paths["sbom_path"].write_text(json.dumps(sbom), encoding="utf-8")
    with pytest.raises(ValueError, match="scanner invocation"):
        seal_publication_capsule(**paths)


def test_capsule_rejects_empty_repository_digests(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    inspect = paths["image_inspector"](paths["image_reference"])
    inspect["RepoDigests"] = []
    paths["image_inspector"] = lambda _reference: inspect
    with pytest.raises(ValueError, match="immutable repository digest"):
        seal_publication_capsule(**paths)


def test_capsule_rejects_dirty_repo_or_nonarchive_bytes(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    paths["uv_lock_path"].write_bytes(b"changed")
    with pytest.raises(ValueError, match="completely clean"):
        seal_publication_capsule(**paths)

    paths = _fixture(tmp_path / "invalid")
    receipt = json.loads(paths["source_receipt_path"].read_text())
    archive = Path(receipt["archive"])
    archive.write_bytes(b"not a tar")
    receipt["archive_sha256"] = __import__("hashlib").sha256(archive.read_bytes()).hexdigest()
    paths["source_receipt_path"].write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(ValueError, match="not valid gzip-compressed tar"):
        seal_publication_capsule(**paths)


def test_semantically_identical_inspection_has_stable_capsule_root(tmp_path: Path) -> None:
    first = _fixture(tmp_path / "first")
    inspect = first["image_inspector"](first["image_reference"])
    one = seal_publication_capsule(**first)
    second_output = tmp_path / "second-capsule.json"
    first["output_path"] = second_output
    first["image_inspector"] = lambda _reference: dict(reversed(list(inspect.items())))
    two = seal_publication_capsule(**first)
    assert one["image"]["inspect_projection_sha256"] == two["image"]["inspect_projection_sha256"]
    assert one["capsule_sha256"] == two["capsule_sha256"]


def test_capsule_never_overwrites_existing_output(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    paths["output_path"].write_text("keep", encoding="utf-8")
    with pytest.raises(ValueError, match="refusing to overwrite"):
        seal_publication_capsule(**paths)
    assert paths["output_path"].read_text() == "keep"
