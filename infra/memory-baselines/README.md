# Native memory baseline images

Each open-source system runs in its own image behind `memory-system-v1`. The
main harness owns randomization, task redaction, budgets, outcome evaluation,
and artifacts. A native image sees only ordered prefix events, the current
query, an opaque session scope, and the registered budget.

## MemPalace raw-retrieval candidate image

The MemPalace image is a separate retrieval-reproduction lane, not a persistent
`memory-system-v1` service. It binds repository commit
`906b918a7c6ebb2a9198a6bf5a78f30a173fea56`, the current `uv.lock` (ChromaDB
1.5.7 and ONNX Runtime 1.24.4), the exact raw LongMemEval runner, and Chroma's
SHA-verified `all-MiniLM-L6-v2` ONNX archive. The model artifact is prepared by
`scripts/prepare_chroma_minilm.py` and copied as a named build context; runtime
networking is forbidden.

```bash
uv run python scripts/prepare_mempalace_source_context.py \
  --checkout "$CLEAN_MEMPALACE_CHECKOUT" \
  --output-dir "$MEMPALACE_SOURCE_CONTEXT"
uv run python scripts/prepare_chroma_minilm.py \
  --output-dir "$MINILM_CONTEXT" \
  --allow-network
uv run python scripts/build_mempalace_container.py \
  --cotcodec-image "$COTCODEC_IMAGE" \
  --source-context "$MEMPALACE_SOURCE_CONTEXT" \
  --minilm-context "$MINILM_CONTEXT" \
  --tag "$MEMPALACE_IMAGE" \
  --execute
```

The source preparer requires the official origin, exact commit/tree, and a
completely clean checkout. It verifies the deterministic Git archive and every
one of the 555 source files before emitting the named context. The build wrapper
rejects a mutable CoTCodec base **before invoking Docker**; the Dockerfile then
repeats the source/model checks. `COTCODEC_IMAGE` must be an immutable
`registry/name@sha256:<64-hex>` reference, and the reference is bound into the
final image label and runtime receipt. Direct `docker buildx` is not an admitted
build path for this lane. The wrapper explicitly uses BuildKit host networking
only while resolving the hash-locked Python environment; the final image and
all reproduction jobs remain network-disabled.

After a live build, image-bound Syft SBOM, and runtime receipt exist, submit the
CPU-only reproduction through its fixed workload compiler:

```bash
uv run python scripts/submit_mempalace_cpu_job.py \
  /shared/cotcodec/manifests/mempalace-current-lock.yaml --dry-run
uv run python scripts/submit_mempalace_cpu_job.py \
  /shared/cotcodec/manifests/mempalace-current-lock.yaml --test-only
uv run python scripts/submit_mempalace_cpu_job.py \
  /shared/cotcodec/manifests/mempalace-current-lock.yaml
```

The batch requests no GRES and never passes `--gpus` to Docker. It rehashes the
dataset, runtime receipt, active batch script, live image ID, and OCI labels;
runs network-disabled/read-only; locks one persistent study ID; and forwards
Slurm USR1 to the per-question checkpoint handler. A fresh job with the same
study ID resumes `/outputs/run` byte-for-byte. This lane is retrieval-only; the
matched actor remains a separate H100 job.

The entrypoint is the hash-chained, USR1-resumable exact-function driver. The
image remains a non-publication candidate until live image inspection, an
image-bound SBOM, the external source-context receipt, and the MiniLM receipt
are sealed into the runtime receipt consumed by the job. See
`research/mempalace-intake-2026-08-14.md`. Do not use this lane to claim CRUD,
paging, persistence, graph memory, consolidation, or answer quality.

## Mem0 discovery image

The first adapter binds Mem0 `2.0.18` at commit
`71f2ebefa3494da21550fb525216818776cde67f`. It uses `infer=False` to measure
the native vector store and retrieval path without silently giving Mem0 extra
LLM calls. Full LLM extraction/update is a separate diagnostic cell.

Adapter v2 persists Qdrant and Mem0 history under a hashed per-session directory.
An fsynced event journal makes repeated prefixes idempotent, rejects divergent
prefixes in the same scope, and exposes an `inspect` receipt. Purge calls native
delete/reset, closes Qdrant and SQLite, removes only that hashed scope, and then
proves zero remaining state across a fresh process. Run the executable doctor:

```bash
uv run --extra memory-mem0 python scripts/validate_mem0_persistence.py
```

The Dockerfile requires two immutable inputs:

1. `COTCODEC_IMAGE`: the digest-pinned research image built from the same clean
   CoTCodec commit; and
2. the BuildKit named context `mem0_source`: an archive of the reviewed Mem0
   commit whose SHA-256 is
   `c577ecf9a460b0fa581032037ccbfd887f7a7d0afa0fc091d13fd8b692089b12`.

Build only from a source context emitted by the source-preflight workflow:

```bash
docker buildx build \
  --build-arg COTCODEC_IMAGE="$COTCODEC_IMAGE" \
  --build-context mem0_source="$MEM0_SOURCE_CONTEXT" \
  -f infra/memory-baselines/mem0/Dockerfile \
  -t "$MEM0_IMAGE" .
```

