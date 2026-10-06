# Agent Recall scoped-lifecycle audit — 2026-08-16

Status: `BLOCKED_CROSS_SCOPE_DESTRUCTIVE_DELETE_STALE_CHILD_BRIEFING_AND_SOFT_DELETE_RESIDUE`

This is a bounded exact-source lifecycle falsification of Agent Recall
`dcf21b5cc9691e1371299917e2e474fb82e07cab`. It is not a retrieval-quality,
briefing-quality, active/inactive-paging, model-effect, or publication result.

## Reproducible identity

- Repository: <https://github.com/mnardit/agent-recall>
- Git tree: `1c0395b24d2d9f45d04443f7f187b026ce41f43b`
- Git archive SHA-256: `f1412268b653e971df41c730bd4d1aa19cb0e20e79f358c4c41c8ec80350a06a`
- MIT license SHA-256: `0c51e5594c40bfe9e039ff0925d3efff5cb83402f21e5d466250958e724ff6c6`
- `pyproject.toml` SHA-256: `9272395436cbcba0b6e537bf26d45c4cbe7593560bfb83309c46fb963acfc70f`
- Contained ARM64 doctor image: `sha256:3891f21f20cebb58b7faea07ee86f30d22570a8b8a9c0902b82d1b36f4b115a0`
- Runtime: two clean Docker volumes, two fresh-process restarts, network disabled,
  non-root UID/GID `65532:65532`, read-only root filesystem, all capabilities
  dropped, no provider/model calls, and no GPU.

The complete evidence is retained at
`data/results/agent-recall-scope-lifecycle/2026-08-16-local-docker-v1`.
Its stable two-repeat phase projection is
`2fed18f7943ef6e96ce343ee665c31b90c03f1115eb6ddf0a807989abddcc5a3`.

## What passed

- A child scope selected its local value over inherited parent/global values.
- Replacing `client-v1` with `client-v2` retained the bitemporal history row.
- Scoped precedence and bitemporal history survived a fresh container process.
- The registered negative outcomes reproduced byte-equivalently in two clean
  stores.

## What failed admission

1. A `client-a` MCP bridge deleted `CrossScopeVictim` even though the same entity
   owned a `client-b` observation. `MCPBridge.delete_entities` checks whether the
   entity is writable and then invokes one unscoped entity-row delete. The
   sibling-scope data loss survived restart.
2. A write to the parent `agency` scope invalidated the parent and orchestrator
   caches but not `client-a`, even though `client-a` inherited and could read the
   parent value. The child briefing therefore remained fresh-looking after its
   visible source changed.
3. `delete_observations` only set `archived_at`. The deleted canary remained
   available through `include_archived=True` and remained plaintext in the
   SQLite file after restart.
4. Neither `MemoryStore` nor `MCPBridge` exposed a native scoped purge or erasure
   operation.

## Decision

Do not run an H100 actor for this revision. Admit only a newer immutable revision
or an explicit reviewed patch arm that enforces row-level authorization for
every affected scope, invalidates all descendant caches after inherited parent
writes, and proves physical or cryptographic scoped erasure after restart using
the same two-clean-state doctor.
