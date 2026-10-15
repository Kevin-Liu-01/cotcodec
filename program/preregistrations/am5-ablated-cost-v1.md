# am5-ablated-cost-v1: is the non-abstention keep rule's cost on questions whose evidence is absent below its gain on the same questions with their evidence? (LongMemEval-S, GPU)

**Status: DRAFT, not frozen.** Drafted on branch `stage0/am5-ablated-cost` from `main` at
`9d66c4c4`, as decision D121 specifies (`program/decisions.md`). The orchestrator freezes it with
`scripts/preregister.py` after two independent pre-freeze checks (D121) and the checklist of
section 17. A material change after the freeze is a new experiment id.

This registration runs one GPU job and one image build, about 0.35 physical GPU-h, capped at 1.25
(section 11). It measures, on AM1's 347 held-out answerable questions with their evidence sessions
removed, how often the non-abstention keep rule, capped at K reads, abandons BM25 top 4's correct
abstention for an answer judged wrong, and compares that cost, question by question, with the gain
the same rule makes on the same questions' original pools. **The gain side is already known: it
was measured by `am3-nonabstain-generality-v1` and read at K = 8 by AM4, post hoc, and K = 8 was
chosen after AM4 had looked at these questions. Only the cost side is new.** Section 1 lists what
is known before anything else.

## 1. Disclosures

### 1.1 What is already known about the held-out questions, and the gain side

The 347 questions are AM1's confirmatory set (`am1-memory-credit-v1`, ledger row 23;
`experiments/am1/am1-memory-credit-v1.yaml`, `confirmatory_set`). Four studies used them, all on
their original pools (the evidence present):

- **AM1** (job 1458) ran all 256 subsets of both pool arms with Qwen3-8B and judged every distinct
  reply with Qwen3-32B and Qwen3-8B (`program/evidence/2026-10-16/am1-confirmatory/`).
- **`am1-keepset-search-v1`** (ledger row 24) confirmed the rule's gain over BM25 top 4 for
  Qwen3-8B on the retrieved arm: 39 gained, 0 lost (H-C).
- **`am3-nonabstain-generality-v1`** (ledger row 25, job 1480) ran the three readers of this
  registration on both arms of every question (71 requests per pool) and confirmed the gain for
  OLMo-2-1124-7B-Instruct (35 against 0) and Qwen3.5-9B (31 against 0), with the anchor replaying
  39 against 0. Its committed per-pool records
  (`program/evidence/2026-10-15/am3-nonabstain-generality-v1/per-table.json.gz`) hold, per reader
  and question, BM25 top 4's and the rule's judged outcome and the rule's first answering position:
  everything the gain side of this registration reads.
- **AM4** (`program/evidence/2026-10-16/am4-read-caps/`, exploratory and post hoc, CPU only) read
  those records at read caps K = 1, 2, 4, 8, 16, 26 and 70. Its gains at K = 8 are 31 (Qwen3-8B),
  27 (OLMo-2) and 26 (Qwen3.5-9B) of 347, with no loss; at K = 70 they are 39, 35 and 31. It also
  reported the costs at every K on LongMemEval-S's 30 edited abstention questions (3, 3 and 0 at
  K = 8).
- **So the gain side of the comparison is a known number.** The registered test pairs a known
  gain indicator per question with a new cost indicator per question. K = 8 is the primary cap
  because AM4 found that it keeps 77-84% of K = 70's gains at under a quarter of its mean reads
  on answerable pools and about a seventh on unanswerable ones: that choice was made after AM4
  looked at these very questions, so the gain at K = 8 is a post hoc selection, not an estimate
  free of selection. K = 70 (the registered rule without a cap) is reported as the secondary cap.
- **What no one has.** No model has seen the ablated held-out pools (section 1.2). Every cost
  figure of this registration is new.

### 1.2 What is known about the ablated held-out pools

- **The construction.** For each of the 347 questions every haystack session whose id is in
  LongMemEval's `answer_session_ids` is removed, with its date, and the BM25 top-8 user-turn pool is
  built from what remains with AM1's retrieved-arm functions (`memcredit_am5.ablate`,
  `memcredit_am3g.retrieved_pool`: `harness.memcredit` `rank_user_turns`, `memory_entry`,
  `chronological`), exactly as AM5 built its development pools.
- **Built before the freeze, on the host CPU.** `scripts/memcredit_am5r.py prepare-heldout`
  (`ops/am5r/am5r-prepare-heldout.sh`) wrote the artifact (pool texts; host only, read-only) and a
  text-free summary: ids, digests of every question, answer and memory, pool coordinates, BM25
  ranks and scores, each full-pool prompt's length in characters and the leakage facts (section
  6.7). It also checked that the builder reproduces AM1's held-out retrieved pools, 347 of 347,
  before removing any session, and that it rebuilds AM5's 63 ablated development pools exactly,
  which ride along in the artifact as the replay control (section 8, V3).
- **What the drafter read.** The summary's counts and digests; no memory, question, answer or
  reply text. Before the freeze the image's CPU selftest (no GRES) rendered every held-out request
  with each reader's tokenizer and the judge items (one placeholder reply per pool) with the
  judge's, and recorded only their lengths (section 15). No reader or judge ran on an ablated
  held-out pool, and no model output of them exists.
- **The evidence's absence rests on LongMemEval's own annotations.** The leakage facts (section 6.7) count LongMemEval's `has_answer`
  turns left in each ablated haystack and pool, pool memories whose text equals an evidence-session
  user turn, and memories or remaining turns that contain the normalized reference answer (crude:
  short answers match by chance). They cannot rule out an answer that can be guessed, or one stated
  in a session LongMemEval did not mark.

### 1.3 Development work that shaped the design

