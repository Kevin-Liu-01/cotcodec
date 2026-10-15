# AM1b: keep-set regret against reader calls for cheaper memory-credit rules (exploratory, development tables only)

**EXPLORATORY.** AM1b is the next step that D112 names (`program/decisions.md`). It uses no GPU:
every number is computed on a CPU from the exact 256-subset tables that AM1's development pilot
committed. No decision rule applies. The labels below are AM1's section 7 rule applied
descriptively to 38 tables; they are not verdicts.

- **Development tables only.** The input is
  `program/evidence/2026-10-15/am1-dev-pilot/analysis/tables.json.gz` (SHA-256
  `839542c65332b908e1c80e9b5e9c09d9c23088e2dec4a54bf2e37dde4f0105d3`): 126 tables, 63
  development questions times 2 arms (gold, retrieved). The pilot's `h2.json` (SHA-256
  `89fc5f14ff73143a5aeafa83fa9c6164e901ef8bb0bcf6edbb9130e796bc99c2`) is read only to check the
  bootstrap. **The confirmatory tables (`program/evidence/2026-10-16/am1-confirmatory/`) were not
  opened, read or decoded** by this analysis or while preparing it. The script refuses any path
  that contains `am1-confirmatory`. The held-out tables stay unused, so a later registration can
  evaluate on them.
- **Oracle utility.** Every rule here reads the judged correctness u(S) of the reader's answer
  given memory subset S, as AM1's rules do. Judging needs the reference answer. The curve
  therefore measures how well a rule attributes credit within one question when labels are
  available. It is not a keep policy that could run in deployment without labels.

## Question

AM1 found that leave-one-out credit picks bad keep sets. Exact Shapley does better but reads all
256 subsets of a pool of 8 memories. As a function of reader calls per pool, how close do cheaper
query-based rules get to the exact optimal keep set? The primary cell is the retrieved arm at
B = 4 kept of 8. Is any rule near ADEQUATE (99% upper bound below 0.02), or at least not
MISSPECIFIED (99% lower bound at most 0.05), at a deployable cost?

## Answer (retrieved arm, B = 4, 38 non-constant tables)

- **No credit rule has a 99% upper bound at or below 0.05, and none is ADEQUATE.** The lowest
  99% upper bound among credit rules is SNIPW-128's 0.080, at 101 calls.
- **The cheapest credit rule that is not MISSPECIFIED is SNIPW-16**, at 15.5 calls: 0.115, 99%
  [0.041, 0.217], INCONCLUSIVE. With 38 tables, INCONCLUSIVE covers true regrets from about 0.04
  to 0.2, so it is not evidence of adequacy.
- **No credit rule beats direct search at equal calls, even on the point estimate.** Direct search
  reads m random 4-subsets and keeps the best one. It loses 0.091 at 9 calls, against 0.214 for
  leave-one-out at the same 9 calls, and 0.046 at 16 calls. At 38 calls its 99% upper bound is
  0.050. At 70 calls (every 4-subset) it is exact. Exact credit reads 256 subsets and still loses
  0.079 (Shapley) or 0.031 (Banzhaf).
- **Greedy selection (26 calls) is INCONCLUSIVE and does not beat direct search either.** Forward
  selection loses 0.105 and backward elimination 0.079, against 0.024 for direct search at 26
  calls.
- **Among credit rules, sampled Banzhaf (SNIPW, MSR) lowers regret fastest per call.** It reaches
  about 0.04-0.05 at 57-64 calls and about 0.036 at 101-128 calls, near exact Banzhaf's 0.031.
  Permutation Shapley and KernelSHAP fall more slowly, to 0.06-0.08 at 120-190 calls, near exact
  Shapley's 0.079.
- **Retrieval rank, at 0 calls, loses 0.132.** That is less than leave-one-out, leave-one-in and
  every rule below 15 calls.

## Step 1: the decoding is validated

`values[m]` is bit m of `int(values_hex, 16)`: the empty set is the lowest bit, the full set the
highest, and bit i of a mask keeps memory i in pool order, which is chronological. This inverts
`memcredit_analyze.analyze`'s encoding,
`format(int("".join(str(int(v)) for v in reversed(values)), 2), "064x")`. Every check passed,
and the script stops on any difference:

| Check (harness functions) | Result |
|---|---|
| Re-encoding the decoded values gives the committed hex | 126 / 126 tables |
| `summary`: u(full), u(empty), constant, mean, best value at B = 1..7 | 126 / 126 |
| Credits `shapley_exact`, `banzhaf_exact`, `loo` (both copies), `leave_one_in` equal `mc.shapley`, `ms.banzhaf`, `mc.loo_credit`, `ms.leave_one_in` exactly | 126 / 126 |
| AM1's seeded draws (`perm_shapley_4`, `perm_shapley_16`, `snipw_64`; seeds 42, 43, 44): credit and calls; the memoized counter equals the harness's own count | 1,134 / 1,134 |
| `regret` of `shapley_exact` and `loo` (min, mean, max, number of tie sets) via `mc.keep_set_regret_range`, B = 1..4 | 356 / 356 each (89 tables x 4) |
| `regret` of the 14 other committed rules, `random` included | 89 / 89 tables |
| Exactly the 37 constant tables lack a `regret` field (AM1 skips them) | 126 / 126 |
| AM1's aggregate rows: recomputed regrets + `ms.cluster_bootstrap` (4,000, seed 42) give `h2.json`'s mean, 95% and 99% intervals (LOO, exact Shapley, perm-16, SNIPW-64; both arms; B = 1..4) | 64 / 64 identical |
| The reversed bit order reproduces the Shapley and LOO regrets | 0 / 89 (the order is identified) |

## Rules and how calls are counted

A call is one distinct subset whose u(S) a rule reads, memoized per pool, as a deployed system
would cache it. The empty and full sets count when they are read. Regret is AM1's: the exact
optimum OPT_B minus u(keep set), averaged over every keep set the rule's ties allow
(`mc.keep_set_regret_range`, `mean`). A search rule returns one set and is scored by the same
function on that set's indicator. Only non-constant tables count, as in AM1: 38 retrieved and 51
gold.

| Rule | Sizes | Calls | Definition |
|---|---|---|---|
| `loo`, `leave_one_in`, `loo_plus_loi` | - | 9, 9, 18 | harness `mc.loo_credit` (full set + 8), `ms.leave_one_in` (empty set + 8), and their sum. Ranking by LOO alone would need only the 8 deletions; the harness also reads the full set, and it is counted |
| `perm_shapley_k` | k = 1, 2, 4, 8, 16, 32, 64 | measured | harness `ms.permutation_shapley`; at most 2 + 7k distinct subsets |
| `snipw_e` | e = 8 ... 512 i.i.d. exposures | measured | harness `ms.snipw` (keep probability 1/2; mean u with i kept minus mean u with i dropped) |
| `msr_banzhaf_m` | m = 8 ... 256 distinct subsets | m | maximum-sample-reuse Banzhaf over m distinct uniform subsets (without replacement), in rational arithmetic; m = 256 is exact Banzhaf |
| `kernelshap_n` | n = 8 ... 512 samples | 2 + distinct coalitions | n/2 coalitions from the Shapley kernel plus their complements (paired), unit weight per draw, ridge 1e-6, efficiency constraint u(N) - u(empty) solved in closed form; credits rounded to 9 decimals so float noise does not break exact ties. With exact kernel weights the solver returns exact Shapley (tested) |
| `greedy_forward`, `greedy_backward` | - | 26 at B = 4 | add (remove) one memory per step, taking the best u: 8 + 7 + 6 + 5 subsets. Backward never reads the full set. Ties are broken by BM25 retrieval rank (`credits.retrieval_rank`): forward adds the better-ranked memory, backward drops the worse-ranked one. The pool order is chronological, not retrieval order, so the rank is used, not the pool index |
| `*_tiemean` | - | same | the expected regret when every greedy tie is broken uniformly at random (exact), the analogue of AM1's tie convention |
| direct search (a search baseline, not a credit rule) | m = 1 ... C(8, B) | m | read m distinct random B-subsets and keep the best one read. The expectation over draws is exact (order statistics). Every best-read set has the same u, so ties cannot change its regret |
| `shapley_exact`, `banzhaf_exact` | - | 256 | references |
| `random_keep_set`, `retrieval_rank` | - | 0 | anchors |

"Direct, same calls" pairs each rule with direct search at the rule's own call count, per table
and per seed. At 0 calls this is a random keep set; past C(8, B) calls it is the exhaustive
search.

**SNIPW and MSR are one estimator.** At propensity 1/2 the harness's SNIPW contrast is the
maximum-sample-reuse Banzhaf estimator. The two rows differ only in sampling: SNIPW draws i.i.d.
exposures (duplicates are free calls but count twice in the means), while MSR draws distinct
subsets.

