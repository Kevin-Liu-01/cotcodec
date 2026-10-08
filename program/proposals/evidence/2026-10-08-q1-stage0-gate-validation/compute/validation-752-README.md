# Q1 Stage 0 validation job under `q1-stage0-exec/2` (decision D37 iii)

Branch `stage0/q1-exec2-validation`. Rule `q1-exec2-validation/1`
(`harness/q1/exec2_validation.py`), driver `scripts/run_q1_exec2_validation.py`,
template `experiments/manifests/q1-core/q1-exec2-validation.template.yaml`,
registered in preregistration section 18.10 at commit `23a8768` before the job ran.
Label: **infrastructure and cost, not a Stage 0 result.**

## What ran

| Step | Record |
|---|---|
| Image | CPU-only Slurm 746 (5 min 29 s) built `cotcodec-q1-gates:23a87683` from a fresh clone of `23a8768` (`image-build-receipt-746.json`; image `sha256:28853b9a...`, source tar `8d35417c...`) |
| CPU check | GPU-less, network-less container of that image (CPU-only `srun`): `--plan-only` on the re-pilot artifact gives 433 items, `items_sha256 633b2753...`, the same as on the laptop; the card hashes equal section 2.1 (`gate b5f4fa74...`, `audit b10a62f7...`, `driver aa2f365d...`); 38 tests passed |
| Before submitting | `pre-submit-state.txt`: empty queue, all 8 GPUs at 0 MiB with no compute processes |
| Lane | `q1-exec2-validation-23a87683.yaml`: dry-run (`dry-run.json`, 0.1667 GPU-h), test-only (`test-only.txt`, exit 0), one submission |
| Job | Slurm 752, `COMPLETED 0:0`, 6 min 33 s on one H100 (`slurm-752.txt`, `job-752/`); provenance PASS; GPU prolog exclusive; termination `completed`, no hard stop, no signal |
| GPU-hours | **0.1092 physical** (393 s). D31's 0.5 now holds 0.330 + 0.109 = 0.439 |

## Safety under `q1-stage0-exec/2` (items that ran)

| Quantity | Job 752 (exec/2) | Job 713 (exec/1, for reference) |
|---|---:|---:|
| Items started / final (distinct items) | 122 / 122 | 691 / 598 (699 attempts) |
| Items never final | 0 | 93 |
| GPU resource failures (out of memory and the other `faults` markers), item attempts | 0 (0 shared, 0 alone) | 97 shared |
| Contention retries (out of memory or timeout, shared) | 0 | 100 |
| Failed health checks / recovered alone / failed alone | 0 / 0 / 0 | 5 slots retired |
| Slots or devices retired | 0 | 5 slots |
| A5 `na` checks | 0 (9 A5 rows) | 11 (39 A5 rows) |
| Memory-guard waits / unreadable readings | 0 / 0 | not in exec/1 |
| Largest concurrent sum of measured peaks | 24.2 GB (guard budget 68 GB) | n/a |
| Measured peak over estimate | median 0.35, max 1.12 (5 items above 1) | n/a |
| Cut at the hard deadline / never started (time box) | 1 / 310 | 0 / 178 deferred |

- The one `crashes` count is the cut item (L2/59 `ref_c`, killed at the 390 s hard
  deadline after 20 s; `job-752/cut.jsonl`); no health check runs after a stop.
- The five items above their estimate are gate (c) or `ref_c` on L1/1 and L1/10
  (3.99 GB measured against 3.55 GB estimated, at most): still inside one unit
  (5.67 GB), but the estimate is not a strict upper bound.
- A5 gave `error` (not `na`) on `non_default_stream` in both arms: PRC-01 and PRC-02
  raise `TypeError: cannot pickle 'module' object` on all three adversarial controls
  (A5 copies a candidate that holds a CUDA extension module). Not a store or memory
  effect; a limit of A5 on `load_inline` candidates.
