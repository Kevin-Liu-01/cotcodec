# MemForest exact-source lifecycle audit — 2026-08-17

## Decision

`fb4320a84d296bf7b0752d7ef1f2ad0726ae0b22` is blocked from H100 actor
admission. The exact public lifecycle passed normal restart and saved
session-deletion controls, but failed tenant-path confinement and atomic
snapshot recovery in two clean, network-disabled Linux ARM64 repeats.

Terminal status:
`MEMFOREST_LIFECYCLE_ADMISSION_KILLED_UNCONFINED_TENANT_PATH_AND_TORN_SNAPSHOT`.

## Bound source and runtime

- Repository: `https://github.com/Concyclics/MemForest`
- Revision: `fb4320a84d296bf7b0752d7ef1f2ad0726ae0b22`
- Tree: `2e30793c77ef0b7fc8b36bd6d3648a1d9f2fecb2`
- Source archive SHA-256:
  `3809857bcd1f2fb799038a604149a1354277f80dd87893c7f2e3949c743211e0`
- Doctor image:
  `sha256:33326b6049ab910889d472504d37f0f1b42ba481345f7b3af6e86b50f80a7ba6`
- Runtime: Linux ARM64, Python 3.12.11, non-root UID/GID 65532, Docker
  `--network none`, read-only root filesystem, no provider secrets, no GPU.
- Dependencies came from the committed direct pins. The repository has no
  transitive lock, so the complete `pip freeze` receipt is retained and this
  is not a byte-identical environment reconstruction claim.

## Positive controls

- A normal user, fact, and session survived a fresh-process restart in both
  clean repeats.
- `delete_session` followed by `save` survived restart: the deleted session
  and its fact were absent from live state.
- The bounded scan of retained current files found no deleted plaintext canary
  in either repeat. This is not secure filesystem erasure evidence.
- The synthetic five-session write diagnostic completed in both repeats. The
  one-session incremental update used 8 deterministic chat-double calls and
  25 embedded texts; the clean five-session rebuild used 21 and 76. Wall-clock
  timings are retained as diagnostics only, not sustained-throughput or causal
  mechanism evidence.

## Reproduced admission failures

### Tenant path confinement

`MemForest.register_user` passes `self._snapshot_dir / user_id` directly to
`UserForest` without validating or canonicalizing the tenant identifier.

Both repeats demonstrated that:

- a relative `../...` user ID wrote a complete snapshot outside the configured
  snapshot root;
- an absolute user ID replaced the configured snapshot root;
- a lexical alias containing `parent/../target` and the canonical `target` ID
  resolved to the same storage and disclosed the alias user's facts;
- those escaped and collided artifacts survived fresh-process restart;
- the public coordinator exposes no `delete_user`, `purge_user`, or
  `unregister_user` operation.

### Torn multi-file snapshot

`UserForest.save` writes the fact manager, trees, node index, session registry,
summary cache, cell store, and metadata sequentially without a transaction,
journal, generation pointer, or atomic directory swap.

The doctor created a valid baseline, ingested a second session, and forced an
exception at `NodeIndex.save` after the new facts and trees had been written but
before the registry, cell store, and metadata advanced. A fresh process loaded
successfully into a mixed generation:

- both baseline and new facts were present;
- `session:sess_0002` from the new generation was present;
- only the baseline session was registered and active;
- only the baseline cell and alias entry were present.

The same mixed projection survived a second fresh-process restart in both
clean repeats. The loader neither rejected nor repaired it.

## Claim boundary

This is exact-source local lifecycle evidence for deterministic-fake ingest,
tenant registration, save, restart, saved session deletion, tenant-path
confinement, interrupted multi-file save recovery, native tenant-purge surface,
bounded current-file plaintext scan, and a synthetic write-path diagnostic. It
does not evaluate model extraction quality, semantic retrieval quality, secure
filesystem erasure, sustained serving throughput, localized-maintenance causal
effect, H100 actor quality, or publication readiness.

## Next admissible gate

Admit only a newer immutable revision or explicit reviewed repair arm with:

1. canonical tenant-ID validation and enforced snapshot-root confinement;
2. a native tenant-scoped purge contract;
3. atomic snapshot generations or journaled recovery that rejects or repairs a
   mixed component generation;
4. the same two-clean-state doctor repeated before any common-construction
   retrieval or H100 mechanism cell.
