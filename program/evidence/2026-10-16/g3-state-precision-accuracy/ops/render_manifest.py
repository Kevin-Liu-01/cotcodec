#!/usr/bin/env python3
"""Render one g3-state-precision-accuracy-v1 docker-research manifest (stdlib).

Kinds: run (vLLM overlay; one model x arm; the math worker then the long-context worker;
LongMemEval-S mounted as the lane's hash-bound public benchmark; seeds bound with --seeds) and
judge (vLLM overlay; AM1's primary judge Qwen3-32B; study artifact = the judge input built on the
host from the main run's replies; deterministic). G2c's ops/render_manifest.py with the G3
commands. The model block comes from the host receipt; the image id, git sha and source-capsule
hash are passed in from the build records.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

CACHE = Path("/home/kevin/cotcodec-runs/hf-cache")
LME = Path(
    "/home/kevin/cotcodec-runs/inputs/longmemeval/98d7416c24c778c2fee6e6f3006e7a073259d48f/"
    "longmemeval_s_cleaned.json"
)
LME_SHA256 = "d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442"
LME_REVISION = "98d7416c24c778c2fee6e6f3006e7a073259d48f"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--kind", choices=["run", "judge"], required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--phase", choices=["pilot", "main"], default=None)
    p.add_argument("--arm", choices=["fp32", "fp16", "bf16"], default=None)
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
        f"# g3-state-precision-accuracy-v1 (EXPLORATORY) {a.kind}: {a.comment}".rstrip(),
        f"# Slurm limit {a.minutes} min x 1 H100 = {cap} GPU-h cap; the drivers stop starting"
        " work 210 s before it.",
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
    ]
    if a.kind == "run":
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
    if a.kind == "run":
        if a.phase is None or a.arm is None:
            raise SystemExit("run needs --phase and --arm")
        lines += [
            "public_benchmark:",
            "  source_id: longmemeval-s-cleaned",
            f'  revision: "{LME_REVISION}"',
            "  license: MIT",
            f"  host_path: {LME}",
            f'  sha256: "{LME_SHA256}"',
            f"  size_bytes: {LME.stat().st_size}",
        ]
        cmd = [
            "python", "scripts/run_g3_accuracy.py", "run", "--phase", a.phase, "--model", a.model,
            "--arm", a.arm, "--seeds", "42", "43", "44", "--output-dir", "/outputs/g3",
            "--allocation-minutes", str(a.minutes), "--longmemeval-path",
            "/inputs/longmemeval_s_cleaned.json",
        ]  # fmt: skip
    else:
        evidence = Path(a.evidence)
        digest = sha256(evidence)
        lines += [
            "study_artifact:",
            "  source_id: g3-judge-input",
            f'  revision: "{a.git_sha}"',
            "  license: MIT",
            f"  host_path: {evidence}",
            f'  sha256: "{digest}"',
            f"  size_bytes: {evidence.stat().st_size}",
        ]
        cmd = [
            "python", "scripts/run_g3_accuracy.py", "judge", "--evidence",
            "/inputs/study-artifact.json", "--expected-evidence-sha256", digest, "--output-dir",
            "/outputs/g3judge", "--allocation-minutes", str(a.minutes),
        ]  # fmt: skip
    lines.append("command:")
    lines += [f'  - "{c}"' for c in cmd]
    Path(a.out).write_text("\n".join(lines) + "\n")
    print(a.out)


if __name__ == "__main__":
    main()
