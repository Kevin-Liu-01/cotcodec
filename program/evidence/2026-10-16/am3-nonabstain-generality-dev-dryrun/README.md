# am3-nonabstain-generality-v1: development dry run (EXPLORATORY, development split only, before the freeze)

**EXPLORATORY. DEVELOPMENT SPLIT ONLY. NOT A RESULT.** This is the pre-freeze rehearsal of the
registration `am3-nonabstain-generality-v1` (`program/preregistrations/am3-nonabstain-generality-v1.md`,
draft; D118). It ran the registration's whole pipeline, with its code and operator scripts, on
the AM1 pilot's 63 development questions, and checked that it reproduces AM3's committed
development outputs. No held-out or abstention question was given to any model.

- **Code.** Commit `eae156cf` for the image, the GPU job, extract and the first analysis. The
  analysis and the tests were rerun at `95c3ef5a`, `ea678a99` and `fc9ebb4d` (byte-identical
  outputs, `logs/confirm-*.log`). After pre-freeze check 1, the CPU parts were rerun at
  `0d030015` and `8624a08b` with the round-1 code (see "Round 1"); the code the GPU job runs did
  not change, so no GPU job was rerun.
- **Host directory.** `~/cotcodec-runs/stage0/am3g-dev-dryrun/` (new). The operator scripts
  (`ops/am3g/`) ran in their `dev` mode.
- **Inputs.** The pilot's development artifact (`15567cf1...`), AM3's job 1466 passes (the
  reference) and AM3's host-only features (`67780c98...`, for `power`). The script refuses any
  held-out or abstention path in the development population.

## What ran

| Job | What | GPUs | Run time | GPU-h | Outcome |
|---|---|---:|---:|---:|---|
| (host CPU) | `prepare-abstention` at `ffa8675c`: the abstention population's artifact | 0 | seconds | 0 | 30 questions, artifact `f1c241ba...` (host only), summary `cf7ecb51...` |
| 1467 | cotcodec-vllm cu129 overlay build, commit `eae156cf` | 1 | 00:01:05 | 0.0181 | COMPLETED, `sha256:a8571a41...`, provenance PASS |
| 1468 | post-build CPU selftest, development population | 0 | 00:00:25 | 0 | pass |
| 1469 | post-build CPU selftest, abstention population (tokenizer lengths only) | 0 | 00:00:12 | 0 | pass |
| 1471 | the dry-run GPU job (`scripts/memcredit_am3g.py run --population development`), docker-research lane | 1 | 00:10:18 | 0.1717 | COMPLETED 0:0 |
| 1472, 1473 | ad hoc CPU checks of the gate's code pins inside the image (`adhoc/`) | 0 | seconds | 0 | see "The gate inside the image" |
| | **total** | | | **0.1898** of the 0.5 cap | |

- Run times are `scontrol` RunTime. Both GPU jobs were submitted with no other GPU job of this
  program queued or running; D110's `transcreate-*` jobs held GPUs 0-1 and were not touched
  (`ops/preflight.log`). Slurm allocated the GPU.
- The lane ran the container read-only with `--cap-drop ALL`, `no-new-privileges`, the user's
  uid:gid, a tmpfs `/tmp`, no network and the allocated GPU only; stock vLLM 0.31.0.
- Steps of job 1471 on one H100 (`jobs/1471-development/am3g/summary.json`):

| Step | Engine start | Pass | Outcome |
|---|---:|---:|---|
| `rd-qwen3-8b` (anchor, eager batch-invariant) | 28.3 s | 70.1 s, 8,946 requests | complete; stop 8,945, length 1 |
| `rd-olmo2` (eager batch-invariant, Transformers backend) | 27.9 s | 73.2 s | complete; stop 8,904, length 42 |
| `rd-olmo2-default` | | | not needed |
| `rd-qwen35-9b-default` (eager, default mode) | 41.2 s | 122.1 s | complete; stop 8,937, length 9 |
| `judge32` (Qwen3-32B) | 35.8 s | 20.7 s, 2,869 items | complete |
| `judge8` (Qwen3-8B) | 27.7 s | 4.7 s | complete |

