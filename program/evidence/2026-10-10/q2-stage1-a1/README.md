# q2-stage1-rescoped-v1 (S1a): O2 and the four A1 jobs (sessions 1 and 2, 9B and 4B), 2026-10-09/10

Frozen registration `q2-stage1-rescoped-v1` (ledger row 16, file SHA-256
`f9db7cc38c4954b3144ac5a1afaf7bf5366449081b06c80bf89888bdf653afd8`, row hash
`bc5e88a0043065f93e3ea494633b6c3cd119973708e250110e7bcf4856507d0f`). Everything here ran from
the freeze commit `d5f57988ab94e0c098feddb744b78b73b5ad88ca` (tree
`c299515ccc74e294a25843ebeebed33d4557d629`), the commit that adds the row (section 1), as one
operator, in the order section 5.5 prescribes: O2, A1-9B-S1, A1-4B-S1, then the session-2 9B
pair submitted and held by Slurm until the 12-hour gap had passed, then A1-4B-S2 once A1-9B-S2's
records existed and its DR0 had been read.

**Result, registered per-job checks only.** O2 built the overlay on its first job (no retry).
All four A1 jobs (A1-9B-S1, A1-4B-S1, A1-9B-S2, A1-4B-S2) completed their base and every extension
block (452 of 452 episodes scored each); none lost an episode to infrastructure, and **DR0 does
not fire for any of them** (`rules.job_dr0`). The lane's provenance, engine-argv and Slurm-limit
checks passed for all four. Each later job's manifest named every earlier A1 job's record file
and receipt by SHA-256, and the lane accepted them. **No outcome was read or summarized**: this
README and the operator checks read infrastructure fields only (statuses, losses, re-queues,
fill, Slurm and engine records); no score, success rate or harness comparison was computed. The
registered analysis (D59 runbook) has not started.

## Jobs

| Job | What | Resources | Outcome | Physical GPU-h | Charged (D22) |
|---:|---|---|---|---:|---:|
| 1044 | O2: cu129 overlay build from the freeze commit | 1 H100, 8 CPUs, 32 GB, 3 min | COMPLETED 0:0 in 47 s (22:18:41-22:19:28 UTC, 2026-10-09); overlay `sha256:10327c706dcf2a9bd06e2449908e37d4fa4e46e7030a85e66f30626a1bafecde` | 0.0131 | 3 min |
| 1045 | A1-9B-S1 VM lane | 90 CPUs, 126 GB, 120 min, no GRES | COMPLETED 0:0 in 01:13:16 | 0 | - |
| 1046 | A1-9B-S1 GPU half, `sbatch --test-only` | - | never ran | 0 | - |
| 1047 | A1-9B-S1 engine and bridge (Qwen3.5-9B) | 1 H100, 32 CPUs, 160 GB, 110 min, `--dependency=after:1045` | COMPLETED 0:0 in 01:13:13 (22:21:19-23:34:32) | 1.2203 | 110 min |
| 1048 | A1-4B-S1 VM lane | 90 CPUs, 126 GB, 120 min, no GRES | COMPLETED 0:0 in 01:08:52 | 0 | - |
| 1049 | A1-4B-S1 GPU half, `sbatch --test-only` | - | never ran | 0 | - |
| 1050 | A1-4B-S1 engine and bridge (Qwen3.5-4B) | 1 H100, 32 CPUs, 160 GB, 110 min, `--dependency=after:1048` | COMPLETED 0:0 in 01:08:49 (23:36:29-00:45:18) | 1.1469 | 110 min |
| 1051 | A1-9B-S2 VM lane | 90 CPUs, 126 GB, 120 min, `--begin=2026-10-10T12:45:18` (moved to 12:50:00, D57) | COMPLETED 0:0 in 01:13:26 (12:50:19-14:03:45, 2026-10-10) | 0 | - |
| 1052 | A1-9B-S2 GPU half, `sbatch --test-only` | - | never ran | 0 | - |
| 1053 | A1-9B-S2 engine and bridge (Qwen3.5-9B) | 1 H100, 32 CPUs, 160 GB, 110 min, `--dependency=after:1051` | COMPLETED 0:0 in 01:13:16 (12:50:25-14:03:41) | 1.2211 | 110 min |
| 1062 | A1-4B-S2 VM lane | 90 CPUs, 126 GB, 120 min, `--begin=2026-10-10T12:45:18` (already past) | COMPLETED 0:0 in 01:08:00 (14:09:29-15:17:29) | 0 | - |
| 1063 | A1-4B-S2 GPU half, `sbatch --test-only` | - | never ran | 0 | - |
| 1064 | A1-4B-S2 engine and bridge (Qwen3.5-4B) | 1 H100, 32 CPUs, 160 GB, 110 min, `--dependency=after:1062` | COMPLETED 0:0 in 01:07:43 (14:09:42-15:17:25) | 1.1286 | 110 min |
| | **Total** | | | **4.7300** | **443 min** |

