# Variable 10: Tool Scheduling

**Status (2026-10-06):** Broad mechanism occupied. HEAR, ThunderAgent and
AsyncLLM are required comparisons. No new computer-work scheduling experiment
is admitted by the current literature assessment.

## The Variable

σ = scheduling ∈ {sequential, parallel_independent, speculative, lazy, priority_ordered}

In what order and with what parallelism should tool calls execute?

## Why It Matters

Scheduling affects latency, resource use and the validity of the state on
which an action depends. Parallel work is useful only when dependencies and
conflicts are handled correctly. The previous statement that speculative or
deferred execution was unstudied is withdrawn.

See the October 6 [research reset](../research/scans/2026-10-06-research-reset.md)
for primary sources and a narrower candidate question about application
readiness and inference scheduling. Literature overlap remains unresolved.

## Conditions to Test

| Schedule | Description |
|----------|-------------|
| Sequential | One tool call at a time, wait for result |
| Parallel (independent) | Call all independent tools simultaneously |
| Speculative | Pre-call likely-needed tools before the plan confirms |
| Lazy | Defer tool calls until the result is referenced |
| Priority-ordered | Call cheapest/fastest tools first, expensive tools last |

## Key Hypotheses

1. Parallel independent calls reduce latency by 30-50% on multi-tool tasks
2. Speculative execution wastes money on wrong guesses but reduces latency
   on predictable workflows
3. Lazy evaluation reduces cost by avoiding unnecessary tool calls
4. Priority ordering optimizes cost when cheaper tools might make expensive
   ones unnecessary

## Connections

- **Planning** — the plan determines which tools are independent (parallelizable)
- **Context allocation** — tool schemas for unused tools waste context
- **Retry** — speculative execution can pre-fetch retry alternatives
