# Audit summary with the run-2 adjudications (D81 (a))

**Adjudicated by an isolated model on the owner's instruction (D80); not human-validated.**

Blind warning: the files here name labels, decisions, sham status or answers. D9's human spot check is still pending as a human validation, so anyone doing it answers from the blind packets before reading this directory.

This directory holds the output of `python -m harness.q2_mutation.audit summarize` from a git archive of
`65bc2e2`. Its inputs were the released `sample.jsonl`, the same three calls files as the 2026-10-08
summary, and `--adjudications ../adjudications.jsonl` (34 pool answers from run (a)). The files are the
frozen tool's output, unmodified, so they carry no label field, and this README carries it. The tool still
writes `"human_spot_check": "pending"` and its model-rater label, and both stay true: no human has checked
anything. `adjudication-pool.jsonl` equals the committed 2026-10-08 pool. `summarize-stdout.json` is the
command's stdout. See `../README.md`.
