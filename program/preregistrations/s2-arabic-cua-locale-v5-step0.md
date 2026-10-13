# S2 v5 step 0: the screenshot-only canary target rule, its predictions and its stop rule

**Status: a record, not a ledger registration.** Written on 2026-10-13 by the step-0 owner on
branch `stage0/s2-v5`, under decision D94, and committed before step 0 measured anything. No
step-0 job had been submitted and no step-0 screenshot existed when it was committed.
`experiments/manifests/s2v5/step0-rule.json` pins the SHA-256 of every file listed in section
"What is pinned". `canary_targets_v5.analyze` refuses to run if any pinned file differs. The id
`s2-arabic-cua-locale-v5` has no ledger row. Step 0 runs as development under that unfrozen id.
Nothing here is frozen into the ledger.

## Why step 0

v4's K1 failed on one canary entry (D93). On ER, `writer:drag_select_word` read back
"Ykeep word keep" in 5 of 5 sessions, where "keep Y keep" was expected.

D94 found an instrument defect. A6's Writer targets were measured once, on the certified
left-to-right disk S, and never measured again on v4's cell images. Mirroring draws Writer's
document area shifted: ER at (+71, 0), AR at (+71, +1), A at (0, +1), PL and E at (0, 0). That
puts the frozen drag, (680, 292) to (709, 292), in the left margin.

D94 admits a v5 only through step 0. Step 0 is one CPU-only canary-development job, 5 boots on
each of E, A, ER, AR and PL, run under rules committed and SHA-pinned in advance. This file
states those rules. The code that applies them is `harness/s2_locale/canary_targets_v5.py`.

## The target rule (D94)

Targets come from screenshots only, from the glyph boxes of the canary fixture line:

- **Drag** (`drag_select_word`, fixture "keep word keep"): from the left edge of `w` plus 1 px to
  the right edge of `d` minus 1 px. The edges are those of the ink box of the word "word". The
  drag lasts 500 ms, as in q2.
- **Triple-click** (`triple_click_line`, fixture "replace this line"): the middle of `this`, that
  is, the middle of the ink box of "this".
- **y**: the centre of the glyph rows, meaning the line's first and last ink rows.
- **Rounding**: integer midpoints round down, `(a + b) // 2`. q2's own Writer triple-click target
  did the same (718 for "this" at 703-734).

AT-SPI extents play no gating role. q2's measure mode still records them, and step 0's report
copies them for disclosure only. No admission test reads them, and a test checks that changing
them changes no verdict. On the mirrored images they stay at unmirrored coordinates (D94), so
they would reproduce the failing targets.

The segmentation and its thresholds are fixed in code:

| Step | Rule | Constant |
|---|---|---|
| Region | a fixed screen region per app, `[x0, y0, x1, y1)`: Writer `[400, 230, 1600, 360)` (the region also covers the document area at +71), Chrome `[99, 136, 960, 230)`, VS Code `[548, 271, 1350, 330)` | `ROI` |
| Ink | luminance `(299 R + 587 G + 114 B + 500) // 1000`; background = the region's median; ink = at least 80 from it, either polarity | `INK_DELTA = 80` |
| Lines | a column (row) with ink in at least half of the region's rows (columns) is cleared: Writer's page border, Chrome's frame | `LINE_COVERAGE = 0.5` |
| Bands | maximal runs of rows holding ink | |
| Caret | in a band, a column whose longest vertical ink run is at least 0.9 of the band's height is cleared | `CARET_RUN = 0.9` |
| Words | glyph runs (column runs) closer than 6 px (Writer, VS Code) or 11 px (Chrome) merge; this is about 0.75 of the app's character pitch | `WORD_GAP_PX` |
| Fixture line | the single triple of consecutive words, in exactly one band, whose widths fit the fixture's word lengths (from `n p - 0.75 p` to `n p + 0.5 p`, with p the pitch from `canary_targets.json`: 7.94, 14.4 and 8.43 px) and whose gaps are single spaces (at most `2 p`). If there is none, or more than one, the measurement fails. | `PITCH_PX`, `WIDTH_LOW`, `WIDTH_HIGH`, `SPACE_GAP_MAX` |
| Glyph rows | the first and last ink rows within the triple's columns | |

