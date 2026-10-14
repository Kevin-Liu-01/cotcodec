# S2 v5 Phase 0 run: K1 (P0.6), the census, the oracle and K0

Registration: `program/preregistrations/s2-arabic-cua-locale-v5.md`, **frozen** in ledger row 22
(status-fill commit `cecd06d8`, the row's `git_head_at_freeze`; freeze commit
`7c963f51ad5a634c74c7ac2dff43f75a502656de`, the commit that adds the row and changes only the
ledger). Decisions D93, D94, D96, D98, D99, D100. Every job here runs from a `git archive` export
of the freeze commit whose `.git_sha` is `7c963f51...`, in the order of the freeze procedure's
step 7: `lane_v5.py submit --dry-run` (the registered pre-census check, run first here), then K1
(`ap_delta_v5.py render`, `submit`, one job at a time, then `verdict` over every K1 job
directory), then the capture and gold census (`lane_v5.py render-census --freeze-commit`,
`submit`, and its one resume if interrupted), then the oracle's registered container job
(`oracle_vm.py --k0`) and `k0_v4.decide` (K0). Nothing here is rerun to improve an outcome; the
only reruns are the registered ones (q2-action-path-v2 section 6.1's one rerun of a campaign that
does not count; the rung's one rerun after a foreign-load abort; the census's one resume). K1 is
a kill criterion: if any K1 check fails as registered, the operator stops, and S2 ends at an
honest exit (D94, D96: v5 is S2's last registration; no rerun, no repair).

Operating precedent: v4's Phase 0 operator records
(`program/evidence/2026-10-12/s2v4-phase0-run/`, README and `ops/`). The scripts here are copies
of v4's with v5's paths, ids and verdict (`ops/submit_k1.sh`, `ops/watch_job.sh`,
`ops/collect_k1.sh`, `check_job.py`).

Scheduling rule (D85, D87, D94 and the operator's brief): CPU-only Slurm, no GRES, one job at a
time, each submitted only when the whole queue is empty. Successor E is finished (its last
session E4 ended at 21:58:06Z on 2026-10-13 and its registered analysis jobs 1279-1290 ended by
01:22Z on 2026-10-14, D97), so every K1 job is submitted with `--no-e-deadline`. If a foreign
job appears, the operator waits. The order is the K1 plan's
(`experiments/manifests/s2v4/k1-plan.json`, pinned): per image, E, A, ER, AR, PL, the checks C1,
C2, C3 (parts 1-3), A1, A2, A5, A6; then A3 on AR (parts 1-3); then the rung. 49 jobs.

## Staging (2026-10-14, 04:34-04:36Z)

- Worktree `/Users/kevinliu/repos/cotcodec-wt-ops-s2v5`, branch `ops/s2-v5`, created from
  `7c963f51`.
- Source: `git archive 7c963f51 | ssh -C fal-h100-01 tar -x -C DIR` (GNU tar 1.34 on the host;
  the archive is 259,594,240 bytes uncompressed, SHA-256 `3db7c7d9...`), into
  `~/cotcodec-runs/stage0/s2v5/k1/src/7c963f51ad5a634c74c7ac2dff43f75a502656de/` (the
  directory every K1 manifest names as `source.host_dir`), 45 s, in one pipe (v4's pipe had been
  cut after about 6 s; this one was not). Then `.git_sha` was written as
  `7c963f51ad5a634c74c7ac2dff43f75a502656de` and the tree made read-only (`chmod -R a-w`). No
  macOS tar touched the export.
- Check: the host export and a local export of the same commit (the same archive extracted on
  the Mac by Python's `tarfile`, `filter="data"`, `.git_sha` added) hold the same 9,308 files with
  the same contents: the SHA-256 of the sorted per-file SHA-256 list (`.git_sha`, `__pycache__`
  and `.pyc` excluded) is `9a8d7141224c620b...` on both; no AppleDouble file and no
  `__pycache__` on the host. On the host, `ap_delta_v5.py`, `lane_v5.py` and
  `s2v5-apdelta.sbatch` hash to the registration's pins (`fee65229...`, `86406062...`,
  `df6b936d...`).

## The registered pre-census check: `lane_v5.py submit --dry-run` (04:37Z)

- The census manifest was rendered on the Mac from the local export:
  `lane_v5.py render-census --freeze-commit 7c963f51... --repo <the repository> --source-dir .
  --pool program/proposals/evidence/2026-10-11-s2v3-arabic-cua-locale-pilot/compute/pool/pool-v3.json
  --golds experiments/manifests/s2v4/golds-v4.jsonl` (which checks with git that `7c963f51`'s only
  parent is the row's `git_head_at_freeze` `cecd06d8` and that it changes only the ledger): 1,322
  slots (882 capture, 440 gold), name `s2v5-phase0`, run root
  `~/cotcodec-runs/stage0/s2v5/phase0-runs`, Slurm 81 CPUs, 126 GB, 364 minutes; file SHA-256
  `8398d6bc...`, canonical digest `efdb8832b4d78d65...`; `lane_v5.py validate` admitted it
  (`census-dry-run/s2v5-phase0-census.json`).
- Copied to the host (`~/cotcodec-runs/stage0/s2v5/manifests-in/`, SHA-256 checked there), then,
  on the host from the freeze export, on an empty queue with no labelled container
  (`census-dry-run/census-dry-run-snapshot.txt`): `python3 -E -s -B -m harness.s2_locale.lane_v5
  submit MANIFEST --source-dir . --dry-run`. Exit 0, nothing on stderr
  (`census-dry-run/census-dry-run.out`): `vm_lane.check_host` passed (all eight mounted images
  present, read-only and of the pinned size, S 24,460,197,888 bytes and every cell image
  24,459,214,848; both Docker images present; the OSWorld checkout at `b138d348...`; the file
  cache present; the PD variant equal to its manifest), `check_once` admitted it (no census job
  under the run root), and the only write was the stored manifest
  `phase0-runs/manifests/efdb8832....json`, which `check_once` ignores. No job was submitted. The
  census is submitted only after K1, through `lane_v5.py submit` without `--dry-run`.

## K1 manifests

`ap_delta_v5.py render CHECK --cell CELL` (and `render rung`) on the Mac from the local export,
`--git-sha 7c963f51ad5a634c74c7ac2dff43f75a502656de --repo <the repository>` (the freeze commit
checked with git), default `--images-root` (build 1207's pinned images) and host root
`~/cotcodec-runs/stage0/s2v5/k1`: 49 manifests (`k1-manifests/`, `SHA256SUMS`), copied to the
host (`~/cotcodec-runs/stage0/s2v5/k1/manifests-in/`, every SHA-256 checked there). Against v4's
rendered manifests (`program/evidence/2026-10-12/s2v4-phase0-run/k1-manifests/`), after mapping
the ids (`s2v4` to `s2v5`, the experiment id, 40- and 64-hex digests), the only differing fields
are the source tree digest and the ledger row hash in all 49, and, in A6 on ER and AR only, the
cells file (`harness/s2_locale/canary_v5/suite_cells-ER.json`, `-AR.json`) and
`workload.cells_sha256`. Each manifest is validated again on the host by `ap_delta_v5.py submit`
(harness/q2's validator with the ledger, the image pins, the v5 cells files, the freeze export and
the K1 plan) before `sbatch`; C1 on E, A6 on ER and the rung were also validated there by
`ap_delta_v5.py validate` before the first submission.

Slurm limits (minutes; harness/q2's worst-case budgets plus the image checks), as v4's:

| Check | Jobs | Limit each |
|---|---|---:|
| C1 | 5 (E, A, ER, AR, PL) | 154 |
| C2 | 5 | 362 |
| C3 | 15 (3 parts per image; 17, 17 and 13 campaigns; the 3 unmutated references are in part 3) | 1,404, 1,404, 1,076 |
| A1 | 5 | 1,394 |
| A2 | 5 | 1,344 |
| A5 | 5 | 192 |
| A6 | 5 | 222 |
| A3 | 3 (AR) | 1,222, 1,192, 982 |
| rung | 1 (5 images, N = 20, 90 CPUs, 142 GB) | 110 |

## Jobs

Each job: the guarded submission helper (`ops/submit_k1.sh`, run on the host from the freeze
export) refuses unless the manifest was never submitted (no stored copy of its canonical digest
under the K1 run root, which only a real `ap_delta_v5 submit` writes, and no line in the host's
`ops.log`), the whole queue is empty and no labelled cotcodec container exists; it takes a host
snapshot and runs `ap_delta_v5.py submit --no-e-deadline`. `ops/watch_job.sh` (on the Mac, in the
background) keeps the last `scontrol show job` record while Slurm still knows the job. After the
job, `ops/collect_k1.sh` copies its run directory to the Mac scratch copy and runs
`check_job.py` (`check-JOB.json`): every campaign read by harness/q2's `acceptance` code and by
`ap_delta_v5.verdict` on that job alone (interim; the registered K1 verdict reads every job at
once). Records committed per job: the pre-submission snapshot and submit output
(`submit-JOB.txt`), the Slurm output, the last `scontrol` record and the watch log, the job's
`preflight.txt`, `apdelta-receipt.json` and `manifest.json`, and per campaign its `apdelta.json`,
`preflight.txt`, `manifest.json`, `receipt.json`, `session_plan.json` (and `cells_override.json`
for A6 on ER and AR); the cycle records and VM logs stay on the host under
`~/cotcodec-runs/stage0/s2v5/k1/runs/JOB/`.

| Job | What | Limit (min) | Submitted (UTC) | Ran | Slurm end | Outcome (interim, this job alone) |
|---:|---|---:|---|---|---|---|
| 1292 | K1 C1 on E (H-GA-buggy, H-OSW-up; seed 42) | 154 | 04:44:31 | 04:44:32-04:50:59 (6.5 min) | COMPLETED 0:0 | C1 pass; both campaigns count (driver exit 0, no labelled container, `infra_gates_pass`, image unchanged) |
| 1293 | K1 C2 on E (L0-raw, seed 45) | 362 | 04:51:57 | 04:51:58-05:02:12 (10.2 min) | COMPLETED 0:0 | C2 pass; the campaign counts |
| 1294 | K1 C3 on E, part 1 of 3 (17 mutant campaigns, M01-M11; seed 42) | 1,404 | 05:03:14 | 05:03:15-05:59:31 (56.3 min) | COMPLETED 0:0 | All 17 campaigns count; every mutant fails at least one cell; C3 is read once part 3 (the references) has run |
| 1295 | K1 C3 on E, part 2 of 3 (17 mutant campaigns, M11-M21) | 1,404 | 06:00:54 | 06:00:55-06:57:16 (56.4 min) | COMPLETED 0:0 | All 17 campaigns count; every mutant fails at least one cell |
| 1296 | K1 C3 on E, part 3 of 3 (10 mutant campaigns, M22-M28, and the 3 unmutated references) | 1,076 | 06:58:15 | 06:58:16-07:41:25 (43.2 min) | COMPLETED 0:0 | All 13 campaigns count. **C3 on E pass** over parts 1-3 (1294-1296): 42 mutants killed, 2 equivalent, 0 survived |
| 1297 | K1 A1 on E (L0-fixed at N = 1, seeds 43 and 44, both observation settings) | 1,394 | 07:42:30 | 07:42:30-09:09:50 (87.3 min) | COMPLETED 0:0 | A1 pass and C4 pass; both campaigns count; 2,000 of 2,000 trials |
| 1298 | K1 A2 on E (H-OSW-fixed and H-GA, seed 43, both observation settings) | 1,344 | 09:11:16 | 09:11:17-10:43:02 (91.8 min) | COMPLETED 0:0 | A2 pass; both campaigns count |
| 1299 | K1 A5 on E (boot reset and hygiene: 21 cold boots) | 192 | 10:46:09 | 10:46:09-11:03:24 (17.3 min) | COMPLETED 0:0 | A5 pass; the campaign counts |
| 1300 | K1 A6 on E (cross-app canary: Writer, Chrome, VS Code, GNOME Terminal; seed 43; q2's targets) | 222 | 11:04:39 | 11:04:39-11:54:25 (49.8 min) | COMPLETED 0:0 | A6 pass (300 of 300, all 60 entries 5 of 5); the campaign counts |
| 1301 | K1 C1 on A (H-GA-buggy, H-OSW-up; seed 42) | 154 | 11:55:21 | 11:55:21-12:01:48 (6.5 min) | COMPLETED 0:0 | C1 pass; both campaigns count |
| 1302 | K1 C2 on A (L0-raw, seed 45) | 362 | 12:02:39 | 12:02:39-12:12:50 (10.2 min) | COMPLETED 0:0 | C2 pass; the campaign counts |
| 1303 | K1 C3 on A, part 1 of 3 (17 mutant campaigns, M01-M11; seed 42) | 1,404 | 12:13:43 | 12:13:43-13:10:16 (56.6 min) | COMPLETED 0:0 | All 17 campaigns count; every mutant fails at least one cell; C3 is read once part 3 (the references) has run |
| 1304 | K1 C3 on A, part 2 of 3 (17 mutant campaigns, M11-M21) | 1,404 | 13:11:18 | 13:11:19-14:07:52 (56.6 min) | COMPLETED 0:0 | All 17 campaigns count; every mutant fails at least one cell |
| 1305 | K1 C3 on A, part 3 of 3 (10 mutant campaigns, M22-M28, and the 3 unmutated references) | 1,076 | 14:08:30 | 14:08:31-14:51:53 (43.4 min) | COMPLETED 0:0 | All 13 campaigns count. **C3 on A pass** over parts 1-3 (1303-1305): 42 mutants killed, 2 equivalent, 0 survived |
| 1306 | K1 A1 on A (L0-fixed at N = 1, seeds 43 and 44, both observation settings) | 1,394 | 14:53:01 | 14:53:02-16:20:12 (87.2 min) | COMPLETED 0:0 | A1 pass and C4 pass; both campaigns count; 2,000 of 2,000 trials |
| 1307 | K1 A2 on A (H-OSW-fixed and H-GA, seed 43, both observation settings) | 1,344 | 16:20:55 | 16:20:56-17:52:35 (91.7 min) | COMPLETED 0:0 | A2 pass; both campaigns count |
| 1308 | K1 A5 on A (boot reset and hygiene: 21 cold boots) | 192 | 17:54:35 | 17:54:36-18:11:51 (17.3 min) | COMPLETED 0:0 | A5 pass; the campaign counts |

Per job (host snapshot before submission, from `submit-JOB.txt`; the outcome from `check-JOB.json`
and the last `scontrol` record):
- **1292 (C1, E).** Host snapshot: load 0.02, queue empty, 1 running container (the host's
  long-running local image registry, not a cotcodec container), 0 labelled cotcodec containers,
  no K1 run directory yet. H-GA-buggy: 70 trials (2 sessions), 20 passed; H-OSW-up: 70 trials, 40
  passed (C1 requires the known-defect cells to fail: H-GA-buggy R01, R02, R05, R06, R07 and
  H-OSW-up R08-R11, each 5 of 5). Cold boots at most 17.4 s; step p95 1.36 s and 1.20 s.
  `ap_delta_v5.verdict` on this job: C1 on E `pass`, no problem. No counting, foreign-abort or
  snapshot problem; batch end line `lane_exit=0 labelled_containers_left=0`; 0 labelled
  containers on the host after the job. As v4's job 1245.
- **1293 (C2, E).** Host snapshot: load 0.33, queue empty, 0 labelled containers. One L0-raw
  campaign (seed 45): 9 sessions, 500 trials, 454 passed. C2's own reading (`acceptance.c2`,
  each trial read by `c2_trial_pass`): the entries that are not PASS 5 of 5 are exactly
  `l0_raw_prediction_v2.yaml`'s 8 (`click_button_back`, `click_button_forward`, `key_kp_enter`,
  `type_combining`, `type_emoji`, `type_emoji_zwj`, `type_rtl`, `type_unicode_bmp`); the
  section-5 reading reported beside them (`strict_entries`, not C2's criterion) also has
  `seq_type_chord_type`, `type_long_500` and `type_shell_hostile` FLAKY. Cold boots at most
  17.9 s; step p95 1.19 s; 8 of 8 reset sentinels pristine. C2 on E `pass`, no problem. Driver
  exit 0, `infra_gates_pass` true, image unchanged, no labelled container left; no counting,
  foreign-abort or snapshot problem.
- **1294 (C3, E, part 1).** Host snapshot: load 0.48, queue empty, 0 labelled containers. 17
  campaigns of the plan's 47 C3 campaigns on E (M01-M11 on their layers), 1,675 trials, one VM at a
  time; every campaign counts (driver exit 0, `infra_gates_pass`, image unchanged, no labelled
  container; no foreign-abort or snapshot problem); cold boots at most 17.9 s; step p95 at most
  1.43 s. `ap_delta_v5.verdict` on this job alone lists C3 on E as not passing, as it must: the
  three unmutated reference runs (L0-fixed, H-OSW-fixed, H-GA) are in part 3, and a cell kills a
  mutant only when the reference passed it cleanly, so every mutant reads "survived" and the
  campaigns of parts 2 and 3 read "no run". The operator's interim summary
  (`c3_interim.py`, `c3-interim-1294.json`; decides nothing): every one of the 17 mutant runs
  failed at least one cell (1 to 45 cells), none with an infrastructure failure. C3 on E is read
  from all three parts.
- **1295 (C3, E, part 2).** Host snapshot: load 0.26, queue empty, 0 labelled containers. 17
  campaigns (M11 on L0-fixed to M21), 1,667 trials; every campaign counts; cold boots at most
  17.9 s; step p95 at most 1.37 s. As for part 1, the job-alone verdict cannot read C3 (no
  reference yet). Interim summary (`c3-interim-1295.json`): every mutant run failed at least one
  cell (1 to 18 cells), none with an infrastructure failure.
- **1296 (C3, E, part 3).** Host snapshot: load 0.44, queue empty, 0 labelled containers. 13
  campaigns (M22-M28 on their layers, then the unmutated references on L0-fixed, H-OSW-fixed and
  H-GA), 1,275 trials; every campaign counts; cold boots at most 17.9 s; step p95 at most 1.35 s.
  References: L0-fixed 100 of 100 trials passed, H-OSW-fixed 97 of 99, H-GA 89 of 93 (a cell the
  reference fails cannot kill; C3's rule). Interim summary (`c3-interim-1296.json`): every
  mutant run failed at least one cell, none with an infrastructure failure.
  - **C3 on E over all three parts** (`ap_delta_v5.verdict` over 1294, 1295 and 1296, only its
    C3-on-E entry read; `k1-jobs/c3-e-interim-1294-1296.json`): **pass**, no problem. Of the 44
    scored (mutant, layer) pairs, 42 killed and 2 equivalent (`M12-triple-to-double` and
    `M13-hscroll-to-vscroll` on H-OSW-fixed, whose signatures equal the reference's), 0
    survived; no state-not-observed trial among 4,617. The same 42 killed and the same 2
    equivalent as q2-action-path-v2's attempt 1 on the certified disk
    (`program/evidence/2026-10-08/q2-action-path-v2-acceptance/acceptance/c3-verdict.json`).
- **1297 (A1, E).** Host snapshot: load 0.40, queue empty, 0 labelled containers. Two L0-fixed
  campaigns at N = 1 (seed-43 and seed-44 shuffles, 5 repetitions, screenshot and accessibility
  settings): 18 sessions and 1,000 trials each, 2,000 of 2,000 passed; 0 guest-server restarts
  over 649 counting accessibility calls in the seed-43 campaign (and none in the seed-44 one), 0
  excused trials (D33); 17 of 17 reset sentinels pristine in each; no state-not-observed trial.
  Cold boots at most 17.9 s; step p95 2.68 s and 2.71 s, 2.69 s pooled over both shuffles (the
  reference for the rung's per-image step condition on E: the rung's E sessions must have step
  p95 at most 2 x A1's). `ap_delta_v5.verdict` on this job: A1 on E `pass` and C4 on E (R-dev
  agreement, from A1's trials) `pass`, no problem. Every campaign counts (driver exit 0,
  `infra_gates_pass`, image unchanged, no labelled container; no foreign-abort or snapshot
  problem).
- **1298 (A2, E).** Host snapshot: load 0.35, queue empty, 0 labelled containers. H-OSW-fixed: 18
  sessions, 990 trials, 970 passed; H-GA: 16 sessions, 930 trials, 890 passed. Every failed trial
  is on a cell outside its layer's spec (H-OSW-fixed R03 and R09; H-GA R02, R04, R06 and R10),
  which A2 does not score; A2 judges the gating and declared cells, 5 repetitions in both
  settings. 0 guest-server restarts over 759 and 693 counting accessibility calls, 0 excused
  trials. Cold boots at most 17.9 s; step p95 2.57 s and 2.63 s. `ap_delta_v5.verdict` on this
  job: A2 on E `pass`, no problem. Both campaigns count (driver exit 0, `infra_gates_pass`, image
  unchanged, no labelled container; no foreign-abort or snapshot problem).
- **1299 (A5, E; stint 2).** Host snapshot: load 0.08, queue empty, 0 labelled containers; K1 runs
  1292-1298 only and `ops.log` listing 1292-1298 only (checked at 10:45:52Z before submitting). One
  boot-reset campaign: 21 cold boots, each after the first checking that the previous boot's
  sentinel (a file, a dconf key and a gsettings key) was gone: 20 of 20 pristine; every boot read
  back its own sentinel (21 of 21 in each store). Boots p50 17.2 s, at most 17.9 s. Reported, not
  judged (as q2-action-path-v2's jobs 374 and 964): HMP `sendkey menu` reached X in 0 of 21 boots,
  every other HMP step in 21 of 21, so the receipt's `hmp_cycles_all_ok` is 0 and its
  infrastructure gates pass. `ap_delta_v5.verdict` on this job: A5 on E `pass`, no problem. The
  campaign counts (driver exit 0, `infra_gates_pass`, image unchanged, no labelled container; no
  foreign-abort or snapshot problem).
- **1300 (A6, E).** Host snapshot: load 0.30, queue empty, 0 labelled containers. One canary
  campaign, screenshot setting, seed-43 order, 5 cold boots of 60 entries (Writer 16, Chrome 16, VS
  Code 16, GNOME Terminal 12) at q2's targets, read from q2's `suite_cells.json` (E keeps q2's
  targets): 300 of 300 trials passed, every entry 5 of 5 (`campaign_summary.py`,
  `summary-1300.jsonl`); 4 of 4 reset sentinels pristine; 0 guest-server restarts; no
  state-not-observed, infrastructure or retried trial. Cold boots at most 17.9 s; step p95 1.81 s.
  `ap_delta_v5.verdict` on this job: A6 on E `pass`, no problem, and its cells-file check `pass`
  (the campaign read q2's file, as E must). The campaign counts (driver exit 0, `infra_gates_pass`,
  image unchanged, no labelled container; no foreign-abort or snapshot problem). As v4's job 1262.
- **1301 (C1, A).** Host snapshot: load 0.37, queue empty, 0 labelled containers. H-GA-buggy: 70
  trials (2 sessions), 20 passed; H-OSW-up: 70 trials, 40 passed; the known-defect cells fail 5 of
  5 (H-GA-buggy R01, R02, R05, R06, R07; H-OSW-up R08-R11), as on E (`summary-1301.jsonl`). Cold
  boots at most 17.3 s; step p95 1.39 s and 1.22 s. `ap_delta_v5.verdict` on this job: C1 on A
  `pass`, no problem. Both campaigns count (driver exit 0, `infra_gates_pass`, image unchanged, no
  labelled container; no foreign-abort or snapshot problem).
- **1302 (C2, A).** Host snapshot: load 0.58, queue empty, 0 labelled containers. One L0-raw
  campaign (seed 45): 9 sessions, 500 trials, 454 passed, as on E. `ap_delta_v5.verdict` on this
  job (C2's own reading, `acceptance.c2`): C2 on A `pass`, no problem, so the entries that are not
  PASS 5 of 5 are exactly `l0_raw_prediction_v2.yaml`'s 8. By the trials' plain `pass` field
  (`summary-1302.jsonl`, not C2's criterion): those 8 entries 0 of 5, and `seq_type_chord_type` 1
  of 5, `type_shell_hostile` and `type_symbols_shifted` 4 of 5; 20 trials, all on the four
  window-manager chords (`chord_alt_tab`, `chord_alt_f4`, `chord_super_d`,
  `chord_ctrl_alt_shift_r`, 5 each), carry a state-not-observed mark; 0 guest-server restarts.
  Cold boots at most 17.3 s; step p95 1.19 s. Driver exit 0, `infra_gates_pass` true, image
  unchanged, no labelled container left; no counting, foreign-abort or snapshot problem.
- **1303 (C3, A, part 1).** Host snapshot: load 0.47, queue empty, 0 labelled containers. 17
  campaigns (M01-M11 on their layers, as part 1 on E), 1,675 trials, one VM at a time; every
  campaign counts (driver exit 0, `infra_gates_pass`, image unchanged, no labelled container; no
  foreign-abort or snapshot problem); cold boots at most 17.9 s; step p95 at most 1.40 s. As on E,
  the job-alone verdict cannot read C3 (no reference yet). Interim summary
  (`c3-interim-1303.json`): every mutant run failed at least one cell (1 to 45 cells), none with
  an infrastructure failure.
- **1304 (C3, A, part 2).** Host snapshot: load 0.40, queue empty, 0 labelled containers. 17
  campaigns (M11 on L0-fixed to M21), 1,667 trials; every campaign counts; cold boots at most
  17.9 s; step p95 at most 1.40 s. As for part 1, the job-alone verdict cannot read C3. Interim
  summary (`c3-interim-1304.json`): every mutant run failed at least one cell (1 to 18 cells), none
  with an infrastructure failure.
- **1305 (C3, A, part 3).** Host snapshot: load 0.49, queue empty, 0 labelled containers. 13
  campaigns (M22-M28 on their layers, then the unmutated references on L0-fixed, H-OSW-fixed and
  H-GA), 1,275 trials; every campaign counts; cold boots at most 17.4 s; step p95 at most 1.36 s.
  References: L0-fixed 100 of 100 trials passed, H-OSW-fixed 97 of 99 (R03, R09 failed), H-GA 89
  of 93 (R02, R04, R06, R10 failed), as on E. Interim summary (`c3-interim-1305.json`): every
  mutant run failed at least one cell, none with an infrastructure failure.
  - **C3 on A over all three parts** (`c3_parts.py`: `ap_delta_v5.verdict` over 1303, 1304 and
    1305, only its C3-on-A entry read; `k1-jobs/c3-a-interim-1303-1305.json`): **pass**, no
    problem. Of the 44 scored (mutant, layer) pairs, 42 killed and 2 equivalent
    (`M12-triple-to-double` and `M13-hscroll-to-vscroll` on H-OSW-fixed), 0 survived; no
    state-not-observed trial among 4,617. The same outcome as C3 on E.
- **1306 (A1, A).** Host snapshot: load 0.34, queue empty, 0 labelled containers. Two L0-fixed
  campaigns at N = 1 (seed-43 and seed-44 shuffles, 5 repetitions, screenshot and accessibility
  settings): 18 sessions and 1,000 trials each, 2,000 of 2,000 passed, every one of the 100
  entries in every trial (`summary-1306.jsonl`); 0 guest-server restarts over 649 accessibility
  calls in each campaign, 0 excused trials; 17 of 17 reset sentinels pristine in each; no
  state-not-observed trial. Cold boots at most 17.4 s; step p95 2.67 s and 2.68 s, 2.68 s pooled
  over both shuffles (2,560 steps; the reference for the rung's step condition on A: the rung's A
  sessions must have step p95 at most 2 x A1's). `ap_delta_v5.verdict` on this job: A1 on A `pass`
  and C4 on A `pass`, no problem. Both campaigns count (driver exit 0, `infra_gates_pass`, image
  unchanged, no labelled container; no foreign-abort or snapshot problem).
- **1307 (A2, A; submitted in stint 2, collected in stint 3).** Host snapshot: load 0.73, queue
  empty, 0 labelled containers, K1 runs 1292-1306. H-OSW-fixed: 18 sessions, 990 trials, 970
  passed; H-GA: 16 sessions, 930 trials, 890 passed, as on E. Every failed trial is on a cell
  outside its layer's spec (H-OSW-fixed R03 and R09; H-GA R02, R04, R06 and R10, each 0 of 10 over
  both settings; `summary-1307.jsonl`), which A2 does not score. 0 guest-server restarts over 759
  and 693 counting accessibility calls, 0 excused, retried or state-not-observed trials; 17 of 17
  and 15 of 15 reset sentinels pristine. Cold boots at most 17.3 s; step p95 2.58 s and 2.62 s.
  `ap_delta_v5.verdict` on this job: A2 on A `pass`, no problem. Both campaigns count (driver exit
  0, `infra_gates_pass`, image unchanged, no labelled container; no foreign-abort or snapshot
  problem).
- **1308 (A5, A; stint 3).** Host snapshot: load 0.24, queue empty, 0 labelled containers; K1 runs
  1292-1307 only and `ops.log` listing 1292-1307 only (checked at 17:54:30Z before submitting).
  One boot-reset campaign: 21 cold boots (21 distinct boot ids), each after the first checking
  that the previous boot's sentinel (a file, a dconf key and a gsettings key) was gone: 20 of 20
  pristine; every boot read back its own sentinel (21 of 21 in each store). Boots p50 17.2 s, at
  most 17.4 s. Reported, not judged (as on E and in q2-action-path-v2's jobs 374 and 964): HMP
  `sendkey menu` reached X in 0 of 21 boots, every other HMP step in 21 of 21, so the receipt's
  `hmp_cycles_all_ok` is 0 and its infrastructure gates pass. `ap_delta_v5.verdict` on this job:
  A5 on A `pass`, no problem. The campaign counts (driver exit 0, `infra_gates_pass`, image
  unchanged, no labelled container; no foreign-abort or snapshot problem).

## Stint 1 stop (operator's record, 10:44Z on 2026-10-14)

- Done in stint 1 (04:33-10:44Z): the worktree and branch; the staged freeze export; the
  registered pre-census `lane_v5.py submit --dry-run` (passed); the 49 K1 manifests; and K1 jobs
  1292-1298 in the plan's order, all on E: C1, C2, C3 parts 1-3, A1 and A2. Every job COMPLETED
  0:0, every campaign counts, and every check read so far passes (interim, job by job; C3 on E
  read over its three parts). No K1 check has failed; nothing was rerun or resubmitted.
- Clean point: no job of this workstream is running. At 10:44:23Z the queue was empty and no
  labelled cotcodec container was running on the host.
- Next, in the plan's order: A5 on E (`k1-a5-e.json`), A6 on E (`k1-a6-e.json`), then image A
  (C1, C2, C3 parts 1-3, A1, A2, A5, A6), ER, AR, PL, then A3 on AR (parts 1-3), then the rung;
  42 K1 jobs remain. Then `ap_delta_v5.py verdict` over all 49 K1 job directories (K1), then the
  census (`lane_v5.py submit` of `census-dry-run/s2v5-phase0-census.json`, already rendered and
  dry-run), its one resume if interrupted, the oracle's registered container job and
  `k0_v4.decide` (K0).
- Observed durations on E, for planning: C1 6.5 min, C2 10.2 min, C3 parts 56, 56 and 43 min,
  A1 87 min, A2 92 min (v4: A5 about 20 min, A6 about 50 min). At that pace the remaining 42 jobs
  need about 33 hours of serial wall clock (about 7 hours per image, and A3 and the rung).

## Stint 2 (operator's record, 10:45-16:25Z on 2026-10-14)

- Before submitting (10:45:52Z): the queue was empty, `ops.log` listed jobs 1292-1298 only, the K1
  run directory held 1292-1298 only and no labelled cotcodec container existed; no job was
  resubmitted. `main` did not move during the stint (`bddf4b38`, already merged).
- Done in stint 2, in the K1 plan's order, each on an empty queue through `ops/submit_k1.sh`:
  1299 A5 on E, 1300 A6 on E, then image A: 1301 C1, 1302 C2, 1303-1305 C3 parts 1-3, 1306 A1.
  Every job COMPLETED 0:0, every campaign counts, and every check read so far passes (interim,
  job by job; C3 on A read over its three parts with `c3_parts.py`). E's eight checks have all
  run and pass (C1, C2, C3, C4, A1, A2, A5, A6). No K1 check has failed; nothing was rerun or
  resubmitted. Operator aids added: `campaign_summary.py` (per-entry pass counts,
  `summary-JOB.jsonl`) and `c3_parts.py` (C3 on one image over its three parts); both decide
  nothing.
- Stint 2's operator conveniences, in `ops/` (Mac side; they decide nothing): `post_submit.sh JOB
  MANIFEST` (starts the watcher and records `submit-JOB.txt`), `wait_job.sh JOB` (a bounded poll
  of the watcher, at most 3.5 minutes per call), `collect_and_read.sh JOB` (Headroom check,
  `collect_k1.sh`, `campaign_summary.py`, and a compact print of `check-JOB.json`) and
  `readme_append.py` (adds a jobs-table row and a per-job note here).
- Stop point: job 1307 (A2 on A, submitted 16:20:55Z, limit 1,344 minutes, expected about
  92 minutes from E's A2) is running; at 16:21:29Z it was the only job in the queue and the only
  labelled containers on the host were its own. Its collection is stint 3's. A background
  watcher (`ops/watch_job.sh 1307`) was left running on the Mac to keep its last `scontrol`
  record; if it is gone, start another before the job ends.
- Next, in the plan's order after 1307: A5 on A (`k1-a5-a.json`), A6 on A (`k1-a6-a.json`), then
  ER, AR and PL (C1, C2, C3 parts 1-3, A1, A2, A5, A6 each), then A3 on AR (parts 1-3), then the
  rung: 27 jobs after 1307. Then `ap_delta_v5.py verdict` over all 49 K1 job directories (K1),
  then the census, its one resume if interrupted, the oracle's registered container job and
  `k0_v4.decide` (K0).
- Observed durations on A, as on E: C1 6.5 min, C2 10.2 min, C3 parts 56.6, 56.6 and 43.4 min,
  A1 87.2 min; on E, A5 17.3 min and A6 49.8 min.

## Stopped by the program owner (2026-10-14, D103)

At 18:41Z on 2026-10-14 Kevin decided to give S2 up: "if its unlikely to result in anything meaningful, give up". K1 job 1309 (A6 on A) was running. It was cancelled with `scancel` at about 18:41Z. The lane stopped on TERM and removed its own containers: 0 labelled containers were left, and the queue was empty afterwards. Job 1309 is not counted and was not collected. The K1 jobs completed and collected before the stop are recorded above. No K1 verdict, census, oracle or K0 was run. S2 v5 ends here with no result (D103).
