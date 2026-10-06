# Variable 9: Compaction Policy

**Status:** Unexplored. Directly maps to Kevin's experience with autoCompact in Claude Code. Paper 3-4 candidate.

## The Variable

σ = compaction ∈ {never, at_threshold, at_logical_breakpoints, continuous_rolling, importance_weighted, strategic}

When and how should the agent compress its entire context?

## Why It Matters

From ECC research: Claude Code's autoCompact triggers at ~167K tokens,
keeps 5 files capped at 5K tokens each, compresses everything else into
a 50K-token summary. This is a policy decision that nobody has studied
as a variable.

Kevin's insight from the ECC wiki page: compact at logical breakpoints
(after research, after a milestone) instead of waiting for 95% threshold.
This is a testable hypothesis.

## Conditions to Test

| Policy | Description |
|--------|-------------|
| Never | No compaction (crash at context limit) |
| At threshold | Compact when context hits X% full (50%, 70%, 95%) |
| At logical breakpoints | Compact after completing a subtask |
| Continuous rolling | Compress the oldest N messages at every step |
| Importance-weighted | Score each message, compress lowest-importance first |
| Strategic | ECC pattern — compact at 50%, keep critical files, summarize rest |

## Key Hypotheses

1. Logical-breakpoint compaction outperforms threshold compaction because
   it preserves coherent reasoning chains
2. The optimal threshold depends on task complexity — simple tasks survive
   aggressive compaction, complex tasks need more context
3. Importance-weighted compaction requires a good importance model, which
   is itself a research problem

## Connections

- **Memory** — compaction is global memory management; memory policy is per-step
- **Language** — shorter language = compaction happens later = more context
- **Context allocation** — compaction frees budget, allocation decides how to spend it

## Community Evidence (from Kevin's X bookmarks)

- **Claude Code autoCompact reverse-engineering** (16.5K bm @iamfakeguru) — autoCompact
  triggers at ~167K tokens. Keeps 5 files capped at 5K tokens each, compresses everything
  else into 50K-token summary. This is THE concrete data point for compaction policy.
- **ECC strategic compaction** (wiki/tools/everything-claude-code.md) — "Compact at logical
  breakpoints instead of waiting for 95% auto-compact." CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=50.
  Testable hypothesis: earlier compaction at 50% vs. default 95%.
- **Caveman compression** (@om_patel5) — compaction via reasoning format change rather than
  algorithmic compression. 65% savings. Different mechanism, same goal.
