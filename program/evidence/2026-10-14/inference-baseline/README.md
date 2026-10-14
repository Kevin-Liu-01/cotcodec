# inference-baseline-v1: where time and HBM go when vLLM serves on H100 (2026-10-14)

> **EXPLORATORY. Not a registered experiment.** There is no preregistration, no hypothesis and
> no decision rule here, and nothing below is a confirmatory claim. These are measurements
> taken to ground the D103 area-2 question sweep (hardware memory and GPU acceleration for
> inference and RL). Kevin asked to "just straight up run inference". Every number comes from
> one node, one vLLM build and one day, with two repeats per cell.
>
> **Corrected the same day** after an independent check. The first version counted the
> hybrids' recurrent state as bf16; vLLM keeps it in float32. The tables were recomputed on the
> host from the committed raw records, with no new GPU job. Every change is listed under
> "Corrections after the independent check" near the end.

## Main takeaways (corrected)

- **Batch-1 decode of the 9B and 32B models is weight streaming.** The bytes a step reads, over
  the measured inter-token latency, come to 73-83% of the H100's 3.35 TB/s at TP 1-2. The
  0.6B-4B models and the 3B-active MoE reach only 26-62%: per-step overhead, not bandwidth,
  sets their speed. (An analytical estimate; no hardware counter was read.)
- **The dense models run out of KV cache.** Qwen3-32B on one GPU holds 28,192 tokens of KV. At
  chat-128 it preempts about 80 times per run and the median first token takes 20 s. FP8 KV
  doubles the capacity and gives 1.3-1.5x where KV binds. The cheapest lever was not tried:
  `gpu_memory_utilization` 0.90 sets that KV, and vLLM's own log says 13.44 GiB (about 55,000
  tokens) would fit on the same GPU instead of 6.89 GiB.
- **The hybrids keep their recurrent state in float32, and at short lengths it is most of their
  per-sequence memory.** vLLM 0.31.0 allocates the gated-DeltaNet (GDN) state in the
  checkpoint's `mamba_ssm_dtype`, which is float32 (source lines and engine records in
  `gdn-state-dtype/`). That is 49 MiB per sequence for Qwen3.5-4B and 9B and 61 MiB for
  Qwen3.6-35B-A3B, about twice the bf16 figure first reported. Every running sequence holds
  three state blocks beside its attention blocks. The state is 60% of the blocks a 9B chat
  sequence holds (75% on the MoE), 25% at long output and 5% with 32k prompts.
- **That state, not KV, capped the one-GPU MoE.** After 64.7 GiB of weights, 207 blocks were
  left, and a chat sequence needs four. At chat-128 at most 51 sequences ran, with 77-79
  waiting and a median TTFT of 5.7 s. vLLM's start-up check (181 slots, one block per sequence)
  does not show this cap. The 4B and 9B on one GPU and the MoE on two never came near their
  block pools in this grid (peak 77%).
- **The state also costs decode bandwidth at high concurrency.** At long-output-128 it is a
  third of the bytes a 9B decode step moves (12.7 of 38.8 GB). The estimated bandwidth use there
  is 76% for the 9B and 74% for the 4B, not the 64% and 60% first reported. The batch-1
  estimates move by less than half a point.
- **Prefix sharing roughly doubles throughput at concurrency 32:** 2.1x on Qwen3-1.7B and 2.25x
  on Qwen3.5-9B. The hybrid hits less often (64-74% against 82-88%), and its 528-token blocks
  explain only part of that gap.
- **Heavy cells run against the 700 W power cap**, and energy per output token still falls
  6-37x from concurrency 1 to 128.
- **Repeats agree to about 1-5%, but a fresh engine instance changed tail latency several-fold.**
  On two Qwen3-32B TP 4 engines, the 32k-32 cell gave the same throughput and TPOT, but a median
  ITL of 129 ms against 29-36 ms and a p99 ITL of 1.41 s against 0.48-0.49 s.

## Bottom line (exploratory reading, corrected)

- **Single-stream decode is weight streaming for the 9B and 32B models.** At concurrency 1,
  the bytes a decode step must read, divided by the measured median inter-token latency, come
  to about 73-83% of the H100's 3.35 TB/s for Qwen3.5-9B and Qwen3-32B at TP 1-2. They fall to
  about 60% at TP 4, and to 26-62% for the 0.6B-4B models and the 3B-active MoE. Those smaller
  engines cannot fill HBM bandwidth at batch 1, so per-step overhead dominates. (The bandwidth
  figure is an analytical estimate. No hardware counter was read.)
