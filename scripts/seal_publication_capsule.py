#!/usr/bin/env python3
"""Verify and seal clean Git, live OCI, SBOM, and runtime provenance."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from scripts.create_source_archive import (
    archive_file_manifest,
    git_status,
    publication_tree,
    sha256_file,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BATCH_SCRIPT = PROJECT_ROOT / "infra/slurm/host-single-node/docker-research.sbatch"
DEFAULT_DOCKERFILE = PROJECT_ROOT / "infra/research/Dockerfile"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_RE = re.compile(r"^[0-9a-f]{40}$")
IMAGE_ID_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
REPO_DIGEST_RE = re.compile(r"^[A-Za-z0-9._:/-]+@sha256:[0-9a-f]{64}$")


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _load_object(path: Path, owner: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{owner} must be valid JSON") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{owner} must contain one JSON object")
    return value


def _git(root: Path, *arguments: str) -> str:
    return subprocess.check_output(["git", *arguments], cwd=root, text=True).strip()


def _path_in_repository(path: Path, repository: Path, owner: str) -> str:
    resolved = path.resolve(strict=True)
    try:
        relative = resolved.relative_to(repository)
    except ValueError as exc:
        raise ValueError(f"{owner} must be a committed file inside the repository") from exc
    if not resolved.is_file() or resolved.is_symlink():
        raise ValueError(f"{owner} must be a regular non-symlink file")
    return relative.as_posix()


def _source_contract(
    source_receipt_path: Path,
    repository_path: Path,
    uv_lock_path: Path,
    batch_script_path: Path,
    dockerfile_path: Path,
) -> tuple[dict[str, Any], dict[str, str]]:
    receipt = _load_object(source_receipt_path, "source receipt")
    if receipt.get("schema_version") != 2 or receipt.get("mode") != "publication":
        raise ValueError("source receipt must be a schema-v2 publication archive")
    if receipt.get("worktree_clean") is not True:
        raise ValueError("source receipt is not clean publication provenance")
    repository = repository_path.resolve(strict=True)
    actual_root = Path(_git(repository, "rev-parse", "--show-toplevel")).resolve()
    if actual_root != repository:
        raise ValueError("repository path must be the Git worktree root")
    if git_status(repository):
        raise ValueError("publication capsule requires a completely clean repository")
    git_sha = receipt.get("git_sha")
    git_tree = receipt.get("git_tree")
    if not isinstance(git_sha, str) or not GIT_RE.fullmatch(git_sha):
        raise ValueError("source receipt git_sha is invalid")
    if not isinstance(git_tree, str) or not GIT_RE.fullmatch(git_tree):
        raise ValueError("source receipt git_tree is invalid")
    if _git(repository, "rev-parse", "HEAD") != git_sha:
        raise ValueError("source receipt commit is not the checked-out clean HEAD")
    if _git(repository, "rev-parse", f"{git_sha}^{{tree}}") != git_tree:
        raise ValueError("source receipt tree does not match its Git commit")

    tree_rows = publication_tree(repository, git_sha)
    expected_manifest = tuple(
        {key: row[key] for key in ("mode", "path", "sha256")} for row in tree_rows
    )
    receipt_manifest = receipt.get("file_manifest")
    if receipt_manifest != list(expected_manifest):
        raise ValueError("source receipt file manifest differs from the Git commit")
    manifest_sha256 = sha256_bytes(canonical_json(expected_manifest).encode())
    if receipt.get("file_manifest_sha256") != manifest_sha256:
        raise ValueError("source receipt file-manifest root is invalid")
    if receipt.get("file_count") != len(expected_manifest):
        raise ValueError("source receipt file count differs from the Git commit")

    archive_value = receipt.get("archive")
    if not isinstance(archive_value, str):
        raise ValueError("source receipt archive path is missing")
    archive = Path(archive_value)
    if not archive.is_absolute() or not archive.is_file() or archive.is_symlink():
        raise ValueError("source archive must be an existing regular absolute file")
    archive_sha256 = sha256_file(archive)
    if receipt.get("archive_sha256") != archive_sha256:
        raise ValueError("source archive bytes differ from the source receipt")
    if archive_file_manifest(archive) != expected_manifest:
        raise ValueError("source archive members differ from the committed Git tree")

    runtime_paths = {
        "uv_lock": _path_in_repository(uv_lock_path, repository, "uv.lock"),
        "batch_script": _path_in_repository(batch_script_path, repository, "batch script"),
        "dockerfile": _path_in_repository(dockerfile_path, repository, "Dockerfile"),
    }
    manifest_by_path = {row["path"]: row for row in expected_manifest}
    runtime_sha256: dict[str, str] = {}
    for owner, relative in runtime_paths.items():
        row = manifest_by_path.get(relative)
        path = repository / relative
        if row is None or row["sha256"] != sha256_file(path):
            raise ValueError(f"{owner} bytes differ from the committed source archive")
        runtime_sha256[f"{owner}_sha256"] = row["sha256"]
    if receipt.get("uv_lock_sha256") != runtime_sha256["uv_lock_sha256"]:
        raise ValueError("uv.lock digest differs from the source receipt")
    return (
        {
            "receipt_sha256": sha256_bytes(canonical_json(receipt).encode()),
            "archive_sha256": archive_sha256,
            "archive_format": receipt.get("archive_format"),
            "file_manifest_sha256": manifest_sha256,
            "file_count": len(expected_manifest),
            "git_sha": git_sha,
            "git_tree": git_tree,
            "uv_lock_sha256": runtime_sha256["uv_lock_sha256"],
        },
        runtime_sha256,
    )


def _docker_inspect(image_reference: str) -> dict[str, Any]:
    completed = subprocess.run(
        ["docker", "image", "inspect", "--type", "image", image_reference],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    if not isinstance(payload, list) or len(payload) != 1 or not isinstance(payload[0], dict):
        raise ValueError("live Docker inspection did not return exactly one image")
    return payload[0]


def _image_contract(
    image_reference: str,
    source: dict[str, Any],
    inspector: Callable[[str], dict[str, Any]],
) -> dict[str, Any]:
    if not IMAGE_ID_RE.fullmatch(image_reference):
        raise ValueError("publication image reference must be an exact sha256 image ID")
    try:
        inspect = inspector(image_reference)
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        raise ValueError("live OCI image inspection failed") from exc
    if not isinstance(inspect, dict) or inspect.get("Id") != image_reference:
        raise ValueError("live OCI resolver returned a different image ID")
    config = inspect.get("Config")
    labels = config.get("Labels") if isinstance(config, dict) else None
    if not isinstance(labels, dict):
        raise ValueError("live image lacks OCI labels")
    expected_labels = {
        "org.opencontainers.image.revision": source["git_sha"],
        "org.opencontainers.image.source-tree-sha256": source["archive_sha256"],
        "org.opencontainers.image.cotcodec-dev-dependencies": "false",
    }
    for key, expected in expected_labels.items():
        if labels.get(key) != expected:
            raise ValueError(f"image label {key} differs from clean source provenance")
    profile = labels.get("org.opencontainers.image.cotcodec-runtime-profile")
    if not isinstance(profile, str) or not profile or profile == "unknown":
        raise ValueError("image runtime profile is missing or unresolved")
    repo_digests = inspect.get("RepoDigests")
    if (
        not isinstance(repo_digests, list)
        or not repo_digests
        or not all(
            isinstance(value, str) and REPO_DIGEST_RE.fullmatch(value) for value in repo_digests
        )
    ):
        raise ValueError("publication image requires an immutable repository digest")
    rootfs = inspect.get("RootFS")
    layers = rootfs.get("Layers") if isinstance(rootfs, dict) else None
    if (
        not isinstance(layers, list)
        or not layers
        or not all(isinstance(value, str) and IMAGE_ID_RE.fullmatch(value) for value in layers)
    ):
        raise ValueError("live image lacks a complete content-addressed layer list")
    projection = {
        "image_id": image_reference,
        "repo_digests": sorted(repo_digests),
        "runtime_profile": profile,
        "labels": expected_labels,
        "os": inspect.get("Os"),
        "architecture": inspect.get("Architecture"),
        "rootfs_layers": layers,
    }
    return {
        **projection,
        "inspect_projection_sha256": sha256_bytes(canonical_json(projection).encode()),
    }


def _oci_purl(repo_digest: str) -> str:
    repository, digest = repo_digest.rsplit("@", 1)
    return f"pkg:oci/{repository}@{digest}"


def _scan_contract(sbom: dict[str, Any], image_id: str, repo_digests: list[str]) -> dict[str, Any]:
    scan = sbom.get("cotcodecScan")
    if not isinstance(scan, dict):
        raise ValueError("SBOM must include the exact scanner invocation receipt")
    version = scan.get("scanner_version")
    target = scan.get("target_repo_digest")
    expected_argv = ["syft", target, "--output", "spdx-json"]
    if (
        scan.get("scanner") != "syft"
        or not isinstance(version, str)
        or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version)
        or target not in repo_digests
        or scan.get("target_image_id") != image_id
        or scan.get("argv") != expected_argv
    ):
        raise ValueError("SBOM scanner invocation does not bind the exact OCI target")
    return {
        "scanner": "syft",
        "scanner_version": version,
        "target_repo_digest": target,
        "target_image_id": image_id,
        "argv": expected_argv,
    }


def _spdx_subject_values(sbom: dict[str, Any]) -> tuple[set[str], int]:
    described = sbom.get("documentDescribes")
    packages = sbom.get("packages")
    if not isinstance(described, list) or not described or not isinstance(packages, list):
        raise ValueError("SPDX SBOM must identify at least one described package")
    subjects = [
        package
        for package in packages
        if isinstance(package, dict) and package.get("SPDXID") in described
    ]
    if not subjects:
        raise ValueError("SPDX documentDescribes does not resolve to a package")
    values: set[str] = set()
    for subject in subjects:
        for field in ("name", "versionInfo", "packageFileName"):
            value = subject.get(field)
            if isinstance(value, str):
                values.add(value)
        for reference in subject.get("externalRefs", []):
            if (
                isinstance(reference, dict)
                and reference.get("referenceCategory") == "PACKAGE-MANAGER"
                and reference.get("referenceType") == "purl"
                and isinstance(reference.get("referenceLocator"), str)
                and reference["referenceLocator"].startswith("pkg:oci/")
            ):
                values.add(reference["referenceLocator"])
    creation = sbom.get("creationInfo")
    creators = creation.get("creators") if isinstance(creation, dict) else None
    if (
        not isinstance(creators, list)
        or "Organization: Anchore, Inc" not in creators
        or not any(
            isinstance(value, str) and re.fullmatch(r"Tool: syft-[0-9]+\.[0-9]+\.[0-9]+", value)
            for value in creators
        )
    ):
        raise ValueError("SPDX SBOM must bind a versioned Syft generator")
    return values, len(packages)


def _cyclonedx_subject_values(sbom: dict[str, Any]) -> tuple[set[str], int]:
    metadata = sbom.get("metadata")
    component = metadata.get("component") if isinstance(metadata, dict) else None
    components = sbom.get("components")
    if not isinstance(component, dict) or not isinstance(components, list):
        raise ValueError("CycloneDX SBOM must identify a metadata subject component")
    values: set[str] = set()
    for field in ("bom-ref", "name", "version", "purl"):
        value = component.get(field)
        if isinstance(value, str):
            values.add(value)
    for prop in component.get("properties", []):
        if isinstance(prop, dict) and isinstance(prop.get("value"), str):
            values.add(prop["value"])
    tools = metadata.get("tools")
    tool_components = tools.get("components") if isinstance(tools, dict) else None
    if not isinstance(tool_components, list) or not any(
        isinstance(tool, dict)
        and isinstance(tool.get("name"), str)
        and isinstance(tool.get("version"), str)
        and tool["version"]
        for tool in tool_components
    ):
        raise ValueError("CycloneDX SBOM must bind a versioned generator")
    return values, len(components)


def _sbom_contract(
    sbom_path: Path,
    image_id: str,
    repo_digests: list[str],
) -> dict[str, Any]:
    sbom = _load_object(sbom_path, "SBOM")
    scan = _scan_contract(sbom, image_id, repo_digests)
    if isinstance(sbom.get("spdxVersion"), str) and sbom["spdxVersion"].startswith("SPDX-"):
        subject_values, item_count = _spdx_subject_values(sbom)
        format_id = "spdx-json"
    else:
        raise ValueError("publication SBOM must be Syft SPDX JSON")
    if image_id not in subject_values or not any(
        _oci_purl(digest) in subject_values for digest in repo_digests
    ):
        raise ValueError("SBOM subject does not bind the OCI image ID and repository digest")
    if item_count < 1:
        raise ValueError("SBOM must contain at least one discovered package/component")
    return {
        "sha256": sha256_file(sbom_path),
        "format": format_id,
        "item_count": item_count,
        "subject_image_id": image_id,
        "subject_repo_digests": sorted(
            digest for digest in repo_digests if _oci_purl(digest) in subject_values
        ),
        "scan": scan,
    }


def _write_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
    with tempfile.NamedTemporaryFile(
        prefix=f".{path.name}.", dir=path.parent, delete=False
    ) as temporary:
        temporary_path = Path(temporary.name)
        temporary.write(encoded)
        temporary.flush()
        os.fsync(temporary.fileno())
    try:
        try:
            os.link(temporary_path, path)
        except FileExistsError as exc:
            raise ValueError(f"refusing to overwrite publication capsule: {path}") from exc
        temporary_path.unlink()
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise


def seal_publication_capsule(
    *,
    source_receipt_path: Path,
    repository_path: Path,
    image_reference: str,
    sbom_path: Path,
    uv_lock_path: Path,
    batch_script_path: Path,
    dockerfile_path: Path,
    output_path: Path,
    image_inspector: Callable[[str], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Verify every publication artifact and seal one canonical identity root."""

    source, runtime = _source_contract(
        source_receipt_path,
        repository_path,
        uv_lock_path,
        batch_script_path,
        dockerfile_path,
    )
    image = _image_contract(image_reference, source, image_inspector or _docker_inspect)
    sbom = _sbom_contract(sbom_path, image["image_id"], image["repo_digests"])
    unsigned = {
        "schema_version": 2,
        "status": "SEALED_PUBLICATION_CAPSULE_CANDIDATE",
        "publication_ready": False,
        "publication_gate": (
            "Requires a protected administrator signature over capsule, matrix, "
            "experiment, complete wave, batch script, and every eligible bundle root."
        ),
        "source": source,
        "image": image,
        "sbom": sbom,
        "runtime": runtime,
    }
    capsule = {
        **unsigned,
        "capsule_sha256": sha256_bytes(canonical_json(unsigned).encode()),
    }
    _write_atomic(output_path, capsule)
    return capsule


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-receipt", type=Path, required=True)
    parser.add_argument("--repository", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--image", required=True)
    parser.add_argument("--sbom", type=Path, required=True)
    parser.add_argument("--uv-lock", type=Path, default=PROJECT_ROOT / "uv.lock")
    parser.add_argument("--batch-script", type=Path, default=DEFAULT_BATCH_SCRIPT)
    parser.add_argument("--dockerfile", type=Path, default=DEFAULT_DOCKERFILE)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        capsule = seal_publication_capsule(
            source_receipt_path=args.source_receipt,
            repository_path=args.repository,
            image_reference=args.image,
            sbom_path=args.sbom,
            uv_lock_path=args.uv_lock,
            batch_script_path=args.batch_script,
            dockerfile_path=args.dockerfile,
            output_path=args.output,
        )
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(capsule, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
