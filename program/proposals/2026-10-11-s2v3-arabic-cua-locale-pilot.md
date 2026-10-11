# Research Direction: S2 v3 first step, Arabic interface text versus mirrored layout on the certified OSWorld stack (Phase 0 as an executable CPU pilot on the real LibreOffice, and a Phase 1 census of OSWorld's LibreOffice tasks under 8 GPU-h)

**Status:** new proposal under program decision D71 (ii), gauntlet wave 1 of S2 v3; written on 2026-10-11 by a Claude agent as the gauntlet's single synthesis owner on branch `gauntlet/s2v3-locale` (worktree from `main` at `360058d`). S2 v2 (`s2-arabic-cua-locale-v2`) ended at an honest exit at 59 under D68 (rows `1a24cee8...` and the run-2 row in `program/gauntlet/2026-10-10-s2-arabic-cua-locale.jsonl`); its draft is left unedited. The draft registration of this step is `program/preregistrations/s2-arabic-cua-locale-v3.md` (new experiment id, DRAFT, not frozen, no ledger row). A partial executable Phase 0 pilot ran in this gauntlet as four CPU-only Slurm jobs (1097-1100, no GRES, on an empty queue) in the certified VM's own LibreOffice userland; the derived Arabic image, the VM-lane oracle and the delta certification did not run (blocked, see Cheapest Decisive Pilot). The blind critic, the refute-first triad and the two reviewers of this wave have not run. Phase 1's registered caps are 6.10 GPU-h (below 8); whatever this gauntlet scores, Phase 1's admission is Kevin's ruling under D24 and D70, and a score of 100 cannot be certified in this repository (D24)
**Owner:** Kevin Liu (program owner); synthesis, pilot, simulations and draft registration by a Claude agent acting as the single owner
**Source cutoff:** 2026-10-11
**Coverage limits:** This wave's retrieval is the three discovery cells plus the owner's synthesis queries, all recorded in `evidence/2026-10-11-s2v3-arabic-cua-locale-pilot/query-log.json`. Frontier scout: 35 orx discover calls (25 keyword including title-phrase queries for macOSWorld, RealGUINoise, MPR-GUI, VAF and Left-Right Symmetry Breaking; 7 embedding; 4 OpenAlex), 13 OpenReview API searches (6 restricted to ICLR 2027, one scanned in full: 210 'multilingual' submissions), 4 ACL Anthology regex searches over 131,473 entries, Semantic Scholar citer lists for macOSWorld (34), MPR-GUI (5), RealGUINoise (0) and VAF (5), 2 arXiv version checks (24 ids), 3 web searches and 1 patent fetch; 22 full-text reads. Kill-shot scout: 15 orx discover calls, 4 full-text reads, 3 ACL Anthology regex searches (one too broad, 40 of 274 titles scanned), degraded anonymous OpenReview access, source reads of LibreOffice 7.3.7.2, read-only host reads of the VM rootfs and OSWorld at `b138d348`. Cross-domain scout: 18 orx discover calls, 5 orx paper reads, 11 web searches, 10 page fetches, 6 Bugzilla records. Owner: 3 orx discover calls and 1 full read (2411.00640). Not searched: Google Scholar, X, Reddit, Hacker News, GitHub, Chinese-language venues (no Chinese query this wave), ACM DL and IEEE Xplore full text, EMNLP 2026 proceedings (not yet in the Anthology), patents beyond one Google Patents page. orx is 0.2.2 (reports itself outdated against 0.2.18). PRISMA-style for this wave: 1,493 returned ids recorded (1,047 unique; OpenReview lists truncated at 25 per query in the log), screened by title or abstract; 32 paper reads beyond the abstract (22 frontier, 4 kill-shot, 5 cross-domain, 1 owner; some overlap); 0 direct priors
**Budgets:** queries=150; wall_minutes=600; tokens=8000000; dollars=150; waves=3; gpu_hours=0.3
**Novelty verdict:** NO_DIRECT_PRIOR_FOUND
**Safety verdict:** PASS
**Evidence bundle:** evidence/2026-10-11-s2v3-arabic-cua-locale-pilot/bundle.json

The budgets are this gauntlet's, cumulative over the cells, the synthesis, the triad, the
reviewers and the recorder. Queries counted against the 150: 68 orx discover calls by the three
cells (35 + 15 + 18) and 3 by the owner (71); counting the ACL Anthology and OpenReview searches
as well (the S2 run-2 convention), 92. At least 58 remain, above the 30 reserved for the three
refuters. The gauntlet's GPU budget (0.3 GPU-h) is for the open-weight reviewer's lane job; the
pilot used 0 GPU-h. The novelty verdict field uses the doctor's vocabulary; the merged kill-shot
verdict is STILL_OPEN.

## Changes from S2 v2

S2 v2 scored 49 (wave 1, Relay) and then 59 (run 2, OSWorld; reviewers 61 and 59; all three
refuters refuted). Its two largest defects, one per wave, are the ones this step fixes.

