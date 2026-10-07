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
