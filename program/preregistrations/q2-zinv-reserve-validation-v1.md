# q2-zinv-reserve-validation-v1: held-out test of the corrected z-order comparator on the reserve split

**Status: frozen in `program/preregistrations/ledger.jsonl`; see the ledger row for the
freeze time and `git_head_at_freeze`.** An addendum to `q2-evaluator-mutation-v1` for the
dossier's R03 (b), frozen under program authority (D80) after its pre-freeze audit
(section 13). The registered run (section 5) runs from an export of the freeze commit, the
commit that adds this file's ledger row; the guard admits the reserve split only while this
file's SHA-256 equals the row's and the staged code equals section 3's code table. A
material change after the freeze is a new experiment id. Nothing in this file is a result.

- Experiment id: `q2-zinv-reserve-validation-v1`, an addendum to `q2-evaluator-mutation-v1`
  (ledger row 11: file SHA-256
  `57dc009261244cbdda6dabae2144843a5094dd3e5c31e7810d59c2f70d16c8a5`, row hash
  `dc39bfa2f68e0fd5...`). It changes no rule of the parent and adds no file under
  `harness/q2_mutation/`, `infra/q2-mutation/` or `harness/q2_stage1/`.
- Origin: R03 part (b) of the question-renewal dossier
  (`program/evidence/2026-10-11/question-renewal/dossier.md`, entry 3 and owner check O4),
  which D73 made the spine and D80 and D82 unblocked.
- Route: a CPU-only validation that completes a frozen study (0 GPU-h, a cap of 4 lane-hours
  on the CPU lane). It is neither a new direction nor over 8 GPU-h, so the research gauntlet
  and D24 are not engaged. Research decisions are delegated (D80); the freeze is the
  orchestrator's, never this file's author's.

## 1. Question

The dossier's question, word for word: "Does `zinv` accept at least 95% of held-out z-order
equivalence mutants on the reserve split while accepting no violation mutant the original
rejects?"

Background. The checker-mutation study found that `compare_pptx_files` zips two decks'
top-level shapes in document order, so swapping the stacking order of two shapes that cannot
paint the same pixel fails the checker (35 of 39 evaluable `pptx.eq.zorder_nonoverlap`
mutants on `compare_pptx_files`; D72 (iii); 33 confirmed false negatives in all after the
model adjudication, D82). S1a built the corrected comparator `compare_pptx_files_zinv`
(`harness/q2_stage1/zinv.py`) and validated it on the stored confirm campaign
(`q2-stage1-rescoped-v1` lines 321-351): the third run (job 1000) passed the 29 confirmed
z-order mutants and kept the original verdict on the 256 other items. Its first two runs
failed (0 of 29, then 26 of 29), and each fix came from the confirmed mutants that failed,
so, in that registration's words, "the 29 are a development set as much as a gate". A
held-out test needs mutants zinv's development never saw. The reserve split's pptx targets
are the only OSWorld pptx targets of the study with no mutant in existence.

What this test can and cannot show. zinv reorders a shape only past shapes that are apart by
the operator's own rule (`zorder_pair_is_inert`), so on a correct implementation every
operator-built z-order mutant whose deck is otherwise unchanged passes by construction. What
is untested is the implementation's pairing on documents it was not developed on (the
development fixes were for the 720 EMU save rounding, empty text runs and identical
pictures). Condition B tests that the realignment never hides a real violation. The test
reads the operator's labels; no rater or adjudicator reads a reserve mutant (section 9).

## 2. What the frozen parent says about the reserve split and zinv

Read from `program/preregistrations/q2-evaluator-mutation-v1.md` at `746d60d2` (line
numbers of that file):

- Line 191: the splits, `splits.json`, seed 42, stratified by domain x task class: dev 32,
  confirm 120, reserve 53. No line states a purpose for the reserve split or a rule for
  opening it beyond what follows.
- Lines 375-402 (P1): the reserve split's golds are used. P1 sums the confirm and the
  reserve control runs (92 golds, 67 confirm and 25 reserve; `--reserve-controls-summary`).
  Lines 1175-1176 audit every P1 flip of both control runs; lines 2223-2224 list "P1 as a
  replication that uses reserve-split golds" among Kevin's sign-offs.
- Line 514, the target table: reserve has 53 tasks, 28 with a target, 28 targets
  (12 xlsx / 8 pptx / 5 docx / 3 text), 21 without a complete gold, 7 with no operator
  family.
- Lines 576-579: adding the reserve split's 28 targets "would raise the expected P3 and P4
  sizes ... it is not part of this registration".
- Line 230, the pins block: `"mutation_split": "confirm"`. The parent's code does not enforce
  that pin: `campaign.require_split_allowed` and `check_frozen.py` admit any non-dev split once
  the parent is frozen, so the reserve mutation run is mechanically possible with the frozen
  code but registered nowhere.
