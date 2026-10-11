# E7 G1 floor gate: compute attestations that do not exist yet (registration v2)

Written 2026-10-10 by the gauntlet's synthesis owner for v1 and updated by the
D68 repair owner for `e7-equivariant-writes-g1-v2` (wave 1's text is in git
history). This file is the honest target of the bundle's `container_smoke`,
`slurm_test` and `provenance_verification` records.

- **Real model loop:** none. The A0 model (fla GatedDeltaNet plus SWA-512
  through `flex_attention`), the four evaluation interventions (SPAN_CUT,
  RELAY_BLOCK, D1, ISO), the training loop (fp32 master weights,
  warmup-stable-decay, document-boundary resets, atomic checkpoints, SIGUSR1,
  resume), the tokenizer trainer, and the mixture, bitext (prefix-sharing and
  co-present) and curriculum builders are not written.
- **Benchmark adapter:** none. The TP-MQAR-v2-G1 builder v2 (surface filter with
  the 4-gram clause, sliding-block distractors, surface-twin decoys, B-SURF,
  manifest assertions, sealed manifests), the evaluator (eight-candidate teacher
  forcing with prefix caching, decoy queries, REACH and ISO pairs) and the
  analysis (bootstrap, classification, verdict) are not written. The repair's P1
  (`compute/repair-d68/instrument-pool-v2.py`) implements the builder's
  selection logic on CPU with character-level proxies, as evidence, not as the
  adapter.
- **Data:** not on the host. About 0.25B tokens of K1 slices exist against the
  1.04B-token pool. FineWeb, FineWeb-2 (deu, cmn, tha), ParaDocs (en-de, en-th),
  the ParaCrawl Bonus en-zh release, SCB-MT-EN-TH-2020 and NTREX-128 must be
  fetched with receipts under D1. A host action; it waits until the host is free.
- **Container smoke:** not run. The measured image
  (`cotcodec-research:0b3ecef0-architecture`) was on the host when last read; the
  G1 image is built from the harness commit.
- **Slurm dry run / test-only:** not run; no manifest exists. The repair made no
  host contact.
- **Provenance verification:** not run.
- **Executable pilot:** none for this gate. S3v2, P1, S1v2 and S2v2
  (`compute/repair-d68/`) and wave 1's S1, S2 and S3 are CPU design evidence, not
  a pilot, and none is an orx node.

The deterministic research-direction doctor therefore reports FAIL, which is
the expected and honest state.
