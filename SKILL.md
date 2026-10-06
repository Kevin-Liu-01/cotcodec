---
name: cotcodec-skill
description: Repository-wide procedure for CoTCodec research, experiments, evidence, documentation, and release hygiene.
---

# cotcodec — working here

## Purpose
<!-- agent-docs:fill:purpose -->

CoTCodec is a research program on checker adequacy and calibrated measurement
for verifiable machine work: GPU kernels and desktop computer use, run on an
8 x H100 node. The harness and its receipts are the product.

## Mental model & key files
<!-- agent-docs:fill:model -->

- `program/PROGRAM.md` is the research program; `program/state.json` is the
  machine-readable state; `program/log.md` is the append-only timeline.
- `program/questions/` holds one file per live question; `program/backlog.md`
  holds the ordered backfill queue and dropped lines.
- `experiments/` holds preregistered contracts; `harness/` holds mechanisms;
  `scripts/` validates, submits and attests; `infra/` holds images and Slurm.
- `docs/` holds the node facts, operations, gauntlet procedure and evidence model.
- `legacy/` is the frozen previous program; see `legacy/INDEX.md`.

## Patterns to follow / invariants
<!-- agent-docs:fill:patterns -->

- Preregister falsifiers, budgets, seeds, claim boundaries and stop conditions
  before observing treatment results. Never rewrite a completed contract.
- Preserve negative and pre-result evidence. Version reruns; never overwrite.
- Every GPU run: digest-pinned image, Slurm, persistent checkpoints, fresh-job
  resume test. No model-generated code with GPU access on the R570 driver.
- New mechanisms and runs over 8 GPU-hours go through the research gauntlet.
- The repository is public: no secrets, host addresses, employer-internal
  material or private datasets.

## Common tasks → first action
<!-- agent-docs:fill:tasks -->

| Task | First action |
|---|---|
| Continue research | Read `program/state.json` and the latest `program/log.md` entry. |
| Work on a question | Read its file in `program/questions/` and the dossier entry it names. |
| Run a GPU job | Read `docs/operations.md`, then dry-run the manifest. |
| Propose a new direction | Follow `.claude/rules/research-gauntlet-loop.md`. |
| Revive old work | Read `legacy/INDEX.md`, then `git mv` it back and rerun its doctor. |

## Gotchas
<!-- agent-docs:fill:gotchas -->

- `data/` and `raw/` are ignored and can hold many gigabytes. Inspect before staging.
- The local laptop can be heavily loaded; a timing assertion that fails locally
  may pass on the H100 host. Compare CPU time with wall time before debugging.
- Old tests under `legacy/tests/` are not collected and may not pass.
- Set `KEVIN_WIKI_ROOT` for `scripts/run-agent-docs.ts` when the wiki is elsewhere.
