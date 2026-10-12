# q2-zinv-reserve-validation-v1: the registered run `reserve-v1` (R03 (b))

> **Blind warning (D9, D82).** `release/` names checker verdicts per mutant
> (`zinv-rows.json`, `judgement.json`, `campaign/outcomes.jsonl`, `campaign/verdicts-*.jsonl`).
> The parent's human spot check (D9) is still pending: if you are doing it, answer from its
> blind packets before reading these files
> (`program/evidence/2026-10-08/q2-mutation-confirm/results/README.md`, "Pending for Kevin").
> No reserve mutant is in the spot check or the adjudication pool. The same warning is a field
> of the rows, the judgement and the manifest, and is `release/BLIND-WARNING.txt`.

Registration: `program/preregistrations/q2-zinv-reserve-validation-v1.md`, frozen as ledger
row 20 (file SHA-256 `200f4caa...`, row hash `57cf8861...`, `git_head_at_freeze` `1bf7c8b9`).
The run used an export of the freeze commit `ff802ca5`, the commit that adds the row. It was
run under program authority (D80, D86). It is CPU only: 0 GPU-h, 0.221 lane-hours of the 4.0
cap.

## Registered outcome (section 6): **PASS, descriptive**

`rules.judge` gives exactly this: `outcome` **PASS**, `status` **descriptive**, `fail_reasons`
none.

| Quantity | Value |
|---|---|
| `n_Z`: evaluable `pptx.eq.zorder_nonoverlap` mutants labelled `should_pass_equiv` (condition A) | **13** |
| `t_Z`: tasks with at least one of them | **8** (all 8 registered reserve pptx tasks) |
| `accepted`: zinv scored a pass | **13 of 13** (condition A holds: 1300 >= 1235) |
| `n_V`: evaluable `should_fail_violation` mutants on the same tasks (condition B) | **15** on 5 tasks |
| Violation mutants with an original fail and a zinv pass | **0** (condition B holds) |
| Invalid rows (all 106 rows) | **0** |
| Status | **descriptive**, because `n_Z` = 13 < 20 (`rules.MIN_MUTANTS`); `t_Z` = 8 meets `rules.MIN_TASKS` |

The registered size was not reached. The registration expected a mean `n_Z` of 19.5 and
P(at least 20) = 0.535. The frozen operators planned 13 z-order mutants on these 8 targets
(3, 2, 2, 1, 1, 1, 2, 1), and all 13 were evaluable.

Intervals and bounds (section 6, `harness/q2_mutation/stats.py`):

- Acceptance share: 1.000. Exact two-sided 95% interval: 0.753-1.000. **Exact one-sided 95%
  lower bound: 0.794.**
- Task level: 8 of 8 tasks had every z-order mutant accepted. Exact one-sided 95% lower bound:
  0.688.
- Task-equal share: 1.000 (task-cluster percentile bootstrap, 10,000 resamples, seed 42:
  1.000-1.000; 8 clusters).
- V, exact one-sided 95% upper bound of the new-accept rate: 0.181 per mutant (0 of 15), 0.451
  per task (0 of 5).

## What it licenses (section 7, `rules.LICENSES`)

PASS, descriptive. The licensed statement: "On the reserve split's 13 held-out z-order mutants
on 8 tasks, zinv accepted 13 and newly accepted none of 15 violation mutants." The exact
one-sided 95% lower bound on acceptance is 0.794 (0.688 at the task level). This licenses
saying that the correction held on documents it was not developed on, at this size.

It does **not** license "zinv accepts at least 95% of z-order equivalents" as a population
claim. A PASS bounds acceptance from below only. Further qualifications:

- The result is offline. The K2 VM check covered the confirm sample only, and step 3 recorded
  K2 "not drawn".
- It rests on the frozen operators' labels. No rater, model or person read a reserve mutant.
- "Held out" means unseen by zinv's development. The reserve decks come from the same OSWorld
  pool as the development decks.

The judgement's `license` field carries the registered text.

## Reported regardless of outcome (section 8)

- **Original comparator on Z.** `compare_pptx_files` failed **13 of 13** z-order mutants
  (task-equal share 1.000, bootstrap 1.000-1.000). This is a held-out replication of the
  defect, and it is descriptive.
