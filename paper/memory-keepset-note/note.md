# Which memories should a reader keep? Deletion credit, keep-set search and a label-free abstention rule on LongMemEval-S

Internal research note, draft of 2026-10-15. CoTCodec research program, agent-memory line
(decisions D103-D119 in `program/decisions.md`). Program owner: Kevin Liu.

Repository: <https://github.com/Kevin-Liu-01/cotcodec> (public). Every evidence path below
resolves on `main` at `db589d2f`, the base of this note's branch `paper/memory-keepset-note`.
The branch adds only this note, its `README.md` and its number table `numbers.md`.

> **Status: INTERNAL DRAFT. Not published, not for circulation (D101).**
>
> - Publication is an outward action and stays the program owner's call (D101). Nothing here has
>   been posted, submitted or sent.
> - Every claim carries one status label:
>   - **[confirmatory]**: decided by a frozen registration's rule on held-out data;
>   - **[exploratory]**: development data, no decision rule;
>   - **[descriptive]**: reported by a frozen registration (or by its fixed secondary rule) but
>     deciding nothing;
>   - **[judge-qualified]**: rests on a judge that failed its own registered validation check;
>   - **[post hoc]**: computed after the registered outputs were read.
> - **Hand labels are an agent's, not a human's (D9).** Every judge hand check was labelled by a
>   Claude agent, blind to the judge's labels. No human has validated a judge label.
> - **No gauntlet score.** The three registrations were admitted without a gauntlet wave (D111,
>   D115, D118). Blind discrimination and the provider-distinct reviews did not run.
> - **The held-out questions were reused.** Three registrations read the same 347 held-out
>   questions. The second and third disclosed, before they ran, what the earlier ones had
>   published about them.
> - The note quotes no question, answer, reply or memory text. The only reply string it names is
>   the abstention form "I don't know", which the reader's prompt asks for when the memories
>   lack the answer.

## Summary

A memory system that retrieves 8 memories for a question can show the reader all 8 or keep a
subset. We asked how to choose 4 of 8. On LongMemEval-S (cleaned) we ran a reader, Qwen3-8B,
whose outputs replay bit for bit, on all 256 subsets of each pool, and judged every reply with
Qwen3-32B. That gives, for each question, the exact outcome of every keep set, so any rule's
choice can be scored against the best 4-subset.

- **Deletion credit picks the wrong memories to keep [confirmatory].** On 251 held-out
  questions whose table is not constant, keeping the top 4 by leave-one-out credit loses 0.277
  of a correct answer per question against the best 4-subset (99% [0.223, 0.333]). It loses
  0.233 [0.194, 0.273] more than exact Shapley credit on the same tables. The other four
  registered rules (permutation Shapley-16, SNIPW-64, retrieval rank, raw attention) are also
  MISSPECIFIED. Interactions beyond the AND/OR form of the needed memories carry variance
  (+0.156 [0.119, 0.194] on the retrieved pools) [descriptive].
- **With an oracle utility, search over keep sets beats sampled credit [exploratory, then
  confirmatory; the registered verdict is INCONCLUSIVE].** Reading random 4-subsets and keeping
  the best loses less than leave-one-out, SNIPW-64 and MSR-Banzhaf-64 at equal reader calls, and
  less than SNIPW-64, MSR-Banzhaf-64 and permutation Shapley-16 when search reads 26 subsets to
  their 57-83. Those are six of the seven registered comparisons. The seventh, against greedy
  backward elimination at 26 calls each, is not separated (one-sided upper bound +0.0014), so
  the registered verdict is INCONCLUSIVE, not SEARCH_DOMINATES.
- **Without labels, the reader's confidence is anti-informative; its abstention is usable
  [exploratory, then confirmatory, then generalised].** The reader's most confident reply is
  "I don't know", and searching by confidence gets worse with more calls [exploratory]. Keeping
  the best-BM25-ranked 4-subset whose reply does not abstain beats BM25 top 4 for Qwen3-8B
  (+0.112 [0.081, 0.147], 39 questions gained, 0 lost) [confirmatory], and for two more
  readers, OLMo-2-1124-7B-Instruct (+0.101 [0.069, 0.133], 35 against 0) and Qwen3.5-9B
  (+0.089 [0.061, 0.121], 31 against 0), each confirmed by a blind hand check [confirmatory].
