# Parent analysis rerun with the run-2 adjudications and `--k2-report` (D81 (a))

**Adjudicated by an isolated model on the owner's instruction (D80); not human-validated.**

Blind warning: the files here name labels, decisions, sham status or answers. D9's human spot check is still pending as a human validation, so anyone doing it answers from the blind packets before reading this directory.

This directory holds the output of `python -m harness.q2_mutation.analysis` from a git archive of `65bc2e2`,
run with the parent's outcomes and control summaries, `../audit-summary/audit-summary.json`,
`../audit-summary/decisions.jsonl` and `--k2-report` (the K2 job's `report/k2-report.json`). The files are
the frozen tool's output, unmodified. The before/after against the K2 rerun is in `../README.md` and
`../summary.json`.
