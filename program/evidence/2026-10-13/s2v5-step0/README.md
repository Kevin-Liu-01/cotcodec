# S2 v5 step 0: the canary fixture measured on the five cell images (Slurm 1271)

Record: `program/preregistrations/s2-arabic-cua-locale-v5-step0.md`, under decision D94. This is
development under the unfrozen id `s2-arabic-cua-locale-v5`, which has no ledger row. Nothing here
is frozen, and nothing here is a K1 result.

The rule, its predictions and its stop rule were committed in `31854bc6` and pinned by
`experiments/manifests/s2v5/step0-rule.json` (SHA-256 `8d47c55a...`). That happened before any
step-0 job was submitted and before any step-0 screenshot existed. The rendered manifest was
committed in `76698aa8`. The rule ran unchanged: `canary_targets_v5.analyze` verified the 15 pinned
files before it read anything (`step0-result.json`, key `rule_files`). No threshold, region,
tolerance or prediction was edited after the job ran.

## Result: reading (a), so proceed to the v5 draft

The committed `decide` returned, verbatim:

    {"reading": "(a)", "decision": "PROCEED to the v5 draft (D94)", "exit_labels": []}

Every admission test passed:

| Test | Pass | What was observed |
|---|---|---|
| complete | yes | 150 of 150 pointer-composite trials: 5 boots × 6 (app, entry) pairs × 5 images. None had an infrastructure loss, and every before-action screenshot was measured. |
| (c) stable | yes | Boot-to-boot spread is **0 px** everywhere: the target word's ink edges and the glyph rows are identical on all 5 boots of every (image, app, entry). |
| calibration on E | yes | Writer is within 1 px of q2's frozen targets. Chrome and VS Code are 0 px from the reference. |
| calibration on A | yes | Writer is at 2 px from q2's targets (y 294 against 292), the limit disclosed in advance. Chrome and VS Code are 0 px from the reference. |
| prediction, PL Writer | yes | 1 px from q2's targets; PL is pixel-identical to E. |
| prediction, Chrome and VS Code on ER, AR and PL | yes | 0 px from the reference on every image. |
| prediction, shift | yes | Against E's medians, both Writer fixtures sit at dx +71/+71 (left and right ink edge) on ER and AR. dy is 0/0 on ER and +1/+1 on AR. |
| prediction, v4 read-back | yes | `writer:drag_select_word` at the v4 target read back `Ykeep word keep` on 10 of 10 boots (ER 5, AR 5). That is job 1264's read-back. |
| (b) pointer handling | yes | No trial whose q2 target lay on the measured glyphs failed its read-back. |

D94's numeric predictions held exactly:

- ER and AR at (+71 ± 2, 0 or +1): observed (+71, 0) on ER and (+71, +1) on AR.
- q2's targets reproduced within 2 px on E, A and PL: 1, 2 and 1 px.

Every prediction in the step-0 record's table was met to the pixel, including A's y of 294.

### Per image: glyph boxes, targets and shift

The values are the same on all five boots of each image (spread 0 px), so each row stands for each
boot and for the median. `step0-summary.txt` lists every boot separately, with its trial number,
read-back and shift.

Writer (Liberation Mono 10 pt):

| Image | "word" ink x | "this" ink x | Glyph rows | Drag (rule) | Triple-click (rule) | Offset from q2's frozen targets | Shift against E |
|---|---|---|---|---|---|---:|---|
| E | 679-709 | 704-733 | 288-299 | (680,293) to (708,293) | (718,293) | 1 | (0, 0) |
| A | 679-709 | 704-733 | 289-300 | (680,294) to (708,294) | (718,294) | 2 | (0, +1) |
| ER | 750-780 | 775-804 | 288-299 | (751,293) to (779,293) | (789,293) | 71 | (+71, 0) |
| AR | 750-780 | 775-804 | 289-300 | (751,294) to (779,294) | (789,294) | 71 | (+71, +1) |
| PL | 679-709 | 704-733 | 288-299 | (680,293) to (708,293) | (718,293) | 1 | (0, 0) |

q2's frozen Writer targets are a drag from (680,292) to (709,292) and a triple-click at (718,292).

Chrome and VS Code give the same values on all five images, with a shift of (0, 0) against E:

| App | "word" ink x | "this" ink x | Glyph rows | Drag (rule) | Triple-click (rule) | From the reference | From q2's frozen targets (disclosure) |
|---|---|---|---|---|---|---:|---|
| Chrome | 171-226 | 216-269 | 140-163 | (172,151) to (225,151) | (242,151) | 0 | drag 3, click 2 |
| VS Code | 608-640 | 634-665 | 278-291 | (609,284) to (639,284) | (649,284) | 0 | drag 1, click 1 |

Chrome's 3 px is the disclosed reading (record, section "The Chrome reference"). q2's drag end of 228
is the edge of the accessibility cell of `d`, and its ink ends at 226.

### Read-backs at q2's frozen targets

140 of the 150 trials passed. All 10 failures are `writer:drag_select_word` on ER (5 of 5) and on AR
(5 of 5), and each read back `Ykeep word keep`. On those images the v4 drag, from x 680 to 709,
falls wholly in the left margin, because the line's first glyph now starts at about x 710. The
before and after crops show this, for example `crops/ER/boot-00/canary-001-*`.

`writer:triple_click_line` passed 5 of 5 on ER and AR even though it was off target: the click at
x 718 lands on "replace", and the read-back `X` cannot detect an x error. Every Chrome and VS Code
composite passed on every image.

### What (a) hands to v5

`decide` wrote `v5_targets`: q2's frozen targets for every (image, app), except Writer on ER and AR,
which get their step-0 medians:

- ER Writer: drag from (751,293) to (779,293), 500 ms; triple-click at (789,293).
- AR Writer: drag from (751,294) to (779,294), 500 ms; triple-click at (789,294).

Under the stop rule, proceeding is not a freeze. D94's remaining conditions follow:

- v5 changes only A6's targets per image, and everything else stays byte-identical to v4;
- one development confirmation must show every A6 entry at 5 of 5 on ER, AR and PL;
- v5 is S2's last registration.

Step 0 observed the shift directly on the canary itself. It did not yet observe a drag at the
shifted target selecting `word`, because step 0 runs q2's frozen targets. That positive observation
is the confirmation's job.

### Disclosure: AT-SPI extents (no gating role)

q2's measure mode recorded accessibility extents for Writer and Chrome, 100 trials in all. No test
read them.

- Writer gives a drag from (679,268) to (709,268) and a click at (718,268) on every image, ER and AR
  included. On ER and AR the extents stay at unmirrored coordinates, 71 px left of the pixels. On
  every image they sit 25-26 px above the glyph-row centre.
- Chrome gives (172,151) to (228,151) and (243,151) on every image.

## The job

- **CPU only.** `s2v5-step0.sbatch` (SHA-256 `f9829dab...`), with no GRES. The request was
  `--cpus-per-task=5 --mem=9G --time=09:30:00`. Slurm's TRES was `cpu=6,mem=9G,node=1`, with no GPU.
- **Run.** Submitted at 08:37:17Z, started at once, ended 09:19:46Z (run time 42 min 29 s), exit
  `0:0`. The lane log reads `lane_exit=0 labelled_containers_left=0`. The five campaigns ran in
  order E, A, ER, AR, PL, each about 8.5 minutes, and each had driver exit 0.
- **Per campaign** (receipts):
  - `infra_gates_pass` true, 5 of 5 boots;
  - no GPU, no published ports, every container removed, no leaked volume;
  - the image read-only, hashed to its pin before and after, `qcow2_unchanged` true (E `51e47abb...`,
    A `12500989...`, ER `262fe709...`, AR `77cd9a2a...`, PL `5a4102ee...`);
  - cold boots of 16.9-18.0 s and sessions of 92-97 s.
- **Cost.** About 0.7 VM-h, one VM at a time. The estimate was 1.1-1.5.
- **Scheduling** (D85, D87, D94):
  - Successor E session 3's 4B pair ended at 08:36:10Z (VM job 1268) and 08:36:07Z (GPU job 1270),
    per `scontrol`. The 9B pair (1265, 1267) had ended at 07:56:56Z.
  - E3's later end is therefore 08:36:10Z, and E4's earliest start is 20:41:10Z.
  - The queue was empty at submission (`squeue` returned nothing).
  - `submit --must-end-before 2026-10-13T20:41:10Z` accepted the job, whose limit ended at 18:07:17Z.
  - Nothing else ran during the job: all 60 host snapshots (before and after each session, at the
    start and end of each campaign) saw no foreign Slurm job.
