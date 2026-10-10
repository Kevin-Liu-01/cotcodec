# q2-stage1-rescoped-v1 (Q2 Stage S1a): results

**Not externally anchored.** The OpenCUA-7B anchor was UNAVAILABLE before any GPU job (G0 item
9.6; DR-A: ANCHOR-UNAVAILABLE). Every number below carries this label, and no output was
checked against the public runs. **The data are complete:** all four A1 jobs ran, DR0 fired for
none, and each size holds two sessions of scored base records (`guard.json` `labels`:
`incomplete` null).

Frozen registration `q2-stage1-rescoped-v1` (ledger row 16; file SHA-256 `f9db7cc3...`; freeze
commit `d5f5798`). The analysis ran on 2026-10-10 from the read-only export of `d5f5798` (the code
of record, unchanged). It followed `ops/s1a-analysis/RUNBOOK.md` at `6d85529` under D59, D61 and
D62. Evidence: `program/evidence/2026-10-10/q2-stage1-analysis/`. Read the report as
`report/report-guarded.json`; with complete data it is the registered `report.json` plus a
`guard` block.

## Outcome in one paragraph

On the 32 primary base tasks, under greedy decoding with 15 steps and a 2,048-token thinking
budget, the two certified harnesses did not differ detectably. δ (H-GA minus H-OSW-fixed) was
−3.1 pp, with a 90% t interval of −8.9 to +2.7 pp and paired-t p = 0.37. The X sign-flip test
gave p = 0.46. That interval is too wide to call the pair near-equivalent at the ±7.5 pp margin,
so **DR2 is Inconclusive**. The harness share π_small was 0.055, with one-sided 95% bounds of
0.000 and 0.260. The bounds straddle M = 0.13, so **DR5 is INCONCLUSIVE**. Under D47 only GO
admits S1b, so **S1b does not go to the gauntlet**. The between-session floor D_b was 11.3%
(95% interval 5.9-17.2%), and the within-session floor D_w was 12.5%. The session excess
D_b − D_w was −1.2 pp, with a one-sided 95% upper bound of 0.78 pp, below the registered 1 pp,
so **P1 is falsified**. P2-P5 stand. 4B is not at the floor (**DR1 does not fire**). Realized
cost was 0.0025-0.0027 GPU-h per episode, about 24% of the card's high price (**DR4 does not
fire**). No episode was lost to infrastructure in 1,808.

## What was registered (sections 2, 5, 8-12, 15)

- **Design.** Qwen3.5-4B and Qwen3.5-9B on the two harnesses the action-path suite certifies:
  H-OSW-fixed (OSWorld `bfd62bdc` qwen35vl with its own-spec fixes) and H-GA (gym-anything
  `aae6f7607` qwen35vl). Screenshot only, 15 steps, thinking on, 2,048 output tokens, greedy
  decoding for both, and the matched 60 s and 20 s settle. Two serving sessions per size, at
  least 12 h apart, each with two within-session reruns (R = 4 per size, task and harness). The
  sizes ran one after the other at V = 20 concurrent VMs.
- **Analysis sets.** Primary: the K_base = 32 base, fixed at the freeze, for every estimand and
  decision rule. Registered secondary: the base plus the extension blocks completed in all four
  jobs (here blocks 1-11, 113 tasks). It is reported with every estimand and enters no rule.
- **Estimands (section 9).** These are D_b and D_w (rerun discordance between and within
  sessions) and the excess D_b − D_w. They also include δ, the task-weighted H-GA minus
  H-OSW-fixed success, and X, the mean squared per-task harness effect, which carries δ². X_c is
  the task-specific part of X. π is the harness share of within-task outcome variance:
  π_z = (X⁺/4)/(X⁺/4 + D_b/2), and π_small is the mean over the two sizes. The list ends with
  the scale screen, the session shift, the harness effect by session, the common session share ρ
  and the cost card. **Every estimand is conditional on the two realized sessions per size.**
- **Inference (section 10).** A task-cluster percentile bootstrap (10,000 resamples, seed 42).
  δ: a paired t test, two-sided, with a 90% t interval. X: a one-sided sign-flip test (10,000
  flips). Session shift: a two-sided sign-flip test per size. The secondary model is a crossed
  logit GLMM (glmmTMB) with a likelihood-ratio test of (1|task:harness).
- **Decision rules (section 11)**, DR0-DR5 and DR-A, and **predictions (section 12)**, P1-P5,
  each with its registered falsifier, are restated with their outcomes below.

