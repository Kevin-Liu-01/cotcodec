# g3-state-precision-accuracy-v1: does a 16-bit GDN recurrent state change task accuracy at inference?

> **EXPLORATORY. Not a registered experiment.** There is no preregistration, no hypothesis test
> and no decision rule. Every number below describes these prompts, models, engines, seeds and
> one submission order on one node and one software stack (vLLM 0.31.0, Triton GDN decode path).
> The GPU jobs ran 2026-10-15 18:01-19:36 UTC. **3.8386 physical GPU-h** (13,819 GPU-s) of the 4.0
> cap were used, image builds, the pilot and the judge included.
>
> **Revision of 2026-10-16 (CPU only, no new GPU job).** Two independent checks reproduced every
> number (`independent-check-findings.json`). This revision applies their findings:
> - The math checker missed 32 equivalent answers on the main run. It is fixed (checker v2), and
>   every math number below is rescored. The checker-v1 outputs are kept in `checker-v1/`.
> - Prior work, the partial fp32 A/A, the seed-order contrasts and the statistics caveats are
>   added, and the headline is reworded.

Follows G2b (D108, `program/evidence/2026-10-15/g2b-state-dtype/`) and G2c (D109,
`program/evidence/2026-10-15/g2c-precision-vs-layout/`). They found that vLLM 0.31.0's
`--mamba-ssm-cache-dtype` float16 or bfloat16, against the checkpoints' float32, gives 1.3-1.4x
throughput in 2K-token saturation waves. They also found that it raises the sampler-trainer
mismatch about 2x (fp16) and 5x (bf16). Neither measured task accuracy. G3 does, with everything
except the state dtype fixed.

## Main takeaways (exploratory)

- **Math, long reasoning (MATH-500 level 5, 134 questions x 3 seeds, thinking on, 32,768
  output tokens).** bf16 lowers accuracy by about 10 points. fp16 lowers it by about 3 points,
  and that estimate is marginal.

  | Model | fp32 | fp16 | bf16 | fp16 - fp32 | bf16 - fp32 |
  |---|---:|---:|---:|---|---|
  | Qwen3.5-4B | 87.1 | 83.3 | 76.4 | -3.7 [-7.2, -0.5] | -10.7 [-14.9, -6.7] |
  | Qwen3.5-9B | 91.5 | 88.8 | 81.6 | -2.7 [-6.0, +0.5] | -10.0 [-13.9, -6.5] |
  | pooled over both models | | | | -3.2 [-6.0, -0.7] | -10.3 [-13.9, -7.0] |

  Percent of rollouts correct (checker v2). Differences are against fp32 on the same question
  and request seed, with 95% question-cluster bootstrap intervals. The pooled row averages the
  two models' per-question differences. All numbers are pooled over one submission order (seed
  42 first) under heavy preemption; the bf16 gap differs by order (seed-order bullet).
  - **bf16 is clear:** -10.7 and -10.0. Both intervals stay well below 0 at a Bonferroni
    level for the four primary contrasts (98.75%: [-16.3, -5.7] and [-14.9, -5.5]).
  - **fp16 is marginal.** On the 4B the 95% interval [-7.2, -0.5] reaches 0 after the
    Bonferroni correction ([-8.2, +0.2]). On the 9B the interval includes 0. Pooled over the
    two models, fp16 is -3.2 [-6.0, -0.7]. It is not replicated: on the pilot's 96 shared
    requests it is +0.0 (4B) and -2.1 (9B) points (partial A/A, Results).
  - Equivalence reading at +-2 points (descriptive): no 16-bit arm is within it.
  - G2b's string match scores the same rollouts under a second scorer, so it is not
    independent support. It gives fp16 -4.5 and -3.5 and bf16 -8.7 and -8.5.
- **Nearly all of the loss is rollouts reaching the 32,768-token cap without a final answer.**
  - The 16-bit states lengthen the reasoning on the same question and seed. Mean length rises by
    +932 [+535, +1,343] tokens (4B, +6.0%) and +938 [+508, +1,399] (9B, +6.8%) with fp16, and
    by +2,935 (+18.8%) and +2,872 (+20.7%) with bf16.
  - The share without a final answer rises by +3.7, +10.9 (4B) and +3.0, +10.4 points (9B).
    That equals the accuracy loss within a point.
  - Rollouts that end on their own are about 99% correct in every arm: 98.9 / 99.1 / 99.0%
    (4B) and 98.9 / 99.2 / 99.4% (9B). At that ceiling a 1-point difference in answer quality
    would go undetected. Wrong final answers actually given number 2-4 per 402 in every arm.
  - The capped 16-bit rollouts are not repetition loops. The distinct 16-gram share of their
    last 8,192 tokens has a median of 0.98 in every arm, as for fp32: 0.986 / 0.983 / 0.984
    (4B) and 0.983 / 0.987 / 0.985 (9B). One of 92 capped 4B bf16 rollouts is below 0.5.
    Rollouts that ended past 24K score 0.974-0.981.
  - Of the rollouts still running at 28K tokens, 29% of fp32's ended before the cap on both
    models, against 21% and 24% for fp16 and 21% and 20% for bf16.
  - Under a shorter cap the gap stays: at 16,384 tokens fp16 is -6.0 (4B) and -3.5 (9B)
    points, bf16 -12.2 and -10.4 (`tables.md`).
  - No data address the model card's 81,920-token budget for competition math. A longer cap
    could shrink the gap or not; this was not measured.
  - This mechanism, a round-to-nearest 16-bit recurrent state lengthening the output, is
    already documented (Prior work). G3 adds the accuracy number for vLLM's stock cast.
