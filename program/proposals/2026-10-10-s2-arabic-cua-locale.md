# Research Direction: S2 first step, Arabic interface text versus mirrored layout for an open-weight computer-use agent on Q2's certified OSWorld stack (Phase 0 localized image, catalog isolation and factorial render gate; Phase 1 2x2 sized from S1a's records)

**Status:** repaired under program decision D68 for a fresh gauntlet run, after gauntlet wave 1 (score 49, the lower of 58 and 49; all three refuters refuted; no honest exit; `program/gauntlet/2026-10-10-s2-arabic-cua-locale.jsonl`, row hash `1a24cee8...`); repair by the single owner on 2026-10-10 to 2026-10-11 UTC on the development Mac's CPU (no GPU, no host job); the draft registration is now `program/preregistrations/s2-arabic-cua-locale-v2.md` (new experiment id; v1, the Relay design, superseded and left unedited), a DRAFT, not frozen or admitted; the blind critic, the refute-first triad and the two reviewers of this run have not run; no executable pilot exists; Phase 1's registered caps are at most 7.98 GPU-h (below 8), but by D68's structural note nothing runs without Kevin's admission ruling or D24's trust store; a score of 100 cannot be certified in this repository (D24)
**Owner:** Kevin Liu (program owner); wave-1 synthesis and the D68 repair (substrate move, task screen, fixture and oracle design, identification, draft registration, simulations) written by a Claude agent acting as the gauntlet's single owner
**Source cutoff:** 2026-10-10
**Coverage limits:** wave 1's coverage (orx 0.2.2 alphaXiv keyword and embedding search and OpenAlex, 123 counted queries; OpenReview term searches; Semantic Scholar citer lists through the host relay; Google Patents and web searches by the novelty refuter; see wave 1's header and record) plus this run's repair: 22 counted retrieval queries (14 orx discover: 10 keyword including title-phrase queries for RealGUINoise, WebPageBench, BreakingWeb and macOSWorld, 2 embedding including one Chinese-language query, 2 OpenAlex; 4 ACL Anthology searches over the full `anthology+abstracts.bib` already fetched by the E4 repair, 131,473 entries; 4 OpenReview API searches), 2 uncounted paper reads (2601.21961 in full, 2604.17849 by report) and 13 uncounted primary-source fetches for the per-application switches (LibreOffice core at `08f5d410`, GTK 3.24.33 and 2.24.33, Pango 1.50.6, Gecko `LocaleService.cpp` master, UAX #9, CSS Writing Modes 3), each with line numbers. OpenReview per-note pages return a browser challenge and were not opened. Not searched: Semantic Scholar in this run (the host is reserved for the reviewer's lane job), patents beyond wave 1's IBM family, live X, Reddit, Hacker News, Google Scholar, Chinese-language venues (one Chinese-language alphaXiv embedding query only). PRISMA-style for this run: 441 ids identified, 358 unique, screened by title; 2 read beyond the title; 0 direct priors.
**Budgets:** queries=80; wall_minutes=600; tokens=8000000; dollars=150; waves=1; gpu_hours=0.3
**Novelty verdict:** NO_DIRECT_PRIOR_FOUND
**Safety verdict:** PASS
**Evidence bundle:** evidence/2026-10-10-s2-arabic-cua-locale/bundle.json

The budgets are this fresh run's (D68), cumulative over the repair, the triad, the reviewers
and the recorder; at least 30 of the 80 queries are reserved for the three refuters (six orx
discover queries each at minimum). The repair used 22, leaving 58. The gauntlet's GPU budget
(0.3 GPU-h) is for the open-weight reviewer's lane job only; the repair made no host contact.
The novelty verdict field uses the doctor's vocabulary; the merged verdict is NARROWED, with
the residual STILL_OPEN (below).

## Changes after wave 1

Wave 1 (row hash `1a24cee8...`; proposal sha256 `e16214cf...`, registration v1 sha256
`866f994d...`) scored 49: reviewer 1 (claude-opus-5-5) 58, reviewer 2 (qwen3.6-35b-a3b, Slurm
1079) 49. Blind discrimination against macOSWorld passed (the critic judged the proposal the
stronger contribution). All three refuters refuted. The largest defect was decisiveness on
Relay: its 18 tasks could not power Phase 1 (the registered gate passed with probability
0.000-0.039 in the proposal's own simulation; frontier models completed 0 of 12 Relay pixel
workflows), so the 2.0 GPU-h pilot bought a foreseeable infrastructure exit. Second was
identification: bidi artefacts in the off-diagonal cells (English chrome in a right-to-left
paragraph, Arabic chrome in a left-to-right one) biased D by (s_arL - s_enR)/2 and T by the
opposite, and no gate could see it. D68 ordered one CPU repair by a single owner: move the study
onto Q2's certified OSWorld stack, size Phase 1 from S1a's noise floor and cost, make the
fixture vary text direction and layout direction separately with a check that proves it, and
keep the macOSWorld delta honest, stating what D53 covers for localized applications. This
section is that repair. Evidence is in the bundle's `compute/repair-d68/`: T1 = task screen
and power under the registered estimator (`power-osworld.py`, output `power-osworld.json`;
the superseded runs `power-osworld-v0-partial.json` and `power-osworld-v1-break050.json` are
kept); O = render oracle and its
validation (`render-oracle/`); M = primary-source lines for every switch
(`fetch-mechanism-sources.py`, `mechanism-sources-index.json`, `snapshots/`); Q = this run's
retrieval (`query-log-run2.json`).

