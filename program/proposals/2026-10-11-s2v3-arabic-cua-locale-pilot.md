# Research Direction: S2 v3 first step, Arabic interface text versus mirrored layout on the certified OSWorld stack (Phase 0 as an executable CPU pilot on the real LibreOffice, and a Phase 1 census of OSWorld's LibreOffice tasks under 8 GPU-h)

**Status:** repair after gauntlet wave 1 (score 60, decision D74), a fresh S2 v3 gauntlet run with new budgets, written on 2026-10-11 by a Claude agent as the single owner on branch `gauntlet/s2v3-locale` (main merged at `b2bb87e`). Wave 1's record is the first row of `program/gauntlet/2026-10-11-s2v3-arabic-cua-locale-pilot.jsonl` (hash `8b0c6ef5...`); the wave-1 proposal text is commit `4d8e17e`. The updated draft registration is `program/preregistrations/s2-arabic-cua-locale-v3.1.md` (v3 left unedited; DRAFT, not frozen, no ledger row). Phase 0 was completed on what the CPU lane can run: every cell (en-LTR, ar-LTR, en-RTL, ar-RTL, a placebo, a tagged cell, stock and an A/A replicate) at every candidate task's post-setup state with a generated pseudo-Arabic catalog (Slurm 1131), the registered render oracle with planted controls (orx node `c7bcde07`, run `9e78b49f`, receipt `compute/pilot-r1/orx-node/`; replicated as Slurm 1132), and a checker-invariance test of every cell on the tasks' golds and do-nothing states (Slurm 1139 and 1141). K0 under the rules committed before the sweep: FAIL; under the registration's checker-based admission: 105 of 106 admitted (see "Changes after wave 1"). K1 is not decided: it needs the VM lane on the derived image. Phase 1's caps are 6.83 GPU-h (below 8). Phase 1's admission is Kevin's ruling under D24 and D70, the language-pack downloads are his to approve, and a score of 100 cannot be certified in this repository (D24)
**Owner:** Kevin Liu (program owner); synthesis, pilot, simulations and draft registration by a Claude agent acting as the single owner
**Source cutoff:** 2026-10-11
**Coverage limits:** This wave's retrieval is the three discovery cells plus the owner's synthesis queries, all recorded in `evidence/2026-10-11-s2v3-arabic-cua-locale-pilot/query-log.json`. Frontier scout: 35 orx discover calls (25 keyword including title-phrase queries for macOSWorld, RealGUINoise, MPR-GUI, VAF and Left-Right Symmetry Breaking; 7 embedding; 4 OpenAlex), 13 OpenReview API searches (6 restricted to ICLR 2027, one scanned in full: 210 'multilingual' submissions), 4 ACL Anthology regex searches over 131,473 entries, Semantic Scholar citer lists for macOSWorld (34), MPR-GUI (5), RealGUINoise (0) and VAF (5), 2 arXiv version checks (24 ids), 3 web searches and 1 patent fetch; 22 full-text reads. Kill-shot scout: 15 orx discover calls, 4 full-text reads, 3 ACL Anthology regex searches (one too broad, 40 of 274 titles scanned), degraded anonymous OpenReview access, source reads of LibreOffice 7.3.7.2, read-only host reads of the VM rootfs and OSWorld at `b138d348`. Cross-domain scout: 18 orx discover calls, 5 orx paper reads, 11 web searches, 10 page fetches, 6 Bugzilla records. Owner: 3 orx discover calls and 1 full read (2411.00640). Repair run (this run, `compute/pilot-r1/queries/repair-queries.json`): 6 orx discover calls (two Chinese-language keyword queries, an embedding query with the repaired mechanism, a placebo-perturbation keyword query, a keyword query after 2026-09-01, an OpenAlex query) and 3 GitHub searches (two repository searches, one code search for the direction key), all with raw-output hashes and returned ids, and full reads of 2609.33012 and 2608.25425 (RotDroid). Not searched: Google Scholar, X, Reddit, Hacker News, Chinese-language venues (the two Chinese orx queries returned nothing on topic; orx has no CJK-capable venue index), ACM DL and IEEE Xplore full text, EMNLP 2026 proceedings (not yet in the Anthology), patents beyond one Google Patents page. orx is 0.2.2 (reports itself outdated against 0.2.18). PRISMA-style for this wave: 1,493 returned ids recorded (1,047 unique; OpenReview lists truncated at 25 per query in the log), screened by title or abstract; 32 paper reads beyond the abstract (22 frontier, 4 kill-shot, 5 cross-domain, 1 owner; some overlap); 0 direct priors
**Budgets:** queries=80; wall_minutes=600; tokens=8000000; dollars=150; waves=1; gpu_hours=0.3
**Novelty verdict:** NO_DIRECT_PRIOR_FOUND
**Safety verdict:** PASS
**Evidence bundle:** evidence/2026-10-11-s2v3-arabic-cua-locale-pilot/bundle.json

The budgets are this fresh run's (D74), cumulative over the repair, the triad, the reviewers and the
recorder: queries 80 with at least 30 reserved for the three refuters, wall 600 minutes, tokens 8,000,000,
dollars 150, one wave, 0.3 GPU-h for the open-weight reviewer's lane job only. The repair owner spent
9 counted queries (6 orx discover, 3 GitHub searches; one malformed orx call that reached no backend is
logged, not counted) and 2 full-text reads; wave 1's counts (127 queries) are its own and not carried.
The repair used 0 GPU-h: every host job was a CPU-only Slurm job with no GRES, submitted after a
`squeue` check, one at a time (other workstreams' CPU jobs ran beside them; no VM-lane campaign of
this run). The novelty verdict field uses the doctor's vocabulary; the merged kill-shot verdict is
STILL_OPEN.

## Changes after wave 1

