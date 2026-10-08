#!/usr/bin/env python3
"""Render the docker-research lane manifest of one open-weight rater job.

The open-weight rater (decisions D23 and D27) runs
``harness.q2_mutation.rater_runner open`` in the cu129 vLLM overlay image built
from the submitted commit (``scripts/build_vllm_overlay_on_h100.sh``), with
``container_profile: vllm``, one H100, the rater checkpoint
(``rater_runner.OPEN_WEIGHT``, Qwen3.6-35B-A3B) verified against its model
receipt, and one packet shard mounted read-only as the lane's study artifact.
The job is deterministic (no seed matrix): the engine and request seed is fixed
at 42 in the runner.

GPU caps (preregistration section 9): every job of one audit, all its shards
and reruns together, at most ``AUDIT_GPU_HOURS`` for the confirmatory audit and
``SMOKE_GPU_HOURS`` for a development smoke (D27: the full dev rerate). The
earlier allocations are read from the GPU ledger (``--gpu-ledger``, JSONL), not
given by hand: every manifest this script renders appends its cap there under
its ``--audit-id``, whether or not it is submitted, and a manifest that would
take that audit's total over its cap is refused, as is one whose own
allocation exceeds its cap or a cap above the registered one.

Usage: render_rater_manifest.py --name ... --image-id sha256:... --git-sha ...
         --source-sha256 ... --packets <host path> --packets-revision <sha>
         --run-root <host dir> --minutes N --max-gpu-hours X --kind smoke|audit
         --audit-id <id> --gpu-ledger <ledger.jsonl> --out manifest.yaml
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from harness.q2_mutation.rater_runner import OPEN_WEIGHT  # noqa: E402

# Decision D34: re-measured with thinking on (dev rerate, Slurm 722: 14.4 items
# per minute, 115 s engine start, 72 s of container start, model check and
# stop). The largest confirmatory audit (841 items, six packet shards of at
# most 480 MiB) needs about 2.2 GPU-h at a planning rate of 10 items per
# minute with 4 minutes of start and the 4-minute USR1 lead per job; the cap
# leaves room for a rerun of the rest (preregistration section 9).
AUDIT_GPU_HOURS = 3.0
# Decisions D27 and D34: the development rerate of every dev item with the
# 35B-A3B rater (thinking off, then on), all shards and reruns of one smoke
# together (the earlier 9B smokes were capped at 0.2 and 0.15).
SMOKE_GPU_HOURS = 0.5
LEDGER_SCHEMA = "q2m-rater-gpu-ledger-v1"
MODEL_CACHE = "/home/kevin/cotcodec-runs/hf-cache"
CONTAINER_EVIDENCE = "/inputs/study-artifact.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_ledger(path: Path) -> list[dict[str, object]]:
    """The rows of the rater GPU ledger (an absent ledger has none)."""
    if not path.exists():
        return []
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict) or row.get("schema") != LEDGER_SCHEMA:
            raise SystemExit(f"{path}:{number}: not a {LEDGER_SCHEMA} row")
        rows.append(row)
    return rows


def prior_gpu_hours(rows: list[dict[str, object]], audit_id: str, kind: str) -> float:
    """GPU-hour caps of the jobs already rendered for this audit."""
    hours = 0.0
    for row in rows:
        if row["audit_id"] != audit_id:
            continue
        if row["kind"] != kind:
            raise SystemExit(f"audit {audit_id} has {row['kind']} jobs in the ledger, not {kind}")
        hours += float(row["max_gpu_hours"])  # type: ignore[arg-type]
    return hours


def job_cap(args: argparse.Namespace) -> float:
    """The registered cap of the job's kind; refuses a job over it or over its own cap."""
    cap = SMOKE_GPU_HOURS if args.kind == "smoke" else AUDIT_GPU_HOURS
    if args.max_gpu_hours > cap:
        raise SystemExit(f"{args.kind} jobs are capped at {cap} GPU-h")
    if args.minutes / 60 > args.max_gpu_hours:
        raise SystemExit("the allocation exceeds the job's GPU-hour cap")
    return cap


def manifest(args: argparse.Namespace, prior: float = 0.0) -> dict[str, object]:
    cap = job_cap(args)
    if prior + args.max_gpu_hours > cap + 1e-9:
        raise SystemExit(
            f"earlier shards and reruns of {args.audit_id} in the ledger ({prior:.4f} GPU-h) "
            f"plus this job ({args.max_gpu_hours} GPU-h) exceed the {args.kind} cap of "
            f"{cap} GPU-h"
        )
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
    parser.add_argument(
        "--audit-id",
        required=True,
        help="the audit or smoke this job belongs to; its ledger rows share the cap",
    )
    parser.add_argument(
        "--gpu-ledger",
        type=Path,
        required=True,
        help="JSONL ledger of every rater job rendered (read for the cap, then appended)",
    )
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    job_cap(args)
    if args.out.exists():
        raise SystemExit(f"{args.out} exists; render each job once (its cap is in the ledger)")
    rows = read_ledger(args.gpu_ledger)
    if any(row["name"] == args.name for row in rows):
        raise SystemExit(f"the ledger already has a job named {args.name}")
    prior = prior_gpu_hours(rows, args.audit_id, args.kind)
    data = manifest(args, prior)
    import yaml

    args.out.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    row = {
        "schema": LEDGER_SCHEMA,
        "audit_id": args.audit_id,
        "kind": args.kind,
        "name": args.name,
        "minutes": args.minutes,
        "max_gpu_hours": args.max_gpu_hours,
        "prior_gpu_hours": round(prior, 6),
        "git_sha": args.git_sha,
        "packets_sha256": data["study_artifact"]["sha256"],  # type: ignore[index]
        "manifest": str(args.out),
        "rendered_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),  # noqa: UP017
    }
    args.gpu_ledger.parent.mkdir(parents=True, exist_ok=True)
    with args.gpu_ledger.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "out": str(args.out),
                "study_artifact": data["study_artifact"],
                "audit_gpu_hours_after": round(prior + args.max_gpu_hours, 6),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
