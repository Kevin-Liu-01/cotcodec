# S2 v2: Arabic interface text versus mirrored layout on Q2's certified OSWorld stack, Phase 0 localized image and render gate, Phase 1 2x2 (s2-arabic-cua-locale-v2)

Status: DRAFT. Not frozen, not admitted, no ledger row. Written on 2026-10-10 (UTC
2026-10-11) by the single owner of the S2 repair under program decision D68, on branch
`gauntlet/s2-locale`, as a new versioned attempt (gauntlet rule 3): the wave-1 draft
`s2-arabic-cua-locale-v1.md` (sha256 `866f994d...`, Relay) is left as it was and is superseded
by this file. Wave 1 scored 49 (reviews 58 and 49) and all three refuters refuted
(`program/gauntlet/2026-10-10-s2-arabic-cua-locale.jsonl`). D68 ordered one repair: move the
study onto Q2's certified OSWorld stack (applications with Arabic interfaces, the D53 action
path, S1a's measured noise floor) and make the fixture vary text direction and layout direction
separately. This draft registers S2's first step: Phase 0 (no GPU: a localized image, its
render gate and a delta certification of the action path) and Phase 1 (a 2x2 on the admitted
tasks). Its registered caps sum to at most 7.98 GPU-h, below D20's 8 GPU-h line. D68's
structural note still holds: nothing here runs without Kevin's admission ruling or D24's trust
store, and no host job of any kind runs during the gauntlet except the reviewer's lane job. The
proposal that argues and attacks this design is
`program/proposals/2026-10-10-s2-arabic-cua-locale.md`; its evidence bundle is
`program/proposals/evidence/2026-10-10-s2-arabic-cua-locale/`, with this repair's checks under
`compute/repair-d68/`. Every number labelled "simulated" comes from
`compute/repair-d68/power-osworld.py` (seeds 42, 43, 44) and rests on S1a's measured per-task
records through a fitted and checked propensity model; nothing in it is a localized-cell
measurement.

## Relation to v1 and to the dossier

| v1 (Relay) | v2 (OSWorld) | Why |
|---|---|---|
| Relay, 18 synthetic tasks, a local-engine transport and agent adapter to build (E1-E6) | S1a's OSWorld stack as run: Qwen3.5-9B, the two certified harnesses, the L0-fixed VM lane at V = 20, the S1a cost card | Relay's tasks could not power Phase 1 (frontier models completed 0 of 12 Relay pixel workflows; the v1 gate passed with probability 0.000-0.039 in simulation); S1a measured English base rates, rerun noise and cost on these tasks |
| In-project Arabic catalog, native-speaker review | The applications' own shipped Arabic translations | No in-project translation; the native-speaker precondition goes |
| Stage 1a English pilot (2.0 GPU-h) and a data-driven gate | No pilot: S1a's 8 English episodes per task (both harnesses) select the tasks and anchor the power analysis | The pilot measured what S1a already measured |
| `dir="auto"` on Relay content only; G8 on content nodes | Catalog-level directional isolation in all four cells; render oracle O2 on every text run; positive controls | v1's off-diagonal cells leaked bidi artefacts into D and T (identification refuter) |
| Gates run on the Mac at seeds 42-44 (aurora fixture never gated); K3 references absent | The oracle runs in the measurement lane on the derived image at every candidate task's post-setup state (OSWorld tasks have one initial state each) | v1's manipulation checks never touched the analysed units |
| G3 against P0.2 (server code had to change) | No application or checker code is edited; switches live in system or share layers | v1's gate could not pass without reinterpretation |
| Mechanism named when a one-sided falsifier did not fire | A moderator names a mechanism only if its 95% interval excludes 0 in the predicted direction | Reviewer 1, identification refuter |

The dossier entry `S2-aligned-locale-language` (`program/evidence/2026-10-06/question-dossier.md`,
section 5) keeps: chrome strings localized with content and checker strings English; the
locale as a fixture parameter; an oracle gate before any GPU; a power gate tied to the Q2
noise floor (here computed before data from S1a's records, below); the kill lines (oracle
fails, MDE above about 5 pp with no route to more tasks, English success outside 15-85%, both
effects small). Its "WS1 Relay noise-floor run" is replaced by S1a's measured floor.

## Question

On Q2's certified OSWorld stack, with task instructions, documents, checkers, the system shell,
number formats and the keyboard held fixed, and each application's interface text language
(English, Arabic) and layout direction (left-to-right, mirrored) switched separately in a 2x2,
how large are (D) the main effect of mirroring the application layout and (T) the main effect
of Arabic interface text on the screenshot success of Qwen3.5-9B, with tasks as the random
factor and S1a's measured rerun noise as the floor?