**Seeds and intervals.**

- Stochastic rules run 20 seeds, 42 to 61, each with
  `random.Random(f"{seed}:{question_id}:{arm}:{rule}")`. This is AM1's scheme, so seeds 42-44 of
  `perm_shapley_4`, `perm_shapley_16` and `snipw_64` are AM1's own draws.
- A table's regret is its mean over the 20 seeds. In the primary cell, the Monte Carlo standard
  error of a rule's mean over seeds ("se") is at most 0.011. That is under a fifth of each
  stochastic rule's 95% bootstrap half-width.
- Intervals use `ms.cluster_bootstrap`: 10,000 resamples of questions, numpy `default_rng(42)`,
  at 95% and 99%. Each arm has one table per question.
- Labels come from `memcredit_analyze.h2_verdict`: MISSPECIFIED if the 99% lower bound exceeds
  0.05, ADEQUATE if the 99% upper bound is below 0.02, and INCONCLUSIVE otherwise.

## Results: retrieved arm, B = 4 (primary cell)

38 non-constant tables.

| Rule | Calls | Mean regret | 95% CI | 99% CI | Label | Direct, same calls | Rule - direct [95% CI] |
|---|---:|---:|---|---|---|---:|---|
| *anchors (0 calls)* | | | | | | | |
| random_keep_set | 0 | 0.576 | [0.496, 0.652] | [0.468, 0.673] | MISSPECIFIED | 0.576 | 0.000 [0.000, 0.000] |
| retrieval_rank | 0 | 0.132 | [0.026, 0.237] | [0.026, 0.289] | INCONCLUSIVE | 0.576 | -0.444 [-0.541, -0.340] |
| *leave-one-out / leave-one-in* | | | | | | | |
| loo | 9 | 0.214 | [0.123, 0.316] | [0.099, 0.348] | MISSPECIFIED | 0.091 | 0.123 [0.050, 0.198] |
| leave_one_in | 9 | 0.383 | [0.266, 0.501] | [0.234, 0.535] | MISSPECIFIED | 0.091 | 0.293 [0.202, 0.383] |
| loo_plus_loi | 18 | 0.189 | [0.096, 0.294] | [0.072, 0.324] | MISSPECIFIED | 0.039 | 0.149 [0.071, 0.234] |
| *permutation Shapley* | | | | | | | |
| perm_shapley_1 | 9 | 0.314 (se 0.003) | [0.216, 0.418] | [0.188, 0.450] | MISSPECIFIED | 0.091 | 0.223 [0.158, 0.289] |
| perm_shapley_2 | 15.6 (11-16) | 0.239 (se 0.006) | [0.150, 0.334] | [0.129, 0.363] | MISSPECIFIED | 0.047 | 0.191 [0.127, 0.260] |
| perm_shapley_4 | 27.9 (21-30) | 0.165 (se 0.004) | [0.087, 0.253] | [0.068, 0.287] | MISSPECIFIED | 0.021 | 0.144 [0.078, 0.218] |
| perm_shapley_8 | 49.2 (39-55) | 0.119 (se 0.003) | [0.050, 0.203] | [0.033, 0.232] | INCONCLUSIVE | 0.008 | 0.112 [0.049, 0.186] |
| perm_shapley_16 | 83.4 (72-94) | 0.095 (se 0.005) | [0.032, 0.171] | [0.019, 0.200] | INCONCLUSIVE | 0.000 | 0.095 [0.032, 0.171] |
| perm_shapley_32 | 131.2 (115-145) | 0.083 (se 0.005) | [0.024, 0.159] | [0.012, 0.183] | INCONCLUSIVE | 0.000 | 0.083 [0.024, 0.159] |
| perm_shapley_64 | 187.3 (172-206) | 0.073 (se 0.006) | [0.021, 0.137] | [0.009, 0.159] | INCONCLUSIVE | 0.000 | 0.073 [0.021, 0.137] |
| *SNIPW (i.i.d. exposures)* | | | | | | | |
| snipw_8 | 7.9 (6-8) | 0.181 (se 0.011) | [0.111, 0.260] | [0.093, 0.290] | MISSPECIFIED | 0.105 | 0.076 [0.052, 0.102] |
| snipw_16 | 15.5 (13-16) | 0.115 (se 0.010) | [0.055, 0.190] | [0.041, 0.217] | INCONCLUSIVE | 0.048 | 0.068 [0.037, 0.104] |
| snipw_32 | 30.1 (25-32) | 0.065 (se 0.007) | [0.021, 0.124] | [0.013, 0.146] | INCONCLUSIVE | 0.019 | 0.046 [0.018, 0.080] |
| snipw_64 | 56.8 (48-63) | 0.050 (se 0.006) | [0.014, 0.099] | [0.009, 0.118] | INCONCLUSIVE | 0.005 | 0.045 [0.014, 0.085] |
| snipw_128 | 100.8 (91-111) | 0.036 (se 0.005) | [0.009, 0.070] | [0.004, 0.080] | INCONCLUSIVE | 0.000 | 0.036 [0.009, 0.070] |
| snipw_256 | 162.2 (147-175) | 0.039 (se 0.005) | [0.010, 0.076] | [0.005, 0.089] | INCONCLUSIVE | 0.000 | 0.039 [0.010, 0.076] |
| snipw_512 | 221.5 (206-238) | 0.032 (se 0.006) | [0.001, 0.071] | [0.000, 0.084] | INCONCLUSIVE | 0.000 | 0.032 [0.001, 0.071] |
| *MSR Banzhaf (distinct subsets)* | | | | | | | |
| msr_banzhaf_8 | 8 | 0.191 (se 0.009) | [0.113, 0.278] | [0.095, 0.309] | MISSPECIFIED | 0.104 | 0.087 [0.057, 0.121] |
| msr_banzhaf_16 | 16 | 0.121 (se 0.008) | [0.059, 0.193] | [0.045, 0.221] | INCONCLUSIVE | 0.046 | 0.075 [0.042, 0.112] |
| msr_banzhaf_32 | 32 | 0.078 (se 0.007) | [0.028, 0.143] | [0.018, 0.166] | INCONCLUSIVE | 0.017 | 0.061 [0.025, 0.108] |
| msr_banzhaf_64 | 64 | 0.043 (se 0.005) | [0.009, 0.091] | [0.005, 0.111] | INCONCLUSIVE | 0.002 | 0.040 [0.009, 0.085] |
| msr_banzhaf_128 | 128 | 0.037 (se 0.007) | [0.008, 0.078] | [0.003, 0.092] | INCONCLUSIVE | 0.000 | 0.037 [0.008, 0.078] |
| msr_banzhaf_192 | 192 | 0.031 (se 0.003) | [0.001, 0.072] | [0.000, 0.086] | INCONCLUSIVE | 0.000 | 0.031 [0.001, 0.072] |
| msr_banzhaf_256 | 256 | 0.031 | [0.000, 0.079] | [0.000, 0.096] | INCONCLUSIVE | 0.000 | 0.031 [0.000, 0.079] |
| *KernelSHAP (paired)* | | | | | | | |
| kernelshap_8 | 9.7 (6-10) | 0.195 (se 0.007) | [0.118, 0.281] | [0.099, 0.308] | MISSPECIFIED | 0.084 | 0.111 [0.068, 0.159] |
| kernelshap_16 | 16.5 (12-18) | 0.143 (se 0.008) | [0.067, 0.232] | [0.050, 0.264] | INCONCLUSIVE | 0.045 | 0.099 [0.045, 0.159] |
| kernelshap_32 | 28.6 (18-34) | 0.101 (se 0.007) | [0.039, 0.175] | [0.026, 0.201] | INCONCLUSIVE | 0.021 | 0.080 [0.030, 0.139] |
| kernelshap_64 | 48.0 (36-62) | 0.080 (se 0.007) | [0.025, 0.151] | [0.013, 0.177] | INCONCLUSIVE | 0.009 | 0.072 [0.024, 0.132] |
| kernelshap_128 | 77.1 (58-98) | 0.063 (se 0.008) | [0.018, 0.120] | [0.005, 0.140] | INCONCLUSIVE | 0.000 | 0.062 [0.018, 0.119] |
| kernelshap_256 | 119.9 (88-156) | 0.066 (se 0.007) | [0.018, 0.125] | [0.008, 0.146] | INCONCLUSIVE | 0.000 | 0.066 [0.018, 0.125] |
| kernelshap_512 | 172.8 (148-198) | 0.059 (se 0.006) | [0.011, 0.124] | [0.000, 0.149] | INCONCLUSIVE | 0.000 | 0.059 [0.011, 0.124] |
| *exact references* | | | | | | | |
| shapley_exact | 256 | 0.079 | [0.000, 0.184] | [0.000, 0.211] | INCONCLUSIVE | 0.000 | 0.079 [0.000, 0.184] |
| banzhaf_exact | 256 | 0.031 | [0.000, 0.079] | [0.000, 0.096] | INCONCLUSIVE | 0.000 | 0.031 [0.000, 0.079] |
| *greedy selection (search)* | | | | | | | |
| greedy_forward | 26 | 0.105 | [0.026, 0.211] | [0.000, 0.263] | INCONCLUSIVE | 0.024 | 0.082 [0.007, 0.173] |
| greedy_backward | 26 | 0.079 | [0.000, 0.184] | [0.000, 0.211] | INCONCLUSIVE | 0.024 | 0.055 [-0.003, 0.130] |
| greedy_forward_tiemean | 26 | 0.156 | [0.083, 0.238] | [0.067, 0.264] | MISSPECIFIED | 0.024 | 0.132 [0.075, 0.196] |
| greedy_backward_tiemean | 26 | 0.059 | [0.013, 0.119] | [0.002, 0.141] | INCONCLUSIVE | 0.024 | 0.036 [0.004, 0.076] |

