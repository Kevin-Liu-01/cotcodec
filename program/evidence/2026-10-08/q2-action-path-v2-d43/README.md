# q2-action-path-v2: decision D43, the judge rule and its development (2026-10-08)

**Development evidence only (seed 42, never evidence for any criterion).**
Decision D43 has v2's judge treat the modifier state of a key event the
XRecord tap recorded without the lock bit the entry guard guarantees as
unobservable, and judge that event on kind, keycode, keysym and order only.
`q2-action-path-v2.md` section 27 reports this bundle; sections 4.4, 5, 6.2,
8 and 24-26 and design decisions 47 and 48 state the rule.

## Result

1. **The guaranteed bit is Mod2 (Num Lock).** A read-only scan of every run
   directory of the action-path lane (v1's development runs, v1's C2 job 768
   and v2's jobs 784-787; 424 sessions) found the Num Lock LED on, Num_Lock on
   Mod2 and Mod2 in the modifier state at every session's start, and Mod2 in
   every one of 36,251 guard checks with no key pressed. The guard checked the
   LED only; it now also requires Mod2 (condition f).
2. **Only queued events lack it.** Of 519,344 tap key events, 172 lacked
   Mod2: every one after the press that activates GNOME Shell's grab on one
   of the four shell-grabbed chords, every one with state 0. None of 517,032
   probe key events and none of 1,550 QEMU-monitor key events lacked it.
3. **v1's C2 failure passes under the rule.** Re-judged through the campaign's
   own `suite.observation`, the 15 L0-raw `chord_super_d` trials of jobs 768
   and 784 pass (the `d` press, the `d` release and the Super_L release read
   without their state), the three other shell chords pass too, the nine
   ungrabbed chords and every L0-fixed chord verdict of jobs 785-787 are
   unchanged, and the pre-warm-up failures of runs 549 and 574 and run 486's
   (no key hold) pass. The M11 run 572 (Super_L dropped) still fails.
4. **Development at `126ff8b`** (jobs 830-839, all COMPLETED 0:0, gates
   passed, `System.qcow2` unchanged, 2.4 VM-hours):
   - L0-raw sample (830): the four shell chords pass 10 of 10 with their
     queued events read without state (0-3 ms after the grab key); the four
     ungrabbed chords pass with every state read; `key_kp_enter` and
     `type_unicode_bmp` fail as predicted; `seq_type_chord_type` fails
     section 5 on stale markers only (C2 does not judge the marker).
   - L0-fixed sample on 8 VMs (831): 180 of 180, nothing read without state.
   - Negative case (832 `omit`, 833 `release_first`): 0 of 140; every chord
     with a dropped modifier fails, grabbed or not; no event read without
     state; C4 disagrees in all 140. With `omit` the grab key is never
     pressed and `d` arrives alone with Mod2; with `release_first` every
     event is processed and the last key's press lacks its modifier.
   - v1's final runs 703-708 repeated (834-839, workloads and resources
     unchanged): the same outcomes (52/56 with the injected restarts, 400/400,
     800/800, 194/198 and 178/186 with only the outside-spec R cells failing,
     60/60 canary); C4 140/140 and 280/280; step p95 2.71 s and 2.76 s.
   - 4,394 guard checks read Mod2; the only guard violations were 22 lost
     focus (condition c) in the ungrabbed `release_first` trials.

## Runs (seed 42, CPU only, `vm-campaign.sbatch`, at `126ff8b`)

| Job | Campaign | Layer | VMs | Trials | PASS | Run time |
|---|---|---|---:|---:|---:|---|
| 830 | `q2ap-v2-d43-l0raw-sample-v1` | L0-raw | 1 | 180 | 151 | 7 min 28 s |
| 831 | `q2ap-v2-d43-l0fixed-sample-n8-v1` | L0-fixed | 8 | 180 | 180 | 3 min 13 s |
| 832 | `q2ap-v2-d43-drop-omit-v1` | L0-fixed, fault `omit` | 1 | 70 | 0 | 4 min 1 s |
| 833 | `q2ap-v2-d43-drop-release-first-v1` | L0-fixed, fault `release_first` | 1 | 70 | 0 | 5 min 55 s |
| 834 | `q2ap-v2-d43-l0-restart-v1` | L0-fixed, as 703 | 1 | 56 | 52 | 4 min 19 s |
| 835 | `q2ap-v2-d43-l0-fixed-v1` | L0-fixed, as 704 | 1 | 400 | 400 | 18 min 28 s |
| 836 | `q2ap-v2-d43-l0-fixed-n8-v1` | L0-fixed, as 705 | 8 | 800 | 800 | 5 min 58 s |
| 837 | `q2ap-v2-d43-hosw-fixed-v1` | H-OSW-fixed, as 706 | 1 | 198 | 194 | 10 min 33 s |
| 838 | `q2ap-v2-d43-hga-v1` | H-GA, as 707 | 1 | 186 | 178 | 9 min 57 s |
| 839 | `q2ap-v2-d43-canary-v1` | canary, as 708 | 1 | 60 | 60 | 10 min 45 s |

How they ran: `git archive 126ff8b` extracted read-only to
`~/cotcodec-runs/q2-action-path-v2/dev/src/<sha>` on the host (tree digest
`a303c1e2...`, the same locally and on the host); the manifests
(`experiments/manifests/q2-action-path-v2/d43-*.yaml`, written by
`ops/make_dev_manifests.py`) passed `scripts/submit_vm_campaign.py --dry-run`
from the export (batch script digest `3d86820d...`, the frozen one) and were
submitted from it (`ops/submissions.log`); `scripts/record_slurm_end_states.sh`
recorded each end state (`slurm-state/`).

## Files

| Path | What it is |
|---|---|
| `d43-development-runs.json` | `ops/summarize.py` over jobs 830-839: end states, gates, digests, per-cell PASS counts, reasons, C4, `state_not_observed`, guard violations and modifier states, every key event read without its state |
| `records/lock-bits-scan-v1.json` | `ops/lock_bits_scan.py` over every run directory of the lane (v1's development, 768, 784-787): baselines, guard checks, every key event without Mod2 |
| `records/trials-v1-c2-and-v2-dev.json` | `ops/extract_trials.py`: every chord trial of jobs 768 and 784-787, as the judge's input |
| `records/trials-v1-dev-queued-and-m11.json` | the same for `chord_super_d` and `chord_ctrl_alt_shift_r` in runs 486, 549, 574 and 572 (M11) |
| `records/trials-d43-dev.json` | the same for every chord trial of jobs 830-833 |
| `runs/<job>/` | `manifest.json`, `preflight.txt` (batch record), `receipt.json`, `session_plan.json`, `slurm-<job>.out`, `raw-sha256sums.txt` (every raw file left on the host) |
| `slurm-state/<job>.txt` | the watcher's `scontrol show job` record |
| `ops/rejudge.py` | re-judges extracted trials with the checkout's judge through `suite.observation` (C2's reading and C4 too) |
| `ops/make_dev_manifests.py` | writes and validates the ten manifests |
| `ops/submissions.log` | the submission log |

The scan, extraction and summary scripts ran on the host with the system
Python, and the committed copies are the ones that ran (same SHA-256 there);
re-running the scan and the first two extractions reproduced their outputs
byte for byte. `tests/test_q2_d43_judge.py` reads the records. Raw outputs stay on the
host under `~/cotcodec-runs/q2-action-path-v2/dev/runs/`; v1's run
directories and jobs 768 and 784-787 were only read.
