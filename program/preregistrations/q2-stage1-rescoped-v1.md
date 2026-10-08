# Preregistration: q2-stage1-rescoped-v1 (Q2 Stage 1a: rerun-noise floor and harness screen on the certified harness pair)

**Status: DRAFT, not frozen.** This file has no ledger row. No confirm-split
episode may run under it. The pre-freeze development jobs of section 6 (O1,
A0a, A0b) need a program decision admitting them, as D36 and D42 admitted
their timing jobs. Freezing needs a fresh pre-freeze audit, the G0 items of
section 3, and Kevin's or the program's sign-off on the design decisions of
section 16. A material change after the freeze is a new experiment id.

- Drafted 2026-10-08 on branch `stage0/q2-stage1-rescope`.
- Gauntlet proposal: `program/proposals/2026-10-08-q2-stage1-rescoped.md`.
- Design panel: three designs, two judges; this file is the winning design (A)
  with grafts from both judges, recorded in the proposal's iteration log.

## 1. Identity

- **Experiment id:** `q2-stage1-rescoped-v1`. This is Stage S1a of the
  rescoped Q2 Stage 1.
- **Question:** Q2 (`program/questions/q2-calibrated-cua-instrument.md`), Stage 1.
- **What it measures.** It measures two things on OSWorld-Verified desktop
  tasks:
  - the rerun-noise floor, between and within serving sessions;
  - the harness effect between the two harnesses the action-path suite
    certifies (main effect, and task x harness interaction).
  The models are Qwen3.5-4B and Qwen3.5-9B. The tasks are the web-free
  confirm split used by the checker-mutation study.
- **Claim level.** Confirmatory for the registered estimands of section 9
  under the registered design. Out of scope: any claim about other harnesses,
  the observation factor, step budgets other than 15, sampled decoding, or
  larger models.
- **Why rescoped.** `serving-throughput-probe-v2` priced Stage 1 as designed
  at 431.5 GPU-h (job 466; `program/evidence/2026-10-07/serving-throughput-probe-v2/`).
  Its rule sends anything above 90 GPU-h back for rescoping before the
  gauntlet. The question file's 5,760-episode design is therefore not
  runnable.
- **Inputs it builds on.** All are frozen or committed:

  | Input | Status | Source |
  |---|---|---|
  | `q2-action-path-v2`, `-inputs`, `-executor` | frozen, ledger rows 13-15; acceptance not yet run | `program/preregistrations/q2-action-path-v2*.md` |
  | `serving-throughput-probe-v2` | frozen, job 466 | cost card and engine settings |
  | `q2-holo3-rerun-audit-v2` | confirmatory | two same-day runs of one agent differ by a session shift, so the floor must be measured between sessions |
  | `q2-evaluator-mutation-v1` | descriptive (D35) | checker corrections and K1 task exclusions |

- **Code revision.** The jobs run from an export of the freeze commit (or,
  for O1, A0a and A0b, of the draft commit named in their manifests). The
  following must not change between A0 and the freeze:
  - the engine launcher;
  - the episode driver;
  - both harness clients;
  - the checker invocation.
  The freeze row's git head is the code of record for O2, ANC and A1.

## 2. What S1a decides, and what it does not

S1a stands on its own. Every exit is a reportable Q2 result.

1. **Noise floor.** The between-session rerun discordance D_b and the
   within-session discordance D_w, per size and pooled, under the stated
   configuration. The difference D_b − D_w is the session excess that the
   Holo3 v2 result predicts.
2. **Harness main effect.** δ = H-GA minus H-OSW-fixed in task-weighted
   success, pooled over sizes and per size.
3. **Harness interaction and share.** The task x harness interaction X, and
   the harness share π of within-task outcome variance, per size.
4. **Floor criterion.** The question file's 4B floor criterion, as a ladder
   decision for Stage S1b.
5. **First real cost card** for the certified pair: realized GPU-h and VM-h
   per episode, steps, output tokens, truncation at the token cap,
   setup/eval/queue times and infrastructure loss. It replaces the synthetic
   431.5 GPU-h projection.
6. **External runtime check (D11).** OpenCUA-7B at 15 steps against its three
   public 15-step runs on the same tasks.
7. **Admission rule for S1b.** A pre-specified GO / NO-GO / INCONCLUSIVE
   rule for the scale ladder, tied to the ladder's own minimum detectable
   share (section 11, DR5).

S1a does **not** answer:

- whether the harness-plus-interface share shrinks with scale;
- the observation factor. Neither certified harness reads an accessibility
  tree: OSWorld `bfd62bdc` raises `ValueError` for any observation other than
  screenshot, and gym-anything `aae6f7607` has no accessibility path;
- 27B or 35B-A3B;
- step caps of 50 or 100;
- sampled decoding.

Those belong to Stage S1b, which exceeds 8 GPU-h. S1b needs the gauntlet and,
under D24, Kevin's trust store or admission ruling.

## 3. Gates

### 3.1 Before any GPU job (G0, CPU only, 0 GPU-h)

1. `q2-action-path-v2` acceptance holds: A1-A6 and validity controls C1-C3
   pass, and the ladder has set N*. A7 is not needed, because S1a uses the
   screenshot setting only (action-path v2 section 7).
2. **Qwen3.5-4B model receipt.** Repository `Qwen/Qwen3.5-4B`, revision
   `851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a`, made by a CPU job as for the
   other receipts. The 9B receipt exists (revision
   `c202236235762e1c871ad0ccb60c8ee5ba337b9a`).
3. **Episode driver** (`harness/q2/stage1/`), reviewed and tested against a
   fake OpenAI-compatible engine on CPU:
   - It reproduces each harness's upstream runner semantics:
     - H-OSW-fixed: OSWorld `bfd62bdc` `lib_run_single`.
     - H-GA: gym-anything `aae6f7607`'s runner.
     - Covered: step counting, replies with no action, `wait`,
       `terminate`/`answer`, the step cap, and evaluation after the last step.
   - Every difference from upstream is recorded in
     `harness/q2/action_path/harness_design_diffs.md`.
   - It runs on the certified L0-fixed executor through the frozen IR.
