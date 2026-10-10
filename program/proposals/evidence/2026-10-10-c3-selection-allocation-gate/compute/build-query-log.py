#!/usr/bin/env python3
"""Build query-log.json for the C3 gate gauntlet from the discovery cells' raw logs.

The four discovery cells of workflow gauntlet-c3-wave1 (frontier, kill-shot,
cross-domain, asset) wrote their orx outputs to the session scratchpad. This
script parses every raw orx output (the JSON array after orx's version warning)
for the returned ids, hashes each raw file, and adds the cells' non-orx searches
(OpenReview API, web search restricted to aclanthology.org or openreview.net,
OpenAlex API) and paper reads as reported in the cells' structured results.
Counting convention (K1 v2 and v3, E4): a counted query is one `orx discover`
call that reached its backend; paper reads, version checks, OpenReview and web
searches and fetches are recorded and not counted, and the log states what the
total would be if they were counted.

The scratchpad is session-local, so this script reproduces the log only inside
that session; the output records every raw file's SHA-256.

Usage: python build-query-log.py <scratchpad-dir> <out.json>
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def orx_ids(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    start = text.find("[")
    if start < 0:
        return []
    try:
        arr = json.loads(text[start:])
    except json.JSONDecodeError:
        end = text.rfind("]")
        arr = json.loads(text[start:end + 1])
    return [str(x.get("id")) for x in arr if isinstance(x, dict) and x.get("id")]


def frontier(s: Path) -> list[dict]:
    rows = []
    for line in (s / "c3scout/querylog.tsv").read_text().splitlines():
        n, strat, query, args, _ = (line.split("\t") + [""] * 5)[:5]
        raw = s / f"c3scout/out/q{n}.txt"
        rows.append({"id": f"FR-{int(n):02d}", "stage": "cell:frontier", "tool": f"orx discover {strat}",
                     "query": query + (f" [{args}]" if args else ""), "returned_ids": orx_ids(raw),
                     "raw_output_sha256": sha(raw), "counts_against_query_budget": True})
    return sorted(rows, key=lambda r: r["id"])


def killshot(s: Path) -> list[dict]:
    rows = []
    for line in (s / "c3-killshot/queries.tsv").read_text().splitlines():
        tag, strat, query, args = (line.split("\t") + [""] * 4)[:4]
        raw = s / f"c3-killshot/{tag}.out"
        if raw.is_file():
            ids, digest, note = orx_ids(raw), sha(raw), None
        else:
            ids, digest = ["2508.15260", "2606.31484", "2602.13517"], None
            note = "raw output not saved; ids from the cell's structured result (inline K0)"
        row = {"id": f"KS-{tag}", "stage": "cell:killshot", "tool": f"orx discover {strat}",
               "query": query + (f" [{args}]" if args else ""), "returned_ids": ids,
               "raw_output_sha256": digest, "counts_against_query_budget": True}
        if note:
            row["note"] = note
        rows.append(row)
    return rows


def crossdomain(s: Path) -> tuple[list[dict], list[dict], list[str]]:
    rows, other, reads = [], [], []
    for line in (s / "c3-xdomain/querylog.txt").read_text().splitlines():
        parts = line.split("|")
        if parts[0] == "paper":
            reads.append(f"{parts[1]} ({parts[2]})")
            continue
        if parts[0] == "openreview":
            continue
        n, kind, query, args = (parts + [""] * 4)[:4]
        raw = s / f"c3-xdomain/q{int(n):02d}.txt"
        if raw.is_file():
            ids, digest, note = orx_ids(raw), sha(raw), None
        else:
            ids, digest = ["2610.09239", "2606.08419"], None
            note = "raw output file q00.txt absent; ids from the cell's structured result"
        row = {"id": f"XD-{int(n):02d}", "stage": "cell:cross-domain", "tool": f"orx discover {kind}",
               "query": query + (f" [{args}]" if args else ""), "returned_ids": ids,
               "raw_output_sha256": digest, "counts_against_query_budget": True}
        if note:
            row["note"] = note
        rows.append(row)
    for i, name in enumerate(("or_47", "or_48", "or_49")):
        raw = s / f"c3-xdomain/{name}.json"
        notes = json.loads(raw.read_text()).get("notes", [])
        other.append({"id": f"XD-OR{i + 1}", "stage": "cell:cross-domain", "tool": "OpenReview API notes/search",
                      "query": ["adaptive sampling test-time compute allocation held-out",
                                "hidden state probe answer selection grouped cross-validation",
                                "wall-clock cost test-time scaling batching"][i],
                      "returned_ids": [n.get("id") for n in notes][:15], "raw_output_sha256": sha(raw),
                      "counts_against_query_budget": False})
    return sorted(rows, key=lambda r: r["id"]), other, reads


def asset(s: Path) -> tuple[list[dict], list[dict]]:
    rows, other = [], []
    blocks: list[tuple[str, list[str]]] = []
    for path in (s / "c3-asset/q-len-1.txt", s / "c3-asset/querylog.txt"):
        text = path.read_text(encoding="utf-8", errors="replace")
        if path.name == "q-len-1.txt":
            for chunk in text.split("### ")[1:]:
                header, body = chunk.split("\n", 1)
                blocks.append((header.strip(), orx_ids_from_text(body), sha(path)))
            continue
        for chunk in text.split("### ")[1:]:
            header, body = chunk.split("\n", 1)
            ids = [ln.split("|")[0].strip() for ln in body.splitlines() if "|" in ln]
            blocks.append((header.strip(), ids, sha(path)))
    k = 0
    for header, ids, digest in blocks:
        mode, query = header.split(":", 1)
        mode = mode.strip()
        if mode in {"keyword", "embedding", "openalex"}:
            k += 1
            rows.append({"id": f"AS-{k:02d}", "stage": "cell:asset", "tool": f"orx discover {mode}",
                         "query": query.strip(), "returned_ids": ids, "raw_output_sha256": digest,
                         "counts_against_query_budget": True})
        else:
            other.append({"id": f"AS-X{len(other) + 1}", "stage": "cell:asset",
                          "tool": "OpenReview API notes/search" if mode == "openreview" else "OpenAlex API (venue filter)",
                          "query": query.strip(), "returned_ids": ids, "raw_output_sha256": digest,
                          "counts_against_query_budget": False})
    return rows, other


def orx_ids_from_text(body: str) -> list[str]:
    start = body.find("[")
    if start < 0:
        return []
    try:
        arr, _ = json.JSONDecoder().raw_decode(body[start:])
    except json.JSONDecodeError:
        # the asset cell saved this output truncated; fall back to the top-level "id" lines
        return re.findall(r'^    "id": "([^"]+)"', body, flags=re.MULTILINE)
    return [str(x.get("id")) for x in arr if isinstance(x, dict) and x.get("id")]


def frontier_openreview(s: Path) -> list[dict]:
    terms = ["adaptive test-time compute allocation verifier", "hidden state answer selection reasoning",
             "test-time budget allocation out-of-sample", "verifier adaptive sampling selection allocation interaction",
             "compute-matched wall-clock test-time scaling reasoning", "learned answer selector re-sampling reasoning models"]
    out = []
    for i, term in enumerate(terms, 1):
        raw = s / ("c3scout/out/or_" + "".join(ch for ch in term.replace(" ", "_") if ch.isalnum() or ch in "_-") + ".json")
        notes = json.loads(raw.read_text()).get("notes", [])
        out.append({"id": f"FR-OR{i}", "stage": "cell:frontier", "tool": "OpenReview API notes/search", "query": term,
                    "returned_ids": [n.get("id") for n in notes], "raw_output_sha256": sha(raw),
                    "counts_against_query_budget": False})
    return out


MANUAL_OTHER = [
    {"id": "FR-WS1", "stage": "cell:frontier", "tool": "WebSearch",
     "query": "openreview adaptive test-time compute allocation learned verifier selection interaction reasoning models 2026",
     "returned_ids": ["2602.01070", "2602.03975", "icml.cc/virtual/2026/poster/60797", "proceedings.mlr.press/v306/bilal26a"]},
    {"id": "FR-WS2", "stage": "cell:frontier", "tool": "WebSearch",
     "query": "aclanthology.org 2026 hidden state probe answer selection self-consistency adaptive sampling budget",
     "returned_ids": ["2026.findings-acl.1085", "2608.24590", "2605.26849", "2601.02970", "2026.acl-srw.89", "2025.findings-naacl.383"]},
    {"id": "FR-WS3", "stage": "cell:frontier", "tool": "WebSearch",
     "query": "openreview.net forum 2026 test-time budget allocation verifier out-of-sample OR held-out reasoning LLM selection allocation",
     "returned_ids": ["2602.03975", "2602.01070", "icml.cc/virtual/2026/77873", "2606.19808"]},
    {"id": "FR-WS4", "stage": "cell:frontier", "tool": "WebSearch",
     "query": "Reliability-Aware Adaptive Self-Consistency ReASC confidence stopping ACL 2026 Qwen3",
     "returned_ids": ["2026.findings-acl.1085", "2601.02970"]},
    {"id": "KS-WS1", "stage": "cell:killshot", "tool": "WebSearch (site:openreview.net)",
     "query": "openreview hidden-state probe answer selection adaptive sampling allocation reasoning model matched compute 2026",
     "returned_ids": ["UD4Rw8MOEK", "ztGHhyicWs", "2506.23274", "rysYQ9KGgV", "2604.21018", "2605.31561", "2606.22864", "2601.09093", "2608.03961"]},
    {"id": "KS-WS2", "stage": "cell:killshot", "tool": "WebSearch (site:aclanthology.org)",
     "query": "aclanthology 2026 adaptive self-consistency probe difficulty allocation reasoning models selection verifier",
     "returned_ids": ["2026.findings-acl.1085", "2026.findings-acl.622", "2026.acl-long.2190", "2608.27964", "2025.findings-naacl.383", "2605.26849", "2605.17609", "2606.00532"]},
    {"id": "XD-WS1", "stage": "cell:cross-domain", "tool": "WebSearch (allowed_domains aclanthology.org)",
     "query": "hidden state probe correctness answer selection question-grouped split leakage",
     "returned_ids": ["2025.emnlp-main.411", "2605.31561", "2606.14530", "2025.findings-emnlp.880", "2025.findings-naacl.181", "2608.07528", "2025.acl-long.880", "2607.18553"]},
    {"id": "XD-WS2", "stage": "cell:cross-domain", "tool": "WebSearch (allowed_domains aclanthology.org)",
     "query": "adaptive test-time compute allocation per-question sampling budget LLM reasoning",
     "returned_ids": ["2605.26849", "2608.03961", "2602.16745", "2604.14853", "2025.emnlp-main.1638", "2604.21018", "2026.findings-acl.1124", "2505.20643", "2503.24377"]},
    {"id": "XD-WS3", "stage": "cell:cross-domain", "tool": "WebSearch (allowed_domains aclanthology.org)",
     "query": "efficiency evaluation wall-clock latency versus token count reporting LLM inference cost",
     "returned_ids": ["2509.25835", "2025.emnlp-main.618", "2602.08948", "2025.emnlp-industry.186", "2511.05722", "2025.emnlp-main.1705", "2025.findings-emnlp.1402", "2605.11733"]},
    {"id": "XD-WS4", "stage": "cell:cross-domain", "tool": "WebSearch",
     "query": "Gelman \"16 times the sample size\" interaction main effect",
     "returned_ids": ["statmodeling.stat.columbia.edu/2018/03/15/need16/", "statmodeling.stat.columbia.edu/2023/11/09/", "2604.08421"]},
]
MANUAL_FETCH_FAILURES = [
    {"stage": "cell:cross-domain", "tool": "WebFetch", "target": "statmodeling.stat.columbia.edu 2018 need-16 post", "result": "HTTP 403, not retrieved"},
    {"stage": "cell:frontier", "tool": "WebFetch", "target": "openreview.net/pdf?id=X7X1K0xfZe; openreview.net/forum?id=SId4cvKz6D", "result": "bot-check page; not bypassed"},
    {"stage": "cell:frontier", "tool": "OpenReview API notes?id=", "target": "RJtxGvLeYP, X7X1K0xfZe, BLOx9TYfgl, SId4cvKz6D, XfNsXlvV7S", "result": "ChallengeRequiredError (HTTP 403)"},
]
CELL_VERDICTS = {
    "cell:frontier": "NARROWED, further than the dossier; not OCCUPIED. HSRM and TrajSelector cover most of the thinking-mode selector residual; DeepConf, MARS, ReASC, ZIP-RC, Tracing the Traces and SANE cover the shared-signal recipe under token or sample accounting; no Bae replication in LLMs found; probe v2 measured a different model, so the 6 GPU-h estimate is unmeasured.",
    "cell:killshot": "NARROWED, not OCCUPIED; the Stage-0 gate as the dossier wrote it cannot be decisive: the spread share is non-monotone in true heterogeneity, pooled decodability is trivially high and CASE's 0.60 was fitted on non-thinking models, the full 2x2's likely answer is predicted by 2609.32035 and 2609.33290, the GPU-second residual faces a tokens-versus-serving-settings dilemma, and an informative pool likely exceeds 8 GPU-h. Repairs: noise-corrected spread, a decision-level gate with length and question-only baselines and at least 80 mixed held-out questions, and a measured Qwen3-8B throughput.",
    "cell:cross-domain": "NARROWED; methods outside LLM test-time scaling are classical. Gate changes: deconvolved or identified spread with family-clustered intervals; layer and C chosen inside training families by grouped log loss; an output-only floor; family-level CIs; a cross-question signal measure; whole-job GPU-seconds with concurrency sweeps; a power gate for the 2x2; replay of stored i.i.d. streams is unbiased for accuracy.",
    "cell:asset": "No novelty verdict. Recommends Qwen3-8B (Apache-2.0, revision b968826d; weights not on the host), math-first data with ids and hashes only in the public repository, 6 draws for every question, a P0 pilot, and caps under 8 GPU-h only up to a mean thinking length of about 6.6k tokens for 800 questions; Qwen3.5-9B as a fallback under a new registration.",
}
PAPER_READS = {
    "cell:frontier": "orx paper --full on 47 papers (the cell lists 43 ids: 2608.03961 2607.17531 2609.13257 2608.13087 2609.27917 2608.17124 2606.19808 2410.04707 2604.14853 2512.01457 2610.08719 2610.02808 2610.04512 2609.33290 2609.14500 2609.40190 2608.20256 2608.07968 2610.01110 2609.14995 2605.17609 2609.37700 2608.04001 2609.29664 2609.19671 2609.38699 2606.27288 2608.25937 2508.15260 2510.10494 2510.16449 2504.05419 2608.30841 2606.31484 2608.16425 2607.08665 2609.18126 2604.05868 2608.27046 2609.19499 2606.12935 2606.28661 2608.18931); export.arxiv.org version checks on the 10 dossier priors",
    "cell:killshot": "orx paper --full on 17: 2609.32035 2609.33290 2608.17124 2512.01457 2508.15260 2608.11403 2609.19499 2608.03961 2607.17531 2609.13257 2608.13087 2609.27917 2601.21619 2609.34864 2410.04707 2606.12935 2601.09093",
    "cell:asset": "orx paper --full on 8: 2608.17124 2610.05685 2505.09388 2609.27917 2504.05419 2609.37700 2608.03961 2609.13257; skims 2606.00206 2607.21433; HF API model, dataset and licence reads; read-only ssh to the host",
}


def main() -> int:
    s, out = Path(sys.argv[1]), Path(sys.argv[2])
    fr = frontier(s)
    ks = killshot(s)
    xd, xd_other, xd_reads = crossdomain(s)
    asr, as_other = asset(s)
    counted = fr + ks + xd + asr
    other = frontier_openreview(s) + xd_other + as_other + [dict(r, counts_against_query_budget=False) for r in MANUAL_OTHER]
    by_stage = {"cell:frontier": len(fr), "cell:killshot": len(ks), "cell:cross-domain": len(xd), "cell:asset": len(asr),
                "synthesis": 0}
    other_by_stage: dict[str, int] = {}
    for r in other:
        other_by_stage[r["stage"]] = other_by_stage.get(r["stage"], 0) + 1
    total = sum(by_stage.values())
    log = {
        "schema": "c3-gauntlet-query-log-v1",
        "workflow": "gauntlet-c3-wave1 (discovery cells, then single-owner synthesis)",
        "source_cutoff": "2026-10-10",
        "convention": "A counted query is one orx discover call that reached its backend (K1 v2 and v3, E4). Paper reads, version checks, OpenReview and web searches, OpenAlex API calls and fetches are recorded here and not counted.",
        "queries_against_budget": {"declared": 150, "reserve_for_refuters": 30, "counted_by_stage": by_stage,
                                   "counted_total": total, "remaining_under_declared": 150 - total,
                                   "reservation_breached_by": max(0, total + 30 - 150),
                                   "uncounted_other_searches_by_stage": other_by_stage,
                                   "total_if_other_searches_counted": total + len(other)},
        "budget_note": "The four cells spent 127 counted queries before synthesis, leaving 23 of the 150; the triad's reserve of at least 30 was already breached by 7. Synthesis therefore made no orx discover call and read only full texts the cells had already fetched. If the 24 OpenReview, web and OpenAlex API searches were counted, the cells alone would total 151.",
        "orx_client": "orx 0.2.2 (reports itself outdated against 0.2.18)",
        "cell_verdicts_summary": CELL_VERDICTS,
        "counted": counted,
        "other_searches_not_counted": other,
        "fetch_failures": MANUAL_FETCH_FAILURES,
        "paper_reads_not_counted": {**PAPER_READS, "cell:cross-domain": "orx paper: " + "; ".join(xd_reads),
                                    "synthesis": "re-read by targeted section, from the cells' saved full texts (no new retrieval): 2608.17124 (Secs. 3.1-3.5, 4 Props. 1-2, 6.4, 6.7, Table 6), 2609.32035 (abstract, Sec. 3, Table 1, Table 13, Sec. 8), 2608.30841 (Secs. 4.1-4.4, 6.6, Table 2), 2608.03961 (abstract, Sec. 5), 2609.33290 (Sec. 3.3), 2510.16449 (abstract, Sec. 4, main table), 2610.05685 (Tables 10, 11, 13)"},
        "prisma_synthesis": {"identified": 0, "screened": 0, "full_texts_re_read": 7, "included_as_direct_prior": 0,
                             "note": "synthesis added no new retrieval; the cells' approximate counts: frontier ~640 unique ids identified, ~110 screened, 47 full texts, 33 cited"},
    }
    out.write_text(json.dumps(log, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(log["queries_against_budget"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
