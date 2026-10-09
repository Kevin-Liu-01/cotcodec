# q2-action-path-v2: validity controls and acceptance at N = 1 (2026-10-08)

This bundle holds two operator stages of `q2-action-path-v2`. Both ran from the
same read-only export of `bf99a64`.

1. **Acceptance at N = 1** (the second stage, jobs 964-1015). It ran A5's
   boot-reset campaign, A1 with C4, A2, A3 and A6. Every criterion it could
   judge passes. See "Second stage" just below.
2. **Validity controls** (the first stage, jobs 864-962, commit `a491c0e`).
   C2, C1 and C3 all pass. See "First stage" further down. That text is
   unchanged, apart from its heading.

## Second stage: acceptance at N = 1 (A5, A1 with C4, A2, A3, A6)

**Result: A1 at N = 1, C4, A2, A3 and A6 pass. A5 passes on everything it
can read so far.** Each criterion ran at attempt 1, in the registered order
(A5's boot-reset campaign, A1, A2, A3, A6), one campaign at a time and N = 1.
Every campaign counted at its first attempt, so nothing was rerun. Nothing was
repaired. No trial had an infrastructure failure, an observation retry or a
guest-server restart.

- **A5** (reset and hygiene). The boot-reset campaign at `bf99a64` shows 20
  of 20 pristine reset-sentinel checks. The receipts of all 8 acceptance
  campaigns of this stage show `System.qcow2` unchanged and no labelled
  container or volume left. A5 judges every acceptance campaign's receipt,
  so it is judged again once A4, A7 and the ladder have run.
- **A1** (runtime layer) at N = 1. L0-fixed passed every one of the 100
  entries 5 of 5 in the seed-43 and seed-44 shuffles, under both observation
  settings: 2,000 of 2,000 trials. The 86 entries of G gate. A1's part at
  N* > 1 is read later from the ladder rung N* (section 7).
- **C4** (R-dev agreement). All 700 A1 trials of the 35 key, chord and Caps
  Lock entries agree with the R-dev reference.
- **A2** (harness layer). H-OSW-fixed passed all 97 of its in-spec cells and
  H-GA all 87 of its in-spec cells, 5 of 5 in each setting. The only
  failures are outside-spec R cells, the same ones as in development and in
  C3's reference runs.
- **A3** (stress). 4,980 of 4,980 trials passed: L0-fixed 1,800 (30 entries),
  H-OSW-fixed 1,740 (29) and H-GA 1,440 (24).
- **A6** (cross-app canary). 300 of 300 trials passed. Each app passed 100%:
  Writer, Chrome and VS Code 16 entries each, GNOME Terminal 12.

Not in this stage, and not run: the concurrency ladder, A4 and A7. N*,
A1's part at N* > 1 and A5's final judgement wait for them.

| Criterion | Campaign | Job | Run time | Sessions | Trials | PASS | Not PASS (all outside spec) |
|---|---|---:|---|---:|---:|---:|---|
| A5 | `q2ap-v2-a5-bootreset-a1` (21 cold boots, 20 reset checks) | 964 | 17 min 20 s | 21 | - | 20/20 checks | - |
| A1 | `q2ap-v2-a1-l0fixed-s43-a1` (L0-fixed, seed 43) | 968 | 43 min 41 s | 18 | 1,000 | 1,000 | - |
| A1 | `q2ap-v2-a1-l0fixed-s44-a1` (L0-fixed, seed 44) | 970 | 43 min 54 s | 18 | 1,000 | 1,000 | - |
| A2 | `q2ap-v2-a2-hoswfixed-a1` (H-OSW-fixed) | 974 | 48 min 20 s | 18 | 990 | 970 | R03, R09 (0 of 10 each) |
| A2 | `q2ap-v2-a2-hga-a1` (H-GA) | 991 | 45 min 10 s | 16 | 930 | 890 | R02, R04, R06, R10 (0 of 10 each) |
| A3 | `q2ap-v2-a3-l0fixed-a1` (L0-fixed) | 1004 | 1 h 30 min 31 s | 30 | 1,800 | 1,800 | - |
| A3 | `q2ap-v2-a3-hoswfixed-a1` (H-OSW-fixed) | 1008 | 1 h 38 min 42 s | 30 | 1,740 | 1,740 | - |
| A3 | `q2ap-v2-a3-hga-a1` (H-GA) | 1013 | 1 h 21 min 30 s | 24 | 1,440 | 1,440 | - |
| A6 | `q2ap-v2-a6-canary-a1` (four apps, screenshot setting) | 1015 | 49 min 40 s | 5 | 300 | 300 | - |

Every job is CPU only (`TRES=cpu=6,mem=12G,node=1`, no GRES). Each ended
`COMPLETED` 0:0, by the watcher's Slurm record and by the batch record
(`driver_exit=0 labelled_containers_left=0`); the two agree. Each has an
empty `counting_problems`, `infra_gates_pass` true, `System.qcow2` unchanged,
nothing left and no unreadable file. Every cold boot served its first valid
screenshot in 16.9-18.5 s.

### A5: the boot-reset campaign and the receipts

- Job 964 ran 21 cold boots at `bf99a64` (the manifest's `git_sha`; frozen
  `acceptance.a5` checks it). Each boot after the first checked that the
  previous boot's sentinel (a file, a dconf key and a gsettings key) was
  gone: 20 of 20 pristine. Every boot read back its own sentinel.
- `acceptance.a5` over that campaign and the 8 acceptance campaigns gives
  `pass: true`. No campaign has an earlier attempt.
- The 50 control campaigns of the first stage also show `System.qcow2`
  unchanged and nothing left (`checks/run-checks.json`).
- Reported, not judged: HMP `sendkey menu` reached X in 0 of 21 boots, and
  `compose` (Menu) in 21 of 21. Section 4.3 records this from job 374 (0 of
  22). So the receipt's `hmp_cycles_all_ok` is 0, as in job 374, and its
  infrastructure gates pass.
- `acceptance/a5-after-boot-reset/` is the same analysis run right after job
  964, before any acceptance campaign existed.

### A1 at N = 1 and C4

- `acceptance.a1` gives `pass: true` with no problems. Every entry is PASS in
  both seeds, the 14 non-gating entries included.
- No trial was excused for a guest-server restart. No entry is over D33's
  limit (`entries_over_restart_limit` is empty in both seeds).
- `acceptance.c4` gives `pass: true` over 700 trials. Every A1 trial of an
  entry with a reference had `c4` true. No earlier attempt exists.
- `chord_super_d` passed 20 of 20 in A1 and 20 of 20 in A2 (10 per harness).
  In none of these 40 L0-fixed-path trials was a key event read without its
  state, so no slow shell answer (section 26) occurred.
- **A1's N = 1 reference for the ladder** (`acceptance/a1-n1-reference.json`,
  computed as `acceptance.n_star` computes it): step p95 2.694 s over 2,560
  steps (both shuffles and both settings pooled), step p50 1.823 s; boot p95
  17.92 s over 36 boots. A ladder rung needs step p95 at most 2 x 2.694 s =
  5.389 s. No foreign Slurm job ran during either A1 job (host snapshots).

