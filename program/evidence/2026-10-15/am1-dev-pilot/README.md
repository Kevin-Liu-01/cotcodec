# AM1 development-set pilot (exploratory): exact credit tables, credit-rule regret, placebo arms and attention signals on 63 LongMemEval-S questions

**EXPLORATORY.** This is AM1's development-set pilot (D104; dossier entry 3 of
`program/evidence/2026-10-14/question-sweep-memory-gpu/dossier.md`, with AM2's placebo arms and
AM6's internal signals folded in), after Step 0 (D107; `program/evidence/2026-10-15/am1-step0/`).
It ran on the development split only: 63 of LongMemEval-S's 416 usable questions, drawn with seed
42 and stratified by type. The other 353 are held out for the confirmatory run drafted as
`program/preregistrations/am1-memory-credit-v1.md` (DRAFT, not frozen, not in the ledger). No
decision rule applies to anything below; every number describes these 63 questions, this reader
and judge, on two H100s of this node.

- Config: `experiments/am1/memcredit-study-v1.yaml` (the pilot),
  `experiments/am1/memcredit-study-v1-aa.yaml` (the cross-GPU A/A diagnostic) and
  `experiments/am1/memcredit-study-v1-eager.yaml` (the eager replay check). Split:
  `experiments/am1/memcredit-split-v1.json` (ids and digests only). The draft registration's
  config is `experiments/am1/am1-memory-credit-v1.yaml`.
- Code: `harness/memcredit_study.py`, `scripts/memcredit_study_prepare.py` (split and artifact),
  `scripts/memcredit_study.py` (the GPU job), `scripts/memcredit_analyze.py` (analysis, hand-check
  sample, A/A report, power); Step 0's `harness/memcredit.py` and `scripts/memcredit_step0.py`
  unchanged. Tests: `tests/test_memcredit_study.py` (35) with `tests/test_memcredit.py` (30).
- GPU use: see "What ran". The pilot's cap was 2 physical GPU-h, builds included.

## Main takeaways (exploratory)

1. **Compiled batch-invariant replay is exact only for the same compiled kernels; eager mode
   replays exactly.** The reader's GPU-1 replicate in job 1411 (its own fresh compile, shuffled
   order) matched the GPU-0 pass in tokens for 33,463 of 34,524 requests (96.93%, 95% CP [96.74%,
   97.11%]) and in log-prob bits for only 4,614; judged correctness differs on 87 of the 34,399
   requests whose two replies are both judged (0.25%, [0.20%, 0.31%]), in 41 of 126 tables. The
   A/A diagnostic (job 1435) and the eager check (job 1441) located the cause. The odd pass out
   was job 1411's GPU-0 compile: the three other fresh compiles (job 1411's GPU 1 and both of job
   1435's) agree with each other bit for bit, as do two engines running a copy of another
   engine's compile cache; job
   1411's two compile caches differ in inductor's timing-based autotune records (for one
   reduction kernel `R0_BLOCK` 2048 against 4096, both timed at 25 ms). In eager mode
   (`enforce_eager`, no torch.compile) the reader replayed bit-exactly across the two GPUs, two
   processes, two jobs, canonical against shuffled order and an in-engine replicate (8,768 of
   8,768 in every comparison), at 1.06x the compiled pass's wall time; the Qwen3-32B judge was
   bit-exact in both modes (1,738, 627 and 573 of 573). The pilot's tables come from job 1411's
   GPU-0 pass, the odd compile: exact for that engine, and 0.25% of their cells differ from the
   typical compile's. The draft registration runs every engine eager.
