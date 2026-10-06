# Shodh Memory tier-admission audit — 2026-08-16

## Verdict

Pinned Shodh Memory revision
`98c6e4861847a76f75eb880acf9e145d30794a46` is **not admitted** to an
H100 actor or a memory-quality comparison. Two clean, network-disabled Docker
runs reproduced the terminal status
`BLOCKED_OVERLAPPING_RESIDENCY_AND_RESTART_STRANDING`.

This is a lifecycle/mechanism negative, not a memory-quality result. It does
not imply that Shodh's graph retrieval, reinforcement, or ordinary persistent
recall are ineffective.

## Immutable source and runtime

- Repository: <https://github.com/varun29ankuS/shodh-memory>
- Commit: `98c6e4861847a76f75eb880acf9e145d30794a46`
- Tree: `a7c6ee81b9299cfe4fd56789b1cfd76a5c46bc85`
- `git archive` tar SHA-256:
  `e5930fc638929d98e2149452afd2d7d02c74134115e78bcd8197d7f06165ed60`
- License: Apache-2.0; file SHA-256:
  `219672554a141ac4ba8a1cb3fecf8d1e3209515963ff1c1f946c5cda3a85d86d`
- `Cargo.lock` SHA-256:
  `0f3356ec80fe3b3f683fd896e2a65c23d5cc8e11fc175b3f90efc58487b03972`
- Admission image ID:
  `sha256:7afbe36f4023ca96beac46249aff049ccd4ae3b06a969fe1cd31eb6f7770ebc5`
- Doctor SHA-256:
  `9612d25d5ae6d62a527fe344ca8ee2a6890bd55b9dea153499ff881a4f50cae4`
- Runtime: Linux ARM64, uid/gid 65532, read-only root, all capabilities
  dropped, `no-new-privileges`, no network, no provider secrets, no GPU, and
  simplified deterministic local embeddings.

The retained machine-verifiable bundle is
[`research/evidence/memory/shodh-tier-admission-negative-v1.json`](evidence/memory/shodh-tier-admission-negative-v1.json),
SHA-256
`e8805c42e64847eb82858b09d7d56b83b7fd71afd8a1633d840afcf272f278ad`.
It embeds the experiment, doctor, runner, validator, relevant pinned source,
image inspection, both raw runs, both parsed runs, report, and manifest. The
stable semantic projection SHA-256 is
`1a9fc93172a6b682ec26fafb718259d17da7e7e041b7317d369abfcf288eb082`.

## What the source implements

The public API writes every new memory to RocksDB before adding the same object
to the in-memory working tier. “Working,” “Session,” and “LongTerm” therefore
do not form three disjoint residence stores. They are a durable record plus
overlapping process-local caches and a persisted tier label.

At process construction, working and session counts start at zero and the two
maps are not rebuilt from RocksDB. Maintenance promotes items by scanning those
process-local maps. These mechanics predict two restart boundaries that the
ordinary upstream persistence tests do not exercise: a durable item can retain
a stale Working label after its working cache disappears, and a Session item
that becomes old enough while the process is down is invisible to the session
promotion scan after restart.

## Falsifier and exact observations

Each clean repeat performed the same three public-path probes:

1. Write one fresh Working item, inspect the logical tier counts and durable
   store, restart the full system, then inspect again.
2. Persist a 26-hour-old Session item, start a fresh process, call the real
   maintenance path, and inspect the stored tier and promotion counter.
3. Write one canary, call public `forget(All)`, restart, test logical access,
   and perform only a bounded raw substring scan.

Both runs produced the same observations:

| Probe | Before | After |
|---|---|---|
| Fresh Working record | total 1, working 1, long-term 1, stored tier Working | total 1, working 0, long-term 1, stored tier still Working |
| Offline-aged Session record | session cache 0, long-term 1, stored tier Session | maintenance promotions 0, stored tier still Session |
| `forget(All)` | one unique record | return value 2; logical total 0 after restart |

The bounded raw scan did **not** find the plaintext canary before or after
forget. That supports neither a residue claim nor a physical-erasure claim:
the canary was not present as a raw substring before deletion, so absence after
deletion is uninformative about RocksDB erasure.

## Upstream regression tests

The admission image intentionally contains only locked runtime dependencies.
A separate build-only image resolved the checked-in dev dependencies with
network access, after which the compiled tests were executed with network
disabled, read-only root, non-root uid, no capabilities, and no GPU:

- `memory_tiering_tests`: 15 passed, 0 failed.
- `memory_persistence_tests`: 20 passed, 0 failed.
- Test image ID:
  `sha256:6aa126278dd721d5616f728c5219e497493941c5711e080a5e15d8e3b44c1294`.

These green results are compatible with the negative. The tests verify
ordinary logical persistence, cache coherency, retrieval, and same-process
tier promotion. They do not require disjoint residence, reconstruct active
caches after restart, or age a Session record while the process is absent and
then require fresh-process maintenance to promote it.

The upstream-suite result is diagnostic and not part of the retained evidence
root; only the two-repeat falsifier above is machine-sealed.

## Claim boundary and next gate

This revision may remain a deterministic graph/reinforcement implementation
reference, but it is not evidence for active/inactive paging. Do not spend H100
time on an actor cell for this pin.

A newer pin or explicit patch arm may be reconsidered only if it provides:

1. one authoritative, disjoint residency state per record;
2. deterministic reconstruction or explicit lifecycle treatment of active
   caches across fresh processes;
3. offline-aged Session-to-LongTerm promotion after restart;
4. unique-item forget accounting and a separately specified physical erasure
   contract;
5. the same two-clean-state contained doctor plus the upstream regression
   suites.

Only after those gates pass should graph-vs-flat or actor-quality H100 cells be
compiled.