- **The rule has a cost [descriptive; judge-qualified].** On LongMemEval-S's 30 unanswerable
  questions it turns a correct abstention into a wrong answer 5, 8 and 1 times for the three
  readers (hand counts 5, 8 and 0). At the dataset's own mix of 470 answerable to 30
  unanswerable questions the net effect stays positive (+0.079 to +0.096). The rule stops paying
  when unanswerable questions exceed 27-73% of the mix, depending on the reader. It reads a
  median of 1 subset on answerable questions and 70 on unanswerable ones.

The scope throughout is one dataset, one prompt that asks for "I don't know", BM25 user-turn
pools of 8, a budget of 4 and the Qwen3-32B judge (section 7).

## 1. The question

Agent memory systems decide which stored memories to show the reader for a question. Several
2026 memory learners train on per-memory causal credit: one-shot deletion (leave-one-out),
permutation Shapley, or exposure-weighted estimates [AM1-REG section 1]. But a keep or evict
decision chooses a set, and if memories act jointly a score per memory need not rank sets well.
The line asked three questions. Is per-memory credit, especially deletion credit, the right tool
for choosing which memories to keep, judged against the exact best keep set (AM1)? If a keep
set's utility can be queried, is search over keep sets cheaper and better than estimating credit
(AM1b, then H-A of `am1-keepset-search-v1`)? And what chooses keep sets without labels, at what
cost (AM1d, H-C, AM3, `am3-nonabstain-generality-v1`)?

The line came from the program's 2026-10-14 question sweep, which ranked AM1 the memory lead and
folded two other candidates into it as placebo arms (AM2) and an internal-signal analysis (AM6)
[SWEEP entries 3, 5 and 6; DEC D103, D104]. Table 1 lists the studies.

**Table 1. The studies of the memory line.**

| Study | Status | Data | Decision |
|---|---|---|---|
| AM1 Step 0 | exploratory | eight demo questions | replay works (D107) |
| AM1 development pilot | exploratory | 63 development questions, 126 tables | design of AM1 (D111) |
| `am1-memory-credit-v1` (AM1) | confirmatory | 347 held-out questions, 694 tables | H2: five rules MISSPECIFIED (D112) |
| AM1b | exploratory | the pilot's tables, CPU only | search beats credit on development (D113) |
| AM1d | exploratory | the pilot's replies, CPU only | abstention is the usable signal (D115) |
| `am1-keepset-search-v1` | confirmatory | AM1's held-out tables and replies, CPU only | H-A INCONCLUSIVE; H-C NONABSTAIN_HELPS (D117) |
| AM3 | exploratory | 63 development questions, three readers | direction holds, not separated (D118) |
| `am3-nonabstain-generality-v1` | confirmatory (H1); descriptive (H2) | 347 held-out + 30 abstention questions | H1 NONABSTAIN_HELPS for both new readers (D119) |

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

The three confirmatory studies followed one process:

- **Freeze.** Hypotheses, decision rules, seeds, caps and the SHA-256 of every code file are
  fixed in a registration, frozen by `scripts/preregister.py freeze` into a hash-chained row of
  `program/preregistrations/ledger.jsonl`, in a commit that adds only that row. The scripts
  refuse held-out inputs until that row exists and every code pin matches.
- **Checks before the freeze.** Fresh reviewers who did not draft the file checked it and its
  code: two rounds for AM1 and `am1-keepset-search-v1`, three for
  `am3-nonabstain-generality-v1`.
- **Checks after the run.** The digest of the blind hand labels was committed before the
  analysis joined them [AM1; AM3G]. A verifier that shared no context with the analyst reran the
  registered analysis from a new `git archive` export of the freeze commit, got byte-identical
  outputs, and reproduced the headline results with its own code [AM1; KS; AM3G,
  "Verification"]. The exploratory studies had a fresh checker of the same kind [AM1B; AM1D;
  AM3D].

Intervals are question-cluster percentile bootstraps, 95% unless stated: 4,000 resamples in AM1
[AM1-REG section 6] and 10,000 in AM1b, AM1d and the two later registrations. Paired accuracy
comparisons use the exact McNemar test, and rates over the 30 abstention questions get exact
Clopper-Pearson intervals.

