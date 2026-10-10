# Research Direction: S2 first step, Arabic interface text versus mirrored layout for an open-weight computer-use agent on a locale-parameterized Relay (Phase 0 locale fixture and oracle gate; Phase 1 design with a power gate sized from S1a's noise floor)

**Status:** draft for gauntlet wave 1 (program decision D67); synthesis by the single owner on 2026-10-10 from four independent discovery cells (frontier and novelty, kill-shot, cross-domain, asset and cost) of the S2 gauntlet workflow; the blind closest-prior critic, the refute-first triad and the two provider-distinct reviewers have not run; the registration `program/preregistrations/s2-arabic-cua-locale-v1.md` is a DRAFT, not frozen or admitted, with no ledger row; no executable pilot exists; the sum of the registered caps (17.0 GPU-h) is over 8 GPU-h, so admission of the GPU stages is Kevin's under D24 whatever this gauntlet scores; a score of 100 cannot be certified in this repository (D24)
**Owner:** Kevin Liu (program owner); synthesis, mechanism statement, identification design, simulation and draft registration written by a Claude agent acting as the gauntlet's single synthesis owner
**Source cutoff:** 2026-10-10
**Coverage limits:** orx 0.2.2 only for literature search (alphaXiv keyword and embedding search, OpenAlex; the build reports itself outdated against 0.2.18; alphaXiv keyword retrieval is recency-biased, offset by `--prioritize historical` on 7 queries and a pre-2026 bounded embedding query); 113 counted orx discover queries (frontier 45, kill-shot 33, cross-domain 21, asset 10, synthesis 4) and 9 more that failed with HTTP 429 (not counted); the OpenReview search API (11 term searches, abstract-level; per-note pages and PDFs return a browser challenge and were not bypassed, so every OpenReview item is abstract-only, UNVERIFIABLE_ACCESS for full text); Semantic Scholar through the H100 host relay for citation lists only (4 calls; all 6 keyword searches returned HTTP 429); the OpenAlex API (2 calls before the IP's free daily budget ran out; 4 ACL-DOI-filtered searches failed, so the ACL Anthology was searched only through OpenAlex and web search); arXiv abstract pages for version histories; Crossref metadata (11 lookups); 18 web searches and fetches for standards, platform documentation and model cards; local source code (Relay at `e6c815e`, LibreOffice core at `08f5d410`, Chromium). Not searched: live X, Reddit, Hacker News, Google Scholar, patents, Chinese-language sources, GitHub code search, CHI and UIST beyond OpenAlex, vendor GUI-model technical-report appendices (Qwen-UI-Agent, UI-Venus-2, UI-TARS-2 seen by title only). Citing-paper lists (34 for the closest prior) were screened by title. About 650 records identified, about 120 screened by abstract, about 30 read in full or by targeted section (PRISMA-style counts from the cells).
**Budgets:** queries=150; wall_minutes=600; tokens=8000000; dollars=150; waves=3; gpu_hours=0.3
**Novelty verdict:** NO_DIRECT_PRIOR_FOUND
**Safety verdict:** PASS
**Evidence bundle:** evidence/2026-10-10-s2-arabic-cua-locale/bundle.json

The novelty verdict field uses the doctor's vocabulary. The merged
discovery verdict is NARROWED, with the residual STILL_OPEN (frontier and
kill-shot cells independently; none returned OCCUPIED): the split of an
executable GUI agent's Arabic drop into a text part and a mirroring part,
measured inside one environment, has no direct prior under the coverage above.
The method around it is not new: paired, grader-preserving UI variants are
now standard (WebPageBench, BreakingWeb), and UI language has already been
used as a bundled robustness perturbation (RealGUINoise). The claim is a
measurement, scoped to one model and one app.

The gauntlet's GPU budget (0.3 GPU-h) is for reviewer inference only. No
host job was run for this proposal; the host queue was read once (empty at
2026-10-10T21:42:52Z).

## Scope and what changed from the dossier

This proposal covers S2's first step only: Phase 0 (CPU: extract Relay's
interface strings into i18next catalogs, make the locale a fixture
parameter, and gate the result with an oracle) and the design of Phase 1
(about 15 GPU-h) with a power gate sized from S1a's measured noise floor. The
reasoning-language arm (d), other locales, and any training are out of scope.

The four cells were merged by mechanism. Fifteen mechanisms change S2 as the
dossier wrote it (`program/evidence/2026-10-06/question-dossier.md`,
section 5). Synthesis re-checked each against the primary source, the Relay
code (read-only at `e6c815e`), S1a's records, or its own simulation
(`evidence/2026-10-10-s2-arabic-cua-locale/compute/power-gate.py`,
seeds 42, 43, 44).

