# AM3: does abstention-aware keep selection hold for other readers and under the second judge? (exploratory, development split only)

**EXPLORATORY. DEVELOPMENT SPLIT ONLY.** AM3 is the next memory step of D117
(`program/decisions.md`). No decision rule applies, and nothing here is confirmatory. Every number
describes the AM1 pilot's 63 development questions, in two pool arms, under the readers, judges
and node below.

- **Data.** The pilot's study artifact (`15567cf1...`, 63 questions, 126 pools of 8 memories). No
  held-out data was opened. The script refuses any path that names `am1-confirmatory`,
  `am1-memory-credit-v1` or `am1-keepset-search-v1`, after resolving symlinks, and refuses any
  study artifact but the pilot's. The ops scripts name only development inputs.
- **Requests.** Per pool, the 70 4-subsets and the full pool of 8: 71 requests, 8,946 per reader.
  BM25 top 4 is one of the 70.
- **Prompt and decoding.** AM1's prompt, unchanged, with its "I don't know" instruction. Greedy
  decoding, at most 64 new tokens, in each reader's own chat template. Thinking is off for both
  Qwen readers.
- **Judges.** Qwen3-32B (primary) and Qwen3-8B (second), with LongMemEval's official
  answer-check prompt as AM1 used it. They ran in eager batch-invariant mode, on every distinct
  (question, reply) of the three readers plus the pilot's 188 validation items: 2,743 items in all.
- **The rule.** Nonabstain-BM25 is AM1d's rule, with its four abstention patterns unchanged
  (digest `031bee27...`). It reads 4-subsets in BM25 order and keeps the first whose reply does
  not abstain. When every 4-subset abstains, it keeps BM25 top 4.
- **Reply texts stayed on the host.** The committed files hold numbers, ids, masks and digests
  only. The staging script searched every staged file for each of the 2,443 distinct replies of
  at least 12 characters and found none.

## Readers

| Reader | Revision | Licence, access | Engine | Role |
|---|---|---|---|---|
| Qwen/Qwen3-8B | `b968826d` | Apache-2.0, on the host since AM1 | vLLM 0.31.0, eager, batch-invariant; AM1's engine block, unchanged | sanity anchor |
| allenai/OLMo-2-1124-7B-Instruct | `470b1fba1ae01581f270116362ee4aa1b97f4c84` | Apache-2.0, ungated | vLLM 0.31.0 Transformers modeling backend, eager, batch-invariant | second family |
| Qwen/Qwen3.5-9B | `c2022362` | Apache-2.0, on the host since G2b | vLLM 0.31.0, eager, **default (not batch-invariant) mode**, text only, prefix caching off | Qwen hybrid (GDN) |

- **OLMo-2-1124-7B-Instruct** was checked without credentials.
  - The Hub API reports `gated: false` with licence tag `apache-2.0`. Its `config.json` and a
    weight shard's headers resolved anonymously at the pinned revision.
  - It was fetched by the GPU-less fetch lane (job 1460, CPU only, 73 s). The host has no Hugging
    Face token, and none was passed. No licence was accepted and no account was created.
  - The receipt (`models/olmo-2-1124-7b-instruct.receipt.json`) records every file's SHA-256 and
    the artifact root `ec7f6955...`. The driver re-verified every file against it before the job
    ran. The registry entry is in `models/registry.yaml`.
  - vLLM 0.31.0 maps `Olmo2ForCausalLM` to its Transformers modeling backend
    (`_TRANSFORMERS_SUPPORTED_MODELS`). The selftest confirmed it resolves, and the engine log
    reads "Using Transformers modeling backend", with FlashAttention 3. No remote code was used.
  - Its context is 4,096 tokens. The longest prompt is 1,099 tokens.
- **Qwen3.5-9B in batch-invariant mode was refused.** vLLM 0.31.0 raises "VLLM batch_invariant
  mode is not supported for GDN_ATTN" at engine start (`v1/attention/selector.py`). The job's
  fallback step then ran the same reader in vLLM's default mode, as the config specified before
  the run. Its replies carry no replay guarantee.

## What ran

| Job | What | GPUs | Run time | GPU-h | Outcome |
|---|---|---:|---:|---:|---|
| 1460 | OLMo-2 fetch (CPU fetch lane, no GRES) | 0 | 73 s | 0 | complete, receipt `4120a5c9...` |
| 1461 | pre-image CPU selftest: commit `18e8f125` mounted into AM1's overlay `abcd2b56` | 0 | about 1 min | 0 | pass |
| 1462 | cotcodec-vllm cu129 overlay build, commit `18e8f125` | 1 | 00:01:08 | 0.0189 | COMPLETED, `sha256:a763bbbc...` |
| 1463 | post-build CPU selftest of the baked `18e8f125` | 0 | 00:00:24 | 0 | pass |
| 1466 | the AM3 job (`scripts/memcredit_am3.py run`), docker-research lane | 1 | 00:10:58 | 0.1828 | COMPLETED 0:0 |
| | **total** | | | **0.2017** of the 2.0 cap | |

