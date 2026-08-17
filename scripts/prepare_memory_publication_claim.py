#!/usr/bin/env python3
"""Prepare the exact complete-wave payload for offline administrator signing."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from harness.publication_attestation import publication_claim_bindings
from scripts.compile_memory_public_docker_job import DEFAULT_EXPERIMENT
from scripts.compile_memory_publication_wave import preview_publication_wave
from scripts.fetch_open_model import DEFAULT_REGISTRY
from scripts.submit_docker_research_job import BATCH_SCRIPT


def _write_new(path: Path, payload: dict) -> None:
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
    with path.open("xb", buffering=0) as handle:
        handle.write(encoded)
        os.fsync(handle.fileno())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--publication-capsule", type=Path, required=True)
    parser.add_argument("--control-matrix-dir", type=Path, required=True)
    parser.add_argument("--publication-trust-store-sha256", required=True)
    parser.add_argument("--model-receipt-sha256", required=True)
    parser.add_argument("--model-artifact-root", required=True)
    parser.add_argument("--model-id", default="qwen3.6-35b-a3b")
    parser.add_argument("--experiment", type=Path, default=DEFAULT_EXPERIMENT)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error(f"refusing to overwrite claim preview: {args.output_dir}")
    wave = preview_publication_wave(
        publication_capsule_path=args.publication_capsule,
        control_matrix_dir=args.control_matrix_dir,
        model_receipt_sha256=args.model_receipt_sha256,
        model_artifact_root=args.model_artifact_root,
        publication_trust_store_sha256=args.publication_trust_store_sha256,
        model_id=args.model_id,
        experiment_path=args.experiment,
        registry_path=args.registry,
    )
    bindings = publication_claim_bindings(
        capsule_path=args.publication_capsule,
        matrix_path=args.control_matrix_dir / "manifest.json",
        experiment_path=args.experiment,
        wave=wave,
        batch_script_path=BATCH_SCRIPT,
    )
    args.output_dir.mkdir(parents=True)
    _write_new(args.output_dir / "wave-contract.json", wave)
    _write_new(args.output_dir / "claim-bindings.json", bindings)
    descriptor = os.open(args.output_dir, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    print(json.dumps(bindings, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
