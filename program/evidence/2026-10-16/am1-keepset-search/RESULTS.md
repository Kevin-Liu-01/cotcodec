# am1-keepset-search-v1: results

**CONFIRMATORY, VERIFIED. Frozen registration `am1-keepset-search-v1`.**
- Ledger row 24; file SHA-256 `37256cc8...`.
- Fill commit `4b89e8eb`; freeze commit `72d50162`, which adds only the row.
- The registered run used a `git archive` export of `72d50162` (tar SHA-256 `5b545142...`).
- It ran on the host CPU from 09:10:20 to 09:11:31 UTC on 2026-10-15, after the freeze (ledger
  `frozen_at` 09:09:26).
- It ran section 16's three commands unchanged (`ops/run.sh`), all exiting 0.
- No GPU was used and no new model call was made.

**Disclosures that apply to every number here (registration section 1):**

- **The tables are not new.** They are AM1's 694 held-out tables (job 1458).
  - AM1 had already published some of their figures: the B = 4 regrets of leave-one-out,
    permutation Shapley-16, SNIPW-64, retrieval rank, raw attention, and exact Shapley and
    Banzhaf; the full-pool rate; and the census.
  - AM1b and AM1d, run on the development split, shaped these hypotheses (D113, D115).
- **H-B's direction was known before the run.** AM1's figures put BM25 top 4 at least 17
  questions behind all 8, so H-B is a description and decides nothing (D116).
- **No gauntlet score (D115).**
- **H-A reads oracle (judged) utilities, which need the reference answer.** H-C reads no label.
- **Same reader and judges as AM1.** The reader is Qwen3-8B, eager, batch-invariant, replayed bit
  for bit in AM1's G1. The primary judge is Qwen3-32B.
  - H-C's c ≈ 0 rests on this judge, which marked "I don't know." wrong on 347 of 347 validation
    items.
  - The second judge (Qwen3-8B) called it correct on 49 of 347.
- **Error rates are nominal.** H-A's per-direction rates are nominal. Their measured size under
  skewed differences is 0.0025-0.0185 per comparison, and 0.0385 for a false RULE_BEATS_SEARCH
  (section 9). Every measured verdict error is below 0.05.
- **Deviations:** none. The commands, seeds, inputs and code are as registered, and every
  section 16 pin matched.

## Outcome

**H-A (primary, search against credit at equal or fewer calls, oracle utility): INCONCLUSIVE.**
- Six of seven comparisons are SEARCH_BETTER.
- Greedy backward elimination (A7) is NOT_SEPARATED: its one-sided 99.29% upper bound is +0.0014.
- SEARCH_DOMINATES needed all seven.

**H-C (label-free, deployable): NONABSTAIN_HELPS.**
- The rule keeps the best-BM25-ranked 4-subset whose reply does not abstain, and falls back to
  BM25 top 4 when every 4-subset abstains.
- Accuracy is **0.571 against 0.458** for BM25 top 4 on the 347 held-out questions (retrieved
  arm). That is +0.112, bootstrap 95% [+0.081, +0.147].
- 39 questions gained and **0 lost**: exact McNemar p = 3.6e-12.
- It needs one reader call for the median question.

**H-B (descriptive, D116): BM25 top 4 is 0.066 behind all 8** on the retrieved arm (15 against
38, p = 0.0022). The development lead reversed, as AM1's figures implied.

## H-A, retrieved arm (251 non-constant tables, keep 4 of 8)

The difference is direct search's regret minus the rule's; negative means search loses less.
Decision bounds are one-sided at 1 - 0.05/7.

| Id | Comparison | Rule calls | Difference | 95% CI | Bounds (lower, upper) | Class |
|---|---|---:|---:|---|---|---|
| A1 | leave-one-out vs direct search, both 9 calls | 9 | -0.151 | [-0.180, -0.124] | -0.187, -0.117 | SEARCH_BETTER |
| A2 | SNIPW-64 vs direct search at the same calls | 56.7 | -0.078 | [-0.098, -0.059] | -0.104, -0.055 | SEARCH_BETTER |
| A3 | SNIPW-64 vs direct search at 26 calls | 56.7 | -0.049 | [-0.062, -0.036] | -0.066, -0.034 | SEARCH_BETTER |
| A4 | MSR-Banzhaf-64 vs direct search, both 64 calls | 64 | -0.076 | [-0.097, -0.056] | -0.102, -0.051 | SEARCH_BETTER |
| A5 | MSR-Banzhaf-64 vs direct search at 26 calls | 64 | -0.042 | [-0.055, -0.030] | -0.059, -0.027 | SEARCH_BETTER |
| A6 | permutation Shapley-16 vs direct search at 26 calls | 83.3 | -0.096 | [-0.119, -0.073] | -0.125, -0.068 | SEARCH_BETTER |
| A7 | greedy backward (BM25 ties) vs direct search, both 26 calls | 26 | -0.032 | [-0.062, -0.005] | -0.069, +0.001 | NOT_SEPARATED |

