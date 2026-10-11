#!/usr/bin/env python3
"""Assemble bundle.json for the S2 v3 gauntlet wave 1 (synthesis).

Hashes every artifact, computes evidence_root_sha256 exactly as scripts/research_direction_doctor.py
does (over source_snapshots, query_log, compute, doctors, audit_log), and records the proposal and
draft-registration hashes. Run from the worktree root after any change:

    python3 program/proposals/evidence/2026-10-11-s2v3-arabic-cua-locale-pilot/compute/build-bundle.py
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
BUNDLE = ROOT / "program/proposals/evidence/2026-10-11-s2v3-arabic-cua-locale-pilot"
PROPOSAL = ROOT / "program/proposals/2026-10-11-s2v3-arabic-cua-locale-pilot.md"
REGISTRATION = ROOT / "program/preregistrations/s2-arabic-cua-locale-v3.md"
REG_V2 = ROOT / "program/preregistrations/s2-arabic-cua-locale-v2.md"
SBATCH = ROOT / "infra/slurm/host-single-node/s2v3-pilot-cpu.sbatch"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def art(rel: str, **extra) -> dict:
    return {"artifact": rel, "sha256": sha(BUNDLE / rel), **extra}


def files(sub: str) -> list[dict]:
    return [art(str(p.relative_to(BUNDLE))) for p in sorted((BUNDLE / sub).rglob("*")) if p.is_file()]


def main() -> None:
    snapshots = []
    for path in sorted((BUNDLE / "snapshots").glob("*.json")):
        rec = json.loads(path.read_text(encoding="utf-8"))
        entry = {"url": rec["url"], "http_status": rec["http_status"], "fetched_at": rec["fetched_at"],
                 "raw_sha256": rec["raw_sha256"], "raw_bytes": rec["raw_bytes"], **art(f"snapshots/{path.name}")}
        if "openreview.net" in rec["url"]:
            entry["content_note"] = "OpenReview pages may return a browser challenge; the HTTP status verifies nothing about content"
        snapshots.append(entry)
    qlog = json.loads((BUNDLE / "query-log.json").read_text(encoding="utf-8"))
    pool = json.loads((BUNDLE / "compute/pool/pool-v3.json").read_text())
    power = json.loads((BUNDLE / "compute/power/power-v3.json").read_text())
    receipt = "compute/pilot/job1098/run-1098.json"
    compute = {
        "scope": ("s2-arabic-cua-locale-v3 is a DRAFT. A partial executable Phase 0 pilot ran as CPU-only Slurm jobs 1097-1100 in the "
                  "certified VM's own LibreOffice userland (compute/attestations.md); the derived Arabic image, the VM-lane oracle, the delta "
                  "certification, Phase 1 and any orx node did not run."),
        "image_digest": "docker.io/vllm/vllm-openai@sha256:b18abb2df97b8f798e81862bd93f872ea18613372e2c3adc0cc2ac21e66ac12f",
        "image_scope": ("Phase 1 engine base image (vLLM v0.31.0, commit db9527a4; cu129 overlay rebuilt per commit as S1a). The Phase 0 pilot "
                        "ran in cotcodec-q2-lo-vm@sha256:f5b4c40eefd2b92f846652910ba34db35e1ae7bf90fa474595cc745cc5895361."),
        "pilot_image_digest": "sha256:f5b4c40eefd2b92f846652910ba34db35e1ae7bf90fa474595cc745cc5895361",
        "real_model_loop": False,
        "real_model_loop_scope": "S1a's loop ran 1,808 episodes (D66); no S2 episode has run",
        "benchmark_adapter": None,
        "benchmark_adapter_scope": "OSWorld b138d348 as S1a ran it; S2 adds a cell selector and checks, not an adapter (not written)",
        "manifest": None,
        "manifest_scope": "no Phase 1 Slurm manifest exists",
        "container_smoke": {"label": "container_smoke", "status": "PASS", "return_code": 0,
                            "scope": "Phase 0 pilot container only (job 1098); not the Phase 1 engine image", **art(receipt)},
        "slurm_test": {"label": "slurm_test", "status": "NOT_RUN", "return_code": None,
                       "scope": "no Phase 1 dry run or test-only; the pilot's CPU jobs were real submissions", **art("compute/attestations.md")},
        "provenance_verification": {"label": "provenance_verification", "status": "NOT_RUN", "return_code": None,
                                    **art("compute/attestations.md")},
        "pilot_jobs": {
            "sbatch": {"path": str(SBATCH.relative_to(ROOT)), "sha256": sha(SBATCH)},
            "receipts": [art(f"compute/pilot/job{j}/run-{j}.json") for j in (1097, 1098, 1099, 1100)],
            "records": [art("compute/pilot/job1097/debug-record.json"), art("compute/pilot/job1098/pilot-record.json"),
                        art("compute/pilot/job1099/pilot-b-record.json"), art("compute/pilot/job1099/pilot-b-analysis.json"),
                        art("compute/pilot/job1100/pilot-b-record.json"), art("compute/pilot/job1100/o3-analysis.json")],
            "scripts": files("compute/pilot") and [a for a in files("compute/pilot") if a["artifact"].endswith(".py")],
            "slurm_logs": [art(f"compute/pilot/job{j}/slurm-cotcodec-s2v3-pilot-cpu-{j}.out") for j in (1097, 1098, 1099, 1100)],
            "gpu_hours": 0.0,
        },
        "registered_caps_gpu_h": {"K106_n4": power["costs"]["K106_n4"], "K89_n4": power["costs"]["K89_n4"], "K62_n4": power["costs"]["K62_n4"],
                                  "registered_total_gpu_h": 6.10, "at_p95_slot_gpu_h": 6.867},
        "supplementary_cpu_evidence": [
            {"label": "pool: the enlarged LibreOffice task pool (106 tasks) under rules E1-E5, C1, F1", "script": art("compute/pool/pool-v3.py"),
             "output": art("compute/pool/pool-v3.json"), "summary": pool["summary"]["admitted_by_split"]},
            {"label": "power: operating characteristics of the registered rules, 2,000 replicates x seeds 42-44",
             "script": art("compute/power/power-v3.py"), "output": art("compute/power/power-v3.json"), "log": art("compute/power/power-v3.log"),
             "tables": [art("compute/power/tables-v3.py"), art("compute/power/tables-v3.md")]},
            {"label": "discovery cells: query logs, kill-shot simulations, cross-domain guard sketch (copied unchanged from the cells' scratch)",
             "files": files("compute/cells")},
            {"label": "builders", "files": [art("compute/build-query-log.py"), art("compute/build-doctors.py"), art("compute/build-bundle.py"),
                                            art("compute/snapshot-sources.py")]},
        ],
        "repository_evidence_used": {
            "s1a_records": "program/evidence/2026-10-10/q2-stage1-analysis/a1.jsonl",
            "s1a_plan": "program/evidence/2026-10-09/q2-stage1-prefreeze/plan/plan-a0a.json",
            "splits": "program/evidence/q2-mutation/splits.json",
            "osworld_test_all_sha256": pool["inputs"]["test_all_json_sha256"],
            "design_study": "program/evidence/2026-10-10/q2-next-step-design-study/README.md",
            "d53": "program/decisions.md D53",
        },
    }
    doctors = [{"name": n.capitalize(), "status": json.loads((BUNDLE / f"doctors/{n}.json").read_text())["status"], **art(f"doctors/{n}.json")}
               for n in ("source", "citation", "novelty", "design", "compute", "safety")]
    bundle = {
        "schema_version": 1,
        "proposal": str(PROPOSAL.relative_to(ROOT)),
        "proposal_sha256": sha(PROPOSAL),
        "draft_registration": {"path": str(REGISTRATION.relative_to(ROOT)), "sha256": sha(REGISTRATION),
                               "experiment_id": "s2-arabic-cua-locale-v3", "status": "DRAFT, not frozen, no ledger row",
                               "predecessor": {"path": str(REG_V2.relative_to(ROOT)), "sha256": sha(REG_V2),
                                               "experiment_id": "s2-arabic-cua-locale-v2", "note": "left unedited (gauntlet rule 3)"}},
        "source_snapshots": snapshots,
        "query_log": {**art("query-log.json"), "counted": qlog["counted"], "declared": 150, "reserved_for_refuters": 30,
                      "remaining_under_run2_convention": qlog["remaining_under_run2_convention"]},
        "reviews": [],
        "reviews_status": "NOT_RUN: this wave's blind critic, refute-first triad and reviewers run after the synthesis. No trusted Ed25519 store exists (D24).",
        "compute": compute,
        "doctors": doctors,
        "audit_log": None,
        "audit_log_status": "This wave's row is appended to program/gauntlet/ with scripts/research_gauntlet_record.py after its reviewers score.",
    }
    payload = {key: bundle.get(key) for key in ("source_snapshots", "query_log", "compute", "doctors", "audit_log")}
    bundle["evidence_root_sha256"] = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    roles = json.loads((BUNDLE / "compute/blind-roles.json").read_text())
    blind = {}
    for path in sorted((BUNDLE / "blind").glob("paragraph-*.txt")):
        blind[path.name] = art(f"blind/{path.name}", text_sha256=hashlib.sha256(path.read_text().rstrip("\n").encode()).hexdigest())
    bundle["blind_discrimination_packet"] = {"proposal": blind[roles["proposal"]], "closest_prior": blind[roles["closest_prior"]],
                                             "closest_prior_id": roles["closest_prior_id"],
                                             "note": "File names carry no role; compute/blind-roles.json is for the recorder only."}
    bundle["budget_ledger"] = {"declared": {"queries": 150, "wall_minutes": 600, "tokens": 8000000, "dollars": 150, "waves": 3, "gpu_hours": 0.3},
                               "queries_used_before_triad": qlog["counted"], "gpu_hours_used": 0.0,
                               "host_jobs": "CPU-only Slurm 1096 (cancelled), 1097-1100 (exit 0); no GPU job"}
    out = BUNDLE / "doctors/research-direction-doctor-output.json"
    if out.exists():
        bundle["research_direction_doctor_output"] = {**art("doctors/research-direction-doctor-output.json"),
                                                      "note": "verbatim stdout of the doctor on this bundle (exit 1); not part of the evidence root"}
    (BUNDLE / "bundle.json").write_text(json.dumps(bundle, indent=1, ensure_ascii=False) + "\n")
    print("proposal", bundle["proposal_sha256"][:12], "root", bundle["evidence_root_sha256"][:12], "snapshots", len(snapshots))


if __name__ == "__main__":
    main()
