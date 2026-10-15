# am1-memory-credit-v1: results

**CONFIRMATORY. Frozen registration `am1-memory-credit-v1`:** ledger row 23, file SHA-256
`51d0abb1...`, `git_head_at_freeze` `c50017af`, freeze commit `9ad36b10`, the commit that adds the
row. Every artifact, image, job and analysis below comes from `9ad36b10`.

**Disclosures that apply to every number here:**

- **No gauntlet score (D111).** Blind discrimination and the two provider-distinct reviews did
  not run.
- **Agent hand labels, not Kevin's (D9, D111).** The G2 hand check was labelled blind by an
  isolated agent.
- **Not independently verified.** No fresh verifier has re-run the analysis. The numbers are the
  frozen code's outputs (`analysis/`). The analyst only recomputed the B = 4 regret means and
  the hand-check kappa from the committed files, and both matched.
- **Development data.** The development pilot used only the 63-question development split.
  Step 0's eight demo questions are excluded (registration section 4).

The registered analysis ran once, on 2026-10-15 UTC on the host CPU, from a `git archive` export
of `9ad36b10`. The commands were section 17's `analyze` (with `--hand-labels`,
`--hand-labels-sha256` and `--expected-evidence-sha256`) and `aa`, unchanged. The labels file's
SHA-256 was committed before the join: commit `9e641945` at 04:22:22Z, and `analyze` started at
04:24:06Z. The operations record is `README.md` in this directory.

## Outcome in one paragraph

Every gate passed and no kill criterion fired:

- G1 replay PASS: 190,156 of 190,156 reader requests and 10,230 of 10,230 judge items gave
  identical tokens and log-prob bits across GPUs and orders.
- G2 judge PASS: validation 322 of 322 and 347 of 347; hand-check kappa 0.867 against the
  0.80 bar.
- The void rule did not fire (0 incomplete tables). K2 did not fire (12.4% constant
  questions). K3 did not fire. K4 is not underpowered (251 non-constant retrieved tables).

So H2 is read and a program decision follows. On the deployable retrieved pool at a budget of 4
of 8, all five primary credit rules are **MISSPECIFIED**. The mean keep-set regret against the
exact optimum, with its 99% interval, is:

| Rule | Regret | 99% interval |
|---|---:|---|
| leave-one-out (the headline) | 0.277 | [0.223, 0.333] |
| permutation Shapley-16 | 0.138 | [0.096, 0.187] |
| SNIPW-64 | 0.094 | [0.058, 0.133] |
| retrieval rank | 0.343 | [0.271, 0.418] |
| raw attention | 0.311 | [0.235, 0.382] |

Leave-one-out loses **+0.233 [0.194, 0.273]** more than exact Shapley credit on the same tables
(`LOO_LOSES_MORE_THAN_EXACT_SHAPLEY`). Exact Shapley itself loses 0.044 [0.020, 0.072]. The
registered program reading therefore holds: "per-memory deletion credit is misspecified for
keep/evict decisions on this benchmark (this reader, this judge, BM25 user-turn pools, 4 of
8)". The loss is specific to deletion credit, and exact additive credit does not share it. The
second judge's tables give the same five verdicts.

Secondary readings:

- H1: interactions exceed the AND/OR baseline at the gold count by +0.156 [0.119, 0.194]
  (retrieved) and +0.094 [0.058, 0.129] (gold).
- AM2: non-gold deletion labels are ABOVE THE SWAP FLOOR over both arms, at +0.0099
  [0.0026, 0.0170]. The gold arm drives this (+0.020); on the retrieved arm alone the
  difference is +0.0002 [-0.009, +0.010].
- AM6: cross-fitted attention heads predict necessity at AUROC 0.890, 0.060 above the best
  cheap baseline (overlap with the reply, 0.830). So neither "internal signals add nothing" nor
  "none predicts necessity" holds.

## What was registered

These are the parts of the registration that bear on this report.

**Question and units (sections 1 and 4).** The confirmatory set is 347 held-out LongMemEval-S
(cleaned) questions: the 353 held-out ids minus Step 0's six demo ids among them. Its id digest
is `d4f024fb...`, and `headline.json` reproduces it. Each question has two pools of k = 8
user-turn memories:

- `retrieved` (primary): the BM25 top 8.
- `gold` (secondary): the gold turns plus seeded distractors.

Each pool has all 256 subsets, 8 x 2 matched content swaps and 2 reorders: 274 requests per
pool and 190,156 per pass.

**Reader and judge (section 5).**

- Reader: Qwen3-8B, eager batch-invariant vLLM, greedy, thinking off.
- Judge: Qwen3-32B with LongMemEval's official prompt. A cell's utility u(S) is the judge's
  label of its reply.
- Second judge: Qwen3-8B.
- AM6's signals come from HF eager attention.

**Estimands (section 6).**

- Regret is OPT_B minus u(top-B by credit), averaged over tie-breaks and over seeds 42-44 for
  the stochastic rules.
- E1: the order ≥ 2 Fourier share minus 1 - m/(2^m - 1).
- E2: the mean regret at B = 4, retrieved arm, for the primary family {leave-one-out,
  permutation Shapley-16, SNIPW-64, retrieval rank, raw attention}.
