# Which memories should a reader keep? Exact keep-set tables, credit, search and an abstention rule on LongMemEval-S

Internal research note, draft of 2026-10-16. CoTCodec research program, agent-memory line
(decisions D103-D131 in `program/decisions.md`). Program owner: Kevin Liu.

Repository: <https://github.com/Kevin-Liu-01/cotcodec> (public). Every evidence path below
resolves on `main` at `1cf31346`, the base of this revision's branch
`paper/memory-keepset-note-d131`. The revision changes only this note, its `README.md` and its
number table `numbers.md`. It narrows the claims to the novelty audit of decision D131 and adds
the line's later studies (AM4, AM5 and `am5-ablated-cost-v2`).

> **Status: INTERNAL DRAFT. Not published, not for circulation (D101).**
>
> - Publication is an outward action and stays the program owner's call (D101). Nothing here has
>   been posted, submitted or sent.
> - **No result here is a new phenomenon.** A novelty audit found prior work for each (D131)
>   [AUDIT]. Section 8 lists it, and the claims below are narrowed to it.
> - Every claim carries one status label:
>   - **[confirmatory]**: decided by a frozen registration's rule on held-out data;
>   - **[exploratory]**: development data, no decision rule;
>   - **[descriptive]**: reported by a frozen registration (or by its fixed secondary rule) but
>     deciding nothing;
>   - **[judge-qualified]**: rests on a judge that failed its own registered validation check;
>   - **[post hoc]**: computed after the registered outputs were read.
> - **Hand labels are an agent's, not a human's (D9).** Every judge hand check was labelled by a
>   Claude agent, blind to the judge's labels. No human has validated a judge label.
> - **No gauntlet score.** The four registrations were admitted without a gauntlet wave (D111,
>   D115, D118, D121). Blind discrimination and the provider-distinct reviews did not run.
> - **The held-out questions were reused.** Four registrations used the same 347 held-out
>   questions (the fourth with their evidence removed). Each later one disclosed, before it ran,
>   what the earlier ones had published about them.
> - The note quotes no question, answer, reply or memory text. The only reply string it names is
>   the abstention form "I don't know", which the reader's prompt asks for when the memories
>   lack the answer.

## Summary

A memory system that retrieves 8 memories for a question can show the reader all 8 or keep a
subset. We asked how to choose 4 of 8. On LongMemEval-S (cleaned) we ran a reader, Qwen3-8B,
whose outputs replay bit for bit, on all 256 subsets of each pool, and judged every reply with
Qwen3-32B. That gives, for each question, the exact outcome of every keep set, so any rule's
choice can be scored against the best 4-subset. None of the findings is a new phenomenon
(D131). The strongest result is the exact tables: keep-set regret against the exact keep-4
optimum, on 694 exhaustive judged tables, is the one measurement for which the novelty audit
found no direct prior [AUDIT]. Wherever this note says the audit found no prior, it means none
was found through 2026-10-16 under the audit's coverage (section 8), not that none exists.

- **Exact tables score the credit rules that memory learners use [confirmatory].** On 251
  held-out questions whose table is not constant, keeping the top 4 by leave-one-out credit
  loses 0.277 of a correct answer per question against the best 4-subset (99% [0.223, 0.333]),
  0.233 [0.194, 0.273] more than exact Shapley. All five registered rules, among them CMP's
  SNIPW-64 and MeClear's permutation Shapley-16, are MISSPECIFIED; the audit found no earlier
  exact-truth score for those two.
- **Leave-one-out fails mainly where the reader fails [post hoc].** 64.6% of its regret comes
  from the 69 of the 251 tables that the reader gets wrong even with all 8 memories. Exact
  Shapley and exact Banzhaf keep an optimal set in 95.6% and 96.4% of those 251 tables. This is not
  evidence that memory interactions defeat per-memory credit.
- **With an oracle utility, search over keep sets beats the credit rules tested; the registered
  verdict is INCONCLUSIVE [confirmatory].** Keeping the best of random 4-subsets loses less than
  leave-one-out, SNIPW-64 and MSR-Banzhaf-64 at equal calls, and less than SNIPW-64,
  MSR-Banzhaf-64 and permutation Shapley-16 when it reads 26 subsets to their 57-83. Against
  greedy backward elimination it is not separated (one-sided upper bound +0.0014). The utility
  needs the reference answer, and the search is easy: on average 37.5% of the 70 candidate
  4-subsets are optimal [post hoc].
- **A known abstention-gated keep rule replicates in the agent-memory setting [confirmatory].**
  Keeping the first BM25-ranked 4-subset whose reply does not abstain, a variant of the stop
  rule of Wang, Ma and Kumar (2025), beats BM25 top 4 for Qwen3-8B (+0.112 [0.081, 0.147], 39
  questions gained, 0 lost), OLMo-2-1124-7B-Instruct (+0.101 [0.069, 0.133], 35 against 0) and
  Qwen3.5-9B (+0.089 [0.061, 0.121], 31 against 0). A Self-Route-style fallback, BM25 top 4
  unless its reply abstains and all 8 otherwise, recovers 43-77% of that gain [post hoc].
- **The rule has a cost [descriptive and judge-qualified; then confirmatory].** On
  LongMemEval-S's 30 unanswerable questions it turns a correct abstention into a wrong answer 5,
  8 and 1 times for the three readers (hand counts 5, 8 and 0). With each held-out question's
  evidence removed and the rule capped at 8 reads, its cost is below its gain for Qwen3-8B (6
  against 31 of 347) and Qwen3.5-9B (6 against 26; uncapped, 16 against 31, not separated
  [descriptive]), and not separated for OLMo-2 (22 against 27). The gain side and the cap were
  known before that registration.

The scope throughout is one dataset, one prompt that asks for "I don't know", BM25 user-turn
pools of 8, a budget of 4 and the Qwen3-32B judge (section 7).

## 1. The question

Agent memory systems decide which stored memories to show the reader for a question. Several
2026 memory learners train on per-memory causal credit: one-shot deletion (leave-one-out),
permutation Shapley, or exposure-weighted estimates [AM1-REG section 1]. A keep or evict
decision chooses a set. That the top k by per-item credit need not be the best k-subset, and
that leave-one-out does worse than Shapley when items are redundant or complementary, are known
(section 8). The line scored these estimators against the exact best keep set on a memory
benchmark (Result 1), asked whether search over keep sets beats estimating credit when a keep
set's utility can be queried (Result 2), and asked what chooses keep sets without labels, at
what cost (Result 3 and section 6).

The line came from the program's 2026-10-14 question sweep, which ranked AM1 the memory lead and
folded two other candidates into it as placebo arms (AM2) and an internal-signal analysis (AM6)
[SWEEP entries 3, 5 and 6; DEC D103, D104]. Only AM1, AM2 and AM6 keep the sweep's meanings: in
the sweep, AM3-AM5 name other candidates (D120) [SWEEP].

**Table 1. The studies of the memory line.**

| Study | Status | Data | Decision |
|---|---|---|---|
| AM1 Step 0 | exploratory | eight demo questions | replay works (D107) |
| AM1 development pilot | exploratory | 63 development questions, 126 tables | design of AM1 (D111) |
| `am1-memory-credit-v1` (AM1) | confirmatory | 347 held-out questions, 694 tables | H2: five rules MISSPECIFIED (D112) |
| AM1b | exploratory | the pilot's tables, CPU only | with an oracle utility, direct search beats query-based credit at equal calls on development (D113) |
| AM1d | exploratory | the pilot's replies, CPU only | abstention is the usable signal (D115) |
| `am1-keepset-search-v1` | confirmatory | AM1's held-out tables and replies, CPU only | H-A INCONCLUSIVE; H-C NONABSTAIN_HELPS (D117) |
| AM3 | exploratory | 63 development questions, three readers | direction holds, not separated (D118) |
| `am3-nonabstain-generality-v1` | confirmatory (H1); descriptive (H2) | 347 held-out + 30 abstention questions | H1 NONABSTAIN_HELPS for both new readers (D119) |
| AM4 | exploratory, post hoc | the previous row's features, CPU only | a read-cap curve; licenses nothing (D119) |
| AM5 | exploratory | 63 development questions, evidence removed, three readers | design of the cost test (D121) |
| `am5-ablated-cost-v1` | void before running | none | stale code pin; never opened its gate (D123) |
| `am5-ablated-cost-v2` | confirmatory (K = 8); descriptive (K = 70) | 347 held-out questions, evidence removed, three readers | COST_BELOW_GAIN for both Qwen readers; NOT_SEPARATED for OLMo-2 (D126) |

## 2. Setup

### 2.1 Data and split

The data are LongMemEval-S, cleaned (`xiaowu0162/longmemeval-cleaned` at `98d7416c`, MIT,
SHA-256 `d6f21ea9...`), kept on the host only [AM1-REG section 3]. Each question comes with a
chat history of sessions. A question is usable when it is not an abstention question, every
gold turn is a user turn, and it has 1 to 6 gold turns: 416 of the 500 questions [PILOT,
"Design"].

