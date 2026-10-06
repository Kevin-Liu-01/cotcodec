#!/usr/bin/env python3
"""Materialize and verify the exact MemPalace Git tree as a Docker context."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.memory_trials.mempalace_control import (  # noqa: E402
    MEMPALACE_REPOSITORY,
    MEMPALACE_REVISION,
    MEMPALACE_SOURCE_ARCHIVE_SHA256,
    MEMPALACE_TREE,
)

SOURCE_RECEIPT_NAME = ".cotcodec-mempalace-source.json"
MEMPALACE_SOURCE_FILE_COUNT = 555
MEMPALACE_SOURCE_MANIFEST_SHA256 = (
    "77c2bc19bf763e9172515b62f7e1f784d25932052350af090db19e735b2bf831"
)


@dataclass(frozen=True)
class SourceExpectations:
    repository: str = MEMPALACE_REPOSITORY
    revision: str = MEMPALACE_REVISION
    tree: str = MEMPALACE_TREE
    archive_sha256: str = MEMPALACE_SOURCE_ARCHIVE_SHA256
    manifest_sha256: str = MEMPALACE_SOURCE_MANIFEST_SHA256
    file_count: int = MEMPALACE_SOURCE_FILE_COUNT


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _git(checkout: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(checkout), *arguments],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise ValueError(f"git {' '.join(arguments)} failed: {detail}")
    return completed.stdout.strip()


def _normalize_repository(value: str) -> str:
    normalized = value.strip().removesuffix("/").removesuffix(".git")
    if normalized.startswith("git@github.com:"):
        normalized = "https://github.com/" + normalized.removeprefix("git@github.com:")
    return normalized


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest_sha256(rows: list[dict[str, Any]]) -> str:
    return hashlib.sha256(_canonical(rows).encode()).hexdigest()


def git_file_manifest(checkout: Path, revision: str) -> list[dict[str, Any]]:
    raw = subprocess.check_output(
        ["git", "-C", str(checkout), "ls-tree", "-r", "-z", revision]
    )
    rows: list[dict[str, Any]] = []
    for item in raw.split(b"\0"):
        if not item:
            continue
        metadata, raw_path = item.split(b"\t", 1)
        mode, kind, object_id = metadata.decode().split()
        if kind != "blob" or mode not in {"100644", "100755", "120000"}:
            raise ValueError("MemPalace Git tree contains an unsupported object")
        content = subprocess.check_output(
            ["git", "-C", str(checkout), "cat-file", "blob", object_id]
        )
        rows.append(
            {
                "mode": mode,
                "path": raw_path.decode(),
                "sha256": hashlib.sha256(content).hexdigest(),
                "size": len(content),
            }
        )
    return rows


def _materialized_manifest(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if relative == SOURCE_RECEIPT_NAME or path.is_dir():
            continue
        if path.is_symlink():
            target = os.readlink(path)
            target_path = PurePosixPath(target)
            if target_path.is_absolute() or ".." in target_path.parts:
                raise ValueError("MemPalace source context contains an unsafe symbolic link")
            content = target.encode()
            mode = "120000"
        elif path.is_file():
            content = path.read_bytes()
            mode = "100755" if path.stat().st_mode & 0o111 else "100644"
        else:
            raise ValueError("MemPalace source context contains an unsupported entry")
        rows.append(
            {
                "mode": mode,
                "path": relative,
                "sha256": hashlib.sha256(content).hexdigest(),
                "size": len(content),
            }
        )
    # ``Path`` ordering visits a directory before path-component siblings,
    # which is not the same as ordering the final relative file names.  Hash
    # the manifest in one canonical path order independent of traversal.
    return sorted(rows, key=lambda row: row["path"])


def _safe_tar_member(member: tarfile.TarInfo) -> None:
    path = PurePosixPath(member.name)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("MemPalace source archive contains path traversal")
    if member.ischr() or member.isblk() or member.isfifo():
        raise ValueError("MemPalace source archive contains a special file")
    if member.issym() or member.islnk():
        target = PurePosixPath(member.linkname)
        if target.is_absolute() or ".." in target.parts:
            raise ValueError("MemPalace source archive contains an unsafe link")


def _archive_checkout(checkout: Path, revision: str, output: Path) -> None:
    with output.open("xb", buffering=0) as handle:
        completed = subprocess.run(
            ["git", "-C", str(checkout), "archive", "--format=tar", revision],
            check=False,
            stdout=handle,
            stderr=subprocess.PIPE,
        )
        os.fsync(handle.fileno())
    if completed.returncode:
        detail = completed.stderr.decode(errors="replace").strip()
        raise ValueError(f"git archive failed: {detail}")


def _receipt(
    *, expectations: SourceExpectations, manifest: list[dict[str, Any]]
) -> dict[str, Any]:
    unsigned = {
        "schema_version": 1,
        "status": "VERIFIED_MEMPALACE_SOURCE_CONTEXT",
        "repository": expectations.repository,
        "revision": expectations.revision,
        "tree": expectations.tree,
        "source_archive_sha256": expectations.archive_sha256,
        "file_count": expectations.file_count,
        "file_manifest_sha256": expectations.manifest_sha256,
        "file_manifest": manifest,
    }
    return {
        **unsigned,
        "receipt_sha256": hashlib.sha256(_canonical(unsigned).encode()).hexdigest(),
    }


def verify_context(
    context: Path, *, expectations: SourceExpectations | None = None
) -> dict[str, Any]:
    expectations = expectations or SourceExpectations()
    context = context.resolve()
    receipt_path = context / SOURCE_RECEIPT_NAME
    if not receipt_path.is_file() or receipt_path.is_symlink():
        raise ValueError("MemPalace source-context receipt is missing or unsafe")
    try:
        stored = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("MemPalace source-context receipt is invalid") from exc
    manifest = _materialized_manifest(context)
    if (
        len(manifest) != expectations.file_count
        or _manifest_sha256(manifest) != expectations.manifest_sha256
    ):
        raise ValueError("MemPalace materialized source differs from the pinned Git tree")
    expected = _receipt(expectations=expectations, manifest=manifest)
    if stored != expected:
        raise ValueError("MemPalace source-context receipt differs from its full tree")
    return stored


def prepare_context(
    checkout: Path,
    output_dir: Path,
    *,
    expectations: SourceExpectations | None = None,
) -> dict[str, Any]:
    expectations = expectations or SourceExpectations()
    checkout = checkout.resolve()
    if not checkout.is_dir() or checkout.is_symlink():
        raise ValueError("MemPalace checkout must be a regular directory")
    if _git(checkout, "rev-parse", "HEAD") != expectations.revision:
        raise ValueError("MemPalace checkout HEAD differs from the pinned revision")
    if _git(checkout, "rev-parse", f"{expectations.revision}^{{tree}}") != expectations.tree:
        raise ValueError("MemPalace checkout tree differs from the pinned tree")
    if _git(checkout, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError("MemPalace checkout must be completely clean")
    origin = _normalize_repository(_git(checkout, "remote", "get-url", "origin"))
    if origin != _normalize_repository(expectations.repository):
        raise ValueError("MemPalace checkout origin differs from the official repository")
    manifest = git_file_manifest(checkout, expectations.revision)
    if (
        len(manifest) != expectations.file_count
        or _manifest_sha256(manifest) != expectations.manifest_sha256
    ):
        raise ValueError("MemPalace Git file manifest differs from the pinned tree")

    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise ValueError(f"refusing to overwrite source context: {output_dir}")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output_dir.name}.tmp-", dir=output_dir.parent)
    )
    archive = staging.parent / f".{output_dir.name}.archive-{os.getpid()}.tar"
    try:
        _archive_checkout(checkout, expectations.revision, archive)
        if _sha256_file(archive) != expectations.archive_sha256:
            raise ValueError("MemPalace Git archive differs from the pinned archive")
        with tarfile.open(archive, mode="r:") as bundle:
            members = bundle.getmembers()
            for member in members:
                _safe_tar_member(member)
            bundle.extractall(staging, members=members, filter="data")
        materialized = _materialized_manifest(staging)
        if materialized != manifest:
            raise ValueError("MemPalace extracted context differs from its Git manifest")
        receipt = _receipt(expectations=expectations, manifest=manifest)
        receipt_path = staging / SOURCE_RECEIPT_NAME
        with receipt_path.open("xb", buffering=0) as handle:
            handle.write((_canonical(receipt) + "\n").encode())
            os.fsync(handle.fileno())
        os.replace(staging, output_dir)
        descriptor = os.open(output_dir.parent, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        return verify_context(output_dir, expectations=expectations)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    finally:
        archive.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    try:
        if args.verify_only:
            if args.checkout is not None:
                parser.error("--verify-only cannot accept --checkout")
            receipt = verify_context(args.output_dir)
        else:
            if args.checkout is None:
                parser.error("--checkout is required unless --verify-only is used")
            receipt = prepare_context(args.checkout, args.output_dir)
    except ValueError as exc:
        parser.error(str(exc))
    print(
        f"{receipt['status']} files={receipt['file_count']} "
        f"manifest={receipt['file_manifest_sha256']} output={args.output_dir.resolve()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
