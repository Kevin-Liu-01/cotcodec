---
title: Tokenizer Fertility Check
slug: fertility-check
schedule: on_new_model
agents: [cursor, claude-code]
sources:
  - "model release announcements"
output_format: json
tags: [tokenizer, fertility, measurement]
---

# Tokenizer Fertility Check

> When a new model is released, measure tokenizer fertility across target languages.

## Context

Read `memory.json` → `landscape_tracking.models_to_track` for the model list.
Read `data/tokens/` for existing fertility measurements.

## Task

For each new model:

1. Prepare a parallel corpus of 20 text samples spanning:
   - Planning text (agent planner notes)
   - Memory summaries (agent working memory)
   - Technical documentation
   - Error messages and diagnostics
   - Mixed code-and-prose

2. Translate each sample into: Chinese, Korean, Polish, Russian, Japanese

3. Measure token counts using the model's tokenizer

4. Compute fertility: tokens(L) / tokens(English)

5. Write results to `data/tokens/{model}_fertility.json`

6. Update `memory.json` → `landscape_tracking` with the new model's fertility data

## Output Format

```json
{
  "model": "model-name",
  "date": "YYYY-MM-DD",
  "samples": 20,
  "languages": {
    "chinese": { "mean_fertility": 0.79, "std": 0.05, "samples": [...] },
    "korean": { "mean_fertility": 0.56, "std": 0.08, "samples": [...] },
    "polish": { "mean_fertility": 1.62, "std": 0.12, "samples": [...] }
  }
}
```

## Quality Gate

- Minimum 20 parallel text samples
- All samples must be semantically equivalent (verified by back-translation)
- Report both mean and standard deviation
- Flag any language with fertility > 1.5 or < 0.5 as notable