- **AM5** (`program/evidence/2026-10-16/am5-evidence-ablated/README.md`, exploratory, the 63
  development questions with their evidence removed, jobs 1483 and 1487) is this registration on
  development data. Switches at K = 8 / 70: Qwen3-8B 1 / 2, OLMo-2 6 / 10, Qwen3.5-9B 3 / 3 of 63.
  Costs (switched replies judged wrong; hand labels equal to the judge's on all 18 replies): at
  K = 8, 0, 5 and 3; at K = 70, 1, 9 and 3. Without single-session-preference questions (58):
  K = 8 gives 0, 4 and 2. AM5 fixed the construction, the readers' steps, the outcome definition
  (section 6.1) and the hand check's subject (switched replies and answering top-4 replies).
- **AM4** chose the primary cap (section 1.1). **am3g** supplied the readers, the engines, the
  steps, the gain side and the hand-check protocol, unchanged.
- **The power** (section 9) was computed from AM5's development cost rates and the known gains,
  before any held-out ablated output existed.
- **The development gains understate the held-out gains** (on the same 63 questions the rule
  gained 1, 4 and 3 at K = 8 against held-out 31, 27 and 26 of 347), so AM5's side-by-side was not
  a deployment estimate; this registration pairs the held-out cost with the held-out gain.

### 1.4 Readers and judge

- **The readers are am3g's, unchanged** (revisions, receipts, engines, chat templates, steps):
  Qwen3-8B (eager, batch-invariant), OLMo-2-1124-7B-Instruct (eager, batch-invariant through vLLM's
  Transformers backend; a default-mode fallback step if that step does not complete) and Qwen3.5-9B
  (eager, vLLM's default mode, which vLLM 0.31.0 requires for GDN attention). OLMo-2's card limits
  it to research and educational use under additional Gemma terms; no acceptance was required to
  fetch it (am3g, section 1.4).
- **Qwen3.5-9B is not replay-exact.** Its replies can depend on the batch schedule, which this
  registration's request list fixes (the held-out pools, then the control). Its readings say so.
- **The judge** is Qwen3-32B, eager and batch-invariant, with LongMemEval's non-abstention
  answer-check prompt against the reference answer (AM1's port), as in AM5. No second judge runs.
  The judge decides only whether a reply that does not abstain matches the reference answer; an
  abstaining reply is scored without it (section 6.1).

### 1.5 No gauntlet score (D121)

As in D111, D115 and D118, the registration continues a confirmed line under 8 GPU-h: it measures
the confirmed rule's cost on a new population. No gauntlet wave runs, and it carries no gauntlet
score. Two independent pre-freeze checks are required instead.

## 2. Question

On LongMemEval-S, with AM1's prompt, BM25 user-turn pools of 8 memories, a keep budget of 4 and
the non-abstention keep rule capped at K = 8 reads (AM4's definition): **for each of Qwen3-8B,
OLMo-2-1124-7B-Instruct and Qwen3.5-9B, is the rule's cost per question when the question's
evidence is absent (the rule abandons BM25 top 4's correct abstention for an answer judged wrong)
below, or above, its gain per question on the same questions with their evidence (the rule's
answer judged right where BM25 top 4's is judged wrong)?**

The comparison is what a deployer needs: if a share p of questions lack their evidence, and the
rest resemble these answerable questions, the rule changes accuracy by (1 - p) x gain - p x cost
per question. Cost below gain means the rule pays at least whenever no more than half the
questions lack their evidence. The break-even share gain / (gain + cost) is estimated with it.

## 3. What it decides and what it does not

It decides the primary reading per reader at K = 8: COST_BELOW_GAIN, COST_ABOVE_GAIN or
NOT_SEPARATED, a directional reading standing only when the blind hand check agrees (section 7.1);
VOID, JUDGE_DEPENDENT or PENDING_HAND_CHECK under sections 7.1 and 8. The secondary reading at
K = 70, the break-even share, the sensitivity analysis without single-session-preference
questions, the switch rate, the full-pool abstention rate, top-4 non-abstention and every other
output of section 6.6 are registered descriptions: reported regardless of outcome, deciding
nothing.

It does not decide:
- anything about unanswerable questions other than these: removing a question's evidence
  sessions leaves a question about something the user did discuss, with that discussion deleted.
  Deployment's unanswerable questions also include questions about things never discussed, and
  near-miss edits such as LongMemEval's `_abs` questions (am3g's H2);
- the gain side, which is known (section 1.1), or any cap other than 8 and 70;
- anything for other prompts (AM1's prompt tells the reader to say "I don't know"), retrievers,
  pool sizes, budgets, abstention patterns or judges;
- the net effect at any real mix of questions, which needs a share of evidence-absent questions
  that no dataset here supplies;
- why a reader answers without the evidence;
- anything about Qwen3.5-9B's replies under another batch schedule.

## 4. Identity and pins

| Item | Pin |
|---|---|
| Experiment id | `am5-ablated-cost-v1` (this file; config `experiments/am5/am5-ablated-cost-v1.yaml`) |
| Data | LongMemEval-S cleaned, `xiaowu0162/longmemeval-cleaned` @ `98d7416c24c778c2fee6e6f3006e7a073259d48f`, `longmemeval_s_cleaned.json`, 277,383,467 bytes, SHA-256 `d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442`, MIT; host only |
| Split | `experiments/am1/memcredit-split-v1.json`, SHA-256 `4fa1b774d4131080855d668ac8f00f5cb07d49cf741f2051d5f8d96577edb3e3` |
| Held-out questions | AM1's confirmatory set: 347 ids, SHA-256 of the newline-joined ids `d4f024fbcda5394984a46c421cd938f2b6db6067fef0f21a5c6e72359b27e50a`, in the order of AM1's held-out study artifact (host `~/cotcodec-runs/stage0/am1-memory-credit-v1/study-artifact.json`, SHA-256 `f23bca047dc7246c5a8db12f67a76a2ea36304d8669dc5c62ae6c42821f73eb7`), which `prepare-heldout` reads for the order and the builder check only |
| Held-out ablated artifact | host `~/cotcodec-runs/stage0/am5-ablated-cost-v1/inputs/heldout-ablated-artifact.json`, read-only: the 347 ablated pools, then the 63 control pools; 2,493,448 bytes, SHA-256 `68a75dcf1bc37ebe54fde61ec288d9c393adc1d0197b88168d7c153be34c1ce6`, built by `prepare-heldout` at `ca661cd9` (section 15); text-free summary `heldout-ablated-summary.json`, SHA-256 `c68b1da9e0e456c8bf7e06741df298cfbd622b6e3fd44602a812c137069a8355` (in the dry-run evidence, `prepare/`) |
| Replay control and development population | AM5's ablated development artifact, unchanged: 63 ids, SHA-256 of the ids `183ee4d3406786be721c4c846fa9f72f0fc2ae8c905dcb198eaaff17d78846fc`, artifact `f6d27d4cf2f3cf62789466cdfe80bab2cdc007c449411e1ad9b53aab76558b23`, summary `c9df7dbdafe94f9b54d3c1782e965f9a1492081ad6e063701643848450e8de9e` |
| Replay reference (V3) | AM5's job 1487: `sessions/{rd-qwen3-8b, rd-olmo2, rd-qwen35-9b-default, judge32}/all.{json, npz, texts.jsonl.gz}` and `judge-items.json`, the thirteen digests in the config (`populations.*.reference`; the npz, texts and judge-items digests equal AM5's committed `raw-sha256.txt` and `judge-items.sha256.txt`, a test checks) |
| Gain side | am3g's committed held-out per-pool records `program/evidence/2026-10-15/am3-nonabstain-generality-v1/per-table.json.gz`, SHA-256 `921c0ea00342d20b9c014ecfdc4940b9a56bbdaf3dc5f987a4c3930ff3bf6eb7`; expected gains 31, 27, 26 (K = 8) and 39, 35, 31 (K = 70), no loss, equal to AM4's committed `results.json` (`56fe0d99a5e1d2d3f01694be84c393469816b1f34de67829937273bfcba97721`; a test checks) |
| Development dry run's references | AM5's committed `results.json` `a0d5f35812c9165d81134b3cbf68299cdcbb4cb2d068c677987f6a8af2096bdb` and `per-table.json.gz` `58bec8389e37e9a9b92c6c1038fbced721731b496fee0512108d197763e11f9c`; AM5's host-only features `16bbd3855a67cd789b77acae855c9962225bdb1326cef12fd5340a6d72eb0889` and receipted hand labels `9da82b416383fb01fcd5b4f9c97f383f13625748e6dd299020fbd0fd96e5658c` (plan `171707ec40cb99d772d3f55ac3af1923dffc30fd5cd36ca43e582e50024d4dc0`); AM3's development per-pool records `0fc5635bad037588e521980536e4548eb51a6a3d9573e703b0f92010be72701e` (the dry run's gain side) |
| Readers | am3g's (`experiments/am3/am3-nonabstain-generality-v1.yaml`, SHA-256 `96fcd2186c43d6bdad7b1eb90e843aed39f0d56bad349799f8f1db6efb67d60e`, which this config pins as its base): `Qwen/Qwen3-8B` @ `b968826d9c46dd6066d109eabc6255188de91218`; `allenai/OLMo-2-1124-7B-Instruct` @ `470b1fba1ae01581f270116362ee4aa1b97f4c84`; `Qwen/Qwen3.5-9B` @ `c202236235762e1c871ad0ccb60c8ee5ba337b9a`; receipts and snapshot roots in that config (`models`) |
| Judge | `Qwen/Qwen3-32B` @ `9216db5781bf21249d130ec9da846c4624c16137` (receipt `06e4a7e9...`, root `8fcd9106...`); AM1's engine and sampling |
| Reader prompt | Step 0's template (the pilot config's `prompt`), SHA-256 of the template text `e63a0f995fe94ee72d6dcda7462a09c20e83f86dcc8252a53cdefb1ccf6fb37c`, thinking off for both Qwen readers |
| Judge prompt | LongMemEval's `get_anscheck_prompt` answer-check templates as AM1 ported them (`harness.memcredit_study.JUDGE_TEMPLATES`, SHA-256 `2e27234d4c7d50a1fd99da3e8d3c97704a1f10cc9d52185924b6d8ece3ef71d4`) |
| Abstention patterns | AM1d's four (`scripts/memcredit_label_free.py`), SHA-256 `031bee27e934a772f3419e38f9956d33dbea01096e6657e67426fd8a399d935f` |
| Hand check | am3g's labeller model (`claude-opus-5-5`) and launch prompt (`HAND_LABELLER_PROMPT`, SHA-256 `98c35ceac9710033b095f01abe4a5fc98f6ed3a597b461e12a98ac213a7ae096`); this registration's instructions (`memcredit_am5r.HAND_INSTRUCTIONS`, SHA-256 in the plan and every receipt) |
| Engine and image | vLLM 0.31.0 (`db9527a46873454610df6dbedf79a36d6bf1a7f6`), the cotcodec-vllm cu129 overlay built by `scripts/build_vllm_overlay_on_h100.sh` from the freeze commit's source capsule on the base `docker.io/vllm/vllm-openai@sha256:b18abb2df97b8f798e81862bd93f872ea18613372e2c3adc0cc2ac21e66ac12f` (am3g's and AM5's base); the image id is recorded by the build and the job checks it through the lane's provenance verification |
| Code | section 16 |

## 5. Units, pools and requests

- **Questions** are the unit of analysis and of resampling: the 347 held-out questions. Each has
  two pools: its original retrieved pool (the gain side, already run by am3g) and its ablated pool
  (the cost side, run here).
- **Memory unit**: one user turn with its session date, at most 1,500 characters (longer turns cut
  with " [...]"), as in AM1.
- **Ablated pool** (k = 8, chronological; bit i of a mask keeps memory i): the BM25 top 8 user turns
  (Okapi with Lucene's idf, k1 1.5, b 0.75, AM1's stopwords) of the haystack without the evidence
  sessions (section 1.2).
- **Requests.** Per pool the 70 4-subsets (masks ascending) and the full pool (mask 255): 71. The
  job's artifact holds the 347 held-out pools, then the 63 control pools: 29,110 requests per
  reader (24,637 held-out, 4,473 control).
- **Readers.** Greedy, at most 64 new tokens, the sampled token's log-prob, each in its own chat
  template, AM1's prompt (with its instruction to say "I don't know"). Engines as section 1.4.
- **Judge.** Every distinct (question, stripped reply) of the three readers, then the validation
  items (section 8, G-J1), scored by Qwen3-32B, eager, batch-invariant, greedy, 10 tokens, thinking
  off, with the question type's answer-check template; the label is LongMemEval's rule ("yes"
  occurs in the case-folded reply). Replies that hit the 64-token cap are judged as they stand.

## 6. Estimands

### 6.1 The capped rule and the outcome on an ablated pool

- **The rule** (`memcredit_am5.capped_rule`, equal to AM4's, a test checks): read a pool's 70
  4-subsets in ascending sum of their four BM25 ranks, equal sums to the lexicographically smaller
  sorted rank tuple (`memcredit_label_free.rank_key`), and keep the first whose reply does not
  abstain within the first K of that order; when none of the first K answers, keep BM25 top 4
  (always read first). A reply abstains when, normalized by `harness.memcredit.normalize_answer`,
  it is empty or matches one of AM1d's four patterns. The rule reads no label. K = 8 (primary) and
  K = 70 (secondary; the registered rule without a cap).
- **Correct, on an ablated pool**: a reply is correct when it abstains (the four patterns), or,
  when it does not abstain, when the Qwen3-32B answer check against the reference answer says yes.
  The cost indicator therefore needs a judge only for replies that do not abstain.
- **Why an abstention counts as correct without a judge.** (a) With the evidence removed, "I don't
  know" is the right reply by construction (LongMemEval's annotations; section 1.2), and the
  answer-check judge, which asks whether a reply matches the reference answer, says no to it by
  design, so judging abstentions with it would score every correct abstention wrong. (b)
  LongMemEval's abstention prompt would need an explanation these questions do not have, and in
  am3g it failed its own check (G-J2: it accepted plain answers as "identified as unanswerable" on
  4 of 30 decoys), which would hide costs. (c) The four patterns are the rule's own signal: with
  this scoring, BM25 top 4 is correct whenever the rule leaves it, so the cost indicator is exactly
  "the rule switched, and the judge rejects the reply it switched to", as AM5 defined it, and the
  development dry run reproduces AM5's figures under it. (d) Its two error modes are measured: a
  judge that accepts or rejects a switched reply wrongly, and a switched reply that declines in
  words outside the four patterns (which this scoring counts as a wrong answer, overstating the
  cost); the blind hand check labels both (section 8). A reply that matches a pattern and still
  guesses ("I don't know, maybe X") counts as an abstention; that error mode is not measured.

### 6.2 The cost and gain indicators

Per reader and question i, at cap K:

- **cost_i(K)** = 1 when BM25 top 4's reply on the ablated pool is correct and the capped rule's
  is not. The rule leaves top 4 only when top 4 abstains (then top 4 is correct), so cost_i(K) = 1
  exactly when the rule switched within K reads and the judge rejects the switched reply. The
  reverse (the rule correct, top 4 wrong) cannot occur: a top 4 that does not abstain is kept.
  `memcredit_am5r.cost_indicator`.
- **gain_i(K)** = 1 when, on the question's original pool, the capped rule's reply is judged
  correct and BM25 top 4's is judged wrong (Qwen3-32B, am3g's committed records read as AM4's
  crosscheck reads them: the capped choice is the rule's when its first answering position is at
  most K and differs from top 4, else top 4; `memcredit_am5r.gain_of`). The reverse (a loss) is 0
  for every question and reader at both caps; a test checks it and the counts (31, 27, 26 at K = 8;
  39, 35, 31 at K = 70), and `analyze` treats any other gain side as VOID (V1).
- **cost rate** C(K) = sum cost_i / 347 and **gain rate** G(K) = sum gain_i / 347; the registered
  difference is D(K) = C(K) - G(K) (cost minus gain).

### 6.3 Primary (K = 8) and secondary (K = 70)

Per reader at K = 8 (primary) and K = 70 (secondary): C, G, D; the paired counts n10 (cost, no
gain), n01 (gain, no cost) and n11 (both), D = (n10 - n01) / 347; the exact conditional 95%
interval of D (`memcredit_keepset_search.paired_reading`: (n10 + n01)/347 x (2 pi - 1) with pi's
Clopper-Pearson interval for n10 of n10 + n01), whose ends are the one-sided 97.5% bounds; its
question-cluster bootstrap interval; the exact two-sided McNemar p on (n10, n01) and the
Holm-adjusted p; the interval at the reader's Holm step level (1 - 0.05/3, 1 - 0.05/2 or 0.95,
reported); C and G with exact Clopper-Pearson 95% intervals.

### 6.4 The break-even evidence-absent share

Per reader and cap, s = G / (G + C) (`memcredit_am3g.break_even`: 1 when C = 0, 0 when G = 0 < C):
the share of evidence-absent questions at which the rule and BM25 top 4 tie, the rule ahead below
it. Interval: a question-cluster percentile bootstrap that resamples the 347 questions, each with
its (gain, cost) pair (10,000 resamples, numpy `default_rng(42)`, the sorted values at
floor(0.025 (n - 1)) and ceil(0.975 (n - 1))); undefined resamples cannot occur here (both
indicators are 0 or 1) and are counted anyway. Under the hand labels too, when they cover every
switched reply at that cap (section 8).

### 6.5 The sensitivity analysis

Sections 6.3 and 6.4, with Holm across the three readers, over the 322 questions that are not
single-session-preference (the 25 preference questions' references are rubrics for a personalised
suggestion; without the evidence a reader can still give a generic suggestion, and "I don't know"
is not clearly the right reply there; AM5 found 4 of its 15 switches on 5 such questions). A
description; it decides nothing.

### 6.6 Descriptive outputs

Per reader (`memcredit_am5.ablated_block`, unchanged, and this registration's blocks):
- the **switch rate** at K = 8 and 70 (BM25 top 4 abstains and a 4-subset answers within K
  reads; abstention flags only, no judge), per pool and per abstaining top 4, with exact intervals;
- the **full-pool abstention rate** (the all-8 reply abstains), every 4-subset abstaining, and the
  share of 4-subset replies that abstain;
- **top-4 non-abstention** (BM25 top 4's reply does not abstain), how many of those replies the
  judge calls correct and how many the hand labels call correct;
- the rule keeping an abstention, the reads (mean, median, distribution) and the pools reaching
  the cap without an answer;
- switched replies judged correct, by the judge and by hand, and the switches by question type;
- cost and gain by question type at both caps;
- the abstention patterns' counts;
- the replay control: the 63 control pools' figures for every reader (`control_ablated`), which
  for the batch-invariant readers equal AM5's job 1487 figures when V3 passes;
- the judge's validation counts (section 8, G-J1) on the held-out part and on the control.

### 6.7 Leakage facts (from the prepare summary)

Per question and in total: evidence sessions removed (and repeated evidence session ids),
`has_answer` turns before, inside the evidence sessions and left after the removal, `has_answer`
memories in the ablated pool, ablated-pool memories whose text equals an evidence-session user
turn, pools with a memory containing the normalized reference answer and questions whose remaining
user turns contain it (crude), and memories shared with the original pool
(`memcredit_am5.pool_facts`). Reported, and listed beside each hand-labelled reply.

## 7. Hypotheses and decision rules

### 7.1 Primary (confirmatory): cost against gain at K = 8, per reader

**Test.** Per reader, the exact two-sided McNemar test on (n10, n01) (section 6.3): p = min(1,
2 P(X <= min(n10, n01))), X ~ Binomial(n10 + n01, 1/2), exact rational arithmetic, p = 1 when
n10 + n01 = 0 (`memcredit_keepset_search.mcnemar_exact`). The exact conditional 95% interval of D
excludes 0 exactly when p <= 0.05 (a test checks): the test is the one-sided 97.5% bound of D
compared with 0, in each direction.

**Family and correction.** The three readers, familywise alpha 0.05, Holm's step-down
(`memcredit_am3g.holm`): the smallest p is compared with 0.05/3, then the next with 0.05/2, then
the largest with 0.05; equivalently the Holm-adjusted p is compared with 0.05.

**Judge-based readings**, per reader, from its Holm decision:
- **COST_BELOW_GAIN** if rejected and n01 > n10 (the upper bound of D below 0);
- **COST_ABOVE_GAIN** if rejected and n10 > n01 (the lower bound of D above 0);
- **NOT_SEPARATED** otherwise.

**Confirmation by the blind hand check** (section 8). The cost indicators rest on Qwen3-32B's
labels of switched replies and on the four patterns, which the hand check tests. Every switched
reply at K = 8 is hand-labelled (judged correct or not), so the hand-based cost indicator is exact
at K = 8: cost_hand_i = 1 when the rule switched within 8 reads and the switched reply's hand label
is 0, the hand label being 1 for a reply that gives the reference answer or declines to answer
(section 8). The gain indicators are the same on both sides (section 1.1; am3g's hand check
confirmed every OLMo-2 and Qwen3.5-9B gain at K = 70, which holds K = 8's, and AM4 reported 0
reversals; Qwen3-8B's held-out gains were not hand-labelled by am3g). The readings are fixed now:
- per reader the same exact McNemar test on (n10_hand, n01_hand), with Holm across the three
  readers at 0.05, gives the hand-based label (`hand_costs`, `family_readings`);
- a judge-based COST_BELOW_GAIN stands as **COST_BELOW_GAIN** only if the hand-based label is also
  COST_BELOW_GAIN; a judge-based COST_ABOVE_GAIN stands only if the hand-based label is
  COST_ABOVE_GAIN; otherwise the reading is **JUDGE_DEPENDENT** (`confirm_reading`);
- a judge-based NOT_SEPARATED stays **NOT_SEPARATED** whatever the hand labels say (the hand check
  confirms; it never creates a reading), and the hand-based label is reported beside it;
- labels that do not cover the plan exactly (an item unlabelled, labelled twice, outside the plan
  or not 0 or 1) make every directional reading JUDGE_DEPENDENT; without labels a directional
  reading is PENDING_HAND_CHECK and no decision follows (the registered `analyze` refuses to run
  without the receipted labels, section 16).

**Precedence.** VOID (V3) over JUDGE_DEPENDENT from G-J1 over the hand check: a void run reads VOID
whatever else holds, and a G-J1 failure makes a directional reading JUDGE_DEPENDENT before the hand
check is consulted (`analyze_population`).

**What a reading licenses**, for that reader (AM1's prompt; BM25 user-turn pools, 4 of 8; AM1d's
four patterns; the Qwen3-32B judge confirmed by blind agent labels; for Qwen3.5-9B, and for OLMo-2
if its pass comes from the default-mode fallback, in vLLM's default mode and this registration's
batch schedule):
- **COST_BELOW_GAIN**: "on AM1's 347 held-out LongMemEval-S questions, the rule capped at 8 reads
  loses fewer correct answers per question when the question's evidence sessions are removed than
  it gains per question when they are present, by D with its intervals; so it pays whenever at
  most half of such questions lack their evidence, and the break-even share s is estimated with
  its interval." The gain side is post hoc (section 1.1) and is part of the statement.
- **COST_ABOVE_GAIN**: the reverse: the rule capped at 8 reads loses more per evidence-absent
  question than it gains per answerable one; it costs accuracy whenever at least half of such
  questions lack their evidence.
- **NOT_SEPARATED**, **JUDGE_DEPENDENT**: nothing directional. The estimates and the break-even
  share are reported.

**What a licence amounts to.**
- *A comparison with a known number.* The gain indicators were observed before this registration
  and K = 8 was chosen after AM4 looked at them; the test treats them as the realized values of a
  sample, which is what they are, but a cap chosen to make the gain look good makes the comparison
  favour COST_BELOW_GAIN. The secondary cap (K = 70, the registered rule) is reported with the same
  test so that the reader can see whether the reading depends on the cap.
- *One kind of unanswerable question.* Removing the evidence sessions makes the question
  unanswerable from the history by LongMemEval's annotations; it is not a sample of deployment's
  unanswerable questions (section 3).
- *A read cost.* The capped rule calls the reader up to 8 times per pool, against BM25 top 4's
  once; the reads are reported (section 6.6).

**Why this test.** D121 and the drafting brief ask for a paired, per-question comparison of cost
and gain with one-sided 97.5% bounds and Holm across the three readers. The exact McNemar test
is the exact paired test of P(cost only) = P(gain only), which is D = 0; it is the test of
`am1-keepset-search-v1` and am3g, so its operating characteristics are known in this program, and
its exact conditional interval is the one-sided bound pair. Holm controls the familywise error at
0.05 and is at least as powerful as Bonferroni.

### 7.2 Secondary (registered, decides nothing): K = 70

The same estimand, test, Holm family (the three readers at K = 70) and labels, reported regardless
of outcome. Its hand-based label: the switched replies the judge calls wrong beyond K = 8 are
hand-labelled on a seeded sample of half (section 8), so a switched reply without a hand label is
assigned the outcome least favourable to the reading under confirmation: a cost when a
COST_BELOW_GAIN is confirmed, no cost when a COST_ABOVE_GAIN is (both hand-based families are
reported). The secondary reading licenses nothing beyond what the primary licenses.

### 7.3 Multiplicity across hypotheses

The primary carries its own Holm correction over the three readers. The secondary, the
sensitivity analysis and the descriptions carry no decision. No claim is made from "either of" the
readers beyond what each reading licenses.

## 8. Validity checks, void and kill rules

`scripts/memcredit_am5r.py` evaluates every check below. Each failure is a named error whose text
begins with its rule (`VOID (V1, ...)`, `VOID (V2, ...)`, `VOID (V3, ...)`); none surfaces as a
traceback: the host commands catch a missing or unreadable input that no named check caught and
report it as `VOID (V2, incomplete): an input is missing or unreadable`, with its cause (the GPU
job's driver and workers record their own failures in `summary.json`).

- **Freeze gate.** `run` and `worker` (the GPU job), `extract`, `hand-sample` and `analyze` refuse
  the held-out population unless the ledger holds a row for `am5-ablated-cost-v1` whose SHA-256
  equals this file's and every code pin of section 16 matches the working tree (parsed from this
  file; in the GPU job, the image's copy of the freeze commit, which holds every pinned file). The
  gate runs before any input of the population is opened. Those commands run the held-out
  population only with the pinned config path, `experiments/am5/am5-ablated-cost-v1.yaml`
  (`check_config_binding`; its SHA-256 is pinned in section 16). `prepare-heldout`, `plan` and the
  tokenizer-only `selftest` produce no model output and run before the freeze. The tests check
  refusal (with any file read before the gate caught) and opening against a scratch ledger and a
  scratch copy of this file.
- **VOID, nothing read (V1): a pinned input differs.** The held-out artifact, its summary, its
  question ids, parts and count; a model's revision, receipt SHA-256 or snapshot root (checked by
  the driver after the lane's own verification, before any step runs); job 1487's thirteen pinned
  files; the gain side's per-pool records, or a gain side whose counts or losses differ from the
  pinned ones; the abstention patterns; the judge templates; any code pin; a worker that finds its
  engine mode other than the pinned one; or the features' recorded provenance (population, artifact
  and id digests, pattern and template digests, and the digests of the fourteen repository modules
  the extraction imports, `FEATURE_CODE`). An input is fixed, never the code; a code change is a
  new registration id.
- **VOID (V2): incomplete, and the rerun rule.** am3g's rule, unchanged
  (`memcredit_am3g.rerun_decision`; its essential steps are this registration's: a complete pass
  of each reader, OLMo-2 from either of its steps, and of judge32). Right after the GPU job ends,
  before extract reads it, `rerun-decision` (`am5r-rerun-decision.sh`) applies these rules, in this
  order, to the driver's `summary.json` and the lane's `termination.env`; the first that applies
  decides. It decides a job once, only after the job ended (its saved `scontrol` record,
  `R/ops/scontrol-JOB.txt`, and the lane's `termination.env` both exist; a repeat is refused), and
  writes the decision through a temporary file, so a failed run leaves none. A `summary.json` that
  is not a JSON object is a named V2 error. A job that ended without the lane's termination record,
  or whose summary is such an error, cannot be decided, and the run is VOID (V2, incomplete).
  1. **rerun** when the workload never started (lane reasons `gpu_prolog_unavailable`,
     `foreign_gpu_process`, `hard_stop_before_start`). Without a driver summary: **no-rerun**
     after the lane's hard stop, **rerun** otherwise.
  2. **void** (V1) when the model verification failed or a worker found its engine mode other
     than the pinned one.
  3. **complete** when every essential step completed; extract reads this job.
  4. **no-rerun**, VOID (V2, time budget), when the lane's hard stop ended the incomplete job,
     whatever else the job records.
  5. For a signal (a lane reason starting `signal_`, or a signal the driver recorded):
     **no-rerun** when the lane's finish time is within 300 s of its hard stop; **rerun**
     otherwise (a cancellation or a node event).
  6. Otherwise, from the steps' records: the first incomplete essential unit, in the order
     Qwen3-8B, OLMo-2, Qwen3.5-9B, judge32, decides, and within that unit (OLMo-2's two steps) the
     first step's record that matches decides: **no-rerun** for a step skipped for lack of time, a
     pass stopped by its `max_s` or the deadline, or a worker killed as late; **rerun** for an
     engine that failed to start (OLMo-2's batch-invariant step excepted, whose declared fallback
     decides), a failed smoke check, a worker that ended without its done record, or a unit with no
     complete pass for any other reason.
  A rerun is a new job of this registration with the same commit, image, inputs and seeds
  (`am5r-submit.sh ... rerun`), submitted as soon as the decision is made and only when the
  decision record of the submitted job says "rerun" (the script refuses otherwise). Extract then
  reads the rerun's job, whose own decision is final: for the job named in the rerun record a
  "rerun" becomes **void** (V2, `--is-rerun`), and a second rerun is refused. The incomplete job's
  records are kept and reported. A job that ends incomplete for good makes the run VOID with its
  named reason. A failed image build is rebuilt once from the same capsule (`am5r-build.sh ...
  rebuild`, into its own build root `overlay-build-vllm-FREEZE8-r2`; `am5r-image.sh` reads the
  latest attempt); a second failure stops the run before the GPU job, and nothing is read. The
  attempts are counted from the job ids recorded as each build is submitted
  (`R/ops/build-attempts-FREEZE8.txt`), not from the build roots.
- **Named V2 errors in extract.** A run directory without `judge-items.json` (judge32 was skipped)
  is `VOID (V2, incomplete): the judge items (no judge step ran: judge32 was skipped) ...`; a
  missing or unreadable `summary.json`, reader pass or judge pass is likewise a named V2 error; a
  pool without its replies or labels is a V2 error in `analyze`.
- **VOID (V3): the replay control fails.** The job's artifact appends AM5's 63 development ablated
  pools, unchanged, after the 347 held-out ones. Extract compares Qwen3-8B's replies there with job
  1487's `rd-qwen3-8b` at every control cell (R1: identical tokens and finish reasons at all 4,473
  cells; log-prob bits reported), and the primary judge's labels at those cells with job 1487's
  `judge32` labels (R2: equal at all 4,473 cells) (`replay_checks`). If either fails, the pipeline
  is not the one AM5 ran: every reading is VOID and the figures are reported as a description of a
  void run, with the differences. A replay failure is not an infrastructure failure, and the
  registration is not rerun under this id. OLMo-2's (batch-invariant) and Qwen3.5-9B's (default
  mode, a different batch schedule from job 1487's) control replies, and the judge's item-level
  replay of the control's validation items, are reported, not gated. *Why the control, and why the
  anchor gates it.* Without it a pipeline error in the registered job (the image, the artifact, the
  prompt rendering, the engine, the judge) would be indistinguishable from a reader's behaviour;
  the control costs 18% more requests. Qwen3-8B in AM1's eager batch-invariant engine has replayed
  across different request lists: AM3's anchor check matched the pilot's eager pass on 2,272 of
  2,272 replies although each pool then had 71 requests instead of 274, and am3g's anchor replayed
  AM1's job 1458 on 49,274 of 49,274; the judge's labels replayed across different item lists in
  both.
- **G-J1, a replay of AM1's validation items.** On the held-out part the primary judge says yes to
  at least 95% of reference answers (single-session-preference questions left out) and no to at
  least 95% of "I don't know." (AM1's G2 rule, am3g's G-J1). The items and the batch-invariant
  judge are AM1's, so this checks that the judge replays (AM1 and am3g: 322 of 322 and 347 of
  347); the other-answer decoys' yes count is reported (am3g: 3 of 346), since a judge that accepts
  wrong answers would hide costs, which the hand check of every judged-correct switched reply
  covers. If G-J1 fails, a directional reading is JUDGE_DEPENDENT and no decision follows.
- **The blind hand check** (D9: agent labels, disclosed as such, not human labels). am3g's
  protocol, unchanged in its launch, audit, stages and receipts; this registration's plan and
  instructions.
  - *What is labelled.* `hand-sample` draws, from the features (`hand_plan`, text-free and
    deterministic, so `analyze` recomputes it and checks its digest against the receipted one,
    `--hand-plan-sha256`), per reader on the held-out pools:
    - every switched reply at K = 70 that the judge calls correct (which holds K = 8's), role
      `switched-judged-correct`: a judge error there hides a cost;
    - every switched reply at K = 8 that the judge calls wrong, role
      `switched-judged-wrong-primary`: so that the primary's hand-based cost is exact and can
      confirm a COST_ABOVE_GAIN as well as a COST_BELOW_GAIN;
    - a seeded sample of half (rounded up) of the switched replies the judge calls wrong that switch
      only beyond K = 8 (positions 9-70), `random.Random(f"44:am5r:hand:wrong:{reader}")`, role
      `switched-judged-wrong-secondary`;
    - every BM25 top-4 reply that does not abstain, role `top4-answers` (descriptive);
    - as distractors, as many other replies of that reader that do not abstain (any other requested
      mask of its ablated pools), none of them a target of any reader,
      `random.Random(f"44:am5r:hand:distractor:{reader}")`; a reader with fewer gets all of them,
      and the plan records the shortfall.
    Every item is a reply that does not abstain by the four patterns, so targets and distractors
    look alike. Items are deduplicated by (question, SHA-256 of the normalized reply), keep every
    use, and are put in one seeded order (`random.Random("44:am5r:hand:order")`).
  - *The labels' meaning.* The instructions (`HAND_INSTRUCTIONS`) give the check
    "answer-or-decline": 1 if the reply gives the reference answer (LongMemEval's answer-check
    criteria per question type, as am3g's check "answer"), or declines to answer and gives no
    answer (says it does not know, that the messages do not say, that the information is missing,
    or asks for it); 0 if it gives an answer that is not the reference answer (a different answer,
    a guess, part of the needed information, or alternatives none of which is the reference); a
    reply that declines and still offers an answer is labelled by that answer. They tell the
    labeller that the messages the reply was written from may or may not hold the needed
    information. A hand label of 1 on a switched reply is therefore "not a wrong answer": the
    judge-based cost counts a switched refusal outside the four patterns as a cost, the hand-based
    cost does not, and the confirmation rule (section 7.1) catches a reading that rests on it.
  - *Blindness and files.* `hand-sample` writes to `R/hand/`, a directory of its own: the sample
    (per item only its id, the question id and type, the check, the question, the reference answer
    and the reply: no reader, judge label, role, mask or rule identity), the instructions, the
    chunks of 60 consecutive items (`memcredit_am3g.write_chunks`), one launch prompt per chunk, the
    text-free plan and a text-free manifest. The features and every judge label stay in
    `R/private/`, which no labeller sees.
  - *The labeller.* For each chunk, in order and one at a time, a fresh Claude agent, model
    `claude-opus-5-5`, in a fresh context and a fresh working directory that holds only the chunk
    and the instructions, launched with am3g's pinned prompt (`HAND_LABELLER_PROMPT`, SHA-256
    `98c35ceac9710033b095f01abe4a5fc98f6ed3a597b461e12a98ac213a7ae096`, with the chunk's three file
    names filled in): read the two files, label every line independently, write the labels to the
    named output file, read nothing else and use no other tool.
  - *The stage's claim.* `am5r-hand-label-mac.sh` first claims the stage on the host, atomically
    and once (`mkdir R/hand/claim-STAGE`, with a line in `R/ops/jobs.log`); a stage already claimed
    is refused, from any work directory.
  - *The first launch: the CLI.* `am5r-hand-label-mac.sh ... cli` runs, in each chunk's directory,
    `claude -p --model claude-opus-5-5 --restricted --strict-mcp-config --tools Read,Write
    --permission-mode acceptEdits --no-session-persistence --output-format stream-json --verbose`,
    so the tools are only Read and Write and file access is confined to that directory; its
    stream-json transcript is kept per chunk. A CLI push happens only inside this action. In am3g's
    and this registration's dry runs the CLI could not authenticate ("Invalid API key", an
    environment matter), and it is expected to fail the same way at the registered run. It is still
    launched first, to record that failure: when it cannot start a session on the stage's first
    chunk (neither a tool call nor a result that is not an error), it launches nothing else, keeps
    its output and the time, and exits 3. No one enters or creates a credential to make the CLI
    start.
  - *The expected launch: one subagent per chunk.* After that failure the operator's Claude Code
    session launches, per chunk and in order, one fresh subagent, model `claude-opus-5-5`, whose
    whole prompt is the chunk's pinned prompt naming its files by absolute path
    (`prompt-NN-abs.txt`). Then `am5r-hand-label-mac.sh ... push subagent DIR`, DIR being that
    session's `subagents/` directory, reads the first user message of every `agent-ID.jsonl` there
    and counts per chunk the transcripts whose message is the chunk's prompt (SHA-256 of the
    stripped text). A chunk with exactly one gets that file, copied unmodified, as its transcript;
    the launch record (`labeller-STAGE.json`, host only) holds the counts, the agent ids, the number
    of files scanned, each chunk's directory and the CLI's failure time. More than one transcript
    for any chunk is an extra labelling attempt: it voids the hand check (`hand-merge` writes the
    final labels empty, so the join is "incomplete" and a directional reading is JUDGE_DEPENDENT).
    None leaves the chunk unlabelled, for the repair stage.
  - *What the subagent sees.* Its tools are not limited by its launch: the audit below checks what
    it did. Its working directory is the repository (the operator session's), and its context
    carries the session's instruction files (the user's and the project's `CLAUDE.md` and the
    auto-memory index `MEMORY.md`), the git status with recent commit subjects, and the skill and
    agent listings, but no file of the run and no label. The receipt records, per chunk, the
    instruction files' types and names found in the transcript. So that nothing in that context
    carries a result: from the GPU job's submission until the hand-check receipt is committed, the
    orchestrator writes no commit subject, memory note or file in the repository that carries
    judge-derived counts or readings of this run.
  - *Transcript audit.* `hand-merge` (`memcredit_am3g.cmd_hand_merge`, unchanged) requires the
    launch record and audits every chunk's transcript against it before it reads the chunk's
    labels (`memcredit_am3g.audit_transcript`). A transcript passes only if every line parses;
    every assistant line names the model `claude-opus-5-5`; every tool-call block is a `tool_use`
    Read of one of the chunk's two input files or Write of its output file, by a path in the
    chunk's own directory, with no other block that calls a tool; the output was written; the
    first user message, when the transcript holds one, is the chunk's pinned prompt; and, for a
    subagent, every line carries the launch record's agent id and a timestamp after the CLI's
    recorded failure. The rows of a chunk whose transcript fails, or is missing, are dropped, so
    its items go to the repair stage.
  - *One labelling run and one repair.* The first stage labels every chunk once. `hand-merge` keeps
    the rows that parse, name an item of the stage once and carry a label of 0 or 1; the items
    without such a row form the one repair stage, with its own claim, chunks and prompts, labelled
    the same way. After it the labels are final, complete or not; there is no third stage and no
    other relabelling: no item is labelled again by choice and no label is edited. A correction
    found after the join is reported separately, beside the registered result, and changes nothing
    in it. `hand-sample` and `hand-merge` each run once (a repeat is refused and leaves the first
    record), and write their records through a temporary file.
  - *Receipts before the join.* Each stage is receipted (`am5r-hand-receipt.sh`), text-free. The
    receipt refuses a stage without a launch record, a subagent launch without the CLI's recorded
    failure, and a transcript whose SHA-256 on the Mac differs from the audit's. It records the
    labeller's model and launch, the CLI's error digest and failure time, the labelling attempts
    per chunk and the matching transcripts in all, the agent ids, models, first-prompt digests and
    times the audit found, the context's instruction files, the prompt's SHA-256, the
    instructions', sample's and plan's digests, every chunk's digest, every transcript's digest
    with its audit, a void, the stage's raw labels' digest and, after the last stage, the final
    labels' digest. With the sample's and the merge's records, the manifest and the plan it goes to
    `R/hand-check/`, which is committed, before `analyze` joins the labels, as the run's evidence
    directory's `hand-check/` (`program/evidence/RUNDATE/am5-ablated-cost-v1/hand-check/`, RUNDATE
    being the job's date); `am5r-stage-evidence.sh` later copies the same files to the same path.
    The commit's id is passed to `am5r-analyze.sh` as RECEIPT_COMMIT and logged at the head of its
    log. `analyze` refuses labels or a plan with another digest, and the hand check is "incomplete"
    unless the labels cover exactly the recomputed plan's items, each once, with 0 or 1. The
    verifier checks that `results.json`'s hand-check labels and plan digests equal the committed
    receipt's, and that the receipt commit precedes the analysis log.
  - *Size and time.* No cap on items. At AM5's development rates (switches at K = 8 / 70 of 1 / 2,
    6 / 10 and 3 / 3 per 63 pools; answering top 4s 1, 4 and 0) the held-out pools give about 100
    targets and as many distractors: about 200 items, 4 chunks. The maximum, every pool switching
    within 8 reads for every reader, is 3 x 694 = 2,082 items (35 chunks). The dry run's one chunk
    of 34 items took the subagent 96 s; am3g's 278 items took 5 chunks. The first stage is expected
    to take under 15 minutes.
  - *Decision.* Section 7.1 (primary) and 7.2 (secondary). Hand-against-judge agreement (counts and
    Cohen's kappa), overall and per role, is reported as a description.
- **Kill.** None beyond the void rules. A void is reported with its check and counts.

## 9. Operating characteristics

Computed by `scripts/memcredit_am5r.py power` from AM5's committed `results.json` (the development
cost rates) and the pinned gain counts, in the development dry run
(`program/evidence/2026-10-16/am5-ablated-cost-dev-dryrun/power.json`). The model: the gain
indicators fixed at their known held-out values (31, 27 and 26 of 347 at K = 8), each question's
cost indicator Bernoulli(q), independently of its gain (AM5 found the rule switching on the same
question on both pool versions for 0-1 questions per reader); the exact McNemar test on
(n10, n01). Holm rejects a reader at least at 0.05/3 and at most at 0.05, so the two values bound
its power (`power_cost_gain`, exact sums over both binomials).

**Primary (K = 8): the probability of each reading.**

| Cost rate q | Qwen3-8B (gain 31): COST_BELOW_GAIN | OLMo-2 (gain 27): COST_BELOW_GAIN / COST_ABOVE_GAIN | Qwen3.5-9B (gain 26): COST_BELOW_GAIN / COST_ABOVE_GAIN |
|---|---|---|---|
| 0.00-0.01 | 1.00 | 1.00 / 0 | 1.00 / 0 |
| 0.02 | 1.00 | 0.95-0.99 / 0 | 0.92-0.98 / 0 |
| 0.03 | 0.90-0.97 | 0.66-0.85 / 0 | 0.56-0.81 / 0 |
| 0.04 | 0.60-0.80 | 0.27-0.51 / 0 | 0.20-0.44 / 0 |
| 0.05 | 0.26-0.48 | 0.07-0.20 / 0 | 0.04-0.15 / 0 |
| 0.06 | 0.08-0.20 | 0.01-0.05 / 0 | 0.01-0.04 / 0 |
| 0.08 | 0.00-0.01 | 0 / 0.00 | 0 / 0.00 |
| 0.10 | 0 | 0 / 0.01-0.06 | 0 / 0.02-0.09 |
| 0.12 | 0 | 0 / 0.16-0.37 | 0 / 0.22-0.45 |
| 0.15 | 0 | 0 / 0.75-0.90 | 0 / 0.80-0.93 |
| 0.20 | 0 | 0 / 1.00 | 0 / 1.00 |

Qwen3-8B's COST_ABOVE_GAIN probability is 0.46-0.70 at q = 0.15 and 0.99-1.00 at q = 0.20.

**At AM5's development rates** (K = 8: q = 0/63, 5/63 = 0.079 and 3/63 = 0.048):
- Qwen3-8B: COST_BELOW_GAIN with probability 1.00 at the point rate; at its exact upper bound
  (0.057) 0.12-0.27.
- OLMo-2: q = 0.079 is almost its gain rate (0.078): every reading has probability at most 0.002;
  NOT_SEPARATED is the expected outcome. At its upper bound (0.176) COST_ABOVE_GAIN has 0.97-0.99.
- Qwen3.5-9B: COST_BELOW_GAIN 0.07-0.20; at its upper bound (0.133) COST_ABOVE_GAIN 0.48-0.72.

**Readings.** The power reaches about 0.8 only when the cost rate is about 0.045 below the gain
rate, or about 0.07 above it. Near AM5's development rates it is likely to read
COST_BELOW_GAIN for Qwen3-8B and NOT_SEPARATED for the other two, and the break-even share
(section 6.4) with its interval is then the informative output. The development rates rest on 63
questions; held-out rates may differ (on LongMemEval's edited `_abs` questions the K = 8 costs
were 3, 3 and 0 of 30).

**With the hand check** (the combined rule of section 7.1). The hand labels can only make a
COST_BELOW_GAIN stronger when they find no hidden cost, so its power is the judge-only power when
the judge's judged-correct switched replies are right (AM5's development hand labels agreed with
the judge on all 18). A COST_ABOVE_GAIN needs the hand-based test too: if each judge-counted cost
is a hand-confirmed wrong answer with probability a (the others refusals outside the patterns, or
correct answers the judge missed), its power falls. OLMo-2 at q = 0.15: 0.75-0.90 (a = 1),
0.45-0.69 (a = 0.9), 0.16-0.37 (a = 0.8); Qwen3.5-9B at q = 0.15: 0.80-0.93, 0.53-0.76 and
0.22-0.45 (`power.json`, `with_the_hand_check`).

## 10. Seeds

Declared `[42, 43, 44]`. 42: every engine's seed, every bootstrap. 44: the hand check's draws (the
sample beyond K = 8, the distractors and the item order). 43 is unused; the lane's seed-matrix
contract binds three seeds. No unseeded randomness: the rule, the tests and the exact intervals
involve no random draw.

## 11. Compute plan and caps

- **Steps.** One image build, then one GPU job on one H100, from the freeze commit, in the image
  built from its source capsule, through the docker-research lane
  (`scripts/submit_docker_research_job.py`): the container runs read-only with `--cap-drop ALL`,
  `no-new-privileges`, the user's uid:gid, a tmpfs `/tmp`, no network and only the GPU Slurm
  allocated (`--gpus device=` that GPU), stock vLLM only, in Slurm partition `research`. Steps, in
  order: `rd-qwen3-8b`, `rd-olmo2` (`rd-olmo2-default` only if it does not complete),
  `rd-qwen35-9b-default`, `judge32`.
- **Estimate**, from AM5's job 1487 (4,473 requests per reader: passes of 32.7, 34.0 and 58.5 s,
  engine starts of 27-41 s; the judge 3.4 s on 460 items): 29,110 requests per reader (6.5 times),
  passes of about 215, 220 and 380 s; the judge on about 3,000 items (about 1,800 distinct replies
  and 1,228 validation items) about 25 s; with the starts, the checks and the lane's prolog about
  20 minutes, 0.33 GPU-h; the build about 1 minute, 0.02 GPU-h; about 0.35 GPU-h in all.
- **Caps.** Slurm limits: build 5 minutes, the job 70 minutes: **1.25 GPU-h**; with the one rebuild
  and the one rerun section 8 allows, 2.50 GPU-h. Well under D24's 8 GPU-h line.
- **Step budgets** (`jobs.heldout` in the config: per step [`min_start_s`, `max_s`]). A step starts
  only with `min_start_s` left before the job's deadline (the limit minus the lane's 210 s), and
  its passes stop at `max_s`. They are sized with am3g's held-out overhead model
  (`budget.overhead_model`: per job 100 s; per step outside its pass 135 s for a reader, 155 s for
  the judge, 125 s for a batch-invariant step whose engine refuses to start), which am3g's job
  1480 fitted inside at 49,274 requests per reader: readers [750, 600] (2.7 times the expected
  pass), Qwen3.5-9B [1150, 1000], judge32 [480, 300]. With every step at its cap, judge32 starts
  with 1,285 s left on the normal path, 1,160 s on the fallback path (OLMo-2's batch-invariant
  engine refuses to start and the default-mode step runs) and 550 s on the residual path (OLMo-2's
  batch-invariant pass stopped by its `max_s`, then the fallback), and the job ends by 3,160,
  3,285 and 3,895 s of its 3,990; a test simulates the three paths
  (`test_the_judge_starts_and_fits_on_every_path`).
  - **A hung engine start.** A step's `max_s` bounds its passes, not its engine start. An engine
    start that hangs is stopped only near the job's end (the lane's USR1, which the driver passes
    on, or the worker overrunning the deadline by 90 s, killed as late). Either way no later step
    can start, and the rule of section 8 makes the job a time-budget void with no rerun. The
    registration accepts this risk: every engine start of these models in am3g's and AM5's jobs
    took 27-41 s.
  - **A cold page cache** can lengthen an engine start by tens of seconds; the smallest slack, on
    the residual path, is 70 s at judge32's start and 95 s at the job's end.
- **Order.** Build (rebuilt once if it fails); the post-build CPU selftest of the held-out
  population (no GRES); the GPU job, its rerun decision and its one rerun if the rule says so; then,
  on the host CPU, extract and the blind hand-check sample; the labelling on the operator's Mac,
  each stage merged and receipted on the host; the receipts committed; then analyze and the tests on
  the host. The GPU job is submitted only when no other GPU job of this program is queued or
  running (`am5r-preflight.sh`). Under D110 another project's `transcreate-*` jobs hold GPUs; they
  are never touched, and Slurm allocates this program's GPU.

## 12. Data handling

The reply texts, the judge items, the artifacts (pool texts, questions, answers) and the features
stay on the host, under `~/cotcodec-runs/stage0/am5-ablated-cost-v1/` (AM5's artifact and job 1487
stay where AM5 left them). `extract` writes the features (per mask: the judge's label, the
abstention flag and pattern, the finish reason, the token count, the SHA-256 of the normalized
reply; no text) to a host-only directory and refuses one inside the repository. The repository gets
`results.json`, `per-table.json.gz` (ids, types, masks, outcomes, reads, cost and gain indicators;
no text) and `tables.md` from `analyze`, the text-free logs and lane records, the prepare summary
(text-free) and a judge-item list with each response replaced by its SHA-256. The staging script
searches every staged file for every reply of 12 or more characters and every question, answer and
memory text of both artifacts, and exits with an error on a hit; a staged tree with a hit is not
committed. The blind hand check's files (the sample, the chunks and their prompts, the labels,
whose notes may quote the texts, and the labellers' transcripts) stay on the host in `R/hand/`,
made read-only after each step. The operator's Mac holds copies during the labelling (the work
directory W outside the repository, and the subagents' transcripts in the operator session's
`subagents/` directory); both are deleted from the Mac once the run's evidence is staged and
committed. The repository gets the text-free receipts, committed before the join.

## 13. Exclusions and infrastructure failures

No question is excluded for its outcome. The 347 are AM1's confirmatory set (Step 0's eight demo
questions were excluded there before any run). A request that does not finish leaves its pool
incomplete, which is the V2 rule (section 8). A smoke-check failure (16 requests at the start of
every pass) stops that step before data. An engine that fails to start ends its step; OLMo-2's
batch-invariant step is then followed by its declared default-mode fallback.

