# Mnemosyne Cognitive lifecycle admission audit — 2026-08-16

## Verdict

The exact Mnemosyne Cognitive Memory OS revision
`5506aae7cec9ada5523099fd5ab858a4eee593b6` is **killed before H100** as an
active/inactive-memory or physical-forgetting candidate.

Two clean, contained Docker repeats reproduced the same initial and fresh-process
restart projections. The public consolidation path mutates state during dry-run,
repeatedly halves the same stale record on subsequent calls, and leaves the
supposedly demoted record in normal serving search. The public forget path hides a
record logically but leaves its exact plaintext and tombstone in Qdrant after a
fresh database process. No native session-scoped purge operation is exposed.

This is a local negative lifecycle result. It is not a memory-quality result, a
graph-quality result, or a reproduction of the repository's performance claims.

## Immutable source and runtime

- Repository: `https://github.com/28naem-del/mnemosyne`
- Git commit: `5506aae7cec9ada5523099fd5ab858a4eee593b6`
- Git tree: `d5cb986483135f016d731d73baad95f2326d84bb`
- License: MIT; license SHA-256
  `97c063041231883a482d84fe93a1ffce5183bed6ffd17bef32e40a27aeb83e08`
- Package lock SHA-256:
  `791028b9eb8b0c918157436a41f1d4f7d675920ec39018e2b9b7364025d887b9`
- Deterministic source archive SHA-256:
  `278cd0fe963854df21847fcaf6b7a650c7ad00f584a551bf48b71e6eb44e2d2e`
- Doctor image ID:
  `sha256:b64c3e21d431440cadd289e72eea3a2d63bb9bb38da95bf9ebbc3469dceef6d4`
- Qdrant image ID:
  `sha256:affb67e1d6f2f93d7d20b90d238a7d4b974d36351c162e73bda794e4b2e03483`
- Artifact root:
  `data/results/mnemosyne-cognitive/2026-08-16-local-docker-v1`

The doctor and database ran as non-root containers on an internal Docker network,
with read-only root filesystems, dropped capabilities, `no-new-privileges`, bounded
CPU/memory/PIDs, no host ports, no API/model calls, and no GPU access. Qdrant state
alone persisted across the restart phase. Each repeat used a fresh network, volume,
collection, and container pair.

The four committed upstream Vitest files passed twice: 62/62 tests. Those tests are
mock-only and the upstream package has no `test` script, so this does not substitute
for the native lifecycle doctor. A contained production-dependency audit found one
moderate direct `uuid` advisory and no high or critical advisories at collection.

## Reproduced lifecycle failures

1. `consolidate({dryRun: true})` changed a stale record's priority from `0.8` to
   `0.4`. Dry-run is therefore not observational.
2. A second consolidation changed the same record from `0.4` to `0.2` and again
   reported one stale demotion. The transition is not idempotent.
3. The demoted record remained retrievable through normal serving search. This is
   a score mutation, not an inactive residency boundary.
4. Public forget reported success and hid the record from search, but the underlying
   Qdrant point remained with `deleted=true` and the exact plaintext canary.
5. The tombstone and plaintext survived a fresh Qdrant process.
6. The public memory API exposes no native session-scoped purge operation.
7. Consolidation reported `analyzed=200` while only five points were resident,
   demonstrating that the report field reflects a configured batch cap rather than
   the actual resident count.

Positive controls also worked: popular-memory promotion to `core`, the duplicate
tombstone, ordinary resident state, and all failure conditions persisted across the
fresh-process restart. Both clean repeats were byte-identical at the structured
report level:

- initial projection SHA-256:
  `a78cf1418f4687e6744c43d5408617b420b6a31a78c42d8ccf89e99f5996b691`
- restart projection SHA-256:
  `fcebdca6cf05a724e57719f91e789a28ccd8911e56d859179bb4ec5fab23641a`

## Decision

- Terminal status:
  `MNEMOSYNE_COGNITIVE_ACTIVE_INACTIVE_ADMISSION_KILLED`
- `scientific_result=false`
- `publication_ready=false`
- H100 actor admission: `forbidden-for-this-revision`

Do not run an H100 quality screen for this revision. A later upstream revision may
re-enter only with a new preregistered contract that proves non-mutating dry-run,
idempotent consolidation, an actual inactive serving boundary, restart-stable
physical purge or cryptographic erasure, and a bounded resident-set invariant.

