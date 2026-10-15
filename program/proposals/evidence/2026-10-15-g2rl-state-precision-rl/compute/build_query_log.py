#!/usr/bin/env python3
"""Build query-log.json for the G2-RL gauntlet from the discovery cells' returned query records.

The cells (frontier and novelty, kill-shot, cross-domain, asset and cost) ran independently and
returned their queries with the ids each returned; this script records them verbatim as data,
adds the synthesis owner's reads, and computes the counts under the two counting conventions the
proposal's "Budget accounting" section describes. The cells' raw outputs were not saved as files,
so there is no raw-output digest per query (unlike the R01 repair's log); the cells' own coverage
statements are copied in full.

Usage (repo root): python3 build_query_log.py --out query-log.json
"""

from __future__ import annotations

import argparse
import json

KW, EM, OA = "orx discover keyword", "orx discover embedding", "orx discover openalex"

FRONTIER = [
    (KW, "linear attention state precision reinforcement learning mismatch", ["2610.07043", "2609.32444", "2608.26481", "2609.39034", "2609.38166", "2608.28158", "2606.29526", "2608.30386"]),
    (KW, "Gated DeltaNet reinforcement learning training-inference mismatch", ["2605.22791", "2609.32444", "2609.14320", "2608.20961", "2609.20807", "2610.07043", "2609.04098", "2605.14220"]),
    (KW, "mamba_ssm_cache_dtype", ["2610.13778", "2604.03444"]),
    (KW, "recurrent state bf16 fp32 rollout reinforcement learning", ["2610.07767", "2609.04663", "2604.06916", "2610.16593", "2609.34272", "2610.07043"]),
    (EM, "numerical precision of the recurrent state of linear attention or Gated DeltaNet layers in the rollout inference engine during RL of hybrid LMs, fp32 vs bf16 vs fp16 state, effect on training stability and IS correction", ["2609.20807", "2609.37852", "2610.07043", "2609.22870", "2610.13306", "2609.04098", "2609.39185", "2609.30950"]),
    (KW, "SSM cache dtype float32 reinforcement learning hybrid", ["2610.13778", "2610.01172", "2609.29618", "2609.02029"]),
    (KW, "Defeating the Training-Inference Mismatch via FP16", ["2510.26788", "2609.32444", "2610.05458", "2605.14220", "2604.07853", "2602.01826", "2607.24062"]),
    (KW, "truncated importance sampling rollout training mismatch off-policy", ["2610.18738", "2609.20807", "2609.32444", "2610.09597", "2609.35433"]),
    (KW, "Every Attention Matters hybrid linear attention reinforcement learning", ["2609.31947", "2608.28444", "2608.28158", "2608.12149"]),
    (KW, "Kimi Linear reinforcement learning training inference consistency", ["2607.24653", "2510.26692", "2610.11959", "2607.24062"]),
    (KW, "Ring-linear hybrid linear attention RL training inference alignment", ["2608.28444", "2608.28158", "2609.31947"]),
    (KW, "Qwen3.5 reinforcement learning rollout mismatch linear attention", ["2610.07767", "2610.07043", "2609.20807", "2608.28158"]),
    (KW, "IcePop", ["2510.18855", "2609.32444", "2607.22186", "2607.12395"]),
    (KW, "When Speed Kills Stability training-inference mismatch", ["2609.32444", "2605.14220", "2510.26788", "2604.07853", "2602.01826"]),
    (KW, "Forgetting to Forget bf16 Gated DeltaNet state", ["2605.22791", "2609.04098", "2608.20961", "2608.13668"]),
    (KW, "Low-Bit Recurrent States in Hybrid Language Models", ["2609.30950", "2610.15709", "2609.04098"]),
    (KW, "lightning attention RL LM head fp32 precision probability mismatch", ["2610.07043", "2610.05458", "2609.26621"]),
    (KW, "Mamba hybrid reinforcement learning rollout state precision Nemotron", ["2606.15007", "2604.12374", "2512.20856", "2512.20848", "2608.28158"]),
    (EM, "controlled experiment comparing RL outcomes with reduced-precision vs full-precision rollouts, with and without IS correction such as TIS", ["2609.32444", "2610.07043", "2610.02911"]),
    (EM, "RL of hybrid linear attention LMs (Qwen3-Next, Qwen3.5, Kimi Linear, MiniMax), mismatch from recurrent state kernels (after 2026-01-01)", ["2609.20807", "2609.20751", "2609.32444", "2610.07043", "2609.04434"]),
    (KW, "stochastic rounding SSM cache recurrent state", ["2610.13778", "2609.39185", "2610.15709", "2610.15139", "2609.38166"]),
    (KW, "masked importance sampling sequence-level rollout correction training-inference mismatch", ["2609.20807", "2609.32444", "2610.18738", "2609.15471", "2604.07853"]),
    (KW, "Tapered Off-Policy REINFORCE", ["2503.14286"]),
    (OA, "training-inference mismatch reinforcement learning large language models", ["10.48550/arxiv.2609.32444", "10.48550/arxiv.2605.14220", "10.48550/arxiv.2606.29526", "10.48550/arxiv.2511.17826", "10.48550/arxiv.2510.11370", "10.48550/arxiv.2609.20807", "10.48550/arxiv.2602.01826", "10.48550/arxiv.2607.26515"]),
    (OA, "linear attention hybrid reinforcement learning precision recurrent state", ["(no relevant hits; off-topic RL surveys)"]),
    (KW, "FP8 rollout RL importance sampling correction quantized rollout", ["2610.07767", "2609.22870", "2601.14243", "2602.13953"]),
    (KW, "Qwen3-Next reinforcement learning", ["2603.00729", "2610.07043"]),
    (EM, "recurrent state rounding error accumulates during decoding and makes hybrid generations longer (after 2026-03-01)", ["2610.13778", "2610.15709", "2609.39185", "2610.15139", "2609.38169"]),
    (KW, "training-inference mismatch grows with response length long chain-of-thought position", ["(no relevant hits)"]),
    (KW, "KV cache quantization reinforcement learning rollout throughput mismatch", ["2610.07767", "2610.14448"]),
    (KW, "Trust Region Masking Long-Horizon LLM Reinforcement Learning", ["2512.23075", "2606.10968"]),
    (KW, "Stabilizing Reinforcement Learning with LLMs Formulation and Practices", ["2512.01374"]),
    (KW, "On the Rollout-Training Mismatch in Modern RL Systems truncated importance sampling", ["2609.20807", "2609.32444", "2610.14448"]),
    (KW, "batch invariant bitwise on-policy RL Gated DeltaNet recurrent kernel", ["2605.22791", "2608.20961", "2609.04098"]),
    (EM, "IS correction when rollout-trainer mismatch accumulates with sequence length in long-CoT RL (after 2026-01-01)", ["2609.20807", "2609.32444", "2610.14440", "2608.01418"]),
    (KW, "Qwen3.5 technical report hybrid Gated DeltaNet RL infrastructure", ["2604.15804", "2610.11959"]),
    (KW, "Ring-flash-linear Ling hybrid linear RL KVCache precision FP32", ["2606.15079", "2510.19338"]),
    (KW, "Kimi Delta Attention state precision fp32 bf16", ["2607.24653", "2609.24797", "2609.38169", "2608.27513"]),
    (EM, "low-precision recurrent state cache in rollout engine makes RL off-policy for SSM hybrids; mamba ssm cache fp16 bf16 during RL", ["2610.13778", "2610.07767", "2609.33051", "2610.07043", "2610.14448"]),
    (OA, "Gated DeltaNet hybrid reinforcement learning rollout", ["10.48550/arxiv.2608.28158", "10.48550/arxiv.2604.03444"]),
    (EM, "effect of linear attention recurrent state numerical precision on RL training of hybrid LMs (after 2026-09-01, recency)", ["2610.15709", "2610.07767", "2610.07043", "2610.06750"]),
    (KW, "stochastic rounding rollout reinforcement learning language model", ["(no relevant hits)"]),
    (KW, "hybrid model RL recurrent state drift rollout length off-policy (after 2026-06-01)", ["2609.20807"]),
    (KW, "fp16 recurrent state verbosity longer generations hybrid", ["2609.39185", "2608.27513", "2609.30950", "2609.38169", "2610.15709"]),
]
FRONTIER_WEB = [
    ("WebSearch", "Qwen3.5 GRPO training-inference mismatch linear attention state fp32 bf16 rollout verl OR slime OR miles", ["x.com/YichuanM/status/2085463113189802207", "arxiv 2604.11554", "arxiv 2601.18150", "github.com/ByteDance-Seed/VeOmni/pull/1266"]),
    ("WebSearch", "bitwise exact trainer generator parity Gated DeltaNet Qwen3.5 TorchTitan vLLM async RL", ["yichuan-w.github.io/blog/GDN-train-inference-mismatch-asyncRL/", "vllm.ai/blog/2026-08-21-isoexec", "github.com/PrimeIntellect-ai/prime-rl/pull/3214"]),
    ("WebSearch", "'Your Efficient RL Framework Secretly Brings You Off-Policy RL Training' TIS Feng Yao", ["fengyao.notion.site/off-policy-rl", "neurips.cc/virtual/2025/124259"]),
    ("WebSearch", "'Forgetting to Forget' Gated DeltaNet bf16 recurrent state", ["inferencex.semianalysis.com/glossary/gated-deltanet", "docs.modular.com gated_delta"]),
    ("WebSearch", "RL collapse hybrid bf16 SSM state cache mamba_ssm_cache_dtype float32 GRPO", ["arxiv 2606.15007", "TensorRT-LLM KvCacheConfig docs"]),
]
FRONTIER_READS = {
    "orx paper --full or targeted grep": "2510.19338, 2510.26788, 2510.18855, 2506.13585, 2604.03444, 2605.14220, 2609.32444, 2609.30950, 2610.15709, 2604.12374, 2512.20848, 2510.26692, 2608.28158, 2607.24062, 2603.00729, 2610.14448, 2601.14243, 2602.13953, 2609.22870, 2610.15139, 2512.23075, 2512.01374, 2609.20807, 2606.29526, 2601.18150, 2604.11554, 2606.15079, 2607.24653, 2610.11959, 2604.15804, 2609.39185, 2609.38169, 2610.13306, 2606.15007; report: 2602.01826",
    "WebFetch": "yichuan-w.github.io GDN blog; vllm.ai IsoExec blog; inferencex glossary (succeeded); X post (402); fengyao.notion.site and richardli.xyz/rl-collapse (Notion did not render); openreview 9LUInzhKZc (bot challenge, not bypassed)",
    "GitHub search and API (about 41 searches plus about 25 reads)": "issues 'mamba_ssm_cache_dtype'; code 'mamba_ssm_cache_dtype' and 'mamba_ssm_dtype' in verl, slime, miles, AReaL, NeMo-RL, OpenRLHF, TRL, prime-rl, SkyRL, torchtitan, sglang; SGLang stochastic-rounding PRs; vLLM SR issues/PRs; issue searches for Qwen3.5/Qwen3-Next mismatch; reads of vLLM v0.31.0 config.py, mamba_utils.py, qwen3_next.py, cache.py; SGLang mamba_utils.py and server_arguments.mdx; verl Qwen3.5/Qwen3-Next example scripts and rollout_corr.md; NeMo-RL grpo_nanov3.yaml and #4243; miles #3597; prime-rl #3214; HF config.json for Qwen3-Next-80B-A3B and Qwen3.5-4B/9B",
}

