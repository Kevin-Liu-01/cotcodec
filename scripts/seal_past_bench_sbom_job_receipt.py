#!/usr/bin/env python3
"""Seal a PAST-Bench candidate-image SBOM discovery job."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.seal_mempalace_sbom_job_receipt import _seal_job_receipt

SOURCE_RECEIPT_SHA256 = (
    "5e686206db8d1447d1b18d27bfffdd792f45c9d3418aedc7c15a5d134d6a6a5c"
)
RUNTIME_RECEIPT_SHA256 = (
    "27fb11233ecb18bbdc60ca1c7c0100284b93c87b9fb5d07eb461d028bfd4a64d"
)
EXPECTED_LABELS = {
    "org.opencontainers.image.cotcodec-past-source-receipt-sha256": (
        SOURCE_RECEIPT_SHA256
    ),
    "org.opencontainers.image.cotcodec-past-runtime-contract-sha256": (
        RUNTIME_RECEIPT_SHA256
    ),
    "org.opencontainers.image.cotcodec-publication-ready": "false",
    "org.opencontainers.image.cotcodec-checkpoint-runtime": "episode-boundary-v1",
}


def seal_past_bench_sbom_job(**kwargs: object) -> dict[str, object]:
    return _seal_job_receipt(
        **kwargs,
        expected_job_name="past-bench-sbom",
        expected_cpus_per_task=8,
        expected_memory_mb=32768,
        receipt_status="SELF_ATTESTED_DISCOVERY_PAST_BENCH_SBOM_JOB",
        expected_target_labels=EXPECTED_LABELS,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-inspect", type=Path, required=True)
    parser.add_argument("--syft-inspect", type=Path, required=True)
    parser.add_argument("--publish-target-inspect", type=Path, required=True)
    parser.add_argument("--publish-syft-inspect", type=Path, required=True)
    parser.add_argument("--target-image-id", required=True)
    parser.add_argument("--target-repo-digest", required=True)
    parser.add_argument("--image-archive", type=Path, required=True)
    parser.add_argument("--raw-sbom", type=Path, required=True)
    parser.add_argument("--sealed-sbom", type=Path, required=True)
    parser.add_argument("--annotation-receipt", type=Path, required=True)
    parser.add_argument("--batch-script", type=Path, required=True)
    parser.add_argument("--expected-batch-sha256", required=True)
    parser.add_argument("--gpu-inventory", type=Path, required=True)
    parser.add_argument("--slurm-job-id", type=int, required=True)
    parser.add_argument("--slurm-job-name", required=True)
    parser.add_argument("--slurm-partition", required=True)
    parser.add_argument("--slurm-cpus-per-task", type=int, required=True)
    parser.add_argument("--slurm-memory-mb", type=int, required=True)
    parser.add_argument("--cuda-visible-devices", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        receipt = seal_past_bench_sbom_job(
            target_inspect_path=args.target_inspect,
            syft_inspect_path=args.syft_inspect,
            publish_target_inspect_path=args.publish_target_inspect,
            publish_syft_inspect_path=args.publish_syft_inspect,
            target_image_id=args.target_image_id,
            target_repo_digest=args.target_repo_digest,
            image_archive_path=args.image_archive,
            raw_sbom_path=args.raw_sbom,
            sealed_sbom_path=args.sealed_sbom,
            annotation_receipt_path=args.annotation_receipt,
            batch_script_path=args.batch_script,
            expected_batch_sha256=args.expected_batch_sha256,
            gpu_inventory_path=args.gpu_inventory,
            slurm_job_id=args.slurm_job_id,
            slurm_job_name=args.slurm_job_name,
            slurm_partition=args.slurm_partition,
            slurm_cpus_per_task=args.slurm_cpus_per_task,
            slurm_memory_mb=args.slurm_memory_mb,
            cuda_visible_devices=args.cuda_visible_devices,
            output_path=args.output,
        )
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
