# Mnemo Cortex exact-source lifecycle audit — 2026-08-26

## Decision

Mnemo Cortex revision `8a0cff9492f010f73d722688924b09938b2dd682` is
blocked from H100 actor admission. Its smart-note, raw-log, Analyst, deterministic
dream, and fresh-process persistence controls passed in two clean states, but the
official no-Git container surface returned 500 after mutating Passport pending
state, an identical retry created a second pending row, both rows survived
restart, and the primary memory API exposed no native delete, forget, or purge
route.

Terminal status:
`MNEMO_CORTEX_ADMISSION_KILLED_NO_GIT_PARTIAL_WRITES_NO_NATIVE_PURGE_AND_UNPINNED_DEPS`.

## Bound source, build, and runtime

- Repository: `https://github.com/GuyMannDude/mnemo-cortex`
- Revision: `8a0cff9492f010f73d722688924b09938b2dd682`
- Tree: `5a87d92d70052717a928c3c109b138da4d8af723`
- Source archive SHA-256:
  `6b6e7709a85f9f949f2a7820ee4c2a7e60112671297fa5229919a266f014c113`
  (`18,810,880` bytes)
- Doctor image:
  `sha256:6a81c7eac7a1105736e1fa0d271a0d531448f1c9c80da7b980b8fda3af3e1cdb`
- Slurm job: `347`, four CPUs, 16 GiB, no GPU request, no visible CUDA
  devices, no provider secrets, and zero external model calls.
- Runtime: Linux AMD64, Python 3.12.11, non-root UID/GID 65532, read-only root
  filesystem, Docker build and execution networks both disabled.
- Digest-pinned base:
  `python:3.12.11-slim-bookworm@sha256:519591d6871b7bc437060736b9f7456b8731f1499a57e22e6c285135ae657bf7`.
- Offline dependency transport: 26 wheels (`23,917,516` bytes), manifest
  `95395024deabd10961d58ca20fd2b19afad9b4c654207e243e9edf35796dcd9a`,
  and hash-locked requirements
  `e7661ad02aad751446fd3f889c8a7c1a4f61a3ee333e940e583b3ed9b9a0b055`.

The runtime lock makes this execution replayable; it does not repair upstream
provenance. The exact repository has no Python lock, declares lower bounds, and
uses mutable `python:3.12-slim` in its Dockerfile. Those remain source findings.
The pinned revision was reachable only through an explicit SHA fetch, not an
advertised remote branch or tag.

## Positive controls

- A forced smart note was classified once as `decision`; the raw auto-capture
  record was classified as `session_log` without an extra classifier call.
- Default recall excluded the exact raw memory ID before and after restart.
  Explicit `category=session_log` drill-down returned that ID in both clean
  states. After Analyst consolidation, default recall could legitimately return
  the derived `decision` note containing the raw canary in its key facts; the
  doctor therefore binds category and memory ID rather than token absence.
- The Analyst emitted one derived `decision` note whose `derived_from` lineage
  referenced the raw record, marked the raw record processed, and retained that
  raw Tier-2 source.
- Deterministic dreaming executed two per-agent calls followed by one rollup
  call and produced the registered joint result.
- Three primary-memory records and two Passport pending observations survived a
  fresh process. Both clean-state projections were identical at
  `f07a317a4dfa6cea1ccf2b33364a607ca279dcabf4feb33fea014786f1cd2779`.

These controls establish exact-source topology and lifecycle behavior only.
They do not measure real-provider extraction, consolidation, sharing, or answer
quality.

## Reproduced admission failures

### Passport acknowledges after a non-transactional partial write

`POST /passport/observe` calls `pending.add()` before the Git-backed commit.
The upstream image installs the Python package but not Git. In each clean state:

1. the first observe request returned HTTP 500;
2. `/passport/pending` nevertheless exposed `obs_001`;
3. retrying the identical request returned HTTP 500 again;
4. pending state then contained `obs_001` and `obs_002` with the same proposed
   claim; and
5. both duplicate rows survived a fresh process.

The failure therefore is not merely an unavailable optional command. The public
request mutates durable state before its error response, and retry is not
idempotent across the pending, Git, and acknowledgement boundary.

### No native primary-memory purge or erasure boundary

Static source inspection and runtime route enumeration found no native primary
memory delete, forget, or purge operation. The only adjacent demotion surface is
not a tenant-scoped erasure contract. A bounded scan after restart found every
smart, raw, Analyst, and Passport canary in current files; the raw canary appeared
in its raw memory file, the derived Analyst note, L1 cache, and SQLite vector
index. Because the test did not perform deletion, this is a residency projection,
not proof of failed secure erasure. The admission failure is the absence of a
native operation with which to exercise that contract.

### Upstream environment is not reconstruction-complete

The exact source provides lower-bounded dependencies and a mutable base tag but
no transitive Python lock. The doctor used an independently receipted offline
wheel closure so the execution result is bound; this does not turn the upstream
artifact into a byte-identical reconstruction contract.

## Pre-result launch diagnostics retained

Jobs `342` through `346` are not scientific results:

- `342` stopped before image build on a static-check predicate typo.
- `343` stopped before image build because the safe extractor initially rejected
  a tracked, root-confined relative symlink.
- `344` pulled the exact base but Docker DNS could not reach PyPI for
  `setuptools>=68`; no image or phase ran. This triggered the offline,
  hash-complete wheel transport.
- `345` reached the mechanism but the doctor assumed every FastAPI route object
  had `.path`; it crashed before producing a complete projection.
- `346` completed phase one, then used token presence as a proxy for raw-log
  presence after restart. Exact inspection showed the token belonged to the
  Analyst-derived `decision` note. The final doctor binds the raw memory ID and
  category and makes false checks sealable rather than discarding them.

Each attempt used a fresh output path. Only job `347` produced the complete,
manifested evidence bundle used for this decision.

## Claim boundary

This is exact-source CPU lifecycle evidence for smart-note classification,
session-log filtering, Analyst lineage, deterministic map-reduce dream topology,
Passport error and retry semantics in the official no-Git surface,
fresh-process persistence, native primary-memory purge surface, bounded current
file scanning, and dependency provenance. It is not semantic extraction quality,
real-provider dream quality, secure filesystem erasure, concurrent serving,
sustained throughput, H100 actor quality, or publication evidence.

## Next admissible gate

Do not run an H100 actor for `8a0cff9`. Admit only a newer immutable revision or
an explicitly reviewed repair arm with:

1. an exact Python lock and digest-pinned base;
2. a complete Passport runtime dependency surface;
3. idempotent transaction recovery across pending, stable, Git, and audit state;
4. a native tenant-scoped primary-memory purge or cryptographic-erasure
   contract; and
5. the same two-clean-state, fresh-process doctor before any matched actor or
   consolidation-quality cell.

## Evidence

- Portable receipt:
  `research/evidence/memory/mnemo-cortex-native-lifecycle-negative-v1.json`
  (`cf288154955ffb701345ea5b1484118057c5f3dfcf0e04b7e9e2506160173aff`)
- Run manifest:
  `4651effc1bf92080f4784d6816c20c511d3ae883760ffadd4a1af313cb0eb194`
- Report:
  `97d2d5abab74982194b53065b3481db0dd2431b512c3510c05361c4c64006970`
- Original experiment:
  `1ffeb25b43d06aefbe56ba0255cca3e9c73767b8f6f184bfbbaba7b71e3b9d9e`

The portable receipt embeds every decision-bearing artifact except `source.tar`,
which is bound by exact size and SHA-256.
