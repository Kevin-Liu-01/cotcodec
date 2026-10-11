# Run (a), the record: `wf_843930b8-5af`, `claude-opus-5-5`, 52 items

**Adjudicated by an isolated model on the owner's instruction (D80); not human-validated.**

- `collection.json` and `collect-stdout.json` come from `rater_runner collect-transcripts` (frozen).
- `calls.jsonl`, `receipt.json`, `rerate.json` and `ingest-stdout.json` come from `rater_runner
  ingest-isolated` (frozen): 52 `ok`.
- `rating-run.json` is the workflow's own record, with reasons omitted and ids and answers kept.
- `q2m-d81-adjudication-a-opus.js` is the workflow script, byte for byte.
- `audit_runs-equivalence-check.json` is the output of `../../audit_runs.py` on this run. It equals the
  frozen ingest on every per-item field.

Frozen-tool outputs are unmodified. Files authored here carry a `label` field.
