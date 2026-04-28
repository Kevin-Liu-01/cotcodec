# Variable 1: Language

**Status:** Paper 1 (active). Harness built. Pilot experiments next.

## The Variable

σ = ℓ ∈ {English, Chinese, Structured English, Controlled Chinese, Compressed English, Dynamic}

## Intervention

System prompt addendum instructs the model to use a specific language for
intermediate messages. Tool schemas and final responses stay English.

## Why It's Tractable

- No framework modifications required
- Token count is the direct measurement (exact, not approximate)
- DeepSeek-R1, EfficientXLang, Li et al. provide strong priors
- Natural message-type decomposition
- Clean compression baselines (LLMLingua)

## Open Questions

1. Does Chinese reduce tokens after fixed tool overhead?
2. Where do savings arise? (planning, memory, retries, handoffs)
3. Is it tokenization or different reasoning paths?
4. Can structured English beat Chinese on code-heavy tasks?
5. Does a router outperform any fixed language?
6. Safety regressions under multilingual mixing?

## Connections to Other Variables

- **Reasoning format** — structured English is both a language condition
  AND a reasoning format. The boundary is blurry on purpose.
- **Compaction** — language routing is a form of lossy compression.
  Overlaps with prompt compression baselines.
- **Memory policy** — shorter memories in Chinese = more context budget
  for other things. Language and memory interact.
