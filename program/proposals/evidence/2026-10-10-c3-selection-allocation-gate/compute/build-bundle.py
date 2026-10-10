#!/usr/bin/env python3
"""Assemble bundle.json for the C3 Stage-0 gate gauntlet from the files in this bundle.

Hashes every artifact, computes evidence_root_sha256 exactly as
scripts/research_direction_doctor.py does (over source_snapshots, query_log,
compute, doctors, audit_log), and records the proposal and draft-registration
hashes. Run from the worktree root after any change to the proposal or an
artifact:

    python3 program/proposals/evidence/2026-10-10-c3-selection-allocation-gate/compute/build-bundle.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
BUNDLE = ROOT / "program/proposals/evidence/2026-10-10-c3-selection-allocation-gate"
PROPOSAL = ROOT / "program/proposals/2026-10-10-c3-selection-allocation-gate.md"
REGISTRATION = ROOT / "program/preregistrations/c3-selection-allocation-gate-v1.md"


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
        "scope": "c3-selection-allocation-gate-v1 is a DRAFT; no compute attestation of its own exists (compute/attestations-not-run.md). Supplementary CPU evidence: simulation S1 (decision-rule operating characteristics and the identification of the spread target) and S2 (cost model, cap formula and N rule), each script with its output.",
        "image_digest": "docker.io/vllm/vllm-openai@sha256:b18abb2df97b8f798e81862bd93f872ea18613372e2c3adc0cc2ac21e66ac12f",
        "image_scope": "generation base image; the cu129 overlay is built per source commit by scripts/build_vllm_overlay_on_h100.sh (probe v2 overlay image ID sha256:a59d7782755ac7db3e5ffdeaa1dd023af169b0ed6a5e04213ebbecbc7d5c30fc); it served the Qwen3-8B architecture with dummy weights in serving-throughput-probe-v1 job B (Slurm 446)",
        "extraction_image_digest": "127.0.0.1:5000/cotcodec-research@sha256:13a9de831cff50461d8ecee3c2794f0c6d6bcffe9d602968fe2ee06e5a1096e9",
        "real_model_loop": False,
        "real_model_loop_scope": "none: the generation driver, answer-position extractor and HF extraction job are not written; Qwen3-8B real weights are not on the host",
        "benchmark_adapter": None,
        "benchmark_adapter_scope": "none: data manifest builder, graders and family builder are not written",
        "manifest": None,
        "manifest_scope": "no Slurm manifest exists for the smoke, P0, G-decode or G-extraction jobs",
        "container_smoke": {"label": "container_smoke", "status": "NOT_RUN", "return_code": None, **art(not_run)},
        "slurm_test": {"label": "slurm_test", "status": "NOT_RUN", "return_code": None, **art(not_run)},
        "provenance_verification": {"label": "provenance_verification", "status": "NOT_RUN", "return_code": None, **art(not_run)},
        "registered_caps_gpu_h": {"smoke": 0.25, "P0": 1.0,
                                  "G_decode": "1.2 x high projection after P0 (formula fixed before P0)",
                                  "G_extraction": "1.2 x projected time at 0.8 x P0-measured MFU + 0.05",
                                  "sum_limit": 8.0,
                                  "example_N800_meanL6000_cv075": {"G_decode": 5.33, "G_extraction": 0.74, "sum": 7.32}},
        "supplementary_cpu_evidence": [
            {"label": "S1 decision-rule operating characteristics and identification of the spread target (assumed distributions; 600 replicates per cell over seeds 42/43/44; B = 1,000)",
             "script": art("compute/gate-sim.py"), "output": art("compute/gate-sim.json")},
            {"label": "S2 GPU-hour estimate, cap formula and N rule (calibrated on probe v1 job B dummy-weight points; real-weight throughput unmeasured)",
             "script": art("compute/cost-model.py"), "output": art("compute/cost-model.json")},
            {"label": "query-log builder (parses the cells' raw orx outputs from the session scratchpad)", "script": art("compute/build-query-log.py")},
            {"label": "snapshot script for source_snapshots", "script": art("compute/snapshot-sources.py")},
        ],
        "repository_evidence_used": {
            "serving_probe_v1_job_B_points": "program/evidence/2026-10-07/serving-throughput-probe-v1/jobs/b-446/probe/points/{b1a,b1b,b1c,b2,b3,b6}.json",
            "serving_probe_v2": "program/evidence/2026-10-07/serving-throughput-probe-v2/README.md",
            "qwen3_8b_metadata_receipt": "program/evidence/2026-10-07/serving-throughput-probe-v1/metadata/qwen3-8b.receipt.json",
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
                      "note": "127 counted orx discover queries (cells 127, synthesis 0) against the declared 150; the triad's reserve of 30 was breached by 7 before synthesis; 24 uncounted OpenReview, web and OpenAlex API searches (151 if counted); 94 cell paper reads and 7 synthesis re-reads, not counted."},
        "reviews": [],
        "reviews_status": "NOT_RUN: the blind critic, the refute-first triad and both reviewers run after synthesis. No trusted Ed25519 store exists (D24), so no review can be signed.",
        "compute": compute,
        "doctors": doctors,
        "audit_log": None,
        "audit_log_status": "This gauntlet's wave-1 row is appended to program/gauntlet/2026-10-10-c3-selection-allocation-gate.jsonl with scripts/research_gauntlet_record.py after its reviewers score.",
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
        "used_by_discovery_cells": {"queries": 127, "uncounted_searches": 24, "paper_reads": 94, "gpu_hours": 0.0,
                                    "wall_minutes_reported": "kill-shot about 45; others not reported (cells finished by about 14:37 UTC)",
                                    "host": "read-only ssh by the asset and cross-domain cells (squeue, point files, receipts); no host job"},
        "used_by_synthesis": {"queries": 0, "paper_reads": "7 re-reads of cell-fetched texts; Hugging Face API reads for the model and datasets (auxiliary)",
                              "gpu_hours": 0.0, "host": "one read-only squeue at 14:50 UTC (S1a jobs 1062 and 1064 RUNNING); no host job",
                              "cpu": "S1 (about 160 s) and S2 on the development Mac",
                              "tokens_and_dollars": "not metered by the synthesis agent; the recorder meters from transcripts"},
        "remaining_queries": 23,
        "refuter_reserve_shortfall": 7,
    }
    out = BUNDLE / "doctors/research-direction-doctor-output.json"
    if out.is_file():
        bundle["direction_doctor_run"] = {
            **art("doctors/research-direction-doctor-output.json"),
            "command": "uv run python scripts/research_direction_doctor.py program/proposals/2026-10-10-c3-selection-allocation-gate.md",
            "note": "Outside evidence_root by design: the doctor output depends on this bundle."}
    (BUNDLE / "bundle.json").write_text(json.dumps(bundle, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(bundle["proposal_sha256"], bundle["evidence_root_sha256"], len(snapshots))


if __name__ == "__main__":
    main()
