# Variable 8: Verification Cadence

**Status:** Unexplored. Directly relevant to Kevin's harness work (hooks, quality gates). Paper 3 candidate.

## The Variable

σ = verification ∈ {never, every_step, every_n_steps, after_tool_calls, on_uncertainty, at_checkpoints}

When should the agent check whether its intermediate state is correct?

## Why It Matters

From Kevin's Claude Code harness: the post-edit verification gate (type-check
+ lint after every edit) is gated behind internal Anthropic builds. External
users get no verification. This creates a 29-30% false-claims rate.

The same principle applies to agents generally. If the agent never checks
intermediate results, errors compound. If it checks everything, it wastes
tokens on verification of correct steps.

## Conditions to Test

| Cadence | Description |
|---------|-------------|
| Never | No intermediate verification (baseline) |
| Every step | Verify after every action |
| Every N steps | Verify periodically |
| After tool calls | Verify only after tool call results |
| On uncertainty | Verify when model confidence is low (logprobs) |
| At checkpoints | Verify at pre-defined milestones |

## Key Hypotheses

1. After-tool-call verification has the best cost-benefit ratio
2. Every-step verification wastes tokens on simple, reliable steps
3. On-uncertainty requires logprob access (not all APIs provide this)
4. Checkpoint verification works well for structured tasks with clear milestones

## Connections

- **Retry** — verification detects failures early, enabling cheaper retries
- **Reasoning format** — structured formats are easier to verify automatically
- **Planning** — verification can trigger re-planning if the plan is off track
