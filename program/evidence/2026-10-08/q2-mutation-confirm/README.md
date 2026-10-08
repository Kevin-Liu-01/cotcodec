# q2-evaluator-mutation-v1, confirm campaign, stage A1 (CPU): K1, P1, confirm mutants

Operator record of the first steps after the freeze of
`q2-evaluator-mutation-v1` (ledger row 11, hash `dc39bfa2...`, registration
SHA-256 `57dc0092...`, frozen on main at `65bc2e2`). A pre-specified
descriptive protocol under D35 and D38; nothing here is confirmatory. Every
job ran through the registered CPU-only Slurm lane
(`infra/slurm/host-single-node/q2-mutation-cpu.sbatch`, D12): no GPU
requested, `--network=none`, no `/dev/nvidia*` in any receipt. GPU time: 0.

Order, as registered (sections 3, 4 and 10): K1 on the confirm control run
(the first step after the freeze), the P1 gold fixed point over the confirm
and reserve control runs, then the confirm mutation run (targets, build,
admission, GUI-faithful save, scoring under both venvs, the S1 rescoring,
recheck and report). No registered stop condition fired.

## Staging (`staging/`)

- Source: `git archive` of `65bc2e2` staged at
  `~/cotcodec-runs/stage0/q2-evaluator-mutation/src/65bc2e2.../` with
  `.git_sha`; its 3,744 files equal the local export file for file
  (`staged-tree.json`). The only other files are two `__pycache__`
  directories that the host's `check_frozen.py` run (inside
  `submit_controls.sh`) wrote; every pin skips them.
- Pins (`pins-local-65bc2e2.txt`, `pins-host-65bc2e2.json`): every
  `PINNED_KEYS` digest of the export equals the frozen pins block (code tree
  `58bee019...`, catalog `3a5ff949...`, specs `05d4fb20...`, splits, schema,
  probe map, file-cache receipts), and on the host so do the mounted inputs
  (OSWorld tree `4153c686...`, VM baseline `f3253818...`). The ledger's hash
  chain holds (11 rows) and the staged registration matches its row. Each
  submission's `check_frozen.py` returned `frozen: true` with that ledger hash
  (`ops/`), and `campaign guard` ran in jobs 1 and 3 of every run.
- `local-tests-q2m-65bc2e2.txt`: the Q2 tests of the export, locally: 291
  passed, 21 skipped.
- Venv fingerprints in every scoring job: lock-exact `f2c9e208...`, scoping
  `e591c887...`, as pinned (section 2); the copies of jobs 781, 791 and 796
  are byte-identical, one is kept in `staging/venv-fingerprints/`.

## K1 harness validity (`controls-confirm-v1/`, Slurm 781-783)

`submit_controls.sh 65bc2e2 confirm confirm-controls-v1`, 16 workers: 197
control jobs (77 golds, 120 do-nothing), raw scoring 9 min 32 s, save stage
2 min 13 s, saved scoring 9 min 19 s, every job `COMPLETED`, exit 0.
Summary by `harness.q2_mutation.report` (registered), written to the run
directory on the host; its aggregate is `summary-aggregate.json`, the
per-task file is held (below).

- **K1: 70/74 (94.6%) under the lock-exact venv (and the scoping venv), at
  least 90% required: PASS** (`k1.json`). The four tasks not met are raw-gold
  failures (one `check_tabstops`, three `compare_pptx_files`; their raw
  do-nothing fails too), as many as the second review counted among the
  confirm target golds before the freeze; no infrastructure exclusion.
- Unemulated (section 8): 14 confirm tasks, 3 with a gold: 2a729ded and
  e8172110 (registered) and 5df7b33a, whose postconfig shell `zip` writes the
  checked archive. The registered rule (`step_may_write`) excludes it; the
  pre-freeze count in section 8 did not name it. Its gold is a `.zip`, not
  exposed to the save stage, so it changes K1's denominator only (75 to 74),
  not P1. A raw-only preview after job 781 read 71/75 because 2a729ded's
  typed postconfig is only seen by the save stage's plan.