## 14. Reported regardless of outcome

- The primary per reader: C, G, n10, n01, n11, D with its exact and bootstrap intervals, the
  one-sided 97.5% bounds, the exact p, the Holm-adjusted p, the interval at the Holm step's level,
  the judge-based reading, the hand-based label and the reading (or VOID, JUDGE_DEPENDENT or
  PENDING_HAND_CHECK with the named check); the break-even share with its interval, by judge and by
  hand;
- the same at K = 70 (secondary) and without single-session-preference questions (sensitivity);
- the blind hand check: the plan's counts per role and reader, the distractor shortfall and the
  digest, the labels' digest, the receipts (labeller model and launch, prompt digest, transcript
  audits, the repair stage's size), hand-against-judge agreement with kappa overall and per role,
  and any correction found after the join, separately;
- the replay control (R1, R2 for the anchor; the other readers' replay and the judge's item-level
  replay), G-J1 with the decoy count;
- every rerun decision with its reason;
- every descriptive output of section 6.6 and the leakage facts of section 6.7;
- GPU-h; every deviation; the disclosures of section 1, including that the gain side was known and
  K = 8 chosen after AM4, and that the run carries no gauntlet score.

## 15. What development fixed in this design: the development dry run

Before the freeze the whole pipeline ran on the development population (AM5's 63 ablated
development pools, AM5's artifact unchanged) in a new host directory
(`~/cotcodec-runs/stage0/am5r-dev-dryrun/`), with the operator scripts of section 16 in their `dev`
mode, from commit `c16437bc` (the code of `ca661cd9` with the held-out artifact pinned). Record:
`program/evidence/2026-10-16/am5-ablated-cost-dev-dryrun/README.md`.

- **The held-out ablated artifact** (host CPU, no model): `am5r-prepare-heldout.sh dev ca661cd9`
  built `68a75dcf...` (2,493,448 bytes) and its summary `c68b1da9...` (`prepare/`). The builder
  reproduces AM1's held-out retrieved pools, 347 of 347, and the ablation rebuilds AM5's 63
  development ablated pools exactly. 700 evidence sessions removed; LongMemEval's 691 `has_answer`
  turns all lay inside them and none is left in any ablated haystack or pool; no pool memory equals
  an evidence-session user turn; by the crude string check 27 of 347 ablated pools hold a memory
  containing the reference answer and 91 questions have it in a remaining user turn (AM5's
  development figures: 4 and 10 of 63).
- **A CPU precheck** at `ca661cd9`, before any GPU time: `extract`, `analyze` and `dryrun-compare`
  on a scratch copy of AM5's job 1487 (its passes, the summary relabelled) passed all 24 checks.
- **Build** (job 1502, 1 H100, 00:01:11, 0.0197 GPU-h): image
  `sha256:a16f70c1bc732961f1c9dd44bc13767a8ec292df2000206cdaafaafa8a328ab8` from capsule
  `003eb3c1...`, provenance PASS. The first submission was refused by the preflight while two GPU
  jobs of another workstream of this program ran; it was submitted when they had ended.
- **Post-build CPU selftests** (no GRES): development (job 1503) and held-out (job 1504,
  tokenizers only, no model output). Every prompt fits: development at most 1,148 (Qwen3-8B),
  1,077 (OLMo-2) and 1,164 (Qwen3.5-9B) tokens; held-out with the control 29,110 requests per
  reader, at most 1,778, 1,699 and 1,803 tokens, and placeholder judge items of at most 349.
- **GPU job** (job 1507, 1 H100, 00:06:46, 0.1128 GPU-h; limit 13 minutes): every step complete
  (OLMo-2's fallback not needed); reader passes 32.4, 34.3 and 58.6 s after engine starts of
  27.8-41.2 s; the judge 3.5 s on 460 items. The rerun rule: complete.
- **Total 0.1325 GPU-h** of the 0.3 allowed (`program/state.json`, `gpu_hours_ledger`).

**It reproduced AM5 exactly** (`dryrun-compare.json`, 24 of 24 checks):
- every reader's 4,473 replies equal job 1487's in tokens, finish reasons and log-prob bits, for
  Qwen3-8B, OLMo-2 and Qwen3.5-9B (the same request list and order), and the primary labels at every
  cell; the judge-item list is byte-identical (`4bbb7f5c...`) and its 460 labels equal job 1487's;
- the features' per-pool cells equal AM5's features (`16bbd385...`) for all three readers;
- AM5's own analysis (`memcredit_am5.analyze`), run on these features with AM5's receipted hand
  labels and plan, reproduces AM5's committed `per-table.json.gz` byte for byte (`58bec838...`) and
  its reader blocks, leakage, judge validation, labelled items and hand check;
- this registration's ablated blocks equal AM5's in every judge-based field at K = 8 and 70
  (switches 1, 6 and 3 / 2, 10 and 3; costs 0, 5 and 3 / 1, 9 and 3), and its development gain
  side equals AM5's original-pool gains (1, 4 and 3 at both caps).

**The blind hand check under the registered protocol.** `hand-sample` drew 34 items in one chunk
(plan `2bcd07af...`): 2 switched replies judged correct, every switched reply at K = 8 judged wrong
(8 uses, 7 items), the seeded half of the 5 judged-wrong switches beyond K = 8 (3), the 5 answering
top-4 replies and 18 distractors. The CLI launch could not authenticate (an error result, at
18:41:11Z) and exited 3; one fresh subagent, model `claude-opus-5-5`, with the absolute-path pinned
prompt labelled the chunk; `push subagent` found its one transcript among 45, which passed the
audit (three tool calls, one agent id, every line after the CLI's failure; context files
`CLAUDE.md` (user and project) and `MEMORY.md`); 34 valid rows, so no repair stage. The receipt was
committed at `351dc062` before the join. Hand against judge: 34 of 34 (kappa 1.00), 6 labelled
correct, no switched reply labelled a decline outside the patterns; against AM5's own receipted
labels, 16 of AM5's 18 items are in this plan and all 16 agree (the other 2 are judged-wrong
switches beyond K = 8 that the seeded half left out). The hand-based costs equal the judge's at
K = 8; at K = 70 the two unlabelled OLMo-2 switches give 7 or 9 under the two assignments of
section 7.2.

**Analyze** (development mechanics, deciding nothing) ran twice at `c16437bc` with byte-identical
outputs; `power` wrote section 9's tables; the memcredit tests passed on the host (221). At K = 8
the development data give D = -0.016 (Qwen3-8B), +0.016 (OLMo-2) and 0.000 (Qwen3.5-9B), all
NOT_SEPARATED, judge and hand alike, with break-even shares 1.00, 0.44 and 0.50; V3 (all 4,473
cells) and G-J1 (58 of 58, 63 of 63; decoys 4 of 62 yes) pass.

**The runbook rehearsal** (`rehearsal/am5r-rehearse.sh` and its log): section 16's host scripts
under a fake HOME on the host, with `sbatch`, `scontrol`, `squeue`, `nvidia-smi`, `ssh`, `scp` and
`claude` stubbed; no job submitted, no GPU and no model used. It runs am3g's 56 cases adapted to
these scripts and 5 of this registration's own (dev mode refusing to submit or extract the
held-out population; `prepare-heldout` refusing reg mode and an existing artifact; the held-out
tokenizer-only selftest submitting in dev mode). Its first run, at `cf9f9ebb`, stopped on an error
in the rehearsal script itself (an apostrophe inside a parameter expansion); its second, at
`943348f4`, failed one case, again the rehearsal's own (it reused the "no sbatch call" check after
an earlier case had legitimately submitted; the refusal itself was right); with the script of
`8128800a`, against the operator scripts of `943348f4` (unchanged since `c16437bc`), all 61 cases
pass.

