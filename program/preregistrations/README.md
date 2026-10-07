# Preregistrations

One Markdown file per experiment, written and frozen before any treatment data
exists. A file states:

- the experiment id, question, and the exact code revision and data it uses;
- primary and secondary metrics, with their unit of analysis;
- the decision rules and kill criteria, with thresholds;
- seeds, sample sizes, and the minimum effect the design can detect;
- what counts as an infrastructure failure and how it is excluded;
- what will be reported regardless of outcome.

Freeze it, then commit both files:

```bash
uv run python scripts/preregister.py freeze <experiment-id> program/preregistrations/<file>.md
uv run python scripts/preregister.py verify <experiment-id>
```

`ledger.jsonl` is hash-chained. Every result receipt records the frozen
SHA-256. A frozen file is never edited; a material change is a new file with a
new experiment id, and the old one stays in the ledger.
