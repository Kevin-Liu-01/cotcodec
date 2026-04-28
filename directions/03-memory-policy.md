# Variable 3: Memory Policy

**Status:** Unexplored. Natural Paper 2-3 candidate. Strong connection to Kevin's production experience at Dedalus.

## The Variable

σ = memory_policy ∈ {keep_all, sliding_window, importance_weighted, type_aware_eviction, hierarchical_compression, semantic_dedup}

## Intervention

Control what the agent remembers across steps. Most agents either keep
everything (until context fills) or use crude truncation. The variable is
how to manage working memory.

## Why It Matters

Context erosion is the central systems problem for long-horizon agents.
Liu et al. show lost-in-the-middle effects. MemGPT attempts explicit
memory management. But no one has systematically studied memory policy
as a measurable orchestration variable with agent benchmarks.

From Kevin's production experience at Dedalus: MCP tool-using agents in
the real world hit context limits. The question is always "what do we keep?"

## Conditions to Test

| Policy | Description |
|--------|-------------|
| Keep-all | Retain everything until context limit (baseline) |
| Sliding window | Keep last N messages, drop oldest |
| Importance-weighted | Score messages by relevance, evict lowest |
| Type-aware eviction | Keep tool schemas + latest plan, evict old observations |
| Hierarchical compression | Compress old messages into summaries, keep recent verbatim |
| Semantic dedup | Merge messages that say the same thing differently |

## Key Hypotheses

1. Type-aware eviction (keep plans, drop old observations) outperforms
   keep-all on long trajectories
2. Hierarchical compression preserves more useful state than sliding window
3. The optimal policy depends on trajectory length — short tasks don't
   benefit, long tasks benefit enormously
4. Memory policy interacts with language: Chinese memories are shorter,
   so keep-all works longer before hitting context limits

## Measurement

- Same Pareto framework: cost-latency vs. success-safety
- New metric: **information retention score** — does the agent remember
  facts from step 2 when they're needed at step 10?
- Lost-in-the-middle probe: inject critical info at various positions

## Connections

- **Language** — shorter language = more memory budget. These interact.
- **Context allocation** — memory policy is one piece of context allocation.
- **Compaction** — related but distinct. Compaction is about when to compress
  the full context. Memory policy is about what to keep at each step.

## Prior Work

- Packer et al. 2023 — MemGPT
- Maharana et al. 2024 — Long-term conversational memory
- Wu et al. 2024 — LongMemEval
- Liu et al. 2024 — Lost in the Middle