The usable questions were split by type with a seeded shuffle: 15% per type (rounded half up)
to development, 63 questions, and the other 353 held out [PILOT, "Design"]. Step 0 had already
run eight demo questions before the split was drawn, six of them held-out ids, so all eight are
excluded from every estimand. The confirmatory set is the remaining **347** held-out questions
(knowledge-update 59, multi-session 101, single-session-assistant 4, single-session-preference
25, single-session-user 52, temporal-reasoning 106) [AM1-REG sections 3-4].

LongMemEval-S also has 30 abstention questions, made by editing an answerable question so that
it asks about something the history does not contain. Every AM1 config excluded them, so no
study of this line used them before `am3-nonabstain-generality-v1` [AM3G-REG sections 1.2 and
3].

### 2.2 Memories, pools and the budget

A memory is one user turn with its session date, at most 1,500 characters. A pool is 8 memories
in chronological order [AM1-REG section 4]. There are two pool arms:

- **retrieved** (primary, the deployable pool): the BM25 top 8 user turns for the question
  (Okapi with Lucene's idf, k1 1.5, b 0.75). BM25 stands in for the MiniLM retriever the sweep
  proposed [PILOT, "Problems and deviations"]. On the held-out questions the retrieved pool holds
  no gold turn for 43 questions, 1 for 117, 2 for 174 and 3-5 for 13 [AM1].
- **gold** (secondary, for identification): every gold user turn plus seeded distractors from
  the question's other user turns.

The decision studied is keeping B = 4 of the 8.

### 2.3 Reader and exact replay

The reader is Qwen3-8B (Apache-2.0) with thinking off, greedy decoding, at most 64 new tokens,
and Step 0's prompt, which asks it to say "I don't know" when the memories lack the answer
[AM1-REG sections 3 and 5; AM1D, "Design"]. It ran in vLLM 0.31.0 in batch-invariant mode
(`VLLM_BATCH_INVARIANT=1`) with `enforce_eager=True`.

Step 0 found batch-invariant greedy replay bit-exact on 4,096 of 4,096 requests, at 1.32-1.38x
the wall time when batched [DEC D107; exploratory]. The pilot then found that compiled replay is
exact only for the same compiled kernels: in job 1411 a replicate with its own compile matched
in tokens on 33,463 of 34,524 requests (96.93%), and judged correctness differed on 87 of 34,399
(0.25%), in 41 of 126 tables, because inductor's autotune chose another reduction block
(`R0_BLOCK` 2048 against 4096). Eager mode replayed bit-exactly in every comparison (8,768 of
8,768 requests each) at 1.06x the wall time [PILOT; exploratory]. In AM1's registered run (gate
G1), 190,156 of 190,156 reader requests and 10,230 of 10,230 primary-judge items gave identical
tokens and log-prob bits across two GPUs, two processes and two orders [AM1; confirmatory].

The two later readers differ. vLLM 0.31.0 refuses batch-invariant mode for Qwen3.5-9B's GDN
attention, so it ran in vLLM's default mode, with no replay guarantee. OLMo-2 ran
batch-invariant through vLLM's Transformers backend [AM3D, "Readers"].

### 2.4 Judge and hand checks

A cell's utility u(S) is 1 when the judge says the reply to the question, given memory subset
S, is correct. The judge is Qwen3-32B (Apache-2.0) with LongMemEval's own answer-check prompt
(`get_anscheck_prompt`, ported word for word); the label is whether "yes" occurs in its
case-folded reply. Qwen3-8B with the same prompt is a second judge [AM1-REG section 5].

- **Pilot [exploratory].** The judge agreed with a blind hand check on 117 of 120 development
  items (κ 0.95); Qwen3-8B on 109 (κ 0.82); Step 0's containment rule had κ 0.45 [PILOT].
- **AM1's gate G2 [confirmatory].** The judge said yes to 322 of 322 reference answers of
  non-preference questions and no to "I don't know." on 347 of 347 held-out questions. A blind
  hand check of 120 judged replies gave κ 0.867 against the 0.80 bar; the gate reads the point
  estimate, and its 95% interval, [0.767, 0.950], reaches below the bar. In a post-join
  description, 7 of the 8 disagreements are on preference items [AM1].
- **The second judge's known error.** Qwen3-8B called "I don't know." correct on 49 of 347
  held-out validation items [AM1; KS-REG section 1.1].

### 2.5 Exact tables and regret

For each pool the reader answered all 256 subsets; with 16 matched content swaps and 2
reorders (the placebo arms) that is 274 requests per pool and 190,156 per pass over 694 pools
[AM1-REG section 4]. The judged labels form a table u over the subsets. A table is constant when
u is the same on all 256 subsets; every constant table is all 0, and the empty pool is never
answered right. Keep decisions are scored on non-constant tables only: 251 retrieved and 288
gold on the held-out set [AM1].

For a budget B, OPT_B is the best value over all B-subsets. A rule's **regret** is OPT_B minus
u(its keep set), averaged over every keep set its ties allow and, for randomized rules, over
seeds [AM1-REG section 6]. It is in correct answers per non-constant question: 0.05 means losing
one answer in twenty that the best keep set gets. A reader call is one distinct subset whose
u(S) a rule reads, memoized per pool; leave-one-out reads 9 (the full set and 8 deletions), and
exact Shapley or Banzhaf credit reads all 256 [AM1B, "Rules and how calls are counted"].

### 2.6 Preregistration, the ledger and verification

The four confirmatory studies followed one process:

- **Freeze.** Hypotheses, decision rules, seeds, caps and the SHA-256 of every code file are
  fixed in a registration, frozen by `scripts/preregister.py freeze` into a hash-chained row of
  `program/preregistrations/ledger.jsonl`, in a commit that adds only that row. The scripts
  refuse held-out inputs until that row exists and every code pin matches.
- **Checks before the freeze.** Fresh reviewers who did not draft the file checked it and its
  code: two rounds for AM1, `am1-keepset-search-v1` and `am5-ablated-cost-v2`, three for
  `am3-nonabstain-generality-v1`.
- **Checks after the run.** The digest of the blind hand labels was committed before the
  analysis joined them [AM1; AM3G; AM5R]. A verifier that shared no context with the analyst
  reran the registered analysis from a new export or clone of the freeze commit, got
  byte-identical outputs, and reproduced the headline results with its own code [AM1; KS; AM3G,
  "Verification"; AM5R, "Verification"]. The exploratory studies had a fresh checker of the same
  kind [AM1B; AM1D; AM3D; AM5], except AM4, which has a second computation route (section 9).

Intervals are question-cluster percentile bootstraps, 95% unless stated: 4,000 resamples in AM1
(1,000 for AUROC) [AM1-REG section 6] and 10,000 in AM1b, AM1d, AM4 and the later
registrations. Paired accuracy comparisons use the exact McNemar test, and rates over the 30
abstention questions get exact Clopper-Pearson intervals.

## 3. Result 1: exact keep-set tables; leave-one-out credit picks bad keep sets (AM1)

**Development pilot [exploratory].** On the 63 development questions, 53 of 89 non-constant
tables were non-monotone: some memory helps on some sets and hurts on others. A non-gold memory
mattered in 58. On the retrieved arm at B = 4, leave-one-out lost 0.214 [0.121, 0.316] and
exact Shapley 0.079; their paired difference was +0.135 [0.051, 0.227] [PILOT]. The
registration's thresholds were set from the pilot's scale [AM1-REG section 15].

**The registered rule.** For each of five primary rules, a 99% interval for the mean regret at
B = 4 on the retrieved arm (Bonferroni over the five): MISSPECIFIED if the lower bound exceeds
0.05, ADEQUATE if the upper bound is below 0.02, INCONCLUSIVE otherwise. Leave-one-out is the
headline, read together with its paired difference from exact Shapley [AM1-REG section 7].

**Gates [confirmatory].** Every gate passed and no kill criterion fired: no incomplete table,
G1 replay PASS, G2 judge PASS, 43 of 347 questions constant in both arms (12.4%, against a 60%
kill line), and 251 non-constant retrieved tables against a 150 floor [AM1].

**Table 2. Keep-set regret at B = 4, retrieved arm, 251 non-constant held-out tables**
[confirmatory for the five primary rules; the three references are descriptive] [AM1, "H2"].

| Rule | Calls | Regret, 95% | 99% (decision) | Verdict | Suboptimal share | Minus exact Shapley, 95% |
|---|---:|---|---|---|---:|---|
| leave-one-out (the headline) | 9 | 0.277 [0.235, 0.319] | [0.223, 0.333] | MISSPECIFIED | 0.546 | +0.233 [+0.194, +0.273] |
| permutation Shapley-16 | ≤ 129 | 0.138 [0.107, 0.173] | [0.096, 0.187] | MISSPECIFIED | 0.279 | +0.094 [+0.066, +0.126] |
| SNIPW-64 | 64 | 0.094 [0.066, 0.123] | [0.058, 0.133] | MISSPECIFIED | 0.171 | +0.050 [+0.023, +0.078] |
| retrieval rank (BM25 top 4) | 0 | 0.343 [0.287, 0.402] | [0.271, 0.418] | MISSPECIFIED | 0.343 | +0.299 [+0.243, +0.359] |
| raw attention | 1 + 1 forward | 0.311 [0.251, 0.371] | [0.235, 0.382] | MISSPECIFIED | 0.311 | +0.267 [+0.207, +0.323] |
| exact Shapley (reference) | 256 | 0.044 [0.020, 0.072] | [0.012, 0.080] | none | 0.044 | |
| exact Banzhaf (reference) | 256 | 0.025 [0.009, 0.043] | [0.005, 0.050] | none | 0.036 | |
| random keep set (reference) | 0 | 0.625 [0.596, 0.653] | [0.587, 0.661] | none | 0.976 | |