- **Source.** A `git archive` of `31854bc67596046c1412de1024b98a70a199baad`, piped directly over
  `ssh` to GNU tar 1.34 on the host, into `~/cotcodec-runs/stage0/s2v5/step0/src/31854bc6.../`.
  Then `.git_sha` was written and the tree made read-only.
  - The host tree holds 8,187 files and 27 symlinks. The SHA-256 of its sorted per-file SHA-256
    list is `95715928...`, equal to a local export of the same commit.
  - There is no AppleDouble file and no `__pycache__`.
  - harness/q2's `source_tree_sha256` is `e0e91310...`, the digest the manifest names. The 15 files
    `step0-rule.json` pins verify there.
- **Manifest.** `experiments/manifests/s2v5/step0-canary-v1.json` was taken from a `git archive` of
  `76698aa85d2efd956e4663d064d3472c994db816`: file SHA-256 `50e038cf...`, canonical digest
  `06974321...`.
  - It passed `submit --dry-run` on the host before submission.
  - The job's `1271/manifest.json` has the same canonical digest.
  - `76698aa8` is `31854bc6` plus this one file. The manifest pins `source.host_dir` to the
    `31854bc6` export and `git_sha` to `31854bc6`, and the runner checks both. So the source tree is
    the export of `31854bc6`, and the manifest comes from `76698aa8`'s archive. The content is the
    same.
- **Analysis.** Run on the host from the export at 09:22-09:23Z:
  `python3 -B -E -s -m harness.s2_locale.canary_targets_v5 analyze .../runs/1271 --source-dir
  <export> --out step0-result.json`. The record's command line includes `--out`, which the CLI
  requires.

## Re-deriving the reading from this directory

The full screenshots stay on the host: 300 PNGs in `.../runs/1271/*/cycles/shots-NN/`, before and
after each composite, about 210 MB. Their SHA-256 values are in each session's
`record-NN.json` (`step0_screenshots`) and in `crops/crops-index.json`.

`crops/` holds, for every screenshot, the region `ROI[app]` that the rule reads, as an RGB crop.
`tools/crop_rois.py` cut them on the host and checked, for all 300, that the rule's luminance of
the crop equals its luminance of the region in the full screenshot. The rule reads nothing outside
that region.

`rederive.py` (standard library, repository root) does three things:

1. checks the crops' digests;
2. rebuilds the observations exactly as `collect` does, from the committed cycle records and the
   rule's `segment` on each before-action crop;
3. runs the rule's `decide` with q2's frozen targets.

It reproduces `step0-result.json` exactly. Its output on the Mac:

    {"crops": 300, "observations": 150, "reading": "(a)", "decision": "PROCEED to the v5 draft (D94)", "exit_labels": [], "problems": []}

## Files

- `step0-result.json`: `canary_targets_v5 analyze`'s output (SHA-256 `18d8b910...`). It holds the
  reading, every test, `per_image`, `v5_targets`, the observations and the disclosures.
- `step0-summary.txt` and `step0-summary.json`: descriptive per-boot tables from `tools/summarize.py`
  (reads `step0-result.json` only and decides nothing).
- `crops/`: the 300 region crops, with `crops-index.json`. `tools/crop_rois.py` made them.
  `rederive.py` is the check above.
- `1271/`: the job's records.
  - Job level: `preflight.txt`, `manifest.json` and `step0-receipt.json`.
  - Per campaign: `apdelta.json`, `manifest.json`, `preflight.txt`, `receipt.json` and
    `session_plan.json`.
  - Per session, under `cycles/`: `config-NN.json`, `record-NN.json`, `cycle-NN.trials.jsonl` and
    `vm-NN.log`.
  - Left on the host: `cycle-NN.json`, which is identical to `record-NN.json`'s `runner_result`,
    and the screenshots.
- `slurm-1271.out`: the job's Slurm output.
- `submit.json`: the submit result, including the sbatch argv. `ops.log`: the operator's log on the
  host. `analyze.stdout`, `crop.stdout`: the two commands' outputs.