- E3: other budgets, the gold arm, the other rules, the paired difference against exact
  Shapley, and the second judge.
- E4: AM2's deletion and swap flip rates, their difference, survival and reorders.
- E5: AM6's necessity AUROC and Spearman correlation with exact Shapley.
- Intervals are percentile intervals from 4,000 question-cluster bootstrap resamples (AUROC:
  1,000).

**Decision rules (sections 7, 8 and 13).** H2 uses each primary rule's 99% interval
(Bonferroni over the five rules):

- MISSPECIFIED if the lower bound is above 0.05.
- ADEQUATE if the upper bound is below 0.02.
- INCONCLUSIVE otherwise.

The headline is leave-one-out. Its program reading needs G1 PASS, G2 PASS and no K2 or K3, and
it is read with the paired leave-one-out minus exact Shapley difference (95%).

The gates come before H2:

- The void rule: more than 2% of an arm's tables incomplete.
- G1: both reader passes and both primary-judge passes complete and token-identical. A reader
  time cap means INCOMPLETE with no rerun.
- G2: reference answers of non-preference questions judged yes at ≥ 95%, "I don't know." judged
  no at ≥ 95%, and a blind 120-item hand check with Cohen's kappa ≥ 0.80. The labels' SHA-256 is
  committed before the join, and the labels must cover exactly the seeded sample.
- K2: more than 60% of questions constant in both arms.
- K3: at least 90% of non-constant tables with order-1 share ≥ 0.9, and both leave-one-out and
  exact Shapley optimal at B = 4 in ≥ 95% of them.
- K4: fewer than 150 non-constant retrieved tables.

Secondary readings follow fixed rules:

- AM2: ABOVE THE SWAP FLOOR if the 95% lower bound of the non-gold deletion flip rate minus the
  swap flip rate at the same slots is above 0.
- AM6: INTERNAL SIGNALS ADD NOTHING if the best cheap baseline is within 0.03 AUROC of the best
  attention signal; NONE PREDICTS NECESSITY if every signal is below 0.65.

## What ran

| Step | When (UTC, 2026-10-15) | Outcome |
|---|---|---|
| Held-out artifact, image build 1454, CPU selftest 1455, host tests | 03:17-03:23 | `f23bca04...` (347 questions); image `sha256:abcd2b56...`; selftest pass; 80 tests pass (`README.md`) |
| Registered GPU job 1458 (2 H100, limit 90 min) | 03:23:39-04:09:28 | COMPLETED 0:0 in 00:45:49; every phase and worker complete; reader passes 1,281 s and 2,297 s, neither stopped by the 3,600 s cap; nothing rerun |
| Hand-check sample (registered `hand-sample`) | 04:12 | 120 items, `cebfe191...`, no judge label |
| Blind labels by an isolated agent | 04:20 | `70a5f2ec...`, 120 rows, read-only on the host |
| Labels' SHA-256 committed (`hand-check/hand-labels.sha256.txt`, `hand-labels-receipt.json`) | 04:22:22 | commit `9e641945` |
| Registered `analyze`, then `aa` (`ops/am1c-analyze.sh`), from the export of `9ad36b10` on the host CPU | 04:24:06-04:24:39 | exit 0 and exit 0; outputs read-only; text-free copies in `analysis/` |

Compute: 1.5444 physical GPU-h (build 0.0172, job 1.5272) of the 3.1 cap. The analysis used no
GPU.

## Gates, the void rule and kill criteria (`analysis/headline.json`, `verdicts` and `kill`)

| Gate | Registered rule | Value | Outcome |
|---|---|---|---|
| Void (section 13) | > 2% of an arm's tables incomplete | retrieved 0 of 347, gold 0 of 347 | does not fire |
| **G1 replay** | both reader passes and both primary-judge passes finish every request with identical tokens | reader 190,156 of 190,156 compared, 0 differ; judge 10,230 of 10,230, 0 differ; no reader pass time-capped | **PASS** |
| K2 constant tables | > 60% of questions constant in both arms | 43 of 347 (12.4%) | does not fire |
| K3 interactions do not matter | ≥ 90% of non-constant tables with order-1 share ≥ 0.9, **and** LOO and exact Shapley optimal at B = 4 in ≥ 95% | 29.7% of 539 tables; LOO optimal 51.8%; exact Shapley 96.1% | does not fire (the first two conditions fail) |
| K4 coverage | < 150 non-constant retrieved tables | 251 | not underpowered |
| **G2 judge** | reference yes ≥ 95% (non-preference), "I don't know." no ≥ 95%, hand-check kappa ≥ 0.80 on exactly the seeded sample | 322 of 322 (1.000); 347 of 347 (1.000); kappa **0.867**, 95% [0.767, 0.950], n = 120, `matches_seeded_sample` true, labels `70a5f2ec...` | **PASS** |

H2 is read (`h2_read` true, no blockers, no qualifiers), and a program decision follows
(`program_decision` true).

The kappa gate reads the point estimate (section 8). Its 95% interval reaches below 0.80 (lower
bound 0.767), which is reported here as section 8 requires. The A/A identity behind G1 is in
the A/A section below.

