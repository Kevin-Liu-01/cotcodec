# Variable 2: Reasoning Format

**Status:** Partially overlaps Paper 1 (structured English condition). Natural Paper 2 candidate.

## The Variable

σ = format ∈ {free_form_cot, structured_protocol, symbolic_cot, program_of_thought, compressed_telegraphic, xml_tagged, json_reasoning}

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

## Conditions to Test

| Format | Example |
|--------|---------|
| Free-form CoT | "I need to check the user's order history first, then verify..." |
| Structured protocol | "PLAN: goal=check_refund, steps=[get_orders, verify_window]" |
| Symbolic CoT | "∀ order ∈ user.orders: order.date > now - 30d → eligible" |
| Program-of-thought | "orders = get_orders(user_id); eligible = [o for o in orders if o.date > cutoff]" |
| XML-tagged | "<plan><goal>check refund</goal><step>get orders</step></plan>" |
| JSON reasoning | {"goal": "check_refund", "steps": ["get_orders", "verify_window"]} |
| Compressed | "chk order hist → verify refund elig → process if valid" |

## Key Hypotheses

1. Structured formats reduce token count AND improve tool-call accuracy
   (the model has less room to drift)
2. Program-of-thought dominates on code-heavy tasks (SWE-bench)
3. Free-form CoT dominates on ambiguous tasks requiring flexible reasoning
4. XML/JSON reasoning trades tokens for parseability — worth it when
   downstream components need to read intermediate state

## Connections

- **Language** — structured English is the intersection. Language Paper 1
  already tests one format variant.
- **Observation granularity** — the format of reasoning affects how much
  of it needs to be retained for the next step.
- **Verification** — structured formats are easier to verify automatically.

## Prior Work

- Chen et al. 2022 — Program of Thoughts
- Xu et al. 2024 — Symbolic Chain-of-Thought
- Cuadron et al. 2025 — Overthinking in agentic tasks
- Munkhbat et al. 2025 — Self-training elicits concise reasoning

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
