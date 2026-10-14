#!/usr/bin/env python3
"""Render the six docker-research manifests of inference-baseline-v1 (exploratory).

Usage: render_manifests.py IMAGE_ID OUT_DIR [--receipts receipts.json]
receipts.json maps model id -> {revision, receipt_sha256, artifact_root_sha256}.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

GIT_SHA = "f6eaf1b22f45e1f09b4a3ad844ad6a3f39988135"
SOURCE_SHA256 = "97301983bda277977928e124ab9c535d4d14908d647bc8323e8403c47c35e616"
RUN_ROOT = "/home/kevin/cotcodec-runs/stage0/inference-baseline/runs"
CACHE = "/home/kevin/cotcodec-runs/hf-cache"

# job -> (primary model, GPUs, CPUs, memory GB, Slurm minutes)
JOBS = {
    "a": ("qwen3.5-4b", 1, 16, 128, 55),
    "b": ("qwen3.5-9b", 1, 16, 128, 42),
    "c": ("qwen3.6-35b-a3b", 2, 24, 192, 28),
    "d": ("qwen3-32b", 2, 24, 192, 40),
    "e": ("qwen3-32b", 1, 16, 192, 44),
    "f": ("qwen3-32b", 4, 32, 192, 15),
    # Follow-ups, rendered with --git-sha 3343668a... --source-sha256 e7909353... (second image).
    "g": ("qwen3-32b", 4, 32, 192, 15),
    "h": ("qwen3.6-35b-a3b", 1, 16, 192, 12),
}


def render(job: str, image_id: str, receipts: dict, git_sha: str, source_sha256: str) -> str:
    model, gpus, cpus, memory_gb, minutes = JOBS[job]
    r = receipts[model]
    cap = round(gpus * minutes / 60 + 0.00005, 4)
    return f"""# inference-baseline-v1 job {job}: EXPLORATORY baseline, not a registered experiment.
# Rendered by program/evidence/2026-10-14/inference-baseline/ops/render_manifests.py.
# Slurm limit {minutes} min x {gpus} H100 = {cap} GPU-h cap; the driver stops starting work
# 200 s before the limit. Primary model is verified by the lane; the driver re-verifies others.
runtime: docker-single-node-discovery-v1
name: ib-v1-{job}
image_id: {image_id}
git_sha: "{git_sha}"
source_sha256: "{source_sha256}"
run_root: {RUN_ROOT}/{job}
container_profile: vllm
resources:
  gpu_type: h100
  gpus: {gpus}
  cpus: {cpus}
  memory_gb: {memory_gb}
  minutes: {minutes}
budget:
  max_gpu_hours: {cap}
# Prompt and engine seed 42 come from experiments/serving/inference-baseline-v1.yaml.
randomness_contract: deterministic
seeds: []
model:
  cache_host_path: {CACHE}
  model_id: {model}
  revision: "{r['revision']}"
  receipt_sha256: "{r['receipt_sha256']}"
  artifact_root_sha256: "{r['artifact_root_sha256']}"
command:
  - python
  - scripts/run_inference_baseline.py
  - run
  - --job
  - {job}
  - --output-dir
  - /outputs/ib
  - --allocation-minutes
  - "{minutes}"
"""


def main() -> int:
    image_id, out_dir = sys.argv[1], Path(sys.argv[2])
    receipts = json.loads(Path(sys.argv[4]).read_text()) if "--receipts" in sys.argv else {}
    out_dir.mkdir(parents=True, exist_ok=True)
    jobs = sys.argv[sys.argv.index("--jobs") + 1].split(",") if "--jobs" in sys.argv else JOBS
    git_sha = sys.argv[sys.argv.index("--git-sha") + 1] if "--git-sha" in sys.argv else GIT_SHA
    source = (
        sys.argv[sys.argv.index("--source-sha256") + 1]
        if "--source-sha256" in sys.argv
        else SOURCE_SHA256
    )
    for job in jobs:
        text = render(job, image_id, receipts, git_sha, source)
        (out_dir / f"{job}.yaml").write_text(text, encoding="utf-8")
        print(out_dir / f"{job}.yaml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
