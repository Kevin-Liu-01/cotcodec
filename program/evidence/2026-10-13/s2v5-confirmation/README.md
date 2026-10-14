# S2 v5 development confirmation (Slurm 1278 and 1291)

Registration draft: `program/preregistrations/s2-arabic-cua-locale-v5.md`, section "v5 development:
step 0 and the confirmation (a pre-freeze gate)", under decisions D94 and D96. This is development
under the unfrozen id `s2-arabic-cua-locale-v5`, which has no ledger row. Nothing here is frozen,
and nothing here is a K1 result.

The confirmation had one attempt: two jobs, each submitted once. Neither was rerun, and no target
or file was changed after either job.

## Result: the reading passes, so the draft goes to review and audit

`ap_delta_v5.py confirm-read` over both job directories returned, verbatim:

    {"pass": true, "decision": "PROCEED to the pre-freeze audit (D96)"}

Its full output is `confirm-reading.json` (SHA-256 `bb2adbe7...`), with an empty `problems` list.
The reading uses harness/q2's own acceptance code for each campaign: `acceptance.load`,
`acceptance.counting_problems` (section 6.1), `acceptance.realized` and `acceptance.expected` (the
plan), `acceptance.outcomes` and `acceptance.entry_status`. It also checks the cells file each
campaign read.

| Image | Job | What ran | Cells file read | Entries | Trials passed | Every entry 5 of 5 | Counts (6.1) |
|---|---:|---|---|---:|---:|---|---|
| ER | 1278 | full A6 | `harness/s2_locale/canary_v5/suite_cells-ER.json`, with its override record | 60 | 300 of 300 | yes | yes |
| AR | 1278 | full A6 | `harness/s2_locale/canary_v5/suite_cells-AR.json`, with its override record | 60 | 300 of 300 | yes | yes |
| PL | 1291 | full A6 | q2's `suite_cells.json` | 60 | 300 of 300 | yes | yes |
| E | 1291 | Writer's two pointer composites | q2's `suite_cells.json` | 2 | 10 of 10 | yes | yes |
| A | 1291 | Writer's two pointer composites | q2's `suite_cells.json` | 2 | 10 of 10 | yes | yes |

### Writer's pointer composites, per image

`writer:drag_select_word` is the entry that failed v4's K1 on ER (job 1264, read-back
"Ykeep word keep", D93). It is expected to read back "keep Y keep": the drag selects "word", and
typing "Y" replaces it.

| Image | Targets (from the cells file the session config names) | `drag_select_word` | `triple_click_line` |
|---|---|---|---|
| ER | drag (751, 293) to (779, 293) in 500 ms; triple-click (789, 293) | **5 of 5, "keep Y keep" on every boot** | 5 of 5, "X" |
| AR | drag (751, 294) to (779, 294) in 500 ms; triple-click (789, 294) | **5 of 5, "keep Y keep" on every boot** | 5 of 5, "X" |
| PL | q2's: drag (680, 292) to (709, 292); triple-click (718, 292) | 5 of 5, "keep Y keep" | 5 of 5, "X" |
| E | q2's | 5 of 5, "keep Y keep" | 5 of 5, "X" |
| A | q2's | 5 of 5, "keep Y keep" | 5 of 5, "X" |

