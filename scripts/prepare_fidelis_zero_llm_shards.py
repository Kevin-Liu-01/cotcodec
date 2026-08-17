#!/usr/bin/env python3
"""Prepare deterministic LongMemEval-S shards for the pinned Fidelis runner."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_once(path: Path, payload: Any) -> None:
    if path.exists() or path.is_symlink():
        raise ValueError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = _canonical(payload) + b"\n"
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
        raise ValueError(f"refusing to overwrite {path}") from exc
    finally:
        temporary_path.unlink(missing_ok=True)


def prepare_shards(dataset_path: Path, output_dir: Path, shard_count: int) -> dict[str, Any]:
    if shard_count < 1:
        raise ValueError("shard count must be positive")
    if not dataset_path.is_file() or dataset_path.is_symlink():
        raise ValueError("dataset must be a regular non-symlink file")
    if output_dir.exists() or output_dir.is_symlink():
        raise ValueError(f"refusing to overwrite {output_dir}")
    try:
        payload = json.loads(dataset_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("dataset is not valid JSON") from exc
    if not isinstance(payload, list) or not payload:
        raise ValueError("dataset must contain a non-empty JSON list")

    rows = [row for row in payload if "_abs" not in str(row.get("question_id", ""))]
    question_ids = [row.get("question_id") for row in rows]
    if any(not isinstance(qid, str) or not qid for qid in question_ids):
        raise ValueError("dataset contains an invalid question ID")
    if len(set(question_ids)) != len(question_ids):
        raise ValueError("dataset contains duplicate non-abstention question IDs")
    if shard_count > len(rows):
        raise ValueError("shard count exceeds the non-abstention question count")

    output_dir.mkdir(parents=True)
    base, remainder = divmod(len(rows), shard_count)
    offset = 0
    shards: list[dict[str, Any]] = []
    for index in range(shard_count):
        size = base + (1 if index < remainder else 0)
        shard_rows = rows[offset : offset + size]
        relative = Path(f"shard-{index:02d}") / "longmemeval_s_cleaned.json"
        path = output_dir / relative
        _write_once(path, shard_rows)
        shards.append(
            {
                "index": index,
                "relative_path": relative.as_posix(),
                "row_count": len(shard_rows),
                "first_original_index": offset,
                "last_original_index": offset + size - 1,
                "first_question_id": shard_rows[0]["question_id"],
                "last_question_id": shard_rows[-1]["question_id"],
                "sha256": _sha256(path),
            }
        )
        offset += size

    manifest = {
        "schema_version": 1,
        "status": "FIDELIS_LONGMEMEVAL_SHARDS_PREPARED",
        "source_dataset_sha256": _sha256(dataset_path),
        "source_row_count": len(payload),
        "non_abstention_row_count": len(rows),
        "question_id_root_sha256": hashlib.sha256(_canonical(question_ids)).hexdigest(),
        "shard_count": shard_count,
        "shards": shards,
    }
    _write_once(output_dir / "manifest.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--shards", type=int, default=4)
    args = parser.parse_args()
    try:
        manifest = prepare_shards(args.dataset, args.output_dir, args.shards)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(manifest, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
