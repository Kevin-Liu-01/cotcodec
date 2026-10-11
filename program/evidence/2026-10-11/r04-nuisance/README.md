# R04 nuisance invariance: images, operating characteristics and dev-split smoke tests (2026-10-11)

**Blind warning.** The score rows and analyses here name checker verdicts per gold task and
per S1a state, as the checker-mutation study's released analysis does. Kevin's adjudication
of that study's pool and his human spot check are pending: to stay blind, answer them before
reading these files (`program/evidence/2026-10-08/q2-mutation-confirm/results/README.md`,
"Pending for Kevin"). R04 reads no audit, decision, adjudication or rater file. Every
reading here is "offline harness, VM fidelity unverified" (the parent's K2 label;
registration section 2.1).

Evidence for the DRAFT registration `r04-checker-nuisance-invariance-v1`
(`program/preregistrations/r04-checker-nuisance-invariance-v1.md`), decision D73 (iii).
**Exploratory and pre-freeze**: only the dev split ran; no confirm or reserve item was built,
saved or scored; nothing here is a registered result. Every host job was CPU-only (no
GRES) through the unchanged lane `infra/slurm/host-single-node/q2-mutation-cpu.sbatch`,
submitted only on an empty queue by `infra/r04-nuisance/run/r04_host.py`. One container ran
outside the lane: a bare `docker run` of the B3 image that printed the build's own records
under `/opt/r04` (the dpkg listings before and after the unpack, `soffice --version`, the
bundled Python files, the tarball's identity), named in the drafting owner's report and in
pre-freeze audit 1; it read no document and queued no job.

## Contents

| Path | What it is |
|---|---|
| `power.json` | exact operating characteristics of the cell and arm readings (`harness/r04_nuisance/power.py`) |
| `images/` | the five derived LibreOffice images: per build the record of `r04_host.py check-image` (image ID, tag, layers added to the LO-VM image), the lane's build receipt and build log, and the submission record; `images.json` maps builds to image IDs |
| `dev-smoke-v1/` | first smoke: 5 cells; items, scores, save summary, analysis |
| `dev-smoke-v2/` | second smoke: the save stage of 17 of the 23 cells (B0, its replicate, B1-B3), stopped before B4, B5 and scoring when the `store_as` client defect showed; items and save summary |
| `dev-smoke-v3/` | the smoke of record: all 23 cells at the fixed code, scored and analysed, with both confirmation rounds |
| `dev-smoke-v4-control/` | the control and replicate at the latest code (input check, freeze guard) |
| `dev-smoke-v5/` | the whole registered procedure on the dev split at the code that fixes pre-freeze audit 1 (`e56fb45`): a mirror of the host run directory without documents (plan, items, per-job receipts, score rows, save summaries, the rounds' pending list), `analysis-main.json` and `analysis.json` from `analysis --run` |
| `counts/` | pre-freeze count of the registered S1a items from S1a's committed records |

No document is here: no gold, capture or saved file, no event log, no stdout tail. Items
carry VM paths, container paths and digests; score rows carry scores, verdicts, digests and
save events (timing, dialogs, whether bytes changed).

## Images (jobs 1104-1108)

Each image is the LO-VM image (`sha256:f5b4c40e...`, tag checked before the build) plus one
layer: TDF's deb tarball fetched from TDF's archive, size and SHA-256 checked against TDF's
statement, each `.deb` unpacked with `dpkg-deb -x` under `/opt` (dpkg database byte-identical
before and after), `soffice --version` checked. About 25 s per build.

| Build | TDF version | Image | Tag | Job |
|---|---|---|---|---|
| B1 | 7.3.7.2 | `sha256:fd1f1bfed3e6...` | `cotcodec-q2-r04-lo-b1:8b8b405e9c3f` | 1105 |
| B2 | 7.6.7.2 | `sha256:c39f6957ec75...` | `cotcodec-q2-r04-lo-b2:477adcc3ed81` | 1106 |
| B3 | 24.8.7.2 | `sha256:728aaa69a5ea...` | `cotcodec-q2-r04-lo-b3:1d29bbbfea03` | 1104 |
| B4 | 25.8.7.3 | `sha256:87af250e3cd8...` | `cotcodec-q2-r04-lo-b4:00b54883d1c1` | 1107 |
| B5 | 26.2.6.2 | `sha256:6cf86ce55e0c...` | `cotcodec-q2-r04-lo-b5:2043b4262ffe` | 1108 |

Tags end in the first 12 hex digits of the rendered Dockerfile's SHA-256, which match the
committed `infra/r04-nuisance/lo-tdf/<build>/Dockerfile`. Full IDs: `images/images.json`.

## Inspection job (1103)

One CPU job in the LO-VM image read the image's facts: Ubuntu's python3-uno present;
`localedef` and the `de_DE`, `ar_EG`, `ja_JP`, `tr_TR` sources under `/usr/share/i18n`
present; compiled locales en_* only; the VM profile sets `ooLocale` en-US,
`ooSetupLastVersion` 7.3, `FirstRun` and `ShowTipOfTheDay` false, `WarnAlienFormat` false.
This set the locale design (compile at start-up, no new image).

## dev-smoke-v1 (jobs 1109-1112; code `c9e3189`)

Items: 17 dev golds (the dev control run's 17 counted golds, reproduced from configs) and 17
S1a A0a states (8 pass on 2 tasks; 9 of 12 fail states, sampled at most 3 per task).
Cells: control, `B0.store_as`, `B0.headless_convert`, `B3.ctrl_s`, `B0.ctrl_s.L1`.

- V1: the control's 17 gold verdicts equal the frozen dev control run's saved verdicts
  (`dev-controls-v9-summary.json`), the dev P1 flip `af23762e` included.
- `store_as` and `headless_convert` at B0: no discordance (17 golds, 8 pass states, 9 fail
  states).
- `B3.ctrl_s`: every item's save failed on window activation. TDF 24.8 titles windows
  "`<file>` — LibreOffice `<App>`" (em dash); OSWorld's postconfig activates
  "`<file>` - LibreOffice `<App>`" with `wmctrl -Fa`. The registered save treats that as a
  save failure, so the build would have been dropped. Fixed by the title fallback of the
  registration's section 4.4 (the registered title first, the em-dash title only if it
  fails; recorded per item).
- `B0.ctrl_s.L1` (de_DE): one gold discordance, `6e99a1ad` (`compare_table`, "keep two
  decimal points"), pass under en_US and fail under de_DE. The task's postconfig converts the
  saved `.xlsx` to CSV; under de_DE LibreOffice's CSV export writes the numbers with a
  decimal comma (quoted), on 7 of the CSV's 8 lines (checked on the host by a structural
  comparison, no content copied). This is the judges' predicted path (a conversion, not the
  OOXML re-save). Not confirmed in v1 (no rounds ran); v3 repeats it.

## dev-smoke-v2 (jobs 1114-1121, save stage only; code `b116f11`)

The save stage of 17 cells (all B0 cells, the replicate, and B1-B3 with their three routes)
ran on the same 34 items; the B4 and B5 jobs and scoring were not reached. Every cell saved
every item, except
`store_as` under TDF builds: the UNO client was Ubuntu 7.3's pyuno for every build, and
against TDF 7.6 it failed on Writer and Impress documents (17 of 34 saves unwritten) and
against 24.8 on every document ("Binary URP bridge disposed during call"). Fixed: each build
drives its instance with its own bundled Python and pyuno. The title fallback was needed on
every item under B2 (7.6.7.2) and B3 (24.8.7.2) and on none under B1 (TDF 7.3.7.2): the
em-dash titles arrived between 7.3 and 7.6. Locale data compiled offline for all four
locales. v2 was stopped before scoring and superseded by v3.

## dev-smoke-v3 (the smoke of record; jobs 1125-1151; code `ac58b58`)

All 23 registered cells on the 34 dev items, scored with the pinned checker and the corrected
comparator, then both confirmation rounds on every discordant item (3 items x the 9 cells with
a discordance, plus the control). `analysis.json` is the registered analysis over the main
run and both rounds (`analysis-main.json`: the main run alone; `pending-round-1.json`: what
the rounds re-ran; `pending-after-rounds.json`: nothing left pending).

**Validity.** V1 passed (17 of 17 control gold verdicts equal the frozen dev control run's).
V2 passed: the replicate cell, run in its own container, changed no verdict. Every item was
saved in every cell (retention 100% everywhere); no save timed out or showed a dialog.

**Readings on the dev split (exploratory; pinned checker, the corrected comparator agrees on
every cell):**

| Arm | Cells | Reading |
|---|---|---|
| route | `B0.store_as`, `B0.headless_convert` | INVARIANT (0 discordances) |
| build | B1 (TDF 7.3.7.2), B2 (7.6.7.2), B3 (24.8.7.2): INVARIANT; B4 (25.8.7.3), B5 (26.2.6.2): MINOR | MINOR |
| locale | de_DE, ar_EG, tr_TR: MINOR; ja_JP: INVARIANT | MINOR |

Every discordance was a gold going from pass to fail, and both rounds reproduced every one
(15 of 15 (item, cell) discordances confirmed under each checker, 0 unstable):

- `4ed5abd0` (`compare_pptx_files_robust`) and `e4ef0baf` (`compare_pptx_files`), two
  Impress golds, fail under B4 and B5 in all three routes and pass under B0-B3. The corrected
  comparator fails them too, so this is not the z-order defect.
- `6e99a1ad` (`compare_table` on the postconfig's CSV export) fails under de_DE, ar_EG and
  tr_TR and passes under ja_JP: the decimal-separator path seen in v1.

No S1a A0a state (8 pass, 9 fail) changed verdict in any cell. The control reproduced the dev
P1 flip (`af23762e`, pass unsaved, fail saved) and every cell's flip set against the unsaved
item contains it. On these 17 golds, DRIFT (3 or more) was not reached by any cell; at the
registered 92 golds the B4/B5 and locale lines are the ones to watch.

Save timing: the registered save wrote within 0.30 s (median 0.10 s); `store_as` returns
after the write; `headless_convert` takes about 0.9-1.5 s per file (a different path, not
read by a checker 0.5 s after Ctrl+S). The title fallback was used on every item under
B2-B5 (`ctrl_s` and `store_as`) and on none under B0 and B1.

## dev-smoke-v4-control (jobs 1152-1155; code `16c1233`)

The control and the replicate at the latest code of record (the item builder now checks the
freeze guard and the mounted inputs). The item builder verified the mounted inputs against
the checker-mutation study's pins (OSWorld tree `4153c686...`, VM baseline `f3253818...`,
447 file-cache files) and wrote a manifest identical to v3's (`8c6227b8...`). The control's
34 verdicts equal v3's control verdicts, the replicate's equal the control's, and the
unsaved scores equal v3's. A plan for the confirm split was refused by the host tool before
any directory or job existed ("runs only after r04-checker-nuisance-invariance-v1 is
frozen").

## dev-smoke-v5 (jobs 1164-1185; code `e56fb45`, code tree `1ffe2d19...`)

The procedure of the registration's section 6 at the code that fixes pre-freeze audit 1,
on the dev split: `r04_host.py plan --split dev --golds --s1a 1037` with all 23 cells, 8
workers and a 2 lane-hour cap; `next` until complete (items, seven save jobs, the six score
jobs); `analysis --run` with `--pending-out`; `r04_host.py confirm` (both rounds at once);
`next` until complete; `analysis --run` again. Every job finished on its first attempt; no
step was dropped or stopped.

- The item builder checked the 17 dev golds against P1's counted dev golds of the frozen dev
  control run and wrote v3's manifest again (`8c6227b8...`).
- All 816 (item, cell) verdicts of the main run, both checkers, equal dev-smoke-v3's; no
  saved office file has v3's SHA-256 (the saves are not byte-deterministic).
- `analysis-main.json`: control retention, V1 and V2 pass; route INVARIANT; the same 15
  discordances as v3 pending (3 items under 9 cells), so `"complete": false`;
  `pending.json` is its pending list, which `confirm` copied to `rounds/pending.json`.
- `analysis.json` (both rounds): every discordance confirmed (15 of 15, 0 unstable, no
  `harness_noise` flag), `"complete": true`; route INVARIANT, build MINOR (B4 and B5:
  `4ed5abd0`, `e4ef0baf`), locale MINOR (de_DE, ar_EG, tr_TR: `6e99a1ad`), as in v3, under
  both checkers; the control reproduces the dev P1 flip `af23762e`.
- Job times against the projections of section 6 (8 workers): save jobs 0.4-2.4 minutes
  (projected 0.3-2.3), main score jobs 4.3-10.8 minutes (projected 4.6-11.5); the round
  score jobs took 7.0-7.1 minutes against 2.0 projected, because the scorer runs a job's
  cells one after another and a round with fewer items than workers leaves workers idle
  (the 60-minute floor covers it). 22 jobs, 75.5 lane-minutes (59.4 for the main run),
  20.1 allocated CPU-h.

Reproduce from this directory: `python -m harness.r04_nuisance.analysis --run
program/evidence/2026-10-11/r04-nuisance/dev-smoke-v5 --src . --out OUT.json`.

## Pre-freeze audit 1: independent reproduction (jobs 1156-1158, 1160; exploratory)

The auditor reran the dev smoke's control, de_DE and B4 cells from the staged export
`16c1233` (code tree equal to `4b2acf2`'s, checked by digest), plan `audit-r04-repro-1`:
jobs 1156 (items), 1157 (save B0), 1158 (save B4) and 1160 (score), CPU only, each submitted
on an empty queue (1159 was another agent's job and did not overlap); about 7 minutes of
lane time and about 1.9 allocated CPU-h. All 17 dev golds gave the same raw, control, de_DE
and B4 verdicts as dev-smoke-v3 under both checkers: `6e99a1ad` fails under de_DE,
`4ed5abd0` and `e4ef0baf` fail under B4 (`zinv` too), and the control's dev P1 flip
`af23762e` reproduced. Every saved item's office file had another SHA-256 than in v3:
LibreOffice's saves are not byte-deterministic, so the per-discordance digests of the
registration's section 11 identify one session's files, and "byte for byte" in its section
4.4 is about the profile only. The run directory is on the host under
`r04-nuisance/runs/audit-r04-repro-1`; its records are not copied here.

## Cost

| Run | Jobs | Lane wall time | Allocated CPU-h |
|---|---:|---:|---:|
| inspection, five image builds | 6 | about 2.5 min | 0.3 |
| dev-smoke-v1 | 4 | 12.5 min | 3.3 |
| dev-smoke-v2 (saves only) | 6 | 5.8 min | 1.5 |
| dev-smoke-v3 (with both rounds) | 17 | 58.0 min | 18.4 |
| dev-smoke-v4-control | 4 | 5.0 min | 2.0 |
| **Total (drafting owner)** | 37 | about 84 min | 25.5 |
| pre-freeze audit 1 reproduction | 4 | about 7 min | 1.9 |
| dev-smoke-v5 (with both rounds) | 22 | 75.5 min | 20.1 |

GPU: 0. Measured per (item, cell) in v3: save 4.6 worker-seconds, scoring 32.5
worker-seconds (both checkers, two fresh-process scorings each). Projection for the
registered run (553 items x 23 cells, plus the unsaved scores) on the 32-CPU lane with 16
workers: save stage about 1.0 h, scoring about 7.5 h, two confirmation rounds about 1 h:
about 9.5 lane-hours (about 300 CPU-h).
