# Variable 2: Reasoning Format

**Status:** Partially overlaps Paper 1 (structured English condition). Now MASSIVELY elevated
by IBM Research's Abstract Chain-of-Thought (April 2026). Natural Paper 2 candidate — possibly
the single most important direction after language.

## The Variable

σ = format ∈ {free_form_cot, structured_protocol, symbolic_cot, program_of_thought, compressed_telegraphic, xml_tagged, json_reasoning, **abstract_cot**}

## Intervention

Control how the model structures its intermediate reasoning — not which
language, but which format. Free-form prose vs. structured key-value vs.
symbolic logic vs. executable pseudocode.

## Why It Matters

Cuadron et al. show overthinking hurts agent performance. The format of
reasoning directly affects:
- How many tokens reasoning consumes
- Whether reasoning is parseable by downstream components
- Whether the model stays on track or drifts
- How easily errors can be diagnosed

The structured English condition from Paper 1 is already testing this.
A dedicated study would isolate format from language.

## BREAKING: Abstract Chain-of-Thought (Ramji et al., IBM Research, April 2026)

**Paper:** "Thinking Without Words: Efficient Latent Reasoning with Abstract Chain-of-Thought"
**URL:** https://arxiv.org/abs/2604.22709
**Source tweet:** https://x.com/KeshavRamji/status/2048743883580817620

### What it is

Instead of reasoning in natural language (English, Chinese, structured, compressed),
the model reasons through a short sequence of **reserved abstract tokens** from a
learned vocabulary. The abstract tokens are NOT natural language — they are a newly
introduced discrete codebook (64 tokens like `<A>`, `<B>`, `<AE>`, etc.) that the
model learns to use as a "latent scratchpad" via RL.

### Key results

| Benchmark | Verbal CoT tokens | Abstract CoT tokens | Compression | Accuracy (Verbal) | Accuracy (Abstract) |
|-----------|-------------------|---------------------|-------------|-------------------|---------------------|
| MATH-500 | ~1100 | ~95 | **11.6x** | 92.6% | 90.6% |
| AlpacaEval | ~290 | ~140 | **2.2x** | 34.3% | **36.7%** (+2.4) |
| HotpotQA | ~350 | ~82 | **4.3x** | 52.8% | 52.4% |
| GPQA-Diamond | ~1382 | ~174 | **7.9x** | 51.5% | 50.5% |
| AIME'25 | ~9343 | ~3438 | **2.7x** | 25.6% | 24.4% |

**11.6x fewer reasoning tokens** while matching verbalized CoT performance.
Sometimes EXCEEDS it (AlpacaEval +2.4 points). This is not compression of
existing CoT — it's an entirely new reasoning pathway via RL.

### Why this changes CoTCodec

Our Variable 2 (reasoning format) now has a fundamentally new point in the
design space. The spectrum is:

```
Natural language CoT (verbose, human-readable)
  → Compressed English (caveman, 65% savings)
  → Structured protocols (key-value, 40-60% savings)
  → Non-English language (Chinese, 20-40% savings)
  → Abstract CoT (learned tokens, 80-92% savings, non-human-readable)
```

Abstract CoT is the logical endpoint of CoTCodec's thesis: if language is a
controllable compression protocol for agent communication, then the most
efficient "language" might not be a human language at all — it might be a
learned discrete codebook optimized via RL.

### Key technical details

- **Codebook:** 64 reserved tokens, max 128 tokens per abstract sequence
- **Training:** Policy iteration warm-up (bottlenecked SFT + self-distillation)
  followed by RL (GRPO) with constrained decoding
- **Cold-start fails:** Random abstract tokens + RL alone doesn't work.
  The warm-up stage (verbal CoT guidance → information bottleneck) is critical.
- **Power law emerges:** Token frequencies follow Zipf's law after RL training,
  suggesting the model learns a genuine "reasoning language" with reuse patterns
- **Permutation-sensitive:** Shuffling abstract tokens degrades performance (-7.8
  on MATH-500), proving order matters — this is compositional, not just filler
- **Generalizes across model families:** Tested on Qwen3-8B, Qwen3-4B, Granite 4.0

### Implications for our research program

