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
- `versions.py` is the version card the preregistration names.

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
| Write the Stage 0 report | `scripts/report_q1_stage0.py --journal J --corpus C --replay-journal O/journal.jsonl --calibration audit-v1.json --output R` |

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
- A worker crash after the candidate loads is a rejection, so a concurrency-
  induced CUDA out-of-memory error would be charged to the candidate; it must
  become an infrastructure failure before running more than 4 items per GPU
  on problems above 0.6 GB.
- The runner never journals an item it kills at the hard deadline;
  `cost_card.censored_items` recovers it as a lower bound.