KILLSHOT = [
    (KW, "linear attention recurrent state precision reinforcement learning training-inference mismatch", ["2609.38166", "2609.32444", "2609.36529", "2609.20807", "2610.07043", "2609.39034", "2609.27373", "2606.29526"]),
    (KW, "mamba_ssm_cache_dtype", ["2610.13778", "2604.03444"]),
    (KW, "Gated DeltaNet hybrid reinforcement learning rollout mismatch", ["2605.22791", "2610.16593", "2609.04098", "2610.07767", "2610.07043", "2608.20961", "2609.14320", "2607.07508"]),
    (EM, "Reduced-precision recurrent state in the rollout engine of hybrid linear-attention or Mamba LMs increases train-inference mismatch during RL; does it destabilize training and does IS correction fix it", ["2609.20807", "2609.32444", "2610.04158", "2610.07043", "2609.35378", "2610.18343", "2610.10422", "2610.05292"]),
    (KW, "truncated importance sampling rollout training mismatch RL collapse", ["2609.20807", "2610.16593", "2610.07767", "2609.32444", "2610.14448", "2607.07508", "2605.13907", "2604.07853"]),
    (KW, "bf16 linear attention state RL instability hybrid model", ["2610.08527", "2609.34272", "2607.21553", "2608.30386", "2609.38166", "2608.28158", "2609.31947", "2610.14448"]),
    (KW, "Mamba SSM state precision reinforcement learning rollout fp32 Nemotron", ["2610.13778", "2610.16593", "2606.15007", "2604.12374", "2610.01172", "2610.07767", "2512.20856", "2609.33051"]),
    (KW, "Qwen3.5 GRPO training-inference mismatch linear attention", ["2609.32444", "2604.15804", "2610.11251", "2609.20751", "2608.05600", "2609.39321", "2610.05842", "2605.14220"]),
    (KW, "Kimi Delta Attention reinforcement learning precision mismatch", ["2607.24653", "2609.24797", "2510.26692", "2610.07043", "2609.20807", "2609.38166", "2609.38169"]),
    (EM, "How large must rollout-trainer log-prob mismatch be before it harms RL of LMs", ["2609.20807", "2609.33220", "2610.02835", "2604.06268", "2605.14220", "2602.01826"]),
    (OA, "training-inference mismatch reinforcement learning large language model rollout", ["10.48550/arxiv.2609.32444", "10.48550/arxiv.2604.07853", "10.48550/arxiv.2601.14243", "10.48550/arxiv.2601.10079", "10.48550/arxiv.2605.14220", "10.48550/arxiv.2511.17826", "10.48550/arxiv.2609.20807", "10.48550/arxiv.2610.07767"]),
    (KW, "Low-Bit Recurrent States in Hybrid Language Models", ["2609.30950", "2610.15709", "2610.05265", "2610.13041", "2609.04098", "2609.39185", "2609.38169", "2608.02032"]),
    (KW, "stochastic rounding SSM state cache fp16 Mamba inference", ["2610.13778", "2609.39185", "2603.15569", "2610.01889"]),
    (KW, "Nemotron 3 Nano reinforcement learning mamba state precision rollout", ["2610.16593", "2606.15007", "2604.24954", "2512.20856", "2604.12374", "2512.20848", "2508.14444"]),
    (KW, "Forgetting to Forget bf16 Gated DeltaNet state round-to-nearest", ["2605.22791", "2609.04098", "2608.20961", "2609.14320", "2610.13778"]),
    (KW, "Defeating the Training-Inference Mismatch via FP16", ["2510.26788", "2609.32444", "2610.05458", "2605.14220", "2609.20807", "2606.29526", "2604.07853", "2602.01826"]),
    (EM, "Hybrid linear attention RL: keep linear attention recurrent state FP32 in inference engine to align rollout and training and prevent RL collapse", ["2609.20807", "2610.06647", "2609.37852", "2609.22870", "2607.nvfp4-rl", "2607.24062", "2606.00395"]),
    (KW, "rollout precision ablation RL training curves hybrid Mamba transformer GRPO collapse", ["2610.07767", "2607.07508", "2610.16593", "2601.14243", "2606.15007"]),
    (KW, "bf16 recurrent state Qwen3.5-0.8B generation length fp32 heads excess NLL", ["2609.38169", "2609.30950", "2609.38166", "2608.27513", "2610.15139", "2610.13778"]),
    (KW, "rollout precision RL training curves fp32 bf16 inference engine Gated DeltaNet Qwen3-Next RL", ["2610.07767", "2610.14448", "2610.08430", "2601.14243", "2609.08368", "2607.24062"]),
    (KW, "When Speed Kills Stability training-inference mismatch masked importance sampling", ["2609.32444", "2609.20807", "2605.14220", "2510.26788", "2602.01826", "2606.29526", "2604.07853"]),
    (EM, "Fraction of RL step time spent in rollout generation versus policy training for long-CoT RL on a single node", ["2610.18853", "2609.36830", "2610.13202", "2609.25463", "2608.01418", "2607.09207"]),
    (KW + " (--published-after 2026-01-01)", "recurrent state bfloat16 rollout RL reward GRPO hybrid", ["2610.16593", "2610.09804", "2609.33126", "2608.28158"]),
    (EM, "train a hybrid linear-attention model with RL using reduced-precision recurrent-state rollouts and compare reward curves to full precision", ["2510.26692", "2602.13953", "2507.06457", "2601.11667"]),
    (OA, "linear attention hybrid model reinforcement learning numerical precision rollout", ["10.48550/arxiv.2608.01717", "10.48550/arxiv.2602.04879"]),
]
KILLSHOT_READS = {
    "orx paper --full": "2510.19338, 2609.20807, 2610.14448, 2609.30950, 2604.03444, 2512.20856, 2604.12374, 2512.20848, 2609.39185, 2510.26788, 2609.32444, 2605.14220, 2608.27513, 2602.01826, 2608.28158, 2510.26692",
    "GitHub issue and code searches (about 10) and gh api reads (about 12)": "issues 'mamba_ssm_cache_dtype' (plus 4 queries that returned nothing); code mamba_ssm in NeMo-RL, verl, slime, miles, OpenRLHF, TRL; mamba-ssm-dtype in slime, miles, sglang; stochastic_rounding in vllm; returned NVIDIA-NeMo/RL#4243, vllm#59764, vllm#55524, vllm#53239, NeMo-RL recipes, slime docs, miles qwen3-8.md, vllm config/mamba.py, miles PR #3597",
    "WebFetch": "OpenReview 9LUInzhKZc (bot challenge; not bypassed)",
}