Direct search (a search baseline, not a credit rule), retrieved, B = 4:

| Calls | Mean regret | 95% CI | 99% CI | Label |
|---:|---:|---|---|---|
| 1 | 0.576 | [0.496, 0.652] | [0.468, 0.673] | MISSPECIFIED |
| 4 | 0.216 | [0.142, 0.298] | [0.123, 0.327] | MISSPECIFIED |
| 8 | 0.104 | [0.046, 0.172] | [0.033, 0.197] | INCONCLUSIVE |
| 9 | 0.091 | [0.037, 0.156] | [0.026, 0.180] | INCONCLUSIVE |
| 16 | 0.046 | [0.011, 0.096] | [0.005, 0.116] | INCONCLUSIVE |
| 18 | 0.039 | [0.008, 0.086] | [0.003, 0.106] | INCONCLUSIVE |
| 26 | 0.024 | [0.002, 0.060] | [0.001, 0.077] | INCONCLUSIVE |
| 32 | 0.017 | [0.001, 0.047] | [0.000, 0.062] | INCONCLUSIVE |
| 48 | 0.008 | [0.000, 0.025] | [0.000, 0.033] | INCONCLUSIVE |
| 64 | 0.002 | [0.000, 0.007] | [0.000, 0.009] | ADEQUATE |
| 70 | 0.000 | [0.000, 0.000] | [0.000, 0.000] | ADEQUATE |

