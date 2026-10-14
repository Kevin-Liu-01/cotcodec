# inference-baseline-v1: where time and HBM go when vLLM serves on H100 (2026-10-14)

> **EXPLORATORY. Not a registered experiment.** There is no preregistration, no hypothesis and
> no decision rule here, and nothing below is a confirmatory claim. These are measurements
> taken to ground the D103 area-2 question sweep (hardware memory and GPU acceleration for
> inference and RL). Kevin asked to "just straight up run inference". Every number comes from
> one node, one vLLM build and one day, with two repeats per cell.

## Bottom line (exploratory reading)

- **Single-stream decode is weight streaming for the 9B and 32B models.** At concurrency 1,
  the bytes a decode step must read, divided by the measured median inter-token latency, come
  to about 73-83% of the H100's 3.35 TB/s for Qwen3.5-9B and Qwen3-32B at TP 1-2. They fall to
  about 60% at TP 4, and to 25-61% for the 0.6B-4B models and the 3B-active MoE. Those smaller
  engines cannot fill HBM bandwidth at batch 1, so per-step overhead dominates. (The bandwidth
  figure is an analytical estimate. No hardware counter was read.)
- **HBM is reserved, not used.** `nvidia-smi` reports 72-75 GiB in every run, at any load,
  because vLLM claims 90% of the device at start-up. What varies is what the reservation holds:
  - Qwen3-32B at TP 1: 61.0 GiB of weights leave 6.9 GiB of KV cache, about 28,000 tokens.
  - The same model at TP 4: 878,400 tokens.
  - Qwen3.5-9B holds 1.5 million tokens on one GPU. Its gated-DeltaNet hybrid keeps KV on only
    8 of 32 layers (32 KiB per token, against 256 KiB for Qwen3-32B), plus about 25 MiB of
    recurrent state per sequence.
  - The KV gauge (`vllm:kv_cache_usage_perc`) is the informative memory signal. Device memory
    used is not.
- **KV capacity sets throughput only for the dense models.** The dense engines reached 98-100%
  KV use, some with preemptions:
  - Qwen3-32B TP 1 at chat-128: 1,142 tok/s and a median TTFT of 20 s.
  - Qwen3-32B TP 2 at long-output-128.
  - Qwen3-0.6B and 1.7B with 8k and 32k prompts.

  The hybrids in their main configurations (4B and 9B at TP 1, 35B-A3B at TP 2) never filled
  their KV cache in this grid. The highest reading was 77%. Only the one-GPU MoE, with 4.2 GiB
  of KV, reached 99% at chat-128, without preemptions.
- **FP8 KV doubles capacity, and it helps only where capacity binds.** On Qwen3-32B TP 1:
  - capacity goes from 28,192 to 56,400 tokens;
  - 8k-prompt c8 runs 1.53x faster and chat-128 1.42x;
  - long-output c8 runs 1.28x faster, with no preemptions;
  - a 32k prompt fits on one GPU.

  On Qwen3.5-9B, FP8 KV changes throughput by -6% to -0.5%, because its KV never bound.
- **Prefix caching on shared 4,096-token prefixes** roughly doubles total throughput at
  concurrency 32: 2.1x on Qwen3-1.7B and 2.25x on Qwen3.5-9B. It cuts the median TTFT by
  2.5-6x.
  The hybrid's hit rate was lower: 64-74%, against 82-88% for 1.7B.
- **Concurrency buys throughput, and power ends up the limit.**
  - From c1 to c128 on long output, Qwen3.5-9B goes from 154 to 8,230 tok/s, and the energy per
    output token falls from 2.93 J to 0.084 J.
  - The heaviest cells run at 550-690 W per GPU, against the 700 W limit.
  - In many of them NVML reports the software power cap in 60-93% of samples, and mean SM
    clocks drop from 1,980 to 1,600-1,930 MHz. Not in all: the MoE at TP 2 and the 32B at TP 4
    stayed under the cap at long-output-128 (0-6% of samples).
- **Tensor parallelism buys latency, not efficiency, for the 32B at low load.**
  - Single-stream TPOT is 23.2, 13.2 and 8.1 ms at TP 1, 2 and 4.
  - Output per GPU falls from 43 to 38 to 31 tok/s.
  - Energy rises from 11.2 to 12.8 to 13.4 J per token.
- **Run-to-run spread is small.** The two repeats differ by a median of 1% in output throughput
  and 1% in median TPOT (p90 4-5%, max 8%), and by 2% in median TTFT (p90 14%, max 43%). The
  larger throughput spreads (4-7%) all sit in overhead-bound cells: the 0.6B and 1.7B at low
  concurrency, and the MoE at concurrency 1.
