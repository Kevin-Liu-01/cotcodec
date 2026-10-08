# D38 pass: the sixth review's minor items fixed (ninth draft; exploratory, no GPU)

Records of the pass that applied decision D38 to `q2-evaluator-mutation-v1`
on `stage0/q2-evaluator-mutation`: code at `58435c3`, the ninth draft and the
refreshed code-tree pin (`50edcc45...`) at `e6cdbd7`. No GPU was used and
nothing was frozen or ingested.

- `collect_dev_transcripts.py` and `collector-dev-58435c3.json`: the
  registered collector (`rater_runner.collect_transcripts`) and transcript
  audit at `58435c3`, run in a scratch directory over copies of the 158
  rater transcripts of the D34 development rating (workflow run
  `wf_65ce9899-24a`) and the journal lines of those agents. The collector
  maps all 158 to their items (142 answering agents, 16 interrupted
  attempts), and its layout equals the hand-copied one the sixth review
  audited, file name and SHA-256 for all 158. With the ingest's answering
  rule (an attempt without a journal result answers only through a
  structured answer) the audit finds no void reason, 142 answering
  transcripts, one per item, and one relay digest (`8e7dbd00`) in 110. Run on
  the whole workflow run, whose fix, audit and review agents are not raters,
  the collector refuses at the first agent it cannot map, as registered.
  Counts only: the development packets predate the difference-first order,
  so they are not re-ingested, and the registered development result (kappa
  0.066) stays as recorded.
- `host-tests-e6cdbd7.txt`: ruff and the full test suite on the host at
  `e6cdbd7`, from a fresh scratch copy of the worktree.
- `freeze-lint-e6cdbd7.json`: `scripts/preregister.py freeze` of the ninth
  draft into a scratch copy of the ledger (equal to main's, 7 rows), then
  `verify` and `check-chain` on that copy (8 rows, PASS). The registration's
  SHA-256 at that commit is in `scratch_row.sha256`. The real ledger is
  untouched.

`SHA256SUMS` covers every file here.