## H2 (primary, E2): keep-set regret at B = 4 on the retrieved arm (`analysis/h2.json`)

Each value is the mean regret over the 251 non-constant retrieved tables. Raw attention
succeeded on 694 of 694 pools, so it also uses all 251 tables. "Suboptimal" is the share of
tables with any regret. The last column is the paired difference against exact Shapley on the
same tables, with its 95% interval.

| Rule | Tables | Regret, 95% | 99% (decision) | Verdict | Suboptimal | Minus exact Shapley, 95% |
|---|---:|---|---|---|---:|---|
| leave-one-out (deletion), **the headline** | 251 | 0.277 [0.235, 0.319] | [0.223, 0.333] | **MISSPECIFIED** | 0.546 | +0.233 [+0.194, +0.273] |
| permutation Shapley, 16 | 251 | 0.138 [0.107, 0.173] | [0.096, 0.187] | **MISSPECIFIED** | 0.279 | +0.094 [+0.066, +0.126] |
| SNIPW, 64 exposures | 251 | 0.094 [0.066, 0.123] | [0.058, 0.133] | **MISSPECIFIED** | 0.171 | +0.050 [+0.023, +0.078] |
| retrieval rank | 251 | 0.343 [0.287, 0.402] | [0.271, 0.418] | **MISSPECIFIED** | 0.343 | +0.299 [+0.243, +0.359] |
| attention, raw | 251 | 0.311 [0.251, 0.371] | [0.235, 0.382] | **MISSPECIFIED** | 0.311 | +0.267 [+0.207, +0.323] |
| exact Shapley (reference, not in the family) | 251 | 0.044 [0.020, 0.072] | [0.012, 0.080] | | 0.044 | |
| exact Banzhaf (reference, not in the family) | 251 | 0.025 [0.009, 0.043] | [0.005, 0.050] | | 0.036 | -0.019 [-0.040, -0.002] |
| random keep set (reference, not in the family) | 251 | 0.625 [0.596, 0.653] | [0.587, 0.661] | | 0.976 | +0.581 [+0.547, +0.613] |

- **Leave-one-out (the headline): MISSPECIFIED.** Its 99% lower bound, 0.223, is far above
  0.05. Top-4 keep sets by deletion credit lose about 0.28 of a correct answer per non-constant
  question, against the best 4-subset. They are suboptimal in 55% of tables.
- **The other four rules are MISSPECIFIED too.** SNIPW-64 is the closest call: its 99% lower
  bound is 0.058, against the 0.05 threshold.
- **No rule is ADEQUATE.** As section 9 anticipated, ADEQUATE was nearly out of reach at this
  sample size.

## The program reading and the leave-one-out minus exact Shapley class

The registered reading applies because G1 and G2 pass and neither K2 nor K3 fires
(`verdicts.headline`):

> per-memory deletion credit is misspecified for keep/evict decisions on this benchmark (this
> reader, this judge, BM25 user-turn pools)

The scope stated in section 7 adds "4 of 8".

The paired difference is R_LOO minus exact Shapley's regret on the same tables: **+0.233, 95%
[+0.194, +0.273]**. Its lower bound is above 0, so the class is
**`LOO_LOSES_MORE_THAN_EXACT_SHAPLEY`**. Leave-one-out loses more than exact Shapley credit
does, and the loss is specific to deletion credit. It is not a loss that every per-memory
additive score suffers here.

Exact Shapley's own regret is 0.044, 95% [0.020, 0.072] and 99% [0.012, 0.080]. That interval
spans both thresholds, so this run neither shows exact Shapley above 0.05 nor below 0.02. Exact
Shapley is not in the decision family, and no verdict is attached to it.

The direction holds at every budget and on both arms (paired, 95%):

| Arm | B = 1 | B = 2 | B = 3 | B = 4 |
|---|---|---|---|---|
| retrieved | +0.149 [+0.112, +0.188] | +0.254 [+0.206, +0.300] | +0.256 [+0.215, +0.299] | +0.233 [+0.194, +0.273] |
| gold | +0.104 [+0.075, +0.136] | +0.159 [+0.122, +0.198] | +0.191 [+0.154, +0.230] | +0.207 [+0.169, +0.245] |

## E3 (secondary): the same rules at other budgets and on the gold arm (`verdicts.h2_secondary`)

Each cell gives the mean regret, its 99% interval, and the verdict under section 7's rules.
These are secondary readings with no program decision. "Binds" is the number of tables where a
random keep set loses anything.

