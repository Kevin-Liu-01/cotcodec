# Graphiti native lifecycle admission audit — 2026-08-15

## Decision

Graphiti `401c59a65bdeb22a44136901ff30231e6998a7fe` is blocked from H100
memory-quality work in the registered ARM64 runtime. The lifecycle contract and
host development tests pass, but the contained native backend cannot start:
FalkorDBLite 0.10.0 packages an x86-64 `falkordb.so` beside an AArch64
`redis-server`.

This is a container-admission negative, not a Graphiti retrieval-quality result.
No contained lifecycle operation completed, no model ran, and no GPU time was
used.

## Bound identities

- Graphiti revision: `401c59a65bdeb22a44136901ff30231e6998a7fe`
- Graphiti source archive SHA-256:
  `9cfbc01e90f4e6dfbf61fefe86e7f04b15c57c08a7ff8298f873d6f5696d0303`
- Graphiti version: 0.29.3
- FalkorDBLite version: 0.10.0
- Adapter: `graphiti-explicit-triplet-lifecycle-v1`
- Image ID:
  `sha256:de790ca9605b172009ca833ef82d3cf0761b8316be53a9d9ebbe5ca8ddc347b8`
- Registered experiment SHA-256:
  `6dfb4bf7f415378b8351870aeedda80881bb8842523bfc6ae4d7a1365d10526c`
- Sealed evidence:
  `research/evidence/memory/graphiti-falkordblite-arm64-v2.json`
- Evidence SHA-256:
  `6664df62075c190d9e1a257ddae08a932ac8bad37173826cf6920a6727b66102`

## What passed

The task-blind lifecycle adapter has host-development coverage for explicit
triplet write/update/delete/query, source-lineage closure, idempotency and
divergent replay rejection, fresh-process restart, physically separate branch
databases, adapter-scoped purge, residue checks, and capability refusal. The
registered memory-experiment validator also passes.

These checks establish adapter semantics only. They are not contained,
publication-grade evidence and are not included in the sealed negative bundle.

## Reproduced contained blocker

Two fresh Docker invocations used the immutable image ID with `--pull=never`,
`--network none`, a read-only root filesystem, all Linux capabilities dropped,
`no-new-privileges`, non-root UID/GID `65532:65532`, bounded CPU/memory/PIDs,
and only tmpfs state/output paths. Both failed before the first lifecycle write
with `The redis-server process failed to start`.

The sealed ELF probe found:

| Runtime file | ELF machine | SHA-256 | Size |
|---|---:|---|---:|
| `redis-server` | 183 (AArch64) | `a98cb3fd27705c7e33b0a2db3c8647bcc33ef230200bc5670bf792ddf75e9f9e` | 13,897,584 |
| `falkordb.so` | 62 (x86-64) | `47885e2da788c3fb822b9bd4c182a9694d67286a7fd8fe18c33e3c1a0d05636b` | 51,475,528 |

All 14 registered probe checks passed, including exact source, experiment,
adapter, runner, architecture, network policy, and two-run failure semantics.
Each repetition now binds the Docker-created container ID, creation time,
start/finish times, exit state, immutable image ID, mounts, and security/resource
configuration. The two container receipts differ independently of the run index.

## Secondary development observations

- The host development path exposed an upstream FalkorDB group-filter problem
  after RDB reload: an unfiltered relationship query succeeds while the
  equivalent literal/parameterized group-filter query returns no row. The
  adapter therefore isolates each session in a separate physical database and
  does not claim shared-database group isolation. This observation is not part
  of the sealed container result.
- An emulated AMD64 build under QEMU failed while compiling FalkorDBLite with a
  segmentation fault. That attempt is not a native AMD64 reproduction and is
  not evidence that the package fails on an AMD64 cluster node.

## Admission rule and next gate

H100 admission stays forbidden for this revision/runtime. Reconsider only after
one of the following produces a new immutable evidence bundle:

1. a newer pinned FalkorDBLite/Graphiti combination ships architecture-correct
   native modules and passes the same contained lifecycle doctor twice; or
2. a reviewed, explicitly labeled patch arm vendors/builds the Falkor module for
   the target architecture and passes restart, branch isolation, lineage,
   purge/residue, crash recovery, and phase-cost gates on the actual Slurm node.

Only then may the common-construction flat-versus-graph actor study be compiled.