- **Per task.** All 13 original fails, all 13 accepted:

  | Task | z-order mutants | zinv accepted | original failed |
  |---|---:|---:|---:|
  | `05dd4c1d` | 3 | 3 | 3 |
  | `39be0d19` | 2 | 2 | 2 |
  | `7dbc52a6` | 2 | 2 | 2 |
  | `841b50aa` | 1 | 1 | 1 |
  | `8979838c` | 1 | 1 | 1 |
  | `986fc832` | 1 | 1 | 1 |
  | `c82632a4` | 2 | 2 | 2 |
  | `f23acfd2` | 1 | 1 | 1 |

- **Non-accepted z-order mutants:** none. **Newly accepted violation mutants:** none.
- **The 15 V mutants:** 9 `pptx.viol.delete_bound_shape`, 4 `pptx.viol.text_edit`, 1
  `pptx.viol.drop_char_format`, and 1 `pptx.alt.textbox_for_placeholder` labelled
  `should_fail_violation`. The original failed all 15, and so did zinv.
- **Every other item** (93 rows: 47 other equivalence mutants, 14 extra-change mutants, 15 V
  mutants, 8 saved golds and 9 saved do-nothing states from `reserve-controls-v1`):
  - zinv's verdict equals the registered one on 93 of 93;
  - no extra-change mutant was newly accepted;
  - no pass became a fail;
  - zinv raised no scoring error;
  - no z-order mutant had a label other than `should_pass_equiv`.
- **Validity.**
  - The fresh original scoring reproduced the registered verdict on all 106 rows.
  - Every job's file digest was unchanged between before and after both scorings.
  - No scoring hit the 300 s timeout (longest 11.4 s).
- **Step 1** (`release/targets-selection.json`): of the split's 28 targets (12 xlsx, 8 pptx,
  5 docx, 3 text), the 8 registered pptx targets on the 8 registered tasks were kept. The
  other 20 were never built.
- **Step 2** (`campaign/build-summary.json`, `campaign/reachability-summary.json`):
  - 116 mutants were planned, applied and admitted, with 0 duplicates and 124 scoring jobs.
  - Labels: 60 `should_pass_equiv`, 15 `should_fail_violation`, 14
    `should_fail_extra_change`, 27 ambiguous.
  - 124 of 124 saves were written, with no dialog and no infrastructure error.
- **Step 3** (`campaign/report.json`, `campaign/recheck-summary.json`):
  - Under both venvs: 89 evaluable, 27 ambiguous, with no venv disagreement.
  - S3 recheck: 116 of 116 admitted after the save.
  - S7: every one of the 8 null mutants passes under both venvs (no null failure).
  - S5: none unstable at repeat 5. No infrastructure failure or nondeterminism.
  - K2 recorded "not drawn" (one domain).
  - Its checker-error tables for these 8 targets are **exploratory**. They are not part of the
    parent's P2-P5.

## The run

From an export of `ff802ca5` staged with `git archive ff802ca5 | ssh host tar -x` at
`/home/kevin/cotcodec-runs/stage0/q2-zinv-reserve/src/ff802ca5.../` with `.git_sha`.

- **Export check.** Before any job, this session checked the staged tree against the commit.
  Its 7,640 regular files have the same git blob ids as `git ls-tree -r ff802ca5`, and there
  is no AppleDouble file. The only additions are `.git_sha` and the `__pycache__` that the
  host's Python wrote when it ran `plan`, as in the dev rehearsal.
- **Plan.** `zr_host.py plan --src SRC --name reserve-v1 --split reserve` ran with
  `Q2ZR_PREREG_FROZEN=q2-zinv-reserve-validation-v1` at 2026-10-12T01:35:50Z. An earlier
  session of this operator ran it, and was restarted before submitting any step. This session
  found the plan with all four steps pending and no job id, verified it, and continued it with
  `next`. Nothing was planned twice.
- **Steps.** `next --dry-run` rendered step 1, with this addendum's guard admitting the reserve
  split on the host and nothing submitted. Each step was then
  submitted by `zr_host.py next` with the whole Slurm queue empty, one at a time, through the
  parent's unchanged CPU lane. Every job had exit status 0, network none, `gpus_requested` 0,
  and the images of section 3. No step failed, no step was rerun and no `.a2` attempt exists.

