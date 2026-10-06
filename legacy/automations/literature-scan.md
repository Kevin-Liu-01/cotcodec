---
title: CoTCodec Literature Scan
slug: literature-scan
schedule: weekly
agents: [cursor, claude-code]
sources:
  - "https://arxiv.org (cs.CL, cs.AI, cs.MA)"
  - "https://aclanthology.org"
  - "https://semanticscholar.org"
  - "https://huggingface.co/papers"
output_format: markdown
tags: [research, papers, literature]
---

# CoTCodec Literature Scan

> Weekly scan for new papers relevant to the CoTCodec project.

## Context

Read these files first:
- `memory.json` — current project state and landscape tracking
- `wiki/log.md` — what's already been found

## Task

Search for papers from the last 14 days matching these threads:

### Thread 1: Agent Internal Language / Protocol
Papers varying internal language or structured protocol in multi-step tool-using agents.

### Thread 2: Reasoning Model Language Behavior
Follow-ups to DeepSeek-R1 language mixing, Li et al. RLVR, EfficientXLang.

### Thread 3: Tokenizer / Script Tax
New tokenizer fairness papers, multilingual fertility measurements.

### Thread 4: Agent Benchmarks
Updates to tau-bench, API-Bank, WebArena, X-WebAgentBench, SWE-bench.

### Thread 5: Prompt Compression
LLMLingua successors, concise reasoning techniques.

### Thread 6: Safety Under Multilingual Mixture
Multilingual blending attacks, instruction hierarchy violations.

### Thread 7: Provider Updates
API changes, pricing changes, new model releases affecting the cost model.

## Output Format

```markdown
## Literature Scan — YYYY-MM-DD

### New Signals
1. [Title](url) — Thread X — Key finding — Impact on CoTCodec — Action: cite|read|watch

### Rejected
- [Title](url) — why rejected

### Recommended Updates to memory.json
- landscape_tracking.key_papers_since_proposal: [additions]
- landscape_tracking.provider_changes: [additions]
```

## Quality Gate

Only promote items with: a new measurement, mechanism, benchmark, baseline, or provider change.
Reject: surveys without data, blog posts, hype, tangential multilingual NLP.
