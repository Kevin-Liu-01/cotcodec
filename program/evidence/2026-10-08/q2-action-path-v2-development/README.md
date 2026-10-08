# q2-action-path-v2: development characterisation of v1's C2 failure (2026-10-08)

**Development evidence only (seed 42, never evidence for any criterion).**
Decision D40 lets development characterise why `chord_super_d` failed v1's
C2 (job 768) and whether L0-fixed is exposed, on seed 42 only. Nothing here
changes a rule; `q2-action-path-v2.md` section 26 reports it.

## Result

1. **Reproduced.** Under L0-raw (`pyautogui.hotkey('winleft', 'd')`, no
   interval and no hold) `chord_super_d` failed 10 of 10 (job 784), as in
   job 768 (5 of 5): the `d` press 1-2 ms after Super_L is recorded with core
   state 0, and so are the releases after it.
2. **Only on chords the shell grabs.** Of the 13 chord entries sent by
   L0-raw at the same speed, the nine the shell does not grab passed 10 of
   10 with every state right; the four it grabs (Super+d, Alt+F4, Alt+Tab,
   Ctrl+Alt+Shift+R) failed 10 of 10, with every key event after the
   grab-activating key recorded with state 0, not even the NumLock bit that
   every other event carries.
3. **Mechanism.** mutter 42.9 grabs its overlay key and every keybinding in
   `XIGrabModeSync`, so the X server freezes the keyboard and queues later
   key events until the shell answers. RECORD reports a queued event when it
   is queued, before its state is computed, and not again on replay (X
   server `dix/events.c` `EnqueueEvent`, `Xi/exevents.c`
   `ProcessDeviceEvent`, read at the GitHub mirror's master; the guest's
   Xorg 21.1 release was not read).
4. **The shell received Super+d.** Under L0-raw the probe got no key, lost
   the focus and left the screen in 15 of 15 trials, exactly as under
   L0-fixed (30 of 30), where `d` carries Mod4. Had the shell received `d`
   without Mod4 it would have replayed it to the probe. The press-state loss
   is in the tap's record, not in what reached the shell.
5. **L0-fixed's exposure.** With the keyboard warmed up, `chord_super_d` on
   the L0-fixed path passed 127 of 127 trials (v1 development 97, jobs
   785-787 30, at 8 and 16 concurrent VMs with 32 running at once), 109 of
   them not the session's first key event; the `d` press came 10-14 ms after
   Super_L with Mod4 every time. Upper 95% bound 2.3% per trial (2.7% over
   the 109). The only failures on the L0-fixed path are runs 549 and 574,
   before the warm-up existed, where `chord_super_d` was the session's first
   key event: `d` at 12-17 ms, state 0, the shell acting on the chord.

## Runs (seed 42, CPU only, `vm-campaign.sbatch`, at `e66bf16`)

| Job | Campaign | Layer | VMs | Trials | End state |
|---|---|---|---:|---:|---|
| 784 | `q2ap-v2-dev-l0raw-chords-v1` | L0-raw, 13 chord entries | 1 | 130 | COMPLETED 0:0, 5 min 36 s |
| 785 | `q2ap-v2-dev-l0fixed-superd-n8-v1` | L0-fixed, 8 entries | 8 | 80 | COMPLETED 0:0, 1 min 42 s |
| 786 | `q2ap-v2-dev-l0fixed-superd-n16-v1` | L0-fixed, 8 entries | 16 | 80 | COMPLETED 0:0, 1 min 27 s |
| 787 | `q2ap-v2-dev-l0fixed-superd-n8-v2` | L0-fixed, 8 entries | 8 | 80 | COMPLETED 0:0, 2 min 8 s |

Every job: Slurm (watcher record) and the batch record agree; TRES CPU and
memory only (no GRES); infrastructure gates passed; `System.qcow2` unchanged
(SHA-256 `6bf667a8...` before and after); no labelled container or volume
left; no trial with an infrastructure failure. 1.0 VM-hours in all (run time
times VMs). Jobs 785-787 ran at the same time. Every cell of jobs 785-787
passed 10 of 10; job 784's per-cell results are in `v2-development-runs.json`.

How they ran: `git archive e66bf16` extracted read-only to
`~/cotcodec-runs/q2-action-path-v2/dev/src/<sha>` on the host (tree digest
`73e373a2...`, the same locally and on the host); the manifests
(`experiments/manifests/q2-action-path-v2/`, written by
`ops/make_dev_manifests.py`) passed `scripts/submit_vm_campaign.py --dry-run`
from the export (batch script digest `3d86820d...`, the frozen one) and were
submitted from it; `scripts/record_slurm_end_states.sh` recorded each end
state. The submission log lost the job ids (the submitter prints the id
alone); its last line gives them.

## Files

| Path | What it is |
|---|---|
| `v2-development-runs.json` | One row per job: end state, gates, receipt SHA-256, tree digest, per-cell PASS counts |
| `chord-super-d-by-condition.json` | Every `chord_super_d` trial of v1's development runs, job 768 and jobs 784-787, by executor, warm-up and first key event: timing, state and the shell's response |
| `shell-chords-by-executor.json` | The four shell-grabbed chords and the nine others under L0-raw (768, 784) and L0-fixed (785-787): the core state of every key event after the first |
| `chord-trials-v2-and-c2.json` | Every chord trial of jobs 768 and 784-787, as `ops/chord_timing.py` reads it |
| `runs/<job>/` | `manifest.json`, `preflight.txt` (batch record), `receipt.json`, `session_plan.json`, `slurm-<job>.out`, `raw-sha256sums.txt` (every raw file left on the host) |
| `slurm-state/<job>.txt` | The watcher's `scontrol show job` record |
| `ops/chord_timing.py` | The read-only scan of run directories (run on the host over v1's development runs 482-708, job 768 and jobs 784-787; its output, 2.4 MB, stays on the host, SHA-256 `cde5d64d...`) |
| `ops/summarize.py` | Writes the three summaries above from that scan |
| `ops/make_dev_manifests.py` | Writes and validates the four manifests |
| `ops/submissions.log` | The submission log |

Raw outputs stay on the host under `~/cotcodec-runs/q2-action-path-v2/dev/runs/`.
v1's development runs and job 768 were only read; nothing in their run
directories changed.
