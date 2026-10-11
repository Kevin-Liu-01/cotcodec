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

## Development job 1122 (`k2-dev-smoke-v2`, executor `1448559`)

The same six pairs, two runs each, V = 3, CPU-only (16 CPUs; no GRES).
`dev-smoke-v2-job1122/run/` holds the lane's records, receipt, manifest and
preflight; `report/` the development report (`python -m
harness.q2_mutation_k2.report ... --only k2:000,k2:002,k2:004,k2:034,k2:037,k2c:005`).

- 12 of 12 runs scored, none excluded; every pair agrees with its offline
  lock-exact verdict in both runs: `k2:000` (Calc postconfig save, pass),
  `k2:002` (Writer agent save, pass), `k2:004` (Calc save with the derived CSV
  left to the postconfig, pass), `k2:034` (text target without a save, fail),
  `k2:037` (agent save after a `launch` setup, pass) and `k2c:005` (a
  `pptx.eq.zorder_nonoverlap` false negative on `compare_pptx_files`: it fails
  in the VM as it does offline).
- LibreOffice quit by Ctrl+Q in 0.2-0.4 s before every upload; no SIGTERM, no
  recovery dialog. Runs took 111-118 s. No target was unsaved at the checker's
  read; the save-time readings (-0.02 to -0.01 s) are clock-offset noise
  around a save that finished with the Ctrl+S call (reported only).
- The lane's host snapshots show another CPU job (1123, 32 CPUs, S2 v3's
  pilot) running from the second block on.

## Development job 1130 (`k2-dev-full-v1`, executor `a06dc69`): dress rehearsal

The registered job's shape on the dev split: all 80 pairs of the
`dev-mutants-v9` K2 sample, then its 11 candidate events, two runs each, V = 8,
40 CPUs and 64 GB, CPU-only (no GRES); submitted when the queue was empty.
`dev-full-v1-job1130/run/` holds the records, receipt, manifest and preflight;
`report/` the development report (no `--only`: every dev pair).

- 182 of 182 runs scored; no exclusion and no re-queue, so the fitness gate
  reads 0 of 80 excluded pairs.
- K2 (dev sample): 80 of 80 pairs agree with the offline lock-exact verdict in
  both runs (53 pass, 27 fail), over 7 checker families (`compare_table` 32,
  `compare_pptx_files` 19, `compare_docx_files` 9, `compare_docx_tables` 7,
  `compare_docx_files_and_ignore_new_lines` 6, `compare_pptx_files_robust` 5,
  `compare_text_file` 2). Development outcome VERIFIED (never an analysis
  input).
- K2-C (dev candidate events): 11 of 11 reproduced in both runs. The 8
  `pptx.eq.zorder_nonoverlap` false negatives (6 `compare_pptx_files`, 2
  `compare_pptx_files_robust`) fail in the VM as they do offline; the 3
  `docx.viol.drop_char_format` false positives pass in the VM as offline.
- Saves: 156 postconfig saves, 22 agent saves, 4 targets without a save; no
  target was unsaved at the checker's read, no late write, no postconfig reply
  failure, no metric error. LibreOffice quit by Ctrl+Q with no signal in all
  152 runs that had it open (26 runs had no LibreOffice to close).
- Runs took 111-122 s (median 116 s); the job took 45.5 minutes. The save-time
  reading has median -0.39 s because many tasks' Ctrl+S commands sleep after
  the keystroke before replying (reported only).
- Submitted on an empty queue; another CPU job (1132, 32 CPUs) appears only in
  the end snapshot, after the last block had started.

These are dev-split items: they test the executor and say nothing about the
confirm campaign's K2 result.

## Reports regenerated after the pre-freeze audit

Both development reports (`dev-smoke-v2-job1122/report/`,
`dev-full-v1-job1130/report/`) were rerun with the report code of the audit
fixes, from the same committed records. Each pair row gains `save_path`; every
other field of every pair row is unchanged. The summaries now give, per set,
agreement by save path and the run statistics (with S1a's checker-observation
summary summed), the receipt's host-snapshot overlap, and (job 1122's summary
predated it) `families_not_covered_by_k2`. Commands (dev inputs; the dev notes
summary is `program/evidence/q2-mutation/integration/dev-mutants-v9/notes-summary.json`):

```bash
python -m harness.q2_mutation_k2.report --run-dir <job>/run \
  --sample dev-inputs/k2-sample.jsonl --k2c dev-inputs/k2c-candidates-dev.jsonl \
  --verdicts dev-inputs/verdicts-lock.jsonl --notes-summary <dev notes summary> \
  --out-dir <job>/report   # job 1122 adds --only k2:000,k2:002,k2:004,k2:034,k2:037,k2c:005
```
