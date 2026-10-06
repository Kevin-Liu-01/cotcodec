# Active Graph fork-lifecycle admission audit — 2026-08-16

## Verdict

Pinned Active Graph revision `8aedb1866cf5dce056af97529152ffd6f468a1ed`
passes its native SQLite parent/fork divergence, nested-fork isolation, deterministic
reload, structural-diff, retirement, and retirement-idempotency checks. It fails the
memory-system lifecycle admission boundary because retirement is explicitly an
archive move rather than erasure, keeps the rejected run and its plaintext in the
same SQLite database after a fresh-process restart, and exposes no native run-scoped
purge operation.

Terminal status:
`BLOCKED_ARCHIVE_ONLY_RETENTION_NO_SCOPED_PURGE_AND_SHARED_DB_ERASURE`.
Do not run an H100 actor for this revision.

## Reproduced contract

- Exact source commit: `8aedb1866cf5dce056af97529152ffd6f468a1ed`
- Exact source tree: `8f101d35376f5ef12f197b34a27a2c5aa80ac584`
- Git archive SHA-256:
  `91e0f4099336d34fdb60aee6d9c134ba8f91a2b358d1f46548501353e448461a`
- Doctor image ID:
  `sha256:59fb38ce501a861d1670b1cc385e77d83c5f55fdf6567053ea71cd0a9c10acaf`
- Runtime: two fresh non-root Linux/ARM64 Docker volumes, network disabled,
  read-only root, all capabilities dropped, no-new-privileges, no provider calls,
  no model calls, and one fresh-process restart per repeat.
- Stable phase projection:
  `bc1be630657d7629ce35975b0387f4e34968c8eb79c3a18f7ca838fd204940a1`

Both clean repeats proved:

1. parent and child diverge at the fork point;
2. a nested fork remains isolated from both parent and first child;
3. those identities and projections survive a fresh-process restart;
4. `retire()` moves the rejected run out of the active event log and is idempotent;
5. the archived event, run metadata, and unique plaintext canary remain in the same
   database after restart; and
6. the pinned public `SQLiteEventStore` exposes no `purge`, `purge_run`,
   `delete_run`, or `erase_run` operation.

The source-level receipt independently binds the upstream contract language
`snapshot + archive tier, never deletion`, `retire()` calling `archive_run()`, and
the SQLite implementation copying rows into `events_archive` before deleting only
their active-table copies.

## Claim boundary

This is lifecycle/component evidence only. It does not measure retrieval quality,
semantic-memory utility, active/inactive paging, graph efficacy, model effects, or
publication performance. The positive fork/replay result makes Active Graph a useful
event-sourced experiment substrate, but it is not admissible as a user-scoped
persistent-memory system under the registered erasure contract.

## Next admissible gate

Admit only a newer immutable revision or an explicitly reviewed repair arm with a
native branch-scoped physical purge or cryptographic erasure operation. The repair
must survive restart, leave parent and sibling runs byte-for-byte unchanged, clear
all rejected-run metadata and plaintext residue, and repeat the same fork/replay and
isolation doctor twice before any H100 actor cell.

## Evidence

- Receipt: `research/evidence/memory/activegraph-fork-lifecycle-negative-v1.json`
- Retained bundle:
  `data/results/activegraph-fork-lifecycle/2026-08-16-local-docker-v1`
- Report SHA-256:
  `74b2ec1dbfdd1599341c68ea97cde35e67ff7967c1330589ca3674659dea654c`
- Manifest SHA-256:
  `b64277d439b66e620a662a63352e6b3b464955a5c0c82bd13d47619bbb2524cb`
- Validator: `uv run python scripts/validate_activegraph_lifecycle_evidence.py`
