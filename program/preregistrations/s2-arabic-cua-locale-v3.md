# S2 v3: Arabic interface text versus mirrored layout on the certified OSWorld stack, Phase 0 executable CPU pilot and a Phase 1 census of OSWorld's LibreOffice tasks (s2-arabic-cua-locale-v3)

Status: DRAFT. Not frozen, not admitted, no ledger row. Written on 2026-10-11 by the single owner
of the S2 v3 gauntlet under program decision D71 (ii), on branch `gauntlet/s2v3-locale`, as a new
experiment id (gauntlet rule 3). `s2-arabic-cua-locale-v1.md` (Relay, wave 1, score 49) and
`s2-arabic-cua-locale-v2.md` (OSWorld, K = 26-43, score 59, honest exit under D68) are left as they
were. The proposal that argues and attacks this design is
`program/proposals/2026-10-11-s2v3-arabic-cua-locale-pilot.md`; its evidence bundle is
`program/proposals/evidence/2026-10-11-s2v3-arabic-cua-locale-pilot/`. Phase 0 is CPU-only. Phase 1's
registered caps sum to 6.10 GPU-h (6.87 at the p95 slot price), below D20's 8 GPU-h line; whatever the
gauntlet scores, Phase 1's admission is Kevin's ruling under D24 and D70. Every number labelled
"simulated" comes from `compute/power/power-v3.py` (seeds 42, 43, 44) on S1a's measured records;
every number labelled "pilot" comes from the CPU Slurm jobs 1097-1099 recorded under
`compute/pilot/`.

## What changed from v2, and why

