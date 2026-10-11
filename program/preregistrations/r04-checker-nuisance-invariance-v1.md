# r04-checker-nuisance-invariance-v1: do OSWorld checker verdicts survive nuisance changes?

**Status: DRAFT. Not frozen, no ledger row, no pre-freeze audit yet.** Drafted on
2026-10-11 by the single owner of R04 under decision D73 (iii), on branch
`stage0/r04-nuisance`. A registered CPU study at 0 GPU-h: it runs only after a pre-freeze
audit and the program owner's freeze (section 17); nothing here may be frozen by the agent
that drafted it. Only dev-split smoke tests have run (section 15). Origin: the renewal
dossier's `R04-nuisance-invariance` (`program/evidence/2026-10-11/question-renewal/`,
`dossier.md` section 7, `slate.md` section 5, `verification.json` claims c012, c019, c021,
c036, c040-c042, c066, c091, c092, c181, c183, c202), with the judges' defects repaired
(section 16).

## 1. Question

When the environment around a fixed OSWorld-Verified end state changes in ways that should
not matter to the task, does the task's checker give the same verdict? The end states are
the reference golds of the checker-mutation study's P1 population and the end states S1a's
agents saved. The nuisance factors are three, each varied one at a time from the
registered save:

- **LibreOffice build**: the VM's own Ubuntu build (1:7.3.7-0ubuntu0.22.04.4, "LibreOffice
  7.3.7.2") against five TDF builds, 7.3.7.2 (same upstream version, other packaging),
  7.6.7.2, 24.8.7.2, 25.8.7.3 and 26.2.6.2;
- **save route**: the registered GUI Ctrl+S save against a Save As in the document's own
  format and a headless same-format `--convert-to` round trip;
- **desktop locale**: en_US against de_DE, ar_EG, ja_JP and tr_TR (desktop and LibreOffice
  locale; interface language kept en-US).

A verdict that changes is a checker that is not invariant to the factor on that end state,
whatever the cause (the build writes the document differently, or the checker reads a
locale- or build-dependent detail). The study measures that, per factor level, on fixed
populations with a paired control. It does not ask whether a changed verdict is right; each
confirmed discordance is listed with what changed (section 11) for a later audit.

## 2. What it decides and what it does not

It decides, for each factor level, one of INVARIANT, MINOR or DRIFT (section 9), and for
each factor (arm) the same three readings. These are the precondition that the dossier
named for S2 v3 and for any re-hosted OSWorld image: whether a study that changes the
LibreOffice build or the desktop locale can keep OSWorld's checkers as they are.

It does not decide: whether a flipped verdict is a checker defect or a real document change
(listed, not adjudicated); anything about agents typing into a localized desktop (the
slate's descriptive keystroke arm needs the certified VM path and is not part of this
registration); builds, locales or save routes other than the registered ones; Windows or
macOS LibreOffice; OOXML producers other than LibreOffice.

## 3. Identity and pins