## 3. Result 1: deletion credit is misspecified for keep and evict decisions (AM1)

**Development pilot [exploratory].** On the 63 development questions, 53 of 89 non-constant
tables were non-monotone: some memory helps on some sets and hurts on others. A non-gold memory
mattered in 58. On the retrieved arm at B = 4, leave-one-out lost 0.214 [0.121, 0.316] and
exact Shapley 0.079; their paired difference was +0.135 [0.051, 0.227] [PILOT]. The sweep's
owner check had warned that under a pure AND leave-one-out keeps the right set, and exact Shapley
does under a pure AND or OR, so regret needs mixed structures, redundancy, a binding budget or
negative interference [SWEEP, check O5]. The pilot showed that the tables are mostly not pure,
and the registration's thresholds were set from its scale [AM1-REG section 15].

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
  per non-constant question and are suboptimal in 55% of tables.
- **The loss is specific to deletion credit [confirmatory].** Leave-one-out loses 0.233
  [0.194, 0.273] more than exact Shapley credit on the same tables. The other rules' paired
  differences (+0.094, +0.050) are secondary descriptions with no decision rule.
- **Not licensed:** any statement about exact Shapley's adequacy (its 99% interval, [0.012,
  0.080], spans both thresholds) or a ranking of the rules. No rule is ADEQUATE, which the
  registration expected to need a true regret below about 0.01 [AM1-REG sections 7 and 9].
- **SNIPW-64's verdict rests on three seeds.** It was the closest call (99% lower bound 0.058).
  Over 3 seeds its regret was 0.094; over 200 seeds on the same tables it is 0.085 [KS], and on
  development 3 seeds gave 0.070 against 0.050 for 20 [AM1B, caveat 2]. No 99% interval at 200
  seeds was computed, so whether SNIPW-64 stays MISSPECIFIED in expectation over its draws is
  not known.

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
over that baseline at each question's gold count is **+0.156 [+0.119, +0.194]** on the
retrieved arm and +0.094 [+0.058, +0.129] on the gold arm. Of the 251 non-constant retrieved
tables, 167 are non-monotone, 57 depend on a single memory, 12 are AND, 8 are OR and 7 are
monotone but mixed; a non-gold memory matters in 182 [AM1]. The gold count understates how many
memories a table depends on.

**Placebo floor for non-gold deletion labels (AM2) [descriptive: a registered secondary rule
with no program decision].** A deletion label says that removing memory i flips judged
correctness. The placebo replaces memory i's text with a length- and rank-matched irrelevant user
turn of the same question at the same slot [AM1-REG section 4]. Over both arms:

| Memory class | Deletion flip rate | Swap flip rate | Deletion minus swap, 95% | Nonzero deletion labels that survive |
|---|---|---|---|---|
| gold | 0.440 [0.399, 0.483] | 0.441 [0.400, 0.483] | -0.0008 [-0.0097, +0.0082] | 0.641 [0.586, 0.697] |
| non-gold | 0.072 [0.059, 0.085] | 0.062 [0.051, 0.074] | **+0.0099 [+0.0026, +0.0170]** | 0.128 [0.086, 0.175] |

The registered reading is ABOVE THE SWAP FLOOR for non-gold labels, since the lower bound,
+0.0026, is above 0. The gold arm drives it: the non-gold difference is +0.0204 [+0.0090,
+0.0324] there and +0.0002 [-0.0094, +0.0103] on the retrieved arm. ABOVE is not evidence of a
content effect, because deletion is a larger edit than a matched swap: it also shortens the
prompt and moves the later memories [AM1-REG section 7]. Only 12.8% of nonzero non-gold deletion
labels survive the placebo control (both swaps reproduce the label and no reorder flips the
pool), against 64.1% of gold labels, and a content-free reorder of the full pool changes judged
correctness in 17.1% [14.6%, 19.8%] of reorders [AM1]. The pilot had read NOT ABOVE, +0.0006
[-0.013, 0.013] [PILOT, "AM2"]; on the retrieved arm alone, the deployable one, neither data set
shows an excess (development -0.017 [-0.040, 0.001]).

