#!/usr/bin/env python3
"""Assemble bundle.json for the S2 gauntlet (wave 1) from the files in this bundle.

Hashes every artifact, computes evidence_root_sha256 exactly as
scripts/research_direction_doctor.py does (over source_snapshots, query_log,
compute, doctors, audit_log), and records the proposal and draft-registration
hashes. Run from the worktree root after any change to the proposal or an
artifact:

    python3 program/proposals/evidence/2026-10-10-s2-arabic-cua-locale/compute/build-bundle.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
BUNDLE = ROOT / "program/proposals/evidence/2026-10-10-s2-arabic-cua-locale"
PROPOSAL = ROOT / "program/proposals/2026-10-10-s2-arabic-cua-locale.md"
REGISTRATION = ROOT / "program/preregistrations/s2-arabic-cua-locale-v1.md"


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
            entry["content_note"] = ("HTTP 200 browser-challenge page ('Verifying your browser | OpenReview'); verifies "
                                     "nothing about content; abstract from the OpenReview search API (query-log.json)")
        snapshots.append(entry)
    qlog = json.loads((BUNDLE / "query-log.json").read_text(encoding="utf-8"))
    qb = qlog["queries_against_budget"]
    not_run = "compute/attestations-not-run.md"
    cells = sorted(p.name for p in (BUNDLE / "compute/cells").glob("*") if p.name != "ORIGINAL_SHA256.txt")
    compute = {
        "scope": ("s2-arabic-cua-locale-v1 is a DRAFT; no compute attestation of its own exists "
                  "(compute/attestations-not-run.md). Supplementary CPU evidence: power-gate.py (analytic MDE grid, "
                  "cost model, gate on transported S1a inputs, Monte Carlo of the staged design) with its output, "
                  "and the discovery cells' scripts and outputs (compute/cells/, local test tokens redacted)."),
        "image_digest": "docker.io/vllm/vllm-openai@sha256:b18abb2df97b8f798e81862bd93f872ea18613372e2c3adc0cc2ac21e66ac12f",
        "image_scope": ("engine base image (vLLM v0.31.0, commit db9527a4); the cu129 overlay is rebuilt per source commit by "
                        "scripts/build_vllm_overlay_on_h100.sh, as S1a did; the Relay environment image is not built (E3)"),
        "environment_base_digest": "node:24.13.0-bookworm-slim@sha256:4660b1ca8b28d6d1906fd644abe34b2ed81d15434d26d845ef0aced307cf4b6f",
        "real_model_loop": False,
        "real_model_loop_scope": "none for Relay: no local-engine transport (E1) and no qwen35vl adapter for Relay's action set (E2)",
        "benchmark_adapter": None,
        "benchmark_adapter_scope": "none: Relay has no locale parameter, catalogs, test ids or gate doctor (Phase 0 creates them)",
        "manifest": None,
        "manifest_scope": "no Slurm manifest exists for Stage 1a or Stage 1b (E5)",
        "container_smoke": {"label": "container_smoke", "status": "NOT_RUN", "return_code": None, **art(not_run)},
        "slurm_test": {"label": "slurm_test", "status": "NOT_RUN", "return_code": None, **art(not_run)},
        "provenance_verification": {"label": "provenance_verification", "status": "NOT_RUN", "return_code": None, **art(not_run)},
        "registered_caps_gpu_h": {"phase0": 0.0, "stage1a": 2.0,
                                  "stage1b": "4 x K_inf x n x 1.5 x pilot-measured English GPU-h per episode + 0.10, at most 15.0",
                                  "total": 17.0, "d22_line": 8.0, "admission": "D24 ruling (design decision 1 offers a 2.0 GPU-h split for the pilot)"},
        "supplementary_cpu_evidence": [
            {"label": "power gate: analytic MDE grid (exact noncentral t), TOST power, cost model, gate on transported S1a inputs, pass region, Monte Carlo of pilot + gate + main study (4 assumed base-rate scenarios x 3 heterogeneity patterns x 4 true effects; 1,500 replicates per cell over seeds 42/43/44)",
             "script": art("compute/power-gate.py"), "output": art("compute/power-gate.json")},
            {"label": "query-log builder (parses the cells' raw orx outputs from the session scratchpad)", "script": art("compute/build-query-log.py")},
            {"label": "snapshot script for source_snapshots", "script": art("compute/snapshot-sources.py")},
            {"label": "discovery-cell scripts and outputs (kill-shot power simulation and Relay probes; cross-domain MDE grid; asset power and chrome-share measurement); tokens redacted, originals' SHA-256 in ORIGINAL_SHA256.txt",
             "files": [art(f"compute/cells/{n}") for n in cells] + [art("compute/cells/ORIGINAL_SHA256.txt")]},
        ],
        "repository_evidence_used": {
            "s1a_records": "program/evidence/2026-10-10/q2-stage1-analysis/a1.jsonl (SHA-256 in power-gate.json inputs)",
            "s1a_results": "program/evidence/2026-10-10/q2-stage1-a1/RESULTS.md",
            "s1a_costs": "program/evidence/2026-10-10/q2-stage1-analysis/costs.json",
            "serving_probe_v2": "program/evidence/2026-10-07/serving-throughput-probe-v2/README.md",
            "relay": "~/repos/Relay at e6c815e634f6 (read-only; public as github.com/Kevin-Liu-01/Relay)",
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
                               "experiment_id": "s2-arabic-cua-locale-v1", "status": "DRAFT, not frozen, no ledger row"},
        "source_snapshots": snapshots,
        "query_log": {**art("query-log.json"), "queries_against_budget": qb,
                      "note": (f"{qb['counted_total']} counted orx discover queries against the declared 150 "
                               f"(remaining {qb['remaining_under_declared']}, reserve of 30 intact); "
                               f"{sum(qb['orx_calls_failed_429_by_stage'].values())} orx calls failed with HTTP 429 (not counted); "
                               f"{sum(qb['uncounted_other_searches_and_fetches_by_stage'].values())} uncounted searches and fetches "
                               f"({qb['total_if_other_searches_counted']} if counted)")},
        "reviews": [],
        "reviews_status": "NOT_RUN: the blind critic, the refute-first triad and both reviewers run after synthesis. No trusted Ed25519 store exists (D24), so no review can be signed.",
        "compute": compute,
        "doctors": doctors,
        "audit_log": None,
        "audit_log_status": "This gauntlet's wave-1 row is appended to program/gauntlet/2026-10-10-s2-arabic-cua-locale.jsonl with scripts/research_gauntlet_record.py after its reviewers score.",
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
        "used_by_discovery_cells": {"queries": qb["counted_total"] - qb["counted_by_stage"].get("synthesis", 0),
                                    "failed_orx_calls": sum(qb["orx_calls_failed_429_by_stage"].values()),
                                    "uncounted_searches_and_fetches": sum(qb["uncounted_other_searches_and_fetches_by_stage"].values()),
                                    "gpu_hours": 0.0,
                                    "wall_minutes_reported": "frontier about 60; others not reported",
                                    "host": "read-only ssh by the frontier cell for the Semantic Scholar relay; no host job"},
        "used_by_synthesis": {"queries": qb["counted_by_stage"].get("synthesis", 0),
                              "paper_reads": "1 re-read of the closest prior's orx full text (cell file); spot checks of 6 cell-fetched texts; LibreOffice source re-fetched",
                              "gpu_hours": 0.0, "host": "one read-only squeue at 2026-10-10T21:42:52Z (empty); no host job",
                              "cpu": "power-gate.py (about 25 minutes on the development Mac at nrep 500 x 3 seeds), snapshot fetches",
                              "tokens_and_dollars": "not metered by the synthesis agent; the recorder meters from transcripts"},
        "remaining_queries": qb["remaining_under_declared"],
        "refuter_reserve_intact": qb["reserve_intact"],
    }
    out = BUNDLE / "doctors/research-direction-doctor-output.json"
    if out.is_file():
        bundle["direction_doctor_run"] = {
            **art("doctors/research-direction-doctor-output.json"),
            "command": "uv run python scripts/research_direction_doctor.py program/proposals/2026-10-10-s2-arabic-cua-locale.md",
            "note": "Outside evidence_root by design: the doctor output depends on this bundle."}
    (BUNDLE / "bundle.json").write_text(json.dumps(bundle, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(bundle["proposal_sha256"], bundle["evidence_root_sha256"], len(snapshots))


if __name__ == "__main__":
    main()
