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
  bundle codec), `sparse_indexer_k1_stats.py` (xi, xi_rel, the seed-plus-cluster
  interval with a Welch-Satterthwaite t quantile, the verdict, the V1
  extension rule and the final verdict of program decision D16) and `sparse_indexer_k1_runtime.py` (checkpoints with
  completion records, training, evaluation and receipt assembly for the GPU
  entry point; evaluation loads exactly the completed final generation).
- Q3 K1 successor (v2): `sparse_indexer_bank.py` (batched indexer bank per
  layer: stacked cells, per-slot clipping, one Adam per cell, row-chunked
  causal KL; exact composite-key top-k selection), `sparse_indexer_k1_runtime_v2.py`
  (v1's workers on the bank, timed per step and per unit),
  `sparse_indexer_k1_budget_v2.py` (torch-free registered limit formula and
  smoke gate) and `sparse_indexer_k1_equivalence_v2.py` (the device TF32 gates
  the throughput probe runs). None of v1's tabled files changes.
- `publication_attestation.py` verifies administrator signatures over complete
  publication claim waves.
- `remote_zip.py` reads selected members of pinned remote ZIP archives by HTTP
  range (CRC-checked, cached, at most 6 concurrent requests);
  `osworld_source.py` fetches OSWorld files bound to a commit by git blob SHA-1.
  `holo3_rerun_audit.py` and `holo3_v2.py` are Q2's Holo3 rerun audit (v1
  post-hoc reproduction, v2 rules).
- `serving_probe/` is the CPU-testable core of the vLLM serving probe: contract
  loader, synthetic screenshots and prompts, the OSWorld (h1) and cua-speedrun
  (h2) message layouts, the streaming client and episode replay, metric parsing
  and the preregistered budget rules. Only `cuda_doctor.py` and
  `triton_kernels.py` import torch or Triton.
- `serving_probe_v2/` is serving-throughput-probe-v2, built beside the frozen
  v1 package (never edit `serving_probe/`: its digest is frozen with v1): the
  v2 contract loader, the contamination rule (foreign processes by PID, own
  growth against a largest-shape reservation), the launch-window ledger, the
  identified client with prebuilt replay history, and control X1 on identical
  prompt token sequences.
- `q2_mutation/` is Q2's OSWorld checker-mutation harness: the binding
  `schema.py`, task scope and sanitization, the GUI-faithful LibreOffice save
  stage, the offline `evaluate()` scorer, clustered statistics, the D9
  rater protocol, the operator catalog (`q2_mutation/operators/`) and the
  campaign driver that joins specs, operators and scorer
  (`q2_mutation/campaign.py`). Runbook: `q2_mutation/README.md`.
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
