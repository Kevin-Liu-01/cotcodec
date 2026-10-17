# Memory keep-set note

**Status: internal draft, not published (D101).** Publication is an outward action and stays the
program owner's call. Nothing in this directory has been posted, submitted or sent.

This is the internal write-up of the program's agent-memory line (decisions D103-D131), which
D119 asked for. It summarises, from the committed evidence only, the line's results on
LongMemEval-S with exact 256-subset outcome tables, narrowed to the novelty audit of D131. None
of the results is a new phenomenon; the audit found prior work for each.

1. **Exact keep-set tables (the strongest result).** Keep-set regret against the exact keep-4
   optimum, on 694 exhaustive judged tables, is the one measurement for which the audit found no
   direct prior (through 2026-10-16, under the audit's coverage; this is not evidence of novelty
   beyond it). On them, top-4 keep sets by leave-one-out credit are misspecified
   (`am1-memory-credit-v1`, confirmatory). Post hoc, most of that loss sits in pools the reader
   gets wrong even with all 8 memories, and exact Shapley and Banzhaf keep an optimal set in
   95.6% and 96.4% of the 251 non-constant retrieved tables (no adequacy verdict is licensed); this is not evidence that
   memory interactions defeat per-memory credit.
2. **Search with an oracle.** Given the judged utility, search over keep sets beats
   leave-one-out and sampled credit rules in six of seven registered comparisons; the comparison
   with greedy backward elimination is not separated, so the registered verdict is INCONCLUSIVE
   (`am1-keepset-search-v1`, H-A). This is a known wrapper-versus-filter effect.
3. **A known abstention-gated keep rule, replicated.** Switching away from a keep set whose
   reply abstains, a variant of the stop rule of Wang, Ma and Kumar (2025), gains on answerable
   questions for three readers (`am1-keepset-search-v1` H-C, `am3-nonabstain-generality-v1` H1).
   Its cost was measured on LongMemEval-S's 30 unanswerable questions (descriptive,
   judge-qualified), across read caps (AM4, exploratory and post hoc), and with each question's
   evidence removed (AM5 on the 63 development questions; `am5-ablated-cost-v2` on the 347
   held-out questions, confirmatory: cost below gain for the two Qwen readers at a cap of 8
   reads, not separated for OLMo-2).

## Files

- `note.md`: the note. Every claim carries a status label (confirmatory, exploratory,
  descriptive, judge-qualified or post hoc).
- `numbers.md`: the claims check. Every number in `note.md`, with its status, its source file
  and the source text it was checked against.

## Basis

Every evidence path in the note resolves on `main` at `1cf31346`, the base of the branch
`paper/memory-keepset-note-d131`. The note quotes no question, answer, reply or memory text;
those stay on the host. No human has reviewed the note, and its hand-check figures rest on agent
labels (D9).