## What ran

| Job | Size, session | VM job / GPU job | Episodes scored (base + blocks 1-11) | Infrastructure losses | GPU-h physical | GPU-h per episode (DR4 input) |
|---|---|---|---:|---:|---:|---:|
| A1-9B-S1 | 9B, S1 | 1045 / 1047 (2026-10-09 22:21-23:34 UTC) | 452 of 452 | 0 | 1.2203 | 0.002700 |
| A1-4B-S1 | 4B, S1 | 1048 / 1050 (23:36-00:45) | 452 of 452 | 0 | 1.1469 | 0.002537 |
| A1-9B-S2 | 9B, S2 | 1051 / 1053 (2026-10-10 12:50-14:03) | 452 of 452 | 0 | 1.2211 | 0.002702 |
| A1-4B-S2 | 4B, S2 | 1062 / 1064 (14:09-15:17) | 452 of 452 | 0 | 1.1286 | 0.002497 |

The four jobs scored 1,808 episodes: 512 on the base and 1,296 on extension blocks 1-11.
Session-1 jobs completed all 11 fill blocks, so session 2 ran the same 11. The per-job checks
are in `README.md` in this directory. The A1 jobs used 4.7169 GPU-h physical; S1a's caps total
474 of 477 charged minutes (D22). The analysis used no GPU: all nine of its Slurm jobs were
CPU-only (1065-1068 rescoring, 1071 report, 1072 identity check, 1073 first divergence, 1074
GLMM, 1075 section 15 assembler). It ran 15:23-18:56 UTC on 2026-10-10. The step-by-step record
is `../q2-stage1-analysis/README.md`.

## Decision rules

| Rule | Outcome | Numbers |
|---|---|---|
| **DR0** validity | **does not fire** for any job | Every job completed its base. In every (size, harness) cell of every job, 0 of 226 first attempts were lost to infrastructure. No lane refusal. Re-run by the registered CLI (`dr0-*.json`, byte-identical to the per-job `pair/dr0.json`) and recomputed from the records by the guard |
| **DR-A** anchor | **ANCHOR-UNAVAILABLE** | G0 item 9.6: at most 6 of the 116 tasks keep the config and checker the public runs were scored with (58 needed), so A0b and ANC were never submitted. Label: "not externally anchored" |
| **DR1** 4B floor | **does not fire** (4B stays) | 4B pooled success on the base: H-OSW-fixed 28.91%, H-GA 26.56%, both at or above 10%. π_small is therefore the mean of π_4B and π_9B |
| **DR2** harness pair | **Inconclusive** | Not Present: Holm over δ (p = 0.3671) and X (p = 0.4588) needs min p ≤ 0.025. Not near-equivalent: the 90% t interval of pooled δ, [−8.91, +2.66] pp, crosses −7.5 pp, and π_small's one-sided 95% upper bound, 0.260, is not below 0.12. Both near-equivalence conditions fail |
| **DR3** components for S1b | reported, no decision | Per-size table below |
| **DR4** cost | **does not fire** | Highest realized GPU-h per episode: 0.002702 (A1-9B-S2), against the high price at V = 20 of 0.011274 (ratio 0.24). By the rule, any S1b projection uses realized cost x 1.2, with no re-probe required by DR4. This is moot while S1b does not start |
| **DR5** S1b admission | **INCONCLUSIVE** | Share π_small = 0.055, one-sided 95% bounds [0.000, 0.260], M = 0.13. GO needs a lower bound above 0.13 (it is 0.000). NO-GO needs an upper bound below 0.13 (it is 0.260) |

**Consequence (D47, section 11).** DR5 INCONCLUSIVE starts no S1b, so the harness scale ladder
does not go to the gauntlet. The registration says that after INCONCLUSIVE the result points to
more sessions at 4B and 9B. Any such follow-up would be a new proposal with its own gauntlet,
and whether to pursue one is the program owner's choice. Nothing here starts it.

## Predictions (read once, on the primary set)

| | Prediction | Falsifier | Reading | Verdict |
|---|---|---|---|---|
| P1 | Session excess D_b − D_w > 0 | one-sided 95% upper bound of pooled D_b − D_w below 1 pp | estimate −1.17 pp, 95% interval [−3.52, +1.56], one-sided upper bound **0.78 pp** | **falsified** |
| P2 | Pooled D_b in 6-20% | 95% interval wholly outside [6%, 20%] | D_b 11.33%, 95% interval [5.86, 17.19]% | not falsified |
| P3 | Pair not "Present" | DR2 says Present | DR2 Inconclusive | not falsified |
| P4 | 4B at least 10% under at least one harness | DR1 fires | 28.91% and 26.56% | not falsified |
| P5 | Realized GPU-h per episode at most the high price | DR4 fires | 0.002497-0.002702 against 0.011274 | not falsified |