**Internal signals (AM6) [descriptive].** Attention heads chosen by cross-fitting against exact
Shapley predict which memories are necessary at AUROC 0.890 [0.865, 0.914], 0.060 above the best
cheap baseline (overlap with the reply, 0.830); raw attention (0.832) ties it. The heads need
exact tables of other questions to select, so they are not a deployable signal [AM1].

## 4. Result 2: with an oracle utility, search over keep sets beats sampled credit

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
8 calls, 0.126 at 9, 0.067 at 16, 0.036 at 26, 0.020 at 38, 0.003 at 64 and 0 at 70 [KS].

Read exactly:

- **The verdict is INCONCLUSIVE.** Six of the seven comparisons are SEARCH_BETTER; A7 is
  NOT_SEPARATED. SEARCH_DOMINATES needed all seven.
- **Of the six, three are at equal calls** (A1, A2, A4) and three give search fewer calls (26
  against the rule's 56.7-83.3: A3, A5, A6). Every comparison against a credit rule is
  SEARCH_BETTER.
- **The comparison not separated is search against search.** Greedy backward elimination is
  itself a search over keep sets, not a credit rule. Its two-sided 95% interval excludes 0, but
  the registered one-sided upper bound, +0.0014, does not. Under 200 other bootstrap seeds the
  verifier found that bound between +0.0005 and +0.0032. Greedy loses a whole answer on 17 of
  251 tables, so the differences are skewed [KS].
- **What is licensed:** given an oracle utility, direct search over random 4-subsets loses less
  than the sampled credit rules, in expectation over held-out questions with a non-constant
  retrieved table: against leave-one-out at 9 calls, against SNIPW-64 and MSR-Banzhaf-64 at
  equal calls, and against SNIPW-64, MSR-Banzhaf-64 and permutation Shapley-16 even when search
  reads 26 subsets to their 57-83 [KS, "What the result licenses"].
- **What is not licensed:** SEARCH_DOMINATES, or any statement about greedy backward
  elimination against direct search in either direction.
- **The error rates are nominal.** In a size simulation from the development differences, a
  false RULE_BEATS_SEARCH came out at 0.0385 (nominal 0.029), and a false SEARCH_DOMINATES
  reached 0.032-0.0395 in a skew stress case. Every measured verdict error was below 0.05
  [KS-REG section 9].
- **The gold arm [descriptive]** shows the same pattern: A1-A6 SEARCH_BETTER and A7 not
  separated.

H-A reads the judged utility, which needs the reference answer. It measures how well a rule
attributes credit within one question when labels are available; it is not a keep policy that
runs without labels. The tables are deterministic replays, so a search that keeps the best of
noisy utilities would face a winner's curse that this design cannot see [KS-REG section 3].

## 5. Result 3: the reader's abstention is a usable label-free signal; its confidence is not

### 5.1 Development: label-free search (AM1d) [exploratory]

AM1d replaced the judged utility with scores computed from the reader's own replies under each
subset, on the pilot's 63 development questions, and searched over 4-subsets with them. The
four abstention patterns were committed before any reply was read [AM1D].

- **The reader's confidence is anti-informative.** On the retrieved arm, 2,405 of 4,410 4-subset
  replies (54.5%) abstain, and 2 of those are judged correct. The median mean token log-prob is
  -5.3e-6 for abstaining replies, -0.0037 for non-abstaining replies judged correct and -0.0131
  for those judged wrong, so "I don't know" is the most confident reply [post hoc diagnostic].
  Within a table, mean log-prob ranks subsets below chance (mean AUROC 0.326; the non-abstention
  flag, 0.854).
- **More search makes confidence worse.** Keeping the most confident reply is right on 0.208 of
  the 38 non-constant retrieved tables at 8 calls and 0.105 at 70; BM25 top 4 is right on 0.842.
  A majority vote over subsets fails the same way (0.318 at 8 calls, 0.237 at 70).
- **The only usable signal was abstention.** `nonabstain@70`, the best-BM25-ranked 4-subset
  whose reply does not abstain, scored 0.868 against 0.842 for BM25 top 4: +0.026 [+0.000,
  +0.079], one table of 38. Chosen in sample among 40 rules; picking the utility on half the
  questions and scoring it on the other half gives +0.025 at 70 calls.
- **A development lead that reversed.** BM25 top 4 was ahead of all 8 by +0.105 [+0.026,
  +0.211] on the non-constant retrieved tables, 4 tables against 0 (exact p = 0.125). On held-out
  data it reversed (section 5.2).

AM1d's own caveat: the prompt tells the reader to say "I don't know", so that string is its most
probable output. A different prompt, or a reader that does not abstain, could make confidence
behave differently; that was not tested [AM1D, caveat 1].

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
- **Why it works.** 13,598 of 24,290 retrieved 4-subset replies abstain (56%). BM25 top 4's own
  reply abstains on 116 questions; on 71 of them another 4-subset answers, and switching gained
  39 and lost none. In 45 pools every 4-subset abstains, and the rule keeps BM25 top 4 [KS].
- **Why it rarely loses.** The rule leaves BM25 top 4 only when top 4's reply abstains, and
  the primary judge rejects abstentions on answerable questions ("I don't know." judged wrong on
  347 of 347 validation items). So losses are near 0 by construction, and the gain is the rate at
  which a pool that makes top 4 abstain holds a 4-subset that answers correctly [KS-REG section
  7.3].
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
  top-4 reply abstained and that Qwen3-8B judged correct. In 4 of the 6 the reply is a bare
  "I don't know" on an answerable question, a judge error by the pilot's validation standard;
  the other 2 are hedges that also contain the gold answer, and are ambiguous [AM3D, "(b)"].

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
twin, and 22 twins are among the 347 held-out questions of H1. The two populations are related
[AM3G; AM3G-REG section 1.2].

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
questions). Resampling the 22 twins together with their abstention questions gives nearly the
same intervals. On the unanswerable questions, all 8 does better than the rule for every reader
[AM3G].

