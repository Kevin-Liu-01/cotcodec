# OpenResearch run ledger — frontier gauntlet directions 19–22

Project `595ba408-91e5-44d0-a7f2-0b7ebf565191` (`cotcodec`, baseline `main`). Fixed run command: `uv run --locked python scripts/orx_run.py`. Each node is a root (`--baseline`) because the four doctors answer four different questions; children will descend from whichever node a later wave repairs. Runs execute an immutable snapshot of the recorded commit on the `local` backend; the run log is the evidence channel (`orx logs <runId>`). Portable bundle with receipt and log hashes: `research/evidence/infrastructure/orx-phase0-doctor-runs-2026-09-14.json`.

| direction | experiment id | node commit | run id | exit | doctor status | note |
|---|---|---|---|---:|---|---|
| `semantic-clock-gate-parity` | `41f5d3b0-1424-43ec-9303-6983c31fc790` | `caf9d9f46790` | `0c4bb3f1-1f47-4ba2-b016-a8d61b5865e9` | 0 | `PHASE0_OBJECT_DOCTOR_PASS` | 17 registered cases; exit 0; 1m20s |
| `translation-supervised-sparse-indexer` | `9a0f98a2-d44c-42e6-bb81-c698a3453911` | `011237acf800` | `c4e6988a-e59b-4ca9-9c49-9ccae5fecb66` | 0 | `PHASE0_DOCTOR_PASS` | 10 registered cases all PASS; exit 0; 2m05s |
| `translation-equivariant-state-writes` | `1bcd752d-02a1-451d-a997-8e765912165b` | `bb1eacd7ea93` | `bc04fb03-da40-4ec3-a56f-15f419bfdda4` | 0 | `PHASE0_OBJECT_DOCTOR_PASS` | 11/11 cases; exit 0; 1m10s |
| `icl-rule-distillation-port` | `c8ef9a1e-211b-4ccb-9a65-0dbbdd47ca7a` | `bc05cc496bcf` | `e20eeccb-8c51-42de-891b-007e52282bf4` | 0 | `PHASE0_DOCTOR_PASS` | 8 registered cases all PASS; 33.6 s doctor; exit 0; 1m40s |

All four nodes have **answered** (2026-09-14) and are frozen. Outcome semantics: exit 0 with the doctor's own status line means the phase-0 doctor is executable and its registered synthetic cases hold; it proves nothing about any model, corpus, or GPU number.

Known defect in these runs' logs: the dispatcher's `ORX_RECEIPT_SUMMARY` line counted only `passed: true` cases, so three doctors that report per-case `status: PASS` show `passed: 0`. The doctors' own status lines in the same logs are authoritative. Fixed on `main` after these runs (`scripts/orx_run.py`, `case_passed`); child nodes must merge `main` into their branch to inherit it — frozen roots are never edited.

Next node kind: `slurm-manifest` for the `qwen3.5-4b-base` phase-0 screens (directions 20 and 22), launched with `--backend ssh --host kevin@207.241.191.91` once the compiled discovery manifest exists.
