---
name: harness-benchmarks-skill
description: Procedure for benchmark adapters, task specifications, deterministic oracles, and benchmark readiness claims.
---

# cotcodec / harness/benchmarks

## Purpose
<!-- agent-docs:fill:purpose -->

Benchmark adapters translate external or custom task suites into the harness's
common task and evaluation interfaces without hiding benchmark-specific policy.

## Mental model & key files
<!-- agent-docs:fill:model -->

- `base.py` defines the adapter contract.
- One module owns each external benchmark.
- `orchvar_canary*.py` plus `specs/*.yaml` own the custom regression tasks and
  exact tool/action oracles.
- Task specifications are research inputs: version and validate them like code.

## Patterns to follow / invariants
<!-- agent-docs:fill:patterns -->

- An adapter is implemented only when task loading, environment/tool execution,
  scoring, and trace validation all work on a 3–5 task pilot.
- Keep benchmark source IDs and splits stable; never relabel an observed task.
- Prefer deterministic exact-key or state-transition oracles. LLM judges require
  a separate contract, prompt/version provenance, and calibration evidence.
- Report protocol, benchmark, and safety failures separately.

## Common tasks → first action
<!-- agent-docs:fill:tasks -->

- New external benchmark: read `base.py`, pin upstream data/revision/license,
  implement one task, then add a focused test before bulk ingestion.
- OrchVar task edit: update the spec, oracle, validator, and tamper tests together.
- Readiness audit: verify the adapter is not a stub before queueing any spend.

## Gotchas
<!-- agent-docs:fill:gotchas -->

- File presence and registry entries do not imply runnable benchmark support.
- Never tune an oracle after seeing treatment output; create a new task/spec version.
