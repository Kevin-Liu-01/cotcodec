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
