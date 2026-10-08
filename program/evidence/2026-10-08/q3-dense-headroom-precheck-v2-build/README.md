# q3-dense-headroom-precheck-v2: build, timing job and checks (2026-10-08)

Branch `stage0/q3-dense-v2` (from main `5e9e1f7`, D36; main merged back in
at `30f9c7c` before the program-state update). Registration
`program/preregistrations/q3-dense-headroom-precheck-v2.md`: DRAFT, not
frozen. Nothing here was frozen against the real ledger and nothing was
pushed. GPU use: one timing job, Slurm 766, 205 s on one H100 (0.0569 GPU-h
physical), and after D42 a second, Slurm 810, 162 s (0.045 GPU-h; section
"Second timing job" and `timing-2/`). Every other host job was CPU only.

## What D36 asked for and what was done

| D36 item | Done | Evidence |
|---|---|---|
| (i) receipts bound to their Slurm job | `harness/dense_headroom_v2.py::batch_job_id` reads `job_id` from the run directory's `job.env`, which `docker-research.sbatch` writes before `docker create` (the batch script is unchanged, digest `2a10c9c7...`); under the batch path the entry point exits 2 without it or when `SLURM_JOB_ID` disagrees; the receipt records `slurm_job_id` and `slurm_job_id_source: job.env`, and v2's summariser requires both | `tests/test_dense_headroom_v2_job_binding.py` (stub-sbatch end to end: the real batch script, v2's and v1's receipt writers, v1's `check_job`), doctor `job_binding`/`end_to_end`, live: `timing-766/dense-precheck_timing-receipt.json` (`slurm_job_id: "766"`, source `job.env`) |
| (ii) SIGUSR1 honoured on the 4B path | cause below; SIGUSR1/SIGTERM blocked from process start in every thread, consumed at chunk boundaries by `SignalGuard`, which also records and repairs a replaced OS handler | `diagnosis/probe/sigprobe-cpu.log`, doctor `usr1_displaced` (images 763, 770, 776), `tests/pid1-image-770/`, `tests/pid1-image-776/` (entry point as the container's PID 1 with a real Triton compile; v2 exit 75 with marker, v1 exit 0 without), live: `timing-766/termination.env.txt` (`signal_USR1_checkpoint_confirmed`, exit 75) |
| (iii) CPU bottleneck removed without changing any computed quantity | cause and fix below; every change is bit-equal except the 4B lane's cuDNN switch, which changes computed quantities and so departs from (iii) (registration decision 18; the owner's decision must amend (iii) for that lane, "Review fixes" below) | `timing-766/`, `diagnosis/prof-out/`, doctor `equivalence`/`end_to_end`/`timing_profile` |
| validity gate | the v2 0.6B lane must reproduce job 727's receipt to 1e-6 (every numeric leaf of `report`, `decisions`, `coverage`, `artifact_counts`, `selectors`, `attention_layers`; `hashes.dev_artifact_sha256` exact) and smoke 452 within 0.5 points, else INVALID and the 4B lane does not run | `harness/dense_headroom_v2.py::v1_reproduction`, filler `check_small_lane_receipt`, summariser, doctor `v1_gate` |
| timing job (at most 0.1 GPU-h) on the fixed 4B path | Slurm 766, 6-minute limit, registered subset; 205 s; it ran the path before the fix (cuDNN's attention on), so the fixed path was not timed and has not run on a GPU | `timing-766/` |
| limits and caps | 0.6B 12 min (0.20 GPU-h) from job 727's measured 278 s; 4B 45 min (0.75 GPU-h), projected, not measured (a departure from D36's timing rule, for the owner's decision); timing 6 min (0.10); total 1.05 of 1.5 | `harness/dense_headroom_v2_lanes.py`, registration Compute |

## SIGUSR1 (job 730's defect)

`sigprobe-cpu.log` (the image's own Python, as PID 1, CPU) shows the OS-level
SIGUSR1 handler stays CPython's through `import torch`, `transformers`,
`triton` and `tilelang`, and changes at the first Triton kernel compile:
LLVM's `RegisterHandlers` installs process-wide handlers (SIGUSR1 among its
"info" signals, which it swallows; SIGTERM re-raised). `signal.getsignal`
still reports CPython's handler, so nothing in Python notices. Job 730 ran
21 minutes on the 4B lane, received Slurm's SIGUSR1 and kept computing until
the hard stop. v2 blocks both signals before any import
(`scripts/run_dense_headroom_precheck_v2.py`, only when the file runs as the
program) so the kernel keeps them pending regardless of the installed
handler, and `SignalGuard.poll` consumes them with `sigwait` at each chunk
boundary. In Slurm 766 the guard found the replacement 65.6 s in and Slurm's
SIGUSR1 was answered at the next chunk boundary (marker `trigger=SIGUSR1`,
exit 75).

## The CPU bottleneck (job 730: about 3.8 s per unit, one core busy, GPU idle)

Not the hypotheses in v1's write-up: in Slurm 766 the per-option cache copy
took 5 ms per unit and the selectors with the fp32 recompute 43 ms
(`timing-766/analysis.txt`, `parts per unit`). torch 2.11 sends Qwen3.5's
head-dimension-256 attention to cuDNN (`aten::_cudnn_attention_forward` in
both torch profiles of the receipt), and cuDNN builds a graph for every new
(query length, key length): about 0.7 s of CPU per forward, five new shapes
per unit (prefill and four options). Evidence in the receipt: a unit whose
prefill length had been seen took 0.11 s for its prefill against about 0.8 s;
the two units re-evaluated with every graph cached took 0.511 and 0.517 s
whole (v1's path, cProfile) against 3.6 to 4.1 s cold; the warm-unit torch
profile has 0.42 s of CPU and 0.18 s of GPU time. Before the timing job, the CPU
profiles in `diagnosis/prof-out/` (tiny models at 6,000 tokens and the real
layer structures at 300 tokens) and the probes in `diagnosis/probe/`
established which implementations the image resolves (fla's Triton kernel for
the chunked gated delta, torch fallbacks for the one-step recurrence and the
causal conv1d, the CUDA depthwise convolution) and the thread layout; on CPU
they could not show the cost, which is cuDNN's, so the timing job located it.

Fix: on the hybrid lane only, `torch.backends.cuda.enable_cudnn_sdp(False)`
(flash or memory-efficient attention, math where neither applies). Every
other v2 change to the evaluation (`harness/dense_headroom_torch_v2.py`:
literal blocks on the device before the layer loop, `clone_cache` instead of
`copy.deepcopy`, the first option token from the host array) is bit-equal to
v1:

- `tests/test_dense_headroom_v2_torch.py` and doctor `equivalence`: every
  receipt field of selection-only, multiple-choice-only and combined units
  equal to v1's, bit for bit, on tiny Qwen3 and Qwen3.5-style models;
- doctor `end_to_end`: on both tiny lanes every statistic and receipt field of
  v2's entry point equals v1's entry point's with tolerance 0;
- Slurm 766: two real 4B units through v1's path equal v2's output bit for
  bit (both with cuDNN attention); the development artifact equals job 730's
  (`b5210f79...`).

The cuDNN switch is the one change that is not bit-equal (another
accumulation order at bf16). The 0.6B lane does not use it, so the job-727
gate binds that lane exactly. The 4B lane has no v1 number to reproduce (job
730 left no receipt); its receipt reports `attention_backends` and, for its
first unit with selection and multiple choice, the largest difference of every
recall and option score between cuDNN's attention and the lane's
(`attention_backend_check`, descriptive, not gated). Registration decision 18
states this.

The fixed 4B path was not timed: the timing job (the one D36 allows) ran
before the cause was known. The 4B limit applies D36's rule to twice the
warm-unit projection: 0.52 s x 1,160 units + 5 s = 608 s projected, 1,216 s
entering the rule, plus 75 s measured start-up, rounded up, plus the 3-minute
SIGUSR1 lead: 45 minutes. At the timed (cuDNN) rate the lane would need about
75 minutes; a lane that runs at that rate ends INCOMPLETE under the
registered rules.

## Timing job, Slurm 766

Image `sha256:3f2cc537...` (Slurm 763, CPU-only build path, fresh clone of
`71dc954`, source tar `3b5a1fce...`); the v2 CPU doctor passed in it (12/12)
before submission. Filled manifest `timing-766/filled/`, one claim
(`timing-766/fill-claims/`), dry-run and `--test-only` before the submit.
Run 07:32:07 to 07:35:32 UTC (205 s, 0.0569 GPU-h physical; 5 minutes, 0.0833
GPU-h, charged under v1's rounding rule); limit 6 minutes. Start-up 19.4 s to
the first unit, first unit 47.7 s (first-use compiles); A-main chunk 0 in
108 s (median 4.08 s per unit), B-absent chunk 0 in 54 s (median 3.62 s);
GPU utilisation 0 to 13 percent when sampled (`observe-766.txt`). The subset
did not complete (2 of 8 chunks); Slurm's SIGUSR1 ended it with a confirmed
checkpoint. `analysis.txt` is `analyse_timing.py` run on the receipt.

## Images and doctor runs (CPU only)

| Slurm | Commit | Image | Doctor |
|---|---|---|---|
| 763 | `71dc954` | `sha256:3f2cc537...` | `doctor/doctor-cpu-image-3f2cc537.*`: DENSE_V2_DOCTOR_PASS, 12/12 |
| 770 | `de999f7` | `sha256:3426eca9...` | `doctor/doctor-cpu-image-final.*`: DENSE_V2_DOCTOR_PASS, 12/12 |
| 776 | `e6e81e7` | `sha256:62e229be...` | `doctor/doctor-cpu-image-e6e81e7.*` (Slurm 778): DENSE_V2_DOCTOR_PASS, 12/12 |

Cases: codecs, features, derive, statistics, selectors, multiple_choice (v1's
doctor cases), equivalence, v1_gate, end_to_end, job_binding, usr1_displaced,
timing_profile. Grade: executability and gate semantics on tiny synthetic
models only. `doctor/run-doctor-in-image.sh` ran each (`--network none`, no
GPU, source baked into the image). Build receipts and logs in `images/`.
`e6e81e7` is the last commit that changed a tabled file; later commits change
a test, documents and evidence only. The lanes run the image built from the
frozen commit (freeze procedure), not these.

## Tests

- `tests/pid1-image-770/`, `tests/pid1-image-776/`:
  `tests/test_dense_headroom_v2_usr1_pid1.py` against each image, entry point
  as PID 1 through `exec_research_workload.py`, Triton compile in the shim,
  `docker kill --signal USR1`: v2 exit 75 with marker, v1 exit 0 without;
  both report the displaced handler.
- `tests/host-suite-e6e81e7/pytest-full.log`: the full suite at `e6e81e7` in a
  fresh `~/cotcodec-scratch/` directory (`uv sync --locked --extra dev`):
  1,824 passed, 36 skipped, 1 failed, the Linux-only stub-sbatch binding test,
  whose workload program did not start (the inner receipt code at column 0
  defeated `textwrap.dedent`; the Mac skips the test). Fixed in `50153d0`;
  the file then passed on the host (3 passed).
- `tests/host-suite-final/pytest-full-f2510dd.log`: the full suite at
  `f2510dd` (main merged, state and evidence committed), fresh
  `~/cotcodec-scratch/` directory from a bundle clone plus an rsync of the
  worktree without `.venv`/`.git` (clean tree), `uv sync --locked --extra dev`,
  Slurm 788 (CPU): 2,212 passed, 40 skipped, 0 failed. The dev extra has no
  torch, so the torch tests skip there.
- `tests/torch-in-image-776/pytest-torch-image-776.log`: the torch-dependent
  dense tests (`test_dense_headroom_v2_torch`, `test_dense_headroom_torch`,
  `test_run_dense_headroom_precheck`, `test_dense_headroom_data`,
  `test_dense_headroom_v2_timing`, `test_dense_headroom_v2_signals`,
  `test_dense_headroom_v2_prereg`) inside image 776 on CPU (`--network none`,
  pytest's pure-Python packages mounted read-only, since the image has no
  pytest): 43 passed. The first attempt
  (`pytest-torch-image-776-without-USER.log`, 7 failed) ran as a uid with no
  passwd entry and without `USER`/`LOGNAME`, so an import's
  `getpass.getuser()` failed and torch's re-import then raised "Artifact of
  type=precompile already registered"; the doctor wrapper and the batch
  path set both variables. Setting them was the only change.
- Locally (macOS, `.venv`): the v2, v1 dense and preregister tests 105
  passed, 7 skipped; `ruff check .` clean.

## Freeze simulation

`freeze-simulation/`: on a scratch clone, never the real ledger.

## Review fixes (after `fd8e906`; code at `b8977d9`)

A review of the draft found six blocking issues. All are real; none needed a
GPU job, and the limits, caps and every computed quantity are unchanged. Two
of them can only be closed by the program owner, and the registration now
says so instead of presenting them as settled.

| Finding | Disposition |
|---|---|
| 1, 6: the 4B lane's cuDNN switch changes computed quantities, which D36 (iii) rules out, yet decision 18 was titled "Evaluation equal to v1's (D36 (iii))"; the carried "same code" wording implies the 0.6B gate covers the 4B backend | Real. No bit-equal alternative exists: any other attention backend changes the bf16 accumulation order, and keeping cuDNN keeps the per-shape graph build. Decision 18 is retitled as a departure from D36 (iii); the status paragraph, the design-decision lead-in, Changes item 4 and freeze step 1 say the owner's decision must amend D36 (iii) for the 4B lane or require another fix; decisions 18 and 19 say the job-727 gate and smoke 452 do not cover the backend and that `attention_backend_check`, descriptive, is the only check; decision 18 qualifies v1's carried wording (decision 11 and the INVALID rule stay verbatim, as the carried-text test requires). The amendment itself is not recorded here: it is the owner's decision. |
| 2, 5: the registered 4B path (cuDNN off) has never run on a GPU, and its limit is a projection, not the measurement D36 asks for | Real. No GPU job was run. None of this round's fixes changes evaluated code (the entry point's change is a docstring and a comment), and what is left of the timing allowance cannot hold a job: 6 minutes less job 766's 5 charged minutes under the run-root rule (`ceil(205 s / 60) + 1`) leaves 1, against the 5 any job needs (0.043 GPU-h physical, also under 5 minutes). Compute, decisions 20 and 21, Changes item 6 and the status say the 4B limit is projected, not measured, that the fixed path has not run on a GPU, and that the lane completes only if that path averages at most about 2.1 s per unit (`large_lane_break_even_unit_s`). The owner's decision must amend D36's timing rule for the 4B lane, or authorise a second timing job (at most 0.1 GPU-h, 1.15 of 1.5; a fresh timing run root, because the filler refuses a second job in `timing-qwen3.5-4b-base`), whose measurement then replaces the projection before the freeze. |
| 3: decisions 20 and 21 and the lanes docstring call the 4B limit measured and job 766's path the fixed one | Real. Decision 21: job 766 ran the 4B path before the fix (cuDNN's attention on). Decision 20: the 0.6B limit is measured; the 4B limit doubles a warm-shape projection, doubled again, and departs from D36's timing rule. `harness/dense_headroom_v2_lanes.py`: docstring corrected; `LARGE_LANE_MEASURED` renamed `LARGE_LANE_PROJECTED` (`measured: False`, `evaluation_entering_rule_s`); the 4B template's comment likewise. Code table re-rendered. |
| 4: freeze step 1 rewrote only the status paragraph, so the frozen file would keep "wait for the program owner's acceptance" in the design-decision lead-in | Real. Step 1 now rewrites the lead-in as well. In frozen mode `test_status_and_decisions` refuses any draft wording ("DRAFT", "wait for the program owner") and requires the status paragraph and the lead-in to name a decision after D36 in `program/decisions.md` that names this experiment and amends D36 (iii). |

Checks at `b8977d9` (all CPU; the real ledger untouched, nothing pushed):

- Locally (macOS): the v2, v1 dense and preregister tests 109 passed, 9
  skipped; `ruff check .` clean.
- Host suite (fresh `~/cotcodec-scratch/` clone of a bundle, `uv sync
  --locked --extra dev`, Slurm CPU step 802): 2,213 passed, 40 skipped, 0
  failed (`review-fixes/tests/host-suite-b8977d9/`).
- Image `sha256:5281ac01...` built by Slurm 801 (CPU-only build path, fresh
  clone of `b8977d9`, source tar `4e040f36...`; `review-fixes/images/`). v2
  CPU doctor in it (Slurm 803, network none): DENSE_V2_DOCTOR_PASS, 12/12
  (`review-fixes/doctor/`). The torch-dependent dense tests inside it
  (Slurm 804; the earlier list plus the v2 prereg and manifest tests): 52
  passed (`review-fixes/tests/torch-in-image-801/`). The PID-1 SIGUSR1 test
  against it (Slurm 805): passed (`review-fixes/tests/pid1-image-801/`).
- Freeze simulated on three fresh local scratch clones of `b8977d9`, each
  chained onto the branch's ledger head (11 rows, `dc39bfa2...`;
  `review-fixes/freeze-simulation/`, `simulate.sh` and `rewrite.py`). A
  stand-in decision "D42 FREEZE SIMULATION ONLY" was added to the clone's
  `program/decisions.md` only. `full` (step 1 as now registered: status and
  lead-in rewritten, naming the stand-in): freeze, verify and check-chain
  (12 rows PASS) exit 0; no draft wording left; frozen-mode tests (v2 and v1
  prereg, v2 manifests, preregister) 26 passed; the entry point's code table
  matches the clone; the 0.6B fill with a stand-in image receipt exit 0 and
  differs from the template only in the FILL values; the 4B fill without the
  small-lane receipt exit 2; submitter dry run exit 0 (0.2 GPU-h).
  `status-only` (the old step 1): the frozen file keeps "wait for the program
  owner", and `test_status_and_decisions` fails. `wrong-dec` (both rewritten
  but naming D41): `test_status_and_decisions` fails, "names no decision that
  accepts v2 and amends D36 (iii)".

