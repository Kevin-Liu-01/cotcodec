# q2-stage1-successor-e-v1 (Q2 successor E): results

**Not externally anchored.** The OpenCUA-7B anchor is unavailable, as in S1a (DR-A:
ANCHOR-UNAVAILABLE). Every number below carries this label. **The data are complete:** all
eight E jobs ran, DR0 fired for none, and each size holds four sessions of scored records
(`report.json` `labels`: `incomplete` null). **Verification status:** the analyst's
self-check reproduced the primary reading (disclosure 4), but the fresh verifier that section
18 requires before RESULTS is written has not yet run (deviation 1). Read this file as
pending that verification.

Frozen registration `q2-stage1-successor-e-v1` (ledger row 19; file SHA-256 `47e65877...`;
freeze commit `f6144d6b`; plan `4e7298a7...`). The analysis ran on 2026-10-13/14 UTC on the
host, from the read-only export of `f6144d6b` that every E job ran from, with the registered
commands of section 18 (iii) unchanged. Steps, commands, Slurm jobs and digests:
`analysis/README.md`. Per-job evidence for OE and the eight E jobs: `README.md` (this
directory). E is its own sample: no estimate, test, rule or prediction below reads S1a's
sessions; the joint reading with S1a is a description and comes last.

## Outcome in one paragraph

For E's four new serving sessions per size, on all 113 eligible pool tasks, one episode per
(size, task, harness, session), under S1a's configuration (greedy decoding, 15 steps, a
2,048-token thinking budget, screenshots only), the two certified harnesses succeeded equally
often: H-GA and H-OSW-fixed each succeeded in 263 of 904 episodes, so δ (H-GA minus
H-OSW-fixed) is exactly 0.00 pp, with a 90% t interval of −2.44 to +2.44 pp (paired t
p = 1.000). The X sign-flip test gave p = 0.093, so no harness effect is Present. The 90%
interval lies within ±7.5 pp and the one-sided 95% upper bound of π_small is 0.1187, below
0.12, so **DR2 classifies the pair Near-equivalent**. π_small is 0.055 with one-sided 95%
bounds [0.010, 0.119], wholly below M = 0.13, so **DR5 is NO-GO**: S1b stays closed, as D69
forecast, and nothing starts. 4B is not at the floor (**DR1 does not fire**; 27.2% and
26.3%). The between-session rerun floor D_b is 10.7% (95% interval 8.0-13.5%). P1 is not
estimable at one episode per session; **P2-P5 are not falsified** (P3, forecast to fall with
probability 0.52-0.73, stands). Realized cost was 0.0027-0.0030 GPU-h per episode, 24-27% of
the card's high price (**DR4 does not fire**). No episode was lost to infrastructure in 1,808.

## What was registered (sections 2, 5, 10-14, 18, 19)

- **Design.** S1a's design with more data: Qwen3.5-4B and Qwen3.5-9B on H-OSW-fixed and H-GA,
  S1a's engine, prompts (pinned date), action path, VM image, settle and step cap unchanged;
  **all 113 eligible pool tasks**, no draw; **four new sessions per size (E1-E4)**, at least
  12 h 5 min apart, 9B then 4B in each; **one episode per (size, task, harness, session)**:
  226 episodes per job, 1,808 in all, V = 20.
- **Analysis sets.** Primary: the 113 tasks, raw verdicts, for every estimand, rule and
  prediction. Registered secondary: S1a's 32 base tasks (no rule reads it). Sensitivities:
  metric exceptions missing, postconfig server errors missing (D56), S1a's seven flagged tasks
  excluded, checker-corrected verdicts (`compare_pptx_files_zinv`), the fractional score, and
  the D82 gold-defect sensitivity (110 tasks, raw and corrected).
- **Estimands (section 10)** by S1a's frozen estimators on the (2, 113, 2, 4, 1) array: δ
  (pooled, per size, per session), X_z (mean over ordered session pairs of d_zts · d_zts'),
  X_c,z, D_b,z (six cross-session pairs per cell), π_z = (X_z⁺/4)/(X_z⁺/4 + D_b,z/2),
  π_small, the scale screens, the Bernoulli X, and S1a's two-session quantities for each of
  the six session pairs (descriptive). D_w, the session excess, the cross-block D_b and ρ are
  not estimable at R = 1.
- **Inference (section 11).** Task-cluster percentile bootstrap (10,000 resamples, seed 42;
  sessions fixed); δ paired t with its 90% t interval; X: the frozen one-sided sign flip of
  q_t (10,000 flips; conservative at S = 4), with the per-cell label permutation as a
  sensitivity; the crossed logit GLMM as the secondary model.
- **Rules (section 13)**: DR0-DR5 and DR-A with S1a's thresholds (DR2: Present if Holm over
  δ and X rejects, min p ≤ 0.025; Near-equivalent if not Present, δ's 90% t interval within
  ±7.5 pp and π_small's one-sided 95% upper bound below 0.12. DR5 against M = 0.13 for
  π_small). **Predictions (section 14)**: P1-P5, P1 not estimable.
