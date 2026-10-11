# Equivalence check: `audit_runs.py` on the 2026-10-08 registered rating

**Adjudicated by an isolated model on the owner's instruction (D80); not human-validated.**

`audit_runs.py --model claude-opus-5-5` (no suffix) on `wf_138e30b5-c1a` and its 178 answer files gives
177 `ok` and 1 `isolation_void` (`fd455942...`, the Read outside its directory). Every item's outcome,
answer, void reasons, tool counts, transcript digest and answer source equal the committed
`../../../../2026-10-08/q2-mutation-confirm/audit/claude-isolated/calls.jsonl`. All 178 item trees re-hash
equal to the export. The page counts give the registered rating's image coverage: 1,453 of 1,457 images
opened, and 176 of 178 agents opened every image.
