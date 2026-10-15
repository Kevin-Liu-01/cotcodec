# AM4: a read cap on the non-abstention stop rule (EXPLORATORY, POST HOC)

**POST HOC AND EXPLORATORY. AM4 licenses nothing.**
- **Same questions.** Every number here comes from the held-out and abstention questions on which
  `am3-nonabstain-generality-v1` confirmed the rule (D119).
- **K seen after the data.** The cap K is examined after those results were known.
- **No K is chosen.** The whole curve is reported, and no K is picked as a finding. A K chosen from
  this curve would be optimistic, and it would need confirmation on new questions (another
  dataset, or LongMemEval-M; D119).
- **No new model call.** AM4 is CPU only and recomputes the registered run's features.

## The question

The registered rule reads a pool's 70 4-subsets in BM25 order and keeps the first whose reply does
not abstain. When none answers, it keeps BM25 top 4.
- **Answerable questions.** It stops after a median of 1 read.
- **Unanswerable questions.** It reads a median of 70 subsets. There it turns correct abstentions
  into wrong answers.

With a read cap K, the rule reads at most the first K 4-subsets. When none of them answers, it keeps
BM25 top 4, which is always read first, so falling back costs no extra read.
- K = 1 is BM25 top 4 itself. K = 70 is the registered rule.
- For each pool the capped choice is either the registered rule's choice or BM25 top 4.
- Lowering K can only remove switches away from BM25 top 4, never add one.

This README answers four questions, for K = 1, 2, 4, 8, 16, 26 and 70 and all three readers:
- **(a)** the gain b, c on the 347 held-out answerable questions;
- **(b)** the cost b2 on the 30 unanswerable questions;
- **(c)** the mean reads on each population;
- **(d)** the net rate at LongMemEval-S's mix (470 answerable to 30 unanswerable) and the
  break-even unanswerable share.

The main results use the retrieved arm and the Qwen3-32B judge. `tables.md` also gives:
- the second judge (Qwen3-8B);
- the gold arm on the answerable questions;
- the blind hand labels where they cover the changed cells;
- the read distributions.

## How it was computed

- **Registered code, reused unchanged.** `scripts/memcredit_am4.py` changes only the cap.
  - Reading order and stop rule: `memcredit_am3.bm25_order` and `nonabstain_bm25`.
  - Per-pool records: `memcredit_am3g.table_record` (via `records_of`).
  - b, c, the exact McNemar test and both intervals: `memcredit_keepset_search.paired_reading`
    (`mcnemar_exact`).
  - Read summaries: `memcredit_keepset_search.reads_summary`.
  - Natural-mix rate and break-even share: `memcredit_am3g.natural_mix`.
  - Provenance: `memcredit_am3g.check_features`.
  - Hand plan and join: `memcredit_am3g.hand_plan` and `hand_check`.
  - Bootstrap settings are the registration's: 10,000 resamples, seed 42.
- **Inputs, each checked against its registered SHA-256 before use:**
  - held-out features `ed417538...` and abstention features `4a18d2cf...`, under
    `~/cotcodec-runs/stage0/am3-nonabstain-generality-v1/private/` on the host;
  - the receipted hand labels `2ff9f353...` and the plan these features give, `918468a4...`;
  - the registered `results.json`, `d0ff2896...`.
  - Only `item_id` and `label` are read from the hand labels. Reply texts and label notes stay on
    the host.
- **The K = 70 check: pass.** K = 70 reproduced 243 registered figures exactly, with 0
  differences, and the script refuses to write outputs unless it does:
  - the headline counts: OLMo-2 35 against 0, Qwen3.5-9B 31 against 0 and Qwen3-8B 39 against 0;
    H2 costs 5, 8 and 1;
  - every field of the rule-against-top-4 comparison, per reader, judge and arm, on both
    populations;
  - the read summaries;
  - the abstention cost figures under both judges;
  - the natural-mix summaries under both judges and both resampling schemes;
  - the registered hand check, recomputed.
- **Run.** Host CPU only, from a clean checkout of commit `23e09457` under
  `~/cotcodec-runs/stage0/am4-read-caps/`, on 2026-10-15 (16:06:01-16:06:16Z), with
  `uv run --locked --offline`.
  - `analyze` ran twice. `results.json` and `tables.md` were byte-identical (`56fe0d99...`,
    `9ef05c57...`).
  - `tests/test_memcredit_am4.py` passed: 95 tests.
- **A second route.** `crosscheck` recomputes the judge-based figures without the features or the
  stop-rule code. It reads the committed `per-table.json.gz` of the registered run (`921c0ea0...`):
  at cap K a pool's outcome is the rule's when its first answering position is at most K, and BM25
  top 4's otherwise.
  - Covered: b, c, b2, c2, the cap counts, the mean reads and the natural-mix point estimates.
  - It agrees on all 462 figures, on the host and on a Mac from the committed files alone.

