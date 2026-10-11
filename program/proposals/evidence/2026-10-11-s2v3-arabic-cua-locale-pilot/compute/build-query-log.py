#!/usr/bin/env python3
"""Build query-log.json for the S2 v3 gauntlet wave 1 from the discovery cells' records.

Sources: compute/cells/frontier-all-queries.json (the frontier scout's own log, 61 records),
compute/cells/killshot-orx-queries.json (the kill-shot scout's 15 orx discover calls), the
kill-shot scout's other searches and the cross-domain scout's full list (transcribed below from
their structured cell outputs, which the workflow passed to the synthesis owner), and the owner's
synthesis queries (raw orx outputs compute/cells/owner-S-q0*.json).

Counting conventions: "orx" counts orx discover calls only (wave 1 of S2's convention);
"run2" also counts ACL Anthology and OpenReview searches (S2 run 2's convention).
"""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUNDLE = HERE.parent

KILLSHOT_OTHER = [
    {"tool": "orx paper --full", "query": "2506.04135 (macOSWorld)", "returned_ids": ["2506.04135"]},
    {"tool": "orx paper --full", "query": "2512.00756 (MPR-GUI)", "returned_ids": ["2512.00756"]},
    {"tool": "orx paper --full", "query": "2609.38184 (RealGUINoise)", "returned_ids": ["2609.38184"]},
    {"tool": "orx paper --full", "query": "2610.07972 (Cross-User Reliability for Mobile GUI Agents in Personalized UIs)", "returned_ids": ["2610.07972"]},
    {"tool": "ACL Anthology regex", "query": "(right-to-left|RTL|mirror) AND (GUI agent|computer-use agent|web agent|screen agent|GUI) (274 hits; first 40 titles scanned)", "returned_ids": ["yu-etal-2026-visual (VAF)"]},
    {"tool": "ACL Anthology regex", "query": "Arabic AND (GUI agent|computer-use|user interface|screenshot)", "returned_ids": ["bach-etal-2007-cmu", "graff-etal-2006-lexicon"]},
    {"tool": "ACL Anthology regex", "query": "(localization|interface language|UI language) AND (GUI agent|computer-use agent|web agent)", "returned_ids": ["tang-etal-2026-lpo", "toles-etal-2026-formgym", "park-etal-2025-r", "wang-etal-2025-inreact", "tao-etal-2025-understanding"]},
    {"tool": "OpenReview API notes/search (anonymous)", "query": "right-to-left GUI agent; mirrored layout computer-use agent; Arabic interface GUI agent (degraded: untitled notes)", "returned_ids": ["5VXMfsWTae", "IbYB4SBdcm", "AQJa7fuxao", "dKk6T7nVEP", "P1rGwEYDxm"]},
]