### A2

`acceptance.a2` gives `pass: true` with no problems. Each in-spec cell
(gating or declared deviation) passed in 10 of 10 trials (5 per setting).
The outside-spec cells failed 10 of 10, for the same reasons as in
development jobs 852 and 853 and in C3's reference runs 872 and 870.

- H-OSW-fixed:
  - R03: Ctrl in `keys` was not pressed. `keys` on clicks is not in its
    prompt.
  - R09: the scroll ran at the pointer park point (1234, 777), not at the
    given coordinate. Coordinates on scroll are not in its prompt.
- H-GA:
  - R02 and R04: modifiers given in `text` were not pressed.
  - R06: a one-point drag pressed at the target with no motion.
  - R10: hscroll sent no event.
  - Its other outside-spec cells, R03 and R09, passed.

### A3

`acceptance.a3` gives `pass: true` with no problems. Every stress entry
passed 60 of 60 on every layer where it is expressible.

### A6

`acceptance.a6` gives `pass: true` with no problems. All 60 app-entry cells
passed 5 of 5 (`acceptance/a6-verdict.json`, `entries`, by
`app:entry`). The canary's own read-back judges these trials. The tap is not
read, so section 12's report covers 300 trials with no tap window.

### Guest-server restarts and observations (sections 6.1 and 12)

- Restarts: 0 in 7,172 accessibility calls. That is A1 1,298, A2 1,452
  (H-OSW-fixed 759, H-GA 693) and A3 4,422 (L0-fixed 1,425, H-OSW-fixed
  1,665, H-GA 1,332), exactly the registered counts (section 9).