Publication launch must pass the resulting OCI digest, the source-archive
digest, and the common embedding-model receipt to the sidecar. The handshake
fails in `COTCODEC_PUBLICATION_MODE=1` when any is missing. GPU-backed embedding
or construction-model services run as scheduler-owned jobs; the adapter itself
is CPU-only and must not perform compute on a login node.

The local lifecycle doctor is not publication evidence. Discovery Slurm job 122
also passed this exact lifecycle in a network-disabled, read-only Docker image on
one H100. It binds CoTCodec source archive
`a3aa58e8415f8d63220a705514cf3b656345be8924fc23eb5171d109d12ba285`,
image `sha256:51067ef74ab12573f867dc369aae68796ef9f8b31d16a3642042a4a8310678e3`,
and locked-wheel manifest
`7471c56fdc8e34a9866ab0971588fbe9256e3187115fc73544f1df27c2463f1c`.
The job committed 27 events into 26 native records, preserved the journal and
retrieved evidence across process restart, rejected a byte-divergent committed
prefix without changing the journal, then proved the scoped state remained
absent after purge and another restart. This is native lifecycle-conformance
evidence only: the source tree is still dirty, the image has no SBOM, and no
matched memory-quality or cross-tenant/poisoning study has run.

## Graphiti discovery image

The Graphiti adapter binds version `0.29.3` at commit
`401c59a65bdeb22a44136901ff30231e6998a7fe`. Its discovery cell uses explicit
temporal triplets and FalkorDBLite 0.10.0, with reranking disabled. A
deterministic deduplication fixture exercises the Graphiti/FalkorDB interface
without silently spending construction-model calls; the common Qwen3.5 4B
construction model is a later matched diagnostic.

Prepare the reviewed source context and build it as a named input:

```bash
uv run python scripts/prepare_memory_baseline_context.py \
  graphiti "$GRAPHITI_SOURCE_CONTEXT"
docker buildx build \
  --build-arg COTCODEC_IMAGE="$COTCODEC_IMAGE" \
  --build-context graphiti_source="$GRAPHITI_SOURCE_CONTEXT" \
  -f infra/memory-baselines/graphiti/Dockerfile \
  -t "$GRAPHITI_IMAGE" .
```

The exact source archive is
`9cfbc01e90f4e6dfbf61fefe86e7f04b15c57c08a7ff8298f873d6f5696d0303`.
Publication mode requires that source context plus OCI and embedding-model
receipts. No image attestation is claimed while the local Docker daemon and
remote Slurm/Pyxis path remain unavailable.

## LangMem discovery image

The LangMem adapter binds version `0.0.30` at commit
`29cbe41e58528f92e9efa773c12e15c47be3808c`. It uses LangMem's public memory
management and search tools over the locked LangGraph 1.2.11 in-memory store.
The discovery cell performs explicit source-attributed CRUD and disables the
LLM background manager; manager quality is tested later with the same Qwen3.5
construction model used by other systems.

```bash
uv run python scripts/prepare_memory_baseline_context.py \
  langmem "$LANGMEM_SOURCE_CONTEXT"
docker buildx build \
  --build-arg COTCODEC_IMAGE="$COTCODEC_IMAGE" \
  --build-context langmem_source="$LANGMEM_SOURCE_CONTEXT" \
  -f infra/memory-baselines/langmem/Dockerfile \
  -t "$LANGMEM_IMAGE" .
```

The exact source archive is
`24c85c514c80bb263a16626971e8ef53978fd1bc7f9319e47d8a5a0bf4956521`.
Publication mode requires source-context, OCI-image, and embedding-model
receipts. The current local CPU artifact deliberately fails that gate.

## Hindsight discovery image

The Hindsight adapter binds version `0.9.0` at commit
`5781d28d8fcc717a15818330b12250b311957000`. It has an isolated lock because
its Protobuf 7.35.1+ requirement conflicts with Mem0's Protobuf `<7` ceiling.
The CPU diagnostic uses embedded PostgreSQL, LLM-free chunk retention, native
recall, and RRF passthrough; reflect and fact extraction are later common-model
cells.

The reviewed source commit contains an absolute development-machine
`node_modules` symlink. The source-context compiler rejects broad unsafe links
and excludes only the exact path registered in the experiment contract.

```bash
uv run python scripts/prepare_memory_baseline_context.py \
  hindsight "$HINDSIGHT_SOURCE_CONTEXT"
docker buildx build \
  --build-arg COTCODEC_IMAGE="$COTCODEC_IMAGE" \
  --build-context hindsight_source="$HINDSIGHT_SOURCE_CONTEXT" \
  -f infra/memory-baselines/hindsight/Dockerfile \
  -t "$HINDSIGHT_IMAGE" .
```

The exact source archive is
`993a015782322ab0fd336b6ab457d895d74d941390e36ebfd562dec9790bdf9c`.
Publication mode requires source-context, OCI-image, and embedding-model
receipts. The current local CPU artifact deliberately fails that gate.
