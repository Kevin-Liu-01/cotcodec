---
name: analyze-traces
version: 0.1.0
triggers: ["analyze traces", "compare conditions", "pareto", "decomposition", "results"]
tools: [shell, read]
mutating: false
---

# Analyze Traces

Analyze collected experiment traces and produce comparison reports.

## Contract

Given a trace directory or experiment ID, this skill:
1. Loads all traces from the specified source
2. Produces cross-condition comparison table
3. Computes message-type decomposition (where savings arise)
4. Identifies Pareto-optimal conditions
5. Generates safety evaluation summary
6. Outputs structured analysis

## Steps

1. Load traces: `python -c "from harness.metrics.analyzer import load_traces; ..."`
2. Cross-condition comparison: aggregate by condition, show success/tokens/latency
3. Message-type decomposition: which message types save the most tokens?
4. Pareto frontier: which conditions are on the frontier?
5. Safety check: any conditions flagged?

## Key Questions to Answer

- Does internal Chinese reduce total tokens after fixed tool overhead?
- Where do savings come from? (planning, memory, retries, handoffs)
- Does structured English match or beat Chinese?
- Is the dynamic router better than any single condition?
- Any safety regressions?

## Output Format

Tables comparing conditions, decomposition by message type,
Pareto frontier coordinates, and safety summary.
