# q2-evaluator-mutation-v1-k2: K2 VM-fidelity addendum to q2-evaluator-mutation-v1

**Status: DRAFT. Not frozen; no ledger row exists. A pre-freeze audit is pending
(decision D73 (ii)), and the freeze is the program owner's step.** Until this
file has its own ledger row the K2 lane refuses every confirm-split job and runs
only development jobs on dev-split items (section 4). Nothing in this file is a
result.

- Experiment id: `q2-evaluator-mutation-v1-k2`, an addendum to
  `q2-evaluator-mutation-v1` (ledger row 11: file SHA-256
  `57dc009261244cbdda6dabae2144843a5094dd3e5c31e7810d59c2f70d16c8a5`, row hash
  `dc39bfa2f68e0fd5...`, `git_head_at_freeze`
  `71fe02e42b34edd8ba2f710c31bdea164224d76e`). It changes no rule of the
  parent. The parent's section 10 registers the K2 sample, the comparison, the
  four explanations and the consequence, and says "No executor commit is
  available at this draft (the branch is unfinished), so K2 is not a
  precondition of the freeze or of the confirm run". This addendum supplies the
  executor and states exactly which comparison is made, on which items, with
  which pass rule, what happens if fidelity fails, and how K2 interacts with the
  pending adjudication.
- Drafted 2026-10-11 on branch `stage0/q2-mutation-k2` from main at `0c29047`,
  under D73 (ii): R03 of the question-renewal dossier
  (`program/evidence/2026-10-11/question-renewal/dossier.md`, item O3: "R03's K2
  executor does not exist").
- Route: the existing frozen registration with an executor amendment, a
  pre-freeze audit and its own freeze (D73 (ii); dossier, "What each needs
  before any GPU"). No GPU step, so the research gauntlet and D24 are not
  engaged.

## 1. The K2 comparison

For each sampled scoring job, the comparison is the in-VM verdict against the
offline verdict for the same `candidate_sha256`:

- **In-VM verdict.** The job's candidate is injected into a freshly booted
  certified VM that has run the task's own setup, saved by the VM's own
  LibreOffice as the pipeline saves it, and scored by the pinned, unmodified
  `DesktopEnv.evaluate()` running over the VM, with `DONE` as the last action.
  The verdict is `pass` iff the score is 1.0, `error` iff `evaluate()` raised
  inside the checker or returned `None`, and `fail` otherwise
  (`harness.q2_mutation.schema.verdict_for_score`, the offline rule).
- **The candidate.** The files of the job's row in the mutation run's
  `build/scoring-jobs.jsonl`: the mutant (or null mutant) file the offline save
  stage started from, whose SHA-256 is the job's `candidate_sha256`, plus the
  task's other gold files, placed unchanged (the parent's "context"). Context
  files that a postconfig `--convert-to` derives are left to the postconfig
  (section 3.3).
- **Offline verdict.** The lock-exact verdict row of the same job in
  `released/confirm-mutants-v1/verdicts-lock.jsonl`, whose `candidate_sha256`
  must equal the sample's. Its offline repeat scorings disagree iff the job is
  in `notes-summary.json`'s `lock.nondeterministic` list (empty in the confirm
  run).

**Items.**

