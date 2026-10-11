#!/usr/bin/env python3
"""Write the six preflight doctor records for the R01 gauntlet (wave 1 synthesis).

Each record states PASS or FAIL, the evidence and the remediation, as the proposal's
Preflight Doctors table does; the citation record carries the claim registry parsed from the
proposal's Primary-Source Evidence table, with each claim's read level and verdict. Run from the
worktree root after the snapshots exist (the citation record reads their HTTP statuses).

Usage: python3 write_doctors.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
B = ROOT / "program/proposals/evidence/2026-10-11-r01-rerun-noise-sources"
PROPOSAL = ROOT / "program/proposals/2026-10-11-r01-rerun-noise-sources.md"
LEVEL = {"F": "full text read with orx paper --full by a discovery cell",
         "A": "abstract or report only", "R": "repository record", "1P": "first-party page"}


def claims() -> list[dict]:
    text = PROPOSAL.read_text(encoding="utf-8")
    sec = text.split("## Primary-Source Evidence", 1)[1].split("\n## ", 1)[0]
    snaps = {}
    for p in (B / "snapshots").glob("*.json"):
        rec = json.loads(p.read_text())
        snaps[rec["url"]] = rec["http_status"]
    out = []
    for line in sec.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 5 or not re.fullmatch(r"[CR]\d+", cells[0]):
            continue
        cid, claim, src, date, lvl = cells
        url = src.strip("`")
        verdict = "VERIFIED"
        note = None
        if lvl == "A" and "openreview.net" in url:
            verdict, note = "VERIFIED-ABSTRACT", "full text UNVERIFIABLE_ACCESS (browser challenge, not bypassed)"
        elif lvl == "A":
            verdict = "VERIFIED-ABSTRACT"
        elif lvl == "1P":
            verdict, note = "FIRST-PARTY", "not replicated"
        if cid == "C30":
            note = ("licence confirmed on 2026-10-11 through https://huggingface.co/api/models/Qwen/Qwen3.5-4B: "
                    "cardData.license apache-2.0, sha 851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a (S1a's revision)")
        out.append({"claim_id": cid, "claim": claim, "source": url, "date": date, "read_level": LEVEL.get(lvl, lvl),
                    "verdict": verdict, "snapshot_http_status": snaps.get(url), **({"note": note} if note else {})})
    return out


def main() -> int:
    d = B / "doctors"
    d.mkdir(parents=True, exist_ok=True)
    reg = claims()
    recs = {
        "source": {"name": "Source", "status": "PASS", "protocol": "K-Dense literature-review (PRISMA counts)",
                   "evidence": ["orx 0.2.2 alphaXiv and OpenAlex reachable from the Mac (query-log.json: 103 counted discover queries with returned ids)",
                                "OpenReview api2 term searches (abstracts); arXiv API version checks through the host relay (frontier cell)",
                                "source cutoff 2026-10-11; newest alphaXiv results 2026-10-09 to 2026-10-10"],
                   "degraded_coverage": ["orx client outdated (0.2.2 against 0.2.18)", "OpenReview per-note pages and PDFs behind a challenge",
                                         "no Semantic Scholar or Google Scholar citers, GitHub code search, vLLM issues, patents, X, Reddit, Chinese-language venues",
                                         "ACL Anthology only through the renewal dossier's regex queries and two site-restricted web searches"],
                   "remediation": "Semantic Scholar citer refresh for 2604.17849 and cELldjX2oq through the host relay when free"},
        "citation": {"name": "Citation", "status": "PASS", "protocol": "ARS claim_verification_protocol.md",
                     "claim_registry": reg,
                     "summary": {"claims": len(reg), "verified_full_or_repository": sum(c["verdict"] == "VERIFIED" for c in reg),
                                 "abstract_only": sum(c["verdict"] == "VERIFIED-ABSTRACT" for c in reg),
                                 "first_party": sum(c["verdict"] == "FIRST-PARTY" for c in reg)},
                     "remediation": "Read cELldjX2oq in full if a copy becomes reachable; replicate the first-party figures before any claim rests on them"},
        "novelty": {"name": "Novelty", "status": "FAIL",
                    "evidence": ["kill-shot verdict NARROWED (frontier, kill-shot and cross-domain cells agree); no direct prior found through 2026-10-11 under the recorded coverage",
                                 "closest prior by mechanism, cELldjX2oq, judged from its abstract only (no arXiv copy found)",
                                 "blind critic and novelty refuter not yet run"],
                    "remediation": "Run the blind critic on blind/ (roles in compute/blind-roles.json, recorder only) and the novelty refuter"},
        "design": {"name": "Design", "status": "PASS", "self_assessed": True,
                   "protocol": "K-Dense experimental-design and statistical-power (vendored)",
                   "evidence": ["interventions: serving configuration (2x2 batch by cache), observation perturbation (clock swap, mask, other-region swap), blink-off condition",
                                "controls: replica floor B0b, P0/P0' self-test, paired interaction cell, replay-vs-replay and replay-vs-original, prompt-id fidelity check, clock-box positive control",
                                "falsifiers P1-P8, P-K6; the six kill criteria restated with reachable thresholds (registration section 10)",
                                "operating characteristics for every threshold: compute/power-r01.json (seeds 42, 43, 44)",
                                "Stage A0 natural experiment replicated from hash-checked records (program/evidence/2026-10-11/r01-stage-a0/census.json)"],
                   "limits": ["the identification refuter has not run", "Stage B's loaded passes reproduce S1a-like load, not S1a's exact batch or cache history",
                              "text-level identity may saturate under batching; IR-level readings registered beside it"],
                   "remediation": "Identification refuter; pre-freeze audit"},
        "compute": {"name": "Compute", "status": "FAIL",
                    "evidence": ["executable CPU pilot: Stage A0 as orx cpu-doctor run 83ee815a-426a-4b94-a93f-cc1277972d76 (exit 0), receipt byte-identical to the committed census",
                                 "registered caps 4.22 cap-GPU-h with conditional jobs (compute/caps-r01.json)"],
                    "missing": ["capture and open-loop replay driver modes", "request rebuilder", "Stage B manifests", "container smoke", "Slurm dry run and test-only",
                                "the deterministic doctor's real-model-loop and benchmark-adapter attestations"],
                    "remediation": "Build the A1 capture and C replay modes and the rebuilder with tests; render manifests; dry run and test-only before a freeze"},
        "safety": {"name": "Safety", "status": "PASS",
                   "evidence": ["no training, no downloads, no outward action; offline VMs on the certified lane",
                                "licences: OSWorld Apache-2.0, Qwen3.5-4B Apache-2.0, vLLM Apache-2.0",
                                "screenshots and request bodies stay on the host; repository receives hashes and counts only",
                                "host rule: read-only squeue before submissions; no overlap with other workflows' jobs"],
                   "remediation": "none"},
    }
    for name, rec in recs.items():
        (d / f"{name}.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(name, rec["status"], len(json.dumps(rec)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