- **HBM is reserved, not used.** `nvidia-smi` reports 72-76 GiB in every run, at any load,
  because vLLM claims 90% of the device at start-up. What varies is what the reservation holds:
  - Qwen3-32B at TP 1: 61.0 GiB of weights leave 6.9 GiB of KV cache, about 28,000 tokens.
  - The same model at TP 4: 878,400 tokens.
  - Qwen3.5-9B: vLLM reports 1.5 million tokens on one GPU. Its gated-DeltaNet hybrid keeps KV
    on only 8 of 32 layers (32 KiB per token, against 256 KiB for Qwen3-32B), plus 49 MiB of
    float32 recurrent state per sequence. How many sequences fit therefore depends on their
    length: 634 chat sequences, 264 long-output sequences or 48 with 32k prompts.
  - The KV gauge (`vllm:kv_cache_usage_perc`) is the informative memory signal. Device memory
    used is not.
- **Cache capacity bound the dense models and the one-GPU MoE.** The dense engines reached
  98-100% KV use, some with preemptions:
  - Qwen3-32B TP 1 at chat-128: 1,142 tok/s and a median TTFT of 20 s.
  - Qwen3-32B TP 2 at long-output-128.
  - Qwen3-0.6B and 1.7B with 8k and 32k prompts.

  The one-GPU MoE (job h) had 4.17 GiB for KV and state. At chat-128 it ran at most 51
  sequences, because each held one attention block and three GDN-state blocks. 77-79 requests
  waited, the median TTFT was 5.7 s, and the gauge read 99% (204 of 206 usable blocks). There
  were no preemptions, because vLLM admitted no more than fit. The hybrids in their main
  configurations (4B and 9B at TP 1, 35B-A3B at TP 2) never filled their block pools in this
  grid. The highest reading was 77%.
- **FP8 KV doubles capacity, and it helps only where capacity binds.** On Qwen3-32B TP 1:
  - capacity goes from 28,192 to 56,400 tokens;
  - 8k-prompt c8 runs 1.53x faster and chat-128 1.42x;
  - long-output c8 runs 1.28x faster, with no preemptions;
  - a 32k prompt fits on one GPU.

  On Qwen3.5-9B, FP8 KV changes throughput by -6% to -0.5%, because its KV never bound. A
  cheaper lever was not tried: raising `gpu_memory_utilization` above 0.90 (see the HBM
  section).
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
- **Run-to-run spread is small on one engine instance.** The two repeats differ by a median of
  1% in output throughput and 1% in median TPOT (p90 4-5%, max 8%), and by 2% in median TTFT
  (p90 14%, max 43%). Throughput spreads above 4% (14 cells, up to 7.4%) sit mostly in
  overhead-bound cells: the 0.6B and 1.7B at low concurrency, and the MoE TP 2 at a
  concurrency of 1. The one-GPU MoE at chat-32 (4.2%) is the exception. Across two engine
  instances, the one comparison in the data, throughput agreed but tail latency in a
  prefill-heavy cell did not (see the spread section).
- **Qwen3.6-35B-A3B fits on one H100 only with few sequences.** Its 64.7 GiB of weights leave
  4.17 GiB. With `max_num_seqs` 256 vLLM refused to start (181 state blocks, one counted per
  sequence). At 128 it started, but at most 51 chat sequences ran at a time, for 2,482 tok/s
  at chat-128.

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
GPU-h) kept the worst case at 5.39. Six CPU-only jobs used no GPU:
- fetch 1310 (Qwen3-32B download, 5 min 23 s by its receipt: 19:44:33-19:49:56);
- selftests 1312 and 1326, which parse every argv with vLLM's own parsers in the image;
- for the correction, source checks 1346, 1348 and 1350, which print the vLLM source that sets
  the GDN state dtype in both overlay images (1348 failed on an ambiguous `grep` partway through
  the first image; 1350 is the complete rerun). See `gdn-state-dtype/`.

