# S2 v3.1: Arabic interface text versus mirrored layout on the certified OSWorld stack, Phase 0 decided on the CPU lane and a Phase 1 census of OSWorld's LibreOffice tasks with a placebo rearrangement (s2-arabic-cua-locale-v3.1)

Status: DRAFT. Not frozen, not admitted, no ledger row. v3.1 is the repair of `s2-arabic-cua-locale-v3`
after its gauntlet wave 1 (score 60; decision D74), written on 2026-10-11 by the single owner of the
fresh S2 v3 repair run on branch `gauntlet/s2v3-locale`. `s2-arabic-cua-locale-v3.md` (the draft the
wave-1 reviewers scored, sha256 `74f969e1...`) is left unedited; v1 and v2 too. The proposal is
`program/proposals/2026-10-11-s2v3-arabic-cua-locale-pilot.md` (section "Changes after wave 1"); the
evidence bundle is `program/proposals/evidence/2026-10-11-s2v3-arabic-cua-locale-pilot/`. Phase 0 is
CPU-only. Phase 1's registered caps sum to 6.83 GPU-h at K = 106 (7.70 at the p95 slot price), below D20's 8 GPU-h line; whatever the
gauntlet scores, Phase 1's admission is Kevin's ruling under D24 and D70, and fetching the shipped
Arabic language packs is a download he approves. Numbers labelled "simulated" come from
`compute/power-v4/power-v4.py` (seeds 42, 43, 44; v3's `compute/power/` outputs are kept as they
were and superseded where v4 re-ran them); numbers labelled "pilot" come from the CPU Slurm jobs
recorded under `compute/pilot/` (wave 1: 1097-1100) and `compute/pilot-r1/` (this repair: 1116,
1120, 1123, 1124, 1129 cancelled, 1131, 1132, 1139-1141), and the orx node of
`scripts/run_s2v3_phase0_doctor.py`.

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

## Changes in v3.1 (repair after gauntlet wave 1, decision D74)

Wave 1's largest defect (both reviewers, the feasibility refuter): the CPU pilot exercised only
the layout switch, so it decided neither K0 nor K1. Its identification refuter added that the
census truth of D includes changes with no direction, and its recorder confirmed a miscomputed
sharp-null variance and an admission rule that conditioned on how the treatment renders. v3.1:

| v3 | v3.1 | Evidence |
|---|---|---|
| No Arabic catalog rendered; ar-LTR only on blank documents; "pseudo-Arabic" cell fell back to English | A generated pseudo-Arabic interface (Arabic-script strings of matched length, one Arabic letter per Latin letter, placeholders, mnemonics, digits and acronyms kept) built offline in the job from the installed build's own English strings: 13,226 exact `.ui` keys, 155,390 candidate code-string keys (168,616 catalog entries), 5,580 registry labels (`res/registry_ar.xcd`); keyboard-shortcut tables and command URLs are never transformed. Every cell, ar-LTR included, rendered at every candidate task's post-setup state | `compute/pilot-r1/` capture 1131: 1,022 renders, 0 errors, all stable; median 0.93 of visible named chrome in Arabic script in the ar cells |
| Interface language set by `ooLocale` alone | Both keys of the interface language, `Setup/L10N/ooLocale` and `Linguistic/General/UILocale`, finalized in the selector | debug 1123: with `ooLocale` alone the gettext strings switched but every registry label (menus, commands, toolbars) stayed English; the wave-1 cell L4 had this defect even apart from its missing catalogs |
| Selector in an extra configuration layer after `res:` | The selector file `zz-s2v3-cell.xcd` in a copy of `/etc/libreoffice/registry` that both system layers (`xcsxcu:` and `res:`) point at: the registered location, only the directory path differs | capture 1131 records each render's `CONFIGURATION_LAYERS` line and selector hash |
| `ooSetupSystemLocale` pinned to en-US | Left at its default, the system locale, which is the same in every cell | smoke 1124: the pin changed Calc's default paper (A4 to Letter) in saved files against the stock cell |
| `LANGUAGE=ar` for GTK (a second difference with no mechanism) | Dropped: the cells differ only in the selector file (and PL in its toolbar definitions) | capture 1131 |
| Toolbars text-only in the container (broken icon-theme symlinks in the private copy) | Relative symlinks re-pointed; the VM's icon theme (Yaru) pinned identically in every cell including stock | capture 1131 worker records (12 symlinks) |
| Oracle O2, O3, O6, controls not implemented; O3 on AT-SPI extents; O5 not discriminative | Implemented (`harness/s2_locale/oracle.py`): O1-O8 on pixel-located boxes (AT-SPI only in LTR cells, with the VCL coordinate offset estimated on the dev tasks), O2 as whole-run pixel identity, O5 by full-width alignment with a flipped comparison, O6 against a stock cell, planted controls in the application and synthetic plants on every task | orx node run «ORX_RUN» and Slurm 1132 |
| No tagged cell | Cell Q: LibreOffice's own KeyID UI language `qtz` tags every gettext string; registry labels tagged by a generated `registry_qtz.xcd` | capture 1131 |
| Admission: O1-O7 pass in all four cells (conditions on how the treatment renders; discretionary exclusion or remedy) | Intention to treat: only agent-independent failures exclude; O2, O3, O5 and O8 are treatment descriptors and moderators; deterministic rules committed before the sweep (`harness/s2_locale/phase0.py`, commit `c8669d2`) | K0 below |
| Census truth of D includes direction-free change; no comparator | A fifth Phase 1 cell, PL (placebo): the en-LTR interface with every toolbar's items in a fixed seeded order; P3 is read as a total effect with no mechanism; a mechanism label needs the population-frame excess of en-RTL over PL | simulated: false MIRROR_SPECIFIC 0.023-0.027 under direction-free scenarios |
| Sharp-null test with Var = v | Var = 4v | simulated rejection at the null 0.048 (v3: 0.32) |
| Phase 1 cap 6.10 GPU-h (4 cells) | 6.83 GPU-h at K = 106, 7.70 at the p95 slot (4 cells at n = 4 plus PL at n = 2) | `power-v4.json` costs |

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
tolerances, the mirror specification, the VCL coordinate offset, positive controls and every remedy
are decided on them. Confirm and reserve tasks meet Phase 0 only through frozen checks and the
intention-to-treat admission rule (no discretionary exclusion; a remedy applies to all cells and is
followed by a full rerun of the oracle, thresholds unchanged). All admitted tasks, dev included, form the Phase 1 census: nothing about the agent is tuned on any
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
- **P0.3 Switches (system layer only).** The Phase 1 cells differ only in one selector file,
  `/etc/libreoffice/registry/zz-s2v3-cell.xcd` (the system configuration layer of this build, which
  both its `xcsxcu:` and `res:` layers read; the file sorts after `main.xcd`, so its finalized
  values win inside the layer and cannot be overridden by the user profile), checked byte for byte:
  - text: `org.openoffice.Setup/L10N/ooLocale` and `org.openoffice.Office.Linguistic/General/UILocale`,
    both `en-US` or both `ar`, finalized. Both keys are needed: `ooLocale` selects the gettext
    catalogs, `UILocale` (what Tools > Options > Language Settings > User interface writes) decides
    the configuration locale of every registry label (debug job 1123: with `ooLocale` alone the menus,
    commands and toolbars stayed English);
  - layout: `org.openoffice.Office.Common/I18N/CTL/UIMirroring` = false (LTR) or true (RTL), finalized,
    in every cell; `SAL_RTL_ENABLED` is never set.
  - pins in every derived cell: `SheetPrefix` "Sheet", `CTLFont` false, `EnglishFunctionName` true.
  No environment variable differs between cells (v3's `LANGUAGE=ar` is dropped: GTK's own strings
  follow whatever LibreOffice does in-process, identically in container and VM). Nothing is written
  to the user profile's `registrymodifications.xcu`, which three checkers read.
  - The placebo cell PL (P1.2) has the en-LTR selector and differs in its toolbar definitions
    (`share/config/soffice.cfg/modules/*/toolbar/*.xml`, each toolbar's items and separators in an
    order fixed by a SHA-256 key of (seed 42, file, position); 369 of 386 definitions change). A
    finalized window-state `DockingArea` in the system layer did not move the toolbars (debug job
    1123, three forms), so the placebo rearranges within the toolbars.
  - Per-VM cell mechanism (Phase 1 and P0.6): five pinned qcow2 overlays of the derived image, one
    per cell (E, A, ER, AR, PL), each differing from the derived base only in its selector or
    toolbar files, digests recorded; the lane gets a per-slot cell field that selects the overlay's
    path and checks its SHA-256 before `docker run` (`vm_run_argv` mounts one read-only qcow2 per VM
    container already). This is new lane code, reviewed before the freeze.