4. **Engine bridge under D13.** Runners join each VM container's
   `--network none` namespace, so they reach the engine only through a
   Unix-domain socket. The socket is bind-mounted into each GPU-less runner
   and forwarded to the engine's port, which is bound to 127.0.0.1 only. No
   Docker network is created. The remaining exposure is recorded.
5. **Offline task setup** from the pinned file cache (the mutation study's
   `file-cache-receipts.tsv`, 447 files with SHA-256). Every base task's setup
   is checked to complete offline on one VM with no model call.
6. **Final-state capture.** After the checker runs, the files the checker
   read are copied off the VM and hashed, so every verdict can be rescored
   offline.
7. **Per-episode cost logging** (section 7.3).
8. **Corrected comparator** `compare_pptx_files_zinv`. It ignores shape order
   only among shapes whose frames do not overlap. It is validated on CPU on
   the stored confirm mutants and golds before the freeze:
   - It passes the 30 audit-confirmed `pptx.eq.zorder_nonoverlap` equivalence
     mutants.
   - It gives the original comparator's verdict on every other evaluable
     `compare_pptx_files` mutant and on every gold.
   - The 6 unresolved candidates are reported, not used to tune it.
9. **Anchor feasibility** (section 5.7), checked on CPU:
   - The vLLM v0.31.0 overlay lists OpenCUA-7B's architecture.
   - Serving it requires `--trust-remote-code`, i.e. third-party model code
     on a GPU. That needs an admission decision of the D29 kind; see
     decision 21.
   - The public runs' per-task `result.txt` members can be read by ranged
     reads, with the member manifest SHA-256 `55d03377...` recorded in
     `program/evidence/2026-10-07/holo3-v2/receipt-v2-final.json`.
   - If any of these fails, the anchor jobs (A0b, ANC) are not submitted and
     the anchor status is UNAVAILABLE (section 11, DR-A).
10. **Task draw and episode orders** written by a committed script and hashed
    (section 5.4). The draft draw is in the proposal's evidence bundle
    (`analysis/task-draw-K32.json`).

### 3.2 Before any confirm-split episode

1. A0a has run (and A0b, if the anchor is available). The constants of
   section 6.2 are computed from their records by the registered rule and
   written into this file.
2. Fresh pre-freeze audit, then freeze (`scripts/preregister.py freeze`).
3. No confirm-split task is touched by any job before the freeze. A0a and A0b
   use dev-split tasks only.

## 4. Frozen inputs (pinned at freeze; values known now are given)

| Input | Pin |
|---|---|
| OSWorld runtime | `xlang-ai/OSWorld` at `b138d348256078fa634fc3b73567a7337c793e6b` (as action-path v2) |
| VM image, guest disk, VM settings, runner image, lane | as `q2-action-path-v2` section 2.1 (VM image `happysixd/osworld-docker@sha256:0e6497a9295647cf05bf2b2af522fdd79bdeba2737595259cab310a3bcf6baa9`; runner image `sha256:ac2b5815...`) |
| Executor, IR, harness adapters | file digests of the `q2-action-path-v2-executor` addendum |
| H-OSW-fixed upstream | OSWorld `bfd62bdc5a3319809a236dc90ddbbaf3cb4b7e06` `mm_agents/qwen35vl_agent.py`, SHA-256 `1f39be92cf5461d9671ab9307a69c05691abf0226aa6b53d2af332003a5096fe` (re-fetched 2026-10-08, equal to `harness/q2/action_path/upstream/PROVENANCE.json`) |
| H-GA upstream | gym-anything `aae6f7607e0f3d9d6306e1fefbad92bda99ca99a` `agents/agents/qwen35vl.py`, SHA-256 `93666f2751d99dfee0034700f65385ca2db1544e3d9a0d194807050d2edea1a5` (re-fetched 2026-10-08, equal to PROVENANCE) |
| Engine | vLLM v0.31.0 (commit `db9527a46873454610df6dbedf79a36d6bf1a7f6`), base `docker.io/vllm/vllm-openai@sha256:b18abb2df97b8f798e81862bd93f872ea18613372e2c3adc0cc2ac21e66ac12f`, cu129 overlay rebuilt by O1 and O2 from the draft and freeze commits |
| Engine flags | the `serving-throughput-probe-v2` contract's: TP 1, bf16, seed 42, `max_model_len` 131072, `gpu_memory_utilization` 0.90, `max_num_seqs` 256, `max_num_batched_tokens` 8192, prefix caching on, `generation_config: vllm`, at most 20 images (1920x1080) and no video per prompt, no reasoning parser, no speculative decoding |
| Models | `Qwen/Qwen3.5-9B` at `c2022362...`, `Qwen/Qwen3.5-4B` at `851bf6e8...` (Apache-2.0); anchor `xlangai/OpenCUA-7B` at `a2efb7d2b104d477a4a2666a357e79550a28aafc` (MIT) |
| Tasks | `program/evidence/q2-mutation/splits.json` (SHA-256 `2099792e6fb86c69e4f79b1ce47d2839cc25623f5c4633698e95822553c007d9`) and the sanitized task files |
| Public anchor runs | `xlangai/ubuntu_osworld_verified_trajs` at `5473c39e42a538a187a9b2c2b499db59d560fd8c`, archive `opencua_agent-opencua_7b-cot_l2-action_history-3image-Ubuntu-15steps.zip` (LFS SHA-256 `b642e1212d3ebb87e88addc0c55525b12d1ce8b9b253306fa7706908778e9688`) |

## 5. Design

### 5.1 Models and engine

- **Models:** Qwen3.5-4B and Qwen3.5-9B, bf16, one H100 per engine.
- **One engine per (size, session) job.** Both harness clients share it.
- **Engine settings** are the cost card's, so the card's prices apply.
  `serving-throughput-probe-v2` requires Stage 1 to reuse these settings or
  re-probe.
