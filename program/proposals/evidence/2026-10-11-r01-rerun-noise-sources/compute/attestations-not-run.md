# R01 first step: compute attestations that do not exist yet

Updated 2026-10-11 by the gauntlet's single owner for the D75 repair (registration v2). The
deterministic doctor (`scripts/research_direction_doctor.py`) requires a real model loop, a
non-stub benchmark adapter, a hashed Slurm manifest, a container smoke run, a Slurm test-only run
and a provenance verification. None exists for R01's Stage B or for the CPU-lane Stages A1 and C.

| Item | State after the D75 repair | What is still needed |
|---|---|---|
| Stage A1 capture mode | built and CPU-tested: `harness/r01/openloop.py` mode `a1` (frames at offsets, late frame, one open-loop step, blink-off with read-back) against S1a's fake guest (`tests/test_r01_openloop.py`) | an R01 lane adapter (S1a's lane hard-codes S1a's runner module, experiment id and ledger row); a first run in the lane |
| Stage C open-loop replay mode | built and CPU-tested: `openloop.py` mode `stage-c` (recorded IR, f0 and f1 per step, recorded latency spacing, S1a's checker path) | the same adapter; a first run |
| Request rebuilder | built and CPU-tested: `harness/r01/requests.py` (bodies equal the frozen client's; composites; fidelity rule) | the corpus builder CLI over A1's frames and S1a's step-1 replies |
| Stage B replay client | built and CPU-tested: `harness/r01/replay.py` (batch-1, cold/warm, loaded protocols; resets; atomic passes; resume) against `harness/r01/fake_engine.py` | a container smoke over the bridge socket on the real engine |
| P0 self-test and timing gate | built and CPU-tested: `harness/r01/p0.py` | P0 on the real engine (after Kevin's admission) |
| Stage B report | the estimator and the two-stage model are built and tested (`estimators.py`, `stepkick.py`) | the report CLI over the results files |
| Manifests | not rendered | `experiments/manifests/r01/` for P0, P0', J1, J1b, J2, J3, J4 and the lane jobs |
| Container smoke, Slurm dry run, test-only, provenance | not run | after the manifests, before a freeze |

What exists and is executable:

- Stage A0: `scripts/run_r01_stage_a0_doctor.py` as orx cpu-doctor node `ff110047` (branch
  `orx/r01-stage-a0-records-census`, commit `ca3cdbf`), run
  `83ee815a-426a-4b94-a93f-cc1277972d76`, `ORX_RESULT kind=cpu-doctor
  direction=r01-rerun-noise-sources exit=0` (log in `pilot/`); receipt byte-identical to
  `program/evidence/2026-10-11/r01-stage-a0/census.json` (SHA-256 `5568bc7f...`).
- The R01 tests (`tests/test_r01_*.py`), run on the Mac; output in `repair-d75/pytest-r01.txt`.
- The engine image, model receipt, VM image and metric image S1a used are present on the host
  (wave 1's asset cell, read-only).

No host job was submitted by this repair. The only host job the gauntlet may run is the
open-weight reviewer's lane job.
