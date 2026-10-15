# AM1d: can a label-free utility choose keep sets by search? (exploratory, development data only)

**EXPLORATORY.** AM1d is step 1 of D113's next steps (`program/decisions.md`). It ran on the
host CPU with no GPU, from the AM1 development pilot's recorded reader pass. No decision rule
applies.

- **Development data only.** The data are the 63 development questions in two arms (126 tables).
  **No confirmatory data was used.**
  - The script refuses any path that contains `am1-confirmatory` or `am1-memory-credit-v1`,
    after resolving symlinks, and it pins the SHA-256 of every input it reads.
  - The run scripts in `ops/` name only development inputs.
  - Locally, the access times of all 60 confirmatory JSON and gz files in this worktree are older
    than their checkout. They were never read here. This was checked by the independent checker.
  - On the host, most files under the confirmatory directories would not record a read (relatime),
    so access times cannot prove a negative there. The evidence on the host is the path refusal
    and the run scripts.
- **Raw pass used.** Job 1411, `reader-gpu0`: GPU 0, canonical order, compiled batch-invariant
  mode. Its labels come from job 1411's Qwen3-32B judge, `judge32-gpu0`. This is the pass whose
  labels made the committed tables. The eager replay (job 1441, `rd-eager-gpu0`, first 16
  questions) is used only for a sensitivity check.
- **The abstention pattern list was fixed before any result.** The four patterns below were
  committed at `7465903f` before the script had read any reply. A test pins their SHA-256
  (`031bee27...`).
  - The first results came from `7465903f`.
  - `ccd077e7` added post hoc diagnostics, marked as such below.
  - `5a31db61` changed only the calls column, so that it counts the call that produces the
    answer.
  - Every declared number is identical across the three commits, and the committed files come
    from `5a31db61`.
- **Reply text stayed on the host.** The per-request features sit in a host-only directory:
  log-probs, abstention flags, reply-class ids and SHA-256 digests of normalized replies. The
  committed files hold only numbers, question ids, masks and digests.

## Question

AM1b showed that when the judged utility u(S) can be queried, searching over keep sets beats
every per-memory credit rule. Judging needs the reference answer, so that search cannot be
deployed.

AM1d replaces u(S) by utilities computed only from the reader's own outputs under each subset S.
It asks whether search on such a utility can choose which 4 of 8 memories to keep well enough to
beat two zero-search baselines:

- BM25 top 4, which loses 0.132 on the retrieved arm (AM1b);
- the full pool of 8.

## Answer (retrieved arm, keep 4 of 8, 38 non-constant tables)

| Rule | Reader calls | Accuracy | minus BM25 top 4 [95% CI] | minus all 8 [95% CI] |
|---|---:|---:|---|---|
| BM25 top 4 | 1 | 0.842 | | +0.105 [+0.026, +0.211] |
| all 8 (no pruning) | 1 | 0.737 | -0.105 [-0.211, -0.026] | |
| best label-free in sample: `nonabstain@70` | 70 | 0.868 | +0.026 [+0.000, +0.079] | +0.132 [+0.026, +0.237] |
| `nonabstain@8` | 8 | 0.775 | -0.067 [-0.143, +0.012] | +0.038 [-0.058, +0.140] |
| `agree_full@70` | 71 | 0.789 | -0.053 [-0.132, +0.000] | +0.053 [+0.000, +0.132] |
| `nonabstain_conf_mean@70` | 70 | 0.711 | -0.132 [-0.289, +0.026] | -0.026 [-0.184, +0.132] |
| `conf_mean@70` | 70 | 0.105 | -0.737 [-0.868, -0.579] | -0.632 [-0.789, -0.474] |
| `vote@70` | 70 | 0.237 | -0.605 [-0.763, -0.447] | -0.500 [-0.658, -0.342] |
| oracle search at 16 calls (needs labels) | 16 | 0.928 | +0.086 [+0.006, +0.183] | +0.191 [+0.073, +0.320] |

- **No label-free search beats BM25 top 4 with a 95% interval above zero.** BM25 top 4 is ahead
  of the full pool by +0.105 [+0.026, +0.211]. That rests on 4 tables against 0 (exact sign test
  p = 0.125), so it is a lead, not a finding (see "The deployable question").
- **The best rule in sample is `nonabstain@70`.** It reads all 70 4-subsets and keeps the
  best-ranked one by BM25 whose reply is not an abstention.
  - Its gain over BM25 top 4 is one table of 38, a single-session-preference question; the
    judge scores those against a rubric.
  - It keeps BM25 top 4 whenever that set's reply does not abstain, which is 36 of 38 tables.
  - Abstaining replies are almost never judged correct, so it can hardly do worse than BM25 top
    4. The interval's lower end of 0.000 reflects this.
  - A BM25-ordered stop rule reaches the same choice in 1.21 reads on average, and at most 8 (post
    hoc, below).
- **With random draws below 70 calls, every label-free search is below BM25 top 4 on the point
  estimate.**
  - `nonabstain` loses 0.067 at 8 calls and 0.014 at 38 calls; both seeded intervals include 0.
    The seeded means at 8 calls run about 2 standard errors high: the 50 seeds share their draws
    across utilities. The checker computed the exact expectation over draws by order statistics:
    accuracy 0.761, and -0.081 [-0.157, -0.005] against BM25 top 4, so at 8 calls the interval
    lies below zero. The script does not yet emit exact expectations.
  - Random draws often miss BM25 top 4. Non-abstention then picks among the answering subsets by
    BM25 rank alone.