- Saves: 135 written, none failed, none with a dialog, 7 slower than 0.5 s
  (slowest 1.10 s); no job excluded at merge. No dependency flip, no S1
  candidate, no S5 instability, no saved do-nothing passes.

## P1 gold fixed point (`controls-*/`, `p1/`)

Reserve control run `reserve-controls-v1` (Slurm 791-793, 85 jobs: 32
golds, 53 do-nothing; 4 min 15 s, 40 s and 4 min 16 s, all `COMPLETED`, exit
0): 5 unemulated tasks, none with a gold; 52 saves written, none slower than
0.5 s; no dependency flip. (Its 31/32 raw gold-pass and do-nothing-fail
count is not a K1 input.)

| Run | Counted golds | Raw flips | Clopper-Pearson 95% |
|---|---:|---:|---|
| confirm | 67 | 3 | 0.93% - 12.5% |
| reserve | 25 | 1 | 0.10% - 20.4% |
| both (registered, `analysis.p1_over_controls`) | 92 | 4 (4.35%) | 1.20% - 10.76% |

The populations are the registered 92 (67 and 25); 14 golds are listed as not
exposed (7 per split), none as not counted. P1 is a replication only (the
headless scoping round trip, another save path, flipped 7 of 63 and 1 of
26). The audit-confirmed share waits on the audit, where every flip is an
item (stratum `p1_flip`); the flip task ids stay held until the ingest.

## Confirm mutation run (`mutants-confirm-v1/`, Slurm 794-796)

`submit_mutants.sh 65bc2e2 confirm confirm-mutants-v1 ... 16 gold`: targets
2 s, build and save stage 11 min 57 s, scoring 59 min 59 s, all
`COMPLETED`, exit 0.

- Targets (`prep/targets-counts.json`): 68 targets on 67 tasks (32 xlsx, 22
  pptx, 13 docx, 1 text), as counted before the freeze; 43 tasks without a
  complete gold, 11 files without an operator family, 5 derived files.
- Build (`aggregates/build-summary.json`): 1,289 planned (the registration
  estimated about 1,100), 1,288 applied, 1,235 passed build-time purity, 3
  duplicates, 1,232 admitted (495 equivalence, 93 alternative, 290
  violation, 138 extra change, 216 ambiguous); 1,300 scoring jobs (1,232
  mutants, 68 null mutants).
- Save stage (S4 input, `aggregates/reachability-summary.json`): 1,300
  saves, all written, no failure, no dialog, no infrastructure error; 96
  (7.4%) slower than 0.5 s, slowest 1.20 s; no job excluded at merge.
- Scoring (`aggregates/notes-summary.json`): 1,300 jobs per venv, two
  fresh-process scorings each; no timeout, no infrastructure failure, no
  nondeterministic scoring; 65 jobs carry a setup step the harness cannot
  replay that does not write (no unemulated exclusion). No venv
  disagreement: S1 has no candidate (`score/mut-s1.json`).
- Recheck (S3, `aggregates/recheck-summary.json`): 1,209 of 1,232 admitted
  mutants keep their edit after the save; 23 normalized (largest share
  6/19, `xlsx.extra.clear_unrelated_row`, so no K5 finding).
- Status per mutant (lock-exact = scoping): `not_admitted` 57,
  `null_not_pass` 135, `normalized` 23, `ambiguous` 186, `evaluable` 888;
  `save_failed`, `unemulated`, `not_scored`, `infra_failed`, `error` and
  `nondeterministic` 0.
- S7: 7 of 68 targets (10.3%) have a saved null mutant that does not pass,
  four of them the K1 raw-gold failures; K9 (at least 18) does not fire.
- K2 sample (`score/k2-sample.summary.json`): drawn in job 3 from the job
  list before any verdict, 80 jobs, 20 per domain, 41 tasks. No K2 executor
  exists yet (section 10).
