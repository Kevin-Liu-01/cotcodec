# am3-nonabstain-generality-v1: results

**CONFIRMATORY, VERIFIED. Frozen registration `am3-nonabstain-generality-v1`.**
- **Ledger and commits.** Ledger row 25 (`ff8670f2...`). Fill commit `78e9c00f`; freeze commit
  `6384f294`, which adds only the row.
- **Checks.** Three independent pre-freeze checks ran, recorded in section 19.
- **Run.** Section 16's runbook ran once on 2026-10-15, in reg mode, from the freeze commit:
  - image build 1475;
  - CPU selftests 1476 and 1477;
  - held-out GPU job 1480 (33:01);
  - abstention GPU job 1482 (06:13).
- **Outcome of the run.** No rerun was needed. GPU use was 0.6722 physical GPU-h against the
  2.08 cap.
- **Receipt order.** The blind hand-label receipt was committed (`417d1149`, 15:32:14Z) before
  `analyze` started (15:32:24Z). No commit falls between the first GPU job and the receipt.

**Disclosures (registration section 1):**
- **No gauntlet score (D118).**
- **Hand labels are an agent's (D9).** An isolated agent made the hand labels: `claude-opus-5-5`,
  one subagent per chunk, 278 items in 5 chunks. Each transcript was audited, and the CLI launch
  failed as expected beforehand.
- **Data already used.** The held-out questions were used before by AM1 and
  `am1-keepset-search-v1`, with Qwen3-8B as reader.
- **Design shaped by development work.** The rule, and its four abstention patterns, came from
  development work on Qwen3-8B (AM1d, AM3).
- **Qwen3.5-9B ran in vLLM's default mode,** which is not replay-exact. OLMo-2 ran
  batch-invariant, with no fallback.
- **OLMo-2's licence.** Its model card limits it to research and educational use, under
  additional Gemma terms. No acceptance was required.
- **The abstention questions are near-miss edits.** 27 of the 30 share memories with an
  answerable twin, and 22 twins are in H1's population.
- **Deviations:** none.

## Outcome

**H1 (confirmatory): NONABSTAIN_HELPS for both new readers.** Keeping the best-BM25-ranked
4-subset whose reply does not abstain is more accurate than BM25 top 4 on the 347 held-out
answerable questions (retrieved arm, Qwen3-32B judge):

| Reader | BM25 top 4 | nonabstain-BM25 | b | c | Difference [95% bootstrap] | p (Holm) | Hand check (b, c) |
|---|---:|---:|---:|---:|---|---:|---|
| OLMo-2-1124-7B-Instruct | 0.329 | 0.429 | 35 | 0 | +0.101 [+0.069, +0.133] | 1.2e-10 | 35, 0: confirmed |
| Qwen3.5-9B | 0.464 | 0.553 | 31 | 0 | +0.089 [+0.061, +0.121] | 9.3e-10 | 31, 0: confirmed |
| *Qwen3-8B (anchor, replayed)* | *0.458* | *0.571* | *39* | *0* | *+0.112* | — | — |

- **Hand check.** The blind labels agree with the judge on 274 of 278 items (kappa 0.967). The two
  held-out disagreements are in distractor pairs and would be hidden gains, so H1 is, if anything,
  conservative.
- **The anchor.** It replayed job 1458 token for token on 49,274 of 49,274 requests, and its labels
  equal AM1's tables. It reproduces `am1-keepset-search-v1`'s 39 against 0.

**H2 (descriptive, JUDGE_QUALIFIED): what the rule costs on unanswerable questions.**
- **The questions.** LongMemEval-S has 30 abstention questions, never used before.
- **What goes wrong.** On them, a correct "I don't know" from BM25 top 4 becomes a wrong answer
  when the rule switches to a 4-subset that answers.

| Reader | BM25 top 4 correct | rule correct | cost b2 | c2 | cost rate [exact 95%] | hand (b2, c2) |
|---|---:|---:|---:|---:|---|---|
| Qwen3-8B | 30 | 25 | 5 | 0 | 0.167 [0.056, 0.347] | 5, 0 |
| OLMo-2 | 25 | 17 | 8 | 0 | 0.267 [0.123, 0.459] | 8, 0 |
| Qwen3.5-9B | 29 | 28 | 1 | 0 | 0.033 [0.001, 0.172] | 0, 0 |

**Why H2 is JUDGE_QUALIFIED.**
- **The failed check.** G-J2 failed: the abstention judge rejected 26 of 30 decoy answers, and
  the registered bar was 29.
- **The failure mode.** The judge accepted plain answers as "identified as unanswerable" on two
  knowledge-update questions, one single-session-user and one multi-session.
- **The direction.** This failure can only hide costs, so b2 could be too low.
- **The bound.** The judge called the rule's switched reply correct on only 0-2 pools per reader.
  The hand labels agree on every pool they cover, and they found no hidden cost.

