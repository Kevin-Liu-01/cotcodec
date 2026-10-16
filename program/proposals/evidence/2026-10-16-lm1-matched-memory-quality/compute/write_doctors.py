#!/usr/bin/env python3
"""Write the six preflight doctor records for the LM1 gauntlet (wave 1 synthesis).

Each record states PASS or FAIL, its evidence and its remediation, as the proposal's Preflight
Doctors table does. The citation record carries the claim registry parsed from the proposal's
Primary-Source Evidence table, with each claim's read level, verdict and snapshot HTTP status.
Adapted from the G2-stream bundle's write_doctors.py. Run from the repo root after the snapshots,
the query log, the simulation and the caps arithmetic exist.

Usage: python3 write_doctors.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
B = ROOT / "program/proposals/evidence/2026-10-16-lm1-matched-memory-quality"
PROPOSAL = ROOT / "program/proposals/2026-10-16-lm1-matched-memory-quality.md"
LEVEL = {
    "F": "full text read with orx paper --full (or targeted grep) by a discovery cell",
    "F (synthesis)": "full text read with orx paper --full by the synthesis owner",
    "F\\*": "full text read by a discovery cell and re-read by the synthesis owner",
    "A": "abstract or report only",
    "A (synthesis)": "abstract read by the synthesis owner",
    "R": "repository, code, model or dataset record at a pinned revision",
    "1P": "first-party page, README, vendor card or index",
    "M": "this program's committed measurement",
    "D": "this synthesis's arithmetic on published numbers, committed in the bundle",
}
VERDICT = {"F": "VERIFIED", "F (synthesis)": "VERIFIED", "F\\*": "VERIFIED", "A": "VERIFIED-ABSTRACT",
           "A (synthesis)": "VERIFIED-ABSTRACT", "R": "VERIFIED-RECORD", "1P": "FIRST-PARTY",
           "M": "COMMITTED-MEASUREMENT", "D": "DESK-ARITHMETIC"}


def claims() -> list[dict]:
    text = PROPOSAL.read_text(encoding="utf-8")
    sec = text.split("## Primary-Source Evidence", 1)[1].split("\n## ", 1)[0]
    snaps = {}
    for p in (B / "snapshots").glob("*.json"):
        rec = json.loads(p.read_text(encoding="utf-8"))
        snaps[rec["url"]] = rec["http_status"]
    out = []
    for line in sec.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 5 or not re.fullmatch(r"C\d+", cells[0]):
            continue
        cid, claim, src, date, lvl = cells
        src = src.strip("`")
        rec = {"claim_id": cid, "claim": claim, "source": src, "date": date,
               "read_level": LEVEL.get(lvl, lvl), "verdict": VERDICT.get(lvl, "UNCLASSIFIED"),
               "snapshot_http_status": snaps.get(src)}
        if lvl == "1P":
            rec["note"] = "first-party; not replicated"
        if lvl == "D":
            rec["note"] = "arithmetic on published numbers; reproducible from the named bundle file"
        if lvl == "M":
            rec["note"] = "committed in this repository (D127 host prep)"
        out.append(rec)
    return out


def main() -> int:
    d = B / "doctors"
    d.mkdir(parents=True, exist_ok=True)
    reg = claims()
    q = json.loads((B / "query-log.json").read_text(encoding="utf-8"))
    sim = json.loads((B / "compute/sim-lm1.json").read_text(encoding="utf-8"))
    caps = json.loads((B / "compute/caps-lm1.json").read_text(encoding="utf-8"))
    base = [r for r in sim["seed_mean_table"] if r["setting"] == "base" and r["primary_items"] == 1600]
    recs = {
        "source": {
            "name": "Source", "status": "PASS",
            "protocol": "K-Dense literature-review (PRISMA counts); orx retrieval rule (six or more discover queries per cell, title-phrase queries for closest priors, closest priors read in full)",
            "evidence": {
                "backends_reached": ["orx alphaXiv keyword and embedding", "OpenAlex", "GitHub search", "Hugging Face API", "web search"],
                "counts": q["counts"], "prisma": q["prisma"], "cutoff": "2026-10-15",
                "degraded": [
                    "orx 0.2.2 outdated against 0.2.18 (ranking may differ)",
                    "the asset cell's 13 counted searches were reported without query strings",
                    "AA-Omniscience per-model accuracy values render client-side and were not read; only the comparison page's index values",
                    "not searched: X, Reddit (one snapshot mirror only), Hacker News, OpenReview, ACL Anthology, patents, Chinese-language sources beyond one web search, Semantic Scholar or Google Scholar forward citations",
                ],
            },
            "remediation": "A Semantic Scholar citer pass for 2509.25689, 2504.02010 and 2604.18556 through the host relay",
        },
        "citation": {
            "name": "Citation", "status": "PASS",
            "protocol": "ARS academic-pipeline claim_verification_protocol (claim registry, locators, verdicts, first-party labels)",
            "claims": reg,
            "summary": {"claims": len(reg),
                        "first_party": sum(r["verdict"] == "FIRST-PARTY" for r in reg),
                        "desk": sum(r["verdict"] == "DESK-ARITHMETIC" for r in reg),
                        "with_snapshot": sum(r["snapshot_http_status"] is not None for r in reg),
                        "snapshots_http_200": sum(r["snapshot_http_status"] == 200 for r in reg)},
            "corrections_after_rereading": [
                "1.87 bpw (K2.5 UD-TQ1_0, 239.5 GB over 1,026.4B parameters) and the dossier's 1.92 bits (K2-Thinking TQ1_0, 246.8 GB) describe different files",
                "cloud finding (a): GSQ's AgentBench model is 2.37 bits, not Table 3's 2.13",
                "the V4 Flash Q8_K_XL reference moved from the asset cell's pilot to the full study",
            ],
            "remediation": "Replace first-party speeds (Anemll, ds4) and AA indices when replicated",
        },
        "novelty": {
            "name": "Novelty", "status": "FAIL",
            "evidence": {
                "frontier_verdict": "NARROWED, not OCCUPIED",
                "killshot_verdict": "NARROWED, not OCCUPIED",
                "closest_prior": "CC-MoE (arXiv 2509.25689), read in full by the frontier cell and the synthesis owner",
                "closest_priors_read_full_by_synthesis": ["2509.25689", "2504.02010", "2604.18556", "2610.15372"],
                "not_run": ["blind closest-prior discrimination", "novelty refuter"],
                "open_risk": "recombination of CC-MoE Table 2, 2504.02010 Finding 1 and 2610.15372's wall-clock framing",
            },
            "remediation": "Run the blind critic on blind/ (roles in compute/blind-roles.json, recorder only) and the novelty refuter within the remaining query budget",
        },
        "design": {
            "name": "Design", "status": "PASS", "self_assessed": True,
            "protocol": "K-Dense experimental-design and statistical-power (design before data; minimum effect = the 5-point practical margin; operating characteristics by simulation)",
            "evidence": {
                "matched_memory": "RAM-matched eligibility tiers R-Y, R-T, S; strict-fit view reported",
                "decision_rule": "NOT_WORTH by Bonferroni non-superiority at +5 points over four resident arms; LEADS by intersection-union superiority with min point >= +5, index and per-benchmark conditions; SPLIT across two benchmarks with opposite contamination exposure",
                "gates": ["G1 assay sensitivity", "G2 judge", "G3 template fidelity", "G4 mode conformance", "G5 placement"],
                "kill_criteria": ["KC1-KC5 (registration section 7.2)"],
                "falsifiers": ["H1", "H2", "H3", "H4", "H5"],
                "operating_characteristics_base_1600": base,
                "simulation": "compute/sim-lm1.json",
            },
            "remediation": "Identification refuter; pre-freeze audit of the registration",
        },
        "compute": {
            "name": "Compute", "status": "FAIL",
            "evidence": {
                "image": "llama.cpp b11669 image and overlay exist (D127, digest-pinned); no LM1 overlay built",
                "models": "six GGUFs with receipts on the host (D127); judge Qwen3-32B with receipt (AM1)",
                "harness": "request runner, grader client, analysis and template check not written",
                "manifest": None, "container_smoke": "NOT_RUN for LM1 (D127's smoke test ran the image)",
                "slurm_dry_run": "NOT_RUN",
                "pilot_guards_gpu_h": caps["pilot"]["sum_of_guards_without_conditional_P2"],
                "pilot_line_gpu_h": caps["pilot"]["line_gpu_h"],
                "pilot_expected_unconditional_gpu_h": caps["pilot"]["expected_unconditional_gpu_h"],
                "full_study_gpu_h_by_branch": {k: v["gpu_h"] for k, v in caps["full_study"]["branches"].items()},
                "arithmetic": "compute/caps-lm1.json",
            },
            "remediation": "Write and test the harness, build the overlay from the freeze commit, render manifests, dry runs and test-only runs before a freeze (compute/attestations-not-run.md)",
        },
        "safety": {
            "name": "Safety", "status": "PASS",
            "evidence": {
                "licences": "Kimi K2.5 modified MIT; V4 Flash 0731 MIT; Qwen3 Apache-2.0; gpt-oss Apache-2.0; datasets Apache-2.0, MIT, ODC-BY; all ungated; GPQA-Diamond excluded (gated)",
                "r570": "stock llama.cpp at a pinned tag in a digest-pinned image; CPU-side harness only; no GPU kernel; model outputs graded, never executed",
                "host": "GPUs among 1-7 only, at most 3 before 2026-10-21; GPU 0, ~/cotcodec, ~/tc-speedrun and transcreate, tcsr and g3b jobs untouched; no sudo",
                "public_repo": "ids, hashes, grades and aggregates only; no host addresses, credentials, raw responses or benchmark text",
                "outward_actions": "none; full-study downloads await Kevin's go-ahead",
            },
            "remediation": "none",
        },
    }
    for name, rec in recs.items():
        (d / f"{name}.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(name, rec["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
