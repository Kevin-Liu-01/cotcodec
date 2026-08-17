#!/usr/bin/env python3
"""Materialize a reviewed native-memory source commit as a Docker named context."""

from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.validate_memory_sources import load_and_validate  # noqa: E402
from scripts.verify_memory_baseline_sources import (  # noqa: E402
    DEFAULT_CONTRACT,
    DEFAULT_LEDGER,
    _canonical_json,
    _git,
    _git_archive_sha256,
    load_contract,
    verify_checkout,
)


class SourceContextError(ValueError):
    """Raised when an exact, safe Docker source context cannot be materialized."""


def _safe_member(member: tarfile.TarInfo) -> None:
    path = PurePosixPath(member.name)
    if path.is_absolute() or ".." in path.parts:
        raise SourceContextError(f"archive contains unsafe path: {member.name}")
    if member.ischr() or member.isblk() or member.isfifo():
        raise SourceContextError(f"archive contains unsupported special file: {member.name}")
    if member.issym() or member.islnk():
        target = PurePosixPath(member.linkname)
        resolved = path.parent.joinpath(target)
        if target.is_absolute() or ".." in resolved.parts:
            raise SourceContextError(f"archive contains unsafe link: {member.name}")


def _tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            kind = "symlink"
            content = os.readlink(path).encode()
        elif path.is_file():
            kind = "file"
            content = path.read_bytes()
        elif path.is_dir():
            kind = "directory"
            content = b""
        else:
            raise SourceContextError(f"context contains unsupported file: {relative}")
        digest.update(f"{kind}\0{relative}\0{len(content)}\0".encode())
        digest.update(content)
    return digest.hexdigest()


def prepare_context(
    system_id: str,
    output_dir: Path,
    *,
    contract_path: Path = DEFAULT_CONTRACT,
    ledger_path: Path = DEFAULT_LEDGER,
) -> dict[str, Any]:
    contract = load_contract(contract_path, ledger_path)
    if system_id not in contract["systems"]:
        raise SourceContextError(f"unknown memory system: {system_id}")
    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise SourceContextError(f"output path already exists: {output_dir}")
    system = contract["systems"][system_id]
    ledger = load_and_validate(ledger_path)
    source = ledger["sources"][system["source_id"]]
    source_receipt = verify_checkout(system_id, system, source)
    checkout = (PROJECT_ROOT / system["checkout"]).resolve()
    revision = system["revision"]
    expected_archive_sha256 = _git_archive_sha256(checkout, revision)
    output_dir.mkdir(parents=True)
    with tempfile.TemporaryFile() as archive:
        completed = subprocess.run(
            ["git", "-C", str(checkout), "archive", "--format=tar", revision],
            stdout=archive,
            stderr=subprocess.PIPE,
            check=False,
        )
        if completed.returncode:
            detail = completed.stderr.decode(errors="replace").strip()
            raise SourceContextError(f"git archive failed: {detail}")
        archive.seek(0)
        digest = hashlib.sha256()
        for chunk in iter(lambda: archive.read(1024 * 1024), b""):
            digest.update(chunk)
        if digest.hexdigest() != expected_archive_sha256:
            raise SourceContextError("materialized archive differs from source preflight")
        archive.seek(0)
        with tarfile.open(fileobj=archive, mode="r:") as tar:
            members = tar.getmembers()
            excluded = set(system.get("excluded_archive_paths", []))
            observed_exclusions: set[str] = set()
            safe_members: list[tarfile.TarInfo] = []
            for member in members:
                if member.name in excluded:
                    try:
                        _safe_member(member)
                    except SourceContextError:
                        observed_exclusions.add(member.name)
                        continue
                    raise SourceContextError(
                        f"registered exclusion is no longer unsafe: {member.name}"
                    )
                _safe_member(member)
                safe_members.append(member)
            if observed_exclusions != excluded:
                missing = sorted(excluded - observed_exclusions)
                raise SourceContextError(
                    f"registered unsafe archive exclusions are missing: {missing}"
                )
            tar.extractall(output_dir, members=safe_members, filter="data")
    if _git(checkout, "status", "--porcelain", "--untracked-files=all"):
        raise SourceContextError("source checkout changed during context materialization")
    payload = {
        "schema_version": "1.0",
        "system_id": system_id,
        "revision": revision,
        "source_archive_sha256": expected_archive_sha256,
        "source_tree_sha": source_receipt["tree_sha"],
        "materialized_tree_sha256": _tree_digest(output_dir),
        "excluded_unsafe_archive_paths": sorted(
            system.get("excluded_archive_paths", [])
        ),
    }
    receipt = {
        **payload,
        "receipt_sha256": hashlib.sha256(_canonical_json(payload).encode()).hexdigest(),
    }
    receipt_path = output_dir / ".cotcodec-source-context.json"
    receipt_path.write_text(_canonical_json(receipt) + "\n", encoding="utf-8")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("system_id")
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    args = parser.parse_args()
    receipt = prepare_context(
        args.system_id,
        args.output_dir,
        contract_path=args.contract,
        ledger_path=args.ledger,
    )
    print(
        f"memory source context PASS: system={args.system_id} "
        f"archive={receipt['source_archive_sha256']} output={args.output_dir.resolve()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
