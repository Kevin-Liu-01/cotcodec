# Run (b), the independence sensitivity: `wf_4d1fa210-001`, `claude-fable-5-1`, 52 items

**Adjudicated by an isolated model on the owner's instruction (D80); not human-validated.**

- `collection.json` and `collect-stdout.json` come from the frozen collector, which accepted the run: 52
  transcripts mapped, 52 answered.
- `ingest-refusal.txt` is the frozen ingest's stderr. It refuses any model but `claude-opus-5-5` and wrote
  nothing.
- `audit_runs.json` is the output of `../../audit_runs.py --model claude-fable-5-1`. Every check passes
  except the attachment allow-list. Each transcript holds `batching_reminder_sent`, a fixed harness
  sentence about batching tool requests (171 entries), so under the strict rules all 52 are void.
  `answer_given` is what each agent returned, and the (b) sensitivity uses it with that one attachment
  type excepted.
- `rating-run.json` is the workflow's record, without reasons. The script is copied byte for byte.
