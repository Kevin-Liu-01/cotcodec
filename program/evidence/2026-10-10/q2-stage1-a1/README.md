# q2-stage1-rescoped-v1 (S1a): O2, A1 session 1 (9B, 4B), and session 2 9B queued, 2026-10-09/10

Frozen registration `q2-stage1-rescoped-v1` (ledger row 16, file SHA-256
`f9db7cc38c4954b3144ac5a1afaf7bf5366449081b06c80bf89888bdf653afd8`, row hash
`bc5e88a0043065f93e3ea494633b6c3cd119973708e250110e7bcf4856507d0f`). Everything here ran from
the freeze commit `d5f57988ab94e0c098feddb744b78b73b5ad88ca` (tree
`c299515ccc74e294a25843ebeebed33d4557d629`), the commit that adds the row (section 1), as one
operator, in the order section 5.5 prescribes: O2, A1-9B-S1, A1-4B-S1, then the session-2 9B
pair submitted and held by Slurm until the 12-hour gap has passed.

**Result, registered per-job checks only.** O2 built the overlay on its first job (no retry).
Both session-1 jobs completed their base and every extension block; neither lost an episode to
infrastructure, and **DR0 does not fire for either** (`rules.job_dr0`). The lane's provenance,
engine-argv and Slurm-limit checks passed for both. The session-2 9B pair is PENDING: VM job
1051 held by `--begin=2026-10-10T12:45:18` (UTC), GPU job 1053 by `--dependency=after:1051`.
Session 2 4B is not submitted (its manifest must name session 2 9B's records). **No outcome
was read or summarized**: this README and the operator checks read infrastructure fields only
(statuses, losses, re-queues, fill, Slurm and engine records); no score, success rate or harness
comparison was computed. The registered analysis waits for all four A1 jobs.

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
| 1051 | A1-9B-S2 VM lane | 90 CPUs, 126 GB, 120 min, `--begin=2026-10-10T12:45:18` | PENDING (BeginTime) | 0 | - |
| 1052 | A1-9B-S2 GPU half, `sbatch --test-only` | - | never ran | 0 | - |
| 1053 | A1-9B-S2 engine and bridge (Qwen3.5-9B) | 1 H100, 32 CPUs, 160 GB, 110 min, `--dependency=after:1051` | PENDING (Dependency) | 0 | (110 min when it runs) |
| | **Total so far** | | | **2.3803** | **223 min** |

The O2 retry was not needed; its pre-funded 3 minutes stay in the remainder rule's allocation
(section 6.1), so T_A1 stays 110 and the caps total 477 minutes. Charged so far under S1a: the
pre-freeze 31 minutes plus these 223, 254 of 477. Job ids 1040-1043 were allocated before O2 and
are not this operator's; none was in the queue at any submission here.

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

## GPU-hours

Physical (scontrol RunTime): O2 0.0131, A1-9B-S1 1.2203, A1-4B-S1 1.1469; 2.3803 GPU-h in all
(`program/state.json`, `gpu_hours_ledger`). The test-only ids never ran; the session-2 jobs have
not run.

## Disclosures

- **The 4B GPU job's receipt file.** `docker-research.sbatch` verifies the receipt in
  `hf-cache/cotcodec-receipts/<model>.json` only. For Qwen3.5-4B that file's SHA-256 is
  `75ebfc531acdcbc0c39bbf83ee7bf5267a3ddf02c4fafdf6181624612a0d3082`. G0 item 2 names the CPU
  lane's re-verification receipt `efc88487...` in `cotcodec-receipts-cpu-lane/`. The two differ
  only in `registry_sha256`, the registry file's digest at each fetch: revision `851bf6e8...`, the
  file list, total bytes and artifact root `3b8a0751...` are equal, and the job's own model
  verification checked the files against them. The registration pins the model by revision
  (section 4) and G0 item 2 by artifact root; the receipt digest is one of the template's
  host-specific fills. The 9B job used A0a's receipt, `0a9e052d...`.
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
  runs inside a job.
- **Dates.** O2 and A1-9B-S1 ran on 2026-10-09 UTC (22:18-23:35); A1-4B-S1 ran from 23:36 on
  2026-10-09 to 00:45 on 2026-10-10; the session-2 submission was at 00:46 on 2026-10-10.
- **Records with scores.** `vm-*/episodes.jsonl` hold the checker scores, as A0a's copy did.
  They are here because the later manifests name them by SHA-256. They were not summarized.
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
| `o2/build-receipt.json` | `81467002b25e139cf38da7268c91f7882beaa558895069284a09d9c7942f112d` |
| `o2/source-receipt-head.json` | `1b60ae409473aa345e788762aa91b6a3b0d02b235be7357e0ccd56222daa4185` |

`vm-*/raw-sha256sums.txt` (4,691 and 4,679 files) and `gpu-*/raw-sha256sums.txt` list every file of
the host run directories, including the step logs, model replies, screenshots, captures and engine
logs, which stay on the host (section 16). The GPU UUID appears only as its SHA-256
(`gpu.jsonl`). No host address and no credential is recorded here: the only IPv4 values are the
engine's `127.0.0.1` bind and the VM's internal guest address, as in A0a's evidence, and the
episode records keep setup and postconfig replies without their stdout tails
(`driver.strip_stdout`).

## Next

1. Session 2 9B starts at 12:45:18 UTC on 2026-10-10 (Slurm and the lane both hold it). After it
   ends: collect, run DR0 on its records; if DR0 does not fire, render session 2 4B with
   `--prior-run-dirs runs/1045 runs/1048 runs/1051`, validate and submit it (the queue empty
   first).
2. After all four A1 jobs: the registered analysis (`harness.q2_stage1.analysis`), DR1-DR5, P1-P5,
   with the label "not externally anchored".