- **K2 (registered; feeds the parent's analysis).** The 80 jobs of the frozen
  K2 sample, drawn by `campaign k2-sample` in job 3 of `confirm-mutants-v1`
  before any verdict existed (parent section 10): 20 per domain over
  `libreoffice_calc`, `libreoffice_impress`, `libreoffice_writer` and
  `multi_apps`, 41 tasks, 73 mutants and 7 null mutants, offline verdicts 42
  pass and 38 fail. By checker family (the job's metric functions,
  `campaign.checker_family`): `compare_table` 27, `compare_pptx_files` 23,
  `compare_docx_files` 11, `compare_line_spacing` 6, `compare_docx_images` 6,
  `check_tabstops` 3, `evaluate_strike_through_last_paragraph` 2,
  `compare_docx_tables` 1, `compare_csv+compare_table` 1. The sample holds one
  checker candidate event (a `pptx.eq.zorder_nonoverlap` false negative); the
  other mutants are 56 evaluable non-events, 8 ambiguous, 7 `null_not_pass` and
  1 normalized, each compared on its verdict whatever its label.
- **K2-C (descriptive; never passed to the analysis).** The 41 checker
  candidate events of the confirm campaign (section 8): 36 false negatives
  (35 `compare_pptx_files`, 1 `compare_pptx_files_tolerant`, all
  `pptx.eq.zorder_nonoverlap`) and 5 false positives (`FP_R`: 3
  `compare_pptx_files`, 1 `compare_pptx_files_tolerant`, 1
  `compare_docx_files`), on 17 tasks. One of them is also in the K2 sample and
  is run in both sets.

Every pair is run twice, in two independent fresh VMs (section 4).

## 2. Identity and pins

| Object | Pin |
|---|---|
| Parent | `program/preregistrations/q2-evaluator-mutation-v1.md`, ledger row 11 (above); its pins block (code tree `58bee0190c0c7eb5d44f36e27c0f1e0daab82c1c48716009a9066777c69a0721`) is unchanged: this addendum adds no file under `harness/q2_mutation/` or `infra/q2-mutation/` |
| K2 sample | `program/evidence/2026-10-08/q2-mutation-confirm/results/released/k2/k2-sample.jsonl`, SHA-256 `1194168019c4aa87fa3f4aa0ad02f9ed53c207a86ebec264e731545afed6525a`; its summary (`mutants-confirm-v1/score/k2-sample.summary.json`) records `jobs_sha256` `9c2426b7dce17f6357950b0bdb2560ce1a20005a5702a49b5058d840fa811b14`, seed 42 |
| K2-C list | `program/evidence/2026-10-11/q2-mutation-k2/k2c-candidates-confirm.jsonl`, written by `harness/q2_mutation_k2/candidates.py` from the released outcomes and verdicts. K2-C list SHA-256: `c7b1869049749c8311e73f3ba09ea98e53e45086d49922c6ccea72ab6bb8a028` |
| Offline verdicts | `released/confirm-mutants-v1/verdicts-lock.jsonl`, SHA-256 `e9289a954d5aee21156d0b317267b6f818f630b140ac5337e8fae0cc4c66b021` (1,300 rows) |
| Offline repeats | `released/confirm-mutants-v1/notes-summary.json`, SHA-256 `de597827720bce5aacffa6e51f649510f425bbd89cf558f52da5fe0f881ee823` |
| Offline outcomes (K2-C only) | `released/confirm-mutants-v1/outcomes.jsonl`, SHA-256 `b1bd6a87f1d80d8eca79af417801b359a88d02dfeb04d1f282d6859bdde0be88` |
| Candidate files | the host's `confirm-mutants-v1/build/files` (mutant documents never leave the host, parent section 16); every file is hashed at submission and again inside the run, and the target file's SHA-256 must equal `candidate_sha256`; context files from the pinned file cache must match `program/evidence/q2-mutation/harness/file-cache-receipts.tsv` |
| VM runtime | action-path v2 section 2.1 (ACCEPTED on attempt 1, D53; certified at N* = 32): `happysixd/osworld-docker@sha256:0e6497a9295647cf05bf2b2af522fdd79bdeba2737595259cab310a3bcf6baa9` (image ID `sha256:fe8d9a5e5ad6c593d059887ea2c790481b3f32dd42fa961f2441cdbbe2c70cf4`), guest disk `Ubuntu.qcow2` SHA-256 `6bf667a852b3c307f61d9f09c42559351f45e0607e428b4997becf534cf4d313` (24,460,197,888 B, read-only), 4 GB RAM, 4 cores, 32 GB disk, 6 GB container memory, `none-netns`, guest server port 5000. The VM's LibreOffice is its own Ubuntu build (`libreoffice-core 1:7.3.7-0ubuntu0.22.04.4`, the parent's section 2) |
| Episode container | the parent's metric image `sha256:2006c1a9247e4911a82508cd22e9d9a7efc5c13e35a20e8a03baac7112876230`, `/opt/venv-lock/bin/python` (the lock-exact venv); read-only root, no capabilities, no GPU variables, in the VM container's network namespace (D13) |
| OSWorld | `b138d348256078fa634fc3b73567a7337c793e6b` (the parent's checkout, mounted read-only); the pinned file cache, served locally (S1a's network shim: guest requests pass, file-cache URLs are answered from the hash-checked cache, every other URL is refused) |

Reused code, unchanged and pinned elsewhere (each file's SHA-256 on main at
`0c29047`, equal to its frozen pin):

