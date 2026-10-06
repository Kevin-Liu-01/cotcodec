# Variable 12: Instruction Hierarchy

**Status:** Unexplored. Safety-critical. Connects to Wallace et al. Paper 4+ candidate.

## The Variable

σ = hierarchy ∈ {flat_equal, system_dominant, recency_weighted, source_trust_scored, dynamic_priority}

How should the agent weight conflicting instructions from different sources?

## Why It Matters

Wallace et al. (2024) show that models often fail to distinguish privileged
developer instructions from lower-trust text. In agent settings, the problem
is sharper: system prompts, user messages, tool outputs, and retrieved documents
all contain "instructions" at different trust levels.

This variable is especially relevant to CoTCodec because multilingual
internal communication may make instruction hierarchy harder to maintain —
safety-critical instructions in English could be diluted by surrounding
Chinese reasoning.

## Conditions to Test

| Hierarchy | Description |
|-----------|-------------|
| Flat (equal) | All text treated equally (baseline — most current systems) |
| System-dominant | System prompt overrides everything |
| Recency-weighted | Recent instructions override older ones |
| Source-trust-scored | Each source has a trust score; higher trust wins |
| Dynamic priority | Priority changes based on task phase (planning vs. execution) |

## Key Hypotheses

1. Source-trust-scored hierarchy improves safety without hurting success
2. Flat hierarchy is the root cause of most prompt injection vulnerabilities
3. Dynamic priority is optimal but hard to implement correctly
4. This variable interacts with language — instructions in the reasoning
   language (Chinese) may receive more weight than they should

## Connections

- **Safety** — this is the most safety-relevant orchestration variable
- **Language** — multilingual mixing may blur instruction boundaries
- **Memory** — old system instructions can get "lost in the middle"

## Community Evidence (from Kevin's X bookmarks — 18 signals)

- **Anthropic Project Glasswing** (15.4K bm @AnthropicAI) — "An urgent initiative to help
  secure the world's most critical software." Instruction hierarchy is the foundation.
- **GStack security fixes wave** (117 bm @garrytan) — "Big wave of security fixes for GStack
  and GBrain." Open-source agent harnesses have real security surface area.
- **Claude Managed Agents** (50.7K bm @claudeai) — official agent harness implies a specific
  instruction hierarchy (system → developer → agent → user). Our conditions must test
  whether language mixing degrades this hierarchy.
