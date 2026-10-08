---
name: harness-q1-skill
description: Procedure for the Q1 Stage 0 kernel gate stack, mutator and substrate corpus in harness/q1/.
---

# cotcodec / harness / q1

## Purpose
<!-- agent-docs:fill:purpose -->

Q1 Stage 0 measures how often three kernel correctness gates accept kernels an
independent audit rejects, and how often they reject correct kernels, on a
corpus of compiler-generated and human-written Triton kernels and their
deterministic mutants. The draft preregistration is
`program/preregistrations/q1-stage0-gate-validation.md`.

## Mental model & key files
<!-- agent-docs:fill:model -->

- `schema.py` is the binding interface: substrate, mutant and control
  directories and verdict rows. Every component reads and writes it.
- `substrates/` builds the corpus (S1 Inductor conversion, S2 catalog,
  admission, the S1 split); `mutate/` derives mutants, the cap, the dev/test
  split and hack controls; `controls.py` builds the core controls.
- `runner.py` runs one `worker.py` process per kernel x gate x seed with a
  phase watchdog and an append-only journal; `gates/` and `audit/` produce the
  rows; `analysis.py` composes the ladder, tiers, metrics and control checks.
- `versions.py` is the version card the preregistration names; `driver_sha256`
  binds what decides what Stage 0 scores (`trim.py`, `pilot.py`,
  `cost_card.py`, `data/pilot_exposed.json` and the drivers).
- `trim.py` is the trimming rule `q1-stage0-trim/2`: seeded frames and samples,
  the FRR set with its margin, the control schedule, buckets P1-P8, the
  concurrency units and the budget check. `scripts/run_q1_stage0.py` runs its
  plan and nothing else; the report reads the same `plan.json`.

## Patterns to follow / invariants
<!-- agent-docs:fill:patterns -->

- Never edit `schema.py` from a component branch; record a needed change.
- Config ids must match `schema.CONFIG_ID_RE` where they are made
  (`shapes.root_label`); the worker never lets a row-building failure become a
  candidate rejection.
- Mutant metrics need the parent filter and one kernel set across gates;
  unrefereeable families and A2/A3 channels are vacuous per problem
  (`analysis.compose(problem_of=...)`).
- `gates/gate_b.py` is a spec-only rewrite (KernelGYM has no licence): change
  it from `KERNELGYM_SPEC.md` and black-box probes of the clone, never from
  KernelGYM's source.
- Splits come from their owners (`substrates/split.py`, `mutate/sampling.py`);
  the analysis never re-derives them.
- Agent-written Triton never runs with GPU access (D3, D7). CPU fixtures run
  under `TRITON_INTERPRET=1` in GPU-less containers only.
- After any change to Q1 code or data, regenerate the preregistration's
  version table with `python scripts/q1_version_card.py --markdown`.
- Every random choice of the trimming rule is a seeded permutation
  (`trim.seed_of`); a sample is a prefix of it, so a cut leaves a simple random
  sample. Never draw with an unseeded RNG or reorder a frame by outcome.
- Pilot-exposed kernels (`data/pilot_exposed.json`, hash-pinned in
  `trim.PILOT_EXPOSED_SHA256`) never enter a sampling frame; regenerate the file
  only with `scripts/q1_pilot_records.py` and update the pin (decision D28).
- The reference store (`refstore.py`, decision D31) must never change a verdict
  row: reference-side code lives in one function per channel that both the
  inline path and the reference item call; a consumer adds no row keys and
  computes inline whenever an entry is missing, unusable or unreadable. Rerun
  `tests/test_q1_refstore_equivalence.py` and the integration CPU test after
  any change to a gate's or channel's reference side.
- An audit change chosen after seeing a pilot verdict is data-motivated: design
  and validate it on S1-cal and non-evaluation kernels only, and name the units
  it affects in `pilot_exposed.json["data_motivated_units"]`.

## Common tasks → first action
<!-- agent-docs:fill:tasks -->