2. **The judge.** Qwen3-32B in batch-invariant mode with LongMemEval's own answer-check prompt
   ([`get_anscheck_prompt`, evaluate_qa.py at 9e0b455f](https://github.com/xiaowu0162/LongMemEval/blob/9e0b455f4ef0e2ab8f2e582289761153549043fc/src/evaluation/evaluate_qa.py),
   MIT; ported word for word and checked against the archived port) agrees with a blind hand
   check of 120 judged replies on 117 (97.5%, [92.9%, 99.5%], Cohen's kappa 0.95; 2 false yes,
   1 false no). Qwen3-8B with the same prompt: 109 of 120 (kappa 0.82, 11 false yes). Step 0's
   containment rule: 87 of 120 (kappa 0.45). On the reference answers as responses the judge says
   yes on 58 of 58 non-preference questions and on 0 of 5 preference rubrics (a rubric is not a
   response, so that control does not apply to them); on "I don't know." it says no on 63 of 63.
   The hand check was done by the agent, not by a human (below).
3. **The tables are mostly not AND/OR.** Of the 126 exact 256-subset tables, 37 are constant
   (25 retrieved, 12 gold-augmented; all constant tables are 0). Among the 89 non-constant ones
   the census finds 53 non-monotone (some memory helps on some sets and hurts on others), 22
   single-memory, 8 AND, 2 OR and 4 other monotone tables. A non-gold memory matters somewhere in
   58 of the 89.
4. **H1 (descriptive).** The order >= 2 share of the uniform-measure Fourier variance is 0.374
   (question-clustered 95% bootstrap [0.301, 0.454]) over the 89 non-constant tables; it exceeds
   each table's AND/OR baseline at its gold count, 1 - m/(2^m - 1), by 0.121 [0.046, 0.198]
   (retrieved 0.153 [0.067, 0.241]; gold 0.098 [0.013, 0.184]).
5. **H2: per-memory credit picks materially worse keep sets.** At B = 4 kept of 8, the expected
   regret of the top-4 set against the exact optimum (mean over tie-breaks and non-constant
   tables; in judged correctness) is, on the retrieved pool: leave-one-out (Hindsight-PRM's
   one-shot deletion) 0.214 [0.121, 0.316], suboptimal in 53% of tables; permutation Shapley with
   16 permutations (MeClear) 0.097 [0.030, 0.177]; SNIPW over 64 random exposures (CMP) 0.070
   [0.018, 0.140]; retrieval rank 0.132 [0.026, 0.237]; raw attention mass 0.263 [0.132, 0.395];
   exact Shapley 0.079 [0, 0.184]; a random keep set 0.576. The gold-augmented pool agrees
   (0.200, 0.124, 0.078, 0.235, 0.255, 0.078, 0.654). Exact Shapley's own regret is the
   additive-credit floor: no per-memory score reaches the optimum on the non-monotone tables.
6. **AM2's placebo arms.** Deleting a gold memory flips judged correctness in 40.5% of cases and
   swapping its text for a length- and rank-matched irrelevant turn in 39.8%; 70.8% [56.0%,
   83.9%] of the gold deletion labels survive the placebo control (both swaps reproduce the label
   and neither reorder of the pool flips the outcome). Non-gold deletion labels are rare (4.6% of
   non-gold memories) and mostly do not survive (16.7% [3.0%, 34.1%]). A content-free reorder of
   the full pool flips judged correctness in 13.1% [7.9%, 18.7%] of pools.
7. **AM6's attention signal.** At predicting which memories are necessary in the full pool
   (leave-one-out > 0, pools answered correctly), raw attention mass from the reply tokens has
   AUROC 0.868 [0.819, 0.917] against retrieval rank 0.852, question overlap 0.830 and the
   overlap with the reader's own reply 0.888 [0.846, 0.926]. Heads chosen on the other fold of
   questions (cross-fitted against exact Shapley) reach 0.935 [0.897, 0.973].
8. **Power for the held-out run** (353 questions, about 213 non-constant retrieved tables), by
   resampling the development questions: at the development effects, the draft's rule
   (MISSPECIFIED when the 99% lower bound of the B = 4 regret exceeds 0.05) fires for leave-one-out
   with probability 1.00 (0.999 at half the effect), raw attention 1.00, retrieval rank 0.93,
   permutation Shapley-16 0.77 and SNIPW-64 0.13; 99% half-widths are 0.035-0.077.

## What ran

| Job | What | GPUs | Run time | GPU-h | Outcome |
|---|---|---:|---:|---:|---|
| 1404 | pre-image CPU selftest: source `b94672f4` mounted into Step 0's overlay `sha256:51540dd5` | 0 | about 1 min | 0 | pass: 34,524 reader prompts (109-1,570 tokens) fit, 126 of 126 pools' memory spans, judge prompts fit, attention code on Qwen3-0.6B-Base on CPU |
| 1405 | cotcodec-vllm cu129 overlay build, commit `b94672f4` | 1 | 00:01:07 | 0.0186 | COMPLETED, `sha256:13e85fa7c4d12267560caea33ad81e7b89fd6aeae9555f87bd6dd9e8aed664a1` |
| 1408 | post-build CPU selftest of the baked `b94672f4` | 0 | about 1 min | 0 | pass |
| 1411 | the pilot: phases reader, judge, extra on 2 H100 | 2 | 00:26:45 | 0.8917 | COMPLETED 0:0, every phase and worker complete |
| 1432 | overlay build, commit `5aa1f35a` (the A/A diagnostic's driver) | 1 | 00:01:02 | 0.0172 | COMPLETED, `sha256:93f45a6e24cb3d598f1d604b060b8678bf174c80cbdc559eb6e40590823d0529` |
| 1435 | the A/A diagnostic (`memcredit-study-v1-aa`): phases fresh, swapcache, eager, judge on 2 H100, first 16 development questions | 2 | 00:11:04 | 0.3689 | COMPLETED 0:0, every phase complete |
| 1436 | post-build CPU selftest of the baked `5aa1f35a` | 0 | about 1 min | 0 | pass |
| 1439 | overlay build, commit `a3365b8f` (the eager check's config) | 1 | 00:01:09 | 0.0192 | COMPLETED, `sha256:a821739ed4839a8aa09d8e28e73f0182eadf9e13e19bc280e1312c0611b13c86` |
| 1441 | the eager check (`memcredit-study-v1-eager`): phases reader, judge on 2 H100, first 16 questions | 2 | 00:05:07 | 0.1706 | COMPLETED 0:0 |
| | **total** | | | **1.4862** of the 2.0 cap | |

Run times are `scontrol` RunTime. Job 1411's lane records give 00:11:53Z-00:38:37Z.

### Job 1411, phase by phase (2026-10-15 UTC)

| Phase | Worker | GPU (UUID prefix) | Engine init | Pass | Requests | Wall | Notes |
|---|---|---|---:|---|---:|---:|---|
| reader 00:12:55 | `reader-gpu0` | 0 (`b23c3b4d`) | 94.3 s | canonical | 34,524 | 221.9 s | 61% of prompt tokens from the prefix cache; 31 replies at the 64-token cap |
| | `reader-gpu1` | 1 (`34c1e8e2`) | 94.7 s | shuffled (seed 43) | 34,524 | 315.1 s | 39% from the prefix cache |
| judge 00:23:58 | `judge32-gpu0` | 0 | 141.1 s | canonical | 1,738 | 12.0 s | Qwen3-32B |
| | `judge32-gpu1` | 1 | 141.3 s | shuffled | 1,738 | 11.6 s | |
| extra 00:26:45 | `judge8-gpu0` | 0 | 94.4 s | canonical | 1,738 | 2.7 s | Qwen3-8B as a second judge |
| | `attention-gpu1` | 1 | 7.3 s load | | 126 pools | 8 s | HF eager attention, `[126, 36, 32, 8]` masses |

Both GPUs sat idle for about 15 of the 26.75 minutes while the driver read the reader passes back
(a quadratic `load_pass`, below): 0.89 GPU-h bought about 0.4 GPU-h of work.

### Images, code, models, data

| Item | Identity |
|---|---|
| Image | `cotcodec-vllm` cu129 overlay `sha256:13e85fa7...` (`builds/vllm-overlay-b94672f4-build-receipt.json`): vLLM 0.31.0 (`db9527a4`), the base `vllm/vllm-openai@sha256:b18abb2d...` as in Step 0 |
| Code | git `b94672f4daeb2b2383bf10b0d38b52d0c2bea80a`, source capsule `5866114e...` (11,999 files) for job 1411; `5aa1f35a` (capsule `a97dd19f...`) for job 1435 and `a3365b8f` (capsule `86ca0200...`) for job 1441, which change the driver and configs only. The analysis ran on the host CPU at `9ecc914c` from the raw passes, the A/A reports `aa-1435.json` and `aa-1441.json` at `a3365b8f` |
| Reader | `Qwen/Qwen3-8B` @ `b968826d`, Apache-2.0, re-verified file by file by the driver (12.1 s) against its full receipt in `cotcodec-receipts-cpu-lane` |
| Judge | `Qwen/Qwen3-32B` @ `9216db57`, Apache-2.0, the lane's model (verified by the lane before the workload) |
| Data | LongMemEval-S `xiaowu0162/longmemeval-cleaned` @ `98d7416c`, `longmemeval_s_cleaned.json` (SHA-256 `d6f21ea9...`, MIT), on the host since Step 0 (D1) |
| Split | `experiments/am1/memcredit-split-v1.json` (SHA-256 `4fa1b774...`): development 63 (TR 19, MS 18, KU 11, SSU 9, SSP 5, SSA 1), held out 353; the 416 usable ids equal Step 0's census eligible ids |
| Study artifact | `15567cf14a0c38c1f9edec1f47feceb2a6fccf116338e5957182d03f1d996ebc` (2,300,015 bytes, host only), built twice with the same digest; text-free summary `prepare/pools-summary-b94672f4.json.gz` |
| Hardware | two NVIDIA H100 80GB HBM3 (UUID prefixes `b23c3b4d`, PCI bus 97, and `34c1e8e2`, bus 98), driver 570.148.08 |

No `--trust-remote-code`. The GPUs ran vLLM, torch and transformers only; replies and verdicts are
text that nothing executes (D7).

## Design

**Usable questions and the split.** Step 0's census definition: no abstention question, every
gold turn a user turn, 1 to 6 gold turns (416 of 500; every question type kept). Per type, the
sorted ids are shuffled with `random.Random(f"42:{type}")` and the first round-half-up(15%) are
development. `scripts/memcredit_study_prepare.py artifact` refuses the held-out split unless
`am1-memory-credit-v1` is frozen in the ledger with this checkout's file and the config is the
registration's, and the GPU driver runs the pilot's configs on the development artifact only.

**Pools.** Step 0's two arms, unchanged: `retrieved`, the BM25 top 8 user turns (Okapi, k1 1.5,
b 0.75; it stands in for the dossier's MiniLM retriever), and `gold`, every gold user turn plus
distractors drawn uniformly (seed 42 per question) from the question's other user turns. One
memory is one user turn with its session date, at most 1,500 characters, in chronological order;
bit i of a mask keeps memory i. Gold turns in the pool: retrieved 0 (5 questions), 1 (25), 2 (30),
3 (3); gold 1 (19), 2 (33), 3 (7), 4-6 (4).

**AM2's placebo arms** (per pool, 18 requests besides the 256): for each slot, two swaps that keep
the slot's position and date and replace its text with a non-gold user turn of the same question
that is in neither arm's pool, matched first on length (|ln(chars ratio)| within ln 1.25, else
ln 1.5, else ln 2: 1,994, 18 and 4 of the 2,016 swaps) and then on BM25 rank (median rank gap 7);
and two reorders of the full pool (reversed; a seeded permutation, seed 43).

**Reader.** Step 0's reader unchanged: Qwen3-8B, thinking off, greedy, at most 64 new tokens,
`VLLM_BATCH_INVARIANT=1`, prefix caching on, bf16, engine seed 42, Step 0's prompt. 34,524
requests (126 pools x 274). GPU 0 ran them in canonical order; GPU 1, in a separate process with
its own compile cache, in a shuffled order (seed 43).

**Judge.** Every distinct (question, reply) of the GPU-0 pass (1,550) plus 188 validation items
(per question: the reference answer as the response, "I don't know.", and the reference answer
of another development question of the same type by a seeded derangement, seed 44) were scored by
Qwen3-32B in batch-invariant mode with LongMemEval's type-specific prompt (thinking off, greedy,
10 tokens; the label is the official rule, "yes" occurs in the reply), on GPU 0 in canonical
order and on GPU 1 shuffled; and by Qwen3-8B with the same prompt on GPU 0. A table cell's
utility is the Qwen3-32B GPU-0 label of its reply.

**Hand check.** 120 judged reader items, 60 the judge called yes and 60 no (seed 44), shuffled,
without any judge's label: question, reference answer and reply only
(`scripts/memcredit_analyze.py hand-sample`; the sample and its texts stay on the host). The
agent labelled each by the official prompt's criteria (off-by-one days tolerated for temporal
questions, an updated answer for knowledge-update, rubric use for preference) before the labels
were joined to the judges'. 12 of the 120 were borderline and are flagged in
`analysis/hand-labels.jsonl`.