H = " (historical, before {})"
CROSS = [
    (KW, "recurrent experience replay distributed reinforcement learning recurrent state staleness burn-in", ["2609.recurrent-looped-transformer", "2609.18167", "2610.12668", "2609.24456", "2610.13197"]),
    (KW, "V-trace importance weighted actor-learner architecture truncated importance sampling policy lag", ["2610.14440", "2609.36953", "2609.15471", "2610.18738", "2607.15067"]),
    (KW, "statistical precipice interquartile mean stratified bootstrap few runs", ["2607.adaptive-stratified-active-statistical-inference", "2609.33812", "2605.08261"]),
    (KW, "how many random seeds statistical power analysis deep reinforcement learning", ["2608.00133", "2609.28807", "2607.07769", "1806.08295"]),
    (KW + H.format("2022-01-01"), "recurrent experience replay distributed reinforcement learning recurrent state staleness burn-in", ["1511.05952", "1803.00933", "2007.06700", "1507.06527"]),
    (KW + H.format("2020-01-01"), "IMPALA V-trace off-policy correction actor learner policy lag", ["1802.01561", "1909.11583", "1205.4839", "1903.11329"]),
    (KW + H.format("2023-01-01"), "deep reinforcement learning statistical precipice interquartile mean stratified bootstrap", ["2108.13264", "2108.03706", "2205.07802"]),
    (KW + H.format("2023-01-01"), "nondeterminism instability neural network optimization run-to-run variability single bit", ["2103.04514"]),
    (KW + H.format("2026-01-01"), "Mamba state space model quantization hidden state precision sensitivity outliers", ["2312.00752", "2412.20386", "2411.11843"]),
    (KW + H.format("2026-01-01"), "linear attention recurrent state bfloat16 precision error accumulation long sequence", ["2312.00752", "2411.13476", "2510.04212"]),
    (KW + H.format("2024-01-01"), "stochastic rounding probabilistic rounding error analysis stagnation low precision accumulation", ["2207.10321", "2010.16225", "2104.15076", "2207.14598", "2103.13445"]),
    (KW + H.format("2024-01-01"), "recurrent neural networks limited numerical precision fixed point training", ["1710.03740", "1608.06902", "1502.02551", "2212.11791"]),
    (OA, "16-bit arithmetic weather climate shallow water model Float16 BFloat16 posits number formats", ["10.1029/2020ms002246", "10.1029/2021ms002684", "10.1038/s41598-023-37004-4"]),
    (KW + H.format("2024-01-01"), "closer look at deep policy gradients gradient estimate true gradient cosine similarity sample size", ["1811.02553", "2107.11433"]),
    (KW + H.format("2024-01-01"), "breaking the curse of horizon importance sampling variance exponential horizon off-policy estimation", ["1810.12429", "1910.06508", "1909.05850", "2212.03932"]),
    (KW + H.format("2024-01-01"), "policy optimization via importance sampling Renyi divergence effective sample size bound", ["1809.06098", "2110.00641", "1511.01437"]),
    (OA, "Recurrent Experience Replay in Distributed Reinforcement Learning", ["W2908064123"]),
    (KW + H.format("2024-01-01"), "hitchhiker's guide statistical comparisons reinforcement learning algorithms Welch t-test false positive", ["1904.06979", "2108.13264", "1806.08295"]),
    (KW + H.format("2025-01-01"), "empirical design in reinforcement learning hyperparameters seeds confidence intervals", ["2304.01315", "2306.01324", "2412.07165"]),
    (KW + H.format("2025-01-01"), "revisiting bfloat16 training stochastic rounding Kahan summation weight update precision", ["2010.06192", "2408.03069", "2411.13476", "1905.12322"]),
    (EM, "the hidden state of a recurrent policy used by actors drifts from the state the learner recomputes, and this discrepancy grows along the sequence, harming off-policy learning", ["2609.20807", "2610.15139", "2605.14220", "2603.20521"]),
    (EM, "storing the recurrent state of a linear recurrent or state space model in 16-bit floating point causes rounding errors to accumulate over long sequences during inference", ["2609.33093", "2610.15709", "2609.38169", "2610.15139", "2609.39185"]),
    (KW + H.format("2024-01-01"), "low-precision reinforcement learning soft actor-critic half precision fp16", ["2102.13565"]),
    (KW + H.format("2025-06-01"), "Quamba quantization selective state space models recurrent state", ["2410.13229", "2503.22879", "2404.08819"]),
    (KW, "Nemotron 3 Super Mamba state FP16 stochastic rounding generation length", ["2604.12374", "2606.15007", "2512.20856", "2610.13778", "2609.39185"]),
    (OA, "Equivalence tests: a practical primer for t tests, correlations, and meta-analyses", ["10.1177/1948550617697177", "10.1177/2515245918770963"]),
    (OA, "On the use of a pilot sample for sample size determination", ["10.1002/sim.4780141709", "10.1002/bimj.4710380806"]),
    (OA, "Some guidelines and guarantees for common random numbers", ["10.1287/mnsc.38.6.884", "10.48550/arxiv.2605.04732"]),
    (KW + H.format("2024-01-01"), "rethinking the effective sample size importance sampling", ["1809.04129", "1511.01437", "1602.03572", "1507.02646"]),
]
CROSS_WEB = [
    ("WebSearch", "R2D2 Recurrent Experience Replay in Distributed Reinforcement Learning recurrent state staleness representational drift burn-in", ["mlanthology.org/iclr/2019/kapturowski2019iclr-recurrent"]),
    ("WebSearch", "vllm mamba_ssm_cache_dtype stochastic rounding pull request", ["docs.vllm.ai/en/stable/api/vllm/config/mamba/", "nvidia.github.io/TensorRT-LLM KvCacheConfig"]),
    ("WebSearch", "Gelman You need 16 times the sample size to estimate an interaction than to estimate a main effect", ["statmodeling.stat.columbia.edu/2018/03/15/need16/", "statmodeling.stat.columbia.edu/2023/11/09/"]),
]
CROSS_READS = {
    "orx paper --full": "1802.01561 1806.08295 2108.13264 2103.04514 1811.02553 1511.01437 1810.12429 2110.00641 1909.11583 2104.15076 2010.16225 2102.13565 1709.06560 2304.01315 2010.06192 2610.15709 2609.39185 2604.12374 1507.02646",
    "orx paper (OpenAlex metadata)": "10.1029/2020ms002246; 10.1029/2021ms002684; W2908064123; 10.1002/sim.4780141709; 10.1287/mnsc.38.6.884; 10.1177/1948550617697177",
    "WebFetch": "openreview r1lyTjAqYX (bot verification); Wiley 10.1029/2020MS002246 (403); api.semanticscholar.org (429); statmodeling 2018 post (403); docs.sglang.io Nemotron3-Ultra cookbook; docs.vllm.ai MambaConfig; github.com/state-spaces/mamba README; mlanthology R2D2 page",
}

