# R04 nuisance invariance: images, operating characteristics and dev-split smoke tests (2026-10-11)

Evidence for the DRAFT registration `r04-checker-nuisance-invariance-v1`
(`program/preregistrations/r04-checker-nuisance-invariance-v1.md`), decision D73 (iii).
**Exploratory and pre-freeze**: only the dev split ran; no confirm or reserve item was built,
saved or scored; nothing here is a registered result. Every host job was CPU-only (no
GRES) through the unchanged lane `infra/slurm/host-single-node/q2-mutation-cpu.sbatch`,
submitted only on an empty queue by `infra/r04-nuisance/run/r04_host.py`.

## Contents

| Path | What it is |
|---|---|
| `power.json` | exact operating characteristics of the cell and arm readings (`harness/r04_nuisance/power.py`) |
| `images/` | the five derived LibreOffice images: per build the record of `r04_host.py check-image` (image ID, tag, layers added to the LO-VM image), the lane's build receipt and build log, and the submission record; `images.json` maps builds to image IDs |
| `dev-smoke-v1/` | first smoke: 5 cells; items, scores, save summary, analysis |
| `dev-smoke-v2/` | second smoke: the save stage of 17 of the 23 cells (B0, its replicate, B1-B3), stopped before B4, B5 and scoring when the `store_as` client defect showed; items and save summary |
| `dev-smoke-v3/` | the smoke of record: all 23 cells at the fixed code, scored and analysed, with its confirmation rounds |

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

## dev-smoke-v3 (the smoke of record)

Filled in below once the run and its confirmation rounds complete.
