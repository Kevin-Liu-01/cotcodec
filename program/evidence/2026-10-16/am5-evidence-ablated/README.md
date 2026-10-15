# AM5: what the non-abstention rule costs when the evidence is absent (EXPLORATORY, development data only)

**EXPLORATORY. DEVELOPMENT SPLIT ONLY. AM5 licenses nothing.**
- **Questions.** The pilot's 63 development questions, the same 63 that AM3 and the am3g dry run
  used. No held-out question and no `_abs` question was used or given to a model (`prepare` parses the whole LongMemEval-S file to select the development ids).
- **No test.** Every number is a description with an exact interval. Counts are small (63 pools
  per reader), so the intervals are wide.
- **Decision.** D120: a held-out registration on the 347 questions follows only if this
  development run is clean. That decision is not made here.

## The question

The non-abstention keep rule reads a pool's 70 4-subsets in BM25 order and keeps the first whose
reply does not abstain, up to K reads; otherwise it keeps BM25 top 4.
- **Gain.** On answerable questions it gains +0.089 to +0.112 on held-out data
  (`am3-nonabstain-generality-v1`).
- **Cost, until now.** Its cost on unanswerable questions was measured only on LongMemEval-S's 30
  edited abstention questions, with a judge that failed its check (G-J2).
- **AM5.** It measures the cost on pools built so that the evidence is absent and "I don't know"
  is the correct reply by construction.

## Construction

- **Removing the evidence.** For each development question, every haystack session whose id is
  in LongMemEval's `answer_session_ids` is removed, with its date. A repeated id would be removed
  in every copy; none of the 63 has one.
  - 124 sessions were removed, the 124 evidence session ids, all present in their haystacks.
  - About 47 sessions per question before removal; 15,294 user turns before, 14,557 after.
- **The pool.** The BM25 top-8 user-turn pool of what remains, exactly as AM1's retrieved arm:
  `memcredit_am3g.retrieved_pool` calls `harness.memcredit` `rank_user_turns`, `memory_entry`
  and `chronological`.
  - The same call on the unablated records reproduces the pilot's development pools, 63 of 63
    (`prepare/ablated-summary.json`, `dev_retrieved_pool_check`).
  - The ablated pools share 263 of their 504 memories with the original pools.
- **Built once on the host CPU.** `memcredit_am5.py prepare` at `658d2c6e` built the artifact.
  - The artifact is `f6d27d4c...`, 375,482 bytes, host only and read-only.
  - It was pinned in the config at `6f681226` before the image was built.
  - The committed summary `prepare/ablated-summary.json` is text-free: ids, digests, pool
    coordinates and the leakage facts.

### Leakage check (e)

| Check | Result |
|---|---:|
| LongMemEval `has_answer` turns, all 63 development questions | 126 |
| of which inside the evidence sessions | 126 |
| `has_answer` turns left in the ablated haystacks | **0** |
| `has_answer` memories in the ablated pools | **0** |
| ablated pool memories whose text equals an evidence-session user turn | 0 |
| ablated pools with a memory containing the normalized reference answer (crude) | 4 |
| questions whose remaining user turns contain the normalized reference answer (crude) | 10 |
| for comparison: original pools with a `has_answer` memory | 58 of 63 |

- **The string check is crude.** It looks for the normalized reference answer as words in a
  memory (`harness.memcredit.contains_answer`).
  - All 4 pool matches are one-token answers, on knowledge-update and multi-session questions.
  - 9 of the 10 questions with a match in a remaining turn also have one-token answers.
  - These are most likely chance matches, such as a number.
  - None of the three replies found correct below comes from such a pool.
- **By the dataset's own flags, no evidence is left.** What the flags cannot rule out is an answer
  that can be guessed, or that is stated in a session LongMemEval did not mark.

## Readers, judge and run