- **Qwen3.6-35B-A3B fits on one H100 only with fewer sequences.** Its 64.7 GiB of weights leave
  room for 181 GDN-state slots, so vLLM refused `max_num_seqs` 256. At 128 it served with 4.17
  GiB of KV (178,499 tokens) and 2,482 tok/s at chat-128.

## What ran

All jobs ran on `fal-h100-01` through Slurm, in the docker-research lane with the digest-pinned
`cotcodec-vllm` overlay (vLLM 0.31.0, commit `db9527a4`, torch 2.13.0+cu129, driver 570.148.08).
GPU-hours are physical: the GPU count times `scontrol RunTime`. `sacct` is disabled on this host.

| Job | Slurm id | GPUs | Engines | Limit | RunTime | GPU-h | State |
|---|---:|---:|---|---:|---:|---:|---|
| Overlay build 1 (git `f6eaf1b2`) | 1311 | 1 | - | 5 min | 00:01:26 | 0.0239 | COMPLETED 0:0 |
| a | 1314 | 1 | Qwen3.5-4B; Qwen3-1.7B-Base (prefix on/off); Qwen3-0.6B-Base | 55 | 00:36:20 | 0.6056 | COMPLETED 0:0 |
| b | 1320 | 1 | Qwen3.5-9B (prefix on/off, FP8 KV) | 42 | 00:27:20 | 0.4556 | COMPLETED 0:0 |
| c | 1321 | 2 | Qwen3.6-35B-A3B TP 2 | 28 | 00:17:40 | 0.5889 | COMPLETED 0:0 |
| d | 1322 | 2 | Qwen3-32B TP 2 | 40 | 00:34:30 | 1.1500 | COMPLETED 0:0 |
| e | 1323 | 1 | Qwen3-32B TP 1 (BF16 and FP8 KV); 35B-A3B TP 1 (refused) | 44 | 00:32:10 | 0.5361 | COMPLETED 0:0 |
| f | 1324 | 4 | Qwen3-32B TP 4 | 15 | 00:11:13 | 0.7478 | COMPLETED 0:0 |
| Overlay build 2 (git `3343668a`) | 1325 | 1 | - | 5 min | 00:01:02 | 0.0172 | COMPLETED 0:0 |
| g | 1329 | 4 | Qwen3-32B TP 4 (two cells' second repeat) | 15 | 00:08:38 | 0.5756 | COMPLETED 0:0 |
| h | 1330 | 1 | 35B-A3B TP 1, `max_num_seqs` 128 | 12 | 00:04:48 | 0.0800 | COMPLETED 0:0 |
| **Total** | | | | | | **4.7806** (17,210 GPU-seconds; the rounded rows sum to 4.7807) | |

The budget was 6 physical GPU-h. Jobs a-f and build 1 were submitted with Slurm limits totalling
5.70 GPU-h. g, h and build 2 were added after a-f had finished at 4.11 GPU-h; their limits (1.28
GPU-h) kept the worst case at 5.39. Three CPU-only jobs used no GPU:
- fetch 1310 (Qwen3-32B download, 00:05:24);
- selftests 1312 and 1326, which parse every argv with vLLM's own parsers in the image.

Jobs a-f ran at the same time on separate GPUs and disjoint CPU sets (16-32 CPUs each, from 208).
f waited for four free GPUs, and g and h ran together.

## Models

The six models below were served (the fla, RWKV and OpenCUA checkpoints on disk were not, being
non-standard or remote-code). All are standard architectures served without
`--trust-remote-code`. The receipts sit on the host model cache. The lane verified each job's
primary model, and the driver re-verified the others with `fetch_open_model.py verify`. Every
verification exited 0.

| Model id | Hugging Face revision | Receipt SHA-256 | Bytes on disk | Architecture |
|---|---|---|---:|---|
| qwen3-0.6b-base | `da87bfb6...` | `e7f36f05...` | 1,203,641,805 | dense transformer, 28 layers |
| qwen3-1.7b-base | `ea980cb0...` | `873ab07b...` | 3,452,692,285 | dense transformer, 28 layers |
| qwen3.5-4b | `851bf6e8...` | `75ebfc53...` | 9,342,907,469 | gated-DeltaNet hybrid, 8 attention + 24 linear layers |
| qwen3.5-9b | `c2022362...` | `0a9e052d...` | 19,329,393,661 | gated-DeltaNet hybrid, 8 + 24 |
| qwen3.6-35b-a3b | `995ad96e...` | `18c2a128...` | 71,926,865,825 | hybrid MoE, 256 experts top-8, 10 + 30 layers |
| qwen3-32b | `9216db57...` | `06e4a7e9...` | 65,540,298,478 | dense transformer, 64 layers |

Qwen3-32B (`Qwen/Qwen3-32B`, Apache-2.0, no remote code) was downloaded under D1 by the GPU-less
fetch lane:
- job 1310: 27 files, 5 min 24 s;
- receipt `fetch/qwen3-32b.receipt.json`, artifact root `8fcd9106...`;
- registry entry added in `models/registry.yaml`.

Full digests are in `analysis/summary.json` and each job's `ib/models.json`.

## Method

- **Driver.** `scripts/run_inference_baseline.py` reads `experiments/serving/inference-baseline-v1.yaml`.
  It runs inside the overlay, where the command is the lane's validated argv.
- **Engines.** `vllm serve` with:
  - BF16 weights, seed 42, `--gpu-memory-utilization 0.90`, `--max-model-len 32768`;
  - `--max-num-seqs 256`, `--max-num-batched-tokens 8192`, prefix caching on, KV dtype `auto`;
  - per-engine overrides: prefix caching off, `--kv-cache-dtype fp8`, TP 2 or 4;
  - Qwen3-32B TP 1 with BF16 KV at `--max-model-len 16384`, since 32k does not fit;
  - the Qwen3.5 and 3.6 models text-only, with `--limit-mm-per-prompt '{"image":0,"video":0}'`.
- **Serving cells.** vLLM's own `vllm bench serve` code (`vllm.benchmarks.serve.main`) runs
  in-process in a long-lived client against `/v1/completions`. The client uses:
  - closed loop at concurrency 1, 8, 32 and 128;
  - random token prompts, seed 42;
  - `--ignore-eos`, temperature 0;
  - percentiles 50, 90 and 99 of TTFT, TPOT, ITL and E2E latency.

  The shapes are chat (512 in, 256 out), 8k-in (8,192, 256), 32k-in (32,000, 256; concurrency up
  to 32) and long output (512, 4,096). Prompt counts are in the config, for example 256 for
  chat-128 and 1 for long-output-1. Two warm-up runs per engine are discarded.
- **Repeats.** Each cell ran twice. Repeat 1 of every cell ran before repeat 2. The engine's
  prefix cache was reset (`POST /reset_prefix_cache`) before every run, because the random
  dataset's prompts overlap as prefixes across cells. Every core-grid run then recorded a
  prefix-cache hit rate of 0. vLLM's ready-check request was disabled, because it would have
  pre-cached request 0.
- **Prefix workload.** vLLM's `prefix_repetition` dataset: 8 distinct 4,096-token prefixes, each
  with a fresh 256-token suffix and 128 output tokens, at concurrency 8 (64 prompts) and 32
  (128 prompts). It ran on an engine with prefix caching on and on one with it off.
- **Offline cells.** vLLM's own `vllm bench throughput` functions (`get_requests`,
  `_run_vllm_requests`) ran on one `LLM` per engine, with every prompt submitted at once. The
  shapes are chat 512/256 (512 prompts), 8k/256 (64) and decode 512/2048 (128). The prompt
  counts were halved for the TP 2 engines. The prefix cache was reset before every run. The
  tool's own default sampling (temperature 1.0) applies.