- At the development rate (1 in 8,114 calls) no restart in these calls had
  probability about 0.41 (section 9). The development rate's exact interval
  is in every restart report.
- No trial was hit, none was excused, and no session's restart count
  exceeded those attributed to its trials. A6 runs the screenshot setting.
  A5's boot-reset campaign is infrastructure validation: its latency probe
  made 63 `/accessibility` calls, and no criterion counts them.
- No observation retry of any type. Every reset observation was delivered.

### Section 12: key events read without their state

Each criterion's analysis carries `acceptance.state_not_observed_report`
(`acceptance/*-section12-state-not-observed.json`): A1 and C4 over 2,000
trials, A2 over 1,920, A3 over 4,980 and A6 over 300. No key event was read
without its state, and no key event lacked Mod2 without a preceding processed
press. Every key event the tap recorded carried the guard's lock bit.

### How it was run

1. **Export.** The controls' read-only export of `bf99a64` on the host was
   checked again before the first submission: tree digest `abbbfe6c...`,
   `dr-xr-xr-x`, no `__pycache__`, and the batch script, `acceptance.py`,
   renderer and submitter at their frozen digests. A fresh local export of
   the same commit passed `check-chain` (15 rows), `verify` of all three ids,
   and the pin and admission tests (51 passed)
   (`checks/acceptance-export-and-reproduction.json`).
2. **Manifests.** `ops/render_acceptance.sh` ran the frozen renderer from the
   export with `--host-root ~/cotcodec-runs/q2-action-path-v2`. It wrote the
   9 manifests (A5; A1 seeds 43 and 44; A2 and A3 per layer; A6), each
   validated against the ledger. The same renderer, run locally with the same
   arguments, wrote 9 byte-identical files. No field was edited.
3. **Submission.** `ops/submit.sh` is the controls stage's script, unchanged.
   For each manifest it ran `--dry-run` (batch script `3d86820d...`),
   `--test-only` and the submission, then started
   `scripts/record_slurm_end_states.sh` for the job (`slurm-state/`).
   - One campaign ran at a time, in the registered order.
   - Each submission came after the previous job had left the queue and its
     end state was read. Before each one, `squeue` showed no job of this
     stage pending or running.
   - So at most one VM of this stage ran at any time.
4. **Analysis.**
   - `ops/make_attempts.py` (unchanged) built each criterion's attempt map
     from the submission log (`ops/attempts-a*.json`).
   - `ops/analyze_acceptance.py`, run from the export, loaded each run
     directory with `acceptance.load` and called `acceptance.a1` (and `c4`),
     `a2`, `a3`, `a6` and `a5`.
   - It wrote each verdict, its section-12 report and per-campaign summaries
     (end state, counting problems, per-cell pass counts per setting, every
     failed trial with its reasons, retries, boots, steps, restarts, calls).
   - It only groups run directories and writes JSON. Every judgement is the
     frozen code's.
5. **Reproduction and run checks.**
   - The 9 raw run directories (914 files, 446 MB) were copied to a local
     scratch directory. Every file's SHA-256 equals its
     `raw-sha256sums.txt` entry.
   - The local export under Python 3.13 gave all 18 JSON files
     byte-identical to the host's (Python 3.10).
   - `ops/check_runs_acceptance.py` (`checks/run-checks-acceptance.json`)
     checks each of the 9 jobs: its `manifest.json` equals the rendered one
     and its canonical digest is the batch record's; batch script, tree,
     git SHA, receipt, campaign, manifest and session-plan digests agree; it
     started after row 15; no GPU in the receipt or the Slurm TRES;
     `System.qcow2` unchanged and nothing left; Slurm and the batch record
     both COMPLETED 0:0; N = 1, attempt 1, and the registered seed, layer,
     settings and repetitions.
   - Every check passed. The only IPv4 address in those files is the guest
     VM's internal NAT address in each manifest, which the first stage's
     manifests already carry.

### Operator notes

These are disclosed operator choices. None changed what a registration fixes.

- **The same export as the controls.** The suite's controls and acceptance
  campaigns ran from one source tree (`bf99a64`, tree `abbbfe6c...`).
