# S2 (s2-arabic-cua-locale-v2): compute attestations that do not exist yet

Rewritten 2026-10-11 by the single owner of the D68 repair (wave 1's version described the
Relay design and is in git history). This file is the honest target of the bundle's
`container_smoke`, `slurm_test` and `provenance_verification` records.

- **Real model loop:** exists for the stack, not for S2. S1a ran Qwen3.5-9B through the two
  certified harnesses on the L0-fixed lane (1,808 episodes, 0 infrastructure losses; D53, D66).
  No S2 episode has run: the cell selector, the step-0 check and the keyboard check are not
  written, and the derived localized image does not exist.
- **Benchmark adapter:** OSWorld at `b138d348` as S1a ran it (task configs, setup and
  checkers). S2 adds no adapter; it adds the derived image and the selector (Phase 0).
- **Environment image:** the certified OSWorld image exists on the host; the derived image
  (Arabic language packs, fonts, pseudo-locale catalogs with FSI/PDI isolation, share-layer
  configuration, launcher selector) is not built. Building it needs host CPU lane jobs, which
  this gauntlet run may not submit.
- **Delta certification of the action path (P0.6):** not run.
- **Render oracle:** code written (`compute/repair-d68/render-oracle/oracle.py`) and validated
  on Chromium fixtures with known properties (`oracle-validation.json`: 7 of 7 variants as
  expected); not run on the real applications in the lane.
- **Model weights:** present on the host (revision `c202236235762e1c871ad0ccb60c8ee5ba337b9a`,
  receipt `0a9e052d`, used by S1a).
- **Container smoke:** not run for S2.
- **Slurm dry run / test-only:** not run; no Phase 1 manifest exists.
- **Provenance verification:** not run.
- **Executable pilot:** none. `power-osworld.py` is CPU design evidence (a fitted propensity
  model on S1a's records and a simulation of the registered estimator), not a pilot, and not
  an orx node.
- **Host:** the repair made no host contact of any kind.

The deterministic research-direction doctor therefore reports FAIL for Compute, which is the
expected and honest state.
