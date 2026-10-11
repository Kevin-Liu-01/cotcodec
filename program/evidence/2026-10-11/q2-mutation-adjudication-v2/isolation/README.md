# Isolation audit of the D81 run-2 sessions

**Adjudicated by an isolated model on the owner's instruction (D80); not human-validated.**

- `a/` is the record. It holds the registered `collect-transcripts` and `ingest-isolated` outputs, frozen
  and unmodified: 52 `ok`, 0 void.
- `b/` holds the Fable sensitivity. The frozen collector accepted it, the frozen ingest refused it on the
  model pin, and `audit_runs.py` then audited it. Under the strict rules all 52 are void, each only for the
  unregistered `batching_reminder_sent` attachment.
- `c/` holds the notation sensitivity. The frozen collector refused it on the task turn, and
  `audit_runs.py` audited it with D81's sentence: 12 `ok`.
- `validation/` shows that `audit_runs.py` reproduces the frozen ingest on the 2026-10-08 registered
  rating.

No file here holds a reason or document text. Transcripts and answer files stay outside the repository,
hashed. See `../README.md`, section "Isolation audit: outcome".
