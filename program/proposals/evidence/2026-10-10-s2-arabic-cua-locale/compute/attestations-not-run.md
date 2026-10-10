# S2 v1 (s2-arabic-cua-locale-v1): compute attestations that do not exist yet

Written 2026-10-10 by the gauntlet's synthesis owner. This file is the honest
target of the bundle's `container_smoke`, `slurm_test` and
`provenance_verification` records.

- **Real model loop:** none for Relay. Relay's runner reaches models only
  through its hosted-router transport, which accepts a single hosted endpoint
  (`runner/router.mjs:131-140`). A local OpenAI-compatible transport through
  `harness/q2_stage1/bridge.py` (E1) and a qwen35vl adapter for Relay's
  action set (E2) are not written. S1a's certified loop (D53) covers the
  OSWorld VM path only.
- **Benchmark adapter:** none. Relay has no locale parameter, no i18n catalogs,
  no test ids on its interactive elements and no gate doctor
  (`scripts/run_s2_locale_gate_doctor.py` is not written). Phase 0 is the work
  that creates them.
- **Environment image:** not built. The host has no Node or Chromium image and
  no `node` binary (asset cell, read-only check). E3 builds one from Relay's
  pinned base `node:24.13.0-bookworm-slim@sha256:4660b1ca8b28d6d1906fd644abe34b2ed81d15434d26d845ef0aced307cf4b6f`.
- **Model weights:** present on the host (Qwen3.5-9B revision
  `c202236235762e1c871ad0ccb60c8ee5ba337b9a`, receipt `0a9e052d`, used by S1a).
- **Container smoke:** not run (E4).
- **Slurm dry run / test-only:** not run; no manifest exists (E5).
- **Provenance verification:** not run.
- **Executable pilot:** none. `power-gate.py` is CPU design evidence (analytic
  MDEs, a cost model and a Monte Carlo of the staged design under assumed
  distributions), not a pilot, and not an orx node.
- **Host:** one read-only `squeue` at 2026-10-10T21:42:52Z (empty). No host job
  was submitted by synthesis.

The deterministic research-direction doctor therefore reports FAIL, which is
the expected and honest state.