CROSS = [
    ("orx discover openalex", "Statistical power and optimal design in experiments in which samples of participants respond to samples of stimuli", ["10.1037/xge0000014", "10.3389/fnins.2013.00055", "10.1146/annurev-psych-122414-033702", "W3042851038", "10.1525/collabra.33267"]),
    ("orx discover openalex", "A new probability formula for surveys to substantiate freedom from disease", ["10.1016/s0167-5877(97)00081-0", "10.1038/s41467-018-06657-5", "10.1186/1746-6148-7-49", "10.32614/cran.package.ffd", "10.1186/1746-6148-5-16"]),
    ("orx discover openalex", "Detecting and localizing internationalization presentation failures in web pages", ["10.1109/icst.2016.36", "10.1002/stvr.1746", "10.1145/3468264.3468581", "10.1075/jial.19002.tor", "10.1002/stvr.1756"]),
    ("orx discover openalex", "small sample confidence interval approach to assess individual bioequivalence", ["10.1002/1097-0258(20001030)19:20<2885::aid-sim553>3.0.co;2-h", "10.1002/1097-0258(20001030)19:20<2885::aid-sim553>3.3.co;2-8", "10.4148/2475-7772.1242", "10.5414/cp202525", "10.48550/arxiv.2306.06698"]),
    ("orx discover openalex", "If nothing goes wrong, is everything all right? Interpreting zero numerators", []),
    ("orx discover openalex", "If nothing goes wrong is everything all right interpreting zero numerators", ["10.1001/jama.249.13.1743", "10.1053/j.jvca.2008.07.008", "10.1111/anae.12980", "10.1016/s0022-5347(01)65903-2", "10.6339/jds.2008.06(2).401"]),
    ("orx discover openalex", "Cluster randomized trials with a small number of clusters: which analyses should be used", ["10.1093/ije/dyx169", "10.1093/ije/dyy057", "10.1093/ije/dyad064", "10.1093/ije/dyl129", "10.1093/ije/dyy061"]),
    ("orx discover keyword", "right-to-left mirrored layout GUI agent Arabic", ["2608.09654", "2609.00048", "2610.01215", "2610.05861", "2607.28227", "2609.28565", "2607.24571", "2610.11942", "2609.32679", "2610.11406"]),
    ("orx discover embedding", "automated detection of right-to-left layout mirroring failures in user interfaces using layout graphs or accessibility trees", ["2609.17959", "2608.25425", "2608.08880", "2607.04120", "2604.19081", "2603.20358", "2509.05197", "2511.19380", "2511.14359", "2510.12972"]),
    ("orx discover openalex", "rigorous benchmarking in reasonable time", ["10.1145/2464157.2464160", "10.1145/2491894.2464160", "10.1145/2555670.2464160", "10.1145/235543.235545", "10.14778/3665844.3665863"]),
    ("orx discover openalex", "Producing wrong data without doing anything obviously wrong", ["10.1145/1508244.1508275", "10.1145/1508284.1508275", "10.1145/2528521.1508275", "10.1093/oxrep/grx053", "10.2307/1229336"]),
    ("orx discover openalex", "non-inferiority tests for clustered matched-pair data", ["10.1002/sim.3580", "W2232188949", "10.1002/sim.3910", "10.1016/j.csda.2011.06.019", "10.1002/sim.1385"]),
    ("orx discover openalex", "estimating prevalence from the results of a screening test", ["10.1093/oxfordjournals.aje.a112510", "10.1093/oxfordjournals.aje.a112737", "10.1093/oxfordjournals.aje.a112736", "W2368921486", "10.1016/0378-3758(89)90061-x"]),
    ("orx discover keyword", "accuracy on the line effective robustness distribution shift", ["2609.27546", "2607.05908", "2608.00928", "2610.07758", "2609.13655", "2608.17711", "2608.29112", "2608.26080"]),
    ("orx discover openalex", "Testing the robustness and performance of spatially consistent interfaces", ["10.1145/2470654.2466430", "10.1111/brv.12934", "W1523401619", "10.1038/ncomms13749", "10.1021/acscatal.9b05223"]),
    ("orx discover openalex", "Regression to the mean: what it is and how to deal with it", ["10.1093/ije/dyh299", "10.1093/ije/dyv161", "W2613566475", "10.1038/nature25496", "10.1057/9780230280816_12"]),
    ("orx discover embedding", "measuring robustness to natural distribution shifts effective robustness relative to baseline accuracy trend", ["2608.00928", "2606.31581", "2606.06335", "2604.07266", "2601.10836", "2601.09153", "2510.17794", "2507.23128"]),
    ("orx discover openalex", "Automated Bidirectional Languages Localization Testing for Android Apps with Rich GUI", ["10.1155/2016/2872067", "10.5281/zenodo.1467654", "10.20943/01201703.113", "W3015266663", "10.1145/3816025"]),
    ("orx paper --full", "2607.04120", ["2607.04120"]),
    ("orx paper", "2608.25425", ["2608.25425"]),
    ("orx paper", "2609.28565", ["2609.28565"]),
    ("orx paper", "2007.00644", ["2007.00644"]),
    ("orx paper", "2107.04649", ["2107.04649"]),
    ("WebSearch", "LibreOffice bug U+2068 FIRST STRONG ISOLATE rendering VCL bidi isolate", ["listarchives.libreoffice.org/global/dev/2013/msg09755", "libreoffice bugzilla 116322", "unicode.org L2/12186r"]),
    ("WebSearch", "Android pseudolocale ar-XB RTL mirrored English text developer guide", ["developer.android.com/guide/topics/resources/pseudolocales"]),
    ("WebSearch", "ITDroid internationalization testing Android apps collateral changes GUI RTL", ["ieeexplore 9240697", "ICSE/MOBILESoft 2021 ITDroid tool demo", "academia.edu 97294473"]),
    ("WebSearch", "chromium force-ui-direction force-text-direction switch base/i18n rtl", ["chromium base/i18n/base_i18n_switches.h", "cobalt base_i18n_switches.cc", "codereview.chromium.org/1458043003"]),
    ("WebSearch", "Automated Bidirectional Languages Localization Testing for Android Apps with Rich GUI", ["academia.edu 97294473"]),
    ("WebSearch", "FDA guidance individual bioequivalence subject-by-formulation interaction replicate crossover design 2001", ["PMC4195669", "pubmed 11707058", "govinfo FR-2000-10-27"]),
    ("WebSearch", "LibreOffice accessibility AT-SPI RTL mirrored UI wrong coordinates getExtents bug tdf", ["tdf#150231", "tdf#149952", "tdf#153080", "tdf#147271", "tdf#96333", "tdf#74751", "fdo#42577", "gtk MR 7104"]),
    ("WebSearch", "LibreOffice Calc Use English function names localized function names UI language formula", ["help.libreoffice.org Formula Options", "tdf#144536", "tdf#97815"]),
    ("WebSearch", "Cameron Baldock 1998 freedom from disease probability formula imperfect sensitivity specificity finite population", ["CRAN freedom package"]),
    ("WebSearch", "FriBidi 1.0 release Unicode 6.3 bidi isolates support FSI LRI RLI PDI NEWS", ["sources.debian.org fribidi 1.0.16-5 NEWS", "linux-il FriBidi 1.0.0 announce"]),
    ("WebSearch", "FDA Non-Inferiority Clinical Trials to Establish Effectiveness guidance 2016 M1 M2 margin", ["fda.gov UCM202140.pdf", "hhs 15546fnl Jan-2025 update"]),
    ("WebFetch", "developer.android.com pseudolocales", ["developer.android.com/guide/topics/resources/pseudolocales"]),
    ("WebFetch", "learn.microsoft.com globalization pseudolocalization", ["learn.microsoft.com/en-us/globalization/methodology/pseudolocalization"]),
    ("WebFetch", "firefox-source-docs Fluent tutorial pseudolocalization", ["firefox-source-docs.mozilla.org/l10n/fluent/tutorial.html"]),
    ("WebFetch", "chromium base_i18n_switches.h", ["chromium.googlesource.com base/i18n/base_i18n_switches.h"]),
    ("WebFetch", "W3C qa-bidi-unicode-controls", ["w3.org/International/questions/qa-bidi-unicode-controls"]),
    ("WebFetch", "unicode.org/reports/tr9", ["UAX#9 rev 52"]),
    ("WebFetch", "fda.gov/media/70958/download (2001 BE guidance)", ["HTTP 404"]),
    ("WebFetch", "pmc.ncbi.nlm.nih.gov/articles/PMC4195669", ["PMC4195669"]),
    ("WebFetch", "sources.debian.org fribidi NEWS", ["fribidi NEWS"]),
    ("curl (Bugzilla XML)", "show_bug ctype=xml for 150231, 149952, 153080, 147271, 96333, 74751", ["tdf#150231", "tdf#149952", "tdf#153080", "tdf#147271", "tdf#96333", "tdf#74751"]),
]

