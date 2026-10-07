#!/usr/bin/env python3
"""Render the docker-research lane manifest of one open-weight rater job.

The open-weight rater (decision D23) runs ``harness.q2_mutation.rater_runner
open`` in the cu129 vLLM overlay image built from the submitted commit
(``scripts/build_vllm_overlay_on_h100.sh``), with ``container_profile: vllm``,
one H100, the Qwen3.5-9B checkpoint verified against its model receipt, and
one packet shard mounted read-only as the lane's study artifact. The job is
deterministic (no seed matrix): the engine and request seed is fixed at 42 in
the runner.

GPU caps (preregistration section 9): the whole confirmatory audit, every
shard and any rerun together, at most ``AUDIT_GPU_HOURS``; a development
smoke at most ``SMOKE_GPU_HOURS``. This script refuses a manifest whose
allocation exceeds the cap it is given or a cap above the registered one.

Usage: render_rater_manifest.py --name ... --image-id sha256:... --git-sha ...
         --source-sha256 ... --packets <host path> --packets-revision <sha>
         --run-root <host dir> --minutes N --max-gpu-hours X --kind smoke|audit
         --out manifest.yaml
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from harness.q2_mutation.rater_runner import OPEN_WEIGHT  # noqa: E402

AUDIT_GPU_HOURS = 1.0
SMOKE_GPU_HOURS = 0.2
MODEL_CACHE = "/home/kevin/cotcodec-runs/hf-cache"
CONTAINER_EVIDENCE = "/inputs/study-artifact.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manifest(args: argparse.Namespace) -> dict[str, object]:
    cap = SMOKE_GPU_HOURS if args.kind == "smoke" else AUDIT_GPU_HOURS
    if args.max_gpu_hours > cap:
        raise SystemExit(f"{args.kind} jobs are capped at {cap} GPU-h")
    if args.minutes / 60 > args.max_gpu_hours:
        raise SystemExit("the allocation exceeds the job's GPU-hour cap")
    packets = Path(args.packets)
    digest = sha256_file(packets)
    return {
        "runtime": "docker-single-node-discovery-v1",
        "name": args.name,
        "image_id": args.image_id,
        "git_sha": args.git_sha,
        "source_sha256": args.source_sha256,
        "run_root": args.run_root,
        "container_profile": "vllm",
        "resources": {
            "gpu_type": "h100",
            "gpus": 1,
            "cpus": 16,
            "memory_gb": 128,
            "minutes": args.minutes,
        },
        "budget": {"max_gpu_hours": args.max_gpu_hours},
        "randomness_contract": "deterministic",
        "seeds": [],
        "model": {
            "cache_host_path": MODEL_CACHE,
            "model_id": OPEN_WEIGHT["model_id"],
            "revision": OPEN_WEIGHT["revision"],
            "receipt_sha256": OPEN_WEIGHT["receipt_sha256"],
            "artifact_root_sha256": OPEN_WEIGHT["artifact_root_sha256"],
        },
        "study_artifact": {
            "source_id": args.source_id,
            "revision": args.packets_revision,
            "license": "Apache-2.0",
            "host_path": str(packets),
            "sha256": digest,
            "size_bytes": packets.stat().st_size,
        },
        "command": [
            "python",
            "-m",
            "harness.q2_mutation.rater_runner",
            "open",
            "--evidence",
            CONTAINER_EVIDENCE,
            "--expected-evidence-sha256",
            digest,
            "--output-dir",
            "/outputs/rater",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    parser.add_argument("--name", required=True)
    parser.add_argument("--image-id", required=True)
    parser.add_argument("--git-sha", required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--packets", required=True)
    parser.add_argument("--packets-revision", required=True)
    parser.add_argument("--source-id", default="q2m-audit-packets")
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--minutes", type=int, required=True)
    parser.add_argument("--max-gpu-hours", type=float, required=True)
    parser.add_argument("--kind", choices=["smoke", "audit"], required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    data = manifest(args)
    import yaml

    args.out.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    print(json.dumps({"out": str(args.out), "study_artifact": data["study_artifact"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
