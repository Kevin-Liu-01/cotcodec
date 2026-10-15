# am1-keepset-search-v1: development selftest and dry run (development data only; not a result)

**DEVELOPMENT ONLY. Before the freeze.** This directory records the pre-freeze test of the analysis
code of `program/preregistrations/am1-keepset-search-v1.md` (DRAFT, not frozen). It ran on the
63-question development split only: AM1's 126 committed development tables and the development
pilot's reader pass (job 1411), the inputs AM1b and AM1d used. Nothing here is a result of the
registration, and no decision rule applies to these numbers.

- **No held-out data was opened.** `--split development` refuses any path that contains
  `am1-confirmatory` or `am1-memory-credit-v1` (symlinks resolved), and `--split heldout` refuses to
  open any held-out input until the registration is frozen; the tests check both refusals. The run
  script names only development inputs (`ops/run-f97697b5.sh`).
- **Code.** Commit `f97697b5` on `stage0/am1-keepset-search`, after the fixes of pre-freeze check
  1 (registration section 19), exported with `git archive` into a new host directory,
  `~/cotcodec-runs/stage0/am1ks-dev-selftest-f97697b5/export-f97697b5`, and run in that export's
  `uv` environment (CPython 3.14.6, numpy 2.5.2) on the host CPU, outside Slurm, with no GPU. The
  registration's section 16 pins these files at this commit.
- **Reply text stayed on the host, and the host directory is gone.** `extract` wrote AM1d's
  per-request features (numbers, flags, reply-class ids and digests; no text) to the run
  directory's `private-f97697b5/`. After the outputs below were copied, the run directory was
  deleted, as were the directories of the earlier runs (`5a80e38e`, `f41b59cd`, `8c2f4ad7`). This
  directory holds only numbers, question ids, question types, masks and digests. Home directories
  in the logs are shortened to `~`.

## What ran

`ops/run-f97697b5.sh`, once, in this order:

1. `extract --split development` on job 1411 (`reader-gpu0`, `judge32-gpu0`) and the pilot's study
   artifact. It checked the artifact and every pinned pass file, reran AM1's join
   (`memcredit_analyze.join_rows`, unchanged), reproduced `values_hex` on 126 of 126 tables and
   `distinct_replies` on 126 of 126, found AM1d's join and AM1's in agreement on 34,524 of 34,524
   requests, and wrote the features (`ops/extract-f97697b5.log`; SHA-256 `ba1dd648...`).
2. `analyze --split development` twice (`out-a`, `out-b`), with the registered settings: 200 seeds
   from 42, 10,000 bootstrap resamples with seed 42. The two runs' `results.json`,
   `per-table.json.gz` and `tables.md` are byte-identical (`ops/sha256-f97697b5.txt`). The copy here
   is `dry-run/`.
3. `selftest` on the dry run, with this extract's features and AM1d's `features-1411.json.gz`
   (pinned SHA-256 `cb678e3b...`): 19 of 19 checks pass (`selftest.json`).
4. `power` on the dry run (`power.json`; registration section 9).
5. `pytest` on the whole `tests/` directory: 3,450 passed, 66 skipped, 2 failed
   (`ops/pytest-f97697b5.log`). The two failures are `tests/test_r04_evidence.py` and
   `tests/test_r04_nuisance.py`, which compare another experiment's committed floats and differ in
   the last digits on this host. They fail identically on `main` (`d888f6b6`) on the host, checked
   in a separate new directory, since deleted; this branch does not touch them. All 50 tests of
   this registration and AM1b's and AM1d's tests pass.

Earlier runs at `5a80e38e`, `f41b59cd` and `8c2f4ad7` also passed 19 of 19. Every run's
`per-table.json.gz` is byte-identical (`62f4a78b...`): the fixes of pre-freeze check 1 changed the
verdict labels, the H-B block (now descriptive, D116), the H-C void path and the published-count
block of `power`, not any per-table number.

## The selftest: AM1b's and AM1d's committed numbers, reproduced

Every check compares exact values (floats by equality, intervals by equality), not tolerances.