| # | Defect (who named it) | v3 repair | Where | Evidence |
|---:|---|---|---|---|
| 1 | Wave 1: Relay's 18 tasks cannot power Phase 1 (reviewers, feasibility refuter) | Already moved in v2 onto Q2's certified OSWorld stack; kept | Registration, Identity | D68; v2 |
| 2 | Wave 2: P3/P4's only falsifier, an unqualified SMALL, is unreachable at K = 26-31; the rare-break bound is the success-run bound U = 1 - 0.05^(1/K) times the en mean (both reviewers, feasibility and identification refuters) | A census of every OSWorld LibreOffice single-application task that passes the pool rules (106 tasks; S1a's confirm split plus the dev and reserve splits), with a census frame for the primary decision: complete breaks in a few tasks enter the mean instead of needing a bound. Simulated census SMALL at a true null 0.97 (homogeneous) and 0.92 (task-specific mixed-sign perturbation) at K = 106, n = 4; false SMALL when the census truth is beyond a margin at most 0.051 (0.056 at K = 89) | Decision rules; Tasks | `compute/power/power-v3.json`; `compute/pool/pool-v3.json` |
| 3 | An enlarged unscreened pool reaches SMALL by dilution, since about half of the tasks are never solved (33 of the 62 with S1a records are 0 of 8) (kill-shot scout) | Dual margin: +/-5 pp on the census mean and the ratio of solve rates inside (0.85, 1/0.85); the ratio does not change when never-solved tasks are added. At a 15% relative drop the absolute margin alone would call SMALL in 0.17-0.29 of replicates, the dual margin in 0.07-0.19, and SMALL when the census truth is beyond a margin stays at or below 0.051 | Decision rules | `power-v3.json` (`small_abs_only` against `small`) |
| 4 | Selection on English success pushes D towards PRESENT_HARM under direction-free decorrelation; no placebo (reviewer 2, identification refuter) | No selection at all: every admitted task, all cells measured fresh; a reshuffle is mean-preserving on the census (simulated census true D 0.0 pp under reshuffles of 10% and 30% of tasks; interval coverage 0.94-0.95) | Tasks; Leakage | `power-v3.json` reshuffle rows |
| 5 | Heterogeneous-effect power 0.45 at K = 26 (feasibility refuter, reviewer 1) | Distinct tasks, not reruns: K = 106 at n = 4. PRESENT at a 15% relative drop (about -4.3 pp on the census) 0.85-0.96 across uniform, proportional, quarter-of-tasks, complete-break and mixed-sign structures | Statistics | `power-v3.json` |
| 6 | Catalog isolation incomplete; STR_TABLE_DEF becomes document content and 42e0a640's checker reads "Sheet2" (reviewers, identification refuter) | Executed on the real LibreOffice 7.3.7.2 (pilot job 1098): a pseudo-Arabic interface names the first sheet "ورقة1"; wrapping STR_TABLE_DEF in FSI/PDI writes U+2068/U+2069 into the saved .xlsx in the English cell; a finalized `SheetPrefix` = "Sheet" gives "Sheet1" in both languages and leaves English unchanged. v3 pins SheetPrefix in all cells, wraps only where the oracle finds a coupling leak and never strings that reach documents, and adds a tagged pseudo-catalog cell to find the rest | P0.4, P0.5, P0.8 | `compute/pilot/job1098/` |
| 7 | Switches read at LibreOffice master, not the installed build (reviewer 1) | Executed: finalized `UIMirroring` = true in the system layer is pixel-identical to `SAL_RTL_ENABLED` = 1, false is pixel-identical to stock English, the env variable overrides the key, and a finalized system-layer `ooLocale` = `ar` overrides the profile's `en-US` (blank Calc, Impress, Writer); at the post-open state of 104 of 106 pool tasks the mirrored chrome reverses (column-ink correlation with the reversed LTR band, median 0.59 against -0.08 unreversed; 105 of 106 tasks) and the window title is byte-identical in all three cells for all 104 tasks that opened | P0.3, O7 | `compute/pilot/job1098/`, `job1099/` |
| 8 | P6 screen-half moderator degenerate under whole-window mirroring (reviewer 2, identification refuter) | Positional exposure from S1a's own English click coordinates (share of click actions, mean mirrored displacement), plus the RTL-defect count | P0.12 | registration |
| 9 | Step-0 failures not re-queued; K_min equals the modal K; P7 not a stop, so a degraded image eased SMALL (reviewer 1) | Re-queue up to twice; K_min = 62 (58% of the pool; census SMALL and PRESENT still decisive there, `power-v3.json`); K5 suppresses SMALL when the English cell is confidently degraded; K4 makes the 15-85% English band a stop | Kill criteria | registration |
| 10 | D53's delta suite omitted A2, A3, A6 and the V = 20 concurrency Phase 1 uses (kill-shot scout) | P0.6 adds A2 (both adapters), A6 (Writer typing canary), one V = 20 rung with the cells interleaved, and A3 once in ar-RTL | P0.6 | registration |
| 11 | No executable pilot (cap 79) | Partial: four CPU jobs on the real application (switch mechanics, content leaks, mirrored layout and window titles at 106 post-open states, AT-SPI capture, which showed that AT-SPI extents cannot certify mirroring here). Not the derived image, not the VM lane | Cheapest Decisive Pilot | `compute/pilot/` |

Not repaired, and why:

- **The derived Arabic image (P0.2).** The certified image has no Arabic interface (no
  `libreoffice-l10n-*`, no Arabic GTK catalog; pilot facts). Building it needs three package
  downloads on the login host (the lane has no network), which is an outward action that waits on
  Kevin, and new image-surgery and lane code that needs review. So no real Arabic catalog was
  rendered; the "pseudo-Arabic" pilot cells test the mechanics of an Arabic interface language, not
  the catalogs.
- **A placebo layout cell.** No LibreOffice switch relocates widgets by a matched displacement
  without reversing direction (docking the sidebar or switching to the tabbed interface changes
  far more), and the census removes the selection mechanism the placebo was meant to control. A
  fifth cell would still fit (7.57 GPU-h at K = 106, n = 4); it is deferred, with its cost stated.
- **Unsigned reviews (cap 89)** and the trust store (D24).

## Claim and Research Question

**Question.** On Q2's certified OSWorld stack, with instructions, documents, checkers, the system
shell, number formats, Calc's default sheet prefix and the keyboard held fixed, and LibreOffice's
interface text language and layout direction switched separately in a 2x2 {English, Arabic
interface text} x {left-to-right, mirrored layout}, how large are (D) the main effect of mirroring
and (T) the main effect of Arabic interface text on the screenshot success of Qwen3.5-9B over
OSWorld's LibreOffice tasks?

**This step.** Phase 0 (CPU only): (a) the enlarged task pool, frozen now; (b) the derived image
with LibreOffice's shipped Arabic interface and the separate layout switch; (c) the factorial render
oracle on the real application in the measurement lane at every candidate task's post-setup state.
Plus the design of Phase 1 under 8 GPU-h. Phase 0's mechanics ran here as an executable pilot in the
CPU lane; (b) and the VM-lane part of (c) did not.

**Variable.** The cell: the application's interface language (`ooLocale` `en-US` or `ar`) and its
layout key (`UIMirroring` false or true), both finalized in the system configuration layer.

**Claim scope.** `portability-protocol`: a measurement on one frozen model and two certified
scaffolds over LibreOffice Calc, Impress and Writer. Primary frame: the census of admitted tasks;
secondary: tasks like these. Application-level localization over English documents and an English
system shell. It does not decompose macOSWorld's whole-OS drop.

**Why the 2x2.** The two main effects average both paths and sum exactly to the total
English-to-mirrored-Arabic change (ar-RTL - en = T + D). The off-diagonal cells (English in a
mirrored layout; Arabic in an unmirrored one) are what LibreOffice's own key produces and what
platform test practice renders (Android's forced RTL, Chromium's separate `--force-ui-direction`
and `--force-text-direction`, the qps-plocm and en-XB pseudo-locales).

## Strategic Fit and Why Now

- **Program fit.** D71 (ii) asked for exactly this: S2 v3 with a larger LibreOffice pool so SMALL is
  reachable, and Phase 0 built as an executable CPU pilot to attack the 79 cap. It reuses the
  program's most expensive certified asset (the D53 action path, S1a's lane, records and cost card)
  and puts language back as the controlled variable on it.
- **Why now.** macOSWorld's latest version (v4, 2025-10-18) still leaves its split open ("the visual
  complexity of Arabic glyphs or the mirrored UI layout, or both", Sec. 5.2). None of its 34
  Semantic Scholar citers takes it up; its macOS successor MacArena dropped the language axis; no
  ICLR 2027 submission in a full scan of 210 'multilingual' entries renders a localized GUI. The
  cross-lingual agent gap is now documented for instruction language in text and tool environments
  (OmnilingualGAIA2: 8.8-18.4 points pass@3), not for the interface the agent sees.
- **What it buys.** A census claim about the benchmark people actually run, decisive in both
  directions: SMALL is reachable when the effect is small, and a 15% relative drop is detected with
  probability 0.85-0.96. The infrastructure (a render-certified localized OSWorld image, the
  oracle, the content-leak and RTL-defect inventories) is useful beyond S2 even at an
  infrastructure exit.
