# E3 Stage-0 probe v1: compute attestations that do not exist yet

Written 2026-10-10 by the gauntlet's synthesis owner. This file is the honest
target of the bundle's `container_smoke`, `slurm_test` and
`provenance_verification` records.

- **Real model loop:** none. The H-Net boundary-extraction driver (weights-only
  load, per-stage probabilities, byte-gap mapping, atomic per-file outputs with
  hash-verified resume) and the aligner driver are not written.
- **Benchmark adapter:** none. The FLORES+ manifest builder, the canonicalizer,
  the consistent-cut builder and the projected-boundary-Dice scorer exist only
  as simulation code in `compute/instrument_sim.py`, not in `harness/` with unit
  tests.
- **Image:** no overlay with hnet (3673fe12), mamba-ssm, causal-conv1d and
  flash-attn exists; `uv.lock` has none of them. The build is a host CPU job.
- **Model weights:** the three H-Net checkpoints are not on the host and declare
  no licence (reserved sign-off R4).
- **Data:** FLORES+ is gated; accepting it and providing a read token are
  Kevin's actions (R2). Nothing has been fetched.
- **Container smoke:** not run.
- **Slurm dry run / test-only:** not run; no manifest exists. The host queue
  was empty at 21:22 UTC on 2026-10-10, but the program requires a scored,
  reviewed package and a freeze before any GPU job.
- **Provenance verification:** not run.
- **Executable pilot:** none for this probe. S1 and S2 are CPU design evidence,
  not a pilot; neither is an orx node.

The deterministic research-direction doctor therefore reports FAIL, which is
the expected and honest state.

## Update for `e3-byte-boundary-headroom-v2` (D68 repair, 2026-10-10)

Nothing above has changed state. The repair added only CPU design evidence on
the development Mac (`compute/repair-run2/`) and made no host contact (no ssh, no
host job). Specifically still absent:

- **Overlay image:** the v2 stack (torch 2.7.1+cu128, flash-attn 2.8.0.post2
  wheel for torch 2.7, mamba_ssm a6a1dae and causal_conv1d e940ead from source,
  transformers 4.57.1, hnet 3673fe12, the aligners and spaCy) is specified and
  checked statically against the pinned files; it has not been built.
- **Real model loop and adapter:** the encoder-only extraction driver, the aligner
  drivers (OmniAlign, BinaryAlign), the spaCy segmentation and parse step and the
  harness port of `e3_estimator_v2.py` are not written.
- **Gold data:** XL-WA en-zh has not been requested (R5, an outward action).
- **Container smoke, Slurm dry run, provenance verification, executable pilot:**
  none. S1v2 and S2v2 are CPU design evidence, not a pilot.
