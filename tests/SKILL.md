---
name: tests-skill
description: Procedure for focused unit, contract-tamper, doctor and submitter tests.
---

# cotcodec / tests

## Purpose
<!-- agent-docs:fill:purpose -->

Tests enforce both software behavior and scientific fail-closed boundaries.
Each contract proves valid inputs pass and decision-bearing drift fails.

## Mental model & key files
<!-- agent-docs:fill:model -->

- Test modules mirror script and harness names.
- `test_architecture_contracts.py` tampers with the live D21 contract.
- `test_submit_*` cover manifest validation, sbatch rendering and the
  fail-closed rejection of archived memory workloads.
- Pre-restart tests are in `legacy/tests/` and are not collected.
- Q3 K1 tests that need torch (`test_sparse_indexer_torch.py`,
  `test_sparse_indexer_k1_runtime.py`, `test_run_sparse_indexer_phase0a.py`,
  `test_sparse_indexer_k1_doctor.py`) skip without the architecture extra; run
  them inside the research image (CPU, `--network none`).
  `test_sparse_indexer_k1_prereg.py` binds the K1 preregistration's code table
  to the working tree until the experiment is frozen.
- K1 successor: `test_sparse_indexer_bank.py` (float64 and exact equivalence
  with v1's per-indexer code), `test_run_sparse_indexer_phase0a_v2.py`,
  `test_probe_sparse_indexer_k1_throughput.py` and
  `test_sparse_indexer_k1_v2_doctor.py` need torch;
  `test_sparse_indexer_k1_budget_v2.py`, `test_sparse_indexer_k1_v2_manifests.py`
  and `test_sparse_indexer_k1_v2_prereg.py` mostly do not.
  `test_sparse_indexer_bank_gpu.py` runs only with `COTCODEC_GPU_TESTS=1` on a
  Slurm-allocated GPU inside the image.
- Dense headroom pre-check: `test_dense_headroom_data.py`,
  `test_dense_headroom_stats.py`, `test_dense_headroom_manifests.py` (the
  filler's run-root accounting and slot claims for every job, a filled
  manifest submitted twice, the 4B lane's smoke-reproduction gate, and a
  filled continuation through the entry point's manifest check),
  `test_dense_headroom_prereg.py` (binds the draft's code table to the tree
  until frozen) and `test_summarise_dense_headroom_precheck.py` run without
  torch; `test_dense_headroom_torch.py` and
  `test_run_dense_headroom_precheck.py` (end to end on CPU) need the image
  (the K1 v2 pytest overlay supplies pytest there).
- `_holo3_world.py` builds in-memory stand-ins for the Holo3 and OpenCUA
  archives that reproduce the real leaderboard cells, so the audit's controls
  and tamper cases run without network.
- `serving_probe_fakes.py` (not collected) holds a word tokenizer, a fake
  vLLM server on `httpx.MockTransport` and a stand-in for vLLM's offline request
  bookkeeping for the serving-probe tests.
- `serving_probe_v2_fakes.py` (not collected) adds the v2 fakes: a server that
  streams prompt token ids, and device and compute-process timelines.
- `test_open_weight_review.py` runs the reviewer on a scripted fake engine
  (retry, replicates, signals, receipts) and the vLLM adapter and doctor on
  fake `vllm`, `transformers` and `torch` modules; no GPU or vLLM needed.

## Patterns to follow / invariants
<!-- agent-docs:fill:patterns -->

- Add behavior, tamper and routing tests together.
- Use temporary directories and synthetic canaries; never mutate sealed evidence.
- Keep remote or container requirements out of default unit tests.

## Common tasks → first action
<!-- agent-docs:fill:tasks -->

| Task | First action |
|---|---|
| Run everything | `uv run pytest -q tests` |
| Run one doctor's tests | `uv run pytest -q tests/test_<name>_doctor.py` |

## Gotchas
<!-- agent-docs:fill:gotchas -->

- `test_doctor_runs_end_to_end_and_refuses_to_overwrite` asserts wall time
  under 60 s. On a heavily loaded laptop it can fail with low CPU time; rerun
  on an idle machine before debugging.
