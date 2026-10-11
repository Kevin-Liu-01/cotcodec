#!/usr/bin/env python3
"""Assemble bundle.json for the E3 Stage-0 probe's fresh gauntlet run after the D68 repair.

Same contract as wave 1's compute/build_bundle.py (kept as it was): hashes every artifact,
computes evidence_root_sha256 exactly as scripts/research_direction_doctor.py does (over
source_snapshots, query_log, compute, doctors, audit_log), and records the proposal and
draft-registration hashes. Differences: the draft registration is v2 (v1 kept and hashed),
the query log is this run's (wave 1's referenced by hash), the repair's CPU evidence is listed,
and the blind packets follow compute/repair-run2/blind-roles-run2.json. Run from the worktree
root after any change:

    python3 program/proposals/evidence/2026-10-10-e3-byte-boundary-headroom/compute/repair-run2/build_bundle_v2.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
BUNDLE = ROOT / "program/proposals/evidence/2026-10-10-e3-byte-boundary-headroom"
PROPOSAL = ROOT / "program/proposals/2026-10-10-e3-byte-boundary-headroom.md"
REGISTRATION = ROOT / "program/preregistrations/e3-byte-boundary-headroom-v2.md"
REGISTRATION_V1 = ROOT / "program/preregistrations/e3-byte-boundary-headroom-v1.md"
BASE_IMAGE = "127.0.0.1:5000/cotcodec-research@sha256:13a9de831cff50461d8ecee3c2794f0c6d6bcffe9d602968fe2ee06e5a1096e9"
R = "compute/repair-run2"


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
            entry["content_note"] = "HTTP 200 browser-challenge page; verifies nothing about content; abstract from the OpenReview search API (wave-1 query-log.json)"
        snapshots.append(entry)
    qlog = json.loads((BUNDLE / "query-log-run2.json").read_text(encoding="utf-8"))
    not_run = "compute/attestations-not-run.md"
    compute = {
        "scope": "e3-byte-boundary-headroom-v2 is a DRAFT; no compute attestation of its own exists (compute/attestations-not-run.md). Supplementary CPU evidence: wave 1's S1 and S2 (kept unedited) and the D68 repair's registered estimator as code, S1v2 (calibration, attenuation maps, design exploration, band constants, gates, identification scenario, line M, operating characteristics) and S2v2 (cost), each script with its output.",
        "image_digest": BASE_IMAGE,
        "image_scope": "pinned research base (CUDA 12.8.1 cudnn-devel; torch 2.11.0+cu128, transformers 5.15.0 in its own venv); the probe needs the v2 overlay environment (torch 2.7.1+cu128, flash-attn 2.8.0.post2 cu12torch2.7 wheel, mamba_ssm a6a1dae and causal_conv1d e940ead from source, transformers 4.57.1, hnet 3673fe12), specified and checked statically; not built",
        "real_model_loop": False,
        "real_model_loop_scope": "none: the encoder-only H-Net extraction driver, the OmniAlign and BinaryAlign drivers and the spaCy step are not written; no checkpoint is on the host",
        "benchmark_adapter": None,
        "benchmark_adapter_scope": "none: the estimator exists as compute/repair-run2/e3_estimator_v2.py (decision code used by S1v2), not yet as a harness/ module with unit tests",
        "manifest": None,
        "manifest_scope": "no Slurm manifest exists for the smoke or probe job",
        "container_smoke": {"label": "container_smoke", "status": "NOT_RUN", "return_code": None, **art(not_run)},
        "slurm_test": {"label": "slurm_test", "status": "NOT_RUN", "return_code": None, **art(not_run)},
        "provenance_verification": {"label": "provenance_verification", "status": "NOT_RUN", "return_code": None, **art(not_run)},
        "registered_caps_gpu_h": {"smoke": 0.2, "probe": 0.7, "sum": 0.9, "threshold": 8.0,
                                  "estimate_central": 0.263, "estimate_high": 0.628},
        "supplementary_cpu_evidence": [
            {"label": "E: the registered v2 estimator as code", "script": art(f"{R}/e3_estimator_v2.py")},
            {"label": "S1v2 simulation driver (imports the estimator unchanged)", "script": art(f"{R}/instrument_sim_v2.py"),
             "merge_script": art(f"{R}/merge_v2.py")},
            {"label": "S1v2 error-model calibration (seed 2042)", "output": art(f"{R}/calib.json")},
            {"label": "S1v2 attenuation map, per-aligner targets (seed 42)", "output": art(f"{R}/atten-single-aligner.json")},
            {"label": "S1v2 attenuation map, consensus target (seed 42)", "output": art(f"{R}/atten-consensus.json")},
            {"label": "design exploration of two-aligner targets (not decision-bearing)", "script": art(f"{R}/explore_targets.py"),
             "output": art(f"{R}/explore-targets.json")},
            {"label": "band-path constants", "script": art(f"{R}/band_envelope.py"), "output": art(f"{R}/band-registered.json"),
             "provisional_in_run_constants": art(f"{R}/band.json")},
            {"label": "S1v2 gates and budget diagnostics (seeds 42-44)", "output": art(f"{R}/gates-v2.json")},
            {"label": "S1v2 wave-1 density and word-end scenario under v2 (seeds 42-44)", "output": art(f"{R}/ident-v2.json")},
            {"label": "S1v2 synthetic line M reference (seeds 42-44)", "output": art(f"{R}/linem-v2.json")},
            {"label": "superseded diagnostics (before the consensus target)", "outputs": [art(f"{R}/superseded/{n}") for n in
              ("gates-per-aligner-budget.json", "ident-per-aligner-budget.json", "linem-per-aligner-budget.json")]},
            {"label": "S1v2 operating characteristics: per-replicate statistics (24 condition-seed runs)", "output": art(f"{R}/oc-merged.json")},
            {"label": "S1v2 verdicts under the registered rule", "script": art(f"{R}/oc_decide.py"), "output": art(f"{R}/oc-decisions.json")},
            {"label": "S1v2 OC summary tables", "script": art(f"{R}/oc_summary.py"), "output": art(f"{R}/oc-summary.json"),
             "markdown": art(f"{R}/oc-summary.md")},
            {"label": "S2v2 GPU-hour arithmetic and caps", "script": art(f"{R}/cost_model_v2.py"), "output": art(f"{R}/cost-model-v2.json")},
            {"label": "run-2 query log builder", "script": art(f"{R}/build_query_log_run2.py")},
            {"label": "run-2 snapshot script (new URLs only)", "script": art(f"{R}/snapshot_new_sources.py")},
            {"label": "wave-1 S1 instrument simulation (kept unedited)", "script": art("compute/instrument_sim.py"),
             "output": art("compute/instrument-sim.json")},
            {"label": "wave-1 S2 cost model (kept unedited)", "script": art("compute/cost_model.py"), "output": art("compute/cost-model.json")},
            {"label": "snapshot script for source_snapshots", "script": art("compute/snapshot_sources.py")},
        ],
        "repro_check": art(f"{R}/repro-check.json") if (BUNDLE / R / "repro-check.json").is_file() else None,
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
                      "declared_budget": 80, "reserved_for_refuters": 30, "wave1_query_log": art("query-log.json"),
                      "note": "This run's counted queries so far (the repair's 20); wave 1's are in query-log.json and the wave-1 record."},
        "reviews": [],
        "reviews_status": "NOT_RUN for this run: the blind critic, the refute-first triad and both reviewers run after the repair. Wave 1's reviews are in program/gauntlet/2026-10-10-e3-byte-boundary-headroom.jsonl. No trusted Ed25519 store exists (D24).",
        "compute": compute,
        "doctors": doctors,
        "audit_log": None,
        "audit_log_status": "Wave 1's row is the first row of program/gauntlet/2026-10-10-e3-byte-boundary-headroom.jsonl (hash 13d97526...); this run's row is appended after its reviewers score.",
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
        "wave1_packets": {"proposal": "blind/paragraph-8110cb24.txt", "closest_prior": "blind/paragraph-a0d3d6e0.txt",
                          "role_map": "compute/blind-roles.json"},
        "note": "File names carry no role and each file holds only its paragraph. One critic call per prior packet, each with the proposal paragraph, in randomized order, read by path, without the role map or any other text.",
    }
    bundle["budget_ledger"] = {
        "declared": {"queries": 80, "wall_minutes": 600, "tokens": 8000000, "dollars": 150, "waves": 1, "gpu_hours": 0.3},
        "used_by_repair": {"queries": qlog["counted_by_repair_owner"], "paper_reads": len(qlog["paper_reads_not_counted"]),
                           "gpu_hours": 0.0, "host": "none (no ssh, no host job)",
                           "cpu": "S1v2 and S2v2 on the development Mac (about 80 process runs kept, plus superseded runs listed in README)",
                           "wall_minutes_and_tokens": "metered by the recorder from transcripts"},
        "remaining_queries": 80 - qlog["counted_by_repair_owner"],
    }
    out = BUNDLE / "doctors/research-direction-doctor-output.json"
    if out.is_file():
        bundle["direction_doctor_run"] = {
            **art("doctors/research-direction-doctor-output.json"),
            "command": "uv run python scripts/research_direction_doctor.py program/proposals/2026-10-10-e3-byte-boundary-headroom.md",
            "note": "Outside evidence_root by design: the doctor output depends on this bundle."}
    (BUNDLE / "bundle.json").write_text(json.dumps(bundle, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(bundle["proposal_sha256"], bundle["evidence_root_sha256"], len(snapshots))


if __name__ == "__main__":
    main()