| Arm | B | Binds | leave-one-out | permutation Shapley-16 | SNIPW-64 | retrieval rank | attention, raw |
|---|---:|---:|---|---|---|---|---|
| retrieved | 1 | 131 | 0.153 [0.105, 0.206] MISSP. | 0.011 [0.000, 0.030] INCONCL. | 0.019 [0.003, 0.042] INCONCL. | 0.223 [0.155, 0.295] MISSP. | 0.171 [0.116, 0.235] MISSP. |
| retrieved | 2 | 215 | 0.326 [0.263, 0.386] MISSP. | 0.129 [0.088, 0.173] MISSP. | 0.108 [0.066, 0.153] MISSP. | 0.331 [0.255, 0.410] MISSP. | 0.303 [0.231, 0.378] MISSP. |
| retrieved | 3 | 234 | 0.303 [0.244, 0.359] MISSP. | 0.122 [0.081, 0.165] MISSP. | 0.085 [0.051, 0.123] MISSP. | 0.343 [0.267, 0.418] MISSP. | 0.303 [0.231, 0.378] MISSP. |
| retrieved | **4 (primary)** | 245 | 0.277 [0.223, 0.333] MISSP. | 0.138 [0.096, 0.187] MISSP. | 0.094 [0.058, 0.133] MISSP. | 0.343 [0.271, 0.418] MISSP. | 0.311 [0.235, 0.382] MISSP. |
| gold | 1 | 144 | 0.108 [0.069, 0.150] MISSP. | 0.005 [0.000, 0.014] **ADEQUATE** | 0.012 [0.001, 0.030] INCONCL. | 0.132 [0.083, 0.184] MISSP. | 0.097 [0.056, 0.142] MISSP. |
| gold | 2 | 230 | 0.202 [0.149, 0.258] MISSP. | 0.074 [0.045, 0.106] INCONCL. | 0.076 [0.044, 0.113] INCONCL. | 0.170 [0.118, 0.229] MISSP. | 0.250 [0.188, 0.316] MISSP. |
| gold | 3 | 266 | 0.243 [0.187, 0.301] MISSP. | 0.129 [0.089, 0.174] MISSP. | 0.078 [0.048, 0.113] INCONCL. | 0.243 [0.181, 0.312] MISSP. | 0.240 [0.177, 0.306] MISSP. |
| gold | 4 | 279 | 0.239 [0.185, 0.293] MISSP. | 0.138 [0.098, 0.183] MISSP. | 0.082 [0.052, 0.117] MISSP. | 0.278 [0.208, 0.351] MISSP. | 0.271 [0.205, 0.344] MISSP. |

Every rule at B = 4 on both arms, with 95% intervals. The pilot's other rules are included.
"Calls" is the number of reader calls per pool.

| Rule | Calls | retrieved regret | retrieved suboptimal | gold regret | gold suboptimal |
|---|---|---|---:|---|---:|
| exact Shapley | 256 | 0.044 [0.020, 0.072] | 0.044 | 0.032 [0.014, 0.054] | 0.035 |
| exact Banzhaf | 256 | 0.025 [0.009, 0.043] | 0.036 | 0.021 [0.008, 0.038] | 0.028 |
| leave-one-out (deletion) | 9 | 0.277 [0.235, 0.319] | 0.546 | 0.239 [0.198, 0.279] | 0.427 |
| leave-one-in | 9 | 0.420 [0.372, 0.469] | 0.633 | 0.455 [0.410, 0.500] | 0.660 |
| permutation Shapley, 4 | <= 33 | 0.231 [0.191, 0.271] | 0.526 | 0.229 [0.192, 0.267] | 0.497 |
| permutation Shapley, 16 | <= 129 | 0.138 [0.107, 0.173] | 0.279 | 0.138 [0.107, 0.171] | 0.295 |
| SNIPW, 64 exposures | 64 | 0.094 [0.066, 0.123] | 0.171 | 0.082 [0.058, 0.108] | 0.156 |
| deletion, placebo-filtered | 27 | 0.396 [0.349, 0.441] | 0.673 | 0.384 [0.339, 0.429] | 0.576 |
| swap effect | 17 | 0.251 [0.210, 0.294] | 0.490 | 0.251 [0.209, 0.293] | 0.413 |
| retrieval rank | 0 | 0.343 [0.287, 0.402] | 0.343 | 0.278 [0.226, 0.330] | 0.278 |
| attention, raw | 1 + 1 forward | 0.311 [0.251, 0.371] | 0.311 | 0.271 [0.219, 0.323] | 0.271 |
| attention, cross-fitted heads | 1 + 1 forward | 0.255 [0.203, 0.311] | 0.255 | 0.229 [0.181, 0.281] | 0.229 |
| question overlap | 0 | 0.329 [0.280, 0.379] | 0.458 | 0.265 [0.223, 0.308] | 0.424 |
| overlap with the reply | 1 | 0.328 [0.277, 0.380] | 0.410 | 0.257 [0.213, 0.302] | 0.392 |
| length | 0 | 0.406 [0.347, 0.466] | 0.406 | 0.415 [0.358, 0.472] | 0.417 |
| random keep set | 0 | 0.625 [0.596, 0.653] | 0.976 | 0.671 [0.646, 0.695] | 0.969 |

- At B = 1 (`analysis/tables.md`), leave-one-in, exact Shapley and exact Banzhaf are near 0 on
  both arms. Leave-one-in is exactly the B = 1 optimum by construction. Leave-one-out stays at
  0.153 (retrieved) and 0.108 (gold).
- Section 2 rules out ranking the rules: pairwise comparisons are secondary. Exact Banzhaf's
  regret is below exact Shapley's on the retrieved arm at B = 4 (paired -0.019 [-0.040,
  -0.002]), and that is reported here only as a description.

**E2 on the second judge's tables (`analysis/h2-second-judge.json`; sensitivity, no
decision).** Qwen3-8B's labels give 260 non-constant retrieved tables. At B = 4 every primary
rule is again MISSPECIFIED:

