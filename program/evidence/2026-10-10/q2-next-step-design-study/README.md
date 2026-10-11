# Q2's next step after S1a: successor designs, the attack, and options (D66)

CPU only. No host job of any kind ran for this study. Every number is for S1a's realized
sessions and tasks, on this host, under greedy decoding with 15 steps, and carries S1a's label:
**not externally anchored**. Seeds are 42, 43 and 44 throughout; nothing used unseeded
randomness. Branch `stage0/q2-design-study`, not pushed.

## The answer

**No successor within 8 GPU-h can admit S1b.**

- The calibrations S1a's 113 tasks do not reject put the share DR5 reads at 0.067-0.098
  (0.056-0.092 on the 32 base tasks), below M = 0.13.
- At S1a's estimates, P(DR5 GO) is at most 0.03 for every design examined. GO is the only
  outcome that starts S1b under D47.

**What a successor can still buy:** a decisive DR2 reading and a formal DR5 NO-GO.

**The best successor is E:** all 113 pool tasks, 4B and 9B, four new serving sessions per
size, one rerun. It uses 406 of 478 cap-minutes (6.77 GPU-h; 1,808 episodes; 37 h of calendar
time at minimum). At S1a's estimates, across the four calibrations that pass the extended
check:

| E at S1a's estimates | Probability |
|---|---|
| DR2 decisive | 0.83-0.87 |
| Present (task-specific harness effects, mostly at 9B, through the X test) | 0.52-0.73 |
| Near-equivalent | 0.12-0.34 |
| DR5 NO-GO | 0.23-0.54 |
| Both rules inconclusive (S1a's outcome) | 0.08-0.13 |

E beats S1a's own secondary design, C (the same 113 tasks at S = 2, R = 2), by 0.08-0.17 on
DR2.

**These numbers come after repairing the attack's blocking finding.** The base-fitted
calibrations that three of the four evaluators used gave 4B a task-specific harness effect
that 4B's data do not show. They fail an extended posterior-predictive check. Removing that
effect makes NO-GO two to four times as likely, but leaves GO out of reach.

**Recommendation.**

- **Option 1 (recommended):** close Q2's harness-scale question (S1b) now, and spend no
  successor GPU on it.
- **Option 2:** register E only if the program wants a decisive harness reading at 4B and 9B
  for its own sake.

**For S2 and S3**, S1a's noise floor says three things:

- S2's 5 pp gate needs about 100 structurally distinct tasks per contrast, unless the locale
  effect is nearly the same on every task. Reruns do not help.
- S3's checkpoint evaluations must interleave base and trained models in one serving session.
- S3 is gauntlet-bound whatever the floor says.

**Contents.**

- Section 3: the attack's points and how each was handled.
- Section 4: every design's decisiveness.
- Section 5: cost.
- Section 6: the options with their numbers.
- Section 7: S2 and S3.


## 1. What D66 asked, and the inputs

D66 asked for a CPU-only design study built on S1a's records: its variance components and its
realized cost. For each successor design within 8 GPU-h the study gives the probability of a
decisive DR2 (Present or Near-equivalent) and a decisive DR5 (GO or NO-GO), under scenarios
anchored to S1a's estimates. It also sizes S2's power gate with S1a's noise floor.

Inputs, all read only:

- `../q2-stage1-analysis/a1.jsonl`: 1,808 episode records.
  - The primary set is the 32 base tasks with raw verdicts.
  - The registered secondary set is all 113 eligible pool tasks.
- `../q2-stage1-analysis/costs.json` and the four lane receipts.
- `../q2-stage1-analysis/report/report-guarded.json`: the registered readings.
- The frozen registration `q2-stage1-rescoped-v1` (sections 5, 6 and 9-12).
- Decisions D47, D49, D56, D59 and D66.
- The S2 and S3 entries in the dossier and the backlog.

The work happened in three passes:

1. **Design study** (`../q2-design-study/`, commits `34a57a8`-`79096f8`): the simulator, the
   fits, a validation at S1a's own design, and the cost model.
2. **Four independent evaluators**, each covering one family: more sessions, more tasks, a
   K x S x R x sizes grid, and the frontier together with S2 and S3.
3. **An attack** on the study and the four evaluations.

This README is the single owner's synthesis. It repairs the attack's blocking problems,
re-runs everything they affect, and states the options. The evaluators' and the attack's
drivers stay in the session scratchpad and are not committed. Their numbers are quoted here
only where they are not superseded.

## 2. The model and the original calibration (summary of `../q2-design-study/README.md`)

The generative model is the registration's own operating-characteristics model (section
10.2), fitted by maximum marginal likelihood:

    logit p = eta0_tz + (h - 1/2) beta_tz + session + task x session (sigma_e)
              + task x harness x session (sigma_f),  Bernoulli reruns

- The task effects (eta0_4B, eta0_9B) are bivariate normal with correlation rho_a.
- The harness contrasts (beta_4B, beta_9B) are bivariate normal with means c_z, SDs sigma_b,z
  and correlation rho_b.
- S1a's two realized sessions per size enter as fixed effects (omega, kappa).
- New sessions draw from sigma_g and sigma_k.
- Task sources:
  - **pool**: S1a's 113 tasks, with posterior draws of their effects given S1a's records.
  - **parametric**: new tasks drawn from the fitted population.

The study's fits:

| Fit | Tasks | logL | rho_b | sigma_b 4B / 9B | sigma_f 4B / 9B | pi° 4B / 9B / small |
|---|---|---:|---:|---|---|---|
| `fit-base` (normal) | 32 base | -146.18 | 0.995 (bound) | 1.46 / 2.31 | 0 / 0 | 0.062 / 0.156 / 0.109 |
| `fit-base-spikeslab` (post hoc) | 32 base | -144.46 | 0.995 (bound) | slab 4.45 / 8.0, w 0.16 | 0 / 0 | 0.053 / 0.162 / 0.107 |
| `fit-pool` (normal) | 113 | -483.25 | 0.995 (bound) | 0.83 / 2.36 | 0.48 / 0 | 0.029 / 0.167 / 0.098 |

pi° is the population harness share over the 113 pool tasks (posterior draws).

The study validated at S1a's own design only (K = 32, S = 2, R = 2), on interval widths and
outcome probabilities:

- The normal parametric source failed: pi_small's widths came out 28-29% narrow.
- The pool-posterior and spike-and-slab sources passed.
- The four evaluators therefore used, as their primary sources:
  - eval-0: the spike-and-slab pool bank;
  - eval-1: the `fit-pool` bank;
  - eval-2: the spike-and-slab pool bank;
  - eval-3: the base-normal pool bank, with the spike-and-slab parametric source.


## 3. The attack, and how each point was handled

The attack found three blocking problems and six minor or informational ones. Each one is
handled below. Every repair run uses the committed code: `harness/q2_design/fast.py`,
`successor.py`, and the `study fit` options `--fix`, `--free` and `--no-se`. Each was run from
a clean detached checkout of the commit that added it, and the outputs are in this directory.

### 3.1 Blocking: 4B's task-specific harness effect is coupled to 9B's (confirmed; repaired)

**What the attack showed.** Every committed fit puts rho_b, the cross-size correlation of the
per-task harness contrast, at its 0.995 bound. That copies 9B's task-specific effects into 4B.
S1a's 4B data do not show them:

- On the 81 extension tasks, which the base fits never saw, X_4B = −0.015.
- On all 113 tasks, X_4B = −0.009 and pi_4B = 0.000.
- The 4B-only X sign-flip p is 0.82, against 0.04 for 9B alone.

**Confirmed here, with the extended check of section 3.2:**

- **The base-fitted sources fail.** These are the base-normal bank (eval-3's primary, eval-0's
  pool-n) and the base spike-and-slab bank (eval-0's and eval-2's primary).
  - On S1a's own 113-task run, observed X_4B sits at mid-rank 0.02 under both.
  - Out of sample on the 81 extension tasks, these fits miss on 4B:
    - X_4B at 0.01-0.02;
    - the 4B-only X p at 0.99;
    - 4B's count of non-constant tasks at 0.01-0.02;
    - D_w,4B at 0.02-0.04.
- **These sources put pi°_4B at 0.053-0.062. The 113-task fit puts it at 0.029.**

**Repair.** All 113 tasks were refitted with the coupling removed. These are conditional ML
fits, warm-started at `fit-pool` and holding the parameters not named:

| Fit | Held | Free | logL | sigma_b 4B / 9B | sigma_f 4B / 9B | pi° 4B / 9B / small | LR against `fit-pool` |
|---|---|---|---:|---|---|---|---:|
| `fit-pool` (committed) | none | all 18 | −483.25 | 0.83 / 2.36 (rho_b 0.995) | 0.48 / 0 | 0.029 / 0.167 / 0.098 | 0 |
| `fit-pool-rhob0.json` | rho_b = 0 | c, sigma_b (both sizes) | −485.04 | 0.68 / 2.30 | 0.48 / 0 | 0.022 / 0.164 / 0.093 | 3.59 |
| `fit-pool-rhob0-sf.json` | rho_b = 0 | c, sigma_b, sigma_f | −485.04 | 0.65 / 2.30 | 0.54 / 0 | (not used) | 3.58 |
| `fit-pool-4b0.json` | rho_b = 0, sigma_b,4B = 0.02 (floor) | c, sigma_b,9B | −485.19 | 0.02 / 2.29 | 0.48 / 0 | 0.004 / 0.164 / 0.084 | 3.90 |
| `fit-pool-4b0-sf.json` | as above | c, sigma_b,9B, sigma_f | −485.13 | 0.02 / 2.30 | 0.66 / 0 | (not used) | 3.76 |

How to read the table:

- **The likelihood mildly prefers coupling:** LR 3.6 for rho_b, p about 0.06 on one degree of
  freedom. A few tasks favour the same harness strongly in both sizes. For example, on
  `e2dd0213` H-OSW-fixed succeeds and H-GA fails in both sizes.
- **Once the sizes are decoupled, 4B's own data carry no evidence of task-specific harness
  variance:** LR 0.31 for sigma_b,4B = 0 against 0.68.
- **The decision-relevant change is from base-fitted to pool-fitted calibrations,** not from
  coupled to decoupled at the pool. pi°_small falls from 0.107-0.109 to 0.084-0.098, and to
  0.067 with the added session noise of P4sf.

The repaired family is every calibration that passes the extended check:

| Calibration | Definition | pi° 4B / 9B / small |
|---|---|---|
| **P0** | `fit-pool` as committed (coupled; eval-1's primary) | 0.029 / 0.167 / 0.098 |
| **PR** | decoupled | 0.022 / 0.164 / 0.093 |
| **P4** | 4B with no task-specific effect | 0.004 / 0.164 / 0.084 |
| **P4sf** | P4 with sigma_f = 1.0 in both sizes (section 3.2) | 0.004 / 0.131 / 0.067 |

Each calibration uses its own fit's pool posterior bank.

### 3.2 Blocking: the simulated X test is stronger than S1a's data show (confirmed in part; carried as a bracket)

**What was done.** The study's validation checked only widths, at K = 32. It is replaced by an
extended posterior-predictive check (`successor ppc`, criteria in
`successor.PPC_CRITERIA`). The criteria were written after the attack's report and before any
refitted calibration was checked. The check simulates S1a's own two runs with the realized
sessions: the 113-task secondary set (K113) and the base (K32). There are 450 data sets per
target (seeds 42-44 x 150), each analysed with the registered 10,000 resamples and flips. It
ranks the observed statistics by mid-rank:

- **Decision statistics** must lie in [0.05, 0.95]: X_4B, X_9B, p_X, pi_small and its two
  bounds, and the width of δ's 90% interval.
- **Structure statistics** must lie in [0.01, 0.99]: D_b and D_w per size, non-constant tasks,
  tasks with a non-zero harness difference in both sessions, positive and negative session
  products, and the per-size X sign-flip p.
- **Outcome probabilities:** each observed DR2 class and DR5 outcome needs simulated
  probability of at least 0.10.

An out-of-sample target, EXT81 (the 81 extension tasks, parametric), is reported beside them.

| Calibration | Verdict | K113 X_4B | K113 p_X (obs 0.157) | K113 δ 90% width | K113 qneg_4B / both-nonzero_4B | P(obs DR2), P(obs DR5) at K113 | Failed checks |
|---|---|---:|---:|---:|---|---|---|
| N0 base-normal (eval-3) | **fail** | 0.02 | 0.92 | 0.31 | 0.99 / 0.86 | 0.22, 0.79 | K113 X_4B |
| SS0 base spike-slab (eval-0, eval-2) | **fail** | 0.02 | 0.90 | 0.22 | 0.98 / 0.88 | 0.52, 0.92 | K113 X_4B |
| N0 with 4B's slab removed | **fail** | 0.17 | 0.76 | 0.98 | 0.97 / 0.97 | 0.26, 0.48 | K113 and K32 δ width |
| SS0 with 4B's slab removed | **fail** | 0.18 | 0.78 | 0.98 | 0.97 / 0.97 | 0.50, 0.73 | K113 and K32 δ width |
| P0 `fit-pool` (eval-1) | pass | 0.09 | 0.90 | 0.56 | 0.98 / 0.97 | 0.33, 0.81 | none |
| PR decoupled | pass | 0.11 | 0.85 | 0.88 | 0.98 / 0.96 | 0.28, 0.73 | none |
| P4 4B-null | pass | 0.16 | 0.82 | 0.94 | 0.98 / 0.98 | 0.31, 0.66 | none |
| P0 with sigma_b,4B = 0 | pass | 0.16 | 0.84 | 0.95 | 0.98 / 0.98 | 0.33, 0.72 | none |
| P0, sigma_f = 1 | pass | 0.12 | 0.81 | 0.46 | 0.97 / 0.92 | 0.32, 0.64 | none |
| P0 with sigma_b,4B = 0, sigma_f = 1 | pass | 0.20 | 0.74 | 0.83 | 0.96 / 0.95 | 0.34, 0.56 | none |
| P4sf (P4, sigma_f = 1) | pass | 0.20 | 0.72 | 0.86 | 0.96 / 0.94 | 0.34, 0.54 | none |

What this shows:

- **Part of the claim stands under every passing calibration.**
  - S1a's 113-task run has more 4B tasks with a non-zero harness difference in both sessions
    than the models produce: 15 against a median of 9-10.
  - More of those tasks have opposite signs: 9 negative products against a median of 4-5.
  - Both counts sit at mid-rank 0.94-0.98, inside the band set before the check but near its
    edge.
  - Observed p_X sits at mid-rank 0.72-0.90.
  - The models give S1a's own Inconclusive secondary reading probability 0.28-0.34.
  - The likeliest explanation is that 4B's per-task harness differences flip between sessions
    (task x harness x session noise), not that they are stable. Adding sigma_f = 1.0 moves
    every one of these statistics towards the centre, and it keeps 9B's D_b in range (rank
    0.16).
- **The rest does not hold for the pool-fitted calibrations.** Their K113 X_4B and p_X ranks
  are inside the band.

**Handling.** P0 is kept as the calibration most favourable to X, and P4sf as the least. P4sf
is the one closest to S1a on these statistics. The design tables report both, with PR and P4
between them. A forecast that holds only under P0 is marked as optimistic.

### 3.3 Blocking: "DR5 cannot be settled within 8 GPU-h" came from the 4B coupling (confirmed; re-run)

Every design was re-run under P0, PR, P4 and P4sf (section 4).

- **The share DR5 reads.** At S1a's estimates, the passing calibrations put pi°_small at
  0.067-0.098 over the 113 tasks. That is 0.03-0.06 below M. The base-fitted sources had it at
  0.107-0.115, only 0.015-0.025 below M.
- **NO-GO becomes reachable.** P(NO-GO) for C, D, E, F and F5 is 0.18-0.62. Under the
  base-fitted sources it was 0.05-0.17 (the evaluators' runs and the attack's unmodified
  re-runs). For E it is 0.23-0.54.
- **GO stays out of reach:** at most 0.03 for any design.
- **The change comes from the calibration, not from code.** The attack's unmodified re-runs
  reproduced the evaluators' numbers. This study's fast path equals the registered wrapper
  field by field (tests).

Section 4 also shows that the conclusion "more sessions on the base tasks barely help" was a
product of the failed calibration (section 4.4).

### 3.4 Minor and informational points