- **Confidence picks the wrong sets, and more search makes it worse.** Keeping the most
  confident reply is right on 0.208 of tables at 8 calls and 0.105 at 70 calls (mean log-prob).
  - The reader's abstentions are its most confident replies (post hoc, added at `ccd077e7`). The
    median mean token log-prob is -5e-6 for abstentions, -0.0037 for correct answers and -0.013
    for wrong ones.
  - 55% of the 4-subset replies on this arm abstain.
  - Within a table, confidence ranks the 4-subsets below chance: mean AUROC 0.33 for u.
- **The subset vote fails for the same reason.** The majority reply is usually an abstention: 0.318
  at 8 calls, 0.237 at 70.
- **Agreement with the full-pool reply lands near the full pool.** It scores 0.741-0.789, within
  0.053 of all 8, and 0.053-0.101 below BM25 top 4. The intervals lie below zero at 9-39 calls.
- **Non-abstention followed by confidence or vote** scores 0.711-0.738. That is about the full
  pool's accuracy and 0.10-0.13 below BM25 top 4.
  - Among replies that do not abstain, confidence separates right from wrong only weakly: mean
    within-table AUROC 0.61 (post hoc).
- **Corrected for the choice of rule, the gain is small or negative.** Pick the utility on half
  the questions and score it on the other half, over 200 random splits:
  - the held-out gain over BM25 top 4 is -0.079 at 8 calls and -0.029 at 38 calls;
  - it is +0.025 at 70 calls: at least 0 in 95% of the held-out halves and positive in half of
    them. The lowest is -0.368, from the one split that picked `nonabstain_conf_mean@70`. This
    minimum is not in `results.json`. It was computed on the host, and the checker reproduced it
    independently.
- **The gold arm (51 tables) shows the same pattern.**
  - BM25 top 4 scores 0.706 and all 8 scores 0.725.
  - `nonabstain@70` and `agree_full@70` both reach 0.765: +0.059 [+0.000, +0.137] over BM25 top
    4, which is three tables.
  - Confidence and vote fall to 0.06-0.19.

**The deployable question.** Does pruning by label-free search keep or improve accuracy compared
with BM25 top 4 and with all 8? On this reader and prompt:

- **Against all 8, retrieved arm:** pruning is ahead on the point estimate, but the evidence is
  thin. BM25 top 4 is +0.105 [+0.026, +0.211] over all 8 on the 38 non-constant tables, which
  is +0.063 [+0.016, +0.127] over all 63 questions. That rests on 4 tables favouring top 4 and
  0 favouring all 8. The percentile bootstrap excludes 0, but an exact sign (McNemar) test gives
  p = 0.125 two-sided. `nonabstain@70` over all 8 is 5 tables against 0 (p = 0.0625), and
  `nonabstain@38` rests on the same tables. Treat "pruning beats the full pool" as a lead for the
  held-out registration, not a finding.
- **Against all 8, gold arm:** no label-free rule's interval lies above all 8, and BM25 top 4 is
  0.020 below it (-0.016 [-0.079, +0.048] over all 63 questions; 2 tables against 3).
- **Against BM25 top 4:** label-free search keeps accuracy only through non-abstention.
  - `nonabstain@70` ties BM25 top 4 or improves it by a table (three on the gold arm), and no gain
    is detectable.
  - On the retrieved arm, every utility built on confidence, vote or agreement loses accuracy
    against BM25 top 4.
  - On the gold arm, agreement (26-70 calls) and non-abstention with vote (38-70 calls) are above
    BM25 top 4 on the point estimate. Both reach 0.765 at 70 calls, and every interval includes 0.

The usable label-free signal is whether the reader abstains, and it adds information only in the
few pools where BM25 top 4 abstains. Oracle search shows how much room is left: 0.928 at 16
calls, 0.974 at 70.

## Step 1: the join is validated

The tables were built by `memcredit_analyze.join_rows`, at the pilot's analysis commit
`9ecc914c`. Since then the function has changed only in how it handles a missing pass. Its join
works as follows:

1. A request index maps to (question index, arm, kind, mask) through
   `harness.memcredit_study.request_table`.
2. The reply is the reader pass's text for that index, when the reply finished with stop or
   length.
3. The label is the primary judge's label of the judge item keyed by (question index, stripped
   reply).

AM1d calls that function unchanged. It then reruns the same join keeping tokens and log-probs,
and stops on any difference.

| Check | Result |
|---|---|
| The study artifact and the 7 raw files used (reader pass, judge pass, judge items) match the pilot's committed SHA-256 | 8 / 8 |
| Joined labels reproduce `values_hex` (the committed 256-bit vector; mask m is bit m) | **126 / 126 tables** |
| The joined distinct-reply count equals the committed `distinct_replies` | 126 / 126 |
| AM1d's own join, which keeps tokens and log-probs, agrees with `join_rows` on reply text and label | 34,524 / 34,524 requests |
| Table requests that have a reply and a label | 32,256 / 32,256 |
| Missing (NaN) log-probs | 0 |
| BM25 top 4 is one keep set and has AM1b's `retrieval_rank` regret | 126 / 126 (89 compared with AM1b's per-table regrets, in the tests) |
| Exhaustive search (m = 70) gives the same set under every seed, and its regret equals `harness.memcredit.keep_set_regret_range` | every table, every utility |

## Design

### Label-free utilities

Each utility scores a subset S from reply(S) alone; a larger score is preferred.

