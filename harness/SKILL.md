---
name: harness-skill
description: Procedure for CoTCodec's deterministic experiment runner, live agent loops, traces, checkpoints, and provider boundaries.
---

# cotcodec / harness

## Purpose
<!-- agent-docs:fill:purpose -->

`harness/` is the product: a model-agnostic collector that runs controlled
orchestration interventions and emits reproducible traces, metrics, and resumes.

## Mental model & key files
<!-- agent-docs:fill:model -->

- `runner.py` loads experiment YAML, schedules cells, and writes traces/results.
- `agent_loop.py`, `iterative_*`, `two_stage_*`, and `live_*` implement admitted
  execution protocols; `receipted_tool_runtime.py` owns tool-attempt receipts.
- `run_state.py` owns checkpoint/journal semantics.
- `benchmarks/`, `conditions/`, `metrics/`, and `routing/` are replaceable axes.
- `memory_trials/` is a separate, source-bound memory evaluation subsystem.

## Patterns to follow / invariants
<!-- agent-docs:fill:patterns -->

- Deterministic code owns scheduling, accounting, validation, and persistence;
  the model is only the treatment actor.
- Vary only preregistered framework-visible messages. Tool schemas, tool results,
  and final-answer language stay fixed unless a contract explicitly says otherwise.
- Journal atomically before advancing a cursor; fresh-process resume must not
  duplicate or silently skip a completed cell.
- Preserve tool attempts, successes, and errors separately. Do not convert broad
  exceptions into model observations.
- Every trace records task, condition, model identity, seed, tokens, latency,
  tool behavior, safety outcomes, and completion status.

## Common tasks → first action
<!-- agent-docs:fill:tasks -->

- Runner change: read `runner.py`, `run_state.py`, and `tests/test_runner.py`.
- Live protocol change: read the matching loop, canary, runner, experiment
  validator, and evidence sealer as one dependency chain.
- New provider: implement behind the existing adapter boundary and capture the
  returned model identity; never scatter provider conditionals through the core.
- Resume behavior: test normal, signal-interrupted, budget-exhausted, and corrupt
  checkpoint cases before a remote run.

## Gotchas
<!-- agent-docs:fill:gotchas -->

- A completed process is not necessarily a completed experiment; check planned
  versus journaled cells and safety-gate reachability.
- Do not reconstruct missing live completions or tool receipts after a crash.
- Local deterministic admissions and live-model outcomes use different evidence
  statuses and must never be merged into one positive claim.
