# g3b-long-budget-v1: does the bf16 GDN-state accuracy loss on Qwen3.5-4B survive the model card's 81,920-token budget, with no preemption?

> **EXPLORATORY. Not a registered experiment.** There is no preregistration, no hypothesis test
> and no decision rule. Every number below describes one engine run per arm of Qwen3.5-4B on 51
> MATH-500 level-5 questions x 3 seeds, on one node and one software stack (vLLM 0.31.0, Triton
> GDN decode path). The GPU jobs ran 2026-10-16 02:30-04:15 UTC. **2.2369 physical GPU-h**
> (8,053 GPU-s) of the 2.5 cap were used, image builds and the pilot included.
>
> **Revision of 2026-10-16 (CPU only, no new GPU job).** An independent check reproduced every
> number and the analysis byte for byte. This revision applies its wording fixes: the 81,920
> takeaway against the check's 15-point bar, seeds 42-43 as the cleanest 81,920 number, bounds for
> the unknown pairs, the seed contrast on matching questions and what it can separate,
> non-causal wording for the comparison with G3, both of the check's predictions, the cap
> arithmetic and the tokens-per-solved caveat. The new figures are in
> `analysis/posthoc-check.json`.
>
> **The 51 questions were selected on G3's own outcomes:** each had at least one rollout that
> reached G3's 32,768-token cap. G3's numbers on these questions are biased by that selection,
> and the gap rescored at 32,768 here is not an unbiased estimate of G3's 134-question gap.

Follows G3 (D124, `program/evidence/2026-10-16/g3-state-precision-accuracy/`). G3 found that a
bfloat16 GDN recurrent state (`--mamba-ssm-cache-dtype bfloat16`, rounded to nearest at every
decode step) lowers Qwen3.5-4B's MATH-500 level-5 accuracy by 10.7 points at a 32,768-token cap.
Nearly all of that loss was rollouts that reached the cap without an answer, and the bf16 gap
depended on submission order under heavy preemption. G3b asks two things:
1. Does the gap survive at 81,920 tokens, the model card's budget for competition math, or does
   bf16 only take longer to reach the same answers?
2. Does preemption or scheduling affect the gap?

## Main takeaways (exploratory)

