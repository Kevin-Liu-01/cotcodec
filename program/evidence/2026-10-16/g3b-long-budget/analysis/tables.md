# g3b-long-budget-v1 tables (EXPLORATORY)

Qwen3.5-4B, 51 MATH-500 level-5 questions (those with a capped rollout in G3) x seeds 42-44. Percent of rollouts; differences in points (arm minus fp32, same question and request seed), with 95% question-cluster bootstrap intervals (10000 draws, seed 42).

## Accuracy

| Budget and treatment of time-cut rollouts | Pairs | fp32 | bf16 | bf16 - fp32 |
|---|---:|---:|---:|---|
| accuracy at 81,920, as run (a time-cut rollout counts as unsolved) | 153 | 92.2 | 70.6 | -21.6 [-30.1, -13.7] |
| accuracy at 81,920, pairs with no time-cut rollout | 140 | 92.5 | 75.5 | -17.0 [-25.8, -8.8] |
| accuracy at 81,920, time-cut rollouts counted as solved (bound) | 153 | 92.2 | 79.1 | -13.1 [-20.3, -6.5] |
| accuracy rescored at 32,768, pairs with a known outcome | 147 | 67.0 | 23.5 | -43.5 [-54.6, -32.4] |
| accuracy rescored at 32,768, unknown counted unsolved | 153 | 67.3 | 23.5 | -43.8 [-54.9, -32.7] |
| accuracy rescored at 32,768, unknown counted solved | 153 | 67.3 | 27.5 | -39.9 [-51.0, -28.8] |

## G3 on the same questions (32,768 cap, heavy preemption; selected on these outcomes)

| Run | fp32 | fp16 | bf16 | bf16 - fp32 |
|---|---:|---:|---:|---|
| G3 | 66.7 | 56.2 | 37.9 | -28.8 [-37.3, -19.6] |

## G3b minus G3, per question (same questions and request seeds)

| Measure | fp32 | bf16 | bf16 gap (G3b) minus bf16 gap (G3) |
|---|---|---|---|
| accuracy, G3b rescored at 32,768 | +0.3 [-7.5, +8.5] | -14.4 [-22.9, -6.5] | -14.7 [-25.8, -4.2] |
| accuracy, G3b at 81,920 | +25.8 [+17.0, +35.6] | +37.6 [+28.8, +46.7] | +11.8 [-1.0, +24.2] |
| past 32,768 tokens | -1.0 [-9.2, +6.9] | +16.3 [+7.8, +24.9] | +17.3 [+6.9, +28.1] |

## Lengths and truncation

| Measure | fp32 | bf16 | bf16 - fp32 |
|---|---:|---:|---|
| length (tokens), complete pairs, 140 pairs | 29593 | 51988 | +22395 [+18859, +25981] |
| reached 81,920 (%), 140 pairs | 2.3 | 23.2 | +20.9 [+12.1, +30.4] |
| past 32,768 (%), 147 pairs | 30.4 | 76.5 | +46.1 [+35.3, +57.2] |
| final answer given at 81,920 (%), 140 pairs | 97.1 | 77.5 | -19.6 [-29.1, -10.8] |
| final answer given within 32,768 (%), 147 pairs | 69.0 | 23.5 | -45.4 [-56.9, -34.0] |
| cut by the time budget (%), 153 pairs | 0.0 | 8.5 | +8.5 [+4.6, +12.4] |

## Rollouts by arm

| Arm | Rollouts | Ended (EOS) | Accuracy among EOS | Wrong answer given | No answer | Reached 81,920 | Time cut | Median | p90 | Max | Past 32,768: ended / correct |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| fp32 | 153 | 149 | 94.6 | 7 | 5 | 4 | 0 | 26652 | 47712 | 81920 | 42 / 38 of 46 |
| bf16 | 153 | 109 | 98.2 | 2 | 43 | 31 | 13 | 46258 | 81920 | 81920 | 73 / 72 of 111 |

## Accuracy by output cap (correct and ended within L tokens; descriptive)