### 6.3 Read cost [descriptive]

The rule calls the reader until a 4-subset's reply does not abstain.

- **Answerable questions.** For Qwen3-8B over the 347 held-out questions, the median is 1 read,
  the mean 11.24 and the 90th percentile 70; 231 questions stop at one read and 288 within 8.
  The 45 pools where every 4-subset abstains read all 70, which is 3,150 of the 3,901 reads
  [KS]. Over the three readers the mean is 11-14 with a median of 1 [AM3G].
- **Unanswerable questions.** The median is 70 reads and the mean 43-59: 90-97% of their
  4-subset replies abstain, so the rule reads them all before falling back to BM25 top 4 [AM3G].
- **Capped reads [post hoc; licenses nothing].** For Qwen3-8B on the held-out answerable
  questions, the verifier aggregated the capped variants: a cap of 8 reads gives accuracy 0.548
  at 2.68 mean reads, 16 gives 0.553 at 3.98, and 26 or more gives the uncapped 0.571 (5.45 mean
  reads at 26) [KS].
- **Calls are not equal in cost.** A 4-memory call is shorter than an 8-memory one, and token
  cost was not modelled [AM1B, caveat 6; AM1D].

A read-capped variant that would trade gains against reads and against the H2 cost is the next
step D119 names (an exploratory, post hoc study on these held-out data). It had not run at this
note's base commit.

## 7. What these results do not show

