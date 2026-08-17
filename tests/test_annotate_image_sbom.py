from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.annotate_image_sbom import SUBJECT_ID, seal_sbom


def _raw(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "SPDXID": "SPDXRef-DOCUMENT",
                "spdxVersion": "SPDX-2.3",
                "creationInfo": {
                    "creators": [
                        "Organization: Anchore, Inc",
                        "Tool: syft-1.51.0",
                    ]
                },
                "packages": [
                    {
                        "SPDXID": "SPDXRef-Package-a",
                        "name": "dependency-a",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def test_seal_sbom_binds_subject_without_changing_discovery(tmp_path: Path) -> None:
    raw = tmp_path / "raw.json"
    _raw(raw)
    output = tmp_path / "sealed.json"
    published_raw = tmp_path / "published-raw.json"
    receipt_path = tmp_path / "receipt.json"
    image_id = "sha256:" + "a" * 64
    repo_digest = "registry.invalid/image@sha256:" + "b" * 64
    receipt = seal_sbom(
        raw_path=raw,
        published_raw_path=published_raw,
        output_path=output,
        receipt_path=receipt_path,
        image_id=image_id,
        repo_digest=repo_digest,
        syft_version="1.51.0",
        syft_image="anchore/syft@sha256:" + "c" * 64,
        scanner_target="docker-archive:/input/image.tar",
    )
    sealed = json.loads(output.read_text(encoding="utf-8"))
    assert sealed["packages"][0]["name"] == "dependency-a"
    assert sealed["packages"][1]["SPDXID"] == SUBJECT_ID
    assert sealed["documentDescribes"] == [SUBJECT_ID]
    assert sealed["cotcodecScan"] == {
        "scanner": "syft",
        "scanner_version": "1.51.0",
        "target_repo_digest": repo_digest,
        "target_image_id": image_id,
        "argv": [
            "syft",
            "docker-archive:/input/image.tar",
            "--output",
            "spdx-json",
        ],
    }
    assert receipt["discovered_packages_unchanged"] is True
    assert receipt["sealed_package_count"] == 2


def test_seal_sbom_rejects_generator_drift_and_overwrite(tmp_path: Path) -> None:
    raw = tmp_path / "raw.json"
    _raw(raw)
    common = {
        "raw_path": raw,
        "published_raw_path": tmp_path / "published-raw.json",
        "output_path": tmp_path / "sealed.json",
        "receipt_path": tmp_path / "receipt.json",
        "image_id": "sha256:" + "a" * 64,
        "repo_digest": "registry.invalid/image@sha256:" + "b" * 64,
        "syft_image": "anchore/syft@sha256:" + "c" * 64,
        "scanner_target": "docker-archive:/input/image.tar",
    }
    with pytest.raises(ValueError, match="generator"):
        seal_sbom(**common, syft_version="1.50.0")
    seal_sbom(**common, syft_version="1.51.0")
    with pytest.raises(ValueError, match="overwrite"):
        seal_sbom(**common, syft_version="1.51.0")


def test_seal_sbom_rejects_symlinked_output_parent(tmp_path: Path) -> None:
    raw = tmp_path / "raw.json"
    _raw(raw)
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError, match="symbolic links"):
        seal_sbom(
            raw_path=raw,
            published_raw_path=tmp_path / "published-raw.json",
            output_path=link / "sealed.json",
            receipt_path=tmp_path / "receipt.json",
            image_id="sha256:" + "a" * 64,
            repo_digest="registry.invalid/image@sha256:" + "b" * 64,
            syft_version="1.51.0",
            syft_image="anchore/syft@sha256:" + "c" * 64,
            scanner_target="docker-archive:/input/image.tar",
        )