The O2 retry was not needed; its pre-funded 3 minutes stay in the remainder rule's allocation
(section 6.1), so T_A1 stays 110 and the caps total 477 minutes. Charged under S1a: the
pre-freeze 31 minutes plus these 443, 474 of 477 (the 3 left are O2's unspent retry). Job ids
1040-1043 and 1054-1061 are not this operator's (1054, 1056 and 1057: the D59 dry run's CPU-only
jobs; 1059 and 1061: E4's reviewer jobs; 1055, 1058 and 1060 never appeared in a queue sample
here); none was in the queue at any submission here, and none ran while an S1a job ran.

## Source and the frozen registration

- A git bundle of `main` (which holds `d5f5798`) was copied to the host. A clean clone
  (`o2/checkout-d5f57988ab94`) was checked out detached at `d5f5798`: `git status` empty, tree
  `c299515c...`. The read-only export `~/cotcodec-runs/stage0/q2-stage1/src/d5f5798.../` is `git
  archive` of the commit (tar SHA-256
  `412def036e25f3cbcf8ef9979dc3c27bff4426fa39d662c0c91d75cf4adc783c`), its file list equal to the
  commit's `git ls-files`, made read-only (`chmod -R a-w`); the VM lane's preflight records its
  tree digest `a63a0378cc029a057fb9de5c077f03cadeab082bb8731fd16fcec4d2b6efab74`. Every A1 job ran
  from this export; O2 ran from the clone.
- `scripts/preregister.py verify q2-stage1-rescoped-v1` and `check-chain` passed in the export
  and in the clone before O2 (`o2/preregister-verify.txt`, 22:17:51 UTC: row 16, file SHA-256
  `f9db7cc3...`, 16 rows, PASS), and again in the export right before each pair was submitted
  (`*/pair/preregister-verify.txt`, `a1-9b-s2-submitted/preregister-verify.txt`). The lane makes
  the same check itself at `validate`, `submit` and job start (`lane.frozen_registration`).

## O2 (`o2/`)

- Source archive: `scripts/create_source_archive.py --discovery` in the clean clone with the
  default ref `HEAD`, SHA-256 `4a59e87c8a04b3005606248f77b1b81b82e1bde127c72206f4113cc1b07349d8`,
  5,879 files, `selected_ref: HEAD`, `worktree_clean: true`, git tree `c299515c...`
  (`source-receipt-head.json`, SHA-256
  `1b60ae409473aa345e788762aa91b6a3b0d02b235be7357e0ccd56222daa4185`, as written).
- Before the job, so that its one retry could not be spent on job 1032's receipt error (section
  5.5), the pinned extractor (`9b4d21a8...`) validated that archive and receipt on CPU into a
  scratch directory with the expected commit and tree (`VALIDATED_DISCOVERY_SOURCE`, 5,879
  members), and the base image's ID (`sha256:423783aa...`) and commit label (`db9527a4...`) were
  checked. No GPU was used for this.
- Job 1044: `sbatch` of the clone's `scripts/build_vllm_overlay_on_h100.sh` (builder
  `aa43283e...`, extractor `9b4d21a8...`: job 464's and O1's), one H100, 8 CPUs, 32 GB,
  `--time=00:03:00`, `--no-requeue`, the queue empty and every GPU at 0 MiB before
  (`ops.log`). `build-receipt.json` (SHA-256
  `81467002b25e139cf38da7268c91f7882beaa558895069284a09d9c7942f112d`): provenance PASS (`git_sha`
  `d5f5798...`, `source_sha256` `4a59e87c...`), base `vllm/vllm-openai@sha256:b18abb2d...` (vLLM
  0.31.0), torchcodec removed as in O1, tag `cotcodec-vllm:4a59e87c-cu129-overlay`.

## A1 session 1

Both pairs were run by `ops/submit-pair.sh` (SHA-256 `79fdbb4e...`), in this order: verify and
`check-chain` in the export; `lane validate`; `squeue -a` empty and GPUs at 0 MiB; `lane submit`
(the VM job first); the GPU half rendered from the validated VM manifest with that job's id
(`render_q2_stage1_manifest.py gpu`); the docker submitter's `--dry-run`; `sbatch --test-only` of
the same argv; a foreign-queue check; the GPU job (`start_after_job_id`, so
`--dependency=after:` the VM job); its id written to the pair's `gpu_job_id`; end-state and
15-second queue watchers. Before each submission the VM manifest's `lane submit --dry-run` and a
GPU half rendered with a placeholder VM id went through the submitter's `--dry-run` (not
committed). The renderers, lane, submitter and checks ran with the host's system `python3 -E -s`,
the interpreter `s1a-vm.sbatch` runs the lane with.

