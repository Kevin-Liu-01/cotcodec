#!/usr/bin/env python3
"""Assemble bundle.json for the LM1 gauntlet (wave 1 synthesis).

Hashes every artifact, computes evidence_root_sha256 exactly as scripts/research_direction_doctor.py
does (over source_snapshots, query_log, compute, doctors, audit_log), and records the proposal and
draft-registration hashes. With --doctor-output FILE it only adds the deterministic doctor's run
record (outside the evidence root, so the root and the doctor's reading stay valid).
Adapted from the G2-stream bundle's build_bundle.py.

Usage (repo root):
  python3 program/proposals/evidence/2026-10-16-lm1-matched-memory-quality/compute/build_bundle.py
  python3 .../build_bundle.py --doctor-output program/proposals/evidence/.../doctors/direction-doctor-output.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
BUNDLE = ROOT / "program/proposals/evidence/2026-10-16-lm1-matched-memory-quality"
PROPOSAL = ROOT / "program/proposals/2026-10-16-lm1-matched-memory-quality.md"
REGISTRATION = ROOT / "program/preregistrations/lm1-matched-memory-quality-v1.md"
LLAMACPP_IMAGE = "127.0.0.1:5000/cotcodec-llamacpp@sha256:d445e09f9f0167cbce65be9fecd0f38c539b243ea321ee281ebeea259e904131"
LLAMACPP_IMAGE_ID = "sha256:fb8600d96560412d65ec9c269b555c8db6ed4bcfd86a3556658b1c108073e848"
CUDA_BASE = "docker.io/nvidia/cuda@sha256:4b9ed5fa8361736996499f64ecebf25d4ec37ff56e4d11323ccde10aa36e0c43"
VLLM_BASE = "docker.io/vllm/vllm-openai@sha256:b18abb2df97b8f798e81862bd93f872ea18613372e2c3adc0cc2ac21e66ac12f"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def art(rel: str, **extra) -> dict:
    return {"artifact": rel, "sha256": sha(BUNDLE / rel), **extra}


def evidence_root(bundle: dict) -> str:
    payload = {k: bundle.get(k) for k in ("source_snapshots", "query_log", "compute", "doctors", "audit_log")}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def build() -> dict:
    snapshots = []
    for path in sorted((BUNDLE / "snapshots").glob("*.json")):
        rec = json.loads(path.read_text(encoding="utf-8"))
        snapshots.append({
            "url": rec["url"], "http_status": rec["http_status"], "fetched_at": rec["fetched_at"],
            "raw_sha256": rec["raw_sha256"], "raw_bytes": rec["raw_bytes"], "primary": rec.get("primary"),
            **art(f"snapshots/{path.name}"),
        })
    caps = json.loads((BUNDLE / "compute/caps-lm1.json").read_text(encoding="utf-8"))
    not_run = "compute/attestations-not-run.md"
    compute = {
        "scope": (
            "lm1-matched-memory-quality-v1 is a DRAFT pilot registration. The llama.cpp image, the six GGUFs and a "
            "smoke test exist from the LM1 host prep (D127); no LM1 harness, manifest or host attestation exists. "
            "Only the decision-rule simulation and cap arithmetic were run (compute/attestations-not-run.md)."
        ),
        "image_digest": LLAMACPP_IMAGE,
        "image_scope": f"stock llama.cpp b11669 (620d2225), image id {LLAMACPP_IMAGE_ID}, built on {CUDA_BASE}; the judge runs in the cotcodec-vllm overlay on {VLLM_BASE}",
        "real_model_loop": False,
        "benchmark_adapter": None,
        "manifest": None,
        "manifest_scope": "no LM1 manifest is rendered",
        "container_smoke": {"label": "container_smoke", "status": "NOT_RUN", "return_code": None,
                            "note": "the image's smoke test (job 1582, D127) loaded all six GGUFs; no LM1 request has been sent", **art(not_run)},
        "slurm_test": {"label": "slurm_test", "status": "NOT_RUN", "return_code": None, **art(not_run)},
        "provenance_verification": {"label": "provenance_verification", "status": "NOT_RUN", "return_code": None,
                                    "note": "model receipts and image provenance exist (D127); datasets not fetched", **art(not_run)},
        "executable_pilot": None,
        "executable_pilot_scope": "none run; the gauntlet's host rule allowed only the open-weight reviewer's lane job",
        "pilot_caps_gpu_h": {
            "guards_unconditional": caps["pilot"]["sum_of_guards_without_conditional_P2"],
            "line": caps["pilot"]["line_gpu_h"],
            "expected_unconditional": caps["pilot"]["expected_unconditional_gpu_h"],
            "jobs": [{"job": j["job"], "gpus": j["gpus"], "guard": j["guard_gpu_h"], "estimate": j["gpu_h"]} for j in caps["pilot"]["jobs"]],
        },
        "full_study_gpu_h_by_branch": {k: v["gpu_h"] for k, v in caps["full_study"]["branches"].items()},
        "downloads_GB": {"pilot": 0, "full_study_conditional": {"qwen3.8-27b_bf16_approx": 54, "kimi-k2.6_iq1_m": 232.43}},
        "supplementary_cpu_evidence": [
            {"label": "decision-rule operating characteristics (superpopulation simulation, seeds 42-44, 1,000 replicates per cell per seed)",
             "script": art("compute/sim_lm1.py"), "output": art("compute/sim-lm1.json"), "stdout": art("compute/sim-lm1.stdout")},
            {"label": "pilot guards, full-study arithmetic by branch, Mac-time matching for P2",
             "script": art("compute/caps_lm1.py"), "output": art("compute/caps-lm1.json"), "stdout": art("compute/caps-lm1.stdout")},
        ],
    }
    doctors = []
    for name in ("source", "citation", "novelty", "design", "compute", "safety"):
        rec = json.loads((BUNDLE / f"doctors/{name}.json").read_text(encoding="utf-8"))
        doctors.append({"name": rec["name"], "status": rec["status"], **art(f"doctors/{name}.json")})
    bundle = {
        "schema_version": 1,
        "proposal": str(PROPOSAL.relative_to(ROOT)),
        "proposal_sha256": sha(PROPOSAL),
        "draft_registration": {"path": str(REGISTRATION.relative_to(ROOT)), "sha256": sha(REGISTRATION), "status": "DRAFT"},
        "source_snapshots": snapshots,
        "query_log": art("query-log.json"),
        "reviews": [],
        "reviews_status": "not run: the blind critic, the refute-first triad and both reviewers follow this synthesis; no trusted Ed25519 store exists (D24)",
        "compute": compute,
        "doctors": doctors,
        "audit_log": None,
        "audit_log_status": "no gauntlet row yet; the recorder appends program/gauntlet/2026-10-16-lm1-matched-memory-quality.jsonl after the reviewers score",
        "blind_discrimination_packet": {
            "paragraphs": [art(f"blind/{p.name}") for p in sorted((BUNDLE / "blind").glob("*.txt"))],
            "roles": art("compute/blind-roles.json", note="recorder only; never shown to the critic"),
        },
        "source_reads_by_synthesis": {
            "orx_full_text": ["2509.25689", "2504.02010", "2610.15372", "2604.18556", "2404.05405", "2508.10925"],
            "orx_abstract": ["2604.24827", "2609.12111", "2610.02462", "2609.06076", "2505.24832"],
            "llamacpp_commit": "620d2225cc436ab0b001e3200e590e3b286ef9ab",
            "hub_revisions": {"AA-Omniscience-Public": "e4883edbb9f5ccf2b2a8fdc6fb65e01a58e99849",
                              "simpleqa-verified": "0dc97e0d28d8233463e005cdc4475cc2a13ba2dc",
                              "SuperGPQA": "4430d4458112c7d4497fdcf94d7cc223313d6acf",
                              "Kimi-K2.5": "4d01dfe0332d63057c186e0b262165819efb6611",
                              "Qwen3-235B-A22B-Instruct-2507": "ac9c66cc9b46af7306746a9250f23d47083d689e",
                              "DeepSeek-V4-Flash-0731": "7872f01b1d1fe23eabc4c98b48bffcef5a386062",
                              "Qwen3.8-27B": "1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0"},
        },
        "budget_ledger": {
            "declared": {"queries": 150, "wall_minutes": 720, "tokens": 10000000, "dollars": 150, "waves": 3, "gpu_hours": 0.5},
            "queries": json.loads((BUNDLE / "query-log.json").read_text(encoding="utf-8"))["counts"],
            "gpu_hours_used_by_synthesis": 0.0,
            "host_jobs_submitted_by_synthesis": 0,
            "tokens_wall_dollars": "metered by the orchestrator over the whole wave",
        },
    }
    bundle["evidence_root_sha256"] = evidence_root(bundle)
    return bundle


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--doctor-output", type=Path)
    args = ap.parse_args()
    path = BUNDLE / "bundle.json"
    if args.doctor_output:
        bundle = json.loads(path.read_text(encoding="utf-8"))
        rel = str(args.doctor_output.resolve().relative_to(BUNDLE.resolve()))
        out = json.loads(args.doctor_output.read_text(encoding="utf-8"))
        bundle["direction_doctor_run"] = {
            "command": "uv run python scripts/research_direction_doctor.py program/proposals/2026-10-16-lm1-matched-memory-quality.md",
            "status": out.get("status"), "acceptedScore": out.get("acceptedScore"), "hardCaps": out.get("hardCaps"),
            "evidence_root_at_run": bundle["evidence_root_sha256"], **art(rel),
        }
    else:
        bundle = build()
    path.write_text(json.dumps(bundle, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print("proposal", bundle["proposal_sha256"])
    print("evidence_root", bundle["evidence_root_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
