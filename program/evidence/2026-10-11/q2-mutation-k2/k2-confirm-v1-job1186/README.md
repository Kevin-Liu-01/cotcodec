# K2 registered job 1186 (`k2-confirm-v1`): records, report and the parent analysis rerun

**Blind warning for the adjudication (D9, D77, D78).** Everything in this
directory and its subdirectories names checker verdicts per mutant (in the VM
and offline), and the K2-C rows name which mutants are checker candidate events
(their ids carry the operator). The rerun analysis in `analysis-with-k2/` names
labels, audit decisions and sham status like the parent's `analysis.json`. If
you are adjudicating the `q2-evaluator-mutation-v1` pool (34 items) or doing
its spot check (25 items), answer from the blind packets before reading
anything here, as for the parent results README's `sample.jsonl`,
`decisions.jsonl`, `analysis.json` and `summary.json`.

The registered `k2` job of `q2-evaluator-mutation-v1-k2` (ledger row 17, row
hash `7d03d928...`, registration SHA-256 `564f8c5c...`, `git_head_at_freeze`
`0a864682`), run once, CPU only (0 GPU-h), from an export of the freeze commit
`7d9c881af581d8004b8014570fa7c825045f01b1` (the commit that adds only the
ledger row; section 14 step 3).

## Outcome: VERIFIED

- **Fitness gate passes:** 2 of 80 K2 pairs excluded (at most 8 allowed), both
  cause (4) `vm_infrastructure_failure`.
- **K2 (the registered sample):** 78 pairs compared, 78 agree with the offline
  lock-exact verdict in both runs (41 pass, 37 fail), 0 differ, so no
  `unexplained` difference and no family dropped. No single-run pair. Compared
  per family: `compare_table` 27 of 27, `compare_pptx_files` 23 of 23,
  `compare_docx_files` 9 of 11 (the 2 excluded), `compare_line_spacing` 6,
  `compare_docx_images` 6, `check_tabstops` 3,
  `evaluate_strike_through_last_paragraph` 2, `compare_docx_tables` 1,
  `compare_csv+compare_table` 1. Not covered by K2 (no compared pair;
  descriptive): `compare_pptx_files_tolerant`.
- **K2-C (descriptive, never an analysis input):** 41 of 41 candidate events
  reproduced in the VM in both runs (the 36 false negatives fail in the VM as
  offline, the 5 false positives pass as offline); none excluded. The one pair
  in both sets (`k2:069` = `k2c:000`) agrees in both.
- **Parent analysis rerun with `--k2-report`:** the label "offline harness, VM
  fidelity unverified" becomes "VM fidelity checked (K2)", `families_dropped`
  is empty, and nothing else in `analysis.json` changes (a structural diff
  against the committed `../../../2026-10-08/q2-mutation-confirm/results/analysis.json`
  differs only at `exclusions.k2`: the label, plus `executor_commit` and
  `pairs: 80`).

### The two excluded pairs

