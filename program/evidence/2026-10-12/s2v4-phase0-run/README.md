# S2 v4 Phase 0 run: K1 (P0.6), the census, the oracle and K0

Registration: `program/preregistrations/s2-arabic-cua-locale-v4.md`, **frozen** in ledger row 21
(status-fill commit `d27331d4`, the row's `git_head_at_freeze`; freeze commit
`cf17405026ca2aa20f528b39bdaaff3b257a6610`, the commit that adds the row and changes only the
ledger). Decisions D80 (iv), D84, D87, D89, D90, D91. Every job here runs from a `git archive`
export of the freeze commit whose `.git_sha` is `cf174050...`, in the order of the freeze
procedure's step 5: K1 (`ap_delta.py render`, `submit`, one job at a time, then `verdict`), then
the capture and gold census (`vm_lane.py render-census --freeze-commit`, `submit`, and its one
resume if interrupted), then the oracle's registered container job (`oracle_vm.py --k0`) and
`k0_v4.decide` (K0). Nothing here is rerun to improve an outcome; the only reruns are the
registered ones (q2-action-path-v2 section 6.1's one rerun of a campaign that does not count; the
rung's one rerun after a foreign-load abort; the census's one resume).

Scheduling rule (D85, D87, D90, D91 and the operator's brief): CPU-only Slurm, no GRES, one job
at a time, each submitted only when the whole queue is empty, and only if its Slurm time limit
ends before the next successor E session's earliest start (12 h 5 min after the previous
session's later end, read from E's receipts on the host), or after E4 has ended; never during an
E session. E1's later end was 2026-10-12T05:46:36Z (job 1222, `scontrol` record in E's pair
directory), so E2 may start no earlier than 2026-10-12T17:51:36Z. K1's 49 jobs may run in any
order (the registration fixes none), so the short ones go into E's gaps; the jobs whose limits
exceed a 12 h 5 min gap (C3's parts, A1, A2, A3's parts) wait until E4 has ended.

## Staging

- Source: `git archive cf174050` (tar.gz, 43,673,275 bytes, SHA-256
  `e2cf765da10413a55853a91cedfea7f164b98a8499a25e4db158c0f42951f9b2`), extracted on the host by
  GNU tar 1.34 into `~/cotcodec-runs/stage0/s2v4/k1/src/cf17405026ca2aa20f528b39bdaaff3b257a6610/`,
  with `.git_sha` written as `cf17405026ca2aa20f528b39bdaaff3b257a6610`, then made read-only.
  The direct pipe (`git archive cf174050 | ssh host tar -x -C DIR`) was tried first: the host
  closed the connection after about 6 s (109 files extracted). That partial directory was removed,
  and the archive went to the host in eleven 4 MB parts (two parts needed a second `ssh`), whose
  concatenation matched the archive's SHA-256 on the host before GNU tar extracted it, as for the
  development rung 1244. No macOS tar touched the export.
