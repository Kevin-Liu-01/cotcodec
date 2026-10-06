# MemPalace raw-retrieval intake

Date: 2026-08-14  
Status: current-lock retrieval and 500-task mechanism-port equivalence reproduced as discovery evidence  
Scientific result: false

## Decision

Admit MemPalace only as a **raw user-only per-session retrieval floor** in two
separate lanes:

1. an upstream current-lock reproduction of the released LongMemEval raw runner;
2. a matched CoTCodec mechanism port feeding the same frozen actor and judge as
   every other memory control.

Do not describe either lane as an active/inactive pager, CRUD system,
consolidator, graph memory, persistent lifecycle, or end-to-end QA system. The
first lane measures retrieval recall. The second measures the downstream value
of user-only session evidence under our top-k and token budgets.

## Verified primary-source receipt

| Item | Bound value |
| --- | --- |
| Repository | <https://github.com/MemPalace/mempalace> |
| Commit | `906b918a7c6ebb2a9198a6bf5a78f30a173fea56` |
| Tree | `98789ad017781f52550b511fcedd9e00c3346761` |
| Commit date | `2026-08-12T22:27:16-03:00` |
| License | MIT; `LICENSE` SHA-256 `81dc6cc278d80f0f1b028ecd86af30d61e441b9ae53d9d9a2ed19389ba657a5d` |
| Uncompressed Git archive | 64,962,560 bytes; SHA-256 `efbc106cb344a1c5031268909adc2fb5c11cc783ec61adccbe3da0867b4d25c7` |
| Raw runner | [`benchmarks/longmemeval_bench.py`](https://github.com/MemPalace/mempalace/blob/906b918a7c6ebb2a9198a6bf5a78f30a173fea56/benchmarks/longmemeval_bench.py); SHA-256 `c4b4ba3da9e2d7e0e3f27bc93918877fe5f46e202be9ff98b1e90c7e0124628d` |
| Current lock | SHA-256 `9cea6756cee6b4a4c24d03c23e92116e62479d0d062c1cd3af8da806d1aeb4da`; ChromaDB 1.5.7, ONNX Runtime 1.24.4 on Python 3.11+, NumPy 2.4.4, tokenizers 0.22.2 |
| Dataset | `xiaowu0162/longmemeval-cleaned@98d7416c24c778c2fee6e6f3006e7a073259d48f`, `longmemeval_s_cleaned.json`, 277,383,467 bytes, SHA-256 `d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442` |
| Default embedding | Chroma 1.5.7 `all-MiniLM-L6-v2` ONNX archive, SHA-256 `913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3`, 384 dimensions, 256-token truncation, attention-weighted mean pooling and L2 normalization |
| Chroma embedding source | [`onnx_mini_lm_l6_v2.py`](https://github.com/chroma-core/chroma/blob/1.5.7/chromadb/utils/embedding_functions/onnx_mini_lm_l6_v2.py) |

The raw runner creates a fresh Chroma collection for each question. It joins
only user turns with newlines into one document per session, embeds all session
documents, embeds the question, asks Chroma for the top 50, and scores the
returned session IDs. Assistant turns are discarded. Reference answers are read
only after retrieval for scoring, but the released JSONL includes those answers
and therefore remains quarantined from actor inputs.

## Released artifact audit

The committed file
`benchmarks/results_mempal_raw_session_20260414_1629.jsonl` is 13,113,499 bytes,
has SHA-256
`2b71b5e514279c28443736561e2ac453045520b0f8832ff092e8a6143965e5d1`,
contains 500 unique question rows, and stores 483 custom `recall_any@5` hits and
491 custom `recall_any@10` hits. This verifies the released artifact's headline
arithmetic; it does not reproduce retrieval.

The artifact was introduced at commit
`61d02e10fe23ce102b11c64fff91f50da55f5dd7`, whose lock SHA-256 is
`c6eb70271a40ddcba3204fe451574ebe579bf87b23d557111b1293776cefb545`
and resolves ChromaDB 0.6.3. The current pin resolves ChromaDB 1.5.7. No retained
receipt proves the old rankings came from the current lock, so a current-lock
reproduction is mandatory.

The 96.6% headline is MemPalace's **any labeled session in top five** metric.
The official LongMemEval script excludes `_abs` tasks and reports
`recall_all@5`. The upstream result rows omit `recall_all`, and their NDCG
normalization differs from the official utility. Never call 96.6% “official
LongMemEval R@5.” `scripts/audit_mempalace_upstream_artifact.py` verifies all
input hashes, rejoins rows to the pinned dataset, recomputes both definitions,
and emits `UPSTREAM_ARTIFACT_AUDITED_NOT_REPRODUCED`.

The verified 500-row audit excludes 30 abstention tasks for official metrics.
Across the remaining 470 questions it recomputes official `recall_all@5` as
85.7447%, `recall_all@10` as 93.4043%, NDCG@5 as 87.4322%, and NDCG@10 as
89.0094%. The same artifact retains custom `recall_any@5` 96.6% and
`recall_any@10` 98.2%. Duplicate source session IDs are counted with the exact
official corpus-entry multiplicity. These are integrity recomputations of the
released historical artifact, not a current-lock reproduction.

Official metric sources are pinned at LongMemEval commit
`9e0b455f4ef0e2ab8f2e582289761153549043fc`:

- [`print_retrieval_metrics.py`](https://github.com/xiaowu0162/LongMemEval/blob/9e0b455f4ef0e2ab8f2e582289761153549043fc/src/evaluation/print_retrieval_metrics.py), SHA-256 `58b70c0b562ea57372a7774a554c347cd908e901b77ac0149fc90b097b6f1b8f`;
- [`eval_utils.py`](https://github.com/xiaowu0162/LongMemEval/blob/9e0b455f4ef0e2ab8f2e582289761153549043fc/src/retrieval/eval_utils.py), SHA-256 `c98b8d1096877a15aa755c9de44fe33c195298466a2eb6f3c0f9f6bde8c72349`.

## Lane A: exact upstream current-lock reproduction

This is a CPU-only retrieval workload. It must still run in Docker under Slurm,
but assigning an H100 would add no scientific value because the registered ONNX
provider is `CPUExecutionProvider`. H100s are reserved for the identical frozen
actor in Lane B.

Build a benchmark-specific image from the exact Git archive and `uv.lock`. The
official runtime image is insufficient because `.dockerignore` excludes
`benchmarks/` and the runtime copies only the virtual environment. The image
must:

- use digest-pinned base images;
- reject mutable CoTCodec base tags and bind the exact
  `name@sha256:<64-hex>` reference into the image label and runtime receipt;
- retain the exact runner at
  `/opt/mempalace/source/benchmarks/longmemeval_bench.py`;
- fetch and hash the MiniLM archive during the networked build/prestage phase;
- record the extracted model-tree root and force `CPUExecutionProvider`;
- include an SPDX or CycloneDX SBOM bound to the immutable image;
- run with no network, read-only root, dropped capabilities, no new privileges,
  a read-only dataset/model cache, and a persistent output mount.

The source and model prestages are executable and idempotently verifiable:

```bash
uv run python scripts/prepare_mempalace_source_context.py \
  --checkout /shared/cotcodec/sources/mempalace-906b918a \
  --output-dir /shared/cotcodec/contexts/mempalace-906b918a
uv run python scripts/prepare_mempalace_source_context.py \
  --output-dir /shared/cotcodec/contexts/mempalace-906b918a \
  --verify-only
uv run python scripts/prepare_chroma_minilm.py \
  --output-dir /shared/cotcodec/models/chroma-all-minilm-l6-v2 \
  --allow-network
uv run python scripts/prepare_chroma_minilm.py \
  --output-dir /shared/cotcodec/models/chroma-all-minilm-l6-v2 \
  --verify-only
```

The source preparer requires the official origin, exact commit/tree, and a clean
checkout; it verifies the deterministic archive and all 555 Git files. The
model preparer rejects archive traversal, links, special files, duplicates,
extra files, missing files, SHA drift, receipt drift, and post-extraction mutation. The
candidate image at `infra/memory-baselines/mempalace/Dockerfile` consumes the
verified model and exact MemPalace source as named build contexts, resolves the
current lock, verifies ChromaDB 1.5.7 and ONNX Runtime 1.24.4, and labels every
source/model identity. It remains explicitly non-publication-ready until a live
build, immutable repository digest, image-bound SBOM, and externally verified
runtime receipt exist.

The only admitted build entry point is `scripts/build_mempalace_container.py`.
It validates the immutable CoTCodec base reference and both context receipts
before Docker can resolve a `FROM`; the in-Docker checks are defense in depth.
Direct `docker buildx` is discovery-only and cannot produce an admitted receipt.

The scheduler seam is `scripts/submit_mempalace_cpu_job.py` plus
`infra/slurm/host-single-node/mempalace-cpu.sbatch`. It accepts no arbitrary
workload command, requests zero GPUs, mounts only the exact dataset/runtime
receipt and persistent study directory, revalidates live image labels, runs
with network disabled and a read-only root, serializes one study with `flock`,
and forwards USR1 to the durable per-question checkpoint. Its manifest declares
finite wall-time and CPU-hour ceilings. Contained discovery jobs 208-211 built
and doctored the candidate runtime and processed all 500 tasks; job 212 matched
the direct and port paths on all 500 task/query/session/ranking contracts, and
fresh job 213 revalidated the completed bundle without changing artifact hashes.
These jobs remain dirty-source and self-attested rather than publication evidence.

`scripts/run_mempalace_upstream_reproduction.py` imports the exact pinned
`build_palace_and_retrieve` function only after verifying its source hash. Each
call receives a strict four-field allowlist (question, haystack sessions,
session IDs, and dates), so answers, answerability labels, and future benchmark
metadata cannot reach the retriever. The wrapper fsyncs a hash-chained record
after every question. `SIGUSR1` stops only after a durable question boundary and
writes the scheduler checkpoint marker; a fresh job verifies and resumes the
chain without resampling or dropping a task. Completed-bundle resume recomputes
every result, progress, journal, manifest, and file-roster binding rather than
trusting a self-authored status file.

Run the wrapper twice in fresh output directories:

```bash
/workspace/.venv/bin/python scripts/run_mempalace_upstream_reproduction.py \
  --source-root /opt/mempalace/source \
  --dataset /inputs/longmemeval_s_cleaned.json \
  --runtime-receipt /inputs/mempalace-runtime.json \
  --output-dir /outputs/run-a \
  --resume
```

Then run the artifact auditor inside the same image:

```bash
/workspace/.venv/bin/python scripts/audit_mempalace_upstream_artifact.py \
  --source-root /opt/mempalace/source \
  --dataset /inputs/longmemeval_s_cleaned.json \
  --result /outputs/raw-current-lock.jsonl \
  --output /outputs/raw-current-lock-audit.json
```

The exact auditor defaults bind the released artifact, so the current-lock run
will require a separately sealed reproduction comparator accepting the new file
hash while holding every source/runtime constant. Do not overwrite or relabel
the released artifact.

### Lane A gates

1. Both fresh runs have byte-identical ordered session IDs for all 500 tasks.
2. The current-lock run reproduces 483/500 custom `recall_any@5`; otherwise the
   historical result is not reproduced and the version delta is reported.
3. Recompute and report official non-abstention `recall_all@5`, `recall_all@10`,
   and official NDCG beside the custom any-hit values.
4. Permuting `answer` and `answer_session_ids` leaves every ranking identical.
5. Mutating only assistant turns leaves every raw ranking identical.
6. Missing the exact model archive, CPU provider, runner, lock, dataset, image,
   SBOM, or source receipt fails closed.
7. No `--skip`, auto-created split, alternate embedder, reranker, diary, hybrid,
   or silent fallback is allowed.

## Lane B: matched CoTCodec mechanism port

`harness/memory_trials/mempalace_control.py` implements the deep public
contract. It receives only `MemorySystemRequest`, groups append-only `key=user`
events by opaque session entity in event order, joins each session with
newlines, and delegates ranking to `MemPalaceRetrievalPort`. It rejects update,
delete, access, and other lifecycle events. The response cites every contributing
user event, fits top-k=4 into the 256-token actor budget, and charges one session
document write per session, one read, every document embedding plus the query,
serialized bytes, and latency.

The production port must run the pinned Chroma 1.5.7 and MiniLM artifacts inside
the dedicated offline image. Unit tests use a fake port through the identical
contract; they are interface evidence only. Until all 500 direct-runner and port
rank lists match, label this a **mechanism port**, not an upstream reproduction.

Freeze all 500 selections, then feed that bundle to the same all-SERVE
Qwen3.6-35B actor and official GPT-4o judge contract as no-memory, BM25,
raw-log-RRF, dense-BGE, profile, and graph controls. The full-prefix ceiling is
diagnostic and unmatched.

### Lane B gates

1. Exact task/source/budget/treatment manifests match every other control.
2. Direct runner and port ranks match all 500 tasks before “faithful port” wording.
3. User-turn source attribution is complete; assistant source IDs never appear.
4. Candidate storage/service treatment remains engine-owned and task blind.
5. Every eligible control covers all 500 tasks through one actor and judge.
6. Compare paired task-level official semantic accuracy and retrieval metrics;
   do not rank systems by retrieval-any alone.
7. If MemPalace does not beat the existing dense-BGE/raw-log controls at matched
   actor budgets, kill it as a redundant primary control. A null result is valid.

## Required receipts

- MemPalace commit, tree, archive, license, runner, lock, and exact file manifest;
- LongMemEval revision, filename, byte size, SHA-256, license, and task roster;
- MiniLM URL, archive SHA-256, extracted-tree root, tokenizer/model file hashes,
  dimensions, maximum tokens, pooling, and ONNX provider;
- Python/platform and exact resolved package/wheel hashes;
- Dockerfile, immutable base/final image digests, labels, SBOM, and runtime policy;
- Slurm job/allocation/system/command/environment and output logs;
- ordered per-task ranking root, output hash, custom and official metric-code hashes;
- actor/model/bundle/prompt/decoding receipts and official judge receipts;
- cost ledger and termination/checkpoint lineage.

## Current blockers

- Two fresh direct current-lock runs reproduce identical ordered rankings on all
  500 tasks. Their sealed comparison report has SHA-256
  `a94bbfbfcd8b8f2d1105b18711989143fabb6338951700823783d46ca01bd6fe`.
- Contained Slurm job 212 executed the production port on one H100 and matched
  the upstream runner on all 500 tasks for query bytes, session roster, session
  order, session text, full ranking, top five, and top ten. The journal and
  report SHA-256 values are `5d6961ae4d54f84e7ce20c6faa5c71691a420000437e1860e4c2e977ffbf734d`
  and `685afc9550b9b61481606e26a1b9b10b60f1ec8024c62795345402e4c16d97a9`.
  Fresh Slurm job 213 revalidated the completed bundle without changing its
  hashes. This closes the direct-runner-equivalence gate.
- The passing v19 image and runtime are discovery artifacts from source archive
  `9308bd65...`; the runtime/SBOM receipt is self-attested and the shared tree is
  dirty. Rebuild and rerun from a clean, externally attested publication capsule
  before treating the transport as publication provenance.
- Failed v17/v18 runs are retained. They exposed duplicate raw session IDs with
  distinct timestamps and empty user turns before v19 preserved both semantics.
- The complete LongMemEval actor/judge publication wave remains blocked on a clean
  committed source archive, externally attested image/SBOM/runtime, complete
  matched bundle roster, and external administrator signature.

No answer-quality actor or API judge has executed. The completed H100 cells are
retrieval-reproduction and mechanism-equivalence evidence only, with
`scientific_result: false`.
