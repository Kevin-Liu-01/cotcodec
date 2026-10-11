#!/usr/bin/env python3
"""Assemble bundle.json for the R01 gauntlet (wave 1) from the files in this bundle.

Hashes every artifact, computes evidence_root_sha256 exactly as
scripts/research_direction_doctor.py does (over source_snapshots, query_log, compute, doctors,
audit_log), and records the proposal and draft-registration hashes. Run from the worktree root
after any change to the proposal or an artifact:

    python3 program/proposals/evidence/2026-10-11-r01-rerun-noise-sources/compute/build_bundle.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
BUNDLE = ROOT / "program/proposals/evidence/2026-10-11-r01-rerun-noise-sources"
PROPOSAL = ROOT / "program/proposals/2026-10-11-r01-rerun-noise-sources.md"
REGISTRATION = ROOT / "program/preregistrations/r01-rerun-noise-sources-v1.md"
A0 = ROOT / "program/evidence/2026-10-11/r01-stage-a0"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def art(rel: str, **extra) -> dict:
    return {"artifact": rel, "sha256": sha(BUNDLE / rel), **extra}


def repo(rel: str) -> dict:
    return {"path": rel, "sha256": sha(ROOT / rel)}


def main() -> None:
    snapshots = []
    for path in sorted((BUNDLE / "snapshots").glob("*.json")):
        rec = json.loads(path.read_text(encoding="utf-8"))
        entry = {"url": rec["url"], "http_status": rec["http_status"], "fetched_at": rec["fetched_at"],
                 "raw_sha256": rec["raw_sha256"], "raw_bytes": rec["raw_bytes"], **art(f"snapshots/{path.name}")}
        if "openreview.net" in rec["url"]:
            entry["content_note"] = ("HTTP 200 browser-challenge page ('Verifying your browser | OpenReview'); verifies "
                                     "nothing about content; abstract from the OpenReview api2 search (query-log.json)")
        snapshots.append(entry)
    qlog = json.loads((BUNDLE / "query-log.json").read_text(encoding="utf-8"))
    qb = qlog["queries_against_budget"]
    not_run = "compute/attestations-not-run.md"
    caps = json.loads((BUNDLE / "compute/caps-r01.json").read_text())
    compute = {
        "scope": ("r01-rerun-noise-sources-v1 is a DRAFT. Stage A0 (records-only census) ran as an orx cpu-doctor node; "
                  "no Stage A1, B or C code, manifest or attestation exists (compute/attestations-not-run.md)."),
        "image_digest": "docker.io/vllm/vllm-openai@sha256:b18abb2df97b8f798e81862bd93f872ea18613372e2c3adc0cc2ac21e66ac12f",
        "image_scope": ("engine base image (vLLM v0.31.0, commit db9527a4); S1a's cu129 overlay, local image ID "
                        "sha256:10327c706dcf2a9bd06e2449908e37d4fa4e46e7030a85e66f30626a1bafecde (source 4a59e87c), is reused"),
        "real_model_loop": False,
        "real_model_loop_scope": "S1a's agent loop exists (harness/q2_stage1); Stage B's replay client and Stage C's replay mode do not",
        "benchmark_adapter": None,
        "manifest": None,
        "manifest_scope": "no Stage B or CPU-lane manifest is rendered",
        "container_smoke": {"label": "container_smoke", "status": "NOT_RUN", "return_code": None, **art(not_run)},
        "slurm_test": {"label": "slurm_test", "status": "NOT_RUN", "return_code": None, **art(not_run)},
        "provenance_verification": {"label": "provenance_verification", "status": "NOT_RUN", "return_code": None, **art(not_run)},
        "executable_pilot": {
            "stage": "A0, records-only census of S1a (CPU, model-free)",
            "orx_node": "ff110047-8f18-4b5b-b85d-fd73fa767d35", "orx_branch": "orx/r01-stage-a0-records-census",
            "orx_commit": "ca3cdbf09db81be978145ee5d05151d9b6973fc8",
            "orx_run_id": "83ee815a-426a-4b94-a93f-cc1277972d76", "backend": "local",
            "run_command": "uv run --locked python scripts/orx_run.py",
            "orx_result": "ORX_RESULT kind=cpu-doctor direction=r01-rerun-noise-sources exit=0",
            "log": art("compute/pilot/orx-run-83ee815a-426a-4b94-a93f-cc1277972d76.log"),
            "receipt_sha256": "5568bc7f9d7c87f64a6f5a91bc845dd514e6b78f17a5d55cf231f099e269e4b7",
            "receipt_matches_committed_census": True,
            "repository_files": [repo("scripts/run_r01_stage_a0_doctor.py"), repo("tests/test_r01_stage_a0_doctor.py"),
                                 repo("program/evidence/2026-10-11/r01-stage-a0/census.json"),
                                 repo("program/evidence/2026-10-11/r01-stage-a0/s1a-step-digests.jsonl.gz"),
                                 repo("program/evidence/2026-10-11/r01-stage-a0/derive_digests.py"),
                                 repo("program/evidence/2026-10-11/r01-stage-a0/derive-report.json")],
        },
        "registered_caps_gpu_h": {"total_with_conditional": caps["total_cap_gpu_h"],
                                  "total_without_conditional": caps["total_cap_gpu_h_without_conditional"],
                                  "physical_central": caps["physical_gpu_h_central"], "physical_high": caps["physical_gpu_h_high"],
                                  "d22_line": 8.0, "admission": "Kevin's ruling (D24, D70)"},
        "supplementary_cpu_evidence": [
            {"label": "operating characteristics of every registered threshold (B_det, B_read, A1_cen, C_env, K6, CL, PRED); seeds 42, 43, 44",
             "script": art("compute/power_r01.py"), "output": art("compute/power-r01.json")},
            {"label": "caps and prices from S1a's per-step records under the design study's realized-cost rule",
             "script": art("compute/caps_r01.py"), "output": art("compute/caps-r01.json")},
            {"label": "query-log builder (the cells' reported queries, verbatim)", "script": art("compute/build_query_log.py")},
            {"label": "snapshot script for source_snapshots", "script": art("compute/snapshot-sources.py")},
            {"label": "doctor-record writer (claim registry parsed from the proposal)", "script": art("compute/write_doctors.py")},
        ],
        "repository_evidence_used": {
            "s1a_records": repo("program/evidence/2026-10-10/q2-stage1-analysis/a1.jsonl"),
            "s1a_results": "program/evidence/2026-10-10/q2-stage1-a1/RESULTS.md",
            "s1a_plan": repo("program/evidence/2026-10-09/q2-stage1-prefreeze/plan/plan-a0a.json"),
            "design_study": "program/evidence/2026-10-10/q2-next-step-design-study/README.md (with D72 (ii))",
            "renewal_dossier": "program/evidence/2026-10-11/question-renewal/dossier.md (R01) and slate.md section 3",
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
                               "experiment_id": "r01-rerun-noise-sources-v1", "status": "DRAFT, not frozen, no ledger row"},
        "source_snapshots": snapshots,
        "query_log": {**art("query-log.json"), "queries_against_budget": qb},
        "reviews": [],
        "reviews_status": ("NOT_RUN: the blind critic, the refute-first triad and both reviewers run after synthesis. "
                           "No trusted Ed25519 store exists (D24), so no review can be signed."),
        "compute": compute,
        "doctors": doctors,
        "audit_log": None,
        "audit_log_status": ("This gauntlet's wave-1 row is appended to program/gauntlet/2026-10-11-r01-rerun-noise-sources.jsonl "
                             "with scripts/research_gauntlet_record.py after its reviewers score."),
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
        "note": ("File names carry no role and each file holds only its paragraph. The critic receives the two texts in "
                 "randomized order, read by path, without compute/blind-roles.json or any other text."),
    }
    bundle["budget_ledger"] = {
        "declared": {"queries": 150, "wall_minutes": 600, "tokens": 8000000, "dollars": 150, "waves": 3, "gpu_hours": 0.3},
        "used_by_discovery_cells": {"orx_discover_queries": qb["orx_discover_total"], "other_searches": qb["other_searches"],
                                    "failed_calls": qb["failed_calls"], "gpu_hours": 0.0,
                                    "host": "read-only ssh by the kill-shot, cross-domain and asset cells (squeue; ls, find, head; tar of step logs); no host job"},
        "used_by_synthesis": {"searches": 0, "gpu_hours": 0.0,
                              "host": "none (worked from the asset cell's read-only copy, verified file by file against committed host listings)",
                              "cpu": "Stage A0 derivation and doctor (seconds); power_r01.py (about 4 minutes); snapshots (27 fetches)",
                              "orx": "one local cpu-doctor run (83ee815a)",
                              "tokens_and_dollars": "not metered by the synthesis agent; the recorder meters from transcripts"},
        "remaining_queries_under_counting_rule": qb["remaining_under_counting_rule"],
        "remaining_queries_if_other_searches_counted": qb["remaining_if_other_searches_counted"],
        "refuter_reserve_intact_under_counting_rule": qb["reserve_intact_under_counting_rule"],
    }
    out = BUNDLE / "doctors/research-direction-doctor-output.json"
    if out.is_file():
        bundle["direction_doctor_run"] = {
            **art("doctors/research-direction-doctor-output.json"),
            "command": "uv run python scripts/research_direction_doctor.py program/proposals/2026-10-11-r01-rerun-noise-sources.md",
            "note": "Outside evidence_root by design: the doctor output depends on this bundle."}
    (BUNDLE / "bundle.json").write_text(json.dumps(bundle, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(bundle["proposal_sha256"], bundle["evidence_root_sha256"], len(snapshots))


if __name__ == "__main__":
    main()
