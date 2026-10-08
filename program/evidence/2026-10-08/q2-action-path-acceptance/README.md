# q2-action-path-v1: validity controls (2026-10-08)

**Result: C2 fails, so the suite is invalid for `q2-action-path-v1`.** C2
was the first validity control scored. L0-raw failed every predicted entry
and one more, `chord_super_d`, in 5 of 5 repetitions. Under section 8 any
deviation from the frozen prediction invalidates the suite for v1. Under
section 11 a failed validity control is not repaired within v1, and a
corrected suite is a new preregistration. C1 and C3 were therefore not run.
No acceptance campaign (A1-A7 or the ladder) ran either.

The registrations are `q2-action-path-v1`, `-inputs` and `-executor`
(ledger rows 8-10, frozen 2026-10-08 07:28 UTC). The campaign ran from a
`git archive` export of `a9948ee`, the commit that records the three rows.
Raw outputs stay on the host under
`~/cotcodec-runs/q2-action-path-v1/runs/768/`; `runs/768/raw-sha256sums.txt`
lists the SHA-256 of every file there.

## C2 (L0-raw prediction): FAIL

| Item | Value |
|---|---|
| Campaign | `q2ap-v1-c2-l0raw-a1`: L0-raw, all 100 entries, 5 repetitions, seed-42 shuffle, screenshot setting, N = 1, attempt 1 |
| Job | 768, CPU-only (`TRES=cpu=6,mem=12G,node=1`; no GRES), 07:33:45 to 07:43:56 UTC, run time 10 min 11 s |
| End state | Slurm `COMPLETED` `0:0` (watcher record `slurm-state/768.txt`) and batch record `driver_exit=0 labelled_containers_left=0`; they agree |
| Counts | yes: `counting_problems` is empty, `infra_gates_pass` is true, `System.qcow2` is unchanged (SHA-256 `6bf667a8...` before and after), no labelled container or volume was left, no file is unreadable |
| Sessions and trials | 9 cold boots (boot p50 17.2 s, max 17.9 s), 500 trials in the realized seed-42 order; 435 PASS under section 5 |
| Infrastructure | no infrastructure failure, no observation retry, every reset observation delivered, no guest-server restart (the screenshot setting makes no accessibility call) |
| Verdict | `acceptance.c2` (frozen `acceptance.py`, SHA-256 `39c59210...`): `pass: false`, "L0-raw failing set deviates: unpredicted failures ['chord_super_d'], predicted but passing []" |
| Rerun | none. The campaign counted, and section 6.1 never reruns a campaign that counted |

The prediction table, observed under C2's rule (section 8, design decision
34) and under section 5 as written. Each entry ran 5 repetitions; the other
85 entries passed 5 of 5 under both readings.