| Cap L | fp32 | bf16 | bf16 - fp32 |
|---:|---:|---:|---|
| 16,384 | 7.8 | 2.6 | -5.2 [-10.5, -0.7] |
| 32,768 | 67.0 | 23.5 | -43.5 [-54.6, -32.4] |
| 49,152 | 86.6 | 51.3 | -35.3 [-46.4, -24.5] |
| 65,536 | 91.2 | 63.4 | -27.8 [-38.6, -17.6] |
| 81,920 | 92.5 | 75.5 | -17.0 [-25.8, -8.8] |

## Seed order (seed 42 submitted and admitted first; descriptive)

| Budget | Seed | fp32 | bf16 | bf16 - fp32 | G3: fp32 | G3: bf16 | G3: bf16 - fp32 |
|---|---:|---:|---:|---|---:|---:|---|
| 81,920 (complete pairs) | 42 | 88.2 | 70.6 | -17.6 [-29.4, -5.9] | 68.6 | 17.6 | -51.0 [-64.7, -37.3] |
| 81,920 (complete pairs) | 43 | 94.1 | 72.5 | -21.6 [-33.3, -11.8] | 64.7 | 45.1 | -19.6 [-35.3, -3.9] |
| 81,920 (complete pairs) | 44 | 97.4 | 92.1 | -5.3 [-13.2, +0.0] | 66.7 | 51.0 | -15.7 [-29.4, -2.0] |
| 32,768 | 42 | 62.7 | 23.5 | -39.2 [-54.9, -23.5] | 68.6 | 17.6 | -51.0 [-64.7, -37.3] |
| 32,768 | 43 | 74.5 | 21.6 | -52.9 [-66.7, -39.2] | 64.7 | 45.1 | -19.6 [-35.3, -3.9] |
| 32,768 | 44 | 64.4 | 28.9 | -35.6 [-48.9, -22.2] | 66.7 | 51.0 | -15.7 [-29.4, -2.0] |

Seed-order contrast: (bf16 - fp32 at seed 42) minus its mean at seeds 43-44, paired by question.

| Run | Budget | Contrast [95%] |
|---|---|---|
| G3b | 81,920 (complete pairs) | -1.3 [-11.8, +9.2] (38 questions) |
| G3b | 32,768 | +5.6 [-10.0, +22.2] (45 questions) |
| G3 | 32,768 | -33.3 [-51.0, -15.7] (51 questions) |

## Engines (one per arm; single runs)

| Arm | Requests | Wall (s) | Output tokens | Output tok/s | Mean running | Peak running | Preemptions | Peak KV | Blocks x size | Fit (max sequences at max_model_len) | Time-cut | Solved (as run) | Solved per 1,000 s | Tokens per solved | Tokens per solved at 32,768 | Wall-clock figures |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---:|---:|---:|---:|---:|---|
| fp32 | 153 | 2338 | 4,597,287 | 1966 | 20.5 | 23 | 0 | 30% | 3821 x 528 | 23 >= 23 | 0 | 141 | 60.3 | 32,605 | 38,284 | clean |
| bf16 | 153 | 4556 | 7,700,200 | 1690 | 22.7 | 23 | 0 | 60% | 7418 x 272 | 24 >= 23 | 13 | 108 | 23.7 | 71,298 | 129,307 | affected: host load average about 17,600 from another project's CPU-only run outside Slurm, 04:05-04:08 UTC (killed 04:08; load 13,729 and falling at 04:08:15) |

## Rollouts cut by the job's time budget (outcome unknown at 81,920)

| Arm | Request | Tokens at the cut |
|---|---|---:|
| bf16 | m/q068/s44 | 79,888 |
| bf16 | m/q078/s44 | 64,720 |
| bf16 | m/q084/s44 | 54,136 |
| bf16 | m/q086/s44 | 52,849 |
| bf16 | m/q088/s44 | 47,774 |
| bf16 | m/q089/s44 | 43,009 |
| bf16 | m/q103/s44 | 34,965 |
| bf16 | m/q106/s44 | 32,067 |
| bf16 | m/q115/s44 | 30,001 |
| bf16 | m/q122/s44 | 23,768 |
| bf16 | m/q124/s44 | 23,557 |
| bf16 | m/q130/s44 | 21,981 |
| bf16 | m/q131/s44 | 19,415 |

## Token-level agreement with the fp32 arm (same request id and seed)

| Arm | Pairs | Identical | First difference, median (p10, p90) |
|---|---:|---:|---|
| bf16 | 153 | 0 | 188 (62, 528) |
