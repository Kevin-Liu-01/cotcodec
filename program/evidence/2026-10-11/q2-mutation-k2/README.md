# K2 VM-fidelity executor: inputs and development record (2026-10-11)

**Blind warning for the adjudication (D9).** These files name checker verdicts
per mutant, and the K2-C lists name which mutants are checker candidate events
(their ids carry the operator). If you are adjudicating the
`q2-evaluator-mutation-v1` pool or doing its spot check, answer from the blind
packets before reading anything here, as for the results README's
`sample.jsonl`, `decisions.jsonl`, `analysis.json` and `summary.json`.

Addendum: `program/preregistrations/q2-evaluator-mutation-v1-k2.md` (DRAFT, not
frozen; D73 (ii)). Code: `harness/q2_mutation_k2/`. Nothing here is a K2
result: the registered K2 job runs only after the addendum is frozen.

## Files

| Path | What it is |
|---|---|
| `k2c-candidates-confirm.jsonl` | The registered K2-C list: the confirm campaign's 41 checker candidate events (36 FN, 5 FP_R; 17 tasks), written by `python -m harness.q2_mutation_k2.candidates` from the released `outcomes.jsonl` and `verdicts-lock.jsonl` (no audit file read). SHA-256 `c7b1869049749c8311e73f3ba09ea98e53e45086d49922c6ccea72ab6bb8a028` |
| `dev-inputs/k2-sample.jsonl`, `k2-sample.summary.json` | The K2 sample drawn in job 3 of the dev-split run `dev-mutants-v9` (80 jobs, 17 tasks), copied from the host |
| `dev-inputs/verdicts-lock.jsonl` | `dev-mutants-v9`'s lock-exact verdict rows (digests, metric functions, scores; no document content), copied from the host |
| `dev-inputs/k2c-candidates-dev.jsonl` | `dev-mutants-v9`'s 11 candidate events (8 FN, 3 FP_R), from the committed dev outcomes |

Development jobs (dev split only, exploratory, never evidence) are recorded
below as they run.
