# q2-stage1-rescoped-v1 (S1a): pre-freeze jobs O1 and A0a, and the D53 (iii) check, 2026-10-09

The draft `q2-stage1-rescoped-v1` (branch `stage0/q2-stage1-rescope`, not frozen, no ledger
row) after the action path's acceptance on attempt 1 (D53). D49 (ii) admits the pre-freeze
GPU jobs O1 and A0a within S1a's caps; A0b is not submitted, because the anchor is
unavailable (G0 item 9.6). Everything here ran from the draft commit
`bb67aa02fa9bce8a2b10a4822a23a2f81fae4d40` (tree `905a5a51214eff228a5c71070ab421d7573ba3d1`),
which holds the D53 (iii) fix and G0 item 1. The host export is read-only at
`~/cotcodec-runs/stage0/q2-stage1/src/bb67aa0.../`; the overlay was built from a clone of
the same commit.

**Result.** O1 built the overlay on its second job. A0a completed 20 of 20 episodes in one
wave at V = 20, and both of its gates hold. The constants follow from the registered rules:
c_A0a 0.003054, L_A0a 1.887 min, c_proj 0.011274 (the card's high price binds), T_A1 110
minutes, total caps 477 minutes, **K_base 32**, which meets the floor of 32. No registered
rule sends the draft back to review. The pinned-code check shows that the D53 (iii) fix
turns every server-error run into an infrastructure loss and leaves the agent's own state
(a missing file) scored.

## Jobs

| Job | What | Resources | Outcome | Physical GPU-h | Charged (D22) |
|---:|---|---|---|---:|---:|
| 1032 | O1: overlay build | 1 H100, 8 CPUs, 32 GB, 3 min | FAILED 2:0 after 1 s. The source receipt was made with `--ref bb67aa0...`, and the extractor admits only `selected_ref: HEAD`. This was an operator error; nothing was built | 0.0003 | 3 min |
| 1033 | O1 retry | the same | COMPLETED 0:0 in 47 s; overlay `sha256:2c5f9b20f6709dd6fdd4743dee50dab3aec3ef753a9b7f11d9e5ce6cd8e4df62` (`cotcodec-vllm:83d0d503-cu129-overlay`) | 0.0131 | 3 min |
| 1034 | D53 (iii) check, first run | CPU only, 8 CPUs, no GRES | cancelled by the operator after 22 rows, because the pinned `get_file`'s 5 s pause was not skipped and the run would have outrun its 30-minute limit | 0 | - |
| 1035 | the check, second run | the same | COMPLETED; the stand-in answered every `/execute` with a path, which the vlc and gimp getters read as the OS name. So in `file500` 2 tasks raised before any file read; `reads500` caught them | 0 | - |
| 1036 | the check, third run (the result) | the same | COMPLETED in 15 s (below) | 0 | - |
| 1037 | A0a VM lane | 90 CPUs (4 x 20 + `runner_cpus(20)`), 126 GB, 35 min, no GRES | COMPLETED 0:0 in 6 min 09 s; 20 of 20 scored | 0 | - |
| 1038 | A0a GPU half, `--test-only` | - | never ran | 0 | - |
| 1039 | A0a engine and bridge (Qwen3.5-9B) | 1 H100, 32 CPUs, 160 GB, 25 min, `--dependency=after:1037` | COMPLETED 0:0 in 6 min 04 s | 0.1011 | 25 min |
| | **Total** | | | **0.1144** | **31 min** |

The registered caps count whatever the job's outcome (D22), and an O1 retry enters the
remainder rule (section 6.1). So T_A1 = floor((478 − 3 − 3 − 25 − 3 − 3)/4) = **110**
minutes, not the 111 the draft planned. The caps total 477 minutes (7.950 GPU-h).

## O1 (`o1/`)

- Source archive: `create_source_archive.py --discovery` in a clean clone of `bb67aa0`,
  SHA-256 `83d0d5032105cb5cac156eb635fd7918917d9f9ddf006d6b8cc5f3c8862cfcbb`, 5,803
  files. `source-receipt-head.json` is the one 1033 used (SHA-256
  `a092d0aa720565c3cd731aa67a6d99765aa1c7afd95253c9aa9aeae8528caf6e` as copied here,
  re-indented). `source-receipt-1032.json` is the refused one; the archive bytes are the
  same.
- Builder `scripts/build_vllm_overlay_on_h100.sh` `aa43283e757695384e0548d060a18b98f07a3af06f583efdb2d709f677e1a96d`
  and extractor `9b4d21a83beac8913dc06a946cf43ea31d77326e65d04957fad66d7b97d8c3cb`.
  These are job 464's (serving probe v2) digests.
- `build-receipt.json` (SHA-256
  `320e23a3901198ec6789b020ee160258b902c5b228fabe9c0aa1daf1f57ed13d`): provenance PASS, base
  `vllm/vllm-openai@sha256:b18abb2d...` (vLLM 0.31.0, `db9527a4...`), torchcodec removed
  (`vllm-overlay-fixups.json`), labels `revision = bb67aa0...`,
  `source-tree-sha256 = 83d0d503...`.
- `ops.log` holds the queue reads before each submission (all empty), the failure note and
  the check submissions. `scontrol-103{2,3}.txt` and `slurm-o1-103{2,3}.out` are the
  Slurm records and outputs.

## The D53 (iii) check on the pinned code (`observation-check/`)

`observation_check.py` (job 1036's copy, byte for byte). It ran as `s1a-cpu.sbatch` run
mode: the checker-mutation metric image `sha256:2006c1a9...`, `--network none`, no VM, no
GPU (receipt `container_dev_nvidia: []`). It used the export of `bb67aa0` and OSWorld
`b138d348` with the file cache from the mutation study's inputs, on **the 32 dev-split tasks
only** (no confirm task). For each task and stand-in guest, it ran the pinned
`DesktopEnv.evaluate()` as the old runner called it, then `LiveTask.evaluate()` as the new
runner does, and classified the result with the driver's rule. In job 1036 the stand-in
answers every `execute_python_command` with `Linux`, because its prefix names
`platform.system`.

| Guest | Old runner | New runner |
|---|---|---|
| `file500`: `/file` answers HTTP 500, the rest healthy | 32 of 32 scored (0, or a metric exception scored 0) | 32 of 32 `guest_observation` |
| `reads500`: `/file` and `/execute` answer HTTP 500 | 32 of 32 scored | 32 of 32 `guest_observation` |
| `missing404`: healthy, no file exists (404) | 32 of 32 scored | 32 of 32 scored (30 returned 0, 2 metric exceptions on the missing state, as the pinned code does); no loss |

`observation-check-1036.json` (SHA-256
`12082e1ba9e0f7e48d50c02191893b9352b77f4432b26ffdf3fe5da27be07b81`) has every row, with no
file content. Job 1035's rows and script (`observation-check-1035.json`,
`observation_check-1035.py`) and job 1034's receipt and Slurm record are kept.

## A0a (`a0a/`)

How it ran, as the draft and D49 (ii) prescribe:

- **Code**: the read-only export of `bb67aa0`. The lane's preflight records the source tree
  digest `a6c83bc1...` and runtime runc.
- **Manifests**: rendered from the plan, never hand-written. `host.json` holds the host
  inputs (VM pins and qcow2, OSWorld, file cache, the bridge directory template).
  `render_q2_stage1_manifest.py vm --purpose a0a --n-star 32` wrote `a0a-vm.json`: V = 20,
  the five dev tasks of `plan.a0a_slots` (`6a33f9b9`, `bf4e9888`, `d681960f`, `4172ea6e`,
  `12382c62`) x 2 harnesses x 2 reruns in the seeded block orders, prompt date 2026-10-08,
  90 CPUs, 35 minutes. `lane validate` accepted it, and `lane submit` wrote the canonical
  manifest. It has two digests, of one content: `lane submit` stores and submits the
  compact canonical form (`lane.canonical`: sorted keys, no spaces), SHA-256
  `051cdd6e6380ee62987109815e79cdcb740052e84603b634ba9e08d430205a79`, which `vm-submit.json`
  and `vm-1037/preflight.txt` name; the run directory keeps it indented,
  `vm-1037/manifest.json`, SHA-256
  `057b6353ca1bc7c9020968ca2aede2350e24655eeffdaf38080a827172af64a5`, which the draft, the
  plan and `a0a-measurements.json` name. `lane.canonical` of `vm-1037/manifest.json` gives
  `051cdd6e...` again (checked 2026-10-09). The GPU half, `a0a-gpu.yaml`,
  was rendered from the validated VM manifest (9B, 25 minutes, `gpu-values.json`: the O1
  overlay, the commit, the archive digest, the 9B receipt `0a9e052d...` and artifact root
  `9845026d...`) and passed the submitter's `--dry-run` (`gpu-dry-run.json`) and
  `--test-only` (job 1038). `gpu-test-only.txt` is empty (one newline): `sbatch
  --test-only` reports on stderr, which was not saved. That the call passed is shown by the
  narrative and by the job-id sequence (1038 allocated to the test, 1039 to the
  submission); a later run saves the test-only call's stderr.
- **CPUs**: 90 for the VM job and 32 for the GPU job, 122 in all, at most 200 (section 5.5).
- **Quiet host**: `squeue -a` was empty before the VM submission, and showed no foreign job
  before the GPU submission (`ops.log`). While A0a ran, a 15 s queue watcher took 25 samples
  (`squeue-watch.log`) and the lane took 4 host snapshots (`vm-1037/lane-receipt.json`). They
  show only the pair's own jobs 1037 and 1039; the lane's `squeue_foreign` lists only 1039,
  its GPU partner. Job ids 1032-1039 are all this operator's. The snapshots' container
  counts are not foreign compute: `containers_ours` counts containers labelled with the VM
  job's id and is 0 at every snapshot (each is taken at the start, as a block's first slot
  is dispatched and before its VM container starts, or after the last teardown);
  `containers_running_total` is 1 at the start, the host's long-running local image
  registry (`cotcodec-registry`, up 8 weeks and the only running container when checked on
  2026-10-09), and 2 while GPU job 1039's engine container runs. The other workflow's
  reviewer job did not appear, so no foreign job had to be waited for or judged under the
  draft's rules (section 5.5 "Quiet host"; section 15 reports any foreign load).
