#!/usr/bin/env python3
"""Assemble bundle.json for the E4 gate's fresh gauntlet run after the D60 repair.

Same contract as wave 1's `compute/build-bundle.py` (kept as it was): hashes every
artifact, computes evidence_root_sha256 exactly as scripts/research_direction_doctor.py
does (over source_snapshots, query_log, compute, doctors, audit_log), and records the
proposal and draft-registration hashes. Differences: the draft registration is v2, the
query log is this run's (`query-log-run2.json`, wave 1's `query-log.json` referenced by
hash), the repair's CPU checks are listed, and the blind packets follow
`compute/repair-d60/blind-roles-run2.json`. Run from the worktree root after any change:

    python3 program/proposals/evidence/2026-10-10-e4-icl-write-rule-gate/compute/repair-d60/build-bundle-v2.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
BUNDLE = ROOT / "program/proposals/evidence/2026-10-10-e4-icl-write-rule-gate"
PROPOSAL = ROOT / "program/proposals/2026-10-10-e4-icl-write-rule-gate.md"
REGISTRATION = ROOT / "program/preregistrations/e4-icl-write-rule-gate-v2.md"
REGISTRATION_V1 = ROOT / "program/preregistrations/e4-icl-write-rule-gate-v1.md"
R = "compute/repair-d60"


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
    qlog = json.loads((BUNDLE / "query-log-run2.json").read_text(encoding="utf-8"))
    not_run = "compute/attestations-not-run.md"
    compute = {
        "scope": "e4-icl-write-rule-gate-v2 is a DRAFT; no compute attestation of its own exists (compute/attestations-not-run.md). Supplementary CPU evidence: wave 1's S1-S3 (kept unedited) and the D60 repair's F1 (family table under the teacher's tokenizer), S1v2 (the registered estimator on the linear surrogate, central run and identifiability grid), G1 (guard), S2v2 (decision path) and S3v2 (cost), each script with its output.",
        "image_digest": "127.0.0.1:5000/cotcodec-research@sha256:13a9de831cff50461d8ecee3c2794f0c6d6bcffe9d602968fe2ee06e5a1096e9",
        "image_scope": "build 855, commit ed5d5a93 (torch 2.11.0+cu128, transformers 5.15.0, flash-linear-attention 0.5.2, tilelang 0.1.13); no flash-attn, so the fla teacher needs the registration's Llama remap or SDPA shim, neither written",
        "real_model_loop": False,
        "real_model_loop_scope": "none: harness/e4_gate.py does not exist; no fla-hub checkpoint has been loaded in any image; the D60 repair ran on the Mac CPU only",
        "benchmark_adapter": None,
        "benchmark_adapter_scope": "none: the family generators exist only as the repair's table builder (compute/repair-d60/family-table.py), not as a manifest builder",
        "manifest": None,
        "manifest_scope": "no Slurm manifest exists for any of the four registered jobs",
        "container_smoke": {"label": "container_smoke", "status": "NOT_RUN", "return_code": None, **art(not_run)},
        "slurm_test": {"label": "slurm_test", "status": "NOT_RUN", "return_code": None, **art(not_run)},
        "provenance_verification": {"label": "provenance_verification", "status": "NOT_RUN", "return_code": None, **art(not_run)},
        "registered_caps_gpu_h": {"S0_smoke": 0.17, "S1_eligibility": 0.55, "S2_oracle_main": 5.5, "S2_conditional": 1.5, "sum": 7.72},
        "supplementary_cpu_evidence": [
            {"label": "F1 family table under the teacher's tokenizer (d6f66f41, tokenizer.json sha256 fc4f0bd7...)",
             "script": art(f"{R}/family-table.py"), "output": art(f"{R}/family-table.json")},
            {"label": "S1v2 registered v2 estimator on the linear surrogate (central regime, wave-1 regime, misfit scenario; seeds 42/43/44)",
             "script": art(f"{R}/oracle-estimator-v2.py"), "output": art(f"{R}/oracle-estimator-v2.json")},
            {"label": "S1v2 identifiability grid (d_task x fitting probes; seed 42)",
             "script": art(f"{R}/oracle-estimator-v2.py"), "output": art(f"{R}/oracle-estimator-v2-grid.json")},
            {"label": "G1 episode-constant guards on a categorical teacher (exact)",
             "script": art(f"{R}/guard-sim.py"), "output": art(f"{R}/guard-sim.json")},
            {"label": "S2v2 decision path end to end (2,000 replicates per cell; design seed 42)",
             "script": art(f"{R}/decision-sim-v2.py"), "output": art(f"{R}/decision-sim-v2.json")},
            {"label": "S3v2 GPU-hour arithmetic and caps",
             "script": art(f"{R}/cost-model-v2.py"), "output": art(f"{R}/cost-model-v2.json")},
            {"label": "run-2 query log builder", "script": art(f"{R}/build-query-log-run2.py")},
            {"label": "wave-1 S1 oracle-class semantics and KILL A (kept unedited)",
             "script": art("compute/oracle-class-semantics.py"), "output": art("compute/oracle-class-semantics.json")},
            {"label": "wave-1 S2 decision-rule operating characteristics (kept unedited)",
             "script": art("compute/decision-sim.py"), "output": art("compute/decision-sim.json")},
            {"label": "wave-1 S3 cost model (kept unedited)",
             "script": art("compute/cost-model.py"), "output": art("compute/cost-model.json")},
            {"label": "snapshot script for source_snapshots", "script": art("compute/snapshot-sources.py")},
        ],
    }
    doctors = [{"name": name.capitalize(), "status": json.loads((BUNDLE / f"doctors/{name}.json").read_text())["status"],
                **art(f"doctors/{name}.json")}
               for name in ("source", "citation", "novelty", "design", "compute", "safety")]
    bundle = {
        "schema_version": 1,
        "proposal": str(PROPOSAL.relative_to(ROOT)),
        "proposal_sha256": sha(PROPOSAL),
        "draft_registration": {"path": str(REGISTRATION.relative_to(ROOT)), "sha256": sha(REGISTRATION),
                               "status": "DRAFT, not frozen, no ledger row; supersedes v1",
                               "superseded_v1": {"path": str(REGISTRATION_V1.relative_to(ROOT)), "sha256": sha(REGISTRATION_V1)}},
        "source_snapshots": snapshots,
        "query_log": {**art("query-log-run2.json"), "queries_against_budget": qlog["counted_by_repair_owner"],
                      "declared_budget": 80, "reserved_for_refuters": 30,
                      "wave1_query_log": art("query-log.json"),
                      "note": "This run's counted queries so far (the repair's 33); wave 1's 159 are in query-log.json and the wave-1 record."},
        "reviews": [],
        "reviews_status": "NOT_RUN for this run: the blind critic, the refute-first triad and both reviewers run after the repair. Wave 1's reviews are in program/gauntlet/2026-10-10-e4-icl-write-rule-gate.jsonl. No trusted Ed25519 store exists (D24).",
        "compute": compute,
        "doctors": doctors,
        "audit_log": None,
        "audit_log_status": "Wave 1's row is the first row of program/gauntlet/2026-10-10-e4-icl-write-rule-gate.jsonl (hash b658a265...); this run's row is appended after its reviewers score.",
    }
    payload = {key: bundle.get(key) for key in ("source_snapshots", "query_log", "compute", "doctors", "audit_log")}
    bundle["evidence_root_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    blind = {}
    for path in sorted((BUNDLE / "blind").glob("paragraph-*.txt")):
        blind[path.name] = art(f"blind/{path.name}", text_sha256=hashlib.sha256(
            path.read_text(encoding="utf-8").rstrip("\n").encode()).hexdigest())
    roles = json.loads((BUNDLE / f"{R}/blind-roles-run2.json").read_text(encoding="utf-8"))
    bundle["blind_discrimination_packet"] = {
        "proposal": blind[roles["proposal"]],
        "closest_prior": blind[roles["closest_prior"]],
        "closest_prior_id": roles["closest_prior_id"],
        "additional_prior_packets": [{"packet": blind[name], "prior": desc} for name, desc in roles["additional_packets"].items()],
        "wave1_packets": {"proposal": "blind/paragraph-b8b5e36a.txt", "closest_prior": "blind/paragraph-c840d8c6.txt",
                          "role_map": "compute/blind-roles.json"},
        "note": "File names carry no role and each file holds only its paragraph. One critic call per prior packet, each with the proposal paragraph, in randomized order, read by path, without the role map or any other text.",
    }
    bundle["budget_ledger"] = {
        "declared": {"queries": 80, "wall_minutes": 600, "tokens": 8000000, "dollars": 150, "waves": 1, "gpu_hours": 0.3},
        "used_by_repair": {"queries": qlog["counted_by_repair_owner"], "paper_reads": len(qlog["full_text_reads_not_counted"]),
                           "gpu_hours": 0.0, "host": "none (no ssh, no host job)",
                           "wall_minutes_and_tokens": "metered by the recorder from transcripts"},
        "remaining_queries": 80 - qlog["counted_by_repair_owner"],
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
