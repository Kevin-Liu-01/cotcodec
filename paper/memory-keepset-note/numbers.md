# Claims check: every number in `note.md` and its source

Each row lists numbers as `note.md` states them, the claim's status, the source file and
the source text they were checked against. Source text is verbatim, with whitespace
collapsed, `**` and backticks dropped, and table pipes written `\|`; several fragments are
separated by ` … `. The check was mechanical: every fragment was found in its source file
at `1cf31346`, every number was found in its fragments, and every number was found in
`note.md` (a leading `+` ignored). Rows marked `derived` give the arithmetic instead.
Section numbers, decision numbers, table numbers, ledger-row identifiers inside source
names, commit and file digests, this table's row ids, the note's own date, and the B, k, K
and m of the design notation are identifiers, not claims, and are not listed.

Source keys:

- AM1-REG: `program/preregistrations/am1-memory-credit-v1.md`
- KS-REG: `program/preregistrations/am1-keepset-search-v1.md`
- AM3G-REG: `program/preregistrations/am3-nonabstain-generality-v1.md`
- AM5R-REG: `program/preregistrations/am5-ablated-cost-v2.md`
- PILOT: `program/evidence/2026-10-15/am1-dev-pilot/README.md`
- AM1: `program/evidence/2026-10-16/am1-confirmatory/RESULTS.md`
- AM1B: `program/evidence/2026-10-15/am1b-cost-curve/README.md`
- AM1D: `program/evidence/2026-10-15/am1d-label-free/README.md`
- KS: `program/evidence/2026-10-16/am1-keepset-search/RESULTS.md`
- AM3D: `program/evidence/2026-10-16/am3-reader-replication/README.md`
- AM3G: `program/evidence/2026-10-15/am3-nonabstain-generality-v1/RESULTS.md`
- AM4: `program/evidence/2026-10-16/am4-read-caps/README.md`
- AM5: `program/evidence/2026-10-16/am5-evidence-ablated/README.md`
- AM5DRY: `program/evidence/2026-10-16/am5-ablated-cost-dev-dryrun/README.md`
- AM5R: `program/evidence/2026-10-16/am5-ablated-cost-v2/RESULTS.md`
- AM5RT: `program/evidence/2026-10-16/am5-ablated-cost-v2/tables.md`
- AUDIT: `program/evidence/2026-10-16/novelty-audit/AUDIT.md`
- SWEEP: `program/evidence/2026-10-14/question-sweep-memory-gpu/dossier.md`
- DEC: `program/decisions.md`
- LEDGER: `program/preregistrations/ledger.jsonl`
- derived: computed from listed rows; arithmetic shown.

