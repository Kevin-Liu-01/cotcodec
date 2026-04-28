# CoTCodec Research Log

Chronological record of all operations. Append-only.

## [2026-04-28] project-init | Repository scaffolded

Created the CoTCodec research repository with:
- `memory.json` — project state, direction, exploration strategies, Danqi's confirmation
- `AGENTS.md` — master operating guide incorporating patterns from Kevin's toolkit
  (brain-agent loop, no-one-off-work, compiled truth, deterministic collectors,
  cross-modal review, GBrain/GStack patterns, Claude Code harness architecture)
- Wiki identity files (SOUL.md, USER.md, HEARTBEAT.md)
- Directory structure: harness/, data/, experiments/, automations/, skills/, raw/
- Evaluation harness scaffolded with conditions, benchmarks, metrics, routing

Key decision: Danqi confirmed as advisor for Fall 2026. Field moving fast —
infrastructure must be model-agnostic and benchmark-pluggable. Phase 1
(foundation building) runs now through August 2026.

## [2026-04-28] research | Generalized to 12 orchestration variables + frontier research spec

Reframed from "language paper" to "orchestration variables research program."
Language is Paper 1; 11 additional variables mapped with hypotheses, conditions,
connections, and prior work. Created `directions/` with docs for all 12 variables.

Built frontier research intelligence infrastructure:
- `research/frontier-research-spec.md` — full operational spec covering 30+ sources
  across 3 tiers (labs, academic, community), 7 research threads, signal scoring
  rubric, competitive intelligence tracking, execution schedule
- `automations/frontier-research.md` — weekly scan automation with concrete search
  queries for arXiv, lab blogs, X, HN, Reddit, Semantic Scholar, GitHub
- `skills/frontier-research.md` — research scan skill
- `research/scans/` — directory for weekly scan reports

Source coverage: Anthropic, OpenAI, DeepSeek, DeepMind, Meta, Qwen, Mistral, xAI,
Cohere (labs); arXiv cs.CL/AI/MA/SE, ACL, Semantic Scholar, HF Papers, Papers With
Code, Princeton/Stanford/CMU/UW NLP (academic); X, HN, Reddit, GitHub, Alignment
Forum, Interconnects, The Gradient (community).

Competitive groups tracked: DeepSeek Research, Microsoft (EfficientXLang),
Li et al. (UPenn), Wang et al. (LMU Munich), Schut/Gal (Oxford).

## [2026-04-28] intel | Full intelligence source audit

Audited all Kevin's data sources for research intelligence:

- **294 X bookmarks** (168 unique accounts) — extracted 60+ research-relevant
  bookmarks covering agent harnesses, memory architecture, token optimization,
  subagent orchestration, benchmark infrastructure
- **41 installed skills** — mapped 13 research-relevant + 3 design/viz skills
- **51 Obsidian clips** — 8 research-relevant clips identified
- **378 wiki pages** — key pages mapped for each orchestration variable
- **10 key people to track** — @garrytan, @karpathy, @rauchg, @shawmakesmagic,
  @akseljoonas, @mvanhorn, @hwchase17, @affaanmustafa, @iamfakeguru, @himanshustwts
- **10 primary research tools** — last30days, agent-reach, Jina Reader,
  Semantic Scholar API, arXiv API, GitHub CLI, Exa, qmd, defuddle, nia-docs

Key signals captured:
- Claude Managed Agents (Anthropic official harness) — compatibility requirement
- Caveman token optimization (65% savings) — reasoning format baseline
- Claude Code reverse-engineering — compaction policy data points
- GBrain v0.11 Minions — delegation topology evidence
- ml-intern (HuggingFace) — automated research loop pattern

Built: `research/intelligence-sources.md` (comprehensive inventory)
Updated: `memory.json` with key signals, people, tool inventory

## [2026-04-28] intel | Deep intelligence audit — every bookmark, every follow

Full audit of all Kevin's data sources:

**X Bookmarks (294):**
- Every bookmark read, classified into 6 categories (agent_architecture: 147,
  design_engineering: 104, research: 13, tools: 4, career: 5, other: 21)
