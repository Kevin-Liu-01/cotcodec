#!/usr/bin/env python3
"""Validate and extract one normalized discovery source archive."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import tarfile
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_receipt(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise ValueError("source receipt must be a regular non-symlink file")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("source receipt is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("source receipt must contain one JSON object")
    return payload


def _snapshot_archive(
    archive_path: Path, output_dir: Path
) -> tuple[BinaryIO, str]:
    """Copy one no-follow source handle and return an unlinked private snapshot."""

    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        source_fd = os.open(archive_path, flags)
    except OSError as exc:
        raise ValueError("source archive must be a regular non-symlink file") from exc
    snapshot_path: Path | None = None
    try:
        source_stat = os.fstat(source_fd)
        if not stat.S_ISREG(source_stat.st_mode):
            raise ValueError("source archive must be a regular non-symlink file")
        digest = hashlib.sha256()
        with (
            os.fdopen(source_fd, "rb", closefd=False) as source,
            tempfile.NamedTemporaryFile(
                mode="xb",
                prefix=".source-archive-",
                dir=output_dir,
                delete=False,
            ) as snapshot,
        ):
            snapshot_path = Path(snapshot.name)
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
                snapshot.write(chunk)
            snapshot.flush()
            os.fsync(snapshot.fileno())
        snapshot_fd = os.open(snapshot_path, flags)
        snapshot_stat = os.fstat(snapshot_fd)
        if not stat.S_ISREG(snapshot_stat.st_mode):
            os.close(snapshot_fd)
            raise ValueError("private source archive snapshot is not regular")
        snapshot_path.unlink()
        snapshot_path = None
        return os.fdopen(snapshot_fd, "rb"), digest.hexdigest()
    finally:
        os.close(source_fd)
        if snapshot_path is not None:
            snapshot_path.unlink(missing_ok=True)


def validate_and_extract(
    *,
    archive_path: Path,
    receipt_path: Path,
    output_dir: Path,
    expected_archive_sha256: str,
    expected_git_sha: str,
    expected_git_tree: str,
) -> tuple[str, ...]:
    if not archive_path.is_file() or archive_path.is_symlink():
        raise ValueError("source archive must be a regular non-symlink file")
    if not output_dir.is_dir() or output_dir.is_symlink() or any(output_dir.iterdir()):
        raise ValueError("output must be an existing empty non-symlink directory")
    if re.fullmatch(r"[0-9a-f]{64}", expected_archive_sha256) is None:
        raise ValueError("expected source archive SHA-256 is malformed")
    if re.fullmatch(r"[0-9a-f]{40}", expected_git_sha) is None or re.fullmatch(
        r"[0-9a-f]{40}", expected_git_tree
    ) is None:
        raise ValueError("expected Git identities are malformed")
    archive_snapshot, actual_archive_sha256 = _snapshot_archive(
        archive_path, output_dir
    )
    if actual_archive_sha256 != expected_archive_sha256:
        archive_snapshot.close()
        raise ValueError("source archive SHA-256 drifted")

    receipt = _load_receipt(receipt_path)
    expected_fields = {
        "schema_version": 2,
        "mode": "discovery",
        "archive_sha256": expected_archive_sha256,
        "archive_format": "normalized-worktree-tar+gzip-mtime-zero",
        "git_sha": expected_git_sha,
        "git_tree": expected_git_tree,
        "selected_ref": "HEAD",
        "data_excluded": True,
        "metadata_normalized": True,
    }
    if any(receipt.get(key) != value for key, value in expected_fields.items()):
        raise ValueError("source receipt differs from the registered discovery archive")
    manifest = receipt.get("file_manifest")
    if (
        not isinstance(manifest, list)
        or not manifest
        or any(not isinstance(name, str) or not name for name in manifest)
        or len(set(manifest)) != len(manifest)
        or manifest != sorted(manifest, key=lambda name: name.encode())
    ):
        raise ValueError("source receipt file manifest is malformed")
    manifest_digest = hashlib.sha256(
        json.dumps(manifest, separators=(",", ":")).encode()
    ).hexdigest()
    if (
        receipt.get("file_count") != len(manifest)
        or receipt.get("file_manifest_sha256") != manifest_digest
    ):
        raise ValueError("source receipt file manifest digest drifted")

    extracted_names: list[str] = []
    try:
        with archive_snapshot, tarfile.open(
            fileobj=archive_snapshot, mode="r:gz"
        ) as archive:
            for member in archive:
                member_path = PurePosixPath(member.name)
                if (
                    not member.isfile()
                    or member_path.is_absolute()
                    or ".." in member_path.parts
                    or member.name in extracted_names
                    or member.uid != 0
                    or member.gid != 0
                    or member.mtime != 0
                    or member.mode not in {0o644, 0o755}
                ):
                    raise ValueError("source archive contains an unsafe member")
                if member.name != manifest[len(extracted_names)]:
                    raise ValueError("source archive member order differs from its manifest")
                extracted = archive.extractfile(member)
                if extracted is None:
                    raise ValueError("source archive contains an unreadable member")
                destination = output_dir.joinpath(*member_path.parts)
                destination.parent.mkdir(parents=True, exist_ok=True)
                with destination.open("xb") as handle:
                    while chunk := extracted.read(1024 * 1024):
                        handle.write(chunk)
                    handle.flush()
                    os.fsync(handle.fileno())
                destination.chmod(member.mode)
                extracted_names.append(member.name)
    except (OSError, tarfile.TarError) as exc:
        raise ValueError("source archive is not valid gzip-compressed tar") from exc
    if extracted_names != manifest:
        raise ValueError("source archive differs from its complete file manifest")
    uv_lock = output_dir / "uv.lock"
    if not uv_lock.is_file() or _sha256_file(uv_lock) != receipt.get("uv_lock_sha256"):
        raise ValueError("source archive uv.lock drifted")
    return tuple(extracted_names)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-archive-sha256", required=True)
    parser.add_argument("--expected-git-sha", required=True)
    parser.add_argument("--expected-git-tree", required=True)
    args = parser.parse_args()
    try:
        members = validate_and_extract(
            archive_path=args.archive,
            receipt_path=args.receipt,
            output_dir=args.output_dir,
            expected_archive_sha256=args.expected_archive_sha256,
            expected_git_sha=args.expected_git_sha,
            expected_git_tree=args.expected_git_tree,
        )
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps({"status": "VALIDATED_DISCOVERY_SOURCE", "members": len(members)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