**Development check before the commit.** The rule was run on q2's own measurement screenshots
from development runs 515 and 501 on the certified disk, 2026-10-07. These are the screenshots
`canary_targets.json` cites for its targets. They stay on the host. Their SHA-256 values are in
`REFERENCE`, and their regions are committed as test fixtures in `tests/fixtures/s2v5_step0/`.

The rule reproduces q2's Writer and VS Code targets within 1 px:

| App | Rule on run 515 (the reference) | q2's frozen target | Largest offset |
|---|---|---|---:|
| Writer drag | (680, 293) to (708, 293) | (680, 292) to (709, 292) | 1 |
| Writer triple-click | (718, 293) | (718, 292) | 1 |
| Chrome drag | (172, 151) to (225, 151) | (172, 150) to (228, 150) | 3 |
| Chrome triple-click | (242, 151) | (244, 150) | 2 |
| VS Code drag | (609, 284) to (639, 284) | (609, 284) to (640, 284) | 1 |
| VS Code triple-click | (649, 284) | (650, 284) | 1 |

Robustness:

- The reference values are identical for every ink threshold from 48 to 96, and within 1 px up
  to 144.
- Run 501, another boot of S, gives the same glyph boxes. Its Writer drag region is
  byte-identical to run 515's.
- Chrome's caret was visible in one boot and not in the other. It was removed, and the result is
  the same.
- A Writer caret added to the real region changes nothing, and neither does erasing VS Code's
  cursor.
- Synthetic glyph lines are measured correctly under shifts, under a caret at either end, and
  with ER's page border and the crop marks present. A synthetic region with no fixture line, or
  with two, fails.

The thresholds were set on these development screenshots. No step-0 data existed.

## The Chrome reference (a disclosed reading of the task)

q2 took its Chrome targets from accessibility character cells. Its drag end, 228, is the right
edge of the cell of `d`. The ink of `d` at 24 px ends 3 px earlier, at 226. An ink rule therefore
cannot reproduce q2's frozen Chrome drag end within 2 px, even on q2's own screenshot: the
reference itself is 3 px away. Comparing against the frozen number would make step 0 fail by
construction on all five images.

So Chrome's and VS Code's step-0 targets are compared with the reference. The reference is this
rule applied to the screenshots q2 measured its targets on, which is q2's measurement read by the
step-0 rule. The comparison with q2's frozen numbers is reported for disclosure.

D94's own numbers concern Writer's document area. Writer is compared with q2's frozen targets, as
D94 states it.

## The step-0 job

`harness/s2_locale/ap_delta_step0.py` extends `ap_delta`'s development renderer under the unfrozen
id `s2-arabic-cua-locale-v5`. `ap_delta.py` itself is pinned by v4's frozen registration and
admits only v4's id, which is frozen, so this module extends it without editing it.

**What it renders.** One manifest holds ONE q2 `canary-development` campaign per image, in the
order E, A, ER, AR, PL. Each campaign:

- runs on the pinned cell image (`images.json`), with provenance naming the certified disk, as
  `ap_delta.swap_disk` does;
- is admitted by harness/q2's own validator: purpose development, the frozen `q2-action-path-v2`
  registration, no model, seed 42, one VM at a time;
- runs Writer, Chrome and VS Code, with the entries `triple_click_line` and `drag_select_word`;
- has `measure_targets` true;
- has 5 repetitions cut into sessions of 6 trials. That gives 5 cold boots per image, each running
  every (app, entry) pair once;
- uses q2's boot (300 s), settle (60 s) and per-trial (90 s) limits.

