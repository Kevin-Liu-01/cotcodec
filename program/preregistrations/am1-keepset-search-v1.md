# am1-keepset-search-v1: at equal reader calls, does search over keep sets beat sampled memory credit, and does a label-free non-abstention search beat BM25 top 4? (AM1's held-out LongMemEval-S tables, CPU only)

**Status: DRAFT, not frozen.** Drafted on branch `stage0/am1-keepset-search` from `main` at
`ea9d57dc`, as decision D115 specifies (`program/decisions.md`). Freezing is the orchestrator's,
with `scripts/preregister.py`, after two independent pre-freeze checks (D115) and the checklist of
section 17. A material change after the freeze is a new experiment id.

This registration runs no GPU job and makes no new model call. It reads two things the program
already holds: AM1's 694 committed held-out tables (the judged utility of all 256 subsets of each
pool) and, for the label-free rule, the held-out reader pass that made them. Every hypothesis
below was shaped by development results, and several held-out quantities are already public from
AM1. Section 1 lists both before anything else.

## 1. Disclosures

### 1.1 What AM1 already reported about these tables

AM1 (`am1-memory-credit-v1`, ledger row 23, freeze `9ad36b10`, job 1458) committed these tables
and published, in `program/evidence/2026-10-16/am1-confirmatory/RESULTS.md`, the following figures
about them. They were read, as text, before this file was drafted.

- **Census.** Retrieved arm: 347 tables, 96 constant (all 0), 251 non-constant, u(full pool) 0.524.
  Gold arm: 59 constant, 288 non-constant, u(full pool) 0.579. "Every constant table is constant 0,
  and the empty pool is never answered right." 43 of 347 questions are constant in both arms. The
  retrieved pool holds no gold turn for 43 questions, 1 for 117, 2 for 174, and 3-5 for 13.
  Structure classes (retrieved): 167 non-monotone, 57 single, 12 AND, 8 OR, 7 monotone-mixed.
- **Keep-set regret at B = 4, retrieved arm, 251 tables** (95% intervals; "suboptimal" is the
  share of tables with any regret):

  | Rule | Calls | Regret | Suboptimal |
  |---|---|---|---:|
  | leave-one-out | 9 | 0.277 [0.235, 0.319] | 0.546 |
  | permutation Shapley-16 (seeds 42-44) | at most 129 | 0.138 [0.107, 0.173] | 0.279 |
  | SNIPW-64 (seeds 42-44) | 64 | 0.094 [0.066, 0.123] | 0.171 |
  | retrieval rank (BM25 top 4) | 0 | 0.343 [0.287, 0.402] | 0.343 |
  | raw attention | 1 + 1 forward | 0.311 [0.251, 0.371] | 0.311 |
  | exact Shapley | 256 | 0.044 [0.020, 0.072] | 0.044 |
  | exact Banzhaf | 256 | 0.025 [0.009, 0.043] | 0.036 |
  | random keep set | 0 | 0.625 [0.596, 0.653] | 0.976 |

  AM1 also reported, at B = 4, leave-one-in 0.420, permutation Shapley-4 0.231, the
  placebo-filtered deletion label 0.396, the swap effect 0.251, cross-fitted attention 0.255,
  question overlap 0.329, overlap with the reply 0.328 and length 0.406; the gold arm's regrets
  (leave-one-out 0.239, permutation Shapley-16 0.138, SNIPW-64 0.082, retrieval rank 0.278, raw
  attention 0.271, exact Shapley 0.032, exact Banzhaf 0.021, random 0.671); B = 1-3; and the
  second judge's tables. Its verdicts: all five primary rules MISSPECIFIED, leave-one-out minus
  exact Shapley +0.233 [0.194, 0.273].
- **Judge validation (AM1's G2).** The primary judge called the literal reply "I don't know."
  wrong on 347 of 347 held-out questions (validation items, not reader replies). The reader's
  abstentions are almost all of that form (2,386 of the 2,405 flagged development 4-subset replies
  matched the `i_dont_know` pattern), so an abstaining reply is almost never judged correct and H-C
  is in effect one-directional (section 1.2). That rests on the primary judge: the second judge
  (Qwen3-8B) called "I don't know." correct on 49 of 347 held-out validation items (298 of 347
  judged no; RESULTS.md, judge table). H-C's scope therefore names this judge (section 7.3).
- **Held-out replies already read.** AM1's G2 hand check read 120 held-out reader replies (agent
  labels). Their reply SHA-256s, the hand labels and both judges' labels are public in
  `analysis/hand-check-joined-text-free.jsonl`. This registration does not use them. That file
  publishes the SHA-256 of 120 held-out replies with the primary judge's labels, so hashing
  candidate abstention strings could reveal which of those replies abstain; nobody has done this.
- **What AM1 did not report, and nobody has computed:** direct search at any number of calls,
  MSR-Banzhaf, greedy selection, SNIPW-64 or permutation Shapley-16 beyond seeds 42-44, u(BM25 top
  4) as an accuracy, any statistic of the held-out replies' abstention, and any label-free rule.

### 1.2 What AM1's figures already imply for H-B, H-C and H-A

