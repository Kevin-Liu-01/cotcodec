#!/usr/bin/env python3
"""Assemble bundle.json for the E7 G1 gauntlet from the files in this bundle.

Hashes every artifact, computes evidence_root_sha256 exactly as
scripts/research_direction_doctor.py does (over source_snapshots, query_log,
compute, doctors, audit_log), and records the proposal and draft-registration
hashes. Run from the worktree root after any change to the proposal or an
artifact:

    python3 program/proposals/evidence/2026-10-10-e7-equivariant-writes-g1/compute/build-bundle.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
BUNDLE = ROOT / "program/proposals/evidence/2026-10-10-e7-equivariant-writes-g1"
PROPOSAL = ROOT / "program/proposals/2026-10-10-e7-equivariant-writes-g1.md"
REGISTRATION = ROOT / "program/preregistrations/e7-equivariant-writes-g1-v1.md"


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
            entry["content_note"] = ("HTTP 200 page may be a browser challenge; it verifies nothing about content; "
                                     "the abstract comes from the OpenReview search API (cells' query logs)")
        snapshots.append(entry)
    qlog = json.loads((BUNDLE / "query-log.json").read_text(encoding="utf-8"))
    cost = json.loads((BUNDLE / "compute/cost-model.json").read_text(encoding="utf-8"))
    reach = json.loads((BUNDLE / "compute/reach-doctor.json").read_text(encoding="utf-8"))
    not_run = "compute/attestations-not-run.md"
    compute = {
        "scope": ("e7-equivariant-writes-g1-v1 is a DRAFT; no compute attestation of its own exists "
                  "(compute/attestations-not-run.md). Supplementary CPU evidence: S1 (decision-rule operating "
                  "characteristics), S2 (cost model and caps), S3 (state-free reach of the A0 layer graph on a NumPy "
                  "stand-in), each script with its output, and the asset cell's rerun of the legacy phase-0 object doctor."),
        "image_digest": "127.0.0.1:5000/cotcodec-research@sha256:02965f3d696d4e516a7cd6d5c03434e9098139738748ae778ed967215db7be6d",
        "image_scope": ("the image behind the measured 134M throughput (cotcodec-research:0b3ecef0-architecture, Slurm 359; "
                        "torch 2.11.0+cu128, fla 0.5.2, triton 3.6.0, tilelang 0.1.13); the G1 image is built from the "
                        "harness commit and pinned before J1"),
        "real_model_loop": False,
        "real_model_loop_scope": "none: the A0 model, the training loop and the data builders are not written",
        "benchmark_adapter": None,
        "benchmark_adapter_scope": "none: the TP-MQAR-v2-G1 builder, the evaluator and the analysis are not written",
        "manifest": None,
        "manifest_scope": "no Slurm manifest exists for J1, J2, J3, T42, T43 or T44",
        "container_smoke": {"label": "container_smoke", "status": "NOT_RUN", "return_code": None, **art(not_run)},
        "slurm_test": {"label": "slurm_test", "status": "NOT_RUN", "return_code": None, **art(not_run)},
        "provenance_verification": {"label": "provenance_verification", "status": "NOT_RUN", "return_code": None, **art(not_run)},
        "registered_caps_gpu_h": {j["job"].split(" ")[0]: j["cap_gpu_h"] for j in cost["jobs"]},
        "cap_sum_gpu_h_D22": cost["cap_sum_gpu_h_D22"],
        "central_gpu_h": cost["central_gpu_h_all_seeds_no_extension"],
        "central_gpu_h_futility_path": cost["central_gpu_h_if_futility_stop_after_seed_42"],
        "throughput_gate_tokens_per_s": cost["throughput_gate_min_training_tokens_per_s"],
        "supplementary_cpu_evidence": [
            {"label": "S1 decision-rule operating characteristics (assumed distributions; 1,000 replicates per scenario over seeds 42/43/44)",
             "script": art("compute/gate-sim.py"), "output": art("compute/gate-sim.json")},
            {"label": "S2 GPU-hour estimate and registered caps (base: measured 282,501.4 tokens/s, Slurm 359; everything else assumed)",
             "script": art("compute/cost-model.py"), "output": art("compute/cost-model.json")},
            {"label": f"S3 state-free reach of the A0 layer graph by complex-step derivative (NumPy stand-in, seeds 42/43/44): all_checks_ok={reach['all_checks_ok']}, bound {reach['claimed_state_free_bound']}",
             "script": art("compute/reach-doctor.py"), "output": art("compute/reach-doctor.json")},
            {"label": "legacy phase-0 object doctor rerun on main by the asset cell (PHASE0_OBJECT_DOCTOR_PASS, 11/11; synthetic objects only)",
             "output": art("compute/legacy-phase0-doctor-main.json")},
            {"label": "query-log builder (parses the cells' raw orx outputs from the session scratchpad)", "script": art("compute/build-query-log.py")},
            {"label": "snapshot script for source_snapshots", "script": art("compute/snapshot-sources.py")},
        ],
        "repository_evidence_used": {
            "throughput_receipt": "legacy/research/evidence/infrastructure/fla-throughput-h100-2026-09-01.json (runs[1], Slurm 359)",
            "throughput_doctor": "scripts/fla_throughput_doctor.py (layout i % 4 == 3, MLP 768-4096-768)",
            "legacy_contract": "legacy/experiments/architectures/translation-equivariant-state-writes.yaml (v5)",
            "k1_source_receipts": "program/evidence/2026-10-07/q3-k1-bundle-sources.json",
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
                               "experiment_id": "e7-equivariant-writes-g1-v1",
                               "status": "DRAFT, not frozen, no ledger row"},
        "source_snapshots": snapshots,
        "query_log": {**art("query-log.json"), "queries_against_budget": qlog["queries_against_budget"],
                      "note": (f"{qlog['queries_against_budget']} counted orx discover queries ({qlog['queries_by_cell']}) against the declared 150; "
                               f"{qlog['remaining_queries']} remain, the refuters' reserve of 30 is intact; "
                               f"{qlog['uncounted_calls']} uncounted calls (OpenReview, web, GitHub, Hugging Face, curl, paper reads)")},
        "reviews": [],
        "reviews_status": "NOT_RUN: the blind critic, the refute-first triad and both reviewers run after synthesis. No trusted Ed25519 store exists (D24), so no review can be signed.",
        "compute": compute,
        "doctors": doctors,
        "audit_log": None,
        "audit_log_status": "This gauntlet's wave-1 row is appended to program/gauntlet/2026-10-10-e7-equivariant-writes-g1.jsonl with scripts/research_gauntlet_record.py after its reviewers score.",
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
    bundle["cell_verdicts"] = art("cells/cell-verdicts.json")
    bundle["budget_ledger"] = {
        "declared": {"queries": 150, "wall_minutes": 600, "tokens": 8000000, "dollars": 150, "waves": 3, "gpu_hours": 0.3},
        "used_by_discovery_cells": {"queries": qlog["queries_against_budget"] - qlog["queries_by_cell"].get("synthesis", 0),
                                    "paper_reads": 68, "gpu_hours": 0.0,
                                    "host": "read-only ssh by the asset cell (squeue, images, data listing); no host job"},
        "used_by_synthesis": {"queries": qlog["queries_by_cell"].get("synthesis", 0), "paper_reads": "2 abstracts; full-text re-checks by grep of the cells' saved texts",
                              "gpu_hours": 0.0, "host": "one read-only squeue at 21:25 UTC (queue empty); no host job",
                              "cpu": "S1 (about 305 s, 6 workers), S2, S3 (about 120 s) on the development Mac",
                              "tokens_and_dollars": "not metered by the synthesis agent; the recorder meters from transcripts"},
        "remaining_queries": qlog["remaining_queries"],
        "refuter_reserve_shortfall": max(0, 30 - qlog["remaining_queries"]),
    }
    out = BUNDLE / "doctors/research-direction-doctor-output.json"
    if out.is_file():
        bundle["direction_doctor_run"] = {
            **art("doctors/research-direction-doctor-output.json"),
            "command": "uv run python scripts/research_direction_doctor.py program/proposals/2026-10-10-e7-equivariant-writes-g1.md",
            "note": "Outside evidence_root by design: the doctor output depends on this bundle."}
    (BUNDLE / "bundle.json").write_text(json.dumps(bundle, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(bundle["proposal_sha256"], bundle["evidence_root_sha256"], len(snapshots))


if __name__ == "__main__":
    main()
