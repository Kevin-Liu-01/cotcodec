# q2-action-path-v2: validity controls C2, C1 and C3 (2026-10-08)

**Result: C2, C1 and C3 all pass.** None of the validity controls run in this
stage invalidates the suite for `q2-action-path-v2`. Each control was scored
once on frozen code, in the registered order (C2, then C1, then C3). Every
campaign counted at its first attempt, so nothing was rerun. Nothing was
repaired.

- **C2** (L0-raw failing set, a reproduction test in v2): L0-raw failed
  exactly the 8 predicted entries and passed the other 92.
- **C1** (detection): H-OSW-up and H-GA-buggy failed each of their 9
  known-defect cells in 5 of 5 repetitions.
- **C3** (mutation score): 42 of 44 scored mutants were killed. The other two,
  M12 and M13 on H-OSW-fixed, are the predicted equivalent ones and came out
  equivalent. Every scored, non-equivalent mutant was killed.

C4 is read from A1's trials. A1-A7, the concurrency ladder and A5's
boot-reset campaign are outside this stage, and none of them ran. A pass of
the controls says the suite can be used. It does not say the action path
passes.

The registrations are `q2-action-path-v2`, `-inputs` and `-executor` (ledger
rows 13-15, frozen 2026-10-08 14:23:48-49 UTC). Every campaign ran from a
read-only `git archive` export of `bf99a64`, the commit that records row 15,
with tree digest `abbbfe6c...`. Raw outputs stay on the host under
`~/cotcodec-runs/q2-action-path-v2/runs/` (202 MB, 50 run directories).
`runs/<job>/raw-sha256sums.txt` lists the SHA-256 of every file there.

## C2: PASS (v2's C2 is a reproduction test, not an a-priori one)

| Item | Value |
|---|---|
| Campaign | `q2ap-v2-c2-l0raw-a1`: L0-raw, all 100 entries, 5 repetitions, the **seed-45** shuffle (C2's own order seed, decision D40), screenshot setting, N = 1, attempt 1 |
| Job | 864, CPU only (`TRES=cpu=6,mem=12G,node=1`; no GRES), 14:30:34 to 14:40:46 UTC, run time 10 min 12 s |
| End state | Slurm `COMPLETED` `0:0` (watcher record `slurm-state/864.txt`) and batch record `driver_exit=0 labelled_containers_left=0`; they agree |
| Counts | yes: `counting_problems` is empty, `infra_gates_pass` is true, `System.qcow2` is unchanged, no labelled container or volume was left, no file is unreadable |
| Sessions and trials | 9 cold boots (boot 16.9-17.4 s), 500 trials in the realized seed-45 order (`acceptance.c2` checks it against `order.plan(..., 45, criterion="C2")`); 454 PASS under section 5 |
| Infrastructure | no infrastructure failure, no observation retry, every reset observation delivered, no guest-server restart (the screenshot setting makes no accessibility call) |
| Verdict | frozen `acceptance.c2` (`ae5470e5...`): `pass: true`, no problems |

v2's C2 tests whether the L0-raw failing set reproduces on a new order seed.
It is **not** an a-priori prediction test. The predicted pass of
`chord_super_d` is informed by v1's C2 (job 768), by decision D43's judge
rule (as D45 narrows it) and by seed-42 development (decisions D40 and D43;
registration sections 8, 25-27). The a-priori result is v1's: one
unpredicted failure, `chord_super_d`.

The prediction table (section 12) gives v2's result under C2's rule and under
section 5 as written. v1's a-priori result (job 768, judged by v1's rules) is
beside it. The other 85 entries passed 5 of 5 under both readings in both
runs (`acceptance/c2-prediction-table.json`).