**Tests.** `tests/test_memcredit_am5r.py` (62 tests) passes locally; on the host the memcredit tests
of am3, am3g, AM5 and this registration pass (221). The whole suite on the host at `943348f4`:
3,770 passed, 64 skipped and 2 failed in another experiment's tests (`test_r04_evidence.py`,
`test_r04_nuisance.py`), the same two that am3g's dry run found failing on `main`; this branch
changes no existing code.

Development also set: the construction and the outcome definition (AM5), the readers and engines
(am3g), the 71 requests per pool, the development job's 13-minute limit and budgets (job 1487's
timeline), and the held-out budgets (am3g's overhead model, section 11).

## 16. Code of record (at the draft revision; re-pinned at the freeze)

The fill commit re-pins every row; a row that changes is reviewed before the freeze. The gate
parses this table and refuses to run unless every file matches.

| File | Role | SHA-256 |
|---|---|---|
| `scripts/memcredit_am5r.py` | this registration: gate and config binding, the held-out artifact, driver and workers, extract and the replay control, the cost and gain indicators, the paired test with Holm, the break-even share, the hand check's plan, sample and join, the confirmation rule, analyze, the dry-run comparison, power | `b24766ddb8f90b268fa7660d5c09dec98009827b5a799a87767c92bb039e2006` |
| `tests/test_memcredit_am5r.py` | its tests | `8727795313c4c8767298b4f1d49564ebcb097a0b924082abda7e076dc274b2ef` |
| `experiments/am5/am5-ablated-cost-v1.yaml` | this registration's config | `f18eeb7317c9fd4f2673934e3c435295605e6d3d89af6f973d86a7bcb2a0f863` |
| `scripts/memcredit_am5.py` | AM5's ablation, capped rule, per-pool records and blocks (imported) | `225e42e7d4f2e9a1ccfce1c4a826a04bcdb57511fea248f8009bf97467b6fa0b` |
| `experiments/am5/am5-evidence-ablated-dev.yaml` | AM5's config (the dry run's comparison) | `0c49e157755a3a67e83eed9c07e1c37ba912e93aaf29416d9ac7fbc643ea88a9` |
| `scripts/memcredit_am3g.py` | am3g's readers, steps, pools, judge items, rerun rule, hand-check protocol (imported) | `4bb0d42c09f9fca6e728a2487966bc13c08715672dce33316db195f6e7573e26` |
| `experiments/am3/am3-nonabstain-generality-v1.yaml` | am3g's config (the readers, models and steps) | `96fcd2186c43d6bdad7b1eb90e843aed39f0d56bad349799f8f1db6efb67d60e` |
| `scripts/memcredit_am3.py` | AM3's engine helpers, rule and per-pool helpers (imported) | `25f634edd29a23f2fdee12b0825013d624aa5305d49cf512f74fdf1827ea130f` |
| `experiments/am3/am3-reader-replication-v1.yaml` | AM3's config (the reader blocks) | `525ebf29e80941ef02e646e04c66fdaa40aba67f6bb0dbb9d5926c68befa07c4` |
| `tests/test_memcredit_am3.py` | AM3's tests (supply a pass writer to these tests) | `1ab5196ca553f8cc92deda0a728ec98987853ec81d3f75041561661659d848b3` |
| `tests/test_memcredit_am3g.py` | am3g's tests (supply the transcript and launch writers to these tests) | `e4f5f152e5dc6e89bdaa0eed94dfbb21f02dde36001b32813d2fd638e928032e` |
| `scripts/memcredit_keepset_search.py` | McNemar, paired readings, reads, ledger and pin parsing | `3fbb804328bd310a6c8626f408d0d1b44a4624f06829a0762e3afc6134add584` |
| `scripts/memcredit_cost_curve.py` | table decoding (imported by am3g) | `431f4cb21ccd398e1433e29a5b40c1a697d48b9aecc5fc728956f819e28c9bab` |
| `scripts/memcredit_label_free.py` | AM1d's abstention patterns, BM25 order | `721015de434021a72ab3bbbab5e91d0de39a2fc359df7283068f83026dcb9d8f` |
| `scripts/memcredit_step0.py` | request streaming, pass files, GPU sampler | `57f2e4bbbd11bf750ff224852ba5dd19923ecb3decfde74d23a6913a7f9a7227` |
| `scripts/memcredit_study.py` | pass reader (`load_pass`) | `f27ecd21e769655cddc1e9b06ee8f4c7c4ee8494348b4fc73dba7c68fdb66bb3` |
| `scripts/memcredit_analyze.py` | imported by `scripts/memcredit_keepset_search.py` | `5444104d3c760b17f311656f4e0dbd50b2b154c89d806f1e4aa2ab6791fb0f34` |
| `harness/__init__.py` | the harness package | `17dac2704be26050e324aa36aba6d2c855abbd592e4d72f750b9b6e9c4399fec` |
| `harness/g2_pilot.py` | lane helpers (deadline, marker, model verification) | `8c685425522377de9fbab92fac02aea321bb2b3bd69d82d2118c4ecea49f6599` |
| `harness/memcredit.py` | BM25, pools, prompts, Clopper-Pearson, answer normalization | `ad0964d0caab382b5541b64d56a30105bc306d2286f6e62137b1eff9121dd607` |
| `harness/memcredit_study.py` | configs, split, request messages, answer-check templates, validation items, bootstrap | `14a97d826ba619e23ea9686e2d2d57149d9f0119df3f80240843178953cf301b` |
| `experiments/am1/memcredit-study-v1.yaml` | the pilot's config (prompt, pools, judges) | `ecdb5c11ff4eaf757ec6712c6f2c75d61c79882bb3d418202b7143abf90793db` |
| `experiments/am1/am1-memory-credit-v1.yaml` | AM1's registration config (confirmatory set) | `8466d6d42ace1477bb9b2377de8ed67027502ff11b179a369eed352fda212069` |
| `experiments/am1/memcredit-split-v1.json` | the split | `4fa1b774d4131080855d668ac8f00f5cb07d49cf741f2051d5f8d96577edb3e3` |
| `models/registry.yaml` | the readers' registry entries | `4a084c2f2a4d7f9c1cbdcc6ce3032f558ed3d3a8399428159627512f46a99a03` |
| `scripts/fetch_open_model.py` | snapshot verification | `d995b59ece3c809edd70d6c60a78628ae5cb1ccc0ce8350cc455084d3787d29f` |
| `scripts/submit_docker_research_job.py` | the lane's submitter | `660271655aa22ebd387a023e25d21e6a809c22699ec6314d9d535be74e17a994` |
| `infra/slurm/host-single-node/docker-research.sbatch` | the lane | `2a10c9c72c22ab6dd5135061ff1b9b50977a468687180353d8cd7273acbaf1ec` |
| `scripts/build_vllm_overlay_on_h100.sh` | the overlay build | `aa43283e757695384e0548d060a18b98f07a3af06f583efdb2d709f677e1a96d` |
| `scripts/create_source_archive.py` | the source capsule | `672670ca29d3254e9af90b810eef591e15dae6934612c5184a72e5d0c7e9948c` |
| `scripts/extract_discovery_source_archive.py` | the capsule extractor | `9b4d21a83beac8913dc06a946cf43ea31d77326e65d04957fad66d7b97d8c3cb` |
| `scripts/preregister.py` | the ledger | `21fc3ef0ed0958b1600ce742c3b4f8d557d0a298635acb20342710eb814b2c0d` |
| `scripts/verify_compute_provenance.py` | the lane, inside the container: image provenance | `ca62d62ae5c0e820a08574d5c5b1227c4495a24f3abcf342a1ae3ff1958d54ba` |
| `scripts/check_compute_env.sh` | the lane, inside the container: environment doctor | `76fc5d64f7e84fd1e93340688b6be845d97f01c4791981c31ac8e70d66ff08ff` |
| `scripts/exec_research_workload.py` | the lane, inside the container: runs the workload | `bb3abd1dd11e8ec9336fc181ac1999b1deea00e08e05d0fff3227111eaa6e4c1` |
| `infra/research/Dockerfile.vllm-overlay` | the overlay image's Dockerfile | `437ff4f6d95d564a5065cc4383e79b34f166417358edcee34b82e5d05574852e` |
| `uv.lock` | the Python environment of every host step | `4721104d055ec9d7488f82831c24b7e080124f27e9b850abd51c91024629b60f` |
| `ops/am5r/am5r-env.sh` | operator: shared host paths | `4c143054a7995599d47e411304ea5bb089494ed6b4e334a4519c114275726eef` |
| `ops/am5r/am5r-checkout.sh` | operator: clean clone from a bundle | `afd3b7250e755e25183ed4d48895152a7042729c4cce5cc522ebbdc6ad2035a0` |
| `ops/am5r/am5r-mac-bundle.sh` | operator, on the Mac: the bundle and the bootstrap copies | `9a75fd99d37a0973610c73d4f8d7594a1ac3ed4478f9369d67fe60368451e018` |
| `ops/am5r/am5r-prepare-heldout.sh` | operator: the held-out ablated artifact (before the freeze) | `50e2e9f8413645c6274354d5ed4660420eae17dd69e2aa3283970c7612f7b33d` |
| `ops/am5r/am5r-capsule.sh` | operator: source capsule | `26cd09af379f4425f24c3e61ed8aa318268c84d025527be3e408e32597490b79` |
| `ops/am5r/am5r-preflight.sh` | operator: queue and GPU check (reports on stderr) | `2280dd2bcea713751edcebc7bccca1d7487c528aea1ad9168e80ec7a0fd297d5` |
| `ops/am5r/am5r-build.sh` | operator: image build, and the one rebuild | `16424eb10ca6a329103865d8381bda1338e364e84c0bb265bd5d31287656df9a` |
| `ops/am5r/am5r-image.sh` | operator: the built image id, after its provenance and receipt checks | `6a020d8614b90766d7597b1e0177325b64c91df6ddc9dfc8df5628b3b6fa748d` |
| `ops/am5r/am5r-job-state.sh` | operator: a job's state, and its scontrol record when it ends | `56f3e3ffa0d8cab4bbf051611476fe13a9f6cf12cf5ed7cb5bb7f052be5dea46` |
| `ops/am5r/am5r-selftest.sh` | operator: submits the CPU selftest | `2ea474db02bc7b0dc2247e57f35437fd293dc4c4db9b238ebef8380608761a9f` |
| `ops/am5r/am5r-selftest-cpu.sbatch` | operator: CPU selftest in the image | `938d915d5fce6d0118ce92845db0a11d3c00acd7b1a7c33842fb4fc81e9d2783` |
| `ops/am5r/am5r-submit.sh` | operator: lane manifest, dry run, test-only check, submit, the rerun the rule allows | `7a950119f0e60b6e8a29a0f85dbdb44ea0b23612127d3fbe251ed28209bd20d6` |
| `ops/am5r/am5r-rerun-decision.sh` | operator: the mechanical rerun rule | `824a55829000dd20a14b04f30c741377be5ce1969a3fb635e8b0afd1a552f529` |
| `ops/am5r/am5r-extract.sh` | operator: extract and the replay checks | `265afa319f450122ea5f7b3808034a63e26d7f5e172aa37c86ae6083efa5bb66` |
| `ops/am5r/am5r-hand-sample.sh` | operator: the blind hand-check sample, its chunks and prompts | `5190f220f5108d789bd733e69d5bdba88f5082e2eb04f79d2af997190b131b02` |
| `ops/am5r/am5r-hand-label-mac.sh` | operator, on the Mac: the registered labelling of one stage (prepare, the CLI launch, the recorded subagent fallback, push) | `b9a99cf7e6c4e71966dda102d21d8d00dada4ea0b94066e12cd662e8c7b64096` |
| `ops/am5r/am5r-hand-merge.sh` | operator: audits the transcripts and merges a labelling stage; writes the one repair stage | `6625a9846881f5a1c360bb6d11828f83c478fe06f2ecdbbec3197080e2ac198f` |
| `ops/am5r/am5r-hand-receipt.sh` | operator: one stage's text-free receipt, committed before the join | `d07c17abc9f13a9ccaa0299210c08f8571183dbf02b56f2a330ecf752009ad99` |
| `ops/am5r/am5r-analyze.sh` | operator: analyze twice, tests (dev: dryrun-compare and power) | `15683ba56d732cfe9a18736c827aeddef67934d27fc369447929cf59e9942dad` |
| `ops/am5r/am5r-stage-evidence.sh` | operator: text-free staging and the text search | `e800ef610979d22bdb36a849132eebd89ce31717666d2fddeb8998511f2feaf2` |