- **P0.4 Direction coupling and isolation.** Coupling (a string's internal order changing with the
  layout) is measured, not assumed: O2 runs first with the shipped catalogs. Where O2 finds a
  coupling leak on the dev tasks or the sweep, the remedy wraps that string source in FSI ... PDI
  (U+2068 ... U+2069) in all four cells (Arabic `.mo` catalogs rewritten; English through generated
  `en_US` `.mo` catalogs, which this build loads: pilot K1 shows a tagged `en_US` `sc.mo` renaming the
  first sheet "⟦Sheet⟧1"; registry labels through generated system-layer label overrides). Strings that
  P0.8 finds in saved outputs are never wrapped (pilot K2: a wrapped STR_TABLE_DEF puts U+2068/U+2069
  into the saved sheet names).
- **P0.5 Held fixed in every cell.** Task instructions, documents and checker inputs (English, LTR);
  the system shell (English, LTR); `ooSetupSystemLocale` at its default, the system locale
  (en_US.UTF-8 in every cell; number, date and paper defaults; a pin to en-US changed the saved paper
  size against stock, smoke 1124); the document default language; `SheetPrefix` = "Sheet"
  (finalized); `CTLFont` = false (finalized); Calc's English function names (finalized); autocorrect
  and spelling languages; the X keyboard map `us` and no input method; screen resolution 1920x1080;
  the agent, decoding, step cap and settles. UI digit shaping, translated status-bar fields and the
  localized placeholder prompts of empty Impress placeholders (pilot: they appear inside the slide in
  the ar cells and render right-to-left) are part of the text treatment, not held fixed.
- **P0.6 Delta certification of the action path (K1).** The frozen acceptance suite of
  `q2-action-path-v2` (executor and catalog unchanged) on each of the five cell overlays: C1-C4, A1 at
  N = 1, A5 (D53's delta), plus A2 (both harness adapters), A6 (the Writer typing canary, read back)
  and the keyboard-map check, pass lines as D53's; then one V = 20 rung with the five cells
  interleaved (4 VMs each); A3 once, in ar-RTL. A registered deviation of `q2-action-path-v2` (or a
  short registration of its own) is written before it runs. VM-hours from `vm_hours.json`: C1 0.12,
  C2 0.25, C3 2.82, A1 at N = 1 1.53, A5 0.30, so 5.0 per overlay and 25.1 for the five; A2 1.62 and
  A6 0.87 per overlay (12.5), A3 4.76, the rung about 2: about 44 VM-hours in all, CPU only. What the
  CPU lane decided in this repair is listed under "The executable part of Phase 0" below.
- **P0.7 Factorial render oracle** (`harness/s2_locale/oracle.py`, `phase0.py`). Captured at every
  admitted task's post-setup state (setup replayed as the task config states; download and open
  emulated in the container pilot, every step in the lane). Inputs: the screenshot and the
  accessibility tree (role, name, box). Boxes: accessibility extents are used only in left-to-right
  cells; VCL-drawn widgets report them `dy` px too high under the container's window manager (the
  native GTK menubar and welded entries do not), so each node takes 0 or `dy` by which frames its
  content with a more uniform border, `dy` estimated on the 17 dev tasks (23 px, range 23-27). In a
  right-to-left cell every box is located by ink: the element's LTR ink is template-matched near its
  reflection (locating tolerance 10% of template pixels: a mirrored toolbar redraws its icons with
  one-pixel offsets), and anywhere in its row band if not there. Checks:
  - O1 structure: (path, role) of showing accessibles; text pairs (E-A, ER-AR) must be identical
    (instrument check I3); layout-pair differences are O8 structure defects;
  - O2 text runs: each text element's whole ink run, re-cut by one rule around its LTR box and around
    its located RTL position, is the same image (size within 1 px, at most tol2 = max(0.02, 2 x the
    worst identity A/A mismatch) of pixels differing); a failure is a coupling-leak candidate and
    goes to P0.4's remedy on the dev tasks;
  - O3 mirror fidelity: the element's ink lies within tol3 px of its reflection inside the window.
    The mirror specification frozen on the dev tasks is tol3, the 95th percentile of |dx| among
    dev-task elements located within 24 px of their reflection (20 px): this build mirrors toolbars
    and the menubar by reversing their packing, not by exact reflection. Reported per task: share at
    the reflection, share located elsewhere in the row, share not located (altered ink: RTL icon
    variants, compound widgets), clipped;
  - O4 order under text swap: sibling left-to-right order equal in E and A (accessible boxes) and in
    ER and AR (located boxes) (I4);
  - O5 content identity: the document region of E aligned by translation (full width, coarse then
    fine) in each other cell; a pass is at most tol5 differing pixels, a match of the horizontally
    flipped region marks a mirrored document, flip-symmetric content is "uninformative";
  - O6 invisibility: E equals the stock cell S within tol6 pixels (I2);
  - O7 window title: byte-identical across the Phase 1 cells and the placebo;
  - O8 RTL-defect inventory: per task, elements outside the mirror specification, clipped, or not
    located; descriptive and a moderator, never an exclusion.
  A/A: a second en-LTR render of every task (E2) and a second en-RTL render of each dev task (ER2);
  tol5 and tol6 = max(50 px, 2 x the worst A/A count). Positive controls: in the application, a
  planted coupled string (the status bar's language field rendered "English (USA):" by an en_US
  catalog in E and ER, cells PCL and PCR; bidi moves the colon in the mirrored VCL widget) and a planted
  document change (cell PD: ER with the first text run of the document changed before it opens), on
  the 17 dev tasks; synthetic plants on every task's ER screenshot (a widget shifted by tol3 + 8 px,
  a text run with its halves swapped, an inverted 48 x 14 block in the document region).
