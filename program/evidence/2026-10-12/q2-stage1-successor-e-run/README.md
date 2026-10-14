# q2-stage1-successor-e-v1 (successor E): OE and the E jobs, from 2026-10-12

Frozen registration `q2-stage1-successor-e-v1` (ledger row 19, file SHA-256
`47e65877aed069fe919d1a2976345b3d5755e4323a71b47f99ece61c6e2ae98b`, row hash
`0da0a6825c8aad1b0db085f13adef5febb2661bced7e676156c88e009d521ba2`, frozen
2026-10-12T01:02:32Z). Everything here runs from E's freeze commit
`f6144d6bf745d944cb016cfc2b9894e1dbf7eb66` (tree `b8d37e7f4bdb4a54593447b68524b34b309cd4a5`),
the commit that adds the row, never its parent (`7fcf0a4a`, the row's `git_head_at_freeze`).
One operator per session, in the registered order (section 5.3): OE, then E-9B-E1 and
E-4B-E1 (session E1), then the later sessions, each at least 12 h 5 min after the previous
session's later end.

This README is extended per session. It reads infrastructure fields only (statuses, losses,
re-queues, completeness, observation and restart counts, Slurm and engine records): **no
score, success rate or harness comparison is computed here**. The registered analysis
(section 18) ran after the last E job; its readings are in `RESULTS.md` and its steps in
`analysis/`. All eight E jobs have run (sessions E1-E4, the last
ending at 21:58:03 UTC on 2026-10-13), and none fired DR0.

## Jobs

| Job | What | Resources | Outcome | Physical GPU-h | Charged (D22) |
|---:|---|---|---|---:|---:|
| 1215 | OE: cu129 overlay build from the freeze commit | 1 H100, 8 CPUs, 32 GB, 3 min | COMPLETED 0:0 in 57 s (02:01:30-02:02:27 UTC, 2026-10-12); overlay `sha256:5d1d4d8f1ff4a92cc607704b5e8e9adaa0269b8fa27757d6fe51616e438584ef` | 0.0158 | 3 min |
| 1219 | E-9B-E1 VM lane | 90 CPUs, 126 GB, 62 min, no GRES | COMPLETED 0:0 in 00:39:55 (04:28:39-05:08:34 UTC, 2026-10-12) | 0 | - |
| 1220 | E-9B-E1 GPU half, `sbatch --test-only` | - | never ran | 0 | - |
| 1221 | E-9B-E1 engine and bridge (Qwen3.5-9B) | 1 H100, 32 CPUs, 160 GB, 52 min, `--dependency=after:1219` | COMPLETED 0:0 in 00:39:52 (04:28:39-05:08:31) | 0.6644 | 52 min |
| 1222 | E-4B-E1 VM lane | 90 CPUs, 126 GB, 58 min, no GRES | COMPLETED 0:0 in 00:36:41 (05:09:55-05:46:36) | 0 | - |
| 1223 | E-4B-E1 GPU half, `sbatch --test-only` | - | never ran | 0 | - |
| 1224 | E-4B-E1 engine and bridge (Qwen3.5-4B) | 1 H100, 32 CPUs, 160 GB, 48 min, `--dependency=after:1222` | COMPLETED 0:0 in 00:36:37 (05:09:56-05:46:33) | 0.6103 | 48 min |
| 1251 | E-9B-E2 VM lane | 90 CPUs, 126 GB, 62 min, no GRES, `--begin=2026-10-12T17:51:33` (already past at submission) | COMPLETED 0:0 in 00:40:45 (17:53:07-18:33:52 UTC, 2026-10-12) | 0 | - |
| 1252 | E-9B-E2 GPU half, `sbatch --test-only` | - | never ran | 0 | - |
| 1253 | E-9B-E2 engine and bridge (Qwen3.5-9B) | 1 H100, 32 CPUs, 160 GB, 52 min, `--dependency=after:1251` | COMPLETED 0:0 in 00:40:41 (17:53:08-18:33:49) | 0.6781 | 52 min |
| 1254 | E-4B-E2 VM lane | 90 CPUs, 126 GB, 58 min, no GRES, `--begin=2026-10-12T17:51:33` (already past) | COMPLETED 0:0 in 00:36:09 (18:36:41-19:12:50) | 0 | - |
| 1255 | E-4B-E2 GPU half, `sbatch --test-only` | - | never ran | 0 | - |
| 1256 | E-4B-E2 engine and bridge (Qwen3.5-4B) | 1 H100, 32 CPUs, 160 GB, 48 min, `--dependency=after:1254` | COMPLETED 0:0 in 00:36:03 (18:36:44-19:12:47) | 0.6008 | 48 min |
| 1265 | E-9B-E3 VM lane | 90 CPUs, 126 GB, 62 min, no GRES, `--begin=2026-10-13T07:17:47` (already past at submission) | COMPLETED 0:0 in 00:38:54 (07:18:02-07:56:56 UTC, 2026-10-13) | 0 | - |
| 1266 | E-9B-E3 GPU half, `sbatch --test-only` | - | never ran | 0 | - |
| 1267 | E-9B-E3 engine and bridge (Qwen3.5-9B) | 1 H100, 32 CPUs, 160 GB, 52 min, `--dependency=after:1265` | COMPLETED 0:0 in 00:38:51 (07:18:02-07:56:53) | 0.6475 | 52 min |
| 1268 | E-4B-E3 VM lane | 90 CPUs, 126 GB, 58 min, no GRES, `--begin=2026-10-13T07:17:47` (already past) | COMPLETED 0:0 in 00:37:28 (07:58:42-08:36:10) | 0 | - |
| 1269 | E-4B-E3 GPU half, `sbatch --test-only` | - | never ran | 0 | - |
| 1270 | E-4B-E3 engine and bridge (Qwen3.5-4B) | 1 H100, 32 CPUs, 160 GB, 48 min, `--dependency=after:1268` | COMPLETED 0:0 in 00:37:22 (07:58:45-08:36:07) | 0.6228 | 48 min |
| 1272 | E-9B-E4 VM lane | 90 CPUs, 126 GB, 62 min, no GRES, `--begin=2026-10-13T20:41:07` (already past at submission) | COMPLETED 0:0 in 00:38:49 (20:41:28-21:20:17 UTC, 2026-10-13) | 0 | - |
| 1273 | E-9B-E4 GPU half, `sbatch --test-only` | - | never ran | 0 | - |
| 1274 | E-9B-E4 engine and bridge (Qwen3.5-9B) | 1 H100, 32 CPUs, 160 GB, 52 min, `--dependency=after:1272` | COMPLETED 0:0 in 00:38:46 (20:41:28-21:20:14) | 0.6461 | 52 min |
| 1275 | E-4B-E4 VM lane | 90 CPUs, 126 GB, 58 min, no GRES, `--begin=2026-10-13T20:41:07` (already past) | COMPLETED 0:0 in 00:36:21 (21:21:45-21:58:06) | 0 | - |
| 1276 | E-4B-E4 GPU half, `sbatch --test-only` | - | never ran | 0 | - |
| 1277 | E-4B-E4 engine and bridge (Qwen3.5-4B) | 1 H100, 32 CPUs, 160 GB, 48 min, `--dependency=after:1275` | COMPLETED 0:0 in 00:36:18 (21:21:45-21:58:03) | 0.6050 | 48 min |
| | **Total (all eight E jobs and OE)** | | | **5.0908** | **403 of 406 min** |

Job ids 1213, 1214 and 1216 are other workstreams' (R03 part (b)'s rehearsal 1213, S2 v4's
development smoke 1214, R04's score job 1216); none was in the queue when OE was submitted or
while it ran. Job ids 1217 and 1218 are not this experiment's; neither was in the queue at any
E submission or in any queue sample taken while an E job ran. 1220 and 1223 are the ids Slurm
gave the GPU halves' `sbatch --test-only` probes (as S1a's 1046 and 1049); no job ran under
them. Job ids 1225-1250 are not this experiment's either: the ones this operator's queue polls
saw were R04's (1225, 1230, 1234, 1235, 1239), R03 part (b)'s (1227-1229) and S2 v4's (1240,
1242, 1244-1250), all in the gap between sessions E1 and E2; none was in the queue at either E2
submission or in any queue sample taken while an E2 job ran. 1252 and 1255 are E2's
`--test-only` ids. S2 v4's job 1257 was submitted at 19:13:59 UTC, after E-4B-E2's VM batch job
had ended (19:12:50). Job ids 1257-1264 are S2 v4's K1 jobs, all in the gap between sessions E2
and E3 (D93); none was in the queue at any poll this operator took from 00:06 UTC on
2026-10-13, at either E3 submission or in any queue sample taken while an E3 job ran. 1266 and
1269 are E3's `--test-only` ids. Job 1271 (S2 v5's `s2v5-step0-canary-v1`, 6 CPUs, no GRES)
was submitted at 08:37:17 UTC, after E-4B-E3's VM batch job had ended (08:36:10), and had left
the queue by 09:21 UTC, in the gap between sessions E3 and E4 (D94, D96); it was in no queue
sample taken at either E4 submission or while an E4 job ran. 1273 and 1276 are E4's
`--test-only` ids. The next job on the host, S2 v5's 1278 (6 CPUs, no GRES), was submitted at
22:00:32 UTC, after E-4B-E4's VM batch job had ended (21:58:06). Charged under D22: OE's 3 minutes and 52 + 48 for each of sessions E1, E2,
E3 and E4, 403 of E's 406 cap-minutes; the OE retry's 3 minutes stay unspent.

