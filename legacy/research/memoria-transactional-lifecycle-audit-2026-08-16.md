# Memoria transactional lifecycle audit — 2026-08-16

## Verdict

The exact pinned Memoria revision is a useful transactional-memory component,
but it is not admitted to the H100 actor wave. Two clean contained runs reached
the same terminal status:

`BLOCKED_SHARED_TABLE_BRANCH_EXPOSURE_SOFT_PURGE_RESIDUE_AND_NONATOMIC_ROLLBACK`

This is a local negative lifecycle reproduction, not a memory-quality or paper
result. The retained evidence is
`research/evidence/memory/memoria-transactional-lifecycle-negative-v1.json`.

## Bound identities

- Source: `matrixorigin/Memoria` at
  `efd3d6515969971dfa894737272b8317bcb643e7`
- Tree: `c07d7b427a9d664d8473b0c2139ecc0d72e229d4`
- Git archive SHA-256:
  `a81f15ca11c616d477e929853019a2156799229f75c1d264a761fe7b42cdaa2e`
- MatrixOne image:
  `matrixorigin/matrixone@sha256:66e2e0123d32094bff32ef7b8ba06d6d84391983cd1c9c41329dc3f7a05a2518`
- Doctor image ID:
  `sha256:47198b00190e64a35459c83a76008a2f01b20358f220aab0ee356ea7b84046c4`
- Stable phase projection:
  `b5281d07d35d4bbdc5cb053d4a06cc3ea53026e93f4d7ed2c2ec55e909a06a33`

The doctor ran as non-root in a Docker internal network. MatrixOne and the
doctor received no GPU and no provider secrets. Each of two clean states forced
two MatrixOne restarts.

## What passed

- Snapshot creation, restoration, and deletion executed through the pinned
  native source.
- Branch state diverged from main state, a native merge added the branch-only
  row, a conflicting main value was kept, and the second merge was idempotent.
- Main, snapshot, branch, and inactive-row state survived the prescribed
  process restarts.
- Dropped branch and snapshot state remained dropped after restart.

## Reproduced blockers

1. In legacy shared-database mode, a branch made for one user contained another
   user's rows. This is not an isolated per-user fork.
2. Native purge was a soft deactivation. The memory row remained physically
   present and remained present after restart. Calling purge twice was
   idempotent underneath, but the public service response still reports
   `purged: 1` independently of the actual deactivation count.
3. Source inspection confirmed that snapshot restoration is an explicit
   `DELETE` followed by `INSERT`, and the source itself marks that sequence as
   non-atomic. A crash between those operations can expose a partial restore.

## Claim boundary and next gate

The result supports only exact pinned branch/snapshot/merge/restart component
behavior in legacy shared-database mode. It does not establish multi-database
isolation, retrieval quality, active/inactive paging, paper results, or
publication readiness.

Do not run an H100 actor on this revision. A newer revision or explicit patch
arm must first demonstrate branch scope isolation, physical deletion or
cryptographic erasure after restart, truthful purge counts, and atomic snapshot
restore under an injected crash. Only then should a bounded matched actor cell
be considered.
