# am3-nonabstain-generality-v1: does the non-abstention keep rule hold for other readers on held-out questions, and what does it cost on questions that have no answer? (LongMemEval-S, GPU)

**Status: frozen in `program/preregistrations/ledger.jsonl`; see the ledger row for the freeze time and `git_head_at_freeze`.** Drafted on branch `stage0/am3-nonabstain-generality` from `main`
at `957a3c0a`, as decision D118 specifies (`program/decisions.md`). The orchestrator froze it
with `scripts/preregister.py` after three independent pre-freeze checks (D118) and the checklist
of section 17. A material change after the freeze is a new experiment id.

This registration runs two GPU jobs and one image build, about 0.7 physical GPU-h, capped at 2.08
(section 11). It tests one rule, already confirmed for one reader and one judge, on two new
readers (H1), and measures what the rule costs on LongMemEval-S's unanswerable questions (H2).
Every hypothesis was shaped by development results, and the held-out questions were used before
by AM1 and `am1-keepset-search-v1` with Qwen3-8B. Section 1 lists both before anything else.

## 1. Disclosures

### 1.1 What is already known about the held-out questions

The 347 questions of H1 are AM1's confirmatory set (`am1-memory-credit-v1`, ledger row 23;
`experiments/am1/am1-memory-credit-v1.yaml`, `confirmatory_set`). Two registrations used them,
both with the Qwen3-8B reader, which is this registration's anchor.

- **AM1** (job 1458) ran all 256 subsets of both pool arms of every question with Qwen3-8B and
  judged every distinct reply with Qwen3-32B and Qwen3-8B. Its tables and results are committed
  (`program/evidence/2026-10-16/am1-confirmatory/`). Its G2 hand check read 120 held-out
  Qwen3-8B replies (agent labels).
- **`am1-keepset-search-v1`** (ledger row 24) computed, from those tables and replies, the very
  comparison H1 makes, for Qwen3-8B (`program/evidence/2026-10-16/am1-keepset-search/RESULTS.md`):
  - retrieved arm: nonabstain-BM25 0.571 against BM25 top 4 0.458, 39 gained and 0 lost
    (NONABSTAIN_HELPS); gold arm (descriptive) 0.663 against 0.573, 31 against 0;
  - against all 8: 33 against 17 (retrieved), 49 against 20 (gold), descriptive;
  - BM25 top 4's reply abstains on 116 of 347 retrieved pools; the rule leaves it on 71; every
    4-subset abstains on 45; 13,598 of 24,290 retrieved 4-subset replies abstain;
  - per question type, the stop rule's reads, and the abstention counts by pattern.
- **What no one has.** No reply of OLMo-2-1124-7B-Instruct or Qwen3.5-9B exists for any held-out
  question. H1's two readers are new; the anchor's held-out numbers are a replay check of
  published figures, not new information (section 8, V3).
- **AM3 did not use the held-out questions.** AM3 (exploratory) ran the development split only;
  its script refused held-out paths (`scripts/memcredit_am3.py`, `check_path`), and its
  independent checker confirmed that its 63 questions are exactly the development split.

### 1.2 What is known about the abstention questions

- **Never used by AM1, AM1b, AM1d, AM3 or `am1-keepset-search-v1`.** Every AM1 config sets
  `usable.exclude_abstention: true`, and `harness.memcredit_study.usable_reason` returns
  "abstention" for an id ending in `_abs` before any other rule
  (`harness.memcredit.is_abstention`). The split (`experiments/am1/memcredit-split-v1.json`) and
  every study artifact were built from the usable set only; the split records 30 questions
  dropped for that reason. Step 0's demo used `memcredit-step0-v1.yaml`, which also sets
  `exclude_abstention: true`. AM1b, AM1d and `am1-keepset-search-v1` read AM1's tables and
  passes, and AM3 the pilot's artifact, so none of them saw an abstention question.
- **What the program holds about them.** Step 0's CPU census
  (`program/evidence/2026-10-15/am1-step0/census/census-e87a6c1a.json`) records, for each of the
  30, its type, user-turn count and gold-turn BM25 ranks; no reader output. Two of the 30 ids
  (`2133c1b5_abs`, `29f2956b_abs`) are listed in the old program's 32-task LongMemEval-S panel
  manifest (`legacy/experiments/memory/stage1-longmemeval-screen.yaml`,
  `legacy/harness/memory_trials/public_sources.py`); the repository holds their ids only and no
  model output. A search of the repository for the 30 ids finds nothing else.
- **Their non-abstention twins were used.** 29 of the 30 share an id prefix with a non-abstention
  question of LongMemEval-S (LongMemEval made each abstention question from one): 22 twins are
  among AM1's 347 held-out confirmatory questions (AM1, `am1-keepset-search-v1` and this
  registration's H1 run them); 5 are development questions (the pilot, AM1d and AM3 ran them, and
  one, `09ba9854`, was also a Step 0 demo question); 2 are Step 0 demo questions in the split's
  held-out part that AM1 excluded from its 347 (`6aeb4375`, `gpt4_70e84552`; Step 0 ran all 256
  subsets of both); 1 has no twin. (Check 1 found that the first draft counted 4 development and
  3 Step 0 twins, because `twin_membership` tested the Step 0 exclusion before the split; the
  order is fixed and `abstention-facts` recounted.) No haystack session id is shared between an
  abstention question and its twin, but turn texts are. By SHA-256 of AM1's memory text
  (`abstention-facts`, text-free): 27 of the 30 abstention pools hold at least one memory whose
  text is one of the twin's user turns; 89 of the 240 pool memories are among the twin's user
  turns, and 70 are in the twin's own retrieved pool. H1's and H2's populations are therefore
  related through 22 twins that share memories; section 6.4 reports the natural-mix interval with
  the twins resampled separately and together.
- **The old program's audits.** Its CPU audits aligned third-party released outputs to all 500
  LongMemEval-S tasks, the 30 abstention questions included: SodaMem's released artifacts
  (`legacy/wiki/log.md`, 2026-08-17: every released row aligned to all 500 tasks, "including 30
  abstentions", and a stored self-judge score recomputed) and MemPalace's retrieval runs over all
  500 tasks (2026-08-14). None of those outputs came from this registration's readers, prompt or
  pools, and this program holds no reader output of its own for the abstention questions.
- **What the drafter opened.** The drafter counted the `_abs` ids, types and turn counts in the
  host's dataset file, printing ids and counts only, and built their pools on the host CPU with
  `scripts/memcredit_am3g.py prepare-abstention`, which writes the pool texts to a host-only
  artifact and a text-free summary (ids, digests, pool coordinates, BM25 ranks and scores, each
  full-pool prompt's length in characters, the decoys' ids and the twin facts). The drafter read
  the summary and no memory, question or explanation text. Before the freeze, the image's CPU
  selftest (job 1469, no GRES) rendered the abstention population's prompts with each reader's
  and judge's tokenizer and recorded only their lengths: at most 1,027 (Qwen3-8B), 972 (OLMo-2)
  and 1,040 (Qwen3.5-9B) tokens, and 272 for the judge items (section 15). No model ran on an
  abstention question.

### 1.3 Development work that shaped the design

- **AM3** (`program/evidence/2026-10-16/am3-reader-replication/README.md`, exploratory, 63
  development questions, jobs 1462 and 1466) shaped H1: the readers, their engines, the 71
  requests per pool and the anchor. On the retrieved arm under Qwen3-32B the rule gained 4 and
  lost 0 for OLMo-2 (p = 0.125) and gained 3 and lost 0 for Qwen3.5-9B (p = 0.25); the anchor
  gained 1 and lost 0 there, against 39 and 0 on held-out data. Under the second judge the rule
  lost 6 cells on 3 questions, mostly that judge's error of accepting "I don't know" on
  answerable questions (D118).
- **AM1d** chose the rule and its four abstention patterns on development data (committed at
  `7465903f` before it read any reply); they are used unchanged. The patterns were written for
  Qwen3-8B's development replies. A refusal by OLMo-2 or Qwen3.5-9B worded outside them counts as
  an answer, so the rule may keep it; each cell's abstention counts and the gains whose reply
  hedges (section 6.4) describe how the patterns fit the new readers, and the blind hand check
  (section 8) reads such replies as they stand.
- **H2's power** was estimated from AM3's development features, before any abstention output
  existed, and it decided that H2 is a registered description rather than a test (section 7.2).

### 1.4 Readers and judges

- **OLMo-2-1124-7B-Instruct.** Apache-2.0 in its card's front matter, ungated, fetched without
  credentials (AM3, job 1460). The card's "License and use" section also says the model is
  "intended for research and educational use" and is subject to the Gemma Terms of Use. This
  research use fits those terms, and accessing the model required accepting nothing.
- **Qwen3.5-9B is not replay-exact.** vLLM 0.31.0 refuses batch-invariant mode for GDN attention,
  so it runs in vLLM's default mode (AM3). Its replies can depend on the batch schedule. The
  schedule is fixed by the request list and order, the engine settings and the hardware, all
  pinned. In the development dry run, with AM3's request list and order in a freshly built image,
  it repeated all 8,946 of AM3's job 1466 replies in tokens and log-prob bits (section 15). That
  shows the schedule is reproducible, not that the replies are invariant to it: its held-out
  replies carry no batch-invariance guarantee, and its readings say so.
- **OLMo-2** runs in batch-invariant mode through vLLM's Transformers backend. AM3 did not replay
  it; the dry run did, 8,946 of 8,946 identical in tokens and log-prob bits against job 1466
  (section 15).
- **The anchor** is AM1's reader in AM1's eager batch-invariant engine. Its replies must equal
  job 1458's token for token (section 8, V3: tokens and finish reasons are gated, log-prob bits
  reported), which AM1's G1 and AM3's anchor check (2,272 of 2,272 against the pilot's eager
  pass) support.
- **The second judge's known error.** Qwen3-8B called the reply "I don't know." correct on 49 of
  347 held-out validation items (AM1) and 11 of 63 development items (AM3), and AM3's
  second-judge losses were mostly that error. On answerable questions its readings are
  descriptions only. On abstention questions accepting "I don't know." is right, so that error
  does not bias H2; its other errors there are measured only by the validation items of section
  6.3, and its H2 figures are descriptions.

### 1.5 No gauntlet score (D118)

As in D111 and D115, the registration continues a confirmed line: it runs a confirmed rule on new
readers and a new question type, under 8 GPU-h. No gauntlet wave runs, and it carries no gauntlet
score. Two independent pre-freeze checks are required instead.

## 2. Question

On LongMemEval-S, with AM1's prompt, BM25 user-turn pools of 8 memories and a keep budget of 4:

- **H1 (confirmatory).** Does keeping the best-BM25-ranked 4-subset whose reply does not abstain
  change accuracy against BM25 top 4 for OLMo-2-1124-7B-Instruct and for Qwen3.5-9B, on AM1's 347
  held-out answerable questions (retrieved arm, Qwen3-32B judge)?
- **H2 (descriptive, registered estimand).** On LongMemEval-S's 30 abstention questions, how
  often does the rule turn a correct abstention by BM25 top 4 into an answer judged wrong, for
  each of the three readers? And what does that cost at LongMemEval-S's own mix of answerable
  and unanswerable questions?

`am1-keepset-search-v1` answered H1's question for Qwen3-8B. The delta here is generality across
reader families and engines, and the rule's cost where abstaining is the right answer.

## 3. What it decides and what it does not

It decides H1's reading per reader (NONABSTAIN_HELPS, NONABSTAIN_HURTS or NO_DETECTED_DIFFERENCE,
a directional reading standing only when the blind hand check of the discordant cells confirms
it; VOID, JUDGE_DEPENDENT or PENDING_HAND_CHECK under sections 7.1 and 8). H2 is a registered description: its estimand, intervals
and labels are fixed here and reported regardless of outcome, but it decides nothing (section
7.2). The gold arm, the second judge, the question types, the stop rule's reads, the
natural-mix net effect and every comparison with all 8 are descriptive.

It does not decide:
- anything for other prompts (AM1's prompt tells the reader to say "I don't know"), retrievers,
  pool sizes, budgets, memory units or judges;
- anything about other unanswerable questions than LongMemEval-S's 30 (made by editing an
  answerable question so that it asks about something the history does not contain);
- whether the rule beats keeping all 8 (a description);
- why the readers abstain where they do;
- anything about Qwen3.5-9B's replies under another batch schedule.

## 4. Identity and pins

