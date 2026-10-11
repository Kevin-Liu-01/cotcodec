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

## Development job 1113 (`k2-dev-smoke-v1`, executor `60ed1b0`; void)

Six dev pairs (`k2:000`, `002`, `004`, `034`, `037`, `k2c:005`), two runs
each, V = 3, CPU-only (16 CPUs; no GRES). Cancelled after four records
(`dev-smoke-v1-job1113/k2-runs.jsonl`, `manifest.json`, `preflight.txt`):

- **Defect found.** The plan's `kill_process` sent SIGTERM to LibreOffice. That
  leaves the open document in LibreOffice's recovery list
  (`registrymodifications.xcu`, `Recovery/RecoveryList`), so the reopened
  candidate came up behind a "LibreOffice 7.3 Document Recovery" dialog, and the
  guest server's `/setup/open_file` returned only after 4 to 6 minutes.
  `k2:000:r1` and `k2:004:r1` were excluded at the pre-postconfig window check
  (`executor:pre_postconfig`, cause (4)), as designed.
- **Manual probe (contaminates one run).** While `k2:002:r1`'s executor waited
  on the open call, a probe script was run by hand in that VM (through
  `docker exec` into the run's own episode container and the guest's
  `/execute`): it killed LibreOffice, cleared the recovery list, opened the
  document, quit it with Ctrl+Q, reopened it (no dialog), and finally signalled
  it. The executor then went on with the probe's LibreOffice instance, so that
  run's `scored`/`pass` record is void. The probe's readings: one recovery-list
  entry exists while a document is open; after Ctrl+Q, LibreOffice exited in
  0.5 s and the reopened document showed no dialog.
- `k2:034:r1` (a text target with no save) ran as designed: `fail` in the VM,
  `fail` offline.
- Fix (`b5a5247`): `kill_process` asks LibreOffice to quit (Ctrl+Q in one of
  its windows) before any signal; executor setup steps are bounded at 180 s;
  every step prints a progress line to the run's container log.
