---
title: Frontier Research Scan
slug: frontier-research
schedule: weekly
agents: [cursor, claude-code, codex]
sources:
  - "https://arxiv.org (cs.CL, cs.AI, cs.MA, cs.SE)"
  - "https://huggingface.co/papers"
  - "https://anthropic.com/research"
  - "https://openai.com/research"
  - "https://github.com/deepseek-ai"
  - "https://deepmind.google/research"
  - "https://ai.meta.com/research"
  - "https://news.ycombinator.com"
  - "https://reddit.com/r/MachineLearning"
  - "https://x.com (research accounts)"
  - "https://semanticscholar.org"
  - "https://paperswithcode.com"
output_format: markdown
tags: [research, frontier, intelligence, papers, models]
---

# Frontier Research Scan

> Weekly scan across labs, arxiv, community, and providers for signals
> relevant to ANY of CoTCodec's 12 orchestration variables.
> Full spec: `research/frontier-research-spec.md`

## Context

Read these files first:
- `research/frontier-research-spec.md` — full operational spec
- `memory.json` → `landscape_tracking` for last scan date, known papers
- `memory.json` → `orchestration_variables` for the full variable list
- `directions/README.md` — variable taxonomy and connections

## Execution Protocol

### Step 1: Lab Blogs & Announcements (Tier 1)

Check each lab for new posts/papers since last scan:

```bash
# Anthropic
curl -s "https://r.jina.ai/https://anthropic.com/research"

# OpenAI
curl -s "https://r.jina.ai/https://openai.com/research"

# DeepSeek — check GitHub releases
gh api repos/deepseek-ai/DeepSeek-R1/releases --jq '.[0:3] | .[] | .tag_name + " " + .published_at'

# Google DeepMind
curl -s "https://r.jina.ai/https://deepmind.google/research/publications/"

# Meta FAIR
curl -s "https://r.jina.ai/https://ai.meta.com/research/publications/"
```

### Step 2: arXiv (Tier 2)

Search for papers from the last 14 days:

```bash
# Primary queries (daily relevance)
curl -s "http://export.arxiv.org/api/query?search_query=ti:agent+AND+(ti:orchestration+OR+ti:tool+OR+ti:language)&sortBy=submittedDate&sortOrder=descending&max_results=20"

curl -s "http://export.arxiv.org/api/query?search_query=ti:reasoning+AND+(ti:language+OR+ti:multilingual+OR+ti:token)&sortBy=submittedDate&sortOrder=descending&max_results=20"

curl -s "http://export.arxiv.org/api/query?search_query=ti:agent+AND+(ti:memory+OR+ti:context+OR+ti:planning)&sortBy=submittedDate&sortOrder=descending&max_results=20"

# Safety
curl -s "http://export.arxiv.org/api/query?search_query=ti:agent+AND+(ti:safety+OR+ti:instruction+OR+ti:injection)&sortBy=submittedDate&sortOrder=descending&max_results=10"
```

### Step 3: Community Signal (Tier 3)

Use last30days or agent-reach for real engagement data:

```bash
# Hacker News — agent + reasoning + orchestration discussions
rdt search "LLM agent orchestration" --subreddit MachineLearning

# X — check key researcher accounts for announcements
twitter search "agent orchestration reasoning 2026" -n 20

# GitHub — trending repos in agent/LLM space
gh search repos "agent orchestration" --sort stars --limit 10
gh search repos "LLM benchmark agent" --sort updated --limit 10
```

### Step 4: Citation Tracking

Check forward citations of our key seed papers:

```bash
# Semantic Scholar API for citation tracking
# DeepSeek-R1
curl -s "https://api.semanticscholar.org/graph/v1/paper/search?query=deepseek+r1+reasoning+reinforcement&limit=5&fields=title,year,citationCount,url"

# EfficientXLang
curl -s "https://api.semanticscholar.org/graph/v1/paper/search?query=efficientxlang+cross+lingual+reasoning&limit=5&fields=title,year,citationCount,url"

# tau-bench
curl -s "https://api.semanticscholar.org/graph/v1/paper/search?query=tau+bench+tool+agent+user&limit=5&fields=title,year,citationCount,url"
```

### Step 5: Benchmark Leaderboards

Check for leaderboard changes on our target benchmarks:

```bash
# SWE-bench
curl -s "https://r.jina.ai/https://www.swebench.com"

# Papers With Code — agent benchmarks
curl -s "https://r.jina.ai/https://paperswithcode.com/task/autonomous-agents"
```

### Step 6: Provider API Changes

Check for pricing, model, or API changes:

```bash
# Anthropic docs
curl -s "https://r.jina.ai/https://docs.anthropic.com/en/docs/about-claude/models"

# OpenAI pricing
curl -s "https://r.jina.ai/https://openai.com/api/pricing"
```

## Evaluation

For each signal found, apply the scoring rubric from `research/frontier-research-spec.md`:

| Score | Meaning | Action |
|-------|---------|--------|
| 5 | Changes our experimental design | Read immediately, update proposal |
| 4 | New baseline or competitor | Read within 48h, add to bibliography |
| 3 | Relevant evidence | Read within a week |
| 2 | Tangentially relevant | File for later |
| 1 | Interesting but not actionable | Note and move on |

## Output

Write the report to `research/scans/YYYY-MM-DD.md` following the schema
in `research/frontier-research-spec.md` → Output Schema.

Then:
1. Update `memory.json` → `landscape_tracking` with all signals scored 3+
2. Update relevant `directions/*.md` files for signals scored 4+
3. Add bibliography entries for signals with action `cite`
4. Append summary to `wiki/log.md`

## Quality Gate

- Every promoted signal must have a concrete URL and date
- Every score 4+ signal must explain impact on a specific orchestration variable
- Reject anything without data, measurements, or reproducible claims
- Note if someone is working on the same question (competitive intelligence)