- **Seed order: the bf16 gap depends on the submission order; fp32 does not.** Seed 42 was
  submitted first and seed 44 last, all in one batch per engine.
  - The bf16 gap at seed 42 minus its mean at seeds 43-44, paired by question, is -11.9
    [-19.4, -4.9] (4B) and -6.3 [-12.3, -0.7] (9B). For fp16 it is -1.1 [-7.5, +5.2] and +0.7
    [-4.1, +5.6].
  - fp32 accuracy by seed is 87.3 / 86.6 / 87.3 (4B) and 91.0 / 91.0 / 92.5 (9B). By load,
    main minus the lightly loaded pilot is +1.0 and +3.1 points on 96 shared requests. So
    scheduling alone does not create the arm difference; it changes the size of the 16-bit
    effect.
  - So the pooled bf16 estimate is specific to this order under heavy preemption. A lightly
    loaded server, or another order, may see a different gap.
  - A possible cause, not tested, is preemption. vLLM 0.31.0's FCFS scheduler preempts the most
    recently scheduled running request (`v1/core/sched/scheduler.py:771`, `:803`). A preempted
    request restarts from zero computed tokens (`:1560`), so its GDN state is rebuilt by
    prefill, which G2b found as close to the trainer in a 16-bit state as in fp32.
    Per-request preemption was not recorded (`RequestOutput` does not expose it).
  - Evidence for and against the hypothesis:
    - Every request got its first token within 9 s, and seed-44 requests ran at about half
      the per-request token rate of seeds 42-43 in every arm (independent check, from
      `jobs/*/records.json`). That fits preemption falling on the last-submitted requests.
    - But the 9B bf16 gap does not track it (seed 43 -6.7, seed 44 -9.0).
