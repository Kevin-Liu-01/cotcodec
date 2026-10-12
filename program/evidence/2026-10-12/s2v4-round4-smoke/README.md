# S2 v4 round 4 (D90): the development smoke and the oracle's registered route

Registration: `program/preregistrations/s2-arabic-cua-locale-v4.md` (DRAFT, not frozen; D80 (iv);
repaired under D84, D87 and D90). Development only, dev split only: nothing here is a Phase 0
result, and nothing here decides anything registered. The K0 section is unchanged (`ed38b953...`),
and so are `harness/s2_locale/k0_v4.py` and the batch files.

D90 fixed round 4's acceptance criterion and stop rule before this smoke. The criterion: on all 17
dev tasks, every masked boot pair E-E2, ER-ER2, AD-AR and E-S is at most tol6, so I2, I5 and I6 are
each 17 of 17; and no Impress boot shows a deviating status-bar field. Its reading was fixed in
`harness/s2_locale/dev_smoke.py read` before the smoke ran.

## Result: PASS

- **(a) Registered pairs.** On all 17 dev tasks the four registered pairs are present and within
  tol6 = 50 (the oracle route's tolerance on this run).
  - E-E2: at most 1 px (I6 17 of 17).
  - ER-ER2: at most 1 px.
  - AD-AR: 0 px on every task (I5 17 of 17).
  - E-S: at most 18 px (I2 17 of 17). The 18 px are on the Writer task `e528b65e`: a 1 x 18 px
    text caret at x 647, y 386-403, shown in one render and not the other. Every other task is at
    0 or 1 px.
- **(b) Status bar.** 140 Impress capture boots were read: 7 tasks, 20 boots each. That is 98 pairs
  in all, the registered pairs plus each further boot of a cell against that cell's first boot. In
  every pair, 0 pixels differ in LibreOffice's status bar (rows 1060-1079), both by K0's rule and
  for any change at all. Whole-screen masked counts on these pairs are at most 1 px.
- **Oracle route (Slurm 1243).** `instrument_checks.pass` is true. I1-doc holds: the synthetic plant
  is detected on 17 of 17 tasks, and PD on all 15 named tasks. I2, I5 and I6 are each 17 of 17. I3
  and I4 are 100%.

D90's stop rule does not fire on the smoke. It still applies to a fresh audit of round 4.

## smoke-1242/ (Slurm 1242)

Job:
- CPU only, `s2v4-vm.sbatch` (batch SHA-256 `1f831bbb...`, unchanged).
- From a `git archive` export of `b8c815c89771183f22114df83a08b2b46c8d4461`, extracted on the host
  with GNU tar. The upload went in 4 MB parts and was checked against the archive's SHA-256 before
  extraction, because the link dropped larger streams. Source tree digest `6c1037c9...`.
- Manifest `experiments/manifests/s2v4/dev-smoke-v5.json`: canonical SHA-256 `0e288e18...`, 310
  slots (240 capture, 70 gold).
- V = 20; 81 CPUs requested, 82 allocated; 126 GB.

Timing:
- Submitted at 11:57:53 UTC on an empty queue. Successor E session 1's 4B pair had ended at about
  05:47 UTC, and E2's 9B pair may start no earlier than about 17:51 UTC. No other workstream had a
  step pending, and the lane's 14 host snapshots saw no foreign Slurm job.
- The lane ran from 11:58:27 to 13:00:55 UTC (62.5 minutes, against a 98-minute limit).
- `lane_exit=0`, no labelled container left.

Files:
- `probes.jsonl`: every attempt.
- `lane-receipt.json`: host snapshots removed, as for smoke 1240.
- `preflight.txt`.
- `smoke-summary.json`: `smoke_summary.py` on a Mac copy of the capture records and renders.
- `dev-smoke-read.json`: `dev_smoke.py read --tol6 50` on the same copy.
- `probe-stats.json`: descriptive numbers from the records.
- The screenshots and accessibility trees stay on the host (`vm-runs/1242`).

What the records show:
- 310 of 310 slots probed. 9 slots were re-queued once after an infrastructure loss and probed on
  the second attempt:
  - 6 guest-server restarts, found by the end-of-slot check: `01b269ae` PL, `4ed5abd0` A,
    `ac9bb6cb` A, `af23762e` PL r2, `d681960f` E r1 and r2.
  - 3 `runner_crash`: guest transport failures at `evaluate` (`GET /terminal` connection aborted),
    on `2b94c692` A, `ac9bb6cb` E r1 and `bf4e9888` PL.
  - Records: 319.
- The capture as registered in round 4 ran in all 249 capture attempts. The order was the 60 s
  settle (60.0-60.02 s), then one warp from (1728, 972) to (995, 540) (0.222-0.237 s in the guest),
  then the 4 s wait (`timings.pointer_wait_s` 4.000-4.036 s), then the two screenshots.
- The warp now lands 59.0-61.0 s after the guest server's reply to the task's open step (median
  59.98 s). In smoke 1240 it landed within about 1.1 s of that reply (median 0.06 s).
- Capture slots took 3.99 minutes at the median (4.74 at most).
- Held fixed in all 240 capture slots, S included, as in smokes 1214 and 1240:
  - keyboard `setxkbmap` `us,us`, `ibus-daemon`, input sources `[('xkb', 'us')]`, IBus engine
    `xkb:us::eng`;
  - `LANG=en_HK.UTF-8` and `LANGUAGE=en_HK:en` for the guest server and every LibreOffice process;
  - `fc-match :lang=ar` DejaVu Sans, with 20 Arabic-capable families;
  - the same package states, and P0.10's same three values.
- No setup or postconfig failure, and every postconfig save rewrote its file.
- The Arabic chrome share was 0.952-0.979 in A, AR and AD and 0 elsewhere. The menu bar ran right
  to left exactly in ER, AR, AD and PD. The strict activation title was missing only on `936321ce`,
  in every cell, as in smoke 1240.
- Do-nothing verdict:
  - `fail` in every slot of S and of the derived cells;
  - on PD, `error` in 21 of the 24 slots and `fail` in 3: `0e47de2a`, and `ac9bb6cb` r1 and r2.
    Both of these tasks have a planted document. The tasks behave the same way in smokes 1214
    and 1240. The two tasks without a plant (`2b94c692`, `bf4e9888`) give `error`.
  - Correction: smoke 1240's README reads "`error` on the 15 planted documents", and the
    registration's account adds "`fail` on the two tasks without a plant". In 1240's records the 15
    `error` slots include the two tasks without a plant, and the 2 `fail` slots are `0e47de2a` and
    `ac9bb6cb`.
- Golds: 65 of 70 pass. 13 of the 14 tasks pass in all five admission cells. `af23762e`'s gold
  fails in all five, E included.

## oracle-route-1243/ (Slurm 1243)

The oracle's registered route, run exactly as P0.7 registers it:
- one CPU container job through `s2v4-cpu.sbatch` run mode (batch SHA-256 `47c09008...`);
- `--network=none`, 0 GPUs;
- the metric image `sha256:2006c1a9...` (`oracle_vm.ORACLE_IMAGE_ID`);
- argv `oracle_vm.registered_argv(1)`, generated from the export (its hex SHA-256 is `015a969f...`,
  the same as job 1241's);
- the export of `b8c815c8` at `/src`, and smoke 1242's run directory read-only at `/ro/run1`.

It was submitted at 13:01:46 UTC on an empty queue, right after 1242 ended, and ran for 35 s in
Python 3.12.13 with numpy 1.26.4, scipy 1.17.1 and Pillow 11.0.0.

Files: `oracle.json`, `k0.json` (development only), `receipt-1243.json` and `slurm-1243.out`.

Numbers:
- tol6 = tol5 = 50; tol2 0.0565; tol3 19.
- The instrument checks pass:
  - I1-doc: synthetic plant 17 of 17, PD on all 15 named tasks, correctly not on `2b94c692` and
    `bf4e9888`;
  - I2 17 of 17; I5 17 of 17; I6 17 of 17;
  - I3 34 of 34; I4 148 of 148.
- Descriptor plants: O3 16 of 17 (missed on `4ed5abd0`) and O2 16 of 17 (missed on `ac9bb6cb`),
  both above the 90% bar. On these dev renders the descriptors are valid; on smoke 1240's they were
  invalid, at O2 15 of 17.
- K0's admission on the dev tasks: 13 admitted and 4 more runnable (`0e47de2a`, `2b94c692`,
  `ac9bb6cb`, `af23762e`). `k0.json`'s `runnable` count of 17 includes the admitted tasks. These are
  the same as on smoke 1240. `k0.json` reads "FAIL" only because a dev-only run cannot reach
  K_min = 62.

Mac cross-check: on the Mac copy, `dev_smoke.py read`'s registered-pair counts equal the
container's on all 68 registered pairs, both the masked and the exact counts. The full Mac run of
`oracle_vm.py` (round 3's `mac-crosscheck.json`) was not repeated.

## Not done here

These are recorded as open in the round-4 review log:
- the fresh audit of round 4;
- the scratch freeze rehearsal at the final head;
- the host development rung for `ap_delta.run_rung`'s pre-run checks.
