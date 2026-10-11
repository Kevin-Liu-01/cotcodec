#!/usr/bin/env python3
"""Write the six preflight doctor records of the S2 v3 wave-1 synthesis (doctors/*.json).

These are the single owner's assessments, not independent reviews. Statuses follow the
evidence: Novelty and Compute stay FAIL (no blind critic or novelty refuter yet; no derived image,
VM-lane oracle, Phase 1 manifest, dry run or orx node).
"""
import json
from pathlib import Path

B = Path(__file__).resolve().parents[1]
BY = "S2 v3 wave-1 synthesis by the single owner (Claude agent), 2026-10-11 UTC; not an independent review"
D = "2026-10-11"

docs = {
    "source": {
        "doctor": "Source", "status": "PASS", "evaluated_on": D, "evaluated_by": BY,
        "pass_condition": "Required backends reachable; cutoff and degraded coverage recorded",
        "evidence": ("orx 0.2.2 (alphaXiv keyword and embedding, OpenAlex) reachable from the development Mac; Semantic Scholar citer "
                     "lists and the arXiv export API reached by the frontier scout; OpenReview api2 term search (13 searches, one full "
                     "scan of 210 ICLR 2027 'multilingual' submissions); ACL Anthology bibliography with abstracts (131,473 entries). "
                     "query-log.json: 71 orx discover calls (frontier 35, kill-shot 15, cross-domain 18, owner 3), 91 with ACL Anthology and "
                     "OpenReview searches (the frontier's own tally gives 92), every returned id recorded; cutoff 2026-10-11."),
        "degraded_coverage": ["no Chinese-language query this wave", "Google Scholar, X, Reddit, Hacker News, GitHub not searched",
                              "EMNLP 2026 proceedings not yet in the Anthology", "anonymous OpenReview access degraded for the kill-shot scout",
                              "orx 0.2.2 reports itself outdated against 0.2.18", "patents: one Google Patents page only"],
        "remediation": "A Chinese-language query and a RealGUINoise revision check before any write-up.",
    },
    "citation": {
        "doctor": "Citation", "status": "PASS", "evaluated_on": D, "evaluated_by": BY,
        "pass_condition": "URLs, dates, authors, and quantitative claims verified in primary sources",
        "protocol": "ARS claim_verification_protocol: claim registry, source tracing, cross-referencing; first-party numbers labelled; "
                    "abstract-level reads marked",
        "evidence": ("39 claims (C01-C39) in the proposal with locators, dates and read status. Full-text reads by the cells for every "
                     "closest prior (macOSWorld, MPR-GUI, RealGUINoise, VAF, WebPageBench, BreakingWeb, Skill Issue, 2608.11110, PuMVR) "
                     "and the owner's full read of 2411.00640; LibreOffice source claims at tag libreoffice-7.3.7.2 with file and line; "
                     "pilot claims tied to Slurm job records and receipts (jobs 1097-1100); primary URLs snapshotted with HTTP status "
                     "and body hash (snapshots/)."),
        "claims": {"full_text": ["C01", "C02", "C04", "C05", "C06", "C07", "C08", "C09", "C10", "C14", "C18"],
                   "abstract_or_metadata": ["C11", "C12", "C15", "C16", "C17", "C19", "C20", "C21"],
                   "source_code": ["C23", "C27", "C28", "C29"], "standards_and_bug_records": ["C22", "C24", "C25", "C26"],
                   "patent_summary": ["C13"], "first_party_numbers": ["C14"],
                   "pilot": ["C30", "C36", "C37", "C38", "C39"], "repository": ["C32", "C33", "C34", "C35"],
                   "metadata_head_only": ["C31"], "citation_counts": ["C03"]},
        "remediation": "Read ITDroid and RotDroid in full before any delta row rests on them; re-check RealGUINoise's version before a write-up.",
    },
    "novelty": {
        "doctor": "Novelty", "status": "FAIL", "evaluated_on": D, "evaluated_by": BY,
        "pass_condition": "Synonyms, component pairs, citation graph, code, and adjacent fields searched",
        "protocol": ("K-Dense literature-review (PRISMA counts); orx rule: at least six discover queries per candidate including "
                     "keyword with exact terms and each closest prior's title phrase, embedding with the mechanism paragraph, openalex; "
                     "orx paper --full for every closest prior"),
        "evidence": ("Frontier verdict NO_DIRECT_PRIOR_FOUND, kill-shot verdict STILL_OPEN, both through 2026-10-10/11 under the coverage in "
                     "the proposal header; title-phrase queries for macOSWorld, RealGUINoise, MPR-GUI and VAF; citer lists for macOSWorld "
                     "(34, none relevant), MPR-GUI, RealGUINoise and VAF; a full ICLR 2027 'multilingual' scan; the census frame's method "
                     "priors (2411.00640, 2609.33012, Cameron and Baldock) recorded as infrastructure."),
        "why_fail": "This wave's blind critic and novelty refuter have not run; the rule requires them before Novelty can pass.",
        "queries_remaining_for_triad": 59,
        "remediation": "Run the blind critic on blind/ (macOSWorld) and the novelty refuter with at least six orx discover queries.",
    },
    "design": {
        "doctor": "Design", "status": "PASS", "evaluated_on": D, "evaluated_by": BY,
        "pass_condition": "Intervention, controls, falsifier, metrics, leakage, and statistics specified",
        "protocol": ("K-Dense experimental-design and statistical-power (vendored): design before data (a 2x2 blocked by task and session, "
                     "seeded interleaving, random slot assignment, both harnesses); power by simulation of the registered estimators on "
                     "measured inputs (beta-binomial propensities fitted and checked on S1a's records); K-Dense statistical-analysis and "
                     "the ARS reporting standards"),
        "evidence": ("Intervention: one system-layer selector (finalized ooLocale and UIMirroring), executed on the installed build in the "
                     "pilot. Controls: en baseline; O1-O8 with planted positive controls; tagged pseudo-catalog cell; functional A/A; config "
                     "invariance; offline setup; step-0 and keyboard checks. Falsifiers P1-P7 and kill criteria K0-K8, all reachable: "
                     "census SMALL at a true null 0.97 (homogeneous) and 0.92 (mixed-sign perturbation) at K = 106, n = 4; PRESENT_HARM at "
                     "a 15% relative drop 0.85-0.96 across five structures; SMALL when the census truth is beyond a margin at most 0.051 "
                     "(0.056 at K = 89); census coverage 0.94-0.95. No selection on outcomes; dual margin against dilution."),
        "why_fail": None,
        "remediation": "Re-run the simulation with real Phase 0 inputs (Arabic chrome share, RTL-defect counts) before the freeze.",
        "disclosed_limits": ["the 44 tasks without S1a records are drawn from a task-level fit (no harness heterogeneity)",
                             "the population-frame SMALL is much weaker under reshuffles (0.04-0.50)",
                             "the margins are fixed by judgement anchored on macOSWorld, which reports no interval"],
    },
    "compute": {
        "doctor": "Compute", "status": "FAIL", "evaluated_on": D, "evaluated_by": BY,
        "pass_condition": "Image digest, Slurm dry-run, seeds, quota, checkpoint, and cost plan specified",
        "evidence": ("Engine base digest (vllm/vllm-openai@sha256:b18abb2d...) and S1a's loop, adapters and lane as the Phase 1 stack; seeds "
                     "[42, 43, 44]; Phase 1 cap 6.10 GPU-h by the Q2 design study's slot rule (power-v3.json costs); checkpoint and resume "
                     "per episode as S1a. Executed in this gauntlet: four CPU-only Slurm jobs (1097-1100; 1096 cancelled), no GRES, on an "
                     "empty queue, in the LO-VM container sha256:f5b4c40e... through the D12 CPU lane pattern, all exit 0 with receipts "
                     "(compute/pilot/job109*/)."),
        "why_fail": ("No derived Arabic image (downloads wait on Kevin; image surgery and lane code unreviewed), no VM-lane oracle, no delta "
                     "certification, no Phase 1 manifest, no Slurm dry run or test-only of Phase 1, no orx node over experiments/orx/node.yaml, "
                     "no real model loop run for S2."),
        "remediation": ("Kevin's go-ahead for the three downloads; review of the image-surgery script and the lane version; Phase 0 in the "
                        "lane; then the Phase 1 manifest's dry run and test-only and an orx slurm-manifest node."),
    },
    "safety": {
        "doctor": "Safety", "status": "PASS", "evaluated_on": D, "evaluated_by": BY,
        "pass_condition": "Safety, monitorability, data rights, and project red lines addressed",
        "evidence": ("Offline VMs and containers on public OSWorld tasks; no host-run model code (D3, D7 not triggered); pilot containers "
                     "with --network=none, read-only root, no capabilities, the host user's uid, a GPU-device preflight; one CPU job at a "
                     "time on an empty queue; ~/cotcodec untouched; no outward action taken (downloads deferred to Kevin); licences "
                     "recorded (OSWorld Apache-2.0, LibreOffice and l10n-ar MPL-2.0, Ubuntu language packs per upstream, fonts already in "
                     "the image, Qwen3.5-9B Apache-2.0); committed records scanned for host addresses."),
        "remediation": "none",
    },
}
for name, d in docs.items():
    (B / "doctors" / f"{name}.json").write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n")
print("wrote", len(docs))