| Entry | Predicted | C2 rule | Section 5 | Section 5 PASS | Failure reasons |
|---|---|---|---|---:|---|
| `type_unicode_bmp` | FAIL | FAIL | FAIL | 0/5 | text |
| `type_emoji` | FAIL | FAIL | FAIL | 0/5 | text |
| `type_rtl` | FAIL | FAIL | FAIL | 0/5 | text (marker also stale in 3) |
| `type_combining` | FAIL | FAIL | FAIL | 0/5 | text |
| `type_emoji_zwj` | FAIL | FAIL | FAIL | 0/5 | text |
| `key_kp_enter` | FAIL | FAIL | FAIL | 0/5 | R-dev projection |
| `click_button_back` | FAIL | FAIL | FAIL | 0/5 | PyAutoGUI raised on integer button 8; no event |
| `click_button_forward` | FAIL | FAIL | FAIL | 0/5 | PyAutoGUI raised on integer button 9; no event |
| **`chord_super_d`** | **PASS** | **FAIL** | FAIL | 0/5 | R-dev projection: the `d` press arrives without Mod4 |
| `chord_alt_f4` | PASS | PASS | FAIL | 0/5 | key-release modifier state only (excused by C2's rule) |
| `chord_alt_tab` | PASS | PASS | FAIL | 0/5 | key-release modifier state only (excused) |
| `chord_ctrl_alt_shift_r` | PASS | PASS | FAIL | 0/5 | key-release modifier state only (excused) |
| `seq_type_chord_type` | PASS | PASS | FLAKY | 3/5 | stale marker only (reported, not judged) |
| `type_shell_hostile` | PASS | PASS | FLAKY | 3/5 | stale marker only |
| `type_symbols_shifted` | PASS | PASS | FLAKY | 4/5 | stale marker only |

What the failure is (reported, as section 8 requires; it does not change
v1's verdict). `chord_super_d` is a `raw-only` entry judged on the XRecord
stream. L0-raw sends it as `pyautogui.hotkey('winleft', 'd')`. The
prediction file states only that "'winleft' maps to Super_L (keycode 133)".
That part held: in all 5 trials the tap saw the right four key events
(Super_L press, `d` press, `d` release, Super_L release). The modifier state
differed. The Super_L press carried state 16 (Mod2, the NumLock baseline),
but the `d` press, within 1 ms by server time, carried state 0, without
Mod4 and without Mod2. The R-dev reference has the `d` press with Mod4.
C2's rule leaves out the modifier state of key releases only; a press keeps
it. So this is a counted failure in every repetition. Each of the nine
sessions ran the guard's keyboard warm-up (keycode 230, the shell then
reporting idle) before its first trial (`start.warmup` in every cycle
record). `chord_super_d` was at zero-based position 15, 20, 7, 45 and 33 of its
sessions, never a session's first trial. No further investigation was run.
A corrected prediction, or a C2 rule that also covers press timing, can
only enter a new preregistration (section 8).

## Not run

- **C1 and C3.** Their 49 manifests (2 C1, 3 C3 reference runs and the 44
  scored mutants) were rendered on the host by `ops/render_controls.sh`
  while C2 ran. None was submitted. They stay on the host under
  `~/cotcodec-runs/q2-action-path-v1/manifests/` and are not part of this
  evidence.
- **A1-A7 and the ladder** are outside this stage, and the suite is now
  invalid for v1 in any case.

## How it was run

1. `git archive a9948ee` was extracted to
   `~/cotcodec-runs/q2-action-path-v1/src/a9948ee.../` on the host and made
   read-only. Its tree digest is `dec80447...`, the same in the manifest,
   the submitter check and the job's own check.
2. The frozen renderer, run from that export
   (`scripts/render_q2_action_path_manifest.py C2 --seed 42`), wrote
   `manifests/rendered/c2-l0raw-seed42-a1.yaml`. It validated the manifest
   against the ledger.
3. Operator step (see the deviation below): `ops/relocate_manifest.py`
   rewrote `source.host_dir` and `run_root` from the renderer's built-in
   development root (`~/cotcodec-runs/stage0/q2-action-path`) to the v1 root
   (`~/cotcodec-runs/q2-action-path-v1/{src/<sha>,runs}`). It checked that no
   other field changed and validated the result again with the export's
   `validate_manifest` and ledger check. The output is
   `manifests/submitted/c2-l0raw-seed42-a1.yaml`. `diff` of the two files
   shows only those two lines and the added header comment.
4. From the export, `scripts/submit_vm_campaign.py` ran `--dry-run` (batch
   script SHA-256 `3d86820d...`, the frozen digest; both images present),
   then `--test-only`, then the submission (job 768). Right after it,
   `scripts/record_slurm_end_states.sh runs/slurm-state 768` was started on
   the host. It recorded `COMPLETED 0:0` and exited.
5. `ops/analyze_controls.py`, run from the export, loaded the run directory
   with `acceptance.load` and called `acceptance.c2`. It wrote
   `acceptance/c2-verdict.json` (the verdict, every entry under C2's rule and
   under section 5) and `acceptance/c2-campaigns.json` (end state, counting
   problems, every failed trial with its reasons, retries, boots, steps,
   restarts). The script only groups run directories and writes JSON; every
   judgement is the frozen code's.

## Deviation from the operator brief

The brief asks for experiments to run from exports under
`~/cotcodec-runs/q2-action-path-v1/`. The frozen renderer hard-codes the
development host root in `source.host_dir` and `run_root`, so step 3 moved
exactly those two fields. No registration fixes host paths. The edited
manifest passed the same admission check (ledger rows, registration
digests, every frozen-table file in the export, no unpinned file under
`harness/q2/`) in the relocation script, in the submitter and inside the
job. Both the verbatim rendering and the submitted manifest are kept here.
The rendered C2 manifest also pins the executor addendum, because the
renderer pins every addendum the ledger holds. C2 itself needs only the
inputs addendum, and `check_ledger` checks only what each campaign needs.

## Files

| Path | What it is |
|---|---|
| `manifests/rendered/`, `manifests/submitted/` | The C2 manifest as the frozen renderer wrote it, and as submitted |
| `runs/768/` | `manifest.json`, `preflight.txt` (batch record), `receipt.json` (SHA-256 `6c939522...`), `session_plan.json`, `slurm-768.out`, `raw-sha256sums.txt` (49 files on the host) |
| `slurm-state/768.txt` | The watcher's `scontrol show job` record |
| `acceptance/c2-verdict.json`, `acceptance/c2-campaigns.json` | `acceptance.c2`'s output and the campaign summary |
| `ops/` | Attempt map, submission log and the operator scripts (relocation, analysis, evidence collection, and the C1/C3 renderer that was never followed by a submission). The two Python scripts were reformatted for ruff after the run. Both formatted copies were re-run on the host and wrote byte-identical outputs (the submitted manifest and both JSON files) |

VM time: one job, 10 min 11 s at N = 1 (0.17 VM-hours, against C2's
sized 0.25). No GPU was requested or used.
