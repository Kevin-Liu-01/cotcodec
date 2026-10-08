# q3-dense-headroom-precheck-v2: second timing job of the fixed 4B path (D42 (ii), 2026-10-08)

Branch `stage0/q3-dense-v2` (main `18fe252`, D42, merged in at `175d35e`).
Registration `program/preregistrations/q3-dense-headroom-precheck-v2.md`:
DRAFT, not frozen. Nothing here was frozen against the real ledger (SHA-256
`1052d58b...` before and after every simulation) and nothing was pushed. GPU
use: one job, Slurm 810, 162 s on one H100 (0.045 GPU-h physical). Every
other host job was CPU only.

## What D42 asked for and what was done

| D42 item | Done | Evidence |
|---|---|---|
| (ii) one `attention_backend_check` at the start of the timing profile, so the lane's exact start-up (cuDNN's attention on, then off) runs on the GPU | `87242fa`: `Job.timing_run` calls the lane's own `attention_backend_check` after `load()` and before any unit, records it with the backend flags before and after and its start time; a failing check writes the timing receipt (`TIMING_FAILED_BACKEND_CHECK`) and ends the job as it would end the lane. The doctor's `timing_profile` case checks it ran first and left cuDNN off | `precheck/` (the case in image 801 with the new files mounted: PASS), `doctor/doctor-cpu-image-87242fa.*` (12/12), `timing-810/` |
| (ii) a fresh timing run root and template, accounted separately | template `q3-dense-headroom-v2-timing-2-4b.yaml` (the first's manifest under the name `q3-dense-headroom-v2-timing-2-4b` and run root `timing-2-qwen3.5-4b-base`); filler `--timing 2`; `registered_caps_total` counts both timing jobs | `ops/filled/`, `timing-810/fill-claims/after-0.json` (one claim), `tests/test_dense_headroom_v2_manifests.py` |
| image from a fresh clean clone of the head, CPU-only build path | Slurm 806, `build-architecture-image.sbatch` on a fresh clone of `87242fa` (bundle), image `sha256:15514bd1...`, source tar `b8bee28b...` | `images/` |
| v2 CPU doctor in that image | `DENSE_V2_DOCTOR_PASS`, 12/12 (srun CPU step, `--network none`, 186.6 s, ended 10:12:05) | `doctor/` |
| ONE timing job, at most 0.1 GPU-h, 6 minutes, registered subset, code head, through the lane | filled once (claim slot 0), dry run (0.1 GPU-h, `--time=00:06:00`, `--signal=B:USR1@180`), `--test-only`, submitted once: Slurm 810 | `ops/`, `timing-810/` |
| per-stage per-unit times (cold and warm), start-up, GPU utilisation, the check's output, physical GPU-h | below | `timing-810/analysis.txt`, `analysis.json`, `observe-810.txt`, receipt |
| 4B minutes by D36's rule from this measurement; 0.6B stays 12 | 4B 30 minutes (0.50 GPU-h); caps with both timing jobs 0.90 of 1.5 | `harness/dense_headroom_v2_lanes.py`, registration Compute |

## Slurm 810

- Image `sha256:15514bd1dabe...` from `87242fa` (the code head; the entry
  point's digest `e36e021b...` in the receipt is the tabled one). 1 x H100
  (GPU 0), 16 CPUs, 96 GB, limit 6 minutes. Slurm start 10:12:44, `job.env`
  10:12:46, `termination.env` 10:15:28 UTC: 162 s, **0.045 GPU-h physical**
  (Slurm's run time 164 s, 0.0456). Charged under the run-root rule
  (elapsed minutes rounded up, plus one): 4 minutes, 0.0667 GPU-h.
- Ended by Slurm's SIGUSR1, received 150.6 s into the process (about 162 s
  after Slurm's start, 18 s before the nominal three-minute lead) and
  answered at the next chunk boundary: `receipt` status
  `TIMING_INTERRUPTED`, marker `trigger=SIGUSR1`, exit 75, reason
  `signal_USR1_checkpoint_confirmed`. The guard found Triton's LLVM handlers
  for SIGUSR1 and SIGTERM 65.4 s in (after the check's compiles) and
  repaired them. Receipt bound to job 810 from `job.env`.
- Development artifact `b5210f79...`, equal to job 730's and job 766's.

### Start-up (everything before the first unit): 78.7 s

| Part | Seconds |
|---|---|
| Slurm start to `job.env` | 2.0 |
| job outside the workload process (container creation and checks before it, epilogue after it; over-counts) | 9.7 |
| process: imports and start-up checks (1.7 + 3.5), derivation 4.6, model load 7.1, other imports | 19.6 |
| process: the lane's `attention_backend_check` (two evaluations of `c320-q0`, with every first-use compile) | 47.4 |
| total | 78.7 |

Slurm 766 had 19.4 s to its first unit and a 47.7 s first unit (the
compiles); the backend check now carries them, as it does in the lane.

### `attention_backend_check` (the lane's first combined unit, `c320-q0`)

cuDNN's attention against the lane's: largest absolute difference 1.152
points in recall and 0.0111 in an option score; `k_blocks`, `max_selected`,
`ties` and `mc_correct` identical. `attention_backends` before and after the
check: flash, memory-efficient and math on, cuDNN off. The torch profiles of
v1's and v2's evaluation of a warm unit show
`aten::_efficient_attention_forward` and no cuDNN attention.

### Per-unit times by stage

First evaluations ("cold"; every subset and continue unit except `c320-q0`,
which the check had already evaluated). The continue chunks A-main 2 and
B-absent 2 ran under cProfile.

| Stage | Cold units | Median s | Mean s | Mean without one-off compiles | Measured mean tokens | Lane mean tokens | Warm (re-evaluated) s |
|---|---|---|---|---|---|---|---|
| A-main | 47 | 0.422 | 0.435 | 0.435 | 3,723 | 6,607 | 0.366 (`c320-q0`, v2, after the check); 0.491, 0.519 (v1 path, cProfile) |
| B-absent | 48 | 0.385 | 0.566 | 0.416 (one 7.64 s compile left out) | 4,412 | 6,974 | 0.446 (v1 path, cProfile) |
| C-literal | 32 | 0.156 | 0.383 | 0.156 (one 7.43 s compile left out) | 3,763 | 5,990 | 0.161 (v1 path, cProfile) |
| D-nohaystack | 32 | 0.346 | 0.339 | 0.339 | 240 | 181 | 0.417 (v1 path, cProfile) |

Cold and warm units now take the same time: the per-shape cost (Slurm 766:
3.6-4.1 s cold against 0.51 s warm) is gone. The same A-main and B-absent
chunks took 6.3 s and 6.0 s against 108 s and 54 s in Slurm 766. Per cold
A-main unit: prefill 0.116 s, selection 0.037 s, four options 0.274 s, cache
copies 0.006 s. Units of 8,310 tokens (B-absent, cProfile) took 0.58-0.61 s.
The two one-off compiles are the first selection-only prefill (`c320-q160`,
prefill 7.39 s) and the first prefill above 8,192 tokens (`c40-q20`, 8,313
tokens, prefill 7.27 s); the next units of the same kinds took 0.16 s and
0.61 s.

v1's evaluation path on five units (`c320-q0`, `c320-q20`, `c0-q0`,
`c320-q160`, `c160-q0`: every stage) was bit for bit equal to v2's output
with the lane's backend (cuDNN off in both).

### CPU and GPU

Each chunk's CPU seconds equal its wall seconds and one Python thread holds
the ticks (`busiest_threads`): the lane is still host-bound, but at about a
tenth of the time per unit. The job's GPU (index 0 from `job.env`), sampled
every 2 s: 0 to 95 percent, mean 31 percent, median 24 percent during the
evaluation; 9.7 to 10.5 GB used (`observe-810.txt`).

## The 4B limit by D36's rule

`timing-810/analyse_timing2.py`, run in image 806 on CPU (`--network none`)
with the job's own development artifact so that the lane's unit plan and
token lengths come from the harness:

- per stage, the mean of the cold units without one-off compiles (a unit over
  five times its stage's median), scaled up by the ratio of the lane's mean
  token length in that stage to the measured units' (1.77, 1.58, 1.59, 1;
  never below 1), times the stage's units (440, 280, 160, 280): 339 + 184 +
  40 + 95 = 658 s. Proportional scaling over-predicts the longest measured
  units (0.78 s predicted, 0.60 s measured at 8,310 tokens);
- the one-off compiles at their observed rate (2 in 159 cold units) over all
  1,160 units, each at the larger one's extra cost (7.27 s): 106 s;
- a 5 s statistics bound (job 727: 1.2 s): 769 s of evaluation and statistics;
- start-up 78.7 s.

minutes = ceil((2 x 769.1 + 78.7) / 60) + 3 = ceil(26.95) + 3 = **30**, cap
**0.50 GPU-h**. Useful window 27 minutes; the first job completes if it
averages at most 1.32 s per unit (3 times the slowest stage's measured
mean). Cross-checks: unscaled means give 428 s; Slurm's SIGUSR1 came 8 s (766)
and 18 s (810) early, which would trim the useful window by well under the
margin. The 0.6B lane stays 12 minutes (job 727). Caps: 0.10 + 0.10 (timing
jobs) + 0.20 + 0.50 = **0.90 GPU-h** of D36's 1.5. The fixed path did not
fail on the GPU and its rate fits well inside the cap, so the design is
unchanged.

`analysis-first-pass.txt` (and its script) is an earlier pass, kept as run,
that fitted a per-stage line in tokens and used the larger of that line's
lane mean and the stage's mean. It would have given 73 minutes (1.22 GPU-h,
caps 1.62, over D36's 1.5). The fits were ill-posed: A-main's and C-literal's
measured units all lie between 3,600 and 3,950 tokens, and C-literal's one
7.4 s compile at 3,835 tokens set its slope (3.3 ms per token, intercept
-12 s), which extrapolated 7.7 s per C-literal unit against 0.16 s measured;
B-absent's slope came from one 7.6 s compile at 8,313 tokens. It was replaced
by the estimator above, which was written after the first pass came out over
the cap. The two differ in two ways, not one: the registered estimator leaves
the compiles out of the per-unit means and adds them back as an allowance,
and it scales by length in proportion where the first pass scaled by the
fitted line.

The second difference crosses a minute boundary of D36's rule
(`limit-recheck/estimator-sensitivity.py`, standard library only, from the
receipt and `analysis.json`; output `estimator-sensitivity.txt` and `.json`;
it reproduces both committed analyses, 30 and 73 minutes):

| Estimator | A-main | B-absent | C-literal | D-nohaystack | Stages | Evaluation and statistics | (2 x that + 78.7 s) / 60 | Minutes |
|---|---|---|---|---|---|---|---|---|
| registered: compiles as an allowance, proportional scaling | 0.771 | 0.657 | 0.249 | 0.339 | 658.1 s | 769.2 s | 26.95 | **30** |
| first pass's line fit, compiles treated as registered | 0.896 | 0.539 | 0.239 | 0.339 | 678.0 s | 789.2 s | 27.62 | **31** |
| the larger of those two in every stage (a bound, not a proposed estimator) | 0.896 | 0.657 | 0.249 | 0.339 | 712.8 s | 823.9 s | 28.78 | 32 |
| first pass as run (compiles in the fits and means, no allowance) | 0.896 | 1.160 | 7.674 | 0.339 | 2,041.8 s | 2,046.8 s | 69.54 | 73 |

(seconds per unit entering the rule.) The increase from the first row to the
second is all A-main's, which has no compile: +54.8 s for the stage, while
the line gives B-absent 33.2 s and C-literal 1.5 s less than proportional
scaling. A-main's 47 measured units span only 211 tokens (3,614 to 3,825),
over which the line's slope is 0.160 ms per token, 3.3 times B-absent's
0.048 ms per token over 3,551 to 8,313 tokens; at the lane's mean of 6,607
tokens the line gives 0.896 s per unit against proportional scaling's
0.771 s. Proportional scaling was kept because B-absent is the only stage
with measured units at the lane's long contexts, and there it over-predicts:
0.78 s against 0.60 s measured for the seven units at 8,304-8,313 tokens (all
in the cProfile chunk, which only slows them). Against B-absent's 40 units
near 3,730 tokens, those seven had prefill 0.247 s against 0.116 s and option
forwards 0.347 s against 0.261 s, the whole unit 0.60 s against 0.38 s, for
2.2 times the tokens. At the first three rows' estimates the lane's first
job, run at that speed, ends 14.1, 14.5 or 15.0 minutes after Slurm's start
(start-up included), of its 27 useful minutes; the minute boundaries lie
inside D36's doubled margin. The registration's Compute section and decision
20 disclose this (Limit re-check, below); the 4B limit stays 30 minutes, the
registered estimator's.

## Registration and code after the job

Changed after Slurm 810: `harness/dense_headroom_v2_lanes.py`
(`LARGE_LANE_MEASURED`, `LARGE_LANE_STAGES`, `LARGE_LANE_TIMING_JOB`; the
4B lane 30 minutes; `LARGE_LANE_PROJECTED` removed), the 4B template (30
minutes, 0.5 GPU-h, comment), the registration (status and lead-in name D42;
Changes 4, 6, 7, 10; validity gate; Compute; both timing jobs' results;
Reported; freeze step 1; decisions 12, 18, 20, 21; code table) and the
tests. Every other tabled file Slurm 810 ran has the digest tabled now
(its receipt's `hashes.code`; a test pins the entry point's).
`tests/test_dense_headroom_v2_manifests.py::test_the_4b_measurement_is_the_second_timing_jobs`
binds the lanes module's figures to `timing-810/analysis.json` and the
receipt.

## Checks

- Before the image: the doctor's `timing_profile` case with `87242fa`'s
  entry point, doctor and lanes module mounted over image 801 (CPU, network
  none): PASS, the check ran first on the tiny hybrid (`precheck/`).
- v2 CPU doctor, 12/12 `DENSE_V2_DOCTOR_PASS`: in image 806 (`87242fa`, the
  timing job's image) and again in image 825 (`8c3f076`, the final code
  head), both srun CPU steps with `--network none` and the source baked in
  (`doctor/`).
- Host suite, fresh `~/cotcodec-scratch` clones from bundles, `uv sync
  --locked --extra dev`, srun CPU steps (`tests/host-suite.sh`):
  - at `7ab5b8b` (Slurm 814): hung after 179 results in
    `tests/test_dense_headroom_v2_signals.py::test_poll_restores_a_replaced_handler_and_records_it`
    and was cancelled (log kept). The pytest main thread sat in `sigwait`
    for SIGUSR1 (`/proc` status: SIGTERM blocked, nothing pending) with 30
    other threads in the process. The test blocks the signals in its own
    thread only and sends them to the process, so another thread of pytest's
    process (which does not block them) can take the signal between the
    guard's `sigpending` and its `sigwait`. Run alone or with the suite's
    first 183 tests it passed (6 of 6 and 1 of 1). Fixed in the test at
    `8c3f076` (signals sent to the test's own thread with `pthread_kill`);
    no tabled file changed. The entry point blocks both signals before any
    thread exists, so every thread of a lane inherits the block, and both
    timing jobs and the PID-1 test answered SIGUSR1 through the guard.
  - at `8c3f076` (Slurm 826): **2,216 passed, 40 skipped, 0 failed**.
  - at `436f038`, after main (`692b83d`, D43) was merged in again: **2,216
    passed, 40 skipped, 0 failed**.
- Torch-dependent dense tests inside image 825 (`8c3f076`; CPU, network
  none; pytest mounted read-only): **55 passed**
  (`tests/torch-in-image-825/`).
- PID-1 SIGUSR1 test against image 825 from the host clone at `8c3f076`:
  **1 passed** (`tests/pid1-image-825/`).
- Local (macOS `.venv`): ruff clean; the dense, preregister and Q1 policy
  tests 132 passed, 7 skipped.
- Freeze simulation (`freeze-simulation/`; local scratch clones of the
  final head `57f3cc2` (unsuffixed files), each chaining onto main's 11-row ledger ending at
  `q2-evaluator-mutation-v1`, `dc39bfa2...`; the real ledger `1052d58b...`
  before and after every run). D42 is the real decision in
  `program/decisions.md`; no stand-in decision was needed.
  - `full` (the registered step 1: status and lead-in rewritten to the frozen
    wording naming D42): freeze, verify and check-chain exit 0 (12 rows
    PASS); no "DRAFT", "wait for the program owner" or "still to be done"
    left; frozen-mode tests (v2 and v1 prereg, v2 manifests, preregister) 29
    passed; the entry point's code table matches (no differing file); the
    0.6B fill with a stand-in image receipt exits 0 and differs from the
    template only in the `FILL-*` values; the 4B fill exits 2 without the
    0.6B receipt and 0 with a stand-in one (v1 job 727's statistics bound to
    a stand-in job and the frozen digest); dry runs 0.2 GPU-h
    (`--time=00:12:00`) and 0.5 GPU-h (`--time=00:30:00`). The full suite
    in the frozen clone of `8c3f076` (macOS; the registration then lacked
    only Compute's sentence on the discarded first pass): 2,169 passed, 87
    skipped, 0 failed (`pytest-frozen-clone-full-8c3f076.txt`).
  - `status-only` (lead-in left in draft): the frozen-mode test fails ("the
    frozen file still says 'still to be done'").
  - `wrong-dec` (both naming D41): the frozen-mode test fails ("the status
    does not name D42").
  The same three runs at `7ab5b8b` and `8c3f076` gave the same results
  (kept with those suffixes), and the `full` run again at `436f038` after
  the second merge of main (`sim-full-436f038.txt`: check-chain 12 rows
  PASS, frozen-mode tests 29 passed).

## Limit re-check: the 4B estimator's sensitivity (`ddb3d02`)

The narrow re-check of the measured limits (D42 (iii)) found that the
registration's Compute section said the discarded first analysis pass and the
registered one "differ only in how the two compiles are treated", and that
this README said the same. They also differ in how they scale to the lane's
lengths (a fitted line against proportional scaling), the registered scaling
was chosen after the first pass came out over the cap, and that choice
crosses a minute boundary of D36's rule: 31 minutes under the first pass's
line fit with the compiles treated as registered, 30 under the registered
estimator (the table above; `limit-recheck/`). The text could not have been
corrected after the freeze.

Fixed in text only, with no GPU job and no tabled file changed (the
entry point's code table still matches): Compute's parenthetical and
decision 20 now state both differences, the 31 minutes and where they come
from (A-main's 211-token span), the per-stage larger-of-two bound (32), why
proportional scaling is registered (it over-predicts B-absent's measured
8,310-token units) and that the lane's first job ends in about 14 to 15 of
its 27 useful minutes at any of these estimates; decision 20 no longer calls
the scaling "the conservative choice" without qualification. The 4B limit
stays 30 minutes (0.50 GPU-h; caps 0.90 of 1.5). The paragraph on
`analysis-first-pass.txt` above is corrected likewise.
`tests/test_dense_headroom_v2_manifests.py::test_the_4b_limits_estimator_sensitivity_is_disclosed`
recomputes both estimators from the receipt and `analysis.json` (30 and 31
minutes, A-main's span and both slopes) and requires the registration's
Compute section and decision 20 to say so.

Checks at `ddb3d02`:

- Local (macOS `.venv`): ruff clean; the dense, preregister and v2 tests
  (`tests/test_dense_headroom_*.py`, `test_run_dense_headroom_precheck.py`,
  `test_summarise_dense_headroom_precheck.py`, `test_preregister.py`,
  `test_*prereg*.py`) 185 passed, 15 skipped.
- Freeze simulation (`freeze-simulation/*-ddb3d02.*`; local scratch clones of
  `ddb3d02` chaining onto the branch's 11-row ledger ending at
  `q2-evaluator-mutation-v1`, `dc39bfa2...`; the real ledger `1052d58b...`
  before and after every run):
  - `full`: freeze, verify and check-chain exit 0 (12 rows PASS); no
    "DRAFT", "wait for the program owner" or "still to be done" left;
    frozen-mode tests (v2 and v1 prereg, v2 manifests with the new test,
    preregister) 30 passed; the frozen-wording diff equals the earlier runs'
    but for line offsets; the entry point's code table matches (no differing
    file); 0.6B fill exit 0, 4B fill exit 2 without the 0.6B receipt and 0
    with a stand-in one; dry runs 0.2 GPU-h (`--time=00:12:00`) and 0.5 GPU-h
    (`--time=00:30:00`). The full suite in the frozen clone (macOS): 2,170
    passed, 87 skipped, 0 failed (`pytest-frozen-clone-full-ddb3d02.txt`).
  - `status-only`: the frozen-mode test fails ("the frozen file still says
    'still to be done'"); `wrong-dec`: it fails ("the status does not name
    D42").