Wave 1 scored 60 (Claude 61, open-weight 60; record `8b0c6ef5...`); blind discrimination passed; the
refute-first triad refuted 3 of 3. Its largest defect (both reviewers, the feasibility refuter): the
CPU pilot exercised only the layout switch, so Phase 0 decided neither K0 nor K1. D74 asked one
repair run to complete the pilot on what the CPU lane can run. What changed, and what it showed:

| # | Wave-1 defect (who) | Repair | Result | Evidence |
|---:|---|---|---|---|
| 1 | The text factor never ran: no Arabic catalog rendered, the "pseudo-Arabic" cell fell back to English, ar-LTR only on blank documents (reviewer 1, feasibility refuter) | A pseudo-Arabic interface generated in the job from the installed build's own English strings (no download): 13,226 exact dialog keys, 155,390 candidate code-string keys, 5,580 registry labels, Arabic letters of matched length with placeholders, mnemonics, digits and acronyms kept; shortcut tables and command URLs never transformed. Every cell, ar-LTR included, at every candidate task's post-setup state | 1,022 renders (106 tasks x 9 cells, 17 dev tasks x 4 more), 0 errors; median 0.93 of named chrome in Arabic script in the ar cells (minimum 0.91); 93% of tagged chrome covered | Slurm 1131; `compute/pilot-r1/capture-1131/` |
| 2 | The registered oracle not implemented (O2, O3 on pixel boxes, O6, planted controls); O5 not discriminative (reviewer 1, recorder) | `harness/s2_locale/oracle.py`: boxes located from ink (accessibility extents only in LTR cells, VCL's vertical offset estimated on the dev tasks), O2 as whole-run pixel identity, O3 against a mirror specification frozen on the dev tasks (tol3 = 20 px), O5 by full-width alignment with a flipped comparison, O6 against a stock cell, in-application and synthetic planted positive controls, and negative controls (A/A replicates, stock against en-LTR, synthetic fixtures) that must pass | O6: 0 differing pixels on 106/106; O1 text structure identical 212/212; O4 943/943; P7 106/106 within tolerance (98 identical; 8 differ in one 11 x 5 px spot, 28 px); A/A 106/106 at 0 px; O3: 84% of chrome elements within tol3 of their reflection, 94% located in their row; O5: the document is not mirrored for en-RTL on 105/106 (the flipped document differs by at least 7,759 px everywhere), and the Arabic interface changes the slide in 14 of 40 Impress tasks (localized placeholder prompts) | orx node `c7bcde07` run `9e78b49f`; Slurm 1132 replicate |
| 3 | Selector tested in an extra layer, not `/etc/libreoffice/registry` (reviewer 1, feasibility refuter) | The selector in a copy of the system layer that both of its layer entries read (only the path differs) | Recorded per render | capture 1131 |
| 4 | The cells differ in more than one file (`LANGUAGE=ar`, identification refuter) | Dropped; the interface language set by both of its keys (`ooLocale`, `UILocale`): with `ooLocale` alone the registry labels stay English (debug 1123), a defect the wave-1 cell L4 also had | One selector file between Phase 1 cells | debug 1123, capture 1131 |
| 5 | K0 and K1 undecided | K0 decided twice (below); K1's CPU-lane parts decided, the rest scoped | K0 under the rules committed before the sweep: **FAIL** (53 admitted by a file-identity and content-leak proxy stricter than the registration; synthetic plants caught 101/106 for O3 and 95/106 for O2 against a 100% bar). Under the registration's own checker semantics (a leak excludes only if the checker reads it): **105 of 106 admitted**; no cell changes any checker verdict on any task's gold or do-nothing state (1,110 scored saves) | Slurm 1139, 1141; `compute/pilot-r1/admitted-checker-invariance.json` |
| 6 | The census truth of D includes direction-free change; no comparator (identification refuter) | A fifth cell, PL: the en-LTR interface with every toolbar's items in a fixed seeded order (a window-state pin did not move toolbars, debug 1123); P3 read as a total effect with no mechanism; a mechanism may be named only if en-RTL is worse than PL across tasks (population frame) | Simulated false MIRROR_SPECIFIC 0.023-0.027 under every direction-free scenario (0.068-0.143 if the census frame were used); power 0.37-0.56 at a mirror-only 15% harm with n_pl = 2. The placebo moved 53% of chrome elements by a median 271 px (mirroring: all, 991 px): it controls for rearranging the toolbars, not for an equally large change | `compute/power-v4/`, oracle E-PL |
| 7 | Sharp-null variance v instead of 4v; PRESENT_FRAGILE disabled (reviewer 1, refuter, recorder) | 4v | Rejection 0.048 at the exact null (v3: 0.32); PRESENT_FRAGILE 0.006 | `power-v4.json` |
| 8 | Admission conditioned on how the treatment renders (O1-O7 in all cells; discretionary remedies; recorder's defect 2) | Intention to treat: only agent-independent failures exclude (setup, window title, save, checker invariance); O2, O3, O5 and O8 are descriptors and moderators; D also reported on all 106 | 1 exclusion | registration v3.1 |
| 9 | Moderator P0.12a coded every click as a reflection; O8 constant across tasks; no baseline covariate (refuter) | Chrome and document clicks separately (documents shift, they are not reflected); O8 per task (15-23 elements outside the specification); baseline success as a covariate | | registration v3.1 P0.12 |
| 10 | `compare_pptx_files` order defect not carried (recorder's defect 6) | Sensitivity analysis without its 43 tasks | | registration v3.1 |
| 11 | Overstatements: "documents stay unmirrored", P7's numbers, job list (reviewer 1, recorder) | Backed or restated: O5 now measures it; P7 now compares the language-default RTL cell with the key RTL cell (within tolerance on 106/106: 98 identical, 8 differing in one 28-pixel spot); headers cite the jobs that produced each number; fresh blind paragraphs say what has and has not run | | `blind/paragraph-84279667.txt` |
| 12 | Novelty a measurement delta; "Why now" framed as macOSWorld's open split; coverage gaps (novelty refuter, reviewers) | Restated as a measurement on a narrower object; 6 new orx queries (two in Chinese, nothing usable), 3 GitHub searches (no agent study), full reads of 2609.33012 and RotDroid | No direct prior found | `compute/pilot-r1/queries/` |
| 13 | No orx node (79 cap) | A `cpu-doctor` node runs the oracle over the committed manifest | PHASE0_K0_FAIL; 11 of 13 cases pass (c04 planted controls and c10 the committed admission fail; c13, admission under checker invariance, passes with 105); `ORX_RESULT ... exit=0` in 1,897 s; every gate, admission and instrument verdict equals the host replicate 1132 (descriptors such as text-run identity differ by about one point through floating-point ties) | orx node `c7bcde07` |

Not repaired, and why:
- The shipped Arabic catalogs, the derived image and the VM lane: the three package downloads wait on
  Kevin (D74). The stand-in is not the shipped catalog: it transforms every localized registry value
  (except the window-title factory names, which the shipped catalog also leaves in English) and misses
  code strings its key heuristic does not pair, so the leak, coverage and O5 numbers are the
  stand-in's; Phase 0 proper repeats them with the shipped catalog.
- K1 (P0.6): C1-C4, A1 at N = 1 and A5 need the five cell overlays in the VM lane (about 25 VM-hours;
  with A2, A3, A6 and the V = 20 rung about 44), plus reviewed image-surgery and lane code and a
  registered deviation of `q2-action-path-v2`.
- I1's synthetic-plant bar: the committed 100% was not met (look-alike neighbours inside the locating
  window are a plausible cause, not verified); Phase 0 proper fixes a bar or a uniqueness test before
  it runs.
- The placebo's magnitude (above), signed reviews (cap 89) and the cap rule (Kevin's).

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

**This step.** Phase 0 (CPU only): (a) the enlarged task pool, frozen; (b) the derived image with
LibreOffice's shipped Arabic interface, the separate layout switch and five cell overlays; (c) the
factorial render oracle and the checker-invariance test at every candidate task's post-setup state;
(d) the delta certification of the action path (K1). Plus the design of Phase 1 under 8 GPU-h. In
this repair, (c) ran in the CPU lane on the certified VM's userland with a generated stand-in catalog
and decided K0 as described under "Changes after wave 1"; (b) and (d) need the downloads and the VM
lane.

**Variable.** The cell: the application's interface language (`ooLocale` and `UILocale`, both `en-US`
or both `ar`) and its layout key (`UIMirroring` false or true), all finalized in the system
configuration layer; a fifth cell (PL) keeps the en-LTR selector and reorders each toolbar's items.

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
- **Why now.** macOSWorld's latest version (v4, 2025-10-18) leaves its own split open ("the visual
  complexity of Arabic glyphs or the mirrored UI layout, or both", Sec. 5.2) for whole-OS
  localization; none of its 34 Semantic Scholar citers takes it up, MacArena dropped the language axis,
  and no ICLR 2027 'multilingual' submission renders a localized GUI. S2 does not answer that split. It
  measures a narrower object that can be measured cleanly now: application-level localization of one
  office suite over an English shell, on the benchmark people run, paired within task and session,
  with each cell certified before any model runs. The cross-lingual agent gap is documented for
  instruction language (OmnilingualGAIA2: 8.8-18.4 points pass@3), not for the interface an agent sees.