## Primary estimands (base, 32 tasks, raw verdicts)

Success, pooled over tasks, sessions and reruns: 4B 28.91% (H-OSW-fixed) and 26.56% (H-GA); 9B
32.81% and 28.91%. δ, D and session-shift rows are in percentage points. X rows are in
probability² and π rows are shares, neither in pp. Intervals are task-cluster bootstrap
percentiles (10,000 resamples, seed 42), and sessions are held fixed.

| Estimand | Estimate | 95% interval | One-sided 95% bounds [lower, upper] |
|---|---:|---|---|
| δ pooled (H-GA − H-OSW-fixed), pp | −3.12 | [−10.55, 2.73] | [−9.38, 1.95] |
| δ_4B, pp | −2.34 | [−10.16, 4.69] | [−8.59, 3.91] |
| δ_9B, pp | −3.91 | [−12.50, 2.34] | [−10.94, 1.56] |
| δ_4B − δ_9B (scale screen), pp | 1.56 | [−3.91, 7.81] | [−3.12, 7.03] |
| D_b pooled, pp | 11.33 | [5.86, 17.19] | [7.03, 16.02] |
| D_b,4B, pp | 14.06 | [7.03, 21.88] | [8.59, 20.31] |
| D_b,9B, pp | 8.59 | [3.91, 14.06] | [4.69, 13.28] |
| D_w pooled, pp | 12.50 | [6.64, 19.14] | [7.42, 17.97] |
| D_w,4B, pp | 16.41 | [7.81, 25.78] | [9.38, 24.22] |
| D_w,9B, pp | 8.59 | [3.91, 14.06] | [4.69, 13.28] |
| D_b − D_w pooled (session excess), pp | −1.17 | [−3.52, 1.56] | [−3.12, 0.78] |
| D_b − D_w, 4B, pp | −2.34 | [−7.03, 3.12] | [−6.25, 1.56] |
| D_b − D_w, 9B, pp | 0.00 | [0.00, 0.00] | [0.00, 0.00] (see note) |
| D_b on same-block pairs, pp | 11.72 | [6.25, 17.58] | [7.03, 16.80] |
| D_b on cross-block pairs, pp | 10.94 | [5.47, 16.80] | [6.25, 16.02] |
| X pooled | 0.0117 | [−0.0312, 0.0703] | [−0.0273, 0.0586] |
| X_4B | 0.0078 | [−0.0469, 0.0625] | [−0.0391, 0.0547] |
| X_9B | 0.0156 | [−0.0312, 0.0938] | [−0.0312, 0.0781] |
| X_c,4B (task-specific part) | 0.0084 | [−0.0447, 0.0546] | [−0.0366, 0.0471] |
| X_c,9B | 0.0150 | [−0.0309, 0.0815] | [−0.0298, 0.0690] |
| X, Bernoulli-corrected form (secondary, biased upward) | 0.0156 | [−0.0195, 0.0716] | [−0.0163, 0.0632] |
| π_4B | 0.027 | [0.000, 0.200] | [0.000, 0.176] |
| π_9B | 0.083 | [0.000, 0.444] | [0.000, 0.375] |
| π_small (mean of π_4B and π_9B) | 0.055 | [0.000, 0.306] | [0.000, 0.260] |
| π_4B − π_9B (scale screen) | −0.056 | [−0.322, 0.100] | [−0.273, 0.077] |
| Session shift, 4B (S2 − S1), pp | 2.34 | [−2.34, 7.03] | [−1.56, 6.25] |
| Session shift, 9B (S2 − S1), pp | 5.47 | [2.34, 9.38] | [2.34, 8.59] |

Tests. δ paired t: p = 0.3671, with a 90% t interval of [−8.91, +2.66] pp. Per size (secondary):
4B p = 0.5401, 9B p = 0.3045. X sign flip (primary, one-sided): p = 0.4588. X label permutation
(sensitivity): p = 0.2796. Session sign flip (primary, two-sided, per size): 4B p = 0.5631, 9B
p = 0.0163.