- **(1) At 81,920 tokens the bf16 gap on these 51 questions shrinks from its 32,768 size but
  stays below 0 in every treatment. Whether it clears the bar G3's independent check set in
  advance for refuting "bf16 just takes longer" (a gap above about 15 points) depends on how the
  13 time-cut rollouts are counted, and no interval clears it.**

  | Budget | Pairs | fp32 | bf16 | bf16 - fp32 [95%] |
  |---|---:|---:|---:|---|
  | 81,920, seeds 42-43 only (no time-cut rollout) | 102 | 91.2 | 71.6 | -19.6 [-30.4, -9.8] |
  | 81,920, pairs with no time-cut rollout | 140 | 92.5 | 75.5 | -17.0 [-25.8, -8.8] |
  | 81,920, as run (13 time-cut bf16 rollouts count as unsolved) | 153 | 92.2 | 70.6 | -21.6 [-30.1, -13.7] |
  | 81,920, the 13 time-cut rollouts counted as solved (bound) | 153 | 92.2 | 79.1 | -13.1 [-20.3, -6.5] |
  | rescored at 32,768, pairs with a known outcome | 147 | 67.0 | 23.5 | -43.5 [-54.6, -32.4] |
  | G3 on the same 51 questions (32,768) | 153 | 66.7 | 37.9 | -28.8 [-37.3, -19.6] |

  Percent of rollouts correct (G3's checker v2). Differences are against fp32 on the same
  question and request seed, with 95% question-cluster bootstrap intervals (10,000 draws).
  - The bf16 job did not finish: 13 seed-44 rollouts were still running when its time budget
    ended (Deviations). How those 13 are treated moves the 81,920 gap between -13.1 and -21.6
    points. Every treatment's interval stays below 0.
  - Against the check's bar: as run (-21.6), with the cut pairs dropped (-17.0) and on seeds
    42-43 (-19.6), the point estimate is beyond 15 points. With the cut rollouts counted as solved
    (-13.1) it is not. Every interval includes -15.
  - Seeds 42-43 pooled is the cleanest single number at 81,920: -19.6 [-30.4, -9.8], 102 pairs,
    nothing missing (`analysis/posthoc-check.json`).
  - bf16 is still converging at the top of the budget. From 65,536 to 81,920 tokens its
    accuracy rises from 63.4 to 75.5 (+12.1 points), against +1.3 for fp32 (91.2 to 92.5). A
    budget above 81,920 could narrow the gap further; this run cannot say how far.
  - **The loss is still rollouts that do not finish, now at 81,920.**
    - On the 140 complete pairs, 23.2% of bf16 rollouts reach 81,920, against 2.3% of fp32
      (+20.9 [+12.1, +30.4]).
    - On the same pairs, 22.5% of bf16 rollouts give no final answer, against 2.9% of fp32.
    - Rollouts that end on their own are 98.2% correct with bf16 (109) and 94.6% with fp32 (149).
      Wrong final answers given number 2 (bf16) and 7 (fp32) of 153.
  - **bf16 reasons much longer.** Mean length on the complete pairs is 51,988 against 29,593
    tokens (+22,395 [+18,859, +25,981], +76%). The median over all 153 is 46,258 against 26,652.
  - Most long bf16 rollouts are not loops. The distinct 16-gram share of the last 8,192 tokens
    (G3's repetition measure) has a median of 0.984 for the 31 bf16 rollouts that reached 81,920.
    3 of the 31 are below 0.5, against 1 of 4 for fp32 (`analysis/posthoc-repetition.json`).
  - Of the rollouts still running at 32,768 tokens, 73 of 111 bf16 rollouts ended on their own
    by 81,920 (72 correct; 7 of the 111 were cut by the time budget), against 42 of 46 for fp32
    (38 correct). So the longer budget recovers many bf16 answers, but not all.
  - Accuracy rises with the cap in both arms (correct within L tokens): at 49,152 it is 86.6
    against 51.3, and at 65,536 91.2 against 63.4. The tables label this "ended within L"; the
    81,920 row also counts one bf16 rollout that reached 81,920 after giving a correct answer
    (`m/q049/s44`, thinking closed).
  - Tokens per solved problem, as run: 32,605 (fp32) against 71,298 (bf16), about 2.2x. The
    bf16 figure includes the partial tokens of the 13 time-cut rollouts.
- **(2) In a run with no preemption and 23 concurrent sequences (G3: 114-128), the bf16 gap
  rescored at 32,768 is larger than G3's on the same questions and shows no seed-order pattern
  (+5.6 [-10.0, +22.2]).**
  - fp32 rescored at 32,768 matches G3's fp32 on these questions: +0.3 [-7.5, +8.5] points
    (G3b minus G3, paired by question). bf16 is lower than in G3: -14.4 [-22.9, -6.5]. The gap
    is 14.7 [4.2, 25.8] points larger than G3's (with the 6 unknown pairs counted as unsolved,
    15.0 [4.6, 26.1]; counted as solved, 11.1 [0.0, 22.2]).
  - This level shift, bf16 down while fp32 is unchanged, is the evidence that separates the
    runs. The seed-order contrast is not (below).
  - The selection on G3's capped rollouts should, if anything, make a fresh run look better
    than G3 on these questions (regression to the mean), not worse.
  - By seed (seed 42 submitted and admitted first), rescored at 32,768:

    | Seed | G3b fp32 | G3b bf16 | G3b bf16 - fp32 | G3 fp32 | G3 bf16 | G3 bf16 - fp32 |
    |---:|---:|---:|---|---:|---:|---|
    | 42 | 62.7 | 23.5 | -39.2 [-54.9, -23.5] | 68.6 | 17.6 | -51.0 [-64.7, -37.3] |
    | 43 | 74.5 | 21.6 | -52.9 [-66.7, -39.2] | 64.7 | 45.1 | -19.6 [-35.3, -3.9] |
    | 44 | 64.4 | 28.9 | -35.6 [-48.9, -22.2] | 66.7 | 51.0 | -15.7 [-29.4, -2.0] |

    The seed-order contrast (the seed-42 gap minus its mean at seeds 43-44, paired by question)
    is +5.6 [-10.0, +22.2] in G3b on 45 questions; with the 6 unknown pairs counted as unsolved
    or solved it is +6.9 or +1.0 on all 51. G3's contrast is -33.3 [-51.0, -15.7] on 51
    questions and -32.2 [-51.1, -12.2] on the same 45, so G3b minus G3 is +37.8 [+10.0, +66.7]
    (`analysis/posthoc-check.json`). G3b's seed-44 row at 32,768 has 45 pairs: 6 time-cut
    rollouts stopped before 32,768 tokens.
  - What a null contrast can and cannot separate: in G3b nothing is preempted, so seed order
    sets only when a request is admitted. A null contrast is expected there whether G3's seed
    pattern came from preemption, from concurrency or by chance. It does not discriminate among
    them.
  - At 81,920, seeds 42 and 43 (no time cuts) give -17.6 [-29.4, -5.9] and -21.6 [-33.3, -11.8].
    Seed 44's 81,920 gap cannot be read: as run it is -25.5, and with the 13 time-cut rollouts
    counted as solved it is 0.0.
  - The level shift fits G3's preemption hypothesis. A preempted request restarts from
    prefill, which rebuilds its GDN state close to fp32 (G2b) and discards the rounding error
    accumulated over its decode steps. In G3 the last-submitted seeds were probably preempted
    most (they decoded at about half the per-request rate; per-request preemption was not
    recorded) and showed the smallest bf16 gap. In G3b nothing is preempted, and every seed's
    bf16 accuracy is near G3's seed 42 (the first submitted).
  - G3's independent check made two predictions before this run:
    - (a) if bf16 only lengthens the reasoning, the 81,920 gap shrinks toward the 0-1 point gap
      among finished rollouts. That is contradicted: every treatment gives -13 to -22 points.
    - (c) under the preemption hypothesis, a gap at 32,768 at least as large as G3's seed-42 gap
      (-51.0 on these questions). The point estimate, -43.5, falls short of -51.0, though its
      interval [-54.6, -32.4] includes it.
    - The check proposed seeds 42-43 only (102 requests per arm). This run used seeds 42-44, as
      specified, and the added seed 44 is what ran into the time limit.
  - It does not isolate preemption. G3b also changes the concurrency (23 running against G3's
    114-128) and the batch composition, and each arm is one engine run.
- **No preemption occurred.** vLLM's preemption counter stayed at 0 in both engines. At most 23
  sequences ran (peak KV use 30% for fp32, 60% for bf16), and 23 sequences of 82,944 tokens fit
  both block pools (23.7 and 24.1). Each worker checked the fit before submitting a request.
- **Reading (exploratory).** On these 51 hard questions, the model card's 81,920-token budget does
  not remove the cost of vLLM's stock bf16 GDN state on Qwen3.5-4B. bf16 rollouts run about 1.8x as
  long, about a fifth of them reach 81,920 without finishing (against 2-3% of fp32's), and
  accuracy is 13-22 points lower; bf16 was still gaining at the top of the budget. In this run
  with no preemption and 23 concurrent sequences (G3: 114-128), the 32,768-token gap on the same
  questions is about 1.5x the gap G3 measured under heavy preemption. That suggests G3's pooled
  -10.7 may understate the cost under such serving conditions, but this run cannot say why or by
  how much on the full 134 questions.

## Design as run

| Item | Setting |
|---|---|
| Model | Qwen3.5-4B `851bf6e8` (lane-verified receipt; checkpoint `mamba_ssm_dtype: float32`). |
| Arms | `mamba_ssm_cache_dtype` = `auto` (resolves to float32) and `bfloat16`, at vLLM's own block size (528 and 272 tokens). One engine per arm, side by side on separate H100s (GPUs 1 and 2), as in G3. |
| Questions | The 51 MATH-500 level-5 questions with at least one rollout that reached G3's 32,768-token cap, in any arm and seed of G3's 4B main run (`finish_reason` "length" in G3's committed `data/per-request.jsonl.gz`, checker v2, SHA-256 `683c6ceb...`). The list is pinned in `experiments/g3/g3b-long-budget-v1.yaml` with the SHA-256 of its indices (`af3837b9...`), and the tests rederive it from G3's file. |
| Requests | Seeds 42, 43, 44; request seed `100000 * seed + question index`, the same as G3's; 153 requests per engine, submitted at once in G3's order (seed, then question), FCFS admission. |
| Prompt and sampling | G3's math arm unchanged: G3's 134-question file (SHA-256 `04154d64...`), the suffix "Please reason step by step, and put your final answer within \boxed{}.", the Qwen3.5 chat template with thinking on, temperature 1.0, top-p 0.95, top-k 20, min-p 0, presence penalty 1.5, repetition penalty 1.0, stop at `<|im_end|>`. Only `max_tokens` changes: 81,920, the model card's setting for benchmarking on math and programming competitions (32,768 for most queries; Qwen/Qwen3.5-4B README at `851bf6e8`, "Best Practices", https://huggingface.co/Qwen/Qwen3.5-4B, read 2026-10-16). |
| Engine | G3's rollout engine (bf16 weights, `gpu_memory_utilization` 0.90, `max_num_batched_tokens` 8,192, prefix caching off, CUDA graphs on, engine seed 42, `logprobs_mode raw_logprobs`, stats on, ReplaySSM off, Triton GDN decode path), with `max_model_len` 82,944 (81,920 + 1,024; the longest of the 51 prompts is 857 tokens) and `max_num_seqs` 23. |
| No preemption | A running sequence of `max_model_len` tokens holds ceil(82,944 / block size) attention blocks plus one block in each of the 3 GDN groups. With the engines' pools (3,821 x 528 for fp32, 7,418 x 272 for bf16), 23 such sequences fit at once (23.7 and 24.1; vLLM's own `kv_cache_max_concurrency` agrees with the formula). Each worker checked this against its engine before submitting a request. vLLM's preemption counter (`vllm:num_preemptions`) was sampled every 0.5 s. |
| Scoring | G3's checker v2 (`harness.g3_state_precision.math_equiv`): the last `\boxed{}` after the last `</think>`; no closed thinking block means no answer. **At 81,920**: the full rollout. **Rescored at 32,768**: a rollout that ended within 32,768 tokens is scored as is. A longer one is scored on the decoding of its first 32,768 tokens (made by the worker, `text_at_32768`) and counts as having reached the cap. Sampling does not depend on `max_tokens`, so this is what a 32,768 cap would have given for the tokens this run sampled. A rollout cut by the time budget has no outcome at a cap it had not reached. |
| Analysis | `scripts/analyze_g3b_long_budget.py` on the host CPU (texts stay there). Per arm: per-question means over the seeds, averaged over the 51 questions. Paired differences against fp32 use a percentile bootstrap over questions (10,000 draws, seed 42), 95% intervals. A (question, seed) pair with no outcome in either arm is dropped from both arms. G3's numbers on the same 51 questions come from G3's committed per-request file, and the G3b-minus-G3 differences pair the two runs by question. |

**Statistics caveats.** The intervals resample questions within one engine run per arm. They
include no engine-instance or scheduling variance, and the partial A/A that would bound it was
not run (Deviations). There is no multiplicity adjustment across the many tables. Seeds were
submitted and admitted in order, so a seed-level figure belongs to this order. The complete-pair
figures at 81,920 drop 13 seed-44 pairs whose bf16 rollouts were long-running when cut, so they
lean toward a smaller gap; the as-run figures lean the other way.

### Sizing

The pilot (jobs 1562 and 1564, one per arm, 240 s of generation each on the main request list;
sizing only, not in the analysis; `pilot/pilot.json`):
- Block pools of 3,821 x 528 and 7,418 x 272 at `max_num_seqs` 23 (G3 had 3,733 and 7,248 at
  512), so 23 full-length sequences fit both.
- 23 running throughout, 0 preemptions, about 2,520 output tok/s at up to 0.5M context tokens.
  Step time was about 6 ms plus 12 ms per million context tokens.
- A no-preemption FCFS simulation with G3's lengths on these questions (`ops/size_main.py`)
  continued each capped rollout with G3's late-ending hazard, or with 0.6 of it. It put the
  generation at 2,500-3,200 s for fp32 and 3,500-4,600 s for bf16.
- The two main jobs got Slurm limits of 55 min (fp32) and 82 min (bf16). The cap held because
  each driver stops generating about 255 s before its Slurm limit and then saves and exits (the
  bf16 job ended 242 s before its limit). It does not follow from the Slurm limits alone: 844
  GPU-s before the main run plus 3,300 and 4,920 GPU-s of limits is 9,064 GPU-s, 2.518 GPU-h.
  The config comment and `pilot/pilot.json` say the cap holds "even if both are cut by time";
  that relied on the same early stop.
- fp32 took 2,338 s, a little faster than simulated. bf16 generated 7.70M tokens against the
  simulated 5.9-6.6M, and 31 of its 153 rollouts ran to 81,920. Its time budget ended at 4,556 s
  with 13 rollouts unfinished.

## What ran

Every GPU job used the docker-research lane through `scripts/submit_docker_research_job.py`
(dry-run and test-only, then submit; `manifests/`), with digest-pinned images built from this
branch by G3's route (retained source capsule, offline overlay build), Slurm GRES and time
limits, and lane receipts (`jobs/`). GPU-h are physical: GPUs times the Slurm `RunTime`, read with
`scontrol` at completion (`jobs/*/scontrol.txt`, `builds/scontrol-build-*.txt`, `ops/jobs.log`).

| Job | What | Image (commit) | Run time | GPU-h | Outcome |
|---|---|---|---:|---:|---|
| 1557 | vLLM overlay build | `78471b75` -> `e9950f79` | 00:01:14 | 0.0206 | PASS |
| 1558 | CPU: post-build selftest | `e9950f79` | <1 min | 0 | pass (prompt 857 + 81,920 <= 82,944; 23 fit both of G3's pools) |
| 1562, 1564 | pilot: fp32, bf16 (240 s each) | `e9950f79` | 00:05:32, 00:05:32 | 0.1844 | exit 3 by design (time budget); 14 and 4 of 153 finished; 0 preemptions |
| 1569 | vLLM overlay build (main phase declared) | `8ba1898a` -> `cd9170d5` | 00:01:46 | 0.0294 | PASS |
| 1570 | CPU: post-build selftest (pilot and main plans) | `cd9170d5` | <1 min | 0 | pass |
| 1574 | main: fp32 | `cd9170d5` | 00:40:58 | 0.6828 | COMPLETED 0:0; 153 of 153 in 2,338 s; 0 preemptions |
| 1576 | main: bf16 | `cd9170d5` | 01:17:58 | 1.2994 | FAILED 3:0 by design: 140 of 153 finished, 13 cut by the time budget at 4,556 s; 0 preemptions |
| 1577 | CPU: scoring check on the pilot workers | host checkout `8ba1898a` | <1 min | 0 | scoring runs on the real files |
| 1583 | vLLM overlay build (A/A phase declared) | `063273d1` -> `34f01e3a` | 00:01:13 | 0.0203 | PASS; the A/A did not run |
| 1584 | CPU: post-build selftest (pilot, main and A/A plans) | `34f01e3a` | <1 min | 0 | pass |
| 1599 | CPU: scoring and analysis | host checkout `b066babd` | ~1 min | 0 | `analysis/`, `data/` |
| 1600, 1601 | CPU: repetition measure (token ids only) | host checkout `b066babd` venv | <1 min | 0 | 1601 is the record (committed script) |
| | **Total** | | 8,053 GPU-s | **2.2369** | |

The ledger's three G3b rows (`program/state.json`) are 0.0703 (builds), 0.1844 (pilot) and
1.9822 (main), summing to 2.2369. GPU 0 held another project's job (`transcreate-lama`, 1451)
throughout and was not touched. Another workstream's CPU jobs (LM1 fetches) ran during the main
runs.

## Results

`tables.md` (identical to `analysis/tables.md`) holds every table:
- accuracy under each treatment of the time-cut rollouts;
- G3 on the same questions and the G3b-minus-G3 differences;
- lengths and truncation, rollouts by arm and accuracy by output cap;
- the seed-order breakdown and contrasts;
- the engines, the time-cut rollouts and token agreement.

`results.json` holds the same numbers with the GPU-h by job and the pilot record.

### G3b minus G3, paired by question (same 51 questions and request seeds)

| Measure | fp32 | bf16 | bf16 gap (G3b) minus bf16 gap (G3) |
|---|---|---|---|
| accuracy, G3b rescored at 32,768 | +0.3 [-7.5, +8.5] | -14.4 [-22.9, -6.5] | -14.7 [-25.8, -4.2] |
| accuracy, G3b at 81,920 (complete pairs) | +25.8 [+17.0, +35.6] | +37.6 [+28.8, +46.7] | +11.8 [-1.0, +24.2] |
| past 32,768 tokens | -1.0 [-9.2, +6.9] | +16.3 [+7.8, +24.9] | +17.3 [+6.9, +28.1] |

In G3, 31.4% (fp32) and 60.1% (bf16) of rollouts on these questions reached 32,768. In G3b,
30.4% and 76.5% ran past it.

### Lengths and truncation (paired against fp32)

| Measure | Pairs | fp32 | bf16 | bf16 - fp32 [95%] |
|---|---:|---:|---:|---|
| mean length (tokens) | 140 | 29,593 | 51,988 | +22,395 [+18,859, +25,981] |
| reached 81,920 | 140 | 2.3% | 23.2% | +20.9 [+12.1, +30.4] |
| ran past 32,768 | 147 | 30.4% | 76.5% | +46.1 [+35.3, +57.2] |
| final answer given at 81,920 | 140 | 97.1% | 77.5% | -19.6 [-29.1, -10.8] |
| final answer given within 32,768 | 147 | 69.0% | 23.5% | -45.4 [-56.9, -34.0] |
| cut by the time budget | 153 | 0.0% | 8.5% | +8.5 [+4.6, +12.4] |

| Arm | Rollouts | Ended (EOS) | Accuracy among EOS | Wrong answer given | No answer | Reached 81,920 | Time cut | Median | p90 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| fp32 | 153 | 149 | 94.6 | 7 | 5 | 4 | 0 | 26,652 | 47,712 |
| bf16 | 153 | 109 | 98.2 | 2 | 43 | 31 | 13 | 46,258 | 81,920 |

- 4 of the 31 bf16 rollouts that reached 81,920 had closed their thinking block (cut inside the
  answer); none of fp32's 4 had.
- First differing token against fp32 on the same request: median 188 (p10 62, p90 528). As in
  G3, that is batch nondeterminism; "paired by question and seed" pairs by question in effect.

### Engines and timing

| Arm | Wall (s) | Output tokens | Output tok/s | Mean running | Preemptions | Peak KV | Solved (as run) | Tokens per solved | Wall-clock figures |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| fp32 | 2,338 | 4,597,287 | 1,966 | 20.5 | 0 | 30% | 141 | 32,605 | clean |
| bf16 | 4,556 | 7,700,200 | 1,690 | 22.7 | 0 | 60% | 108 | 71,298 | affected (host load; time cut) |

- **Host-load window.** From about 04:05 to 04:08 UTC, another project's CPU-only run outside
  Slurm pushed the host's load average to about 17,600. It was killed at 04:08, and at 04:08:15
  the load was 13,729 and falling. The note in `ops/timing-windows.json`, which the analysis uses
  to flag affected engines, reads: "host load average about 17,600 from another project's
  CPU-only run outside Slurm, 04:05-04:08 UTC (killed 04:08; load 13,729 and falling at
  04:08:15)", for 04:05:00-04:08:15 UTC.
  - The bf16 job (generation 02:58:53-04:14:49 UTC) ran through the window. The fp32 job (ended
    03:37:58), the pilot and the builds did not.
  - The window cannot change accuracy, lengths, truncation at a cap or preemption counts.
  - It can distort wall-clock figures. In the window the bf16 engine decoded 1,537 tok/s
    against 1,691 in the 5 minutes before, about 18 s of generation lost
    (`analysis/posthoc-window.json`). Part of the decline is longer contexts, which also slowed
    the minutes after the window.
  - So bf16's wall time, tok/s and solved per engine-second are labelled affected. They are left
    out of every comparison between arms. They also differ in workload (longer contexts) and the
    bf16 run did not finish.
  - The lost seconds may have cost each of the 13 time-cut rollouts about 1,300 tokens (18 s at
    about 73 tok/s per sequence). That cannot change any outcome at 32,768 except the 6 already
    counted as unknown there.
- Tokens per solved problem do not depend on wall time. Rescored at 32,768 (tokens within the cap
  over problems solved within it), they are 38,284 (fp32) and 129,307 (bf16) (`tables.md`). The
  bf16 figure includes 150,789 partial tokens from the 6 rollouts with no outcome at 32,768. On
  the 147 known pairs it is 38,146 against 125,119 (`analysis/posthoc-check.json`).

## Deviations and problems

- **The bf16 arm was cut by its time budget.** 13 seed-44 rollouts, the last admitted, were still
  running at 4,556 s, with 19,415-79,888 tokens (`tables.md`).
  - bf16 rollouts held their slots longer, so seed 43 started later (median admission 1,840 s
    against 811 s for fp32) and seed 44 later still (3,458 s against 1,500 s).
  - At 81,920 their outcomes are unknown. The analysis reports them three ways (as run,
    complete pairs, counted as solved), and every interval for the gap stays below 0.
  - At 32,768, 7 of the 13 had passed 32,768 tokens and are scored there. 6 had not, and their
    pairs are dropped (147 pairs). Counting the 6 as solved or unsolved gives -39.9 and -43.8.
  - The sizing simulation's late-ending hazard was too low for bf16 at these lengths. The bf16
    job got 82 min, the most the cap allowed alongside the fp32 job and the pilot given the
    drivers' early stop (Sizing).
- **The host-load window** (Engines and timing).
- **The partial A/A was not run.** Its phase was declared in the config while the bf16 job was
  running (a second fp32 engine on the 51 seed-42 requests, 25-min limit). It was to run only if
  the cap left 25 min after the bf16 job. The bf16 job's 01:17:58 left 947 GPU-s, so the gate
  did not submit it (`ops/aa-gate.sh`, `ops/guard.log`). Its image build (1583, 0.0203 GPU-h)
  is counted.
- **Slurm limits.** The config comment for the main phase says 56 and 83 min. The jobs were
  submitted at 55 and 82 min, for margin under the cap.
- **Build 1557's RunTime was read by hand.** The first `capture-scontrol.sh` stopped after one
  query and missed the final record. `scontrol show job 1557`, run within a minute of the end,
  gave 00:01:14. The script was then made robust, and every later job's record was captured.
- **Transfers.** A full git bundle stalled on the host's network during the LM1 fetches. Later
  commits went over as incremental bundles. Every host checkout's `git archive` SHA-256 matched
  the Mac's (`ops/jobs.log`).
- **Manifest name.** The first A/A manifest name (`fp32_aa`) failed the submitter's slug check at
  dry-run. It was renamed `fp32aa`; no job was submitted with it.
- **Repetition post hoc.** Job 1600 ran an unformatted draft of `ops/posthoc_repetition.py`. Job
  1601 reran the committed script (its log prints SHA-256 `b8bfae89...`, the committed file's)
  and is the record.
- **Exit codes.** The pilot jobs and the bf16 main job end FAILED 3:0 by design: the driver exits
  3 when a request did not finish. The fp32 job completed 0:0.
- **No fresh-job resume test (AGENTS.md hard rule 2).** As in G3, these short exploratory jobs
  have none. A rerun is a new job.

## What it does not show

- Anything confirmatory. One engine run per arm, one node, one vLLM build, one submission order,
  no preregistration and no decision rule. The partial A/A was not run, so run-to-run variation
  at this budget is not bounded here. G3's pilot gave a rough fp32 A/A of a few points on 96
  requests at 32,768.
- An unbiased estimate of G3's population gap. The 51 questions were selected on G3's own
  outcomes (a capped rollout in any arm and seed). G3's numbers on them are biased by that
  selection, most at bf16 seed 42, where most of the capped rollouts were.
  - G3b is a fresh run on a fixed set, but the set is the hard tail of the 134.
  - Neither G3b gap can be scaled to the 134 questions without the other 83. Those had no capped
    rollout in G3 and were not rerun.
- That preemption causes G3's seed pattern. G3b removes preemption, but it also changes the
  concurrency (23 running against G3's 114-128) and the batch composition. A difference between
  the runs is not attributable to preemption alone.
- The 81,920 gap at seed 44, or a seed-order contrast at 81,920 that includes it. The 13
  time-cut pairs are all at seed 44.
- Budgets above 81,920. bf16 was still gaining about 12 points per 16K tokens at the top of the
  curve (fp32 about 1), so a larger budget could narrow the gap further.
- Other budgets between 32,768 and 81,920 as separate runs (the by-cap table rescores this run),
  other rounding (stochastic rounding, ReplaySSM's separate precisions), fp16, the 9B or other
  models, other kernels, prefix caching or other engines.
- Throughput or cost at scale. The engines ran 23 sequences at a time to rule out preemption, and
  the bf16 wall-clock figures are affected by the host-load window and the time cut.

## Files

| Path | Contents |
|---|---|
| `results.json`, `tables.md` | the numbers (`ops/build_results.py` from `analysis/`, the job records and `pilot/pilot.json`) |
| `analysis/` | `results.json` and `tables.md` from `scripts/analyze_g3b_long_budget.py analyze` (host CPU job 1599, git `b066babd`), `SHA256SUMS.txt`, `workers.txt`; `posthoc-window.json` (`ops/posthoc_window.py`, Mac), `posthoc-repetition.json` (`ops/posthoc_repetition.py`, host job 1601) and `posthoc-check.json` (`ops/posthoc_check.py`, Mac, from the committed files: the independent check's figures) |
| `data/per-request.jsonl.gz` | text-free per request (306 rows): ids, seed, lengths, finish reason, admission and finish times, checker-v2 verdicts at 81,920 and rescored at 32,768, the completion's SHA-256, first differing token against fp32 |
| `pilot/pilot.json` | the pilot's engines, fit, step-time fit and the sizing simulation |
| `jobs/<id>-<kind>/` | lane receipts (`job.env`, `termination.env`, `manifest.json`, `command.json`, model and provenance verification, GPU prolog, container doctor, compressed container log, `scontrol.txt`). Under `g3b/`: driver and worker summaries, engine records with the fit check, progress logs, per-request `records.json` (text-free), phase stats, and `raw-sha256.txt` for the outputs kept on the host |
| `manifests/`, `builds/`, `selftests/` | every GPU job's manifest with its checks; build receipts and source capsules; CPU selftests and plans |
| `ops/` | `jobs.log`, `preflight.log`, `guard.log`, the timing window, and the checkout, build, selftest, submit, manifest, sizing, A/A-gate, scontrol-capture, staging, analysis and post hoc scripts |

The committed ops scripts, manifests and lane receipts keep the host's absolute run paths
(`/home/kevin/cotcodec-runs/...`), as G3's merged evidence does; the records are not rewritten.

Every completion (`texts.jsonl.gz`, with `text_at_32768` for rollouts past 32,768 tokens) and its
token ids (`tokens.npz`) stay on the host under `~/cotcodec-runs/stage0/g3b-long-budget/`, with
SHA-256 in `jobs/*/g3b/raw-sha256.txt`.

Code: `experiments/g3/g3b-long-budget-v1.yaml`, `harness/g3b_long_budget.py`,
`scripts/run_g3b_long_budget.py`, `scripts/analyze_g3b_long_budget.py` and
`tests/test_g3b_long_budget.py`. G3's prompts, checker, sampling, engine loop and analysis
statistics are imported unchanged. The tests cover:
- the pinned questions and their derivation from G3's committed data;
- plans, and requests and seeds identical to G3's;
- engine and sampling settings equal to G3's except the budget;
- the fit check against G3's recorded block pools and vLLM's own concurrency figure;
- scoring at a shorter cap, including time-cut rollouts;
- score and analyze end to end, recovering injected differences, the time-cut treatments and
  the timing flag.

### Reproduce

From the committed files alone (CPU, no texts needed), `analysis/results.json` and
`analysis/tables.md` are reproduced byte for byte:

```bash
uv run --locked python - <<'EOF'
import importlib.util, json, pathlib
spec = importlib.util.spec_from_file_location("a", "scripts/analyze_g3b_long_budget.py")
a = importlib.util.module_from_spec(spec); spec.loader.exec_module(a)
from harness import g3b_long_budget as g3b
E = pathlib.Path("program/evidence/2026-10-16/g3b-long-budget")
G3 = pathlib.Path("program/evidence/2026-10-16/g3-state-precision-accuracy/data/per-request.jsonl.gz")
res = a.analyze(a.a3.read_jsonl_gz(E / "data/per-request.jsonl.gz"),
                a.worker_summaries([E / "jobs/1574-main/g3b", E / "jobs/1576-main/g3b"]),
                g3b.read_g3_rows(G3), 10000, 42,
                timing_windows=json.loads((E / "ops/timing-windows.json").read_text()))
assert a.tables_md(res) == (E / "analysis/tables.md").read_text()
assert json.dumps(res, indent=2, sort_keys=True) + "\n" == (E / "analysis/results.json").read_text()
print("reproduced")
EOF
```

Scoring (`score`) needs the host-only texts: `ops/analysis-cpu.sbatch` with `G3B_RUNS` set to the
two main run directories and `G3B_TIMING_WINDOWS=ops/timing-windows.json` (`ops/jobs.log`, job
1599).