## Every cell (gold arm; B = 1, 2, 3)

Mean regret and label (M MISSPECIFIED, I INCONCLUSIVE, A ADEQUATE) in every cell.

Calls are those at B = 4; greedy calls depend on B (forward 8, 15, 21, 26; backward 35, 33, 30, 26 at B = 1, 2, 3, 4).

| Rule | Calls (B = 4) | ret B=1 | ret B=2 | ret B=3 | ret B=4 | gol B=1 | gol B=2 | gol B=3 | gol B=4 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| random_keep_set | 0 | 0.431 M | 0.665 M | 0.674 M | 0.576 M | 0.375 M | 0.674 M | 0.760 M | 0.654 M |
| retrieval_rank | 0 | 0.132 I | 0.237 M | 0.263 M | 0.132 I | 0.059 I | 0.176 M | 0.333 M | 0.235 M |
| loo | 9 | 0.173 M | 0.284 M | 0.273 M | 0.214 M | 0.095 I | 0.235 M | 0.293 M | 0.200 M |
| leave_one_in | 9 | 0.000 A | 0.330 M | 0.416 M | 0.383 M | 0.000 A | 0.372 M | 0.516 M | 0.464 M |
| loo_plus_loi | 18 | 0.000 A | 0.188 M | 0.223 M | 0.189 M | 0.000 A | 0.175 M | 0.255 M | 0.176 M |
| perm_shapley_1 | 9 | 0.061 I | 0.299 M | 0.362 M | 0.314 M | 0.043 I | 0.349 M | 0.467 M | 0.397 M |
| perm_shapley_2 | 15.6 (11-16) | 0.030 I | 0.201 M | 0.274 M | 0.239 M | 0.027 I | 0.244 M | 0.368 M | 0.309 M |
| perm_shapley_4 | 27.9 (21-30) | 0.013 I | 0.121 I | 0.187 M | 0.165 M | 0.015 I | 0.173 M | 0.282 M | 0.229 M |
| perm_shapley_8 | 49.2 (39-55) | 0.005 A | 0.082 I | 0.132 I | 0.119 I | 0.005 A | 0.114 I | 0.212 M | 0.157 M |
| perm_shapley_16 | 83.4 (72-94) | 0.000 A | 0.053 I | 0.101 I | 0.095 I | 0.003 A | 0.101 I | 0.177 M | 0.131 I |
| perm_shapley_32 | 131.2 (115-145) | 0.000 A | 0.039 I | 0.086 I | 0.083 I | 0.000 A | 0.084 I | 0.163 M | 0.114 I |
| perm_shapley_64 | 187.3 (172-206) | 0.000 A | 0.028 I | 0.085 I | 0.073 I | 0.000 A | 0.063 I | 0.145 I | 0.097 I |
| snipw_8 | 7.9 (6-8) | 0.079 I | 0.221 M | 0.230 M | 0.181 M | 0.047 I | 0.269 M | 0.340 M | 0.236 M |
| snipw_16 | 15.5 (13-16) | 0.026 I | 0.126 M | 0.166 M | 0.115 I | 0.021 I | 0.162 M | 0.245 M | 0.172 M |
| snipw_32 | 30.1 (25-32) | 0.005 I | 0.074 I | 0.109 I | 0.065 I | 0.014 I | 0.107 I | 0.185 M | 0.115 I |
| snipw_64 | 56.8 (48-63) | 0.000 A | 0.047 I | 0.073 I | 0.050 I | 0.013 I | 0.077 I | 0.127 I | 0.092 I |
| snipw_128 | 100.8 (91-111) | 0.000 A | 0.026 I | 0.052 I | 0.036 I | 0.006 I | 0.062 I | 0.109 I | 0.070 I |
| snipw_256 | 162.2 (147-175) | 0.000 A | 0.021 I | 0.047 I | 0.039 I | 0.000 A | 0.055 I | 0.092 I | 0.075 I |
| snipw_512 | 221.5 (206-238) | 0.000 A | 0.014 I | 0.036 I | 0.032 I | 0.000 A | 0.052 I | 0.083 I | 0.052 I |
| msr_banzhaf_8 | 8 | 0.072 I | 0.207 M | 0.236 M | 0.191 M | 0.043 I | 0.247 M | 0.331 M | 0.226 M |
| msr_banzhaf_16 | 16 | 0.022 I | 0.118 I | 0.153 M | 0.121 I | 0.018 I | 0.167 M | 0.247 M | 0.165 M |
| msr_banzhaf_32 | 32 | 0.006 I | 0.074 I | 0.099 I | 0.078 I | 0.013 I | 0.096 I | 0.166 M | 0.106 I |
| msr_banzhaf_64 | 64 | 0.003 A | 0.039 I | 0.063 I | 0.043 I | 0.009 I | 0.070 I | 0.124 I | 0.082 I |
| msr_banzhaf_128 | 128 | 0.001 A | 0.020 I | 0.056 I | 0.037 I | 0.003 A | 0.060 I | 0.100 I | 0.071 I |
| msr_banzhaf_192 | 192 | 0.000 A | 0.012 I | 0.037 I | 0.031 I | 0.000 A | 0.055 I | 0.082 I | 0.064 I |
| msr_banzhaf_256 | 256 | 0.000 A | 0.000 A | 0.018 I | 0.031 I | 0.000 A | 0.052 I | 0.069 I | 0.046 I |
| kernelshap_8 | 9.7 (6-10) | 0.156 M | 0.292 M | 0.277 M | 0.195 M | 0.163 M | 0.321 M | 0.363 M | 0.256 M |
| kernelshap_16 | 16.5 (12-18) | 0.049 I | 0.175 M | 0.199 M | 0.143 I | 0.042 I | 0.180 M | 0.269 M | 0.195 M |
| kernelshap_32 | 28.6 (18-34) | 0.013 I | 0.096 I | 0.142 I | 0.101 I | 0.008 I | 0.126 I | 0.198 M | 0.157 M |
| kernelshap_64 | 48.0 (36-62) | 0.000 A | 0.062 I | 0.087 I | 0.080 I | 0.001 A | 0.088 I | 0.171 M | 0.116 I |
| kernelshap_128 | 77.1 (58-98) | 0.000 A | 0.036 I | 0.085 I | 0.063 I | 0.000 A | 0.065 I | 0.146 M | 0.105 I |
| kernelshap_256 | 119.9 (88-156) | 0.000 A | 0.016 I | 0.067 I | 0.066 I | 0.000 A | 0.061 I | 0.122 I | 0.095 I |
| kernelshap_512 | 172.8 (148-198) | 0.000 A | 0.021 I | 0.054 I | 0.059 I | 0.000 A | 0.050 I | 0.088 I | 0.088 I |
| shapley_exact | 256 | 0.000 A | 0.000 A | 0.039 I | 0.079 I | 0.000 A | 0.039 I | 0.085 I | 0.078 I |
| banzhaf_exact | 256 | 0.000 A | 0.000 A | 0.018 I | 0.031 I | 0.000 A | 0.052 I | 0.069 I | 0.046 I |
| greedy_forward | 26 | 0.000 A | 0.026 I | 0.079 I | 0.105 I | 0.000 A | 0.039 I | 0.098 I | 0.098 I |
| greedy_backward | 26 | 0.000 A | 0.026 I | 0.105 I | 0.079 I | 0.000 A | 0.078 I | 0.137 I | 0.098 I |
| greedy_forward_tiemean | 26 | 0.000 A | 0.191 M | 0.216 M | 0.156 M | 0.000 A | 0.245 M | 0.329 M | 0.259 M |
| greedy_backward_tiemean | 26 | 0.008 I | 0.016 I | 0.073 I | 0.059 I | 0.013 I | 0.089 I | 0.130 I | 0.084 I |

