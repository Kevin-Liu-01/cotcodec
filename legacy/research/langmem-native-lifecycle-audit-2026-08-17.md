# LangMem native PostgreSQL lifecycle audit — 2026-08-17

## Decision

LangMem revision `29cbe41e58528f92e9efa773c12e15c47be3808c` is blocked
from an H100 actor cell. Two clean-state ARM64 Docker repetitions passed the
public hot-path tool, deterministic background-manager transport, user
isolation, logical record deletion, and PostgreSQL plus fresh-process restart
checks. The exact persistent stack has no first-class namespace purge, and all
four logically purged plaintext canaries remained recoverable from both the
PostgreSQL heap and WAL after clean shutdown.

Terminal status:
`BLOCKED_NO_FIRST_CLASS_SCOPED_PURGE_AND_POSTGRES_PLAINTEXT_RESIDUE`.

## Bound execution

- LangMem source: `29cbe41e58528f92e9efa773c12e15c47be3808c`
- Source tree: `d85d1f815fb2b54bbc0a85c18453b7a7953ca38c`
- Source archive SHA-256:
  `24c85c514c80bb263a16626971e8ef53978fd1bc7f9319e47d8a5a0bf4956521`
- LangMem package: `0.0.30`, installed from the exact source archive
- LangGraph PostgreSQL store package: `3.1.0`
- Psycopg: `3.3.4`
- PostgreSQL image:
  `postgres@sha256:ef257d85f76e48da1c64832459b59fcaba1a4dac97bf5d7450c77753542eee94`
- App image:
  `sha256:2571173b00e1774bb3d4a0ac3f8f945d6b6d044840cf6951e35d77fc0c08520f`
- Stable semantic projection:
  `96602010adaf5b90c706c9be759d4790464ccd7a2ee4eea302011ce76cbdac61`
- Repetitions: two, each with one clean PostgreSQL restart and fresh app
  process
- Runtime: private internal Docker bridge, no external network, zero GPUs

The background manager's extraction runnable was deterministic test
instrumentation. It exercised LangMem's public manager construction and native
store apply path without introducing model quality as a second estimand.
Vector indexing was disabled because semantic ranking is outside this lifecycle
contract.

## Reproduced boundary

Both repetitions established:

1. public manage/search tools created, updated, retrieved, and logically deleted
   user-scoped records;
2. the background `MemoryStoreManager` persisted its deterministic extraction;
3. hot-path and background state survived a clean database restart and a fresh
   app process;
4. user A and user B namespaces remained isolated;
5. `PostgresStore` exposed per-record delete but no callable
   `delete_namespace` surface;
6. enumerating and deleting remaining records made all tested namespaces
   logically empty; and
7. bounded, self-verifying proof windows recovered every original, updated,
   isolated, and background canary from
   `pgdata/base/16384/16390` and
   `pgdata/pg_wal/000000010000000000000001` after clean shutdown.

## Claim boundary and next gate

This is exact-source lifecycle/storage evidence. It is not evidence about
LangMem extraction quality, semantic retrieval, procedural prompt quality,
model effects, or the managed LangGraph service. The physical-residue result is
about the reproduced official local PostgreSQL path; it does not establish the
retention behavior of an externally managed database service.

Admit a newer immutable revision or explicit repair arm only after it provides
a first-class tenant-scoped purge plus physical purge or cryptographic erasure
and passes the same two-clean-state restart, isolation, logical-delete, and
post-shutdown residue doctor. Evaluate extraction and retrieval quality only in
a separate preregistered actor contract after lifecycle admission.

## Evidence

The self-contained receipt is
`research/evidence/memory/langmem-native-lifecycle-negative-v1.json`. It embeds
the experiment, exact-source and image receipts, phase logs, both repeat
reports, bounded heap/WAL proof windows, and manifest, and validates without the
ignored `data/` directory.
