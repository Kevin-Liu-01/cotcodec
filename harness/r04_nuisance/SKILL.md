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
- A discordance counts only after two confirmation rounds reproduce it.
- Documents (golds, captures, saved files) stay on the host; commit manifests, verdicts,
  digests and save summaries only.
- One Slurm job at a time: `r04_host.py next` submits only on an empty queue.

## Common tasks → first action
<!-- agent-docs:fill:tasks -->

| Task | First action |
|---|---|
| Change a level | Edit `levels.py`, run `infra/r04-nuisance/render_dockerfiles.py`, rebuild the image, update the pins block, rerun the dev smoke. |
| Run on the host | Stage `git archive HEAD` under `r04-nuisance/src/<sha>`, `r04_host.py plan ... --split dev`, then `next` until complete. |
| Confirm discordances | `analysis --pending-out`, then `r04_host.py confirm --round 1` and `--round 2` with those items and cells. |

## Gotchas
<!-- agent-docs:fill:gotchas -->

- `levels.py`, `xcu.py`, `resave.py` and `guard.py` run under the LO images' Python 3.10;
  `uno_store_as.py` runs under each build's own Python (TDF bundles 3.8+).
- TDF builds from 7.6 on title windows with an em dash; `resave` falls back to that title
  only after the registered one fails, and records it.
- A cross-version UNO client (Ubuntu 7.3 pyuno against TDF 7.6 or 24.8) fails with "Binary
  URP bridge disposed during call"; use the build's own Python.
- Locale data is compiled at start-up into `$TMPDIR` (`LOCPATH`); the image is unchanged.