The Slurm records of the first three are thin: `fetch/scontrol-1310.txt` and
`selftest/scontrol-1312.txt` are empty (0 bytes), and `selftest-2/` has no `scontrol-1326.txt`.
Their run times and the absence of GRES rest on other records: the fetch receipt
(`gres_requested` none, `container_dev_nvidia` [], start and finish times) and each sbatch's GPU
guard. The three source checks have full `scontrol` records (TRES cpu=2, mem=4G, no GRES).

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
- job 1310: 27 files, 5 min 23 s;
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
  - for the hybrids, `B x` GDN state read and written, in the dtypes vLLM allocated: the
    recurrent (SSM) state in float32 and the convolution state in bf16. That is 49.1 MiB per
    sequence for the 4B and 9B and 61.4 MiB for the MoE (corrected; the first version used bf16
    for both, 25.1 and 31.4 MiB).

  This total is divided by TP and by the median ITL and compared with 3.35 TB/s. It ignores
  activations, all-reduce and kernel overheads. It is meaningful only where decode dominates:
  concurrency 1, and chat or long output at higher concurrency. For prefill-heavy cells the
  median ITL includes prefill chunks.
- **Analysis.** `scripts/analyze_inference_baseline.py` uses the standard library only. It ran on
  the host and wrote `analysis/`. The corrected version reran there on the committed job
  records (`corrections/analysis-rerun.txt`; the previous version reproduces the first
  `analysis/` byte for byte from the same records). It writes:
  - `serve_runs.csv`: 258 runs;
  - `serve_cells.csv`: 130 cells, 128 with two repeats and the 2 TP 4 cells job f ran once;
  - `offline_runs.csv`: 36 runs;
  - `engines.csv`: 15 engines;
  - `tables.md`: every table below, and more, including a GDN-state table and peak running
    and waiting requests per cell.

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

All engines reserve 0.90 of 79.19 GiB (71.3 GiB). The NVML peak was 71.6-75.1 GiB in every
serving run and 72.4-75.6 GiB in every offline run, idle or loaded. Notes on the table:
- **`gpu_memory_utilization` 0.90 sets Qwen3-32B TP 1's KV, and raising it is the cheapest
  lever.** vLLM's own start-up line for that engine reads: "Free memory on device (78.68/79.19
  GiB) on startup. Desired GPU memory utilization is (0.9, 71.27 GiB)." It continues:
  "Replace gpu_memory_utilization config with `--kv-cache-memory=6483179828` (6.04 GiB) to fit
  into requested memory, or `--kv-cache-memory=14435698176` (13.44 GiB) to fully utilize gpu
  memory. Current kv cache memory in use is 6.89 GiB." At 256 KiB per token, 13.44 GiB is
  55,067 tokens, close to FP8 KV's 56,400. It was not tried, and it would leave almost no
  headroom outside vLLM's own memory profile. The one-GPU MoE's log gives the same option:
  11.07 GiB against the 4.17 GiB in use, which by the block arithmetic below is 549 blocks, or
  137 chat sequences instead of 51 (`corrections/corrections.json`, `qwen3_32b_tp1_full_kv` and
  `moe_tp1_full_kv`).
- The KV-capacity figures are vLLM's own. For the hybrids they do not show that each running
  sequence also holds three GDN-state blocks (next section), so they overstate how many tokens
  of short sequences fit. With prefix caching on ("align" mode), vLLM reports about 4% fewer
  tokens for the 9B than with it off, from the same 3,171 blocks.
- Start-up took 36-192 s, including up to 45 s of `torch.compile`. The TP 2 engines took 180
  and 192 s and the TP 4 engines 182 and 164 s, against 36-120 s at TP 1. Concurrent loading
  does not explain the TP 4 times: at most three engine start-ups overlapped (19:52-19:55), and
  each TP 4 start-up overlapped only one other. The cause was not measured. (The first version
  said five jobs loaded weights at once.)

### Hybrid block pool: what the float32 GDN state costs

vLLM gives the hybrids one shared block pool. It groups the layers into one attention group and
three GDN groups of equal size (8 layers each for the 4B and 9B, 10 for the MoE). It sizes a
block so that one sequence's GDN state for one layer fits in one layer's page. With the float32
state, that page is 2,146,304 bytes per layer. A 528-token attention page (4,096 bytes per token
per layer on the 4B and 9B) is 2,162,688 bytes, 0.76% larger, which is the padding vLLM logs. A
bf16 state would need a 272-token block. A running sequence then holds one block in each GDN
group plus enough attention blocks for its tokens.

