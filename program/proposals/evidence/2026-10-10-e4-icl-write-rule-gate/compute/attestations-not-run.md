# E4 gate v1: compute attestations that do not exist yet

Written 2026-10-10 by the gauntlet's synthesis owner. This file is the honest
target of the bundle's `container_smoke`, `slurm_test` and
`provenance_verification` records.

- **Real model loop:** none. `harness/e4_gate.py` (four-site affine read path,
  state classes, planted recovery, non-vacuity check) is not written.
- **Benchmark adapter:** none. The family generators and the manifest builder
  are not written.
- **Container smoke:** not run. The pinned image
  `127.0.0.1:5000/cotcodec-research@sha256:13a9de831cff50461d8ecee3c2794f0c6d6bcffe9d602968fe2ee06e5a1096e9`
  has no flash-attn, and fla 0.5.2's `Attention` raises ImportError without it
  (asset-cost cell, read from the host uv cache, `uv.lock` and the
  Dockerfile; not run). The registration loads the teacher through a Llama
  weight remap with SDPA, cross-checked against fla with an SDPA shim; neither
  path exists yet.
- **Slurm dry run / test-only:** not run; no manifest exists. The host is
  reserved for Q2 S1a until its session 2 has ended, and D58 requires a scored,
  reviewed package and a freeze before any GPU job.
- **Provenance verification:** not run.
- **Executable pilot:** none for this gate. The legacy D19 phase-0 CPU doctor
  (orx run `e20eeccb-8c51-42de-891b-007e52282bf4`, PHASE0_DOCTOR_PASS) tests a
  synthetic regime and none of the gate's quantities; it is not counted.

The deterministic research-direction doctor therefore reports FAIL, which is
the expected and honest state.

D60 repair (2026-10-10): still none. The repair ran only CPU simulations and
the tokenizer-based family table on the development Mac; no harness, adapter,
manifest, container smoke, Slurm dry run or provenance verification exists for
`e4-icl-write-rule-gate-v2`, and no host job may run while a Q2 S1a job is
running or pending.