- Re-pilot items that also ran in job 713 (store arm, same kernel and gate): 64 of 65
  have identical verdict rows. The one difference is L2/59's substrate on
  `A4_poison`: a reject in 713 (`CUDA error: invalid argument` while moving 4.3 GB of
  parameters under the poison allocator at 12 per GPU) and an accept here. That text
  is not in `faults.RESOURCE_MARKERS`, so under memory pressure the contention rule
  would not retry it.

**Coverage limit.** The time box reached the adversarial controls, the substrates of
L2/95, L2/77 and L1/10 (all 15 gates), L1/18's substrate (10 gates; its five store
consumers never started, every slot thread then holding a queued 6-unit L2/59 item)
and 10 non-consumer gates plus two reference items of L2/59's substrate. L2/87 and
L2/100 (two of the three problems that ran out of memory in 713), L2/46, L2/59's
consumer gates at 8 units, every identity control and every mutant were not reached. One
item ran at one per GPU (L2/59 `ref_A1`, 8 units). The safety record covers 12 and
2 items per GPU only.

## Adversarial controls under the store (consumer gates, store against inline twin)

| Control | c (c1, c2, c3, c_1e-2, c_kbv_raw) | A1 | A2 | A3 | A5 |
|---|---|---|---|---|---|
| `result_reuse` | reject / reject | reject / reject | reject / reject | reject / reject | reject / reject |
| `zero_out` | reject / reject | reject / reject | reject / reject | reject / reject | reject / reject |
| `non_default_stream` | accept / accept | accept / accept | accept / accept | accept / accept | error / error |

Every aggregate verdict is the same through the store and inline (15 of 15 pairs);
verdict rows are identical in 10 pairs and verdict multisets in 13. All differences
are `result_reuse`, whose output is `torch.empty` (it reads memory it never wrote;
the documented allocator-history exception, section 18.8 item 4): inline, gate (c)
accepted 7 of its 16 configurations with error 0.0, because the freed reference
output was handed back to the candidate (the attack KernelBench wrote it for);
through the store no reference output is freed in the candidate's process and all 16
configurations reject. A2 differs on one draw and A1, A3 and A5 in error fields only.
Every store lookup was used (30 of 30; 27 usable entries, none unusable).

## Cost against the `q1-stage0-exec/2` model

`exec2-validation.json` (pre-specified analysis; `analyze_exec2_validation.py`) and
`posthoc-regime-split.json` (post hoc). GPU-seconds are each item's share of the GPU
while it ran. The device was busy 369.9 s of the 390 s window with 8.6 items running
on average; the adversarial controls took 149.7 GPU-s (40%), their items running 31-95
s each while their CUDA extensions compiled.

| Set (re-pilot store items) | Items | Measured GPU-s | exec/2 model GPU-s | Measured / model |
|---|---:|---:|---:|---:|
| All (scoring and reference items): **R** | 87 | 220.2 | 90.8 | **2.425** |
| Scoring items | 65 | 161.6 | 52.6 | 3.07 |
| Reference items | 22 | 58.6 | 38.2 | 1.53 |
| 12 per GPU (four light problems, all during the adversarial compiles) | 55 | 76.6 | 39.2 | 1.96 |
| 2 per GPU (L2/59, after the adversarial phase) | 10 | 85.0 | 13.4 | 6.35 |
| By problem: L1/10, L1/18, L2/77, L2/95, L2/59 | 20, 15, 20, 20, 12 | | | 0.82, 1.26, 1.86, 2.11, 7.79 |
| Same items in job 713 (exec/1, store arm) | 86 | 213.7 | 132.0 (713) | 1.62 (exec/2 over exec/1) |

