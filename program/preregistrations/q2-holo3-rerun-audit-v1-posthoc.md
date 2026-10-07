# q2-holo3-rerun-audit-v1-posthoc: Holo3 two-row diff, v1 (POST-HOC record)

**Status: POST-HOC.** This file records the v1 registration of the Holo3
two-row diff verbatim, so it has a place in the hash-chained ledger. It is not
a prospective preregistration and no claim based on it is confirmatory. The
only registration that can carry confirmatory claims for this question is
`q2-holo3-rerun-audit-v2`, which concerns data no one has read. Program
decision D10 (`program/decisions.md`) sets this labelling.

- **Experiment id:** `q2-holo3-rerun-audit-v1-posthoc`
- **Question (Q2 Stage 0c):** are the two OSWorld-Verified leaderboard rows for
  Holo3-35B-A3B (82.56 and 78.15) two exchangeable reruns, an infrastructure
  artefact, or an operator contrast?
- **Data:** Hugging Face dataset `xlangai/ubuntu_osworld_verified_trajs` at
  revision `5473c39e42a538a187a9b2c2b499db59d560fd8c` (MIT); OSWorld task
  configs at `c7e54d24d136d52be0c6d5a7487a1a32f99e7017` (Apache-2.0).
- **Code that reproduces it:** `scripts/run_holo3_rerun_audit_doctor.py --stage v1`
  with `harness/holo3_rerun_audit.py`. The original host script is not in the
  repository; its output is reproduced exactly (see Outcome).

## Disclosure (from the adversarial review, re-checked by this build)

1. **Frozen after the per-task data was on disk.** Host file birth times
   (`stat`, UTC, read 2026-10-07):

   | Event | Time (UTC) |
   |---|---|
   | run1, repair and run2 `status.json`/`result.txt` extracted (1,456 files) | 05:32:57 to 05:33:05 |
   | H Company runs' `task_summary.json`/`actions.json` extracted (2,157 files) | 05:38:08 to 05:44:03 |
   | v1 registration file written (`prereg_holo3_diff_v1.txt`, mode 444) | 05:44:54 |
   | `prereg_frozen_at.txt` written (mode 664, self-attested) | 05:44:55 |
   | analysis script created | 05:46:20 |
   | analysis output written | 05:47:51 |

   The run1 and run2 per-task files were on disk 11 min 49 s before the
   registration, and the last H Company file 51 s before it. That no per-task
   pairing was computed before the freeze is self-attested only. (The review
   quoted 05:42:06 for the last extracted file; the host's birth times show
   05:44:03. The conclusion is the same.)
2. **Outside the ledger.** The registration was not entered in
   `program/preregistrations/ledger.jsonl` when it was written. The ledger
   cannot backdate, so this record enters it with the date of its own freeze.
3. **The deciding test was nearly fixed by known totals.** The registration
   lists the run totals and per-domain sums as already seen. They fix a net of
   about 16 binary flips between run1 and run2 on the 359 common tasks. With a
   net of 16, exact two-sided McNemar is below 0.05 at every discordant count
   up to 58 (16.2% of 359). On the 342 clean tasks the realised net was 14,
   which gives p below 0.05 up to 44 discordant tasks (12.9%). Every rerun
   pair measured since, within one operator, has a discordance rate between
   7.5% and 16.8%. R3 was therefore largely foreseeable. The new,
   decision-bearing information was R1, the infrastructure share.

## Required reading of the outcome, fixed before v2

- R3 here means **task-level non-exchangeable reruns (a session shift is
  present)**. It does not mean an operator contrast: both rows are maintainer
  runs of the same agent, from the same package, on the same day and region.
