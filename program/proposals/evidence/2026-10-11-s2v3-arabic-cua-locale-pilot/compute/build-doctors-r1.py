#!/usr/bin/env python3
"""Write the six preflight doctor records of the S2 v3 repair run after wave 1 (doctors-r1/*.json).

The single owner's assessments, not independent reviews. The wave-1 records (doctors/) are kept as
they were. Compute stays FAIL: no derived image, no VM-lane Phase 0, no Phase 1 manifest or dry run,
no S2 model loop; an orx cpu-doctor node now exists for the Phase 0 oracle.
"""
import json
from pathlib import Path

B = Path(__file__).resolve().parents[1]
BY = "S2 v3 repair run after wave 1 (D74), single owner (Claude agent), 2026-10-11 UTC; not an independent review"
D = "2026-10-11"
P1 = "compute/pilot-r1"

docs = {
    "source": {
        "doctor": "Source", "status": "PASS", "evaluated_on": D, "evaluated_by": BY,
        "pass_condition": "Required backends reachable; cutoff and degraded coverage recorded",
        "evidence": ("orx 0.2.2 (alphaXiv keyword and embedding, OpenAlex) and the GitHub search API reachable from the development "
                     "Mac on 2026-10-11. Wave 1's retrieval (query-log.json, 91 logged records) stands; this run added 9 counted "
                     f"queries with raw-output hashes and returned ids ({P1}/queries/repair-queries.json): two Chinese-language orx "
                     "keyword queries (nothing on topic returned), an embedding query with the repaired mechanism, a placebo-perturbation "
                     "keyword query, a dated keyword query (after 2026-09-01), an OpenAlex query, and three GitHub searches (two repository "
                     "searches with no result, a code search for the direction key returning only LibreOffice forks, games and this "
                     "repository). Two full-text reads (2609.33012, 2608.25425)."),
        "degraded_coverage": ["Google Scholar, X, Reddit, Hacker News not searched", "EMNLP 2026 proceedings not yet in the Anthology",
                              "Chinese-language retrieval through orx returns off-topic results (no CJK-capable venue index)",
                              "orx 0.2.2 reports itself outdated against 0.2.18"],
        "remediation": "A RealGUINoise revision check and a citer refresh of macOSWorld before any write-up.",
    },
    "citation": {
        "doctor": "Citation", "status": "PASS", "evaluated_on": D, "evaluated_by": BY,
        "pass_condition": "URLs, dates, authors, and quantitative claims verified in primary sources",
        "protocol": "ARS claim_verification_protocol: claim registry, source tracing, cross-referencing; pilot claims tied to job records",
        "evidence": ("Claims C01-C39 as in wave 1 (two upgraded from abstract to full-text reads this run: C11 RotDroid 2608.25425 and C19 "
                     "2609.33012); C40-C52 are this run's pilot claims, each tied to a Slurm job's receipt and record (1116-1142) or to the "
                     "orx node's receipt."),
        "claims": {"full_text": ["C01", "C02", "C04", "C05", "C06", "C07", "C08", "C09", "C10", "C11", "C14", "C18", "C19"],
                   "abstract_or_metadata": ["C12", "C15", "C16", "C17", "C20", "C21"],
                   "pilot_r1": [f"C{i}" for i in range(40, 53)]},
        "remediation": "Read ITDroid in full if a delta row comes to rest on it.",
    },
    "novelty": {
        "doctor": "Novelty", "status": "PASS", "evaluated_on": D, "evaluated_by": BY,
        "pass_condition": "Synonyms, component pairs, citation graph, code, and adjacent fields searched",
        "protocol": "K-Dense literature-review (PRISMA counts); the orx rule (six or more discover queries; full reads of closest priors)",
        "evidence": ("Wave 1: frontier NO_DIRECT_PRIOR_FOUND, kill-shot STILL_OPEN, blind discrimination PASS against macOSWorld (proposal "
                     "judged the stronger contribution, same_mechanism false); the novelty refuter's 'already published' prong failed and "
                     "its recombination prong held (a judgement on the bar). This run: code search (GitHub) and Chinese-language queries "
                     "added, nothing on topic; the novelty claim is restated as a measurement on a narrower object than macOSWorld's open "
                     "split, with the placebo comparison as part of the design."),
        "caveat": "The delta is a measurement, not a method; this run's blind critic and novelty refuter re-judge it.",
        "remediation": "none before the triad",
    },
    "design": {
        "doctor": "Design", "status": "PASS", "evaluated_on": D, "evaluated_by": BY,
        "pass_condition": "Intervention, controls, falsifier, metrics, leakage, and statistics specified",
        "protocol": "K-Dense experimental-design and statistical-power; K-Dense statistical-analysis; ARS reporting standards",
        "evidence": ("Intervention: one system-layer selector file (both interface-language keys and the direction key), executed at "
                     "106 task states. Controls: en baseline; stock cell for invisibility; A/A replicates; a placebo cell (seeded toolbar "
                     "order); a tagged KeyID cell; planted controls in the application and synthetic plants; checker invariance on golds "
                     "and do-nothing states. Falsifiers P1-P8 and kill criteria K0-K9, reachable. Simulation of the registered estimators "
                     "(power-v4.py): sharp-null test corrected (0.048 at the null), census SMALL 0.97 at the null, PRESENT_HARM 0.86-0.96 at "
                     "a 15% harm, MIRROR_SPECIFIC 0.023-0.027 under direction-free scenarios. Admission by intention to treat."),
        "disclosed_limits": ["the placebo is a smaller rearrangement than mirroring (median displacement 271 px against 991 px)",
                             "MIRROR_SPECIFIC power 0.37-0.56 at a mirror-only 15% harm with n_pl = 2",
                             "the checker-invariance operationalization was chosen after the committed proxy's K0 result"],
        "remediation": "Rerun Phase 0 on the derived image with the shipped catalogs before the freeze.",
    },
    "compute": {
        "doctor": "Compute", "status": "FAIL", "evaluated_on": D, "evaluated_by": BY,
        "pass_condition": "Image digest, Slurm dry-run, seeds, quota, checkpoint, and cost plan specified",
        "evidence": ("Phase 0 in the CPU lane: Slurm 1116, 1120, 1123, 1124, 1129 (cancelled), 1131, 1132, 1139, 1140 (failed), 1141, "
                     "1142, all CPU-only with no GRES and receipts; images cotcodec-q2-lo-vm@sha256:f5b4c40e..., the metric image "
                     "sha256:2006c1a9..., the research image sha256:500f3b02... (no GPU); an orx cpu-doctor node runs the oracle over the "
                     "committed capture manifest. Phase 1: engine base digest and S1a's loop as before; cap 6.83 GPU-h (power-v4 costs); "
                     "seeds [42, 43, 44]; per-episode checkpoints as S1a."),
        "why_fail": ("No derived Arabic image (downloads wait on Kevin), no VM-lane Phase 0, no delta certification (K1), no Phase 1 manifest, "
                     "no dry run or test-only of Phase 1, no S2 model loop."),
        "remediation": ("Kevin's go-ahead for the downloads; the image-surgery script and the per-slot overlay lane change reviewed; P0.6 in "
                        "the VM lane; the Phase 1 manifest's dry run and test-only."),
    },
    "safety": {
        "doctor": "Safety", "status": "PASS", "evaluated_on": D, "evaluated_by": BY,
        "pass_condition": "Safety, monitorability, data rights, and project red lines addressed",
        "evidence": ("Unprivileged, network-less containers on public OSWorld tasks, CPU only, one of this run's jobs at a time after a "
                     "queue check; no host root, no docker-group escalation; ~/cotcodec untouched; nothing downloaded (the stand-in "
                     "catalogs are generated from strings the installed build ships; generated catalogs and screenshots stay off the "
                     "repository); no outward action; committed records scanned for host addresses."),
        "remediation": "none",
    },
}
for name, d in docs.items():
    (B / "doctors-r1" / f"{name}.json").write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n")
print("wrote", len(docs))