- zinv: the parent never names it (it predates zinv). zinv is registered by
  `q2-stage1-rescoped-v1` (lines 321-351; file pin line 1932). R04
  (`r04-checker-nuisance-invariance-v1` lines 91-93) scores zinv on the reserve split's golds
  and states that those verdicts "are not used to change `zinv` before the dossier's R03 (b),
  its held-out test on the reserve split, has run" (also its line 743).

State of the reserve split on 2026-10-11:

- Opened for golds and do-nothing states only: the parent's reserve control run
  `reserve-controls-v1` (Slurm 791-793; summary
  `program/evidence/2026-10-08/q2-mutation-confirm/results/released/controls/reserve-controls-v1.summary.json`)
  saved and scored all 32 golds and 53 do-nothing states, and R04's registered run (in
  progress) re-saves and rescores the reserve golds, zinv included.
- No mutant of the frozen operators exists on the reserve split: the parent's host run root
  holds no reserve mutation run (listing of 2026-10-11: its only reserve run is
  `reserve-controls-v1`; its mutation runs are `confirm-mutants-v1` and `dev-mutants-v1` to
  `-v9`), and no released file names one.
- Two earlier uses touched the 8 registered tasks, neither with zinv nor with a frozen
  operator: the pre-registration scoping probe
  (`program/evidence/q2-mutation/harness/probe_touched.json`) built probe edits on all 8
  (E-META, E-ZIP, F-TYPO, F-TYPO-BODY or F-TYPO-TABLE, E-RUNSPLIT; none a z-order edit),
  and the S2 v3 locale pilot saved and scored their golds and do-nothing states with the
  original comparator under six locale conditions (96 verdicts;
  `program/proposals/evidence/2026-10-11-s2v3-arabic-cua-locale-pilot/compute/pilot-r1/goldscore-1141`).
  Neither touches zinv's held-out status.

Conclusion: a reserve-split zinv evaluation is not registered (no rule, inputs or code), so
this addendum registers it. Running it needs: the reserve pptx mutants built with the frozen
operators (section 5, steps 1-3), the zinv rescoring (step 4), this file's freeze, and four
CPU jobs on an empty queue.

## 3. Identity and pins

