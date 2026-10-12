---
name: harness-q2-stage1e-skill
description: Procedure for the Q2 successor E code (q2-stage1-successor-e-v1, draft) in harness/q2_stage1e/: S1a's design with more data (113 tasks, four sessions per size, one rerun), as a thin layer over S1a's code of record.
---

# cotcodec / harness / q2_stage1e

## Purpose

`q2-stage1-successor-e-v1` (successor E, D66, D69, D80 (iii)) reruns S1a's design on all 113
eligible pool tasks with four new serving sessions per size and one episode per (size, task,
harness, session), for a decisive DR2 reading. E's estimands, rules, harnesses, engine,
prompts, action path, lane and records are S1a's (`harness/q2_stage1/`), imported unchanged.
This package holds only what E's design adds.

## Key files

- `plan.py`: the 113 tasks (S1a's eligible pool, no draw), sessions E1-E4, S1a's size order
  (9B then 4B), one seeded block per job, the job order, the session gaps (12 h 5 min), and the
  caps by arithmetic on S1a's realized cost (52 min at 9B, 48 at 4B, 406 in all). It renders
  `program/evidence/2026-10-11/q2-stage1-successor-e/plan/plan-e.json`.
- `records.py`: S1a's record schema with E's labels (session E1-E4, rerun 1); S1a's
  `validate` on every other field; the (Z, K, H, 4, 1) outcome array; DR0 per job.
- `driver.py`: the episode container's entry point, S1a's driver with E's record check.
- `lane.py`: S1a's lane with E's manifest rules (purposes `development` and `e`), the job
  order and DR0 by digest, the session gap, the engine check and E's entry point;
  `infra/slurm/host-single-node/q2e-vm.sbatch` runs it; `scripts/render_q2e_manifest.py`
  renders E's manifests and the GPU half from S1a's template.
- `analysis.py`: S1a's estimators and rules on E's array (`analyse_array`, `report`), the
  D59/D61/D62 rules built in, the D82 gold-defect sensitivity (registration section 9), the
  costs, DR0, GLMM input and the descriptive joint reading with S1a; `section15.py`: the
  descriptive items of S1a section 15.

## Invariants

- Never edit a file of S1a's code of record (`q2-stage1-rescoped-v1` section 20); the E
  prereg test checks every digest.
- E is its own sample: no E estimate, test, rule or prediction reads S1a's sessions.
- Every E job's slots come from `plan.slots`; the lane refuses anything else.
- Tests: `tests/test_q2_stage1e.py`, `tests/test_q2_stage1e_prereg.py`.