| Rule | Regret | 99% interval |
|---|---:|---|
| leave-one-out | 0.259 | [0.206, 0.312] |
| permutation Shapley-16 | 0.137 | [0.093, 0.186] |
| SNIPW-64 | 0.089 | [0.056, 0.130] |
| retrieval rank | 0.323 | [0.246, 0.400] |
| raw attention | 0.319 | [0.246, 0.392] |

Exact Shapley loses 0.058 [0.031, 0.088]. Leave-one-out minus exact Shapley is +0.201 [+0.167,
+0.239].

## E1 / H1 (descriptive): interaction share (`analysis/h1.json`)

| Arm | Non-constant tables | Order ≥ 2 Fourier share | **E1**: minus the AND/OR baseline at the gold count | Share of tables above that baseline | Minus the baseline at the relevant count |
|---|---:|---|---|---|---|
| retrieved | 251 (246 with m ≥ 1) | 0.379 [0.342, 0.416] | **+0.156 [+0.119, +0.194]** | 0.577 [0.516, 0.638] | -0.311 [-0.348, -0.275] |
| gold | 288 | 0.362 [0.327, 0.398] | **+0.094 [+0.058, +0.129]** | 0.486 [0.427, 0.542] | -0.274 [-0.309, -0.239] |
| both | 539 (534) | 0.370 [0.338, 0.403] | +0.122 [+0.092, +0.155] | 0.528 [0.479, 0.578] | -0.291 [-0.319, -0.262] |

E1 > 0 on both arms. Interactions beyond the AND/OR form of the gold memories carry variance. No
decision follows from H1 (section 7).

By structure class, the order ≥ 2 share is:

| Structure | Order ≥ 2 share |
|---|---:|
| single | 0 |
| OR | 0.333 |
| AND | 0.37 |
| monotone-mixed | 0.28 |
| non-monotone | 0.52 |

The baseline at the relevant count, which counts non-gold memories that matter, is higher than
the observed share. The gold count understates how many memories a table depends on.

**Census (`headline.json` `census`).**

| Arm | Tables | Constant (all 0) | Non-constant | u(full pool) | Non-monotone | Single | AND | OR | Monotone, mixed | A non-gold memory matters |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| retrieved | 347 | 96 | 251 | 0.524 | 167 | 57 | 12 | 8 | 7 | 182 |
| gold | 347 | 59 | 288 | 0.579 | 175 | 77 | 35 | 0 | 1 | 176 |

- Every constant table is constant 0, and the empty pool is never answered right.
- The retrieved pool holds no gold turn for 43 questions, 1 for 117, 2 for 174, and 3-5 for 13.
- 43 of 347 questions are constant in both arms (K2 above).
- There are 251 non-constant retrieved tables, against section 9's planning figure of about
  209.

## E4 / AM2 (secondary): placebo arms (`analysis/placebo.json`)

The table pools both arms, as the registered reading does. A deletion or swap "flips" when
judged correctness differs from the full pool's. The swap rate counts both matched swaps of
every slot.

| Class | Deletion flip rate (slots) | Swap flip rate (swaps) | **Deletion minus swap**, 95% | Swap flips where deletion does not (descriptive) | Nonzero deletion labels that survive |
|---|---|---|---|---|---|
| gold | 0.440 [0.399, 0.483] (1,198) | 0.441 [0.400, 0.483] (2,396) | -0.0008 [-0.0097, +0.0082] | 0.028 [0.016, 0.043] | 0.641 [0.586, 0.697] (527 labels) |
| non-gold | 0.072 [0.059, 0.085] (4,354) | 0.062 [0.051, 0.074] (8,708) | **+0.0099 [+0.0026, +0.0170]** | 0.028 [0.022, 0.034] | 0.128 [0.086, 0.175] (313 labels) |

**AM2 floor verdict: ABOVE THE SWAP FLOOR** (`verdicts.am2.nongold`). The 95% lower bound of the
non-gold deletion-minus-swap difference, +0.0026, is above 0.

- **The gold arm drives this.** Per arm (descriptive), the non-gold difference is +0.0002
  [-0.0094, +0.0103] on the retrieved arm and +0.0204 [+0.0090, +0.0324] on the gold arm.
- **ABOVE does not show content effects.** As section 7 states, deletion is a larger edit than
  a matched swap: it also shortens the prompt and moves the later memories.
- **Most non-gold deletion labels do not survive the placebo control.** 12.8% of nonzero
  non-gold labels survive (both swaps reproduce the label, and no reorder flips the pool),
  against 64.1% of gold labels. Neither survival share is judged.
- **The dossier's AM2 kill criterion 2 does not hold.** It needs non-gold deletion and swap
  flip rates both below 1%; they are 7.2% and 6.2%.
- **Reorders change many answers.** A content-free reorder of the full pool changes u(full) in
  17.1% [14.6%, 19.8%] of reorders: 14.6% on the retrieved arm and 19.7% on the gold arm.

## E5 / AM6 (secondary): internal signals (`analysis/internal.json`, `analysis/xfit.json`)