- **One campaign at a time.** The registrations require N = 1 within each of
  these campaigns. They do not order separate campaigns, and the first
  stage ran some concurrently. This stage ran them strictly one after
  another, for two reasons:
  - A1's step p95 is the ladder's N = 1 reference, so it should measure one
    VM;
  - no trial of these criteria should fail on load from this stage itself.

  Wall-clock time was 8 h 50 min, from 15:28:50 to 00:18:44 UTC
  (2026-10-09).
- **Foreign load.** Other sessions' Slurm jobs ran on the host during some
  campaigns, recorded in each campaign's host snapshots
  (`checks/host-snapshots-acceptance.json`, `ops/host_snapshots.py`):
  - the `s1a-*` CPU jobs, 2-8 CPUs each, during A2 and A3;
  - an open-weight reviewer job on one GPU during A5 and A2.

  None ran during A1 or A6. The largest 1-minute load average seen was
  13.9, on 208 CPUs. The registrations judge foreign load only for a ladder
  rung. Here it is context.
- **A5's acceptance receipts.** A5 was given the 8 acceptance campaigns of
  this stage (section 7 names A1-A7). The 50 control campaigns are reported
  separately above.
- **A5's manifest header.** The frozen renderer writes its `--seed` value
  into the YAML header comment, so `a5-bootreset-a1.yaml` says "seed 43".
  The manifest itself is deterministic (`seeds: []`).
- **Job ids.** Each `--test-only` takes a job id, and other sessions
  submitted jobs in between. This stage's jobs are exactly 964, 968, 970,
  974, 991, 1004, 1008, 1013 and 1015 (`ops/submissions.log`).
- **Requeue.** Every Slurm record of both stages (and v1's job 768) shows
  `Requeue=1`: the VM submitter does not pass `--no-requeue`. Every record
  also shows `Restarts=0`, so no job was requeued. The lane is frozen, and
  this is noted for the longer campaigns still to come (A4, A7 and the
  ladder).

### VM time

The 9 jobs used 8.65 VM-hours, CPU only (run time times one VM):

| Criterion | VM-hours | Sized (section 9) |
|---|---:|---:|
| A5 | 0.29 | 0.3 |
| A1 | 1.46 | 1.5 |
| A2 | 1.56 | 1.6 |
| A3 | 4.51 | 4.8 |
| A6 | 0.83 | 0.9 |

With the first stage's 2.95, v2 has used 11.60 VM-hours. No GPU was
requested or used.

### Files (second stage)

| Path | What it is |
|---|---|
| `manifests/rendered/a*.yaml` | the 9 manifests as the frozen renderer wrote them and as submitted; `manifests/rendered-sha256sums-acceptance.txt` |
| `runs/<job>/` for jobs 964-1015 | `manifest.json`, `preflight.txt` (batch record), `receipt.json`, `session_plan.json` (not for A5), `slurm-<job>.out`, `raw-sha256sums.txt` (every raw file left on the host, 447 MB for the 9 jobs) |
| `slurm-state/<job>.txt` | the watcher's `scontrol show job` record of each job |
| `acceptance/a{1,2,3,5,6}-verdict.json`, `c4-verdict.json` | the frozen `acceptance.a1`/`a2`/`a3`/`a5`/`a6`/`c4` output, each with its section-12 report under `state_not_observed` (not for A5) |
| `acceptance/*-section12-state-not-observed.json` | the same section-12 reports on their own |
| `acceptance/a{1,2,3,5,6}-campaigns.json` | per-campaign summaries |
| `acceptance/a1-n1-reference.json` | A1's step and boot quantiles, the ladder's N = 1 reference |
| `acceptance/a5-after-boot-reset/` | A5 computed right after job 964, before any acceptance campaign |
| `checks/acceptance-export-and-reproduction.json`, `checks/local-render-sha256sums-acceptance.txt`, `checks/run-checks-acceptance.json`, `checks/host-snapshots-acceptance.json` | export, rendering, reproduction and run checks, and the host load per campaign |
| `ops/render_acceptance.sh`, `ops/analyze_acceptance.py`, `ops/check_runs_acceptance.py`, `ops/host_snapshots.py` | this stage's operator scripts (the render and analysis scripts are byte-identical to the copies that ran on the host) |
| `ops/submissions.log`, `ops/attempts-a*.json`, `ops/dryrun/a*` | the submission log (both stages), the attempt maps and each manifest's dry-run and test-only output |

## First stage: validity controls C2, C1 and C3

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
