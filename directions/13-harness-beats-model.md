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

## This Is Already Proven — We Need to Systematize It

### Quantified Evidence (2026)

The harness-beats-model hypothesis is not speculative. Multiple independent
results have already demonstrated it:

**SWE-bench: 42% → 78% from scaffolding alone.**
Claude Opus 4.5 scored 42% with one harness and 78% with Claude Code's harness.
A 36-point swing. Swapping between six frontier models produced less than 1.3
points difference. (Source: CORE-Bench / Particula.tech / Victorino Group)

**LangChain Terminal Bench: +13.7 points from harness iteration.**
GPT-5.2-Codex improved from 52.8% to 66.5% through harness changes only.

**Vercel agent: 80% → 100% by reducing tools from 15 to 2.**
Also 3.5x faster and 37% fewer tokens. Context allocation (Variable 4)
was the dominant factor.

**AdaptOrch (arXiv 2602.16873): mathematical proof.**
Under performance convergence (frontier models within 2-5% of each other),
variance from orchestration topology exceeds model selection variance by
Ω(1/ε²). Orchestration IS the bottleneck, not capability.

### The "Model Quality Crisis" of 2026

Every major provider has faced quality degradation complaints — and in
every case, the root cause was orchestration-level, not model-level:

**Anthropic (Claude):**

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

Sonnet 4.6 was independently quantified by a developer who tracked 50
sessions over 60 days: WTF frequency went from ~25 errors/week at baseline
to ~480 errors/week at peak — a 19x increase. 1,400+ frustration events total.
Root cause: the same three harness bugs from the Opus postmortem also
affected Sonnet. (Source: GitHub issue #46935, anthropics/claude-code)

**OpenAI (GPT-5):**
- GPT-5 "frequently ignores explicit instructions, produces buggy code,
  and fails to understand context from earlier conversations"
- Hallucination rate increased from 12% (early 2024) to 23% (late 2025)
- Average code response length dropped from 187 lines to 62 lines
- "Lazy" outputs: uses "etc." or "and so on" instead of completing requests
- Root cause: cost optimization (token economics), aggressive quantization
  (INT4, 10-15% quality loss during peak demand), RLHF over-correction
  toward caution. ALL are orchestration/deployment variables, not model
  capability. (Source: chatgptdisaster.com, atomwriter.com, multiple reports)

**Google (Gemini 3.1 Pro):**
- Higher rates of ignoring formatting instructions vs. 3.0
- At 500K+ tokens, more "attention drift" than 3.0 at equivalent lengths
- Lost "emotional depth, empathy, creative flexibility, and nuance"
- Operational: 90-99 hour lockouts, phantom quota drain (2x consumption),
  104-second launch latency, MODEL_CAPACITY_EXHAUSTED errors
- Root cause: deployment infrastructure and capacity management, not model
  architecture. (Source: TokenCalculator.com, Awesome Agents, Yahoo Tech)

**DeepSeek (V4):**
- Multi-turn dialogue degradation: "reasoning output suffix constraints"
  cause repetitive responses and stagnation
- Model becomes "robotic" with fixed patterns after multiple turns
- Self-reinforcing loop: performance worsens as patterns accumulate
- Root cause: reasoning output format constraints — literally Variable 2
  (reasoning format). (Source: GitHub issue #1125, deepseek-ai/DeepSeek-V3)

**Cursor (Composer 2):**
- Launched March 19, 2026 as "in-house" model with impressive benchmarks
- Within 24 hours, developer found model ID `kimi-k2p5-rl-0317-s515-fast`
  revealing it was Moonshot AI's Kimi K2.5 with RL fine-tuning
- Cursor valued at $29.3B, $167M monthly revenue, failed to disclose
  base model or provide required attribution under modified MIT license
- Rapid "authorized commercial partnership" announced after exposure
- Demonstrates: the HARNESS (Cursor's scaffolding) was the real product,
  not the model. They proved our thesis by shipping someone else's model
  under their own orchestration. (Source: Medium, OpenSourcePress, Implicator)

### The Key Insight

The 2026 "model quality crisis" is actually an ORCHESTRATION quality crisis.
In every case — Anthropic, OpenAI, Google, DeepSeek, Cursor — the complaints
trace to orchestration-level decisions: reasoning effort, context management,
token economics, deployment infrastructure, or output formatting.

This validates our entire research program. If harness changes can make a
frontier model feel like last-generation, harness changes can also make
last-generation perform like frontier.

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

- **AdaptOrch** (arXiv 2602.16873) — Formal proof: under performance convergence,
  orchestration variance exceeds model selection variance by Ω(1/ε²)
- **CORE-Bench / SWE-bench** — 42% → 78% from scaffolding alone (Particula.tech)
- **"The Agent Harness Is the Architecture"** — Evangelos Pappas, Feb 2026
- **Anthropic postmortem** (April 23, 2026) — 3 harness bugs degraded Opus + Sonnet
- **GPT-5 degradation reports** — hallucination 12% → 23%, code length 187 → 62 lines
- **Gemini 3.1 Pro regression** — formatting, context drift, capacity management
- **DeepSeek V4 multi-turn bug** — reasoning suffix constraints cause stagnation
- **Cursor/Kimi K2.5** — proved harness IS the product (shipped someone else's model)
- **Cuadron et al. 2025** — Overthinking in agentic tasks
- **Kiela et al. 2026** (ICLR) — Statistical degradation detection via McNemar's test
- **Quantifying Laziness** (arXiv 2512.20662) — Measured lazy outputs across frontier models
- **Yen et al. 2024** — tau-bench (model vs. harness effects on tool correctness)
