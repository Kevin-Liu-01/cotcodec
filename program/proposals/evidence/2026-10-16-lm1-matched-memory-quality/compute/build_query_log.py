#!/usr/bin/env python3
"""Build query-log.json for the LM1 gauntlet (wave 1): every counted search of the four discovery
cells and of the synthesis, with the ids each returned.

The cells' records are transcribed from the structured outputs they returned to the orchestrator
(the workflow's computed task text); the cells saved no raw orx outputs, so there are no per-query
raw digests for them. The synthesis's six records come from compute/synthesis-queries.json, built
from the raw orx JSON saved in the session scratchpad. The asset cell reported 13 counted searches
without their query strings; they are counted, not itemized.

Usage: python build_query_log.py --out query-log.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

FRONTIER = [
    ("orx discover keyword", "matched memory budget larger quantized model versus smaller model higher precision", ["2610.18642","2610.17637","2609.26708","2609.35570","2610.08164","2610.15629","2610.07457","2610.13041","2610.13706","2610.15640","2609.04490","2610.14369","2609.29999","2610.21344","2610.05034"]),
    ("orx discover embedding", "Under a fixed memory budget, compare a very large mixture-of-experts language model quantized to 1-2 bits per weight against a smaller model at 4-8 bits on downstream tasks", ["2610.15640","2610.18343","2610.20353","2609.13415","2609.01962","2609.00665","2608.24615","2608.06564","2607.27275","2609.25014","2606.00079","2605.19645","2604.04356","2601.15287","2603.04162"]),
    ("orx discover openalex", "quantization model size precision tradeoff fixed memory budget large language models", ["W7132866158","W7148215146","2607.25380","10.1109/icdcsw63273.2025.00058","10.56975/ijedr.v14i3.309404","10.1145/3748304","2410.23918","2402.09748","2605.14929","2604.20079","2509.23729","10.1109/tpami.2026.3718968","10.52202/075280-0441","10.1145/3731569.3764810","2608.28048"]),
    ("orx discover keyword", "k-bit inference scaling laws total model bits", ["2609.40316","2610.17637","2609.36263","2610.19281","2610.14277","2610.02462","2609.08690","2609.19683","2607.10855","2212.09720","2026.2026-06-24-scaling-laws","2607.19623","2605.23901","2606.02011","2606.06888"]),
    ("orx discover keyword (published-after 2025-06-01)", "Kimi K2 DeepSeek 1-bit 2-bit quantization benchmark evaluation", ["2607.24653","2609.26425","2610.14745","2609.06161","2610.15384","2609.36760","2610.03027","2610.quantization-aware-training-reasoning-llms","2609.32042","2608.21134","2610.20686","2608.19388","2610.12444","2610.03402","2507.20534"]),
    ("orx discover keyword", "MoE-XBench", ["2610.21378","2610.05744","2610.19975","2610.07332","2607.21978","2610.01296","2610.05123","2610.01950","2610.19232","2610.11158","2609.33385","2608.27867","2610.07333","2609.00791","2609.35751"]),
    ("orx discover embedding", "Is it better to run a larger language model at lower precision or a smaller model at higher precision for the same memory footprint? Pareto frontier of accuracy versus bytes across quantized model families", ["2610.15640","2610.15629","2610.18343","2610.15146","2609.17863","2608.25761","2609.13415","2609.00665","2608.24615","2608.06564","2607.29397","2609.25014","2607.25583","2606.04063","2605.19645"]),
    ("orx discover keyword (published-after 2025-01-01)", "larger quantized model outperforms smaller full-precision model same memory", ["2610.17637","2609.29999","2609.34380","2609.26708","2609.35570","2610.16003","2609.39801","2609.21834","2610.05745","2609.39185","2608.05326","2610.06414","2610.15629","2610.08164","2601.22101"]),
    ("orx discover keyword", "DeepSeek-R1 dynamic 1.58-bit quantization evaluation Qwen3-235B", ["2608.01078","2610.15259","2610.quantization-aware-training-reasoning-llms","2609.16338","2606.24033","2609.01962","2610.14745","2603.05168","2511.21631","2606.26650","2609.33601","2606.20474","2610.03027","2609.09240","2609.01587"]),
    ("orx discover embedding", "Evaluation of extreme low-bit (1-2 bit) quantized trillion-parameter mixture-of-experts models such as Kimi K2 and DeepSeek V3 against smaller models on reasoning, coding and agentic benchmarks", ["2606.25519","2606.21257","2604.04356","2504.04823","2603.25944","2603.04162","2512.24776","2601.13243","2511.05722","2602.14444","2504.02010","2508.17467","2508.11318","2502.10928","2402.14992"]),
    ("orx discover keyword", "scaling laws for precision post-training quantization degradation overtrained", ["2610.17637","2609.11716","2610.09183","2610.05329","2608.08188","2610.16368","2610.15092","2610.03218","2609.32060","2610.09969","2610.09877","2608.12239","2610.09227","2608.13932","2607.28589"]),
    ("orx discover openalex", "larger model lower bit quantization versus smaller model same memory accuracy", ["10.59256/indjcst.20260502102","2605.19929","2509.23729","2605.02404","2305.12356","10.18653/v1/2025.findings-emnlp.645","10.1038/s44335-026-00099-9","2607.02893","2312.07950","2509.15206","10.3390/electronics10222823","W7170111364","W7132866158","2607.23047","2609.38477"]),
    ("orx discover keyword", "ParetoQ scaling laws extremely low-bit LLM quantization", ["2502.02631","2610.04457","2610.17637","2610.quantization-aware-training-reasoning-llms","2610.15384","2607.27694","2610.04490","2610.00432","2610.02462","2610.05265"]),
    ("orx discover keyword", "scaling laws for precision post-train quantization degradation", ["2610.17637","2608.08188","2609.11716","2610.16368","2609.32060","2610.15092","2608.12239","2610.09183","2411.04330","2610.09969"]),
    ("orx discover embedding", "Quantization scaling law for mixture-of-experts models relating total parameters, active parameters and bits per weight to choose the best model under a fixed memory budget", ["2610.17637","2610.20353","2610.20247","2610.22353","2609.18131","2607.16184","2606.04980","2605.23078","2606.05688","2605.29350","2603.21862","2604.06515","2603.10379","2601.20205","2601.13563"]),
    ("orx discover keyword (published-after 2026-01-01)", "GGUF IQ1 IQ2 DeepSeek GLM Kimi quantized evaluation compared smaller model", ["2607.24653","2609.19969","2610.04403","2608.glm-5","2609.26333","2609.14864","2606.19348","2610.07792","2604.03121","2610.00917","2607.kimi-k3","2609.36603","2602.15763","2608.08634","2026.glm-5-2"]),
    ("orx discover embedding (published-after 2025-06-01)", "Practitioner study: choosing among open-weight models of different sizes and quantization levels for a fixed device memory budget such as a 128 GB workstation, measuring downstream task accuracy", ["2610.15640","2610.15629","2610.14180","2609.24965","2609.right-sized-ai-edge-sustainability","2609.33874","2609.18005","2609.07901","2609.08307","2609.15706","2609.01587","2608.30076","2609.00665","2608.24615","2608.06564"]),
    ("orx discover keyword (published-after 2025-06-01)", "same memory footprint larger model quantized smaller model full precision reasoning benchmark", ["2609.39801","2610.16003","2609.26708","2609.34380","2610.17637","2609.29999","2608.05326","2610.05124","2610.10381","2610.18642","2610.17531","2608.04771","2609.35570","2610.04204","2610.05685"]),
    ("orx discover keyword", "UD-TQ1_0 Unsloth dynamic GGUF Kimi", ["2607.24653","2609.14864","2610.04403","2607.kimi-k3","2602.02276","2604.03121","2510.26692","2609.31834","2610.15886","2609.24797","2604.18556","2609.26333","2504.07491","2507.20534","2610.10263"]),
    ("orx discover keyword (published-after 2026-01-01)", "Unsloth dynamic GGUF IQ1_M evaluation trillion parameter MoE agentic benchmark", ["2609.15636","2609.18110","2610.05744","2610.08430","2610.07332","2610.21378","2609.14864","2606.30616","2608.12103","2610.04403","2610.02241","2609.08690","2607.21653","2606.15079","2606.24937"]),
    ("orx discover openalex", "extreme low-bit quantization trillion-parameter mixture of experts evaluation Kimi DeepSeek", ["2606.10493","2606.15007","2606.15079","2609.26333","2609.36070","10.54097/bvpfjj49","2604.02715","2510.19366","2604.24827","2603.10031","2602.04705","10.1145/3725843.3756043","2607.18631","2601.14053","2605.23901"]),
    ("orx discover keyword (published-after 2025-09-01)", "128GB unified memory Strix Halo DGX Spark quantized model accuracy comparison", ["2610.13125","2610.20354","2609.19169","2608.07226","2609.35110","2610.10528","2609.14258","2607.10863","2609.11875","2605.16184","2609.34380","2606.15682","2609.07664","2607.07647","2609.35570"]),
    ("orx discover embedding (published-after 2025-09-01)", "Which open-weight model gives the best task accuracy on a 128 GB unified-memory machine: a heavily quantized frontier mixture-of-experts or a smaller model near native precision", ["2610.05458","2610.15640","2609.18110","2610.15629","2610.20353","2609.15636","2610.02701","2609.33874","2609.07901","2609.17863","2609.13415","2609.00665","2608.24615","2608.15383","2608.15693"]),
    ("orx discover keyword", "optimal bits per parameter memory-constrained inference quantization frontier model size ternary 2-bit 4-bit", ["2609.16338","2608.21134","2610.15384","2609.35465","2609.33601","2610.quantization-aware-training-reasoning-llms","2610.12444","2609.33269","2607.02893","2610.21808","2610.14277","2606.13054","2609.06161","2608.20953","2601.07892"]),
    ("WebSearch", "Kimi K2.5 1.8-bit UD-TQ1_0 benchmark accuracy compared Qwen3-235B gpt-oss-120b 128GB", ["arxiv.org/pdf/2604.18556","unsloth.ai/docs/models/kimi-k2.5","benchlm.ai/compare/kimi-k2-5-vs-qwen3-235b-2507"]),
    ("WebSearch", "r/LocalLLaMA 128GB same size quantized large model vs smaller model benchmark Qwen3-235B Q3 GLM 4.5 Air Q8 gpt-oss-120b", ["reddit.sentinel-team.org/posts/1pulqzt","localclaw.io/ram/128gb"]),
    ("WebSearch", "Red Hat half a million quantized LLM evaluations accuracy larger quantized model vs smaller unquantized", ["developers.redhat.com/articles/2024/10/17/we-ran-over-half-million-evaluations-quantized-llms","developers.redhat.com/articles/2025/03/03/deployment-ready-reasoning-quantized-deepseek-r1-models"]),
    ("WebSearch", "Intel AutoRound Kimi-K2 int2 mixed accuracy evaluation DeepSeek-R1 int2 gguf q2ks", ["lmsys.org/blog/2025-11-13-AutoRound","huggingface.co/OPEA/DeepSeek-R1-0528-int2-mixed-AutoRound","github.com/intel/auto-round"]),
    ("WebSearch", "ubergarm Kimi-K2.5 GGUF perplexity KLD smol-IQ1_KT table", ["huggingface.co/ubergarm/Kimi-K2-Thinking-GGUF","huggingface.co/ubergarm/Kimi-K2.6-GGUF","huggingface.co/unsloth/Kimi-K2.5-GGUF"]),
    ("WebSearch", "matched memory OR iso-memory evaluation quantized large MoE versus smaller model 2026 benchmark Kimi DeepSeek V4 Flash local", ["arxiv.org/pdf/2503.06823","blog.nota.ai/insights/icml-2026-workshop-moe-quantization","bestllmfor.com/reports/state-of-local-llm-jun-2026"]),
    ("WebSearch", "Kaitchup Benjamin Marie Qwen3-235B GGUF quantization evaluation accuracy Q3_K_XL Q2_K_XL benchmark", ["kaitchup.substack.com/p/summary-of-qwen35-gguf-evaluations","kaitchup.substack.com/p/lessons-from-gguf-evaluations-ternary","unsloth.ai/docs/models/qwen3.5/gguf-benchmarks"]),
    ("WebSearch", "Kimi K2 量化 1bit 2bit 评测 对比 Qwen3-235B 同等显存 内存", ["arxiv.org/pdf/2604.18556","dev.to/gentic_news/1-bit-kimi-k3-quant","unsloth.ai/docs/models/kimi-k2.5"]),
    ("WebSearch", "oobabooga benchmark quantized models size GB DeepSeek R1 IQ1 Kimi K2 low-bit score leaderboard", ["arxiv.org/abs/2505.02390","forum.level1techs.com/t/deepseek-deep-dive-r1-at-home/225826","reddit r/LocalLLaMA 1ibbloy"]),
    ("WebSearch", "DeepSeek V4 Flash 0731 IQ2_XXS ds4 Q2 quantized GPQA LiveCodeBench MMLU-Pro accuracy measured vs full", ["arxiv.org/pdf/2606.19348","datalearner.com deepseek-v4-flash","benchlm.ai deepseek-v4-flash-0731-vs-deepseek-v4-pro-0813"]),
    ("WebSearch", "best LLM for 128GB unified memory quality benchmark quantized comparison 2026 GLM-5.3-Flash DeepSeek V4 Flash Qwen3.8 gpt-oss-120b eval scores", ["smartscope.blog glm-5-3-best-local-llm","bestllmfor.com/reports/state-of-local-llm-aug-2026","datalearner.com benchmark-compare deepseek-v4-flash qwen3-8-flash-next"]),
    ("WebSearch", "Kimi K2 Thinking 1-bit 1.8-bit GGUF Aider polyglot score benchmark quantized result", ["unsloth.ai/docs/models/tutorials/kimi-k2-thinking-how-to-run-locally","huggingface.co/ubergarm/Kimi-K2-Thinking-GGUF","theneuron.ai kimi-k2-thinking"]),
    ("GitHub search (gh search repos)", "quantized models same memory budget benchmark", []),
    ("GitHub search (gh search repos)", "quantization model size tradeoff benchmark GGUF same VRAM", []),
    ("Hugging Face dataset search", "gguf-eval", ["temp-enpaiva/eval_gua-a_v0.1-ft_mistral-7b_GGUF","temp-enpaiva/eval_gua-a_v0.2-dpo_mistral-7b_GGUF","YukiTomita-CC/calm3-22b_gguf_eval"]),
    ("Hugging Face dataset search", "kimi-k2 gguf", []),
    ("Hugging Face dataset search", "quant benchmark", ["siddharthbhadu/quant-benchmark-results"]),
]

KILLSHOT = [
    ("orx discover keyword (published-after 2025-01-01)", "larger quantized model versus smaller full precision model same memory budget", ["2610.17637","2610.18642","2609.29999","2609.26708","2610.08164","2610.15629","2610.15640","2609.35570","2609.34380","2610.14369","2610.05034","2608.05326"]),
    ("orx discover embedding (published-after 2025-06-01)", "Under a fixed memory budget, is a very large mixture-of-experts model quantized to 1-2 bits better on downstream tasks than a smaller model at 4-8 bits? Matched-memory comparison across model families", ["2610.05458","2610.18343","2610.05685","2610.19373","2610.20353","2609.29999","2609.34227","2609.15636","2610.00232","2609.07901","2609.06922","2609.13415","2609.01962","2609.00665","2608.24615"]),
    ("orx discover keyword", "Kimi K2.5 GGUF quantization", ["2602.02276","2604.03121","2607.24653","2604.18556","2609.14864","2609.26333","2610.04403","2607.kimi-k3","2606.12280","2609.38166","2608.24615","2604.18566"]),
    ("orx discover openalex", "quantized large language model versus smaller model same memory budget downstream accuracy", ["10.1007/s11704-026-60308-3","10.48550/arxiv.2607.23047","10.1145/3744746","10.48550/arxiv.2605.02404","10.48550/arxiv.2607.25380","10.48550/arxiv.2303.17564","10.36079/lamintang.ijai-01301.1050","10.48550/arxiv.2608.08188","10.48550/arxiv.2609.25492","10.48550/arxiv.2609.34259","10.1007/s10791-026-10580-5","10.21203/rs.3.rs-3296728/v1"]),
    ("WebSearch", "Kimi K2.5 UD-TQ1_0 1.8-bit benchmark accuracy vs smaller model 128GB", ["unsloth.ai/docs/models/tutorials/kimi-k2.5","developer.tenten.co/how-to-run-kimi-k25-locally-on-mac-studio-m3-ultra-with-512gb","benchlm.ai/models/kimi-k2-5"]),
    ("WebSearch", "\"same memory\" OR \"matched memory\" quantized 1T MoE vs smaller model benchmark evaluation 2026 Kimi DeepSeek V4 Flash gpt-oss-120b", ["huggingface.co/blog/mishig/local-moores-law","arxiv.org/pdf/2508.10925","siliconflow.com/models/compare/deepseek-v4-flash-vs-gpt-oss-120b","benchlm.ai/compare/deepseek-v4-flash-max-vs-gpt-oss-120b","spheron.network/blog/open-weight-frontier-model-showdown-2026"]),
    ("WebSearch", "reddit LocalLLaMA Kimi K2.5 TQ1_0 vs DeepSeek V4 Flash Q2 quality comparison 128GB Mac", ["llmreference.com/compare/deepseek-v4-flash/kimi-k2-5","requesty.ai/models/compare/deepseek--deepseek-v4-flash-0731/moonshot--kimi-k2.5","terminalbytes.com/run-deepseek-v4-flash-at-home","benchlm.ai/compare/deepseek-v4-flash-base-vs-kimi-k2-5"]),
    ("WebSearch", "Unsloth dynamic GGUF Aider polyglot 1-bit DeepSeek V3.1 vs Qwen3-235B unquantized 55.7 59.6", ["unsloth.ai/docs/basics/dynamic-3.0-ggufs/unsloth-dynamic-ggufs-on-aider-polyglot"]),
]

CROSS = [
    ("orx discover keyword", "error bars evals paired differences clustered standard errors power analysis", ["2608.22659","2512.21326","2610.10142","2609.36263","2610.12674","2609.35583"]),
    ("orx discover embedding", "statistical power and minimum detectable difference when comparing two language models on the same benchmark questions with paired tests", ["2609.32890","2609.33196","2610.01471","2609.00482","2608.22659","2607.15190","2607.16259","2605.30315","2606.07726","2602.17316","2512.21326","2601.12343"]),
    ("orx discover keyword", "quantized reasoning models output length quantization hurts reasoning", ["2609.39801","2609.26708","2606.25519","2606.00206","2504.04823","2610.11226","2610.15259"]),
    ("orx discover embedding (published-after 2025-01-01)", "fair evaluation of reasoning language models under a fixed thinking token budget versus each model's default best reasoning mode", ["2610.03509","2610.13570","2608.20256","2608.26235","2608.07968","2608.12150","2606.23181","2605.28398","2604.10739","2605.07686","2510.07364"]),
    ("orx discover keyword", "flips quantized model answers change accuracy is not all you need", ["2609.07664","2610.19498","2606.00206","2407.09141"]),
    ("orx discover embedding (published-after 2025-06-01)", "contamination-free LLM benchmark built from problems released after the models' training cutoff, continuously updated", ["2609.27510","2609.24555","2607.01813","2605.00674","2605.19999","2605.21543","2606.26101","2602.24173"]),
    ("orx discover keyword", "equivalence testing TOST non-inferiority margin LLM evaluation", ["2603.10889","2609.13714","2604.06499","2610.11145"]),
    ("orx discover embedding", "reporting a Pareto frontier of accuracy against memory footprint or inference cost with uncertainty when comparing compressed language models", ["2610.02462","2609.08307","2609.00665","2608.26926","2606.04063","2605.23071","2606.01850"]),
    ("orx discover keyword", "larger quantized model versus smaller full-precision model same memory budget", ["2610.17637","2610.18642","2609.29999","2609.26708"]),
    ("orx discover embedding", "comparing a slow large model against a fast small model at equal wall-clock time using repeated sampling and majority voting", ["2610.15372","2608.11403","2608.14079","2603.27844","2509.21091"]),
    ("orx discover keyword", "Not all bits are equal scale-dependent memory optimization strategies for reasoning models", ["2510.10964"]),
    ("orx discover keyword", "cost-accuracy Pareto frontier agents evaluation joint optimization", ["2609.17863","2609.24971","2606.16111"]),
    ("orx discover embedding", "statistical uncertainty in Pareto frontier membership, bootstrap probability that a model is Pareto optimal across accuracy and cost", ["2508.17622","2503.21495","2511.04457"]),
    ("orx discover keyword", "verifiable instruction following IFBench out-of-distribution constraints", ["2609.14992","2610.19525","2610.05278"]),
    ("orx discover openalex", "constrained simultaneous confidence intervals for multiple comparisons with the best", ["10.1214/aos/1176346732","10.1080/03610928508829027","10.1016/0378-3758(92)90067-3"]),
    ("orx discover openalex", "equivalence tests practical primer t tests correlations meta-analyses", ["10.31234/osf.io/97gpc"]),
    ("orx discover embedding", "does low-bit quantization erase memorized benchmark answers more than reasoning ability, contamination interacting with quantization", ["2610.06174","2609.07901","2609.23125"]),
    ("orx discover embedding", "anytime-valid sequential testing or group sequential design with early stopping for comparing two language models to save evaluation compute", ["2609.28560","2608.14425","2607.17409","2608.03437","2609.25645"]),
    ("WebSearch", "MathArena new competition results September 2026", ["matharena.ai/competitions"]),
    ("WebSearch", "LiveCodeBench release v7 2026 problems after", ["github.com/LiveCodeBench/LiveCodeBench (no v7 found)"]),
    ("WebSearch", "SWE-rebench leaderboard 2026 fresh tasks decontaminated monthly", ["hub.harborframework.com swe-rebench","benchlm.ai swe-rebench"]),
    ("WebSearch", "MoonshotAI K2-Vendor-Verifier tool call schema accuracy providers", ["evalscope k2_verifier docs","platform.kimi.ai K2VV newsletter"]),
    ("WebSearch", "\"LiveBench 2.0\" contamination-free long-horizon benchmark release", ["arXiv 2406.19314 only; no 2.0 found"]),
    ("WebSearch", "Berkeley Function Calling Leaderboard BFCL V4 AST evaluation paper ICML 2025", ["icml.cc/virtual/2025/poster/46593","gorilla.cs.berkeley.edu/leaderboard.html"]),
]


def recs(cell: str, rows: list) -> list[dict]:
    return [{"cell": cell, "tool": t, "query": q, "returned_ids": ids, "counted": True} for t, q, ids in rows]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    synth = json.loads((HERE / "synthesis-queries.json").read_text(encoding="utf-8"))
    for r in synth:
        r["counted"] = True
    records = recs("frontier", FRONTIER) + recs("kill_shot", KILLSHOT) + recs("cross_domain", CROSS) + synth
    counts = {
        "frontier": len(FRONTIER), "kill_shot": len(KILLSHOT), "cross_domain": len(CROSS),
        "asset_cost": 13, "synthesis": len(synth),
    }
    counts["total_counted"] = sum(counts.values())
    counts["declared"] = 150
    counts["reserved_for_refuters"] = 30
    counts["remaining_after_synthesis"] = 150 - counts["total_counted"]
    counts["orx_discover_records"] = sum(1 for r in records if r["tool"].startswith("orx discover"))
    ids = [i for r in records for i in r["returned_ids"]]
    out = {
        "gauntlet": "lm1-matched-memory-quality, wave 1",
        "source_cutoff": "2026-10-15",
        "counting_rule": "every orx discover, web search, GitHub search and Hugging Face search that reaches a backend counts; orx paper fetches, fixed-URL fetches, Hub API reads by id and repository reads do not",
        "counts": counts,
        "asset_cell_note": "the asset and cost cell reported queries_used = 13 without query strings or returned ids; counted, not itemized",
        "prisma": {"ids_returned": len(ids), "unique_ids": len(set(ids)),
                   "read_beyond_abstract_approx": 35, "direct_priors": 0,
                   "closest_or_narrowing": ["2509.25689", "2504.02010", "2604.18556", "2610.15372"]},
        "uncounted_reads_by_synthesis": {
            "orx_paper_full": ["2509.25689", "2504.02010", "2610.15372", "2604.18556", "2404.05405", "2508.10925"],
            "orx_paper_abstract": ["2604.24827", "2609.12111", "2610.02462", "2609.06076", "2505.24832"],
            "hub_api_and_cards": ["ArtificialAnalysis/AA-Omniscience-Public@e4883edb", "google/simpleqa-verified@0dc97e0d",
                                  "m-a-p/SuperGPQA@4430d445", "moonshotai/Kimi-K2.5@4d01dfe0",
                                  "Qwen/Qwen3-235B-A22B-Instruct-2507@ac9c66cc", "deepseek-ai/DeepSeek-V4-Flash-0731@7872f01b",
                                  "Qwen/Qwen3.8-27B@1d4bf0f2"],
            "github_at_commit": ["ggml-org/llama.cpp@620d2225 tools/server/README.md", "ggml-org/llama.cpp@620d2225 docs/multi-gpu.md"],
            "web_pages": ["artificialanalysis.ai/models/comparisons/deepseek-v4-flash-vs-kimi-k2-6",
                          "artificialanalysis.ai/evaluations/omniscience", "artificialanalysis.ai/models/kimi-k2-5",
                          "artificialanalysis.ai/models/qwen3-8-27b"],
            "host": "one read-only nvidia-smi, squeue and free check at 2026-10-16T04:29:40Z",
        },
        "records": records,
    }
    raw = json.dumps(out, indent=1, ensure_ascii=False) + "\n"
    Path(args.out).write_text(raw, encoding="utf-8")
    print(json.dumps(counts), hashlib.sha256(raw.encode()).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
