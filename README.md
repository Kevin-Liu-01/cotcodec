# CoTCodec

**Language Choice as an Orchestration Variable for Tool-Using LLM Agents**

Kevin Liu — Princeton University / Dedalus Labs — 2026

Advisor: Professor Danqi Chen (Princeton NLP Group)

## What

An empirical study of whether internal language routing can improve the
cost-latency-success frontier of realistic agent trajectories. The intervention
is narrow: only framework-visible intermediate messages (planner notes, memory
summaries, retry diagnoses) vary in language. Tool schemas and user responses
stay English.

## Quick Start

```bash
# Install dependencies
pip install -e ".[dev]"

# Run a pilot experiment
python -m harness.runner experiments/pilot_01_tau_bench.yaml

# Measure tokenizer fertility
python scripts/fertility.py --model gpt-4o

# Analyze traces
python scripts/analyze.py data/traces/
```

## Structure

```
harness/          # Evaluation framework
  conditions/     # 7 language conditions (English, Chinese, compressed, structured, router, Polish)
  benchmarks/     # Benchmark adapters (tau-bench, API-Bank, WebArena)
  metrics/        # Collection, analysis, fertility, safety
  routing/        # Dynamic routing policy
experiments/      # YAML experiment definitions
data/             # Collected traces and results (gitignored)
automations/      # Recurring research tasks
skills/           # Agent skills for this project
wiki/             # Research knowledge base
```

## Key Files

- `memory.json` — Project state, direction, and exploration strategies
- `AGENTS.md` — Master operating guide for AI agents
- `wiki/log.md` — Chronological research log

## Related

- [Research proposal](../my-wiki/wiki/research/cotcodec-paper.md) (in personal wiki)
- [LaTeX source](../my-wiki/raw/research/language-orchestration-research-spec.tex)