- **End states**: `scripts/record_slurm_end_states.sh` caught both (`slurm-state/`). The lane
  recorded the GPU job's Slurm start and end, so the registered stand-in for a missed end
  was not needed.

What it measured (`a0a-measurements.json`: `python -m harness.q2_stage1.plan
a0a-measurements` on the host, which reads the step logs that stay there):

- 20 of 20 slots scored, all in one wave; no slot was cut, re-queued or left undispatched.
- Slot occupancy (dispatch to teardown) ranged 151.6-248.7 s, mean 219.9 s, sum 4,397.99
  s. So **c_A0a = 4,397.99 / 3,600 / (20 x 20) = 0.003054 GPU-h**.
- **L_A0a = 1.887 min**: from the GPU job's Slurm start (18:15:42 UTC) to the first
  dispatch, 113 s. The engine was ready 96.6 s after the bridge started, and the first
  forwarded request came 3.585 min after the Slurm start.
- **Truncation gate**: 0 of 131 H-OSW-fixed turns and 0 of 125 H-GA turns ended at 2,048
  tokens without a complete tool call, against a gate of 20%. Holds.
- **Concurrency gate**: the `DesktopEnv.step` p95 was **1.265 s** over 255 steps, against
  2 x 2.6944 = 5.389 s (G0 item 1: the accepted attempt's `step_p95_n1_s`). Holds.
- **Other counts**:
  - 256 model turns, 94,891 output tokens (371 per turn);
  - no infrastructure loss, `IRError`, metric exception, postconfig failure or guest-server
    restart;
  - 275 agent screenshots and 40 checker reads, none retried, slow or undelivered;
  - 8 uncertified key actions.
- **Outcomes** (dev split, descriptive only; no rule reads them): 8 of 20 scored 1.0, both
  harnesses on `6a33f9b9` and `4172ea6e` in both reruns. The other 12 reached the 15-step
  cap and scored 0.

## Constants and the plan (`plan/plan-a0a.json`)

On the host, `scripts/render_q2_stage1_plan.py --a0a-run-dir runs/1037 --a0a-bridge-dir
gpu/1039/bridge --n-star 32 --action-path-step-p95 2.6944 --prefreeze-jobs O1 O1 A0a`
applied `plan.freeze_constants`:

| Constant | Value |
|---|---|
| N*, V | 32, 20 |
| c_A0a (GPU-h) | 0.003054 |
| c_proj (GPU-h) | 0.011274 = max(the card's high price at V = 20, 1.25 x 0.003054 = 0.003818) |
| L_A0a (min) | 1.887 |
| T_A1 (min), total caps (min) | 110, 477 |
| K_base (floor) | 32 (32): ((110 − 3 − 1.887)/60)/(4 x 1.05 x 0.011274) = 37.0 tasks, 32 after the rounding to a multiple of 8 and the cap at 32 |
| Base | section 5.4's K = 32 draw, unchanged |
| Gates | truncation 0.0 / 0.0; step p95 1.265 s against 5.389 s; both hold |

- The plan's `plan_sha256` is `6a3f0219448301d95a80d443ed75892eaac093e42349ef98fb985a5d87467d51`
  (file SHA-256 `a5f0aadce1208d9d9ab31ff572ca93e624dbd87e1b50dd194987ff8cc46e1806`). Run
  locally on `a0a-measurements.json` and the committed inputs, `plan.freeze_constants` and
  `plan.render_plan` give the same constants and the same `plan_sha256`.
- This is not yet the frozen plan. If no A0 job is repeated, this committed file is the
  frozen plan: A1 manifests name it (`--plan
  program/evidence/2026-10-09/q2-stage1-prefreeze/plan/plan-a0a.json`), and the freeze
  writes its **`plan_sha256` field** (`6a3f0219...`), in backticks, into G0 item 10's slot,
  not the file's SHA-256 (`a5f0aadc...`): `lane.load_frozen_plan` refuses every A1 manifest
  unless the registration states the field in that form (G0 item 10). That happens after
  the program's sign-off of section 18 (Kevin's two slots are filled from D55); the fresh
  pre-freeze audit is answered (registration section 22).

## Records' SHA-256

| File | SHA-256 |
|---|---|
| `a0a/vm-1037/episodes.jsonl` | `8b2ce375ac444b8fce4a9796b1900d169a9e40da5bbc7e34ea386f03a8f0c724` |
| `a0a/vm-1037/lane-receipt.json` | `d5389962a722037096a45e803acc0183265455f5ce539d24beb0e3f8a34eaceb` |
| `a0a/vm-1037/manifest.json` | `057b6353ca1bc7c9020968ca2aede2350e24655eeffdaf38080a827172af64a5` |
| `a0a/gpu-1039/bridge/stopped.json` | `a95a0f61540f763a5ff1207dccbaa5df9f2590173f3550fcfa0769073a0fce8b` |
| `a0a/a0a-measurements.json` | `e81050a811d371b1c85071fd64f58b4513bd4b7e8b60c0653e1216afaf5a78cb` |
| `plan/plan-a0a.json` | `a5f0aadce1208d9d9ab31ff572ca93e624dbd87e1b50dd194987ff8cc46e1806` |
| `o1/build-receipt.json` | `320e23a3901198ec6789b020ee160258b902c5b228fabe9c0aa1daf1f57ed13d` |
| `observation-check/observation-check-1036.json` | `12082e1ba9e0f7e48d50c02191893b9352b77f4432b26ffdf3fe5da27be07b81` |
| `observation-check/receipt-1036.json` | `46be07142ee6478685f8ea50f1651ee3af93b648e865065cc5f4011bfca5073d` |

`a0a/vm-1037/raw-sha256sums.txt` and `a0a/gpu-1039/raw-sha256sums.txt` list every file in
the two host run directories. That covers the episodes' step logs, model replies, captures
and the engine log, which stay on the host (section 16). The GPU UUID appears only as its
SHA-256 (`gpu.jsonl`). No host address and no credential is recorded here; the episode
records keep setup replies without their stdout tails.