ASSET_READS = {
    "GitHub release, file and API reads": "verl v0.9.1 release and pyproject at v0.9.1 and main f724e7f2; vllm_async_server.py; verl qwen3_5.py; rollout_corr docs; docker/Dockerfile.stable.vllm; verl issues #8154, #6829, #7476, #6662, #6549, #7438 and PR #8072; TRL v1.15.0 grpo_config.py; OpenRLHF v0.11.2; slime v0.4.0; miles v0.1.2; AReaL v2.1.0; vime v0.3.2; flash-attn v2.8.3.post2 wheels; NVIDIA CUDA forward-compatibility table (fetch summary)",
    "Hugging Face API reads": "BytedTsinghua-SIA/DAPO-Math-17k @65877096c24f; open-r1/DAPO-Math-17k-Processed @31dd3095; HuggingFaceH4/MATH-500 @6e4ed1a2; math-ai/aime24 @83a7f387; math-ai/aime25 @563bb840; opencompass/AIME2025 @a6ad95f6; HuggingFaceH4/aime_2024",
    "Host (read-only ssh)": "nvidia-smi, sinfo, squeue, docker image listing, model directory listing at about 03:29 UTC 2026-10-15",
}

SYNTHESIS_READS = {
    "orx paper --full": "2510.19338 (Sections 5.2-5.2.3 read for the closest-prior row and the blind paragraph)",
    "gh api (issue metadata)": "verl #6829, #7438, #8154; vllm #59764; NeMo-RL #4243 (creation dates and state)",
    "source snapshots": "every URL the proposal cites (compute/snapshot_sources.py; 49 records, all HTTP 200; the OpenReview record is a browser-challenge page)",
}