- **Power statement (section 12)**, at S1a's estimates: DR2 decisive 0.83-0.87 (Present
  0.52-0.73, Near-equivalent 0.12-0.34); DR5 NO-GO 0.23-0.54, GO 0.00; both inconclusive
  0.08-0.13; median width of δ's 90% interval 4.7-5.4 pp.

## What ran

| Job | Size, session | VM job / GPU job (UTC) | Episodes scored | Infrastructure losses | GPU-h physical | GPU-h per episode (DR4 input) |
|---|---|---|---:|---:|---:|---:|
| E-9B-E1 | 9B, E1 | 1219 / 1221 (2026-10-12 04:28-05:08) | 226 of 226 | 0 | 0.6644 | 0.002940 |
| E-4B-E1 | 4B, E1 | 1222 / 1224 (05:09-05:46) | 226 of 226 | 0 | 0.6103 | 0.002700 |
| E-9B-E2 | 9B, E2 | 1251 / 1253 (17:53-18:33) | 226 of 226 | 0 | 0.6781 | 0.003000 |
| E-4B-E2 | 4B, E2 | 1254 / 1256 (18:36-19:12) | 226 of 226 | 0 | 0.6008 | 0.002659 |
| E-9B-E3 | 9B, E3 | 1265 / 1267 (2026-10-13 07:18-07:56) | 226 of 226 | 0 | 0.6475 | 0.002865 |
| E-4B-E3 | 4B, E3 | 1268 / 1270 (07:58-08:36) | 226 of 226 | 0 | 0.6228 | 0.002756 |
| E-9B-E4 | 9B, E4 | 1272 / 1274 (20:41-21:20) | 226 of 226 | 0 | 0.6461 | 0.002859 |
| E-4B-E4 | 4B, E4 | 1275 / 1277 (21:21-21:58) | 226 of 226 | 0 | 0.6050 | 0.002677 |

Every job ran from the export of `f6144d6b` on OE's overlay (job 1215), in the registered
order, each session at least 12 h 5 min after the previous session's later end, each pair
submitted on an empty queue, and no foreign Slurm job ran while any E job ran (`README.md`).
The E jobs used 5.0750 GPU-h physical (5.0908 with OE), against 4.97 projected; charged under
D22, 403 of E's 406 cap-minutes (the OE retry's 3 unspent). The analysis used no GPU: its
Slurm jobs 1279-1290 were CPU only (GLMM 1279; rescoring 1280-1287; report 1288; section 15
items 1289; joint reading 1290), ran 2026-10-13 23:40 to 2026-10-14 01:22 UTC, and every one
exited 0.

## Decision rules

