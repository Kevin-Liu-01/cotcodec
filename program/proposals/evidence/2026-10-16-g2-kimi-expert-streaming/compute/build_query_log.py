#!/usr/bin/env python3
"""Build query-log.json for the G2-stream gauntlet (wave 1) from the discovery cells' own records.

The four cells (frontier, kill-shot, cross-domain, asset and cost) ran independently and read-only
before the synthesis and returned their queries with the ids each returned; they saved no raw
outputs, so there are no per-query raw digests. The synthesis owner ran no search (only fetches of
known URLs and orx full-text reads, listed under `uncounted_reads`). Counting rule: every orx
discover, web search, GitHub search and Hugging Face search that reached a backend counts against
the gauntlet's 150 (the task's rule); direct fetches by URL or id do not.

Usage: python3 build_query_log.py --out ../query-log.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

FRONTIER = [
    ("orx discover keyword", "expert routing trace Kimi K2 expert cache hit rate", ["2607.24653", "2608.12103", "2610.07332", "2610.07333", "2610.01950", "2609.04895", "2610.13328", "2608.08650", "2609.33252", "2609.36724", "2609.33385", "2609.38090", "2610.00671", "2610.09372", "2609.38823", "2609.13058", "2607.00466", "2609.18752", "2608.07911", "2507.20534"]),
    ("orx discover keyword", "expert cache hit rate LRU routing trace DeepSeek-V3 offloading", ["2609.19969", "2610.01950", "2609.33385", "2609.12978", "2608.12103", "2609.34077", "2609.04895", "2609.27746", "2609.28870", "2608.07911", "2610.07668", "2609.38090", "2609.32278", "2610.01265", "2608.02989", "2609.18063", "2608.18261", "2608.07009", "2609.02027", "2412.19437"]),
    ("orx discover keyword", "temporal locality expert activation consecutive tokens reuse distance mixture-of-experts", ["2609.22471", "2609.36959", "2609.18176", "2609.33385", "2608.21614", "2607.12696", "2610.13328", "2608.05303", "2604.23150"]),
    ("orx discover keyword", "SSD expert streaming Apple Silicon unified memory MoE decode tokens per second", ["2609.18110", "2608.24938", "2609.18063", "2610.01950", "2609.34117", "2607.22785", "2609.19169", "2610.07219", "2609.38090", "2610.15417", "2608.11688", "2608.23841"]),
    ("orx discover keyword", "trace-driven simulator expert offloading validated against measured decode throughput", ["2610.02732", "2610.01950", "2609.34117", "2609.34555", "2609.12978", "2608.07911", "2605.17889", "2610.01265", "2608.12103", "2608.21614", "2608.14333"]),
    ("orx discover keyword", "Kimi-K2 expert offloading cache 384 experts", ["2607.24653", "2610.01950", "2507.20534", "2608.12103", "2609.12978", "2609.38090", "2608.02989", "2609.04895", "2610.01265", "2608.30181", "2608.21693"]),
    ("orx discover keyword", "Belady optimal expert caching mixture-of-experts LFU LRU comparison", ["2609.07566", "2609.38090", "2609.12978", "2608.07911", "2609.29032", "2609.28870", "2608.18261", "2608.12103", "2608.21614"]),
    ("orx discover embedding", "Measuring expert routing locality and expert cache hit rates of a trillion-parameter MoE model on real chat, coding, agentic tool-use and long-document workloads, and replaying the traces through LRU, LFU and pinned caches", ["2609.28870", "2609.32283", "2609.04895", "2610.07219", "2610.15366", "2609.02027", "2608.00101", "2608.12103", "2608.26612", "2608.18261"]),
    ("orx discover embedding", "A trace-driven performance model that predicts decode tokens per second of MoE expert streaming from SSD on a laptop with unified memory, calibrated and validated against measured hardware runs", ["2609.18063", "2609.18110", "2610.15629", "2610.15366", "2609.09800", "2609.14864", "2608.12103", "2608.02989", "2607.17283"]),
    ("orx discover embedding", "Running a 1 trillion parameter MoE model on a consumer laptop by streaming experts from flash storage with an expert cache", ["2608.16157", "2609.18063", "2609.18110", "2609.14643", "2610.07219", "2610.01950", "2609.06551", "2607.09686", "2604.02715", "2601.17063", "2603.09983"]),
    ("orx discover keyword --published-after 2025-01-01", "expert popularity skew domain shift hot experts Jaccard coding chat workloads", ["2610.00671", "2607.11586", "2610.01950", "2606.16824", "2609.38090", "2607.16721", "2608.12103", "2606.30560"]),
    ("orx discover keyword --published-after 2025-01-01", "cross-layer expert correlation prefetch next layer gate prediction offloading", ["2610.01950", "2609.33385", "2609.12978", "2610.01265", "2608.21240", "2609.38090", "2609.18063", "2605.05899", "2607.24787", "2509.23638"]),
    ("orx discover embedding", "public dataset of MoE router traces (per-token expert IDs per layer) released for systems research on expert caching", ["2608.16157", "2609.18063", "2610.01950", "2609.34634", "2510.05497", "2508.17137", "2505.20225", "2401.14361"]),
    ("orx discover openalex", "expert offloading mixture-of-experts inference cache hit rate", ["10.48550/arxiv.2505.16056", "10.5281/zenodo.21856980", "10.48550/arxiv.2312.17238", "10.5281/zenodo.22711486", "10.48550/arxiv.2601.17063", "10.48550/arxiv.2410.17954", "10.21203/rs.3.rs-11268552/v1", "10.48550/arxiv.2602.03495", "10.48550/arxiv.2411.01433", "10.24963/ijcai.2026/657", "10.48550/arxiv.2610.01950", "10.48550/arxiv.2512.12990"]),
    ("orx discover openalex", "mixture of experts expert activation prediction prefetching locality inference", ["10.48550/arxiv.2511.14102", "10.48550/arxiv.2608.11688", "10.48550/arxiv.2604.23150", "10.48550/arxiv.2410.17954", "10.24963/ijcai.2026/657", "10.21203/rs.3.rs-10741449/v1", "10.48550/arxiv.2505.16056", "10.48550/arxiv.2608.18261", "10.48550/arxiv.2603.27624", "10.48550/arxiv.2512.03927"]),
    ("orx discover keyword", "Patterns behind Chaos forecasting data movement MoE expert activation profiling", ["2609.36959", "2510.05497", "2608.21614", "2609.00407", "2610.01950", "2609.14643", "2610.07332"]),
    ("orx discover embedding", "expert routing locality in multi-turn agentic tool-use sessions: reuse of experts across turns and its effect on expert caching for MoE inference", ["2610.07332", "2610.11775", "2609.04895", "2610.02951", "2605.26297", "2605.26289"]),
    ("orx discover keyword --published-after 2025-06-01", "quantization changes expert routing top-k agreement low-bit MoE router flips", ["2609.32581", "2610.20353", "2610.10616", "2609.04895", "2610.07332", "2610.01950", "2605.23078", "2609.38090"]),
    ("orx discover keyword --published-after 2026-04-01", "DeepSeek-V4-Flash expert cache hit rate GLM-5 routing locality offloading", ["2609.19969", "2610.01950", "2609.15627", "2606.19348", "2609.12978", "2607.00466", "2609.04895", "2609.39131", "2608.16157"]),
    ("orx discover keyword", "SpecMD Least-Stale eviction expert caching prefetch framework", ["2602.03921", "2609.38090", "2608.07911", "2609.12978", "2610.01950", "2608.21240", "2609.29032", "2608.12103"]),
    ("orx discover keyword --published-after 2026-03-01", "M5 Max MacBook mixture-of-experts SSD streaming expert cache decode measured", ["2609.19969", "2609.18110", "2609.34117", "2609.18063", "2608.08910", "2608.18261", "2608.12103", "2607.09686", "2607.00466"]),
    ("orx discover embedding", "emulating a target laptop's LLM decode throughput on a server by replaying measured expert routing traces through a cache model plus storage and memory bandwidth constants, checked against measurements on the real laptop", ["2609.39131", "2610.15366", "2610.15629", "2609.32283", "2610.09778", "2610.04537", "2610.02732", "2609.09800", "2609.08307"]),
    ("orx discover keyword", "DwarfStar ds4 antirez SSD streaming Metal DeepSeek V4 Flash", ["2609.19969", "2609.15627", "2606.19348", "2608.08910", "2609.18110", "2609.16161", "2608.25062", "2609.18063"]),
    ("orx discover keyword --published-after 2025-11-01", "Kimi-K2-Thinking expert selection trace prefill decode correlation", ["2607.24653", "2609.34117", "2608.24938", "2607.00466", "2608.03741", "2610.01950"]),
    ("WebSearch", "\"Kimi K2\" expert cache hit rate offloading routing trace", ["arxiv 2608.07911", "arxiv 2605.27081", "arxiv 2608.18261"]),
    ("WebSearch", "Kimi K2.6 SSD expert streaming Mac 128GB tokens per second llama.cpp mmap", ["willitrunai.com (estimates)", "aipricing.guru Deltafin article"]),
    ("WebSearch", "Kimi K2 专家 缓存 命中率 卸载 路由 局部性", []),
    ("WebSearch", "KTransformers Kimi-K2 \"expert\" activation statistics GPU experts hit rate kt-num-gpu-experts", []),
    ("GitHub search repos", "moe expert cache simulator", []),
    ("GitHub search repos", "kimi expert routing trace", []),
    ("GitHub search repos", "\"expert cache\" moe", ["yalun753/moe-l2", "ongunm/llama-moe-cache", "CAN230921/moe-expert-cache", "davetha/vllm-expert-cache", "shijiuzhang/moe-cache-eval", "szibis/mlx-flash", "georgemoncure/moe-expert-cache"]),
    ("Hugging Face dataset search (5 searches)", "expert trace / routing trace / expert selection / moe trace / kimi routing", ["core12345/MoE_expert_selection_trace", "woongkk/s26-moe-expert-io-trace", "aswinkumar99/qwen3.8-flash-next-expert-traces", "RASMUS/commitmoe-qwen35-fp8-expert-routing-traces", "CMU-FLAME/FLAME-MoE-Traces", "satsder/qwen3.8-flash-next-routing-traces", "Carloriezo/MoE_expert_selection_trace"]),
]
FRONTIER_COUNT = 37  # 24 orx discover + 5 web + 3 GitHub + 5 HF dataset searches (the cell's own count)

KILLSHOT = [
    ("orx discover keyword", "Kimi K2 expert cache hit rate", ["2607.24653", "2507.20534", "2608.12103", "2609.04895", "2607.kimi-k3", "2510.26692", "2609.27746", "2608.30181", "2610.13060", "2609.35263", "2602.02276", "2610.01950", "2609.33252", "2610.10579", "2610.13328"]),
    ("orx discover keyword", "Kimi-K2 routing trace expert locality LRU", ["2607.24653", "2507.20534", "2609.33385", "2610.07333", "2607.00466", "2609.36724", "2610.07332", "2609.23460", "2608.08650", "2608.18261", "2609.07566", "2607.kimi-k3", "2610.09372", "2610.00671", "2608.12103"]),
    ("orx discover keyword", "Kimi-K2 expert offloading SSD streaming hit rate", ["2607.24653", "2609.18110", "2507.20534", "2609.18063", "2610.01950", "2609.12978", "2609.33385", "2607.kimi-k3", "2610.02652", "2608.30181", "2602.02276", "2609.36938", "2610.01265", "2608.12103", "2510.26692"]),
    ("orx discover embedding", "measured expert routing traces of a trillion-parameter MoE with 384 experts top-8 replayed through LRU and LFU expert caches to estimate cache hit rates and decode speed when streaming experts from SSD on a laptop", ["2609.18063", "2609.18110", "2609.14643", "2610.01950", "2609.04895", "2610.07219", "2610.15366", "2608.14333", "2609.15636", "2608.12103", "2608.26612", "2608.18261", "2608.07911", "2607.24434", "2607.24787"]),
    ("orx discover keyword", "expert-cache cliff LRU working set k L trillion-parameter projection", ["2608.12103", "2609.27746", "2609.32278", "2609.18110", "2609.07175", "2609.29032", "2609.15636", "2608.28911", "2610.05744", "2610.08430"]),
    ("orx discover keyword", "Apple Silicon MoE expert streaming SSD simulator predicts decode tokens per second validated", ["2609.18110", "2609.34117", "2609.18063", "2608.24938", "2610.19232", "2610.01950", "2610.15417", "2610.16890", "2610.13328", "2610.02732", "2609.36959", "2610.07219", "2609.33385", "2607.00466", "2608.23841"]),
    ("orx discover embedding", "analytical performance model of SSD expert offloading for mixture-of-experts on Apple M-series unified memory calibrated against measured decode throughput", ["2609.18110", "2609.14643", "2609.12978", "2610.01950", "2608.14333", "2609.18066", "2608.13127", "2609.14864", "2607.00501", "2607.24787", "2606.27098", "2607.09686", "2605.04178", "2604.18788", "2604.10152"]),
    ("orx discover keyword", "quantization changes expert selection top-k routing agreement low-bit MoE router flip", ["2610.07332", "2609.32581", "2610.00367", "2610.20353", "2609.13058", "2610.10616", "2610.07333", "2608.04401", "2610.05744", "2607.20981", "2609.05228", "2609.04895", "2609.08115", "2609.32821", "2608.25276"]),
    ("orx discover keyword --published-after 2025-06-01", "DeepSeek-V3 expert cache hit rate decode trace LRU offloading", ["2609.19969", "2610.01950", "2609.33385", "2608.12103", "2609.12978", "2609.32278", "2609.34555", "2608.07009", "2609.04895", "2609.34117", "2609.27746", "2610.07668", "2609.28870", "2608.07911", "2608.18261"]),
    ("orx discover openalex", "mixture of experts expert offloading cache hit rate routing trace", ["10.5281/zenodo.21856980", "10.5281/zenodo.22711486", "10.21203/rs.3.rs-11268552/v1", "10.48550/arxiv.2603.19289", "10.24963/ijcai.2026/657", "10.48550/arxiv.2608.18261", "10.48550/arxiv.2610.01950", "10.48550/arxiv.2601.17063", "10.48550/arxiv.2605.05899", "10.48550/arxiv.2511.10054", "10.48550/arxiv.2604.23150", "W7202319636", "10.1145/3794845", "10.48550/arxiv.2401.14361", "10.48550/arxiv.2608.12103"]),
    ("WebSearch", "Kimi K2 expert routing trace cache hit rate LRU offloading 384 experts", ["arxiv 2511.14102", "arxiv 2512.16473", "mkvn-moe-expert-cache-cliff.static.hf.space", "arxiv 2505.16056", "themenonlab.blog kimi-k2-1t-macbook-rustane", "arxiv 2412.00099", "arxiv 2511.05814"]),
    ("WebSearch", "Kimi K2.6 SSD streaming M5 Max 128GB tok/s flash-moe", ["siliconflow.com kimi-k2-6", "willitrunai.com kimi-k2-6-on-m2-max-96gb", "llmrun.dev nvidia-kimi-k2-6-dflash"]),
    ("gh search issues", "Kimi K2 expert cache hit rate", []),
    ("gh search issues", "kimi expert cache", []),
    ("gh search repos", "kimi k2 ssd streaming experts", []),
    ("gh search repos", "kimi streaming experts mac", []),
    ("gh search repos", "flash-moe", ["danveloper/flash-moe", "Anemll/flash-moe", "Anemll/Flash-iOS", "Anemll/anemll-flash-llama.cpp", "PrimeIntellect-ai/prime-flash-moe"]),
]
KILLSHOT_COUNT = 17

CROSS = [
    ("orx discover openalex", "SHARDS efficient online miss ratio curve construction spatial sampling", ["10.5555/2750482.2750490", "10.48550/arxiv.1804.01972", "10.1145/3185751", "10.1145/3299706.3210571", "10.37099/mtu.dc.etdr/653"]),
    ("orx discover openalex", "Evaluation techniques for storage hierarchies stack algorithms", ["10.1145/182.358467", "10.1098/rsta.2019.0055", "10.1145/225535.225539", "10.1145/58564.59296", "W190085180"]),
    ("orx discover openalex", "Trace-driven memory simulation: a survey", ["10.1007/3-540-46506-5_5", "10.1145/267580.269951", "10.1145/254180.254184", "W4389457357", "10.1145/76738.76871"]),
    ("orx discover openalex", "SMARTS accelerating microarchitecture simulation via rigorous statistical sampling", ["10.1109/isca.2003.1206991", "10.1145/1061267.1061272", "10.1109/sc41404.2022.00084", "10.1145/3656012", "W2398399613"]),
    ("orx discover openalex", "Measuring experimental error in microprocessor simulation", ["10.1145/375212.379271", "10.1145/379240.565338", "10.1109/isca.2001.937455", "10.1145/379377.379271", "10.1145/511120.511122"]),
    ("orx discover openalex", "Temporal locality in today's content caching: why it matters and how to model it", ["10.1145/2541468", "10.1109/tmm.2015.2458043", "10.1145/2660129.2660143", "10.1109/twc.2017.2762661"]),
    ("orx discover openalex", "A versatile and accurate approximation for LRU cache performance", ["10.48550/arxiv.1202.3974", "W7214273135", "10.1145/3239164", "10.1109/itc.2014.6932936"]),
    ("orx discover openalex", "Predicting whole-program locality through reuse distance analysis", ["10.1145/780822.781159", "10.1145/781131.781159", "10.1145/781158.781159", "10.1145/1552309.1552310"]),
    ("orx discover openalex", "The accuracy of trace-driven simulations of multiprocessors", ["10.1145/166955.167001", "10.1145/166962.167001", "W1582530102", "10.1007/978-1-4613-1537-7_3"]),
    ("orx discover openalex", "HOTL a higher order theory of locality footprint miss ratio shared cache composition", ["W2205356921", "10.1145/3185751", "10.1145/3018743.3018759", "10.1145/3134437"]),
    ("orx discover openalex", "Talus simple way to remove cliffs in cache performance", ["10.1109/hpca.2015.7056022", "W2311055650", "10.3390/app13063556", "10.1145/3297858.3304067"]),
    ("orx discover openalex", "FIFO queues are all you need for cache eviction", ["10.1145/3600006.3613147", "10.14778/3785297.3785299", "10.48550/arxiv.2502.02750", "10.48550/arxiv.2608.27975"]),
    ("orx discover openalex", "A study of integrated prefetching and caching strategies", ["10.1145/223586.223608", "10.1145/223587.223608", "10.1145/233008.233052", "10.1016/j.ic.2005.01.003"]),
    ("orx discover openalex", "Quantifying performance bottlenecks of stencil computations using the Execution-Cache-Memory model", ["10.1145/2751205.2751240", "10.1137/070693199", "10.48550/arxiv.1509.03118"]),
    ("orx discover openalex", "Producing wrong data without doing anything obviously wrong", ["10.1145/1508244.1508275", "10.1145/1508284.1508275", "10.1145/2528521.1508275"]),
    ("orx discover openalex", "Rigorous benchmarking in reasonable time", ["10.1145/2464157.2464160", "10.1145/2491894.2464160", "10.1145/2555670.2464160"]),
    ("orx discover openalex", "The unwritten contract of solid state drives", ["10.1145/3064176.3064187", "10.1109/dac63849.2025.11132948", "W61554827"]),
    ("orx discover openalex", "Cache modeling and optimization using miniature simulations", ["W2740361432", "10.1145/3185751", "10.1145/2541228.2541236"]),
    ("orx discover openalex", "A comparison of trace-sampling techniques for multi-megabyte caches", ["10.1109/12.286300", "W1594170083", "10.1145/195473.195524"]),
    ("orx discover openalex", "Evaluation techniques for storage hierarchies IBM Systems Journal Mattson", ["W190085180", "10.1145/224057.224065", "W1576469599"]),
    ("orx discover openalex", "Calibration of microprocessor performance models", ["10.1109/2.675637", "10.1007/978-981-10-3159-5_3", "10.14288/1.0065506"]),
    ("OpenAlex DOI filter lookup", "doi: 10.1147/sj.92.0078 | 10.1147/sj.52.0078 | 10.1145/605397.605403 | 10.1109/jsac.2002.801752 | 10.1145/321623.321632 | 10.1214/aos/1176347265 | 10.1145/1297027.1297033 | 10.1145/1250662.1250713 | 10.1109/pact.2002.1106006", ["10.1214/aos/1176347265", "10.1145/605397.605403", "10.1147/sj.52.0078", "10.1147/sj.92.0078", "10.1145/1297027.1297033", "10.1109/jsac.2002.801752", "10.1145/1250662.1250713", "10.1145/321623.321632", "10.1109/pact.2002.1106006"]),
    ("orx discover keyword", "mixture-of-experts expert cache miss ratio curve reuse distance stack distance", ["2609.28870", "2609.22471", "2610.13328", "2609.18176", "2608.18261", "2608.12103", "2609.10266", "2610.14644", "2607.09686", "2608.08650"]),
    ("orx discover embedding", "Trace-driven simulation of expert offloading caches for mixture-of-experts language models, using reuse-distance analysis, miss-ratio curves, Belady optimal bound, and validation of a performance model against measured hardware throughput", ["2609.28870", "2610.15755", "2610.15366", "2609.12978", "2609.28006", "2609.16215", "2610.02766", "2608.14333", "2609.02027", "2609.15030"]),
    ("OpenAlex DOI filter lookup", "doi: 10.1145/2451116.2451153 | 10.1145/1168857.1168881 | 10.1109/ispass.2010.5452069 | 10.1145/107971.107981 | 10.1145/1498765.1498785 | Murphy 1988 MWR | Fagin 1977 (did not resolve) | 10.1145/2465529.2465542 (wrong guess, unused)", ["10.1145/1498765.1498785", "10.1175/1520-0493(1988)116<2417:ssbotm>2.0.co;2", "10.1145/1168857.1168881", "10.1109/ispass.2010.5452069", "10.1145/2451116.2451153", "10.1145/107971.107981", "10.1145/2465529.2465542"]),
    ("OpenAlex DOI filter lookup (abstracts)", "abstracts for 10.1145/2451116.2451153, 10.1145/1168857.1168881, 10.1145/107971.107981, 10.1109/pact.2002.1106006, 10.1145/1250662.1250713, 10.1145/605397.605403", ["10.1145/605397.605403", "10.1145/1168857.1168881", "10.1145/1250662.1250713", "10.1145/2451116.2451153", "10.1109/pact.2002.1106006", "10.1145/107971.107981"]),
]
CROSS_COUNT = 26

ASSET = [
    ("Hugging Face dataset search", "kimi-k2.6", ["0xSero/kimi-k2.6-reap-observations-v1", "rex099/Kimi-K2.6-Thinking-200x-Cleaned", "uniquealexx/Kimi-K2.6-Thinking-200x", "trjxter/Kimi-K2.6-Technical-Reasoning-AddOn-3300x", "DJLougen/Talos-kimi-k2.6-Hermes-synthetic", "(others not listed by the cell)"]),
    ("Hugging Face dataset search", "kimi-k2-thinking", ["(ids not listed by the cell)"]),
]
ASSET_COUNT = 2

UNCOUNTED_SYNTHESIS = [
    "orx paper 2608.12103 --full; 2608.07911 --full; 2510.05497 --full; 2609.14864 --full; 2608.16157 --full (targeted reads of replay semantics, K2 locality numbers, MAPE, LRU miss rates)",
    "GitHub raw and API reads of antirez/ds4 at fc80bd69 (main) and 90aa4b56 (2026-09-06): docs/SSD_STREAMING.md, QA_BEFORE_RELEASES.md, README.md, docs/PERFORMANCE.md, ds4_metal.m, ds4.c, ds4_bench.c, ds4_ssd.c, the recursive tree listing and three file metadata reads",
    "GitHub API reads of Anemll/anemll-flash-llama.cpp at a809594f: README.md, docs/moe-bank-modeling-workflow.md, repository metadata",
    "Hugging Face API metadata: core12345/MoE_expert_selection_trace, 0xSero/kimi-k2.6-reap-observations-v1, ten workload datasets, unsloth/Kimi-K2.6-GGUF, antirez/glm-5.3-gguf, antirez/deepseek-v4-gguf",
    "One web page fetch: themenonlab.blog/blog/kimi-k2-1t-macbook-rustane",
    "Source snapshots of every URL the proposal cites (compute/snapshot_sources.py)",
]


def recs(cell, rows):
    return [{"cell": cell, "tool": t, "query": q, "returned_ids": ids} for t, q, ids in rows]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    queries = recs("frontier", FRONTIER) + recs("kill-shot", KILLSHOT) + recs("cross-domain", CROSS) + recs("asset-cost", ASSET)
    orx = sum(1 for r in queries if r["tool"].startswith("orx discover"))
    ids = [i for r in queries for i in r["returned_ids"]]
    counts = {
        "frontier": FRONTIER_COUNT, "kill_shot": KILLSHOT_COUNT, "cross_domain": CROSS_COUNT, "asset_cost": ASSET_COUNT,
        "synthesis": 0,
        "total_counted": FRONTIER_COUNT + KILLSHOT_COUNT + CROSS_COUNT + ASSET_COUNT,
        "declared": 150, "reserved_for_refuters": 30,
        "remaining_after_synthesis": 150 - (FRONTIER_COUNT + KILLSHOT_COUNT + CROSS_COUNT + ASSET_COUNT),
        "orx_discover_records": orx,
    }
    out = {
        "schema": "g2stream query log v1",
        "counting_rule": "every orx discover, web search, GitHub search and Hugging Face search that reached a backend counts; fetches by URL or id do not",
        "counts": counts,
        "prisma": {"identified_ids": len(ids), "unique_ids": len(set(ids)),
                   "read_beyond_abstract": "about 45 (cells: 8 frontier full texts plus about 30 targeted; 13 kill-shot; 3 cross-domain plus 6 PDFs; synthesis: 5 orx full texts, ds4 and Anemll sources)",
                   "direct_priors": 0, "narrowing_priors": 7},
        "queries": queries,
        "uncounted_reads_synthesis": UNCOUNTED_SYNTHESIS,
        "raw_outputs": "none saved by the cells; ids transcribed from their returned records",
    }
    args.out.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(counts), "ids", len(ids), "unique", len(set(ids)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
