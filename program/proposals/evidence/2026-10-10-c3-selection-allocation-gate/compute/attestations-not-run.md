# C3 Stage-0 gate v1: compute attestations that do not exist yet

Written 2026-10-10 by the gauntlet's synthesis owner. This file is the honest
target of the bundle's `container_smoke`, `slurm_test` and
`provenance_verification` records.

- **Real model loop:** none. The generation driver (seeded requests,
  log-probabilities, step statistics, checkpoint and resume), the answer-position
  extractor and the HF extraction job are not written.
- **Benchmark adapter:** none. The data manifest builder, the graders
  (math-verify primary, strict cross-check) and the family builder with its
  near-duplicate audit are not written.
- **Model weights:** not on the host. `cotcodec-models/qwen3-8b` holds a
  metadata receipt only (15,910,042 B, `publication_eligible: false`, asset
  cell, read-only ssh); `models/registry.yaml` says "No weight download is
  planned". A registry amendment and a CPU fetch of 16,381,516,776 B of
  safetensors at revision b968826d are prerequisites (D1); the fetch is a host
  action and waits for Q2 S1a.
- **Container smoke:** not run. The cu129 vLLM overlay served the Qwen3-8B
  architecture with dummy weights in serving-throughput-probe-v1 job B (Slurm
  446); real weights have never been loaded on this host.
- **Slurm dry run / test-only:** not run; no manifest exists. The host was
  running S1a jobs 1062 (s1a-a1-4b-s2) and 1064 (q2s1a-a1-4b-s2) when this was
  written, and D64 requires a scored, reviewed package and a freeze before any
  GPU job.
- **Provenance verification:** not run.
- **Executable pilot:** none for this gate. The simulations S1
  (`compute/gate-sim.py`) and S2 (`compute/cost-model.py`) are CPU design
  evidence, not a pilot; neither is an orx node.

The deterministic research-direction doctor therefore reports FAIL, which is
the expected and honest state.
