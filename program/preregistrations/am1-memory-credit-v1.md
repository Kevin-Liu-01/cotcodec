# am1-memory-credit-v1: do per-memory credit rules pick the keep set that the exact subset table says is best? (LongMemEval-S, held-out split)

**Status: DRAFT. Not frozen; there is no row for this id in
`program/preregistrations/ledger.jsonl`, and nothing in this file is a result of the held-out
split, which has not been opened.** Drafted on 2026-10-15 by the single owner of AM1 on branch
`stage0/am1-study`, after AM1 Step 0 (D107) and the development-set pilot
(`program/evidence/2026-10-15/am1-dev-pilot/README.md`; exploratory, 63 development questions).
Origin: the D103 question sweep's memory lead, AM1, with AM2's placebo arms and AM6's internal
signals folded in (D104; `program/evidence/2026-10-14/question-sweep-memory-gpu/dossier.md`,
entries 3, 5 and 6, owner check O5; `ranking.json`). The freeze is the orchestrator's, after the
checklist of section 16, by an operator who did not draft this file; a material change after the
freeze is a new experiment id.

## 1. Question

The dossier's corrected question (entry 3): on LongMemEval-S, with a reader whose outputs are
bit-exact on replay and generated answers scored by a judge, over pools of k = 8 memories:

- (a) what share of the exact set function's variance lies in interaction terms of order 2 or
  higher, against the AND/OR baseline at each question's count of required memories (descriptive,
  H1); and
