# Variable 15: Interpretable Abstract Reasoning

**Status:** NARROWED on 2026-09-01 — every axis occupied at ≤8B on math/QA; surviving deltas are tool-use × monitorability, translation-equivariant codes, and a controlled Abstract-CoT replication
and the intersection with CoTCodec's orchestration variable framework.

## The Core Tension

Abstract-CoT achieves 11.6x compression but the tokens are opaque — no human
can read `<E> <C> <AE> <F> <A> <BB> <D>` and understand what the model is
thinking. This creates a fundamental tension:

**Efficiency vs. monitorability.**

Two critical safety papers establish why this matters:

1. **Baker et al. (OpenAI, arXiv 2503.11926):** "Monitoring Reasoning Models
   for Misbehavior." CoT monitoring catches reward hacking in frontier agents
   that output-only monitoring misses. GPT-4o can monitor o3-mini's CoT for
   misbehavior — a weaker model supervising a stronger one. But when CoT
   monitoring is incorporated into the RL reward, agents learn "obfuscated
   reward hacking" — hiding intent while still misbehaving.

2. **METR (2025):** "CoT May Be Highly Informative Despite Unfaithfulness."
   Even unfaithful CoTs achieve 99.3% true positive rate for detecting
   whether models used specific reasoning clues. CoT is informative enough
   for safety monitoring even when it doesn't perfectly narrate reasoning.

**The implication for Abstract-CoT:** If abstract tokens are opaque, CoT
monitoring becomes impossible. If models can't be monitored through their
reasoning, misbehavior detection loses its most effective signal channel.

## Research Directions

### Direction A: Structured Abstract Tokens (Kevin's intuition)

**What if abstract tokens had deterministic, interpretable meaning?**

Instead of purely learned embeddings with no semantic constraints, introduce
structure into the abstract codebook:

| Approach | Description | Tradeoff |
|----------|-------------|----------|
| **Typed tokens** | Reserve token subsets for specific functions: `<PLAN_*>` for planning, `<TOOL_*>` for tool reasoning, `<MEM_*>` for memory | Lose some compression, gain type-level interpretability |
| **Vectorized tokens** | Each token maps to a known position in a semantic embedding space (not random init) | Warm-up is guided, not cold-start |
| **Grounded tokens** | Tokens are constrained to correspond to discrete operations (like opcodes) | Most interpretable, least flexible |
| **Hierarchical tokens** | Two levels: abstract "category" tokens that are interpretable + abstract "detail" tokens that aren't | Partial interpretability |
| **Probe-interpretable** | Train a separate probe to decode abstract token meanings post-hoc | No compression cost, but interpretation is approximate |

### Direction B: Hybrid CoT — Abstract + Verbal Checkpoints

**What if the model reasons abstractly but checkpoints verbally?**

```
<beginabstract> <E> <C> <AE> <F> <endabstract>
<checkpoint> Plan: check order history, verify refund window </checkpoint>
<beginabstract> <A> <BB> <D> <G> <endabstract>
<checkpoint> Decision: eligible, processing refund </checkpoint>
Answer: ...
```

This gives:
- Abstract tokens for efficiency (compress the reasoning)
- Verbal checkpoints for monitorability (expose the decisions)
- A tunable ratio: more checkpoints = more monitorable, less efficient
- The checkpoint frequency IS an orchestration variable

This directly maps to our Variable 8 (Verification cadence) — the
checkpoints are verification points where reasoning becomes legible.

### Direction C: The Monitorability Tax

Baker et al. introduce the concept of a **"monitorability tax"** — the
cost of keeping CoT readable enough to monitor. We can formalize this:

```
U(π) = Success − λ_c·Cost − λ_t·Latency − λ_s·SafetyRisk − λ_m·MonitorabilityCost
```

A new term in our optimization function. The monitorability cost is the
efficiency you give up to keep reasoning interpretable. Our research can
measure this tradeoff precisely across the reasoning format spectrum:

| Format | Compression | Monitorability | MonitorabilityCost |
|--------|------------|----------------|-------------------|
| Verbose English CoT | 1x | Full (human-readable) | 0 (baseline) |
| Compressed English | 1.5-3x | High (still readable) | Low |
| Structured protocol | 2-4x | High (parseable) | Low |
| Non-English (Chinese) | 1.2-1.4x | Medium (translator needed) | Medium |
| Hybrid (abstract + checkpoints) | 3-6x (estimated) | Medium (checkpoints readable) | Medium |
| Abstract CoT | 4-12x | None (opaque) | Undefined (monitoring breaks) |

**The research question:** What is the Pareto frontier of efficiency vs.
monitorability? Is there a sweet spot where you get 5x compression and
retain 90% of monitoring effectiveness?

### Direction D: Abstract Tokens for Agent Tool Use (our unique gap)

