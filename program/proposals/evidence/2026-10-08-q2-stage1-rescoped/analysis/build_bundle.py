"""Assemble bundle.json for the q2-stage1-rescoped gauntlet proposal (wave 0).

Hashes every artifact, binds the proposal by SHA-256 and computes evidence_root_sha256 exactly as
scripts/research_direction_doctor.py does. Usage (from the bundle directory):
python analysis/build_bundle.py ../../2026-10-08-q2-stage1-rescoped.md
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(".").resolve()
proposal = Path(sys.argv[1]).resolve()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def art(rel: str, **extra) -> dict:
    return {"artifact": rel, "sha256": sha(HERE / rel), **extra}


snapshots = json.loads((HERE / "analysis/snapshot-index.json").read_text())
for rec in snapshots:
    rec["sha256"] = sha(HERE / rec["artifact"])
doctors = []
for name in ("source", "citation", "novelty", "design", "compute", "safety"):
    rec = json.loads((HERE / f"doctors/{name}.json").read_text())
    doctors.append({"name": rec["doctor"], "status": rec["status"], **art(f"doctors/{name}.json")})
compute = {
    "scope": (
        "No S1a job has run (compute/s1a-attestations-not-run.md). The engine image named is"
        " the cost card's base image; the S1a overlay, manifest, dry-run, smoke and orx node"
        " do not exist."
    ),
    "image_digest": (
        "docker.io/vllm/vllm-openai"
        "@sha256:b18abb2df97b8f798e81862bd93f872ea18613372e2c3adc0cc2ac21e66ac12f"
    ),
    "real_model_loop": False,
    "real_model_loop_scope": (
        "The S1a episode driver (harness/q2/stage1/) is a G0 item and does not exist yet."
    ),
    "benchmark_adapter": None,
    "note": art("compute/s1a-attestations-not-run.md"),
}
analyses = [
    art(p)
    for p in (
        "analysis/cost_s1a.py",
        "analysis/cost_s1a.json",
        "analysis/sim_s1a.py",
        "analysis/sim_s1a.json",
        "analysis/sim_signflip.py",
        "analysis/sim_signflip.json",
        "analysis/task_draw.py",
        "analysis/task-draw-K32.json",
        "analysis/task-draw-K24.json",
        "analysis/task-draw-K16.json",
        "analysis/snapshot_sources.py",
        "analysis/snapshot-index.json",
        "analysis/build_bundle.py",
    )
]
bundle = {
    "schema_version": 1,
    "proposal": "program/proposals/2026-10-08-q2-stage1-rescoped.md",
    "proposal_sha256": sha(proposal),
    "source_snapshots": snapshots,
    "query_log": art("query-log.json", queries_against_budget=10, full_text_reads=3),
    "reviews": [],
    "reviews_status": "NOT_RUN: wave 0 is synthesis only; no trusted Ed25519 store exists (D24)",
    "compute": compute,
    "doctors": doctors,
    "audit_log": None,
    "audit_log_status": (
        "No hash-chained row: it is appended to program/gauntlet/ after the reviewers score"
    ),
    "synthesis_analyses": analyses,
}
if (HERE / "doctors/direction-doctor-output.json").is_file():
    bundle["direction_doctor_run"] = art("doctors/direction-doctor-output.json")
payload = {
    k: bundle.get(k) for k in ("source_snapshots", "query_log", "compute", "doctors", "audit_log")
}
bundle["evidence_root_sha256"] = hashlib.sha256(
    json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
).hexdigest()
(HERE / "bundle.json").write_text(json.dumps(bundle, indent=1) + "\n")
print(bundle["proposal_sha256"], bundle["evidence_root_sha256"])