Commands of the registered run, after the freeze. The names in capitals are values that exist only
then: FREEZE, the freeze commit's full id, and FREEZE8, its first 8 characters (every script that
takes a "commit short id" takes FREEZE8); IMAGE, the image id; JB, JS and JOB, the Slurm ids of the
build, the CPU selftest and the GPU job (each submitting script prints only the id it submits on
stdout, and its log lines on stderr); W, a new work directory on the operator's Mac outside the
repository; RECEIPT_COMMIT, the full id of the commit that holds the hand-label receipts. The host
root R is `~/cotcodec-runs/stage0/am5-ablated-cost-v1/` (the scripts' `reg` mode). Every script
appends a line to `R/ops/jobs.log`. The host scripts that run repository code (capsule, build,
selftest, submit, rerun-decision, extract, hand-sample, hand-merge, analyze) refuse a dirty
checkout or another commit; `am5r-checkout.sh` makes the clean checkout and refuses to go on
otherwise; `am5r-hand-label-mac.sh` refuses a dirty repository on the Mac or another commit;
`am5r-image.sh`, `am5r-job-state.sh`, `am5r-hand-receipt.sh` and `am5r-preflight.sh` read records
only and run no repository code; `am5r-stage-evidence.sh` copies records and runs its text search
with the system Python. No command waits: `am5r-job-state.sh` prints a job's state once and is
polled (exit 1 in any state that is not terminal), and when a job has ended it saves the whole
`scontrol show job` record to `R/ops/scontrol-J.txt`, because Slurm accounting is disabled on the
node; `am5r-rerun-decision.sh` refuses a job without that record.

```bash
# On the operator's Mac, in the repository (the branch that holds FREEZE):
bash ops/am5r/am5r-mac-bundle.sh reg FREEZE       # bundle -> R/bundles; bootstrap copies of
                                                  # am5r-env.sh and am5r-checkout.sh -> R/bootstrap;
                                                  # prints their SHA-256: they must equal section 16
# On the host:
bash ~/cotcodec-runs/stage0/am5-ablated-cost-v1/bootstrap/am5r-checkout.sh reg FREEZE
cd ~/cotcodec-runs/stage0/am5-ablated-cost-v1/checkout   # every later host command runs here
bash ops/am5r/am5r-capsule.sh reg FREEZE8
bash ops/am5r/am5r-build.sh reg FREEZE8 build                   # prints JB (1 H100, 5 minutes)
bash ops/am5r/am5r-job-state.sh reg JB                          # poll until it exits 0
IMAGE=$(bash ops/am5r/am5r-image.sh reg FREEZE8)                # one line, the image id, after
                                                                # the provenance and receipt checks;
                                                                # on a failed build:
#   bash ops/am5r/am5r-build.sh reg FREEZE8 rebuild (once, into overlay-build-vllm-FREEZE8-r2),
#   poll it, and capture IMAGE again; a second failure stops the run
bash ops/am5r/am5r-selftest.sh reg FREEZE8 "$IMAGE" heldout     # prints JS (CPU, no GRES)
bash ops/am5r/am5r-job-state.sh reg JS                          # poll until it exits 0
cat R/selftest-heldout-FREEZE8/exits.txt                        # all exit 0
bash ops/am5r/am5r-submit.sh reg FREEZE8 "$IMAGE" heldout check      # dry run and test-only check
bash ops/am5r/am5r-submit.sh reg FREEZE8 "$IMAGE" heldout submit     # prints JOB (70 minutes); a
                                                                     # failure before sbatch records
                                                                     # nothing; rerun it
bash ops/am5r/am5r-job-state.sh reg JOB                              # poll until it exits 0
bash ops/am5r/am5r-rerun-decision.sh reg FREEZE8 heldout JOB         # complete | rerun | no-rerun | void
#   on "rerun" only (am5r-submit.sh refuses without that record):
#   am5r-submit.sh reg FREEZE8 "$IMAGE" heldout rerun, poll it, and run am5r-rerun-decision.sh on
#   the rerun's id, which then replaces JOB below (its own "rerun" is void)
bash ops/am5r/am5r-extract.sh reg FREEZE8 heldout JOB
bash ops/am5r/am5r-hand-sample.sh reg FREEZE8 JOB          # the blind sample, chunks and prompts -> R/hand
# On the Mac, in the repository at FREEZE (clean):
bash ops/am5r/am5r-hand-label-mac.sh reg FREEZE8 first W cli   # claims the stage on the host
#   exit 3 when the CLI cannot start a session (expected): then, per chunk NN in order, one fresh
#   subagent (model claude-opus-5-5) whose whole prompt is W/first/prompt-NN-abs.txt, and:
#   bash ops/am5r/am5r-hand-label-mac.sh reg FREEZE8 first W push subagent \
#     ~/.claude/projects/PROJECT/SESSION/subagents     # the operator session's subagents/
# On the host:
bash ops/am5r/am5r-hand-merge.sh reg FREEZE8 first     # audits the transcripts; the final labels,
                                                       # or the one repair stage's chunks
bash ops/am5r/am5r-hand-receipt.sh reg FREEZE8 first
#   if the merge wrote a repair stage: the same three steps with "repair" in place of "first"
#   (am5r-hand-label-mac.sh, am5r-hand-merge.sh, am5r-hand-receipt.sh); no third stage
#   commit R/hand-check/ as program/evidence/RUNDATE/am5-ablated-cost-v1/hand-check/
#   (the receipts before the join; the staging copies the same files there); its id is
#   RECEIPT_COMMIT; nothing judge-derived of this run is written to the repository before it
RECEIPT_COMMIT=... bash ops/am5r/am5r-analyze.sh reg FREEZE8  # analyze twice (byte-identical), tests
bash ops/am5r/am5r-stage-evidence.sh reg FREEZE8 heldout:JOB
#   after the evidence commit: delete W and the session's subagents/ transcripts on the Mac
```

`am5r-analyze.sh` runs `scripts/memcredit_am5r.py analyze --population heldout --features
private/features-heldout.json.gz --hand-labels hand/hand-labels.jsonl --hand-labels-sha256 S
--hand-plan-sha256 P --output-dir out-FREEZE8-a` (and `-b`) in the checkout's `uv` environment
(`uv run --locked --offline`), S and P being the receipted digests of the final labels and the plan
(`R/hand-check/hand-labels.sha256.txt`, `hand-plan.sha256.txt`). It refuses to run without the
receipted labels or without RECEIPT_COMMIT (a full commit id), which it logs; `analyze` runs once
per input set and never overwrites an output directory. A fresh verifier reruns `analyze` from a
new clone at FREEZE, and the outputs must be byte-identical.
## 17. Freeze checklist

Before the freeze, by the orchestrator:

1. Two independent, sequential pre-freeze checks of this file, the config and the code of section
   16, by reviewers that did not draft them, and the corrections they require; their dispositions
   go in section 19.
2. The gauntlet question: resolved by D121. No gauntlet wave runs, and the run carries no gauntlet
   score (section 1.5).
3. If any code of section 16 changed after the development dry run, rerun the affected parts of it
   (at least `extract`, `analyze`, `dryrun-compare` and `power` on the dry run's run directory, and
   the tests on the host) and update its record. A change to the GPU job's code (`run`, `worker`
   and what they call) needs a new development GPU job within the dry run's 0.3 GPU-h.