| Engine | Blocks | Block (tokens) | GDN state per sequence | Blocks per sequence: chat / long output / 32k | Most running sequences: chat / long output / 32k | GDN share of a chat sequence's blocks |
|---|---:|---:|---:|---|---|---:|
| qwen3.5-4b-tp1 | 3,767 | 528 | 49.1 MiB | 5 / 12 / 65 | 753 / 313 / 57 | 60% |
| qwen3.5-9b-tp1 | 3,171 | 528 | 49.1 MiB | 5 / 12 / 65 | 634 / 264 / 48 | 60% |
| qwen3.5-9b-tp1, FP8 KV | 3,170 | 1,056 | 49.1 MiB | 4 / 8 / 34 | 792 / 396 / 93 | 75% |
| qwen3.6-35b-a3b-tp2 | 3,575 | 1,056 | 61.4 MiB (30.7 per GPU) | 4 / 8 / 34 | 893 / 446 / 105 | 75% |
| qwen3.6-35b-a3b-tp1-seqs128 | 207 | 1,056 | 61.4 MiB | 4 / 8 / 34 | 51 / 25 / 6 | 75% |

- The GDN share of a sequence's blocks falls with length: 60% at chat (768 tokens), 25% at
  long output (4,608) and 5% at 32k (32,256) on the 9B.
- This accounting reproduces vLLM's peak KV gauge to within 1 point in every hybrid core-grid
  cell. For example, the 9B at 32k-32 gives 32 x 65 / 3,170 = 65.6% (measured 64.9%), and the
  one-GPU MoE at chat-128 gives 51 x 4 / 206 = 99.0% (measured 99.0%). The prefix cells with
  caching on share prefix blocks and do not follow it. Per-cell checks are in
  `corrections/corrections.json` (`hybrid_peak_kv_vs_block_model`).
- **The one-GPU MoE was state-capacity-bound.** In both chat-128 repeats, 51 sequences ran at
  peak (mean 44.3 and 44.9), 77 and 79 waited, and the median TTFT was 5.4 and 6.0 s. vLLM's
  start-up check compares `max_num_seqs` with the block count (181 for job e's engine, which
  had 3.65 GiB), as if a sequence needed one block. It needs four. By vLLM's block-size rule,
  a bf16 state would have fit about 80 chat sequences. That was not run, and the checkpoint asks
  for float32.

## Single-stream decode (concurrency 1, chat shape, mean of 2 repeats)

| Engine | TTFT ms | TPOT ms | Output tok/s | Est. GB read per step | Est. TB/s per GPU | Est. % of 3.35 TB/s | W per GPU | J per output token |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| qwen3-0.6b-tp1 | 12.9 | 1.46 | 663 | 1.27 | 0.86 | 26% | 183 | 0.37 |
| qwen3-1.7b-tp1 | 13.4 | 2.19 | 448 | 3.52 | 1.60 | 48% | 257 | 0.73 |
| qwen3.5-4b-tp1 | 28.1 | 4.12 | 237 | 8.54 | 2.07 | 62% | 329 | 1.68 |
| qwen3.5-9b-tp1 | 29.2 | 6.54 | 151 | 16.0 | 2.44 | 73% | 393 | 2.95 |
| qwen3.6-35b-a3b-tp1-seqs128 | 84.5 | 4.45 | 210 | 6.04 | 1.35 | 40% | 285 | 1.63 |
| qwen3.6-35b-a3b-tp2 | 36.1 | 3.51 | 275 | 6.04 | 0.86 | 26% | 241 | 2.14 |
| qwen3-32b-tp1 | 59.4 | 23.2 | 42.9 | 64.1 | 2.77 | 83% | 469 | 11.2 |
| qwen3-32b-tp2 | 39.4 | 13.2 | 75.2 | 64.1 | 2.43 | 73% | 458 | 12.8 |
| qwen3-32b-tp4 | 30.8 | 8.12 | 122 | 64.1 | 1.98 | 59% | 384 | 13.4 |

The four hybrid rows changed slightly with the float32 state: by 0.05-0.07 GB per step and at
most 0.4 points of bandwidth (9B 72.7% to 72.9%, 4B 61.4% to 61.8%, MoE TP 2 25.4% to 25.8%).

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
- Qwen3.5-9B reads 15.9 GB of weights, 10.3 GB of KV and 12.7 GB of GDN state: 38.8 GB, of
  which the state is a third (corrected from 6.5 GB and 20%). The estimate is then 76% of 3.35
  TB/s (first given as 64%). The 4B's is 74% (first 60%), with the state 40% of its bytes. The
  MoE at TP 2 reaches 82% (first 75%).

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
prefill chunks share each step with the decodes. The p99 ITL there reaches 40-530 ms. With 32k
prompts on the 32B it is 0.81-0.82 s at TP 2. At TP 4 (32k-32) it depends on the engine
instance: 1.41 s on job f's engine against 0.48 and 0.49 s on job g's. TTFT at concurrency 128
is mostly queueing.

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
these are random prompts with `ignore_eos`. FP8 KV does not shrink the hybrids' GDN state, which
keeps its float32 recurrent part and bf16 convolution part. On the 9B it only doubles the
attention block to 1,056 tokens.

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

