---
name: harness-q1-skill
description: Procedure for the Q1 Stage 0 kernel gate stack, mutator and substrate corpus in harness/q1/.
---

# cotcodec / harness / q1

## Purpose
<!-- agent-docs:fill:purpose -->

Q1 Stage 0 measures how often three kernel correctness gates accept kernels an
independent audit rejects, and how often they reject correct kernels, on a
corpus of compiler-generated and human-written Triton kernels and their
deterministic mutants. The draft preregistration is
`program/preregistrations/q1-stage0-gate-validation.md`.

## Mental model & key files
<!-- agent-docs:fill:model -->

- `schema.py` is the binding interface: substrate, mutant and control
  directories and verdict rows. Every component reads and writes it.
- `substrates/` builds the corpus (S1 Inductor conversion, S2 catalog,
  admission, the S1 split); `mutate/` derives mutants, the cap, the dev/test
  split and hack controls; `controls.py` builds the core controls.
- `runner.py` runs one `worker.py` process per kernel x gate x seed with a
  phase watchdog and an append-only journal; `gates/` and `audit/` produce the
  rows; `analysis.py` composes the ladder, tiers, metrics and control checks.
- `versions.py` is the version card the preregistration names.

## Patterns to follow / invariants
<!-- agent-docs:fill:patterns -->

- Never edit `schema.py` from a component branch; record a needed change.
- Splits come from their owners (`substrates/split.py`, `mutate/sampling.py`);
  the analysis never re-derives them.
- Agent-written Triton never runs with GPU access (D3, D7). CPU fixtures run
  under `TRITON_INTERPRET=1` in GPU-less containers only.
- After any change to Q1 code or data, regenerate the preregistration's
  version table with `python scripts/q1_version_card.py --markdown`.

## Common tasks → first action
<!-- agent-docs:fill:tasks -->

| Task | First action |
|---|---|
| Run the Q1 tests | GPU-less container with `cotcodec-q1-gates`: `python -m pytest -q tests/test_q1_*.py` |
| Run the CPU doctor | `experiments/manifests/q1-core/q1-gate-doctor-cpu.md` |
| Change shape rules | Edit `shapes.py`, then `scripts/build_q1_shape_manifest.py --write` in a container |
| Build controls | `python -m harness.q1.controls --out-root R` |

## Gotchas
<!-- agent-docs:fill:gotchas -->

- The Triton interpreter patches `triton.language` for the whole process;
  compile for sm_90 only in a fresh process without `TRITON_INTERPRET`.
- S1 substrates refuse CPU tensors and sizes below 2; gate (c) shapes are
  floored at 2 for that reason, while audit A3 keeps size 1.
- Gate (a)'s absolute tolerance 1e-2 hides errors on outputs far below 1e-2
  (softmax over many columns).
