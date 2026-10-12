# Q2 successor E (`q2-stage1-successor-e-v1`, DRAFT): pre-freeze gates G-E4 and G-E5

The two CPU-only gates of the registration's section 4.1 that run on the host before the
freeze. **Both passed.** No GPU, no model and no confirm-split task was used: three CPU-only
Slurm jobs (no GRES) ran from a read-only export of the draft commit `8a23a483`, each
submitted only when the whole Slurm queue was empty, one at a time. The registration is
not frozen; the G-E6 audit and the program's sign-off (section 21) are still open.

| Gate | Jobs | Verdict |
|---|---|---|
| G-E4, the development smoke of E's lane and episode entry point | VM job 1206; offline rescoring job 1208 | passed: 4 of 4 slots scored with session `E1`, records accepted by E's `records.validate`, lane receipt without an error, offline rescoring equal to the live score on 4 of 4 |
| G-E5, the unchanged `glmm.R` on synthetic rows of E's shape | CPU job 1210 | passed: both fits converged with positive-definite Hessians; the fit is reported as `glmm.R` wrote it |

`check_gates.py` checks every record of this directory with E's code (`harness.q2_stage1e`)
and S1a's, and writes `gates-check.json`. It reads only this directory and the repository's
committed code.

## How it ran

- **Export.** `git archive 8a23a483dc39f6e34aa52dca75a9a5e106b18375` into
  `~/cotcodec-runs/stage0/q2-stage1e/src/8a23a483dc39f6e34aa52dca75a9a5e106b18375/` on the host,
  with `.git_sha` naming the commit, made read-only. Its `harness/` tree digest
  (`c652b14f...`, `harness.q2.vm.manifest.source_tree_sha256`) equals that of a `git archive` of
  the same commit computed on the Mac. The manifest, `q2e-vm.sbatch`, `lane.py`, `driver.py`
  and `records.py` in the export hash to the registration's section 23 table.
- **Quiet host.** Other workstreams held the queue for about two hours (S2 v4's development
  smoke 1201, a zinv reserve job 1202, R04's score jobs 1203 and 1204, S2 v4's CPU job 1207,
  a rehearsal job 1209). Each of E's jobs was submitted by a loop that polled `squeue` every
  2 s and called `sbatch` only on an empty queue (`scripts/*.sh`, each run as one command of at
  most about four minutes). After each submission the queue held only E's job, and the VM
  lane's three host snapshots (start, block, end) saw no foreign Slurm job. R04's next job
  (1211) started after job 1210 had ended.
- **Branch.** `main` moved to `2b8fadc7` (D83, D84, the Q2 report revision; no ledger change)
  while the jobs ran. It was merged into the branch (`2f278e81`) before the slots were filled;
  E's code and the exported commit's code are identical.

| Job | What | Submitted (UTC) | Ran | Slurm state |
|---|---|---|---|---|
| 1206 | `python3 -m harness.q2_stage1e.lane submit experiments/manifests/q2-stage1e/dev-smoke-v1.json --source-dir .` from the export; `q2e-vm.sbatch`, 8 CPUs, 16 GB, 60 min limit | 23:06:59 | 23:07:00-23:14:38 (7 min 38 s) | COMPLETED, exit 0 |
| 1208 | `s1a-cpu.sbatch` in the metric image `sha256:2006c1a9...`: `python -m harness.q2_stage1.rescore capture --run-dir /ro/run ...` on run 1206 (S1a's G0 item 6 command, as in S1a's job 983) | 23:31:19 | 2 min 3 s | COMPLETED, exit 0 |
| 1210 | `s1a-cpu.sbatch` in the GLMM image `sha256:b15584f3...`: `Rscript harness/q2_stage1/glmm.R synthetic-e-k113.csv glmm-synthetic-e-k113.json 200 42`, exit code captured | 23:35:11 | 23:35:11-23:49:52 (14 min 41 s) | COMPLETED, exit 0 |

## G-E4: the development smoke