| Utility | Score | Reader calls at budget m |
|---|---|---:|
| `conf_mean` | mean sampled-token log-prob of reply(S) | m |
| `conf_sum` | summed sampled-token log-prob | m |
| `nonabstain` | 1 unless reply(S) matches the abstention list | m |
| `agree_full` | 1 when `normalize_answer(reply(S)) == normalize_answer(reply(all 8))` | m + 1 |
| `vote` | (number of queried subsets with the same normalized reply, mean log-prob) | m |
| `nonabstain_conf_mean` | (non-abstention, mean log-prob) | m |
| `nonabstain_conf_sum` | (non-abstention, summed log-prob) | m |
| `nonabstain_vote` | (non-abstention, vote count, mean log-prob) | m |

All eight were declared at `7465903f`. `nonabstain_vote` is one combination beyond the five
utilities AM1d was asked to test.

- **Confidence.** The pass recorded the float32 log-prob of each sampled token (`logprobs: 0`).
  Every generated token counts, including the end-of-turn token: every 4-subset reply generated it,
  and none reached the 64-token cap. Sums use `math.fsum`.
- **Normalization.** `harness.memcredit.normalize_answer` (lowercase, punctuation to spaces,
  articles removed, number words as digits) is applied to the stripped reply. It is used by
  `agree_full` and `vote`, and by the abstention patterns.
- **The abstention list.** These are regular expressions searched in the normalized reply. An
  empty reply also counts as abstaining. The reader's prompt asks it to say "I don't know" when
  the memories lack the answer.

  | Name | Pattern |
  |---|---|
  | `i_dont_know` | `\bi (?:don t\|do not\|dont) know\b` |
  | `cannot_answer` | `\b(?:cannot\|can t\|can not\|unable to\|not able to) (?:answer\|determine\|tell\|say\|know\|find\|recall\|be determined)\b` |
  | `no_information` | `\b(?:no\|not enough\|insufficient) (?:information\|info\|details\|data)\b` |
  | `not_in_memories` | `\b(?:not (?:mentioned\|provided\|specified\|stated)\|(?:do\|does\|did) not (?:contain\|mention\|include\|specify)\|(?:don t\|doesn t\|didn t) (?:contain\|mention\|include\|specify))\b` |

  Over the 4,410 4-subset replies per arm, the patterns flagged these replies:

  | Arm | Flagged | `i_dont_know` | `not_in_memories` | `no_information` | `cannot_answer` | Judged correct |
  |---|---:|---:|---:|---:|---:|---:|
  | retrieved | 2,405 | 2,386 | 19 | 0 | 0 | 2 |
  | gold | 2,599 | 2,568 | 26 | 4 | 1 | 2 |

### Search

- **Draws.** For each table and seed, `random.Random(f"{seed}:{question_id}:{arm}:am1d-search")`
  orders the 70 4-subsets at random, and the first m are read (m = 8, 16, 26, 38, 70).
  - The draws are distinct (without replacement) and nested across m.
  - Every utility uses the same draws, so comparisons between utilities are paired.
- **Seeds.** There are 50 seeds, 42 to 91. The search at m = 70 is deterministic. Monte Carlo
  standard errors over seeds are at most 0.007.
- **Choice.** The search keeps the read subset with the best score.
  - **Ties go to the lower BM25 rank sum, then to the lexicographically smaller sorted ranks.**
    BM25 ranks are distinct within every pool, so this is a total order.
  - Binary utilities tie often, so the tie-break does much of their choosing. `nonabstain` keeps
    the best-ranked subset by BM25 among the read subsets that do not abstain.
- **Calls.** The calls column counts reader calls per question, including the call that produces
  the answer. A search answers with the chosen subset's reply, which it has already generated.

### Baselines and scoring