| Item | Pin |
|---|---|
| Experiment id | `am3-nonabstain-generality-v1` (this file; config `experiments/am3/am3-nonabstain-generality-v1.yaml`) |
| Data | LongMemEval-S cleaned, `xiaowu0162/longmemeval-cleaned` @ `98d7416c24c778c2fee6e6f3006e7a073259d48f`, `longmemeval_s_cleaned.json`, 277,383,467 bytes, SHA-256 `d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442`, MIT; host only (Step 0's fetch receipt) |
| Split | `experiments/am1/memcredit-split-v1.json`, SHA-256 `4fa1b774d4131080855d668ac8f00f5cb07d49cf741f2051d5f8d96577edb3e3` |
| Held-out population (H1) | AM1's confirmatory set: 347 ids, SHA-256 of the newline-joined ids `d4f024fbcda5394984a46c421cd938f2b6db6067fef0f21a5c6e72359b27e50a`; AM1's held-out study artifact, host `~/cotcodec-runs/stage0/am1-memory-credit-v1/study-artifact.json`, SHA-256 `f23bca047dc7246c5a8db12f67a76a2ea36304d8669dc5c62ae6c42821f73eb7` (unchanged since AM1; both arms) |
| Abstention population (H2) | every LongMemEval-S id ending in `_abs`: 30 ids (knowledge-update 6, multi-session 12, single-session-user 6, temporal-reasoning 6), SHA-256 of the newline-joined sorted ids `e08d46ccab4604e4e0bd61ff1d140f0e0648b43070c70d63bc968d3ac1aa0513`; study artifact (retrieved arm, validation decoys), host `~/cotcodec-runs/stage0/am3-nonabstain-generality-v1/inputs/abstention-artifact.json`, 186,699 bytes, SHA-256 `f1c241baeaeddcd5690daa22337612843b049059c354fe25fe348947e346a0f5`, built at `ffa8675c`, read-only |
| Development population (dry run only) | the pilot's artifact, 63 ids, SHA-256 `15567cf14a0c38c1f9edec1f47feceb2a6fccf116338e5957182d03f1d996ebc` |
| Anchor reference (R1, R2) | job 1458's `reader-gpu0`, `judge32-gpu0`, `judge8-gpu0` and `judge-items.json` (the ten digests in the config, `populations.heldout.reference`, equal to `am1-keepset-search-v1`'s pins); AM1's committed held-out tables `program/evidence/2026-10-16/am1-confirmatory/analysis/tables.json.gz`, SHA-256 `841e79452d7af6441492abfce64d85cadf5b51415cc7e0461df76ce228df0729`, uncompressed `2d3574be5d3686d73b73dc2d1b36ed3c9b04b23731078bcb6b5f92b83cc3a9cd` |
| Readers | `Qwen/Qwen3-8B` @ `b968826d9c46dd6066d109eabc6255188de91218` (anchor; receipt `b9e3a74d...`, root `325ab760...`); `allenai/OLMo-2-1124-7B-Instruct` @ `470b1fba1ae01581f270116362ee4aa1b97f4c84` (receipt `4120a5c9...`, root `ec7f6955...`); `Qwen/Qwen3.5-9B` @ `c202236235762e1c871ad0ccb60c8ee5ba337b9a` (receipt `0a9e052d...`, root `9845026d...`). AM3's reader blocks, unchanged; full digests in the config (`models`) |
| Judges | `Qwen/Qwen3-32B` @ `9216db5781bf21249d130ec9da846c4624c16137` (primary; receipt `06e4a7e9...`, root `8fcd9106...`); Qwen3-8B as above (second); AM1's engines and sampling |
| Reader prompt | Step 0's template (the pilot config's `prompt`), SHA-256 of the template text `e63a0f995fe94ee72d6dcda7462a09c20e83f86dcc8252a53cdefb1ccf6fb37c`, thinking off for both Qwen readers |
| Judge prompts | LongMemEval's `get_anscheck_prompt` (src/evaluation/evaluate_qa.py at `9e0b455f4ef0e2ab8f2e582289761153549043fc`, MIT): the answer-check templates as AM1 ported them (`harness.memcredit_study.JUDGE_TEMPLATES`, SHA-256 `2e27234d4c7d50a1fd99da3e8d3c97704a1f10cc9d52185924b6d8ece3ef71d4`), and the abstention template (`scripts/memcredit_am3g.py`, `ABSTENTION_TEMPLATE`), SHA-256 of its text `5c0b365a1e1d06db36377c735432b56e122ca3c428f89faf61d43a0d5a7e050b`, equal word for word to the program's archived port (`legacy/harness/memory_trials/longmemeval_judge.py`, SHA-256 `77aed59acdf42f0848f59f73cc3f61f0d625300b16a18b35797bae139b8dfee1`, read-only under `legacy/`, which pinned the evaluator source `ecce9c4c...`; a test checks the two agree on the host; the file is not in the image, so it is not a code pin of section 16) |
| Abstention patterns | AM1d's four (`scripts/memcredit_label_free.py`), SHA-256 `031bee27e934a772f3419e38f9956d33dbea01096e6657e67426fd8a399d935f` |
| Engine and image | vLLM 0.31.0 (`db9527a46873454610df6dbedf79a36d6bf1a7f6`), cotcodec-vllm cu129 overlay built by `scripts/build_vllm_overlay_on_h100.sh` from the freeze commit's source capsule on the base `docker.io/vllm/vllm-openai@sha256:b18abb2df97b8f798e81862bd93f872ea18613372e2c3adc0cc2ac21e66ac12f` (AM3's base); the image id is recorded by the build and every job checks it through the lane's provenance verification |
| Code | section 16 |

## 5. Units, pools and requests

- **Questions** are the unit of resampling: the 347 held-out questions (H1) and the 30 abstention
  questions (H2).
- **Memory unit**: one user turn with its session date, at most 1,500 characters (longer turns cut
  with " [...]"), as in AM1.
- **Pools** (k = 8, chronological; bit i of a mask keeps memory i):
  - `retrieved` (H1 and H2): the BM25 top 8 user turns (Okapi with Lucene's idf, k1 1.5, b 0.75,
    AM1's stopwords). For the held-out questions these are AM1's pools, unchanged. For the
    abstention questions `memcredit_am3g.retrieved_pool` builds them with AM1's functions
    (`rank_user_turns`, `memory_entry`, `chronological`); on the 63 development questions it
    reproduces the committed artifact's retrieved pools, 63 of 63 (`dev_retrieved_pool_check`).
  - `gold` (held-out only, descriptive): AM1's gold arm, unchanged. It is not built for the
    abstention questions, where it is not defined.
- **Requests.** Per pool, the 70 4-subsets (masks ascending) and the full pool (mask 255): 71
  requests. Held-out: 347 x 2 x 71 = 49,274 per reader. Abstention: 30 x 71 = 2,130 per reader.
- **Readers.** Greedy, at most 64 new tokens, the sampled token's log-prob, each in its own chat
  template, AM1's prompt (with its instruction to say "I don't know"). Qwen3-8B: eager,
  batch-invariant (AM1's engine). OLMo-2: eager, batch-invariant through the Transformers backend;
  if that step does not complete, a default-mode fallback step runs (declared here, as in AM3).
  Qwen3.5-9B: eager, vLLM's default mode, prefix caching off, text only.
- **Judges.** Every distinct (question, stripped reply) of the three readers, plus validation
  items (section 6.3), scored by Qwen3-32B (primary) and Qwen3-8B (second), eager,
  batch-invariant, greedy, 10 tokens, thinking off. The label is LongMemEval's rule: "yes" occurs
  in the case-folded reply. An abstention question is judged with the abstention template, its
  "answer" field (an explanation of why it cannot be answered) in the Explanation slot; every
  other question with its type's answer-check template. Replies that hit the 64-token cap are
  judged as they stand.

## 6. Estimands

### 6.1 The rule and the BM25 order

`nonabstain-BM25` (AM1d's `nonabstain@70`, `am1-keepset-search-v1`'s H-C): read a pool's 70
4-subsets in ascending sum of their four BM25 ranks, equal sums to the lexicographically smaller
sorted rank tuple (`memcredit_label_free.rank_key`), and keep the first whose reply does not
abstain; keep BM25 top 4 (always read first) when every 4-subset abstains. A reply abstains when,
normalized by `harness.memcredit.normalize_answer`, it is empty or matches one of the four
patterns of section 4. The rule reads no label. Its outcome on a pool is the judge's label of the
chosen 4-subset's reply; BM25 top 4's is the label of its reply; all 8's of the full pool's
(`memcredit_am3.table_record`, unchanged).

### 6.2 H1

Per H1 reader (OLMo-2, Qwen3.5-9B), retrieved arm, primary judge, over all 347 questions: b (the
rule right, BM25 top 4 wrong), c (the reverse) and the accuracy difference (b - c)/347.

### 6.3 H2

Per reader (Qwen3-8B, OLMo-2, Qwen3.5-9B), retrieved arm, primary judge with the abstention
template, over the 30 abstention questions:

- **b2**, the cost: BM25 top 4 judged correct (it identified the question as unanswerable) and
  the rule's choice judged wrong; **c2** the reverse;
- the **cost rate** b2/30 with its exact Clopper-Pearson 95% interval (the registered H2
  quantity), and the net loss (b2 - c2)/30;
- the accuracies of BM25 top 4 and of the rule, each with its Clopper-Pearson 95% interval;
- how often BM25 top 4's reply abstains and how often the rule leaves it;
- the rule's opportunities to cost: BM25 top 4's abstentions judged correct, and b2 per such
  abstention with its Clopper-Pearson interval (`cost_per_correct_top4_abstention`), which does
  not depend on how often the reader abstains;
- b2, c2 and both accuracies in two strata (`by_near_miss_memory`): pools that hold a memory
  LongMemEval flags as evidence (`has_answer`, the near miss the question was edited from) and
  pools that hold none;
- the blind hand check's H2 part (section 8): b2_hand and c2_hand per reader, with Holm across
  the three, and hand-against-judge agreement, beside the judge's figures.

The rule leaves BM25 top 4 only when top 4's reply abstains, so b2 counts abstentions judged
correct that the rule traded for a reply judged wrong, and c2 can be positive only when the judge
rejects an abstaining top-4 reply and accepts the reply the rule chose (for instance a correct
refusal phrased outside the four patterns).

**Abstention-judge validation items**, per abstention question: its explanation as the response
(expected yes), "I don't know." (expected yes), and a decoy (expected no): the reference answer
of a development question of the same type, drawn with `random.Random(f"44:{question_id}")` from
the sorted development ids of that type. Decoys come from development questions so that no
held-out answer enters the artifact.

### 6.4 Descriptive outputs

- **The anchor on the held-out questions**: its b and c on both arms; with V3 passed they equal
  `am1-keepset-search-v1`'s (39 and 0 retrieved, 31 and 0 gold).
- **The gold arm**: the rule against BM25 top 4 for all three readers, with Holm across them, as
  descriptions.
- **The second judge**: H1's and H2's comparisons under Qwen3-8B, with Holm, as descriptions.
- **Every cell** (reader x judge x arm, both populations; `memcredit_am3.cell_summary`,
  unchanged): the accuracies of BM25 top 4, the rule, all 8 and the oracle best 4-subset with
  question-bootstrap intervals; the rule against BM25 top 4, the rule against all 8 and BM25 top
  4 against all 8 (b, c, exact p, intervals); the abstention counts; the stop rule's reads.
- **The stop rule's reads**: the position in the BM25 order of the first 4-subset whose reply
  does not abstain (the answering call included), or 70 when none answers; mean, median, 90th
  percentile, maximum, the counts at 1, at most 8 and at most 16, and the distribution.
- **Per question type**, both populations, both judges: the three accuracies, b and c.
- **Gains whose reply hedges**: per reader, H1's gains (the rule's reply judged right, top 4's
  wrong) whose reply offers alternatives (`HEDGE_PATTERN`: "or", "either", "possibly", "perhaps",
  "maybe", "might", "could be", "not sure", "unsure", as words), which can contain the right
  answer among wrong ones; a flag per reply in the features (`hedge`), reported as a count.
- **The net effect at LongMemEval-S's mix**, per reader and judge: the rule's correct answers
  minus BM25 top 4's over the 347 + 30 questions run (a count); the rate at LongMemEval-S's own
  mix of 470 answerable and 30 abstention questions, 0.94 x (b - c)/347 + 0.06 x (c2 - b2)/30; and
  the break-even unanswerable share, with g = (b - c)/347 the net gain per answerable question and
  l = (b2 - c2)/30 the net loss per unanswerable one:
  - l <= 0 <= g (the rule never loses net on either population, g = l = 0 included): 1;
  - g <= 0 <= l: 0;
  - g > 0 and l > 0: g/(g + l), the unanswerable share above which BM25 top 4 is ahead;
  - g < 0 and l < 0: reported as undefined; there is a crossing at g/(g + l), above which the rule
    wins (it loses on answerable questions and gains on unanswerable ones).
  Intervals: percentile, from 10,000 bootstrap resamples (numpy `default_rng(42)`): the sorted
  resampled values at indices floor(0.025 (n - 1)) and ceil(0.975 (n - 1)). The break-even
  interval uses only the resamples where the share is defined, and the number where it is not is
  reported. Two resampling schemes, both descriptive: each population's questions resampled
  separately (`natural_mix`), and the 22 abstention questions whose twin is among the 347
  resampled together with their twin as one unit, the other questions within their population
  (`natural_mix_linked_twins`; the twins share memories, section 1.2). Both treat the 347 as
  representative of LongMemEval-S's answerable questions, which they are not exactly (they
  exclude assistant-turn and development questions).

### 6.5 Intervals

Accuracy and paired-difference intervals are question-cluster percentile bootstraps
(`harness.memcredit_study.cluster_bootstrap`, 10,000 resamples, numpy `default_rng(42)`), 95%
two-sided, as AM3 and `am1-keepset-search-v1`. Paired differences also get the exact conditional
interval that inverts the McNemar test (`memcredit_keepset_search.paired_reading`). Rates over the
30 abstention questions get exact Clopper-Pearson intervals (`harness.memcredit.clopper_pearson`).

## 7. Hypotheses and decision rules

### 7.1 H1 (confirmatory): the rule against BM25 top 4 for OLMo-2 and Qwen3.5-9B

**Test.** Per reader, the exact two-sided McNemar test on b and c (section 6.2): p = min(1, 2
P(X <= min(b, c))), X ~ Binomial(b + c, 1/2), exact rational arithmetic, p = 1 when b + c = 0
(`memcredit_keepset_search.mcnemar_exact`).

**Family and correction.** The two readers, alpha 0.05, Holm's step-down: the smaller p is
compared with 0.025 and, if it is at or below it, the larger with 0.05; equivalently the
Holm-adjusted p (the running maximum of (3 - i) p_(i)) is compared with 0.05
(`memcredit_am3g.holm`). With c = 0 the first step needs b >= 7 (p = 0.0156; b = 6 gives 0.031)
and the second b >= 6.

**Judge-based readings**, per reader, from its Holm decision:
- **NONABSTAIN_HELPS** if rejected and b > c;
- **NONABSTAIN_HURTS** if rejected and b < c;
- **NO_DETECTED_DIFFERENCE** otherwise.

**Confirmation by the blind hand check** (section 8). H1's b and c are Qwen3-32B labels of OLMo-2's
and Qwen3.5-9B's replies, which nothing else validates: G-J1 replays AM1's validation items and
cannot catch an error the judge makes on these readers' replies. So every discordant cell of each
reader (both replies of every question where the rule's choice and BM25 top 4 are judged
differently) is hand-labelled blind, and the readings are fixed now as follows:
- per reader, b_hand and c_hand are counted over its judge-discordant questions from the hand
  labels of the two replies (b_hand: the rule's reply labelled 1 and top 4's 0; c_hand the
  reverse); the same exact McNemar test, with Holm across the two readers at 0.05, gives the
  hand-based label (`memcredit_am3g.hand_check`);
- a judge-based NONABSTAIN_HELPS stands as **NONABSTAIN_HELPS** only if the hand-based label is
  also NONABSTAIN_HELPS; a judge-based NONABSTAIN_HURTS stands only if the hand-based label is
  NONABSTAIN_HURTS; otherwise the reading is **JUDGE_DEPENDENT** (`confirm_reading`);
- a judge-based NO_DETECTED_DIFFERENCE stays **NO_DETECTED_DIFFERENCE** whatever the hand
  labels say (the hand check confirms; it never creates a reading), and the hand-based label is
  reported beside it;
