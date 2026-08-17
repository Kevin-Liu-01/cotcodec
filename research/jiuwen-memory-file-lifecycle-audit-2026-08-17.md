# JiuwenMemory file-backend lifecycle audit — 2026-08-17

## Decision

JiuwenMemory revision `600432b55e480bec5948ee40089884ccf15a7c5d` is not
admitted to an H100 actor comparison. Its exact-source `FileMemoryIndex` uses a
global `mem_id` primary key, so the same ID in two tenant scopes leaves only one
tenant in the searchable SQLite index while both tenant-specific Markdown copies
remain readable through filesystem fallback. Migration traversal can change which
tenant owns that single index row, and the migration schema version resets to zero
in a fresh process and replays.

This is a discovery negative, not a memory-quality result. Extraction, dreaming,
the independent graph subsystem, semantic retrieval quality, and model effects
were not tested.

## Bound source and runtime

- Repository: `https://github.com/openJiuwen-ai/agent-memory`
- Revision: `600432b55e480bec5948ee40089884ccf15a7c5d`
- Tree: `1b6518ba4f0d89d99cb7febd3e3d7a27b2e8347c`
- Git-archive SHA-256: `38c6868fe7a707d1912c0b10a64a5661571b0ed6e341464fea65463d83842c3e`
- License: Apache-2.0; license SHA-256
  `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30`
- Committed `uv.lock` SHA-256:
  `e2a62926d1fd01ad9ecf4a8b305791146bace9ddac5ed941a95490ab66a85d0c`
- Runtime: Linux ARM64, network disabled, read-only root, all capabilities
  dropped, `no-new-privileges`, non-root `65532:65532`, zero provider/model
  calls, zero GPUs.
- Shared image ID:
  `sha256:c5ca75c1f299fde9efc0097d941d9e2c12973649aa8b91c6ecc76f00e2d54eae`
- Minimal disclosed runtime overlay: `gmssl==3.2.2`,
  `pycryptodomex==3.23.0`, and `sqlite-vec==0.1.9`.

The committed lock is not self-consistent: `uv lock --check` requires an update,
the declared `file-index` extra is absent from the lock metadata, and a frozen
base install cannot import the package because `gmssl` is missing. The source
tree and committed lock were not modified.

## Protocol

Each of two clean state volumes received unique-ID positive controls and the same
duplicate ID under `user-a/scope-a` and `user-b/scope-b`. The exact native add,
list, get, migration, restart, user-scope delete, and SQLite paths were exercised.
The two repetitions fixed `PYTHONHASHSEED` to `1` and `7`, respectively, to make
the unordered scope traversal falsifiable rather than relying on ambient process
randomness. A deterministic local embedding stub prevented model calls.

## Results

| Invariant | Result |
|---|---|
| Unique IDs remain visible and isolated | PASS |
| Duplicate ID remains independently indexed by both tenants | FAIL |
| Both tenant Markdown copies remain tenant-readable | PASS |
| Indexed duplicate owner is invariant to process hash order | FAIL |
| Migration version survives a fresh process | FAIL |
| Migration re-executes after the restart reset | REPRODUCED |
| Native scoped deletion is logically effective | PASS |
| Deleted Markdown files remain | NO |
| Deleted plaintext remains in contained Linux live files | NO |
| Committed lock is self-consistent and importable | FAIL |

Before migration, the second duplicate insert overwrote the first tenant's
`chunks` row because `mem_id` is the table's sole primary key and the upsert
updates `path`, `user_id`, and `scope_id`. Both Markdown files persisted, so
`get_by_id` could still recover the hidden tenant through a scoped filesystem
scan while `list_memories` omitted it.

Under hash seed `1`, migration left `user-a` as the indexed duplicate owner;
under seed `7`, it left `user-b`. In both cases exactly one tenant was indexed and
both tenant Markdown copies survived. A fresh `FileMemoryIndex` then reported
schema version zero, and the same version-1 migration performed database changes
again. The two runs had the same Boolean semantic projection SHA-256
`a9c6e7fdf059275048ec911961956ff707e554b247cfa6ffc68a0a277c402aac`.

SQLite reported `PRAGMA secure_delete=1` in both contained Linux runs. After both
scopes were deleted and the connection closed, the bounded canary scan found zero
plaintext proof windows. This positive Linux result is retained explicitly and is
not generalized into a cross-platform erasure claim. An earlier unsealed macOS
exploratory probe reported `secure_delete=0`; it is context only, not part of the
sealed admission finding.

## Auxiliary upstream suite

After disclosing the missing runtime packages, the pinned source collected 1,376
tests and completed with 1,327 passed and 49 skipped in 5.21 seconds. The ignored
JUnit receipt has SHA-256
`9bc3ed97b192e418c7662dd73faf6979f8f7d57d3e146f055b1116c24a4e0bfe`.
This auxiliary suite does not cover the duplicate-ID tenant collision or durable
migration metadata and is not a substitute for the sealed lifecycle doctor.

## Evidence and next gate

- Experiment: `experiments/memory/stage3-jiuwen-memory-file-lifecycle-doctor.yaml`
- Self-contained evidence:
  `research/evidence/memory/jiuwen-memory-file-lifecycle-negative-v1.json`
- Evidence SHA-256:
  `7e1d06c90f965678ca6395c5b36e7a5c15c4699727b0df4482750237cfe95858`
- Report SHA-256:
  `786faf81f28fb7173b583ba10b7b4a0888757ce6c94c5f908ebbb9270430f762`
- Manifest SHA-256:
  `878abd44c1a9caaae74524cf6f1ec84ca8ae3b095f1eea5a26d91a4064588b17`

Admit only a newer immutable revision or an explicit repair arm with a
tenant-composite index key, durable migration metadata, a self-consistent lock,
and a cross-platform physical-purge or cryptographic-erasure contract. Repeat the
same fixed-seed, two-clean-state doctor before evaluating extraction, dreaming,
graph behavior, retrieval quality, or an H100 actor.
