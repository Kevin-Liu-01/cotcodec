# Q2 evaluator mutation: shared evidence

Inputs and outputs of the OSWorld-Verified checker-mutation study (Q2 Stage 0).
The binding record formats are in `harness/q2_mutation/schema.py`
(`q2-mutation-schema-v1`). Branches: harness `stage0/q2-mut-harness`, specs
`stage0/q2-mut-specs`, operators `stage0/q2-mut-operators`, integration
`stage0/q2-evaluator-mutation`.

| Path | What it is | Who may read it |
|---|---|---|
| `sanitized-tasks/<task_id>.json` | Blind-author view of one in-scope task: `task_id`, `domain`, `instruction`, `related_apps`, `initial_files` (`url` at the pinned file-cache revision, absolute `path_in_vm`, `sha256`), `snapshot` | Everyone, including the blind spec author |
| `sanitized-tasks.manifest.json` | Pins (OSWorld commit, file-cache revision), selection rule, manual web exclusions, SHA-256 of every exported file | Everyone |
| `splits.json` | Seeded (42) stratified task split: `dev` (harness validation, pilot, τ calibration), `confirm` (the 120-task confirmatory mutation subset), `reserve` | Everyone |
| `specs/<task_id>.yaml` | Requirement specs written blind (spec branch) | Everyone after they are committed |
| `operators/` | Operator catalog (`operator-catalog.json`), synthetic and dev-split operator validation, the operators' preregistration input | Not the blind spec author |
| `integration/` | Integration of specs, operators and harness: `blind-spec-provenance.json` (no trace of checker access; the spec author's model and provider), `target-counts-v1.json` (targets per split, no specs or checkers), one `campaign export` per dev-split end-to-end run (`dev-mutants-v*`: redacted recipes, outcomes, verdict rows, summaries; exploratory), the pre-freeze recount at the cell-level rule and the K7 power simulation (`prefreeze-counts-v2/`), the dev K2 sample (`k2-sample-dev-mutants-v6/`) and the dev rater smoke (`rater-smoke-dev-v1/`: audit sample, packet manifest, open-weight rater calls and receipt; no packet or response content) | Not the blind spec author or the raters |
| `harness/` | Checker-derived harness side: `task-scope.json` (task classes and metric functions), `file-cache-receipts.tsv` (447 files with SHA-256), `inputs-manifest.json` (every external source), dev-split validation (`dev-validation-2026-10-07.json`, `dev-controls-v6-summary.json`, `dev-controls-v7-summary.json` at the reviewed code: save failures and unemulated tasks listed, exact P1 interval; `dev-controls-v8-summary.json` and `-v9-summary.json` after the second review: P1 only on save-exposed golds, S1 confirmation) | Not the blind spec author |

## Scope

The 205 tasks of `evaluation_examples/test_nogdrive.json` at OSWorld
`b138d348256078fa634fc3b73567a7337c793e6b` whose every metric reads a file or
an application config file obtainable offline, minus tasks that need the web
(config criteria plus a manual reading of eight flagged instructions; see the
manifest). Infeasible tasks and tasks scored on live VM or browser state are
out of scope.

Relative download targets are resolved the way the OSWorld server does it:
`expanduser`/`expandvars` (`desktop_env/server/main.py:1166`) with
`WorkingDirectory=/home/user`, confirmed in the VM image's
`/etc/systemd/system/osworld.service` (`User=user`,
`ExecStart=/usr/bin/python /home/user/server/main.py`).

## Rules for the blind requirement-spec author

1. Read only `sanitized-tasks/`, `splits.json`, the manifest, `schema.py`, the
   initial files (fetch them by URL and check the SHA-256) and public
   application documentation.
2. Never open OSWorld's `desktop_env/evaluators`, the task JSONs in
   `evaluation_examples/`, gold files, anything under `harness/`,
   `operators/` or `integration/` here, the scoping and review plans, or any
   probe output.
3. Write `specs/<task_id>.yaml` with `author: blind-model-author-v1`. Each
   requirement's `observable` says how to test it on the end-state document
   without any checker. List what the instruction leaves open under
   `allowed_variations`.
4. Priority order: `dev`, then `confirm`, then `reserve`.
5. Record the session, model and date of authorship in the spec branch's
   provenance file.

## Licences

Task configs: Apache-2.0 (xlang-ai/OSWorld). File cache: apache-2.0 dataset
card; the documents contain third-party content. This repository releases
task metadata, mutation recipes and verdicts, never mutant documents.