- **Readers.** am3g's readers, revisions, engines and steps, unchanged, with AM1's prompt (which
  tells the reader to say "I don't know"):
  - Qwen3-8B, eager and batch-invariant;
  - OLMo-2-1124-7B-Instruct, eager and batch-invariant through the Transformers backend, as in
    AM3. Its declared default-mode fallback was not needed.
  - Qwen3.5-9B, eager, in vLLM's default mode. That mode is not replay-exact, and this request
    list differs from AM3's.
- **Requests.** Per pool, the 70 4-subsets and all 8: 4,473 requests per reader. Greedy, at most
  64 tokens. Every reply ended on its stop token.
- **Judge.** Qwen3-32B (eager, batch-invariant) with LongMemEval's non-abstention answer-check
  prompt against the reference answer.
  - It scored all 272 distinct replies and AM1's 188 validation items on these questions.
  - Validation: reference answers 58 of 58 yes (preference questions left out), "I don't know."
    0 of 63 yes, another question's answer 4 of 62 yes.
- **Rule and abstention.** The rule, the BM25 order and AM1d's four abstention patterns are the
  registered ones (`memcredit_am3.nonabstain_bm25`). The capped rule is AM4's (a test checks
  that it is equal).
- **Code.** `scripts/memcredit_am5.py`.
  - The GPU job's driver and worker port `memcredit_am3g.run_main`, `run_step` and `vllm_worker`
    to this population, with the same engine calls. am3g's registered file is unchanged.
  - The operator scripts are `ops/am5/`.
- **Host rules.** Every job used Slurm partition `research`. D110's `transcreate-*` jobs held
  GPUs 0-1 and were not touched (`ops/preflight.log`).
  - The docker-research lane ran the container read-only, with `--cap-drop ALL`,
    `no-new-privileges`, the user's uid:gid, a tmpfs `/tmp`, no network and only the allocated
    GPU. Stock vLLM 0.31.0.

| Job | What | GPUs | Run time | GPU-h |
|---|---|---:|---:|---:|
| (host CPU) | `prepare` at `658d2c6e` | 0 | seconds | 0 |
| 1483 | cotcodec-vllm cu129 overlay build from the capsule of `6f681226` (image `112e45eb...`, provenance PASS) | 1 | 00:01:06 | 0.0183 |
| 1484 | post-build CPU selftest (no GRES): prompts at most 1,148 / 1,077 / 1,164 tokens; judge items 302 | 0 | 00:00:16 | 0 |
| 1487 | GPU job: readers 32.7, 34.0 and 58.5 s passes; judge 3.4 s on 460 items | 1 | 00:06:41 | 0.1114 |
| | **total** | | | **0.1297** of the config's 0.5 cap (D120 estimated about 0.3; the config comment's "D120's budget" is wrong, and is left as run) |

- **Run times.** These are `scontrol` RunTime. Slurm limits were 5 and 20 minutes, 0.42 GPU-h at
  the limits.
- **Not AM5's jobs.** Jobs 1485 and 1486 appear in none of AM5's logs, and scontrol no longer knew
  them.

## Results

Per reader, over 63 pools; exact 95% intervals in `tables.md`.
- **(a) Switch rate:** BM25 top 4 abstains and a non-abstaining 4-subset is found within K reads.
  It is read from abstention flags, with no judge.
- **(b)** BM25 top 4 itself does not abstain.
- **(c)** The all-8 reply abstains. Also shown: every 4-subset abstains.

| Reader | (a) K = 8 | (a) K = 70 | (b) top 4 answers | (c) all 8 abstains | every 4-subset abstains | 4-subset replies abstaining |
|---|---:|---:|---:|---:|---:|---:|
| Qwen3-8B | 1 (0.016) | 2 (0.032) | 1 | 61 | 60 | 98.4% |
| OLMo-2 | 6 (0.095) | 10 (0.159) | 4 | 56 | 49 | 92.9% |
| Qwen3.5-9B | 3 (0.048) | 3 (0.048) | 0 | 61 | 60 | 98.0% |

- **Intervals.** OLMo-2's K = 70 rate is 0.159 [0.079, 0.273]; Qwen3-8B's is 0.032
  [0.004, 0.110].