- **What it buys.** A census claim about OSWorld's LibreOffice tasks, decisive in both directions
  (SMALL reachable, a 15% relative harm detected with probability 0.86-0.96), with a placebo that
  says whether a mirror cost exceeds the agent's sensitivity to rearranging its toolbars. The Phase 0
  machinery (the generated-catalog instrument, the oracle, the checker-invariance test, the leak and
  RTL-defect inventories) is reusable at an infrastructure exit; the pilot already shows that an
  Arabic interface writes localized defaults into saved documents and that no checker on these tasks
  reads them.
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
| C11 | Cross-orientation state-equivalence testing with paired-state oracles (a fine-tuned VLM judges paired portrait-landscape states; 94 bugs reported) | [RotDroid, ISSRE 2026](https://arxiv.org/abs/2608.25425) | full text (repair run) |
| C12 | i18n testing mapping study: 24 primary studies, layout bugs one of four categories, six tools | [IST 2026](https://doi.org/10.1016/j.infsof.2026.108258) | abstract |
| C13 | A true RTL layout is a mirror plus restoration of forward-oriented elements, not a pixel flip | US12008219B2 (ByteDance), granted 2024-06-11 (Google Patents summary) | summary |
| C14 | Qwen-UI-Agent: 79.5% on OSWorld-Verified; no Arabic or multilingual evaluation | [Qwen-UI-Agent report](https://arxiv.org/abs/2607.28227), 2026-07-30 | full text (first-party number) |
| C15 | With stimuli random, power plateaus as participants grow | [Westfall, Kenny and Judd 2014](https://doi.org/10.1037/xge0000014) | abstract |
| C16 | Zero events in n: 95% upper bound 1 - 0.05^(1/n) (rule of three) | [Hanley and Lippman-Hand 1983](https://doi.org/10.1001/jama.249.13.1743) | abstract |
| C17 | Freedom-from-disease surveys: finite-population (hypergeometric) design with imperfect tests | [Cameron and Baldock 1998](https://doi.org/10.1016/S0167-5877(97)00081-0) | metadata |
| C18 | Evals as samples from a super-population; clustered errors; the fixed-question view is the alternative | [Adding Error Bars to Evals](https://arxiv.org/abs/2411.00640), Sec. 2 | full text (owner) |
| C19 | If the board and outcomes are fixed, the mean is an exact summary and any interval must come from another declared source of randomness; a population interval needs the entries as draws | [When Pair Count Is Not the Sample Size](https://arxiv.org/abs/2609.33012), 2026-09, Sec. 3 | full text (repair run) |
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

Repair-run claims (each tied to a CPU-only Slurm job's receipt and record under `compute/pilot-r1/`):

| Id | Claim | Source | Read |
|---|---|---|---|
| C40 | With `ooLocale` alone the gettext strings switch to the requested UI language while every registry label (menus, commands, toolbars) stays English; adding `Linguistic/General/UILocale` switches them | debug 1123 (`slurm/…-1123.out`), smoke 1124 | pilot |
| C41 | Transforming the keyboard-shortcut table's localized values (command URLs) breaks Ctrl+S in the transformed language; excluded from the generator | debug 1123 | pilot |
| C42 | Pinning `ooSetupSystemLocale` to en-US changes Calc's saved default paper (A4 to Letter) against the stock profile | smoke 1124, saved `sheet1.xml` | pilot |
| C43 | A finalized window-state `DockingArea` in the system layer does not move the toolbars (three forms) | debug 1123 | pilot |
| C44 | Capture: 106 tasks x 9 cells and 17 dev tasks x 4 cells, 1,022 renders, 0 errors, all stable, every postconfig save written, `setxkbmap` reports `us` | capture 1131 | pilot |
| C45 | The generated catalogs: 13,226 `.ui` keys, 155,390 candidate code keys (168,616 entries), 5,580 registry labels, matched length on every string; median 0.93 of named chrome in Arabic script in the ar cells | capture 1131 `catalog-stats.json`; oracle | pilot |
| C46 | O6, O1 text pairs, O4, P7 and A/A pass on every task (0 differing pixels for O6 and A/A on every task; P7 0 on 98 tasks and 28 px in one small spot on 8) | orx node; Slurm 1132 | pilot |
| C47 | Mirroring: 84% of chrome elements within 20 px of their reflection, 94% located in their row; the document is not mirrored for en-RTL on 105/106 tasks (flipped differs by at least 7,759 px) | oracle | pilot |
| C48 | In 14 of 40 Impress tasks the Arabic interface changes the slide (empty placeholders show localized prompts, right-to-left) | oracle O5 | pilot |
| C49 | Localized defaults reach saved files in the ar cells (Impress slide and notes masters, Writer style names, Calc header and footer defaults: 34 tasks; 53 in the tagged cell); in Writer a localized style display name also changes the saved style identifier (e.g. `FrameContents` becomes `Style9`) | oracle `content_leaks`; saved files of 1131 | pilot |
| C50 | Golds (88) and do-nothing states (97), each saved in S, E, A, ER, AR and PL, get the same checker verdict in all six cells for every task (1,110 verdicts) | Slurm 1139, 1141 | pilot |
| C51 | K0 under the rules committed before the sweep: FAIL (53 admitted; synthetic plants 101/106 O3, 95/106 O2); under checker invariance 105 of 106 admitted | orx node, Slurm 1132, `admitted-checker-invariance.json` | pilot |
| C52 | The placebo moves 53% of chrome elements by a median per-task mean of 271 px; mirroring moves all, 991 px (orx node; the host replicate: 264 and 996) | oracle E-PL against E-ER | pilot |

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
the owner's 3 orx discover queries and 1 full read; and this repair run's 6 orx discover queries (two in Chinese), 3 GitHub searches and 2 full reads. Every query and returned id is in `query-log.json` and `compute/pilot-r1/queries/repair-queries.json`.
The residual is narrow and is a measurement, not a method: a paired, render-certified split of
application-level localization into text and direction on an executable benchmark, with a
direction-free placebo, for one model. It is narrower than macOSWorld's open whole-OS split and does
not answer it. The census frame, the oracle, the isolation
mechanism, the off-diagonal cells and the paired-variant method are prior art used as
infrastructure.

## Mechanism and Falsifiable Predictions

**Instrument.** A derived image of the certified OSWorld image adds LibreOffice's shipped Arabic
catalogs and GTK's Arabic strings. One selector file in the system configuration layer sets the
interface language (both of its keys, `ooLocale` and `UILocale`) and the layout key (`UIMirroring`),
all finalized, so the Phase 1 cells differ in exactly that file; a fifth cell (PL) keeps the
en-LTR selector and puts each toolbar's items in a fixed seeded order. The CPU pilot ran this
instrument in the certified VM's LibreOffice userland with a generated Arabic-script stand-in
catalog, at every candidate task's post-setup state: the English configuration is invisible against
stock (identical pixels on 106 of 106 tasks), the key mirrors the chrome (84% of elements within the
mirror specification of their reflection) while the document stays unmirrored (O5: en-RTL passes on
105 of 106, the flipped document never matches), and no cell changes any checker verdict on a gold or
a do-nothing state. Phase 0 proper reruns the oracle and the checker-invariance test on the derived
image in the measurement lane and re-certifies the input path there (P0.6).

**Hypothesized causes.** Mirroring could lower success through (i) target relocation into regions
where the model grounds worse (ScreenHaystack) and (ii) left-to-right priors about menus, toolbars
and panels that mislead planning (macOSWorld's Settings anecdote), and through (v) RTL-only
rendering defects that are part of real RTL LibreOffice (the clipped status bar the pilot found).
Arabic interface text could lower success through (iii) weaker reading of Arabic glyphs and Arabic
UI digits and (iv) lost word overlap between English instructions and interface labels.

**Predictions (registration v3.1), each with a reachable falsifier:** P1, Phase 0 admits at least 62
tasks (falsifier K0; the pilot admitted 105 under checker invariance, 53 under the committed proxy);
P2, the delta certification passes (K1; not yet run); P3, D < 0, read as a total effect on these tasks
with no mechanism attached (falsified by census SMALL or PRESENT_BENEFIT; simulated SMALL at a true
null 0.97); P4, T < 0 (same); P5 and P6, negative moderator slopes for positional exposure (D; chrome
and document clicks separately, baseline success as a covariate) and lexical overlap (T), named only
on a 95% CR2 interval below 0; P7, the language-default RTL cell equals the key RTL cell (pilot: within
tolerance on 106 of 106; 98 identical); P8, the mirror cost exceeds the toolbar rearrangement's (E_dir < 0; falsified by
NO_EXCESS in the population frame).

**Kill criteria:** K0 fewer than 62 admitted tasks or a failed instrument check (infrastructure
exit); K1 a failed delta certification; K2 more than 5% infrastructure losses in a cell; K3 more than
2% step-0 failures in a cell; K4 English census success outside [0.15, 0.85]; K5 a confidently
degraded English cell (no SMALL claim); K6 D and T both SMALL and neither PRESENT (publish the
robustness null); K7 neither PRESENT (no reasoning-language arm); K8 cap reached (analyse complete
blocks if at least 62); K9 D PRESENT_HARM without MIRROR_SPECIFIC (D reported as a net change; no
mechanism row of the Negative-Result table claimed).

## Cheapest Decisive Pilot

**Wave 1 (jobs 1097-1100)** exercised the layout switch's mechanics on blank documents and at 106
post-open states with an English-fallback "pseudo-Arabic" cell; it decided neither K0 nor K1
(`compute/pilot/`, `compute/attestations.md`).

**This repair (CPU only, 0 GPU-h, `compute/pilot-r1/`).** Every job a CPU-only Slurm job with no GRES,
submitted after a queue check, one of this run's jobs at a time, through
`infra/slurm/host-single-node/s2v3-pilot-cpu.sbatch` (the D12 CPU lane: `--network=none`, read-only
root, no capabilities, the host user's uid, a GPU-device preflight):

| Job | What | Result |
|---|---|---|
| 1116, 1120, 1123, 1124 | smoke and debug on dev tasks | four instrument defects found and fixed before the sweep: registry labels need `UILocale` (C40); transformed shortcut tables broke Ctrl+S (C41); icon-theme symlinks dangled in the private copy; the `ooSetupSystemLocale` pin changed saved paper size (C42); a window-state pin does not move toolbars (C43) |
| 1129 | sweep, cancelled after 94 renders | the paper-size pin |
| 1131 | the sweep: 106 tasks x {S, E, E2, A, ER, AR, AD, Q, PL}, 17 dev tasks x {ER2, PCL, PCR, PD}; per render the post-setup screenshot, accessibility dump, window list, the task's own postconfig save and the saved result file | 1,022 renders in 15.4 min, 0 errors (C44) |
| orx node `c7bcde07`, run `9e78b49f` | `scripts/run_s2v3_phase0_doctor.py`: the oracle over the captures, every file checked against the committed manifest | PHASE0_K0_FAIL; 11 of 13 cases pass (c04 planted controls and c10 the committed admission fail; c13, admission under checker invariance, passes with 105); `ORX_RESULT ... exit=0` in 1,897 s; every gate, admission and instrument verdict equals the host replicate 1132 (descriptors such as text-run identity differ by about one point through floating-point ties) |
| 1132 | the same doctor in the host CPU lane (replicate) | PHASE0_K0_FAIL under the committed rules; I2-I6 pass; 53 admitted by the proxy |
| 1139, 1141 | checker invariance: golds and do-nothing states saved in six cells, scored by the real OSWorld checkers in the metric container | no verdict changes in any task (C50); 105 of 106 admitted under the registration's semantics |
| 1142 | `power-v4.py` | the tables under Evaluation |

**K0, decided.** Under the rules committed before the sweep (`phase0.py` at `c8669d2`): FAIL. Its
admission proxy excluded any saved-file difference or content leak (53 admitted), stricter than the
registration's P0.8b and P0.9, which exclude a leak only if the checker reads it; and its I1 required
every synthetic plant to be caught (O3 101 of 106, O2 95 of 106; the in-application coupled string was
flagged on 17 of 17 dev tasks and the document change on all 15 where it was on screen). Under the
registration's semantics, operationalized after the proxy's result by checker invariance: 105 of 106
admitted; the one exclusion (`2cd43775`) has window titles that differ across cells. The residual K0
failure is the oracle's planted-control sensitivity against a 100% bar.

**K1, scoped.** Decided on the CPU lane: the keyboard map (`us` in every worker), the postconfig
activation and save path in every cell for every task, and identical saved files from the dev tasks'
keyboard edit probe across en-RTL, the placebo and the replicate (in the ar cells the typed content is
the same; localized style names and identifiers differ, and no checker verdict changes). Remaining for Phase 1's go-ahead: C1-C4, A1 at N = 1 and A5 on the five
cell overlays (about 25 VM-hours), A2, A3, A6 and the V = 20 rung (about 19 more), after Kevin approves
the downloads, the image-surgery script and the per-slot overlay lane change pass review, and a
deviation of `q2-action-path-v2` is registered; then the oracle and checker invariance again on the
overlays with the shipped catalogs.

**Limits of the container pilot.** The stand-in catalog is not the shipped one (it translates more
registry strings and misses code strings its heuristic does not pair); the window's bottom edge sits
3-4 px below the screen under openbox, so status-bar fields are partly cut in every cell; welded GTK
panels escape the KeyID tags.

**Phase 1 (one GPU job, cap 6.83 GPU-h at K = 106).** Qwen3.5-9B on the admitted census in five
cells: the 2x2 at n = 4 per task-cell split across both harnesses and PL at n = 2, one session at
V = 20 (1,908 episodes at K = 106).

## Controls, Baselines, and Ablations

- **Within-environment controls.** en is the baseline; ar-LTR changes only the text; en-RTL only the
  layout; ar-RTL both; PL rearranges the toolbars without a change of direction (a smaller
  rearrangement than mirroring: 53% of chrome elements moved by a median 271 px against all by
  991 px). Every cell of a task runs in one serving session, interleaved in seeded task blocks, cells
  assigned to VM slots at random within each batch, both harnesses equally.
- **Manipulation checks before any GPU job.** O1-O8 with planted controls (P0.7), the tagged KeyID cell
  (P0.8), the postconfig save and the keyboard edit probe in every cell, checker invariance on golds and
  do-nothing states (P0.9), config invariance (P0.10), offline setup (P0.11); per episode, the step-0
  screen and the keyboard map.
- **Held fixed.** Instructions, documents and checkers (English); the system shell; `ooSetupSystemLocale`
  at its default (the system locale, the same in every cell); SheetPrefix; CTLFont; Calc's English
  function names; autocorrect; the keyboard map; model, decoding, step cap, settles and harness prompts.
- **Baselines not used.** macOSWorld's numbers are context. S1a's English records are a reference for
  the English cell (K5), not a control.
- **Deferred ablations.** A rearrangement matched to mirroring in magnitude (toolbars, top-level menus
  and sidebar together), reasoning and instruction language, other languages, full-OS localization, a
  second model (Qwen3.5-4B), the accessibility observation setting.

## Evaluation, Statistics, and Leakage Checks

- **Primary estimand.** D = mean over tasks of D_t = ((y_arR - y_arL) + (y_enR - y_en)) / 2, cell means
  over n = 4 episodes (2 per harness); companion ratio R_D = S_RTL / S_LTR. Placebo contrasts: P =
  mean_t (y_PL - y_en) and E_dir = mean_t (y_enR - y_PL). Secondary: T and R_T, the interaction, the
  total Delta = T + D, D and T by harness and application, fractional scores, without the 7
  S1a-flagged tasks, without the 43 `compare_pptx_files` tasks, and on all 106 candidates (intention
  to treat), process metrics, moderators.
- **Decision rules (census frame, primary).** Var(D) = (1/K^2) sum of within-task variances, each
  estimated without bias per (task, cell, harness); log R_D by the delta method. PRESENT if the 95%
  interval of D excludes 0, beside the stratified sharp-null randomization test with variance 4v
  (PRESENT_FRAGILE on disagreement). SMALL if the 90% interval of D lies inside +/-5 pp and that of
  log R_D inside +/-log(1/0.85). P3 is read as a total effect: CONFIRMED on PRESENT_HARM, FALSIFIED on
  SMALL without PRESENT or on PRESENT_BENEFIT. A mechanism may be named only on MIRROR_SPECIFIC: the
  population-frame 95% interval of E_dir below 0.
- **Why tasks, not episodes.** Qwen3.5-9B is close to deterministic on these tasks (beta-binomial
  a = 0.099, b = 0.246 over S1a's 124 cells); distinct tasks bind, not reruns.
- **Simulated operating characteristics** (`compute/power-v4/power-v4.json`, Slurm 1142; 2,000 replicates
  per seed, seeds 42-44; propensities from S1a's records; v3's tables are kept in `compute/power/`):

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

- **Reading.** The corrected sharp-null test rejects in 0.048 of replicates at the exact null (v3:
  0.32). Under every direction-free scenario, matched between the mirror and the placebo, the
  population-frame MIRROR_SPECIFIC fires in 0.023-0.027 of replicates, the nominal one-sided 2.5%; the
  census-frame version would fire in up to 0.143, which is why a mechanism is never named from the
  census frame. P3's total effect keeps v3's characteristics (SMALL 0.97 at the null, PRESENT_HARM
  0.86-0.96 at a 15% harm, false SMALL beyond a margin at most 0.05). The direction-specific reading is
  secondary and weaker (0.37-0.56 at a mirror-only 15% harm with n_pl = 2; 0.45-0.72 with n_pl = 4 at a
  7.57 GPU-h cap). On the 105 admitted tasks every rate is within 0.03 of the 106-task census.
- **Leakage and selection.** No task is selected on any outcome; admission excludes only
  agent-independent failures; the dev tasks shaped only Phase 0's tolerances (A/A, the mirror
  specification, the VCL coordinate offset), which apply identically to all cells.
- **Missing data and infrastructure.** Re-queue up to twice; a task enters if every cell has at least
  2 valid episodes (1 in PL); K2 and K3 make a run INCOMPLETE; K8 analyses complete blocks if at least 62.
- **Statistical reporting protocol.** K-Dense `statistical-analysis` and the ARS statistical reporting
  standards: effect sizes with intervals in both frames, paired and clustered errors, coverage checked
  by simulation, frames, margins, the placebo reading and moderators registered before data.

## Compute and Reproducibility

Engine: vLLM v0.31.0 (commit `db9527a4`) on
`docker.io/vllm/vllm-openai@sha256:b18abb2df97b8f798e81862bd93f872ea18613372e2c3adc0cc2ac21e66ac12f`
with the cu129 overlay rebuilt from the freeze commit by `scripts/build_vllm_overlay_on_h100.sh`, as
S1a. Model: Qwen3.5-9B revision `c202236235762e1c871ad0ccb60c8ee5ba337b9a` (receipt `0a9e052d`). Agent
loop, harness adapters, VM lane and records: S1a's code of record (`harness/q2_stage1/`, freeze
`d5f5798`) plus the new cell selector, step-0 and keyboard checks and a lane version that accepts the
derived image (new code, reviewed before the freeze). Pilot container:
`cotcodec-q2-lo-vm@sha256:f5b4c40eefd2b92f846652910ba34db35e1ae7bf90fa474595cc745cc5895361`.

Pilot launch path (as run; CPU only, no GRES, one of this run's jobs at a time after a queue check;
other workstreams' CPU jobs may run beside it):

```bash
sbatch --parsable --export=ALL,Q2M_MODE=run,Q2M_IMAGE_ID=sha256:f5b4c40eefd2b92f846652910ba34db35e1ae7bf90fa474595cc745cc5895361,Q2M_ARGV_JSON_HEX=$ARGV_HEX,Q2M_SOURCE=/home/kevin/cotcodec-runs/stage0/s2v3-phase0-pilot/src-r1,Q2M_RUN_DIR=/home/kevin/cotcodec-runs/stage0/s2v3-phase0-pilot/run-r1-full2,Q2M_INPUTS=/home/kevin/cotcodec-runs/stage0/q2-evaluator-mutation/inputs infra/slurm/host-single-node/s2v3-pilot-cpu.sbatch
# ARGV: ["python3","/src/capture.py","/src/pool-v3.json","/out","--workers","16"]; the job receipts
# (compute/pilot-r1/receipts/) record every argv, mount and image id.
```

The Phase 0 oracle as an orx node (local backend, the project's fixed run command over the committed
`experiments/orx/node.yaml` of branch `orx/s2-v3-1-phase-0-render-oracle-doctor-parallel-ca`; its parent node
`a4c30924` ran the serial doctor and was cancelled before answering, run `41dce444`, because the
development Mac was at a load average above 150):

```bash
orx exp run c7bcde07-b08f-4e7a-ba0b-ab82a333f7f0 --backend local   # runs: uv run --locked python scripts/orx_run.py
```

Phase 1 launch path (as S1a; the manifest does not exist yet; dry run, test-only, submit on an empty
queue; one GPU job and its CPU VM job):

```bash
uv run --locked python scripts/submit_docker_research_job.py infra/slurm/host-single-node/s2-arabic-cua-locale-v3-phase1.yaml --dry-run
uv run --locked python scripts/submit_docker_research_job.py infra/slurm/host-single-node/s2-arabic-cua-locale-v3-phase1.yaml --test-only
uv run --locked python scripts/submit_docker_research_job.py infra/slurm/host-single-node/s2-arabic-cua-locale-v3-phase1.yaml
```

The submitter wraps `sbatch infra/slurm/host-single-node/docker-research.sbatch`.

Machine fields: seeds: [42, 43, 44]; gpu_hours: 7 (the ceiling of the registered 6.83 GPU-h: the
Phase 1 job cap of 6.73 at K = 106 plus the 0.1 GPU-h overlay reserve; 7.70 at the p95 slot price;
Phase 0 is 0; separate from the gauntlet's 0.3 GPU-h reviewer budget).

Cost model (`power-v4.json` `costs`): the Q2 design study's slot rule, s = 197.73 s at V = 20, cap
ceil(3 + L/60 + (N s / V + drain) x 1.2 x 1.05 / 60) + 6 minutes, N = 18 K. K = 106: 1,908 episodes,
5.30 physical GPU-h at the high slot, 410 cap-minutes (6.83 GPU-h; 7.70 at the p95 slot); K = 89:
5.77; K = 62: 4.08. Under S1a's registered c_proj the same 1,908 episodes would be 21.5 GPU-h; the cap
rule is Kevin's decision (design study section 5).

Checkpoints and resume: as S1a, each episode is the unit of work, records are appended as episodes
finish, and a fresh job skips completed (task, cell, harness, rerun) keys and continues the seeded
order; preempted time counts against the cap (D22). Artifacts: per-episode records, the oracle
record, codings and the decision record in the public repository; screenshots and trajectories on
the host and in the private archive. Pilot artifacts: `compute/pilot/` (wave 1) and `compute/pilot-r1/`
(this repair: capture records and manifest, the oracle records, the checker-invariance jobs and
verdicts, receipts, Slurm logs, the orx node's receipt); the code is `harness/s2_locale/` and
`scripts/run_s2v3_phase0_doctor.py`. Screenshots, accessibility dumps, saved documents and the
generated catalogs stay on the host and in the scratchpad copy the doctor reads (hashes committed).

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
  screenshot are Kevin's call (D2). The repair's stand-in catalogs were generated in the job from
  strings the installed build ships; they and the screenshots stay off the repository.
- **Public-repo hygiene.** No host address, credentials or private data in any artefact (the
  committed records were scanned for addresses).

## Negative-Result Value

| Outcome | What it says | What it closes |
|---|---|---|
| K0 (fewer than 62 tasks pass Phase 0, or an instrument check fails) | LibreOffice cannot be localized and mirrored to the oracle's standard on enough tasks, or the oracle cannot certify it; the leak and RTL-defect inventories say where (the pilot: admission passes under checker invariance, the oracle's planted-control bar does not) | S2 on this stack; a public i18n record either way |
| K1 | The localized image breaks the certified action path | Phase 1 on this image |
| D SMALL (census) | Mirroring LibreOffice's interface changes this agent's success on OSWorld's LibreOffice tasks by less than 5 pp and less than 15% of the solve rate | The mirror half of the split for application-level localization on this benchmark; a publishable robustness null |
| D PRESENT_HARM, not MIRROR_SPECIFIC | A net cost of mirroring on these tasks that is not separated from the agent's sensitivity to rearranging its toolbars | No mechanism claimed (K9) |
| D PRESENT_HARM, MIRROR_SPECIFIC, positional moderator named | A mirror cost beyond a toolbar rearrangement that tracks target relocation | Points mitigation at grounding (position augmentation) |
| D PRESENT, unresolved; O8 defects large | A mirror cost possibly carried by RTL rendering defects | Separates "RTL is hard for agents" from "this RTL build is broken" |
| T PRESENT_HARM, lexical moderator named | An Arabic-interface cost that tracks lost instruction-label overlap | Points at lexical matching, not glyph reading |
| PRESENT in the census, not in the population frame | An effect on these tasks that does not generalize with confidence | Sizes a successor |
| INCONCLUSIVE | Nothing beyond the intervals | Sizes a successor |

## Preflight Doctors

| Doctor | Status | Evidence | Remediation |
|---|---|---|---|
| Source | PASS | Wave 1's retrieval stands (`query-log.json`); this run's 9 counted queries with raw-output hashes and ids, 2 full reads; cutoff 2026-10-11; degraded coverage recorded (no CJK-capable venue index, social media, Google Scholar) (`doctors-r1/source.json`) | A RealGUINoise revision check and a macOSWorld citer refresh before any write-up |
| Citation | PASS | C01-C39 (C11 and C19 now full reads) and C40-C52 tied to job receipts and records (`doctors-r1/citation.json`) | Read ITDroid in full if a delta row rests on it |
| Novelty | PASS | No direct prior under the recorded coverage; wave-1 blind discrimination PASS; code search and Chinese queries added; the delta restated as a measurement on a narrower object (`doctors-r1/novelty.json`) | This run's blind critic and novelty refuter re-judge it |
| Design | PASS | One selector file; stock, A/A, placebo and tagged cells; planted controls; checker invariance; P1-P8 and K0-K9 reachable; power-v4 under the registered estimators (`doctors-r1/design.json`) | Rerun Phase 0 on the derived image before the freeze |
| Compute | FAIL | Phase 0 CPU-lane jobs with receipts and an orx cpu-doctor node; no derived image, VM-lane Phase 0, delta certification, Phase 1 manifest, dry run or S2 model loop (`doctors-r1/compute.json`) | Kevin's go-ahead for the downloads; image surgery and lane change reviewed; P0.6; the Phase 1 manifest's dry run and test-only |
| Safety | PASS | Unprivileged network-less containers, CPU only, nothing downloaded, no outward action, records scanned for host addresses (`doctors-r1/safety.json`) | none |

Protocols followed: Citation, the ARS claim-verification protocol (claim registry, locators,
verdicts); Design, the vendored K-Dense `experimental-design` and `statistical-power` skills (design
before data; a 2x2 blocked by task and session; power by simulation of the registered estimator on
measured inputs); Evaluation, K-Dense `statistical-analysis`; Novelty, K-Dense `literature-review`
(PRISMA counts in the header). The integrity gate's seven failure modes are answered in the
registration.

## Independent Adversarial Reviews

Reviewer A: FAIL | provider=not-run | model=not-run | run_id=not-run | artifact=none (this run's reviewers run after the blind critic and the refute-first triad; wave 1's reviews are in the gauntlet record)

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
| **Total** | **0** | **0** | Lower total is authoritative (S2 v2: 49, then 59; S2 v3 wave 1: 60) |

## Iteration Log

| Wave | Score | Highest-impact defect | Change | Result |
|---:|---:|---|---|---|
| dossier (2026-10-06) | not scored | String swap cannot hold layout fixed; Relay not internationalized | Corrected question and kill lines | dossier section 5 |
| S2 v1 wave 1 (2026-10-10) | 49 | Relay's 18 tasks cannot power Phase 1 | moved to OSWorld (D68) | gauntlet row `1a24cee8...` |
| S2 v2 run 2 (2026-10-11) | 59 | SMALL unreachable at K = 26-31; heterogeneous power 0.45 | honest exit (D68, D70) | gauntlet row 2 |
| S2 v3 wave 1 (2026-10-11) | 60 (61, 60) | The CPU pilot decided neither K0 nor K1 (no text factor, oracle unimplemented); direction-free change in D; sharp-null variance | repair run under D74 | row `8b0c6ef5...` |
| S2 v3 repair (2026-10-11) | not yet scored | as wave 1 | generated catalogs and every cell at every task; the oracle with controls as an orx node; checker invariance; placebo cell and direction-specific reading; corrected sharp null; ITT admission; K0 decided (FAIL as committed, 105 admitted under checker invariance), K1 scoped | this run's blind critic, triad and reviewers |

## Deterministic Doctor Output

Verbatim output of `uv run python scripts/research_direction_doctor.py
program/proposals/2026-10-11-s2v3-arabic-cua-locale-pilot.md` on the committed bundle, also stored as
`evidence/2026-10-11-s2v3-arabic-cua-locale-pilot/doctors-r1/research-direction-doctor-output.json`.
Readings the doctor does not make for itself, as in wave 1: "all declared budgets must be positive"
comes from parsing the declared `gpu_hours=0.3` as an integer (the budget is honest and is not
rounded up to pass); its executable-pilot check is textual, while by the gauntlet rule's cap table the
proposal stays capped at 89 (no signed, provider-distinct review) and cannot reach 100 without D24's
trust store. Compute is FAIL by the doctor's own conditions (no Phase 1 manifest, dry run or S2 model
loop); the Phase 0 pilot's executable evidence is the orx node and the CPU-lane receipts.

Exit code 1.

```json
{
  "acceptedScore": 0,
  "doctorStatus": {
    "Citation": "PASS",
    "Compute": "FAIL",
    "Design": "PASS",
    "Novelty": "PASS",
    "Safety": "PASS",
    "Source": "PASS"
  },
  "evidenceBundleLoaded": true,
  "hardCaps": [
    89
  ],
  "issues": [
    "all declared budgets must be positive",
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
