#!/usr/bin/env python3
"""Bind a raw Syft SPDX document to one immutable OCI image subject."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

IMAGE_ID_RE = re.compile(r"sha256:[0-9a-f]{64}")
REPO_DIGEST_RE = re.compile(
    r"[A-Za-z0-9][A-Za-z0-9._:/-]*@sha256:[0-9a-f]{64}"
)
SYFT_IMAGE_RE = re.compile(
    r"[A-Za-z0-9][A-Za-z0-9._:/-]*@sha256:[0-9a-f]{64}"
)
VERSION_RE = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+")
SUBJECT_ID = "SPDXRef-CotcodecContainerImage"


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_raw(path: Path, syft_version: str) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise ValueError("raw SBOM must be a regular non-symlink file")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("raw SBOM is not valid JSON") from exc
    if not isinstance(payload, dict) or not str(payload.get("spdxVersion", "")).startswith(
        "SPDX-"
    ):
        raise ValueError("raw SBOM must be SPDX JSON")
    packages = payload.get("packages")
    if not isinstance(packages, list) or not packages:
        raise ValueError("raw SBOM has no discovered packages")
    if payload.get("cotcodecScan") is not None or any(
        isinstance(package, dict) and package.get("SPDXID") == SUBJECT_ID
        for package in packages
    ):
        raise ValueError("raw SBOM is already annotated")
    creators = payload.get("creationInfo", {}).get("creators", [])
    if "Organization: Anchore, Inc" not in creators or (
        f"Tool: syft-{syft_version}" not in creators
    ):
        raise ValueError("raw SBOM generator differs from the registered Syft version")
    return payload


def annotate(
    raw: dict[str, Any],
    *,
    image_id: str,
    repo_digest: str,
    syft_version: str,
    scanner_target: str,
) -> dict[str, Any]:
    if IMAGE_ID_RE.fullmatch(image_id) is None:
        raise ValueError("image_id must be an immutable sha256 image ID")
    if REPO_DIGEST_RE.fullmatch(repo_digest) is None:
        raise ValueError("repo_digest must be an immutable OCI repository digest")
    if VERSION_RE.fullmatch(syft_version) is None:
        raise ValueError("syft_version must be semantic x.y.z")
    if scanner_target != "docker-archive:/input/image.tar":
        raise ValueError("scanner_target differs from the reviewed offline archive path")
    sealed = json.loads(json.dumps(raw))
    packages = sealed["packages"]
    packages.append(
        {
            "SPDXID": SUBJECT_ID,
            "name": image_id,
            "versionInfo": repo_digest.rsplit("@", 1)[1],
            "downloadLocation": "NOASSERTION",
            "filesAnalyzed": False,
            "licenseConcluded": "NOASSERTION",
            "licenseDeclared": "NOASSERTION",
            "copyrightText": "NOASSERTION",
            "externalRefs": [
                {
                    "referenceCategory": "PACKAGE-MANAGER",
                    "referenceType": "purl",
                    "referenceLocator": f"pkg:oci/{repo_digest}",
                }
            ],
        }
    )
    sealed["documentDescribes"] = [SUBJECT_ID]
    sealed["cotcodecScan"] = {
        "scanner": "syft",
        "scanner_version": syft_version,
        "target_repo_digest": repo_digest,
        "target_image_id": image_id,
        "argv": ["syft", scanner_target, "--output", "spdx-json"],
    }
    return sealed


def _write_bytes_once(path: Path, encoded: bytes) -> None:
    path = Path(os.path.abspath(os.fspath(path)))
    if any(component.is_symlink() for component in (path, *path.parents)):
        raise ValueError("SBOM output path cannot contain symbolic links")
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        prefix=f".{path.name}.", dir=path.parent, delete=False
    ) as temporary:
        temporary_path = Path(temporary.name)
        temporary.write(encoded)
        temporary.flush()
        os.fsync(temporary.fileno())
    try:
        os.link(temporary_path, path)
    except FileExistsError as exc:
        raise ValueError(f"refusing to overwrite artifact: {path}") from exc
    finally:
        temporary_path.unlink(missing_ok=True)
    descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_once(path: Path, payload: dict[str, Any]) -> None:
    _write_bytes_once(path, _canonical(payload) + b"\n")


def seal_sbom(
    *,
    raw_path: Path,
    published_raw_path: Path,
    output_path: Path,
    receipt_path: Path,
    image_id: str,
    repo_digest: str,
    syft_version: str,
    syft_image: str,
    scanner_target: str,
) -> dict[str, Any]:
    if SYFT_IMAGE_RE.fullmatch(syft_image) is None:
        raise ValueError("syft_image must be an immutable repository digest")
    outputs = tuple(
        Path(os.path.abspath(os.fspath(path)))
        for path in (published_raw_path, output_path, receipt_path)
    )
    if len(set(outputs)) != len(outputs):
        raise ValueError("raw, sealed, and receipt SBOM outputs must be distinct")
    if Path(os.path.abspath(os.fspath(raw_path))) in outputs:
        raise ValueError("staged raw SBOM input must differ from final outputs")
    for artifact in outputs:
        if artifact.exists() or artifact.is_symlink():
            raise ValueError(f"refusing to overwrite artifact: {artifact}")
    raw = _load_raw(raw_path, syft_version)
    raw_packages = raw["packages"]
    raw_package_root = _sha256_bytes(_canonical(raw_packages))
    sealed = annotate(
        raw,
        image_id=image_id,
        repo_digest=repo_digest,
        syft_version=syft_version,
        scanner_target=scanner_target,
    )
    if _sha256_bytes(_canonical(sealed["packages"][:-1])) != raw_package_root:
        raise ValueError("SBOM annotation changed discovered Syft packages")
    _write_bytes_once(published_raw_path, raw_path.read_bytes())
    _write_once(output_path, sealed)
    unsigned_receipt = {
        "schema_version": 1,
        "status": "SEALED_SYFT_SBOM_SUBJECT_BINDING",
        "target_image_id": image_id,
        "target_repo_digest": repo_digest,
        "syft_image": syft_image,
        "syft_version": syft_version,
        "raw_sbom_sha256": _sha256_file(published_raw_path),
        "sealed_sbom_sha256": _sha256_file(output_path),
        "raw_package_count": len(raw_packages),
        "sealed_package_count": len(sealed["packages"]),
        "raw_package_root_sha256": raw_package_root,
        "discovered_packages_unchanged": True,
        "synthetic_subject_spdx_id": SUBJECT_ID,
    }
    receipt = {
        **unsigned_receipt,
        "receipt_sha256": _sha256_bytes(_canonical(unsigned_receipt)),
    }
    _write_once(receipt_path, receipt)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-sbom", type=Path, required=True)
    parser.add_argument("--publish-raw", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--image-id", required=True)
    parser.add_argument("--repo-digest", required=True)
    parser.add_argument("--syft-version", required=True)
    parser.add_argument("--syft-image", required=True)
    parser.add_argument("--scanner-target", required=True)
    args = parser.parse_args()
    try:
        receipt = seal_sbom(
            raw_path=args.raw_sbom,
            published_raw_path=args.publish_raw,
            output_path=args.output,
            receipt_path=args.receipt,
            image_id=args.image_id,
            repo_digest=args.repo_digest,
            syft_version=args.syft_version,
            syft_image=args.syft_image,
            scanner_target=args.scanner_target,
        )
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
