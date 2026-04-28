# Orchestration Variables — Research Directions

Language is Paper 1. The broader research program is about the full space
of orchestration variables for tool-using agents.

## The Frame

Most agent systems make orchestration choices **implicitly** — they're
hard-coded into the framework, never measured, never optimized. The research
contribution is making them **explicit, measurable, and optimizable.**

Every agent system has a loop:

```
Goal → Reason → Act → Observe → Update → (repeat)
```

At every step, the system makes choices that are currently invisible:

| Choice point | What most systems do | What we study |
|-------------|---------------------|---------------|
| What language to reason in | English (default) | Language routing policy |
| How much to plan ahead | Whatever the prompt says | Planning depth as a variable |
| What to remember | Everything until context fills | Memory policy as a variable |
| How to handle errors | Retry the same way | Recovery strategy as a variable |
| When to verify | Never (or always) | Verification cadence as a variable |
| How to compress context | Truncate from the front | Compaction policy as a variable |
| How much tool output to keep | All of it | Observation granularity as a variable |
| When to delegate | Never (single agent) | Delegation topology as a variable |
| How to order tool calls | Sequential | Tool scheduling as a variable |

Each of these is an **orchestration variable** — a degree of freedom that
affects cost, latency, success, and safety. The harness framework generalizes
to test any of them.

## The Generalized Optimization

For any orchestration variable σ:

```
π(m_t, x_t) → σ_t ∈ {option_1, option_2, ..., option_k}

max_π U(π) = Success − λ_c·Cost − λ_t·Latency − λ_s·SafetyRisk
```

Language routing is σ = ℓ ∈ {English, Chinese, Structured, Compressed}.
But σ can be anything: memory retention level, planning depth, retry budget,
delegation granularity.

## Variable Taxonomy

See individual files in this directory for each variable:

| Variable | File | Tractability | Paper # |
|----------|------|-------------|---------|
| Language | `01-language.md` | High (Paper 1) | 1 |
| Reasoning format | `02-reasoning-format.md` | High | 1-2 |
| Memory policy | `03-memory-policy.md` | Medium | 2 |
| Context allocation | `04-context-allocation.md` | Medium | 2 |
| Observation granularity | `05-observation-granularity.md` | Medium | 2-3 |
| Planning depth | `06-planning-depth.md` | Medium | 3 |
| Retry / recovery | `07-retry-recovery.md` | Medium | 3 |
| Verification cadence | `08-verification-cadence.md` | Medium | 3 |
| Compaction policy | `09-compaction-policy.md` | Medium-Low | 3-4 |
| Tool scheduling | `10-tool-scheduling.md` | Medium-Low | 4 |
| Delegation topology | `11-delegation-topology.md` | Low | 4+ |
| Instruction hierarchy | `12-instruction-hierarchy.md` | Low | 4+ |

## Why Language First

Language is the most tractable first variable because:

1. **Easy to manipulate** — system prompt addendum, no framework changes
2. **Easy to measure** — token counts are exact, not approximate
3. **Clear prior work** — DeepSeek-R1, EfficientXLang, Li et al.
4. **Natural decomposition** — by message type (planning, memory, retry)
5. **Clean baselines** — prompt compression, structured reasoning

But the harness, metrics, routing policy, and analysis pipeline all generalize.
