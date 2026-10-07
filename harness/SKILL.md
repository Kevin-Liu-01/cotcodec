---
name: harness-skill
description: Procedure for CoTCodec mechanisms, doctors and attestation helpers in harness/.
---

# cotcodec / harness

## Purpose
<!-- agent-docs:fill:purpose -->

`harness/` holds the mechanisms behind live questions and the shared
attestation helpers. It starts small after the 2026-10-06 restart.

## Mental model & key files
<!-- agent-docs:fill:model -->

- `translation_supervised_indexer.py` is Q3's NumPy Phase-0 mechanism: indexer,
  targets, reference sets, statistics and gates as pure functions.
- `publication_attestation.py` verifies administrator signatures over complete
  publication claim waves.
- `q1/` is Q1's Stage 0 gate stack: shared `schema.py`, gates (a)-(c), the
  independent audit, runner/worker/journal, analysis, the mutator (`q1/mutate/`)
  and the substrate builders (`q1/substrates/`). `q1/README.md` maps it;
  `program/preregistrations/q1-stage0-gate-validation.md` is its draft
  preregistration.
- The old agent loops, conditions, metrics, routing and memory trials are in
  `legacy/harness/`.

## Patterns to follow / invariants
<!-- agent-docs:fill:patterns -->

- Deterministic code owns scheduling, accounting, validation and persistence;
  a model is only the treatment actor.
- Gates are pure functions with hand-made table tests for each direction.
- Raise a typed contract error on leakage, causality violations and degenerate
  inputs; never coerce them into results.
- Every output records seed, inputs' hashes and the code revision.

## Common tasks → first action
<!-- agent-docs:fill:tasks -->

| Task | First action |
|---|---|
| Add a question's mechanism | Write its contract in `experiments/` first, then the module and a doctor. |
| Change Q3 gates | Read the D21 contract and `tests/test_translation_supervised_indexer_doctor.py`. |
| Change any Q1 code or data | Run `tests/test_q1_*.py` in a GPU-less container, then `python scripts/q1_version_card.py --markdown` and update the preregistration's version table. |

## Gotchas
<!-- agent-docs:fill:gotchas -->

- Doctor numbers are synthetic-case evidence only; they never lift the Compute
  doctor from FAIL.
- `harness/q1/schema.py` is binding on every Q1 component; never edit it in a
  component branch.
- Running Triton kernels under `TRITON_INTERPRET=1` patches `triton.language`
  for the whole process. Compile for sm_90 (the mutant compile filter) only in
  a fresh process without that variable.
- S1 substrates target CUDA: they refuse CPU tensors and refuse sizes below 2.
  CPU tests port their host code explicitly (`tests/test_q1_integration_cpu.py`).
