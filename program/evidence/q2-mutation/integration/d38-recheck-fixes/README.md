# Narrow re-check of the ninth draft: minor items fixed (exploratory, no GPU)

Records of the pass that fixed the minor items of the narrow re-check of
`q2-evaluator-mutation-v1`'s ninth draft (90/100, ready to freeze, no
blocking defect) on `stage0/q2-evaluator-mutation`: code at `de24e23`, the
registration and the refreshed code-tree pin (`58bee019...`) at `a8ea642`,
and the merge of main `a9948ee` (the action-path registrations frozen, the
ledger at 10 rows) at `88bd376`. No GPU was used and nothing was frozen or
ingested.

The fixes: `audit summarize --rerate-list` and `export-isolated
--rerate-list` recompute the re-rate items from the ingest's calls file
(`rater_runner.check_rerate_list`: the records whose only void reason is the
relay mismatch) and refuse a list that differs; tests pin that rule and the
journal's started-twice refusal; the transcript collector copies into a
staging directory and renames it into place only when every copy checks;
section 9 and section 17 say that a resume with a different relay frame puts
every relay-voided item in Kevin's pool (113 items against 24 on the
development analogue); the harness README's pool row.

- `mutants.py` and `mutants-88bd376.json`: nine targeted mutants of these
  fixes, each applied to a `git archive` copy of `88bd376` and run against
  its tests in `tests/test_q2_mutation_rater_runner.py`. All nine are killed,
  including the re-check's survivors M7 (the re-rate filter `in` instead of
  `==`) and M14 (no started-twice refusal); the baseline passes.
- `host-tests-88bd376.txt`: ruff and the full test suite on the host at the
  merge head, and at `a8ea642` before the merge, each from a fresh scratch
  copy of the worktree. The one failure at the merge head is main's own
  action-path test that predates main's freeze (it fails on main too).
- `freeze-lint-88bd376.json`: `scripts/preregister.py freeze` of the ninth
  draft into a scratch copy of the ledger (equal to main's at `a9948ee`, 10
  rows), then `verify` and `check-chain` on that copy (11 rows, PASS). The
  registration's SHA-256 at that commit is in `scratch_row.sha256`. The real
  ledger is untouched.

`SHA256SUMS` covers every file here.
