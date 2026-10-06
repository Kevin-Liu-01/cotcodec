# Variable 7: Retry / Recovery Strategy

**Status:** Unexplored. High practical relevance. Paper 3 candidate.

## The Variable

σ = retry ∈ {no_retry, same_approach, diagnose_then_retry, backtrack, escalate, skip_and_continue}

When a tool call fails or produces unexpected results, what does the agent do?

## Why It Matters

Retries are a massive hidden cost in agent systems. tau-bench shows that
retry count is a key differentiator between models. But nobody studies
the retry STRATEGY as an independent variable — most agents just retry
the same thing with slightly different wording.

## Conditions to Test

| Strategy | Description |
|----------|-------------|
| No retry | Accept first result, never retry |
| Same approach | Retry with same tool and approach (up to N times) |
| Diagnose-then-retry | Analyze the error, modify approach, then retry |
| Backtrack | Undo last N steps, try a different path |
| Escalate | Switch to a more capable (expensive) model for the retry |
| Skip-and-continue | Skip the failed step, continue with partial information |

## Key Hypotheses

1. Diagnose-then-retry outperforms same-approach retry on all tasks
2. Backtracking is expensive but catches errors that diagnosis misses
3. Skip-and-continue is underrated — many tasks can succeed with
   partial information from failed tool calls
4. Escalation (model routing on failure) is the highest-ROI strategy
   for cost-optimized pipelines

## Connections

- **Language** — retry diagnoses are a compression target (from Paper 1)
- **Verification** — more verification = earlier failure detection = cheaper retries
- **Planning** — better plans cause fewer retries
