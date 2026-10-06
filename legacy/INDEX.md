# Legacy archive (frozen 2026-10-06)

Everything here belongs to the program that ran from August to early October
2026. It is kept read-only for reference, reuse and honesty about what was
tried. Nothing here is the current program; see `program/PROGRAM.md`.

- Every file was moved with `git mv` from its original path, so
  `legacy/<path>` was `<path>` before 2026-10-06 and `git log --follow` works.
- The exact pre-restart tree is git tag `legacy-2026-10-06`.
- Tests under `legacy/tests/` are not collected by pytest, and ruff skips
  this directory. They ran against the old layout and may not pass here.
- To revive something, move it back out with `git mv`, rerun its doctor and
  tests, and re-check its priors against
  `program/evidence/2026-10-06/question-dossier.md`.

## What the old program was

A study of orchestration variables for tool-using agents. Paper 1 asked
whether the language of an agent's intermediate messages could be routed per
task. A memory-policy line audited about 40 open-source agent-memory systems
for lifecycle correctness. The D17-D22 lines proposed architecture and
attachment experiments, mostly around translation as supervision.

## Status of each line on 2026-10-06

| Line | Where | Status |
|---|---|---|
| Paper 1, reasoning-language routing | `directions/01-language.md`, `paper/` | Dropped; claims withdrawn. Failed the correctness gate in the 2026-10-06 verification |
| Directions 02-16 | `directions/` | Not re-verified; superseded by the restart |
| D17 causal memory holdout | `directions/17-*`, `harness/causal_memory_trials.py` | Dropped; occupied by CMP (arXiv 2610.02070) |
| D18 translation byte boundaries | `directions/18-*`, `harness/translation_boundaries.py` | Backlog (E3) |
| D19 in-context rule distillation | `directions/19-*`, `harness/icl_rule_distillation.py` | Backlog (E4) |
| D20 semantic clock gate parity | `directions/20-*`, `harness/semantic_clock_gate_parity.py` | Backlog (E5) |
| D21 translation-supervised sparse indexer | `directions/21-*` | **Live as Q3.** Contract, doctor and proposal moved to the live tree |
| D22 translation-equivariant state writes | `directions/22-*`, `harness/translation_equivariant_state_writes.py` | Backlog (E7) |
| Memory lifecycle audits | `research/*-audit-*.md`, `infra/memory-baselines/`, `experiments/memory/`, `harness/memory_trials/` | Dropped as a line (E8); evidence kept |
| Relay interface lab | `research/`, `experiments/orchvar_*` | Dropped (E9); interface main effects fold into Q2 |
| Qwen recurrent-state interface gate | `experiments/architectures/qwen35-4b-recurrent-state-interface.yaml` | Frozen node; not continued |
| Tinker and Kimi policies | `experiments/tinker/`, `infra/tinker/` | Not continued |
| Frontier gauntlet waves | `research/gauntlet/`, `data/research-gauntlet/` | Historical ledger |

## Map

| Path | Contents |
|---|---|
| `directions/` | 22 direction write-ups and their index |
| `research/` | Scans, program docs, audits, proposals, sealed evidence, gauntlet waves |
| `harness/` | Agent loops, conditions, metrics, routing, memory trials, capsules |
| `experiments/` | Experiment YAMLs: orchestration, memory stages, architectures, Tinker |
| `scripts/` | Validators, runners, sealers and doctors for the lines above |
| `infra/` | Memory baseline doctors and sidecars, Tinker, older Slurm manifests |
| `tests/` | Tests for all of the above, plus the pre-split versions of live tests |
| `docs/` | Old state, runbooks, data policy, repository map |
| `wiki/`, `memory.json` | Old session context and state |
| `skills/`, `automations/` | Old agent procedures and scheduled-task specs |
| `paper/` | Paper 1 LaTeX spec |

## Not here on purpose

Some material was never committed, or was removed because the repository is
public: an employer-internal corpus inventory, the host address, a local Slack
bot with credentials, and an unfinished Letta doctor that demonstrates an
issue not yet disclosed to its maintainers. Those are kept in a private archive
outside this repository. Earlier versions of some of them remain in public git
history; purging history is a separate decision.
