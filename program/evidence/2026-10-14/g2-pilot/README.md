# G2 exploratory pilot: GDN-hybrid train-inference mismatch by token position

**EXPLORATORY.** This is the executable pilot of the G2 gauntlet wave (D104). It is not a
registered experiment: there is no preregistration, no decision rule and no confirmatory
claim. Every number below describes these 96 rollouts on this node, nothing more.

**Corrected 2026-10-14** after an independent check. The first analysis binned token entropy
against an edge that YAML had loaded as a string, so every entropy-dependent number was wrong,
and with it the reading that the position trend vanishes at fixed entropy. The analysis was
rerun on the host from the committed `data/per-token.npz`; no GPU job ran. What changed is
listed under [Corrections](#corrections-after-the-independent-check-2026-10-14).

## Main takeaways (corrected)

Exploratory readings of 24 prompts (72 hybrid and 24 dense rollouts, one node, one stack).
"Trainer" here means an unpacked, batch-1 HF+FLA bf16 forward (the dossier's R2), not the
packed verl path.

1. The harness works end to end on stock libraries (vLLM rollouts, teacher forcing through
   HF+FLA in bf16 with a GDN-kernel swap, an fp32 reference) at 0.44 GPU-h.
2. Qwen3.5-4B's rollout-vs-trainer mismatch is small: mean |Δ log p| 0.0076, p99 0.11, k3
   2.7e-4, 0.03% of importance ratios outside [0.8, 1.25].
3. The raw mismatch rises about 12% over the first 3K positions, as token entropy rises
   (0.318 to 0.394 nats). Held at a fixed entropy, it does not grow with position; it falls
   slightly. With entropy-bin fixed effects the slope is -5.2e-5 per 1K [-6.8e-5, -3.5e-5],
   about -0.7% of the mean per 1K, and finer entropy bins give the same. Within sequences
   the raw slope is +2.4e-5 [-2.8e-5, +7.5e-5]. Nothing beyond 11.5K tokens was measured.
4. vLLM decode and the trainer sit about equally far from the fp32 reference (0.0073 and
   0.0076). No second implementation has checked that reference.
5. Every bf16 pair differs by about 0.0075, including the trainer with chunk against
   fused_recurrent GDN. The mismatch sits at a bf16 noise floor that this design cannot see
   beneath, so "the GDN kernel does not matter" is not shown.
6. The dense control (Qwen3-8B) is not size-matched to the 4B, sampled different text and
   ran one seed. It cannot carry a hybrid-vs-dense comparison, and this pilot does not
   evaluate the dossier's kill criterion 1.

- Question (dossier entry 1, `program/evidence/2026-10-14/question-sweep-memory-gpu/dossier.md`):
  does the per-token log-prob mismatch between vLLM rollouts and the HF+FLA trainer grow with
  token position for a Gated-DeltaNet hybrid (Qwen3.5-4B), while a dense control stays flat?
- Config: `experiments/g2/g2-pilot-v1.yaml`. Code: `scripts/run_g2_rollouts.py`,
  `scripts/run_g2_teacher_force.py`, `scripts/analyze_g2_pilot.py`, `harness/g2_pilot.py`,
  tests in `tests/test_g2_pilot.py`.
- GPU use: **0.4402 physical GPU-h** of the 0.5 cap, image builds and one failed attempt
  included (table below; first reported as 0.4372, see Corrections).

## What ran

| Job | What | GPUs | Run time | GPU-h | Outcome |
|---|---|---:|---:|---:|---|
| 1331, 1332 | CPU pre-image selftest: committed scripts mounted into the existing images | 0 | about 1 min each | 0 | 1331: teacher-force selftest failed (no `USER` in the container); 1332: both pass |
| 1333 | GPU-less fetch lane: Qwen3-8B full weights under D1 | 0 | 00:00:58 | 0 | COMPLETED |
| 1334 | vLLM overlay build, commit `cd1692c5` | 1 | 00:01:01 | 0.0169 | COMPLETED, `sha256:8608bc52...` |
| 1335 | research source-overlay build, commit `cd1692c5` | 1 | 00:00:17 | 0.0047 | COMPLETED, `sha256:be6d183d...` |
| 1337 | rollouts, attempt 1 (64 prompts x 3 seeds, no time budget) | 1 | 00:12:52 | 0.2144 | **no data**, cancelled (see Problems) |
| 1338 | CPU post-build selftest of the `cd1692c5` images | 0 | about 1 min | 0 | pass |
| 1339 | vLLM overlay build, commit `307fa7ed` | 1 | 00:01:00 | 0.0167 | COMPLETED, `sha256:fabad633...` |
| 1340 | research source-overlay build, commit `307fa7ed` | 1 | 00:00:16 | 0.0044 | COMPLETED, `sha256:95bb9a2d...` |
| 1343 | CPU post-build selftest of the `307fa7ed` images | 0 | about 1 min | 0 | pass |
| 1342 | rollouts, attempt 2 | 1 | 00:06:45 | 0.1125 | COMPLETED 0:0, `reason=completed` |
| 1352 | teacher forcing | 1 | 00:04:14 | 0.0706 | COMPLETED 0:0, `reason=completed` |
| | **total** | | 00:26:25 on GPUs | **0.4402** | |

Run times are `scontrol` RunTime, except job 1337's. Its 00:12:52 comes from the lane's own
records (`jobs/1337-rollouts-attempt1/job.env` `started_at` 20:43:37Z, `termination.env`
`finished_at` 20:56:29Z), because the RunTime first used (00:12:41, 0.2114 GPU-h) was not
committed and Slurm accounting is off on the host. For jobs 1342 and 1352 the lane's records
agree with RunTime to within a second.

Every GPU job was submitted on a queue with no inference-baseline job (`stage0/inference-baseline`)
running. `ops/preflight.log` holds the GPU state taken just before each submission (all eight
GPUs idle each time); only its first entry also lists the queue (`-- squeue`, empty). The
baseline's GPU jobs g (1329, 20:33:23-20:42:00Z) and h (1330, 20:33:26-20:38:13Z) ended before
the first G2 build was submitted (20:42:09Z). The CPU jobs 1331-1333 did not wait: the two
selftests (no GPU, 8 CPUs each, about a minute each, submitted 20:35:55Z and 20:36:34Z) and the
16.4 GB Qwen3-8B fetch with per-file SHA-256 (20:36:56-20:37:53Z) ran on the same node while
g and h were measuring throughput. They shared host CPU, memory bandwidth, disk and network
with those measurements; the contention was not measured, and the baseline README now says
so.

### Images, code and models

| Item | Identity |
|---|---|
| Rollout image (job 1342) | `cotcodec-vllm` cu129 overlay `sha256:fabad63386d3c39b296e037491d6a6a3b5457c3af31e57764c80ca33c4dec011`; vLLM 0.31.0 (`db9527a4`), torch 2.13.0+cu129, transformers 5.17.0; base `vllm/vllm-openai@sha256:b18abb2d...` (image `sha256:423783aa...`); build receipt `builds/vllm-overlay-307fa7ed-job1339-build-receipt.json` |
| Teacher-forcing image (job 1352) | research source overlay `sha256:95bb9a2d6602f743be1f0556e0aa3283de28a3330991f6996a9d66ffc35c080a`; torch 2.11.0+cu128, transformers 5.15.0, flash-linear-attention 0.5.2, no `causal_conv1d`, no `kernels`; base `cotcodec-research:ed5d5a93-architecture` (image `sha256:500f3b02...`, local-registry digest `sha256:13a9de83...`), offline `uv sync --frozen`; `builds/research-overlay-307fa7ed-job1340.txt` |
| Code in both images | git `307fa7ed2734847091e34e76f50332aa4c7b3982`, source capsule `6c93dc46...` (`builds/source-capsules.json`); attempt 1 used `cd1692c5`, capsule `c3b4e6dc...` |
| Qwen3.5-4B (GDN hybrid) | `Qwen/Qwen3.5-4B` @ `851bf6e8`, 9,342,907,469 bytes, artifact root `3b8a0751...`, receipt `75ebfc53...`; verified by the lane in both jobs |
| Qwen3-8B (dense control) | `Qwen/Qwen3-8B` @ `b968826d`, Apache-2.0, fetched in full under D1 by job 1333 from huggingface.co: 16,397,461,266 bytes, 15 files, artifact root `325ab760...`, receipt `b9e3a74d...` (per-file SHA-256 in `fetch/qwen3-8b-full-receipt.json`). The receipt went to the lane's own receipt root (`cotcodec-receipts-cpu-lane`), so the earlier metadata receipt (`8c206de0...`) was not overwritten. Re-verified by the drivers (`fetch_open_model.py verify`, 12 s) in both jobs |
| Prompts | 64 MATH-500 level-5 problems (`HuggingFaceH4/MATH-500` `test.jsonl` @ `6e4ed1a2`, 446,564 bytes, SHA-256 `35dc4108...`, MIT), chosen with `random.Random(42)`; this run used 24 of them (`g2.prompt_subset`, again seed 42) |
| Rollout data | `tf-input.json` SHA-256 `e50934f2...` (96 sequences), the teacher-forcing job's hash-bound study artifact; raw files and their SHA-256 in `jobs/1342-rollouts/g2/raw-sha256.txt` and `jobs/1352-teacher-force/g2tf/raw-sha256.txt` (kept on the host) |

The chat template is each model's own, thinking on, with Qwen's math suffix ("Please reason
step by step, and put your final answer within \boxed{}"). No `--trust-remote-code`; no
model-generated code ran (D7): the GPUs ran vLLM, torch, transformers and FLA only.

### Design as run, against the plan

| | Planned (dossier; config) | Run |
|---|---|---|
| Prompts | dossier: 64 DAPO-Math prompts x 4; config: 64 MATH-500 level-5 problems | 24 MATH-500 level-5 problems (seeded subset); **not DAPO-Math** |
| Rollouts | Qwen3.5-4B 64 x seeds 42/43/44; Qwen3-8B 64 x seed 42 | Qwen3.5-4B 24 x 3 = 72; Qwen3-8B 24 x 1 = 24 |
| Length | up to 16,384 tokens | a 120 s generation budget per model: Qwen3.5-4B 31 of 72 ended (`<|im_end|>`), 41 cut at 11,503-11,504 tokens; Qwen3-8B 18 of 24 ended, 6 cut (median 6,261, max 11,741) |
| Sampling | T 1.0, top-p 1, top-k off, vLLM `raw_logprobs` of the sampled token | as planned, for both models (Qwen3-8B's `generation_config` T 0.6, top-k 20, top-p 0.95 was not applied); per-request seed; engine seed 42; bf16; prefix caching off; CUDA graphs on (`FULL_AND_PIECEWISE`); FLASH_ATTN; KV cache `auto`; GDN state cache dtype `auto` (the model config sets `mamba_ssm_dtype: float32`; the engine did not log the resolved value) |
| Dossier R1: HF+FLA chunk, bf16, **packed** `cu_seqlens` (the verl trainer path) | dossier | **not run** |
| Dossier R2: the same, unpacked | dossier | run on every rollout (96), batch 1. **This README's "r1" or "trainer" is this path**, named r1 in the code and data |
| R3 HF+FLA `fused_recurrent_gated_delta_rule`, bf16 | every rollout | seed-42 rollouts of Qwen3.5-4B (24) |
| R4 fp32 reference (fp32 upcast weights, TF32 off, memory-efficient SDPA, HF torch-native chunked GDN) | seed-42 rollouts | seed-42 rollouts of both models (48) |
| R5 vLLM prefill recompute | every rollout | **not run** (budget after attempt 1) |
| Common-text arm, FP16 and `mamba_ssm_cache_dtype` arms, per-layer diagnostics | dossier | **not run** |

So "rollout vs trainer" in this pilot means vLLM decode against an unpacked batch-1 HF+FLA
forward. Packing (the path a verl trainer would take) was not measured.

Every forward is one unpacked sequence with no KV cache. The LM head runs on 2,048-position
chunks: logits in the model dtype, fp32 log-softmax (as the trainer does). Entropy is that of
the r1 distribution. The GDN function was swapped through the module global
`modeling_qwen3_5.torch_chunk_gated_delta_rule`; a counter checked 24 GDN calls per forward
on every sequence, and the stock resolution of that global is FLA's
`chunk_gated_delta_rule` (`jobs/1352-teacher-force/g2tf/summary.json`), so r1 is the stock HF
path.

Metrics (per completion token, on the rollout's own tokens; `d = log p_A - log p_B`): mean and
p99 of |d|; for comparisons with the decode path, mean k3 = `exp(r) - 1 - r` with
`r = log p_B - log p_dec` (an estimate of KL(p_dec || p_B), since the tokens are samples from
the decode distribution) and the share of importance ratios `exp(r)` outside [0.8, 1.25].
Four position slopes of |d| (per 1,000 tokens of absolute position), each with a 95%
percentile bootstrap over sequences (2,000 draws, seed 42):

- **pooled**: OLS over all tokens;
- **within entropy bins**: entropy-bin fixed effects, bins [0, 0.01, 0.1, 0.5, 1, 2, inf)
  nats, pooled across sequences;
- **within sequences**: sequence fixed effects, so only positions inside one sequence are
  compared and differences between sequences drop out;
- **within sequence x entropy bin**: both at once (`analysis/tables.md`).

Per 1K position bin the tables also give the mean r1 entropy and an entropy-standardized mean
|d| (the bin's per-entropy-bin means reweighted to the comparison's overall entropy-bin
shares). Sampling is calibrated: the mean -log p of the sampled tokens equals the mean r1
entropy (0.3884 vs 0.3871 nats for the hybrid, 0.2664 vs 0.2667 for the dense model;
`corrections/robustness-checks.json`), as T 1 untruncated sampling requires.

## Results

![mismatch by position](mismatch-by-position.png)

`mismatch-by-position.png` (from `scripts/analyze_g2_pilot.py analyze`): top, every pair of
paths by 1K position bin on the seed-42 rollouts of each model; bottom left, rollout vs
trainer (dec vs r1) per seed, with the all-seed Qwen3.5-4B curve raw (black) and
entropy-standardized (dotted); bottom right, dec vs r1 by entropy bin. Bands are 95% bootstrap
intervals over sequences. Full tables: `analysis/tables.md`; everything: `analysis/analysis.json`.

### Seed-42 rollouts of both models

Slopes per 1K positions [95% CI].

| Model | Comparison | Tokens | Mean abs | p99 abs | k3 | Ratio outside [0.8, 1.25] | Slope, pooled | Slope within entropy bins | Slope within sequences |
|---|---|---:|---:|---:|---:|---:|---|---|---|
| Qwen3.5-4B | dec vs r1 (rollout vs trainer) | 220,099 | 0.0076 | 0.111 | 2.7e-4 | 0.032% | +7.9e-5 [-1.5e-5, +1.8e-4] | -6.2e-5 [-9.2e-5, -3.2e-5] | +1.5e-5 [-7.7e-5, +1.0e-4] |
| Qwen3.5-4B | dec vs r3 (rollout vs trainer, recurrent GDN) | 220,099 | 0.0075 | 0.111 | 2.7e-4 | 0.040% | +7.2e-5 [-1.7e-5, +1.6e-4] | -6.8e-5 [-1.0e-4, -3.2e-5] | +1.6e-6 [-9.0e-5, +7.8e-5] |
| Qwen3.5-4B | dec vs r4 (rollout vs fp32) | 220,099 | 0.0073 | 0.073 | 1.5e-4 | 0.001% | +1.1e-4 [+2.6e-5, +2.1e-4] | -1.8e-5 [-3.6e-5, -2.4e-8] | +4.7e-5 [-4.1e-5, +1.2e-4] |
| Qwen3.5-4B | r1 vs r4 (trainer vs fp32) | 220,099 | 0.0076 | 0.077 | | | +1.1e-4 [+1.6e-5, +2.1e-4] | -2.7e-5 [-4.0e-5, -1.3e-5] | +4.5e-5 [-4.8e-5, +1.3e-4] |
| Qwen3.5-4B | r3 vs r4 | 220,099 | 0.0076 | 0.076 | | | +1.0e-4 [+1.0e-5, +2.0e-4] | -3.5e-5 [-5.2e-5, -1.9e-5] | +3.1e-5 [-6.0e-5, +1.1e-4] |
| Qwen3.5-4B | r1 vs r3 (chunk vs recurrent) | 220,099 | 0.0075 | 0.111 | | | +1.0e-4 [+1.7e-5, +1.9e-4] | -3.4e-5 [-6.2e-5, -7.3e-6] | +3.7e-5 [-4.8e-5, +1.1e-4] |
| Qwen3-8B | dec vs r1 | 167,450 | 0.0123 | 0.190 | 7.3e-4 | 0.42% | -1.6e-4 [-3.1e-4, +2.7e-5] | -2.4e-4 [-3.5e-4, -1.6e-4] | -2.3e-4 [-4.1e-4, -4.4e-5] |
| Qwen3-8B | dec vs r4 | 167,450 | 0.0100 | 0.120 | 3.4e-4 | 0.041% | -1.8e-4 [-3.0e-4, -3.4e-5] | -2.3e-4 [-3.1e-4, -1.6e-4] | -2.5e-4 [-3.8e-4, -1.1e-4] |
| Qwen3-8B | r1 vs r4 | 167,450 | 0.0108 | 0.130 | | | -1.8e-4 [-3.0e-4, -2.7e-5] | -2.4e-4 [-3.3e-4, -1.7e-4] | -2.4e-4 [-3.8e-4, -9.0e-5] |

All three seeds of Qwen3.5-4B (72 rollouts, 679,588 tokens), dec vs r1: mean 0.0076, p99
0.112, k3 2.7e-4. Its four slopes per 1K:

| Estimate | Slope [95% CI] | What it says |
|---|---|---|
| pooled | +7.6e-5 [+2.2e-5, +1.3e-4] | the raw curve rises (mostly over the first 3K); the CI excludes 0 |
| within entropy bins | -5.16e-5 [-6.85e-5, -3.47e-5] | at a fixed entropy the mismatch falls with position; the CI excludes 0 |
| within sequences | +2.4e-5 [-2.8e-5, +7.5e-5] | inside a sequence, no clear trend; the CI includes 0 |
| within sequence x entropy bin | -4.95e-5 [-6.76e-5, -3.01e-5] | inside a sequence at a fixed entropy, it falls; the CI excludes 0 |

Finer entropy control gives the same within-entropy slope: with 6, 20 and 50 entropy
quantile bins it is -4.7e-5, -5.3e-5 and -5.4e-5 per 1K, every CI excluding 0, and within
sequences -4.4e-5, -5.0e-5 and -5.2e-5 (`corrections/robustness-checks.json`). So the
negative slope is not an artifact of entropy drifting inside the six coarse bins.

### Position curve, rollout vs trainer (dec vs r1), seed 42

| Bin start | 4B seqs | 4B mean abs | 4B mean entropy (nats) | 4B entropy-standardized | 8B seqs | 8B mean abs | Mean ratio 4B/8B | 4B p99 | 8B p99 | p99 ratio |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 24 | 0.0069 | 0.317 | 0.0082 | 24 | 0.0112 | 0.62 | 0.109 | 0.196 | 0.56 |
| 1,024 | 24 | 0.0072 | 0.359 | 0.0078 | 24 | 0.0128 | 0.57 | 0.112 | 0.196 | 0.57 |
| 2,048 | 24 | 0.0077 | 0.391 | 0.0077 | 24 | 0.0132 | 0.58 | 0.111 | 0.198 | 0.56 |
| 3,072 | 24 | 0.0075 | 0.386 | 0.0076 | 19 | 0.0145 | 0.52 | 0.109 | 0.201 | 0.54 |
| 4,096 | 23 | 0.0078 | 0.410 | 0.0075 | 17 | 0.0118 | 0.66 | 0.111 | 0.187 | 0.59 |
| 5,120 | 21 | 0.0070 | 0.355 | 0.0076 | 15 | 0.0121 | 0.58 | 0.110 | 0.191 | 0.57 |
| 6,144 | 17 | 0.0076 | 0.396 | 0.0075 | 13 | 0.0131 | 0.58 | 0.112 | 0.194 | 0.58 |
| 7,168 | 15 | 0.0082 | 0.424 | 0.0076 | 11 | 0.0125 | 0.65 | 0.113 | 0.178 | 0.63 |
| 8,192 | 15 | 0.0080 | 0.422 | 0.0074 | 9 | 0.0103 | 0.77 | 0.112 | 0.166 | 0.68 |
| 9,216 | 15 | 0.0084 | 0.454 | 0.0073 | 8 | 0.0097 | 0.86 | 0.113 | 0.171 | 0.66 |
| 10,240 | 15 | 0.0079 | 0.432 | 0.0072 | 6 | 0.0111 | 0.71 | 0.112 | 0.154 | 0.73 |
| 11,264 (partial bin) | 14 | 0.0066 | 0.346 | 0.0076 | 6 | 0.0101 | 0.66 | 0.108 | 0.133 | 0.81 |

The all-seed Qwen3.5-4B curve (72 rollouts, `analysis/tables.md`) rises from 0.0069
[0.0065, 0.0074] in the first bin to 0.0076-0.0081 from 3K on, while the bins' mean r1
entropy rises from 0.318 to 0.390-0.429 nats. Its entropy-standardized curve falls instead,
from 0.0082 in the first bin to 0.0073-0.0076 from 4K on. The early rise is within
sequences: all 72 sequences cover the first three bins, and 46 of 72 have a higher mean |d|
in the third bin (2,048-3,071) than in the first, 51 of 72 a higher mean entropy
(`corrections/robustness-checks.json`). Past 4K the bins lose the shorter rollouts (72, 70,
63, 57, 53, 48, 47, 46 and 41 sequences in the bins from 3K to 11K), so the pooled curve
there mixes position with which rollouts remain; the within-sequence slopes above do not.

### By entropy (dec vs r1, seed 42)

| r1 entropy (nats) | 4B tokens | 4B mean abs | 8B tokens | 8B mean abs | Mean ratio 8B/4B |
|---|---:|---:|---:|---:|---:|
| [0, 0.01) | 99,677 | 0.000009 | 91,423 | 0.000012 | 1.4 |
| [0.01, 0.1) | 25,698 | 0.00068 | 15,002 | 0.00164 | 2.4 |
| [0.1, 0.5) | 29,961 | 0.0063 | 21,616 | 0.0139 | 2.2 |
| [0.5, 1) | 31,330 | 0.0175 | 24,448 | 0.0384 | 2.2 |
| [1, 2) | 26,488 | 0.0259 | 14,448 | 0.0529 | 2.0 |
| [2, inf) | 6,945 | 0.0331 | 513 | 0.0520 | 1.6 |

The mismatch rises steeply with entropy in both models. Within entropy bins (4B, all seeds),
the position slope interval includes 0 in the three bins below 0.5 nats and is negative in
the three above: [0.5, 1) -1.2e-4 [-1.9e-4, -5.4e-5], [1, 2) -1.9e-4 [-2.6e-4, -1.1e-4],
[2, inf) -3.4e-4 [-5.0e-4, -1.8e-4]. These are six of many intervals in an exploratory
table; no correction for multiplicity was made.

### Spread across rollouts

- Per-sequence mean |dec - r1|, Qwen3.5-4B, 72 rollouts: min 0.0051, quartiles 0.0067 /
  0.0071 / 0.0081, max 0.0115. Qwen3-8B, 24 rollouts: min 0.0094, quartiles 0.0111 / 0.0121 /
  0.0126, max 0.0158. The two ranges barely overlap.
- Per seed (Qwen3.5-4B, 24 rollouts each), dec vs r1: mean 0.0076 / 0.0077 / 0.0076, k3
  2.67e-4 / 2.71e-4 / 2.71e-4 for seeds 42 / 43 / 44. Pooled position slopes +7.9e-5
  [-1.5e-5, +1.8e-4], +5.4e-5 [-5.5e-5, +1.5e-4], +9.4e-5 [+1.3e-5, +1.7e-4] (one of three
  excludes 0). Within entropy bins -6.2e-5 [-9.2e-5, -3.2e-5], -5.8e-5 [-8.5e-5, -3.6e-5],
  -3.5e-5 [-6.6e-5, -4.7e-6] (all three exclude 0). Within sequences +1.5e-5 [-7.7e-5,
  +1.0e-4], +6.4e-6 [-1.0e-4, +9.5e-5], +4.9e-5 [-3.2e-5, +1.3e-4] (all three include 0).
  The per-seed curves cross each other throughout (figure, bottom left).

## What the pilot says and what it does not

It says, for these rollouts on this stack:

1. The harness works end to end on stock libraries: vLLM rollouts with streamed sampled-token
   log-probs, teacher forcing of the identical token sequences through HF+FLA in bf16, a swap
   of the trainer's GDN kernel, and an fp32 reference, with receipts, on 0.44 GPU-h.
2. Qwen3.5-4B's rollout-vs-trainer mismatch is small and close to what practitioners report:
   mean |d| 0.0076, k3 2.7e-4, 0.03% of importance ratios outside [0.8, 1.25]. The only
   comparable number the D103 sweep found is first-party (not opened again here):
   radixark/miles PR #3597 (opened 2026-09-22, open;
   https://github.com/radixark/miles/pull/3597) reports `train_rollout_logprob_abs_diff`
   0.0072-0.0096 and KL about 3.6e-4 for Qwen3.5-4B GRPO on 4xB200. The pilot's aggregate
   is consistent with that range. It is a sanity check, not a replication: that number
   comes from a different stack (GRPO training on B200s, its own engine, kernels and
   prompts).
3. No sign of a semantic mismatch between vLLM and HF for Qwen3.5 (dossier kill criterion 4):
   no path differs from the fp32 reference by more than the bf16 paths differ from each other.
4. Neither side looks like the noisy one (kill criterion 3): vLLM decode (0.0073) and the
   HF+FLA trainer (0.0076) sit about equally far from the fp32 reference. That reading treats
   r4 as the truth, which rests on the design and on its smaller tail (p99 0.073-0.077
   against 0.111 for bf16 pairs). The fp32 forward is genuine
   (`jobs/1352-teacher-force/g2tf/summary.json`: fp32 parameters, TF32 off,
   `float32_matmul_precision` highest, the torch-native chunked GDN in fp32 with 24 GDN calls
   per forward enforced, no unrestricted SDPA fallbacks), but no second fp32 implementation
   (for example a torch recurrent GDN) and no fp64 spot check was run on real sequences. The
   only chunk-vs-recurrent agreement check (max 3.6e-7) used a random tiny model on CPU
   (`selftests/selftest-postbuild-307fa7ed/teacher-force-selftest.json`).
5. Swapping the trainer's GDN kernel (FLA chunk for `fused_recurrent`) does not bring the
   trainer closer to the rollout: dec vs r1 0.00758, dec vs r3 0.00755, and the distance to
   fp32 is unchanged (0.0076). But the swap itself moves the trainer's log-probs about as much
   as the whole rollout-trainer mismatch: r1 vs r3 is 0.00747, and every bf16 pair (dec-r1,
   dec-r3, r1-r3) sits near 0.0075 with p99 near 0.111. The measured mismatch is at a
   bf16-vs-bf16 noise floor, and the H2b design cannot resolve differences beneath it. (For
   independent, equal-sized errors a bf16-bf16 distance would be about 1.4x the distance to
   fp32; here it is about 1.0x, which fits bf16 errors correlated at roughly 0.5.) So this
   does not show that the kernel has no effect, and a kill-criterion-2 reading ("drop the
   H2b arm") would be weak.
6. Position (Qwen3.5-4B, all seeds, dec vs r1). The raw mismatch rises by about 12% over the
   first 3K positions (0.0069 to 0.0077), inside sequences, while token entropy rises (mean
   r1 entropy 0.318 to 0.394 nats); after 3K the pooled curve is flat to 11.5K within its
   intervals. The four slope estimates (per 1K) say different things:
   - pooled, raw: +7.6e-5 [+2.2e-5, +1.3e-4], CI excludes 0 (positive);
   - with entropy-bin fixed effects: -5.16e-5 [-6.85e-5, -3.47e-5], CI excludes 0
     (negative);
   - within sequences (sequence fixed effects), raw: +2.4e-5 [-2.8e-5, +7.5e-5], CI
     includes 0;
   - within sequence x entropy bin: -4.95e-5 [-6.76e-5, -3.01e-5], CI excludes 0
     (negative).

   The raw rise is accounted for by the entropy profile of the traces (the J2/J3 concern).
   Beyond it there is not a null but a small negative position effect at fixed entropy,
   about -0.7% of the mean per 1K, robust to finer entropy bins; the entropy-standardized
   curve falls from 0.0082 to 0.0073-0.0076. What causes that decline is not known: later
   tokens at the same entropy may be different kinds of tokens, or the numerics may differ
   with position. Nothing in this pilot separates the two.
7. The dense control, described on its own: Qwen3-8B's rollout-vs-trainer mismatch is mean
   0.0123, p99 0.19, k3 7.3e-4, and every slope estimate is negative (pooled -1.6e-4
   [-3.1e-4, +2.7e-5], CI includes 0; within entropy bins -2.4e-4 [-3.5e-4, -1.6e-4];
   within sequences -2.3e-4 [-4.1e-4, -4.4e-5]). Its per-bin means are 1.2-1.9x the
   hybrid's in every 1K bin and 1.6-2.4x in every entropy bin above 0.01 nats, the top one
   included (the first analysis's "except the top one" was an artifact of the binning bug).
   These ratios are descriptive only. They are not a hybrid-vs-dense comparison (next section).

Kill criterion 1 (hybrid mean and p99 within 1.5x of dense Qwen3-8B in every 1K bin, and the
slope's 95% CI including 0: publish a null note) is **not evaluated** by this pilot. The
dense control cannot carry it (below), and the slope half depends on the estimator: the
pooled raw slope's CI excludes 0 on the positive side, the entropy-adjusted slopes' CIs
exclude 0 on the negative side, and only the within-sequence raw slope's CI includes 0. The
first version of this README read the pilot "as the null" on kill 1; that reading is
withdrawn.

It does not say:

- Anything confirmatory. The sample is 24 prompts, 72 hybrid and 24 dense rollouts, one node,
  one software stack, no preregistration.
- Anything about 11.5K-16K. The generation budget cut 41 of 72 hybrid rollouts at about 11.5K
  tokens, so the last bin is partial and nothing beyond it was measured. Cut rollouts are
  also a length-biased subsample of the traces that would have run to 16K.
- How position and composition separate in the pooled numbers. The pooled slope and the 1K
  curves pool tokens across sequences; from about 3.8K on the bins lose the shorter rollouts
  (41 of 72 hybrid rollouts were cut at 11,503-11,504 tokens, and the dense model has only 6
  sequences past 10K), so differences between sequences enter them. The within-sequence
  slopes remove that, at the cost of wider intervals.
- Anything about a hybrid against a dense model. The dense control is Qwen3-8B against the
  4B hybrid; the dossier names Qwen3-8B as the size match for the 9B. It also has 36 layers
  against 32, an untied LM head, a different vocabulary (about 151K against about 248K
  entries, by the independent check's reading of the configs), one seed against three, a
  shorter and lower-entropy completion profile (median 6,261 against 11,503 tokens; mean r1
  entropy 0.267 against 0.387 nats), and it generated different text from the same prompts.
  The common-text arm, which would hold the text fixed, did not run. Kill criterion 1 is
  defined on the full study, with a size-matched control.
- What causes the tail. p99 |d| is almost the same in every bin (0.108-0.113 for the hybrid,
  0.13-0.20 for the dense model), as a fixed quantization step would make it. One untested
  explanation is bf16 logits: both vLLM and the trainer form logits in bf16, whose spacing at
  logit magnitudes 16-32 is 0.125, and the fp32 reference's tail is smaller (p99 0.073). An
  fp32 LM-head arm would test this; it was not run.
- Anything about packing (dossier R1), vLLM prefill vs decode (R5), FP16, the GDN state-cache
  dtype, the common-text arm or per-layer error. None ran. The prompts are MATH-500 level 5,
  not the dossier's DAPO-Math.
- That the decode path is free of recomputation. The engine was not run with statistics, so
  preemptions were not counted; the KV pools (1.59M and 334K tokens) exceeded the peak demand
  of 72 x 11.8K and 24 x 11.7K tokens, so none is expected.

## Problems

- **Attempt 1 (job 1337) returned no data and cost about 0.2144 GPU-h** (00:12:52 by the
  lane's records; first reported as 0.2114 from an uncommitted RunTime). `LLM.enqueue` in vLLM
  0.31.0 returns internal request ids (`"<n>-<suffix>"`, from `InputProcessor.assign_request_id`),
  while `RequestOutput.request_id` carries the external id; the driver matched them the
  wrong way round, so all 192 finished rollouts (390 s of generation) were counted unmatched
  and dropped. The worker then hung at interpreter exit, past the USR1/TERM sequence, until
  it was cancelled. The CPU selftests could not catch either (no engine without a GPU). Fixed
  in `a97c41e9`: requests go through `LLMEngine.add_request` under our own ids with DELTA
  output (so a request cut at a time budget keeps its tokens), the worker writes `done.json`
  and leaves with `os._exit` after a bounded engine shutdown, and the driver kills a hung
  worker's process group.
- Attempt 1 also showed the plan was too large: 192 rollouts up to 16K tokens had not all
  finished after 6.5 minutes. What remained of the cap set the reduced scope above.
- Job 1331's teacher-force selftest failed because the container had no `USER` (torch's
  Inductor cache path calls `getpass.getuser`); the lane sets `USER`, the selftest script
  now does too.
- **The first analysis binned entropy as text** (corrected; next section).
- The pilot was not wrapped as an orx `slurm-manifest` node (orx is not installed on the
  host), so a gauntlet review may apply the no-executable-pilot cap unless it accepts the
  lane receipts.

## Corrections after the independent check (2026-10-14)

An independent checker reproduced the committed analysis byte for byte and recomputed it from
the raw job outputs on the host. It found one high, one medium and several low problems. All
are fixed here; the raw records and `data/per-token.npz` are unchanged and no GPU job ran.

- **Entropy binning (high).** `experiments/g2/g2-pilot-v1.yaml` wrote the top entropy edge as
  `1.0e9`. PyYAML follows YAML 1.1, which needs a signed exponent for a float, so it loaded
  the edge as the string `'1.0e9'`. `np.asarray` then built a `<U32` string array, and
  `np.searchsorted` compared the entropies with the edges as text, against an edge array that
  is not even sorted as text (an entropy of 3.05e-5, printed in scientific notation, landed
  in [2, inf)). 24.1% of the hybrid's and 24.9% of the dense model's tokens were in the wrong
  bin (`corrections/robustness-checks.json`, which
  reproduces the old binning). Every entropy-dependent number was wrong: the slope within
  entropy bins (all-seed hybrid, first reported +1.3e-5 [-2.3e-5, +4.9e-5], now -5.16e-5
  [-6.85e-5, -3.47e-5]; dense -3.3e-4, now -2.4e-4), the by-entropy table (for example the
  hybrid's [2, inf) bin, first 53,992 tokens at 0.0083, now 6,945 at 0.0331; the dense
  model's, first 36,943 at 0.0070, now 513 at 0.052), the per-entropy-bin slopes and the
  figure's entropy panel. The claim that the position trend is "not a separate position
  effect" (the adjusted slope being null) and "except the top one" in claim 7 do not hold.
  Fixed: the edge is written `1.0e+9`; `harness.g2_pilot.numeric_edges` refuses non-numeric
  or non-increasing edges and `load_config` applies it; the analysis bins through
  `entropy_groups`. New tests fail on string edges and check where known entropies land
  (`tests/test_g2_pilot.py`, 15 passed locally and on the host).
- **Kill criterion 1 (medium).** The "reads as the null" reading is withdrawn (claims above).
  The analysis now reports a within-sequence slope (sequence fixed effects) and a
  sequence-by-entropy-bin slope beside the pooled and entropy-adjusted ones.
- **Low items**, each now stated where it applies: the composition-vs-position caveat;
  the bf16-vs-bf16 noise floor under the chunk-vs-recurrent attribution; the unverified fp32
  reference; the dense control's comparability; the deviations from the dossier (MATH-500
  level 5 instead of DAPO-Math; this README's r1 is the dossier's unpacked R2, and the packed
  R1 did not run); attempt 1's GPU-h from the lane's records (0.2144, pilot total 0.4402,
  still under the 0.5 cap); the CPU jobs beside the baseline's jobs g and h; "matches" the
  miles PR #3597 aggregate is now "is consistent with"; and the `models/registry.yaml` note
  for qwen3-8b, which no longer calls it metadata-only now that its full weights are
  fetched.
- Added: per-position-bin mean entropy and an entropy-standardized mean, by-entropy tables
  with p99 and sequence counts, a hybrid/dense entropy-bin table (`analysis/tables.md`), the
  all-seed raw and standardized curves in the figure, and `corrections/robustness_checks.py`
  (entropy quantile bins, the early rise per sequence, sampling calibration, the old
  misbinning). The rerun record, with commits and SHA-256 of every output, is
  `corrections/analysis-rerun.txt`.

## Reproduce

On the host, from a clean checkout of this branch (CPU only):

```bash
uv run --locked python scripts/analyze_g2_pilot.py analyze \
  --per-token program/evidence/2026-10-14/g2-pilot/data/per-token.npz --output-dir <dir>
uv run --locked python program/evidence/2026-10-14/g2-pilot/corrections/robustness_checks.py \
  --per-token program/evidence/2026-10-14/g2-pilot/data/per-token.npz
```

The committed `analysis/` files and figure reproduce byte for byte on the host
(`corrections/analysis-rerun.txt`). `data/per-token.npz` (written by `analyze_g2_pilot.py
pack` from the two jobs' raw outputs) holds, per model and completion token, the absolute
position, the r1 log-prob (fp32), every other path as an fp16 difference from r1, and the r1
and r4 entropies. `data/rollouts-*-tokens.npz` hold the rollout token ids and decode
log-probs; `data/rollouts-*-texts.jsonl.gz` the completions. The jobs' manifests, lane
records and logs are under `manifests/`, `jobs/`, `builds/`, `fetch/`, `selftests/` and
`ops/` (`ops/jobs.log` is the operator log).

## Next

For the G2 gauntlet wave: the pilot argues for narrowing G2 before spending the 3 GPU-h. At
4B up to 11.5K, the raw position trend follows token entropy, and at fixed entropy the
mismatch falls slightly rather than growing. What is left: (a) whether 11.5K-16K or the 9B
changes that; (b) the bf16 LM-head tail, an fp32 LM-head arm being nearly free; (c) a design
that can see beneath the bf16-vs-bf16 floor before any kernel attribution (per-layer error
against fp32, or a second fp32 implementation to anchor the reference); (d) the packed
trainer path (dossier R1); and (e) a size-matched dense control on common text, without
which no hybrid-vs-dense statement can be made.
