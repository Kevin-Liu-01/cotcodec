#!/usr/bin/env python3
"""Assemble bundle.json for the G2-stream gauntlet (wave 1 synthesis).

Hashes every artifact, computes evidence_root_sha256 exactly as scripts/research_direction_doctor.py
does (over source_snapshots, query_log, compute, doctors, audit_log), and records the proposal and
draft-registration hashes. With --doctor-output FILE it only adds the deterministic doctor's run
record (outside the evidence root, so the root and the doctor's reading stay valid).
Adapted from the G2-RL bundle's build_bundle.py.

Usage (repo root):
  python3 program/proposals/evidence/2026-10-16-g2-kimi-expert-streaming/compute/build_bundle.py
  python3 .../build_bundle.py --doctor-output program/proposals/evidence/.../doctors/direction-doctor-output.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
BUNDLE = ROOT / "program/proposals/evidence/2026-10-16-g2-kimi-expert-streaming"
PROPOSAL = ROOT / "program/proposals/2026-10-16-g2-kimi-expert-streaming.md"
REGISTRATION = ROOT / "program/preregistrations/g2-kimi-expert-streaming-v1.md"
RESEARCH_BASE = "docker.io/nvidia/cuda:12.8.1-cudnn-devel-ubuntu24.04@sha256:24c8e3581ea6330038b0d374920721983312627f8adbfcf390bdb4b399d280ed"
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
        entry = {
            "url": rec["url"], "http_status": rec["http_status"], "fetched_at": rec["fetched_at"],
            "raw_sha256": rec["raw_sha256"], "raw_bytes": rec["raw_bytes"], "primary": rec.get("primary"),
            **art(f"snapshots/{path.name}"),
        }
        if rec["http_status"] != 200:
            entry["content_note"] = (
                "HTTP 403 bot-challenge page; verifies nothing about content (UNVERIFIABLE_ACCESS by page). "
                "DOI metadata and abstract were verified through OpenAlex by the cross-domain cell (query-log.json)"
            )
        snapshots.append(entry)
    caps = json.loads((BUNDLE / "compute/caps-g2stream.json").read_text(encoding="utf-8"))
    not_run = "compute/attestations-not-run.md"
    compute = {
        "scope": (
            "g2-kimi-expert-streaming-v1 is a DRAFT pilot registration. No llama.cpp image, dump tool, manifest or "
            "host attestation exists; only CPU simulations on synthetic data and arithmetic on published numbers were "
            "run (compute/attestations-not-run.md)."
        ),
        "image_digest": RESEARCH_BASE,
        "image_scope": "research base on which the pilot's llama.cpp b11669 image is built at P0b; the full study's INT4 route uses " + VLLM_BASE,
        "real_model_loop": False,
        "benchmark_adapter": None,
        "manifest": None,
        "manifest_scope": "no manifest is rendered; the llama.cpp image id does not exist",
        "container_smoke": {"label": "container_smoke", "status": "NOT_RUN", "return_code": None, **art(not_run)},
        "slurm_test": {"label": "slurm_test", "status": "NOT_RUN", "return_code": None, **art(not_run)},
        "provenance_verification": {"label": "provenance_verification", "status": "NOT_RUN", "return_code": None, **art(not_run)},
        "executable_pilot": None,
        "executable_pilot_scope": "none run; the gauntlet's host rule allowed only the open-weight reviewer's lane job",
        "pilot_caps_gpu_h": {
            "total": caps["pilot"]["cap_gpu_h"], "expected": caps["pilot"]["expected_gpu_h"], "line": 8.0,
            "jobs": [{"job": j["job"], "cap": j["cap_gpu_h"], "conditional": j["conditional"], "arithmetic": j["arithmetic"]} for j in caps["pilot"]["jobs"]],
        },
        "full_study_gpu_h": {"range": caps["full"]["total_gpu_h"], "proposed_cap": caps["full"]["proposed_cap_gpu_h"]},
        "downloads_GB": caps["downloads_GB"],
        "supplementary_cpu_evidence": [
            {"label": "cache-policy simulators (LRU, LFU, ds4 decayed hotness, static, Belady; event-atomic), unit tests, readout and validation-rule operating characteristics (seeds 42-44, synthetic)",
             "script": art("compute/sim_g2stream.py"), "output": art("compute/sim-g2stream.json"), "stdout": art("compute/sim-g2stream.stdout")},
            {"label": "identification arithmetic on ds4's published targets: B from the whole-pool append, the frozen null, Kimi sensitivity",
             "script": art("compute/identification_g2stream.py"), "output": art("compute/identification-g2stream.json"), "stdout": art("compute/identification-g2stream.stdout"),
             "input": art("compute/ds4-targets.json")},
            {"label": "cap arithmetic for the pilot and the full study",
             "script": art("compute/caps_g2stream.py"), "output": art("compute/caps-g2stream.json"), "stdout": art("compute/caps-g2stream.stdout")},
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
        "audit_log_status": "no gauntlet row yet; the recorder appends program/gauntlet/2026-10-16-g2-kimi-expert-streaming.jsonl after the reviewers score",
        "blind_discrimination_packet": {
            "paragraphs": [art(f"blind/{p.name}") for p in sorted((BUNDLE / "blind").glob("*.txt"))],
            "roles": art("compute/blind-roles.json", note="recorder only; never shown to the critic"),
        },
        "source_reads_by_synthesis": {
            "ds4_commit": "90aa4b560a1dec1590f2c60648af404aa40b1188",
            "anemll_commit": "a809594fd2035979ad2b7ef23398127c1d07e891",
            "orx_full_text": ["2608.12103", "2608.07911", "2510.05497", "2609.14864", "2608.16157"],
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
            "command": "uv run python scripts/research_direction_doctor.py program/proposals/2026-10-16-g2-kimi-expert-streaming.md",
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