- **No 27B or 35B-A3B rung.** Their multipliers are unmeasured (the card
  uses 4.5x and 1.5x by rule). Measuring them belongs to S1b's replay probe.

### 5.2 Harnesses

Both are certified by `q2-action-path-v2` A2 and A3:

- **H-OSW-fixed:** OSWorld `bfd62bdc` `Qwen35VLAgent` with its own-spec fixes
  (action-path v2 section 3).
- **H-GA:** gym-anything `aae6f7607` `qwen35vl`, unmodified, with its IR
  adapter.

Each harness keeps its own system prompt, tool description, parser and
message layout. Both use the same upstream layout:

- 100 history turns;
- at most 20 live screenshots, with older ones folded in blocks of 10;
- every later turn wrapped as a tool response;
- the full reply, thinking included, passed back into history. The Qwen3.5
  template keeps that thinking, because every later user turn is a tool
  response.

They differ by design, and the differences are part of the harness factor:

| Area | H-OSW-fixed | H-GA |
|---|---|---|
| Modifiers on clicks | yes (via `text`) | no |
| Horizontal scroll | `hscroll`, mapped to vertical | absent |
| Drag | from the current pointer | two-point |
| Scroll units | its own | magnitude 1 to 10 |
| `wait` | waits its time | the step returns only the wait |
| Reply that does not parse | no action that step | a one-second wait |
| `terminate` status | own handling | reported through `metadata.status` |
| Upstream token budget | 32,768 | 2,048 |

The token budget is deliberately equalised here (section 5.3). The full list
is `harness/q2/action_path/harness_design_diffs.md`.

### 5.3 Observation, step cap, token budget, sampling

- **Observation:** screenshot only (`require_a11y_tree=False`), 1920x1080.
- **Step cap:** T = 15 for both harnesses. The OSWorld runner's default is
  50 (`scripts/python/run_multienv_qwen35vl.py` at `bfd62bdc`).
- **Pause after execution:** 0.0.
- **Thinking:** on, by the Qwen3.5 template default. Neither harness sends
  `chat_template_kwargs`.
- **max_tokens:** 2,048 for both. This is H-GA's default; H-OSW's runner
  default of 32,768 is lowered and disclosed. The harness factor therefore
  excludes the thinking budget.
- **Sampling, both harnesses:** temperature 0.0 and top_p 0.9, the OSWorld
  runner defaults. This is greedy decoding. The Qwen model card's
  recommended thinking-mode sampling is not used (disclosed).
- **Context:** the largest context is 62,950 tokens even if every history
  turn carries a full 2,048-token thinking block (proposal, cost analysis).
  This is below 131,072, so H-GA's context-retry fallback should never fire.
  If it fires, it is logged.

### 5.4 Tasks

- **Eligible pool (116 tasks).** The 120-task confirm split of
  `splits.json` (seed 42, stratified by domain x checker class) minus the four
  K1 raw-gold failures of the checker-mutation study (`0a0faba3`, `15aece23`,
  `ac1b39ff`, `ed43c15f`). Their checkers fail their own gold. Pool by domain:
  gimp 8, calc 28, impress 24, writer 12, multi_apps 24, thunderbird 7, vlc 6,
  vs_code 7.
- **Base set (K_base = 32 unless section 6.2 lowers it).**
  - Allocation: plain largest-remainder apportionment over domains, ties
    broken by domain name. At K = 32: gimp 2, calc 8, impress 7, writer 3,
    multi_apps 6, thunderbird 2, vlc 2, vs_code 2.
  - Draw: within each domain, the first n_d ids of `sorted(ids)` shuffled by
    `random.Random(f"q2-stage1a:base:42:{domain}")`.
  - K = 24 and K = 16 bases drawn this way are nested in the K = 32 base.
- **Extension order.** The remaining tasks, sorted and shuffled by
  `random.Random("q2-stage1a:ext:42")`, are cut into blocks of 8; the last
  block may be shorter. Draft output (SHA-256 recorded at the freeze):
  - base: `035f41ba 0a211154 0bf05a7d 185f29bd 26150609 2cd43775 358aa0a7 3a93cae4 4188d3a4 4f07fbe9 53ad5833 5df7b33a 66399b0d 70bca0cc 72b810ef 7a4deb26 7efeb4b1 881deb30 982d12a5 9b7bc335 9cf05d24 a01fbce3 c59742c0 d06f0d4d dfac9ee8 e2dd0213 e8172110 ecb0df7a edb61b14 f178a4a9 f9584479 fba2c100`;
  - 84 extension tasks in 10 blocks of 8 and one of 4.
- **Dev tasks for A0a and A0b.** The first 4 ids of the dev split
  (`splits.json`, 32 tasks) sorted and shuffled by
  `random.Random("q2-stage1a:dev:42")`, restricted to tasks whose setup
  completes offline (G0 item 5).

### 5.5 Sessions, blocks, reruns, order, concurrency

- **A session** is one GPU job for one size, with a fresh engine, paired with
  one CPU-only VM job (D12) holding a fresh pool of VMs. Every episode is a
  cold boot from the read-only qcow2 base.
- **Sessions per size:** S1 and S2.
  - Both S1 jobs (4B and 9B) run first.
  - The S2 jobs start at least 12 hours after the later S1 job ends.
  - Within a session, the two sizes are separate jobs.
- **Blocks within a session job.**
  - Block 1 runs every base (task, harness) cell once.
  - Block 2 runs them all again.
  - Each block is in its own random order, mixing the harnesses.
  - Order seed: `random.Random(f"q2-stage1a:{session}:{size}:{block}:{seed}")`,
    with seed 43 for S1 and 44 for S2.
- **Replicates.** Each (size, task, harness) therefore has R = 4 episodes:
  2 sessions x 2 within-session reruns. Pairs are between-session (4 per
  cell) or within-session (2 per cell).
