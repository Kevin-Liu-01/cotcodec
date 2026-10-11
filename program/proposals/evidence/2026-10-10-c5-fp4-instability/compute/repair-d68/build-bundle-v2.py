#!/usr/bin/env python3
"""Assemble bundle.json for C5's fresh gauntlet run after the D68 repair.

Same contract as wave 1's `compute/build-bundle.py` (kept as it was): hashes every artifact, computes
evidence_root_sha256 exactly as scripts/research_direction_doctor.py does (over source_snapshots,
query_log, compute, doctors, audit_log), and records the proposal and draft-registration hashes.
Differences: the draft registration is v2 (v1 recorded as superseded), the query log is run 2's
(`query-log-run2.json`; wave 1's `query-log.json` referenced by hash), the repair's CPU computations
are listed, and the blind packets follow `compute/repair-d68/blind-roles-run2.json`. Run from the
worktree root after any change:

    python3 program/proposals/evidence/2026-10-10-c5-fp4-instability/compute/repair-d68/build-bundle-v2.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
BUNDLE = ROOT / "program/proposals/evidence/2026-10-10-c5-fp4-instability"
PROPOSAL = ROOT / "program/proposals/2026-10-10-c5-fp4-instability.md"
REGISTRATION = ROOT / "program/preregistrations/c5-fp4-instability-v2.md"
REGISTRATION_V1 = ROOT / "program/preregistrations/c5-fp4-instability-v1.md"
GAUNTLET = ROOT / "program/gauntlet/2026-10-10-c5-fp4-instability.jsonl"
R = "compute/repair-d68"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def art(rel: str, **extra) -> dict:
    return {"artifact": rel, "sha256": sha(BUNDLE / rel), **extra}


def main() -> None:
    snapshots = []
    for path in sorted((BUNDLE / "snapshots").glob("*.json")):
        rec = json.loads(path.read_text(encoding="utf-8"))
        snapshots.append({"url": rec["url"], "http_status": rec["http_status"], "fetched_at": rec["fetched_at"],
                          "raw_sha256": rec["raw_sha256"], "raw_bytes": rec["raw_bytes"], **art(f"snapshots/{path.name}")})
    qlog = json.loads((BUNDLE / "query-log-run2.json").read_text(encoding="utf-8"))
    not_run = "compute/attestations-not-run.md"
    compute = {
        "scope": "c5-fp4-instability-v2 is a DRAFT; no compute attestation of its own exists (compute/attestations-not-run.md). Supplementary CPU evidence: wave 1's N1, N2, D1, S1 and S2 (kept unedited; all five reproduce byte for byte on 2026-10-10) and the D68 repair's N2v2 and N3 (tensor-level prediction for the v2 cells and the identification table), D1v2 (estimability and contrast SEs), S1v2 (the registered v2 decision path end to end) and S2v2 (caps with every factor applied), each script with its output.",
        "image_digest": "127.0.0.1:5000/cotcodec-research@sha256:13a9de831cff50461d8ecee3c2794f0c6d6bcffe9d602968fe2ee06e5a1096e9",
        "image_scope": "architecture image (build 855; torch 2.11.0+cu128, Triton 3.6.0, ml_dtypes present); holds no C5 code; a rebuild at the freeze commit is required",
        "real_model_loop": False,
        "real_model_loop_scope": "none: no LM pretraining loop, quantizer kernels, data loader, checkpointing or evaluation for this study exist; the D68 repair ran on the Mac CPU only",
        "benchmark_adapter": None,
        "benchmark_adapter_scope": "none: FineWeb-Edu files and tokenized shards are not on the host",
        "manifest": None,
        "manifest_scope": "no Slurm manifest exists for J0 to J4",
        "container_smoke": {"label": "container_smoke", "status": "NOT_RUN", "return_code": None, **art(not_run)},
        "slurm_test": {"label": "slurm_test", "status": "NOT_RUN", "return_code": None, **art(not_run)},
        "provenance_verification": {"label": "provenance_verification", "status": "NOT_RUN", "return_code": None, **art(not_run)},
        "registered_caps_gpu_h": {"J0": 0.25, "J1": 1.85, "J2": 0.40, "J3": 0.30, "fixed_sum": 2.80,
                                  "J4": "formula, at most 5.20; central 4.82; runs only if Part A stays at or below 8.0",
                                  "part_b": "formula after Phase 0; central single-process 70.1 / 79.2 / 88.3 / 97.4 at n = 3 / 4 / 5 / 6"},
        "supplementary_cpu_evidence": [
            {"label": "N2v2 and N3: tensor-level prediction for the v2 cells and the identification table (registered quantizer; exact-scale and wide-UE4M3 toggles; whole-tensor and per-row QSNR; UE4M3 subnormal and clamp shares; seeds 42-44)",
             "script": art(f"{R}/numerics_v2.py"), "output": art(f"{R}/numerics-v2.json")},
            {"label": "D1v2: estimability of the 10-cell set and contrast SEs and MDEs at n = 3 to 6",
             "script": art(f"{R}/doe_v2.py"), "output": art(f"{R}/doe-v2.json")},
            {"label": "S1v2: the registered v2 decision path end to end (J4 probe, G1, seed-count rule, sweeps, RCBD, P2 on 95% intervals, range flag, secondary verdicts, v1 reuse replay; 4,000 replicates per setting; exact Spearman critical value for 10 cells)",
             "script": art(f"{R}/power_sim_v2.py"), "output": art(f"{R}/power-sim-v2.json")},
            {"label": "S2v2: Phase 0 caps derived from workloads, J4 formula and fit, Part B caps with the 0.9 factor, wave 1's caps recomputed",
             "script": art(f"{R}/cost_model_v2.py"), "output": art(f"{R}/cost-model-v2.json")},
            {"label": "run-2 query log builder", "script": art(f"{R}/build-query-log-run2.py")},
            {"label": "snapshotter for the URLs the repair added (imports wave 1's snapshot code)", "script": art(f"{R}/snapshot-new-sources.py")},
            {"label": "wave-1 N1 exact numerics (kept unedited; reproduces)", "script": art("compute/numerics.py"), "output": art("compute/numerics.json")},
            {"label": "wave-1 N2 tensor-level prediction (kept unedited; reproduces)", "script": art("compute/crest_prediction.py"), "output": art("compute/crest-prediction.json")},
            {"label": "wave-1 D1 estimability (kept unedited; reproduces)", "script": art("compute/doe.py"), "output": art("compute/doe.json")},
            {"label": "wave-1 S1 decision-rule simulation (kept unedited; reproduces; superseded by S1v2)", "script": art("compute/power_sim.py"), "output": art("compute/power-sim.json")},
            {"label": "wave-1 S2 cost model (kept unedited; reproduces; its Phase 1 table omits the 0.9 factor, corrected in S2v2)", "script": art("compute/cost_model.py"), "output": art("compute/cost-model.json")},
            {"label": "snapshot script for source_snapshots", "script": art("compute/snapshot-sources.py")},
        ],
    }
    doctors = [{"name": name.capitalize(), "status": json.loads((BUNDLE / f"doctors/{name}.json").read_text())["status"],
                **art(f"doctors/{name}.json")} for name in ("source", "citation", "novelty", "design", "compute", "safety")]
    bundle = {
        "schema_version": 1,
        "proposal": str(PROPOSAL.relative_to(ROOT)),
        "proposal_sha256": sha(PROPOSAL),
        "draft_registration": {"path": str(REGISTRATION.relative_to(ROOT)), "sha256": sha(REGISTRATION),
                               "status": "DRAFT, not frozen, no ledger row; supersedes v1",
                               "superseded_v1": {"path": str(REGISTRATION_V1.relative_to(ROOT)), "sha256": sha(REGISTRATION_V1)}},
        "source_snapshots": snapshots,
        "query_log": {**art("query-log-run2.json"), "queries_against_budget": qlog["counted_by_repair_owner"],
                      "declared_budget": 80, "reserved_for_refuters": 30, "wave1_query_log": art("query-log.json"),
                      "note": "This run's counted queries so far (the repair's 16, 2 of them OpenAlex 429 rejections, counted); wave 1's 114 are in query-log.json and the wave-1 record."},
        "reviews": [],
        "reviews_status": "NOT_RUN for this run: the blind critic, the refute-first triad and both reviewers run after the repair. Wave 1's reviews are in program/gauntlet/2026-10-10-c5-fp4-instability.jsonl. No trusted Ed25519 store exists (D24).",
        "compute": compute,
        "doctors": doctors,
        "audit_log": None,
        "audit_log_status": "Wave 1's row is the first row of program/gauntlet/2026-10-10-c5-fp4-instability.jsonl (file sha256 " + sha(GAUNTLET) + "); this run's row is appended after its reviewers score.",
    }
    payload = {key: bundle.get(key) for key in ("source_snapshots", "query_log", "compute", "doctors", "audit_log")}
    bundle["evidence_root_sha256"] = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    blind = {}
    for path in sorted((BUNDLE / "blind").glob("paragraph-*.txt")):
        blind[path.name] = art(f"blind/{path.name}", text_sha256=hashlib.sha256(path.read_text(encoding="utf-8").rstrip("\n").encode()).hexdigest())
    roles = json.loads((BUNDLE / f"{R}/blind-roles-run2.json").read_text(encoding="utf-8"))
    bundle["blind_discrimination_packet"] = {
        "proposal": blind[roles["proposal"]],
        "closest_prior": blind[roles["closest_prior"]],
        "closest_prior_id": roles["closest_prior_id"],
        "additional_prior_packets": [{"packet": blind[name], "prior": desc} for name, desc in roles["additional_packets"].items()],
        "wave1_packets": {"proposal": "blind/paragraph-43655420.txt (superseded)", "closest_prior": "blind/paragraph-201f330b.txt",
                          "role_map": "compute/blind-roles.json"},
        "role_map_run2": art(f"{R}/blind-roles-run2.json"),
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
        bundle["direction_doctor_run"] = {**art("doctors/research-direction-doctor-output.json"),
                                          "command": "uv run python scripts/research_direction_doctor.py program/proposals/2026-10-10-c5-fp4-instability.md",
                                          "note": "Outside evidence_root by design: the doctor output depends on this bundle."}
    (BUNDLE / "bundle.json").write_text(json.dumps(bundle, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(bundle["proposal_sha256"], bundle["evidence_root_sha256"], len(snapshots))


if __name__ == "__main__":
    main()
