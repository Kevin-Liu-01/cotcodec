---
name: harness-memory-trials-skill
description: Procedure for frozen memory controls, lifecycle studies, causal holdouts, provider adapters, and matched memory-system trials.
---

# cotcodec / harness/memory_trials

## Purpose
<!-- agent-docs:fill:purpose -->

`memory_trials/` provides the controlled tasks and analysis primitives for
studying memory policy without conflating storage conformance with memory quality.

## Mental model & key files
<!-- agent-docs:fill:model -->

- `models.py` and `schema.py` define shared records and canonical serialization.
- `engine.py`/`collection.py` run trials and retain diagnostics.
- `frozen.py`, `splits.py`, and `quality.py` own immutable controls and scoring.
- `lifecycle.py`/`lifecycle_study.py` test CRUD, restart, isolation, retry, and purge.
- `systems.py`, `sidecar.py`, and provider modules isolate runtime integrations.
- Specialized modules own causal holdouts, procedural memory, and graph controls.

## Patterns to follow / invariants
<!-- agent-docs:fill:patterns -->

- Freeze task bundles and splits before treatment execution.
- Match prompt, retrieval, tool, write, and latency accounting across arms.
- Use only past-available features for gates or learned controls.
- Record lifecycle/conformance and semantic-quality outcomes separately.
- Preserve native failures; do not patch an upstream system inside its treatment
  arm unless the repair is a separately named, preregistered arm.

## Common tasks → first action
<!-- agent-docs:fill:tasks -->

- New system: complete exact-source and lifecycle admission before quality screens.
- New control: add deterministic paired audit and frozen fixtures first.
- New judge: bind prompt/model identity and test score stability on known cases.
- Causal trial: verify eligibility, propensity logging, overlap, and paired replay.

## Gotchas
<!-- agent-docs:fill:gotchas -->

- Successful CRUD/restart is not evidence of useful memory.
- A failed lifecycle gate forbids actor escalation for that revision but does not
  establish that every later revision or different mechanism is broken.
