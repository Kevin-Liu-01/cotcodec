# OpenResearch run ledger — frontier gauntlet directions 19–22

Project `595ba408-91e5-44d0-a7f2-0b7ebf565191` (`cotcodec`, baseline `main`). Fixed run command: `uv run --locked python scripts/orx_run.py`. Each node is a root (`--baseline`) because the four doctors answer four different questions; children will descend from whichever node a later wave repairs. Runs execute an immutable snapshot of the recorded commit on the `local` backend; the run log is the evidence channel (`orx logs <runId>`).

| direction | experiment id | branch | node commit | run id | backend | outcome |
|---|---|---|---|---|---|---|
| `semantic-clock-gate-parity` | `41f5d3b0-1424-43ec-9303-6983c31fc790` | `orx/d20-semantic-clock-gate-parity-phase-0-cpu-docto` | `caf9d9f46790` | `0c4bb3f1-1f47-4ba2-b016-a8d61b5865e9` | local | in flight (2026-09-14) |
| `translation-supervised-sparse-indexer` | `9a0f98a2-d44c-42e6-bb81-c698a3453911` | `orx/d21-translation-supervised-sparse-indexer-phase` | `011237acf800` | `c4e6988a-e59b-4ca9-9c49-9ccae5fecb66` | local | in flight (2026-09-14) |
| `translation-equivariant-state-writes` | `1bcd752d-02a1-451d-a997-8e765912165b` | `orx/d22-translation-equivariant-state-writes-phase-0` | `bb1eacd7ea93` | `bc04fb03-da40-4ec3-a56f-15f419bfdda4` | local | in flight (2026-09-14) |
| `icl-rule-distillation-port` | `c8ef9a1e-211b-4ccb-9a65-0dbbdd47ca7a` | `orx/d19-icl-rule-distillation-port-phase-0-cpu-docto` | `bc05cc496bcf` | `e20eeccb-8c51-42de-891b-007e52282bf4` | local | in flight (2026-09-14) |

Outcome semantics: `ORX_RESULT … exit=0` with an `ORX_RECEIPT_SUMMARY` whose gates all pass means the phase-0 doctor is executable and its registered synthetic cases hold; it proves nothing about any model, corpus, or GPU number (see each proposal's "what the doctor does not prove").
