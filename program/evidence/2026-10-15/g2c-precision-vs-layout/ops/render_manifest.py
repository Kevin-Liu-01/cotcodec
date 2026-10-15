#!/usr/bin/env python3
"""Render one g2c-precision-layout-v1 docker-research manifest from measured artifacts (stdlib).

Kinds: rollouts (vLLM overlay, seeds bound with --seeds; both arms of one model in turn, each
with its own prefill) and teacher-force (research overlay; study artifact = the rollout job's
tf-input.json, deterministic). G2b's ops/render_manifest.py with the G2c commands. The model
block comes from the host receipt; the image id, git sha and source-capsule hash are passed in
from the build records.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

CACHE = Path("/home/kevin/cotcodec-runs/hf-cache")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--kind", choices=["rollouts", "teacher-force"], required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--smoke", action="store_true")
    p.add_argument("--probe", action="store_true")
    p.add_argument("--minutes", type=int, required=True)
    p.add_argument("--memory-gb", type=int, default=128)
    p.add_argument("--image", required=True)
    p.add_argument("--git-sha", required=True)
    p.add_argument("--source-sha256", required=True)
    p.add_argument("--run-root", required=True)
    p.add_argument("--evidence", default=None)
    p.add_argument("--comment", default="")
    p.add_argument("--out", required=True)
    a = p.parse_args()
    receipt_path = CACHE / "cotcodec-receipts" / f"{a.model}.json"
    receipt = json.loads(receipt_path.read_text())
    cap = math.ceil(a.minutes / 60.0 * 1e4) / 1e4  # round up: the submitter compares exactly
    lines = [
        f"# g2c-precision-layout-v1 (EXPLORATORY) {a.kind}: {a.comment}".rstrip(),
        f"# Slurm limit {a.minutes} min x 1 H100 = {cap} GPU-h cap; the drivers stop starting"
        " work 210 s before it.",
        "runtime: docker-single-node-discovery-v1",
        f"name: {a.name}",
        f"image_id: {a.image}",
        f'git_sha: "{a.git_sha}"',
        f'source_sha256: "{a.source_sha256}"',
        f"run_root: {a.run_root}",
        f"container_profile: {'default' if a.kind == 'teacher-force' else 'vllm'}",
        "resources:",
        "  gpu_type: h100",
        "  gpus: 1",
        "  cpus: 16",
        f"  memory_gb: {a.memory_gb}",
        f"  minutes: {a.minutes}",
        "budget:",
        f"  max_gpu_hours: {cap}",
    ]
    if a.kind == "rollouts":
        lines += [
            "randomness_contract: assignment-seed-matrix",
            "seeds: [42, 43, 44]",
            "seed_binding:",
            '  flag: "--seeds"',
        ]
    else:
        lines += ["randomness_contract: deterministic", "seeds: []"]
    lines += [
        "model:",
        f"  cache_host_path: {CACHE}",
        f"  model_id: {a.model}",
        f'  revision: "{receipt["revision"]}"',
        f'  receipt_sha256: "{sha256(receipt_path)}"',
        f'  artifact_root_sha256: "{receipt["artifact_root_sha256"]}"',
    ]
    if a.kind == "rollouts":
        cmd = [
            "python", "scripts/run_g2c_rollouts.py", "run", "--model", a.model, "--seeds", "42",
            "43", "44", "--output-dir", "/outputs/g2c", "--allocation-minutes", str(a.minutes),
        ]  # fmt: skip
        cmd += (["--smoke"] if a.smoke else []) + (["--probe"] if a.probe else [])
    else:
        evidence = Path(a.evidence)
        digest = sha256(evidence)
        lines += [
            "study_artifact:",
            f"  source_id: g2c-tf-input-{a.model}",
            f'  revision: "{a.git_sha}"',
            "  license: MIT",
            f"  host_path: {evidence}",
            f'  sha256: "{digest}"',
            f"  size_bytes: {evidence.stat().st_size}",
        ]
        cmd = [
            "python", "scripts/run_g2c_teacher_force.py", "run", "--evidence",
            "/inputs/study-artifact.json", "--expected-evidence-sha256", digest, "--model",
            a.model, "--output-dir", "/outputs/g2ctf", "--allocation-minutes", str(a.minutes),
        ]  # fmt: skip
    lines.append("command:")
    lines += [f'  - "{c}"' for c in cmd]
    Path(a.out).write_text("\n".join(lines) + "\n")
    print(a.out)


if __name__ == "__main__":
    main()