| v2 (s2-arabic-cua-locale-v2) | v3 (this file) | Why |
|---|---|---|
| 26-43 tasks selected on S1a's English success; SMALL needed a rare-break bound that is unreachable at K <= 31 (U = 1 - 0.05^(1/K) times the en mean) | A census of every OSWorld LibreOffice single-application task that passes the pool rules (106: 62 confirm, 17 dev, 27 reserve), with no selection on outcomes; the primary decision is about these tasks (census frame), with the population claim reported beside it | Wave 2's largest defect: P3 and P4 could not be falsified at the admitted K. A census has no unseen tasks, so complete breaks in a few tasks enter the estimate instead of a bound. Simulated census SMALL under the null: 0.97 (homogeneous) and 0.92 (task-specific mixed-sign perturbation) at K = 106, n = 4 |
| Absolute margin +/-5 pp only | Dual margin: +/-5 pp on the census mean and a ratio of solve rates inside (0.85, 1/0.85) | An unscreened census includes about half never-solved tasks (33 of 62 S1a tasks are 0 of 8); the ratio is unchanged by tasks nobody solves, so the census cannot reach SMALL by dilution (the kill-shot scout's objection) |
| Selection on English success (identification refuter: a direction-free reshuffle gives PRESENT_HARM 0.13-0.36) | No selection; all cells measured fresh; a reshuffle is mean-preserving on the census | Removes the selection mechanism instead of adding a placebo |
| n = 12-16 episodes per task-cell | n = 4 (2 per harness) | Distinct tasks bind, not reruns (design study section 7; Westfall, Kenny and Judd 2014) |
| Every catalog string wrapped in FSI ... PDI in all four cells | Wrapping only where the oracle finds a coupling leak on the dev tasks, never for strings that become document content | Pilot job 1098: wrapping STR_TABLE_DEF puts U+2068/U+2069 into sheet names and the saved .xlsx in the English cell |
| Calc's default sheet name not held fixed (12 checkers read "Sheet2") | `Office.Calc/Defaults/Sheet/SheetPrefix` pinned to "Sheet", finalized, in all four cells | Pilot job 1098: a pseudo-Arabic interface names the first sheet "ورقة1"; the pin gives "Sheet1" in both languages and leaves the English cell unchanged |
| Layout: `SAL_RTL_ENABLED` for en-RTL, finalized `UIMirroring` = false for ar-LTR | Both directions by the finalized `UIMirroring` key in a system-level layer (`/etc/libreoffice/registry`) | Pilot job 1098: `UIMirroring` = true gives pixel-identical screens to `SAL_RTL_ENABLED` = 1; `UIMirroring` = false gives pixel-identical screens to stock English |
| P6 screen-half moderator (about 1 for every task under whole-window mirroring) | Displacement moderator from S1a's own English click coordinates and the oracle's boxes | The screen-half coding was degenerate (identification refuter, reviewer 2) |
| P7 descriptive; the rare-break bound multiplied by the en mean, so a degraded instrument eased SMALL | K5: a confidently degraded English cell suppresses every SMALL claim | Reviewer 1 |
| Step-0 failures not re-queued; K_min = 26 = the modal K | Infrastructure losses and step-0 failures re-queued up to twice; K_min = 62, about 58% of the pool | Reviewer 1 |
| O3 on AT-SPI boxes | O3 on ink-located boxes; AT-SPI extents only for the LTR reference | Pilot job 1100: 53% of matched accessibles report unmirrored extents in the mirrored cell |
| D53's delta suite: C1-C4, A1 (N = 1), A5 | Adds A2 (both harness adapters), A6 (the Writer typing canary) and one V = 20 rung with the four cells interleaved | Kill-shot scout: v2's suite left out the layers Phase 1 uses |

## Question

On Q2's certified OSWorld stack, with task instructions, documents, checkers, the system shell,
number formats, Calc's default sheet prefix and the keyboard held fixed, and LibreOffice's
interface text language (English, Arabic) and layout direction (left-to-right, mirrored) switched
separately in a 2x2, how large are (D) the main effect of mirroring the application layout and (T)
the main effect of Arabic interface text on the screenshot success of Qwen3.5-9B over OSWorld's
LibreOffice tasks?

Claim scope: `portability-protocol`, a measurement on one frozen model, two certified scaffolds
and LibreOffice Calc, Impress and Writer (Ubuntu 1:7.3.7-0ubuntu0.22.04.4, gtk3). Primary frame: the
census of admitted tasks ("on OSWorld's LibreOffice tasks, on this stack"). Secondary frame: tasks
like these ("population"). Application-level localization over English documents and an English
system shell only; not full operating-system localization, instruction language, reasoning
language, other models or training. macOSWorld's whole-OS drop is not decomposed.

## Identity

- Experiment id: `s2-arabic-cua-locale-v3`. Code of record: the freeze commit on
  `gauntlet/s2v3-locale` or its successor.
- Model: Qwen3.5-9B, revision `c202236235762e1c871ad0ccb60c8ee5ba337b9a` (receipt `0a9e052d`).
  Greedy decoding, thinking on, 2,048 output tokens per step, 15 steps, screenshot only, the matched
  60 s and 20 s settles (S1a's configuration).
- Harnesses: H-OSW-fixed (OSWorld `bfd62bdc` qwen35vl with its own-spec fixes) and H-GA
  (gym-anything `aae6f7607` qwen35vl), unchanged from `q2-stage1-rescoped-v1`; their prompts do not
  mention the interface language.
- Engine: vLLM v0.31.0 (commit `db9527a4`) on
  `docker.io/vllm/vllm-openai@sha256:b18abb2df97b8f798e81862bd93f872ea18613372e2c3adc0cc2ac21e66ac12f`
  with the cu129 overlay rebuilt from the freeze commit.
- VM lane: S1a's L0-fixed lane, V = 20 concurrent VMs, offline VMs, OSWorld task configs and checkers
  at `b138d348256078fa634fc3b73567a7337c793e6b`, the pinned file cache `file_cache_1e112283`.
- Image: a derived image of the certified OSWorld image (HF `xlangai/ubuntu_osworld` `a5d9c3ea`,
  `Ubuntu.qcow2` sha256 `6bf667a8...`), built in Phase 0 (P0.2); its digest and package list are
  recorded before the Phase 1 freeze.

## Tasks (P0.1, frozen here)

`compute/pool/pool-v3.py` applied to OSWorld `test_all.json` at `b138d348` (sha256 `9ebc5187...`),
the checker-mutation splits (`splits.json`, seed 42), S1a's records and S1a's plan; output
`compute/pool/pool-v3.json` lists every task with its split, checker, setup steps, window titles and
S1a record.

| Step | Tasks | Detail |
|---|---:|---|
| LibreOffice single-application tasks in `test_all.json` | 117 | Calc 47, Impress 47, Writer 23 |
| E1 infeasible | -2 | `2bd59342`, `bb8ccc78` |
| E2 outside the 205-task file-checker scope | -1 | `ef9d12bd` (`check_left_panel` reads the accessibility tree; a layout-dependent checker) |
| E3 setup clicks or moves the pointer at screen coordinates | -3 | `550ce7e7`, `a669ef01`, `21760ecb` |
| E4 the checker fails its own raw gold | -5 | `8472fece` (reserve controls); `0a0faba3`, `15aece23`, `ac1b39ff`, `ed43c15f` (S1a's K1 exclusions) |
| E5 setup needs the network | 0 | none |
| **Admitted pool** | **106** | confirm 62, dev 17, reserve 27; Calc 46, Impress 40, Writer 20 |
| C1 conditional: checker reads `registrymodifications.xcu` | 3 | `0f84bef9`, `2cd43775`, `f178a4a9` (enter only if P0.10 passes) |
| F1 checker reads a sheet the agent creates by Calc's default name (`RNSheet2`) | 12 | confirm 7, dev 1, reserve 4; held fixed by the SheetPrefix pin (P0.5) and checked by P0.9 |

S1a's Qwen3.5-9B English records exist for the 62 confirm tasks: 29 solved at least once in 8
episodes, 33 never; mean success 0.288. The 44 dev and reserve tasks have no 9B record. 99 tasks end
with a strict `activate_window` on `<file> - LibreOffice <Module>` before a Ctrl+S postconfig.

Split rules. The 17 dev tasks are Phase 0's development set: switch development, the oracle's A/A
tolerances, positive controls and every remedy are decided on them. Confirm and reserve tasks meet
Phase 0 only through frozen checks; a failure on them is either an exclusion of that task or a
remedy applied to all four cells followed by a full rerun of the oracle (thresholds never change).
All admitted tasks, dev included, form the Phase 1 census: nothing about the agent is tuned on any
task, and no task is selected on any outcome. Multi-application tasks are out (a second
application has its own interface switch).

## Phase 0 (CPU only; host CPU lane jobs; no GPU)

- **P0.1 Task pool.** Above; frozen.
- **P0.2 Derived image.** From the certified image, offline: `libreoffice-l10n-ar`
  `1:7.3.7-0ubuntu0.22.04.4` (all; 663,804 B; Launchpad librarian; its dependencies
  `libreoffice-common`, `locales` and `ucf` are installed), `language-pack-ar-base` `22.04+20230801`
  (151,600 B) and `language-pack-gnome-ar-base` `22.04+20230801` (930,704 B, for GTK's own dialog
  strings). No font is added: `fonts-kacst`, `fonts-kacst-one` and DejaVu already cover Arabic (pilot:
  20 Arabic-capable families; `fc-match :lang=ar` gives DejaVu Sans). Route: the three packages are
  extracted with `dpkg-deb -x` and written into an extracted raw root partition with `debugfs -w`
  inside the existing `cotcodec-q2-vmprobe` image (no host root, no maintainer scripts), then the
  partition is written back to a new qcow2 overlay whose digest is recorded. The package files and
  their SHA-256 are recorded. Two preconditions block it today: (a) the three downloads are an
  outward network action on the login host (the lane runs with `--network=none`), which waits on
  Kevin's go-ahead; (b) the image surgery script, and a lane version that accepts the derived image's
  digest (`harness/q2_stage1/lane.py` pins `QCOW2_SHA256`) and the 27 reserve tasks (line 253 allows
  only pool and dev tasks), are new code that needs review.
- **P0.3 Switches (system layer only).** The four cells differ only in one selector file in
  `/etc/libreoffice/registry/` (the system configuration layer of this build, first in its
  `CONFIGURATION_LAYERS`), checked byte for byte:
  - text: `org.openoffice.Setup/L10N/ooLocale` = `en-US` or `ar`, finalized (pilot: a finalized
    system-layer value overrides the user profile's `ooLocale` = `en-US`);
  - layout: `org.openoffice.Office.Common/I18N/CTL/UIMirroring` = false (LTR) or true (RTL), finalized,
    in every cell (pilot: true is pixel-identical to `SAL_RTL_ENABLED` = 1 on blank Calc, Impress and
    Writer; false is pixel-identical to stock English); `SAL_RTL_ENABLED` is never set (it overrides
    the key, pilot job 1098 L6).
  - GTK's own strings follow the process `LANGUAGE` (`ar` in the Arabic cells), and GTK's widget
    direction follows LibreOffice's setting (`vcl/unx/gtk3/gtkdata.cxx:61`).
  Nothing is written to the user profile's `registrymodifications.xcu`, which three checkers read.
- **P0.4 Direction coupling and isolation.** Coupling (a string's internal order changing with the
  layout) is measured, not assumed: O2 runs first with the shipped catalogs. Where O2 finds a
  coupling leak on the dev tasks or the sweep, the remedy wraps that string source in FSI ... PDI
  (U+2068 ... U+2069) in all four cells (Arabic `.mo` catalogs rewritten; English through generated
  `en_US` `.mo` catalogs, which this build loads: pilot K1 shows a tagged `en_US` `sc.mo` renaming the
  first sheet "⟦Sheet⟧1"; registry labels through generated system-layer label overrides). Strings that
  P0.8 finds in saved outputs are never wrapped (pilot K2: a wrapped STR_TABLE_DEF puts U+2068/U+2069
  into the saved sheet names).
- **P0.5 Held fixed in every cell.** Task instructions, documents and checker inputs (English, LTR);
  the system shell (English, LTR); `ooSetupSystemLocale` = `en-US` (number and date formats) and the
  document default language; `SheetPrefix` = "Sheet" (finalized; pilot K3, K5, K6); `CTLFont` = false
  (finalized; the l10n package's `ctl_ar.xcd` would otherwise turn complex-text-layout support on in
  every cell); Calc's English function names; autocorrect and spelling languages; the X keyboard map
  `us` and no input method; screen resolution 1920x1080; the agent, decoding, step cap and settles.
  UI digit shaping in the Arabic cells (pilot L4: the zoom field reads "٪١٠٠") is part of the text
  treatment, not held fixed.
- **P0.6 Delta certification of the action path.** The frozen acceptance suite of
  `q2-action-path-v2` (executor and catalog unchanged) on the derived image with each cell selector:
  C1-C4, A1 at N = 1, A2 (both harness adapters), A5, A6 (the Writer typing canary, read back) and the
  keyboard-map check, pass lines as D53's; then one V = 20 rung with the four cells interleaved (5 VMs
  each). A3 (stress set) runs once, in the ar-RTL cell. This needs a registered deviation of
  `q2-action-path-v2` or its own short registration, written before Phase 0 runs.
- **P0.7 Factorial render oracle.** Captured in the measurement lane on the derived image (never on
  the Mac), at every admitted task's post-setup state (setup replayed exactly as the task config
  states) and over a sweep per application (each top-level menu on the first dev task, and the
  dialogs named by a keyword map from the instructions, frozen before Phase 0 runs). Inputs: the
  screenshot and the accessibility tree (role, name, box), with U+2066-U+2069 stripped before name
  matching. Checks:
  - O1 structure: the (path, role) list is identical in the four cells;
  - O2 text runs: each text element's ink is the same image in the two layout levels of the same
    text level, at tolerance max(0.02, 2 x the worst A/A mismatch on the dev tasks);
  - O3 mirror fidelity: each widget in the RTL cell sits at the reflection of its LTR position inside
    the window (2 px), with exceptions only from a mirror specification frozen on the dev tasks. Boxes
    are located by ink: each widget's LTR ink (from its LTR box, cross-checked against the LTR
    screenshot) is template-matched in the RTL screenshot at the expected reflected position. AT-SPI
    extents are not used for the RTL cells: pilot job 1100 found that a median 53% of matched
    accessibles (VCL toolbar buttons and menu objects) keep their unmirrored extents while the
    screen is mirrored, and centred Impress text has wrong extents even in LTR (tdf#150231);
  - O4 order under text swap: sibling order is unchanged between en and ar-LTR and between en-RTL and
    ar-RTL;
  - O5 content identity: the document region is the same image in the four cells (allowing the
    horizontal offset the mirrored chrome imposes; a mirrored document fails);
  - O6 invisibility: the en cell's screenshots equal the stock image's at the same states, after
    clock and caret masks;
  - O7 window title: the LibreOffice window title is byte-identical in the four cells (99 tasks'
    postconfig activates it strictly);
  - O8 RTL-defect inventory: per task and cell, controls that are clipped, missing, misplaced or
    whose meaning flips, against the mirror specification (pilot L2: the status bar's text fields are
    clipped to one character in the mirrored layout); reported as part of the treatment, used as a
    moderator, never a reason to drop a task silently.
  Positive controls, required before the verdict counts: a planted coupled string, a half-mirrored
  planted widget, and a planted document change must fail O2, O3 and O5 respectively in each
  application.
- **P0.8 Source coverage (tagged pseudo-catalog).** A fifth, Phase-0-only cell replaces every
  string source (all LibreOffice `.mo` domains, registry labels, GTK's catalog) by a tagged
  pseudo-translation. (a) Any visible untagged string at a post-setup state or in the sweep lies
  outside the catalogs and is listed. (b) Any tag found in a saved output (after each task's own
  postconfig save and after the P0.9 probes) is a content leak: that string is excluded from P0.4's
  wrap set and pinned where a configuration key exists, and a task whose checker reads it is
  excluded.
- **P0.9 Functional A/A across cells.** Keyboard-driven probes per application (open a candidate
  document, type a value and a formula with an English function name, insert a sheet with the
  default name, apply a format, save keeping the format, export where a task exports) run in all
  four cells; saved files must be byte-identical after removing timestamps, or checker-equal under
  every candidate checker. Each task's own postconfig (strict activate_window, Ctrl+S) must save in
  all four cells.
- **P0.10 Config invariance (C1 tasks).** After a fixed probe session the keys that differ between
  cells must not include a key the task's checker reads, and the checker's verdict on the
  post-setup state must agree across cells; otherwise the task is dropped.
- **P0.11 Setup validation.** Every admitted task's setup runs offline in each cell (the 27 reserve
  tasks have never been setup-checked on the lane).
- **P0.12 Moderators, frozen before any GPU job.** (a) Positional exposure: for each confirm task
  with a successful S1a English episode, the share of that episode's actions that are clicks and the
  mean mirrored displacement |W - 2x| / W of its click targets (S1a's records, independent of Phase
  1); (b) lexical overlap: distinct English interface labels visible at the post-setup state whose
  lowercased tokens appear in the instruction; (c) O8's defect count.
- **P0.13 Arabic chrome share.** Per task and state, the share of visible interface strings rendered
  in Arabic script in the ar cells (untranslated strings stay English in both layout levels).

Phase 0 admission (K0). A task enters Phase 1 if, in all four cells, its setup runs offline (P0.11),
O1-O7 pass at its post-setup state with the positive controls passing, P0.8 finds no content leak its
checker reads, P0.9 passes for its application and (C1 tasks) P0.10 passes. Phase 1 runs only if the
admitted tasks number at least K_min = 62 and P0.6 passes (K1); otherwise infrastructure exit with the
image, the oracle record and the leak and defect inventories published.

### The executable part of Phase 0 run during this gauntlet (pilot jobs 1097-1099)

CPU-only Slurm jobs, no GRES, one at a time on an empty queue, through
`infra/slurm/host-single-node/s2v3-pilot-cpu.sbatch` (a path-only copy of the D12 CPU lane:
`--network=none`, read-only root, no capabilities, the host user's uid) in the LO-VM container
`cotcodec-q2-lo-vm@sha256:f5b4c40e...` (the certified VM's own LibreOffice 7.3.7.2 userland plus Xvfb
and openbox). Not the VM lane and not the derived image: no Arabic catalog exists on the certified
image, so the Arabic cells are "pseudo-Arabic" (UI language `ar` with a minimal language pack and a
one-string catalog). What ran and what it showed is in the proposal's pilot section and in
`compute/pilot/`; the derived image, P0.6, the VM-lane oracle and P0.8-P0.11 did not run.

## What the D53 certification covers for the localized cells

As v2's table (unchanged facts): the runtime, the harness adapters, the lane and V <= 32 carry over;
the derived image ("another image"), the keyboard map under an Arabic locale, the guest server under
localized applications and the rendered treatment are not covered. v3 adds A2, A6 and a V = 20 rung
to P0.6, so the harness layer and the concurrency Phase 1 uses are re-certified on the derived image.

## Phase 1 (only after K0 and K1 pass and an admission ruling)

- Tasks: the admitted census, K of them (62 <= K <= 106). Cells: en, ar-LTR, en-RTL, ar-RTL.
- Episodes: n = 4 per (task, cell): 2 per harness. Total 16 K (1,696 at K = 106).
- Order: one serving session (one GPU job and its CPU VM job). Task blocks in a seeded order (PCG64
  seed 42); within a block the 16 episodes in a seeded interleave; cells assigned to VM slots at
  random within each batch of 20, slot and batch recorded.
- Step-0 check: each episode's first screenshot, after the clock and caret masks, against the Phase 0
  reference for its (task, cell) recorded in the same lane on the same image; the tolerance from
  Phase 0's A/A. A mismatch makes the episode invalid.
- Keyboard check: `setxkbmap -query` reports `us` and no input method runs at every episode start; a
  failure is an infrastructure loss.
- Re-queue: an infrastructure loss or a step-0 failure is re-queued at the end of its task block, at
  most twice per episode. A task enters the analysis if each of its four cells has at least 2 valid
  episodes; cell means use all valid episodes (harnesses weighted equally where both exist).
- Cap (D22 counting): one job, ceil(3 + L/60 + (N x s / V + drain) x 1.2 x 1.05 / 60) minutes with L =
  113.2 s, drain = 104.6 s, V = 20, N = 16 K and s = 197.73 s (the mean slot of S1a's 9B episodes that
  ran to the 15-step cap), plus 6 minutes for the overlay build and retry.

  | K | episodes | physical GPU-h (high slot) | job cap (min) | cap incl. overlay (GPU-h) | cap at the p95 slot 223.6 s (GPU-h) |
  |---:|---:|---:|---:|---:|---:|
  | 62 | 992 | 2.79 | 214 | 3.67 | 4.10 |
  | 89 | 1,424 | 3.97 | 303 | 5.15 | 5.80 |
  | 106 | 1,696 | 4.72 | 360 | 6.10 | 6.87 |

  The cap stays below 8 GPU-h while the mean slot stays below about 263 s at K = 106 (33% above the
  high slot). n = 6 at K = 106 would cap at 9.03 GPU-h, so n = 4 is the largest balanced n that fits.
  Beyond it K8 stops the job at the last complete task block.

## Estimands

Per task t, cell means y_en, y_arL, y_enR, y_arR (harnesses equally weighted).

- **Primary, D (layout main effect):** D = mean_t D_t, D_t = ((y_arR - y_arL) + (y_enR - y_en)) / 2.
  Relative companion: R_D = S_RTL / S_LTR with S_RTL = mean_t (y_enR + y_arR) / 2 and
  S_LTR = mean_t (y_en + y_arL) / 2.
- **Secondary, T (Arabic interface text main effect):** T = mean_t ((y_arL - y_en) + (y_arR - y_enR)) / 2,
  with R_T likewise. T changes language, script, UI digits and the word overlap between English
  instructions and interface labels together; it is not a "glyph" effect.
- **Secondary:** the total Delta = T + D; the interaction I; the dossier's conditional contrasts
  M_ar = ar-RTL - ar-LTR and G = ar-LTR - en; D and T by harness and application (descriptive);
  fractional checker scores (sensitivity); the same estimates without the 7 S1a-flagged tasks
  (sensitivity); process metrics (steps, cap share, invalid actions) by cell.
- **Moderators (task-level regressions, CR2 standard errors):** D_t on positional exposure (P0.12a)
  and on O8's defect count; T_t on lexical overlap (P0.12b). A mechanism is named only if the 95% CR2
  interval excludes 0 in the predicted direction (negative); otherwise "unresolved".
- **Reference:** the en cell against S1a's 9B English success on the 62 overlapping tasks (K5).

## Decision rules (primary D; the same labels are reported for T)

Census frame (primary; "these tasks"). Var(D) = (1/K^2) sum_t v_t, where v_t sums, over the four
cells, (1/4) x the variance of the cell mean, estimated without bias per (task, cell, harness) from
its m valid episodes as m/(m-1) p(1-p)/m. log R_D has delta-method variance Var(S_RTL)/S_RTL^2 +
Var(S_LTR)/S_LTR^2 from the same within-task variances (the two layout levels use disjoint
episodes).

- **PRESENT:** the 95% normal interval of D excludes 0; labelled PRESENT_HARM or PRESENT_BENEFIT. The
  stratified randomization test of the sharp null (no layout effect on any episode distribution) is
  reported beside it; disagreement at 0.05 gives PRESENT_FRAGILE.
- **SMALL:** the 90% interval of D lies inside (-5, +5) pp and the 90% interval of log R_D lies inside
  (log 0.85, -log 0.85). PRESENT and SMALL can hold together (PRESENT_AND_SMALL).
- **INCONCLUSIVE:** neither.
- **SMALL is suppressed** (reported as SMALL_DEGRADED_INSTRUMENT) if K5 fires.

Population frame (secondary, reported, not decision-bearing; "tasks like these"): the t interval over
task-level D_t (df K - 1) and a task-level delta-method interval for log R_D; PRESENT_POP and
SMALL_POP as above, and SMALL_POP also needs the concentration guard: B = tasks whose one-sided Fisher
exact test (RTL against LTR successes, 2n against 2n episodes) gives p <= 0.01, U = the
Clopper-Pearson 95% upper bound on B / K, U x S_LTR < 5 pp and U < 0.15. With no break the success-run
bound U = 1 - 0.05^(1/K) is 0.028 at K = 106 and 0.047 at K = 62.

Margins. The absolute margin is the dossier's 5 pp (macOSWorld's whole-OS English-to-Arabic drop is
5.6 pp on a benchmark-wide mean of 19.3%, likewise an unscreened mean). The relative margin, 15% of
the solve rate, is about half of macOSWorld's 28.8% relative drop, which mixes text, layout and (in
the matched condition) instruction language; macOSWorld reports no interval, so neither margin is an
M1 in the non-inferiority sense, and both are fixed here before data.

## Kill criteria

| Id | Trigger | Consequence |
|---|---|---|
| K0 | Fewer than 62 tasks pass Phase 0 admission | Infrastructure exit: image, oracle record, leak and defect inventories published; no Phase 1 |
| K1 | P0.6 fails | No Phase 1 on this image; a repair is a new image and a new P0.6 run |
| K2 | More than 5% of a cell's episodes are infrastructure losses after re-queue | INCOMPLETE |
| K3 | More than 2% of a cell's episodes fail the step-0 check after re-queue | INCOMPLETE |
| K4 | The en cell's census mean success lies outside [0.15, 0.85] | UNINFORMATIVE: D and T claims dropped (expected about 0.29 from S1a) |
| K5 | On the 62 S1a-overlap tasks, the 90% interval of (en cell - S1a 9B English success) lies entirely below -5 pp | INSTRUMENT_DEGRADED: no SMALL claim for D or T; PRESENT still reported |
| K6 | D and T both SMALL (census) and neither PRESENT | Publish the robustness null for application-level localization of OSWorld's LibreOffice tasks at this scale; drop the locale arm from S3's plan |
| K7 | Neither D nor T PRESENT | No reasoning-language arm |
| K8 | The Phase 1 cap is reached | Stop at the last complete task block; analyse if at least 62 tasks are complete, else INCOMPLETE |

## Predictions and falsifiers

| | Prediction | Falsifier (reachable?) |
|---|---|---|
| P1 | Phase 0 admits at least 62 tasks | K0 (reachable: with the real Arabic catalogs, window titles may change through a translated module name, and the pilot already found a clipped mirrored status bar and unmirrored accessibility extents) |
| P2 | P0.6 passes | K1 |
| P3 | D < 0 (mirroring hurts) | D is SMALL (census) or PRESENT_BENEFIT. Simulated P(SMALL) under the null at K = 106, n = 4: 0.97 (homogeneous), 0.92 (task-specific mixed-sign perturbation), 0.82 and 0.62 (reshuffles of 10% and 30% of tasks) |
| P4 | T < 0 | T is SMALL (census) or PRESENT_BENEFIT (same operating characteristics) |
| P5 | The D_t slope on positional exposure is negative | its 95% CR2 interval lies above 0 (named only if below) |
| P6 | The T_t slope on lexical overlap is negative | its 95% CR2 interval lies above 0 (named only if below) |
| P7 | The layout switch is one treatment whether set by the key or by the language | Phase 0: en-RTL (key) and ar-RTL (language) screens differ outside the catalog strings, the status bar's locale fields and the caret (pilot L2 against L4: 0.05-0.09% of pixels differ, all in those regions) |

## Reported regardless of outcome

Phase 0: every gate item per task and cell; the leak inventory (O2), the coupling remedies and the
content-leak list (P0.8); the RTL-defect inventory (O8); A/A tolerances; positive controls; the
Arabic chrome share; functional A/A and config-invariance results; the mirror specification;
moderator codings; the delta certification record; CPU time. Phase 1: per-task successes per cell
and harness; D, T, I, Delta, M_ar, G with census and population intervals; R_D and R_T; the
sharp-null test; the concentration guard; process metrics; moderator slopes; the en-cell reference
against S1a; infrastructure losses and step-0 failures per cell; cost per cell; slot and batch per
episode.

## Statistics, sample sizes and simulation

- **Propensity model** (`power-v3.json` `prior`). Cell level, 124 (task, harness) cells of the 62
  confirm tasks with 4 trials each: a = 0.099, b = 0.246 (beta-binomial, maximum marginal
  likelihood); task level, 62 tasks with 8 trials: a = 0.137, b = 0.342 (mean 0.287). Each observed cell draws from
  its posterior; each of the 44 tasks without records draws one probability from the task-level fit
  (harness heterogeneity ignored for them; S1a put task-by-harness variance at 3-4%). One session with
  a common logit shift of SD 0.3. 2,000 replicates per seed over seeds 42, 43, 44.
- **Effect structures** on the layout factor (text null): uniform logit shift; proportional reduction
  on every task; on a random quarter of tasks; complete breaks on a random share of tasks;
  task-specific logit perturbations N(theta, 1) (mixed sign); reshuffles of 10% and 30% of tasks
  (redrawn from the propensity distribution). Targets are relative effects on the census
  (RD = sum (p_RTL - p_LTR) / sum p_LTR), calibrated on a fixed bank.
- **Operating characteristics of the registered rules** (simulated, `power-v3.json`, rendered by
  `tables-v3.py`):

Census of all 106 pool tasks, n = 4 (cap 6.10 GPU-h). Nulls:

| Null structure | census true D (pp) | PRESENT_HARM | PRESENT_BENEFIT | SMALL | INCONCLUSIVE | 95% coverage of the census D | SMALL_POP (population, with guard) | v2's rule: SMALL unqualified |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| homogeneous (no effect) | 0.00 | 0.029 | 0.025 | 0.971 | 0.004 | 0.946 | 0.963 | 0.958 |
| task-specific logit perturbation N(0, 1) | -0.02 | 0.058 | 0.062 | 0.924 | 0.009 | 0.947 | 0.843 | 0.802 |
| reshuffle of 10% of tasks | 0.00 | 0.121 | 0.125 | 0.817 | 0.007 | 0.944 | 0.497 | 0.551 |
| reshuffle of 30% of tasks | 0.00 | 0.218 | 0.221 | 0.624 | 0.011 | 0.948 | 0.037 | 0.051 |

Alternatives (relative layout effect RD on the census; the absolute census D is about 0.29 x RD):

| Structure | RD | census true D (pp) | PRESENT_HARM | SMALL | SMALL when the census truth is beyond a margin | 95% coverage | SMALL_POP | v2's rule: SMALL unqualified |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| uniform logit shift | -0.10 | -2.87 | 0.707 | 0.386 | n/a | 0.947 | 0.364 | 0.487 |
| uniform logit shift | -0.15 | -4.30 | 0.958 | 0.068 | 0.027 | 0.947 | 0.060 | 0.136 |
| uniform logit shift | -0.20 | -5.73 | 0.999 | 0.003 | 0.003 | 0.949 | 0.002 | 0.017 |
| uniform logit shift | -0.30 | -8.60 | 1.000 | 0.000 | 0.000 | 0.947 | 0.000 | 0.000 |
| proportional, every task | -0.10 | -2.87 | 0.651 | 0.330 | n/a | 0.949 | 0.330 | 0.414 |
| proportional, every task | -0.15 | -4.31 | 0.920 | 0.051 | 0.051 | 0.948 | 0.052 | 0.107 |
| proportional, every task | -0.20 | -5.74 | 0.990 | 0.003 | 0.003 | 0.947 | 0.002 | 0.015 |
| proportional, every task | -0.30 | -8.61 | 1.000 | 0.000 | 0.000 | 0.942 | 0.000 | 0.000 |
| proportional, a quarter of tasks | -0.10 | -2.87 | 0.636 | 0.382 | 0.014 | 0.951 | 0.292 | 0.354 |
| proportional, a quarter of tasks | -0.15 | -4.30 | 0.877 | 0.132 | 0.014 | 0.948 | 0.070 | 0.126 |
| proportional, a quarter of tasks | -0.20 | -5.74 | 0.962 | 0.042 | 0.007 | 0.948 | 0.014 | 0.034 |
| complete breaks | -0.10 | -2.86 | 0.633 | 0.434 | 0.012 | 0.951 | 0.266 | 0.351 |
| complete breaks | -0.15 | -4.29 | 0.849 | 0.188 | 0.009 | 0.951 | 0.088 | 0.138 |
| complete breaks | -0.20 | -5.73 | 0.952 | 0.062 | 0.005 | 0.954 | 0.022 | 0.041 |
| complete breaks | -0.30 | -8.59 | 0.998 | 0.003 | 0.001 | 0.947 | 0.001 | 0.002 |
| mixed-sign perturbation, mean shifted | -0.15 | -4.31 | 0.924 | 0.109 | 0.017 | 0.945 | 0.061 | 0.116 |
| mixed-sign perturbation, mean shifted | -0.30 | -8.61 | 1.000 | 0.000 | 0.000 | 0.942 | 0.000 | 0.000 |

By task count and episodes (census frame; 'at -15%' is the range over the five alternative structures):

| Task set | K | n | cap GPU-h | census SE of D (pp, null) | SMALL, homogeneous null | SMALL, perturbation null | SMALL, 10% reshuffle | PRESENT_HARM at RD -15% | PRESENT_HARM at RD -20% | max SMALL when beyond a margin | SMALL_POP, homogeneous null |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| census_all_106 | 106 | 4 | 6.10 | 1.16 | 0.971 | 0.924 | 0.817 | 0.849-0.958 | 0.952-0.999 | 0.051 | 0.963 |
| census_all_106 | 106 | 6 | 9.03 | 0.95 | 0.995 | 0.976 | 0.895 | 0.911-0.995 | 0.976-1.000 | 0.051 | 0.993 |
| census_all_106 | 106 | 8 | 11.97 | 0.82 | 1.000 | 0.993 | 0.925 | 0.944-0.999 | 0.986-1.000 | 0.072 | 1.000 |
| without_dev_89 | 89 | 4 | 5.15 | 1.26 | 0.946 | 0.895 | 0.761 | 0.819-0.928 | 0.936-0.995 | 0.056 | 0.932 |
| confirm_only_62 | 62 | 4 | 3.67 | 1.44 | 0.876 | 0.802 | 0.628 | 0.726-0.864 | 0.865-0.981 | 0.051 | 0.858 |
| confirm_only_62 | 62 | 8 | 7.08 | 1.02 | 0.994 | 0.957 | 0.808 | 0.840-0.986 | 0.935-1.000 | 0.059 | 0.988 |
| v2_K26_like_confirm_informative | 26 | 16 | 5.98 | 1.50 | 0.904 | 0.665 | 0.437 | 0.887-1.000 | 0.956-1.000 | 0.031 | 0.001 |

The K = 26 row is v2's kind of set (26 confirm tasks solved at least once in S1a), shown under v3's census rule for comparison: there the population-frame SMALL with the concentration guard is 0.001 and v2's own rule 0.002 at the null, and a direction-free 10% reshuffle gives PRESENT_HARM 0.46 because the selected tasks regress (census true D -2.9 pp): the selection effect the census avoids. Its RD targets are on a set with mean success near 0.6, so its absolute effects are about twice the census's. n = 6 and 8 at K = 106 cap above 8 GPU-h (9.03 and 11.97) and are shown only to size the value of reruns.

- **Reading.** At K = 106, n = 4 the census SE of D is about 1.15 pp (1.24-1.29 pp under
  proportional effects), so the 90% interval is about +/-1.9 pp: SMALL is reachable whenever the
  census effect is near zero, and PRESENT fires for a 15% relative drop (about -4.3 pp on the
  census) with probability 0.85-0.96 across structures. The census interval covers the census truth
  in 0.94-0.95 of replicates in every structure. Among replicates whose census truth lies beyond
  either margin, SMALL is declared in at most 0.051 at K = 106 (0.056 at K = 89, 0.051 at K = 62),
  the nominal 5% of the TOST. v2's rule applied to the
  same data would call SMALL in 0.11-0.14 of replicates at a true 15% drop.
- Every interval reports K, n and the number of valid episodes.

## Seeds

Simulation: [42, 43, 44]. Episode order, slot assignment and the sharp-null test: PCG64 seed 42.
vLLM request seed 42 (inert under greedy decoding; vLLM is not batch-invariant, so reruns are not
assumed identical: that is the rerun noise S1a measured). OSWorld tasks have one initial state each.

## Compute caps (D22 counting)

| Job | Cap (GPU-h) | Arithmetic |
|---|---:|---|
| Phase 0 (image build, P0.6, oracle, P0.8-P0.11) | 0 | CPU-only lane jobs, no GRES; about 45 VM-h (oracle 424 states plus sweep about 16 VM-h; P0.6 about 6 VM-h per cell and the V = 20 rung about 2 VM-h; setup checks and probes about 3 VM-h) |
| Overlay build and pre-funded retry | 0.10 | 3 + 3 minutes, as S1a |
| Phase 1 (one job, K <= 106, n = 4) | 6.00 | ceil(3 + 113.2/60 + (1,696 x 197.73/20 + 104.6) x 1.2 x 1.05 / 60) = 360 minutes |
| Registered total | 6.10 | below D20's 8 GPU-h line; 6.87 at the p95 slot price |

The gauntlet's reviewer budget (0.3 GPU-h) is separate. Under S1a's own registered c_proj (the cost
card's high price, 0.011274 GPU-h per episode) 1,696 episodes would be 19.1 GPU-h; the cap rule above
is the Q2 design study's (realized price x 1.2 x 1.05), a decision the program owner has to adopt
(design study section 5).

## Infrastructure failures and exclusions

As `q2-stage1-rescoped-v1` section 15 and D56: an undelivered observation, a guest-server restart, a
setup or postconfig server error (HTTP >= 500 or no reply), a VM or container failure, an engine error
or timeout, and a failed keyboard check are infrastructure losses; a step-0 mismatch is invalid. Both
are re-queued (at most twice). Model behaviour (invalid actions, truncation, wrong state) is never
infrastructure.

## Data rights

OSWorld task configs and checkers: Apache-2.0. LibreOffice and `libreoffice-l10n-ar`: MPL-2.0.
Ubuntu language packs (`language-pack-ar-base`, `language-pack-gnome-ar-base`): translations under
their upstream projects' licences (GTK: LGPL-2.1), recorded per file. Fonts already in the image:
KACST (GPL-2.0), DejaVu (Bitstream Vera licence). Qwen3.5-9B: Apache-2.0. The derived image and any
generated catalogs are derived works under those licences and stay on the host; the image is not
redistributed. Public cotcodec artefacts are metrics, hashes, codings and per-episode records;
screenshots and trajectories stay on the host and in the private archive unless Kevin decides
otherwise. No personal data; the VMs are offline.

## Integrity gate (the seven failure modes)

1. Implementation bug passing self-review: the oracle reads screenshots and the accessibility tree,
   independent of the switch code; positive controls are required; the pilot already caught one bug
   of its own (a headless start forced onto a display, job 1097) and one of the accessibility walk
   (job 1098); a fresh agent audits Phase 0 against this file before the freeze.
2. Hallucinated citation: sources snapshotted with HTTP status and hash; switch sources read at the
   installed build (7.3.7.2) with line numbers.
3. Hallucinated result: no localized-agent measurement exists; simulated numbers come from
   `power-v3.py` with seeds and input hashes; pilot numbers from job records with receipts.
4. Shortcut reliance: the agent may succeed from English document content; that is the registered
   estimand (application chrome over English documents), and the Arabic chrome share is reported.
5. Bug reframed as insight: a half-mirrored layout, a clipped status bar or a setup that diverges
   across cells could look like a treatment effect; O3, O5, O7 and O8 exist for that, and O8's
   defects are reported as part of the treatment.
6. Methodology fabrication: the pool, estimands, decision rules, margins and cap are fixed here before
   any localized data.
7. Frame-lock: the census frame is declared before data, the population frame is reported beside it
   with its own guard, and the infrastructure exit (K0, K1) is a first-class result.

## Owner's prior forecast (not a decision input)

Kevin permits the three downloads and the image surgery passes review: 0.6. Phase 0 admits at least
62 tasks after at most one remedy round: 0.65 (window titles and the status bar are the known risks).
P0.6 passes: 0.85. Phase 1 reached overall, including an admission ruling: about 0.3. If it runs: D
PRESENT_HARM 0.35, D SMALL 0.45, T PRESENT_HARM 0.45, T SMALL 0.35.

## Freeze procedure

Phase 0 is built and its gate run in the lane (CPU only) after this draft and the P0.6 registration
are accepted and the downloads are permitted; a fresh agent's pre-freeze audit checks the
registration against the image, the oracle record and the code; then
`uv run python scripts/preregister.py freeze s2-arabic-cua-locale-v3 program/preregistrations/s2-arabic-cua-locale-v3.md`
and `verify`; then the admission ruling for Phase 1.

## Design decisions (for the owner's acceptance; v2's 31-53 are withdrawn with v2)

54. The census of OSWorld's LibreOffice single-application tasks (106) under rules E1-E5, C1, F1.
55. Dev tasks as Phase 0's development set and members of the census.
56. Census frame primary, population frame reported.
57. Dual margin (5 pp absolute; ratio inside (0.85, 1/0.85)).
58. n = 4 per task-cell, both harnesses, one session.
59. Layout by the finalized `UIMirroring` key in both directions; `SAL_RTL_ENABLED` never set.
60. Coupling remedies only where O2 finds a leak on the dev tasks; content strings never wrapped.
61. SheetPrefix and CTLFont pinned in all four cells.
62. P0.6 extended with A2, A6 and a V = 20 rung.
63. O7 (window title) and O8 (RTL-defect inventory) added to the oracle.
64. The tagged pseudo-catalog cell (P0.8).
65. K_min = 62; re-queue of infrastructure and step-0 failures, at most twice.
66. K4 and K5 as stops on the English cell.
67. The cap rule (realized price x 1.2 x 1.05 at the high slot); 6.10 GPU-h registered.
68. Moderators from S1a's click coordinates and O8.
69. The derived image built offline by `dpkg-deb -x` and `debugfs -w`, after Kevin permits the three
    downloads.
