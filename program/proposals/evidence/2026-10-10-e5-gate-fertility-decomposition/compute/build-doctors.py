#!/usr/bin/env python3
"""Write the six preflight doctor records for the E5 gauntlet bundle.

The citation record's claim registry is parsed from the proposal's
"Primary-Source Evidence" table, so the registry and the proposal cannot drift.
Every record is a synthesis pass by the single synthesis owner, not an
independent review.

Usage (from the worktree root):
    python3 program/proposals/evidence/2026-10-10-e5-gate-fertility-decomposition/compute/build-doctors.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
BUNDLE = ROOT / "program/proposals/evidence/2026-10-10-e5-gate-fertility-decomposition"
PROPOSAL = ROOT / "program/proposals/2026-10-10-e5-gate-fertility-decomposition.md"
BY = "synthesis pass by the single synthesis owner (Claude agent), 2026-10-10; not an independent review"


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
    out.mkdir(exist_ok=True)
    reg = registry()
    docs = {
        "source": {
            "doctor": "Source", "status": "PASS", "evaluated_on": "2026-10-10", "evaluated_by": BY,
            "pass_condition": "Required backends reachable; cutoff and degraded coverage recorded",
            "evidence": "orx 0.2.2 (alphaXiv keyword and embedding, OpenAlex) reachable from the development Mac; arxiv.org abstract pages, the Hugging Face model, tree and dataset APIs and github.com reachable; 120 counted orx discover queries (frontier 47, kill-shot 24, cross-domain 43, asset 6, synthesis 0) with returned ids and raw-output SHA-256 in query-log.json (one asset raw output not saved, ids from the cell's result); 9 OpenReview term searches, 7 web searches, 2 ACL Anthology fetches and 2 failures logged as uncounted; 57 cell paper reads (40 distinct); source cutoff 2026-10-10; every primary URL snapshotted with HTTP 200.",
            "degraded_coverage": [
                "Semantic Scholar and the arXiv API unreachable from the Mac; the host relay was not used",
                "OpenReview: most ICLR 2027 forum titles hidden or HTTP 403; note pages behind a browser challenge, not bypassed",
                "ACL Anthology only through restricted web searches and two page fetches, not its own index",
                "patents, X, Reddit, GitHub code search and Chinese-language venues not searched; citation graph only through OpenAlex",
                "orx 0.2.2 reports itself outdated against 0.2.18; the alphaXiv keyword index leans to recent papers",
                "psychology sources read as OpenAlex metadata or abstracts only; LongMamba, ReMamba and LAMB not opened",
                "full texts read by targeted section, not end to end",
            ],
            "remediation": "Semantic Scholar forward citations for 2609.33093 and 2609.16183 through the host relay; a full OpenReview sweep when accessible.",
        },
        "citation": {
            "doctor": "Citation", "status": "PASS", "evaluated_on": "2026-10-10", "evaluated_by": BY,
            "pass_condition": "URLs, dates, authors, and quantitative claims verified in primary sources",
            "protocol": "ARS claim-verification protocol: claim registry, locators, read status and verdict per claim; abstract-only and report-level reads labelled as such",
            "evidence": f"Claim registry of {len(reg)} claims parsed from the proposal; every arXiv and Hugging Face URL snapshotted with HTTP 200 and arXiv version histories; Lee et al. Secs. 2.2-2.3, 4.1-4.2 and App. A, Boesch and Wee Sec. 4, 2507.06457 Sec. 3 and Limitations, 2506.19004 Sec. 4.1, SpectralShift abstract and App. B.2 and MambaExtend's abstract re-read by synthesis in the cells' full texts; first-party labels on card and release-paper numbers.",
            "claim_registry": reg,
            "dossier_corrections": [
                "GDN-1.3B training data is documented first-party (FineWeb-Edu, 100B tokens; 2507.06457 Sec. 3); the checkpoint has no licence",
                "the 'modest decline' over 128 to 1024 filler tokens is measured on the 340M models only, with filler that writes to the state",
                "a halved decay rate cannot identify the decay share (S1)",
                "600 episodes per cell gives P(KILL | no decay share) of 0.59 at discordance 0.30 (S2)",
                "the 16-language fund branch has no valid subject",
                "the 3 GPU-h estimate: S3 central 1.26, high 3.29; caps 4.0",
            ],
            "cell_corrections": [
                "cross-domain cell: duplicated pieces without write normalisation are not decay-only in a delta-rule memory (S1 world W5: decay share 0.41 to 0.44)",
                "asset cell: the 73,045 tok/s anchor was measured in image 0b3ecef0-architecture, not ed5d5a93",
            ],
            "remediation": "Open the psychology sources cited from metadata only before any write-up; read DeciMamba and GDN-2 in full if a delta row ever depends on more than their abstracts.",
        },
        "novelty": {
            "doctor": "Novelty", "status": "FAIL", "evaluated_on": "2026-10-10", "evaluated_by": BY,
            "pass_condition": "Synonyms, component pairs, citation graph, code, and adjacent fields searched",
            "evidence": "No direct prior art found through 2026-10-10 under the recorded coverage (120 counted orx queries including each closest prior's title phrase, the mechanism in plain words and published-after bounds; 40 distinct papers opened; 0 direct priors). Merged verdict NARROWED: Lee et al. (2609.33093), Boesch and Wee (2609.16183), MambaExtend, DeciMamba (2406.14528), Mamba Modulation (2509.19633), SpectralShift (2609.14320) and the re-segmentation literature each occupy one component.",
            "why_fail": [
                "the blind closest-prior critic has not run (packets in blind/)",
                "the novelty refuter has not run",
                "no counted query targeted activation patching of decay or gate parameters as such; synthesis had no queries left above the triad's reserve of 30",
                "no full OpenReview sweep of ICLR 2027 submissions; no citation-graph traversal beyond OpenAlex",
            ],
            "remediation": "Run the blind critic on blind/ and the novelty refuter, including the query 'activation patching decay gate recurrent language model mediation'.",
        },
        "design": {
            "doctor": "Design", "status": "FAIL", "evaluated_on": "2026-10-10", "evaluated_by": BY,
            "pass_condition": "Intervention, controls, falsifier, metrics, leakage, and statistics specified",
            "protocol": "K-Dense experimental-design and statistical-power (design before data; power by simulation for every threshold); statistical-analysis (paired, clustered intervals)",
            "evidence": "Per-token decay clamp (mediator held at its canonical value) with identity, two-way r = 2, FILL, BND, ZERO, SIL and FACT/BOTH controls; falsifiers P1 to P5; primary estimand and decision rules as code (compute/estimator.py); S1 identification in six worlds, S2 operating characteristics for every threshold, S3 cost, S4 splitting rules measured on both real tokenizers; leakage and shortcut risks stated.",
            "why_fail": [
                "discordance between clamp and native arms is assumed (0.05 to 0.30), not measured",
                "no harness exists; the clamp has never run on either checkpoint",
                "the boundary-only arm re-bounds only 8 to 12% of tokens",
                "the episode builder, passages and key lists do not exist; S4 used CC0 abstracts as a stand-in",
            ],
            "remediation": "Build the harness and the new CPU doctor (orx cpu-doctor node); measure discordance and R_F in the smoke before the main jobs.",
        },
        "compute": {
            "doctor": "Compute", "status": "FAIL", "evaluated_on": "2026-10-10", "evaluated_by": BY,
            "pass_condition": "Image digest, Slurm dry-run, seeds, quota, checkpoint, and cost plan specified",
            "evidence": "Image 127.0.0.1:5000/cotcodec-research@sha256:13a9de831cff50461d8ecee3c2794f0c6d6bcffe9d602968fe2ee06e5a1096e9 (build 855, fla 0.5.2); seeds [42, 43, 44]; caps smoke 0.25 + G 1.25 + R 2.5 = 4.0 GPU-h (D22); S3 central 1.26, high 3.29 GPU-h; checkpoint every 5 minutes keyed by (episode, cell) with a kill-and-resume test in the smoke; launch via scripts/submit_docker_research_job.py (dry run, test-only, submit).",
            "why_fail": [
                "no real model loop for this step (the harness does not exist)",
                "no benchmark adapter (episode builder, passages and splitting rules not written as harness code)",
                "no container smoke, Slurm dry run, manifest or provenance verification",
                "subject G not on the host, not in the registry, and without a licence (fetch waits for Kevin's ruling and the host rule)",
                "neither checkpoint has been loaded in the image on this host; inference throughput never measured here",
            ],
            "remediation": "Kevin's ruling on subject G; registry entry and CPU fetch; harness; smoke manifest; dry run and test-only; run the smoke as an orx slurm-manifest node.",
        },
        "safety": {
            "doctor": "Safety", "status": "PASS", "evaluated_on": "2026-10-10", "evaluated_by": BY,
            "pass_condition": "Safety, monitorability, data rights, and project red lines addressed",
            "evidence": "Subject R apache-2.0 (card and 2503.14456); subject G has no licence and its use is gated on Kevin's ruling (registration decision 1), with nothing redistributed under either option and an apache-2.0 fallback registered; WikiText-103 (CC BY-SA 3.0, GFDL) passages kept off the public repository; the RWKV tokenizer is vendored with ast.literal_eval instead of eval; no untrusted code executes; nothing trained or deployed; host rule respected (one read-only squeue by synthesis, empty; no job).",
            "condition": "Subject G is not fetched or run before decision 1 is made.",
            "remediation": "Decision 1 before any fetch.",
        },
    }
    for name, rec in docs.items():
        (out / f"{name}.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(len(reg), "claims;", {k: v["status"] for k, v in docs.items()})


if __name__ == "__main__":
    main()