The actions use q2's frozen targets: `suite_cells.json` and harness/q2 are unchanged. So on ER and
AR, step 0 repeats v4's drag, this time with screenshots.

**Per-boot screenshots.** q2's measure mode saves the screen before each pointer composite (the
measured screenshot) and after it. It names each file `canary-<trial>-<app>-<entry>.png` in the
campaign's `cycles/` directory, and the trial number restarts in every session. Run through q2's
driver as one process, the 5 boots of a campaign would overwrite one another's screenshots.

`run_canary` therefore runs driver.main's single-VM branch itself, as `ap_delta.run_rung` runs
the concurrent branch:

- it makes the same pre-run checks with harness/q2's own functions;
- it calls `driver.run_cycle`, unchanged, for each session in order;
- after each session it moves that session's screenshots into `cycles/shots-NN/` and records
  their SHA-256 in the session's record.

Nothing inside a session changes.

**CPU only.** The batch file `infra/slurm/host-single-node/s2v5-step0.sbatch` is
`s2v4-apdelta.sbatch` with the names and the program changed. It has no GRES line and refuses a
GPU allocation or GPU environment. The sbatch request names CPUs (5), memory (9 GB) and minutes
only. harness/q2's runner asserts that it sees no NVIDIA device.

**Cost and limit.** The job limit is 570 minutes: q2's worst-case budget of 110 minutes per
campaign, plus two image checks per campaign, plus 10. Expected use is about 1.1-1.5 VM-h, 25 boots
in all.

**Scheduling** (D85, D86, D94):

- one job, on an empty queue;
- never during a successor E session;
- submitted only once E3's 4B pair has ended;
- only if its limit ends before E4's earliest start, which is 12 h 5 min after E3's later end.

`submit` refuses a non-empty queue. It also refuses any limit that ends after the time passed in
`--must-end-before`, so the operator passes E4's earliest start there.

**Commands:**

- Mac: `python -m harness.s2_locale.ap_delta_step0 render --source-dir <export> --git-sha <sha> --out step0.json`.
  The export is of this commit or a later one that changes no pinned file. Stage it with
  `git archive | ssh host tar -x`, as D86 notes.
- Host: `python3 -m harness.s2_locale.ap_delta_step0 submit step0.json --source-dir <export> --must-end-before <E4 earliest, UTC>`.
- After the job:
  `python3 -m harness.s2_locale.canary_targets_v5 analyze <run root>/<job id> --source-dir <export> --out step0-result.json`.
  This uses the standard library only, on the host.

## Numeric predictions (committed before step 0)

Each image's target is the coordinate-wise median of its 5 boots. Tolerances are in pixels, in x
and in y.

| Image | Writer drag | Writer triple-click | Prediction |
|---|---|---|---|
| E | (680, 293) to (708, 293) | (718, 293) | q2's targets within 2 px (calibration) |
| A | (680, 294) to (708, 294) | (718, 294) | q2's targets within 2 px (calibration) |
| PL | (680, 293) to (708, 293) | (718, 293) | q2's targets within 2 px |
| ER | (751, 293) to (779, 293) | (789, 293) | fixture shifted against E by +71 ± 2 in x and 0 or +1 in y |
| AR | (751, 294) to (779, 294) | (789, 294) | fixture shifted against E by +71 ± 2 in x and 0 or +1 in y |

Chrome on all five images is expected at (172, 151) to (225, 151), with the triple-click at
(242, 151). VS Code on all five is expected at (609, 284) to (639, 284), with the triple-click at
(649, 284). The prediction is the reference within 2 px.

At the v4 targets, `writer:drag_select_word` is predicted to read back "Ykeep word keep" on every
boot of ER and AR. That is the read-back of job 1264, which D94's mechanism predicts.