- **Zero-search baselines** make one reader call each:
  - BM25 top 4 (AM1b's `retrieval_rank` keep set);
  - all 8;
  - a uniformly random 4-subset (exact expectation over the 70).
- **Oracle search** (`oracle_search@m`) is AM1b's direct search on the judged utility, as an exact
  expectation. It needs labels, so it is a reference and not deployable.
- **Accuracy** is u(chosen), the Qwen3-32B judged correctness from the committed table.
- **Regret** is the best 4-subset's u minus u(chosen), AM1b's convention, reported on the
  non-constant tables only (38 retrieved, 51 gold).
  - For all 8 the regret can be negative: when the full pool is right and no 4-subset is.
- **Accuracy over all 63 questions per arm** is also reported, as the per-question rate a
  deployment would see. On the constant tables every rule scores 0.
- **Intervals** are 95% question-cluster bootstraps: `harness.memcredit_study.cluster_bootstrap`,
  10,000 resamples, seed 42. Each arm has one table per question.
- **Differences** against BM25 top 4 and against all 8 are paired by question.
- **Selection-adjusted gain.** For 200 random half-splits of the questions (seed 42), pick the
  utility with the highest mean gain over BM25 top 4 on one half and score it on the other, in
  both directions.

## Results: retrieved arm, keep 4 of 8, 38 non-constant tables (primary cell)

Accuracy is the mean over 50 seeds, with "se" the Monte Carlo standard error over seeds.
Differences are positive when the rule is more accurate.

| Rule | Calls | Regret [95% CI] | Accuracy [95% CI] | minus BM25 top 4 [95% CI] | minus all 8 [95% CI] |
|---|---:|---|---|---|---|
| bm25_top4 | 1 | +0.132 [+0.026, +0.237] | 0.842 [0.711, 0.947] | +0.000 [+0.000, +0.000] | +0.105 [+0.026, +0.211] |
| all_8 | 1 | +0.237 [+0.105, +0.368] | 0.737 [0.579, 0.868] | -0.105 [-0.211, -0.026] | +0.000 [+0.000, +0.000] |
| random_4 | 1 | +0.576 [+0.496, +0.652] | 0.398 [0.324, 0.474] | -0.444 [-0.541, -0.340] | -0.339 [-0.453, -0.221] |
| oracle_search@8 | 8 | +0.104 [+0.046, +0.172] | 0.870 [0.786, 0.939] | +0.028 [-0.049, +0.119] | +0.133 [+0.022, +0.254] |
| oracle_search@16 | 16 | +0.046 [+0.011, +0.096] | 0.928 [0.854, 0.983] | +0.086 [+0.006, +0.183] | +0.191 [+0.073, +0.320] |
| oracle_search@26 | 26 | +0.024 [+0.002, +0.060] | 0.950 [0.882, 0.996] | +0.108 [+0.022, +0.211] | +0.213 [+0.093, +0.346] |
| oracle_search@38 | 38 | +0.013 [+0.000, +0.038] | 0.961 [0.896, 0.999] | +0.118 [+0.026, +0.224] | +0.224 [+0.104, +0.357] |
| oracle_search@70 | 70 | +0.000 [+0.000, +0.000] | 0.974 [0.921, 1.000] | +0.132 [+0.026, +0.237] | +0.237 [+0.105, +0.368] |
| conf_mean@8 | 8 | +0.765 [+0.654, +0.866] | 0.208 [0.115, 0.314] (se 0.006) | -0.634 [-0.762, -0.499] | -0.528 [-0.671, -0.387] |
| conf_mean@16 | 16 | +0.821 [+0.712, +0.914] | 0.153 [0.068, 0.254] (se 0.004) | -0.689 [-0.816, -0.552] | -0.584 [-0.728, -0.439] |
| conf_mean@26 | 26 | +0.843 [+0.738, +0.932] | 0.131 [0.052, 0.226] (se 0.005) | -0.712 [-0.837, -0.574] | -0.606 [-0.749, -0.461] |
| conf_mean@38 | 38 | +0.854 [+0.748, +0.942] | 0.119 [0.043, 0.215] (se 0.004) | -0.723 [-0.849, -0.583] | -0.617 [-0.761, -0.469] |
| conf_mean@70 | 70 | +0.868 [+0.763, +0.974] | 0.105 [0.026, 0.211] | -0.737 [-0.868, -0.579] | -0.632 [-0.789, -0.474] |
| conf_sum@8 | 8 | +0.781 [+0.672, +0.878] | 0.193 [0.103, 0.295] (se 0.006) | -0.649 [-0.776, -0.515] | -0.544 [-0.688, -0.401] |
| conf_sum@16 | 16 | +0.837 [+0.731, +0.927] | 0.137 [0.056, 0.234] (se 0.003) | -0.705 [-0.830, -0.567] | -0.600 [-0.743, -0.454] |
| conf_sum@26 | 26 | +0.865 [+0.763, +0.948] | 0.109 [0.037, 0.197] (se 0.004) | -0.733 [-0.855, -0.595] | -0.628 [-0.769, -0.480] |
| conf_sum@38 | 38 | +0.880 [+0.777, +0.963] | 0.094 [0.024, 0.183] (se 0.003) | -0.748 [-0.871, -0.609] | -0.643 [-0.786, -0.492] |
| conf_sum@70 | 70 | +0.895 [+0.789, +0.974] | 0.079 [0.000, 0.184] | -0.763 [-0.895, -0.632] | -0.658 [-0.816, -0.500] |
| nonabstain@8 | 8 | +0.199 [+0.115, +0.295] | 0.775 [0.670, 0.867] (se 0.007) | -0.067 [-0.143, +0.012] | +0.038 [-0.058, +0.140] |
| nonabstain@16 | 16 | +0.175 [+0.091, +0.272] | 0.799 [0.694, 0.892] (se 0.005) | -0.043 [-0.106, +0.020] | +0.062 [-0.022, +0.155] |
| nonabstain@26 | 26 | +0.161 [+0.077, +0.262] | 0.813 [0.705, 0.905] (se 0.005) | -0.029 [-0.093, +0.037] | +0.076 [-0.009, +0.172] |
| nonabstain@38 | 38 | +0.146 [+0.061, +0.248] | 0.828 [0.717, 0.923] (se 0.004) | -0.014 [-0.073, +0.050] | +0.091 [+0.005, +0.189] |
| nonabstain@70 | 70 | +0.105 [+0.026, +0.211] | 0.868 [0.763, 0.974] | +0.026 [+0.000, +0.079] | +0.132 [+0.026, +0.237] |
| agree_full@8 | 9 | +0.233 [+0.135, +0.340] | 0.741 [0.626, 0.845] (se 0.006) | -0.101 [-0.166, -0.039] | +0.004 [-0.066, +0.078] |
| agree_full@16 | 17 | +0.204 [+0.101, +0.317] | 0.770 [0.648, 0.881] (se 0.005) | -0.072 [-0.136, -0.017] | +0.033 [-0.019, +0.096] |
| agree_full@26 | 27 | +0.193 [+0.085, +0.312] | 0.781 [0.653, 0.894] (se 0.004) | -0.062 [-0.131, -0.007] | +0.044 [-0.004, +0.107] |
| agree_full@38 | 39 | +0.188 [+0.079, +0.311] | 0.785 [0.655, 0.901] (se 0.003) | -0.057 [-0.128, -0.004] | +0.048 [-0.001, +0.116] |
| agree_full@70 | 71 | +0.184 [+0.079, +0.316] | 0.789 [0.658, 0.921] | -0.053 [-0.132, +0.000] | +0.053 [+0.000, +0.132] |
| vote@8 | 8 | +0.655 [+0.540, +0.764] | 0.318 [0.214, 0.430] (se 0.007) | -0.524 [-0.647, -0.396] | -0.418 [-0.557, -0.280] |
| vote@16 | 16 | +0.679 [+0.559, +0.793] | 0.294 [0.186, 0.409] (se 0.006) | -0.548 [-0.677, -0.415] | -0.443 [-0.586, -0.302] |
| vote@26 | 26 | +0.675 [+0.545, +0.797] | 0.298 [0.183, 0.423] (se 0.006) | -0.544 [-0.677, -0.407] | -0.438 [-0.586, -0.294] |
| vote@38 | 38 | +0.695 [+0.563, +0.820] | 0.279 [0.161, 0.408] (se 0.005) | -0.563 [-0.702, -0.421] | -0.458 [-0.605, -0.314] |
| vote@70 | 70 | +0.737 [+0.605, +0.868] | 0.237 [0.105, 0.368] | -0.605 [-0.763, -0.447] | -0.500 [-0.658, -0.342] |
| nonabstain_conf_mean@8 | 8 | +0.252 [+0.145, +0.367] | 0.722 [0.598, 0.834] (se 0.006) | -0.120 [-0.228, -0.018] | -0.015 [-0.126, +0.092] |
| nonabstain_conf_mean@16 | 16 | +0.255 [+0.139, +0.379] | 0.718 [0.587, 0.840] (se 0.005) | -0.124 [-0.245, -0.007] | -0.018 [-0.138, +0.096] |
| nonabstain_conf_mean@26 | 26 | +0.257 [+0.139, +0.386] | 0.716 [0.583, 0.842] (se 0.005) | -0.126 [-0.255, +0.000] | -0.021 [-0.147, +0.103] |
| nonabstain_conf_mean@38 | 38 | +0.258 [+0.137, +0.389] | 0.715 [0.580, 0.844] (se 0.004) | -0.127 [-0.259, +0.004] | -0.022 [-0.154, +0.111] |
| nonabstain_conf_mean@70 | 70 | +0.263 [+0.132, +0.395] | 0.711 [0.553, 0.842] | -0.132 [-0.289, +0.026] | -0.026 [-0.184, +0.132] |
| nonabstain_conf_sum@8 | 8 | +0.256 [+0.148, +0.373] | 0.717 [0.594, 0.831] (se 0.006) | -0.125 [-0.230, -0.026] | -0.019 [-0.131, +0.085] |
| nonabstain_conf_sum@16 | 16 | +0.257 [+0.141, +0.380] | 0.717 [0.587, 0.838] (se 0.005) | -0.125 [-0.243, -0.014] | -0.020 [-0.137, +0.091] |
| nonabstain_conf_sum@26 | 26 | +0.262 [+0.143, +0.391] | 0.712 [0.578, 0.837] (se 0.005) | -0.131 [-0.258, -0.009] | -0.025 [-0.149, +0.095] |
| nonabstain_conf_sum@38 | 38 | +0.257 [+0.136, +0.388] | 0.716 [0.581, 0.845] (se 0.004) | -0.126 [-0.258, +0.006] | -0.021 [-0.154, +0.112] |
| nonabstain_conf_sum@70 | 70 | +0.263 [+0.132, +0.395] | 0.711 [0.553, 0.842] | -0.132 [-0.289, +0.026] | -0.026 [-0.184, +0.132] |
| nonabstain_vote@8 | 8 | +0.248 [+0.139, +0.366] | 0.726 [0.602, 0.839] (se 0.006) | -0.116 [-0.226, -0.014] | -0.011 [-0.127, +0.099] |
| nonabstain_vote@16 | 16 | +0.245 [+0.131, +0.370] | 0.729 [0.598, 0.849] (se 0.005) | -0.113 [-0.227, -0.009] | -0.008 [-0.129, +0.106] |
| nonabstain_vote@26 | 26 | +0.235 [+0.118, +0.364] | 0.738 [0.603, 0.862] (se 0.005) | -0.104 [-0.219, +0.005] | +0.002 [-0.122, +0.118] |
| nonabstain_vote@38 | 38 | +0.240 [+0.117, +0.374] | 0.734 [0.593, 0.862] (se 0.003) | -0.108 [-0.228, +0.002] | -0.003 [-0.128, +0.116] |
| nonabstain_vote@70 | 70 | +0.237 [+0.105, +0.368] | 0.737 [0.579, 0.868] | -0.105 [-0.237, +0.000] | +0.000 [-0.132, +0.132] |

Selection-adjusted gain over BM25 top 4: pick the utility on one half of the questions and score
it on the other half.

| Candidates | Held-out gain, mean | Share of halves > 0 | 5th-95th percentile | Most chosen |
|---|---:|---:|---|---|
| every utility, m = 8 | -0.079 | 0.03 | [-0.157, -0.005] | `nonabstain@8` (345 of 400) |
| every utility, m = 16 | -0.059 | 0.04 | [-0.118, -0.004] | `nonabstain@16` |
| every utility, m = 26 | -0.050 | 0.10 | [-0.117, +0.008] | `nonabstain@26` |
| every utility, m = 38 | -0.029 | 0.23 | [-0.097, +0.027] | `nonabstain@38` |
| every utility, m = 70 | +0.025 | 0.50 | [+0.000, +0.053] | `nonabstain@70` (399 of 400) |
| every utility and every m | +0.021 | 0.47 | [+0.000, +0.053] | `nonabstain@70` (383 of 400) |

## Other cells

These rows come from `tables.md`, which has every rule in every cell.

**Retrieved arm, accuracy over all 63 questions.** The 25 constant tables are all 0, so they
dilute every rule's accuracy equally.

| Rule | Accuracy [95% CI] | minus BM25 top 4 [95% CI] | minus all 8 [95% CI] |
|---|---|---|---|
| bm25_top4 | 0.508 [0.381, 0.635] | | +0.063 [+0.016, +0.127] |
| all_8 | 0.444 [0.317, 0.571] | -0.063 [-0.127, -0.016] | |
| oracle_search@70 (needs labels) | 0.587 [0.460, 0.698] | +0.079 [+0.016, +0.159] | +0.143 [+0.063, +0.238] |
| nonabstain@8 | 0.467 [0.355, 0.577] | -0.041 [-0.088, +0.006] | +0.023 [-0.033, +0.084] |
| nonabstain@70 | 0.524 [0.397, 0.651] | +0.016 [+0.000, +0.048] | +0.079 [+0.016, +0.159] |
| agree_full@70 | 0.476 [0.349, 0.603] | -0.032 [-0.079, +0.000] | +0.032 [+0.000, +0.079] |
| nonabstain_vote@70 | 0.444 [0.317, 0.571] | -0.063 [-0.143, +0.000] | +0.000 [-0.079, +0.079] |
| conf_mean@70 | 0.063 [0.016, 0.127] | -0.444 [-0.571, -0.317] | -0.381 [-0.508, -0.254] |
| vote@70 | 0.143 [0.063, 0.238] | -0.365 [-0.492, -0.254] | -0.302 [-0.413, -0.190] |

**Gold arm, 51 non-constant tables.** BM25 top 4 here is the top 4 of the gold-augmented pool by
BM25 rank.

| Rule | Calls | Accuracy [95% CI] | minus BM25 top 4 [95% CI] | minus all 8 [95% CI] |
|---|---:|---|---|---|
| bm25_top4 | 1 | 0.706 [0.569, 0.824] | | -0.020 [-0.098, +0.059] |
| all_8 | 1 | 0.725 [0.608, 0.843] | +0.020 [-0.059, +0.098] | |
| oracle_search@16 (needs labels) | 16 | 0.842 [0.756, 0.916] | +0.136 [+0.050, +0.234] | +0.116 [+0.026, +0.218] |
| nonabstain@8 | 8 | 0.650 [0.551, 0.745] | -0.056 [-0.134, +0.023] | -0.076 [-0.165, +0.010] |
| nonabstain@38 | 38 | 0.743 [0.631, 0.845] | +0.037 [-0.022, +0.106] | +0.018 [-0.076, +0.116] |
| nonabstain@70 | 70 | 0.765 [0.647, 0.882] | +0.059 [+0.000, +0.137] | +0.039 [-0.059, +0.157] |
| agree_full@8 | 9 | 0.631 [0.522, 0.735] | -0.075 [-0.144, -0.007] | -0.094 [-0.163, -0.027] |
| agree_full@70 | 71 | 0.765 [0.647, 0.882] | +0.059 [+0.000, +0.137] | +0.039 [+0.000, +0.098] |
| nonabstain_conf_mean@70 | 70 | 0.686 [0.549, 0.804] | -0.020 [-0.176, +0.137] | -0.039 [-0.176, +0.098] |
| nonabstain_vote@70 | 70 | 0.765 [0.647, 0.882] | +0.059 [-0.059, +0.196] | +0.039 [-0.098, +0.176] |
| conf_mean@70 | 70 | 0.059 [0.000, 0.137] | -0.647 [-0.784, -0.510] | -0.667 [-0.784, -0.529] |
| vote@8 | 8 | 0.185 [0.124, 0.249] | -0.521 [-0.639, -0.396] | -0.540 [-0.667, -0.408] |
| vote@70 | 70 | 0.118 [0.039, 0.216] | -0.588 [-0.725, -0.431] | -0.608 [-0.765, -0.451] |

On the gold arm the selection-adjusted gain is -0.078 at 8 calls and +0.022 at 70 calls.

## Why the utilities behave this way (diagnostics)

The counts cover the 70 4-subsets of all 63 pools per arm; no text was used.

| Statistic | retrieved | gold |
|---|---:|---:|
| 4-subset replies | 4,410 | 4,410 |
| abstaining (pattern list) | 2,405 (54.5%) | 2,599 (58.9%) |
| abstaining replies judged correct | 2 | 2 |
| non-abstaining replies judged correct | 1,056 of 2,005 | 1,022 of 1,811 |
| median mean log-prob: abstaining replies | -5.3e-6 | -2.2e-6 |
| median mean log-prob: non-abstaining replies judged correct | -0.0037 | -0.0037 |
| median mean log-prob: non-abstaining replies judged wrong | -0.0131 | -0.0112 |
| full-pool replies that abstain (none judged correct) | 16 of 63 | 13 of 63 |
| 4-subset replies equal to the full-pool reply | 1,763 | 1,501 |
| mean distinct normalized replies among a pool's 70 4-subsets | 7.7 | 7.2 |

The table below gives the mean within-table AUROC of each score for u over the 70 4-subsets. It
covers the tables whose 4-subsets have both labels: 37 retrieved and 48 gold.

| Arm | conf_mean | conf_sum | nonabstain | agree_full | vote | nonabstain_conf_mean | nonabstain_conf_sum | nonabstain_vote |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| retrieved | 0.326 | 0.294 | 0.854 | 0.718 | 0.314 | 0.861 | 0.861 | 0.865 |
| gold | 0.260 | 0.237 | 0.878 | 0.705 | 0.248 | 0.886 | 0.888 | 0.905 |

A high AUROC does not make a good top-1 choice. `nonabstain_vote` ranks subsets well on average
(0.865) but picks the wrong one in many tables: its accuracy, 0.737, equals the full pool's. A
search keeps one subset, so what counts is whether its top-scored subset is right. The BM25
tie-break gets that right more often than confidence or vote among the answering subsets.

### Post hoc diagnostics (added after the first results; not declared utilities)

These were added at `ccd077e7`, after the declared results were seen. They are not used to pick
the best rule.

**AUROC among non-abstaining 4-subsets only.** This covers the tables that have both labels among
the answering subsets: 24 retrieved and 29 gold.

| Arm | conf_mean | conf_sum | agree_full | vote |
|---|---:|---:|---:|---:|
| retrieved | 0.613 | 0.598 | 0.685 | 0.661 |
| gold | 0.659 | 0.669 | 0.725 | 0.760 |

**A BM25-ordered stop rule.** It reads 4-subsets in BM25 rank-sum order (position 1 is BM25 top
4) and stops at the first reply that does not abstain. Uncapped, its choice is exactly
`nonabstain@70`'s.

| Arm, tables | BM25 top 4 answers | First answer later | Nothing answers | Mean position when found (max) | Better / worse than BM25 top 4 | Mean reads, uncapped |
|---|---:|---:|---:|---|---|---:|
| retrieved, 38 non-constant | 36 | 2 | 0 | 1.21 (8) | 1 / 0 | 1.21 |
| retrieved, all 63 | 46 | 7 | 10 | 2.09 (41) | 1 / 0 | 12.87 |
| gold, 51 non-constant | 42 | 6 | 3 | 3.46 (57) | 3 / 0 | 7.37 |
| gold, all 63 | 48 | 7 | 8 | 3.16 (57) | 3 / 0 | 11.65 |

With a cap of 8 reads, the rule keeps the full gain on the retrieved non-constant tables, with
1.21 reads on average. On the gold arm it keeps none of the three improved tables at 8 or 16
reads, and two at 26 or 38 (`tables.md`). Its mean reads include the pools where no subset
answers: there the uncapped rule reads all 70 and falls back to BM25 top 4.

## Eager replay sensitivity

The eager replay (job 1441) covers the first 16 questions, in 32 pools.

- **Cells.** 15 of the 8,192 table cells have a different judged label from the compiled pass,
  across 8 tables.
- **Replies.** 7,932 of the 8,192 table replies are identical.
- **Method.** Every rule was recomputed from the eager replies and scored on the eager pass's own
  judged tables. The numbers are point estimates, as means over all 16 questions per arm
  (`tables.md`). Of these, 7 retrieved and 12 gold tables are non-constant.
- **Retrieved arm.**
  - Confidence and vote reach 0.06-0.14 under both modes.
  - `nonabstain@70` equals BM25 top 4 under both, at 0.312 over the 16 questions.
  - `agree_full@70` equals all 8 under both.
- **Gold arm.**
  - `nonabstain@70` gains +0.062 over BM25 top 4 under both modes.
  - Confidence and vote fall to 0.00-0.09.
- **Reading.** The pattern does not depend on the compile, as far as 16 questions can show.

## Surprises and caveats

1. **Confidence is not merely uninformative but reversed.** The prompt tells the reader to say "I
   don't know" when the memories lack the answer. That fallback string is the reader's most
   probable output. So the most confident reply is usually an abstention, and reading more
   subsets makes confidence search worse. With a different prompt, or a reader that does not
   abstain, confidence could behave differently. That was not tested.
2. **The best rule's gain is one table of 38, and it is close to BM25 top 4 by construction.**
   `nonabstain@70` keeps BM25 top 4 whenever it answers. An abstention is judged correct in 2 of
   2,405 cases, so the rule can lose to BM25 top 4 only on such a case. The interval's lower end of
   0.000 reflects this, not luck.
3. **Random draws waste calls when BM25 rank already points to a good set.** Every random-draw
   search at 8-38 calls is below BM25 top 4 on the point estimate. Reading subsets in BM25 order
   reaches `nonabstain@70`'s choice in about one read on the retrieved non-constant tables. That
   rule is post hoc here and was not a declared utility.
4. **The rule was chosen in sample.** The best rule was picked among 8 utilities and 5 budgets on
   the tables it is scored on. Cross-fitting brings the m = 70 gain to +0.025, and below 70 calls
   the selected rule loses to BM25 top 4 on held-out halves.
5. **Agreement with the full pool tracks the full pool.** Every 4-subset reply equal to the
   full-pool reply after normalization has the full pool's judged label: 1,763 of 1,763 retrieved
   and 1,501 of 1,501 gold (post hoc, counted on the host and not emitted by the script; the
   checker reproduced it by reply digest). So `agree_full` reproduces all 8's outcome
   whenever it finds an agreeing subset. It differs only when none of the read subsets agrees and
   the BM25 tie-break chooses. Its accuracy stays within 0.053 of all 8.
6. **Pruning to BM25 top 4 beats the full pool on the retrieved arm** (+0.105 on non-constant
   tables, +0.063 over all 63). It does not on the gold arm (-0.020). On the retrieved arm, the
   four lower-ranked memories cost this reader more answers than they add.
7. **Two replies per arm that the patterns flag as abstentions were judged correct.** The pilot's
   hand check found the judge calling one "I don't know" reply correct (a page-count question), so
   some of these may be judge errors. The texts were not inspected for AM1d.
8. **Every 4-subset reply ended with the end-of-turn token and none hit the 64-token cap.** Every
   confidence score therefore includes the end-of-turn token's log-prob, and none is cut short.

## What this does not show

- **No confirmed result.** These are 38 retrieved and 51 gold development tables, and the
  intervals are wide. A claim needs the held-out registration that D113 plans. It must disclose
  that AM1 used those tables for other estimands, and that this README's results were known when
  it was designed.
- **Nothing beyond AM1's reader and judge.**
  - The reader is Qwen3-8B with thinking off, greedy decoding, at most 64 new tokens, and AM1's
    prompt with its explicit "I don't know" instruction.
  - Accuracy is the Qwen3-32B judge's label with LongMemEval's prompt; the agent's hand check of
    the judge gave κ 0.95.
  - Other readers, judges, prompts, retrievers, pool sizes and budgets were not tested.
- **The tables come from compiled-mode pass 1411.** That is job 1411's GPU-0 compile, the odd
  compile, in which about 0.25% of cells differ from the typical compile and about 0.2% from eager
  mode. The replies and log-probs come from the same pass. The eager check covers only 16
  questions.
- **Only these label-free signals were tested:**
  - the sampled-token log-probs the pass recorded (`logprobs: 0`; no top-k alternatives and no
    entropy);
  - a fixed abstention list;
  - exact agreement after `normalize_answer`;
  - a vote across subsets, not across samples.
  Verbalized confidence, sampling-based self-consistency, a trained verifier and judging by
  another model were not tried.
- **Search variants not tried as declared rules:** BM25-ordered or BM25-seeded search (post hoc
  only, above), adaptive search, and a choice between pruning and keeping all 8.
- **No cost model.** Calls are counted, not tokens. A 4-memory call is shorter than an 8-memory
  call.

## Reproduce

The run is on the host, CPU only, from a `git archive` export of `5a31db61`, in the host's `uv`
environment (CPython 3.14.6, numpy 2.5.2). It took under a minute in all. `ops/run-5a31db61.sh`
is the exact script; in short:

```bash
B=~/cotcodec-runs/stage0/am1d-label-free; R=~/cotcodec-runs/stage0/am1-study/runs
cd $B/export-5a31db61
uv run --offline python scripts/memcredit_label_free.py extract \
    --run-dir $R/main/1411/am1 --evidence $R/main/1411/study-artifact.json \
    --private-dir $B/private-5a31db61 --eager-run-dir $R/eager/1441/am1
uv run --offline python scripts/memcredit_label_free.py analyze \
    --features $B/private-5a31db61/features-1411.json.gz \
    --eager-features $B/private-5a31db61/features-1441.json.gz --output-dir $B/out-5a31db61-a
uv run --offline --extra dev pytest -q tests/test_memcredit_label_free.py   # 35 tests, on toy data
```

The defaults are 50 seeds from base 42 and 10,000 bootstrap resamples with seed 42.

- **Determinism.** Three extract runs gave byte-identical feature files (at `7465903f`, `ccd077e7`
  and `5a31db61`). Two analyze runs at `5a31db61` gave byte-identical outputs.
- **Host-only features.**
  - `features-1411.json.gz` has SHA-256 `cb678e3bdd5b55bd206a10816ac30eb5502530bc3c47e87d4213bb3f767b7fa5`.
  - `features-1441.json.gz` has SHA-256 `3b2d5554af275d3d4c42db05cd34f4525574ab86494ff7bf4568710e7705b765`.
- **Without the raw passes.** The tests run on toy tables and toy run directories: the join is
  checked against `memcredit_analyze.join_rows` and the search on hand-made tables.

## Files

- `results.json` holds the aggregates:
  - inputs and their digests, config, the abstention list and its digest;
  - the Step 1 validation counts and the reply statistics;
  - per arm and table set, every rule's accuracy, regret and differences against BM25 top 4 and
    all 8, with intervals and seed standard errors;
  - within-table AUROC, the cross-fitted selection, the post hoc diagnostics, the eager
    sensitivity and the headline answers (`answers`).
- `per-table.json.gz` holds, per table:
  - each rule's accuracy and regret, with the per-seed 0/1 outcomes of the searches;
  - the chosen mask at m = 70;
  - the BM25-ordered rule's first answering position.
- `tables.md` holds every cell's tables, generated by the script.
- `ops/` holds the host run script, the extract step's text-free stdout (the validation counts)
  and the host's pytest log.
- Code is in `scripts/memcredit_label_free.py`. Tests are in `tests/test_memcredit_label_free.py`.

## Independent check

A fresh checker reran `analyze` on the host from a new `git archive` of `03e38932`. It ran once
on the existing features and once on a fresh extract. `results.json`, `per-table.json.gz` and
`tables.md` were byte-identical each time, and the fresh extract's feature digests equal the ones
above.

Its own code reproduced the following:
- the top-4 and all-8 accuracies;
- `nonabstain@70`;
- the abstention rate (2,405 of 4,410), and its 2 correct abstentions;
- the confidence AUROC (0.326);
- the `agree_full` agreement;
- the cross-fitted selection.

The checker also confirmed these:
- the abstention list was committed at `7465903f`, 05:50:10Z, before the host directory existed
  (05:51:45Z) and before the first extract (05:52:01Z);
- no label-free rule reads u, the reference answer or the table;
- the BM25 top-4 mask equals AM1b's `retrieval_rank` keep set.

Its corrections are applied in this file. The one that changes a reading: "pruning beats all 8"
rests on 4 tables against 0, so it is now reported as a lead, not a finding.