### A1-9B-S1 (`a1-9b-s1/`: VM job 1045, GPU job 1047)

- **Manifest**: `render_q2_stage1_manifest.py vm --purpose a1 --plan
  program/evidence/2026-10-09/q2-stage1-prefreeze/plan/plan-a0a.json --size 9B --session S1`
  from the export, with A0a's host inputs and the pair's `gpu_job_id` file (`pair/host.json`):
  128 base slots (32 tasks x 2 harnesses x blocks `b1`, `b2`), 11 fill blocks, V 20, GPU cap
  110 (T_A1), 90 CPUs, 126 GB, 120 minutes, prompt date 2026-10-08, plan `6a3f0219...`.
  `pair/a1-9b-s1-vm.json` (SHA-256 `95408b37...`); `lane submit` stored and submitted its
  canonical form `4316c68a923e61523a63363db9589f115e7ca3a376c10ecf907f36bbe05e7314`.
- **GPU half** (`pair/a1-9b-s1-gpu.yaml`, `068bed53...`): 9B, 110 minutes, the O2 overlay, the
  freeze commit, the O2 archive, the 9B receipt `0a9e052d...` and artifact root `9845026d...`
  (A0a's). Dry run: 1.8333 GPU-h budget, `--time=01:50:00`, `--signal=B:USR1@180`,
  `--dependency=after:1045`; `--test-only` exit 0 (job id 1046; `pair/gpu-test-only.txt` keeps
  sbatch's reply).
- **The lane's checks** (`pair/job-checks.json`, from `ops/job_checks.py`):
  - provenance: `gpu-1047/provenance-verification.txt` PASS, `git_sha` and `source_sha256` equal
    to the GPU manifest's; model verification: `qwen3.5-9b` at `c2022362...`, root `9845026d...`;
  - engine argv: `ready.json`'s argv equals `plan.engine_argv` for 9B (SHA-256 `9b307cdc...`,
    A0a's); the engine was ready 96.6 s after the bridge started;
  - Slurm limit: the lane read TimeLimit 110 minutes from `scontrol`, equal to T_A1; USR1 point
    = Slurm start (22:21:19) + 110 min - 180 s (00:08:19);
  - the receipt holds no error; the lane dispatched (it refuses before dispatch otherwise); first
    dispatch 112.9 s after the GPU job's Slurm start.
- **Counts**: 452 slots dispatched, 452 records, every one `scored`; no infrastructure loss, no
  re-queue, no cap truncation, no USR1 (`stopped: false`). All 11 fill decisions allowed (each
  recomputed with `plan.fill_allowed`; smallest margin 19.4 minutes), all 11 extension blocks
  completed. The lane ended at 23:34:30, 33.8 minutes before its USR1 point; the bridge stopped
  on `vm.done`, engine return code 0. Guest-server restarts 0; 5,956 agent screenshots and 1,258
  checker reads, none retried, slower than 30 s or undelivered; no `/dev/nvidia*` in any episode
  container; preflight: TRES `cpu=90,mem=126G`, no GRES, Docker runtime runc, no labelled
  container left.
- **DR0** (`pair/dr0.json`, `python -m harness.q2_stage1.rules dr0`, exit 0): **does not fire**.
  Base complete; 9B/H-OSW-fixed 0 of 226 first attempts lost, 9B/H-GA 0 of 226; no lane error.
- **DR4 input** (section 9 item 10): GPU elapsed 4,393 s over 452 episodes = **0.002700 GPU-h per
  episode**, against the card's high price at V = 20, 0.011274.
- **Quiet host**: 294 queue samples (`pair/squeue-watch.log`) and 26 lane snapshots show only
  jobs 1045 and 1047; the only other running containers were the host's local registry and the
  job's own engine.

### A1-4B-S1 (`a1-4b-s1/`: VM job 1048, GPU job 1050)

- **Manifest**: as 9B with `--size 4B --prior-run-dirs runs/1045`. It names A1-9B-S1's record
  file `episodes.jsonl` (`a05dbf8473b83afef8522402e776460ff702e0fae2730f99c25f3978a51f7fc1`) and
  receipt `lane-receipt.json`
  (`692b9a2a60c0ab7924cbe13874ae9b05812eae2ed46a37e240734d673802d812`), the earlier job in
  `plan.a1_job_order`; `lane validate` re-ran DR0 on them and accepted. 128 base slots, 11 fill
  blocks; `pair/a1-4b-s1-vm.json` (`ae1ea55c...`), canonical
  `171294dd31cb5bb5ea5c7f68af7ab4bdeb7a75dfb7718170793958df9a8a59b9`.
- **GPU half** (`pair/a1-4b-s1-gpu.yaml`, `81c02d8f...`): 4B, 110 minutes, the O2 overlay; the 4B
  receipt `75ebfc53...` and artifact root `3b8a0751...` (see Disclosures). `--test-only` exit 0
  (job id 1049).
- **The lane's checks**: provenance PASS; model verification `qwen3.5-4b` at `851bf6e8...`, root
  `3b8a0751...`, 9,342,907,469 B; engine argv equals `plan.engine_argv` for 4B (`1c4cffba...`),
  ready 95.6 s after the bridge started; Slurm limit 110 = T_A1 (start 23:36:29, USR1 point
  01:23:29); no receipt error; first dispatch 104.6 s after the Slurm start.
- **Counts**: 452 dispatched, 452 `scored`; no loss, re-queue, cap truncation or USR1. 11 fill
  decisions allowed (smallest margin 24.6 minutes), all 11 extension blocks completed. Lane end
  00:45:16, 38.2 minutes before its USR1 point; bridge stopped on `vm.done`, engine return code
  0. Restarts 0; 6,118 agent screenshots and 1,257 checker reads, none retried, slow or
  undelivered; no GPU device in an episode container; no GRES, runc, no container left.
- **DR0**: **does not fire**. Base complete; 4B/H-OSW-fixed 0 of 226, 4B/H-GA 0 of 226; no lane
  error.
- **DR4 input**: 4,129 s over 452 episodes = **0.002537 GPU-h per episode** (high price 0.011274).
- **Quiet host**: 277 queue samples and 26 snapshots show only jobs 1048 and 1050.

## Session 2, 9B: submitted and held (`a1-9b-s2-submitted/`)

- **Manifest**: `--size 9B --session S2 --prior-run-dirs runs/1045 runs/1048`: it names A1-9B-S1
  (records `a05dbf84...`, receipt `692b9a2a...`) and A1-4B-S1 (records
  `733d73fdc49b7582aedb4f09e91a8e07c54c83941496e980f18fb668266b17bd`, receipt
  `9cf0950282b6206b148e54543dbb1e879208fa8caacef80985d1a7d0a9a5dc18`). Its extension blocks are
  recomputed from both session-1 record files (`records.completed_extension_blocks(...,
  sessions=("S1",))`): blocks 1-11, so 452 slots (base `b1`, `b2`, then `x01.1` to `x11.2`) and
  no fill. `lane validate` accepted it (both DR0 verdicts re-run); `a1-9b-s2-vm.json`
  (`32ec81fe...`), canonical `fe02f1cd10db7f288a016865176fd5e1c79a3daa1ebfe542b255b017255f9528`.
- **The 12-hour gap**: `lane.earliest_start` is the later of each session-1 pair's lane end and
  GPU EndTime, plus 12 hours: job 1050's EndTime, 2026-10-10T00:45:18, plus 12 h =
  **2026-10-10T12:45:18 UTC** (the host's clock is UTC). `lane submit` added
  `--begin=2026-10-10T12:45:18` (`vm-submit.json`), and the lane refuses to start before that
  time anyway.
- **Pending state** (`pending-check.txt`, 00:46:22 UTC): VM job 1051 `PENDING`,
  `Reason=BeginTime`, `EligibleTime=2026-10-10T12:45:18`, TimeLimit 02:00:00; GPU job 1053
  `PENDING`, `Reason=Dependency`, `Dependency=after:1051(unfulfilled)`, TimeLimit 01:50:00
  (`a1-9b-s2-gpu.yaml`, `cf5ceb93...`; `--test-only` job id 1052). Neither can start, or spend
  capped minutes, before 12:45:18. The queue was empty before the submission, and the end-state
  and queue watchers (`ops/submit-pair-v2.sh`, bounded at 18 hours) run on the host.
- Session 2 4B is **not** submitted: its manifest must name session 2 9B's record file and
  receipt (`plan.a1_job_order`).

## A1 session 2

One operator ran both session-2 pairs from the same read-only export of `d5f5798` (tree digest
`a63a0378...` again in each VM job's preflight), with the same interpreters and checks as
session 1. The session-2 9B pair was the one submitted and held above (begin time moved by D57).
After it left the queue, `ops/collect-pair.sh a1-9b-s2 1051 1053` ran DR0 and wrote the evidence
subset, and `ops/job_checks.py a1-9b-s2 1051 1053` re-read the lane's checks. Only then was
session 2 4B rendered, validated and submitted, by `ops/submit-pair.sh` exactly as in session 1.

### A1-9B-S2 (`a1-9b-s2/`: VM job 1051, GPU job 1053)

- **Ran**: VM job 1051 12:50:19-14:03:45 UTC (2026-10-10), COMPLETED 0:0 in 01:13:26; GPU job
  1053 started 6 s after it, 12:50:25-14:03:41, COMPLETED 0:0 in 01:13:16. The lane started at
  12:50:20, after `lane.earliest_start` (12:45:18) and more than 12 hours after the later
  session-1 job's Slurm end (VM job 1048, 00:45:21). `pair/a1-9b-s2-vm.json` and
  `pair/a1-9b-s2-gpu.yaml` are byte-identical to the copies in `a1-9b-s2-submitted/`.
- **The lane's checks** (`pair/job-checks.json`, `ops/job_checks.py`):
  - provenance: `gpu-1053/provenance-verification.txt` PASS, `git_sha` `d5f5798...` and
    `source_sha256` `4a59e87c...`, equal to the GPU manifest's; the O2 overlay
    `sha256:10327c70...`; model verification `qwen3.5-9b` at `c2022362...`, root `9845026d...`,
    19,329,393,661 B, receipt `0a9e052d...` (A0a's, as in session 1);
  - engine argv: `ready.json`'s argv equals `plan.engine_argv` for 9B (SHA-256 `9b307cdc...`,
    as in session 1); the engine was ready 97.6 s after the bridge started;
  - Slurm limit: the lane read TimeLimit 110 minutes from `scontrol`, equal to T_A1; USR1 point
    = Slurm start (12:50:25) + 110 min - 180 s (14:37:25);
  - the receipt holds no error; first dispatch 113.2 s after the GPU job's Slurm start.
- **Counts**: 452 slots dispatched (base `b1`, `b2` and the declared `s2_extension_blocks` 1-11,
  no fill decision, as section 5.6 requires of a session-2 job), 452 records, every one `scored`;
  no infrastructure loss, no re-queue, no cap truncation, no USR1 (`stopped: false`). Every one of
  blocks 1-11 completed. The lane ended at 14:03:40, 33.8 minutes before its USR1 point; the
  bridge stopped on `vm.done`, engine return code 0. Guest-server restarts 0; 5,946 agent
  screenshots and 1,258 checker reads, none retried, slower than 30 s or undelivered; no context
  fallback; no `/dev/nvidia*` in any episode container; every episode container removed, no
  leaked volume; preflight: TRES `cpu=90,mem=126G`, no GRES, Docker runtime runc, no labelled
  container left.
- **DR0** (`pair/dr0.json`, `python -m harness.q2_stage1.rules dr0`, exit 0): **does not fire**.
  Base complete; 9B/H-OSW-fixed 0 of 226 first attempts lost, 9B/H-GA 0 of 226; no lane error.
- **DR4 input** (section 9 item 10): GPU elapsed 4,396 s over 452 episodes = **0.002702 GPU-h per
  episode**, against the card's high price at V = 20, 0.011274.
- **Quiet host**: from 12:50:12 (both jobs eligible) to the end, 295 queue samples
  (`pair/squeue-watch.log`) and the lane's 26 snapshots show only jobs 1051 and 1053; the only
  other running containers were the host's local registry and the job's own engine. Earlier in
  the same log, while the pair was held, the watcher saw the D59 dry run's CPU-only jobs 1054,
  1056 and 1057 (01:42-02:00 UTC) and E4's reviewer job 1059 (one H100, 07:11-07:14); no S1a job
  was running then.

### A1-4B-S2 (`a1-4b-s2/`: VM job 1062, GPU job 1064)

- **Manifest**: `render_q2_stage1_manifest.py vm --purpose a1 --plan
  program/evidence/2026-10-09/q2-stage1-prefreeze/plan/plan-a0a.json --size 4B --session S2
  --prior-run-dirs runs/1045 runs/1048 runs/1051` (the run root's absolute paths) from the
  export, with A1-4B-S1's host inputs and this pair's `gpu_job_id` file (`pair/host.json`, which
  differs from `a1-4b-s1/pair/host.json` only in that path). It names, by SHA-256, the record
  file and receipt of every earlier A1 job in `plan.a1_job_order`, each equal to the file's
  digest on the host at rendering:
  - A1-9B-S1: `episodes.jsonl` `a05dbf84...`, `lane-receipt.json` `692b9a2a...`;
  - A1-4B-S1: `733d73fd...`, `9cf09502...`;
  - A1-9B-S2: `53559050bdcf66ddc4ee28208aa33d60b5e22db52b3aadf0207a3193a5d53f2a`,
    `d7e8575b33ba2dc53dafcfcb65882da8334d1920796e1b070fbbf8c4487cb241`.

  Its extension blocks are recomputed from both session-1 record files: blocks 1-11, so 452
  slots (base `b1`, `b2`, then `x01.1` to `x11.2`), the same (task, harness, rerun) slots as
  A1-9B-S2, and no fill. `lane validate` accepted it (the three earlier DR0 verdicts re-run);
  `pair/a1-4b-s2-vm.json` (`26e788a0...`), canonical
  `4031208e60bc19aa26040ed8d4e3945aae1be2b4e13bc33d0e48bf2fcbc62f67`.
- **Before submission** (not committed, as in session 1): the manifest's `lane submit --dry-run`
  (90 CPUs, 126 GB, `--time=02:00:00`, `--begin=2026-10-10T12:45:18`, source tree digest
  `a63a0378...`) and a GPU half rendered with a placeholder VM id through the submitter's
  `--dry-run` (`--time=01:50:00`, `--signal=B:USR1@180`, one H100, 32 CPUs, 160 GB). E4's
  reviewer job 1061 (one H100, 16 CPUs, 15-minute limit) started at 14:05:59, after A1-9B-S2 had
  left the queue (14:03:45), so the operator waited: the queue was empty and every GPU at 0 MiB
  by 14:09:19.
- **Submission** (`ops/submit-pair.sh a1-4b-s2`, the session-1 script, `pair/ops.log`): verify and
  `check-chain` PASS in the export at 14:09:27 (`pair/preregister-verify.txt`: row 16, file
  SHA-256 `f9db7cc3...`, 16 rows); `lane validate`; `squeue -a` empty and every GPU at 0 MiB; VM
  job 1062 (`lane submit`; its `--begin` from `lane.earliest_start` was already past, so Slurm
  started it at 14:09:29, 13 h 24 min after the later session-1 job's end); the GPU half rendered
  from the validated VM manifest (`pair/a1-4b-s2-gpu.yaml`, `c154b4ff...`, equal to
  `a1-4b-s1-gpu.yaml` but for its name and VM job id: 4B, 110 minutes, the O2 overlay, the
  freeze commit, the O2 archive, receipt `75ebfc53...` and root `3b8a0751...`); its dry run
  (1.8334 GPU-h budget, `--dependency=after:1062`); `--test-only` exit 0 (job id 1063); no foreign
  job; GPU job 1064, which started 13 s after its VM job.
- **The lane's checks** (`pair/job-checks.json`): provenance PASS, `git_sha` and `source_sha256`
  equal to the GPU manifest's; model verification `qwen3.5-4b` at `851bf6e8...`, root
  `3b8a0751...`, 9,342,907,469 B, receipt `75ebfc53...` (the receipt file of session 1, see
  Disclosures); engine argv equals `plan.engine_argv` for 4B (`1c4cffba...`), ready 95.1 s after
  the bridge started; Slurm limit 110 = T_A1 (start 14:09:42, USR1 point 15:56:42); no receipt
  error; first dispatch 103.2 s after the Slurm start.
- **Counts**: 452 dispatched, 452 `scored`; no loss, re-queue, cap truncation or USR1; no fill
  decision, and every one of blocks 1-11 completed. Lane end 15:17:24, 39.3 minutes before its
  USR1 point; bridge stopped on `vm.done`, engine return code 0. Restarts 0; 6,198 agent
  screenshots and 1,258 checker reads, none retried, slow or undelivered; no context fallback;
  no GPU device in an episode container; every container removed, no leaked volume; no GRES,
  runc, no container left.
- **DR0** (`pair/dr0.json`, exit 0): **does not fire**. Base complete; 4B/H-OSW-fixed 0 of 226,
  4B/H-GA 0 of 226; no lane error.
- **DR4 input**: 4,063 s over 452 episodes = **0.002497 GPU-h per episode** (high price 0.011274).
- **Quiet host**: 273 queue samples (14:09:28-15:17:34) and 26 snapshots show only jobs 1062 and
  1064; the only other running containers were the registry and the engine.

## GPU-hours

Physical (scontrol RunTime): O2 0.0131, A1-9B-S1 1.2203, A1-4B-S1 1.1469, A1-9B-S2 1.2211,
A1-4B-S2 1.1286; 4.7300 GPU-h in all (`program/state.json`, `gpu_hours_ledger`). The test-only
ids (1046, 1049, 1052, 1063) never ran. Charged under D22: 443 post-freeze minutes, 474 of S1a's
477 with the pre-freeze jobs.

## Disclosures

- **The 4B GPU job's receipt file.** `docker-research.sbatch` verifies the receipt in
  `hf-cache/cotcodec-receipts/<model>.json` only. For Qwen3.5-4B that file's SHA-256 is
  `75ebfc531acdcbc0c39bbf83ee7bf5267a3ddf02c4fafdf6181624612a0d3082`. G0 item 2 names the CPU
  lane's re-verification receipt `efc88487...` in `cotcodec-receipts-cpu-lane/`. The two differ
  only in `registry_sha256`, the registry file's digest at each fetch: revision `851bf6e8...`, the
  file list, total bytes and artifact root `3b8a0751...` are equal, and the job's own model
  verification checked the files against them. The registration pins the model by revision
  (section 4) and G0 item 2 by artifact root; the receipt digest is one of the template's
  host-specific fills. The 9B job used A0a's receipt, `0a9e052d...`. D57 (i) records this as a
  disclosure, not a deviation. Session 2 used the same receipt files: `75ebfc53...` for A1-4B-S2
  (job 1064) and `0a9e052d...` for A1-9B-S2 (job 1053).
- **Interpreters.** `scripts/preregister.py` needs Python 3.11 or later (`datetime.UTC`), so it
  ran under the host's uv-managed CPython 3.12.13; everything else ran under the system Python
  3.10 with `-E -s` (numpy 1.21.5 from the system packages), as the VM lane does.
- **The test-only reply.** The docker submitter's `--test-only` discards sbatch's stderr (A0a's
  `gpu-test-only.txt` was empty). The script ran the submitter's dry-run argv with `--test-only`
  inserted before the batch script, which is what `sbatch_argv(manifest, test_only=True)` builds,
  and kept the reply.
- **Operator scripts** (`ops/`): `submit-pair.sh` (session 1), `submit-pair-v2.sh` (the same plus
  a `WATCH_S` bound for the watchers, used for the held session-2 pair; SHA-256 `41860d17...`),
  `collect-pair.sh` (`6aa149a1...`: DR0, the raw listings and this evidence subset) and
  `job_checks.py` (`5698a4a2...`: the infrastructure checks above). None is code of record; none
  runs inside a job. Session 2 used the same files from the host's read-only `a1-ops/` (SHA-256s
  equal to these): `collect-pair.sh` and `job_checks.py` for both pairs, and `submit-pair.sh` for
  A1-4B-S2. Two copies of the S2 9B inputs exist: `a1-9b-s2/pair/a1-9b-s2-vm.json` and
  `a1-9b-s2-gpu.yaml` are byte-identical to those in `a1-9b-s2-submitted/`.
- **Dates.** O2 and A1-9B-S1 ran on 2026-10-09 UTC (22:18-23:35); A1-4B-S1 ran from 23:36 on
  2026-10-09 to 00:45 on 2026-10-10; the session-2 9B submission was at 00:46 on 2026-10-10;
  A1-9B-S2 ran 12:50-14:04 and A1-4B-S2 14:09-15:17 on 2026-10-10.
- **Jobs of other work between S1a jobs.** The quiet-host rule (section 5.5) covers the time an
  S1a job runs; it held throughout. While the session-2 9B pair was held, the D59 dry run's CPU
  jobs (1054, 1056, 1057) and E4's reviewer job 1059 ran; between A1-9B-S2's end and A1-4B-S2's
  submission, E4's reviewer job 1061 ran (14:05:59 to before 14:09:19). The A1-4B-S2 pair was
  submitted only after the queue was empty and every GPU was at 0 MiB.
- **Records with scores.** `vm-*/episodes.jsonl` hold the checker scores, as A0a's copy did.
  They are here because the later manifests name them by SHA-256 (A1-4B-S2's, the last, is
  named by its digest in this README and is the registered analysis's input). They were not
  summarized: the hygiene and infrastructure scans of session 2 read only statuses, losses,
  observation counts, restarts, devices, teardown and receipt timing.
- **Deviations from the registration:** none.

## Records' SHA-256

| File | SHA-256 |
|---|---|
| `a1-9b-s1/vm-1045/episodes.jsonl` | `a05dbf8473b83afef8522402e776460ff702e0fae2730f99c25f3978a51f7fc1` |
| `a1-9b-s1/vm-1045/lane-receipt.json` | `692b9a2a60c0ab7924cbe13874ae9b05812eae2ed46a37e240734d673802d812` |
| `a1-9b-s1/vm-1045/manifest.json` | `d4a0743cc2044130384c9aac6fc07584fa80f0f43b7f070cbe6315f671192fcf` |
| `a1-9b-s1/gpu-1047/bridge/stopped.json` | `d88d0436cf4d974e0e5d1b2a0c0014381fc5d015a07068f5655dd78fc9442813` |
| `a1-9b-s1/pair/dr0.json` | `0bccd1f95c3dae92c1a601d79201f323f0389012d303fb7d52b7142df750e1da` |
| `a1-4b-s1/vm-1048/episodes.jsonl` | `733d73fdc49b7582aedb4f09e91a8e07c54c83941496e980f18fb668266b17bd` |
| `a1-4b-s1/vm-1048/lane-receipt.json` | `9cf0950282b6206b148e54543dbb1e879208fa8caacef80985d1a7d0a9a5dc18` |
| `a1-4b-s1/vm-1048/manifest.json` | `54b803d3da18831fd41a20871170770fe53b6e2ff5e87fc245427f3b108fdb5e` |
| `a1-4b-s1/gpu-1050/bridge/stopped.json` | `4a20813ee9a9b18c9ae4e821a8a660e39d898cfb69376259d59d0ad8a0835609` |
| `a1-4b-s1/pair/dr0.json` | `7db4f60a6709503831497e7f7be75bbdb4caa144f5298eb726c405c9ba74c806` |
| `a1-9b-s2-submitted/a1-9b-s2-vm.json` | `32ec81fe1b930ef39f5867b7a7087153e42a142be8d78e68c0c13cfcf5388f8a` |
| `a1-9b-s2/vm-1051/episodes.jsonl` | `53559050bdcf66ddc4ee28208aa33d60b5e22db52b3aadf0207a3193a5d53f2a` |
| `a1-9b-s2/vm-1051/lane-receipt.json` | `d7e8575b33ba2dc53dafcfcb65882da8334d1920796e1b070fbbf8c4487cb241` |
| `a1-9b-s2/vm-1051/manifest.json` | `7b342d20bda98aea979d1c39224b6f37212369fe526a448434a4fde75d8f3dc2` |
| `a1-9b-s2/gpu-1053/bridge/stopped.json` | `44bcd02ae4bcf80d66bc971abcb421871a9ab63f5b5be9d99ccacaff0f6029ca` |
| `a1-9b-s2/pair/dr0.json` | `9d45ef217eb3e9cae3cd38adddffa1e726ef67b5da46511e74f5c2a82997a944` |
| `a1-9b-s2/pair/job-checks.json` | `cc26747d9a6c0e7e803fcfb4ab742a12486f155ab0b48270caf6f8ba1c9100d1` |
| `a1-4b-s2/pair/a1-4b-s2-vm.json` | `26e788a01c0f4ce0f81d4b59e12b51ed6787acbc7f16bcfdb5aa6c9a3b2040af` |
| `a1-4b-s2/vm-1062/episodes.jsonl` | `1b33883129f012009e2ff3a5c7ef2d2093d00b8f562cca1f8d309b56978de4c2` |
| `a1-4b-s2/vm-1062/lane-receipt.json` | `06bb05aae9dcdc82b9c5973c5735ca58640c1e110ed098766e2790005c33fffe` |
| `a1-4b-s2/vm-1062/manifest.json` | `f8440455a5213b5acbc79e9db9f29f7dc37a98dc38e564d3755ec7b3e92d4beb` |
| `a1-4b-s2/gpu-1064/bridge/stopped.json` | `9d8bb6a8e68893982797ad81f5511f867f52222a487cfcb90b4ee9aa5b59e39c` |
| `a1-4b-s2/pair/dr0.json` | `7a7ed9f045334e2905badedfc975f3165a586375675bcc1d21fb262af8176e95` |
| `a1-4b-s2/pair/job-checks.json` | `6a8be9c280f1c99a56793d2fee0e010109a03cba76f24335df21513249ef9872` |
| `o2/build-receipt.json` | `81467002b25e139cf38da7268c91f7882beaa558895069284a09d9c7942f112d` |
| `o2/source-receipt-head.json` | `1b60ae409473aa345e788762aa91b6a3b0d02b235be7357e0ccd56222daa4185` |

`vm-*/raw-sha256sums.txt` (4,691, 4,679, 4,693 and 4,690 files for jobs 1045, 1048, 1051 and 1062)
and `gpu-*/raw-sha256sums.txt` list every file of
the host run directories, including the step logs, model replies, screenshots, captures and engine
logs, which stay on the host (section 16). The GPU UUID appears only as its SHA-256
(`gpu.jsonl`). No host address and no credential is recorded here: the only IPv4 values are the
engine's `127.0.0.1` bind and the VM's internal guest address, as in A0a's evidence, and the
episode records keep setup and postconfig replies without their stdout tails
(`driver.strip_stdout`).

## Next

1. Session 2 ran: A1-9B-S2 (1051/1053) and A1-4B-S2 (1062/1064), DR0 does not fire for either
   (sections above). No S1a job is pending or running.
2. An independent verification of the session-2 per-job checks, as D57 did for session 1.
3. The registered analysis under D59, D61 and D62 (`ops/s1a-analysis/RUNBOOK.md`) on the four A1
   run directories (VM jobs 1045, 1048, 1051, 1062): offline rescoring, the report, DR1-DR5 and
   P1-P5, every output labelled "not externally anchored". **Done on 2026-10-10:** see
   `RESULTS.md` here and `../q2-stage1-analysis/`.

## Session 2 begin time moved (D57)

At 2026-10-10T01:10Z, after the session-1 verification, the pending S2 9B VM
job 1051's begin time was moved from 12:45:18 to 12:50:00 UTC (`scontrol update
JobId=1051 StartTime=2026-10-10T12:50:00`, before it started), so that it starts
at least 12 hours after the later S1 job's Slurm end (VM job 1048, 00:45:21) as
well as after `lane.earliest_start` (00:45:18 + 12 h). GPU job 1053 still waits
on `after:1051`. Before and after: `squeue` showed 1051 PENDING (BeginTime) and
1053 PENDING (Dependency).
