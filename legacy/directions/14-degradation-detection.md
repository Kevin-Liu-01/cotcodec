# Variable 14: Degradation Detection

**Status:** New research direction. Directly motivated by Anthropic's April 23, 2026 postmortem.

## The Problem

The 2026 "model quality crisis" revealed that EVERY major provider has
shipped orchestration-level regressions that users perceived as model
degradation. The phenomenon is industry-wide:

| Provider | Degradation | Root cause category | Our variable |
|----------|------------|--------------------|----|
| Anthropic (Opus 4.6, Sonnet 4.6) | Forgetful, repetitive, less intelligent | Effort level, cache bug, verbosity limit | V2, V3, V4, V9 |
| OpenAI (GPT-5) | Lazy outputs, hallucinations ↑, code length ↓ | Token economics, quantization, RLHF caution | V2, V4, V8 |
| Google (Gemini 3.1 Pro) | Formatting ignored, attention drift, robotic | Capacity management, context handling | V4, V5 |
| DeepSeek (V4) | Multi-turn stagnation, repetitive, robotic | Reasoning suffix constraints | V2 |
| Cursor (Composer 2) | — | Shipped Kimi K2.5 as own model | Meta (harness IS the product) |

These degradations share characteristics that are hard to detect:
- **Invisible to internal evals** — Anthropic's own evals didn't catch 2 of 3 issues
- **Indistinguishable from model noise** — users see "worse" but can't prove it statistically
- **Compounding** — multiple small changes stack into perceived broad degradation
- **Hard to reproduce** — bugs appear only in corner cases (stale sessions, peak load)
- **Cross-provider** — every provider ships these; none has systematic detection

Sonnet 4.6 was quantified: 25 errors/week → 480 errors/week (19x increase) over
60 days across 50 sessions, tracking 1,400+ frustration events. (GitHub #46935)

## The Research Question

Can we build automated detection that catches orchestration-level quality
regressions before users notice them?

## Anthropic Postmortem Decomposition

| Change | Orchestration variable | Detection difficulty | Their timeline |
|--------|----------------------|---------------------|----------------|
| Effort high→medium | V2: Reasoning format | Low — direct A/B | 33 days to revert |
| Thinking cache cleared every turn | V9: Compaction + V3: Memory | High — corner case, stale sessions | 15 days to fix |
| "≤25 words between tool calls" | V4: Context allocation | Medium — needs broad evals | 4 days to revert |

Key quotes from the postmortem:
- "Neither our internal usage nor evals initially reproduced the issues"
- "Two unrelated experiments made it challenging for us to reproduce"
- "Combined with this only happening in a corner case (stale sessions)"
- Opus 4.7 Code Review found the bug that Opus 4.6 Code Review missed

## Approaches

### 1. McNemar's Test (ICLR 2026)

From "When LLMs get significantly worse" (accepted ICLR 2026):

Instead of comparing aggregate scores (which are noisy), compare per-sample
outcomes. For each test sample, record whether the model got it right under
condition A vs. condition B. McNemar's test then determines if the difference
is statistically significant.

- Can detect degradations as small as 0.3% accuracy drop
- Controls false positive rate
- Works on top of LM Evaluation Harness (already standard)

Three aggregation methods across benchmarks:
- **Bonferroni** — most conservative, low false positives
- **Fisher** — balanced sensitivity
- **Simes** — most sensitive, higher false positive risk

### 2. OrchVar-Canary Benchmark

A custom benchmark specifically designed to be sensitive to orchestration
variable changes. Small (50-100 tasks), fast to run, high signal.

**Task categories:**

| Category | What it catches | Inspired by |
|----------|----------------|-------------|
| **Reasoning depth probes** | Tasks that fail when thinking is too short | Effort high→medium regression |
| **Context recall probes** | Tasks that need info from step 2 at step 10 | Thinking cache bug |
| **Verbosity-sensitive** | Tasks where brevity causes info loss | "≤25 words" prompt regression |
| **Multi-turn memory** | Tasks that degrade if working memory is cleared | Memory policy regressions |
| **Tool argument precision** | Tasks where sloppy args cause failure | Schema fidelity under compression |
| **Safety canaries** | Tasks that test refusal under language mixing | Instruction hierarchy regressions |

Design principle: each task should PASS under good orchestration and FAIL
under a specific known-bad orchestration change. If the canary dies, you
know exactly which variable changed.

### 3. Continuous Monitoring

Run the canary suite on every harness change:

```
Harness change committed
  → Run OrchVar-Canary (50 tasks, ~5 min)
  → Compare against last N runs (McNemar's test)
  → If significant regression → block change, alert
  → If no regression → proceed
```

This is the agent-systems equivalent of a CI test suite, but for
orchestration quality instead of code correctness.

## Connections

- **All variables** — degradation detection is the quality gate for every other variable
- **Harness-beats-model** (V13) — if harness changes can degrade frontier models,
  detecting those changes is critical infrastructure
- **Verification cadence** (V8) — degradation detection IS verification at the
  experiment level, not the step level

## Sources (all verified 2026-04-28)

| Source | URL |
|--------|-----|
| Anthropic postmortem (3 harness bugs) | https://www.anthropic.com/engineering/april-23-postmortem |
| Sonnet 4.6: 1400+ frustration events quantified | https://github.com/anthropics/claude-code/issues/46935 |
| When LLMs get significantly worse (McNemar's test, ICLR 2026) | https://arxiv.org/abs/2602.10144 |
| OpenReview discussion | https://openreview.net/forum?id=cM3gsqEI4K |
| Amazon LLM-Accuracy-Stats framework | https://github.com/amazon-science/LLM-Accuracy-Stats |
| MonitorBench: CoT monitorability | https://arxiv.org/abs/2603.28590 |
| GPT-5 quality degradation reports | https://chatgptdisaster.com/gpt-5-problems-2026.html |
| ChatGPT quality analysis | https://www.atomwriter.com/blog/chatgpt-quality-degradation/ |
| Claude quality special report | https://techmaniacs.com/2026/04/17/special-report-why-claude-has-seemed-slower-lower-quality-and-less-reliable/ |
| Gemini 3.1 Pro degradation | https://tokencalculator.com/degradation |
| DeepSeek V4 multi-turn bug | https://github.com/deepseek-ai/DeepSeek-V3/issues/1125 |
| LLM quality degradation causes | https://docs.bswen.com/blog/2026-03-25-llm-quality-degradation |
| Quantifying Laziness in LLMs | https://arxiv.org/abs/2512.20662 |