Direct search at selected calls (exhaustive at C(8, B) = 8, 28, 56, 70 calls):

| Calls | ret B=1 | ret B=2 | ret B=3 | ret B=4 | gol B=1 | gol B=2 | gol B=3 | gol B=4 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0.431 M | 0.665 M | 0.674 M | 0.576 M | 0.375 M | 0.674 M | 0.760 M | 0.654 M |
| 4 | 0.205 M | 0.351 M | 0.325 M | 0.216 M | 0.210 M | 0.423 M | 0.457 M | 0.313 M |
| 8 | 0.000 A | 0.181 M | 0.178 M | 0.104 I | 0.000 A | 0.262 M | 0.308 M | 0.184 M |
| 9 | 0.000 A | 0.157 M | 0.159 M | 0.091 I | 0.000 A | 0.237 M | 0.286 M | 0.167 M |
| 16 | 0.000 A | 0.062 I | 0.089 I | 0.046 I | 0.000 A | 0.127 M | 0.188 M | 0.099 I |
| 18 | 0.000 A | 0.047 I | 0.079 I | 0.039 I | 0.000 A | 0.104 M | 0.170 M | 0.088 I |
| 26 | 0.000 A | 0.008 A | 0.049 I | 0.024 I | 0.000 A | 0.020 I | 0.115 I | 0.057 I |
| 32 | 0.000 A | 0.000 A | 0.034 I | 0.017 I | 0.000 A | 0.000 A | 0.085 I | 0.042 I |
| 48 | 0.000 A | 0.000 A | 0.009 I | 0.008 I | 0.000 A | 0.000 A | 0.026 I | 0.017 I |
| 64 | 0.000 A | 0.000 A | 0.000 A | 0.002 A | 0.000 A | 0.000 A | 0.000 A | 0.004 A |

