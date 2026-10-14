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