- **Long context, prefill-heavy (LongMemEval-S, full 102-113K-token haystack, thinking off,
  about 20-token replies).** No arm changed the measured accuracy, and a null was expected.
  - About 20 decode steps follow a prefill that G2b found as close to the trainer in a 16-bit
    state as in fp32. So this task barely exercises per-step rounding (as in ReplaySSM's
    RULER-128K, Prior work).
  - Token-identical replies to fp32: on the 9B (100 questions), 94 with fp16 and 88 with
    bf16. On the 4B (50 questions), 47 and 48.
  - The pilot's fp32 replies match the main fp32 replies on 23 of 24 shared questions. So the
    few changed replies are at the engine-nondeterminism level.
  - Judge accuracy (Qwen3-32B, AM1's prompt) is 60 / 61 / 61 (9B) and 52 / 52 / 54 (4B) for
    fp32 / fp16 / bf16. Of the replies that differ, one more is marked correct in three of the
    four cells and none less correct. Containment is identical in every arm.
- **Throughput: each arm's run decoded 3-6% more output tokens per second. This is not fixed
  work.**
  - Output tok/s: +6% (4B) and +5% (9B) with fp16, +4% and +3% with bf16, each from one run on
    its own GPU under the host's shared 700 W power cap.
  - The 16-bit arms also generated longer outputs at longer context, preempted less (372 and
    314 against 469 on the 4B, 450 and 353 against 562 on the 9B), and drained a longer tail.
  - G2b's 1.33-1.38x came from fixed 2,048-token waves (`ignore_eos`) at about 500 running
    sequences. There the 49 MiB fp32 state is comparable to each sequence's attention cache
    (about 64 MiB at 2K tokens) and is read and written at every step.
  - Here sequences average about 15K tokens (about 470 MiB of attention cache each), the
    block pool is full, and 114-128 sequences run at a time. G2b's own block table predicted
    this: 4-20% more 32K sequences fit with a 16-bit state. A fixed-length, cache-bound wave was
    not run.
  - Single runs, so no interval: the fixed request set took 1,410 / 1,405 / 1,607 s (4B) and
    1,400 / 1,429 / 1,636 s (9B). Solved problems per 1,000 engine-seconds were 248 / 238 / 191
    (4B) and 263 / 250 / 200 (9B).
  - Long-context prefill ran at the same rate in every arm: 29.3 / 29.3 / 29.2K prompt tok/s
    (9B) and 37.8 / 37.8 / 37.5K (4B).
- **Reading (exploratory).** On this stack, for long thinking-mode math on these GDN hybrids,
  vLLM's stock 16-bit state is not free.
  - bf16 costs about 10 points of MATH-500 level-5 accuracy at a 32K cap (under this load and
    order).
  - fp16 may cost about 3 points (marginal, not replicated).
  - The loss is longer reasoning that runs out of output budget. The token-rate gain does not
    pay for the longer outputs.
  - For short replies after a long prefill, neither dtype changed the measured accuracy.

## Prior work

A 16-bit recurrent state that rounds to nearest at every step is already known to lengthen
outputs and cost accuracy. Stochastic rounding is known to remove most of the effect. Each source
below was read for this revision (arXiv HTML, 2026-10-16).
- **Nemotron 3 Ultra report** (NVIDIA, arXiv 2606.15007, v1 2026-06-12), §4.5 "SSM Cache
  Optimization", Table 16. Nemotron 3 Super NVFP4 (Mamba-2), emulated quantization, relative to an
  FP32 Mamba cache, averaged over nine benchmarks (MMLU Pro, GPQA, HLE, LiveCodeBench, IFBench,
  OmniScience, AA-LCR, RULER 128K and 256K), no checkpointing.
  - FP16 round-to-nearest (RTN): mean accuracy drop 1.07%, average verbosity increase 9.98%.
  - FP16 stochastic rounding (SR): mean accuracy drop -0.26% (that is, no loss) and verbosity
    increase 0.36%.
  - The text states that "FP16 with stochastic rounding preserves FP32-cache accuracy and
    verbosity."
- **Nemotron 3 Super report** (NVIDIA, arXiv 2604.12374, v1 2026-04-14), §4.3 "Mamba State
  Quantization".
  - Casting the SSM cache directly to FP16 gave "up to 40% increase in verbosity".
  - Table 9 (an early checkpoint, LiveCodeBench) shows +36.95% (W16A16) and +40.27% (W8A8)
    completion tokens with an FP16 cache. FP16 with SR gives +1.79%, at 72.63 accuracy against
    72.91 for FP32.
  - The released model stores the Mamba SSM cache in FP16 with SR (Philox<5>).
- **ReplaySSM** (arXiv 2610.13778, v1 2026-10-09). It caches SSM inputs plus a periodic
  checkpoint, implemented in vLLM for Mamba-2 and Gated DeltaNet.
  - Table 12, Qwen3.5-4B on Math-L5 (1,324 questions; temperature 1.0, top-p 0.95, top-k 20,
    presence penalty 1.5; a token budget set near FP32's 99th-percentile length). FP32 scores
    93.7%. A shared FP16 checkpoint with SR, requantized once per 16-step window, changes it by
    -0.3 points, with mean length 15.9K tokens in both (90th percentile 31.3K and 32.4K).
  - Shared NVFP4+SR costs -1.7 points.
  - RULER-128K is within 0.3 points of FP32 for every configuration and model.
  - Where losses appear they come with failure to finish: on Nemotron-3-Super NVFP4 (GPQA
    Diamond), 20.7% of shared-NVFP4 generations hit the budget against 5.7% for FP32.
  - Its appendix E.4.5 finds that a checkpoint read back into the recurrence needs SR.
  - ReplaySSM is present in this vLLM build (`use_replayssm: False`, `replayssm_buffer_len: 16`
    in every `engine.json`) and was not run.
- **Olmo Hybrid** (arXiv 2604.03444, §5.3 "Decoding Settings", v4). With vLLM, scores dropped
  unless eager mode was used or the GDN cache was stored in FP32 (`--mamba_ssm_cache_dtype
  float32`). The authors suggest that "repeated low-precision downcasting across recurrent steps
  is part of the issue."

**What G3 adds, and how it fits.** G3 measures vLLM 0.31.0's stock `mamba_ssm_cache_dtype`
cast on GDN hybrids under long thinking. That cast rounds to nearest at every decode step. G3
reports both bf16 and fp16. The mechanism is not new.
- G3's fp16 RTN agrees in direction and rough size with the Ultra report's FP16 RTN row: +6-7%
  mean length here against +9.98% verbosity there.
- The accuracy cost is larger here: -3.7 and -2.7 points against 1.07%. The likely reason is
  that long-thinking math at a binding 32K cap turns longer reasoning directly into
  truncation, while Table 16 averages nine benchmarks.
- ReplaySSM's near-null for FP16 on Qwen3.5-4B Math-L5 (-0.3 points, lengths unchanged)
  differs from G3's fp16 result (-3.7 points, +6% length) in three ways, none tested here:
  - rounding mode: SR there, RTN here;
  - rounding frequency: once per 16-step window there, every step here;
  - budget: near FP32's 99th-percentile length there, while 8-12% of fp32 rollouts hit G3's
    cap.
  The question sets (1,324 against 134) and the implementations also differ.
- So the near-null and G3's result do not conflict; they measure different roundings.

## Design as run

| Item | Setting |
|---|---|
| Models | Qwen3.5-4B `851bf6e8`, Qwen3.5-9B `c2022362` (lane-verified receipts; `mamba_ssm_dtype: float32`). Qwen3.6-35B-A3B was not run (budget; What it does not show). |
| Arms | `mamba_ssm_cache_dtype` = `auto` (resolves to float32), `float16`, `bfloat16`, at vLLM's own block size: 528, 272, 272 tokens (worker logs). vLLM casts the state to the cache dtype with round-to-nearest at every decode step. Each model's three arms ran side by side on separate H100s. |
| Engine | G2b's rollout engine: bf16 weights, `gpu_memory_utilization` 0.90, `max_num_seqs` 512, `max_num_batched_tokens` 8,192, prefix caching off, CUDA graphs on, engine seed 42, `logprobs_mode raw_logprobs`, stats on, ReplaySSM off. `max_model_len` 33,792 for math (G2b: 33,536; the longest of these prompts is 857 tokens) and 131,072 for long context. GDN decode on the Triton path ("Falling back to the Triton GDN decode path", as in G2b). |
| Math prompts | All 134 MATH-500 level-5 problems (`experiments/g3/math500-l5-134.jsonl`, from `HuggingFaceH4/MATH-500` `test.jsonl` @ `6e4ed1a2`, SHA-256 `35dc4108...`, MIT, fetched by the G2 pilot; G2's 64 are a subset). User suffix "Please reason step by step, and put your final answer within \boxed{}.", Qwen3.5 chat template, thinking on. |
| Math sampling | The model card's thinking-mode recommendation: temperature 1.0, top-p 0.95, top-k 20, min-p 0, presence penalty 1.5, repetition penalty 1.0; at most 32,768 output tokens ("32,768 tokens for most queries"; the card suggests 81,920 for competition math); stop at `<|im_end|>`; sampled-token log-prob on. Seeds 42, 43, 44 per question; request seed `100000 * seed + question index`, identical in every arm. All 402 requests per engine were submitted at once (seed, then question). Time budget 2,100 s; no rollout was cut by it. |
| Math scoring | Checker v2, `harness.g3_state_precision.math_equiv`. It takes the last `\boxed{}` after the last `</think>` (no closed thinking block means no answer). It then applies MATH-style normalization and exact rational evaluation of plain LaTeX arithmetic. Matrices compare entry by entry, and a two-sided inequality compares with an interval. An unbracketed reference compares as an unordered list, with set braces stripped and one `\pm` per item expanded into its two values. Anything else compares as a string. G2b's string match is reported beside it. |
| Long-context task | LongMemEval-S cleaned (`xiaowu0162/longmemeval-cleaned` @ `98d7416c`, SHA-256 `d6f21ea9...`, MIT, on the host since AM1). Non-abstention questions; within each type ids sorted then shuffled with `random.Random("42:<type>")`, types interleaved by rank / type size. The 9B used the first 100 (main run), the 4B the first 50 (`lme_extra`). The prompt is the full haystack, sessions sorted by date, then the question and date ("Answer the question in one short sentence ... If they do not contain the answer, say \"I don't know\"."). 102,063-113,429 prompt tokens (CPU probe 1488). |
| Long-context sampling | Thinking off; the model card's non-thinking recommendation: temperature 0.7, top-p 0.8, top-k 20, min-p 0, presence penalty 1.5; at most 256 tokens; seed 42; request seed `100000 * 42 + index`. |
| Judge | AM1's primary judge: Qwen3-32B `9216db57`, LongMemEval's answer-check prompt (`harness.memcredit_study.JUDGE_TEMPLATES`), greedy, 10 tokens, thinking off, `max_model_len` 4,096, prefix caching on. Each distinct (question, reply) is judged once, so identical replies get identical labels. Validation per question: the reference answer (expect yes) and "I don't know." (expect no). |
| Analysis | `scripts/analyze_g3_accuracy.py` on the host CPU (texts stay there). Per model x task x arm: per-question means over seeds, averaged over questions. Paired differences against fp32 use a percentile bootstrap over questions (10,000 draws, seed 42), with 95%, 90% and 98.75% (Bonferroni for the four primary contrasts) intervals. The equivalence reading asks whether the 90% (TOST at 5% per side) or the 95% interval lies inside +-2 points. `extras` (host) compares the pilot's fp32 rollouts with the main fp32 arm and measures repetition in capped rollouts from token ids. |

**Statistics caveats.** The intervals resample questions within one engine run per arm. They
include no engine-instance or scheduling variance; the pilot's partial A/A below gives a rough
idea of its size. There is no multiplicity adjustment beyond the Bonferroni column for the four
primary contrasts; the scorer, cap, seed, length and long-context tables add many more
contrasts. Seeds were submitted in order and are not exchangeable (seed-order bullet), so the
seed-averaged estimand belongs to this order.

### Sizing

The pilot (fp32 only, sizing; not in the main tables) ran 48 of the 134 questions x seeds 42 and
43, and 12 long-context questions, on each model (`pilot/pilot.json`, scored with checker v1 at
the time).
- Math accuracy 0.90 and 0.93; mean per-question p(1-p) 0.042 and 0.031. So k = 3 seeds on 134
  questions gives a paired 95% half-width of about +-2.8 (4B) and +-2.4 (9B) points.
- Mean length 13.7K and 12.5K tokens; 7-8% hit the cap.
- Long-context prefill at 37.9K and 27.7K prompt tok/s.
- A block-pool simulation fitted to the pilot's step times (`ops/size_main_sim.py`) put each
  math engine at 930-1,390 s for k = 3. The measured time was 1,400-1,640 s (Deviations).

The realized 95% intervals for the differences (+-3.2 to +-4.1 points) are wider than the pilot
predicted. The 16-bit arms add truncation variance, and 48 x 2 pilot draws gave a low p(1-p).

## What ran

All GPU jobs used the docker-research lane through `scripts/submit_docker_research_job.py`
(dry-run and test-only, then submit; `manifests/`), with digest-pinned images built from this
branch (the G2b route: retained source capsule, offline overlay build), Slurm GRES and time
limits, and lane receipts (`jobs/`). GPU-h are physical: GPUs times the Slurm `RunTime`, read with
`scontrol` at completion (`ops/jobs.log`, `jobs/*/scontrol.txt`).

| Job | What | Image (commit) | Run time | GPU-h | Outcome |
|---|---|---|---:|---:|---|
| 1488 | CPU: LongMemEval-S prompt lengths (G2c image, no GRES) | `7f6d49d7` | ~2 min | 0 | 500 questions, 102,063-113,429 tokens |
| 1489 | vLLM overlay build | `c1bd94ef` -> `a00d30fb` | 00:01:06 | 0.0183 | PASS |
| 1490 | CPU: post-build selftest | `a00d30fb` | ~4 min | 0 | **failed** its fit check (Deviations) |
| 1493 | vLLM overlay build | `4bbf141c` -> `05a6446d` | 00:01:06 | 0.0183 | PASS |
| 1494 | CPU: post-build selftest | `05a6446d` | ~4 min | 0 | pass |
| 1498, 1500 | pilot, fp32: 4B, 9B | `05a6446d` | 00:09:48, 00:11:14 | 0.3506 | COMPLETED 0:0 |
| 1501 | CPU: pilot scoring | host checkout `4bbf141c` | ~1 min | 0 | `pilot/pilot.json` |
| 1508 | vLLM overlay build (main phase declared) | `fd4b909b` -> `13cdd466` | 00:01:05 | 0.0181 | PASS |
| 1509 | CPU: post-build selftest (pilot and main plans) | `13cdd466` | ~4 min | 0 | pass |
| 1517, 1519, 1521 | main: 9B fp32, fp16, bf16 (math, then long context) | `13cdd466` | 00:33:43, 00:34:10, 00:37:36 | 1.7581 | COMPLETED 0:0 |
| 1523, 1525, 1527 | main: 4B fp32, fp16, bf16 (math; long context stopped by the budget USR1) | `13cdd466` | 00:26:32, 00:26:32, 00:28:39 | 1.3619 | math complete; exit 3 by design (1523, 1525 FAILED 3:0; 1527 lane exit 3, USR1 checkpoint confirmed, Slurm record expired, run time = lane interval + 2 s) |
| 1529 | vLLM overlay build (`lme_extra` phase) | `274a2a99` -> `03b8bf02` | 00:01:28 | 0.0244 | PASS |
| 1530 | CPU: preliminary scoring (no judge) | host checkout `274a2a99` | ~2 min | 0 | not the final analysis |
| 1531 | CPU: post-build selftest (all three plans) | `03b8bf02` | ~4 min | 0 | pass |
| 1536, 1538, 1540 | `lme_extra`: 4B fp32, fp16, bf16, 50 long-context questions | `03b8bf02` | 00:04:51, 00:04:51, 00:04:48 | 0.2417 | COMPLETED 0:0 |
| 1541, 1542 | CPU: read-only vLLM scheduler source check | `13cdd466` | <1 min | 0 | `source-check/` |
| 1543 | CPU: scoring and the judge input | host checkout `6ae45397` | ~1 min | 0 | 358 items |
| 1546 | judge, Qwen3-32B | `03b8bf02` | 00:02:50 | 0.0472 | COMPLETED 0:0; validation 194 of 200 |
| 1547 | CPU: analysis with checker v1 | host checkout `6ae45397` | ~1 min | 0 | `checker-v1/` |
| 1555 | CPU: rescoring and analysis with checker v2, `extras` | host checkout `652e9527` | ~2 min | 0 | `analysis/`, `data/` |
| | **Total** | | 13,819 GPU-s | **3.8386** | |

The ledger's five G3 rows (`program/state.json`) are rounded per row and sum to 3.8387; the
difference is rounding. The jobs ran with D110's hosting job on GPU 0. Another registration's
job (1507) held one GPU during build 1508 and was gone before the main run (`ops/preflight.log`).

## Results

`tables.md` holds every table, computed with checker v2:
- accuracy by both scores, the primary contrasts with Bonferroni and pooled intervals, and the
  seed-order contrasts;
- length and truncation shifts, and token-level agreement with fp32;
- math rollouts by arm, accuracy under shorter caps and by seed;
- throughput and solved problems per engine-second.

`results.json` holds the same numbers, plus the GPU-h by job, the post-hoc paired lengths, the
partial A/A, the repetition measure and the checker-v1 accuracies.

### Accuracy (percent; differences in points against fp32, 95% bootstrap intervals over questions)

| Model | Task | Score | Questions | fp32 | fp16 | bf16 | fp16 - fp32 | bf16 - fp32 |
|---|---|---|---:|---:|---:|---:|---|---|
| 4B | math | checker v2 | 134 | 87.1 | 83.3 | 76.4 | -3.7 [-7.2, -0.5] | -10.7 [-14.9, -6.7] |
| 4B | math | G2b string match | 134 | 76.6 | 72.1 | 67.9 | -4.5 [-8.5, -1.0] | -8.7 [-12.9, -4.7] |
| 9B | math | checker v2 | 134 | 91.5 | 88.8 | 81.6 | -2.7 [-6.0, +0.5] | -10.0 [-13.9, -6.5] |
| 9B | math | G2b string match | 134 | 79.9 | 76.4 | 71.4 | -3.5 [-7.0, -0.0] | -8.5 [-12.7, -4.7] |
| 4B | long context | judge | 50 | 52.0 | 52.0 | 54.0 | +0.0 | +2.0 (1 reply gained) |
| 4B | long context | containment | 50 | 40.0 | 40.0 | 40.0 | +0.0 | +0.0 |
| 9B | long context | judge | 100 | 60.0 | 61.0 | 61.0 | +1.0 (1 gained) | +1.0 (1 gained) |
| 9B | long context | containment | 100 | 42.0 | 42.0 | 42.0 | +0.0 | +0.0 |

- On the long-context task the bootstrap intervals are degenerate (0 or 1 changed label), so the
  table gives the label changes instead (`results.json`, `lme_judge_changes_vs_fp32`).
- Checker v1 gave 86.1 / 82.1 / 75.1 (4B) and 89.6 / 87.6 / 80.3 (9B), with differences -4.0,
  -10.9, -2.0 and -9.2 (`checker-v1/`, Deviations).

### Partial fp32 A/A (from the pilot)

The pilot's fp32 rollouts used the main run's request seeds on 48 questions x seeds 42-43 (96
requests per model). They ran under light load: no preemption, peak KV 35-39%, about 40 running
(`analysis/extras.json`).

| Model | Main fp32 - pilot fp32 | Length (tokens) | Longer / shorter (of 96) | First differing token, median (p10, p90) |
|---|---|---|---|---|
| 4B | +1.0 [-4.2, +6.2] | +242 [-447, +955] | 50 / 42 | 237 (36, 803) |
| 9B | +3.1 [+0.0, +8.3] | -186 [-824, +426] | 47 / 45 | 283 (70, 1,091) |

On the same 96 requests, against the main fp32 arm:

| Model | Arm | Accuracy | Length (tokens) | Longer / shorter | First differing token, median |
|---|---|---|---|---|---:|
| 4B | fp16 | +0.0 [-5.2, +5.2] | +630 [-30, +1,324] | 53 / 37 | 325 |
| 4B | bf16 | -6.2 [-13.5, +0.0] | +3,795 [+2,641, +5,026] | 67 / 24 | 279 |
| 9B | fp16 | -2.1 [-5.2, +0.0] | +547 [-111, +1,250] | 55 / 39 | 251 |
| 9B | bf16 | -8.3 [-14.6, -3.1] | +2,783 [+1,764, +3,841] | 66 / 26 | 277 |

- Load and engine instance move fp32 by a few points, with balanced lengths. That is small
  against the bf16 effect, but comparable to the fp16 one.
- **The token-divergence point is batch nondeterminism, not the state dtype.** No pair is
  token-identical, not even fp32 against fp32 under a different load: they diverge at a
  median of 237 (4B) and 283 (9B) tokens. Over all 402 requests, the 16-bit arms diverge from
  fp32 at a median of 246 / 208 (4B fp16 / bf16) and 258 / 259 (9B), as in G2b (about 250). So
  "paired on the same question and seed" pairs by question, in effect.

### Length and truncation (math; per-question means, paired against fp32)

| Model | Measure | fp32 | fp16 | bf16 | fp16 - fp32 | bf16 - fp32 |
|---|---|---:|---:|---:|---|---|
| 4B | mean length (tokens) | 15,586 | 16,517 | 18,521 | +932 [+535, +1,343] | +2,935 [+2,355, +3,526] |
| 4B | hit the 32,768 cap | 11.9% | 15.9% | 22.9% | +4.0 [+0.7, +7.5] | +10.9 [+7.0, +15.2] |
| 4B | no final answer | 12.2% | 15.9% | 23.1% | +3.7 [+0.5, +7.2] | +10.9 [+7.0, +15.2] |
| 9B | mean length (tokens) | 13,843 | 14,782 | 16,715 | +938 [+508, +1,399] | +2,872 [+2,337, +3,415] |
| 9B | hit the 32,768 cap | 7.5% | 10.4% | 17.9% | +3.0 [-0.2, +6.2] | +10.4 [+7.0, +14.4] |
| 9B | no final answer | 7.5% | 10.4% | 17.9% | +3.0 [-0.2, +6.2] | +10.4 [+7.0, +14.4] |

- Ended with EOS, of 402: 354 / 338 / 310 (4B) and 372 / 360 / 330 (9B). Accuracy among them is
  98.9 / 99.1 / 99.0% and 98.9 / 99.2 / 99.4%.
- Among (question, seed) pairs where both arms ended, accuracy is 99.1 against 98.8 (4B fp16),
  99.0 against 99.0 (4B bf16), 99.1 against 99.1 (9B fp16) and 99.4 against 99.4 (9B bf16)
  (`analysis/posthoc.json`).
- Wrong final answers given: 3 / 3 / 2 (4B) and 4 / 3 / 2 (9B) of 402.
- Rollouts capped after their thinking block closed (cut inside the answer): 7 / 8 / 4 and
  3 / 3 / 3.
- Paired lengths: the 16-bit rollout ran longer in 215 against 151 (4B fp16), 257 against 105
  (4B bf16), 230 against 151 (9B fp16) and 266 against 109 (9B bf16) pairs. These sign counts
  treat the 3 seeds of a question as independent; the question-cluster intervals above do not.
  G2c, with 72 pairs and other sampling, saw 37 against 24 for fp16 (p = 0.12).

### Throughput (one engine per model x arm; math: 402 requests at once; single runs)

| Model | Arm | Wall (s) | Output tokens | Output tok/s | vs fp32 | Mean running | Preemptions | Solved per 1,000 s |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 4B | fp32 | 1,410 | 6.27M | 4,443 | | 128 | 469 | 248 |
| 4B | fp16 | 1,405 | 6.64M | 4,725 | 1.06x | 124 | 372 | 238 |
| 4B | bf16 | 1,607 | 7.45M | 4,634 | 1.04x | 126 | 314 | 191 |
| 9B | fp32 | 1,400 | 5.57M | 3,974 | | 117 | 562 | 263 |
| 9B | fp16 | 1,429 | 5.94M | 4,159 | 1.05x | 114 | 450 | 250 |
| 9B | bf16 | 1,636 | 6.72M | 4,106 | 1.03x | 114 | 353 | 200 |

- Block pools as in G2b: 3,733 x 528 against 7,248 x 272 (4B) and 3,137 x 528 against
  6,090 x 272 (9B). Every math engine reached 100% KV use.
- Each arm is one engine instance, and the six engines shared the host and its 700 W power cap
  (D105).

## Deviations and problems

- **Checker v1 missed 32 equivalent answers on the main run** (independent checks).
  It had no handling for a reference written with `\pm` (q085, 18 rollouts), for a `\pm` inside
  set braces (q077, 8), for a two-sided inequality against an interval (q083, 3), or for decimal
  entries in a matrix (q126, 3).
  - The misses fell in every arm: 9B fp32 8, the other five arms 4-5 each. One more was in the
    pilot (4B q083).
  - Checker v2 (`652e9527`) adds those four steps, with tests. Rescoring changed exactly those
    33 verdicts, all from wrong to right, and no other per-request field. Host job 1555 recomputed
    every table.
  - The headline differences moved by at most 0.8 points, and no conclusion changed.
  - Two numbers from the independent check, computed with checker v1, move with v2. The 4B bf16
    seed-order contrast is -11.9 [-19.4, -4.9] against v1's -10.4 [-17.5, -3.4]. The 9B partial
    A/A is +3.1 [+0.0, +8.3] against v1's +1.0 [+0.0, +3.1].
  - Earlier statements that "wrong final answers are rare (7-12 of 402)" and that finished
    rollouts are "96.8-97.9%" correct were checker-v1 artefacts. The v2 figures are 2-4 and
    about 99%.
  - `pilot/pilot.json`, the sizing record, was computed with checker v1 and is kept as it was.
    The pilot's rows rescored with v2 are in `data/per-request.jsonl.gz` (phase `pilot`).
- **Selftest 1490 failed its fit check.** The longest of the 134 math prompts is 857 tokens, and
  G2b's `max_model_len` of 33,536 leaves 768. The math engine's `max_model_len` became 33,792 in
  `4bbf141c`, and the image was rebuilt (1493) before any GPU job.
- **The math phases ran longer than sized, and the 4B's long-context arms moved to a separate
  phase.**
  - Each math engine took 1,400-1,640 s against the simulation's 930-1,390 s. The block pool
    filled after about 2 minutes, and from then on the run was KV-bound with heavy preemption.
  - At 19:06 UTC the projected total with every in-job long-context phase was 3.97 of 4.0
    GPU-h. The three 4B jobs were sent the lane's USR1 when their math phase had saved (1523 and
    1525 at 19:06:14Z, 1527 by `ops/stop-after-math-1527.sh` when its math saved). Their
    long-context workers stopped during engine start and produced no reply; the jobs end FAILED
    3:0 because a declared task did not complete.
  - The 9B jobs ran the long-context phase as declared (100 questions).
  - The 4B's three long-context arms then ran as `lme_extra` on the first 50 of the same 100
    questions, with the same order and request seeds. That needed a config change and a rebuild
    (`274a2a99`, 1529), declared before the jobs (`experiments/g3/`, `lme_extra`). The 4B's
    long-context engines therefore ran alone, without a math phase before them in the same job.
  - An earlier guard for all six jobs (`ops/stop-after-math.sh`) ran 18:59-19:00 UTC and was
    stopped before any math phase ended. It sent no signal.
- **No time cut.** No math rollout hit the 2,100 s budget; the 32,768-token cap is the only
  truncation.
- **The pilot's 12 long-context questions are the first 12 of the main run's 100.** The pilot
  ran fp32 only. It enters the analysis only as the partial A/A.
- **Judge validation: 194 of 200.** Six reference answers were judged "no"; "I don't know." was
  judged "no" 100 of 100 times. The judge's labels are not hand-checked.
- **Slurm record of 1527 expired** before capture (Slurm accounting is off). Its run time is the
  lane interval (00:28:37) plus 2 s, the offset the other jobs show.
- **No fresh-job resume test (AGENTS.md hard rule 2).** As in G2b and G2c, these short
  exploratory jobs have none. On USR1 the driver saves finished tasks and writes the lane's
  checkpoint marker with a "no resume" note (1523, 1525, 1527). A rerun is a new job.
- **Staging and reproducibility.**
  - `checker-v1/analysis/workers.txt` was relativized when staged, so its line in
    `checker-v1/analysis/SHA256SUMS.txt` refers to the host original. The v2 `analysis/workers.txt`
    is the host original and verifies.
  - The per-request file is now written with a gzip mtime of 0, so it reproduces byte for byte
    (`data/per-request.jsonl.gz` matches `analysis/SHA256SUMS.txt`).

## What it does not show

- Anything confirmatory. There is one engine instance per arm, one node, one vLLM build and one
  submission order. There is no dedicated fp32 A/A pair beyond the pilot's 96-request
  comparison, and the design was sized from a 96-rollout pilot.
- Anything about RL training. No training ran, so this says nothing about how an RL trainer
  would respond to 16-bit-state rollouts (G2-RL, D114).
- Other rounding. vLLM rounds the 16-bit state to nearest at every decode step. Stochastic
  rounding, and ReplaySSM's separate read and recurrence precisions (`use_replayssm`, present but
  off in this build), were not run. Prior work finds that both remove most of the effect.
- A lightly loaded server or another submission order. The bf16 gap varied with order, so these
  pooled numbers are specific to this load and order.
- Other kernels or settings: the fused CUDA GDN decode kernel (not built in this image), prefix
  caching, FP8 KV, batch-invariant mode, other engines (SGLang) or other `max_num_seqs`.
- Sampling other than the card's settings (thinking: temperature 1.0, top-p 0.95, top-k 20,
  presence penalty 1.5). G2b's temperature 1.0 and top-p 1 also showed the bf16 length effect.