| Attack point | Handling |
|---|---|
| The validation was too loose and ran at the wrong K (K = 32 only; widths only) | Replaced by the extended check above at K113 and K32, with EXT81 out of sample. The criteria are fixed in code (`PPC_CRITERIA`). They were written after the attack's numbers were known. That is disclosed here: the check is not blind to which statistics misfit |
| Cost: stratified designs below K = 113 were priced at the pool-mean slot, but the cap depends on the draw | Recomputed over 2,000 registered stratified draws (`cost-draws.json`): F5 (K105 S5 R1) exceeds 478 minutes on 31% of draws, F (K94 S3 R2) on 4%. No recommended design draws tasks. Every K = 113 design has a fixed task list and an exact cap |
| Cost: realized x 1.2 x 1.05 is not the registered c_proj rule | Accepted, and it needs a decision (section 5). Under S1a's registered rule (the card's high price, 0.011274 GPU-h per episode at V = 20), 478 minutes buy at most about 700 episodes. Every K = 113 design needs 900-2,256 |
| Eval-1's "two reruns are essential" and "K113-R2 beats every other configuration" hold only within S = 2 | Confirmed (section 4): under every passing calibration E (K113 S4 R1) beats C (K113 S2 R2) on DR2 by 0.08-0.17 and matches or beats it on DR5. C is S1a's own secondary design, which already came out Inconclusive / INCONCLUSIVE |
| The S ≥ 3 X test (the U-statistic q_t, flipped whole) is not exact but is conservative | Accepted. The attack's null size at alpha 0.025 is 0.004-0.017, and DR2's false Present is at most 0.049. This study simulates the frozen statistic, so S ≥ 3 power is if anything understated. A successor registration must register the S ≥ 3 statistic, and could register the exact per-cell flip (size 0.016-0.026) for more power |
| Eval-2's composite counts a decisive DR5 at pi = M as success and ranks on gaps of 1-2 Monte Carlo SE | Dropped. The tables report each scenario separately, label decisive calls at pi = M as errors, and do not rank on differences below 0.05 |
| Eval-3's S2 verdict assumes locale heterogeneity like the harness contrast's | Accepted. Section 7 gives S2's power across heterogeneity scenarios and states which conclusions hold regardless |


## 4. Every design's decisiveness and cost, under the repaired calibrations

**Setup.**

- **Designs.** Successors of S1a with new serving sessions; the harnesses run interleaved in
  each session.
- **Task source.** Pool posterior of each calibration's own fit.
- **Simulation.** 450 data sets per cell (seeds 42-44 x 150). Each gets the registered analysis
  (`fast.analyse`, equal to `analyse.analyse`): 10,000 resamples and 10,000 sign flips, Holm
  DR2, and DR5 at M = 0.13 (M_9B = 0.18 for the 9B-only designs).
- **Monte Carlo error.** At most 0.024 per probability, and the per-seed rates agree within
  about 0.1 (`per_seed` in each file).
- **Scenarios.**
  - **fitted**: S1a's estimates under the calibration.
  - **piM**: the task-specific harness part scaled until pi°_small = 0.13 (pi°_9B = 0.18 for
    9B-only designs). At this point every decisive DR5 is an error.
  - **null**: no harness effect of any kind.
  - **2M**: pi°_small = 0.26 (pi°_9B = 0.36).
- **Truths.** They are computed over the 113 pool tasks:

| Calibration | pi°_small fitted | pi°_9B fitted | δ° fitted |
|---|---:|---:|---:|
| P0 | 0.098 | 0.167 | −1.1 pp |
| PR | 0.093 | 0.164 | −1.1 pp |
| P4 | 0.084 | 0.164 | −1.1 pp |
| P4sf | 0.067 | 0.131 | −1.1 pp |

The K32 designs read only the base, whose truth is lower (section 4.4). The δ0 scenario that
the evaluators used is dropped here: under these calibrations fitted δ° is already −1.1 pp.

### 4.1 At S1a's estimates: the range over P0, PR, P4 and P4sf