- The Q2 kill criterion ("if the Holo3 diff traces the 4.4 pp gap mostly to
  infrastructure or operator differences, do not use the pair as a noise
  anchor") **does not fire**: the infrastructure share is 12.6% and the
  operator is the same.
- The pair is one observation of between-session spread for a remotely served
  agent. It is not a task-level exchangeable rerun reference.

## Metrics, rules, seeds and sample size (as registered)

The verbatim text below is the registration. In the README's terms:

- **Unit:** task. Universe: the 361 tasks of `test_nogdrive.json`; common
  scored set 359; clean set (common minus infrastructure-flagged) 342.
- **Primary metric:** exact two-sided McNemar on y = 1[score >= 0.5], alpha
  0.05; sensitivity binarisations 1[s > 0] and 1[s == 1]; companion 1e6-draw
  sign-flip test.
- **Decision rules:** R1, R2, R3 and inconclusive, with the thresholds below.
- **Seeds:** the Monte Carlo seed is 42 (one generator shared by both sign-flip
  tests and the H-only model, in that order). This build also reports seeds
  43 and 44 as Monte Carlo sensitivity; they do not change any decision.
- **Minimum detectable effect:** not stated in v1. Computed afterwards from the
  H Company rerun discordance (q = 0.0993): 4.66 pp for a single two-run
  contrast on 359 tasks (80% power, two-sided alpha 0.05).
- **Infrastructure failures:** flags F1 to F6 below. A task flagged in either
  run leaves the clean set; errored tasks (F1) leave the common set, as the
  runner's own denominator does.
- **Reported regardless of outcome:** every quantity v1 printed, in
  `program/evidence/2026-10-06/holo3/`.

## Outcome as executed (reproduced by this build)

Not R1 (infrastructure share 12.6%); R3 fires (clean McNemar 23 vs 9,
p = 0.0201; common set 25 vs 9, p = 0.0090). The doctor reproduces all 51
exact quantities v1 printed and its three Monte Carlo p-values digit for digit
(`program/evidence/2026-10-06/holo3/results-v1-posthoc.md`).

## Original artefacts on the host (not in the repository)

| Artefact | SHA-256 |
|---|---|
| `prereg_holo3_diff_v1.txt` (the text below) | `e9a947a303600b091f60ef3781f40dfcb52b91417b380ddcde26e01be9450b97` |
| `analyze.py` | `e07687ae400f47c7be24b9078df1689ee9e88da9f1f7b8967a85e8f285d9b367` |
| `analysis/run_output.txt` | `a24e15906b5d588cfa15599137bceff31de0ee27f5034b3f8c09c1699b4eb83c` |
| `analysis/per_task_matrix.csv` | `91b3441f28e100c141fe0c0c16b1723db2a0a21843e5d1ea6414de451e3763a5` |

They live under the host's Stage 0 scratch directory
(`~/cotcodec-runs/stage0/holo3/`).

## Verbatim v1 registration

The bytes between the fences, with the final newline, hash to
`e9a947a303600b091f60ef3781f40dfcb52b91417b380ddcde26e01be9450b97`
(`tests/test_holo3_preregistrations.py` checks this).

```text
Q2 Stage 0c -- Holo3-35B-A3B OSWorld-Verified two-row diff. PREREGISTRATION v1.
Frozen before any per-task concordance between runs was computed.
Already seen at freeze time: leaderboard totals and per-domain sums for both rows; run-level summary
JSONs (scored/passed/errors/score); status.json schema; one task's actions.json; internal-run READMEs.
NOT seen: any per-task pairing of outcomes across runs.

DATA (HF dataset xlangai/ubuntu_osworld_verified_trajs @ 5473c39e42a538a187a9b2c2b499db59d560fd8c)
  V1 = local_results/results_hcompany_verified_run1_20260420_121655 merged with
       results_hcompany_verified_run1_repair_20260420_183538 (leaderboard row 82.56, 296.41/359)
  V2 = local_results/results_hcompany_verified_run2_20260420_191308 (leaderboard row 78.15, 280.55/359)
  H1,H2,H3 = h_company_internal_runs/trajectories_results_20260416_{072452,072955,073458} task_summary.json
  Task universe: evaluation_examples/test_nogdrive.json (361 tasks).

OUTCOMES
  s_ir = OSWorld evaluator score in [0,1] for task i, run r (status.json "score" / task_summary "reward").
  Primary binary y_ir = 1[s_ir >= 0.5]. Sensitivity: 1[s>0] (runner "passed"), 1[s==1].
  Inclusion set C = tasks with a completed score in both V1 and V2.

PRIMARY TEST (exchangeability of V1 and V2)
  Exact two-sided McNemar (binomial on discordant pairs, p=0.5) on y over C.
  Companion: exact/Monte-Carlo (1e6 draws, seed 42) paired sign-flip test on d_i = s_iV1 - s_iV2 over C.
  Alpha 0.05.

REFERENCE NOISE (within-operator reruns)
  For each pair among H1,H2,H3 on common completed tasks: discordance rate k/n and net gap.
  Pool: q_H = mean pairwise discordance rate. Expected SD of a two-run gap under exchangeability
  = sqrt(q_H * n)/n. Report V1-V2 gap in those SD units.
  Five-run per-task model: p_i from H1..H3 only (Beta(0.5,0.5) posterior mean), simulate 1e5 pairs of
  independent reruns on C, two-sided tail prob of |gap| >= observed.

INFRASTRUCTURE FLAGS (per task, per run) -- task is infra-flagged in a pair if flagged in either run
  F1 status=="error" or missing status (excluded from runner denominator).
  F2 env-prep retry logged for the task ("Env prep failed" with that task's 8-char id prefix).
  F3 AGP outcome "Failed: ..." (agent-platform failure scored as FAIL).
  F4 elapsed_s >= 10000 (near AGP 3 h timeout) or elapsed_s < 20 with score 0.
  F5 (H runs only) .err file or actions.json with zero action entries.
  F6 task repaired (V1 repair pass).
  Web-dependent tasks: config "config"/"evaluator" referencing http(s) URLs other than localhost or
  huggingface file cache -> reported as a stratum, not an infra flag.

DECOMPOSITION OF THE GAP
  Delta = sum_i (s_iV1 - s_iV2) over the 361-task universe with the runner's own denominators,
  split into: (a) inclusion/denominator effects (F1, F6), (b) infra-flagged tasks in C (F2-F4),
  (c) web-dependent clean tasks, (d) offline clean tasks.

DECISION RULES
  R1 INFRA: if (a)+(b) account for >= 50% of the leaderboard gap (4.41 pp) -> "infrastructure-driven";
     do not use the pair as a noise anchor (Q2 kill criterion).
  R2 NOISE: if not R1 AND McNemar p >= 0.05 on clean tasks (C minus infra-flagged)
     AND V1-V2 clean discordance rate <= upper 95% Clopper-Pearson bound of the largest H-H pair rate
     AND no domain has Holm-adjusted exact McNemar p < 0.05
     AND paired elapsed_s Wilcoxon p >= 0.01 or |median ratio - 1| < 0.10
     -> "consistent with rerun noise"; pair usable as a noise anchor; report SD.
  R3 SYSTEMATIC: if not R1 AND (McNemar p < 0.05 on clean tasks OR V1-V2 discordance exceeds the bound
     above OR elapsed_s shift with Wilcoxon p < 0.01 and |median ratio - 1| >= 0.10)
     -> "systematic non-infrastructure difference (server-side/time-varying)"; not a noise anchor.
  Otherwise "inconclusive".
  Domain breakdown: exact McNemar per domain, Holm over 10 domains.
  Step counts: available for H runs from actions.json; for V1/V2 only after the 5.75 GB tarball is
  streamed (not in this phase); elapsed_s is the V1/V2 proxy.
```