- **The registered program reading holds [confirmatory]:** per-memory deletion credit is
  misspecified for keep and evict decisions on this benchmark (this reader, this judge, BM25
  user-turn pools, 4 of 8). Top-4 keep sets by deletion credit lose 0.277 of a correct answer
  per non-constant question and are suboptimal in 55% of tables. The reading is about
  leave-one-out; it does not extend to per-memory credit as such, and only per-query keep sets
  were scored, not retention in a shared memory store [AUDIT].
- **In the registered sense, the loss is specific to deletion credit [confirmatory]:**
  leave-one-out loses 0.233 [0.194, 0.273] more than exact Shapley credit on the same tables.
  Permutation Shapley-16 and SNIPW-64 are MISSPECIFIED too; their paired differences (+0.094,
  +0.050) are secondary descriptions with no decision rule.
- **Not licensed:** any statement about exact Shapley's adequacy (its 99% interval, [0.012,
  0.080], spans both thresholds) or a ranking of the rules. No rule is ADEQUATE, which the
  registration expected to need a true regret below about 0.01 [AM1-REG sections 7 and 9].
- **SNIPW-64's verdict rests on three seeds.** It was the closest call (99% lower bound 0.058).
  Over 3 seeds its regret was 0.094; over 200 seeds on the same tables it is 0.085 [KS], and on
  development 3 seeds gave 0.070 against 0.050 for 20 [AM1B, caveat 2]. No 99% interval at 200
  seeds was computed, so whether SNIPW-64 stays MISSPECIFIED in expectation over its draws is
  not known.