The figures above are rounded, but on these denominators they pin integer counts. A retrieval-rank
regret of 0.343 over 251 tables is 86 tables (85/251 = 0.339, 87/251 = 0.347): BM25 top 4 is
suboptimal, so wrong, on exactly 86 non-constant retrieved tables. u(full pool) 0.524 over 347
questions is 182 questions (181/347 = 0.522, 183/347 = 0.527). BM25 top 4 is therefore right on at
most 251 - 86 = 165 questions (fewer if some non-constant table has no right 4-subset), against 182
for all 8. AM1's committed `h2.json` and `headline.json` hold these figures at full precision
(86/251, 182/347, and the random keep set's regret 10,975/17,570), as pre-freeze check 1 reported
from them; the drafter did not open those files, and every figure below is also derived from the
rounded RESULTS.md values (`power.json`, `conditional_on_am1_published_counts`).

- **H-B is not blind.** Over the 347 questions, u(BM25 top 4) - u(all 8) is at most
  (165 - 182)/347 = **-0.049**: all 8 is right on at least 17 more questions than BM25 top 4. The
  label PRUNING_HELPS cannot occur. The development lead that motivated H-B (BM25 top 4 ahead of
  all 8 by +0.105 on the non-constant development tables, 4 tables against 0) is already reversed
  in sign on the held-out tables. **H-B is therefore descriptive (D116), not a hypothesis.** Its
  exact test and intervals are reported (section 7.2), but they carry no decision. At a net count
  of exactly 17, the exact test of section 7.2 rejects unless there are more than 67 discordant
  pairs (26 or more questions where BM25 top 4 is right and all 8 wrong: b = 25, c = 42 gives
  p = 0.0498; b = 26, c = 43 gives p = 0.0533). On the gold arm the same arithmetic bounds the difference
  by (288 - 80 - 201)/347 = +0.020, which implies no direction.
- **H-C's direction is not implied.** nonabstain-BM25 keeps BM25 top 4 whenever that set's reply
  does not abstain, so it can differ from BM25 top 4 only where top 4's reply abstains. It can gain
  only on the 86 tables where BM25 top 4 is wrong. It can lose only where an abstaining top-4
  reply was judged correct (2 of 2,405 abstaining 4-subset replies on the development retrieved
  arm; the judge called "I don't know." wrong on 347 of 347 held-out questions, section 1.1), so
  c, the count against it, is expected near 0. No held-out abstention statistic exists.
- **H-A: published figures bound direct search but fix no direction.** The 3-seed SNIPW-64 and
  permutation Shapley-16 regrets and the leave-one-out regret are known; greedy backward
  elimination and MSR-Banzhaf-64 are unpublished. Direct search's curve is not published, but
  AM1's figures bound it. A 0/1 table whose best 4-subset is right, with j of its 70 4-subsets
  wrong, has random-set regret j/70 and direct-search regret C(j, m)/C(70, m) at m calls. The sum
  of j over the 251 tables is 70 x 251 x 0.625 (10,975 exactly per check 1; 10,973-10,990 from
  the rounded figure); exactly 245 tables have j above 0 (the random set's suboptimal share,
  0.976); and the census fixes j = 35 for the 57 single tables and limits the 12 AND and 8 OR
  tables to a few values. Under these constraints, direct search's held-out mean regret lies in:
  - [0.022, 0.448] at 9 calls (leave-one-out: 0.277);
  - [0, 0.323] at 26 calls (SNIPW-64: 0.094; permutation Shapley-16: 0.138; seeds 42-44);
  - [0, 0.095] at 57 calls (SNIPW-64: 0.094);
  - [0, 0.044] at 64 calls (MSR-Banzhaf-64: unpublished).

  These are exact bounds under the constraints (`direct_search_bounds`; they equal check 1's).
  The 57-call bound nearly excludes RULE_BETTER on A2 before the run: SNIPW-64 would have to lose
  less than direct search at its own calls, which needs direct search's regret near the top of
  its range. For A4, exact Banzhaf's published regret, 0.025 [0.009, 0.043], is MSR-Banzhaf's
  many-sample limit; with direct search at 64 calls bounded by [0, 0.044], A4's sign is open.
  Nothing published bounds greedy backward elimination, so A7 is open too. No other comparison's
  direction is fixed.

### 1.3 Development work that shaped the hypotheses

- **AM1b** (`program/evidence/2026-10-15/am1b-cost-curve/README.md`, exploratory, the 126
  development tables): on the retrieved arm at B = 4 (38 tables), no query-based credit rule beat
  direct search at equal calls, even on the point estimate. Direct search lost 0.091 at 9 calls
  and 0.024 at 26 calls; leave-one-out lost 0.214 at 9 calls, greedy backward 0.079 at 26, SNIPW-64
  0.050 at about 57, MSR-Banzhaf-64 0.043 at 64, permutation Shapley-16 0.095 at about 83. AM1's
  3-seed SNIPW-64 figure (0.070) was seed noise; AM1b used 20 seeds. The comparisons of H-A, their
  call counts, the 26-call point and the 200 seeds here all come from AM1b.
- **AM1d** (`program/evidence/2026-10-15/am1d-label-free/README.md`, exploratory, development
  replies of job 1411): confidence and vote utilities were anti-informative; the only usable
  label-free signal was whether the reply abstains. `nonabstain@70` was the best of 40 label-free
  rules in sample (+0.026 [0.000, 0.079] over BM25 top 4 on 38 tables, one table), and BM25 top 4
  led all 8 by 4 tables against 0 (exact p = 0.125). H-C tests that one rule, chosen in sample on
  development data; H-B describes how that lead reversed (D116). AM1d's abstention pattern list was committed at
  `7465903f` before AM1d read any reply; it is used unchanged.

### 1.4 Development and held-out differ

On the retrieved arm at B = 4, retrieval rank lost 0.132 on development and 0.343 on held-out;
exact Shapley 0.079 and 0.044; the random keep set 0.576 and 0.625; SNIPW-64 (seeds 42-44) 0.070
and 0.094; leave-one-out 0.214 and 0.277. Development effects need not transfer, and section 1.2
shows that one did not.

### 1.5 Reader, judge, tables; no gauntlet score

- The reader (Qwen3-8B, eager batch-invariant vLLM, greedy, thinking off, Step 0's prompt) and the
  judge (Qwen3-32B with LongMemEval's official prompt) are AM1's. AM1's judge gate G2 passed with
  agent hand labels, kappa 0.867 (D9, D111).
- The tables come from job 1458's GPU-0 eager pass (`reader-gpu0`, canonical order) and its
  primary judge (`judge32-gpu0`). That pass replayed bit-exactly across GPUs, processes and orders:
  190,156 of 190,156 reader requests and 10,230 of 10,230 judge items (AM1's G1).
- The utilities in H-A are oracle utilities: u(S) is the judge's label against the reference
  answer. H-A measures attribution quality per question when labels are available, not a keep
  policy that runs without labels. H-C's rule reads no label; its choices are scored with the
  same oracle utility.
- **No gauntlet score (D115).** The registration is CPU-only, on data the program holds, and
  continues a confirmed line. No gauntlet wave runs; two independent pre-freeze checks are
  required instead.

### 1.6 What the drafter opened

The drafter read `RESULTS.md` and `README.md` of the AM1 confirmatory directory and its SHA-256
records (`raw-sha256.txt`, `judge-items.sha256.txt`, `study-artifact.sha256`,
`analysis/logs/outputs.sha256`), and computed SHA-256 digests of the committed held-out
`tables.json.gz` and, on the host, of the held-out input files (and of `gzip -n` copies of the two
passes' `all.json`, which equal the committed `all.json.gz` digests). No held-out table, reply or
JSON or gz output was decoded or analysed; `h2.json`, `headline.json` and
`hand-check-joined-text-free.jsonl` were not opened by the drafter (pre-freeze check 1 read the
first two for the full-precision counts of section 1.2). The script refuses held-out inputs until this file is
frozen (section 8). The development selftest (section 15) ran in a new host directory,
`~/cotcodec-runs/stage0/am1ks-dev-selftest/`, on development data only.

## 2. Question

When the decision is which 4 of a question's 8 retrieved memories to keep, on LongMemEval-S with
AM1's reader and judge:

- **H-A (oracle utility).** If the judged utility of a subset can be queried, does direct search
  over keep sets (read m distinct random 4-subsets, keep the best one read) lose less than the
  sampled and greedy credit rules at the same or fewer reader calls?
- **H-B (descriptive, D116).** How far does pruning the pool to BM25 top 4 move the reader's
  accuracy against keeping all 8? Its sign is implied before the run (section 1.2).
- **H-C (label-free, deployable).** Does keeping the best-BM25-ranked 4-subset whose reply does not
  abstain change accuracy against BM25 top 4?

Closest prior work is AM1's (section 1 of `am1-memory-credit-v1.md`). The delta here is the
cost axis: credit rules and search scored against the exact optimum at matched reader calls, with
exact expectations over the search's draws, on held-out tables.

## 3. What it decides and what it does not

It decides H-A's verdict (SEARCH_DOMINATES, RULE_BEATS_SEARCH, RULE_AT_MORE_CALLS_BETTER or
INCONCLUSIVE) and H-C's reading (NONABSTAIN_HELPS, NONABSTAIN_HURTS or NO_DETECTED_DIFFERENCE, or
VOID when its inputs fail section 8's V3 or V5), both on the retrieved arm (section 7). H-B is descriptive: its direction was implied by AM1's published figures before the
run (section 1.2, D116). The gold arm, the question types and every other number are also
descriptive.

It does not decide:
- which credit rule is best, or anything at B other than 4;
- anything under a noisy utility: direct search keeps the set that maximizes the same noiseless
  u it is scored on, so under reader or judge noise it would suffer a winner's curse that
  averaging credit rules largely avoid; the tables are deterministic replays;
- anything about token cost: a 7-memory leave-one-out call is longer than a 4-memory search call;
- whether H-A's search is deployable (it reads labels);
- why abstention tracks correctness, or anything for other readers, judges, prompts, retrievers,
  pool sizes or memory units;
- credit's remaining case: one ranking for every budget, or credits that transfer across
  questions (D113).

## 4. Identity and pins

| Item | Pin |
|---|---|
| Experiment id | `am1-keepset-search-v1` (this file) |
| Held-out tables | `program/evidence/2026-10-16/am1-confirmatory/analysis/tables.json.gz` as committed in AM1's results commit `32996482` (unchanged since): SHA-256 `841e79452d7af6441492abfce64d85cadf5b51415cc7e0461df76ce228df0729`; uncompressed, the `tables.json` of AM1's registered `analyze`, SHA-256 `2d3574be5d3686d73b73dc2d1b36ed3c9b04b23731078bcb6b5f92b83cc3a9cd` (`analysis/logs/outputs.sha256`; the host's `analysis/1458/tables.json` has the same digest) |
| Questions | AM1's confirmatory set: 347 ids, SHA-256 of the newline-joined ids in the split's order `d4f024fbcda5394984a46c421cd938f2b6db6067fef0f21a5c6e72359b27e50a` (`experiments/am1/am1-memory-credit-v1.yaml`, `confirmatory_set`; checked against `experiments/am1/memcredit-split-v1.json`, SHA-256 `4fa1b774d4131080855d668ac8f00f5cb07d49cf741f2051d5f8d96577edb3e3`) |
| Study artifact (H-C only) | host `~/cotcodec-runs/stage0/am1-memory-credit-v1/study-artifact.json`, SHA-256 `f23bca047dc7246c5a8db12f67a76a2ea36304d8669dc5c62ae6c42821f73eb7` (`jobs/1458-main/study-artifact.sha256`) |
| Held-out pass (H-C only) | job 1458, host `~/cotcodec-runs/stage0/am1-memory-credit-v1/runs/main/1458/am1/`; the files of the table below |
| Reader, judge | AM1's (registration `am1-memory-credit-v1.md`, section 3) |
| Abstention patterns | AM1d's four patterns (`scripts/memcredit_label_free.py`, `ABSTENTION_PATTERNS`), SHA-256 of their canonical JSON `031bee27e934a772f3419e38f9956d33dbea01096e6657e67426fd8a399d935f`, committed at `7465903f` |
| Code | section 16 |

The held-out pass files that `extract` reads (paths relative to the job's `am1` directory). The
`all.npz` and `all.texts.jsonl.gz` digests equal AM1's committed `raw-sha256.txt` records; the
`all.json` digests were computed on the host, and `gzip -n` of each gives the SHA-256 of AM1's
committed `all.json.gz` copy (`dfeeae61...` reader, `40fe5408...` judge, `7480fba1...` second
judge); `worker-progress.jsonl` equals AM1's committed copy; `judge-items.json` equals
`judge-items.sha256.txt`.

| File | SHA-256 |
|---|---|
| `sessions/reader-gpu0/all.json` | `c8381bcbe4afe33e436ad101cbe313ef1608c40916dbd8a6e3a4c0191322e189` |
| `sessions/reader-gpu0/all.npz` | `8f985d8a2b40ecbb4fcbed1c2a63323c3d4ce398da83eea5fef8bca137054776` |
| `sessions/reader-gpu0/all.texts.jsonl.gz` | `b05d5d87f9b9c7445cb053d8e4830e2fcf105f04f7c265551773dd9665fcfd39` |
| `sessions/reader-gpu0/worker-progress.jsonl` | `0f280d34fa6ede8f6e0a11e4428e7114a9489595fae17a7a22940cb55c9ec470` |
| `sessions/judge32-gpu0/all.json` | `5a36bbac383c6a5395c148dc837c75906cf806ff64969cc67ef770b417929300` |
| `sessions/judge32-gpu0/all.npz` | `229cefd3fdadc060a89f5d16e6c7ab76d8a20f7f444bc88fd7d48740c6f9f7f6` |
| `sessions/judge32-gpu0/all.texts.jsonl.gz` | `e2166086dfe773a4e52054d2dc6d58372adb7cde8a4e4a060e990a6e66fb53f4` |
| `sessions/judge8-gpu0/all.json` | `33c280bf120a551fe41c9569cd2c350d31eca50da4b791b64867ec62a370883c` |
| `sessions/judge8-gpu0/all.npz` | `9fe7bf7d1ac5a35478d8dc064d88f30e6f5f65631d664a74d5f8720f932d1ba7` |
| `sessions/judge8-gpu0/all.texts.jsonl.gz` | `e31d77ad7f39a56d829b5ccbef033e56b5b99fe90d01725d03d837a82de95cae` |
| `judge-items.json` | `c3eec6515b4e654bb88cccef65dba1d88e210326bbf238c27c6f8dfa1c3a2999` |

`memcredit_analyze.join_rows`, the join that built the tables, also loads the second judge's pass
(`judge8-gpu0`) and computes containment against the reference answer; neither is used here, and
the second judge's files are pinned because they are read.

## 5. Units and inputs

- **Questions** are the unit of resampling: the 347 of AM1's confirmatory set, one table per
  question per arm.
- **Arms.** `retrieved` (primary: the BM25 top 8 user turns, chronological) and `gold`
  (secondary), as AM1 built them.
- **Decoding.** `values[m]` is bit m of `int(values_hex, 16)`; bit i of a mask keeps memory i in
  pool order. AM1b validated this decoding against every committed credit, regret and bootstrap
  row of the development tables (`memcredit_cost_curve.decode_values`).
- **Non-constant tables.** A table is non-constant when its 256 values are not all equal (AM1's
  `summary.constant` is false): 251 retrieved and 288 gold, as AM1 reported. H-A reads only these:
  a constant table has no keep decision to score. H-B and H-C read every question; a constant table
  is 0 for every rule and so concordant.
- **BM25 ranks** come from each table's `credits.retrieval_rank` (minus the rank; distinct within
  a pool). **BM25 top 4** is the set of the four best-ranked memories, AM1's retrieval-rank keep set
  (checked for every table).
- **The 70 4-subsets** of the 8 memories, and their order for H-C (section 6.6).

## 6. Rules, calls and estimands

### 6.1 Calls and regret

- A **call** is one distinct subset whose u(S) a rule reads, memoized per pool, as a deployed
  system would cache it; the empty and full sets count when they are read (AM1b).
- **Regret** at B = 4 is OPT_4 minus u(keep set), OPT_4 = max over the 70 4-subsets of u. A credit
  rule keeps its top 4 by credit, and its regret is averaged uniformly over every keep set its ties
  allow (`harness.memcredit.keep_set_regret_range`, `mean`; AM1's convention). A search rule returns
  one set, scored by the same function on that set's indicator (`memcredit_cost_curve.set_regret`).

### 6.2 The rules of H-A (AM1b's definitions and code, unchanged)

| Rule | Calls | Definition |
|---|---|---|
| leave-one-out | 9 | `mc.loo_credit`: u(N) - u(N minus i); the full set and the 8 deletions |
| SNIPW-64 | distinct exposures read (about 57) | `ms.snipw`: 64 i.i.d. exposures, each memory kept with probability 1/2; mean u with i kept minus mean u with i dropped |
| MSR-Banzhaf-64 | 64 | `cc.msr_banzhaf`: 64 distinct uniform subsets without replacement; maximum-sample-reuse Banzhaf in exact rational arithmetic |
| permutation Shapley-16 | distinct subsets read (about 83) | `ms.permutation_shapley`: 16 uniform orders |
| greedy backward, BM25 ties | 26 | `cc.greedy_backward`: remove, 4 times, the memory whose removal leaves the highest u (8 + 7 + 6 + 5 sets, of sizes 7 to 4; never the full set); ties drop the worse BM25 rank |
| direct search at m calls | m | read m distinct uniformly random 4-subsets and keep the best one read |

**Direct search's regret is an exact expectation over its draws** (`cc.direct_search_curve`): with
the 70 4-subsets sorted by regret r_(1) ≤ ... ≤ r_(70), the best of m distinct uniform draws is
the j-th with probability C(70 - j, m - 1)/C(70, m), so E[regret] = sum over j of r_(j) C(70 - j,
m - 1)/C(70, m). Every best-read set has the same u, so ties cannot change it. At 70 calls it is
0.

**Sampled rules** (SNIPW-64, MSR-Banzhaf-64, permutation Shapley-16) run 200 seeds, 42 to 241,
each with `random.Random(f"{seed}:{question_id}:{arm}:{rule}")` and the rule names `snipw_64`,
`msr_banzhaf_64` and `perm_shapley_16`. That is AM1's and AM1b's scheme, so seeds 42-44 are AM1's
draws and seeds 42-61 AM1b's. A table's value for a sampled rule is its mean over the 200 seeds:
the estimand is the expectation over the rule's random draws.

### 6.3 H-A's comparisons

Each comparison j is a paired difference per non-constant retrieved table,

  D_j(table) = regret of direct search at the comparison's calls - regret of the rule,

averaged over seeds for a sampled rule. **Negative D_j means direct search loses less.** For
"matched" comparisons, direct search reads exactly as many 4-subsets as the rule read on that
table and seed (AM1b's pairing; for SNIPW-64 the count varies by draw).

| Id | Rule | Rule's calls | Direct search's calls |
|---|---|---|---|
| A1 | leave-one-out | 9 | 9 (matched) |
| A2 | SNIPW-64 | about 57 | matched, per table and seed |
| A3 | SNIPW-64 | about 57 | 26 (fewer) |
| A4 | MSR-Banzhaf-64 | 64 | 64 (matched) |
| A5 | MSR-Banzhaf-64 | 64 | 26 (fewer) |
| A6 | permutation Shapley-16 | about 83 | 26 (fewer) |
| A7 | greedy backward, BM25 ties | 26 | 26 (matched) |

Permutation Shapley-16 has no matched comparison: it almost always reads more than 70 subsets
(68-94 on development, mean 83), where direct search is exhaustive and loses nothing, so that
comparison would nearly restate its regret.

A1, A2, A4 and A7 are the **matched** comparisons (equal calls). A3, A5 and A6 are the
**fewer-calls** comparisons: direct search reads 26 subsets against the rule's 57-83.

The estimand of comparison j is the expected D_j over questions drawn as AM1's confirmatory set
was (held-out questions whose retrieved table is non-constant), estimated by the mean of D_j over
the 251 such tables; the bootstrap resamples questions.

### 6.4 H-B (descriptive, D116)

Over all 347 questions, retrieved arm: u(BM25 top 4) and u(all 8), each 0 or 1. The discordant
counts are b (BM25 top 4 right, all 8 wrong) and c (the reverse). The estimand is the accuracy
difference (b - c)/347.

### 6.5 H-C

`nonabstain-BM25` keeps the best-BM25-ranked 4-subset whose reply does not abstain, and BM25 top 4
when every 4-subset abstains. "Abstains" means AM1d's rule (`memcredit_label_free.abstention`): the
reply, normalized by `harness.memcredit.normalize_answer`, is empty or matches one of the four
patterns pinned in section 4. This is AM1d's `nonabstain@70`; it reads no label. Over all 347
questions, retrieved arm: b (nonabstain-BM25 right, BM25 top 4 wrong), c (the reverse), and the
difference (b - c)/347.

### 6.6 The BM25 reading order and the stop rule's reads (descriptive)

The 70 4-subsets are read in ascending sum of their four BM25 ranks; equal sums go to the
lexicographically smaller sorted rank tuple (AM1d's `rank_key`, read in descending key order).
BM25 ranks are distinct within a pool, so this is a total order, and BM25 top 4 is first. The
stop rule reads in this order and stops at the first reply that does not abstain; its choice is
exactly nonabstain-BM25's (checked per pool). Its **reads** are the position of that reply (the
answering call included), or 70 when no 4-subset answers (it then answers with BM25 top 4's
reply, already read). Reported: mean, median, 90th percentile, maximum, the counts at 1, at most
8 and at most 16, and the full distribution, over all questions and over non-constant tables,
per arm; and AM1d's capped variants (at most 8, 16, 26, 38 reads, then BM25 top 4).

### 6.7 Descriptive outputs

Per arm, and per question type within each arm:
- the oracle-search ceiling: the mean of OPT_4 over every question (the accuracy of exhaustive
  oracle search);
- direct search at m = 8, 16, 26, 38 and 70 calls: mean regret over the non-constant tables, and
  accuracy (OPT_4 minus regret) over every question;
- the accuracies of BM25 top 4, all 8 and nonabstain-BM25;
- the abstention rate of the 4-subset replies, the number of pools where BM25 top 4 or all 8
  abstains, the number where every 4-subset abstains, and abstaining replies judged correct;
- H-A's comparisons, rule regrets and decision bounds on the gold arm, under the same rule as
  section 7.1 but without a decision;
- H-C's test on the gold arm, without a decision: its label is a descriptive label
  (`h_c.gold.descriptive_label`; "descriptive label, no decision" in `tables.md`), as is H-A's
  gold-arm label (`h_a.gold.descriptive_label_no_decision`; "Descriptive label (no decision)" in
  `tables.md`);
- H-B on both arms, which is descriptive everywhere (D116; section 7.2);
- nonabstain-BM25 against all 8 on both arms, also descriptive.

### 6.8 Intervals

Question-cluster percentile bootstrap, `harness.memcredit_study.cluster_bootstrap`: 10,000
resamples of questions with replacement, numpy `default_rng(42)`. With one table per question per
arm it resamples tables, and since every comparison of an arm has the same questions and the same
seed, all of them use the same resamples. 95% two-sided intervals throughout; H-A's decision
bounds are the one-sided ends of section 7.1.

## 7. Hypotheses and decision rules

### 7.1 H-A (primary): search against credit at equal or fewer calls

**Family**: the seven comparisons A1-A7 of section 6.3, retrieved arm, B = 4, 251 non-constant
tables.

**Bounds.** For each comparison, U_j and L_j are the one-sided upper and lower percentile
bootstrap bounds of the mean of D_j at nominal level 1 - 0.05/7 (one-sided 99.29%): with the
R = 10,000 resampled means sorted, the 0-based indices ceil((1 - 0.05/7)(R - 1)) = 9,928 and
floor((0.05/7)(R - 1)) = 71, that is the 72nd largest and the 72nd smallest (the ends of
`cluster_bootstrap`'s two-sided interval at alpha 2 x 0.05/7).

**Monte Carlo margin.** A bound clears 0 only if it clears it by more than 3 Monte Carlo standard
errors of that comparison's mean (section 7.4), and by any margin for A1 and A7, whose rules are
deterministic.

Each comparison is classified SEARCH_BETTER if U_j is below 0 by more than the margin,
RULE_BETTER if L_j is above 0 by more than the margin, and NOT_SEPARATED otherwise. Then:

- **SEARCH_DOMINATES** if all seven are SEARCH_BETTER;
- **RULE_BEATS_SEARCH** if a matched comparison (A1, A2, A4 or A7: equal calls) is RULE_BETTER;
  the report names them;
- **RULE_AT_MORE_CALLS_BETTER** if no matched comparison is RULE_BETTER but a fewer-calls one (A3,
  A5 or A6) is. There the rule read about 57-83 subsets against direct search's 26, so this label
  says only that the rule, reading two to three times as many subsets, lost less. It blocks
  SEARCH_DOMINATES and licenses nothing at equal calls; the report names the comparisons;
- **INCONCLUSIVE** otherwise; the report names the comparisons not separated. Under
  INCONCLUSIVE the other comparisons' classifications still hold together at 0.05 (nominal) per
  direction.

The four are exclusive: a comparison cannot be both SEARCH_BETTER and RULE_BETTER, SEARCH_DOMINATES
leaves none RULE_BETTER, and RULE_BEATS_SEARCH takes precedence over RULE_AT_MORE_CALLS_BETTER
(both lists are reported).

**Why this family, this alpha, this bootstrap.**
- The family is the set of rules D113 and D115 name for this test, each at the calls where the
  claim "direct search at equal or fewer calls" is made: the two rules AM1 scored with seeds
  (permutation Shapley-16 and SNIPW-64), the cheapest exact rule (leave-one-out), the best sampled
  Banzhaf rule per call in AM1b (MSR-Banzhaf-64), and the only search rule AM1b tried (greedy
  backward with BM25 ties; forward selection with BM25 ties lost more on development, 0.105).
- Alpha: each verdict's nominal probability of being wrong is at most 0.05. AM1's H2 used 99%
  two-sided intervals with Bonferroni over five rules, which is 2.5% per direction; this design
  spends 5% in each direction, because each direction carries its own verdict. The bounds are
  one-sided because the hypothesis has a direction (search loses less), and the opposite
  direction is its falsifier, tested by its own one-sided bound at the same level.
- Bonferroni rather than Holm, because it gives bounds, the dual of the tests, that the report can
  print and a reader can check. Nominally, SEARCH_DOMINATES is an intersection-union claim: it is
  wrong only if some D_j is at least 0, and then it fires with probability at most 0.05/7, so
  Bonferroni is conservative for it. RULE_BEATS_SEARCH is a union over the four matched
  comparisons, wrong with probability at most 4 x 0.05/7; RULE_AT_MORE_CALLS_BETTER a union over
  the three others, at most 3 x 0.05/7.
- **These rates are nominal.** The percentile bootstrap does not hold them under the skewed
  differences of these tables. In the size simulation of section 9, built from the development
  differences, a centred comparison was called RULE_BETTER in up to 0.0185 of runs (nominal
  0.0071), a wrong RULE_BEATS_SEARCH came out in about 0.04 (nominal 0.029), and a wrong
  SEARCH_DOMINATES stayed at or below 0.0065, except in a skew stress case where a rule wins large
  on 2% of tables, where it reached about 0.04. Every measured verdict error was under 0.05. The
  method is kept, as registered, and the measured size is reported with it; a verdict is read
  with that size, not the nominal one.
- A2 and A4 are nearly implied by A3 and A5: direct search's expected regret does not increase
  with calls, so whenever a SNIPW-64 draw reads at least 26 subsets (every development draw read
  47 or more) D_A2 is at most D_A3 table by table, and with shared resamples U_A2 is at most U_A3
  and L_A2 at most L_A3; MSR-Banzhaf-64 always reads 64. So A2 and A4 can change the verdict only
  through their Monte Carlo margins. They are kept because they are the equal-calls comparisons
  D113 names, and their classifications are reported; Bonferroni over seven, not five, is the
  price, and it is conservative.
- The percentile bootstrap of questions is AM1's, AM1b's and AM1d's, with AM1b's and AM1d's 10,000
  resamples. At one-sided 99.29% the bound is the 72nd most extreme of 10,000 resampled means; its
  bootstrap Monte Carlo error is about 0.04 standard errors of the mean.

**Program reading.** SEARCH_DOMINATES licenses, within the scope of section 3: "with the oracle
utility, direct search over random 4-subsets loses less keep-set regret than leave-one-out and
greedy backward elimination at the same calls, and than SNIPW-64, MSR-Banzhaf-64 and permutation
Shapley-16 at 26 calls, fewer than they read; in expectation over the search's and the rules'
random draws and over questions drawn as AM1's confirmatory set was (held-out questions with a
non-constant retrieved table), as estimated by the 251-table mean with questions resampled" (this
reader, this judge, LongMemEval-S held-out questions, BM25 user-turn pools, 4 of 8). RULE_BEATS_SEARCH names the rules that beat
direct search at equal calls. RULE_AT_MORE_CALLS_BETTER names the rules that lost less while
reading more calls, and licenses nothing at equal calls. INCONCLUSIVE names the comparisons not
separated, and the others' classifications stand as reported. On the gold arm the same rule
gives a descriptive label, not a verdict.

### 7.2 H-B (descriptive, D116): BM25 top 4 against all 8

H-B carries no decision. The test, intervals and labels below are computed and reported as a
description only, in a block of their own (`h_b_descriptive`, `decides: false`), outside the
verdicts. The reason is section 1.2: AM1's figures fixed its sign before the run.

**Test.** The exact two-sided McNemar test on the discordant pairs of section 6.4: p = min(1,
2 P(X ≤ min(b, c))), X ~ Binomial(b + c, 1/2), in exact rational arithmetic; p = 1 when b + c = 0.

**Description labels** (at alpha 0.05; descriptions, not readings):

- PRUNING_HELPS if p ≤ 0.05 and b > c;
- PRUNING_HURTS if p ≤ 0.05 and b < c;
- NO_DETECTED_DIFFERENCE otherwise.

**Interval.** The paired difference (b - c)/347 with its exact conditional 95% interval: given
the b + c discordant pairs, ((b + c)/347)(2 pi - 1) at the ends of pi's Clopper-Pearson interval
for b of b + c (`harness.memcredit.clopper_pearson`). It is the inversion of the same exact test,
so it excludes 0 exactly when the test rejects (tested over every b, c up to 25). The
question-cluster bootstrap 95% interval is reported beside it, as AM1d did.

AM1's figures already put the difference at -0.049 or below (section 1.2), so the label
PRUNING_HELPS cannot occur. The size of the difference and its intervals are what H-B adds.

### 7.3 H-C: nonabstain-BM25 against BM25 top 4

**Test.** The same exact McNemar test on the discordant pairs of section 6.5, alpha 0.05 two-sided,
with the same exact conditional and bootstrap intervals.

- **NONABSTAIN_HELPS** if p ≤ 0.05 and b > c;
- **NONABSTAIN_HURTS** if p ≤ 0.05 and b < c;
- **NO_DETECTED_DIFFERENCE** otherwise.

NONABSTAIN_HELPS licenses, within the scope of section 3: "keeping the best-BM25-ranked 4-subset
whose reply does not abstain is more accurate than BM25 top 4" (this reader and prompt, this
judge, LongMemEval-S held-out questions, BM25 user-turn pools, 4 of 8). It is a deployable keep
rule (no label is read) whose cost is the stop rule's reads (section 6.6). NONABSTAIN_HURTS would
license the reverse in the same scope. Because an abstaining reply is almost never judged correct
(section 1.1), c is expected near 0 and the test is in effect one-directional: with c = 0 it
rejects when b is 6 or more, with c = 1 when b is 8 or more, with c = 2 when b is 10 or more.
NONABSTAIN_HELPS does not say the rule beats keeping all 8; that comparison is reported as a
description (section 1.2 shows all 8 at least 17 questions ahead of BM25 top 4). If the inputs of
section 8's V3 or V5 fail, H-C is VOID with the named error, and nothing about it is read.

### 7.4 Monte Carlo error of the sampled rules

For each comparison and rule with seeds, the Monte Carlo standard error is the standard deviation
over the 200 seeds of the seed's mean over tables, divided by the square root of 200 (AM1b's
`seed_mc_se`). On the development tables (38 retrieved, 51 gold) it was 0.0013-0.0020 (the dry
run of section 15); on 251 tables it is expected near 0.0005-0.0008. It enters H-A through the
margin of section 7.1 and is reported for every comparison, with the list of comparisons whose
bounds lie within it (`bounds_within_mc_margin`).

### 7.5 Multiplicity across hypotheses

H-A and H-C answer different questions, and no claim is made from "either of" them, so each is
read at its own alpha without a correction across them. H-A's family carries its own correction.
H-B is descriptive (D116). The secondary and descriptive outputs carry no correction and license
nothing.

## 8. Validity checks, void and kill rules

`scripts/memcredit_keepset_search.py` evaluates every check below. Each failure is a named error
whose text begins with its rule (`VOID (V1/V2, nothing read)`, `VOID (H-C, V3)`, `VOID (H-C,
V5)`); none surfaces as a traceback.

- **Freeze gate.** With `--split heldout`, `extract` and `analyze` refuse to open any held-out
  input unless the ledger holds a row for `am1-keepset-search-v1` whose SHA-256 equals this file's,
  and every code pin of section 16 matches the working tree (parsed from this file). The gate runs
  before any held-out file is opened. The tests check the refusal and the opening against a
  scratch ledger and a scratch copy of this file, never the real ledger's row, so the tests pass
  before and after the freeze. No test decodes the held-out tables; one test hashes the committed
  gz to check its pin (and reads AM1's SHA-256 record files).
- **VOID, nothing read (V1): a digest differs.** The tables' gz file or the uncompressed tables
  (section 4), any code pin, or the abstention list's digest. An input is fixed, never the code; a
  code change is a new registration id.
- **VOID, nothing read (V2): the tables are not AM1's.** Not exactly 694 tables over the 347
  confirmatory ids (checked against the split file and the id digest), one per question and arm;
  any table incomplete; any `values_hex` that does not round-trip; `summary.constant` disagreeing
  with the decoded values; non-constant counts other than 251 retrieved and 288 gold; BM25 ranks
  not distinct; BM25 top 4 not AM1's retrieval-rank keep set.
- **VOID for H-C only (V3): an H-C input fails.** `extract` stops with a `VOID (H-C, V3)` error
  when any of these holds:
  - the study artifact or any pass file of section 4 is missing, unreadable or has another
    SHA-256, or a pass cannot be parsed;
  - any table lacks `distinct_replies`;
  - the joined labels (`memcredit_analyze.join_rows`, unchanged) do not reproduce `values_hex` and
    `distinct_replies` on all 694 tables (`memcredit_label_free.validate_tables`);
  - AM1d's join disagrees with it on any request's reply or label, a table request lacks a reply
    or a label, or a log-prob is missing.

  `analyze` stops with a `VOID (H-C, V3)` error when the features file is unreadable, truncated
  or malformed, or its pools do not match the tables one for one (the table's 256 utilities, BM25
  ranks, question type and 256 abstention flags). `extract` writes its file atomically, so a crash
  leaves no partial file.
- **VOID for H-C only (V5): features provenance.** `analyze` stops with a `VOID (H-C, V5)` error
  when the features' recorded split, pass digests, artifact digest, abstention-list digest or
  code digests differ from the pins. The code digests cover this script and the nine repository
  modules `extract` imports (section 16; a test checks that list against a fresh interpreter's
  imports).
- **The H-C void path.** After a V3 or V5 error, `extract` is not rerun with other inputs, and
  `analyze` runs once with `--h-c-void` and the error's text instead of `--features` (section 16).
  It records H-C as VOID with that reason (`h_c.status`, `verdicts.H-C.reading`), and computes H-A,
  H-B and the descriptive outputs from the pinned tables alone; the abstention outputs and the stop
  rule's reads are then absent. H-A and H-B stand.
- **VOID (V4): a confirmatory file changed.** At the freeze commit and at the analysis commit,
  `git diff ea9d57dc -- program/evidence/2026-10-16/am1-confirmatory` must be empty (freeze
  checklist and the analysis record), and the tables' digests are checked by the code (V1).
- **Kill.** None beyond the void rules: every hypothesis is read when its inputs pass. A void is
  reported with its check, and the registration is not rerun under this id with other inputs.
- **Monte Carlo sensitivity** is handled inside H-A's rule (section 7.1), not as a void.

## 9. Operating characteristics (from the development dry run)

Computed by `scripts/memcredit_keepset_search.py power` from the development dry run of this code
(`program/evidence/2026-10-16/am1-keepset-search-dev-selftest/power.json`; section 15).

**H-A.** 1,000 simulations, each drawing 251 tables with replacement from the 38 development
retrieved non-constant tables (their seven differences together), with a 1,000-resample bootstrap
inside and section 7.1's rule (without the Monte Carlo margin). Reduced effects by Bernoulli
thinning: each drawn table keeps its seven differences with probability 1/2 or 1/4, else all are
0.

| Development mean of D_j | A1 | A2 | A3 | A4 | A5 | A6 | A7 |
|---|---:|---:|---:|---:|---:|---:|---:|
| (38 tables, 200 seeds) | -0.123 | -0.044 | -0.025 | -0.046 | -0.025 | -0.069 | -0.055 |

| Effect | P(SEARCH_DOMINATES) | P(INCONCLUSIVE) | P(RULE_BEATS_SEARCH) | P(RULE_AT_MORE_CALLS_BETTER) | Weakest comparisons, P(SEARCH_BETTER) |
|---|---:|---:|---:|---:|---|
| as on development | 0.999 | 0.001 | 0 | 0 | A7 0.999 |
| half | 0.909 | 0.091 | 0 | 0 | A7 0.919, A5 0.988 |
| quarter | 0.372 | 0.622 | 0.006 (A7) | 0 | A7 0.449, A5 0.773 |

Readings: if the held-out differences resemble development's, the design calls SEARCH_DOMINATES
with probability near 1, and with probability about 0.9 at half the effect. Greedy backward (A7)
is the weak link: on development it lost 0.055 more than direct search at 26 calls, 95% [-0.003,
+0.130] (AM1b, rule minus direct). These figures rest on 38 development tables, and development
and held-out differ (section 1.4).

**H-A's measured size** (`power.json`, `size`; `size_simulation`, seed 44). The same rule
(without the Monte Carlo margin) on 2,000 simulated sets of 251 tables, each drawn with
replacement from the 38 development tables' seven differences, with 2,000 bootstrap resamples
each. The nominal rates of section 7.1 are 0.0071 per comparison and direction, 0.029 for
RULE_BEATS_SEARCH and 0.021 for RULE_AT_MORE_CALLS_BETTER.

| Case | Measured | Nominal |
|---|---|---|
| All seven centred (mean 0): a comparison called RULE_BETTER, per comparison | 0.009-0.0185 (A7 highest) | 0.0071 |
| All seven centred: a comparison called SEARCH_BETTER, per comparison | 0.0025-0.0085 (A1 highest) | 0.0071 |
| All seven centred: RULE_BEATS_SEARCH | **0.0385** | 0.029 |
| All seven centred: RULE_AT_MORE_CALLS_BETTER | 0.010 | 0.021 |
| All seven centred: SEARCH_DOMINATES | 0 | at most 0.0071 |
| One comparison centred, the other six at twice their development mean: SEARCH_DOMINATES | 0.001-0.0065 by comparison | at most 0.0071 |
| Skew stress: as above, but the centred comparison is +1 (the rule wins a whole answer) on 2% of tables and -0.0204 on the rest: SEARCH_DOMINATES | **0.032-0.0395** by comparison | at most 0.0071 |

Readings: the percentile bootstrap is anti-conservative toward RULE_BETTER under these
differences, which are skewed (a few tables where the rule wins), so RULE_BEATS_SEARCH's measured
size, about 0.04, exceeds its nominal 0.029 but stays under 0.05. SEARCH_DOMINATES is
conservative when the differences resemble development's (at most 0.0065 with one comparison at
zero), but when a rule wins large on a few tables, as in the stress case, a wrong SEARCH_DOMINATES
reaches about 0.04, still under 0.05. A verdict is read with these measured sizes (section 7.1).

**H-B (descriptive, D116; its resolution, not a decision's power).** The exact power of the exact
test over 347 questions, at a discordance rate r (the share
of questions where BM25 top 4 and all 8 disagree) and a share s of discordant pairs favouring BM25
top 4 (`mcnemar_power`; symmetric in s and 1 - s; `power.json`, `paired.h_b`). At the development
rate (4 of 63, r = 0.0635): 1.00 at s = 0 or 1, 0.98 at s = 0.1 or 0.9, 0.78 at s = 0.2 or 0.8,
0.39 at s = 0.3 or 0.7, and 0.03 at s = 0.5 (the size). Section 1.2 already fixes the sign (s
below 1/2) and a net count of at least 17 for all 8; the test then rejects unless there are more
than 67 discordant pairs (`power.json`, `conditional_on_am1_published_counts`).

**H-C.** At the development rate (1 discordant pair in 63, r = 0.016) with every discordant pair
favouring the rule, power is 0.47; at r = 0.02, 0.69; at r = 0.04, 0.99 (`paired.h_c`).
Conditioning instead on AM1's published count (BM25 top 4 wrong on exactly 86 retrieved tables,
the only tables where the rule can gain), with each of those 86 tables converted to a right answer
with probability q and c pairs against the rule
(`conditional_on_am1_published_counts.retrieved.h_c_power_by_c`):

| c (pairs against) | Test rejects when | q = 0.02 | q = 0.05 | q = 0.1 | q = 0.2 |
|---:|---|---:|---:|---:|---:|
| 0 | b ≥ 6 | 0.008 | 0.26 | 0.87 | 1.00 |
| 1 | b ≥ 8 | 0.000 | 0.07 | 0.64 | 1.00 |
| 2 | b ≥ 10 | 0.000 | 0.01 | 0.36 | 0.99 |

On development q was 1 of 5 and c was 0. The design detects a conversion rate of about 1 in 10 of
the tables BM25 top 4 gets wrong if c is 0 (power 0.87), less reliably if one or two abstaining
top-4 replies were judged correct (0.64, 0.36), and is unlikely to detect 1 in 20 in any case.

## 10. Seeds

200 seeds for the sampled rules, 42 to 241 (section 6.2; AM1's 42-44 and AM1b's 42-61 among
them). Bootstrap: numpy `default_rng(42)`. Power simulation: numpy `default_rng(43)`. Size
simulation: numpy `default_rng(44)`. Direct
search, H-B and H-C involve no random draw. No unseeded randomness.

## 11. Compute plan

CPU only, no GPU, no Slurm GPU allocation. `extract` reads one reader pass and its judge
(190,156 requests; AM1d's extract of 126 pools took under a minute) and `analyze` computes 200
seeds of three sampled rules on 539 non-constant tables (the development dry run, 89 tables, took
about 15 s of CPU). Both run on the host's login node, outside Slurm, as AM1's CPU steps did, in
minutes. Under D110 another project's inference jobs hold some GPUs; this registration needs none.

## 12. Data handling

The held-out replies, the study artifact and the features stay on the host. `extract` writes the
features (per request: label, token count, log-prob sums, abstention flag and pattern name, reply
class id, SHA-256 of the normalized reply; no text) to a host-only directory and refuses a
directory inside the repository. The repository gets `results.json`, `per-table.json.gz` (ids,
question types, masks, utilities, regrets, differences and reads; no text) and `tables.md` from
`analyze`, and the text-free stdout of `extract` (its validation counts and the features' digest).

## 13. Exclusions and infrastructure failures

No question is excluded for its outcome. The 347 questions are AM1's confirmatory set (Step 0's
eight demo questions were excluded there before any run). Constant tables are outside H-A by
definition and inside H-B and H-C. AM1 had no incomplete table; any incomplete table now is a void
(V2), not an exclusion. A crash of `extract` or `analyze` before it writes its outputs is rerun
with the same commands at the same commit; the outputs are deterministic, so a rerun that
completes is byte-identical.

## 14. Reported regardless of outcome

- H-A on both arms: every comparison's mean difference, 95% interval, decision bounds, Monte Carlo
  standard error, classification and the verdict; every rule's regret, calls and 95% interval;
  direct search's regret at 8, 9, 16, 26, 38, 64 and 70 calls (and its full exact curve per table);
- H-C on both arms: b, c, the accuracies, the difference with both intervals, the exact p-value
  and the reading (or VOID with its named error);
- H-B on both arms, as a description (D116): b, c, the accuracies, the difference with both
  intervals, the exact p-value and the description label; nonabstain-BM25 against all 8, also as
  a description;
- the stop rule's reads (section 6.6) and the descriptive outputs of section 6.7 by question type;
- every validity check of section 8 with its counts, and the features' provenance;
- the disclosures of section 1, including that H-B's direction was known before the run and that
  the run carries no gauntlet score; every deviation.

## 15. What development fixed in this design: the development selftest

Before the freeze, the code ran on development data only, at commit `ff935a86` (after check 2's
fixes), on the platform of record with `--python 3.14.6`, in a new host directory deleted
afterwards (`program/evidence/2026-10-16/am1-keepset-search-dev-selftest/README.md`). It
reproduced AM1b's and AM1d's committed numbers wherever this code overlaps them, by exact
equality: 19 of 19 checks pass (`selftest.json`). It also ran the full analysis on the
development tables and replies as a dry run; two runs were byte-identical. The whole test suite
on the host: 3,452 passed, 66 skipped, and 2 failed in another experiment's tests
(`test_r04_*`), which fail identically on `main` there. In short:

- AM1b, per table and in aggregate, at B = 4 on both arms (89 tables): direct search's exact
  curve, leave-one-out, greedy backward, the random set and retrieval rank, and SNIPW-64,
  MSR-Banzhaf-64 and permutation Shapley-16 seed by seed at AM1b's 20 seeds, with AM1b's means,
  95% and 99% intervals and rule-minus-direct differences (24 of 24 aggregate rows);
- AM1d: `extract` on job 1411 reproduces AM1d's feature file pool for pool (126 of 126; AM1d's
  file pinned at `cb678e3b...`) and its validation record; the analysis reproduces AM1d's
  per-table choices (126 of 126), accuracies with intervals (36 of 36), abstention counts, stop-rule
  reads and the exact sign tests its README quotes (4 vs 0, p = 0.125; 5 vs 0, p = 0.0625; 1 vs 0).

Development also set: the 200 seeds (AM1's 3-seed SNIPW-64 was off by 0.020 from AM1b's 20-seed
mean); the Monte Carlo margin; the 26-call point (greedy selection's cost, where direct search's
development regret, 0.024, is already below every credit rule's at any cost, the lowest being
exact Banzhaf's 0.031); and H-C's single rule (AM1d's best in sample).

## 16. Code of record (at the draft revision; re-pinned at the freeze)

The fill commit re-pins every row; a row that changes is reviewed before the freeze. In held-out
mode the script parses this table and refuses to run unless every file matches.

| File | Role | SHA-256 |
|---|---|---|
| `scripts/memcredit_keepset_search.py` | this registration's analysis: gate, extract, analyze, development selftest and power | `3fbb804328bd310a6c8626f408d0d1b44a4624f06829a0762e3afc6134add584` |
| `tests/test_memcredit_keepset_search.py` | its tests: exact order-statistic expectation, exact McNemar test and its interval, H-A per table and verdict, H-C's stop rule, the gate and the pins | `6ab16170cfef0c7c0b891fa45f4867a17e3ff2a69231dc5b8504cb2abc343e83` |
| `scripts/memcredit_cost_curve.py` | AM1b's decoding, memoized calls, rules, greedy search and exact direct-search curve | `431f4cb21ccd398e1433e29a5b40c1a697d48b9aecc5fc728956f819e28c9bab` |
| `scripts/memcredit_label_free.py` | AM1d's abstention list, join, features, BM25 order and stop rule | `721015de434021a72ab3bbbab5e91d0de39a2fc359df7283068f83026dcb9d8f` |
| `scripts/memcredit_analyze.py` | AM1's join (`join_rows`, `pool_views`) and artifact loader | `5444104d3c760b17f311656f4e0dbd50b2b154c89d806f1e4aa2ab6791fb0f34` |
| `scripts/memcredit_study.py` | AM1's pass reader (`load_pass`) | `f27ecd21e769655cddc1e9b06ee8f4c7c4ee8494348b4fc73dba7c68fdb66bb3` |
| `scripts/memcredit_step0.py` | imported by `scripts/memcredit_study.py` (pass files) | `57f2e4bbbd11bf750ff224852ba5dd19923ecb3decfde74d23a6913a7f9a7227` |
| `harness/g2_pilot.py` | imported by `scripts/memcredit_study.py` and `scripts/memcredit_step0.py` | `8c685425522377de9fbab92fac02aea321bb2b3bd69d82d2118c4ecea49f6599` |
| `harness/__init__.py` | the harness package | `17dac2704be26050e324aa36aba6d2c855abbd592e4d72f750b9b6e9c4399fec` |
| `harness/memcredit.py` | set functions, keep-set regret, Clopper-Pearson, answer normalization | `ad0964d0caab382b5541b64d56a30105bc306d2286f6e62137b1eff9121dd607` |
| `harness/memcredit_study.py` | configs, split, confirmatory set, estimators, bootstrap | `14a97d826ba619e23ea9686e2d2d57149d9f0119df3f80240843178953cf301b` |
| `experiments/am1/am1-memory-credit-v1.yaml` | AM1's registration config (confirmatory set, pools) | `8466d6d42ace1477bb9b2377de8ed67027502ff11b179a369eed352fda212069` |
| `experiments/am1/memcredit-study-v1.yaml` | AM1's pilot config (development selftest) | `ecdb5c11ff4eaf757ec6712c6f2c75d61c79882bb3d418202b7143abf90793db` |
| `experiments/am1/memcredit-split-v1.json` | the split | `4fa1b774d4131080855d668ac8f00f5cb07d49cf741f2051d5f8d96577edb3e3` |
| `tests/test_memcredit_cost_curve.py` | AM1b's tests | `fd162d8a401f7eab7f56a36302263032604085329bd736678c8cac4849f621f3` |
| `tests/test_memcredit_label_free.py` | AM1d's tests | `139bb5098735a06a6c68765e02a3889426b617d074efc31fbbd8e78bbb7ee809` |
| `scripts/preregister.py` | the ledger | `21fc3ef0ed0958b1600ce742c3b4f8d557d0a298635acb20342710eb814b2c0d` |

The features record the SHA-256 of this script and the nine repository modules `extract` imports
(`FEATURE_CODE`, section 8's V5): `scripts/memcredit_cost_curve.py`,
`scripts/memcredit_label_free.py`, `scripts/memcredit_analyze.py`, `scripts/memcredit_study.py`,
`scripts/memcredit_step0.py`, `harness/__init__.py`, `harness/g2_pilot.py`, `harness/memcredit.py`
and `harness/memcredit_study.py`.

Commands of the registered run, on the host, in the `uv` environment of a `git archive` export of
the freeze commit (AM1d's usage), run from inside EXPORT_DIR. The names in capitals are host
paths, all new sibling directories under `~/cotcodec-runs/stage0/am1-keepset-search-v1/`:
- EXPORT_DIR is `.../export-FREEZE`, FREEZE being the freeze commit's short hash;
- PRIVATE_DIR is `.../private`, host only;
- OUTPUT_DIR is `.../out`;
- LOG_DIR is `.../logs`;
- HELDOUT_RUN is `~/cotcodec-runs/stage0/am1-memory-credit-v1/runs/main/1458/am1`;
- HELDOUT_ARTIFACT is `~/cotcodec-runs/stage0/am1-memory-credit-v1/study-artifact.json`.

`extract` refuses a PRIVATE_DIR inside the repository it runs from, so EXPORT_DIR is a sibling of
PRIVATE_DIR, OUTPUT_DIR and LOG_DIR, never their parent.

**Platform of record.** The host (x86_64 Linux), uv's CPython 3.14.6 (`--python 3.14.6` on every
command), and numpy 2.5.2 as the freeze commit's `uv.lock` pins it for Python 3.12 and later. The
registered outputs and the verifier's rerun are made there. A run on a Mac may differ in the last
digit of the exact conditional intervals (`harness.memcredit.clopper_pearson` sums binomial terms
with the platform's `lgamma`) and in the `environment` field of `results.json`; no reading depends
on either.

Each command writes its standard output and error to a log in LOG_DIR and appends its exit code:

```bash
cd EXPORT_DIR
uv run --offline --python 3.14.6 python scripts/memcredit_keepset_search.py extract \
  --split heldout --run-dir HELDOUT_RUN --evidence HELDOUT_ARTIFACT --private-dir PRIVATE_DIR \
  > LOG_DIR/extract.log 2>&1; echo "exit $?" >> LOG_DIR/extract.log
uv run --offline --python 3.14.6 python scripts/memcredit_keepset_search.py analyze \
  --split heldout --features PRIVATE_DIR/features-heldout-1458.json.gz --output-dir OUTPUT_DIR \
  > LOG_DIR/analyze.log 2>&1; echo "exit $?" >> LOG_DIR/analyze.log
uv run --offline --python 3.14.6 --extra dev pytest -q tests/test_memcredit_keepset_search.py \
  > LOG_DIR/pytest.log 2>&1; echo "exit $?" >> LOG_DIR/pytest.log
```

If `extract` or `analyze` stops with a `VOID (H-C, V3)` or `VOID (H-C, V5)` error (section 8), the
registered H-C void path replaces the second command:

```bash
uv run --offline --python 3.14.6 python scripts/memcredit_keepset_search.py analyze \
  --split heldout --h-c-void 'REASON' --output-dir OUTPUT_DIR \
  > LOG_DIR/analyze.log 2>&1; echo "exit $?" >> LOG_DIR/analyze.log
```

REASON is the failing command's error line in its log, the line that begins `error: `, without
that prefix and with the home directory written as `~`. It is passed in single quotes, each single
quote inside it written as `'\''`, so that the shell passes the text unchanged. The verifier passes
the same string.

The committed logs shorten the home directory to `~`: `extract` prints the features' absolute
path.

The defaults are the registered settings: 200 seeds from 42, 10,000 bootstrap resamples with seed
42. `analyze` runs once; a fresh verifier reruns it on the platform of record from a new export,
and the outputs must be byte-identical.

## 17. Freeze checklist

Before the freeze, by the orchestrator:

1. Two independent pre-freeze checks of this file and the code of section 16 (D115), by reviewers
   that did not draft them, and the corrections they require; their dispositions go in section 19.
2. The gauntlet question: resolved by D115. No gauntlet wave runs, and the run carries no gauntlet
   score (section 1.5).
3. If any code of section 16 changed after the development selftest, rerun the selftest and update
   its record.
4. Re-pin section 16 in a fill commit; run the tests locally and on the host.
5. Confirm that `git diff ea9d57dc -- program/evidence/2026-10-16/am1-confirmatory` is empty at
   the fill commit, and on the host that the files of section 4 still have their digests.
6. The fill commit also rewrites the status line (line 3) to the frozen wording that
   `am1-memory-credit-v1` uses: "**Status: frozen in `program/preregistrations/ledger.jsonl`; see
   the ledger row for the freeze time and `git_head_at_freeze`.**". The file must then contain no
   to-be-decided marker and no placeholder in angle brackets, which the freeze command rejects.
   The orchestrator makes this edit, not the drafter.
7. The ledger row, by `uv run python scripts/preregister.py freeze am1-keepset-search-v1
   program/preregistrations/am1-keepset-search-v1.md`, in a commit that adds only that row. A test
   freezes this file into a scratch ledger, so the command's text checks pass.

After the freeze: export the freeze commit to the host, run section 16's commands once, commit the
text-free outputs and `extract`'s stdout, and have a fresh verifier rerun `analyze` from a new
export.

## 18. Priors (for the record; not tested)

- **H-A:** SEARCH_DOMINATES. Development differences are all negative. On held-out,
  leave-one-out, SNIPW-64 and permutation Shapley-16 (seeds 42-44) lost more than on development,
  while exact Shapley and exact Banzhaf lost less (section 1.4); the random keep set lost more
  (0.625 against 0.576), so direct search's held-out curve may sit higher too. The weak links are
  greedy backward (A7) and MSR-Banzhaf-64 against 26 calls (A5).
- **H-B (descriptive):** all 8 ahead of BM25 top 4 by at least 17 questions (0.049), from
  section 1.2; no decision attaches to it.
- **H-C:** uncertain. On development, nonabstain-BM25 converted 1 of the 5 tables BM25 top 4 got
  wrong, with c = 0; at that rate over the 86 held-out tables the test rejects with probability
  near 1 whether c is 0, 1 or 2, and at a quarter of it (q = 0.05) about one time in four with
  c = 0 and rarely otherwise (section 9). The reads: on development, 1.21 on average over
  non-constant retrieved tables and 12.87 over all 63 questions (most of them pools where no
  4-subset answers).
- **Descriptive:** abstention around half of the 4-subset replies (development: 54.5% retrieved,
  58.9% gold); oracle ceiling well above all 8 (development: 0.587 against 0.444 over every
  retrieved question).

## 19. Review log: the independent checks

Two independent, sequential checks are required before the freeze (D115, D116).

### Round 1

Pre-freeze check 1 ran on `747623cd` and found the file ready to freeze after fixes: one blocking
item, three major, nine minor and two for information. The orchestrator then demoted H-B to
descriptive (D116, `55b49dbe`). The fixes are commits `8c2f4ad7` (code, tests, this file) and
`f97697b5` (this section, and one new test made to ignore the packages of a virtual environment
inside a host export), and the commit that carries the refreshed development selftest (section
15). Nothing of the held-out data was decoded; the selftest used development data only, in new
host directories that were deleted afterwards.

| Item | Finding | Disposition |
|---|---|---|
| B1 | The gate test asserted that the real ledger had no row, so the registered pytest command would fail after the freeze, and without that assert the next line would decode the held-out tables. | Fixed: the gate is tested against a scratch ledger and a scratch copy of this file, both for refusal and for opening (`gate(split, ledger, registration)`); `load_tables("heldout")` is only called on a scratch file, with `Path.read_bytes` made to fail, so a read before the gate would fail the test. |
| M1 | Section 8 said a V3 or V5 failure voids only H-C, but `analyze` refused held-out runs without features and raised before H-A on a pool-count or provenance failure. | Fixed: the registered void path `analyze --h-c-void REASON` (sections 8 and 16) records H-C as VOID and computes H-A, H-B and the descriptive outputs from the tables; every H-C input failure in `extract` and `analyze` is a named `VOID (H-C, V3)` or `VOID (H-C, V5)` error (missing or changed pass file, unreadable or truncated features, pools that do not match), tested; the features are written atomically; `distinct_replies` is required on every table and reproduced on all of them. |
| M2 | H-B was still presented as a decision. | Fixed: H-B is a block of its own (`h_b_descriptive`, `decides: false`) outside the verdicts, its label is a description, the markdown section is "H-B (descriptive, D116; no decision)", the docstring says so; sections 1.3, 6.7, 7.2, 14 and 18 are reworded. |
| M3 | RULE_BEATS_SEARCH could fire on a fewer-calls comparison, where the rule read 57-83 calls against search's 26. | Fixed: RULE_BEATS_SEARCH comes only from the matched comparisons A1, A2, A4 and A7; a RULE_BETTER on A3, A5 or A6 gives RULE_AT_MORE_CALLS_BETTER, which blocks SEARCH_DOMINATES and licenses nothing at equal calls (section 7.1, `ha_verdict`, the power simulation, tests). |
| m1 | "25 or more" should be 26. | Fixed in section 1.2, with the two boundary p-values. |
| m2 | The code pins missed `scripts/memcredit_step0.py`, `harness/g2_pilot.py` and `harness/__init__.py`; `FEATURE_CODE` missed `scripts/memcredit_cost_curve.py`. | Fixed: both now cover this script and all nine repository modules `extract` imports; a test checks the list against a fresh interpreter's imports and that every one is pinned. |
| m3 | Section 7.1 misstated AM1's alpha. | Fixed: AM1 spent 2.5% per direction; here each verdict's error is at most 5%. |
| m4 | H-C's power assumed c = 0. | Fixed: power at c = 0, 1 and 2 (section 9; `h_c_power_by_c`), and section 18's prior. |
| m5 | Missing disclosures: G2's "I don't know." result, the 120 hand-checked held-out replies, the full-precision counts. | Added to sections 1.1, 1.2 and 1.6. |
| m6 | Section 1.2 should give the published bounds on direct search. | Added: exact bounds under AM1's published constraints, computed by `direct_search_bounds` (equal to check 1's), with the note that the 57-call bound nearly excludes RULE_BETTER on A2. |
| m7 | Section 16 did not name the export and output directories, and the private-directory guard constrains them. | Fixed: EXPORT_DIR, PRIVATE_DIR and OUTPUT_DIR are named siblings, and the committed logs' `~` is stated. |
| m8 | Partial or unreadable features and missing pass files gave tracebacks. | Fixed with M1: named V3 errors, tested end to end. |
| m9 | H-C's reading lacked a scope. | Fixed in section 7.3, matching H-A's. |
| Info | Permutation Shapley-16 read 68-94 subsets on development; H-A's reading should say it holds in expectation. | Both stated (sections 6.3 and 7.1). |

### Round 2

Pre-freeze check 2 ran on `1accdd93`. It confirmed every round-1 fix in the code, rehearsed
section 16 on the host with no failing command, and found the file ready to freeze after fixes:
no blocking item, one major, ten minor and three for information. The fixes are commit
`ff935a86` (code, tests, this file) and the commit that carries this section and the refreshed
development selftest (section 15). Nothing of the held-out data was decoded; the selftest used
development data only, in a new host directory that was deleted afterwards.

| Item | Finding | Disposition |
|---|---|---|
| 1 (major) | The per-direction error rates of section 7.1 are nominal; under the skewed differences the percentile bootstrap measured 0.009-0.022 per comparison against 0.0071, a false RULE_BEATS_SEARCH of 0.041 against the stated 0.029, and a false SEARCH_DOMINATES up to 0.042 in a skew stress case. | Fixed: section 7.1 calls the rates nominal and quotes the measured ones. `power` now has a deterministic size block (`size_simulation`; 2,000 runs x 2,000 resamples, seed 44): all seven centred, one centred among six at twice the development effect, and the skew stress case. Its numbers are in `power.json` and section 9: per-comparison RULE_BETTER 0.009-0.0185, SEARCH_BETTER 0.0025-0.0085, false RULE_BEATS_SEARCH 0.0385, false RULE_AT_MORE_CALLS_BETTER 0.010, false SEARCH_DOMINATES 0 (all centred), 0.001-0.0065 (one centred) and 0.032-0.0395 (stress). The percentile bootstrap is kept. |
| 2 | `zlib.error` was missing from the H-C read errors. | Fixed: `READ_ERRORS` includes `zlib.error`; the test corrupts 40 features files mid-stream and injects a `zlib.error`, and it fails without the fix. (On a Mac's Python 3.13 the streaming reader turned the corruptions into CRC errors, so the injection is what tests the fix there.) |
| 3 | The estimand read as a fixed finite mean. | Fixed in sections 6.3 and 7.1: the expected D_j over questions drawn as AM1's confirmatory set was, estimated by the 251-table mean, questions resampled. |
| 4 | The order-statistic wording was off by one. | Fixed: 0-based indices 71 and 9,928, the 72nd smallest and the 72nd largest. |
| 5 | The interpreter was not pinned. | Fixed: `--python 3.14.6` on every `uv run` of section 16, and the platform of record named (the host, x86_64 Linux, uv's CPython 3.14.6, numpy 2.5.2 from `uv.lock`), with what a Mac run may differ in. The selftest ran with those flags. |
| 6 | Section 16 did not capture logs or define REASON. | Fixed: each command logs to LOG_DIR, a sibling directory, and appends its exit code; REASON is the `error: ` line's text with `~` for the home directory, single-quoted with embedded quotes escaped, passed identically to the verifier. |
| 7 | The freeze checklist lacked the status-line rewrite. | Added as item 6 of section 17, for the orchestrator to do in the fill commit; this file's status line is unchanged. |
| 8 | Three statements said no test reads the held-out tables, but one test hashes the committed gz. | Reworded in section 8, the test module's docstring and the inline comment: no test decodes the held-out tables; one test hashes the committed gz to check its pin. |
| 9 | NONABSTAIN_HELPS could be read as beating all 8. | Section 7.3 now says it does not; that comparison is a description. |
| 10 | The second judge called "I don't know." correct on 49 of 347. | Disclosed in section 1.1; H-C's scope keeps "this judge". |
| 11 | Gold-arm labels looked like decisions. | Fixed: `h_c.gold` carries `descriptive_label` with `decides: false`, H-A's gold arm `descriptive_label_no_decision`, and `tables.md` prints "Descriptive label (no decision)"; section 6.7 says so; tested. |
| Info | The hand-check file's reply digests; A4's and A7's open signs; INCONCLUSIVE's other classifications. | Added to sections 1.1, 1.2 and 7.1. |
