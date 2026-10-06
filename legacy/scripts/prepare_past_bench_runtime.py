#!/usr/bin/env python3
"""Validate and materialize the pinned PAST-Bench Hermes+ runtime context.

The public interface has three operations:

* validate the CoTCodec dependency/container contract;
* compile one exact clean PAST-Bench Git checkout into a verified Docker context;
* verify a compiled context without Git or network access.

The resulting receipt is source and build-input evidence only.  It is not an
image, Slurm, model, benchmark, or scientific-result attestation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import tomllib
from pathlib import Path, PurePosixPath
from typing import Any

import yaml
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNTIME_ROOT = PROJECT_ROOT / "infra" / "research" / "past-bench"
DEFAULT_RUNTIME_CONTRACT = (
    PROJECT_ROOT / "research" / "source-contracts" / "past-bench-runtime.yaml"
)
DEFAULT_SOURCE_CONTRACT = (
    PROJECT_ROOT / "research" / "source-contracts" / "past-bench.yaml"
)
CONTEXT_RECEIPT = ".cotcodec/source-context-receipt.json"
RUNTIME_OVERLAY = {
    "apply_checkpoint_overlay.py": "infra/research/past-bench/apply_checkpoint_overlay.py",
    "checkpoint_runtime.py": "infra/research/past-bench/checkpoint_runtime.py",
    "checkpoint_runtime_selftest.py": "infra/research/past-bench/checkpoint_runtime_selftest.py",
    "Dockerfile": "infra/research/past-bench/Dockerfile",
    "pyproject.toml": "infra/research/past-bench/pyproject.toml",
    "uv.lock": "infra/research/past-bench/uv.lock",
    "requirements.lock": "infra/research/past-bench/requirements.lock",
    "past-bench-runtime.yaml": "research/source-contracts/past-bench-runtime.yaml",
    "past-bench-source.yaml": "research/source-contracts/past-bench.yaml",
    "prepare_past_bench_runtime.py": "scripts/prepare_past_bench_runtime.py",
}
SHA256_RE = re.compile(r"[0-9a-f]{64}")
IMMUTABLE_IMAGE_RE = re.compile(
    r"[A-Za-z0-9][A-Za-z0-9._:/-]*@sha256:[0-9a-f]{64}"
)


class PastBenchRuntimeError(ValueError):
    """Raised when a runtime or compiled-context invariant fails."""


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _root(value: Any) -> str:
    return _sha256_bytes(_canonical(value).encode("utf-8"))


def _safe_relative(value: str, *, owner: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or any(
        part in {"", ".", ".."} for part in path.parts
    ):
        raise PastBenchRuntimeError(f"{owner}: unsafe relative path {value!r}")
    return path


def _read_regular(path: Path, *, owner: str) -> bytes:
    flags = os.O_RDONLY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise PastBenchRuntimeError(f"{owner}: cannot safely open {path}: {exc}") from exc
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise PastBenchRuntimeError(f"{owner}: expected a regular file: {path}")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _load_mapping(path: Path, *, owner: str) -> dict[str, Any]:
    try:
        value = yaml.safe_load(_read_regular(path, owner=owner).decode("utf-8"))
    except (UnicodeError, yaml.YAMLError) as exc:
        raise PastBenchRuntimeError(f"{owner}: invalid YAML: {exc}") from exc
    if not isinstance(value, dict):
        raise PastBenchRuntimeError(f"{owner}: document must be a mapping")
    return value


def _git(checkout: Path, *arguments: str, binary: bool = False) -> str | bytes:
    completed = subprocess.run(
        ["git", "-C", str(checkout), *arguments],
        check=False,
        capture_output=True,
        text=not binary,
    )
    if completed.returncode:
        stderr = completed.stderr
        stdout = completed.stdout
        if isinstance(stderr, bytes):
            stderr = stderr.decode(errors="replace")
        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors="replace")
        detail = str(stderr).strip() or str(stdout).strip()
        raise PastBenchRuntimeError(f"git {' '.join(arguments)} failed: {detail}")
    if binary:
        assert isinstance(completed.stdout, bytes)
        return completed.stdout
    assert isinstance(completed.stdout, str)
    return completed.stdout.strip()


def _git_blob(checkout: Path, revision: str, relative: str) -> bytes:
    _safe_relative(relative, owner="upstream dependency declaration")
    return _git(checkout, "show", f"{revision}:{relative}", binary=True)  # type: ignore[return-value]


def _git_file_manifest(checkout: Path, revision: str) -> list[dict[str, Any]]:
    raw = _git(checkout, "ls-tree", "-r", "-z", revision, binary=True)
    assert isinstance(raw, bytes)
    rows: list[dict[str, Any]] = []
    for entry in raw.split(b"\0"):
        if not entry:
            continue
        try:
            metadata, raw_path = entry.split(b"\t", 1)
            mode, kind, object_id = metadata.decode("ascii").split()
            relative = raw_path.decode("utf-8")
        except (UnicodeError, ValueError) as exc:
            raise PastBenchRuntimeError("malformed PAST-Bench Git tree entry") from exc
        if kind != "blob" or mode not in {"100644", "100755"}:
            raise PastBenchRuntimeError(
                f"unsupported PAST-Bench Git object {kind}/{mode}: {relative}"
            )
        content = _git(checkout, "cat-file", "blob", object_id, binary=True)
        assert isinstance(content, bytes)
        rows.append(
            {
                "mode": mode,
                "path": relative,
                "sha256": _sha256_bytes(content),
                "size": len(content),
            }
        )
    return sorted(rows, key=lambda row: row["path"])


def _source_manifest(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if relative == ".cotcodec" or relative.startswith(".cotcodec/") or path.is_dir():
            continue
        if path.is_symlink() or not path.is_file():
            raise PastBenchRuntimeError(
                f"compiled PAST-Bench source contains an unsupported entry: {relative}"
            )
        content = _read_regular(path, owner="compiled PAST-Bench source")
        rows.append(
            {
                "mode": "100755" if path.stat().st_mode & 0o111 else "100644",
                "path": relative,
                "sha256": _sha256_bytes(content),
                "size": len(content),
            }
        )
    return sorted(rows, key=lambda row: row["path"])


def _git_tree_sha(root: Path, manifest: list[dict[str, Any]]) -> str:
    """Reconstruct the SHA-1 Git tree identity from materialized source bytes."""

    directories: dict[tuple[str, ...], list[tuple[str, str, bytes]]] = {}
    for row in manifest:
        relative = _safe_relative(str(row["path"]), owner="compiled Git tree")
        content = _read_regular(root.joinpath(*relative.parts), owner="compiled Git blob")
        if _sha256_bytes(content) != row.get("sha256") or len(content) != row.get("size"):
            raise PastBenchRuntimeError(
                f"compiled Git blob differs from its manifest: {relative.as_posix()}"
            )
        mode = row.get("mode")
        if mode not in {"100644", "100755"}:
            raise PastBenchRuntimeError(
                f"compiled Git blob has unsupported mode: {relative.as_posix()}"
            )
        blob = hashlib.sha1(
            f"blob {len(content)}\0".encode("ascii") + content,
            usedforsecurity=False,
        ).digest()
        parent = tuple(relative.parts[:-1])
        directories.setdefault(parent, []).append((str(mode), relative.name, blob))
        for depth in range(len(parent)):
            directories.setdefault(parent[:depth], [])

    tree_ids: dict[tuple[str, ...], bytes] = {}
    for directory in sorted(directories, key=len, reverse=True):
        entries = list(directories[directory])
        child_depth = len(directory) + 1
        for child, tree_id in tree_ids.items():
            if len(child) == child_depth and child[:-1] == directory:
                entries.append(("40000", child[-1], tree_id))
        entries.sort(key=lambda item: (item[1] + ("/" if item[0] == "40000" else "")).encode())
        payload = b"".join(
            mode.encode("ascii") + b" " + name.encode("utf-8") + b"\0" + object_id
            for mode, name, object_id in entries
        )
        tree_ids[directory] = hashlib.sha1(
            f"tree {len(payload)}\0".encode("ascii") + payload,
            usedforsecurity=False,
        ).digest()
    try:
        return tree_ids[()].hex()
    except KeyError as exc:
        raise PastBenchRuntimeError("compiled Git tree is empty") from exc


def _lock_packages(lock_path: Path) -> dict[str, str]:
    try:
        lock = tomllib.loads(_read_regular(lock_path, owner="PAST runtime lock").decode())
    except (UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise PastBenchRuntimeError(f"PAST runtime lock is invalid TOML: {exc}") from exc
    packages = lock.get("package")
    if not isinstance(packages, list):
        raise PastBenchRuntimeError("PAST runtime lock has no package roster")
    selected: dict[str, str] = {}
    for package in packages:
        if not isinstance(package, dict):
            raise PastBenchRuntimeError("PAST runtime lock package is malformed")
        name = package.get("name")
        version = package.get("version")
        if not isinstance(name, str) or not isinstance(version, str):
            raise PastBenchRuntimeError("PAST runtime lock package identity is malformed")
        normalized = canonicalize_name(name)
        if normalized in selected:
            raise PastBenchRuntimeError(f"duplicate locked package: {normalized}")
        selected[normalized] = version
    return selected


def _upstream_requirements(checkout: Path, revision: str) -> list[tuple[str, Requirement]]:
    documents: list[tuple[str, bytes]] = [
        ("past-bench", _git_blob(checkout, revision, "pyproject.toml")),
        (
            "hermes-plus",
            _git_blob(checkout, revision, "agents/hermes-plus/pyproject.toml"),
        ),
    ]
    requirements: list[tuple[str, Requirement]] = []
    for owner, payload in documents:
        try:
            project = tomllib.loads(payload.decode("utf-8"))["project"]
        except (KeyError, TypeError, UnicodeError, tomllib.TOMLDecodeError) as exc:
            raise PastBenchRuntimeError(f"{owner}: invalid upstream pyproject") from exc
        declared = project.get("dependencies")
        if not isinstance(declared, list) or not all(
            isinstance(item, str) for item in declared
        ):
            raise PastBenchRuntimeError(f"{owner}: dependencies must be strings")
        for item in declared:
            requirements.append((owner, Requirement(item)))
        if owner == "past-bench":
            optional = project.get("optional-dependencies")
            mock = optional.get("mock") if isinstance(optional, dict) else None
            if not isinstance(mock, list) or not all(isinstance(item, str) for item in mock):
                raise PastBenchRuntimeError("past-bench: mock dependencies are missing")
            for item in mock:
                requirements.append(("past-bench[mock]", Requirement(item)))
    return requirements


def _upstream_test_roster(checkout: Path, revision: str) -> list[dict[str, Any]]:
    try:
        root = tomllib.loads(_git_blob(checkout, revision, "pyproject.toml").decode())
        testpaths = root["tool"]["pytest"]["ini_options"]["testpaths"]
    except (KeyError, TypeError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise PastBenchRuntimeError("PAST-Bench pytest roster is invalid") from exc
    if not isinstance(testpaths, list) or not all(
        isinstance(item, str) for item in testpaths
    ):
        raise PastBenchRuntimeError("PAST-Bench pytest roster must contain paths")
    if len(testpaths) != len(set(testpaths)):
        raise PastBenchRuntimeError("PAST-Bench pytest roster contains duplicates")
    rows: list[dict[str, Any]] = []
    for relative in testpaths:
        _safe_relative(relative, owner="upstream pytest roster")
        content = _git_blob(checkout, revision, relative)
        rows.append(
            {
                "path": relative,
                "size": len(content),
                "sha256": _sha256_bytes(content),
            }
        )
    return rows


def _validate_upstream_resolution(
    checkout: Path, revision: str, packages: dict[str, str]
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for owner, requirement in _upstream_requirements(checkout, revision):
        name = canonicalize_name(requirement.name)
        locked = packages.get(name)
        if locked is None:
            raise PastBenchRuntimeError(f"{owner}: {name} is absent from the runtime lock")
        version = Version(locked)
        if requirement.marker is not None and not requirement.marker.evaluate(
            {"python_version": "3.11", "sys_platform": "linux"}
        ):
            continue
        if requirement.specifier and not requirement.specifier.contains(
            version, prereleases=True
        ):
            raise PastBenchRuntimeError(
                f"{owner}: locked {name}=={locked} violates {requirement.specifier}"
            )
        rows.append(
            {
                "owner": owner,
                "requirement": str(requirement),
                "locked_version": locked,
            }
        )
    return sorted(rows, key=lambda row: (row["owner"], row["requirement"]))


def _registered_runtime_file_rows(
    contract: dict[str, Any],
    *,
    project_root: Path,
    source_contract_path: Path,
) -> list[dict[str, Any]]:
    """Revalidate host bytes against the runtime contract's registered hashes."""

    source_contract_bytes = _read_regular(
        source_contract_path, owner="PAST source contract"
    )
    source_binding = contract.get("source_contract")
    if not isinstance(source_binding, dict) or source_binding.get(
        "sha256"
    ) != _sha256_bytes(source_contract_bytes):
        raise PastBenchRuntimeError("PAST runtime contract does not bind the source contract")

    registered_files = contract.get("runtime_files")
    self_describing_contracts = {
        "research/source-contracts/past-bench-runtime.yaml",
        "research/source-contracts/past-bench.yaml",
    }
    if not isinstance(registered_files, dict) or set(registered_files) != set(
        RUNTIME_OVERLAY.values()
    ) - self_describing_contracts:
        raise PastBenchRuntimeError("PAST runtime file roster differs from the interface")
    file_rows: list[dict[str, Any]] = []
    for relative, expected in sorted(registered_files.items()):
        path = project_root.joinpath(*_safe_relative(relative, owner="runtime file").parts)
        content = _read_regular(path, owner="registered runtime file")
        if not isinstance(expected, str) or _sha256_bytes(content) != expected:
            raise PastBenchRuntimeError(f"registered runtime file drifted: {relative}")
        file_rows.append({"path": relative, "size": len(content), "sha256": expected})
    return file_rows