- **What it does not buy.** One model, one language, application-level localization, LibreOffice
  only; a population claim ("tasks like these") is weaker (simulated SMALL_POP 0.84-0.96 under
  non-reshuffle nulls, 0.04-0.50 under reshuffles).

## Primary-Source Evidence

Claim registry (full records in `evidence/2026-10-11-s2v3-arabic-cua-locale-pilot/doctors/citation.json`).
"First-party" marks numbers reported by their producers and not replicated here; "abstract" marks
abstract-level reads; "source" marks code read at the pinned revision; "pilot" marks this
gauntlet's executed checks with job receipts; "repository" marks program records.

| Id | Claim | Source and date | Read |
|---|---|---|---|
| C01 | All-agent success excluding Advanced Apps: en 19.3%, ar 13.7% (28.8% relative, 5.6 pp absolute); attributed to "Arabic glyphs or the mirrored UI layout, or both"; no significance testing | [macOSWorld, NeurIPS 2025, v4](https://arxiv.org/abs/2506.04135), 2025-10-18, Table 4, Sec. 5.2, checklist item 7 | full text (frontier, kill-shot) |
| C02 | Arabic cell changes the whole OS (shell and every app), script and direction at once; one mirroring anecdote (Claude CUA clicks the unmirrored Settings location, Fig. 19) | same, Sec. 5.2, App. D.1, Fig. 19 | full text |
| C03 | 34 Semantic Scholar citers, none on Arabic, RTL, mirroring or locale; MacArena (421 tasks, 50 apps) has no language axis | Semantic Scholar citations of 2506.04135, 2026-10-10; [MacArena](https://arxiv.org/abs/2606.06560), 2026-06-04 | metadata; full text |
| C04 | 'Language Swap' is browser auto-translation, one of 42 noise types; multilingual coverage named as future work; still v1, submitted to ARR August 2026 | [RealGUINoise](https://arxiv.org/abs/2609.38184), 2026-08-07, Table 10, Limitations | full text |
| C05 | Static parallel screenshots in six languages, no Arabic, no RTL, not interactive | [MPR-GUI, ACL 2026](https://arxiv.org/abs/2512.00756), v2 2026-04-28; [aclanthology 2026.acl-long.1375](https://aclanthology.org/2026.acl-long.1375/) | full text |
| C06 | Paired grader-preserving UI variants (eight visual-attribute families including position); no language or direction variant | [VAF](https://arxiv.org/abs/2601.21961), v2 2026-02-27; WebPageBench 2609.35026; BreakingWeb 2609.35814 | full text |
| C07 | Instruction-language gaps in text, tool and terminal agents; none renders a localized GUI | [OmnilingualGAIA2](https://arxiv.org/abs/2608.08775), 2026-08-09; BabelArena, WorldBench, PolyWorkBench, Terminal-Bench-LILT | full text / abstract |
| C08 | Model-specific grounding blind zones; relocation into a zone lowers accuracy (Qwen3-VL-8B -16.1 pp) | [ScreenHaystack, EMNLP 2026](https://arxiv.org/abs/2609.32036), 2026-09-25 | full text |
| C09 | Left-right symmetry breaking traced to positional-token attention gradients | [2601.12809, ICML 2026](https://arxiv.org/abs/2601.12809) | full text |
| C10 | 35 language-setting UI display bugs in Android apps, 19 RTL; ITDroid's Spanish/Hindi/Arabic setup | [SUDFinder, TSE](https://arxiv.org/abs/2607.04120), 2026-07-05; ITDroid, ICSME 2020, doi 10.1109/ICSME46990.2020.00061 | full text; metadata |
| C11 | Cross-orientation state-equivalence testing with paired-state oracles | [RotDroid, ISSRE 2026](https://arxiv.org/abs/2608.25425) | abstract |
| C12 | i18n testing mapping study: 24 primary studies, layout bugs one of four categories, six tools | [IST 2026](https://doi.org/10.1016/j.infsof.2026.108258) | abstract |
| C13 | A true RTL layout is a mirror plus restoration of forward-oriented elements, not a pixel flip | US12008219B2 (ByteDance), granted 2024-06-11 (Google Patents summary) | summary |
| C14 | Qwen-UI-Agent: 79.5% on OSWorld-Verified; no Arabic or multilingual evaluation | [Qwen-UI-Agent report](https://arxiv.org/abs/2607.28227), 2026-07-30 | full text (first-party number) |
| C15 | With stimuli random, power plateaus as participants grow | [Westfall, Kenny and Judd 2014](https://doi.org/10.1037/xge0000014) | abstract |
| C16 | Zero events in n: 95% upper bound 1 - 0.05^(1/n) (rule of three) | [Hanley and Lippman-Hand 1983](https://doi.org/10.1001/jama.249.13.1743) | abstract |
| C17 | Freedom-from-disease surveys: finite-population (hypergeometric) design with imperfect tests | [Cameron and Baldock 1998](https://doi.org/10.1016/S0167-5877(97)00081-0) | metadata |
| C18 | Evals as samples from a super-population; clustered errors; the fixed-question view is the alternative | [Adding Error Bars to Evals](https://arxiv.org/abs/2411.00640), Sec. 2 | full text (owner) |
| C19 | If the board and outcomes are fixed, the mean is an exact summary and any interval must come from another declared source of randomness | [When Pair Count Is Not the Sample Size](https://arxiv.org/abs/2609.33012), 2026-09 | abstract (owner) |
| C20 | Few-cluster analyses: cluster-level and corrected methods keep type I error | [Leyrat et al. 2018](https://doi.org/10.1093/ije/dyx169) | abstract |
| C21 | Innocuous setup changes bias systems measurements; randomize setups | [Mytkowicz et al. 2009](https://doi.org/10.1145/1508244.1508275) | abstract |
| C22 | Pseudolocalization finds unlocalized resources by tags; Windows ships a mirrored pseudo-locale | [Microsoft Learn](https://learn.microsoft.com/en-us/globalization/methodology/pseudolocalization) | full page |
| C23 | Chromium separates UI direction from text direction (`--force-ui-direction`, `--force-text-direction`) | [base_i18n_switches.h](https://chromium.googlesource.com/chromium/src/+/master/base/i18n/base_i18n_switches.h) | source |
| C24 | Isolates: text inside FSI ... PDI cannot affect surrounding order; controls are invisible and can survive processing | [UAX #9 rev 52](https://www.unicode.org/reports/tr9/); [W3C bidi controls](https://www.w3.org/International/questions/qa-bidi-unicode-controls) | standard |
| C25 | AT-SPI reports wrong x for centred Impress text (open) | [tdf#150231](https://bugs.documentfoundation.org/show_bug.cgi?id=150231) | bug record |
| C26 | RTL-only VCL defects: misplaced menus under SAL_RTL_ENABLED with gtk3 (tdf#96333), missing icons (tdf#153080), a flipped control's meaning (tdf#74751) | [tdf#96333](https://bugs.documentfoundation.org/show_bug.cgi?id=96333) and the others | bug records |
| C27 | LibreOffice 7.3.7.2: SAL_RTL_ENABLED forces RTL; else `UIMirroring` decides; else the UI language; GTK3 widgets take the default direction from it | `vcl/source/app/settings.cxx` GetConfigLayoutRTL; `vcl/unx/gtk3/gtkdata.cxx:61` at tag `libreoffice-7.3.7.2` ([source](https://raw.githubusercontent.com/LibreOffice/core/libreoffice-7.3.7.2/vcl/source/app/settings.cxx)) | source (kill-shot) |
| C28 | New sheet names come from the SheetPrefix option, default ScResId(STR_TABLE_DEF) = NC_("STR_TABLE_DEF", "Sheet") | `sc/source/core/tool/defaultsoptions.cxx` 30, 73; `sc/inc/globstr.hrc` 146 at 7.3.7.2 | source |
| C29 | No Arabic accelerator overrides in Accelerators.xcu (Ctrl+S stays Save) | `officecfg/registry/data/org/openoffice/Office/Accelerators.xcu` at 7.3.7.2 | source (kill-shot) |
| C30 | The certified image: Ubuntu 22.04.3, LibreOffice 1:7.3.7-0ubuntu0.22.04.4 (7.3.7.2), gtk3 and gen plugins, only `common` resources, English language packs only, no `gtk30.mo` for Arabic, 20 Arabic-capable font families (`fc-match :lang=ar` = DejaVu Sans), system layer `/etc/libreoffice/registry` first in `CONFIGURATION_LAYERS` | host rootfs (read-only) and pilot job 1098 facts | pilot |
| C31 | The three packages exist at the matching versions (HTTP 200/303 on HEAD): l10n-ar 663,804 B; language-pack-ar-base 151,600 B; language-pack-gnome-ar-base 930,704 B | Launchpad librarian (asset cell, HEAD only, nothing downloaded) | metadata |
| C32 | Pool: 117 LibreOffice tasks; 106 admitted (confirm 62, dev 17, reserve 27); 12 checkers read an agent-created "Sheet2"; 3 read `registrymodifications.xcu`; 99 end with a strict activate_window and Ctrl+S | `compute/pool/pool-v3.json` from OSWorld `b138d348` | repository / pilot |
| C33 | S1a 9B on the 62 confirm pool tasks: 29 solved at least once of 8, 33 never; mean 0.288; cost 0.0027 GPU-h per episode; rerun discordance about 11%; 9B session shift +5.5 pp | `program/evidence/2026-10-10/q2-stage1-analysis/a1.jsonl`; `q2-stage1-a1/RESULTS.md` (D66) | repository |
| C34 | A 5 pp gate needs about 100-115 distinct tasks at S1a-like heterogeneity; distinct tasks bind, not reruns | design study README Sec. 7 (D69) | repository |
| C35 | D53's scope excludes another image, untested catalog instances and the guest server under task applications | `program/decisions.md` D53 | repository |
| C36 | Pilot K1-K6: a tagged `en_US` `sc.mo` is loaded (first sheet "⟦Sheet⟧1"); an FSI-wrapped STR_TABLE_DEF puts U+2068/U+2069 into the sheet name and the saved .xlsx; finalized SheetPrefix gives "Sheet1" in English and pseudo-Arabic; pseudo-Arabic without the pin gives "ورقة1" | `compute/pilot/job1098/pilot-record.json` | pilot |
| C37 | Pilot L0-L6: UIMirroring false = stock (identical pixels); UIMirroring true = SAL_RTL_ENABLED (identical pixels); pseudo-Arabic RTL = env RTL with UIMirroring false (env wins); mirrored status bar clips its text fields to one character; pseudo-Arabic changes UI digits ("٪١٠٠") | same | pilot |
| C39 | Pilot job 1100: under mirroring, 53% (median) of matched AT-SPI elements keep their unmirrored LTR extents although the screen is mirrored (VCL toolbar buttons and menu objects); GTK menubar items report exact reflections | `compute/pilot/job1100/o3-analysis.json` | pilot |
| C38 | Pilot at 106 post-open states (L1 en-LTR, L2 en-RTL, L4 pseudo-ar): 104 opened in all cells (one download path is percent-encoded, `%23`, and the pilot did not decode it, a pilot bug since fixed, the file is in the cache; one `launch` setup step not emulated); titles byte-identical across the three cells for all 104 tasks that opened; chrome reverses in 105 of 106; L2 against L4 differ in 0.08% of pixels (median; max 0.9%), in the status bar, Calc's sheet tab and the caret | `compute/pilot/job1099/` | pilot |

## Closest Prior Work

1. **macOSWorld** ([2506.04135](https://arxiv.org/abs/2506.04135), NeurIPS 2025, v4 2025-10-18;
   [OpenReview YJxGJP8feU](https://openreview.net/forum?id=YJxGJP8feU)). About 200 interactive macOS
   tasks in VMs, five system languages, machine-translated instructions, six agents run once per
   task and language, and one cross-lingual analysis with English instructions in localized
   interfaces. It owns the UI-locale main effect on an executable desktop benchmark and names the
   open split. Its Arabic cell changes the whole OS, the script and the direction together.
   **Delta:** S2 v3 separates application interface text from application layout direction inside
   one environment (shell, documents and instructions English), paired within task and session,
   with a census of a fixed benchmark subset, intervals in two frames, a dual-margin equivalence rule
   and a render oracle that certifies each cell. S2's ar-RTL cell corresponds to macOSWorld's
   English-instruction runs in the Arabic interface, and S2 does not decompose macOSWorld's
   whole-OS drop. What S2 lacks: breadth (30 applications, six agents, four languages).
2. **RealGUINoise** ([2609.38184](https://arxiv.org/abs/2609.38184)). Language Swap is browser
   auto-translation, one of 42 perturbations. **Delta:** a controlled decomposition with a direction
   factor. Scoop vector: an ARR revision adding RTL; re-check before any write-up.
3. **VAF, WebPageBench, BreakingWeb** (2601.21961, 2609.35026, 2609.35814). Paired,
   grader-preserving UI variants. **Delta:** none has a language, script or direction variant; the
   paired-variant method is theirs.
4. **MPR-GUI** (2512.00756, ACL 2026). Aligned static screenshots, no Arabic. **Delta:** executable,
   oracle-certified cells.
5. **i18n testing** (ITDroid, SUDFinder, GWALI, the IBM mirroring-test family, RotDroid, the 2026
   mapping study). They build the render oracle's checks; they measure no agent. **Delta:** the
   oracle is infrastructure here, a manipulation check, not a contribution.
6. **Mechanism priors** for a non-null mirror effect: ScreenHaystack's blind zones (relocation
   alone moves grounding), left-right asymmetry in VLM encoders (2601.12809, 2610.06324).
7. **Method priors**: Westfall et al. (tasks set the ceiling), Hanley and Lippman-Hand and Cameron and
   Baldock (success-run and finite-population bounds), Miller 2411.00640 and 2609.33012 (super-population
   against fixed-board inference), Leyrat et al. (few-cluster analysis).

The closest prior for blind discrimination stays macOSWorld. Fresh anonymized mechanism paragraphs
are in `evidence/2026-10-11-s2v3-arabic-cua-locale-pilot/blind/` (file names carry no role;
`compute/blind-roles.json` maps them for the recorder only).

## Novelty Ledger

| Proposed component | Closest prior | Same | Delta | Confidence |
|---|---|---|---|---|
| Split of an executable GUI agent's interface-localization effect into a text part and a layout-direction part inside one environment, for application-level localization | macOSWorld (2506.04135) | interactive desktop tasks in VMs, Arabic mirrored interfaces, screenshot agents, binary success | the prior leaves the split open and localizes the whole OS; S2 crosses application text and application layout in a 2x2 with shell, documents and instructions English, paired within task and session | medium |
| Census of a fixed benchmark subset with a finite-population (census) frame for the equivalence decision, the population frame reported beside it | Miller 2411.00640 (super-population default); 2609.33012 (fixed-board summaries); freedom-from-disease surveys (Cameron and Baldock) | finite- versus super-population inference | applied to make an agent robustness null reachable and valid, with a dual (absolute and ratio) margin against dilution | medium (the statistics are standard) |
| Off-diagonal cells as experimental factors for agents | Android forced RTL, Chromium's separate direction switches, en-XB and qps-plocm | direction without a script change | measured on agents, not used as a QA tool | medium |
| Factorial render oracle (text-run identity, reflection, order, content identity, title identity, RTL-defect inventory) and a tagged pseudo-catalog cell | GWALI, SUDFinder, ITDroid, RotDroid, the IBM family, pseudolocalization practice | layout-relation, reflection and coverage checks | a manipulation check certifying that each cell differs only in its factor; not a novelty claim | high |
| Locale and direction as a grader-preserving UI variant | VAF, WebPageBench, BreakingWeb | paired variants with task and grader fixed | no language or direction variant in any | high (the method is not novel) |
| UI language as an interface perturbation | RealGUINoise | language swap on GUI agents | bundled, no RTL factor, no decomposition | high |
| Positional moderator from the agent's own English click coordinates | ScreenHaystack (2609.32036) | relocation moves grounding | a task-level moderator frozen before data, named only on a negative interval | medium |
| Reasoning-language arm | Skill Issue (2608.25832) | | out of scope | not assessed |

Novelty wording: No direct prior art found through 2026-10-11 under the coverage in the header: the
frontier scout's 35 orx discover queries (keyword with the mechanism's exact terms and each closest
prior's title phrase, embedding with the mechanism paragraph, OpenAlex), its OpenReview, ACL
Anthology, Semantic Scholar and arXiv checks and 22 full-text reads; the kill-shot scout's 15 orx
discover queries and 4 full reads; the cross-domain scout's 18 orx discover queries and 5 paper reads;
the owner's 3 orx discover queries and 1 full read. Every query and returned id is in `query-log.json`.
The residual is narrow: a paired, render-certified split of application-level localization into
text and direction on an executable benchmark. The census frame, the oracle, the isolation
mechanism, the off-diagonal cells and the paired-variant method are prior art used as
infrastructure.

## Mechanism and Falsifiable Predictions

**Instrument.** A derived image of the certified OSWorld image adds LibreOffice's shipped Arabic
catalogs and GTK's Arabic strings. One selector file in the system configuration layer sets the
interface language (`ooLocale`) and the layout key (`UIMirroring`), both finalized, so the four
cells differ in exactly that file. The pilot shows on the installed build that the key alone
mirrors the whole application (menus, toolbars, sidebar, status bar, sheet tabs) while documents
stay unmirrored, that it is pixel-equivalent to LibreOffice's environment switch, and that a
finalized system value overrides the user profile. A render oracle certifies each cell at every
task's post-setup state; a tagged pseudo-catalog finds strings that escape the catalogs or reach
saved documents; D53's action-path suite is rerun on the image.

**Hypothesized causes.** Mirroring could lower success through (i) target relocation into regions
where the model grounds worse (ScreenHaystack) and (ii) left-to-right priors about menus, toolbars
and panels that mislead planning (macOSWorld's Settings anecdote), and through (v) RTL-only
rendering defects that are part of real RTL LibreOffice (the clipped status bar the pilot found).
Arabic interface text could lower success through (iii) weaker reading of Arabic glyphs and Arabic
UI digits and (iv) lost word overlap between English instructions and interface labels.

**Predictions (registration v3), each with a reachable falsifier:** P1, Phase 0 admits at least 62
tasks (falsifier K0); P2, the delta certification passes (K1); P3, D < 0 (falsified by census SMALL
or PRESENT_BENEFIT; simulated census SMALL at a true null 0.92-0.97); P4, T < 0 (same); P5 and P6,
negative moderator slopes for positional exposure (D) and lexical overlap (T), named only on a 95%
CR2 interval below 0; P7, the layout key and the language produce one layout treatment (Phase 0;
pilot: en-RTL and pseudo-ar-RTL screens differ only in catalog strings, the status bar's locale
fields and the caret).

**Kill criteria:** K0 fewer than 62 admitted tasks (infrastructure exit); K1 a failed delta
certification; K2 more than 5% infrastructure losses in a cell; K3 more than 2% step-0 failures in a
cell; K4 English census success outside [0.15, 0.85]; K5 a confidently degraded English cell (no
SMALL claim); K6 D and T both SMALL and neither PRESENT (publish the robustness null); K7 neither
PRESENT (no reasoning-language arm); K8 cap reached (analyse complete blocks if at least 62).

## Cheapest Decisive Pilot

**What ran in this gauntlet (executable, CPU only, 0 GPU-h).** Four Slurm jobs after a cancelled first attempt, each checked
against an empty `squeue` first, no GRES, through `infra/slurm/host-single-node/s2v3-pilot-cpu.sbatch`
(a path-only copy of the D12 CPU lane: `--network=none`, read-only root, all capabilities dropped,
the host user's uid, a preflight that refuses any visible GPU device) in
`cotcodec-q2-lo-vm@sha256:f5b4c40eefd2b92f846652910ba34db35e1ae7bf90fa474595cc745cc5895361`, the certified
VM's own LibreOffice 7.3.7.2 userland plus Xvfb and openbox. A private copy of the installation
adds one extra system-level configuration layer per cell and per-cell `.mo` files, which is what
the derived image will do in `/etc/libreoffice/registry` and `program/resource`.

| Job | What | Result |
|---|---|---|
| 1096 | first attempt | cancelled by the owner after 2 min: headless UNO could not connect |
| 1097 | debug | `SAL_USE_VCLPLUGIN=gtk3` makes `--headless` open a display; fixed (headless runs no longer force the plugin) |
| 1098 | A: switch mechanics on blank documents (7 layout cells x 3 apps) and content probes (8 cells), 4.6 min, exit 0 | C36, C37: en `.mo` catalogs load; wrapped content strings reach saved files; the SheetPrefix pin works in both languages; `UIMirroring` true = `SAL_RTL_ENABLED`, false = stock; env beats key; finalized system-layer `ooLocale` beats the profile; mirrored status bar clips its fields; UI digits change with the language. The AT-SPI bus started but the walk skipped the application node (fixed) |
| 1099 | B: 106 pool tasks x {en-LTR, en-RTL, pseudo-ar default} at the post-open state (setup downloads from the pinned cache, open), 8 workers, 7.6 min, exit 0 | C38: 104 of 106 open in all three cells; titles byte-identical across the three cells for all 104 tasks that opened; chrome reverses in 105 of 106 (median column-ink correlation 0.59 against the reversed LTR band, -0.08 unreversed); en-RTL against pseudo-ar-RTL differ in 0.08% of pixels (median). The coarse document-band match was not discriminative (median residual 0.048 unflipped against 0.057 flipped; grids and white pages match either way), so O5 is not claimed. AT-SPI dumps were captured but truncated by the runner's 4,000-character output tail (fixed) |
| 1100 | B': the same 106 tasks x {en-LTR, en-RTL} with AT-SPI written to files, for O3 on real widget boxes, 5.7 min, exit 0 | C39: 212 dumps (median 1,915 nodes); in 105 tasks a median 227 showing elements match across the two cells, and only 0.475 of them (median; minimum 0.43) report the reflected box while 0.53 report their unmirrored LTR box. The unmirrored ones are VCL-side accessibles (toolbar buttons such as Open at x = 24 in both cells, VCL menu objects) whose pixels are mirrored on screen; GTK's menubar items report exact reflections (File at x = 0, then 1,881). So AT-SPI extents are not a valid O3 input in mirrored LibreOffice 7.3.7.2, and O3 is registered on ink-located boxes |

**What did not run, and exactly what blocks it.**
- P0.2, the derived image: the three package downloads (C31) need network access the lane does not
  have and are an outward action that waits on Kevin's go-ahead; the image-surgery script
  (`dpkg-deb -x` plus `debugfs -w` in the existing `cotcodec-q2-vmprobe` image, no host root) and a lane
  version that accepts a new image digest and the 27 reserve tasks (`harness/q2_stage1/lane.py` pins
  `QCOW2_SHA256` and line 253 allows only pool and dev tasks) are new code that needs review.
- P0.6, the VM-lane oracle (P0.7 with the accessibility service of the VM), P0.8-P0.11: they run on
  the derived image in the VM lane.
- Container fidelity: the container renders toolbar buttons as text labels (no icon theme under
  openbox), so icon mirroring and direction-sensitive icons are untested here.

**The decisive next CPU step (about 3-5 VM-h once permitted).** With the three packages, rerun job
1098's design and job 1100's sweep with the real Arabic catalogs extracted into the container copy
(four real cells, O2-O4 and O7 on real strings, P0.8 with the real catalogs); then the image surgery
and the lane run of P0.6-P0.11. That decides K0 and K1 before any GPU.

**Phase 1 (one GPU job, cap 6.10 GPU-h at K = 106).** Qwen3.5-9B on the admitted census in four
cells, n = 4 per task-cell split across both harnesses, one session at V = 20 (1,696 episodes at
K = 106). It decides D and T at the registered rules; no English pilot precedes it (S1a's records
anchor the prior; the 44 new tasks enter unscreened by design).

## Controls, Baselines, and Ablations

- **Within-environment controls.** en is the baseline; ar-LTR changes only the text; en-RTL only the
  layout; ar-RTL both. Every cell of a task runs in one serving session, interleaved in seeded task
  blocks, cells assigned to VM slots at random within each batch, both harnesses equally.
- **Manipulation checks before any GPU job.** O1-O8 with planted positive controls (P0.7), the tagged
  pseudo-catalog cell (P0.8), functional A/A probes including a default-named sheet insert (P0.9),
  config invariance (P0.10), offline setup (P0.11); per episode, the step-0 screen and the keyboard
  map.
- **Held fixed.** Instructions, documents and checkers (English); the system shell; number and date
  formats and the document default language; SheetPrefix; CTLFont; Calc's English function names;
  autocorrect; the keyboard map; model, decoding, step cap, settles and harness prompts.
- **Baselines not used.** macOSWorld's numbers are context. S1a's English records are a reference
  for the English cell (K5), not a control.
- **Deferred ablations.** A matched-displacement placebo layout (no LibreOffice switch provides one;
  7.57 GPU-h if added as a fifth cell), reasoning and instruction language, other languages, full-OS
  localization, a second model (Qwen3.5-4B), the accessibility observation setting.

## Evaluation, Statistics, and Leakage Checks

- **Primary estimand.** D = mean over tasks of D_t = ((y_arR - y_arL) + (y_enR - y_en)) / 2, cell means
  over n = 4 episodes (2 per harness); companion ratio R_D = S_RTL / S_LTR. Secondary: T and R_T, the
  interaction, the total Delta = T + D, the dossier's conditional contrasts, D and T by harness and
  application, fractional scores, the estimates without the 7 S1a-flagged tasks, process metrics,
  moderators.
- **Decision rules (census frame, primary).** Var(D) = (1/K^2) sum of within-task variances, each
  estimated without bias per (task, cell, harness); log R_D by the delta method. PRESENT if the 95%
  interval of D excludes 0 (sharp-null randomization test beside it; PRESENT_FRAGILE on
  disagreement). SMALL if the 90% interval of D lies inside +/-5 pp and that of log R_D inside
  +/-log(1/0.85). Population frame reported, with a concentration guard (per-task one-sided Fisher
  tests at p <= 0.01; Clopper-Pearson bound U on the broken share; U x S_LTR < 5 pp and U < 0.15).
- **Why tasks, not episodes.** Qwen3.5-9B is close to deterministic on these tasks (U-shaped
  propensities, beta-binomial a = 0.099, b = 0.246 over S1a's 124 cells); n = 6 at K = 106 would cap
  at 9.03 GPU-h, and the census SE falls only from 1.16 to 0.95 pp with it.
- **Simulated operating characteristics** (`compute/power/power-v3.json`; 2,000 replicates per seed,
  seeds 42-44; propensities from S1a's records, the 44 tasks without records from the task-level
  fit; one session with a logit shift of SD 0.3; targets are relative effects on the census):

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

- **Reading.** The census interval covers the census truth in 0.94-0.95 of replicates in every
  structure. Among replicates whose census truth is beyond either margin, SMALL is declared in at
  most 0.051 at K = 106 and 0.056 at K = 89 (the nominal 5% of the TOST). v2's rule on the same data calls SMALL in 0.11-0.14 at a
  true 15% drop. Reshuffles (a direction-free decorrelation) leave the census mean at 0.0 pp and
  return SMALL in 0.82 (10% of tasks reshuffled) and 0.62 (30%); PRESENT of either sign fires in 0.25
  and 0.44 of them because the realized census effect is not zero, and the interval covers it.
- **Leakage and selection.** No task is selected on any outcome; the 44 dev and reserve tasks enter
  unscreened; all four cells are measured fresh in Phase 1. Moderator codings come from S1a's records
  and Phase 0's trees, frozen before any GPU job. The dev tasks shape only Phase 0's tolerances and
  remedies, which apply identically to all four cells.
- **Missing data and infrastructure.** Re-queue up to twice; a task enters if every cell has at least
  2 valid episodes; K2 and K3 make a run INCOMPLETE; K8 analyses complete blocks if at least 62.
- **Statistical reporting protocol.** K-Dense `statistical-analysis` and the ARS statistical
  reporting standards: effect sizes with intervals in both frames, paired and clustered errors,
  coverage checked by simulation, no HARKing (frames, margins and moderators registered before data).

## Compute and Reproducibility

Engine: vLLM v0.31.0 (commit `db9527a4`) on
`docker.io/vllm/vllm-openai@sha256:b18abb2df97b8f798e81862bd93f872ea18613372e2c3adc0cc2ac21e66ac12f`
with the cu129 overlay rebuilt from the freeze commit by `scripts/build_vllm_overlay_on_h100.sh`, as
S1a. Model: Qwen3.5-9B revision `c202236235762e1c871ad0ccb60c8ee5ba337b9a` (receipt `0a9e052d`). Agent
loop, harness adapters, VM lane and records: S1a's code of record (`harness/q2_stage1/`, freeze
`d5f5798`) plus the new cell selector, step-0 and keyboard checks and a lane version that accepts the
derived image (new code, reviewed before the freeze). Pilot container:
`cotcodec-q2-lo-vm@sha256:f5b4c40eefd2b92f846652910ba34db35e1ae7bf90fa474595cc745cc5895361`.

Pilot launch path (as run; CPU only, no GRES, one job at a time after `squeue` is empty):

```bash
sbatch --parsable --export=ALL,Q2M_MODE=run,Q2M_IMAGE_ID=sha256:f5b4c40eefd2b92f846652910ba34db35e1ae7bf90fa474595cc745cc5895361,Q2M_ARGV_JSON_HEX=$ARGV_HEX,Q2M_SOURCE=/home/kevin/cotcodec-runs/stage0/s2v3-phase0-pilot/src,Q2M_RUN_DIR=/home/kevin/cotcodec-runs/stage0/s2v3-phase0-pilot/run-b2,Q2M_INPUTS=/home/kevin/cotcodec-runs/stage0/q2-evaluator-mutation/inputs infra/slurm/host-single-node/s2v3-pilot-cpu.sbatch
```

Phase 1 launch path (as S1a; the manifest does not exist yet; dry run, test-only, submit on an empty
queue; one GPU job and its CPU VM job):

```bash
uv run --locked python scripts/submit_docker_research_job.py infra/slurm/host-single-node/s2-arabic-cua-locale-v3-phase1.yaml --dry-run
uv run --locked python scripts/submit_docker_research_job.py infra/slurm/host-single-node/s2-arabic-cua-locale-v3-phase1.yaml --test-only
uv run --locked python scripts/submit_docker_research_job.py infra/slurm/host-single-node/s2-arabic-cua-locale-v3-phase1.yaml
```

The submitter wraps `sbatch infra/slurm/host-single-node/docker-research.sbatch`. An orx node over a
committed `experiments/orx/node.yaml` does not exist for the pilot (the jobs ran through the CPU lane
directly), which the executable-pilot rule requires; disclosed under Compute.

Machine fields: seeds: [42, 43, 44]; gpu_hours: 7 (the ceiling of the registered 6.10 GPU-h: the
Phase 1 job cap of 6.00 at K = 106 plus the 0.1 GPU-h overlay reserve; 6.87 at the p95 slot price;
Phase 0 is 0; separate from the gauntlet's 0.3 GPU-h reviewer budget).

Cost model (`power-v3.json` `costs`): the Q2 design study's slot rule, s = 197.73 s at V = 20, cap
ceil(3 + L/60 + (N s / V + drain) x 1.2 x 1.05 / 60) + 6 minutes. K = 106: 1,696 episodes, 4.72
physical GPU-h at the high slot, 366 cap-minutes (6.10 GPU-h); K = 89: 5.15; K = 62: 3.67. Under S1a's
registered c_proj the same 1,696 episodes would be 19.1 GPU-h; the cap rule is Kevin's decision
(design study section 5).

Checkpoints and resume: as S1a, each episode is the unit of work, records are appended as episodes
finish, and a fresh job skips completed (task, cell, harness, rerun) keys and continues the seeded
order; preempted time counts against the cap (D22). Artifacts: per-episode records, the oracle
record, codings and the decision record in the public repository; screenshots and trajectories on
the host and in the private archive. Pilot artifacts: `compute/pilot/` (scripts, the exact scripts
each job ran, records, receipts, Slurm logs, the part-B analysis); screenshots stay on the host.

## Safety, Data Rights, and Monitorability

- **Safety.** The agent acts only inside offline VMs on public OSWorld tasks; it generates no code the
  host runs (D3, D7 not triggered). The pilot ran unprivileged containers with no network and no
  GPU device, on an empty queue, one at a time; no root and no docker-group escalation; `~/cotcodec`
  untouched.
- **Monitorability.** Every action, observation hash, token count, checker input hash and verdict is
  logged per episode, as in S1a; thinking traces kept. The pilot's records hash every screenshot.
- **Data rights.** OSWorld configs and checkers Apache-2.0; LibreOffice and `libreoffice-l10n-ar`
  MPL-2.0; Ubuntu language packs under their upstream licences (GTK LGPL-2.1); fonts already in the
  image (KACST GPL-2.0, DejaVu); Qwen3.5-9B Apache-2.0. The derived image and generated catalogs stay
  on the host and are not redistributed.
- **Outward actions.** None taken. The three package downloads and publishing the image or any
  screenshot are Kevin's call (D2).
- **Public-repo hygiene.** No host address, credentials or private data in any artefact (the
  committed records were scanned for addresses).

## Negative-Result Value

| Outcome | What it says | What it closes |
|---|---|---|
| K0 (fewer than 62 tasks pass Phase 0) | LibreOffice cannot be localized and mirrored to the oracle's standard on enough tasks without code changes; the leak and RTL-defect inventories say where | S2 on this stack; a public i18n record either way |
| K1 | The localized image breaks the certified action path | Phase 1 on this image |
| D SMALL (census) | Mirroring LibreOffice's interface changes this agent's success on OSWorld's LibreOffice tasks by less than 5 pp and less than 15% of the solve rate | The mirror half of the split for application-level localization on this benchmark; a publishable robustness null |
| D PRESENT_HARM, positional moderator named | A mirror cost that tracks target relocation | Points mitigation at grounding (position augmentation) |
| D PRESENT, unresolved; O8 defects large | A mirror cost possibly carried by RTL rendering defects | Separates "RTL is hard for agents" from "this RTL build is broken" |
| T PRESENT_HARM, lexical moderator named | An Arabic-interface cost that tracks lost instruction-label overlap | Points at lexical matching, not glyph reading |
| PRESENT in the census, not in the population frame | An effect on these tasks that does not generalize with confidence | Sizes a successor |
| INCONCLUSIVE | Nothing beyond the intervals | Sizes a successor |

## Preflight Doctors

| Doctor | Status | Evidence | Remediation |
|---|---|---|---|
| Source | PASS | orx alphaXiv and OpenAlex reachable from the Mac; 71 counted orx discover queries (92 with ACL Anthology and OpenReview) with returned ids and raw-output hashes; Semantic Scholar citer lists; cutoff 2026-10-11; degraded coverage recorded (no Chinese query, social media, Google Scholar) (`doctors/source.json`) | A Chinese-language query and a RealGUINoise revision check before any write-up |
| Citation | PASS | Claim registry C01-C38 with locators, dates and read status; primary URLs snapshotted with HTTP status and hash; source claims with line numbers at 7.3.7.2; pilot claims tied to job records and receipts (`doctors/citation.json`) | Read ITDroid and RotDroid in full if a delta row comes to rest on them |
| Novelty | FAIL | No direct prior under the recorded coverage (NO_DIRECT_PRIOR_FOUND, STILL_OPEN), but this wave's blind critic and novelty refuter have not run (`doctors/novelty.json`) | Run the blind critic on `blind/` and the novelty refuter (at least 58 queries remain) |
| Design | PASS | Intervention (system-layer selector), controls (en baseline; O1-O8 with positive controls; P0.8-P0.11; step-0 and keyboard checks), falsifiers P1-P7 and kill criteria K0-K8, primary estimand D with a census-frame three-way decision and a dual margin, design before data on S1a's measured records with simulated operating characteristics under seven effect structures (`doctors/design.json`) | Re-run the simulation with real-Arabic Phase 0 inputs (Arabic chrome share, defect counts) before the freeze |
| Compute | FAIL | A partial executable pilot (jobs 1097-1100, receipts) exists, but no derived image, no VM-lane oracle, no delta certification, no Phase 1 manifest, no Slurm dry run of Phase 1, no orx node (`doctors/compute.json`, `compute/attestations.md`) | Kevin's go-ahead for the downloads; the image-surgery and lane code reviewed; then Phase 0 in the lane and the Phase 1 manifest's dry run and test-only |
| Safety | PASS | Offline VMs and containers, public tasks, no host-run model code, licences recorded, no outward actions, host rule respected (`doctors/safety.json`) | none |

Protocols followed: Citation, the ARS claim-verification protocol (claim registry, locators,
verdicts); Design, the vendored K-Dense `experimental-design` and `statistical-power` skills (design
before data; a 2x2 blocked by task and session; power by simulation of the registered estimator on
measured inputs); Evaluation, K-Dense `statistical-analysis`; Novelty, K-Dense `literature-review`
(PRISMA counts in the header). The integrity gate's seven failure modes are answered in the
registration.

## Independent Adversarial Reviews

Reviewer A: FAIL | provider=not-run | model=not-run | run_id=not-run | artifact=none (this wave's reviewers run after the blind critic and the refute-first triad)

Reviewer B: FAIL | provider=not-run | model=not-run | run_id=not-run | artifact=none (the open-weight reviewer's lane job runs only on an empty queue)

No review is signed: no trusted Ed25519 store exists (D24).

## Scorecard

| Dimension | Reviewer A | Reviewer B | Defect/evidence |
|---|---:|---:|---|
| Question and strategic fit | 0 | 0 | not yet reviewed (S2 run 2: 7 and 6) |
| Primary-source evidence | 0 | 0 | not yet reviewed |
| Defensible novelty delta | 0 | 0 | not yet reviewed |
| Mechanism and falsifiability | 0 | 0 | not yet reviewed |
| Controls and causal identification | 0 | 0 | not yet reviewed |
| Evaluation and statistics | 0 | 0 | not yet reviewed |
| Feasibility and information per GPU-hour | 0 | 0 | not yet reviewed |
| Reproducibility and artifact contract | 0 | 0 | not yet reviewed |
| Safety, data rights, and monitorability | 0 | 0 | not yet reviewed |
| Independent adversarial review quality | 0 | 0 | not yet reviewed |
| **Total** | **0** | **0** | Lower total is authoritative (S2 v2: 49, then 59) |

## Iteration Log

| Wave | Score | Highest-impact defect | Change | Result |
|---:|---:|---|---|---|
| dossier (2026-10-06) | not scored | String swap cannot hold layout fixed; Relay not internationalized | Corrected question and kill lines | dossier section 5 |
| S2 v1 wave 1 (2026-10-10) | 49 | Relay's 18 tasks cannot power Phase 1 | moved to OSWorld (D68) | gauntlet row `1a24cee8...` |
| S2 v2 run 2 (2026-10-11) | 59 | SMALL unreachable at K = 26-31; heterogeneous power 0.45 | honest exit (D68, D70) | gauntlet row 2 |
| S2 v3 synthesis (2026-10-11) | not scored | as v2 run 2 | census of 106 tasks, census frame and dual margin, no selection, executed switch and content probes, extended delta suite, new kill criteria | awaiting this wave's blind critic, triad and reviewers |

## Deterministic Doctor Output

Verbatim output of `uv run python scripts/research_direction_doctor.py
program/proposals/2026-10-11-s2v3-arabic-cua-locale-pilot.md` on the committed bundle, also stored as
`evidence/2026-10-11-s2v3-arabic-cua-locale-pilot/doctors/research-direction-doctor-output.json`.
Readings the doctor does not make for itself, as in S2 v2: "all declared budgets must be positive"
comes from parsing the declared `gpu_hours=0.3` as an integer (the budget is honest and is not
rounded up to pass); the doctor applies no 79 cap because its executable-pilot check is textual,
while by the gauntlet rule's cap table this proposal stays capped at 79 (the pilot is partial: no
derived image, no VM lane, no orx node) and 89 (no signed, provider-distinct review), and cannot
reach 100 without D24's trust store.

Exit code 1.

```json
{
  "acceptedScore": 0,
  "doctorStatus": {
    "Citation": "PASS",
    "Compute": "FAIL",
    "Design": "PASS",
    "Novelty": "FAIL",
    "Safety": "PASS",
    "Source": "PASS"
  },
  "evidenceBundleLoaded": true,
  "hardCaps": [
    89
  ],
  "issues": [
    "all declared budgets must be positive",
    "Novelty doctor lacks PASS plus concrete evidence",
    "Compute doctor lacks PASS plus concrete evidence",
    "Reviewer A lacks structured PASS attestation",
    "Reviewer B lacks structured PASS attestation",
    "evidence bundle requires exactly two review artifacts",
    "protected external trust store is not configured; set COTCODEC_TRUSTED_ATTESTORS_PATH in trusted CI",
    "reviewers must use different providers; degraded review cannot score 100",
    "reviewers must have distinct nonempty run IDs",
    "two distinct trusted reviewer signatures are required for 100",
    "compute attestation says the real model loop is not executable",
    "compute attestation lacks a non-stub benchmark adapter",
    "compute benchmark_adapter path does not exist",
    "repository real model loop is still a stub",
    "compute lacks a hashed Slurm manifest",
    "compute slurm_test did not pass",
    "compute provenance_verification did not pass",
    "doctor artifact 2 did not pass",
    "doctor artifact 4 did not pass",
    "evidence bundle lacks audit_log artifact"
  ],
  "path": "/Users/kevinliu/repos/cotcodec-wt-gauntlet-s2v3/program/proposals/2026-10-11-s2v3-arabic-cua-locale-pilot.md",
  "remediation": [
    "all declared budgets must be positive"
  ],
  "reviewerTotals": {
    "A": 0,
    "B": 0
  },
  "sourceCounts": {
    "allUrls": 28,
    "recognizedPrimaryUrls": 15
  },
  "status": "FAIL"
}
```