- too few cells: the hand test can reject only if enough discordant questions keep their
  direction under the hand labels (with c_hand = 0, 7 at Holm's first step and 6 at its second).
  A reader whose judge-based reading is directional but whose hand-labelled cells are too few,
  or split, to reject reads JUDGE_DEPENDENT; a reader with no discordant question has nothing to
  label and reads NO_DETECTED_DIFFERENCE;
- labels that do not cover the sample exactly (an item unlabelled, labelled twice, outside the
  sample or not 0 or 1) make every directional reading JUDGE_DEPENDENT; without labels a
  directional reading is PENDING_HAND_CHECK and no decision follows (the registered `analyze`
  refuses to run without the receipted labels, section 16).

**Precedence.** VOID (V3) over JUDGE_DEPENDENT from G-J1 over the hand check: a void run reads
VOID whatever else holds, and a G-J1 failure reads JUDGE_DEPENDENT before the hand check is
consulted (`analyze_registered`).

NONABSTAIN_HELPS licenses, for that reader: "keeping the best-BM25-ranked 4-subset whose reply
does not abstain (AM1d's four patterns) is more accurate than BM25 top 4, by (b - c)/347 with
its intervals" (AM1's prompt, the Qwen3-32B judge confirmed by blind agent labels of the
discordant cells, LongMemEval-S held-out answerable questions, BM25 user-turn pools, 4 of 8). For
Qwen3.5-9B, and for OLMo-2 if its pass comes from the default-mode fallback, the scope adds "in
vLLM's default mode and this registration's batch schedule" (`h1.readers.*.scope`,
`engine_mode`). NONABSTAIN_HURTS licenses the reverse in the same scope. NO_DETECTED_DIFFERENCE
and JUDGE_DEPENDENT license nothing. Both readers reading NONABSTAIN_HELPS, with the anchor's
replayed 39 against 0, would say the rule's gain on answerable questions holds across the three
readers tried.

**What the licence amounts to.**
- *A count, not a size.* The rule leaves BM25 top 4 only when top 4's reply abstains, and an
  abstaining reply is almost never judged correct on an answerable question, so c is near 0 by
  construction. NONABSTAIN_HELPS then means that the gains reach Holm's threshold under both the
  judge and the hand labels: with no hand-confirmed loss, at least 7 hand-confirmed gains at
  Holm's first step (6 at its second). It says that the rule gains on some held-out questions for
  that reader. How much is the accuracy difference (b - c)/347 with its exact conditional and
  bootstrap intervals (section 6.2), which is reported beside every reading and is part of the
  licensed statement.
- *A read cost.* The rule calls the reader until a 4-subset's reply does not abstain: up to 70
  calls per pool (of the 71 requests run here; the 71st is all 8), against BM25 top 4's one. The
  stop rule's reads (section 6.4) give the distribution per reader. The licence compares accuracy
  only and says nothing for a setting where that cost matters.
- *Patterns from another reader.* The four abstention patterns were chosen on Qwen3-8B's
  development replies (section 1.3); the statement is about the rule with those patterns, not
  with patterns fitted to OLMo-2 or Qwen3.5-9B.

**Why this family and this test.** D118 names the two readers and Holm. The exact McNemar test is
`am1-keepset-search-v1`'s H-C test, so the anchor's reading and the new readers' are the same
statistic. Holm controls the family-wise error at 0.05 and is at least as powerful as
Bonferroni. Under the primary judge c is expected near 0 (an abstaining top-4 reply is almost
never judged correct: 6 of 13,598 held-out abstaining 4-subset replies for Qwen3-8B; 0-8 of
about 2,200-2,600 per reader and arm on development), so the test is in effect
one-directional, as H-C's was. Requiring the hand-based test to agree costs power only where the
judge's discordant labels are wrong, which is the case it is there to catch.

### 7.2 H2 (descriptive, registered estimand): the rule's cost on the abstention questions

**Why H2 is not a test.** With 30 questions and Holm across three readers, the exact McNemar
test rejects at its first step only when b2 >= 7 (with c2 = 0). The development data put the
rate of such discordant pairs low (section 9): treating each development pool's gold-free
4-subsets as an unanswerable question's subsets, the rule would leave an abstaining BM25-best
subset for an answering one on 3 of 63 retrieved pools for Qwen3-8B, 11 of 63 for OLMo-2 and 4 of
63 for Qwen3.5-9B. At those rates the test's power is 0.0004, 0.26 and 0.002 at Holm's strictest
step and at most 0.43 at alpha 0.05. At the anchor's held-out switching rate on answerable
questions (71 of 347) it is 0.42-0.60. Power reaches 0.8 only when the cost rate is about 0.3 or
more. A test would therefore most likely return NO_DETECTED_DIFFERENCE whether or not the cost is
real, and that label would read as safety it does not show. The direction is also fixed by the
rule's construction (it leaves BM25 top 4 only for an abstention, which is the right answer
here), so the test would mostly ask whether b2 reaches 7, a magnitude threshold rather than a
hypothesis. What a deployer needs is the size of the cost and the mix at which it outweighs the
gain, and those are estimated at any outcome.

**What is registered.** For each reader, the cost rate b2/30 with its exact Clopper-Pearson 95%
interval is the H2 quantity, reported with the other figures of section 6.3 and the natural-mix
summary of section 6.4. With 30 questions the interval is wide: 0 of 30 gives [0, 0.116], 3 of
30 [0.021, 0.265], 6 of 30 [0.077, 0.386], 9 of 30 [0.147, 0.494].

**Description labels** (no decision; `h2.decides` is false): the exact McNemar test per reader,
Holm across the three readers at 0.05, labelled NONABSTAIN_COSTS (adjusted p <= 0.05 and b2 >
c2), NONABSTAIN_SAFE (adjusted p <= 0.05 and b2 < c2) or NO_DETECTED_DIFFERENCE. These are
reported with the test's power (section 9). NO_DETECTED_DIFFERENCE does not say the rule is safe
on unanswerable questions.

### 7.3 Multiplicity across hypotheses

H1 carries its own Holm correction. H2 and the descriptive outputs carry no decision. No claim is
made from "either of" H1's readers beyond what each reading licenses.

## 8. Validity checks, void and kill rules

`scripts/memcredit_am3g.py` evaluates every check below. Each failure is a named error whose text
begins with its rule (`VOID (V1, ...)`, `VOID (V2, ...)`, `VOID (V3, ...)`); none surfaces as a
traceback: the host commands catch a missing or unreadable input that no named check caught and
report it as `VOID (V2, incomplete): an input is missing or unreadable`, with its cause (the GPU
job's driver and workers record their own failures in `summary.json`).

- **Freeze gate.** `run` and `worker` (the GPU job), `extract`, `hand-sample` and the registered
  `analyze` refuse the held-out and abstention populations, and `selftest` and `plan` refuse the
  held-out population, unless the ledger holds a row for `am3-nonabstain-generality-v1` whose
  SHA-256 equals this file's and every code pin of section 16 matches the working tree (parsed
  from this file; in the GPU job, the image's copy of the freeze commit, which holds every pinned
  file). The gate runs before any input of those populations is opened. The same commands run
  those populations only with the pinned config path, `experiments/am3/am3-nonabstain-generality-v1.yaml`
  (`check_config_binding`; its SHA-256 is pinned in section 16), so a `--config` pointing at
  another file is refused. `prepare-abstention`, `abstention-facts`, and `selftest` and `plan` of
  the abstention population, run before the freeze: they produce no model output. The tests check
  refusal and opening against a scratch ledger and a scratch copy of this file.
- **VOID, nothing read (V1): a pinned input differs.** A study artifact, its question ids or
  count; a model's revision, receipt SHA-256 or snapshot root (checked by the driver after the
  lane's own verification, before any step runs); job 1458's ten pinned files; AM1's committed
  tables (both digests, and every pool present); the abstention patterns; either judge template;
  any code pin; a worker that finds its engine mode other than the pinned one; or the features'
  recorded provenance (population, artifact and id digests, pattern and template digests, and the
  digests of the twelve repository modules the extraction imports, `FEATURE_CODE`). An input is
  fixed, never the code; a code change is a new registration id.
