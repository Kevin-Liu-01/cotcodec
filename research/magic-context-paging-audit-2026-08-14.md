# Magic Context paging and lifecycle audit — 2026-08-14

Pinned source: `cortexkit/magic-context@13e1d4c3fa3803ba1f4595029d8c4750dc9bef98`.

This zero-model CPU doctor tested only the plugin's chronological prompt-rendering
and lifecycle boundaries. Two clean, network-disabled, read-only, non-root Docker
states produced the same supported-projection root across fresh processes.

## Reproduced boundary

- A tight prompt budget omitted the oldest live-wire message while a wider budget
  rendered it; the newest message remained visible.
- Supported user text and tool input/output projected reproducibly after restart.
- Reasoning and unsupported message metadata were not restored, so expansion is a
  projection rather than exact raw-message recovery.

## Reproduced blockers

- Expansion requires the host raw-message database. Removing the host row made the
  interval unrecoverable.
- The same session identifier was accepted across harnesses and exposed the same
  compartment, so portable tenant/harness isolation is absent.
- Logical `clearSession` removed plugin rows for the target session but left
  plaintext canaries in the plugin and host SQLite files.

Terminal status:
`BLOCKED_PORTABLE_LIFECYCLE_AND_SECURE_PURGE_REPRODUCED`.

The result is a local lifecycle/boundary negative, not a memory-quality or semantic
memory result. This pin must not enter a semantic active/inactive H100 wave. A new
pin or explicit patch arm must namespace sessions, own or cryptographically bind
restorable raw state, preserve registered fields, and pass scoped physical purge
plus two fresh restarts.

Canonical embedded evidence:
`research/evidence/memory/magic-context-paging-v1.json`.
