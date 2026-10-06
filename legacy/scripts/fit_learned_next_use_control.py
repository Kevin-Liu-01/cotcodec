#!/usr/bin/env python3
"""Fit and seal the generated-data learned-next-use control on CPU."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.memory_trials import (  # noqa: E402
    GeneratedMemoryTaskSource,
    MemoryBudget,
    SplitCounts,
    fit_learned_next_use,
    make_exact_family_split,
)
from harness.memory_trials.schema import canonical_json, sha256_text  # noqa: E402


def _write_json(path: Path, payload: dict[str, Any]) -> str:
    encoded = (canonical_json(payload) + "\n").encode()
    with path.open("xb", buffering=0) as handle:
        handle.write(encoded)
        os.fsync(handle.fileno())
    return hashlib.sha256(encoded).hexdigest()


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def compile_learned_control_artifacts(
    output_dir: Path,
    *,
    source: GeneratedMemoryTaskSource,
    counts: SplitCounts,
    split_seed: int,
    training_iterations: int = 250,
    learning_rate: float = 0.1,
) -> dict[str, Any]:
    """Publish the split, fitted weights, and a binding receipt atomically."""

    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise ValueError(f"refusing to overwrite learned-control artifacts: {output_dir}")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output_dir.name}.tmp-", dir=output_dir.parent)
    )
    try:
        split_manifest = make_exact_family_split(
            source,
            counts=counts,
            split_seed=split_seed,
        )
        artifact = fit_learned_next_use(
            source,
            split_manifest,
            training_iterations=training_iterations,
            learning_rate=learning_rate,
        )
        split_payload = split_manifest.model_dump(mode="json")
        artifact_payload = artifact.model_dump(mode="json")
        split_file_sha256 = _write_json(staging / "split-manifest.json", split_payload)
        artifact_file_sha256 = _write_json(
            staging / "learned-next-use-artifact.json",
            artifact_payload,
        )
        unsigned = {
            "schema_version": 1,
            "status": "FROZEN_LEARNED_CONTROL",
            "scientific_result": False,
            "reason": (
                "Noncausal comparator artifact only; generated labels and fitted "
                "weights are not a memory-policy result."
            ),
            "source": {
                **source.provenance,
                "budget": source.budget.model_dump(mode="json"),
            },
            "split_manifest_sha256": split_manifest.manifest_sha256,
            "learned_artifact_sha256": artifact.artifact_sha256,
            "files": {
                "split-manifest.json": split_file_sha256,
                "learned-next-use-artifact.json": artifact_file_sha256,
            },
            "fit": {
                "training_iterations": training_iterations,
                "learning_rate": learning_rate,
                "selected_l2": artifact.selected_l2,
                "label_splits": list(artifact.label_splits),
                "test_labels_opened": False,
            },
        }
        manifest = {
            **unsigned,
            "manifest_sha256": sha256_text(canonical_json(unsigned)),
        }
        _write_json(staging / "manifest.json", manifest)
        _fsync_directory(staging)
        os.replace(staging, output_dir)
        _fsync_directory(output_dir.parent)
        return manifest
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--episodes", type=int, default=2_400)
    parser.add_argument("--source-seed", type=int, default=7)
    parser.add_argument("--split-seed", type=int, default=42)
    parser.add_argument("--train", type=int, default=1_440)
    parser.add_argument("--dev", type=int, default=480)
    parser.add_argument("--test", type=int, default=480)
    parser.add_argument("--training-iterations", type=int, default=250)
    parser.add_argument("--learning-rate", type=float, default=0.1)
    parser.add_argument("--active-slots", type=int, default=4)
    parser.add_argument("--max-archive-reads", type=int, default=1)
    parser.add_argument("--retrieval-top-k", type=int, default=4)
    parser.add_argument("--max-injected-tokens", type=int, default=256)
    args = parser.parse_args()
    source = GeneratedMemoryTaskSource(
        seed=args.source_seed,
        episode_count=args.episodes,
        budget=MemoryBudget(
            active_slots=args.active_slots,
            max_archive_reads=args.max_archive_reads,
            retrieval_top_k=args.retrieval_top_k,
            max_injected_tokens=args.max_injected_tokens,
        ),
    )
    manifest = compile_learned_control_artifacts(
        args.output_dir,
        source=source,
        counts=SplitCounts(train=args.train, dev=args.dev, test=args.test),
        split_seed=args.split_seed,
        training_iterations=args.training_iterations,
        learning_rate=args.learning_rate,
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
