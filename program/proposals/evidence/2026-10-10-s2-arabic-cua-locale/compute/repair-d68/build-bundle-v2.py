#!/usr/bin/env python3
"""Assemble bundle.json for the S2 gauntlet's D68 repair run (wave 1's compute/build-bundle.py is left as it was).

Hashes every artifact, computes evidence_root_sha256 exactly as
scripts/research_direction_doctor.py does (over source_snapshots, query_log,
compute, doctors, audit_log), and records the proposal and draft-registration
hashes. Run from the worktree root after any change to the proposal or an
artifact:

    python3 program/proposals/evidence/2026-10-10-s2-arabic-cua-locale/compute/repair-d68/build-bundle-v2.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
BUNDLE = ROOT / "program/proposals/evidence/2026-10-10-s2-arabic-cua-locale"
PROPOSAL = ROOT / "program/proposals/2026-10-10-s2-arabic-cua-locale.md"
REGISTRATION = ROOT / "program/preregistrations/s2-arabic-cua-locale-v2.md"
REGISTRATION_V1 = ROOT / "program/preregistrations/s2-arabic-cua-locale-v1.md"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def art(rel: str, **extra) -> dict:
    return {"artifact": rel, "sha256": sha(BUNDLE / rel), **extra}


REGISTERED_CAPS = json.loads((Path(__file__).resolve().parent / "registered-caps.json").read_text(encoding="utf-8"))


def main() -> None:
    snapshots = []
    for path in sorted((BUNDLE / "snapshots").glob("*.json")):
        rec = json.loads(path.read_text(encoding="utf-8"))
        entry = {"url": rec["url"], "http_status": rec["http_status"], "fetched_at": rec["fetched_at"],
                 "raw_sha256": rec["raw_sha256"], "raw_bytes": rec["raw_bytes"], **art(f"snapshots/{path.name}")}
        if "openreview.net" in rec["url"]:
            entry["content_note"] = ("HTTP 200 browser-challenge page ('Verifying your browser | OpenReview'); verifies "
                                     "nothing about content; abstract from the OpenReview search API (query-log.json)")
        snapshots.append(entry)
    qlog = json.loads((BUNDLE / "query-log.json").read_text(encoding="utf-8"))
    qb = qlog["queries_against_budget"]
    q2 = json.loads((BUNDLE / "query-log-run2.json").read_text(encoding="utf-8"))
    not_run = "compute/attestations-not-run.md"
    cells = sorted(p.name for p in (BUNDLE / "compute/cells").glob("*") if p.name != "ORIGINAL_SHA256.txt")
    r = "compute/repair-d68"
    oracle_files = sorted(p.name for p in (BUNDLE / r / "render-oracle").glob("*") if p.is_file())
    compute = {
        "scope": ("s2-arabic-cua-locale-v2 is a DRAFT; no compute attestation of its own exists "
                  "(compute/attestations-not-run.md). The D68 repair's CPU evidence is under compute/repair-d68/: the task screen and "
                  "the power analysis under the registered estimator anchored on S1a's records (power-osworld.py/.json; the superseded "
                  "first run power-osworld-v0-partial.json is kept), the render oracle and its validation on Chromium fixtures "
                  "(render-oracle/), and the primary-source lines behind each switch (fetch-mechanism-sources.py, "
                  "mechanism-sources-index.json, snapshots/). Wave 1's Relay evidence (power-gate.py/.json, cells/) is kept as history."),
        "image_digest": "docker.io/vllm/vllm-openai@sha256:b18abb2df97b8f798e81862bd93f872ea18613372e2c3adc0cc2ac21e66ac12f",
        "image_scope": ("engine base image (vLLM v0.31.0, commit db9527a4); the cu129 overlay is rebuilt per source commit by "
                        "scripts/build_vllm_overlay_on_h100.sh, as S1a did; the VM image is S1a's certified OSWorld image, and the derived "
                        "localized image is not built (Phase 0)"),
        "real_model_loop": False,
        "real_model_loop_scope": ("S1a's loop exists and ran 1,808 episodes (D66); no S2 episode has run: the cell selector, step-0 and keyboard "
                                  "checks and the derived image do not exist"),
        "benchmark_adapter": None,
        "benchmark_adapter_scope": "OSWorld b138d348 as S1a ran it; S2 adds no adapter, only the derived image and the selector (Phase 0)",
        "manifest": None,
        "manifest_scope": "no Phase 1 Slurm manifest exists; Phase 0's CPU lane jobs are not written",
        "container_smoke": {"label": "container_smoke", "status": "NOT_RUN", "return_code": None, **art(not_run)},
        "slurm_test": {"label": "slurm_test", "status": "NOT_RUN", "return_code": None, **art(not_run)},
        "provenance_verification": {"label": "provenance_verification", "status": "NOT_RUN", "return_code": None, **art(not_run)},
        "registered_caps_gpu_h": REGISTERED_CAPS,
        "supplementary_cpu_evidence": [
            {"label": "D68 repair: task screen of S1a's pool, beta-binomial propensity model fitted and checked on S1a's cells, simulation of the registered estimator (paired t, sign flip, TOST, rare-break bound) over 4 task sets x 3 n x 17 scenarios, 1,000 replicates per seed x 3 seeds, cost by the Q2 design study's slot rule, exact noncentral-t MDE grid",
             "script": art(f"{r}/power-osworld.py"), "output": art(f"{r}/power-osworld.json")},
            {"label": "D68 repair: first, superseded run (no rare-break bound; n = 4-16 on the LibreOffice strict set only), kept because it showed the t interval under-covering for complete breaks",
             "output": art(f"{r}/power-osworld-v0-partial.json")},
            {"label": "D68 repair: second, superseded run (rare-break bound with a break at D_t <= -0.5), kept because it let unqualified SMALL through in up to 0.087 of replicates at a true -5 pp at K = 43, which is why a large drop is now D_t <= -0.25",
             "output": art(f"{r}/power-osworld-v1-break050.json")},
            {"label": "D68 repair: registered Phase 1 caps by K", "script": art(f"{r}/registered-caps.py"), "output": art(f"{r}/registered-caps.json")},
            {"label": "D68 repair: render oracle (O1-O5 here; O6 is a lane check), Chromium fixture renderer (7 variants plus A/A), validation driver and result",
             "files": [art(f"{r}/render-oracle/{n}") for n in oracle_files]},
            {"label": "D68 repair: primary-source snapshots of the per-application switches (matched line numbers) and their index",
             "script": art(f"{r}/fetch-mechanism-sources.py"), "output": art(f"{r}/mechanism-sources-index.json")},
            {"label": "D68 repair: builder of query-log-run2.json from the session's query runner", "script": art(f"{r}/build-query-log-run2.py")},
            {"label": "D68 repair: this bundle builder (wave 1's compute/build-bundle.py is left as it was)", "script": art(f"{r}/build-bundle-v2.py")},
            {"label": "wave 1 (Relay, history): power gate, analytic MDE grid, cost model, Monte Carlo of the staged design",
             "script": art("compute/power-gate.py"), "output": art("compute/power-gate.json")},
            {"label": "wave 1 (history): query-log builder", "script": art("compute/build-query-log.py")},
            {"label": "snapshot script for source_snapshots (arXiv metadata and page titles)", "script": art("compute/snapshot-sources.py")},
            {"label": "wave 1 (history): discovery-cell scripts and outputs; tokens redacted, originals' SHA-256 in ORIGINAL_SHA256.txt",
             "files": [art(f"compute/cells/{n}") for n in cells] + [art("compute/cells/ORIGINAL_SHA256.txt")]},
        ],
        "repository_evidence_used": {
            "s1a_records": "program/evidence/2026-10-10/q2-stage1-analysis/a1.jsonl (SHA-256 in power-osworld.json inputs)",
            "s1a_plan": "program/evidence/2026-10-09/q2-stage1-prefreeze/plan/plan-a0a.json (task domains, flagged tasks)",
            "s1a_results": "program/evidence/2026-10-10/q2-stage1-a1/RESULTS.md",
            "design_study_cost_model": "stage0/q2-design-study 79096f8 program/evidence/2026-10-10/q2-design-study/cost-model.json (constants copied into power-osworld.py)",
            "d53_acceptance": "program/evidence/2026-10-08/q2-action-path-v2-acceptance/README.md; program/decisions.md D53",
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
                               "experiment_id": "s2-arabic-cua-locale-v2", "status": "DRAFT, not frozen, no ledger row",
                               "supersedes": {"path": str(REGISTRATION_V1.relative_to(ROOT)), "sha256": sha(REGISTRATION_V1),
                                              "experiment_id": "s2-arabic-cua-locale-v1", "note": "wave 1's Relay draft, left unedited (gauntlet rule 3)"}},
        "source_snapshots": snapshots,
        "query_log": {**art("query-log.json"), "queries_against_budget": qb,
                      "run2": {**art("query-log-run2.json"), "counted": q2["counted_by_repair_owner"], "by_tool": q2["counted_by_tool"],
                               "declared": q2["declared_budget_queries"], "remaining": q2["remaining_after_repair"],
                               "note": "the D68 repair run's queries; this run's budget is fresh (80, at least 30 reserved for the triad)"},
                      "note": (f"{qb['counted_total']} counted orx discover queries against the declared 150 "
                               f"(remaining {qb['remaining_under_declared']}, reserve of 30 intact); "
                               f"{sum(qb['orx_calls_failed_429_by_stage'].values())} orx calls failed with HTTP 429 (not counted); "
                               f"{sum(qb['uncounted_other_searches_and_fetches_by_stage'].values())} uncounted searches and fetches "
                               f"({qb['total_if_other_searches_counted']} if counted)")},
        "reviews": [],
        "reviews_status": "NOT_RUN for this run: the blind critic, the refute-first triad and both reviewers run after the D68 repair (wave 1's reviews are in the gauntlet record). No trusted Ed25519 store exists (D24), so no review can be signed.",
        "compute": compute,
        "doctors": doctors,
        "audit_log": None,
        "audit_log_status": "Wave 1's row is in program/gauntlet/2026-10-10-s2-arabic-cua-locale.jsonl (row hash 1a24cee8...); this run's row is appended with scripts/research_gauntlet_record.py after its reviewers score.",
    }
    payload = {key: bundle.get(key) for key in ("source_snapshots", "query_log", "compute", "doctors", "audit_log")}
    bundle["evidence_root_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    blind = {}
    for path in sorted((BUNDLE / "blind").glob("paragraph-*.txt")):
        blind[path.name] = art(f"blind/{path.name}", text_sha256=hashlib.sha256(
            path.read_text(encoding="utf-8").rstrip("\n").encode()).hexdigest())
    roles = json.loads((BUNDLE / "compute/repair-d68/blind-roles-run2.json").read_text(encoding="utf-8"))
    bundle["blind_discrimination_packet"] = {
        "proposal": blind[roles["proposal"]],
        "closest_prior": blind[roles["closest_prior"]],
        "closest_prior_id": roles["closest_prior_id"],
        "note": "This run's packet (compute/repair-d68/blind-roles-run2.json, recorder only). File names carry no role and each file holds only its paragraph. The critic receives the two texts in randomized order, read by path, without this mapping or any other text. Wave 1's packet (compute/blind-roles.json) stays for the record.",
    }
    bundle["budget_ledger"] = {
        "declared_this_run": {"queries": 80, "wall_minutes": 600, "tokens": 8000000, "dollars": 150, "waves": 1, "gpu_hours": 0.3,
                              "refuter_query_reserve": 30},
        "used_by_repair": {"queries": q2["counted_by_repair_owner"], "queries_by_tool": q2["counted_by_tool"],
                           "uncounted": "2 paper reads; 13 primary-source fetches (plus 3 inspection re-fetches of the same files)",
                           "gpu_hours": 0.0, "host": "none (no host contact)",
                           "cpu": "power-osworld.py on the development Mac (heavily loaded host machine; tens of minutes); Chromium fixture renders and oracle validation (minutes)",
                           "tokens_and_dollars": "not metered by the repair agent; the recorder meters from transcripts",
                           "wall_clock": "repair started 2026-10-10T23:53:33Z"},
        "remaining_queries_this_run": q2["remaining_after_repair"],
        "refuter_reserve_intact": q2["reserve_intact"],
        "wave1_declared": {"queries": 150, "wall_minutes": 600, "tokens": 8000000, "dollars": 150, "waves": 3, "gpu_hours": 0.3},
        "wave1_used": {"queries": 123, "gpu_hours": 0.0553, "note": "see the wave-1 gauntlet row"},
    }
    out = BUNDLE / "doctors/research-direction-doctor-output.json"
    if out.is_file():
        bundle["direction_doctor_run"] = {
            **art("doctors/research-direction-doctor-output.json"),
            "command": "uv run python scripts/research_direction_doctor.py program/proposals/2026-10-10-s2-arabic-cua-locale.md",
            "note": "Outside evidence_root by design: the doctor output depends on this bundle."}
    (BUNDLE / "bundle.json").write_text(json.dumps(bundle, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(bundle["proposal_sha256"], bundle["evidence_root_sha256"], len(snapshots))


if __name__ == "__main__":
    main()
