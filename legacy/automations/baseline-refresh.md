---
title: Compression Baseline Refresh
slug: baseline-refresh
schedule: monthly
agents: [cursor, claude-code]
sources:
  - "https://arxiv.org (cs.CL prompt compression)"
  - "https://github.com (llmlingua, prompt compression)"
output_format: markdown
tags: [baselines, compression, llmlingua]
---

# Compression Baseline Refresh

> Monthly check for new prompt compression techniques that should serve as
> baselines in the CoTCodec evaluation.

## Context

Read `memory.json` for current baseline list.
The proposal compares against LLMLingua and LLMLingua-2 as strong compression baselines.
New techniques may emerge that provide stronger baselines.

## Task

1. Search for new prompt compression papers and tools from the last 30 days
2. Check for updates to existing baselines (LLMLingua-3, new versions)
3. Evaluate whether any new technique should be added as a condition
4. Check if any new structured reasoning format has been proposed

## Output

- List of new compression techniques found
- Recommendation: add as condition, monitor, or ignore
- If adding: specify the condition implementation approach