OWNER = [
    ("orx discover keyword", "[S-q01] benchmark as finite population census inference fixed question set evaluation error bars --limit 15", "owner-S-q01.json"),
    ("orx discover embedding", "[S-q02] Treating a fixed benchmark's tasks as the whole population (finite-population or census inference) versus a super-population of tasks when computing confidence intervals for model evaluation --limit 15", "owner-S-q02.json"),
    ("orx discover keyword", "[S-q03] relative effect ratio of success rates paired evaluation GUI agent perturbation --limit 15", "owner-S-q03.json"),
]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    records = []
    for r in json.loads((HERE / "cells/frontier-all-queries.json").read_text()):
        records.append({"cell": "frontier", **r})
    for r in json.loads((HERE / "cells/killshot-orx-queries.json").read_text()):
        records.append({"cell": "killshot", **r})
    for r in KILLSHOT_OTHER:
        records.append({"cell": "killshot", **r})
    for tool, q, ids in CROSS:
        records.append({"cell": "cross-domain", "tool": tool, "query": q, "returned_ids": ids})
    for tool, q, f in OWNER:
        raw = json.loads((HERE / "cells" / f).read_text())
        records.append({"cell": "synthesis", "tool": tool, "query": q, "returned_ids": [x["id"] for x in raw],
                        "raw_output": f"compute/cells/{f}", "raw_sha256": sha(HERE / "cells" / f)})
    records.append({"cell": "synthesis", "tool": "orx paper --full", "query": "2411.00640 (Adding Error Bars to Evals)",
                    "returned_ids": ["2411.00640"], "note": "full text sha256 prefix f446e47e500c; Sec. 2 super-population framing"})

    def is_orx_discover(r):
        return r["tool"].startswith("orx discover")

    def is_run2(r):
        return is_orx_discover(r) or r["tool"].startswith("ACL") or r["tool"].startswith("OpenReview")

    by = {}
    for c in ("frontier", "killshot", "cross-domain", "synthesis"):
        rs = [r for r in records if r["cell"] == c]
        by[c] = {"orx_discover": sum(map(is_orx_discover, rs)), "run2_convention": sum(map(is_run2, rs)), "all_records": len(rs)}
    total_orx = sum(v["orx_discover"] for v in by.values())
    total_run2 = sum(v["run2_convention"] for v in by.values())
    out = {
        "schema": "s2v3-query-log-v1",
        "declared_budget_queries": 150,
        "reserved_for_refuters": 30,
        "counted": {"orx_discover_only": total_orx, "with_acl_and_openreview": total_run2, "by_cell": by},
        "remaining_under_run2_convention": 150 - total_run2,
        "remaining_under_orx_convention": 150 - total_orx,
        "note": ("The frontier scout's own tally was 35 orx discover calls (52 with ACL and OpenReview); its log holds 61 records "
                 "including Semantic Scholar, arXiv version checks, web searches and a patent fetch, which neither convention counts."),
        "records": records,
    }
    (BUNDLE / "query-log.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps(out["counted"], indent=1), out["remaining_under_run2_convention"])


if __name__ == "__main__":
    main()