Regrets:
- Leave-one-out loses 0.277, SNIPW-64 0.085, MSR-Banzhaf-64 0.078, permutation Shapley-16 0.132
  and greedy backward 0.068. Sampled rules are averaged over 200 seeds, with Monte Carlo standard
  error at most 0.0010.
- Direct search's exact regret by calls is 0.141 at 8, 0.126 at 9, 0.067 at 16, 0.036 at 26,
  0.020 at 38, 0.003 at 64 and 0 at 70.

A7 is a real NOT_SEPARATED, not a near miss to be argued away:
- Its two-sided 95% interval excludes 0, but the registered one-sided bound does not.
- Under 200 other bootstrap seeds the verifier found the upper bound stays positive, between
  +0.0005 and +0.0032.
- The differences are skewed: greedy loses a whole answer on 17 of 251 tables.

The gold arm (288 tables) is descriptive. It shows the same pattern: A1-A6 SEARCH_BETTER, A7 not
separated, and a descriptive label of INCONCLUSIVE (`analysis/tables.md`).

## H-C and H-B, accuracy over all 347 questions

| Comparison | Arm | Rule | Base | b (rule right, base wrong) | c | Difference | 95% bootstrap | Exact p |
|---|---|---:|---:|---:|---:|---:|---|---:|
| **H-C: nonabstain-BM25 minus BM25 top 4** | retrieved | 0.571 | 0.458 | 39 | 0 | **+0.112** | [+0.081, +0.147] | 3.6e-12 |
| H-C (descriptive) | gold | 0.663 | 0.573 | 31 | 0 | +0.089 | [+0.061, +0.121] | 9.3e-10 |
| H-B (descriptive): BM25 top 4 minus all 8 | retrieved | 0.458 | 0.524 | 15 | 38 | -0.066 | [-0.107, -0.026] | 0.0022 |
| H-B (descriptive) | gold | 0.573 | 0.579 | 27 | 29 | -0.006 | [-0.049, +0.037] | 0.89 |
| Nonabstain-BM25 minus all 8 (descriptive) | retrieved | 0.571 | 0.524 | 33 | 17 | +0.046 | [+0.006, +0.086] | 0.033 |
| Nonabstain-BM25 minus all 8 (descriptive) | gold | 0.663 | 0.579 | 49 | 20 | +0.084 | [+0.037, +0.130] | 0.0006 |

H-C's exact conditional interval is [+0.092, +0.112]. Its upper end equals the estimate because
all 39 discordant pairs favour the rule. The bootstrap interval describes the uncertainty better.

**Why H-C works.**
- 56% of the reader's 4-subset replies on the retrieved arm abstain: 13,598 of 24,290.
- On the retrieved arm, BM25 top 4's own reply abstains on 116 questions. On 71 of them another
  4-subset answers, and switching to it gained 39 and lost none.
- In 45 pools every 4-subset abstains, and the rule keeps BM25 top 4.
- Abstaining replies are almost never judged correct by the primary judge.

**Cost (the BM25-ordered stop rule).**
- The stop rule reads 4-subsets in BM25 order and stops at the first that does not abstain.
- Over all 347 retrieved questions, the median is 1 read, the mean 11.24 and the 90th percentile
  70. 231 questions stop at one read and 288 within 8.
- The mean is dominated by the 45 all-abstaining pools, which read all 70 (3,150 of 3,901 reads).
- The registration reports capped variants only per table. The verifier aggregated them (post
  hoc; licenses nothing):

  | Cap | Accuracy | Mean reads |
  |---|---|---|
  | 8 | 0.548 | 2.68 |
  | 16 | 0.553 | 3.98 |
  | 26 | 0.571 | 5.45 |
  | 70 | 0.571 | 11.24 |

**By question type (retrieved, descriptive).**

