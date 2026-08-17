# Fidelis zero-LLM retrieval reproduction — 2026-08-17

## Decision

Fidelis revision `0950ff3e6d377b08f02a26045a6508c58a07a1eb`
passes its bounded CPU retrieval gate. On the 470 non-abstention
LongMemEval-S questions, the exact upstream Stage 1b retrieval projection was
reproduced at 391/470 recall-any@1 and 462/470 recall-any@5. Every local top-five
session-ID list and logged score list matched the committed upstream artifact.

This admits Fidelis only as a reproduced retrieval component and candidate for
a future matched common-actor comparison. It does not admit an H100 job by
itself and does not reproduce answer quality, latency, the write path, or the
persistence lifecycle.

## Bound execution

- Source revision: `0950ff3e6d377b08f02a26045a6508c58a07a1eb`
- Source tree: `d50069ac435f801e392c6565f6f9598a415b7e09`
- Deterministic source archive SHA-256:
  `54ef4551964e2f62ff2b8fffcd82d2fffa309b8b3d025b68dfcaa7111dd8b91b`
- License: MIT; license-file SHA-256
  `32272de4bccdba865f5b21f9b83107634c0a90455008db8acb8e62b9ced15598`
- Pipeline SHA-256:
  `6cdafd387e394a4fbbe9bda7c77098f2f571cc16dc91e104acffa7aa44882a66`
- Dataset: `xiaowu0162/longmemeval-cleaned` revision
  `98d7416c24c778c2fee6e6f3006e7a073259d48f`, MIT license,
  277,383,467 bytes, SHA-256
  `d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442`
  (500 source rows; 470 non-abstention questions)
- Upstream per-question artifact SHA-256:
  `aa93767be273060d39d31f4bd22b938a50b27304b4543194c95f3ef1232f2912`
- Upstream aggregate SHA-256:
  `217997e2b60c9035d49d0821e149658da99ba6508ef57039640e32190b989ac6`
- Ollama: official Darwin v0.20.6 archive
  `6ea25ae105a3e807aab1fedad84126f6ffaea4b5eb5d198c98f24bea1d0dd1ba`
  and binary
  `db51a3fb2613fff17235c5123ec5d3f07193068997230c61e1b66cf98a86ca93`
- Embedding artifact: `nomic-embed-text:latest`, locally frozen by manifest
  `0a109f422b47e3a30ba2b10eca18548e944e8a23073ee3f3e947efcf3c45e59f`
  and all four referenced blob digests
- Python: 3.11.15, executable
  `b8014caecb1f334bbc67e99b74d9f5fa6e3519c6567c98a890940b31ffeffa32`
- Dependencies: exact `bm25s==0.3.3` and `numpy==2.4.4` wheel hashes plus
  hashes of both installed package trees
- Host: Apple M5 Max, arm64, macOS 26.4 build 25E246, Darwin 25.4.0
- Execution: four deterministic contiguous shards with
  `OLLAMA_NUM_PARALLEL=4`; interrupted incremental per-question files were
  resumed and restored in original dataset order

Ollama v0.20.6 was selected from the repository's committed reproducibility
section, not inferred by searching for a matching result.

The upstream dependency declaration is open (`bm25s>=0.2`) and the Ollama model
name uses a mutable `latest` tag. The retained receipt therefore binds the
actual wheel, installed-package, manifest, blob, server, Python, and host bytes
rather than treating those names as immutable provenance.

`scripts/prepare_fidelis_zero_llm_shards.py` creates the no-overwrite shard
roster and content-addressed manifest. Each shard runs the exact upstream
`bench/longmemeval_combined_pipeline_v35.py` with `--no-filter` and `--resume`.
`scripts/seal_fidelis_zero_llm_evidence.py` accepts only the exact four shard
rosters and pinned inputs; `scripts/validate_fidelis_zero_llm_evidence.py`
validates the durable receipt without access to the execution workspace.

## Reproduced result

| Metric | Exact result | Upstream rounded result |
|---|---:|---:|
| Questions | 470 | 470 |
| Recall-any@1 | 391/470 = 83.1915% | 83.2% |
| Recall-any@5 | 462/470 = 98.2979% | 98.3% |
| Exact top-five ID-list matches | 470/470 | — |
| Exact logged score-list matches | 470/470 | — |

The local execution forced `--no-filter`. Every row recorded
`route_decision=no_filter`, `filter_called=false`, zero filter time, and an
identical Stage 1/Stage 2 ID list. The referenced upstream run also contains an
LLM-assisted Stage 2, but none of those reranked outputs enter this result. The
repository's 73.0% QA result is a separate upstream claim and was not
reproduced.

## Runtime-drift falsifier

The current official Ollama v0.32.9 Darwin binary was run against the same
source, first question, model manifest, and model blobs. For question
`e47becba`, v0.20.6 placed the gold session first, while v0.32.9 placed it third:
recall-any@1 changed from pass to fail and recall-any@5 remained a pass. The
v0.32.9 archive, binary, and one-question output are hash-bound in the evidence.

This establishes that the Ollama runtime is part of the treatment. It does not
identify which internal runtime change caused the ranking difference and does
not estimate aggregate v0.32.9 performance.

## Instrumentation boundaries

The pinned v35 runner computes `s1_top5_scores` before temporal boosting, then
logs `s1_top5_ids` after temporal boosting. Temporal boosting fired on 90 of
470 questions. ID/score alignment is therefore not guaranteed on those rows;
the exact score match is retained only as a transport/reproduction check, and
all reported hit metrics are recomputed from IDs and gold-session membership.

The runner's resume path reloads prior per-question rows and selected counters
but does not restore retrieval timing or every metric accumulator. The entire
local aggregate is excluded. Counts and rates above are recomputed only from
the restored, exact-roster per-question files and checked against the committed
upstream aggregate's Stage 1b values.

## Claim boundary and next gate

This is a local, self-attested reproduction on a benchmark the repository
explicitly optimized for. The repository's own generalizability review reports
materially weaker behavior on real Claude Code sessions and calls for
out-of-distribution validation. The reproduced object is the committed v35
benchmark driver and Stage 1b artifact; this run does not establish behavioral
equivalence with the packaged service path. No claim is made about general
retrieval, multilingual data, large stores, concurrent writes, latency, QA,
persistence, scoped deletion, physical erasure, network isolation, or
publication-ready external attestation.

The next eligible gate is a preregistered, equal-roster comparison through one
frozen actor against dense-BGE and raw-log controls, with equal top-k, injected
bytes, calls, and judge. It requires a clean publication source capsule,
externally protected attestation, and contained Slurm authority. Until those
exist, no H100 claim cell is admitted.

## Evidence

The self-contained receipt is
`research/evidence/memory/fidelis-zero-llm-retrieval-v1.json`, SHA-256
`32e5327f42bd72dba59aa637cce18ca6a8c71c1be39407c7c287016f458008f0`.
It embeds the canonical 470-row claim projection, exact runtime identities,
shard and run hashes, runtime-drift falsifier, instrumentation findings, and
claim boundary. It validates without the ignored `data/` or `raw/`
directories.
