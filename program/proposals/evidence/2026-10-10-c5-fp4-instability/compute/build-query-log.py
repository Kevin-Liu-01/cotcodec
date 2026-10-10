#!/usr/bin/env python3
"""Build query-log.json for the C5 gauntlet from the discovery cells' and synthesis's raw orx outputs.

The four discovery cells of gauntlet wave 1 (frontier, kill-shot, cross-domain, asset) and the
synthesis owner wrote raw orx outputs to the session scratchpad. This script parses each raw
output (the JSON array after orx's version warning) for the returned ids and hashes every raw
file. Query strings come from each cell's structured result (the frontier cell's
queries_full.json; the others are transcribed below in the order the cells reported them).
Counting convention (as in K1 v2 and v3, E4 and C3): one `orx discover` invocation is one
counted query; this log counts every invocation, including those the backend rejected
(OpenAlex HTTP 429/400, a decode error), so the count is an upper bound. Paper reads, version
checks, OpenReview, Semantic Scholar, Hugging Face and web requests are recorded and not counted.

The scratchpad is session-local, so this script reproduces the log only inside that session;
the output records each raw file's SHA-256.

Usage: python build-query-log.py <scratchpad-dir> <out.json>
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def ids_of(p: Path):
    t = p.read_text(encoding="utf-8", errors="replace")
    i = t.find("[")
    if i < 0:
        return None, t.strip().splitlines()[-1] if t.strip() else "empty"
    try:
        a = json.loads(t[i:])
    except json.JSONDecodeError:
        a, _ = json.JSONDecoder().raw_decode(t[i:])
    return [str(x.get("id")) for x in a if isinstance(x, dict) and x.get("id")], None


KILLSHOT = [  # (tool, query) in the order reported; raw files q01..q26
    ("keyword", "FP4 training block size scale format element grid rounding ablation"),
    ("keyword", "iso-storage FP4 formats bits per element scale overhead MXFP4 NVFP4 comparison"),
    (
        "embedding",
        "Systematic factorial study of 4-bit floating point training formats for language models varying element format (E2M1, INT4), block scale format (E8M0, E4M3), block size and stochastic rounding, compared at equal bits per element, with multiple seeds and variance decomposition of loss gap and loss spikes",
    ),
    ("keyword", "Elucidating the Design Space of FP4 Training"),
    ("keyword", "UE5M3 FP4 block scaling"),
    ("keyword", "Scaling Laws for Floating-Point Quantization Training"),
    (
        "keyword",
        "FP4 All the Way fully quantized training block sizes scaling formats rounding methods",
    ),
    (
        "keyword",
        "INT vs FP comprehensive study fine-grained low-bit quantization formats MXINT4 NVINT4",
    ),
    ("keyword", "Quartet native FP4 training optimal scaling law MXFP4 NVFP4"),
    (
        "keyword",
        "unified scaling laws compressed representations capacity Gaussian MSE quantized formats",
    ),
    (
        "keyword",
        "emulated fake quantization versus native FP4 tensor core training loss discrepancy",
    ),
    ("keyword", "FP4 training instability loss spikes small models proxy scale dependence"),
    ("keyword", "Quartet II NVFP4 pretraining unbiased gradient estimation"),
    ("keyword", "Four Over Six adaptive block scaling NVFP4"),
    ("keyword", "INT4 versus FP4 pretraining NVINT4 MXINT4 training from scratch"),
    (
        "keyword",
        "low precision training instability appears late trillion tokens SwiGLU outlier amplification FP8",
    ),
    ("keyword", "small-scale proxies large-scale transformer training instabilities"),
    (
        "embedding",
        "Which numerical format component causes divergence in 4-bit floating point LLM training: element encoding, shared scale encoding, block size or stochastic rounding, studied with controlled ablations and variance decomposition across seeds [--published-after 2025-01-01]",
    ),
    ("keyword", "adaptive block-scaled data types IF4 per-block INT4 FP4 selection"),
    (
        "keyword",
        "shared microexponents block floating point formats bits per element scale overhead training",
    ),
    (
        "keyword",
        "FP4 GEMM accumulation order emulator bit-exact native tensor core mismatch training",
    ),
    ("openalex", "FP4 training block size scale format language model"),
    ("openalex", "microscaling MXFP4 NVFP4 training stability comparison"),
    ("keyword", "TetraJet-v2 NVFP4 training oscillation outliers"),
    ("openalex", "FP4 microscaling block size scale format factorial numerics Zenodo"),
    (
        "keyword",
        "software emulation FP4 training differs from native hardware execution path loss [--published-after 2025-06-01]",
    ),
]

CROSS = [  # (tool, query, raw file or None, calls) in the order reported
    ("openalex", "stochastic rounding probabilistic backward error analysis", "q01", 1),
    ("openalex", "simulating low precision floating-point arithmetic", "q02", 1),
    ("keyword", "stochastic rounding few random bits bias", "q03", 1),
    ("keyword", "numerical behavior NVIDIA tensor cores accumulation", "q04", 1),
    ("keyword", "nondeterminism instability neural network optimization single bit", "q05", 1),
    (
        "keyword",
        "small-scale proxies large-scale Transformer training instabilities learning rate sensitivity",
        "q06",
        1,
    ),
    ("keyword", "Accurate Models of NVIDIA Tensor Cores", "q07", 1),
    (
        "keyword",
        "Blackwell block-scaled matrix multiply numerical behavior FP4 accumulation rounding [--published-after 2025-01-01]",
        "q08",
        1,
    ),
    ("openalex", "definitive screening designs fractional factorial aliasing", "q09", 1),
    ("openalex", "common random numbers variance reduction simulation guidelines", "q10", 1),
    ("keyword", "functional ANOVA hyperparameter importance variance decomposition", "q11", 1),
    (
        "keyword",
        "loss spike detection rolling average standard deviations spike score pretraining",
        "q12",
        1,
    ),
    ("openalex", "metamorphic testing review challenges opportunities", "q13", 1),
    ("openalex", "theory of nonsubtractive dither", "q14", 1),
    (
        "keyword",
        "spike score standard deviations rolling average loss gradient norm OLMo",
        "q15",
        1,
    ),
    ("keyword", "Accounting for variance in machine learning benchmarks", "q16", 1),
    ("openalex", "optimizer's curse skepticism postdecision surprise", "q17", 1),
    ("keyword", "pychop emulating low-precision arithmetic neural networks", "q18", 1),
    (
        "keyword",
        "P3109 arithmetic formats machine learning reference implementation gfloat",
        "q19",
        1,
    ),
    ("openalex", "roundoff errors block floating point systems", "q20", 1),
    (
        "keyword",
        "Monte Carlo arithmetic Verificarlo numerical instability stochastic arithmetic",
        "q21",
        1,
    ),
    (
        "keyword",
        "microscaling MX format emulation library reference shared exponent floor log2 amax",
        "q22",
        1,
    ),
    (
        "openalex",
        "An efficient approach for assessing hyperparameter importance (FAILED 429, twice)",
        "q23",
        2,
    ),
    (
        "openalex",
        "Accounting for variance in machine learning benchmarks (FAILED 429, twice)",
        "q24",
        2,
    ),
    (
        "openalex",
        "The optimizer's curse: skepticism and postdecision surprise in decision analysis (FAILED 429, twice)",
        "q25",
        2,
    ),
    (
        "openalex",
        "split-plot designs what why and how hard-to-change factors (FAILED 429)",
        "q26",
        1,
    ),
    (
        "openalex",
        "optimal detection of changepoints with a linear computational cost (FAILED 429)",
        "q28",
        1,
    ),
    (
        "keyword",
        "fine-tuning pretrained language models weight initializations data orders early stopping",
        "q27",
        1,
    ),
    ("keyword", "Accounting for Variance in Machine Learning Benchmarks Bouthillier", "q24b", 1),
    (
        "keyword",
        "optimal detection of changepoints with a linear computational cost PELT",
        "q28b",
        1,
    ),
    (
        "embedding",
        "Factorial ablation of low-precision number format components (element grid, block scale format, block size, rounding mode) in neural network training with variance decomposition across random seeds",
        "q29",
        1,
    ),
    (
        "keyword",
        "quantization error correlated with signal additive noise model invalid few bits Bennett Widrow",
        "q30",
        1,
    ),
]

ASSET = [
    (
        "keyword",
        "FP4 training emulation fake quantization microscaling E2M1 open-source code",
        "q1_kw",
    ),
    ("keyword", "Elucidating the Design Space of FP4 Training", "q2_kw"),
    ("keyword", "UE5M3 FP4 Block Scaling", "q3_kw"),
    ("keyword", "Scaling Laws for Floating-Point Quantization Training", "q4_kw"),
    (
        "embedding",
        "factor question: which FP4 factor drives instability (grid, scale format, block size, rounding)",
        "q5_emb",
    ),
    ("openalex", "FP4 training microscaling block scale format language model", "q6_oa"),
    ("keyword", "microxcaling MX library reference quantization", "q7_kw"),
    ("keyword", "torchao MX FP4 training", "q8_kw"),
]

SYNTH = [
    (
        "keyword",
        "grid scale format interaction FP4 pretraining INT4 E2M1 matched storage seeds [--published-after 2025-06-01 --limit 20]",
        "s01",
    ),
    (
        "embedding",
        "Small language model trained from scratch with emulated 4-bit block-scaled matrix multiplications in forward and backward passes; a floating-point E2M1 grid and a uniform symmetric INT4 grid crossed with block-scale configurations chosen so block size and scale encoding are separable at equal storage (power-of-two scale on blocks of 32 and 16, FP8 scale with per-tensor scale on blocks of 16, BF16 scale on blocks of 32); per-configuration learning-rate sweeps and three seeds; variance decomposition of the loss gap into grid, block, scale and interaction contrasts; prediction of each cell's loss from block-level quantization signal-to-noise and crest factor [--published-after 2025-01-01 --limit 20]",
        "s02",
    ),
    (
        "keyword",
        "quantization signal-to-noise ratio predicts training loss across 4-bit formats [--limit 20]",
        "s03",
    ),
    (
        "keyword",
        "crest factor INT4 versus FP4 training loss block size scale [--published-after 2025-10-01 --limit 20]",
        "s04",
    ),
    (
        "keyword",
        "dequantize BF16 emulation inexact block scale TF32 FP4 training emulator [--published-after 2025-06-01 --limit 20]",
        "s05",
    ),
    (
        "openalex",
        "4-bit training element format scale format block size factorial language model pretraining [--published-after 2025-01-01] (FAILED 429)",
        "s06",
    ),
    ("keyword", "Rethinking Shrinkage Bias in LLM FP4 Pretraining [--limit 15]", "s07"),
]


def main() -> None:
    s, out_path = Path(sys.argv[1]), Path(sys.argv[2])
    rows, other = [], []

    # frontier: queries_full.json; raw files q01..q11, q11b, q12..q37 map to discover entries 1..38
    fr = json.loads((s / "c5-frontier/queries_full.json").read_text())
    raw_names = (
        [f"q{i:02d}" for i in range(1, 12)] + ["q11b"] + [f"q{i:02d}" for i in range(12, 38)]
    )
    k = 0
    for e in fr:
        if e["tool"].startswith("orx discover"):
            raw = s / f"c5-frontier/{raw_names[k]}.txt"
            ids, err = ids_of(raw)
            k += 1
            rows.append(
                {
                    "id": f"FR-{k:02d}",
                    "stage": "cell:frontier",
                    "tool": e["tool"],
                    "query": e["query"],
                    "returned_ids": ids if ids is not None else [],
                    "backend_error": err,
                    "reported_ids_match_raw": (ids or []) == e["returned_ids"],
                    "raw_output_sha256": sha(raw),
                    "counts_against_query_budget": True,
                }
            )
        else:
            other.append(
                {
                    "id": f"FR-X{len(other) + 1:02d}",
                    "stage": "cell:frontier",
                    "tool": e["tool"],
                    "query": e["query"],
                    "returned_ids": e["returned_ids"],
                    "counts_against_query_budget": False,
                }
            )
    for i, (tool, q) in enumerate(KILLSHOT, 1):
        raw = s / f"c5kill/q{i:02d}.txt"
        ids, err = ids_of(raw)
        rows.append(
            {
                "id": f"KS-{i:02d}",
                "stage": "cell:killshot",
                "tool": f"orx discover {tool}",
                "query": q,
                "returned_ids": ids or [],
                "backend_error": err,
                "raw_output_sha256": sha(raw),
                "counts_against_query_budget": True,
            }
        )
    for i, (tool, q, name, calls) in enumerate(CROSS, 1):
        raw = s / f"c5xd/{name}.txt"
        ids, err = ids_of(raw)
        rows.append(
            {
                "id": f"XD-{i:02d}",
                "stage": "cell:cross-domain",
                "tool": f"orx discover {tool}",
                "query": q,
                "returned_ids": ids or [],
                "backend_error": err,
                "invocations": calls,
                "raw_output_sha256": sha(raw),
                "counts_against_query_budget": True,
            }
        )
    for i, (tool, q, name) in enumerate(ASSET, 1):
        raw = s / f"c5-asset/{name}.txt"
        ids, err = ids_of(raw)
        rows.append(
            {
                "id": f"AS-{i:02d}",
                "stage": "cell:asset",
                "tool": f"orx discover {tool}",
                "query": q,
                "returned_ids": ids or [],
                "backend_error": err,
                "raw_output_sha256": sha(raw),
                "note": "query text paraphrased from the asset cell's report where it listed ids as 'and others'; returned ids parsed from the raw file",
                "counts_against_query_budget": True,
            }
        )
    for i, (tool, q, name) in enumerate(SYNTH, 1):
        raw = s / f"c5-synth/{name}.txt"
        ids, err = ids_of(raw)
        rows.append(
            {
                "id": f"SY-{i:02d}",
                "stage": "synthesis",
                "tool": f"orx discover {tool}",
                "query": q,
                "returned_ids": ids or [],
                "backend_error": err,
                "raw_output_sha256": sha(raw),
                "counts_against_query_budget": True,
            }
        )

    # uncounted retrieval reported by the cells and by synthesis
    other += [
        {
            "id": "KS-P",
            "stage": "cell:killshot",
            "tool": "orx paper --full",
            "query": "17 full texts",
            "returned_ids": [
                "2505.19115",
                "2510.25602",
                "2506.01863",
                "2604.08826",
                "2605.09825",
                "2509.17791",
                "2609.02846",
                "2501.02423",
                "2606.20381",
                "2605.12327",
                "2601.22813",
                "2509.25149",
                "2608.11859",
                "2603.28765",
                "2601.19026",
                "2610.00053",
                "2505.14669",
            ],
            "counts_against_query_budget": False,
        },
        {
            "id": "XD-P",
            "stage": "cell:cross-domain",
            "tool": "orx paper --full / report",
            "query": "12 full texts and 1 report",
            "returned_ids": [
                "2606.09686",
                "2607.12915",
                "2512.07004",
                "2504.20634",
                "2103.04514",
                "2309.14322",
                "2610.09005",
                "2605.25991",
                "2504.07835",
                "2606.04028",
                "2609.11356",
                "2501.00656",
                "2002.06305",
            ],
            "counts_against_query_budget": False,
        },
        {
            "id": "XD-W",
            "stage": "cell:cross-domain",
            "tool": "WebFetch (2) and WebSearch (3)",
            "query": "PyTorch numerical accuracy notes; Bouthillier et al. MLSys 2021; Smith and Winkler 2006; Hutter et al. ICML 2014",
            "returned_ids": [
                "https://docs.pytorch.org/docs/2.14/notes/numerical_accuracy.html",
                "https://arxiv.org/abs/2103.03098",
                "https://doi.org/10.1287/mnsc.1050.0451",
                "https://proceedings.mlr.press/v32/hutter14.html",
            ],
            "counts_against_query_budget": False,
        },
        {
            "id": "AS-P",
            "stage": "cell:asset",
            "tool": "orx paper --full",
            "query": "9 full texts",
            "returned_ids": [
                "2509.17791",
                "2609.02846",
                "2501.02423",
                "2606.20381",
                "2607.12915",
                "2603.02731",
                "2610.00053",
                "2605.08565",
                "2502.20586",
            ],
            "counts_against_query_budget": False,
        },
        {
            "id": "AS-G",
            "stage": "cell:asset",
            "tool": "GitHub API, Hugging Face API, PyPI (licences and code locations)",
            "query": "gfloat, ml_dtypes, TransformerEngine, ue5m3-fp4, microxcaling, torchao, mxfp4-llm, fouroversix, fp4-all-the-way and others; FineWeb-Edu and tokenizer repos",
            "returned_ids": [],
            "counts_against_query_budget": False,
        },
        {
            "id": "SY-S2",
            "stage": "synthesis",
            "tool": "Semantic Scholar Graph API via read-only host relay",
            "query": "paper DOI:10.1109/ARITH64983.2025.00011 (openAccessPdf CLOSED); forward citations of the ARITH paper, 2505.19115, 2509.17791, 2603.28765, 2606.20381, 2609.02846, 2510.25602",
            "returned_ids": [
                "s2:b3cbb70c7f195a45c41c696641ddff6782c744ef",
                "citations: 12 / 45 / 5 / 3 / 2 / 1 / 23",
            ],
            "raw_output_sha256": sha(s / "c5-synth/s2_cites.txt"),
            "counts_against_query_budget": False,
        },
        {
            "id": "SY-HF",
            "stage": "synthesis",
            "tool": "Hugging Face API (metadata only, no download)",
            "query": "datasets/HuggingFaceFW/fineweb-edu (sha, licence, gating) and its sample/10BT tree at 87f09149; models mistralai/Mistral-7B-v0.1 (and tree at 27d67f1b), HuggingFaceTB/SmolLM2-135M, openai-community/gpt2",
            "returned_ids": [],
            "raw_output_sha256": sha(s / "c5-synth/fwe_tree.json"),
            "counts_against_query_budget": False,
        },
        {
            "id": "SY-PT",
            "stage": "synthesis",
            "tool": "direct fetch",
            "query": "https://docs.pytorch.org/docs/2.14/notes/numerical_accuracy.html (BF16 reduced-precision reduction default)",
            "returned_ids": [],
            "raw_output_sha256": sha(s / "c5-synth/pt_numacc214.html"),
            "counts_against_query_budget": False,
        },
        {
            "id": "SY-R",
            "stage": "synthesis",
            "tool": "re-read of cell-fetched full texts",
            "query": "2505.19115 (Sec. 3.1, Figs. 1-3, App. Table 4), 2509.17791 (Principle 2, App. .3), 2603.28765 (Sec. 4.1, Fig. 5a, App. A), 2606.20381 (Sec. 4 recipe, Table 1, Sec. 5.2), 2609.02846 (Eq. 3, Table 2, Secs. 6.1-6.3, Fig. 2, statistical note), 2510.25602 (Theorem 1 crossovers, Table 2, Sec. 5.1), 2604.08826 (storage and PTS statements), 2509.25149 (Sec. 5, App. A.3), 2605.09825 (abstract), 2501.00656 (spike score), 2309.14322 (LR sensitivity), 2512.07004 (alignment), 2504.20634 (Figs. 1-2), 2610.00053 (abstract numbers, one-trajectory statement), 2601.19026 (abstract, threshold), 2608.11859 (Sec. 1, random search); 16 texts",
            "returned_ids": [],
            "counts_against_query_budget": False,
        },
    ]
    counted = sum(r.get("invocations", 1) for r in rows)
    failed = sum(r.get("invocations", 1) for r in rows if r["backend_error"])
    by_stage = {}
    for r in rows:
        by_stage[r["stage"]] = by_stage.get(r["stage"], 0) + r.get("invocations", 1)
    log = {
        "built_by": "compute/build-query-log.py",
        "source_cutoff": "2026-10-10",
        "counting_rule": "every orx discover invocation counts, including backend rejections; paper reads and non-orx searches do not",
        "queries_against_budget": counted,
        "queries_rejected_by_backend": failed,
        "queries_returning_results": counted - failed,
        "by_stage": by_stage,
        "declared_query_budget": 150,
        "refuter_reserve": 30,
        "remaining_after_synthesis": 150 - counted,
        "discover": rows,
        "uncounted": other,
    }
    out_path.write_text(json.dumps(log, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(counted, failed, by_stage, 150 - counted)
    bad = [
        r["id"] for r in rows if r.get("reported_ids_match_raw") is False and not r["backend_error"]
    ]
    print("frontier rows whose reported ids differ from raw:", bad)


if __name__ == "__main__":
    main()