- **Concurrency.** V is the number of concurrent VMs per engine; N* is the
  ladder's qualified concurrency.

  | N* | Sizes | V per engine | K_base |
  |---|---|---|---|
  | 40 | concurrent (two GPU jobs, two VM jobs) | 20 | 32 |
  | 32 | concurrent | 16 | 32 |
  | 24 | sequential | 20 | 32 |
  | 16 | sequential | 16 | 32 |
  | 8 | sequential | 8 | 16 |
  | 1 | no A1; S1a reports A0 and the anchor only | - | - |

  V never exceeds 20, the card's measured value for this profile. The
  ladder's quiet-host rule carries over: while an A1 job runs, the operator
  submits no other Slurm job. Every block records host snapshots (time, load
  average, foreign Slurm jobs and their CPUs, container counts).

### 5.6 Continuous dispatch and the fill rule

- **Continuous dispatch.** Each VM takes the next queued episode as soon as
  its previous episode has been torn down. There are no synchronized waves,
  so cost follows the steps actually run. Block 2 is queued only after every
  block-1 episode has been dispatched. Prompts and sampling are not affected.
- **Fill rule (session-1 jobs only; decided on cost, never on outcomes).**
  - After its base blocks, a session-1 job starts extension block b (8 tasks
    x 2 harnesses x 2 within-session reruns = 32 episodes, in two
    sub-blocks) only if
    `1.5 x c_job x 32 <= (time to the lane's USR1 signal) - 10 minutes`.
  - c_job is the job's elapsed time since its first request divided by its
    completed episodes.
  - Blocks are taken in the extension order.
- **Session-2 jobs** run the base and then exactly the extension blocks that
  both session-1 jobs completed, in the same order. They make no fill
  decision of their own.
- **Analysis set.** Base tasks, plus extension blocks completed in all four
  A1 jobs. A block cut by the cap is outside the analysis set. Because the
  orders are random, that cut is unrelated to outcomes.

### 5.7 The OpenCUA-7B anchor (D11)

- **Agent.** OpenCUA-7B with the upstream OSWorld OpenCUA agent at the
  settings of the public run: CoT level L2, action history, 3 history images,
  15 steps.
  - Settings are taken from the public archive's recorded run arguments
    where present, else from the agent's defaults. Both are recorded before
    the freeze.
  - It runs the **upstream** action path: PyAutoGUI strings through
    `DesktopEnv.step`, the L0-raw layer that action-path v2's C2
    characterises. This is deliberate, because the public runs used that
    path. Its outcomes are a runtime-equivalence check, not instrument data.
- **Run.** One episode per pool task (116), in an order stratified by domain
  and seeded by `random.Random("q2-stage1a:anchor:42")`, with V = min(40, N*)
  on one H100. The job stops dispatching at the cap's 10-minute margin.
- **Reading.** The anchor is read on its completed tasks. At least 58 must
  complete for a reading.
- **Order.** ANC runs after the freeze and before any A1 job.
- **A0b** is its pre-freeze smoke: 4 dev tasks, one episode each.

## 6. Jobs, caps and the 8 GPU-h count

### 6.1 Jobs

Caps follow D22's counting rule: every job's registered cap counts, whatever
its outcome.

| Job | When | What | Cap (min) | GPU-h cap | Central | High |
|---|---|---|---:|---:|---:|---:|
| O1 | pre-freeze | cu129 overlay build from the draft commit (one H100, as job 464: 44 s) | 3 | 0.050 | 0.012 | 0.050 |
| A0a | pre-freeze | 9B, 4 dev tasks x 2 harnesses x 2 reruns = 16 episodes, V = min(16, N*) | 22 | 0.367 | 0.244 | 0.351 |
| A0b | pre-freeze | OpenCUA-7B, 4 dev tasks x 1 = 4 episodes | 18 | 0.300 | 0.220 | 0.287 |
| O2 | post-freeze | overlay build from the freeze commit | 3 | 0.050 | 0.012 | 0.050 |
| ANC | post-freeze, before A1 | OpenCUA-7B anchor, up to 116 episodes | 32 | 0.533 | 0.449 | 0.533 |
| A1 x4 | post-freeze | (4B, 9B) x (S1, S2), 4K_base episodes per job plus fill | 4 x 100 | 6.667 | 5.018 | 6.561 |
| **Total** | | | **478** | **7.967** | **5.955** | **7.832** |

- Central and high come from the cost card (proposal, Compute and
  Reproducibility). The A1 central and high are for the base at K = 32 and
  V = 16; the fill rule converts any slack into tasks inside the caps.
- **Per-episode prices** for the certified pair at T = 15, H2-thinking
  profile, Qwen3.5-9B:
  - central 0.009020 GPU-h (the open-loop bound binds);
  - high 0.011512 GPU-h (V = 16, 180 s of GPU idle per wave, t_env 4 s);
  - the 4B multiplier is 1.0 by the card's rule.
- **A1 per job at the high price:** 128 episodes x 0.011512 GPU-h = 88.4 min,
  plus 10 min of launch and teardown = 98.4 min, against a cap of 100 min.
- **Maximum.** 478 minutes of one H100 is 7.967 GPU-h, at most 8.0. S1a
  therefore needs no gauntlet. It never spends more than its caps: an
  amendment that would raise any cap above this total is not made, and the
  design goes to the gauntlet instead (D20, D22, D24).

### 6.2 Constants set from A0a before the freeze (the D36/D44 pattern)

- **c_A0a** is A0a's GPU time per completed episode: job elapsed time minus
  time to the first request, divided by completed episodes.
- **c_proj** = max(the card's high price at A1's V, 1.25 x c_A0a).
- **K_base** = min(K_N*, 8 x floor(0.375 / c_proj / 8)).
  - K_N* is from section 5.5.
  - 0.375 is the 90 usable minutes of a 100-minute job divided by 4
    episodes per task.
  - K_base can only fall. At the card's high price it is 32.