| Entry | Predicted (v2 file) | v2 C2 rule | v2 section 5 | v2 section-5 PASS | v1 C2 rule (a priori) | v1 section 5 | v2 failure reasons |
|---|---|---|---|---:|---|---|---|
| `type_unicode_bmp` | FAIL | FAIL | FAIL | 0/5 | FAIL | FAIL | text (non-ASCII skipped) |
| `type_emoji` | FAIL | FAIL | FAIL | 0/5 | FAIL | FAIL | text |
| `type_rtl` | FAIL | FAIL | FAIL | 0/5 | FAIL | FAIL | text (marker also stale in some) |
| `type_combining` | FAIL | FAIL | FAIL | 0/5 | FAIL | FAIL | text |
| `type_emoji_zwj` | FAIL | FAIL | FAIL | 0/5 | FAIL | FAIL | text |
| `key_kp_enter` | FAIL | FAIL | FAIL | 0/5 | FAIL | FAIL | R-dev projection (no event) |
| `click_button_back` | FAIL | FAIL | FAIL | 0/5 | FAIL | FAIL | PyAutoGUI raised on integer button 8; no event |
| `click_button_forward` | FAIL | FAIL | FAIL | 0/5 | FAIL | FAIL | PyAutoGUI raised on integer button 9; no event |
| **`chord_super_d`** | PASS (informed by v1's C2) | PASS | PASS | 5/5 | **FAIL** | FAIL | none |
| `chord_alt_f4` | PASS | PASS | PASS | 5/5 | PASS | FAIL | none |
| `chord_alt_tab` | PASS | PASS | PASS | 5/5 | PASS | FAIL | none |
| `chord_ctrl_alt_shift_r` | PASS | PASS | PASS | 5/5 | PASS | FAIL | none |
| `seq_type_chord_type` | PASS | PASS | FLAKY | 2/5 | PASS | FLAKY | stale marker only (reported, not judged under C2) |
| `type_shell_hostile` | PASS | PASS | FLAKY | 3/5 | PASS | FLAKY | stale marker only |
| `type_symbols_shifted` | PASS | PASS | FLAKY | 4/5 | PASS | FLAKY | stale marker only |

Under D45's rule the four shell-grabbed chords now pass section 5 as well.
In v1 their key events queued during the shell's grab were judged on the
state the tap could not observe: the releases, and `chord_super_d`'s `d`
press as well.

**Section 12, events read without their state** (`acceptance/c2-section12-state-not-observed.json`,
`acceptance.state_not_observed_report`):

- 20 trials, 53 key events, all in the four shell-grabbed chords, and all
  20 trials PASS. Each event follows, 0-2 ms later (server time), a key press
  in its window that the tap recorded with Mod2. That press is the chord's
  grab key in every trial (Super_L, F4, Tab or r). Every event is one the
  trial's verdict read without its state (`in_verdict` true).
- By entry:
  - `chord_super_d`: 5 trials, the `d` press, `d` release and Super_L
    release in each.
  - `chord_alt_tab`: 5 trials, the Tab and Alt_L releases.
  - `chord_ctrl_alt_shift_r`: 5 trials, all four releases.
  - `chord_alt_f4`: 5 trials. The F4 release is in all 5, and the Alt_L
    release in 3.
- No trial has a key event recorded without Mod2 that no processed press
  preceded (`no_processed_press_before` is empty).
- `chord_super_d` was trial 11, 34, 50, 22 and 38 (zero-based) of sessions
  1, 2, 3, 6 and 8, never a session's first trial. Every session ran the
  keyboard warm-up.

## C1: PASS

| Campaign | Job | Run time | Trials | PASS | Known-defect cells, each 0 of 5 |
|---|---:|---|---:|---:|---|
| `q2ap-v2-c1-hoswup-a1` (H-OSW-up, judged against Table 21) | 866 | 3 min 22 s | 70 | 40 | R08 (triple click), R09 (scroll at a coordinate), R10 (hscroll), R11 (terminate failure) |
| `q2ap-v2-c1-hgabuggy-a1` (H-GA-buggy) | 868 | 3 min 7 s | 70 | 20 | R01 (middle click gives no action), R02 (Ctrl released before the click), R05, R06, R07 (only the first call runs) |

Both runs used the 14 R cases in the seed-42 shuffle, 5 repetitions,
screenshot setting, N = 1, attempt 1, with the control translators frozen in
the inputs addendum. Both counted: COMPLETED 0:0 by the watcher and the
batch record, gates passed, `System.qcow2` unchanged, nothing left, no
infrastructure failure, retry or restart. Boots took 17.3-17.9 s. Frozen
`acceptance.c1` gives `pass: true` with no problems.

C1 judges only the known-defect cells. The other cells, reported and not
judged, gave:

- H-OSW-up also fails R03 and R13:
  - R03 is outside both harnesses' specs, and no Ctrl was pressed;
  - in R13 none of the three keys reached X.
- H-GA-buggy also fails:
  - R03: no Ctrl was pressed;
  - R04: each modifier was pressed and released before its click;
  - R09: the wheel turned the other way (button 4) at (1344, 324);
  - R10: a vertical notch (button 4), not button 6;
  - R14: the corner click landed on (1918, 1078), not (1919, 1079).
- H-GA-buggy passes R08, R11, R12 and R13. H-OSW-up passes R01, R02, R04-R07,
  R12 and R14.

Section 12: no key event was read without its state, and none lacked Mod2
without a preceding processed press (`acceptance/c1-section12-state-not-observed.json`).

## C3: PASS

C3 ran 47 campaigns at the executor freeze: the unmutated reference run of
each scored layer, plus one run per scored (operator, layer) pair. All were
in the seed-42 order, 1 repetition per cell, screenshot setting, N = 1,
attempt 1. That makes 4,617 trials in 94 cold boots (boot 17.3-19.1 s; step
p95 at most 1.45 s per campaign).

Every campaign counted: COMPLETED 0:0 by the watcher and the batch record,
gates passed, `System.qcow2` unchanged, nothing left. No trial in any of the
47 campaigns had an infrastructure failure, an observation retry or a
guest-server restart. No campaign has an earlier attempt, so equivalence is
read from the counting attempts alone. Frozen `acceptance.c3` gives
`pass: true` with no problems.

**The reference runs.**

| Reference | Job | Trials | PASS | Cells not PASS (all outside that harness's spec, as in development jobs 852 and 853) |
|---|---:|---:|---:|---|
| L0-fixed | 874 | 100 | 100 | none |
| H-OSW-fixed | 872 | 99 | 97 | R03, R09 |
| H-GA | 870 | 93 | 89 | R02, R04, R06, R10 |

An outside-spec cell cannot kill (section 8). So no mutant had a killing
cell with an infrastructure failure, and none had one the reference failed
to pass cleanly: `infra_cells` and `reference_not_clean` are empty for
every mutant.

**Outcomes:**

- L0-fixed: 23 of 23 killed.
- H-OSW-fixed: 10 killed and 2 equivalent (M12 and M13, the comment-only
  patches predicted equivalent as negative controls of the equivalence
  rule).
- H-GA: 9 of 9 killed.

Section 12 asks for the observed killers next to the predicted ones, in the
table below. Three predicted killers did not kill. These are the same three
that development jobs 553-602 found:

- `scroll_ctrl_down_3` for M01 on H-OSW-fixed;
- `mixed_gesture_state` for M21;
- `seq_long_mixed` for M26.

Each of those mutants was killed by other cells. Many mutants were also
killed by cells nobody predicted; `acceptance/c3-verdict.json` lists every
killer.

| Mutant | Layer | Job | Outcome | Clean kills | Predicted killers | Predicted, did not kill |
|---|---|---:|---|---:|---|---|
| `M01-modifier-released-early` | H-OSW-fixed | 878 | killed | 6 | `R02`, `R04`, `click_ctrl_left`, `scroll_ctrl_down_3` | `scroll_ctrl_down_3` |
| `M01-modifier-released-early` | L0-fixed | 876 | killed | 9 | `click_ctrl_left`, `click_shift_left`, `click_alt_left`, `click_ctrl_shift_right`, `scroll_ctrl_down_3`, `scroll_shift_down_3` | - |
| `M02-button-swap-left-right` | L0-fixed | 880 | killed | 29 | `click_left_center`, `click_right`, `drag_short` | - |
| `M03-middle-click-noop` | H-GA | 886 | killed | 2 | `R01`, `click_middle` | - |
| `M03-middle-click-noop` | H-OSW-fixed | 884 | killed | 2 | `R01`, `click_middle` | - |
| `M03-middle-click-noop` | L0-fixed | 882 | killed | 1 | `click_middle` | - |
| `M04-coordinate-shift-5px` | L0-fixed | 888 | killed | 45 | `click_left_center`, `move_only`, `drag_short` | - |
| `M05-scroll-sign-flip` | H-GA | 894 | killed | 8 | `scroll_down_1`, `scroll_up_3`, `R05` | - |
| `M05-scroll-sign-flip` | H-OSW-fixed | 892 | killed | 12 | `scroll_down_1`, `scroll_up_3`, `R05` | - |
| `M05-scroll-sign-flip` | L0-fixed | 890 | killed | 11 | `scroll_down_1`, `scroll_up_3` | - |
| `M06-scroll-ticks-doubled` | L0-fixed | 896 | killed | 13 | `scroll_down_1`, `scroll_down_3` | - |
| `M07-text-drop-last-char` | L0-fixed | 898 | killed | 20 | `type_single_char`, `type_plain` | - |
| `M08-text-nfc-normalize` | L0-fixed | 900 | killed | 1 | `type_combining` | - |
| `M09-text-drop-non-ascii` | L0-fixed | 902 | killed | 5 | `type_unicode_bmp`, `type_emoji`, `type_rtl`, `type_combining`, `type_emoji_zwj` | - |
| `M10-less-to-greater` | L0-fixed | 904 | killed | 3 | `type_symbols_shifted`, `type_shell_hostile`, `type_long_500` | - |
| `M11-unknown-key-dropped` | H-GA | 910 | killed | 6 | `R13`, `key_kp_enter`, `key_menu` | - |
| `M11-unknown-key-dropped` | H-OSW-fixed | 908 | killed | 6 | `R13`, `key_kp_enter`, `key_menu` | - |
| `M11-unknown-key-dropped` | L0-fixed | 906 | killed | 5 | `key_kp_enter`, `key_kp_add`, `key_menu`, `caps_lock_roundtrip`, `chord_super_d` | - |
| `M12-triple-to-double` | H-GA | 916 | killed | 2 | `R08`, `click_triple_left` | - |
| `M12-triple-to-double` | H-OSW-fixed | 914 | equivalent | 0 | none (predicted equivalent) | - |
| `M12-triple-to-double` | L0-fixed | 912 | killed | 1 | `click_triple_left` | - |
| `M13-hscroll-to-vscroll` | H-OSW-fixed | 920 | equivalent | 0 | none (predicted equivalent) | - |
| `M13-hscroll-to-vscroll` | L0-fixed | 918 | killed | 3 | `scroll_left_3`, `scroll_right_3`, `scroll_diagonal` | - |
| `M14-chord-release-order` | L0-fixed | 922 | killed | 12 | `chord_ctrl_c`, `chord_ctrl_shift_t`, `chord_ctrl_alt_shift_r` | - |
| `M15-duplicate-click` | L0-fixed | 924 | killed | 18 | `click_left_center`, `click_burst_5` | - |
| `M16-double-click-interval-600ms` | L0-fixed | 926 | killed | 2 | `click_double_left`, `click_triple_left` | - |
| `M17-drag-teleport` | L0-fixed | 928 | killed | 12 | `drag_short`, `drag_long_diagonal`, `drag_vertical` | - |
| `M18-first-tool-call-only` | H-GA | 932 | killed | 2 | `R05`, `R07` | - |
| `M18-first-tool-call-only` | H-OSW-fixed | 930 | killed | 3 | `R05`, `R06`, `R07` | - |
| `M19-last-tool-call-only` | H-GA | 936 | killed | 2 | `R05`, `R07` | - |
| `M19-last-tool-call-only` | H-OSW-fixed | 934 | killed | 3 | `R05`, `R07` | - |
| `M20-terminate-failure-to-done` | H-GA | 940 | killed | 1 | `R11` | - |
| `M20-terminate-failure-to-done` | H-OSW-fixed | 938 | killed | 1 | `R11` | - |
| `M21-hold-not-released` | L0-fixed | 942 | killed | 9 | `click_ctrl_left`, `scroll_ctrl_down_3`, `mixed_gesture_state` | `mixed_gesture_state` |
| `M22-keypad-to-main` | H-GA | 948 | killed | 3 | `key_kp_enter`, `key_kp_add`, `R13` | - |
| `M22-keypad-to-main` | H-OSW-fixed | 946 | killed | 3 | `key_kp_enter`, `key_kp_add`, `R13` | - |
| `M22-keypad-to-main` | L0-fixed | 944 | killed | 2 | `key_kp_enter`, `key_kp_add` | - |
| `M23-caps-lock-dropped` | L0-fixed | 950 | killed | 1 | `caps_lock_roundtrip` | - |
| `M24-grid-1000-instead-of-999` | H-GA | 954 | killed | 7 | `R14` | - |
| `M24-grid-1000-instead-of-999` | H-OSW-fixed | 952 | killed | 8 | `R14` | - |
| `M25-shell-expansion` | L0-fixed | 956 | killed | 18 | `type_shell_hostile` | - |
| `M26-newline-dropped` | L0-fixed | 958 | killed | 1 | `type_multiline_tabs`, `seq_long_mixed` | `seq_long_mixed` |
| `M27-extra-buttons-dropped` | L0-fixed | 960 | killed | 2 | `click_button_back`, `click_button_forward` | - |
| `M28-modifier-text-ignored` | H-OSW-fixed | 962 | killed | 6 | `R02`, `R04`, `click_ctrl_left` | - |

The kit scores the 44 pairs above. `mutation_operators.yaml` gives the
reasons for every pair it does not score: for example, M01 on H-GA is
excluded (it can change only outside-spec cells), and M13 and M28 on H-GA
are not applicable (no code path). Pairs that are not scored were not run.

**C3 repeated development's conditions** (section 8): the same seed-42 order
and setting, frozen code and kit, and mutants that development (jobs
553-602 at `b603347`) had already seen killed, with M12 and M13 on
H-OSW-fixed equivalent. Its outcome was largely known in advance. It is
reported as a check that the frozen code and kit still detect every
mutant, not as an independent estimate of the suite's sensitivity.

Section 12: across the 4,617 C3 trials no key event was read without its
state, and none lacked Mod2 without a preceding processed press
(`acceptance/c3-section12-state-not-observed.json`). So no slow shell answer
touched the equivalence comparison of M12 or M13.

## How it was run

1. **Export.** `git archive bf99a64` was extracted to
   `~/cotcodec-runs/q2-action-path-v2/src/bf99a645.../` on the host and made
   read-only (never `~/cotcodec`). Its tree digest is `abbbfe6c...`, the
   same locally, on the host, in every manifest, in every batch record and
   in every receipt. `checks/export-and-reproduction.json` records these
   checks on a local export of the same commit:
   - `preregister.py check-chain` passes (15 rows);
   - `verify` passes for all three ids;
   - `tests/test_q2_prereg_inputs.py` and
     `tests/test_q2_acceptance_admission.py` pass (51 tests), so every
     pinned file holds its frozen digest.
2. **Manifests.** The frozen renderer, run from the export with
   `--host-root ~/cotcodec-runs/q2-action-path-v2` (decision D40), wrote all
   50 manifests: C2, the two C1 runs, the three C3 references and the 44
   mutants (`ops/render_controls.sh`). Each was validated against the
   ledger. No field was edited after rendering, and the submitted manifests
   are the rendered ones. The same renderer, run locally from the local
   export with the same arguments, wrote 50 byte-identical files
   (`checks/local-render-sha256sums.txt` against
   `manifests/rendered-sha256sums.txt`).
3. **Submission.** `ops/submit.sh`, run from the export, did the following
   for each manifest:
   - `scripts/submit_vm_campaign.py --dry-run`, using the batch script
     `3d86820d...` (the frozen digest) with both images present
     (`ops/dryrun/`);
   - `--test-only`;
   - the submission;
   - right after the submission, `scripts/record_slurm_end_states.sh RUN_ROOT/slurm-state JOB`,
     detached with a 24 h limit. It caught every end state (`slurm-state/`).

   Order and concurrency were as follows:
   - C2 (job 864) ran alone.
   - C1 was submitted after C2's verdict. Its two campaigns ran at the same
     time (jobs 866 and 868).
   - C3 was submitted after C1's verdict, with at most six jobs pending or
     running at once (jobs 870-962, even numbers; `ops/submit-c3.log`). The
     three reference runs were submitted first.
   - Every manifest declares N = 1, the registered concurrency of every
     campaign but the ladder, A4 and A7. A Slurm job runs one VM.
   - The receipts show at most six jobs running at once.
4. **Analysis.** `ops/make_attempts.py` built the attempt map of each
   control from the submission log (`ops/attempts-c*.json`). Every campaign
   has one attempt. `ops/analyze_controls.py`, run from the export, loaded
   each run directory with `acceptance.load` and called `acceptance.c2`,
   `c1` or `c3`. It wrote, per control, three files to `acceptance/`:
   - the verdict;
   - the section-12 report the verdict carries (written again on its own);
   - a per-campaign summary: end state, counting problems, every failed
     trial with its reasons, retries, boots, steps and restarts.

   The script only groups run directories and writes JSON. Every judgement
   is the frozen code's.
5. **Reproduction and run checks.**
   - A second run on the host gave identical outputs.
   - The raw run directories were copied to a local scratch directory, and
     each file's SHA-256 equals its `raw-sha256sums.txt` entry. The local
     export under Python 3.13 then gave all nine JSON files byte-identical
     to the host's (Python 3.10).
   - `ops/check_runs.py` (`checks/run-checks.json`) checked each of the 50
     jobs:
     - its `manifest.json` equals the rendered manifest, and its canonical
       digest is the batch record's;
     - the batch script, tree digest, git SHA, receipt, campaign, manifest
       and session-plan digests agree;
     - each job started after row 15 was frozen;
     - the receipt reports no GPU, and so does the Slurm TRES;
     - `System.qcow2` is unchanged and nothing was left;
     - Slurm and the batch record both say COMPLETED 0:0;
     - N = 1, attempt 1, the registered seed and the screenshot setting.

     Every check passed for every job.

## Operator notes

These are disclosed operator choices. None changed what a registration
fixes.

- **Export commit.** The export is `bf99a64`, the commit that records the
  executor row, rather than main's head. Main at `e6f5bf1` and `6b6251c`
  differs from it only outside `harness/`, `scripts/`, `infra/`,
  `experiments/` and `program/preregistrations/`. The pins check above is
  what binds the run to the frozen code (design decision 35).
- **Concurrent N = 1 jobs.** C1's two campaigns, and up to six C3
  campaigns, ran as separate N = 1 jobs at the same time. Development ran
  the mutant runs the same way, in waves of six concurrent jobs (receipts
  of jobs 553-602). No registration orders the campaigns of one control
  serially. No trial had an infrastructure failure, and the step p95 stayed
  at or below 1.45 s.
- **The C2 manifest pins the executor addendum too.** The frozen renderer
  pins every addendum the ledger holds. C2 needs only the inputs addendum,
  and `check_ledger` checks only what each campaign needs (executor
  addendum, section 7).
- **`scripts/preregister.py` on the host.** It needs Python 3.11
  (`datetime.UTC`) and cannot run under the host's Python 3.10, so the
  ledger was checked locally. On the host, `manifest.check_ledger` (hash
  chain, registration digests, every frozen-table file, closed world) passed
  in the renderer, the submitter and every job.
- **Test-only job ids.** Each `sbatch --test-only` takes a job id. That is
  why the submitted jobs carry even numbers only (864, 866, ...). No job with
  an odd id was created.
- **No relocation.** v1's operator step of moving two manifest fields
  (v1 evidence README) was not needed, because the renderer took the host
  root as a parameter.

## VM time

The 50 jobs used 2.95 VM-hours, CPU only (run time times one VM): C2 0.17,
C1 0.11, C3 2.68. They were sized at 0.25, 0.12 and 2.8. Wall-clock time
ran from 14:30:34 to 15:14:35 UTC. No GPU was requested or used.

## Files

| Path | What it is |
|---|---|
| `manifests/rendered/` | the 50 manifests as the frozen renderer wrote them and as submitted; `rendered-sha256sums.txt` |
| `runs/<job>/` | `manifest.json`, `preflight.txt` (batch record), `receipt.json`, `session_plan.json`, `slurm-<job>.out`, `raw-sha256sums.txt` (every raw file left on the host) |
| `slurm-state/<job>.txt` | the watcher's `scontrol show job` record of each job |
| `acceptance/c{1,2,3}-verdict.json` | the frozen `acceptance.c1`/`c2`/`c3` output, with its section-12 report under `state_not_observed` |
| `acceptance/c{1,2,3}-section12-state-not-observed.json` | the same section-12 report on its own (`acceptance.state_not_observed_report`) |
| `acceptance/c{1,2,3}-campaigns.json` | per-campaign summaries |
| `acceptance/c2-prediction-table.json` | `ops/c2_prediction_table.py`: the L0-raw prediction table against v2's C2 under both readings, with v1's a-priori result beside it |
| `checks/` | the export, rendering and reproduction checks, and `run-checks.json` (`ops/check_runs.py`) |
| `ops/` | the operator scripts (render, submit, attempt map, analysis, evidence collection, run checks, prediction table), the submission logs, the attempt maps, the C3 pair list and order, and each manifest's dry-run and test-only output |

The shell scripts and `make_attempts.py` that ran on the host are the
committed ones (same SHA-256 on both sides). `analyze_controls.py` was
changed after the run by one edit for ruff's line length (a message string
moved into a variable). The committed copy was then run again on the host
and locally, and it wrote byte-identical outputs to the copy that ran first.
`c2_prediction_table.py` and `check_runs.py` ran locally on the collected
bundle. After their own ruff fixes they were run again, with the same
results.
