# E5 first step v1: compute attestations that do not exist yet

Written 2026-10-10 by the gauntlet's synthesis owner. This file is the honest
target of the bundle's `container_smoke`, `slurm_test` and
`provenance_verification` records.

- **Real model loop:** none. The harness (fla 0.5.2 model loop, decay-clamp,
  r = 2 and write-silencing hooks, forced-choice scoring from the cached
  recurrent state, greedy decode, BPB, gate ledger, checkpoint and resume) is
  not written.
- **Benchmark adapter:** none. The episode builder (WikiText-103 passages,
  normalizer, key lists, codes, templates) is not written; the splitting rules
  exist only as the CPU prototype `compute/resegment.py`, run on CC0 arXiv
  abstracts as stand-in text.
- **Model weights.** Subject R (`rwkv7-1.5b-world`) is cached on the host with
  a receipt (asset cell, read-only ssh). Subject G
  (`m-a-p/1.3B-100B-GatedDeltaNet-pure` at 930ed6ae) is not on the host, not in
  `models/registry.yaml`, and has no licence; its fetch (5,865,376,000 B) waits
  for Kevin's ruling (registration decision 1) and for no S1a job to be running.
- **Container smoke:** not run. Neither checkpoint has been loaded in image
  `cotcodec-research:ed5d5a93-architecture` on this host.
- **Slurm dry run / test-only:** not run; no manifest exists. The host queue was
  empty at 21:41 UTC on 2026-10-10 (read-only squeue); the host rule allows only
  the open-weight reviewer's lane job during this gauntlet.
- **Provenance verification:** not run.
- **Executable pilot:** none for this step. S1 (`compute/mech-sim.py`), S2
  (`compute/power-sim.py`), S3 (`compute/cost-model.py`) and S4
  (`compute/resegment.py`) are CPU design evidence, not a pilot; none is an orx
  node. The legacy phase-0 doctor passes 17/17 synthetic cases from `legacy/`
  on main d45b4a4 (asset cell; receipt in the session scratchpad, not in the
  repository), but it tests the legacy contract, not this step.

The deterministic research-direction doctor therefore reports FAIL, which is
the expected and honest state.