## Source and the frozen registration

- The read-only export `~/cotcodec-runs/stage0/q2-stage1e/src/f6144d6bf745d944cb016cfc2b9894e1dbf7eb66/`
  on the host is `git archive f6144d6b` (tar SHA-256
  `21eaa6b279805b3b000c44c2bb4270c521a2ae1c4c4d0e08c50f1806f41f9339`) plus a `.git_sha` file
  naming the commit (as in the G-E4 export; the VM lane's preflight reads it), made read-only
  (`chmod -R a-w`). Its file list equals the commit's `git ls-files` (7,629 entries), and its
  contents equal a clean clone of the commit file for file (`diff -r`).
- A git bundle of the operations branch at `f6144d6b` (SHA-256 `a041499f...`) was copied to the
  host and cloned; the clone `oe/checkout-f6144d6bf745` is detached at `f6144d6b`, `git status`
  empty, tree `b8d37e7f...`. OE ran from the clone; every E job runs from the export.
- `scripts/preregister.py verify q2-stage1-successor-e-v1` and `check-chain` passed in the
  export and in the clone before OE (`oe/preregister-verify.txt`, 01:07:39 UTC: row 19, file
  SHA-256 `47e65877...`, 19 rows, PASS), and again in the export right before each pair was
  submitted (`*/pair/preregister-verify.txt`). E's lane makes the same check itself at
  `validate`, `submit` and job start (`lane.frozen_registration`).
- Every file of section 23's two tables (E's 11 files and the 8 infrastructure files) has the
  registered SHA-256 in the export, as do S1a's GPU template and docker submitter.
- Interpreters, as in S1a: `scripts/preregister.py` under the host's uv-managed CPython
  3.12.13 (it needs `datetime.UTC`); the renderers, lane, submitter, DR0 and the checks under
  the system Python 3.10 with `-E -s -B`, the interpreter `q2e-vm.sbatch` runs the lane with.

## OE (`oe/`)

- **Source archive**: `scripts/create_source_archive.py --discovery` in the clean clone with
  the default ref `HEAD`: SHA-256
  `6ad9ad67e825dbc99f4c0fbb7fab25d19caee25a8f17ec7ab8495695f63e2a4f`, 7,602 files,
  `selected_ref: HEAD`, `worktree_clean: true`, git tree `b8d37e7f...`
  (`source-receipt-head.json`, SHA-256
  `84e76f95c0469f65dcd5f092da4ba1ebe7e2fea46ba8513c2da13e90d47fec64`).