`k2:015` and `k2:039`, both on task `51f5801c` (`compare_docx_files`, one agent
save of `notes.docx`; offline `fail` and `pass`). All 8 attempts (2 runs x 2
attempts per pair, each run re-queued once) ended the same way: the task's own
setup opens a presentation in Impress; the plan's `kill_process` sent
LibreOffice's Ctrl+Q to that window, LibreOffice had not exited after 15 s,
SIGTERM ended both processes (no SIGKILL), the candidate uploaded with the right
digest, and the reopen of `notes.docx` (`executor:agent_save:open`) got no
reply within the 180 s step bound. The records do not show the window that
blocked the open; a Document Recovery dialog after the SIGTERM (development job
1113's defect, section 3.2) fits, but is not observed. This task's shape
(another LibreOffice document open from setup, the target a Writer file) was
not among section 11's confirm-only shapes and no development job exercised
it. The exclusions count toward the gate as registered; nothing was rerun.

### Reported only (section 8)

- Attempts: 246 (242 slots plus 4 re-queues): 238 scored, 8 infrastructure
  (all `executor:agent_save:open`, task `51f5801c`).
- Save paths (per target): over the 238 scored runs, 226 postconfig saves, 12
  agent saves and 2 targets without a save; the 8 lost attempts were agent
  saves (the summary's per-attempt counts, 226, 20 and 2, include them). No
  target unsaved at the checker's read, no late write, no postconfig reply
  failure, no metric error.
- Checker observations: 692 calls over 238 runs, none retried, slow,
  undelivered or unusual (longest 0.103 s).
- LibreOffice quit by Ctrl+Q with no signal in all 218 scored runs that had it
  open (20 had no LibreOffice to close); the 8 lost attempts above are the only
  ones signalled.
- Save-time reading: 2 runs above 0.5 s, both of `k2:051` (0.93 s and 0.83 s);
  the checker still read saved bytes in both (no target unsaved at read), and
  the pair agrees. Median -0.48 s (Ctrl+S commands that sleep after the key).
- Scored run times 110.6-136.4 s (median 114.3 s); the lost attempts took
  286-289 s. The job ran 15:56:20-17:01:17 UTC (65.0 minutes).
- The confirm-only shapes of section 11 ran without exclusion: tasks
  `550ce7e7`, `6ada715d` and `c867c42d` (18 runs, all scored).
- Host: submitted at 15:56:19 UTC right after `squeue` showed no job; the
  lane's six host snapshots (start, each block, end) saw no other Slurm job.
  Preflight: no GRES (`TRES=cpu=40,mem=64G,node=1`), runc, lane exit 0, no
  labelled container left.

## What ran (section 14 step 3)

| Step | Command (host paths under `~/cotcodec-runs/stage0/q2-mutation-k2/`) | Result |
|---|---|---|
| Export | `git archive 7d9c881a` into `src/7d9c881af581d8004b8014570fa7c825045f01b1/`, `.git_sha` naming it, made read-only | 7,467 files and 27 symlinks (the commit's 7,494 entries) plus `.git_sha`; `harness/` tree digest `1e087a0e...` equals `git archive` of the commit computed on the Mac; registration SHA-256 equals row 17's; batch file `0cddd6bb...` equals the code table |
| Render | `python3 -E -s -B -m harness.q2_mutation_k2.lane render --base experiments/manifests/q2-mutation-k2/k2-confirm-v1.base.json --sample .../released/k2/k2-sample.jsonl --k2c .../k2c-candidates-confirm.jsonl --jobs <confirm-mutants-v1>/build/scoring-jobs.jsonl --sample-summary <confirm-mutants-v1>/score/k2-sample.summary.json --out manifests/k2-confirm-v1.json` | 242 slots (k2-r1 80, k2-r2 80, k2c-r1 41, k2c-r2 41); job list `9c2426b7...` and sample summary `2c0007f1...` checked |
| Validate | `lane validate manifests/k2-confirm-v1.json --source-dir .` | ok, canonical manifest `00830fde...` |
| Submit checks | `prior_k2_runs` (none: run root holds only development jobs 1113, 1122, 1130, 1159, 1163), `check_one_job`, `check_slurm` (40 CPUs, 64 GB, 360 min), `check_host` (130 candidate and context files hashed) | all passed |
| Submit | `squeue` empty, then `lane submit manifests/k2-confirm-v1.json --source-dir .` | Slurm job 1186, manifest stored as `runs/manifests/00830fde....json` |
| Report | below, on the Mac in the `ops/q2-mutation-k2` worktree at the freeze commit (Python 3.13.14) | exit 0; `freeze` check passed (one parent `0a864682`, only the ledger differs, receipt row = row 17, `harness/` tree `1e087a0e...` = receipt) |
| Parent analysis | below, from a fresh `git archive` of `7d9c881a` (`campaign pins` on it equals the parent's frozen source-tree pins, code tree `58bee019...`), Python 3.13.14, default seeds and 10,000 resamples | exit 0, empty stderr |

Report command (section 7), from the repository root:

```bash
python -m harness.q2_mutation_k2.report \
  --run-dir program/evidence/2026-10-11/q2-mutation-k2/k2-confirm-v1-job1186/run --repo . \
  --sample program/evidence/2026-10-08/q2-mutation-confirm/results/released/k2/k2-sample.jsonl \
  --k2c program/evidence/2026-10-11/q2-mutation-k2/k2c-candidates-confirm.jsonl \
  --verdicts program/evidence/2026-10-08/q2-mutation-confirm/results/released/confirm-mutants-v1/verdicts-lock.jsonl \
  --notes-summary program/evidence/2026-10-08/q2-mutation-confirm/results/released/confirm-mutants-v1/notes-summary.json \
  --out-dir program/evidence/2026-10-11/q2-mutation-k2/k2-confirm-v1-job1186/report
```

Parent analysis rerun (section 9.4: `--k2-report` added to the audit inputs as
they stand, before Kevin's answers; the parent results README's command plus
`--k2-report`):

```bash
R=program/evidence/2026-10-08/q2-mutation-confirm/results
A=program/evidence/2026-10-08/q2-mutation-confirm/audit/audit-summary
python -m harness.q2_mutation.analysis \
  --outcomes $R/released/confirm-mutants-v1/outcomes.jsonl \
  --controls-summary $R/released/controls/confirm-controls-v1.summary.json \
  --reserve-controls-summary $R/released/controls/reserve-controls-v1.summary.json \
  --audit-summary $A/audit-summary.json --decisions $A/decisions.jsonl \
  --k2-report program/evidence/2026-10-11/q2-mutation-k2/k2-confirm-v1-job1186/report/k2-report.json \
  --out analysis-with-k2/analysis.json > analysis-with-k2/analysis-stdout.json
```

Input digests of the rerun: outcomes `b1bd6a87...`, confirm controls
`1ae20605...`, reserve controls `1da42642...`, audit summary `d05a3aa0...` and
decisions `98b3bf53...` (the pre-adjudication files of
`audit/SHA256SUMS`), splits `2099792e...`, K2 report `39cd10ab...` (`report/k2-report.json`). Reproduction control: the same command without
`--k2-report`, in the same archive and interpreter, reproduced the committed
`analysis.json` (`a7c21902...`) and `analysis-stdout.json` (`31bd9013...`)
byte for byte, so the rerun's only change is K2.

When Kevin's answers exist, the analysis is rerun once more with
`--k2-report` and the post-answer `--audit-summary` and `--decisions`
(section 9.4).

## Files

| Path | What it is |
|---|---|
| `run/k2-runs.jsonl` | One `q2m-k2-run-v1` record per attempt (246): identity, status, exclusion, verdict and score, plan ops, save paths, hash checkpoints (digests only), checker-read digests, setup and postconfig replies without stdout, windows, timings |
| `run/lane-receipt.json` | The lane receipt: statuses, dispatch order, host snapshots, and `identity` (executor commit, freeze row, source tree digest, VM pins) |
| `run/manifest.json`, `run/preflight.txt` | The validated manifest as the batch file wrote it, and the batch file's preflight (digests, `.git_sha`, TRES, lane exit) |
| `report/k2-pairs.jsonl` | One row per pair (121: 80 K2, 41 K2-C) |
| `report/k2-summary.json` | Gate, outcome, per-set agreement tables, run statistics per set and pooled, receipt overlap, freeze check, input digests |
| `report/k2-report.json` | The parent analysis's `--k2-report` (written because the gate passes) |
| `analysis-with-k2/analysis.json`, `analysis-stdout.json` | The parent's registered analysis rerun with `--k2-report` |
| `SHA256SUMS` | Every file here |

Not committed (they stay on the host, as the study's packets did): the run
directories' checker-input captures and container logs, the mutant documents,
and the Slurm output file.
