# CoTCodec — Agent Operating Guide

A research program on checker adequacy and calibrated measurement for
verifiable machine work, run on one 8 x H100 node. Restarted 2026-10-06.

**Author:** Kevin Liu (Princeton CS '28). **Advisor:** Professor Danqi Chen
(Princeton NLP Group).

## The mental model

This is a research project, not a product. The goal is rigorous, reproducible
experiments with publishable results, positive or negative. Every piece of
infrastructure exists to produce clean evidence. The harness is the product.

## Session start

1. Read `program/state.json` and the latest entry in `program/log.md`.
2. Read `program/PROGRAM.md` if the task touches research direction.
3. Read `HANDOFF.md` for the most recent session's open items.
4. Report stale gates, failing tests and pending decisions before new work.

## The program in one paragraph

The checker that judges a kernel or a desktop task becomes the RL reward and
the benchmark score. Q1 asks whether a stronger kernel correctness gate changes
what RL learns. Q2 builds a calibrated computer-use instrument that separates
harness, interface and rerun noise, and mutation-tests the benchmark's own
checkers. Q3 is a preemptible backfill on cross-script recall of learned
sparse-attention indexers. Details: `program/PROGRAM.md`.

## Where things live

| Path | Owner of |
|---|---|
| `program/PROGRAM.md` | Thesis, questions, staged plan, Codex comparison |
| `program/questions/` | One file per live question |
| `program/backlog.md` | Backfill queue and dropped lines with reasons |
| `program/state.json` | Machine-readable state and pending decisions |
| `program/log.md` | Append-only timeline |
| `program/proposals/` | Gauntlet proposals, template, evidence schema |
| `program/evidence/` | Dated evidence bundles |
| `experiments/` | Preregistered contracts; `experiments/orx/node.yaml` |
| `harness/` | Mechanisms and attestation helpers |
| `scripts/` | Validators, submitters, doctors, provenance |
| `infra/` | Research images, Slurm entry points |
| `models/` | Model and provider registries |
| `docs/` | `h100-node.md`, `operations.md`, `gauntlet-procedure.md`, `evidence-model.md` |
| `legacy/` | Frozen previous program; `legacy/INDEX.md` explains it |

## Hard rules

1. **Public repository.** Never commit secrets, API keys, host addresses,
   employer-internal material, private datasets or `.env` files. Refer to the
   node as `fal-h100-01` or `<h100-alias>`.
2. **Compute.** Every GPU run uses a digest-pinned Docker image, a Slurm job
   through `scripts/submit_docker_research_job.py`, persistent checkpoints and
   a fresh-job resume test. `tmux` owns the operator session; Slurm owns the
   workload. Never use `orx --backend slurm` for GPU work.
3. **Untrusted code.** No untrusted model-generated code (sampled kernels,
   policy rollouts, programs produced during an experiment) runs with GPU
   access while the node is on the R570 driver. Reviewed, tested, committed
   harness code is project code.
4. **No root.** The research account has no root. Never use `docker` group
   membership to change the host. Admin work is listed in `docs/h100-node.md`.
5. **Gauntlet.** New directions, new mechanisms and any run over 8 GPU-hours
   follow `.claude/rules/research-gauntlet-loop.md` until 100 or an honest exit.
6. **Evidence.** Never edit a contract or doctor to make an existing output
   pass. Version every rerun. Never erase a negative result or a score dip.
7. **Seeds.** `[42, 43, 44]` minimum, declared before the run; seed count is
   justified by a stated minimum effect, not habit.
8. **Citations.** Every quantitative claim carries a primary-source URL and a
   date. Never write "completely novel".
9. **Outward actions** (emails, issues, disclosures, downloads over 1 GB,
   force-pushes) need Kevin's explicit go-ahead.

## Research gauntlet

The always-on contract is `.claude/rules/research-gauntlet-loop.md`, mirrored
at `.cursor/rules/research-gauntlet-loop.mdc`. The full procedure is
`docs/gauntlet-procedure.md`.

```
preflight doctors -> independent discovery -> novelty audit -> candidate contract
  -> adversarial review -> fix the largest defect -> repeat
```

`100/100` means pilot-ready, not proven, novel or perfect. The lower of two
independent reviewer scores counts. Parallelize independent evidence
collection; give coupled synthesis one sequential owner.

## OpenResearch experiment tree

The repository is an `orx` project. Every node runs the single fixed command
`uv run --locked python scripts/orx_run.py` over the committed
`experiments/orx/node.yaml` on its `orx/<slug>` branch. Node kinds:
`cpu-doctor` and `slurm-manifest`. `orx discover` and `orx paper` are the
required novelty-retrieval modality. Daily commands: `docs/operations.md`.

## Checks

```bash
uv run ruff check .
uv run pytest -q tests
uv run python scripts/validate_architecture_experiments.py
uv run python scripts/validate_provider_models.py
node scripts/run-agent-docs.ts doctor .
```

## Conventions

- Slugs are `kebab-case`; dates are ISO 8601.
- Python 3.11+, type hints on public functions, ruff.
- Conventional commits: `feat:`, `fix:`, `research:`, `docs:`, `infra:`.
- Raw outputs stay in ignored `data/` or on the node's persistent run root,
  never modified after collection.

## Agent-docs (auto-maintained)

> Machine-derived facts maintained by `agent-docs`; do not hand-edit inside the markers.

<!-- agent-docs:auto:stack start -->
- **Name:** cotcodec
- **Package manager:** unknown
- **Languages:** n/a
- **Framework:** n/a
<!-- agent-docs:auto:stack end -->

<!-- agent-docs:auto:commands start -->
- (no package.json scripts detected)
<!-- agent-docs:auto:commands end -->

<!-- agent-docs:auto:dirmap start -->
| Directory | Skill | Purpose |
|---|---|---|
| `harness/` | [`harness/SKILL.md`](harness/SKILL.md) | Procedure for CoTCodec mechanisms, doctors and attestation helpers in harness/. |
| `scripts/` | [`scripts/SKILL.md`](scripts/SKILL.md) | Procedure for CoTCodec validators, submitters, doctors, provenance and orx entry points. |
| `tests/` | [`tests/SKILL.md`](tests/SKILL.md) | Procedure for focused unit, contract-tamper, doctor and submitter tests. |
<!-- agent-docs:auto:dirmap end -->

<!-- agent-docs:auto:env start -->
- (none detected)
<!-- agent-docs:auto:env end -->

<!-- agent-docs:auto:repo-graph start -->
- Use Graphify for repo topology, path/explain/affected questions, PR risk, and unfamiliar codebase orientation.
- Use `rg` for exact strings; use Kevin-Wiki `qmd` for people, tools, decisions, and compiled wiki knowledge.
- Use `agent-browser` for browser/UI work; use Playwright only for committed regression tests.
- Runtime memories (Hermes/Hindsight/Honcho) are not project truth until written back to AGENTS.md, SKILL.md, or the wiki.
- Status: `cd ~/Documents/GitHub/kevin-wiki && npm run graphify:sidecar -- status --run outputs/graphify/cotcodec`
- Build from this repo: `PROJECT_ROOT="$(pwd)" && cd ~/Documents/GitHub/kevin-wiki && npm run graphify:sidecar -- build "$PROJECT_ROOT" --run outputs/graphify/cotcodec --no-viz`
- Query after build: `cd ~/Documents/GitHub/kevin-wiki && npm run graphify:sidecar -- query "what should I inspect first?" --run outputs/graphify/cotcodec`
- Never run Graphify installers/hooks or commit generated `graphify-out/` artifacts.
<!-- agent-docs:auto:repo-graph end -->
