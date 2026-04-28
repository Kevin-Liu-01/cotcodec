# CoTCodec — Agent Operating Guide

A research program studying **orchestration variables** for tool-using LLM agents.
Language is Paper 1. The broader program covers the full space of choices that
agent systems make implicitly and never measure. Princeton / Dedalus Labs, Fall 2026.

**Advisor:** Professor Danqi Chen (Princeton NLP Group)
**Author:** Kevin Liu (Princeton CS '28, Dedalus Labs founding engineer)

## The Mental Model

**This is a research project, not a product.** The goal is a rigorous empirical
study with publishable results — positive or negative. Every piece of infrastructure
exists to produce clean, reproducible experiments. The harness is the product.

Read `memory.json` for current project state, direction, and next actions.
Read `wiki/SOUL.md`, `wiki/USER.md`, `wiki/HEARTBEAT.md` on every session start.

## Session Startup

1. Read `wiki/SOUL.md`, `wiki/USER.md`, `wiki/HEARTBEAT.md`
2. Read `memory.json` — check current phase, next actions, landscape changes
3. Report what needs attention before doing anything else

## The Broader Thesis

Agent orchestration is an underexplored design space. Most systems make
orchestration choices **implicitly** — hard-coded into the framework, never
measured, never optimized. Making them **explicit, measurable, and optimizable**
is the research contribution.

Every agent loop makes invisible choices at every step:

| Choice | What most systems do | What we study |
|--------|---------------------|---------------|
| What language to reason in | English (default) | **Language** (Paper 1) |
| How to format reasoning | Free-form prose | **Reasoning format** |
| What to remember | Everything until context fills | **Memory policy** |
| How much context to allocate | Implicitly, whatever fits | **Context allocation** |
| How much tool output to keep | All of it | **Observation granularity** |
| How far ahead to plan | Whatever the prompt says | **Planning depth** |
| What to do when tools fail | Retry the same way | **Retry / recovery** |
| When to verify intermediate state | Never | **Verification cadence** |
| When to compress context | At 95% full | **Compaction policy** |
| How to order tool calls | Sequential | **Tool scheduling** |
| How to distribute work | Single agent | **Delegation topology** |
| How to weight conflicting instructions | Equally | **Instruction hierarchy** |

Each is an **orchestration variable** σ with the same formal structure:

```
π(m_t, x_t) → σ_t ∈ {option_1, ..., option_k}
max_π U(π) = Success − λ_c·Cost − λ_t·Latency − λ_s·SafetyRisk
```

See `directions/README.md` for the full taxonomy and `directions/01-12` for
individual variable exploration docs.

## Paper 1: Language

Language is the most tractable first variable (easy to manipulate, easy to
measure, clear priors from DeepSeek-R1 and EfficientXLang). The intervention
is narrow: only framework-visible intermediate messages vary. Tool schemas
and final responses stay English.

**The best paper is a routing policy, not "always use Chinese."**

## Advisor Context

Danqi confirmed for Fall 2026 with the caveat that the field is moving fast and
settings will need revisiting. This means:

- Infrastructure must be **model-agnostic** (swap models without rewriting harness)
- Benchmarks must be **pluggable** (add new ones as they appear)
- The experimental design must be **revisable** (conditions, metrics configurable)
- Track landscape changes in `memory.json` → `landscape_tracking`
- **Research intelligence is non-negotiable** — see below

## Frontier Research Intelligence

The field moves weekly. Between now and fall, entire research threads will
emerge, models will ship, benchmarks will update. If we're not tracking
this systematically, we show up with a stale proposal.

**Full spec:** `research/frontier-research-spec.md`
**Automation:** `automations/frontier-research.md`
**Skill:** `skills/frontier-research.md`
**Reports:** `research/scans/YYYY-MM-DD.md`

### Source Coverage

| Tier | Sources | Signal | Noise | Cadence |
|------|---------|--------|-------|---------|
| 1 — Labs | Anthropic, OpenAI, DeepSeek, DeepMind, Meta, Qwen, Mistral, xAI, Cohere | Highest | Lowest | Daily-Weekly |
| 2 — Academic | arXiv (cs.CL/AI/MA/SE), ACL Anthology, Semantic Scholar, HF Papers, Princeton/Stanford/CMU/UW NLP | High | Low | Daily-Weekly |
| 3 — Community | X, HN, Reddit (r/ML, r/LocalLLaMA), GitHub Trending, Alignment Forum, Interconnects | Fastest | Highest | Daily-Weekly |

### Research Threads

| Thread | Variables | What to track |
|--------|-----------|---------------|
| A — Agent Internal Communication | 1-2 | Language, reasoning format, structured protocols |
| B — Context Management | 3-5, 9 | Memory, allocation, observation, compaction |
| C — Planning & Recovery | 6-8 | Planning depth, retry, verification |
| D — Coordination & Control | 10-12 | Tool scheduling, delegation, instruction hierarchy |
| E — Benchmarks & Evaluation | All | New benchmarks, leaderboard changes |
| F — Models & Providers | All | New models, API changes, pricing |
| G — Safety & Alignment | All | Multilingual safety, instruction following |

### Competitive Intelligence

Track groups working on adjacent problems — DeepSeek Research, Microsoft
(EfficientXLang), Li et al. (UPenn), Wang et al. (LMU Munich). If someone
publishes on our question, brief Danqi within 24 hours.

## Directory Structure

```
cotcodec/
├── AGENTS.md              # This file — master operating guide
├── CLAUDE.md              # Points here
├── .cursorrules           # Points here
├── memory.json            # Project state, direction, exploration strategies
├── directions/            # Research directions beyond language
│   ├── README.md          # Full orchestration variable taxonomy
│   ├── 01-language.md     # Paper 1 (active)
│   ├── 02-reasoning-format.md  # Paper 1-2 candidate
│   ├── 03-memory-policy.md     # Paper 2 candidate
│   ├── 04-context-allocation.md  # Paper 2 candidate
│   ├── 05-observation-granularity.md  # Paper 2-3 candidate
│   ├── 06-planning-depth.md     # Paper 3 candidate
│   ├── 07-retry-recovery.md     # Paper 3 candidate
│   ├── 08-verification-cadence.md  # Paper 3 candidate
│   ├── 09-compaction-policy.md  # Paper 3-4 candidate
│   ├── 10-tool-scheduling.md    # Paper 4 candidate
│   ├── 11-delegation-topology.md  # Paper 4+ candidate
│   └── 12-instruction-hierarchy.md  # Paper 4+ candidate
├── wiki/                  # Research knowledge base
│   ├── SOUL.md            # Agent identity for this project
│   ├── USER.md            # Kevin in research context
│   ├── HEARTBEAT.md       # Research operational cadence
│   └── log.md             # Chronological operation log
├── research/              # Frontier research tracking
│   ├── frontier-research-spec.md  # Full intelligence spec
│   └── scans/             # Weekly scan reports (YYYY-MM-DD.md)
├── harness/               # Evaluation framework
│   ├── README.md          # Harness architecture and usage
│   ├── config.py          # Shared configuration
│   ├── runner.py          # Experiment runner (async, model-agnostic)
│   ├── conditions/        # Language condition implementations
│   │   ├── base.py        # Abstract condition interface
│   │   ├── english.py     # English-only baseline
│   │   ├── chinese.py     # Internal Chinese
│   │   ├── controlled.py  # Controlled Chinese (restricted lexicon)
│   │   ├── compressed.py  # English + LLMLingua compression
│   │   ├── structured.py  # Structured English protocol
│   │   ├── router.py      # Dynamic router
│   │   └── polish.py      # Polish stress condition
│   ├── benchmarks/        # Benchmark adapters
│   │   ├── base.py        # Abstract benchmark interface
│   │   ├── tau_bench.py   # τ-bench adapter
│   │   ├── api_bank.py    # API-Bank adapter
│   │   ├── webarena.py    # WebArena adapter
│   │   └── swe_bench.py   # SWE-bench adapter (optional)
│   ├── metrics/           # Metric collection and analysis
│   │   ├── collector.py   # Per-step metric collection
│   │   ├── analyzer.py    # Pareto frontier, decomposition
│   │   ├── fertility.py   # Tokenizer fertility measurement
│   │   └── safety.py      # Safety evaluation suite
│   └── routing/           # Dynamic routing policy
│       ├── features.py    # Message feature extraction
│       ├── policy.py      # Routing policy implementation
│       └── optimizer.py   # Policy optimization
├── data/                  # Collected data (gitignored except schemas)
│   ├── traces/            # Raw agent traces (JSONL)
│   ├── tokens/            # Tokenizer fertility measurements
│   └── results/           # Aggregated experiment results
├── raw/                   # Immutable source material
│   ├── papers/            # Downloaded papers for reference
│   ├── traces/            # Raw traces from external benchmarks
│   └── baselines/         # Baseline measurements
├── experiments/           # Experiment definitions (YAML)
│   ├── pilot_01.yaml      # First pilot: tau-bench, 3 conditions, 5 tasks
│   └── ...
├── scripts/               # Utility scripts
│   ├── fertility.py       # Measure tokenizer fertility across languages
│   ├── analyze.py         # Generate analysis reports
│   └── plot.py            # Visualization (Pareto frontiers, decomposition)
├── automations/           # Recurring research tasks
│   ├── _schema.md         # Automation contract
│   ├── literature-scan.md # Weekly paper scan
│   └── fertility-check.md # On new model: measure fertility
├── skills/                # Research-specific agent skills
│   ├── run-experiment.md  # Skill for running experiments
│   ├── analyze-traces.md  # Skill for trace analysis
│   └── update-memory.md   # Skill for updating memory.json
└── .cursor/rules/         # Cursor rules
```

## Research Operations

### Running an Experiment

1. Define the experiment in `experiments/<name>.yaml`
2. Run: `python -m harness.runner experiments/<name>.yaml`
3. Traces written to `data/traces/`
4. Results aggregated to `data/results/`
5. Update `memory.json` with findings
6. Append to `wiki/log.md`

### Experiment YAML Schema

```yaml
name: pilot_01
description: "First pilot: tau-bench with 3 conditions"
benchmark: tau_bench
conditions: [english_only, internal_chinese, structured_english]
model: claude-4-sonnet
tasks: 5
seeds: [42, 43, 44]
metrics:
  - total_billed_tokens
  - task_success_rate
  - tool_call_exact_match
  - wall_clock_latency_ms
  - cost_usd
```

### Adding a New Benchmark

1. Create `harness/benchmarks/<name>.py` implementing `BenchmarkAdapter`
2. Add benchmark config to `memory.json` → `benchmarking.primary_benchmarks`
3. Create an experiment YAML using the new benchmark
4. Run pilot (3-5 tasks) and verify trace collection works

### Adding a New Orchestration Condition

1. Create `harness/conditions/<name>.py` implementing `LanguageCondition`
   (will be generalized to `OrchestrationCondition` as we study more variables)
2. Add condition config to `memory.json` → `benchmarking.conditions`
3. The condition must implement: `transform_message(message, message_type) → str`
4. Test on a small set of messages before using in experiments

## Evaluation Harness Architecture

The harness follows Kevin's deterministic-collector + LLM-judge pattern from
the brain-agent loop:

```
┌─────────────────────────┐     ┌──────────────────────────┐
│  Deterministic Harness  │────>│       LLM Agent          │
│                         │     │                          │
│  • Load experiment YAML │     │  • Execute agent loop    │
│  • Apply language cond  │     │  • Use tools             │
│  • Collect traces       │     │  • Generate responses    │
│  • Count tokens         │     │  • Reason over state     │
│  • Measure latency      │     │                          │
│  CODE — 100% reliable   │     │  AI — the thing we test  │
└─────────────────────────┘     └──────────────────────────┘
```

### Message Type Classification

Every intermediate message in an agent trace is classified:

| Type | Description | Language policy | Expected compression |
|------|-------------|-----------------|---------------------|
| `planner_note` | Planning/reasoning text | VARIABLE | High |
| `subtask_handoff` | Inter-agent delegation | VARIABLE | Medium |
| `memory_update` | Working memory summary | VARIABLE | High |
| `retry_diagnosis` | Error analysis | VARIABLE | Medium |
| `coordinator_msg` | Multi-agent coordination | VARIABLE | Medium |
| `tool_call` | Tool invocation + JSON | FIXED (English) | None |
| `tool_result` | Tool output | MIXED (as received) | None |
| `user_response` | Final answer to user | FIXED (English) | None |

### Metrics Pipeline

```
Agent trace (JSONL)
  → Per-step metrics (tokens, latency, success)
  → Per-message-type aggregation
  → Per-condition aggregation
  → Cross-condition comparison
  → Pareto frontier analysis
  → Message-type decomposition
```

## Key Design Principles

### From Kevin's Toolkit

**Brain-first lookup.** Search existing data and literature before running new
experiments. The wiki in `~/Documents/GitHub/my-wiki/` has compiled knowledge.

**No one-off work.** If an analysis will be needed again, build it into a script
or automation. The first run is manual; the second run should be automated.

**Test before bulk.** Run 3-5 tasks per condition before full benchmark runs.
Review trace quality. Fix issues in the harness, not via one-off patches.

**Boil the lake.** When collecting traces, collect ALL metrics — not just the
ones you think matter. The marginal cost is near-zero. Missing data is expensive.

**Surgeon mindset.** The harness should be minimal and correct. No speculative
abstractions. Build what's needed for the current experiment.

### From GBrain/GStack Patterns

**Compiled truth + timeline.** Wiki pages have compiled synthesis (above `---`)
and append-only evidence log (below `---`). Compiled truth gets REWRITTEN when
new evidence arrives. Timeline is APPEND-ONLY.

**Signal detector.** After every session, check: did anything emerge that should
update `memory.json` or the wiki? New paper, new model, new benchmark result,
new insight about the experimental design.

**Cross-modal review.** Before submitting paper or presenting to Danqi, run the
analysis through a different model for independent verification.

### From Claude Code Harness Patterns

**Model-agnostic.** The harness must work with Claude, GPT, DeepSeek, Gemini.
Model-specific code lives in adapter classes, not in the harness core.

**Hook-based quality gates.** Trace validation runs automatically after every
experiment. Malformed traces are caught immediately.

**Strategic compaction.** For long experiment sessions, compact at logical
breakpoints (after a benchmark suite completes, not mid-run).

## Safety Evaluation Protocol

Safety is not optional — it's a primary metric. The proposal includes safety
as a term in the optimization function (λ_s·SafetyRisk).

### Tests Required

1. **Prompt injection resistance** — tool outputs containing injection attempts
   in mixed languages
2. **Refusal consistency** — does the model refuse harmful requests equally
   across all language conditions?
3. **Schema fidelity** — do tool call arguments maintain correct types and
   values when internal reasoning is in a different language?
4. **Semantic fidelity** — entailment scoring between switched and unswitched
   traces for terminology-heavy reasoning

### Safety Red Lines

If any condition shows:
- >5% increase in safety failure rate vs English-only baseline
- >10% decrease in tool argument correctness
- Evidence of injection bypass via language mixing

That condition is flagged and the result is reported as a negative finding.
This is equally publishable and scientifically valuable.

## Conventions

- **Slugs:** `kebab-case` for files and directories
- **Dates:** ISO 8601 (`YYYY-MM-DD`)
- **Traces:** JSONL format, one message per line
- **Configs:** YAML for experiment definitions
- **Code:** Python 3.11+, type hints, async where applicable
- **Git:** Conventional commits (`feat:`, `fix:`, `data:`, `paper:`, `harness:`)
- **Data:** Raw traces in `data/traces/`, never modified after collection

## Integration with my-wiki

This repo is the implementation. The wiki at `~/Documents/GitHub/my-wiki/` is
the knowledge base. They work together:

- `my-wiki/wiki/research/cotcodec-paper.md` — human-readable proposal mirror
- `my-wiki/wiki/research/language-orchestration.md` — compiled knowledge brief
- `my-wiki/raw/research/language-orchestration-research-spec.tex` — LaTeX source
- `my-wiki/automations/language-orchestration-radar.md` — weekly paper scan

When experiments produce findings, update both the wiki and `memory.json`.

## Skills

### Installed (from my-wiki)

| Skill | Purpose |
|-------|---------|
| `last30days` | Research any topic across Reddit, X, YouTube, HN, etc. |
| `agent-reach` | Internet access for paper fetching, API docs |
| `cross-modal-review` | Quality gate via second model |
| `content-strategy` | For eventual paper promotion |

### Project-Specific

| Skill | Path | Purpose |
|-------|------|---------|
| `frontier-research` | `skills/frontier-research.md` | Frontier research scan across labs, arxiv, community |
| `run-experiment` | `skills/run-experiment.md` | Execute experiment from YAML |
| `analyze-traces` | `skills/analyze-traces.md` | Trace analysis and decomposition |
| `update-memory` | `skills/update-memory.md` | Update memory.json after findings |
| `fertility-check` | `skills/fertility-check.md` | Tokenizer fertility measurement |

## Compute Infrastructure

### Mac Mini (Always-On Runner)

The Mac Mini serves as the project's always-on compute node. Setup:
`./scripts/setup-mac-mini.sh`

| Role | What it does |
|------|-------------|
| Experiment runner | Process queued experiments 24/7 via `scripts/run-queue.sh` |
| Research scanner | Weekly frontier scans on cron (Monday 6am) |
| Local inference | Run open-weight models (DeepSeek, Qwen, Llama) via MLX/Ollama for free |
| Benchmark host | Run tau-bench, API-Bank, WebArena docker environments |
| Trace analysis | DuckDB at `data/traces.duckdb` for fast SQL queries over experiment data |
| Auto-sync | Push results to GitHub automatically after each batch |

### Experiment Workflow

```
Kevin's laptop                           Mac Mini
──────────────                           ────────
Define experiment YAML                   
  │                                      
  ├── ./scripts/queue-experiment.sh ──→  data/queue/*.yaml
  │                                        │
  │                                        ├── ./scripts/run-queue.sh (cron)
  │                                        │     │
  │                                        │     ├── Run harness against API/local models
  │                                        │     ├── Collect traces to data/traces/
  │                                        │     ├── Aggregate to data/results/
  │                                        │     └── git push results
  │                                        │
  └── git pull ←──────────────────────── Results available
```

### Local Inference Strategy

Free experimentation on open-weight models before spending on API calls:

| Model | Framework | Use case |
|-------|-----------|----------|
| DeepSeek-R1 (distilled 8B) | MLX / Ollama | Primary — our key evidence paper. Free pilots. |
| Qwen-3 8B | MLX / Ollama | Multilingual Chinese-English. Language variable experiments. |
| Llama-4 8B | MLX / Ollama | Open-weight baseline. |
| Claude-4-Sonnet | Anthropic API | Publication-grade closed-model experiments. |
| GPT-4o / GPT-5 | OpenAI API | Cross-provider comparison. |

**Strategy:** Run pilot experiments locally (free, unlimited), validate harness
correctness, then run publication experiments on closed models (metered).

### API Budget

Track per-experiment spend. Pilot experiments should cost <$5 each.
Full benchmark runs budget ~$50-100 per condition per benchmark.
Use `memory.json` → `infrastructure.compute.api_budget` to track.

## Required Tooling

| Tool | Purpose |
|------|---------|
| Python 3.11+ | Harness runtime |
| `uv` | Package management (fast, modern) |
| `httpx` | Async API calls |
| `tiktoken` | OpenAI tokenizer measurement |
| `anthropic` | Claude API client |
| `openai` | OpenAI API client |
| `mlx` / `mlx-lm` | Local inference on Apple Silicon |
| `ollama` | Easy local model serving |
| `duckdb` | Fast trace analysis (SQL over JSONL) |
| `matplotlib` / `seaborn` | Plotting (Pareto frontiers) |
| `pandas` | Data analysis |
| `pyyaml` | Experiment configs |
| `rich` | Terminal output |
| `tailscale` | Remote access to Mac Mini |