| Object | Pin |
|---|---|
| Experiment id | `r04-checker-nuisance-invariance-v1`; this file |
| OSWorld | `b138d348256078fa634fc3b73567a7337c793e6b` (the checker-mutation study's checkout on the host; tree digest `4153c68678fedd44a285800b45f4b7e538336a044f614f748f432a7ce5246076`) |
| File cache | HF `xlangai/ubuntu_osworld_file_cache` at `1e112283c4ecb08d6fed8069bca7de74fa2f12aa`, receipts `9a3e06a48afe95c2286d0fa26d56edf947e1a5e0f121d414d565b58d30abe5fb` |
| VM baseline files | the checker-mutation study's 75 files, tree `f32538182c72aa44ca348a42fcc1c04a1faf35b2c18a8f76d8af1d3bfafcb1df` (mounted read-only at `/inputs/vm-baseline`) |
| Splits | `program/evidence/q2-mutation/splits.json`, SHA-256 `2099792e6fb86c69e4f79b1ce47d2839cc25623f5c4633698e95822553c007d9` |
| Build B0 (control) | the LO-VM image `sha256:f5b4c40eefd2b92f846652910ba34db35e1ae7bf90fa474595cc745cc5895361` (tag `cotcodec-q2-lo-vm:4d5db07d`), the checker-mutation study's pinned save-stage image: the OSWorld VM's own userland, `libreoffice-core 1:7.3.7-0ubuntu0.22.04.4`, its profile and pyautogui |
| Builds B1-B5 | images derived from B0 (section 4.1); IDs in the pins block below; each tarball's TDF URL, size and SHA-256 in `harness/r04_nuisance/levels.py` |
| Metric image | `sha256:2006c1a9247e4911a82508cd22e9d9a7efc5c13e35a20e8a03baac7112876230`, lock-exact venv (`/opt/venv-lock`, OSWorld `uv.lock`, Python 3.12.13) |
| Corrected comparator | `harness/q2_stage1/zinv.py` (S1a's validated `compare_pptx_files_zinv`, G0 item 8) |
| S1a records | the lane runs 1037 (A0a, dev tasks) and 1045, 1048, 1051, 1062 (A1-9B-S1, A1-4B-S1, A1-9B-S2, A1-4B-S2), each `episodes.jsonl` by its committed SHA-256 and each capture file by S1a's committed `raw-sha256sums.txt` (`harness/r04_nuisance/items.S1A_RUNS`); the item builder refuses any difference |
| Frozen control verdicts (V1) | `program/evidence/2026-10-08/q2-mutation-confirm/results/released/controls/confirm-controls-v1.summary.json` (`1ae20605...`) and `reserve-controls-v1.summary.json` (`1da42642...`); dev smoke: `program/evidence/q2-mutation/harness/dev-controls-v9-summary.json` (`e13cbbe6...`) |
| Code of record | `harness/r04_nuisance/`, `infra/r04-nuisance/`, and, unchanged, `harness/q2_mutation/` (reachability, controls, offline_eval) and `harness/q2_stage1/rescore.py`; the code-tree digest and commit are filled at the freeze (section 17) |
| Lane | `infra/slurm/host-single-node/q2-mutation-cpu.sbatch`, unchanged (CPU only, no GRES) |

Machine-readable pins (read by `harness/r04_nuisance/guard.py`, which refuses every split
but dev unless this file is frozen and the images below are the ones a job names):

```json
{
 "r04_pins": 1,
 "experiment_id": "r04-checker-nuisance-invariance-v1",
 "images": {
  "B0": "sha256:f5b4c40eefd2b92f846652910ba34db35e1ae7bf90fa474595cc745cc5895361",
  "B1": "sha256:fd1f1bfed3e60f8e86e6d281a072726a8d042d5143703f3a8724f25bf9167d67",
  "B2": "sha256:c39f6957ec75ac270db031c333dd59f5f010056288131453b10aff4ed818a0cb",
  "B3": "sha256:728aaa69a5ea8484895f0678f5e0ba45ac92ab6f4485ccc9fb8700abffe87ce9",
  "B4": "sha256:87af250e3cd88999415631cdfd248228c1365ed82df4952daec8c32d44442e14",
  "B5": "sha256:6cf86ce55e0c2e8ad3a1bddea512b4c9326b552a78c4ad4ecbc4471afd748402"
 },
 "metric_image_id": "sha256:2006c1a9247e4911a82508cd22e9d9a7efc5c13e35a20e8a03baac7112876230",
 "splits_sha256": "2099792e6fb86c69e4f79b1ce47d2839cc25623f5c4633698e95822553c007d9",
 "registered_splits": ["confirm", "reserve"],
 "drift_min": 3,
 "retention_min": 0.9,
 "confirm_rounds": 2
}
```

## 4. Factors, levels and cells

All levels are in `harness/r04_nuisance/levels.py`; the analysis reads them from there.

### 4.1 Builds

| Id | Build | How it is installed | soffice |
|---|---|---|---|
| B0 | Ubuntu `1:7.3.7-0ubuntu0.22.04.4` ("7.3.7.2 30(Build:2)") | the VM's own (LO-VM image) | `/usr/bin/soffice` |
| B1 | TDF 7.3.7.2 | TDF deb tarball unpacked under `/opt/libreoffice7.3` | `/opt/libreoffice7.3/program/soffice` |
| B2 | TDF 7.6.7.2 (last 7.x) | as B1, `/opt/libreoffice7.6` | as B1 |
| B3 | TDF 24.8.7.2 | `/opt/libreoffice24.8` | as B1 |
| B4 | TDF 25.8.7.3 | `/opt/libreoffice25.8` | as B1 |
| B5 | TDF 26.2.6.2 | `/opt/libreoffice26.2` | as B1 |

Each derived image is `FROM` the LO-VM image (by tag, which the host tool checks names
`f5b4c40e...` before building, and whose layers it checks the result extends). Its one
`RUN` fetches TDF's deb tarball from TDF's archive
(`https://downloadarchive.documentfoundation.org/libreoffice/old/<version>/deb/x86_64/`),
checks the size and SHA-256 TDF states for it (its `.mirrorlist` page, read 2026-10-11),
and unpacks each `.deb` with `dpkg-deb -x` (not `dpkg -i`), so the dpkg database is
untouched: `dpkg-query` before and after must be byte-identical, and the build fails
otherwise. The menu package is not unpacked. Builds run through the lane's build mode
(`--network=host` for the fetch; the runtime has no network) with no root on the host
(decision D2, AGENTS.md rule 4). Tarballs are 186-207 MB each (1.04 GB in all, none over
1 GB; D1). The Dockerfiles are rendered from `levels.py`
(`infra/r04-nuisance/render_dockerfiles.py`; a test refuses a stale one).

B1 separates packaging from version: a B1 discordance is a property of TDF's build of the
same upstream release. B2-B5 span the releases from 7.6 to the stable branch of
2026-10-11.

### 4.2 Save routes

| Route | What saves the file | Postconfig |
|---|---|---|
| `ctrl_s` (registered) | the checker-mutation study's GUI-faithful save stage unchanged: candidate placed at its VM path, opened by non-headless LibreOffice under Xvfb and openbox with a fresh copy of the VM profile, the task's postconfig replayed (window activation, keys through the VM's pyautogui, sleeps, `--convert-to` with the task's own filter), one agent-equivalent Ctrl+S per office file the postconfig does not save | replayed |
| `store_as` | the same, except that every save event the registered stage makes with Ctrl+S is a Save As in the document's own format through the document model: the instance is started with a UNO pipe and `uno_store_as.py` calls `storeAsURL` on the document's own URL with the filter it was loaded with and `Overwrite` | replayed |
| `headless_convert` | no GUI instance: each office file is converted to its own format (`soffice --headless --convert-to <ext>:<filter>`, OOXML or ODF filter of its type) into a scratch directory and copied back; then the task's own postconfig conversions run, headless | conversions only (keys and window steps have no GUI to act on) |

The UNO client of `store_as` is the build's own Python and pyuno: the VM's Python with
Ubuntu's python3-uno for B0, the bundled `program/python` of each TDF build. (The first
dev smoke used Ubuntu's client for every build; against TDF 7.6 it failed on Writer and
Impress documents and against 24.8 on every document, "Binary URP bridge disposed during
call", section 15.) A build without a bundled Python gets no `store_as` cell (a cell error,
NOT_EVALUABLE).

### 4.3 Locales

| Id | Locale | Why it could matter |
|---|---|---|
| L0 | en_US (control; the VM's) | |
| L1 | de_DE | decimal comma, `.` grouping, `;` list separator, dd.mm.yyyy |
| L2 | ar_EG | right-to-left locale, Arabic-Indic digits available |
| L3 | ja_JP | CJK locale, yyyy/mm/dd, CJK default document language |
| L4 | tr_TR | dotted and dotless i in case mapping |

A locale cell sets `LANG` and `LC_ALL` of the LibreOffice and pyautogui processes to
`<locale>.UTF-8`, with glibc locale data compiled at start-up by `localedef` from the
image's own `/usr/share/i18n` sources into a `LOCPATH` under the container's `$TMPDIR`
(offline; the image is not changed), and sets the profile's `ooSetupSystemLocale` to the
locale and `ooLocale` (the interface language) to en-US. The keyboard layout stays the X
server's default (us).

### 4.4 Adaptations, and what they leave equal

Two settings change with a level only so that the registered save can run at all; both are
recorded in every save row.

1. A build other than the 7.3 series gets its own `ooSetupLastVersion` in the copied
   profile, so it opens no first-start or what's-new UI over the document. The control's
   profile is the VM's, byte for byte (`xcu.set_props` with no property is the identity; a
   test pins it).
2. Builds from the 7.6 series on title their windows "`<file>` — LibreOffice `<App>`" (an
   em dash; TDF 7.3.7.2 still uses the hyphen), while OSWorld's postconfig activates
   "`<file>` - LibreOffice `<App>`" with `wmctrl -Fa`. The save stage tries the registered
   title first and, only if that fails, the same title with the em dash. The VM's build
   never shows the em-dash title, so the control behaves as registered. In the dev smoke
   every item under 7.6.7.2 and 24.8.7.2 needed it (section 15). Each item's adapted
   activations are recorded and reported per cell: they are what a re-hosted VM with that
   build would fail as written (postconfig replay under other builds was untested,
   dossier O6). Without the fallback the registered save treats the failure as a save
   failure, and every build from 7.6 on would be dropped for retention, so the build arm
   could not be read at all.

Everything else is the registered save: the same profile template, display size, window
manager, VCL plugin (gtk3), pyautogui, timeouts and collection of changed files.

### 4.5 Cells

Each cell changes one factor from the control. 23 cells, run in this order:

| Role | Cells |
|---|---|
| control | `B0.ctrl_s.L0` (the registered save) |
| validity | `B0.ctrl_s.L0.r2` (the control run a second time, in its own session) |
| primary, route arm | `B0.store_as.L0`, `B0.headless_convert.L0` |
| primary, build arm | `B1.ctrl_s.L0` ... `B5.ctrl_s.L0` |
| primary, locale arm | `B0.ctrl_s.L1` ... `B0.ctrl_s.L4` |
| secondary (build x route) | `B1`-`B5` x {`store_as`, `headless_convert`}, at L0 |

Secondary cells get the same tables and readings, labelled secondary; no arm reading uses
them. If the CPU cap of section 14 binds, secondary cells are dropped first, then nothing
else (a primary cell is never dropped for cost).

## 5. Items

Every item is scored in every cell. Items are built by `harness/r04_nuisance/items.py`
from task configs and S1a's records only (no verdict of this study is read).

**Golds** (population `gold`): the checker-mutation study's P1 population, rebuilt by its
own code: every task of the split with a complete gold (`controls.make_jobs`) whose gold
places at least one office file the save stage rewrites (`.docx .xlsx .pptx .odt .ods
.odp`), minus tasks with a setup or postconfig step the harness cannot replay that may write
a checker-read file. Counts: dev 17 (the smoke builder reproduced the dev control run's 17
counted golds), confirm 67, reserve 25. **The registered gold population is the 92 confirm
and reserve golds**, the same 92 as P1 (`integration/prefreeze-counts-v2/counts.json`).

**S1a end states**: every scored S1a episode whose capture holds an office file the checker
read, one item per distinct captured state (`state_sha256`). From S1a's committed records
(`program/evidence/2026-10-10/q2-stage1-analysis/a1.jsonl`; counted before the freeze by
`program/evidence/2026-10-11/r04-nuisance/counts/s1a_counts.py`, which applies the item
builder's rules and lists the 180 sampled fail states), the A1 runs hold 1,084 such
episodes on 69 tasks and 970 distinct states:

| Population | Rule | States | Tasks | Items |
|---|---|---:|---:|---:|
| `s1a_pass` (primary) | every episode of the state scored 1 (the registered score, FAIL rule included) | 270 | 32 | 270 (all) |
| `s1a_fail` (secondary) | every episode scored 0 | 689 | 63 | 180: at most 3 per task, `random.Random(f"r04:s1a-fail:42:{task}")` over the task's sorted state digests |
| `s1a_mixed` (secondary) | anything else (fractional credit, or duplicates that disagree) | 11 | 2 | 11 (all) |

S1a's A1 tasks are all in the confirm split (S1a's pool is the confirm split minus K1
failures and offline exclusions). Its A0a episodes (run 1037: 20 episodes on 5 dev tasks;
8 pass states on 2 tasks, 12 fail states on 3) are the dev items of the smoke. Every
capture file an item uses is checked against S1a's committed per-file digest before it
becomes an item.

Registered population per cell: 92 golds and 461 S1a states (553 items). The unit of the
gold reading is the task (one gold per task); the unit of the S1a reading is the task, with
states nested in it.

## 6. Pipeline (CPU only, one Slurm job at a time)

`infra/r04-nuisance/run/r04_host.py` renders every job through the unchanged lane and
submits a plan's next job only when `squeue` is empty and the previous job's receipt has
exit status 0:

1. **items** (metric image): `python -m harness.r04_nuisance.items` for the split, with the
   S1a runs mounted read-only and checked against their committed digests.
2. **save** (one job per build, in that build's image): `infra/r04-nuisance/run/resave.sh`
   runs `harness.r04_nuisance.resave` with N workers, each on its own Xvfb display, every
   cell of the build in sequence. Each (item, cell) gets the registered save row
   (`reachability.run_job`, or its headless variant for `headless_convert`), plus the
   cell, the build identity (`soffice --version`; for B0 also the dpkg version, refused
   unless it is the VM's), what was set in the profile and the environment, and the
   adapted activations.
3. **score** (metric image): `python -m harness.r04_nuisance.score` merges each saved
   candidate (`controls.merge_lo`: a save that failed is excluded, never scored on its
   pre-save bytes) and scores it with the pinned `DesktopEnv.evaluate()` and with the
   corrected comparator: golds through `offline_eval`'s worker (initial state, VM
   baseline, candidate files, one non-FAIL action), S1a states through
   `rescore._capture_worker` over a derived capture (the captured files with the saved
   outputs in place, the captured task cache, the episode's own last action). `raw`
   scores the items unsaved (golds) or as captured (S1a). Each checker version is scored
   twice in fresh processes; a timeout is retried twice.
4. **analysis** (anywhere, standard library): `python -m harness.r04_nuisance.analysis`.
5. **confirmation rounds** (section 7): `r04_host.py confirm` re-runs steps 2-3 for the
   control and every cell with a discordance, on the discordant items only, twice.

## 7. Outcome and comparison

- **Verdict** of an (item, cell, checker): `pass` iff score is 1.0, `fail` otherwise,
  `error` if `evaluate()` raised (three categories; a change between any two is a
  discordance).
- **Valid pair**: the item is saved without failure, scored without an infrastructure
  failure, and its two scorings agree, in both the control and the cell.
- **Discordance**: a valid pair whose cell verdict differs from its control verdict.
- **Confirmed discordance**: both confirmation rounds re-save and re-score the item under
  the control and under the cell in fresh sessions, and each round reproduces both
  verdicts. A discordance a round does not reproduce, or for which a round is invalid, is
  **unstable**: harness instability, counted and listed, never a finding.
- Counts per cell: `k_gold` = confirmed discordant golds (registered splits); `t_s1a` =
  S1a tasks with at least one confirmed discordant `s1a_pass` state. Secondary: the same
  for `s1a_fail` and `s1a_mixed`.
- Checkers: the pinned checker is primary. The corrected comparator (`zinv`, scored where
  a task's checker is `compare_pptx_files`; elsewhere it equals the pinned verdict) gets the
  same tables and readings as a secondary checker.

## 8. Validity gates and retention (kill criteria)

- **V1 (control reproduces P1's save).** The control cell's gold verdicts equal the frozen
  control runs' saved-gold verdicts (lock venv) on the registered golds, with at most one
  difference. If V1 fails, every reading is INVALID; the run is reported and a successor
  needs a new id.
- **V2 (the save is repeatable).** The replicate cell has no confirmed discordance with the
  control in any population. If V2 fails, every reading is INVALID as above. Unstable
  replicate discordances are reported.
- **Cell retention.** A cell is retained if its save stage succeeded (no save failure, no
  infrastructure error) on at least 90% of its gold items and of its S1a items. A build is
  retained if its `ctrl_s` cell is; a dropped build takes all its cells with it. A locale
  is retained if its data compiled and its cell is retained. A dropped level reads
  NOT_EVALUABLE and is reported with its failure reasons; it is not rerun under this id.
- **Arm stop.** The build arm reads NOT_EVALUABLE if fewer than two of B1-B5 are retained.
  A locale whose data cannot be compiled offline is dropped, not the study.

## 9. Decision rules

Per primary cell, on the pinned checker:

- **DRIFT** if `k_gold >= 3` or `t_s1a >= 3`;
- **INVARIANT** if `k_gold = 0` and `t_s1a = 0`;
- **MINOR** otherwise (one or two confirmed discordant golds or tasks, each listed);
- **NOT_EVALUABLE** if the cell, its build or its locale was not retained;
- **PENDING** while a discordance waits for its confirmation rounds.

Per arm (route, build, locale), over its retained primary cells: DRIFT if any cell is
DRIFT; INVARIANT if every cell is INVARIANT; NOT_EVALUABLE if none is retained (build arm:
fewer than two builds); MINOR otherwise. A failed V1 or V2 makes every reading INVALID; a
gate that has not been evaluated leaves the readings marked pending.

The same rule applies to every arm (the slate's build and locale lines were inconsistent,
J1). What a reading licenses: INVARIANT bounds the level's gold discordance rate below
3.2% and its S1a task-level rate below 8.9% (exact one-sided 95% bounds at 0 of 92 and 0 of
32); DRIFT means at least three golds or three tasks whose verdict the level changes,
reproducibly; MINOR lists one or two. INVARIANT for an arm closes the line as an addendum to
the checker note; DRIFT names the level and the flipped items for the checker note and for
S2 v3's Phase 0.

Registered computation: `harness/r04_nuisance/analysis.py` (`analyze`), with the run's
items, the score rows of every cell, the two confirmation rounds and the frozen control
summaries. No choice is left to make after a result is read.

## 10. Operating characteristics

Exact, from `harness/r04_nuisance/power.py`
(`program/evidence/2026-10-11/r04-nuisance/power.json`): golds independent with a true
per-gold discordance rate `r_gold`; S1a tasks with the registered state counts, each task
susceptible with probability `r_task` and each of its states then discordant with
probability `q`; spurious harness discordances at rate `p0` per run, which count only if both
confirmation rounds reproduce them (`p0^3`).

Bounds at the registered sizes: 0 of 92 golds gives an exact one-sided 95% upper bound of
3.20% (1 of 92: 5.05%; 2: 6.69%); 0 of 32 S1a tasks gives 8.94%. DRIFT has power 0.8 at a
true gold rate of 4.6% and 0.9 at 5.7%; on S1a alone it has power 0.8 at a task rate of 14.1%
(`q` 0.5), 12.9% (`q` 1) or 24.5% (`q` 0.1).

Cell readings, `q` 0.5, no harness noise (P(INVARIANT) / P(MINOR) / P(DRIFT)):

| `r_gold` \ `r_task` | 0 | 0.05 | 0.10 |
|---|---|---|---|
| 0 | 1.000 / 0.000 / 0.000 | 0.222 / 0.598 / 0.180 | 0.046 / 0.381 / 0.573 |
| 0.01 | 0.397 / 0.538 / 0.065 | 0.088 / 0.678 / 0.233 | 0.018 / 0.381 / 0.601 |
| 0.02 | 0.156 / 0.564 / 0.280 | 0.035 / 0.556 / 0.409 | 0.007 / 0.301 / 0.692 |
| 0.03 | 0.061 / 0.416 / 0.524 | 0.013 / 0.377 / 0.609 | 0.003 / 0.201 / 0.797 |
| 0.05 | 0.009 / 0.147 / 0.844 | 0.002 / 0.126 / 0.872 | 0.000 / 0.066 / 0.934 |
| 0.10 | 0.000 / 0.004 / 0.996 | 0.000 / 0.003 / 0.997 | 0.000 / 0.002 / 0.998 |

Under no true effect, the chance that any of the 11 primary cells reads DRIFT is 0 without
harness noise, 3e-11 at `p0` 1%, 6e-5 at 5% and 0.027 at 10%; the chance that any reads
other than INVARIANT is 0.004 at `p0` 1% and 0.39 at 5%. Harness noise of 5% per run would
show in the replicate cell (V2) and in the unstable counts before it could change a
reading. The dev smoke's replicate and unstable counts are in section 15.

The design is decisive by construction: both populations are fixed and fully scored, so
every retained cell reaches a reading; the open risk is retention (section 8), which the
dev smoke measured.

## 11. Reported regardless of outcome

- Validity gates V1 and V2, with every difference and every unstable replicate item.
- Per cell and checker: retention (items saved per population), valid pairs, discordances
  (all, confirmed, unstable, pending), the confirmed ones by direction (`pass->fail`,
  `fail->pass`, `*->error`, `error->*`) and by checker family, with item- and task-level
  exact intervals and, for S1a, the task-equal state-level share with a task-cluster
  bootstrap (10,000 resamples, seed 42); every discordant item with its task, population,
  verdicts, status and the digests of the control's and the cell's saved office files.
- Every cell's flip set against the unsaved item (golds) or the captured state (S1a), and
  its Jaccard overlap with the control's flip set (the slate's "same flip set").
- The P1 replication (control against the unsaved gold, the registered 92) and S1a's fixed
  point (control against the captured state, per S1a population).
- Save timing per cell (median, 90th percentile, maximum, saves slower than 0.5 s), dialogs,
  saves that changed no byte, items with an adapted window activation, and every save
  failure with its reason.
- Each build's identity (`soffice --version`, image ID, tarball SHA-256), each locale's
  compiled `LC_NUMERIC`/`d_fmt`, and every profile property set.
- Both checkers' readings; CPU hours used; every Slurm job, receipt and deviation.

## 12. Infrastructure failures

A save that failed (open or activation failure after the adaptation of section 4.4, an
unwritten save, a conversion that produced nothing, a container error) excludes the item
from that cell (`save_failed`), counts against retention and is never scored on its
pre-save bytes. A scoring that timed out after two retries, met a live getter or a refused
network fetch, or whose process died is an infrastructure failure for that (item, cell). A
checker exception is the verdict `error`, not a failure. A Slurm job that fails is rerun in
full under a versioned run name, at most twice; nothing from a failed attempt is merged into
a later one.

## 13. Data handling

Public repository. Documents stay on the host: the gold files (third-party content from the
file cache), S1a's captures, every saved file, every derived capture and the save stage's
working trees stay under `~/cotcodec-runs/stage0/r04-nuisance/` (derived captures are
deleted after scoring). The repository receives only the item manifest (task ids, VM paths,
container paths and digests), score rows (scores, verdicts, digests, save events: timing,
dialogs, whether bytes changed; no event log, no stdout tail, no document text), the analysis
JSON, receipts and Slurm records. `score.save_summary` drops the save stage's event log; a
test pins that. No host address is recorded. Nothing is released that the checker-mutation
study would not release.

## 14. Caps

- **GPU: 0 GPU-h.** No job requests a GRES; the lane refuses a GPU.
- **CPU:** the lane runs one job at a time with at most 32 CPUs. Scaled from the dev smoke's
  measured rates (section 15) to the registered 553 items x 23 cells plus the unsaved
  scores, with 16 workers on 32 CPUs: save stage about 1.0 h, scoring about 7.5 h, two
  confirmation rounds about 1 h, so about 9.5 lane-hours (about 300 CPU-h). Cap: 20
  wall-clock hours of the 32-CPU lane (640 CPU-h) for the main run and both confirmation
  rounds together. If the projection from the first save job exceeds the cap, secondary
  cells are dropped (section 4.5), and the drop is reported.
- **Downloads:** the five TDF tarballs (1.04 GB in all), already fetched by the image builds
  on 2026-10-11 and recorded in the build receipts.

## 15. Dev-split smoke tests (exploratory; before the freeze)

Allowed before the freeze and reported as exploratory; no confirm or reserve item was built,
saved or scored. The full record is `program/evidence/2026-10-11/r04-nuisance/`.

Items: the 17 dev golds (the item builder reproduced the dev control run's 17 counted golds
from configs) and 17 S1a A0a states (8 pass states on 2 tasks, 9 of 12 fail states), every
capture checked against S1a's committed digests. Images B1-B5 built in about 25 s each
(jobs 1104-1108); an inspection job (1103) read the LO-VM image's locale sources and
profile.

- **dev-smoke-v1** (5 cells; jobs 1109-1112): V1 held (17 of 17 control gold verdicts
  equal the frozen dev control run's, the dev P1 flip `af23762e` included); `store_as` and
  `headless_convert` at B0 changed no verdict; B3 failed every save on window activation
  (the em-dash titles), which led to the title fallback of section 4.4; de_DE flipped one
  gold (`6e99a1ad`, `compare_table`): the task's postconfig CSV export writes decimal commas
  under de_DE (7 of 8 lines, checked structurally on the host). That is the path the
  judges predicted (a conversion, not an OOXML re-save).
- **dev-smoke-v2** (save stage of 17 cells; jobs 1114-1121): every cell saved every item
  except `store_as` under TDF 7.6 and 24.8, where Ubuntu's 7.3 UNO client failed ("Binary URP
  bridge disposed during call"); fixed by using each build's own Python (section 4.2). The
  title fallback was needed on every item under 7.6.7.2 and 24.8.7.2 and on none under TDF
  7.3.7.2. All four locales compiled offline. Stopped before scoring; superseded by v3.
- **dev-smoke-v3** (all 23 cells at the fixed code, scored, both confirmation rounds; jobs
  1125-1151): V1 and V2 held (the replicate, in its own container, changed no verdict);
  every item was saved in every cell; no save timed out or showed a dialog. Route arm
  INVARIANT; build arm MINOR (B1-B3 INVARIANT; B4 and B5 each flip two Impress golds,
  `4ed5abd0` on `compare_pptx_files_robust` and `e4ef0baf` on `compare_pptx_files`, pass to
  fail in all three routes, the corrected comparator too); locale arm MINOR (de_DE, ar_EG and
  tr_TR flip `6e99a1ad` through the CSV export; ja_JP INVARIANT). Both rounds reproduced
  every discordance (15 of 15 per checker, 0 unstable). No S1a A0a state changed verdict in
  any cell. On 17 golds no cell reached DRIFT; the dev rates (2 of 17 for B4 and B5) suggest
  the build arm may reach DRIFT on the registered 92, which the design can detect (section
  10).
- **dev-smoke-v4-control** (jobs 1152-1155, at the latest code of record): the item builder
  verified the mounted inputs against the checker-mutation study's pins and rebuilt v3's
  manifest byte for byte; the control's 34 verdicts equal v3's and the replicate's equal the
  control's. A confirm-split plan was refused by the freeze guard before any job existed.

No decision rule, threshold, population or level changed after a smoke result was read. The
two fixes the smokes led to (the window-title fallback and the build's own UNO client) are
harness repairs that let the registered save run under the builds; both are recorded per
item, and neither touches a rule.

Cost of all R04 host jobs so far (37 CPU-only jobs, about 84 minutes of lane time): 25.5
allocated CPU-h, 0 GPU-h. Measured in v3, per (item, cell): 4.6 worker-seconds to save and
32.5 worker-seconds to score (both checkers, two fresh-process scorings each).

## 16. Corrections to the slate's version

| Slate version | This draft | Source |
|---|---|---|
| INVARIANT "below a 3% upper bound" on the locale arm | the same rule on every arm; INVARIANT is 0 confirmed discordances, whose bound is 3.20% on 92 golds; the bound is reported, not used as a threshold | J2, dossier O8 (zero flips on 92 gives 3.2%) |
| build: "at or below 5% audit-confirmed flips"; locale: "below a 3% upper bound"; DRIFT at 10% or 3 tasks or 2 family flips | one rule: DRIFT at 3 confirmed discordant golds or 3 S1a tasks, INVARIANT at 0, MINOR otherwise, for every arm | J1 (inconsistent thresholds) |
| flips go to the model raters, splits to Kevin; rates of audit-confirmed flips | no audit in this registration: the outcome is the verdict change against a paired control, which needs no rater; discordances are listed with what changed for a later audit | 0 GPU-h; the rater lane is GPU and the Claude path is not a GPU-free census |
| "the same flip set as the control" | pairing with the control (discordance) is the primary comparison; the flip-set overlap is reported | a paired comparison answers it directly |
| Arm B re-saves "through the kit's GUI save path" | the registered save stage with the locale applied to the LibreOffice and pyautogui processes, locale data compiled offline from the image's own sources | dossier precondition: "locale data installs offline" |
| Arm A needs root-free builds | derived images, `dpkg-deb -x` into `/opt`, dpkg database unchanged, no root on the host | dossier O6 |
| keystroke input arm (descriptive) | not in this registration | needs the certified VM path |
| CPU estimate "10-20 CPU-h per arm", unverifiable | measured on the dev smoke | c202 (UNVERIFIABLE) |
| "save paths": Ctrl+S, Save As same format, the task's convert step | `ctrl_s` (which includes the task's own conversions), `store_as` and a headless same-format round trip | the headless round trip is the path the scoping probe used (7 of 63 flips) |

The judges' other point stands as a prediction, not a design change: OOXML stores
locale-neutral values, so locale re-saves are expected to be INVARIANT, and any locale flip
is expected in a conversion or a date or text path (J1, J3).

## 17. Freeze checklist and sign-offs

Before a freeze: (1) a pre-freeze audit by a fresh reviewer, its findings fixed or recorded;
(2) the code-tree digest of the code of record and the commit filled in section 3; (3) the
dev smoke rerun at the frozen commit if any code of record changed after it; (4) the program
owner's freeze (`scripts/preregister.py freeze`), which is Kevin's step and not the drafting
agent's. Kevin's items: whether R04 runs at all (the dossier filed it under S2 v3's Phase 0);
review of the two adaptations of section 4.4; the CPU cap.

## 18. Priors

- P1 of the checker-mutation study: a GUI-faithful save of the gold flips 4 of 92 golds
  (exact 95% 1.20-10.76%), 3 audit-confirmed; the headless scoping round trip flipped 7 of
  63 and 1 of 26 (`program/evidence/2026-10-08/q2-mutation-confirm/results/README.md`).
- How Benchmarks Mis-Score Computer-Use Agents, arXiv 2607.28367
  (https://arxiv.org/abs/2607.28367, 2026-07-30): one OSWorld task unsatisfiable on the
  released VM image; no gold round trip.
- Finding Blind Spots in AppWorld and WorkArena Task Verifiers, arXiv 2610.09142
  (https://arxiv.org/abs/2610.09142, 2026-10-06): web and API verifiers; names
  OSWorld-Verified-class desktop checkers as outside its scope.
- OSWorld 2.0, arXiv 2606.29537 (https://arxiv.org/abs/2606.29537): new images and
  construction-time QA; no cross-version invariance test reported.
- Multilingual Verifier Bias in RLVR, arXiv 2608.20362 (https://arxiv.org/abs/2608.20362):
  exact-match false negatives depend on language (Qwen3-8B JP 0.642 against EN 0.122); math,
  not GUI state checkers.
- macOSWorld, arXiv 2506.04135 (https://arxiv.org/abs/2506.04135): localized environments in
  five languages; checkers not audited for locale.
- Chen et al., Metamorphic Testing: A Review of Challenges and Opportunities, ACM Computing
  Surveys 51(1), 2018 (https://doi.org/10.1145/3143561).
- Claim boundary: no prior found that applies metamorphic null transformations across
  LibreOffice builds and locales to desktop benchmark checkers (the renewal sweep's
  searches, STILL_OPEN, 2026-10-11).

## 19. Code of record

| Path | Role |
|---|---|
| `harness/r04_nuisance/levels.py` | factor levels, cells, profile and environment per cell |
| `harness/r04_nuisance/xcu.py` | profile edits |
| `harness/r04_nuisance/resave.py`, `uno_store_as.py` | the save stage per cell (reuses `harness/q2_mutation/reachability.py` unchanged) |
| `harness/r04_nuisance/items.py` | items (reuses `controls.make_jobs`, `offline_eval`'s setup emulation) |
| `harness/r04_nuisance/score.py` | scoring (reuses `offline_eval`'s worker and `rescore._capture_worker`, `rescore._job_worker`, `zinv`) |
| `harness/r04_nuisance/analysis.py` | the registered analysis |
| `harness/r04_nuisance/power.py` | operating characteristics |
| `harness/r04_nuisance/guard.py` | the freeze guard |
| `infra/r04-nuisance/` | Dockerfile template and renders, the host tool, the worker wrapper |
| `tests/test_r04_nuisance.py` | tests |
