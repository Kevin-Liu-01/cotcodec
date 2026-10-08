# D35 protocol pass: host test record and freeze-lint (exploratory, no GPU)

Records of the pass that applied decision D35 to `q2-evaluator-mutation-v1`
(seventh draft) on `stage0/q2-evaluator-mutation`. No GPU was used and
nothing was frozen.

- `host-tests-1e42036.txt`: ruff and the full test suite on the host at the
  final code commit, from a fresh scratch copy of the worktree.
- `freeze-lint-1e42036.json`: `scripts/preregister.py freeze` of the
  registration into a scratch copy of the ledger (equal to main's, 7 rows),
  then `verify` and `check-chain` on that copy. The real ledger is untouched.
  The registration's SHA-256 at that commit is in `scratch_row.sha256`.

`SHA256SUMS` covers every file here.

## Sixth-review fix (eighth draft, commit `1242da7`)

The sixth review (80/100) found that the transcript audit read only entries
of type user, so a message queued into a running rater (a `queued_command`
attachment) passed it. `rater_runner.audit_transcript` now registers the
entry types (`TRANSCRIPT_ENTRY_TYPES`) and the fifteen harness attachment
types of the D34 development rating (`HARNESS_ATTACHMENT_TYPES`) and voids
any other. Records of that pass, also exploratory, no GPU:

- `transcript-audit-dev-1242da7.json`: the audit at `1242da7` rerun over
  copies of the 158 development transcripts (142 answering agents, 16
  interrupted attempts) by `audit_dev_attachments.py`, counts only: no void
  reason, 3,304 attachments, all of the fifteen registered types, none
  outside the list, one relay digest (`8e7dbd00`) in 110. Nothing was
  ingested; the registered dev result stays as recorded.
- `host-tests-1242da7.txt`: ruff and the full test suite on the host at
  `1242da7`, from a fresh scratch copy of the worktree.
- `freeze-lint-1242da7.json`: the freeze-lint at `1242da7` into a scratch
  copy of the ledger (equal to main's, 7 rows); the real ledger is
  untouched.
