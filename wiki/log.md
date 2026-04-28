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