- **P0.8 Source coverage (tagged cell Q).** UI language `qtz`, LibreOffice's KeyID locale: every
  gettext string renders as a five-character key, U+2016 and the English text, with no catalog;
  registry labels carry a generated `[r]` + U+2016 tag. (a) Visible chrome without a tag lies outside
  the catalogs and is listed; the share of tagged chrome that the pseudo-Arabic catalog renders in
  Arabic script is its coverage. (b) A tag or an Arabic letter in a saved result file that the en-LTR
  file lacks is a content leak; it excludes a task only if the task's checker reads it (P0.9).
- **P0.9 Functional A/A and checker invariance across cells.** (a) Each task's own postconfig (strict
  activate_window, Ctrl+S, Enter, convert) runs in every cell after the capture; the result file is
  kept. (b) On the dev tasks a keyboard edit probe precedes it (Calc: a value and `=SUM(1;2)` below
  the data; Writer: a typed line with digits and symbols). (c) Checker invariance: the task's gold end
  state and its do-nothing end state (the checker-mutation study's controls) are opened and saved
  through the task's own postconfig in each cell by that study's GUI-faithful save stage, and scored
  by the real OSWorld checker in its metric container; a cell that changes the verdict on either
  relative to en-LTR changes the outcome without an agent.
- **P0.10 Config invariance (C1 tasks).** After a fixed probe session the keys that differ between
  cells must not include a key the task's checker reads, and the checker's verdict on the
  post-setup state must agree across cells; otherwise the task is dropped.
- **P0.11 Setup validation.** Every admitted task's setup runs offline in each cell (the 27 reserve
  tasks have never been setup-checked on the lane).
- **P0.12 Moderators, frozen before any GPU job.** (a) Positional exposure: for each confirm task with
  a successful S1a English episode, the share of that episode's actions that are clicks, split by
  target: clicks inside the document region (O5's region, which mirroring shifts by its measured
  horizontal offset, not reflects) and chrome clicks (displaced to the located reflection of the
  nearest element); the mean displacement per task; (b) lexical overlap: distinct English interface
  labels visible at the post-setup state whose lowercased tokens appear in the instruction; (c) O8's
  per-task count (it varies by task: 15-23 elements outside the specification in the pilot);
  (d) baseline success: the task's S1a 9B English solve rate (or the en cell's), entered in every
  moderator regression because D_t >= -p_LTR,t.
- **P0.13 Arabic chrome share.** Per task and state, the share of visible interface strings rendered
  in Arabic script in the ar cells (untranslated strings stay English in both layout levels).

Phase 0 admission (K0), intention to treat. A task enters Phase 1 unless a failure that no agent
could get past occurs in a Phase 1 cell (E, A, ER, AR) or the placebo PL:
- A1 setup: the task's files are staged offline and its document window opens;
- A2 window title: identical across those cells (O7), and equal to the postconfig's strict
  activate_window target where the en-LTR window carries that target;
- A3 save: the task's own postconfig save writes the result file;
- A4 checker invariance (P0.9c): the checker's verdict on the gold and on the do-nothing state, each
  saved in the cell, equals en-LTR's; a task with neither falls back to identical saved-file parts
  (timestamps, rsids and the parts that differ between the two en-LTR replicates removed).
A content leak (P0.8b) or a document change (O5) that does not change a verdict is a property of the
treatment and is reported, not a reason to exclude. Instrument checks, all required: I1 planted
controls detected (in-application coupled string and document change wherever the plant is visible;
synthetic plants: a bar fixed before Phase 0 proper, see below), I2 O6, I3 O1 text pairs, I4 O4,
I5 P7, I6 A/A, each on at least 95% of tasks or compared parents. Phase 1 runs only if at least
K_min = 62 tasks are admitted, the instrument checks hold and P0.6 passes (K1); otherwise
infrastructure exit, with the image, the oracle record and the leak and defect inventories published.

### The executable part of Phase 0 run in the CPU lane