## The K curve (retrieved arm, Qwen3-32B judge)

b: the capped rule right and BM25 top 4 wrong; c: the reverse; on the 347 answerable questions.
c = 0 at every K for every reader under this judge. b2: BM25 top 4 right (a correct abstention)
and the capped rule wrong, on the 30 unanswerable questions; c2 = 0 everywhere. Net rate: at the
470:30 mix. Intervals: 95% bootstrap, each population resampled separately.

| Reader | K | b | b2 | mean reads, answerable | mean reads, unanswerable | net rate [95%] | break-even share [95%] |
|---|---:|---:|---:|---:|---:|---|---|
| Qwen3-8B | 1 | 0 | 0 | 1.00 | 1.00 | +0.000 | 1.00 |
| | 2 | 10 | 1 | 1.33 | 1.97 | +0.025 [+0.009, +0.043] | 0.46 [0.17, 1.00] |
| | 4 | 19 | 1 | 1.86 | 3.83 | +0.049 [+0.028, +0.073] | 0.62 [0.30, 1.00] |
| | 8 | 31 | 3 | 2.68 | 7.47 | +0.078 [+0.051, +0.108] | 0.47 [0.27, 1.00] |
| | 16 | 33 | 3 | 3.98 | 14.40 | +0.083 [+0.055, +0.115] | 0.49 [0.29, 1.00] |
| | 26 | 39 | 3 | 5.45 | 23.07 | +0.100 [+0.069, +0.133] | 0.53 [0.32, 1.00] |
| | 70 | 39 | 5 | 11.24 | 58.93 | +0.096 [+0.065, +0.129] | 0.40 [0.25, 0.75] |
| OLMo-2 | 1 | 0 | 0 | 1.00 | 1.00 | +0.000 | 1.00 |
| | 2 | 10 | 0 | 1.39 | 1.83 | +0.027 [+0.011, +0.046] | 1.00 [1.00, 1.00] |
| | 4 | 20 | 1 | 2.03 | 3.47 | +0.052 [+0.030, +0.077] | 0.63 [0.32, 1.00] |
| | 8 | 27 | 3 | 3.07 | 6.63 | +0.067 [+0.041, +0.096] | 0.44 [0.24, 1.00] |
| | 16 | 30 | 5 | 4.81 | 12.20 | +0.071 [+0.043, +0.101] | 0.34 [0.20, 0.69] |
| | 26 | 33 | 6 | 6.70 | 18.57 | +0.077 [+0.048, +0.108] | 0.32 [0.20, 0.60] |
| | 70 | 35 | 8 | 13.53 | 43.10 | +0.079 [+0.048, +0.111] | 0.27 [0.17, 0.47] |
| Qwen3.5-9B | 1 | 0 | 0 | 1.00 | 1.00 | +0.000 | 1.00 |
| | 2 | 9 | 0 | 1.35 | 1.90 | +0.024 [+0.011, +0.041] | 1.00 [1.00, 1.00] |
| | 4 | 17 | 0 | 1.89 | 3.70 | +0.046 [+0.027, +0.068] | 1.00 [1.00, 1.00] |
| | 8 | 26 | 0 | 2.79 | 7.27 | +0.070 [+0.046, +0.098] | 1.00 [1.00, 1.00] |
| | 16 | 27 | 0 | 4.25 | 13.93 | +0.073 [+0.049, +0.100] | 1.00 [1.00, 1.00] |
| | 26 | 28 | 1 | 5.94 | 22.13 | +0.074 [+0.048, +0.102] | 0.71 [0.41, 1.00] |
| | 70 | 31 | 1 | 12.67 | 57.33 | +0.082 [+0.055, +0.112] | 0.73 [0.44, 1.00] |

The K = 70 rows are the registered results. `tables.md` adds the intervals, p-values and cost
rates for every row.

## The shape of the trade-off (descriptive)

- **Gains come early in the BM25 order.** Counts are in the order Qwen3-8B, OLMo-2, Qwen3.5-9B.
  - By K = 4 the capped rule has 49-57% of K = 70's gains (19 of 39, 20 of 35, 17 of 31).
  - By K = 8 it has 77-84% (31, 27 and 26).
  - c stays 0 at every K.
  - Most answerable pools answer at position 1, so the gain grows with K only on the pools where
    BM25 top 4 abstains.
- **Reads grow almost linearly with K on unanswerable questions, and slowly on answerable ones.**
  - Unanswerable questions read about K subsets at every cap (6.6-7.5 at K = 8, against 43-59
    at 70). Nearly every 4-subset abstains: the cap is reached on 22-26 of 30 pools at K = 8.
  - Answerable questions read a mean of 2.7-3.1 at K = 8, against 11.2-13.5 at 70. The median
    is 1 at every K.
