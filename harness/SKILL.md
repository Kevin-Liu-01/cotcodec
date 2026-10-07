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