- **Sampling.**
  - NVML every 0.2 s for the whole job: memory used, power, the energy counter, utilization,
    SM and memory clocks, temperature and clock-event reasons (`ib/nvml.csv`).
  - The engine's Prometheus metrics every 0.5 s during each run: KV usage, running and waiting
    requests, preemptions, prefix-cache counters and token counters
    (`runs/metrics/*.csv`).
  - Engine start-up memory accounting, parsed from vLLM's log.
  - DCGM is not installed. The host's driver parameter `RmProfilingAdminOnly` is 1, so profiling
    counters (DRAM throughput) are admin-only and were not attempted.
- **Bandwidth estimate** (analytical). The bytes one decode step reads:
  - every text weight a token touches (the input embedding excluded; the head counted once);
  - for the MoE, routed experts scaled by `1-(1-8/256)^B` for `B` running sequences, which
    assumes uniform routing;
  - `B x (input + output/2) x` KV bytes per token;
  - for the hybrids, `B x` GDN state (BF16) read and written.

  This total is divided by TP and by the median ITL and compared with 3.35 TB/s. It ignores
  activations, all-reduce and kernel overheads. It is meaningful only where decode dominates:
  concurrency 1, and chat or long output at higher concurrency. For prefill-heavy cells the
  median ITL includes prefill chunks.
- **Analysis.** `scripts/analyze_inference_baseline.py` uses the standard library only. It ran on
  the host, over the raw run directories, and wrote `analysis/`:
  - `serve_runs.csv`: 258 runs;
  - `serve_cells.csv`: 128 cells;
  - `offline_runs.csv`: 36 runs;
  - `engines.csv`: 15 engines;
  - `tables.md`: every table below, and more.

