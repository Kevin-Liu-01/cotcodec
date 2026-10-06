# Variable 8: Verification Cadence

**Status (2026-10-06):** Pre-admission. Verification and evidence freshness have
direct recent prior work; this is not an unexplored area. A computer-work
extension needs a distinct mechanism and matched controls.

## The Variable

σ = verification ∈ {never, every_step, every_n_steps, after_tool_calls, on_uncertainty, at_checkpoints}

When should the agent check whether its intermediate state is correct?

## Why It Matters

An agent can act on an old observation or mistake an unfinished UI update for
a failed action. Checking more often costs time and compute, so verification
must be evaluated against complete task outcomes. The historical community
claims below do not establish a causal false-claims rate or provider behavior.

The October 6 [research reset](../research/scans/2026-10-06-research-reset.md)
reviews AAS, Desktop-Delta, cua-speedrun and State Footprints. Generic freshness
checks or agent transactions cannot be claimed as new. No experiment is admitted.

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

## Community Evidence (from Kevin's X bookmarks — 16 signals)

- **KingBootoshi custom ESLint anti-slop** (1.1K bm) — "PUT YOUR AGENTS ON CUSTOM ESLINT
  RULES ASAP. IT IS THE BEST WAY TO GUARANTEE ANTI-SLOP." Lint rules as verification
  infrastructure — structural, not advisory. Agent retries automatically on lint failure.
- **Karpathy AutoResearch** (10.4K bm via @shannholmberg) — verification loop in research
  agent: search → evaluate → validate → iterate. Continuous verification cadence.
- **Design system reverse-engineering** (18.6K bm @heynavtoor) — "Someone reverse-engineered
  the design systems of Apple, Spotify, Airbnb, and 30+ companies." Verification by
  comparison against known-good reference implementations.
- **NickSpisak monthly health checks** (9.3K bm) — scheduled verification cadence for
  knowledge base quality. Weekly lint, monthly full audit.
- **GStack Confusion Protocol** (834 bm @garrytan) — "Karpathy called it: the #1 AI coding
  failure mode is the agent confidently picking the wrong path at an ambiguous decision point."
  Verification BEFORE action, not after.
- **Claude Code 29-30% false claims** (16.5K bm @iamfakeguru) — "Post-edit verification gate
  (type-check + lint after every edit) is gated behind USER_TYPE === 'ant'." Evidence that
  verification cadence directly affects reliability. Internal Anthropic has it; external doesn't.
