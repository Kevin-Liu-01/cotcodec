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
