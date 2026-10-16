# lm2-resident-eval-v1: which model that fits a 128 GB machine to run, and what 2-bit and 3-bit quantization cost DeepSeek V4 Flash 0731 on verifiable tasks

> **EXPLORATORY. Not a registered experiment.** There is no preregistration, no hypothesis test
> and no decision rule. Every number describes one engine run per arm on one node and one
> software stack (stock llama.cpp b11669, CUDA 12.8, H100), on 20 items per task with three
> seeds each. Decision D129 asked for this evaluation. The GPU jobs ran on 2026-10-16 from
> 06:17 to 09:05 UTC. **7.7438 physical GPU-h** of the 8.0 budget were used, pilot,
> diagnostics and cancelled jobs included (`jobs/gpu-hours.json`). Kevin's Mac was not used.
> It is only the target spec.

The question (D129, the dossier's gap G4 at task level): on a 128 GB machine, which model that
fits in memory should Kevin run, and how much does 2-bit or 3-bit quantization cost DeepSeek V4
Flash 0731 against its 8-bit reference on real, verifiable tasks?

## Main takeaways (exploratory)

The primary reading is **"answered within 5,120 output tokens"**. A response that ran longer, or
was still running past 5,120 tokens when its job ended, counts as not answered. The rule is the
same for every arm (section "Output budget"). All arms ran in the **instant tier**: each model's
least-deliberating mode, with V4 Flash in chat (non-thinking) mode. Percent of samples correct,
with 95% item-bootstrap intervals; 20 items x 3 seeds per cell.

| Arm (file, size) | Fit at 32K | Math | Code | Knowledge |
|---|---|---:|---:|---:|
| V4 Flash 0731 UD-Q8_K_XL, 161.9 GB (reference) | No | 38.3 [21.7, 55.0] | 46.7 [28.3, 65.0] | 50.0 [33.3, 66.7] |
| V4 Flash 0731 UD-IQ3_XXS, 104.2 GB | Tight | 48.3 [30.0, 66.7] | 41.7 [23.3, 60.0] | 48.3 [28.3, 68.3] |
| V4 Flash 0731 ds4 Q2, 86.7 GB | Yes | 40.0 [26.7, 55.0] | 35.0 [18.3, 53.3] | 51.7 [31.7, 71.7] |
| gpt-oss-120b MXFP4, 63.4 GB | Yes | 40.0 [23.3, 58.3] | 48.3 [30.0, 66.7] | 40.0 [23.3, 56.7] |
| Qwen3-235B-2507 UD-Q3_K_XL, 104.2 GB | Tight | not resolved (below) | | |

- **G4: the quantization cost inside V4 Flash, paired against Q8** (points, 95% interval over
  items; in brackets, items where the quantized file was better / worse):

  | Contrast | Math | Code | Knowledge | Task mean |
  |---|---:|---:|---:|---:|
  | ds4 Q2 minus Q8 | +1.7 [-10.0, +13.3] (5/5) | -11.7 [-25.0, 0.0] (2/6) | +1.7 [-11.7, +15.0] (5/4) | -2.8 |
  | UD-IQ3_XXS minus Q8 | +10.0 [-1.7, +23.3] (5/2) | -5.0 [-11.7, +1.7] (1/4) | -1.7 [-13.3, +11.7] (4/5) | +1.1 |
  | ds4 Q2 minus UD-IQ3_XXS | -8.3 [-16.7, 0.0] (2/7) | -6.7 [-16.7, +3.3] (2/5) | +3.3 [-10.0, +16.7] (5/4) | -3.9 |

  - On math and knowledge, neither file shows a loss against Q8 that 20 items can resolve. Every
    interval spans about 25 points and includes 0. The UD-IQ3_XXS math gain (+10.0) is within
    that noise.
  - **Code is where the 2-bit file loses: -11.7 points, interval [-25.0, 0.0].** Most of the loss
    is answers that did not finish within 5,120 tokens: 20 of 60 code samples for ds4 Q2 and 16
    of 60 for UD-IQ3_XXS, against 4 of 60 for Q8. These are not repetition loops: the distinct
    16-gram share of their last 6,000 characters is 0.94-1.0, and most UD-IQ3_XXS samples cut at
    5,120 had opened a code fence and were still writing the program. Among the code answers ds4
    Q2 did finish at the 16,384 run cap, it was still 11.1 points below Q8 on the 15 items with
    finished pairs ([-28.9, +4.4]; secondary reading).
  - So the quantized V4 Flash files write longer code answers, and the 2-bit file is worse on
    code even when it finishes. This matches G3's finding that lower precision lengthens output,
    here for weights instead of recurrent state.
- **Between models** (same budget, paired):
  - ds4 Q2 minus gpt-oss-120b: math 0.0 [-11.7, +13.3], code -13.3 [-28.3, +3.3], knowledge
    +11.7 [-8.3, +33.3]; task mean -0.6.
  - UD-IQ3_XXS minus gpt-oss-120b: math +8.3 [-1.7, +20.0], code -6.7 [-16.7, +5.0], knowledge
    +8.3 [-6.7, +25.0]; task mean +3.3.
  - No between-model difference is resolved. gpt-oss is nearer V4 Flash's 8-bit reference on
    code than either quantized V4 file, and lower on SuperGPQA knowledge.
- **Qwen3-235B-2507 is not resolved.** Its only job (1987; 2 GPUs under the share rule) finished
  36 of 135 requests. Every one of its 9 math samples in the first wave was still running past
  about 4,900 tokens when the job ended. At a 4,096-token budget, where those count as failures,
  Qwen has a determined prefix of 3 math, 6 code and 7 knowledge items:
  - its accuracy there is math 0.0, code 50.0 and knowledge 76.2 [47.6, 95.2];
  - on the same items, V4 Q8 scores 0.0 / 55.6 / 57.1 and gpt-oss 11.1 / 61.1 / 47.6.

  Its non-thinking math answers are long. At the dossier's estimated 27-35 tok/s on the Mac,
  4,900 tokens is 2.3-3.0 minutes per unfinished answer. The knowledge figure rests on 7 items.
- **Output length** (mean tokens per sample; under the budget rule):
  - V4 Flash Q8: 1,717 (math), 1,377 (code), 223 (knowledge);
  - UD-IQ3_XXS: 2,005, 2,089, 241;
  - ds4 Q2: 1,854, 2,803, 358;
  - gpt-oss-120b at low effort: 1,386, 1,622, 274. It finished every response within 4,353
    tokens.
- **Decode time on the Mac per correct answer** (derived: tokens per correct answer divided by
  the dossier's Mac decode speed; prefill excluded):

  | Arm | Mac decode tok/s (basis) | Math | Code | Knowledge |
  |---|---|---:|---:|---:|
  | gpt-oss-120b | 105 (community report) | 33 s | 32 s | 7 s |
  | V4 Flash UD-IQ3_XXS | about 36 (estimate) | 115 s | 139 s | 14 s |
  | V4 Flash ds4 Q2 | 39.4 (measured, ds4 maintainer) | 118 s | 204 s | 18 s |

- **Throughput on the H100s** (llama.cpp b11669, layer split, all slots busy; this says nothing
  about the Mac):
  - V4 Flash: about 180-223 generated tok/s per server, at 64 slots on 2 GPUs (Q2, IQ3_XXS) or 3
    GPUs (Q8). Its batched decode costs about 4.5 ms per sequence per step, so the rate does not
    grow with more slots or GPUs. Each slot gets about 3 tok/s.
  - gpt-oss-120b: 364 tok/s on 1 GPU at 24 slots, with backend sampling.
  - Qwen3-235B: 145 tok/s on 2 GPUs at 28 slots.
  - This throughput limit, not the GPU count, is why the suite is small.

### Recommendation for a 128 GB Mac (exploratory, instant tier only)

- **Default resident model: gpt-oss-120b (MXFP4, 63.4 GB).**
  - It sits about 45 GB below the default Metal working-set ceiling and decodes about 2.7 times
    as fast as V4 Flash Q2 on an M5 Max.
  - It finished every answer well inside the budget.
  - On this suite it was not distinguishable from V4 Flash at any precision on the task mean
    (Q2 minus gpt-oss -0.6, IQ3_XXS minus gpt-oss +3.3, every per-task interval including 0).
    It was nearer the 8-bit reference on code than either quantized V4 file.
- **If knowledge-heavy questions matter and the Mac can stop other work: V4 Flash 0731
  UD-IQ3_XXS (104.2 GB, Tight).** It held its 8-bit reference's accuracy here (task mean +1.1).
  V4 Flash's lead over gpt-oss on SuperGPQA (+8.3 for UD-IQ3_XXS) is not resolved.
- **Avoid ds4 Q2 (86.7 GB) for code in chat mode.** It held math and knowledge but lost about 12
  points on code. A third of its code answers did not finish within 5,120 tokens, and it was also
  lower on the code answers it did finish.
- **Qwen3-235B-2507 at 3 bits: no recommendation.** It was not measured well enough. Its
  non-thinking math answers ran past 4,900 tokens in every first-wave sample.
- **Limits of this advice.** It rests on 20 items per task and on CUDA numerics. Thinking modes
  are not measured. Differences smaller than about 10 points are not resolved.

Full tables are in `tables.md` (generated) and `results.json`: by-source accuracy, token
statistics, the secondary and 4,096 readings, and the memory table.

## Design as run

| Item | Setting |
|---|---|
| Engine | Stock llama.cpp b11669 (commit `620d2225`, release v0.7.0), the digest-pinned CUDA 12.8 image `cotcodec-llamacpp:b11669-cu128` (image ID `sha256:fb8600d9...`) through the lane's per-commit overlay; `llama-server` with every layer on the GPUs (`-ngl all --split-mode layer -fit off`), F16 KV cache, flash attention auto (on), `--jinja`, `-cram 0`, `-lm none -lzm off`, a fixed context per slot (`-np` slots, `kv_unified` false). No patch, no model-written GPU code. |
| Tier | Instant: every arm in its least-deliberating mode (LM1's instant tier). |
| Output cap and budget | The runs used a 16,384-token cap (Qwen's stated adequate length for instruct use; context per slot 20,480). Holes were re-run at 8,192 (ds4 Q2) or 5,120 (UD-IQ3_XXS, Qwen). The analysis applies one budget to every arm: a response counts only if it finished within 5,120 tokens (section "Output budget"). |
| Seeds | 42, 43, 44 on every item. Every vendor recommends sampling (temperature 1.0 for V4 Flash and gpt-oss, 0.7 for Qwen), not greedy decoding, so greedy would be off-distribution; three seeds is the program minimum (AGENTS.md rule 7). The sampler seed is a hash of (seed, item id), the same for every arm. |
| Order and size | Within a task, items sorted by the SHA-256 of their id and shuffled with `random.Random(42)`; tasks alternate one item at a time; the three seeds of an item are adjacent. The budget cut keeps a prefix of each task's permutation (`--cap task=N`), so every arm runs the same items: **20 items per task (60 items, 180 samples per arm)** in the analysis. |
| Prompts | Math: the problem, a blank line, then "Please reason step by step, and put your final answer within \boxed{}." Code: LiveCodeBench's generic chat prompt (system text first, in the single user turn). Knowledge: SuperGPQA's zero-shot multiple-choice prompt (last line "Answer: X"). One user turn, no system message, for every arm. |
| Scoring | Math: the last `\boxed{}` of the final answer, checked with G3's checker v2 (`harness.g3_state_precision.math_equiv`). Code: LiveCodeBench's extraction (between the last two lines holding ```), every public and private test must pass, 6 s wall per test, first failure stops, run CPU-only in the sandbox below. Knowledge: the last "Answer: X" against the reference letter. For gpt-oss the final answer is the harmony final channel (llama.cpp's parser); a response cut inside its analysis channel has no answer. |
| Analysis | Per arm and task: the mean over items of the share of correct seeds, with a percentile bootstrap over items (10,000 draws, seed 42). Paired differences use the (item, seed) keys both arms have, bootstrapped over items (question clusters). No multiplicity correction. |

### Arms

| Arm | File (registry id) | Bytes | GPUs, slots | Mode | Sampling (source) |
|---|---|---:|---|---|---|
| `v4f-q8` (reference) | Unsloth UD-Q8_K_XL, 5 shards (`deepseek-v4-flash-0731-ud-q8-k-xl-gguf` @ `fbbb5b93`) | 161,869,621,346 | 3, 64 | non-thinking (DeepSeek chat mode) | T 1.0, top-p 1.0, top-k off, min-p 0 (DeepSeek-V4-Flash-0731 README @ `7872f01b`, non-agentic) |
| `v4f-iq3` | Unsloth UD-IQ3_XXS, 4 shards (`deepseek-v4-flash-0731-ud-iq3-xxs-gguf` @ `fbbb5b93`) | 104,207,853,858 | 2, 64 | same | same |
| `v4f-q2` | antirez ds4 Q2 (IQ2_XXS / Q2_K experts, Q8 attention, shared expert and output; `deepseek-v4-flash-0731-ds4-q2-gguf` @ `f71f23d5`) | 86,720,115,016 | 2, 64 | same | same |
| `qwen235-q3` | Unsloth UD-Q3_K_XL, 3 shards (`qwen3-235b-a22b-instruct-2507-ud-q3-k-xl-gguf` @ `437d6915`) | 104,152,938,929 | planned 3, 32; ran 2, 28 at 9,216 tokens per slot (share rule) | non-thinking (Instruct-2507 has no thinking mode) | T 0.7, top-p 0.8, top-k 20, min-p 0 (Qwen3-235B-A22B-Instruct-2507 README @ `ac9c66cc`) |
| `gptoss120` | ggml-org MXFP4 (`gpt-oss-120b-mxfp4-gguf` @ `238abdd2`), native precision | 63,387,346,665 | 1, 24, backend sampling (`-bs`) | reasoning effort low (its minimum) | T 1.0, top-p 1.0 (openai/gpt-oss README, "Recommended Sampling Parameters") |

- **Templates.** The three V4 Flash files are served with one pinned template, Unsloth's 0731
  template (`experiments/lm2/templates/deepseek-v4-flash-0731-unsloth.jinja`, SHA-256 `e643c31f...`,
  Apache-2.0), passed with `--chat-template-file`, so the prompt bytes are identical across the
  three V4 arms; it mirrors DeepSeek's `encoding_dsv4.py`. The ds4 file's own template (`872492...`)
  renders the same single-turn chat prompt. Each job rendered a fixed probe through
  `/apply-template`; the V4 arms end with `<｜Assistant｜></think>` (chat mode). Qwen uses its
  embedded template (`40c21f34...`). For gpt-oss, llama.cpp's active template (`b2215de6...`)
  differs from the embedded one (`a4c9919c...`) in one line that only affects multi-turn assistant
  history; its system block states the current date (2026-10-16 for every gpt-oss job).
- **Memory per slot.** V4 Flash's llama.cpp KV cache (raw, SWA, CSA and HCA compressed, indexer) was
  about 18 GB for 64 slots of 36,864 tokens (pilot 1802's log), so its slots are not memory-bound.
  Qwen's F16 KV is 188 KiB per token: 28 slots of 9,216 fit on 2 GPUs beside 97 GiB of weights.
  gpt-oss stores 36 KiB per token in its 18 full-attention layers: 24 slots of 20,480 fit on 1 GPU
  beside 58 GiB of weights.

## Task sets

All were fetched by one CPU-only Slurm job (1772; `scripts/fetch_lm2_datasets.py`) at pinned
revisions, checked against the Hub's LFS SHA-256, and normalized on the host. Item text stays on the
host; the repository holds ids, digests and grades only (`data/dataset-receipt.json`).

| Set | Source @ revision | Items used | Licence | Released | Contamination note |
|---|---|---:|---|---|---|
| AIME 2026 | `MathArena/aime_2026` @ `d2de22f3` | 7 of 30 | CC BY-NC-SA 4.0 | 2026-02 | After gpt-oss's cutoff (2024-06) and Qwen3-2507's release (2025-07); before V4 Flash 0731 (2026-07-31). |
| HMMT February 2026 | `MathArena/hmmt_feb_2026` @ `02fba4f7` | 6 of 33 | CC BY-NC-SA 4.0 | 2026-02 | Same as AIME 2026. |
| arxivmath June (4) and August (3) 2026, numeric answers | `MathArena/arxivmath-0626` @ `dca0d771`, `-0826` @ `977a3a00` | 4 + 3 of 48 numeric (57 symbolic dropped) | CC BY-SA 4.0 | 2026-06 to 2026-09 | After every model's release. Symbolic answers with free variables are dropped because checker v2 compares them only as strings. |
| LiveCodeBench v6 increment (`test6.jsonl`, contests 2025-01-04 to 2025-04-06) | `livecodebench/code_generation_lite` @ `0fe84c39` | 20 of 175 | "cc" on the card; problems from LeetCode, AtCoder, Codeforces | 2025-01 to 2025-04 | After gpt-oss's cutoff; before Qwen3-2507 and V4 Flash, so exposure is possible for both. No newer release exists in the official repository (last change 2025-06-05). |
| SuperGPQA (300 items ranked by SHA-256 of id) | `m-a-p/SuperGPQA` @ `4430d445` | 20 of 300 | ODC-BY | 2025-02 | Before every release except gpt-oss's cutoff. |

Within V4 Flash the three files share the same training exposure, so contamination cannot explain a
difference between them; it can bias the between-model rows.

## Code sandbox

Model-written programs ran only in `ops/lm2-code-sandbox.sbatch`: a CPU-only Slurm job (no GRES; it
refuses to start if Slurm or the environment shows a GPU), Docker's runc runtime (no NVIDIA hook;
`--runtime runc`, no `--gpus`, `NVIDIA_VISIBLE_DEVICES=void`), `--network none`, read-only root, an
8 GB tmpfs, `--cap-drop ALL`, no-new-privileges, user 65534, 2,048 pids, 88 GB and 32 CPUs, the
source and input mounted read-only, and verdicts leaving only through stdout. Each program runs as a
child with rlimits (4 GB address space, CPU time, 64 MB files, 64 descriptors, no core) and a 6 s
wall per test. The grader refuses to run if it sees a `/dev/nvidia*` or `/dev/dri` node or a
non-loopback interface, and makes itself non-dumpable so a child cannot reach its descriptors. A
self-test with operator-written probes (job 1793) confirmed: no network, no GPU node, read-only
source, the fork limit, the memory limit and no access to the grader's descriptors.

## Pilot, and why the tier changed

The first plan (commit `87118ed3`) ran V4 Flash in thinking mode at DeepSeek's default effort
(`low`), gpt-oss at `medium`, with a 32,768-token cap and 64, 48 and 32 slots. Four short GPU jobs
measured throughput before anything was scored. None of their outputs enters the analysis.

| Job | Arm, setting | GPUs, slots | Generated tok/s, all slots busy | Per slot | Note |
|---|---|---|---:|---:|---|
| 1802 | V4 Flash ds4 Q2, thinking low, CPU sampling | 2, 64 | about 210 | 3.3 | main thread at 100% of one core, GPUs about 60% busy |
| 1804 | gpt-oss-120b, medium, CPU sampling | 2, 48 | about 285 | 5.9 | main thread at 100% |
| 1830 | V4 Flash ds4 Q2, thinking low, backend sampling (`-bs`) | 2, 64 | about 215 | 3.4 | no gain: the cost is in llama.cpp's DeepSeek V4 decode, not the sampler |
| 1832 | gpt-oss-120b, medium, backend sampling | 2, 48 | about 475 | 9.9 | 1.7x: full-vocabulary CPU sampling (201K tokens, top-k off) was its bottleneck |

Single-stream decode on 4 GPUs was 62 tok/s for this file in the host-prep smoke test, so batch 64
raises V4 Flash's aggregate rate only 3.4-fold. A linear fit to the two points gives about 11.5 ms
plus 4.5 ms per sequence per decode step, so the rate saturates near 220 tok/s per server whatever
the slot count. Jobs 1820 and 1822 failed at argument parsing (`--extra-server-arg -bs` needs `=`)
and generated nothing.

At about 210 tok/s per 2-GPU server and 3.3 tok/s per slot, a thinking-mode suite with three seeds
on three tasks for three V4 files does not fit 8 GPU-hours, and a single thinking response of
10,000 tokens takes about 50 minutes in a full server. The evaluation therefore moved to the instant
tier (commit `e643f2c1`) before any output was scored: V4 Flash in chat mode, gpt-oss at `low` on 1
GPU with backend sampling, and one 16,384-token cap.

## What ran

Every GPU job went through the lane (`scripts/submit_docker_research_job.py`: dry run, test-only,
then submit; `manifests/`), in an overlay of the pinned llama.cpp image built from this branch,
with Slurm GRES and time limits and lane receipts (`jobs/<arm>/<job>/`). Each job pinned
`gpt-oss-120b-mxfp4-gguf` as the lane's model, so the model cache was mounted and that snapshot
was re-hashed in the container. The driver checked the served arm's receipt (digest, revision,
artifact root, sizes). CPU job 1792 re-hashed all five served GGUFs against their receipts
before any GPU job, and all matched. GPU-h are physical: GPUs times the Slurm `RunTime`, from
`scontrol` at the end of each job (`ops/scontrol-*-end.txt`, `jobs/gpu-hours.json`).

| Job | What | GPUs | Run time | GPU-h | Outcome |
|---|---|---:|---:|---:|---|
| 1802 | pilot: ds4 Q2, thinking low, 64 slots | 2 | 00:05:53 | 0.1961 | exit 4 by design (time budget); not analysed |
| 1804 | pilot: gpt-oss, medium, 48 slots | 2 | 00:05:59 | 0.1994 | exit 4 by design; not analysed |
| 1820, 1822 | diagnostic: backend sampling | 2 each | 00:00:55, 00:00:50 | 0.0584 | failed at argument parsing; nothing generated |
| 1830, 1832 | diagnostic: backend sampling (`-bs`) | 2 each | 00:04:40, 00:04:39 | 0.3106 | exit 4 by design; not analysed |
| 1842 | main: ds4 Q2, uncapped, 45-min limit | 2 | 00:40:33 | 1.3517 | 199 done, 58 cut at the end |
| 1844 | main: gpt-oss, uncapped, 30-min limit | 1 | 00:24:27 | 0.4075 | 478 done, 0 cut; complete prefix of 53 items per task |
| 1865 | main: UD-IQ3_XXS, uncapped, 37-min limit | 2 | 00:32:34 | 1.0856 | 230 done, 47 cut |
| 1898 | main: Q8, capped at 30 items per task | 3 | 00:38:13 | 1.9108 | 270 of 270 done (20 per task analysed) |
| 1900 | main: Qwen, 3 GPUs | 3 | 00:00:45 | 0.0375 | **cancelled by the orchestrator** for the 3-GPU share (Deviations) |
| 1933 | top-up: ds4 Q2 holes, resumed from 1842, 16,384 cap | 2 | 00:12:28 | 0.4156 | cancelled by the operator: 20 long code requests could not finish in budget |
| 1949 | top-up: ds4 Q2 holes at 8,192 | 2 | 00:01:58 | 0.0656 | cancelled by the operator: misnamed prior files made it re-run the whole queue; not used |
| 1955 | top-up: ds4 Q2 holes at 8,192 | 2 | 00:17:52 | 0.5956 | 3 done; 19 still running past about 6,300 tokens at the end (censored, below) |
| 1974 | top-up: UD-IQ3_XXS holes at 5,120 | 2 | 00:14:55 | 0.4972 | 24 of 24 done (17 stopped at 5,120) |
| 1987 | main: Qwen, 2 GPUs, 28 slots, 5,120 cap, 15 items per task | 2 | 00:18:22 | 0.6122 | 36 of 135 done, 28 cut |
| | **Total** | | | **7.7438** | |

CPU-only jobs (0 GPU-h): 1764 and 1772 (dataset fetch; 1764 failed reading parquet against the
host's system pandas), 1791, 1797, 1818, 1839, 1945, 1958 and 1975 (overlay builds), 1792 (receipt
re-hash), 1793 (sandbox self-test), 1795 (MathArena aggregates), 1861, 1976, 2011 and 2015
(scoring), 1977 and 2012 (code sandbox).

## Output budget, holes and censored requests

At about 3 tok/s per slot, long V4 Flash answers outlived the jobs that started them. A request
still running when a job's budget ended was lost and had to be re-run from the start. The hole
re-runs could not all reach the 16,384 run cap within 8 GPU-h. So the analysis scores every arm
against one budget it could observe exactly: **an answer counts only if the model stopped within
5,120 output tokens.**

- **Responses from the 16,384 runs.** Responses of 5,120 tokens or fewer are scored as they are.
  Longer ones count as not answered. That affects:
  - Q8: 6 of 180 (2 math, 4 code);
  - ds4 Q2: 4;
  - UD-IQ3_XXS: 3;
  - gpt-oss: 0 (its longest was 4,353 tokens).

  A long response might have had a usable answer inside its first 5,120 tokens. That text was not
  recovered, so this is conservative for the arms with long answers, the 8-bit reference
  included.
- **UD-IQ3_XXS holes** (job 1974) re-ran at `max_tokens` 5,120. 17 of 24 stopped at the cap: 15
  code, 2 math. Those count as not answered.
- **ds4 Q2 holes** (job 1955) re-ran at 8,192. All 22 started together, and in continuous
  batching every running request gains one token per decode step. 19 were still running when the
  job ended after 6,409 decode steps, so each had generated at least about 6,300 tokens without
  stopping. They are failures under the 5,120 budget: `grading/censored-v4f-q2.jsonl`, 18 code
  and 1 math, `censored: true`.
- **Qwen** (job 1987):
  - Its first 28 requests started together and ran for 5,016 decode steps. 12 of them never
    finished, so each passed about 4,900 tokens: short of 5,120, but past 4,096.
  - It therefore enters only the 4,096 reading (`data/caps-budget4096.json`). There its determined
    prefix is 3 math, 6 code and 7 knowledge items, and the 12 count as failures
    (`grading/censored-qwen235-q3-4096.jsonl`).
  - Every other arm is rescored at 4,096 for that table.
- **The secondary reading** (`secondary_16k_completed_only` in `results.json`) keeps only
  responses that finished at the 16,384 run cap. It leaves out the arms' long unfinished answers,
  so it favours the quantized files. ds4 Q2 minus Q8 on code is still -11.1 [-28.9, +4.4] there,
  on 15 items.

## What this does not show

- **Metal against CUDA numerics.** Every number comes from llama.cpp's CUDA backend on H100s
  (layer split across 1-3 GPUs). The Mac runs the same files through Metal kernels. The dossier
  records a 4-5% perplexity gap between two CUDA GPUs on the same file (S117), so the size of a
  quantization cost on Metal may differ; the planned CUDA-against-CPU check (G4) was not run.
- **Thinking modes.** Only the instant tier ran. V4 Flash's thinking modes (`low`, `high`, `max`)
  and gpt-oss's `medium` and `high` are not measured. Earlier work points both ways: thinking
  narrowed V3.1's 3-bit Aider loss from 3.2 to 0.5 points (dossier S19), while G3 found that lower
  precision lengthens reasoning and costs accuracy through truncation.
- **Other prompts and budgets.** One prompt per task and one 16,384-token cap. Other wordings,
  few-shot prompts, system prompts or caps were not tried.
- **Judge-free scope.** Math with numeric answers (symbolic arxivmath answers dropped), code with
  unit tests, and 10-option multiple choice. No open-ended writing, tool use, agentic tasks, long
  context, multi-turn chat or factual recall in free form.
- **Sample size.** 20 items per task, three seeds each. Intervals resample items within one engine
  run per arm; they include no run-to-run or engine variance, and there is no multiplicity
  correction across the many contrasts. Differences of a few points are not resolved.
- **Speed on the Mac.** Host throughput is llama.cpp CUDA serving many requests at once, which says
  nothing about Mac decode speed. The Mac speeds in the memory table are the dossier's (measured for
  ds4 Q2 and gpt-oss-120b, estimated for UD-IQ3_XXS and Qwen3-235B).
- **Other models.** GLM-5.3-Flash, Qwen3.8-27B and Kimi were not run. Kimi K2.5 UD-TQ1_0 (optional)
  was skipped: it needs 3-4 GPUs for its own run and the budget went to the five arms.

## Deviations

1. **Host-sharing breach (D127), corrected by the orchestrator.** The research share through
   2026-10-20 is 3 GPUs at once. LM2 exceeded it:
   - 06:52-07:15 UTC: job 1865 (2 GPUs) was queued while 1842 (2) and 1844 (1) ran, 5 GPUs
     running or pending;
   - 07:15-07:25: 1842, 1865 and 1898 ran together, 7 GPUs, with 1900 (3) pending;
   - 07:25:56-07:26:41: 1898 and 1900 ran together, 6 GPUs.

   The pending jobs also held the transcreate speedrun's jobs back at Slurm priority. The
   orchestrator cancelled 1900 (Qwen on 3 GPUs) 45 s after it started; its 0.0375 GPU-h are in
   the ledger. From then on LM2 held at most 3 GPUs across all jobs, running or pending, one GPU
   job at a time, with tight limits; `ops/lm2-submit.sh` now refuses to submit while another LM2
   GPU job is queued. Qwen was rerun on 2 GPUs after 1898 finished.
2. **The tier changed after the pilot**, before anything was scored: thinking mode (V4 Flash at
   effort low, gpt-oss at medium, 32,768 cap) became the instant tier (section "Pilot").
3. **The suite was cut** from the planned 30 items per task to 20, to fit the budget under the
   share rule. Q8 had already run 30; only its first 20 per task are analysed.
4. **The analysis budgets are post hoc.**
   - **5,120 tokens** (primary) replaced the 16,384 run cap after the main runs, when the long V4
     answers turned out not to finish within the budget (section "Output budget"). It was chosen
     at 08:20 UTC, from token counts and decode rates. The only scores seen before then were a
     scoring smoke test on partial rows (job 1861) and an operator check of 5 chat-mode math rows
     at 06:50.
   - **4,096 tokens** (the Qwen reading) was chosen at 09:05, after the early grades of the V4
     and gpt-oss arms (jobs 1976 and 1977) had been seen. It is the largest budget at which
     Qwen's unfinished requests have a known outcome.
5. **Qwen3-235B** ran on 2 GPUs with 28 slots of 9,216 tokens at `max_tokens` 5,120 and 15 items
   per task. The plan said 3 GPUs and 32 slots; the change followed the share rule. It finished
   36 of 135 requests and appears only in the 4,096 reading.
6. **Operator cancellations.** Job 1933 was cancelled when its 20 long code requests could not
   finish in budget. Job 1949 was cancelled because the staged prior files were named
   `<job>-responses-*.jsonl`, which the driver's `responses*.jsonl` glob misses. Its rows are not
   used.
7. **Backend sampling.** gpt-oss-120b used llama.cpp's `-bs` (marked experimental). The other arms
   sampled on the CPU. The sampler chain is temperature then dist, the same target distribution,
   but the random streams differ.
8. **Lane resume.** Hole re-runs at a different output cap needed a new commit, which the lane's
   resume copy refuses. The earlier responses were therefore copied read-only into the model cache
   (`cotcodec-datasets/lm2-prior/`) and passed with `--prior-dir`.
9. **Small items.**
   - The dataset fetch job ran the pre-format version of `scripts/fetch_lm2_datasets.py` (SHA-256
     `d0744c07...`). It differs from the committed file by one wrapped line.
   - The driver's run ids end in `-1` (the container's PID); arm and Slurm job tell runs apart.
   - Cancelled jobs (1933, 1949) wrote no driver summary; their throughput rows come from their
     metrics alone.
   - The gpt-oss template states the current date (2026-10-16 in every gpt-oss job).

## Files

- `README.md` (this file), `results.json` and `tables.md`.
  - `results.json` holds the primary reading (budget 5,120), `secondary_16k_completed_only` and
    `alt_reading` (budget 4,096 with Qwen), with per-source accuracy, paired contrasts, token
    statistics, throughput, fit tiers and GPU-hours.
  - `tables.md` is generated by `scripts/analyze_lm2.py` from the text-free files below.
- `grading/`: text-free grade rows.
  - `grades-budget5120.jsonl`, `grades-budget4096.jsonl` and `grades-nocap.jsonl`: one row per
    (arm, task, item, seed), with ids, token counts, finish reasons, answer flags and correctness.
  - `code-verdicts.jsonl`: the sandbox's verdicts.
  - `censored-*.jsonl`.
  - The sandbox self-test: its input of operator-written probes, and its verdicts.
- `data/`:
  - `dataset-receipt.json`: sources, revisions, LFS digests, normalized-file digests, counts;
  - `caps-budget5120.json` and `caps-budget4096.json`;
  - `matharena-priors.json`: MathArena's published per-model output-token and accuracy aggregates
    on AIME and HMMT February 2026, used only for sizing.
- `jobs/<arm>/<job>/`: per GPU job, the driver's summary and metrics, the active chat template,
  and the lane's records. `jobs/gpu-hours.json` holds the GPU-hours.
- `manifests/`: every rendered lane manifest with its dry run and test-only check. A `.submit.txt`
  marks the ones submitted.
- `inspect/`: GGUF metadata of the five files (tokenizer arrays dropped), including the embedded
  template digests.
- `ops/`: the operator scripts as they ran, `jobs.log`, `preflight.log`, the `scontrol` records
  and the tails of the CPU jobs' logs.
- `stage-SHA256SUMS.txt`: the SHA-256 of every staged file as it left the host.

Model outputs (`responses-*.jsonl`), server logs, extracted programs and the evaluation sets stay
on the host under `~/cotcodec-runs/stage0/lm2-resident-eval/` and
`~/cotcodec-runs/hf-cache/cotcodec-datasets/`.

## Reproduce

Host scripts are in `ops/` as they ran; `ops/jobs.log` has the times.
1. Fetch and normalize the sets (CPU job): `sbatch --export=ALL,LM2_FETCH_SCRIPT=<path>
   ops/lm2-fetch-datasets.sbatch`
   (job 1772; `scripts/fetch_lm2_datasets.py`, pinned revisions and LFS digests inside it).
2. Re-hash the five served GGUFs against their receipts (CPU job 1792,
   `infra/slurm/host-single-node/verify-models-cpu.sbatch`).
3. Check out the commit from a git bundle (`ops/lm2-checkout.sh <commit>`) and build the lane
   overlay of the pinned llama.cpp image (`ops/lm2-overlay-build.sh <short>`; CPU jobs 1791, 1797,
   1818, 1839).
4. One GPU job at a time, through the lane: `ops/lm2-submit.sh <short> <arm> main <minutes> submit
   [--cap task=N ...] [--slots N]`, with `LM2_RESUME_JOB=<job>` for a top-up and `LM2_GPUS=2` for
   Qwen. The manifests, dry runs and test-only checks are in `manifests/`.
5. Score on the host CPU (jobs 2011 and 2015, run from a clean checkout with `uv run --locked`):
   `scripts/lm2_score.py prepare` at `--analysis-cap` 5,120, 4,096 and none over the main runs;
   `censor` for ds4 Q2 (job 1955, `--min-tokens 6300`) and Qwen (job 1987, caps 3/6/7,
   `--min-tokens 4900`); the sandbox (`ops/lm2-code-sandbox.sbatch`, jobs 1977 and 2012); then
   `finalize --max-rank 20`.
6. From the repository root (CPU, text-free inputs only; reproduces `results.json` and
   `tables.md` byte for byte), with `E=program/evidence/2026-10-16/lm2-resident-eval`:

   ```
   uv run --locked python scripts/analyze_lm2.py \
     --grades $E/grading/grades-budget5120.jsonl --caps $E/data/caps-budget5120.json \
     --grades-16k $E/grading/grades-nocap.jsonl \
     --alt-grades $E/grading/grades-budget4096.jsonl --alt-caps $E/data/caps-budget4096.json \
     --alt-name "Reading at a 4,096-token budget, with Qwen3-235B on its determined prefix" \
     --jobs $E/jobs --gpu-hours $E/jobs/gpu-hours.json --out-json $E/results.json --out-md $E/tables.md
   ```
