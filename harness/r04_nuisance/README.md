# harness/r04_nuisance

Code of record of `r04-checker-nuisance-invariance-v1`
(`program/preregistrations/r04-checker-nuisance-invariance-v1.md`, DRAFT): do OSWorld
checker verdicts on reference golds and on S1a's saved end states change when the
LibreOffice build, the save route or the desktop locale changes?

It reuses the checker-mutation study's save stage (`harness/q2_mutation/reachability.py`),
control jobs (`controls.py`) and offline scorer (`offline_eval.py`), and S1a's capture
rescoring (`harness/q2_stage1/rescore.py`) and corrected comparator (`zinv.py`), all
unchanged; `tests/test_r04_nuisance.py` refuses a diff to them.

| Module | Runs in | Role |
|---|---|---|
| `levels.py` | anywhere (stdlib, Python 3.10) | builds B0-B5, routes, locales, the 23 registered cells, per-cell profile and environment |
| `xcu.py` | LibreOffice images | set properties in a copied `registrymodifications.xcu` (identity when none) |
| `resave.py` | LibreOffice images | the save stage per cell: `reachability.run_job` with a session that changes only the cell's factor; `headless_convert` route; window-title fallback for builds that title windows with an em dash |
| `uno_store_as.py` | LibreOffice images | the `store_as` route's UNO client (`storeAsURL` with the load filter) |
| `items.py` | metric image | the registered items: P1's golds by split, S1a's office-exposed captured states (pass all, fail sampled 3 per task, mixed all), each capture checked against S1a's committed digests |
| `score.py` | metric image | pinned and corrected scoring of every (item, cell), twice in fresh processes |
| `analysis.py` | anywhere | the registered analysis: paired discordance against the control, confirmation rounds, control retention, V1/V2, retention, cell and arm readings, the K2 label; fails closed on missing cells, rounds or reference |
| `power.py` | anywhere | exact operating characteristics (`program/evidence/2026-10-11/r04-nuisance/power.json`) |
| `guard.py` | anywhere | refuses every split but dev until the registration is frozen and the staged code tree is the frozen one (`code_tree_sha256`) |

Images: B0 is the LO-VM image; B1-B5 are built from `infra/r04-nuisance/lo-tdf/BUILD/`
(rendered by `infra/r04-nuisance/render_dockerfiles.py`) through the lane's build mode.
Runs: `infra/r04-nuisance/run/r04_host.py` (`build`, `check-image`, `plan`, `next`,
`confirm`, `status`), one Slurm job at a time, CPU only. A plan is items, one save job per
build (the replicate in its own), six score jobs (`levels.score_groups`, secondary last),
and later both confirmation rounds; every step has its own directory, a failed job is rerun
as a new attempt (at most twice), and the registered run's 20 lane-hour cap is enforced by
`next`. The registered analysis reads everything from the run (`analysis --run RUN`).

Documents never leave the host: item files, captures, saved files and derived captures stay
under the host's run root; the repository receives manifests, verdicts, digests and save
timing only.
