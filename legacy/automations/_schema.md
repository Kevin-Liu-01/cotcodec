# Automation Schema

Every automation file in this directory follows this contract.

## Frontmatter

```yaml
---
title: Human-readable name
slug: kebab-case-identifier
schedule: daily | weekly | monthly | on_event
agents: [cursor, claude-code, codex]
wiki_targets: ["path/to/wiki/page.md"]
sources: ["list of URLs or paths to scan"]
output_format: markdown
tags: [relevant, tags]
---
```

## Body

The body is the full prompt for the automation. It must include:
1. Context — what files to read first
2. Task — what to do
3. Output format — structured format for results
4. Quality gate — what counts as a valid signal

## Running

Manual: Read the automation file and execute the task.
Output written to: `data/results/<date>/<slug>.md`
