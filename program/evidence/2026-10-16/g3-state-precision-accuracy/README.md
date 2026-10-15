# g3-state-precision-accuracy-v1: does a 16-bit GDN recurrent state change task accuracy at inference?

> **EXPLORATORY. Not a registered experiment.** There is no preregistration, no hypothesis test
> and no decision rule. Every number below describes these prompts, models, engines and seeds on
> one node and one software stack (vLLM 0.31.0, Triton GDN decode path). The GPU jobs ran
> 2026-10-15 18:01-19:36 UTC. **3.8387 physical GPU-h** of the 4.0 cap were used, image builds,
> the pilot and the judge included.

Follows G2b (D108, `program/evidence/2026-10-15/g2b-state-dtype/`) and G2c (D109,
`program/evidence/2026-10-15/g2c-precision-vs-layout/`). They found that vLLM 0.31.0's
`--mamba-ssm-cache-dtype` float16 or bfloat16, against the checkpoints' float32, gives 1.3-1.4x
throughput in 2K-token saturation waves. They also found that it raises the sampler-trainer
mismatch about 2x (fp16) and 5x (bf16). Neither measured task accuracy. G3 does, with everything
except the state dtype fixed.

## Main takeaways (exploratory)

- **Math, long reasoning (MATH-500 level 5, 134 questions x 3 seeds, thinking on, 32,768
  output tokens).** Both 16-bit states lower accuracy. Points are percent of rollouts correct;
  differences are paired against fp32 on the same question and seed, with 95% question-cluster
  bootstrap intervals.

  | Model | fp32 | fp16 | bf16 | fp16 - fp32 | bf16 - fp32 |
  |---|---:|---:|---:|---|---|
  | Qwen3.5-4B | 86.1 | 82.1 | 75.1 | -4.0 [-7.5, -1.0] | -10.9 [-15.2, -7.0] |
  | Qwen3.5-9B | 89.6 | 87.6 | 80.3 | -2.0 [-5.2, +1.2] | -9.2 [-13.2, -5.7] |

  - Equivalence reading at +-2 points (descriptive): no 16-bit arm is within it. The 90%
    intervals are [-7.0, -1.2] and [-4.7, +0.7] for fp16, and [-14.4, -7.5] and [-12.4, -6.2]
    for bf16. The 9B fp16 interval includes 0 and also reaches -4.7, so the 9B fp16 cell is not
    resolved at this size.
  - G2b's string match gives the same direction: fp16 -4.5 and -3.5, bf16 -8.7 and -8.5.
- **The loss comes from longer reasoning that hits the output cap.** Answers are not worse.
  - The 16-bit states lengthen the reasoning on the same question and seed. The mean length
    rises by +932 [+535, +1,343] tokens (4B) and +938 [+508, +1,399] (9B) with fp16, and by
    +2,935 and +2,872 with bf16.
  - Rollouts that hit the 32,768 cap rise from 11.9% to 15.9% (fp16) and 22.9% (bf16) on the
    4B, and from 7.5% to 10.4% and 17.9% on the 9B.
  - Among (question, seed) pairs where both arms ended on their own, accuracy is the same,
    97.4-98.2% in every arm (`analysis/posthoc.json`).
  - Under a shorter cap the gap stays: at 16,384 tokens fp16 is -6.2 (4B) and -3.0 (9B) points,
    and bf16 -12.2 and -10.2 (`tables.md`).
  - G2c saw no length difference for fp16 with 72 pairs (37 against 24 longer, p = 0.12). Here,
    with 402 pairs and recommended sampling, the fp16 rollout ran longer in 215 against 151
    pairs (4B) and 230 against 151 (9B). These sign tests treat the 3 seeds of a question as
    independent; the question-cluster intervals above do not.
