# Memory keep-set note

**Status: internal draft, not published (D101).** Publication is an outward action and stays the
program owner's call. Nothing in this directory has been posted, submitted or sent.

This is the internal write-up of the program's agent-memory line (decisions D103-D119), which
D119 asked for. It summarises, from the committed evidence only, three registered results on
LongMemEval-S with exact 256-subset outcome tables:

1. per-memory deletion (leave-one-out) credit is misspecified for keep and evict decisions
   (`am1-memory-credit-v1`, confirmatory);
2. with an oracle utility, search over keep sets beats sampled credit rules at equal or fewer
   reader calls, in six of seven registered comparisons; the comparison with greedy backward
   elimination is not separated, so the registered verdict is INCONCLUSIVE
   (`am1-keepset-search-v1`, H-A);
3. without labels, the reader's confidence is anti-informative and its abstention is usable:
   switching away from an abstaining keep set gains on answerable questions for three readers
   (`am1-keepset-search-v1` H-C, `am3-nonabstain-generality-v1` H1), at a measured,
   judge-qualified cost on unanswerable questions (H2, descriptive).

## Files

- `note.md`: the note. Every claim carries a status label (confirmatory, exploratory,
  descriptive, judge-qualified or post hoc).
- `numbers.md`: the claims check. Every number in `note.md`, with its status, its source file
  and the source text it was checked against.

## Basis

Every evidence path in the note resolves on `main` at `db589d2f`, the base of the branch
`paper/memory-keepset-note`. The note quotes no question, answer, reply or memory text; those
stay on the host. No human has reviewed the note, and its hand-check figures rest on agent
labels (D9).