1. **Language routing (V1) may be dominated:** If abstract tokens achieve 11.6x
   compression vs. language routing's 20-40%, the Pareto frontier shifts massively.
   Our router's option set must include abstract CoT.

2. **The harness-beats-model thesis (V13) gets even stronger:** Abstract CoT is
   entirely a post-training intervention. Same base model, different reasoning
   format, dramatically different efficiency.

3. **New condition for experiments:** Add `abstract_cot` alongside our 7 existing
   language conditions. This is the strongest baseline we must compare against.

4. **Cold-start problem = orchestration problem:** The paper shows warm-up
   (policy iteration with verbal CoT guidance) is essential. This is literally
   an orchestration variable — how you bootstrap the reasoning format.

5. **Connection to DeepSeek-R1:** The paper cites DeepSeek-R1-Zero's language
   mixing as evidence that "strong performance can be separable from human-
   readability." Same observation that motivated CoTCodec, taken further.

## Conditions to Test (updated)

| Format | Example | Expected compression |
|--------|---------|---------------------|
| Free-form CoT | "I need to check the user's order history first, then verify..." | 1x (baseline) |
| Structured protocol | "PLAN: goal=check_refund, steps=[get_orders, verify_window]" | 2-3x |
| Symbolic CoT | "∀ order ∈ user.orders: order.date > now - 30d → eligible" | 2-4x |
| Program-of-thought | "orders = get_orders(user_id); eligible = [o for o in orders ..." | 2-3x |
| Compressed English | "chk order hist → verify refund elig → process if valid" | 1.5-3x |
| Non-English (Chinese) | "检查用户订单历史 → 验证退款资格 → 处理" | 1.2-1.4x |
| **Abstract CoT** | `<beginabstract> <E> <C> <AE> <F> <A> <BB> <D> <endabstract>` | **4-12x** |

## Key Hypotheses (updated)

1. Structured formats reduce token count AND improve tool-call accuracy
2. Program-of-thought dominates on code-heavy tasks (SWE-bench)
3. Free-form CoT dominates on ambiguous tasks requiring flexible reasoning
4. **Abstract CoT dominates on token efficiency but may degrade tool-call
   accuracy** — the abstract tokens are non-interpretable, so tool argument
   correctness under abstract reasoning is an open question for agent tasks
5. **The optimal reasoning format may be task-dependent** — abstract for
   planning/memory, structured for tool-adjacent, free-form for ambiguous

## Connections

- **Language** — structured English is the intersection. Language Paper 1
  already tests one format variant.
- **Observation granularity** — the format of reasoning affects how much
  of it needs to be retained for the next step.
- **Verification** — structured formats are easier to verify automatically.

## Prior Work

- **Ramji et al. 2026** — Abstract Chain-of-Thought: 11.6x compression via learned discrete codebook (https://arxiv.org/abs/2604.22709)
- **Hao et al. 2025** — Coconut: continuous latent reasoning vectors
- **Shen et al. 2026** — HybridCoT: interleaved latent and text tokens
- **Deng et al. 2024** — Stepwise Internalization: gradually removing CoT steps
- Chen et al. 2022 — Program of Thoughts
- Xu et al. 2024 — Symbolic Chain-of-Thought
- Cuadron et al. 2025 — Overthinking in agentic tasks
- Munkhbat et al. 2025 — Self-training elicits concise reasoning
- Goyal et al. 2024 — Pause tokens for deliberate thinking
- Xia et al. 2025 — Controllable token skipping in CoT

## Community Evidence (from Kevin's X bookmarks — 9 signals)

- **Caveman token optimization** (6.5K bm @om_patel5) — "TEACH CLAUDE TO TALK LIKE A
  CAVEMAN TO SAVE TOKENS" turned into a skill. Benchmarked: 65% average savings, range
  22-87% across 10 tasks. This IS a reasoning format condition. Three intensity levels:
  lite (drops filler), full (drops articles), ultra (maximum compression).
  Repo: github.com/thedotmack/claude-mem
- **Claude Code memory architecture** (8.3K bm @himanshustwts) — three-layer structured
  format: index → topic files → transcripts. The format IS the memory policy.
- **andrej-karpathy-skills** (10.4K bm combined) — Karpathy's LLM failure mode observations
  turned into structured CLAUDE.md rules. Reasoning constraints as format.
