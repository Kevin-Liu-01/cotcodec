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
- Q3 K1 screen: `sparse_indexer_torch.py` (capture path, hs and QSA Eq. 17 mp
  block targets, block indexer, selection and recall), `sparse_indexer_data.py`
  (Belebele join, ParaDocs filter reimplementation, filters, dedup, packing,
  bundle codec), `sparse_indexer_k1_stats.py` (xi, xi_rel, seed-plus-cluster
  interval, verdict) and `sparse_indexer_k1_runtime.py` (checkpoints, training,
  evaluation and receipt assembly for the GPU entry point).
- `publication_attestation.py` verifies administrator signatures over complete
  publication claim waves.
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

## Gotchas
<!-- agent-docs:fill:gotchas -->

- Doctor numbers are synthetic-case evidence only; they never lift the Compute
  doctor from FAIL.