**Two corrections from the hand labels** (the verifier's; descriptive):
- **Qwen3.5-9B's one judged cost** is a refusal the four patterns do not catch. The hand label
  rejects it as a cost, so the hand count is 0.
- **Qwen3-8B's two H2 accuracies** are each 1/30 too high. The judge accepted a non-abstaining
  top-4 reply that the hand label rejects. Neither b2 nor c2 changes.

## Net effect at LongMemEval-S's own mix (descriptive)

The mix is 470 answerable to 30 unanswerable questions, judged by Qwen3-32B.

| Reader | gain per answerable | loss per unanswerable | net rate at 470:30 [95%] | break-even unanswerable share [95%] |
|---|---:|---:|---|---|
| Qwen3-8B | +0.112 | 0.167 | +0.096 [+0.065, +0.129] | 0.40 [0.25, 0.75] |
| OLMo-2 | +0.101 | 0.267 | +0.079 [+0.048, +0.111] | 0.27 [0.17, 0.47] |
| Qwen3.5-9B | +0.089 | 0.033 | +0.082 [+0.055, +0.112] | 0.73 [0.44, 1.00] |

- **When the rule stops paying.** It pays while unanswerable questions are below the break-even
  share of the mix.
- **Assumption.** These rates treat the 347 held-out questions as representative of
  LongMemEval-S's answerable questions, which holds only approximately.
- **Twins.** The linked-twins bootstrap gives nearly the same intervals.

## Other descriptive results

**Read cost.**
- On answerable questions the stop rule reads a median of 1 subset, with a mean of 11-14.
- On unanswerable questions the median is 70 reads, a mean of 43-59: nearly every 4-subset
  abstains, so the rule reads them all before falling back. 90-97% of their 4-subset replies
  abstain.

**Against keeping all 8** (retrieved arm, Qwen3-32B):

| Reader | all 8 | nonabstain-BM25 | Questions favouring the rule : all 8 | p |
|---|---:|---:|---|---:|
| OLMo-2 | 0.352 | 0.429 | 44 : 17 | 0.0007 |
| Qwen3-8B | 0.524 | 0.571 | 33 : 17 | 0.033 |
| Qwen3.5-9B | 0.524 | 0.553 | 26 : 16 | 0.16 |

On the unanswerable questions, all 8 does better than the rule for every reader.

**Second judge (Qwen3-8B).** The rule's gains over BM25 top 4 shrink, and some losses appear:
OLMo-2 32 against 12, Qwen3.5-9B 25 against 6, Qwen3-8B 33 against 7. Every cell stays
positive. This judge's known error is accepting "I don't know" on answerable questions (AM3).

**Gold arm.**
- The rule leads BM25 top 4 for all three readers: OLMo-2 37 against 0, Qwen3.5-9B 19 against 0,
  Qwen3-8B 31 against 0.
- The full tables are in `tables.md`.

## Verification

A fresh verifier checked the run from scratch.
- **Analyze, rerun.** It reran `analyze` from a new export of the freeze commit on the host.
  `results.json`, `per-table.json.gz` and `tables.md` were byte-identical.
- **Extract, rerun.** Rerunning `extract` reproduced both feature digests.
- **Independent recomputation.** Its own code, which imports nothing from
  `scripts/memcredit_am3g.py`, recomputed every number in this file exactly:
  - H1 and Holm;
  - the anchor's replay and 39 against 0;
  - H2 with its exact intervals;
  - the natural-mix rates and break-even shares;
  - the hand-check join;
  - G-J2's 26 of 30.
- **Process.** It confirmed:
  - the ledger chain (25 rows);
  - that the freeze commit adds only the row;
  - the image provenance;
  - that every job ran after the freeze;
  - the GPU-hours;
  - the receipt ordering, enforced by the commit id in the analyze log;
  - the labelling protocol: one transcript per chunk, audited, and the Mac copies deleted;
  - hygiene: 18,564 run texts searched across the committed files.
- **Effect on the readings.** None of its findings changes a reading. Its corrections are
  applied above.

## What the result licenses

**H1, NONABSTAIN_HELPS for each of OLMo-2-1124-7B-Instruct and Qwen3.5-9B.**
- **The claim.** Keeping the best-BM25-ranked 4-subset whose reply does not abstain is more
  accurate than keeping BM25 top 4.
- **Scope:**
  - AM1's prompt with its "I don't know" instruction;
  - the Qwen3-32B judge, confirmed by blind agent labels;
  - AM1's 347 held-out answerable LongMemEval-S questions;
  - BM25 user-turn pools, keeping 4 of 8.
  - For Qwen3.5-9B only: in vLLM's default mode and this run's batch schedule.
- **Across readers.** With the anchor, the gain on answerable questions holds for all three
  readers tried, from two model families.
- **What it rests on.**
  - c ≈ 0 by construction on answerable questions, so the gain is the rate at which a pool that
    makes BM25 top 4 abstain contains a 4-subset that answers correctly.
  - The rule pays for this in reads.

## What it does not license

- **Not a claim of safety on unanswerable questions.** H2 shows that the rule turns correct
  abstentions into wrong answers: 3-27% of unanswerable questions, judge-qualified.
- **No claim of beating all 8.** That comparison is descriptive, and it fails for Qwen3.5-9B.
- **No conclusions from the descriptive results:**
  - H2's labels, the natural-mix rates and the break-even shares;
  - the gold arm, the second judge and per-type results.
- **No claim beyond the setup tested.** Other prompts, retrievers, pool sizes, budgets, judges,
  datasets, or abstention patterns fitted to these readers were not tested.
- **No mechanism.** It does not say why a different memory subset turns an abstention into a
  correct answer.

## Files

- `results.json`, `per-table.json.gz` and `tables.md`: the registered `analyze` outputs, text-free.
- `hand-check/`: the receipt, committed before the join, plus the sample, plan, merge and manifest
  records (text-free).
- `jobs/`, `logs/`, `manifests/`, `builds/`, `selftests/`, `prepare/` and `ops/`: the operations
  records, including the saved `scontrol` records.
- **What stays on the host.** The reply texts, features and hand-label texts stay under
  `~/cotcodec-runs/stage0/am3-nonabstain-generality-v1/`.