Claim scope: `portability-protocol`, a measurement on one frozen model, two certified
scaffolds and the admitted applications (LibreOffice Calc, Impress and Writer, and
Thunderbird and GIMP if admitted). It covers application-level localization (the
application's own interface strings and layout) over English documents and an English system
shell, not full operating-system localization, instruction language, reasoning language,
other models or training.

## Identity

- Experiment id: `s2-arabic-cua-locale-v2`. Code of record: the freeze commit on
  `gauntlet/s2-locale` or its successor.
- Model: Qwen3.5-9B, revision `c202236235762e1c871ad0ccb60c8ee5ba337b9a` (receipt
  `0a9e052d`, the weights S1a used). Greedy decoding, thinking on, 2,048 output tokens per
  step, 15 steps, screenshot only, the matched 60 s and 20 s settles: S1a's configuration.
- Harnesses: H-OSW-fixed (OSWorld `bfd62bdc` qwen35vl with its own-spec fixes) and H-GA
  (gym-anything `aae6f7607` qwen35vl), unchanged from `q2-stage1-rescoped-v1`; their prompts do
  not mention the interface language.
- Engine: vLLM v0.31.0 (commit `db9527a4`) on
  `docker.io/vllm/vllm-openai@sha256:b18abb2df97b8f798e81862bd93f872ea18613372e2c3adc0cc2ac21e66ac12f`
  with the cu129 overlay rebuilt from the freeze commit, as in S1a.
- VM lane: S1a's L0-fixed lane on the H100 host, V = 20 concurrent VMs, offline VMs, the OSWorld
  task configs and checkers at `b138d348` as S1a ran them.
- Image: a derived image built in Phase 0 from the certified OSWorld image; its digest and
  package list are recorded before the Phase 1 freeze.

## Tasks

The 43 candidates, selected on S1a's English records only (P0.1). Successes are of S1a's 8
Qwen3.5-9B episodes per task (2 harnesses x 2 sessions x 2 reruns). "Conditional" tasks read
an application configuration file in their checker and enter only if P0.9 passes.

| App | Task | 9B successes of 8 (H-OSW-fixed, H-GA) | 4B of 8 | Class | Checker reads |
|---|---|---|---|---|---|
| Calc | `0bf05a7d-b28b-44d2-955a-50b41e24012a` | 7 (4, 3) | 3 | strict | Customers_New_7digit_Id-Sheet1.csv, Customers_New_7digit_Id.xlsx |
| Calc | `1334ca3e-f9e3-4db8-9ca7-b4c653be7d17` | 5 (2, 3) | 5 | strict | Zoom_Out_Oversized_Cells.xlsx |
| Calc | `1e8df695-bd1b-45b3-b557-e7d599cf7597` | 8 (4, 4) | 4 | strict | WeeklySales.xlsx |
| Calc | `4188d3a4-077d-46b7-9c86-23e1a036f6c1` | 7 (3, 4) | 0 | strict | Freeze_row_column.xlsx |
| Calc | `42e0a640-4f19-4b28-973d-729602b5a4a7` | 5 (2, 3) | 3 | strict | NetIncome.xlsx |
| Calc | `51b11269-2ca8-4b2a-9163-f21758420e78` | 5 (3, 2) | 8 | strict | Arrang_Value_min_to_max.xlsx |
| Calc | `7e429b8d-a3f0-4ed0-9b58-08957d00b127` | 3 (2, 1) | 0 | strict | VLOOKUP_Fill_the_form.xlsx |
| Calc | `a9f325aa-8c05-4e4f-8341-9e4358565f4f` | 4 (0, 4) | 0 | strict | Movie_title_garbage_clean.xlsx |
| Calc | `aa3a8974-2e85-438b-b29e-a64df44deb4b` | 4 (3, 1) | 1 | strict | Resize_Cells_Fit_Page.pdf |
| Calc | `ecb0df7a-4e8d-4a03-b162-053391d3afaf` | 1 (1, 0) | 2 | strict | Order_Id_Mark_Pass_Fail.xlsx |
| Impress | `08aced46-45a2-48d7-993b-ed3fb5b32302` | 7 (3, 4) | 8 | strict | 22_6.pptx |
| Impress | `0f84bef9-9790-432e-92b7-eece357603fb` | 4 (0, 4) | 6 | conditional | registrymodifications.xcu |
| Impress | `2cd43775-7085-45d8-89fa-9e35c0a915cf` | 8 (4, 4) | 8 | conditional | registrymodifications.xcu |
| Impress | `5c1a6c3d-c1b3-47cb-9b01-8d1b7544ffa1` | 1 (0, 1) | 0 | strict | 39_2.pptx |
| Impress | `70bca0cc-c117-427e-b0be-4df7299ebeb6` | 7 (4, 3) | 7 | strict, S1a-flagged | 71_6.pptx |
| Impress | `73c99fb9-f828-43ce-b87a-01dc07faa224` | 8 (4, 4) | 8 | strict | 109_4.pptx |
| Impress | `9cf05d24-6bd9-4dae-8967-f67d88f5d38a` | 7 (3, 4) | 7 | strict | 214_9.pptx |
| Impress | `9ec204e4-f0a3-42f8-8458-b772a6797cab` | 1 (1, 0) | 0 | strict, S1a-flagged | MLA_Workshop_061X_Works_Cited.pptx |
| Impress | `af2d657a-e6b3-4c6a-9f67-9e3ed015974c` | 1 (1, 0) | 6 | strict | 9_1.pptx |
| Impress | `c59742c0-4323-4b9d-8a02-723c251deaa0` | 8 (4, 4) | 8 | strict | Baseball.mp3, Mady_and_Mia_Baseball.pptx |
| Impress | `edb61b14-a854-4bf5-a075-c8075c11293a` | 1 (1, 0) | 2 | strict | 24_8.pptx |
| Writer | `0810415c-bde4-4443-9047-d5f70165a697` | 2 (2, 0) | 1 | strict | Novels_Intro_Packet.docx |
| Writer | `3ef2b351-8a84-4ff2-8724-d86eae9b842e` | 8 (4, 4) | 8 | strict | Constitution_Template_With_Guidelines.docx |
| Writer | `66399b0d-8fda-4618-95c4-bfc6191617e9` | 8 (4, 4) | 8 | strict | Table_Of_Work_Effort_Instructions.docx |
| Writer | `6ada715d-3aae-4a32-a6a7-429b2e43fb93` | 4 (0, 4) | 8 | strict | Viewing_Your_Class_Schedule_and_Textbooks.docx |
| Writer | `72b810ef-4156-4d09-8f08-a0cf57e7cefe` | 2 (1, 1) | 2 | strict | GEOG2169_Course_Outline_2022-23.docx |
| Writer | `d53ff5ee-3b1a-431e-b2be-30ed2673079b` | 8 (4, 4) | 7 | strict, S1a-flagged | presentation_instruction_2023_Feb.docx |
| Writer | `ecc2413d-8a48-416e-a3a2-d30106ca36cb` | 8 (4, 4) | 8 | strict | Sample_Statutory_Declaration.docx |
| Writer | `f178a4a9-d090-4b56-bc4c-4b72a61a035d` | 1 (0, 1) | 0 | conditional | registrymodifications.xcu |
| Thunderbird | `10a730d5-d414-4b40-b479-684bed1ae522` | 8 (4, 4) | 6 | conditional | prefs.js |
| Thunderbird | `3f49d2cc-f400-4e7d-90cc-9b18e401cc31` | 5 (4, 1) | 2 | conditional | xulstore.json |
| Thunderbird | `5203d847-2572-4150-912a-03f062254390` | 7 (3, 4) | 8 | strict | msgFilterRules.dat |
| Thunderbird | `9b7bc335-06b5-4cd3-9119-1a649c478509` | 8 (4, 4) | 1 | strict | msgFilterRules.dat |
| Thunderbird | `9bc3cc16-074a-45ac-9bdc-b2a362e1daf3` | 7 (4, 3) | 0 | strict | a cache file |
| Thunderbird | `d38192b0-17dc-4e1d-99c3-786d0117de77` | 8 (4, 4) | 8 | strict | a cache file |
| Thunderbird | `dfac9ee8-9bc4-4cdc-b465-4a4bfcd2f397` | 8 (4, 4) | 8 | strict | a cache file |
| GIMP | `06ca5602-62ca-47f6-ad4f-da151cde54cc` | 8 (4, 4) | 8 | strict | palette_computer.png |
| GIMP | `554785e9-4523-4e7a-b8e1-8016f565f56a` | 8 (4, 4) | 6 | strict | edited_colorful.png |
| GIMP | `77b8ab4d-994f-43ac-8930-8ca087d7c4b4` | 8 (4, 4) | 7 | strict | export.jpg |
| GIMP | `7a4deb26-d57d-4ea9-9a73-630f66a7b568` | 2 (1, 1) | 4 | strict | edited_darker.png |
| GIMP | `7b7617bd-57cc-468e-9c91-40c4ec2bcb3d` | 8 (4, 4) | 8 | conditional | gimprc |
| GIMP | `b148e375-fe0b-4bec-90e7-38632b0d73c2` | 8 (4, 4) | 8 | conditional | gimprc |
| GIMP | `e2dd0213-26db-4349-abe5-d5667bfd725c` | 4 (4, 0) | 3 | strict | leftside_textbox.png |

Task sets used in the power analysis: LibreOffice strict (26 tasks), LibreOffice and
Thunderbird strict (31), LibreOffice and Thunderbird with the conditional tasks (36), all 43.

## Phase 0: the localized image and its gate (no GPU; host CPU lane jobs)

Phase 0 builds one derived VM image from the certified OSWorld image, adds four cell
selectors, and admits an application to Phase 1 only if every item below passes for it. Every
host job of Phase 0 is a CPU-only lane job (no GRES), submitted only when the queue is empty,
and none runs before this registration is accepted (D67's host rule binds this gauntlet run;
nothing in Phase 0 runs in it).

- **P0.1 Task list (done here, frozen).** The 43 candidate tasks in the table under
  "Tasks" were selected on S1a's English records only, by the registered screen in
  `compute/repair-d68/power-osworld.py` (`task_screen`, `task_sets`): applications with a
  shipped Arabic interface whose layout direction can be switched separately (LibreOffice
  Calc, Impress, Writer; Thunderbird; GIMP); informative if Qwen3.5-9B succeeded in at least
  1 of its 8 S1a episodes; tasks whose setup clicks at screen coordinates are excluded
  (`550ce7e7`, `a669ef01`; a mirrored layout would send the click elsewhere); tasks whose
  checker reads an application configuration file are conditional (P0.9). VLC (coordinate
  setup clicks in 5 of 6 tasks; Qt direction switch unverified), VS Code (no Arabic interface
  support established in this run) and multi-application tasks are out.
- **P0.2 Derived image.** From the certified image (its digest recorded in S1a's lane
  receipts), offline: the LibreOffice Arabic language pack matching the installed
  LibreOffice version, Thunderbird's Arabic language pack, GIMP's Arabic catalogs (if not
  already installed), and an Arabic-covering font pinned by package version (Noto Sans Arabic
  or the distribution's default Arabic font; the one actually used is recorded with
  `fc-match`). The X keyboard map stays `us` and no input method runs in any cell (checked by
  `setxkbmap -query` and the IBus state at every episode start in Phase 1). The image digest
  is recorded; packages come from public downloads (D1) with their SHA-256.
- **P0.3 Text and layout switches.** Text: the interface language of the application process
  (LibreOffice: the share-layer key `org.openoffice.Setup/L10N/ooLocale`, finalized, `en-US` or
  `ar`, which selects the catalogs under `program/resource`; GTK applications and GTK's own
  strings: the process's `LANGUAGE`; Thunderbird: its requested locale), never the system
  locale. Layout (one switch per application; nothing else differs between the two layout
  levels of a text level):
  - LibreOffice: `AllSettings::GetLayoutRTL()` decides mirroring
    (`vcl/source/app/settings.cxx` 2633-2669): the environment variable `SAL_RTL_ENABLED`
    forces RTL (en-RTL), and the configuration key
    `org.openoffice.Office.Common/I18N/CTL/UIMirroring` = false keeps an Arabic interface
    left-to-right (ar-LTR). The key is set in a share-layer configuration file with
    `oor:finalized="true"`, never in the user profile's `registrymodifications.xcu`, which
    three candidate checkers read.
  - GTK applications (GIMP; LibreOffice's GTK dialogs follow LibreOffice's own setting,
    `vcl/unx/gtk3/gtkinst.cxx` 4887): GTK takes the default direction from the translation of
    the string `default:LTR` in its own catalog (`gtk/gtkmain.c` 1269-1282 in GTK 3.24.33;
    750-759 in GTK 2.24.33). en-RTL is a pseudo-locale (`en@rtl`) whose GTK catalog holds only
    that entry, translated `default:RTL`; ar-LTR is a pseudo-locale (`ar@ltr`) whose
    catalogs are byte copies of the Arabic ones except that entry, left as `default:LTR`.
  - Thunderbird (Gecko): the interface direction follows the application locale, or the
    `bidi`/`accented` pseudo-locales (`intl/locale/LocaleService.cpp`, `IsAppLocaleRTL`, in
    current Gecko source); an `intl.uidirection` override does not appear there (the installed
    Thunderbird's version and behaviour are checked in Phase 0). en-RTL and ar-LTR therefore need
    pseudo-locale language packs (English strings under an RTL locale tag; Arabic strings under
    an LTR tag). Whether the installed Thunderbird accepts such packs (signature policy) is
    unverified; Thunderbird enters Phase 1 only if they load and its cells pass the gate.
  - The selector is one file in the image that a launcher wrapper reads before starting the
    application; the four cell overlays differ only in that file (checked byte for byte).
    Task setup steps are not edited.
- **P0.4 Text-direction isolation (the identification repair).** Toolkits tie the paragraph
  direction of interface strings to the layout: when LibreOffice's interface is mirrored, every
  output device starts with the `BiDiRtl` text layout mode (`vcl/source/outdev/outdev.cxx`
  87-88) and VCL runs ICU's bidi algorithm with an explicit paragraph level of 1
  (`vcl/source/text/ImplLayoutArgs.cxx` 56-66), so an English string in en-RTL and an Arabic
  string in ar-LTR would be reordered (a trailing ellipsis or a Latin product name moves).
  The repair: in all four cells every catalog string (LibreOffice's gettext catalogs under
  `program/resource`, which are loaded for every interface language including en-US,
  `unotools/source/i18n/resmgr.cxx` 112-145 and 198-213; GTK and GIMP catalogs; Thunderbird's
  Fluent messages) is wrapped in FIRST STRONG ISOLATE ... POP DIRECTIONAL ISOLATE (U+2068 ...
  U+2069; UAX #9, rule X5c). Inside an isolate the bidi algorithm takes the direction from the
  string's first strong character whatever the surrounding paragraph level, so each string
  keeps its natural internal order in both layout levels. The wrapped catalogs are identical
  between the two layout levels of a text level; the English cells use wrapped English
  catalogs, so the en cell differs from S1a's stock English only by invisible isolate
  controls (O6 checks that this changes no pixel). Strings composed in code from several
  catalog strings, literals and numbers can still leak; O2 finds them.
- **P0.5 Held fixed in every cell (declared, not part of the treatment).** Task instructions,
  documents and checker inputs (English, left-to-right); the system shell (English, LTR; only
  the application processes get the cell's language and direction); the locale for numbers,
  dates and the document default language (`en-US`); LibreOffice's complex-text-layout
  support (`CTLFont`) at one pinned value; Calc's English function names
  (`EnglishFunctionName` = true); autocorrect and spelling languages; the keyboard map;
  screen resolution; the agent, decoding, step cap and settles.
- **P0.6 Delta certification of the action path.** D53's verdict does not cover another
  image. The frozen acceptance suite of `q2-action-path-v2` (executor and catalog unchanged)
  runs on the derived image with each of the four cell selectors: C1-C4, A1 at N = 1, A5 and
  the keyboard-map check; pass lines as D53's. Volume (A4) and the accessibility service (A7)
  are not re-run: Phase 1 reads screenshots only and runs at V = 20, inside D53's N* = 32, and
  S1a's 0 losses in 1,808 episodes are on the base image. This needs a registered deviation
  of `q2-action-path-v2` or its own short registration, written before Phase 0 runs.
- **P0.7 Factorial render oracle (O1-O6).** Code: `compute/repair-d68/render-oracle/oracle.py`.
  Inputs per cell and state: the screenshot and the accessibility tree (element path, role,
  name, screen box), captured in the measurement lane on the derived image (never on the
  development Mac). States: every candidate task's post-setup state, and a sweep per
  application (each top-level menu opened on the first task's post-setup state, and the
  dialogs named by a keyword map from the candidate instructions, frozen before Phase 0
  runs). Checks:
  - O1 structure: the (path, role) list is identical in the four cells;
  - O2 text runs: every text-bearing element's ink is the same image in the two layout levels
    of the same text level (en against en-RTL, ar-LTR against ar-RTL), at a mismatch
    tolerance fixed from an A/A run first (the same cell rendered twice and at a subpixel
    shift; tolerance = max(0.02, 2 x the worst A/A mismatch));
  - O3 mirror fidelity: every widget box in the RTL cell is the horizontal reflection of its
    LTR box inside the application window (tolerance 2 px), with each exception named in a
    mirror specification frozen with Phase 0 (icons and controls that platform guidelines do
    not mirror);
  - O4 order under text swap: siblings keep their vertical order and, within a row, their
    horizontal order between en and ar-LTR and between en-RTL and ar-RTL;
  - O5 content identity: the document region (from the tree's document frame) is
    pixel-identical in the four cells at every post-setup state (setup reached the same state;
    content is not treated);
  - O6 isolation is invisible where it should be: the en cell's screenshots equal S1a's stock
    English image's at the same post-setup states, after the clock and caret masks.
  Positive controls, required before the oracle's verdict counts: in each application, the
  unwrapped (coupled) catalogs in the off-diagonal cells must be flagged by O2 on at least one
  run of the sweep, and a planted leak string in each application must be flagged; a
  half-mirrored planted widget must fail O3. Validation on fixtures with known properties
  (this run, `render-oracle/oracle-validation.json`): all 7 variants gave their expected
  verdicts; coupled strings leaked in 7 of 38 run pairs and FSI/PDI isolation removed all 7;
  a code-composed field still leaked under isolation and was flagged.
- **P0.8 Functional A/A across cells.** Registered keyboard-driven probe scripts in each
  application (open a candidate document, type a value and a formula with an English
  function name, apply a format, save in the original format keeping the format, export where
  a candidate task exports) run in all four cells; the saved files must be byte-identical
  after removing metadata timestamps, or checker-equal under each candidate checker.
- **P0.9 Config invariance (conditional tasks).** For the seven tasks whose checker reads
  `registrymodifications.xcu`, `prefs.js`, `xulstore.json` or `gimprc`: after a fixed
  probe session (launch, idle 60 s, quit through the menu by keyboard) the keys that differ
  between cells must not include any key the task's checker reads, and the checker's verdict
  on the post-setup state must be identical across cells. A task that fails is dropped.
- **P0.10 Moderator coding, frozen before any GPU job.** From the en and en-RTL trees at
  each task's post-setup state: (a) the share of interactive elements whose centre changes
  screen half under mirroring; (b) lexical overlap, the number of distinct English interface
  labels visible at the post-setup state whose lowercased tokens appear in the instruction.
- **P0.11 Arabic chrome share.** Per application and state: the share of visible interface
  strings (from the tree) rendered in Arabic script in the ar cells. Reported; untranslated
  strings stay English in the ar cells (a weaker text treatment, the same in both layout
  levels).

Phase 0 admission: an application enters Phase 1 if P0.6, O1-O6 with the positive controls,
P0.8 and its tasks' P0.9 pass, with zero residual O2 leaks over its sweep. A residual leak
can be removed only by a held-fixed configuration change applied identically to all four
cells (for example hiding a status-bar field), recorded, followed by a full rerun; thresholds
never change. Phase 1 runs only if the admitted tasks number at least K_min = 26 (the
LibreOffice-only strict set), otherwise infrastructure exit.

## What the D53 certification covers for localized applications, and what it does not

D53 accepted `q2-action-path-v2` on attempt 1. In its own words, the verdict "covers the
L0-fixed runtime and the two Stage-1 harness adapters on this host as configured, at no more
than 32 concurrent VMs. It does not cover more VMs, another host, image or kernel setting,
untested catalog instances, or the guest server under Stage-1 task applications"
(`program/decisions.md`, D53; evidence `program/evidence/2026-10-08/q2-action-path-v2-acceptance/`).
Read against S2's localized cells:

| Element S2 needs | Covered by D53? | Why, and what S2 adds |
|---|---|---|
| Action delivery at screen coordinates (left click, other click, move, drag, scroll) | Yes in mechanism, not on the derived image | The executor sends X events at coordinates and is application-agnostic; A4 bounded each class at 5 x 10^-4 per action (family-wise 95%, 64,028 trials, 0 failures) on the certified image. A mirrored layout changes where targets are, not how a click is delivered. The derived image is "another image", so P0.6 reruns C1-C4, A1 (N = 1) and A5 on it with each cell selector |
| Typing and key chords | Only under the certified keyboard map | `type` and key actions go through the X keymap; an Arabic locale that switched the layout or started an input method would turn English keystrokes into Arabic characters or swallow chords. S2 holds the map at `us` with no input method and checks it at every episode start; the 33 certified keysyms are re-exercised in P0.6. No Arabic text is ever typed (instructions and content are English) |
| Screenshot observation | Yes (S1a: 24,218 screenshots, none retried or lost) | Unchanged; S2 reads screenshots only. The accessibility service (A7) is used only by Phase 0's oracle, outside episodes, where a failed call is retried and never affects an agent |
| Boot reset (A5) | On the certified image | Rerun on the derived image in P0.6 |
| Concurrency | Up to N* = 32 | Phase 1 runs at V = 20, S1a's measured setting |
| The two harness adapters (H-OSW-fixed, H-GA) | Yes | Unchanged, including their prompts: the agent is not told the interface language |
| The guest server under the task applications | No (excluded by D53) | S1a measured it in English on these tasks (0 infrastructure losses, 0 restarts, 0 postconfig server errors in 1,808 episodes). In Arabic and mirrored cells it is unmeasured; Phase 1 counts losses per cell and stops at 5% in any cell (K2) |
| What the application draws (localized rendering, mirroring, bidi) | No: D53 certifies delivery of actions and observations, not their content | Phase 0's render oracle (O1-O6) is the certification of the treatment itself |
| Checkers | Not part of D53 | The candidate checkers read saved documents and, for seven conditional tasks, configuration files; S2 never writes the latter (P0.3) and tests their invariance (P0.9) |

So the certified stack carries over as runtime, harness adapters, lane, concurrency and
cost card; the localized image and everything it draws must be certified anew, by P0.6
(actions) and P0.7-P0.9 (treatment and checkers), before any GPU job.

## Phase 1: the 2x2 (only after Phase 0 admits at least 26 tasks and an admission ruling)

- Tasks: the admitted tasks, K of them (26 to 43). Cells: en (English, LTR), ar-LTR, en-RTL,
  ar-RTL.
- Episodes: n per (task, cell), split equally between the two harnesses: n = 16 (8 per
  harness) if K <= 35, n = 12 (6 per harness) if K >= 36. Total 4 K n episodes (1,664 at
  K = 26; 2,064 at K = 43).
- Order: one serving session (one GPU job and its VM job, S1a's lane pair). Task blocks in a
  seeded random order (PCG64 seed 42); within a block the 4n episodes (cell x harness x rerun)
  in a seeded random interleave. A cap stop therefore leaves complete task blocks. S1a's 9B
  session shift (+5.5 pp, p 0.016) is why all cells of a task share a session.
- Step-0 check: each episode's first screenshot, after the clock and caret masks, is compared
  with the Phase 0 reference for its (task, cell), recorded in the same lane on the same
  image; the tolerance is set from Phase 0's A/A. A mismatch makes the episode invalid.
- Keyboard check: `setxkbmap -query` reports `us` and no input method runs, at every episode
  start; a failure is an infrastructure loss.
- Cap: one job, ceil(3 + L/60 + (N x s / V + drain) x 1.2 x 1.05 / 60) minutes with
  L = 113.2 s, drain = 104.6 s, V = 20, N = 4 K n, and s = 197.7 s (the mean slot of S1a's
  9B episodes that ran to the 15-step cap on the candidate tasks: the high price, as if every
  episode ran to the cap), plus a 6-minute overlay build and retry reserve (the Q2 design
  study's rule, `stage0/q2-design-study` `79096f8`). 

  | K | n | episodes | physical GPU-h at the high slot | cap incl. overlay (GPU-h) |
  |---:|---:|---:|---:|---:|
  | 26 | 16 | 1664 | 4.63 | 5.983 |
  | 31 | 16 | 1984 | 5.509 | 7.083 |
  | 35 | 16 | 2240 | 6.212 | 7.983 |
  | 36 | 12 | 1728 | 4.806 | 6.2 |
  | 43 | 12 | 2064 | 5.729 | 7.367 |

  The largest cap over K = 26-43 is 7.98 GPU-h (K = 35, n = 16).

## Estimands

Cell means per task t over its n episodes (both harnesses pooled equally): y_en, y_arL,
y_enR, y_arR.

- **Primary, D (layout-direction main effect):** D = mean_t D_t,
  D_t = ((y_arR - y_arL) + (y_enR - y_en)) / 2.
- **Secondary, T (Arabic-interface-text main effect):** T = mean_t ((y_arL - y_en) +
  (y_arR - y_enR)) / 2. It changes language, script and the word overlap between English
  instructions and interface labels together; it is not a "glyph" effect.
- **Secondary:** the total Delta = mean_t (y_arR - y_en) = T + D exactly; the interaction
  I = mean_t ((y_arR - y_arL) - (y_enR - y_en)); the dossier's conditional contrasts
  M_ar = ar-RTL - ar-LTR and G = ar-LTR - en; D and T by harness and by application
  (descriptive); fractional checker scores in place of binary success (sensitivity).
- **Process:** steps, the share of episodes ending at the 15-step cap, invalid-action and
  truncation rates, by cell.
- **Moderators (secondary, task-level regressions with CR2 standard errors):** D_t on the
  share of interactive elements that change screen half under mirroring (P0.10a; predicted
  slope negative if the cost is positional); T_t on lexical overlap (P0.10b; predicted
  negative). A mechanism is named only if the moderator's 95% CR2 interval excludes 0 in the
  predicted direction; otherwise the mechanism is reported as unresolved.
- **Reference:** the en cell against S1a's 9B English success on the same tasks and harnesses
  (the image's effect on the English agent; descriptive).

## Decision rules (primary D; the same labels are reported for T)

- **PRESENT:** two-sided paired t on the K task-level D_t (df K - 1), p <= 0.05, labelled by
  sign (PRESENT_HARM or PRESENT_BENEFIT). The sign-flip test (exact enumeration if K <= 20,
  else 100,000 seeded sign vectors, seed 42) is reported; if it disagrees at 0.05 the label is
  PRESENT_FRAGILE.
- **SMALL:** the 90% t interval of D lies inside (-5, +5) pp (TOST at 0.05), and the
  rare-break bound does not reach 5 pp: with B tasks showing a large drop (D_t <= -0.25), U is
  the exact one-sided 95% upper bound on the share of such tasks (Clopper-Pearson), and
  U x (mean en-cell success) must be below 5 pp. Otherwise a SMALL interval is reported as
  SMALL_RARE_BREAKS_NOT_EXCLUDED: the mean on these tasks is small, but a 5 pp effect made of
  large drops in a few percent of tasks like these is not excluded. At K = 26-31 the bound stays
  at or above 5 pp even with B = 0, so an unqualified SMALL is impossible there; it becomes
  reachable from about K = 36 and realistic near K = 43. The simulation shows why: at a true -5 pp made of complete breaks, a small interval alone calls SMALL in up to 0.191 of replicates (the t interval covers the target in only 0.823-0.883), while the qualified rule's unqualified SMALL rate stays at or below 0.038.
- PRESENT and SMALL can hold together (PRESENT_AND_SMALL).
- **INCONCLUSIVE:** neither.
- Reported beside the label, not decision-bearing: the finite-task interval (the same
  estimate with the sampling variance of the K fixed tasks, for the claim "on these tasks"),
  and a stratified randomization test of the sharp null of no layout effect on any episode
  distribution (it detects any change in behaviour, including changes of mixed sign).

## Kill criteria

| Id | Trigger | Consequence |
|---|---|---|
| K0 | An application fails a Phase 0 item (P0.6-P0.9, O1-O6 with positive controls, zero residual O2 leaks after the remedy rule) | The application is dropped. Thresholds never change. If the admitted tasks number fewer than 26: infrastructure exit (no Phase 1); the localized image, the oracle record and the leak inventory are published |
| K1 | The delta certification (P0.6) fails | No Phase 1 on this image. A repair is a new image and a new P0.6 run |
| K2 | More than 5% of a cell's Phase 1 episodes are infrastructure losses | INCOMPLETE, no decision |
| K3 | More than 2% of a cell's episodes fail the step-0 check | INCOMPLETE, no decision |
| K4 | D and T both SMALL (unqualified) and neither PRESENT | Publish the robustness null for application-level chrome localization at this scale and drop the locale arm from WS3-R |
| K5 | Neither D nor T PRESENT | No reasoning-language arm |
| K6 | The Phase 1 cap is reached | Stop at the last complete task block; analyse if at least 26 tasks are complete, else INCOMPLETE |

## Predictions and falsifiers

| | Prediction | Falsifier |
|---|---|---|
| P1 | Phase 0 admits LibreOffice (Calc, Impress, Writer) | LibreOffice fails a Phase 0 item, including a residual O2 leak (K0) |
| P2 | The delta certification passes | K1 fires |
| P3 | D < 0 (mirroring hurts) | D is SMALL (unqualified) |
| P4 | T < 0 | T is SMALL (unqualified) |
| P5 | The T_t slope on lexical overlap is negative | its 95% CR2 interval lies above 0 (the mechanism is named only if the interval lies below 0) |
| P6 | The D_t slope on the screen-half share is negative | its 95% CR2 interval lies above 0 (named only if below 0) |
| P7 | The en cell's pooled success on the analysed tasks is within 10 pp of S1a's 9B English success on the same tasks | outside (the derived image changed the English agent; contrasts stay valid within the image, and the shift is reported) |

## Reported regardless of outcome

Phase 0: every gate item's result per application and cell; the leak inventory (every O2
leak, its widget and string, before and after isolation); the A/A tolerances; the positive
controls; the Arabic chrome share per screen; the functional A/A and config-invariance
results; the mirror specification; the moderator codings; the delta certification record;
CPU time. Phase 1 (if run): per-task successes in every cell and harness; D, T, I, Delta,
M_ar and G with 95% and 90% intervals; the sign-flip p; TOST; the rare-break bound; the
finite-task interval; the sharp-null test; process metrics; moderator slopes; the en-cell
reference against S1a; infrastructure losses and step-0 failures per cell; cost per cell.

## Statistics, sample sizes and simulation

- **Propensity model.** Beta-binomial over S1a's 154 candidate (task, harness) cells (4 trials
  each, zeros included), maximum marginal likelihood: a = 0.107, b = 0.167. Check
  against S1a: k-histogram [0.513, 0.0844, 0.0325, 0.0714, 0.2987] observed, [0.5202, 0.0682, 0.0515, 0.0614, 0.2987] modelled;
  pairwise rerun discordance 0.0996 observed, 0.0991
  modelled; mean success 0.3896 and 0.3876. Each selected
  cell's probability is drawn from its own posterior.
- **Simulated operating characteristics** (simulated; 3,000 replicates per cell over seeds 42, 43,
  44; one session with a common logit shift of SD 0.3; T = -5 pp; the sign-flip test with 2,000
  seeded sign vectors in simulation and 100,000 in the analysis). PRESENT (harm) at a true
  D = -5 pp by effect structure at the registered n, with the null rows:

| Task set (K, registered n) | uniform logit shift | proportional, all tasks | proportional, half the tasks | proportional, a quarter of the tasks | complete breaks | null: false PRESENT | null: SMALL (qualified + unqualified) | null: SMALL unqualified |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| LibreOffice strict (26, 16) | 0.89 | 0.79 | 0.65 | 0.44 | 0.09 | 0.047 / 0.043 | 0.90 / 0.26 | 0.00 / 0.00 |
| LO + Thunderbird strict (31, 16) | 0.93 | 0.86 | 0.75 | 0.55 | 0.12 | 0.049 / 0.045 | 0.96 / 0.42 | 0.00 / 0.00 |
| LO + Thunderbird incl. conditional (36, 12) | 0.93 | 0.84 | 0.74 | 0.58 | 0.17 | 0.053 / 0.040 | 0.94 / 0.49 | 0.12 / 0.02 |
| all 43 (43, 12) | 0.97 | 0.90 | 0.83 | 0.67 | 0.21 | 0.051 / 0.046 | 0.98 / 0.65 | 0.69 / 0.11 |

- **Power by n:**

| Task set | Structure | n = 8 (-5 pp) | n = 12 (-5 pp) | n = 16 (-5 pp) | n = 16 (-3 pp) | n = 16 (-8 pp) |
|---|---|---:|---:|---:|---:|---:|
| LibreOffice strict (26) | uniform logit shift | 0.60 | 0.77 | 0.89 | 0.48 | 1.00 |
| LibreOffice strict (26) | proportional, all tasks | 0.49 | 0.67 | 0.79 | 0.42 | 0.98 |
| LibreOffice strict (26) | proportional, half the tasks | 0.43 | 0.57 | 0.65 | 0.37 | 0.87 |
| LibreOffice strict (26) | proportional, a quarter of the tasks | 0.32 | 0.41 | 0.44 | 0.29 | 0.58 |
| LibreOffice strict (26) | complete breaks | 0.10 | 0.09 | 0.09 | 0.04 | 0.26 |
| LO + Thunderbird strict (31) | uniform logit shift | 0.72 | 0.87 | 0.93 | 0.56 | 1.00 |
| LO + Thunderbird strict (31) | proportional, all tasks | 0.60 | 0.76 | 0.86 | 0.48 | 0.99 |
| LO + Thunderbird strict (31) | proportional, half the tasks | 0.53 | 0.66 | 0.75 | 0.44 | 0.93 |
| LO + Thunderbird strict (31) | proportional, a quarter of the tasks | 0.43 | 0.49 | 0.55 | 0.36 | 0.70 |
| LO + Thunderbird strict (31) | complete breaks | 0.12 | 0.12 | 0.12 | 0.05 | 0.31 |
| LO + Thunderbird incl. conditional (36) | uniform logit shift | 0.80 | 0.93 | 0.97 | 0.66 | 1.00 |
| LO + Thunderbird incl. conditional (36) | proportional, all tasks | 0.69 | 0.84 | 0.92 | 0.56 | 1.00 |
| LO + Thunderbird incl. conditional (36) | proportional, half the tasks | 0.61 | 0.74 | 0.82 | 0.50 | 0.97 |
| LO + Thunderbird incl. conditional (36) | proportional, a quarter of the tasks | 0.50 | 0.58 | 0.62 | 0.41 | 0.79 |
| LO + Thunderbird incl. conditional (36) | complete breaks | 0.16 | 0.17 | 0.16 | 0.06 | 0.40 |
| all 43 (43) | uniform logit shift | 0.87 | 0.97 | 0.99 | 0.76 | 1.00 |
| all 43 (43) | proportional, all tasks | 0.77 | 0.90 | 0.96 | 0.66 | 1.00 |
| all 43 (43) | proportional, half the tasks | 0.70 | 0.83 | 0.90 | 0.60 | 0.99 |
| all 43 (43) | proportional, a quarter of the tasks | 0.58 | 0.67 | 0.75 | 0.51 | 0.89 |
| all 43 (43) | complete breaks | 0.20 | 0.21 | 0.22 | 0.08 | 0.54 |

- **Equivalence errors and coverage at the registered n (true D = -5 pp):**

| Task set (K, n) | Structure | SMALL at a true -5 pp (any) | SMALL unqualified at -5 pp | 95% coverage of the target | mean breaks B | mean bound U |
|---|---|---:|---:|---:|---:|---:|
| LibreOffice strict (26, 16) | uniform logit shift | 0.061 | 0.000 | 0.956 | 0.82 | 0.157 |
| LibreOffice strict (26, 16) | proportional, all tasks | 0.048 | 0.000 | 0.953 | 0.61 | 0.144 |
| LibreOffice strict (26, 16) | proportional, half the tasks | 0.054 | 0.000 | 0.948 | 1.43 | 0.190 |
| LibreOffice strict (26, 16) | proportional, a quarter of the tasks | 0.075 | 0.000 | 0.944 | 2.85 | 0.261 |
| LibreOffice strict (26, 16) | complete breaks | 0.191 | 0.000 | 0.823 | 1.83 | 0.210 |
| LO + Thunderbird strict (31, 16) | uniform logit shift | 0.067 | 0.000 | 0.958 | 0.98 | 0.141 |
| LO + Thunderbird strict (31, 16) | proportional, all tasks | 0.042 | 0.000 | 0.960 | 0.65 | 0.125 |
| LO + Thunderbird strict (31, 16) | proportional, half the tasks | 0.050 | 0.000 | 0.951 | 1.53 | 0.166 |
| LO + Thunderbird strict (31, 16) | proportional, a quarter of the tasks | 0.075 | 0.000 | 0.941 | 3.39 | 0.244 |
| LO + Thunderbird strict (31, 16) | complete breaks | 0.182 | 0.000 | 0.836 | 2.03 | 0.188 |
| LO + Thunderbird incl. conditional (36, 12) | uniform logit shift | 0.054 | 0.009 | 0.961 | 1.66 | 0.149 |
| LO + Thunderbird incl. conditional (36, 12) | proportional, all tasks | 0.047 | 0.011 | 0.955 | 1.38 | 0.138 |
| LO + Thunderbird incl. conditional (36, 12) | proportional, half the tasks | 0.055 | 0.006 | 0.953 | 2.44 | 0.178 |
| LO + Thunderbird incl. conditional (36, 12) | proportional, a quarter of the tasks | 0.069 | 0.002 | 0.950 | 4.19 | 0.240 |
| LO + Thunderbird incl. conditional (36, 12) | complete breaks | 0.143 | 0.015 | 0.875 | 2.60 | 0.184 |
| all 43 (43, 12) | uniform logit shift | 0.062 | 0.036 | 0.949 | 1.99 | 0.137 |
| all 43 (43, 12) | proportional, all tasks | 0.048 | 0.028 | 0.953 | 1.54 | 0.122 |
| all 43 (43, 12) | proportional, half the tasks | 0.056 | 0.014 | 0.949 | 2.77 | 0.161 |
| all 43 (43, 12) | proportional, a quarter of the tasks | 0.070 | 0.004 | 0.946 | 4.94 | 0.225 |
| all 43 (43, 12) | complete breaks | 0.140 | 0.038 | 0.883 | 3.03 | 0.169 |

- **Analytic MDE** (exact noncentral t, 80% power, two-sided 0.05):

| Task set (K) | tau2 | n = 8 | n = 12 | n = 16 | n -> infinity |
|---|---:|---:|---:|---:|---:|
| LibreOffice strict (26) | 0.0 | 6.72 | 5.49 | 4.75 | 0.0 |
| LibreOffice strict (26) | 0.0025 | 7.3 | 6.19 | 5.55 | 2.86 |
| LibreOffice strict (26) | 0.006 | 8.05 | 7.05 | 6.5 | 4.43 |
| LibreOffice strict (26) | 0.012 | 9.19 | 8.33 | 7.86 | 6.26 |
| LibreOffice strict (26) | 0.03 | 11.97 | 11.32 | 10.98 | 9.9 |
| LO + Thunderbird strict (31) | 0.0 | 5.93 | 4.84 | 4.19 | 0.0 |
| LO + Thunderbird strict (31) | 0.0025 | 6.47 | 5.49 | 4.93 | 2.6 |
| LO + Thunderbird strict (31) | 0.006 | 7.17 | 6.3 | 5.81 | 4.03 |
| LO + Thunderbird strict (31) | 0.012 | 8.22 | 7.48 | 7.07 | 5.7 |
| LO + Thunderbird strict (31) | 0.03 | 10.78 | 10.23 | 9.93 | 9.01 |
| LO + Thunderbird incl. conditional (36) | 0.0 | 5.33 | 4.35 | 3.77 | 0.0 |
| LO + Thunderbird incl. conditional (36) | 0.0025 | 5.85 | 4.97 | 4.47 | 2.4 |
| LO + Thunderbird incl. conditional (36) | 0.006 | 6.5 | 5.73 | 5.3 | 3.72 |
| LO + Thunderbird incl. conditional (36) | 0.012 | 7.49 | 6.83 | 6.47 | 5.26 |
| LO + Thunderbird incl. conditional (36) | 0.03 | 9.88 | 9.39 | 9.13 | 8.32 |
| all 43 (43) | 0.0 | 4.69 | 3.83 | 3.32 | 0.0 |
| all 43 (43) | 0.0025 | 5.18 | 4.41 | 3.97 | 2.19 |
| all 43 (43) | 0.006 | 5.79 | 5.12 | 4.74 | 3.39 |
| all 43 (43) | 0.012 | 6.71 | 6.14 | 5.83 | 4.79 |
| all 43 (43) | 0.03 | 8.91 | 8.49 | 8.27 | 7.57 |

- **Reading.** A diffuse 5 pp direction effect is detected with probability
  0.89-0.97 (uniform logit shift) and 0.79-0.90 (proportional) at
  the registered n for K = 26-43; an effect carried by complete breaks in about 8% of
  tasks with probability 0.09-0.21. The rare-break bound keeps the
  unqualified SMALL rate at a true -5 pp at or below 0.038 in every structure; without it the
  break structure gives SMALL in up to 0.191 of replicates. Two superseded runs are kept: the
  first without the bound (`power-osworld-v0-partial.json`), the second with a break at
  D_t <= -0.5 (`power-osworld-v1-break050.json`), which let an unqualified SMALL through in up to
  0.087 of replicates at a true -5 pp at K = 43 and led to the large-drop threshold of -0.25.
- Every interval reports K, n and the number of episodes.

## Seeds

Random-number seeds: [42, 43, 44] for simulation; 42 for episode order, the sign-flip
enumeration and every bootstrap. vLLM request seed 42 (inert under greedy decoding; vLLM is not
batch-invariant, so reruns are not assumed identical, which is the rerun noise S1a measured).
OSWorld tasks have no fixture seed: each task has one initial state.

## Compute caps (D22 counting)

| Job | Cap (GPU-h) | Arithmetic |
|---|---:|---|
| Phase 0 (image build, delta certification, oracle, probes) | 0 | CPU-only lane jobs, no GRES |
| Overlay build and pre-funded retry | 0.10 | 3 + 3 minutes, as S1a's O2 |
| Phase 1 (one job; n = 16 if K <= 35, else 12) | 5.88 to 7.88 | job cap by K at the high slot price: K = 26: 5.88; K = 35: 7.88; K = 36: 6.10; K = 43: 7.27 (`registered-caps.json` lists each with the overlay reserve included) |
| Registered total | at most 7.98 | the Phase 1 job plus the overlay reserve (5.98 at K = 26, 7.98 at K = 35); below D20's 8 GPU-h line |

The gauntlet's reviewer budget (0.3 GPU-h) is separate.

## Infrastructure failures and exclusions

As in `q2-stage1-rescoped-v1` section 15 and D56: an undelivered observation, a guest-server
restart, a postconfig or setup server error (HTTP >= 500 or no reply), a VM or container
failure, an engine error or timeout, and a failed keyboard check are infrastructure losses. A
lost episode is re-queued once at the end of its task block; a second loss makes it missing.
Model behaviour (invalid actions, truncation, wrong state) is never infrastructure. A task
enters the analysis only if each of its four cells has at least n - 1 valid episodes.

## Data rights

OSWorld task configs and checkers: Apache-2.0. LibreOffice and its language packs: MPL-2.0.
Thunderbird and its language packs: MPL-2.0. GIMP and its catalogs: GPL-3.0 (run, not
redistributed). GTK: LGPL-2.1. Fonts: SIL OFL 1.1 or the distribution's licence, recorded.
Qwen3.5-9B: Apache-2.0. Pseudo-locale catalogs are derived works of the above under their
licences and stay inside the image; the derived image is not redistributed. Public cotcodec
artefacts are metrics, hashes, codings and per-episode records; screenshots and trajectories
stay on the host and in the private archive unless Kevin decides otherwise.

## Integrity gate (the seven failure modes)

1. Implementation bug passing self-review: the oracle is independent of the fixture code (it
   reads screenshots and the accessibility tree), it was validated on fixtures with known
   properties (7 of 7 variants as expected), and Phase 0 adds positive controls on the real
   applications; a fresh agent audits Phase 0 against this file before the freeze.
2. Hallucinated citation: every source is snapshotted with its HTTP status and hash; source
   lines for each switch are recorded with line numbers.
3. Hallucinated result: no localized-cell measurement exists; every simulated number comes
   from `power-osworld.py` with seeds and input hashes.
4. Shortcut reliance: the agent may succeed from English document content; that is the
   registered estimand (application chrome over English documents), and the Arabic chrome
   share is reported.
5. Bug reframed as insight: a half-mirrored layout, a bidi leak or a setup that diverges
   across cells would look like a treatment effect; O3, O2 and O5 exist to catch them, with
   positive controls.
6. Methodology fabrication: the task list, the estimands, the decision rules and the cap are
   fixed here before any localized data.
7. Frame-lock: the simulation shows which effect structures this K cannot detect (complete
   breaks in a few tasks) and the SMALL rule carries the rare-break bound; the
   infrastructure exit (K0, K1) is written as a first-class result.

## Owner's prior forecast (not a decision input)

Phase 0 admits LibreOffice after at most one remedy round: 0.6 (VCL's coupling of text and layout makes residual leaks in code-composed strings likely; the remedy rule may remove them). Thunderbird admitted: 0.3 (pseudo-locale packs and signatures). GIMP admitted: 0.5. The delta certification passes: 0.85. Phase 1 reached overall, including an admission ruling: about 0.35. If it runs: D PRESENT (harm) 0.4, T PRESENT (harm) 0.5, an unqualified SMALL for D 0.1 (it needs K near 43 and no breaks). The single most likely first-step outcome is a certified image with a published leak inventory and either a run or a K0 exit for LibreOffice.

## Freeze procedure

Phase 0 is built and its gate run in the lane (CPU only) after this draft and the P0.6
registration are accepted; a fresh agent's pre-freeze audit checks the registration against
the image, the oracle record and the code; then
`uv run python scripts/preregister.py freeze s2-arabic-cua-locale-v2 program/preregistrations/s2-arabic-cua-locale-v2.md`
and `verify`; then the admission ruling for Phase 1.

## Design decisions (for the owner's acceptance; v1's 1-30 are withdrawn with Relay)

31. Move S2 from Relay to Q2's certified OSWorld stack (D68).
32. The applications: LibreOffice Calc, Impress and Writer; Thunderbird and GIMP if their
    Phase 0 passes. VLC, VS Code and multi-application tasks out (P0.1).
33. The task screen and the 43-task candidate list, selected on S1a's English records only.
34. No English pilot; S1a's records anchor the power analysis.
35. Qwen3.5-9B only, S1a's configuration (15 steps, greedy, thinking on, 2,048 tokens).
36. Both certified harnesses, episodes split equally.
37. The applications' shipped Arabic translations; no in-project catalog; no native-speaker
    precondition.
38. Catalog-level FSI/PDI isolation in all four cells (P0.4).
39. Per-application layout switches (P0.3), set only in system or share layers.
40. The held-fixed list (P0.5), including the English system shell.
41. The delta certification of the action path (P0.6) as a deviation or short registration of
    `q2-action-path-v2`.
42. The render oracle O1-O6, its A/A tolerance rule and its positive controls (P0.7).
43. Zero residual O2 leaks over the sweep for admission; the remedy rule (a held-fixed
    configuration change applied to all four cells, then a full rerun).
44. The functional A/A probes (P0.8) and the config-invariance probe (P0.9).
45. K_min = 26 admitted tasks.
46. n = 16 if K <= 35, else 12; one session; seeded block interleave.
47. The cap rule from the Q2 design study at the high slot price.
48. D primary; paired t on task means; sign-flip sensitivity.
49. SMALL with the rare-break bound (a large drop is D_t <= -0.25; v1 of the simulation used -0.5,
    which let unqualified SMALL through in up to 0.087 of replicates at K = 43).
50. Mechanism naming only on a 95% CR2 interval that excludes 0 in the predicted direction.
51. The step-0 and keyboard checks per episode; references recorded in the lane.
52. The en-cell reference against S1a (P7) as a description, not a stop.
53. Screenshots and trajectories private by default.