| Object | Pin |
|---|---|
| Parent | `q2-evaluator-mutation-v1`, ledger row 11 (above). Its pins block is unchanged; the guard checks its code tree `58bee0190c0c7eb5d44f36e27c0f1e0daab82c1c48716009a9066777c69a0721` (operators, catalog sources, save stage, scorer, the CPU lane `infra/slurm/host-single-node/q2-mutation-cpu.sbatch`), and the parent's own `campaign guard` checks the catalog `3a5ff94953f7b672059b0f6b063064b97a438de166fd664903e239a12f65b46f`, specs `05d4fb2074a7fa53046dff9f5d075b2b45ac014889eaae23d625c1894056de62`, splits `2099792e6fb86c69e4f79b1ce47d2839cc25623f5c4633698e95822553c007d9`, the mounted OSWorld tree `4153c68678fedd44a285800b45f4b7e538336a044f614f748f432a7ce5246076`, VM baseline and file cache in steps 1, 3 and 4 |
| Operators and seeds | the frozen catalog `q2-mut-operators-v1` (64 operators); planning is deterministic per (task, operator) cell: candidate sites ordered by a hash of (task, operator), at most three kept, seeds 42, 43, 44 (`operators/_base.py`); recipes applied to the raw gold (`--apply-to gold`, the parent's pin). Filtering the target list does not change any pptx plan: each target is planned on its own |
| Images | metric `sha256:2006c1a9247e4911a82508cd22e9d9a7efc5c13e35a20e8a03baac7112876230` (lock-exact venv `/opt/venv-lock`); LO-VM `sha256:f5b4c40eefd2b92f846652910ba34db35e1ae7bf90fa474595cc745cc5895361`; both read from the parent's pins block by the host tool |
| Comparators | original: OSWorld `b138d348` `desktop_env.evaluators.metrics.slides.compare_pptx_files` (inside the pinned OSWorld tree); corrected: `harness/q2_stage1/zinv.py`, SHA-256 `64899d5056f4791008c2a10c38a7b0fbb94fbe912d20a702ec74851a0ca7f655`, unchanged since commit `1b18ba37` (the validated job 1000) |
| Reserve control run (golds and do-nothing states) | the host's `q2-evaluator-mutation/runs/reserve-controls-v1/saved/jobs-saved-mounted.jsonl`, SHA-256 `595f31c3ac3ec4eb06dacb0855ec3fad868943a75023d4866c7a60eb23dcee7f` (85 rows), and `saved-verdicts-lock.jsonl`, SHA-256 `a9dea13f32917e4f0d6f5c06904b18d03ceb7daaf0ad988b43cb3c7117723159` (85 rows); summary SHA-256 `1da426424339678c35847380f63ba9bae9983cc4a88beaed19171b118c55bb9b`. The host tool and `run rescore` refuse other bytes |
| Registered targets | the reserve split's 8 pptx targets, one per task, every task checked by `compare_pptx_files` alone (counted from task configs before this draft, `program/evidence/q2-mutation/integration/prefreeze-counts-v2/counts.json`): `05dd4c1d-c489-4c85-8389-a7836c4f0567`, `39be0d19-634d-4475-8768-09c130f5425d`, `7dbc52a6-11e0-4c9a-a2cb-1e36cfda80d8`, `841b50aa-df53-47bd-a73a-22d3a9f73160`, `8979838c-54a5-4454-a2b8-3d135a1a5c8f`, `986fc832-6af2-417c-8845-9272b3a1528b`, `c82632a4-56b6-4db4-9dd1-3820ee3388e4`, `f23acfd2-c485-4b7c-a1e7-d4303ddfe864` |
| Host run root | `/home/kevin/cotcodec-runs/stage0/q2-zinv-reserve` (staged exports under `src/`, runs under `runs/`); inputs are the parent's `q2-evaluator-mutation/inputs`, mounted read-only |

Reused code, unchanged and pinned elsewhere (SHA-256 on main at `746d60d2`):

| File | SHA-256 | Pinned by |
|---|---|---|
| `harness/q2_stage1/zinv.py` | `64899d5056f4791008c2a10c38a7b0fbb94fbe912d20a702ec74851a0ca7f655` | `q2-stage1-rescoped-v1` section 20 |
| `harness/q2_stage1/rescore.py` | `d240db03e969c8aa5bb97403c5005cd4c9e96016599a78f70e97850415893737` | `q2-stage1-rescoped-v1` section 20 |
| `harness/q2_stage1/__init__.py` | `0e2190149cf640fac07dab26332a26f696374ff4400c23aab82e8cf766f3b334` | `q2-stage1-rescoped-v1` section 20 |
| `harness/q2_mutation/` and the CPU lane | code tree `58bee0190c0c7eb5d44f36e27c0f1e0daab82c1c48716009a9066777c69a0721` | parent pins block |

New code of this addendum (SHA-256 of the committed bytes; refreshed before the freeze with
`python -m harness.q2_zinv_reserve.guard code-table --write`; the guard refuses a staged tree
whose files differ, and `tests/test_q2_zinv_reserve.py` fails on drift):

<!-- q2zr-code-table start -->
| File | SHA-256 |
|---|---|
| `harness/q2_zinv_reserve/__init__.py` | `ea19139fbe29b88d9e46f7fe337bab7bf6d1f9e21ac1905f455cc29b2a1d95e2` |
| `harness/q2_zinv_reserve/guard.py` | `a1bf674ed7fe3dc476142b65aabacf5db742b536645a11ae8ec3903e33e9fbf0` |
| `harness/q2_zinv_reserve/rules.py` | `36d9e5ee2f4b1ce102b51d49e41594ae99cf0e39a3b0f8aeafa2cb456b435e20` |
| `harness/q2_zinv_reserve/run.py` | `4e052c88344bb0323bf17899f1eaf3823af351bd0dfb40cab9131faeaeac2a6d` |
| `infra/q2-zinv-reserve/run/zr_host.py` | `09b5be4a145ebdee35ce446013d14d2564244f9ceb2122c8c8f004ecbe522cbc` |
<!-- q2zr-code-table end -->

## 4. Populations, expected size and what the sample can detect

Items (all scored under the lock-exact venv, the parent's primary):

- **Z (condition A).** Every mutant of `pptx.eq.zorder_nonoverlap` with label
  `should_pass_equiv` whose registered status (`campaign.classify`, lock-exact) is
  `evaluable`, on a reserve task whose every metric is `compare_pptx_files`. Its size is
  `n_Z` mutants on `t_Z` tasks.
- **V (condition B).** Every evaluable mutant with label `should_fail_violation`, of any
  operator, on the same tasks (probe-touched cells included: the question compares two
  comparators, not the checker's error rate).
- Probe-touched cells and Z: no `pptx.eq.zorder_nonoverlap` cell is probe-touched on the 8
  tasks (`campaign.is_probe_touched` is false for every one; the probe's cells there are
  document properties, extra changes and text-edit violations; checked by the tests), so Z
  needs no probe rule.
- **Reported only.** Every other evaluable mutant on those tasks (other equivalence,
  alternative-solution and extra-change mutants), and the saved gold and do-nothing state of
  every reserve task checked by `compare_pptx_files` alone (from `reserve-controls-v1`).

Expected size. All 8 reserve pptx golds pass `compare_pptx_files` raw and after the save
(the committed reserve control summary), so all 8 targets are expected to be evaluable. On
the confirm campaign the 16 evaluable `compare_pptx_files` targets yielded 3, 3, 3, 0, 3, 3,
3, 3, 2, 2, 3, 2, 3, 1, 2, 3 evaluable z-order mutants (39 on 15 tasks;
`rules.CONFIRM_ZORDER_YIELDS`, recomputed from the released outcomes by the tests). Drawing 8
targets from these yields (100,000 draws, seed 42; `rules.floor_probability`): mean `n_Z`
19.5 (at most 24); P(at least 20 mutants) 0.535; P(8 tasks) 0.596; P(both, the
registered-rule status of section 6) 0.465. V is expected near 34 mutants (confirm: 67 on
16 targets).

Detection (`rules.design_table`). Below 20 mutants condition A holds only with no rejection;
from 20 to 39 it allows one. If each z-order mutant is accepted with probability `p`:

| `n_Z` | P(A fails), independent mutants, p = 0.80 / 0.85 / 0.90 / 0.95 | P(A fails), tasks of 3 all-or-none | p with P(A fails) = 0.8, independent / tasks of 3 | Exact one-sided 95% lower bound if all accepted |
|---:|---|---|---|---:|
| 12 | 0.931 / 0.858 / 0.718 / 0.460 | 0.590 / 0.478 / 0.344 / 0.185 | 0.874 / 0.669 | 0.779 |
| 15 | 0.965 / 0.913 / 0.794 / 0.537 | 0.672 / 0.556 / 0.410 / 0.226 | 0.898 / 0.725 | 0.819 |
| 18 | 0.982 / 0.946 / 0.850 / 0.603 | 0.738 / 0.623 / 0.469 / 0.265 | 0.914 / 0.765 | 0.847 |
| 21 | 0.942 / 0.845 / 0.635 / 0.283 | 0.790 / 0.679 / 0.522 / 0.302 | 0.864 / 0.795 | 0.867 |
| 24 | 0.967 / 0.894 / 0.708 / 0.339 | 0.832 / 0.728 / 0.570 / 0.337 | 0.880 / 0.818 | 0.883 |

So the rule is a test for held-out counterexamples, not an estimate of a 95% rate: a true
acceptance of exactly 95% fails it about half the time, and even 24 of 24 accepted bounds
the acceptance only above 0.883 (0.861 at 20 of 20; at the task level, 8 of 8 tasks bound
it above 0.688). Condition B detects a per-mutant new-accept rate of 10.2% / 7.7% / 6.2% /
5.2% with probability 0.8 at `n_V` = 15 / 20 / 25 / 30; zero new accepts in 25 bound the
rate below 11.3% (exact, one-sided 95%).

Minimum detectable and the descriptive status (dossier O4): below 20 z-order mutants or 8
tasks the reading is **descriptive** (`rules.MIN_MUTANTS`, `rules.MIN_TASKS`). At about 15
mutants it detects, with probability 0.8, a true acceptance below about 0.90 if mutants are
independent and below about 0.73 if each task's mutants stand or fall together. A PASS there
licenses only the statement of section 7 with its lower bound.

## 5. Procedure

Four CPU-only Slurm jobs, each through the parent's lane `q2-mutation-cpu.sbatch` unchanged
(no GRES, the lane refuses a GPU; GPU-less, network-less containers with a read-only root,
no capabilities and the caller's uid:gid), each submitted by
`infra/q2-zinv-reserve/run/zr_host.py next` only when `squeue` shows no job at all and only
after the previous step's receipt reports exit status 0. Steps 1-3 are the three jobs of the
parent's frozen `infra/q2-mutation/run/submit_mutants.sh` (the commands the confirm run
used; the tests check the host tool's commands against that script), submitted one at a
time, with this addendum's guard first and one target filter added:

1. `targets` (metric image; 4 CPUs, 16 GB, limit 30 min): `guard check --split reserve`;
   the parent's job 1 (`campaign guard`, `make_jobs.sh reserve`, `campaign targets`); then
   `run select-targets --family pptx --split reserve`, which moves the full target list to
   `targets-all.jsonl` and keeps the pptx targets, reading only the target rows (no task
   config, checker or verdict). On the reserve split it refuses any selection other than the
   8 registered targets on the 8 registered tasks. The other 20 reserve targets are never
   built, so the reserve split stays unopened for them.
2. `build` (LO-VM image; 16 CPUs, 96 GB, limit 60 min): the parent's job 2 verbatim
   (`campaign build --apply-to gold` with the blind specs only, purity, deduplication, then
   the GUI-faithful save stage `reach.sh`).
3. `score` (metric image; 16 CPUs, 96 GB, limit 90 min): `guard check`; the parent's job 3
   verbatim (`campaign guard`, `k2-sample`, `merge`, `score.sh` under both venvs with two
   fresh-process scorings each, `dependency_flips`, `recheck`, `report`). `k2-sample` finds
   one domain and records "not drawn"; no VM check runs on reserve mutants (section 9).
4. `zinv` (metric image; 8 CPUs, 32 GB, limit 60 min): `guard check`; `campaign guard`;
   `run rescore --split reserve` over step 3's `jobs-saved.jsonl`, `mut-verdicts-lock.jsonl`
   and `outcomes.jsonl` and the pinned reserve control files; then `run judge`. The rescoring
   is S1a's validated procedure (`q2_stage1.rescore.validation_set` with no audit input, its
   worker `_job_worker` and `run_worker`, each item scored in a fresh process, 7 workers,
   timeout 300 s): the original, then zinv installed in OSWorld's `metrics` namespace. Each
   row keeps the registered verdict and a path-independent digest of the job's files (each
   VM path with the SHA-256 of its local file), taken before and again after both scorings.
   The parent's `scored_sha256` is recorded but never compared: it hashes the scorer's
   temporary path, so it differs between any two scorings of the same files (0 of 1,300
   lock-exact and scoping pairs are equal on the confirm run).

Commands, from an export of the freeze commit staged on the host as
`/home/kevin/cotcodec-runs/stage0/q2-zinv-reserve/src/` plus the freeze commit's id (with
`.git_sha`), with `Q2ZR_PREREG_FROZEN=q2-zinv-reserve-validation-v1` exported:

```bash
python3 SRC/infra/q2-zinv-reserve/run/zr_host.py plan --src SRC --name reserve-v1 --split reserve
python3 SRC/infra/q2-zinv-reserve/run/zr_host.py next --name reserve-v1   # repeat until "complete"
python3 SRC/infra/q2-zinv-reserve/run/zr_host.py status --name reserve-v1
python3 SRC/infra/q2-zinv-reserve/run/zr_host.py export --name reserve-v1 # the release view, section 10
```

Only the plan named `reserve-v1` is evidence. The host tool refuses any other reserve plan
name (`rules.RESERVE_PLAN`) and never plans an existing run root again; any other reserve
plan, run or rescoring, by any tool, is not evidence under this id.

Reruns and caps. A step that fails (exit status other than 0, or no receipt) is rerun once
in full in a fresh directory (`.a2`), and later steps read the attempt that finished; a
second failure ends the run (`failed_final`), and the outcome is INCOMPLETE. Invalid rows
are final: step 4 exits 0 once it has written its rows, whatever their validity, so an
invalid row triggers no rerun (section 6). No job is submitted once the lane hours used
(receipt start to finish) reach 4.0; a run that stops there (`cap_reached`) before step 4
has written its rows is INCOMPLETE (section 6). Projected wall time:
about 30 minutes in all (the confirm run's 68 targets took 12 minutes to build and save and
60 minutes to score 1,300 jobs; this run has 8 targets and about 170 jobs; job 1000 rescored
291 items in 15 minutes). GPU: 0.

Before the freeze only the dev split runs (rehearsal, exploratory, never evidence; section
11): `plan --split dev --controls-run dev-controls-v9`.

## 6. Decision rule

Computed by `harness/q2_zinv_reserve/rules.py` (`judge`) over the rescored rows; a pass is
`score >= 1.0`, as the parent's schema maps a score.

- **Condition A.** zinv passes at least 95% of Z: `accepted * 100 >= 95 * n_Z` (19 of 20
  holds; 14 of 15 does not). A zinv scoring that raises counts as not accepted.
- **Condition B.** No mutant of V has an original fail and a zinv pass.
- **Validity.** A row is invalid if either scoring hit the timeout, if the fresh original
  scoring's verdict differs from the registered verdict, or if the job's files changed or
  went missing between the digest taken before the two scorings and the one taken after.
- **Outcome.**
  - INCOMPLETE: a step ended `failed_final` after the one rerun of section 5 (no rows
    exist), the run stopped at the lane-hour cap (`cap_reached`) before step 4 wrote its
    rows, or any row of Z or V is invalid. Invalid rows are final (no rerun), and
    INCOMPLETE takes precedence over FAIL: a run with an invalid row in Z or V is INCOMPLETE
    even if a condition fails on its valid rows, and both conditions are still reported.
  - FAIL: B fails (whatever `n_Z`), or `n_Z` is at least 1 and A fails; the failed
    conditions are named.
  - NOT_TESTABLE: `n_Z` = 0 and B holds.
  - PASS: A and B hold and `n_V` is at least 1.
  - PASS_A_ONLY: A holds and `n_V` = 0 (B untested).
- **Status (dossier O4).** `descriptive` when `n_Z` < 20 or `t_Z` < 8; otherwise
  `registered_rule`.

Invalid rows outside Z and V are reported, not decisive.

Reported with the outcome: the acceptance share, its exact two-sided 95% interval, the exact
one-sided 95% lower bound, the task-level lower bound (tasks whose z-order mutants were all
accepted, exact), and the task-equal share with a task-cluster percentile bootstrap (10,000
resamples, seed 42; `harness/q2_mutation/stats.py`); for V, the exact one-sided 95% upper
bounds of the new-accept rate per mutant and per task.

Known-answer check: the same rule read on zinv's development data (the committed job-1000
rows, `program/evidence/2026-10-08/q2-stage1-g0/zinv/zinv-validation-v3.json`) gives PASS at
`registered_rule` status, 39 of 39 z-order mutants on 15 tasks and 0 of 67 violation mutants
newly accepted (`tests/test_q2_zinv_reserve.py`). That is the development split, not
evidence.

