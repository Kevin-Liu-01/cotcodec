# agenticow branch lifecycle admission — 2026-08-16

## Verdict

Pinned `agenticow` revision `dd4f437b92d2dbbc1f40dfa00023eed6e9c3bd84`
is a useful copy-on-write branch and rollback substrate, but it fails admission as
a trustworthy persistent memory branch runtime. The terminal status is
`BLOCKED_BLIND_PROMOTION_LOST_UPDATE_TOMBSTONE_RESIDUE_AND_NO_SCOPED_PURGE`.
No H100 actor or memory-quality experiment is permitted for this revision.

This is a contained native lifecycle result, not a model-effect, active/inactive
paging, scientific, or publication result.

## Immutable source and runtime

- Repository: `https://github.com/ruvnet/agenticow`
- Commit: `dd4f437b92d2dbbc1f40dfa00023eed6e9c3bd84`
- Git tree: `b64b6fae03aac0491e3d3b78281b5c6997516ebf`
- Git archive SHA-256: `a563784a4c7645f51a45ab430c7c8d3aec77b61cad609585389173da21bdfeac`
- MIT license SHA-256: `631f94984f626818d42ecf717aa6e8e0afd4f9f355ca706bd2effafbd1416d06`
- `package-lock.json` SHA-256: `3a567fe53f577b56101b5410398b181c4ed2750fd29708ac36dc2f6189982129`
- Container: `cotcodec-agenticow-lifecycle:dd4f437-arm64-v2`
- Image ID: `sha256:b36438eed60b23c0e95f8a69c4cccbde930ea495c059a423c8062b73b7938ef3`
- Runtime: Linux ARM64, non-root `65532:65532`, read-only root, network disabled,
  one isolated persistent `/state` volume, zero model or provider calls, zero GPUs.

The image labels bind the repository revision, tree, source archive, and exact
doctor. The retained image inspection and every experiment artifact are hashed
by the evidence receipt.

## Reproduced positive behavior

Two independent clean-state runs produced the same semantic phase projection,
`eeb24984a901d4bcb2982eab89af6c9a85c5a07ce8db6ce8ca640e5942709571`.
Both runs passed:

- parent/child branch isolation and nested-fork isolation;
- checkpoint visibility followed by rollback removal of the poisoned write;
- child tombstones masking inherited values without changing the sibling;
- branch, nested-fork, sibling, and text-payload behavior after a fresh process
  restart;
- persistence of a promoted child value; and
- logical idempotency of repeated promotion.

These results support using the mechanism as a branch-state implementation
reference after its lifecycle defects are repaired. They do not establish memory
quality or causal-credit validity.

## Reproduced blockers

### Blind promotion loses a newer target write

The parent was updated after the child forked. Promoting the child then silently
overwrote that newer parent value. The native promotion path has no compare-and-
swap, version precondition, merge conflict, or stale-base rejection. The promoted
child value persisted after restart, proving a durable lost update rather than a
transient read artifact.

### Deletion is a tombstone, not erasure

The child tombstone correctly masked its inherited value, and the sibling retained
its own view. After restart, however, the tombstoned plaintext remained in the
persisted manifest. The exact source also persists text for every node.

### No native scoped purge

The inspected public API provides no branch-scoped physical purge or cryptographic
erasure contract. Removing the entire shared persistence root would destroy parent
and sibling state, so it is not an admissible scoped deletion operation.

## Admission boundary and next gate

This exact revision is killed before H100 admission. A future immutable revision
or separately declared repair arm must, in two fresh contained runs, reject stale
promotion or perform an explicitly audited conflict merge and physically purge or
cryptographically erase one branch without changing its parent, sibling, or nested
forks. It must then repeat the same fresh-process restart and residue checks before
any actor or memory-quality allocation.

## Retained artifacts

- Result root: `data/results/agenticow-branch-lifecycle/2026-08-16-local-docker-v1`
- Report SHA-256: `9e06b2afbe0e2ac67eddb52c1656bdccbd82c2f87eac775561b8b91f38ffdba7`
- Manifest SHA-256: `b9003706a570b2c64013ff8f0d7d3acea72ddffe3e7e64a71698946c5a579af8`
- Evidence receipt: `research/evidence/memory/agenticow-branch-lifecycle-negative-v1.json`
- Evidence receipt SHA-256: `87b045a10b1a2fd7649f189f1a71d174dd3b20a81038ad413ae395813ea0a18a`

