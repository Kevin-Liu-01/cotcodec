#!/usr/bin/env python3
"""Write the six preflight doctor records for the G2-RL gauntlet (wave 1 synthesis).

Each record states PASS or FAIL, its evidence and its remediation, as the proposal's Preflight
Doctors table does. The citation record carries the claim registry parsed from the proposal's
Primary-Source Evidence table, with each claim's read level, verdict and snapshot HTTP status.
Run from the repo root after the snapshots exist.

Usage: python3 write_doctors.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
B = ROOT / "program/proposals/evidence/2026-10-15-g2rl-state-precision-rl"
PROPOSAL = ROOT / "program/proposals/2026-10-15-g2rl-state-precision-rl.md"
LEVEL = {
    "F": "full text read with orx paper --full (or targeted grep) by a discovery cell",
    "F*": "full text read by a discovery cell and by the synthesis owner",
    "A": "abstract or report only",
    "R": "repository, code, release or dataset record",
    "1P": "first-party page, blog or issue",
    "M": "this program's committed measurement (exploratory)",
    "UNVERIFIABLE_ACCESS": "not readable from this environment",
}


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
        if len(cells) != 5 or not re.fullmatch(r"[CM]\d+", cells[0]):
            continue
        cid, claim, src, date, lvl = cells
        src = src.strip("`")
        verdict = {
            "F": "VERIFIED",
            "F*": "VERIFIED",
            "A": "VERIFIED-ABSTRACT",
            "R": "VERIFIED-RECORD",
            "1P": "FIRST-PARTY",
            "M": "COMMITTED-MEASUREMENT",
            "UNVERIFIABLE_ACCESS": "UNVERIFIABLE_ACCESS",
        }.get(lvl, "UNCLASSIFIED")
        rec = {
            "claim_id": cid,
            "claim": claim,
            "source": src,
            "date": date,
            "read_level": LEVEL.get(lvl, lvl),
            "verdict": verdict,
            "snapshot_http_status": snaps.get(src),
        }
        if "openreview.net" in src:
            rec["note"] = "the snapshot is an HTTP 200 browser-challenge page; content from the D104 dossier verifier only"
        if lvl == "1P":
            rec["note"] = "first-party; not replicated"
        out.append(rec)
    return out


def main() -> int:
    d = B / "doctors"
    d.mkdir(parents=True, exist_ok=True)
    reg = claims()
    q = json.loads((B / "query-log.json").read_text(encoding="utf-8"))
    recs = {
        "source": {
            "name": "Source",
            "status": "PASS",
            "protocol": "K-Dense literature-review (PRISMA counts); orx retrieval rule (six or more discover queries per cell, closest priors read in full)",
            "evidence": {
                "backends_reached": ["orx alphaXiv keyword and embedding", "OpenAlex", "GitHub API", "Hugging Face API", "web search"],
                "counts": q["counts"],
                "cutoff": "2026-10-15",
                "degraded": [
                    "orx 0.2.2 outdated against 0.2.18 (ranking may differ)",
                    "OpenReview: bot challenge on every route (9LUInzhKZc UNVERIFIABLE_ACCESS)",
                    "X: HTTP 402; Notion blogs did not render; Wiley 403; Semantic Scholar 429",
                    "not searched: citation graphs, arXiv API, Reddit, Chinese-language sources, patents, ACL Anthology",
                    "GitHub code search incomplete",
                ],
            },
            "remediation": "Semantic Scholar citer refresh for 2510.19338 and 2610.14448 through the host relay; a browser read of 9LUInzhKZc",
        },
        "citation": {
            "name": "Citation",
            "status": "PASS",
            "protocol": "ARS academic-pipeline claim_verification_protocol (claim registry, locators, verdicts, UNVERIFIABLE_ACCESS)",
            "claims": reg,
            "summary": {
                "claims": len(reg),
                "first_party": sum(r["verdict"] == "FIRST-PARTY" for r in reg),
                "unverifiable": sum(r["verdict"] == "UNVERIFIABLE_ACCESS" for r in reg),
                "snapshots_http_200": sum(r["snapshot_http_status"] == 200 for r in reg),
            },
            "remediation": "Replace first-party numbers when replicated; re-read the C02/C03 figures directly; read 9LUInzhKZc",
        },
        "novelty": {
            "name": "Novelty",
            "status": "FAIL",
            "evidence": {
                "frontier_verdict": "NARROWED, not OCCUPIED",
                "killshot_verdict": "NARROWED, not OCCUPIED",
                "closest_prior": "arXiv 2510.19338 (Ring-linear), read in full by two cells and the synthesis owner",
                "not_run": ["blind closest-prior discrimination", "novelty refuter"],
                "open_risk": "trivial recombination of the FP16-paper factorial (2510.26788) with KV4-RL's cache lever (2610.14448)",
            },
            "remediation": "Run the blind critic on blind/ (order in compute/blind-roles.json, recorder only) and the novelty refuter within the query budget the orchestrator rules on",
        },
        "design": {
            "name": "Design",
            "status": "PASS",
            "self_assessed": True,
            "protocol": "K-Dense experimental-design and statistical-power (design before data; seed blocking; sample size by simulation from a stated minimum effect)",
            "evidence": {
                "manipulation": "mamba_ssm_cache_dtype only; everything else fixed",
                "controls": ["fp32 between-seed floor", "A/A replicate batches (pilot)", "decoupled correction", "common fp32-state evaluator", "in-run manipulation check"],
                "gates": ["G1 stack", "G2 resume", "G3 anchor", "G4 manipulation", "G5 floor", "G6 cost"],
                "kill_criteria": ["K1-K6 (registration section 7)"],
                "falsifiers": ["PR1 (ratio below 2 stops)", "PR5 (r_hat at least 0.8 falsifies the prefix-shift account)", "F2 (TOST within 3 points with F1 holding)", "F4 (BT equivalent to F)"],
                "operating_characteristics": "compute/power-g2rl.json",
                "excluded_arms_with_evidence": "compute/mismatch-by-cap.json",
            },
            "remediation": "Identification refuter; pre-freeze audit of the registration",
        },
        "compute": {
            "name": "Compute",
            "status": "FAIL",
            "evidence": {
                "image": "base only (vLLM v0.31.0 digest); no verl overlay",
                "manifest": None,
                "container_smoke": "NOT_RUN",
                "slurm_dry_run": "NOT_RUN",
                "pilot_cap_gpu_h": 7.9167,
                "full_design_central_gpu_h": {"null_path": 641.6, "changes_path": 1153.1},
                "arithmetic": "compute/caps-g2rl.json",
            },
            "remediation": "P0 build and selftests, manifests, dry runs and test-only runs before a freeze (compute/attestations-not-run.md)",
        },
        "safety": {
            "name": "Safety",
            "status": "PASS",
            "evidence": {
                "licences": "Qwen3.5-4B Apache-2.0; DAPO-Math-17k Apache-2.0; MATH-500 recorded MIT (no Hub tag); AIME compilations Apache-2.0 or MIT (problems MAA copyright, evaluation only); verl, vLLM, Ray, Math-Verify Apache-2.0; FLA MIT; flash-attn BSD-3-Clause",
                "r570": "stock libraries and reviewed Python only on GPUs; no custom kernels; no stochastic-rounding kernel written",
                "host": "free GPUs only; no preemption of D110 or AM1 work; no sudo",
                "public_repo": "no host addresses, credentials or private data",
                "outward_actions": "none",
            },
            "remediation": "none",
        },
    }
    for key, rec in recs.items():
        (d / f"{key}.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(key, rec["status"])
    print("claims", len(reg))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