## 7. What each outcome licenses

- **PASS, descriptive.** "On the reserve split's `n_Z` held-out z-order mutants on `t_Z`
  tasks, zinv accepted `k` and newly accepted none of `n_V` violation mutants", with the
  lower bound. It licenses saying that the correction held on documents it was not
  developed on, at this size. It does not license "zinv accepts at least 95% of z-order
  equivalents" as a population claim.
- **PASS, registered rule.** The same, at the registered size; the population statement is
  the lower bound (at most about 0.88), not 95%.
- **FAIL (either status).** An existence result, informative at any size: a held-out
  z-order mutant zinv rejects beyond the allowance, or a violation mutant it newly accepts.
  The note then reports zinv as validated on its development split only, and lists each
  failing mutant id. S1a's corrected-score readings, which used zinv, are reported with that
  qualification. zinv is never changed under this id; a revised comparator would be a new
  file, and OSWorld holds no unseen pptx target left to test it on.
- **NOT_TESTABLE, INCOMPLETE.** Nothing is licensed; the cause is reported.

In every case the result is offline (the K2 VM check covered the confirm sample only) and
rests on the operator's labels (no rater read a reserve mutant). The judgement's `license`
field carries these texts (`rules.LICENSES`).

## 8. Reported regardless of outcome

- The outcome, status, both conditions with their populations, intervals and bounds, and the
  ids of every non-accepted z-order mutant and every newly accepted violation mutant.
