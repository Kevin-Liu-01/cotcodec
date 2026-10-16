#!/usr/bin/env python3
"""Write the six preflight doctor records for the G2-stream gauntlet (wave 1 synthesis).

Each record states PASS or FAIL, its evidence and its remediation, as the proposal's Preflight
Doctors table does. The citation record carries the claim registry parsed from the proposal's
Primary-Source Evidence table, with each claim's read level, verdict and snapshot HTTP status.
Adapted from the G2-RL bundle's write_doctors.py (read level D added for desk arithmetic).
Run from the repo root after the snapshots and the query log exist.

Usage: python3 write_doctors.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
B = ROOT / "program/proposals/evidence/2026-10-16-g2-kimi-expert-streaming"
PROPOSAL = ROOT / "program/proposals/2026-10-16-g2-kimi-expert-streaming.md"
LEVEL = {
    "F": "full text read with orx paper --full (or targeted grep) by a discovery cell",
    "F*": "full text read by a discovery cell and re-read by the synthesis owner",
    "A": "abstract or report only",
    "R": "repository, code, release or dataset record",
    "1P": "first-party page, README or blog",
    "M": "this program's committed measurement",
    "D": "this synthesis's desk arithmetic on published numbers, committed in the bundle",
}
VERDICT = {"F": "VERIFIED", "F*": "VERIFIED", "A": "VERIFIED-ABSTRACT", "R": "VERIFIED-RECORD",
           "1P": "FIRST-PARTY", "M": "COMMITTED-MEASUREMENT", "D": "DESK-ARITHMETIC"}


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
        rec = {"claim_id": cid, "claim": claim, "source": src, "date": date,
               "read_level": LEVEL.get(lvl, lvl), "verdict": VERDICT.get(lvl, "UNCLASSIFIED"),
               "snapshot_http_status": snaps.get(src)}
        if lvl == "1P":
            rec["note"] = "first-party; not replicated"
        if lvl == "D":
            rec["note"] = "arithmetic on published numbers; reproducible from the named bundle file"
        out.append(rec)
    return out


def main() -> int:
    d = B / "doctors"
    d.mkdir(parents=True, exist_ok=True)
    reg = claims()
    q = json.loads((B / "query-log.json").read_text(encoding="utf-8"))
    sim = json.loads((B / "compute/sim-g2stream.json").read_text(encoding="utf-8"))
    caps = json.loads((B / "compute/caps-g2stream.json").read_text(encoding="utf-8"))
    ident = json.loads((B / "compute/identification-g2stream.json").read_text(encoding="utf-8"))
    recs = {
        "source": {
            "name": "Source", "status": "PASS",
            "protocol": "K-Dense literature-review (PRISMA counts); orx retrieval rule (six or more discover queries per cell, closest priors read in full)",
            "evidence": {
                "backends_reached": ["orx alphaXiv keyword and embedding", "OpenAlex", "GitHub API", "Hugging Face API", "web search"],
                "counts": q["counts"], "prisma": q["prisma"], "cutoff": "2026-10-15",
                "degraded": [
                    "orx 0.2.2 outdated against 0.2.18 (ranking may differ)",
                    "gated Kimi-K2-Thinking trace files not opened (README and listing only)",
                    "not searched: X, Reddit, Hacker News, OpenReview, ACL Anthology, patents, Chinese-language sources beyond one web search, citation graphs, the arXiv API",
                    "two Research Square preprints with empty abstracts; IJCAI 2026 DoMoE; KTransformers SOSP'25; later pages of the Zenodo PDF",
                ],
            },
            "remediation": "Semantic Scholar citer refresh for 2608.12103 and 2510.05497 through the host relay; a Chinese-language search for Kimi routing locality",
        },
        "citation": {
            "name": "Citation", "status": "PASS",
            "protocol": "ARS academic-pipeline claim_verification_protocol (claim registry, locators, verdicts, first-party labels)",
            "claims": reg,
            "summary": {"claims": len(reg),
                        "first_party": sum(r["verdict"] == "FIRST-PARTY" for r in reg),
                        "desk": sum(r["verdict"] == "DESK-ARITHMETIC" for r in reg),
                        "snapshots_http_200": sum(r["snapshot_http_status"] == 200 for r in reg)},
            "corrections_after_rereading": [
                "kill-shot cell: Anemll's hit rates are consistent with its counters once each miss is three tensor reads (C07)",
                "dossier S51 (1.7 tokens/s, engine not stated) is the rustane report (C26)",
                "dossier G2 status 'No Kimi K2 trace exists' is false (C03, C05, C08)",
            ],
            "remediation": "Replace first-party ds4 and Anemll numbers when replicated",
        },
        "novelty": {
            "name": "Novelty", "status": "FAIL",
            "evidence": {
                "frontier_verdict": "NARROWED, not OCCUPIED",
                "killshot_verdict": "NARROWED, not OCCUPIED",
                "closest_prior": "Anemll Flash-MoE llama.cpp fork and docs/moe-bank-modeling-workflow.md at a809594f, read in full by the synthesis owner",
                "closest_paper_priors_read_full": ["2608.12103", "2608.07911", "2510.05497", "2609.14864", "2608.16157"],
                "not_run": ["blind closest-prior discrimination", "novelty refuter"],
                "open_risk": "recombination of the Anemll workflow, S82's policy comparison and 2609.14864's held-out discipline",
            },
            "remediation": "Run the blind critic on blind/ (order in compute/blind-roles.json, recorder only) and the novelty refuter within the remaining query budget",
        },
        "design": {
            "name": "Design", "status": "PASS", "self_assessed": True,
            "protocol": "K-Dense experimental-design and statistical-power (design before data; one calibration row; operating characteristics by simulation)",
            "evidence": {
                "calibrated_constants": ["B from CAL-B, a prompt-independent whole-pool append"],
                "frozen_null": {"G": ident["null_frozen"]["G"], "mean_abs_log_err": ident["null_frozen"]["mean_abs_log_err"]},
                "primary_contrasts": ["K1 1.625", "K2 1.249", "K3 1.352"],
                "fidelity_strata": ["EXACT", "PROBABLE", "CANDIDATE"],
                "gates": ["G1 dump fidelity", "G2 input fidelity", "G3 runtime correctness", "G4 resume"],
                "kill_criteria": ["KC1-KC5 (registration section 7.3)"],
                "falsifiers": ["PR1", "PR2", "PR3", "PR4", "PR5", "PR7"],
                "unit_tests_all_pass": {s: v["all_pass"] for s, v in sim["unit_tests"].items()},
                "operating_characteristics": "compute/sim-g2stream.json",
            },
            "remediation": "Identification refuter; pre-freeze audit of the registration",
        },
        "compute": {
            "name": "Compute", "status": "FAIL",
            "evidence": {
                "image": "research base and vLLM base digests only; no llama.cpp image",
                "manifest": None, "container_smoke": "NOT_RUN", "slurm_dry_run": "NOT_RUN",
                "pilot_cap_gpu_h": caps["pilot"]["cap_gpu_h"], "pilot_expected_gpu_h": caps["pilot"]["expected_gpu_h"],
                "full_study_gpu_h": caps["full"]["total_gpu_h"], "full_study_cap": caps["full"]["proposed_cap_gpu_h"],
                "downloads_GB": caps["downloads_GB"]["pilot_total"],
                "arithmetic": "compute/caps-g2stream.json",
            },
            "remediation": "P0 and P0b (image, dump tool, policy port), manifests, dry runs and test-only runs before a freeze; Kevin's download go-ahead (compute/attestations-not-run.md)",
        },
        "safety": {
            "name": "Safety", "status": "PASS",
            "evidence": {
                "licences": "Kimi K2.6 modified MIT; GLM-5.3 Licence (upstream; antirez repo untagged); V4 Flash MIT; ds4 MIT (read and ported with attribution); datasets ODC-BY, Apache-2.0, CC-BY-4.0, MIT; unlicensed sets excluded",
                "r570": "stock llama.cpp at a pinned tag in a digest-pinned image; one reviewed CPU-side dump tool, no GPU kernel; ds4 never run",
                "host": "GPUs among 1-7 only; GPU 0 and D110 jobs untouched; no sudo; ~/cotcodec untouched",
                "public_repo": "aggregates and hashes only; no host addresses, credentials or conversation text",
                "outward_actions": "none; downloads await Kevin's go-ahead",
            },
            "remediation": "none",
        },
    }
    for key, rec in recs.items():
        (d / f"{key}.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(key, rec["status"])
    print("claims", len(reg), "http200", sum(r["snapshot_http_status"] == 200 for r in reg))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
