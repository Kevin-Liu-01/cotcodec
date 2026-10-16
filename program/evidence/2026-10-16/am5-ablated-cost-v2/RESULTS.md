# am5-ablated-cost-v2: results

**CONFIRMATORY, VERIFIED. Frozen registration `am5-ablated-cost-v2`:** ledger row 27, fill commit
`83ba8f8d`, freeze commit `6578e0f0`, which adds only the row.

v1 (row 26) was frozen with a stale code pin. It was voided before running, and the same design was
re-frozen as v2 (D123).

**Run**
- Section 16's runbook ran once, on 2026-10-16, in reg mode, from the freeze commit:
  - build 1548;
  - CPU selftest 1549;
  - GPU job 1552 (19:40).
- The rerun decision was "complete".
- GPU use was 0.3461 physical GPU-h of the 1.42 cap.

**Hand labels**
- Four fresh subagents (`claude-opus-5-5`) made the blind hand labels, one per chunk, 195 items in all.
  The CLI launch failed first, as expected.
- Each transcript was audited.
- The receipt (`9d68966b`, 00:54:17Z) was committed before analyze started (00:54:34Z), and no other
  commit falls between the GPU job and the receipt.

**Disclosures (registration section 1)**
- **The gain side was seen before this registration.** It comes from am3g's committed held-out
  records, read at K as AM4 read them.
- **K = 8 was chosen after AM4 looked at these questions.** Only the cost side is new.
- **Qwen3-8B's gains rest on the Qwen3-32B judge alone.** am3g's hand check covered OLMo-2 and
  Qwen3.5-9B.
- **Leakage can only lower the measured cost, which favours COST_BELOW_GAIN.** 27 of 347 ablated
  pools contain the answer string, and 91 questions have it in a remaining user turn (crude string
  match). At K = 8 no judged-correct switch is in a flagged pool.
- **Tested setup:** AM1's prompt and four abstention patterns; three readers; one judge.
- **Qwen3.5-9B ran in vLLM's default mode,** which is not replay-exact.
- **No gauntlet score (D121).** The hand labels are an agent's (D9).
- **Deviation: one host test failed.** It is listed below.

## The question

The non-abstention keep rule reads 4-subsets of a BM25 top-8 pool in BM25 order. It keeps the first
subset whose reply does not abstain within K reads, and otherwise keeps BM25 top 4.

On answerable questions, the rule gains correct answers (`am3-nonabstain-generality-v1`). The
question here is what it costs when the evidence is absent. Each held-out question's evidence
sessions are removed, and a new BM25 pool is built from the rest of the haystack. On that pool,
"I don't know" is the right reply.

- **Cost:** the rule switches away from an abstaining top 4 to a reply that the judge rejects.
- **Gain:** measured on the same question's original pool.

## Outcome (primary, K = 8, Qwen3-32B judge; the hand labels confirm both directional readings)

| Reader | Cost / gain (of 347) | D = cost − gain [exact 95%] | p (Holm) | Reading | Hand-based |
|---|---|---|---|---|---|
| Qwen3-8B | 6 / 31 | −0.072 [−0.093, −0.038] | 1.2e-4 | **COST_BELOW_GAIN** | 6 / 31, same |
| OLMo-2-1124-7B-Instruct | 22 / 27 | −0.014 [−0.055, +0.028] | 0.568 | **NOT_SEPARATED** | 20 / 27, same |
| Qwen3.5-9B | 6 / 26 | −0.058 [−0.079, −0.025] | 1.1e-3 | **COST_BELOW_GAIN** | 6 / 26, same |

**Break-even share of unanswerable questions** below which the rule raises accuracy, with a lost
abstention and a gained answer weighted equally (K = 8, question-cluster bootstrap 95%):

| Reader | Break-even share |
|---|---|
| Qwen3-8B | 0.84 [0.71, 0.95] |
| OLMo-2 | 0.55 [0.41, 0.69] |
| Qwen3.5-9B | 0.81 [0.67, 0.94] |

**Secondary results, which decide nothing:**
- **K = 70, the uncapped rule:**
  - Qwen3-8B 11 / 39, COST_BELOW_GAIN.
  - OLMo-2 39 / 35, NOT_SEPARATED.
  - Qwen3.5-9B 16 / 31, NOT_SEPARATED: Holm p 0.063, though its hand-based label reads
    COST_BELOW_GAIN.
  - Break-even shares are 0.78, 0.47 and 0.66.
- **Without single-session-preference questions** (322 questions):
  - At K = 8: 5 / 28, 17 / 26 and 4 / 21.
  - At K = 70: 9 / 34, 31 / 31 and 10 / 26.
  - The readings match the primary's.

## Validity checks

- **V1:** pins pass.
- **V2:** complete.
- **V3:** the replay control passes. Qwen3-8B and OLMo-2 replayed job 1487 on 4,473 of 4,473 cells
  in tokens, log-prob bits and labels. Qwen3.5-9B differs slightly (4,470 identical tokens, 4,472
  equal labels); this is reported, not gated, as registered.