Necessity means leave-one-out > 0. It is scored over the 3,064 memories of the 383 pools that
the reader answers right with the full pool (230 questions; AUROC interval from 1,000
resamples). The last column is the mean per-table Spearman correlation with exact Shapley.

| Signal | Necessity AUROC, both arms | retrieved | gold | Spearman with exact Shapley |
|---|---|---:|---:|---|
| attention, cross-fitted heads | **0.890 [0.865, 0.914]** | 0.868 | 0.907 | 0.481 [0.453, 0.509] |
| attention, raw | 0.832 [0.803, 0.861] | 0.808 | 0.853 | 0.405 [0.376, 0.435] |
| overlap with the reader's reply (best cheap baseline) | 0.830 [0.800, 0.858] | 0.799 | 0.869 | 0.524 [0.485, 0.563] |
| retrieval rank | 0.777 [0.743, 0.811] | 0.749 | 0.844 | 0.394 [0.363, 0.425] |
| question overlap | 0.774 [0.740, 0.805] | 0.731 | 0.843 | 0.512 [0.476, 0.546] |
| length | 0.688 [0.663, 0.716] | 0.681 | 0.696 | 0.238 [0.206, 0.271] |

**AM6 readings (`verdicts.am6`):**

- **INTERNAL SIGNALS ADD NOTHING: does not hold.** The best attention signal (0.890) is 0.060
  above the best cheap baseline (0.830), beyond the 0.03 margin.
- **NONE PREDICTS NECESSITY: does not hold.** Every signal is above 0.65.

The margin comes from the cross-fitted heads alone. Raw attention (0.832) ties the reply-overlap
baseline. The cross-fitted heads are chosen on the other fold of questions using exact Shapley
tables: 16 heads per fold, in layers 17-28, trained on 261 and 278 tables. 6 of the 16 heads are
common to both folds. So they need exact tables from other questions to select.

By Spearman correlation with exact Shapley, overlap with the reply and question overlap rank
above both attention signals.

## Judge validation and agreement (`analysis/judge.json`)

The judge items are the 9,190 distinct (question, reply) pairs of the GPU-0 reader pass plus
1,040 validation items.

| Check | Qwen3-32B (primary) | Qwen3-8B (second) |
|---|---|---|
| reference answer as the response, non-preference questions (G2) | 322 of 322 yes | 322 of 322 |
| preference rubric as the response (not a valid positive; excluded from G2) | 0 of 25 yes | 4 of 25 |
| "I don't know." (G2) | 347 of 347 no | 298 of 347 no (temporal-reasoning 63 of 106) |
| another question's reference answer (seeded derangement) | 343 of 346 no | 341 of 346 |
| **hand check, 120 judged replies (G2)** | 112 agree (93.3%, [87.3, 97.1]); kappa **0.867** [0.767, 0.950]; 5 false yes, 3 false no | 113 (94.2%, [88.4, 97.6]); kappa 0.884 [0.797, 0.966]; 6 false yes, 1 false no |
| reader items, agreement with the primary | | 8,560 of 9,190 (kappa 0.846) |
| table cells, agreement with the primary | | 171,089 of 190,156 (90.0%) |

**Containment, Step 0's utility.** It agrees with the hand labels on 87 of 120 (kappa 0.44),
with the primary on 7,467 of 9,190 reader items (kappa 0.51), and on 177,776 of 190,156 cells.
The primary judged 2,838 of the 9,190 reader items yes.

**Hand check, post-join description (not registered; no label corrected; G2 unchanged).** The
sample is 60 items the primary judged yes and 60 judged no; the agent labelled 58 yes.

- **Preference items hold almost all the disagreement.** 7 of the 8 disagreements are on
  single-session-preference items, where the primary agrees on 19 of 26. On the 94 other items
  it agrees on 93.
- **Where the agent said no and the judge yes.** Items 359, 370, 394 and 1300 are preference
  replies the agent called generic. Item 8942 is a temporal-reasoning reply that named two
  bikes for a one-bike reference.
- **Where the agent said yes and the judge no.** Items 2505, 3936 and 4516 are preference
  replies.
- **Most disagreements are on items the agent had flagged.** All except item 3936 are among
  the borderline calls the agent flagged before the join.
- **The second judge said yes on all eight.**
- **Joined file.** The text-free joined labels are `analysis/hand-check-joined-text-free.jsonl`:
  ids, types, reply SHA-256, the hand label and both judges' labels.
- **Regrets without preference tables (not registered).** The 13 preference tables of the 251
  non-constant retrieved tables can be left out of the committed `tables.json.gz`. The B = 4
  point estimates then move by at most 0.011: leave-one-out 0.273, permutation Shapley-16
  0.137, SNIPW-64 0.092, retrieval rank 0.332, raw attention 0.307, exact Shapley 0.042. No
  verdict is drawn from this.

## A/A identities (`analysis/aa.json`, `analysis/identity.json`)

| Pair (job 1458) | Compared | Identical tokens | Identical tokens and log-prob bits | Judged-utility flips |
|---|---:|---:|---:|---|
| reader: GPU 0 canonical vs GPU 1 shuffled (`a485003c` vs `0524ae85`, separate processes) | 190,156 | 190,156 (95% CP lower bound 0.99998) | 190,156 | 0 of 190,156 (95% upper bound 1.9e-5); 0 of 694 pools |
| Qwen3-32B judge: GPU 0 canonical vs GPU 1 shuffled | 10,230 | 10,230 (lower bound 0.99964) | 10,230 | |

