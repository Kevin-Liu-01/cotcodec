# S1a analysis tooling under D59 (blind, synthetic records only)

Before any A1 outcome was read, a dry run of the frozen analysis code
(`d5f5798`) on synthetic records found eleven defects (`dry-run-finish.json`),
and an independent checker reproduced every one (`dry-run-check.json`).
D59, D61 and D62 (program/decisions.md) fix how each is handled. The tooling
under `ops/s1a-analysis/` (wrapper, incomplete-data guard, operator scripts,
`RUNBOOK.md`) implements them without changing the code of record.

Three fresh verifiers read the tooling, each on its own synthetic records:

| File | Result |
|---|---|
| `tooling-verify-1.json` | one blocking item (a runbook command missing `--out`), fixed |
| `tooling-verify-2.json` | one blocking item (a size with two sessions but no π; now D62), fixed |
| `tooling-verify-final.json` | wrapper byte-identical to the registered CLI without fractional scores, only the fractional keys change with them; every D59, D61 and D62 case marked as decided; labels on every output file; one blocking runbook gap (step 4 did not wait for the rescoring jobs), fixed in `RUNBOOK.md` with a wait rule and a receipt guard on the merge loop |

The blindness rule held in every pass: no A1 episode record, score, report or
log was read. The code of record is unchanged (`git diff d5f5798 -- harness/
scripts/ infra/ experiments/` is empty). Local paths in these files are written
as `<scratch>`, `<session>`, `~` and `~host`.