The 2,869 judge items are the 2,555 distinct replies, AM1's 188 validation items and 126
abstention-template calibration items (two per question).

## It reproduces AM3 exactly

`dryrun-compare.json` (`scripts/memcredit_am3g.py dryrun-compare`): 20 of 20 checks pass.

| Check | Result |
|---|---|
| Qwen3-8B replies against job 1466, every (question, arm, mask) | 8,946 of 8,946 identical in tokens and log-prob bits |
| OLMo-2 replies against job 1466 | 8,946 of 8,946 identical in tokens and log-prob bits |
| Qwen3.5-9B replies against job 1466 (default mode) | 8,946 of 8,946 identical in tokens and log-prob bits |
| Qwen3-32B labels against job 1466, the 2,743 shared items | 2,743 of 2,743 |
| Qwen3-8B labels against job 1466 | 2,743 of 2,743 |
| per-pool records against AM3's committed `per-table.json.gz` | 126 of 126 per reader; the file is byte-identical (`0fc5635b...`) |
| reader x judge x arm cells against AM3's committed `results.json` | 12 of 12 equal |

- **OLMo-2 in batch-invariant mode through the Transformers backend replays.** AM3 had not
  replayed it.
- **Qwen3.5-9B in default mode repeated job 1466 bit for bit** with the same request list and
  order, the same engine settings and a freshly built image. That shows the schedule is
  reproducible. It does not show batch invariance, which vLLM 0.31.0 refuses for GDN layers.
- Every number of AM3's main table is therefore reproduced by this pipeline (AM3 README, "Answer:
  the main table"). `results.json` and `tables.md` here hold the same cells, plus the H1 and H2
  blocks run on development data as a code exercise (`mechanics`; they decide nothing, and the H2
  block there is neither H2's population nor its judge).

## Abstention-template calibration (development questions)

Under LongMemEval's abstention template, with a generic explanation in the Explanation slot
(`abstention_judge.calibration_explanation` in the config), on the 63 development questions:

| Judge | "I don't know.", yes | the reference answer, yes |
|---|---|---|
| Qwen3-32B | 63 of 63 | 0 of 63 |
| Qwen3-8B | 63 of 63 | 4 of 63 |

The template renders and the primary judge separates a refusal from an answer. These are
answerable questions, so this is a calibration of the judge on the template, not G-J2.

## The abstention population (built before the freeze, no model output)

`prepare/abstention-summary-ffa8675c.json` (text-free) and `prepare/prepare-ffa8675c.json`:

- 30 questions, every LongMemEval-S id ending in `_abs`: knowledge-update 6, multi-session 12,
  single-session-user 6, temporal-reasoning 6. Ids digest `e08d46cc...`; artifact `f1c241ba...`,
  186,699 bytes, read-only on the host under `~/cotcodec-runs/stage0/am3-nonabstain-generality-v1/inputs/`.
- Pools: the BM25 top 8 user turns, as AM1's retrieved arm. The builder reproduces the
  development artifact's retrieved pools, 63 of 63.
- Twins (same id prefix), as recounted by `abstention-facts` (`prepare/abstention-facts-0d030015.json`):
  22 in AM1's held-out confirmatory set, 5 development questions (`09ba9854` is also a Step 0
  demo question), 2 Step 0 demo questions in the split's held-out part outside AM1's 347, 1
  without a twin. The first summary (`prepare/abstention-summary-ffa8675c.json`) counted 4
  development and 3 Step 0 twins: its membership test checked the Step 0 exclusion before the
  split (check 1, m1). No haystack session id is shared with a twin, but memory texts are: 27 of
  the 30 pools hold a memory whose text (by SHA-256) is one of the twin's user turns; 89 of the
  240 pool memories are, and 70 are in the twin's own retrieved pool.
