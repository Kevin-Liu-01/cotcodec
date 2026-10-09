# Preregistration: q2-stage1-rescoped-v1 (Q2 Stage 1a: rerun-noise floor and harness screen on the certified harness pair)

**Status: DRAFT, not frozen (TBD: rewrite this line to the frozen wording at the freeze, as
D32 and D39 required).** This file has no ledger row. No confirm-split episode may run
under it. D49 (ii) admitted the pre-freeze development jobs O1 and A0a within S1a's caps
(A0b is not submitted while the anchor is unavailable); like every GPU episode they run
only after the action-path suite passes. Freezing needs the G0 items of section 3, the
constants of section 6.2 written into their open slots, a fresh pre-freeze audit, and the
sign-offs of section 18 (each an open slot), of which item 17 and the acceptance of an
unanchored read are Kevin's alone. A material change after the freeze is a new experiment
id. Every slot that is filled only at the freeze carries the placeholder that
`scripts/preregister.py freeze` refuses, so the guard refuses this file until each is
filled (section 22 lists them); no other text in this file trips the guard (a test fills
every slot on a scratch copy and freezes it).

- Drafted 2026-10-08 on branch `stage0/q2-stage1-rescope`; revised the same day after
  three adversarial pre-freeze reviews (section 22).
- Gauntlet proposal: `program/proposals/2026-10-08-q2-stage1-rescoped.md`.
- Design panel: three designs, two judges; this file is the winning design (A)
  with grafts from both judges, recorded in the proposal's iteration log.

## 1. Identity

- **Experiment id:** `q2-stage1-rescoped-v1`. This is Stage S1a of the
  rescoped Q2 Stage 1 (D47).
- **Question:** Q2 (`program/questions/q2-calibrated-cua-instrument.md`), Stage 1.
- **What it measures.** On OSWorld-Verified desktop tasks:
  - the rerun-noise floor, between and within serving sessions;
  - the harness effect between the two harnesses the action-path suite
    certifies: the main effect, the mean squared per-task harness effect and its
    task-specific part, and the harness share of within-task outcome variance.
  The models are Qwen3.5-4B and Qwen3.5-9B. The tasks are the web-free confirm
  split used by the checker-mutation study.
- **Claim level.** Confirmatory for the registered estimands of section 9, under
  the registered design, **for the sessions that ran**. Each size has two
  serving sessions; every interval and test resamples or randomizes tasks and
  holds the sessions fixed, so no claim is made about the population of
  sessions (section 9).
- **Out of scope:** any other harness; the observation factor; step budgets
  other than 15; sampled decoding, including H-GA's native sampling
  (temperature 1.0, top_p 0.95, top_k 20); larger models.
- **Why rescoped.** `serving-throughput-probe-v2` priced Stage 1 as designed
  at 431.5 GPU-h (job 466; `program/evidence/2026-10-07/serving-throughput-probe-v2/`).
  Its rule sends anything above 90 GPU-h back for rescoping before the
  gauntlet. The question file's 5,760-episode design is therefore not
  runnable.
- **Inputs it builds on.** All are frozen or committed:

  | Input | Status | Source |
  |---|---|---|
  | `q2-action-path-v2`, `-inputs`, `-executor` (and any accepted `-executor-a2`/`-a3`) | frozen, ledger rows 13-15; acceptance not yet run | `program/preregistrations/q2-action-path-v2*.md` |
  | `serving-throughput-probe-v2` | frozen, job 466 | cost card and engine settings |
  | `q2-holo3-rerun-audit-v2` | confirmatory for its rules (a)-(d) only | the two same-day Holo3 runs differ per task (v1 post-hoc McNemar, D10); v2 showed that checker time-dependence, step-count behaviour and visible environment failures do not explain the shift. A floor measured inside one session may understate the noise between sessions |
  | `q2-evaluator-mutation-v1` | descriptive (D35) | checker corrections and K1 task exclusions |

- **Code revision.** O1, A0a and A0b run from an export of the draft commit
  named in their manifests; O2, ANC and A1 from an export of the freeze commit,
  whose ledger row's git head is the code of record. Any change after A0 to the
  engine launcher, the episode driver, either harness client or the checker
  invocation requires that A0 job to be repeated (section 6.2).

## 2. What S1a decides, and what it does not

S1a stands on its own. Every exit is a reportable Q2 result.

1. **Noise floor.** The between-session rerun discordance D_b and the
   within-session discordance D_w, per size and pooled, under the stated
   configuration. The difference D_b − D_w is the session excess (prediction
   P1, section 12).
2. **Harness main effect.** δ = H-GA minus H-OSW-fixed in task-weighted
   success, pooled over sizes and per size.
3. **Harness terms and share.** X, the mean squared per-task harness effect
   (δ² plus the task-by-harness variance); X_c, its task-specific part; and π,
   the harness share of within-task outcome variance, per size.
4. **Floor criterion.** The question file's 4B floor criterion, as a ladder
   decision (DR1).
5. **First real cost card** for the certified pair: realized GPU-h and VM-h
   per episode, steps, output tokens, truncation at the token cap,
   setup/eval/queue times and infrastructure loss. It replaces the synthetic
   431.5 GPU-h projection.
6. **External runtime check (D11).** OpenCUA-7B at 15 steps against its three
   public 15-step runs on the same tasks.
7. **Admission rule for the scale ladder.** A pre-specified GO / NO-GO /
   INCONCLUSIVE rule (DR5). Under D47 only GO lets the ladder (S1b) go to the
   gauntlet.

S1a does **not** answer:

- whether the harness-plus-interface share shrinks with scale;
- the observation factor. Neither certified harness reads an accessibility
  tree: OSWorld `bfd62bdc` raises `ValueError` for any observation other than
  screenshot, and gym-anything `aae6f7607` has no accessibility path;
- 27B or 35B-A3B;
- step caps of 50 or 100;
- sampled decoding.

## 3. Gates

### 3.1 Before any GPU job (G0, CPU only, 0 GPU-h)

1. **Action-path acceptance, on v2's own verdict.** Every validity control
   C1-C4 passes; A1-A6 pass on one attempt (attempt 1, or a repair attempt
   `-a2`/`-a3` frozen under action-path v2 section 11); no section 11 kill
   fired; N* is that attempt's ladder value. A7 is not required, because S1a
   uses the screenshot setting only (action-path v2 section 7). The executor,
   IR and adapter digests are those of the accepted attempt's executor
   addendum, pinned by its ledger row: TBD. **If N* < 16, S1a does not start**
   and no GPU job runs (section 5.5). **At N* = 16 the draft goes back to review before
   A0a** (V = 16: the card's high price alone gives K_base 24 unless L_A0a is under about 4
   minutes, below any engine start-up; the lane and the manifest renderer refuse A0a below
   N* = 24, so its 25 minutes are not spent).
