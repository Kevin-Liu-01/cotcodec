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

## NEW: Abstract-CoT Changes the Landscape (April 2026)

Ramji et al. (IBM Research, arXiv 2604.22709) show that a learned discrete
codebook of 64 abstract tokens achieves 11.6x fewer reasoning tokens than
verbal CoT while matching performance. This is NOT language routing — it's
a completely new reasoning medium.

**Impact on our language paper:**
- Language routing (20-40% savings) may seem modest next to abstract CoT
  (80-92% savings). We must acknowledge this in the paper.
- BUT: abstract CoT requires post-training (warm-up + RL). Our language
  routing is inference-time only — no model modification. Different tradeoffs.
- Abstract CoT has NOT been tested on agent/tool-use tasks. The paper uses
  MATH-500, AlpacaEval, HotpotQA. Our agent benchmarks (tau-bench, MCP-Atlas,
  Toolathlon) test tool correctness, not just reasoning. Open question:
  does abstract reasoning preserve tool argument fidelity?
- Our paper becomes: "language routing is the best inference-time-only
  approach; abstract CoT is the best post-training approach. For practitioners
  who can't retrain, language routing is the answer."

**Framing update:** Language choice is the most accessible orchestration
variable (no training required, just system prompt changes). Abstract CoT
is the most efficient but requires significant post-training investment.
Our routing policy could include abstract CoT as a condition if models
ship with it pre-trained.

## Connections to Other Variables

- **Reasoning format (V2)** — structured English is both a language condition
  AND a reasoning format. Abstract CoT is the extreme end of format change.
  The boundary is blurry on purpose — and getting blurrier.
- **Compaction** — language routing is a form of lossy compression.
  Overlaps with prompt compression baselines.
- **Memory policy** — shorter memories in Chinese = more context budget
  for other things. Language and memory interact.
- **Harness-beats-model (V13)** — abstract CoT is a pure post-training
  intervention. The base model is the same. This is the ultimate evidence
  that format > model.