**Note on the 9B excess.** On the base, every discordant 9B (task, harness) cell is a 3-to-1
split of its four reruns: 11 such cells, the odd rerun in session 1 in 6 and in session 2 in 5.
The other 53 cells are concordant. In a 3-to-1 cell the between-session and within-session
discordance fractions are both 1/2, so D_b,9B equals D_w,9B in every bootstrap resample, and the
excess interval is exactly 0. 4B has 47 concordant cells, 11 3-to-1 cells and six 2-to-2 cells.
Of the six, five split within each session and one split by session.

**DR3 components** (reported, no decision; `s15.json` `dr3`):

| Size | Success H-OSW-fixed / H-GA | D_b | D_w | X | X_c | ρ (common session share) | Session shift | Harness effect by session (δ_S1 − δ_S2) |
|---|---|---|---|---|---|---|---|---|
| 4B | 28.91% / 26.56% | 14.06% [7.03, 21.88] | 16.41% [7.81, 25.78] | 0.0078 | 0.0084 | not defined: the session-variance estimate is −0.0117, at or below 0, and D_b − D_w ≤ 0 | +2.34 pp (p 0.563) | +4.69 pp (SE 6.87) |
| 9B | 32.81% / 28.91% | 8.59% [3.91, 14.06] | 8.59% [3.91, 14.06] | 0.0156 | 0.0150 | not defined: the session-variance estimate is 0 | +5.47 pp (p 0.016) | +1.56 pp (SE 6.14) |

The 9B session shift is significant at 0.05 by its own per-size test. No decision rule reads it,
there are two per-size tests, and it describes these two sessions only. 9B succeeded more often
in session 2 than in session 1 on the base. In the secondary set the 9B shift is +0.89 pp
(p 0.65).

## Sensitivities (every one changes no decision rule)

| Set | What changes | δ pooled, pp [95%] | D_b pooled, pp | D_b − D_w, pp (1-sided UB) | π_small [1-sided bounds] | X sign flip p | DR2 / DR5 (description only) |
|---|---|---|---|---|---|---|---|
| Primary | none | −3.12 [−10.55, 2.73] | 11.33 | −1.17 (0.78) | 0.055 [0.000, 0.260] | 0.459 | Inconclusive / INCONCLUSIVE |
| Checker-corrected verdicts (base) | `compare_pptx_files_zinv` in place of `compare_pptx_files` | identical to the primary in every value: 0 flips | | | | | |
| Metric exception treated as missing (section 7.2) | 1 episode (4B, H-GA, S1, task `fba2c100`; its cell is 0 in every rerun) | identical to the primary in every value | | | | | |
| **Postconfig server error treated as missing (D56)** | **0 episodes dropped**: no postconfig reply at HTTP ≥ 500 or without an HTTP reply | identical to the primary in every value | | | | | |
| Flagged tasks excluded (section 8) | the base minus `70bca0cc` and `358aa0a7` (30 tasks) | −2.50 [−10.42, 3.33] | 11.25 | −1.25 (0.83) | 0.060 [0.000, 0.275] | 0.447 | Inconclusive / INCONCLUSIVE |
| Fractional score (the score itself) | 14 base episodes with 0 < score < 1 | δ = −3.06 pp | | | | | |
| δ without truncated episodes (a mediator description, not a de-confounded effect) | episodes with a step at the cap dropped | δ = −3.26 pp | | | | | |
| Registered secondary, raw (base + blocks 1-11, 113 tasks) | more tasks | −1.11 [−4.31, 1.99]; 90% t [−3.81, 1.60] | 10.40 [7.52, 13.39] | +0.22 (1.44) | 0.084 [0.020, 0.162] | 0.157 (label permutation 0.035) | Inconclusive / INCONCLUSIVE |
| Registered secondary, corrected | as above | identical to the secondary raw: 0 flips; 16 verdicts fell back to live scores (below) | | | | | |

The secondary set is reported with every estimand and never enters a rule. In it, π_9B is 0.168
(one-sided [0.038, 0.304]) and π_4B is 0.000, X_9B is 0.0376 (95% interval [0.0022, 0.0796]),
and the π scale screen is −0.168 (95% interval [−0.321, −0.009]). These are registered secondary
descriptions and decide nothing. The full secondary tables are in `report-guarded.json`
(`secondary_base_plus_completed_extension`) and `s15.json` (`secondary_corrected`).

## GLMM (secondary model, section 10.1; registered container `b15584f3...`, R package lock `abb8871d...` matched)