- **Run times** are `scontrol` RunTime.
- **Submission.** Both GPU jobs were submitted with no other GPU job of this program queued or
  running, and Slurm allocated the GPU. D110's jobs held GPUs 0-1 throughout and were not
  touched (`ops/preflight.log`).
- **The lane.** The container ran read-only with `--cap-drop ALL`, `no-new-privileges`, the user's
  uid:gid, a tmpfs `/tmp`, no network and `--gpus device=<allocated>`. It ran stock vLLM only.
- **Steps of job 1466**, on one H100, in order:

| Step | Engine init | Pass | Outcome |
|---|---:|---:|---|
| `rd-qwen3-8b` (anchor) | 27.5 s | 70.1 s, 8,946 requests | complete; finish: stop 8,945, length 1 |
| `rd-olmo2` | 28.1 s | 73.4 s | complete; stop 8,904, length 42 |
| `rd-olmo2-default` | | | not needed |
| `rd-qwen35-9b` (batch-invariant) | | | engine refused (above) |
| `rd-qwen35-9b-default` | 41.1 s | 122.1 s | complete; stop 8,937, length 9 |
| `judge32` (Qwen3-32B) | 36.0 s | 19.4 s, 2,743 items | complete |
| `judge8` (Qwen3-8B) | 27.4 s | 4.4 s | complete |

No log-prob was missing. Replies that hit the 64-token cap were judged as they stood, as in AM1.

## Step 1: the pipeline reproduces the pilot (anchor validation)

The anchor reran AM1's reader, Qwen3-8B, through the new 71-request pipeline. It was checked
against the pilot before any other reader's numbers were read.

| Comparison, at the same (question, arm, mask) | Result |
|---|---|
| Replies against the pilot's eager pass (job 1441, first 16 questions) | **2,272 of 2,272 identical in tokens and log-prob bits**, although each pool now has 71 requests, not 274 |
| Qwen3-32B labels against job 1441's, same cells | 2,272 of 2,272 |
| Replies against the compiled pass the tables came from (job 1411, GPU 0) | 8,634 of 8,946 identical in tokens (96.5%), 1,007 also in log-prob bits |
| **Qwen3-32B labels against the pilot's committed tables** (`values_hex`) | **8,913 of 8,946 cells agree (99.63%, 95% CP [99.48%, 99.75%])**; 33 cells differ, in 17 of 126 tables (retrieved 15 cells, gold 18) |
| of which the reply is identical and only the judge differs | 1 cell |
| Qwen3-8B labels against the pilot's second-judge labels | 8,825 of 8,946 cells (8,544 of 8,634 on identical replies) |

- **What the 33 differences are.** They are the expected compiled-against-eager difference. The
  pilot's tables come from job 1411's GPU-0 compile, which differs from eager mode in about 0.2%
  of cells (pilot README). Here the anchor gains 22 cells and loses 11 against the tables.
- **The judges at the item level** (`posthoc.json`, post hoc). Over the 970 judge items AM3
  shares with job 1411:
  - Qwen3-32B eager gives the same label as Qwen3-32B compiled on 969 (one item: pilot yes, AM3
    no);
  - Qwen3-8B on 966 (4 items differ; a recurring reply can cover many cells, which accounts for
    the 90 cells above);
  - against job 1441's eager Qwen3-32B, 403 of 403.
- **The anchor reproduces AM1d's development numbers over all 63 questions.**
  - Retrieved: BM25 top 4 0.508, nonabstain-BM25 0.524 and all 8 0.444, against AM1d's 0.508,
    0.524 and 0.444.
  - Gold: 0.556, 0.619 and 0.587, against 0.571, 0.619 and 0.587. One gold top-4 cell flipped
    under eager mode.
