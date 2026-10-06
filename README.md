# CoTCodec

A research program on **checker adequacy and calibrated measurement for
verifiable machine work**, run on one 8 x H100 node.

Restarted on 2026-10-06. The program is at Stage 0: no experiment from it has
run yet. The previous program (agent orchestration variables, Paper 1 on
reasoning language, memory-system audits) is archived under
[`legacy/`](legacy/INDEX.md) and at git tag `legacy-2026-10-06`.

## The idea

When a model writes GPU kernels or operates a desktop, a checker decides
whether the work was right. That checker becomes the RL reward and the
benchmark score. If it accepts wrong kernels, training learns to produce them.
If benchmark reruns flip outcomes, leaderboard gaps can be noise. So the
program measures the checker and the noise first, then trains or compares.

## Questions

| # | Question | Status |
|---|---|---|
| Q1 | [Does a stronger kernel correctness gate change what RL learns?](program/questions/q1-kernel-gate-strength.md) | Building gates; GPU audit waits on a driver upgrade |
| Q2 | [How much of computer-use benchmark variation is harness, interface or noise?](program/questions/q2-calibrated-cua-instrument.md) | CPU-only Stage 0: checker mutation and action-path tests |
| Q3 | [Do learned sparse-attention indexers drop cross-script evidence?](program/questions/q3-cross-script-indexer.md) | Backfill; CPU doctor passes, GPU entry point next |

The full program, its staged plan, and how it agrees and differs from the
Codex assessment are in [`program/PROGRAM.md`](program/PROGRAM.md). Every cited
source was checked against its primary text; the ranked dossier is in
[`program/evidence/`](program/evidence/README.md).

## Layout

| Path | What it holds |
|---|---|
| `program/` | Program, questions, backlog, state, log, proposals, evidence |
| `experiments/` | Preregistered contracts and the `orx` node |
| `harness/` | Mechanisms and attestation helpers |
| `scripts/` | Validators, submitters, doctors, provenance |
| `infra/` | Research images and Slurm entry points |
| `models/` | Model and provider registries |
| `docs/` | Node facts, operations, gauntlet procedure, evidence model |
| `tests/` | Unit, tamper and submitter tests |
| `legacy/` | The frozen previous program |

## Quick start

```bash
uv sync
uv run pytest -q tests
uv run python scripts/validate_architecture_experiments.py
```

GPU work goes through Slurm with a digest-pinned image. See
[`docs/operations.md`](docs/operations.md) and
[`docs/h100-node.md`](docs/h100-node.md).

## Rules

- Positive and negative results are equally valuable. Neither is erased.
- New mechanisms and runs over 8 GPU-hours pass the research gauntlet first
  (`.claude/rules/research-gauntlet-loop.md`).
- This repository is public. No secrets, host addresses, employer-internal
  material or private datasets.

## License

MIT. See [`LICENSE`](LICENSE).
