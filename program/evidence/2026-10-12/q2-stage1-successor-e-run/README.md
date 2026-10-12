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
(section 18) runs after the last E job.

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
| | **Total so far** | | | **2.5694** | **203 of 406 min** |

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
had ended (19:12:50). Charged under D22: OE's 3 minutes, session E1's 52 + 48 and session E2's
52 + 48, 203 of E's 406 cap-minutes; the OE retry's 3 minutes stay unspent.

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

Next: session E3 (E-9B-E3, then E-4B-E3), each pair submitted only on an empty queue and no
earlier than 2026-10-13T07:17:47Z (the lane passes `--begin` and refuses an earlier start).
Other workstreams may use the host until then, and must have ended before E-9B-E3 is submitted
(section 6.4, D85, D87, D90).

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
- **Deviations from the registration:** none so far (OE, session E1 and session E2).