The hit rates, checked against the block sizes (`corrections/corrections.json`,
`prefix_hit_rates`):
- **The 1.7B reaches the maximum possible.** Every request after the first of each of the 8
  prefixes reuses all 4,096 prefix tokens of its 4,352-token prompt. That predicts 82.4% at
  concurrency 8 (64 prompts) and 88.2% at 32 (128 prompts), and both repeats measured exactly
  that.
- **Block alignment explains only part of the 9B's shortfall.** If only whole 528-token blocks
  are reusable (7 x 528 = 3,696 of the 4,096 prefix tokens), the 9B should reach 74.3% and
  79.6%. It measured 63.7% and 74.3%, identically in both repeats. Alignment accounts for 8.1
  of the 18.7 points lost at concurrency 8 and 8.6 of the 13.9 at 32. The rest is unexplained.
  Two candidates were not tested: requests that share a prefix and start before it is cached,
  and vLLM's rules for which GDN state checkpoints "align" mode keeps. (The first version
  offered alignment alone as the hypothesis.)

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

- Mean power per GPU at concurrency 1 is 183-469 W with chat prompts. With long prompts it
  reaches 559 W (Qwen3-32B TP 2) and 563 W (TP 1 with FP8 KV) at 32k-1, as cell means; one TP 2
  run reached 564 W. The heaviest cells run at 640-690 W. (The first version gave 180-470 W for
  all concurrency-1 cells.)
- NVML's clock-event reasons show the software power cap (`0x4`) in 60-93% of samples in some of
  the heaviest cells:
  - 1.7B long-output-128: 93% at 685 W;
  - 9B 32k-32: 78%, mean SM clock 1,614 MHz;
  - 32B TP 2 32k-32: 76%, mean 1,593 MHz.

  The memory clock stayed at 2,619 MHz throughout.
- Spread between the two repeats on one engine instance, as (max-min)/mean over the 128 cells
  with two repeats:

  | Metric | Median | p90 | Max |
  |---|---:|---:|---:|
  | Output tok/s | 1% | 4% | 7% |
  | Median TPOT | 1% | 5% | 8% |
  | Median TTFT | 2% | 14% | 43% |

  Throughput spread above 4% occurs in 14 cells. Thirteen are overhead-bound: the 0.6B and 1.7B
  at concurrency 1-32, and the MoE TP 2 at concurrency 1 (up to 7.4%). The fourteenth is the
  one-GPU MoE at chat-32 (4.2%, an estimated 94% of bandwidth). The first version said all such
  cells were overhead-bound. TTFT spread is largest where a cell has few prompts, as at
  long-output-1 with its single prompt, or a queue.
- **Spread across engine instances.** The only comparison in the data is the two cells that job
  f ran once and job g reran twice on a fresh TP 4 engine:

  | Cell | Engine | Output tok/s | Median TPOT ms | Median TTFT s | Median ITL ms | p99 ITL ms |
  |---|---|---:|---:|---:|---:|---:|
  | 32k-32 | f | 143.2 | 115.2 | 25.2 | 129.5 | 1,409 |
  | 32k-32 | g, repeats 1 and 2 | 142.3, 142.0 | 115.9, 116.0 | 25.3, 25.4 | 29.4, 35.9 | 484, 493 |
  | long-output-128 | f | 7,384 | 16.99 | 1.38 | 16.81 | 22.2 |
  | long-output-128 | g, repeats 1 and 2 | 7,281, 7,275 | 17.24, 17.26 | 1.33, 1.32 | 17.06, 17.05 | 22.4, 22.5 |

  Throughput and TPOT agree across instances to 0.7-1.5%. The ITL distribution of the
  prefill-heavy 32k-32 cell does not: the median differs 3.6-4.4x and the p99 2.9x. The cause
  was not investigated. Instance-to-instance variance is otherwise unmeasured.

## What the data says (exploratory; for the question sweep, not claims)

1. **Weights fill HBM bandwidth only above roughly 9B dense-equivalent at batch 1.** For the 9B
   and 32B, decode at concurrency 1 runs near the bandwidth roofline: an estimated 73-83% at
   TP 1-2. Below that size, and for the 3B-active MoE, a decode step is too short to fill
   bandwidth, at an estimated 26-62%. Fixed per-step costs set the floor there: kernel
   launches, sampling, the scheduler and all-reduce. The 0.6B decodes in 1.46 ms while its
   weights would stream in under 0.4 ms. These estimates come from bytes and latency, not
   counters, and profiling counters need admin rights on this host.
