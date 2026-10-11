# R01 first step: compute attestations that do not exist yet

Written 2026-10-11 by the gauntlet's single owner. The deterministic doctor
(`scripts/research_direction_doctor.py`) requires a real model loop, a non-stub benchmark
adapter, a hashed Slurm manifest, a container smoke run, a Slurm test-only run and a provenance
verification. None exists for R01's Stage B or for the CPU-lane Stages A1 and C:

| Attestation | State | What is needed |
|---|---|---|
| Stage A1 capture mode | not built | a driver mode that boots, sets up, settles and captures four frames per boot under the default and blink-off conditions, writing PNGs and processed bytes to the host run root and SHA-256 lists to the repository |
| Stage C open-loop replay mode | not built | a driver mode that executes S1a's recorded IR through the certified executor with two frames per step, sleeping the recorded latency, then evaluates and captures as S1a |
| Request rebuilder | not built | a stub-engine run of the frozen H-OSW-fixed client that rebuilds step requests from replay frames and S1a's recorded replies, with the prompt-id fidelity check |
| Stage B replay client | not built | a standard-library client for stored request bodies with the arm protocols (E-det, E-c1, E-s1a, E-nc; cache resets; seeded streams) |
| Manifests | not rendered | `experiments/manifests/r01/` for P0, P0', J1, J1o, J2, J3, J4 and the CPU-lane jobs |
| Container smoke, Slurm dry run, test-only, provenance | not run | after the manifests, before a freeze |

What does exist and is executable:

- Stage A0: `scripts/run_r01_stage_a0_doctor.py` as orx cpu-doctor node `ff110047` (branch
  `orx/r01-stage-a0-records-census`, commit `ca3cdbf`), run
  `83ee815a-426a-4b94-a93f-cc1277972d76`, `ORX_RESULT kind=cpu-doctor
  direction=r01-rerun-noise-sources exit=0` (log in `pilot/`); its receipt is byte-identical to
  `program/evidence/2026-10-11/r01-stage-a0/census.json` (SHA-256 `5568bc7f...`).
- The engine image, model receipt, VM image and metric image S1a used are present on the host
  (asset cell, 2026-10-11, read-only).

No host job was submitted by this gauntlet's synthesis. The only host job the gauntlet may run
is the open-weight reviewer's lane job.