- **Floor.** If K_base < 16, the draft is not frozen and goes back to review.
- **Truncation.** If more than 20% of A0a's steps in either harness end at
  2,048 tokens without a complete tool call, the draft is not frozen. The
  choice between a larger token budget (fewer tasks) and non-thinking mode
  goes back to review.
- **Plumbing.** If A0a or A0b shows a defect in the driver, bridge or
  checker path, it is fixed before the freeze. A second A0 job would need a
  recount under D22: every A0 repeat lowers the A1 caps by its own cap, or
  the design goes to the gauntlet.

### 6.3 VM time (CPU-only lane, D12)

A VM is occupied for the episode's wall time (GPU-h per episode x V) plus
setup and checker time (1.5 min central, 3 min high).

| Job | Central VM-h | High VM-h | Reservation bound VM-h |
|---|---:|---:|---:|
| A1 | 105 | 120 | 133 (4 jobs x 100 min x 20 VMs) |
| A0a | | 4 | |
| Anchor | | | 21 (32 min x 40 VMs) |

- Wall-clock: about 2 h per session at N* of 32 or more, plus the 12-hour
  gap.
- The action-path suite that gates S1a needs 98.4 VM-h.

## 7. Episodes

### 7.1 Definition

An episode is one (size, task, harness, session, block) slot. It runs:

1. VM cold boot from the qcow2 base;
2. offline task setup;
3. up to 15 agent steps;
4. evaluation with OSWorld `b138d348`'s `DesktopEnv.evaluate()` (the
   task's checker);
5. final-state capture;
6. teardown.

### 7.2 Infrastructure failures

An episode is **lost to infrastructure** if any of these occurs:

- VM boot or task setup fails;
- the guest server restarts during the episode (its `NRestarts` counter
  changes or a different server process answers; D30, D33);
- an engine request fails after the client's retries, or times out at 600 s;
- the executor or guard fails;
- the runner crashes;
- the checker raises.

Handling:

- A lost episode is re-queued once, at the end of its block. A second loss
  leaves the slot missing.
- Loss counts are reported per (job, size, harness).
- Cap truncation is not an infrastructure loss (section 5.6).

### 7.3 Logging (also the C1 timing census)

Per step:

- prompt and output tokens;
- the SHA-256 of the prompt token ids (`return_token_ids`);
- whether the output hit 2,048 tokens and whether it held a complete tool
  call;
- the parsed IR;
- engine latency, time to first token and time per output token;
- the executor's settle time;
- queue wait at the engine.

Per episode:

- boot, setup, evaluation and teardown times;
- steps used and how the episode ended;
- the checker score;
- the hashes of the checker's input files;
- guest-server restart counts.

Per job:

- GPU memory and utilisation samples;
- host snapshots;
- realized GPU-h and VM-h.

## 8. Outcomes and checker corrections

- **Primary outcome.** y = 1 if the task's checker score is 1.0, else 0
  (raw verdict). Fractional scores are counted and reported. A sensitivity
  analysis uses the score itself.
- **Checker-corrected outcome (secondary).** Each saved final state is
  rescored with `compare_pptx_files_zinv` in place of `compare_pptx_files`
  (G0 item 8). This covers only the defect the mutation study confirmed
  (`compare_pptx_files` fails 35 of 36 equivalent non-overlapping z-order
  edits; 30 confirmed by both raters).
  - Flips are counted per task.
  - Kevin's adjudication of the 34-item pool and the 25-item spot check are
    pending (D9), so corrected verdicts stay secondary.
- **Flagged tasks.**
  - The two confirm tasks whose GUI-faithful saved gold fails its checker,
    confirmed by both raters (P1: `9ec204e4`, `b8adbc24`). They stay in the
    primary analysis; a sensitivity excludes them.
  - The four K1 raw-gold failures are outside the pool.

## 9. Estimands and estimators

Notation:

- For size z, task t and harness h, p_zth is the success probability over
  the population of sessions and reruns of this configuration.
- m_zths is the mean of the two within-session reruns in session s.
- d_zts = m_zt,GA,s − m_zt,OSW,s.

Every quantity is task-weighted over the analysis set.

1. **Noise floor.**
   - D_b,z is the mean over (t, h) of the fraction of discordant pairs among
     the 4 cross-session pairs.
   - D_w,z is the same over the 2 within-session pairs.
   - The session excess is D_b − D_w.
   - Pooled means are averaged over sizes.
2. **Harness main effect.** δ_z = mean_t mean_s d_zts, and δ = (δ_4B + δ_9B) / 2.
3. **Interaction (session-aware).**
   - X_z = mean_t d_zt1 · d_zt2, the product of the two sessions' harness
     differences.
   - This is unbiased for mean_t (p_zt,GA − p_zt,OSW)^2 when sessions are
     independent given the task. It stays unbiased under task x session and
     task x harness x session variation.
   - Design A's Bernoulli-corrected form, which treats all four reruns as
     independent, is reported as a secondary. In simulation it is biased
     upward when there is task x harness x session variation (proposal,
     Evaluation section).
4. **Harness share.**
   - π_z = (X_z / 4) / (X_z / 4 + D_b,z / 2). This is the harness part of
     within-task outcome variance when each harness is used half the time;
     rerun variance is taken from the between-session floor.
   - π_small is the mean of π_4B and π_9B, or π_9B alone if DR1 drops 4B.
5. **Scale screen.** δ_4B − δ_9B and π_4B − π_9B. These are labelled a
   screen; S1a makes no shrinkage claim.
6. **Session shift.** Per size, mean success in S2 minus S1.
7. **Anchor.**
   - Our success, minus the mean of the three public runs' success, on the
     anchor's completed tasks.
   - Discordance between ours and the public runs, against the mean
     public-versus-public discordance on the same tasks (the public runs
     differ by 7.5-9.7% on all 359 tasks: holo3-v2 receipt).
