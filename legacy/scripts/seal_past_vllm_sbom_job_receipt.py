#!/usr/bin/env python3
"""Seal the scanner-bound SBOM job for the pinned PAST vLLM image."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.seal_mempalace_sbom_job_receipt import _seal_job_receipt

TARGET_IMAGE_ID = "sha256:f26809eb13339cbc59c3d0cc972f8c4997830dc8d2121cf18089cb122834e10d"
TARGET_REPO_DIGEST = (
    "docker.io/vllm/vllm-openai@"
    "sha256:f0b9a0dc75a9fca3b6811e3279367b2d6a448055a000bfd13859587d74cef268"
)


def seal_past_vllm_sbom_job(**kwargs: object) -> dict[str, object]:
    if kwargs.get("target_image_id") != TARGET_IMAGE_ID:
        raise ValueError("target image ID differs from the registered vLLM image")
    if kwargs.get("target_repo_digest") != TARGET_REPO_DIGEST:
        raise ValueError("target repository digest differs from the registered vLLM digest")
    return _seal_job_receipt(
        **kwargs,
        expected_job_name="past-vllm-sbom",
        expected_cpus_per_task=8,
        expected_memory_mb=32768,
        receipt_status="SELF_ATTESTED_DISCOVERY_PAST_VLLM_SBOM_JOB",
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
        receipt = seal_past_vllm_sbom_job(
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