## HBM: where the 80 GB goes (per GPU, vLLM start-up accounting)

| Engine | Weights GiB | Non-torch | Peak activation | CUDA graphs | KV cache GiB | KV capacity (tokens) | Ready s |
|---|---:|---:|---:|---:|---:|---:|---:|
| qwen3-0.6b-tp1 | 1.12 | 0.45 | 0.81 | 0.28 | 68.9 | 644,992 | 48 |
| qwen3-1.7b-tp1 | 3.21 | 0.45 | 1.15 | 0.31 | 66.5 | 622,288 | 74 |
| qwen3.5-4b-tp1 | 7.99 | 0.52 | 2.06 | 0.42 | 60.7 | 1,788,942 | 84 |
| qwen3.5-9b-tp1 | 16.8 | 0.53 | 2.84 | 0.44 | 51.1 | 1,505,903 | 94 |
| qwen3.5-9b-tp1, prefix caching off | 16.8 | 0.53 | 2.84 | 0.44 | 51.1 | 1,574,353 | 70 |
| qwen3.5-9b-tp1, FP8 KV | 16.8 | 0.53 | 2.85 | 0.44 | 51.1 | 2,733,541 | 74 |
| qwen3.6-35b-a3b-tp1 (`max_num_seqs` 256) | 64.7 | - | - | - | 3.65 | 156,079 | refused |
| qwen3.6-35b-a3b-tp1-seqs128 | 64.7 | 0.88 | 1.53 | 0.37 | 4.17 | 178,499 | 116 |
| qwen3.6-35b-a3b-tp2 | 32.4 | 1.33 | 1.50 | 0.66 | 36.0 | 3,082,778 | 192 |
| qwen3-32b-tp1 | 61.0 | 0.42 | 2.94 | 0.70 | 6.89 | 28,192 | 120 |
| qwen3-32b-tp1, FP8 KV | 61.0 | 0.42 | 2.94 | 0.70 | 6.89 | 56,400 | 96 |
| qwen3-32b-tp2 | 30.6 | 0.73 | 1.92 | 0.56 | 38.0 | 311,552 | 180 |
| qwen3-32b-tp4 | 15.5 | 0.71 | 1.46 | 0.49 | 53.6 | 878,400 | 182 |

All engines reserve 0.90 of 79.19 GiB (71.3 GiB). The NVML peak during runs was 71.6-75.1 GiB
in every run, idle or loaded. Notes on the table:
- The KV-capacity figures are vLLM's own. For the hybrids they include the per-sequence GDN state
  in vLLM's unified page accounting. With prefix caching on, Mamba "align" mode costs the 9B
  about 4% of its token capacity.
- Start-up took 36-192 s, including up to 45 s of `torch.compile`. The TP 2 and TP 4 engines
  took about 3 minutes while five jobs loaded weights at once.

## Single-stream decode (concurrency 1, chat shape, mean of 2 repeats)

| Engine | TTFT ms | TPOT ms | Output tok/s | Est. GB read per step | Est. TB/s per GPU | Est. % of 3.35 TB/s | W per GPU | J per output token |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| qwen3-0.6b-tp1 | 12.9 | 1.46 | 663 | 1.27 | 0.86 | 26% | 183 | 0.37 |
| qwen3-1.7b-tp1 | 13.4 | 2.19 | 448 | 3.52 | 1.60 | 48% | 257 | 0.73 |
| qwen3.5-4b-tp1 | 28.1 | 4.12 | 237 | 8.48 | 2.06 | 61% | 329 | 1.68 |
| qwen3.5-9b-tp1 | 29.2 | 6.54 | 151 | 15.9 | 2.44 | 73% | 393 | 2.95 |
| qwen3.6-35b-a3b-tp1-seqs128 | 84.5 | 4.45 | 210 | 5.97 | 1.34 | 40% | 285 | 1.63 |
| qwen3.6-35b-a3b-tp2 | 36.1 | 3.51 | 275 | 5.97 | 0.85 | 25% | 241 | 2.14 |
| qwen3-32b-tp1 | 59.4 | 23.2 | 42.9 | 64.1 | 2.77 | 83% | 469 | 11.2 |
| qwen3-32b-tp2 | 39.4 | 13.2 | 75.2 | 64.1 | 2.43 | 73% | 458 | 12.8 |
| qwen3-32b-tp4 | 30.8 | 8.12 | 122 | 64.1 | 1.98 | 59% | 384 | 13.4 |