8. **Cost card.** Realized GPU-h and VM-h per episode by size, harness and
   job. Also: steps, output tokens, truncation rate, and the step-of-
   termination and step-of-success distributions (censored at 15).

## 10. Inference and operating characteristics

### 10.1 Inference

- **Intervals.** Task-cluster percentile bootstrap: 10,000 resamples, seed
  42. Tasks are resampled jointly across sizes, harnesses and sessions.
- **δ.** Paired t over tasks on d̄_t (the mean over sessions and sizes),
  two-sided, α = 0.05. Per-size tests are secondary.
- **X.** One-sided permutation test that permutes harness labels within each
  task x session. The statistic is the session-aware X pooled over sizes;
  10,000 permutations, seed 42, α = 0.05. Sensitivities:
  - a sign-flip randomization test on the per-task products (valid under
    session-specific harness effects, conservative);
  - the Bernoulli-corrected statistic.
- **Session shift.** Per size, a two-sided permutation test of session labels
  within (task, harness) on mean S2 − S1; 10,000 permutations, seed 42. The
  per-size paired t on session means is secondary.
- **Secondary model.** A logit crossed GLMM:
  `y ~ size*harness + (1|task) + (1|task:size) + (1|task:harness) + (1|task:size:harness) + (1|session) + (1|task:session)`.
  - Fitted by Laplace (glmmTMB in a pinned CPU container built in G0).
  - Latent-scale variance shares get parametric-bootstrap intervals.
  - It includes a likelihood-ratio test of harness-specific task variance.
    Any later uneven allocation of reruns across harnesses rests on that
    homogeneity.
  - A fit that does not converge is reported as such.
- **Missing data.** Missing slots (second infrastructure loss) are treated
  as missing at random. A task with no complete pair for a quantity drops
  out of that quantity only.

### 10.2 Operating characteristics

Monte Carlo, CPU only, seeded (scripts and outputs under
`program/proposals/evidence/2026-10-08-q2-stage1-rescoped/analysis/`):

- `analysis/sim_s1a.py`: 2,000 data sets per point, 200 permutations for
  permutation tests;
- `analysis/sim_signflip.py`: 1,000 data sets.

The generative model is logit p = size + task (SD σ_a, correlation 0.8
across sizes) + harness + task x harness (σ_b) + session (SD 0.1) + task x
session (SD 0.3) + task x harness x session (σ_f), with Bernoulli outcomes.
Scenarios:

- **Literature:** base success 15% (4B) and 30% (9B), σ_a = 3.5; true rerun
  discordance 12% and 18%, matching the 12-14% flip rates of arXiv
  2608.06171.
- **High noise:** σ_a = 2.5.
- **Low base:** 8% and 20%.
- **OpenCUA-calibrated:** σ_a = 6.9, base 18% and 24.3%; bimodal tasks,
  calibrated to the public OpenCUA-7B 15-step runs.

Literature scenario:

| Quantity | K = 32 (base) | K = 64 | K = 116 |
|---|---:|---:|---:|
| δ pooled, MDE at 80% power (two-sided 5%) | 7.4 pp | 5.1 pp | 3.6 pp |
| δ per size (4B / 9B) | 10.3 / 11.4 pp | 6.6 / 7.9 pp | 4.8 / 5.8 pp |
| δ_4B − δ_9B scale screen, MDE | 16.6 pp | 10.8 pp | |
| 90% CI half-width of pooled δ | 4.0 pp | 2.8 pp | 2.1 pp |
| D_b pooled, 95% half-width | ±5.6 pp | ±4.0 pp | ±3.0 pp |
| D_b per size, 95% half-width | ±7.1 / ±7.8 pp | ±5.1 / ±5.5 pp | ±3.7 / ±4.2 pp |
| D_b − D_w, 95% half-width | ±3.4 pp | ±2.5 pp | ±1.8 pp |
| X test (permutation, session-aware): size at the null; with σ_f = 0.5 | 0.022; 0.052 | 0.046; 0.040 | |
| X test power at RMS per-task harness effect 15 pp / 22 pp | 0.38 / 0.76 | 0.57 / 0.96 | |
| X test, Bernoulli statistic: size with σ_f = 0.5; power at 15 / 22 pp | 0.072; 0.47 / 0.86 | 0.066; 0.72 / 0.98 | |
| Sign-flip X test: size; power at 15 / 22 pp | 0.019; 0.23 / 0.56 | 0.036; 0.46 / 0.89 | 0.046; 0.75 / 0.99 |
| π_small sampling SD at the null; at π = 0.14 | 0.048; 0.067 | 0.034; 0.046 | 0.026; 0.035 |
| Session shift 3.6 pp / 5.6 pp, power per size (4B, 9B) | 0.10-0.16 / 0.22-0.37 | 0.23-0.33 / 0.45-0.65 | |

Other scenarios are in the proposal's Evaluation section. At K = 32 the pooled
δ MDE is 8.1 pp (high noise), 6.5 pp (low base) and 5.9 pp (OpenCUA-
calibrated). The δ test's size is 0.042-0.054 across scenarios.

## 11. Decision rules (fixed before any confirm-split episode)

**DR0, validity.** Checked at the end of every A1 job and of ANC from
infrastructure records only; no outcome is read. The rule fires if any of
these holds:

- a (size, harness) cell lost more than 5% of its first-attempt episodes to
  infrastructure;
- a job ended without completing its base;
- a gate of section 3 turned out not to hold.

When it fires, no further job starts. The cause is investigated without
reading outcomes. Any code change is a new experiment id. Data already
collected are reported as incomplete.

**DR-A, anchor.** Read after ANC and before any A1 job.

- Paired bootstrap SE of (ours minus the public mean) per task.
- Kill if our success lies more than 2 SE outside [min, max] of the three
  public runs' success on the same completed tasks.