2. **The usable memory question is per-sequence cache times live sequences, against what the
   weights leave.**
   - Dense 32B at TP 1 holds about 28k tokens, so chat-128 runs KV-bound, preempts about 80
     times per run and waits about 20 s for a first token. FP8 KV, TP 2 and TP 4 each relieve
     this, in that order of cost. A cheaper lever was not tried: `gpu_memory_utilization` 0.90
     sets that KV, and vLLM's log says about 55k tokens (13.44 GiB) would fit on the same GPU.
   - The hybrids carry 8-13x less KV per token than Qwen3-32B but a fixed float32 GDN state of
     49-61 MiB per sequence. That state is 60-75% of a chat sequence's blocks. It is a third of
     the bytes a 9B decode step moves at long-output-128. It, not KV, capped the one-GPU MoE at
     51 running chat sequences: 207 blocks were left after its weights, and each sequence took
     four.
3. **At high concurrency these GPUs often run against the 700 W cap.** Clocks drop, and energy
   per output token still falls 6-37x from concurrency 1 to 128 on long output, more for the
   larger models. Throughput per watt, not per GPU, may be
   the better efficiency axis for the sweep.
4. **TP for a 32B model trades energy for latency at low load.** TP 4 gives 2.9x lower TPOT
   than TP 1 at 1.2x the energy per token. At chat-128 it gives 5.5x the throughput, because TP
   1 is KV-starved at `gpu_memory_utilization` 0.90.
5. **Of the engine settings compared at fixed concurrency, prefix sharing moved throughput
   most,** about 2x. FP8 KV reached 1.5x, but only where KV was full. The prefix gain may be
   smaller for the hybrids, which reached lower hit rates on the same workload.
6. **Measurement noise on this node is about 1-5%** for throughput and TPOT across repeats on
   one engine, and larger for TTFT. A contrast smaller than that needs more repeats than two.
   Across engine instances, throughput reproduced in the two cells that allow a comparison, but
   tail ITL in a prefill-heavy cell differed about 3x.

## Caveats

- **Exploratory only.** There are two repeats per cell, and no confidence intervals were
  computed. The two repeats ran on the same engine instance (except the TP 4 rerun), so
  instance-to-instance variance is mostly not measured. The one comparison shows it can be
  large for tail latency.
- **Concurrent jobs.** Jobs a-f ran at the same time on one node. Each had disjoint GPUs and CPU
  sets, but host memory bandwidth, PCIe and disk were shared, and contention was not measured.
  Start-up times may include some contention, but the TP 4 engines took 164-182 s with only one
  other start-up beside them. Jobs g (20:33:23-20:42:00Z) and h (20:33:26-20:38:13Z) also ran
  beside three CPU-only jobs of the G2 pilot: two selftests (8 CPUs each, submitted 20:35:55Z
  and 20:36:34Z, about a minute each) and the 16.4 GB Qwen3-8B fetch with per-file SHA-256
  (20:36:56-20:37:53Z). They shared host CPU, memory bandwidth, disk and network; that
  contention was not measured either (added 2026-10-14 from the G2 pilot's independent check;
  `program/evidence/2026-10-14/g2-pilot/README.md`).
- **Synthetic prompts.** The random dataset's prompts are runs of consecutive token ids. MoE
  routing, and so the MoE's bandwidth estimate, may differ on natural text, and the uniform-
  routing estimate is likely high for the MoE at large batch. The one-GPU MoE's chat-128
  estimate (98.5%) is at the ceiling, which suggests it is. Output is forced with `ignore_eos`,
  so lengths are fixed and no output quality is measured.
- **Sampling differs.** Serving used greedy decoding (temperature 0). Offline used the tool's
  default (temperature 1.0).
- **Analytical bandwidth.** The bandwidth numbers are estimates under the stated byte model.
  They exclude activations, all-reduce and attention compute. They are not meaningful for
  prefill-heavy cells; see the TP 4 32k-32 row in `analysis/tables.md`. The GDN term assumes a
  decode step reads and writes each sequence's whole state in the dtype vLLM allocated. The
  kernels' actual traffic was not checked.
- **NVML caveats.** `utilization.memory` is the share of time memory was busy, not bandwidth.
  NVML power is per GPU, and node power was not measured.