2. **Model receipts in a GPU-less lane.** Qwen3.5-4B (`Qwen/Qwen3.5-4B`,
   revision `851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a`) and OpenCUA-7B (`xlangai/OpenCUA-7B`,
   revision `a2efb7d2b104d477a4a2666a357e79550a28aafc`, about 16 GB) are fetched and receipted by a CPU-only
   Slurm job with no `--gres` line that asserts, as `vm-campaign.sbatch` does,
   that no GPU is visible. The existing fetch lanes request a GPU and are not
   used. Lane script: `infra/slurm/host-single-node/fetch-model-cpu.sbatch`,
   SHA-256 `22685e5e4dc9f88cd9d6ba7aec7189a89500a4f80d2464b8df86e08e76e33c6d`. It ran as
   job 971 (2026-10-08; TRES `cpu=8,mem=16G`, no GRES, Docker runtime runc, no
   `/dev/nvidia*` in its container; source `9d4205a`). 4B receipt SHA-256:
   `efc8848734965680b20cbd5995ae1fffb0f194de50cc40ad8da560938e84a81a` (artifact root
   `3b8a075149bffe4dea784db5b4b37bc0896688cba0b3de7d8d0f6e8ae6157b9e`, 9,342,907,469 B; the
   snapshot already on the host re-verified, the files equal the earlier receipt's). OpenCUA-7B
   receipt SHA-256: `8109da82afc90b04b91f40cae4338c0e91dc1215d0a924c48e030e007ea6a2bd`
   (artifact root `b3dd62bff3bbd7f3e71f13cf61552d8fd4919febaf1ff34e5c11e4ba5c65a4be`, 40
   files, 16,587,131,875 B); its four remote-code files are read and hashed in
   `program/evidence/2026-10-08/q2-stage1-g0/opencua-remote-code/README.md`. The 9B receipt
   exists (revision `c202236235762e1c871ad0ccb60c8ee5ba337b9a`).
3. **Episode driver** (`harness/q2_stage1/`, outside `harness/q2/`: every
   file under `harness/q2/` must be pinned by a frozen action-path table before
   an acceptance campaign is admitted, design decision 35 of action-path v2),
   reviewed and tested against a fake OpenAI-compatible engine on CPU. It:
   - reproduces each harness's upstream agent and step semantics (H-OSW-fixed:
     OSWorld `bfd62bdc` `lib_run_single.run_single_example`; H-GA:
     gym-anything `aae6f7607`'s runner): step counting, replies with no action,
     `wait`, `terminate`/`answer`, the step cap and evaluation after the last
     step;
   - applies the matched runtime of section 5.3 to both harnesses (the
     upstream OSWorld settle of 60 s after reset and 20 s before evaluation,
     no pause after execution, greedy sampling, 2,048 output tokens);
   - runs the guard's keyboard warm-up once per boot after `DesktopEnv.reset`
     and before the agent's first action (section 7.1 step 3);
   - handles an `IRError` raised from model output under that harness's rule
     for an unparseable reply, counts a checker metric that raises on agent
     state as score 0, and counts a context-variant fallback of H-GA not
     caused by a context-length rejection as an infrastructure loss (section
     7.2);
   - writes the episode records of `harness/q2_stage1/records.py` (schema
     `q2-stage1a-episode-v1`) and the step logs of section 7.3;
   - runs on the certified L0-fixed executor through the frozen IR;
   - checks that no `/dev/nvidia*` device is visible in its container before anything
     else (D12); one that is ends the episode, and the lane stops dispatching.
   Every difference from upstream is recorded in `harness/q2_stage1/design_diffs.md`
   (the action-path file `harness/q2/action_path/harness_design_diffs.md` keeps the
   action-path differences S1a inherits; it is pinned by a frozen action-path table and
   cannot take S1a's). The harness clients (`agents.py`) are checked against message lists
   recorded from the unmodified upstream agents (`tests/fixtures/q2_stage1/`). The runner
   runs in the checker-mutation study's metric image (section 4, "Episode container").
   Driver file digests: section 20 (`driver.py`, `agents.py`, `engine.py`,
   `osworld_live.py`, `lane.py`, `s1a-vm.sbatch`). Development smoke (job 978, 2026-10-08,
   CPU only, the scripted fake engine, dev tasks `2b94c692` and `01b269ae` under both
   harnesses): 3 of 3 episodes scored end to end (cold boot 18 s, setup 11 s, warm-up
   0.2 s, both settles, a click and `terminate`, `DesktopEnv.evaluate()`, capture,
   teardown; slot 114 s); offline rescoring (job 983) matched the live score on 3 of 3.
4. **Engine bridge under D13.** Runners join each VM container's
   `--network none` namespace, so they reach the engine only through a
   Unix-domain socket. The socket is bind-mounted into each GPU-less runner
   and forwarded to the engine's port, which is bound to 127.0.0.1 only. No
   Docker network is created. Built: `harness/q2_stage1/bridge.py` (the GPU job's
   workload: engine, `/health`, forwarder, `ready.json`, stop on the VM job's `vm.done` or
   the lane's USR1 with `usr1.json` and the checkpoint marker), `engine.py` (the client)
   and the lane's resolution of the GPU job's bridge directory
   (`experiments/manifests/q2-stage1/gpu-engine.template.yaml` gives the pairing). The
   remaining exposure: any process of the research account on the host can connect to the
   socket (mode 0600) while it exists; the host is single-user (D13).
5. **Offline task setup, setup only.** For every one of the 116 pool tasks and
   every one of the 32 dev-split tasks, the task's setup is run on one VM
   from the pinned file cache (the mutation study's `file-cache-receipts.tsv`,
   447 files with SHA-256), with no model call, no agent action and no checker
   verdict. This is the only contact any job has with a confirm task before the
   freeze. Built: `driver.py` `mode: setup-only` through the lane.
   - **First pass** (`experiments/manifests/q2-stage1/setup-check-v1.json`, one attempt
     per task, no re-queue). Ran as job 982 (2026-10-08, CPU only, one VM at a time,
     source `ac6c7cd`, 79 minutes): 148 of 148 setups raised no error (116 pool, 32 dev;
     cold boot median 18.3 s; setup median 11.4 s including OSWorld's import, longest
     120 s, task `26150609`; slot median 31 s); no model call, no agent action, no checker
     run, no container left. Records:
     `program/evidence/2026-10-08/q2-stage1-g0/setup-check/setup.jsonl` (SHA-256
     `51fa959aa74fa94ae807f5fb7882c1e6ef7760e832025658c16abdfdaec5b16e`). **What it could
     not see:** the guest server answers `/setup/execute` with HTTP 200 and the command's
     `returncode` for any command that finishes, the pinned `_execute_setup`,
     `_launch_setup` and `_activate_window_setup` only log a reply that is not 200, and the
     records kept no per-step result, so "raised no error" is all it shows. Its container
     logs show one failure: base task `26150609`'s second step, `pip install pygame`, timed
     out after 120 s (HTTP 500), and OSWorld went on, as it would upstream. The configs show
     three more install steps never checked offline: `e2b5e914` (pool, extension block 4)
     runs `code --install-extension ms-python.python`, a Marketplace install that needs the
     network; base task `53ad5833` installs a local `.vsix` its checker depends on
     (`vscode_config` through the extension's `OpenProject` command); and `d38192b0`'s
     postconfig runs `pip install` of a wheel the file cache supplies, which no live VM has
     run.
   - **Second pass** (`experiments/manifests/q2-stage1/setup-check-v2.json`, amended after
     the pre-freeze audit): the same 148 setups with every guest `/setup/*` reply recorded
     per step (HTTP status, `returncode`, stderr tail; `osworld_live`), the registered
     diagnostics after setup (`plan.SETUP_DIAGNOSTICS`: `code --list-extensions` for
     `53ad5833` and `e2b5e914`), and each task's postconfig steps on the untouched initial
     state (no getter and no metric runs, so no verdict exists); a slot that fails is
     re-queued once. Ran as job 1011 (2026-10-08, after the rule was committed; CPU only,
     8 CPUs, one VM at a time, source `8b4a874`, 87 minutes): 148 tasks in 151 slots (the 3
     that failed were re-queued and failed again the same way); 145 setups clean; 439 setup
     and 241 postconfig replies recorded; cold boot median 18.3 s, setup median 11.4 s
     (longest 129 s, `26150609`), slot median 32 s; no model call, no agent action, no
     verdict, no container left. Records:
     `program/evidence/2026-10-08/q2-stage1-g0/setup-check-v2/setup.jsonl` (SHA-256
     `97e792f72a52ff3a380f74dd52ca57c85ed0e496d0e0faf90d685d9d8a94a4ca`,
     `plan.SETUP_CHECK_SHA256`; the lane and both renderers refuse any other file). The
     committed copy drops the replies' stdout tails, because one postconfig prints the
     Thunderbird test profile's stored credentials; the host's original keeps them (SHA-256
     `da37184134df2d06ff19693c4a6f5411972762b6d22d9f25199fd672cb62b0c6`), and the exclusion
     rule reads none of them. Findings:
     - `26150609` (base before the re-draw): step 2, `pip install pygame`, HTTP 500 (timed
       out after 120 s) on both attempts;
     - `e2b5e914`: step 1, `code --install-extension ms-python.python`, HTTP 200 with
       returncode 1 (`getaddrinfo EAI_AGAIN marketplace.visualstudio.com`), and `code
       --list-extensions` lacks the extension;
     - `982d12a5` (base before the re-draw; new): step 1 sets VS Code's colour theme through
       `jq`, which the guest image lacks (`/bin/sh: 1: jq: not found`, returncode 127, both
       attempts), so the task would start without its initial theme. The first pass could
       not see this;
     - `53ad5833`: the local `.vsix` installs offline (`undefined_publisher.eval@0.0.1` is
       listed) and its setup is clean;
     - `d38192b0`: its postconfig `pip install` of the cached wheel succeeds offline
       (returncode 0); its next postconfig step, the attachment check, exits 2 on the initial
       state ("Attachment not detected!"), which is the agent's part;
     - postconfig steps that fail on the initial state because they read what the agent must
       produce, reported and not judged: `415ef462` (dev; `diff` of a file the agent must
       save), `9bc3cc16` (`ls` of a backup the agent must make) and `d38192b0` (above).

     Every one of the 32 dev tasks completes cleanly, so A0a's dev tasks are unchanged: the
     first V/4 of the seeded dev order, `6a33f9b9`, `bf4e9888`, `d681960f`, `4172ea6e` and, at
     V = 20, `12382c62`.
   - **Exclusion.** Section 5.4's offline-setup exclusion (rules (a)-(c)), registered and
     committed before the second pass ran, is applied once to its records, before any GPU
     episode and before the draw (`plan.offline_exclusions`; `plan.OFFLINE_EXCLUDED`).
     **Excluded: `26150609` (rules (a), (b)), `982d12a5` (rule (b)) and `e2b5e914` (rules
     (a), (b)),** all pool tasks; no dev task. Two of them were in the K = 32 base, so the
     base is re-drawn on the eligible pool of 113 tasks (section 5.4); K_base's floor of 32 is
     unchanged.
   - **Decision on `26150609` (the audit's option (b)).** The question the first draft left
     open is decided by the rule, not by judgment: its setup installs a package from the
     network (rule (a)), so it leaves the pool before the draw, and the base is re-drawn by
     the registered seeded procedure (section 5.4). Option (a), keeping it under a rule that
     a step failing the same way in every episode counts as completed when the checker does
     not read its product, is not taken: the agent's VM would lack the pygame the upstream
     setup installs, a task different from upstream. Kevin's sign-off: section 18.
6. **Final-state capture and offline rescoring.** After the checker runs, the
   files the checker read are copied off the VM and hashed, and a CPU tool
   rescores a captured state with the raw and the corrected checker, so every
   verdict can be checked offline. Built: `osworld_live.py` (capture: every file the
   checker's `get_file` returned, the absent ones, and the task cache, hashed; a capture
   sweep runs every result getter after `evaluate()`, so an `and` that stopped early or a
   `FAIL` still leaves every input captured) and `rescore.py` (`capture`, `merge`). Tool
   digests: section 20.
7. **Per-episode cost logging** (section 7.3).
8. **Corrected comparator** `compare_pptx_files_zinv`. It ignores shape order
   only among shapes whose frames are apart (the mutation operator's rule: known frames,
   widened by rotation, more than 2 mm apart). It is validated on CPU on the
   stored confirm mutants and golds before the freeze:
   - it passes the 29 audit-confirmed `pptx.eq.zorder_nonoverlap` mutants
     checked by `compare_pptx_files`;
   - it gives the original comparator's verdict on every other evaluable
     `compare_pptx_files` mutant and on every gold;
   - the 6 unresolved `compare_pptx_files` candidates are reported, not used
     to tune it;
   - `compare_pptx_files_tolerant` is not corrected (its one confirmed z-order
     false negative, task `a434992a`, is flagged instead, section 8).
   Comparator: `harness/q2_stage1/zinv.py`, SHA-256
   `64899d5056f4791008c2a10c38a7b0fbb94fbe912d20a702ec74851a0ca7f655` (section 20). Shapes
   are paired as the comparator examines them (kind; stripped text; geometry within its own
   tolerance when the task examines geometry, else geometry breaks ties); a shape moves past
   another only if the two are apart by the operator's rule (`zorder_pair_is_inert`: known,
   rotation-widened frames more than 2 mm apart). Validation (`rescore.py validate-zinv`,
   the pinned `DesktopEnv.evaluate()` with the stub VM in the metric image, every evaluable
   mutant, gold and do-nothing state of the 16 tasks whose every metric is
   `compare_pptx_files`: 291 items) **passes** in its third run (job 1000, 2026-10-08):
   the 29 confirmed mutants pass, the 256 other items (214 mutants, 21 golds, 21
   do-nothing states) keep the original verdict, the fresh raw scoring reproduces the
   stored verdict on 291 of 291, and the 6 unresolved candidates are reported (all 6 pass
   under the correction). The first two runs failed the gate and are kept: job 980 (0 of
   29: exact frames never matched the raw golds, which a LibreOffice save rounds by 720
   EMU) and job 995 (26 of 29: an empty text run counted as text, and text-only pairing
   kept two identical pictures in their swapped order where `examine_modify_height` reads
   geometry); each fix came from the confirmed mutants that failed, so the 29 are a
   development set as much as a gate, and no run changed the verdict of any other item.
   Evidence: `program/evidence/2026-10-08/q2-stage1-g0/zinv/`.
9. **Anchor feasibility** (section 5.7), on CPU:
   1. the vLLM v0.31.0 registry lists `OpenCUAForConditionalGeneration`;
   2. a D29-style decision admits OpenCUA-7B's remote code (`--trust-remote-code`,
      pinned by revision and file hashes, reviewed) on a GPU under R570;
   3. after O1, a CPU-only container from O1's image, in the GPU-less lane of
      item 2, loads `AutoConfig` and `AutoTokenizer` from the pinned revision
      with `trust_remote_code` (configuration and `tokenization_opencua.py`, a
      tiktoken tokenizer that imports `transformers.tokenization_utils`), and
      vLLM's `EngineArgs` to `ModelConfig` validation accepts the anchor argv
      of section 4 (`max_model_len` 32,768, below the model's 128,000);
   4. the public runs' per-task `result.txt` members can be read by ranged
      reads; member manifest SHA-256
      `55d0337712e38966dbd5a42c0838cfdc4835c8dc589895a912f2919ead930d20`
      (`program/evidence/2026-10-07/holo3-v2/receipt-v2-final.json`);
   5. the public run's arguments are read from the archive and recorded: CoT
      level, history type, image history length, coordinate type, system
      prompt choice (`--use_old_sys_prompt`), sampling, max tokens and pause
      after each step; a setting the archive does not record takes the pinned
      runner's default. Recorded values (`anchor.py public-settings`, the three runs'
      `args.json` agree; `program/evidence/2026-10-08/q2-stage1-g0/anchor/public-settings.json`):
      CoT level `l2`, history `action_history`, 3 history images, coordinate type
      `qwen25`, temperature 0, top_p 0.9, max_tokens 2,048, no stop token, 15 steps,
      **3.0 s after each step** (the pinned runner's default is 5.0 s), 1920x1080,
      provider `aws`, `test_nogdrive.json`; served model names `opencua-7b-15step-2`,
      `-3` and `-4`; run window 2025-07-29 09:47 to 2025-07-30 05:03 (the runner's clock,
      no zone). Not recorded: the system prompt choice (`--use_old_sys_prompt` did not exist
      then), so the rule gives the runner default (the V2 prompt family). Finding
      (`anchor.py prompt-check`): neither choice at `bfd62bdc` reproduces the L2 system
      prompt the public runs' agent sent (`mm_agents/opencua_agent.py` at `00804f8`,
      `AGNET_SYS_PROMPT_L2`): the old-prompt option adds a password sentence and changes
      `terminate`'s status enum from `fail` to `failure` (L1 and L3 are equal), and the
      default is a different template;
   6. the public runs' OSWorld revision, if the archive records it, is compared
      with `b138d348` for the 116 tasks' configs and evaluators; tasks with any
      difference leave the anchor reading. Revision: not recorded in the archive;
      inferred `00804f811874ea34ddfdd2e6b3a2fe307311f57c` (`main` when the runs began; no
      commit touched `evaluation_examples/` or `desktop_env/evaluators/` from 2025-07-27
      until `dd488c7` at 2025-07-30 06:07 UTC, which is inside the compared range).
      Compared (`anchor.py evaluator-diff`, on the host's OSWorld clone): each task's
      config, and the AST (docstrings, comments and layout removed) of every metric and
      getter definition the task reaches inside `desktop_env/evaluators`. Excluded tasks:
      **110 of 116** (`program/evidence/2026-10-08/q2-stage1-g0/anchor/evaluator-diff.json`):
      36 configs differ (21 instructions, 21 evaluator specifications, 4 setup
      configurations), 79 tasks differ in their config or a metric function
      (`compare_table` 33, `compare_pptx_files` 18, ...), and `get_vm_file` (103 tasks) and
      `get_cloud_file` (84) changed (atomic writes). `DesktopEnv.evaluate` differs in the
      proxy flag and a dict-form `FAIL` only. At most 6 tasks remain readable (37 even if
      the getter refactors were ignored), fewer than the 58 section 5.7 requires.
   If 1, 2, 4, 5 or 6 fails (6 fails when fewer than 58 tasks remain readable), A0b and
   ANC are not submitted and the anchor is UNAVAILABLE before any GPU job; if 3 fails, the
   same holds after O1. The A1 caps then follow the remainder rule of section 6.1.
   **Outcome (2026-10-08): item 6 fails, so the anchor is UNAVAILABLE before any GPU
   job**, A0b and ANC are not submitted, and the branch is "anchor unavailable before
   A0b" (T_A1 111 minutes, total caps 478 minutes, K_base 32 at the card's high price;
   section 6.1). Item 3's development dry run fails as well (below). Items 1, 2 and 4
   pass: the vLLM v0.31.0 registry lists the architecture (dry run below); D49 (iii)
   admits the remote code, read and hashed in
   `program/evidence/2026-10-08/q2-stage1-g0/opencua-remote-code/README.md`; the archive
   listing holds 1,079 `result.txt` members. Item 3 is built (`anchor.py check-vllm`,
   which refuses a snapshot whose remote code differs from the reviewed hashes); its
   development dry run (job 998 from `6c5948e`, CPU only, no network, the existing overlay
   `sha256:7d4595f98601d50f7393c447a1d0618d55cda1b7cf60e2d016ab5c6f47cc872e`: vLLM
   0.31.0, transformers 5.17.0) loaded `AutoConfig` but not the tokenizer (`ValueError:
   unk_token should not be set in dumping mode when additional_special_tokens is None`,
   also through vLLM's own `vllm.tokenizers.get_tokenizer`, so the engine could not load
   it), and vLLM's `ModelConfig` validation cannot run without a device ("Failed to infer
   device type"), so that part of item 3 cannot run CPU-only as written.
10. **Plan file.** `scripts/render_q2_stage1_plan.py` (committed and tested,
    section 20) writes the draw, the seeded orders, the anchor order, the
    engine and sampling arguments and, at the freeze, the constants and the job
    list. Draft plan SHA-256 (K = 32 on the eligible pool, no constants):
    `4679ac954847e3eab13973300993befd1af1f46938a89b714706ea792fb1bd21`. Frozen plan SHA-256: TBD.
    Every registered VM job's lane manifest is rendered from the plan by
    `scripts/render_q2_stage1_manifest.py` (section 5.5), and the lane refuses one
    whose slots differ.
11. **Analysis code** (`harness/q2_stage1/`: `estimators.py`, `records.py`,
    `rules.py`, `plan.py`, `analysis.py`), committed and tested on CPU
    (section 20).
12. **GLMM.** The glmmTMB script and a pinned CPU container that runs it,
    tested on synthetic data. Script: `harness/q2_stage1/glmm.R` (section 20; 200
    parametric-bootstrap refits by default); input writer `glmm.py`. Container:
    `infra/q2-stage1/glmm/Dockerfile` (SHA-256
    `e4a09458264a58a783ec91fed91b8e500c83a91c826fbaaa10b9ceb998df86b4`; `rocker/r-ver:4.4.2`
    by digest, CRAN pinned to the 2025-02-27 Posit snapshot), built by job 972 as
    `sha256:b15584f3954f1c83fc3e5067e29c57c5c55e3b2a50ef28e4e68a394e595aabed` (R 4.4.2,
    glmmTMB 1.1.10, TMB 1.9.16; package lock `/opt/q2/r-packages.json`, SHA-256
    `abb8871de4549732cd396dc60fc1f2aec78bf1fffad788cb841e8bf61668bfc7`). Acceptance on
    synthetic data from the registered generative model (32 tasks, 512 episodes):
    job 984 (2026-10-08, 5 min 49 s, CPU only, no network): both fits converged with
    positive-definite Hessians; 200 refits used, none failed, 42 not converged (reported);
    estimated variances task 2.82 (generating 2.25), task:harness 0.50 (1.00),
    task:session 0.43 (0.09), every other component near 0; the task:harness
    likelihood-ratio test gives chi-square 2.64 (p 0.104, boundary-corrected 0.052).
    Evidence: `program/evidence/2026-10-08/q2-stage1-g0/glmm/`.

### 3.2 Before any confirm-split episode

1. O1 and A0a have run (A0b only if the anchor were available; it is not). The
   constants of section 6.2 are computed from their records by
   `harness.q2_stage1.plan.a0a_measurements` and `plan.freeze_constants`
   (`scripts/render_q2_stage1_plan.py` reads A0a's lane run directory and its GPU
   job's bridge directory itself; no constant is typed) and written into section
   6.2's open slots. A0a's gates hold (section 6.2).
2. Fresh pre-freeze audit, then freeze (`scripts/preregister.py freeze`).
3. No model episode and no checker run on agent state touches a confirm task
   before the freeze. G0 item 5's setup-only check is the sole contact. A0a and
   A0b use dev-split tasks only.

## 4. Frozen inputs (pinned at freeze; values known now are given)

| Input | Pin |
|---|---|
| OSWorld runtime | `xlang-ai/OSWorld` at `b138d348256078fa634fc3b73567a7337c793e6b` (as action-path v2) |
| VM image, guest disk, VM settings, lane | as `q2-action-path-v2` section 2.1 (VM image `happysixd/osworld-docker@sha256:0e6497a9295647cf05bf2b2af522fdd79bdeba2737595259cab310a3bcf6baa9`, 4 cores per VM) |
| Episode container | the checker-mutation study's metric image `sha256:2006c1a9247e4911a82508cd22e9d9a7efc5c13e35a20e8a03baac7112876230` (`infra/q2-mutation/metric/Dockerfile`: OSWorld `b138d348`'s `uv.lock` in `/opt/venv-lock`, Python 3.12.13, Pillow 11.0.0, python-pptx 1.0.2), run GPU-less, read-only, with no capabilities in the VM container's network namespace (`harness/q2_stage1/lane.py`). It replaces the action-path suite's stdlib runner image `sha256:ac2b5815...` for S1a: the harness clients need Pillow for the upstream image processing and the checker needs OSWorld's environment; the transport code it runs is the certified standard-library code, unchanged (`harness/q2_stage1/design_diffs.md`) |
| OSWorld tree and file cache | the checker-mutation study's inputs: the OSWorld checkout at `b138d348` and the file cache at `1e112283` (447 files, `file-cache-receipts.tsv`), mounted read-only |
| Executor, IR, harness adapters | file digests of the accepted attempt's executor addendum (G0 item 1), by ledger row: TBD |
| H-OSW-fixed upstream | OSWorld `bfd62bdc5a3319809a236dc90ddbbaf3cb4b7e06` `mm_agents/qwen35vl_agent.py`, SHA-256 `1f39be92cf5461d9671ab9307a69c05691abf0226aa6b53d2af332003a5096fe`; `lib_run_single.py` `6d27d0fed9f4cbc69332cb3a01de3394b486f33d0309316f69c93036a161f74c`; `scripts/python/run_multienv_qwen35vl.py` `a3bf2a6343f470d1c0b55b136ddea58b0d3bfe5970760025add39e8275ba6bb1` (fetched 2026-10-08; the agent equals `harness/q2/action_path/upstream/PROVENANCE.json`) |
| H-GA upstream | gym-anything `aae6f7607e0f3d9d6306e1fefbad92bda99ca99a` `agents/agents/qwen35vl.py`, SHA-256 `93666f2751d99dfee0034700f65385ca2db1544e3d9a0d194807050d2edea1a5` (equal to PROVENANCE); its base `agents/agents/qwen3vl.py` `264f6666014ab76f2b9a805739fc12d48e2d76ca9c1b1575f207a16112804010`; runner `agents/evaluation/run_single.py` `f0baa3e86dc0fef7fe600ed1f7446854b598796ec5bbb69cfca9aa9787caf041` (fetched 2026-10-08) |
| Anchor agent (upstream path) | OSWorld `bfd62bdc` `mm_agents/opencua/opencua_agent.py` `4db7a7615e696a87584e7f2ed64e826ac61ed58b8e8f85f4f1ddca520c61f029`, `prompts.py` `9899d2ae7a362b90e86bf16c5e1ce8e861306e0151ae4921ed27f97d7b002bd4`, `utils.py` `e2c38af08e50709ef2c8ccf575fabc28d6b01bc1a6a0b6e9aa09e4873cee1303`, `__init__.py` `af3781df0c2bc3cb6501c90761a9e60230b61ef87dd078d2028ffb3a2cf5d828`; runner `scripts/python/run_multienv_opencua.py` `02df990ad83c6663a202f2516bf3aedf60079fc7aafe8043ea88e5842a90c1b3` and `lib_run_single.run_single_example_opencua` (fetched 2026-10-08). Its run settings: G0 item 9.5 |
| Engine | vLLM v0.31.0 (commit `db9527a46873454610df6dbedf79a36d6bf1a7f6`), base `docker.io/vllm/vllm-openai@sha256:b18abb2df97b8f798e81862bd93f872ea18613372e2c3adc0cc2ac21e66ac12f`, cu129 overlay rebuilt by O1 and O2 from the draft and freeze commits |
| S1a engine flags | the `serving-throughput-probe-v2` contract's, equal to job 466's argv (`plan.CARD_ENGINE_FLAGS`; a test checks it): TP 1, bf16, seed 42, `max_model_len` 131072, `gpu_memory_utilization` 0.90, `max_num_seqs` 256, `max_num_batched_tokens` 8192, prefix caching on, `generation_config: vllm`, at most 20 images (1920x1080) and no video per prompt, no reasoning parser, no speculative decoding |
| Anchor engine flags | the S1a flags except `max_model_len` 32768 (OpenCUA-7B derives 128,000 and has no rope scaling, so vLLM refuses 131,072), at most 4 images per prompt (the agent sends at most 3), and `--trust-remote-code` (`plan.engine_argv(..., anchor=True)`) |
| Request sampling | both Qwen harnesses: temperature 0.0, top_p 0.9, top_k −1, max_tokens 2,048 (`plan.sampling`); vLLM decodes greedily at temperature 0 and ignores top_p and top_k |
| Models | `Qwen/Qwen3.5-9B` at `c202236235762e1c871ad0ccb60c8ee5ba337b9a`, `Qwen/Qwen3.5-4B` at `851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a` (Apache-2.0); anchor `xlangai/OpenCUA-7B` at `a2efb7d2b104d477a4a2666a357e79550a28aafc` (MIT) |
| Tasks | `program/evidence/q2-mutation/splits.json` (SHA-256 `2099792e6fb86c69e4f79b1ce47d2839cc25623f5c4633698e95822553c007d9`) and the sanitized task files |
| Public anchor runs | `xlangai/ubuntu_osworld_verified_trajs` at `5473c39e42a538a187a9b2c2b499db59d560fd8c`, archive `opencua_agent-opencua_7b-cot_l2-action_history-3image-Ubuntu-15steps.zip` (LFS SHA-256 `b642e1212d3ebb87e88addc0c55525b12d1ce8b9b253306fa7706908778e9688`) |
| Code of record | section 20 |

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

Both are certified by `q2-action-path-v2` A2 and A3, within the certified
action set (section 7.3 counts what lies outside it):

- **H-OSW-fixed:** OSWorld `bfd62bdc` `Qwen35VLAgent` with its own-spec fixes
  (action-path v2 section 3).
- **H-GA:** gym-anything `aae6f7607` `qwen35vl` with its IR adapter; its parser
  and prompt are unmodified, its sampling is not (section 5.3).

Each harness keeps its own system prompt, tool description, parser and
message layout. Both use the same upstream layout:

- 100 history turns;
- at most 20 live screenshots, with older ones folded in blocks of 10;
- every later turn wrapped as a tool response;
- the full reply, thinking included, passed back into history. The Qwen3.5
  template keeps that thinking, because every later user turn is a tool
  response.

They differ by design, and the differences are part of the harness factor
unless the last column says S1a matches them:

| Area | H-OSW-fixed (upstream) | H-GA (upstream) | In S1a |
|---|---|---|---|
| Modifiers on clicks | yes (via `text`) | no | as upstream |
| Horizontal scroll | `hscroll`, mapped to vertical | absent | as upstream |
| Drag | from the current pointer | two-point | as upstream |
| Scroll units | its own | magnitude 1 to 10 | as upstream |
| `wait` | waits its time | the step returns only the wait | as upstream |
| Reply that does not parse, or parses to invalid IR (`IRError`) | no action that step | a one-second wait | as upstream, counted per harness |
| `terminate` status | own handling | reported through `metadata.status` | as upstream |
| Context fallback on a failed call | none | retries with shorter history on any exception | as upstream; a fallback not caused by a context-length rejection is an infrastructure loss (section 7.2) |
| Upstream sampling | temperature 0.0, top_p 0.9 (runner defaults) | temperature 1.0, top_p 0.95, top_k 20 (agent defaults) | matched: greedy for both |
| Upstream token budget | 32,768 | 2,048 | matched: 2,048 |
| Upstream settle | 60 s after reset, 20 s before evaluation | none (`post_reset_observation_delay` 0.0) | matched: 60 s and 20 s for both |
| Upstream step cap | 50 | task-dependent | matched: 15 |
| Date in the system prompt | today (the runner's clock) | today | matched and pinned: Thursday, October 08, 2026 for every A0a, ANC and A1 episode (`plan.PROMPT_DATE`, the lane manifest's `date`), so no pair differs in prompt text |

The full list is `harness/q2/action_path/harness_design_diffs.md`.

### 5.3 Observation, step cap, token budget, sampling, settle

- **Observation:** screenshot only (`require_a11y_tree=False`), 1920x1080.
- **Step cap:** T = 15 for both harnesses.
- **Settle:** OSWorld's 60 s after `DesktopEnv.reset` and 20 s before
  evaluation, for both harnesses; no pause after execution (the OSWorld Qwen
  runner's `sleep_after_execution` default, 0.0).
- **Thinking:** on, by the Qwen3.5 template default. Neither harness sends
  `chat_template_kwargs`.
- **max_tokens:** 2,048 for both. H-OSW's runner default of 32,768 is lowered
  and disclosed. The token cap is held equal; truncation rates at the cap, and
  how each harness handles a truncated reply, still differ by harness and are
  part of the harness factor.
- **Sampling, both harnesses:** temperature 0.0, top_p 0.9 and top_k −1,
  sent explicitly. This is greedy decoding. It is imposed on H-GA, whose agent
  samples at temperature 1.0, so the harness factor excludes sampling. The
  Qwen model card's recommended thinking-mode sampling is not used (disclosed).
- **Thinking pass-back and the serving probe's rule.** Both harnesses pass
  thinking back, so `serving-throughput-probe-v2` section 4 item 7 requires
  Stage 1 to strip it or re-probe. A0a is that re-probe: it measures real
  per-episode cost with thinking passed back, at the card's engine settings,
  and the K-rule takes c_proj = max(the card's high price, 1.25 x A0a's
  measurement). Its limits: 9B only (4B by the card's multiplier 1.0), one
  wave of V episodes on dev tasks. Design decision 6 asks the program to
  accept this substitution.
- **Context:** the largest context is 62,950 tokens even if every history
  turn carries a full 2,048-token thinking block (proposal, cost analysis).
  This is below 131,072, so a context-length fallback should never fire.

### 5.4 Tasks

- **Pool (116 tasks).** The 120-task confirm split of
  `splits.json` (seed 42, stratified by domain x checker class) minus the four
  K1 raw-gold failures of the checker-mutation study (`0a0faba3`, `15aece23`,
  `ac1b39ff`, `ed43c15f`). Their checkers fail their own gold. Pool by domain:
  gimp 8, calc 28, impress 24, writer 12, multi_apps 24, thunderbird 7, vlc 6,
  vs_code 7.
- **Offline-setup exclusion** (`plan.offline_exclusions`; registered after the
  pre-freeze audit and before G0 item 5's second pass ran; applied once, before
  any GPU episode and before the draw). It reads only the task configs, as the
  setup-check records keep them, and the setup-only records; no agent has acted
  and no checker has produced a verdict, so it is outcome-blind. A pool or dev
  task leaves the eligible set if
  - (a) a setup or postconfig step installs software from the network: a
    `pip install` of a package name (not a local file), a
    `code --install-extension` of a Marketplace id (not a local `.vsix`), or any
    apt, apt-get or snap install. The VMs run with `--network none`, so the step
    fails in every episode;
  - (b) in the second setup-only pass the task's setup did not complete
    cleanly: a setup step's guest reply was not HTTP 200 or carried a non-zero
    `returncode`, a step raised, the slot was lost on its final attempt, or a
    registered diagnostic did not show the step's product (`code
    --list-extensions` lacks the extension the step installs);
  - (c) a postconfig step that installs software (any of (a)'s installers,
    local or not) failed on the untouched initial state in that pass.

  Other postconfig steps are not judged on the initial state: they act on the
  agent's final state (a window the agent must open, a file it must write), so
  their failure there can be the agent's. **Eligible pool (113 tasks):** the pool
  minus `26150609`, `982d12a5` and `e2b5e914` (G0 item 5): gimp 8, calc 28,
  impress 24, writer 12, multi_apps 23, thunderbird 7, vlc 6, vs_code 5. The draw
  below runs on the eligible pool; the 32-task floor (section 6.2) is unchanged.
- **Base set (K_base = 24 or 32, by the rule of section 6.2).**
  - Allocation: plain largest-remainder apportionment over domains, ties
    broken by domain name. At K = 32 on the eligible pool: gimp 2, calc 8,
    impress 7, writer 3, multi_apps 7, thunderbird 2, vlc 2, vs_code 1.
  - Draw: within each domain, the first n_d ids of the eligible pool's
    `sorted(ids)` shuffled by `random.Random(f"q2-stage1a:base:42:{domain}")`
    (`plan.draw_tasks`).
  - The K = 24 and K = 16 bases are nested in the K = 32 base.
  - **The base is fixed at the freeze and is the primary analysis set for
    every estimand and every decision rule.**
- **Extension order.** The remaining tasks, sorted and shuffled by
  `random.Random("q2-stage1a:ext:42")`, are cut into blocks of 8; the last
  block may be shorter. Extension blocks enter only the registered secondary
  analysis set (section 5.6).
  - K = 32 base: `02ce9a50 035f41ba 0a211154 0bf05a7d 185f29bd 2cd43775 358aa0a7 4188d3a4 47f7c0ce 4f07fbe9 5df7b33a 66399b0d 6ed0a554 70bca0cc 72b810ef 7a4deb26 7efeb4b1 81c425f5 9b7bc335 9cf05d24 a01fbce3 c59742c0 d06f0d4d dfac9ee8 e2dd0213 e8172110 eb303e01 ecb0df7a edb61b14 f178a4a9 f9584479 fba2c100`;
    81 extension tasks in 10 blocks of 8 and one of 1. The re-draw replaced
    `26150609`, `3a93cae4`, `53ad5833`, `881deb30` and `982d12a5` with `02ce9a50`,
    `47f7c0ce`, `6ed0a554`, `81c425f5` and `eb303e01` (two exclusions change the
    multi_apps and vs_code lists the seeded shuffles run on). The K = 24 and K = 16
    bases nest in it. The proposal bundle's `analysis/task-draw-K*.json` are the
    same procedure on the 116-task pool, before the exclusion.
- **Dev tasks.** The dev split (`splits.json`, 32 tasks), sorted, shuffled by
  `random.Random("q2-stage1a:dev:42")`, **filtered** to tasks whose setup
  completes offline and that the offline-setup exclusion keeps (G0 item 5's
  second pass; all 32 do), **then** the first V/4 taken for A0a (5 at
  V = 20, 4 at V = 16) and the first 4 for A0b (`plan.dev_tasks`).

### 5.5 Sessions, blocks, reruns, order, concurrency

- **A session** is one GPU job for one size, with a fresh engine, paired with
  one CPU-only VM job (D12) holding a fresh pool of VMs. Every episode is a
  cold boot from the read-only qcow2 base.
- **Sessions per size:** S1 and S2. The two sizes run **one after the other**
  in the seeded order `plan.size_order()` (`random.Random("q2-stage1a:size-order:42")`,
  9B then 4B), the same order in both sessions. The S2 jobs start at least 12
  hours after the later S1 job ends.
- **Pairing.** Each VM job is submitted first. Its GPU job is submitted with
  `start_after_job_id` (the submitter adds `--dependency=after:` followed by
  the VM job's id), so it cannot start, or spend capped minutes, before its VM
  job has started. The VM job's limit is the GPU cap plus 10 minutes. If the GPU
  job starts more than 11 minutes after its VM job, the VM job's own USR1 (2
  minutes before its limit) comes before the GPU job's (3 minutes before the
  cap): it stops dispatch and cuts the episodes in flight, and DR0 fires if the
  base is incomplete.
- **Blocks within a session job.**
  - Block 1 runs every base (task, harness) cell once.
  - Block 2 runs them all again.
  - Each block is in its own random order, mixing the harnesses.
  - Order seed: `random.Random(f"q2-stage1a:{session}:{size}:{block}:{seed}")`,
    with seed 43 for S1 and 44 for S2 (`plan.episode_orders`).
- **Replicates.** Each (size, task, harness) therefore has R = 4 episodes:
  2 sessions x 2 within-session reruns. Pairs are between-session (4 per
  cell) or within-session (2 per cell).
- **Concurrency and CPUs.** V is the number of concurrent VMs per engine; N*
  is the ladder's qualified concurrency. The host has 208 CPUs; a GPU job
  takes 32 (the card's lane); a VM job takes 4V plus `runner_cpus(V)`
  (`harness/q2/vm/manifest.py`). The summed CPUs of co-running S1a jobs must
  stay at or below 200, which leaves the ladder's 8-CPU foreign allowance
  (`plan.check_cpus`). The lane's submission refuses a registered VM job (A0a,
  A0b, ANC, A1) whose CPUs are not exactly 4V + `runner_cpus(V)`, or whose limit
  is not its GPU cap plus 10 minutes (`lane.check_slurm`); a temporary host-load
  CPU cap is an operator flag for development and setup-check jobs only.

  | N* | A1 and A0a V | Sizes | CPUs while A1 runs | ANC V | CPUs while ANC runs |
  |---|---|---|---:|---:|---:|
  | 40 or 32 | 20 | one after the other | 32 + 90 = 122 | 32 | 32 + 144 = 176 |
  | 24 | 20 | one after the other | 122 | 24 | 32 + 108 = 140 |
  | 16 | the draft goes back to review before A0a (K_base 32 is out of reach at V = 16); no GPU job runs | | | | |
  | 8 or 1 | S1a does not start; no GPU job runs | | | | |

  V never exceeds 20 in A1, the card's measured value for this profile. N* was
  qualified on the probe desktop with no engine running, so it is an upper
  bound: A0a's step-p95 gate (section 6.2) checks V under S1a's load. Two
  sizes at once (244 CPUs at V = 20) and ANC at V = 40 (212) do not fit.
- **Slots from the plan.** Every registered VM job's slots are rendered from the
  plan (`plan.a0a_slots`, `plan.a1_slots`; `scripts/render_q2_stage1_manifest.py`),
  and `lane.validate_manifest` refuses an A0a or A1 manifest whose slots or fill
  blocks differ. A0a: the first V/4 tasks of `plan.dev_tasks` (from the committed
  setup-check records) x 2 harnesses, rerun r in block `a0a.r`, each block in the
  seeded order `block_order(tasks, "S1", "9B", "a0a.r")`, at A1's V for the N* the
  manifest names. A1: the frozen plan file (its digest must be the one this file
  states at the freeze); rerun r is block `br`, each in `plan.episode_orders`;
  session 1 carries every extension block b as two fill sub-blocks (`x01.1` and
  `x01.2` for block 1, and so on: reruns 1 and 2); session 2 runs, after its base,
  exactly the blocks both session-1 jobs completed, which the lane recomputes from
  their record files (`records.completed_extension_blocks(..., sessions=("S1",))`).
  The anchor purposes are refused while the anchor is UNAVAILABLE (no anchor
  runner is built).
- **Registered parameters are pinned in code, not in manifests.** For A0a and A1,
  `lane.validate_manifest` requires the registered episode image (section 4,
  `lane.EPISODE_IMAGE_ID`; Pillow in it resizes the screenshots) and refuses any
  manifest that sets the re-queue rule, the episode timeout (3,600 s) or the episode
  interpreter. The GPU half of a pair is rendered from its validated VM manifest
  (`render_q2_stage1_manifest.py gpu --vm-manifest`): A0a runs 9B for 25 minutes,
  an A1 job its own size for the frozen T_A1; neither is a command-line argument.
  Before it dispatches anything, the lane checks that the GPU job's `ready.json`
  engine argv is `plan.engine_argv` for the job's size (model and flags) and that
  the GPU job's Slurm time limit (`scontrol`) equals the job's cap; otherwise it
  refuses, records why, and stops the engine. Its stop point is the GPU job's
  USR1, 180 s before its limit counted from the GPU job's Slurm start.
- **Job order is enforced.** Each A1 job's manifest names the lane record file and
  receipt, by SHA-256, of every earlier A1 job in the registered order
  (`plan.a1_job_order`: session 1 then session 2, each 9B then 4B), and the lane
  refuses the job if one is missing, does not match its digest, or fired DR0
  (`rules.job_dr0`, section 11). A session-2 VM job is submitted with Slurm
  `--begin` at the later session-1 lane's end plus 12 hours, and the lane refuses
  to start before that time (`lane.earliest_start`).
- **Quiet host.** While an S1a job runs, the operator submits no other Slurm
  job. Every block records host snapshots (time, load average, foreign Slurm
  jobs and their CPUs, container counts).

### 5.6 Continuous dispatch, the fill rule and the analysis sets

- **Continuous dispatch.** Each VM takes the next queued episode as soon as
  its previous episode has been torn down. Block 2 is queued only after every
  block-1 episode has been dispatched. Prompts and sampling are not affected.
- **Fill rule (session-1 jobs only).** After its base blocks, a session-1 job
  starts extension block b (8 tasks x 2 harnesses x 2 within-session reruns =
  32 episodes, in two sub-blocks) only if
  `1.5 x c_job x 32 <= (time to the lane's USR1 signal) - 10 minutes`
  (`plan.fill_allowed`). c_job is the job's elapsed time since its first
  dispatch divided by its episodes that ran to an end (scored or lost to
  infrastructure); the USR1 time counts from the GPU job's Slurm start. Blocks are taken in the extension
  order. The rule reads cost, not verdicts; but cost follows the steps
  episodes run, which follow their outcomes, so the number of blocks is not
  outcome-blind.
- **Session-2 jobs** run the base and then exactly the extension blocks that
  both session-1 jobs completed, in the same order. They make no fill
  decision of their own.
- **Analysis sets.**
  - **Primary:** the base, fixed at the freeze, for every estimand and every
    decision rule.
  - **Registered secondary:** the base plus the extension blocks completed in
    all four A1 jobs (`records.completed_extension_blocks`). It is reported
    with every estimand and never enters a decision rule.

### 5.7 The OpenCUA-7B anchor (D11)

**Status (2026-10-08): UNAVAILABLE before any GPU job** by G0 item 9.6 (at most 6 of the
116 tasks have the config and checker the public runs were scored with, fewer than the 58
read tasks below). A0b and ANC are not submitted; every S1a output carries the label "not
externally anchored" (DR-A); the caps follow the "anchor unavailable before A0b" branch of
section 6.1. The design below stays for the record and for any successor that pins the
public runs' own revision.

- **Agent.** OpenCUA-7B with the upstream OSWorld OpenCUA agent and runner
  (section 4), at the settings of the public run (G0 item 9.5): CoT level L2,
  action history, 3 history images, 15 steps.
  - It runs the **upstream** action path: PyAutoGUI strings through
    `DesktopEnv.step`, the L0-raw layer that action-path v2's C2
    characterises, and the upstream runner's sleeps (60 s after reset, 20 s
    before evaluation, the recorded pause after each step). This is
    deliberate, because the public runs used that path. It therefore does not
    run the guard warm-up. Its outcomes are a runtime-equivalence check, not
    instrument data.
  - Our VMs run with `--network none` from the pinned file cache; the public
    runs were online. The 116 tasks are web-free, and tasks whose configs or
    evaluators changed are excluded (G0 item 9.6).
- **Size.** n = min(116, V_anc x floor((52 - 3 - L_A0b) / (1.25 d))), where
  V_anc = min(32, N*), L_A0b is A0b's time from job start to its first
  request, and d is the longer of A0b's longest slot and the card's central
  anchor slot of 11.29 minutes (`plan.anchor_tasks`). ANC runs the first n
  tasks of the anchor order. **If n < 58, ANC is not submitted** and the anchor
  is UNAVAILABLE. At N* of 32 or more n is 64 or 96; at 24, 48 or 72; at 16,
  at most 48, so the anchor does not run at N* = 16.
- **Order.** The pool in a domain-stratified order: within each domain, sorted
  ids shuffled by `random.Random(f"q2-stage1a:anchor:42:{domain}")`; position i
  takes the domain whose count lags its proportional share most, ties by name
  (`plan.anchor_order`), so every prefix is near-proportional by domain.
- **Dispatch stop.** ANC dispatches no new episode once the time left before
  its USR1 point is below 1.25 d (`plan.anchor_dispatch_allowed`), so no
  in-flight episode should be cut.
- **Reading set.** The longest prefix of the dispatch order in which every
  episode completed (`rules.anchor_reading_set`). The prefix ends at the first
  episode cut at the cap or never dispatched; an episode lost to
  infrastructure after its re-queue stays inside the prefix but out of the
  reading, and counts toward the anchor's loss share. At least 58 tasks must
  be read.
- **Order of jobs.** ANC runs after the freeze and before any A1 job.
- **A0b** is its pre-freeze smoke: 4 dev tasks, one episode each.

## 6. Jobs, caps and the 8 GPU-h count

### 6.1 Jobs

Caps follow D22's counting rule: every job's registered cap counts, whatever
its outcome. The A1 cap is set by the **remainder rule** (`plan.a1_cap_minutes`):
the four A1 jobs share equally, in whole minutes, what is left of 478 minutes
after the caps of every pre-freeze job that ran (O1, A0a, A0b and any repeat),
O2, one pre-funded O2 retry, and ANC if the anchor will run. At least 2 of the
480 minutes therefore stay unallocated.

| Job | When | What | Cap (min) | Central GPU-h | High GPU-h |
|---|---|---|---:|---:|---:|
| O1 | pre-freeze | cu129 overlay build from the draft commit (one H100, as job 464: 44 s) | 3 | 0.012 | 0.050 |
| A0a | pre-freeze | 9B, V/4 dev tasks x 2 harnesses x 2 reruns = V episodes, one wave at A1's V | 25 | 0.225 | 0.306 |
| A0b | pre-freeze | OpenCUA-7B, 4 dev tasks x 1 = 4 episodes at V = 4 | 26 | 0.238 | 0.319 |
| O2 | post-freeze | overlay build from the freeze commit | 3 | 0.012 | 0.050 |
| O2 retry | post-freeze, only if O2 fails | one rebuild | 3 | 0 | 0.050 |
| ANC | post-freeze, before A1, only if n >= 58 | OpenCUA-7B anchor, n tasks | 52 | 0.615 (n = 96) | 0.758 (n = 96) |
| A1 x4 | post-freeze | (9B, 4B) x (S1, S2), 4 K_base episodes per job plus fill | 4 x T_A1 | 4.818 (K = 32) | 6.461 (K = 32) |

The A1 cap and the total under each branch:

| Branch | T_A1 (min) | Total caps (min) | GPU-h | K_base at the card's high price (L = 6) |
|---|---:|---:|---:|---:|
| Anchor runs | 91 | 476 | 7.933 | 24 |
| Anchor unavailable after A0b (G0 9.3 fails, or n < 58) | 104 | 476 | 7.933 | 32 |
| Anchor unavailable before A0b | 111 | 478 | 7.967 | 32 |

- Central and high are from `analysis/cost_s1a.json` (key `s1a_v2`). Prices,
  GPU-h per episode, at T = 15, H2-thinking-screenshot profile, Qwen3.5-9B. The
  slot now holds VM setup (central 90 s, high 180 s) and the matched 80 s of
  settle, which the draft left out:

  | V | Central | High |
  |---:|---:|---:|
  | 20 | 0.009020 (the open-loop bound binds) | 0.011274 (the open-loop bound at the slowest A1 seed binds) |
  | 16 | 0.010948 | 0.012901 |

  The 4B multiplier is 1.0 by the card's rule.
- **Each A0 cap holds its wave before its USR1 point:** L + 1.25 x the high
  slot <= cap − 3 at the planning launch L = 6 minutes: A0a 6 + 1.25 x 12.39 =
  21.5 <= 22; A0b 6 + 1.25 x 13.17 = 22.5 <= 23 (`plan.check_a0_caps`).
- **Repeats and retries.** An A0 repeat (section 6.2) or an O1 retry is a
  pre-freeze job whose cap enters the remainder rule, so it lowers T_A1. O2 has
  one pre-funded retry; a second O2 failure stops S1a before ANC and is
  reported. No other job is retried.
- **Maximum.** In every branch the caps sum to at most 478 minutes of one H100,
  7.967 GPU-h. S1a therefore needs no gauntlet. An amendment that would raise
  any cap above this total is not made, and the design goes to the gauntlet
  instead (D20, D22, D24).

### 6.2 Constants set from A0 before the freeze (the D36/D44 pattern)

The rules, applied by `plan.freeze_constants` to the A0 records only:

- **c_A0a** = (sum over A0a's V episodes of slot occupancy, lane dispatch to
  teardown) / (V x V), in GPU-h. A0a runs one wave at A1's V, so this is A1's
  cost per episode when the engine is not saturated, VM boot and setup included.
  **Every A0a slot counts:** if any A0a slot was cut at the cap or never
  dispatched, or fewer than V episodes completed (a slot lost again after its
  re-queue), the draft is not frozen and goes back to review, so the longest
  episodes cannot drop out of c_A0a or the gates (`plan.a0a_measurements`).
- **c_proj** = max(the card's high price at A1's V, 1.25 x c_A0a).
- **K_base** = min(32, 8 x floor(((T_A1 − 3 − L_A0a) / 60) / (4 x 1.05 x c_proj) / 8)),
  where T_A1 is the A1 cap of section 6.1, 3 minutes is the USR1 lead, L_A0a is
  A0a's time from its GPU job's Slurm start (`scontrol` StartTime, which the lane
  records in its receipt) to the lane's first dispatch, 4 episodes per task per
  job, and 1.05 allows the re-queues DR0 tolerates. L stops at the first dispatch,
  not the first request, because the first slot's boot, setup and 60 s settle are
  inside its slot; the time to the bridge's first forwarded request is reported
  beside it.
- **Floor (D47; D49 (i)).** Without the anchor, the branch S1a is in since G0 item
  9.6: If K_base < 32, the draft is not frozen and goes back to review; no amendment
  lowers this floor. With the anchor running, the floor is 24 (K_base < 24 goes back to
  review) once the item 18 amendment is signed (D49 (i) states it), and 32 until then.
  `plan.freeze_constants` takes the floor from the branch: it defaults to 32 and applies
  `k_floor=24` only when the anchor runs. In the unanchored branch (T_A1 = 111 minutes)
  K_base = 32 needs c_A0a of at most about 0.01012 GPU-h, a mean A0a slot of at most
  about 728 s at V = 20 and L_A0a = 6 minutes; the card's own high slot (743 s) gives 24,
  so going back to review after A0a is a live outcome. At V = 16 the card's high price
  alone gives 24 unless L_A0a is under 4 minutes, so at N* = 16 the draft goes back to
  review before A0a runs (G0 item 1).
- **Truncation gate.** If more than 20% of A0a's steps under either harness
  end at 2,048 tokens without a complete tool call, the draft is not frozen.
  Per harness, the share is A0a's model turns whose reply hit the cap and held
  no complete tool-call block (`truncated` and not `complete_tool_call` in
  the step log) over all its model turns, in A0a's V episodes (those c_A0a
  counts). The gate is measured on 9B only; 4B's truncation is reported
  per cell (section 15), by the same definition.
- **Concurrency gate.** If A0a's `DesktopEnv.step` p95 exceeds twice the
  action-path A1 step p95, the draft is not frozen. Both are the action path's
  statistic: the ceil(0.95 n)-th smallest `timing_s.total` of every
  `DesktopEnv.step` (A0a: every executed action of its completed episodes,
  harnesses pooled; the action path: the accepted attempt's `step_p95_n1_s`).
- Both gates are computed by `plan.a0a_gates` over the same V episodes as
  c_A0a, inside `plan.a0a_measurements` (`python -m harness.q2_stage1.plan
  a0a-measurements` on the host, or the plan renderer's freeze mode), and
  `plan.freeze_constants` refuses to set the constants when either fails or
  cannot be read.
- **Anchor size** n by section 5.7.
- **Plumbing and repeats.** A defect A0a or A0b shows in the driver, bridge or
  checker path is fixed before the freeze. Any change after A0 to the engine
  launcher, the episode driver, either harness client or the checker
  invocation requires that A0 job to be repeated; its cap enters the remainder
  rule, and the constants are recomputed. If K_base falls below the floor, the
  draft goes back to review.

The constants (filled from the A0 records at the freeze):

| Constant | Value |
|---|---|
| N* (accepted attempt) | TBD |
| V for A0a and A1 | TBD |
| A0a: completed episodes, c_A0a (GPU-h), L_A0a (min); its records' SHA-256 (episodes, lane receipt, bridge `stopped.json`) | TBD |
| A0a truncation share per harness; step p95 against the action-path A1 p95 | TBD |
| c_proj (GPU-h) | TBD |
| Anchor branch; A0b L_A0b and longest slot d (min); n | unavailable before A0b (G0 item 9.6): A0b not run, L_A0b and d not measured, n = 0 |
| T_A1 (min) and total caps (min) | TBD |
| K_base and the base task list (by plan SHA-256) | TBD |

### 6.3 VM time (CPU-only lane, D12)

A VM is occupied for an episode's slot (GPU-h per episode x V at the price
that binds, VM setup and the matched settle included).

| Job | Central VM-h | High VM-h | Reservation bound VM-h |
|---|---:|---:|---:|
| A1, K = 24, V = 20 | 69 | 87 | 135 (4 jobs x 101 min x 20 VMs) |
| A1, K = 32, V = 20 (anchor unavailable) | 92 | 115 | 161 (4 x 121 min x 20) |
| A0a (V = 20) | 3.5 | 4.1 | 12 |
| A0b (V = 4) | 0.8 | 0.9 | 2.4 |
| ANC (V = 32) | | | 33 (62 min x 32) |

- Wall-clock: at most T_A1 = 111 minutes of GPU time per A1 job (about 1.7 h at
  the card's high price with K = 32), so at most about 3.7 h per session with the
  two sizes in turn, plus the 12-hour gap.
- The action-path suite that gates S1a needs 98.4 VM-h.

## 7. Episodes

### 7.1 Definition

An episode is one (size, task, harness, session, block) slot. It runs:

1. VM cold boot from the qcow2 base;
2. offline task setup and `DesktopEnv.reset`;
3. the guard's keyboard warm-up (`guard.py warmup`, the suite's), once per
   boot, after the reset and before the agent's first action (action-path v2
   executor addendum and design decision 31);
4. the 60-second settle;
5. up to 15 agent steps;
6. the 20-second settle;
7. evaluation with OSWorld `b138d348`'s `DesktopEnv.evaluate()` (the
   task's checker);
8. final-state capture, then the guest-server restart check again;
9. teardown.

An anchor episode runs the upstream OpenCUA runner instead of steps 3-6
(section 5.7).

### 7.2 Infrastructure losses and agent-caused events

An episode is **lost to infrastructure** if any of these occurs:

- VM boot or task setup fails. Task setup fails when a setup step raises, or
  when any guest reply to a setup step is not HTTP 200 or carries a non-zero
  `returncode` (`osworld_live.setup_reply_failed`; every reply is recorded per
  step, `setup.replies`): the pinned code goes on after either, and the task
  would then run without its setup. The offline-setup exclusion (section 5.4)
  removes every task whose setup fails this way offline in G0 item 5's second
  pass, so no remaining task fails deterministically, and no deterministic
  offline failure is tolerated or disclosed in its place. A postconfig reply
  that fails during `DesktopEnv.evaluate()` is recorded
  (`postconfig_replies`, `postconfig_failures`, reported per (size, harness))
  and is not a loss: postconfig steps act on the agent's final state;
- the guest server restarts during the episode (its `NRestarts` counter
  changes or a different server process answers; D30, D33);
- an engine request fails after the client's retries, or times out at 600 s;
- H-GA's context-variant fallback fires for any reason other than a
  context-length rejection (the same engine fault costs H-OSW the episode);
- the executor fails at the device level, or the guard fails;
- transport to the VM fails, including a checker getter that cannot retrieve
  a file because of transport;
- the checker asks for a URL the offline run cannot serve (neither the guest
  nor the pinned file cache: `offline_network`; all 374 task URLs are in the
  cache, so this is not expected to fire);
- the runner crashes.

The pinned OSWorld code swallows most transport errors (its `get_vm_file` returns `None`,
its postconfig steps log a failed request and go on), so the runner does not read them from
the checker's outcome: any guest request of task setup, of `DesktopEnv.evaluate()`
(postconfig included) or of the capture that fails in transport makes the episode a loss,
whatever the checker returned (`osworld_live`). The restart check runs after the 20 s
settle and again after the capture; a check that cannot reach the guest server, there or at
the warm-up, is a transport loss.

These are the `INFRASTRUCTURE_TYPES` of `records.py`. Handling:

- A lost episode is re-queued once: at the end of its block while that block
  still has slots waiting; once its block is fully dispatched, at the head of the
  block being dispatched, so it runs next (`lane.Dispatcher.requeue`). A second
  loss leaves the slot missing.
- Losses are reported per (job, size, harness, type).
- Cap truncation is not an infrastructure loss (section 5.6).

**Agent-caused events are not infrastructure** and never count toward DR0:

- An `IRError` raised from model output (an unknown key name, a non-modifier
  key with a click, `type` text holding a control character the certified
  executor cannot type, any invalid translated action) is handled in the episode
  under that harness's rule for an unparseable reply: no action that step for
  H-OSW-fixed, a one-second wait for H-GA. The whole turn's actions are
  dropped. Counted per episode (`ir_errors`) and reported per (size, harness).
- A checker metric that raises on retrieved agent state scores y = 0 in the
  primary analysis (`metric_exception`). A sensitivity treats those episodes
  as missing. The captured final state allows rescoring. Counted per
  (size, harness).

### 7.3 Logging (also the C1 timing census)

Per step:

- prompt and output tokens. vLLM v0.31.0 at the card's flags reports neither a
  cached-token count nor a queue wait per request (the step log's `queue_wait_s`
  is null), so the bridge samples the engine's prefix-cache counters and its
  queue-time histogram (sum and count) every 30 s with the GPU samples
  (`bridge.ENGINE_METRICS`); per block they are the differences across the
  samples around the block's start and end (the lane's block snapshots);
- the SHA-256 of the prompt token ids (`return_token_ids`);
- whether the output hit 2,048 tokens and whether it held a complete tool
  call;
- the parsed IR and its SHA-256, any `IRError`, and any context fallback;
- engine latency, time to first token and time per output token;
- the executor's settle time.

Per episode:

- boot, setup, warm-up, evaluation and teardown times, and the slot
  occupancy from dispatch to teardown;
- every guest reply to a setup and a postconfig step (HTTP status,
  `returncode`, stderr tail; `setup.replies`, `postconfig_replies`) and the
  postconfig failures (`postconfig_failures`);
- steps used and how the episode ended; steps whose reply hit 2,048 tokens,
  and of those the ones without a complete tool call;
- the checker score, and whether the metric raised;
- the hashes of the checker's input files;
- guest-server restart counts;
- **uncertified action-path exposure:** the number of key, chord and hold
  actions, and of click or scroll modifiers, that name a keysym outside the 33
  `catalog.certified_keysyms` of action-path v2 section 4.5
  (`records.uncertified_key_actions`), as that registration requires.

Per job:

- GPU memory and utilisation samples;
- host snapshots;
- realized GPU-h and VM-h.

## 8. Outcomes and checker corrections

- **Primary outcome.** y = 1 if the task's checker score is 1.0, else 0
  (raw verdict). Fractional scores are counted and reported. A sensitivity
  uses the score itself.
- **Checker-corrected outcome (secondary).** Each saved final state is
  rescored with `compare_pptx_files_zinv` in place of `compare_pptx_files`
  (G0 item 8). In the mutation study the z-order operator
  `pptx.eq.zorder_nonoverlap` failed its checker on 36 of 40 evaluable
  equivalence mutants: `compare_pptx_files` 35 of 39 (29 confirmed by both
  raters, 6 unresolved) and `compare_pptx_files_tolerant` 1 of 1 (confirmed).
  The correction covers only the z-order false negatives of
  `compare_pptx_files`; the tolerant family's is not corrected, and the
  confirmed false positives are not corrected.
  - Flips are counted per task.
  - Kevin's adjudication of the 34-item pool and the 25-item spot check are
    pending (D9), so corrected verdicts stay secondary.
- **Flagged tasks** (`plan.FLAGGED_TASKS`). They stay in the primary analysis;
  a sensitivity excludes them:
  - P1 save flips whose GUI-faithful saved gold fails its checker and both
    raters accept: `9ec204e4`, `b8adbc24`;
  - the P1 raw flip whose saved gold both raters reject: `30e3e107`;
  - the confirmed false positives: `70bca0cc` (`drop_char_format` passes
    `compare_pptx_files`; a K = 32 base task) and `d53ff5ee` (`text_edit`
    passes `compare_docx_files`);
  - the false-positive candidates whose label the raters contradicted, pending
    Kevin: `358aa0a7` (a K = 32 base task) and `a434992a` (also the uncorrected
    tolerant-family z-order false negative).
  - The four K1 raw-gold failures are outside the pool.

## 9. Estimands and estimators

Notation:

- For size z, task t and harness h, p_zth is the success probability in the
  two realized sessions of that size. Every estimand below is defined
  **conditional on the realized sessions**: delta, D_b, D_w, D_b − D_w, X,
  X_c and π, and every DR2, DR5 and P1-P5 reading, describe these sessions.
  In particular a harness x session effect shared by every task of a session
  enters δ and is neither modelled nor tested (the heterogeneity check below
  reports it).
- m_zths is the mean of the available within-session reruns in session s.
- d_zts = m_zt,GA,s − m_zt,OSW,s.

Every quantity is task-weighted over the analysis set. The code is
`harness/q2_stage1/estimators.py`; `analysis.statistics` lists every estimand.

1. **Noise floor.**
   - D_b,z is the mean over (t, h) of the fraction of discordant pairs among
     the 4 cross-session pairs; D_w,z the same over the 2 within-session
     pairs. A pair with a missing member is dropped; a cell with no pair drops
     out.
   - The session excess is D_b − D_w. Pooled means are averaged over sizes.
   - D_b is also reported on same-block pairs (block 1 with 1, 2 with 2) and on
     cross-block pairs. Block 1 always precedes block 2, so a drift within a
     job falls fully in D_w but only partly in D_b.
   - The system-prompt date is pinned (section 5.2), so no pair differs in
     prompt text. The guest's own clock is not pinned: the time the desktop's
     top bar shows differs in nearly every pair, and its date differs between
     sessions and, within a session, for a job that runs across the guest's
     local midnight. That is part of the environment D_b includes. No checker of
     the 148 pool and dev tasks reads the date or time (their instructions and
     evaluators were scanned).
2. **Harness main effect.** d̄_t is the mean over the available (size,
   session) cells of d_zts; δ = mean_t d̄_t. Per size, δ_z = mean_t mean_s d_zts.
3. **Mean squared per-task harness effect.**
   - X_z = mean_t d_zt1 · d_zt2. It is unbiased for mean_t Δ_zt², where Δ_zt is
     task t's harness effect, when the two sessions are independent given the
     task; it stays unbiased under task x session and task x harness x session
     variation. Since mean_t Δ_zt² = δ_z² + Var_t(Δ_zt), **X carries the main
     effect**: it is not an interaction statistic.
   - X_c,z = X_z − (δ_z² − Var-hat(δ_z)), with Var-hat(δ_z) = (1/K²) Σ_t
     var_s(d_zts)/2, is unbiased for the task variance of Δ_zt (divisor K): the
     task-specific part. It is reported with its interval; no test is
     registered for it.
   - The Bernoulli-corrected form, which treats all four reruns as
     independent, is reported as a secondary (biased upward under task x
     harness x session variation).
4. **Harness share.**
   - π_z = (X_z⁺/4) / (X_z⁺/4 + D_b,z/2), X⁺ = max(X, 0); π = 0 when the
     denominator is 0, also inside bootstrap resamples (`estimators.pi_share`).
     This is the harness part of within-task outcome variance when each
     harness is used half the time; rerun variance is taken from the
     between-session floor, which includes session variance.
   - The population quantity it estimates (π°) uses the same moments: X° =
     E_t[(μ_t,GA − μ_t,OSW)²] and D_b° = E_t,h[2 μ_th (1 − μ_th)], where μ_th
     averages over sessions. DR5's M is defined on this scale.
   - π_small is the mean of π_4B and π_9B, or π_9B alone if DR1 drops 4B.
5. **Scale screen.** δ_4B − δ_9B and π_4B − π_9B. These are labelled a
   screen; S1a makes no shrinkage claim.
6. **Session shift.** Per size, mean_t u_zt, where u_zt is the mean over
   harnesses of (m_zth,S2 − m_zth,S1).
7. **Harness effect by session.** Per size, δ_z,S1 − δ_z,S2 with its
   task-paired SE (reported, not tested).
8. **Common session share (for S1b).** C_z = mean_t w_zt,GA · w_zt,OSW / 2,
   with w_zth = m_zth,S2 − m_zth,S1, estimates the part of the session variance
   shared by both harnesses; ρ_z = C_z / ((D_b,z − D_w,z)/2), truncated to
   [0, 1].
9. **Anchor.** Our mean score minus the mean of the three public runs' mean
   scores on the reading set; discordance between ours and the public runs,
   against the mean public-versus-public discordance on the same tasks (the
   public runs differ by 7.5-9.7% on all 359 tasks: holo3-v2 receipt).
10. **Cost card.** Realized GPU-h and VM-h per episode by size, harness and
    job (`analysis.realized_costs`; `python -m harness.q2_stage1.analysis costs`
    builds `costs.json` from the lane records):
    - an A1 job's **episodes** are its episode attempts that ran to an end,
      status `scored` or `infrastructure` (first attempts and re-queues, base and
      fill blocks); a `cap_truncated` attempt is not one;
    - **realized GPU-h per episode** is the GPU job's Slurm elapsed time
      (EndTime minus StartTime, engine start-up included) in hours over those
      episodes. This is the input of DR4 and P5. Slurm accounting is off on the
      host and `scontrol` forgets a finished job within minutes, so the VM lane
      records both: StartTime when the engine is ready, EndTime by polling for
      the GPU job's final state after `vm.done`; if the lane could not see the
      end, the bridge's `stopped.json` `t_end` (the workload's end, seconds
      before the job's) stands in (`analysis.gpu_elapsed`);
    - **by harness**: both harnesses share one engine, so the job's GPU-h is
      split between them in proportion to their summed slot occupancy (dispatch
      to teardown) over those episodes, then divided by each harness's episodes;
    - **realized VM-h per episode** is the summed slot occupancy over those
      episodes; by size, the size's jobs are pooled.

    Also: steps, output tokens, truncation rate, the step-of-termination
    and step-of-success distributions (censored at 15), `IRError` and
    metric-exception counts, and uncertified exposure.
11. **Descriptive decompositions.**
    - First divergence per rerun pair (`records.first_divergence`), by within-
      and between-session pairs: the first step whose processed screenshot
      differs (environment), or whose screenshots so far are equal but whose
      request (an earlier reply's text) or IR differs (serving numerics). The
      prompt token ids cannot tell screenshots apart (an image is placeholder
      tokens), so they are not used. The guest's top-bar clock is on every
      screenshot, so nearly every pair parts at step 1 as "environment"; the
      decomposition is descriptive.
    - Discordant pairs whose checker-input hashes are identical (checker or
      live-state noise), and live-versus-offline rescoring mismatches (the
      merged `offline_raw_score`). Identical hashes will be rare for tasks the
      agent saves: a saved office file embeds its save time.
    - δ by uncertified-exposure stratum (tasks with and without any exposed
      episode).

## 10. Inference and operating characteristics

### 10.1 Inference

- **Intervals.** Task-cluster percentile bootstrap: 10,000 resamples, seed
  42 (`estimators.bootstrap`). Tasks are resampled jointly across sizes,
  harnesses, sessions and reruns; sessions are held fixed. One-sided 95% bounds
  are the 5th and 95th percentiles.
- **δ.** Paired t over tasks on d̄_t, two-sided, α = 0.05; its 90% interval is
  the t interval. Per-size tests are secondary.
- **X (primary): sign-flip randomization test**, one-sided, 10,000 flips, seed
  42, on the per-task products q_t = mean over sizes of d_zt1 · d_zt2
  (`estimators.x_signflip_p`). Flipping the sign of d_zts swaps the two harness
  cells of a whole (size, task, session) cell, which is exchangeable under no
  harness effect whatever the session structure. **A rejection supports only
  "a harness effect is present, main or task-specific".** No interaction claim
  is read from X; the GLMM's (1|task:harness) test is the secondary evidence
  for one.
- **X (sensitivity):** the label permutation within each task x session
  (`estimators.x_label_permutation_p`), which assumes exchangeable episodes
  within a cell; the Bernoulli statistic.
- **Session shift (primary):** per size, a two-sided sign-flip test over
  tasks on u_zt, 10,000 flips, seed 42 (`estimators.session_signflip_p`). The
  draft's permutation of session labels within (task, harness) is not used: it
  is anti-conservative under a session excess (section 10.2).
- **Heterogeneity check:** per size, δ_S1 − δ_S2 with its task-paired SE,
  reported.
- **Secondary model.** A logit crossed GLMM:
  `y ~ size*harness + (1|task) + (1|task:size) + (1|task:harness) + (1|task:size:harness) + (1|session) + (1|harness:session) + (1|task:session) + (1|task:harness:session)`,
  sessions nested in size.
  - Fitted by Laplace (glmmTMB in a pinned CPU container built in G0).
  - Latent-scale variance shares get parametric-bootstrap intervals.
  - It includes a likelihood-ratio test of harness-specific task variance
    ((1|task:harness)) with (1|task:harness:session) in both models. Any later
    uneven allocation of reruns across harnesses rests on that homogeneity.
  - A fit that does not converge is reported as such.
- **Missing data.** Missing slots (second infrastructure loss) are treated
  as missing at random; this is an assumption, and losses are reported by
  task. d̄_t averages the available (size, session) cells; a task with none
  drops out of δ; a quantity needing a complete pair drops a task or cell
  with none.
- **Multiplicity.** DR2's family is the δ test and the X sign-flip test,
  combined by Holm at family-wise 5% (section 11). P1-P5 are separate
  predictions, each read once.

### 10.2 Operating characteristics

Monte Carlo, CPU only, seeded, with the registered estimators and tests
imported from `harness/q2_stage1/estimators.py`
(`analysis/sim_s1a_v2.py`, `analysis/sim_s1a_v2.json` in the proposal's evidence
bundle; 2,000 data sets per point, 500 sign flips, 200 label permutations on
1,000 data sets). The generative model is logit p = size + task (SD σ_a,
correlation 0.8 across sizes) + harness + task x harness (σ_b) + session (SD
σ_g) + harness x session common to a session's tasks (κ) + task x session
(σ_e) + task x harness x session (σ_f), Bernoulli outcomes, sessions separate
per size. Scenarios: literature (base 15% and 30%, σ_a = 3.5), high noise
(σ_a = 2.5), low base (8% and 20%), OpenCUA-calibrated (σ_a = 6.9, 18% and
24.3%).

**Size at the null**, literature scenario, 2,000 data sets per cell; each test
cell reads K = 24 / K = 32 (D_b − D_w is the simulated session excess per size
at K = 32):

| Session noise | D_b − D_w at K = 32, 4B / 9B, pp | δ paired t | X sign flip (primary) | X label permutation | Session sign flip (primary), 4B; 9B | Session-label permutation, 4B; 9B | DR2 Present |
|---|---|---|---|---|---|---|---|
| base (σ_g 0.1, σ_e 0.3) | 0.2 / 0.3 | 0.055 / 0.058 | 0.013 / 0.018 | 0.034 / 0.023 | 0.013; 0.026 / 0.023; 0.039 | 0.027; 0.042 / 0.030; 0.048 | 0.030 / 0.026 |
| σ_f 0.5 | 0.7 / 1.1 | 0.051 / 0.050 | 0.017 / 0.018 | 0.029 / 0.033 | 0.018; 0.025 / 0.029; 0.038 | 0.043; 0.037 / 0.047; 0.053 | 0.029 / 0.031 |
| σ_f 1.0 | 1.9 / 3.0 | 0.041 / 0.054 | 0.019 / 0.029 | 0.042 / 0.072 | 0.021; 0.032 / 0.035; 0.034 | 0.034; 0.063 / 0.051; 0.061 | 0.023 / 0.041 |
| σ_f 1.5 | 3.8 / 5.9 | 0.051 / 0.048 | 0.021 / 0.025 | 0.073 / 0.091 | 0.019; 0.035 / 0.034; 0.035 | 0.066; 0.077 / 0.070; 0.090 | 0.036 / 0.033 |
| σ_f 2.0 | 6.2 / 9.2 | 0.046 / 0.044 | 0.020 / 0.031 | 0.086 / 0.114 | 0.029; 0.040 / 0.037; 0.036 | 0.070; 0.091 / 0.099; 0.093 | 0.032 / 0.042 |
| σ_f 3.0 | 11.8 / 15.6 | 0.054 / 0.047 | 0.025 / 0.042 | 0.130 / 0.157 | 0.035; 0.047 / 0.030; 0.037 | 0.107; 0.127 / 0.101; 0.118 | 0.034 / 0.042 |
| σ_e 1.0 | 1.9 / 2.7 | 0.048 / 0.045 | 0.011 / 0.020 | 0.026 / 0.028 | 0.022; 0.041 / 0.028; 0.029 | 0.065; 0.099 / 0.085; 0.095 | 0.022 / 0.026 |
| σ_e 1.5 | 3.8 / 5.5 | 0.052 / 0.052 | 0.006 / 0.011 | 0.016 / 0.023 | 0.025; 0.029 / 0.029; 0.043 | 0.110; 0.101 / 0.113; 0.140 | 0.027 / 0.029 |
| σ_e 2.0 | 6.0 / 8.8 | 0.054 / 0.046 | 0.008 / 0.007 | 0.022 / 0.024 | 0.027; 0.035 / 0.034; 0.034 | 0.151; 0.158 / 0.157; 0.167 | 0.021 / 0.025 |
| σ_e 3.0 | 11.4 / 15.5 | 0.052 / 0.044 | 0.002 / 0.006 | 0.012 / 0.027 | 0.033; 0.035 / 0.035; 0.042 | 0.203; 0.224 / 0.205; 0.207 | 0.029 / 0.021 |
| κ 0.2 | 0.3 / 0.5 | 0.062 / 0.060 | 0.012 / 0.019 | 0.035 / 0.034 | 0.021; 0.036 / 0.037; 0.054 | 0.041; 0.047 / 0.057; 0.072 | 0.034 / 0.042 |
| κ 0.3 | 0.3 / 0.6 | 0.086 / 0.104 | 0.011 / 0.021 | 0.028 / 0.028 | 0.039; 0.054 / 0.041; 0.075 | 0.064; 0.062 / 0.056; 0.105 | 0.051 / 0.058 |

The primary tests hold their size across a session excess of 0-16 pp: the δ
paired t at 0.041-0.058, the X sign flip at 0.002-0.042 (conservative), the
session sign flip at 0.013-0.047. The draft's tests do not: the X label
permutation reaches 0.157 and the session-label permutation 0.224. A harness
x session effect common to a session's tasks (κ) makes the δ test and the
session test reject more often (up to 0.104 and 0.075). κ is a real effect in
the realized sessions, so conditional on them this is power, not size; it is
why δ, the shift and DR2 are stated for the realized sessions (section 9).

**Power and precision**, literature scenario (base noise: σ_g 0.1, σ_e 0.3):

| Quantity | K = 24 | K = 32 | K = 64 | K = 116 |
|---|---:|---:|---:|---:|
| δ pooled, MDE at 80% power (two-sided 5%) | 8.8 pp | 7.2 pp | 5.1 pp | 3.6 pp |
| δ per size (4B / 9B) | > 15 / 13.6 pp | 10.1 / 11.4 pp | 6.5 / 7.9 pp | 4.7 / 5.8 pp |
| δ_4B − δ_9B scale screen, MDE | > 20 pp | 16.8 pp | | |
| 90% CI half-width of pooled δ | 4.6 pp | 4.0 pp | 2.8 pp | 2.1 pp |
| D_b pooled, 95% half-width | ±6.5 pp | ±5.7 pp | ±3.9 pp | ±2.9 pp |
| D_b per size, 95% half-width | ±8.0 / ±9.2 pp | ±6.9 / ±7.9 pp | ±4.9 / ±5.5 pp | ±3.8 / ±4.0 pp |
| D_b − D_w pooled, 95% half-width | ±4.0 pp | ±3.4 pp | ±2.5 pp | ±1.8 pp |
| X sign flip, power at RMS per-task effect 15 / 22 pp | 0.14 / 0.43 | 0.23 / 0.56 | | |
| π_small at the null: mean; SD | 0.029; 0.034 | 0.027; 0.030 | 0.019; 0.020 | 0.014; 0.015 |
| Session shift 3.7 / 5.6 pp, power per size (4B, 9B) | 0.05-0.10 / 0.09-0.20 | 0.08-0.14 / 0.17-0.27 | | |

With a session excess of about 4-6 pp (σ_e = 1.5, or σ_f = 1.5), the pooled δ MDE
is 8.5 or 10.6 pp at K = 24 and 7.1 or 9.1 pp at K = 32. Other scenarios at
K = 24 / 32: pooled δ MDE 9.6 / 8.2 pp (high noise), 8.0 / 6.5 pp (low
base), 7.4 / 5.9 pp (OpenCUA-calibrated). The sign-flip X test is conservative,
so its power is lower than the draft's permutation test claimed; that test's
power was bought with an invalid size.

## 11. Decision rules (fixed before any confirm-split episode)

The code is `harness/q2_stage1/rules.py`; every rule reads the primary
analysis set unless it says otherwise.

**DR0, validity (A1 jobs only).** Checked at the end of every A1 job from
infrastructure records only; no outcome is read. It fires if:

- a (size, harness) cell lost more than 5% of its first-attempt dispatched
  episodes to infrastructure (section 7.2; agent-caused events are not
  losses);
- the job ended without completing its base (every base slot scored, or lost
  after its re-queue);
- a gate of section 3 turned out not to hold.

When it fires, no further job starts: DR0 runs on each A1 job's lane records
(`python -m harness.q2_stage1.rules dr0` on the job's lane run directory and the
frozen plan, `rules.job_dr0`; a lane receipt that records a refusal, such as an
engine or Slurm check or a visible GPU device, counts as a gate that did not
hold), and the next A1 job's manifest must name every earlier job's record file
and receipt by digest, which the lane refuses if DR0 fired for any of them
(section 5.5). The cause is investigated without reading outcomes. Any code
change is a new experiment id. Data already collected are reported as
incomplete. ANC's losses are judged by DR-A alone.

**DR-A, anchor.** Read after ANC and before any A1 job, on the reading set of
section 5.7.

- SE is the task-level SE of (ours minus the public mean) per task.
- Kill if our mean score lies more than 2 SE outside [min, max] of the three
  public runs' mean scores on the same tasks.
- ANC's infrastructure loss share is its infrastructure losses over its
  first-attempt dispatched episodes.
- Outcomes:
  - ANCHOR-FAIL: A1 does not start, and S1a ends. Debugging, and any later run
    of this design, is a new experiment id. This is the question file's kill
    criterion, reworded under D11.
  - ANCHOR-PASS: A1 runs.
  - ANCHOR-INCOMPLETE (fewer than 58 tasks read, or a loss share above 10%) or
    ANCHOR-UNAVAILABLE (G0 item 9, or n < 58): A1 runs, and every S1a output
    carries the label "not externally anchored". Whether S1b may rest on an
    unanchored floor is decided in S1b's gauntlet.
- The rule assumes no session variance between our run and the public runs;
  their own spread is 3.2 pp on 359 tasks. In simulation a per-run logit shift
  of SD 0.15 leaves the false-kill rate at about 1%.
- Operating characteristics (OpenCUA-calibrated, 4,000 data sets; false kill
  about 1.0% at every size):

  | Runtime deficit | n = 58 | n = 64 | n = 72 | n = 96 | n = 116 |
  |---|---:|---:|---:|---:|---:|
  | 4.2 pp | 0.08 | 0.09 | 0.10 | 0.16 | 0.19 |
  | 6.1 pp | 0.20 | 0.22 | 0.26 | 0.38 | 0.48 |
  | 7.9 pp | 0.36 | 0.41 | 0.48 | 0.63 | 0.74 |

  Only gross defects are reliably caught.

**DR1, floor.** If 4B's pooled success is below 10% under both harnesses,
the ladder drops 4B, and π_small = π_9B: DR2's bound, DR5's share and the
reported π_small (handed to S1b) are then all π_9B's (`analysis.analyse_array`;
the two-size mean is reported beside it as `pi_mean_4B_9B`). This is the dossier's criterion as a
ladder decision. It replaces the question file's swap to 122B-A10B, which is
not funded; that replacement is Kevin's to accept (section 18, item 17).

**DR2, harness pair (reported classification, for the realized sessions).**

| Class | Condition |
|---|---|
| Present | Holm over the δ paired t and the X sign-flip test rejects at family-wise 5%: min(p_δ, p_X) <= 0.025 |
| Near-equivalent | not present, the 90% t interval of pooled δ lies within ±7.5 pp, and the one-sided 95% upper bound of π_small is below 0.12 |
| Inconclusive | otherwise |

The ±7.5 pp margin is the question file's 7-8 pp line, which has no
derivation; it is kept as the only pre-existing yardstick and reported beside
the interval itself. Simulated rate of "Present" at the null: 0.021-0.042, and 0.05-0.06 under κ = 0.3 (section 10.2).

**DR3, components for S1b (reported, no decision).** S1a reports per size:
success by harness, D_b, D_w, X, X_c, the common session share ρ (section 9
item 8), the session shift and the harness effect by session. S1b's gauntlet
sizes S1b from these. S1a registers no allocation.

**DR4, cost.** If any A1 job's realized GPU-h per episode (section 9 item 10) exceeds the card's
high price at its V (0.011274 at V = 20, 0.012901 at V = 16), S1b's
projection uses the realized value x 1.2 and a re-probe precedes S1b.
Otherwise S1b is projected from realized costs x 1.2.

**DR5, admission of the S1b scale ladder.**

- **M** is the smallest share of the small rungs whose full shrinkage (the
  larger rungs at share 0) the planned ladder detects with 80% power,
  one-sided 5%, against the simulated null critical value. The ladder is
  harness-only, 60 tasks x 4 sessions x 1 rerun per rung, 4B, 9B, 27B and
  35B-A3B, both harnesses; its contrast is mean(π̂_4B, π̂_9B) − mean(π̂_27B,
  π̂_35B), and for the DR1 case π̂_9B − mean(π̂_27B, π̂_35B). Shares are on
  the π° scale of section 9 (D_b includes session variance) and use the
  registered estimator. The larger rungs' success rates are pinned at 0.40
  (literature) and 0.35 (OpenCUA-calibrated). Power is interpolated linearly
  in π° between σ_b grid points and rounded to 0.01 (`analysis/sim_s1a_v2.py`,
  `ladder_m`; 4,000 null and 2,000 alternative data sets per point).
- **M is frozen now** as the largest value over the six planning cells, so a
  GO means the ladder is powered in every cell:

  | Planning cell | M (π_small) | M (π_9B) |
  |---|---:|---:|
  | literature, σ_e 0.3 | 0.09 | 0.12 |
  | literature, σ_e 1.5 | 0.06 | 0.08 |
  | literature, σ_f 1.5 | 0.08 | 0.10 |
  | OpenCUA-calibrated, σ_e 0.3 | 0.13 | 0.18 |
  | OpenCUA-calibrated, σ_e 1.5 | 0.09 | 0.12 |
  | OpenCUA-calibrated, σ_f 1.5 | 0.12 | 0.16 |
  | **Frozen** (`rules.M_SMALL`, `rules.M_9B`) | **0.13** | **0.18** |

- The share compared with M is π_small, or π_9B with M = 0.18 when DR1 drops
  4B.
- Outcomes:
  - **GO** if the one-sided 95% lower bound of the share exceeds M;
  - **NO-GO** if its one-sided 95% upper bound is below M;
  - **INCONCLUSIVE** otherwise.
- Consequences, under D47: **GO** lets the harness scale ladder (S1b) go to
  the gauntlet (D24). **NO-GO** and **INCONCLUSIVE** start no S1b. S1a's
  report states which follow-up the result points to (an observation-factor
  study on a certified accessibility-tree variant after NO-GO; more sessions
  at 4B and 9B after INCONCLUSIVE); either would be a new proposal with its
  own gauntlet.
- Operating characteristics on S1a's side (`dr5_oc` in the simulation:
  literature scenario, 300 data sets, the registered bootstrap bounds): at
  π° = 0, NO-GO with probability 0.78 (K = 24) and 0.86 (K = 32); at π° =
  0.07, GO at most 0.01; at π° = 0.21, 0.27 and 0.33, GO 0.29, 0.50-0.57 and
  0.72-0.86. NO-GO is the expected exit for a near-equivalent pair, and GO
  needs a share well above M.
- DR5 replaces, for the scale question, the question file's "paired MDE about
  7-8 pp" line. That replacement is Kevin's to accept (section 18, item 17).

## 12. Predictions (each with its falsifier; read on the primary set, for the realized sessions)

| | Prediction | Basis | Falsified if | Read by |
|---|---|---|---|---|
| P1 | The session excess is positive: D_b − D_w > 0 | Holo3 v2 | the one-sided 95% upper bound of pooled D_b − D_w (bootstrap, seed 42) is below 1 pp | `rules.predictions` |
| P2 | The pooled between-session floor D_b lies between 6% and 20% | 12-14% web flips (2608.06171); 13% (2610.04433); OpenCUA public 7.5-9.7% | its 95% bootstrap interval lies wholly outside [6%, 20%] | same |
| P3 | The pair is not "Present" under DR2 | shared layout, template lineage and thinking default | DR2 classifies the pair as Present | same |
| P4 | 4B is not at the floor: at least 10% pooled success under at least one harness | first-party 35.6%; T = 15 lowers it | DR1 fires | same |
| P5 | Realized GPU-h per episode is at most the card's high price at its V | continuous dispatch, early terminations | DR4: some A1 job exceeds it | same |

A falsified prediction is reported as such; none stops the stage.

## 13. Seeds and randomization

Seeds are [42, 43, 44]:

| Seed | Used for |
|---|---|
| 42 | task draw, extension order, dev-task choice, anchor order, size order, engine seed, bootstrap and randomization streams |
| 43 | session-1 episode orders |
| 44 | session-2 episode orders |

Each stream is `random.Random` over a string key naming its use (section 5)
or numpy's PCG64 seeded with 42 (bootstrap and sign flips). Decoding is
greedy, so rerun variation comes from the environment, timing and
batched-serving numerics, not from sampling. This is disclosed. The count of 2
sessions x 2 reruns is justified by power (section 10), not by habit.

## 14. Stop rules

- Every GPU job has a Slurm `--time` equal to its cap and `--signal=B:USR1@180`;
  its VM job's limit is the cap plus 10 minutes.
- On USR1, the driver dispatches no new episode. In-flight episodes are cut
  and recorded as cap-truncated. The engine stops and the lane's marker is
  written.
- A Slurm TIMEOUT keeps the records and marks the job incomplete.
- DR0 and DR-A can stop the stage.
- No job is rerun to improve an outcome. An aborted job's records are kept
  and reported.

## 15. Reported regardless of outcome

- Every estimand of section 9 with its interval, on the primary set and the
  secondary set: raw and corrected verdicts, per size and pooled, per domain
  descriptively.
- DR0-DR5, DR-A and P1-P5.
- Infrastructure losses by type and cell; `IRError` and metric-exception
  counts per (size, harness); restarts per episode; cap truncations; the
  metric-exception-missing sensitivity.
- The cost card of section 9 item 10, against the card's central and high
  prices.
- Truncation rates per cell: the share of steps whose reply hit 2,048 tokens,
  and the share that hit it without a complete tool call. A size whose share of
  steps ending at 2,048 tokens without a complete tool call (A0a's gate
  definition, section 6.2) exceeds 20% under either harness has its δ labelled
  truncation-confounded (`analysis.truncation_labels`). δ on episodes without
  truncation is reported as a description of a mediator (truncation follows the
  harness), not as a de-confounded effect.
- Uncertified action-path exposure per episode and per harness, and δ by
  exposure stratum (descriptive).
- First divergence, checker-input-hash discordance and offline rescoring
  (section 9 item 11).
- Fractional checker scores; corrected-verdict flips; the flagged-task
  sensitivity.
- Host snapshots and any foreign load.
- The anchor's full comparison, whatever its outcome; while the anchor is
  UNAVAILABLE, every output carries the label "not externally anchored"
  (`analysis.report`'s `external_anchor`).
- The offline-setup exclusions (section 5.4) with their reasons, and every
  failed setup or postconfig reply by type.
- Every deviation from this file.

## 16. Data handling

- Final-state captures (files from the third-party file cache), screenshots,
  raw model replies and step logs stay on the host's persistent run root (or,
  copied, in the program's private archive), never in `program/evidence/`.
- Episode records keep each guest setup and postconfig reply's status,
  `returncode` and stderr tail, never its stdout tail: one task's postconfig
  prints the stored credentials of a Thunderbird test profile from the file
  cache. The stdout tails stay in the capture on the host.
- `program/evidence/` receives metadata, verdicts, counts, hashes, receipts and
  the analysis reports.
- NVML samples keep the GPU index; the GPU UUID is replaced by its SHA-256
  before anything is committed.
- No host address is recorded.

## 17. What S1a hands to Stage S1b (not registered here)

| Output | Use in S1b |
|---|---|
| Realized cost card | prices S1b in place of the synthetic card |
| D_b, D_w, X, X_c, π_small and their intervals | DR2 and DR5 |
| DR3 components | size S1b |
| A frozen harness, engine and task order | 4B and 9B data carry forward as the first rungs |

S1b runs only on DR5's GO (D47). It would also need a replay-only serving
probe v3 under its own registration (27B-FP8 and 35B-A3B-FP8 multipliers,
TPOT against V up to 40, the front-end fix). The proposal gives the details.

## 18. Design decisions for sign-off

The program may sign off items 1-16 and 19-26; items 17 and 18 are Kevin's
alone, because they change the question file's kill criteria or D47's stated
floor.

1. Rescope Stage 1 to S1a, at most 8 GPU-h by caps (at most 7.967), and a
   gated S1b (D47).
2. Models: Qwen3.5-4B and 9B only. No 27B or 35B-A3B in S1a.
3. Harnesses: the certified pair, H-OSW-fixed and H-GA, with the upstream
   layout of each.
4. Observation: screenshot only. The accessibility-tree factor needs an
   uncertified harness variant.
5. T = 15 for both harnesses, below both upstream defaults.
6. Thinking on (template default), passed back; max_tokens 2,048 for both;
   A0a stands in for the re-probe `serving-throughput-probe-v2` section 4
   item 7 requires (section 5.3).
7. Greedy decoding (temperature 0.0, top_p 0.9, top_k −1) for both, imposed
   on H-GA.
8. Engine settings exactly the cost card's; the anchor's variant of section 4.
9. Pool: confirm split minus the four K1 raw-gold failures (116 tasks), minus the
   offline-setup exclusions of item 27 (113 eligible tasks). Base
   by the A0 rule (24 or 32; its floor is item 18), drawn by proportional
   largest-remainder apportionment.
10. Two sessions per size, at least 12 h apart, each with 2 within-session
    reruns (R = 4); sizes one after the other in a seeded order.
11. Harnesses interleaved within each session on one engine.
12. Continuous dispatch; the cost-based fill rule in session-1 jobs, its
    blocks in the secondary set only.
13. Infrastructure-loss definition, agent-caused events kept apart, and a
    single replacement (section 7.2).
14. Raw verdicts primary; z-order-corrected verdicts secondary; the flagged
    tasks of section 8.
15. X as the mean squared per-task harness effect with the sign-flip test
    primary; X_c reported; label permutation and Bernoulli forms as
    sensitivities.
16. π computed on the between-session floor; estimands conditional on the
    realized sessions.
17. **(Kevin)** DR1 as a ladder decision in place of the 122B-A10B swap, and
    DR5 in place of the "paired MDE about 7-8 pp" line; the question file says
    the kill criteria are unchanged until Kevin rules.
18. **(Kevin)** D47 states "at least 32 confirm tasks". With the anchor
    running, the A0 rule gives 24 at the card's high price (section 6.1). The
    proposed amendment, as D49 (i) states it: "a base of at least 24 confirm tasks
    with the anchor running, and at least 32 without it". Without the amendment the
    floor is 32 in both branches, and S1a can freeze only when the anchor is
    unavailable. (2026-10-08: G0 item 9.6 makes the anchor unavailable before any GPU
    job, so the floor is 32 whether or not this item is signed. If A0a's price
    lowers K_base below 32, the draft goes back to review; the amendment does not
    apply without the anchor.)
19. Caps of section 6.1 with the remainder rule, and the A0-derived K_base
    rule of section 6.2 (it can only lower K).
20. The OpenCUA-7B anchor on the upstream action path, sized from A0b, read
    before A1.
21. Pre-freeze dev jobs O1, A0a and A0b (needs a program decision as D36
    did).
22. Serving OpenCUA-7B requires `--trust-remote-code` (model code from
    `xlangai/OpenCUA-7B`, pinned by revision and file hashes, reviewed). This
    is third-party code on a GPU under the R570 rule. It is admissible only by
    a D29-style decision; without one the anchor is UNAVAILABLE.
23. Quiet-host rule during S1a jobs; CPUs at most 200; each GPU job waits for
    its VM job to start.
24. GLMM secondary with the harness x session terms and the homogeneity
    likelihood-ratio test.
25. DR5 with M frozen at 0.13 (π_small) and 0.18 (π_9B).
26. The matched settle (60 s and 20 s) for both harnesses.
27. The offline-setup exclusion of section 5.4 (rules (a)-(c)), registered before G0 item
    5's second pass ran, and the definition of a failed task setup in section 7.2.

**Sign-off slots.** Each is filled before the freeze (with the decision id or Kevin's
ruling); an open one keeps the freeze guard refusing this file.

- Kevin: item 17 (DR1 and DR5 replace the question file's kill lines), and acceptance that
  S1a is read without the D11 runtime check (the anchor is UNAVAILABLE by G0 item 9.6, so
  A1 runs with every output labelled "not externally anchored" and nothing replaces the
  question file's Holo3 kill criterion): TBD
- Kevin: G0 item 5's decisions on the offline setup: `26150609` (option (b) of the
  audit), `982d12a5` and `e2b5e914` leave the pool by the offline-setup exclusion, and
  `53ad5833` and `d38192b0` stay (section 5.4; the base re-drawn on 113 tasks): TBD
- Program sign-off of items 1-16 and 19-27 (decision id): TBD

## 19. Disclosures and known limitations

- **Narrow harness contrast.** The two harnesses share their layout, template
  lineage, prompt skeleton and thinking default. A null δ and X is the likely
  result, which DR2 and DR5 make informative.
- **Conditional on two sessions.** Every estimand describes the realized
  sessions. With 2 sessions per size, a Holo3-sized shift (about 4 pp) is
  detected with power 0.05-0.14, and a harness x session effect common to a
  session is not separable from δ.
- **No answer on scale or observation.** 4B and 9B are a 2.25x span, and the
  scale contrast is a screen with an MDE of about 17 pp at K = 32.
- **The floor is specific to this configuration:** greedy decoding, V of 16
  to 20 on vLLM, T = 15, a 2,048-token thinking budget and the matched settle.
- **Cost model gaps.** The card's latencies are synthetic replays; its
  thinking penalty (16.8 s per step, from r4 step 19) may be low by about 50 s
  per episode, which the 2,048-token assumption on every step partly offsets;
  A0a measures the real cost on 9B only and in one wave.
- **Base size.** When the anchor runs, the A0 rule gives 24 base tasks at the
  card's high price; 32 needs the anchor's minutes. Without the anchor the floor is
  32, and a mean A0a slot above about 728 s (the card's high slot is 743 s) sends the
  draft back to review rather than to a smaller base.
- **Prompt date pinned.** Both upstream agents put today's date in the system
  prompt; S1a pins it to Thursday, October 08, 2026 for every A0a and A1
  episode, so the session excess (P1) is not confounded with a calendar change
  in the prompt. Every A1 episode runs after that date, so its prompt date
  differs from the date on the guest's own clock; no checker of the pool or dev
  tasks reads the date or time.
- **Offline tasks.** The VMs have no network. Tasks whose setup or postconfig
  needs the network, or whose setup fails offline, leave the pool before the
  draw (section 5.4), so the results cover the offline-runnable subset of the
  web-free confirm split.
- **Agent-caused events still counted as infrastructure.** A few events the
  agent can cause are classified as infrastructure, because the runner cannot
  tell them from a fault: a key chord that needs more spare keycodes than the
  guest has (an `executor_device` loss), a `type` heavy enough in remapped
  characters to run past `/execute`'s 120 s (a transport loss), and a
  guest-server restart or reboot the agent causes (D30). They are expected to be
  rare; each is re-queued once and counts toward DR0, and losses are reported by
  type and cell.
- **Upstream defaults lowered.** max_tokens 2,048 departs from H-OSW's
  upstream default, and greedy thinking can loop and truncate. Truncation is
  logged; the A0 gate covers 9B only.
- **Corrections are partial.** Only the z-order defect of
  `compare_pptx_files` is corrected; the tolerant family's z-order false
  negative and the confirmed false positives are flagged, not corrected.
  Kevin's adjudication is pending.
- **Real task applications.** Guest-server restarts under LibreOffice and
  GIMP are bounded only through DR0. A7 bounds restarts on the probe desktop
  only, and that bound is for accessibility calls.
- **Uncertified actions.** The action path is certified for 33 keysyms; key
  actions naming others are counted, not certified.
- **The anchor is weak.** It catches defects of roughly 8 pp with probability
  0.4-0.6 at 64-96 tasks, uses an uncertified (upstream) action path on
  purpose, runs offline where the public runs were online, and needs a
  remote-code decision. It runs only at N* >= 24.
- **Task overlap and generality.** The tasks overlap the mutation study, on
  purpose. Results cover 32-113 web-free tasks that run offline, and one interface.
- **Recorded IDs.** No host address is recorded; GPU UUIDs are hashed
  (section 16).

## 20. Code of record

Committed and tested on CPU before the freeze (`tests/test_q2_stage1_*.py`;
`tests/test_q2_stage1_prereg.py` checks this table against the tree until the
freeze). The G0 items' files (from `harness/q2_stage1/driver.py` on) are filled from the
tree they were built and run from on 2026-10-08; a change before the freeze refreshes the
row (the test fails otherwise), and the freeze pins them.

| File | SHA-256 |
|---|---|
| `harness/q2_stage1/__init__.py` | `0e2190149cf640fac07dab26332a26f696374ff4400c23aab82e8cf766f3b334` |
| `harness/q2_stage1/estimators.py` | `b43334b0511d17505a24893d65ce79cd55a58351a2a056075ed5b002007d36b3` |
| `harness/q2_stage1/records.py` | `468bff7150d5d462376cbabf12af8f558b9326e8297f2ef52031cc10b28679e4` |
| `harness/q2_stage1/rules.py` | `63ed09b0362595e85ac65c9bd29b090dc8b1a3a5e4ab3ace559243a82389d8b0` |
| `harness/q2_stage1/plan.py` | `1f9c77f758ed590d99597488219cc49fae0e0f3c53567d628d14382346fc2187` |
| `harness/q2_stage1/analysis.py` | `2cb9f2b942a783492a5d418230370cf461a33daf86be1530c479b58814e59bae` |
| `scripts/render_q2_stage1_manifest.py` | `50344cba078d2d8129b26b43d313c0c29a2ebcb64bf0657faba9b6d63f6ee632` |
| `scripts/render_q2_stage1_plan.py` | `44825c58dfed70f60f37d7afb55de5c59de486c4d000000f05c1261adf902341` |
| `scripts/submit_docker_research_job.py` | `660271655aa22ebd387a023e25d21e6a809c22699ec6314d9d535be74e17a994` |
| `harness/q2/vm/manifest.py` | `f238f12bdb8470919c8892eff46fe8b721e1e0c83ad08a60c0293ed8da3b9e2e` |
| `program/proposals/evidence/2026-10-08-q2-stage1-rescoped/analysis/cost_s1a.py` | `704cae408ff536ccb0c3f1415adad8f54037a4fcf3fc9d23684e40c71f7e4e35` |
| `program/proposals/evidence/2026-10-08-q2-stage1-rescoped/analysis/cost_s1a.json` | `843a123b2d8e98e34d9f20388edc132e673ba9c93b01645c7668c98d2d80e144` |
| `program/proposals/evidence/2026-10-08-q2-stage1-rescoped/analysis/sim_s1a_v2.py` | `19574910a06026b0b042aaf251e0988a72ed0484fa5833a8ca7597e3ba646a4c` |
| `program/proposals/evidence/2026-10-08-q2-stage1-rescoped/analysis/sim_s1a_v2.json` | `e3c52beb5c6160e5e364ef307fb3c6353c226ffb7b762d9cc534f8fc86239d9e` |
| `harness/q2_stage1/driver.py` | `3376678eb020c9a947f9c4fd71e333ae9b6ed9d8bac830ef5d7bcb85757fa9c2` |
| `harness/q2_stage1/agents.py` | `8e72acbd79645b45ccd95cd213d5f8564d7114af538561e28219c12cf0eb0ba1` |
| `harness/q2_stage1/engine.py` | `3e0942349a8fc5b2aef5294a28c029ca318acff88f4cd897df274bb6e3b51bf9` |
| `harness/q2_stage1/bridge.py` | `7083f728511477e8f32ed90a026290e6982ae04c9d5f8f61274112f5724d0550` |
| `harness/q2_stage1/fake_engine.py` | `02e0b66e7b67b3647dc853c4069de21ce3e6234ed01ec4e3842afbd42cd89a00` |
| `harness/q2_stage1/osworld_live.py` | `dacf6336a02c6a69a5f097be50385b7b31d389d5818abc8ecef4612e95153e12` |
| `harness/q2_stage1/lane.py` | `08847e43f2f2e81e0a77d6cfd3fe234aaefecf6fb67e8255de791529a8f5bf09` |
| `harness/q2_stage1/rescore.py` | `d240db03e969c8aa5bb97403c5005cd4c9e96016599a78f70e97850415893737` |
| `harness/q2_stage1/zinv.py` | `64899d5056f4791008c2a10c38a7b0fbb94fbe912d20a702ec74851a0ca7f655` |
| `harness/q2_stage1/anchor.py` | `6c0a31cf1abb261a3522573847ee6dc1798925143b286cf9c02a3550f1c93b7a` |
| `harness/q2_stage1/glmm.py` | `73e4d0f9100262eb0efe828a14308d2b45c17a3c827b476392b5045dfe1377e8` |
| `harness/q2_stage1/glmm.R` | `e3ea337c77bf6a8b9289047b62cfc51053a5f666fe51795071a1ae317f36681d` |
| `harness/q2_stage1/design_diffs.md` | `ef0ab3e8f4285cab130bb855dc4e082a5ea73adea6ede68c697ed2177f888309` |
| `infra/slurm/host-single-node/s1a-vm.sbatch` | `53fcd31d87678c6f5b4c929e6d843e5bc3177cac122842876f563e5191b09d45` |
| `infra/slurm/host-single-node/s1a-cpu.sbatch` | `3880d337ad5bb0dc3c0edfc39f41811028118ef574c75efb08faa023dc6dee33` |
| `infra/slurm/host-single-node/fetch-model-cpu.sbatch` | `22685e5e4dc9f88cd9d6ba7aec7189a89500a4f80d2464b8df86e08e76e33c6d` |
| `infra/q2-stage1/glmm/Dockerfile` | `e4a09458264a58a783ec91fed91b8e500c83a91c826fbaaa10b9ceb998df86b4` |
| `experiments/manifests/q2-stage1/gpu-engine.template.yaml` | `4b1140d53232db46f4a8be02e4f85b0e47fbdf87ce9f3a94a28b2e5fe789fe66` |
| `scripts/q2_stage1_upstream_fixture.py` | `bea62922d74f09b559d0fd8a3a16387df4862a532a2c62ffc6697271bedb9e89` |
| `tests/fixtures/q2_stage1/upstream_messages.json` | `0e10574ba44b4ae2e28b1c580faa80783060f5a16b013f360a10871d4198ba03` |

Outside `harness/q2_stage1/`: every in-repo module the code above imports, transitively
(lazy imports included), and every file it loads as code or data at run time (the
executor's guest program `l0_fixed.py`, the guard, the action-path catalog and the IR's
keysym table). The `harness/q2/` files are also pinned by the frozen action-path tables (G0
item 1 names the accepted attempt's executor, IR and adapter rows); the checker-mutation
study's `offline_eval.py` (the live file-cache shim and setup path) is unchanged since
`ba840b4`, before that study's freeze. `tests/test_q2_stage1_prereg.py` recomputes the
import closure and fails if any file is missing here.

| File | SHA-256 |
|---|---|
| `harness/__init__.py` | `17dac2704be26050e324aa36aba6d2c855abbd592e4d72f750b9b6e9c4399fec` |
| `harness/holo3_rerun_audit.py` | `785aa90eb59d81933a976986808da575844c689c796b6324085fded647a194dd` |
| `harness/publication_attestation.py` | `4a6afb7fe5a274b0401d2346d05af95bacc5b700565792d5265bc1f35d2c5c18` |
| `harness/q2/__init__.py` | `0932bda132c1dab03f40e460874a6827c4609424815e65eedcfefd3cd0b943a1` |
| `harness/q2/action_path/__init__.py` | `8ce4d0afdd20f6b09dbb4e9d40d24acead2fc1992fccebd1ddf3891ec402613f` |
| `harness/q2/action_path/adapters.py` | `3a62eb109d656a717dfe9cbce31fba3bcf02457e9f5690f3e20639e8becbaf40` |
| `harness/q2/action_path/catalog.py` | `2223a05b4e88dbc8af52751c9c87b10db99a121cdb93e5289979c657bf92126b` |
| `harness/q2/action_path/catalog.yaml` | `5934c4281cb85a8309be32cb98442b038054a2bba0e7ec3755e20112710b7bba` |
| `harness/q2/action_path/controls.py` | `d96e7b2acdecfef134c08c22f23113c8d78fae9d8a35d0e5ad826a2f0af9cc72` |
| `harness/q2/action_path/executor.py` | `d5c43bbb76926da056c15a39ddcbf05e1c328bd7dddb6a726cde3c46c2f9776a` |
| `harness/q2/action_path/ir.py` | `33dc24771b823597eef453a4994faf730d0364bd090488aa13e9de5e3498d305` |
| `harness/q2/action_path/keynames.py` | `ed7afec8fd66e1f1ba1a08e2df6eccd834a24f9f22e6bd4a79604153e3816b72` |
| `harness/q2/action_path/keysyms.json` | `a1ea436d9bd4ae8d9fbc8305772f7dca776858b023092ce1cea059a693924acb` |
| `harness/q2/action_path/l0_raw.py` | `391249f7900dfc327947505526b22710f7dd6bf70f71a230d9865ae7da174f84` |
| `harness/q2/action_path/order.py` | `cc709bd455f1899df11e8bf1e780d7efadc0ad374d8e2786bdc6f6e589b65676` |
| `harness/q2/action_path/rdev.py` | `c526f7ed5b8cc560c5419f9f5e25541b46178f2c375b24cbbee84e0093daab83` |
| `harness/q2/action_path/upstream/__init__.py` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `harness/q2/action_path/upstream/gym_anything_aae6f7607.py` | `c624cee586e3b8b8b2ac12102ae1fca91e7de154b494035c4289123f38887aa6` |
| `harness/q2/action_path/upstream/gym_anything_bf965cde0.py` | `f5fb13d2ab6eb024be48f28a439ecb3147308f126217054d4587649f9b1b818f` |
| `harness/q2/action_path/upstream/osworld_bfd62bdc.py` | `9e21622823994721407dc04f606b58c8cbd8848e780e4657e8ee13cb363c77ab` |
| `harness/q2/action_path/upstream/osworld_bfd62bdc_fixed.py` | `9558b956004f6c971e881f073c42792e3d5d437396dbe6c0b407b250df3d8fdf` |
| `harness/q2/action_path/verdict.py` | `29e4501532ab740922645a26a05a365a8aedc95f237efc66be5048df8354c8c4` |
| `harness/q2/action_path/vocab.py` | `f26dd7d34988aebf8e8bbeb3ea118e6da3b9d37505ba8433a6eb6d9f0f186792` |
| `harness/q2/action_path/volume.py` | `91cbbb7f2bf7cd8715ae7c3c88fb8744ff40bd89955283eb680578c24d2a09c7` |
| `harness/q2/vm/__init__.py` | `43fce1e08200acef9b9b82c914eba0713c0d60716bd2be0feaaade042dee3b19` |
| `harness/q2/vm/desktop.py` | `67030d6b5d79753e2db65b33bc12af2b5faaee2eacbaa5e49b4eb2de0a31c188` |
| `harness/q2/vm/driver.py` | `06f3a29f39ad3a5de55efafd23fdfdfe121914f0f7f5dba281f4aabb68f74f7c` |
| `harness/q2/vm/guest/__init__.py` | `99215662111076fd8ca080805ee2b36156cdec720470d16b612954c50f83362f` |
| `harness/q2/vm/guest/guard.py` | `19fe2da1c97c88e07062e9113a8df1b8958b583f6f3bf0e1a763f52eb10a5748` |
| `harness/q2/vm/guest/l0_fixed.py` | `7f8bed98ad22eee662d92d5422ee564d80459645d2e0c58bb6f3df74a94425f1` |
| `harness/q2/vm/guest/probe.py` | `ba5c0f1d364c80d5f8190f3c357b915cd504d754891285c3772ba959a804efeb` |
| `harness/q2/vm/guest/xrecord_tap.py` | `6a6e9453f138776b0717a9087767be0f97460f1ea0d5302f31e21ae1a4a80a74` |
| `harness/q2/vm/guest_http.py` | `13e34f874c89b0b32f7f82ffae658682d2608bc9a0614a569742459d6b796ceb` |
| `harness/q2/vm/marker.py` | `b786b347fc5573425f14090bd67621294ac5c84671bf67f47e663d693ab17fb9` |
| `harness/q2/vm/suite.py` | `6485ddb977d8adaf42ecc8c97f6520d3467633c54aeefba0cec877986805797a` |
| `harness/q2_mutation/__init__.py` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `harness/q2_mutation/offline_eval.py` | `a598e7fb71c434a7ef135afd250576db1025c4b0e77715413ab78c3e521f877a` |
| `harness/q2_mutation/reachability.py` | `00e106f6003a9f1ef9b9ca4cdbd59fbf1145c5608c6c67e37b57a7a094da0e9b` |
| `harness/q2_mutation/schema.py` | `65d91703754b4026b15f6c53a4a6069da723b58d749730770da2910c1edf427d` |
| `harness/q2_mutation/tasks.py` | `4040d852b18d06eea2fe47155ac642af689dea5477cd4a16a2dd5c71f42d8ecc` |
| `harness/remote_zip.py` | `534b84c97b54b83a8fce225bfecf2a23aaa7cd2501b0030121043caf857b2061` |

## 21. Sources (fetched 2026-10-08; hashes in the proposal's evidence bundle)

- cost card: `program/evidence/2026-10-07/serving-throughput-probe-v2/README.md`, `projection-v2.json`
- Holo3 session shift: `program/evidence/2026-10-07/holo3-v2/RESULTS.md`
- checker defects: `program/evidence/2026-10-08/q2-mutation-confirm/results/README.md`, `analysis.json`
- action path: `program/preregistrations/q2-action-path-v2.md` and its addenda; the v2 acceptance evidence: TBD (not yet run; `program/evidence/2026-10-08/q2-action-path-acceptance/` holds v1's C2 result only)
- OSWorld agents and runners at `bfd62bdc`: https://github.com/xlang-ai/OSWorld/blob/bfd62bdc5a3319809a236dc90ddbbaf3cb4b7e06/mm_agents/qwen35vl_agent.py, https://github.com/xlang-ai/OSWorld/blob/bfd62bdc5a3319809a236dc90ddbbaf3cb4b7e06/lib_run_single.py, https://github.com/xlang-ai/OSWorld/blob/bfd62bdc5a3319809a236dc90ddbbaf3cb4b7e06/scripts/python/run_multienv_qwen35vl.py, https://github.com/xlang-ai/OSWorld/blob/bfd62bdc5a3319809a236dc90ddbbaf3cb4b7e06/mm_agents/opencua/opencua_agent.py, https://github.com/xlang-ai/OSWorld/blob/bfd62bdc5a3319809a236dc90ddbbaf3cb4b7e06/scripts/python/run_multienv_opencua.py
- gym-anything at `aae6f7607`: https://github.com/cmu-l3/gym-anything/blob/aae6f7607e0f3d9d6306e1fefbad92bda99ca99a/agents/agents/qwen35vl.py, https://github.com/cmu-l3/gym-anything/blob/aae6f7607e0f3d9d6306e1fefbad92bda99ca99a/agents/agents/qwen3vl.py, https://github.com/cmu-l3/gym-anything/blob/aae6f7607e0f3d9d6306e1fefbad92bda99ca99a/agents/evaluation/run_single.py
- Qwen3.5 model cards (OSWorld-Verified 35.6 for 4B and 41.8 for 9B, first-party, evaluation settings not stated): https://huggingface.co/Qwen/Qwen3.5-4B, https://huggingface.co/Qwen/Qwen3.5-9B
- OpenCUA-7B (MIT; 24.3% at 15 steps, first-party): https://huggingface.co/xlangai/OpenCUA-7B; paper https://arxiv.org/abs/2508.09123 (2025-08-12)
- public trajectories: https://huggingface.co/datasets/xlangai/ubuntu_osworld_verified_trajs (MIT, revision 5473c39e)
- rerun flips 12-14% on the web: https://arxiv.org/abs/2608.06171 (2026-08-06)

## 22. Pre-freeze review log (2026-10-08)

Three adversarial reviews of the draft at `392e0ce` (identification and
statistics; compute and feasibility; protocol and governance) each returned
"not ready to freeze". Every blocking item is fixed below; none is rejected.
"R1-B2" is reviewer 1's second blocking item.

| Item | Finding (short) | Disposition | Where |
|---|---|---|---|
| R1-B1 | X label permutation and session-label permutation lose their size under a session excess | Fixed: the sign-flip test on per-task products is the primary X test, the label permutation a sensitivity; the session test is a two-sided sign flip over tasks; size and power re-run at excesses of 0-16 pp with the registered code | 10.1, 10.2 |
| R1-B2 | DR5's M ill-defined and in other units than π_small | Fixed: M frozen now, on the π° scale (D_b with session variance) for the registered estimator, against the simulated null critical value, for the small-pair contrast; larger-rung rates, grid, interpolation, seeds and the DR1 case pinned; negative X truncated at 0 and 0/0 = 0; DR3 made descriptive | 9, 11 (DR3, DR5) |
| R1-B3 | Estimands over the session population, inference over tasks only | Fixed: every estimand and DR2/P reading stated conditional on the realized sessions; δ heterogeneity check; GLMM gains (1\|harness:session) and (1\|task:harness:session) | 1, 9, 10.1 |
| R1-B4 | Agent-caused exceptions counted as infrastructure | Fixed: `IRError` handled by each harness's unparseable-reply rule; metric exceptions score 0 with a missing-data sensitivity; both kept out of DR0 and reported per cell | 7.2 |
| R1-B5 | The fill rule is not outcome-blind | Fixed: the base is the primary set for every estimand and rule; base plus completed extension blocks is a registered secondary; the "never on outcomes" wording is gone | 5.6 |
| R1-B6, R3-B3 | Stage-1 obligations of action-path v2 and the serving probe missing | Fixed: guard warm-up as episode step 3; uncertified exposure counted per episode and reported per harness with δ by stratum; mechanism sentence narrowed (proposal); A0a stated as the serving probe's re-probe, with its limits, for sign-off | 5.3, 7.1, 7.3, 15 |
| R2-B1 | Concurrency plan does not fit 208 CPUs; GPU jobs can start before VM jobs | Fixed: sizes always one after the other; V = 20 at N* >= 24, ANC V = min(32, N*); co-running CPUs at most 200; VM job first, GPU job `--dependency=after:` (new `start_after_job_id` in the docker submitter, tested); VM limit = cap + 10 | 5.5, 14 |
| R2-B2 | OpenCUA-7B cannot start at `max_model_len` 131,072 | Fixed: anchor argv with 32,768, 4 images and `--trust-remote-code`; a CPU load-and-validate check in O1's image before A0b | 3.1 item 9, 4 |
| R2-B3 | The anchor's cap cannot hold its episodes; cut episodes are outcome-dependent | Fixed: the slot priced with the runner's 60 s, 20 s and per-step pauses; n set from A0b by rule, at least 58 or no ANC; dispatch stop at 1.25 d; reading on the longest completed prefix; ANC cap 52, A0b 26 | 5.7, 6.1 |
| R2-B4 | Caps and the K-rule measured against the Slurm limit, not USR1; no launch or re-queue time; N* = 8 and 1 rows unworkable | Fixed: K-rule with the USR1 lead, measured L and 1.05; A0 caps checked as L + 1.25 slot <= cap − 3; N* < 16 stops S1a before any GPU job | 5.5, 6.1, 6.2 |
| R3-B1 | The freeze guard accepts the draft with values missing | Fixed: every unfilled slot carries the guard's placeholder, the status line included; truncated digests written in full; V-specific prices in 6.1 | throughout |
| R3-B2 | G0 omits C4 and pins the attempt-1 executor | Fixed: G0 item 1 is v2's own verdict (C1-C4, A1-A6 on one attempt, no kill); the accepted attempt's addendum by ledger row | 3.1, 4 |
| R3-B4 | DR0 and DR-A conflict on the anchor | Fixed: DR0 judges A1 jobs only; ANC by DR-A with its loss denominator | 11 |
| R3-B5 | M and DR3 not pre-specified | Fixed with R1-B2 | 11 |
| R3-B6 | X named an interaction | Fixed: renamed; an X rejection supports only "an effect is present"; X_c reported; the GLMM test is the interaction evidence | 2, 9, 10.1 |
| R3-B7 | P1-P5 claimed as preregistered but absent | Fixed: registered with falsifiers and reads | 12 |
| R3-B8 | Checker-correction counts and gate misstated; false positives unflagged | Fixed: counts per family; tolerant family not corrected; the gate is the 29 confirmed `compare_pptx_files` mutants; 70bca0cc, d53ff5ee, 30e3e107, 358aa0a7, a434992a flagged | 3.1 item 8, 8 |
| R3-B9 | H-GA's sampling override undisclosed | Fixed: upstream sampling row; greedy imposed on H-GA; top_k sent explicitly; native sampling out of scope | 1, 4, 5.2, 5.3 |
| R3-B10 | Code-change and confirm-contact rules contradict | Fixed: a change after A0 repeats that A0 (cap through the remainder rule); setup-only check is the sole confirm contact, extended to all pool and dev tasks; dev draw is filter-then-take | 1, 3.1 item 5, 3.2, 5.4, 6.2 |
| R3-B11 | Inconsistent with D47 and the question file | Fixed: only GO leads to S1b; the 24-task floor needs D47's amendment and the DR1/DR5 replacements need Kevin (section 18, items 17-18) | 11, 18 |

Non-blocking items:

| Item | Disposition |
|---|---|
| R1 X carries δ² | Fixed with R3-B6 |
| R1 decompose D_b − D_w | Fixed: same-block and cross-block D_b; first-divergence analysis; cached-token logging where the engine reports it without a flag change (the card's flags stay fixed) |
| R1 truncation sensitivity is post-treatment | Fixed: relabelled a mediator description; size-level truncation label; wording on the token cap |
| R1 GLMM omits (1\|task:harness:session) | Fixed with R1-B3 |
| R1, R3 DR2 family-wise error | Fixed: Holm over the two tests; the 90% interval is the t interval |
| R1, R3 anchor read on completed tasks | Fixed with R2-B3 |
| R1 H-GA fallback on any exception | Fixed: a non-context fallback is an infrastructure loss |
| R1 sequential size order | Fixed: seeded size order, same in both sessions |
| R1 base-completion margin | Fixed: the K-rule's USR1, launch and 1.05 terms |
| R1 checker share of discordance | Fixed: offline rescoring and identical-hash discordance counts |
| R1 DR-A assumes no session variance | Fixed: stated, with a simulation at a per-run shift |
| R2 c_A0a leaves out boot and setup | Fixed: slot occupancy at A1's V |
| R2 upstream sleeps | Fixed: matched settle for both harnesses; the anchor keeps its runner's |
| R2 thinking penalty may be low | Disclosed (section 19); A0a measures |
| R2 N* is an upper bound | Fixed: A0a's step-p95 gate |
| R2 O1/O2 retry | Fixed: O1 retry through the remainder rule; one pre-funded O2 retry |
| R2 fetch lanes request a GPU | Fixed: a GPU-less lane is a G0 item |
| R2 stale numbers | Fixed: cost JSON section `s1a_v2`; the reservation bounds recomputed; the "66 episodes" claim removed from the proposal |
| R3 line-315 overclaim, fill rule | Fixed with R1-B5 |
| R3 data handling | Fixed: section 16. The `/Users/...` worktree path in the proposal's verbatim doctor output is kept (not a secret; the same pattern is in 19 committed files) |
| R3 checker raises | Fixed with R1-B4 |
| R3 DR4 not V-specific | Fixed |
| R3 ANCHOR-FAIL next step | Fixed: S1a ends; any rerun is a new id |
| R3 Holo3 "confirmatory" wording | Fixed (section 1) |
| R3 anchor differences that are not runtime defects | Fixed: network difference stated; config and evaluator diff with exclusion (G0 item 9.6) |
| R3 c_A0a single wave; 4B truncation | Disclosed; A0a at A1's V |
| Found while revising | New code under `harness/q2/` would fail action-path v2's closed-world admission (design decision 35) for any acceptance campaign exported after it; S1a's code lives in `harness/q2_stage1/` and touches no file under `harness/q2/` |
| R3 missing data in δ | Fixed (section 10.1) |
| R3 section 17 sentence conditional | Fixed: the base-size limitation states the branch |

### G0 build (2026-10-08, D49 iv; CPU only, no GPU job)

What building G0 items 2-9 and 12 found, and what changed in this file because of it. None
of it has had the fresh pre-freeze audit D49 (iv) requires; each row is for that audit.

| Finding | Change here | Where |
|---|---|---|
| Every file under `harness/q2/` is pinned by a frozen action-path table, so S1a's differences from upstream cannot go in `harness_design_diffs.md` there | They are in `harness/q2_stage1/design_diffs.md` | 3.1 item 3 |
| The harness clients need Pillow (upstream image processing) and the checker needs OSWorld's locked environment; the stdlib runner image has neither | The episode container is the checker-mutation metric image; the certified transport code runs in it unchanged (Python 3.12 instead of 3.10) | 4 |
| The upstream system prompts carry today's date, so between-session pairs on different days differ in their first prompt | Kept as upstream and recorded per episode (`date_line`); the first-divergence analysis (section 9 item 11) reads a changed date as an environment divergence. Pinning the date is the alternative, for the audit. Superseded by C8 below: the date is pinned | 9 |
| H-GA reports `terminate(failure)` in metadata; S1a scores with OSWorld's evaluator | `FAIL` in OSWorld's action history for both harnesses (0 for a feasible task); the state's verdict is still captured and rescored offline | `design_diffs.md` |
| The certified IR refuses a `wait` over 10 s (`ir.MAX_WAIT_MS`) | Handled as the harness's unparseable reply (agent-caused, `ir_errors`) | 7.2 |
| The action-path rule counts a first `/execute` answered after 30 s as a loss; a long `type` is agent behaviour | Under S1a only a failed or retried `/execute`, or a missing screenshot, is a transport loss; a slow one is recorded (`slow_execute`) | 7.2 |
| `and` stops at the first failing metric and `FAIL` returns before any getter, so the files the checker read may not cover every metric | A capture sweep runs every result getter after `evaluate()` | 3.1 item 6 |
| The public runs' L2 system prompt is reproduced by neither prompt choice of the pinned anchor agent | Recorded (9.5) | 3.1 item 9 |
| The public runs predate `b138d348` by 14 months: 36 task configs and many checker definitions changed | Item 6 now makes the anchor UNAVAILABLE before any GPU job when fewer than 58 tasks remain readable; it does (at most 6) | 3.1 item 9, 5.7, 6.1 |
| vLLM v0.31.0 with transformers 5.17.0 cannot load OpenCUA-7B's remote tokenizer, and its `ModelConfig` validation needs a device (dry run, job 998; `check-vllm-dev.json`) | Recorded (9.3); moot while item 6 fails | 3.1 item 9 |
| The VM job must start before the GPU job, so the GPU job's run directory (the bridge) is unknown when the VM job is submitted | The lane reads the GPU job's id from a file the operator writes after submitting it (`gpu-engine.template.yaml`) | 3.1 item 4 |
| GLMM: a binomial `simulate` returns a successes-failures matrix per draw | `glmm.R` keeps the successes column | 3.1 item 12 |
| The comparator's validation failed twice before it passed (exact frames; empty text runs; text-only pairing under `examine_modify_height`) | Shapes are paired as the comparator examines them; the 29 confirmed mutants served as development set and gate, disclosed; no run changed another item's verdict | 3.1 item 8 |
| G0 item 8 said the comparator "ignores shape order only among shapes whose frames do not overlap" | The rule is now the mutation operator's: frames widened by rotation and more than 2 mm apart, unknown frames never apart | 3.1 item 8 |

### Correctness and readiness review of the G0 build (2026-10-08)

A further review of the G0 build (correctness and readiness lenses) returned eight blocking
items; each is fixed below with tests, none rejected. Like the G0 build table, this is for
the fresh audit D49 (iv) requires.

| Item | Finding (short) | Disposition | Where |
|---|---|---|---|
| C1 | Transport failures in the checker scored as agent outcomes: OSWorld's `get_vm_file` swallows `TransportFailure` (155 of 173 result getters over the pool and dev tasks), postconfig steps swallow or re-wrap a `ConnectionError`, `is_transport_error` read only the top-level type, and nothing re-checked the guest server after evaluation | Fixed: every guest-bound request that raises is recorded; setup, `evaluate()` and the capture sweep end in a transport loss when any of theirs failed; the exception chain is read; the restart check runs again after the capture, and an identity check that cannot reach the server is a transport loss. Tests drive the real `LiveTask` against a guest that resets connections, with a stand-in package that follows the pinned code's error handling; job 1010 ran the pinned OSWorld code (metric image, CPU only, no VM) on 13 pool tasks against a dead and a half-dead guest: the old rule scored 26 of 26 runs (0, or a metric exception scored 0), the fix records 26 of 26 as transport losses (`program/evidence/2026-10-08/q2-stage1-g0/transport-check/`) | 7.1, 7.2; `osworld_live.py`, `driver.py`, `design_diffs.md` |
| C2 | Control characters in typed text (a `\r` from CRLF line ends, ESC, C1 controls) pass the IR, make the guest executor exit non-zero and were recorded as `executor_device` losses, re-queued and, under greedy decoding, lost again, counting toward DR0 | Fixed: a `type` action whose text holds a code point L0-fixed refuses is an `IRError` from model output, handled by the harness's unparseable-reply rule and counted in `ir_errors`; a test checks the rule equals the guest's `char_keysym` | 7.2; `agents.py`, `design_diffs.md` |
| C3 | The lane's `submit` capped every VM job at 8 CPUs (`MAX_JOB_CPUS`, a temporary host-load rule hard-coded and never registered), so A0a and every A1 job (90 CPUs at V = 20) could not be submitted through the code of record | Fixed: `lane.check_slurm` requires a registered job's CPUs to equal `plan.vm_job_cpus(V)` and fit `plan.check_cpus([V], 1)`, and its limit to be the GPU cap plus 10 minutes; the host-load cap is `--host-load-max-cpus`, refused for any purpose but development and setup-check; tests cover V = 20 at 90 CPUs, V = 16 at 72 and the committed development manifests under the 8-CPU flag | 5.5; `lane.py` |
| C4 | The pinned GPU-engine template declared `randomness_contract: deterministic` with `seeds: [42]`, which the docker submitter refuses once the `FILL_*` slots are filled, so no GPU half of a pair could be submitted | Fixed: `seeds: []` (the engine seed reaches vLLM through `plan.CARD_ENGINE_FLAGS`, `--seed 42`); hex fields quoted so YAML cannot read one as a number; a test fills the template for 9B, 4B and the anchor and passes it through the submitter's `validate_manifest` and `sbatch_argv` (`--gres=gpu:h100:1`, 32 CPUs, `--signal=B:USR1@180`, `--dependency=after:` and the VM job's id) | `gpu-engine.template.yaml` |
| C5 | The K_base floor in the branch S1a is in (anchor unavailable before A0b) was 24 in code (`freeze_constants` defaulted to `K_FLOOR`), 32 in D49 (i), and ambiguous in section 6.2 and item 18's note, so the documented procedure would have frozen K = 24 without the anchor | Fixed: the floor follows the branch (32 without the anchor, whatever is signed; 24 only with the anchor running and `k_floor=24` passed after item 18); `freeze_constants` defaults to 32 and records the floor applied; section 6.2, item 18 and section 19 state D49 (i) and that K = 32 needs a mean A0a slot of at most about 728 s, below the card's high slot of 743 s, so going back to review after A0a is a live outcome; a test runs the issue's case | 6.2, 18, 19; `plan.py` |
| C6 | The truncation and concurrency gates of section 6.2 existed only as text: `freeze_constants` read neither, episode records could not tell a cap hit without a tool call, and section 15's label counted any cap hit | Fixed: `plan.a0a_gates` computes both from A0a's step logs (per-harness share of turns at the cap without a complete tool call; the action path's p95 statistic over every `DesktopEnv.step`), `freeze_constants` requires the result and refuses a failed or unreadable gate; records gain `truncated_no_tool_call_steps`, and section 15's label uses the gate's definition beside the plain cap-hit rate; a CLI reads the host run directory | 6.2, 7.3, 15; `plan.py`, `driver.py`, `records.py`, `analysis.py`, `lane.py` |
| C7 | No registered code turned the frozen plan into lane manifests, and the lane checked only that a slot's task was in the dev split or the pool, so the base, the dev-task choice, the block orders, the rerun-to-block mapping (same- and cross-block D_b) and the extension sub-blocks were enforced by nothing; the plan file stored the orders' digest but not the orders | Fixed: `plan.a0a_slots` and `plan.a1_slots` render every registered job's slots and fill blocks; the plan file now holds `episode_orders`; `scripts/render_q2_stage1_manifest.py` renders the lane manifest (and the GPU half from the template); `lane.validate_manifest` requires N* for A0a and the frozen plan file, its digest as stated in the registration, for A1, recomputes session 2's blocks from both session-1 record files, refuses any slot or fill difference, and refuses the anchor purposes; tests cover A0a, A1-S1 (fill) and A1-S2 | 3.1 item 10, 5.5; `plan.py`, `lane.py`, `records.py`, `render_q2_stage1_manifest.py` |
| C8 | Today's date in the system prompt was left open: between-session pairs (at least 12 h apart) almost always see a different date and weekday and within-session pairs the same one, so D_b, the session excess (P1), u_zt and ρ were confounded with a deterministic prompt change | Fixed, option (a): one date, `plan.PROMPT_DATE` = 2026-10-08, for every A0a, A0b, ANC and A1 episode through the lane manifest's `date`, which `validate_manifest` requires for those purposes; the plan file records it; the guest's own clock stays unpinned and is disclosed | 5.2, 9, 19, 3.1 item 10 (draft plan digest); `plan.py`, `lane.py`, `design_diffs.md` |

Found while fixing (not one of the eight; reported for the audit): G0 item 5
counts base task `26150609` (multi_apps, the Snake game) as a completed setup, but its
second step, `pip install pygame`, cannot succeed with no network: the guest answered with
an error after 120 s (the item's longest setup) and OSWorld's `command` step logged it and
went on, as it would upstream (setup-check container log, job 982). Its checker runs the
task's test suite in the metric image, which has pygame (the mutation study scored its gold
offline), so scoring is unaffected; but the agent's VM lacks the pygame that the upstream
online setup installs, so the agent cannot run the game there. This paragraph also said that
no other pool or dev task's setup or postconfig needs the network; **the pre-freeze audit
below showed that wrong** (`e2b5e914` installs a Marketplace extension) and unchecked for
two more (`53ad5833`, `d38192b0`). The audit's B1 and B2 settle all four (section 5.4,
G0 item 5).

### Pre-freeze audit of the G0 build (2026-10-08)

A fresh independent audit of the draft at `72b3e76` (D49 (iv)) returned "not ready to
freeze once the action path passes" with eight blocking items. Each is fixed below with
tests; none is rejected. The cheap non-blocking items are fixed too; none is left open.
Everything is CPU-only; no GPU job and no GPU episode ran.

| Item | Finding (short) | Disposition | Where |
|---|---|---|---|
| A-B1 | The setup check cannot see a step that fails inside the guest (the guest answers `/setup/execute` with HTTP 200 and a `returncode`; the pinned code only logs a reply that is not 200; `setup.jsonl` kept no per-step result). `e2b5e914` needs the network; `53ad5833`'s `.vsix` install and `d38192b0`'s postconfig `pip install` were never checked; "task setup fails" was undefined for an in-guest failure; section 22 said no other task needs the network | Fixed: `osworld_live` records every guest `/setup/*` reply per step (status, `returncode`, stderr tail) in the episode record (`setup.replies`, `postconfig_replies`; stdout tails only in the capture on the host, section 16); section 7.2 defines a failed task setup (a step that raises, or a reply that is not 200 or carries a non-zero `returncode`) as a `task_setup` loss, with no deterministic offline failure tolerated in its place; a failed postconfig reply is recorded, not a loss. Section 5.4's offline-setup exclusion (rules (a)-(c)) was registered and committed (`8b4a874`) before G0 item 5's second pass ran (job 1011, with the postconfig on the initial state and `code --list-extensions` for `53ad5833` and `e2b5e914`): it confirms `26150609` and `e2b5e914`, finds base task `982d12a5`'s setup failing for want of `jq` in the guest, and clears `53ad5833` and `d38192b0`; the rule excludes the first three and the base is re-drawn on 113 tasks. The wrong sentence is corrected. The code landed before A0a, so no A0 repeat is owed | 3.1 item 5, 5.4, 7.2, 7.3, 22; `osworld_live.py`, `driver.py`, `lane.py`, `plan.py` |
| A-B2 | Base task `26150609`'s offline failure left open, and the freeze guard could not see it | Fixed, the audit's option (b), by rule rather than judgment: rule (a) removes it before the draw (its setup installs `pygame` from the network); the base is re-drawn by the registered seeded procedure on the eligible pool; Kevin's sign-off is a slot in section 18 | 3.1 item 5, 5.4, 18 |
| A-B3 | DR2 checked the Near-equivalent bound on the two-size mean of pi when DR1 drops 4B (half of pi_9B when 4B is at the floor) | Fixed: `analysis.analyse_array` applies section 9 item 4's rule, so DR2's bound, DR5's share and the reported pi_small are pi_9B's when DR1 drops 4B (`pi_mean_4B_9B` beside it); a test with 4B at the floor checks the bound DR2 receives | 9, 11; `analysis.py` |
| A-B4 | A0a's inputs to K_base and the freeze typed by hand; L_A0a undefined; only scored A0a episodes counted, which drops the longest | Fixed: `plan.a0a_measurements` derives every input from A0a's lane run directory and its GPU job's bridge directory (slot occupancy of all V slots, L_A0a, both gates over the same V episodes, the files' digests); the lane records the GPU job's Slurm start (`scontrol`) and its first dispatch, the bridge its first forwarded request; L_A0a runs from the Slurm start to the first dispatch (the slot already holds the first boot, setup and settle); any cut or undispatched A0a slot, or fewer than V completed, sends the draft back to review; the plan renderer's freeze mode reads the records (its hand-typed `--constants` is gone) | 3.2, 6.2; `plan.py`, `bridge.py`, `lane.py`, `render_q2_stage1_plan.py` |
| A-B5 | DR0's stop, the 9B-then-4B order and the 12-hour gap existed only as text | Fixed: `rules.job_dr0` and `python -m harness.q2_stage1.rules dr0` judge one A1 job from its lane records and receipt; each A1 manifest names every earlier A1 job's record file and receipt by SHA-256 in `plan.a1_job_order`, and the lane refuses a missing or changed file or a job that fired DR0; a session-2 VM job is submitted with `--begin` at the later session-1 end plus 12 hours and the lane refuses to start earlier | 5.5, 11; `rules.py`, `lane.py`, `plan.py`, `render_q2_stage1_manifest.py` |
| A-B6 | The episode image, re-queue, episode timeout and the GPU half's cap and model were operator input | Fixed: A0a and A1 manifests must name the registered episode image and may not set re-queue, the episode timeout or the interpreter; the GPU half is rendered from the validated VM manifest (size and cap), with no free size or minutes; before dispatch the lane checks the GPU job's `ready.json` engine argv against `plan.engine_argv` for the job's size and its Slurm time limit against the cap, and counts USR1 from the Slurm start | 5.5, 5.6; `lane.py`, `render_q2_stage1_manifest.py` |
| A-B7 | Kevin's sign-offs and the unanchored read were not slots, so the guard would have frozen the file without them | Fixed: three sign-off slots in section 18 (Kevin: item 17 and the read without the D11 check; Kevin: G0 item 5's decisions; the program: items 1-16 and 19-27); a test checks them | 18 |
| A-B8 | "Realized GPU-h per episode" (DR4, P5) undefined and computed by nothing | Fixed: section 9 item 10 defines it (the GPU job's Slurm elapsed hours, EndTime minus StartTime as the VM lane records them from `scontrol` because accounting is off on the host, with the bridge's stop time as the registered stand-in for a missed end, over the job's episodes that ran to an end; per harness by slot-occupancy share); `analysis.realized_costs` and `python -m harness.q2_stage1.analysis costs` build `costs.json` from the lane records, with no typed input | 9, 11; `analysis.py` |

Non-blocking items:

| Item | Disposition |
|---|---|
| First divergence read prompt token-id digests, which cannot see an image | Fixed: the processed screenshot, then the request and the IR; the top-bar clock disclosed (section 9 item 11) |
| `checker_noise` read a field `rescore.merge` never writes | Fixed: it reads `offline_raw_score`; a test covers it |
| Guest clock wording | Fixed: the date also differs within a job that crosses the guest's midnight; every A1 prompt date differs from the guest clock; no checker reads the date (sections 9, 19) |
| Re-queue position | The text now states `Dispatcher.requeue`'s rule (section 7.2) |
| Fill rule from the first request; USR1 from the bridge's start | The text says the first dispatch; USR1 now counts from the GPU job's Slurm start |
| Queue wait and prefix-cache counters | The bridge samples vLLM's queue-time histogram and prefix-cache counters every 30 s; the text says per-request values are not reported at the card's flags (section 7.3) |
| Prose and angle-bracket text that trips the freeze guard | Reworded; a test fills every open slot on a scratch copy and freezes it |
| Section 20 incomplete | Every module the S1a code imports, transitively, and every file it loads is listed; a test recomputes the closure |
| D12 in the S1a lane | The episode container checks for `/dev/nvidia*` before anything else; the lane stops dispatching on a visible device (3.1 item 3) |
| No "not externally anchored" label | `analysis.report` emits it (`external_anchor`) |
| N* = 16 | Back to review before A0a; the lane and the renderer refuse A0a below N* = 24 (3.1 item 1, 5.5, 6.2) |
| Agent-caused events classed as infrastructure; `OfflineNetworkRefused` scored as a metric exception | Disclosed (section 19); a checker that needs the network is an `offline_network` loss (7.2) |
| Checker-input hashes of saved files | Disclosed (section 9 item 11) |
| The lane did not check the setup-check records' digest | `plan.load_setup_check` refuses a record file whose SHA-256 is not the registered one; the lane and both renderers use it |
| Stale text | Status line (D49 (ii)), the A1 GPU-h row for K = 32, the wall-clock per A1 job |
| A GPU job that starts late | Stated with the pairing rule (section 5.5) |
| Anchor branch slot of section 6.2 | Filled: unavailable before A0b, n = 0 |

Open slots until the freeze (each carries the placeholder the guard refuses): the status
line; G0 item 1 (accepted attempt) and item 10 (frozen plan); section 4's executor row;
section 6.2's constants other than the anchor branch; section 18's three sign-offs; section
21's v2 acceptance evidence.

