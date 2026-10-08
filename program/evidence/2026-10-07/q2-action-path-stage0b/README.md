# Q2 Stage 0b: VM runtime validation (2026-10-07)

Infrastructure validation for `q2-action-path-v1`, done before its
preregistration is frozen. None of it is evidence for the acceptance criteria
A1-A6. Raw outputs stay on the host under
`~/cotcodec-runs/stage0/q2-action-path/runs/<job>/`; the files here are
summaries extracted from the job receipts, with the receipt SHA-256 recorded.

| File | What it is |
|---|---|
| `boot-reset-report.json` | Jobs 369 (smoke), 372 (bridge exposure) and 374 (22 cold boots): boot and settle times, reset sentinel, isolation, guest facts, HMP reachability |
| `rdev-capture-report.json` | Jobs 387 (superseded) and 393 (reference): the R-dev capture of the 35 key, chord and Caps Lock entries, 5 repetitions each; job 468, the same plan re-captured with the rewritten tap |
| `tap-selftest-report.json` | Jobs 467, 469, 470 and 471: the rewritten XRecord tap's oracle self-test after the review |
| `development-runs.json` | Jobs 482-637, 662-667 and 694-708: inputs validation and development (seed 42, never evidence), one row per job |

## What the runs show

All five jobs (369, 372, 374, 387, 393) ran as CPU-only Slurm jobs through
`vm-campaign.sbatch` (no GRES in the job's TRES), with the VM image pinned by
digest, the qcow2 read-only and unchanged (SHA-256 checked before and after),
and zero labelled containers or volumes left. Jobs 374, 387 and 393 ended
`COMPLETED`, exit `0:0`; jobs 369 and 372 left the queue before their state
was read, and their driver exit codes are 0.

- **Boot (job 374, N = 1, 4 vCPU, 4 GiB):** 22 of 22 cold boots served a valid
  `/screenshot`; container start to first screenshot p50 18.3 s, p95 20.8 s,
  max 22.4 s; two identical consecutive screenshots p50 21.6 s, p95 25.3 s.
  22 distinct guest boot IDs.
- **Reset sentinel:** a file, a dconf key and a gsettings key written in each
  boot were read back in a fresh process (22 of 22 each) and were absent after
  the next cold boot (21 of 21 reset checks).
- **Latency (66 samples):** `/execute` no-op p50 16 ms, `/screenshot` p50
  0.60 s, `/accessibility` p50 1.45 s (p95 1.86 s).
- **Isolation:** in the default `none-netns` layout the VM container has no
  Docker network and no bridge address; the runner, in the VM's namespace,
  reached the guest server and the QEMU monitor. No container saw
  `/dev/nvidia*`; the runner ran as the host user with no capabilities,
  `NoNewPrivs` and seccomp. In the `bridge-unpublished` fallback (job 372) a
  separate container on the default bridge got HTTP 200 from the guest's
  `/platform` through the image's DNAT: the exposure decision D13 records.
- **HMP input reachability (22 boots):** QEMU `sendkey` reached X for `a`,
  Shift+comma, KP_Enter (keycode 104), KP_Add (86), the 102nd key (94,
  `less`), Escape and Caps Lock (LED bit toggled on and back off), and
  `mouse_button` gave X buttons 1, 2 and 3; HMP wheel input gave buttons 5 and
  4; relative motion arrived. QEMU qcode `menu` gave no X event in 22 of 22
  boots, while qcode `compose` gave keysym Menu (keycode 135) in 22 of 22, so
  the R-dev plan uses `compose`. HMP cannot press buttons 8 or 9.
- **Guest:** Ubuntu 22.04.3, kernel 6.5.0-15, Xorg with GNOME Shell 42.9,
  1920x1080, xkb evdev / pc105 / `us,us`, PyAutoGUI 0.9.54, python-xlib 0.33,
  RECORD and XTEST present, 19 spare keycodes, guest server `main.py` SHA-256
  `41376a5c4f0b68ed7bbbbcc73ece60427f4a58dd8bd4710176f9911de726339e`; installed
  apps include LibreOffice, Google Chrome, VS Code, GNOME Terminal, gedit,
  GIMP, VLC and Thunderbird; no `xdotool`.
- **Disk growth per boot:** copy-on-write overlay about 66 MB; `/storage`
  7.3 MB (the image's sparse data disk and UEFI variables).
- **R-dev reference (job 393):** QEMU `sendkey` for the 35 key, chord and
  Caps Lock entries, 5 repetitions in one boot (175 windows, 175 clean
  guards): all 35 projections identical across repetitions and balanced; the
  Caps Lock LED went on and back off in 5 of 5. The streams are in
  `harness/q2/action_path/rdev_reference.json` and in the catalog. Job 387
  ran the same plan but sent each side-effect entry's recovery chord inside
  the entry's window, so `key_f1`, `key_menu`, `chord_super_d` and
  `chord_ctrl_alt_shift_r` ended with a stray press; the reference now also
  requires every press to be released in the window, and 387 is superseded.

## After the review (jobs 467-471)

The review of 2026-10-07 found that the XRecord tap read keysyms from a keymap
cached when it connected, so a keycode remapped later (the technique the
planned executor uses for Unicode text) would be projected with its old
keysym. The tap was rewritten to record core `ChangeKeyboardMapping` requests
in the same RECORD stream and keep its own keymap; these jobs validate it.
All ran as CPU-only Slurm jobs through `vm-campaign.sbatch`, VM image by
digest, qcow2 unchanged, no labelled container or volume left, no NVIDIA
device in any container.

- **Self-test (jobs 467, 469, 470, 471; 15 cycles in all):** in each cycle a
  guest fixture remapped spare keycode 248 to `eacute`, then U+0416, then
  NoSymbol, pressing it with XTest after each change. In 15 of 15 cycles the
  tap reported exactly 233, 16778262 and 0 for the six events; a keymap read
  at tap start (the old behaviour) gives 0 for all six.
- **The mapping check took three iterations, all recorded.** Every cycle saw
  one keyboard MappingNotify for the whole range 8-255 that no core request
  explains: the server re-sends the keymap when the master keyboard switches
  from the PS/2 device (HMP input earlier in the cycle) to the XTest device.
  Job 467 counted it as an unseen change; job 469 compared it by raw rows and
  found a difference only at keycode 248; job 470 recorded the rows: the tap
  had written `[eacute] * 7` and the server read back `[eacute] * 4 +
  [NoSymbol] * 3`, XKB's core view of the same mapping. Rows are now compared
  under the core protocol's keysym-list rules. Job 471 (5 cycles, commit
  54317d6) passed every gate, `COMPLETED`, exit `0:0`: 4 explained and 1
  benign notify per cycle, reset sentinel 4 of 4 pristine, boots 17.3-21.1 s.
  Jobs 467, 469 and 470 failed only their tap gate, by the check then in
  force; their Slurm states were purged before they were read.
- **R-dev re-capture (job 468):** the job-393 plan, 5 repetitions, with the
  rewritten tap (commit a1aade3, whose tap `main` is the one committed): 35 of
  35 entries stable, and all 35 projections identical to job 393's, so
  `rdev_reference.json` is unchanged. `COMPLETED`, exit `0:0`.

## Development (seed 42, never evidence; jobs 482-637 and 662-667)

Development runs iterate the executor, the harness adapters and the canary
before the freeze (preregistration section 10). None of them is evidence for
A1-A6 or C1-C4; they are listed so a reader can see what changed in response
to what. Every job ran as a CPU-only Slurm job through `vm-campaign.sbatch`
(no GRES in its TRES; `no_gpu_all` true), with the VM in its own network
namespace, `System.qcow2` unchanged and no labelled container or volume left;
every driver exited 0 except job 482, which stopped before any container
started. `development-runs.json` has one row per job (campaign, commit, cells
not PASS, infrastructure failures, observation retries, trial and step times,
Slurm end state where it was read before Slurm forgot the job, receipt
SHA-256).

What the development runs found and what changed (commits on
`stage0/q2-action-path`; the preregistration's section 16 lists the same):

| Jobs | Commit | Finding | Change |
|---|---|---|---|
| 486-499 | `29b056e`-`7c1bb02` | screenshots one compositor frame behind; the screen frozen while GNOME Shell rebuilt its keymap after Unicode typing; chord releases losing their modifiers; H-OSW-fixed's `wait` and edge whitespace | quiet-screen wait, shell barrier, 0.1 s key hold, two more H-OSW-fixed own-spec fixes |
| 501-522 | `7c1bb02`-`fe92765` | Chrome's accessibility text stale; VS Code's walkthrough over the file; Chrome's "Can't update Chrome" bubble | Chrome read back from its mirrored title, the walkthrough off, a flag that keeps the bubble closed |
| 504-541 | `1ce92a6`-`bde1f82` | the probe's last drawing never painted in 31 of 941 typing trials (3.3%) | L0-fixed re-damages every top-level window after each action (working from `a1d7e10`; at `bde1f82` the nudge raised and was skipped, so 537-541 are a control) |
| 537 | `bde1f82` | the boot's first `/accessibility` call answered HTTP 500, its retry 200 | the reset observation before a session's first trial; a delivered retry is reported, not a failure (section 6.1) |
| 549, 574 | `b603347`, `dba0580` | `chord_super_d` lost its Super modifier when its Super_L press was the session's first key (8 VMs and one VM, the same 14 sessions, the same two failures) | the guard's keyboard warm-up before every session (from `a6623ae`; 609 and 610 ran the same sessions clean) |
| 553-602 | `b603347` | the 44 mutants on their predicted kill cells: 42 killed, M12 and M13 on H-OSW-fixed passing (predicted equivalent); three predicted killers did not kill | none (predictions stay; C3 reports predicted next to observed) |
| 613 | `81fd5f3` | on a loaded host VS Code dropped the first keys of three trials while still loading | the canary waits until the app's processes are idle (`59697b3`) |
| 620, 631-632 | `091b33e` | Writer put an emoji before the space typed ahead of it, in 1 of the 336 Writer trials of runs 501-632 (job 620; jobs 631-632 typed every Writer entry five times without it) | none; reported (GNOME's input-method daemon sits between X and GTK applications) |
| 622 | `81fd5f3` | the guest server crashed inside `/accessibility`; systemd stopped everything it had launched (probe and tap) and restarted it, so one session's 55 trials were charged | restarts typed as `guest_server_restart` (`d0c4cec`); A4's exposure is a decision for the owner (inputs addendum, section 6) |
| 545-632 | `a1d7e10`-`091b33e` | the nudge's `DamageAdd` on InputOnly windows drew a `BadMatch` error on almost every action (harmless; those windows have no contents) | InputOnly windows skipped (`d0c4cec`) |
| 662 | `30d8c7f` | after the review of `2b492cd`: the guest server SIGKILLed on purpose after the tenth trial of each session (one per setting), the fault of run 622 | with the tap relaunched alongside the probe, only the next trial failed in each session (`guest_server_restart` typed, server 1747 to 2125 and 1766 to 2520), 27 of 28 trials passed per session, both tap segments' mapping checks clean |

The final validation, at `81fd5f3` (with the warm-up), at `091b33e` (the
canary's idle wait) and at `82af567` (the final runtime commit; the files the
VMs run differ from `81fd5f3` only in the canary's idle wait, the guard's
server report and the nudge's InputOnly skip). Outside-spec R cells fail by
design (preregistration section 3):

| Job | Commit | Campaign | Trials | Cells PASS | Not PASS |
|---|---|---|---:|---:|---|
| 609 | `81fd5f3` | L0-fixed, all 100 entries, 4 repetitions per setting, one VM | 800 | 200 of 200 | none |
| 610 | `81fd5f3` | L0-fixed, the same 14 sessions on 8 concurrent VMs | 800 | 200 of 200 | none |
| 611 | `81fd5f3` | H-OSW-fixed, every corpus cell, 2 repetitions per setting | 396 | 194 of 198 | R03 (outside spec), R09 (outside spec) |
| 612 | `81fd5f3` | H-GA, every corpus cell, 2 repetitions per setting | 372 | 178 of 186 | R02 (outside spec), R04 (outside spec), R06 (outside spec), R10 (outside spec) |
| 618 | `81fd5f3` | L0-fixed, A3's 30 stress entries, 5 repetitions per setting, 8 VMs | 300 | 60 of 60 | none |
| 621 | `81fd5f3` | the same, a second job | 300 | 60 of 60 | none |
| 619 | `81fd5f3` | L0-fixed, all 100 entries, 5 repetitions per setting, 8 VMs | 1000 | 200 of 200 | none |
| 622 | `81fd5f3` | the same, a second job | 1000 | 151 of 200 | 49 cells, all from the one session the guest-server restart broke (tap window missing 55, channel missing 6, probe absent 1) |
| 613 | `81fd5f3` | canary, every app and entry, 2 repetitions (without the idle wait) | 120 | 57 of 60 | vscode:triple_click_line, vscode:type_emoji, vscode:type_symbols_shifted |
| 620 | `091b33e` | canary, every app and entry, 2 repetitions (with the idle wait) | 120 | 59 of 60 | writer:type_emoji |
| 631 | `091b33e` | canary, the 16 Writer entries, 5 repetitions | 80 | 16 of 16 | none |
| 632 | `091b33e` | the same, a second job | 80 | 16 of 16 | none |
| 633 | `82af567` | L0-fixed, all 100 entries, 2 repetitions per setting, one VM | 400 | 200 of 200 | none |
| 634 | `82af567` | L0-fixed, all 100 entries, 4 repetitions per setting, 8 VMs | 800 | 200 of 200 | none |
| 635 | `82af567` | H-OSW-fixed, every corpus cell, 1 repetition per setting | 198 | 194 of 198 | R03 (outside spec), R09 (outside spec) |
| 636 | `82af567` | H-GA, every corpus cell, 1 repetition per setting | 186 | 178 of 186 | R02 (outside spec), R04 (outside spec), R06 (outside spec), R10 (outside spec) |
| 637 | `82af567` | canary, every app and entry, 1 repetition | 60 | 60 of 60 | none |

After the review of `2b492cd`, the fixes (`30d8c7f`) changed the session,
runner, driver and manifest code, so the final validation was repeated there
(every job `COMPLETED` 0:0 as recorded by a watcher, driver exit 0, no GPU in
its TRES, `System.qcow2` unchanged, nothing labelled left). These are the
runs the executor addendum's byte-identity rule refers to:

| Job | Commit | Campaign | Trials | Cells PASS | Not PASS |
|---|---|---|---:|---:|---|
| 662 | `30d8c7f` | L0-fixed, 28 entries, 1 repetition per setting, guest server SIGKILLed after each session's tenth trial | 56 | 54 of 56 | `type_long_200` in both settings: the trial right after each restart (`guest_server_restart`) |
| 663 | `30d8c7f` | L0-fixed, all 100 entries, 2 repetitions per setting, one VM | 400 | 200 of 200 | none |
| 664 | `30d8c7f` | L0-fixed, all 100 entries, 4 repetitions per setting, 8 VMs | 800 | 200 of 200 | none |
| 665 | `30d8c7f` | H-OSW-fixed, every corpus cell, 1 repetition per setting | 198 | 194 of 198 | R03 (outside spec), R09 (outside spec) |
| 666 | `30d8c7f` | H-GA, every corpus cell, 1 repetition per setting | 186 | 178 of 186 | R02 (outside spec), R04 (outside spec), R06 (outside spec), R10 (outside spec) |
| 667 | `30d8c7f` | canary, every app and entry, 1 repetition | 60 | 60 of 60 | none |

Step p95 2.74 s (663, one VM) and 2.79 s (664, 8 VMs); boot p95 19.1 s and
19.3 s. Every trial's reset observation was delivered. The acceptance
analysis's loader read all six run directories (end state from the batch
record and the watcher's Slurm record, both agreeing), and C4's check passed
in 140 of 140 (663) and 280 of 280 (664) key, chord and Caps Lock trials.

From job 545 on (the working repaint request), no trial ended on a stale
marker: 0 of 2,114 typing trials (one-sided 95% upper bound 0.14%),
against 31 of 941 in runs 504-541. Counting rule, recounted from the
receipts after the review: every trial of a `suite-development` campaign
(any layer, mutant runs excluded) whose catalog entry contains a `type`
action; a stale marker is a trial whose verdict has the reason `marker [seq,
crc] != probe final [...]` and no infrastructure failure. The recount gives
31 of 940 for runs 504-541 and 0 of 2,100 for runs 545-637 (10 of those
trials had an infrastructure failure, the session job 622's restart broke
among them); the first counts above and the review's (965 and 2,154) differ
only in which trials entered the population, and none shows a stale marker
after the repaint request. Counting only `type_*` entries of L0-fixed: 22 of
595 before and 0 of 1,446 after (0 of 189 more in jobs 662-664). That bound
(0.14% per typing trial) is about three times looser than the 5 x 10^-4
per-action rate A4 must show for the typing class, so A4 can still fail on a
repaint loss too rare for development to see.

Accessibility calls, recounted the same way: 8,114 `/accessibility` calls
(8,117 attempts) in the 113 accessibility-setting sessions of runs 484-622,
counting the reset observation and every step's call; the first count said
7,969. Two observation faults: run 537's HTTP 500 on its session's first
call (recovered by the retry) and run 622's crash on its session's third
call.

The acceptance analysis (`acceptance.py`) run over these receipts for
information: job 609's 280 key, chord and Caps Lock trials all matched their
R-dev reference (what C4 will check in A1); and job 610's host snapshots
show two foreign Slurm jobs starting and foreign jobs holding 72 CPUs, so a
ladder rung run under those conditions would abort (section 9). The ladder
needs a quiet host.

## Decision D30 (jobs 694-708)

Decision D30 put the probe and the tap in their own systemd scopes, outside
the guest server's unit, and registered A4's restart exclusion and the
observation-service bound A7 (preregistration section 18). These development
runs (seed 42, never evidence) validate the scopes at the runtime commit
`7653799` and repeat the final validation there. Every job ran as a CPU-only
Slurm job through `vm-campaign.sbatch` (no GRES in its TRES; `no_gpu_all`
true), with `System.qcow2` unchanged and no labelled container or volume
left; every job that ran to its end finished `COMPLETED` 0:0 as the watcher
recorded it, with driver exit 0 and `infra_gates_pass` true.

| Job | Commit | Campaign | Trials | Cells PASS | Not PASS | Restarts | Accessibility calls |
|---|---|---|---:|---:|---|---:|---:|
| 694 | `34f79e4` | L0-fixed, 28 entries, 1 repetition per setting, the server SIGKILLed inside the tenth trial (before its post guard) and after the twentieth of each session | 56 | 52 of 56 | `chord_ctrl_c` and `drag_short` in both settings: the two trials each session's kills hit | 4 | 38 |
| 695-699 | `34f79e4` | L0-fixed on 1 and 8 VMs, H-OSW-fixed, H-GA, canary | none | | cancelled while booting (`CANCELLED`) when `manifest.py`'s A7 repair refusal was added; rerun as 704-708 | | |
| 703 | `7653799` | as 694 | 56 | 52 of 56 | as 694 | 4 | 38 |
| 704 | `7653799` | L0-fixed, all 100 entries, 2 repetitions per setting, one VM | 400 | 200 of 200 | none | 0 | 260 |
| 705 | `7653799` | L0-fixed, all 100 entries, 4 repetitions per setting, 8 VMs | 800 | 200 of 200 | none | 0 | 519 |
| 706 | `7653799` | H-OSW-fixed, every corpus cell, 1 repetition per setting | 198 | 194 of 198 | R03 (outside spec), R09 (outside spec) | 0 | 152 |
| 707 | `7653799` | H-GA, every corpus cell, 1 repetition per setting | 186 | 178 of 186 | R02, R04, R06, R10 (all outside spec) | 0 | 139 |
| 708 | `7653799` | canary, every app and entry, 1 repetition | 60 | 60 of 60 | none | 0 | 0 |

What the fault injections (694 and 703, four sessions) show:

- The tap and the probe ran in scopes of the desktop user's manager
  (`user@1000.service/app.slice/q2ap-tap-...scope` and `q2ap-probe-...scope`)
  while the server ran in `system.slice/osworld.service`. Neither was
  relaunched after either kill; each session's tap stream stayed one segment
  and its mapping check was clean.
- The server answered again 5.6 to 6.0 s after each kill inside an entry
  (`DesktopEnv` retries an observation 5 s and 10 s after a failed attempt).
- The trial killed inside (`chord_ctrl_c`, seq 9) failed with
  `guest_server_restart` alone; the acceptance loader reads it as
  restart-only, so A4 would not count it. The trial after the kill between
  entries (`drag_short`, seq 20) failed with `guest_server_restart`,
  `probe_absent`, `guard_script`, `execute`, `tap_window_missing` and
  `channel_missing`: its pre guard met the restarting server, so its window
  never opened (decision 39 charges it; A4 would count it). The other 26
  trials of each session passed.
- Every session counted two restarts, by the unit's `NRestarts` (1 at the
  session's start, 3 at its end) and by the guard reports' server ids alike.
  The counter read 1 at the start of every session of these jobs: the server
  restarts once while the guest boots, before any session starts.

The final validation at `7653799` (704-708) passed every in-spec cell; the
only failures are the outside-spec R cells of each harness, as at `30d8c7f`.
No session of 704-708 saw a restart (1,070 accessibility calls), and no probe
or tap was relaunched. Across all 34 suite sessions of these jobs the unit's
counter read 1 at the session's start. Step p95 2.92 s on one VM (704; 663:
2.74 s) and 3.02 s on 8 VMs (705; 664: 2.79 s), boot p95 19.8 s and 19.6 s:
6-8% slower steps while the host ran the other campaigns of this pass and
other users' processes (load average up to 180 on 208 CPUs during 704's last
session); the scopes act only when a session starts. The acceptance
analysis's loader read every run directory (end state from the batch record
and the watcher's Slurm record, both agreeing; restarts and calls as in the
table), and C4's check passed in 140 of 140 (704) and 280 of 280 (705) key,
chord and Caps Lock trials.