- **One build.** Everything is one vLLM build (0.31.0, CUDA 12.9 image on the R570 driver) with
  its default attention backends: FlashAttention 3, with a FlashInfer-JIT GDN prefill for the
  hybrids. Other versions or flags can move these numbers.
- **Config changes.** The one-GPU MoE result (job h) uses `max_num_seqs` 128 rather than the
  grid's 256. It is a separate engine configuration, not a rerun of job e.

## Operational notes and deviations

1. Job e's third engine, the 35B-A3B at TP 1 with `max_num_seqs` 256, was refused at start-up.
   vLLM reported `max_num_seqs (256) exceeds available Mamba cache blocks (181)`, adding "Each
   decode sequence requires one Mamba cache block". 181 is the number of whole blocks in that
   engine's 3.65 GiB. Job h repeated it with 128 (config
   commit `3343668a`; overlay `sha256:9e411974...`, build job 1325). vLLM accepted that, but
   each running sequence took four blocks, so the real limit was 51 at chat length (see the
   block-pool section).
2. Job f's 15-minute limit cut two second repeats, 32k-32 and long-output-128. The driver
   skipped them before the deadline and recorded both. Job g ran both cells twice on a fresh TP
   4 engine.
3. In job d, the offline engine finished all six runs inside the limit. No serving run in any job
   failed or was partial (258 of 258 ok), and every run produced exactly the requested output
   tokens.
4. Two overlay images were built, from commits `f6eaf1b2` (jobs a-f) and `3343668a` (g and h).
   Both builds used builder `aa43283e...` and extractor `9b4d21a8...`, and both reported
   provenance PASS. The source archives were validated on CPU before each build (`capsule/`).
   CPU-only selftests (1312, 1326) parsed every job's argv with vLLM's own parsers. Their
   records are imperfect:
   - `selftest.json` is not valid JSON as stored. vLLM printed "When dataset path is not set,
     it will default to random dataset" to stdout 18 times before the JSON object.
   - The in-image pytest never ran. The image has no pytest (`pytest.txt`: "No module named
     pytest"), and `selftest-cpu.sbatch` swallowed the failure with `|| true`. The same tests
     pass locally (10 passed after this correction).
5. The lane-recorded argv, manifest, image digest, git SHA, model receipt and verification are
   in each `jobs/<job>-<id>/`. `host-run-dir.sha256` hashes 1,128 files of the host run
   directories (the JIT caches excluded). 1,072 are committed, and every one matches its entry.
   The 56 that stay on the host are 7 per job: `container.log`,
   `container-created-inspect.json`, `container-final-inspect.json`, `container-id.txt`,
   `docker-research.sbatch`, `image-inspect.json` and `system.txt`. The tables in `analysis/`
   were computed on the host from those run directories, and the corrected ones from the
   committed copies.

## Corrections after the independent check (2026-10-14)

An independent checker reproduced the first analysis byte for byte and found the problems
below. All are fixed above. Raw records are unchanged, and no GPU job ran.

1. **GDN state dtype (medium).** `scripts/analyze_inference_baseline.py` counted the
   gated-DeltaNet state as bf16. vLLM 0.31.0 keeps the recurrent (SSM) part in float32, in both
   overlay images (`gdn-state-dtype/vllm-gdn-dtype-v3-*.txt`, identical after the header):
   - `model_executor/models/config.py:1060-1062` maps `Qwen3_5ForConditionalGeneration` and
     `Qwen3_5MoeForConditionalGeneration` to `Qwen3_5ForConditionalGenerationConfig`.
   - `config.py:829-832`: when `mamba_ssm_cache_dtype` is "auto", that config copies the
     checkpoint's `mamba_ssm_dtype` into it. All three checkpoints set "float32".
   - `model_executor/layers/mamba/mamba_utils.py:104-110`: `_mamba_state_dtype` gives the
     convolution state the model dtype (bf16) and the temporal state that dtype.
   - Every hybrid engine that started records `mamba_ssm_cache_dtype` float32 in its own
     `cache_config_info` metric (`engine.json`). The logged block sizes (528 tokens; 1,056 for
     the MoE and FP8 KV) and the "0.76%" page padding match float32 exactly.

   The script now takes the dtype from the engine record (else the checkpoint). It also writes
   a GDN-state table, peak running and waiting requests per cell, and the engine's mamba
   dtypes. Per-sequence state went from 25.1 to 49.1 MiB (4B, 9B) and from 31.4 to 61.4 MiB
   (MoE). Changed estimates: 9B long-output-128 state 6.5 to 12.7 GB per step, share 20% to
   33%, bandwidth 64% to 76%; 4B long-output-128 60% to 74%; one-GPU MoE chat-128 94% to 98.5%;
   MoE TP 2 long-output-128 75% to 82%. Batch-1 estimates moved by at most 0.4 points. No dense
   row changed (`corrections/corrections.json`, `hybrid_bandwidth_cells`).
2. **The one-GPU MoE was capacity-bound (medium).** It ran at most 51 sequences at chat-128,
   four blocks each, with 77-79 waiting. The first version said capacity bound only the dense
   models and cited the 181-slot start-up check as the cap. Corrected in the bottom line, the
   HBM section and "What the data says".
3. **`gpu_memory_utilization` (low).** Added vLLM's logged figure for Qwen3-32B TP 1 (13.44 GiB
   would fit, against 6.89 GiB) as the cheapest untried lever, ahead of FP8 KV and TP.
