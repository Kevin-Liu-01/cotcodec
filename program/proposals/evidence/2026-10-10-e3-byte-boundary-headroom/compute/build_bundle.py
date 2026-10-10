#!/usr/bin/env python3
"""Assemble bundle.json for the E3 Stage-0 gauntlet from the files in this bundle.

Hashes every artifact, computes evidence_root_sha256 exactly as
scripts/research_direction_doctor.py does (over source_snapshots, query_log,
compute, doctors, audit_log), and records the proposal and draft-registration
hashes. Run from the worktree root after any change to the proposal or an
artifact:

    python3 program/proposals/evidence/2026-10-10-e3-byte-boundary-headroom/compute/build_bundle.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
BUNDLE = ROOT / "program/proposals/evidence/2026-10-10-e3-byte-boundary-headroom"
PROPOSAL = ROOT / "program/proposals/2026-10-10-e3-byte-boundary-headroom.md"
REGISTRATION = ROOT / "program/preregistrations/e3-byte-boundary-headroom-v1.md"
BASE_IMAGE = "127.0.0.1:5000/cotcodec-research@sha256:13a9de831cff50461d8ecee3c2794f0c6d6bcffe9d602968fe2ee06e5a1096e9"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def art(rel: str, **extra) -> dict:
    return {"artifact": rel, "sha256": sha(BUNDLE / rel), **extra}


def main() -> None:
    snapshots = []
    for path in sorted((BUNDLE / "snapshots").glob("*.json")):
        rec = json.loads(path.read_text(encoding="utf-8"))
        entry = {"url": rec["url"], "http_status": rec["http_status"], "fetched_at": rec["fetched_at"],
                 "raw_sha256": rec["raw_sha256"], "raw_bytes": rec["raw_bytes"], **art(f"snapshots/{path.name}")}
        if "openreview.net" in rec["url"]:
            entry["content_note"] = "HTTP 200 browser-challenge page ('Verifying your browser | OpenReview'); verifies nothing about content; abstract from the OpenReview search API (query-log.json)"
        snapshots.append(entry)
    qlog = json.loads((BUNDLE / "query-log.json").read_text(encoding="utf-8"))
    not_run = "compute/attestations-not-run.md"
    compute = {
        "scope": "e3-byte-boundary-headroom-v1 is a DRAFT; no compute attestation of its own exists (compute/attestations-not-run.md). Supplementary CPU evidence: simulation S1 (instrument gates for the dossier's UOT cost and for projected boundary Dice, decision-rule operating characteristics, calibration decomposition) and cost model S2 (caps and arithmetic), each script with its output.",
        "image_digest": BASE_IMAGE,
        "image_scope": "pinned research architecture base image (torch 2.11.0+cu128, triton 3.6.0, transformers 5.15.0); the probe needs an overlay with hnet at 3673fe12, mamba-ssm, causal-conv1d and flash-attn, built as a host CPU job after freeze approval; no such overlay exists",
        "real_model_loop": False,
        "real_model_loop_scope": "none: the H-Net boundary-extraction driver, the aligner driver and the PBD scorer in harness/ are not written; the H-Net checkpoints are not on the host",
        "benchmark_adapter": None,
        "benchmark_adapter_scope": "none: no FLORES+ manifest builder, canonicalizer, cut builder or scorer exists in harness/ (S1 holds simulation code only)",
        "manifest": None,
        "manifest_scope": "no Slurm manifest exists for the smoke or probe job",
        "container_smoke": {"label": "container_smoke", "status": "NOT_RUN", "return_code": None, **art(not_run)},
        "slurm_test": {"label": "slurm_test", "status": "NOT_RUN", "return_code": None, **art(not_run)},
        "provenance_verification": {"label": "provenance_verification", "status": "NOT_RUN", "return_code": None, **art(not_run)},
        "registered_caps_gpu_h": {"smoke": 0.2, "probe": 0.6, "sum": 0.8, "threshold": 8.0,
                                  "estimate_central": 0.264, "estimate_high": 0.558},
        "supplementary_cpu_evidence": [
            {"label": "S1 instrument and decision-rule simulation (synthetic pairs, seeds 42/43/44; 31 process runs merged)",
             "script": art("compute/instrument_sim.py"), "merge_script": art("compute/merge_sim.py"),
             "output": art("compute/instrument-sim.json")},
            {"label": "S2 GPU-hour estimate and caps (arithmetic; no host throughput measured)",
             "script": art("compute/cost_model.py"), "output": art("compute/cost-model.json")},
            {"label": "query-log builder (parses the cells' raw orx outputs from the session scratchpad)", "script": art("compute/build_query_log.py")},
            {"label": "snapshot script for source_snapshots", "script": art("compute/snapshot_sources.py")},
        ],
        "repository_evidence_used": {
            "legacy_evaluator": "legacy/harness/translation_boundaries.py (imported by S1's UOT part)",
            "legacy_doctor_rerun": "legacy/scripts/run_boundary_transport_doctor.py re-run 2026-10-10: REFERENCE_OBJECTIVE_DOCTOR_PASS, payload_sha256 6d8c24be8e5042898ba80ebb9204c3df4645d314a3b58982edab15f17ae5b459",
        },
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
                      "note": "118 counted orx discover calls (frontier 62, kill-shot 24, cross-domain 27, asset 5; synthesis 0; 2 failed with OpenAlex 429) against the declared 150, leaving 32 for the triad's reserve of 30; 19 uncounted OpenReview, web and metadata calls; cell paper reads and synthesis re-reads not counted."},
        "reviews": [],
        "reviews_status": "NOT_RUN: the blind critic, the refute-first triad and both reviewers run after synthesis. No trusted Ed25519 store exists (D24), so no review can be signed.",
        "compute": compute,
        "doctors": doctors,
        "audit_log": None,
        "audit_log_status": "This gauntlet's wave-1 row is appended to program/gauntlet/2026-10-10-e3-byte-boundary-headroom.jsonl with scripts/research_gauntlet_record.py after its reviewers score.",
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
        "used_by_discovery_cells": {"queries": 118, "uncounted_calls": 19, "gpu_hours": 0.0,
                                    "host": "read-only metadata access by the asset cell; no host job"},
        "used_by_synthesis": {"queries": 0,
                              "paper_reads": "5 re-reads of cell-fetched texts; Hugging Face, GitHub and raw-file metadata reads (auxiliary)",
                              "gpu_hours": 0.0, "host": "one read-only squeue at 21:22 UTC (empty queue); no host job",
                              "cpu": "S1 (31 process runs, about 89 CPU-minutes) and S2 on the development Mac; one legacy doctor re-run",
                              "tokens_and_dollars": "not metered by the synthesis agent; the recorder meters from transcripts"},
        "remaining_queries": 32,
        "refuter_reserve_shortfall": 0,
    }
    out = BUNDLE / "doctors/research-direction-doctor-output.json"
    if out.is_file():
        bundle["direction_doctor_run"] = {
            **art("doctors/research-direction-doctor-output.json"),
            "command": "uv run python scripts/research_direction_doctor.py program/proposals/2026-10-10-e3-byte-boundary-headroom.md",
            "note": "Outside evidence_root by design: the doctor output depends on this bundle."}
    (BUNDLE / "bundle.json").write_text(json.dumps(bundle, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(bundle["proposal_sha256"], bundle["evidence_root_sha256"], len(snapshots))


if __name__ == "__main__":
    main()