| Rule | Outcome | Numbers |
|---|---|---|
| **DR0** validity | **does not fire** for any job | Every job ended with all 226 slots scored; 0 of 113 first attempts lost in every (size, harness) cell of every job; no lane error. Re-run by the registered CLI (`analysis/dr0-*.json`, byte-identical to each job's `pair/dr0.json`) and recomputed from the records by the report (`completeness`) |
| **DR-A** anchor | **ANCHOR-UNAVAILABLE** | As in S1a (S1a G0 item 9.6). Label: "not externally anchored" |
| **DR1** 4B floor | **does not fire** (4B stays) | 4B pooled success: H-OSW-fixed 27.21%, H-GA 26.33%, both above 10%. π_small is the mean of π_4B and π_9B |
| **DR2** harness pair | **Near-equivalent** | Not Present: Holm over δ (paired t p = 1.000) and X (sign flip p = 0.0927) needs min p ≤ 0.025. Near-equivalent: δ's 90% t interval [−2.44, +2.44] pp lies within ±7.5 pp, and π_small's one-sided 95% upper bound, 0.1187, is below 0.12 |
| **DR3** components | reported, no decision | Per-size table below |
| **DR4** cost | **does not fire** | Highest realized GPU-h per episode 0.003000 (E-9B-E2) against the high price at V = 20 of 0.011274 (ratio 0.27) |
| **DR5** S1b admission | **NO-GO** | π_small = 0.055, one-sided 95% bounds [0.010, 0.119], M = 0.13: the upper bound is below M. GO would need a lower bound above 0.13 |

**Consequence (section 13).** NO-GO and the closed S1b (D69) agree: S1b does not reopen and
nothing starts automatically. As S1a's section 11 says, a NO-GO points to an
observation-factor study, which would be a new proposal with its own gauntlet; whether to
write one is the program owner's choice.

## Predictions (read once, on the primary set, for E's realized sessions)

| | Prediction | Falsifier | Reading | Verdict |
|---|---|---|---|---|
| P1 | Session excess D_b − D_w > 0 | one-sided 95% UB of pooled D_b − D_w below 1 pp | D_w needs a within-session pair; E has one episode per session | **not estimable** (neither falsified nor supported; S1a already falsified P1) |
| P2 | Pooled D_b in 6-20% | 95% interval wholly outside [6%, 20%] | D_b 10.69%, 95% interval [8.00, 13.53]% | not falsified |
| P3 | Pair not "Present" | DR2 says Present | DR2 Near-equivalent | not falsified (the power statement forecast its falsification with probability 0.52-0.73) |
| P4 | 4B not at the floor | DR1 fires | 27.21% and 26.33% | not falsified |
| P5 | Realized GPU-h per episode at most the high price | DR4 fires | 0.002659-0.003000 against 0.011274 | not falsified |

## Primary estimands (113 tasks, raw verdicts)

Success, pooled over tasks and sessions: 4B 27.21% (H-OSW-fixed, 123 of 452) and 26.33%
(H-GA, 119); 9B 30.97% (140) and 31.86% (144). δ, D and session-shift rows are in percentage
points; X rows in probability²; π rows are shares. Intervals are task-cluster bootstrap
percentiles (10,000 resamples, seed 42), sessions held fixed.

| Estimand | Estimate | 95% interval | One-sided 95% bounds [lower, upper] |
|---|---:|---|---|
| δ pooled (H-GA − H-OSW-fixed), pp | 0.00 | [−2.77, 2.88] | [−2.32, 2.43] |
| δ_4B, pp | −0.88 | [−4.42, 2.65] | [−3.76, 1.99] |
| δ_9B, pp | 0.88 | [−2.88, 4.87] | [−2.43, 4.20] |
| δ_4B − δ_9B (scale screen), pp | −1.77 | [−6.86, 3.10] | [−5.97, 2.21] |
| D_b pooled, pp | 10.69 | [8.00, 13.53] | [8.41, 13.05] |
| D_b,4B, pp | 11.06 | [7.60, 14.75] | [8.11, 14.09] |
| D_b,9B, pp | 10.32 | [7.15, 13.72] | [7.67, 13.20] |
| X pooled | 0.0125 | [−0.0037, 0.0302] | [−0.0007, 0.0273] |
| X_4B | 0.0059 | [−0.0147, 0.0310] | [−0.0118, 0.0265] |
| X_9B | 0.0192 | [−0.0029, 0.0457] | [0.0000, 0.0413] |
| X_c,4B (task-specific part) | 0.0061 | [−0.0144, 0.0298] | [−0.0115, 0.0257] |
| X_c,9B | 0.0193 | [−0.0028, 0.0454] | [0.0001, 0.0408] |
| X, Bernoulli form (secondary, biased upward) | 0.0153 | [0.0006, 0.0324] | [0.0028, 0.0293] |
| π_4B | 0.026 | [0.000, 0.136] | [0.000, 0.117] |
| π_9B | 0.085 | [0.000, 0.196] | [0.000, 0.177] |
| π_small (mean of π_4B and π_9B) | 0.055 | [0.003, 0.130] | [0.010, 0.119] |
| π_4B − π_9B (scale screen) | −0.059 | [−0.176, 0.087] | [−0.155, 0.062] |
| D_w, D_b − D_w, cross-block D_b, ρ | not estimable (one episode per session) | | |

The same-block D_b equals D_b at one episode per session.

Tests. δ paired t over the 113 tasks: p = 1.000, 90% t interval [−2.44, +2.44] pp (width 4.89
pp, inside the power statement's median 4.7-5.4). Per size (secondary): 4B p = 0.630, 9B
p = 0.664. X sign flip (primary, one-sided; 30 tasks have a non-zero q_t): p = 0.0927. X label
permutation (sensitivity, the exact per-cell flip at R = 1): p = 0.0468; no rule reads it, and
it too is above DR2's 0.025, so the classification would be the same under it. The sign-flip
p-values are Monte Carlo (10,000 flips, PCG64 seed 42), as registered.

**DR3 components** (reported, no decision):

| Size | Success H-OSW-fixed / H-GA | D_b | X | X_c | π | δ per session E1 / E2 / E3 / E4, pp |
|---|---|---|---|---|---|---|
| 4B | 27.21% / 26.33% | 11.06% [7.60, 14.75] | 0.0059 | 0.0061 | 0.026 | −3.54 / 0.00 / −0.88 / +0.88 |
| 9B | 30.97% / 31.86% | 10.32% [7.15, 13.72] | 0.0192 | 0.0193 | 0.085 | +2.65 / +2.65 / −1.77 / 0.00 |

Success by session (H-OSW-fixed / H-GA): 4B E1 28.32% / 24.78%, E2 27.43% / 27.43%, E3
28.32% / 27.43%, E4 24.78% / 25.66%; 9B E1 29.20% / 31.86%, E2 29.20% / 31.86%, E3 31.86% /
30.09%, E4 33.63% / 33.63%. Each δ per session has a 95% interval about ±6-7 pp wide
(`report.json` `primary.estimates.delta_<size>_<session>`).

**Pairwise session quantities** (S1a's two-session functions on each pair's slice;
descriptive, no rule reads them). Session shift (later minus earlier session), pp, with its
two-sided sign-flip p:

| Pair | 4B shift (p) | 9B shift (p) | Harness effect by session δ_a − δ_b, 4B (SE) | 9B (SE) |
|---|---|---|---|---|
| E1-E2 | +0.88 (0.856) | 0.00 (1.000) | −3.54 (5.47) | 0.00 (3.77) |
| E1-E3 | +1.33 (0.583) | +0.44 (1.000) | −2.65 (4.44) | +4.42 (4.42) |
| E1-E4 | −1.33 (0.630) | +3.10 (0.192) | −4.42 (4.42) | +2.65 (4.07) |
| E2-E3 | +0.44 (1.000) | +0.44 (1.000) | +0.88 (4.62) | +4.42 (4.60) |
| E2-E4 | −2.21 (0.406) | +3.10 (0.190) | −0.88 (4.62) | +2.65 (4.44) |
| E3-E4 | −2.65 (0.239) | +2.65 (0.356) | −1.77 (4.87) | −1.77 (5.03) |

Holm over each size's six session tests: no rejection in either size. In S1a's primary reading
the 9B session test rejected for its two sessions (+5.5 pp, p = 0.016, on its 32 base tasks);
no E session pair differs detectably.

## Sensitivities and the registered secondary set (none changes a decision rule)

| Set | What changes | δ pooled, pp [95%]; 90% t | D_b pooled, pp | π_small [one-sided bounds] | X sign flip p | DR2 / DR5 as computed |
|---|---|---|---|---|---|---|
| Primary | none | 0.00 [−2.77, 2.88]; [−2.44, 2.44] | 10.69 | 0.055 [0.010, 0.119] | 0.093 | Near-equivalent / NO-GO |
| Checker-corrected (113 tasks) | `compare_pptx_files_zinv` in place of `compare_pptx_files` | identical to the primary in every value: 0 flips | | | | |
| Metric exception treated as missing | no metric exception in any episode | identical to the primary | | | | |
| **Postconfig server error treated as missing (D56)** | **0 episodes dropped**: no postconfig reply at HTTP ≥ 500 or without an HTTP reply | identical to the primary | | | | |
| Flagged tasks excluded (S1a's seven) | 106 tasks | +0.47 [−2.48, 3.54]; [−2.09, 3.03] | 10.85 | 0.051 [0.007, 0.119] | 0.124 | Near-equivalent / NO-GO |
| **D82 gold-defect tasks excluded, raw** | 110 tasks (without `5c1a6c3d`, `881deb30`, `8e116af7`) | 0.00 [−2.95, 3.07]; [−2.51, 2.51] | 10.98 | 0.055 [0.010, 0.119] | 0.089 | Near-equivalent / NO-GO |
| **D82 gold-defect tasks excluded, corrected** | as above, corrected verdicts | identical to the D82 raw reading: 0 flips | | | | |
| Fractional score (the score itself) | 33 episodes with 0 < score < 1 | δ = −0.21 pp | | | | |
| δ without truncated episodes (a mediator description) | episodes with a truncated step dropped | δ = −0.46 pp | | | | |
| **Registered secondary: S1a's 32 base tasks, raw** | fewer tasks | +0.39 [−5.08, 6.25]; [−4.60, 5.38] | 13.93 [8.07, 20.44] | 0.045 [0.000, 0.121] | 0.369 (label permutation 0.336) | Inconclusive / NO-GO (description only) |

The D82 sensitivity carries D80's label: "adjudicated by an isolated model on the owner's
instruction (D80); not human-validated". On the 32 base tasks DR2 would read Inconclusive,
because π_small's upper bound (0.121) is not below 0.12; no rule reads that set. There, D_b is
13.9% (4B 14.8%, 9B 13.0%), π_9B 0.091 (one-sided [0.000, 0.227]) and π_4B 0.000; no session
pair's shift test rejects after Holm.

## GLMM (secondary model, section 11; registered container `b15584f3...`, R package lock `abb8871d...` matched)

| Fit (113 tasks, 1,808 episodes) | Converged (`glmm.R`'s status) | Variance components (latent scale, full fit) | Latent shares (bootstrap 95%, 200 refits) | (1\|task:harness) likelihood-ratio test |
|---|---|---|---|---|
| E primary (job 1279, exit 0) | **Full fit: no.** Optimizer code 0, "relative convergence (4)", but no positive-definite Hessian and no log-likelihood (`ok` false). Reduced fit: yes (positive-definite Hessian, logLik −496.29) | task 72.4, task:size 2.71, task:size:harness 1.02; task:harness 4e-17; session, harness:session, task:session and task:harness:session at most 1.1e-7 | task 0.91 [0.75, 0.98], task:size 0.034 [0.002, 0.127], task:size:harness 0.013 [0, 0.060], task:harness 0.000 [0, 0.031]; 105 of the 200 refits did not converge, none failed | **not computed** (the fits did not both converge; statistic null) |

The registered GLMM reading is that the full fit did not converge, so the GLMM gives no
evidence either way on harness-specific task variance. The (1|task:harness:session) term is not
identified at one episode per cell (section 11). The task variance is large because 67 of the
113 tasks have the same outcome in all 16 of their episodes (54 never succeed, 13 always do).
G-E5's fit on synthetic rows of E's shape
converged; this fit on E's data did not.

## Infrastructure, per cell and per session (section 19; D56)

Over all 1,808 episode attempts (the final records and the attempts are the same: no
re-queue):

- **Losses by type: 0 of every type** in every (size, harness), (size, session) and
  (size, harness, session) cell; no re-queue, no cap truncation, no USR1 reached.
- **Guest-server restarts: 0** in every episode. **Context fallbacks: 0.**
- **Observations.** Agent screenshots 24,326 (4B/H-GA 6,323, 4B/H-OSW-fixed 6,036, 9B/H-GA
  6,018, 9B/H-OSW-fixed 5,949); checker reads 5,024. None was delivered only on a retry, none
  took longer than 30 s and none went undelivered, in any cell or session.
- **Postconfig.** 3,008 replies (752 per (size, harness)). Six failed replies, all `command`
  steps answered HTTP 200 with a non-zero `returncode` (the agent's state, D56), all at 4B:
  4B/H-GA in E2, E3 and E4, 4B/H-OSW-fixed in E1, E3 and E4 (one each). **Postconfig server
  errors (HTTP ≥ 500 or no reply): 0** in every cell and session, so the D56 sensitivity drops
  nothing.
- **Setup.** No setup reply failed. The offline-setup exclusions are S1a's: `26150609`,
  `982d12a5`, `e2b5e914` (reasons in `analysis/s15.json` `offline_setup_exclusions`).
- **IRError** (agent-caused, each harness's rule for an unparseable reply): 4B/H-GA 0,
  4B/H-OSW-fixed 10, 9B/H-GA 0, 9B/H-OSW-fixed 18. **Metric exceptions: 0.**
- **Fractional checker scores:** 33 episodes (4B/H-GA 7, 4B/H-OSW-fixed 9, 9B/H-GA 7,
  9B/H-OSW-fixed 10).
- **Uncertified action-path exposure** (key, chord or hold actions outside the certified
  keysyms): 468 such actions (4B/H-GA 131, 4B/H-OSW-fixed 122, 9B/H-GA 104, 9B/H-OSW-fixed
  111); 71 tasks have an exposed episode and 42 have none. δ by stratum (descriptive):
  exposed −1.41 pp, unexposed +2.38 pp.
- **Per session** (D56): per (size, session), 226 episodes scored in each; IRError 4B 5, 1, 1,
  3 and 9B 4, 3, 6, 5 (E1-E4); postconfig failures 4B 1, 1, 2, 2 and 9B 0 in each; every
  observation count above is 0 retried, slow or undelivered in each session.
- **Host.** Each E job's lane snapshots (start, block, end; 24 in all) show no foreign Slurm
  job; the highest one-minute load average was 5.71 (E-4B-E3's start). The 15-second queue
  watchers saw only each pair's own jobs (`README.md`).

Per-cell, per-session and per-(size, harness, session) tables over the final records and
every attempt: `analysis/report.json` (`cells`, `cells_by_size_session`,
`cells_by_size_harness_session`, `attempts`). Per-episode counts: `analysis/s15.json`
(`per_episode`, `losses_by_task` (empty), `setup_and_postconfig_failures`).

## Cost card (section 9 item 10) and DR4

| | GPU-h per episode (H-OSW-fixed, H-GA) | of central 0.009020 | of high 0.011274 | VM-h per episode |
|---|---:|---:|---:|---:|
| E-9B-E1 | 0.002940 (0.003007, 0.002873) | 0.33 | 0.26 | 0.0524 |
| E-4B-E1 | 0.002700 (0.002704, 0.002696) | 0.30 | 0.24 | 0.0490 |
| E-9B-E2 | 0.003000 (0.003003, 0.002997) | 0.33 | 0.27 | 0.0523 |
| E-4B-E2 | 0.002659 (0.002634, 0.002684) | 0.29 | 0.24 | 0.0487 |
| E-9B-E3 | 0.002865 (0.002882, 0.002848) | 0.32 | 0.25 | 0.0525 |
| E-4B-E3 | 0.002756 (0.002752, 0.002759) | 0.31 | 0.24 | 0.0490 |
| E-9B-E4 | 0.002859 (0.002906, 0.002812) | 0.32 | 0.25 | 0.0517 |
| E-4B-E4 | 0.002677 (0.002674, 0.002680) | 0.30 | 0.24 | 0.0489 |
| 9B pooled (904 episodes) | 0.002916 | 0.32 | 0.26 | 0.0522 |
| 4B pooled (904 episodes) | 0.002698 | 0.30 | 0.24 | 0.0489 |

GPU-h per episode is the GPU job's Slurm elapsed time (`scontrol` EndTime minus StartTime,
engine start-up included) over the job's episodes, all at V = 20. VM time totals about 91.4
VM-h (90 projected). E's 9B episodes cost about 8% more GPU time than S1a's (0.002701) and its
4B episodes about 7% more (0.002517); both stay far below the card. Steps per episode, mean:
4B/H-GA 12.76, 4B/H-OSW-fixed 12.56, 9B/H-GA 11.97, 9B/H-OSW-fixed 12.20; episodes reaching
the 15-step cap without `terminate`: 282, 276, 255 and 253 of 452. Output tokens per episode,
mean: 4B/H-GA 4,753, 4B/H-OSW-fixed 4,850, 9B/H-GA 4,207, 9B/H-OSW-fixed 4,690 (352-386 per
step); per job, 9B 4,394-4,529 and 4B 4,722-4,882. Distributions censored at 15 steps:
`analysis/s15.json` (`steps`, `output_tokens`, `cost_card_prices`).

## Truncation (section 19)

The share of steps that ended at 2,048 tokens without a complete tool call (the registered
definition, all final records): 4B/H-GA 0.35%, 4B/H-OSW-fixed 0.78%, 9B/H-GA 0.46%,
9B/H-OSW-fixed 0.62%; the share that hit the cap at all: 0.38%, 0.78%, 0.46%, 0.62%. Both sizes
are far below the 20% line, so **neither size's δ is labelled truncation-confounded**.

## Offline rescoring, checker corrections and checker noise (sections 9, 18, 19)

- **Coverage.** Every scored episode has a capture and a rescoring row: 226 of 226 per job,
  `exit_status` 0, about 1 h 38 min per job at `--time=08:00:00` (jobs 1280-1287). 16 rows
  carry an offline error, all of task `53ad5833` (2 per job), whose checker needs live state,
  as in S1a.
- **Corrected verdicts.** Primary (113 tasks): 1,792 from offline rescoring and **16 fell back
  to the live score** (`53ad5833`); D82 set (110 tasks): 1,744 and the same 16; S1a's 32 base
  tasks: 512 and 0. No metric exception, so the merge rule's zero was never used.
- **Flips: 0.** The corrected comparator applied to 36 episodes per job (288 in all,
  `compare_pptx_files` tasks) and changed no verdict in any set. Live versus offline raw
  replay mismatches: **0** of the 1,792 records replayed (`analysis/rescore-coverage.json`).
- **Checker-input-hash discordance.** 290 discordant cross-session pairs over the scored
  final records; none has identical checker-input hashes.
- **First divergence** (E's tasks, scored final records, each final attempt's step log; 1,808
  logs read, 0 missing). All 2,712 pairs are between sessions, and every one parts at step 1
  as "environment"; as registered, this is descriptive (the guest's top-bar clock is on every
  screenshot).

## Per domain (descriptive, primary, raw; corrected identical)

| Domain | Tasks | Success 4B (OSW / GA) | Success 9B (OSW / GA) | δ, pp |
|---|---:|---|---|---:|
| gimp | 8 | 56.3% / 65.6% | 71.9% / 68.8% | +3.13 |
| libreoffice_calc | 28 | 17.0% / 9.8% | 24.1% / 19.6% | −5.80 |
| libreoffice_impress | 24 | 29.2% / 36.5% | 22.9% / 32.3% | +8.33 |
| libreoffice_writer | 12 | 47.9% / 39.6% | 37.5% / 43.8% | −1.04 |
| multi_apps | 23 | 6.5% / 4.3% | 6.5% / 5.4% | −1.63 |
| thunderbird | 7 | 50.0% / 57.1% | 92.9% / 92.9% | +3.57 |
| vlc | 6 | 29.2% / 29.2% | 41.7% / 37.5% | −2.08 |
| vs_code | 5 | 40.0% / 30.0% | 40.0% / 40.0% | −5.00 |

Five to 28 tasks per domain: descriptions, not estimates. No interval is computed per domain.

## The joint reading with S1a (section 15; descriptive)

`analysis/joint.json`, labelled "descriptive joint reading of S1a and E: not registered
inference; no rule, test or prediction reads it". S1a's numbers are its 113-task secondary set
(2 sessions x 2 reruns per size); intervals are 95% task-cluster bootstrap percentiles that
resample the tasks jointly for both samples (seed 42). No p-value is reported.

| Quantity | S1a | E | E − S1a | Six sessions together |
|---|---|---|---|---|
| δ pooled, pp | −1.11 [−4.31, 2.10] | 0.00 [−2.77, 2.88] | +1.11 [−1.88, 4.20] | −0.37 [−2.99, 2.25] |
| δ_4B, pp | −1.77 [−5.09, 1.55] | −0.88 [−4.42, 2.65] | +0.88 [−2.88, 4.87] | −1.18 [−4.20, 1.70] |
| δ_9B, pp | −0.44 [−4.87, 4.20] | +0.88 [−2.88, 4.87] | +1.33 [−1.99, 4.87] | +0.44 [−3.32, 4.35] |
| D_b pooled, pp | 10.40 [7.52, 13.50] | 10.69 [8.00, 13.53] | +0.30 [−1.66, 2.29] | 10.23 [7.68, 12.93] |
| X_9B | 0.0376 [0.0022, 0.0774] | 0.0192 [−0.0029, 0.0457] | −0.0184 [−0.0501, 0.0111] | 0.0291 [0.0074, 0.0565] |
| X_4B | −0.0089 [−0.0332, 0.0155] | 0.0059 [−0.0147, 0.0310] | +0.0147 [−0.0111, 0.0442] | 0.0089 [−0.0049, 0.0257] |
| π_9B | 0.168 [0.010, 0.333] | 0.085 [0.000, 0.196] | −0.083 [−0.223, 0.048] | 0.131 [0.038, 0.237] |
| π_4B | 0.000 [0.000, 0.067] | 0.026 [0.000, 0.136] | +0.026 [−0.038, 0.127] | 0.039 [0.000, 0.111] |
| mean of π_4B and π_9B | 0.084 [0.005, 0.180] | 0.055 [0.003, 0.130] | −0.029 [−0.107, 0.051] | 0.085 [0.029, 0.151] |

As a description: on the same 113 tasks, E's estimates sit inside S1a's intervals, and every
E − S1a interval covers 0. The task-specific 9B signal that S1a's secondary set showed (X_9B
0.038, π_9B lower bound 0.038) is about half as large in E (X_9B 0.019, interval covering 0).
Across the six sessions together, X_9B's and π_9B's intervals exclude 0. None of this is a
registered reading, and none of it changes DR2 or DR5.

## Deviations and disclosures

**Deviation from the registration:**

1. **The fresh verifier had not run when this file was written.** Section 18 says "a fresh
   verifier recomputes the report from the SHA-checked raw records before RESULTS is
   written". The analysis was run by a single analyst with no means to start an independent
   agent, so this RESULTS precedes that verification. Until a fresh verifier's record is
   committed beside it, this file is provisional; if the verifier disagrees, the verifier's
   recomputation governs and this file is corrected. The analyst's own self-check
   (disclosure 4) is not that verification.

**Disclosures:**

2. **Orchestrator restarts.** The orchestrating session restarted twice after session E2
   (the operator's Mac crashed). The E2 operator's report file did not survive; the E3 and
   E4 operators resumed from the host's run and pair directories and the per-job README, and
   no job was resubmitted (`README.md` disclosures). This analysis started after a further
   resume, at 22:03 UTC on 2026-10-13, from the host's state: no analysis directory and no
   analysis job existed, so every analysis step ran once, and no Slurm job of the analysis was
   resubmitted. To spare the Mac's memory, every computation ran on the host;
   the Mac only read the small JSON outputs.
3. **The analysis waited for a quiet host.** At 22:03 the queue held job 1278, S2 v5's
   development confirmation (CPU only; another workstream's, submitted at 22:00:32, after
   E-4B-E4's VM batch job had ended at 21:58:06). The GLMM and the eight rescoring jobs were
   submitted together at 23:40:14 UTC, after five consecutive empty polls of the whole queue;
   the report, section 15 and joint jobs were submitted with only this analysis's own jobs in
   the queue. No other job was in the queue at any poll from 23:43 to 01:22 UTC. The GLMM
   therefore ran beside the eight rescoring jobs (G-E5 ran alone); its result does not depend
   on load (seed 42, deterministic code). To let it run then, its input was written from the
   raw records before the merge; written again from the merged records after the merge it is
   byte-identical (`ab6abee7...`). The registration fixes no order among these steps.
4. **Analyst's self-check, not the fresh verifier.** `ops/q2e-analysis/selfcheck.py`
   re-implements the primary point estimates, the δ paired t, the X sign flip and the
   bootstrap from the merged records and the registration's definitions, importing no
   harness module and using its own random streams (`analysis/selfcheck.json`). Every point
   estimate agrees with `report.json` to its rounding (largest difference 5e-7, on the
   primary set raw and corrected and on S1a's 32 base tasks); the paired t (p = 1.000, 90%
   [−2.44, +2.44] pp) is identical; its X sign flip gives p = 0.094 (registered 0.093); its
   bootstrap gives π_small's one-sided bounds [0.011, 0.119] (registered [0.010, 0.119]) and
   δ's [−2.32, 2.43] pp (identical). It recomputes DR2 Near-equivalent and DR5 NO-GO. It does
   not check the sensitivities, the GLMM, section 15 or the joint reading.
5. **Operator tooling.** The registered commands ran unchanged from the export; around them,
   `ops/q2e-analysis/e_ops.py` (commit `fb4458a6`) checked digests, submitted the jobs on an
   empty queue, ran the registered merge, counted rescoring coverage and live-score fallbacks
   (S1a's `rescore_jobs.py` definitions) and wrote provenance. It is not code of record, was
   written for this analysis without a separate review, and no local test suite was run for
   it (the Mac's memory, disclosure 2); its outputs are counts and wrappers, and the report is
   the registered CLI's own. Its digest is in `provenance-post.json`.
6. **The π_small bound is close to the near-equivalence line.** DR2 reads Near-equivalent
   because π_small's one-sided 95% upper bound, 0.1187, is below 0.12 by 0.0013 (the
   self-check's independent bootstrap: 0.1189). The flagged-task (0.1188) and D82 (0.1190)
   sensitivities keep it below 0.12; on S1a's 32 base tasks it is 0.121. The registered
   reading is the primary set's, and it is Near-equivalent; the margin is stated so the
   reading is not overstated.
7. **Rescoring.** As in S1a, task `53ad5833`'s checker needs live state, so its 16 episodes
   keep their live verdicts in the corrected outcome (`rescore-coverage.json`). The rescoring
   job outputs (checker warnings and debug prints, about 210 KB each) stay on the host, with
   their SHA-256 in `analysis/logs/rescore-logs.sha256`.
8. **Session-run disclosures** (`README.md`): operator handovers in sessions E1, E3 and E4; the
   E2 operator's network loss while it waited for the gap; failed queue polls on ssh timeouts;
   the `--test-only` start estimates of E-9B-E3 and E-9B-E4; the S2 v5 step-0 export staged on
   the host during E3's 9B pair (D96 item (2): file staging, not a job). None is a deviation,
   and none touches an E record.
9. **No job was rerun to improve an outcome**, no E job was resubmitted, and no frozen file
   changed: provenance checked every file of E's section 23 and S1a's section 20 in the
   export at both ends of the analysis (`analysis/provenance-pre.json`, `-post.json`, `pass`
   true; `verify` and `check-chain` exit 0).
10. **Evidence location.** This file and `analysis/` sit beside the per-job evidence, as the
    analysis assignment specified.

## What the result licenses

For E's four realized serving sessions per size, on the 113 eligible pool tasks, under this
configuration (greedy decoding, 15 steps, 2,048 output tokens with thinking, the matched
settle, V = 20 on vLLM v0.31.0, offline VMs), on this host, VM image and lane as configured
(the scope of D53's action-path certification), all labelled "not externally anchored":

- **DR2 Near-equivalent.** The two certified harnesses' success rates do not differ: δ =
  0.00 pp with a 90% t interval of ±2.44 pp, and the harness share's one-sided upper bound,
  0.119, is below the registered 0.12. Present is excluded by both registered tests (δ
  p = 1.000, X p = 0.093). This is DR2's decisive reading that S1a could not reach.
- **DR5 NO-GO.** π_small = 0.055 with one-sided bounds [0.010, 0.119] below M = 0.13: the
  harness share of within-task outcome variance is small for these sizes. S1b stays closed,
  as D69 decided on the design study's forecast; E confirms that forecast with data.
- **The between-session rerun floor**: D_b = 10.7% [8.0, 13.5] (4B 11.1%, 9B 10.3%), with no
  session pair differing detectably (12 pairwise tests, Holm: none).
- **4B is not at the floor** (27.2% and 26.3%).
- **The cost card**: 0.0027-0.0030 GPU-h and 0.049-0.052 VM-h per episode, 24-27% of the
  card's high price.
- **The infrastructure held** again: 0 losses, 0 restarts, 0 slow, retried or undelivered
  observations and 0 postconfig server errors in 1,808 episodes.

## What it does not license

- Equivalence in any wider sense. Near-equivalent is DR2's registered class, with a ±7.5 pp
  margin on δ and a 0.12 bound on π_small, for these sessions; the π_small bound cleared 0.12
  by 0.0013 (disclosure 6), and on S1a's 32 base tasks it does not.
- The absence of task-specific harness effects. X_9B is 0.019 with an interval reaching 0.046;
  the label-permutation sensitivity gives p = 0.047; the frozen X test is conservative at
  S = 4. A small share is not a zero share.
- Any claim about the population of sessions: every interval resamples tasks with E's four
  sessions per size held fixed. A harness x session effect common to a session's tasks is part
  of each δ per session, which ranged from −3.5 to +2.7 pp.
- Any pooled claim with S1a. The joint reading is descriptive (section 15), and E's design was
  chosen after S1a's readings (section 22, disclosure 1).
- Any GLMM evidence: the registered fit did not converge.
- Any claim about scale. 4B against 9B is a screen (δ difference −1.8 pp, π difference
  −0.059).
- Anything about other harnesses, the observation factor, other step caps, sampled decoding,
  other models, the online setting, another host or image, or more than 32 concurrent VMs.
- External validity of the runtime: there is no anchor.
- Corrected verdicts as primary evidence (they equal the raw verdicts here; the zinv
  correction's wider validation and D82's adjudication are model-made and not
  human-validated).

## Files

- `analysis/report.json`: every estimand, test, rule, prediction, sensitivity, secondary
  reading and count (the registered `analysis report`).
- `analysis/s15.json`: the section 15 items (tokens, steps, per-episode counts, losses by
  task, cost card against the prices, setup and postconfig failures, host snapshots, first
  divergence, exclusions).
- `analysis/joint.json`: the descriptive joint reading with S1a.
- `analysis/glmm-summary.json`, `analysis/glmm-out/`, `analysis/glmm-inputs/`: the GLMM.
- `analysis/rescore-coverage.json`, `analysis/rescore-*/`: offline rescoring.
- `analysis/costs.json`, `analysis/dr0-*.json`, `analysis/e.jsonl` (the merged records, the
  report's input), `analysis/selfcheck.json`, `analysis/provenance-*.json`;
  `analysis/README.md`: steps, commands, jobs and digests.
- `README.md` (this directory): OE and the eight E jobs.
