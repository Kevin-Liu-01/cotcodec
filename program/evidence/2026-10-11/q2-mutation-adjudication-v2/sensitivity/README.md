# The two D81 sensitivities

**Adjudicated by an isolated model on the owner's instruction (D80); not human-validated.**

Each sensitivity is a full `audit summarize --adjudications` plus the parent analysis with `--k2-report`,
from the same archive and with the same inputs as the record, except for the adjudications. Neither
replaces the record (D81).

- `b-fable/` uses the Fable answers (run (b)) as the adjudications: 33 pool answers, because one unsure
  is left out. Under the strict registered audit all 52 Fable answers are void (unregistered attachment),
  and this sensitivity would equal the K2 rerun. The answers are used here with that attachment type
  excepted.
- `c-notation/` uses (a)'s answers with the 12 marker items replaced by (c)'s. No answer changed, so the
  outputs are byte-identical to the record's.

See `../README.md`, section "Sensitivities".