4. Re-pin section 16 in a fill commit; run the tests locally and on the host.
5. Confirm on the host, at the fill commit, that the inputs of section 4 have their digests (the
   held-out ablated artifact and its summary, AM5's artifact, job 1487's thirteen files, AM1's
   held-out artifact, the dataset file) and that `git diff 9d66c4c4 --
   program/evidence/2026-10-15/am3-nonabstain-generality-v1 program/evidence/2026-10-16/am4-read-caps
   program/evidence/2026-10-16/am5-evidence-ablated` is empty.
6. The fill commit rewrites the status line (line 3) to the frozen wording that am3g uses
   ("**Status: frozen in `program/preregistrations/ledger.jsonl`; see the ledger row for the freeze
   time and `git_head_at_freeze`.**"). The file must then contain no to-be-decided marker and no
   placeholder in angle brackets. The orchestrator makes this edit, not the drafter.
7. The ledger row, by `uv run python scripts/preregister.py freeze am5-ablated-cost-v1
   program/preregistrations/am5-ablated-cost-v1.md`, in a commit that adds only that row (the
   freeze commit). A test freezes this file into a scratch ledger, so the command's text checks
   pass.

After the freeze: run section 16's commands once (the hand-label receipt is committed before
`analyze`), commit the text-free outputs, and have a fresh verifier rerun `analyze` from a new
clone and check that `results.json`'s hand-check labels and plan digests equal the committed
receipt's, and that the receipt commit precedes the analysis log's start line.

## 18. Priors (for the record; not tested)

- **Qwen3-8B:** COST_BELOW_GAIN is the likeliest reading: it switched on 1 of 63 development
  pools at K = 8, and that switch was judged correct (a single-session-preference question).
- **OLMo-2:** NOT_SEPARATED: its development cost rate at K = 8 (5 of 63) is almost exactly its
  held-out gain rate (27 of 347); a COST_ABOVE_GAIN would need the held-out rate near 0.15 or more.
- **Qwen3.5-9B:** NOT_SEPARATED, leaning below: development 3 of 63 against a gain rate of 26 of
  347.
- **The hand check:** agreement with the judge as high as AM5's (18 of 18) and am3g's (274 of
  278); a few switched replies that decline outside the four patterns, most likely for OLMo-2.
- **The replay control:** R1 and R2 pass (section 8, V3).

## 19. Review log: the independent checks

Two independent, sequential checks are required before the freeze (D121). None has run yet.
