# CoTCodec

**Orchestration Variables for Tool-Using LLM Agents**

Kevin Liu — Princeton University / Dedalus Labs — 2026

Advisor: Professor Danqi Chen (Princeton NLP Group)

## What

Agent systems make dozens of orchestration choices at every step — what language
to reason in, how much to plan, what to remember, when to retry, how to compress
context — and every one of these choices is currently implicit. Hard-coded into
the framework, never measured, never optimized. CoTCodec makes them explicit,
measurable, and optimizable.

The first study (Paper 1) treats **internal language choice** as a controllable
orchestration variable. The broader program covers 12 variables spanning the
full agent loop: reasoning format, memory policy, context allocation, observation
granularity, planning depth, retry strategy, verification cadence, compaction
policy, tool scheduling, delegation topology, and instruction hierarchy.

All share the same formal structure:

```
π(m_t, x_t) → σ_t ∈ {option_1, ..., option_k}
max_π U(π) = Success − λ_c·Cost − λ_t·Latency − λ_s·SafetyRisk
```

## Quick Start

```bash
pip install -e ".[dev]"

# Run a pilot experiment
python -m harness.runner experiments/pilot_01_tau_bench.yaml

# Measure tokenizer fertility
python scripts/fertility.py --model gpt-5.5

# Analyze traces
python scripts/analyze.py data/traces/

# Run frontier research scan
# (uses automations/frontier-research.md protocol)
```

## Structure

```
directions/       # 12 orchestration variables — the research program
harness/          # Evaluation framework (variable-agnostic)
  conditions/     # Orchestration condition implementations
  benchmarks/     # Benchmark adapters (tau-bench, API-Bank, WebArena)
  metrics/        # Collection, analysis, fertility, safety
  routing/        # Dynamic routing policy
experiments/      # YAML experiment definitions
data/             # Collected traces and results (gitignored)
research/         # Frontier research tracking and intelligence
automations/      # Recurring research tasks
skills/           # Research-specific agent skills
wiki/             # Research knowledge base
```

## Key Files

- `memory.json` — Project state, 12 orchestration variables, exploration strategies
- `AGENTS.md` — Master operating guide for AI agents
- `directions/README.md` — Full orchestration variable taxonomy
- `research/frontier-research-spec.md` — How we track frontier research
- `wiki/log.md` — Chronological research log

## Paper 1: Language

Internal language routing for agent intermediate messages. 7 conditions
(English, Chinese, controlled Chinese, compressed English, structured English,
dynamic router, Polish stress), evaluated on tau-bench and API-Bank.

See `directions/01-language.md` and the
[research proposal](../my-wiki/wiki/research/cotcodec-paper.md) in the personal wiki.

## Beyond Language

See `directions/` for 11 additional orchestration variables, each with
hypotheses, conditions to test, connections to other variables, and relevant
prior work. The harness generalizes to test any of them.