- **G-J1:** the judge validation passes. Reference answers 322 of 322 yes; "I don't know." 347 of
  347 no; decoys 3 of 346 yes.
- **Hand against judge:** 186 of 195 agree (kappa 0.72). All 8 switched replies the judge called
  correct were confirmed. One decline note was given.

## Deviation

The host test step reported "1 failed, 230 passed" (pytest exit 1). The failing test was
`test_the_development_gain_side_is_am5s_original_block`.
- **Cause:** the development path guard refuses any path containing `am5-ablated-cost-v2`, and the
  registered checkout lies under that host root.
- **Effect:** none. The guard runs only for the development population.
- **Verifier's check:** from a fresh clone of the freeze commit outside that root, all 231 tests
  pass, and analyze reproduces byte for byte.
- **What changed:** no code and no output.
- **Two related problems:**
  - The `jobs.log` analyze line ("2 commands exited 0") leaves out the test failure.
  - The runbook itself puts the checkout under the guarded root, so this test always fails in reg
    mode. Future registrations should avoid that layout.

## Verification

A fresh verifier checked the run end to end.
- **Analyze rerun:** run twice from a new clone of the freeze commit on the host. `results.json`
  (`7038fc45…`), `per-table.json.gz` (`7ebbac35…`) and `tables.md` (`88ac6626…`) were
  byte-identical.
- **Extract rerun:** the features came out byte-identical (`7ea8584e…`).
- **Receipt and ordering:** the receipt's digests equal those in `results.json`, and the analyze log
  names the receipt commit.
- **Labelling protocol:** one audited transcript per chunk; the Mac copies deleted.
- **Pins and ledger:** all 57 code pins match the freeze commit. The ledger chain verifies (27 rows,
  hashes recomputed). The image provenance matches the freeze commit, and every job ran after the
  freeze.
- **Independent recomputation:** the verifier's own code, importing no `scripts/` module, recomputed
  every count at K = 8 and K = 70, the intervals, the break-even shares, the hand-based counts and
  V3. Everything matched. It computed the gain side two independent ways, and both agreed on all
  347 questions.
- **Hygiene:** 5,306 run texts were searched for across the committed files; none appears.

## What the result licenses

**Qwen3-8B and Qwen3.5-9B, COST_BELOW_GAIN.** The claim, for each of them:
- **Scope:**
  - AM1's 347 held-out LongMemEval-S questions;
  - AM1's prompt;
  - BM25 user-turn pools, keeping 4 of 8;
  - AM1d's four abstention patterns;
  - the Qwen3-32B judge.
- **Statement:** the rule, capped at 8 reads, loses fewer correct answers when a question's
  evidence is removed than it gains when the evidence is present:
  - Qwen3-8B: 1.7% lost against 8.9% gained;
  - Qwen3.5-9B: 1.7% against 7.5%.
- **Consequence:** with equal weights, the rule raises accuracy whenever at most about 81-84% of
  questions lack their evidence.
- **Qwen3.5-9B only:** the scope adds vLLM's default mode and this batch schedule.
- **Qwen3.5-9B's directional reading depends on the cap.** At K = 70, the uncapped rule, it is
  NOT_SEPARATED, and K = 8 was chosen after the fact.

**OLMo-2, NOT_SEPARATED.** Nothing directional is licensed, and this is not evidence that cost
equals gain. Its break-even point estimate is 55%.

## What it does not license

- **Claims about unanswerable questions in general.** Only questions with their evidence removed
  were tested; LongMemEval's 30 edited abstention questions are a different kind (am3g H2).
- **Claims about other prompts, retrievers, judges, readers, or caps other than 8 and 70.**
- **The net effect at any real mix of questions,** or under unequal weights. A deployer who counts a
  wrong answer as worse than a missed one faces a lower break-even.
- **A deployable choice of K.** K = 8 came from a post hoc look at these questions.

## Files

- `results.json`, `per-table.json.gz` and `tables.md`: the registered analyze outputs, text-free.
- `hand-check/`: the receipt, committed before the join, plus the sample, plan, merge and manifest
  records.
- `jobs/`, `logs/`, `manifests/`, `builds/`, `selftests/` and `ops/`: the operations records.
- Run outputs stay on the host under `~/cotcodec-runs/stage0/am5-ablated-cost-v2/`.

## Post-run test maintenance (2026-10-16)

D125's LM1 host prep added candidate models to `models/registry.yaml`, a file section 16 pins.
- **The test changed:** `test_the_gate_opens_with_a_scratch_ledger_row_and_matching_pins` now
  checks the pins against the files at the freeze commit (the ledger row's `git_head_at_freeze`)
  once the real ledger holds this registration's row. It no longer compares them with today's
  working tree. am3g's test got the same change under D122.
- **Pre-freeze cases are unchanged:** before the freeze it still checks the working tree, and a
  tampered pin is still refused.
- **Nothing else changed:** the registration, the frozen code and every output are untouched.
