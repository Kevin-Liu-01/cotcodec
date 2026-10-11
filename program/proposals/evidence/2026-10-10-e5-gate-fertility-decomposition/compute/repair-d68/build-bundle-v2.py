#!/usr/bin/env python3
"""Assemble bundle.json for the E5 fresh gauntlet run after the D68 repair.

Same contract as wave 1's `compute/build-bundle.py` (kept unedited): hashes every artifact,
computes evidence_root_sha256 exactly as scripts/research_direction_doctor.py does (over
source_snapshots, query_log, compute, doctors, audit_log), and records the proposal and
draft-registration hashes. Differences: the draft registration is v2 (v1 recorded as
superseded), the query log is this run's (`query-log-run2.json`; wave 1's `query-log.json`
referenced by hash), the repair's CPU evidence is listed, and the blind packets follow
`compute/repair-d68/blind-roles-run2.json`. Run from the worktree root after any change:

    python3 program/proposals/evidence/2026-10-10-e5-gate-fertility-decomposition/compute/repair-d68/build-bundle-v2.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
BUNDLE = ROOT / "program/proposals/evidence/2026-10-10-e5-gate-fertility-decomposition"
PROPOSAL = ROOT / "program/proposals/2026-10-10-e5-gate-fertility-decomposition.md"
REGISTRATION = ROOT / "program/preregistrations/e5-gate-fertility-decomposition-v2.md"
REGISTRATION_V1 = ROOT / "program/preregistrations/e5-gate-fertility-decomposition-v1.md"
SLUG = "2026-10-10-e5-gate-fertility-decomposition"
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
                          "raw_sha256": rec["raw_sha256"], "raw_bytes": rec["raw_bytes"],
                          **art(f"snapshots/{path.name}")})
    qlog = json.loads((BUNDLE / "query-log-run2.json").read_text(encoding="utf-8"))
    not_run = "compute/attestations-not-run.md"
    compute = {
        "scope": "e5-gate-fertility-decomposition-v2 is a DRAFT; no compute attestation of its own exists (compute/attestations-not-run.md). Supplementary CPU evidence: the D68 repair's registered estimator as code, S1v2 (identification in a two-layer toy through the registered path), S2v2 (the whole decision path's operating characteristics through the registered estimator), S3v2 (cost per branch), and wave 1's S1-S4 (kept unedited).",
        "image_digest": "127.0.0.1:5000/cotcodec-research@sha256:13a9de831cff50461d8ecee3c2794f0c6d6bcffe9d602968fe2ee06e5a1096e9",
        "image_scope": "build 855 from commit ed5d5a93 (image ID sha256:500f3b027173a2d772b7d6ea00ea667dbe1bc956df51e3c2c4455d9c08a2714b; fla and fla-core 0.5.2, torch 2.11.0, transformers 5.15.0); neither subject has been loaded in it on this host",
        "real_model_loop": False,
        "real_model_loop_scope": "none: the harness (model loop, clamp, transplant, CLAMP-LAST, DOSE, r = 2 and silencing hooks, forced-choice scorer, ledgers, checkpoint and resume) is not written",
        "benchmark_adapter": None,
        "benchmark_adapter_scope": "none: the episode builder is not written; the splitting rules exist only as the CPU prototype compute/resegment.py",
        "manifest": None,
        "manifest_scope": "no Slurm manifest exists for the smoke or the two main jobs",
        "container_smoke": {"label": "container_smoke", "status": "NOT_RUN", "return_code": None, **art(not_run)},
        "slurm_test": {"label": "slurm_test", "status": "NOT_RUN", "return_code": None, **art(not_run)},
        "provenance_verification": {"label": "provenance_verification", "status": "NOT_RUN", "return_code": None, **art(not_run)},
        "registered_caps_gpu_h": {"smoke": 0.75, "gdn_main": 1.75, "rwkv_main": 3.75, "sum": 6.25, "d22_limit": 8.0},
        "supplementary_cpu_evidence": [
            {"label": "v2 registered estimator, operating-point rule and decision rules as code", "script": art(f"{R}/estimator_v2.py")},
            {"label": "S1v2 identification: two-layer gated delta-rule toy with state-dependent writes and decays, presence channel, registered operating-point rule, 2 x 2 factorial plus SIL and DOSE, pool truths and resampled operating characteristics at the registered n, v1 rule's K = 1 dilution",
             "script": art(f"{R}/mech-sim-v2.py"), "output": art(f"{R}/mech-sim-v2.json")},
            {"label": "S2v2 the whole v2 decision path through the registered estimator (held-out selection, four paired arms, article clustering, discordance to about 0.45, every operating-point branch, article heterogeneity, interval coverage against the bootstrap, v1's dilution reproduced with v1's estimator)",
             "script": art(f"{R}/power-sim-v2.py"), "output": art(f"{R}/power-sim-v2.json")},
            {"label": "S2v2 part merger", "script": art(f"{R}/merge-power-v2.py")},
            {"label": "S1v2 per-world merger", "script": art(f"{R}/merge-mech-v2.py")},
            {"label": "S1v2 probe: where the decay-by-write interaction changes sign, and whether that region passes the floors",
             "script": art(f"{R}/int-sign-probe.py"), "output": art(f"{R}/int-sign-probe.json")},
            {"label": "unit checks of estimator_v2 (operating point, readings, overall rule, identity, interval paths)",
             "script": art(f"{R}/estimator-v2-checks.py"), "output": art(f"{R}/estimator-v2-checks.out")},
            {"label": "superseded: S2v2 merged and S1v2 W3, W5 and both W9 attempts under the native floor of 40 that the repair tried first and dropped (kept unedited)",
             "outputs": [art(f"{R}/superseded-floor40/{p.name}") for p in sorted((BUNDLE / R / "superseded-floor40").glob("*.json"))]},
            {"label": "S3v2 tokens, GPU-hours, caps and ladder per (K_p, f_p) branch", "script": art(f"{R}/cost-model-v2.py"), "output": art(f"{R}/cost-model-v2.json")},
            {"label": "run-2 query log builder", "script": art(f"{R}/build-query-log-run2.py")},
            {"label": "run-2 doctor-record builder", "script": art(f"{R}/build-doctors-v2.py")},
            {"label": "wave-1 registered estimator (kept unedited)", "script": art("compute/estimator.py")},
            {"label": "wave-1 S1 (kept unedited)", "script": art("compute/mech-sim.py"), "output": art("compute/mech-sim.json")},
            {"label": "wave-1 S2 (kept unedited)", "script": art("compute/power-sim.py"), "output": art("compute/power-sim.json")},
            {"label": "wave-1 S3 (kept unedited)", "script": art("compute/cost-model.py"), "output": art("compute/cost-model.json")},
            {"label": "S4 splitting rules on the real tokenizers (wave 1; still the reference)", "script": art("compute/resegment.py"), "output": art("compute/resegment.json")},
            {"label": "snapshot script for source_snapshots", "script": art("compute/snapshot-sources.py")},
        ],
        "tokenizer_inputs": {
            "m-a-p tokenizer.json": {"sha256": "1d5b9634c23bdd4540f633d327120e1fa4b57a2a723a56d7a92debfc4d15c061"},
            "rwkv_vocab_v20230424.txt": {"sha256": "e6dee3d4e31b4d5c40ac99508ac6c701ceef4bed681bf2167ce9a908552bca89"},
            "location": "session scratchpad (fetched by the wave-1 frontier cell); not committed",
        },
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
                      "note": "This run's counted queries so far (the repair's); wave 1's are in query-log.json and the wave-1 record."},
        "reviews": [],
        "reviews_status": f"NOT_RUN for this run: the blind critic, the refute-first triad and both reviewers run after the repair. Wave 1's reviews are in program/gauntlet/{SLUG}.jsonl (row 1). No trusted Ed25519 store exists (D24).",
        "compute": compute,
        "doctors": doctors,
        "audit_log": None,
        "audit_log_status": f"Wave 1's row is the first row of program/gauntlet/{SLUG}.jsonl (hash 8b808c0c...); this run's row is appended after its reviewers score.",
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
        "note": "File names carry no role and each file holds only its paragraph. One critic call per prior packet, each with the proposal paragraph, in randomized order, read by path, without the role map or any other text.",
    }
    bundle["budget_ledger"] = {
        "declared": {"queries": 80, "wall_minutes": 600, "tokens": 8000000, "dollars": 150, "waves": 1, "gpu_hours": 0.3},
        "used_by_repair": {"queries": qlog["counted_by_repair_owner"], "failed_not_counted": len(qlog["failed_not_counted"]),
                           "paper_reads": len(qlog["full_text_reads_not_counted"]),
                           "citation_graph_lookups": len(qlog["citation_graph_lookups_not_counted"]),
                           "gpu_hours": 0.0, "host": "none (no ssh, no host job)",
                           "wall_minutes_and_tokens": "metered by the recorder from transcripts"},
        "remaining_queries": 80 - qlog["counted_by_repair_owner"],
    }
    out = BUNDLE / "doctors/research-direction-doctor-output.json"
    if out.is_file():
        bundle["direction_doctor_run"] = {
            **art("doctors/research-direction-doctor-output.json"),
            "command": f"uv run python scripts/research_direction_doctor.py program/proposals/{SLUG}.md",
            "note": "Outside evidence_root by design: the doctor output depends on this bundle."}
    (BUNDLE / "bundle.json").write_text(json.dumps(bundle, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(bundle["proposal_sha256"], bundle["evidence_root_sha256"], len(snapshots))


if __name__ == "__main__":
    main()