| Fit | Converged (`glmm.R`'s status) | Variance components (latent scale) | Latent shares (bootstrap 95%, 200 refits) | (1\|task:harness) likelihood-ratio test |
|---|---|---|---|---|
| **Primary** (base, 512 episodes, 32 tasks): the registered reading | **No.** Full fit: optimizer code 1, "singular convergence (7)", no positive-definite Hessian, logLik not returned. Reduced fit: "relative convergence (4)", no positive-definite Hessian | task 32.6, task:size 3.23, task:harness 1.44, session 0.088; the other components below 1e-7 | task 0.80 [0.42, 0.96], task:size 0.079 [0, 0.50], task:harness 0.035 [0, 0.15], session 0.002 [0, 0.007]. Taken from the fit that did not converge; 98 of the 200 refits did not converge | **not computed** (the fits did not both converge; statistic null) |
| Secondary (base + blocks 1-11, 1,808 episodes, 113 tasks): reported beside it | Yes, both fits (relative convergence, positive-definite Hessian) | task 98.1, task:size 3.44, task:harness 1.32, task:size:harness 0.31, task:harness:session 0.074; session, harness:session and task:session about 0 | task 0.92 [0.89, 0.98], task:size 0.032 [0.005, 0.062], task:harness 0.012 [0, 0.026], task:harness:session 0.0007 [0, 0.008]. 93 of the 200 refits did not converge | χ² = 4.00, df 1, p = 0.045 (boundary-corrected 0.023) |

The registered reading of the GLMM is the primary fit, and it did not converge. The registration
says a fit that does not converge is reported as such, so the GLMM gives no registered evidence
on harness-specific task variance. The secondary fit's test (p = 0.045, boundary-corrected 0.023)
comes from a secondary model on the secondary set. It is not a decision input and supports no
interaction claim (section 10.1).

## Infrastructure, per cell and per session (section 15; D56)

Over all 1,808 episode attempts (finals and attempts are the same here: no re-queue):

- **Losses by type: 0 of every type** in every (size, harness), (size, session) and
  (size, harness, session) cell. There were no re-queues, no cap truncations and no USR1.
- **Guest-server restarts: 0** in every episode.
- **Observations.** The agent's screenshots: 24,218 (4B/H-GA 6,269, 4B/H-OSW-fixed 6,047,
  9B/H-GA 5,987, 9B/H-OSW-fixed 5,915). Checker reads: 5,031. None was delivered only on a
  retry, none took longer than 30 s and none went undelivered, in any cell or session.
