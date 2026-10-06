---
name: run-experiment
version: 0.1.0
triggers: ["run experiment", "execute experiment", "run pilot", "benchmark"]
tools: [shell, read, write]
mutating: true
---

# Run Experiment

Execute an experiment from a YAML definition file.

## Contract

Given an experiment YAML path, this skill:
1. Validates the YAML against the experiment schema
2. Checks that all required benchmark data is available
3. Executes the experiment runner
4. Verifies trace output is well-formed
5. Generates summary statistics
6. Updates `memory.json` with results

## Steps

1. Read the experiment YAML
2. Verify benchmark adapter is implemented (not just a stub)
3. Run: `python -m harness.runner experiments/<name>.yaml`
4. Check output in `data/traces/` — verify JSONL is valid
5. Check output in `data/results/` — verify summary JSON
6. Update `memory.json` → `state.next_actions` with findings

## Anti-Patterns

- Do NOT run experiments without checking that the benchmark adapter is implemented
- Do NOT skip the trace validation step
- Do NOT run full benchmark suites before pilot (3-5 tasks) passes
- Do NOT modify experiment YAML after results are collected (create a new one)

## Output Format

```
Experiment: <name>
Status: completed | failed | partial
Tasks: X/Y completed
Results: data/results/<experiment_id>_summary.json
Traces: data/traces/<benchmark>/<condition>/
Key finding: <1-2 sentences>
```