- **Reads.** The rule reads a mean of 56.5-67.8 subsets at K = 70 and 7.1-7.8 at K = 8: on most
  pools it reads to the cap and keeps BM25 top 4.

### (d) Answers correct by chance

The judge scored every switched reply and every non-abstaining top-4 reply. A blind hand check then
labelled all of them, not only those the judge accepted: 18 distinct replies (15 switched uses, 5
top-4 uses).

| Reader | switched, K = 8 | correct (judge, hand) | switched, K = 70 | correct (judge, hand) | top-4 answers | correct (judge, hand) |
|---|---:|---|---:|---|---:|---|
| Qwen3-8B | 1 | 1, 1 | 2 | 1, 1 | 1 | 0, 0 |
| OLMo-2 | 6 | 1, 1 | 10 | 1, 1 | 4 | 1, 1 |
| Qwen3.5-9B | 3 | 0, 0 | 3 | 0, 0 | 0 | — |

- **Three replies are correct.** The judge and the hand labels agree on all 18 items (kappa
  1.00), and on all 3 that are correct:
  - Qwen3-8B's switch on a single-session-preference question, whose reference is a rubric for a
    personalised suggestion;
  - OLMo-2's switch on a single-session-user question with a two-token answer;
  - OLMo-2's non-abstaining top 4 on a temporal-reasoning question.
- **No string leakage behind them.** None of the three pools holds a memory that contains the
  answer string, and none of the three questions has the answer string in a remaining user turn.
  For the OLMo-2 single-session-user item, this rules out string-level leakage. For the other
  two (a 72-token rubric and an 11-token answer), a whole-answer string check essentially cannot
  match, so it is uninformative there. Those pools also share 5-7 of their 8 memories with the
  original pools. The operator did not read the reply texts, which stay on the host.
- **The cost.** It counts switched replies that are not correct, as a share of the 63 questions.

| Reader | cost K = 8 (hand) [95%] | cost K = 70 (hand) [95%] |
|---|---|---|
| Qwen3-8B | 0/63, 0.000 [0.000, 0.057] | 1/63, 0.016 [0.000, 0.085] |
| OLMo-2 | 5/63, 0.079 [0.026, 0.176] | 9/63, 0.143 [0.067, 0.254] |
| Qwen3.5-9B | 3/63, 0.048 [0.010, 0.133] | 3/63, 0.048 [0.010, 0.133] |

The judge's cost equals the hand cost in every cell.

- **Where switches happen.** 4 of the 15 switches (K = 70, all readers) are on
  single-session-preference questions, which are only 5 of the 63. Their reference is a rubric
  for a personalised suggestion. Without the evidence, a reader can still give a generic
  suggestion, and "I don't know" is not clearly the right reply there.