TPOT barely moves with context at concurrency 1. Qwen3-32B TP 2 goes from 13.2 ms (chat) to
14.5 ms (32k-in), and Qwen3.5-9B from 6.54 to 6.77 ms. At batch 1, the KV read stays small next
to the weights.

Prefill at concurrency 1, taken as the 8k input over the median TTFT, is a lower bound because
TTFT includes queueing and tokenization:
- Qwen3-32B: 8.8k tok/s at TP 1, 15.4k at TP 2 and 26.1k at TP 4.
- Qwen3.5-9B: 34.7k tok/s.
- Qwen3-0.6B: 130k tok/s.

At 2 FLOPs per parameter, the 32B reaches about 42-57% of the H100's BF16 dense datasheet
peak per GPU (989 TFLOP/s). That is a rough estimate that excludes attention.

## Concurrency: long output (512 in, 4,096 out), mean of 2 repeats

| Engine | tok/s c1 | c8 | c32 | c128 | TPOT c1 ms | TPOT c128 ms | Peak KV c128 | Preemptions c128 | J/tok c1 | J/tok c128 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| qwen3-0.6b-tp1 | 635 | 3,505 | 6,873 | 9,255 | 1.57 | 13.8 | 91% | 0 | 0.43 | 0.073 |
| qwen3-1.7b-tp1 | 449 | 2,713 | 5,982 | 8,747 | 2.22 | 14.6 | 94% | 0 | 0.79 | 0.080 |
| qwen3.5-4b-tp1 | 246 | 1,726 | 4,997 | 9,958 | 4.07 | 12.7 | 41% | 0 | 1.67 | 0.069 |
| qwen3.5-9b-tp1 | 154 | 1,130 | 3,641 | 8,230 | 6.50 | 15.3 | 48% | 0 | 2.93 | 0.084 |
| qwen3.6-35b-a3b-tp2 | 283 | 1,309 | 3,337 | 7,764 | 3.53 | 16.3 | 29% | 0 | 2.06 | 0.145 |
| qwen3-32b-tp1 | 42.8 | 252 | - | - | 23.4 | - | (c8: 100%) | (c8: 2) | 11.3 | - |
| qwen3-32b-tp2 | 75.9 | 563 | 1,836 | 3,102 | 13.2 | 27.5 | 100% | 61 | 13.0 | 0.43 |
| qwen3-32b-tp4 | 124 | - | - | 7,384 (rerun 7,278) | 8.07 | 17.0 | 67% | 0 | 13.5 | 0.36 |

At long-output-128, the estimated bytes per step show where decode time goes:
- Qwen3-32B TP 2 reads about 55 GB of KV and 64 GB of weights per step, across both GPUs.
- Qwen3.5-9B reads 16 GB of weights, 10 GB of KV and 6.5 GB of GDN state.

## Concurrency: 8k-token prompts (8,192 in, 256 out), mean of 2 repeats

| Engine | TTFT c1 ms | TTFT c8 | TTFT c32 | TTFT c128 | Total tok/s c1 | Total tok/s c128 | TPOT c1 ms | TPOT c32 ms | Max peak KV |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| qwen3-0.6b-tp1 | 63 | 203 | 245 | 2,848 | 16,331 | 71,410 | 1.78 | 14.1 | 100% |
| qwen3-1.7b-tp1 | 84 | 338 | 405 | 4,560 | 11,670 | 57,475 | 2.51 | 17.4 | 100% |
| qwen3.5-4b-tp1 | 159 | 762 | 824 | 8,458 | 6,858 | 51,439 | 4.21 | 19.7 | 65% |
| qwen3.5-9b-tp1 | 236 | 1,198 | 1,342 | 13,680 | 4,437 | 33,990 | 6.54 | 29.6 | 77% |
| qwen3.6-35b-a3b-tp2 | 209 | 703 | 746 | 7,106 | 7,544 | 61,236 | 3.57 | 19.7 | 40% |
| qwen3-32b-tp1 | 931 | 12,139 | - | - | 1,198 | - | 24.0 | - | 90% |
| qwen3-32b-tp2 | 533 | 2,216 | 2,648 | 41,286 | 2,114 | 11,595 | 13.6 | 78.2 | 100% |
| qwen3-32b-tp4 | 314 | - | - | 19,505 | 3,446 | 22,574 | 8.38 | - | 100% |

With 8k prompts, TPOT at concurrency 32 is 4.5-8 times its concurrency-1 value, because
prefill chunks share each step with the decodes. The p99 ITL there reaches 40-530 ms, and 0.8-1.4
s with 32k prompts on the 32B. TTFT at concurrency 128 is mostly queueing.

## Qwen3-32B across TP 1, 2 and 4 (selected cells)

