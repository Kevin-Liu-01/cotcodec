#!/usr/bin/env python3
"""Verify the exact retained Qwen snapshot before a PAST model call."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

EXPECTED = {
    "schema_version": 1,
    "model_id": "qwen3.6-35b-a3b",
    "backend": "huggingface",
    "repo_id": "Qwen/Qwen3.6-35B-A3B",
    "revision": "995ad96eacd98c81ed38be0c5b274b04031597b0",
    "mode": "full",
    "publication_eligible": True,
    "trust_remote_code": False,
    "artifact_root_sha256": "8ac6d764b84034f4ed0df3f2388c9180afceab806f7e75f5d1e43a73bdd2736b",
}
EXPECTED_SNAPSHOT = {
    "status": "PRIVATE_MODEL_SNAPSHOT_VERIFIED",
    "file_count": 40,
    "total_bytes": 71926865825,
    "artifact_root_sha256": EXPECTED["artifact_root_sha256"],
}


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _read_object(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"{label} must be a regular non-symlink file")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} is invalid JSON") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must contain one JSON object")
    return value


def verify(*, root: Path, receipt_path: Path, snapshot_receipt_path: Path) -> dict[str, Any]:
    if not root.is_dir() or root.is_symlink():
        raise ValueError("model snapshot must be a regular non-symlink directory")
    receipt = _read_object(receipt_path, "model receipt")
    snapshot_receipt = _read_object(snapshot_receipt_path, "snapshot receipt")
    for key, value in EXPECTED.items():
        if receipt.get(key) != value:
            raise ValueError(f"model receipt field {key!r} drifted")
    if snapshot_receipt != EXPECTED_SNAPSHOT:
        raise ValueError("retained snapshot receipt drifted")
    expected_files = receipt.get("files")
    if not isinstance(expected_files, list):
        raise ValueError("model receipt file roster is invalid")
    actual: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        relative = path.relative_to(root)
        if relative.parts[:2] == (".cache", "huggingface"):
            continue
        if path.is_symlink():
            raise ValueError(f"model snapshot contains a symlink: {relative}")
        if not path.is_file():
            continue
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
        actual.append(
            {
                "path": relative.as_posix(),
                "bytes": path.stat().st_size,
                "sha256": digest.hexdigest(),
            }
        )
    artifact_root = hashlib.sha256(_canonical(actual)).hexdigest()
    if actual != expected_files or artifact_root != EXPECTED["artifact_root_sha256"]:
        raise ValueError("model snapshot file roster or bytes drifted")
    return {
        "schema_version": 1,
        "status": "RETAINED_QWEN_SNAPSHOT_VERIFIED",
        "file_count": len(actual),
        "total_bytes": sum(item["bytes"] for item in actual),
        "artifact_root_sha256": artifact_root,
    }


def _write_once(path: Path, value: Any) -> None:
    payload = json.dumps(value, indent=2, sort_keys=True).encode() + b"\n"
    temporary = path.parent / f".{path.name}.{os.getpid()}.tmp"
    with temporary.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--snapshot-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = verify(
            root=args.root,
            receipt_path=args.receipt,
            snapshot_receipt_path=args.snapshot_receipt,
        )
    except ValueError as exc:
        parser.error(str(exc))
    _write_once(args.output, report)
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