So a drag at step 0's shifted target selects "word" on ER and AR, on each of 5 cold boots. Step 0
could not observe this because it ran only q2's targets. The full A6 also passes on AR and PL,
where it had never run before (v4's K1 stopped after ER).

How the shifted targets reached the runner. The trial records do not carry coordinates. The runner
reads the targets from the cells file that its session config names, and these records show that
each ER and AR session got the v5 file:

- every session config, `cycles/config-NN.json`, names `cells_path`
  `/src/harness/s2_locale/canary_v5/suite_cells-ER.json` (or `-AR.json`);
- the override record `cells_override.json`, which `ap_delta_v5.py q2-driver` writes before the
  driver starts, names that file and its pinned SHA-256 (`464c9ab2...` for ER, `b81b63c6...` for AR);
- the campaign manifest's `workload.cells_sha256` is that digest, and harness/q2's driver checks it
  before any session;
- `confirm-read` checks all three.

The PL, E and A sessions name q2's `suite_cells.json`, and their campaigns have no override record.
`confirm-summary.json` lists every Writer composite trial with its session, sequence number,
expected text and read-back.

The triple-click's read-back ("X", the whole line replaced) cannot detect an x error, as before.
Under v5 it is aimed at "this" on ER and AR.

## The jobs

Both jobs ran CPU only, through `infra/slurm/host-single-node/s2v5-apdelta.sbatch` (SHA-256
`df6b936d...`), one VM at a time. Each request was `--cpus-per-task=5 --mem=9G` with no GRES, and
Slurm's TRES was `cpu=6,mem=9G,node=1` with no GPU.

| Job | Part | Limit | Submitted (UTC) | Ran (UTC) | Run time | Slurm end | Batch end line |
|---:|---|---:|---|---|---|---|---|
| 1278 | 1: ER, AR | 434 min | 2026-10-13 22:00:32 | 22:00:33 to 23:40:05 | 1 h 39 min 32 s | COMPLETED 0:0 | `lane_exit=0 labelled_containers_left=0` |
| 1291 | 2: PL, E, A | 366 min | 2026-10-14 01:24:52 | 01:24:52 to 02:22:42 | 57 min 50 s | COMPLETED 0:0 | `lane_exit=0 labelled_containers_left=0` |

Per campaign (from the receipts; `job-facts.json`):

| Campaign | Wall time | Cold boots (max) | Sessions | Image SHA-256 before = after |
|---|---|---|---|---|
| ER | 22:00:34 to 22:50:08 (49.6 min) | 5 (17.9 s) | 5 of 60 trials, 9.7-9.9 min each | `262fe709...` = |
| AR | 22:50:09 to 23:40:05 (49.9 min) | 5 (17.3 s) | 5 of 60, 9.8-10.0 min | `77cd9a2a...` = |
| PL | 01:24:53 to 02:14:43 (49.8 min) | 5 (17.3 s) | 5 of 60, 9.8-9.9 min | `5a4102ee...` = |
| E | 02:14:43 to 02:18:41 (4.0 min) | 5 (17.9 s) | 5 of 2, about 40 s each | `51e47abb...` = |
| A | 02:18:42 to 02:22:42 (4.0 min) | 5 (17.3 s) | 5 of 2, about 40 s each | `12500989...` = |

Every campaign meets the q2-action-path-v2 section 6.1 conditions:

- driver exit 0 and no labelled container left;
- `infra_gates_pass` true;
- the image unchanged (`qcow2_unchanged` true);
- no GPU, no published port, every container removed, and no leaked or dangling volume;
- no unreadable run file.

There was no guest-server restart and no infrastructure failure. All 50 host snapshots, taken
before and after each session, saw no foreign Slurm job. In all, about 2.6 VM-h ran (157 minutes of
campaign wall time). The draft estimated about 2.8.

The Slurm end states are the `scontrol show job` text that harness/q2's own watcher,
`scripts/record_slurm_end_states.sh`, run from the export, saved when each job reached its final
state, in `RUN_DIR/slurm-state/JOB.txt`. That is where `acceptance.load` looks, so the reading
includes the Slurm end state.

## Scheduling

The rules followed were D85, D87, D94 and D96, and the brief: one job at a time, each on an empty
queue, never during a successor E session, and no file staged on the host during one.

- E3's later end was 08:36:10Z (step-0 record), so E4 could start from 20:41:10Z. Neither part's
  limit (434 and 366 minutes) could end before then, so neither could go in before E4.
- E4's 9B pair (1272, 1274) ran from 20:41:28Z to 21:20:17Z. Its 4B pair (1275, 1277) ran from
  21:21:45Z to 21:58:06Z (1275's lane `t_end` was 21:58:01Z). All four ended COMPLETED 0:0, per
  E's own `scontrol` records. E's post-session steps (DR0: not fired; the collect archive) were done
  by 21:59:40Z.
- E4 is E's last session (E1-E4, registration section 5.3). So no E session remained, and both
  parts were submitted with `--no-e-deadline`.
- Part 1 (1278) was submitted at 22:00:32Z on an empty queue. `ops/pre-submit-p1.txt` holds the host
  snapshot and E4's four end states.
- E's analysis jobs then went in 9 s after 1278 ended: 1279 `q2e-glmm`, 1280-1287 `q2e-rescore-*`,
  1288 `q2e-report`, 1289 `q2e-s15` and 1290 `q2e-joint`. They ran from 23:40:15Z to 01:21:50Z.
  Part 2 waited for an empty queue, and then for a further 3 minutes to see whether E submitted
  anything else. It went in at 01:24:52Z (`ops/pre-submit-p2.txt`).
- No confirmation job overlapped any other job.

## Source and manifests

- **Source tree run by the jobs.** A `git archive` of `f24557aa555987157b5b75049ec1cb1b8e0a81a2`, the
  commit the manifests name (`git_sha`, `source.host_dir`). It was piped over `ssh` to GNU tar 1.34
  into `~/cotcodec-runs/stage0/s2v5/confirm/src/f24557aa.../` at 18:05Z on 2026-10-13. After that,
  `.git_sha` was written and the tree made read-only.
  - It holds 8,640 files and 27 symlinks. Its tree digest (`tools/treedigest.py`) is `5b025dd7...`,
    equal to a local export of the same commit.
  - There is no AppleDouble file and no `__pycache__`.
  - harness/q2's `source_tree_sha256` is `896c46a8...`. That is what the manifests name, what both
    `preflight.txt` files record, and what each receipt records.
- **Manifests.** These were read from a `git archive` of
  `26a9477cfa12da43f82e5fc78314804089cc0949`, the draft's head, staged beside the source tree in the
  same way: 8,644 files, tree digest `e2b361d2...`.
  - `experiments/manifests/s2v5/confirm-a6-v1-p1.json`: file SHA-256 `c2ee9614...`, canonical digest
    `1d7289f19f4d551cbc2f306a13b939432abcf592ef471840354ec154f209c9d5`.
  - `confirm-a6-v1-p2.json`: file SHA-256 `3bf04212...`, canonical digest
    `3e75de8cb3d93426e602e3765a93770ec3657682a2b25069676127df2f7e5fc3`.
  - Each job's `manifest.json` has the same canonical digest.
  - Before E4, both manifests passed `ap_delta_v5.py validate` and `submit --dry-run` on the host
    (18:06Z).
- **Why two exports.** The brief asked for an export of `26a9477c`. The manifests and the draft's
  freeze procedure (step 2) require the export of the commit the manifests name. `ap_delta_v5` refuses
  a source tree whose `.git_sha` differs from the manifests' `git_sha` and whose path differs from
  `source.host_dir`.
  - `26a9477c` differs from `f24557aa` only in the two manifests, the draft registration, the
    freeze-rehearsal record and `tests/conftest.py`. `harness/` (`896c46a8...`) and `infra/`
    (`88954410...`) are identical in both exports.
  - So the jobs ran exactly the code at `26a9477c`, from the tree the manifests pin. This follows
    step 0's precedent: manifest from the later commit, source from the commit it names.

## Reading and cross-check

- On the host, from the `f24557aa` export, at 02:23Z:
  `python3 -E -s -B -m harness.s2_locale.ap_delta_v5 confirm-read RUN_ROOT/1278 RUN_ROOT/1291
  --source-dir EXPORT --out confirm-reading.json`.
- On the Mac, the same command over the committed copies in this directory. It was run once with
  the local `f24557aa` export and once with the local `26a9477c` export (Python 3.13). Both outputs
  equal the host's `confirm-reading.json`.
- An interim read of 1278 alone, on the Mac, before part 2, passed ER and AR. It reported only the
  three campaigns that had not yet run. It decided nothing.

To read again: `python -m harness.s2_locale.ap_delta_v5 confirm-read
program/evidence/2026-10-13/s2v5-confirmation/1278 program/evidence/2026-10-13/s2v5-confirmation/1291
--source-dir EXPORT --out reading.json`, with EXPORT an export of `f24557aa` or any later commit that
leaves `harness/` unchanged.

## Files

- `confirm-reading.json`: the registered reading.
- `confirm-summary.json`: `tools/summarize.py`, a descriptive view. It gives per-image entry counts,
  the cells file each session named with its Writer targets, and every Writer composite trial.
- `job-facts.json`: `tools/facts.py`. It gives job and campaign times, Slurm end states, receipt
  gates, image digests, boots and session times.
- `1278/`, `1291/`: each job directory, copied whole from the host run root
  `~/cotcodec-runs/stage0/s2v5/confirm/runs/`. The canary composites saved no screenshots, so nothing
  stayed behind. Each holds:
  - the job's `manifest.json`, `preflight.txt` and `apdelta-receipt.json`, and `slurm-state/JOB.txt`
    from the q2 watcher;
  - per campaign, `apdelta.json`, `manifest.json`, `preflight.txt`, `receipt.json`,
    `session_plan.json` and, for ER and AR, `cells_override.json`;
  - per session, under `cycles/`, `config-NN.json`, `cycle-NN.json`, `cycle-NN.trials.jsonl`,
    `record-NN.json` and `vm-NN.log`.

  The session configs carry the VM-internal guest address 20.20.20.21, as step 0's records do.
- `slurm/`: the two jobs' Slurm output.
- `ops/`: the host snapshots taken before each submission, the submit results with the sbatch argv,
  and the host-side operator log (`host-ops.log`). `ops.log` is the operator's own timeline.
- `tools/`: the helpers used.
  - `submit_confirm.sh` is the guarded submission, run through `ssh bash -s`. It refuses unless the
    queue is empty and E4's 4B pair has final end states. It runs `ap_delta_v5.py submit` and starts
    the q2 watcher.
  - `collect.sh` copies a finished job.
  - `poll_e.sh` and `poll_job.sh` are the read-only polls.
  - `treedigest.py` gives the export digests.
  - `summarize.py` and `facts.py` are described above.

## Disclosures

- **Exports.** The source tree is the export of `f24557aa`, not of `26a9477c` as the brief worded it.
  The reason is in "Source and manifests". The code is identical in both.
- **Staging.** Both exports were staged at 18:05-18:06Z on 2026-10-13, in the E3-E4 gap, before E4
  began at 20:41:28Z. Nothing was written to the host during E4 except by E itself. The operator's
  read-only polls (`squeue`, listings of E's pair directories) continued during E4.
- **E's analysis.** E's analysis jobs waited for part 1 to end: they went in 9 s after it, so part 1
  delayed them by up to about 1 h 40 min. Part 2 then waited for them. No rule was broken: E4 had
  ended, and no E session remained. The interleaving is recorded here.
- **The q2 watcher** wrote `slurm-state/JOB.txt` inside each job directory, where
  `acceptance.load` reads it. This is harness/q2's own convention for a campaign's run directory, one
  level up. It adds a file the batch script did not write.
- **A digest typo** in the draft owner's report: it gave part 2's canonical digest as
  `3e75de8c3d93426e...`. The correct value is `3e75de8cb3d93426e...`, as the manifest gives and as
  the job used. The registration gives only the prefix `3e75de8c...`, which is correct.