| Type | BM25 top 4 | nonabstain-BM25 | All 8 |
|---|---|---|---|
| knowledge-update | 0.746 | 0.831 | 0.712 |
| multi-session | 0.297 | 0.426 | 0.426 |
| temporal-reasoning | 0.349 | 0.434 | 0.425 |
| single-session-user | 0.827 | 0.962 | 0.904 |
| single-session-preference | 0.120 | 0.320 | 0.160 |

The oracle ceiling, the best 4-subset, is 0.706 over all 347 questions. Full tables are in
`analysis/tables.md`.

## Validity checks (section 8)

All of them passed.
- **Pins.** The held-out tables match their pin (`841e7945...`). All 12 pinned host files had
  their digests at the fill commit and again at verification. All 17 code pins matched.
- **Join.** The join reproduced `values_hex` on 694 of 694 tables and `distinct_replies` on 694 of
  694. AM1's join and AM1d's join agreed on all 190,156 requests, and all 10,230 judge items were
  used.
- **Features.** SHA-256 `8d4753f9...`. They stay on the host
  (`~/cotcodec-runs/stage0/am1-keepset-search-v1/private/`) and hold no text. The extract log is
  `logs/extract.log`.
- **Tests.** The registered pytest passed: 52 passed.

## Verification

A fresh verifier made a new export of `72d50162` on the host and reran `extract` and `analyze`
on the platform of record.
- The features digest was identical, and `results.json`, `per-table.json.gz` and `tables.md`
  were byte-identical.
- It also confirmed the process:
  - the ledger chain (24 rows) and the row's file digest;
  - that the freeze commit adds only the row;
  - the export tar's digest;
  - the timeline: no held-out output predates the freeze.
- Its own code, which imports no `scripts/` module, recomputed every headline number exactly. It
  recomputed the abstention flags from the reader's texts on the host, with an independent join,
  and they agree on 347 of 347 questions in both arms.
- It found no blocking or major problem. Its minor points are applied here: the capped stop-rule
  aggregates are labelled post hoc, nonabstain-BM25 against all 8 is labelled descriptive, A7 is
  worded as above, and H-C's exact interval carries its caveat.

## What the result licenses

The scope covers:
- the Qwen3-8B reader with AM1's prompt (greedy, 64 tokens);
- the Qwen3-32B judge;
- held-out LongMemEval-S (cleaned), with BM25 top-8 user-turn pools;
- keeping 4 of 8.

1. **H-C, NONABSTAIN_HELPS.** Keeping the best-BM25-ranked 4-subset whose reply does not abstain
   is more accurate than keeping BM25 top 4: +0.112 [+0.081, +0.147], 39 gained, 0 lost. The rule
   reads no label, and its cost is the stop rule's reads (median 1).
2. **H-A, comparisons A1-A6 (SEARCH_BETTER).** Given an oracle utility, direct search over random
   4-subsets loses less than the sampled credit rules, in expectation over held-out questions
   with a non-constant retrieved table:
   - against leave-one-out at 9 calls;
   - against SNIPW-64 and MSR-Banzhaf-64 at equal calls;
   - against SNIPW-64, MSR-Banzhaf-64 and permutation Shapley-16 even when search reads 26
     subsets to their 57-83.

## What it does not license

- **SEARCH_DOMINATES.** It does not license that verdict, or any statement about greedy backward
  elimination against search in either direction.
- **That nonabstain-BM25 beats keeping all 8.** That comparison is a description: +0.046,
  p = 0.033, unregistered as a test.
- **Anything under the second judge**, which calls abstentions correct more often.
- **Why abstention tracks correctness.**
- **Other readers, prompts, retrievers, pool sizes, budgets or memory units.**
- **A deployable search for H-A**, which reads labels; anything under a noisy utility; anything
  about token cost per call.
- **Anything from the gold arm or the question types**, which are descriptive.

## Files

- `analysis/`: the registered outputs, text-free.
  - `results.json`, `per-table.json.gz` (ids, types, masks, utilities, regrets, choices, reads)
    and `tables.md`.
- `logs/`: logs of `extract`, `analyze` and `pytest`, with their exit codes, the start and end
  times, and the outputs' SHA-256. `$HOME` is written as `~`.
- `ops/run.sh`: the script that ran section 16's commands once.
- The development selftest and power analysis are in
  `program/evidence/2026-10-16/am1-keepset-search-dev-selftest/`.
