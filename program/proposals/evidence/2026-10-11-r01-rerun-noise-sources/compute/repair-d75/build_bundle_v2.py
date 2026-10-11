#!/usr/bin/env python3
"""Assemble bundle.json for R01's fresh gauntlet run under D75 (the repaired candidate).

Hashes every artifact, computes evidence_root_sha256 exactly as scripts/research_direction_doctor.py
does (over source_snapshots, query_log, compute, doctors, audit_log), and records the proposal and
draft-registration (v2) hashes. Wave 1's builder (``../build_bundle.py``) is kept unchanged.

Usage (worktree root): python3 program/proposals/evidence/2026-10-11-r01-rerun-noise-sources/compute/repair-d75/build_bundle_v2.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
BUNDLE = ROOT / "program/proposals/evidence/2026-10-11-r01-rerun-noise-sources"
PROPOSAL = ROOT / "program/proposals/2026-10-11-r01-rerun-noise-sources.md"
REGISTRATION = ROOT / "program/preregistrations/r01-rerun-noise-sources-v2.md"
REGISTRATION_V1 = ROOT / "program/preregistrations/r01-rerun-noise-sources-v1.md"
R = "compute/repair-d75"
CODE = [
    "harness/r01/__init__.py",
    "harness/r01/regions.py",
    "harness/r01/requests.py",
    "harness/r01/replay.py",
    "harness/r01/p0.py",
    "harness/r01/openloop.py",
    "harness/r01/fake_engine.py",
    "harness/r01/caps.py",
    "harness/r01/estimators.py",
    "harness/r01/stepkick.py",
    "harness/r01/SKILL.md",
]
TESTS = [
    "tests/test_r01_regions_requests.py",
    "tests/test_r01_replay_p0.py",
    "tests/test_r01_openloop.py",
    "tests/test_r01_estimators_stepkick_caps.py",
    "tests/test_r01_stage_a0_doctor.py",
]


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
                "HTTP 200 browser-challenge page; verifies nothing about content; abstract from the "
                "OpenReview api2 search (wave 1's query-log.json)"
            )
        snapshots.append(entry)
    q2 = json.loads((BUNDLE / "query-log-run2.json").read_text(encoding="utf-8"))
    caps = json.loads((BUNDLE / f"{R}/caps-r01-v2.json").read_text())
    not_run = "compute/attestations-not-run.md"
    compute = {
        "scope": (
            "r01-rerun-noise-sources-v2 is a DRAFT. Stage A0 ran as an orx cpu-doctor node. P0, the request-replay "
            "driver, the open-loop driver, the rebuilder, the estimator and the two-stage model are built and tested on "
            "CPU against fakes; no lane adapter, manifest or host attestation exists (compute/attestations-not-run.md)."
        ),
        "image_digest": "docker.io/vllm/vllm-openai@sha256:b18abb2df97b8f798e81862bd93f872ea18613372e2c3adc0cc2ac21e66ac12f",
        "image_scope": (
            "engine base image (vLLM v0.31.0, commit db9527a4); S1a's cu129 overlay, local image ID "
            "sha256:10327c706dcf2a9bd06e2449908e37d4fa4e46e7030a85e66f30626a1bafecde (source 4a59e87c), is reused"
        ),
        "real_model_loop": False,
        "real_model_loop_scope": (
            "S1a's agent loop exists (harness/q2_stage1); R01's replay client and open-loop runner exist "
            "and pass CPU tests against harness/r01/fake_engine.py and S1a's fake guest, but have not run "
            "against a real engine or VM"
        ),
        "benchmark_adapter": None,
        "manifest": None,
        "manifest_scope": "no Stage B or CPU-lane manifest is rendered; the R01 lane adapter is not built",
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
        "executable_pilot": {
            "stage": "A0, records-only census of S1a (CPU, model-free)",
            "orx_node": "ff110047-8f18-4b5b-b85d-fd73fa767d35",
            "orx_branch": "orx/r01-stage-a0-records-census",
            "orx_commit": "ca3cdbf09db81be978145ee5d05151d9b6973fc8",
            "orx_run_id": "83ee815a-426a-4b94-a93f-cc1277972d76",
            "backend": "local",
            "run_command": "uv run --locked python scripts/orx_run.py",
            "orx_result": "ORX_RESULT kind=cpu-doctor direction=r01-rerun-noise-sources exit=0",
            "log": art("compute/pilot/orx-run-83ee815a-426a-4b94-a93f-cc1277972d76.log"),
            "receipt_sha256": "5568bc7f9d7c87f64a6f5a91bc845dd514e6b78f17a5d55cf231f099e269e4b7",
            "receipt_matches_committed_census": True,
        },
        "cpu_tested_code": {
            "modules": [repo(p) for p in CODE],
            "tests": [repo(p) for p in TESTS],
            "command": "uv run --locked --extra dev pytest -q tests/test_r01_*.py",
            "result_file": art(f"{R}/pytest-r01.txt"),
        },
        "registered_caps_gpu_h": {
            "total_with_conditional": caps["total_cap_gpu_h"],
            "total_without_conditional": caps["total_cap_gpu_h_without_conditional"],
            "physical_central": caps["physical_gpu_h_central"],
            "d22_line": 8.0,
            "admission": "Kevin's ruling (D24, D70)",
        },
        "supplementary_cpu_evidence": [
            {
                "label": "operating characteristics of every v2 decision rule under the registered estimator, and the two-stage model (seeds 42-44)",
                "script": art(f"{R}/power_r01_v2.py"),
                "output": art(f"{R}/power-r01-v2.json"),
            },
            {
                "label": "caps repriced from S1a's realized step costs; loaded passes simulated as the slowest of 20 lanes",
                "script": art(f"{R}/caps_r01_v2.py"),
                "output": art(f"{R}/caps-r01-v2.json"),
            },
            {
                "label": "this run's query log builder",
                "script": art(f"{R}/build_query_log_run2.py"),
            },
            {
                "label": "snapshots of newly cited sources",
                "script": art(f"{R}/snapshot_new_sources.py"),
            },
            {"label": "doctor-record writer (v2)", "script": art(f"{R}/write_doctors_v2.py")},
            {
                "label": "wave-1 simulation and caps (kept; v1 design)",
                "script": art("compute/power_r01.py"),
                "output": art("compute/power-r01.json"),
            },
        ],
        "repository_evidence_used": {
            "s1a_records": repo("program/evidence/2026-10-10/q2-stage1-analysis/a1.jsonl"),
            "s1a_step_digests": repo(
                "program/evidence/2026-10-11/r01-stage-a0/s1a-step-digests.jsonl.gz"
            ),
            "engine_log_mamba_mode": repo(
                "program/evidence/2026-10-07/serving-throughput-probe-v1/jobs/a-442/probe/engines/real/engine.log"
            ),
            "s1a_results": "program/evidence/2026-10-10/q2-stage1-a1/RESULTS.md",
        },
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
            "experiment_id": "r01-rerun-noise-sources-v2",
            "status": "DRAFT, not frozen, no ledger row",
            "supersedes": {
                "path": str(REGISTRATION_V1.relative_to(ROOT)),
                "sha256": sha(REGISTRATION_V1),
                "status": "superseded, left unedited",
            },
        },
        "source_snapshots": snapshots,
        "query_log": {
            **art("query-log-run2.json"),
            "queries_against_budget": {
                "declared": q2["declared_queries"],
                "reserve": q2["refuter_reserve"],
                "used_by_repair": q2["counted"]["total"],
                "remaining": q2["remaining_after_repair"],
                "reserve_intact": q2["reserve_intact"],
            },
        },
        "query_log_wave1": art("query-log.json"),
        "reviews": [],
        "reviews_status": (
            "NOT_RUN in this run: the blind critic, the refute-first triad and both reviewers run after the repair. "
            "No trusted Ed25519 store exists (D24)."
        ),
        "compute": compute,
        "doctors": doctors,
        "audit_log": None,
        "audit_log_status": (
            "Wave 1's row is in program/gauntlet/2026-10-11-r01-rerun-noise-sources.jsonl (hash 22639b76...); "
            "this run's row is appended after its reviewers score."
        ),
    }
    payload = {
        key: bundle.get(key)
        for key in ("source_snapshots", "query_log", "compute", "doctors", "audit_log")
    }
    bundle["evidence_root_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    roles = json.loads((BUNDLE / f"{R}/blind-roles-run2.json").read_text())
    blind = {}
    for key in ("proposal", "closest_prior", "second_prior"):
        path = BUNDLE / "blind" / roles[key]
        blind[key] = art(
            f"blind/{roles[key]}",
            text_sha256=hashlib.sha256(path.read_text().rstrip("\n").encode()).hexdigest(),
        )
    bundle["blind_discrimination_packet"] = {
        **blind,
        "closest_prior_id": roles["closest_prior_id"],
        "second_prior_id": roles["second_prior_id"],
        "roles": art(f"{R}/blind-roles-run2.json"),
        "note": "File names carry no role. One critic call per prior, the two texts in randomized order, without the roles file.",
    }
    bundle["budget_ledger"] = {
        "declared": {
            "queries": 80,
            "wall_minutes": 600,
            "tokens": 8000000,
            "dollars": 150,
            "waves": 1,
            "gpu_hours": 0.3,
        },
        "used_by_repair": {
            "counted_queries": q2["counted"]["total"],
            "reads_not_counted": len(q2["reads_not_counted"]),
            "fetch_attempts_not_counted": len(q2["fetch_attempts_not_counted"]),
            "gpu_hours": 0.0,
            "host": "read-only ssh: squeue checks and one curl fetch attempt through the relay; no host job",
            "tokens_and_dollars": "metered by the recorder from transcripts",
        },
        "remaining_queries": q2["remaining_after_repair"],
    }
    out = BUNDLE / "doctors/research-direction-doctor-output.json"
    if out.is_file():
        bundle["direction_doctor_run"] = {
            **art("doctors/research-direction-doctor-output.json"),
            "command": "uv run --locked python scripts/research_direction_doctor.py program/proposals/2026-10-11-r01-rerun-noise-sources.md",
            "note": "Outside evidence_root by design: the doctor output depends on this bundle.",
        }
    (BUNDLE / "bundle.json").write_text(
        json.dumps(bundle, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(bundle["proposal_sha256"], bundle["evidence_root_sha256"], len(snapshots))


if __name__ == "__main__":
    main()
