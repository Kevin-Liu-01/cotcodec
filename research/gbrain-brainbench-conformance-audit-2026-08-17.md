# GBrain BrainBench conformance audit — 2026-08-17

Status: `GBRAIN_BRAINBENCH_CONFORMANCE_PASS_PULL_COMPARISON_MISSING`

This is an exact-source deterministic conformance reproduction. It is not a
matched push-versus-pull experiment, live-agent result, memory-quality result,
or publication result.

## Bound inputs

- GBrain revision `d941e9f918236c33e10e42d8a4223f36789b02c9`
- Tree `4d7960cc1d88c40e0642204dfb144fd988c02208`
- Git archive SHA-256 `d83320b8a155f26d3b707e23fae5ba6f4245cc6c284766b382ba011521b82698`
- MIT license SHA-256 `e56fbb5b3d95756f3fa1cfefa24732ec79f18ece1ad08a4e79e00df57e8b198c`
- `package.json` SHA-256 `30a1e103ae53c41be2713a08b6589d69fd8e86f826d1911468baa300aa5aa2f0`
- `bun.lock` SHA-256 `398e282d37f78c4e40a8be050b7c9e8858c35875310f39ec30a74fd8d557f9c2`
- Official Bun 1.3.13 Darwin ARM64 archive SHA-256
  `5467e3f65dba526b9fea98f0cce04efafc0c63e169733ec27b876a3ad32da190`
- Bun binary SHA-256 `fc0b4cae13a911098f0c61d13b7d9fd6b640bdb9f6b6a0b78bdb9d778c12bc3f`
- BrainBench corpus ledger SHA-256
  `79cca16cbafc52c81fbf6f1d4b07a921540f034cc4feb3fb7b859480f37b92b5`
- Committed baseline SHA-256 `6566285f6a3f66b87db5b046ed2f8f14fbf806162b65db7e38d3d979f5f9774c`

Dependencies were installed from the exact frozen lock with lifecycle scripts
disabled. The root postinstall targets a machine-global GBrain store and is not
part of BrainBench; allowing it would have expanded the audit's mutation scope.

## Reproduced conformance

- The focused upstream suite passed 146 tests and 725 assertions across 12
  source files under the pinned Bun runtime.
- Two independent BrainBench commands completed with `pass` / `same-hash`, no
  breaches, no notes, and no seed failures.
- The gate executed 106 generated fixtures and emitted 786 turn rows. The
  semantic projection was identical after excluding invocation receipts and
  local per-turn latency.
- Semantic projection SHA-256:
  `8e4ebad237c774eaeed37ee40c4b4b8a2a6a9fa9511485257655cd2f6dc1ab27`.
- Every row reported zero cross-source slug injection.

The reproduced cells were:

| Seam | Suite | Gold failed / total | Key metric |
|---|---:|---:|---:|
| OpenClaw production | know-to-ask | 9 / 146 | failure rate 0.15; false-fire 0 |
| OpenClaw production | push | 18 / 94 | precision 1; recall 0.8085 |
| OpenClaw production | write-back | 0 / 58 | fidelity 1; provenance 1 |
| OpenClaw production | continuity | 0 / 12 | continuity 1 |
| Claude Code contract | know-to-ask | 11 / 146 | failure rate 0.15; false-fire 0.0233 |
| Claude Code contract | push | 32 / 94 | precision 1; recall 0.6596 |
| Codex contract | know-to-ask | 9 / 146 | failure rate 0.15; false-fire 0 |
| Codex contract | push | 52 / 94 | precision 1; recall 0.4468 |

Both contract seams also passed write-back and continuity. Those rows exercise
GBrain-owned adapters; they do not establish third-party production behavior.

## Unresolved validity boundaries

- Only OpenClaw exercises a shipped production injection seam.
- The committed comparison is a same-fixture-hash regression gate against an
  upstream baseline, not an independent control.
- BrainBench contains no matched pull-retrieval arm. It therefore cannot answer
  the registered question of pull retrieval versus hook injection at equal
  actor, bytes, calls, and derived-index cost.
- The corpus is template-generated from fictional entities, and gate mode
  excludes the holdout fixtures.
- No live model, embedding provider, LLM extraction, answer quality, external
  benchmark, or H100 actor cell was run.
- External network was not hard-disabled for the whole setup session; provider
  credentials were unset and the retained benchmark runs made zero model or
  provider API calls.

## Decision

Record the result as `local-conformance-reproduced` and remove this revision
from H100 execution order. Do not call the result a push-injection advantage or
a memory-quality reproduction. The next admission gate is a preregistered
matched pull-retrieval versus production OpenClaw hook-injection cell with one
frozen Markdown/Git authority, identical actor, equal injected bytes, equal
tool/model calls, complete derived-index cost, and explicit holdout separation.

The self-contained receipt is
`research/evidence/memory/gbrain-brainbench-conformance-v1.json`, SHA-256
`4c6f6d5fb8524826054a324c44f100f00177b6d22cca472e8c3b5539852f87b4`.