- The original comparator on Z: how many it fails, with the task-equal share and its
  interval (a held-out replication of the defect, descriptive).
- Per task: z-order mutants, accepted, failed by the original.
- Every other item whose zinv verdict differs from the registered one, with its direction;
  extra-change mutants newly accepted; any pass that zinv turns into a fail; zinv scoring
  errors; z-order mutants with a label other than `should_pass_equiv`; invalid rows.
- Step 1's selection summary (`targets-selection.json`), step 2's build summary and step 3's
  report (counts per status, S3 recheck, S7 null failures). Step 3's exploratory checker-error
  tables for the reserve pptx targets are labelled exploratory; they are not part of the
  parent's P2-P5.

## 9. Interactions

- **R04.** Its reserve-gold zinv verdicts are not inputs here, and nothing in them changed
  zinv (R04 section 2.1); zinv's digest is checked in every step.
- **The adjudication (D80-D82).** No reserve item was audited or adjudicated, and this
  addendum adds no audit: the labels are the frozen operators' (the confirm audit confirmed
  the label on 33 of 36 z-order candidates, model-adjudicated, D82; 3 sat on a gold-defect
  task). No rater, model or person reads a reserve mutant.
- **K2.** The VM-fidelity check (`q2-evaluator-mutation-v1-k2`, VERIFIED) covered the
  confirm sample; reserve verdicts are offline verdicts.