| Step | Slurm | Image | Start-finish (UTC) | Exit |
|---|---:|---|---|---:|
| 1 `targets` | 1226 | metric `2006c1a9...` | 07:15:02-07:15:04 | 0 |
| 2 `build` | 1227 | LO-VM `f5b4c40e...` | 07:15:09-07:16:48 | 0 |
| 3 `score` | 1228 | metric `2006c1a9...` | 07:16:50-07:22:37 | 0 |
| 4 `zinv` | 1229 | metric `2006c1a9...` | 07:22:39-07:28:26 | 0 |

- **Guards.** In every step this addendum's guard admitted the reserve split against ledger
  row hash `57cf8861...`, and the parent's `campaign guard` verified the following:
  - 447 file-cache files;
  - OSWorld tree `4153c686...`;
  - VM baseline `f3253818...`.
- **Rescoring.** Step 4 rescored 106 items: 89 mutants, 8 golds and 9 do-nothing states. The
  pinned `reserve-controls-v1` files matched their digests. Comparator SHA-256: `64899d50...`,
  unchanged.
- **Local recomputation.** On the Mac, `rules.judge` re-read from `release/zinv-rows.json`
  gives the same outcome, status, conditions, intervals and bounds as the host's
  `judgement.json`. The only difference is in the last digit of one float.
- **Scheduling (D86).** The run was submitted only in a gap of successor E. When this session
  began (04:26Z), E's session E1 was due: its 9B pair was waiting for an empty queue. This
  session waited, submitting nothing, through the whole E1 session:
  - 9B pair: jobs 1219 and 1221, 04:28:39-05:08:34Z;
  - 4B pair: jobs 1222 and 1224, 05:09:55-05:46:36Z;
  - then R04 job 1225 until about 07:15Z.

  E2 cannot start before 12 h 5 min after E1's later end, that is not before about 17:51Z.
  That is more than the four steps' combined limits (4 h) after step 1's submission. No E job
  was queued or running while any step ran.

## Files

`release/` is exactly what `zr_host.py export --name reserve-v1` wrote on the host: 23 files.
They were copied with `ssh host tar -c | tar -x`, and each local file's SHA-256 equals the
host's. `release/manifest.json` (SHA-256 `a02415be...`) lists every other file's digest and
carries the outcome, the status, the frozen ledger hash and the blind warning.

| File | What | SHA-256 |
|---|---|---|
| `release/judgement.json` | `rules.judge` on the rows: outcome, status, conditions, bounds, license, warning | `19eaeaf4...` |
| `release/zinv-rows.json` | 106 rows: ids, labels, operators, scores (stored, fresh original, zinv), file digests, errors cut to 80 characters | `90f1b8cf...` |
| `release/targets-selection.json` | Step 1's selection (8 of 28 targets) | `0a158e8c...` |
| `release/plan.json` | The host plan with every step's command, job and times | `4e25bf6c...` |
| `release/receipts/` | The lane receipts of jobs 1226-1229 (the only attempts) | in the manifest |
| `release/campaign/` | The parent's own `campaign export` of the run in its layout: redacted recipes, outcomes, verdict rows, summaries, receipts, its manifest. `targets.json` is the parent's report on all 28 reserve targets, of which step 1 kept 8 | in the manifest |
| `release/BLIND-WARNING.txt` | The blind warning | `36d0d7a1...` |

The step logs stay on the host under `/home/kevin/cotcodec-runs/stage0/q2-zinv-reserve/slurm/`.
They hold checker messages on third-party documents, and section 10 releases them only for an
unfinished run.

| Log | SHA-256 |
|---|---|
| `slurm-q2zr-reserve-v1-targets-1226.out` | `f8e09a9701986ed7d6c0f1c725475c6ef318a11743b2611679d137e582cc9e5f` |
| `slurm-q2zr-reserve-v1-build-1227.out` | `09c5133807a3969acab6c272057a7ab88db60d281d50013a68c7e2b92c5eff36` |
| `slurm-q2zr-reserve-v1-score-1228.out` | `f5630214e8c3c04d421bfd975335c627e2e2a487d43c261eae0aa8146e04b472` |
| `slurm-q2zr-reserve-v1-zinv-1229.out` | `23184ab08a90a0b7fad2c43a927c4f8db3436e9069a642ba90e2d9cc9bc0692b` |

Mutant documents, recipes and saved files stay on the host (parent section 16). No outward
action.