- Outcomes:
  - ANCHOR-FAIL: A1 does not start. Stop and debug; the question file's
    kill criterion, reworded under D11.
  - ANCHOR-PASS: A1 runs.
  - ANCHOR-INCOMPLETE (fewer than 58 tasks completed, or more than 10%
    infrastructure loss) or ANCHOR-UNAVAILABLE (section 3.1 item 9): A1 runs,
    and every S1a output carries the label "not externally anchored". Whether
    S1b may rest on an unanchored floor is decided in S1b's gauntlet.
- Operating characteristics (simulation, OpenCUA-calibrated, 4,000 data
  sets, 116 tasks):
  - false kill 0.8%;
  - a runtime deficit of 4.2 pp is caught with probability 0.19, 6.1 pp with
    0.48, 7.9 pp with 0.74, and 11.2 pp with 0.97;
  - at the 58-task minimum, a 7.9 pp deficit is caught with probability
    0.35.
  Only gross defects are reliably caught.

**DR1, floor.** If 4B's pooled success is below 10% under both harnesses,
S1b drops 4B, and π_small = π_9B. This is the dossier's criterion as a
ladder decision; the question file's swap to 122B-A10B is not funded.

**DR2, harness pair (reported classification).**

| Class | Condition |
|---|---|
| Present | the δ test or the X test rejects |
| Near-equivalent | not present, the 90% CI of pooled δ lies within ±7.5 pp, and the one-sided 95% upper bound of π_small is below 0.12 |
| Inconclusive | otherwise |

**DR3, sizing.** S1a's components are moment-matched into the generative
model of section 10.2:

- base rates and task SD from success and D_b;
- σ_b from X;
- σ_e from D_b − D_w;
- the session SD from the shift.

The registered simulator then reports the paired δ MDE and the ladder's
detectable share M for the candidate S1b allocations: 60 tasks x 4 sessions
x 1 rerun; 116 x 2 x 1; 60 x 2 x 2; 116 x 3 x 1; per rung, both harnesses.

**DR4, cost.** If any job's realized GPU-h per episode exceeds 0.011512 (the
high price), S1b's projection uses the realized value x 1.2, and a re-probe
precedes S1b. Otherwise S1b is projected from realized costs x 1.2.

**DR5, admission of the S1b scale ladder.**

- M is the smallest 4B harness share whose full shrinkage (larger rungs at
  share 0) the planned ladder detects with 80% power, one-sided 5%. It is
  computed by DR3's simulator with S1a's components. The planning value
  for 60 tasks x 4 sessions x 1 rerun per rung is 0.21 under the literature
  scenario and 0.27 under the OpenCUA calibration.
- Outcomes:
  - **GO** if the one-sided 95% lower bound of π_small exceeds M;
  - **NO-GO** if the one-sided 95% upper bound of π_small is below M;
  - **INCONCLUSIVE** otherwise.
- **GO** sends the harness ladder to the gauntlet.
- **NO-GO** means the ladder cannot detect shrinkage of this pair's share at
  an affordable size. S1b re-specifies the factor instead: the observation
  factor, once a harness variant that reads the accessibility tree is built
  and certified.