The registered manifest `experiments/manifests/q2-stage1e/dev-smoke-v1.json` (SHA-256
`3d215fac...`, canonical `97bac56e...`): the scripted fake engine of S1a's smoke (a click,
then `terminate(success)`), V = 1, the two dev-split tasks of S1a's job 978 (`2b94c692`,
`01b269ae`) under both harnesses, session `E1`, rerun 1.

- **Records** (`ge4/episodes.jsonl`): 4 of 4 slots `scored` on attempt 1, sessions `E1`,
  rerun 1, no infrastructure type, no `IRError`, no metric exception, no guest-server restart,
  no GPU device seen. E's `records.validate` accepts every record; S1a's `records.validate`
  refuses every one ("unknown session or rerun"), as section 5.5 says. A scored record with
  session `E1` exists, so E's entry point (`harness.q2_stage1e.driver`) ran: S1a's driver
  refuses that label at its final check.
- **Each episode**: cold boot 18.3 s, offline setup 11.4 s (two steps, every reply HTTP 200),
  the guard's warm-up 0.14-0.16 s, the 60 s settle, two steps (the click and `terminate`), the
  20 s settle, `DesktopEnv.evaluate()` 1.4-1.9 s, the capture (every result getter `ok`), the
  postconfig replies (HTTP 200, no failure) and teardown. Every screenshot and checker read was
  delivered on its first attempt (at most 0.1 s). Slot occupancy 113.4-114.4 s. The live score
  is 0 on all four, as in S1a's smoke (the scripted click does not solve either task).
- **Lane receipt** (`ge4/lane-receipt.json`): `statuses` `{"scored": 4}`, 4 records, not
  stopped, no `error`. Preflight (`ge4/preflight.txt`): the batch file is section 23's
  `q2e-vm.sbatch` (`2d27bbe5...`), the source is `8a23a483`, TRES `cpu=8,mem=16G` (no GRES),
  Docker's default runtime `runc`, lane exit 0, no labelled container left.
- **Offline rescoring** (`ge4/rescored-1208.jsonl`): one row per scored episode with the same
  `state_sha256` as its record; `raw`, `raw_state`, `corrected` and `corrected_state` are 0 on
  all four, `live_offline_match` is true on 4 of 4, and no row has an error. The corrected
  comparator applies to `2b94c692` (`compare_pptx_files`) and not to `01b269ae`.

What G-E4 does not reach (section 22, disclosure 10): the `e` purpose's own checks (prior jobs
by digest, the session gap, the engine argv and the Slurm limit) first run on the host in
E-9B-E1.

## G-E5: the GLMM on E's shape

Input `ge5/synthetic-e-k113.csv`: `python -m harness.q2_stage1e.analysis glmm-synthetic --out
...` (113 tasks, seed 42): 1,808 rows (2 sizes x 113 tasks x 2 harnesses x 4 sessions x 1
rerun), sessions nested in size (`9B:E1`), from S1a's synthetic generative model
(`glmm.SYNTHETIC_TRUTH`). Generated on the host from the export (numpy 1.21.5) and on the Mac
from a `git archive` of the same commit (numpy 2.5.2): both SHA-256 `41d87779...`.
`check_gates.py` regenerates it byte for byte with E's code.