No judged reply received two labels: 0 of 9,190 conflicting. Eager batch-invariant replay was
bit-exact for every reader request and judge item of the run.

In `aa.json`, the judge pair's `pools` (38), `pools_with_a_utility_flip` and `utility_covered`
(0) do not mean anything. `aa_pair` maps judge item indices onto the reader's request table,
and judge outputs are not reader replies. The judge's identity is the token and log-prob-bit
comparison.

## Against the priors of section 18 (for the record; not tested)

| Prior (pilot) | This run |
|---|---|
| leave-one-out MISSPECIFIED, R about 0.2 | MISSPECIFIED, 0.277 |
| leave-one-out minus exact Shapley +0.135 [0.051, 0.227] | +0.233 [0.194, 0.273] |
| raw attention and retrieval rank MISSPECIFIED | both MISSPECIFIED |
| permutation Shapley-16 likely MISSPECIFIED | MISSPECIFIED |
| SNIPW-64 INCONCLUSIVE | **MISSPECIFIED** (99% lower bound 0.058) |
| H1 excess near +0.1 | +0.156 (retrieved), +0.094 (gold) |
| AM2 non-gold NOT ABOVE THE SWAP FLOOR, difference 0.0006 [-0.013, 0.013] | **ABOVE**, +0.0099 [0.0026, 0.0170]; the gold arm drives it (pilot gold arm +0.020 [-0.004, 0.048]; here +0.020 [0.009, 0.032]) |
| non-gold survival 0.17; gold survival about 0.7 | 0.128; 0.641 |
| a reorder flips about one answer in eight | 17.1%, about one in six |
| AM6 cross-fitted heads ahead of the best cheap baseline by about 0.05; raw attention behind it | ahead by 0.060; raw attention ties it (0.832 vs 0.830) |
| the second judge gives the same H2 verdicts | the same five verdicts |

Compared with the pilot (exploratory, 63 development questions):

| Regret, retrieved, B = 4 | Pilot | This run |
|---|---:|---:|
| exact Shapley | 0.079 | 0.044 |
| exact Banzhaf | 0.031 | 0.025 |
| random keep set | 0.576 | 0.625 |

## Deviations and disclosures

**None of the registration's commands, seeds, config, caps or contingency rules was changed.**
The analysis ran exactly as section 17 states: `analyze` with `--hand-labels`,
`--hand-labels-sha256 70a5f2ec...` and `--expected-evidence-sha256 f23bca04...`, then `aa`. The
details below are ones the registration leaves open, or apply to the whole run.

1. **D111.** The run carries no gauntlet score. Blind discrimination and the two
   provider-distinct reviews did not run.
2. **Agent hand labels (D9, D111).** An isolated agent labelled the 120 items blind, from the
   question, reference answer and reply. It read no judge label, analysis output or result.
   Kevin did not label. The agent's rules were:
   - Preference items follow LongMemEval's rubric guidance. A generic reply was marked no even
     when it named a type the rubric lists.
   - A hedged count was marked yes only when the stated number equals the reference.
   - Its borderline calls were listed before the join.
3. **The labels file stays on the host.** Its path is
   `~/cotcodec-runs/stage0/am1-confirmatory/hand-labels.jsonl`, the agent's fallback location
   beside HOST_DIR (section 12 names HOST_DIR for the sample and the joined rows). It is
   read-only, 120 rows, SHA-256 `70a5f2ec...`. Its rows carry the agent's free-text notes, which
   may quote LongMemEval, so it is not committed. Only its digest was committed, before the
   join (commit `9e641945`, 04:22:22Z; `analyze` at 04:24:06Z). After the join a text-free
   projection was committed (`analysis/hand-check-joined-text-free.jsonl`).
4. **Labels schema.** The registration fixes none. The rows are `{item_id, item_index, label,
   note}` with an integer label (1 yes, 0 no), which is what `analyze` reads (`item_index`,
   `int(label)`). `matches_seeded_sample` is true: 120 of 120 sample items, none extra, none
   twice.