- **Costs also grow with K, from small counts.**
  - b2 rises from 0 at K = 1 to 5, 8 and 1 at K = 70 (Qwen3-8B, OLMo-2, Qwen3.5-9B). At K = 8 it
    is 3, 3 and 0.
  - Adjacent caps differ by 0-2 questions out of 30. Every exact interval overlaps the others.
- **Net rate at the 470:30 mix.**
  - It rises steeply up to K = 8 (+0.067 to +0.078). After that it moves by at most +0.022 (+0.079
    to +0.096 at K = 70).
  - From K = 8 up, the intervals of every reader overlap heavily.
  - Only Qwen3-8B's net is not monotone in K: +0.100 at K = 26 against +0.096 at 70. The
    difference is two abstention questions (b2 3 against 5), not evidence of an optimum.
- **Break-even share.**
  - Without a judged cost the share is 1 (Qwen3.5-9B up to K = 16; OLMo-2 at K = 2).
  - Otherwise it falls as late costs accrue after the gains have slowed. For OLMo-2 it goes
    from 0.63 at K = 4 to 0.27 at K = 70.
  - The intervals are wide, and most reach 1.
- **Second judge (Qwen3-8B), the same shape.**
  - The second judge records losses (c up to 12), so the gains are smaller.
  - The net rate stays at or above zero at every K, at +0.017 to +0.069.
  - This judge's known error is accepting "I don't know" on answerable questions (AM3).
- **Gold arm, the same shape.** By K = 8 it has 22 of 31, 23 of 37 and 12 of 19 of K = 70's gains,
  with c = 0 under Qwen3-32B.
- **Hand labels agree with the judge at every K.**
  - Held-out, OLMo-2 and Qwen3.5-9B: on every question the judge splits, the hand count equals
    the judge's b, with 0 reversals.
  - Abstention: the hand b2 equals the judge's for Qwen3-8B and OLMo-2. It is 0 at every K for
    Qwen3.5-9B. Its one judged cost, from K = 26, is a refusal the four patterns miss, which the
    hand labels do not count as a cost.
  - Among switched pairs that the judge calls concordant and that were hand-labelled as
    distractors, the hand labels split only two held-out pairs. Both are gains the judge missed:
    Qwen3.5-9B's from K = 2, and OLMo-2's only at K = 70.
  - No hand-labelled abstention pair hides a cost.

## Caveats

- **Post hoc, on the confirmation questions.** Any K that looks good here was found on the data
  that confirmed the rule, so its figures are optimistic. Confirmation needs new questions.
- **Few unanswerable questions.** There are 30, and b2 is at most 8, so the cost side of the curve
  rests on a handful of questions per reader.
- **The cost is JUDGE_QUALIFIED at every K.**
  - G-J2 failed: the abstention judge rejected 26 of 30 decoys, so costs could be undercounted.
  - The hand labels cover every judge-split abstention question, but they cannot reveal costs
    in pairs the judge called concordant beyond the sampled distractors.
- **The abstention questions are near-miss edits.** 27 of 30 share memories with an answerable
  twin. They are not a sample of deployment's unanswerable questions.
- **The natural mix is an assumption.** The net rates assume that the 347 held-out questions
  represent LongMemEval-S's answerable questions, and they use the 470:30 mix. Other mixes move
  the net by the break-even arithmetic.
- **Reads are a count of reader calls on 4-subsets.**
  - They assume sequential calls that stop at the first answer.
  - They do not price latency, batching, or the all-8 alternative.
  - All 8 beats the rule on unanswerable questions for every reader (registered result).
- **p-values are unadjusted and descriptive** across 7 caps, 3 readers, 2 judges and 2 arms.
- **Qwen3.5-9B ran in vLLM's default mode.** That mode is not replay-exact. The features are the
  registered run's, unchanged.
- **The anchor's hand labels cover only its abstention replies.** Its held-out replies were not
  hand-labelled by the registration.

## Files

- `results.json`, text-free: per reader and K, the following, plus the K = 70 check, the inputs'
  digests and the code's digests:
  - held-out, both arms and both judges: the paired readings, read summaries, cap counts and
    switches;
  - abstention: the cost figures;
  - the natural mix, both judges and both resampling schemes;
  - the hand-label counts.
- `tables.md`, text-free: every table above, with intervals.
- **Reproduce on the host.** From a clean checkout of `23e09457`, run
  `uv run --locked --offline python scripts/memcredit_am4.py analyze --heldout-features
  .../private/features-heldout.json.gz --abstention-features
  .../private/features-abstention.json.gz --hand-labels .../hand/hand-labels.jsonl --output-dir
  OUT`.
- **Check anywhere.** `python scripts/memcredit_am4.py crosscheck --results
  program/evidence/2026-10-16/am4-read-caps/results.json`.