Abstract-CoT has NOT been tested on agent/tool-use tasks. The paper tests
reasoning (MATH-500, GPQA) and instruction following (AlpacaEval). But
agent tasks require:

1. **Tool argument precision** — the model must emit exact JSON arguments.
   Do abstract reasoning tokens preserve this precision?
2. **Multi-step state tracking** — the model must remember tool outputs
   across steps. Do abstract tokens maintain state as well as verbal reasoning?
3. **Error diagnosis** — when a tool call fails, the model must diagnose why.
   Can it diagnose effectively through abstract tokens?
4. **Schema fidelity** — tool schemas are in English. Does abstract internal
   reasoning preserve the mapping to English schemas?

This is where CoTCodec can make a unique contribution: be the first to
test abstract reasoning on agent benchmarks (tau-bench, MCP-Atlas, Toolathlon).

### Direction E: Abstract Tokens as a Learned Orchestration Language

The power-law distribution over abstract tokens (Zipf's law emerges via RL)
suggests the model learns a genuine internal language. This connects to the
original CoTCodec thesis:

- DeepSeek-R1 mixed English and Chinese in its CoT
- EfficientXLang showed cross-lingual reasoning is shorter and sometimes better
- Abstract-CoT shows the optimal "language" for reasoning may not be human at all

**The spectrum of reasoning media:**

```
Human language (English) → Human language (Chinese) → Structured protocol
  → Compressed notation → Abstract discrete tokens → Continuous latent vectors
```

CoTCodec started at the left (language choice). Abstract-CoT operates further
right. The full research program spans the entire spectrum. Our contribution
is measuring where on this spectrum different agent task types should sit.

## Connections

- **Variable 1 (Language):** Abstract-CoT is the logical endpoint of the
  language routing thesis — the most efficient "language" is a learned one
- **Variable 2 (Reasoning format):** Abstract tokens are the most extreme
  format change
- **Variable 8 (Verification cadence):** Hybrid CoT checkpoints = verification
  points in abstract reasoning
- **Variable 12 (Instruction hierarchy):** Opaque reasoning may make
  instruction hierarchy harder to enforce and monitor
- **Variable 13 (Harness beats model):** Abstract-CoT is pure post-training.
  Same model, different format, massively different efficiency.
- **Variable 14 (Degradation detection):** How do you detect quality
  regression in opaque abstract reasoning?

## Sources (all verified)

| Source | URL |
|--------|-----|
| Abstract Chain-of-Thought | https://arxiv.org/abs/2604.22709 |
| Monitoring Reasoning Models (OpenAI) | https://arxiv.org/abs/2503.11926 |
| CoT May Be Highly Informative (METR) | https://metr.org/blog/2025-08-08-cot-may-be-highly-informative-despite-unfaithfulness/ |
| METR CoT faithfulness code | https://github.com/METR/CoT-faithfulness-and-monitorability |
| Coconut (continuous latent reasoning) | https://arxiv.org/abs/2412.06769 |
| KeshavRamji tweet | https://x.com/KeshavRamji/status/2048743883580817620 |

## 2026-09-01 kill-shot update

Verdict from the 2026-09-01 frontier sweep: **NARROWED**. Abstract-CoT has no
official code and three failed or stalled third-party reproductions; the
"verbal checkpoint" hybrid exists in stronger form (SELR, ICML 2026);
DiffusionGemma's interpretable token bottleneck reduces opaque serial depth
28.6× → 1.1× ([2606.20560](https://arxiv.org/abs/2606.20560)); monitorability is
filling fast (FACE-Eval [2608.29464](https://arxiv.org/abs/2608.29464), HCDS
[2608.29956](https://arxiv.org/abs/2608.29956), Intent-as-a-Tool
[2608.27348](https://arxiv.org/abs/2608.27348)); looped LMs cover single-turn
compositional tool calling ([2608.18171](https://arxiv.org/abs/2608.18171)).

Surviving deltas: (a) monitorability of latent/abstract media on tool-use agent
tasks with one fixed monitor across media at matched accuracy, under
reasoning-rewrite and monitor-awareness attacks; (b) translation-equivariant
abstract reasoning codes with a monitor trained in one language and tested in
others (the only cross-lingual datapoint is an n=8 case study,
[2608.15392](https://arxiv.org/abs/2608.15392); the audio-LLM multilingual
middle-layer workspace [2608.24958](https://arxiv.org/abs/2608.24958) is the
existence proof); (c) a controlled Abstract-CoT reproduction with token-necessity
ablations at 4B–8B. Verification note (2026-09-01): ALCA
([2026.acl-long.1570](https://aclanthology.org/2026.acl-long.1570/), ACL 2026)
already moves safety deliberation into a latent space with a restricted
self-decoding mechanism for supervision, so "interpretable-by-construction
latents as a monitor channel" is partly occupied; the surviving clause is its
behaviour on tool-use tasks under obfuscation pressure and across languages.