| ID | Note | Number(s) | Status | Source | Source text |
|---|---|---|---|---|---|
| N001 | Status | 347 | confirmatory (population) | AM3G-REG | The 347 questions of H1 are AM1's confirmatory set |
| N002 | Summary | 8; 4; 256 | design | AM1-REG | at a budget of 4 kept of 8 … per pool 256 subsets + 16 swaps + 2 reorders = 274 |
| N003 | Summary | 251; 0.277; 0.223; 0.333 | confirmatory | AM1 | K4 is not underpowered (251 non-constant retrieved tables) … keep sets lose 0.277 (99% [0.223, 0.333]) of a correct answer per non-constant table |
| N004 | Summary | 0.233; 0.194; 0.273 | confirmatory | AM1 | They lose 0.233 [0.194, 0.273] more than exact Shapley credit |
| N006 | Summary | 26; 57-83; +0.0014 | confirmatory | KS | even when search reads 26 subsets to their 57-83 … its one-sided 99.29% upper bound is +0.0014 |
| N007 | Summary | +0.112; 0.081; 0.147; 39; 0 | confirmatory | KS | +0.112 [+0.081, +0.147], 39 gained, 0 lost |
| N008 | Summary | +0.101; 0.069; 0.133; 35; +0.089; 0.061; 0.121; 31 | confirmatory | AM3G | \| OLMo-2-1124-7B-Instruct \| 0.329 \| 0.429 \| 35 \| 0 \| +0.101 [+0.069, +0.133] \| 1.2e-10 \| 35, 0: confirmed \| … \| Qwen3.5-9B \| 0.464 \| 0.553 \| 31 \| 0 \| +0.089 [+0.061, +0.121] \| 9.3e-10 \| 31, 0: confirmed \| |
| N009 | Summary | 30; 5, 8; 1; 0 | descriptive; judge-qualified | DEC | on the 30 unanswerable questions the rule turns correct abstentions into wrong answers 5, 8 and 1 times (hand counts 5, 8 and 0) |
| N013 | 1 | 2026-10-14 | record | SWEEP | # Question sweep: agent-memory causality and GPU memory (2026-10-14) |
| N014 | 1, Table 1 | 63; 126 | exploratory | DEC | on the 63-question development split of LongMemEval-S only … It built 126 exact 256-subset tables |
| N015 | 1, Table 1 | 347; 694 | confirmatory (population) | KS-REG | AM1's 694 committed held-out tables … the 347 of AM1's confirmatory set |
| N016 | 1, Table 1 | 30 | descriptive (population) | AM3G | LongMemEval-S has 30 abstention questions, never used before. |
| N017 | 2.1 | 1; 6; 416; 500 | design | PILOT | 1 to 6 gold turns (416 of 500; every question type kept) |
| N018 | 2.1 | 15%; 63; 353 | design | PILOT | the first round-half-up(15%) are development … development 63 (TR 19, MS 18, KU 11, SSU 9, SSP 5, SSA 1), held out 353 |
| N019 | 2.1 | 347; 59; 101; 4; 25; 52; 106 | design | AM1-REG | 347 ids … (knowledge-update 59, multi-session 101, single-session-assistant 4, single-session-preference 25, single-session-user 52, temporal-reasoning 106) |
| N020 | 2.1 | 30 | design | AM3G-REG | every LongMemEval-S id ending in _abs: 30 ids |
| N021 | 2.2 | 1,500; 8 | design | AM1-REG | one user turn with its session date, at most 1,500 characters … Pool arms (k = 8, chronological |
| N022 | 2.2 | 1.5; 0.75 | design | AM1-REG | Okapi with Lucene's idf, k1 1.5, b 0.75 |
| N023 | 2.2 | 43; 117; 174; 13 | descriptive | AM1 | The retrieved pool holds no gold turn for 43 questions, 1 for 117, 2 for 174, and 3-5 for 13. |
| N024 | 2.2 | 4 | design | AM1-REG | at a budget of 4 kept of 8 |
| N025 | 2.3 | 64; 0.31.0 | design | AM1-REG | greedy, at most 64 new tokens … vLLM 0.31.0 |
| N026 | 2.3 | 4,096; 1.32-1.38x | exploratory | DEC | Greedy gave 4,096 of 4,096 under shuffled order, an engine restart and a reconfigured engine … The cost is 1.32-1.38x wall time when batched |
| N027 | 2.3 | 1411; 33,463; 34,524; 96.93%; 87; 34,399; 0.25%; 41; 126; 2048; 4096; 8,768; 1.06x | exploratory | PILOT | The reader's GPU-1 replicate in job 1411 … matched the GPU-0 pass in tokens for 33,463 of 34,524 requests (96.93% … judged correctness differs on 87 of the 34,399 requests whose two replies are both judged (0.25% … in 41 of 126 tables … R0_BLOCK 2048 against 4096 … (8,768 of 8,768 in every comparison), at 1.06x the compiled pass's wall time |
| N028 | 2.3 | 190,156; 10,230 | confirmatory (gate G1) | AM1 | G1 replay PASS: 190,156 of 190,156 reader requests and 10,230 of 10,230 judge items gave identical tokens and log-prob bits across GPUs and orders. |
| N029 | 2.4 | 117; 120; 0.95; 109; 0.82; 0.45 | exploratory | PILOT | agrees with a blind hand check of 120 judged replies on 117 (97.5%, [92.9%, 99.5%], Cohen's kappa 0.95 … Qwen3-8B with the same prompt: 109 of 120 (kappa 0.82 … containment rule: 87 of 120 (kappa 0.45) |
| N030 | 2.4 | 322; 347; 120; 0.867; 0.80; 0.767; 0.950 | confirmatory (gate G2) | AM1 | G2 judge PASS: validation 322 of 322 and 347 of 347; hand-check kappa 0.867 against the 0.80 bar. … kappa 0.867, 95% [0.767, 0.950], n = 120 |
| N031 | 2.4 | 7; 8 | descriptive (post-join, not registered) | AM1 | 7 of the 8 disagreements are on single-session-preference items |
| N032 | 2.4 | 49; 347 | descriptive | KS-REG | called "I don't know." correct on 49 of 347 held-out validation items |
| N033 | 2.5 | 256; 16; 2; 274; 190,156 | design | AM1-REG | per pool 256 subsets + 16 swaps + 2 reorders = 274; 347 x 2 x 274 = 190,156 reader requests per pass. |
| N034 | 2.5 | 694 | design | AM1 | Raw attention succeeded on 694 of 694 pools |
| N035 | 2.5 | 251; 288 | descriptive | KS-REG | non-constant counts other than 251 retrieved and 288 gold |
| N036 | 2.5 | 0.05 | design | AM1-REG | MISSPECIFIED if the lower bound exceeds 0.05: keep sets chosen by r lose, relative to the exact optimum, more than one correct answer in twenty |
| N037 | 2.5 | 9; 8; 256 | design | AM1B | \| loo, leave_one_in, loo_plus_loi \| - \| 9, 9, 18 \| harness mc.loo_credit (full set + 8) … \| shapley_exact, banzhaf_exact \| - \| 256 \| references \| |
| N038 | 2.6 | 4,000; 1,000 | design | AM1-REG | Intervals are percentile intervals from 4,000 bootstrap resamples of questions with replacement (harness.memcredit_study.cluster_bootstrap, numpy default_rng(42); for AUROC, 1,000 resamples in scripts/memcredit_analyze.py), 95% unless stated. |
| N039 | 2.6 | 10,000 | design | KS-REG | Question-cluster percentile bootstrap, harness.memcredit_study.cluster_bootstrap: 10,000 resamples of questions |
| N040 | 2.6 | 10,000 | design | AM1B | Intervals use ms.cluster_bootstrap: 10,000 resamples of questions |
| N041 | 2.6 | 10,000 | design | AM1D | 10,000 resamples, seed 42 |
| N042 | 2.6 | 10,000; 30 | design | AM3G-REG | (harness.memcredit_study.cluster_bootstrap, 10,000 resamples, numpy default_rng(42)) … Rates over the 30 abstention questions get exact Clopper-Pearson intervals |
| N043 | 3 | 63; 53; 89; 58 | exploratory | DEC | on the 63-question development split of LongMemEval-S only … Of 89 non-constant tables, 53 are non-monotone, and a non-gold memory matters in 58. |
| N044 | 3 | 0.214; 0.121; 0.316; 0.079; +0.135; 0.051; 0.227 | exploratory | PILOT | leave-one-out (Hindsight-PRM's one-shot deletion) 0.214 [0.121, 0.316] … exact Shapley 0.079 [0, 0.184] … Leave-one-out loses 0.135 [0.051, 0.227] more than exact Shapley on the retrieved arm |
| N045 | 3 | 99%; 0.05; 0.02 | design | AM1-REG | with a 99% interval for R_r (Bonferroni over the five rules, family-wise 95%) … MISSPECIFIED if the lower bound exceeds 0.05 … ADEQUATE if the upper bound is below 0.02 |
| N046 | 3, gates | 43; 347; 12.4%; 60%; 251; 150 | confirmatory (gates) | AM1 | 43 of 347 (12.4%) … > 60% of questions constant in both arms … < 150 non-constant retrieved tables … K4 is not underpowered (251 non-constant retrieved tables) |
| N047 | 3, Table 2 | 9; 0.277; 0.235; 0.319; 0.223; 0.333; 0.546; +0.233; +0.194; +0.273 | confirmatory | AM1 | \| leave-one-out (deletion), the headline \| 251 \| 0.277 [0.235, 0.319] \| [0.223, 0.333] \| MISSPECIFIED \| 0.546 \| +0.233 [+0.194, +0.273] \| … \| leave-one-out (deletion) \| 9 \| |
| N048 | 3, Table 2 | 129; 0.138; 0.107; 0.173; 0.096; 0.187; 0.279; +0.094; +0.066; +0.126 | confirmatory (paired difference descriptive) | AM1 | \| permutation Shapley, 16 \| 251 \| 0.138 [0.107, 0.173] \| [0.096, 0.187] \| MISSPECIFIED \| 0.279 \| +0.094 [+0.066, +0.126] \| … \| permutation Shapley, 16 \| <= 129 \| |
| N049 | 3, Table 2 | 64; 0.094; 0.066; 0.123; 0.058; 0.133; 0.171; +0.050; +0.023; +0.078 | confirmatory (paired difference descriptive) | AM1 | \| SNIPW, 64 exposures \| 251 \| 0.094 [0.066, 0.123] \| [0.058, 0.133] \| MISSPECIFIED \| 0.171 \| +0.050 [+0.023, +0.078] \| … \| SNIPW, 64 exposures \| 64 \| |
| N050 | 3, Table 2 | 0; 0.343; 0.287; 0.402; 0.271; 0.418; +0.299; +0.243; +0.359 | confirmatory (paired difference descriptive) | AM1 | \| retrieval rank \| 251 \| 0.343 [0.287, 0.402] \| [0.271, 0.418] \| MISSPECIFIED \| 0.343 \| +0.299 [+0.243, +0.359] \| … \| retrieval rank \| 0 \| |
| N051 | 3, Table 2 | 1 + 1 forward; 0.311; 0.251; 0.371; 0.235; 0.382; +0.267; +0.207; +0.323 | confirmatory (paired difference descriptive) | AM1 | \| attention, raw \| 251 \| 0.311 [0.251, 0.371] \| [0.235, 0.382] \| MISSPECIFIED \| 0.311 \| +0.267 [+0.207, +0.323] \| … \| attention, raw \| 1 + 1 forward \| |
| N052 | 3, Table 2 | 256; 0.044; 0.020; 0.072; 0.012; 0.080 | descriptive (reference) | AM1 | \| exact Shapley (reference, not in the family) \| 251 \| 0.044 [0.020, 0.072] \| [0.012, 0.080] \| \| 0.044 \| \| … \| exact Shapley \| 256 \| |
| N053 | 3, Table 2 | 0.025; 0.009; 0.043; 0.005; 0.050; 0.036 | descriptive (reference) | AM1 | \| exact Banzhaf (reference, not in the family) \| 251 \| 0.025 [0.009, 0.043] \| [0.005, 0.050] \| \| 0.036 \| |
| N054 | 3, Table 2 | 0.625; 0.596; 0.653; 0.587; 0.661; 0.976 | descriptive (reference) | AM1 | \| random keep set (reference, not in the family) \| 251 \| 0.625 [0.596, 0.653] \| [0.587, 0.661] \| \| 0.976 \| |
| N055 | 3 | 55% | confirmatory | AM1 | They are suboptimal in 55% of tables. |
| N056 | 3 | 0.01 | design | AM1-REG | ADEQUATE needs a true regret below about 0.01 (section 9), so it is nearly out of reach |
| N057 | 3, SNIPW-64 seeds | 0.058 | confirmatory | AM1 | SNIPW-64 is the closest call: its 99% lower bound is 0.058 |
| N058 | 3, SNIPW-64 seeds | 0.094; 0.070 | confirmatory (3 seeds) and exploratory | KS-REG | SNIPW-64 (seeds 42-44) 0.070 and 0.094 |
| N059 | 3, SNIPW-64 seeds | 3 | design | AM1-REG | regret is averaged over draws with seeds 42, 43, 44 |
| N060 | 3, SNIPW-64 seeds | 200; 0.085 | confirmatory run (regret descriptive) | KS | SNIPW-64 0.085 … Sampled rules are averaged over 200 seeds |
| N061 | 3, SNIPW-64 seeds | 0.070; 0.050; 20 | exploratory | AM1B | SNIPW-64 is lower with 20 seeds (0.050) than AM1's 3-seed figure (0.070). |
| N062 | 3, budgets (every lower bound above 0) | +0.149; +0.256 | descriptive | AM1 | \| retrieved \| +0.149 [+0.112, +0.188] \| +0.254 [+0.206, +0.300] \| +0.256 [+0.215, +0.299] \| +0.233 [+0.194, +0.273] \| |
| N063 | 3, budgets (every lower bound above 0) | +0.104; +0.207 | descriptive | AM1 | \| gold \| +0.104 [+0.075, +0.136] \| +0.159 [+0.122, +0.198] \| +0.191 [+0.154, +0.230] \| +0.207 [+0.169, +0.245] \| |
| N064 | 3, second judge | 260; 0.259; 0.206; 0.312; +0.201; +0.167; +0.239 | descriptive (sensitivity) | AM1 | Qwen3-8B's labels give 260 non-constant retrieved tables … \| leave-one-out \| 0.259 \| [0.206, 0.312] \| … Leave-one-out minus exact Shapley is +0.201 [+0.167, +0.239]. |
| N065 | 3, K3 | 539; 51.8%; 96.1% | confirmatory (gate K3) | AM1 | 29.7% of 539 tables; LOO optimal 51.8%; exact Shapley 96.1% |
| N066 | 3, H1 | 0.379; 0.342; 0.416; +0.156; +0.119; +0.194; 251 | descriptive | AM1 | \| retrieved \| 251 (246 with m ≥ 1) \| 0.379 [0.342, 0.416] \| +0.156 [+0.119, +0.194] \| |
| N067 | 3, H1 | +0.094; +0.058; +0.129 | descriptive | AM1 | +0.094 [0.058, 0.129] (gold) … +0.094 [+0.058, +0.129] |
| N068 | 3, census | 167; 57; 12; 8; 7; 182 | descriptive | AM1 | \| retrieved \| 347 \| 96 \| 251 \| 0.524 \| 167 \| 57 \| 12 \| 8 \| 7 \| 182 \| |
| N069 | 3, AM2 | 0.440; 0.399; 0.483; 0.441; 0.400; -0.0008; -0.0097; +0.0082; 0.641; 0.586; 0.697 | descriptive (registered secondary) | AM1 | \| gold \| 0.440 [0.399, 0.483] (1,198) \| 0.441 [0.400, 0.483] (2,396) \| -0.0008 [-0.0097, +0.0082] \| … 0.641 [0.586, 0.697] (527 labels) |
| N070 | 3, AM2 | 0.072; 0.059; 0.085; 0.062; 0.051; 0.074; +0.0099; +0.0026; +0.0170; 0.128; 0.086; 0.175 | descriptive (registered secondary) | AM1 | \| non-gold \| 0.072 [0.059, 0.085] (4,354) \| 0.062 [0.051, 0.074] (8,708) \| +0.0099 [+0.0026, +0.0170] \| … 0.128 [0.086, 0.175] (313 labels) |
| N071 | 3, AM2 | +0.0026; +0.0204; +0.0090; +0.0324; +0.0002; -0.0094; +0.0103 | descriptive | AM1 | The 95% lower bound of the non-gold deletion-minus-swap difference, +0.0026, is above 0. … the non-gold difference is +0.0002 [-0.0094, +0.0103] on the retrieved arm and +0.0204 [+0.0090, +0.0324] on the gold arm |
| N072 | 3, AM2 | 12.8%; 64.1%; 17.1%; 14.6%; 19.8% | descriptive | AM1 | 12.8% of nonzero non-gold labels survive … against 64.1% of gold labels … changes u(full) in 17.1% [14.6%, 19.8%] of reorders |
| N073 | 3, AM2 pilot | +0.0006; -0.013; 0.013; -0.017; -0.040; 0.001 | exploratory | PILOT | by 0.0006 [-0.013, 0.013] over both arms (retrieved -0.017 [-0.040, 0.001], gold 0.020 [-0.004, 0.048] |
| N074 | 3, AM6 | 0.890; 0.865; 0.914; 0.060; 0.830; 0.832 | descriptive (registered secondary) | AM1 | \| attention, cross-fitted heads \| 0.890 [0.865, 0.914] \| … The best attention signal (0.890) is 0.060 above the best cheap baseline (0.830) … Raw attention (0.832) ties the reply-overlap baseline. |
| N075 | 4.1 | 70; 0 | exploratory | AM1B | \| 70 \| 0.000 \| [0.000, 0.000] \| [0.000, 0.000] \| ADEQUATE \| |
| N076 | 4.1, Table 3 | 38; 0; 0.132; 0.026; 0.237; 0.576 | exploratory | AM1B | 38 non-constant tables. … \| retrieval_rank \| 0 \| 0.132 \| [0.026, 0.237] \| [0.026, 0.289] \| INCONCLUSIVE \| 0.576 \| |
| N077 | 4.1, Table 3 | 9; 0.214; 0.123; 0.316; 0.091 | exploratory | AM1B | \| loo \| 9 \| 0.214 \| [0.123, 0.316] \| [0.099, 0.348] \| MISSPECIFIED \| 0.091 \| |
| N078 | 4.1, Table 3 | 26; 0.105; 0.026; 0.211; 0.024 | exploratory | AM1B | \| greedy_forward \| 26 \| 0.105 \| [0.026, 0.211] \| [0.000, 0.263] \| INCONCLUSIVE \| 0.024 \| |
| N079 | 4.1, Table 3 | 26; 0.079; 0.000; 0.184; 0.024 | exploratory | AM1B | \| greedy_backward \| 26 \| 0.079 \| [0.000, 0.184] \| [0.000, 0.211] \| INCONCLUSIVE \| 0.024 \| |
| N080 | 4.1, Table 3 | 20; 56.8; 0.050; 0.014; 0.099; 0.005 | exploratory | AM1B | \| snipw_64 \| 56.8 (48-63) \| 0.050 (se 0.006) \| [0.014, 0.099] \| [0.009, 0.118] \| INCONCLUSIVE \| 0.005 \| … Stochastic rules run 20 seeds |
| N081 | 4.1, Table 3 | 64; 0.043; 0.009; 0.091; 0.002 | exploratory | AM1B | \| msr_banzhaf_64 \| 64 \| 0.043 (se 0.005) \| [0.009, 0.091] \| [0.005, 0.111] \| INCONCLUSIVE \| 0.002 \| |
| N082 | 4.1, Table 3 | 83.4; 0.095; 0.032; 0.171; 0.000 | exploratory | AM1B | \| perm_shapley_16 \| 83.4 (72-94) \| 0.095 (se 0.005) \| [0.032, 0.171] \| [0.019, 0.200] \| INCONCLUSIVE \| 0.000 \| |
| N083 | 4.1, Table 3 | 256; 0.031; 0.000; 0.079 | exploratory | AM1B | \| banzhaf_exact \| 256 \| 0.031 \| [0.000, 0.079] \| [0.000, 0.096] \| INCONCLUSIVE \| 0.000 \| |
| N084 | 4.1, Table 3 | 256; 0.079; 0.000; 0.184 | exploratory | AM1B | \| shapley_exact \| 256 \| 0.079 \| [0.000, 0.184] \| [0.000, 0.211] \| INCONCLUSIVE \| 0.000 \| |
| N085 | 4.1 | 0.091; 9; 0.046; 16; 0.024; 26; 0.017; 32 | exploratory | AM1B | \| 9 \| 0.091 \| [0.037, 0.156] \| … \| 16 \| 0.046 \| [0.011, 0.096] \| … \| 26 \| 0.024 \| [0.002, 0.060] \| … \| 32 \| 0.017 \| [0.001, 0.047] \| |
| N086 | 4.1 | 99%; 0.05 | exploratory | AM1B | No credit rule has a 99% upper bound at or below 0.05, and none is ADEQUATE. |
| N087 | 4.1 | 0; 15 | exploratory | DEC | retrieval rank (0 calls, 0.132) beats every rule below about 15 calls |
| N088 | 4.1 | 2; 95% | exploratory | AM1B | Only greedy forward at gold B = 2 has a 95% interval below zero. |
| N089 | 4.1 | 1; 4; 162 | exploratory | AM1B | Covering B = 1..4 by direct search takes up to 8 + 28 + 56 + 70 = 162 calls. |
| N090 | 4.2 | 694 | confirmatory (input) | KS | They are AM1's 694 held-out tables (job 1458). |
| N091 | 4.2 | 251; 200 | confirmatory | KS | ## H-A, retrieved arm (251 non-constant tables, keep 4 of 8) … Sampled rules are averaged over 200 seeds |
| N092 | 4.2 | 1 - 0.05/7; 3 | design | KS-REG | one-sided upper and lower percentile bootstrap bounds of the mean of D_j at nominal level 1 - 0.05/7 … A bound clears 0 only if it clears it by more than 3 Monte Carlo standard errors |
| N093 | 4.2, Table 4 | 9; -0.151; -0.180; -0.124; -0.187; -0.117 | confirmatory | KS | \| A1 \| leave-one-out vs direct search, both 9 calls \| 9 \| -0.151 \| [-0.180, -0.124] \| -0.187, -0.117 \| SEARCH_BETTER \| |
| N094 | 4.2, Table 4 | 56.7; -0.078; -0.098; -0.059; -0.104; -0.055 | confirmatory | KS | \| A2 \| SNIPW-64 vs direct search at the same calls \| 56.7 \| -0.078 \| [-0.098, -0.059] \| -0.104, -0.055 \| SEARCH_BETTER \| |
| N095 | 4.2, Table 4 | 56.7; 26; -0.049; -0.062; -0.036; -0.066; -0.034 | confirmatory | KS | \| A3 \| SNIPW-64 vs direct search at 26 calls \| 56.7 \| -0.049 \| [-0.062, -0.036] \| -0.066, -0.034 \| SEARCH_BETTER \| |
| N096 | 4.2, Table 4 | 64; -0.076; -0.097; -0.056; -0.102; -0.051 | confirmatory | KS | \| A4 \| MSR-Banzhaf-64 vs direct search, both 64 calls \| 64 \| -0.076 \| [-0.097, -0.056] \| -0.102, -0.051 \| SEARCH_BETTER \| |
| N097 | 4.2, Table 4 | 64; 26; -0.042; -0.055; -0.030; -0.059; -0.027 | confirmatory | KS | \| A5 \| MSR-Banzhaf-64 vs direct search at 26 calls \| 64 \| -0.042 \| [-0.055, -0.030] \| -0.059, -0.027 \| SEARCH_BETTER \| |
| N098 | 4.2, Table 4 | 83.3; 26; -0.096; -0.119; -0.073; -0.125; -0.068 | confirmatory | KS | \| A6 \| permutation Shapley-16 vs direct search at 26 calls \| 83.3 \| -0.096 \| [-0.119, -0.073] \| -0.125, -0.068 \| SEARCH_BETTER \| |
| N099 | 4.2, Table 4 | 26; -0.032; -0.062; -0.005; -0.069; +0.0014 | confirmatory | KS | \| A7 \| greedy backward (BM25 ties) vs direct search, both 26 calls \| 26 \| -0.032 \| [-0.062, -0.005] \| -0.069, +0.001 \| NOT_SEPARATED \| … its one-sided 99.29% upper bound is +0.0014 |
| N100 | 4.2 | 0.277; 0.085; 0.078; 0.132; 0.068 | confirmatory run (regrets descriptive) | KS | Leave-one-out loses 0.277, SNIPW-64 0.085, MSR-Banzhaf-64 0.078, permutation Shapley-16 0.132 and greedy backward 0.068. |
| N101 | 4.2 | 0.141; 8; 0.126; 9; 0.067; 16; 0.036; 26; 0.020; 38; 0.003; 64; 0; 70 | confirmatory run (descriptive curve) | KS | Direct search's exact regret by calls is 0.141 at 8, 0.126 at 9, 0.067 at 16, 0.036 at 26, 0.020 at 38, 0.003 at 64 and 0 at 70. |
| N102 | 4.2 | 56.7-83.3 | derived | KS | \| A3 \| SNIPW-64 vs direct search at 26 calls \| 56.7 \| … \| A6 \| permutation Shapley-16 vs direct search at 26 calls \| 83.3 \| |
| N103 | 4.2 | 200; +0.0005; +0.0032 | confirmatory run (verifier check) | KS | Under 200 other bootstrap seeds the verifier found the upper bound stays positive, between +0.0005 and +0.0032. |
| N105 | 4.2 | 0.05 | design (size simulation) | KS-REG | Every measured verdict error was under 0.05. |
| N106 | 5.1 | 63; 4 | exploratory | AM1D | The data are the 63 development questions in two arms (126 tables). … The four patterns below were committed at 7465903f before the script had read any reply. |
| N107 | 5.1 | 2,405; 4,410; 54.5%; 2 | exploratory | AM1D | \| abstaining (pattern list) \| 2,405 (54.5%) \| 2,599 (58.9%) \| … \| 4-subset replies \| 4,410 \| 4,410 \| … \| abstaining replies judged correct \| 2 \| 2 \| |
| N108 | 5.1 | -5.3e-6; -0.0037; -0.0131 | exploratory (post hoc diagnostic) | AM1D | \| median mean log-prob: abstaining replies \| -5.3e-6 \| -2.2e-6 \| … \| median mean log-prob: non-abstaining replies judged correct \| -0.0037 \| -0.0037 \| … \| median mean log-prob: non-abstaining replies judged wrong \| -0.0131 \| -0.0112 \| … The reader's abstentions are its most confident replies (post hoc, added at ccd077e7). |
| N109 | 5.1 | 0.326; 0.854 | exploratory | AM1D | \| retrieved \| 0.326 \| 0.294 \| 0.854 \| 0.718 \| 0.314 \| 0.861 \| 0.861 \| 0.865 \| |
| N110 | 5.1 | 0.208; 38; 8; 0.105; 70; 0.842 | exploratory | AM1D | Keeping the most confident reply is right on 0.208 of tables at 8 calls and 0.105 at 70 calls (mean log-prob). … ## Answer (retrieved arm, keep 4 of 8, 38 non-constant tables) … \| BM25 top 4 \| 1 \| 0.842 \| |
| N111 | 5.1 | 0.318; 0.237 | exploratory | AM1D | The majority reply is usually an abstention: 0.318 at 8 calls, 0.237 at 70. |
| N112 | 5.1 | 0.868; +0.026; +0.000; +0.079; 38; one | exploratory | AM1D | \| best label-free in sample: nonabstain@70 \| 70 \| 0.868 \| +0.026 [+0.000, +0.079] \| … Its gain over BM25 top 4 is one table of 38 |
| N113 | 5.1 | 40 | exploratory | KS-REG | nonabstain@70 was the best of 40 label-free rules in sample |
| N114 | 5.1 | +0.025; 70 | exploratory | AM1D | it is +0.025 at 70 calls |
| N115 | 5.1 | +0.105; +0.026; +0.211; 4; 0; 0.125 | exploratory | AM1D | BM25 top 4 is ahead of the full pool by +0.105 [+0.026, +0.211]. That rests on 4 tables against 0 (exact sign test p = 0.125) |
| N116 | 5.2 | 70; 4 | design | KS-REG | The 70 4-subsets are read in ascending sum of their four BM25 ranks |
| N117 | 5.2 | 347 | design | KS-REG | Over all 347 questions, retrieved arm: b (nonabstain-BM25 right, BM25 top 4 wrong) |
| N118 | 5.2 | 0.571; 0.458; +0.112; +0.081; +0.147; 39; 0; 3.6e-12 | confirmatory | KS | \| H-C: nonabstain-BM25 minus BM25 top 4 \| retrieved \| 0.571 \| 0.458 \| 39 \| 0 \| +0.112 \| [+0.081, +0.147] \| 3.6e-12 \| |
| N119 | 5.2 | +0.092; +0.112 | confirmatory | KS | H-C's exact conditional interval is [+0.092, +0.112]. |
| N120 | 5.2 | 13,598; 24,290; 56%; 116; 71; 39; 45 | confirmatory run (descriptive) | KS | 56% of the reader's 4-subset replies on the retrieved arm abstain: 13,598 of 24,290. … BM25 top 4's own reply abstains on 116 questions. On 71 of them another 4-subset answers, and switching to it gained 39 and lost none. … In 45 pools every 4-subset abstains, and the rule keeps BM25 top 4. |
| N121 | 5.2 | 347 | descriptive | KS | which marked "I don't know." wrong on 347 of 347 validation items. |
| N122 | 5.2 | 0.458; 0.524; -0.066; -0.107; -0.026; 15; 38; 0.0022 | descriptive (H-B) | KS | \| H-B (descriptive): BM25 top 4 minus all 8 \| retrieved \| 0.458 \| 0.524 \| 15 \| 38 \| -0.066 \| [-0.107, -0.026] \| 0.0022 \| |
| N123 | 5.2 | +0.046; +0.006; +0.086; 33; 17; 0.033 | descriptive | KS | \| Nonabstain-BM25 minus all 8 (descriptive) \| retrieved \| 0.571 \| 0.524 \| 33 \| 17 \| +0.046 \| [+0.006, +0.086] \| 0.033 \| |
| N124 | 5.2 | +0.089; +0.061; +0.121; 31; 0 | descriptive | KS | \| H-C (descriptive) \| gold \| 0.663 \| 0.573 \| 31 \| 0 \| +0.089 \| [+0.061, +0.121] \| 9.3e-10 \| |
| N125 | 5.3 | 63; 71; 70 | exploratory | AM3D | Every number describes the AM1 pilot's 63 development questions … Per pool, the 70 4-subsets and the full pool of 8: 71 requests, 8,946 per reader. |
| N126 | 5.3 | 2,272 | exploratory | AM3D | 2,272 of 2,272 identical in tokens and log-prob bits |
| N127 | 5.3 | 0; 4; 0.125; 3; 0.25; 1; 39; six | exploratory | AM3D | c = 0 in all six reader-by-arm cells … OLMo-2: 4 against 0, p = 0.125; … Qwen3.5-9B: 3 against 0, p = 0.25. … The anchor gains 1 question against 0 here, where the held-out registration found 39 against 0 over 347 questions. |
| N128 | 5.3 | 6; 3; 4 | exploratory; the 4-of-6 split post hoc (AM3D) | DEC | Second judge (Qwen3-8B): 6 losses on 3 questions. … and 4 of the 6 are a bare "I don't know" judged correct, which is a judge error by the pilot's validation standard. |
| N129 | 5.3 | 2 | derived (6 - 4; post hoc, checked) | AM3D | are 24-word hedges that contain both "I don't know" and the one-word gold answer. They are ambiguous. |
| N130 | 5.4 | 347; 71 | design | AM3G-REG | Per pool, the 70 4-subsets (masks ascending) and the full pool (mask 255): 71 requests. Held-out: 347 x 2 x 71 = 49,274 per reader. |
| N131 | 5.4, Table 5 | 0.329; 0.429; 35; 0; +0.101; +0.069; +0.133; 1.2e-10 | confirmatory | AM3G | \| OLMo-2-1124-7B-Instruct \| 0.329 \| 0.429 \| 35 \| 0 \| +0.101 [+0.069, +0.133] \| 1.2e-10 \| 35, 0: confirmed \| |
| N132 | 5.4, Table 5 | 0.464; 0.553; 31; 0; +0.089; +0.061; +0.121; 9.3e-10 | confirmatory | AM3G | \| Qwen3.5-9B \| 0.464 \| 0.553 \| 31 \| 0 \| +0.089 [+0.061, +0.121] \| 9.3e-10 \| 31, 0: confirmed \| |
| N133 | 5.4, Table 5 | 0.458; 0.571; 39; 0; +0.112; +0.081; +0.147; 3.6e-12 | confirmatory (replay of KS) | KS | \| H-C: nonabstain-BM25 minus BM25 top 4 \| retrieved \| 0.571 \| 0.458 \| 39 \| 0 \| +0.112 \| [+0.081, +0.147] \| 3.6e-12 \| |
| N134 | 5.4 | 274; 278; 0.967 | confirmatory (hand check) | AM3G | The blind labels agree with the judge on 274 of 278 items (kappa 0.967). |
| N135 | 5.4 | 1458; 49,274 | confirmatory (gate V3) | AM3G | It replayed job 1458 token for token on 49,274 of 49,274 requests, and its labels equal AM1's tables. |
| N136 | 5.4 | 32; 12; 25; 6; 33; 7 | descriptive | AM3G | OLMo-2 32 against 12, Qwen3.5-9B 25 against 6, Qwen3-8B 33 against 7. |
| N137 | 5.4 | 37; 0; 19; 31 | descriptive | AM3G | OLMo-2 37 against 0, Qwen3.5-9B 19 against 0, Qwen3-8B 31 against 0. |
| N138 | 5.4 | 0.429; 0.352; 44; 17; 0.0007 | descriptive | AM3G | \| OLMo-2 \| 0.352 \| 0.429 \| 44 : 17 \| 0.0007 \| |
| N139 | 5.4 | 0.571; 0.524; 33; 17; 0.033 | descriptive | AM3G | \| Qwen3-8B \| 0.524 \| 0.571 \| 33 : 17 \| 0.033 \| |
| N140 | 5.4 | 0.553; 0.524; 26; 16; 0.16 | descriptive | AM3G | \| Qwen3.5-9B \| 0.524 \| 0.553 \| 26 : 16 \| 0.16 \| |
| N141 | 6.1 | 30 | descriptive | AM3G | LongMemEval-S has 30 abstention questions, never used before. |
| N142 | 6.1 | 30; 7; 0.8; 0.3 | design | AM3G-REG | With 30 questions and Holm across three readers, the exact McNemar test rejects at its first step only when b2 >= 7 (with c2 = 0). … Power reaches 0.8 only when the cost rate is about 0.3 or more. |
| N143 | 6.1, Table 6 | 30; 25; 5; 0; 0.167; 0.056; 0.347 | descriptive; judge-qualified | AM3G | \| Qwen3-8B \| 30 \| 25 \| 5 \| 0 \| 0.167 [0.056, 0.347] \| 5, 0 \| |
| N144 | 6.1, Table 6 | 25; 17; 8; 0; 0.267; 0.123; 0.459 | descriptive; judge-qualified | AM3G | \| OLMo-2 \| 25 \| 17 \| 8 \| 0 \| 0.267 [0.123, 0.459] \| 8, 0 \| |
| N145 | 6.1, Table 6 | 29; 28; 1; 0; 0.033; 0.001; 0.172 | descriptive; judge-qualified | AM3G | \| Qwen3.5-9B \| 29 \| 28 \| 1 \| 0 \| 0.033 [0.001, 0.172] \| 0, 0 \| |
| N146 | 6.1 | 26; 30; 29 | descriptive (failed gate G-J2) | AM3G | G-J2 failed: the abstention judge rejected 26 of 30 decoy answers, and the registered bar was 29. |
| N147 | 6.1 | 0-2 | descriptive | AM3G | The judge called the rule's switched reply correct on only 0-2 pools per reader. |
| N148 | 6.1 | 0; 1/30 | descriptive (hand labels) | AM3G | The hand label rejects it as a cost, so the hand count is 0. … Qwen3-8B's two H2 accuracies are each 1/30 too high. |
| N149 | 6.1 | 27; 30; 22 | descriptive | AM3G | 27 of the 30 share memories with an answerable twin, and 22 twins are in H1's population. |
| N150 | 6.2 | 470; 30; 347; 0.94; 0.06 | design | AM3G-REG | the rate at LongMemEval-S's own mix of 470 answerable and 30 abstention questions, 0.94 x (b - c)/347 + 0.06 x (c2 - b2)/30 |
| N151 | 6.2, Table 7 | +0.112; 0.167; +0.096; +0.065; +0.129; 0.40; 0.25; 0.75 | descriptive; judge-qualified | AM3G | \| Qwen3-8B \| +0.112 \| 0.167 \| +0.096 [+0.065, +0.129] \| 0.40 [0.25, 0.75] \| |
| N152 | 6.2, Table 7 | +0.101; 0.267; +0.079; +0.048; +0.111; 0.27; 0.17; 0.47 | descriptive; judge-qualified | AM3G | \| OLMo-2 \| +0.101 \| 0.267 \| +0.079 [+0.048, +0.111] \| 0.27 [0.17, 0.47] \| |
| N153 | 6.2, Table 7 | +0.089; 0.033; +0.082; +0.055; +0.112; 0.73; 0.44; 1.00 | descriptive; judge-qualified | AM3G | \| Qwen3.5-9B \| +0.089 \| 0.033 \| +0.082 [+0.055, +0.112] \| 0.73 [0.44, 1.00] \| |
| N155 | 6.3 | 347; 1; 11.24; 90; 70; 231; 288; 8 | descriptive | KS | Over all 347 retrieved questions, the median is 1 read, the mean 11.24 and the 90th percentile 70. 231 questions stop at one read and 288 within 8. |
| N156 | 6.3 | 45; 70; 3,150; 3,901 | descriptive | KS | The mean is dominated by the 45 all-abstaining pools, which read all 70 (3,150 of 3,901 reads). |
| N157 | 6.3 | 11-14; 1 | descriptive | AM3G | On answerable questions the stop rule reads a median of 1 subset, with a mean of 11-14. |
| N158 | 6.3 | 70; 43-59; 90-97% | descriptive | AM3G | On unanswerable questions the median is 70 reads, a mean of 43-59 … 90-97% of their 4-subset replies abstain. |
| N160 | 6.3 | 4; 8 | design | AM1D | Calls are counted, not tokens. A 4-memory call is shorter than an 8-memory call. |
| N161 | 7 | 347; 30 | scope | AM3G | AM1's 347 held-out answerable LongMemEval-S questions … LongMemEval-S has 30 abstention questions |
| N162 | 7 | 1,500; 8; 4 | scope | AM1 | BM25 top-8 user-turn pools (memories of at most 1,500 characters) … keeping 4 of 8. |
| N163 | 7 | 3-27% | descriptive; judge-qualified | AM3G | 3-27% of unanswerable questions, judge-qualified. |
| N164 | 7 | 0-27% | derived | AM3G | \| Qwen3.5-9B \| 29 \| 28 \| 1 \| 0 \| 0.033 [0.001, 0.172] \| 0, 0 \| … \| OLMo-2 \| 25 \| 17 \| 8 \| 0 \| 0.267 [0.123, 0.459] \| 8, 0 \| |
| N165 | 7 | 17% | descriptive | AM1 | a content-free reorder alone changes 17% of answers |
| N166 | 8, Sources | 2608.29605; 2026-08-30; 16; 2609.09115; 2026-09-08; 2610.02070; 2026-10-01; 80,187 | citation record | AM1-REG | Hindsight Memory-PRM, [2608.29605](https://arxiv.org/abs/2608.29605), 2026-08-30 … permutation Shapley with 16 permutations (MeClear, [2609.09115](https://arxiv.org/abs/2609.09115), 2026-09-08) … (CMP, [2610.02070](https://arxiv.org/abs/2610.02070), 2026-10-01) … estimates exposure effects with SNIPW from 80,187 calls of a closed model |
| N167 | 8, Sources | 2504.13752; 2025-04-18; 2507.04480; 2025-07-06; 100; 10 | citation record | AM1-REG | AT2, [2504.13752](https://arxiv.org/abs/2504.13752), 2025-04-18 … Nematov et al. ([2507.04480](https://arxiv.org/abs/2507.04480), 2025-07-06) compare credit estimators against exact Shapley on 100 RAG queries x 10 documents with a log-prob utility |
| N168 | 8, Sources | 2609.36805; 2026-09-29; 2609.27276; 2026-09-23; 2502.13870; 2025-02-19 | citation record | SWEEP | \| UpliftMem \| [2609.36805](https://arxiv.org/abs/2609.36805), 2026-09-29 \| … \| DRSR \| [2609.27276](https://arxiv.org/abs/2609.27276), 2026-09-23 \| … \| SPEX \| [2502.13870](https://arxiv.org/abs/2502.13870), 2025-02-19 \| |
| N169 | 8, Sources | 2606.15621; 2026-06; 0.22.1; 0.31.0 | citation record | SWEEP | \| Re-feeding Is Not Replaying \| [2606.15621](https://arxiv.org/abs/2606.15621), 2026-06 \| … VLLM_BATCH_INVARIANT=1 gave zero disagreement (vLLM 0.22.1, A100). … The v0.31.0 tag was also read directly: - vllm/v1/attention/backends/gdn_attn.py contains no batch-invariance hook. |
| N170 | 8, Sources | 2608.17781; 2026-08-18; nine; 33% | citation record | SWEEP | [2608.17781](https://arxiv.org/abs/2608.17781), "Preference Is Not Intervention" (2026-08-18). Nine readers … Effect signs disagree in 33% of jointly affected cells. |
| N171 | 8 | 2026-10-14 | citation record | SWEEP | nothing occupies G2 or AM1 through 2026-10-14 under these queries. |
| N172 | 9, Table 9 | 0.20 | exploratory | DEC | What ran. Exploratory, 0.20 physical GPU-h. vLLM 0.31.0 ran the Qwen3-8B |
| N173 | 9, Table 9 | 1405; 1411; 1432; 1435; 1439; 1441; 1.4862; 2.0 | exploratory | PILOT | \| 1405 \| cotcodec-vllm cu129 overlay build … \| 1411 \| the pilot: … \| 1432 \| overlay build … \| 1435 \| the A/A diagnostic … \| 1439 \| overlay build … \| 1441 \| the eager check … \| \| total \| \| \| 1.4862 of the 2.0 cap \| \| |
| N174 | 9, Table 9 | 23; 1454; 1458; 1.5444; 3.1 | confirmatory | AM1 | ledger row 23 … Held-out artifact, image build 1454 … Registered GPU job 1458 … Compute: 1.5444 physical GPU-h (build 0.0172, job 1.5272) of the 3.1 cap. |
| N175 | 9, Table 9 | 24; 0 | derived (no GPU: 0 GPU-h) | KS | Ledger row 24; file SHA-256 37256cc8... … No GPU was used and no new model call was made. |
| N176 | 9, Table 9 | 1462; 1466; 0.2017; 2.0 | exploratory | AM3D | \| 1462 \| cotcodec-vllm cu129 overlay build … \| 1466 \| the AM3 job … \| \| total \| \| \| 0.2017 of the 2.0 cap \| |
| N177 | 9, Table 9 | 1467; 1471; 0.1898; 0.5 | development | AM3G-REG | Build (job 1467, 1 H100 … GPU job (job 1471, 1 H100 … Total 0.1898 GPU-h of the 0.5 allowed |
| N178 | 9, Table 9 | 25; 1475; 1480; 1482; 0.6722; 2.08 | confirmatory | AM3G | Ledger row 25 … image build 1475; … held-out GPU job 1480 (33:01); … abstention GPU job 1482 (06:13). … GPU use was 0.6722 physical GPU-h against the 2.08 cap. |
| N179 | 9, Table 9 | 0 | derived (no GPU: 0 GPU-h) | AM1B | It uses no GPU |
| N180 | 9, Table 9 | 0 | derived (no GPU: 0 GPU-h) | AM1D | It ran on the host CPU with no GPU |
| N181 | 9 | 4.9 | derived | derived | 0.20 + 1.4862 + 1.5444 + 0 + 0 + 0 + 0.2017 + 0.1898 + 0.6722 + 0 + 0.1297 + 0 + 0.1325 + 0.3461 = 4.9026; 0.20 is D107's rounded figure |
| N182 | 9 | 23-27 | derived (ledger lines 23 to 27) | LEDGER | "experiment_id": "am1-memory-credit-v1" … "experiment_id": "am1-keepset-search-v1" … "experiment_id": "am3-nonabstain-generality-v1" … "experiment_id": "am5-ablated-cost-v1" … "experiment_id": "am5-ablated-cost-v2" |
| N183 | 9 | 34 | this note's rerun | derived | uv run --locked --offline python scripts/memcredit_cost_curve.py ... at 1cf31346: 33.72s user; results.json, per-table.json.gz and tables.md byte-identical to program/evidence/2026-10-15/am1b-cost-curve/ (SHA-256 compared) |
| N184 | Summary, 8 | 694 | audit record | AUDIT | Keep-set regret in correct answers against the exact keep-4 optimum, from 694 exhaustive judged tables, on a real agent-memory benchmark. |
| N185 | Summary, 3 | 64.6%; 69; 251; 182; 0.135; 0.011; 0.005; 0.651; 0.130; 0.075 | post hoc (audit recomputation; rerun by this note's author, same figures) | AUDIT | \| All non-constant \| 251 \| 0.277 \| 0.044 \| 0.025 \| … \| Reader right with all 8 \| 182 \| 0.135 \| 0.011 \| 0.005 \| … \| Reader wrong with all 8 \| 69 \| 0.651 \| 0.130 \| 0.075 \| … 64.6% of LOO's total regret comes from the 69 full-pool-wrong tables. |
| N186 | Summary, 3 | 95.6%; 96.4%; 45.4% | post hoc (audit recomputation) | AUDIT | Exact Shapley's keep set is optimal in 95.6% of retrieved tables (96.1% over both arms, 539 tables). Exact Banzhaf's is optimal in 96.4%, and LOO's in 45.4%. |
| N187 | 3 | 25; 69; 19; 182 | post hoc (audit recomputation; rerun by this note's author, same counts) | AUDIT | 64.6% of LOO's total regret comes from the 69 full-pool-wrong tables. In 25 of them all LOO credits are tied. In 19 of the 182 full-correct tables all LOO credits are zero, which is the redundancy failure Ghorbani and Zou describe. |
| N188 | 3 | 0.124; 0.098; 0.153; half; +0.233 | post hoc (auditor's bootstrap) | AUDIT | On full-correct pools, LOO minus exact Shapley is 0.124. The auditor's post hoc bootstrap gives [0.098, 0.153], about half the registered +0.233. |
| N189 | 3, H1 | 17.1% | audit reading of a descriptive figure | AUDIT | A content-free reorder flips 17.1% of full-pool answers, so part of the order ≥ 2 share is position brittleness. |
| N190 | Summary, 4.2, 7 | 251; 70; 37.5%; 0.375; 0.400 | post hoc (audit recomputation) | AUDIT | on the retrieved arm's non-constant tables at B = 4 (post hoc, not registered): … \| All non-constant \| 251 \| 0.277 \| … there are only 70 candidates, and 37.5% of them are optimal on average … Optimal 4-subsets per table: mean 0.375, median 0.400. |
| N191 | Summary, 5.5 | 23; 15; 24; 18:2; 4e-4; 25:5; 3e-4; 10:3; 0.09; 4:0; 8:1; 1:0; 78% | post hoc (audit recomputation; rerun by this note's author, same counts) | AUDIT | \| Qwen3-8B \| 23:0 \| 18:2 \| 4e-4 \| 4:0 \| … \| OLMo-2-7B \| 15:0 \| 25:5 \| 3e-4 \| 8:1 \| … \| Qwen3.5-9B \| 24:0 \| 10:3 \| 0.09 \| 1:0 \| … The fallback, which is the prior-art baseline, recovers 43-78% of the rule's gain. |
| N192 | Summary, 5.5 | 43-77%; 39; 35; 31; 24/31; 77.4% | derived | derived | fallback net gain over the rule's net gain over BM25 top 4: 23/39 = 59.0%, 15/35 = 42.9%, 24/31 = 77.4%, so 43-77%. The rule's 39, 35 and 31 are N118, N131 and N132. AUDIT and D131 state 43-78%; 77.4% rounds to 77%, and 78% appears to come from 24/347 divided by the rounded +0.089 (0.0692/0.089 = 0.777). |
| N193 | Summary | 6; 31; 26; 22; 27; 347; 8 | confirmatory | DEC | K = 8 (cost when the evidence is removed / gain with the evidence, of 347): … \| Qwen3-8B \| 6 / 31 \| COST_BELOW_GAIN \| 0.84 \| … \| Qwen3.5-9B \| 6 / 26 \| COST_BELOW_GAIN \| 0.81 \| … \| OLMo-2 \| 22 / 27 \| NOT_SEPARATED \| 0.55 \| |
| N194 | 6.4, Table 8 | 6 / 31; -0.072; -0.093; -0.038; 1.2e-4; 0.84; 0.71; 0.95 | confirmatory | AM5R; AM5RT | \| Qwen3-8B \| 6 / 31 \| −0.072 [−0.093, −0.038] \| 1.2e-4 \| COST_BELOW_GAIN \| 6 / 31, same \| … \| qwen3-8b \| 6 \| 31 \| 6 \| 31 \| -0.072 [-0.093, -0.038] \| … \| Qwen3-8B \| 0.84 [0.71, 0.95] \| |
| N195 | 6.4, Table 8 | 22 / 27; -0.014; -0.055; +0.028; 0.568; 20 / 27; 0.55; 0.41; 0.69 | confirmatory | AM5R; AM5RT | \| OLMo-2-1124-7B-Instruct \| 22 / 27 \| −0.014 [−0.055, +0.028] \| 0.568 \| NOT_SEPARATED \| 20 / 27, same \| … \| olmo-2-1124-7b-instruct \| 22 \| 27 \| 22 \| 27 \| -0.014 [-0.055, +0.028] \| … \| OLMo-2 \| 0.55 [0.41, 0.69] \| |
| N196 | 6.4, Table 8 | 6 / 26; -0.058; -0.079; -0.025; 1.1e-3; 0.81; 0.67; 0.94 | confirmatory | AM5R; AM5RT | \| Qwen3.5-9B \| 6 / 26 \| −0.058 [−0.079, −0.025] \| 1.1e-3 \| COST_BELOW_GAIN \| 6 / 26, same \| … \| qwen3.5-9b \| 6 \| 26 \| 6 \| 26 \| -0.058 [-0.079, -0.025] \| … \| Qwen3.5-9B \| 0.81 [0.67, 0.94] \| |
| N197 | 6.4 | 347 | confirmatory (population) | AM5R-REG | on AM1's 347 held-out answerable questions with their evidence sessions removed |
| N198 | 6.4 | 1.7%; 8.9%; 7.5%; half | confirmatory | AM5R; AM5R-REG | Qwen3-8B: 1.7% lost against 8.9% gained; … Qwen3.5-9B: 1.7% against 7.5%. … it raises accuracy whenever at most half of such questions lack their evidence |
| N199 | Summary, 6.4 | 70; 16 / 31; 0.063 | descriptive (secondary) | AM5R | K = 70, the uncapped rule: … Qwen3.5-9B 16 / 31, NOT_SEPARATED: Holm p 0.063 |
| N200 | 6.4 | 27; 347; 8 | descriptive | AM5R | 27 of 347 ablated pools contain the answer string … At K = 8 no judged-correct switch is in a flagged pool. |
| N201 | 6.4 | 1 failed, 230 passed; 231 | deviation record | AM5R | The host test step reported "1 failed, 230 passed" (pytest exit 1). … all 231 tests pass, and analyze reproduces byte for byte. |
| N202 | 6.4 | 186; 195; 0.72; 8 | confirmatory (hand check) | AM5R | Hand against judge: 186 of 195 agree (kappa 0.72). All 8 switched replies the judge called correct were confirmed. |
| N203 | 6.4 | 63; 126; 0, 5 and 3; 1, 9 and 3; 70 | exploratory | DEC | For each of the 63 development questions, the evidence sessions were removed … None of LongMemEval's 126 has_answer turns survives. … at K = 8: 0, 5 and 3; … at K = 70: 1, 9 and 3; |
| N204 | 6.3 | 1, 2, 4, 8, 16, 26 and 70 | exploratory, post hoc (design) | AM4 | This README answers four questions, for K = 1, 2, 4, 8, 16, 26 and 70 and all three readers: |
| N205 | 6.3 | 77-84%; 31; 27; 26; 39; 35; 31 | exploratory, post hoc | AM4 | By K = 8 it has 77-84% (31, 27 and 26). … the headline counts: OLMo-2 35 against 0, Qwen3.5-9B 31 against 0 and Qwen3-8B 39 against 0; |
| N206 | 6.3 | 0; 2.7-3.1 | exploratory, post hoc | AM4 | c stays 0 at every K. … Answerable questions read a mean of 2.7-3.1 at K = 8 |
| N207 | 6.3 | 3, 3 and 0 | exploratory, post hoc; judge-qualified | AM4 | At K = 8 it is 3, 3 and 0. |
| N208 | 6.3 | 470:30; +0.067; +0.078; +0.022 | exploratory, post hoc; judge-qualified | AM4 | Net rate: at the 470:30 mix. … It rises steeply up to K = 8 (+0.067 to +0.078). After that it moves by at most +0.022 |
| N209 | 2.6 | 10,000 | design | AM4 | Bootstrap settings are the registration's: 10,000 resamples, seed 42. |
| N210 | 2.6 | 10,000 | design | AM5R-REG | (10,000 resamples, numpy default_rng(42), |
| N211 | 9 | 462 | exploratory check; rerun by this note's author at 1cf31346 ("compared": 462, "differences": []) | AM4 | It agrees on all 462 figures, on the host and on a Mac from the committed files alone. |
| N212 | 9, Table 9 | 0 | derived (no GPU: 0 GPU-h) | AM4 | AM4 is CPU only and recomputes the registered run's features. |
| N213 | 9, Table 9 | 1483; 1487; 0.1297; 0.5 | exploratory | AM5 | \| 1483 \| cotcodec-vllm cu129 overlay build … \| 1487 \| GPU job: … 0.1297 of the config's 0.5 cap |
| N214 | 9, Table 9 | 26; 0 | derived (void; no GPU: 0 GPU-h) | DEC | D123. am5-ablated-cost-v1 (ledger row 26) is void before running … No GPU job was submitted, and no held-out output exists or was read. |
| N215 | 9, Table 9 | 0.1325; 0.3; 1502; 1507 | development dry run | AM5DRY | 0.1325 physical GPU-h, against the 0.3 allowed. Build 1502 took 0.0197 and job 1507 took 0.1128. |
| N216 | 9, Table 9 | 27; 1548; 1552; 0.3461; 1.42 | confirmatory | AM5R | ledger row 27, fill commit 83ba8f8d, freeze commit 6578e0f0, which adds only the row. … build 1548; … GPU job 1552 (19:40). … GPU use was 0.3461 physical GPU-h of the 1.42 cap. |
| N217 | 7 | 1.7-6.3% | derived | derived | 6/347 = 1.7% (Qwen3-8B, Qwen3.5-9B) and 22/347 = 6.3% (OLMo-2), the judge-based costs at K = 8 of N194-N196 |
| N218 | 8 | 2^10; 2^6; 2025-07-06; 2025-12-05 | citation record | AUDIT | \| Nematov et al., Source Attribution in Retrieval-Augmented Generation \| 2025-07-06 (ECML-PKDD 2025) \| https://arxiv.org/abs/2507.04480 \| full (auditor); S \| Exact 2^10 Shapley reference … \| Patel, Zhou, Fanti, MaxShapley \| 2025-12-05 (v2 2026-05-19) \| https://arxiv.org/abs/2512.05958 \| part, Sections 1-4 (refuter); S \| Exact Shapley over 2^6 sources with an LLM-judge utility that sees the reference answer; LOO under-credits redundancy \| |
| N219 | 8, Sources | 2512.05958; 2405.03875; 2024-05-06; 2502.04554; 2025-02-06 | citation record | AUDIT | https://arxiv.org/abs/2512.05958 … \| Wang, Yang, Zou, Kwon, Jia, Rethinking Data Shapley for Data Selection Tasks \| 2024-05-06 (ICML 2024) \| https://arxiv.org/abs/2405.03875 \| … \| Chi et al., Unifying and Optimizing Data Values for Selection via Sequential Decision-Making \| 2025-02-06 (v2 2026-05-29) \| https://arxiv.org/abs/2502.04554 \| |
| N220 | 8 | +25.5 pp; +20.9; +29.8 | citation record | AUDIT | \| MeClear \| 2026-09-08 \| https://arxiv.org/abs/2609.09115 \| part (auditor); S \| LOO blind spot for redundant harm; permutation Shapley-16 beats LOO by +25.5 pp [+20.9, +29.8] on LoCoMo \| |
| N221 | 8, Sources | 2019-04; 1904.02868; 2022-05; 2205.15466; 2021-10; 2110.14049; 2024-09-01; 2409.00729; 2025-06; 2506.04202 | citation record | AUDIT | \| Ghorbani and Zou, Data Shapley \| 2019-04 (ICML 2019) \| https://arxiv.org/abs/1904.02868 \| … \| Wang and Jia, Data Banzhaf \| 2022-05 (AISTATS 2023) \| https://arxiv.org/abs/2205.15466 \| … \| Kwon and Zou, Beta Shapley \| 2021-10 (AISTATS 2022) \| https://arxiv.org/abs/2110.14049 \| … \| ContextCite \| 2024-09-01 (NeurIPS 2024) \| https://arxiv.org/abs/2409.00729 \| … \| TracLLM \| 2025-06 (USENIX Security 2025) \| https://arxiv.org/abs/2506.04202 \| |
| N222 | 7, Sources | 2026-07-01; 2607.00725 | citation record | AUDIT | \| What Survives Into Context \| 2026-07-01 \| https://arxiv.org/abs/2607.00725 \| |
| N223 | 8, Sources | 1997; 2023-10; 2310.03714; 2025-05 | citation record | AUDIT | \| Kohavi and John, Wrappers for Feature Subset Selection \| 1997 \| https://doi.org/10.1016/S0004-3702(97)00043-X \| … \| Schoch and Ji, Monte Carlo Sampling for Analyzing In-Context Examples \| 2025-05 (Insights workshop) \| https://aclanthology.org/2025.insights-1.7/ \| … \| Khattab et al., DSPy \| 2023-10 \| https://arxiv.org/abs/2310.03714 \| |
| N224 | Summary, 5, 8, Sources | 2025-12-29; 2512.23836; 2026-09-24; 2609.29828; 2024-07-23; 2407.16833; 2024-05; 2405.15556 | citation record | AUDIT | \| Wang, Ma, Kumar, Retrieval Augmented Question Answering: When Should LLMs Admit Ignorance? \| 2025-12-29 \| https://arxiv.org/abs/2512.23836 \| … \| ChunkRank \| 2026-09-24 \| https://arxiv.org/abs/2609.29828 \| … \| Self-Route (Li et al.) \| 2024-07-23 (EMNLP 2024 industry track) \| https://arxiv.org/abs/2407.16833 \| … \| RobustRAG \| 2024-05 (v2 2026-04-01; SaTML 2026) \| https://arxiv.org/abs/2405.15556 \| |
| N225 | 8, Sources | 2026-09-26; 2609.32269; 2025-07-22; 2507.16199; 2020-10-24; 2010.12786 | citation record | AUDIT | \| Before Answering (Mondal et al.) \| 2026-09-26 \| https://arxiv.org/abs/2609.32269 \| … \| LLM Abstention Can Be a Prompt Artifact \| 2025-07-22 \| https://arxiv.org/abs/2507.16199 \| … \| Khayrallah and Sedoc, the "I don't know" problem \| 2020-10-24 \| https://arxiv.org/abs/2010.12786 \| |
| N226 | 8 | 30; 12; 45; 6; 429; 2026-10-16 | audit coverage | AUDIT | \| A \| about 30 \| about 12 \| GitHub and Hugging Face API searches \| … \| B \| about 45 \| 6 \| GitHub and Hugging Face searches \| … OpenAlex returned HTTP 429 for every agent … No direct prior art found through 2026-10-16 under the coverage in the Appendix. |
| N227 | 8, Sources | 2026-10-07; 2610.09348; 2026-10-11; 2610.15642; 2025-05-23; 2505.17495 | citation record | AUDIT | \| Relevance Is Not Sufficiency \| 2026-10-07 \| https://arxiv.org/abs/2610.09348 \| abs (auditor) \| Set-level memory sufficiency on LongMemEval-S, 72.4% to 82.2% \| … \| MemPursuit, Recall What Is Missing \| 2026-10-11 \| https://arxiv.org/abs/2610.15642 \| … \| ProxySPEX (and SPEX, 2502.13870) \| 2025-05-23 (NeurIPS 2025) \| https://arxiv.org/abs/2505.17495 \| abs (auditor) \| Sparse interactions under context masking (relevant to claim 2) \| |
| N228 | 2.1, Table 1 | eight; six | design (exclusion) | AM1 | Step 0's eight demo questions, six of them held-out ids that development ran, are excluded from every estimand |
| N229 | 2.3 | two | confirmatory (gate G1) | AM1 | item replayed bit for bit across two GPUs, two processes and two orders (G1). |
| N230 | 2.6 | two; three | derived (count of each registration's review-round sections: two in AM1-REG, KS-REG and AM5R-REG, three in AM3G-REG) | AM1-REG; KS-REG; AM3G-REG; AM5R-REG | ### Round 2 … ### Round 3 |
| N231 | 4.2 | Six; seven; three | confirmatory (the three and three derived from Table 4's call columns) | KS | Six of seven comparisons are SEARCH_BETTER. |
| N232 | 5.4 | two | confirmatory (hand check) | AM3G | The two held-out disagreements are in distractor pairs and would be hidden gains |
| N233 | 6.1 | four | derived (two + one + one questions) | AM3G | The judge accepted plain answers as "identified as unanswerable" on two knowledge-update questions, one single-session-user and one multi-session. |

## Result of the check

- 226 rows. Every source fragment was found in its file at `1cf31346`, every number was
  found in its fragments (except in `derived` rows, which show their arithmetic), and every
  number was found in `note.md` (spelled-out numbers compared without case).
- Coverage: every numeric token in `note.md` outside code spans and code blocks is listed in
  some row, apart from the identifiers named above. Spelled-out counts that report a result or
  a check outcome and restate no listed digit are listed too (N228-N233, and the words in N112,
  N127, N170, N188 and N198). Spelled-out design and structural counts (three readers, five
  rules, seven comparisons, four patterns, two pool arms, four registrations) are not.
- The mechanical check shows that a number exists in its source; it does not show that the
  note uses it in the right context. That was checked by reading each sentence against its
  source.
- This revision (D131) removed rows N005, N010-N012 (the summary's interaction excess,
  natural-mix rates, break-even range and read medians; the figures stay in sections 3 and 6
  under other rows), N104 (the repeated licensed calls of H-A), N154 (the joint resampling of
  the 22 twins) and N159 (the verifier's capped-read figures, which AM4 replaces). It trimmed
  N103 (greedy's 17 of 251) and N105 (the size-simulation rates other than 0.05).
- One source disagreement is recorded in N192: AUDIT and D131 give the fallback's share of
  the rule's gain as 43-78%, but the audit's own counts give 43-77% (24/31 = 77.4%). The note
  states 43-77% and gives both figures.
- AM5R's RESULTS.md states the consequence of COST_BELOW_GAIN as "whenever at most about
  81-84% of questions lack their evidence". The registration's licence (AM5R-REG section 7.1)
  says "at most half" and makes the break-even share a registered description (section 3), so
  the note follows the registration (N198) and reports the break-even shares as descriptions.
- Reruns while revising, all on a Mac from committed files at `1cf31346`: AM1b's script
  (byte-identical outputs, N183); AM4's `crosscheck` (462 figures, no difference, N211); the
  audit's split of leave-one-out regret by full-pool correctness and its Self-Route-style
  fallback comparison (every count in N185, N187 and N191 reproduced, with ad hoc scripts that
  were not committed; the counts can be recomputed from the two committed files named in note
  section 9). No rerun is recorded for the figures in N186, N188 and N190.
