#!/usr/bin/env python3
"""Build query-log.json for the S2 gauntlet (wave 1) from the discovery cells' raw outputs.

The four discovery cells of the S2 workflow (frontier, kill-shot, cross-domain,
asset) and the synthesis owner wrote their orx outputs to the session
scratchpad. This script parses every raw orx output (the JSON array after orx's
version warning) for the returned ids and hashes each raw file. Query strings
come from the cells' own logs where they kept one (frontier `queries.log`,
asset `orx/queries.log`, synthesis `queries.log`) and, for the kill-shot and
cross-domain cells, from the ordered query lists in their structured results;
the order is checked against each raw file's first returned id.

Counting convention (K1 v2 and v3, E4, C3): a counted query is one
`orx discover` call that reached its backend. Calls that failed with HTTP 429
are recorded and not counted. Paper reads, version checks, OpenReview,
Semantic Scholar, OpenAlex-API, Crossref and web searches and fetches are
recorded and not counted; the log states the total if they were.

The scratchpad is session-local, so this script reproduces the log only inside
that session; the output records every raw file's SHA-256.

Usage: python3 build-query-log.py <scratchpad-dir> <out.json>
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def orx_ids(path: Path) -> list[str] | None:
    text = path.read_text(encoding="utf-8", errors="replace")
    start = text.find("\n[")
    if start < 0:
        return None
    try:
        arr, _ = json.JSONDecoder().raw_decode(text[start + 1:])
    except json.JSONDecodeError:
        return re.findall(r'^    "id": "([^"]+)"', text, flags=re.MULTILINE)
    return [str(x.get("id")) for x in arr if isinstance(x, dict) and x.get("id")]


def row(rid, stage, tool, query, raw: Path):
    ids = orx_ids(raw)
    ok = ids is not None
    r = {"id": rid, "stage": stage, "tool": f"orx discover {tool}", "query": query,
         "returned_ids": ids if ok else [], "raw_output": f"{raw.parent.name}/{raw.name}",
         "raw_output_sha256": sha(raw), "counts_against_query_budget": ok}
    if not ok:
        r["note"] = "failed: " + raw.read_text(errors="replace").strip().splitlines()[-1][:160]
    return r


def frontier(s: Path) -> list[dict]:
    rows = []
    for line in (s / "s2-frontier/queries.log").read_text().splitlines():
        m = re.match(r"^(q\d+r?)\s+\[(keyword|embedding|openalex)\]\s+(.*)$", line, flags=re.IGNORECASE)
        if not m:
            continue
        tag, tool, query = m.group(1).lower(), m.group(2), m.group(3)
        raw = s / f"s2-frontier/{tag}.txt"
        if raw.is_file():
            rows.append(row(f"FR-{tag}", "cell:frontier", tool, query, raw))
    return rows


KILLSHOT = [
    ("keyword", "right-to-left GUI agent mirrored layout", "2608.09654"),
    ("keyword", "Arabic GUI agent benchmark", "2609.00048"),
    ("keyword", "Arabic glyphs mirrored UI layout", "2610.10374"),
    ("embedding", "Disentangling Arabic script from right-to-left mirrored layout in multilingual computer-use agents: Arabic strings in a left-to-right layout versus a mirrored RTL interface with identical structure", "2610.11510"),
    ("embedding", "multilingual GUI agent benchmark with localized interfaces in Arabic and other right-to-left languages", "2609.34139"),
    ("openalex", "right-to-left user interface GUI agent Arabic", "10.52202/085713-4468"),
    ("keyword", "macOSWorld multilingual interactive benchmark GUI agents", "2506.04135"),
    ("keyword", "MPR-GUI multilingual perception reasoning GUI agents", "2512.00756"),
    ("keyword", "Skill Issue are skills language-invariant", "2608.25832"),
    ("keyword", "cross-lingual policy retention tool-using agents", "2608.11110"),
    ("keyword", "RTL right-to-left web agent Arabic Hebrew interface", "2609.28565"),
    ("keyword", "UI language localization computer-use agent Arabic RTL", "2607.28227"),
    ("embedding", "GUI agents performance drops on right-to-left Arabic interfaces; controlled study of layout direction [--published-before 2026-01-01]", "2512.00756"),
    ("openalex", "Arabic web agent benchmark multilingual GUI", "10.52202/085713-4468"),
    ("keyword", "mirrored interface right-to-left grounding screenshot", "2608.26991"),
    ("keyword", "UI language swap robustness web agent perturbation localization", "2609.13287"),
    ("keyword", "multilingual GUI grounding benchmark Arabic screenshots", "2610.05185"),
    ("embedding", "controlled ablation of interface language and layout direction for vision-language web agents on an identical synthetic web application [--published-after 2026-01-01]", "2610.10178"),
    ("keyword", "X-WebAgentBench multilingual interactive web benchmark", "2505.15372"),
    ("keyword", "BabelArena multilingual benchmark LLM agents", "2609.23490"),
    ("keyword", "pseudo-localization internationalization testing GUI", "2608.25425"),
    ("openalex", "right-to-left layout mirroring internationalization bugs mobile apps", "W3015266663"),
    ("keyword", "Arabic mobile GUI agent AndroidWorld multilingual", "2609.30186"),
    ("keyword", "Hebrew Persian right-to-left screenshot agent", "2609.28565"),
    ("keyword", "OSWorld multilingual localized desktop Arabic", "2606.21654"),
    ("embedding", "Does the language of the user interface affect GUI agent grounding? multilingual screenshot grounding with translated UI text including Arabic", "2608.25832"),
    ("keyword", "dir=rtl", "2609.25335"),
    ("openalex", "multilingual GUI agent benchmark right-to-left", "10.52202/085713-4468"),
    ("keyword", "Arabic OCR benchmark vision-language models Qwen", "2608.22366"),
    ("keyword", "KITAB-Bench Arabic OCR document understanding", "2608.22366"),
    ("embedding", "Arabic scene text and screenshot text recognition ability of open multimodal models Qwen-VL", "2609.20064"),
    ("keyword", "element ordering LM agent performance", "2609.36086"),
    ("keyword", "GUI agent robustness perturbation horizontal flip layout language change", "2608.09654"),
]

CROSS = [
    ("openalex", "internationalization presentation failures web applications detection", "10.1145/3468264.3468581"),
    ("openalex", "right-to-left user interface mirroring Arabic users usability", "10.1201/9781003715764"),
    ("openalex", "treating stimuli as a random factor statistical power participants stimuli", "10.1146/annurev-psych-122414-033702"),
    ("openalex", "language-as-fixed-effect fallacy", "10.1016/s0022-5371(73)80014-3"),
    ("openalex", "reading direction spatial bias Arabic readers inhibition of return", "10.3758/s13421-012-0285-2"),
    ("keyword", "Adding Error Bars to Evals clustered standard errors paired differences", "2608.22659"),
    ("openalex", "Detecting and localizing internationalization presentation failures in web applications", "10.1109/icst.2016.36"),
    ("openalex", "pseudo-localization software testing", "10.17513/snt.37070"),
    ("openalex", "bootstrap-based improvements for inference with clustered errors few clusters wild bootstrap", "10.2139/ssrn.956890"),
    ("openalex", "equivalence testing for psychological research tutorial smallest effect size of interest", "10.1177/2515245918770963"),
    ("embedding", "vision-language model GUI agent performance changes when the interface layout is horizontally mirrored right-to-left, separating text script from layout direction", "2610.07972"),
    ("keyword", "horizontal flip positional bias GUI grounding screenshot", "2610.05185"),
    ("openalex", "Statistical power and optimal design in experiments in which samples of participants respond to samples of stimuli", "10.1037/xge0000014"),
    ("openalex", "information scent label goal similarity link selection cognitive walkthrough for the web", "W39604414"),
    ("openalex", "metamorphic testing review challenges opportunities", "10.1145/3143561"),
    ("openalex", "Arabic font size legibility reading speed screen", "10.1088/1742-6596/364/1/012115"),
    ("keyword", "right-to-left Arabic GUI agent mirrored interface", "2610.01215"),
    ("openalex", "cluster-robust variance small sample correction CR2 Bell McCaffrey few clusters", "10.3758/s13428-021-01627-0"),
    ("openalex", "blinded sample size re-estimation internal pilot type I error", None),
    ("openalex", "role of internal pilot studies in increasing the efficiency of clinical trials", None),
    ("keyword", "Arabic OCR vision-language model dots diacritics low resolution benchmark", "2608.22366"),
    ("openalex", "A/A test online controlled experiments trustworthy pitfalls", None),
    ("openalex", "negative controls epidemiology detecting confounding bias", None),
    ("keyword", "pseudo-localization pseudolocale agent evaluation", "2609.34320"),
    ("keyword", "force RTL layout direction mirrored English", "2609.25335"),
]


def ordered(s: Path, cell_dir: str, stage: str, prefix: str, spec) -> list[dict]:
    rows = []
    for i, (tool, query, first) in enumerate(spec, 1):
        raw = s / f"{cell_dir}/q{i:02d}.txt"
        r = row(f"{prefix}-q{i:02d}", stage, tool, query, raw)
        got = r["returned_ids"][0] if r["returned_ids"] else None
        if got != first:
            raise SystemExit(f"order check failed for {raw}: expected first id {first}, got {got}")
        rows.append(r)
    return rows


def asset(s: Path) -> list[dict]:
    rows = []
    for line in (s / "s2-asset/orx/queries.log").read_text().splitlines():
        m = re.match(r"^(q\d+):\s+(keyword|embedding|openalex)\s+(.*?)\s+->\s+exit\s+(\d+)$", line)
        if m:
            raw = s / f"s2-asset/orx/{m.group(1)}.txt"
            rows.append(row(f"AS-{m.group(1)}", "cell:asset", m.group(2), m.group(3), raw))
    return sorted(rows, key=lambda r: r["id"])


def synthesis(s: Path) -> list[dict]:
    rows = []
    for line in (s / "s2-synth/queries.log").read_text().splitlines():
        tag, tool, query = line.split("\t")
        rows.append(row(f"SY-{tag}", "synthesis", tool, query, s / f"s2-synth/{tag}.txt"))
    return rows


def other(s: Path) -> list[dict]:
    """Non-orx searches and fetches as reported by the cells (not counted)."""
    out = []
    def add(rid, stage, tool, query, ids, raw=None, note=None, calls=1):
        r = {"id": rid, "stage": stage, "tool": tool, "query": query, "returned_ids": ids, "calls": calls,
             "counts_against_query_budget": False}
        if raw is not None and raw.is_file():
            r["raw_output"] = f"{raw.parent.name}/{raw.name}"; r["raw_output_sha256"] = sha(raw)
        if note:
            r["note"] = note
        out.append(r)
    f = s / "s2-frontier"
    for i, (fname, term) in enumerate([("or_right-to-left_GUI_agent.json", "right-to-left GUI agent"),
                                        ("or_Arabic_GUI_agent.json", "Arabic GUI agent"),
                                        ("or_mirrored_layout_agent.json", "mirrored layout agent"),
                                        ("or_multilingual_computer-use_agent.json", "multilingual computer-use agent"),
                                        ("or2_multilingual_GUI_agent.json", "multilingual GUI agent (2026+ filter)"),
                                        ("or2_GUI_agent_language_interface_localization.json", "GUI agent language interface localization (2026+ filter)"),
                                        ("or2_Arabic_interface_agent_screenshot.json", "Arabic interface agent screenshot (2026+ filter)")], 1):
        raw = f / fname
        ids = []
        try:
            ids = [n.get("id") for n in json.loads(raw.read_text()).get("notes", [])][:25]
        except Exception:  # noqa: BLE001
            pass
        add(f"FR-OR{i}", "cell:frontier", "OpenReview API notes/search", term, ids, raw)
    add("FR-OR8", "cell:frontier", "OpenReview API notes?id", "gD64I8FOzS irjWqxKeHm 0H5Im3Xvuf (direct fetch)", [],
        note="403 browser challenge; abstracts taken from search results")
    add("FR-OA1", "cell:frontier", "OpenAlex API", "works?search=macOSWorld multilingual interactive benchmark",
        ["W4416131189", "W7163893052", "W7161827071", "W7166665335", "W7156939280"])
    add("FR-OA2", "cell:frontier", "OpenAlex API", "works?filter=fulltext.search:macOSWorld (27 works)", [], f / "oa26.json")
    for j, term in enumerate(["GUI agent multilingual", "web agent multilingual benchmark",
                              "right-to-left Arabic interface vision language", "Arabic GUI screenshot"], 3):
        add(f"FR-OA{j}", "cell:frontier", "OpenAlex API (2025-2026, ACL DOI subset)", term, [],
            f / f"oaacl_{term.replace(' ', '_')}.json", note="failed: OpenAlex daily budget exhausted for this IP")
    add("FR-S2C1", "cell:frontier", "Semantic Scholar API via host (read-only ssh)", "citations of arXiv:2506.04135 (34 citing papers)", [], f / "s2_macosworld_cites.json")
    add("FR-S2C2", "cell:frontier", "Semantic Scholar API via host", "citations of arXiv:2512.00756, 2608.25832, 2608.11110", [], f / "s2_cites3.txt", calls=3)
    add("FR-S2S", "cell:frontier", "Semantic Scholar API search via host", "5 searches + 1 retry (right-to-left GUI agent; Arabic GUI agent benchmark; mirrored layout RTL vision language model; multilingual web agent benchmark localized interface; RTL user interface multimodal agent; Arabic mirrored GUI agent right-to-left)", [], f / "s2_search5.txt", note="all returned HTTP 429", calls=6)
    add("FR-ARX", "cell:frontier", "export.arxiv.org abs pages", "version check 2506.04135 2512.00756 2608.25832 2608.11110 2610.03136",
        ["2506.04135v4", "2512.00756v2", "2608.25832v1", "2608.11110v2", "2610.03136v1"], calls=5)
    k = s / "s2kill"
    for i, (fname, term) in enumerate([("or_right-to-left_GUI_agent.json", "right-to-left GUI agent"), ("or_Arabic_GUI_agent.json", "Arabic GUI agent"),
                                        ("or_mirrored_layout_agent.json", "mirrored layout agent"), ("or_multilingual_computer-use_agent.json", "multilingual computer-use agent")], 1):
        raw = k / fname
        ids = []
        try:
            ids = [n.get("id") for n in json.loads(raw.read_text()).get("notes", [])][:25]
        except Exception:  # noqa: BLE001
            pass
        add(f"KS-OR{i}", "cell:killshot", "OpenReview api2 notes/search", term, ids, raw)
    add("KS-WS1", "cell:killshot", "WebSearch", "GUI agent right-to-left Arabic mirrored layout benchmark computer-use 2026",
        ["2506.04135", "openreview:YJxGJP8feU", "2607.26041", "2606.29537", "2606.09426", "2608.15930", "2605.07110"])
    add("KS-WS2", "cell:killshot", "WebSearch", "aclanthology Arabic GUI agent screenshot right-to-left interface evaluation", ["2508.17378"])
    add("KS-WS3", "cell:killshot", "WebSearch", "\"right-to-left\" web agent OR \"GUI agent\" layout mirroring ablation Arabic text left-to-right layout arXiv",
        ["2607.24571", "m2.material.io/design/usability/bidirectionality"])
    add("KS-WF1", "cell:killshot", "WebFetch", "huggingface.co/Qwen/Qwen3.5-9B model card", ["Qwen/Qwen3.5-9B"])
    add("KS-WF2", "cell:killshot", "WebFetch", "github.com/QwenLM/Qwen3-VL README", ["QwenLM/Qwen3-VL"])
    add("XD-CR", "cell:cross-domain", "Crossref API (11 lookups)", "metadata verification for Wittes & Brittain 1990, Kieser & Friede 2003, Lipsitch 2010, Cameron et al. 2008, Pustejovsky & Tipton, Lakens 2018, Chen 2018, Clark 1973, Alameer GWALI, Collins et al. 2009, Arabic mirrored UI usability",
        ["10.1002/sim.4780090113", "10.1002/sim.1585", "10.1097/EDE.0b013e3181d61eeb", "10.1162/rest.90.3.414", "10.1080/07350015.2016.1247004",
         "10.1177/2515245918770963", "10.1145/3143561", "10.1016/s0022-5371(73)80014-3", "10.1109/icst.2018.00030", "10.1037/a0015826"], calls=11)
    add("XD-WF", "cell:cross-domain", "WebFetch / WebSearch (13)", "Android pseudolocales; Microsoft pseudolocalization; Firefox Fluent bidi; Firefox RTL guidelines; Android Force RTL; W3C qa-html-dir; W3C css-logical-1; Material and Apple HIG (unreadable); ACM 10.1145/3759155 (403); Nature srep18248 (redirect); Ajou thesis (unreadable); RTL usability web search",
        ["developer.android.com/guide/topics/resources/pseudolocales", "learn.microsoft.com/globalization/methodology/pseudolocalization",
         "firefox-source-docs.mozilla.org/l10n/fluent/tutorial.html", "firefox-source-docs.mozilla.org/code-quality/coding-style/rtl_guidelines.html",
         "developer.android.com/training/basics/supporting-devices/languages", "w3.org/International/questions/qa-html-dir", "w3.org/TR/css-logical-1"], calls=13)
    add("XD-SRC", "cell:cross-domain", "curl (source code)", "LibreOffice core vcl/source/app/settings.cxx and Common.xcs at 08f5d410; Chromium base_i18n_switches.cc; GWALI author PDF",
        ["LibreOffice/core@08f5d410a474badedeaa3fbabaea9b6f564d1b83"], s / "s2xd/lo_settings.cxx", calls=3)
    return out


READS = {
    "cell:frontier": ["2506.04135", "2512.00756", "2608.25832", "2608.11110", "2609.35026", "2609.35814", "2609.32036", "2512.18231",
                      "2505.15372", "2609.38184", "2604.16385", "2605.25707", "2604.14262", "2607.04120"],
    "cell:killshot": ["2506.04135", "2512.00756", "2608.25832", "2608.11110", "2505.15372", "2609.35026", "2609.23490", "2609.01056",
                      "2608.08775", "2607.06008", "2608.21832", "2608.12333", "2609.38184", "2502.14949", "2604.12978", "2508.17378",
                      "2608.21794 (report)", "2608.21832 (report)", "2608.12333 (report)", "2609.34139 (report)"],
    "cell:cross-domain": ["2411.00640", "2512.21326", "2609.35583", "2609.28565", "2609.32036", "2610.00651", "2603.11759 (report)",
                          "10.1037/xge0000014 (OpenAlex metadata)", "10.1109/icst.2016.36 (OpenAlex metadata; author PDF read)",
                          "10.1146/annurev-psych-122414-033702 (metadata)", "10.1038/srep18248 (metadata)", "10.1145/3759155 (metadata)",
                          "10.1109/vis55277.2024.00058 (metadata)", "W2590195251 (metadata)"],
    "cell:asset": [],
    "synthesis": ["2506.04135 (re-read of the frontier cell's orx full text: Secs. 3.2-3.4, 4.1-4.2, 5.1-5.3, Tables 3-4, App. D.1 Tables 6-7, App. Fig. 19 text, checklist item 7)"],
}


def main() -> int:
    s, out = Path(sys.argv[1]), Path(sys.argv[2])
    counted = frontier(s) + ordered(s, "s2kill", "cell:killshot", "KS", KILLSHOT) + \
        ordered(s, "s2xd", "cell:cross-domain", "XD", CROSS) + asset(s) + synthesis(s)
    oth = other(s)
    by_stage: dict[str, int] = {}
    failed: dict[str, int] = {}
    for r in counted:
        key = "counted_by_stage" if r["counts_against_query_budget"] else "failed_by_stage"
        d = by_stage if r["counts_against_query_budget"] else failed
        d[r["stage"]] = d.get(r["stage"], 0) + 1
    total = sum(by_stage.values())
    oth_by: dict[str, int] = {}
    for r in oth:
        oth_by[r["stage"]] = oth_by.get(r["stage"], 0) + r["calls"]
    log = {
        "gauntlet": "s2-arabic-cua-locale wave 1 (D67)",
        "built_on": "2026-10-10",
        "counting_convention": "a counted query is one orx discover call that reached its backend; 429 failures, paper reads, version checks and non-orx searches and fetches are recorded and not counted",
        "queries_against_budget": {
            "declared": 150, "reserve_for_refuters": 30, "counted_by_stage": by_stage, "counted_total": total,
            "remaining_under_declared": 150 - total, "reserve_intact": 150 - total >= 30,
            "orx_calls_failed_429_by_stage": failed,
            "uncounted_other_searches_and_fetches_by_stage": oth_by,
            "total_if_other_searches_counted": total + sum(oth_by.values()),
        },
        "orx_discover": counted,
        "other_searches_and_fetches": oth,
        "paper_reads": READS,
        "cell_verdicts": {
            "cell:frontier": "NARROWED (residual STILL_OPEN): no direct prior through 2026-10-10 for an oracle-aligned within-environment split of an executable GUI agent's Arabic drop into text and mirroring; macOSWorld v4 still leaves the split open; RealGUINoise, WebPageBench and BreakingWeb narrow it",
            "cell:killshot": "NARROWED on novelty (split STILL_OPEN); KILL for Phase 1 as the dossier designed it (power gate fails by construction at 18 tasks); four further defects (oracle gate blind to half-mirrored layouts, identification of the 'glyph' contrast, weak treatment, missing Relay inputs and transport)",
            "cell:cross-domain": "Phase 0 worthwhile with gate additions; Phase 1 as written is underpowered; add en-RTL (2x2), layout-graph gate, render-level A/A in place of the a11y arm, OCR round trip, logical CSS, pinned Arabic font and numerals, dir=auto; moderators for position, direction-sensitive steps and lexical overlap; paired t or sign-flip at few clusters; TOST before any null; staged design with variance re-estimation; LibreOffice 2x2 as a concrete route to more tasks",
            "cell:asset": "Relay is a separate public MIT repo (HEAD e6c815e), its English oracle passes 18 of 18 tasks on seeds 42 and 43 (91 node tests, 27 + 14 browser recipes); i18n extraction is about 150-200 keys; Q2 certification (D53) does not transfer; no local-engine path, no Node or Chromium image on the host; dossier design detects 7.3-12.6 pp; recommends a Relay English noise-floor pilot of about 1 GPU-h first",
        },
    }
    out.write_text(json.dumps(log, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(log["queries_against_budget"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