- **VOID (V2): incomplete, and the rerun rule.** A job is complete when each reader has a complete
  pass (OLMo-2 from either of its steps) and the primary judge's pass is complete; otherwise it is
  incomplete. Right after each GPU job ends, before extract reads it, `rerun-decision`
  (`am3g-rerun-decision.sh`) applies these rules, in this order, to the driver's `summary.json`
  and the lane's `termination.env` (`rerun_decision`); the first that applies decides. It
  decides a job once, only after the job ended (its saved `scontrol` record,
  `R/ops/scontrol-JOB.txt`, and the lane's `termination.env` both exist; a repeat is refused),
  and writes the decision through a temporary file, so a failed run leaves none. A
  `summary.json` that is not a JSON object is a named V2 error. A job that ended without the
  lane's termination record, or whose summary is such an error, cannot be decided, and its
  population is VOID (V2, incomplete).
  1. **rerun** when the workload never started (lane reasons `gpu_prolog_unavailable`,
     `foreign_gpu_process`, `hard_stop_before_start`). Without a driver summary: **no-rerun**
     after the lane's hard stop, **rerun** otherwise.
  2. **void** (V1) when the model verification failed or a worker found its engine mode other
     than the pinned one.
  3. **complete** when every essential step completed (an incomplete second judge only drops
     that judge's descriptions); extract reads this job.
  4. **no-rerun**, VOID (V2, time budget), when the lane's hard stop ended the incomplete job,
     whatever else the job records (a signal, a failed step).
  5. For a signal (a lane reason starting `signal_`, or a signal the driver recorded):
     **no-rerun** (the limit's own signal) when the lane's finish time (`finished_at`) is within
     300 s of its hard stop (`hard_stop_at`); **rerun** otherwise (a cancellation or a node
     event), whatever the steps record.
  6. Otherwise, from the steps' records: the first incomplete essential unit, in the order
     Qwen3-8B, OLMo-2, Qwen3.5-9B, judge32, decides, and within that unit (OLMo-2's two steps)
     the first step's record that matches decides: **no-rerun** for a step skipped for lack of
     time, a pass stopped by its `max_s` or the deadline, or a worker killed as late (the budgets
     are part of the design); **rerun** for an engine that failed to start (OLMo-2's
     batch-invariant step excepted, whose declared fallback decides), a failed smoke check, a
     worker that ended without its done record (a crash), or a unit with no complete pass for
     any other reason.
  A rerun is a new job of this registration with the same commit, image, inputs and seeds
  (`am3g-submit.sh ... rerun`), submitted as soon as the decision is made, and only when the
  decision record of the population's submitted job says "rerun" (the script refuses otherwise);
  a held-out rerun runs before the abstention job is submitted. Extract then reads the rerun's
  job, whose own decision is final: for the job named in the population's rerun record, a
  "rerun" becomes **void** (V2, `--is-rerun`), and a second rerun is refused. The incomplete
  job's records are kept and reported. If
  the held-out job ends incomplete for good, H1 and H2 are VOID (there is no complete anchor
  check). If only the abstention job does, H2 is VOID with its named reason and `analyze` runs
  once with `--abstention-void REASON` (section 16); H1 stands. A failed image build is rebuilt
  once from the same capsule (`am3g-build.sh ... rebuild`, into its own build root
  `overlay-build-vllm-FREEZE8-r2`; `am3g-image.sh` reads the latest attempt); a second failure
  stops the run before any GPU job, and nothing is read. The attempts are counted from the job
  ids recorded as each build is submitted (`R/ops/build-attempts-FREEZE8.txt`), not from the
  build roots, so a build that fails before its root exists still counts. A missing second-judge label affects only the second judge's descriptions: a reader and
  arm with any missing second-judge label is reported as incomplete under that judge.
- **Named V2 errors in extract.** A run directory without `judge-items.json` (no judge step ran,
  because judge32 was skipped) is `VOID (V2, incomplete): the judge items (no judge step ran:
  judge32 was skipped) ...`; a missing or unreadable `summary.json` or reader pass is likewise a
  named V2 error.
- **VOID (V3): the anchor replay fails.** On the held-out job, extract compares the anchor's
  replies with job 1458's `reader-gpu0` at every requested cell (R1: identical tokens and finish
  reasons, token for token, at all 49,274 cells; log-prob bits are reported, not gated), and its
  primary-judge labels with AM1's committed tables (R2: equal at all 49,274 cells). If either
  fails, the pipeline is not the one AM1 validated: H1's readings are VOID and H2 is reported as a
  description of a void run, with the differences at the token and label levels. A replay
  failure is not an infrastructure failure, and the registration is not rerun under this id.
  Why the anchor runs on all 347 questions: its pass costs about 0.12 GPU-h, under a quarter of
  the held-out job, and it checks the whole pipeline (the artifact, the prompt rendering, the
  engine, the image and the primary judge) against AM1 token for token before any new reader's
  number is read, and reproduces H-C's counts (39 and 0) exactly. Without it a pipeline error
  would be indistinguishable from a reader effect. Its counts are not part of H1's family.
- **G-J1, a replay of AM1's validation items.** On the held-out validation items the primary judge
  says yes to at least 95% of reference answers (single-session-preference questions left out)
  and no to at least 95% of "I don't know." (AM1's G2 rule). The items and the batch-invariant
  judge are AM1's, so this checks that the judge replays; it cannot catch an error the judge
  makes on OLMo-2's or Qwen3.5-9B's replies, which is what the blind hand check is for. If G-J1
  fails, H1's readings are JUDGE_DEPENDENT and no decision follows. (AM1's run of the same items
  gave 322 of 322 and 347 of 347.)
- **The blind hand check of H1's discordant cells, with H2's mixed in** (D9: agent labels,
  disclosed as such, not human labels).
  - *What is labelled.* `hand-sample` draws, from the features (`hand_plan`, text-free and
    deterministic, so `analyze` recomputes it and checks its digest against the receipted one,
    `--hand-plan-sha256`):
    - H1 (decides): for OLMo-2 and Qwen3.5-9B on the held-out job, both replies (the rule's
      choice and BM25 top 4's) of every question whose two replies the primary judge labels
      differently on the retrieved arm; and, as distractors, as many concordant questions of
      that reader, drawn with `random.Random(f"44:hand:{reader}")`, first from those where the
      rule left BM25 top 4 (they look like discordant pairs) and then from the others, each
      giving BM25 top 4's reply and the rule's (or, where the rule kept top 4, a seeded other
      4-subset's reply that differs). A reader with fewer such switched questions than
      discordant ones gets the rest from the others, and one with fewer concordant questions than
      discordant ones gets fewer distractors; the plan records both shortfalls per reader
      (`switched_shortfall`, `distractor_questions`). Items carry the check "answer".
    - H2 (descriptive): the same for all three readers on the abstention job (seed
      `44:hand:abstention:{reader}`), discordance under the abstention template, items with the
      check "abstention". When H2 is void, no abstention item is drawn.
    Items are deduplicated by (question, SHA-256 of the normalized reply) and put in one seeded
    order across both populations and every reader (`random.Random("44:hand:order")`), so H1 and
    H2 items are labelled in the same run and look alike.
  - *Blindness and files.* `hand-sample` writes to `R/hand/`, a directory of its own: the sample
    (per item only its id, the question id and type, the check, the question, the reference text
    and the reply: no reader, judge label, role, mask or rule identity), the instructions
    (`HAND_INSTRUCTIONS`: LongMemEval's answer-check criteria per question type, "a reply that
    declines to answer is 0" for the check "answer", and for the check "abstention" 1 when the
    reply identifies the question as unanswerable), the chunks of 60 consecutive items
    (`HAND_CHUNK`), one launch prompt per chunk and a text-free manifest. The features and every
    judge label stay in `R/private/`, which no labeller sees.
  - *The labeller.* For each chunk, in order and one at a time, a fresh Claude agent, model
    `claude-opus-5-5`, in a fresh context and a fresh working directory that holds only the chunk
    and the instructions, launched with the pinned prompt (`HAND_LABELLER_PROMPT`, SHA-256
    `98c35ceac9710033b095f01abe4a5fc98f6ed3a597b461e12a98ac213a7ae096`, with the chunk's three
    file names filled in): read the two files, label every line independently, write the labels
    to the named output file, read nothing else and use no other tool.
  - *The stage's claim.* `am3g-hand-label-mac.sh` first claims the stage on the host, atomically
    and once (`mkdir R/hand/claim-STAGE`, with a line in `R/ops/jobs.log`); a stage already
    claimed is refused, from any work directory.
  - *The first launch: the CLI.* `am3g-hand-label-mac.sh ... cli` runs, in each chunk's
    directory, `claude -p --model claude-opus-5-5 --restricted --strict-mcp-config --tools
    Read,Write --permission-mode acceptEdits --no-session-persistence --output-format stream-json
    --verbose`, so the tools are only Read and Write and file access is confined to that
    directory; its stream-json transcript is kept per chunk. A CLI push happens only inside this
    action. In drafting the CLI could not authenticate ("Invalid API key", an environment matter),
    and it is expected to fail the same way at the registered run. It is still launched first, to
    record that failure: when it cannot start a session on the stage's first chunk (the script
    finds neither a tool call nor a result that is not an error), it launches nothing else, keeps
    its output and the time (the receipt records the error's SHA-256 and the time) and exits 3.
    No one enters or creates a credential to make the CLI start.
  - *The expected launch: one subagent per chunk.* After that failure the operator's Claude Code
    session launches, per chunk and in order, one fresh subagent, model `claude-opus-5-5`, whose
    whole prompt is the chunk's pinned prompt naming its files by absolute path
    (`prompt-NN-abs.txt`). Then `am3g-hand-label-mac.sh ... push subagent DIR`, DIR being that
    session's `subagents/` directory, reads the first user message of every `agent-ID.jsonl`
    there, and counts per chunk the transcripts whose message is the chunk's prompt (SHA-256 of
    the stripped text). A chunk with exactly one gets that file, copied unmodified, as its
    transcript; the launch record (`labeller-STAGE.json`, host only) holds the counts, the agent
    ids, the number of files scanned, each chunk's directory and the CLI's failure time. More
    than one transcript for any chunk is an extra labelling attempt: it voids the hand check
    (`hand-merge` writes the final labels empty, so the join is "incomplete" and a directional
    reading is JUDGE_DEPENDENT, section 7.1). None leaves the chunk unlabelled, for the repair
    stage. The dry run's labelling used this launch (section 15).
  - *What the subagent sees.* Its tools are not limited by its launch: the audit below checks
    what it did. Its working directory is the repository (the operator session's), and its
    context carries the session's instruction files (the user's and the project's `CLAUDE.md`
    and the auto-memory index `MEMORY.md`), the git status with recent commit subjects, and the
    skill and agent listings, but no file of the run and no label. The receipt records, per
    chunk, the instruction files' types and names found in the transcript. So that nothing in
    that context carries a result: from the first GPU job's submission until the hand-check
    receipt is committed, the orchestrator writes no commit subject, memory note or file in the
    repository that carries judge-derived counts or readings of this run.
  - *Transcript audit.* `hand-merge` requires the launch record and audits every chunk's
    transcript against it before it reads the chunk's labels (`audit_transcript`). A transcript
    passes only if every line parses; every assistant line names the model `claude-opus-5-5`;
    every tool-call block is a `tool_use` Read of one of the chunk's two input files or Write of
    its output file, by a path in the chunk's own directory (the absolute paths of
    `prompt-NN-abs.txt`, or bare names for the CLI), with no other block that calls a tool
    (`server_tool_use` included); the output was written; the first user message, when the
    transcript holds one (a subagent's always does; the CLI's stream-json does not echo it), is
    the chunk's pinned prompt; and, for a subagent, every line carries the launch record's agent
    id and a timestamp after the CLI's recorded failure. The rows of a chunk whose transcript
    fails, or is missing, are dropped, so its items go to the repair stage.
  - *One labelling run and one repair.* The first stage labels every chunk once. `hand-merge`
    keeps the rows that parse, name an item of the stage once and carry a label of 0 or 1; the
    items without such a row form the one repair stage, with its own claim, chunks and prompts,
    labelled the same way. After it the labels are final, complete or not; there is no third
    stage and no other relabelling: no item is labelled again by choice and no label is edited.
    A correction found after the join (an operator who disagrees with a label, say) is reported
    separately, beside the registered result, and changes nothing in it. `hand-sample` and
    `hand-merge` each run once (a repeat is refused and leaves the first record), and write their
    records through a temporary file.
  - *Receipts before the join.* Each stage is receipted (`am3g-hand-receipt.sh`), text-free. The
    receipt refuses a stage without a launch record, a subagent launch without the CLI's recorded
    failure, and a transcript whose SHA-256 on the Mac differs from the audit's. It records the
    labeller's model and launch, the CLI's error digest and failure time, the labelling attempts
    per chunk and the matching transcripts in all, the agent ids, models, first-prompt digests
    and times the audit found, the context's instruction files, the prompt's SHA-256, the
    instructions', sample's and plan's digests, every chunk's digest, every transcript's digest
    with its audit, a void, the stage's raw labels' digest and, after the last stage, the final
    labels' digest. With the sample's and the merge's records and the manifest it goes to
    `R/hand-check/`, which is committed, before `analyze` joins the labels, as the run's evidence
    directory's `hand-check/`
    (`program/evidence/RUNDATE/am3-nonabstain-generality-v1/hand-check/`, RUNDATE being the
    held-out job's date); `am3g-stage-evidence.sh` later copies the same files to the same path,
    so the staging shows no difference there. The commit's id is passed to `am3g-analyze.sh` as
    RECEIPT_COMMIT and logged at the head of its log. `analyze` refuses labels or a plan with
    another digest, and the hand check is "incomplete" unless the labels cover exactly the
    recomputed plan's items, each once, with 0 or 1. The verifier checks that `results.json`'s
    hand-check labels and plan digests equal the committed receipt's, and that the receipt
    commit precedes the analysis log.
  - *Size and time.* No cap on items. About four items per discordant question (its two replies
    and a distractor's two). At the development rates of discordance (4 and 3 of 63) H1 draws
    about 22 and 17 discordant questions, about 90 and 70 items; at the anchor's held-out rate
    (39 of 347) about 155 per reader. H2 adds at most 60 items per reader and probably under 40 in
    all (the development proxy's rates, section 9). Expected: about 200-400 items, 4-7 chunks.
    The maximum, every question discordant, is 2 x 694 + 3 x 60 = 1,568 items (27 chunks). The
    dry run's chunk of 27 items took 18 s to label; a chunk of 60 should take about a minute, so
    the first stage is expected to take under 10 minutes and at most about 30.
  - *Decision.* H1: section 7.1. H2's hand labels are descriptive: b2_hand and c2_hand per reader
    with Holm across the three, reported beside H2's judge-based figures; they change no H2
    figure. Hand-against-judge agreement (counts and Cohen's kappa), overall and per population,
    is reported as a description.
- **G-J2, the abstention judge.** On the abstention validation items the primary judge says yes
  to "I don't know." on at least 95% of questions (29 of 30) and no to the decoy on at least 95%.
  If it fails, H2 is reported as JUDGE_QUALIFIED: its cost rests on a judge that failed its own
  validation. The explanation item's yes rate is reported. VOID (V3) takes precedence over
  JUDGE_QUALIFIED.
- **Kill.** None beyond the void rules. A void is reported with its check and counts.

## 9. Operating characteristics

Computed by `scripts/memcredit_am3g.py power` on the host CPU from AM3's committed `results.json`,
`am1-keepset-search-v1`'s committed `results.json` and AM3's host-only development features
(`67780c98...`, text-free), in the development dry run
(`program/evidence/2026-10-16/am3-nonabstain-generality-dev-dryrun/power.json`).

**H1.** The exact power of the exact McNemar test over 347 questions, when each question is
discordant with probability r and a discordant pair favours the rule with probability s
(`memcredit_keepset_search.mcnemar_power`). Holm rejects a reader at least when p <= 0.025 and at
most when p <= 0.05, so the two values bound its power.

| Scenario | OLMo-2: r, power | Qwen3.5-9B: r, power |
|---|---|---|
| AM3's development rate (4 of 63; 3 of 63), s = 1 | 0.063, 1.00 | 0.048, 0.998-0.999 |
| half of it, s = 1 | 0.032, 0.93-0.96 | 0.024, 0.72-0.83 |
| a quarter of it, s = 1 | 0.016, 0.31-0.47 | 0.012, 0.12-0.23 |
| development rate, s = 0.9 | 0.063, 0.96-0.98 | 0.048, 0.87-0.92 |
| the anchor's held-out rate (39 of 347), s = 1 | 0.112, 1.00 | 0.112, 1.00 |

Readings: if the new readers' held-out discordance resembles their development rate, H1 rejects
for both with probability near 1, and at half that rate with about 0.9 (OLMo-2) and 0.7-0.8
(Qwen3.5-9B). Development understated the anchor's held-out rate about sevenfold (1 of 63
against 39 of 347), so these may be conservative; but 4 and 3 development discordant pairs are
small numbers.

**H1 with the hand check (the combined rule of section 7.1).** A directional reading stands only
if the judge-based test and the hand-label test both reject. With c = c_hand = 0, if the hand
labels confirm each judge-counted gain independently with probability a, b_hand ~ Binomial(b, a),
and the power is P(b_hand >= k), with k = 7 at Holm's first step (alpha 0.025) and 6 at its second
(alpha 0.05), which bound it (`combined_power`; `power.json`, `with_the_hand_check`):

| Scenario (s = 1) | reader | a = 1 | a = 0.9 | a = 0.8 |
|---|---|---|---|---|
| development rate | OLMo-2 | 1.00 | 1.00 | 0.999-1.00 |
| | Qwen3.5-9B | 0.998-0.999 | 0.993-0.997 | 0.979-0.992 |
| half of it | OLMo-2 | 0.93-0.96 | 0.87-0.93 | 0.78-0.88 |
| | Qwen3.5-9B | 0.72-0.83 | 0.62-0.75 | 0.49-0.65 |
| a quarter of it | OLMo-2 | 0.31-0.47 | 0.23-0.38 | 0.16-0.28 |
| | Qwen3.5-9B | 0.12-0.23 | 0.08-0.17 | 0.05-0.12 |
| the anchor's held-out rate (39 of 347) | both | 1.00 | 1.00 | 1.00 |

a = 1 is the judge-only power above. In the dry run the hand labels confirmed all 7 of the
judge's development gains (a = 1 on 7; section 15). If 1 in 5 of the judge's gains were wrong,
the hand check would cost OLMo-2 0.09-0.15 of power at half the development rate, and
Qwen3.5-9B 0.19-0.23.

**H2 (a description; the test's power is reported so that its labels are read correctly).** With
N = 30 and c2 = 0, Holm's strictest step needs b2 >= 7 and alpha 0.05 needs b2 >= 6.

| Cost rate q (b2 ~ Binomial(30, q)) | 0.05 | 0.10 | 0.15 | 0.20 | 0.25 | 0.30 | 0.35 | 0.40 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| P(b2 >= 7), Holm's strictest step | 0.001 | 0.03 | 0.15 | 0.39 | 0.65 | 0.84 | 0.94 | 0.98 |
| P(b2 >= 6), alpha 0.05 | 0.003 | 0.07 | 0.29 | 0.57 | 0.80 | 0.92 | 0.98 | 0.99 |

Development proxy (`gold_free_proxy`): in each development pool, the 4-subsets that hold no gold
memory stand in for an unanswerable question's subsets. On the retrieved arm, the BM25-best
gold-free 4-subset abstains in 44 (Qwen3-8B), 42 (OLMo-2) and 46 (Qwen3.5-9B) of 63 pools, and
another gold-free 4-subset then answers in 3, 11 and 4 (rates 0.048, 0.175, 0.063); 74-82% of
gold-free 4-subset replies abstain. The anchor's held-out switching rate on answerable questions
is 71 of 347 (0.205). The proxy describes missing information, not LongMemEval's edited
questions, which ask about something near what the history holds, so the real rates may be
higher.

## 10. Seeds

Declared `[42, 43, 44]`. 42: every engine's seed, the bootstrap of every interval. 44: the
abstention decoy draw (and, through AM1's unchanged validation items, the held-out derangement).
43 is unused; the lane's seed-matrix contract binds three seeds. No unseeded randomness: the
rule, the tests and the exact intervals involve no random draw.

## 11. Compute plan and caps

- **Steps.** One image build, then two GPU jobs on one H100 each, from the freeze commit, in the
  image built from its source capsule, through the docker-research lane
  (`scripts/submit_docker_research_job.py`): the container runs read-only with `--cap-drop ALL`,
  `no-new-privileges`, the user's uid:gid, a tmpfs `/tmp`, no network and only the GPU Slurm
  allocated (`--gpus device=` that GPU), stock vLLM only. Steps per job, in order: `rd-qwen3-8b`,
  `rd-olmo2` (`rd-olmo2-default` only if it does not complete), `rd-qwen35-9b-default`,
  `judge32`, `judge8`.
- **Estimate**, from AM3's job 1466 (0.18 GPU-h for three readers x 8,946 requests and both
  judges on 2,743 items: reader passes of 70, 73 and 122 s, engine starts of 27-41 s, judges 19
  and 4 s):
  - held-out job: 49,274 requests per reader (5.5 times AM3's), about 390, 400 and 670 s of
    passes, judges on about 15,000 items about 110 and 25 s, plus starts and checks: about 32
    minutes, 0.53 GPU-h;
  - abstention job: 2,130 requests per reader, judges on about 700 items: about 7 minutes,
    0.11 GPU-h;
  - build: about 1 minute, 0.02 GPU-h;
  - expected about 0.66 physical GPU-h in all.
- **Caps.** Slurm limits: build 5 minutes, held-out job 90 minutes (1.5 GPU-h), abstention job
  30 minutes (0.5 GPU-h): **2.08 GPU-h**; with the one rerun per job that section 8 allows, 4.08
  GPU-h. Well under D24's 8 GPU-h line.
- **Step budgets** (`jobs` in the config: per step [`min_start_s`, `max_s`]). A step starts only
  with `min_start_s` left before the job's deadline (the limit minus the lane's 210 s), and its
  passes stop at `max_s`. They are sized with an overhead model measured in job 1471
  (`budget.overhead_model`): per job 100 s (the lane's prolog, 46 s, and the driver's model
  verification, 36 s); per step, outside its pass, the prompt rendering before the engine
  (11-12 s for a development reader, 7 s for a judge, scaled with the requests, plus, for judge32,
  the driver building the judge items from three passes), the engine start (28-41 s), the smoke
  pass (1-6 s) and the hand-off (3-4 s). With margin: held-out readers 135 s, judge32 155 s,
  judge8 90 s, a batch-invariant step whose engine refuses to start 125 s; abstention readers
  70 s, judge32 80 s, judge8 65 s, a refused engine 70 s.
  - Held-out: readers [1150, 1000] (the expected passes are about 390-400 s), Qwen3.5-9B
    [1650, 1500] (about 670 s), judge32 [700, 500] (about 110 s), judge8 [350, 250] (about 25 s).
    With every reader at its cap, judge32 starts with 1,185 s left (it needs 700) and judge8 with
    530 s (it needs 350), and the job ends by 5,000 s of its 5,190; on the fallback path (OLMo-2's
    batch-invariant engine refuses to start and the default-mode step runs) 1,060 s and 405 s,
    ending by 5,125 s. (Check 1 found the first draft's budgets could starve judge32 on the
    fallback path; these replace them.)
  - Abstention: readers [280, 200], Qwen3.5-9B [330, 250], judge32 [240, 150], judge8 [170, 100]
    (every pass is expected under 30 s); worst case ends by 1,355 s of 1,590, and 1,425 s on the
    fallback path.
  - Every step's `min_start_s` covers its own overhead plus its `max_s`, and a test simulates both
    paths for both registered jobs (`test_judges_start_and_fit_in_the_worst_case`).
  - **The residual path.** If OLMo-2's batch-invariant pass is itself stopped by its `max_s`
    (2.5 times its expected length) and its default-mode fallback then runs too, the held-out job
    cannot reach judge32: `judge-items.json` is never written, extract stops with its named V2
    error, and the rule of section 8 makes it a time-budget void with no rerun. A test records
    this path (`test_the_residual_path_is_the_one_section_11_discloses`). In every path judge8
    starts only if judge32 completed with time left; if judge8 is skipped, only the second
    judge's descriptions are lost.
  - **A hung engine start.** A step's `max_s` bounds its passes, not its engine start. An engine
    start that hangs is stopped only near the job's end: usually by the lane's USR1, 180 s
    before the limit, which the driver passes on, its watchdog then killing the worker as
    "signal" (the lane's finish then falls within 300 s of its hard stop); otherwise when the
    worker overruns the job's deadline (the limit minus the lane's 210 s) by 90 s, killed as
    late. Either way no later step can start, and the rule of section 8 makes the job a
    time-budget void with no rerun. The registration accepts this risk rather than change the
    GPU job's code after the dry run: every engine start of these models in AM3's job 1466 and
    the dry run's job 1471 took 27-41 s.
  - **A cold page cache.** The overhead model was measured in job 1471, whose engines may have
    read weights that earlier jobs had left in the node's page cache. A cold start reads up to
    about 65 GB (Qwen3-32B) from disk and can take tens of seconds longer per engine. On the
    fallback path with every reader at its cap, judge8 starts with 405 s against its 350, 55 s of
    slack, so slow starts there could skip judge8, which loses only the second judge's
    descriptions. judge32 keeps 360 s of slack on that path (485 s on the normal one, where judge8
    keeps 180 s).
  - The development job ran (job 1471) under its own, smaller budgets, which the overhead model
    does not cover in its worst case; it took 10:18 of its 25 minutes.
- **Order.** Build (rebuilt once if it fails); the post-build CPU selftests of both populations
  (no GRES); the held-out job, its rerun decision and its one rerun if the rule says so; then the
  abstention job, submitted after the held-out job's final attempt ends whatever its outcome, and
  its rerun decision; then, on the host CPU, extract and the blind hand-check sample; the
  labelling on the operator's Mac, each stage merged and receipted on the host (section 8: the
  first stage, then the one repair stage if items lack a label); the receipts committed; then
  analyze and the tests on the host. Each GPU job is submitted only when no other GPU job of this
  program is queued or running (`am3g-preflight.sh`). Under D110 another project's
  jobs (`transcreate-*`) hold GPUs 0-1; they are never touched, and Slurm allocates this
  program's GPU.

## 12. Data handling

The reply texts, the judge items, the study artifacts (pool texts, questions, explanations,
decoys) and the features stay on the host, under `~/cotcodec-runs/stage0/am3-nonabstain-generality-v1/`
(AM1's held-out artifact stays where AM1 left it).
`extract` writes the features (per mask: labels, abstention flag and pattern, finish reason,
token count, SHA-256 of the normalized reply; no text) to a host-only directory and refuses one
inside the repository. The repository gets `results.json`, `per-table.json.gz` (ids, types,
masks, outcomes, reads; no text) and `tables.md` from `analyze`, the text-free logs and lane
records, and a judge-item list with each response replaced by its SHA-256. The staging script
searches every staged file for every reply of 12 or more characters and every question,
explanation, decoy and memory text of the two artifacts, and exits with an error on a hit; a
staged tree with a hit is not committed. The blind hand check's files (the sample, the chunks
and their prompts, the labels, whose notes may quote the texts, and the labellers' transcripts)
stay on the host in `R/hand/`, made read-only after each step. The operator's Mac holds copies
during the labelling: a stage's chunks, prompts, outputs and transcripts in the work directory W
outside the repository, and the subagents' own transcripts in the operator session's
`subagents/` directory (under `~/.claude/projects/`). Both are deleted from the Mac once the
run's evidence is staged and committed; the host's copies remain the record. The repository
gets the text-free receipts (digests, counts, the transcript audits, the launch record's counts
and ids), committed before the join, and the counts and digests that `hand-sample` and
`hand-merge` print.

## 13. Exclusions and infrastructure failures

No question is excluded for its outcome. The 347 are AM1's confirmatory set (Step 0's eight demo
questions were excluded there before any run); the 30 are every abstention question of
LongMemEval-S. A request that does not finish leaves its pool incomplete, which is the V2 rule
(section 8). A smoke-check failure (16 requests at the start of every pass) stops that step
before data. An engine that fails to start ends its step; OLMo-2's batch-invariant step is then
followed by its declared default-mode fallback.

## 14. Reported regardless of outcome

- H1 per reader: b, c, both accuracies, the difference with both intervals, the exact p, the
  Holm-adjusted p and the reading (or VOID or JUDGE_DEPENDENT with the named check);
- H2 per reader: b2, c2, the cost rate with its exact interval, both accuracies with theirs, the
  net loss, BM25 top 4's correct abstentions and b2 per such abstention with its interval, the
  near-miss strata, the exact p, the Holm-adjusted p and the description label, and G-J2;
- the blind hand check: the plan's counts, shortfalls and digest, the labels' digest, the
  receipts (labeller model and launch, prompt digest, transcript audits, the repair stage's size),
  per H1 reader b_hand, c_hand, the exact p, the Holm-adjusted p and the hand-based label, the
  reading before and after it, H2's b2_hand and c2_hand per reader, hand-against-judge agreement
  with kappa per population, and any correction found after the join, separately;
- the anchor's replay (R1, R2, with log-prob bits and the judges' item-level replay) and its
  held-out counts on both arms;
- every rerun decision with its reason;
- every descriptive output of section 6.4, including the natural-mix net effect and the
  break-even share per reader and judge;
- every validity check of section 8 with its counts; GPU-h; every deviation; the disclosures of
  section 1, including that the run carries no gauntlet score.

## 15. What development fixed in this design: the development dry run

Before the freeze the whole pipeline ran on the development split only, from commit `eae156cf`
(the GPU job's steps, `run`, `worker` and what they call, are unchanged since, apart from the
checks in front of them that apply to the held-out and abstention populations only; the CPU
steps were rerun after each round of checks, below), in a new host directory
(`~/cotcodec-runs/stage0/am3g-dev-dryrun/`), with the operator scripts of section 16 in their
`dev` mode. Record: `program/evidence/2026-10-16/am3-nonabstain-generality-dev-dryrun/README.md`.

- **Build** (job 1467, 1 H100, 00:01:05, 0.0181 GPU-h): image
  `sha256:a8571a4150585cbb31432a2f3b1e88d53315315df8500f6904d50bed14394584` from capsule
  `9cd8e794...`, provenance PASS.
- **Post-build CPU selftests** (no GRES): development (job 1468) and abstention (job 1469). Every
  prompt fits: development at most 1,169 (Qwen3-8B), 1,099 (OLMo-2) and 1,190 (Qwen3.5-9B) tokens,
  as in AM3; abstention 1,027, 972 and 1,040; judge items at most 302 and 272. vLLM 0.31.0
  resolves the three architectures (OLMo-2 through its Transformers backend).
- **GPU job** (job 1471, 1 H100, 00:10:18, 0.1717 GPU-h; limit 25 minutes): every step complete
  (OLMo-2's fallback not needed); reader passes 70.1, 73.2 and 122.1 s after engine starts of
  28-41 s; the judges 20.7 and 4.7 s on 2,869 items (2,555 replies, 188 validation and 126
  calibration items).
- **Host CPU**: extract, analyze twice (byte-identical), `dryrun-compare`, `power` and the tests
  (81 passed).
- **The gate inside the image** (ad hoc CPU jobs 1472 and 1473, no GRES): the GPU job's gate
  checks every section 16 pin inside the image, and the first check found one pinned file
  absent there, the archived prompt port under `legacy/`, which `.dockerignore` keeps out of
  every image. The registered gate would have refused the GPU job after the freeze. The port is
  no longer a code pin (section 4 records its digest; the test that compares it runs on the host),
  a test now checks that no pin sits under a `.dockerignore` entry, and the second check, with
  this draft's table mounted into the dry-run image, found all 39 pins present, differing only
  in the two files changed after `eae156cf` (`tests/test_memcredit_am3g.py` and the staging script).
  After round 1 (job 1474), with 50 pins, the only files absent from that image are the six
  operator scripts added since, and the newly pinned lane scripts, Dockerfile and `uv.lock` are
  present and equal.
- **Total 0.1898 GPU-h** of the 0.5 allowed (`program/state.json`, `gpu_hours_ledger`).

**It reproduced AM3 exactly** (`dryrun-compare.json`, 20 of 20 checks):
- every reader's 8,946 replies equal job 1466's in tokens and log-prob bits, for Qwen3-8B,
  OLMo-2 and Qwen3.5-9B;
- both judges' labels equal job 1466's on all 2,743 shared items;
- the 378 per-pool records equal AM3's committed `per-table.json.gz` (the file is byte-identical,
  `0fc5635b...`), and the 12 reader x judge x arm cells equal AM3's committed `results.json`.

**Abstention-template calibration** (development questions only, a generic explanation in the
Explanation slot): Qwen3-32B said yes to "I don't know." on 63 of 63 questions and to the
reference answer on 0 of 63; Qwen3-8B on 63 and 4. The template renders and the primary judge
behaves as G-J2 requires; these are answerable questions, so this is a calibration, not G-J2.

**Tests.** Locally and on the host, `tests/test_memcredit_am3g.py` and `tests/test_memcredit_am3.py`
pass (86 at `fc9ebb4d`; the analysis rerun there gave byte-identical outputs). The whole suite on the host at `eae156cf`: 3,535 passed, 64 skipped and 2 failed in
another experiment's tests (`test_r04_evidence.py`, `test_r04_nuisance.py`), the same two that
`am1-keepset-search-v1`'s selftest found failing on `main`; this branch changes no existing code.

**Round 1 corrections, rerun on the CPU** (from commit `0d030015`). No GPU job was needed: none
of the code the GPU job runs changed (`run`, `worker`, the request and judge-item tables, the
prompts and the config loading are as at `eae156cf`); the registered jobs' step budgets changed,
which the development job does not use.
- `abstention-facts` rebuilt the abstention artifact byte for byte (`f1c241ba...`) and recounted
  the twins with their text overlap (section 1.2).
- `extract` read job 1471 again. The R2 code (`load_pinned_tables`, `labels_vs_tables`) read the
  pilot's committed tables: the anchor's labels equal them on 8,913 of 8,946 cells, AM3's figure
  (the rest is the compiled-against-eager difference).
- The blind hand check was rehearsed on development data. `hand-sample` drew 27 items (OLMo-2: 4
  discordant and 4 distractor questions; Qwen3.5-9B: 3 and 3). An isolated agent labelled them
  blind (7 correct, 20 not), the receipt was written before the join, and `analyze` joined them.
  Hand and judge agree on 27 of 27 (kappa 1.00); b_hand and c_hand are 4 and 0 (OLMo-2) and 3
  and 0 (Qwen3.5-9B), as the judge's; on 63 questions neither separates, so both read
  NO_DETECTED_DIFFERENCE.
- `analyze` twice (byte-identical), `dryrun-compare` (20 of 20 again; `per-table.json.gz` still
  byte-identical to AM3's), `power` (unchanged) and the memcredit tests (120 passed), at
  `0d030015` and again at `8624a08b`. The whole suite on the host at `8624a08b`: 3,574 passed, 64
  skipped and the same two `test_r04_*` failures.
- Job 1470 is not this registration's: it appears in none of its logs or scripts (its jobs are
  1467-1469 and 1471-1473), it was submitted between 11:09:27 and 11:10:05 UTC, and scontrol no
  longer knew it when check 1 asked (Slurm accounting is disabled). The preflight before job 1471
  found no GPU job of this program queued or running.

**Round 2 corrections, rerun on the CPU** (code at `c2eaa62b`, then `507f4284`, `495090ef` and
`3d4762ba`). No GPU job: the GPU job's steps are as at `eae156cf` (round 2 added only the config
binding in front of them, which does not apply to the development population), and round 2 used
no development GPU time.
- `extract` read job 1471 again at `c2eaa62b` (features `5e2e3366...`, now with the hedge flag);
  the R2 code on the pilot's tables gave 8,913 of 8,946 again.
- **The runbook rehearsal** (`rehearsal/am3g-rehearse.sh` and its logs in the dry-run record):
  section 16's host scripts under a fake HOME on the host, with `sbatch`, `scontrol`, `squeue` and
  `nvidia-smi` stubbed; no job submitted, no GPU and no model used. Its first run, at
  `c2eaa62b`, found that `am3g-preflight.sh` printed its report on stdout, so `am3g-build.sh` and
  `am3g-submit.sh` printed more than the job id they submit (check 2's first finding, in another
  script); the preflight now reports on stderr. At `3d4762ba` all 40 cases pass:
  - the bootstrap checkout, and a bootstrap copy that differs from the commit's refused;
  - the image capture: one line matching `^sha256:[0-9a-f]{64}$`; the record checks pass on the
    real build record of job 1467 and refuse another base image, another vLLM commit and a
    malformed `image-id.txt`;
  - build, the one rebuild into `-r2`, a second build and a third attempt refused, the image read
    from the latest attempt;
  - the job state: the whole `scontrol` record saved when a job ends and printed again after
    scontrol forgets it; exit 1 while a job runs;
  - selftest and submit refusing a malformed image id;
  - submit stopping, with no submit record, on a failed dry run, a failed test-only check, a GPU
    job of this program in the queue (D110's `transcreate-*` ignored), a failed sbatch and a
    submitter output without a job id; then submitting once, printing only the job id, and
    refusing a second submit;
  - rerun refused without the rule's record, allowed once after it, the rerun's own "rerun" void
    (V2), and a second rerun refused;
  - the rule's order on fake job records: a hard stop on an incomplete job with a failed step and
    a signal, no-rerun; a signal an hour before the limit with a step killed late, rerun; a
    signal 120 s before the hard stop, no-rerun; a pass stopped by its budget, no-rerun; complete
    through OLMo-2's fallback; a job that never started, rerun.
- **The blind hand check, rerun with the registered protocol** at `3d4762ba`: 27 items in one
  chunk, plan `85497ef8...`, sample `9597c6ca...` (as at `c2eaa62b`). The CLI launch could not
  authenticate ("Invalid API key"; the error's digest is in the receipt), so the fallback ran:
  one subagent, model claude-opus-5-5, with the pinned prompt; its transcript holds three tool
  calls (Read of the two files, Write of the output) and passed the audit; 27 valid rows, so no
  repair stage. The receipt was committed at `ea449d9d` before the join. 7 replies labelled
  correct and 20 not; agreement with the judge 27 of 27 (kappa 1.00); b_hand and c_hand 4 and 0
  (OLMo-2) and 3 and 0 (Qwen3.5-9B), so both read NO_DETECTED_DIFFERENCE on 63 questions. The
  labels equal those of the `c2eaa62b` rehearsal on all 27 items (the notes differ). An earlier
  attempt at `495090ef` showed that the CLI reports an authentication failure as an assistant
  text and an error result, which the launch script then took for a started session: it pushed a
  stage without labels. That attempt is kept on the host (`hand-495090ef`, with the unlabelled
  sample drawn at `507f4284`), and the script now reads the result record.
- `analyze` twice at `3d4762ba` (byte-identical; it joins the receipted labels and binds the
  plan's digest), `dryrun-compare` (20 of 20; `per-table.json.gz` byte-identical to AM3's),
  `power` (with the combined rule, section 9) and the memcredit tests (130 passed). The whole
  suite on the host at `3d4762ba`: 3,584 passed, 64 skipped and the same two `test_r04_*`
  failures.

**Round 3 corrections, rerun on the CPU** (code at `acd58d73`; no GPU, no model). The runbook
rehearsal, extended with ssh, scp and claude stubs so that the Mac's labelling script runs
against the fake HOME, passed all 56 cases: the 40 above (the build cases now with a build that
fails before its root exists, which no longer blocks the rebuild), and the stage's claim (a
second claim refused from another work directory), a CLI push outside the `cli` action refused,
the subagent push finding the one transcript among the session's files and copying it
unmodified, the audit of model, prompt, agent id, paths and times passing, a repeated hand-sample
and hand-merge refused with their records unchanged, the transcripts' digest list made
read-only, the receipt with its records, an extra transcript for a chunk voiding the hand check
(empty final labels, no repair stage, the void receipted), a rerun decision refused before the
job ended and refused when repeated, a summary that is not a JSON object refused with a named V2
error, and a state that is not terminal counted as running. The new audit, applied to the real
transcript of the `3d4762ba` development labeller, passes (one agent id, every assistant line
`claude-opus-5-5`, the absolute-path prompt first, three tool calls in the chunk's directory,
every line after the CLI's failure; the instruction files `CLAUDE.md` (user and project) and
`MEMORY.md`). The memcredit tests: 132 passed, locally and on the host.

Development also set: the readers and engines (AM3), the 71 requests per pool, H2's status as a
description (section 7.2), the abstention-judge validation items, and the step budgets (from the
timings above, which match AM3's job 1466).

## 16. Code of record (at the draft revision; re-pinned at the freeze)

The fill commit re-pins every row; a row that changes is reviewed before the freeze. The gate
parses this table and refuses to run unless every file matches.

| File | Role | SHA-256 |
|---|---|---|
| `scripts/memcredit_am3g.py` | this registration: gate and config binding, abstention pools, driver and workers, extract, analyze, the rerun rule, the blind hand check (plan, sample, chunks, transcript audit, merge, join), dry-run comparison, power | `4bb0d42c09f9fca6e728a2487966bc13c08715672dce33316db195f6e7573e26` |
| `tests/test_memcredit_am3g.py` | its tests: config and pins, the gate and the config binding, the pins inside the image, the abstention template against the archived port, pools, requests, judge items, the anchor replay checks R1 and R2, Holm and H1's readings, H2's estimand and strata, the natural mix, the hand check (blindness, plan, merge, repair, transcript audit, join), the rerun rule's order, the combined power, end to end on toy runs | `e4f5f152e5dc6e89bdaa0eed94dfbb21f02dde36001b32813d2fd638e928032e` |
| `experiments/am3/am3-nonabstain-generality-v1.yaml` | this registration's config | `96fcd2186c43d6bdad7b1eb90e843aed39f0d56bad349799f8f1db6efb67d60e` |
| `scripts/memcredit_am3.py` | AM3's engine helpers, rule, per-pool record and cell summary (imported) | `25f634edd29a23f2fdee12b0825013d624aa5305d49cf512f74fdf1827ea130f` |
| `tests/test_memcredit_am3.py` | AM3's tests (also supply a pass writer to these tests) | `1ab5196ca553f8cc92deda0a728ec98987853ec81d3f75041561661659d848b3` |
| `experiments/am3/am3-reader-replication-v1.yaml` | AM3's config (the reader blocks) | `525ebf29e80941ef02e646e04c66fdaa40aba67f6bb0dbb9d5926c68befa07c4` |
| `scripts/memcredit_keepset_search.py` | McNemar, paired readings, reads, ledger and pin parsing | `3fbb804328bd310a6c8626f408d0d1b44a4624f06829a0762e3afc6134add584` |
| `scripts/memcredit_cost_curve.py` | table decoding | `431f4cb21ccd398e1433e29a5b40c1a697d48b9aecc5fc728956f819e28c9bab` |
| `scripts/memcredit_label_free.py` | AM1d's abstention patterns, BM25 order | `721015de434021a72ab3bbbab5e91d0de39a2fc359df7283068f83026dcb9d8f` |
| `scripts/memcredit_step0.py` | request streaming, pass files, GPU sampler | `57f2e4bbbd11bf750ff224852ba5dd19923ecb3decfde74d23a6913a7f9a7227` |
| `scripts/memcredit_study.py` | pass reader (`load_pass`) | `f27ecd21e769655cddc1e9b06ee8f4c7c4ee8494348b4fc73dba7c68fdb66bb3` |
| `scripts/memcredit_analyze.py` | imported by `scripts/memcredit_keepset_search.py` | `5444104d3c760b17f311656f4e0dbd50b2b154c89d806f1e4aa2ab6791fb0f34` |
| `harness/__init__.py` | the harness package | `17dac2704be26050e324aa36aba6d2c855abbd592e4d72f750b9b6e9c4399fec` |
| `harness/g2_pilot.py` | lane helpers (deadline, marker, model verification) | `8c685425522377de9fbab92fac02aea321bb2b3bd69d82d2118c4ecea49f6599` |
| `harness/memcredit.py` | BM25, pools, prompts, Clopper-Pearson, answer normalization | `ad0964d0caab382b5541b64d56a30105bc306d2286f6e62137b1eff9121dd607` |
| `harness/memcredit_study.py` | configs, split, request messages, answer-check templates, validation items, bootstrap | `14a97d826ba619e23ea9686e2d2d57149d9f0119df3f80240843178953cf301b` |
| `experiments/am1/memcredit-study-v1.yaml` | the pilot's config (prompt, pools, judges) | `ecdb5c11ff4eaf757ec6712c6f2c75d61c79882bb3d418202b7143abf90793db` |
| `experiments/am1/am1-memory-credit-v1.yaml` | AM1's registration config (confirmatory set, demo exclusions) | `8466d6d42ace1477bb9b2377de8ed67027502ff11b179a369eed352fda212069` |
| `experiments/am1/memcredit-split-v1.json` | the split (decoy pool) | `4fa1b774d4131080855d668ac8f00f5cb07d49cf741f2051d5f8d96577edb3e3` |
| `models/registry.yaml` | the readers' registry entries | `4a084c2f2a4d7f9c1cbdcc6ce3032f558ed3d3a8399428159627512f46a99a03` |
| `scripts/fetch_open_model.py` | snapshot verification | `d995b59ece3c809edd70d6c60a78628ae5cb1ccc0ce8350cc455084d3787d29f` |
| `scripts/submit_docker_research_job.py` | the lane's submitter | `660271655aa22ebd387a023e25d21e6a809c22699ec6314d9d535be74e17a994` |
| `infra/slurm/host-single-node/docker-research.sbatch` | the lane | `2a10c9c72c22ab6dd5135061ff1b9b50977a468687180353d8cd7273acbaf1ec` |
| `scripts/build_vllm_overlay_on_h100.sh` | the overlay build | `aa43283e757695384e0548d060a18b98f07a3af06f583efdb2d709f677e1a96d` |
| `scripts/create_source_archive.py` | the source capsule | `672670ca29d3254e9af90b810eef591e15dae6934612c5184a72e5d0c7e9948c` |
| `scripts/extract_discovery_source_archive.py` | the capsule extractor | `9b4d21a83beac8913dc06a946cf43ea31d77326e65d04957fad66d7b97d8c3cb` |
| `scripts/preregister.py` | the ledger | `21fc3ef0ed0958b1600ce742c3b4f8d557d0a298635acb20342710eb814b2c0d` |
| `ops/am3g/am3g-env.sh` | operator: shared host paths | `021996f3e681b35cfb00fc21a121b8c4e9d441abe80ef586f483879b02e29ea3` |
| `ops/am3g/am3g-checkout.sh` | operator: clean clone from a bundle | `fef6cba73c929da5f4af7147ff7edc1fb27c2f5afc4cbf6731b5da24a0df27dd` |
| `ops/am3g/am3g-prepare-abstention.sh` | operator: the abstention artifact (before the freeze) | `bc93c751efcec2f25a35bc046beea3f212757c09ed8dc5c17a849a483d895425` |
| `ops/am3g/am3g-capsule.sh` | operator: source capsule | `73b19889a335c204e754f3565c30ca51c239297b63c4ef9d3cf282a1f5caa579` |
| `ops/am3g/am3g-preflight.sh` | operator: queue and GPU check (reports on stderr) | `6c1ac55cccca8d8e8478ec8403bd3123f61c397e3b04e5ba488e63e3faa35035` |
| `ops/am3g/am3g-build.sh` | operator: image build, and the one rebuild | `82ce5dc7dfe9be584d43172520056c62eac7dec0690b151767fa1674431df86c` |
| `ops/am3g/am3g-selftest-cpu.sbatch` | operator: CPU selftest in the image | `7fbbe82d36e6c86efb3c4cba19ef799783fa3033fa0f97f803e6b40edd2e7919` |
| `ops/am3g/am3g-selftest.sh` | operator: submits the CPU selftest | `5b7eae57d1d031850760ee2dee31c5bbadb91e34064c0afc0458c2d905f77309` |
| `ops/am3g/am3g-submit.sh` | operator: lane manifest, dry run, test-only check, submit, the rerun the rule allows | `269a739644b986d8e2c3776a537d22751cf5b5e2b0c91ac81bfda089733de04e` |
| `ops/am3g/am3g-extract.sh` | operator: extract | `ef96744ab8f7b254bdbb95dc18d5b1ee776ff111dc23c8de73f60afcd5fe05ea` |
| `ops/am3g/am3g-analyze.sh` | operator: analyze twice, tests | `9602b90ae1675f6f71473c77bd32b6a3b0d8447a1dddb10ebdd3c62e790aa2ad` |
| `ops/am3g/am3g-stage-evidence.sh` | operator: text-free staging and the text search | `fcc8a46f64fb83d03fe2f33d94fe8877c969fa2741121d16ec2f7cef46bd6164` |
| `ops/am3g/am3g-mac-bundle.sh` | operator, on the Mac: the bundle and the bootstrap copies | `15524e2fc8f467328505314e0a4d8e3c5edf4c09d481d72d2cbfc52b99199721` |
| `ops/am3g/am3g-job-state.sh` | operator: a job's state, and its scontrol record when it ends | `f48456a6f628ad98af0a57b8817903130bc78eb473a6afe5da92f158826b4505` |
| `ops/am3g/am3g-image.sh` | operator: the built image id, after its provenance and receipt checks | `5ee1ef539e6fbcff9d9f3a5fee29d103f299fbc50ba3fce1e5eb36526953c1ef` |
| `ops/am3g/am3g-rerun-decision.sh` | operator: the mechanical rerun rule | `8bcc8460b328871ab6ee31d0b27cf1665c541b671e3a6b8a18c5faed9989d7df` |
| `ops/am3g/am3g-hand-sample.sh` | operator: the blind hand-check sample (H1, with H2 mixed in), its chunks and prompts | `7cf1f9a8348cd469dc5eb3a463001a12e0050951c1dafd3488c8827fe57b38b6` |
| `ops/am3g/am3g-hand-receipt.sh` | operator: one stage's text-free receipt, committed before the join | `5014b7101b8b70d999788cac7d075817a21c618fc7ee34f192e73d46617432d1` |
| `ops/am3g/am3g-hand-label-mac.sh` | operator, on the Mac: the registered labelling of one stage, chunk by chunk (prepare, the CLI launch, the recorded subagent fallback, push) | `86b2e32bb1d7d70dbb074dfdb7561b4473da38aaf4f5c4db72346da586c782c9` |
| `ops/am3g/am3g-hand-merge.sh` | operator: audits the transcripts and merges a labelling stage; writes the one repair stage | `890632c9d409c486e3e76dd0f08a588563d471ad7644162d2c122b255968c30a` |
| `scripts/verify_compute_provenance.py` | the lane, inside the container: image provenance | `ca62d62ae5c0e820a08574d5c5b1227c4495a24f3abcf342a1ae3ff1958d54ba` |
| `scripts/check_compute_env.sh` | the lane, inside the container: environment doctor | `76fc5d64f7e84fd1e93340688b6be845d97f01c4791981c31ac8e70d66ff08ff` |
| `scripts/exec_research_workload.py` | the lane, inside the container: runs the workload | `bb3abd1dd11e8ec9336fc181ac1999b1deea00e08e05d0fff3227111eaa6e4c1` |
| `infra/research/Dockerfile.vllm-overlay` | the overlay image's Dockerfile | `437ff4f6d95d564a5065cc4383e79b34f166417358edcee34b82e5d05574852e` |
| `uv.lock` | the Python environment of every host step | `4721104d055ec9d7488f82831c24b7e080124f27e9b850abd51c91024629b60f` |

Commands of the registered run, after the freeze. The names in capitals are values that exist
only then: FREEZE, the freeze commit's full id, and FREEZE8, its first 8 characters (every script
that takes a "commit short id" takes FREEZE8); IMAGE, the image id; JB, JS1, JS2, JOB_H and JOB_A,
the Slurm ids of the build, the two CPU selftests and the two GPU jobs (each submitting script
prints only the id it submits on stdout, and its log lines on stderr); W, a new work directory on
the operator's Mac outside the repository; RECEIPT_COMMIT, the full id of the commit that holds
the hand-label receipts; ABSTENTION_VOID, section 8's reason when the H2 void path applies. The
host root R is `~/cotcodec-runs/stage0/am3-nonabstain-generality-v1/` (the scripts' `reg` mode).
Every script appends a line to `R/ops/jobs.log`. The host scripts that run repository code
(capsule, build, selftest, submit, rerun-decision, extract, hand-sample, hand-merge, analyze)
refuse a dirty checkout or another commit; `am3g-checkout.sh` makes the clean checkout and
refuses to go on otherwise; `am3g-hand-label-mac.sh` refuses a dirty repository on the Mac or
another commit; `am3g-image.sh`, `am3g-job-state.sh`, `am3g-hand-receipt.sh` and
`am3g-preflight.sh` read records only and run no repository code; `am3g-stage-evidence.sh` copies
records and runs its text search with the system Python. No command waits: `am3g-job-state.sh`
prints a job's state once and is polled (exit 1 in any state that is not terminal), and when a
job has ended (COMPLETED, FAILED, CANCELLED, TIMEOUT, OUT_OF_MEMORY, NODE_FAIL, PREEMPTED,
BOOT_FAIL or DEADLINE) it saves the whole `scontrol show job` record to `R/ops/scontrol-J.txt`,
because Slurm accounting is disabled on the node and scontrol forgets ended jobs;
`am3g-rerun-decision.sh` refuses a job without that record.

```bash
# On the operator's Mac, in the repository (the branch that holds FREEZE):
bash ops/am3g/am3g-mac-bundle.sh reg FREEZE       # bundle -> R/bundles; bootstrap copies of
                                                  # am3g-env.sh and am3g-checkout.sh -> R/bootstrap;
                                                  # prints their SHA-256: they must equal section 16
# On the host:
bash ~/cotcodec-runs/stage0/am3-nonabstain-generality-v1/bootstrap/am3g-checkout.sh reg FREEZE
cd ~/cotcodec-runs/stage0/am3-nonabstain-generality-v1/checkout   # every later host command runs
                                                  # here; am3g-checkout.sh refused unless the
                                                  # bootstrap copies equal FREEZE's own
bash ops/am3g/am3g-capsule.sh reg FREEZE8
bash ops/am3g/am3g-build.sh reg FREEZE8 build                   # prints JB (1 H100, 5 minutes)
bash ops/am3g/am3g-job-state.sh reg JB                          # poll until it exits 0
IMAGE=$(bash ops/am3g/am3g-image.sh reg FREEZE8)                # one line, the image id (sha256:
                                                                # and 64 hex digits), after the
                                                                # provenance and receipt checks;
                                                                # on a failed build:
#   bash ops/am3g/am3g-build.sh reg FREEZE8 rebuild (once, into overlay-build-vllm-FREEZE8-r2),
#   poll it, and capture IMAGE again (am3g-image.sh reads the latest attempt); a second failure
#   stops the run
bash ops/am3g/am3g-selftest.sh reg FREEZE8 "$IMAGE" heldout     # prints JS1 (CPU, no GRES)
bash ops/am3g/am3g-selftest.sh reg FREEZE8 "$IMAGE" abstention  # prints JS2 (CPU, no GRES)
bash ops/am3g/am3g-job-state.sh reg JS1; bash ops/am3g/am3g-job-state.sh reg JS2   # poll both
cat R/selftest-heldout-FREEZE8/exits.txt R/selftest-abstention-FREEZE8/exits.txt  # all exit 0
bash ops/am3g/am3g-submit.sh reg FREEZE8 "$IMAGE" heldout check      # dry run and test-only check
bash ops/am3g/am3g-submit.sh reg FREEZE8 "$IMAGE" heldout submit     # prints JOB_H (90 minutes);
                                                                     # a failure before sbatch
                                                                     # records nothing; rerun it
bash ops/am3g/am3g-job-state.sh reg JOB_H                            # poll until it exits 0
bash ops/am3g/am3g-rerun-decision.sh reg FREEZE8 heldout JOB_H       # complete | rerun | no-rerun | void
#   on "rerun" only (am3g-submit.sh refuses without that record):
#   am3g-submit.sh reg FREEZE8 "$IMAGE" heldout rerun, poll it, and run am3g-rerun-decision.sh on
#   the rerun's id, which then replaces JOB_H below (its own "rerun" is void)
bash ops/am3g/am3g-submit.sh reg FREEZE8 "$IMAGE" abstention submit  # prints JOB_A (30 minutes),
                                                                     # after JOB_H's final
                                                                     # attempt ended
bash ops/am3g/am3g-job-state.sh reg JOB_A
bash ops/am3g/am3g-rerun-decision.sh reg FREEZE8 abstention JOB_A    # the same rule
bash ops/am3g/am3g-extract.sh reg FREEZE8 heldout JOB_H
bash ops/am3g/am3g-extract.sh reg FREEZE8 abstention JOB_A
bash ops/am3g/am3g-hand-sample.sh reg FREEZE8 JOB_H JOB_A   # the blind sample, chunks and prompts
                                                            # -> R/hand (JOB_A left out when H2 is
                                                            # void)
# On the Mac, in the repository at FREEZE (clean):
bash ops/am3g/am3g-hand-label-mac.sh reg FREEZE8 first W cli   # claims the stage on the host
#   exit 3 when the CLI cannot start a session (expected): then, per chunk NN in order, one fresh
#   subagent (model claude-opus-5-5) whose whole prompt is W/first/prompt-NN-abs.txt, and:
#   bash ops/am3g/am3g-hand-label-mac.sh reg FREEZE8 first W push subagent \
#     ~/.claude/projects/PROJECT/SESSION/subagents     # the operator session's subagents/
# On the host:
bash ops/am3g/am3g-hand-merge.sh reg FREEZE8 first     # audits the transcripts; the final labels,
                                                       # or the one repair stage's chunks
bash ops/am3g/am3g-hand-receipt.sh reg FREEZE8 first
#   if the merge wrote a repair stage: the same three steps with "repair" in place of "first"
#   (am3g-hand-label-mac.sh, am3g-hand-merge.sh, am3g-hand-receipt.sh); no third stage
#   commit R/hand-check/ as program/evidence/RUNDATE/am3-nonabstain-generality-v1/hand-check/
#   (the receipts before the join; the staging copies the same files there); its id is
#   RECEIPT_COMMIT; nothing judge-derived of this run is written to the repository before it
RECEIPT_COMMIT=... bash ops/am3g/am3g-analyze.sh reg FREEZE8  # analyze twice (byte-identical), tests
bash ops/am3g/am3g-stage-evidence.sh reg FREEZE8 heldout:JOB_H abstention:JOB_A
#   after the evidence commit: delete W and the session's subagents/ transcripts on the Mac
```

`am3g-analyze.sh` runs `scripts/memcredit_am3g.py analyze --heldout-features
private/features-heldout.json.gz --abstention-features private/features-abstention.json.gz
--hand-labels hand/hand-labels.jsonl --hand-labels-sha256 S --hand-plan-sha256 P --output-dir
out-FREEZE8-a` (and `-b`) in the checkout's `uv` environment (`uv run --locked --offline`), S and
P being the receipted digests of the final labels and the plan (`R/hand-check/hand-labels.sha256.txt`,
`hand-plan.sha256.txt`). It refuses to run without the receipted labels or without
RECEIPT_COMMIT (a full commit id), which it logs. Under section 8's H2 void path, the operator
sets ABSTENTION_VOID to the failing command's error line (the line that begins `error: `, without
that prefix, the home directory written as `~`), and the script passes it as `--abstention-void`
and writes to `out-FREEZE8-void-{a,b}` and `analyze-FREEZE8-void.log`, keeping the failing
attempt's records: `analyze` runs once per input set and never overwrites an output directory. A
fresh verifier reruns `analyze` from a new clone at FREEZE, and the outputs must be
byte-identical.
## 17. Freeze checklist

Before the freeze, by the orchestrator:

1. Two independent, sequential pre-freeze checks of this file, the config and the code of
   section 16, by reviewers that did not draft them, and the corrections they require; their
   dispositions go in section 19.
2. The gauntlet question: resolved by D118. No gauntlet wave runs, and the run carries no
   gauntlet score (section 1.5).
3. If any code of section 16 changed after the development dry run, rerun the affected parts of
   it (at least `extract`, `analyze` and `dryrun-compare` on the dry run's run directory, and the
   tests on the host) and update its record. A change to the GPU job's code (`run`, `worker` and
   what they call) needs a new development GPU job within the 0.5 GPU-h dry-run cap.
4. Re-pin section 16 in a fill commit; run the tests locally and on the host.
5. Confirm on the host, at the fill commit, that the inputs of section 4 have their digests (the
   two study artifacts, job 1458's ten files, the dataset file) and that `git diff 957a3c0a --
   program/evidence/2026-10-16/am1-confirmatory program/evidence/2026-10-16/am3-reader-replication`
   is empty.
6. The fill commit rewrites the status line (line 3) to the frozen wording that
   `am1-keepset-search-v1` uses ("**Status: frozen in `program/preregistrations/ledger.jsonl`; see
   the ledger row for the freeze time and `git_head_at_freeze`.**"). The file must then contain no
   to-be-decided marker and no placeholder in angle brackets. The orchestrator makes this edit,
   not the drafter.
7. The ledger row, by `uv run python scripts/preregister.py freeze am3-nonabstain-generality-v1
   program/preregistrations/am3-nonabstain-generality-v1.md`, in a commit that adds only that row
   (the freeze commit). A test freezes this file into a scratch ledger, so the command's text
   checks pass.

After the freeze: run section 16's commands once (the hand-label receipt is committed before
`analyze`), commit the text-free outputs, and have a fresh verifier rerun `analyze` from a new
clone and check that `results.json`'s hand-check labels and plan digests equal the committed
receipt's, and that the receipt commit precedes the analysis log's start line.

## 18. Priors (for the record; not tested)

- **H1:** NONABSTAIN_HELPS for both readers is the likeliest outcome. On development the rule
  never lost under the primary judge for any reader (17 gained, 0 lost without the anchor), and
  the anchor's held-out gain was seven times its development rate. OLMo-2 switches away from an
  abstaining top 4 more often than the Qwen readers (15 of 63 development pools against 7-8),
  which gives it more chances to gain and to lose. Qwen3.5-9B's development gains (3) were the
  fewest; its reading is the less certain.
- **H2:** a nonzero cost for OLMo-2 (its development switch rate on gold-free subsets was 0.175)
  and a small one for the Qwen readers (0.048 and 0.063), possibly larger on LongMemEval's edited
  questions than on the proxy. G-J2 is expected to pass: the abstention template asks whether
  the response identifies the question as unanswerable, which a bare "I don't know." does, and
  the development calibration gave 63 of 63 (section 15).
- **Natural mix:** at LongMemEval-S's 6% unanswerable questions, a reader whose held-out gain
  resembles the anchor's (0.112 per answerable question, 0.94 x 0.1124 = 0.106 at the mix) stays
  ahead whatever its cost on the 30 (at most 0.06 at the mix), so the break-even unanswerable
  share is the more informative figure.

## 19. Review log: the independent checks

Two independent, sequential checks are required before the freeze (D118).

### Round 1

Pre-freeze check 1 ran on `3f989999` and found the file ready to freeze after fixes: no blocking
item, three major, thirteen minor and five for information. It confirmed the blindness of the
draft, every pin, the dataset and artifact digests, the GPU-hour ledger, the docker flags, the
in-image gate fix, the power figures and the text search (against 4,953 texts). The fixes are
commit `0d030015` (code, tests, operator scripts, config) and the commit that carries this
section; the CPU parts of the development dry run were rerun (section 15). No model ran on a
held-out or abstention question.

| Item | Finding | Disposition |
|---|---|---|
| M1 | The held-out step budgets left out the per-job and per-step overheads; with the readers near their caps judge32 started with about 715 s against 700 and was skipped on OLMo-2's fallback path, leaving no `judge-items.json` and a FileNotFoundError in extract. | Fixed: an overhead model measured in job 1471 (`budget.overhead_model`); held-out budgets readers [1150, 1000], Qwen3.5-9B [1650, 1500], judge32 [700, 500], judge8 [350, 250]; abstention budgets re-sized too; `min_start_s` covers each step's overhead plus `max_s`; tests simulate the normal and fallback paths for both jobs and record the residual path (a time-capped OLMo-2 pass followed by its fallback), which section 11 discloses; a missing `judge-items.json` is a named V2 error (sections 8 and 11). |
| M2 | Section 16's commands could not run end to end. | Fixed: `am3g-mac-bundle.sh` (bundle and bootstrap copies, with their SHA-256), a bootstrap check in `am3g-checkout.sh` (the copies must equal the commit's), `am3g-job-state.sh` (polls once and saves `scontrol` when a job ends), `am3g-image.sh` (IMAGE from the build record after provenance and receipt checks), the selftest wait, FREEZE and FREEZE8 used consistently (section 16). |
| M3 | G-J1 replays AM1's items and cannot fail; nothing validated the judge on the new readers' replies. | Fixed: a registered blind hand check of every H1 discordant cell with as many seeded concordant distractors, by an isolated agent (D9, disclosed as agent labels), the labels' digest committed before the join, and the decision rule of section 7.1 (a directional reading stands only if the hand-label test, with Holm, rejects in the same direction; otherwise JUDGE_DEPENDENT; NO_DETECTED_DIFFERENCE stays; too few or missing labels defined); hand-against-judge agreement and kappa reported; `hand-sample`, `hand_check`, `confirm_reading`, `am3g-hand-sample.sh`, `am3g-hand-receipt.sh`, tests; rehearsed on development data (section 15). G-J1 is renamed a replay of AM1's validation items. |
| m1 | Twin counts: 5 development twins (`09ba9854` is also a Step 0 demo), and 2 Step 0 demos outside the 347; the membership order was wrong. | Fixed in `twin_membership` (split first) and recounted by `abstention-facts`; section 1.2 and the dry-run record corrected. |
| m2 | The old program's audits aligned third-party outputs to all 500 tasks, the abstentions included. | Disclosed in section 1.2. |
| m3 | The rerun rule was not mechanical. | Fixed: `rerun-decision` maps the driver's step statuses and the lane's termination reasons to complete, rerun, no-rerun or void, before extract; a held-out rerun runs before the abstention job; extract takes the rerun's id (sections 8 and 16; tests). |
| m4 | A second analyze with ABSTENTION_VOID overwrote the failing run's outputs and logs. | Fixed: the void path writes to `out-FREEZE8-void-*` and its own log; analyze runs once per input set and refuses an existing output directory. |
| m5 | The break-even definitions were incomplete. | Section 6.4 states the defined-only interval and the count of undefined resamples, the percentile indices, gain = loss = 0 giving 1, and the crossing hidden by "undefined". |
| m6 | Twins: turn-text overlap unchecked; no interval that resamples the linked pairs together. | `abstention-facts` counts memory-text overlap by SHA-256 (27 of 30 pools share a memory with the twin's user turns); `natural_mix_linked_twins` resamples the 22 linked pairs as units (section 6.4). |
| m7 | `load_heldout_tables` and `labels_vs_tables` never read a real tables file. | `load_pinned_tables` checks both digests and the entries' keys (tested on scratch files); the dry run reads the pilot's committed tables with the R2 code and reproduces AM3's 8,913 of 8,946; a test opens the development tables and hashes the held-out ones. |
| m8 | A missing judge-items file and a missing table raised tracebacks. | Named V2 and V1 errors; the host commands report any other missing or unreadable input as a named V2 error (section 8; tests). |
| m9 | "Bit for bit" overstated R1. | "Token for token" in sections 1.4 and 8; log-prob bits are reported, not gated. |
| m10 | VOID's precedence was not stated. | Section 7.1 and section 8: VOID over JUDGE_DEPENDENT (G-J1) over the hand check, and over JUDGE_QUALIFIED. |
| m11 | OLMo-2's scope if its pass comes from the fallback. | Section 7.1; `h1.readers.*.scope` and `engine_mode` record it. |
| m12 | The abstention inputs directory was writable. | `chmod a-w` on the host (the file was already read-only). |
| m13 | The archived port's digest was not asserted. | A test asserts `77aed59a...` where `legacy/` exists (skipped in the image). |
| Info | Job 1470; 0.94 x 0.1124; Holm's power; `ops/jobs.log`; pin the lane's container-side scripts and `uv.lock`. | Section 15 says what is known of job 1470 (not this registration's); section 18 corrected to 0.106; section 7.1 says "at least as powerful"; extract, analyze, staging and the new scripts append to `ops/jobs.log`; the lane's container-side scripts, the Dockerfile and `uv.lock` are pinned in section 16. |

### Round 2

Pre-freeze check 2 ran on `10735cd7` and found four major items, nine minor ones and several for
information. The fixes are commit `c2eaa62b` (code, tests, operator scripts, power), three
commits the dry run's own rehearsals made necessary (`507f4284`, `495090ef`, `3d4762ba`), and the
commit that carries this section. The CPU parts of the dry run were rerun, a runbook rehearsal
was added and the hand check was labelled again under the registered protocol (section 15). No
model ran on a held-out or abstention question, and round 2 used no GPU time.

| Item | Finding | Disposition |
|---|---|---|
| M1 | `IMAGE=$(am3g-image.sh ...)` captured two lines, because `log_job` wrote its line to stdout as well as the log. | `log_job` writes to the log and stderr only; `am3g-image.sh` prints exactly the image id; `check_image` (one line matching `^sha256:[0-9a-f]{64}$`) guards `am3g-selftest.sh` and `am3g-submit.sh`. The rehearsal found the same fault in `am3g-preflight.sh`, whose report reached the stdout of `am3g-build.sh` and `am3g-submit.sh`; it now reports on stderr (`507f4284`). Rehearsed (section 15). |
| M2 | `am3g-submit.sh` went on after a failed dry run, and a failed submission used up the population's one submission. | Every check is `cmd > f \|\| { ...; exit 2; }`; the submitter's output goes to `T.tmp` and becomes the submit record only when it exited 0 with a numeric last line. Rehearsed: a failed dry run, a failed test-only check, a GPU job in the queue, a failed sbatch and an output without a job id each leave no record, and submit then succeeds once. |
| M3 | The rerun rule's order let a step's status decide before a hard stop or a signal. | `rerun_decision` applies, in order: never started; void (V1); complete; the lane's hard stop on an incomplete job, no-rerun; a signal, rerun unless the lane's finish time is within 300 s of its hard stop; then the steps. Section 8 lists the order; tests and the rehearsal cover a hard stop with a failed step and a signal (no-rerun) and a signal before the limit with a step killed late (rerun). |
| M4 | The labeller was not registered: who labels, with what prompt and tools, in what units, how often, and with what record. | Section 8: files in `R/hand/`; an isolated Claude agent, model `claude-opus-5-5`, per chunk of 60 items in a fresh context and directory, launched by `am3g-hand-label-mac.sh` through the CLI with only Read and Write; the launch prompt pinned (`HAND_LABELLER_PROMPT`, SHA-256 `98c35cea...`); one labelling run and one repair stage, each receipted (prompt digest, transcript digests, labels' digest); no other relabelling, and a correction after the join reported separately; no cap, with the expected count (200-400 items) and time. Beyond the finding: `hand-merge` audits every transcript (only the two Reads and the Write) and drops a chunk that fails; and since the CLI could not authenticate in drafting, one fallback is registered (a subagent with the same prompt, only after the CLI fails on a stage's first chunk, recorded in the receipt). The dry run's labelling used it (section 15); the rehearsal at `495090ef` exposed that the CLI reports an authentication failure as an assistant text, and the script now reads the result record (`3d4762ba`). |
| m1 | No rebuild action. | `am3g-build.sh ... rebuild` writes to `overlay-build-vllm-FREEZE8-r2` and refuses a third attempt; `am3g-image.sh` reads the latest attempt. Rehearsed. |
| m2 | A rerun did not require the rule's decision, and a rerun of a rerun was not void. | `am3g-submit.sh ... rerun` requires `rerun-decision-POP-J.json` for the submitted job to say "rerun"; `am3g-rerun-decision.sh` passes `--is-rerun` for the job in the rerun record, which turns "rerun" into void (V2). Tested and rehearsed. |
| m3 | Only two lines of the `scontrol` record were kept. | `am3g-job-state.sh` saves the whole record. Rehearsed. |
| m4 | The plan's digest was not bound, and the receipt's commit was not recorded. | `analyze --hand-plan-sha256` (from the receipt) refuses another plan; `am3g-analyze.sh` requires RECEIPT_COMMIT (40 hex) in `reg` mode and logs it. |
| m5 | A hung engine start can use up the job. | Disclosed in section 11 (a time-budget void with no rerun); the GPU job's code is unchanged. |
| m6 | `am3g-image.sh` did not check the base image, the vLLM commit or the provenance's commit and capsule. | It checks the base digest `b18abb2d...`, vLLM 0.31.0 at `db9527a4...`, and the provenance's and receipt's commit and capsule. The checks pass on job 1467's real record and refuse altered ones (rehearsal). |
| m7 | H1's power ignored the hand check. | `combined_power` and section 9's table (a = 1, 0.9, 0.8); `power.json`, `with_the_hand_check`. |
| m8 | H2's judge was not hand-checked. | A descriptive H2 part of the hand check: every H2 discordant cell of the three readers with as many distractors, check "abstention", mixed into the same run and order; b2_hand and c2_hand with Holm, and agreement per population (sections 6.3 and 8). |
| m9 | The held-out and abstention commands accepted any `--config`. | `check_config_binding` refuses any but the pinned config for those populations (section 8; tested). |
| Info | The overhead model's warm cache; the licence wording; replies that hedge; the distractor shortfall; H2's opportunities and strata; which scripts refuse a dirty checkout. | Section 11 (cold cache: judge8's 55 s of slack on the fallback path, only the second judge at stake); section 7.1 (c near 0 by construction, so NONABSTAIN_HELPS means at least 7 hand-confirmed gains at Holm's first step; the effect size with its intervals is part of the licence; the read cost of up to 70 calls against 1; patterns chosen on Qwen3-8B's development replies); section 6.4 (the hedge flag and the gains that hedge); section 8 (the shortfalls recorded per reader); section 6.3 (b2 per correct top-4 abstention, and the near-miss strata); section 16 (which scripts check the checkout, and which read records only). |

### Round 3

Pre-freeze check 3 ran on `0d62badf`, confirmed the rehearsal (40 of 40), 34 rerun-rule cases of
its own, the 52 pins, the config binding, the 130 tests, the dry run's labelling record against
the protocol and the absence of text and of stdout traps, and found two major and seven minor
items. The fixes are commit `acd58d73` (code, tests, operator scripts, rehearsal) and the commit
that carries this section (section 15). No model ran and no GPU was used.

| Item | Finding | Disposition |
|---|---|---|
| M1 | A relabelling or a chosen transcript left no record: `prepare` refused only an existing Mac work directory, `push subagent` needed only an error file's name, nothing counted the subagents per chunk or named the transcript kept, and the audit checked tool calls only. | `prepare` claims the stage on the host atomically (`mkdir R/hand/claim-STAGE`, a `jobs.log` line) and a claimed stage is refused; a CLI push happens only inside the `cli` action; `push subagent DIR` reads the operator session's `subagents/agent-ID.jsonl`, finds each chunk's transcript by its first message's SHA-256, copies it unmodified, and records per chunk the attempts, the agent id and the files scanned; the audit checks the model on every assistant line, the first prompt (with the absolute-path variant), the agent id and every timestamp after the CLI's recorded failure; the receipt records them and the count of matching transcripts. More than one transcript for a chunk voids the hand check (empty final labels: JUDGE_DEPENDENT for a directional reading). Section 8; tests; rehearsed, including the extra transcript. |
| M2 | A rerun decision taken before the job ended was kept for good. | `am3g-rerun-decision.sh` refuses unless `R/ops/scontrol-JOB.txt` and `termination.env` both exist, decides once, and writes through a temporary file; a job that cannot be decided is VOID (V2). Rehearsed. |
| m3 | A failed or repeated command could empty or overwrite a record. | Temporary file then move, and a refused repeat, for rerun-decision, hand-merge and hand-sample; a `summary.json` that is not a JSON object is a named V2 error. Tested and rehearsed. |
| m4 | The rebuild limit keyed on a directory the builder creates late. | `am3g-build.sh` records each submitted job id in `R/ops/build-attempts-SHORT.txt` and counts attempts from it; `build_root` follows it. Rehearsed with a build that fails before its root exists. |
| m5 | Audit paths matched by file name only; other tool-call block types passed. | Every Read and Write path must be in the chunk's own directory (absolute, or bare names for the CLI); any tool-call block other than a `tool_use` Read or Write fails, `server_tool_use` included. Tested. |
| m6 | Section 8 implied the CLI might work. | Section 8: the CLI is expected to fail the same way and is launched first to record the failure; the subagent is the expected launch; no one enters or creates a credential to make the CLI start. |
| m7 | What the fallback subagent sees was not disclosed or guarded. | Section 8 discloses its working directory (the repository) and context (`CLAUDE.md` files, `MEMORY.md`, git status with recent commit subjects, skill and agent listings); from the first GPU job until the receipt commit the orchestrator writes nothing judge-derived of this run to commit subjects, memory notes or repository files; the receipt records the instruction files' types and names; section 12 covers the Mac's copies (W and the session's `subagents/`) and their deletion after the evidence commit. |
| m8 | The receipt did not enforce its inputs. | It refuses a missing launch record, a subagent launch without the CLI's error, and a Mac transcript digest that differs from the audit's; it carries the sample's and merge's records and the manifest, and is committed at the staging destination (`hand-check/` of the run's evidence directory), which the staging copies unchanged; the verifier checks `results.json`'s hand digests against it and that its commit precedes the analysis log (sections 8, 16 and 17). |
| m9 | `am3g-job-state.sh` treated any state outside a short list as ended. | Only terminal Slurm states are ended; any other state is "running or unknown" (exit 1); exit 2 as before. Rehearsed. |
| Info | 0.12-0.24; USR1; the first step's record within a reader; the digest list's mode; `--verbose`. | Section 9 reads 0.12-0.23; section 11 says a hung engine start is usually killed by the lane's USR1 as "signal", with the same outcome; section 8 says the first incomplete unit, and within it the first matching step's record, decides; `transcripts-STAGE.sha256` is read-only after the merge; section 8's CLI command has `--verbose`. |
