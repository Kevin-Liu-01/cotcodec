#!/usr/bin/env python3
"""Assemble bundle.json for the E5 first-step gauntlet from the files in this bundle.

Adapted from the C3 bundle's builder. Hashes every artifact, computes
evidence_root_sha256 exactly as scripts/research_direction_doctor.py does (over
source_snapshots, query_log, compute, doctors, audit_log), and records the
proposal and draft-registration hashes. Run from the worktree root after any
change to the proposal or an artifact:

    python3 program/proposals/evidence/2026-10-10-e5-gate-fertility-decomposition/compute/build-bundle.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
BUNDLE = ROOT / "program/proposals/evidence/2026-10-10-e5-gate-fertility-decomposition"
PROPOSAL = ROOT / "program/proposals/2026-10-10-e5-gate-fertility-decomposition.md"
REGISTRATION = ROOT / "program/preregistrations/e5-gate-fertility-decomposition-v1.md"
SLUG = "2026-10-10-e5-gate-fertility-decomposition"


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
    qlog = json.loads((BUNDLE / "query-log.json").read_text(encoding="utf-8"))
    not_run = "compute/attestations-not-run.md"
    compute = {
        "scope": "e5-gate-fertility-decomposition-v1 is a DRAFT; no compute attestation of its own exists (compute/attestations-not-run.md). Supplementary CPU evidence: S1 identification simulation, S2 operating characteristics, S3 cost model, S4 splitting rules on the real tokenizers, and the registered estimator as code.",
        "image_digest": "127.0.0.1:5000/cotcodec-research@sha256:13a9de831cff50461d8ecee3c2794f0c6d6bcffe9d602968fe2ee06e5a1096e9",
        "image_scope": "build 855 from commit ed5d5a93 (image ID sha256:500f3b027173a2d772b7d6ea00ea667dbe1bc956df51e3c2c4455d9c08a2714b; fla and fla-core 0.5.2, torch 2.11.0, transformers 5.15.0); neither subject has been loaded in it on this host",
        "real_model_loop": False,
        "real_model_loop_scope": "none: the harness (model loop, hooks, forced-choice scorer, ledgers, checkpoint and resume) is not written",
        "benchmark_adapter": None,
        "benchmark_adapter_scope": "none: the episode builder is not written; the splitting rules exist only as the CPU prototype compute/resegment.py",
        "manifest": None,
        "manifest_scope": "no Slurm manifest exists for the smoke or the two main jobs",
        "container_smoke": {"label": "container_smoke", "status": "NOT_RUN", "return_code": None, **art(not_run)},
        "slurm_test": {"label": "slurm_test", "status": "NOT_RUN", "return_code": None, **art(not_run)},
        "provenance_verification": {"label": "provenance_verification", "status": "NOT_RUN", "return_code": None, **art(not_run)},
        "registered_caps_gpu_h": {"smoke": 0.25, "gdn_main": 1.25, "rwkv_main": 2.5, "sum": 4.0, "d22_limit": 8.0},
        "estimate_gpu_h": {"central": 1.257, "high": 3.291},
        "supplementary_cpu_evidence": [
            {"label": "registered estimator and decision rules as code", "script": art("compute/estimator.py")},
            {"label": "S1 identification: per-token decay clamp against the uniform r = 2 rescale on a NumPy gated delta-rule memory, six worlds, seeds 42/43/44 x 600 episodes per load",
             "script": art("compute/mech-sim.py"), "output": art("compute/mech-sim.json")},
            {"label": "S2 operating characteristics of every threshold (paired, passage-clustered; assumed discordance 0.05 to 0.30; 4,000 replicates per cell; bootstrap coverage check)",
             "script": art("compute/power-sim.py"), "output": art("compute/power-sim.json")},
            {"label": "S3 token counts, GPU-hour estimate, caps and degradation ladder (assumed throughputs; no inference throughput measured on the host)",
             "script": art("compute/cost-model.py"), "output": art("compute/cost-model.json")},
            {"label": "S4 splitting rules R(f, seed) and B(seed) on the real m-a-p and RWKV World tokenizers (CC0 arXiv abstracts as stand-in text)",
             "script": art("compute/resegment.py"), "output": art("compute/resegment.json")},
            {"label": "query-log builder (parses the cells' raw orx outputs from the session scratchpad)", "script": art("compute/build-query-log.py")},
            {"label": "doctor-record builder (claim registry parsed from the proposal)", "script": art("compute/build-doctors.py")},
            {"label": "snapshot script for source_snapshots", "script": art("compute/snapshot-sources.py")},
        ],
        "tokenizer_inputs": {
            "m-a-p tokenizer.json": {"sha256": "1d5b9634c23bdd4540f633d327120e1fa4b57a2a723a56d7a92debfc4d15c061", "git_blob_sha1": "b667161bc937dfaed6f27e9e7849a664c3e869b3", "hf_tree_oid": "b667161bc937dfaed6f27e9e7849a664c3e869b3"},
            "rwkv_vocab_v20230424.txt": {"sha256": "e6dee3d4e31b4d5c40ac99508ac6c701ceef4bed681bf2167ce9a908552bca89"},
            "location": "session scratchpad (fetched by the frontier cell); not committed",
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
                               "status": "DRAFT, not frozen, no ledger row"},
        "source_snapshots": snapshots,
        "query_log": {**art("query-log.json"), "queries_against_budget": qlog["queries_against_budget"],
                      "note": "120 counted orx discover queries (frontier 47, kill-shot 24, cross-domain 43, asset 6, synthesis 0) against the declared 150; exactly the triad's reserve of 30 remains; uncounted OpenReview, web and Anthology searches and 57 cell paper reads logged separately."},
        "reviews": [],
        "reviews_status": "NOT_RUN: the blind critic, the refute-first triad and both reviewers run after synthesis. No trusted Ed25519 store exists (D24), so no review can be signed.",
        "compute": compute,
        "doctors": doctors,
        "audit_log": None,
        "audit_log_status": f"This gauntlet's wave-1 row is appended to program/gauntlet/{SLUG}.jsonl with scripts/research_gauntlet_record.py after its reviewers score.",
    }
    payload = {key: bundle.get(key) for key in ("source_snapshots", "query_log", "compute", "doctors", "audit_log")}
    bundle["evidence_root_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    blind = {}
    for path in sorted((BUNDLE / "blind").glob("paragraph-*.txt")):
        blind[path.name] = art(f"blind/{path.name}", text_sha256=hashlib.sha256(
            path.read_text(encoding="utf-8").rstrip("\n").encode()).hexdigest())
    roles = json.loads((BUNDLE / "compute/blind-roles.json").read_text(encoding="utf-8"))
    bundle["blind_discrimination_packet"] = {
        "proposal": blind[roles["proposal"]],
        "closest_prior": blind[roles["closest_prior"]],
        "closest_prior_id": roles["closest_prior_id"],
        "note": "File names carry no role and each file holds only its paragraph. The critic receives the two texts in randomized order, read by path, without this mapping or any other text.",
    }
    bundle["budget_ledger"] = {
        "declared": {"queries": 150, "wall_minutes": 600, "tokens": 8000000, "dollars": 150, "waves": 3, "gpu_hours": 0.3},
        "used_by_discovery_cells": {"queries": 120, "uncounted_searches": 18, "paper_reads": 57, "gpu_hours": 0.0,
                                    "host": "read-only ssh by the kill-shot and asset cells (squeue empty; cached cards, receipts, tokenizer files); no host job"},
        "used_by_synthesis": {"queries": 0, "paper_reads": "re-reads of cell-fetched full texts (2609.33093, 2609.16183, 2507.06457, 2506.19004, 2609.14320, 2410.07145, MambaExtend); 32 arXiv and Hugging Face snapshot fetches (auxiliary)",
                              "gpu_hours": 0.0, "host": "one read-only squeue at 21:41 UTC (empty); no host job",
                              "cpu": "S1 (612 s), S2 (79 s), S3 and S4 (159 s wall) on the development Mac",
                              "tokens_and_dollars": "not metered by the synthesis agent; the recorder meters from transcripts"},
        "remaining_queries": 30,
        "refuter_reserve_shortfall": 0,
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
