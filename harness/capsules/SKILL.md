---
name: harness-capsules-skill
description: Procedure for fail-closed portable execution capsules, schema verification, and memory-graph instrumentation.
---

# cotcodec / harness/capsules

## Purpose
<!-- agent-docs:fill:purpose -->

Capsules package declared orchestration inputs, memory graphs, receipts, and
verification metadata so an execution can be checked outside its source runtime.

## Mental model & key files
<!-- agent-docs:fill:model -->

- `schema.py` defines the wire contract.
- `runtime.py` executes admitted capsule operations.
- `verification.py` validates hashes, signatures, and declared capabilities.
- `memory_graph.py` handles capsule-local memory topology.

## Patterns to follow / invariants
<!-- agent-docs:fill:patterns -->

- Fail closed on unknown fields, algorithms, identities, capabilities, or hashes.
- Bind every decision to canonical serialized bytes and explicit versioning.
- Treat capsules as instrumentation after a real agent loop exists, not as a
  universal orchestration protocol or a scientific result by themselves.

## Common tasks → first action
<!-- agent-docs:fill:tasks -->

- Schema change: add a new version plus conformance/tamper vectors.
- Runtime change: update capability declarations and negative verification tests.
- Evidence export: run capsule conformance before referencing the artifact.

## Gotchas
<!-- agent-docs:fill:gotchas -->

- Never accept a trust key shipped inside the artifact it authenticates.
- Hash-valid structure does not establish semantic correctness or model quality.
