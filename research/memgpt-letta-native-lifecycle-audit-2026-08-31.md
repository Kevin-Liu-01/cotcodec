# MemGPT / legacy Letta V1 exact-source lifecycle audit — 2026-08-31

## Decision

Legacy Letta V1 revision `ff19ffeafeb54bd2a7dc5d4a552f10191732a235`
is blocked from H100 actor admission. Two clean Slurm CPU states passed the
provider-free construction, core mutation, archival write/read, organization
isolation, fresh-process restart, and explicit logical-deletion controls. The
same states also reproduced three admission failures:

1. an injected compiled-message rebuild error returned HTTP 500 after the core
   block mutation had already become durable;
2. an identical archival write retry created a second durable passage; and
3. agent deletion retained its archive and core blocks, while explicit logical
   deletion later removed the API-visible rows but left every canary in stopped
   PostgreSQL heap and WAL files.

Terminal status:
`MEMGPT_LETTA_ADMISSION_KILLED_PARTIAL_CORE_UPDATE_DUPLICATE_ARCHIVE_RETRY_AGENT_DELETE_ORPHANS_AND_POSTGRES_RESIDUE`.

## Bound source, image, and runtime

- Legacy repository: `https://github.com/letta-ai/letta`
- Revision: `ff19ffeafeb54bd2a7dc5d4a552f10191732a235`
- Tree: `675c06071568dd48ca9b16b755041937286b7d95`
- Version and license: `0.16.8`, Apache-2.0
- Source archive: `24,176,640` bytes, SHA-256
  `68858b2315fd6a3f8f499fd5354307c22320d430a7a9b52e475523ec2d43f108`
- Official image:
  `docker.io/letta/letta@sha256:7bdff3a3f876b79db0b347900a392bd6f13eff5c294735eda98be1f8ecf7a7a2`
- Local image ID:
  `sha256:ddfc72e92d690aeea244fd55b617594e468290ee8ede21cbb5aca9876d40e356`
- The tested source files, `pyproject.toml`, `uv.lock`, license, and Dockerfile
  hash-matched their `/app` counterparts in the official image.
- Slurm job `351`: four CPUs, 16 GiB, no GPU request, zero visible GPUs,
  Docker network `none`, no provider secrets, and zero provider or model calls.
- Each repeat used a fresh PostgreSQL data directory, an initial server process,
  a clean stop, and a fresh server process before deletion and residue checks.

The current `letta-ai/letta-code` runtime was also pinned at
`a575e11753943d9a4e18373a8817eb16a5b76b47` / tree
`9bb2cadf097f522bdcbc09fe0268dd6dd82bb410`, with a `50,759,680`-byte source
archive at SHA-256
`d81b210456b049a09d1a98618846273c7f41aadd63e4873fa796ecab20db9bd9`.
That receipt is provenance context only. Letta Code uses a different local
MemFS mechanism and was not treated as a repair or runtime arm in this test.

## Positive controls

- Two organizations and users were created through the versioned admin API.
- An agent was created from a deterministic LLM configuration without invoking
  a provider or generation path.
- A normal core block update returned 200, appeared through the block API, and
  survived a fresh process.
- Two archival writes were readable through the agent archive and survived the
  fresh process.
- Cross-organization reads of the agent, block, and archive returned 404 before
  restart, and the isolation check remained true afterward.
- After explicit passage, archive, and block deletion, the public resources
  returned 404 and direct PostgreSQL counts for `archival_passages` and
  `"block"` were zero.
- Both repeats produced the same semantic projection at
  `25b09cf3288e045afcb71908b03af97f898dab2ea8921e64506ba8d5234a8f3a`.

These controls establish the tested API and lifecycle boundary. They do not
establish autonomous paging quality, retrieval quality, or production safety.

## Reproduced admission failures

### Core mutation and compiled prompt update are not one recoverable transaction

The doctor injected failure into the system-message update after the block
mutation. In both clean states, the public PATCH returned HTTP 500 while a
subsequent public block read contained the failed-update canary and the agent's
compiled system message did not. After restart the block mutation remained.
Retrying the update with the same block value returned 200 and repaired the
compiled prompt, showing that manual retry can converge but that the original
error response left split durable state.

