#!/usr/bin/env python3
"""Assemble bundle.json for the E7 G1 gate's fresh gauntlet run after the D68 repair.

Same contract as wave 1's `compute/build-bundle.py` (kept as it was): hashes every
artifact, computes evidence_root_sha256 exactly as scripts/research_direction_doctor.py
does (over source_snapshots, query_log, compute, doctors, audit_log), and records the
proposal and draft-registration hashes. Differences: the draft registration is v2 (v1
recorded as superseded), the query log is this run's (`query-log-run2.json`, wave 1's
`query-log.json` referenced by hash), the repair's CPU checks are listed, the wave-1
audit row is referenced, and the blind packets follow
`compute/repair-d68/blind-roles-run2.json`. Run from the worktree root after any change:

    python3 program/proposals/evidence/2026-10-10-e7-equivariant-writes-g1/compute/repair-d68/build-bundle-v2.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
BUNDLE = ROOT / "program/proposals/evidence/2026-10-10-e7-equivariant-writes-g1"
PROPOSAL = ROOT / "program/proposals/2026-10-10-e7-equivariant-writes-g1.md"
REGISTRATION = ROOT / "program/preregistrations/e7-equivariant-writes-g1-v2.md"
REGISTRATION_V1 = ROOT / "program/preregistrations/e7-equivariant-writes-g1-v1.md"
AUDIT = ROOT / "program/gauntlet/2026-10-10-e7-equivariant-writes-g1.jsonl"
R = "compute/repair-d68"


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
                                     "the abstract comes from the OpenReview search API (query logs)")
        snapshots.append(entry)
    qlog = json.loads((BUNDLE / "query-log-run2.json").read_text(encoding="utf-8"))
    cost = json.loads((BUNDLE / f"{R}/cost-model-v2.json").read_text(encoding="utf-8"))
    reach = json.loads((BUNDLE / f"{R}/reach-cut-v2.json").read_text(encoding="utf-8"))
    pool = json.loads((BUNDLE / f"{R}/instrument-pool-v2.json").read_text(encoding="utf-8"))
    sim = json.loads((BUNDLE / f"{R}/gate-sim-v2.json").read_text(encoding="utf-8"))
    not_run = "compute/attestations-not-run.md"
    compute = {
        "scope": ("e7-equivariant-writes-g1-v2 is a DRAFT; no compute attestation of its own exists "
                  "(compute/attestations-not-run.md). Supplementary CPU evidence: the D68 repair's S3v2 (which "
                  "intervention removes which path, complex step against exact symbolic reachability), P1 (the "
                  "measured NTREX-128 pool and the surface controls), S1v2 (the decision rule under the registered "
                  "estimator) and S2v2 (caps with arithmetic), and wave 1's S1, S2 and S3 (kept unedited)."),
        "image_digest": "127.0.0.1:5000/cotcodec-research@sha256:02965f3d696d4e516a7cd6d5c03434e9098139738748ae778ed967215db7be6d",
        "image_scope": ("the image behind the measured 134M throughput (cotcodec-research:0b3ecef0-architecture, Slurm 359; "
                        "torch 2.11.0+cu128, fla 0.5.2, triton 3.6.0, tilelang 0.1.13); the G1 image is built from the "
                        "harness commit and pinned before J1"),
        "real_model_loop": False,
        "real_model_loop_scope": "none: the A0 model, the interventions, the training loop and the data builders are not written",
        "benchmark_adapter": None,
        "benchmark_adapter_scope": "none: the TP-MQAR-v2-G1 builder v2, the evaluator and the analysis are not written (P1 is CPU evidence, not the adapter)",
        "manifest": None,
        "manifest_scope": "no Slurm manifest exists for J1, J2, J3, T42, T43 or T44",
        "container_smoke": {"label": "container_smoke", "status": "NOT_RUN", "return_code": None, **art(not_run)},
        "slurm_test": {"label": "slurm_test", "status": "NOT_RUN", "return_code": None, **art(not_run)},
        "provenance_verification": {"label": "provenance_verification", "status": "NOT_RUN", "return_code": None, **art(not_run)},
        "registered_caps_gpu_h": {j["job"].split(" ")[0]: j["cap_gpu_h"] for j in cost["jobs"]},
        "cap_sum_gpu_h_D22": cost["cap_sum_gpu_h_D22"],
        "cap_sum_with_one_J2_resubmission": round(cost["cap_sum_gpu_h_D22"] + cost["jobs"][1]["cap_gpu_h"], 3),
        "central_gpu_h": cost["central_gpu_h_all_seeds_no_extension"],
        "central_gpu_h_futility_path": cost["central_gpu_h_if_futility_stop_after_seed_42"],
        "throughput_gate_tokens_per_s": cost["throughput_gate_min_training_tokens_per_s"],
        "supplementary_cpu_evidence": [
            {"label": f"S3v2 intervention table on a NumPy reference of the module graph: all_checks_ok={reach['all_checks_ok']}, rows {reach['n_rows']}, boundaries {reach['symbolic_reach_boundaries']}",
             "script": art(f"{R}/reach-cut-v2.py"), "output": art(f"{R}/reach-cut-v2.json")},
            {"label": f"P1 NTREX-128 pool and surface controls (test half {pool['test_half_eligible']} key sentences; pooled cross-script clogit oracle {pool['cross_script_pooled_equal_weight']})",
             "script": art(f"{R}/instrument-pool-v2.py"), "output": art(f"{R}/instrument-pool-v2.json")},
            {"label": f"S1v2 decision rule under the registered estimator ({sim['replicates_per_scenario']} replicates per scenario; prior-weighted decisive {sim['prior_weighted_decisive']['by_seed_sd']})",
             "script": art(f"{R}/gate-sim-v2.py"), "output": art(f"{R}/gate-sim-v2.json")},
            {"label": f"S2v2 caps and arithmetic (sum {cost['cap_sum_gpu_h_D22']} GPU-h)",
             "script": art(f"{R}/cost-model-v2.py"), "output": art(f"{R}/cost-model-v2.json")},
            {"label": "run-2 query log builder", "script": art(f"{R}/build-query-log-run2.py")},
            {"label": "snapshot script for the run's new source URLs", "script": art(f"{R}/snapshot-new-sources.py")},
            {"label": "wave-1 S1 decision-rule simulation (kept unedited)", "script": art("compute/gate-sim.py"), "output": art("compute/gate-sim.json")},
            {"label": "wave-1 S2 cost model (kept unedited)", "script": art("compute/cost-model.py"), "output": art("compute/cost-model.json")},
            {"label": "wave-1 S3 reach doctor (kept unedited)", "script": art("compute/reach-doctor.py"), "output": art("compute/reach-doctor.json")},
            {"label": "legacy phase-0 object doctor rerun on main by the wave-1 asset cell (synthetic objects only)",
             "output": art("compute/legacy-phase0-doctor-main.json")},
            {"label": "wave-1 query-log builder and snapshot script", "script": art("compute/build-query-log.py")},
            {"label": "snapshot script for source_snapshots (wave 1)", "script": art("compute/snapshot-sources.py")},
        ],
        "repository_evidence_used": {
            "throughput_receipt": "legacy/research/evidence/infrastructure/fla-throughput-h100-2026-09-01.json (runs[1], Slurm 359)",
            "throughput_doctor": "scripts/fla_throughput_doctor.py (layout i % 4 == 3, MLP 768-4096-768)",
            "legacy_contract": "legacy/experiments/architectures/translation-equivariant-state-writes.yaml (v5; the 4-gram clause restored from it)",
        },
    }
    doctors = [{"name": name.capitalize(), "status": json.loads((BUNDLE / f"doctors/{name}.json").read_text())["status"],
                **art(f"doctors/{name}.json")}
               for name in ("source", "citation", "novelty", "design", "compute", "safety")]
    audit_rows = [json.loads(line) for line in AUDIT.read_text(encoding="utf-8").splitlines() if line.strip()]
    bundle = {
        "schema_version": 1,
        "proposal": str(PROPOSAL.relative_to(ROOT)),
        "proposal_sha256": sha(PROPOSAL),
        "draft_registration": {"path": str(REGISTRATION.relative_to(ROOT)), "sha256": sha(REGISTRATION),
                               "experiment_id": "e7-equivariant-writes-g1-v2",
                               "status": "DRAFT, not frozen, no ledger row; supersedes v1",
                               "superseded_v1": {"path": str(REGISTRATION_V1.relative_to(ROOT)), "sha256": sha(REGISTRATION_V1)}},
        "source_snapshots": snapshots,
        "query_log": {**art("query-log-run2.json"), "queries_against_budget": qlog["counted_by_repair_owner"],
                      "declared_budget": 80, "reserved_for_refuters": 30,
                      "wave1_query_log": art("query-log.json"),
                      "note": (f"This run's counted queries so far (the repair's {qlog['counted_by_repair_owner']}); "
                               f"{80 - qlog['counted_by_repair_owner']} remain for the triad (at least 30 reserved). Wave 1's "
                               "97 cell queries are in query-log.json and the novelty refuter's 15 in the wave-1 record.")},
        "reviews": [],
        "reviews_status": ("NOT_RUN for this run: the blind critic, the refute-first triad and both reviewers run after the "
                           "repair. Wave 1's reviews are in program/gauntlet/2026-10-10-e7-equivariant-writes-g1.jsonl. No "
                           "trusted Ed25519 store exists (D24)."),
        "compute": compute,
        "doctors": doctors,
        "audit_log": None,
        "audit_log_status": (f"Wave 1's row is row 1 of {AUDIT.relative_to(ROOT)} (hash {audit_rows[-1]['hash'][:16]}..., "
                             f"file sha256 {sha(AUDIT)[:16]}...); this run's row is appended after its reviewers score."),
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
        "wave1_packets": roles["wave1_packets"],
        "note": ("File names carry no role and each file holds only its paragraph. One critic call per prior packet, each "
                 "with the proposal paragraph, in randomized order, read by path, without the role map or any other text."),
    }
    bundle["cell_verdicts"] = art("cells/cell-verdicts.json")
    bundle["budget_ledger"] = {
        "declared": {"queries": 80, "wall_minutes": 600, "tokens": 8000000, "dollars": 150, "waves": 1, "gpu_hours": 0.3},
        "used_by_repair": {"queries": qlog["counted_by_repair_owner"], "paper_reads": len(qlog["full_text_reads_not_counted"]),
                           "gpu_hours": 0.0, "host": "none (no ssh, no host job)",
                           "cpu": "S3v2 (about 13 min, 12 workers), P1 (about 6 min), S1v2 (multi-worker, see its runtime_seconds), S2v2 on the development Mac",
                           "wall_minutes_and_tokens": "metered by the recorder from transcripts"},
        "remaining_queries": 80 - qlog["counted_by_repair_owner"],
        "refuter_reserve_shortfall": max(0, 30 - (80 - qlog["counted_by_repair_owner"])),
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
