#!/usr/bin/env python3
"""Assemble bundle.json for the S2 v3 repair run after wave 1 (D74).

Hashes every artifact and computes evidence_root_sha256 as scripts/research_direction_doctor.py does
(over source_snapshots, query_log, compute, doctors, audit_log). The wave-1 builder (build-bundle.py)
and its doctor records (doctors/) are left as they were; this run's doctors are doctors-r1/.

    python3 program/proposals/evidence/2026-10-11-s2v3-arabic-cua-locale-pilot/compute/build-bundle-r1.py
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
BUNDLE = ROOT / "program/proposals/evidence/2026-10-11-s2v3-arabic-cua-locale-pilot"
PROPOSAL = ROOT / "program/proposals/2026-10-11-s2v3-arabic-cua-locale-pilot.md"
REGISTRATION = ROOT / "program/preregistrations/s2-arabic-cua-locale-v3.1.md"
REG_V3 = ROOT / "program/preregistrations/s2-arabic-cua-locale-v3.md"
SBATCH = ROOT / "infra/slurm/host-single-node/s2v3-pilot-cpu.sbatch"
P1 = "compute/pilot-r1"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def art(rel: str, **extra) -> dict:
    return {"artifact": rel, "sha256": sha(BUNDLE / rel), **extra}


def files(sub: str, suffix: str | None = None) -> list[dict]:
    return [art(str(p.relative_to(BUNDLE))) for p in sorted((BUNDLE / sub).rglob("*"))
            if p.is_file() and (suffix is None or p.name.endswith(suffix))]


def code(rel: str) -> dict:
    p = ROOT / rel
    return {"path": rel, "sha256": sha(p)}


def main() -> None:
    snapshots = []
    for path in sorted((BUNDLE / "snapshots").glob("*.json")):
        rec = json.loads(path.read_text(encoding="utf-8"))
        snapshots.append({"url": rec["url"], "http_status": rec["http_status"], "fetched_at": rec["fetched_at"],
                          "raw_sha256": rec["raw_sha256"], "raw_bytes": rec["raw_bytes"], **art(f"snapshots/{path.name}")})
    rq = json.loads((BUNDLE / P1 / "queries/repair-queries.json").read_text())
    oracle = json.loads((BUNDLE / P1 / "oracle-1132/oracle-receipt.json").read_text())
    orx_receipt = BUNDLE / P1 / "orx-node/receipt.json"
    power = json.loads((BUNDLE / "compute/power-v4/power-v4.json").read_text())
    compute = {
        "scope": ("s2-arabic-cua-locale-v3.1 is a DRAFT. Phase 0 ran in the CPU lane on the certified VM's own LibreOffice userland "
                  "(container) with generated stand-in catalogs: capture 1131, oracle (orx node and Slurm 1132), checker invariance "
                  "(1139, 1141). The derived image, the VM-lane Phase 0, the delta certification (K1) and Phase 1 did not run."),
        "image_digest": "docker.io/vllm/vllm-openai@sha256:b18abb2df97b8f798e81862bd93f872ea18613372e2c3adc0cc2ac21e66ac12f",
        "image_scope": "Phase 1 engine base image (as S1a). Phase 0 images: pilot_images.",
        "pilot_images": {"lo_vm": "sha256:f5b4c40eefd2b92f846652910ba34db35e1ae7bf90fa474595cc745cc5895361",
                         "metric": "sha256:2006c1a9247e4911a82508cd22e9d9a7efc5c13e35a20e8a03baac7112876230",
                         "research_cpu_only": "sha256:500f3b027173a2d772b7d6ea00ea667dbe1bc956df51e3c2c4455d9c08a2714b"},
        "real_model_loop": False,
        "real_model_loop_scope": "S1a's loop ran 1,808 episodes (D66); no S2 episode has run",
        "benchmark_adapter": None,
        "manifest": None,
        "manifest_scope": "no Phase 1 Slurm manifest exists",
        "container_smoke": {"label": "container_smoke", "status": "PASS", "return_code": 0,
                            "scope": "Phase 0 capture container (job 1131); not the Phase 1 engine image",
                            **art(f"{P1}/capture-1131/receipt-1131.json")},
        "slurm_test": {"label": "slurm_test", "status": "NOT_RUN", "return_code": None,
                       "scope": "no Phase 1 dry run or test-only", **art(f"{P1}/receipts/run-1131.json")},
        "provenance_verification": {"label": "provenance_verification", "status": "NOT_RUN", "return_code": None,
                                    **art(f"{P1}/receipts/run-1131.json")},
        "orx_node": ({**art(f"{P1}/orx-node/receipt.json"), "log": art(f"{P1}/orx-node/orx-run.log"),
                      "node_yaml": art(f"{P1}/orx-node/node.yaml")} if orx_receipt.exists() else None),
        "phase0_pilot": {
            "sbatch": {"path": str(SBATCH.relative_to(ROOT)), "sha256": sha(SBATCH)},
            "code": [code(p) for p in ("harness/s2_locale/capture.py", "harness/s2_locale/catalog.py",
                                       "harness/s2_locale/oracle.py", "harness/s2_locale/phase0.py",
                                       "harness/s2_locale/goldsave.py", "harness/s2_locale/score_gold.py",
                                       "harness/s2_locale/summarize.py", "harness/q2_mutation/reachability.py",
                                       "scripts/run_s2v3_phase0_doctor.py")],
            "capture": files(f"{P1}/capture-1131"),
            "oracle_replicate_1132": files(f"{P1}/oracle-1132"),
            "checker_invariance": files(f"{P1}/gold-1139") + files(f"{P1}/goldscore-1141"),
            "admitted_checker_invariance": art(f"{P1}/admitted-checker-invariance.json"),
            "summary": art(f"{P1}/oracle-summary.json"),
            "receipts": files(f"{P1}/receipts"),
            "slurm_logs": files(f"{P1}/slurm"),
            "k0_committed_rules": oracle["k0"], "admitted_committed_rules": oracle["admitted"],
            "gpu_hours": 0.0,
        },
        "wave1_pilot": {"receipts": [art(f"compute/pilot/job{j}/run-{j}.json") for j in (1097, 1098, 1099, 1100)]},
        "registered_caps_gpu_h": {"K106_n4_npl2": power["costs"]["K106_n4_npl2"], "K62_n4_npl2": power["costs"]["K62_n4_npl2"],
                                  "registered_total_gpu_h": 6.83, "at_p95_slot_gpu_h": 7.70},
        "supplementary_cpu_evidence": [
            {"label": "power-v4: registered rules re-run (corrected sharp null, placebo, direction-specific reading)",
             "script": art("compute/power-v4/power-v4.py"), "output": art("compute/power-v4/power-v4.json"),
             "log": art("compute/power-v4/power-v4.log"), "tables": [art("compute/power-v4/tables-v4.py"), art("compute/power-v4/tables-v4.md")]},
            {"label": "pool (wave 1, unchanged)", "script": art("compute/pool/pool-v3.py"), "output": art("compute/pool/pool-v3.json")},
            {"label": "builders", "files": [art("compute/build-doctors-r1.py"), art("compute/build-bundle-r1.py")]},
        ],
    }
    doctors = [{"name": n.capitalize(), "status": json.loads((BUNDLE / f"doctors-r1/{n}.json").read_text())["status"],
                **art(f"doctors-r1/{n}.json")} for n in ("source", "citation", "novelty", "design", "compute", "safety")]
    bundle = {
        "schema_version": 1,
        "proposal": str(PROPOSAL.relative_to(ROOT)),
        "proposal_sha256": sha(PROPOSAL),
        "draft_registration": {"path": str(REGISTRATION.relative_to(ROOT)), "sha256": sha(REGISTRATION),
                               "experiment_id": "s2-arabic-cua-locale-v3.1", "status": "DRAFT, not frozen, no ledger row",
                               "predecessor": {"path": str(REG_V3.relative_to(ROOT)), "sha256": sha(REG_V3),
                                               "experiment_id": "s2-arabic-cua-locale-v3", "note": "left unedited (wave-1 draft)"}},
        "source_snapshots": snapshots,
        "query_log": {**art(f"{P1}/queries/repair-queries.json"), "counted": rq["counted_queries"], "declared": 80,
                      "reserved_for_refuters": 30, "wave1_log": art("query-log.json")},
        "reviews": [],
        "reviews_status": "NOT_RUN: this run's blind critic, refute-first triad and reviewers run after the repair. No trusted Ed25519 store exists (D24).",
        "compute": compute,
        "doctors": doctors,
        "audit_log": None,
        "audit_log_status": "program/gauntlet/2026-10-11-s2v3-arabic-cua-locale-pilot.jsonl holds wave 1 (hash 8b0c6ef5...); this run's row is appended by the recorder after its reviewers score.",
    }
    payload = {key: bundle.get(key) for key in ("source_snapshots", "query_log", "compute", "doctors", "audit_log")}
    bundle["evidence_root_sha256"] = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    roles = json.loads((BUNDLE / "compute/blind-roles-r1.json").read_text())
    blind = {p.name: art(f"blind/{p.name}", text_sha256=hashlib.sha256(p.read_text().rstrip("\n").encode()).hexdigest())
             for p in sorted((BUNDLE / "blind").glob("paragraph-*.txt"))}
    bundle["blind_discrimination_packet"] = {"proposal": blind[roles["proposal"]], "closest_prior": blind[roles["closest_prior"]],
                                             "closest_prior_id": roles["closest_prior_id"],
                                             "note": "Fresh paragraphs for this run; file names carry no role; compute/blind-roles-r1.json is for the recorder only."}
    bundle["budget_ledger"] = {"declared": {"queries": 80, "wall_minutes": 600, "tokens": 8000000, "dollars": 150, "waves": 1, "gpu_hours": 0.3},
                               "queries_used_by_repair": rq["counted_queries"], "gpu_hours_used": 0.0,
                               "host_jobs": "CPU-only Slurm 1116, 1120, 1123, 1124, 1129 (cancelled), 1131, 1132, 1139, 1140 (failed), 1141, 1142; no GPU job"}
    out = BUNDLE / "doctors-r1/research-direction-doctor-output.json"
    if out.exists():
        bundle["research_direction_doctor_output"] = {**art("doctors-r1/research-direction-doctor-output.json"),
                                                      "note": "verbatim stdout of the doctor on this bundle; not part of the evidence root"}
    (BUNDLE / "bundle.json").write_text(json.dumps(bundle, indent=1, ensure_ascii=False) + "\n")
    print("proposal", bundle["proposal_sha256"][:12], "root", bundle["evidence_root_sha256"][:12])


if __name__ == "__main__":
    main()