**A's y sits at the limit.** q2's Writer y (292) is 1.5 px above the glyph-row centre on S (rows
288-299). A draws Writer 1 px lower. So A's predicted y is 294, exactly 2 px from 292. A 1-px
deviation in A's glyph rows would fail the calibration. The rounding convention above was fixed
on the development screenshots; with rounding up, A would be at 3 px. This is disclosed now,
before the measurement.

## Admission tests

The tests below are computed by `canary_targets_v5.decide` from the job's records and the
measured screenshots:

1. **complete**: every (image, app, entry) has 5 boots, each with no infrastructure loss and a
   successful measurement of its before-action screenshot.
2. **(c) stable**: across the 5 boots of each (image, app, entry), the target word's ink edges and
   the line's glyph rows each vary by at most 1 px. Drift above 1 px is reading (c).
3. **calibration on E and on A**: Writer's targets are within 2 px of q2's frozen targets, and
   Chrome's and VS Code's are within 2 px of the reference.
4. **predictions**:
   - PL's Writer targets are within 2 px of q2's;
   - Chrome and VS Code on ER, AR and PL are within 2 px of the reference;
   - on ER and AR, both Writer fixtures are shifted against E's by +71 ± 2 px in x, at both ink
     edges of the target word, and by 0 or +1 px in y, at both glyph-row edges;
   - the v4 read-back holds on ER and AR.
5. **(b) pointer handling**: no trial whose q2 target lies on the measured glyphs fails its
   read-back. "On the glyphs" means the click is inside the target word's ink box and the glyph
   rows, and both drag ends are within 3 px of the word's ink box. Glyphs under the v4 targets
   with no selection is reading (b).

**Reading (a)** holds when tests 1-5 all pass.

## Stop rule

- **(a): proceed.** v5 is drafted as D94 describes. Its targets are fixed by this step and leave
  no choice: q2's targets on every (image, app) except Writer on ER and AR, which get their step-0
  medians (`decide` writes them as `v5_targets`). Then come the one development confirmation (every
  A6 entry 5 of 5 on ER, AR and PL) and the rest of D94's conditions. Proceeding is not a freeze.
- **Any other outcome: an honest exit for S2.** This covers reading (b), reading (c), a failed
  calibration on E or A, a missed prediction, and an incomplete step 0 (a lost boot or an
  unmeasurable screenshot). There is no second measurement and no coordinate search. No threshold,
  region, tolerance or prediction here is edited after any step-0 screenshot or record has been
  read. v4's record stands as D93 and D94 state it.

## Readings of the computed task, disclosed

- **Chrome and VS Code** are compared with the reference, not with q2's frozen numbers (section
  "The Chrome reference").
- **`ap_delta.py` is not edited.** The extension is a new module, and `run_canary` keeps each
  boot's screenshots. There is still one q2 campaign per image.
- **Two conditions D94 does not list** are added to (a): the v4 read-back on ER and AR, and
  completeness. The read-back is the observation that the shift explains: if the drag at the v4
  target passed on ER while the glyphs were 71 px away, Writer would not be placing input where
  it draws, and shifted targets would fail. Completeness follows from "no second measurement".
- **The rounding convention and the thresholds** were set while looking at q2's development
  screenshots of S. A's y prediction sits at the limit (section "Numeric predictions").

## What is pinned

`experiments/manifests/s2v5/step0-rule.json` holds the SHA-256 of each of these files:

- `harness/s2_locale/canary_targets_v5.py`: the rule, the reference, the admission tests and the
  stop rule;
- `tests/test_s2v5_canary_targets.py` and `tests/fixtures/s2v5_step0/*.png`: the regions of q2's
  run-515 and run-501 screenshots;
- `harness/s2_locale/ap_delta_step0.py` and `tests/test_s2v5_step0.py`;
- `infra/slurm/host-single-node/s2v5-step0.sbatch`;
- this record.

v4's files, harness/q2, the images and K0 are unchanged. Their pins stay in v4's registration,
and `tests/test_s2v4_registration.py` still holds.
