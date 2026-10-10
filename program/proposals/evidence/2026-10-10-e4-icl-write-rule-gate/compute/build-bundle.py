#!/usr/bin/env python3
"""Assemble bundle.json for the E4 gate gauntlet from the files in this bundle.

Hashes every artifact, computes evidence_root_sha256 exactly as
scripts/research_direction_doctor.py does (over source_snapshots, query_log,
compute, doctors, audit_log), and records the proposal and draft-registration
hashes. Run from the worktree root after any change to the proposal or an
artifact:

    python3 program/proposals/evidence/2026-10-10-e4-icl-write-rule-gate/compute/build-bundle.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
BUNDLE = ROOT / "program/proposals/evidence/2026-10-10-e4-icl-write-rule-gate"
PROPOSAL = ROOT / "program/proposals/2026-10-10-e4-icl-write-rule-gate.md"
REGISTRATION = ROOT / "program/preregistrations/e4-icl-write-rule-gate-v1.md"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def art(rel: str, **extra) -> dict:
    return {"artifact": rel, "sha256": sha(BUNDLE / rel), **extra}


def main() -> None:
    snapshots = []
    for path in sorted((BUNDLE / "snapshots").glob("*.json")):
        rec = json.loads(path.read_text(encoding="utf-8"))
        snapshots.append({"url": rec["url"], "http_status": rec["http_status"], "fetched_at": rec["fetched_at"],
                          "raw_sha256": rec["raw_sha256"], "raw_bytes": rec["raw_bytes"],
                          **art(f"snapshots/{path.name}")})
    qlog = json.loads((BUNDLE / "query-log.json").read_text(encoding="utf-8"))
    not_run = "compute/attestations-not-run.md"
    compute = {
        "scope": "e4-icl-write-rule-gate-v1 is a DRAFT; no compute attestation of its own exists (compute/attestations-not-run.md). Supplementary CPU evidence: simulations S1 (oracle-class semantics, KILL A), S2 (decision-rule operating characteristics) and S3 (cost model), each script with its output.",
        "image_digest": "127.0.0.1:5000/cotcodec-research@sha256:13a9de831cff50461d8ecee3c2794f0c6d6bcffe9d602968fe2ee06e5a1096e9",
        "image_scope": "build 855, commit ed5d5a93 (torch 2.11.0+cu128, transformers 5.15.0, flash-linear-attention 0.5.2, tilelang 0.1.13); no flash-attn, so the fla teacher needs the registration's Llama remap or SDPA shim, neither written",
        "real_model_loop": False,
        "real_model_loop_scope": "none: harness/e4_gate.py does not exist; no fla-hub checkpoint has been loaded in any image",
        "benchmark_adapter": None,
        "benchmark_adapter_scope": "none: the family generators and manifest builder are not written",
        "manifest": None,
        "manifest_scope": "no Slurm manifest exists for any of the four registered jobs",
        "container_smoke": {"label": "container_smoke", "status": "NOT_RUN", "return_code": None, **art(not_run)},
        "slurm_test": {"label": "slurm_test", "status": "NOT_RUN", "return_code": None, **art(not_run)},
        "provenance_verification": {"label": "provenance_verification", "status": "NOT_RUN", "return_code": None, **art(not_run)},
        "registered_caps_gpu_h": {"S0_smoke": 0.17, "S1_eligibility": 0.75, "S2_oracle_main": 4.0, "S2_oracle_p_conditional": 1.5, "sum": 6.42},
        "supplementary_cpu_evidence": [
            {"label": "S1 oracle-class semantics and KILL A replication (linear surrogate, seeds 42/43/44)",
             "script": art("compute/oracle-class-semantics.py"), "output": art("compute/oracle-class-semantics.json")},
            {"label": "S2 decision-rule operating characteristics (assumed noise; 4,000 replicates per scenario, design seed 42)",
             "script": art("compute/decision-sim.py"), "output": art("compute/decision-sim.json")},
            {"label": "S3 GPU-hour estimate and caps (FLOP model; no measured throughput)",
             "script": art("compute/cost-model.py"), "output": art("compute/cost-model.json")},
            {"label": "snapshot script for source_snapshots", "script": art("compute/snapshot-sources.py")},
        ],
        "legacy_reference_not_counted": {
            "what": "D19 phase-0 CPU doctor as an orx node (synthetic regime; tests none of the gate's quantities)",
            "orx_run_id": "e20eeccb-8c51-42de-891b-007e52282bf4", "node_commit": "bc05cc496bcf98445b61db12a35f3a2b8de20f55",
            "receipt_sha256": "d05f0cc93e70915e4135b6850a3eaa9b9139af3a31d6ce7fc896106bebe1babd",
            "source": "legacy/research/evidence/infrastructure/orx-phase0-doctor-runs-2026-09-14.json"},
    }
    doctors = [{"name": name.capitalize(), "status": json.loads((BUNDLE / f"doctors/{name}.json").read_text())["status"],
                **art(f"doctors/{name}.json")}
               for name in ("source", "citation", "novelty", "design", "compute", "safety")]
    bundle = {
        "schema_version": 1,
        "proposal": str(PROPOSAL.relative_to(ROOT)),
        "proposal_sha256": sha(PROPOSAL),
        "draft_registration": {"path": str(REGISTRATION.relative_to(ROOT)), "sha256": sha(REGISTRATION),
                               "status": "DRAFT, not frozen, no ledger row"},
        "source_snapshots": snapshots,
        "query_log": {**art("query-log.json"), "queries_against_budget": qlog["queries_against_budget"],
                      "note": "150 counted discover queries against the declared 150 (cells 144, synthesis 6); 73 paper reads, not counted."},
        "reviews": [],
        "reviews_status": "NOT_RUN: the blind critic, the refute-first triad and both reviewers run after synthesis. No trusted Ed25519 store exists (D24), so no review can be signed.",
        "compute": compute,
        "doctors": doctors,
        "audit_log": None,
        "audit_log_status": "This gauntlet's first wave row is appended to program/gauntlet/ with scripts/research_gauntlet_record.py after its reviewers score.",
    }
    payload = {key: bundle.get(key) for key in ("source_snapshots", "query_log", "compute", "doctors", "audit_log")}
    bundle["evidence_root_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    blind = {}
    for path in sorted((BUNDLE / "blind").glob("paragraph-*.txt")):
        blind[path.name] = art(f"blind/{path.name}", text_sha256=hashlib.sha256(
            path.read_text(encoding="utf-8").rstrip("\n").encode()).hexdigest())
    roles = json.loads((BUNDLE / "compute/blind-roles.json").read_text(encoding="utf-8"))
    bundle["blind_discrimination_packet"] = {
        "proposal": blind[roles["proposal"]],
        "closest_prior": blind[roles["closest_prior"]],
        "closest_prior_id": roles["closest_prior_id"],
        "note": "File names carry no role and each file holds only its paragraph. The critic receives the two texts in randomized order, read by path, without this mapping or any other text.",
    }
    bundle["budget_ledger"] = {
        "declared": {"queries": 150, "wall_minutes": 600, "tokens": 8000000, "dollars": 150, "waves": 3, "gpu_hours": 0.3},
        "used_by_discovery_cells": {"queries": 144, "paper_reads": 63, "gpu_hours": 0.0,
                                    "wall_minutes_reported": "frontier about 10, cross-domain about 45; kill-shot and asset not reported",
                                    "host": "read-only ssh by the asset cell before 11:30 UTC; no host job"},
        "used_by_synthesis": {"queries": 6, "paper_reads": 10, "gpu_hours": 0.0,
                              "wall_minutes_estimate": "about 120 for this owner (2026-10-10T05:37Z onward), plus an earlier owner's stalled run",
                              "tokens_and_dollars": "not metered by the synthesis agent; the recorder meters from transcripts"},
        "remaining_queries": 0,
    }
    out = BUNDLE / "doctors/research-direction-doctor-output.json"
    if out.is_file():
        bundle["direction_doctor_run"] = {
            **art("doctors/research-direction-doctor-output.json"),
            "command": "uv run python scripts/research_direction_doctor.py program/proposals/2026-10-10-e4-icl-write-rule-gate.md",
            "note": "Outside evidence_root by design: the doctor output depends on this bundle."}
    (BUNDLE / "bundle.json").write_text(json.dumps(bundle, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(bundle["proposal_sha256"], bundle["evidence_root_sha256"], len(snapshots))


if __name__ == "__main__":
    main()