- Other models: Qwen3.6-35B-A3B and dense models were not run.
- Other output caps. Nothing here addresses the card's 81,920-token budget for competition math,
  where fewer rollouts would be truncated.
- Other tasks or prompt shapes: long-context tasks with long decodes (thinking on), or
  multi-turn agents.
- That preemption order causes the seed pattern (post hoc, untested).
- A long-context difference of a few points. These are 50 and 100 questions with one sample
  each, and the judge is not hand-validated.

## Files

| Path | Contents |
|---|---|
| `results.json`, `tables.md` | the numbers, checker v2 (built by `ops/build_results.py` from `analysis/`) |
| `analysis/` | `results.json` and `tables.md` from `scripts/analyze_g3_accuracy.py analyze`, and `extras.json` from `extras` (host CPU job 1555, git `652e9527`). Also `posthoc.json` (`ops/posthoc_extras.py`), `SHA256SUMS.txt`, `workers.txt` and the judge input's SHA-256 |
| `data/per-request.jsonl.gz` | text-free per request (3,078 rows: main 2,712, `lme_extra` 150, pilot 216): ids, phase, seed, lengths, finish reason, checker-v2 and string-match verdicts, containment, digests of the completion, answer and reply, first differing token against fp32 |
| `checker-v1/` | the outputs before the checker fix: `analysis/`, `results.json`, `tables.md`, the per-request files of the main run and the pilot |
| `independent-check-findings.json` | the two independent checks of the first version (head `8a33006a`). Four quoted final answers (model output) are replaced by descriptions; the file as delivered stays on the host with its SHA-256 in the file's note |
| `pilot/` | `pilot.json` (sizing, checker v1) and its analysis commit |
| `jobs/<id>-<kind>/` | lane receipts (`job.env`, `termination.env`, `manifest.json`, `command.json`, model and provenance verification, GPU prolog, container doctor, compressed container log, `scontrol.txt`). Under `g3/` and `g3judge/`: driver and worker summaries, engine records, progress logs, per-request `records.json` (text-free), phase stats, judge `labels.json`, and `raw-sha256.txt` for the outputs kept on the host |
| `manifests/`, `builds/`, `selftests/`, `probe/`, `source-check/` | every GPU job's manifest with its checks; build receipts and source capsules; CPU selftests; the LongMemEval-S length probe; the vLLM scheduler source lines |
| `ops/` | `jobs.log`, `preflight.log`, build, selftest, submit, manifest, analysis, staging, sizing and budget-guard scripts |

