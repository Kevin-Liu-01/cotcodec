---
name: harness-metrics-skill
description: Procedure for deterministic metric collection, paired degradation tests, safety gates, fertility, and Pareto analysis.
---

# cotcodec / harness/metrics

## Purpose
<!-- agent-docs:fill:purpose -->

Metrics turn raw trace events into auditable per-cell and cross-condition
measurements for success, cost, latency, safety, fidelity, and degradation.

## Mental model & key files
<!-- agent-docs:fill:model -->

- `collector.py` owns per-step observations.
- `analyzer.py` aggregates conditions and Pareto frontiers.
- `degradation.py` owns exact-key paired comparisons and McNemar analysis.
- `fertility.py` measures tokenizer fragmentation; `safety.py` owns red-line gates.

## Patterns to follow / invariants
<!-- agent-docs:fill:patterns -->

- Collect all inexpensive raw metrics before aggregation.
- Pair on immutable task/seed/model keys; reject duplicates and missing mates.
- Report denominators, confidence/uncertainty, and incomplete cells explicitly.
- Do not impute failed or missing runs as successes.
- Safety failures remain first-class outcomes and can kill an otherwise efficient arm.

## Common tasks → first action
<!-- agent-docs:fill:tasks -->

- Metric change: update collector schema, analyzer, fixtures, and backward-compat tests.
- Degradation audit: verify exact pairing and discordant-cell counts before p-values.
- New safety rule: preregister threshold and baseline comparison before execution.

## Gotchas
<!-- agent-docs:fill:gotchas -->

- Statistical significance cannot rescue protocol-invalid or incomplete evidence.
- Tokenizer fertility, billed tokens, and retained context bytes are different measures.