| Cell | TP 1 tok/s | TP 1 FP8 KV | TP 2 | TP 4 | TP 1 / 2 / 4 TPOT ms | TP 1 / 2 / 4 J per token |
|---|---:|---:|---:|---:|---|---|
| chat-1 | 42.9 | - | 75.2 | 122 | 23.2 / 13.2 / 8.1 | 11.2 / 12.8 / 13.4 |
| chat-128 | 1,142 (KV 100%, 80 preemptions) | 1,620 (KV 100%, 71) | 3,718 | 6,300 | 31.6 / 27.9 / 16.1 | 0.56 / 0.37 / 0.42 |
| 8k-1 | 36.3 | 36.3 | 64.0 | 104 | 24.0 / 13.6 / 8.4 | 14.3 / 16.3 / 17.3 |
| 8k-8 | 76.3 (KV 90%) | 116 | 247 | - | 29.3 / 23.6 / - | 7.3 / 4.9 / - |
| 32k-1 | does not fit (BF16 KV) | 22.6 | 39.3 | 66.8 | 25.2 (FP8) / 14.5 / 8.8 | 25.7 (FP8) / 30.1 / 32.3 |
| long-output-1 | 42.8 | - | 75.9 | 124 | 23.4 / 13.2 / 8.1 | 11.3 / 13.0 / 13.5 |

## FP8 KV cache against BF16 KV cache (same model, same cells)

| Cell | Model | BF16 tok/s | BF16 peak KV, preemptions | FP8 tok/s | FP8 peak KV, preemptions | FP8 / BF16 |
|---|---|---:|---|---:|---|---:|
| chat-128 | qwen3.5-9b | 6,789 | 21%, 0 | 6,757 | 16%, 0 | 0.995 |
| 8k-32 | qwen3.5-9b | 909 | 19%, 0 | 883 | 11%, 0 | 0.97 |
| 32k-32 | qwen3.5-9b | 254 | 65%, 0 | 239 | 34%, 0 | 0.94 |
| long-output-128 | qwen3.5-9b | 8,230 | 48%, 0 | 8,172 | 32%, 0 | 0.99 |
| chat-8 | qwen3-32b TP 1 | 313 | 22%, 0 | 311 | 11%, 0 | 0.99 |
| chat-32 | qwen3-32b TP 1 | 994 | 87%, 0 | 1,012 | 43%, 0 | 1.02 |
| chat-128 | qwen3-32b TP 1 | 1,142 | 100%, 80 | 1,620 | 100%, 71 | 1.42 |
| 8k-8 | qwen3-32b TP 1 | 76.3 | 90%, 0 | 116 | 90%, 0 | 1.53 |
| long-output-8 | qwen3-32b TP 1 | 252 | 100%, 2 | 321 | 65%, 0 | 1.28 |

FP8 KV used vLLM's default scales, with no calibration. Output quality was not measured, since
these are random prompts with `ignore_eos`.

## Prefix caching on and off (shared 4,096-token prefixes, mean of 2 repeats)

| Engine | Concurrency | Prefix cache | Hit rate | TTFT p50 ms | TTFT p99 ms | Total tok/s | TPOT p50 ms |
|---|---:|---|---:|---:|---:|---:|---:|
| qwen3-1.7b | 8 | on | 82% | 31.9 | 191 | 75,663 | 3.27 |
| qwen3-1.7b | 8 | off | - | 164 | 241 | 52,428 | 4.08 |
| qwen3-1.7b | 32 | on | 88% | 46.7 | 405 | 163,641 | 5.66 |
| qwen3-1.7b | 32 | off | - | 274 | 936 | 78,162 | 12.2 |
| qwen3.5-9b | 8 | on | 64% | 245 | 774 | 28,853 | 7.17 |
| qwen3.5-9b | 8 | off | - | 608 | 853 | 20,228 | 9.17 |
| qwen3.5-9b | 32 | on | 74% | 272 | 1,975 | 71,637 | 10.9 |
| qwen3.5-9b | 32 | off | - | 995 | 3,325 | 31,841 | 27.4 |

The hit rates fit a simple reading: a prefix is reusable only up to the last whole cache block.
- The 1.7B uses 16-token blocks, and 4,096 tokens divide exactly.
- The 9B's hybrid "align" mode logs 528-token block groups, which would leave the last 400 or
  so prefix tokens uncached.

That reading is a hypothesis, not checked here.

## Offline throughput (all prompts at once, mean of 2 repeats)