- **Long context, prefill-heavy (LongMemEval-S, full 102-113K-token haystack, thinking off,
  about 20-token replies).** No arm changed the measured accuracy.
  - Token-identical replies to fp32: on the 9B (100 questions), 94 with fp16 and 88 with bf16;
    on the 4B (50 questions), 47 and 48.
  - Of the replies that differ, the judge (Qwen3-32B, AM1's prompt) marks one more correct in
    three of the four cells and none less correct. Judge accuracy is 60 / 61 / 61 (9B) and
    52 / 52 / 54 (4B) for fp32 / fp16 / bf16. The containment check is identical in every arm.
  - These sizes cannot rule out a change of a few points. They show that the state dtype rarely
    changes a short reply after a long prefill.
- **Throughput: in this long-reasoning workload the lever is small and is spent on the longer
  outputs.** Each engine took its 402 math requests at once (G2b's engine settings, 512
  sequences at most).
  - Output tokens per second rise by 6% (4B) and 5% (9B) with fp16, and by 4% and 3% with
    bf16. G2b measured 1.33-1.38x in 2K-token saturation waves.
  - Every arm filled the block pool and preempted: 469 / 372 / 314 preemptions (4B) and
    562 / 450 / 353 (9B). About 115-130 sequences ran at a time. At these lengths the KV cache,
    not the GDN state, is most of each sequence's memory, as G2b's block table predicted (4-20%
    more 32K sequences fit).
  - The fixed request set took 1,410 / 1,405 / 1,607 s (4B) and 1,400 / 1,429 / 1,636 s (9B).
  - Solved problems per 1,000 engine-seconds: 245 / 235 / 188 (4B) and 257 / 246 / 197 (9B).
    That is 4% fewer with fp16 and 23% fewer with bf16.
  - Long-context prefill runs at the same rate in every arm: 29.3 / 29.3 / 29.2K prompt tok/s
    (9B) and 37.8 / 37.8 / 37.5K (4B).
- **Reading (exploratory).** For long thinking-mode reasoning on these hybrids, a 16-bit GDN
  state is not free.
  - bf16 costs about 9-11 points of MATH-500 level-5 accuracy at a 32K cap, and about 23% of
    solved problems per GPU-second.
  - fp16 costs 2-4 points (the 9B interval includes 0) and gives back its 5-6% token
    throughput in longer outputs.
  - For short replies after a long prefill, neither dtype changed the measured accuracy.
  - The behaviour change G2b reported for bf16 (longer, indecisive reasoning) also appears,
    smaller, for fp16.
- **Post hoc, not tested: the bf16 gap depends on submission order.** On the 4B, bf16 is
  -17.9 points for seed 42, -9.0 for seed 43 and -6.0 for seed 44. On the 9B it is -13.4, -6.7
  and -7.5. fp16 shows no such order.
  - A possible cause is preemption. Seed 42 was submitted first and seed 44 last.
  - vLLM 0.31.0's FCFS scheduler preempts the most recently scheduled running request
    (`v1/core/sched/scheduler.py:771`, `:803`). A preempted request restarts from zero computed
    tokens (`:1560`), so its GDN state is rebuilt by prefill. G2b found prefill as close to the
    trainer in a 16-bit state as in fp32.
  - Later requests would then spend less of their decode in drifting 16-bit state.
  - Per-request preemption counts are not exposed in `RequestOutput` and were not recorded, so
    this is not tested. If it holds, a lightly loaded server would see a larger bf16 gap than
    the pooled -9 to -11 points.

## Design as run

| Item | Setting |
|---|---|
| Models | Qwen3.5-4B `851bf6e8`, Qwen3.5-9B `c2022362` (lane-verified receipts; `mamba_ssm_dtype: float32`). Qwen3.6-35B-A3B was not run (budget; What it does not show). |
| Arms | `mamba_ssm_cache_dtype` = `auto` (resolves to float32), `float16`, `bfloat16`, at vLLM's own block size: 528, 272, 272 tokens (worker logs). Each model's three arms ran side by side on separate H100s. |
| Engine | G2b's rollout engine: bf16 weights, `gpu_memory_utilization` 0.90, `max_num_seqs` 512, `max_num_batched_tokens` 8,192, prefix caching off, CUDA graphs on, engine seed 42, `logprobs_mode raw_logprobs`, stats on. `max_model_len` 33,792 for math (G2b: 33,536; the longest of these prompts is 857 tokens) and 131,072 for long context. GDN decode on the Triton path ("Falling back to the Triton GDN decode path", as in G2b). |
| Math prompts | All 134 MATH-500 level-5 problems (`experiments/g3/math500-l5-134.jsonl`, from `HuggingFaceH4/MATH-500` `test.jsonl` @ `6e4ed1a2`, SHA-256 `35dc4108...`, MIT, fetched by the G2 pilot; G2's 64 are a subset). User suffix "Please reason step by step, and put your final answer within \boxed{}.", Qwen3.5 chat template, thinking on. |
| Math sampling | The model card's thinking-mode recommendation: temperature 1.0, top-p 0.95, top-k 20, min-p 0, presence penalty 1.5, repetition penalty 1.0; at most 32,768 output tokens ("32,768 tokens for most queries"); stop at `<|im_end|>`; sampled-token log-prob on. Seeds 42, 43, 44 per question; request seed `100000 * seed + question index`, identical in every arm. All 402 requests per engine were submitted at once (seed, then question). Time budget 2,100 s; no rollout was cut by it. |
| Math scoring | `harness.g3_state_precision.math_equiv`: the last `\boxed{}` after the last `</think>` (no closed thinking block means no answer). MATH-style normalization, exact rational evaluation of plain LaTeX arithmetic, unordered comparison of unbracketed lists, else string equality. G2b's string match is reported beside it. |
| Long-context task | LongMemEval-S cleaned (`xiaowu0162/longmemeval-cleaned` @ `98d7416c`, SHA-256 `d6f21ea9...`, MIT, on the host since AM1). Non-abstention questions; within each type ids sorted then shuffled with `random.Random("42:<type>")`, types interleaved by rank / type size. The 9B used the first 100 (main run), the 4B the first 50 (`lme_extra`). The prompt is the full haystack, sessions sorted by date, then the question and date ("Answer the question in one short sentence ... If they do not contain the answer, say \"I don't know\"."). 102,063-113,429 prompt tokens (CPU probe 1488). |
| Long-context sampling | Thinking off; the model card's non-thinking recommendation: temperature 0.7, top-p 0.8, top-k 20, min-p 0, presence penalty 1.5; at most 256 tokens; seed 42; request seed `100000 * 42 + index`. |
| Judge | AM1's primary judge: Qwen3-32B `9216db57`, LongMemEval's answer-check prompt (`harness.memcredit_study.JUDGE_TEMPLATES`), greedy, 10 tokens, thinking off, `max_model_len` 4,096, prefix caching on. Each distinct (question, reply) is judged once, so identical replies get identical labels. Validation per question: the reference answer (expect yes) and "I don't know." (expect no). |
| Analysis | `scripts/analyze_g3_accuracy.py` on the host CPU (texts stay there). Per model x task x arm: per-question means over seeds, averaged over questions. Paired differences against fp32 use a percentile bootstrap over questions (10,000 draws, seed 42), with 95% and 90% intervals. The equivalence reading asks whether the 90% (TOST at 5% per side) or the 95% interval lies inside +-2 points. |

### Sizing

The pilot (fp32 only, sizing; not in the analysis) ran 48 of the 134 questions x seeds 42 and 43,
and 12 long-context questions, on each model (`pilot/pilot.json`).
- Math accuracy 0.90 and 0.93; mean per-question p(1-p) 0.042 and 0.031. So k = 3 seeds on 134
  questions gives a paired 95% half-width of about +-2.8 (4B) and +-2.4 (9B) points.
- Mean length 13.7K and 12.5K tokens; 7-8% hit the cap.
- Long-context prefill at 37.9K and 27.7K prompt tok/s.
- A block-pool simulation fitted to the pilot's step times (`ops/size_main_sim.py`) put each
  math engine at 930-1,390 s for k = 3. The measured time was 1,400-1,640 s (Deviations).

The realized intervals (+-3.2 to +-4.1 points for the differences) are wider than the pilot
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
| 1547 | CPU: final analysis | host checkout `6ae45397` | ~1 min | 0 | `analysis/` |
| | **Total** | | 13,819 GPU-s | **3.8387** | |

The jobs ran with D110's hosting job on GPU 0. Another registration's job (1507) held one GPU
during build 1508 and was gone before the main run (`ops/preflight.log`).

## Results

`tables.md` holds every table: accuracy by both scores, length and truncation shifts,
token-level agreement with fp32, math rollouts by arm, accuracy under shorter caps and by seed,
throughput, and solved problems per engine-second. `results.json` holds the same numbers, the
GPU-h by job and the post-hoc paired-length counts.

### Accuracy (percent; differences in points against fp32, 95% bootstrap intervals over questions)

| Model | Task | Score | Questions | fp32 | fp16 | bf16 | fp16 - fp32 | bf16 - fp32 |
|---|---|---|---:|---:|---:|---:|---|---|
| 4B | math | checker | 134 | 86.1 | 82.1 | 75.1 | -4.0 [-7.5, -1.0] | -10.9 [-15.2, -7.0] |
| 4B | math | G2b string match | 134 | 76.6 | 72.1 | 67.9 | -4.5 [-8.5, -1.0] | -8.7 [-12.9, -4.7] |
| 9B | math | checker | 134 | 89.6 | 87.6 | 80.3 | -2.0 [-5.2, +1.2] | -9.2 [-13.2, -5.7] |
| 9B | math | G2b string match | 134 | 79.9 | 76.4 | 71.4 | -3.5 [-7.0, -0.0] | -8.5 [-12.7, -4.7] |
| 4B | long context | judge | 50 | 52.0 | 52.0 | 54.0 | +0.0 | +2.0 (1 reply gained) |
| 4B | long context | containment | 50 | 40.0 | 40.0 | 40.0 | +0.0 | +0.0 |
| 9B | long context | judge | 100 | 60.0 | 61.0 | 61.0 | +1.0 (1 gained) | +1.0 (1 gained) |
| 9B | long context | containment | 100 | 42.0 | 42.0 | 42.0 | +0.0 | +0.0 |

On the long-context task the bootstrap intervals are degenerate (0 or 1 changed label), so the
table gives the label changes instead (`results.json`, `lme_judge_changes_vs_fp32`).

### Length and truncation (math; per-question means, paired against fp32)

| Model | Measure | fp32 | fp16 | bf16 | fp16 - fp32 | bf16 - fp32 |
|---|---|---:|---:|---:|---|---|
| 4B | mean length (tokens) | 15,586 | 16,517 | 18,521 | +932 [+535, +1,343] | +2,935 [+2,355, +3,526] |
| 4B | hit the 32,768 cap | 11.9% | 15.9% | 22.9% | +4.0 [+0.7, +7.5] | +10.9 [+7.0, +15.2] |
| 4B | no final answer | 12.2% | 15.9% | 23.1% | +3.7 [+0.5, +7.2] | +10.9 [+7.0, +15.2] |
| 9B | mean length (tokens) | 13,843 | 14,782 | 16,715 | +938 [+508, +1,399] | +2,872 [+2,337, +3,415] |
| 9B | hit the 32,768 cap | 7.5% | 10.4% | 17.9% | +3.0 [-0.2, +6.2] | +10.4 [+7.0, +14.4] |
| 9B | no final answer | 7.5% | 10.4% | 17.9% | +3.0 [-0.2, +6.2] | +10.4 [+7.0, +14.4] |

- Ended with EOS, of 402: 354 / 338 / 310 (4B) and 372 / 360 / 330 (9B). Accuracy among
  them: 97.7 / 97.6 / 97.4% and 96.8 / 97.8 / 97.9%.
- Wrong final answers given are rare in every arm (7-12 of 402). The checker's misses on the
  pilot were one interval written as an inequality (Deviations, Checker).
- Every pair diverges in tokens. The first differing token is at a median of 246 and 208 (4B
  fp16, bf16) and 258 and 259 (9B), as in G2b (about 250).

### Throughput (one engine per model x arm; math: 402 requests at once)

| Model | Arm | Wall (s) | Output tokens | Output tok/s | vs fp32 | Mean running | Preemptions | Solved per 1,000 s |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 4B | fp32 | 1,410 | 6.27M | 4,443 | | 128 | 469 | 245 |
| 4B | fp16 | 1,405 | 6.64M | 4,725 | 1.06x | 124 | 372 | 235 |
| 4B | bf16 | 1,607 | 7.45M | 4,634 | 1.04x | 126 | 314 | 188 |
| 9B | fp32 | 1,400 | 5.57M | 3,974 | | 117 | 562 | 257 |
| 9B | fp16 | 1,429 | 5.94M | 4,159 | 1.05x | 114 | 450 | 246 |
| 9B | bf16 | 1,636 | 6.72M | 4,106 | 1.03x | 114 | 353 | 197 |

- Block pools as in G2b: 3,733 x 528 against 7,248 x 272 (4B) and 3,137 x 528 against
  6,090 x 272 (9B). Every math engine reached 100% KV use.
- Each arm is one engine instance, and the six engines shared the host and its 700 W power cap
  (D105).

## Deviations and problems

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
    (`274a2a99`, 1529), declared before the jobs (`experiments/g3/`, `lme_extra`).
  - An earlier guard for all six jobs (`ops/stop-after-math.sh`) ran 18:59-19:00 UTC and was
    stopped before any math phase ended. It sent no signal.
- **The 9B's long-context results come from the main jobs, the 4B's from `lme_extra`.** The
  4B's long-context engines ran alone, without a math phase before them in the same job.
- **No time cut.** No math rollout hit the 2,100 s budget; the 32,768-token cap is the only
  truncation.
- **The pilot's 12 long-context questions are the first 12 of the main run's 100.** The pilot
  ran fp32 only and is not in the analysis.
- **Judge validation: 194 of 200.** Six reference answers were judged "no"; "I don't know." was
  judged "no" 100 of 100 times. The judge's labels are not hand-checked.
- **Checker.** On the pilot, every disagreement with G2b's string match was a true equivalence
  (5.5 and 11/2, x=-4 and -4, 0.25 and 1/4, dollar signs, an unordered pair of roots). One true
  answer was missed: an interval written as an inequality. The same checker scores every arm.
- **Slurm record of 1527 expired** before capture (Slurm accounting is off). Its run time is the
  lane interval (00:28:37) plus 2 s, the offset the other jobs show.
- **No fresh-job resume test (AGENTS.md hard rule 2).** As in G2b and G2c, these short
  exploratory jobs have none. On USR1 the driver saves finished tasks and writes the lane's
  checkpoint marker with a "no resume" note (1523, 1525, 1527). A rerun is a new job.
- **The sign tests on paired lengths** (`analysis/posthoc.json`) treat the 3 seeds of a question as
  independent. The question-cluster bootstrap intervals in the tables are the main measure.

## What it does not show

- Anything confirmatory. There is one engine instance per arm, one node and one vLLM build, with
  no fp32 A/A engine pair, and the design was sized from a 96-rollout pilot.
- Anything about RL training. No training ran, so this says nothing about how an RL trainer
  would respond to 16-bit-state rollouts (G2-RL, D114).
- Other kernels or settings: the fused CUDA GDN decode kernel (not built in this image), prefix
  caching, FP8 KV, batch-invariant mode, other engines (SGLang) or other `max_num_seqs`.
- Other models: Qwen3.6-35B-A3B and dense models were not run.
- Other output caps. At the card's 81,920 tokens for competition math, fewer rollouts would be
  truncated. The accuracy cost might then shrink while the token cost grows. This was not
  measured.
- Other tasks or prompt shapes: long-context tasks with long decodes (thinking on), or
  multi-turn agents.
- That preemption order causes the seed pattern (post hoc, untested).
- A long-context difference of a few points. These are 50 and 100 questions with one sample
  each, and the judge is not hand-validated.

## Files

| Path | Contents |
|---|---|
| `results.json`, `tables.md` | the numbers (built by `ops/build_results.py` from `analysis/`) |
| `analysis/` | `results.json` and `tables.md` from `scripts/analyze_g3_accuracy.py analyze` (host CPU job 1547, git `6ae45397`), `posthoc.json` (`ops/posthoc_extras.py`), `SHA256SUMS.txt`, `workers.txt`, the judge input's SHA-256 |
| `data/per-request.jsonl.gz` | text-free per request (2,862 rows): ids, seed, lengths, finish reason, checker and string-match verdicts, containment, digests of the completion, answer and reply, first differing token against fp32 |
| `pilot/` | `pilot.json` (sizing), the pilot's text-free per-request file |
| `jobs/<id>-<kind>/` | lane receipts (`job.env`, `termination.env`, `manifest.json`, `command.json`, model and provenance verification, GPU prolog, container doctor, compressed container log, `scontrol.txt`). Under `g3/` and `g3judge/`: driver and worker summaries, engine records, progress logs, per-request `records.json` (text-free), phase stats, judge `labels.json`, and `raw-sha256.txt` for the outputs kept on the host |
| `manifests/`, `builds/`, `selftests/`, `probe/`, `source-check/` | every GPU job's manifest with its checks; build receipts and source capsules; CPU selftests; the LongMemEval-S length probe; the vLLM scheduler source lines |
| `ops/` | `jobs.log`, `preflight.log`, build, selftest, submit, manifest, analysis, staging, sizing and budget-guard scripts |

These stay on the host under `~/cotcodec-runs/stage0/g3-state-precision-accuracy/`, with SHA-256
in `jobs/*/g3*/raw-sha256.txt` and `analysis/judge-input-sha256.txt`:
- every completion (`texts.jsonl.gz`) and its token ids (`tokens.npz`);
- the judge input and the judge's replies.

Code: `experiments/g3/g3-state-precision-accuracy-v1.yaml`, `experiments/g3/math500-l5-134.jsonl`,
`harness/g3_state_precision.py`, `scripts/run_g3_accuracy.py`, `scripts/analyze_g3_accuracy.py`,
and `tests/test_g3_state_precision.py` (42 tests: config and plans, paired seeds, 32 checker
cases, the long-context order and prompt, judge items, and an end-to-end score-and-analyze run
that recovers injected differences).

### Reproduce

From the committed per-request file alone (CPU, no texts needed), the math and containment
tables, the cap and seed tables, and the token-agreement table:

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

The judge rows need the host-only judge input. The full analysis, on the host, is
`ops/analysis-cpu.sbatch` with `G3_MODE=analyze` (`ops/jobs.log`, job 1547).