This section collects the "does not decide" and "does not license" statements of the three
registrations and their results [AM1-REG section 2; AM1, "What it does not license"; KS-REG
section 3; KS, "What it does not license"; AM3G-REG section 3; AM3G, "What it does not
license"].

**Scope.**

- One dataset: LongMemEval-S (cleaned), the 347 held-out answerable questions and its 30
  abstention questions. The unanswerable questions are edits of answerable ones; other kinds of
  unanswerable question were not tested.
- One prompt, with an explicit instruction to say "I don't know". The abstention rate the rule
  relies on depends on it, and a prompt without that instruction could change both the
  confidence result and the rule [AM1D, caveat 1; AM3D].
- One retriever (BM25, standing in for MiniLM), one memory unit (user turns of at most 1,500
  characters), one pool size (8) and one budget (4). The gold arm and the other budgets are
  descriptive.
- The abstention patterns were written for Qwen3-8B's development replies. The statement for
  OLMo-2 and Qwen3.5-9B is about the rule with those patterns, not patterns fitted to them.
- Three readers from two families, one size each. Qwen3.5-9B's result holds for its default-mode
  engine and this run's batch schedule.

**Judges.**

- Every accuracy is the Qwen3-32B judge's label. Its hand checks are an agent's labels, not a
  human's, and AM1's κ interval reaches below the registered bar.
- Nothing is claimed under the second judge, which accepts abstentions on answerable questions
  more often.
- H2 rests on an abstention judge that failed G-J2, so its costs are judge-qualified and may be
  too low.

**Credit and search.**

- The registrations do not rank credit rules (pairwise comparisons are secondary) and say
  nothing about exact Shapley's adequacy.
- H-A's search reads labels, so it is not deployable. The tables are noiseless replays, so H-A
  says nothing under a noisy utility, where search would suffer a winner's curse.
- Token cost per call was not modelled.
- Credit's remaining case, one ranking for every budget or credits that transfer across
  questions, was not tested.
- Nothing is shown about training a memory learner on these credits.
- AM2 does not show a content effect of non-gold memories, and AM6 does not give a deployable
  internal signal.

**The rule.**

- It is not safe on unanswerable questions: it turned correct abstentions into wrong answers on
  3-27% of them by the judge's count (0-27% by the hand count).
- It is not shown to beat keeping all 8; that comparison is descriptive, and for Qwen3.5-9B it
  fails.
- The natural-mix rates, the break-even shares, the gold arm, the second judge and the
  question types are descriptions.

**Mechanism.**

- Why the tables are non-monotone is not separated: reader errors, distraction and order
  effects are confounded, and a content-free reorder alone changes 17% of answers.
- Why a different memory subset turns an abstention into a correct answer, and why the readers
  abstain where they do, is not shown.

**Process.** The held-out tables served three registrations, and AM1's published figures fixed
H-B's sign before `am1-keepset-search-v1` ran (D116). The rule and its patterns were chosen on
development data. None of the three registrations carries a gauntlet score.

## 8. Related work

This section cites only work that the program's own records cite: the AM1 registration's
section 1 and the 2026-10-14 question sweep's entries for AM1, AM2 and AM6 and its list of
occupied candidates [AM1-REG section 1; SWEEP]. Descriptions follow those records; this note's
author did not re-read the papers. arXiv dates are the dates the records give.

**Per-memory credit in memory learners.** The credit rules tested here are the ones 2026 memory
learners use, as the registration lists them: one-shot deletion, as in Hindsight Memory-PRM
(arXiv 2608.29605, 2026-08-30); permutation Shapley with 16 permutations, as in MeClear (arXiv
2609.09115, 2026-09-08); and SNIPW over random exposures with known propensity, as in CMP (arXiv
2610.02070, 2026-10-01). CMP shows that memories act jointly and estimates exposure effects with
SNIPW from 80,187 calls of a closed model [AM1-REG section 1]. The sweep also records
UpliftMem (arXiv 2609.36805, 2026-09-29), which learns set-level uplift from sampled probes
rather than exhaustive truth, and DRSR (arXiv 2609.27276, 2026-09-23), which uses exact
joint-deletion supervision because singleton scores do not decide set deletions [SWEEP entry 3].
Result 1 measures this gap on exact tables.

**Exact attribution against an exhaustive reference.** The closest prior work in the
registration is Nematov et al., "Source Attribution in Retrieval-Augmented Generation" (arXiv
2507.04480, 2025-07-06). It compares credit estimators against exact Shapley on 100 RAG queries
with 10 documents each and a log-prob utility. The registration states this study's difference:
agent-memory units on a memory benchmark, a judged generated answer as the utility, exhaustive
exact tables from an open reader under batch-invariant replay, the keep decision scored against
the exact optimum, SNIPW scored against exact truth, and content-placebo controls [AM1-REG
section 1]. The sweep also records SPEX (arXiv 2502.13870, 2025-02-19), sparse Fourier
interactions over sentences [SWEEP entry 3].

**Placebos and replay.** The sweep records that "Re-feeding Is Not Replaying" (arXiv
2606.15621, 2026-06) found engine replay noise in token-level credit and zero disagreement with
`VLLM_BATCH_INVARIANT=1` on another vLLM version and GPU [SWEEP entry 5]. Section 2.3 agrees
for eager mode, and adds that compiled mode replays exactly only for the same compiled kernels.
vLLM's own documentation at the v0.31.0 tag calls batch invariance beta, and GDN attention
has no batch-invariant mode there [SWEEP, check O3], which is why Qwen3.5-9B ran in default mode.

**Internal signals.** AT2 (arXiv 2504.13752, 2025-04-18) learns attention-head weights for
attribution in one pass [AM1-REG section 1]. AM6's cross-fitted heads follow that idea.

**Readers.** The sweep found the question of whether per-memory effects transfer across readers
occupied by "Preference Is Not Intervention" (arXiv 2608.17781, 2026-08-18): over nine readers,
effect signs disagree in 33% of jointly affected cells [SWEEP, "Not ranked"]. This note's
generalisation (section 5.4) is about one keep rule's accuracy across three readers, not about
per-memory effects transferring.

**What the records do not cover.** The sweep's queries through 2026-10-14 found nothing that
occupied AM1 [SWEEP, check O9]. None of the later registrations or results cites prior work on
search over keep sets at matched calls, or on using a reader's abstention as a label-free keep
signal, and none records a prior-art search for either. This note therefore makes no novelty
claim for Results 2 and 3.

## 9. Reproducibility

**Table 8. Studies, registrations, evidence and GPU use.** GPU-h are physical GPU-hours as each
record states them; CPU-only studies used none.

| Study | Ledger row | Freeze commit (fill or head at freeze) | Registration SHA-256 | Evidence | Jobs | Physical GPU-h (cap) |
|---|---:|---|---|---|---|---|
| AM1 Step 0 | | | | `program/evidence/2026-10-15/am1-step0/` | | 0.20 (D107) |
| AM1 development pilot | | | | `program/evidence/2026-10-15/am1-dev-pilot/README.md` | 1405, 1411, 1432, 1435, 1439, 1441 | 1.4862 (2.0) |
| `am1-memory-credit-v1` | 23 | `9ad36b10` (head `c50017af`) | `51d0abb1...` | `program/evidence/2026-10-16/am1-confirmatory/RESULTS.md` | build 1454, job 1458 | 1.5444 (3.1) |
| AM1b | | | | `program/evidence/2026-10-15/am1b-cost-curve/README.md` | CPU | 0 |
| AM1d | | | | `program/evidence/2026-10-15/am1d-label-free/README.md` | CPU | 0 |
| `am1-keepset-search-v1` | 24 | `72d50162` (fill `4b89e8eb`) | `37256cc8...` | `program/evidence/2026-10-16/am1-keepset-search/RESULTS.md` | CPU | 0 |
| AM3 reader replication | | | | `program/evidence/2026-10-16/am3-reader-replication/README.md` | 1462, 1466 | 0.2017 (2.0) |
| `am3-nonabstain-generality-v1`, development dry run | | | | `program/evidence/2026-10-16/am3-nonabstain-generality-dev-dryrun/` | 1467, 1471 | 0.1898 (0.5) |
| `am3-nonabstain-generality-v1` | 25 | `6384f294` (fill `78e9c00f`) | `ff8670f2...` | `program/evidence/2026-10-15/am3-nonabstain-generality-v1/RESULTS.md` | build 1475, jobs 1480, 1482 | 0.6722 (2.08) |

The line used about 4.3 physical GPU-h in all (the sum of the last column, with Step 0's figure
rounded in D107), on H100s of one node.

- **Registrations:** `program/preregistrations/am1-memory-credit-v1.md`,
  `am1-keepset-search-v1.md` and `am3-nonabstain-generality-v1.md`, frozen in rows 23-25 of
  `program/preregistrations/ledger.jsonl`. Each freeze commit adds only its row.
- **Committed outputs are text-free:** tables as 256-bit hex strings, credits, regrets, masks,
  labels, digests and counts. Reply texts, questions, memory texts, features and hand-label texts
  stay on the host, so the registered analyses cannot be rerun from the public repository alone;
  each record names the registered commands, and the verifiers reran them on the host from
  `git archive` exports of the freeze commits.
- **AM1b reproduces from the repository alone**, on a CPU, from the pilot's committed tables
  [AM1B, "Reproduce"]. While writing this note it was rerun at `db589d2f` on a Mac (33 s of CPU)
  into a scratch directory, and `results.json`, `per-table.json.gz` and `tables.md` were
  byte-identical to the committed copies:

  ```bash
  uv run --locked --offline python scripts/memcredit_cost_curve.py \
      --tables program/evidence/2026-10-15/am1-dev-pilot/analysis/tables.json.gz \
      --h2 program/evidence/2026-10-15/am1-dev-pilot/analysis/h2.json \
      --output-dir SCRATCH_DIR
  ```

- **Every number in this note** is listed in `paper/memory-keepset-note/numbers.md` with its
  source file and the source text it was checked against.

## Authorship and process

AI agents ran the studies above under the program's frozen registrations and decisions. The
hand labels were made blind by Claude agents (in `am3-nonabstain-generality-v1`,
`claude-opus-5-5`). An AI agent wrote this note from the committed evidence only, without host
access, and checked its numbers against their sources (`numbers.md`). No human has reviewed this
note or labelled any item. Kevin Liu owns the program and every outward action, including any
publication (D101).

## Sources

Program evidence (paths from the repository root, at `db589d2f`):

- [AM1-REG] `program/preregistrations/am1-memory-credit-v1.md` (frozen, ledger row 23).
- [KS-REG] `program/preregistrations/am1-keepset-search-v1.md` (frozen, ledger row 24).
- [AM3G-REG] `program/preregistrations/am3-nonabstain-generality-v1.md` (frozen, ledger row
  25).
- [PILOT] `program/evidence/2026-10-15/am1-dev-pilot/README.md` (exploratory).
- [AM1] `program/evidence/2026-10-16/am1-confirmatory/RESULTS.md` (confirmatory).
- [AM1B] `program/evidence/2026-10-15/am1b-cost-curve/README.md` (exploratory).
- [AM1D] `program/evidence/2026-10-15/am1d-label-free/README.md` (exploratory).
- [KS] `program/evidence/2026-10-16/am1-keepset-search/RESULTS.md` (confirmatory).
- [AM3D] `program/evidence/2026-10-16/am3-reader-replication/README.md` (exploratory).
- [AM3G] `program/evidence/2026-10-15/am3-nonabstain-generality-v1/RESULTS.md` (confirmatory
  and descriptive).
- [SWEEP] `program/evidence/2026-10-14/question-sweep-memory-gpu/dossier.md`, the question sweep
  that ranked AM1 (entries 3, 5 and 6; owner checks O3, O5 and O9; "Not ranked").
- [DEC] decisions D101, D103, D104, D107 and D111-D119 in `program/decisions.md`.

External sources, as the program's records cite them:

- LongMemEval-S, cleaned: Hugging Face dataset `xiaowu0162/longmemeval-cleaned` at `98d7416c`
  (MIT); the answer-check and abstention prompts from
  <https://github.com/xiaowu0162/LongMemEval> at `9e0b455f`, `src/evaluation/evaluate_qa.py`.
- vLLM 0.31.0 (`db9527a4`), batch-invariant mode; issue
  <https://github.com/vllm-project/vllm/issues/48613> (no batch-invariant mode for GDN
  attention), as read by the sweep's check O3.
- Hindsight Memory-PRM: <https://arxiv.org/abs/2608.29605>.
- MeClear: <https://arxiv.org/abs/2609.09115>.
- CMP: <https://arxiv.org/abs/2610.02070>.
- AT2, Learning to Attribute with Attention: <https://arxiv.org/abs/2504.13752>.
- Nematov et al., Source Attribution in Retrieval-Augmented Generation:
  <https://arxiv.org/abs/2507.04480>.
- UpliftMem: <https://arxiv.org/abs/2609.36805>.
- DRSR: <https://arxiv.org/abs/2609.27276>.
- SPEX: <https://arxiv.org/abs/2502.13870>.
- Re-feeding Is Not Replaying: <https://arxiv.org/abs/2606.15621>.
- Preference Is Not Intervention: <https://arxiv.org/abs/2608.17781>.