- **Judge validation items.**
  - Qwen3-32B said yes to 58 of 58 reference answers, 0 of 63 "I don't know." and 4 of 62 other
    answers.
  - Qwen3-8B said yes to 58 of 58, 11 of 63 (the pilot's compiled pass: 10) and 5 of 62.

Reading: the pipeline reproduces the pilot. Its labels differ from the committed tables at the
compiled-against-eager rate the pilot measured, and it is bit-exact against the pilot's own eager
replay.

## Answer: the main table (all 63 questions per arm)

b: rule right, base wrong. c: rule wrong, base right. p: exact two-sided McNemar.
Descriptions, fixed in the config before the run: HELPS when p ≤ 0.05 and b > c, HURTS when
p ≤ 0.05 and b < c, NOT_SEPARATED otherwise. None of them decides anything.

| Reader | Judge | Arm | BM25 top 4 | nonabstain-BM25 | all 8 | oracle best 4 | nonabstain vs top 4: b, c (p) | nonabstain vs all 8: b, c (p) |
|---|---|---|---:|---:|---:|---:|---|---|
| Qwen3-8B (anchor) | Qwen3-32B | retrieved | 0.508 | 0.524 | 0.444 | 0.603 | 1, 0 (1.000) | 5, 0 (0.062) |
| Qwen3-8B (anchor) | Qwen3-32B | gold | 0.556 | 0.619 | 0.587 | 0.762 | 4, 0 (0.125) | 6, 4 (0.754) |
| Qwen3-8B (anchor) | Qwen3-8B | retrieved | 0.524 | 0.556 | 0.460 | 0.683 | 2, 0 (0.500) | 6, 0 (0.031) |
| Qwen3-8B (anchor) | Qwen3-8B | gold | 0.635 | 0.683 | 0.651 | 0.841 | 4, 1 (0.375) | 6, 4 (0.754) |
| OLMo-2-7B-Instruct | Qwen3-32B | retrieved | 0.413 | 0.476 | 0.444 | 0.635 | 4, 0 (0.125) | 8, 6 (0.791) |
| OLMo-2-7B-Instruct | Qwen3-32B | gold | 0.444 | 0.508 | 0.317 | 0.667 | 4, 0 (0.125) | 13, 1 (0.0018) |
| OLMo-2-7B-Instruct | Qwen3-8B | retrieved | 0.460 | 0.508 | 0.476 | 0.698 | 4, 1 (0.375) | 9, 7 (0.804) |
| OLMo-2-7B-Instruct | Qwen3-8B | gold | 0.524 | 0.571 | 0.413 | 0.730 | 4, 1 (0.375) | 11, 1 (0.0063) |
| Qwen3.5-9B | Qwen3-32B | retrieved | 0.460 | 0.508 | 0.524 | 0.587 | 3, 0 (0.250) | 1, 2 (1.000) |
| Qwen3.5-9B | Qwen3-32B | gold | 0.540 | 0.635 | 0.651 | 0.746 | 6, 0 (0.031) | 5, 6 (1.000) |
| Qwen3.5-9B | Qwen3-8B | retrieved | 0.508 | 0.540 | 0.524 | 0.698 | 2, 0 (0.500) | 1, 0 (1.000) |
| Qwen3.5-9B | Qwen3-8B | gold | 0.603 | 0.619 | 0.667 | 0.794 | 4, 3 (1.000) | 5, 8 (0.581) |

Intervals for every accuracy and difference are in `tables.md`. On 63 questions, a single
question moves accuracy by 0.016, and the 95% question-bootstrap intervals of accuracy are about
±0.13 wide.

**(a) Other readers, primary judge.**
- **Direction.** Nonabstain-BM25 is at or above BM25 top 4 in every cell, and the rule never
  loses a question under Qwen3-32B. c = 0 in all six reader-by-arm cells:
  - OLMo-2: 4 and 4 gained;
  - Qwen3.5-9B: 3 and 6;
  - the anchor: 1 and 4.
- **Separation.** On the retrieved arm, the arm of H-C, no cell reaches p ≤ 0.05:
  - OLMo-2: 4 against 0, p = 0.125;
  - Qwen3.5-9B: 3 against 0, p = 0.25.
  The only separated cell is Qwen3.5-9B on the gold arm (6 against 0, p = 0.031).
- **The development split cannot separate this rule even for AM1's own reader.** The anchor gains
  1 question against 0 here, where the held-out registration found 39 against 0 over 347
  questions. With c = 0, the exact test needs b ≥ 6 to reach p ≤ 0.05.
- So, for OLMo-2 and Qwen3.5-9B, the development data show H-C's direction, with no loss under the
  primary judge, and do not separate it from zero.

**(b) The second judge.**
- **Losses appear.** Under Qwen3-8B the rule loses questions: c = 1 in three cells and c = 3 in
  one (Qwen3.5-9B, gold). Summed over readers and arms it is 20 gained against 6 lost, against 22
  against 0 under Qwen3-32B.
- **Every one of the 6 losses is a pool whose BM25 top-4 reply abstained** and that the second
  judge called correct (`per-table.json.gz`). This follows from the rule: it leaves BM25 top 4
  only when top 4's reply abstains, so it can lose only on an abstention judged correct.
- **How often each judge accepts abstentions.**
  - Qwen3-8B called 335-513 of the abstaining 4-subset replies correct in each reader-by-arm cell,
    14-20% of them.
  - Qwen3-32B called 0-8 correct, and 8 is the most (Qwen3.5-9B, retrieved).
- So under the second judge the rule's gains shrink or vanish:
  - Qwen3.5-9B on the gold arm: 4 against 3;
  - every other cell keeps b > c, and none is separated.

**Nonabstain-BM25 against all 8 (descriptive).** It depends on the reader:
- **OLMo-2, gold arm.** It is ahead (13 against 1 and 11 against 1, p ≤ 0.05 under both judges).
  OLMo-2 with all 8 gold-arm memories is right on only 0.317 (Qwen3-32B).
- **Anchor, retrieved arm.** It is ahead (5 against 0 and 6 against 0), as AM1d found.
- **Qwen3.5-9B.** All 8 is equal or better in every cell (1 against 2, 5 against 6, 1 against 0, 5
  against 8). For this reader BM25 top 4 is below all 8, by 0.063 (retrieved) and 0.111 (gold)
  under Qwen3-32B.

## Abstention and the stop rule

| Reader | Arm | 4-subset replies abstaining | BM25 top 4 abstains | every 4-subset abstains | rule leaves top 4 | reads: median, mean, p90 |
|---|---|---|---:|---:|---:|---|
| Qwen3-8B | retrieved | 2,396 of 4,410 (54.3%) | 17 | 10 | 7 | 1, 12.35, 70 |
| Qwen3-8B | gold | 2,602 (59.0%) | 15 | 8 | 7 | 1, 11.32, 70 |
| OLMo-2 | retrieved | 2,234 (50.7%) | 20 | 5 | 15 | 1, 7.71, 10 |
| OLMo-2 | gold | 2,483 (56.3%) | 17 | 5 | 12 | 1, 7.05, 5 |
| Qwen3.5-9B | retrieved | 2,464 (55.9%) | 19 | 11 | 8 | 1, 13.83, 70 |
| Qwen3.5-9B | gold | 2,541 (57.6%) | 18 | 8 | 10 | 1, 11.00, 70 |

- **All three readers abstain on about half of the 4-subsets.** That gives the rule something to
  act on.
- **The rule leaves BM25 top 4 in 7-15 pools per cell.** Of OLMo-2's 15 switches on the retrieved
  arm, 4 turn a wrong answer right (Qwen3-32B) and 11 stay wrong.
- **Reads.** The stop rule reads one 4-subset for the median pool. Its mean, 7-14, is dominated
  by the pools in which every 4-subset abstains (5-11 per cell), which read all 70.
- **The four patterns cover these readers' abstentions** (`posthoc.json`, post hoc).
  - Of the flagged replies, at least 98.9% match `i_dont_know` first, for every reader.
  - Among unflagged replies, 2 (Qwen3-8B), 6 (OLMo-2) and 29 (Qwen3.5-9B) of about 3,800-4,100
    match a broader post hoc list of abstention-like phrases. The primary judge called none of
    them correct.
  - No unflagged normalized reply recurs in 5 or more questions.

## What this does not show

- **Anything confirmatory.** There are 63 development questions and no registration. The rule was
  chosen on development data (AM1d), and these are the same questions.
- **That H-C holds or fails for OLMo-2 or Qwen3.5-9B.** Their retrieved-arm results (4 against 0
  and 3 against 0) are not separated from zero. The anchor shows that this split cannot separate
  the rule even for the reader whose held-out result was 39 against 0. A held-out run would need
  new reader passes, about 49,000 requests per reader.
- **Anything about other judges or about the second judge's correctness.**
  - The second judge's losses rest on it calling abstentions correct.
  - Its hand-check agreement in the pilot was 109 of 120 (κ 0.82), against 117 of 120 for
    Qwen3-32B.
  - For the anchor cells the second judge is the reader's own model.
- **Bit-exact replay for the new readers.** OLMo-2 ran batch-invariant through the Transformers
  backend and was not replayed. Qwen3.5-9B ran in default mode, which vLLM 0.31.0 requires for
  GDN layers, and its replies may change with batching.
- **Other prompts, retrievers, pool sizes, budgets or model sizes.** Every reader got AM1's
  prompt with its "I don't know" instruction. A prompt without that instruction would change the
  abstention rate the rule relies on.
- **Why the readers abstain where they do**, or why OLMo-2 does worse with all 8 gold-arm
  memories.
- **One reader per family.** Only one non-Qwen family was run, at one size.

## Deviations and notes

- **Qwen3.5-9B ran in default mode.** The config's batch-invariant step failed at engine start,
  and its declared fallback ran in default mode. Cost: one engine start, 44 s. The fallback step
  for OLMo-2 was not needed.
- **The anchor's engine** is AM1's eager batch-invariant reader engine, unchanged; the config
  checks it.
- **CPU work outside Slurm.** The capsule, extract, analyze, post hoc diagnostics and host tests
  ran on the login node outside Slurm, for seconds each, as in AM1.
- **Post hoc (`ops/am3-posthoc.py`, `posthoc.json`).** These were added after the declared
  outputs were read, and they decide nothing:
  - the judge replay at the item level;
  - the abstention-pattern coverage.
  The pooled sums over arms in the text (22 against 0, 20 against 6) are descriptions, not tests:
  the two arms share their questions.
- **Directory date.** The directory carries the orchestrator's date (2026-10-16). Everything ran
  on 2026-10-15 UTC.

## Reproduce

Host steps, in `ops/` (`jobs.log` has the times):
1. `am3-fetch-olmo2.sh`.
2. `am3-checkout.sh`: a clean clone of `18e8f125` from a git bundle. The `git archive` SHA-256,
   `e30fc703...`, equals the Mac's.
3. `am3-capsule.sh`: capsule `b7ea3454...`.
4. `am3-selftest-cpu.sbatch`, pre-image and post-build.
5. `am3-build-vllm-overlay.sh`.
6. `am3-submit-main.sh`.
7. `am3-analyze.sh 18e8f125 1466`: extract, analyze twice (byte-identical) and the tests (29
   passed).
8. `am3-posthoc.py`.
9. `am3-stage-evidence.sh`.

In short, from the clean checkout on the host:

```bash
R=~/cotcodec-runs/stage0/am3-reader-replication; P=~/cotcodec-runs/stage0/am1-study/runs
uv run --locked --offline python scripts/memcredit_am3.py extract --run-dir $R/runs/main/1466/am3 \
    --evidence $P/main/1411/study-artifact.json --private-dir $R/private-18e8f125 \
    --pilot-run-dir $P/main/1411/am1 --pilot-eager-run-dir $P/eager/1441/am1
uv run --locked --offline python scripts/memcredit_am3.py analyze \
    --features $R/private-18e8f125/features.json.gz --output-dir $R/out-18e8f125-a
```

- The host-only features file (per-mask labels, abstention flags, normalized-reply digests; no
  text) has SHA-256 `67780c98...`.
- The outputs' SHA-256:
  - `results.json`: `7988abfb...`;
  - `per-table.json.gz`: `0fc5635b...`;
  - `tables.md`: `af026a73...`.
- The tests (`tests/test_memcredit_am3.py`, 29) run on toy data without a GPU.

## Files

- `results.json`, `tables.md` and `per-table.json.gz`: the outputs of `analyze`, text-free.
  - Per reader, judge and arm: every accuracy with its interval, the paired comparisons,
    abstention counts and stop-rule reads.
  - The anchor comparisons and the judge validation.
  - Per pool: masks, the 0/1 outcomes under both judges, and the reads.
- `posthoc.json`: the post hoc diagnostics.
- `logs/`: the extract summary (validation counts, digests), the analyze log with output digests,
  and the host test log.
- `jobs/1466-main/`: the lane records.
  - `am3/` holds the driver summary and environment, per-step records and progress logs,
    per-pass metadata, the SHA-256 of every raw pass file, worker logs, and a text-free copy of the
    judge items.
- `builds/`, `selftests/`, `manifests/`: the image build, the two CPU selftests (prompt lengths
  and digests per reader, architecture resolution), and the lane manifest with its dry run.
- `models/`: the OLMo-2 fetch receipt and the fetch lane's record.
- `ops/`: every host script as it ran, `jobs.log` and `preflight.log`.
- Code: `scripts/memcredit_am3.py`, `experiments/am3/am3-reader-replication-v1.yaml`,
  `tests/test_memcredit_am3.py`, and the registry entry in `models/registry.yaml`.
- Raw outputs stay on the host under `~/cotcodec-runs/stage0/am3-reader-replication/`:
  `runs/main/1466/am3/` holds the token ids, log-probs, reply texts and judge items.
