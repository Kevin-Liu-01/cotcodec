# Variable 10: Tool Scheduling

**Status:** Unexplored. Connects to LLMCompiler. Paper 4 candidate.

## The Variable

σ = scheduling ∈ {sequential, parallel_independent, speculative, lazy, priority_ordered}

In what order and with what parallelism should tool calls execute?

## Why It Matters

LLMCompiler (Kim et al. 2023) showed that parallel function calling is a
real optimization for latency. But most agent systems still call tools
sequentially, even when calls are independent. And nobody has studied
speculative execution (call tools before knowing you need them) or lazy
evaluation (defer tool calls until their results are actually needed).

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