- **INCONCLUSIVE** lets S1b's gauntlet weigh more sessions at 4B and 9B
  first. Simulation finds sessions more valuable than tasks once the floor
  is noise-dominated (design C's result).
- This replaces, for the scale question, the question file's "paired MDE
  about 7-8 pp" line. That line has no derivation, and no affordable design
  reaches it for a variance share.

## 12. Seeds and randomization

Seeds are [42, 43, 44]:

| Seed | Used for |
|---|---|
| 42 | task draw, extension order, dev-task choice, anchor order, engine seed, bootstrap and permutation streams |
| 43 | session-1 episode orders |
| 44 | session-2 episode orders |

Each stream is `random.Random` over a string key naming its use (section
5). Decoding is greedy, so rerun variation comes from the environment,
timing and batched-serving numerics, not from sampling. This is disclosed.
The count of 2 sessions x 2 reruns is justified by power (section 10), not
by habit.

## 13. Stop rules

- Every job has a Slurm `--time` equal to its cap and `--signal=B:USR1@180`.
- On USR1, the driver dispatches no new episode. In-flight episodes are cut
  and recorded as cap-truncated. The engine stops and the lane's marker is
  written.
- A Slurm TIMEOUT keeps the records and marks the job incomplete.
- DR0 and DR-A can stop the stage.
- No job is rerun to improve an outcome. An aborted job's records are kept
  and reported.

## 14. Reported regardless of outcome

- Every estimand of section 9 with its interval: raw and corrected verdicts,
  per size and pooled, per domain descriptively.
- DR0-DR5 and DR-A outcomes.
- Infrastructure losses by type and cell; restarts per episode; cap
  truncations.
- The cost card of section 9 item 8, against the card's central and high
  prices.
- Truncation rates per cell. δ is also reported with truncation-hit episodes
  removed (sensitivity).
- Fractional checker scores; corrected-verdict flips; the P1-flagged
  sensitivity.
- Host snapshots and any foreign load.
- The anchor's full comparison, whatever its outcome.
- Every deviation from this file.

## 15. What S1a hands to Stage S1b (not registered here)

| Output | Use in S1b |
|---|---|
| Realized cost card | prices S1b in place of the synthetic card |
| D_b, D_w, X, π_small and their intervals | DR2 and DR5 decide which S1b is proposed |
| DR3 allocation grid | sizes S1b |
| A frozen harness, engine and task order | 4B and 9B data carry forward as the first rungs |

S1b also needs a replay-only serving probe v3 under its own registration.
It would measure the 27B-FP8 and 35B-A3B-FP8 multipliers, TPOT against V up
to 40, and the front-end fix. The proposal gives the details.

## 16. Design decisions for sign-off

1. Rescope Stage 1 to S1a, which is at most 8 GPU-h by caps (7.967), and a
   gated S1b.
2. Models: Qwen3.5-4B and 9B only. No 27B or 35B-A3B in S1a.
3. Harnesses: the certified pair, H-OSW-fixed and H-GA, with the upstream
   layout of each.
4. Observation: screenshot only. The accessibility-tree factor needs an
   uncertified harness variant and goes to S1b.
5. T = 15 for both harnesses, below both upstream defaults.
6. Thinking on (template default). max_tokens 2,048 for both; H-OSW's 32,768
   is lowered.
7. Greedy decoding (temperature 0.0, top_p 0.9) for both, the OSWorld runner
   defaults.
8. Engine settings exactly the cost card's.
9. Pool: confirm split minus the four K1 raw-gold failures (116 tasks).
   Base of 32, drawn by proportional largest-remainder apportionment.
10. Two sessions per size, at least 12 h apart, each with 2 within-session
    reruns (R = 4).
11. Harnesses interleaved within each session on one engine.
12. Continuous dispatch, and the outcome-blind fill rule in session-1 jobs.
13. Infrastructure-loss definition and a single replacement (section 7.2).
14. Raw verdicts primary; z-order-corrected verdicts secondary; P1 tasks
    flagged.
15. Session-aware X as the primary interaction statistic; within-task-
    session permutation test; sign-flip and Bernoulli forms as
    sensitivities.
16. π computed on the between-session floor.
17. DR0-DR5 and DR-A as written.
18. Caps of section 6.1, and the A0-derived K_base rule of section 6.2 (it
    can only lower K).
19. The OpenCUA-7B anchor on the upstream action path, read before A1.
20. Pre-freeze dev jobs O1, A0a and A0b (needs a program decision as D36
    did).
21. Serving OpenCUA-7B requires `--trust-remote-code` (model code from
    `xlangai/OpenCUA-7B`, pinned by revision and file hashes, reviewed). This
    is third-party code on a GPU under the R570 rule. It is admissible only
    by a D29-style decision; without one the anchor is UNAVAILABLE.
22. Quiet-host rule during A1 jobs.
23. GLMM secondary with the homogeneity likelihood-ratio test.
24. DR5 replaces the 7-8 pp line for the scale question.

## 17. Disclosures and known limitations

- **Narrow harness contrast.** The two harnesses share their layout, template
  lineage, prompt skeleton and thinking default. A null δ and X is the likely
  result, which DR2 and DR5 make informative.
- **No answer on scale or observation.** 4B and 9B are a 2.25x span, and the
  scale contrast is a screen with an MDE of about 17 pp at K = 32.
- **Session variance weakly identified.** With 2 sessions per size, a
  Holo3-sized shift (about 4 pp) is detected with power 0.10-0.33.
- **The floor is specific to this configuration:** greedy decoding, V of 16
  to 20 on vLLM, T = 15 and a 2,048-token thinking budget.
- **Cost model gaps.** The card's latencies are synthetic replays, and VM
  setup and checker time are excluded. Its history entries are 300 tokens,
  while both harnesses pass thinking back. The bound in the proposal raises
  the high price to 0.01331 GPU-h per episode at V = 16. Under that bound,
  section 6.2 lowers K_base to 24.
- **Upstream defaults lowered.** max_tokens 2,048 departs from H-OSW's
  upstream default, and greedy thinking can loop and truncate. Truncation is
  logged; the A0 gate and the δ sensitivity cover it.
- **Corrections are partial.** Only the z-order defect is corrected. Kevin's
  adjudication is pending.
- **Real task applications.** Guest-server restarts under LibreOffice and
  GIMP are bounded only through DR0. A7 bounds restarts on the probe desktop
  only, and that bound is for accessibility calls.
- **The anchor is weak.** It catches defects of roughly 8 pp or more, uses an
  uncertified (upstream) action path on purpose, and needs a remote-code
  decision.
- **Task overlap and generality.** The tasks overlap the mutation study, on
  purpose. Results cover 32-116 web-free tasks and one interface.
- **Recorded IDs.** No host address is recorded. The engine's GPU UUID may
  appear in NVML samples, as in job 466.

## 18. Sources (fetched 2026-10-08; hashes in the proposal's evidence bundle)

- cost card: `program/evidence/2026-10-07/serving-throughput-probe-v2/README.md`, `projection-v2.json`
- Holo3 session shift: `program/evidence/2026-10-07/holo3-v2/RESULTS.md`
- checker defects: `program/evidence/2026-10-08/q2-mutation-confirm/results/README.md`
- action path: `program/preregistrations/q2-action-path-v2.md`; `program/evidence/2026-10-08/q2-action-path-acceptance/README.md`
- OSWorld agent and runner at `bfd62bdc`: https://github.com/xlang-ai/OSWorld/blob/bfd62bdc5a3319809a236dc90ddbbaf3cb4b7e06/mm_agents/qwen35vl_agent.py and https://github.com/xlang-ai/OSWorld/blob/bfd62bdc5a3319809a236dc90ddbbaf3cb4b7e06/scripts/python/run_multienv_qwen35vl.py
- gym-anything agent at `aae6f7607`: https://github.com/cmu-l3/gym-anything/blob/aae6f7607e0f3d9d6306e1fefbad92bda99ca99a/agents/agents/qwen35vl.py
- Qwen3.5 model cards (OSWorld-Verified 35.6 for 4B and 41.8 for 9B, first-party, evaluation settings not stated): https://huggingface.co/Qwen/Qwen3.5-4B, https://huggingface.co/Qwen/Qwen3.5-9B
- OpenCUA-7B (MIT; 24.3% at 15 steps, first-party): https://huggingface.co/xlangai/OpenCUA-7B; paper https://arxiv.org/abs/2508.09123 (2025-08-12)
- public trajectories: https://huggingface.co/datasets/xlangai/ubuntu_osworld_verified_trajs (MIT, revision 5473c39e)
- rerun flips 12-14% on the web: https://arxiv.org/abs/2608.06171 (2026-08-06)