The normal, failed, and repair PATCH latencies were respectively 108.80, 85.89,
and 99.67 ms in repeat one, and 106.60, 81.83, and 99.56 ms in repeat two. These
are matched-path diagnostics from one contained host, not performance claims.

### Payload-equivalent archive retry is not idempotent

In each repeat, two POSTs carrying the same archive canary both returned 200 and
created distinct passage IDs. Both passages survived the fresh server process.
The first and retry writes took 114.00 and 87.36 ms in repeat one, and 112.21
and 72.76 ms in repeat two. The timing difference is descriptive only; the
admission failure is the duplicate durable effect with no idempotency boundary.

### Agent deletion retains resources; logical purge does not erase stopped storage

Deleting the agent returned 200 and made the agent unreadable, but its archive,
two passages, and two core blocks remained readable. The doctor then used the
native public endpoints to delete both passages, the archive, and both blocks.
All became logically absent and the current table counts reached zero.

After a controlled PostgreSQL stop, the doctor scanned 1,563 files and
68,272,020 bytes in each repeat. Every archive, failed-core, initial-core,
normal-core, and persona canary remained in both a current relation file or
equivalent heap path and `pg_wal/000000010000000000000001`. This is a bounded
plaintext-residue observation after logical deletion. It is not a claim about
secure media erasure, storage reuse over time, managed Letta Cloud, or encrypted
deployment configurations.

## Pre-result diagnostics retained

Jobs `348` through `350` are not scientific results:

- `348` stopped before a lifecycle result because the staged runner could not
  import the contract validator from its execution location.
- `349` verified exact image/source identity, then stopped on obsolete admin
  route assumptions before treatment.
- `350` completed the initial treatment but the cleanup instrumentation queried
  a nonexistent plural `blocks` table instead of the exact ORM table `"block"`.

Each attempt has a distinct output path. Job `351` hash-bound the validator,
used the corrected versioned routes and ORM table name, completed all three
phases twice, and is the only run used for this decision.

## Claim boundary

This is exact pinned legacy Letta V1 evidence for public core-block and
archival-memory lifecycle, official-image/source identity, organization
isolation, fresh-process restart, injected message-update failure semantics,
payload-equivalent retry, agent/resource deletion, stopped PostgreSQL plaintext
scan, and matched local operation diagnostics. It is not evidence about
semantic memory quality, autonomous paging policy, live-model behavior,
concurrent serving, managed Letta Cloud, the separate Letta Code MemFS runtime,
secure media erasure, H100 quality, or publication readiness.

## Next admissible gate

Do not run an H100 actor for `ff19ffe`. Admit only a newer immutable legacy V1
revision or an explicitly reviewed repair arm that:

1. makes block persistence and compiled-message rebuild one recoverable
   transaction;
2. defines an idempotency key and replay result for archive writes;
3. specifies ownership and teardown for agent-linked archives and blocks;
4. provides physical purge or cryptographic erasure with a testable contract;
   and
5. passes this same two-clean-state, fresh-process doctor before any semantic
   quality comparison.

Evaluate current Letta Code MemFS under its own contract rather than treating it
as a repair for the legacy server.

## Evidence

- Portable receipt:
  `research/evidence/memory/memgpt-letta-native-lifecycle-negative-v1.json`
  (SHA-256
  `81bee6fa8115d62c527e6972d8c5ae0880de65a1743c6feb445f78ce6537a117`)
- Raw run root:
  `data/results/memgpt-letta-lifecycle/2026-08-31-slurm-cpu-v4`
- Report SHA-256:
  `78737148ddd6bb49cd23edee076414dcd5e02d18cf24f8114883a04f414d4c18`
- Manifest SHA-256:
  `525f19a1a6183ebedf78ceeeb4bd8a1e922fe44c86cd3e763894117fb9e4090d`
- Contract:
  `experiments/memory/stage3-memgpt-letta-native-lifecycle-doctor.yaml`