- 160 research-relevant signals extracted and mapped to 12 orchestration variables
- 53 unique linked URLs/repos cataloged
- Variable 3 (Memory policy) richest with 31 signals
- Variable 12 (Instruction hierarchy) has 18 signals
- Variable 8 (Verification cadence) has 16 signals
- Variable 11 (Delegation topology) has 13 signals

**X Following (172):**
- Full list pulled via `twitter following kevskgs --json`
- Classified: ai_ml_research (80), design (31), dedalus (10), infra (11),
  founders (8), agent_builders (4), other (28)
- 41 accounts overlap between following and bookmarks (highest signal)
- Key followed accounts not in bookmarks identified as monitoring gaps

**Cross-reference:**
- 33 tiered people to track (6 Tier 1, 14 Tier 2, 13 Tier 3)
- 6 direction docs enriched with community evidence

Built: `research/bookmark-signals.md` (329 lines — all 160 signals by variable)
Built: `research/x-following-analysis.md` (319 lines — full following classified)
Rewrote: `research/intelligence-sources.md` (complete inventory)
Enriched: `directions/02,03,08,09,11,12.md` with bookmark evidence
Updated: `memory.json` with full audit data + 33 people tracking list

## [2026-04-28] models+benchmarks | Frontier model update, harness-beats-model, degradation detection

**Model landscape updated to April 2026 frontier:**
- Frontier tier: Claude Opus 4.7 Adaptive (Elo 1503, SWE 87.6%), GPT-5.5
  (agentic 90.1, long-context 87.5), DeepSeek V4 Pro (overall 85, 9x cheaper, MIT)
- Strong tier: Sonnet 4.6, GPT-5.4 (Toolathlon 54.6%), DeepSeek V3.2, Gemini 3 Pro
  (tau-bench 85.4%)
- Baseline old: Sonnet 3.5, GPT-4o (for harness-beats-model hypothesis)
- All experiment YAMLs and model references updated

**Two new research directions:**
- `directions/13-harness-beats-model.md` — can old model + optimized orchestration
  beat new model + naive orchestration? Directly motivated by Anthropic April 23
  postmortem (3 harness-level changes caused perceived model degradation)
- `directions/14-degradation-detection.md` — McNemar's test statistical framework
  (ICLR 2026) + OrchVar-Canary custom benchmark for catching harness regressions

**Benchmark overhaul (2 existing + 6 new + 2 custom):**
- Added: MCP-Atlas (1K tasks, 36 MCP servers), Toolathlon (108 multi-system),
  SWE-bench Verified (500 human-validated), Amazing Agent Race (1400 DAG puzzles)
- Custom: OrchVar-Canary (regression detection, inspired by Anthropic postmortem),
  Multilingual-Agent-Fidelity (semantic fidelity under language switching)
- New module: `harness/metrics/degradation.py` — McNemar's test, Bonferroni/Fisher/Simes
  aggregation, canary task categories

**3 new experiments:**
- `harness_beats_model_01.yaml` — old + orchestrated vs. new + naive
- `degradation_canary_01.yaml` — validate canary catches simulated Anthropic bugs
- `frontier_comparison_01.yaml` — all 4 frontier models, all 7 conditions, 10 seeds

## [2026-04-28] research | Deep research on model degradation + harness-beats-model evidence

Researched the full 2026 "model quality crisis" across all major providers:

**Quantified harness-beats-model evidence:**
- SWE-bench: 42% → 78% from scaffolding alone (model swap < 1.3pts)
- AdaptOrch (arXiv 2602.16873): formal proof orchestration variance > model selection
- Vercel: 80% → 100% by reducing tools 15 → 2
- LangChain: +13.7pts from harness iteration only

**Provider-specific degradation mapped to orchestration variables:**
- GPT-5: hallucination 12%→23%, code length 187→62 lines (token economics, quantization, RLHF)
- Sonnet 4.6: 25→480 errors/week (19x), 1400+ events over 50 sessions (GitHub #46935)
- Gemini 3.1 Pro: formatting regression, attention drift, capacity issues
- DeepSeek V4: multi-turn stagnation from reasoning suffix constraints (V2)
- Cursor Composer 2: shipped Kimi K2.5 as own model — proved harness IS the product

Updated: directions/13 with full evidence from all providers + quantified data,
directions/14 with cross-provider degradation table, memory.json with evidence + papers