Per-cell tables with intervals and the paired direct-search difference are in `tables.md`.
Readings:

- **B = 1.** Leave-one-in and greedy forward read every singleton, so they are exhaustive search
  at B = 1. Their zero regret there holds by construction and says nothing about credit.
- **Gold arm, B = 4 (51 tables).** The pattern repeats:
  - leave-one-out loses 0.200 (MISSPECIFIED);
  - SNIPW-64 loses 0.092, MSR-64 0.082, permutation Shapley-16 0.131;
  - exact Banzhaf loses 0.046 and exact Shapley 0.078;
  - greedy forward and backward each lose 0.098;
  - direct search's 99% upper bound reaches 0.05 at 46 calls.
- **The only exception to "direct search wins at equal calls"** is greedy forward at B = 2
  (15 calls): gold -0.100 [-0.170, -0.025], retrieved -0.044 [-0.107, 0.028]. No credit rule's
  95% interval lies below direct search in any cell.

## Surprises and caveats

1. **Direct search is the baseline to beat, and no credit rule beats it at equal calls.**
   Exhaustive search over 4-subsets is exact at 70 calls, fewer than exact credit's 256. One
   credit vector ranks memories for every budget at once, whereas direct search answers one
   budget. Covering B = 1..4 by direct search takes up to 8 + 28 + 56 + 70 = 162 calls. A credit
   rule's case would therefore rest on many budgets, or on cost per call, not on regret at one
   budget.