Per gate (measured / model): a 3.91, a_1e-3 4.91, a_head_1e-4 2.58, a_head_1e-2 5.87,
a_static 8.12, b1 4.64, b2 2.39, c 1.17, A1 1.23, A2 1.85, A3 1.16, A4 3.59,
A4_poison 2.97, A4_sanitizer 2.43, A5 2.45; reference items ref_c 0.90, ref_A1 3.04,
ref_A2 0.74, ref_A3 1.24, ref_A5 2.02. The non-consumer gates include L2/59 and the
consumer gates do not (its consumers were not reached), so per-gate ratios mix
problems. Two effects drive R: L2/59 items take about 16 s alone (its 4.3 GB of
parameters, not its 17 MB of inputs, set the process cost) and run 2 per GPU, where
the input-sized model charges under 1 GPU-s; and the light items ran 1.5-2.4 times
their job-713 wall times while the adversarial controls compiled on the same 32 CPUs.
The first is a property of the policy and the model; the second is this job's
contention and is smaller in Stage 0, where the adversarial controls are 135 items
(3 controls, 15 gates, 3 replicates) of several thousand.

## Stage 0 projection recomputed (GPU-h, central / high; fixed part 4.294 including this job's 0.109)

| Row | Status | Through P3 | Through P7 |
|---|---|---:|---:|
| A: exec/2 without the store (fix pass model) | model | 10.57 / 12.41 | 15.16 / 18.35 |
| B: exec/2, store without gate (a), linear ratio, per job (fix pass model) | model | 10.77 / 12.69 | 15.67 / 19.06 |
| **C: B scaled by R = 2.425** | **pre-specified primary** | **19.99 / 24.66** | **31.89 / 40.10** |
| C at R's bootstrap 2.5% point (1.140; 5 problems) | pre-specified | 11.68 / 13.87 | 17.27 / 21.13 |
| C at R's bootstrap 97.5% point (4.837) | pre-specified | 35.60 / 44.92 | 59.33 / 75.71 |
| D: B with per-gate scales | pre-specified (secondary) | 18.14 / 22.26 | 27.04 / 33.81 |
| E: A scaled by the store-independent gates' ratio 3.475 | pre-specified (secondary) | 26.11 / 32.51 | 42.05 / 53.13 |
| F: 12-per-GPU items x1.955, fewer x6.349, references x1.533 | post hoc | 35.33 / 44.56 | 51.69 / 65.79 |
| G: 12-per-GPU items at the model, fewer x6.349, references x1.533 | post hoc | 34.26 / 43.17 | 50.12 / 63.75 |

"High" is the card's convention (fixed part plus scoring times the matching
registered scenario's bootstrap scale). Rows C-G scale a model by a partial sample
that the rule's cheapest-first order selected: the problems the model expects to be
most expensive (L2/46, L2/100, L2/87) carry R without having been measured, and the
fewer-than-12 ratio of F and G rests on one problem. **No row is within 8 GPU-h
through P3; even R's bootstrap lower point gives 11.68 central.** The exec/2 model of
section 18.9 is biased low on this evidence, most where items run fewer than 12 per
GPU.

## Corrections and files

- `analyze_exec2_validation.py` was committed with the rule. After the job one bug was
  fixed: the adversarial comparison grouped rows by the row's gate, and gate (c) items
  write rows `c1`, `c2`, `c3`, `c_1e-2`, `c_kbv_raw`, so the first run found no gate
  (c) pair. It now groups by the item's gate; no other quantity changed.
  `posthoc_regime_split.py` and `exposure_entry.py` were written after the data.
- `validation-752-exposure.json`: the exposure ledger entry (8 kernels scored: five
  S1-cal substrates already exposed by job 713 and the three adversarial controls
  already listed in `pilot_exposed.json`; no evaluation unit).
- Raw journals, worker logs and the store's manifests stay in the run root on the
  host (`~/cotcodec-runs/stage0/q1-exec2-validation/runs/752`); `job-752/` holds the
  driver summary, plan, phases, memory records, the cut record and the lane files.
- Inputs not committed: `stage0-counts-v2.json` (host-only, SHA-256 `246e0fb6...`,
  the file every earlier card used) and job 713's run directory.