These stay on the host under `~/cotcodec-runs/stage0/g3-state-precision-accuracy/`, with SHA-256
in `jobs/*/g3*/raw-sha256.txt` and `analysis/judge-input-sha256.txt`:
- every completion (`texts.jsonl.gz`) and its token ids (`tokens.npz`);
- the judge input and the judge's replies.

Code: `experiments/g3/g3-state-precision-accuracy-v1.yaml`, `experiments/g3/math500-l5-134.jsonl`,
`harness/g3_state_precision.py`, `scripts/run_g3_accuracy.py`, `scripts/analyze_g3_accuracy.py`,
and `tests/test_g3_state_precision.py`. The tests cover config and plans, paired seeds, 40
checker cases (the four v2 cases and four guards among them), the long-context order and prompt,
and judge items. They also run score-and-analyze end to end (recovering injected differences)
and check the A/A and repetition extras and the deterministic gzip.

### Reproduce

From the committed per-request file alone (CPU, no texts needed): the math and containment
tables, the primary, pooled and seed-order contrasts, the cap and seed tables, and the
token-agreement table.

```bash
uv run --locked python - <<'EOF'
import importlib.util, json, pathlib
spec = importlib.util.spec_from_file_location("a", "scripts/analyze_g3_accuracy.py")
a = importlib.util.module_from_spec(spec); spec.loader.exec_module(a)
E = pathlib.Path("program/evidence/2026-10-16/g3-state-precision-accuracy")
rows = a.read_jsonl_gz(E / "data/per-request.jsonl.gz")
res = a.analyze(rows, None, json.loads((E / "analysis/results.json").read_text())["throughput"],
                10000, 42, 0.02)
print(a.tables_md(res))
EOF
```

- The judge rows need the host-only judge input, and `extras` needs the host-only token ids.
- The full analysis runs on the host: `ops/analysis-cpu.sbatch` with `G3_MODE=analyze` and
  `G3_PILOT_RUNS` set (`ops/jobs.log`, job 1555).