Wave 1 (jobs 1097-1100) is described in v3. This repair (all CPU-only Slurm jobs, no GRES, one at a
time after a queue check, in the certified VM's own LibreOffice 7.3.7.2 userland as a container with
Xvfb and openbox, `cotcodec-q2-lo-vm@sha256:f5b4c40e...`; scoring in the checker-mutation study's
metric container `sha256:2006c1a9...`; simulations in the project's research image without a GPU):

| Job | What | Result |
|---|---|---|
| 1116 | smoke, 3 dev tasks x 12 cells | the generated catalogs load; the Arabic cells' saves did not write and toolbars had no icons (both traced below) |
| 1120, 1123 | debug | (i) with `ooLocale` alone the registry labels stay English: `UILocale` added; (ii) the transformed keyboard-shortcut table broke Ctrl+S in the Arabic cells: shortcut tables, command URLs and identifiers are never transformed; (iii) the icon-theme archives are relative symlinks that dangled in the private copy: re-pointed; (iv) a window-state `DockingArea` pin in the system layer does not move toolbars (three forms): the placebo shuffles items within toolbars |
| 1124 | smoke, 1 dev task x 13 cells | all saves written; icons; menus in Arabic script; the qtz cell tags 102 of 104 named chrome elements; the planted coupled string renders ":English (USA)" mirrored. The en-LTR saved file differed from stock in its paper size: the `ooSetupSystemLocale` pin was removed |
| 1129 | full sweep, cancelled after 94 renders | the pin defect above |
| 1131 | full sweep: 106 tasks x 9 cells (S, E, E2, A, ER, AR, AD, Q, PL) and 17 dev tasks x 4 cells (ER2, PCL, PCR, PD) | 1,022 renders in 15.4 min, 0 errors, all frames stable, accessibility dump for every render, every postconfig save written; `setxkbmap -query` reports `us` in all 16 workers |
| 1132 | the oracle over capture 1131 (host replicate of the orx node) | see K0 below |
| 1139 | checker invariance, saves: 88 gold and 97 do-nothing jobs (106 tasks; 17 without a gold) x 6 cells (S, E, A, ER, AR, PL) through the checker-mutation study's GUI-faithful save stage | 1,110 saves, 0 save failures |
| 1141 | checker invariance, scoring with the real OSWorld checkers (locked venv) | 1,110 verdicts; for every task and both controls the verdict is the same in all six cells (83 golds pass and 5 fail in every cell; 97 do-nothing states fail in every cell) |
| 1142 | `power-v4.py` | the tables below (52.6 s) |
| orx node «ORX_EXP» run «ORX_RUN» | `scripts/run_s2v3_phase0_doctor.py` over the committed manifest of 1131 and the verdicts of 1141 | «ORX_SUMMARY» |

K0 as decided here:
- Under the rules committed before the sweep (`harness/s2_locale/phase0.py` at `c8669d2`): **FAIL.**
  Its admission proxy excluded any task with a saved-file difference or a content leak, which is
  stricter than this registration's own P0.8b and P0.9 (a leak excludes only if the checker reads
  it): 53 of 106 admitted (exclusions: content leaks in Q 53 tasks, in A and AR 34; saved-file
  differences 23; window title 2). Its I1 required every synthetic plant to be detected: O3 caught
  101 of 106 shifted widgets and O2 95 of 106 reordered runs; the in-application coupled string was
  flagged on all 17 dev tasks; the in-application document change was caught on all 15 dev tasks
  where it was visible (on 2 Impress tasks the changed run is not on screen: PD's document region
  equals E's, so those plants are not controls). I2-I6 passed: O6 0 differing pixels on 106 of 106,
  O1 text structure identical on 212 of 212 pairs, O4 943 of 943 parents, P7 106 of 106, A/A 106 of
  106 (0 pixels).
- Under this registration's P0.8b and P0.9 (checker invariance, A4 above; the operationalization
  through the gold and do-nothing controls was chosen after the proxy's result, the semantics are
  v3's): **105 of 106 admitted** (46 Calc, 39 Impress, 20 Writer; 61 confirm, 17 dev, 27 reserve);
  the one exclusion, `2cd43775`, has window titles that differ across cells (its setup opens no
  document; the first window is a start-centre in some renders and "Untitled 1", localized in the ar
  cells, in others). No cell changed any verdict. The remaining K0 failure is I1's synthetic-plant
  sensitivity (95% for O3, 90% for O2) against the committed 100% bar; Phase 0 proper fixes a bar, or
  a uniqueness test for look-alike neighbours, before it runs.
- What the oracle measured (descriptors, not exclusions): mirroring puts 84% of chrome
  elements within the mirror specification (tol3 = 20 px) of their reflection and locates 94% in
  their row (the rest have altered ink: RTL icon variants, compound widgets, clipped status-bar
  fields); the document is not mirrored (O5 passes for ER on 105 of 106 tasks; the flipped document
  differs by at least 7,759 pixels on every task); text runs: 81% of E-ER runs are pixel-identical, the rest are
  coupling-leak candidates (labels, sidebar list items) or clipped status-bar fields, for P0.4's
  remedy on the dev tasks; in 14 of 40 Impress tasks the Arabic interface changes the slide
  itself (O5 fails for A and AR): empty placeholders show localized prompt text, right-to-left;
  content leaks are localized default strings written on save (slide-master and notes-master
  placeholder text in Impress, style names in Writer, header and footer defaults in Calc), none read
  by a checker in any task (A4); the qtz cell leaves 2 named chrome elements per task untagged at
  the median (1-10): names that are not catalog strings ("Menu", sheet names) and, in Impress, the
  welded GTK sidebar panel's labels, which GtkBuilder translates directly so LibreOffice's KeyID
  never sees them (the generated `.ui` catalog does render them in Arabic script); of the tagged
  chrome, the pseudo-Arabic catalog renders 93% in Arabic script (median; minimum 92%).

What the CPU lane decided toward K1 (P0.6): the keyboard map is `us` in every worker; the postconfig
activation and save path works in every cell for every task (1,022 renders, 1,110 control saves);
on the 17 dev tasks the keyboard edit probe (a Calc value and formula, a typed Writer line) saves
identical files in en-RTL, the placebo and the en-LTR replicate, and in the Arabic cells differs only
by localized defaults that no checker reads. Not decided: C1-C4, A1 at N = 1, A5, A2, A3, A6 and the
V = 20 rung, which run in the VM lane on the five cell overlays (about 44 VM-hours) after (a) Kevin
approves the three package downloads, (b) the image-surgery script and the per-slot overlay lane
change are written and reviewed, (c) a deviation of `q2-action-path-v2` is registered, and (d) the
render oracle and checker-invariance test are rerun on the overlays with the shipped catalogs.

## What the D53 certification covers for the localized cells

As v2's table: the runtime, the harness adapters, the lane and V <= 32 carry over; the derived
image and its overlays ("another image"), the keyboard map under an Arabic interface, the guest
server under localized applications and the rendered treatment are not covered. P0.6 re-certifies
the input path on each overlay (C1-C4, A1 at N = 1, A5), the harness layer (A2), the Writer canary
(A6) and the concurrency Phase 1 uses (one V = 20 rung).

## Phase 1 (only after K0 and K1 pass and an admission ruling)

- P1.1 Tasks: the admitted census, K of them (62 <= K <= 106). Cells: en, ar-LTR, en-RTL, ar-RTL.
- P1.2 Placebo cell PL: the en-LTR interface with the toolbar items in the fixed seeded order (P0.3),
  n_pl = 2 per task (one per harness). It is a direction-free rearrangement of the most-clicked chrome
  targets, smaller than mirroring: in the pilot it moved 53% of located chrome elements (mirroring:
  all) by a median per-task mean of 264 px (mirroring: 996 px). It answers whether a mirror cost
  exceeds the agent's sensitivity to rearranging its toolbars, not to an equally large rearrangement.
- Episodes: n = 4 per (task, cell) in the 2x2 (2 per harness) and 2 in PL. Total 18 K (1,908 at
  K = 106).
- Order: one serving session (one GPU job and its CPU VM job). Task blocks in a seeded order (PCG64
  seed 42); within a block the 18 episodes in a seeded interleave; cells assigned to VM slots at
  random within each batch of 20, slot and batch recorded.
- Step-0 check: each episode's first screenshot, after the clock and caret masks, against the Phase 0
  reference for its (task, cell) recorded in the same lane on the same image; the tolerance from
  Phase 0's A/A. A mismatch makes the episode invalid.
- Keyboard check: `setxkbmap -query` reports `us` and no input method runs at every episode start; a
  failure is an infrastructure loss.
- Re-queue: an infrastructure loss or a step-0 failure is re-queued at the end of its task block, at
  most twice per episode. A task enters the analysis if each of its four 2x2 cells has at least 2 valid
  episodes (and PL at least 1 for the placebo contrasts); cell means use all valid episodes (harnesses weighted equally where both exist).
- Cap (D22 counting): one job, ceil(3 + L/60 + (N x s / V + drain) x 1.2 x 1.05 / 60) minutes with L =
  113.2 s, drain = 104.6 s, V = 20, N = 18 K and s = 197.73 s (the mean slot of S1a's 9B episodes that
  ran to the 15-step cap), plus 6 minutes for the overlay build and retry.

  | K | episodes | physical GPU-h (high slot) | job cap incl. overlay (min) | cap (GPU-h) | cap at the p95 slot 223.6 s (GPU-h) |
  |---:|---:|---:|---:|---:|---:|
  | 62 | 1,116 | 3.13 | 245 | 4.08 | 4.60 |
  | 89 | 1,602 | 4.46 | 346 | 5.77 | 6.50 |
  | 100 | 1,800 | 5.00 | 387 | 6.45 | 7.27 |
  | 106 | 1,908 | 5.30 | 410 | 6.83 | 7.70 |

  n = 4 in PL as well would cap at 7.57 GPU-h at K = 106 (8.52 at the p95 slot); n = 2 keeps the
  p95-slot cap under 8 GPU-h. Beyond the cap K8 stops the job at the last complete task block.
  The cap rule (realized price x 1.2 x 1.05 at the high slot) is the Q2 design study's; under S1a's
  registered c_proj (0.011274 GPU-h per episode) 1,908 episodes would be 21.5 GPU-h. Adopting the
  rule is the program owner's decision, part of the admission ruling (D24).

## Estimands

Per task t, cell means y_en, y_arL, y_enR, y_arR (harnesses equally weighted).

- **Primary, D (layout main effect):** D = mean_t D_t, D_t = ((y_arR - y_arL) + (y_enR - y_en)) / 2.
  Relative companion: R_D = S_RTL / S_LTR with S_RTL = mean_t (y_enR + y_arR) / 2 and
  S_LTR = mean_t (y_en + y_arL) / 2.
- **Secondary, T (Arabic interface text main effect):** T = mean_t ((y_arL - y_en) + (y_arR - y_enR)) / 2,
  with R_T likewise. T changes language, script, UI digits and the word overlap between English
  instructions and interface labels together; it is not a "glyph" effect.
- **Placebo contrasts (en level):** P = mean_t (y_PL - y_en), the effect of the direction-free
  rearrangement; E_dir = mean_t (y_enR - y_PL), the mirror's excess over it.
- **Secondary:** the total Delta = T + D; the interaction I; the dossier's conditional contrasts
  M_ar = ar-RTL - ar-LTR and G = ar-LTR - en; D and T by harness and application (descriptive);
  fractional checker scores (sensitivity); the same estimates without the 7 S1a-flagged tasks
  and without the 43 tasks checked by `compare_pptx_files`, whose element-order defect the
  checker-mutation study found (sensitivity); D and T on all 106 candidates beside the admitted
  census (intention to treat: an excluded task's cells are analysed as measured); process metrics (steps, cap share, invalid actions) by cell.
- **Moderators (task-level regressions, CR2 standard errors, baseline success as a covariate):** D_t
  on positional exposure (P0.12a, chrome and document clicks separately) and on O8's per-task count;
  T_t on lexical overlap (P0.12b) and on the Arabic chrome share (P0.13). A mechanism is named only if the 95% CR2
  interval excludes 0 in the predicted direction (negative); otherwise "unresolved".
- **Reference:** the en cell against S1a's 9B English success on the 62 overlapping tasks (K5).

## Decision rules (primary D; the same labels are reported for T)

Census frame (primary; "these tasks"). Var(D) = (1/K^2) sum_t v_t, where v_t sums, over the four
cells, (1/4) x the variance of the cell mean, estimated without bias per (task, cell, harness) from
its m valid episodes as m/(m-1) p(1-p)/m. log R_D has delta-method variance Var(S_RTL)/S_RTL^2 +
Var(S_LTR)/S_LTR^2 from the same within-task variances (the two layout levels use disjoint
episodes).

- **PRESENT:** the 95% normal interval of D excludes 0; labelled PRESENT_HARM or PRESENT_BENEFIT. The
  stratified randomization test of the sharp null (no layout effect on any episode distribution;
  strata task x harness x text level, successes fixed; S = sum (k_RTL - k_LTR) with variance 4v, v
  the hypergeometric variance of k_RTL; v3 used v) is reported beside it; disagreement at 0.05 gives
  PRESENT_FRAGILE.
- **SMALL:** the 90% interval of D lies inside (-5, +5) pp and the 90% interval of log R_D lies inside
  (log 0.85, -log 0.85). PRESENT and SMALL can hold together (PRESENT_AND_SMALL).
- **INCONCLUSIVE:** neither.
- **SMALL is suppressed** (reported as SMALL_DEGRADED_INSTRUMENT) if K5 fires.
- **Governing labels for P3 (total effect, no mechanism):** CONFIRMED if PRESENT_HARM (with
  PRESENT_AND_SMALL reported as "a small harm"); FALSIFIED if SMALL without PRESENT, or
  PRESENT_BENEFIT; OPEN otherwise.
- **Direction-specific reading (decides only whether a mechanism may be named):** E_dir in the
  population frame (t interval over tasks, df K - 1): MIRROR_SPECIFIC if its 95% interval lies below
  0; NO_EXCESS if its 90% interval lies inside (-5, +5) pp; otherwise UNRESOLVED. The population
  frame is used because a direction-specific claim is about the mechanism: it must hold beyond the
  idiosyncratic task-level reactions that any one rearrangement produces (a census-frame version
  is reported; under direction-free reshuffles it calls MIRROR_SPECIFIC far above 2.5%, 0.068 and 0.143 under reshuffles of 10% and 30% of tasks).
  A Negative-Result row that names relocation, left-to-right priors or RTL defects requires
  MIRROR_SPECIFIC and the matching moderator slope; otherwise D is reported as a net change.

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
| K9 | D PRESENT_HARM and E_dir not MIRROR_SPECIFIC | D is reported as a net change; no mechanism row of the Negative-Result table is claimed |

## Predictions and falsifiers

| | Prediction | Falsifier (reachable?) |
|---|---|---|
| P1 | Phase 0 admits at least 62 tasks | K0 (reachable: with the real Arabic catalogs, window titles may change through a translated module name, and the pilot already found a clipped mirrored status bar and unmirrored accessibility extents) |
| P2 | P0.6 passes | K1 |
| P3 | D < 0: mirroring lowers success on these tasks (a total effect, no mechanism attached) | D is SMALL (census) or PRESENT_BENEFIT. Simulated P(SMALL) under the null at K = 106, n = 4: 0.97 (homogeneous), 0.92 (task-specific mixed-sign perturbation), 0.82 and 0.62 (reshuffles of 10% and 30% of tasks) |
| P4 | T < 0 | T is SMALL (census) or PRESENT_BENEFIT (same operating characteristics) |
| P5 | The D_t slope on positional exposure is negative | its 95% CR2 interval lies above 0 (named only if below) |
| P6 | The T_t slope on lexical overlap is negative | its 95% CR2 interval lies above 0 (named only if below) |
| P7 | The layout switch is one treatment whether set by the key or by the language | Phase 0: the ar cell with UIMirroring (AR) and the ar cell whose direction follows the language (AD) differ beyond tol6 pixels at a task's post-setup state. Pilot (capture 1131): identical in 106 of 106 tasks (0 differing pixels) |
| P8 | The mirror cost exceeds the toolbar rearrangement's (E_dir < 0) | E_dir NO_EXCESS (population frame) |

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

- **Propensity model** (`power-v4.json` `prior`, unchanged from v3): cell level, 124 (task, harness)
  cells of the 62 confirm tasks with 4 trials each, beta-binomial a = 0.099, b = 0.246; task level,
  62 tasks with 8 trials, a = 0.137, b = 0.342; the 44 tasks without records draw from the task-level
  fit; one session with a common logit shift of SD 0.3; 2,000 replicates per seed, seeds 42, 43, 44.
- **Scenarios** pair a mirror structure with a placebo structure. Generic (direction-free) scenarios
  give the placebo the same structure as the mirror, drawn independently; mirror-specific ones give
  the placebo none, or less. Targets are relative effects on the census (calibrated on a fixed bank).
- **Registered rules** as in "Decision rules": census-frame D (PRESENT, SMALL with the dual margin),
  the corrected sharp-null test and PRESENT_FRAGILE, P3's governing labels, E_dir in the population
  frame. Simulated by `compute/power-v4/power-v4.py` (Slurm 1142), tables by `tables-v4.py`:

Census of all 106 candidates, n = 4 in the 2x2, n_pl = 2 (cap 6.83 GPU-h):

| Scenario | kind | census true D (pp) | PRESENT_HARM | SMALL | P3 CONFIRMED | P3 FALSIFIED | sharp-null reject | PRESENT_FRAGILE | MIRROR_SPECIFIC (population) | MIRROR_SPECIFIC (census, reported) | NO_EXCESS | 95% coverage of census D |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| null (no effect) | null | 0.00 | 0.024 | 0.975 | 0.024 | 0.970 | 0.048 | 0.006 | 0.024 | 0.015 | 0.587 | 0.950 |
| task-specific perturbation N(0, 1), both cells | generic | -0.00 | 0.059 | 0.929 | 0.059 | 0.934 | 0.103 | 0.016 | 0.024 | 0.029 | 0.389 | 0.950 |
| reshuffle of 10% of tasks, both cells | generic | -0.02 | 0.129 | 0.816 | 0.129 | 0.863 | 0.218 | 0.036 | 0.025 | 0.068 | 0.079 | 0.949 |
| reshuffle of 30% of tasks, both cells | generic | -0.04 | 0.222 | 0.629 | 0.222 | 0.768 | 0.341 | 0.095 | 0.023 | 0.143 | 0.000 | 0.950 |
| uniform -15%, mirror and placebo alike | generic | -4.31 | 0.961 | 0.066 | 0.961 | 0.034 | 0.960 | 0.003 | 0.027 | 0.014 | 0.640 | 0.949 |
| complete breaks -15%, both alike | generic | -4.35 | 0.859 | 0.181 | 0.859 | 0.135 | 0.840 | 0.019 | 0.024 | 0.076 | 0.093 | 0.950 |
| mirror uniform -10%, placebo none | specific | -2.87 | 0.708 | 0.380 | 0.708 | 0.274 | 0.702 | 0.015 | 0.287 | 0.218 | 0.267 | 0.954 |
| mirror uniform -15%, placebo none | specific | -4.31 | 0.961 | 0.066 | 0.961 | 0.034 | 0.960 | 0.003 | 0.555 | 0.474 | 0.107 | 0.949 |
| mirror uniform -20%, placebo none | specific | -5.74 | 0.998 | 0.004 | 0.998 | 0.002 | 0.998 | 0.000 | 0.795 | 0.741 | 0.034 | 0.947 |
| mirror proportional -15%, placebo none | specific | -4.32 | 0.920 | 0.051 | 0.920 | 0.047 | 0.919 | 0.005 | 0.508 | 0.434 | 0.091 | 0.951 |
| mirror on a quarter of tasks -15%, placebo none | specific | -4.34 | 0.881 | 0.126 | 0.881 | 0.105 | 0.871 | 0.011 | 0.432 | 0.472 | 0.083 | 0.950 |
| mirror complete breaks -15%, placebo none | specific | -4.35 | 0.860 | 0.181 | 0.860 | 0.130 | 0.841 | 0.019 | 0.373 | 0.490 | 0.091 | 0.950 |
| mirror mixed-sign -15%, placebo none | specific | -4.30 | 0.928 | 0.101 | 0.928 | 0.062 | 0.921 | 0.007 | 0.501 | 0.491 | 0.099 | 0.955 |
| mirror uniform -15%, placebo reshuffle 10% | specific | -4.31 | 0.960 | 0.065 | 0.960 | 0.034 | 0.960 | 0.003 | 0.377 | 0.473 | 0.072 | 0.953 |
| mirror uniform -30%, placebo uniform -15% | specific | -8.62 | 1.000 | 0.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.588 | 0.503 | 0.109 | 0.949 |

The 105 tasks admitted under checker invariance, n_pl = 2:

| Scenario | kind | census true D (pp) | PRESENT_HARM | SMALL | P3 CONFIRMED | P3 FALSIFIED | sharp-null reject | PRESENT_FRAGILE | MIRROR_SPECIFIC (population) | MIRROR_SPECIFIC (census, reported) | NO_EXCESS | 95% coverage of census D |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| null (no effect) | null | 0.00 | 0.024 | 0.962 | 0.024 | 0.965 | 0.049 | 0.004 | 0.023 | 0.012 | 0.574 | 0.951 |
| task-specific perturbation N(0, 1), both cells | generic | 0.02 | 0.056 | 0.915 | 0.056 | 0.933 | 0.106 | 0.013 | 0.023 | 0.027 | 0.376 | 0.953 |
| reshuffle of 10% of tasks, both cells | generic | 0.07 | 0.113 | 0.808 | 0.113 | 0.873 | 0.204 | 0.038 | 0.020 | 0.062 | 0.076 | 0.953 |
| reshuffle of 30% of tasks, both cells | generic | 0.16 | 0.201 | 0.619 | 0.201 | 0.784 | 0.334 | 0.091 | 0.027 | 0.140 | 0.000 | 0.953 |
| uniform -15%, mirror and placebo alike | generic | -4.21 | 0.949 | 0.067 | 0.949 | 0.041 | 0.949 | 0.004 | 0.026 | 0.014 | 0.615 | 0.951 |
| complete breaks -15%, both alike | generic | -4.16 | 0.839 | 0.192 | 0.839 | 0.149 | 0.818 | 0.021 | 0.023 | 0.076 | 0.094 | 0.950 |
| mirror uniform -10%, placebo none | specific | -2.81 | 0.661 | 0.397 | 0.661 | 0.309 | 0.656 | 0.015 | 0.261 | 0.195 | 0.287 | 0.950 |
| mirror uniform -15%, placebo none | specific | -4.21 | 0.949 | 0.067 | 0.949 | 0.041 | 0.949 | 0.004 | 0.528 | 0.444 | 0.128 | 0.951 |
| mirror uniform -20%, placebo none | specific | -5.61 | 0.998 | 0.004 | 0.998 | 0.002 | 0.998 | 0.000 | 0.771 | 0.706 | 0.034 | 0.952 |
| mirror proportional -15%, placebo none | specific | -4.22 | 0.902 | 0.053 | 0.902 | 0.050 | 0.901 | 0.005 | 0.484 | 0.411 | 0.107 | 0.951 |
| mirror on a quarter of tasks -15%, placebo none | specific | -4.20 | 0.873 | 0.121 | 0.873 | 0.102 | 0.862 | 0.013 | 0.404 | 0.437 | 0.094 | 0.950 |
| mirror complete breaks -15%, placebo none | specific | -4.16 | 0.833 | 0.189 | 0.833 | 0.151 | 0.812 | 0.021 | 0.343 | 0.447 | 0.093 | 0.947 |
| mirror mixed-sign -15%, placebo none | specific | -4.19 | 0.911 | 0.115 | 0.911 | 0.077 | 0.903 | 0.010 | 0.459 | 0.442 | 0.106 | 0.948 |
| mirror uniform -15%, placebo reshuffle 10% | specific | -4.21 | 0.951 | 0.064 | 0.951 | 0.038 | 0.949 | 0.004 | 0.381 | 0.472 | 0.071 | 0.945 |
| mirror uniform -30%, placebo uniform -15% | specific | -8.41 | 1.000 | 0.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.557 | 0.478 | 0.125 | 0.946 |

Census of 106, n_pl = 4 (cap 7.57 GPU-h):

| Scenario | kind | census true D (pp) | PRESENT_HARM | SMALL | P3 CONFIRMED | P3 FALSIFIED | sharp-null reject | PRESENT_FRAGILE | MIRROR_SPECIFIC (population) | MIRROR_SPECIFIC (census, reported) | NO_EXCESS | 95% coverage of census D |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| null (no effect) | null | 0.00 | 0.025 | 0.970 | 0.025 | 0.971 | 0.048 | 0.005 | 0.023 | 0.022 | 0.822 | 0.950 |
| task-specific perturbation N(0, 1), both cells | generic | -0.02 | 0.058 | 0.927 | 0.058 | 0.935 | 0.102 | 0.013 | 0.027 | 0.061 | 0.564 | 0.947 |
| reshuffle of 10% of tasks, both cells | generic | 0.00 | 0.128 | 0.808 | 0.128 | 0.863 | 0.224 | 0.034 | 0.025 | 0.122 | 0.149 | 0.945 |
| reshuffle of 30% of tasks, both cells | generic | 0.01 | 0.222 | 0.626 | 0.222 | 0.769 | 0.342 | 0.095 | 0.024 | 0.212 | 0.000 | 0.946 |
| uniform -15%, mirror and placebo alike | generic | -4.31 | 0.957 | 0.065 | 0.957 | 0.037 | 0.956 | 0.003 | 0.026 | 0.027 | 0.848 | 0.951 |
| complete breaks -15%, both alike | generic | -4.29 | 0.854 | 0.187 | 0.854 | 0.137 | 0.833 | 0.022 | 0.026 | 0.141 | 0.166 | 0.944 |
| mirror uniform -10%, placebo none | specific | -2.88 | 0.698 | 0.386 | 0.698 | 0.279 | 0.696 | 0.011 | 0.388 | 0.408 | 0.376 | 0.952 |
| mirror uniform -15%, placebo none | specific | -4.31 | 0.957 | 0.065 | 0.957 | 0.037 | 0.956 | 0.003 | 0.721 | 0.744 | 0.126 | 0.951 |
| mirror uniform -20%, placebo none | specific | -5.75 | 0.998 | 0.004 | 0.998 | 0.001 | 0.998 | 0.000 | 0.925 | 0.938 | 0.026 | 0.951 |
| mirror proportional -15%, placebo none | specific | -4.31 | 0.917 | 0.053 | 0.917 | 0.048 | 0.914 | 0.006 | 0.630 | 0.664 | 0.114 | 0.954 |
| mirror on a quarter of tasks -15%, placebo none | specific | -4.31 | 0.876 | 0.128 | 0.876 | 0.103 | 0.865 | 0.012 | 0.531 | 0.678 | 0.108 | 0.950 |
| mirror complete breaks -15%, placebo none | specific | -4.29 | 0.849 | 0.192 | 0.849 | 0.141 | 0.831 | 0.019 | 0.452 | 0.689 | 0.115 | 0.946 |
| mirror mixed-sign -15%, placebo none | specific | -4.33 | 0.932 | 0.101 | 0.932 | 0.060 | 0.925 | 0.008 | 0.632 | 0.737 | 0.105 | 0.944 |
| mirror uniform -15%, placebo reshuffle 10% | specific | -4.31 | 0.961 | 0.063 | 0.961 | 0.032 | 0.961 | 0.003 | 0.482 | 0.693 | 0.083 | 0.955 |
| mirror uniform -30%, placebo uniform -15% | specific | -8.63 | 1.000 | 0.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.752 | 0.778 | 0.135 | 0.953 |

K_min = 62 (the confirm split), n_pl = 2:

| Scenario | kind | census true D (pp) | PRESENT_HARM | SMALL | P3 CONFIRMED | P3 FALSIFIED | sharp-null reject | PRESENT_FRAGILE | MIRROR_SPECIFIC (population) | MIRROR_SPECIFIC (census, reported) | NO_EXCESS | 95% coverage of census D |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| null (no effect) | null | 0.00 | 0.027 | 0.879 | 0.027 | 0.904 | 0.053 | 0.006 | 0.021 | 0.007 | 0.280 | 0.946 |
| task-specific perturbation N(0, 1), both cells | generic | 0.01 | 0.051 | 0.807 | 0.051 | 0.855 | 0.091 | 0.015 | 0.022 | 0.013 | 0.140 | 0.952 |
| reshuffle of 10% of tasks, both cells | generic | -0.03 | 0.125 | 0.635 | 0.125 | 0.751 | 0.205 | 0.039 | 0.025 | 0.059 | 0.014 | 0.949 |
| reshuffle of 30% of tasks, both cells | generic | -0.07 | 0.227 | 0.444 | 0.227 | 0.652 | 0.335 | 0.102 | 0.023 | 0.132 | 0.000 | 0.951 |
| uniform -15%, mirror and placebo alike | generic | -4.32 | 0.848 | 0.061 | 0.848 | 0.060 | 0.845 | 0.014 | 0.022 | 0.008 | 0.319 | 0.949 |
| complete breaks -15%, both alike | generic | -4.30 | 0.718 | 0.203 | 0.718 | 0.201 | 0.685 | 0.034 | 0.022 | 0.064 | 0.013 | 0.948 |
| mirror uniform -10%, placebo none | specific | -2.88 | 0.517 | 0.300 | 0.517 | 0.297 | 0.511 | 0.020 | 0.192 | 0.101 | 0.155 | 0.945 |
| mirror uniform -15%, placebo none | specific | -4.32 | 0.848 | 0.061 | 0.848 | 0.060 | 0.845 | 0.014 | 0.379 | 0.245 | 0.085 | 0.949 |
| mirror uniform -20%, placebo none | specific | -5.75 | 0.977 | 0.006 | 0.977 | 0.006 | 0.978 | 0.003 | 0.601 | 0.462 | 0.030 | 0.948 |
| mirror proportional -15%, placebo none | specific | -4.33 | 0.768 | 0.052 | 0.768 | 0.052 | 0.765 | 0.013 | 0.335 | 0.227 | 0.051 | 0.952 |
| mirror on a quarter of tasks -15%, placebo none | specific | -4.29 | 0.729 | 0.144 | 0.729 | 0.143 | 0.709 | 0.023 | 0.277 | 0.269 | 0.050 | 0.948 |
| mirror complete breaks -15%, placebo none | specific | -4.30 | 0.724 | 0.199 | 0.724 | 0.197 | 0.689 | 0.036 | 0.218 | 0.299 | 0.039 | 0.948 |
| mirror mixed-sign -15%, placebo none | specific | -4.31 | 0.809 | 0.103 | 0.809 | 0.102 | 0.797 | 0.017 | 0.336 | 0.256 | 0.068 | 0.949 |
| mirror uniform -15%, placebo reshuffle 10% | specific | -4.32 | 0.856 | 0.067 | 0.856 | 0.066 | 0.854 | 0.012 | 0.262 | 0.304 | 0.026 | 0.942 |
| mirror uniform -30%, placebo uniform -15% | specific | -8.63 | 1.000 | 0.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.404 | 0.264 | 0.092 | 0.951 |

- **Reading.** The corrected sharp-null test rejects in 0.048 of replicates at the exact null (v3's
  variance: 0.32), and PRESENT_FRAGILE fires in 0.006. Under every direction-free scenario, matched
  between mirror and placebo, MIRROR_SPECIFIC (population frame) fires in 0.023-0.027 of
  replicates, the nominal one-sided 2.5%, while the census-frame version would fire in up to 0.143
  under a 30% reshuffle: the population frame is what keeps a realized direction-free reaction from
  being named a mirror mechanism. P3's total-effect reading keeps v3's operating characteristics
  (SMALL 0.97 at the null; PRESENT_HARM 0.86-0.96 at a 15% relative harm; SMALL when the census truth
  lies beyond a margin at most 0.05). The direction-specific reading is a secondary, lower-powered
  question: with n_pl = 2, MIRROR_SPECIFIC at a mirror-only 15% harm is 0.37-0.56 across structures
  (0.80 at 20%); n_pl = 4 raises it to 0.45-0.72 (0.93 at 20%) at a 7.57 GPU-h cap. On the 105
  admitted tasks every rate is within 0.03 of the 106-task census.
- Every interval reports K, n and the number of valid episodes.

## Seeds

Simulation: [42, 43, 44]. Episode order, slot assignment and the sharp-null test: PCG64 seed 42.
vLLM request seed 42 (inert under greedy decoding; vLLM is not batch-invariant, so reruns are not
assumed identical: that is the rerun noise S1a measured). OSWorld tasks have one initial state each.

## Compute caps (D22 counting)

| Job | Cap (GPU-h) | Arithmetic |
|---|---:|---|
| Phase 0 (image build, P0.6, oracle, checker invariance, P0.10-P0.11) | 0 | CPU-only lane jobs, no GRES; about 44 VM-hours for P0.6 and about 1 container-hour for the oracle captures and the checker-invariance saves (the pilot's took 15.4 and 9.3 minutes on 16 workers) |
| Overlay build and pre-funded retry | 0.10 | 3 + 3 minutes, as S1a |
| Phase 1 (one job, K <= 106, n = 4 in the 2x2, n_pl = 2) | 6.73 | ceil(3 + 113.2/60 + (1,908 x 197.73/20 + 104.6) x 1.2 x 1.05 / 60) = 404 minutes |
| Registered total | 6.83 | below D20's 8 GPU-h line; 7.70 at the p95 slot price |

The gauntlet's reviewer budget (0.3 GPU-h) is separate. Under S1a's registered c_proj (0.011274
GPU-h per episode) the 1,908 episodes would be 21.5 GPU-h; the cap rule above is the Q2 design
study's (realized price x 1.2 x 1.05), a decision the program owner has to adopt.

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
   `power-v4.py` (v3's `power-v3.py` kept) with seeds and input hashes; pilot numbers from job records
   with receipts and the orx node's receipt.
4. Shortcut reliance: the agent may succeed from English document content; that is the registered
   estimand (application chrome over English documents), and the Arabic chrome share is reported.
5. Bug reframed as insight: a half-mirrored layout, a clipped status bar or a setup that diverges
   across cells could look like a treatment effect; O3, O5, O7 and O8 exist for that, and O8's
   defects are reported as part of the treatment. The pilot caught four defects of its own
   instrument before the sweep (registry labels needed `UILocale`, transformed shortcut tables broke
   Ctrl+S, dangling icon-theme symlinks, a paper-size change from a locale pin) and one in its oracle
   (VCL accessibility extents offset vertically under the container's window manager).
6. Methodology fabrication: the pool, estimands, decision rules, margins and cap are fixed here before
   any localized agent data. The Phase 0 admission and instrument rules were committed before the
   106-task sweep (`c8669d2`); the oracle's measurement code was completed on the dev smoke (1124)
   after the sweep had run and before any oracle output on it existed (first output: 1132); the
   checker-invariance operationalization of P0.8b and P0.9 was chosen after the committed proxy's
   result, and both verdicts are reported.
7. Frame-lock: the census frame is declared before data, the population frame is reported beside it
   with its own guard, and the infrastructure exit (K0, K1) is a first-class result.

## Owner's prior forecast (not a decision input)

Kevin permits the three downloads and the image surgery and lane change pass review: 0.6. With the
shipped catalogs, Phase 0 admits at least 62 tasks under checker invariance: 0.85 (the pilot admitted
105 with a stand-in catalog that translated more registry strings than the shipped one does); the
oracle's planted-control bar is met after a uniqueness test: 0.7. P0.6 passes on the five overlays:
0.85. Phase 1 reached overall, including an admission ruling: about 0.3. If it runs: D PRESENT_HARM
0.35, D SMALL 0.45, MIRROR_SPECIFIC given D PRESENT_HARM 0.4, T PRESENT_HARM 0.45, T SMALL 0.35.

## Freeze procedure

Phase 0 is built and its gate run in the lane (CPU only) after this draft and the P0.6 registration
are accepted and the downloads are permitted; a fresh agent's pre-freeze audit checks the
registration against the image, the oracle record and the code; then
`uv run python scripts/preregister.py freeze s2-arabic-cua-locale-v3 program/preregistrations/s2-arabic-cua-locale-v3.md`
and `verify`; then the admission ruling for Phase 1.

## Design decisions (for the owner's acceptance; v2's 31-53 are withdrawn with v2)

v3.1 adds 70-79 and amends 61 and 67:

70. The interface language set by both `ooLocale` and `UILocale`; `ooSetupSystemLocale` unpinned; no
    environment difference between cells.
71. The placebo cell PL (seeded toolbar-item order) at n_pl = 2, with the population-frame
    direction-specific reading; P3 read as a total effect (K9).
72. The corrected sharp-null variance (4v).
73. Intention-to-treat admission (A1-A4) with checker invariance through the gold and do-nothing
    controls; leaks and O5 changes reported, not excluded.
74. The oracle as implemented: ink-located boxes, tol3 from the dev tasks, O2 as whole-run identity,
    the VCL coordinate offset estimated on the dev tasks.
75. The tagged cell by LibreOffice's KeyID locale `qtz` plus generated registry tags.
76. Five cell overlays and a per-slot overlay field in the lane (new code, reviewed).
77. Moderators: chrome and document clicks separately, baseline success as a covariate, O8 per task.
78. Sensitivity analyses without the 43 `compare_pptx_files` tasks and on all 106 candidates.
79. A planted-control bar (or a uniqueness test for look-alike neighbours) fixed before Phase 0
    proper runs.

54. The census of OSWorld's LibreOffice single-application tasks (106) under rules E1-E5, C1, F1.
55. Dev tasks as Phase 0's development set and members of the census.
56. Census frame primary, population frame reported.
57. Dual margin (5 pp absolute; ratio inside (0.85, 1/0.85)).
58. n = 4 per task-cell, both harnesses, one session.
59. Layout by the finalized `UIMirroring` key in both directions; `SAL_RTL_ENABLED` never set.
60. Coupling remedies only where O2 finds a leak on the dev tasks; content strings never wrapped.
61. SheetPrefix, CTLFont and English function names pinned in every derived cell (amended in v3.1).
62. P0.6 extended with A2, A6 and a V = 20 rung.
63. O7 (window title) and O8 (RTL-defect inventory) added to the oracle.
64. The tagged pseudo-catalog cell (P0.8).
65. K_min = 62; re-queue of infrastructure and step-0 failures, at most twice.
66. K4 and K5 as stops on the English cell.
67. The cap rule (realized price x 1.2 x 1.05 at the high slot); 6.83 GPU-h registered (amended in v3.1 for PL).
68. Moderators from S1a's click coordinates and O8.
69. The derived image built offline by `dpkg-deb -x` and `debugfs -w`, after Kevin permits the three
    downloads.