- **CPU pre-check** (S1a's O2 step, so that OE's one retry could not be spent on a receipt
  error like job 1032's): the pinned extractor (`9b4d21a8...`) validated that archive and
  receipt into an empty scratch directory with the expected commit and tree
  (`precheck-source-validation.json`: `VALIDATED_DISCOVERY_SOURCE`, 7,602 members); the base
  image's ID (`sha256:423783aa...`) and its commit label (`db9527a4...`) were checked. No GPU.
- **Job 1215** (`ops/oe-wait-submit.sh oe`): `sbatch` of the clone's
  `scripts/build_vllm_overlay_on_h100.sh` (builder `aa43283e...`, extractor `9b4d21a8...`:
  section 23's, S1a's O2's), one H100, 8 CPUs, 32 GB, `--time=00:03:00`, `--no-requeue`,
  submitted at 02:01:28 UTC by a loop that polls `squeue` every 2 s and calls `sbatch` only on
  an empty queue (`ops.log`: queue empty, every GPU at 0 MiB). It ran 02:01:30-02:02:27,
  **COMPLETED 0:0 in 57 s** (`slurm-state-1215.txt`); the 5-second queue watcher saw only job
  1215 while it ran (`squeue-watch.log`).
- **Build receipt** (`build-receipt.json`, SHA-256
  `b8f36411bf44cb1975cf2aafef4af6e574fa48da2d3473bf471aa77fcced17c9`): provenance **PASS**
  (`git_sha` `f6144d6b...`, `source_sha256` `6ad9ad67...`), base
  `vllm/vllm-openai@sha256:b18abb2d...` (vLLM 0.31.0, `db9527a4...`), torchcodec removed as
  in O1 and O2, the vLLM argument doctors pass, tag `cotcodec-vllm:6ad9ad67-cu129-overlay`,
  **overlay `sha256:5d1d4d8f1ff4a92cc607704b5e8e9adaa0269b8fa27757d6fe51616e438584ef`**; the
  image's labels carry revision `f6144d6b...` and source-tree digest `6ad9ad67...`.
- The OE retry was not needed; its 3 minutes stay unspent (section 7.2). Every E GPU half
  names this overlay, the freeze commit and this archive (`gpu-values.json`), and its container
  refuses to start unless the overlay's embedded `git_sha` and `source_sha256` equal its
  manifest's (G-E7).

## Session E1 (2026-10-12; `e-9b-e1/`, `e-4b-e1/`)

**Result, registered per-job checks only.** Both jobs of session E1 scored 226 of 226
episodes, with no infrastructure loss, no re-queue and no cap truncation, and **DR0 does not
fire for either** (`python -m harness.q2_stage1e.analysis dr0`, exit 0, `fires: false`, no
reasons). The lane's frozen-registration, prior-job, engine-argv and Slurm-limit checks passed
for both, and no foreign Slurm job ran while either job ran. **No outcome was read or
summarized**: this section reads infrastructure fields only.

**Session E1's later end: 2026-10-12T05:46:33Z** (epoch 1791783993), E-4B-E1's end by
`lane.job_end`: the later of its lane's `t_end` (05:46:31.09) and its GPU job's recorded Slurm
EndTime (05:46:33). E-9B-E1 ended at 05:08:31 by the same rule. **Session E2 may not start
before 2026-10-12T17:51:33Z** (12 h 5 min later, `plan.session_not_before`). VM batch job
1222 ended at 05:46:36, 3 s after the GPU job, inside the 5-minute margin (section 5.3).

### Waiting for a quiet host

E-9B-E1's VM manifest was rendered and validated at 01:11 UTC (`pair/e-9b-e1-vm.json`, SHA-256
`a08a6afa...`; canonical form `85e71881...`). R04's job 1216 started five seconds after OE
ended and held the queue at every check from 02:02:50 to 03:18:23 UTC (`pair/ops.log`,
`pair/wait.log`); nothing of E's was submitted while it ran. The operator session that ran OE
ended at 03:18 without submitting; this operator resumed at 04:25:38 and found the queue empty
and no operator process left on the host (no `submit-pair-e.sh`, `wait-then-submit-pair-e.sh`
or watcher running). Before submitting it re-checked the export against the freeze commit:
every regular file's SHA-256 equals `git archive f6144d6b` (7,602 files), the 27 symlinks and
their targets are equal, `.git_sha` names `f6144d6b...`, and no file or directory is writable.
The five operator scripts on the host equal the committed files by SHA-256.

### E-9B-E1 (`e-9b-e1/`: VM job 1219, GPU job 1221)

- **Host before submission** (`pair/pre-submit-snapshot.txt`, 04:28:38 UTC): `squeue -a`
  empty, load 0.06, one container (the local registry), every GPU at 0 MiB (`pair/ops.log`).
- **Submission** (`wait-then-submit-pair-e.sh e-9b-e1`, run under `nohup setsid` on the host,
  so a dropped ssh session could not leave a VM job without its GPU half; `pair/submit-run.out`):
  verify and `check-chain` PASS in the export (row 19, file SHA-256 `47e65877...`, 19 rows;
  `pair/preregister-verify.txt`); `lane validate` ok (226 slots); `lane submit --dry-run`
  (`--cpus-per-task=90 --mem=126G --time=01:02:00`); a placeholder GPU half through the
  submitter's `--dry-run`; queue empty; VM job 1219 at 04:28:39; the GPU half rendered from the
  validated VM manifest (`pair/e-9b-e1-gpu.yaml`, `5e2f28c9...`: 9B, 52 minutes, the OE
  overlay, the freeze commit, OE's archive, the 9B receipt `0a9e052d...` and artifact root
  `9845026d...`, S1a's A1 9B halves'); dry run `--time=00:52:00 --signal=B:USR1@180
  --dependency=after:1219`, 0.8667 GPU-h budget; `--test-only` exit 0; no foreign job; GPU job
  1221 at 04:28:39.
- **The lane's checks** (`pair/job-checks.json`, from `ops/job_checks_e.py`):
  - manifest: purpose `e`, plan `4e7298a7...`, 226 slots equal to `plan.slots(9B, E1)`, V 20,
    GPU cap 52, VM limit 62 minutes, 90 CPUs, no prior jobs (E-9B-E1 is first);
  - preflight (`vm-1219/preflight.txt`): batch `2d27bbe5...` (`q2e-vm.sbatch`), manifest
    `85e71881...`, source git SHA `f6144d6b...`, TRES `cpu=90,mem=126G` with no GRES, lane
    exit 0, no labelled container left;
  - provenance: `gpu-1221/provenance-verification.txt` PASS, `git_sha` `f6144d6b...` and
    `source_sha256` `6ad9ad67...` equal to the GPU manifest's; image the OE overlay
    `5d1d4d8f...`; model verification: `qwen3.5-9b` at `c2022362...`, root `9845026d...`;
  - engine argv: `ready.json`'s argv equals S1a's `plan.engine_argv` for 9B (SHA-256
    `9b307cdc...`, S1a's); the bridge started 15.7 s after the Slurm start and the engine was
    ready 97.1 s later;
  - Slurm limit: the lane read TimeLimit 52 minutes, equal to the cap; USR1 point = Slurm start
    (04:28:39) + 52 min - 180 s (05:17:39);
  - receipt: no error, not stopped; first dispatch 113.2 s after the GPU job's Slurm start
    (L = 113.19 s was assumed, section 7.1); last record 9.2 minutes before the USR1 point;
    the engine stopped on `vm_done`, return code 0; termination `completed`, no container
    killed.
- **Counts**: 226 slots dispatched, 226 records, every one `scored`, every one attempt 1 (113
  per harness); no infrastructure loss, no `cap_truncated`; 226 of 226 plan cells final; no
  guest-server restart; no context fallback; observations: 3,009 agent screenshot calls and
  629 checker reads, none retried, slower than 30 s or undelivered; no setup failure, no
  postconfig failure; no GPU device seen in an episode container; every container gone at
  teardown, no leaked volume.
- **DR0** (`pair/dr0.json`, exit 0): `fires: false`, `base_complete: true`, 0 of 113
  first-attempt episodes lost in each (9B, harness) cell; records `278e8112...`, receipt
  `32a4a1f7...`, manifest `d7ed851d...`.
- **Host while it ran**: the lane's three snapshots (start, block `e1`, end) list only the
  pair's own GPU job 1221 (load at most 1.54, no foreign job); the 15-second queue watcher's 161
  samples (04:28:39-05:08:43) hold only 1219 and 1221.

### E-4B-E1 (`e-4b-e1/`: VM job 1222, GPU job 1224)

- **Manifest** (rendered after E-9B-E1 left the queue and its DR0 was read):
  `render_q2e_manifest.py vm --host pair/host.json --size 4B --session E1 --prior-run-dirs
  runs/1219` from the export (`pair/e-4b-e1-vm.json`, SHA-256 `478f7f57...`; canonical form
  `b0707682...`): 226 slots, V 20, GPU cap 48, VM limit 58 minutes, 90 CPUs, prompt date
  2026-10-08, plan `4e7298a7...`; `e.prior_jobs` names E-9B-E1's records (`278e8112...`) and
  receipt (`32a4a1f7...`), the digests DR0 had just read. `lane validate` ok.
- **Host before submission** (`pair/pre-submit-snapshot.txt`, 05:09:54 UTC): `squeue -a`
  empty, load 0.68 (falling after E-9B-E1), one container (the local registry), every GPU at
  0 MiB.
- **Submission** (the same script, 05:09:54-05:09:55; `pair/submit-run.out`): verify and
  `check-chain` PASS; `lane submit --dry-run` (`--time=00:58:00`); VM job 1222 at 05:09:55; GPU
  half `pair/e-4b-e1-gpu.yaml` (`d86754c5...`: 4B, 48 minutes, the OE overlay, the 4B receipt
  `75ebfc53...` and artifact root `3b8a0751...`, the receipt S1a's A1 4B halves verified, D57
  (i)); dry run `--time=00:48:00 --signal=B:USR1@180 --dependency=after:1222`, 0.8 GPU-h
  budget; `--test-only` exit 0; no foreign job; GPU job 1224 at 05:09:55.
- **The lane's checks** (`pair/job-checks.json`):
  - manifest: 226 slots equal to `plan.slots(4B, E1)`; the prior job E-9B-E1 by both digests,
    which the lane accepted at submission and at job start;
  - preflight: batch `2d27bbe5...`, manifest `b0707682...`, source `f6144d6b...`, no GRES,
    lane exit 0, no labelled container left;
  - provenance PASS (`f6144d6b...`, `6ad9ad67...`, equal to the GPU manifest's); model
    verification: `qwen3.5-4b` at `851bf6e8...`, root `3b8a0751...`;
  - engine argv equals S1a's `plan.engine_argv` for 4B (SHA-256 `1c4cffba...`); the bridge
    started 7.9 s after the Slurm start and the engine was ready 97.1 s later;
  - Slurm limit: TimeLimit 48 minutes, equal to the cap; USR1 point = 05:09:56 + 48 min - 180 s
    (05:54:56);
  - receipt: no error, not stopped; first dispatch 105.6 s after the Slurm start; last record
    8.4 minutes before the USR1 point; engine stopped on `vm_done`, return code 0; termination
    `completed`.
- **Counts**: 226 records, all `scored`, all attempt 1 (113 per harness); no infrastructure
  loss, no `cap_truncated`; 226 of 226 plan cells final; no guest-server restart, no context
  fallback; 3,047 agent screenshot calls and 628 checker reads, none retried, slow or
  undelivered; no setup failure; **one postconfig failure**: a postconfig reply at HTTP 200
  with a non-zero return code during evaluation, which is recorded and is not a loss (section
  8; D56: a non-zero `returncode` under HTTP 200 is the agent's state, not a server error); no
  GPU device seen; teardown clean.
- **DR0** (`pair/dr0.json`, exit 0): `fires: false`, `base_complete: true`, 0 of 113
  first-attempt episodes lost in each (4B, harness) cell; records `0db38f8e...`, receipt
  `9fc15cfb...`, manifest `47aa3a2a...`.
- **Host while it ran**: the lane's three snapshots list only GPU job 1224 (load at most 2.55);
  the queue watcher's 148 samples (05:09:55-05:46:44) hold only 1222 and 1224.

### Collection

After each pair left the queue: its end states were recorded (`pair/slurm-state/`), then, from
the export, `python3 -E -s -B e-ops/job_checks_e.py NAME VM GPU > pair/job-checks.json` and
`e-ops/collect-pair-e.sh NAME VM GPU > pairs/NAME-collect.tar` (the registered DR0 command,
raw SHA-256 listings of both run directories, the evidence subset). Tars: E-9B-E1
`6cbbe68f...`, E-4B-E1 `0bb64dd8...`, unpacked here unchanged; the pair's `wait.log`,
`pre-submit-snapshot.txt` and `submit-run.out` were added from the host. Step logs, replies,
captures and engine logs stay on the host (section 20); the committed files hold no host
address.

Session E2 followed (below), each pair submitted only on an empty queue and after 17:51:33
UTC; R03 part (b), S2 v4 and R04 used the host in the gap (section 6.4, D85, D86).

## Session E2 (2026-10-12; `e-9b-e2/`, `e-4b-e2/`)

**Result, registered per-job checks only.** Both jobs of session E2 scored 226 of 226
episodes, with no infrastructure loss, no re-queue and no cap truncation, and **DR0 does not
fire for either** (`python -m harness.q2_stage1e.analysis dr0`, exit 0, `fires: false`, no
reasons). The lane's frozen-registration, prior-job, session-gap, engine-argv and Slurm-limit
checks passed for both, and no foreign Slurm job ran while either job ran. **No outcome was
read or summarized**: this section reads infrastructure fields only.

**Session E2's later end: 2026-10-12T19:12:47Z** (epoch 1791832367), E-4B-E2's end by
`lane.job_end`: the later of its lane's `t_end` (19:12:45.17) and its GPU job's recorded Slurm
EndTime (19:12:47). E-9B-E2 ended at 18:33:49 by the same rule. **Session E3 may not start
before 2026-10-13T07:17:47Z** (12 h 5 min later; `plan.session_not_before` on the four
receipts gives the same time). VM batch job 1254 ended at 19:12:50, 3 s after the GPU job,
inside the 5-minute margin (section 5.3).

### Waiting for the gap and a quiet host

This operator started at 05:55 UTC, after session E1 had ended, and submitted nothing until the
gap had passed. While waiting it prepared E-9B-E2 without touching Slurm: the pair directory
with `host.json` and `gpu-values.json` (E1's, with only `gpu_job_id_file` and `FILL_JOB`
changed), and the VM manifest rendered from the export at 05:57 UTC with `--prior-run-dirs`
naming runs 1219 and 1222 (`pair/e-9b-e2-vm.json`, SHA-256 `2d69bb16...`; canonical form
`0878b184...`). `lane validate` accepted it (226 slots) and `lane submit --dry-run` gave
`--begin=2026-10-12T17:51:33`, the lane's own earliest start. Nothing was queued ahead with a
future `--begin` (that would have held the queue against the other workstreams). It then polled
the host's queue about every 4 minutes. R04 (1225, 1230, 1234, 1235, 1239), R03 part (b)
(1227-1229) and S2 v4 (1240, 1242, 1244-1250) ran in the gap; the queue was empty at every poll
from 15:30 UTC on (no poll succeeded between 16:24 and 16:49 UTC, while this operator's own
network was down; nothing of E's was pending or running then). Before submitting, at 17:42 UTC,
it re-checked the export against `git archive f6144d6b` (every regular file's SHA-256, 7,602
files; the 27 symlinks and their targets; `.git_sha`; no writable file or directory but the
symlinks) and the five operator scripts on the host against the committed ones (equal by
SHA-256), and found no operator process left on the host.

### E-9B-E2 (`e-9b-e2/`: VM job 1251, GPU job 1253)

- **Host before submission** (`pair/pre-submit-snapshot.txt`, 17:53:06 UTC, after the gap
  had passed at 17:51:33): `squeue -a` empty, load 0.01, one container (the local registry),
  every GPU at 0 MiB.
- **Submission** (`wait-then-submit-pair-e.sh e-9b-e2` under `nohup setsid` on the host, as in
  session E1; `pair/submit-run.out`, `pair/ops.log`): verify and `check-chain` PASS in the
  export (row 19, file SHA-256 `47e65877...`, 19 rows; `pair/preregister-verify.txt`); `lane
  validate` ok (226 slots); `lane submit --dry-run` (`--time=01:02:00
  --begin=2026-10-12T17:51:33`); a placeholder GPU half through the submitter's `--dry-run`;
  queue empty; VM job 1251 at 17:53:07, its `--begin` already past; the GPU half rendered from
  the validated VM manifest (`pair/e-9b-e2-gpu.yaml`, `94f7dd72...`: 9B, 52 minutes, the OE
  overlay, the freeze commit, OE's archive, the 9B receipt `0a9e052d...` and artifact root
  `9845026d...`, as in E-9B-E1); dry run `--time=00:52:00 --signal=B:USR1@180
  --dependency=after:1251`, 0.8667 GPU-h budget; `--test-only` exit 0 (id 1252); no foreign
  job; GPU job 1253 at 17:53:07.
- **The lane's checks** (`pair/job-checks.json`, from `ops/job_checks_e.py`):
  - manifest: purpose `e`, plan `4e7298a7...`, 226 slots equal to `plan.slots(9B, E2)`, V 20,
    GPU cap 52, VM limit 62 minutes, 90 CPUs; `e.prior_jobs` names E-9B-E1 (records
    `278e8112...`, receipt `32a4a1f7...`) and E-4B-E1 (records `0db38f8e...`, receipt
    `9fc15cfb...`), which the lane accepted at submission and at job start, DR0 included;
  - session gap: the lane's earliest start 17:51:33 (E1's later end 05:46:33 plus 12 h 5 min);
    the VM job started at 17:53:07 and the engine wait after it;
  - preflight (`vm-1251/preflight.txt`): batch `2d27bbe5...` (`q2e-vm.sbatch`), manifest
    `0878b184...`, source git SHA `f6144d6b...`, TRES `cpu=90,mem=126G` with no GRES, lane
    exit 0, no labelled container left;
  - provenance: `gpu-1253/provenance-verification.txt` PASS, `git_sha` `f6144d6b...` and
    `source_sha256` `6ad9ad67...` equal to the GPU manifest's; image the OE overlay
    `5d1d4d8f...`; model verification: `qwen3.5-9b` at `c2022362...`, root `9845026d...`;
  - engine argv: `ready.json`'s argv equals S1a's `plan.engine_argv` for 9B (SHA-256
    `9b307cdc...`); the bridge started 15.4 s after the Slurm start and the engine was ready
    98.6 s later;
  - Slurm limit: the lane read TimeLimit 52 minutes, equal to the cap; USR1 point = Slurm start
    (17:53:08) + 52 min - 180 s (18:42:08);
  - receipt: no error, not stopped; first dispatch 114.3 s after the GPU job's Slurm start
    (1.1 s more than the L = 113.19 s the caps assume, section 7.1; no rule reads it); lane end
    8.4 minutes before the USR1 point; the engine stopped on `vm_done`, return code 0;
    termination `completed`, no container killed.
- **Counts**: 226 slots dispatched, 226 records, every one `scored`, every one attempt 1 (113
  per harness); no infrastructure loss, no `cap_truncated`; 226 of 226 plan cells final; no
  guest-server restart; no context fallback; observations: 2,975 agent screenshot calls and
  626 checker reads, none retried, slower than 30 s or undelivered; no setup failure, no
  postconfig failure; no GPU device seen in an episode container; every container gone at
  teardown, no leaked volume.
- **DR0** (`pair/dr0.json`, exit 0): `fires: false`, `base_complete: true`, 0 of 113
  first-attempt episodes lost in each (9B, harness) cell; records `e8755336...`, receipt
  `e1664285...`, manifest `ce4a0d86...`.
- **Host while it ran**: the lane's three snapshots (start, block `e1`, end) list no foreign
  job (load at most 1.08); the 15-second queue watcher's 163 samples (17:53:07-18:33:41, then
  one empty sample at 18:33:56) hold only 1251 and 1253.

### E-4B-E2 (`e-4b-e2/`: VM job 1254, GPU job 1256)

- **Manifest** (rendered after E-9B-E2 left the queue and its DR0 was read):
  `render_q2e_manifest.py vm --host pair/host.json --size 4B --session E2 --prior-run-dirs
  runs/1219 runs/1222 runs/1251` from the export (`pair/e-4b-e2-vm.json`, SHA-256
  `55bdc447...`; canonical form `876361d7...`): 226 slots, V 20, GPU cap 48, VM limit 58
  minutes, 90 CPUs, prompt date 2026-10-08, plan `4e7298a7...`; `e.prior_jobs` names E-9B-E1,
  E-4B-E1 and E-9B-E2 by records and receipt (E-9B-E2's `e8755336...` and `e1664285...`, the
  digests DR0 had just read). `lane validate` ok.
- **Host before submission** (`pair/pre-submit-snapshot.txt`, 18:36:39 UTC): `squeue -a`
  empty, load 0.08 (falling after E-9B-E2), one container (the local registry), every GPU at
  0 MiB.
- **Submission** (the same script, 18:36:39-18:36:41; `pair/submit-run.out`): verify and
  `check-chain` PASS; `lane submit --dry-run` (`--time=00:58:00 --begin=2026-10-12T17:51:33`);
  VM job 1254 at 18:36:41; GPU half `pair/e-4b-e2-gpu.yaml` (`2abccad2...`: 4B, 48 minutes,
  the OE overlay, the 4B receipt `75ebfc53...` and artifact root `3b8a0751...`, as in E-4B-E1,
  D57 (i)); dry run `--time=00:48:00 --signal=B:USR1@180 --dependency=after:1254`, 0.8 GPU-h
  budget; `--test-only` exit 0 (id 1255); no foreign job; GPU job 1256 at 18:36:41.
- **The lane's checks** (`pair/job-checks.json`):
  - manifest: 226 slots equal to `plan.slots(4B, E2)`; the three prior jobs by both digests,
    which the lane accepted at submission and at job start;
  - preflight: batch `2d27bbe5...`, manifest `876361d7...`, source `f6144d6b...`, no GRES,
    lane exit 0, no labelled container left;
  - provenance PASS (`f6144d6b...`, `6ad9ad67...`, equal to the GPU manifest's); model
    verification: `qwen3.5-4b` at `851bf6e8...`, root `3b8a0751...`;
  - engine argv equals S1a's `plan.engine_argv` for 4B (SHA-256 `1c4cffba...`); the bridge
    started 8.1 s after the Slurm start and the engine was ready 96.1 s later;
  - Slurm limit: TimeLimit 48 minutes, equal to the cap; USR1 point = 18:36:44 + 48 min - 180 s
    (19:21:44);
  - receipt: no error, not stopped; first dispatch 104.5 s after the Slurm start; lane end 9.0
    minutes before the USR1 point; engine stopped on `vm_done`, return code 0; termination
    `completed`.
- **Counts**: 226 records, all `scored`, all attempt 1 (113 per harness); no infrastructure
  loss, no `cap_truncated`; 226 of 226 plan cells final; no guest-server restart, no context
  fallback; 3,106 agent screenshot calls and 629 checker reads, none retried, slow or
  undelivered; no setup failure; **one postconfig failure**: a postconfig command reply at HTTP
  200 with a non-zero return code during evaluation, which is recorded and is not a loss
  (section 8; D56: a non-zero `returncode` under HTTP 200 is the agent's state, not a server
  error), the same kind as E-4B-E1's; no postconfig reply at HTTP 500 or above or without a
  reply; no GPU device seen; teardown clean.
- **DR0** (`pair/dr0.json`, exit 0): `fires: false`, `base_complete: true`, 0 of 113
  first-attempt episodes lost in each (4B, harness) cell; records `09de5e82...`, receipt
  `5f27ccd6...`, manifest `7ae67eda...`.
- **Host while it ran**: the lane's three snapshots list no foreign job (load at most 3.11);
  the queue watcher's 145 samples (18:36:41-19:12:44, then one empty sample at 19:12:59) hold
  only 1254 and 1256. The next job on the host, S2 v4's 1257, was submitted at 19:13:59.

### Collection

As in session E1: after each pair left the queue its end states were recorded
(`pair/slurm-state/`), then, from the export, `job_checks_e.py NAME VM GPU >
pair/job-checks.json` and `collect-pair-e.sh NAME VM GPU > pairs/NAME-collect.tar` (the
registered DR0 command, raw SHA-256 listings of both run directories, the evidence subset).
Tars: E-9B-E2 `5a27de56...`, E-4B-E2 `71d20db9...`, unpacked here unchanged; the pair's
`wait.log`, `pre-submit-snapshot.txt` and `submit-run.out` were added from the host. Step logs,
replies, captures and engine logs stay on the host (section 20); the committed files hold no
host address.

Session E3 followed (below), each pair submitted only on an empty queue and after 07:17:50 UTC
on 2026-10-13; S2 v4's K1 jobs 1257-1264 used the host in the gap (section 6.4, D85, D91,
D93).

## Session E3 (2026-10-13; `e-9b-e3/`, `e-4b-e3/`)

**Result, registered per-job checks only.** Both jobs of session E3 scored 226 of 226
episodes, with no infrastructure loss, no re-queue and no cap truncation, and **DR0 does not
fire for either** (`python -m harness.q2_stage1e.analysis dr0`, exit 0, `fires: false`, no
reasons). The lane's frozen-registration, prior-job, session-gap, engine-argv and Slurm-limit
checks passed for both, and no foreign Slurm job ran while either job ran. **No outcome was
read or summarized**: this section reads infrastructure fields only.

**Session E3's later end: 2026-10-13T08:36:07Z** (epoch 1791880567), E-4B-E3's end by
`lane.job_end`: the later of its lane's `t_end` (08:36:05.03) and its GPU job's recorded Slurm
EndTime (08:36:07). E-9B-E3 ended at 07:56:53 by the same rule. **Session E4 may not start
before 2026-10-13T20:41:07Z** (12 h 5 min later; `plan.session_not_before` on the six
receipts gives the same time). VM batch job 1268 ended at 08:36:10, 3 s after the GPU job,
inside the 5-minute margin (section 5.3), so 20:41:10Z also satisfies the VM-batch reading.

### Waiting for the gap and a quiet host

The orchestrating session restarted twice before session E3 (the operator's own Mac crashed).
An earlier E3 operator instance had prepared both pair directories at 19:23 UTC on 2026-10-12
without touching Slurm: `host.json` and `gpu-values.json` for each (E2's, with only
`gpu_job_id_file` and `FILL_JOB` changed) and E-9B-E3's VM manifest, rendered from the export
with `--prior-run-dirs` naming runs 1219, 1222, 1251 and 1254 (`pair/e-9b-e3-vm.json`, SHA-256
`79cbf8d3...`; canonical form `ee1e4546...`), with `lane validate` (226 slots) and `lane submit
--dry-run` (`--begin=2026-10-13T07:17:47`) kept on the host as `prep-lane-validate.json` and
`prep-vm-submit-dry-run.json`. This operator started at 00:06 UTC on 2026-10-13 and checked the
host before anything else: the queue empty, no E3 run directory (the run root held only runs
1206, 1219, 1222, 1251 and 1254), no `vm-submit.json` or `gpu_job_id` in either E3 pair
directory and no operator process, so nothing of E3 had been submitted. It re-rendered
E-9B-E3's manifest from the export with the same arguments and got a byte-identical file, and
found the five operator scripts on the host equal to the committed ones by SHA-256. `main`
(D93, S2 v4's K1 jobs) was merged into the branch first, every ledger row kept (21 rows).

It then polled the host's queue about every 4 minutes from 00:07 to 07:15 UTC; the queue was
empty at every poll (S2 v4's K1 jobs 1257-1264 had ended at 22:45 UTC on 2026-10-12, D93).
At 06:39 UTC it re-checked the export against `git archive f6144d6b`, taken from the OE clone
(tree `b8d37e7f...`): every regular file's SHA-256 equal (7,602 files), the 27 symlinks and
their targets equal, `.git_sha` naming `f6144d6b...`, no writable file or directory but the
symlinks. It checked that the four earlier jobs' records and receipts still had the digests
E-9B-E3's manifest names. Nothing was queued ahead of the gap.

### E-9B-E3 (`e-9b-e3/`: VM job 1265, GPU job 1267)

- **Host before submission** (`pair/pre-submit-snapshot.txt`, 07:18:00 UTC, after both
  readings of the gap had passed, 07:17:47 by `lane.job_end` and 07:17:50 by E-4B-E2's VM
  batch end): `squeue -a` empty, load 0.01, one container (the local registry), every GPU at
  0 MiB.
- **Submission** (`wait-then-submit-pair-e.sh e-9b-e3` under `nohup setsid` on the host, as in
  sessions E1 and E2; `pair/submit-run.out`, `pair/ops.log`): verify and `check-chain` PASS in
  the export (row 19, file SHA-256 `47e65877...`, 19 rows; `pair/preregister-verify.txt`); `lane
  validate` ok (226 slots); `lane submit --dry-run` (`--time=01:02:00
  --begin=2026-10-13T07:17:47`); a placeholder GPU half through the submitter's `--dry-run`;
  queue empty; VM job 1265 at 07:18:02, its `--begin` already past; the GPU half rendered from
  the validated VM manifest (`pair/e-9b-e3-gpu.yaml`, `1e80ed2a...`: 9B, 52 minutes, the OE
  overlay, the freeze commit, OE's archive, the 9B receipt `0a9e052d...` and artifact root
  `9845026d...`, as in E-9B-E1 and E-9B-E2); dry run `--time=00:52:00 --signal=B:USR1@180
  --dependency=after:1265`, 0.8667 GPU-h budget; `--test-only` exit 0 (id 1266; `sbatch`
  estimated a start at 08:20:02, the VM job's limit, an estimate only); no foreign job; GPU job
  1267 at 07:18:02, which started at once with the VM job.
- **The lane's checks** (`pair/job-checks.json`, from `ops/job_checks_e.py`):
  - manifest: purpose `e`, plan `4e7298a7...`, 226 slots equal to `plan.slots(9B, E3)`, V 20,
    GPU cap 52, VM limit 62 minutes, 90 CPUs; `e.prior_jobs` names E-9B-E1, E-4B-E1, E-9B-E2
    and E-4B-E2 by records and receipt (E-4B-E2's `09de5e82...` and `5f27ccd6...`), which the
    lane accepted at submission and at job start, DR0 included;
  - session gap: the lane's earliest start 07:17:47 (E2's later end 19:12:47 plus 12 h 5 min);
    the VM job started at 07:18:02 and the engine wait after it;
  - preflight (`vm-1265/preflight.txt`): batch `2d27bbe5...` (`q2e-vm.sbatch`), manifest
    `ee1e4546...`, source git SHA `f6144d6b...`, TRES `cpu=90,mem=126G` with no GRES, lane
    exit 0, no labelled container left;
  - provenance: `gpu-1267/provenance-verification.txt` PASS, `git_sha` `f6144d6b...` and
    `source_sha256` `6ad9ad67...` equal to the GPU manifest's; image the OE overlay
    `5d1d4d8f...`; model verification: `qwen3.5-9b` at `c2022362...`, root `9845026d...`;
  - engine argv: `ready.json`'s argv equals S1a's `plan.engine_argv` for 9B (SHA-256
    `9b307cdc...`); the bridge started 16.0 s after the Slurm start and the engine was ready
    97.6 s later;
  - Slurm limit: the lane read TimeLimit 52 minutes, equal to the cap; USR1 point = Slurm start
    (07:18:02) + 52 min - 180 s (08:07:02);
  - receipt: no error, not stopped; first dispatch 113.7 s after the GPU job's Slurm start
    (0.5 s more than the L = 113.19 s the caps assume, section 7.1; no rule reads it); lane end
    10.2 minutes before the USR1 point; the engine stopped on `vm_done`, return code 0;
    termination `completed`, no container killed.
- **Counts**: 226 slots dispatched, 226 records, every one `scored`, every one attempt 1 (113
  per harness); no infrastructure loss, no `cap_truncated`; 226 of 226 plan cells final; no
  guest-server restart; no context fallback; observations: 3,059 agent screenshot calls and
  628 checker reads, none retried, slower than 30 s or undelivered; no setup failure, no
  postconfig failure (every postconfig reply at HTTP 200); no GPU device seen in an episode
  container; every container gone at teardown, no leaked volume.
- **DR0** (`pair/dr0.json`, exit 0): `fires: false`, `base_complete: true`, 0 of 113
  first-attempt episodes lost in each (9B, harness) cell; records `d2fb985b...`, receipt
  `bc30d8e2...`, manifest `7ab8f0fa...`.
- **Host while it ran**: the lane's three snapshots (start, block `e1`, end) list no foreign
  job (load at most 2.53); the 15-second queue watcher's 156 samples (07:18:02-07:56:51, then
  one empty sample at 07:57:06) hold only 1265 and 1267.

### E-4B-E3 (`e-4b-e3/`: VM job 1268, GPU job 1270)

- **Manifest** (rendered at 07:58 UTC, after E-9B-E3 left the queue and its DR0 was read):
  `render_q2e_manifest.py vm --host pair/host.json --size 4B --session E3 --prior-run-dirs
  runs/1219 runs/1222 runs/1251 runs/1254 runs/1265` from the export (`pair/e-4b-e3-vm.json`,
  SHA-256 `9e9c9efc...`; canonical form `bd61a484...`): 226 slots, V 20, GPU cap 48, VM limit
  58 minutes, 90 CPUs, prompt date 2026-10-08, plan `4e7298a7...`; `e.prior_jobs` names the
  five earlier E jobs by records and receipt (E-9B-E3's `d2fb985b...` and `bc30d8e2...`, the
  digests DR0 had just read). `lane validate` ok.
- **Host before submission** (`pair/pre-submit-snapshot.txt`, 07:58:40 UTC): `squeue -a`
  empty, load 0.63 (falling after E-9B-E3), one container (the local registry), every GPU at
  0 MiB.
- **Submission** (the same script, 07:58:40-07:58:42; `pair/submit-run.out`): verify and
  `check-chain` PASS; `lane submit --dry-run` (`--time=00:58:00 --begin=2026-10-13T07:17:47`);
  VM job 1268 at 07:58:41; GPU half `pair/e-4b-e3-gpu.yaml` (`a679c6d8...`: 4B, 48 minutes,
  the OE overlay, the 4B receipt `75ebfc53...` and artifact root `3b8a0751...`, as in E-4B-E1
  and E-4B-E2, D57 (i)); dry run `--time=00:48:00 --signal=B:USR1@180 --dependency=after:1268`,
  0.8 GPU-h budget; `--test-only` exit 0 (id 1269); no foreign job; GPU job 1270 at 07:58:42.
- **The lane's checks** (`pair/job-checks.json`):
  - manifest: 226 slots equal to `plan.slots(4B, E3)`; the five prior jobs by both digests,
    which the lane accepted at submission and at job start;
  - preflight: batch `2d27bbe5...`, manifest `bd61a484...`, source `f6144d6b...`, no GRES,
    lane exit 0, no labelled container left;
  - provenance PASS (`f6144d6b...`, `6ad9ad67...`, equal to the GPU manifest's); model
    verification: `qwen3.5-4b` at `851bf6e8...`, root `3b8a0751...`;
  - engine argv equals S1a's `plan.engine_argv` for 4B (SHA-256 `1c4cffba...`); the bridge
    started 8.3 s after the Slurm start and the engine was ready 96.6 s later;
  - Slurm limit: TimeLimit 48 minutes, equal to the cap; USR1 point = 07:58:45 + 48 min - 180 s
    (08:43:45);
  - receipt: no error, not stopped; first dispatch 105.4 s after the Slurm start; lane end 7.7
    minutes before the USR1 point; engine stopped on `vm_done`, return code 0; termination
    `completed`, no container killed.
- **Counts**: 226 records, all `scored`, all attempt 1 (113 per harness); no infrastructure
  loss, no `cap_truncated`; 226 of 226 plan cells final; no guest-server restart, no context
  fallback; 3,115 agent screenshot calls and 627 checker reads, none retried, slow or
  undelivered; no setup failure; **two postconfig failures**, in two episodes, each a
  postconfig command reply at HTTP 200 with a non-zero return code during evaluation, which is
  recorded and is not a loss (section 8; D56: a non-zero `returncode` under HTTP 200 is the
  agent's state, not a server error), the same kind as E-4B-E1's and E-4B-E2's; every
  postconfig reply of both E3 jobs was HTTP 200, so none was at HTTP 500 or above or without a
  reply; no GPU device seen; teardown clean.
- **DR0** (`pair/dr0.json`, exit 0): `fires: false`, `base_complete: true`, 0 of 113
  first-attempt episodes lost in each (4B, harness) cell; records `2af9f2be...`, receipt
  `d80eaa91...`, manifest `4729afd0...`.
- **Host while it ran**: the lane's three snapshots list no foreign job (load at most 5.71);
  the queue watcher's 150 samples (07:58:42-08:36:01, then one empty sample at 08:36:16) hold
  only 1268 and 1270. The next job on the host, S2 v5's 1271, was submitted at 08:37:17.

### Collection

As in sessions E1 and E2: after each pair left the queue its end states were recorded
(`pair/slurm-state/`), then, from the export, `job_checks_e.py NAME VM GPU >
pair/job-checks.json` and `collect-pair-e.sh NAME VM GPU > pairs/NAME-collect.tar` (the
registered DR0 command, raw SHA-256 listings of both run directories, the evidence subset).
Tars: E-9B-E3 `0c2ac0cc...`, E-4B-E3 `afb4b470...`, unpacked here unchanged; the pair's
`wait.log`, `pre-submit-snapshot.txt` and `submit-run.out` were added from the host. Step logs,
replies, captures and engine logs stay on the host (section 20); the committed files hold no
host address.

Session E4 followed (below), each pair submitted only on an empty queue and after 20:41:10 UTC
on 2026-10-13; S2 v5's step 0 (job 1271, CPU only) used the host in the gap (section 6.4, D85,
D94, D96).

## Session E4 (2026-10-13; `e-9b-e4/`, `e-4b-e4/`)

**Result, registered per-job checks only.** Both jobs of session E4 scored 226 of 226
episodes, with no infrastructure loss, no re-queue and no cap truncation, and **DR0 does not
fire for either** (`python -m harness.q2_stage1e.analysis dr0`, exit 0, `fires: false`, no
reasons). The lane's frozen-registration, prior-job, session-gap, engine-argv and Slurm-limit
checks passed for both, and no foreign Slurm job ran while either job ran. **No outcome was
read or summarized**: this section reads infrastructure fields only. Session E4 was E's last;
all eight registered E jobs have now run, and none fired DR0.

**Session E4's later end: 2026-10-13T21:58:03Z** (epoch 1791928683), E-4B-E4's end by
`lane.job_end`: the later of its lane's `t_end` (21:58:01.58) and its GPU job's recorded Slurm
EndTime (21:58:03). E-9B-E4 ended at 21:20:14 by the same rule. VM batch job 1275 ended at
21:58:06, 3 s after the GPU job, inside the 5-minute margin (section 5.3).

### Waiting for the gap and a quiet host

The orchestrating session had restarted twice before session E3 (the operator's Mac crashed);
the E3 operator's report was the handover. This operator started at 08:41 UTC on 2026-10-13,
after session E3 had ended, and checked the host first: S2 v5's step-0 job 1271 (CPU only, no
GRES) running, no E4 pair or run directory, no operator process; the five operator scripts on
the host equal to the committed ones by SHA-256; the six earlier E jobs' records and receipts
at the digests their DR0 reads and E-4B-E3's manifest name. At 08:43 UTC it prepared E-9B-E4
without touching Slurm: both pair directories with `host.json` and `gpu-values.json` (E3's,
with only `gpu_job_id_file` and `FILL_JOB` changed) and E-9B-E4's VM manifest, rendered from
the export with `--prior-run-dirs` naming runs 1219, 1222, 1251, 1254, 1265 and 1268
(`pair/e-9b-e4-vm.json`, SHA-256 `c181d0aa...`; canonical form `72a0f39a...`); `lane validate`
accepted it (226 slots) and `lane submit --dry-run` gave `--begin=2026-10-13T20:41:07`, the
lane's own earliest start. Nothing was queued ahead.

It then polled the host's queue about every 4 minutes from 08:47 to 20:41 UTC, 189 polls logged
on the host (one more, at about 09:15, failed on an ssh connection timeout). Job 1271 was
running at the nine polls up to 09:17 and had left the queue by 09:21; the queue was empty at
all 180 polls from 09:21 UTC on. `main` (D96: S2 v5's step 0 read (a)) was merged into the
branch at 17:43 UTC, every ledger row kept (21 rows). At 19:33 UTC it re-checked the export
against `git archive f6144d6b`, taken from the OE clone (detached at `f6144d6b`, tree
`b8d37e7f...`, `git status` empty): every regular file's SHA-256 equal (7,602 files), the 27
symlinks and their targets equal, `.git_sha` naming `f6144d6b...`, no writable file or directory
but the symlinks.

### E-9B-E4 (`e-9b-e4/`: VM job 1272, GPU job 1274)

- **Host before submission** (`pair/pre-submit-snapshot.txt`, 20:41:26 UTC, after both
  readings of the gap had passed, 20:41:07 by `lane.job_end` and 20:41:10 by E-4B-E3's VM
  batch end): `squeue -a` empty, load 0.03, one container (the local registry), every GPU at
  0 MiB.
- **Submission** (`wait-then-submit-pair-e.sh e-9b-e4` under `nohup setsid` on the host, as in
  sessions E1-E3, started by a guard that refused to run before 20:41:10 UTC, with an earlier
  submission file present, with an operator process running or with a non-empty queue;
  `pair/submit-run.out`, `pair/ops.log`): verify and `check-chain` PASS in the export (row 19,
  file SHA-256 `47e65877...`, 19 rows; `pair/preregister-verify.txt`); `lane validate` ok (226
  slots); `lane submit --dry-run` (`--time=01:02:00 --begin=2026-10-13T20:41:07`); a
  placeholder GPU half through the submitter's `--dry-run`; queue empty; VM job 1272 at
  20:41:27, its `--begin` already past; the GPU half rendered from the validated VM manifest
  (`pair/e-9b-e4-gpu.yaml`, `b7daa8e6...`: 9B, 52 minutes, the OE overlay, the freeze commit,
  OE's archive, the 9B receipt `0a9e052d...` and artifact root `9845026d...`, as in E-9B-E1 to
  E-9B-E3); dry run `--time=00:52:00 --signal=B:USR1@180 --dependency=after:1272`, 0.8667
  GPU-h budget; `--test-only` exit 0 (id 1273; `sbatch` estimated a start at 21:43:28, the VM
  job's limit, an estimate only, as for E-9B-E3); no foreign job; GPU job 1274 at 20:41:28,
  which started at once with the VM job.
- **The lane's checks** (`pair/job-checks.json`, from `ops/job_checks_e.py`):
  - manifest: purpose `e`, plan `4e7298a7...`, 226 slots equal to `plan.slots(9B, E4)`, V 20,
    GPU cap 52, VM limit 62 minutes, 90 CPUs; `e.prior_jobs` names E-9B-E1, E-4B-E1, E-9B-E2,
    E-4B-E2, E-9B-E3 and E-4B-E3 by records and receipt (E-4B-E3's `2af9f2be...` and
    `d80eaa91...`), which the lane accepted at submission and at job start, DR0 included;
  - session gap: the lane's earliest start 20:41:07 (E3's later end 08:36:07 plus 12 h 5 min);
    the VM job started at 20:41:28 and the engine wait after it;
  - preflight (`vm-1272/preflight.txt`): batch `2d27bbe5...` (`q2e-vm.sbatch`), manifest
    `72a0f39a...`, source git SHA `f6144d6b...`, TRES `cpu=90,mem=126G` with no GRES, lane
    exit 0, no labelled container left;
  - provenance: `gpu-1274/provenance-verification.txt` PASS, `git_sha` `f6144d6b...` and
    `source_sha256` `6ad9ad67...` equal to the GPU manifest's; image the OE overlay
    `5d1d4d8f...`; model verification: `qwen3.5-9b` at `c2022362...`, root `9845026d...`;
  - engine argv: `ready.json`'s argv equals S1a's `plan.engine_argv` for 9B (SHA-256
    `9b307cdc...`); the bridge started 15.6 s after the Slurm start and the engine was ready
    97.1 s later;
  - Slurm limit: the lane read TimeLimit 52 minutes, equal to the cap; USR1 point = Slurm start
    (20:41:28) + 52 min - 180 s (21:30:28);
  - receipt: no error, not stopped; first dispatch 113.0 s after the GPU job's Slurm start
    (within the L = 113.19 s the caps assume, section 7.1); lane end 10.3 minutes before the
    USR1 point; the engine stopped on `vm_done`, return code 0; termination `completed`, no
    container killed.
- **Counts**: 226 slots dispatched, 226 records, every one `scored`, every one attempt 1 (113
  per harness); no infrastructure loss, no `cap_truncated`; 226 of 226 plan cells final; no
  guest-server restart; no context fallback; observations: 2,924 agent screenshot calls and
  630 checker reads, none retried, slower than 30 s or undelivered; no setup failure, no
  postconfig failure (all 376 postconfig replies at HTTP 200); no GPU device seen in an
  episode container; every container gone at teardown, no leaked volume.
- **DR0** (`pair/dr0.json`, exit 0): `fires: false`, `base_complete: true`, 0 of 113
  first-attempt episodes lost in each (9B, harness) cell; records `014b4689...`, receipt
  `79a11458...`, manifest `186245a9...`.
- **Host while it ran**: the lane's three snapshots (start, block `e1`, end) list no foreign
  job (load at most 1.69); the 15-second queue watcher's 156 samples (20:41:28-21:20:16, then
  one empty sample at 21:20:31) hold only 1272 and 1274.

### E-4B-E4 (`e-4b-e4/`: VM job 1275, GPU job 1277)

- **Manifest** (rendered at 21:21 UTC, after E-9B-E4 left the queue and its DR0 was read):
  `render_q2e_manifest.py vm --host pair/host.json --size 4B --session E4 --prior-run-dirs
  runs/1219 runs/1222 runs/1251 runs/1254 runs/1265 runs/1268 runs/1272` from the export
  (`pair/e-4b-e4-vm.json`, SHA-256 `999407e5...`; canonical form `75c20528...`): 226 slots, V 20,
  GPU cap 48, VM limit 58 minutes, 90 CPUs, prompt date 2026-10-08, plan `4e7298a7...`;
  `e.prior_jobs` names the seven earlier E jobs by records and receipt (E-9B-E4's
  `014b4689...` and `79a11458...`, the digests DR0 had just read). `lane validate` ok.
- **Host before submission** (`pair/pre-submit-snapshot.txt`, 21:21:43 UTC): `squeue -a`
  empty, load 0.56 (falling after E-9B-E4), one container (the local registry), every GPU at
  0 MiB.
- **Submission** (the same guard and script, 21:21:43-21:21:45; `pair/submit-run.out`): verify
  and `check-chain` PASS; `lane submit --dry-run` (`--time=00:58:00
  --begin=2026-10-13T20:41:07`); VM job 1275 at 21:21:45; GPU half `pair/e-4b-e4-gpu.yaml`
  (`de458508...`: 4B, 48 minutes, the OE overlay, the 4B receipt `75ebfc53...` and artifact
  root `3b8a0751...`, as in E-4B-E1 to E-4B-E3, D57 (i)); dry run `--time=00:48:00
  --signal=B:USR1@180 --dependency=after:1275`, 0.8 GPU-h budget; `--test-only` exit 0 (id
  1276); no foreign job; GPU job 1277 at 21:21:45.
- **The lane's checks** (`pair/job-checks.json`):
  - manifest: 226 slots equal to `plan.slots(4B, E4)`; the seven prior jobs by both digests,
    which the lane accepted at submission and at job start;
  - preflight: batch `2d27bbe5...`, manifest `75c20528...`, source `f6144d6b...`, no GRES,
    lane exit 0, no labelled container left;
  - provenance PASS (`f6144d6b...`, `6ad9ad67...`, equal to the GPU manifest's); model
    verification: `qwen3.5-4b` at `851bf6e8...`, root `3b8a0751...`;
  - engine argv equals S1a's `plan.engine_argv` for 4B (SHA-256 `1c4cffba...`); the bridge
    started 8.7 s after the Slurm start and the engine was ready 97.1 s later;
  - Slurm limit: TimeLimit 48 minutes, equal to the cap; USR1 point = 21:21:45 + 48 min - 180 s
    (22:06:45);
  - receipt: no error, not stopped; first dispatch 105.9 s after the Slurm start; lane end 8.7
    minutes before the USR1 point; engine stopped on `vm_done`, return code 0; termination
    `completed`, no container killed.
- **Counts**: 226 records, all `scored`, all attempt 1 (113 per harness); no infrastructure
  loss, no `cap_truncated`; 226 of 226 plan cells final; no guest-server restart, no context
  fallback; 3,091 agent screenshot calls and 627 checker reads, none retried, slow or
  undelivered; no setup failure; **two postconfig failures**, in two episodes, each a
  postconfig command reply at HTTP 200 with a non-zero return code during evaluation, which is
  recorded and is not a loss (section 8; D56: a non-zero `returncode` under HTTP 200 is the
  agent's state, not a server error), the same kind as E-4B-E1's to E-4B-E3's; all 376
  postconfig replies of each E4 job were HTTP 200, so none was at HTTP 500 or above or without
  a reply; no GPU device seen; teardown clean.
- **DR0** (`pair/dr0.json`, exit 0): `fires: false`, `base_complete: true`, 0 of 113
  first-attempt episodes lost in each (4B, harness) cell; records `36aaccee...`, receipt
  `11a59b7e...`, manifest `45c0882d...`.
- **Host while it ran**: the lane's three snapshots list no foreign job (load at most 2.63);
  the queue watcher's 146 samples (21:21:45-21:58:03, then one empty sample at 21:58:19) hold
  only 1275 and 1277. Nothing else was submitted to the host by this operator after the pair.

### Collection

As in sessions E1-E3: after each pair left the queue its end states were recorded
(`pair/slurm-state/`), then, from the export, `job_checks_e.py NAME VM GPU >
pair/job-checks.json` and `collect-pair-e.sh NAME VM GPU > pairs/NAME-collect.tar` (the
registered DR0 command, raw SHA-256 listings of both run directories, the evidence subset).
Tars: E-9B-E4 `9209328c...`, E-4B-E4 `e0d4ee7e...`, unpacked here unchanged; the pair's
`wait.log`, `pre-submit-snapshot.txt` and `submit-run.out` were added from the host. Step logs,
replies, captures and engine logs stay on the host (section 20); the committed files hold no
host address.

Next: E's registered analysis (section 18 (iii)), on the records of all eight E jobs: offline
rescoring (one CPU job per E job), the cost card, the report, the section 15 items, the GLMM,
the joint reading and the provenance record, then a fresh verifier before RESULTS. Every E job
has run and none fired DR0.

The analysis ran on 2026-10-13/14 UTC (CPU jobs 1279-1290; `analysis/README.md`); its
readings are in `RESULTS.md`: DR2 Near-equivalent, DR5 NO-GO, DR1 and DR4 do not fire, P2-P5
not falsified, P1 not estimable. The fresh verifier had not run when `RESULTS.md` was first
written (its deviation 1). It ran afterwards and reproduced every registered output and
outcome (`analysis/verification/verifier-record.json`), and `RESULTS.md` was corrected for
the wording and disclosure items it raised.

## Operator scripts (`ops/`)

None is code of record; none runs inside a job. Each was copied to the host's
`~/cotcodec-runs/stage0/q2-stage1e/e-ops/` (read-only) and run from there; the SHA-256s there
equal the committed files'.

| Script | What |
|---|---|
| `oe-wait-submit.sh` | OE: checks the clean clone, the builder's and extractor's digests and the archive, waits for an empty queue (2 s polls, at most about 200 s per invocation), submits the build, starts the end-state and queue watchers |
| `submit-pair-e.sh` | one E pair: S1a's `submit-pair.sh` with E's registration, lane, renderer and paths; verify and `check-chain`, `lane validate`, `lane submit --dry-run`, a placeholder GPU half through the submitter's `--dry-run`, an empty-queue wait (at most about 180 s), the VM job, the GPU half rendered from the validated VM manifest with the VM job's id, the submitter's dry run, `--test-only`, a foreign-queue check, the GPU job (`--dependency=after:` the VM job), the watchers |
| `wait-then-submit-pair-e.sh` | polls the queue (2 s, at most about 200 s per invocation) and runs `submit-pair-e.sh` only once it is empty; one line per busy invocation in the pair's `wait.log` |
| `collect-pair-e.sh` | after a pair: the registered DR0 command (section 18 (iii) step 1), raw SHA-256 listings of both run directories, and the evidence subset |
| `job_checks_e.py` | after a pair: the lane's checks re-read from its records (provenance, model verification, engine argv, Slurm limit and USR1 point, receipt, counts, losses, completeness against the plan, restarts, observations, devices, teardown, the session end by `lane.job_end`, physical run times); infrastructure fields only |

## Disclosures

- **The export's `.git_sha`.** The export adds one file to `git archive f6144d6b`: `.git_sha`,
  naming the commit, as the G-E4 export did; `q2e-vm.sbatch`'s preflight prints it. The lane's
  source-tree digest covers `harness/` only.
- **Operator handover in session E1.** The operator that ran OE stopped polling at 03:18 UTC
  with nothing of E-9B-E1 submitted; the next operator resumed at 04:25, found no leftover
  operator process and an empty queue, and submitted on the first check. The registration does
  not time session E1, so this is a disclosure, not a deviation.
- **Session E2's wait.** The E2 operator lost its own network connection to the host between
  about 16:24 and 16:49 UTC on 2026-10-12, while waiting for the gap (nothing of E's was pending
  or running); its queue polls resumed at 16:49 and the queue was empty then and at every later
  poll until the submission. Both E2 VM jobs carried `--begin=2026-10-12T17:51:33` from the
  lane, already past when each was submitted, so each started at submission.
- **Session E3's operator handover.** The orchestrating session restarted twice after session
  E2 (the operator's Mac crashed). This README's session E2 section and the host's run and
  pair directories were the record. (Correction, 2026-10-14: this item first said that the
  E2 operator's report file did not survive. That was wrong. A copy is in the orchestrator's
  scratch directory, written at 00:07 UTC on 2026-10-13, after the restarts and before E3
  was submitted. Its content agrees with the session E2 section above: session end
  19:12:47Z, DR0 not fired, no deviation, and the same disclosures.) An earlier E3 operator instance had prepared the E3 pair
  directories and E-9B-E3's VM manifest at 19:23 UTC on 2026-10-12 and submitted nothing; this
  operator found no E3 job, run directory or submission file, re-rendered that manifest
  (byte-identical) and submitted each pair once, after the gap, on an empty queue. No job was
  resubmitted.
- **E-9B-E3's `--test-only` estimate.** `sbatch --test-only` for the GPU half (id 1266)
  printed a start estimate of 08:20:02, the VM job's limit, where E1's and E2's printed the
  submission time; the GPU job itself (1267) started at 07:18:02 with its VM job. The estimate
  changes nothing the registration fixes. E-9B-E4's (id 1273) printed 21:43:28, again the VM
  job's limit; its GPU job (1274) started at 20:41:28 with its VM job. E-4B-E3's and E-4B-E4's
  printed the submission time.
- **Session E4's operator.** It started from the E3 operator's report, after session E3 had
  ended, found no E4 pair, run directory, job or operator process, and submitted each E4 pair
  once, after the gap, on an empty queue. One of its queue polls (about 09:15 UTC) failed on an
  ssh connection timeout while job 1271, another workstream's, was running and nothing of E's
  was pending; the next poll succeeded. No job was resubmitted.
- **S2 v5's step-0 export during E-9B-E3 (D96 item (2)).** S2 v5's step-0 source export was
  staged on the host while E3's 9B pair ran. It was file staging, not a Slurm job, so
  section 6.4 does not count it. D85, E's sign-off, allows other workstreams on the host only
  in the gaps between E's sessions, never during an E job, so the staging departed from
  D85's host-use condition. It touched no E record, and E-9B-E3's lane snapshots and queue
  watcher show no foreign Slurm job. (Added 2026-10-14; `RESULTS.md` disclosure 8.)
- **Deviations from the registration:** none (OE and sessions E1, E2, E3 and E4). The
  departure from D85's condition above is disclosed separately.