- **Postconfig.** 3,008 replies (752 per (size, harness)). Six failed replies, all `command`
  steps answered HTTP 200 with a non-zero `returncode` (the agent's state): 4B/H-GA/S2 2,
  4B/H-OSW-fixed/S1 2 and 4B/H-OSW-fixed/S2 2, none in 9B. **Postconfig server errors (HTTP ≥ 500
  or no reply): 0** in every cell and session, so the D56 sensitivity drops nothing.
- **Setup.** 5,312 setup replies, none failed. The offline-setup exclusions are
  `26150609` (rules (a), (b)), `982d12a5` (rule (b)) and `e2b5e914` (rules (a), (b)), with their
  reasons in `s15.json` `offline_setup_exclusions`.
- **IRError** (agent-caused, handled under each harness's rule for an unparseable reply):
  4B/H-GA 2, 4B/H-OSW-fixed 6, 9B/H-GA 0, 9B/H-OSW-fixed 11. **Metric exceptions:** 1 (4B/H-GA,
  S1, base task `fba2c100`; scored 0 in the primary). **Context fallbacks:** 0.
- **Fractional checker scores:** 35 episodes in all (4B/H-GA 7, 4B/H-OSW-fixed 8, 9B/H-GA 11,
  9B/H-OSW-fixed 9), 14 of them on the base.
- **Uncertified action-path exposure** (key, chord or hold actions outside the 33 certified
  keysyms). On the base, episodes exposed: 4B/H-GA 24 of 128 (31 actions), 4B/H-OSW-fixed 20
  (34), 9B/H-GA 24 (43), 9B/H-OSW-fixed 22 (29). 18 base tasks have an exposed episode and 14
  have none. δ by stratum (descriptive): exposed −4.86 pp, unexposed −0.89 pp.
- **Host.** While each A1 job ran, the lane's 26 snapshots per job show no foreign Slurm job; the
  highest one-minute load average was 15.5.

Per-cell, per-session and per-attempt tables: `report-guarded.json` (`cells`,
`cells_by_size_session`, `cells_by_size_harness_session`, `attempts`). Per-episode counts:
`s15.json` (`restarts_per_episode`, `observations_per_episode`, `losses_by_task`).

## Cost card (section 9 item 10) and DR4

| | GPU-h per episode | of central 0.009020 | of high 0.011274 | VM-h per episode |
|---|---:|---:|---:|---:|
| A1-9B-S1 | 0.002700 (H-OSW-fixed 0.002754, H-GA 0.002645) | 0.30 | 0.24 | 0.0517 |
| A1-4B-S1 | 0.002537 (0.002538, 0.002537) | 0.28 | 0.23 | 0.0483 |
| A1-9B-S2 | 0.002702 (0.002730, 0.002673) | 0.30 | 0.24 | 0.0514 |
| A1-4B-S2 | 0.002497 (0.002484, 0.002509) | 0.28 | 0.22 | 0.0478 |
| 9B pooled (904 episodes) | 0.002701 | 0.30 | 0.24 | 0.0515 |
| 4B pooled (904 episodes) | 0.002517 | 0.28 | 0.22 | 0.0481 |

GPU-h per episode is the GPU job's Slurm elapsed time (`scontrol` EndTime minus StartTime,
engine start-up included) over the episodes that ran to an end, all four at V = 20. The total is
about 90.0 VM-h, against the registered central 92 and high 115. Steps on the base, mean per
episode: 4B/H-GA 12.41, 4B/H-OSW-fixed 12.27, 9B/H-GA 11.77, 9B/H-OSW-fixed 11.81. Episodes
ending at the 15-step cap without `terminate`: 72, 75, 57 and 65 of 128. Output tokens per
episode, mean over each job's 452 episodes: 9B 4,393 (S1) and 4,359 (S2); 4B 4,862 and 4,715.
That is 362-386 per step. The step-of-termination and step-of-success distributions censored at
15 are in `s15.json` (`steps`, `output_tokens`, `cost_card_prices`). DR4 does not fire: no job
exceeds the high price. This card replaces the synthetic 431.5 GPU-h projection's per-episode
price for this profile, under these settings, on this host.

## Truncation (section 15)

The share of steps that ended at 2,048 tokens without a complete tool call is the registered
definition, read on all final records. It was 4B/H-GA 0.44%, 4B/H-OSW-fixed 0.42%, 9B/H-GA
0.17% and 9B/H-OSW-fixed 0.33%. The share of steps that hit the cap at all was 0.45%, 0.42%,
0.17% and 0.33%. Both sizes are far below the 20% label line, so **neither size's δ is labelled
truncation-confounded**. As a description, the base-only shares are 0.50%, 0.64%, 0.27% and
0.53%.

## Offline rescoring, checker corrections and checker noise (sections 8, 9 item 11)

- **Coverage.** Every scored episode has a capture and a rescoring row: 452 of 452 per job, with
  `exit_status` 0, in 3 h 08-3 h 12 per job at `--time=08:00:00`. 17 rows carry an offline error.
  Sixteen are all of extension task `53ad5833` (block 10, 4 per job), whose checker needs live
  state (`LiveStateRequired: setup_controller._activate_window_setup`). One is the base
  metric-exception episode (`fba2c100`, A1-4B-S1): its offline replay raised
  `UnidentifiedImageError` on the same image the live metric failed to read.
- **Corrected verdicts.** Primary: all 512 base verdicts have a corrected score. 511 come from
  offline rescoring. The metric-exception episode gets 0 by the registered merge rule (a metric
  exception scores 0), so no base verdict fell back to the live score. Secondary: 1,792 from
  rescoring and **16 fell back to live scores** (`53ad5833`).
- **Flips: 0.** The corrected comparator applied to 72 episodes per job (`compare_pptx_files`
  tasks) and changed no verdict on the base or the secondary set. Live versus offline raw replay
  mismatches: **0** on every record replayed. The checker-correction split, with replay
  mismatches beside the flips, is in `rescore-coverage.json`. Kevin's adjudication of the
  checker defects is still pending (D9), so corrected verdicts stay secondary in any case.
- **Checker-input-hash discordance.** 280 discordant rerun pairs, read over every scored final
  record on base and extension tasks (`s15.json` `checker_noise_set`). None has identical
  checker-input hashes.
- **First divergence** (base, scored final records, final attempt; 512 step logs read, 0
  missing). Between-session pairs: 512 of 512 part at step 1 as "environment". Within-session
  pairs: 255 at step 1 as "environment" and 1 (9B) at step 2 as "serving". As registered, this
  is descriptive: the guest's top-bar clock appears on every screenshot.

## Per domain (descriptive, base, raw; corrected identical)

| Domain | Tasks | Success 4B (OSW / GA) | Success 9B (OSW / GA) | δ, pp |
|---|---:|---|---|---:|
| gimp | 2 | 62.5% / 25.0% | 62.5% / 12.5% | −43.75 |
| libreoffice_calc | 8 | 15.6% / 15.6% | 25.0% / 21.9% | −1.56 |
| libreoffice_impress | 7 | 57.1% / 64.3% | 57.1% / 53.6% | +1.79 |
| libreoffice_writer | 3 | 41.7% / 41.7% | 41.7% / 50.0% | +4.17 |
| multi_apps | 7 | 3.6% / 0.0% | 0.0% / 0.0% | −1.79 |
| thunderbird | 2 | 62.5% / 50.0% | 100% / 100% | −6.25 |
| vlc | 2 | 0% / 0% | 0% / 0% | 0.00 |
| vs_code | 1 | 0% / 0% | 0% / 0% | 0.00 |

Two to eight tasks per domain: these are descriptions, not estimates. The secondary per-domain
tables are in `s15.json` `per_domain`.

## Deviations and disclosures

1. **Deviation (D59 (i)).** The report ran through `run_report.py`. It imports the frozen modules
   unchanged and widens `estimators._check` to accept outcomes in [0, 1] and NaN. The base holds
   14 fractional scores, so the registered CLI raised (`ValueError: outcomes must be 0, 1 or
   NaN`), as the dry run predicted (bug B1). The identity check ran the registered CLI on the
   same records with those scores set to 0. Its report differs from the wrapper's only in
   `fractional_score` and the `fractional_scores` counts (`identity.json`: PASS, mode
   `fractional`). No estimand, rule or decision depends on the widening.
2. **D59 (ii), D61, D62: not triggered.** The data are complete, the guard changed no reading
   (`guard.json` `readings` is empty), and `report-guarded.json` is `report.json` plus the guard
   block.
3. **Operator steps (D59 (iii)), each disclosed with its command** in
   `../q2-stage1-analysis/README.md`. Offline rescoring ran as one CPU job per A1 job with
   `--time=08:00:00`, and its coverage and fallbacks are given above. Replay mismatches are shown
   beside the flips (0 and 0). First divergence used base tasks, scored final records and the
   final attempt. The section 15 assembler (`s15.json`) supplied output tokens, the censored
   step distributions, restarts per episode, losses by task, the cost card against the central
   price, the exclusions, setup and postconfig failures by type, host snapshots, DR0 per job and
   the secondary set under corrected verdicts. The GLMM input was written with
   `glmm.rows_from_records` and `write_csv`; the primary fit is the registered reading, and exit
   codes (0, 0) and the R package digest were checked. The truncation label was read on all
   final records (the registered definition), with the base-only share shown as a description.
   The checker-noise set is stated above.
4. **Verification of the session-2 per-job checks.** The per-job evidence README lists "an
   independent verification of the session-2 per-job checks" as the next step, and no such
   record existed when this analysis started. Here the registered `rules dr0` re-ran on all four
   run directories, and its outputs are byte-identical to the per-job `pair/dr0.json` files. The
   guard recomputed DR0 from the records, and `provenance.py` checked the registration, the
   frozen plan and the 75 code-of-record files (PASS). The session-2 jobs' other lane checks
   (provenance, engine argv, Slurm limit) were not re-verified by a second person.
5. **The runbook's independent verifier (its step 12) has not run.** As a self-check on the Mac,
   the registered merge reproduced all four merged files and `a1.jsonl` byte for byte from the
   committed files, and `run_report.py` reproduced `report.json` and `report-guarded.json` byte
   for byte (numpy 2.5.2 against the host's 1.21.5). This is not the independent verification.
6. **Host activity during the analysis.** One job of other work, 1070 (a C3 gauntlet reviewer job
   from another workflow), was in the queue at one poll during the rescoring (about 15:58 UTC).
   The quiet-host rule covers the A1 jobs, which had all ended. The analysis outputs do not
   depend on host load: they are deterministic, and the report reproduced byte for byte off the
   host. The GLMM job (1074) ran with no other job in the queue at its submission or at any poll.
7. **Ops commit.** The operator scripts ran from `6d85529`: the last commit to touch
   `ops/s1a-analysis/`, carrying the fix for the final D59 verification's one blocking item.
   Their 71 tests pass at the current branch head. Before the analysis, `main` (D63, D64) was
   merged into `ops/q2-s1a`. The conflicts in `program/log.md` and `program/state.json` were
   resolved by keeping both sides, and the program total became 9.746 GPU-h (the ledger sum).
   This is repository housekeeping, not a deviation.
8. **Evidence location.** The runbook puts the analysis evidence in
   `program/evidence/2026-10-10/q2-stage1-analysis/`, where it is. This RESULTS file sits beside
   the per-job evidence, as the analysis assignment specified.
9. **No job was rerun or resubmitted**, and no frozen file was changed (`git diff d5f5798 --
   harness/ scripts/ infra/ experiments/` is empty). No registered stop condition fired:
   provenance passed, the report and identity check exited 0, and the GLMM collector found the
   registered package lock.

**Deviations from the registration:** D59 (i)'s wrapper only (item 1).

## What the result licenses

For these two serving sessions per size, this configuration (greedy decoding, T = 15, 2,048
output tokens with thinking passed back, the matched settle, V = 20 on vLLM v0.31.0, offline
VMs) and the 32 base tasks, all labelled "not externally anchored":

- The **rerun-noise floor** on the base. D_b = 11.3% (95% interval 5.9-17.2%; 4B 14.1%, 9B 8.6%)
  and D_w = 12.5%. There is no evidence of a positive between-session excess: the one-sided upper
  bound is 0.78 pp, so P1 is falsified. In the secondary set, 10.4% and 10.2%.
- **No detectable harness main effect.** δ = −3.1 pp, 90% t interval [−8.9, +2.7] pp. DR2
  classifies the pair **Inconclusive**: not Present, and not shown near-equivalent at ±7.5 pp.
- **DR5 INCONCLUSIVE.** π_small = 0.055 with one-sided 95% bounds [0.000, 0.260] around
  M = 0.13. Under D47, **S1b does not go to the gauntlet**. The registered pointer after
  INCONCLUSIVE is more sessions at 4B and 9B, as a new proposal.
- **4B is not at the floor**: 28.9% and 26.6% pooled success, so P4 stands and DR1 keeps 4B.
- **The first real cost card** for the certified pair at these settings: 0.0025-0.0027 GPU-h and
  0.048-0.052 VM-h per episode, 22-24% of the card's high price. DR4 does not fire.
- **The infrastructure held**: 0 losses, 0 restarts and 0 slow, retried or undelivered
  observations in 1,808 episodes, and 0 postconfig server errors.

## What it does not license

- Any claim about the population of sessions. Every interval resamples tasks with the two
  sessions per size held fixed (section 9).
- That the two harnesses are equivalent. DR2 is Inconclusive, not Near-equivalent.
- Any task-by-harness interaction claim. The X test does not reject (and an X rejection would
  support only "an effect is present"). The GLMM's registered fit did not converge, and its
  secondary-set test is not a decision input.
- Any claim about scale. 4B against 9B is a screen (δ difference +1.6 pp, π difference −0.056,
  MDE about 17 pp), and S1a makes no shrinkage claim.
- Anything about other harnesses, the observation factor (accessibility tree), step caps of 50 or
  100, sampled decoding (including H-GA's native sampling), larger models, the online setting or
  the tasks outside the offline-runnable web-free confirm subset.
- External validity of the runtime. There is no anchor, and nothing replaces the question file's
  Holo3 kill line (D55 (i)).
- Any reading of the 9B session shift (+5.5 pp, p = 0.016) beyond these two sessions. No rule
  reads it.
- Corrected verdicts as primary evidence. Kevin's adjudication is pending (D9), though here they
  equal the raw verdicts.

## Files

- `../q2-stage1-analysis/report/report-guarded.json` (SHA-256 `6bda751e...`): every estimand,
  test, rule, prediction, sensitivity and count.
- `../q2-stage1-analysis/s15.json` (`f09a8031...`): the section 15 items the CLI lacks, including
  DR3.
- `../q2-stage1-analysis/glmm-summary.json` and `glmm-out/glmm-{primary,secondary}.json`: the
  GLMM.
- `../q2-stage1-analysis/rescore-coverage.json`, `first-divergence.json`, `costs.json`,
  `identity/identity.json`, `provenance.json`; `../q2-stage1-analysis/README.md`: steps,
  commands and digests.
- `README.md` (this directory): the per-job evidence for O2 and the four A1 jobs.
