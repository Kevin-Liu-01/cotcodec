# Variable 13: Harness Beats Model

**Status:** New research direction. The most provocative hypothesis in the project.

## The Hypothesis

**A 2024 model with optimized orchestration can outperform a 2026 frontier
model with naive orchestration on agent benchmarks.**

Claude Sonnet 3.5 (2024) + optimized language routing, structured reasoning,
intelligent memory management, and verification gates can beat Claude Opus 4.7
(2026) running with default settings on real agent tasks.

If true, this is a headline result: **orchestration variables matter more
than model generation for agent performance.**

## Why This Is Credible

### The Anthropic Postmortem (April 23, 2026)

Anthropic traced "Claude getting dumber" reports to three harness-level
changes — not model changes. All three are orchestration variables:

**1. Reasoning effort: high → medium (Variable 2: Reasoning Format)**
On March 4, Claude Code's default reasoning effort was changed from `high`
to `medium` to reduce latency. Users immediately reported Claude felt less
intelligent. Reverted April 7.

- This is literally Variable 2 in our taxonomy
- Effort level controls how long the model thinks — a reasoning format knob
- The "wrong tradeoff" was a harness decision, not a model limitation

**2. Thinking cache bug (Variable 9: Compaction Policy)**
On March 26, a caching optimization meant to clear old thinking from stale
sessions had a bug: instead of clearing once, it cleared every turn for the
rest of the session. Claude lost memory of why it chose its approach.

- This is Variable 9 (compaction) and Variable 3 (memory policy) combined
- A single harness bug made Opus 4.6 "forgetful and repetitive"
- Cache misses also drained usage limits faster (cost impact)

**3. Verbosity limit in system prompt (Variable 4: Context Allocation)**
On April 16, Anthropic added "keep text between tool calls to ≤25 words"
to the system prompt. After weeks of internal testing, they shipped it.
It caused a 3% quality drop on both Opus 4.6 and 4.7.

- This is Variable 4 (context allocation) — restricting output budget
- A single system prompt line degraded TWO model generations
- Internal evals didn't catch it; broader evals did

### The Key Insight

All three degradations were orchestration-level changes that made a
frontier model perform worse than its predecessor. If harness changes
can make a new model feel like an old one, harness changes can also
make an old model perform like a new one.

## Experimental Design

### Phase 1: Establish Baselines

Run each model with naive English-only orchestration (no routing, no
compression, default everything):

| Model | Tier | Expected tau-bench | Cost per task |
|-------|------|-------------------|---------------|
| Claude Sonnet 3.5 | Baseline old | ~70% | Low |
| GPT-4o | Baseline old | ~65% | Low |
| Claude Sonnet 4.6 | Strong | ~78% | Medium |
| Claude Opus 4.7 | Frontier | ~85% | High |
| GPT-5.5 | Frontier | ~87% | High |

### Phase 2: Orchestrate the Old Models

Run baseline old models with all 7 orchestration conditions + the
dynamic router, plus reasoning format, memory policy, and verification:

| Model | Orchestration | Expected outcome |
|-------|---------------|------------------|
| Sonnet 3.5 + dynamic router | Language + structured reasoning + verification | Success ↑, cost ↓ |
| Sonnet 3.5 + full orchestration | All variables optimized | Maximum uplift |
| GPT-4o + dynamic router | Same | Cross-provider validation |

### Phase 3: Compare Pareto Frontiers

Plot both on the same cost-success Pareto chart:
- X-axis: cost per task (tokens * price)
- Y-axis: task success rate
- Each point is a (model, orchestration) pair

**The kill result:** Old model + orchestration sits on or above the Pareto
frontier defined by new models + naive orchestration. The orchestration
contribution exceeds the model generation contribution.

## What Each Outcome Means

| Outcome | Implication | Paper framing |
|---------|-------------|---------------|
| Old + orchestration > New + naive | Orchestration matters more than model generation | "Orchestration is the bottleneck, not capability" |
| Old + orchestration ≈ New + naive | Orchestration closes the generational gap | "Orchestration as a model-generation multiplier" |
| Old + orchestration < New + naive | Model generation dominates | "Orchestration helps but can't substitute for capability" |
| Old + orchestration > New + orchestration | Would be extraordinary — harness amplifies old models more | "Diminishing returns on model capability" |

All four outcomes are publishable. The first two are the most interesting.

## Connections

This direction subsumes all 12 orchestration variables because it tests
their combined effect against raw model capability. It's the meta-experiment
that justifies the entire research program.

- **Language** — most direct test (Paper 1 conditions)
- **Reasoning format** — Anthropic postmortem showed effort level matters enormously
- **Compaction** — postmortem showed a compaction bug alone caused major degradation
- **Verification** — postmortem showed internal verification gates catch 29% false claims

## Prior Work

- Anthropic, "An update on recent Claude Code quality reports" (April 23, 2026)
- Cuadron et al. 2025 — Overthinking in agentic tasks (harness-level effect)
- ECC token optimization benchmarks — 65% savings via reasoning format alone
- Yen et al. 2024 — tau-bench (model vs. harness effects on tool correctness)