| File | SHA-256 | Pinned by |
|---|---|---|
| `harness/q2_mutation/vm_injection.py` | `43886a101ea7f0dc569454be99bd7bfd1fea051713e0ec886ca25dcf3071f567` | parent code tree |
| `harness/q2_mutation/reachability.py` | `00e106f6003a9f1ef9b9ca4cdbd59fbf1145c5608c6c67e37b57a7a094da0e9b` | parent code tree |
| `harness/q2_mutation/tasks.py` | `4040d852b18d06eea2fe47155ac642af689dea5477cd4a16a2dd5c71f42d8ecc` | parent code tree |
| `harness/q2_mutation/schema.py` | `65d91703754b4026b15f6c53a4a6069da723b58d749730770da2910c1edf427d` | parent `schema_sha256` |
| `harness/q2_mutation/analysis.py` | `4424eed4fa7cc8098e6a4103c495ca7ff150cc38c984bd918fd8498898081edd` | parent code tree |
| `harness/q2_stage1/osworld_live.py` | `38b017c04f67b59e08bc1d764702a2ff91c80ebde8054c8e80bc277746334313` | `q2-stage1-rescoped-v1` section 20 |
| `harness/q2_stage1/driver.py` | `52f835f6a2f8149ec0b3c14720593c02a42e1d410ab25062845fd3700aeee227` | `q2-stage1-rescoped-v1` section 20 |
| `harness/q2_stage1/lane.py` | `d646b144f857d5947ed20d27a5d33107123913321969c89af22729674246eaa5` | `q2-stage1-rescoped-v1` section 20 |
| `harness/q2/vm/` (all 20 files) | the action-path v2 tables | `q2-action-path-v2`, `-inputs`, `-executor` (86 pinned files, all byte-identical on main) |

New code of this addendum (SHA-256 of the committed bytes; refreshed before the
freeze; `tests/test_q2_mutation_k2_prereg.py` fails on drift):

<!-- k2-code-table start -->
| File | SHA-256 |
|---|---|
| `harness/q2_mutation_k2/__init__.py` | `66667a5fcd60b2bfcb72dbe74c94b1443f68dbe75a6ce0cf28816807cccc1ebf` |
| `harness/q2_mutation_k2/candidates.py` | `cf1dbcb56de21a452015eb45652128384fae2eb7d766a2e951fe5a8daeb6df3b` |
| `harness/q2_mutation_k2/executor.py` | `bda81bda66bc7c368adf226b1ec689014c2866e8e726af43d98ecfdd090dde8a` |
| `harness/q2_mutation_k2/guest/k2_guest.py` | `869ebb3811f44ee990f587077756c3bb774392930e6973a54a2225714608dda8` |
| `harness/q2_mutation_k2/lane.py` | `472479c5a927cbdeac07f4280db675d836bd6fa90a397efbbda4bed5bf2f183c` |
| `harness/q2_mutation_k2/report.py` | `c8a68a173c0ffc130ee576ecdc0bac6d74ec88a306c3d2f49591247891d204c4` |
| `harness/q2_mutation_k2/rules.py` | `58ea109a1aff6d6b059b6ca841b99a3a8b7ca858fe698c8b5ab33238e6be8c05` |
| `infra/slurm/host-single-node/q2m-k2-vm.sbatch` | `0cddd6bb624758f66e0f02c45b1c7cfb7a6e2d4dcc8aa9dc7e1d983077b8c6b0` |
<!-- k2-code-table end -->

## 3. One run

`harness/q2_mutation_k2/executor.py`, one process per run inside the episode
container, executing the frozen plan of
`harness/q2_mutation/vm_injection.py` (`build_injection_plan`, whose
`check_plan` invariants hold for every plan) in the plan's order.

### 3.1 Before the plan

1. Wait for the cold boot (S1a's `driver.Runner.wait_for_boot`: a screenshot
   answers within 300 s).
2. Check each candidate file against its declared SHA-256 inside the container;
   one file must carry `candidate_sha256`.
3. `reset_task`: the task's own setup on the clean VM (S1a's
   `osworld_live.LiveTask.setup`, the pinned `SetupController.setup(config)`).
   A setup step that raises, or whose guest reply is not HTTP 200 or has a
   non-zero `returncode`, fails the run (cause (4)).
