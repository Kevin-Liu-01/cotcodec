# Hermes Hindsight native lifecycle audit — 2026-08-14

## Verdict

The exact bundled Hermes Hindsight provider works for retain, recall,
auto-prefetch, and session-end auto-retain against Hindsight 0.9.0. Native
state survives full backend and PostgreSQL restarts, logical banks isolate two
tenants, and administrative bank deletion remains logically absent after a
second restart.

The pin is nevertheless blocked from H100 quality work. Hermes exposes retain,
recall, and reflect tools but no Hindsight purge tool. After administrative
bank deletion and a fresh full-stack restart, both independent runs found each
deleted random plaintext canary in four PostgreSQL heap files and one WAL
segment. Logical deletion is not physical erasure.

## Frozen identities

- Hindsight: `vectorize-io/hindsight@5781d28d8fcc717a15818330b12250b311957000`,
  tree `a33e9ea9a13c83f70925bf657aac3e36ea837475`, MIT.
- Hermes: `NousResearch/hermes-agent@a90d5369f76c87c98547d2e283aa26d5cfabf322`,
  tree `963eb136bfb21fd0b296a40529cbb3575c610874`, MIT.
- Backend image: `sha256:91ddf1da2ac339c4b44f2a837c1536965a3cf41f2fe7b332416b65e29b4b424e`.
- Hermes adapter image: `sha256:0ae493490c0539a08343eec995865fdb0651562896f58cfd8fc0ae720b6d9c06`.
- PostgreSQL/pgvector image: `sha256:78bf48b801e792f99e3ac62b5036fd3876e9be48afda16c1e331af1c75ceb2ff`.
- Deterministic embedding stub image: `sha256:6136cd68a7bed538b224756278fb15344e79e2c19b9640d9b942e41170ade440`.

Hermes' plugin manifest permits `hindsight-client>=0.6.1`, while the executable
lazy-dependency allowlist pins `hindsight-client==0.6.1`. The doctor follows
that exact Hermes pin against the Hindsight 0.9.0 service. The result must not
be relabeled as a current-client comparison.

## Method

Each run used fresh PostgreSQL storage with data-page checksums and a
Docker-internal network. Every container had a read-only root filesystem, all
Linux capabilities dropped, `no-new-privileges`, no external API access, and
zero GPUs. A deterministic 16-dimensional token-hash embedding service removed
model variance; no LLM was called.

The registered operation sequence was:

1. tenant A tool retain;
2. tenant A automatic prompt prefetch;
3. tenant B cannot see tenant A;
4. tenant B session-end auto-retain;
5. tenant B retrieves its own memory;
6. tenant A cannot see tenant B;
7. full database/backend restart, then tenant A recall;
8. tenant B recall after that restart;
9. administrative deletion of tenant A's bank;
10. administrative deletion of tenant B's bank;
11. second full restart, then tenant A remains logically absent;
12. tenant B remains logically absent.

All 12 operations passed in both runs. The doctor then scanned every retained
PostgreSQL file and recorded path, byte offset, base64 proof window, and window
SHA-256 for every plaintext hit.

## Reproduced result

| Run | Operations | Retained files | Retained bytes | Residue per canary |
| --- | ---: | ---: | ---: | --- |
| 1 | 12/12 PASS | 1,433 | 67,717,047 | 4 heap files + 1 WAL segment |
| 2 | 12/12 PASS | 1,433 | 67,717,047 | 4 heap files + 1 WAL segment |

The runs used different random canaries and produced different report hashes,
but shared the same immutable images, operation sequence, and failure shape.
The sealed evidence is
`research/evidence/memory/hermes-hindsight-lifecycle-v1.json`, SHA-256
`68176f77d759be15497203dac3d7e449c609c76507e5d8242af88a2a62064c1b`.
Its validator decodes every proof window, requires the canary bytes, verifies
the report/manifest bindings, and rejects a modified proof.

## Scope and next gate

This is local negative lifecycle evidence. It does not measure memory quality,
reflection, graph retrieval, mental models, agent success, or publication
performance. The exact pin may enter no H100 quality wave until a newer pin or
an explicit repair arm exposes a first-class scoped purge and demonstrates
native physical purge or cryptographic erasure with zero plaintext residue
after a fresh full-stack restart.