**Where leave-one-out loses [post hoc].** The audit recomputed regret from AM1's committed
tables, split by whether the reader answers correctly with all 8 memories [AUDIT, "Synthesis
recomputation"]. On the 182 tables it gets right, leave-one-out loses 0.135, exact Shapley 0.011
and exact Banzhaf 0.005; on the 69 it gets wrong, 0.651, 0.130 and 0.075.

- 64.6% of leave-one-out's regret comes from those 69 tables. Leave-one-out measures marginals
  only at the full pool: in 25 of the 69 all its credits are tied, and in 19 of the 182 they are
  all zero, the redundancy failure Ghorbani and Zou describe.
- On the 182 tables leave-one-out still loses 0.124 more than exact Shapley (the auditor's
  bootstrap [0.098, 0.153]), about half the registered +0.233.
- Exact Shapley and exact Banzhaf, both additive per-memory credits, keep an optimal set in
  95.6% and 96.4% of the 251 tables, leave-one-out in 45.4%; no adequacy verdict is licensed.
- So the result is **not** evidence that memory interactions defeat per-memory credit: one-shot
  deletion is a poor keep rule here, mostly in pools the reader fails anyway.

**Across budgets, arms and judges [descriptive].** Leave-one-out loses more than exact Shapley
at every budget from 1 to 4 on both arms, with every 95% interval above 0: from +0.149 (B = 1)
to +0.256 (B = 3) on the retrieved arm and from +0.104 (B = 1) to +0.207 (B = 4) on the gold
arm. On the second judge's 260 non-constant retrieved tables all five primary rules are again
MISSPECIFIED; leave-one-out loses 0.259 (99% [0.206, 0.312]), +0.201 [+0.167, +0.239] more than
exact Shapley. Over the 539 non-constant tables of both arms, leave-one-out picked an optimal
4-subset in 51.8% of tables and exact Shapley in 96.1% [AM1].

**Interaction share (H1) [descriptive].** Under the uniform measure on subsets, the share of a
table's variance at Fourier order 2 or higher is 0.379 [0.342, 0.416] on the retrieved arm. An
AND or OR of m needed memories already puts 1 - m/(2^m - 1) at order 2 or higher. The excess
over that baseline at each question's gold count is +0.156 [+0.119, +0.194] on the retrieved arm
and +0.094 [+0.058, +0.129] on the gold arm. Of the 251 non-constant retrieved tables, 167 are
non-monotone, 57 depend on a single memory, 12 are AND, 8 are OR and 7 are monotone but mixed; a
non-gold memory matters in 182 [AM1]. The audit reads part of the order ≥ 2 share as position brittleness,
since a content-free reorder changes 17.1% of full-pool answers (AM2 below) [AUDIT]; order effects
were not separated from other causes (section 7).

**Placebo floor for non-gold deletion labels (AM2) [descriptive: a registered secondary rule
with no program decision].** A deletion label says that removing memory i flips judged
correctness. The placebo replaces memory i's text with a length- and rank-matched irrelevant user
turn of the same question at the same slot [AM1-REG section 4]. Over both arms:

| Memory class | Deletion flip rate | Swap flip rate | Deletion minus swap, 95% | Nonzero deletion labels that survive |
|---|---|---|---|---|
| gold | 0.440 [0.399, 0.483] | 0.441 [0.400, 0.483] | -0.0008 [-0.0097, +0.0082] | 0.641 [0.586, 0.697] |
| non-gold | 0.072 [0.059, 0.085] | 0.062 [0.051, 0.074] | **+0.0099 [+0.0026, +0.0170]** | 0.128 [0.086, 0.175] |

The registered reading is ABOVE THE SWAP FLOOR for non-gold labels (lower bound +0.0026), and
the gold arm drives it: the non-gold difference is +0.0204 [+0.0090, +0.0324] there and +0.0002
[-0.0094, +0.0103] on the retrieved arm. ABOVE is not evidence of a content effect: deletion also
shortens the prompt and moves the later memories [AM1-REG section 7]. Only 12.8% of nonzero
non-gold deletion labels survive the placebo control (both swaps reproduce the label and no
reorder flips the pool), against 64.1% of gold labels, and a content-free reorder of the full
pool changes judged correctness in 17.1% [14.6%, 19.8%] of reorders [AM1]. The pilot had read
NOT ABOVE, +0.0006 [-0.013, 0.013], and on the retrieved arm neither data set shows an excess
(development -0.017 [-0.040, 0.001]) [PILOT, "AM2"].

**Internal signals (AM6) [descriptive].** Attention heads chosen by cross-fitting against exact
Shapley predict which memories are necessary at AUROC 0.890 [0.865, 0.914], 0.060 above the best
cheap baseline (overlap with the reply, 0.830); raw attention (0.832) ties it. The heads need
exact tables of other questions to select, so they are not a deployable signal [AM1].

## 4. Result 2: with an oracle utility, search over keep sets beats the credit rules tested

### 4.1 Development: the cost curve (AM1b) [exploratory]

AM1b computed, on a CPU from the pilot's committed tables, each rule's regret against the reader
calls it reads, on development data only. Its baseline is **direct search**: read m distinct
random 4-subsets and keep the best one read. Its expected regret is exact, from order
statistics, and at 70 calls (every 4-subset) it is 0 [AM1B].

**Table 3. Regret against calls, retrieved arm, B = 4, 38 non-constant development tables**
[exploratory] [AM1B, "Results"].

| Rule | Calls | Regret [95%] | Direct search at the same calls |
|---|---:|---|---:|
| retrieval rank | 0 | 0.132 [0.026, 0.237] | 0.576 |
| leave-one-out | 9 | 0.214 [0.123, 0.316] | 0.091 |
| greedy forward (BM25 ties) | 26 | 0.105 [0.026, 0.211] | 0.024 |
| greedy backward (BM25 ties) | 26 | 0.079 [0.000, 0.184] | 0.024 |
| SNIPW-64 (20 seeds) | 56.8 | 0.050 [0.014, 0.099] | 0.005 |
| MSR-Banzhaf-64 | 64 | 0.043 [0.009, 0.091] | 0.002 |
| permutation Shapley-16 | 83.4 | 0.095 [0.032, 0.171] | 0.000 |
| exact Banzhaf | 256 | 0.031 [0.000, 0.079] | 0.000 |
| exact Shapley | 256 | 0.079 [0.000, 0.184] | 0.000 |

Direct search alone loses 0.091 at 9 calls, 0.046 at 16, 0.024 at 26 and 0.017 at 32.

In this cell no query-based credit rule beats direct search at equal calls, even on the point
estimate, and no credit rule's 99% upper bound is at or below 0.05. Retrieval rank, at 0 calls,
beats every rule below about 15 calls. Outside this cell only greedy forward at gold B = 2 beats
direct search with a 95% interval below zero. A credit vector ranks memories for every budget at
once, while direct search answers one budget (covering B = 1 to 4 takes up to 162 calls), so a
case for credit would rest on many budgets or on credits that transfer across questions; neither
was tested [AM1B, caveat 1; DEC D113].

### 4.2 Held-out: H-A of `am1-keepset-search-v1` [confirmatory; verdict INCONCLUSIVE]

The registration ran CPU-only on AM1's 694 held-out tables, without a new model call. It
compared direct search with five rules in seven paired comparisons, each a mean over the 251
non-constant retrieved tables of direct search's regret minus the rule's (negative means search
loses less). Sampled rules were averaged over 200 seeds. Each comparison is SEARCH_BETTER if its
one-sided upper bound at 1 - 0.05/7 is below 0, RULE_BETTER if its lower bound is above 0, and
NOT_SEPARATED otherwise; for the sampled rules a bound must clear 0 by more than three Monte
Carlo standard errors. SEARCH_DOMINATES needs all seven SEARCH_BETTER [KS-REG sections 6.3 and
7.1].

**Table 4. H-A, retrieved arm, 251 tables** [confirmatory] [KS, "H-A"].

| Id | Rule (rule's calls) | Direct search's calls | Difference | 95% CI | One-sided bounds (lower, upper) | Class |
|---|---|---|---:|---|---|---|
| A1 | leave-one-out (9) | 9, equal | -0.151 | [-0.180, -0.124] | -0.187, -0.117 | SEARCH_BETTER |
| A2 | SNIPW-64 (56.7) | equal, per draw | -0.078 | [-0.098, -0.059] | -0.104, -0.055 | SEARCH_BETTER |
| A3 | SNIPW-64 (56.7) | 26, fewer | -0.049 | [-0.062, -0.036] | -0.066, -0.034 | SEARCH_BETTER |
| A4 | MSR-Banzhaf-64 (64) | 64, equal | -0.076 | [-0.097, -0.056] | -0.102, -0.051 | SEARCH_BETTER |
| A5 | MSR-Banzhaf-64 (64) | 26, fewer | -0.042 | [-0.055, -0.030] | -0.059, -0.027 | SEARCH_BETTER |
| A6 | permutation Shapley-16 (83.3) | 26, fewer | -0.096 | [-0.119, -0.073] | -0.125, -0.068 | SEARCH_BETTER |
| A7 | greedy backward, BM25 ties (26) | 26, equal | -0.032 | [-0.062, -0.005] | -0.069, +0.0014 | NOT_SEPARATED |

The rules' regrets were 0.277 (leave-one-out), 0.085 (SNIPW-64), 0.078 (MSR-Banzhaf-64), 0.132
(permutation Shapley-16) and 0.068 (greedy backward). Direct search's exact regret was 0.141 at
8 calls, 0.126 at 9, 0.067 at 16, 0.036 at 26, 0.020 at 38, 0.003 at 64 and 0 at 70
[descriptive] [KS].

Read exactly:

- **The verdict is INCONCLUSIVE.** Six of the seven comparisons are SEARCH_BETTER; A7 is
  NOT_SEPARATED. SEARCH_DOMINATES needed all seven.
- **Of the six, three are at equal calls** (A1, A2, A4) and three give search fewer calls (26
  against the rule's 56.7-83.3: A3, A5, A6). Every comparison against a credit rule is
  SEARCH_BETTER.
- **The comparison not separated is search against search.** Greedy backward elimination is
  itself a search over keep sets. Its two-sided 95% interval excludes 0, but the registered
  one-sided upper bound, +0.0014, does not; under 200 other bootstrap seeds the verifier found
  that bound between +0.0005 and +0.0032 [KS].
- **What is licensed:** given an oracle utility, direct search over random 4-subsets loses less
  than the credit rules of A1-A6, in expectation over held-out questions with a non-constant
  retrieved table [KS, "What the result licenses"].
- **What is not licensed:** SEARCH_DOMINATES, or any statement about greedy backward
  elimination against direct search in either direction.
- **The error rates are nominal.** In a size simulation every measured verdict error was below
  0.05 [KS-REG section 9].
- **The gold arm [descriptive]** shows the same pattern: A1-A6 SEARCH_BETTER and A7 not
  separated.

H-A reads the judged utility, which needs the reference answer, so it measures how well a rule
attributes credit within one question when labels are available; it is not a keep policy. The
tables are deterministic replays, so a search that keeps the best of noisy utilities would face a
winner's curse that this design cannot see [KS-REG section 3]. The search is also easy here: on
the 251 tables the share of the 70 4-subsets that are optimal has mean 0.375 and median 0.400
[post hoc; AUDIT]. Search with a label-seeing utility over candidate sets is a known approach
(section 8).

## 5. Result 3: a known abstention-gated keep rule, replicated in the agent-memory setting

The rule tested here is a known stop rule, Wang, Ma and Kumar's (2025), with overlapping
4-subsets in place of disjoint windows (section 8) [AUDIT]. What this line adds is the
agent-memory setting, three open readers, frozen registrations and a cost test with the
evidence removed (section 6.4).

### 5.1 Development: label-free search (AM1d) [exploratory]

AM1d replaced the judged utility with scores computed from the reader's own replies under each
subset, on the pilot's 63 development questions, and searched over 4-subsets with them. The
four abstention patterns were committed before any reply was read [AM1D].

- **The reader's confidence follows the prompt.** On the retrieved arm, 2,405 of 4,410 4-subset
  replies (54.5%) abstain, and 2 of those are judged correct. The median mean token log-prob is
  -5.3e-6 for abstaining replies, -0.0037 for non-abstaining replies judged correct and -0.0131
  for those judged wrong, so "I don't know" is the most confident reply [post hoc diagnostic].
  Within a table, mean log-prob ranks subsets below chance (mean AUROC 0.326; the non-abstention
  flag, 0.854). Keeping the most confident reply is right on 0.208 of the 38 non-constant
  retrieved tables at 8 calls and 0.105 at 70; BM25 top 4 is right on 0.842. A majority vote
  over subsets fails the same way (0.318 at 8 calls, 0.237 at 70).
- **This is expected, not a finding (section 8).** The prompt asks for "I don't know", which
  makes that string the most probable output [AM1D, caveat 1], and the measurement covers 38
  development tables for one reader [AUDIT].
- **The only usable signal was abstention.** `nonabstain@70`, the best-BM25-ranked 4-subset
  whose reply does not abstain, scored 0.868 against 0.842 for BM25 top 4: +0.026 [+0.000,
  +0.079], one table of 38. Chosen in sample among 40 rules; picking the utility on half the
  questions and scoring it on the other half gives +0.025 at 70 calls.
- **A development lead that reversed.** BM25 top 4 was ahead of all 8 by +0.105 [+0.026,
  +0.211] on the non-constant retrieved tables, 4 tables against 0 (exact p = 0.125). On held-out
  data it reversed (section 5.2).

### 5.2 Held-out: H-C of `am1-keepset-search-v1` [confirmatory]

H-C tested one rule, chosen by AM1d: **nonabstain-BM25**. Read the 70 4-subsets in BM25 order
(BM25 top 4 first), keep the first whose reply does not abstain under AM1d's four patterns, and
keep BM25 top 4 when every 4-subset abstains. The rule reads no label. The test is the exact
two-sided McNemar test against BM25 top 4 over all 347 held-out questions, retrieved arm
[KS-REG sections 6.5 and 7.3].

- **NONABSTAIN_HELPS [confirmatory].** Accuracy 0.571 against 0.458: +0.112, bootstrap 95%
  [+0.081, +0.147]; 39 questions gained and 0 lost; exact p = 3.6e-12 [KS]. The exact
  conditional interval is [+0.092, +0.112]; its upper end equals the estimate because every
  discordant pair favours the rule.
- **Why it works [descriptive].** 13,598 of 24,290 retrieved 4-subset replies abstain (56%).
  BM25 top 4's own reply abstains on 116 questions; on 71 of them another 4-subset answers, and
  switching gained 39 and lost none. In 45 pools every 4-subset abstains, and the rule keeps
  BM25 top 4 [KS].
- **Why it rarely loses.** The rule leaves BM25 top 4 only when top 4's reply abstains, and
  the primary judge rejects abstentions on answerable questions ("I don't know." judged wrong on
  347 of 347 validation items). So losses are near 0 by construction, and the gain is the rate
  at which a pool that makes top 4 abstain holds a 4-subset that answers correctly [KS-REG
  section 7.3]. The audit calls the registered test close to guaranteed [AUDIT].
- **Pruning to BM25 top 4 is behind all 8 [descriptive, H-B].** 0.458 against 0.524: -0.066
  [-0.107, -0.026], 15 against 38, p = 0.0022. AM1's published figures implied this sign before
  the run, so H-B decides nothing (D116).
- **Against all 8 [descriptive].** Nonabstain-BM25 is ahead, +0.046 [+0.006, +0.086], 33
  against 17, p = 0.033. That comparison was not registered as a test.
- **Gold arm [descriptive].** +0.089 [+0.061, +0.121], 31 against 0.

### 5.3 Development: other readers (AM3) [exploratory]

AM3 ran three readers on the 63 development questions, with 71 requests per pool (the 70
4-subsets and the full pool): Qwen3-8B as an anchor, OLMo-2-1124-7B-Instruct (Apache-2.0,
ungated) and Qwen3.5-9B (default mode). The anchor's replies equal the pilot's eager pass on
2,272 of 2,272 shared cells [AM3D].

- **Under the primary judge the rule never lost**: c = 0 in all six reader-by-arm cells.
- **On the retrieved arm nothing separated**: OLMo-2 4 against 0 (p = 0.125), Qwen3.5-9B 3
  against 0 (p = 0.25). The anchor itself showed only 1 against 0 on these questions, against 39
  against 0 on held-out ones, so the development split cannot separate this rule.
- **Under the second judge, losses appeared**: 6 losses on 3 questions, every one a pool whose
  top-4 reply abstained and that Qwen3-8B judged correct. In 4 of the 6 [post hoc] the reply is
  a bare "I don't know" on an answerable question, a judge error by the pilot's validation
  standard; the other 2 are hedges that also contain the gold answer, and are ambiguous [AM3D,
  "(b)"].

### 5.4 Held-out: H1 of `am3-nonabstain-generality-v1` [confirmatory]

The registration ran OLMo-2 and Qwen3.5-9B on AM1's 347 held-out questions (71 requests per
pool), with the exact McNemar test per reader and Holm's correction across the two. A
directional reading stands only if a blind hand check of every judge-discordant cell gives the
same reading [AM3G-REG section 7.1].

**Table 5. Nonabstain-BM25 against BM25 top 4, 347 held-out questions, retrieved arm,
Qwen3-32B judge** [confirmatory for OLMo-2 and Qwen3.5-9B; the anchor row replays
`am1-keepset-search-v1`] [AM3G; KS].

| Reader | BM25 top 4 | nonabstain-BM25 | b (gained) | c (lost) | Difference [95% bootstrap] | p (Holm) | Hand check (b, c) |
|---|---:|---:|---:|---:|---|---:|---|
| OLMo-2-1124-7B-Instruct | 0.329 | 0.429 | 35 | 0 | +0.101 [+0.069, +0.133] | 1.2e-10 | 35, 0: confirmed |
| Qwen3.5-9B | 0.464 | 0.553 | 31 | 0 | +0.089 [+0.061, +0.121] | 9.3e-10 | 31, 0: confirmed |
| Qwen3-8B (anchor) | 0.458 | 0.571 | 39 | 0 | +0.112 [+0.081, +0.147] | 3.6e-12 (unadjusted, KS) | none |

- **NONABSTAIN_HELPS for both new readers [confirmatory].** With the anchor, the gain on
  answerable questions holds for all three readers tried, from two model families. For
  Qwen3.5-9B the scope is vLLM's default mode and this run's batch schedule.
- **Checks.** Blind agent labels agree with the judge on 274 of 278 items (κ 0.967); the two
  held-out disagreements are in distractor pairs and would be hidden gains. The anchor replayed
  job 1458 token for token on 49,274 of 49,274 requests, and its labels equal AM1's tables
  [AM3G].
- **Second judge [descriptive].** Gains shrink and some losses appear: OLMo-2 32 against 12,
  Qwen3.5-9B 25 against 6, Qwen3-8B 33 against 7. Every cell stays positive.
- **Gold arm [descriptive].** OLMo-2 37 against 0, Qwen3.5-9B 19 against 0, Qwen3-8B 31
  against 0.
- **Against all 8 [descriptive].** OLMo-2 0.429 against 0.352 (44 : 17, p = 0.0007); Qwen3-8B
  0.571 against 0.524 (33 : 17, p = 0.033); Qwen3.5-9B 0.553 against 0.524 (26 : 16, p = 0.16).
  For Qwen3.5-9B the rule is not shown to beat all 8.

### 5.5 Against a Self-Route-style fallback [post hoc; licenses nothing]

Self-Route (2024) escalates to the full context when the model says it cannot answer. Its
analogue here keeps BM25 top 4 unless that reply abstains, and all 8 otherwise. The audit
compared it with the rule on the committed records of `am3-nonabstain-generality-v1`,
retrieved arm, primary judge [AUDIT, "Synthesis recomputation"].

- **The fallback recovers 43-77% of the rule's gain.** It beats BM25 top 4 by 23 to 0
  (Qwen3-8B), 15 to 0 (OLMo-2) and 24 to 0 (Qwen3.5-9B), against the rule's 39, 35 and 31
  (D131 and [AUDIT] give 78% as the upper end; the audit's own counts give 24/31 = 77.4%).
- **The overlapping-subset search adds something for two readers.** The rule beats the fallback
  18:2 (Qwen3-8B, exact p 4e-4) and 25:5 (OLMo-2, 3e-4); for Qwen3.5-9B it is 10:3 (0.09).
- **The fallback is safer on unanswerable questions.** On the 30 abstention questions the
  fallback against the rule is 4:0, 8:1 and 1:0.

## 6. The cost

### 6.1 What the rule costs on unanswerable questions (H2) [descriptive; judge-qualified]

On an unanswerable question "I don't know" is the right answer, and the rule's switch away from
an abstaining top 4 trades it for an answer. H2 measured this on LongMemEval-S's 30 abstention
questions, never used before, judged with LongMemEval's abstention prompt. The cost count b2 is
the number of questions where BM25 top 4 was judged correct and the rule's choice wrong
[AM3G-REG section 6.3].

H2 was registered as a description, not a test: with 30 questions, Holm across three readers
and c2 = 0, the exact test rejects at its first step only when b2 is 7 or more, and its power
reaches 0.8 only at a cost rate of about 0.3 or more [AM3G-REG section 7.2].

**Table 6. The rule on the 30 abstention questions, retrieved arm, Qwen3-32B with the
abstention prompt** [descriptive; judge-qualified] [AM3G].

| Reader | BM25 top 4 correct | Rule correct | Cost b2 | c2 | Cost rate [exact 95%] | Hand (b2, c2) |
|---|---:|---:|---:|---:|---|---|
| Qwen3-8B | 30 | 25 | 5 | 0 | 0.167 [0.056, 0.347] | 5, 0 |
| OLMo-2 | 25 | 17 | 8 | 0 | 0.267 [0.123, 0.459] | 8, 0 |
| Qwen3.5-9B | 29 | 28 | 1 | 0 | 0.033 [0.001, 0.172] | 0, 0 |

**Why judge-qualified.** The registered check G-J2 failed: the abstention judge rejected 26 of
30 decoy answers against a bar of 29. It accepted plain answers as "identified as unanswerable"
on four questions. That failure can only hide costs, so b2 could be too low. The judge called
the rule's switched reply correct on only 0-2 pools per reader, and the hand labels, which agree
on every pool they cover, found no hidden cost [AM3G].

**Two corrections from the hand labels [descriptive].** Qwen3.5-9B's one judged cost is a
refusal the four patterns do not catch, so its hand count is 0. Qwen3-8B's two H2 accuracies are
each 1/30 too high; neither b2 nor c2 changes [AM3G].

**Related populations.** 27 of the 30 abstention questions share memories with an answerable
twin, and 22 twins are among the 347 held-out questions of H1 [AM3G].

### 6.2 Net effect at LongMemEval-S's mix [descriptive; judge-qualified]

LongMemEval-S has 470 answerable and 30 unanswerable questions. With g the net gain per
answerable question, (b - c)/347, and l the net loss per unanswerable one, (b2 - c2)/30, the
net rate at that mix is 0.94 g - 0.06 l, and the rule is ahead while the unanswerable share is
below g/(g + l) [AM3G-REG section 6.4].

**Table 7. Net effect and break-even share, Qwen3-32B judge** [AM3G].

| Reader | Gain per answerable | Loss per unanswerable | Net rate at 470:30 [95%] | Break-even unanswerable share [95%] |
|---|---:|---:|---|---|
| Qwen3-8B | +0.112 | 0.167 | +0.096 [+0.065, +0.129] | 0.40 [0.25, 0.75] |
| OLMo-2 | +0.101 | 0.267 | +0.079 [+0.048, +0.111] | 0.27 [0.17, 0.47] |
| Qwen3.5-9B | +0.089 | 0.033 | +0.082 [+0.055, +0.112] | 0.73 [0.44, 1.00] |

These rates treat the 347 held-out questions as representative of LongMemEval-S's answerable
questions, which holds only approximately (they exclude assistant-turn and development
questions). On the unanswerable questions, all 8 does better than the rule for every reader
[AM3G].

### 6.3 Read cost and read caps (AM4)

The rule calls the reader until a 4-subset's reply does not abstain.

- **Answerable questions [descriptive].** For Qwen3-8B over the 347 held-out questions, the
  median is 1 read, the mean 11.24 and the 90th percentile 70; 231 questions stop at one read and
  288 within 8. The 45 pools where every 4-subset abstains read all 70, which is 3,150 of the
  3,901 reads [KS]. Over the three readers the mean is 11-14 with a median of 1 [AM3G].
- **Unanswerable questions [descriptive].** The median is 70 reads and the mean 43-59: 90-97% of
  their 4-subset replies abstain, so the rule reads them all before falling back to BM25 top 4
  [AM3G].
- **Read caps (AM4) [exploratory; post hoc; licenses nothing; costs and net rates
  judge-qualified].** A cap K reads at most the first K 4-subsets in BM25 order and otherwise
  keeps BM25 top 4. AM4 recomputed the registered run's features on a CPU for K = 1, 2, 4, 8,
  16, 26 and 70, after the registered results were known, and selects no K [AM4]. By K = 8 the
  capped rule keeps 77-84% of the uncapped gains (31 of 39, 27 of 35 and 26 of 31), with c = 0,
  at a mean of 2.7-3.1 reads on answerable questions. On unanswerable questions it reads about K
  subsets, and b2 is 3, 3 and 0 at K = 8. The net rate at the 470:30 mix rises steeply up to
  K = 8 (+0.067 to +0.078) and moves by at most +0.022 after that.
- **Calls are not equal in cost.** A 4-memory call is shorter than an 8-memory one, and token
  cost was not modelled [AM1B, caveat 6; AM1D].

### 6.4 Cost when the evidence is absent (AM5; `am5-ablated-cost-v2`)

H2's cost rests on 30 edited questions and a judge that failed its check, so the next studies
built pools on which "I don't know" is right by construction (D120). For each question, every
haystack session that LongMemEval marks as evidence is removed, and a BM25 top-8 pool is built
from the rest. An abstaining reply counts as correct; the cost is a switch to a reply the judge
rejects; the gain is the rule's gain on the same question's original pool [AM5; AM5R-REG
section 6].

- **Development (AM5) [exploratory].** On the 63 development questions none of LongMemEval's 126
  `has_answer` turns survives the removal. Costs were 0, 5 and 3 at K = 8 and 1, 9 and 3 at
  K = 70 (Qwen3-8B, OLMo-2, Qwen3.5-9B), with hand labels equal to the judge's in every cell.
  The development gains are far below the held-out ones, so AM5 gives no cost-benefit estimate
  [DEC D121; AM5].
- **A voided first freeze.** `am5-ablated-cost-v1` (ledger row 26) was frozen after a merge had
  changed a pinned file, and a shell pipe hid the failing gate test. It could never open its
  gate; no GPU job ran and no held-out output exists. The same design was re-frozen as
  `am5-ablated-cost-v2` (row 27) [DEC D123].
- **The registered test.** Per reader at K = 8, the exact McNemar test on the per-question cost
  and gain indicators over the 347 held-out questions, with Holm across the three readers; a
  directional reading stands only if the blind hand check agrees [AM5R-REG section 7.1].

**Table 8. Cost with the evidence removed against gain with it, K = 8, 347 held-out questions,
Qwen3-32B judge** [confirmatory; the break-even share is descriptive] [AM5R].

| Reader | Cost / gain | Cost minus gain [exact 95%] | p (Holm) | Reading | Hand-based cost / gain | Break-even share [95%] |
|---|---|---|---:|---|---|---|
| Qwen3-8B | 6 / 31 | -0.072 [-0.093, -0.038] | 1.2e-4 | COST_BELOW_GAIN | 6 / 31 | 0.84 [0.71, 0.95] |
| OLMo-2 | 22 / 27 | -0.014 [-0.055, +0.028] | 0.568 | NOT_SEPARATED | 20 / 27 | 0.55 [0.41, 0.69] |
| Qwen3.5-9B | 6 / 26 | -0.058 [-0.079, -0.025] | 1.1e-3 | COST_BELOW_GAIN | 6 / 26 | 0.81 [0.67, 0.94] |

- **What is licensed**, for the two Qwen readers in this scope: capped at 8 reads, the rule
  loses fewer correct answers when a question's evidence is removed than it gains when it is
  present (1.7% against 8.9% for Qwen3-8B, 1.7% against 7.5% for Qwen3.5-9B), so with equal
  weights it raises accuracy whenever at most half of such questions lack their evidence
  [AM5R-REG section 7.1]. The break-even shares in Table 8 are registered descriptions, not part
  of the licence. For OLMo-2 nothing directional is licensed, and NOT_SEPARATED is not evidence
  that cost equals gain [AM5R].
- **Caveats (D126).** The gain side was known before the registration, and K = 8 was chosen
  after AM4 had looked at these questions; only the cost side is new. Qwen3.5-9B is
  NOT_SEPARATED for the uncapped rule (K = 70: 16 / 31, Holm p 0.063) [descriptive]. Leakage
  favours COST_BELOW_GAIN: by a crude string match 27 of the 347 ablated pools hold a memory
  containing the reference answer, though no judged-correct switch at K = 8 is in such a pool
  [descriptive]. A path-guard test failed in the registered run ("1 failed, 230 passed") because
  of where the checkout lay; from a fresh clone elsewhere all 231 tests pass, and the outputs are
  unchanged. Qwen3-8B's gains rest on the judge alone [AM5R].
- **Checks [confirmatory].** The replay control passed, and so did the judge's validation. The
  hand labels agree with the judge on 186 of 195 items (κ 0.72) and confirm all 8 switched
  replies the judge called correct [AM5R].

## 7. What these results do not show

This section collects the "does not decide" and "does not license" statements of the four
registrations and their results [AM1-REG section 2; AM1, "What it does not license"; KS-REG
section 3; KS, "What it does not license"; AM3G-REG section 3; AM3G, "What it does not
license"; AM5R-REG section 3; AM5R, "What it does not license"] and the audit's list of claims
not to make [AUDIT].

**Novelty.** Not claimed as new: that leave-one-out does worse than Shapley; that the top k by
credit is not the best k-subset; that search beats credit in general; abstention-gated selection
or its cost; that the reader's token confidence is anti-informative (D131). Not claimed at all:
that memory interactions defeat per-memory credit (section 3).

**Scope.**

- One dataset: LongMemEval-S (cleaned), its 347 held-out answerable questions, and two kinds of
  unanswerable question: the 30 edited abstention questions and the held-out questions with
  their evidence removed. Questions about things never discussed were not tested.
- One prompt, with an explicit instruction to say "I don't know", on which the abstention rate
  depends [AM1D, caveat 1; AM3D], and abstention patterns written for Qwen3-8B's development
  replies.
- One retriever (BM25, standing in for MiniLM), one memory unit (user turns of at most 1,500
  characters), one pool size (8) and one budget (4). The gold arm and the other budgets are
  descriptive.
- Three readers from two families, one size each, and credit tables for one 8B reader.
  Set-selection gains shrink with reader scale in other work (What Survives Into Context, 2026)
  [AUDIT]. Qwen3.5-9B's results hold for its default-mode engine and these runs' batch
  schedules.

**Judges.** Every accuracy is the Qwen3-32B judge's label; its hand checks are an agent's labels,
not a human's, and AM1's κ interval reaches below the registered bar. Nothing is claimed under
the second judge. H2 rests on an abstention judge that failed G-J2, so its costs may be too low.

**Credit and search.**

- The registrations do not rank credit rules and say nothing about exact Shapley's adequacy.
  The split by full-pool correctness is post hoc.
- H-A's search reads labels, so it is not deployable, and on noiseless replays it says nothing
  about the winner's curse a noisy utility would bring. It is also easy here: on average 37.5%
  of the 70 4-subsets are optimal [post hoc].
- Only per-query keep sets were scored; nothing is shown about what a shared memory store
  should retain.
- Credit's remaining case, one ranking for every budget or credits that transfer across
  questions, was not tested, and nothing is shown about training a memory learner on these
  credits.
- AM2 does not show a content effect of non-gold memories, and AM6 does not give a deployable
  internal signal.

**The rule.**

- It is not safe on unanswerable questions: by the judge's count it turned correct abstentions
  into wrong answers on 3-27% of the edited ones (0-27% by hand) and, with the evidence removed,
  on 1.7-6.3% of the held-out questions at K = 8.
- Its cost is shown below its gain only as section 6.4 qualifies it.
- It is not shown to beat keeping all 8 (descriptive; for Qwen3.5-9B it fails), nor the
  Self-Route-style fallback net of cost (post hoc).
- AM4 selects no cap. The natural-mix rates, break-even shares, gold arm, second judge and
  question types are descriptions. Token cost per call was not modelled.

**Mechanism and process.** Why the tables are non-monotone is not separated: reader errors,
distraction and order effects are confounded, and a content-free reorder alone changes 17% of
answers. Why a reader answers without the evidence is not shown. The held-out questions served
four registrations, AM1's published figures fixed H-B's sign before `am1-keepset-search-v1` ran
(D116), and the rule was chosen on development data.

**What could be new.** D131 names two experiments that could produce something new: a stronger
reader on fresh questions with the full-pool-correct split registered as primary, which would
test whether the gap is a weak-reader artifact, and the retention decision on a shared memory
store, scored on held-out questions against the exact optimum, which the audit calls the one
experiment that could give a new result rather than a better measurement of a known one
[AUDIT]. Neither has started.

## 8. Related work

This section cites only work that the program's own records cite: the AM1 registration's
section 1, the 2026-10-14 question sweep [SWEEP] and the 2026-10-16 novelty audit, which ran a
prior-art auditor and an adversarial refuter per finding [AUDIT]. Descriptions follow the audit
wherever it describes a work; the details tagged only [SWEEP] or [AM1-REG] (CMP's call count,
Nematov et al.'s query count, Hindsight Memory-PRM's rule, UpliftMem, Re-feeding Is Not
Replaying, AT2 and Preference Is Not Intervention) follow those
records and were not checked by the audit. This note's author did not re-read the papers.
Identifiers and dates are under Sources.

**Result 1.**

- **Leave-one-out against Shapley is known.** Leave-one-out fails under duplicates in data
  valuation (Ghorbani and Zou, 2019). Nematov et al. (2025) compare credit estimators against
  an exhaustive 2^10 Shapley reference with a log-likelihood utility [AUDIT], on 100 RAG queries
  with 10 documents each [AM1-REG section 1]. MaxShapley (2025) computes exact Shapley
  over 2^6 sources with an LLM-judge utility that sees the reference answer and finds that
  leave-one-out under-credits redundancy. TracLLM (2025) finds leave-one-out sub-optimal when
  texts jointly cause the output. In the memory setting, MeClear (2026), a direct directional
  prior, finds permutation Shapley-16 ahead of leave-one-out by +25.5 pp [+20.9, +29.8] on
  LoCoMo memory faults [AUDIT].
- **The top k by credit need not be the best set.** Wang et al. (2024) show this for all
  semivalues including leave-one-out and Banzhaf, show that credit-based subset selection can be
  no better than random, and show that Shapley top-k is optimal for monotone-transformed modular
  utilities; Chi et al. (2025) treat semivalue top-k as a myopic approximation of the exact
  optimum. The point estimates in Table 2 fall in the order exact Banzhaf, exact Shapley, the
  sampled estimators, leave-one-out [descriptive; no ranking is licensed], which is the order
  data-valuation work predicts (Beta Shapley; Data Banzhaf; Wang et al. 2024, Theorem 6) [AUDIT].
- **Memory learners.** The rules tested are those of Hindsight Memory-PRM (one-shot deletion [AM1-REG section 1]),
  MeClear (permutation Shapley-16) and CMP (SNIPW over random exposures). CMP shows that
  memories act jointly, estimating exposure effects from 80,187 calls of a closed model
  [AM1-REG section 1], but never scores them against an exact optimum [AUDIT]. DRSR (2026),
  another direct directional prior, finds that singleton deletion scores do not determine
  set-deletion risk; Relevance Is Not Sufficiency (2026) and MemPursuit (2026) already show
  set-level selection on memory benchmarks, the first on LongMemEval-S; ContextCite (2024)
  prunes context to the top k by attribution, without exact-optimum regret; ProxySPEX and SPEX
  (2025) model sparse interactions under context masking, which bears on the interaction share
  (H1) [AUDIT]. UpliftMem (2026) learns set-level uplift from sampled probes [SWEEP entry 3].
- **What the audit found no direct prior for:** keep-set regret, in correct answers, against the
  exact keep-4 optimum, from 694 exhaustive judged tables on an agent-memory benchmark, with the
  first exact-truth scores for SNIPW-64 and permutation Shapley-16. MaxShapley scores rank
  agreement with exact Shapley and Nematov et al. removal-set precision; neither scores keep-set
  regret. The audit states this as no direct prior art found through 2026-10-16 under its
  coverage, which is not evidence of novelty beyond it [AUDIT].

**Result 2.** Search with a label-seeing utility over candidate sets is the wrapper-versus-filter
point of Kohavi and John (1997). It is routine in DSPy (2023), and Schoch and Ji (2025) report
that valuation-inspired selection of in-context examples loses to random sampling [AUDIT].

**Result 3.**

- **The closest direct prior.** Wang, Ma and Kumar, "When Should LLMs Admit Ignorance?" (2025),
  slide a window over BM25-ranked pages: if a window yields the answer the model answers and
  stops, otherwise it says "Answer not found" and moves on. The audit rates the rule tested here
  the same stop rule, with overlapping 4-subsets in place of disjoint windows [AUDIT].
- **The other direct priors.** ChunkRank (2026) finds that no content ranker beats the first
  non-empty answer: abstention, not ranking, does the work. Self-Route (2024) escalates to the
  full context when the model says it cannot answer (section 5.5). RobustRAG (2024) drops
  isolated groups whose reply says "I don't know" [AUDIT].
- **The confidence half is expected.** A generic "I don't know" is a known high-likelihood reply
  (Khayrallah and Sedoc, 2020), offering an "Unknown" option inflates abstention (LLM Abstention
  Can Be a Prompt Artifact, 2025), and ChunkRank finds that confidence works once abstentions are
  removed [AUDIT].
- **What the audit found no direct prior for:** this overlapping-subset variant of a known
  rule, with size-matched cost-against-gain accounting, in a memory keep-set setting; Mondal et
  al. (2026) show why size matching matters for deletion-built insufficient-evidence sets
  [AUDIT].

**Replay, internal signals and readers.** "Re-feeding Is Not Replaying" (2026) found engine
replay noise in token-level credit and none with `VLLM_BATCH_INVARIANT=1` on vLLM 0.22.1 and an
A100 [SWEEP entry 5]; section 2.3 agrees for eager mode on vLLM 0.31.0, and GDN attention has no
batch-invariant mode there [SWEEP, check O3]. AM6's cross-fitted heads follow AT2 (2025), which
learns attention-head weights for attribution [AM1-REG section 1]. Whether per-memory effects
transfer across readers is occupied by "Preference Is Not Intervention" (2026): over nine
readers, effect signs disagree in 33% of jointly affected cells [SWEEP, "Not ranked"]. Section 5.4
concerns one keep rule's accuracy, not per-memory effects.

**What the records cover.** The sweep's queries through 2026-10-14 found nothing that occupied
AM1 [SWEEP, check O9]. The audit ran about 30 orx queries and 12 web searches for Finding A
(Results 1 and 2) and about 45 orx queries and 6 web searches for Finding B (Result 3); OpenAlex
returned HTTP 429 to every agent, and Reddit, X and Chinese-language sources were not searched.
It rates Finding A INCREMENTAL and Finding B INCREMENTAL with the rule itself KNOWN, both of LOW
importance as they stand [AUDIT; DEC D131]. This note makes no novelty claim for Results 2 and 3,
and for Result 1 claims only the measurement above.

## 9. Reproducibility

**Table 9. Studies, registrations, evidence and GPU use.** GPU-h are physical GPU-hours as each
record states them; CPU-only studies used none. The fill commit is the ledger row's
`git_head_at_freeze`; the freeze commit adds only the row.

| Study | Ledger row | Freeze commit (fill) | Registration SHA-256 | Evidence | Jobs | Physical GPU-h (cap) |
|---|---:|---|---|---|---|---|
| AM1 Step 0 | | | | `program/evidence/2026-10-15/am1-step0/` | | 0.20 (D107) |
| AM1 development pilot | | | | `program/evidence/2026-10-15/am1-dev-pilot/README.md` | 1405, 1411, 1432, 1435, 1439, 1441 | 1.4862 (2.0) |
| `am1-memory-credit-v1` | 23 | `9ad36b10` (`c50017af`) | `51d0abb1...` | `program/evidence/2026-10-16/am1-confirmatory/RESULTS.md` | build 1454, job 1458 | 1.5444 (3.1) |
| AM1b | | | | `program/evidence/2026-10-15/am1b-cost-curve/README.md` | CPU | 0 |
| AM1d | | | | `program/evidence/2026-10-15/am1d-label-free/README.md` | CPU | 0 |
| `am1-keepset-search-v1` | 24 | `72d50162` (`4b89e8eb`) | `37256cc8...` | `program/evidence/2026-10-16/am1-keepset-search/RESULTS.md` | CPU | 0 |
| AM3 reader replication | | | | `program/evidence/2026-10-16/am3-reader-replication/README.md` | 1462, 1466 | 0.2017 (2.0) |
| `am3-nonabstain-generality-v1`, development dry run | | | | `program/evidence/2026-10-16/am3-nonabstain-generality-dev-dryrun/` | 1467, 1471 | 0.1898 (0.5) |
| `am3-nonabstain-generality-v1` | 25 | `6384f294` (`78e9c00f`) | `ff8670f2...` | `program/evidence/2026-10-15/am3-nonabstain-generality-v1/RESULTS.md` | build 1475, jobs 1480, 1482 | 0.6722 (2.08) |
| AM4 read caps | | | | `program/evidence/2026-10-16/am4-read-caps/README.md` | CPU | 0 |
| AM5 | | | | `program/evidence/2026-10-16/am5-evidence-ablated/README.md` | 1483, 1487 | 0.1297 (0.5) |
| `am5-ablated-cost-v1` (void, D123) | 26 | `ea4a7206` (`f46242ee`) | `78b4e8ba...` | none: no job ran | none | 0 |
| `am5-ablated-cost`, development dry run | | | | `program/evidence/2026-10-16/am5-ablated-cost-dev-dryrun/README.md` | 1502, 1507 | 0.1325 (0.3) |
| `am5-ablated-cost-v2` | 27 | `6578e0f0` (`83ba8f8d`) | `1f27e7d6...` | `program/evidence/2026-10-16/am5-ablated-cost-v2/RESULTS.md` | build 1548, job 1552 | 0.3461 (1.42) |

The line used about 4.9 physical GPU-h in all (the sum of the last column, with Step 0's figure
rounded in D107), on H100s of one node.

- **Registrations:** `program/preregistrations/am1-memory-credit-v1.md`,
  `am1-keepset-search-v1.md`, `am3-nonabstain-generality-v1.md`, `am5-ablated-cost-v1.md` (void)
  and `am5-ablated-cost-v2.md`, frozen in rows 23-27 of `program/preregistrations/ledger.jsonl`.
- **Committed outputs are text-free:** tables as 256-bit hex strings, credits, regrets, masks,
  labels, digests and counts, so AM1's tables can score any credit estimator without the texts
  [AUDIT]. Reply texts, questions, memory texts, features and hand-label texts stay on the host,
  so the registered analyses cannot be rerun from the public repository alone; the verifiers
  reran them on the host from exports or clones of the freeze commits.
- **Reruns from the repository alone, at `1cf31346`, on a Mac.** AM1b's script [AM1B,
  "Reproduce"] gave `results.json`, `per-table.json.gz` and `tables.md` byte-identical to the
  committed copies (34 s of CPU). AM4's second route, which recomputes the judge-based figures
  from the committed records of `am3-nonabstain-generality-v1` without the features [AM4],
  compared 462 figures with no difference. The audit's two recomputations (quoted in sections 3,
  4.2 and 5.5) used scripts it did not commit. The counts of its split table and of its fallback
  table were recomputed independently from AM1's `analysis/tables.json.gz` and the committed
  `per-table.json.gz` of `am3-nonabstain-generality-v1`, and matched (`numbers.md` N185, N187
  and N191). The optimal-set rates, the auditor's bootstrap interval and the optimal-set density
  are quoted from the audit; no rerun of them is recorded.

  ```bash
  uv run --locked --offline python scripts/memcredit_cost_curve.py \
      --tables program/evidence/2026-10-15/am1-dev-pilot/analysis/tables.json.gz \
      --h2 program/evidence/2026-10-15/am1-dev-pilot/analysis/h2.json \
      --output-dir SCRATCH_DIR
  uv run --locked --offline python scripts/memcredit_am4.py crosscheck \
      --results program/evidence/2026-10-16/am4-read-caps/results.json
  ```

- **Every number in this note** is listed in `paper/memory-keepset-note/numbers.md` with its
  source file and the source text it was checked against.

## Authorship and process

AI agents ran the studies above under the program's frozen registrations and decisions, and ran
the novelty audit. The hand labels were made blind by Claude agents (in
`am3-nonabstain-generality-v1`, AM5 and `am5-ablated-cost-v2`, `claude-opus-5-5`). An AI agent
wrote this note from the committed evidence only, without host access, and checked its numbers
against their sources (`numbers.md`). No human has reviewed this note or labelled any item.
Kevin Liu owns the program and every outward action, including any publication (D101).

## Sources

Program evidence (paths from the repository root, at `1cf31346`):

- [AM1-REG] `program/preregistrations/am1-memory-credit-v1.md` (frozen, ledger row 23).
- [KS-REG] `program/preregistrations/am1-keepset-search-v1.md` (frozen, ledger row 24).
- [AM3G-REG] `program/preregistrations/am3-nonabstain-generality-v1.md` (frozen, ledger row
  25).
- [AM5R-REG] `program/preregistrations/am5-ablated-cost-v2.md` (frozen, ledger row 27).
- [PILOT] `program/evidence/2026-10-15/am1-dev-pilot/README.md` (exploratory).
- [AM1] `program/evidence/2026-10-16/am1-confirmatory/RESULTS.md` (confirmatory).
- [AM1B] `program/evidence/2026-10-15/am1b-cost-curve/README.md` (exploratory).
- [AM1D] `program/evidence/2026-10-15/am1d-label-free/README.md` (exploratory).
- [KS] `program/evidence/2026-10-16/am1-keepset-search/RESULTS.md` (confirmatory).
- [AM3D] `program/evidence/2026-10-16/am3-reader-replication/README.md` (exploratory).
- [AM3G] `program/evidence/2026-10-15/am3-nonabstain-generality-v1/RESULTS.md` (confirmatory
  and descriptive).
- [AM4] `program/evidence/2026-10-16/am4-read-caps/README.md` (exploratory, post hoc).
- [AM5] `program/evidence/2026-10-16/am5-evidence-ablated/README.md` (exploratory).
- [AM5R] `program/evidence/2026-10-16/am5-ablated-cost-v2/RESULTS.md` (confirmatory).
- [AUDIT] `program/evidence/2026-10-16/novelty-audit/AUDIT.md`, the novelty audit behind D131.
- [SWEEP] `program/evidence/2026-10-14/question-sweep-memory-gpu/dossier.md`, the question sweep
  that ranked AM1 (entries 3, 5 and 6; owner checks O3 and O9; "Not ranked").
- [DEC] decisions D9, D101, D103, D104, D107, D111-D121, D123, D126 and D131 in
  `program/decisions.md`.

External sources, as the program's records cite them, with the dates they give:

- LongMemEval-S, cleaned: Hugging Face dataset `xiaowu0162/longmemeval-cleaned` at `98d7416c`
  (MIT); the answer-check and abstention prompts from
  <https://github.com/xiaowu0162/LongMemEval> at `9e0b455f`, `src/evaluation/evaluate_qa.py`.
- vLLM 0.31.0 (`db9527a4`), batch-invariant mode; issue
  <https://github.com/vllm-project/vllm/issues/48613> (no batch-invariant mode for GDN
  attention), as read by the sweep's check O3.
- Memory learners: Hindsight Memory-PRM, 2026-08-30, <https://arxiv.org/abs/2608.29605>;
  MeClear, 2026-09-08, <https://arxiv.org/abs/2609.09115>; CMP, 2026-10-01,
  <https://arxiv.org/abs/2610.02070>; UpliftMem, 2026-09-29, <https://arxiv.org/abs/2609.36805>;
  DRSR, 2026-09-23, <https://arxiv.org/abs/2609.27276>; Relevance Is Not Sufficiency,
  2026-10-07, <https://arxiv.org/abs/2610.09348>; MemPursuit, 2026-10-11,
  <https://arxiv.org/abs/2610.15642>.
- Attribution and data valuation: Nematov et al., 2025-07-06,
  <https://arxiv.org/abs/2507.04480>; MaxShapley, 2025-12-05, <https://arxiv.org/abs/2512.05958>;
  Wang et al., 2024-05-06, <https://arxiv.org/abs/2405.03875>; Chi et al., 2025-02-06,
  <https://arxiv.org/abs/2502.04554>; Ghorbani and Zou, 2019-04,
  <https://arxiv.org/abs/1904.02868>; Data Banzhaf, 2022-05, <https://arxiv.org/abs/2205.15466>;
  Beta Shapley, 2021-10, <https://arxiv.org/abs/2110.14049>; TracLLM, 2025-06,
  <https://arxiv.org/abs/2506.04202>; ContextCite, 2024-09-01, <https://arxiv.org/abs/2409.00729>;
  AT2, 2025-04-18, <https://arxiv.org/abs/2504.13752>; ProxySPEX, 2025-05-23,
  <https://arxiv.org/abs/2505.17495>; SPEX, 2025-02-19, <https://arxiv.org/abs/2502.13870>.
- Subset search: Kohavi and John, 1997, <https://doi.org/10.1016/S0004-3702(97)00043-X>; DSPy,
  2023-10, <https://arxiv.org/abs/2310.03714>; Schoch and Ji, 2025-05,
  <https://aclanthology.org/2025.insights-1.7/>.
- Abstention: Wang, Ma and Kumar, 2025-12-29, <https://arxiv.org/abs/2512.23836>; ChunkRank,
  2026-09-24, <https://arxiv.org/abs/2609.29828>; Self-Route, 2024-07-23,
  <https://arxiv.org/abs/2407.16833>; RobustRAG, 2024-05, <https://arxiv.org/abs/2405.15556>;
  Khayrallah and Sedoc, 2020-10-24, <https://arxiv.org/abs/2010.12786>; LLM Abstention Can Be a
  Prompt Artifact, 2025-07-22, <https://arxiv.org/abs/2507.16199>; Mondal et al., 2026-09-26,
  <https://arxiv.org/abs/2609.32269>.
- Readers and replay: What Survives Into Context, 2026-07-01, <https://arxiv.org/abs/2607.00725>;
  Re-feeding Is Not Replaying, 2026-06, <https://arxiv.org/abs/2606.15621>; Preference Is Not
  Intervention, 2026-08-18, <https://arxiv.org/abs/2608.17781>.