| # | Mechanism (cells) | What it does to the dossier's S2 | Where handled |
|---:|---|---|---|
| M1 | **The dossier's Phase 1 cannot reach its own 5 pp line** (kill-shot simulation, cross-domain and asset analytics; synthesis reproduced it with an exact noncentral t). Its contrast ar-RTL minus ar-LTR at 8 episodes per task-cell (4 seeds x 2 reruns) over 18 tasks has an 80%-power MDE of 7.3-8.8 pp with no effect heterogeneity and 8.1-9.4 pp at the gate's heterogeneity, for S1a's within-cell variance 0.043-0.0625 | Redesigned: a 2x2 of interface text by direction (adds en-RTL), the direction main effect D as primary (two thirds of the conditional contrast's sampling variance for the same episodes, and with T it sums exactly to the total drop), all episodes on pixels, n per cell set by a registered gate on the pilot's informative tasks. The redesign reaches about 4.6-5.0 pp (n = 24) at 18 informative tasks inside 15 GPU-h only if the price, the variance and the floor cooperate (M10) | Registration "Power gate", "Estimands" |
| M2 | **The a11y "negative control" is identical by construction** (dossier judge 3; asset cell): Relay's a11y observation is `ariaSnapshot()` plus a role/name list in DOM order, and `dir=rtl` does not change DOM order | No a11y GPU arm (432 episodes freed). Gate G2b checks byte identity of the a11y snapshot between ar-LTR and ar-RTL (and en and en-RTL) at every reference state on CPU, which is exact rather than a noisy GPU contrast | Registration gate G2b |
| M3 | **The dossier's oracle gate passes a half-mirrored layout** (kill-shot probe): under a naive `dir=rtl` on one Relay screen, 37 of 88 interactive elements were not within 24 px of their mirrored positions, hover toolbars covered author names, and the DOM tree was unchanged; `src/style.css` has 48 physical-direction declarations and 0 logical ones (synthesis count; cells 44-45 without corner radii) | Logical-CSS conversion and a frozen mirror specification (Firefox RTL guidelines); a geometric mirror-fidelity gate G5 in the GWALI layout-graph tradition (boxes at W - x - w within 4 px for at least 98% of boxes, no clipping, no new overlap) and a text-swap layout gate G6 | Registration P0.3, G5, G6 |
| M4 | **A catalog-driven oracle would be circular** (asset and kill-shot cells): Relay's browser recipes locate elements by English accessible names (86 `getByRole` calls in one spec) on seeds 42 and 43 only; its runner references are API-only (`runner/workflow-reference.mjs:143-144`) | Recipes re-keyed to catalog-independent test ids; a third seed (44); gate G12 replays every reference trajectory as coordinate actions through the agent's own executor in every locale (the Relay analogue of D53's action-path certification, on CPU) | Registration P0.7, G1, G12 |
| M5 | **"Glyph effect" overclaims** (kill-shot and cross-domain cells): ar-LTR minus en changes language, script and the word overlap between English instructions and interface labels together ("thread", "pin", "topic", "Later", "DM"); lexical coupling drives GUI grounding (2608.21794) and cross-script binding collapses (2608.12333) | Renamed "Arabic interface text" (T); a pre-registered lexical-overlap moderator; the en-RTL cell gives a mirror effect with fully readable text | Registration "Estimands", P0.10 |
| M6 | **Mirroring relocates targets, so a "mirror effect" may be positional** (frontier and cross-domain cells): model-specific grounding blind zones, some weaker on the right (ScreenHaystack, Qwen3-VL-8B down 16.1 pp inside them); VLMs describe left content first in 97% of cases even for an Arabic-finetuned model under Arabic prompting (2512.18231) | Every action's target box is logged; a pre-registered moderator regresses D_t on the share of reference targets that change screen half; click-landing rates by screen third are reported | Registration P0.9, P0.10, "Estimands" |
| M7 | **The treatment is weak** (all cells): chrome is 18% of visible characters on one first screen (kill-shot) and 22-25% across the 18 first screens (asset, pooled 24.3%); content and grader strings stay English by design | The estimand is named "chrome localization over an English workspace"; the chrome share is measured per screen and reported; no claim about full Arabic deployments | Registration P0.1, "Reported regardless" |
| M8 | **Bidi and numeral artefacts** (kill-shot probe; cross-domain cell): English text in RTL containers rendered "AM 9:33" and moved trailing periods left; Node 24's ICU gives Arabic-Indic digits for ar-EG and ar-SA; Relay hard-codes `toLocaleTimeString('en-US')` at `src/main.jsx:630, 716, 1178` | `dir="auto"` on user content and inputs; numerals, dates and times held at en-US formatting in every cell (declared, not part of the treatment); gates G8 (bidi order) and G9 (formats identical) | Registration P0.4, G8, G9 |
| M9 | **No Arabic font** (cross-domain and asset cells): Relay's bundled fonts cover 0-1 Arabic code points and the host lists no Arabic font, so the glyph treatment would depend on the runner's fallback stack | Noto Sans Arabic (OFL 1.1) pinned and served from the app origin after Lato; G7 OCR round trip against a control render; G10 font check | Registration P0.5, G7, G10 |
| M10 | **The gate's inputs do not exist** (kill-shot and asset cells): no Relay noise-floor run anywhere in the program; S1a's floor is OSWorld VM tasks at 15 steps, Relay is a browser app at up to 40; frontier models passed 3 of 24 Relay pixel runs (19 blocked, 14 by connection failures), so Relay's pixel base rate for a local model is unknown | A Stage 1a English pilot (144 analysed episodes, cap 2.0 GPU-h) measures per-task base rates, Relay's own seed and rerun variance and the price; the gate is computed from those, not from the transport | Registration "Stage 1a", "Power gate" |
| M11 | **No local-engine path or certified action path for Relay** (asset and kill-shot cells): Relay's hosted-router transport accepts only its one hosted endpoint (`runner/router.mjs:131-140`); D53 certifies only the OSWorld VM path; the host has no Node or Chromium image | Engineering prerequisites E1-E6 (bridge transport, qwen35vl adapter, `--network none` image from Relay's pinned Node base, container smoke, manifests, orx nodes) before any GPU stage | Registration "Engineering prerequisites" |
| M12 | **Novelty narrowed** (frontier and kill-shot cells): RealGUINoise (2609.38184) bundles a "Language Swap" perturbation; WebPageBench (2609.35026) and BreakingWeb (2609.35814) make grader-preserving paired UI variants standard | The novelty claim is restricted to the text-by-direction decomposition; the fixture and gate are infrastructure, not novelty | Novelty Ledger |
| M13 | **Few-cluster inference** (cross-domain cell): percentile cluster bootstraps and cluster-robust Wald tests over-reject at about 18 clusters (Cameron, Gelbach and Miller 2008) | Paired t on task means (df K - 1) primary, exact sign-flip enumeration as sensitivity, CR2 for moderator regressions, TOST at +/-5 pp before any null claim | Registration "Decision rules" |
| M14 | **Generality** (cross-domain cell): one model in one app is a coverage of 1 on both facets (Hardy et al. 2026, G-theory) | Claims scoped to (Qwen3.5-9B, Relay). Two routes to a powered study are recorded for successors: R1, a Relay template factory (S3's prerequisite), and R2, a LibreOffice 2x2 on S1a's certified harness via `SAL_RTL_ENABLED` and `UIMirroring` (verified in LibreOffice source) | Registration K1, route R2 |
| M15 | **Translation quality can manufacture gaps** (frontier cell: GAIA-v2-LILT reports up to 32.7% higher agent success under careful alignment than under minimal translation) | A back-translation pass and a native-speaker review with per-key verdicts, required before the Stage 1b freeze; counts reported | Registration P0.6 |

Corrections to the frozen dossier, recorded here because it is not edited:

1. "Compute the paired MDE from the WS1 Relay noise-floor run": no such run
   exists; S1a measured OSWorld VM tasks.
2. "The paired MDE is about 8-12 pp (estimate)": reproduced as 7.3-9.4 pp
   for the planned contrast at S1a's variance and gate heterogeneity
   (exact noncentral t; `power-gate.json` `B_analytic_mde_grid`).
3. "~15 GPU-h (range 4-34)" for the 864 episodes: the synthesis cost model
   gives 3.5 low, 5.8 central and 11.3 high GPU-h, with a 13.7 GPU-h cap,
   pricing a11y steps at 1.5x pixels from serving probe v2 (within the
   dossier's range).
4. "Most visible text (fixture content) stays English": measured, the chrome
   share is 18-25% of visible characters.
5. "A nonzero a11y mirror contrast beyond noise means the alignment is
   broken": the a11y observations of ar-LTR and ar-RTL are identical by
   construction, so the check is exact on CPU (G2b), not statistical.

## Claim and Research Question

**Question.** On Relay after real i18n extraction, with page structure,
element test ids, task steps and state graders identical in every locale and
English instructions throughout, how large are (D) the main effect of
right-to-left mirroring and (T) the main effect of Arabic interface text on
the screenshot success of Qwen3.5-9B, in a 2x2 locale design {English,
Arabic interface text} x {left-to-right, right-to-left}, with tasks as the
random factor and Relay's own seed-and-rerun noise as the floor? The main
study runs only if a registered power gate, computed from a Relay English
pilot, shows that the paired design can detect a 5 pp direction main effect
with 80% power inside a 15 GPU-h cap.

**Variable.** The locale cell of the fixture: catalog language (en, ar) and
document direction (ltr, rtl), with everything else (structure, test ids,
content, graders, instructions, numerals and formats, Playwright context
locale, model, decoding, step cap, seeds) held fixed.

**Claim scope.** `portability-protocol`: a measurement on one frozen model and
one app. Evidence level by outcome: Phase 0 gives an engineering artefact
with a passing gate; Stage 1a gives Relay's measured pixel floor; Stage 1b, if
run, gives a paired, clustered estimate with a three-way decision. No claim
about other models or apps, full Arabic deployments, instruction or reasoning
language, or training is licensed.

**Why the 2x2.** With three cells (en, ar-LTR, ar-RTL) the split of the total
drop depends on the order of the path (en to ar-LTR to ar-RTL) whenever text
and direction interact. With four cells the two main effects average both
paths and sum exactly to the total English-to-mirrored-Arabic drop:
ar-RTL - en = T + D. The fourth cell (English text, mirrored layout) is what
platform test practice already renders (Android's "Force RTL layout
direction", ICU's en-XB pseudo-locale, Windows' qps-plocm) and what
psycholinguistics uses to separate direction from script (Román et al. 2015,
mirror-reversed Spanish).

## Strategic Fit and Why Now

- **Program fit.** D67 restarts S2 now that S1a has given the Q2 noise floor
  (D66). Phase 0 is the locale fixture that S3's locale arm needs (dossier
  section 4: "S2's localized Relay (the locale fixture)"), so it pays off
  even if S2's Phase 1 never runs. The question also matches the program's
  identity: language as a controlled variable.
- **Why now.** The closest prior, macOSWorld, still leaves its split open in
  its latest version (v4, 2025-10-18): "Arabic glyphs or the mirrored UI
  layout, or both" (Sec. 5.2). None of its 34 Semantic Scholar citers or 27
  OpenAlex full-text mentions decomposes the drop (frontier cell, by title
  and abstract). Meanwhile UI language has entered robustness suites as a
  bundled perturbation (RealGUINoise, 2026-08-07), so the clean
  decomposition is the remaining, cheap estimand, and the window is open.
- **What it does not buy.** Phase 1 on 18 synthetic tasks is capped at a
  workshop-level measurement for one model. The simulation below makes the
  infrastructure exit the most likely outcome of this first step, and the
  proposal treats that exit as a first-class result.

## Primary-Source Evidence

Claim registry (full records with locators and read status in
`evidence/2026-10-10-s2-arabic-cua-locale/doctors/citation.json`).
"First-party" marks numbers reported by the producing team and not
replicated here; "abstract" marks sources read only at abstract level.

| Id | Claim | Source and date | Read |
|---|---|---|---|
| C01 | All-agent mean success excluding Advanced Apps: en 19.3%, ru 17.7%, zh 17.2%, ja 15.8%, ar 13.7% (28.8% relative drop for Arabic); attributed to "Arabic glyphs or the mirrored UI layout, or both" | [macOSWorld, NeurIPS 2025, v4](https://arxiv.org/abs/2506.04135), 2025-10-18, Table 4 and Sec. 5.2 | full text (frontier, kill-shot; synthesis re-read) |
| C02 | Per agent, 171 tasks, one run each, en to ar: Claude CUA 44.4 to 31.6 (and zh also 31.6), OpenAI CUA 33.3 to 28.1, Gemini 2.5 Pro 22.8 to 15.8, GPT-4o 8.8 to 2.9, UI-TARS-7B 5.3 to 2.3, ShowUI 1.2 to 1.8 | same, Table 3 | full text |
| C03 | English instructions with an Arabic UI (OpenAI CUA): 22.8% against 33.3% en/en and 28.1% ar/ar; System and Interface 13.8% against 41.4%; Claude CUA clicks the non-mirrored Dock location of System Settings | same, App. D.1 Tables 6-7; App. Fig. 19 text | full text |
| C04 | No error bars or significance tests (NeurIPS checklist item 7, "No") | same, checklist | full text |
| C05 | Six languages (EN, ZH, FR, RU, JA, TH), static parallel screenshots, no Arabic or RTL, not interactive; interactive benchmarks "inevitably introduce language-irrelevant variations" | [MPR-GUI, ACL 2026, v2](https://arxiv.org/abs/2512.00756), 2026-04-28 | full text |
| C06 | State and actions held fixed across 8 languages in text games; Arabic and Hebrew weakest; reasoning-language changes recover performance; Qwen3-4B Belebele Arabic 75.0 against English 84.1 | [Skill Issue](https://arxiv.org/abs/2608.25832), 2026-08-26, Table 4 | full text |
| C07 | Cross-lingual policy divergence normalized by each model's rerun reproducibility; frontier models retain 71-73% of their policy under greedy decoding | [Actions Speak Louder than Words, COLM 2026, v2](https://arxiv.org/abs/2608.11110), 2026-08-13 | full text |
| C08 | 7 GUI agent frameworks under 42 interactive noise types including "Language Swap" (Visual); results only by category; benchmark primarily English | [RealGUINoise](https://arxiv.org/abs/2609.38184), 2026-08-07, Table 10 and Limitations | full text |
| C09 | Event-level verification independent of interface language; one switch re-renders a task through another control implementation; 152 tasks (65 canonical, 87 variants), Russian interfaces, no locale variant | [WebPageBench](https://arxiv.org/abs/2609.35026), 2026-09-28 | full text |
| C10 | 519 clean/intervention task pairs, 7 self-hosted sites, 29 intervention families, grader preserved; agents lose 22.9% on average, humans 10.0%; no locale, translation or RTL intervention (full-text grep) | [Constructing Challenging Browser-Use Tasks](https://arxiv.org/abs/2609.35814), 2026-09-20 | full text |
| C11 | Model-specific grounding blind zones; Qwen3-VL-8B drops 16.1 pp inside them on ScreenSpot-Pro; GTA1-7B and UI-TARS-1.5-7B weaker toward the right | [ScreenHaystack](https://arxiv.org/abs/2609.32036), 2026-09-25 | full text |
| C12 | VLMs describe the left image first in 97% of cases, including the Arabic-finetuned AIN under Arabic (RTL) prompting | [Investigating Spatial Attention Bias in VLMs](https://arxiv.org/abs/2512.18231), 2025-12-20 | full text |
| C13 | Holding the language fixed and varying the script gives gaps up to 16% in 10 VLMs | [Not Truly Multilingual (PuMVR)](https://arxiv.org/abs/2606.17188), 2026-06-15 | abstract |
| C14 | 35 language-setting UI display bugs in Android apps, 19 of them RTL | [SUDFinder](https://arxiv.org/abs/2607.04120), 2026-07-05 | full text |
| C15 | Careful functional and cultural alignment raises agent success by up to 32.7% over minimally translated versions | [GAIA-v2-LILT, MELLM 2026](https://aclanthology.org/2026.mellm-1.13/) (arXiv 2604.24929), 2026-04-27 | abstract |
| C16 | Arabic OCR CER: Qwen2.5-VL-7B 1.20, GPT-4o 0.31, Gemini-2.0-Flash 0.13 | [KITAB-Bench](https://arxiv.org/abs/2502.14949), 2025-02-20 | full text |
| C17 | Arabic is the most degraded script across OCR models, Qwen3-VL-8B included | [GlotOCR Bench](https://arxiv.org/abs/2604.12978), 2026-04-14, Sec. 5.2 | full text |
| C18 | Qwen3.5-9B: "201 languages and dialects", ScreenSpot Pro 65.2, OSWorld-Verified 41.8 (first-party); no Arabic GUI or OCR result | [Qwen3.5-9B model card](https://huggingface.co/Qwen/Qwen3.5-9B), fetched 2026-10-10 | first-party |
| C19 | Grounding success tracks recovery of the visible label from the instruction's wording; concept binding collapses across scripts including Arabic | [Lexical Coupling in GUI Element Grounding](https://arxiv.org/abs/2608.21794), 2026-08-22; [M2BIND](https://arxiv.org/abs/2608.12333), 2026-06-02 | abstract; full text |
| C20 | S1a: D_w 12.5% pooled (9B 8.59%, 4B 16.41%), D_b 11.33%, no session excess (upper bound 0.78 pp), 9B session shift +5.5 pp (p 0.016), 9B cost 0.0027 GPU-h per episode; synthesis from `a1.jsonl`: 9B mean 12.04 steps, 59% of 9B base cells at 0 and 23% at 1 | `program/evidence/2026-10-10/q2-stage1-a1/RESULTS.md` (D66) | repository |
| C21 | Serving probe v2 on this host: 2.52-2.57 requests/s at 300 output tokens; a11y cell 1.129 against screenshot 0.752 GPU-h-equivalent (1.5x) | `program/evidence/2026-10-07/serving-throughput-probe-v2/README.md` | repository |
| C22 | Relay: `locale: 'en-US'` (`runner/environment.mjs:64`), English-name wait (`:79`), hosted-endpoint-only transport (`runner/router.mjs:131-140`), 18 tasks (6 controls, 12 workflows, `maxSteps` 60 and 80), graders return named checks, 48 physical-direction CSS lines and 0 logical, 86 `getByRole` in the deep-workflow spec on seeds 42 and 43, `en-US` formatting at `src/main.jsx:630, 716, 1178`, no Arabic glyphs in bundled fonts | [Relay](https://github.com/Kevin-Liu-01/Relay) at `e6c815e`, read-only by synthesis and cells | repository |
| C23 | Relay's English oracle: 91 of 91 node tests, 27 of 27 deep-workflow browser recipes and 14 of 14 control recipes on a scratch copy; about 2.2 CPU-minutes | asset cell logs (`compute/cells/` and the cell's scratch logs) | first-party, this program |
| C24 | Naive `dir=rtl` on release-sync: 37 of 88 interactive elements not within 24 px of mirrored positions; bidi artefacts in English text | kill-shot cell probe `compute/cells/s2kill__mirrorcheck.mjs` | first-party, this program |
| C25 | Interface study: pixel arm 3 of 24 passed, 19 blocked (14 by router connection failures) | Relay `evidence/campaigns/interface-study-2026-10-05/analysis.md` | first-party (Relay) |
| C26 | With participants and stimuli both random, power approaches a possibly small ceiling as participants grow | [Westfall, Kenny and Judd 2014](https://doi.org/10.1037/xge0000014) | abstract |
| C27 | More similar tasks raise model-ranking reliability by at most 0.097 when scaffold coverage dominates | [Agent Evaluation Reliability](https://arxiv.org/abs/2610.00651), 2026-09-30 | full text |
| C28 | Clustered and paired standard errors for evals; resampling saturates | [Adding Error Bars to Evals](https://arxiv.org/abs/2411.00640), 2024-11-01; [Measuring all the noises of LLM Evals](https://arxiv.org/abs/2512.21326), 2025-12-24 | full text |
| C29 | Few-cluster over-rejection and the wild cluster bootstrap-t; CR2 small-sample correction | [Cameron, Gelbach and Miller 2008](https://doi.org/10.1162/rest.90.3.414); [Pustejovsky and Tipton](https://doi.org/10.1080/07350015.2016.1247004) | metadata |
| C30 | Equivalence testing (TOST) for null claims | [Lakens, Scheel and Isager 2018](https://doi.org/10.1177/2515245918770963) | metadata |
| C31 | Layout graphs detect internationalization presentation failures at 91% precision and 100% recall on 54 web apps | [GWALI, ICST 2016](https://doi.org/10.1109/icst.2016.36) | author PDF |
| C32 | What to mirror and what not; logical CSS; base direction in `dir`; `dir="auto"` for user content | [Firefox RTL guidelines](https://firefox-source-docs.mozilla.org/code-quality/coding-style/rtl_guidelines.html); [W3C qa-html-dir](https://www.w3.org/International/questions/qa-html-dir); [CSS Logical Properties Level 1, WD 2025-12-04](https://www.w3.org/TR/css-logical-1/) | full page |
| C33 | Forced RTL with Latin text in platform practice; en-XB and qps-plocm pseudo-locales | [Android: support different languages](https://developer.android.com/training/basics/supporting-devices/languages); [Microsoft: pseudolocalization](https://learn.microsoft.com/en-us/globalization/methodology/pseudolocalization) | full page |
| C34 | `SAL_RTL_ENABLED` forces an RTL UI; `UIMirroring` can force LTR under an Arabic UI | [LibreOffice core settings.cxx at 08f5d410](https://raw.githubusercontent.com/LibreOffice/core/08f5d410a474badedeaa3fbabaea9b6f564d1b83/vcl/source/app/settings.cxx) | source |
| C35 | Reading direction manipulated causally within one script shifts spatial biases | [Román et al. 2015](https://doi.org/10.1038/srep18248) | abstract |
| C36 | Default RTL rendering of explanation labels gave OCR CER 0.820-0.979 | [When Explanations Cannot Be Read](https://arxiv.org/abs/2609.28565), 2026-09-23 | full text |
| C37 | Text-only multilingual WebShop tasks (14 languages); no rendering or RTL layout | [X-WebAgentBench, ACL Findings 2025](https://arxiv.org/abs/2505.15372), 2025-05-21 | full text |
| C38 | Multilingual agent gaps in text and tool settings: OmnilingualGAIA2 8.8-18.4 pass@3 points; BabelArena 23 languages | [OmnilingualGAIA2](https://arxiv.org/abs/2608.08775), 2026-08-09; [BabelArena](https://arxiv.org/abs/2609.23490), 2026-09-20 | abstract; full text |
| C39 | A factorial interface contrast with a stated resolution threshold over 75 tasks and 1,992 episodes (no locale factor) | [OpenReview irjWqxKeHm](https://openreview.net/forum?id=irjWqxKeHm), 2026-08-25 | abstract (UNVERIFIABLE_ACCESS for full text) |

## Closest Prior Work

1. **macOSWorld** ([2506.04135](https://arxiv.org/abs/2506.04135), NeurIPS
   2025, v4 2025-10-18; also [OpenReview YJxGJP8feU](https://openreview.net/forum?id=YJxGJP8feU)
   and [code](https://github.com/showlab/macosworld)). 202 interactive macOS
   tasks (171 in Arabic), five system languages with instructions translated
   by GPT-4o, six agents run once per task and language, success compared
   across languages, one cross-lingual analysis. It owns the UI-locale main
   effect on an executable desktop benchmark and names the open split. Its
   Arabic cell confounds script, mirroring, platform-level translation and
   instruction language; per-agent drops have an unpaired SE of about 5 pp at
   171 tasks and one run (frontier cell), and none carries an interval.
   **Delta:** the split, inside one environment, with an en-RTL and an ar-LTR
   cell, paired on tasks and seeds, with intervals, a noise floor and an
   oracle that certifies the mirrored layout.
2. **RealGUINoise** ([2609.38184](https://arxiv.org/abs/2609.38184),
   2026-08-07; ACL ARR August 2026). "Language Swap" is one of 42 noise types,
   reported only by category. **Delta:** a controlled decomposition, not a
   perturbation bundle; RTL and mirroring are absent there.
3. **WebPageBench** ([2609.35026](https://arxiv.org/abs/2609.35026)) and
   **BreakingWeb** ([2609.35814](https://arxiv.org/abs/2609.35814)). Paired,
   grader-preserving UI variants. **Delta:** neither has a locale or
   direction variant; the method is theirs, the factor is not.
4. **MPR-GUI** ([2512.00756](https://arxiv.org/abs/2512.00756), ACL 2026).
   Aligned static screenshots in six languages without Arabic. **Delta:** S2's
   executable, oracle-aligned locale fixture answers its critique of
   interactive benchmarks directly.
5. **Direction-versus-script priors outside agents**: spatial attention bias
   ([2512.18231](https://arxiv.org/abs/2512.18231)), vertical Japanese
   ([2511.15059](https://arxiv.org/abs/2511.15059), abstract), PuMVR
   ([2606.17188](https://arxiv.org/abs/2606.17188), abstract), Román et al.
   2015. They motivate treating direction as its own factor.
6. **Method priors**: rerun-normalized cross-lingual agent effects
   ([2608.11110](https://arxiv.org/abs/2608.11110)); the reasoning-language
   crossing with fixed state ([2608.25832](https://arxiv.org/abs/2608.25832),
   the closest prior for the deferred arm (d), not for this step).

The closest prior for blind discrimination is macOSWorld; its anonymized
mechanism paragraph and this proposal's are in
`evidence/2026-10-10-s2-arabic-cua-locale/blind/` (file names carry no role).

## Novelty Ledger

| Proposed component | Closest prior | Same | Delta | Confidence |
|---|---|---|---|---|
| Split of an executable GUI agent's Arabic drop into an interface-text part and a mirroring part inside one environment | macOSWorld (2506.04135) | interactive tasks, an Arabic mirrored UI, screenshot agents, binary success | the prior leaves the split open; S2 crosses text and direction in a 2x2 in one app, paired on tasks and seeds, with intervals and a noise floor | medium-high |
| en-RTL cell (Latin text in a mirrored layout) as an experimental factor for agents | Android Force RTL, ICU en-XB (test practice); Román et al. 2015 (humans) | direction without a script change | used here as a measured factor on agents, not as a QA tool or a human study | medium |
| Locale and direction as a grader-preserving UI variant | WebPageBench (2609.35026), BreakingWeb (2609.35814) | paired variants, task and grader fixed | no locale or direction variant in either; method not claimed | high (the method is not novel) |
| UI language as an interface perturbation | RealGUINoise (2609.38184) | language swap on interactive GUI agents | bundled, category-level, no RTL factor, no decomposition | high |
| Aligned cross-lingual GUI evaluation | MPR-GUI (2512.00756) | strict alignment across languages | static, no Arabic, not executable | high |
| Geometric oracle for mirrored layouts | GWALI (ICST 2016), SUDFinder (2607.04120) | layout-relation checks for i18n failures | used as an experimental manipulation check and gate; not a novelty claim | high |
| Noise-floor-normalized cross-lingual agent effects | 2608.11110 | rerun-normalized language effects | tool agents and instruction language there; GUI and interface language here | medium |
| Moderators separating positional, directional and lexical mechanisms | ScreenHaystack (2609.32036), information scent (2603.11759), lexical coupling (2608.21794) | each mechanism exists separately | combined as pre-registered task-level moderators of the two main effects | medium |
| Reasoning-language arm | Skill Issue (2608.25832) | | out of scope for this step | not assessed |

Novelty wording: No direct prior art found through 2026-10-10 under the coverage in the header: 113 counted orx discover queries (keyword with the exact mechanism terms and each closest prior's title phrase, embedding with the mechanism paragraph, openalex), 9 failed orx calls, 11 OpenReview term searches, Semantic Scholar citation lists of the four dossier priors, OpenAlex full-text matches for macOSWorld, arXiv version histories, and the full-text reads listed in `query-log.json`. The queries and every returned id are in `evidence/2026-10-10-s2-arabic-cua-locale/query-log.json`.

## Mechanism and Falsifiable Predictions

**Instrument.** Relay's interface strings move into catalogs; the locale is a
fixture parameter; the four cells differ only in catalog language and
document direction (with logical CSS, a frozen mirror specification,
`dir="auto"` on English content, a pinned Arabic webfont and en-US formats).
An oracle gate (G1-G12) certifies functional equivalence (test-id recipes
and coordinate replays through the agent's executor reach the goal in every
cell), structural identity (role and test-id trees; a11y snapshots
byte-identical between the two directions of the same text), geometric
mirroring (every box at its reflection within 4 px, no clipping or overlap),
render identity of the English build, bidi order, format identity, font and
OCR legibility. Only then is the agent measured.

**Hypothesized causes.** Mirroring could lower success through (i) target
relocation into model-specific low-reliability screen regions (positional:
ScreenHaystack's blind zones, the left-first bias), and (ii) left-to-right
priors about flow and side panels that mislead planning (directional:
macOSWorld's Dock example). Arabic interface text could lower success
through (iii) weaker reading of Arabic glyphs at the agent's input resolution
(KITAB-Bench, GlotOCR) and (iv) lost word overlap between English
instructions and interface labels (lexical coupling; information scent).

**Predictions (Stage 1b, if it runs), each with its falsifier:**

- P3: D lower than 0 (mirroring hurts). Falsified if D is SMALL: its 90%
  interval lies inside (-5, +5) pp.
- P4: T lower than 0. Falsified if T is SMALL.
- P5: the slope of T_t on lexical-overlap count is negative (mechanism iv).
  Falsified if its 95% CR2 interval lies above 0.
- P6: the slope of D_t on the share of reference targets that change screen
  half is negative (mechanism i). Falsified if its 95% CR2 interval lies above
  0; a D that is PRESENT while P6 is falsified points to mechanism (ii).

**Predictions for the first step:** P1, Phase 0 passes every gate item
(falsified if one item fails three full gate runs, K0); P2, English pixel
success on Relay lies in [15%, 85%] with at least 12 informative tasks
(falsified by K2).

**Kill criteria (quantitative; the registration has the full table):** K0,
any gate item fails in any locale or seed: no GPU job; K1, the power gate
returns FAIL_POWER or FAIL_COST: infrastructure exit; K2, pooled English
pilot success outside [0.15, 0.85] or fewer than 12 informative tasks: the
mirror claim is dropped, infrastructure exit; K3, more than 2% of a cell's
Stage 1b episodes fail the per-episode render or tree hash: INCOMPLETE; K4,
D and T both SMALL with neither PRESENT: publish the robustness null and drop
the locale arm from WS3-R; K5, neither PRESENT: no reasoning-language arm;
K6, the Stage 1b cap is reached: analyse complete task blocks if at least 12.

## Cheapest Decisive Pilot

Two steps, each decisive for what follows.

1. **Phase 0 (0 GPU-h).** The CPU build and the gate. It decides whether a
   locale-aligned Relay exists at all (K0). Relay's English oracle already
   passes 18 of 18 tasks on two seeds in about 2.2 CPU-minutes (asset cell),
   so the full gate (216 recipe runs plus 216 replays and the geometric,
   OCR and render checks) is expected to take minutes of CPU per run.
2. **Stage 1a (cap 2.0 GPU-h; central 0.81, high 1.56).** An English-only
   Relay pilot: 18 tasks x 4 seeds x 2 reruns = 144 analysed episodes plus
   54 three-step smoke episodes in the other cells that test only the action
   path. It measures exactly the three inputs the gate lacks (informative
   tasks, Relay's own variance, the price) and the floor kill. Its result
   alone decides whether 15 GPU-h are spent. Design decision 1 lets it be
   admitted under its own registration, below 8 GPU-h.

The pilot cannot confirm an effect, and it is not meant to. The simulation
below says the most likely result is a gate failure, which closes Phase 1 on
Relay cheaply and leaves the pilot's English base rates as Relay's first
measured pixel floor for a local model, an input S3 needs anyway.

## Controls, Baselines, and Ablations

- **Within-environment controls.** en (LTR) is the baseline; ar-LTR changes
  only the text; en-RTL changes only the direction; ar-RTL changes both.
  Every cell of a task uses the same fixture seeds and rerun indices, in one
  serving session, interleaved in a seeded random order inside task blocks
  (S1a saw a +5.5 pp session shift at 9B).
- **Negative controls on CPU, exact.** G4 (the English build after
  extraction is pixel-identical to the build before it, so extraction itself
  is not a treatment) and G2b (a11y snapshots identical across direction, the
  dossier's a11y control done exactly).
- **Manipulation checks.** G5 and G6 (geometry), G7 (OCR legibility against
  a control render), G8 (bidi), G9 (formats), G10 (font), the chrome share,
  and in Stage 1b a per-episode step-0 render and tree hash against Phase 0
  (K3).
- **Held fixed by design.** Instructions (English), content and grader
  strings (English), numerals and formats (en-US), Playwright context locale
  (en-US), model, decoding (greedy, thinking on), step cap (40), action
  policy.
- **Baselines not used.** macOSWorld's numbers are a different platform,
  task set and agent set, so they are context, not a baseline.
- **Deferred ablations.** The reasoning-language arm (d), zh, ja and
  pseudo-locales, an a11y interface arm, and a second model.

## Evaluation, Statistics, and Leakage Checks

- **Primary estimand.** The direction main effect D = mean over tasks of
  D_t = ((y_arR - y_arL) + (y_enR - y_en)) / 2, cell means over n episodes.
  Secondary: T, the interaction I (MDE about twice the main effects', 8.7-10.1
  pp at 18 tasks), the total Delta = T + D, the dossier's two conditional
  contrasts, required-change completion (the share of the grader's named
  change checks passed), process metrics and three moderators.
- **Test and decisions.** Paired t on the K task-level D_t, df K - 1,
  two-sided 0.05 (PRESENT); 90% t interval inside +/-5 pp (SMALL, TOST);
  otherwise INCONCLUSIVE; exact sign-flip enumeration as sensitivity
  (PRESENT_FRAGILE if it disagrees). Tasks are the random factor; K, n and
  the episode count are reported with every interval.
- **Why not more reruns.** With tasks random, power has a ceiling set by K
  and the between-task variance tau2 of the true effect (Westfall et al.
  2014): at K = 18 and tau2 = 0.005 the MDE is 4.95 pp even with infinitely
  many episodes per cell; at tau2 = 0.0025 it is 3.50 pp.
- **Analytic MDE (exact noncentral t; `power-gate.json`).** 2x2 main effect
  at K = 18, tau2 = 0.0025: 5.05-5.61 pp at n = 16, 4.59-5.01 pp at n = 24,
  4.34-4.68 pp at n = 32 (sigma2 0.043-0.0625). Tasks needed for a 5 pp MDE
  at n = 16: 19-23 at tau2 = 0.0025, 30-34 at tau2 = 0.006, 52-56 at
  tau2 = 0.013 (sigma2 0.043-0.0625).
- **The gate on today's transported inputs.** If all 18 tasks were
  informative, at the S1a-realized central price x 1.5 (0.0081 GPU-h per
  episode) the gate passes with sigma2 = 0.043 (n = 20) and fails on cost
  with sigma2 = 0.0625 (n = 24 fits and gives 5.01 pp); at the transported
  high price x 1.2 (0.0126) both fail on cost. If S1a's floor pattern
  transports (59% of 9B base cells at 0), only about 7 tasks are informative
  and the gate fails on tasks.
- **Monte Carlo operating characteristics of the staged design.**
  Simulated with `power-gate.py` (1,500
  replicates per cell over seeds 42, 43, 44; every distribution assumed; the
  pilot, the gate and the main study are all simulated, and the dossier's
  fixed design is run on the same truth draws). Base-rate scenarios: A
  transports S1a's 9B cells (zero-inflated beta-binomial fit: 26% structural
  zeros, Beta(0.15, 0.20)); B is mid-range (Beta(2, 2), 10% zeros); C is near
  the floor (Beta(1, 4), 50% zeros); D is near-deterministic and mostly
  solvable (Beta(0.30, 0.12), 15% zeros), the most favourable case.

  | Scenario | P(gate PASS), expected price / high price | Main reason for FAIL | Mean informative tasks |
  |---|---|---|---:|
  | A, S1a transport | 0.000 / not run | FAIL_TASKS (0.93-0.95) | 6.8-7.1 |
  | B, mid-range | 0.000 / not run | FAIL_COST (0.87-0.91) | 13.6-13.8 |
  | C, near floor | 0.000 / not run | FAIL_FLOOR (0.87-0.89) | 3.7-3.9 |
  | D, near-deterministic | 0.024-0.039 / 0.005-0.012 | FAIL_COST (0.61-0.66), FAIL_TASKS (0.30-0.35) | 12.2-12.4 |

  Conditional on a PASS in scenario D at the expected price (36-58 passing
  replicates per cell, so these rates carry Monte Carlo errors of about
  0.06-0.08): with no true effect the study says SMALL (equivalent within
  +/-5 pp) in 0.92-0.97 of runs, with a false PRESENT (always alongside
  SMALL) in at most 0.04; with a true -5 pp
  direction effect it says PRESENT in 0.42 of runs if the effect is a
  uniform logit shift, 0.19 if half the tasks carry it and 0.02 if a quarter
  do; at -8 pp, 0.70, 0.17 and 0.07. The realized between-task heterogeneity
  of a -5 pp effect is 0.006, 0.012 and 0.017 for those three patterns,
  against the gate's 0.0025 floor; the data-driven term tau2_logit never rose
  above that floor in the simulation (quartiles 0.0025), so it did not bind.
  For comparison, the dossier's fixed design (ar-RTL minus ar-LTR, n = 8,
  all 18 tasks, no gate) on the same draws says PRESENT in 0.02-0.06 of runs
  with no effect, 0.02-0.16 with a -5 pp effect and at most 0.41 with
  -8 pp. Reading: the registered design mostly spends 2.0 GPU-h to learn
  that the 15 GPU-h study should not run; it reaches a PRESENT decision on a
  real -5 pp effect with unconditional probability of about 0.015 even in
  the most favourable scenario. That is the quantitative case for the
  infrastructure exit, and for routes R1 and R2 (a 5 pp MDE needs about
  19-23 informative tasks at tau2 0.0025, 30-34 at 0.006 and 52-56 at 0.013,
  with n = 16).
- **Leakage and selection.** Pilot seeds (101-105) are disjoint from Stage 1b
  seeds (201 onward); tasks are selected on pilot data only and English is
  re-measured in Stage 1b, so selection does not bias the English baseline
  (the pilot-versus-Stage-1b English difference on the selected tasks is
  reported). Smoke episodes are capped at 3 steps and never analysed.
  Moderator codings are frozen before any GPU job.
- **Missing data and infrastructure.** One re-queue per failed episode; a
  task enters only if each of its four cells has at least n - 1 valid
  episodes; more than 5% missing pilot episodes makes the pilot INCOMPLETE.
- **Statistical reporting protocol.** K-Dense `statistical-analysis` and the
  ARS statistical reporting standards: effect sizes with intervals, paired
  and clustered errors, assumption checks (normality of D_t checked by the
  sign-flip sensitivity), and no HARKing (moderators registered).

## Compute and Reproducibility

Engine image: vLLM v0.31.0 (commit `db9527a4`) on
`docker.io/vllm/vllm-openai@sha256:b18abb2df97b8f798e81862bd93f872ea18613372e2c3adc0cc2ac21e66ac12f`
with the cu129 overlay rebuilt per source commit by
`scripts/build_vllm_overlay_on_h100.sh` and its provenance receipt, as S1a
used. Environment image (to be built, E3) from Relay's pinned base
`node:24.13.0-bookworm-slim@sha256:4660b1ca8b28d6d1906fd644abe34b2ed81d15434d26d845ef0aced307cf4b6f`
plus Playwright's Chromium, the pinned Noto Sans Arabic and Relay at the
Phase 0 commit; one `--network none` container per episode slot (app server,
browser, driver), joined to the engine only through
`harness/q2_stage1/bridge.py`'s Unix socket (D13). Model: Qwen3.5-9B
revision `c202236235762e1c871ad0ccb60c8ee5ba337b9a` (receipt `0a9e052d`),
weights already on the host.

Launch path (none of these manifests exists yet; dry run, then test-only,
then submit, one GPU per job):

```bash
uv run --locked python scripts/submit_docker_research_job.py infra/slurm/host-single-node/s2-arabic-cua-locale-v1-stage1a.yaml --dry-run
uv run --locked python scripts/submit_docker_research_job.py infra/slurm/host-single-node/s2-arabic-cua-locale-v1-stage1a.yaml --test-only
uv run --locked python scripts/submit_docker_research_job.py infra/slurm/host-single-node/s2-arabic-cua-locale-v1-stage1a.yaml
```

The submitter wraps `sbatch infra/slurm/host-single-node/docker-research.sbatch`;
the environment containers run as a CPU-only Slurm job beside the GPU engine
job, as S1a's VM lanes did (D12). Every executable pilot also runs as an orx
node through `uv run --locked python scripts/orx_run.py` over a committed
`experiments/orx/node.yaml` (`kind: cpu-doctor` for the Phase 0 gate doctor
`scripts/run_s2_locale_gate_doctor.py`, to be written; `kind:
slurm-manifest` for Stage 1a and 1b).

Machine fields: seeds: [42, 43, 44]; gpu_hours: 17 (registered caps: Stage
1a 2.0, Stage 1b at most 15.0 by formula, Phase 0 0; separate from the
gauntlet's 0.3 GPU-h reviewer budget). Fixture seeds: gates 42-44, pilot
101-105, Stage 1b 201 onward.

Cost model (`compute/power-gate.json` `C_cost_model`): S1a-realized 9B
price 0.002701 GPU-h per episode over 12.04 mean steps = 0.000224 GPU-h per
step (environment-bound, conservative for a browser app); GPU-bound low
price 0.000134 per step from serving probe v2 (2.55 requests/s at 300 output
tokens, scaled to 370); high = central x 1.3 for longer histories; mean
steps 24 (central, low) and 36 (high) under a 40-step cap. Per episode: low
0.0032, central 0.0054, high 0.0105 GPU-h; cap price 1.2 x high = 0.0126.
Stage 1a: low 0.49, central 0.81, high 1.56, cap 1.97 rounded to 2.0. Stage 1b
examples: K = 18, n = 16 (1,152 episodes) central 6.2, high 12.1, cap at the
high price 14.6; the registered cap uses 1.5 x the pilot-measured English
price, at most 15.0.

Checkpoints and resume: each episode is the unit of work; completed
episodes (trajectory, actions with target boxes, grader checks, step-0
hashes, tokens and timings) are appended to the persistent run directory as
they finish; a fresh job skips completed (task, seed, rerun, locale) keys and
continues the seeded order; E4 includes a kill-and-resume test that must
reproduce the set of completed keys and their step-0 hashes. Preemption: a
preempted job is resubmitted with the same manifest and its time counts
against the cap (D22). Artifacts: per-episode records, the gate record,
moderator codings and the decision record in the public repository;
screenshots and trajectories on the host and in the private archive.

## Safety, Data Rights, and Monitorability

- **Safety.** The agent acts only inside a synthetic, self-hosted chat app in
  a `--network none` container whose browser may fetch only the app's origin;
  it generates no code, so the untrusted-code rules (D3, D7) are not
  triggered. No real user data, no outward messages. Relay's own
  `.env.local` is never read and its `.runtime` directory never copied.
- **Monitorability.** Every action, target box, observation hash, token count
  and grader check is logged per episode; trajectories are replayable from
  seeds; thinking traces are kept.
- **Data rights.** Relay: MIT (Kevin's), fixtures and portraits synthetic.
  Lato: OFL. Camber: proprietary to Relay's live site, never copied.
  Noto Sans Arabic: OFL 1.1 (public download, D1). i18next and
  react-i18next: MIT. Tesseract and tessdata: Apache-2.0. Playwright:
  Apache-2.0. Qwen3.5-9B: Apache-2.0. The Arabic catalog is authored
  in-project; the native-speaker reviewer is credited with consent.
- **Outward actions.** Pushing Relay's Phase 0 branch to its public remote
  and engaging a native-speaker reviewer are Kevin's calls (D2).
- **Public-repo hygiene.** No host address, credentials or private data in
  any artefact; the scout scripts copied into the bundle have their local
  test tokens redacted (`compute/cells/ORIGINAL_SHA256.txt` records the
  originals' hashes).

## Negative-Result Value

| Outcome | What it says | What it closes |
|---|---|---|
| K0 (Phase 0 fails three runs on one item) | Relay cannot be mirrored to the gate's standard without redesign | S2 on Relay; the failure record is itself a useful i18n case |
| K2 (floor) | Qwen3.5-9B's pixel success on Relay is outside 15-85%, or fewer than 12 tasks are informative | Phase 1 on Relay for this model; S3's pre-RL cells need different tasks or a different model, measured, not assumed |
| K1 (power or cost) | Relay's 18 tasks cannot detect a 5 pp direction effect at the measured variance and price | Phase 1 on Relay; a measured reason the dossier's power gate fails; routes R1 and R2 need their own proposals |
| D SMALL (TOST) | Chrome mirroring changes success by less than 5 pp for this model and app | The mirror half of the open split for chrome localization at this scale; a publishable robustness null |
| D PRESENT, P6 holds | A mirror cost that tracks target relocation | Points mitigation at grounding (position augmentation), not at language |
| D PRESENT, P6 falsified | A mirror cost not explained by relocation | Points at directional priors in planning |
| T PRESENT, P5 holds | An Arabic-interface cost that tracks lost instruction-label overlap | Points at lexical matching, not glyph reading |
| INCONCLUSIVE | Nothing beyond the intervals | Sizes a successor through route R1 or R2 |

By the owner's prior the most likely outcome of this first step is the
infrastructure exit (K1 or K2): a locale-aligned, gate-certified Relay for
S3 and a measured Relay pixel floor, at 0 GPU-h for Phase 0 and at most
2.0 GPU-h for the pilot.

## Preflight Doctors

| Doctor | Status | Evidence | Remediation |
|---|---|---|---|
| Source | PASS | orx alphaXiv and OpenAlex reachable from the Mac; 113 counted discover queries with returned ids and raw-output SHA-256, 9 failed calls and 65 uncounted searches and fetches logged; cutoff 2026-10-10; degraded coverage recorded (Semantic Scholar keyword search, OpenAlex daily budget, OpenReview full texts, ACL Anthology index, social media, patents) (`doctors/source.json`) | Rerun Semantic Scholar keyword searches and an ACL Anthology venue search when the rate limits reset |
| Citation | PASS | Claim registry C01-C39 with locators, dates and read status; every primary URL snapshotted with its HTTP status and hash; abstract-only and first-party claims labelled; OpenReview rows UNVERIFIABLE_ACCESS (their HTTP 200 pages are a browser challenge) (`doctors/citation.json`) | Read PuMVR, GAIA-v2-LILT and the lexical-coupling paper in full before any delta row rests on them |
| Novelty | FAIL | No direct prior under the recorded coverage, but the blind closest-prior critic and the novelty refuter have not run; the ACL Anthology was searched only through OpenAlex and web search (`doctors/novelty.json`) | Run the blind critic on `blind/` and the novelty refuter (37 queries remain, above the reserve of 30) |
| Design | FAIL | Intervention, controls, falsifiers, decision rules and the gate are specified and simulated, but every base-rate distribution is assumed; tau2 cannot be measured before treatment; the simulation gives a gate pass probability of at most a few percent in every assumed scenario and low conditional power for concentrated effects; no Phase 0 code exists (`doctors/design.json`) | Build Phase 0 and run its gate as a `cpu-doctor` node; run the pilot to replace the transport |
| Compute | FAIL | No local-engine transport, agent adapter, environment image, manifest, container smoke or Slurm dry run; no executable pilot (`doctors/compute.json`, `compute/attestations-not-run.md`) | E1-E6 |
| Safety | PASS | Synthetic app in a network-less container, no code generation, permissive licences, proprietary font excluded, outward actions reserved, host rule respected (`doctors/safety.json`) | none |

Protocols followed: Citation, the ARS claim-verification protocol (claim
registry, locators, verdicts, UNVERIFIABLE_ACCESS); Design, the vendored
K-Dense `experimental-design` and `statistical-power` skills (design before
data, a 2x2 factorial with blocking by task and seed, power by exact
computation and simulation); Evaluation, K-Dense `statistical-analysis`;
Novelty, K-Dense `literature-review` (PRISMA counts in the header). The
integrity gate's seven failure modes are answered in the registration.

## Independent Adversarial Reviews

Reviewer A: FAIL | provider=not-run | model=not-run | run_id=not-run | artifact=none (wave-1 reviewers run after the blind critic and the refute-first triad)

Reviewer B: FAIL | provider=not-run | model=not-run | run_id=not-run | artifact=none (the open-weight reviewer's lane job may run only while no S1a VM or GPU job is running; the queue was empty at 21:42:52 UTC)

No review is signed: no trusted Ed25519 store exists (D24).

## Scorecard

| Dimension | Reviewer A | Reviewer B | Defect/evidence |
|---|---:|---:|---|
| Question and strategic fit | 0 | 0 | not yet reviewed; S3 prerequisite, open split in the closest prior |
| Primary-source evidence | 0 | 0 | not yet reviewed; claim registry C01-C39 in doctors/citation.json |
| Defensible novelty delta | 0 | 0 | not yet reviewed; blind discrimination not run |
| Mechanism and falsifiability | 0 | 0 | not yet reviewed; P1-P6 and K0-K6 with registered falsifiers |
| Controls and causal identification | 0 | 0 | not yet reviewed; 2x2 with en-RTL, exact CPU controls, moderators |
| Evaluation and statistics | 0 | 0 | not yet reviewed; simulated gate pass probability is low |
| Feasibility and information per GPU-hour | 0 | 0 | not yet reviewed; Phase 0 CPU, pilot cap 2.0 GPU-h, no executable pilot |
| Reproducibility and artifact contract | 0 | 0 | not yet reviewed; no harness, image or manifest yet |
| Safety, data rights, and monitorability | 0 | 0 | not yet reviewed; synthetic app, permissive licences |
| Independent adversarial review quality | 0 | 0 | not yet reviewed; no signed reviews possible (D24) |
| **Total** | **0** | **0** | Lower total is authoritative |

## Iteration Log

| Wave | Score | Highest-impact defect | Change | Result |
|---:|---:|---|---|---|
| dossier (2026-10-06) | not scored | String swap cannot hold layout fixed; Relay not internationalized; 18 tasks underpowered; a11y control identical by construction | Corrected question and kill lines written | Recorded in the dossier, section 5 |
| new gauntlet, synthesis (2026-10-10) | not scored | The dossier's Phase 1 cannot reach its own 5 pp line, and its oracle gate passes a half-mirrored layout | 2x2 with en-RTL and main effects; a11y arm replaced by exact CPU checks; geometric, render, bidi, OCR and action-path gates; Stage 1a pilot and a registered gate on Relay-measured inputs; simulation of the staged design | Awaiting blind critic, refuters and reviewers |

## Deterministic Doctor Output

Verbatim output of `uv run python scripts/research_direction_doctor.py
program/proposals/2026-10-10-s2-arabic-cua-locale.md` (exit 1) on the
committed bundle, also stored as
`evidence/2026-10-10-s2-arabic-cua-locale/doctors/research-direction-doctor-output.json`.
Three readings the doctor does not make for itself: "all declared budgets
must be positive" comes from parsing the declared `gpu_hours=0.3` as an
integer (the budget is honest and is not rounded up to pass); the doctor
applies no 79 cap because its executable-pilot check is textual, while by
the gauntlet rule's cap table this proposal is capped at 79 (no executable
pilot) and 89 (no independent provider-distinct review), and cannot reach 100
without D24's trust store; and it counts the two OpenReview snapshots as
resolved because those pages return HTTP 200, although their bodies are a
browser challenge.

```json
{
  "acceptedScore": 0,
  "doctorStatus": {
    "Citation": "PASS",
    "Compute": "FAIL",
    "Design": "FAIL",
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
    "Design doctor lacks PASS plus concrete evidence",
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
    "doctor artifact 3 did not pass",
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
    "allUrls": 41,
    "recognizedPrimaryUrls": 29
  },
  "status": "FAIL"
}
```
