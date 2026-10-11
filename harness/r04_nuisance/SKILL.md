---
name: harness-r04-nuisance-skill
description: Procedure for the R04 checker nuisance-invariance study (r04-checker-nuisance-invariance-v1) in harness/r04_nuisance/.
---

# cotcodec / harness / r04_nuisance

## Purpose
<!-- agent-docs:fill:purpose -->

r04-checker-nuisance-invariance-v1 (DRAFT) asks whether OSWorld checker verdicts on the
checker-mutation study's reference golds and on S1a's saved end states change when the
LibreOffice build, the save route or the desktop locale changes. Every cell is the
mutation study's registered GUI-faithful save with one factor changed; every comparison
is paired with the control cell. Runbook: `README.md` in this directory and the
registration.

## Mental model & key files
<!-- agent-docs:fill:model -->

- `levels.py` is the design: builds B0-B5, routes, locales, the 23 cells and what each
  sets in the profile and environment. The analysis, the host tool and the Dockerfile
  renders read it.
- `resave.py` subclasses `reachability.LoSession`; the control cell must stay the
  registered save (no profile or environment override, `reachability.run_job`).
- `items.py` rebuilds P1's golds from configs and S1a's states from the lane's captures,
  checked against S1a's committed digests; `score.py` reuses `offline_eval`'s worker and
  `rescore._capture_worker`; `analysis.py` is the registered analysis.
- `infra/r04-nuisance/run/r04_host.py` renders and submits every job through the
  unchanged `q2-mutation-cpu.sbatch`.

## Patterns to follow / invariants
<!-- agent-docs:fill:patterns -->

- Never edit `harness/q2_mutation/`, `infra/q2-mutation/`, the q2 lane or
  `harness/q2_stage1/`: they are pinned by frozen registrations (a test refuses a diff).
- A discordance counts only after two confirmation rounds reproduce it; missing round rows
  keep it pending (never INVARIANT).
- The analysis fails closed: every registered cell is scored or named with a reason, exactly
  0 or 2 rounds, the pinned control summaries and a registered split set (dev alone, or
  confirm and reserve). Never add a way to drop a scored cell or pick rounds by hand.
- Every step writes to its own directory; a failed job is rerun as `.a2`/`.a3` by `next`.
  Never write into another attempt's directory.
- Every analysis output carries the K2 label and the blind warning; never read audit or
  adjudication files (`analysis.FORBIDDEN_INPUT`).
- Documents (golds, captures, saved files) stay on the host; commit manifests, verdicts,
  digests and save summaries only.
- Any change to the code tree (`guard.CODE_TREE_ROOTS`, tests included) after the freeze
  makes the guard refuse the registered splits.
- One Slurm job at a time: `r04_host.py next` submits only on an empty queue.

## Common tasks → first action
<!-- agent-docs:fill:tasks -->

| Task | First action |
|---|---|
| Change a level | Edit `levels.py`, run `infra/r04-nuisance/render_dockerfiles.py`, rebuild the image, update the pins block, rerun the dev smoke. |
| Dev smoke on the host | Stage `git archive HEAD` under `r04-nuisance/src/SHA` (with `.git_sha`), `r04_host.py plan --src SRC --name NAME --split dev --golds --s1a 1037 --cells ... --workers 8`, then `next` until complete. |
| Registered run (after the freeze only) | `export R04_PREREG_FROZEN=r04-checker-nuisance-invariance-v1`, `r04_host.py plan --src SRC --name r04-registered-v1 --registered`, `next` until complete; the exact lines are the registration's section 6. |
| Confirm discordances | `python -m harness.r04_nuisance.analysis --run RUN --src . --out RUN/analysis-main.json --pending-out RUN/pending.json`, then `r04_host.py confirm --name NAME --pending RUN/pending.json` (adds both rounds), `next` until complete, and the analysis again without `--pending-out`. |
| Re-analyse old smoke evidence | The explicit form: `--items`, `--scores`, `--round` twice, `--splits dev`, `--reference` (the pinned dev summary). |

## Gotchas
<!-- agent-docs:fill:gotchas -->

- `levels.py`, `xcu.py`, `resave.py` and `guard.py` run under the LO images' Python 3.10;
  `uno_store_as.py` runs under each build's own Python (TDF bundles 3.8+).
- TDF builds from 7.6 on title windows with an em dash; `resave` falls back to that title
  only after the registered one fails, and records it.
- A cross-version UNO client (Ubuntu 7.3 pyuno against TDF 7.6 or 24.8) fails with "Binary
  URP bridge disposed during call"; use the build's own Python.
- Locale data is compiled at start-up into `$TMPDIR` (`LOCPATH`); the image is unchanged.
- LibreOffice saves are not byte-deterministic: compare verdicts, never saved bytes.
- `r04_host.py plan` for the registered splits needs `R04_PREREG_FROZEN` exported in the
  host shell (the host's own guard check), besides the frozen ledger row.
- The analysis is slow on intervals (exact bounds); run the test file in the background.
