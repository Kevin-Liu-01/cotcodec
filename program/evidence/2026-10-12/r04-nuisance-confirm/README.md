# R04 registered run: checker verdicts under LibreOffice build, save route and locale (2026-10-11/12)

**Blind warning.** The score rows and analyses here name checker verdicts per gold task and
per S1a state, as the checker-mutation study's released analysis does
(`analysis.BLIND_WARNING`, printed in every analysis file). Under D80 the checker-mutation
pool and spot check were adjudicated by an isolated model (D81, D82; not human-validated);
Kevin's optional human spot check (D9) is still his, so if he means to do it blind, he does it
before reading these files. R04 reads no audit, decision, adjudication or rater file, and its
reserve-split `zinv` verdicts are not used to change `zinv` before R03 (b).

Registered run of `r04-checker-nuisance-invariance-v1`
(`program/preregistrations/r04-checker-nuisance-invariance-v1.md`, ledger row 18), under D80
(Kevin's delegation: R04 runs standalone; the section 4.4 adaptations and the CPU cap
accepted as drafted; the freeze authorized). CPU only, 0 GPU-h. Readings carry the label
"offline harness, VM fidelity unverified" in `analysis.json`; `analysis-k2.json` is the same
analysis with the K2 report (registration section 2.1).

## Result (section 9 decision rules; pinned checker, and the same under `zinv`)