**Internal signals (AM6).** Qwen3-8B in transformers with eager attention, one teacher-forced
forward per pool of the full-pool prompt plus the GPU-0 greedy reply; forward hooks on every
layer's self-attention reduce the weights to the mean mass, per head, from the positions that
predict the reply tokens onto each memory's tokens. `attention_raw` is the mean over all 36 x 32
heads; `attention_xfit` the mean over 16 heads chosen on the other fold of questions (two folds,
seed 43) by mean per-table Spearman with exact Shapley.

**Estimators** (credit per memory, then the top B by credit; regret is the best B-set value minus
the chosen set's value, averaged over tie-breaks; stochastic ones averaged over seeds 42-44):
exact Shapley and Banzhaf (256 calls), leave-one-out (9), leave-one-in (9), permutation Shapley
with 4 and 16 permutations (at most 33 and 129 distinct subsets), SNIPW over 64 random exposures
with known propensity 1/2 (64), the placebo-filtered deletion label (27), the mean swap effect
(17), retrieval rank, raw and cross-fitted attention, question overlap, overlap with the
full-pool reply, and length; a uniformly random keep set as the floor.

## Results

### A/A identity (job 1411)

| Pair | Compared | Identical replies | Identical log-prob bits | Judged-utility flips |
|---|---:|---:|---:|---|
| reader GPU 0 canonical vs GPU 1 shuffled (separate compiles) | 34,524 | 33,463 (96.93%, [96.74, 97.11]) | 4,614 | 87 of 34,399 judged (0.25%, [0.20, 0.31]); 41 of 126 tables touched |
| judge Qwen3-32B GPU 0 canonical vs GPU 1 shuffled (separate compiles) | 1,738 | 1,738 | 1,738 | 0 |

Of the 1,061 differing replies, 271 differ at token 0, so the prompt's forward pass itself
differs; where tokens agree, the largest per-reply log-prob difference has median 3e-4 and 99th
percentile 0.25. The reader's GPU-1 replies were not all judged in job 1411: a reply's label is
known when the same (question, reply) was judged by a primary judge in job 1411, 1435 or 1441,
which covers 34,399 of 34,524 (34,354 with job 1411's labels alone, 84 flips;
`analysis/aa-1411.json`).

### Where the replay difference comes from (jobs 1435 and 1441; `analysis/aa-1411.json`, `aa-1435.json`, `aa-1441.json`)

The diagnostic ran the reader on the first 16 development questions (8,768 requests per pass, 32
tables), canonical order unless noted. Judged-utility flips use every label the three jobs' primary
judges gave (1,623 distinct replies judged; no reply was given two different labels across jobs
or modes).

| Pair | What differs | Identical replies | Identical log-prob bits | Judged-utility flips |
|---|---|---:|---:|---|
| 1411 GPU 0 vs 1411 GPU 1 (shuffled), all 63 questions | compile, GPU, order | 33,463 of 34,524 | 4,614 | 87 of 34,399; 41 of 126 tables |
| 1411 GPU 0 vs 1435 fresh GPU 0 (same physical GPU `b23c3b4d`) | compile, job | 8,530 of 8,768 | 1,110 | 18 of 8,768; 10 of 32 tables |
| 1411 GPU 1 (shuffled) vs 1435 fresh GPU 0 | compile, GPU, order, job | 8,768 | 8,768 | 0 |
| 1435 fresh GPU 0 vs fresh GPU 1 | compile, GPU | 8,768 | 8,768 | 0 |
| 1435 fresh GPU 0 vs GPU 1 running GPU 0's copied compile cache | GPU | 8,768 | 8,768 | 0 |
| 1435 fresh GPU 1 vs GPU 0 running GPU 1's copied compile cache | GPU | 8,768 | 8,768 | 0 |
| 1435 eager GPU 0 vs eager GPU 1 | GPU, process | 8,768 | 8,768 | 0 |
| 1441 eager GPU 0 vs eager GPU 1 (shuffled) | GPU, process, order | 8,768 | 8,768 | 0 |
| 1441 eager GPU 0, canonical vs a shuffled replicate in the same engine | order | 8,768 | 8,768 | 0 |
| 1435 eager vs 1441 eager (GPU 0-0, 1-1, 0-1) | job | 8,768 each | 8,768 each | 0 |
| 1435 fresh GPU 0 (compiled) vs 1435 eager GPU 0 | compiled vs eager | 8,471 | 973 | 16; 8 tables |
| 1411 GPU 0 vs 1435 eager GPU 0 | odd compile vs eager | 8,480 | 992 | 20; 10 tables |
| Qwen3-32B judge, compiled: 1411 GPU 0 vs GPU 1 (shuffled); 1435 GPU 0 vs GPU 1 (shuffled) | compile, GPU, order | 1,738; 627 | 1,738; 627 | |
| Qwen3-32B judge, eager: 1441 GPU 0 vs GPU 1 (shuffled) | GPU, process, order | 573 | 573 | |

- Job 1411's two compile caches (771 files each, on the host) differ in 460 files. Among the
  inductor autotune records (`*.best_config`, 9 each), two chose differently: `XBLOCK` 2 with 2
  warps against 4 with 4 warps for one reduction, and `R0_BLOCK` 2048 against 4096 for another,
  both timed at 25 ms. A different reduction block sums in a different order, which fits the
  differences starting at the first token (271 of 1,061 replies) and the 87% of same-token
  requests whose log-prob bits differ. Which compile is "odd" is decided by timing noise during
  the engine's start; Step 0's sessions shared one cache directory, so they never recompiled
  independently.
- A copied compile cache starts the engine in 44 s instead of 97 s and replays the source
  compile exactly; eager mode starts in 29 s and its canonical pass takes 57.7-58.3 s against
  54.2-54.7 s compiled (1.06x), 66.4 s shuffled. The judge labels agree across modes on all 573
  items both modes scored.
- So the tables of the pilot are exact for job 1411's GPU-0 engine; they differ from the
  typical compile's in about 0.25% of cells, and from eager mode's in about 0.2%. The registration
  runs every vLLM engine eager.

### Judge validation and agreement (`analysis/judge.json`)

| Check | Qwen3-32B (primary) | Qwen3-8B (second) |
|---|---|---|
| reference answer as the response, non-preference questions | 58 of 58 yes | 58 of 58 |
| preference rubric as the response (not a valid positive) | 0 of 5 yes | 0 of 5 |
| "I don't know." | 63 of 63 no | 53 of 63 no (10 false yes, 7 temporal) |
| another question's reference answer | 58 of 62 no | 57 of 62 |
| hand check, 120 judged replies | 117 agree (97.5%, [92.9, 99.5]), kappa 0.95, 2 false yes, 1 false no | 109 (90.8%), kappa 0.82, 11 false yes |
| reader items, agreement with the primary | | 1,460 of 1,550 (kappa 0.86) |
| table cells, agreement with the primary | | 31,450 of 34,524 |

Of the four "another question's answer" items judged yes, three are equivalent to the reference
(5 vs 5 days; 7 days vs one week, twice) and one is a judge error (21 days vs 5.5 weeks). The
primary's two false yes in the hand check are "I don't know" for a page-count question and
"0.5 years" for "2.5 years"; its false no is a knowledge-update reply that affirms yes with a wrong
count (flagged borderline). Containment (Step 0) agrees with the hand labels on 87 of 120 (kappa
0.45) and with the primary on 31,342 of 34,524 cells.

### Census of the tables (`analysis/headline.json`, `analysis/tables.json.gz`)

| Arm | Tables | Constant (all 0) | Non-constant | u(full pool) | Non-monotone | Single | AND | OR | Monotone, mixed | Non-gold memory matters |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| retrieved | 63 | 25 | 38 | 0.444 | 23 | 8 | 2 | 2 | 3 | 28 |
| gold | 63 | 12 | 51 | 0.587 | 30 | 14 | 6 | 0 | 1 | 30 |

Every constant table is 0 (the reader never answers right from these pools); the empty pool is
never answered right. 10 of 63 questions are constant in both arms (15.9%; the dossier's kill
criterion 2 is 60%). By type, the non-monotone tables are temporal-reasoning (21), multi-session
(12), knowledge-update (12), preference (5) and single-session-user (3).

### H1: interaction share (descriptive; `analysis/h1.json`)

| Arm | Non-constant tables | Order >= 2 share | Minus AND/OR baseline at the gold count | Share above that baseline | Minus AND/OR baseline at the relevant count |
|---|---:|---|---|---|---|
| retrieved | 38 | 0.370 [0.284, 0.460] | +0.153 [0.067, 0.241] | 0.541 [0.378, 0.703] | -0.317 [-0.406, -0.227] |
| gold | 51 | 0.377 [0.289, 0.470] | +0.098 [0.013, 0.184] | 0.490 [0.353, 0.627] | -0.244 [-0.324, -0.169] |
| both | 89 | 0.374 [0.301, 0.454] | +0.121 [0.046, 0.198] | 0.511 [0.381, 0.640] | -0.275 [-0.344, -0.205] |

By class the share is 0 for single-memory tables, 1/3 for OR, 0.42 for AND (more than 1/3 when
more than two memories are required), 0.53 for non-monotone tables. The gold count understates how
many memories a table depends on (non-gold memories matter in 58 of 89), so the baseline at the
relevant count is far higher; the registration names the gold-count baseline as primary.

### H2: keep-set regret against the exact optimum (`analysis/h2.json`)

B = 4 (the dossier's headline), mean expected regret over non-constant tables with question-
clustered 95% bootstrap intervals; "suboptimal" is the share of tables with any regret.

| Estimator | Reader calls | retrieved regret | retrieved suboptimal | gold regret | gold suboptimal |
|---|---|---|---|---|---|
| exact Shapley | 256 | 0.079 [0.000, 0.184] | 0.079 | 0.078 [0.020, 0.157] | 0.078 |
| exact Banzhaf | 256 | 0.031 [0.000, 0.079] | 0.053 | 0.046 [0.000, 0.105] | 0.059 |
| leave-one-out (deletion) | 9 | 0.214 [0.121, 0.316] | 0.526 | 0.200 [0.111, 0.301] | 0.353 |
| leave-one-in | 9 | 0.383 [0.268, 0.501] | 0.605 | 0.464 [0.352, 0.580] | 0.627 |
| permutation Shapley, 4 | <= 33 | 0.156 [0.077, 0.247] | 0.474 | 0.212 [0.128, 0.302] | 0.471 |
| permutation Shapley, 16 | <= 129 | 0.097 [0.030, 0.177] | 0.211 | 0.124 [0.053, 0.208] | 0.216 |
| SNIPW, 64 exposures | 64 | 0.070 [0.018, 0.140] | 0.132 | 0.078 [0.026, 0.143] | 0.137 |
| deletion, placebo-filtered | 27 | 0.330 [0.227, 0.436] | 0.684 | 0.320 [0.213, 0.429] | 0.471 |
| swap effect | 17 | 0.255 [0.153, 0.363] | 0.553 | 0.241 [0.145, 0.345] | 0.412 |
| retrieval rank | 0 | 0.132 [0.026, 0.237] | 0.132 | 0.235 [0.118, 0.353] | 0.235 |
| attention, raw | 1 forward | 0.263 [0.132, 0.395] | 0.263 | 0.255 [0.137, 0.373] | 0.255 |
| attention, cross-fitted heads | 1 forward | 0.184 [0.079, 0.316] | 0.184 | 0.235 [0.118, 0.353] | 0.235 |
| question overlap | 0 | 0.197 [0.086, 0.320] | 0.289 | 0.227 [0.131, 0.335] | 0.353 |
| overlap with the reply | 1 | 0.204 [0.095, 0.332] | 0.263 | 0.210 [0.110, 0.313] | 0.333 |
| length | 0 | 0.303 [0.171, 0.447] | 0.316 | 0.431 [0.294, 0.569] | 0.431 |
| random keep set | 0 | 0.576 [0.494, 0.653] | 0.974 | 0.654 [0.583, 0.723] | 0.941 |

Leave-one-out loses 0.135 [0.051, 0.227] more than exact Shapley on the retrieved arm and 0.122
[0.058, 0.196] on the gold arm (paired by table); SNIPW-64 and permutation Shapley-16 do not differ
from exact Shapley detectably here. At B = 1 every exact rule, leave-one-in and permutation
Shapley-16 reach the optimum, and leave-one-out's regret is 0.173 (retrieved) and 0.095 (gold);
B = 2 and 3 are in `analysis/tables.md`. The dossier's kill criterion 3 does not fire: 27% of
non-constant tables have order-1 share >= 0.9, and leave-one-out picks the optimal B = 4 set in
57% of tables (exact Shapley 92%).

### AM2: placebo arms (`analysis/placebo.json`)

Over all 126 pools (both arms); a deletion or swap "flips" when judged correctness changes from
the full pool's.

| Memory class | Deletion flips | Swap flips | Swap flips where deletion does not | Deletion labels that survive |
|---|---|---|---|---|
| gold (220 memories) | 0.405 [0.311, 0.498] | 0.398 [0.307, 0.490] | 0.019 [0.004, 0.039] | 63 of 89: 0.708 [0.560, 0.839] |
| non-gold (788) | 0.046 [0.023, 0.072] | 0.045 [0.023, 0.070] | 0.021 [0.009, 0.036] | 6 of 36: 0.167 [0.030, 0.341] |

A deletion label survives when both swaps of that slot reproduce it and neither reorder of the
full pool changes the outcome; the reorder flips alone remove 13.1% [7.9%, 18.7%] of pools. The
swap of a gold memory is a length- and position-controlled deletion, and it agrees with plain
deletion (ratio 0.98); for non-gold memories it is a content placebo, and its flip rate equals the
deletion flip rate (ratio 0.99). The dossier's AM2 robustness rule (placebo-to-deletion ratio at
most 0.1 in both classes, fewer than 2% of labels changed) does not hold: per-memory deletion
labels on non-gold memories are mostly not content effects.

### AM6: internal signals against exact labels (`analysis/internal.json`)

| Signal | Necessity AUROC, both arms | retrieved | gold | Spearman with exact Shapley |
|---|---|---|---|---|
| attention, cross-fitted heads | 0.935 [0.897, 0.973] | 0.937 | 0.939 | 0.510 |
| attention, raw | 0.868 [0.819, 0.917] | 0.833 | 0.886 | 0.445 |
| overlap with the reader's reply | 0.888 [0.846, 0.926] | 0.860 | 0.947 | 0.572 |
| retrieval rank | 0.852 [0.812, 0.892] | 0.855 | 0.927 | 0.424 |
| question overlap | 0.830 [0.783, 0.873] | 0.822 | 0.907 | 0.537 |
| length | 0.620 [0.554, 0.683] | 0.596 | 0.650 | 0.185 |

Necessity is leave-one-out > 0 in pools the reader answers right. The best cheap baseline is 0.047
below the cross-fitted heads (the dossier's AM6 kill criterion 1 is 0.03) and above raw attention.
The chosen heads differ by fold (`analysis/xfit.json`); with 63 questions the head choice is
noisy.

### Power for the held-out run (`analysis/power.json`)

2,000 simulations per statistic; each draws the held-out number of units (353 questions times
the development rate of non-constant tables: 213 retrieved, 286 gold) with replacement from the
development values, at the observed effect and at one half and one quarter of it, with a
1,000-resample question bootstrap inside.

| Statistic (retrieved, B = 4) | Development | 99% half-width | P(MISSPECIFIED) at 1, 1/2, 1/4 of the effect | P(ADEQUATE) |
|---|---:|---:|---|---:|
| leave-one-out | 0.214 | 0.053 | 1.00, 1.00, 0.03 | 0 |
| permutation Shapley-16 | 0.097 | 0.040 | 0.77, 0.00, 0.00 | 0 |
| SNIPW-64 | 0.070 | 0.035 | 0.13, 0.00, 0.00 | 0 at 1; 0.06 at 1/4 |
| retrieval rank | 0.132 | 0.059 | 0.93, 0.10, 0.00 | 0 |
| attention, raw | 0.263 | 0.077 | 1.00, 1.00, 0.36 | 0 |
| exact Shapley (reference, not in the family) | 0.079 | 0.047 | 0.17, 0, 0 | 0 |

H1's excess over the gold-count baseline has a 95% half-width of 0.036 at the held-out size.

## What the pilot says and does not say

It says, for these 63 development questions, this reader, this judge and this node:

1. A per-memory credit rule that keep-sets by leave-one-out loses about a fifth of the answers the
   exact optimal 4-of-8 set keeps, on both pool arms, and about a seventh more than exact Shapley;
   exact Shapley itself loses about 8%, which no additive score can avoid on these tables.
2. The exact tables are dominated by non-monotone structure: memories, gold and not, help on some
   subsets and hurt on others. The dossier's O5 premise that pure AND/OR structures would make H2
   unable to fire does not describe this reader's tables.
3. Under this reader, deletion labels on non-gold memories are mostly not content effects, and a
   content-free reorder of the pool changes about one answer in eight.
4. The Qwen3-32B judge with the official prompt agrees with a blind check on 117 of 120 replies.
5. Compiled batch-invariant replay is exact for the same compiled kernels (Step 0's setting, and
   a copied compile cache across GPUs), not across independent compiles, because inductor's
   autotune can pick a different reduction block; eager-mode replay was exact in every comparison
   made, for the reader and the judge.

It does not say:

- Anything confirmatory: 63 questions, one job, no registration in force. The held-out split was
  not opened.
- Which estimator is best: the intervals overlap for SNIPW, permutation Shapley-16, Banzhaf and
  exact Shapley.
- Why the tables are non-monotone: the reader's own errors (Step 0 found it wrong on temporal
  questions even with the full pool), memories that distract, and order effects are not separated.
- Anything for other readers (thinking on, larger models), retrievers (MiniLM), memory units or
  pool sizes.
- That the hand check is a human's: the agent labelled the sample (D9's optional human spot check
  is still Kevin's).

## Problems and deviations

- **A quadratic read in `load_pass`.** The driver read each pass back by subscripting the NpzFile
  per row, which decompresses the whole array each time; reading the 34,524-request reader pass
  took about 3.5 minutes each time the driver did it (judge items, the attention worker, the
  closing A/A summary). Both GPUs idled for about 15 of 26.75 minutes. Fixed in `9c3d0db8` (each
  array read once; 0.8 s); the job's outputs are unaffected.
- **The pilot's tables come from the odd compile** (job 1411, GPU 0; above). They are exact for
  that engine; nothing was rerun, and the confirmatory design changed instead (eager mode).
- **G2c GPU jobs ran beside job 1411.** It was submitted at 00:11:52Z with no G2c GPU job queued
  or running (`ops/preflight.log`); G2c's jobs 1414 (from 00:13Z), 1418 and 1420 started while it
  ran, on other GPUs. Their timings may have been perturbed by this job's CPU and disk load, and
  this job's by theirs; neither was measured.
- **A transcription error in the hand labels, corrected.** The labels of sample positions 75 and
  76 were typed transposed relative to the agent's item-by-item notes written before the join; the
  error showed up as two disagreements with the judge, and every one of the 120 typed labels was
  then rechecked against those notes, which found no other difference. Both files are kept
  (`analysis/hand-labels.jsonl`, and the uncorrected `hand-labels-transcription-error.jsonl`); the
  analysis uses the corrected one (with the uncorrected one the primary agrees on 115 of 120).
- **The preference control.** The reference answer of a single-session-preference question is a
  rubric, so "reference answer as the response" is not a positive control for those 5 questions.
- **The dossier's MiniLM retriever** is BM25 here, as in Step 0; memory units are user turns.
- Jobs 1432-1441 were submitted with no G2c GPU job queued or running (`ops/preflight.log`); G2c's
  CPU jobs 1433 and 1442 ran beside them.
- The CPU selftests' last step (`pytest` inside the image) fails because the image has no pytest;
  the tests ran on the host checkout instead (56 at `b94672f4`, all passing), and locally at every
  commit.
- **CPU work on the login node** (split, artifact, analysis) ran outside Slurm, single-threaded,
  for seconds to a minute each, partly while G2c's GPU jobs ran.
- The host's `uv` environment uses CPython 3.14.6 for the CPU steps; the image runs 3.12.3.

## Files

- `prepare/`: the split's and the artifact's stdout, the text-free pools summary, the prepare log
  (digests; the artifact was built twice with the same digest).
- `selftests/`: the pre-image (`b94672f4` mounted) and post-build (`b94672f4`, `5aa1f35a`) CPU
  selftests.
- `builds/`: the overlay build receipts and logs, source capsule receipts (`file_manifest`
  omitted).
- `manifests/`: the jobs' manifests, dry runs and submissions.
- `jobs/1411-main/`, `jobs/1435-aa/`, `jobs/1441-eager/`: lane records; `am1/` with the driver summary, environment,
  GPU samples, worker logs, per-pass metadata (`<pass>.json.gz`: finish reasons, timing, token
  counts) and SHA-256 of every raw pass file (token ids, log-probs, reply texts and the judge
  items stay on the host), and a text-free copy of the judge items (`judge-items-public.json.gz`:
  indices, question ids, sources and reply SHA-256).
- `analysis/`: the analysis at `9ecc914c` from the raw passes: `headline.json`, `identity.json`,
  `judge.json`, `tables.json.gz` (every table's values as a 256-bit hex string whose bit m is
  u(mask m), its set-function
  summary, credits, placebo record and regrets), `h1.json`, `h2.json`, `placebo.json`,
  `internal.json`, `xfit.json`, `power.json`, `aa-1411.json`, `tables.md`; the A/A reports
  `aa-1435.json` and `aa-1441.json`; the hand labels (`hand-labels.jsonl`, used, and
  `hand-labels-transcription-error.jsonl`; no text) and the hand-check sample's SHA-256.
- `ops/`: the scripts and sbatch files run on the host, `jobs.log` and `preflight.log`.

Raw outputs stay on the host under `~/cotcodec-runs/stage0/am1-study/` (`runs/main/1411/`,
`runs/aa/1435/`, `runs/eager/1441/`); the study artifact, the dataset, the reply texts and the hand-check sample never
leave it.
