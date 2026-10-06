# Sage Wiki published-artifact audit — 2026-08-17

Status:
`SAGE_WIKI_RELEASED_ARTIFACTS_AUDITED_BINARY_AND_RETRIEVAL_PROVENANCE_MISSING`

This is a zero-API, zero-LLM audit of committed benchmark bytes. It is not a
binary-bound benchmark rerun, retrieval reproduction, independent regrade,
graph ablation, memory-quality result, or publication result.

## Bound inputs

- Sage Wiki revision `78b71575834750962d14265550a099ac64426d91`
- Tree `f04621c7f2821bd70fa2da27f5736473d1662a42`, tag `v0.2.9`
- Git archive SHA-256 `1f9c349efb2fac7a20b790b8e6dee66f03c773522e5cd36905c07b06cbfbcf44`
- MIT license SHA-256 `a0488807e16c1976de2d2408e793af5cd5e889de35f7fa4a11086c1da4683615`
- Ten committed result artifacts: three BEAM, four LoCoMo, and three
  LongMemEval files
- LongMemEval-S SHA-256
  `d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442`
- LoCoMo-10 SHA-256
  `79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4`
- Go 1.26.6 binary SHA-256
  `a1c83801d1756c3eca78366c6b585f2c21c20694fb1c7eb92c446a0580420412`

## Deterministic findings

- Both audit repetitions produced byte-identical report and semantic
  projection files. Projection SHA-256:
  `9d4c35cca58d04ccf95908a8b4db1269c0c20c4b0bfc6c2d3447f478bf63e954`.
- Every stored overall, group, cutoff, and latency aggregate recomputes from
  the per-question rows using the committed formulas.
- All 45 machine-readable `REPORT.md` annotations match the committed result
  files.
- All 61 LongMemEval artifact rows match the pinned LongMemEval-S dataset and
  its seed-42 stratified sample. All 3,235 LoCoMo artifact rows match the pinned
  LoCoMo-10 questions, answers, categories, conversations, and registered
  sample policies.
- The exact source passed 158 Python evaluation tests. Six focused Go packages
  passed 359 tests with 18 skips and zero failures.

## Provenance and validity boundaries

- Every result reports `sage-wiki dev (commit none, built unknown)`, so none is
  bound to revision `78b7157`.
- Result serialization strips retrieval IDs and text. Multi-cutoff files also
  report `retrieved_count: 0` while retaining positive
  `memories_evaluated` counts. Compiled projects, databases, and manifests are
  absent, so retrieval cannot be regenerated.
- Provider strings such as `gpt-5` and `gpt-4o-mini` do not identify immutable
  model snapshots. Raw responses, request IDs, and provider fingerprints are
  absent, and no provider-distinct judge has been run.
- BEAM is loaded from a mutable Hugging Face dataset without a revision. Its
  committed roster is internally auditable but not independently source-bound.
- `locomo_full` has 1,540 rows but reports only 152 answerer and judge calls and
  compile metadata only for conversation zero. `locomo_parity` has 529 scored
  rows and 1,011 infrastructure errors. Neither supports a clean full-run cost
  or parity claim.
- Retrieval depth, answerer, judge, prompts, and samples changed across
  generations. There is no matched flat arm, so no graph-retrieval mechanism
  effect is identified.

## Decision

Record `local-artifact-audited`, mark the portfolio candidate
`artifact-audited-not-reproduced`, and remove this revision from H100 execution
order. The next admission gate is an exact-source common-construction full-task
comparison of flat, lexical/vector, and graph retrieval at matched actor,
top-k, injected bytes, calls, and judge. It must retain retrieval IDs/text and
bind immutable binary, image, SBOM, dataset, and provider receipts.

The self-contained receipt is
`research/evidence/memory/sage-wiki-published-artifact-audit-v1.json`, SHA-256
`eeb7f14c189f540b15493d5db8af7a9b14d11d106f349c9fb609152a72f01cef`.