Gates: control retained (92 of 92 golds and 461 of 461 S1a states saved), **V1 pass** (92
of 92 control gold verdicts equal the frozen control runs', 0 differences, 0 not compared),
**V2 pass** (the replicate cell has 0 discordances in every population: 0 confirmed, 0
unstable, 0 pending). `"complete": true`, two confirmation rounds.

| Arm | Reading | Cells |
|---|---|---|
| build | **DRIFT** | B1 (TDF 7.3.7.2) INVARIANT, B2 (7.6.7.2) INVARIANT, B3 (24.8.7.2) INVARIANT, **B4 (25.8.7.3) DRIFT**, **B5 (26.2.6.2) DRIFT** |
| locale | **DRIFT** | **de_DE DRIFT**, **ar_EG DRIFT**, ja_JP INVARIANT, **tr_TR DRIFT** |
| route | **MINOR** | `store_as` INVARIANT, `headless_convert` MINOR |

The corrected comparator (`zinv`, secondary checker) gives the same reading in every cell
and arm, with the same counts: no confirmed discordance here is a z-order effect.

Per cell (pinned checker; `k_gold` = confirmed discordant golds of 92; `t_s1a` = S1a tasks
of 32 with a confirmed discordant `s1a_pass` state; every discordance of the main run was
reproduced by both rounds, so confirmed = discordant and unstable = pending = 0 in every
cell; every cell saved 100% of its items and has 92 of 92 gold and 270 of 270 pass-state
valid pairs; no `harness_noise` flag anywhere):

| Cell | Role | Reading | `k_gold` | `t_s1a` (pass states) | `s1a_fail` | `s1a_mixed` | Families of the confirmed golds |
|---|---|---|---:|---:|---:|---:|---|
| `B0.ctrl_s.L0.r2` | validity (V2) | INVARIANT | 0 | 0 (0) | 0 | 0 | |
| `B0.store_as.L0` | route | INVARIANT | 0 | 0 (0) | 0 | 0 | |
| `B0.headless_convert.L0` | route | MINOR | 1 | 1 (7) | 3 | 0 | `compare_table` 1 |
| `B1.ctrl_s.L0` | build | INVARIANT | 0 | 0 (0) | 0 | 0 | |
| `B2.ctrl_s.L0` | build | INVARIANT | 0 | 0 (0) | 0 | 0 | |
| `B3.ctrl_s.L0` | build | INVARIANT | 0 | 0 (0) | 0 | 0 | |
| `B4.ctrl_s.L0` | build | DRIFT | 18 | 6 (67) | 1 | 0 | `compare_pptx_files` 17, `compare_table` 1 |
| `B5.ctrl_s.L0` | build | DRIFT | 20 | 6 (67) | 1 | 0 | `compare_pptx_files` 18, `compare_table` 2 |
| `B0.ctrl_s.L1` (de_DE) | locale | DRIFT | 3 | 1 (5) | 1 | 0 | `compare_table` 3 |
| `B0.ctrl_s.L2` (ar_EG) | locale | DRIFT | 4 | 2 (6) | 0 | 0 | `compare_table` 3, `compare_pptx_files` 1 |
| `B0.ctrl_s.L3` (ja_JP) | locale | INVARIANT | 0 | 0 (0) | 0 | 0 | |
| `B0.ctrl_s.L4` (tr_TR) | locale | DRIFT | 3 | 1 (5) | 1 | 0 | `compare_table` 3 |
| `B1.store_as.L0` | secondary | INVARIANT | 0 | 0 (0) | 0 | 0 | |
| `B1.headless_convert.L0` | secondary | MINOR | 1 | 1 (7) | 3 | 0 | `compare_table` 1 |
| `B2.store_as.L0`, `B2.headless_convert.L0` | secondary | INVARIANT | 0 | 0 (0) | 0 | 0 | |
| `B3.store_as.L0`, `B3.headless_convert.L0` | secondary | INVARIANT | 0 | 0 (0) | 0 | 0 | |
| `B4.store_as.L0`, `B4.headless_convert.L0` | secondary | DRIFT | 18 | 6 (67) | 1 | 0 | as `B4.ctrl_s.L0` |
| `B5.store_as.L0`, `B5.headless_convert.L0` | secondary | DRIFT | 20 | 6 (67) | 1 | 0 | as `B5.ctrl_s.L0` |

What the cells show (descriptive; nothing here is adjudicated, registration section 1):

- **Builds.** The three builds up to TDF 24.8 change no verdict; TDF 25.8 and 26.2 change
  18 and 20 of 92 gold verdicts (19.6%, exact 95% 12.0-29.1%; 21.7%, 13.8-31.6%) and 6 of
  32 S1a pass tasks (18.8%, 7.2-36.4%; 67 of 270 pass states, all `compare_pptx_files`). The
  same golds flip in all three routes of each build, so the save route does not carry it.
  Direction: pass to fail, except gold `3a7c8185` (`compare_table`), which fails in the
  control (it is one of the control's four P1 flips) and passes again under B4 and B5. B5
  adds `841b50aa` (`compare_pptx_files`) and `bc2b57f3` (`compare_table`), both pass to
  fail, to B4's set. The one S1a fail state (task `70bca0cc`) that the control flips to pass
  against the captured state reads fail again under B4 and B5.
- **Locales.** de_DE and tr_TR flip the same three `compare_table` golds (`21df9241`,
  `4f07fbe9`, `7e287123`) and five pass states of task `4f07fbe9`; ar_EG flips those three
  golds and five states, plus gold `5c1a6c3d` (`compare_pptx_files`, one of D82's
  gold-defect tasks) and one pass state of task `5c1a6c3d`; ja_JP flips nothing. de_DE and tr_TR also turn one S1a fail state
  of task `a01fbce3` (`compare_table`) to pass. Every locale flip is pass to fail on golds.
  The compiled locale data per cell (from `main/saves-summary.json`): de_DE decimal `,`,
  grouping `.`, `d_fmt` `%d.%m.%Y`; ar_EG decimal `.`, grouping `,`, `%d %b, %Y`; ja_JP
  decimal `.`, `%Y年%m月%d日`; tr_TR decimal `,`, grouping `.`, `%d-%m-%Y`.
- **Routes.** `store_as` changes nothing at any build up to 24.8. `headless_convert` changes
  one gold (`4188d3a4`, `compare_table`, pass to fail) and seven pass states of the same
  task, and turns three fail states of task `1334ca3e` (`compare_table`) to pass, under B0
  and B1 alike.
- **P1 replication** (control against the unsaved gold): 4 of 92 golds change, all pass to
  fail (`30e3e107`, `3a7c8185`, `9ec204e4`, `b8adbc24`; 4.3%, exact 95% 1.2-10.8%), as in the
  checker-mutation study's P1 (4 of 92). **S1a fixed point** (control against the captured
  state): 1 of 270 pass states (`9ec204e4`), 3 of 180 fail states (`70bca0cc`, `ecb0df7a`
  twice), 0 of 11 mixed.
- What the readings license (section 9): DRIFT names at least three golds or three tasks
  whose verdict the level changes reproducibly, here for B4, B5, de_DE, ar_EG and tr_TR;
  INVARIANT (B1-B3, ja_JP, `store_as`) bounds that level's gold discordance rate below 3.20%
  and its S1a task rate below 8.94% (exact one-sided 95%). For a re-hosted OSWorld image or
  S2's localized desktop, OSWorld's checkers cannot be kept as they are under LibreOffice
  25.8 or later, or under the de_DE, ar_EG or tr_TR locale, without accepting these flips;
  under TDF builds up to 24.8 and under ja_JP no flip was found.

## K2 label (section 2.1)

The K2 addendum's report exists (`q2-evaluator-mutation-v1-k2`, job 1186, VERIFIED, 80
pairs, no checker family dropped; `program/evidence/2026-10-11/q2-mutation-k2/k2-confirm-v1-job1186/report/k2-report.json`,
SHA-256 `39cd10ab...`). `analysis-k2.json` is the registered analysis rerun with
`--k2-report`: it differs from `analysis.json` only in `vm_fidelity` ("VM fidelity checked
(K2)", executor `7d9c881a`, outcome VERIFIED, 80 pairs, no family dropped) and the
`k2_report` input; no reading changes and there is no `k2_exploratory` part. On every cell
but the control the label means that the cell's paired control is VM-checked, not the cell
itself (section 2.1).

## Procedure

Freeze (section 17, done on `main` by this workflow's operator, who did not draft the file):
fill commit `c908b978` on `c0971a77` (status paragraph, `code_tree_sha256`
`1ffe2d19...`, the code-of-record row naming `c0971a77`); scratch freeze in a clone of the
fill commit (R04 suite 62 passed at the scratch freeze commit; the ledger-touching suites
574 passed, 11 skipped); then on `main` `scripts/preregister.py freeze`, `check-chain` and
`verify`, and the freeze commit `e312e996` adding only row 18 (row hash `f7b350a3...`,
registration SHA-256 `1191a4a0...`, frozen at 2026-10-11T18:27:01Z; the R04 suite 62 passed
at it), pushed. At the fill
commit itself the R04 suite gave 61 passed and 1 failed, by construction:
`test_registration_pins_match_the_code` requires a ledger row once the status line says
frozen (section 17 item 4), and the row only exists in the next commit. `check-chain` (20
rows) and `verify` pass on `main` today.

Run (section 6), from `SRC` = a `git archive` export of the freeze commit `e312e996` on the
host (`~/cotcodec-runs/stage0/r04-nuisance/src/e312e996.../`, `.git_sha` naming it), with
`R04_PREREG_FROZEN=r04-checker-nuisance-invariance-v1`:

1. `r04_host.py plan --src SRC --name r04-registered-v1 --registered` (2026-10-11T18:28:08Z).
2. `r04_host.py next` until complete: the item job and 13 main jobs, each submitted by the
   host tool only on an empty queue (other workstreams' jobs held the queue between R04's;
   the `waiting_for_queue` lines are in the operator's log). The last main job waited for Q2
   successor E's first session (jobs 1219-1224) to end, so that no R04 job fell between E's
   9B and 4B jobs. The item job's guard passed in the metric container; the builder matched
   P1's counted golds (67 confirm, 25 reserve; the parent's two unemulated confirm golds
   excluded) and the S1a captures of runs 1045, 1048, 1051 and 1062 against their committed
   digests: 553 items (92 golds; S1a 270 pass, 180 fail, 11 mixed).
3. `python -m harness.r04_nuisance.analysis --run RUN --src . --out RUN/analysis-main.json
   --pending-out RUN/pending.json`, run on the host from `SRC` (standard library, Python
   3.10.12, `nice`, `-B`): gates pass, 108 items (24 golds) pending under 11 cells.
4. `r04_host.py confirm --name r04-registered-v1 --pending RUN/pending.json`: both rounds
   added at once (control plus the 11 cells, on the 108 items).
5. `r04_host.py next` until complete (10 round jobs).
6. `python -m harness.r04_nuisance.analysis --run RUN --src . --out RUN/analysis.json`, then
   the same with `--k2-report program/evidence/2026-10-11/q2-mutation-k2/k2-confirm-v1-job1186/report/k2-report.json
   --out RUN/analysis-k2.json`, both on the host from `SRC` (kept in `host-analysis/`), and
   both again on the Mac from this copy, in the repository's venv (Python 3.13.14) at the
   freeze commit's checkout (`r04-registered-v1/analysis.json`, `analysis-k2.json`; see
   "Host and Mac analyses" below).

Every one of the 24 jobs finished on its first attempt (exit 0, receipt written, 0 GPUs
requested, no GRES, network none); no step was rerun, dropped or stopped by the cap.

| Step | Job | Start (UTC) | Minutes | Projected | Limit |
|---|---|---|---:|---:|---:|
| items | 1187 | 10-11 18:28:18 | 0.1 | | 60 |
| main-save-B0 | 1188 | 10-11 18:28:46 | 18.8 | 18.5 | 60 |
| main-save-B0.r2 | 1190 | 10-11 18:49:07 | 3.0 | 2.6 | 60 |
| main-save-B1 | 1191 | 10-11 18:52:10 | 7.7 | 7.9 | 60 |
| main-save-B2 | 1193 | 10-11 19:01:24 | 8.0 | 7.9 | 60 |
| main-save-B3 | 1194 | 10-11 19:09:31 | 8.0 | 7.9 | 60 |
| main-save-B4 | 1196 | 10-11 19:25:45 | 8.2 | 7.9 | 60 |
| main-save-B5 | 1198 | 10-11 19:41:29 | 8.1 | 7.9 | 60 |
| main-score-control | 1200 | 10-11 19:58:16 | 52.3 | 56.2 | 169 |
| main-score-route | 1203 | 10-11 21:05:04 | 34.8 | 37.4 | 113 |
| main-score-build | 1204 | 10-11 21:39:51 | 87.1 | 93.6 | 281 |
| main-score-locale | 1211 | 10-11 23:49:53 | 69.7 | 74.9 | 225 |
| main-score-secondary-store_as | 1216 | 10-12 02:02:30 | 89.2 | 93.6 | 281 |
| main-score-secondary-headless_convert | 1225 | 10-12 05:47:40 | 87.3 | 93.6 | 281 |
| round-1-save-B0 / B4 / B5 / B1 | 1230-1233 | 10-12 07:29:14 | 3.6 / 2.2 / 2.1 / 0.3 | 2.6 / 1.6 / 1.6 / 0.5 | 60 |
| round-1-score | 1234 | 10-12 07:39:54 | 58.7 | 43.9 | 132 |
| round-2-save-B0 / B4 / B5 / B1 | 1235-1238 | 10-12 08:38:54 | 3.5 / 2.2 / 2.1 / 0.3 | 2.6 / 1.6 / 1.6 / 0.5 | 60 |
| round-2-score | 1239 | 10-12 08:50:12 | 58.8 | 43.9 | 132 |

Lane time 616.2 minutes (10.27 lane-hours: main run 8.04, rounds 2.23) against the 20 h
cap and the registration's 9.5 h estimate; at 32 CPUs per job, 328.6 allocated CPU-h. 0
GPU-h. Main score jobs ran 5-7% under their projections; the round score jobs ran 34% over
(the scorer runs a round's 12 cells one after another on 108 items), inside their limits.

Saves (`main/saves-summary.json`, `analysis.json` `descriptive.timing`): 556 saves per cell
(553 rows), none unwritten, none with a dialog, no save failure, no infrastructure error,
no cell error; every save changed bytes. Builds identify as `LibreOffice 7.3.7.2
30(Build:2)` (B0, the VM's package `libreoffice-core 1:7.3.7-0ubuntu0.22.04.4`), 7.3.7.2
`e114eadc...` (B1), 7.6.7.2 `dd47e4b3...` (B2), 24.8.7.2 `e07d0a63...` (B3), 25.8.7.3
`30742500...` (B4) and 26.2.6.2 `ad5cf9fd...` (B5). The em-dash title fallback of section
4.4 was used on 553 items in every `ctrl_s` and `store_as` cell of B2-B5 and on none
elsewhere. The `store_as` UNO client reported ok on all 556 saves in every `store_as` cell.
No scoring failure, no excluded pair, and none of the 15,864 score rows (main run and both
rounds) has a nondeterministic or infrastructure-failed scoring under either checker.

## Contents

| Path | What it is |
|---|---|
| `r04-registered-v1/plan.json` | the host tool's plan: every step's state, job id, command, limit and times; the rounds' pending list |
| `r04-registered-v1/items/` | `items.jsonl` (the 553 items: task ids, VM and container paths, digests), `items.report.json`, the item job's receipt |
| `r04-registered-v1/main/`, `round-1/`, `round-2/` | per save job its receipt; per score job its receipt and one `scores-CELL.jsonl` per cell (scores, verdicts, digests, save events); `saves-summary.json` per run part (build identities, locale data, profile edits, failures) |
| `r04-registered-v1/rounds/` | `pending.json` and `only.txt`, written by `confirm` |
| `r04-registered-v1/analysis-main.json`, `pending.json` | the main-run analysis (`"complete": false`) and its pending list |
| `r04-registered-v1/analysis.json` | the registered analysis with both rounds (`"complete": true`), run with `--run` on this copy in the repository's venv |
| `r04-registered-v1/analysis-k2.json` | the same with `--k2-report` |
| `host-analysis/analysis.json`, `analysis-k2.json` | the same two analyses as first run on the host from the freeze export (Python 3.10.12); SHA-256 `f6c456c5...` and `4ade206f...`, equal to the host's files |
| `operator/` | the operator's wrappers: `host.sh` (runs `r04_host.py` from `SRC` over ssh), `step.sh` and `drive.sh` (call `next`, log state changes), `watch_e1.sh` and `wj.sh` (queue waits), `mirror.sh` (this copy), `jobs.py` (the job table above) |

No document is here (registration section 13): no gold, capture or saved file, no event
log, no stdout tail. The copy is the host's run directory without documents, made with
`operator/mirror.sh` (rsync with an include list) after the run. Of its 84 files, the 79
copied from the run directory (plan, items, receipts, score rows, the rounds' lists,
`analysis-main.json`, `pending.json`) have the host's SHA-256; the three
`saves-summary.json` files were written by the export's `summarize_saves.py` on the host
from the save directories; `analysis.json` and `analysis-k2.json` were made here. `tests/test_r04_evidence.py` checks that every finished
step of `plan.json` is here, that nothing here is git-ignored, and that `analysis.json`
reproduces from this copy.

Reproduce from this directory (repository root at the freeze commit or later, as the
working directory; `V=program/evidence/2026-10-12/r04-nuisance-confirm/r04-registered-v1`):

- `analysis.json`: `python -m harness.r04_nuisance.analysis --run $V --src . --out OUT.json`
  gives it except for input paths (the test strips `path` and `dir`).
- `analysis-k2.json`: the same with `--k2-report
  program/evidence/2026-10-11/q2-mutation-k2/k2-confirm-v1-job1186/report/k2-report.json`.
- `analysis-main.json` and `pending.json`: once `confirm` has written the rounds into
  `plan.json`, `--run` reads both rounds, so the main-run analysis reproduces in the
  explicit form only: `python -m harness.r04_nuisance.analysis --items $V/items/items.jsonl
  --scores $V/main/scores/control $V/main/scores/route $V/main/scores/build
  $V/main/scores/locale $V/main/scores/secondary-store_as
  $V/main/scores/secondary-headless_convert --splits confirm reserve --reference
  program/evidence/2026-10-08/q2-mutation-confirm/results/released/controls/confirm-controls-v1.summary.json
  program/evidence/2026-10-08/q2-mutation-confirm/results/released/controls/reserve-controls-v1.summary.json
  --out MAIN.json --pending-out PENDING.json`.

Host and Mac analyses. The Mac runs (from this copy, 2026-10-12) and the host runs (from
the run directory) give the same output except in the last bits of 131 Clopper-Pearson
bounds (the largest absolute difference 8.2e-16, relative 3.7e-14; the bound is computed
numerically and the two Python versions differ there) and in input paths. Every count,
discordance, bootstrap interval, gate and reading is equal. `tests/test_r04_evidence.py`
compares exactly, so the committed `analysis.json` and `analysis-k2.json` are the Mac runs,
which reproduce in the repository's environment, and the host's are kept in
`host-analysis/`. `analysis-main.json` and `pending.json` are the host's (the pending list
`confirm` used); the explicit form above, on the Mac, gives `pending.json` byte for byte
(equal to `plan.json`'s `rounds.pending` and to `rounds/pending.json`) and
`analysis-main.json` but for one bound's last bit (2.8e-17) and the run-mode inputs.

## Deviations and disclosures

- **An earlier operator instance ran an exploratory peek.** Before the main run finished
  (about 2026-10-12T02:04Z, with the secondary score jobs not yet done), the operator ran
  the analysis in its explicit form on a partial copy of the run, with the unfinished cells
  named "exploratory peek: not yet scored". Nothing in the registered procedure was chosen
  after it: the analysis, the pending rule, the rounds and the readings are fixed by the
  registration, and no step was added, rerun or dropped. The peek's files stayed in the
  operator's scratch space and are not part of this evidence.
- **The workflow was resumed mid-run.** The first operator instance stopped polling at
  2026-10-12T03:33Z while the last main score job waited for the queue; this operator
  resumed at 04:28Z from the same plan (no plan or step was edited by hand), waited for Q2
  successor E's first session to end (05:47Z) and drove the rest.
- **Analyses run on the host.** The registration lets the analysis run anywhere ("from a
  checkout of the freeze commit"); the procedure's runs were made on the host from the
  read-only export of the freeze commit (the same tree), outside Slurm, under `nice`, each
  under a minute, between R04's jobs, because the Mac was overloaded (another workstream's
  CPU job, 1228, was running during the main-run analysis). The committed final analyses are
  the Mac reruns, for the reason given under "Host and Mac analyses".
- **`tests/test_r04_evidence.py`'s glob** was widened from `r04-nuisance/` to
  `r04-nuisance*/` so that this directory (`r04-nuisance-confirm/`) is checked too. The file
  is outside R04's code tree, so the registered digest does not move.
- The S1a items cover documents the checker reads directly; derived-file paths (a postconfig
  CSV export) are tested on the golds only (registration section 5).