| Engine | Chat 512/256 out tok/s | 8k/256 total tok/s | Decode 512/2048 out tok/s | J per output token (decode) |
|---|---:|---:|---:|---:|
| qwen3-0.6b-tp1 | 25,628 | 72,541 | 13,752 | 0.047 |
| qwen3-1.7b-tp1 | 20,609 | 57,871 | 12,590 | 0.055 |
| qwen3.5-4b-tp1 | 10,648 | 49,167 | 10,735 | 0.061 |
| qwen3.5-9b-tp1 | 8,023 | 32,369 | 8,657 | 0.079 |
| qwen3.6-35b-a3b-tp2 (half prompts) | 9,231 | 44,845 | 4,796 | 0.217 |
| qwen3-32b-tp2 (half prompts) | 4,519 | 11,801 | 3,215 | 0.401 |

Repeat ranges were at most 1.7%. Offline chat throughput exceeds the online concurrency-128
figure: 8,023 against 6,789 tok/s for the 9B. Offline runs keep up to 256 sequences in flight,
online runs 128, and offline runs have no HTTP or streaming layer.

## Power, clocks and run-to-run spread

- Mean power per GPU: 180-470 W at concurrency 1, and 640-690 W in the heaviest cells.
- NVML's clock-event reasons show the software power cap (`0x4`) in 60-93% of samples in some of
  the heaviest cells:
  - 1.7B long-output-128: 93% at 685 W;
  - 9B 32k-32: 78%, mean SM clock 1,614 MHz;
  - 32B TP 2 32k-32: 76%, mean 1,593 MHz.

  The memory clock stayed at 2,619 MHz throughout.
- Spread between the two repeats, as (max-min)/mean over 128 serving cells:

  | Metric | Median | p90 | Max |
  |---|---:|---:|---:|
  | Output tok/s | 1% | 4% | 7% |
  | Median TPOT | 1% | 5% | 8% |
  | Median TTFT | 2% | 14% | 43% |

  Throughput spread above 4% occurs only in overhead-bound cells: the 0.6B and 1.7B at
  concurrency 1-32, and the MoE TP 2 at concurrency 1 (up to 7.4%). TTFT spread is largest where
  a cell has few prompts, as at long-output-1 with its single prompt, or a queue. The two cells that job f ran once were rerun on a new TP 4 engine in job g:
  - 32k-32: 143 tok/s against 142;
  - long-output-128: 7,384 against 7,278 (1.4% apart).

## What the data says (exploratory; for the question sweep, not claims)

1. **Weights fill HBM bandwidth only above roughly 9B dense-equivalent at batch 1.** For the 9B
   and 32B, decode at concurrency 1 runs near the bandwidth roofline: an estimated 73-83% at
   TP 1-2. Below that size, and for the 3B-active MoE, a decode step is too short to fill
   bandwidth, at an estimated 25-61%. Fixed per-step costs set the floor there: kernel
   launches, sampling, the scheduler and all-reduce. The 0.6B decodes in 1.46 ms while its
   weights would stream in under 0.4 ms. These estimates come from bytes and latency, not
   counters, and profiling counters need admin rights on this host.
2. **The usable memory question is KV per token times live sequences, against what the weights
   leave.** Dense 32B at TP 1 holds about 28k tokens, so chat-128 runs KV-bound, preempts about
   80 times per run and waits about 20 s for a first token. FP8 KV, TP 2 and TP 4 each relieve
   this, in that order of cost. The hybrids carry 8-13x less KV per token than Qwen3-32B but a
   fixed 25-31 MiB state per sequence. That state reaches 20% of the bytes moved per step at
   long-output-128 (9B), and it capped the one-GPU MoE at 181 sequences.
3. **At high concurrency these GPUs often run against the 700 W cap.** Clocks drop, and energy
   per output token still falls 6-37x from concurrency 1 to 128 on long output, more for the
   larger models. Throughput per watt, not per GPU, may be
   the better efficiency axis for the sweep.
4. **TP for a 32B model trades energy for latency at low load.** TP 4 gives 2.9x lower TPOT
   than TP 1 at 1.2x the energy per token. At chat-128 it gives 5.5x the throughput, because TP
   1 is KV-starved.
5. **Of the engine settings compared at fixed concurrency, prefix sharing moved throughput
   most,** about 2x. FP8 KV reached 1.5x, but only where KV was full. The prefix gain may be
   smaller for the hybrids, which reached lower hit rates on the same workload.
6. **Measurement noise on this node is about 1-5%** for throughput and TPOT across repeats, and
   larger for TTFT. A contrast smaller than that needs more repeats than two.

## Caveats

- **Exploratory only.** There are two repeats per cell, and no confidence intervals were
  computed. The two repeats ran on the same engine instance (except the TP 4 rerun), so
  instance-to-instance variance is mostly not measured.
