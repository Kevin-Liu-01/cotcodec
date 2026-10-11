# Sensitivity (b): Fable answers as the adjudications

**Adjudicated by an isolated model on the owner's instruction (D80); not human-validated.**

- `adjudications.jsonl` holds 33 `{item_id, answer}` rows in pool order. `0fd24b93ee7cd70c`, which Fable
  answered unsure, is left out and stays unresolved.
- `spot-check-answers.jsonl` holds all 25 spot-check answers, equal to (a)'s.
- `audit-summary/` and `analysis/` are frozen-tool outputs.

These answers are void under the strict registered audit because of an unregistered harness attachment,
`batching_reminder_sent`. They are used with that one type excepted, as a disclosed departure that applies
only to this sensitivity.
