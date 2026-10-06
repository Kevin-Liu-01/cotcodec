#!/usr/bin/env python3
"""Compile sealed TRAIN trajectories and generations into a bank-input artifact."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.memory_trials.procedural_bank import ProceduralSplitManifest  # noqa: E402
from harness.memory_trials.procedural_induction import (  # noqa: E402
    compile_procedural_induction,
)


def _load_split(path: Path) -> ProceduralSplitManifest:
    if path.is_symlink() or not path.is_file():
        raise ValueError("split manifest must be a regular file")
    payload = json.loads(path.read_text(encoding="utf-8"))
    return ProceduralSplitManifest.model_validate(payload)


def _atomic_no_replace(path: Path, encoded: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        raise FileExistsError(f"output already exists: {path}")
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
        temporary = Path(handle.name)
    try:
        os.link(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split-manifest", type=Path, required=True)
    parser.add_argument("--expected-split-manifest-sha256", required=True)
    parser.add_argument("--trajectories", type=Path, required=True)
    parser.add_argument("--generations", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    artifact = compile_procedural_induction(
        trajectory_jsonl=args.trajectories,
        generation_jsonl=args.generations,
        split_manifest=_load_split(args.split_manifest),
        expected_split_manifest_sha256=args.expected_split_manifest_sha256,
    )
    encoded = (
        json.dumps(artifact.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    _atomic_no_replace(args.output, encoded)
    print(
        json.dumps(
            {
                "status": "PROCEDURAL_INDUCTION_COMPILED",
                "artifact_sha256": artifact.artifact_sha256,
                "train_tasks": artifact.trajectory_count,
                "procedures": artifact.procedure_count,
                "scientific_result": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