- Evaluable outside probe-touched cells: 444 mutants on 60 tasks. Candidate
  events there (`audit-preview/census-counts.json`, counts only): 36
  equivalence mutants the checker fails (35 `compare_pptx_files`, 1
  `compare_pptx_files_tolerant`), 5 violations it passes (3
  `compare_pptx_files`, 1 `compare_docx_files`, 1
  `compare_pptx_files_tolerant`), no alternative solution it fails, no extra
  change it passes; 93 alternative solutions it passes (P2's gate). Inside
  probe-touched cells (reported, never audited): 15 extra changes and 13
  violations it passes. The census therefore holds 134 real items on 33
  tasks plus shams and the 4 P1 flips, far under the 1,139-item capacity:
  no fallback sample is expected.
- `campaign.build_report`'s report (`report.json`, held on the host until
  the isolated ingest because it lists per-target null-mutant verdicts; its
  SHA-256 is in `held/SHA256SUMS`) gives these exploratory tables before any
  audit (task-equal, outside probe cells):
  FN 12.4% (7.2-18.3%, 60 tasks), FP_R 6.1% (0.8-13.1%, 25 tasks), FN_alt 0
  of 93, FP_F 0 of 5; 17 of 60 tasks with an FN or FP_R event. P2-P5 are
  exploratory under D34 (i); P2 and P4 are only defined after the audit.

## Held on the host until the isolated ingest (`held/SHA256SUMS`)

`~/cotcodec-runs/stage0/q2-evaluator-mutation/scratch/held-after-isolated-ingest-confirm-v1/`:
the `campaign export` of the mutation run (release rows with labels,
outcomes, verdicts, targets; its aggregate files are copied here and match
these digests), both control summaries (per-task verdicts), the raw P1
output (flip task ids), the K2 sample and the target report. Section 9: no
sample, label or rater output on the rating side before the ingest. The run
directories (mutant files, recipes, saved files) stay on the host as
registered (section 16).

## Stage A2: the audit (`audit/`)

`audit/README.md`: the salt (SHA-256 committed), the census sample of 178
items with every P1 flip of both runs (Slurm 815, CPU), the packets (two
shards), the cu129 overlay of `65bc2e2` (Slurm 817; 816 refused before any
build), the CPU args and image-input doctor (819), the open-weight rater
(Slurm 823 and 824: 178 of 178 items rated, 172 `ok` and 6
`thinking_unfinished`, clean exits; 0.365 GPU-h physical in all) and the
isolated export for the Claude rater.

## Stage B: ingest, summary, analysis (`audit/`, `results/`)

`audit/README.md` (section "Stage B") and `results/README.md`: the isolated
Claude rating ran as one unresumed workflow session of 178 rater agents
(`wf_138e30b5-c1a`); the registered collector mapped all 178 transcripts;
the ingest gave 177 `ok` and 1 `isolation_void` (a Read of a mistyped,
non-existent path outside the item directory), no relay frame, nothing to
re-rate; the salt was revealed and all 178 ids recompute; both held sets
were released after their digests checked; `audit summarize` gave κ 0.343
(138 real items) and a 34-item adjudication pool; the registered analysis
ran on the released outcomes and both control summaries. Descriptive
outputs: P1 raw 4/92 (4.35%, 1.20-10.76%), audit-confirmed 3/92 (3.26%,
0.68-9.23%); 36 false-negative candidates (all `pptx.eq.zorder_nonoverlap`
on `compare_pptx_files`(`_tolerant`): 30 confirmed, 6 unresolved; candidate
share 12.4%, 7.2-18.3%) and 5 false-positive candidates (2 confirmed, 3
label-contradicted by both raters, pending Kevin; 5.9%, 0.8-12.3%).

## Not done here

Kevin's adjudication of the 34-item pool and the 25-item human spot check
(D9), after which `audit summarize --adjudications` and the analysis are
rerun; K2 (no executor).

`SHA256SUMS` covers every file here.
