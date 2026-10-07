#!/usr/bin/env python3
"""Validate and extract one normalized discovery source archive.

Accepts schema 3 receipts, which record the tracked agent-tooling links the
creator left out, and schema 2 receipts (no omission record) for the capsules
retained before schema 3 only. Omitted links are validated against the
archive's manifest and never recreated: the extracted tree holds regular files
only. This file runs as a standalone snapshot (under the host's python3), so it
carries its own copy of the creator's rules table and lexical omission rule.
"""

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

# Must equal OMITTABLE_SYMLINK_RULES in scripts/create_source_archive.py.
OMITTABLE_SYMLINK_RULES: tuple[tuple[str, str], ...] = ((".agents/skills/", ".claude/skills/"),)
SYMLINK_RECEIPT_FIELDS = (
    "omittable_symlink_rules",
    "omitted_symlinks",
    "omitted_symlinks_sha256",
)
# Schema 2 receipts carry no omission record. Nothing the lane pins binds that
# record, so a schema 3 receipt with its record stripped would read as schema
# 2; schema 2 is therefore accepted only for these capsules, built before
# schema 3. Extract any other schema 2 capsule with the extractor revision
# pinned when it was built.
SCHEMA_2_RETAINED_ARCHIVE_SHA256 = frozenset(
    {
        # serving-throughput-probe-v1 at 80a87ee; receipt retained in
        # program/evidence/2026-10-07/serving-throughput-probe-v1/capsule/.
        "2c607c86d83c0b023bddb28ac22ed7fa2541c816ac8b6b16370d83bc3fb4d5b9",
    }
)


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


def omitted_symlink_target(link: str, target: str) -> str:
    """Return the repository path an omittable link names, or raise ValueError.

    Lexical, and identical in create_source_archive.py and
    extract_discovery_source_archive.py (a test compares the source).
    The link is a canonical relative path under a reviewed link prefix. The
    target is canonical: a run of `..` and then at least one named part, with no
    empty, `.` or `..` part after it, so it resolves on disk exactly as it does
    here whenever no directory it passes is a symlink. It stays inside the
    repository and resolves under the rule's target prefix.
    """

    def named(parts: list[str]) -> bool:
        return bool(parts) and all(
            part not in {"", ".", ".."} and "\0" not in part for part in parts
        )

    link_parts = link.split("/")
    rule = next((rule for rule in OMITTABLE_SYMLINK_RULES if link.startswith(rule[0])), None)
    if rule is None or not named(link_parts):
        raise ValueError(
            "source archive forbids symlinks outside the reviewed agent-tooling "
            f"rules {[list(rule) for rule in OMITTABLE_SYMLINK_RULES]}: {link!r}"
        )
    target_parts = target.split("/")
    climb = 0
    while climb < len(target_parts) and target_parts[climb] == "..":
        climb += 1
    if not named(target_parts[climb:]):
        raise ValueError(
            f"symlink target is not a canonical relative path: {link} -> {target!r}"
        )
    directory = link_parts[:-1]
    if climb > len(directory):
        raise ValueError(f"symlink target escapes the repository: {link} -> {target}")
    resolved = "/".join(directory[: len(directory) - climb] + target_parts[climb:])
    if not resolved.startswith(rule[1]):
        raise ValueError(
            f"symlink target is outside the reviewed target prefix {rule[1]!r}: "
            f"{link} -> {target}"
        )
    return resolved


def _validate_omitted_symlinks(receipt: dict[str, Any], manifest: list[str]) -> None:
    """Check a schema 3 receipt's omitted links name content the archive holds."""

    if receipt.get("omittable_symlink_rules") != [list(rule) for rule in OMITTABLE_SYMLINK_RULES]:
        raise ValueError("source receipt records a different symlink omission rule")
    rows = receipt.get("omitted_symlinks")
    if not isinstance(rows, list) or any(
        not isinstance(row, dict)
        or set(row) != {"path", "target"}
        or not all(isinstance(row[key], str) and row[key] for key in ("path", "target"))
        for row in rows
    ):
        raise ValueError("source receipt omitted symlinks are malformed")
    links = [row["path"] for row in rows]
    if len(set(links)) != len(links) or links != sorted(links, key=lambda name: name.encode()):
        raise ValueError("source receipt omitted symlinks are malformed")
    digest = hashlib.sha256(
        json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    if receipt.get("omitted_symlinks_sha256") != digest:
        raise ValueError("source receipt omitted symlink digest drifted")
    archived = set(manifest)

    def holds(name: str) -> bool:
        return name in archived or any(member.startswith(f"{name}/") for member in manifest)

    for row in rows:
        resolved = omitted_symlink_target(row["path"], row["target"])
        if holds(row["path"]) or any(
            parent.as_posix() in archived for parent in PurePosixPath(row["path"]).parents
        ):
            raise ValueError(f"omitted symlink collides with an archived file: {row['path']}")
        if not holds(resolved):
            raise ValueError(
                f"omitted symlink target is not archived content: {row['path']} -> {row['target']}"
            )


def _validated_manifest(
    receipt: dict[str, Any],
    *,
    expected_archive_sha256: str,
    expected_git_sha: str,
    expected_git_tree: str,
) -> list[str]:
    """Check a discovery receipt against the registered identities; return its manifest."""

    schema_version = receipt.get("schema_version")
    if type(schema_version) is not int or schema_version not in {2, 3}:
        raise ValueError("source receipt differs from the registered discovery archive")
    expected_fields = {
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
    if schema_version == 2:
        if expected_archive_sha256 not in SCHEMA_2_RETAINED_ARCHIVE_SHA256:
            raise ValueError(
                "schema 2 source receipts are accepted only for capsules retained "
                "before schema 3"
            )
        if any(key in receipt for key in SYMLINK_RECEIPT_FIELDS):
            raise ValueError("schema 2 source receipt cannot record omitted symlinks")
    else:
        _validate_omitted_symlinks(receipt, manifest)
    return manifest


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
    try:
        if actual_archive_sha256 != expected_archive_sha256:
            raise ValueError("source archive SHA-256 drifted")
        receipt = _load_receipt(receipt_path)
        manifest = _validated_manifest(
            receipt,
            expected_archive_sha256=expected_archive_sha256,
            expected_git_sha=expected_git_sha,
            expected_git_tree=expected_git_tree,
        )
    except BaseException:
        archive_snapshot.close()
        raise

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
