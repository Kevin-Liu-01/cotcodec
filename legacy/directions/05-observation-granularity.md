# Variable 5: Observation Granularity

**Status:** Unexplored. High practical impact. Paper 2-3 candidate.

## The Variable

σ = observation ∈ {full_output, truncated, summarized, schema_only, diff_from_expected, error_only}

How much of a tool's output should the agent see before deciding what to do next?

## Why It Matters

Tool outputs are often the largest single token consumer in agent traces.
A web search returns pages of text. A file read returns entire files.
A database query returns full result sets. Most agents include ALL of this
in their context, even when they only need one number from the result.

This is the ECC "tool result truncation" problem made explicit as a variable.

## Conditions to Test

| Granularity | What the agent sees |
|-------------|-------------------|
| Full output | Everything the tool returned (baseline) |
| Truncated | First N tokens of output |
| Summarized | LLM-generated summary of tool output |
| Schema-only | Just the structure/shape of the output |
| Diff-from-expected | Only what differs from what the agent predicted |
| Error-only | Only error messages and exceptions; success = "ok" |

## Key Hypotheses

1. Summarized observation dramatically reduces tokens on information-retrieval
   tools (web search, file read) without hurting success
2. Error-only observation works for well-understood tools where the agent
   already knows what success looks like
3. Full output is still necessary for tools with unpredictable output
   (code execution, database queries with unknown schema)
4. The optimal granularity is tool-specific, not global

## Connections

- **Context allocation** — observation granularity directly controls one
  of the largest budget components
- **Memory** — summarized observations are easier to retain in memory
- **Verification** — seeing less output means more trust in the tool.
  Verification cadence should increase when observations are reduced.
