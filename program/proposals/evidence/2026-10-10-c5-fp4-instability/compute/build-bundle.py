#!/usr/bin/env python3
"""Assemble bundle.json for the C5 FP4 instability gauntlet from the files in this bundle.

Hashes every artifact, computes evidence_root_sha256 exactly as
scripts/research_direction_doctor.py does (over source_snapshots, query_log,
compute, doctors, audit_log), and records the proposal and draft-registration
hashes. Run from the worktree root after any change to the proposal or an
artifact:

    python3 program/proposals/evidence/2026-10-10-c5-fp4-instability/compute/build-bundle.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
BUNDLE = ROOT / "program/proposals/evidence/2026-10-10-c5-fp4-instability"
PROPOSAL = ROOT / "program/proposals/2026-10-10-c5-fp4-instability.md"
REGISTRATION = ROOT / "program/preregistrations/c5-fp4-instability-v1.md"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def art(rel: str, **extra) -> dict:
    return {"artifact": rel, "sha256": sha(BUNDLE / rel), **extra}


def main() -> None:
    snapshots = []
    for path in sorted((BUNDLE / "snapshots").glob("*.json")):
        rec = json.loads(path.read_text(encoding="utf-8"))
        entry = {
            "url": rec["url"],
            "http_status": rec["http_status"],
            "fetched_at": rec["fetched_at"],
            "raw_sha256": rec["raw_sha256"],
            "raw_bytes": rec["raw_bytes"],
            **art(f"snapshots/{path.name}"),
        }
        if "openreview.net" in rec["url"]:
            entry["content_note"] = (
                "HTTP 200 browser-challenge page; verifies nothing about content; the abstract "
                "comes from the OpenReview search API (query-log.json, frontier cell)"
            )
        snapshots.append(entry)
    qlog = json.loads((BUNDLE / "query-log.json").read_text(encoding="utf-8"))
    not_run = "compute/attestations-not-run.md"
    compute = {
        "scope": (
            "c5-fp4-instability-v1 is a DRAFT; no compute attestation of its own exists "
            "(compute/attestations-not-run.md). Supplementary CPU evidence: N1 exact numerics, N2 tensor-level "
            "prediction, D1 design estimability, S1 decision-rule simulation, S2 cost model, each script with its output."
        ),
        "image_digest": "127.0.0.1:5000/cotcodec-research@sha256:13a9de831cff50461d8ecee3c2794f0c6d6bcffe9d602968fe2ee06e5a1096e9",
        "image_scope": "architecture image (build 855; torch 2.11.0+cu128, Triton 3.6.0, ml_dtypes present); holds no C5 code; a rebuild at the freeze commit is required",
        "real_model_loop": False,
        "real_model_loop_scope": "none: no LM pretraining loop, model, loader, checkpointing or evaluation exists for this study",
        "benchmark_adapter": None,
        "benchmark_adapter_scope": "none: FineWeb-Edu files and the tokenizer are not on the host; no tokenized shards",
        "manifest": None,
        "manifest_scope": "no Slurm manifest exists for J0 to J3 or for any Phase 1 job",
        "container_smoke": {
            "label": "container_smoke",
            "status": "NOT_RUN",
            "return_code": None,
            **art(not_run),
        },
        "slurm_test": {
            "label": "slurm_test",
            "status": "NOT_RUN",
            "return_code": None,
            **art(not_run),
        },
        "provenance_verification": {
            "label": "provenance_verification",
            "status": "NOT_RUN",
            "return_code": None,
            **art(not_run),
        },
        "registered_caps_gpu_h": {
            "phase0": {"J0": 0.10, "J1": 2.20, "J2": 0.45, "J3": 0.30, "sum": 3.05},
            "phase1": "formula fixed in the registration; S2 cap values 29.4 (low, 2 per GPU) to 326.0 (high); admission under D24",
        },
        "supplementary_cpu_evidence": [
            {
                "label": "N1 exact numerics: grids, scale codebooks, decoded-operand representability, folded tensor scale, metamorphic identity, storage, 2505.19115 Table 4 SD, tie handling",
                "script": art("compute/numerics.py"),
                "output": art("compute/numerics.json"),
            },
            {
                "label": "N2 tensor-level prediction of the grid effect per scale configuration (numpy reference quantizer, five synthetic distributions, with and without RHT; seeds 42-44)",
                "script": art("compute/crest_prediction.py"),
                "output": art("compute/crest-prediction.json"),
            },
            {
                "label": "D1 estimability of the dossier, registered and extended cell sets; contrast SEs and MDEs in sigma units",
                "script": art("compute/doe.py"),
                "output": art("compute/doe.json"),
            },
            {
                "label": "S1 operating characteristics of G1 and the Stage 1b verdicts with LR tuning (2,000 replicates per setting; seeds 42-44); SR test power; exact Spearman critical values for n = 8",
                "script": art("compute/power_sim.py"),
                "output": art("compute/power-sim.json"),
            },
            {
                "label": "S2 Phase 0 caps and Phase 1 projections (assumed throughput; caps by the registered formula)",
                "script": art("compute/cost_model.py"),
                "output": art("compute/cost-model.json"),
            },
            {
                "label": "query-log builder (parses the cells' and synthesis's raw orx outputs from the session scratchpad)",
                "script": art("compute/build-query-log.py"),
            },
            {
                "label": "snapshot script for source_snapshots",
                "script": art("compute/snapshot-sources.py"),
            },
        ],
        "repository_evidence_used": {
            "fla_throughput_anchor": "legacy/research/evidence/infrastructure/fla-throughput-h100-2026-09-01.json",
            "fla_throughput_doctor": "scripts/fla_throughput_doctor.py (tests pass on main per the asset cell)",
        },
        "host_state": "read-only ssh at 2026-10-10T21:21:22Z: squeue empty, all eight GPUs at 0 MiB; no host job submitted by synthesis",
    }
    doctors = [
        {
            "name": name.capitalize(),
            "status": json.loads((BUNDLE / f"doctors/{name}.json").read_text())["status"],
            **art(f"doctors/{name}.json"),
        }
        for name in ("source", "citation", "novelty", "design", "compute", "safety")
    ]
    bundle = {
        "schema_version": 1,
        "proposal": str(PROPOSAL.relative_to(ROOT)),
        "proposal_sha256": sha(PROPOSAL),
        "draft_registration": {
            "path": str(REGISTRATION.relative_to(ROOT)),
            "sha256": sha(REGISTRATION),
            "status": "DRAFT, not frozen, no ledger row",
        },
        "source_snapshots": snapshots,
        "query_log": {
            **art("query-log.json"),
            "queries_against_budget": qlog["queries_against_budget"],
            "note": (
                "114 counted orx discover invocations (frontier 38, kill-shot 26, cross-domain 35, asset 8, "
                "synthesis 7), of which 11 were rejected by the backend; 36 remain of the declared 150, "
                "above the triad's reserve of 30; paper reads and non-orx searches recorded, not counted."
            ),
        },
        "reviews": [],
        "reviews_status": "NOT_RUN: the blind critic, the refute-first triad and both reviewers run after synthesis. No trusted Ed25519 store exists (D24), so no review can be signed.",
        "compute": compute,
        "doctors": doctors,
        "audit_log": None,
        "audit_log_status": "This gauntlet's wave-1 row is appended to program/gauntlet/2026-10-10-c5-fp4-instability.jsonl with scripts/research_gauntlet_record.py after its reviewers score.",
    }
    payload = {
        key: bundle.get(key)
        for key in ("source_snapshots", "query_log", "compute", "doctors", "audit_log")
    }
    bundle["evidence_root_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    blind = {}
    for path in sorted((BUNDLE / "blind").glob("paragraph-*.txt")):
        blind[path.name] = art(
            f"blind/{path.name}",
            text_sha256=hashlib.sha256(
                path.read_text(encoding="utf-8").rstrip("\n").encode()
            ).hexdigest(),
        )
    roles = json.loads((BUNDLE / "compute/blind-roles.json").read_text(encoding="utf-8"))
    bundle["blind_discrimination_packet"] = {
        "proposal": blind[roles["proposal"]],
        "closest_prior": blind[roles["closest_prior"]],
        "closest_prior_id": roles["closest_prior_id"],
        "note": "File names carry no role and each file holds only its paragraph. The critic receives the two texts in randomized order, read by path, without this mapping or any other text.",
    }
    bundle["budget_ledger"] = {
        "declared": {
            "queries": 150,
            "wall_minutes": 600,
            "tokens": 8000000,
            "dollars": 150,
            "waves": 3,
            "gpu_hours": 0.3,
        },
        "used_by_discovery_cells": {
            "queries": 107,
            "queries_rejected_by_backend": 10,
            "full_text_reads": 58,
            "gpu_hours": 0.0,
            "host": "read-only ssh by the frontier cell (arXiv API relay) and one docker import check by the asset cell (no GPU, no Slurm job)",
        },
        "used_by_synthesis": {
            "queries": 7,
            "queries_rejected_by_backend": 1,
            "full_text_rereads": 16,
            "gpu_hours": 0.0,
            "host": "read-only ssh: one squeue/nvidia-smi read and two Semantic Scholar relay calls; no host job",
            "cpu": "N1 (about 100 s), N2 (about 60 s), D1, S1 (about 5 s), S2 on the development Mac",
            "tokens_and_dollars": "not metered by the synthesis agent; the recorder meters from transcripts",
        },
        "remaining_queries": 36,
        "refuter_reserve_shortfall": 0,
    }
    out = BUNDLE / "doctors/research-direction-doctor-output.json"
    if out.is_file():
        bundle["direction_doctor_run"] = {
            **art("doctors/research-direction-doctor-output.json"),
            "command": "uv run python scripts/research_direction_doctor.py program/proposals/2026-10-10-c5-fp4-instability.md",
            "note": "Outside evidence_root by design: the doctor output depends on this bundle.",
        }
    (BUNDLE / "bundle.json").write_text(
        json.dumps(bundle, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(bundle["proposal_sha256"], bundle["evidence_root_sha256"], len(snapshots))


if __name__ == "__main__":
    main()