`glmm.R` (S1a's, SHA-256 `e3ea337c...`, section 20 of S1a) ran unchanged with 200 parametric
bootstrap refits and seed 42, as S1a's acceptance job 984 did; R 4.4.2, glmmTMB 1.1.10, TMB
1.9.16; the R package lock copied from the image is S1a's (`abb8871d...`). R wrote nothing to
its log; the exit code file holds 0.

| | Full model | Reduced (without `(1\|task:harness)`) |
|---|---|---|
| Optimizer | code 0, "relative convergence (4)" | code 0, "relative convergence (4)" |
| Hessian positive definite | yes | yes |
| Log-likelihood (df) | -1,041.37 (12) | -1,058.42 (11) |

| Variance component | Estimate | Generating value | Latent share (95% bootstrap interval) |
|---|---:|---:|---|
| task | 1.334 | 2.25 | 0.238 (0.130-0.323) |
| task:size | 0.0058 | 0.09 | 0.001 (0.000-0.023) |
| task:harness | 0.974 | 1.00 | 0.174 (0.089-0.256) |
| task:size:harness | ~0 | 0.04 | 0.000 (0.000-0.019) |
| session | ~0 | 0.01 | 0.000 (0.000-0.004) |
| harness:session | ~0 | 0.0025 | 0.000 (0.000-0.004) |
| task:session | ~0 | 0.09 | 0.000 (0.000-0.000) |
| task:harness:session | ~0 | 0.09 | 0.000 (0.000-0.000) |

- Bootstrap: 200 refits used, 0 failed, 42 not converged (reported, not dropped; job 984 also
  reported 42 of 200 on S1a's shape).
- Fixed effects: intercept -1.03 (generating -1.0), size 9B +0.55 (+0.5), harness H-OSW-fixed
  -0.01 (0), interaction +0.08 (0).
- Likelihood-ratio test of `(1|task:harness)`: chi-square 34.1 on 1 df, p 5.2e-9,
  boundary-corrected 2.6e-9; both fits converged.
- As section 11 says, with one episode per (task, harness, session) the
  `(1|task:harness:session)` term has one observation per level and is not identified apart
  from the Bernoulli variance; here it is estimated at about 0, and so is task:session. The
  task variance comes out below its generating value (1.33 against 2.25) on this one data set.
  The GLMM is secondary: none of this changes a registered rule.

## Files

| File | What |
|---|---|
| `check_gates.py`, `gates-check.json` | the check of both gates with E's code; `gates-check.json` was written at `2f627aed` (the commit that added this directory's records), `harness/` clean, Python 3.13.14, and lists every input's SHA-256 |
| `ge4/manifest.json`, `ge4/preflight.txt`, `ge4/lane-receipt.json`, `ge4/episodes.jsonl`, `ge4/submit-1206.json`, `ge4/slurm-1206.out` | job 1206: the lane's canonical manifest copy, the batch preflight, the receipt with its host snapshots, the four episode records, the submission (argv and stored manifest digest) and the Slurm output |
| `ge4/rescored-1208.jsonl`, `ge4/receipt-1208.json`, `ge4/rescore-submit-1208.json`, `ge4/slurm-1208.out` | job 1208: the rescored rows, the CPU lane's receipt (no GPU, no network, no `/dev/nvidia*`), the submission and the Slurm output (library warnings only) |
| `ge5/synthetic-e-k113.csv`, `ge5/synthetic-e-k113.truth.json` | G-E5's input and its generating values |
| `ge5/glmm-synthetic-e-k113.json`, `ge5/glmm.exit`, `ge5/glmm.log`, `ge5/r-packages.json`, `ge5/r-packages.sha256`, `ge5/receipt-1210.json`, `ge5/submit-1210.json`, `ge5/slurm-1210.out` | job 1210: `glmm.R`'s output as written, its exit code and (empty) log, the image's R package lock and its digest, the CPU lane's receipt, the submission and the (empty) Slurm output |
| `scripts/ge4-wait-submit.sh`, `scripts/ge4-rescore-wait-submit.sh`, `scripts/ge5-glmm-wait-submit.sh` | the operator scripts that submitted each job only on an empty Slurm queue (run on the host from `~/cotcodec-runs/stage0/q2-stage1e/gates/`) |

Raw step logs, screenshots, captured final states and fake-engine replies stay on the host
under `~/cotcodec-runs/stage0/q2-stage1e/runs/1206/` (section 20). No host address is
recorded; the one address in `ge4/manifest.json` is the guest's inside its `--network none`
namespace, as in the committed manifest.

## Reproduction

From the repository root, with the project's Python:

    python program/evidence/2026-10-11/q2-stage1-successor-e/gates/check_gates.py --out OUT.json

`OUT.json` equals `gates-check.json` except for `provenance.checked_at_commit` when run at a
later commit.