- **Sensitivity without single-session-preference questions** (58 questions; the independent
  checker's counts):
  - cost at K = 8 is 0, 4 and 2 (Qwen3-8B, OLMo-2, Qwen3.5-9B);
  - cost at K = 70 is 1, 7 and 2.
  - Qwen3-8B's zero cost at K = 8 on all 63 rests on one preference switch that was judged
    correct.

### The same questions with their evidence (AM3's committed records)

These are the same 63 questions with their original retrieved pools, from AM3's committed
`per-table.json.gz` (`0fc5635b...`, job 1466), Qwen3-32B. The capped choice is the rule's when its
first answering position is at most K (AM4's crosscheck).

| Reader | switch rate K = 8 / 70 | top 4 answers | all 8 abstains | gain b, c at K = 8 | gain b, c at K = 70 | gain per question |
|---|---|---:|---:|---|---|---:|
| Qwen3-8B | 7 / 7 | 46 | 17 | 1, 0 | 1, 0 | +0.016 |
| OLMo-2 | 13 / 15 | 43 | 21 | 4, 0 | 4, 0 | +0.063 |
| Qwen3.5-9B | 7 / 8 | 44 | 17 | 3, 0 | 3, 0 | +0.048 |

- **Side by side, per question (descriptive).** Development gain against cost with the evidence
  removed, hand labels, K = 70:
  - Qwen3-8B: +0.016 against 0.016;
  - OLMo-2: +0.063 against 0.143;
  - Qwen3.5-9B: +0.048 against 0.048.
- **Not a deployment estimate.** The development gains are far below the held-out gains (+0.112,
  +0.101 and +0.089; D118 noted that development understated the anchor about sevenfold). So
  `tables.md`'s break-even shares from these numbers (0.31-0.50 at K = 70) are not an estimate
  for deployment.
- **Different questions switch.** On the ablated pools the rule switches on different questions
  than on the original pools: only 0-1 per reader switched on both.

### Against the earlier cost measurements

| Reader | AM5 cost, K = 70 (hand), 63 ablated dev pools [AM5 switches] | `am3-nonabstain-generality-v1` H2 cost (judge; hand), 30 edited `_abs` questions | development gold-free proxy (am3g section 9): switch counts, not costs |
|---|---|---|---|
| Qwen3-8B | 1 (0.016) [2] | 5; 5 (0.167) | 3 of 63 |
| OLMo-2 | 9 (0.143) [10] | 8; 8 (0.267) | 11 of 63 |
| Qwen3.5-9B | 3 (0.048) [3] | 1; 0 (0.000 by hand) | 4 of 63 |

- **The order of readers repeats.** OLMo-2 costs the most.
- **The two Qwen readers.** For Qwen3-8B the evidence-absent cost is lower than on LongMemEval's
  edited near-miss questions. Qwen3.5-9B's three switches here are all wrong, against none by
  hand there.
- **The intervals overlap** for every reader.
- **AM5 matches the proxy.** AM5's switch counts (2, 10 and 3) are close to the gold-free proxy
  that am3g computed from development data before any of this existed.

## What this does not show

- **Nothing about the held-out questions.** Development counts are small. The development gains
  understate the held-out gains, so the side-by-side is not a net-effect estimate.
- **Not every kind of unanswerable question.** Removing the evidence sessions leaves a question
  about something the user did discuss, with that discussion deleted. Deployment's unanswerable
  questions also include questions about things never discussed, and near-miss edits like
  LongMemEval's `_abs` questions.
- **"Correct by construction" is approximate.** It rests on LongMemEval's session and turn
  annotations. It is weaker for single-session-preference questions, where a generic answer can
  satisfy the rubric, and for answers that can be guessed.
- **One judge and one agent.** The judge is Qwen3-32B only. The hand labels are one isolated
  agent's (D9: agent labels, not human labels), on 18 replies. Neither covers replies that
  abstain, which the rule's construction treats as correct here.
- **One prompt.** AM1's prompt tells the reader to say "I don't know". 93-98% of 4-subset replies
  on the ablated pools abstain, almost all with that phrase. Another prompt could change the
  switch rate.
- **No replay check for Qwen3.5-9B.** It ran in default mode on a new request list.
- **Two caps.** Only K = 8 and K = 70, as D120 asked; no cap is selected.
- **No mechanism.** AM5 does not say why a reader answers without the evidence.

## Blind hand check (d)

- **The sample.** `hand-sample` drew it from the features, text-free and deterministic: every
  switched reply at K = 70 (which contains K = 8's) and every non-abstaining top-4 reply.
  - Replies are deduplicated by question and normalized-reply SHA-256, in one seeded order.
  - Plan `171707ec...`, sample `9665e749...`.
  - The labeller saw only, per item, the question, its type, the reference answer and the reply.
    It did not see the reader, the judge label, the role or the mask.
- **The labeller.** One fresh Claude Code subagent (`claude-opus-5-5`) of the operator's session.
  - Its whole prompt was am3g's pinned labeller prompt (`98c35cea...`) with the work directory's
    absolute paths. Its instructions (`cf7b3d3c...`) are am3g's criteria for the check "answer".
  - The work directory was outside the repository and held only the chunk, the instructions and
    the manifest.
- **The audit.** It used am3g's `audit_transcript` and passed (`hand-check/hand-audit-01.json`):
  - three tool calls: a Read of each input and a Write of the output;
  - every assistant line from `claude-opus-5-5`;
  - the pinned prompt first;
  - one agent id;
  - every line after the recorded launch time.
  - Its context held the user's and the project's `CLAUDE.md` and `MEMORY.md`. The commits it
    could see carried no judge-derived result.
- **Receipt before the join.** The receipt (`hand-check/hand-receipt.json`: prompt, instructions,
  sample, plan, chunk, transcript and labels digests, the audit and the merge) was committed at
  `632b822d` before `analyze` joined the labels. `logs/analyze-909b571d.log` names that commit.
- **Labels.** 18 of 18 labelled, 3 labelled correct; labels `9da82b41...`.
- **What stays on the host.** The labels' notes, the sample and the transcript stay on the host,
  under `~/cotcodec-runs/stage0/am5-evidence-ablated/hand/`.

## Reproduce

- **Order on the host.** From clean checkouts, the commands ran in this order:
  - `ops/am5/am5-prepare.sh 658d2c6e`;
  - at `6f681226`: `am5-capsule.sh`, `am5-build.sh`, `am5-image.sh`, `am5-selftest.sh`,
    `am5-submit.sh ... submit`, `am5-extract.sh 6f681226 1487` and `am5-hand-sample.sh`;
  - on the Mac, `am5-hand-label-mac.sh prepare` and `push`;
  - `am5-hand-merge.sh`;
  - `RECEIPT_COMMIT=632b822d... am5-analyze.sh` at `6f681226`, then again at `909b571d`.
- **What changed at `909b571d`.** Only the analysis's item-level table and the hand-judge
  agreement were added. The counts are unchanged. Both analyses ran twice and gave byte-identical
  outputs, and the memcredit tests passed on the host each time (254 passed).
- **The committed outputs are `909b571d`'s:**
  - `results.json` `a0d5f358...`;
  - `per-table.json.gz` `58bec838...`;
  - `tables.md` `45b803d5...`.
- **Features.** The features (`16bbd385...`, host only) were extracted at `6f681226`.

## Files

- `results.json`, `per-table.json.gz` and `tables.md`: the analysis outputs, text-free.
  - `per-table.json.gz` holds, per reader and pool: ids, types, masks, abstention flags, first
    answering position, labels and per-cap choices.
- `prepare/`: the ablated artifact's text-free summary, with the per-question leakage facts and
  the pool-builder check, and the prepare output.
- `hand-check/`: the receipt and its text-free records, committed before the join.
- `jobs/1487-dev-ablated/`: the lane records, the driver's summary and environment, per-step
  records, per-pass metadata, the SHA-256 of every raw pass, worker logs and the judge items with
  each response replaced by its SHA-256.
- `builds/`, `selftests/`, `manifests/`, `ops/`, `logs/`: the build, selftest, lane manifest
  (dry run, test-only, submission), `jobs.log`, `preflight.log`, saved `scontrol` records, and the
  extract, hand-sample, analyze and pytest logs.
- **Text search.** The staging script searched every staged file for each of 1,429 texts and found
  none. The texts were every distinct reply of at least 12 characters, and every question, answer
  and memory text of the ablated and the original development artifacts. Home paths are written
  as `~`.
- **What stays on the host.** Raw replies, the judge items, the artifact, the features and the
  hand-check texts stay under `~/cotcodec-runs/stage0/am5-evidence-ablated/`.

## Independent check

A fresh checker reproduced every committed count with its own code on the host. That covered:
- the ablated pools, rebuilt identically (63 of 63, every field);
- the leakage counts;
- the switch rates, the full-pool abstention counts, the reads, the costs and the judged-correct
  counts;
- the hand-judge agreement;
- the original-pool comparison;
- the GPU-hours.

It confirmed four things:
- the ported pipeline matches am3g's engine settings and prompts;
- the labeller saw only the item fields, and its transcript audit passes;
- the receipt commit precedes the join;
- no text appears in the committed files.

Its wording corrections are applied above: the preference sensitivity, the leakage wording, the
comparison table's units, the budget attribution, and smaller nits.
