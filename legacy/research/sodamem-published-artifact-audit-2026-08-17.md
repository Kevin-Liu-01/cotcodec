# SodaMem published-artifact audit — 2026-08-17

Status: `SODAMEM_RELEASED_ARTIFACTS_AUDITED_NOT_REPRODUCED`

This is a zero-API, zero-LLM audit of released bytes. It is not an independent
judge result, retrieval reproduction, construction reproduction, temporal-graph
ablation, or memory-quality result.

## Bound inputs

- SodaMem revision `b182c1a603e47d82ee6e99190aa5022db28077b5`
- Tree `2c6f29b5bcf3a570d7f9d381ce79b8050b7d94d3`
- Git archive SHA-256 `2abd4be8e9af9e3d05d351b5585b5d4c27adee2b93ad9b7af9ca8acfeea170bc`
- Apache-2.0 license SHA-256 `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30`
- Judged artifact SHA-256 `a5f4208b544d28396e38bf0dd3784366f80a6f743194a8f670ac7afbe658df51`
- Retrieved-context artifact SHA-256 `c7000364da353ba91ebb491dcd9dfccc610a4bb17360db60800b7685fcefe168`
- LongMemEval-S revision `98d7416c24c778c2fee6e6f3006e7a073259d48f`
- LongMemEval-S SHA-256 `d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442`

## Deterministic findings

- Both audit repetitions were byte-identical.
- All 500 published questions, answers, and question types align exactly to the
  pinned dataset, including 30 abstention rows and 32 numeric reference answers.
- The stored `deepseek-v4-flash` verdicts recompute to 464/500 (92.8%). This is
  the released self-judge score: reader, planner, and judge use the same model.
- The retrieval artifact contains 8,427 nonempty evidence rows, 10–70 per
  question, with no per-question duplicate evidence IDs and no empty
  `source_trace_ids` lists.
- The answer artifact's documented `evidence_ids` field is boolean `true` on all
  500 rows. It contains zero evidence-ID lists. Cross-file linkage therefore
  relies on the synthetic `q001`–`q500` IDs.
- Full NFKC/casefolded/alphanumeric-normalized reference text occurs in 314/500
  hypotheses and 239/470 non-abstention retrieval unions. These are lower-bound
  string-containment diagnostics, not semantic correctness or support measures.
- The released usage totals are 2,836 provider calls, 8,293,078 prompt tokens,
  881,135 completion tokens, and 9,174,213 total tokens. They do not include a
  reproduced ingest or judging cost.

## Upstream source check

The repository's documented `uv sync --extra dev` path collected tests that
exercise undeclared runtime extras and failed with missing Chroma and provider
modules. Using the exact lock plus the declared `dev`, `chroma`, `llm`, and
`server` extras passed 737 tests with 19 skips. This is package conformance, not
benchmark reproduction.

## Unresolved validity boundaries

- The 12 GB frozen store and ingest inputs are not distributed.
- The measured pre-release construction build predates the public repository
  history.
- The reader input prompt was not captured and cannot be reconstructed exactly
  from the union of retrieved evidence.
- `source_trace_ids` cannot be dereferenced against the absent raw source spans.
- The same-model self-judge requires a provider-distinct regrade.
- No matched flat-history or temporal-graph construction control exists yet.

## Decision

The artifacts are useful, aligned, and independently auditable, but the system
result is not reproduced. SodaMem is removed from H100 execution order. The next
admission gates are:

1. Run a provider-distinct judge over the content-addressed official-prompt
   cases.
2. Freeze identical extraction outputs and compare SodaMem, flat history, and a
   temporal-graph control at matched actor, bytes, retrieval calls, and judge.
3. Only then consider a bounded H100 actor cell.

The self-contained receipt is
`research/evidence/memory/sodamem-published-artifact-audit-v1.json`, SHA-256
`a9e914b2f64a163796d43f5b86755feff1a7cf9504be86d15aef6b5009ba1473`.