| Task | First action |
|---|---|
| Run the Q1 tests | GPU-less container with `cotcodec-q1-gates`: `python -m pytest -q tests/test_q1_*.py` |
| Run the CPU doctor | `experiments/manifests/q1-core/q1-gate-doctor-cpu.md` |
| Change shape rules | Edit `shapes.py`, then `scripts/build_q1_shape_manifest.py --write` in a container |
| Build controls | `python -m harness.q1.controls --out-root R` |
| Calibrate the audit (M, audit v1) | `scripts/q1_calibrate_audit.py --journal CAL --corpus C --output audit-v1.json` |
| Adjudicate gate rejections of audit-accepted kernels | `scripts/q1_audit_hole_replay.py --journal J --corpus C --output O --multiplier M --seeds 42 43 44` |
| Write the Stage 0 report | `scripts/report_q1_stage0.py --journal J --corpus C --replay-journal O/journal.jsonl --calibration audit-v1.json --plan PLAN.json --output R` |
| Measure the reference store (re-pilot, D31) | `scripts/q1_prepare_repilot_corpus.py` (CPU), then `experiments/manifests/q1-core/q1-repilot-d31.template.yaml`, then `scripts/q1_pilot_cost_card.py ... --repilot-job RUNS/JOB` |
| Plan Stage 0 (CPU) | `scripts/run_q1_stage0.py --corpus C ... --output OUT --seeds 42 43 44 --plan-only` (records `plan_sha256`) |
| Run a Stage 0 job | `experiments/manifests/q1-core/q1-stage0-trim-job.template.yaml` (buckets, plan hash, spent GPU-h and caps filled from the ledger) |
| Bind pilot run records / list exposure | `scripts/q1_pilot_records.py --job RUNS/474 --job RUNS/518 --job RUNS/548 --corpus ... --records R --exposed E` |

## Gotchas
<!-- agent-docs:fill:gotchas -->

- The Triton interpreter patches `triton.language` for the whole process;
  compile for sm_90 only in a fresh process without `TRITON_INTERPRET`.
- S1 substrates refuse CPU tensors and sizes below 2; gate (c) shapes are
  floored at 2 for that reason, while audit A3 keeps size 1.
- Gate (a)'s absolute tolerance 1e-2 hides errors on outputs far below 1e-2
  (softmax over many columns).
- Any probe that runs a candidate at a held-out shape must skip shapes the
  candidate refuses before launch (S1 refuses size 1 and fp16/bf16): the
  pilot's compute-sanitizer probe did not, and A4 was `error` for every S1
  kernel until `gpu_probes.run_first_accepted`. A5 still counts dtype
  refusals as failures (open, preregistration section 18.3).
- Cost is dominated by native input size and per-process overhead, not GPU
  compute: items of problems under 0.6 GB cost half as many GPU-seconds at 12
  per GPU as at 4 with identical verdicts (pilot job 548); problems of 1 GB or
  more run alone and can take over 10 minutes per gate (c on L1/89).
- A worker crash after the candidate loads is a rejection. Since the second
  review a shared item's watchdog timeout or CUDA out-of-memory error is an
  infrastructure failure retried once alone (`runner.contention_failure`,
  `retry_alone` survives a resume); alone, the outcome stands. Existing tests
  that run a hanging kernel on two slots now see two timeouts.
- The runner never journals an item it kills at the hard deadline; it records
  it in `cut.jsonl` with spawn and kill times, and `cost_card.censored_items`
  reads that (the pilot jobs predate it: mtimes, bound by
  `program/evidence/2026-10-07/q1-pilot/run-records.json`). With
  `fit_deadline` an item starts only if its watchdog limits end before the
  hard deadline.
- The c/b statistic is pinned in `analysis.c_over_b_statistic` (ratio of
  medians of per-kernel cumulative cost); report the other readings, never
  switch.
- The compute-sanitizer row runs at a held-out shape and reports memcheck
  alone; a post-launch crash there is A3's (`workload_raised_after_launch`).