- The full-pool prompt is at most 4,363 characters. The CPU selftest (job 1469) rendered every
  request: at most 1,027 (Qwen3-8B), 972 (OLMo-2) and 1,040 (Qwen3.5-9B) tokens; judge items at
  most 272.

## The gate inside the image

The registered GPU job checks, inside its image, that the ledger holds the registration's row and
that every file pinned in section 16 of the registration matches. Before the freeze that can be
checked only ad hoc (`adhoc/`, CPU jobs with no GRES, no network):

- **Job 1472** ran the check in the dry-run image with the image's own copy of the draft. The
  registration and ledger are in the image, but one pinned file was not: the archived prompt port
  `legacy/harness/memory_trials/longmemeval_judge.py`. `.dockerignore` keeps `legacy/` out of
  every image. After the freeze, the gate would have refused the registered GPU job.
- **The fix** (commit `ea678a99`): the port is no longer a code pin. The registration's section 4
  records its digest, and the test that compares the abstention template with it runs on the host.
  A new test checks that no pin sits under a `.dockerignore` entry.
- **Job 1473** mounted the fixed draft's table into the dry-run image: all 39 pins are present,
  and only the two files changed after `eae156cf` differ (the tests and the staging script).

## Round 1: after pre-freeze check 1 (CPU only)

The registration's round-1 fixes changed the host-side code (extract, analyze, the hand check,
the rerun rule, the twin facts) and the registered jobs' step budgets, not the code the GPU job
runs. So the CPU parts were rerun on job 1471's records, and no GPU job ran.

- **`abstention-facts`** (`prepare/abstention-facts-0d030015.*`): it rebuilt the abstention
  artifact in memory and found it byte-identical to the pinned file (`f1c241ba...`), then wrote
  the corrected twin facts and the memory-text overlap above.
- **The R2 code on a real tables file.** `extract` now also compares the anchor's labels with the
  pilot's committed development tables through `load_pinned_tables` and `labels_vs_tables`:
  8,913 of 8,946 cells agree, AM3's figure (the 33 others are the compiled-against-eager
  difference AM3 explained).
- **The blind hand check, rehearsed on development data.**
  - `hand-sample` (`hand-check/hand-sample-0d030015.json`) drew 27 items: for OLMo-2, 4
    discordant questions (both replies) and 4 distractor questions; for Qwen3.5-9B, 3 and 3.
    The sample (host only) holds the question, its type and id, the reference answer and the
    reply, and nothing else.
  - An isolated agent read only the sample and the instructions and labelled every item: 7
    correct, 20 not (14 of them refusals). One temporal item, half a week off, it labelled correct
    as borderline under the off-by-one rule.
  - `am3g-hand-receipt.sh` wrote the labels' SHA-256 (`604896d5...`) and a text-free receipt
    (`hand-check/`) before `analyze` joined them.
  - The join: hand and judge agree on 27 of 27 items (kappa 1.00). b_hand and c_hand are 4 and 0
    for OLMo-2 and 3 and 0 for Qwen3.5-9B, equal to the judge's; neither separates on 63
    questions (p = 0.125 and 0.25), so both read NO_DETECTED_DIFFERENCE before and after the hand
    check (`results.json`, `mechanics.h1_hand_check`).
