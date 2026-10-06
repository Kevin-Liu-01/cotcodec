---
name: harness-conditions-skill
description: Procedure for language, compression, structure, degradation, and routing conditions applied to visible agent messages.
---

# cotcodec / harness/conditions

## Purpose
<!-- agent-docs:fill:purpose -->

Conditions implement the controlled orchestration intervention for a message
while leaving benchmark semantics and fixed protocol surfaces unchanged.

## Mental model & key files
<!-- agent-docs:fill:model -->

- `base.py` defines the transformation interface.
- Language conditions (`english.py`, `chinese.py`, `polish.py`) are Paper 1 arms.
- `controlled.py`, `compressed.py`, and `structured.py` alter constrained format.
- `router.py` selects a condition from message features; `degraded.py` is a
  deliberate regression control.

## Patterns to follow / invariants
<!-- agent-docs:fill:patterns -->

- Transform only message types declared variable by the experiment.
- Keep tool names, JSON schemas, raw tool outputs, and final responses fixed in
  English unless the experiment explicitly varies that surface.
- A condition must be deterministic under its declared seed/config and expose
  enough metadata to reproduce the transformation.
- Register conditions in config and test representative terminology-heavy inputs.

## Common tasks → first action
<!-- agent-docs:fill:tasks -->

- New condition: subclass the base interface, add config registration and tests,
  then run a small message-only smoke before a benchmark pilot.
- Router change: read `harness/routing/SKILL.md` and verify features are past-only.

## Gotchas
<!-- agent-docs:fill:gotchas -->

- Do not claim hidden chain-of-thought manipulation; this project varies only
  framework-visible intermediate communication.
- Compression and reasoning format are distinct variables even when one
  implementation affects both; label the intervention honestly.