| Design | Cap-min | DR2 decisive | Present | Near-equivalent | DR5 decisive (all NO-GO) | GO | Both inconclusive | δ 90% width, pp |
|---|---:|---|---|---|---|---|---|---|
| A: K32 base, S2 R2 (S1a repeated) | 136 | 0.18-0.28 | 0.06-0.09 | 0.10-0.20 | 0.20-0.33 | 0.00 | 0.60-0.73 | 8.7-10.4 |
| A6: K32 base, S6 R2 | 396 | 0.58-0.76 | 0.28-0.43 | 0.15-0.47 | 0.28-0.72 | 0.00 | 0.18-0.37 | 6.5-8.7 |
| B: K113, S2 R1 | 206 | 0.25-0.30 | 0.15-0.22 | 0.06-0.15 | 0.11-0.22 | 0.01-0.03 | 0.64-0.71 | 5.8-6.4 |
| D: K113, S3 R1 | 306 | 0.54-0.62 | 0.27-0.48 | 0.13-0.34 | 0.20-0.46 | 0.00-0.01 | 0.29-0.40 | 5.1-5.7 |
| C: K113, S2 R2 (S1a's secondary design) | 376 | 0.66-0.75 | 0.36-0.65 | 0.10-0.32 | 0.18-0.44 | 0.00 | 0.20-0.27 | 4.7-5.4 |
| **E: K113, S4 R1** | **406** | **0.83-0.87** | 0.52-0.73 | 0.12-0.34 | **0.23-0.54** | 0.00 | 0.08-0.13 | 4.7-5.4 |
| F: K94 stratified, S3 R2 | 477 | 0.88-0.93 | 0.52-0.83 | 0.09-0.36 | 0.27-0.62 | 0.00 | 0.05-0.08 | 4.5-5.4 |
| F5: K105 stratified, S5 R1 | 471 | 0.92-0.96 | 0.67-0.83 | 0.10-0.28 | 0.25-0.61 | 0.00 | 0.02-0.05 | 4.6-5.3 |
| J2: 9B, K113, S2 R2 | 198 | 0.50-0.70 | 0.45-0.69 | 0.01-0.04 | 0.10-0.22 | 0.01-0.03 | 0.24-0.36 | 7.6-7.8 |
| J: 9B, K113, S4 R2 | 390 | 0.97-0.99 | 0.95-0.99 | 0.00-0.02 | 0.09-0.36 | 0.00 | 0.00 | 6.7-6.9 |
| J3: 9B, K113, S3 R3 | 426 | 0.96-1.00 | 0.94-0.99 | 0.00-0.02 | 0.09-0.33 | 0.00 | 0.00 | 6.7-6.8 |

For comparison, S1a's δ 90% width was 11.6 pp on the base and 5.4 pp on the 113 tasks.

**Power anchors and error at the boundary**, as the range over the same four calibrations:

| Design | piM: DR5 decisive (an error) | null: DR2 Near-equivalent | null: DR5 NO-GO | null: false Present | 2M: DR2 decisive | 2M: GO |
|---|---|---|---|---|---|---|
| A | 0.10-0.13 | 0.57-0.64 | 0.72-0.77 | 0.01-0.02 | 0.64-0.86 | 0.39-0.69 |
| A6 | 0.12-0.17 | 0.97-0.99 | 1.00 | 0.01-0.03 | 0.99-1.00 | 0.49-0.82 |
| B | 0.10-0.13 | 0.52-0.55 | 0.61-0.64 | 0.03 | 0.96-1.00 | 0.74-0.95 |
| D | 0.08-0.10 | 0.89-0.91 | 0.95 | 0.02-0.03 | 1.00 | 0.88-0.99 |
| C | 0.06-0.10 | 0.94-0.96 | 0.99 | 0.03 | 1.00 | 0.92-1.00 |
| **E** | **0.06-0.09** | **0.95-0.97** | **0.99-1.00** | **0.02-0.03** | **1.00** | **0.94-1.00** |
| F | 0.07-0.09 | 0.97 | 1.00 | 0.03 | 1.00 | 0.94-1.00 |
| F5 | 0.06-0.08 | 0.96-0.97 | 1.00 | 0.03-0.04 | 1.00 | 0.94-1.00 |
| J2 | 0.06-0.09 | 0.78-0.84 | 0.96-0.97 | 0.03-0.04 | 1.00 | 0.82-0.86 |
| J | 0.04-0.08 | 0.96-0.98 | 1.00 | 0.02-0.04 | 1.00 | 0.96 |
| J3 | 0.07-0.08 | 0.95-0.98 | 1.00 | 0.02-0.05 | 1.00 | 0.97-0.98 |

**What the tables say.**

1. **No design can admit S1b.**
   - At S1a's estimates GO is at most 0.03, for every design and calibration, and there GO is
     an error, because the truth is below M.
   - GO needs a share near 2M. Under the 4B-null calibrations that means pi°_9B near 0.5.
   - S1a's own 113-task upper bound for pi_small is already 0.16.
2. **DR5 NO-GO is reachable.** Its probability for C, D, E, F and F5 is 0.18-0.62 at S1a's
   estimates. It rises as 4B's share falls (P0 lowest, P4sf highest).
   - The base-fitted sources had it at 0.05-0.17. Section 3.3 gives the reason.
   - At the boundary (piM), the error rate of the same designs is 0.06-0.10, close to
     nominal.
3. **DR2 is mostly Present, and it comes from 9B's task-specific effects through the X test.**
   - P(p_δ ≤ 0.025) is only 0.02-0.05.
   - Near-equivalent is limited by π_small's upper bound, not by δ's interval:
     - for C and E, δ's 90% interval lies within ±7.5 pp in 99-100% of data sets;
     - π_small's upper bound falls below 0.12 in only 11-41% of them.
4. **E beats C.** E gains 0.08-0.17 on DR2 and matches or beats C on DR5. Under every passing
   calibration it has the highest DR2 of the designs that leave a margin under the cap.
   - F and F5 gain at most 0.10 on DR2 and 0.12 on DR5, for 65-71 more cap-minutes.
   - F5 is over the cap on 31% of draws.
5. **The 9B-only designs** (J, J3) are DR2-decisive with probability 0.96-1.00, but they read
   DR5 against M_9B and drop the 4B rung (option 3).

### 4.2 Per-calibration tables

Every design is listed under each calibration, with its cost. The columns are, in order:

- cap-minutes and data sets;
- at the fitted scenario: DR2 decisive (Present / Near-equivalent), DR5 decisive (NO-GO / GO),
  and both inconclusive;
- at piM: DR5 decisive, which is an error there;
- at null: DR2 Near-equivalent, DR5 NO-GO and false Present;
- at 2M: DR2 decisive and GO;
- the median δ 90% width.

The same numbers are in `designs-<calibration>.json`, and `python tables.py` prints them.

**P0**: `../q2-design-study/fit-pool.json` as committed (coupled).

Truth over the 113 tasks, as (pi°_small, pi°_9B, δ° in pp): fitted (0.098, 0.167, -1.14); null (0.0, 0.0, 0.0); pi2M (0.26, 0.405, -1.5); piM (0.13, 0.218, -1.22).

| Design | Cap-min | Fitted: DR2 decisive (Present / Near-eq.) | Fitted: DR5 decisive (NO-GO / GO) | Fitted: both inconclusive | piM: DR5 decisive (error) | Null: Near-eq. / NO-GO / false Present | 2M: DR2 decisive / GO | δ 90% width, pp |
|---|---|---|---|---|---|---|---|---|
| A-K32-S2R2 | 136 | 0.18 (0.08/0.10) | 0.20 (0.20/0.00) | 0.73 | 0.10 | 0.64 / 0.76 / 0.02 | 0.64 / 0.39 | 10.4 |
| A6-K32-S6R2 | 396 | 0.58 (0.43/0.15) | 0.28 (0.28/0.00) | 0.37 | 0.12 | 0.99 / 1.00 / 0.01 | 0.99 / 0.49 | 8.7 |
| B-K113-S2R1 | 206 | 0.27 (0.21/0.06) | 0.11 (0.09/0.02) | 0.71 | 0.10 | 0.52 / 0.62 / 0.03 | 0.96 / 0.74 | 6.4 |
| D-K113-S3R1 | 306 | 0.61 (0.48/0.13) | 0.20 (0.19/0.00) | 0.34 | 0.08 | 0.91 / 0.95 / 0.02 | 1.00 / 0.88 | 5.7 |
| C-K113-S2R2 | 376 | 0.75 (0.65/0.10) | 0.18 (0.18/0.00) | 0.20 | 0.06 | 0.96 / 0.99 / 0.03 | 1.00 / 0.92 | 5.4 |
| E-K113-S4R1 | 406 | 0.83 (0.71/0.12) | 0.23 (0.23/0.00) | 0.12 | 0.09 | 0.97 / 0.99 / 0.02 | 1.00 / 0.94 | 5.4 |
| F-K94-S3R2 | 477 (3% of draws over 478) | 0.92 (0.83/0.09) | 0.27 (0.27/0.00) | 0.05 | 0.08 | 0.97 / 1.00 / 0.03 | 1.00 / 0.94 | 5.4 |
| F5-K105-S5R1 | 471 (33% of draws over 478) | 0.93 (0.83/0.10) | 0.25 (0.25/0.00) | 0.05 | 0.06 | 0.97 / 1.00 / 0.03 | 1.00 / 0.94 | 5.3 |
| J2-9B-K113-S2R2 | 198 | 0.62 (0.61/0.01) | 0.11 (0.08/0.03) | 0.32 | 0.09 | 0.81 / 0.97 / 0.04 | 1.00 / 0.82 | 7.6 |
| J-9B-K113-S4R2 | 390 | 0.99 (0.99/0.00) | 0.09 (0.09/0.00) | 0.00 | 0.04 | 0.96 / 1.00 / 0.04 | 1.00 / 0.96 | 6.9 |
| J3-9B-K113-S3R3 | 426 | 0.99 (0.99/0.00) | 0.09 (0.09/0.00) | 0.00 | 0.07 | 0.98 / 1.00 / 0.02 | 1.00 / 0.97 | 6.7 |

**PR**: `fit-pool-rhob0.json` (decoupled).

Truth over the 113 tasks, as (pi°_small, pi°_9B, δ° in pp): fitted (0.093, 0.164, -1.13); null (0.0, 0.0, 0.0); pi2M (0.26, 0.425, -1.35); piM (0.13, 0.227, -1.18).

| Design | Cap-min | Fitted: DR2 decisive (Present / Near-eq.) | Fitted: DR5 decisive (NO-GO / GO) | Fitted: both inconclusive | piM: DR5 decisive (error) | Null: Near-eq. / NO-GO / false Present | 2M: DR2 decisive / GO | δ 90% width, pp |
|---|---|---|---|---|---|---|---|---|
| A-K32-S2R2 | 136 | 0.23 (0.09/0.14) | 0.22 (0.22/0.00) | 0.70 | 0.11 | 0.64 / 0.76 / 0.02 | 0.70 / 0.44 | 9.3 |
| A6-K32-S6R2 | 396 | 0.68 (0.39/0.28) | 0.48 (0.48/0.00) | 0.25 | 0.17 | 0.98 / 1.00 / 0.02 | 1.00 / 0.60 | 7.2 |
| B-K113-S2R1 | 206 | 0.29 (0.22/0.07) | 0.14 (0.11/0.03) | 0.68 | 0.11 | 0.54 / 0.61 / 0.03 | 0.98 / 0.81 | 6.0 |
| D-K113-S3R1 | 306 | 0.60 (0.45/0.15) | 0.22 (0.21/0.01) | 0.35 | 0.08 | 0.89 / 0.95 / 0.03 | 1.00 / 0.92 | 5.3 |
| C-K113-S2R2 | 376 | 0.71 (0.58/0.13) | 0.24 (0.23/0.00) | 0.23 | 0.08 | 0.95 / 0.99 / 0.03 | 1.00 / 0.98 | 4.8 |
| E-K113-S4R1 | 406 | 0.87 (0.73/0.14) | 0.24 (0.24/0.00) | 0.10 | 0.08 | 0.96 / 0.99 / 0.03 | 1.00 / 0.97 | 4.8 |
| F-K94-S3R2 | 477 (3% of draws over 478) | 0.93 (0.80/0.13) | 0.32 (0.32/0.00) | 0.05 | 0.08 | 0.97 / 1.00 / 0.03 | 1.00 / 0.98 | 4.7 |
| F5-K105-S5R1 | 471 (33% of draws over 478) | 0.95 (0.83/0.11) | 0.26 (0.26/0.00) | 0.03 | 0.07 | 0.96 / 1.00 / 0.04 | 1.00 / 0.98 | 4.7 |
| J2-9B-K113-S2R2 | 198 | 0.70 (0.69/0.01) | 0.10 (0.08/0.01) | 0.24 | 0.06 | 0.84 / 0.97 / 0.03 | 1.00 / 0.85 | 7.6 |
| J-9B-K113-S4R2 | 390 | 0.99 (0.98/0.01) | 0.11 (0.11/0.00) | 0.00 | 0.06 | 0.96 / 1.00 / 0.04 | 1.00 / 0.96 | 6.9 |
| J3-9B-K113-S3R3 | 426 | 1.00 (0.99/0.00) | 0.13 (0.12/0.01) | 0.00 | 0.07 | 0.98 / 1.00 / 0.02 | 1.00 / 0.98 | 6.7 |

**P4**: `fit-pool-4b0.json` (4B with no task-specific effect).

Truth over the 113 tasks, as (pi°_small, pi°_9B, δ° in pp): fitted (0.084, 0.164, -1.13); null (0.0, 0.0, 0.0); pi2M (0.26, 0.514, -1.47); piM (0.13, 0.255, -1.22).

| Design | Cap-min | Fitted: DR2 decisive (Present / Near-eq.) | Fitted: DR5 decisive (NO-GO / GO) | Fitted: both inconclusive | piM: DR5 decisive (error) | Null: Near-eq. / NO-GO / false Present | 2M: DR2 decisive / GO | δ 90% width, pp |
|---|---|---|---|---|---|---|---|---|
| A-K32-S2R2 | 136 | 0.25 (0.06/0.19) | 0.28 (0.28/0.00) | 0.66 | 0.12 | 0.64 / 0.77 / 0.02 | 0.84 / 0.66 | 8.7 |
| A6-K32-S6R2 | 396 | 0.67 (0.29/0.38) | 0.55 (0.55/0.00) | 0.28 | 0.17 | 0.98 / 1.00 / 0.02 | 0.99 / 0.73 | 6.5 |
| B-K113-S2R1 | 206 | 0.25 (0.16/0.09) | 0.15 (0.13/0.02) | 0.71 | 0.11 | 0.55 / 0.62 / 0.03 | 1.00 / 0.95 | 5.8 |
| D-K113-S3R1 | 306 | 0.54 (0.36/0.18) | 0.26 (0.25/0.01) | 0.40 | 0.08 | 0.90 / 0.95 / 0.02 | 1.00 / 0.99 | 5.1 |
| C-K113-S2R2 | 376 | 0.66 (0.50/0.17) | 0.28 (0.28/0.00) | 0.27 | 0.07 | 0.95 / 0.99 / 0.03 | 1.00 / 1.00 | 4.7 |
| E-K113-S4R1 | 406 | 0.83 (0.65/0.17) | 0.30 (0.30/0.00) | 0.13 | 0.09 | 0.95 / 0.99 / 0.03 | 1.00 / 1.00 | 4.7 |
| F-K94-S3R2 | 477 (3% of draws over 478) | 0.88 (0.66/0.22) | 0.42 (0.42/0.00) | 0.08 | 0.07 | 0.97 / 1.00 / 0.03 | 1.00 / 1.00 | 4.5 |
| F5-K105-S5R1 | 471 (33% of draws over 478) | 0.92 (0.75/0.17) | 0.36 (0.36/0.00) | 0.05 | 0.06 | 0.96 / 1.00 / 0.04 | 1.00 / 0.99 | 4.6 |
| J2-9B-K113-S2R2 | 198 | 0.69 (0.68/0.01) | 0.10 (0.09/0.01) | 0.24 | 0.06 | 0.83 / 0.97 / 0.03 | 1.00 / 0.85 | 7.6 |
| J-9B-K113-S4R2 | 390 | 0.99 (0.98/0.01) | 0.12 (0.12/0.00) | 0.00 | 0.06 | 0.96 / 1.00 / 0.04 | 1.00 / 0.96 | 6.8 |
| J3-9B-K113-S3R3 | 426 | 1.00 (0.99/0.00) | 0.13 (0.12/0.01) | 0.00 | 0.08 | 0.98 / 1.00 / 0.02 | 1.00 / 0.97 | 6.7 |

**P4sf**: `fit-pool-4b0.json` with sigma_f = 1.0 in both sizes.

Truth over the 113 tasks, as (pi°_small, pi°_9B, δ° in pp): fitted (0.067, 0.131, -1.11); null (0.0, 0.0, 0.0); pi2M (0.26, 0.514, -1.46); piM (0.13, 0.256, -1.23).

| Design | Cap-min | Fitted: DR2 decisive (Present / Near-eq.) | Fitted: DR5 decisive (NO-GO / GO) | Fitted: both inconclusive | piM: DR5 decisive (error) | Null: Near-eq. / NO-GO / false Present | 2M: DR2 decisive / GO | δ 90% width, pp |
|---|---|---|---|---|---|---|---|---|
| A-K32-S2R2 | 136 | 0.28 (0.08/0.20) | 0.33 (0.33/0.00) | 0.60 | 0.13 | 0.57 / 0.72 / 0.01 | 0.86 / 0.69 | 9.4 |
| A6-K32-S6R2 | 396 | 0.76 (0.28/0.47) | 0.72 (0.72/0.00) | 0.18 | 0.14 | 0.97 / 1.00 / 0.03 | 1.00 / 0.82 | 6.7 |
| B-K113-S2R1 | 206 | 0.30 (0.15/0.15) | 0.22 (0.21/0.01) | 0.64 | 0.13 | 0.54 / 0.64 / 0.03 | 1.00 / 0.95 | 6.1 |
| D-K113-S3R1 | 306 | 0.62 (0.27/0.34) | 0.46 (0.46/0.00) | 0.29 | 0.10 | 0.91 / 0.95 / 0.02 | 1.00 / 0.98 | 5.2 |
| C-K113-S2R2 | 376 | 0.69 (0.36/0.32) | 0.44 (0.44/0.00) | 0.25 | 0.10 | 0.94 / 0.99 / 0.03 | 1.00 / 1.00 | 4.9 |
| E-K113-S4R1 | 406 | 0.86 (0.52/0.34) | 0.54 (0.54/0.00) | 0.08 | 0.06 | 0.97 / 1.00 / 0.03 | 1.00 / 1.00 | 4.7 |
| F-K94-S3R2 | 477 (3% of draws over 478) | 0.89 (0.52/0.36) | 0.62 (0.62/0.00) | 0.07 | 0.09 | 0.97 / 1.00 / 0.03 | 1.00 / 0.99 | 4.7 |
| F5-K105-S5R1 | 471 (33% of draws over 478) | 0.96 (0.67/0.28) | 0.61 (0.61/0.00) | 0.02 | 0.08 | 0.97 / 1.00 / 0.03 | 1.00 / 1.00 | 4.6 |
| J2-9B-K113-S2R2 | 198 | 0.50 (0.45/0.04) | 0.22 (0.21/0.01) | 0.36 | 0.09 | 0.78 / 0.96 / 0.04 | 1.00 / 0.86 | 7.8 |
| J-9B-K113-S4R2 | 390 | 0.97 (0.95/0.02) | 0.36 (0.36/0.00) | 0.00 | 0.08 | 0.98 / 1.00 / 0.02 | 1.00 / 0.96 | 6.7 |
| J3-9B-K113-S3R3 | 426 | 0.96 (0.94/0.02) | 0.33 (0.33/0.00) | 0.00 | 0.07 | 0.95 / 1.00 / 0.05 | 1.00 / 0.98 | 6.8 |

The cap column's draw fractions for F and F5 come from the 450 task draws each cell simulated.
`cost-draws.json` gives 4% and 31% over 2,000 draws.

### 4.3 What the four evaluators reported, and whether it stands

Each evaluator's best design and its headline numbers at S1a's estimates, read against the
repaired calibrations:

| Evaluator (family) | Primary source | Extended check | Their best design | Their P(DR2), P(DR5) | Status |
|---|---|---|---|---|---|
| eval-0 (more sessions on the 32 base tasks) | spike-and-slab pool bank | fails (K113 X_4B 0.02) | fresh-S6 (A6) | 0.11, 0.04 | Superseded. Its verdict that more sessions barely beat repeating S1a does not hold under the repaired calibrations (A6 reaches 0.58-0.76 and 0.28-0.72). A6 is still dominated by E, for other reasons (section 4.4) |
| eval-1 (more tasks) | `fit-pool` bank (= P0) | passes | K113-R2 (C) | 0.68, 0.18 | Stands as the P0 reading of C. Its "best overall" claim is wrong outside S = 2: E beats C |
| eval-2 (K x S x R x sizes grid) | spike-and-slab pool bank | fails | K105 S5 R1 (F5) | 0.65, 0.11 | Superseded. F5 is also over the cap on 31% of task draws |
| eval-3 (frontier; S2 and S3) | base-normal pool bank (with spike-and-slab parametric) | fails | K113 S4 R1 (E) | 0.87 / 0.69, 0.12 / 0.16 | Its choice of E stands. Its DR5 numbers are superseded: NO-GO is 2-4 times as likely. Its S2 and S3 numbers stand with the qualification in section 7 |

The top of the ranking holds in every source the evaluators or this study ran:

1. Tasks first: use all or nearly all of the 113-task pool.
2. Then sessions.
3. Then reruns.
4. S1a's own shape (K = 32, S = 2) is last.

Two things changed: the level of DR5 decisiveness, through pi_4B, and the standing of more
sessions on the base tasks (section 4.4).

### 4.4 More sessions on the 32 base tasks: better than reported, still dominated

**What changed.** Under the repaired calibrations, A6 (6 sessions on S1a's base) reaches DR2
0.58-0.76 and NO-GO 0.28-0.72. Eval-0 reported 0.11 and 0.04 under the spike-and-slab bank,
which fails the extended check. Its verdict that more sessions barely beat repeating S1a was
an artefact of that calibration.

**Why the base reads differently.** Part of A6's DR5 strength is the base itself. On the 32
base tasks the population share at S1a's estimates is 0.092 (P0), 0.078 (PR), 0.069 (P4) and
0.056 (P4sf), lower than over the 113 tasks (`base-truth.json`).

**Where A6 loses to E.** A6 is dominated by E on everything except DR5 at the fitted scenario
under the 4B-null calibrations:

- At piM its error rate is 0.12-0.17, against 0.06-0.09 for E. The percentile bound with about
  ten informative tasks under-covers.
- At 2M, GO is 0.49-0.82, against 0.94-1.00.
- δ's 90% interval stays 6.5-8.7 pp wide, against 4.7-5.4.
- Its readings cover 32 tasks, not 113.


## 5. Cost and the cap rule

The cost model is `../q2-design-study/cost-model.json`, recomputed per design in
`cost-draws.json`. It reprices all 1,808 S1a episodes to within 0.4% of the realized 4.717
GPU-h. The engine never queued, so cost is set by VM slots at V = 20.

**Cap rule.** The model assumes this rule:

- Each job's cap is ceil(3 min USR1 lead + startup L + (N x slot / V + drain) x 1.2 (DR4) x
  1.05 (re-queue)).
- 6 minutes are reserved for an overlay build and its retry.
- The total must stay within S1a's 478-minute maximum (7.967 GPU-h).

At V = 20, one (size, session) pair takes 122 of the 200 allowed CPUs, so the jobs run one
after another. Sessions are at least 12 h apart, as in S1a.

| Design | Sizes | K | S | R | Episodes | Jobs | Cap-minutes | Cap GPU-h | Physical GPU-h | VM-h | Minimum calendar |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| A: S1a repeated | 4B, 9B | 32 base | 2 | 2 | 512 | 4 | 136 | 2.27 | 1.57 | 27 | 13 h |
| A6: more sessions | 4B, 9B | 32 base | 6 | 2 | 1,536 | 12 | 396 | 6.60 | 4.70 | 80 | 61 h |
| B | 4B, 9B | 113 | 2 | 1 | 904 | 4 | 206 | 3.43 | 2.49 | 45 | 13 h |
| D | 4B, 9B | 113 | 3 | 1 | 1,356 | 6 | 306 | 5.10 | 3.73 | 68 | 25 h |
| C: S1a's secondary design | 4B, 9B | 113 | 2 | 2 | 1,808 | 4 | 376 | 6.27 | 4.74 | 90 | 14 h |
| **E** | 4B, 9B | 113 | 4 | 1 | 1,808 | 8 | **406** | **6.77** | 4.97 | 90 | 37 h |
| F | 4B, 9B | 94 stratified | 3 | 2 | 2,256 | 6 | 477 (4% of draws over 478) | 7.95 | 5.97 | 112 | 26 h |
| F5 | 4B, 9B | 105 stratified | 5 | 1 | 2,100 | 10 | 471 (31% of draws over 478) | 7.85 | 5.82 | 105 | 49 h |
| J2 | 9B | 113 | 2 | 2 | 904 | 2 | 198 | 3.30 | 2.45 | 47 | 13 h |
| J | 9B | 113 | 4 | 2 | 1,808 | 4 | 390 | 6.50 | 4.90 | 93 | 37 h |
| J3 | 9B | 113 | 3 | 3 | 2,034 | 3 | 426 | 7.10 | 5.42 | 105 | 26 h |

Notes on the table:

- **Minimum calendar** is (S − 1) x 12 h plus one session window (both sizes' jobs for one
  session, run one after the other).
- **Pre-freeze budget.** No pre-freeze job is budgeted. An A0a-type check or an O1 retry
  would have to fit the margin: 72 minutes for E, 102 for C, 1-7 for F and F5.
- **The cap rule is a decision the program owner has to make.** S1a's registered c_proj is
  max(card high price, 1.25 c_A0a), and the card's high price at V = 20 is 0.011274 GPU-h per
  episode, 4.2 times the realized price. Under that rule, 478 minutes buy about 700 episodes,
  and no K = 113 design fits. The model's rule is DR4's own projection rule for S1b (realized
  x 1.2), plus the K-rule's re-queue allowance. A successor registration needs that rule
  adopted.
- **V = 32** fits the CPU limit (176 CPUs). It is unvalidated under load and is not used.


## 6. Options for the program owner

Every option below is stated for the realized sessions, not externally anchored, on this host.
The ranges run across the four calibrations that pass the extended check (P0, PR, P4, P4sf),
at S1a's estimates unless a row says otherwise.

### Option 1 (recommended): close Q2's harness-scale question now; no successor GPU

- **What S1a already answers.**
  - The two certified harnesses do not differ detectably on average at 4B and 9B.
  - Primary set: δ is −3.1 pp, 90% interval [−8.9, +2.7].
  - Registered secondary set, all 113 tasks: δ is −1.1 pp, 90% interval [−3.8, +1.6].
  - The harness share of within-task outcome variance is small next to rerun noise: π_small
    is 0.055 on the base and 0.084 on the 113 tasks, with a one-sided upper bound of 0.16 on
    the 113 tasks.
  - There is secondary, non-confirmatory evidence of task-specific harness effects at 9B:
    X_9B's interval excludes 0, and the secondary GLMM's (1|task:harness) test gives p = 0.045.
- **Why stop.**
  - Under D47 only DR5 GO admits S1b.
  - At S1a's estimates, P(GO) is at most 0.03 for every design within 8 GPU-h, under every
    passing calibration.
  - So no successor can change whether S1b runs. S1a's INCONCLUSIVE has already kept S1b out.
  - The scale question Q2 poses ("does the harness share shrink with scale?") needs S1b's
    larger rungs. The ladder was sized to detect a small-rung share of at least 0.13. S1a puts
    that share at about 0.07-0.10, below what the planned ladder could read as shrinkage.
- **Cost.** 0 GPU-h. The 5-7 cap-GPU-h of a successor stay available for other lines.
- **What is given up.**
  - A decisive DR2 reading. A Present reading would most likely be "task-specific effects at
    9B".
  - A formal DR5 NO-GO. That would change only which follow-up S1a "points to": after NO-GO,
    the observation factor, whose harness code does not exist upstream (D47).

### Option 2: one successor that only adds data (registration and pre-freeze audit, no gauntlet, D66)

**E: all 113 pool tasks, 4B and 9B, four new sessions per size, one rerun.**

| Quantity | Value |
|---|---|
| Cap-minutes | 406 of 478 (margin 72) |
| Cap GPU-h | 6.77 |
| Physical GPU-h | 4.97 |
| VM-h | 90 |
| Episodes | 1,808 |
| Jobs | 8, one (size, session) pair at a time |
| Minimum calendar | 37 h |

At S1a's estimates:

| Reading | E | C (K113 S2 R2) | D (K113 S3 R1) |
|---|---|---|---|
| Cap-minutes | 406 | 376 | 306 |
| P(DR2 decisive) | 0.83-0.87 | 0.66-0.75 | 0.54-0.62 |
| of which Present / Near-equivalent | 0.52-0.73 / 0.12-0.34 | 0.36-0.65 / 0.10-0.32 | 0.27-0.48 / 0.13-0.34 |
| P(DR5 NO-GO) | 0.23-0.54 | 0.18-0.44 | 0.20-0.46 |
| P(DR5 GO) | 0.00 | 0.00 | 0.00-0.01 |
| Both inconclusive | 0.08-0.13 | 0.20-0.27 | 0.29-0.40 |
| δ 90% width | 4.7-5.4 pp | 4.7-5.4 pp | 5.1-5.7 pp |

Power anchors for E:

- With no harness effect: Near-equivalent 0.95-0.97, NO-GO 0.99-1.00, false Present
  0.02-0.03.
- At π_small = M (an error if decisive): DR5 decisive 0.06-0.09.
- At π_small = 2M: DR2 1.00, GO 0.94-1.00.

How to choose among them:

- E beats C on DR2 under every passing calibration, and matches or beats it on DR5.
- C is S1a's own secondary design, which already came out Inconclusive / INCONCLUSIVE.
- D is the cheaper fallback at 306 cap-minutes.

**What a successor needs before it runs:**

- the cap rule (realized x 1.2 x 1.05, section 5);
- with R = 1, dropping D_w and P1 (P1 was already falsified);
- the S ≥ 3 X statistic, with the exact per-cell flip as an option;
- new sessions at least 12 h apart, with the harnesses interleaved within each session;
- a disclosure that the design and the scenarios were chosen after S1a's readings, and that
  the successor reuses S1a's tasks;
- that Present carries the main effect and the task-specific part together.
  - The δ test rejects only 3-5% of the time.
  - So Present would mean "harness effects exist on some tasks, mostly at 9B", not a main
    effect.

### Option 3: 9B only (estimand change; needs its own decision)

| Design | Cap-minutes | DR2 decisive (almost all Present) | DR5 against M_9B = 0.18: NO-GO / GO |
|---|---:|---|---|
| J2: 9B, K113, S2 R2 | 198 | 0.50-0.70 | 0.08-0.21 / 0.01-0.03 |
| J: 9B, K113, S4 R2 | 390 | 0.97-0.99 | 0.09-0.36 / 0.00 |
| J3: 9B, K113, S3 R3 | 426 | 0.96-1.00 | 0.09-0.33 / 0.00-0.01 |

- The harness signal lives at 9B, so these designs settle DR2 more cheaply.
- They read DR5 on π_9B against M_9B, which the registration allows only when DR1 drops 4B.
  4B is at 27-29%, not at the floor.
- They remove the 4B rung that S1b's contrast needs.
- Near-equivalent is out of reach, because π_9B's upper bound would have to fall below 0.12.

### Not recommended

| Design | Why |
|---|---|
| A6: more sessions on the 32 base tasks (396 cap-minutes; the registration's default after INCONCLUSIVE) | At S1a's estimates: DR2 0.58-0.76, NO-GO 0.28-0.72. Dominated by E: errors at π = M of 0.12-0.17, GO at 2M of 0.49-0.82, a δ width of 6.5-8.7 pp, and only 32 tasks covered (section 4.4) |
| F, F5 | They use 471-477 cap-minutes for at most 0.10 more DR2 and 0.12 more DR5 than E. F5's caps exceed 478 on 31% of task draws, and neither leaves room for a pre-freeze job |
| A: S1a repeated | DR2 0.18-0.28, DR5 0.20-0.33. The likeliest outcome repeats S1a's (both inconclusive 0.60-0.73) |


## 7. What S1a's noise floor implies for S2 and S3

### The floor itself, as the design study reads it

| Quantity | Base, 32 tasks | Secondary set, 113 tasks |
|---|---|---|
| D_b (cross-session discordance) | 11.3% | 10.4% |
| D_w (within-session discordance) | 12.5% | 10.2% (4B 11.1%, 9B 9.3%) |
| Session excess D_b − D_w | −1.2 pp; P1 falsified (upper bound 0.78 pp) | +0.2 pp (upper bound 1.44 pp) |
| 9B session shift | +5.5 pp (p 0.016) | +0.9 pp (p 0.65) |

- **Per-episode variance.** Rerun variance is about D_b / 2, so 0.05 per episode.
- **Informative tasks.** 54-56% of the pool's tasks never succeed and 15-18% always succeed.
  So only about 30% of tasks carry any contrast at 4B and 9B with 15 steps.
- **Session terms.**
  - The task x session and task x harness x session SDs are estimated at 0 to 0.66. They are
    weakly identified.
  - The new-session harness x session SD has an upper bound of 0.95-1.17 logits.
  - A shift common to one session's tasks happened once at 9B (+5.5 pp).

These are OSWorld desktop numbers for Qwen3.5-4B and 9B. They transfer to other environments
only as an assumption.

### S2 (Arabic computer-use locale: interface text against mirrored layout)

**Result.** Eval-3 computed the paired power of a −5 pp locale contrast at 9B with S1a's floor:
one-sided 5%, paired t over tasks, 1,200 data sets per cell (`eval-3/s2power.py`). The
repairs here do not change these numbers. They use the parametric 9B population, and 9B's
fitted task-specific SD is the same in the base and the pool fits (2.3 logits).

Eval-3's 4B rows (not shown) used the base fit's coupled sigma_b,4B of 1.46. After the repair
(0 to 0.7), 4B's rows move towards the "uniform" column.

Power at −5 pp, 9B, by distinct tasks K and episodes per (task, arm):

| K, episodes per task-arm | uniform (no task x locale variance) | S1a-like (task x harness SD) | sparse (spike-and-slab) | session stress |
|---|---:|---:|---:|---:|
| 18 (Relay), 8 (S4 R2) | 0.47 | 0.24 | 0.30 | 0.23 |
| 18, 32 (S8 R4) | 0.82 | 0.26 | 0.49 | 0.31 |
| 64 (OSWorld LibreOffice tasks in the pool), 8 | 0.98 | 0.62 | 0.60 | 0.61 |
| 113 (whole pool), 8 | 1.00 | 0.83 | 0.79 | 0.83 |
| 113, 4 (S2 R2) | 0.95 | 0.75 | 0.72 | 0.68 |

**The attack's qualification, accepted.** Whether S2 can pass a 5 pp gate depends on how much
the locale effect varies across tasks, and S1a cannot measure that. S1a's harness contrast is
a proxy. The registration defines the gate on a Relay noise-floor run that does not exist.
What does not depend on that assumption:

- With 18 Relay templates, a 5 pp gate passes only if the locale effect is nearly the same on
  every task.
  - Even then it needs at least 32 episodes per task-arm: 1,152 episodes for two arms, about
    4.6-4.9 cap-GPU-h at OSWorld's price.
  - With any heterogeneity like S1a's, power at K = 18 stays at 0.23-0.49 whatever the
    reruns, because tasks set the ceiling (Westfall, Kenny and Judd 2014).
- D68 already moved S2's repair onto Q2's certified OSWorld stack (route R2: LibreOffice with
  RTL enabled).
  - The eligible pool holds 64 LibreOffice tasks (calc 28, impress 24, writer 12).
  - At 8 episodes per task-arm they give 0.60-0.62 under S1a-like heterogeneity and 0.98 if the
    effect is homogeneous.
- A 5 pp gate at S1a-like heterogeneity needs about 100-115 distinct tasks at 8 episodes per
  task-arm. For one two-arm contrast at 9B that is 1,550-1,860 episodes, 5.3-6.6 cap-GPU-h at
  S1a's realized price x 1.2.
- **2x2 design.** The S2 proposal's text-by-direction 2x2 reads each main effect over all four
  cells. So a 2x2 with half the per-cell episodes has about the power of the two-arm figures
  above, for the same total episodes.
- **Every locale arm must run interleaved inside each serving session.** S1a's 9B session
  shift (+5.5 pp) is as large as the effect S2 wants to detect.

**Implication for S2.** S2's power gate cannot pass on Relay's 18 tasks. It can pass on the
OSWorld route only if the locale effect is close to homogeneous across 64 tasks, or if the
task set grows to about 100 distinct tasks. Distinct tasks bind, not reruns or GPU-h. This is
an input to the S2 repair run under D68; it changes no D68 line.

### S3 (does RL on one interface or locale transfer?)

**Result.** Eval-3 simulated 100 held-out instances and a +5 pp diagonal gain
(`eval-3/s3power.py`, seeds 42-44). In each case the base model and the checkpoint are
compared with 5 reruns each.

| Scenario, 5 reruns each | Power |
|---|---:|
| Interleaved in one serving session, homogeneous gain | 0.92-0.98 |
| Interleaved in one serving session, S1a-like task heterogeneity | 0.70-0.73 |
| Interleaved in one serving session, session stress | 0.53-0.58 |
| Interleaved, S1a-like heterogeneity, 10 reruns instead of 5 | 0.76-0.85 |
| Run in different serving sessions, S1a's fitted session SD | 0.53-0.84 |
| Run in different serving sessions, a 9B-sized session shift | 0.50 |

**Two reading rules follow.**

- Every checkpoint must be evaluated interleaved with its baseline in the same serving session.
- The dossier's kill rule ("diagonal gain below max(5 pp, 2x rerun SE)") must read a
  confidence bound, not the point estimate. Applied to the point estimate, it kills a true
  5 pp gain about half the time.

**Implication for S3.** S3 is 150 GPU-h, so it goes through the gauntlet whatever the floor
says. Its blockers are its prerequisites, not the floor:

- 100 or more templates in the target environment, which S2 also needs;
- S2's locale fixture;
- RL-seed variance, which S1a does not measure.

If D68 moves S2 onto OSWorld, S3's locale arm would have to follow it there or wait for a Relay
template factory.


## 8. Reproduction

Run every command from the repository root with the project's Python (numpy 2.5.2,
scipy 1.18.0) and `PYTHONPATH=.`. Set `$E = program/evidence/2026-10-10/q2-design-study` and
`$N = program/evidence/2026-10-10/q2-next-step-design-study`. Each output records its
provenance: commit, dirty flag, versions and argv.

- The fits, the checks, the design runs and `cost-draws.json` ran from a clean detached
  checkout of `2ded9da`.
- The design merges ran from `9d7d097`. Its changes after `2ded9da` touch only the merge: it
  takes the union of the design groups and keeps each scenario's spec.
- `base_truth.py` and `tables.py` in this directory read only committed outputs.

| Output | Command |
|---|---|
| `fit-pool-rhob0.json` | `python -m harness.q2_design.study fit --set pool --fix rho_b=0 --free c_4B sigma_b_4B c_9B sigma_b_9B --no-se --warm $E/fit-pool.json --out $N/fit-pool-rhob0.json` |
| `fit-pool-4b0.json` | `... fit --set pool --fix rho_b=0 sigma_b_4B=0.02 --free c_4B c_9B sigma_b_9B --no-se --warm $E/fit-pool.json --out ...` |
| `fit-pool-rhob0-sf.json`, `fit-pool-4b0-sf.json` | as the two above, with `sigma_f_4B sigma_f_9B` added to `--free` |
| `ppc-<calibration>.json` | for seeds 42, 43 and 44: `python -m harness.q2_design.successor ppc --fit F [--set-param ...] --targets K113 K32 EXT81 --seed S --nsim 150 --out ppc-NAME-seedS.json`; then `successor merge-ppc --out $N/ppc-NAME.json ppc-NAME-seed4{2,3,4}.json` |
| `designs-<calibration>.json` | for seeds 42, 43 and 44 and the three design groups: `python -m harness.q2_design.successor designs --fit F [--set-param ...] --source pool --designs ... --scenarios fitted piM null pi2M --seed S --nsim 150 --out ...`; then `successor merge-designs --out $N/designs-NAME.json <the nine files>` |
| `cost-draws.json` | `python -m harness.q2_design.successor cost-draws --out $N/cost-draws.json` |
| `base-truth.json` | `python $N/base_truth.py > $N/base-truth.json` (truth on the 32 base tasks for the K32 designs) |
| README tables | `python $N/tables.py` |

The calibrations are defined as follows:

| Calibration | `--fit` | `--set-param` |
|---|---|---|
| N0 | `$E/fit-base.json` | none |
| N0-4B0 | `$E/fit-base.json` | `sigma_b_4B=0` |
| SS0 | `$E/fit-base-spikeslab.json` | none |
| SS-4B0 | `$E/fit-base-spikeslab.json` | `sigma_b_4B=0` |
| P0 | `$E/fit-pool.json` | none |
| P0-4B0 | `$E/fit-pool.json` | `sigma_b_4B=0` |
| P0-sf1 | `$E/fit-pool.json` | `sigma_f=1.0` |
| P0-4B0-sf1 | `$E/fit-pool.json` | `sigma_b_4B=0 sigma_f=1.0` |
| PR | `$N/fit-pool-rhob0.json` | none |
| P4 | `$N/fit-pool-4b0.json` | none |
| P4sf | `$N/fit-pool-4b0.json` | `sigma_f=1.0` |

The design groups are:

| Group | Designs |
|---|---|
| g1 | C-K113-S2R2, E-K113-S4R1, D-K113-S3R1, B-K113-S2R1 |
| g2 | F-K94-S3R2, F5-K105-S5R1, A-K32-S2R2, A6-K32-S6R2 |
| g3 | J2-9B-K113-S2R2, J-9B-K113-S4R2, J3-9B-K113-S3R3 |

**Random streams.**

- Data: PCG64 [seed, 11, crc32(design)].
- Sign flips: [seed, 12, crc32(design)].
- Per-size diagnostic flips: [seed, 13, target].
- PPC data: [seed, 21, target].
- The posterior bank: seed 42.
- The registered bootstrap: seed 42 for every data set.

A design therefore sees the same random numbers under every scenario and calibration. The per-seed files are not committed: each merged file lists its inputs, and the commands above regenerate them exactly.

**Tests.** `tests/test_q2_design.py` has 21 tests. Five are new:

- `fast.analyse` equals `analyse.analyse` field by field at S = 2-4, R = 1-2 and 9B only.
- It reproduces S1a's committed readings: base p_X 0.4588 with bounds [0, 0.259909]; the
  113-task set p_X 0.1571 with bounds [0.019608, 0.162165].

The frozen modules are imported unchanged: `git diff d5f5798 -- harness/q2_stage1` is empty.


## 9. Limitations

- **Plug-in calibrations.** The repaired calibrations are conditional ML fits, warm-started at
  `fit-pool`; the parameters they do not name are held. The posterior banks plug in each fit's
  estimates, with no hyperparameter uncertainty.
  - The likelihood ratios in section 3.1 are therefore upper bounds on the full-profile ratios.
  - The P(decisive) forecasts are conditional on each calibration.
  - The four calibrations bracket the uncertainty the extended check cannot resolve. They are
    not a posterior over models.
- **In-sample check.** The pool-fitted calibrations are checked on the 113 tasks they were
  fitted to.
  - The only out-of-sample check is the base fits' EXT81, which the base-fitted sources fail.
  - A pool-fitted calibration has no held-out test. The extended check guards against
    structural misfit, not against overfitting.
- **Residual 4B misfit.** It is in section 3.2: 4B's harness differences reverse sign across
  sessions more often than any calibration produces (mid-rank 0.94-0.98). P4sf comes closest.
  If the true 4B noise is larger still, X power and P(DR2 Present) fall further, and P(NO-GO)
  rises.
- **Weakly identified session terms.**
  - New-session terms rest on two degrees of freedom: sigma_g 0 (pool) to 0.65 (base), and
    sigma_k at most 0.95-1.17.
  - A harness x session effect common to a new session's tasks (sigma_k) was not simulated
    here. Eval-1 ran it at 0.95 on C under P0: DR2 0.78, DR5 0.38.
- **Reused tasks, outcome-aware design.** A successor reuses S1a's 113 tasks, and the design
  and scenarios were chosen after S1a's readings. New-data tests stay valid conditional on the
  task set, but this must be disclosed.
  - Pooling S1a's records with a successor's was not modelled, and would need its own rule.
  - Eval-0's augmentation designs, which add sessions to S1a's, gave GO at most 0.02 and were
    dominated.
- **Cost.** The cost model assumes V = 20, S1a's startup and drain, and a quiet host. No
  pre-freeze job is budgeted.
- **Monte Carlo error.** Each cell has 450 data sets, so the Monte Carlo SE is at most 0.024
  per probability. Differences below 0.05 are not read.
- **Run-time evidence and metadata.**
  - The evaluators' and the attack's drivers and outputs stay in the session scratchpad and
    are not committed. Their numbers are quoted only where marked.
  - The `fit` field of the PR, P4 and P4sf outputs names the scratchpad copy of each fit file.
    The committed files here are byte-identical copies.