- **Concurrent jobs.** Jobs a-f ran at the same time on one node. Each had disjoint GPUs and CPU
  sets, but host memory bandwidth, PCIe and disk were shared, and contention was not measured.
  Start-up times in particular were inflated by concurrent weight loading.
- **Synthetic prompts.** The random dataset's prompts are runs of consecutive token ids. MoE
  routing, and so the MoE's bandwidth estimate, may differ on natural text, and the uniform-
  routing estimate is likely high for the MoE at large batch. Output is forced with
  `ignore_eos`, so lengths are fixed and no output quality is measured.
- **Sampling differs.** Serving used greedy decoding (temperature 0). Offline used the tool's
  default (temperature 1.0).
- **Analytical bandwidth.** The bandwidth numbers are estimates under the stated byte model.
  They exclude activations, all-reduce and attention compute. They are not meaningful for
  prefill-heavy cells; see the TP 4 32k-32 row in `analysis/tables.md`.
- **NVML caveats.** `utilization.memory` is the share of time memory was busy, not bandwidth.
  NVML power is per GPU, and node power was not measured.
- **One build.** Everything is one vLLM build (0.31.0, CUDA 12.9 image on the R570 driver) with
  its default attention backends: FlashAttention 3, with a FlashInfer-JIT GDN prefill for the
  hybrids. Other versions or flags can move these numbers.
- **Config changes.** The one-GPU MoE result (job h) uses `max_num_seqs` 128 rather than the
  grid's 256. It is a separate engine configuration, not a rerun of job e.

## Operational notes and deviations

1. Job e's third engine, the 35B-A3B at TP 1 with `max_num_seqs` 256, was refused at start-up.
   vLLM reported `max_num_seqs (256) exceeds available Mamba cache blocks (181)`. Job h repeated
   it with 128 (config commit `3343668a`; overlay `sha256:9e411974...`, build job 1325).
2. Job f's 15-minute limit cut two second repeats, 32k-32 and long-output-128. The driver
   skipped them before the deadline and recorded both. Job g ran both cells twice on a fresh TP
   4 engine.
3. In job d, the offline engine finished all six runs inside the limit. No serving run in any job
   failed or was partial (258 of 258 ok), and every run produced exactly the requested output
   tokens.
4. Two overlay images were built, from commits `f6eaf1b2` (jobs a-f) and `3343668a` (g and h).
   Both builds used builder `aa43283e...` and extractor `9b4d21a8...`, and both reported
   provenance PASS. CPU-only selftests (1312, 1326) passed for every job's argv. The source
   archives were validated on CPU before each build (`capsule/`).
5. The lane-recorded argv, manifest, image digest, git SHA, model receipt and verification are
   in each `jobs/<job>-<id>/`. `host-run-dir.sha256` lists every file in the host run directory,
   excluding the JIT caches, which were not copied. Every committed job file matches its entry
   (1,072 files, 0 mismatches). The tables in `analysis/` were computed on the host from those
   run directories.

## Files

| Path | Contents |
|---|---|
| `manifests/` | the eight docker-research manifests; each submitter dry-run, test-only and submit output |
| `jobs/<job>-<slurm id>/` | lane receipts (`command.json`, `manifest.json`, `job.env`, `model-receipt.json`, `model-verification.txt`, `provenance-verification.txt`, `termination.env`, `scontrol`, Slurm output) and the driver's `ib/` output (see the next row) |
| `jobs/*/ib/` | `plan.json`, `environment.json`, `models.json`, `summary.json`, `progress.jsonl`, `nvml.csv`, `client.log`; per engine `engine.log`, `engine.json`, `runs/*.json` (vLLM bench result), `runs/*.meta.json` (timings, metrics summary, prefix reset), `runs/metrics/*.csv`, `offline/*` |
| `analysis/` | `serve_runs.csv`, `serve_cells.csv`, `offline_runs.csv`, `engines.csv`, `summary.json`, `tables.md` (all tables) |
| `overlay/`, `overlay-2/` | build receipts, image inspection, provenance and selftest inputs of both overlay images |
| `selftest/`, `selftest-2/` | CPU-only parse checks of every argv in the image |
| `capsule/` | source-archive receipts and CPU pre-validation for both commits |
| `fetch/` | the Qwen3-32B fetch lane receipt, summary and log |
| `ops/` | `jobs.log`, `preflight.log` (queue and GPU state before each submission), `render_manifests.py`, `receipts.json`, `collect_job.sh`, `selftest-cpu.sbatch` |

Reproduce the tables:
`python3 scripts/analyze_inference_baseline.py program/evidence/2026-10-14/inference-baseline/jobs --out <dir>`.
The script is standard-library only and reads the committed job directories.
