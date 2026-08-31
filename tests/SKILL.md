---
name: tests-skill
description: Procedure for focused unit, contract-tamper, lifecycle, evidence, and integration tests.
---

# cotcodec / tests

## Purpose
<!-- agent-docs:fill:purpose -->

Tests enforce both software behavior and scientific fail-closed boundaries. Each
experiment family should prove valid inputs pass and decision-bearing drift fails.

## Mental model & key files
<!-- agent-docs:fill:model -->

- Test modules mirror harness and script names.
- `test_memory_experiments.py`, `test_memory_sources.py`, and
  `test_memory_portfolio.py` are directory/ledger routing gates.
- `*_evidence.py` tests validate sealed bundles; `*_doctor.py` tests the contained
  observation logic without requiring the full external runtime.

## Patterns to follow / invariants
<!-- agent-docs:fill:patterns -->

- Add focused behavior tests, contract tamper tests, and routing tests together.
- Use temporary directories and synthetic canaries; do not mutate sealed evidence.
- Assert incomplete, duplicate, corrupt, or mismatched evidence fails closed.
- Keep remote/container requirements out of default unit tests unless explicitly marked.

## Common tasks → first action
<!-- agent-docs:fill:tasks -->

- Bug fix: reproduce with the narrowest failing test before patching.
- New lifecycle gate: test normal projection, each falsifier, two-repeat agreement,
  source/image mismatch, and unexpected status.
- Before commit: run focused tests first, then the relevant directory validators,
  followed by the full suite when feasible.

## Gotchas
<!-- agent-docs:fill:gotchas -->

- Do not weaken expected hashes/statuses to make an observed run pass.
- A test over a portable bundle does not replace checking the raw run manifest.