| Check | Compared | Identical |
|---|---:|---:|
| AM1b per-table direct-search curve at B = 4 (70 exact expectations per table, both arms) | 89 | 89 |
| AM1b per-table leave-one-out: regret, calls, matched direct search | 89 | 89 |
| AM1b per-table greedy backward, BM25 ties: regret, calls, matched direct search | 89 | 89 |
| AM1b per-table SNIPW-64 at AM1b's seeds 42-61: each seed's regret, calls, matched direct search | 89 | 89 |
| AM1b per-table MSR-Banzhaf-64, the same | 89 | 89 |
| AM1b per-table permutation Shapley-16, the same | 89 | 89 |
| AM1b per-table random keep set and retrieval rank (0 calls) | 89 + 89 | 89 + 89 |
| AM1b `results.json`: those five rules' mean, 95% and 99% intervals and rule-minus-direct difference at matched calls, and direct search at 8, 9, 16, 26, 38, 64 and 70 calls, both arms | 24 | 24 |
| The 200-seed dry run's per-table leave-one-out, greedy backward and direct curve equal AM1b's | 267 | 267 |
| AM1d's `features-1411.json.gz` pools equal this `extract`'s pools | 126 | 126 |
| AM1d's extract validation record equals this one's | 1 | 1 |
| AM1d per-table: BM25 top 4 (mask and u), all 8, best 4-subset, oracle search at 8, 16, 26, 38, 70 calls, `nonabstain@70` (mask and u), the stop rule's first answering position and capped rows | 126 | 126 |
| AM1d `results.json`: accuracies of BM25 top 4, all 8, oracle search and `nonabstain@70`, and `nonabstain@70` minus BM25 top 4 (mean and 95% interval; both arms; non-constant and all questions) | 36 | 36 |
| AM1d reply statistics (4-subset abstentions 2,405 retrieved and 2,599 gold, abstentions judged correct, by pattern, full-pool abstentions, agreement with the full pool) | 16 | 16 |
| AM1d stop-rule reads (mean and maximum uncapped reads, first answers at position 1) | 4 | 4 |
| AM1d README: BM25 top 4 vs all 8, retrieved, 4 vs 0, exact p = 0.125 | 1 | 1 |
| AM1d README: `nonabstain@70` vs all 8, retrieved, 5 vs 0, exact p = 0.0625 | 1 | 1 |
| AM1d README: `nonabstain@70` vs BM25 top 4, retrieved, 1 vs 0 | 1 | 1 |

So the H-A rules are AM1b's rules on AM1b's draws, direct search is AM1b's exact expectation,
`extract` is AM1d's extract, and H-C's rule is AM1d's `nonabstain@70` with AM1d's reading order.
The code new to this registration is the 200-seed averaging, the comparisons and their decision
bounds, the Monte Carlo margin, the exact McNemar test and its interval, the gate and pins, and
the descriptive tables; the tests cover each of these on toy tables.

## The dry run (development tables; not a result; for the checkers' orientation)

The full registered analysis on the development data (`dry-run/tables.md`). The verdict rules are
applied as code, and they are not readings of anything: 38 retrieved tables, against the 251 the
registration is sized for. The H-A verdict on these tables is INCONCLUSIVE (A3, A5 and A7 not
separated; no rule better at any calls).

**H-A, retrieved arm, 38 non-constant tables, 200 seeds.** Difference = direct search's regret
minus the rule's; bounds one-sided at 1 - 0.05/7.

| Id | Comparison | Rule calls | Difference | Lower | Upper | MC se | Class |
|---|---|---:|---:|---:|---:|---:|---|
| A1 | leave-one-out vs direct at 9 | 9.0 | -0.123 | -0.214 | -0.032 | 0 | SEARCH_BETTER |
| A2 | SNIPW-64 vs direct at matched calls | 56.7 | -0.044 | -0.092 | -0.011 | 0.0019 | SEARCH_BETTER |
| A3 | SNIPW-64 vs direct at 26 | 56.7 | -0.025 | -0.057 | -0.004 | 0.0020 | NOT_SEPARATED |
| A4 | MSR-Banzhaf-64 vs direct at 64 | 64.0 | -0.046 | -0.097 | -0.010 | 0.0020 | SEARCH_BETTER |
| A5 | MSR-Banzhaf-64 vs direct at 26 | 64.0 | -0.025 | -0.060 | +0.001 | 0.0020 | NOT_SEPARATED |
| A6 | permutation Shapley-16 vs direct at 26 | 83.3 | -0.069 | -0.141 | -0.014 | 0.0015 | SEARCH_BETTER |
| A7 | greedy backward vs direct at 26 | 26.0 | -0.055 | -0.155 | +0.006 | 0 | NOT_SEPARATED |

Rule regrets at 200 seeds: leave-one-out 0.214, SNIPW-64 0.049, MSR-Banzhaf-64 0.048, permutation
Shapley-16 0.093, greedy backward 0.079 (AM1b at 20 seeds: 0.214, 0.050, 0.043, 0.095, 0.079).
A3's upper bound (-0.004) clears 0 but not the Monte Carlo margin (3 x 0.0020), which is the
margin doing its job on 38 tables; on 251 tables the standard errors shrink by about 2.6.

