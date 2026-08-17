# Total Recall Native Lifecycle Audit — 2026-08-14

## Verdict

Total Recall v4.0.4 at commit
[`a2630f671be9b12df8b8ac78df9d26f7053d2fa9`](https://github.com/strvmarv/total-recall/tree/a2630f671be9b12df8b8ac78df9d26f7053d2fa9)
is rejected as the first fixed active/inactive H100 control. Its native
automatic hot-to-warm transition loses the vector row; on the next process
open, orphan cleanup deletes the demoted content row. The finding reproduced
in two fresh, network-disabled Docker containers.

This is a negative lifecycle result. It does not evaluate memory quality and
does not imply that unrelated Total Recall operations fail.

## Primary-source mechanism

- [`HotTierCompactor.Compact`](https://github.com/strvmarv/total-recall/blob/a2630f671be9b12df8b8ac78df9d26f7053d2fa9/src/TotalRecall.Infrastructure/Memory/HotTierCompactor.cs#L35-L93)
  calls `store.Move` for automatic hot-to-warm compaction.
- [`SqliteStore.Move`](https://github.com/strvmarv/total-recall/blob/a2630f671be9b12df8b8ac78df9d26f7053d2fa9/src/TotalRecall.Infrastructure/Storage/SqliteStore.cs#L458-L544)
  copies and deletes the content row but does not migrate its vector.
- The production `SqliteStore` constructor runs
  [`CleanupOrphanRows`](https://github.com/strvmarv/total-recall/blob/a2630f671be9b12df8b8ac78df9d26f7053d2fa9/src/TotalRecall.Infrastructure/Storage/Schema.cs#L439-L470),
  which deletes content rows with no vector.
- [`MoveHelpers.MoveAndReEmbed`](https://github.com/strvmarv/total-recall/blob/a2630f671be9b12df8b8ac78df9d26f7053d2fa9/src/TotalRecall.Infrastructure/Memory/MoveHelpers.cs#L42-L73)
  is the manual positive-control path. It re-embeds after moving, while also
  documenting a separate crash window between the two operations.

## Reproduction contract

- Source commit: `a2630f671be9b12df8b8ac78df9d26f7053d2fa9`
- Git tree: `6d62153e3db4026d2146a80251146f9bc3efca68`
- Git archive SHA-256:
  `19c7e803e6887c740b841043d6a86980f59947b51e6b282a155c477fc37a1338`
- License: MIT; file SHA-256:
  `d97ac8afe40f62ed6f5bffe8dd941a1fac3543b6c68475f6f4e5923f7c128f15`
- Runtime: Docker, Linux/arm64, non-root UID/GID 65532, read-only root,
  `--network none`, all capabilities dropped, no-new-privileges, zero GPUs,
  no sudo.
- SDK base:
  `mcr.microsoft.com/dotnet/sdk:10.0.100@sha256:4c85fffe3c700195278ea4f86ca47ecac394da6d91b8fd3282fde63807e26659`
- Node acquisition base:
  `node:20.19.4-bookworm-slim@sha256:ea5377506163eeea3b3b163b10d74d7e82d735dc89435d3f54f1a783afc83d89`
- Built image ID:
  `sha256:5d64ffaf4706e92f802736d664692d9d49e4326053cf2f41b9253918a1c1732b`
- NuGet lock SHA-256:
  `615a3f37e6d494f6fae7e293dd6fefdd2464780701ef318fa02cbb694ab10d67`;
  restore ran with `--locked-mode`.

The doctor inserts two native 384-dimensional sqlite-vec records. The first is
demoted through `HotTierCompactor`; the second is moved through
`MoveAndReEmbed`. It closes and reopens the same database through the
production `SqliteStore(string dbPath)` constructor.

| Invariant | Automatic path | Vector-preserving control |
| --- | ---: | ---: |
| Content rows before restart | 1 | 1 |
| Vector rows before restart | 0 | 1 |
| Content rows after restart | 0 | 1 |
| Vector rows after restart | 0 | 1 |

All six preregistered negative-result gates passed twice, and the deterministic
status/row/gate projections were identical. Elapsed time is deliberately not
part of that equality check.

## Artifacts

- Self-contained tracked evidence bundle:
  [`research/evidence/memory/total-recall-restart-v3.json`](evidence/memory/total-recall-restart-v3.json),
  file SHA-256 `b1bc7c003584d6b089da91bafef4ac0ba77452557fc358d97e40b2a16418422d`.
  It embeds and rehashes both complete run directories, validates their child
  manifests, and binds the shared source, image, input receipt, terminal
  status, and deterministic negative-result projection.

- First run:
  [`data/results/total-recall-lifecycle/2026-08-14-restart-doctor-v3/manifest.json`](../data/results/total-recall-lifecycle/2026-08-14-restart-doctor-v3/manifest.json),
  file SHA-256 `1db53b5dcb8222db015199473a1ebc99342cb0676111bfe0e92913fcfdaee0fd`
- Replication:
  [`data/results/total-recall-lifecycle/2026-08-14-restart-doctor-v3-replication/manifest.json`](../data/results/total-recall-lifecycle/2026-08-14-restart-doctor-v3-replication/manifest.json),
  file SHA-256 `5ea10267da55b28c1e455efbe3b5fece6ddb26ebd0ac991c7de7d40202c189e4`
- Registered experiment:
  [`experiments/memory/stage3-total-recall-lifecycle-doctor.yaml`](../experiments/memory/stage3-total-recall-lifecycle-doctor.yaml)

These are local discovery receipts from the shared dirty CoTCodec tree. The
upstream Total Recall source itself was clean and exact, but the CoTCodec doctor
image lacks externally trusted publication attestation. `scientific_result`
and `publication_ready` remain false.

The v3 input receipt additionally binds the experiment YAML, runner,
experiment validator, Dockerfile, doctor source/project, upstream package lock,
generated NuGet lock, and upstream `global.json`. Both v3 runs have identical
input receipts and use the same image ID.

## Other hard boundaries at this pin

1. Warm-to-hot promotion can exceed the configured hot capacity because
   capacity demotion occurs before promotion and the promotion loop does not
   subtract current occupancy.
2. The MCP session-end handler is constructed without the configured decay
   threshold and constant, so those settings do not govern that path.
3. Automatic warm-to-cold compaction is not implemented; `compact_now` is an
   informational stub.
4. Hybrid-search returns are touched before the downstream model acts, so
   “access earned” means retrieval exposure, not demonstrated use or outcome
   utility.
5. Manual promotion/demotion re-embeds but is itself non-atomic across content
   movement and vector insertion.

## Decision

Do not implement a `memory-lifecycle-v1` H100 actor adapter for this pin. Admit
only one of:

1. a newer immutable upstream commit that passes the same doctor twice plus a
   crash fault-injection test; or
2. an explicitly labeled patch arm that atomically moves content and vector,
   preserves identity and lineage across two restarts, enforces `hot_count <= K`
   after promotion, and makes configured thresholds govern the actual MCP path.

The next unblocked native mechanism cells are a graph-state doctor (Graphiti or
GAAMA), a fixed decay/consolidation doctor (Hippo), and a procedural-state
doctor (ReasoningBank). They remain CPU admission work before H100 comparison.