| # | Wave-1 defect (named by) | Repair | Registration v2 clause | Evidence |
|---:|---|---|---|---|
| 1 | Relay's 18 tasks cannot power Phase 1; the gate essentially cannot pass; the pilot buys a foreseeable exit (largest defect, reviewer 1; feasibility refuter; reviewer 2 jointly) | Substrate moved to S1a's OSWorld stack: Qwen3.5-9B, the two certified harnesses, the L0-fixed lane at V = 20, S1a's cost card. Tasks come from S1a's 113-task pool in applications with shipped Arabic interfaces whose layout can be switched separately (LibreOffice Calc, Impress, Writer; Thunderbird; GIMP): 43 candidates that Qwen3.5-9B solved in at least 1 of 8 S1a episodes, 26 of them strict LibreOffice tasks. No pilot: S1a's 8 English episodes per task (both harnesses) select the tasks and anchor the power analysis | Tasks; Phase 1 | T1 `task_screen`, `sets` |
| 2 | Sizing on transported, assumed inputs; S1a's all-cell variance used as the informative-task variance (reviewer 1's enumeration) | A beta-binomial propensity model fitted on S1a's 154 candidate (task, harness) cells (a = 0.107, b = 0.167) reproduces S1a's k-histogram and rerun discordance (0.099 against 0.0996 observed); each selected cell's success probability is drawn from its own posterior. The simulation runs the registered estimator end to end (paired t, sign flip, TOST, the rare-break bound) under six effect structures, from a uniform logit shift to complete breaks in a few tasks | Statistics | T1 `prior`, `simulation` |
| 3 | Is a 5 pp direction effect detectable within a compute cap? | Yes for a diffuse effect, no for a concentrated one. Under the registered estimator, a true -5 pp direction effect is called PRESENT (harm) with probability 0.89-0.97 when it is a uniform logit shift and 0.79-0.90 when it is a proportional reduction on every task, across the four task sets (K = 26-43, n = 16 or 12, caps 5.98-7.98 GPU-h including the overlay reserve, all below 8); 0.65-0.83 when half the tasks carry it, 0.44-0.67 when a quarter do, and 0.09-0.21 when it consists of complete breaks in about 8% of tasks. The false PRESENT rate under the null is 0.040-0.053. More episodes cannot rescue the concentrated cases: with near-deterministic outcomes the limit is the number of tasks | Statistics; Phase 1 | T1 `simulation`, `cost` |
| 4 | The gate's tau2 floor (0.0025) sat below the heterogeneity of a realistic effect (feasibility refuter, reviewer 1) | The data-driven gate is gone; the design is fixed now. The simulation's effect structures span realized between-task heterogeneity from near 0 (uniform shifts on near-deterministic tasks) to that of complete breaks, and the SMALL rule now carries a rare-break bound because the t interval under-covers when a few tasks break (coverage 0.82-0.92 for the flip structure at K = 26 in T1's first run). A second run counted only D_t at most -0.5 as a break and still let an unqualified SMALL through in up to 0.087 of replicates at a true -5 pp at K = 43, so a large drop is now D_t at most -0.25 | Decision rules | T1; `power-osworld-v0-partial.json`, `power-osworld-v1-break050.json` |
| 5 | Off-diagonal bidi leakage biases D and T; G8, G9 and K3 could not see it (identification refuter; both reviewers) | Text direction is decoupled from layout by construction: every interface catalog string, English and Arabic, is wrapped in FIRST STRONG ISOLATE ... POP DIRECTIONAL ISOLATE in all four cells, so each string takes its direction from its own first strong character whatever paragraph level the toolkit imposes (UAX #9 X5c). The need is shown in source: when LibreOffice's interface is mirrored, every output device starts in the `BiDiRtl` text mode and VCL runs ICU's bidi with an explicit paragraph level (`outdev.cxx` 87-88, `ImplLayoutArgs.cxx` 56-66). A factorial render oracle proves the separation: O2 requires every text run's ink to be the same image in both layout levels of its text level; O3 requires mirrored widget boxes; O4 forbids reordering under a text swap; O5 requires identical document regions; O6 requires the isolation to be invisible in the en cell. Validated on Chromium fixtures with known properties (Blink lays out bidi text with ICU, the library VCL calls): all 7 variants gave their expected verdicts; unisolated strings leaked in 7 of 38 run pairs and isolation removed all 7; a field composed in code still leaked under isolation and was flagged; half-mirroring, reordering and content drift each failed exactly their check. Phase 0 adds positive controls on the real applications | P0.4, P0.7 | O `oracle-validation.json`; M |
| 6 | Manipulation checks never touched the analysed units (aurora seeds; references rendered on the Mac) (identification refuter, reviewer 1) | OSWorld tasks have one initial state each; the oracle runs in the measurement lane on the derived image at every candidate task's post-setup state and over a menu and dialog sweep; Phase 1's step-0 check compares against references recorded in the same lane and image | P0.7; Phase 1 | registration |
| 7 | G3 could not pass without reinterpretation (server code had to change) (identification refuter, reviewer 1) | No application or checker code is edited. Switches live in system or share layers (a finalized share-layer LibreOffice setting, pseudo-locale catalogs, a launcher selector). Three candidate checkers read LibreOffice's user `registrymodifications.xcu`, so nothing is written there; seven config-reading tasks are conditional on an invariance probe | P0.3, P0.9 | T1 `conditional_config_checker` |
| 8 | G6 demanded equal container boxes across text, impossible for content-sized controls (feasibility refuter) | Replaced: O3 compares boxes only between the two layout levels of the same text; O4 checks order, not width, across text | P0.7 | O |
| 9 | Mechanism attribution defaulted to "positional" when a one-sided falsifier did not fire (identification refuter, reviewer 1) | A moderator names a mechanism only if its 95% CR2 interval excludes 0 in the predicted direction; otherwise "unresolved" | Estimands | registration |
| 10 | Novelty framing overstated the match to macOSWorld's open split; G5's reflection rule uncredited (novelty refuter; reviewer 1) | The claim is restated as application-level localization over English documents and an English system shell, and the closest analog in macOSWorld is named (its English-instruction runs in localized interfaces). The IBM GUI-mirroring test patent family is cited for O3's reflection rule. Title-phrase queries for RealGUINoise, WebPageBench and BreakingWeb, ACL Anthology and OpenReview searches, and a Chinese-language query were run; VAF (2601.21961) was read in full and added | Proposal | Q; Novelty Ledger |
| 11 | In-project Arabic catalog and an unavailable native-speaker review (wave 1's own precondition) | The applications' shipped Arabic translations are used; the native-speaker precondition goes; the Arabic chrome share per screen is measured | P0.2, P0.11 | registration |
| 12 | What does D53 cover for localized applications? (D68) | Stated in a table: the runtime, the harness adapters, the lane and V = 20 carry over; the derived image, the keyboard map under an Arabic locale, the guest server under localized applications and the rendered treatment are not covered, so P0.6 reruns D53's per-action suite on the derived image and P0.7-P0.9 certify the treatment | D53 section | registration |
| 13 | Relay's engineering (local transport, adapter, image, smoke) did not exist (feasibility refuter, compute doctor) | Replaced by S1a's existing lane, agent loop and manifests; the new engineering is the derived image, the cell selector, the pseudo-locale catalogs, the oracle doctor and the delta certification | Phase 0 | `attestations-not-run.md` |
| 14 | Refuters ran no orx queries; query budget (process defect) | This run declares 80 queries with at least 30 reserved for the triad; the repair used 22 | Header | Q |

Not repaired, and why:

- **No executable pilot (cap 79).** Phase 0 needs host CPU lane jobs (building the derived image
  from offline packages, running the action-path suite and the oracle in VMs). This run may
  submit nothing to the host but the reviewer's lane job, so the oracle is validated on Chromium
  fixtures only and the switches are verified in source only.
- **Unsigned reviews (cap 89)** and the trust store (D24).
- **Thunderbird's switch.** Current Gecko source has no layout-direction override independent
  of the locale (`IsAppLocaleRTL` reads only the `bidi`/`accented` pseudo-locales and the app
  locale; `intl.uidirection` does not appear), so Thunderbird's off-diagonal cells need
  pseudo-locale language packs whose acceptance by the installed build is unverified. It is conditional,
  and the power analysis is reported without it.
- **Concentrated effects.** A 5 pp mean effect carried by complete breaks in a few percent of tasks is detected with probability 0.09-0.21 (0.26-0.51 at -8 pp), and an unqualified SMALL needs about 43 tasks (the rare-break bound). Only more tasks fix this (for example the remaining OSWorld tasks in these applications, once their offline setup is validated on the lane); more episodes or a second model would not. It is reported, not repaired
- **External validity.** One model, two scaffolds, 26-43 tasks in three to five applications,
  one language, application-level localization only.

## Scope

This proposal covers S2's first step only: Phase 0 (no GPU: a derived localized image, four
cell selectors, catalog isolation, a delta certification of the action path and a render gate)
and Phase 1 (one GPU job: the 2x2 on the admitted tasks). The reasoning-language arm, other
languages, full operating-system localization, other models and any training are out of
scope. Relay is out of S2: if S3 still needs a localized Relay, wave 1's specification
defects (bidi decoupling of all chrome and inputs, gates on the analysed seeds, G3 against
P0.2, G6's containers) belong to S3's own proposal.

## Claim and Research Question

**Question.** On Q2's certified OSWorld stack, with task instructions, documents, checkers, the
system shell, number formats and the keyboard held fixed, and each application's interface
text language and layout direction switched separately in a 2x2 {English, Arabic interface
text} x {left-to-right, mirrored layout}, how large are (D) the main effect of mirroring and (T)
the main effect of Arabic interface text on the screenshot success of Qwen3.5-9B, with tasks
as the random factor and S1a's measured rerun noise as the floor?

**Variable.** The cell: the application's interface catalog (English or Arabic, both wrapped in
directional isolates) and its layout switch (off or on), with everything else held fixed.

**Claim scope.** `portability-protocol`: a measurement on one frozen model and two certified
scaffolds over the admitted applications. Evidence level by outcome: Phase 0 gives a certified
localized image and an oracle record; Phase 1 gives a paired, clustered estimate with a
three-way decision. Nothing about full operating-system localization, instruction or
reasoning language, other models or training is licensed.

**Why the 2x2.** With four cells the two main effects average both paths and sum exactly to the
total English-to-mirrored-Arabic drop (ar-RTL - en = T + D). The off-diagonal cells (English in
a mirrored layout; Arabic in an unmirrored one) are what platform test practice renders
(Android's forced RTL layout, ICU's en-XB and Windows' qps-plocm pseudo-locales) and what
LibreOffice's own switches produce (`SAL_RTL_ENABLED`, `UIMirroring`).

## Strategic Fit and Why Now

- **Program fit.** D67 restarted S2 once S1a gave the Q2 noise floor (D66), and D68 asked for
  exactly this move. S2 now reuses the program's most expensive certified asset (the D53
  action path, S1a's lane and cost card) instead of building a new one, and it puts language
  back as the controlled variable on that stack.
- **Why now.** macOSWorld still leaves its split open in its latest version (v4, 2025-10-18):
  "Arabic glyphs or the mirrored UI layout, or both" (Sec. 5.2). None of its 34 Semantic
  Scholar citers decomposes the drop (wave 1, read by title and abstract), and this run's
  title-phrase, ACL Anthology and OpenReview searches found none either. UI language has
  entered robustness suites only as a bundled perturbation (RealGUINoise).
- **What it does not buy.** Phase 1 on 26-43 S1a tasks in three to five applications is a measurement for one model at a cap of at most 7.98 GPU-h. It detects a diffuse 5 pp direction effect with high probability (0.89-0.97 for a uniform logit shift) and a concentrated one poorly (0.09-0.21 for complete breaks in a few tasks), and below about 43 tasks it cannot return an unqualified robustness null. The infrastructure exit (K0, K1) remains a first-class result: a render-certified localized OSWorld image is useful beyond S2

## Primary-Source Evidence

Claim registry (full records in `evidence/2026-10-10-s2-arabic-cua-locale/doctors/citation.json`).
"First-party" marks numbers reported by the producing team and not replicated here; "abstract"
marks sources read only at abstract level; "source" marks code read at the pinned revision with
line numbers. C22-C25 concern Relay and are kept as wave-1 history only.

| Id | Claim | Source and date | Read |
|---|---|---|---|
| C01 | All-agent mean success excluding Advanced Apps: en 19.3%, ru 17.7%, zh 17.2%, ja 15.8%, ar 13.7% (28.8% relative drop for Arabic); attributed to "Arabic glyphs or the mirrored UI layout, or both" | [macOSWorld, NeurIPS 2025, v4](https://arxiv.org/abs/2506.04135), 2025-10-18, Table 4 and Sec. 5.2 | full text |
| C02 | Per agent, 171 tasks, one run each, en to ar: Claude CUA 44.4 to 31.6, OpenAI CUA 33.3 to 28.1, Gemini 2.5 Pro 22.8 to 15.8, GPT-4o 8.8 to 2.9, UI-TARS-7B 5.3 to 2.3, ShowUI 1.2 to 1.8 | same, Table 3 | full text |
| C03 | English instructions with an Arabic UI (OpenAI CUA): 22.8% against 33.3% en/en and 28.1% ar/ar; Claude CUA clicks the non-mirrored Dock location of System Settings | same, App. D.1 Tables 6-7; App. Fig. 19 text | full text |
| C04 | No error bars or significance tests (NeurIPS checklist item 7, "No") | same, checklist | full text |
| C05 | Six languages, static parallel screenshots, no Arabic or RTL; interactive benchmarks "inevitably introduce language-irrelevant variations" | [MPR-GUI, ACL 2026](https://arxiv.org/abs/2512.00756), 2026-04-28 | full text |
| C06 | State and actions held fixed across 8 languages in text games; Arabic and Hebrew weakest | [Skill Issue](https://arxiv.org/abs/2608.25832), 2026-08-26 | full text |
| C07 | Cross-lingual policy divergence normalized by rerun reproducibility | [Actions Speak Louder than Words, COLM 2026](https://arxiv.org/abs/2608.11110), 2026-08-13 | full text |
| C08 | 42 interactive noise types including "Language Swap" (browser auto-translation); results by category; benchmark primarily English | [RealGUINoise](https://arxiv.org/abs/2609.38184), 2026-08-07, Table 10 and Limitations | full text |
| C09 | Event-level verification; controlled UI variants; Russian interfaces, no locale or direction variant | [WebPageBench](https://arxiv.org/abs/2609.35026), 2026-09-28 | full text |
| C10 | 519 grader-preserving clean/intervention pairs, 29 intervention families, no locale, translation or RTL intervention | [Constructing Challenging Browser-Use Tasks](https://arxiv.org/abs/2609.35814), 2026-09-20 | full text |
| C11 | Model-specific grounding blind zones; Qwen3-VL-8B drops 16.1 pp inside them | [ScreenHaystack](https://arxiv.org/abs/2609.32036), 2026-09-25 | full text |
| C12 | VLMs describe the left image first in 97% of cases, including an Arabic-finetuned model under Arabic prompting | [Spatial Attention Bias in VLMs](https://arxiv.org/abs/2512.18231), 2025-12-20 | full text |
| C13 | Holding the language fixed and varying the script gives gaps up to 16% in 10 VLMs | [PuMVR](https://arxiv.org/abs/2606.17188), 2026-06-15 | abstract |
| C14 | 35 language-setting UI display bugs in Android apps, 19 of them RTL | [SUDFinder](https://arxiv.org/abs/2607.04120), 2026-07-05 | full text |
| C15 | Careful functional and cultural alignment raises agent success by up to 32.7% over minimal translation | [GAIA-v2-LILT, MELLM 2026](https://aclanthology.org/2026.mellm-1.13/), 2026-04-27 | abstract |
| C16 | Arabic OCR CER: Qwen2.5-VL-7B 1.20, GPT-4o 0.31, Gemini-2.0-Flash 0.13 | [KITAB-Bench](https://arxiv.org/abs/2502.14949), 2025-02-20 | full text |
| C17 | Arabic is the most degraded script across OCR models, Qwen3-VL-8B included | [GlotOCR Bench](https://arxiv.org/abs/2604.12978), 2026-04-14 | full text |
| C18 | Qwen3.5-9B: "201 languages and dialects", OSWorld-Verified 41.8 (first-party); no Arabic GUI result | [Qwen3.5-9B model card](https://huggingface.co/Qwen/Qwen3.5-9B), fetched 2026-10-10 | first-party |
| C19 | Grounding tracks recovery of the visible label from the instruction's wording; concept binding collapses across scripts | [Lexical Coupling](https://arxiv.org/abs/2608.21794), 2026-08-22; [M2BIND](https://arxiv.org/abs/2608.12333), 2026-06-02 | abstract; full text |
| C20 | S1a: D_w 12.5% pooled (9B 8.59%), D_b 11.33%, no session excess (upper bound 0.78 pp), 9B session shift +5.5 pp (p 0.016), 9B cost 0.0027 GPU-h per episode, 0 infrastructure losses in 1,808 episodes | `program/evidence/2026-10-10/q2-stage1-a1/RESULTS.md` (D66) | repository |
| C21 | Serving probe v2 on this host (wave 1's price input; superseded here by S1a's realized card) | `program/evidence/2026-10-07/serving-throughput-probe-v2/README.md` | repository |
| C22-C25 | Relay facts (wave 1 only: code, oracle, mirror probe, interface study) | wave-1 version of this file | historical |
| C26 | With participants and stimuli random, power approaches a ceiling as participants grow | [Westfall, Kenny and Judd 2014](https://doi.org/10.1037/xge0000014) | abstract |
| C27 | More similar tasks raise model-ranking reliability by at most 0.097 when scaffold coverage dominates | [Agent Evaluation Reliability](https://arxiv.org/abs/2610.00651), 2026-09-30 | full text |
| C28 | Clustered and paired standard errors for evals | [Adding Error Bars to Evals](https://arxiv.org/abs/2411.00640); [Measuring all the noises of LLM Evals](https://arxiv.org/abs/2512.21326) | full text |
| C29 | Few-cluster over-rejection; CR2 small-sample correction | [Cameron, Gelbach and Miller 2008](https://doi.org/10.1162/rest.90.3.414); [Pustejovsky and Tipton](https://doi.org/10.1080/07350015.2016.1247004) | metadata |
| C30 | Equivalence testing (TOST) | [Lakens, Scheel and Isager 2018](https://doi.org/10.1177/2515245918770963) | metadata |
| C31 | Layout graphs detect internationalization presentation failures | [GWALI, ICST 2016](https://doi.org/10.1109/icst.2016.36) | author PDF |
| C32 | What to mirror and what not; logical CSS; `dir="auto"` | [Firefox RTL guidelines](https://firefox-source-docs.mozilla.org/code-quality/coding-style/rtl_guidelines.html); [W3C qa-html-dir](https://www.w3.org/International/questions/qa-html-dir) | full page |
| C33 | Forced RTL with Latin text in platform practice; en-XB and qps-plocm pseudo-locales | [Android: support different languages](https://developer.android.com/training/basics/supporting-devices/languages); [Microsoft: pseudolocalization](https://learn.microsoft.com/en-us/globalization/methodology/pseudolocalization) | full page |
| C34 | LibreOffice mirroring: `SAL_RTL_ENABLED` forces RTL; the `UIMirroring` key can hold an Arabic interface LTR; otherwise the UI language decides | `vcl/source/app/settings.cxx` 2633-2669 at `08f5d410` ([source](https://raw.githubusercontent.com/LibreOffice/core/08f5d410a474badedeaa3fbabaea9b6f564d1b83/vcl/source/app/settings.cxx)) | source |
| C35 | Reading direction manipulated within one script shifts spatial biases (humans) | [Román et al. 2015](https://doi.org/10.1038/srep18248) | abstract |
| C36 | Default RTL rendering of explanation labels gave OCR CER 0.820-0.979 | [When Explanations Cannot Be Read](https://arxiv.org/abs/2609.28565), 2026-09-23 | full text |
| C37-C39 | Text-only multilingual web and tool agents; a factorial interface contrast without a locale factor | X-WebAgentBench, OmnilingualGAIA2, BabelArena, OpenReview irjWqxKeHm (wave 1) | as in wave 1 |
| C40 | S1a pool: of 113 tasks, 79 are in the five candidate applications; after screening, 43 were solved by Qwen3.5-9B in at least 1 of 8 episodes (17 in 8 of 8); 26 are strict LibreOffice tasks; mean 9B success on the 43 is 0.70 | `program/evidence/2026-10-10/q2-stage1-analysis/a1.jsonl`, `plan-a0a.json`; T1 | repository |
| C41 | Setup steps that click at screen coordinates (`550ce7e7`, `a669ef01`; five of six VLC tasks); checkers that read `registrymodifications.xcu` (3 tasks), `prefs.js`, `xulstore.json`, `gimprc` (2) | same, `setup.config_steps`, `checker_input_sha256` | repository |
| C42 | Cost: GPU time is set by VM slots (the engine never queued); cap rule ceil(3 + L/60 + (N s/V + drain) x 1.2 x 1.05 / 60) minutes; 9B start-up 113.2 s, drain 104.6 s | Q2 design study, `stage0/q2-design-study` `79096f8`, `cost-model.json` | repository |
| C43 | D53's scope: the L0-fixed runtime and the two harness adapters on this host as configured, at most 32 concurrent VMs; not another image, untested catalog instances, or the guest server under task applications | `program/decisions.md` D53; `program/evidence/2026-10-08/q2-action-path-v2-acceptance/README.md` | repository |
| C44 | When the UI is mirrored, every VCL output device starts with the `BiDiRtl` text layout mode; VCL runs ICU bidi with an explicit paragraph level 1 for it (no automatic direction) | `vcl/source/outdev/outdev.cxx` 87-88; `vcl/source/text/ImplLayoutArgs.cxx` 56-66 at `08f5d410` ([source](https://raw.githubusercontent.com/LibreOffice/core/08f5d410a474badedeaa3fbabaea9b6f564d1b83/vcl/source/outdev/outdev.cxx)) | source |
| C45 | LibreOffice loads gettext catalogs from `program/resource` for every interface language through boost.locale, with no en-US special case; a key-id pseudo-locale (`qtz`) exists | `unotools/source/i18n/resmgr.cxx` 112-145, 198-213 at `08f5d410` | source |
| C46 | LibreOffice's GTK 3 plugin sets GTK's default direction from `AllSettings::GetLayoutRTL()` | `vcl/unx/gtk3/gtkinst.cxx` 4887 at `08f5d410` | source |
| C47 | GTK takes its default direction from the translation of `default:LTR` in its own catalog | GTK 3.24.33 `gtk/gtkmain.c` 1269-1282; GTK 2.24.33 `gtk/gtkmain.c` 750-759 | source |
| C48 | Pango layouts default to `auto_dir = TRUE` (paragraph direction from content) | Pango 1.50.6 `pango/pango-layout.c` 224 | source |
| C49 | Gecko's interface direction follows the app locale or the `bidi`/`accented` pseudo-locales; no `intl.uidirection` override remains | `intl/locale/LocaleService.cpp` (gecko-dev master, fetched 2026-10-11) | source |
| C50 | Isolates: FIRST STRONG ISOLATE takes the direction of the first strong character up to its matching POP DIRECTIONAL ISOLATE (rule X5c) | [UAX #9](https://www.unicode.org/reports/tr9/) | standard |
| C51 | `unicode-bidi: plaintext` sets each paragraph's direction from its content | [CSS Writing Modes 3](https://www.w3.org/TR/css-writing-modes-3/) | standard |
| C52 | Finalized configuration nodes in a lower layer cannot be overridden by a higher one; `EnglishFunctionName`, `UIMirroring` and `CTLFont` are schema keys | `configmgr/source/xcuparser.cxx`; `officecfg/.../Calc.xcs` 1508; `.../Common.xcs` 6400, 6458 at `08f5d410` | source |
| C53 | Controlled visual-attribute variants (background, text colour, font, size, position, card size, clarity, order) shift web-agent choices; no language, script or direction variant | [VAF, ACL Findings 2026](https://arxiv.org/abs/2601.21961) (also [aclanthology](https://aclanthology.org/2026.findings-acl.1723/)) | full text |
| C54 | Repeated executions of the same task diverge; unreliability decomposes into execution stochasticity, ambiguity and planning variability | [On the Reliability of Computer Use Agents](https://arxiv.org/abs/2604.17849) | report |
| C55 | An automated GUI-mirroring test places each mirrored element at x' = W - (x + w) within a few pixels | US9529606B1 family (IBM, priority 2015-06-24), raised by wave 1's novelty refuter (Google Patents) | metadata |
| C56 | The render oracle on Chromium fixtures: 7 of 7 variants as expected; A/A tolerance 0.136; smallest coupled leak 0.167 | `compute/repair-d68/render-oracle/oracle-validation.json` | this program |

## Closest Prior Work

1. **macOSWorld** ([2506.04135](https://arxiv.org/abs/2506.04135), NeurIPS 2025, v4
   2025-10-18; [OpenReview YJxGJP8feU](https://openreview.net/forum?id=YJxGJP8feU)). About 200
   interactive macOS tasks in VMs, five system languages, instructions machine-translated,
   six agents run once per task and language, one cross-lingual analysis with English
   instructions in each localized interface for one agent. It owns the UI-locale main effect on
   an executable desktop benchmark and names the open split. Its Arabic cell changes the whole
   operating system (system shell and every application), the script, the layout direction
   and, in the matched runs, the instruction language together; per-agent drops have an
   unpaired SE of about 5 pp at 171 tasks and one run, and none carries an interval.
   **Delta, stated narrowly:** S2 separates interface text from layout direction inside one
   environment for the application layer only (system shell, documents and instructions
   English), on the same tasks and in the same session, with two scaffolds, intervals, an
   equivalence rule and a render oracle that proves each cell differs only in its factor. S2's
   ar-RTL cell corresponds to macOSWorld's English-instruction runs in the Arabic interface,
   not to its matched-language cell, and S2's estimate does not decompose macOSWorld's
   full-system drop. What S2 lacks: macOSWorld's breadth (30 applications, six agents, four
   languages, a pop-up subset).
2. **RealGUINoise** ([2609.38184](https://arxiv.org/abs/2609.38184)). "Language Swap" is
   browser auto-translation, one of 42 noise types, reported by category. **Delta:** a
   controlled decomposition, not a perturbation bundle; no RTL or mirroring factor there.
3. **WebPageBench** ([2609.35026](https://arxiv.org/abs/2609.35026)), **BreakingWeb**
   ([2609.35814](https://arxiv.org/abs/2609.35814)) and **VAF**
   ([2601.21961](https://arxiv.org/abs/2601.21961)). Paired, grader-preserving UI variants
   (VAF: eight visual-attribute families, including position, on web pages). **Delta:** none
   has a language, script or direction variant; the paired-variant method is theirs.
4. **MPR-GUI** ([2512.00756](https://arxiv.org/abs/2512.00756)). Aligned static screenshots in
   six languages without Arabic. **Delta:** executable, oracle-aligned cells.
5. **Direction-versus-script priors outside agents**: spatial attention bias
   ([2512.18231](https://arxiv.org/abs/2512.18231)), PuMVR
   ([2606.17188](https://arxiv.org/abs/2606.17188)), Román et al. 2015. They motivate
   direction as its own factor.
6. **Method priors**: rerun-normalized cross-lingual agent effects
   ([2608.11110](https://arxiv.org/abs/2608.11110)); repeated-execution reliability
   ([2604.17849](https://arxiv.org/abs/2604.17849)); i18n presentation-failure detection
   (GWALI) and automated mirroring tests (the IBM family, C55), which O3 follows; pseudo-locales
   (en-XB, qps-plocm), which the off-diagonal catalogs follow.

The closest prior for blind discrimination stays macOSWorld; fresh anonymized mechanism
paragraphs for it and for this proposal are in `evidence/2026-10-10-s2-arabic-cua-locale/blind/`
(file names carry no role; `compute/blind-roles.json` maps them for the recorder only).

## Novelty Ledger

| Proposed component | Closest prior | Same | Delta | Confidence |
|---|---|---|---|---|
| Split of an executable GUI agent's interface-localization effect into a text part and a layout-direction part inside one environment, for application-level localization | macOSWorld (2506.04135) | interactive desktop tasks in VMs, Arabic mirrored interfaces, screenshot agents, binary success | the prior leaves the split open and localizes the whole system; S2 crosses application text and application layout in a 2x2 with the system shell, documents and instructions English, paired within task and session, with intervals | medium |
| Off-diagonal cells (English in a mirrored layout, Arabic in an unmirrored one) as experimental factors for agents | Android forced RTL, ICU en-XB, qps-plocm (test practice); Román et al. 2015 (humans) | direction without a script change | used as a measured factor on agents, not a QA tool | medium |
| Catalog-level directional isolation (FSI/PDI around every catalog string) to make text direction independent of layout | UAX #9 isolates, the HTML bdi element and `dir="auto"` (standard i18n practice) | the isolation mechanism | applied to whole interface catalogs as an experimental control, with a render check that proves it | high (the mechanism is standard) |
| Factorial render oracle (text-run identity across layout, reflection across direction, order across text, content identity) | GWALI (ICST 2016), the IBM GUI-mirroring test family (C55), SUDFinder | layout-relation and reflection checks for i18n failures | used as a manipulation check that certifies each cell differs only in its factor; not a novelty claim | high |
| Locale and direction as a grader-preserving UI variant | WebPageBench, BreakingWeb, VAF | paired variants, task and grader fixed | no language or direction variant in any | high (the method is not novel) |
| UI language as an interface perturbation | RealGUINoise (2609.38184) | language swap on GUI agents | bundled, category-level, no RTL factor, no decomposition | high |
| Noise-floor-anchored design for cross-lingual agent effects | 2608.11110; S1a | rerun-normalized effects | sized before data from S1a's per-task records on the same stack | medium |
| Moderators separating positional and lexical mechanisms | ScreenHaystack (2609.32036), lexical coupling (2608.21794) | each mechanism exists separately | pre-registered task-level moderators, named only on a positive interval | medium |
| Reasoning-language arm | Skill Issue (2608.25832) | | out of scope | not assessed |

Novelty wording: No direct prior art found through 2026-10-10 under the coverage in the header:
wave 1's 123 counted orx discover queries and other searches (`query-log.json`) and this run's
22 counted queries (`query-log-run2.json`): orx keyword with the mechanism terms and each
closest prior's title phrase (RealGUINoise, WebPageBench, BreakingWeb, macOSWorld), orx
embedding with the mechanism paragraph in English and in Chinese, orx OpenAlex for venue and
citation context, four ACL Anthology searches over the full bibliography with abstracts, and
four OpenReview API searches; the returned ids are in the two logs. The residual is narrow: the
paired, render-certified split for application-level localization. The geometric check, the
isolation mechanism, the pseudo-locale cells and the paired-variant method are prior art used
as infrastructure.

## Mechanism and Falsifiable Predictions

**Instrument.** A derived image of the certified OSWorld image installs each application's
shipped Arabic translation. Each application's layout switch (LibreOffice's
`SAL_RTL_ENABLED` or finalized `UIMirroring`; GTK's `default:LTR` catalog entry through
pseudo-locales; Thunderbird's locale through pseudo-locale packs) changes only where widgets
go; the catalog changes only which strings are shown; every catalog string is wrapped in
directional isolates in all four cells, so no string's internal order depends on the layout. A
render oracle (O1-O6) with positive controls certifies the cells, functional probes certify
that saved files do not depend on the cell, and D53's per-action suite is rerun on the image.

**Hypothesized causes.** Mirroring could lower success through (i) target relocation into
screen regions where the model grounds less reliably (ScreenHaystack's blind zones; the left
bias) and (ii) left-to-right priors about menus, toolbars and side panels that mislead planning
(macOSWorld's Dock example). Arabic interface text could lower success through (iii) weaker
reading of Arabic glyphs at the model's input resolution (KITAB-Bench, GlotOCR) and (iv) lost
word overlap between English instructions and interface labels (lexical coupling).

**Predictions (registration v2), each with its falsifier:** P1, Phase 0 admits LibreOffice
(falsified by any failed LibreOffice gate item, including a residual leak); P2, the delta
certification passes; P3, D < 0 (falsified if D is SMALL, unqualified); P4, T < 0 (falsified if
T is SMALL); P5 and P6, the lexical-overlap and screen-half moderators have negative slopes
(falsified if the 95% CR2 interval lies above 0; a mechanism is named only if it lies below);
P7, the en cell is within 10 pp of S1a's English success on the same tasks.

**Kill criteria:** K0, an application failing Phase 0 is dropped, and fewer than 26 admitted
tasks is an infrastructure exit; K1, a failed delta certification stops Phase 1 on this image;
K2, more than 5% infrastructure losses in a cell, INCOMPLETE; K3, more than 2% step-0 failures
in a cell, INCOMPLETE; K4, D and T both SMALL (unqualified) and neither PRESENT, publish the
robustness null (a qualified SMALL is published as such, with its rare-break bound);
K5, neither PRESENT, no reasoning-language arm; K6, cap reached, analyse complete task blocks
if at least 26.

## Cheapest Decisive Pilot

1. **Phase 0 (0 GPU-h; host CPU lane jobs).** The derived image, the delta certification, the
   oracle with positive controls, the functional and config probes. It decides whether a
   render-certified localized OSWorld exists for each application (K0, K1). Its cost is VM
   time on the CPU lane: the oracle needs four cells x 43 post-setup states plus the sweep, the
   suite a few hundred sessions.
2. **Phase 1 (one GPU job, cap 5.98-7.98 GPU-h by K).** Qwen3.5-9B on the admitted tasks in four cells, n = 16 episodes per task-cell if K at most 35 else 12, split across both harnesses, in one session at V = 20 (1,664-2,240 episodes). It decides D at the registered rules; by the simulation it detects a diffuse 5 pp direction effect with probability 0.89-0.97 and a break-type one rarely. No pilot precedes it: S1a's records already give the English base rates, the rerun noise and the price.

## Controls, Baselines, and Ablations

- **Within-environment controls.** en is the baseline; ar-LTR changes only the text; en-RTL
  only the layout; ar-RTL both. Every cell of a task runs in one serving session, interleaved
  in seeded task blocks, with episodes split equally across the two certified harnesses.
- **Manipulation checks, exact or calibrated, before any GPU job.** O1 structure, O2
  text-run identity across layout, O3 reflection, O4 order under text swap, O5 document-region
  identity, O6 invisibility of the isolation in English (against S1a's stock image), with A/A
  tolerances and planted positive controls; per episode in Phase 1, the step-0 screen and the
  keyboard map.
- **Held fixed.** Instructions, documents and checkers (English); the system shell (English,
  LTR); number and date formats and the document default language (`en-US`); LibreOffice's CTL
  support at one pinned value; Calc's English function names; autocorrect; the keyboard map
  (`us`, no input method); model, decoding, step cap, settles, harness prompts.
- **Baselines not used.** macOSWorld's numbers (another platform, task set and agent set) are
  context. S1a's English records are a reference for the en cell (P7), not a control.
- **Deferred ablations.** Reasoning and instruction language, other languages, full system
  localization, a second model (Qwen3.5-4B ran the same tasks in S1a and is the obvious
  extension), the accessibility observation setting.

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

## Evaluation, Statistics, and Leakage Checks

- **Primary estimand.** D = mean over tasks of D_t = ((y_arR - y_arL) + (y_enR - y_en)) / 2, cell
  means over n episodes split equally across the two certified harnesses. Secondary: T, the
  interaction I, the total Delta = T + D, the dossier's two conditional contrasts, D and T by
  harness and application, fractional checker scores, process metrics and two moderators.
- **Test and decisions.** Paired t on the K task-level D_t (df K - 1), two-sided 0.05: PRESENT
  (labelled by sign); 90% t interval inside +/-5 pp and the rare-break bound below 5 pp: SMALL;
  a small interval with the bound at or above 5 pp: SMALL_RARE_BREAKS_NOT_EXCLUDED; otherwise
  INCONCLUSIVE. Sign-flip sensitivity (PRESENT_FRAGILE on disagreement). The rare-break bound:
  with B tasks showing a large drop (D_t at most -0.25), the exact one-sided 95% upper bound U on that
  share, times the en cell's mean success. Reported beside it: the finite-task interval and a sharp-null
  randomization test.
- **Why tasks, not episodes, limit power.** Qwen3.5-9B is close to deterministic on these tasks:
  of the 43 candidates, 17 were solved in 8 of 8 S1a episodes, and the fitted propensity prior is
  U-shaped (Beta(0.107, 0.167) over (task, harness) cells). It reproduces
  S1a's k-histogram over 4 episodes ([0.513, 0.0844, 0.0325, 0.0714, 0.2987] observed against
  [0.5202, 0.0682, 0.0515, 0.0614, 0.2987] modelled) and the rerun discordance (0.0996
  against 0.0991). A mirror effect on such tasks is a change in a few
  tasks' outcomes, so its between-task heterogeneity, not the episode count, sets the interval.
- **Simulated operating characteristics of the registered design** (`power-osworld.json`;
  3,000 replicates per cell over seeds 42, 43, 44; each selected (task, harness) cell's success
  probability drawn from its posterior given S1a's 4 episodes; one serving session with a common
  logit shift of SD 0.3; T = -5 pp with the same structure throughout; the superpopulation target
  calibrated on a fixed bank). Probability of PRESENT (harm) at a true D of -5 pp, by effect
  structure, at the registered n, and the null rows:

| Task set (K, registered n) | uniform logit shift | proportional, all tasks | proportional, half the tasks | proportional, a quarter of the tasks | complete breaks | null: false PRESENT | null: SMALL (qualified + unqualified) | null: SMALL unqualified |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| LibreOffice strict (26, 16) | 0.89 | 0.79 | 0.65 | 0.44 | 0.09 | 0.047 / 0.043 | 0.90 / 0.26 | 0.00 / 0.00 |
| LO + Thunderbird strict (31, 16) | 0.93 | 0.86 | 0.75 | 0.55 | 0.12 | 0.049 / 0.045 | 0.96 / 0.42 | 0.00 / 0.00 |
| LO + Thunderbird incl. conditional (36, 12) | 0.93 | 0.84 | 0.74 | 0.58 | 0.17 | 0.053 / 0.040 | 0.94 / 0.49 | 0.12 / 0.02 |
| all 43 (43, 12) | 0.97 | 0.90 | 0.83 | 0.67 | 0.21 | 0.051 / 0.046 | 0.98 / 0.65 | 0.69 / 0.11 |

  The two null columns are a null with no direction effect and a null in which mirroring moves
  each task's success up or down (task-specific logit perturbations of SD 1, mean change 0). The
  second is what greedy agents on new screenshots plausibly do; it leaves the false PRESENT rate
  at the nominal level but makes equivalence rarer. Under either null an unqualified SMALL is
  impossible at K = 26-31 (the bound stays at or above 5 pp) and reached in
  0.12 / 0.02 of replicates at K = 36 and 0.69 / 0.11 at K = 43.
- **Power by n** (PRESENT, harm):

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

- **Equivalence errors and coverage at the registered n** (true D = -5 pp). The t interval
  under-covers when the effect is a few complete breaks (0.823-0.883), so
  a small interval alone would wrongly call SMALL in 0.140-0.191 of those
  replicates; with the rare-break bound the unqualified SMALL rate is at most 0.038 in every
  structure:

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

- **Cost** (the Q2 design study's slot rule; central = the mean S1a slot of the selected tasks,
  high = every episode at the 15-step cap's slot):

| Task set (K) | n | episodes | physical GPU-h (central / high slot) | registered cap incl. overlay, GPU-h (central / high) | wall hours, one job (high) |
|---|---:|---:|---:|---:|---:|
| LibreOffice strict (26) | 8 | 832 | 1.96 / 2.345 | 2.617 / 3.1 | 2.28 |
| LibreOffice strict (26) | 12 | 1248 | 2.909 / 3.488 | 3.817 / 4.55 | 3.43 |
| LibreOffice strict (26) | 16 | 1664 | 3.859 / 4.63 | 5.017 / 5.983 | 4.57 |
| LO + Thunderbird strict (31) | 8 | 992 | 2.332 / 2.785 | 3.083 / 3.667 | 2.72 |
| LO + Thunderbird strict (31) | 12 | 1488 | 3.467 / 4.147 | 4.517 / 5.383 | 4.09 |
| LO + Thunderbird strict (31) | 16 | 1984 | 4.603 / 5.509 | 5.95 / 7.083 | 5.45 |
| LO + Thunderbird incl. conditional (36) | 8 | 1152 | 2.689 / 3.224 | 3.533 / 4.217 | 3.16 |
| LO + Thunderbird incl. conditional (36) | 12 | 1728 | 4.003 / 4.806 | 5.2 / 6.2 | 4.75 |
| LO + Thunderbird incl. conditional (36) | 16 | 2304 | 5.317 / 6.388 | 6.85 / 8.2 | 6.33 |
| all 43 (43) | 8 | 1376 | 3.181 / 3.839 | 4.15 / 4.983 | 3.78 |
| all 43 (43) | 12 | 2064 | 4.741 / 5.729 | 6.117 / 7.367 | 5.67 |
| all 43 (43) | 16 | 2752 | 6.301 / 7.618 | 8.083 / 9.75 | 7.56 |

- **Analytic cross-check** (exact noncentral t, 80% power, two-sided 0.05; v = tau2 +
  sigma2/n with sigma2 at the posterior mean of the selected cells, 0.092-0.111):

| Task set (K) | tau2 | n = 8 | n = 12 | n = 16 | n infinite |
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

- **The answer to D68's question.** Yes for a diffuse effect, no for a concentrated one. Under the registered estimator, a true -5 pp direction effect is called PRESENT (harm) with probability 0.89-0.97 when it is a uniform logit shift and 0.79-0.90 when it is a proportional reduction on every task, across the four task sets (K = 26-43, n = 16 or 12, caps 5.98-7.98 GPU-h including the overlay reserve, all below 8); 0.65-0.83 when half the tasks carry it, 0.44-0.67 when a quarter do, and 0.09-0.21 when it consists of complete breaks in about 8% of tasks. The false PRESENT rate under the null is 0.040-0.053. More episodes cannot rescue the concentrated cases: with near-deterministic outcomes the limit is the number of tasks. A design that also had to detect complete
  breaks in a few percent of tasks would need several times more tasks than S1a's certified pool
  holds in these applications.
- **Leakage and selection.** Tasks are selected on S1a's English episodes, which are independent of
  Phase 1; Phase 1 re-measures all four cells, so selection and regression to the mean shift the
  English level, not the paired contrasts. The en cell is compared with S1a's records on the same
  tasks and harnesses (P7) as a description of the derived image's effect on the English agent.
  Moderator codings come from the Phase 0 trees, frozen before any GPU job.
- **Missing data and infrastructure.** One re-queue per lost episode; a task enters only if each
  of its four cells has at least n - 1 valid episodes; more than 5% losses or more than 2% step-0
  failures in a cell makes the run INCOMPLETE.
- **Statistical reporting protocol.** K-Dense `statistical-analysis` and the ARS statistical
  reporting standards: effect sizes with intervals, paired and clustered errors, an assumption
  check through the sign-flip sensitivity and the simulated coverage, and no HARKing (moderators
  and the rare-break bound registered before data).

## Compute and Reproducibility

Engine: vLLM v0.31.0 (commit `db9527a4`) on
`docker.io/vllm/vllm-openai@sha256:b18abb2df97b8f798e81862bd93f872ea18613372e2c3adc0cc2ac21e66ac12f`
with the cu129 overlay rebuilt from the freeze commit by
`scripts/build_vllm_overlay_on_h100.sh` and its provenance receipt, as S1a. Model:
Qwen3.5-9B revision `c202236235762e1c871ad0ccb60c8ee5ba337b9a` (receipt `0a9e052d`), weights on
the host. Agent loop, harness adapters, VM lane, records, rescoring and DR0-style
infrastructure accounting: S1a's code of record (`harness/q2_stage1/`, freeze commit
`d5f5798`), unchanged except for the cell selector and the step-0 and keyboard checks, which
are new code reviewed before the freeze. Image: the derived image (to be built in Phase 0), its
digest recorded.

Launch path (as S1a; a Phase 1 manifest does not exist yet; dry run, test-only, submit on an
empty queue, one GPU job and its CPU VM job):

```bash
uv run --locked python scripts/submit_docker_research_job.py infra/slurm/host-single-node/s2-arabic-cua-locale-v2-phase1.yaml --dry-run
uv run --locked python scripts/submit_docker_research_job.py infra/slurm/host-single-node/s2-arabic-cua-locale-v2-phase1.yaml --test-only
uv run --locked python scripts/submit_docker_research_job.py infra/slurm/host-single-node/s2-arabic-cua-locale-v2-phase1.yaml
```

The submitter wraps `sbatch infra/slurm/host-single-node/docker-research.sbatch`; the VM
lane runs as a CPU-only Slurm job beside the GPU engine job, as S1a's did (D12). Every
executable pilot also runs as an orx node through `uv run --locked python
scripts/orx_run.py` over a committed `experiments/orx/node.yaml` (`kind: cpu-doctor` for a
registered `scripts/run_s2_locale_gate_doctor.py` wrapping the oracle; `kind: slurm-manifest`
for Phase 0's CPU lane jobs and Phase 1).

Machine fields: seeds: [42, 43, 44]; gpu_hours: 7.98 at most (between 5.98 and 7.98 by the admitted K) (Phase 1 cap at the registered n
for the admitted K, plus the 0.1 GPU-h overlay reserve; Phase 0 is 0; separate from the
gauntlet's 0.3 GPU-h reviewer budget).

Cost model (`compute/repair-d68/power-osworld.json` `cost`): the Q2 design study's slot rule.
Slot occupancy at V = 20 sets GPU time (the engine never queued in S1a). Selected tasks' mean 9B slot 163-165 s (central); 197.73 s for episodes that ran to the 15-step cap (high, used for the cap). Phase 1 caps by K at the registered n: 5.98 (K = 26) to 7.98 (K = 35) GPU-h including the 0.1 GPU-h overlay reserve (`registered-caps.json`); physical use at the central price is about two thirds of the cap.

Checkpoints and resume: as S1a, each episode is the unit of work, records are appended as
episodes finish, and a fresh job skips completed (task, cell, harness, rerun) keys and continues
the seeded order; a preempted job is resubmitted with the same manifest and its time counts
against the cap (D22). Artifacts: per-episode records, the oracle record, moderator codings and
the decision record in the public repository; screenshots and trajectories on the host and in
the private archive.

## Safety, Data Rights, and Monitorability

- **Safety.** The agent acts only inside offline VMs on public OSWorld tasks with synthetic or
  public documents; it generates no code that the host runs (D3, D7 not triggered). No real
  user data, no outward messages (the VMs are offline; Thunderbird tasks use local profiles).
- **Monitorability.** Every action, observation hash, token count, checker input hash and
  verdict is logged per episode, as in S1a; thinking traces are kept.
- **Data rights.** OSWorld task configs and checkers Apache-2.0; LibreOffice and Thunderbird
  (and their language packs) MPL-2.0; GIMP GPL-3.0 (run, not redistributed); GTK LGPL; fonts
  OFL or the distribution's licence, recorded; Qwen3.5-9B Apache-2.0. Pseudo-locale catalogs
  stay inside the image, which is not redistributed. The Chromium fixtures in the bundle are
  synthetic.
- **Outward actions.** None. Publishing the derived image or any screenshot would be Kevin's
  call (D2).
- **Public-repo hygiene.** No host address, credentials or private data in any artefact.

## Negative-Result Value

| Outcome | What it says | What it closes |
|---|---|---|
| K0 for LibreOffice (a residual leak or a failed gate item) | LibreOffice cannot be localized and mirrored to the gate's standard without code changes; the leak inventory says where | S2 on this stack unless another application set reaches 26 tasks; a useful i18n record either way |
| K1 | The localized image breaks the certified action path | Phase 1 on this image |
| D SMALL (unqualified) | Application mirroring changes this model's success by less than 5 pp on tasks like these, and complete breaks in more than a few percent of tasks are excluded | The mirror half of the open split for application-level localization at this scale; a publishable robustness null |
| D SMALL_RARE_BREAKS_NOT_EXCLUDED | The mean change on these tasks is under 5 pp, but rare complete breaks are not excluded | Sizes the task count a successor needs |
| D PRESENT, positional moderator named | A mirror cost that tracks target relocation | Points mitigation at grounding (position augmentation), not language |
| D PRESENT, mechanism unresolved | A mirror cost without an identified route | A successor with a direction-sensitive-step coding |
| T PRESENT, lexical moderator named | An Arabic-interface cost that tracks lost instruction-label overlap | Points at lexical matching, not glyph reading |
| INCONCLUSIVE | Nothing beyond the intervals | Sizes a successor (more tasks, a second model) |

## Preflight Doctors

| Doctor | Status | Evidence | Remediation |
|---|---|---|---|
| Source | PASS | orx alphaXiv and OpenAlex reachable from the Mac; wave 1's 113 + 10 counted queries and this run's 22 (14 orx, 4 ACL Anthology, 4 OpenReview) with returned ids and raw-output SHA-256; 13 primary-source fetches with line numbers; cutoff 2026-10-10; degraded coverage recorded (Semantic Scholar not used in this run, Chinese-language venues, social media) (`doctors/source.json`) | Semantic Scholar keyword searches and a citer refresh when the host relay is free |
| Citation | PASS | Claim registry C01-C56 with locators, dates and read status; every primary URL snapshotted with its HTTP status and hash; source claims carry line numbers; OpenReview rows UNVERIFIABLE_ACCESS for full text (`doctors/citation.json`) | Read PuMVR and GAIA-v2-LILT in full before any delta row rests on them |
| Novelty | FAIL | No direct prior under the recorded coverage, but this run's blind critic and novelty refuter have not run (`doctors/novelty.json`) | Run the blind critic on the fresh `blind/` packet and the novelty refuter (58 queries remain, above the reserve of 30) |
| Design | PASS | Intervention (application catalog x layout switch, isolated catalogs), controls (en baseline; O1-O6 with positive controls; functional and config probes; step-0 and keyboard checks), falsifiers P1-P7 and kill criteria K0-K6, primary estimand D with a three-way decision and the rare-break bound, design before data on measured inputs: a propensity model fitted on S1a's cells and checked against them, and a simulation of the registered estimator over six effect structures (PRESENT at -5 pp: 0.89-0.97 for a uniform logit shift, 0.09-0.21 for complete breaks; null false PRESENT at most 0.053; unqualified false SMALL at most 0.038). Disclosed limits: break-type effects are underpowered at this K, and an unqualified SMALL needs about 43 tasks (`doctors/design.json`) | Build Phase 0 and run its gate as a cpu-doctor node; add tasks (a full-pool extension) if break-type effects must be detectable |
| Compute | FAIL | No derived image, delta certification, oracle run on the real applications, Phase 1 manifest, Slurm dry run or executable pilot (`doctors/compute.json`, `compute/attestations-not-run.md`) | Phase 0 as lane CPU jobs after acceptance; then the Phase 1 manifest's dry run and test-only |
| Safety | PASS | Offline VMs, public tasks, no code execution by the host, permissive or recorded licences, no outward actions, host rule respected (`doctors/safety.json`) | none |

Protocols followed: Citation, the ARS claim-verification protocol (claim registry, locators,
verdicts, UNVERIFIABLE_ACCESS); Design, the vendored K-Dense `experimental-design` and
`statistical-power` skills (design before data; a 2x2 blocked by task and session; power by
exact computation and by simulation of the registered estimator on measured inputs);
Evaluation, K-Dense `statistical-analysis`; Novelty, K-Dense `literature-review` (PRISMA counts
in the header). The integrity gate's seven failure modes are answered in the registration.

## Independent Adversarial Reviews

Reviewer A: FAIL | provider=not-run | model=not-run | run_id=not-run | artifact=none (this run's reviewers run after the blind critic and the refute-first triad; wave 1's reviews are in the gauntlet record)

Reviewer B: FAIL | provider=not-run | model=not-run | run_id=not-run | artifact=none (the open-weight reviewer's lane job runs only on an empty queue)

No review is signed: no trusted Ed25519 store exists (D24).

## Scorecard

| Dimension | Reviewer A | Reviewer B | Defect/evidence |
|---|---:|---:|---|
| Question and strategic fit | 0 | 0 | not yet reviewed in this run (wave 1: 6 and 7) |
| Primary-source evidence | 0 | 0 | not yet reviewed (wave 1: 8 and 7) |
| Defensible novelty delta | 0 | 0 | not yet reviewed (wave 1: 5 and 4) |
| Mechanism and falsifiability | 0 | 0 | not yet reviewed (wave 1: 6 and 4) |
| Controls and causal identification | 0 | 0 | not yet reviewed (wave 1: 4 and 4) |
| Evaluation and statistics | 0 | 0 | not yet reviewed (wave 1: 6 and 5) |
| Feasibility and information per GPU-hour | 0 | 0 | not yet reviewed (wave 1: 3 and 4) |
| Reproducibility and artifact contract | 0 | 0 | not yet reviewed (wave 1: 6 and 2) |
| Safety, data rights, and monitorability | 0 | 0 | not yet reviewed (wave 1: 9 and 7) |
| Independent adversarial review quality | 0 | 0 | not yet reviewed (wave 1: 5 and 5) |
| **Total** | **0** | **0** | Lower total is authoritative (wave 1: 58 and 49, score 49) |

## Iteration Log

| Wave | Score | Highest-impact defect | Change | Result |
|---:|---:|---|---|---|
| dossier (2026-10-06) | not scored | String swap cannot hold layout fixed; Relay not internationalized; 18 tasks underpowered; a11y control identical by construction | Corrected question and kill lines | dossier section 5 |
| wave-1 synthesis (2026-10-10) | not scored | The dossier's Phase 1 cannot reach its 5 pp line; its oracle passes a half-mirrored layout | Relay 2x2, exact CPU checks, geometric and render gates, Stage 1a pilot and gate | reviewed in wave 1 |
| 1 (2026-10-10) | 49 (58, 49) | Decisiveness on Relay (the gate essentially cannot pass), then off-diagonal bidi leakage | recorded; triad 3 of 3 refuted; D68 ordered one repair | row `1a24cee8...` |
| D68 repair (2026-10-10/11) | not scored | as wave 1 | Substrate moved to S1a's OSWorld stack; 43-task screen; power from S1a's records under the registered estimator; catalog isolation and factorial render oracle (validated); rare-break bound on SMALL; D53 coverage stated; novelty coverage extended | awaiting this run's blind critic, triad and reviewers |

## Deterministic Doctor Output

Verbatim output of `uv run --locked python scripts/research_direction_doctor.py
program/proposals/2026-10-10-s2-arabic-cua-locale.md` (exit 1) on the committed bundle, also
stored as `evidence/2026-10-10-s2-arabic-cua-locale/doctors/research-direction-doctor-output.json`.
Against wave 1's output, the Design doctor now passes and no other doctor changed state. Readings the doctor does not
make for itself, as in wave 1: "all declared budgets must be positive" comes from parsing the
declared `gpu_hours=0.3` as an integer (the budget is honest and is not rounded up to pass);
the doctor applies no 79 cap because its executable-pilot check is textual, while by the
gauntlet rule's cap table this proposal is capped at 79 (no executable pilot) and 89 (no
independent, signed, provider-distinct review), and cannot reach 100 without D24's trust
store; and it counts the two OpenReview snapshots as resolved because those pages return
HTTP 200, although their bodies are a browser challenge.

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
    "compute container_smoke did not pass",
    "compute slurm_test did not pass",
    "compute provenance_verification did not pass",
    "doctor artifact 2 did not pass",
    "doctor artifact 4 did not pass",
    "evidence bundle lacks audit_log artifact"
  ],
  "path": "/Users/kevinliu/repos/cotcodec-wt-gauntlet-s2/program/proposals/2026-10-10-s2-arabic-cua-locale.md",
  "remediation": [
    "all declared budgets must be positive"
  ],
  "reviewerTotals": {
    "A": 0,
    "B": 0
  },
  "sourceCounts": {
    "allUrls": 39,
    "recognizedPrimaryUrls": 25
  },
  "status": "FAIL"
}
```
