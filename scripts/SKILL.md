---
name: scripts-skill
description: Procedure for CoTCodec validators, runners, sealers, compilers, analyzers, and remote workload entry points.
---

# cotcodec / scripts

## Purpose
<!-- agent-docs:fill:purpose -->

Scripts make every repeated research operation executable: validate contracts,
prepare immutable inputs, run contained workloads, analyze traces, and seal evidence.

## Mental model & key files
<!-- agent-docs:fill:model -->

- `validate_*` scripts fail closed on decision-bearing contract drift.
- `run_*` scripts execute local or contained workloads and write versioned outputs.
- `seal_*` scripts reduce raw outputs into portable evidence bundles.
- `compile_*`, `prepare_*`, and `freeze_*` scripts construct preregistered inputs.
- `run-agent-docs.ts` forwards documentation maintenance to the canonical wiki kit.

## Patterns to follow / invariants
<!-- agent-docs:fill:patterns -->

- Make scripts runnable both as modules and by file path; insert the project root
  before repository imports when remote launchers execute `python path/to/script.py`.
- Validate inputs before creating output, refuse overwrite, write temporary files,
  then atomically replace the final artifact.
- Return distinct codes for expected falsification versus infrastructure crash.
- Capture commands, versions, hashes, stdout/stderr, timings, and completion state.
- Keep validation logic shared between CLI and tests rather than parsing CLI text.

## Common tasks → first action
<!-- agent-docs:fill:tasks -->

- New experiment family: create validator, runner, sealer, tamper tests, and route
  it through the directory-level validator.
- Remote Slurm run: validate locally, hash staged files, verify remote hashes, then
  submit to a new immutable output root.
- Analysis: consume raw immutable inputs and emit a new derived artifact with lineage.

## Gotchas
<!-- agent-docs:fill:gotchas -->

- Remote nodes may lack `rg`, project virtualenvs, or the repository on `sys.path`.
- Never silently accept a partial manifest, missing repeat, unknown status, or
  locally committed trust key.
- Do not put large source archives, model weights, databases, or build trees in Git.