4. **Engine instances and prefix hits (low).** The TP 4 32k-32 ITL figures are now quoted for
   both engine instances, with an instance-spread table. The block-alignment reading of the 9B's
   prefix hit rate is replaced by the check above: it does not fit, explaining only part of the
   gap.
5. **Smaller mismatches and thin records (low).**
   - Throughput spread above 4% includes one cell that is not overhead-bound.
   - Concurrency-1 power reaches 563 W, not 470 W.
   - `serve_cells.csv` has 130 rows, not 128.
   - The offline NVML peak is 75.6 GiB.
   - Start-ups overlapped at most three at a time, not five.
   - The fetch took 5 min 23 s by its receipt.
   - The empty or missing `scontrol` files, the invalid `selftest.json` and the in-image pytest
     that never ran are now stated, and so are the 56 host files not committed.

The operator's report from the first version repeated items 1 and 2: "about 25 MiB GDN state
per sequence", "KV capacity binds only for the dense models", and the state as "about 20% of
the estimated bytes per decode step (6.5 GB)". Those statements are superseded by this README
and by the corrected `program/log.md` entry.

## Files

| Path | Contents |
|---|---|
| `manifests/` | the eight docker-research manifests; each submitter dry-run, test-only and submit output |
| `jobs/<job>-<slurm id>/` | lane receipts (`command.json`, `manifest.json`, `job.env`, `model-receipt.json`, `model-verification.txt`, `provenance-verification.txt`, `termination.env`, `scontrol`, Slurm output) and the driver's `ib/` output (see the next row) |
| `jobs/*/ib/` | `plan.json`, `environment.json`, `models.json`, `summary.json`, `progress.jsonl`, `nvml.csv`, `client.log`; per engine `engine.log`, `engine.json`, `runs/*.json` (vLLM bench result), `runs/*.meta.json` (timings, metrics summary, prefix reset), `runs/metrics/*.csv`, `offline/*` |
| `analysis/` | `serve_runs.csv`, `serve_cells.csv`, `offline_runs.csv`, `engines.csv`, `summary.json`, `tables.md` (all tables; regenerated with the float32 GDN state) |
| `gdn-state-dtype/` | the CPU-only, read-only source checks (jobs 1346, 1348 failed, 1350): sbatch scripts, test-only and submit output, `scontrol`, Slurm output, and the vLLM source lines from both overlay images |
| `corrections/` | `derive_corrections.py` (standard library) and its output `corrections.json`, the numbers behind the corrections; `analysis-rerun.txt`, the host rerun record with hashes |
| `overlay/`, `overlay-2/` | build receipts, image inspection, provenance and selftest inputs of both overlay images |
| `selftest/`, `selftest-2/` | CPU-only parse checks of every argv in the image |
| `capsule/` | source-archive receipts and CPU pre-validation for both commits |
| `fetch/` | the Qwen3-32B fetch lane receipt, summary and log |
| `ops/` | `jobs.log`, `preflight.log` (queue and GPU state before each submission), `render_manifests.py`, `receipts.json`, `collect_job.sh`, `selftest-cpu.sbatch` |

Reproduce the tables:
`python3 scripts/analyze_inference_baseline.py program/evidence/2026-10-14/inference-baseline/jobs --out <dir>`.
The script is standard-library only and reads the committed job directories. Then
`python3 program/evidence/2026-10-14/inference-baseline/corrections/derive_corrections.py <evidence dir> <dir> <old analysis dir>`
gives the correction numbers.