- Check: the host export and a local export of the same commit (`git archive | tar -x` on the Mac,
  `.git_sha` added) hold the same 7,910 files with the same contents (the SHA-256 of the sorted
  per-file SHA-256 list, `.git_sha` excluded, is `bd289bb8...` on both), no AppleDouble file, and
  harness/q2's `source_tree_sha256` over `harness/` is `6c1037c9...`, the digest every rendered
  manifest names (and the development jobs' since round 4: the code is unchanged since `b8c815c8`).
- Correction (16:51Z, read-only on the host): the host export holds 7,914 files, the 7,910
  of the archive plus 4 Python bytecode caches (`harness/__pycache__/__init__`,
  `harness/q2/__pycache__/__init__`, `harness/q2/vm/__pycache__/__init__` and `.../manifest`,
  `cpython-310.pyc`) written at 14:43:17Z, during staging and before the tree was made read-only,
  so before the first job (14:44:33Z): every K1 job sees the same tree. The archive's own files are
  unchanged (the per-file SHA-256 list without `.git_sha` and `__pycache__` is again `bd289bb8...`,
  7,909 files, equal to the Mac export's), and harness/q2's `source_tree_sha256` and closed-world
  walk skip `__pycache__` and `.pyc` files (`harness/q2/vm/manifest.py`). The caches are left in
  place so that the remaining jobs run on the same tree.
- K1 manifests: `ap_delta.py render CHECK --cell CELL` (and `render rung`) on the Mac from the local
  export, `--git-sha cf17405026ca...` (which checks with git that the commit's only parent is the
  row's `git_head_at_freeze` and that it changes only the ledger), `--images-root
  ~/cotcodec-runs/stage0/s2v4/image-build-v5/a` (build 1207's pinned images), default host root
  `~/cotcodec-runs/stage0/s2v4/k1`. 49 manifests (`k1-manifests/`), copied to the host
  (`~/cotcodec-runs/stage0/s2v4/k1/manifests-in/`, SHA-256 list checked there). Each is validated
  again on the host by `ap_delta.py submit` (harness/q2's validator with the ledger, the image pins,
  the freeze export and the K1 plan) before `sbatch`.

Slurm limits of the 49 K1 jobs (minutes; harness/q2's worst-case budgets plus the image checks):

| Check | Jobs | Limit each | Fits a 12 h 5 min E gap |
|---|---|---:|---|
| C1 | 5 (E, A, ER, AR, PL) | 154 | yes |
| C2 | 5 | 362 | yes |
| A5 | 5 | 192 | yes |
| A6 | 5 | 222 | yes |
| rung | 1 (5 images, N = 20, 90 CPUs, 142 GB) | 110 | yes |
| C3 | 15 (3 parts per image) | 1,404, 1,404, 1,076 | no |
| A1 | 5 | 1,394 | no |
| A2 | 5 | 1,344 | no |
| A3 | 3 (AR) | 1,222, 1,192, 982 | no |

## Jobs

Each job: the guarded submission helper (`ops/submit_k1.sh`) takes a host snapshot, refuses unless
the whole queue is empty and the job's limit ends before the deadline (E's next earliest start),
and then runs `ap_delta.py submit` from the export. After the job: its Slurm state (`scontrol`,
read while Slurm still knew it), the batch's end line, every campaign read by harness/q2's
`acceptance` code and by `ap_delta.verdict` on that job alone (`check-JOB.json`; interim, the
registered K1 verdict reads every job at once). Records copied per job: the job's `preflight.txt`,
`apdelta-receipt.json` and `manifest.json`, and per campaign its `apdelta.json`, `preflight.txt`,
`manifest.json`, `receipt.json` and `session_plan.json`; the cycle records and VM logs stay on the
host under `~/cotcodec-runs/stage0/s2v4/k1/runs/JOB/`.

Host snapshot before every submission (`k1-jobs/JOB/submit-JOB.txt`): the whole queue empty, load,
available memory, running containers (always 1 so far: the host's long-running local image
registry, not a cotcodec lane container), labelled cotcodec containers (0), and E's pair
directories (E2's held only its staged configuration, no job).

| Job | What | Limit (min) | Submitted (UTC) | Ran | Slurm end | Outcome (interim, this job alone) |
|---:|---|---:|---|---|---|---|
| 1245 | K1 C1 on E (H-GA-buggy, H-OSW-up; seed 42) | 154 | 14:44:33 | 14:44:33-14:51:00 (6.5 min) | COMPLETED 0:0 | C1 pass; both campaigns count (driver exit 0, no labelled container, `infra_gates_pass`, image unchanged) |
| 1246 | K1 C1 on A | 154 | 14:51:41 | 14:51:41-14:58:09 (6.5 min) | COMPLETED 0:0 | C1 pass; both campaigns count |
| 1247 | K1 C1 on ER | 154 | 14:58:54 | 14:58:55-15:05:21 (6.4 min) | COMPLETED 0:0 | C1 pass; both campaigns count |
| 1248 | K1 C1 on AR | 154 | 15:06:02 | 15:06:02-15:12:30 (6.5 min) | COMPLETED 0:0 | C1 pass; both campaigns count |
| 1249 | K1 C1 on PL | 154 | 15:13:00 | 15:13:00-15:19:28 (6.5 min) | COMPLETED 0:0 | C1 pass; both campaigns count |
| 1250 | K1 V = 20 rung over E, A, ER, AR, PL (seed-43 order x 12; 40 sessions, 2,400 trials) | 110 | 15:20:07 | 15:20:07-15:29:10 (9.1 min) | COMPLETED 0:0 | Not aborted; 2,400 of 2,400 trials pass; every condition but the per-image step p95 met; the step condition waits for each image's A1 |
| 1257 | K1 C2 on E (L0-raw, seed 45) | 362 | 19:13:59 | 19:14:00-19:24:12 (10.2 min) | COMPLETED 0:0 | C2 pass; the campaign counts |
| 1258 | K1 C2 on A | 362 | 19:24:54 | 19:24:55-19:35:04 (10.2 min) | COMPLETED 0:0 | C2 pass; the campaign counts |

Per job:
- **1245 (C1, E).** Limit ends 17:19:33Z, before E2's earliest start 17:51:36Z. H-GA-buggy: 70
  trials (2 sessions), 20 passed; H-OSW-up: 70 trials, 40 passed (C1 requires the known-defect
  cells to fail: H-GA-buggy R01, R02, R05, R06, R07 and H-OSW-up R08-R11, each 5 of 5). Cold boots
  at most 17.9 s; step p95 1.33 s and 1.22 s. `ap_delta.verdict` on this job: C1 on E `pass`, no
  problem. No counting, foreign-abort or snapshot problem; batch end line `lane_exit=0
  labelled_containers_left=0`. Host snapshot: load 0.14, queue empty, no labelled container.
- **1246 (C1, A).** Limit ends 17:26:41Z. H-GA-buggy 70 trials, 20 passed; H-OSW-up 70, 40 passed;
  boots at most 17.3 s; step p95 1.30 s and 1.23 s. C1 on A `pass`. No problem of any kind. Host
  snapshot: load 0.70, queue empty.
- **1247 (C1, ER).** Limit ends 17:33:54Z. H-GA-buggy 70 trials, 20 passed; H-OSW-up 70, 40
  passed; boots at most 17.3 s; step p95 1.38 s and 1.22 s. C1 on ER `pass`. No problem of any
  kind. Host snapshot: load 0.44, queue empty.
- **1248 (C1, AR).** Limit ends 17:41:02Z. H-GA-buggy 70 trials, 20 passed; H-OSW-up 70, 40
  passed; boots at most 17.3 s; step p95 1.31 s and 1.23 s. C1 on AR `pass`. No problem of any
  kind. Host snapshot: load 0.55, queue empty.
- **1249 (C1, PL).** Limit ends 17:47:59Z (submitted 3.5 minutes before the last moment at which a
  154-minute job could still end before 17:51:36Z). H-GA-buggy 70 trials, 20 passed; H-OSW-up 70,
  40 passed; boots at most 17.3 s; step p95 1.30 s and 1.22 s. C1 on PL `pass`. No problem of any
  kind. Host snapshot: load 0.82, queue empty. All five C1 jobs are done.
- **1250 (the rung).** Limit ends 17:11:07Z. 90 CPUs and 142 GB allocated (20 VMs at 4 cores plus
  10 runner CPUs). `run_rung` made `driver.main`'s pre-run checks before any session (Docker
  28.3.1, runtime `runc`, cgroup v2; per image the pinned read-only file and `qemu-img info`;
  dangling volumes 0 before and 0 after). Session i ran on image i mod 5 (8 sessions per image).
  2,400 of 2,400 trials passed; 40 cold boots, boot p95 20.7 s (at most 20.8 s); 0 excused trials,
  0 guest-server restarts over 1,556 accessibility calls; no foreign Slurm job in any host snapshot
  (`aborted` false, no abort reason); every image hashed to its pin before and after
  (`qcow2_unchanged` true); no labelled container left; no counting or snapshot problem. Step
  p95 per image over its 8 sessions: E 3.053 s, A 3.087 s, ER 3.051 s, AR 3.091 s, PL 3.003 s. On
  this job alone `ap_delta.verdict` lists only the per-image step condition as a problem, because
  no A1 reference exists yet (`a1_step_p95_s` null): the rung's qualification is read in the K1
  verdict against each image's own A1 at N = 1 (step p95 at most 2 x A1's). The rung did not abort,
  so it is not rerun (registration section "K1"). Host snapshot before submission: load 0.57, queue
  empty, no labelled container.
- **1257 (C2, E).** The first job of the E2-E3 gap (section "E2 and the E2-E3 gap" below). Limit
  ends 01:16:59Z on 2026-10-13, before E3's earliest start 07:17:50Z. One L0-raw campaign (seed 45):
  9 cycles, 500 trials, 451 passed. C2's own reading (`acceptance.c2`, each trial read by
  `c2_trial_pass`): the entries that are not PASS 5 of 5 are exactly
  `l0_raw_prediction_v2.yaml`'s 8 (`click_button_back`, `click_button_forward`, `key_kp_enter`,
  `type_combining`, `type_emoji`, `type_emoji_zwj`, `type_rtl`, `type_unicode_bmp`); the section-5
  reading it reports beside them (`strict_entries`, not C2's criterion) also has
  `seq_type_chord_type`, `type_mixed_case`, `type_shell_hostile` and `type_symbols_shifted` FLAKY.
  9 cold boots at most 17.3 s; step p95 1.19 s; 8 of 8 reset sentinels pristine. `ap_delta.verdict` on this job: C2
  on E `pass`, no problem. Driver exit 0, `infra_gates_pass` true, image unchanged, no labelled
  container left; no counting, foreign-abort or snapshot problem. Host snapshot: load 0.91, queue
  empty, no labelled container; E's pair directories held E2's two collected pairs.
- **1258 (C2, A).** Limit ends 01:27:54Z. 500 trials, 457 passed; C2's reading: exactly the
  prediction's 8 entries not PASS (`strict_entries` also has `seq_type_chord_type` and
  `type_symbols_shifted` FLAKY); 9 cold boots at most 17.2 s; step p95 1.19 s; 8 of 8 reset
  sentinels pristine. C2 on A `pass`. No problem of any kind. Host snapshot: load 0.49, queue
  empty, no labelled container; E's operator had staged `e-9b-e3` and `e-4b-e3` (no job).

## Schedule for the rest of K1 (the operator's plan; not a registered rule)

- E's first gap (now to 17:51:36Z) is used up: after the rung (ended 15:29:10Z) no remaining K1
  job's limit fits before E2's earliest start (the shortest left is A5 at 192 minutes).
- E2 (9B pair, then 4B pair, about 1.3 h) may start at 17:51:36Z. Nothing is submitted from then
  until E2's 4B pair has ended (its later job end, from E's `scontrol` records under
  `~/cotcodec-runs/stage0/q2-stage1e/pairs/e-4b-e2/`). The next gap runs from that end to 12 h
  5 min after it (E3's earliest start), and so on for E3 and E4.
- In the E2-E3 and E3-E4 gaps: the 15 short jobs left (C2, A5 and A6 on each image; limits 362,
  192 and 222 minutes, expected about 15-20, 20 and 55 minutes each), each submitted only on an
  empty queue and only if its limit ends before E's next earliest start.
- After E4's 4B pair has ended: the 28 long jobs (C3's 15 parts, A1 and A2 on each image, A3's 3
  parts on AR; limits 982-1,404 minutes, expected about 1-2.5 hours each), one at a time; then
  `ap_delta.py verdict` over all 49 job directories (K1), then the census (`render-census
  --freeze-commit`, `submit`; 364-minute limit), its one resume if interrupted, the oracle's
  registered container job and `k0_v4.decide` (K0).

## E2 and the E2-E3 gap (operator's record)

- E2's 9B pair (VM job 1251, GPU job 1253) ran 17:53-18:33:52Z and its 4B pair (VM job 1254, GPU job
  1256) 18:36:41-19:12:50Z, both submitted by E's operator; no S2 v4 job was submitted from E2's
  earliest start (17:51:36Z) until the 4B pair had ended. E's `scontrol` records
  (`pairs/e-4b-e2/scontrol-1254.last.txt`, `scontrol-1256.last.txt`) give the later end
  2026-10-12T19:12:50Z (1254, COMPLETED), so E3 starts no earlier than 2026-10-13T07:17:50Z
  (epoch 1791875870), the deadline every job of this gap is checked against.
- Order in this gap, longest limit first so that every job keeps the most slack: C2 on E, A, ER, AR
  and PL (362 minutes), then A6 (222), then A5 (192), each on an empty queue.
