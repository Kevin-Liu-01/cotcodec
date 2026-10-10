# Q2 design study (D66): simulator, fits, validation and cost model

CPU only; no host job of any kind. Code: `harness/q2_design/` (tests:
`tests/test_q2_design.py`). The frozen S1a modules (`harness/q2_stage1/`, freeze commit
`d5f5798`) are imported unchanged; `git diff d5f5798 -- harness/q2_stage1` is empty.

## Inputs (read only)

| File | Role |
|---|---|
| `../q2-stage1-analysis/a1.jsonl` | S1a's 1,808 episode records (primary set: 32 base tasks, raw verdicts) |
| `../q2-stage1-analysis/costs.json` | realized GPU-h per episode per A1 job |
| `../q2-stage1-analysis/report/report-guarded.json` | S1a's registered readings (the validation targets) |
| `../../2026-10-09/q2-stage1-prefreeze/plan/plan-a0a.json` | frozen plan: base, extension order, domains |
| `../q2-stage1-a1/a1-*-s*/vm-*/{lane-receipt.json,episodes.jsonl}` | per-job start-up, slots and drain |

Each output records the SHA-256 of the first four (`inputs`) and its provenance (commit,
interpreter, library versions, argv).

## Outputs

| File | Command (from the repository root) |
|---|---|
| `fit-base.json` | `python -m harness.q2_design.study fit --set base --out $E/fit-base.json` |
| `fit-pool.json` | `python -m harness.q2_design.study fit --set pool --out $E/fit-pool.json` (sensitivity: all 113 tasks) |
| `profile-base.json` | `python -m harness.q2_design.study profile --fit $E/fit-base.json --out $E/profile-base.json` |
| `validation-base-seed{42,43,44}.json` | `python -m harness.q2_design.study validate --fit $E/fit-base.json --seed S --nsim N --out ...` |
| `validation-base.json` | `python -m harness.q2_design.study merge-validation --out $E/validation-base.json $E/validation-base-seed*.json` |
| `recovery-{fitted,session-noise}-seed{42,43,44}.json` | `python -m harness.q2_design.study recovery --fit $E/fit-base.json --truth {fitted,session-noise} --seed S --out ...` |
| `fit-base-spikeslab.json` | `python -m harness.q2_design.study fit --set base --harness spike-slab --out $E/fit-base-spikeslab.json` (post hoc: added after the normal model's pi_small widths came out narrow in validation) |
| `validation-spikeslab-seed{42,43,44}.json`, `validation-spikeslab.json` | as above with `--fit $E/fit-base-spikeslab.json --modes parametric_realized pool_base_realized` |
| `cost-model.json` | `python -m harness.q2_design.study cost --out $E/cost-model.json` |
| `summary.json` | `python -m harness.q2_design.study summary --dir $E --out $E/summary.json` (index of the headline numbers) |
| `repro-*.json` | `python -m harness.q2_design.study compare --a <committed output> --b <re-run> [--mode M] --out ...` |

`$E` is `program/evidence/2026-10-10/q2-design-study`. Run with the project's Python
(numpy 2.5.2, scipy 1.18.0); the exact versions are in each file's `provenance`.

## Seeds

Seeds are [42, 43, 44]. The fit is deterministic (fixed grid, no random draws). Every
simulation stream is numpy PCG64 seeded `[seed, stream]`; the pool posterior bank uses 42;
the registered bootstrap uses seed 42 for every simulated data set, as S1a's report does.
The validation acceptance criteria are fixed in `study.CRITERIA` before any validation run.

## Provenance of the runs

The fits, profile, validation and recovery runs were launched from the working tree while
the package was being committed, so their `provenance` records `harness_dirty: true` and a
parent commit. Every result-bearing code path is unchanged in the commits that follow
(`34a57a8`, `b94ffe5`, `a9985ee`): `b94ffe5` adds the spike-and-slab option, which keeps
the normal model's computation and random stream, and later commits add only the
`summary` and `compare` commands. The `repro-*.json` files are re-runs launched from the
clean commit `b94ffe5` (scratch outputs, not committed), compared field by field with the
committed outputs, ignoring run metadata and fields that later code added (`w_b = 1`,
`harness`). A re-run whose output was written after `study.py` was edited for `compare`
records `harness_dirty: true` although it loaded `b94ffe5`.
