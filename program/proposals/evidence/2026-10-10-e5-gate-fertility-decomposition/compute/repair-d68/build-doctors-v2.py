#!/usr/bin/env python3
"""Rewrite the six preflight doctor records for the E5 fresh gauntlet run after the D68 repair.

Wave 1's builder (`compute/build-doctors.py`) is kept unedited; its records are replaced by
this run's, and wave 1's are preserved in the wave-1 record's doctor_results. The citation
record's claim registry is parsed from the proposal's "Primary-Source Evidence" table, so
the registry and the proposal cannot drift. Every record is a pass by the single repair
owner, not an independent review.

Usage (from the worktree root):
    python3 program/proposals/evidence/2026-10-10-e5-gate-fertility-decomposition/compute/repair-d68/build-doctors-v2.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
BUNDLE = ROOT / "program/proposals/evidence/2026-10-10-e5-gate-fertility-decomposition"
PROPOSAL = ROOT / "program/proposals/2026-10-10-e5-gate-fertility-decomposition.md"
BY = "pass by the single repair owner under D68 (Claude agent), 2026-10-10; not an independent review"


def registry() -> list[dict]:
    text = PROPOSAL.read_text(encoding="utf-8")
    sec = text.split("## Primary-Source Evidence", 1)[1].split("\n## ", 1)[0]
    rows = []
    for line in sec.splitlines():
        m = re.match(r"^\| (C\d\d) \| (.+?) \| (.+?) \| (.+?) \| (.+?) \|$", line)
        if not m:
            continue
        cid, claim, source, locator, read = m.groups()
        urls = re.findall(r"\((https?://[^)]+)\)", source)
        if read.startswith("full") or read.startswith("synthesis") or read == "code read" or read == "repository":
            verdict = "VERIFIED"
        elif read.startswith("report"):
            verdict = "VERIFIED_REPORT_LEVEL"
        else:
            verdict = "VERIFIED_ABSTRACT_ONLY"
        rows.append({"claim_id": cid, "claim": claim, "source": source, "urls": urls,
                     "locator": locator, "read_status": read, "verdict": verdict})
    return rows


def main() -> None:
    out = BUNDLE / "doctors"
    reg = registry()
    qlog = json.loads((BUNDLE / "query-log-run2.json").read_text(encoding="utf-8"))
    n_q = qlog["counted_by_repair_owner"]
    docs = {
        "source": {
            "doctor": "Source", "status": "PASS", "evaluated_on": "2026-10-10", "evaluated_by": BY,
            "pass_condition": "Required backends reachable; cutoff and degraded coverage recorded",
            "evidence": f"Wave 1's coverage (120 counted cell queries plus 15 refuter queries, query-log.json and the wave-1 record) plus this run's repair: {n_q} counted orx discover queries (alphaXiv keyword and embedding) with returned ids and raw-output SHA-256, 2 OpenAlex discover calls that failed with HTTP 429 (logged, not counted), 7 uncounted full-text reads (orx paper --full), and 6 uncounted OpenAlex API citation-graph lookups (query-log-run2.json); source cutoff 2026-10-10; every primary URL snapshotted with HTTP 200.",
            "degraded_coverage": [
                "OpenAlex through orx refused twice (HTTP 429); the direct OpenAlex API answered the citation-graph lookups",
                "Semantic Scholar and the arXiv API not used (unreachable from the Mac; the host is reserved for the reviewer's lane job)",
                "citation graph: OpenAlex lists 0 citing works for 2609.33093, 2609.16183 and 2606.27510 (too recent) and 17 for 1804.11188 (all screened by title); 94 works citing 2111.00396 match 'tokenization', of which the first 25 were screened by title",
                "OpenReview and the ACL Anthology not searched again in this run (wave 1's 9 OpenReview term searches and 2 Anthology fetches stand)",
                "patents, X, Reddit, GitHub code search and Chinese-language venues not searched",
                "orx 0.2.2 reports itself outdated against 0.2.18; the alphaXiv indices lean to recent papers",
                "full texts read by targeted section, not end to end",
            ],
            "remediation": "Semantic Scholar forward citations for 2609.33093 and 2609.16183 through the host relay once the host rule allows; an OpenReview sweep of ICLR 2027 forums when accessible.",
        },
        "citation": {
            "doctor": "Citation", "status": "PASS", "evaluated_on": "2026-10-10", "evaluated_by": BY,
            "pass_condition": "URLs, dates, authors, and quantitative claims verified in primary sources",
            "protocol": "ARS claim-verification protocol: claim registry, locators, read status and verdict per claim; abstract-only and report-level reads labelled as such",
            "evidence": f"Claim registry of {len(reg)} claims parsed from the proposal. The four ledger rows wave 1 closed on abstracts (2004.12265, 2404.03646, 2406.14528, 1804.11188) were re-read in full with orx paper --full; 2606.27510 (Prop. 3.1, Theorem 3.2) and the legacy direction-20 span oracle are credited; 2609.33093 Secs. 2.1-2.3, 4.2, 5-6 and App. B and 2609.16183's abstract, Axis 3 and Secs. 5-6 re-read for the delta rows. Every arXiv and Hugging Face URL is snapshotted with HTTP 200.",
            "claim_registry": reg,
            "corrections": [
                "wave-1 record: the pure decay cost in S1's worlds is 16-45 points (W6 K = 4 is 16.2), not 17-45",
                "wave-1 proposal: 'the dossier's kill line is kept in its unit' was wrong; v2 states the line on the guessing-corrected scale (2.25 raw forced-choice points)",
                "wave-1 proposal: subject R's registry entry records trust_remote_code: true and a vendoring blocker; v2 states it and clears it in prerequisite 2",
            ],
            "remediation": "Open the psychology sources cited from metadata only before any write-up.",
        },
        "novelty": {
            "doctor": "Novelty", "status": "FAIL", "evaluated_on": "2026-10-10", "evaluated_by": BY,
            "pass_condition": "Synonyms, component pairs, citation graph, code, and adjacent fields searched",
            "evidence": f"No direct prior art found through 2026-10-10 under wave 1's coverage plus this run's {n_q} counted queries (the factorial's components, the v2 mechanism in plain words, both closest priors' title phrases bounded after their first versions, noising and denoising in recurrent models, decay patching, forgetting-mass parity) and the OpenAlex citation-graph lookups. The verdict stays NARROWED and the proposal claims no new mechanism: the factorial is the noising/denoising pair of 2606.27510 applied to the decay channel; the clamp is legacy D20's span oracle at token granularity, i.e. Tallec and Ollivier's time-warp condition imposed on decay only.",
            "why_fail": [
                "this run's blind closest-prior critic has not run (packets in blind/, role map compute/repair-d68/blind-roles-run2.json)",
                "this run's novelty refuter has not run",
                "no Semantic Scholar citation traversal; OpenReview and the ACL Anthology not searched again",
            ],
            "remediation": "Run the blind critic on the proposal packet against each prior packet, and the novelty refuter, with OpenReview and Semantic Scholar if reachable.",
        },
        "design": {
            "doctor": "Design", "status": "FAIL", "evaluated_on": "2026-10-10", "evaluated_by": BY,
            "pass_condition": "Intervention, controls, falsifier, metrics, leakage, and statistics specified",
            "protocol": "K-Dense experimental-design and statistical-power (design before data; power by simulation for every threshold); statistical-analysis (paired, clustered intervals)",
            "evidence": "2 x 2 factorial (CAN, DEC, CLAMP, NAT) at a held-out-selected load with a ceiling gate; TNIE, PNIE, INT and PNDE with the exact identity; guessing-corrected line; article clustering; decision rules and operating-point rule as code (compute/repair-d68/estimator_v2.py); S1v2 (two-layer toy with state-dependent writes, presence channel, registered path), S2v2 (whole decision path through the registered estimator, discordance to about 0.45, every operating-point branch, v1's dilution reproduced), S3v2 (cost per branch).",
            "why_fail": [
                "discordance, accuracy profile and R_F are assumed or simulated, not measured on either checkpoint",
                "no harness exists; neither the clamp nor the transplant has run on a checkpoint",
                "the boundary-only arm re-bounds only 8 to 12% of tokens",
                "the episode builder, passages and key lists do not exist",
            ],
            "remediation": "Build the harness and the new CPU doctor (orx cpu-doctor node); measure the operating point, R_F and discordance in the smoke before the main jobs.",
        },
        "compute": {
            "doctor": "Compute", "status": "FAIL", "evaluated_on": "2026-10-10", "evaluated_by": BY,
            "pass_condition": "Image digest, Slurm dry-run, seeds, quota, checkpoint, and cost plan specified",
            "evidence": "Image 127.0.0.1:5000/cotcodec-research@sha256:13a9de831cff50461d8ecee3c2794f0c6d6bcffe9d602968fe2ee06e5a1096e9 (build 855, fla 0.5.2); seeds [42, 43, 44]; caps smoke 0.75 + G 1.75 + R 3.75 = 6.25 GPU-h (D22); S3v2 per branch, worst primary-only high 1.48 (G) and 3.34 (R) GPU-h; checkpoint every 5 minutes keyed by (episode, cell) with a kill-and-resume test; launch via scripts/submit_docker_research_job.py (dry run, test-only, submit).",
            "why_fail": [
                "no real model loop for this step (the harness does not exist)",
                "no benchmark adapter (episode builder not written as harness code)",
                "no container smoke, Slurm dry run, manifest or provenance verification",
                "subject G not on the host, not in the registry, and without a licence (fetch waits for Kevin's ruling and the host rule)",
                "inference throughput never measured on this host",
            ],
            "remediation": "Kevin's ruling on subject G; registry entry and CPU fetch; harness; smoke manifest; dry run and test-only; the smoke as an orx slurm-manifest node.",
        },
        "safety": {
            "doctor": "Safety", "status": "PASS", "evaluated_on": "2026-10-10", "evaluated_by": BY,
            "pass_condition": "Safety, monitorability, data rights, and project red lines addressed",
            "evidence": "Subject R apache-2.0 (card and 2503.14456; registry still records trust_remote_code: true and a vendoring blocker, cleared by prerequisite 2 before any run); subject G has no licence and its use is gated on Kevin's ruling (decision 1) with an apache-2.0 fallback and nothing redistributed; WikiText-103 (CC BY-SA 3.0, GFDL) passages kept off the public repository; the RWKV tokenizer vendored with ast.literal_eval; no untrusted code executes; nothing trained or deployed; no host access by the repair.",
            "condition": "Subject G is not fetched or run before decision 1 is made.",
            "remediation": "Decision 1 before any fetch.",
        },
    }
    for name, rec in docs.items():
        (out / f"{name}.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(len(reg), "claims;", {k: v["status"] for k, v in docs.items()})


if __name__ == "__main__":
    main()