def validate_runtime_contract(
    checkout: Path,
    *,
    contract_path: Path = DEFAULT_RUNTIME_CONTRACT,
    runtime_root: Path = DEFAULT_RUNTIME_ROOT,
    source_contract_path: Path = DEFAULT_SOURCE_CONTRACT,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    """Validate the exact dependency/container contract against upstream source."""

    contract = _load_mapping(contract_path, owner="PAST runtime contract")
    if contract.get("schema_version") != 1:
        raise PastBenchRuntimeError("PAST runtime contract schema_version must be 1")
    if contract.get("status") != "LOCKED_BUILD_INPUTS_NOT_EXECUTION":
        raise PastBenchRuntimeError("PAST runtime contract status overstates its evidence")
    if contract.get("scientific_result") is not False:
        raise PastBenchRuntimeError("PAST runtime contract cannot be a scientific result")

    source_contract_bytes = _read_regular(
        source_contract_path, owner="PAST source contract"
    )
    source_binding = contract.get("source_contract")
    if not isinstance(source_binding, dict):
        raise PastBenchRuntimeError("PAST runtime source binding is missing")

    execution = contract.get("execution")
    if not isinstance(execution, dict):
        raise PastBenchRuntimeError("PAST runtime execution contract is missing")
    base_image = execution.get("base_image")
    if not isinstance(base_image, str) or IMMUTABLE_IMAGE_RE.fullmatch(base_image) is None:
        raise PastBenchRuntimeError("PAST runtime base image is not immutable")
    if execution.get("platform") != "linux/amd64":
        raise PastBenchRuntimeError("PAST runtime is registered only for linux/amd64")
    if execution.get("runtime_mode") != "whole-process-local-inside-docker":
        raise PastBenchRuntimeError("PAST self-evolve containment mode drifted")
    if execution.get("runtime_scope") != (
        "benchmark-harness-hermes-plus-mock-services-and-tests"
    ):
        raise PastBenchRuntimeError("PAST candidate runtime scope drifted")
    if execution.get("upstream_nested_runtime_container_supported") is not False:
        raise PastBenchRuntimeError("unsupported nested runtime mode cannot be enabled")
    if execution.get("model_transport") != "not-implemented":
        raise PastBenchRuntimeError("unattested PAST model transport cannot be promoted")

    file_rows = _registered_runtime_file_rows(
        contract,
        project_root=project_root,
        source_contract_path=source_contract_path,
    )

    lock_contract = contract.get("lock")
    if not isinstance(lock_contract, dict):
        raise PastBenchRuntimeError("PAST lock contract is missing")
    packages = _lock_packages(runtime_root / "uv.lock")
    if len(packages) != lock_contract.get("package_count"):
        raise PastBenchRuntimeError("PAST lock package count drifted")
    required_uv = lock_contract.get("uv_version")
    completed = subprocess.run(
        ["uv", "--version"], check=False, capture_output=True, text=True
    )
    version_fields = completed.stdout.strip().split()
    if (
        completed.returncode
        or len(version_fields) < 2
        or version_fields[:2] != ["uv", str(required_uv)]
    ):
        raise PastBenchRuntimeError(f"runtime contract requires uv {required_uv}")
    lock_check = subprocess.run(
        ["uv", "lock", "--check", "--project", str(runtime_root)],
        check=False,
        capture_output=True,
        text=True,
    )
    if lock_check.returncode:
        detail = lock_check.stderr.strip() or lock_check.stdout.strip()
        raise PastBenchRuntimeError(f"uv lock check failed: {detail}")
    exported = subprocess.run(
        [
            "uv",
            "export",
            "--project",
            str(runtime_root),
            "--locked",
            "--all-groups",
            "--no-emit-project",
            "--no-annotate",
            "--no-header",
            "--format",
            "requirements-txt",
        ],
        check=False,
        capture_output=True,
    )
    if exported.returncode:
        raise PastBenchRuntimeError(
            "uv export failed: " + exported.stderr.decode(errors="replace").strip()
        )
    committed_requirements = _read_regular(
        runtime_root / "requirements.lock", owner="hashed requirements export"
    )
    if exported.stdout != committed_requirements:
        raise PastBenchRuntimeError("requirements.lock is not the exact frozen uv export")

    source_revision = source_binding.get("revision")
    if not isinstance(source_revision, str) or not re.fullmatch(
        r"[0-9a-f]{40}", source_revision
    ):
        raise PastBenchRuntimeError("PAST source revision is malformed")
    dependency_rows = _validate_upstream_resolution(checkout, source_revision, packages)
    if len(dependency_rows) != lock_contract.get("upstream_requirement_count"):
        raise PastBenchRuntimeError("upstream direct requirement count drifted")
    test_rows = _upstream_test_roster(checkout, source_revision)
    if len(test_rows) != lock_contract.get("upstream_test_file_count"):
        raise PastBenchRuntimeError("upstream declared test-file count drifted")

    if str(_git(checkout, "rev-parse", "HEAD")) != source_revision:
        raise PastBenchRuntimeError("PAST checkout differs from runtime source revision")
    receipt = {
        "schema_version": 1,
        "status": "VALIDATED_LOCKED_BUILD_INPUTS_NOT_EXECUTION",
        "scientific_result": False,
        "source_revision": source_revision,
        "source_contract_sha256": _sha256_bytes(source_contract_bytes),
        "platform": execution["platform"],
        "base_image": base_image,
        "runtime_scope": execution["runtime_scope"],
        "runtime_mode": execution["runtime_mode"],
        "model_transport": execution["model_transport"],
        "uv_version": required_uv,
        "locked_package_count": len(packages),
        "upstream_requirement_count": len(dependency_rows),
        "upstream_requirement_root_sha256": _root(dependency_rows),
        "upstream_test_file_count": len(test_rows),
        "upstream_test_roster_sha256": _root(test_rows),
        "runtime_file_root_sha256": _root(file_rows),
        "runtime_files": file_rows,
    }
    receipt["receipt_sha256"] = _root(receipt)
    admission = contract.get("admission")
    if not isinstance(admission, dict):
        raise PastBenchRuntimeError("PAST runtime admission roots are missing")
    expected_runtime_receipt = admission.get("runtime_receipt_sha256")
    if receipt["receipt_sha256"] != expected_runtime_receipt:
        raise PastBenchRuntimeError(
            "PAST runtime receipt drifted: "
            f"computed {receipt['receipt_sha256']}, expected {expected_runtime_receipt}"
        )
    return receipt


def _extract_git_archive(checkout: Path, revision: str, output: Path) -> None:
    archive = output.parent / f".{output.name}.source-{os.getpid()}.tar"
    try:
        with archive.open("xb", buffering=0) as handle:
            completed = subprocess.run(
                ["git", "-C", str(checkout), "archive", "--format=tar", revision],
                check=False,
                stdout=handle,
                stderr=subprocess.PIPE,
            )
            os.fsync(handle.fileno())
        if completed.returncode:
            raise PastBenchRuntimeError(
                "git archive failed: "
                + completed.stderr.decode(errors="replace").strip()
            )
        seen: set[str] = set()
        with tarfile.open(archive, "r:") as bundle:
            for member in bundle:
                path = _safe_relative(member.name, owner="PAST source archive")
                relative = path.as_posix().rstrip("/")
                if relative in seen:
                    raise PastBenchRuntimeError(
                        f"duplicate PAST source archive member: {relative}"
                    )
                seen.add(relative)
                destination = output.joinpath(*path.parts)
                if member.isdir():
                    destination.mkdir(parents=True, exist_ok=True)
                    continue
                if not member.isfile():
                    raise PastBenchRuntimeError(
                        f"unsupported PAST source archive member: {relative}"
                    )
                destination.parent.mkdir(parents=True, exist_ok=True)
                stream = bundle.extractfile(member)
                if stream is None:
                    raise PastBenchRuntimeError(
                        f"cannot read PAST source archive member: {relative}"
                    )
                data = stream.read()
                descriptor = os.open(
                    destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, member.mode & 0o777
                )
                with os.fdopen(descriptor, "wb") as handle:
                    handle.write(data)
                    handle.flush()
                    os.fsync(handle.fileno())
    finally:
        archive.unlink(missing_ok=True)


def _context_receipt(
    source_receipt: dict[str, Any],
    runtime_receipt: dict[str, Any],
    source_manifest: list[dict[str, Any]],
    overlay_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    unsigned = {
        "schema_version": 1,
        "status": "VERIFIED_PAST_BUILD_CONTEXT_NOT_IMAGE",
        "scientific_result": False,
        "source_receipt_sha256": source_receipt["receipt_sha256"],
        "source_revision": source_receipt["checkout"]["revision"],
        "source_archive_sha256": source_receipt["checkout"][
            "source_archive_sha256"
        ],
        "source_file_count": len(source_manifest),
        "source_file_manifest_sha256": _root(source_manifest),
        "source_files": source_manifest,
        "runtime_receipt_sha256": runtime_receipt["receipt_sha256"],
        "runtime_file_manifest_sha256": _root(overlay_rows),
        "runtime_files": overlay_rows,
    }
    return {**unsigned, "receipt_sha256": _root(unsigned)}


def verify_context(
    context: Path,
    *,
    trusted_project_root: Path | None = PROJECT_ROOT,
) -> dict[str, Any]:
    """Verify a compiled context, optionally against registered host bytes.

    ``trusted_project_root=None`` is a self-contained integrity recheck for use
    during the image build.  It is deliberately insufficient to authorize a
    build command; the host-side default additionally binds the registered
    CoTCodec contracts and runtime files.
    """

    context = context.resolve()
    if not context.is_dir() or context.is_symlink():
        raise PastBenchRuntimeError("PAST build context must be a regular directory")
    receipt_path = context / CONTEXT_RECEIPT
    try:
        receipt = json.loads(
            _read_regular(receipt_path, owner="PAST context receipt").decode("utf-8")
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise PastBenchRuntimeError(f"PAST context receipt is invalid: {exc}") from exc
    if not isinstance(receipt, dict):
        raise PastBenchRuntimeError("PAST context receipt must be a mapping")
    source_manifest = _source_manifest(context)
    if (
        len(source_manifest) != receipt.get("source_file_count")
        or _root(source_manifest) != receipt.get("source_file_manifest_sha256")
        or source_manifest != receipt.get("source_files")
    ):
        raise PastBenchRuntimeError("compiled PAST source differs from its receipt")
    source_contract = _load_mapping(
        context / ".cotcodec/past-bench-source.yaml",
        owner="compiled PAST source contract",
    )
    expected_tree = source_contract.get("tree_sha")
    actual_tree = _git_tree_sha(context, source_manifest)
    if not isinstance(expected_tree, str) or actual_tree != expected_tree:
        raise PastBenchRuntimeError(
            f"compiled PAST Git tree drifted: {actual_tree} != {expected_tree}"
        )
    if receipt.get("source_revision") != source_contract.get("revision"):
        raise PastBenchRuntimeError("compiled PAST source revision drifted")
    if receipt.get("source_archive_sha256") != source_contract.get(
        "source_archive_sha256"
    ):
        raise PastBenchRuntimeError("compiled PAST archive identity drifted")
    overlay_rows: list[dict[str, Any]] = []
    for name in sorted(RUNTIME_OVERLAY):
        relative = f".cotcodec/{name}"
        content = _read_regular(context / relative, owner="PAST context runtime file")
        overlay_rows.append(
            {"path": relative, "size": len(content), "sha256": _sha256_bytes(content)}
        )
    if (
        _root(overlay_rows) != receipt.get("runtime_file_manifest_sha256")
        or overlay_rows != receipt.get("runtime_files")
    ):
        raise PastBenchRuntimeError("compiled PAST runtime overlay differs from its receipt")
    unsigned = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    if receipt.get("receipt_sha256") != _root(unsigned):
        raise PastBenchRuntimeError("PAST context receipt digest is invalid")

    runtime_contract = _load_mapping(
        context / ".cotcodec/past-bench-runtime.yaml",
        owner="compiled PAST runtime contract",
    )
    admission = runtime_contract.get("admission")
    if not isinstance(admission, dict):
        raise PastBenchRuntimeError("compiled PAST admission roots are missing")
    if receipt.get("source_receipt_sha256") != admission.get(
        "source_receipt_sha256"
    ):
        raise PastBenchRuntimeError("compiled PAST source receipt is not registered")
    if receipt.get("runtime_receipt_sha256") != admission.get(
        "runtime_receipt_sha256"
    ):
        raise PastBenchRuntimeError("compiled PAST runtime receipt is not registered")

    if trusted_project_root is not None:
        trusted_project_root = trusted_project_root.resolve()
        trusted_runtime_contract_path = trusted_project_root.joinpath(
            *_safe_relative(
                RUNTIME_OVERLAY["past-bench-runtime.yaml"],
                owner="trusted runtime contract",
            ).parts
        )
        trusted_runtime_contract = _load_mapping(
            trusted_runtime_contract_path,
            owner="trusted PAST runtime contract",
        )
        trusted_source_contract_path = trusted_project_root.joinpath(
            *_safe_relative(
                RUNTIME_OVERLAY["past-bench-source.yaml"],
                owner="trusted source contract",
            ).parts
        )
        _registered_runtime_file_rows(
            trusted_runtime_contract,
            project_root=trusted_project_root,
            source_contract_path=trusted_source_contract_path,
        )
        for name, relative in sorted(RUNTIME_OVERLAY.items()):
            trusted = trusted_project_root.joinpath(
                *_safe_relative(relative, owner="trusted runtime overlay").parts
            )
            if _read_regular(
                context / ".cotcodec" / name, owner="compiled runtime overlay"
            ) != _read_regular(trusted, owner="trusted runtime overlay"):
                raise PastBenchRuntimeError(
                    f"compiled PAST overlay is not the registered host file: {name}"
                )
    return receipt


def prepare_context(
    checkout: Path,
    output_dir: Path,
    *,
    contract_path: Path = DEFAULT_RUNTIME_CONTRACT,
    runtime_root: Path = DEFAULT_RUNTIME_ROOT,
    source_contract_path: Path = DEFAULT_SOURCE_CONTRACT,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    """Compile exact source plus registered runtime files into one Docker context."""

    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from scripts.validate_past_bench_source import validate_checkout

    checkout = checkout.resolve()
    source_receipt = validate_checkout(
        checkout,
        contract_path=source_contract_path,
        ledger_path=project_root / "research/memory-sources.yaml",
    )
    runtime_receipt = validate_runtime_contract(
        checkout,
        contract_path=contract_path,
        runtime_root=runtime_root,
        source_contract_path=source_contract_path,
        project_root=project_root,
    )
    runtime_contract = _load_mapping(contract_path, owner="PAST runtime contract")
    admission = runtime_contract.get("admission")
    if not isinstance(admission, dict) or source_receipt.get(
        "receipt_sha256"
    ) != admission.get("source_receipt_sha256"):
        raise PastBenchRuntimeError("PAST source-doctor receipt is not registered")
    source_revision = source_receipt["checkout"]["revision"]
    git_manifest = _git_file_manifest(checkout, source_revision)

    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise PastBenchRuntimeError(f"refusing to overwrite PAST context: {output_dir}")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output_dir.name}.tmp-", dir=output_dir.parent)
    )
    try:
        _extract_git_archive(checkout, source_revision, staging)
        materialized = _source_manifest(staging)
        if materialized != git_manifest:
            raise PastBenchRuntimeError(
                "materialized PAST source differs from its complete Git tree"
            )
        overlay = staging / ".cotcodec"
        overlay.mkdir(mode=0o755)
        overlay_rows: list[dict[str, Any]] = []
        for name, relative in sorted(RUNTIME_OVERLAY.items()):
            source = project_root.joinpath(
                *_safe_relative(relative, owner="runtime overlay source").parts
            )
            data = _read_regular(source, owner="runtime overlay source")
            destination = overlay / name
            descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            overlay_rows.append(
                {
                    "path": f".cotcodec/{name}",
                    "size": len(data),
                    "sha256": _sha256_bytes(data),
                }
            )
        receipt = _context_receipt(
            source_receipt, runtime_receipt, materialized, overlay_rows
        )
        receipt_path = staging / CONTEXT_RECEIPT
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(receipt_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write((_canonical(receipt) + "\n").encode())
            handle.flush()
            os.fsync(handle.fileno())
        os.rename(staging, output_dir)
        directory = os.open(output_dir.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        return verify_context(output_dir, trusted_project_root=project_root)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def build_command(context: Path, *, tag: str) -> list[str]:
    """Return the exact Docker build command after validating its context."""

    if not tag or tag.startswith("-") or any(character.isspace() for character in tag):
        raise PastBenchRuntimeError("PAST image tag is invalid")
    receipt = verify_context(context, trusted_project_root=PROJECT_ROOT)
    return [
        "docker",
        "buildx",
        "build",
        "--load",
        "--platform",
        "linux/amd64",
        "--network",
        "host",
        "--build-arg",
        f"PAST_RUNTIME_CONTRACT_SHA256={receipt['runtime_receipt_sha256']}",
        "--build-arg",
        f"PAST_SOURCE_RECEIPT_SHA256={receipt['source_receipt_sha256']}",
        "--file",
        str(context.resolve() / ".cotcodec/Dockerfile"),
        "--tag",
        tag,
        str(context.resolve()),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--context", type=Path)
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--self-contained", action="store_true")
    parser.add_argument("--contract-only", action="store_true")
    parser.add_argument("--tag")
    args = parser.parse_args()
    try:
        if args.verify_only:
            if args.context is None or args.checkout is not None or args.output_dir is not None:
                parser.error("--verify-only requires only --context")
            receipt = verify_context(
                args.context,
                trusted_project_root=None if args.self_contained else PROJECT_ROOT,
            )
        elif args.contract_only:
            if args.self_contained:
                parser.error("--self-contained is only valid with --verify-only")
            if args.checkout is None or args.context is not None or args.output_dir is not None:
                parser.error("--contract-only requires only --checkout")
            receipt = validate_runtime_contract(args.checkout)
        else:
            if args.self_contained:
                parser.error("--self-contained is only valid with --verify-only")
            if args.checkout is None or args.output_dir is None or args.context is not None:
                parser.error("context compilation requires --checkout and --output-dir")
            receipt = prepare_context(args.checkout, args.output_dir)
        payload: dict[str, Any] = {"receipt": receipt}
        if args.tag is not None:
            target = args.context or args.output_dir
            if target is None:
                parser.error("--tag requires a compiled --context or --output-dir")
            payload["build_command"] = build_command(target, tag=args.tag)
    except PastBenchRuntimeError as exc:
        parser.error(str(exc))
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