2. **SNIPW-64 is lower with 20 seeds (0.050) than AM1's 3-seed figure (0.070).**
   - This is the same code, and seeds 42-44 reproduce 0.070 exactly.
   - Single-seed means over the 38 tables range from 0.000 to 0.105 (SD 0.028), so a 3-seed
     average carries about ±0.016 of Monte Carlo noise here.
   - Permutation Shapley-16 agrees (0.095 against 0.097).
   - A registration that scores sampled rules should average more seeds.
3. **Banzhaf-type estimators (SNIPW, MSR) are ahead of Shapley-type ones (permutation, KernelSHAP)
   at every sampled size**, and their limit is lower (exact Banzhaf 0.031, exact Shapley 0.079).
   AM1's pilot already showed the exact values. Here the order holds along the whole curve.
4. **Greedy forward depends on tie-breaking.** It loses 0.105 with BM25-rank ties and 0.156 with
   uniform ties. With 0/1 utilities most single memories score 0, so the first step is mostly a
   tie. Backward elimination loses 0.079 with rank ties and 0.059 with uniform ties.
5. **The harness's SNIPW uses float arithmetic.** In 265 of 12,460 SNIPW credit vectors (2.1%),
   rounding orders or ties memories differently from exact arithmetic. The mean absolute effect
   on regret is about 0.0002 per draw. SNIPW is kept exactly as the harness computes it.
6. **Calls are not equal cost.** A 7-memory prompt (a leave-one-out call) costs more tokens than
   a 4-memory one (a direct-search call at B = 4). Token cost is not modelled.
7. **Memoization assumes the reader replays deterministically.** Eager replay was bit-exact in
   AM1. The pilot's tables, however, come from job 1411's GPU-0 compiled pass, in which 0.25% of
   judged cells differ from the typical compile (pilot README).

## What this does not show

- **No deployable keep policy.** Every rule reads judged correctness, which needs the reference
  answer. Utilities that need no label were not tested.
- **No confirmed result.** These are 38 retrieved development tables, and the intervals are wide.
  AM1's thresholds were sized for about 209 tables, so the labels here are descriptive.
- **No unbiased estimate for a chosen rule.** Picking the best rule or size from this curve and
  quoting its regret on the same tables would be optimistic. A claim needs a registration on the
  held-out tables, and it must disclose that AM1 already used those tables for other estimands
  (D112).
- **Nothing beyond this setup:** other readers, judges, retrievers, pool sizes or memory units,
  or training a memory learner on these credits.
- **Search variants not tried:** credit-guided candidate lists followed by evaluation, adaptive
  (bandit) search, and stratified or antithetic sampling.

## Reproduce

From the repository root, CPU only. It ran in the repository's virtualenv (Python 3.13.14,
numpy 2.5.2). It took about 40 s of CPU, or 4-5 min of wall clock in the CPU-throttled sandbox
where it ran.

```bash
uv run python scripts/memcredit_cost_curve.py \
    --tables program/evidence/2026-10-15/am1-dev-pilot/analysis/tables.json.gz \
    --h2 program/evidence/2026-10-15/am1-dev-pilot/analysis/h2.json \
    --output-dir program/evidence/2026-10-15/am1b-cost-curve
uv run python scripts/memcredit_cost_curve.py --validate-only   # Step 1 only
uv run pytest -q tests/test_memcredit_cost_curve.py             # 26 tests
```

The defaults are the same: 20 seeds from base 42, 10,000 bootstrap resamples with seed 42, and
both input digests. Two full runs gave byte-identical `results.json` and `per-table.json.gz`.

## Files

- `results.json`, the aggregates:
  - inputs and digests, config, seeds and rule definitions;
  - the Step 1 validation counts;
  - per arm and budget, every rule's calls, mean regret, 95% and 99% intervals, label, seed
    standard error, and difference from direct search at the same calls;
  - the full direct-search curve;
  - the headline answers (`answers`).
- `per-table.json.gz`: per table and rule, the regret (with per-seed values for stochastic
  rules), calls and the matched direct-search regret, plus each table's direct-search curve.
- `tables.md`: every cell's table, generated by the script.
- Code: `scripts/memcredit_cost_curve.py`. Tests: `tests/test_memcredit_cost_curve.py`, which
  covers the decoding against the committed regrets, memoized call counting, and the greedy and
  direct-search rules on hand-made toy tables.