4. The guard's keyboard warm-up, once per boot (action-path v2 design decision
   31; S1a's `driver.Runner.warm_up`), so that no save's Ctrl+S is the boot's
   first XTest key event (development run 549 of the action-path suite lost a
   chord's modifier on that event), then OSWorld's 60 s settle (S1a section
   7.1 step 4).

### 3.2 The plan's ops

- `kill_process` (`soffice`, or `gimp` for image targets): for LibreOffice, its
  own Quit first (one of its windows activated with `wmctrl -a`, then Ctrl+Q
  through the guest's pyautogui), awaited 15 s; then SIGTERM to every process
  still alive whose name or first argument names the application (`oosplash`
  and `soffice.bin` for LibreOffice), and SIGKILL to any still alive after
  20 s; the run fails if any survives 5 s more. LibreOffice's `.~lock.NAME#`
  file next to each target is then removed. (Development job 1113 showed that
  a SIGTERM leaves the open document in LibreOffice's recovery list, so the
  reopened document came up behind a "Document Recovery" dialog; its Quit
  leaves no such dialog.)
- `assert_no_window`: no window title (`wmctrl -l`) contains a target's file
  name.
- `hash` `pre_inject`, `post_inject`, `pre_postconfig`: SHA-256, size and
  mtime of each target, read in the guest (`harness/q2_mutation_k2/guest/k2_guest.py`).
  At `post_inject` every placed file must equal its candidate digest, else the
  run is cause (3).
- `upload`: the pinned `SetupController._upload_file_setup`, the guest server's
  `/setup/upload` endpoint that the task's own download step uses.
- `config_step`: the task's own `open` or `launch` step for the target, through
  the pinned `SetupController`, then a wait (at most 90 s) for a window whose
  title names the file. Every executor setup step (upload, open, activate,
  Ctrl+S) must return within 180 s (the guest server's `/setup/open_file`
  otherwise waits up to 1,800 s for a window), else the run fails (cause (4)).
- `agent_save`: if no window names the file, the `open` step and the window
  wait; `activate_window` with the window title `"FILE - LibreOffice APP"`
  (for example `"report.docx - LibreOffice Writer"`), strict; the postconfig's own Ctrl+S command
  (`python -c 'import pyautogui; pyautogui.hotkey("ctrl", "s");'`); then a
  wait (at most 30 s) until the file's (mtime, size) changes and holds for 0.3 s
  (the offline save stage's `LoSession.wait_written` rule).
- `open_file`: the `open` step, then the window wait.
- Any window title naming "Document Recovery", "Document in Use" or "Locked
  Document" after a reopen, or before the postconfig, fails the run (cause
  (4)): such a dialog would block the save.

### 3.3 Postconfig outputs

A candidate file that a postconfig `libreoffice --convert-to` produces (in the
conversion's output directory, `stem.ext` or `stem-*.ext` of a converted input)
is not uploaded: the VM's postconfig makes it from the saved document, as the
offline save stage deletes such a file before its conversion
(`reachability.LoSession.convert`). The run records the paths it left out.

### 3.4 Evaluation

After the last executor op: S1a's 20 s settle before evaluation and its
guest-server restart check, the window check above, then `hash pre_postconfig`.
The plan's last three ops (`postconfig`, `hash post_postconfig`, `evaluate`)
are executed as one call of the pinned `DesktopEnv.evaluate()`, which runs the
task's postconfig itself and then the getters and the metric, exactly as the
pipeline does. `post_postconfig` is read without any guest call between the
postconfig and the getters: it is the SHA-256 of the bytes each getter's
`get_file` returned (S1a's `CaptureController`). Then `hash post_evaluate`; a
postconfig-saved target whose checker-read bytes equal its pre-postconfig bytes
(unsaved at read) is watched up to 30 s more for a write. Then S1a's capture
sweep and capture (the checker inputs, kept on the host) and the final restart
check.

## 4. Runs, order and re-queue

- Two runs per pair, each in its own freshly booted VM. Slots are ordered in
  blocks: the K2 sample's first runs, its second runs, then K2-C's first and
  second runs, so a stop leaves the registered sample's runs done first.
- The K2 lane (`harness/q2_mutation_k2/lane.py`) is S1a's lane
  (`harness.q2_stage1.lane.Lane`) with K2's slots and records: continuous
  dispatch, one re-queue of a run lost to infrastructure on its first attempt
  (at the end of its block), the USR1 stop (runs cut or never dispatched are
  recorded `cap_truncated`), host snapshots and the D12 stop.
- The registered job (purpose `k2`): V = 8 concurrent VMs (at most 32, D53),
  Slurm 40 CPUs, 64 GB, 360 minutes, run timeout 900 s, settles 60 s and 20 s,
  candidates from `confirm-mutants-v1`, and exactly the registered slots (the
  K2 sample in its order, then the K2-C list in its order, two runs each). The
  lane refuses any other manifest after this file's freeze, and refuses the
  `k2` purpose before it. One job; it is rerun only under section 6's repair
  rule.
- CPU-only Slurm job through `infra/slurm/host-single-node/q2m-k2-vm.sbatch`
  (S1a's VM batch file with K2's names: no GRES, no GPU variables, the batch
  file's, manifest's and source tree's digests checked, Docker's runc runtime,
  labelled containers removed on exit). One host job at a time, checked against
  `squeue` first (D71, D73).

## 5. Classification

`harness/q2_mutation_k2/rules.py`; the report step (section 7) applies it.

### 5.1 A run

A run is **scored** when its in-VM verdict exists (pass, fail or error). It is
**excluded** under one of the parent's two exclusion causes:

- (3) `injection_hash_mismatch`: a placed file's in-VM SHA-256 after upload
  differs from its candidate digest;
- (4) `vm_infrastructure_failure`: the boot wait times out; the task setup fails
  (section 3.1); the warm-up fails; a candidate file differs from its digest in
  the container; an executor op fails (kill, a window that names a target after
  the kill, lock removal, upload, reopen or open without the window within 90 s,
  a recovery or lock dialog, an agent save not written within 30 s); a guest
  request of the run fails in transport; a checker observation goes
  undelivered (S1a's D53 (iii) rule); the checker asks for a URL the offline
  run cannot serve; the guest server restarts (S1a's identity check after the
  settle and after the capture); the run exceeds 900 s; the VM container does
  not start; the runner crashes.

A run lost on its first attempt is dispatched once more; the run is scored if
either attempt scored, and excluded otherwise (cause (3) if either attempt
ended in a hash mismatch). A run never dispatched or cut at a stop is missing
and counts as cause (4).

Not exclusions: a postconfig step whose guest reply failed (recorded; it is the
pipeline acting on the end state, S1a section 7.2); a metric that raises or
returns `None` (the verdict `error`); a postconfig save that did not write by
the time the checker read the file (recorded, section 5.2).

### 5.2 A pair

A pair is **excluded** when neither run scored, with cause (3) if any attempt
ended in a hash mismatch, else (4). Otherwise it is **compared** on its scored
runs (one or two). It **agrees** when every scored run's verdict equals the
offline verdict. Otherwise it **differs**, and its explanation is the first of:

1. `save_slower_than_0_5s` (cause 1): every differing run read, at the checker,
   the pre-postconfig bytes of a target the postconfig saves (its
   `post_postconfig` digest equals its `pre_postconfig` digest), and that file's
   bytes on disk changed after the read (at `post_evaluate` or within the 30 s
   watch): the save landed after the checker read the file;
2. `nondeterministic` (cause 2): the offline repeat scorings disagree (the job
   is in `lock.nondeterministic`), or the pair's two scored runs disagree with
   each other;
3. `unexplained`: anything else, including a save that never wrote, a verdict
   `error` in the VM, and a difference both runs reproduce.

## 6. Pass rule, fitness gate and what happens if fidelity fails

- **Fitness gate.** At most 8 of the 80 K2 pairs (10%) may be excluded. Above
  that the executor is not fit (R03's slate: "If more than 10% of K2 pairs are
  infrastructure exclusions, the executor is not fit: stop and fix"). The gate
  reads run states only; it is computed before any in-VM verdict is compared
  with an offline one.
- **Pass rule.** A checker family passes K2 when none of its compared K2 pairs
  has an `unexplained` difference. A family with no compared K2 pair is "not
  covered by K2" in the family tables (descriptive; the parent's label and
  consequence are unchanged).
- **Outcomes.**
  - `VERIFIED`: the gate passes and no K2 pair is `unexplained`. The K2 report
    is written; the parent's analysis replaces its label "offline harness, VM
    fidelity unverified" with "VM fidelity checked (K2)" and drops no family.
  - `FAMILIES_DROPPED`: the gate passes and some family has an `unexplained`
    pair. The K2 report is written and the parent's consequence applies
    verbatim (`analysis.headline` with `--k2-report`): each such family leaves
    the headline, P2-P5 and the checker candidates are recomputed without its
    mutants, and its own tables and the pooled rates that include it are
    reported as exploratory (`k2_exploratory`). If `compare_pptx_files` is
    dropped, the z-order false-negative result moves to `k2_exploratory` and
    the note says so.
  - `INCOMPLETE`: the gate fails. No K2 report is written for the analysis and
    the parent's label stays "offline harness, VM fidelity unverified". One
    repair attempt is allowed, only after a recorded decision that names the
    infrastructure cause from the run records, with a new executor commit and a
    refreshed code table under a new experiment id
    (`q2-evaluator-mutation-v1-k2-r1`, frozen before it runs); it reruns every
    slot, and both attempts are reported. A second `INCOMPLETE` ends K2 at an
    honest exit with the label kept.
- R03's kill line "K2 reproduces fewer than 50% of confirmed verdicts in the
  VM" is not adopted here: adopting R03 is Kevin's call (D73). Its input is
  reported (section 8).

## 7. The report step

After the job, on any machine, from the committed inputs and the job's run
directory (`k2-runs.jsonl`, `lane-receipt.json`):

```bash
python -m harness.q2_mutation_k2.report --run-dir K2_RUN_DIR \
  --sample program/evidence/2026-10-08/q2-mutation-confirm/results/released/k2/k2-sample.jsonl \
  --k2c program/evidence/2026-10-11/q2-mutation-k2/k2c-candidates-confirm.jsonl \
  --k2c-sha256 c7b1869049749c8311e73f3ba09ea98e53e45086d49922c6ccea72ab6bb8a028 \
  --verdicts program/evidence/2026-10-08/q2-mutation-confirm/results/released/confirm-mutants-v1/verdicts-lock.jsonl \
  --notes-summary program/evidence/2026-10-08/q2-mutation-confirm/results/released/confirm-mutants-v1/notes-summary.json \
  --out-dir OUT_DIR
```

It writes `k2-pairs.jsonl` and `k2-summary.json` always, and `k2-report.json`
(the parent's `--k2-report`: `executor_commit`, the VM image, `pairs`,
`disagreements` with `checker_family` and `explanation`, the excluded pairs,
the gate and the outcome) only for the `k2` job and only when the gate passes.
It refuses inputs other than the registered ones. The executor commit and the
VM image digest come from the lane receipt (`identity`: the exported tree's
`.git_sha` and harness digest, which the batch file checks at the job's start
and records in `preflight.txt`, and the manifest's VM pins). No in-VM verdict is
compared with an offline one during the job: the comparison exists only in this
report step, after the receipt is written (the parent's section 10). The parent's analysis is then rerun with `--k2-report` added to
whatever audit inputs exist at that time (section 9).

## 8. K2-C and reported-only quantities (descriptive)

- **K2-C.** Each of the 41 candidate events is run and classified by the same
  rules as a K2 pair, and reported beside that candidate in the note's
  candidate lists as "reproduced in the VM" (every scored run gives the offline
  verdict), "not reproduced" (with its explanation) or "excluded", with counts
  per family and per event type. K2-C is selected on the checker's verdict, so
  it is a reproduction check of the reported events, never a fidelity estimate;
  it changes no registered number, it is never passed to the analysis, and its
  results drop no family. If Kevin adopts R03's kill line, its input is K2-C's
  reproduction among the candidates his adjudication confirms; that join is the
  note's, outside this addendum's code.
- **Reported only.** Per set: agreement by family, by offline verdict and by
  save path; single-run pairs; exclusions by type; runs with a target unsaved at
  the checker's read; late writes; postconfig reply failures; metric errors;
  checker observations; the save-time reading (each postconfig-saved target's
  guest mtime minus the reply time of the postconfig's first `execute` step,
  mapped through the guest clock offset read at `pre_postconfig`; a task whose
  Ctrl+S command sleeps after the keystroke makes it negative, so it only
  bounds the save, and it decides nothing; cause (1) reads the checker's bytes)
  and the run times.

## 9. Interaction with the pending adjudication

Kevin's adjudication of the 34-item pool and his 25-item spot check (52
distinct items; D9, D35, D38) are pending (`results/README.md`, "Pending for
Kevin").

1. **K2 reads no audit or adjudication file.** The executor, the lane and the
   report read only the inputs of section 2 and the run records. The report
   refuses any input path that names an adjudication, audit summary, decision,
   adjudication pool, spot check, rater answer or calls file, or the audit
   sample, and no K2 module imports the audit, rater or packet code
   (`tests/test_q2_mutation_k2_report.py`). K2-C's membership is fixed by the
   offline outcomes and verdicts alone, so it is the same before and after the
   adjudication.
2. **Independent results.** K2's outcome and consequence depend only on
   checker verdicts (in the VM and offline); the adjudication changes audit
   readings, gold-defect flags and K3/K4, never a verdict. Neither changes the
   other's input.
3. **Blindness.** The K2 outputs (`k2-pairs.jsonl`, `k2-summary.json`,
   `k2-report.json`, the run records) and the K2-C list name checker verdicts
   per mutant and which mutants are candidate events, so they are unblinding
   in the same way as the files the results README tells Kevin not to read
   before he answers (`sample.jsonl`, `decisions.jsonl`, `analysis.json`,
   `summary.json`). Every K2 evidence directory's README opens with that
   warning, and the K2 outputs are committed only under
   `program/evidence/2026-10-11/q2-mutation-k2/` and the K2 run's own dated
   directory, never inside the audit's packet tree. Packets are not changed
   and carry nothing from K2.
4. **Order.** Neither waits for the other: freezing and running K2 need no
   adjudication answer, and adjudicating needs no K2 result. When both exist
   the parent's analysis is rerun once with `--k2-report` and
   `--adjudications`. If K2 lands first, the analysis is rerun with
   `--k2-report` and the audit as it stands, and again after the answers; if
   the answers land first, the reverse. Each rerun is committed with its
   inputs' digests.

## 10. Data, budget and safety

- Records: one JSON record per run attempt (`q2m-k2-run-v1`): identity, status,
  exclusion and type, verdict and score, the plan's digest and ops, save paths,
  the hash checkpoints (digests only), checker-read digests, unsaved-at-read
  paths, late writes, setup and postconfig replies without any stdout tail
  (S1a's `strip_stdout`; a postconfig can print a fixture's stored credentials),
  windows before the postconfig, timings and the guest-server identities.
  Records and summaries are committed; captures, container logs and mutant
  documents stay on the host (OSWorld document contents stay out of the
  repository, as the study's packets did).
- Budget: 242 runs of about 2 minutes each (job 1122: 111-118 s, with boot,
  setup, the 60 s and 20 s settles, injection, evaluation and capture), about
  8 VM-hours and 40 CPU-hours, about 1 hour of wall time at V = 8 (the 360
  minute limit leaves room for re-queues). Zero GPU-hours. No model runs and no
  model-generated code runs (D3, D7, D29 not engaged).

## 11. Development record (dev split only; exploratory, never evidence)

Development jobs inject items of the dev-split mutation run `dev-mutants-v9`
(its K2 sample, `program/evidence/2026-10-11/q2-mutation-k2/dev-inputs/k2-sample.jsonl`,
80 jobs on 17 tasks, and its 11 candidate events, `k2c-candidates-dev.jsonl`)
through the same lane, executor and report (purpose `development`; the lane
refuses any confirm task before the freeze). Records and reports:
`program/evidence/2026-10-11/q2-mutation-k2/`. All are CPU-only Slurm jobs
(no GRES), one host job at a time.

| Job | Executor | Items | Result |
|---|---|---|---|
| 1113 (`k2-dev-smoke-v1`) | `60ed1b0` | 6 pairs (a Calc postconfig save, two agent saves, a derived CSV, a text target without a save, a z-order FN candidate), V = 3 | Void, cancelled after 4 records. Defect: `kill_process` sent SIGTERM, which leaves the open document in LibreOffice's recovery list, so the reopened candidate came up behind a "Document Recovery" dialog; two runs were excluded at the pre-postconfig window check (cause (4)), as designed. One run was contaminated by a manual probe in its VM (the probe showed that LibreOffice's own Quit leaves no dialog on reopen). Fixed in `b5a5247` (section 3.2) |
| 1122 (`k2-dev-smoke-v2`) | `1448559` | the same 6 pairs, two runs each, V = 3 | 12 of 12 runs scored; 6 of 6 pairs agree with the offline verdict in both runs (5 K2 pairs, 1 K2-C z-order FN that fails in the VM as offline); LibreOffice quit cleanly in 0.2-0.4 s with no signal; runs 111-118 s; no target unsaved at the checker's read; save-latency estimates -0.02 to -0.01 s (clock-offset noise around a save that finished with the Ctrl+S call) |

| 1130 (`k2-dev-full-v1`) | `a06dc69` | the dress rehearsal at the registered job's shape: all 80 pairs of the dev K2 sample, then the 11 dev candidate events, two runs each, V = 8, 40 CPUs | 182 of 182 runs scored, none excluded or re-queued (gate: 0 of 80 excluded); 80 of 80 K2 pairs agree with the offline verdict in both runs (53 pass, 27 fail; 7 families: `compare_table` 32, `compare_pptx_files` 19, `compare_docx_files` 9, `compare_docx_tables` 7, `compare_docx_files_and_ignore_new_lines` 6, `compare_pptx_files_robust` 5, `compare_text_file` 2); 11 of 11 K2-C events reproduced in both runs (the 8 z-order false negatives fail in the VM, the 3 false positives pass); 156 postconfig saves, 22 agent saves, 4 targets without a save; no target unsaved at the checker's read; LibreOffice quit by Ctrl+Q with no signal in all 152 runs that had it open; runs 111-122 s (median 116 s); 45.5 minutes of wall time |

Development outcome: on the dev split the executor met the fitness gate with
no exclusion and found no in-VM/offline difference. This is exploratory and
says nothing about the confirm campaign's K2 result.

## 12. Readings of the parent's text

1. **The executor.** The parent names "the VM runtime of
   `stage0/q2-action-path` at the commit of its own frozen acceptance
   registration, running the injection plan of
   `harness/q2_mutation/vm_injection.py`". That runtime does not implement the
   plan's ops (`upload`, `open_file`, `agent_save`, `hash` with
   `expect_changed`; dossier O3). The executor is therefore that runtime's
   files unchanged (pinned by action-path v2's frozen tables and byte-identical
   on main), S1a's lane and OSWorld session code unchanged (pinned by S1a's
   section 20), and this addendum's injection code, pinned in section 2. The K2
   report records the exported tree's commit and digest and the VM image.
2. **One `evaluate()` call for the plan's last three ops** (section 3.4). A
   guest hash between the postconfig and the getters would delay the
   checker's read and hide the save timing that cause (1) is about.
3. **`expect_changed` is recorded, not failed.** A run whose checker read a
   postconfig-saved target before its save wrote is compared, because cause (1)
   exists to explain exactly those runs.
4. **"In-VM repeated evaluations"** (cause 2) are two independent runs in fresh
   VMs. A second `evaluate()` in the same VM would run the postconfig's save a
   second time on an already saved file, which the pipeline never does.
5. **Postconfig outputs are not uploaded** (section 3.3), mirroring the offline
   conversion rule.
6. **"Evaluate error" in cause (4)** is read as an `evaluate()` call that fails
   for the infrastructure (transport, an undelivered observation, an offline
   refusal, a timeout). A metric that raises is the verdict `error`, as offline,
   so a VM-only checker failure is compared, not excluded.
7. **Cause (1)'s evidence is the bytes the checker read**, not a clock: the
   parent names the cause by the postconfig's 0.5 s wait; the latency estimate
   is reported only.
8. **Additions that are stricter than the parent:** the fitness gate (section
   6) and the requirement that the K2 report come from the registered slots.
   **Additions that are descriptive:** K2-C and the reported-only quantities.
9. **The warm-up and the settles** (sections 3.1 and 3.4) are the certified
   lane's (action-path v2 design decision 31; S1a section 7.1).
10. **`kill_process`** ("`pkill` the process" in the plan) asks LibreOffice to
    quit before it signals it, and removes stale lock files: a signalled
    LibreOffice leaves recovery or lock state that puts a dialog in front of the
    reopened document (development job 1113, section 11).

## 13. Reported regardless of outcome

The gate (excluded pairs by cause), the outcome, the families dropped, every
K2 pair's reading (with its offline verdict, both runs' verdicts and its
explanation), agreement per family and per save path, single-run pairs, the
K2-C reading of each candidate, the reported-only quantities of section 8, the
executor commit, the source tree digest and the VM image, and any repair
attempt with the decision that allowed it.

## 14. Freeze checklist and what stays Kevin's

- A pre-freeze audit by an independent reviewer of this file and the code of
  section 2 (pending).
- The development record of section 11 complete, the code table refreshed, and
  `uv run pytest -q tests/test_q2_mutation_k2_*.py` passing.
- The freeze, by the program owner:
  `uv run python scripts/preregister.py freeze q2-evaluator-mutation-v1-k2 program/preregistrations/q2-evaluator-mutation-v1-k2.md`,
  then `verify`, and the ledger committed. The ledger row's
  `git_head_at_freeze` is the executor commit the `k2` job must run from.
- After the freeze: export that commit to the host, render the `k2` manifest
  from the registered slots (`lane render`, hashing every candidate file),
  submit it when no other host job runs, then the report step and the parent's
  analysis rerun.
- Kevin's own items are unchanged: the adjudication pool and the spot check
  (D9), the disclosure to xlang-ai (an outward action, D2), and whether R03 is
  adopted as a program question (D73).