- **S1a.** The result qualifies, but never changes, S1a's registered corrected-score readings.

## 10. Data, budget and safety

CPU only, 0 GPU-h, at most 4.0 lane-hours on the shared lane, one job at a time, nothing
submitted while another job is queued (R04, S2 v4 and Successor E share the host). Mutant
documents, recipes and saved files are third-party content and stay on the host (parent
section 16). Released after the run, written by `zr_host.py export --name reserve-v1`
(section 5) into the run's `release/` and committed:

- `campaign/`: the parent's own `campaign export` (redacted recipes, outcomes, verdict
  rows, summaries, receipts, manifest) of `view/`, a run root in the parent's layout
  (`prep`, `build`, `score` and `zinv` link to the finished attempts; `submitted.json`
  holds the parent's keys `run`, `split`, `git_sha`, `apply_to` and `jobs`, the finished
  jobs). Its `targets.json` is the parent's report on the split's 28 targets, of which step
  1 kept 8.
- `zinv-rows.json` (ids, labels, operators, scores, digests; checker messages cut to 80
  characters, as the parent's release cuts them), `judgement.json`,
  `targets-selection.json`, every receipt of every attempt, the plan, and `manifest.json`
  with each file's SHA-256.

If the run ends INCOMPLETE before step 4 (`failed_final` or `cap_reached`), `zr_host.py
export` refuses the unfinished plan; the plan, every receipt of every attempt and the
step logs are then committed by hand with their SHA-256 and the blind warning, and no
release view is claimed.

Blind warning: D9's human spot check is still pending, so every released file that names
verdicts per mutant carries the parent's blind warning (`rules.BLIND_WARNING`): a field of
the rows, the judgement and the manifest, and `BLIND-WARNING.txt` beside `campaign/`, whose
parent-format files carry none of their own. No outward action.

## 11. Development record (exploratory, never evidence)

- Unit tests: `uv run pytest -q tests/test_q2_zinv_reserve.py` (the rule, the known-answer
  read, the design numbers, the target filter, the rescoring rows, the guard, the host tool's
  commands against the frozen `submit_mutants.sh`, the code table and this file's status).
- Scratch-ledger rehearsal (2026-10-11): on a scratch copy of the branch with its own copy
  of the ledger, the draft is refused by the freeze guard, the filled file freezes into the
  copy (row 19 while main's ledger had 18 rows), `check-chain` and `verify` pass, the guard
  then admits the reserve split only with `Q2ZR_PREREG_FROZEN` set, and refuses it after any
  edit of this file; the real ledger is untouched. Record: `program/evidence/2026-10-11/q2-zinv-reserve/README.md`.
- Host rehearsal: the draft is staged on the host; `plan --split reserve` is refused (no
  ledger row); `plan --split dev` with `next --dry-run` renders step 1 without submitting;
  a scratch-frozen tree in a host temp directory passes the host-side reserve checks (the
  pinned control files match) without writing anything.
- Dev rehearsal of step 4 (Slurm 1202, from `bc14599e`, on the parent's stored
  `dev-mutants-v9` and `dev-controls-v9`; 2 min 36 s, exit 0): both guards passed in the
  container; 48 rows, all valid; zinv accepted 6 of 6 dev z-order mutants on 2 tasks, newly
  accepted none of 6 violation mutants and changed no other verdict (PASS, descriptive;
  exploratory). Before it, inspection of the released confirm verdicts showed that the
  parent's `scored_sha256` cannot be compared across scorings, and the validity rule was
  changed to the file digest of section 6 (the earlier plan was never submitted).
- Full dev rehearsal of steps 1-4 and the release view (`dev-rehearsal-v2`, from the staged
  export of `046f82e7`, whose code equals section 3's code table; Slurm 1205, 1209, 1212 and
  1213, each submitted on an empty queue, all exit 0; 0.16 lane-hours; GPU-less, network
  none). Step 1 kept the dev split's 5 pptx targets of 17; step 2 planned and admitted 97
  mutants (0 duplicates, 102 scoring jobs); step 3 recorded K2 "not drawn" (one domain) and
  scored all 102 jobs under both venvs (lock-exact: 57 evaluable, 11 ambiguous, 1 normalized,
  28 whose null mutant fails). The 97 outcomes have the same (task, operator, label, statuses,
  verdicts, probe flag) multiset as the parent's stored `dev-mutants-v9` on the same 5 tasks
  (mutant ids differ because they carry a digest of the LibreOffice-saved base, whose bytes
  differ between runs), so the target filter changed no plan. Step 4: 48 rows, all valid,
  the same multiset as `dev-zinv-v2` with identical control rows; PASS, descriptive (6 of 6
  z-order mutants on 2 tasks, none of 6 violation mutants newly accepted, 42 of 42 other
  items unchanged). `zr_host.py export` then wrote the release view of section 10 (the
  parent's `campaign export` of `view/` with jobs 1205, 1209, 1212 and 1213 and all four
  receipts, plus this addendum's files). Exploratory; record and files:
  `program/evidence/2026-10-11/q2-zinv-reserve/` (`dev-rehearsal-v2/`).
- Scratch freeze rehearsal of this file as committed (scratch clone, `main` merged, its own
  ledger copy): the suite passes at the merge (draft), at the fill commit and at the scratch
  freeze commit; the freeze export admits the reserve split only with `Q2ZR_PREREG_FROZEN`
  set, and the fill export refuses it. Record: the evidence README.

## 12. Limitations

- Small by construction (O4): 8 targets, at most 24 z-order mutants.
- The labels are the operators'; a z-order mutant on a gold-defect task would still count.
- The reserve decks come from the same OSWorld pool as the development decks; "held out"
  means unseen by zinv's development, not drawn from another distribution.
- `compare_pptx_files_tolerant` is not corrected and has no reserve task.

## 13. Freeze checklist

- A pre-freeze audit by a reviewer who did not draft this file, of this file and the code of
  section 3, including a rehearsal on a scratch clone with its own copy of the ledger (audit
  1 done; its dispositions follow; whether the fixes need a second audit is the
  orchestrator's call).
- A decisions entry recording that R03 (b) runs under program authority (D80), before the
  freeze.
- The code table refreshed, `uv run pytest -q tests/test_q2_zinv_reserve.py` passing before
  the freeze and at the freeze commit.
- The branch merged to `main` first, so the row joins `main`'s linear ledger.
- Kevin's items unchanged: the outward actions (the xlang-ai disclosure), D9's optional human
  spot check, and adopting R03 as a program question (D73).

### Pre-freeze audit 1 (2026-10-11): dispositions

The first pre-freeze audit (a reviewer who did not draft this file; scratch clone with main
merged at `08033ba7`, fill commit and scratch freeze, row 19 in a ledger copy) found one
blocking item and judged the file not ready. Each item and what was done (commit `046f82e7`
unless named):

| # | Audit item | Disposition |
|---|---|---|
| B1 (blocking) | Two tests chose the draft or frozen branch by the status paragraph, so they failed at the fill commit (filled, no row yet), which step 1 below requires to pass | Fixed: both branch on `guard.frozen_row(ROOT) is None`. The suite passes at the draft, the fill commit and the scratch freeze commit (section 11) |
| N1 | The reading of the frozen parent (section 2) is correct line by line | No change |
| N2 | "No reserve mutant exists" is too broad: the scoping probe edited all 8 tasks, and the S2 v3 pilot saved and scored their golds and do-nothing states | Fixed: section 2 says no mutant of the frozen operators exists and names both uses (neither used zinv or a frozen operator) |
| N3 | Steps 1-3 never ran in a container, not even on dev | Done: the full dev rehearsal of steps 1-4 and the release view (`dev-rehearsal-v2`, section 11) |
| N4 | The promised `campaign export` release view cannot run on the host tool's layout (no `submitted.json`, reruns in `.a2`) | Fixed: `zr_host.py export` writes `view/` in the parent's layout and runs the parent's own `campaign export` on it (section 10); tested and rehearsed on dev |
| N5 | `rules.LICENSES['PASS']['registered_rule']` claimed generalization "at the observed rate", beyond section 7 | Fixed: aligned with section 7 (the lower bound, not 95%); tested |
| N6 | Invalid rows trigger no rerun; INCOMPLETE takes precedence over FAIL in `rules.judge` but was not stated | Fixed: stated in sections 5 and 6 and in the INCOMPLETE license text; tested |
| N7 | Main moved to `08033ba7`; the merge is conflict-free | Merged (`08033ba7` and `2b8fadc7`, which changed no ledger, harness or registration file; then `f6144d6b`, which adds successor E's ledger row 19 and touches none of the code of section 3), every ledger row kept (19) |
| N8 | Design numbers, yields, known answer and the rejudged dev step-4 rows reproduce | No change |
| N9 | Host: the pinned reserve control files and both images match | No change |
| N10 | Section 4 was silent on probe-touched z-order cells | Fixed: none on the 8 tasks (section 4); tested |
| N11 | A second reserve plan under another name would be accepted | Fixed: only `reserve-v1` is evidence (section 5); the host tool refuses any other reserve plan name; tested |
| N12 | A decisions entry should record running R03 (b) under program authority (D80 does not name it; D83 says it was being scouted); optionally the parent's blind warning on released per-mutant verdicts | The decisions entry is the orchestrator's, before the freeze, and stays open here. The blind warning is added (`rules.BLIND_WARNING`, section 10) |

### At the freeze

One slot is filled only at the freeze: the status paragraph at the top of this file, whose
draft holds the placeholder that `scripts/preregister.py freeze` refuses. The freeze replaces
the whole status paragraph, from its first line to the line before the first bullet, with the
paragraph below, word for word (its line breaks may differ). Nothing else changes.

> **Status: frozen in `program/preregistrations/ledger.jsonl`; see the ledger row for the
> freeze time and `git_head_at_freeze`.** An addendum to `q2-evaluator-mutation-v1` for the
> dossier's R03 (b), frozen under program authority (D80) after its pre-freeze audit
> (section 13). The registered run (section 5) runs from an export of the freeze commit, the
> commit that adds this file's ledger row; the guard admits the reserve split only while this
> file's SHA-256 equals the row's and the staged code equals section 3's code table. A
> material change after the freeze is a new experiment id. Nothing in this file is a result.

The steps, in order:

1. On `main`, after the merge, one commit replaces the status paragraph as stated and
   changes nothing else; the tests pass on it. It becomes the row's `git_head_at_freeze`.
2. The freeze, on `main` with that commit as `HEAD`:
   `uv run python scripts/preregister.py freeze q2-zinv-reserve-validation-v1 program/preregistrations/q2-zinv-reserve-validation-v1.md`,
   then `check-chain` and `verify`; the ledger row is committed alone. That commit is the
   **freeze commit**: its parent is `git_head_at_freeze`, and the two trees differ only by
   `program/preregistrations/ledger.jsonl`.
3. After the freeze: export the freeze commit itself, never its parent (whose tree has no
   row, so the guard refuses it), to the host run root, and run section 5's commands.
4. After the freeze commit, never in it: `program/state.json`, `program/log.md` and
   `HANDOFF.md` record the freeze.