def entries(cell: str, rows: list) -> list[dict]:
    return [
        {"cell": cell, "n": i + 1, "tool": tool, "query": q, "returned_ids": ids}
        for i, (tool, q, ids) in enumerate(rows)
    ]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    orx = entries("frontier", FRONTIER) + entries("kill-shot", KILLSHOT) + entries("cross-domain", CROSS)
    web = entries("frontier", FRONTIER_WEB) + entries("cross-domain", CROSS_WEB)
    by_tool: dict[str, int] = {}
    for e in orx:
        base = e["tool"].split(" (")[0]
        by_tool[base] = by_tool.get(base, 0) + 1
    gh_searches = {"frontier": 41, "kill-shot": 10}
    log = {
        "gauntlet": "G2-RL (2026-10-15)",
        "cutoff": "2026-10-15",
        "orx_version": "0.2.2 (reports itself outdated against 0.2.18)",
        "orx_discover": orx,
        "web_search": web,
        "github_search_counts_approximate": gh_searches,
        "uncounted_reads": {
            "frontier": FRONTIER_READS,
            "kill-shot": KILLSHOT_READS,
            "cross-domain": CROSS_READS,
            "asset-cost": ASSET_READS,
            "synthesis": SYNTHESIS_READS,
        },
        "counts": {
            "orx_discover_by_cell": {"frontier": len(FRONTIER), "kill-shot": len(KILLSHOT), "cross-domain": len(CROSS)},
            "orx_discover_by_mode": by_tool,
            "orx_discover_total": len(orx),
            "web_search_total": len(web),
            "github_search_total_approximate": sum(gh_searches.values()),
            "literature_searches": len(orx) + len(web),
            "all_searches_reaching_a_backend_approximate": len(orx) + len(web) + sum(gh_searches.values()),
            "declared_query_budget": 150,
            "refuter_reserve": 30,
            "convention_note": (
                "Counting literature searches only, 44 queries remain (reserve intact). Counting every search that "
                "reached a backend (the D75 convention), about 157 were used and the budget is exceeded before the "
                "refuters; the orchestrator rules on the convention."
            ),
        },
        "prisma": {
            "identified_ids_orx_discover": sum(len([i for i in e["returned_ids"] if not i.startswith("(")]) for e in orx),
            "unique_ids_orx_discover": len({i for e in orx for i in e["returned_ids"] if not i.startswith("(")}),
            "screened": "by title, all",
            "read_beyond_abstract": 71,
            "direct_priors": 0,
            "narrowing_priors": ["2510.19338", "first-party TorchTitan GDN blog + vLLM IsoExec blog", "2510.26788 / 2610.14448 design template"],
        },
        "raw_output_digests": "not available: the cells returned their query records in their reports and saved no raw orx outputs",
    }
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(log, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print(json.dumps(log["counts"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
