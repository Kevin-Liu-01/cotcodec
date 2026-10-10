# E7 G1 floor gate v1: compute attestations that do not exist yet

Written 2026-10-10 by the gauntlet's synthesis owner. This file is the honest
target of the bundle's `container_smoke`, `slurm_test` and
`provenance_verification` records.

- **Real model loop:** none. The A0 model (fla GatedDeltaNet plus SWA-512
  through `flex_attention`), the training loop (fp32 master weights,
  warmup-stable-decay, document-boundary resets, atomic checkpoints, SIGUSR1,
  resume), the tokenizer trainer, and the mixture, bitext and curriculum
  builders are not written.
- **Benchmark adapter:** none. The TP-MQAR-v2-G1 builder (surface filter,
  bins, sealed manifests), the evaluator (eight-candidate teacher forcing with
  prefix caching, state cut, fact-write ablation) and the analysis
  (bootstrap, classification, verdict) are not written.
- **Data:** not on the host. About 0.25B tokens of K1 slices exist against
  the 1.04B-token pool. FineWeb, FineWeb-2 (deu, cmn, tha), ParaDocs (en-de,
  en-th), the ParaCrawl Bonus en-zh release, SCB-MT-EN-TH-2020 and NTREX-128
  must be fetched with receipts under D1. This is a host action and waits
  until no S1a VM or GPU job is running.
- **Container smoke:** not run. The measured image
  (`cotcodec-research:0b3ecef0-architecture`) is still on the host; the G1
  image is built from the harness commit.
- **Slurm dry run / test-only:** not run; no manifest exists. The host queue
  was empty at 21:25 UTC on 2026-10-10 (read-only `squeue`).
- **Provenance verification:** not run.
- **Executable pilot:** none for this gate. S1 (`compute/gate-sim.py`), S2
  (`compute/cost-model.py`) and S3 (`compute/reach-doctor.py`) are CPU design
  evidence, not a pilot, and none is an orx node. The legacy phase-0 object
  doctor's rerun on main (`compute/legacy-phase0-doctor-main.json`, asset
  cell) tests synthetic W, D and P objects, not anything G1 depends on.

The deterministic research-direction doctor therefore reports FAIL, which is
the expected and honest state.
