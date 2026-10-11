# K2 job 1186: the parent analysis rerun with `--k2-report`

**Blind warning for the adjudication (D9, D77, D78).** `analysis.json` names
labels, audit decisions, sham status and checker verdicts per mutant, like the
parent's `results/analysis.json`. If you are adjudicating the
`q2-evaluator-mutation-v1` pool (34 items) or doing its spot check (25 items),
answer from the blind packets before reading anything here.

`python -m harness.q2_mutation.analysis` with the parent's inputs as they stand
(pre-adjudication audit summary and decisions) plus `--k2-report
../report/k2-report.json` (section 9.4). Against the committed parent
`analysis.json` only `exclusions.k2` changes: the label becomes "VM fidelity
checked (K2)", with `executor_commit` and `pairs`; no family is dropped. See
`../README.md` for the command, the input digests and the reproduction control.