## Second timing job of the fixed 4B path (D42 (ii); code at `87242fa`, limits at `7ab5b8b`)

D42 amended D36 (iii) for the 4B lane and authorised a second timing job of
the fixed path, starting with the lane's `attention_backend_check`, in a
fresh run root. Slurm 810 (image `15514bd1...` from `87242fa`, CPU-only
build 806, doctor 12/12) ran 162 s, 0.045 GPU-h: the lane's start-up with
the check (47.4 s; recall within 1.15 points and option scores within 0.011
of cuDNN's on `c320-q0`; cuDNN left off), the registered subset and two more
chunks at 0.16-0.43 s per unit by stage with memory-efficient attention,
v1's path bit-equal on five units, SIGUSR1 answered at a chunk boundary. By
D36's rule the 4B lane is now 30 minutes (0.50 GPU-h; 769 s of evaluation
and statistics with length scaling and a compile allowance, 79 s of
start-up); the 0.6B lane stays 12; caps with both timing jobs 0.90 of 1.5
GPU-h. The earlier sections' 45-minute projection and "untimed fixed path"
are superseded. Everything is in `timing-2/README.md`. The narrow re-check
then found that the registered estimator's proportional scaling, chosen after
a first analysis pass came out over the cap, crosses a minute boundary: the
first pass's line fit with the compiles treated as registered gives 31
minutes. The registration now discloses it (`ddb3d02`, text only; the limit
stays 30 minutes; `timing-2/README.md`, "Limit re-check").

## Files

- `timing-2/`: the second timing job (D42 (ii)): images 806, 813 and 825,
  doctor runs, the fill, dry run, test-only and submit records, the run
  directory of Slurm 810 with the analysis, the tests (host suites, torch
  tests in image 825, PID-1) and the freeze simulations naming D42.
- `diagnosis/`: probes (CPU) and their logs; CPU profiles.
- `timing-766/`: the timing job's run-directory files, receipt, progress,
  observation and collection scripts, filler and submitter records.
- `images/`, `doctor/`, `tests/`, `freeze-simulation/`; `operator-log.txt`.
- `review-fixes/`: the review round's freeze simulations, image 801, doctor
  and test runs.