**H-B (descriptive, D116) and H-C, all 63 questions** (exact McNemar, discordant pairs b and c):

| Arm | Comparison | b | c | Difference | 95% exact conditional | p |
|---|---|---:|---:|---:|---|---:|
| retrieved | BM25 top 4 - all 8 | 4 | 0 | +0.063 | [-0.013, +0.063] | 0.125 |
| gold | BM25 top 4 - all 8 | 2 | 3 | -0.016 | [-0.071, +0.056] | 1 |
| retrieved | nonabstain-BM25 - BM25 top 4 | 1 | 0 | +0.016 | [-0.015, +0.016] | 1 |
| gold | nonabstain-BM25 - BM25 top 4 | 3 | 0 | +0.048 | [-0.020, +0.048] | 0.25 |

The exact conditional interval and the exact test agree (the interval includes 0, and p = 0.125),
where the percentile bootstrap does not ([+0.016, +0.127] for the first row), which is why the
registration reads the test.

**Stop-rule reads**, retrieved: 1.21 on average over the 38 non-constant tables (36 at 1, maximum
8); 12.87 over all 63, because in 10 pools no 4-subset answers and the rule reads all 70.

## Operating characteristics (`power.json`)

H-A, from the 38 development tables resampled to 251: P(SEARCH_DOMINATES) 0.999 at the development
effects, 0.909 at half, 0.372 at a quarter; RULE_BEATS_SEARCH 0.006 at a quarter (A7, a matched
comparison), RULE_AT_MORE_CALLS_BETTER never; greedy backward (A7) is the weakest comparison.
H-B and H-C: exact power grids by discordance rate and share, and what AM1's published counts
imply (`conditional_on_am1_published_counts`): BM25 top 4 at least 17 questions behind all 8 on
the held-out retrieved arm, where the exact test rejects with at most 67 discordant pairs; H-C's
power by conversion rate of the 86 tables BM25 top 4 gets wrong, at c = 0, 1 and 2; and exact
bounds on direct search's held-out mean regret ([0.022, 0.448] at 9 calls, [0, 0.323] at 26,
[0, 0.095] at 57, [0, 0.044] at 64). The registration's sections 1.2 and 9 quote these.

## Reproduce

On the host, from a `git archive` export of `f97697b5`, in a new directory:

```bash
B=~/cotcodec-runs/stage0/am1ks-dev-selftest-f97697b5; R=~/cotcodec-runs/stage0/am1-study/runs
P=$B/private-f97697b5
uv run --offline python scripts/memcredit_keepset_search.py extract --split development \
  --run-dir $R/main/1411/am1 --evidence $R/main/1411/study-artifact.json --private-dir $P
uv run --offline python scripts/memcredit_keepset_search.py analyze --split development \
  --features $P/features-development-1411.json.gz --output-dir $B/out-f97697b5-a
uv run --offline python scripts/memcredit_keepset_search.py selftest \
  --analysis-dir $B/out-f97697b5-a --features $P/features-development-1411.json.gz \
  --am1d-features ~/cotcodec-runs/stage0/am1d-label-free/private-5a31db61/features-1411.json.gz \
  --output $B/selftest-f97697b5.json
uv run --offline python scripts/memcredit_keepset_search.py power \
  --analysis-dir $B/out-f97697b5-a --output $B/power-f97697b5.json
uv run --offline --extra dev pytest -q tests/
```

The H-A, H-B and descriptive parts need only the committed development tables, so they also run
locally without `--features` (H-C and the abstention outputs are then left out). Such a run on a
Mac (CPython 3.13.14, numpy 2.5.2) gave H-A rows equal to the dry run's. One H-B number differed in
its last bit: the gold arm's exact conditional interval, -0.07099286499582265 against
-0.07099286499582268 on the host, because `harness.memcredit.clopper_pearson` sums binomial terms
with the platform's `lgamma`. No reading depends on it (the readings use the exact rational
p-value), but byte-identical reruns need the same platform; the registered run and its verifier
both run on the host.

## Files

- `selftest.json`: every check with its counts and the digests of AM1b's and AM1d's committed
  files it read.
- `dry-run/`: `results.json`, `per-table.json.gz` and `tables.md` of `analyze --split development`.
- `power.json`: the operating characteristics.
- `ops/`: the run script, the logs of `extract`, `analyze`, `selftest`, `power` and `pytest`, and
  the SHA-256 of every output (`sha256-f97697b5.txt`).