5. **Source for the analysis.** The analysis did not run in the operator's clone. A fresh
   `git archive --format=tar 9ad36b10` of the host clone (SHA-256 `8806cd7b...`, equal to the
   operator's on the Mac and host) was extracted with GNU tar into
   `HOST_DIR/analysis/export-9ad36b10`, and all 19 pins of section 17 were checked there. Its
   venv was made with `uv sync --locked --offline` before the registered commands, which then
   ran with `uv run --locked --offline`; it is the same CPython 3.14.6 as the clone's venv
   (`analysis/logs/uv-sync-export.txt`). Commands ran on the login node's CPU, outside Slurm,
   for 33 s, like the hand sample. No GPU was used.
6. **Output locations.** ANALYSIS_DIR is `HOST_DIR/analysis/1458`. `--private-dir` is not in
   section 17's command and was not passed, so no joined rows with texts were written. The
   committed copies in `analysis/` are text-free: `tables.json` is committed gzipped (`gzip -n`),
   and the raw outputs' SHA-256 are in `analysis/logs/outputs.sha256`.
7. **Post-join descriptions (not registered).** The disagreement breakdown of the hand check
   and the B = 4 point estimates without preference tables are descriptions. Neither changes a
   gate or a verdict, and no label was corrected.
8. **Not independently verified.** No fresh verifier re-ran or re-implemented the analysis. The
   registration does not require one.
9. **The development pilot used only development data.** It ran on the 63-question development
   split (D111). Step 0's eight demo questions, six of them held-out ids that development ran,
   are excluded from every estimand (section 4). 19 confirmatory ids appear in two legacy
   files as ids only, with no model output, and stay in (status paragraph of the registration).
10. **Operator details (`README.md`).**
    - The host got the source by a git bundle clone.
    - A determinism rebuild of the artifact was made and deleted.
    - The CPU selftest was passed `--config` and dropped the in-image pytest step.
    - The first host test run lacked the `dev` extra.
    - CPU steps ran outside Slurm.
    - The steps ran on 2026-10-15 UTC, and the directory carries the assigned date 2026-10-16.
11. **Shared node (D110).** Another project's `transcreate-*` jobs held GPUs 0-1 throughout and
    were not touched. Job 1458 ran on GPUs 2-3.

## What the result licenses

The scope is:

- the Qwen3-8B reader (thinking off, Step 0's prompt, greedy, 64 tokens, eager batch-invariant
  vLLM 0.31.0);
- the Qwen3-32B judge with LongMemEval's official prompt;
- BM25 top-8 user-turn pools (memories of at most 1,500 characters) on the 347 held-out
  LongMemEval-S (cleaned) questions;
- keeping 4 of 8.

Within that scope, the result licenses four claims:

1. **The registered program reading, as a confirmatory claim.** Per-memory deletion
   (leave-one-out) credit is misspecified for keep/evict decisions on this benchmark. Its top-4
   keep sets lose 0.277 (99% [0.223, 0.333]) of a correct answer per non-constant table against
   the exact optimal 4-subset. They lose 0.233 [0.194, 0.273] more than exact Shapley credit
   does, so the loss is specific to deletion credit.
2. **The other four primary rules are MISSPECIFIED at this budget, each by its own registered
   rule.** These are permutation Shapley with 16 permutations, SNIPW with 64 exposures,
   retrieval rank and raw attention mass. For the two sampled estimators, the loss beyond exact
   Shapley is +0.094 and +0.050 (paired, 95% intervals above 0).
3. **The tables replay exactly.** On this stack, every reader request and judge item of the run
   replayed bit for bit across two GPUs, two processes and two orders (G1).
4. **The secondary readings stand as stated, with their caveats.**
   - H1's positive excess.
   - AM2 ABOVE THE SWAP FLOOR over both arms, driven by the gold arm, and not evidence of
     content effects.
   - AM6's cross-fitted heads exceeding the best cheap baseline by 0.060 AUROC.

## What it does not license

- **Anything outside the scope above.** That includes other readers, judges, retrievers, memory
  units, pool sizes or budgets (section 2), and any human-labelled judge accuracy: the hand
  check is an agent's.
- **Which credit rule is best.** Pairwise comparisons, such as exact Banzhaf against exact
  Shapley, are secondary.
- **Anything about exact Shapley's own adequacy.** Its 99% interval [0.012, 0.080] spans both
  thresholds, and it is not in the decision family.
- **Why the tables are non-monotone.** Reader errors, distraction and order effects are not
  separated, and a content-free reorder alone changes 17% of answers.
- **Anything about training a memory learner on these credits.**
- **A content effect of non-gold memories from AM2.** Deletion is a larger edit than a matched
  swap, and only 12.8% of non-gold deletion labels survive the placebo control.
- **A deployable internal signal from AM6.** The cross-fitted heads are selected with exact
  tables of other questions, and raw attention does no better than the reply-overlap baseline.

## Files

- `analysis/`: the registered `analyze` and `aa` outputs, text-free.
  - `headline.json`: `verdicts`, census, kill criteria, identity.
  - `h1.json`, `h2.json`, `h2-second-judge.json`, `placebo.json`, `internal.json`, `xfit.json`.
  - `judge.json`, `identity.json`, `aa.json`, `tables.md`.
  - `tables.json.gz`: every table's set-function summary, structure, credits and regrets;
    values as hex.
  - `hand-check-joined-text-free.jsonl`.
  - `logs/`: stdout, stderr and exits, the outputs' SHA-256, the run log, the export's venv
    sync log.
- `hand-check/`: the sample's SHA-256, `hand-labels.sha256.txt` and `hand-labels-receipt.json`,
  committed before the join.
- `ops/am1c-analyze.sh`: the script that checked the export, pins and digests and ran
  `analyze` and `aa` once.
- `README.md`: the operations record (artifact, image, selftest, job 1458, hand sample).

Raw outputs stay on the host under `~/cotcodec-runs/stage0/am1-memory-credit-v1/`. These are
the passes, judge items with replies, the study artifact, the hand-check sample and the analysis
directory. The labels file is under `~/cotcodec-runs/stage0/am1-confirmatory/` (registration
section 12).