- **`analyze`** at `8624a08b`: twice, byte-identical; `dryrun-compare` 20 of 20 again
  (`per-table.json.gz` still byte-identical to AM3's); `power.json` unchanged; tests passed
  (`logs/analyze-8624a08b.log`, `logs/pytest-8624a08b.log`).
- **The pins inside the image, again** (job 1474, `adhoc/pins-in-image-1474.out`): the revised
  draft's table (50 pins) mounted into the dry-run image, built from `eae156cf`. The only files
  absent are the six operator scripts added after `eae156cf` (`am3g-mac-bundle.sh`,
  `am3g-job-state.sh`, `am3g-image.sh`, `am3g-rerun-decision.sh`, `am3g-hand-sample.sh`,
  `am3g-hand-receipt.sh`), and the only ones that differ are the seven changed after it. The
  newly pinned lane scripts (`verify_compute_provenance.py`, `check_compute_env.sh`,
  `exec_research_workload.py`), the Dockerfile and `uv.lock` are present and equal. An image
  built from the freeze commit holds every pin, since no pin sits under a `.dockerignore`
  entry (a test checks that).
- **Job 1470** is not this registration's: it appears in none of its logs or scripts, and
  scontrol no longer knew it when check 1 asked (Slurm accounting is disabled on the node).

## Power (`power.json`)

`scripts/memcredit_am3g.py power`, CPU, from AM3's committed `results.json`, `am1-keepset-search-v1`'s
committed `results.json` and AM3's host-only features. The registration's section 9 quotes it.

- **H1** (347 questions; bounds between alpha 0.025 and 0.05): at AM3's development rates (4 of
  63 for OLMo-2, 3 of 63 for Qwen3.5-9B, no losses) power is 1.00 and 0.998-0.999; at half those
  rates 0.93-0.96 and 0.72-0.83; at a quarter 0.31-0.47 and 0.12-0.23.
- **H2** (30 questions): power reaches 0.8 only at a cost rate of about 0.3. The development
  proxy (gold-free 4-subsets as an unanswerable question's subsets) gives switching rates of
  0.048 (Qwen3-8B), 0.175 (OLMo-2) and 0.063 (Qwen3.5-9B), with power 0.0004, 0.26 and 0.002 at
  Holm's strictest step. That is why the draft makes H2 a registered description.

## Tests

- `tests/test_memcredit_am3g.py` and `tests/test_memcredit_am3.py`: 81 passed at `eae156cf` and
  `95c3ef5a`, 82 at `ea678a99` (the pins-in-image test added), 86 at `fc9ebb4d` (tests of the
  anchor replay checks R1 and R2 added), on the host (`logs/pytest-eae156cf.log`,
  `logs/confirm-pytest-*.log`) and locally.
- The whole suite on the host at `eae156cf`: 3,535 passed, 64 skipped, and 2 failed in another
  experiment's tests (`test_r04_evidence.py`, `test_r04_nuisance.py`), the two that
  `am1-keepset-search-v1`'s selftest also found failing on `main`. This branch changes no
  existing code. At `8624a08b`, after round 1: the memcredit tests 120 passed; the whole suite
  3,574 passed, 64 skipped and the same 2 failed (`logs/pytest-full-suite-*-summary.txt`).

## Files

- `results.json`, `per-table.json.gz`, `tables.md`: `analyze --development-features` outputs,
  text-free. `dryrun-compare.json`; `power.json`.
- `jobs/1471-development/`: the lane records; `am3g/` holds the driver summary and environment,
  per-step records and progress logs, per-pass metadata, the SHA-256 of every raw pass file, worker
  logs and a text-free copy of the judge items (each response replaced by its SHA-256).
- `builds/`, `selftests/`, `manifests/`: the image build, the two CPU selftests and the lane
  manifest with its dry run.
- `prepare/`: the abstention population's text-free summary and the prepare command's output.
- `logs/`: extract, analyze, `dryrun-compare`, `power` and pytest logs; `logs/confirm-*.log`:
  the reruns at the later commits.
- `adhoc/`: the in-image pin checks (jobs 1472, 1473, 1474; scripts and outputs).
- `hand-check/`: the development hand check's receipt, the labels' SHA-256 and the sample's
  counts and digests (the sample and the labels stay on the host).
- `ops/`: `jobs.log` and `preflight.log`. The scripts themselves are `ops/am3g/` at the commit.
- The staging script searched every staged file for each of the 3,717 texts of at least 12
  characters (every distinct reply, and every question, answer, decoy and memory text of the
  development and abstention artifacts) and found none. Home paths are written as `~`.
- Raw outputs stay on the host under `~/cotcodec-runs/stage0/am3g-dev-dryrun/` (`runs/`,
  `private/`).