- (b) how often, and by how much, do the per-memory credits that 2026 memory learners train on
  choose a worse B-of-k keep set than the exact optimum (H2, the headline):
  - one-shot deletion, leave-one-out (Hindsight Memory-PRM,
    [2608.29605](https://arxiv.org/abs/2608.29605), 2026-08-30);
  - permutation Shapley with 16 permutations (MeClear,
    [2609.09115](https://arxiv.org/abs/2609.09115), 2026-09-08);
  - SNIPW over random exposures with known propensity (CMP,
    [2610.02070](https://arxiv.org/abs/2610.02070), 2026-10-01);
  - the retriever's own rank (the deployable default);
  - attention mass on each memory (AM6; AT2, [2504.13752](https://arxiv.org/abs/2504.13752),
    2025-04-18, learns head weights for it).

Folded in as secondary readings: AM2's question (what fraction of per-memory deletion labels
survives length- and rank-matched content-placebo arms, by gold and non-gold memory) and AM6's
(does a one-pass internal signal beat cheap non-internal baselines at predicting causal
necessity).

Closest prior work, from the dossier: Nematov et al. ([2507.04480](https://arxiv.org/abs/2507.04480),
2025-07-06) compare credit estimators against exact Shapley on 100 RAG queries x 10 documents
with a log-prob utility; CMP shows memories act jointly and estimates exposure effects with SNIPW
from 80,187 calls of a closed model. This study's delta: agent-memory units on a memory benchmark,
a judged generated answer as utility, exhaustive exact tables from an open reader under
batch-invariant replay, the keep/evict decision scored against the exact optimum, SNIPW scored
against exact truth, and content-placebo controls on the deletion labels.

## 2. What it decides and what it does not

It decides, for each of the five primary credit rules on the deployable (retrieved) pool at a
budget of 4 kept of 8: MISSPECIFIED, ADEQUATE or INCONCLUSIVE (section 7). It reports H1 and
the secondary readings with intervals and fixed rules but no program decision.

It does not decide: which credit rule is best (pairwise comparisons are secondary); why tables
are non-monotone (reader errors, distraction and order effects are not separated); anything for
other readers, retrievers, memory units, pool sizes or budgets than those registered; anything
about training a memory learner on these credits.

## 3. Identity and pins

| Item | Pin |
|---|---|
| Experiment id | `am1-memory-credit-v1` (this file; the confirmatory config `experiments/am1/am1-memory-credit-v1.yaml`) |
| Data | LongMemEval-S cleaned, `xiaowu0162/longmemeval-cleaned` @ `98d7416c24c778c2fee6e6f3006e7a073259d48f`, `longmemeval_s_cleaned.json`, 277,383,467 bytes, SHA-256 `d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442`, MIT; on the host only (D1, Step 0's fetch receipt) |
| Split | `experiments/am1/memcredit-split-v1.json`, SHA-256 `4fa1b774d4131080855d668ac8f00f5cb07d49cf741f2051d5f8d96577edb3e3`; the **held-out** list: 353 ids, SHA-256 of the newline-joined ids `9305024fece35c357db9ca2d10fb06ee684a37c6b055ef3174914ce04e65dba8` (knowledge-update 61, multi-session 102, single-session-assistant 4, single-session-preference 25, single-session-user 53, temporal-reasoning 108) |
| Reader | `Qwen/Qwen3-8B` @ `b968826d9c46dd6066d109eabc6255188de91218` (Apache-2.0), full receipt in `cotcodec-receipts-cpu-lane` |
| Judge | `Qwen/Qwen3-32B` @ `9216db5781bf21249d130ec9da846c4624c16137` (Apache-2.0), full receipt in `cotcodec-receipts`; second judge Qwen3-8B as above |
| Judge prompt | LongMemEval's `get_anscheck_prompt` (src/evaluation/evaluate_qa.py at [`9e0b455f`](https://github.com/xiaowu0162/LongMemEval/blob/9e0b455f4ef0e2ab8f2e582289761153549043fc/src/evaluation/evaluate_qa.py), MIT), ported word for word as `harness.memcredit_study.JUDGE_TEMPLATES`; SHA-256 of `json.dumps(JUDGE_TEMPLATES, sort_keys=True, ensure_ascii=False)` = `2e27234d4c7d50a1fd99da3e8d3c97704a1f10cc9d52185924b6d8ece3ef71d4` (a test pins it, another checks it against the archived port `legacy/harness/memory_trials/longmemeval_judge.py`) |
| Reader prompt | Step 0's template (`experiments/am1/memcredit-step0-v1.yaml`, `prompt.user`), SHA-256 of the template text `e63a0f995fe94ee72d6dcda7462a09c20e83f86dcc8252a53cdefb1ccf6fb37c`, thinking off |
| Engine | vLLM 0.31.0 (`db9527a4`) in the cotcodec-vllm cu129 overlay built from the freeze commit, `VLLM_BATCH_INVARIANT=1`, `enforce_eager=True` (section 5), bf16, engine seed 42, prefix caching on |
| Code | the files of section 17 at the freeze commit (`git_head_at_freeze`), and the image built from that commit's source capsule |

## 4. Units, pools and requests

- **Questions**: the 353 held-out ids. A question is the unit of resampling.
- **Memory unit**: one user turn with its session date, at most 1,500 characters (longer turns cut
  with " [...]"), as in Step 0 and the pilot.
- **Pool arms** (k = 8, chronological; bit i of a mask keeps memory i):
  - `retrieved` (primary, the deployable pool): the BM25 top 8 user turns for the question (Okapi
    with Lucene's idf, k1 1.5, b 0.75, the stopword list of `harness/memcredit.py`);
  - `gold` (secondary, the identification pool): every gold user turn plus distractors drawn
    uniformly with `random.Random(f"42:{question_id}")` from the question's other user turns.
- **Placebo arms** (AM2), per pool: for each slot, 2 swaps that keep the slot's position and date
  and replace its text with a non-gold user turn of the same question that is in neither arm's
  pool, matched first on length (|ln chars ratio| <= ln 1.25, else ln 1.5, else ln 2, else none)
  then on BM25 rank, ties by length gap, session and turn; and 2 reorders of the full pool
  (reversed; `random.Random(f"43:{question_id}:{arm}")`).
- **Requests**: per pool 256 subsets + 16 swaps + 2 reorders = 274; 353 x 2 x 274 = 193,444
  reader requests per pass.

## 5. Reader, judge, internal signals

- **Reader**: greedy, at most 64 new tokens, stop at `<|im_end|>`, sampled-token log-prob
  returned, thinking off, Step 0's prompt.
- **Judge**: every distinct (question, stripped reply) of the primary reader pass, plus the
  validation items (per question: the reference answer as the response, "I don't know.", and the
  reference answer of another held-out question of the same type by a seeded derangement, seed
  44), scored by Qwen3-32B in batch-invariant mode, greedy, 10 tokens, thinking off, with the
  type's template; label = "yes" occurs in the case-folded reply (the official rule). A cell's
  utility u(S) is that label for its reply. Qwen3-8B scores the same items as a second judge.
  The pilot validated the judge in compiled mode; on the 573 items that both the compiled
  (job 1435) and the eager (job 1441) judge scored, no label differs.
- **Internal signals**: Qwen3-8B in transformers (the image's), eager attention, one
  teacher-forced forward per pool of the full-pool prompt plus the primary pass's greedy reply;
  per layer and head, the mean attention mass from the positions that predict the reply tokens
  onto each memory's tokens. `attention_raw` averages all heads; `attention_xfit` averages the 16
  heads with the highest mean per-table Spearman correlation with exact Shapley on the other fold
  of questions (two folds by `random.Random(43)` over sorted ids).
- **Replay**: every vLLM engine (reader and judges) runs in batch-invariant mode with
  `enforce_eager=True` (no torch.compile, no CUDA graphs). The pilot found that compiled
  batch-invariant replay is exact only for the same compiled kernels: inductor's timing-based
  autotune picked a different reduction block (`R0_BLOCK` 2048 against 4096) in one of four fresh
  compiles of the reader, which changed 3.1% of replies and 0.25% of judged cells against the
  other three. Eager passes were bit-exact in every comparison made (two GPUs, separate processes,
  two jobs, canonical against shuffled order, an in-engine replicate: 8,768 of 8,768 requests each
  for the reader, 573 of 573 for the judge), at 1.06x the compiled reader pass's wall time
  (`program/evidence/2026-10-15/am1-dev-pilot/README.md`, jobs 1435 and 1441). Eager mode is the
  dossier's "one configuration repair" (kill criterion 1). The tables come from the GPU-0 reader
  pass (canonical order); the GPU-1 pass (another process, shuffled order) is the A/A replicate,
  and the judge runs the same way.

## 6. Estimands

For a non-constant table u: {0,1}^8 -> {0, 1} and a budget B, let OPT_B = max over |S| = B of
u(S). A credit rule gives each memory a score; its keep set is the top B by score. Its **regret**
is OPT_B minus u(keep set), averaged uniformly over every keep set the rule can return when
scores tie (`harness.memcredit.keep_set_regret_range`, `mean`). For rules with random draws
(permutation Shapley, SNIPW), the regret is averaged over draws with seeds 42, 43, 44
(`random.Random(f"{seed}:{question_id}:{arm}:{rule}")`).

- **E1 (H1)**: per non-constant table, the uniform-measure Fourier variance share at order >= 2
  minus the AND/OR baseline 1 - m/(2^m - 1), m the number of gold memories in the pool (tables
  with m = 0 have no baseline and are left out of E1); averaged over tables, per arm.
- **E2 (H2, primary)**: for each primary rule r in {leave-one-out, permutation Shapley-16,
  SNIPW-64, retrieval rank, raw attention}, R_r = mean regret at B = 4 over the non-constant
  tables of the retrieved arm.
- **E3 (secondary)**: the same at B = 1, 2, 3 and on the gold arm; the share of tables with any
  regret; R_r minus exact Shapley's regret, paired by table; and the other rules of the pilot
  (exact Shapley and Banzhaf, leave-one-in, permutation Shapley-4, the placebo-filtered deletion
  label, the swap effect, cross-fitted attention, question overlap, overlap with the full-pool
  reply, length, a random keep set).
- **E4 (AM2)**: per memory class (gold, non-gold), over all pools: the deletion flip rate
  (u(full) differs from u(full minus i)), the swap flip rate, the swap flip rate where deletion
  does not flip, and the share of nonzero deletion labels that survive (both swaps reproduce the
  label and neither reorder changes u(full)); and the reorder flip rate per pool.
- **E5 (AM6)**: the AUROC of each signal at predicting necessity (leave-one-out > 0) over the
  memories of pools with u(full) = 1, and its mean per-table Spearman correlation with exact
  Shapley.

Intervals are percentile intervals from 4,000 bootstrap resamples of questions with replacement
(`harness.memcredit_study.cluster_bootstrap`, numpy `default_rng(42)`; for AUROC, 1,000 resamples
in `scripts/memcredit_analyze.py`), 95% unless stated.

## 7. Hypotheses and decision rules

**H1 (descriptive).** Interactions beyond the AND/OR structure of the required memories carry
variance: E1 > 0. Reported with its 95% interval per arm and with the census of structure classes
(constant, single, AND, OR, monotone-mixed, negative, non-monotone; `structure_class`). No
decision follows from H1: an AND or OR of m memories already puts 1 - m/(2^m - 1) of the variance
at order >= 2 (O5), so H1 can only say how far the tables are from those pure forms.

**H2 (primary).** For each primary rule r, with a 99% interval for R_r (Bonferroni over the five
rules, family-wise 95%):

- **MISSPECIFIED** if the lower bound exceeds 0.05: keep sets chosen by r lose, relative to the
  exact optimum, more than one correct answer in twenty non-constant questions;
- **ADEQUATE** if the upper bound is below 0.02;
- **INCONCLUSIVE** otherwise.

The headline is leave-one-out's verdict; the program reading is "per-memory deletion credit is
misspecified for keep/evict decisions on this benchmark" if it is MISSPECIFIED and "adequate" if
ADEQUATE. Why these thresholds: 0.05 is below exact Shapley's regret in the pilot (0.079, the
best any per-memory score achieved there) and about a tenth of a random keep set's (0.576); a
rule above it gives up more than one answer in twenty that the exact table shows a better keep
set would keep. 0.02 is about ten times the share of table cells whose judged outcome changes
when only the kernels' numerics change (0.18-0.25% in the pilot, between compiled variants and
between compiled and eager mode), the smallest regret the tables resolve with a margin. The
verdicts on the gold arm and at B = 1, 2, 3 are reported with the same rules as secondary
readings.

**Secondary readings (no program decision).**

- AM2 (E4), the dossier's rule: the labels are ROBUST if the swap-to-deletion flip ratio is at
  most 0.1 for non-gold memories and fewer than 2% of nonzero deletion labels fail the placebo
  control; otherwise NOT ROBUST. (For gold memories the swap removes the content, so its ratio to
  deletion is expected near 1 and is reported, not judged.)
- AM6 (E5), the dossier's rules: INTERNAL SIGNALS ADD NOTHING if the best cheap baseline (retrieval
  rank, question overlap, overlap with the reply, length) is within 0.03 AUROC of the best
  attention signal; NONE PREDICTS NECESSITY if every signal is below 0.65.

## 8. Validity gates and kill criteria

Each gate is evaluated before H2 is read; a failed gate is reported with its numbers and the
decision it suspends.

- **G1, replay** (dossier kill criterion 1): the GPU-1 reader replicate must give the same
  tokens as the GPU-0 pass for every one of the 193,444 requests, and the GPU-1 judge replicate the same tokens for
  every judge item (log-prob bits are reported, not gated). Any differing reply means the repair
  did not hold: the dossier's kill criterion 1 fires, H2 is not read, and the run is reported as
  descriptive with the differences at the token, log-prob-bit and judged-utility levels.
- **G2, judge**: on the held-out validation items the primary judge says yes to at least 95% of
  reference answers of non-preference questions and no to at least 95% of "I don't know."; and a
  fresh blind hand check of 120 judged held-out reader items (60 judged yes, 60 no, seed 44;
  `scripts/memcredit_analyze.py hand-sample`), labelled from question, reference answer and reply
  alone before any join, gives Cohen's kappa >= 0.80 with the primary judge, with its 95% interval
  reported. A human labeller is preferred (D9); if the agent labels, the report says so. If G2
  fails, H2's verdicts are reported as judge-dependent and no program decision follows.
- **K2, constant tables** (dossier kill criterion 2): if u is constant on all 256 subsets of both
  arms for more than 60% of held-out questions, H2 is not read (pilot: 15.9% of development
  questions).
- **K3, interactions do not matter** (dossier kill criterion 3): if at least 90% of non-constant
  tables have order-1 Fourier share >= 0.9 and both leave-one-out and exact Shapley pick an
  optimal B = 4 set in at least 95% of non-constant tables, the study ends with a short negative
  note (pilot: 27%; 57% and 92%).
- **K4, coverage**: if fewer than 150 non-constant retrieved tables remain (the power of section 9
  assumes about 213), H2 is reported as underpowered; its rules still apply.

## 9. Operating characteristics (simulated from the development pilot)

`scripts/memcredit_analyze.py power` (`program/evidence/2026-10-15/am1-dev-pilot/analysis/power.json`):
2,000 simulations per statistic, each drawing the held-out number of units (353 questions times
the development rate of non-constant tables, 0.603 retrieved and 0.810 gold: 213 and 286) with
replacement from the 63 development questions' values, at the development effect and at 1/2 and
1/4 of it, with a 1,000-resample bootstrap inside, applying the rules of section 7.

| Rule (retrieved, B = 4) | Development R | 99% half-width | P(MISSPECIFIED) at 1, 1/2, 1/4 | P(ADEQUATE) at 1/4 |
|---|---:|---:|---|---:|
| leave-one-out | 0.214 | 0.053 | 1.00, 1.00, 0.03 | 0 |
| permutation Shapley-16 | 0.097 | 0.040 | 0.77, 0.00, 0.00 | 0.00 |
| SNIPW-64 | 0.070 | 0.035 | 0.13, 0.00, 0.00 | 0.06 |
| retrieval rank | 0.132 | 0.059 | 0.93, 0.10, 0.00 | 0 |
| attention, raw | 0.263 | 0.077 | 1.00, 1.00, 0.36 | 0 |

Readings: the design is near-certain to call leave-one-out MISSPECIFIED if its true regret is
half the development estimate or more, and cannot call any rule ADEQUATE unless its true regret is
below about 0.01; a rule whose regret lies between 0.02 and about 0.09 will usually be
INCONCLUSIVE. The development values come from 63 questions (38 non-constant retrieved tables),
so the effects themselves are uncertain (leave-one-out 0.214, 95% [0.121, 0.316]). H1's excess has
a simulated 95% half-width of 0.036.

## 10. Seeds

Declared in the config: `[42, 43, 44]`. 42: the split (already drawn), the gold arm's
distractors, the engine seed, the bootstrap; 43: the reorder placebo, shuffled pass orders, the
cross-fitting folds, the power simulation; 44: the validation derangement and the hand-check
sample. Permutation Shapley and SNIPW use all three (averaged). No unseeded randomness.

## 11. Compute plan and caps

- One image build from the freeze commit's source capsule (about 1 minute on 1 H100), then
  one job on 2 H100 (`experiments/am1/am1-memory-credit-v1.yaml`, `job`): the reader phase about
  25 minutes (193,444 eager requests per pass at the pilot's eager rates, 152 requests/s canonical
  and 132 shuffled), the judge phase about 3 minutes (about 9,800 items), the extra phase about 2
  minutes. Expected about 1.1 physical GPU-h.
- Caps: the job's Slurm limit is 60 minutes on 2 GPUs (2.0 GPU-h); with the build, 2.1 physical
  GPU-h in all. Under D24's 8 GPU-h line. A phase starts only with its `min_start_s` left before
  the deadline; a skipped phase is an infrastructure failure (section 13).
- The job is submitted only when no other study's GPU job that could share the node's GPUs at
  the same time is queued or running, and the preflight log records the queue.
- CPU: the analysis, the A/A report and the hand-check sample on the host CPU (minutes).

## 12. Data handling

LongMemEval-S, the study artifact (pool texts), the reader's replies, the judge items, the
hand-check sample and the joined rows stay on the host under
`~/cotcodec-runs/stage0/am1-memory-credit-v1/`. The repository gets ids, counts, hashes, labels
without text, the per-table analysis (values as 256-bit hex strings, credits, regrets), and short
quotes in the report where needed. The held-out split is opened only by
`scripts/memcredit_study_prepare.py artifact --split heldout`, which refuses unless this file's
SHA-256 equals its ledger row's.

## 13. Infrastructure failures and exclusions

- A reader or judge request that does not finish (`finish_reason` not stop or length) leaves its
  table incomplete; an incomplete table is excluded from every estimand and counted. More than 2%
  of tables incomplete in either arm voids the run (a rerun is a new job of the same registration
  with the same seeds; the void run's records are kept).
- A smoke-check failure (16 requests at the start of every pass) stops the job before data.
- A pool whose attention forward fails is excluded from E5 only, and counted.
- No question is excluded for its outcome; constant tables stay in the census and in K2 and are
  outside E1-E3 by definition (no keep decision to score).

## 14. Reported regardless of outcome

Every gate's numbers; the census; E1 per arm; R_r with 95% and 99% intervals for every rule, arm
and budget; the suboptimal shares; the paired differences against exact Shapley; E4 and E5 with
their readings; the judge validation, agreement with the second judge and with containment, and
the hand check; the A/A identities at the token, log-prob-bit and judged-utility levels; GPU-h;
every deviation.

## 15. What the development pilot fixed in this design

From `program/evidence/2026-10-15/am1-dev-pilot/README.md` (exploratory):

- The judge (Qwen3-32B, official prompt) agreed with a blind check on 117 of 120 development
  items (kappa 0.95); Qwen3-8B and Step 0's containment rule were worse (kappa 0.82, 0.45). The
  primary judge and the gate G2 follow.
- The reference-answer control does not apply to preference rubrics; G2 counts non-preference
  questions only.
- H2 can fire: 53 of 89 non-constant development tables are non-monotone, against O5's worry that
  pure AND/OR tables would make it silent. The thresholds of section 7 were set from the pilot's
  scale (random 0.58, exact Shapley 0.08, cell flips between kernel variants 0.18-0.25%), before
  any held-out data.
- Compiled batch-invariant replay, Step 0's setting, is exact only for the same compiled
  kernels (one of four fresh reader compiles autotuned a different reduction block); every vLLM
  worker now runs eager, which replayed bit-exactly in every comparison (jobs 1435 and 1441). The
  development tables came from that one odd compile; 0.25% of their judged cells differ from the
  other compiles', and 0.18-0.23% from eager mode's.
- `load_pass` read passes quadratically (fixed in `9c3d0db8`); the confirmatory job has no idle
  phase from it.

## 16. Freeze checklist

Before the freeze, by the orchestrator:

1. An independent check of this file and the code of section 17 (a fresh reviewer that did not
   draft them), and the corrections it requires.
2. The gauntlet question: the run is under 8 GPU-h and comes out of the D103 sweep (judged and
   verified there) and a pilot; whether `.claude/rules/research-gauntlet-loop.md` applies to it is
   the program's ruling.
3. Re-pin section 17 in a fill commit, and run the tests on the host checkout.
4. The ledger row by `uv run python scripts/preregister.py freeze am1-memory-credit-v1
   program/preregistrations/am1-memory-credit-v1.md`, in a commit that adds only that row (the
   freeze commit).

After the freeze and before the GPU job: build the held-out artifact from a clean clone at the
freeze commit (refused before the freeze), build the image from the freeze commit's source
capsule (it carries the ledger row the driver checks), and pass the CPU selftest on that image
with the held-out artifact mounted (it renders every request, checks every memory span and runs
the attention code on CPU). A failure there is fixed by a new registration id, not by an edit.

## 17. Code of record (at the draft commit; re-pinned at the freeze)

At the commit that adds this file (its code is `6f39ae3c`'s plus a comment in the
registration's config). The fill commit re-pins every row; a row that changes is reviewed before the
freeze.

| File | Role | SHA-256 |
|---|---|---|
| `harness/memcredit.py` | Step 0's pools, BM25, prompts, set functions (Fourier, Moebius, Shapley, leave-one-out, keep-set regret) | `ad0964d0caab382b5541b64d56a30105bc306d2286f6e62137b1eff9121dd607` |
| `harness/memcredit_study.py` | configs, split, placebo arms, request table, judge prompt and label, estimators, structure census, statistics, the held-out gate | `6381783a1fcb100d50f80328238796580c6e69332c1ba268400568aa0912789d` |
| `harness/g2_pilot.py` | lane helpers the driver uses (deadline, checkpoint marker, model verification) | `8c685425522377de9fbab92fac02aea321bb2b3bd69d82d2118c4ecea49f6599` |
| `scripts/memcredit_step0.py` | the request loop, pass files and identity comparison the driver imports | `57f2e4bbbd11bf750ff224852ba5dd19923ecb3decfde74d23a6913a7f9a7227` |
| `scripts/memcredit_study.py` | the GPU job: phases, workers (reader, judge, attention), A/A summaries | `4db1d611892403051009bf5cb9b2fa273268a36747114afe79cdac57c22579ab` |
| `scripts/memcredit_study_prepare.py` | the split and the per-split artifact (refuses held-out data unless frozen) | `fe5734a5567832d0acd531635e9d2185394f601700c51b8dc1d51422e8edb86b` |
| `scripts/memcredit_analyze.py` | the analysis, hand-check sample, A/A report and power simulation | `c3e2d3237175043eb148d1ed2f167e6243dc5a70ac647e4c7d6f5ab239f08944` |
| `scripts/fetch_open_model.py` | the reader's snapshot verification | `d995b59ece3c809edd70d6c60a78628ae5cb1ccc0ce8350cc455084d3787d29f` |
| `experiments/am1/am1-memory-credit-v1.yaml` | this registration's config | `991976bfe349d43d45bb1d83bfd891f9d4882a22017d35b683fa37da86923122` |
| `experiments/am1/memcredit-split-v1.json` | the split | `4fa1b774d4131080855d668ac8f00f5cb07d49cf741f2051d5f8d96577edb3e3` |
| `tests/test_memcredit_study.py` | 35 tests: config and seeds, split, placebo matching, requests, the judge prompt against the archived port and its digest, estimators and structure classes, statistics, driver helpers, the held-out gate, the analysis, A/A report and power on a synthetic run, the lane's admission of the commands | `7ada0955a406a5d3eaf5cda48aaadc1fc658f9c56500a53b2d640b93d5c4533f` |
| `tests/test_memcredit.py` | Step 0's 30 tests | `7d31909428c3301df905ebed13da91fb018f7b476d2f0214635477bf6c210f0f` |
| `scripts/submit_docker_research_job.py` | the lane's submitter | `660271655aa22ebd387a023e25d21e6a809c22699ec6314d9d535be74e17a994` |
| `infra/slurm/host-single-node/docker-research.sbatch` | the lane | `2a10c9c72c22ab6dd5135061ff1b9b50977a468687180353d8cd7273acbaf1ec` |
| `scripts/build_vllm_overlay_on_h100.sh` | the overlay build | `aa43283e757695384e0548d060a18b98f07a3af06f583efdb2d709f677e1a96d` |
| `scripts/create_source_archive.py`, `scripts/extract_discovery_source_archive.py` | the source capsule | `672670ca29d3254e9af90b810eef591e15dae6934612c5184a72e5d0c7e9948c`, `9b4d21a83beac8913dc06a946cf43ea31d77326e65d04957fad66d7b97d8c3cb` |

Commands of the registered run (host, from a clean clone at the freeze commit). The names in
capitals stand for host paths and digests that exist only at run time: SOURCE_JSON, the pinned
`longmemeval_s_cleaned.json`; HOST_DIR, `~/cotcodec-runs/stage0/am1-memory-credit-v1/`; RUN_DIR,
the job's run directory; ANALYSIS_DIR, the analysis output; HAND_LABELS, the blind labels file;
ARTIFACT_SHA256 and HAND_LABELS_SHA256, those files' digests as receipted and committed.

```bash
uv run --locked --offline python scripts/memcredit_study_prepare.py artifact \
  --config experiments/am1/am1-memory-credit-v1.yaml --source SOURCE_JSON \
  --split-file experiments/am1/memcredit-split-v1.json --split heldout \
  --artifact HOST_DIR/study-artifact.json --summary HOST_DIR/pools-summary.json
# the GPU job (lane manifest, 90 minutes, 2 GPUs; image built from the freeze commit's capsule):
python scripts/memcredit_study.py run --config experiments/am1/am1-memory-credit-v1.yaml \
  --seeds 42 43 44 --output-dir /outputs/am1 --allocation-minutes 90 \
  --evidence /inputs/study-artifact.json --expected-evidence-sha256 ARTIFACT_SHA256
uv run --locked --offline python scripts/memcredit_analyze.py hand-sample \
  --config experiments/am1/am1-memory-credit-v1.yaml --run-dir RUN_DIR/am1 \
  --evidence HOST_DIR/study-artifact.json --output HOST_DIR/hand-check-sample.jsonl
# (the sample is labelled blind; the labels file's SHA-256 is committed; then:)
uv run --locked --offline python scripts/memcredit_analyze.py analyze \
  --config experiments/am1/am1-memory-credit-v1.yaml --run-dir RUN_DIR/am1 \
  --evidence HOST_DIR/study-artifact.json --output-dir ANALYSIS_DIR \
  --hand-labels HAND_LABELS --hand-labels-sha256 HAND_LABELS_SHA256
uv run --locked --offline python scripts/memcredit_analyze.py aa \
  --config experiments/am1/am1-memory-credit-v1.yaml --run run=RUN_DIR/am1 \
  --pair run:reader-gpu0,run:reader-gpu1 --pair run:judge32-gpu0,run:judge32-gpu1 \
  --evidence HOST_DIR/study-artifact.json --output ANALYSIS_DIR/aa.json
```

The hand-check sample is drawn and labelled before `analyze --hand-labels` joins it to the
judges, and `analyze` refuses labels whose SHA-256 differs from the committed one.

## 18. Priors (from the pilot; for the record, not tested)

The pilot expects leave-one-out MISSPECIFIED (R about 0.2), raw attention and retrieval rank
MISSPECIFIED, permutation Shapley-16 likely MISSPECIFIED, SNIPW-64 INCONCLUSIVE; H1's excess near
+0.1; AM2 NOT ROBUST (non-gold deletion labels mostly fail the placebo control; a reorder flips
about one answer in eight); AM6 with cross-fitted heads ahead of the best cheap baseline by about
0.05 AUROC and raw attention behind it.
