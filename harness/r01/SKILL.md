---
name: harness-r01-skill
description: Procedure for the R01 first-step code (r01-rerun-noise-sources-v2, DRAFT) in harness/r01/: the onset-step request corpus, the Stage B replay driver, the P0 self-test, the A1 and Stage C open-loop runner, the estimator and the two-stage model.
---

# cotcodec / harness / r01

## Purpose
<!-- agent-docs:fill:purpose -->

R01 asks where S1a's greedy rerun disagreement starts. Its first step measures,
at the divergence-onset step, how often each source alone (serving numerics,
the clock region, other screen regions) changes the reply and the action, on
fixed requests rebuilt from fresh A1 captures, and replays S1a's recorded
actions open loop. Registration: `program/preregistrations/r01-rerun-noise-sources-v2.md`.
Nothing here has run a model or a VM; every module is tested on CPU against fakes.

## Mental model & key files
<!-- agent-docs:fill:model -->

- `regions.py`: the clock box fitted to the full label extent, region swaps and
  masks on raw PNGs, the pixel-difference census.
- `requests.py`: step-k bodies rebuilt by the frozen H-OSW-fixed client with a
  stub engine returning S1a's recorded replies; the 2 x 2 composites R, C, O, X;
  prompt-id fidelity; the seeded episode choice.
- `replay.py`: batch-1, cold/warm and loaded protocols, cache resets, atomic
  loaded passes, append-only results with fsync; a CLI for the GPU jobs.
- `p0.py`: the bitwise self-test, the log-probability check, Mamba-mode
  parsing and the per-job timing gate.
- `openloop.py`: S1a's runner subclassed for mode `a1` (frames, one open-loop
  step) and mode `stage-c` (recorded IR replay with two frames per step).
- `caps.py`: prices from S1a's realized step costs; the loaded-pass simulation.
- `estimators.py` and `stepkick.py`: the registered readings and the two-stage
  onset model (fit, validation on S1a, removal predictions).
- `fake_engine.py`: tests only; an OpenAI-compatible engine with controllable
  text, pixel and serving nondeterminism and vLLM's stream shape.

## Patterns to follow / invariants
<!-- agent-docs:fill:patterns -->

- Never edit `harness/q2_stage1/` (pinned by S1a's registration); import and
  subclass it.
- Composites act on raw PNGs before `agents.process_image`.
- Every live comparison is across two different seeded schedules; a loaded
  pass is atomic (voided and rerun whole when cut).
- The fake engine never serves a measurement.

## Common tasks → first action
<!-- agent-docs:fill:tasks -->

| Task | First action |
|---|---|
| Change a driver or reading | `uv run --locked --extra dev pytest -q tests/test_r01_*.py` |
| Re-run the operating characteristics | `PYTHONPATH=. uv run --locked python program/proposals/evidence/2026-10-11-r01-rerun-noise-sources/compute/repair-d75/power_r01_v2.py --out ...` |
| Re-price the caps | the same folder's `caps_r01_v2.py` |
