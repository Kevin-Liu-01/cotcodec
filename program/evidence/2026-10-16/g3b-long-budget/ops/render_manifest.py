#!/usr/bin/env python3
"""Render one g3b-long-budget-v1 docker-research manifest (stdlib).

One model x arm x phase: scripts/run_g3b_long_budget.py run (vLLM overlay, the math worker; seeds
bound with --seeds). G3's ops/render_manifest.py with the G3b command and no public benchmark
(the math prompts are baked into the image). The model block comes from the host receipt; the
image id, git sha and source-capsule hash are passed in from the build records.
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
    p.add_argument("--name", required=True)
    p.add_argument("--model", default="qwen3.5-4b")
    p.add_argument("--phase", choices=["pilot", "main", "aa"], required=True)
    p.add_argument("--arm", choices=["fp32", "bf16", "fp32_aa"], required=True)
    p.add_argument("--minutes", type=int, required=True)
    p.add_argument("--memory-gb", type=int, default=128)
    p.add_argument("--image", required=True)
    p.add_argument("--git-sha", required=True)
    p.add_argument("--source-sha256", required=True)
    p.add_argument("--run-root", required=True)
    p.add_argument("--comment", default="")
    p.add_argument("--out", required=True)
    a = p.parse_args()
    receipt_path = CACHE / "cotcodec-receipts" / f"{a.model}.json"
    receipt = json.loads(receipt_path.read_text())
    cap = math.ceil(a.minutes / 60.0 * 1e4) / 1e4  # round up: the submitter compares exactly
    lines = [
        f"# g3b-long-budget-v1 (EXPLORATORY) run: {a.comment}".rstrip(),
        f"# Slurm limit {a.minutes} min x 1 H100 = {cap} GPU-h cap; the driver stops generating"
        " about 3 min before it.",
        "runtime: docker-single-node-discovery-v1",
        f"name: {a.name}",
        f"image_id: {a.image}",
        f'git_sha: "{a.git_sha}"',
        f'source_sha256: "{a.source_sha256}"',
        f"run_root: {a.run_root}",
        "container_profile: vllm",
        "resources:",
        "  gpu_type: h100",
        "  gpus: 1",
        "  cpus: 16",
        f"  memory_gb: {a.memory_gb}",
        f"  minutes: {a.minutes}",
        "budget:",
        f"  max_gpu_hours: {cap}",
        "randomness_contract: assignment-seed-matrix",
        "seeds: [42, 43, 44]",
        "seed_binding:",
        '  flag: "--seeds"',
        "model:",
        f"  cache_host_path: {CACHE}",
        f"  model_id: {a.model}",
        f'  revision: "{receipt["revision"]}"',
        f'  receipt_sha256: "{sha256(receipt_path)}"',
        f'  artifact_root_sha256: "{receipt["artifact_root_sha256"]}"',
    ]
    cmd = [
        "python", "scripts/run_g3b_long_budget.py", "run", "--phase", a.phase, "--model", a.model,
        "--arm", a.arm, "--seeds", "42", "43", "44", "--output-dir", "/outputs/g3b",
        "--allocation-minutes", str(a.minutes),
    ]  # fmt: skip
    lines.append("command:")
    lines += [f'  - "{c}"' for c in cmd]
    Path(a.out).write_text("\n".join(lines) + "\n")
    print(a.out)


if __name__ == "__main__":
    main()
