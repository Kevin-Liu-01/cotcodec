---
name: harness-q2-zinv-reserve-skill
description: Procedure for the held-out test of the corrected z-order comparator (zinv) on the reserve split (registration q2-zinv-reserve-validation-v1, DRAFT, an addendum to q2-evaluator-mutation-v1) in harness/q2_zinv_reserve/.
---

# cotcodec / harness / q2_zinv_reserve

## Purpose
<!-- agent-docs:fill:purpose -->

R03 (b) of the 2026-10-11 renewal dossier: does `compare_pptx_files_zinv`
(`harness/q2_stage1/zinv.py`, validated by S1a on the confirm split, which was
also its development set) accept at least 95% of held-out z-order equivalence
mutants on the reserve split while accepting no violation mutant the original
rejects? Registration: `program/preregistrations/q2-zinv-reserve-validation-v1.md`
(DRAFT; the orchestrator freezes it, D80).

## Mental model & key files
<!-- agent-docs:fill:model -->

- `rules.py`: the registered constants (the 8 reserve pptx tasks, the reserve
  control files' digests, the reused code's pins), `judge` (conditions A and B,
  the O4 descriptive status, validity, outcomes) and the design numbers the
  registration quotes (`design_table`).
- `run.py`: the container steps. `select-targets` (end of step 1: pptx targets
  only, the registered 8 on reserve), `rescore` (step 4: S1a's validation set
  and worker, unchanged, original then zinv, each row with the registered
  verdict and scored-file digests), `judge`.
- `guard.py`: standard library only; code table, reused pins, the parent's code
  tree; reserve needs this experiment's ledger row and `Q2ZR_PREREG_FROZEN`.
- `infra/q2-zinv-reserve/run/zr_host.py`: the host tool (`plan`, `next`,
  `status`); steps 1-3 are the parent's frozen `submit_mutants.sh` jobs, one at a
  time, through the unchanged CPU lane.

## Patterns to follow / invariants
<!-- agent-docs:fill:patterns -->

- Never edit `harness/q2_mutation/`, `infra/q2-mutation/` or `harness/q2_stage1/`:
  the parent, R04 and S1a pin their bytes. New code lives here.
- zinv is never changed under this id; its digest is checked in every step.
- Every code change before the freeze: `uv run python -m harness.q2_zinv_reserve.guard code-table --write`
  and `uv run pytest -q tests/test_q2_zinv_reserve.py`. After the freeze a change
  is a new experiment id.
- Mutant documents stay on the host; only ids, labels, scores, errors and digests
  are committed.

## Common tasks → first action
<!-- agent-docs:fill:tasks -->

| Task | First action |
|---|---|
| Rehearse on dev (before the freeze) | Stage `git archive HEAD` under `/home/kevin/cotcodec-runs/stage0/q2-zinv-reserve/src/SHA` with `.git_sha`; `python3 SRC/infra/q2-zinv-reserve/run/zr_host.py plan --src SRC --name dev-rehearsal-vN --split dev --controls-run dev-controls-v9`, then `next --dry-run`, then `next` on an empty queue |
| The registered run (after the freeze) | Export the freeze commit, export `Q2ZR_PREREG_FROZEN=q2-zinv-reserve-validation-v1`, `plan --split reserve --name reserve-v1`, `next` until complete |
| Read a result | `zr_host.py status --name NAME`; `zinv/judgement.json` in the run directory |

## Gotchas
<!-- agent-docs:fill:gotchas -->

- `next` submits nothing while any job is queued (R04, S2 v4 and Successor E
  share the host); poll it, never block on it.
- The host runs Python 3.10: `guard.py` and `zr_host.py` stay standard library
  only and 3.10 compatible.
- `k2-sample` in step 3 records "not drawn" (one domain); that is expected.
