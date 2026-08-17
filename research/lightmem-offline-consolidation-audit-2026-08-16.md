# LightMem exact-source consolidation admission — 2026-08-16

## Verdict

Pinned LightMem revision `8fc9a9179f91` is **not admitted** as an active/inactive
memory system or as an H100 actor candidate. Two clean, network-disabled,
read-only Docker repetitions reproduced the terminal status
`BLOCKED_DESTRUCTIVE_DEFAULT_REOPEN_AND_CONSOLIDATION_CONTRACT_DRIFT` with an
identical semantic projection
`80a2b06c818ece9fce8319c0121d3e951b7469e456ed636b79d6d02f1aa72b56`.

This is a component-level exact-source negative. It does not measure LightMem's
paper-reported answer quality, and it is not a reproduction of the paper.

## Immutable source and runtime

- Repository: `https://github.com/zjunlp/LightMem`
- Git revision: `8fc9a9179f9170c4a40fc653fcb410375900f26e`
- Git tree: `343831b5f0aa1d6dec62cb1c12ed71d9c7ab4a62`
- Git archive SHA-256: `50830e429b65043767f485b5494829715a4c98980f98c1dd4c52c0342e588601`
- Root license: MIT, while `pyproject.toml` declares Apache-2.0
- Root dependency lock: absent
- Image: `sha256:7590709501e0d2cbfadd59284818fd96d1962a3210d26c911b56ebd153fd9b6f`
- Runtime: Linux arm64, non-root UID/GID 65532, `--network none`, read-only
  rootfs, all capabilities dropped, no new privileges, fresh tmpfs state for
  each repetition, no provider/model calls, and no GPU passthrough.

The retained artifact root is
`data/results/lightmem-offline-consolidation/2026-08-16-local-docker-v1`.
`research/evidence/memory/lightmem-offline-negative-v1.json` binds the source
archive, image inspection, doctor code, both reports, and the artifact manifest.

## Reproduced mechanisms and blockers

The doctor imports the pinned source methods while replacing only external
provider/vector dependencies with deterministic test doubles.

1. `LightMemory.online_update` is a no-op and returns `None`; it does not write
   online active memory.
2. The Qdrant adapter deletes an existing local path when `on_disk=False`, which
   is the default used by the official examples and the LongMemEval offline
   update script. Reopening the configured path removed a persisted canary.
3. Automatic offline update calls `offline_update_all_entries` with the unknown
   keyword `update_sim_threshold`; the exact source raises `TypeError`.
4. The actual consolidation direction is later source to earlier target, but an
   updated memory payload retains the target's old embedding vector. Semantic
   retrieval can therefore index stale text after consolidation.
5. The advertised context-only retrieval route still dereferences
   `text_embedder`/`embedding_retriever` and fails without them.
6. The public memory class exposes no scoped `purge`, `delete`, `forget`, or
   `erase` operation, and `MemoryEntry` has no source-event lineage field.

The positive part of the mechanism was also checked: queue construction causes
a later matching memory to update the earlier target. That does not establish
durability, retrieval correctness, lifecycle safety, or memory quality.

## Claim boundary and next gate

LightMem at this pin may remain a paper-level reference for sensory filtering,
topic-aware buffering, and offline consolidation. It must not be described as a
bidirectional active/inactive pager, a persistent online memory system, or an
admitted matched H100 baseline.

Re-admission requires either a newer immutable revision or an explicitly
labeled repair arm that:

- defaults local stores to non-destructive durable reopen;
- implements and persists online writes;
- fixes the automatic offline-update API;
- re-embeds every changed memory payload;
- correctly dispatches context retrieval;
- carries transitive source-event lineage; and
- passes scoped restart, retry/idempotency, isolation, physical purge, and
  residue checks twice in clean contained states.

Only after those CPU lifecycle gates pass should a matched frozen-actor H100
quality cell be considered.
