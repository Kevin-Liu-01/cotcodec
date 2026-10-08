# q2-action-path-v2: decision D45, the narrowed judge rule and its repeated development (2026-10-08)

**Development evidence only (seed 42, never evidence for any criterion).**
Decision D45 narrows D43's judge rule: a key event the XRecord tap recorded
without Mod2 (the lock bit the entry guard guarantees) is read without its
modifier state only when a key press recorded with Mod2 comes before it in
the same window; otherwise its state is judged as recorded. It applies the
same rule inside C3's stream signature and earlier-attempt comparison, and
has the analysis produce section 12's report of every event read without its
state. `q2-action-path-v2.md` section 27 reports this bundle; sections 4.4,
5, 8 (C2, C3, C4), 10, 12, 24 and 26 and design decisions 47-49 state the
rule. D43's own bundle is `../q2-action-path-v2-d43/`.

## Result

1. **The code (`c74eae0`).** `verdict.py`: `modifier_state_observable`
   takes the condition on the preceding processed press, and its docstrings
   state what the rule still does not check (a grab that activates inside
   an entry after a processed press is taken to be the shell's).
   `acceptance.py`: C2's reading of the tap window and C3's comparison read
   the state by the same rule (`tap_state_unread`, `_stream`,
   `_events_equal`); every criterion's analysis returns
   `state_not_observed_report` (each event read without its state, with its
   offset from the preceding processed press and that press's keysym; each
   event without Mod2 that no processed press preceded). The prediction
   file's `d43_judge` note and `chord_super_d` reason name D45.
2. **On real records** (`tests/test_q2_d43_judge.py`): the 280 development
   events without Mod2 (the scan's 172 and job 830's 108) are still read
   without their state, and the judge reads exactly those; job 785's
   `chord_super_d` with every key state 0 (a grab already active before the
   entry, section 27 case 6) now fails, C4 disagrees, C2's reading fails and
   the report lists it; the C3 slow-answer probe (job 785's `chord_super_d`
   with the three events after Super_L at state 0) now leaves M12 and M13 on
   H-OSW-fixed equivalent and C3 passing, in a mutant's counting attempt, an
   earlier attempt or the reference run, while a processed `d` press without
   Mod4 still makes M12 a survivor; the dropped-modifier records (jobs
   832/833 and 847/848) still fail.
3. **Development repeated at `c74eae0`** (jobs 845-854, all COMPLETED 0:0,
   gates passed, `System.qcow2` unchanged, no GPU, 2.4 VM-hours): every
   cell's PASS count, failure reasons and number of trials with an event
   read without state equal those of the D43 job it repeats (830-839),
   except one trial of job 851. The number of events read without state is
   not equal in every cell (it counts each trial's events the shell's grab
   held queued); see the first item below.
   - L0-raw sample (845): 151 of 180, as 830; 108 events read without state
     in the four shell chords, as 830, in all ten trials of each chord,
     every one 0-3 ms after a processed press of its own chord (the grab
     key's, except one `chord_super_d` trial whose `d` press was processed
     with Mod4 1 ms after Super_L and only its two releases were queued).
     Per entry (`section12-report.json`, `by_entry`):

     | Entry | 830 events | 845 events | Trials (each) |
     |---|---:|---:|---:|
     | `chord_super_d` | 30 | 29 | 10 |
     | `chord_alt_f4` | 18 | 19 | 10 |
     | `chord_alt_tab` | 20 | 20 | 10 |
     | `chord_ctrl_alt_shift_r` | 40 | 40 | 10 |
     | all four | 108 | 108 | 40 |

     `chord_super_d`: three events queued per trial (the `d` press and
     release, the Super_L release) but in 845's one trial above, which had
     two. `chord_alt_f4`: the F4 release queued in every trial, and the
     Alt_L release too except in one trial of 845 and two of 830, where it
     was recorded with its state (Mod1 and Mod2) and judged on it.
   - L0-fixed sample on 8 VMs (846): 180 of 180, nothing read without state.
   - Negative case (847 `omit`, 848 `release_first`): 0 of 140, nothing read
     without state, C4 disagrees in all 140; 848 repeats 833's 22 lost-focus
     post checks.
   - Final runs as 703-708 (849-854): 52/56 (the injected restarts), 400/400,
     799/800, 194/198, 178/186 (only the outside-spec R cells), 60/60; C4
     140/140 and 280/280; step p95 2.71 s and 2.77 s.
   - Job 851's one failure: an unprovoked guest-server restart during the
     `/accessibility` call of `drag_vertical` in its ninth session (accessibility
     setting; the retry delivered; the unit's restart counter 1 to 2); the
     trial failed with `guest_server_restart` alone, a restart-only trial
     that A1-A4 and the ladder excuse (D30, D33). It is the lane's second
     unprovoked restart after run 622's, and the only one in the 2,726
     accessibility calls of jobs 830-839 and 845-854 outside the
     fault-injection runs 834 and 849.
   - 4,394 guard checks read Mod2; the only guard violations were the 22
     lost-focus post checks of job 848.
4. **Section 12's report from the analysis** (`section12-report.json`,
   `ops/section12_report.py` run from the export of `c74eae0` over v1's C2
   job 768 and every v2 run): events read without their state in job 768
   (54), 784 (110), 830 (108) and 845 (108), none elsewhere; no event without
   Mod2 that no processed press preceded, in any job.

## Runs (seed 42, CPU only, `vm-campaign.sbatch`, at `c74eae0`)

| Job | Campaign | Repeats | VMs | Trials | PASS | Run time |
|---|---|---|---:|---:|---:|---|
| 845 | `q2ap-v2-d45-l0raw-sample-v1` | 830 | 1 | 180 | 151 | 7 min 26 s |
| 846 | `q2ap-v2-d45-l0fixed-sample-n8-v1` | 831 | 8 | 180 | 180 | 3 min 10 s |
| 847 | `q2ap-v2-d45-drop-omit-v1` | 832 | 1 | 70 | 0 | 3 min 57 s |
| 848 | `q2ap-v2-d45-drop-release-first-v1` | 833 | 1 | 70 | 0 | 5 min 52 s |
| 849 | `q2ap-v2-d45-l0-restart-v1` | 834 (703) | 1 | 56 | 52 | 4 min 18 s |
| 850 | `q2ap-v2-d45-l0-fixed-v1` | 835 (704) | 1 | 400 | 400 | 18 min 23 s |
| 851 | `q2ap-v2-d45-l0-fixed-n8-v1` | 836 (705) | 8 | 800 | 799 | 6 min 8 s |
| 852 | `q2ap-v2-d45-hosw-fixed-v1` | 837 (706) | 1 | 198 | 194 | 10 min 32 s |
| 853 | `q2ap-v2-d45-hga-v1` | 838 (707) | 1 | 186 | 178 | 9 min 54 s |
| 854 | `q2ap-v2-d45-canary-v1` | 839 (708) | 1 | 60 | 60 | 10 min 45 s |

How they ran: `git archive c74eae0` extracted read-only to
`~/cotcodec-runs/q2-action-path-v2/dev/src/<sha>` on the host (tree digest
`4f66fe7e...`, the same locally and on the host; the registration's digest
at that commit `b01f554f...`); the manifests
(`experiments/manifests/q2-action-path-v2/d45-*.yaml`, written by
`ops/make_dev_manifests.py` from that commit, each equal to its `d43-*`
manifest but for its names, commit, export and registration digest) passed
`scripts/submit_vm_campaign.py --dry-run` from the export (batch script
digest `3d86820d...`, the frozen one) and were submitted from it
(`ops/submissions.log`); `scripts/record_slurm_end_states.sh` recorded each
end state (`slurm-state/`).

## Files

| Path | What it is |
|---|---|
| `d45-development-runs.json` | `ops/summarize.py` over jobs 845-854: end states, gates, digests, per-cell PASS counts, reasons, C4, `state_not_observed`, guard violations and modifier states; every key event read without its state with its offset from the grab key and (D45) from the preceding processed press; every key event without Mod2 no processed press preceded (none) |
| `section12-report.json` | `ops/section12_report.py`: `acceptance.state_not_observed_report` at `c74eae0` per job, over job 768 and jobs 784-787, 830-839 and 845-854 |
| `records/trials-d45-dev.json` | `ops/extract_trials.py` (D43's script, unchanged): every chord trial of jobs 845-848, as the judge's input |
| `runs/<job>/` | `manifest.json`, `preflight.txt` (batch record), `receipt.json`, `session_plan.json`, `slurm-<job>.out`, `raw-sha256sums.txt` (every raw file left on the host) |
| `slurm-state/<job>.txt` | the watcher's `scontrol show job` record |
| `ops/make_dev_manifests.py` | writes and validates the ten manifests (D43's, retargeted to `c74eae0`) |
| `ops/summarize.py` | D43's summary with D45's two reports added |
| `ops/submissions.log` | the submission log |
| `checks/` | the checks at the commit that recorded this bundle (`checks-e09e362.json`) and at the commit that corrected section 27's and item 3's wording on the events read without state (`checks-50f3861.json`) |

The summary, extraction and report scripts ran on the host with the system
Python (the report from the read-only export, so it is the analysis's own
code), and the committed copies are the ones that ran (same SHA-256 there).
Raw outputs stay on the host under `~/cotcodec-runs/q2-action-path-v2/dev/runs/`;
the earlier run directories were only read.
