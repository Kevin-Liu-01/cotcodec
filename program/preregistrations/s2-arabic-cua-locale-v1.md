# S2 v1: Arabic interface text versus mirrored layout on a locale-parameterized Relay, Phase 0 gate and Phase 1 design (s2-arabic-cua-locale-v1)

Status: DRAFT. Not frozen, not admitted, no ledger row. Written on 2026-10-10
by the single synthesis owner of the S2 research gauntlet (D67) on branch
`gauntlet/s2-locale`. It registers S2's first step: Phase 0 (CPU only: the
locale fixture and its oracle gate) and the design of Phase 1 (an English
Relay pilot, a power gate, and a conditional main study). The sum of the
registered caps is 17.0 GPU-h, over the 8 GPU-h line of D22, so admission of
the GPU stages is Kevin's ruling under D24 whatever the gauntlet scores.
Design decision 1 offers a split that would let the 2.0 GPU-h pilot be
admitted under its own registration. No host job of any kind runs while a Q2
S1a VM or GPU job (`s1a-a1-*`, `q2s1a-*`) is running or pending. The proposal
that argues and attacks this design is
`program/proposals/2026-10-10-s2-arabic-cua-locale.md`; its evidence bundle
is `program/proposals/evidence/2026-10-10-s2-arabic-cua-locale/`. Every
number labelled "simulated" comes from
`program/proposals/evidence/2026-10-10-s2-arabic-cua-locale/compute/power-gate.py`
(seeds 42, 43, 44) and rests on assumed distributions; nothing in it is a
Relay measurement.

## Relation to the dossier and to D67

Source: dossier entry `S2-aligned-locale-language`
(`program/evidence/2026-10-06/question-dossier.md`, section 5). Each dossier
step and kill line is kept, made quantitative, or replaced, as follows.

| Dossier text | Here | Why |
|---|---|---|
| Extract chrome strings into i18next catalogs for en, ar-LTR, ar-RTL; locale as a fixture parameter; fixture content and grader strings stay English | Kept, plus a fourth cell, en-RTL (English catalog, `dir=rtl`, logical CSS) | Completes a 2x2 of text by direction, so the total drop splits into two main effects that sum to it exactly, at two thirds of the conditional contrast's sampling variance for the same episodes (section "Estimands") |
| Oracle gate: reference solutions 18/18 on at least 3 seeds, identical DOM role/ID tree hash, graders unchanged | Kept as G1, G2, G3, plus nine more gates (G2b, G4-G12) | Under a naive `dir=rtl`, 37 of 88 interactive elements on one Relay screen were not at their mirrored positions while the DOM tree was unchanged (kill-shot cell probe), so the dossier's gate passes a half-mirrored layout |
| Record the chrome-vs-content ratio; native-speaker check | Kept; the ratio method is registered; the native-speaker check is a precondition of the Stage 1b freeze | Measured share of chrome characters on first screens: 18% (kill-shot cell, one screen) to 22-25% (asset cell, 18 tasks, pooled 24.3%) |
| Power gate from "the WS1 Relay noise-floor run" | Replaced: a Stage 1a English Relay pilot measures the inputs; the gate rule is fixed here | No Relay noise-floor run exists; S1a's floor is from OSWorld VM tasks |
| Phase 1: 18 tasks x 4 seeds x {en, ar-LTR, ar-RTL} x {pixels, a11y} x 2 reruns = 864 episodes | Replaced: pixels only, 2x2, n episodes per task-cell set by the gate, on the pilot's informative tasks | The a11y mirror contrast is identical by construction (it becomes CPU gate G2b); the dossier design's paired MDE is 8.1-9.4 pp at the gate's heterogeneity (analytic, below) |
| Glyph effect = ar-LTR minus en; mirror effect = ar-RTL minus ar-LTR; task-clustered paired bootstrap | Primary is the direction main effect D; the dossier's two contrasts are secondaries under the names "Arabic-text contrast" and "conditional mirror contrast"; inference is a paired t on task means with an exact sign-flip sensitivity | ar-LTR minus en changes language, script and instruction-label word overlap together, so "glyph" overclaims; a percentile cluster bootstrap over-rejects at about 18 clusters |
| Kill: oracle gate fails -> fix alignment first | K0 | |
| Kill: paired MDE above ~5 pp with no route to more templates -> publish infrastructure and stop | K1 with the gate rule below | |
| Kill: English pixel success outside 15-85% -> drop the mirror claim | K2, plus at least 12 informative tasks | |
| Kill: nonzero a11y mirror contrast beyond noise -> alignment broken | K3 (exact CPU checks G2/G2b, and per-episode render and tree hashes in Stage 1b) | |
| Kill: both effects under the MDE -> publish the robustness null, drop the locale arm from WS3-R | K4 as an equivalence (TOST) rule at +/-5 pp | A non-significant result is not evidence of absence |
| Reasoning-language arm only if Phase 1 survives; zh/ja/pseudo-locale deferred to 100+ templates | K5 | |

## Question

On Relay (`~/repos/Relay`, a synthetic Slack-like workplace app with
state graders, HEAD `e6c815e`) after real i18n extraction, with page
structure, element test ids, task steps and state graders identical in every
locale, and English task instructions throughout: for Qwen3.5-9B acting on
screenshots, how large are (D) the main effect of right-to-left mirroring of
the interface and (T) the main effect of Arabic interface text, in a 2x2
locale design {English, Arabic interface text} x {left-to-right,
right-to-left}, estimated with tasks as the random factor against Relay's own
seed-and-rerun noise? The main study runs only if the registered power gate
passes on Relay-measured inputs.

Claim scope: `portability-protocol`, a measurement on one frozen model and
one app. It licenses no claim about other models, other apps, full Arabic
deployments (content and grader strings stay English), or instruction or
reasoning language.

## Identity

- Experiment id: `s2-arabic-cua-locale-v1`.
- cotcodec code of record: the freeze commit on `gauntlet/s2-locale` (or its
  successor branch), recorded at freeze.
- Relay: base `e6c815e634f6` (clean, MIT). Phase 0 work is a local branch of
  Relay; its commit SHA and a source-archive SHA-256 are pinned at freeze.
  Pushing that branch to the public Relay remote is an outward action and
  needs Kevin's OK (D2); the registration does not depend on it.
- Model: Qwen3.5-9B, revision `c202236235762e1c871ad0ccb60c8ee5ba337b9a`
  (`models/registry.yaml`, receipt `0a9e052d`, Apache-2.0), the weights S1a
  used.
- Engine: vLLM v0.31.0 (commit `db9527a4`), base
  `docker.io/vllm/vllm-openai@sha256:b18abb2df97b8f798e81862bd93f872ea18613372e2c3adc0cc2ac21e66ac12f`,
  cu129 overlay rebuilt per source commit by
  `scripts/build_vllm_overlay_on_h100.sh` with its provenance receipt, as in
  S1a.
- Environment image: to be built (E3) from
  `node:24.13.0-bookworm-slim@sha256:4660b1ca8b28d6d1906fd644abe34b2ed81d15434d26d845ef0aced307cf4b6f`
  (the base Relay's Dockerfile already pins), with Playwright's Chromium,
  the pinned Arabic webfont and Relay at the Phase 0 commit; its digest is
  recorded before the Stage 1a freeze.

## Stages

| Stage | What | GPU | Admission |
|---|---|---|---|
| Phase 0 | Locale fixture (P0.1-P0.10) and oracle gate G1-G12 | 0 (development Mac, CPU) | none needed; runs after this draft is accepted |
| E1-E6 | Engineering prerequisites for any GPU stage | 0 (Mac and host CPU jobs) | after Phase 0 passes |
| Stage 1a | English Relay pilot, 144 analysed episodes plus 54 three-step smoke episodes | cap 2.0 GPU-h | D24 ruling (or its own registration under design decision 1) |
| Gate | Registered power gate (CPU, deterministic) | 0 | automatic |
| Stage 1b | 2x2 main study on the informative tasks | cap by formula, at most 15.0 GPU-h | D24 ruling; only after the gate passes and the native-speaker check |

## Phase 0: the locale fixture (CPU, no GPU)

- **P0.1 Extraction.** Every user-visible chrome string in `src/main.jsx`
  moves to i18next catalogs (`src/locales/en/chrome.json`,
  `src/locales/ar/chrome.json`) used through react-i18next (MIT). The asset
  cell's AST parse counted 63 unique JSX text strings, 37 literal and 22
  expression `aria-label`/`title`/`placeholder` attributes, about 43
  user-facing string literals and about 20 user-visible templates (for example
  "Reply to ${}'s message"): about 150-200 keys. Fixture-derived values
  (names, channel names, message bodies, topics) are not chrome and stay
  English.
- **P0.2 Locale parameter.** Session creation takes `locale` in
  {`en`, `ar-LTR`, `en-RTL`, `ar-RTL`} beside `taskId` and `seed`; the server
  stores it on the session; the client sets `<html lang>` (`en` or `ar`) and
  `<html dir>` before first paint. The runner's Playwright context keeps
  `locale: 'en-US'` and `timezoneId: 'UTC'` in every cell, so `Intl` defaults
  do not vary with the cell. The waits on the English accessible name
  "Search Northstar" (`runner/environment.mjs:79` and `runner/interfaces.mjs:304`) move
  to a test id.
- **P0.3 Direction.** `dir="rtl"` on `<html>` for en-RTL and ar-RTL. The
  physical-direction declarations in `src/style.css` (48 lines with
  `margin-left`, `padding-left/right`, `left:`, `right:`, `text-align: left`,
  `border-left/right` and four corner radii; 0 logical properties; the cells
  counted 44 and 45 without the radii) become logical properties
  (`margin-inline-start`, `inset-inline-*`, `text-align: start`,
  `border-inline-*`, `border-start-start-radius` and so on). A mirror
  specification, following the Firefox RTL guidelines, lists every icon and
  component as mirrored (directional arrows, reply and back glyphs, sidebar
  and thread-panel sides, toolbars) or not mirrored (emoji, checkmarks,
  logos, avatars, media controls); it is frozen with Phase 0.
- **P0.4 Bidi and formats.** `dir="auto"` on message bodies, channel names,
  topics, the composer and the search input, so English content keeps
  logical order inside RTL containers (without it, "9:33 AM" rendered as
  "AM 9:33" and trailing periods moved left in the kill-shot cell's probe).
  The three `toLocaleTimeString`/`toLocaleDateString('en-US')` calls
  (`src/main.jsx:630, 716, 1178`) stay `en-US` in every cell: Latin digits
  and AM/PM are held fixed, not part of the treatment (Node 24's ICU gives
  Arabic-Indic digits for `ar-EG` and `ar-SA` and Latin for `ar`; a numeral
  factor is not wanted).
- **P0.5 Font.** Noto Sans Arabic (SIL OFL 1.1; release and SHA-256 pinned)
  is bundled and served from the app origin (the runner blocks every other
  origin), after Lato in the font stack so Latin glyphs keep rendering in
  Lato. Relay's bundled fonts have no Arabic coverage (cross-domain cell:
  Camber 0 of 68 Arabic code points checked, Lato 1 of 2,164) and the host
  lists no Arabic font. Camber is proprietary to Relay's live site and is
  never copied.
- **P0.6 Arabic catalog.** Drafted in-project in Modern Standard Arabic, UI
  register, by a Claude agent (disclosed); a machine back-translation pass
  flags meaning drift; then a native-speaker review (Kevin arranges; no such
  resource exists in the repository) gives each key accept, minor or major.
  Every major is fixed before the Stage 1b freeze; counts are reported.
- **P0.7 Test ids.** Every element any reference recipe touches gets a
  stable `data-testid` independent of the catalog. Recipes locate elements by
  test id and role, never by translated name. The current recipes locate by
  English accessible name (86 `getByRole` calls in
  `tests/browser/deep-workflows.spec.mjs`), which would make a catalog-driven
  oracle circular; the English-name recipes are kept as a cross-check in `en`.
- **P0.8 Seeds.** Gate fixture seeds 42, 43 and 44 (44 is new; 97 stays the
  grader-challenge seed).
- **P0.9 Instrumentation.** The executor logs, for every agent action, the
  element under the action point (test id, role, bounding box), the
  coordinate after the model-to-viewport mapping and the locale. It does not
  change any observation.
- **P0.10 Moderator coding, frozen before any GPU job.** Per task, by
  registered scripts: (a) lexical overlap, the number of distinct English
  catalog labels whose lowercased tokens appear in the instruction
  ("thread", "pin", "topic", "Later", "save", "reply", "DM" and so on);
  (b) direction-sensitive steps, the number of reference-recipe steps whose
  target the mirror specification marks as direction-bearing (side panels,
  horizontal toolbars, back/forward, list order); (c) the reference targets'
  x-positions in LTR and RTL and the share whose centre moves between screen
  halves.

## Phase 0: the oracle gate

Every gate runs on all 18 tasks, seeds 42, 43 and 44, and the four locales,
at a 1440x900 viewport with animations disabled. "Reference states" are the
initial state and the state after each step of the test-id-keyed reference
recipe. The gate passes only if every item passes. Thresholds are fixed here;
failures are fixed in Relay's code, never by changing a threshold.

| Gate | Check | Pass line |
|---|---|---|
| G1 functional | Test-id-keyed scripted reference solutions reach grader success; Relay's node suites (91 tests: grader positives, negatives, unrelated mutations, API references, adversarial challenges) pass unchanged | 216 of 216 recipe runs; 91 of 91 tests |
| G2 structure | Hash of the role and test-id tree in DOM order (names excluded) at every reference state | identical across the four locales; 0 mismatches |
| G2b a11y identity | Full `ariaSnapshot()` text at every reference state, ar-LTR against ar-RTL and en against en-RTL | byte-identical; 0 mismatches (this replaces the dossier's a11y GPU arm) |
| G3 grader identity | SHA-256 of `server/*.mjs` and the fixture modules against `e6c815e`; grader verdict and check list at every reference end state | files identical; verdicts identical across locales |
| G4 render A/A | en after extraction against the pre-extraction build `e6c815e`, PNG at every reference state | 0 differing pixels, or no more than the same-build repeat difference measured first on 20 states (recorded) |
| G5 mirror fidelity | For every visible interactive element and text-run box, RTL cell against its LTR counterpart (en-RTL vs en; ar-RTL vs ar-LTR): x_rtl against W - x_ltr - w and y | at least 98% of boxes within 4 px in x and y at every reference state, each exception named in the mirror specification; 0 clipped interactive elements; 0 new overlaps between interactive elements or with text runs |
| G6 text-swap layout | ar-LTR against en and ar-RTL against en-RTL: container boxes; text containers' `scrollWidth` against `clientWidth`; overlaps | container boxes within 4 px; 0 overflowing chrome text containers; 0 new overlaps |
| G7 OCR round trip | Tesseract (pinned version, Arabic traineddata) on crops of every Arabic chrome string as rendered in the app, against the same strings rendered in a plain page with the same font (control) | per-string CER(app) - CER(control) at most 0.05 for at least 95% of strings; no string with zero Arabic characters recognised; rendered Arabic glyph x-height at the model's input resolution recorded |
| G8 bidi integrity | Character order (per-character client rects) of every English content text node in RTL cells; trailing punctuation position | logical left-to-right order and end punctuation at the logical end for every node; 0 violations |
| G9 formats | Every rendered number, time and date string | identical across the four locales |
| G10 font | Arabic glyphs render with the pinned webfont (`document.fonts`, computed family); content regions (message pane, outside chrome masks) of ar-LTR against en | pinned font active; content-region pixels identical |
| G11 extraction completeness | AST scan for user-visible literals outside the catalogs; missing keys; Latin-script words left in rendered Arabic chrome (registered allow-list: "Northstar", channel and user names) | 0; 0; 0 |
| G12 pixel-replay action path | Each reference trajectory converted to the agent's action language (click at element centres, type, key, scroll) and replayed through the same executor and coordinate mapping (smart_resize and back) the agent uses | 216 of 216 grader successes |

Also measured and reported, not gated: the chrome share of visible
characters per screen and locale (text nodes classified as chrome by catalog
membership), and the Phase 0 CPU time.

## Engineering prerequisites (before the Stage 1a freeze)

- **E1 transport.** A local OpenAI-compatible client in Relay's runner that
  reaches the served model through `harness/q2_stage1/bridge.py`'s Unix socket
  (D13: no Docker network). Relay's hosted-router transport accepts only its
  one hosted endpoint (`runner/router.mjs:131-140`) and is left unchanged.
- **E2 agent.** S1a's H-OSW-fixed qwen35vl prompt, history and smart_resize
  (`harness/q2_stage1/agents.py`), mapped to Relay's 1440x900 viewport and
  action set (click, move, type, key, scroll, wait, finish). An action Relay
  cannot execute (double click, right click, drag) is a no-op with an error
  observation and is counted (invalid-action rate).
- **E3 image.** One `--network none` container per episode slot holding the
  Relay app server, Chromium and the driver; image digest recorded; built
  from public downloads under D1.
- **E4 container smoke.** In the container on a host CPU job: G12 for 18
  tasks x 4 locales at seed 42 (72 of 72), and a kill-and-resume test of the
  episode queue.
- **E5 manifests.** Stage 1a Slurm manifest; `--dry-run` and `--test-only`
  through `scripts/submit_docker_research_job.py` pass.
- **E6 ledger.** The Phase 0 gate as an orx `kind: cpu-doctor` node running a
  registered `scripts/run_s2_locale_gate_doctor.py`; Stage 1a and 1b as
  `kind: slurm-manifest` nodes, run only through the submitter.

## Stage 1a: English Relay pilot

- Model and decoding: Qwen3.5-9B, thinking on, 2,048 output tokens per step,
  greedy (temperature 0), screenshot only, English instructions, step cap 40
  (Relay's own `maxSteps` of 60 and 80 are not used), one H100, 16 concurrent
  environment slots.
- Analysed episodes: locale `en`, 18 tasks x fixture seeds {101, 102, 103,
  104} x 2 reruns = 144.
- Smoke episodes (never analysed): 18 tasks x {ar-LTR, en-RTL, ar-RTL} x
  seed 105 x 1 rerun = 54, capped at 3 steps. The analysis reads only their
  infrastructure fields (observation delivered, actions executed, step-0
  render and tree hashes equal to Phase 0's); their success field is not
  written to any analysis output.
- Measured: per-task English successes k_t of 8; pooled success pi_hat; the
  informative set {t : k_t >= 2}, of size K_inf; within-(task, seed) rerun
  discordance D_w,Relay; between-seed variance; the unbiased within-task
  variance s_t = k_t (8 - k_t) / 56 and its mean sigma2_hat over informative
  tasks with SE = sd(s_t) / sqrt(K_inf); whole-job GPU-h per analysed
  episode p_hat (from `scontrol`, startup included); steps; invalid-action
  and truncation rates; infrastructure losses.
- Cap: 2.0 GPU-h = 1.2 x (144 x 36 steps x 0.000292 GPU-h/step + 162 smoke
  steps x 0.000292) + 0.10 startup, rounded up (1.97). The per-step price is
  S1a's realized 9B price (0.002701 GPU-h per episode over 12.04 mean steps =
  0.000224) times 1.3 for longer histories.

## Power gate (registered rule; CPU; deterministic)

1. FAIL_FLOOR if pi_hat is outside [0.15, 0.85].
2. FAIL_TASKS if K_inf < 12.
3. sigma2_U = sigma2_hat + 0.8416 x SE (one-sided 80% upper bound).
   Cap price c = 1.5 x p_hat (1.2 margin x 1.25 allowance for longer
   non-English episodes).
4. tau2_gate = max(0.0025, tau2_logit), where tau2_logit is the
   between-task variance (ddof 1) of the probability change when one uniform
   logit shift gives a mean change of -5 pp on the informative tasks'
   Jeffreys-smoothed pilot base rates (k_t + 0.5) / 9. The 0.0025 floor is a
   5 pp mean effect carried entirely by half the tasks (0.5 x 0.5 x 0.10^2).
5. For n in {8, 12, 16, 20, 24, 28, 32, 36, 40, 48, 56, 64}, in order: if
   4 x K_inf x n x c + 0.10 > 15.0, stop with FAIL_COST; if
   MDE_80(K_inf, v = tau2_gate + sigma2_U / n) <= 5.0 pp, PASS with this n.
   MDE_80 is the smallest mean effect with 80% power for a two-sided paired t
   at alpha 0.05 with K_inf - 1 df (exact noncentral t). If the grid is
   exhausted, FAIL_POWER.
6. Allocation of n: if D_w,Relay <= 0.02, reruns = 1 and fixture seeds =
   n; otherwise reruns = 2 and seeds = n / 2. Stage 1b seeds are 201, 202,
   and so on (disjoint from the pilot's).

What the gate does not protect against (disclosed): tau2 cannot be measured
before treatment. On the probability scale, logit-shift effect models give
more heterogeneity than the 0.0025 floor: the simulated realized tau2 of a
-5 pp effect is about 0.006 for a uniform logit shift, 0.012 when half the
tasks carry it and 0.017 when a quarter do (`power-gate.json`,
`mean_realized_tau2_given_any_pass`), while tau2_logit computed from
smoothed pilot rates stayed at or below 0.0025 in every simulated cell
(quartiles 0.0025), so in simulation the data-driven term never bound. At K = 18 no design reaches
5 pp once tau2 exceeds about 0.005 (the infinite-n floor is 4.95 pp at
0.005). A PASS therefore licenses Stage 1b for a diffuse effect; for an
effect concentrated in a few tasks the study is underpowered by
construction, and the simulation's conditional power given PASS is reported
beside the gate verdict.

Gate on today's transported inputs (analytic, `power-gate.json`
`gate_on_transported_s1a_inputs`), taking all 18 tasks as informative:

| Price per episode | sigma2 0.043 (S1a 9B D_w / 2) | sigma2 0.0625 (S1a pooled) |
|---|---|---|
| S1a-realized central x 1.5 = 0.0081 GPU-h | PASS at n = 20 (n = 24 is the largest under 15.0 GPU-h, MDE 4.59 pp) | FAIL_COST: n = 24 fits and gives 5.01 pp |
| transported high x 1.2 = 0.0126 GPU-h | FAIL_COST: n = 16 fits and gives 5.05 pp | FAIL_COST: 5.61 pp at n = 16 |

If S1a's floor pattern transports (59% of 9B base cells at 0, 23% at 1),
about 7 of 18 tasks are informative and the gate stops at FAIL_TASKS. The
verdict therefore rests on three Relay quantities only the pilot can measure:
K_inf, sigma2 and p_hat.

## Stage 1b: the main study (only after PASS, the native-speaker check and a D24 ruling)

- Tasks: the K_inf informative tasks. Cells: en, ar-LTR, en-RTL, ar-RTL.
  Every cell of a task uses the same fixture seeds and rerun indices.
- Order: one serving session; task blocks in a seeded random order (PCG64
  seed 42); within a block, the 4n episodes in a seeded random interleave. A
  cap stop therefore leaves complete task blocks. S1a's 9B session shift
  (+5.5 pp, p 0.016) is why all cells of a task share a session.
- Model, engine, decoding, step cap and action policy as in Stage 1a.
- Cap: 4 x K_inf x n x 1.5 x p_hat + 0.10, at most 15.0 GPU-h.

## Estimands

Cell means per task t over its n episodes: y_t,en, y_t,arL, y_t,enR, y_t,arR.

- **Primary, D (direction main effect):** D = mean_t D_t with
  D_t = ((y_t,arR - y_t,arL) + (y_t,enR - y_t,en)) / 2.
- **Secondary, T (Arabic-text main effect):** T = mean_t
  ((y_t,arL - y_t,en) + (y_t,arR - y_t,enR)) / 2. Named "Arabic interface
  text", not "glyph": it changes language, script and instruction-label word
  overlap together.
- **Secondary, total and shares:** Delta = mean_t (y_t,arR - y_t,en) = T + D
  exactly (the 2x2 Shapley decomposition). D / Delta and T / Delta are
  reported with task-bootstrap percentile intervals only if Delta's 95%
  interval excludes 0.
- **Secondary, interaction:** I = mean_t ((y_t,arR - y_t,arL) - (y_t,enR - y_t,en)).
  Its MDE is about twice the main effects' (8.7-10.1 pp at K = 18, analytic).
- **Secondary, the dossier's contrasts:** conditional mirror contrast
  M_ar = ar-RTL - ar-LTR and Arabic-text contrast G = ar-LTR - en.
- **Secondary outcome:** required-change completion, the share of the
  grader's change checks passed (Relay's graders return named checks), with
  the same D and T.
- **Process:** steps, invalid-action rate, truncation share, rate of clicks
  that land on no interactive element, by cell and screen third.
- **Moderators (pre-registered, secondary, task-level regressions with CR2
  standard errors):** T_t on lexical-overlap count (prediction: negative
  slope); D_t on direction-sensitive step count (negative slope); D_t on the
  share of reference targets that change screen half under mirroring
  (negative slope if the effect is positional, after ScreenHaystack's
  model-specific blind zones). The click-landing rates by screen third
  are descriptive.

## Decision rules (primary D; the same labels are reported for T)

- **PRESENT:** two-sided paired t on the K task-level D_t, p <= 0.05. The
  exact sign-flip test (all 2^K patterns when K <= 20) is reported; if it
  disagrees at 0.05 the label is PRESENT_FRAGILE.
- **SMALL:** the 90% t interval of D lies inside (-5, +5) pp (TOST at
  alpha 0.05).
- PRESENT and SMALL can hold together (PRESENT_AND_SMALL).
- **INCONCLUSIVE:** neither.

## Kill criteria

| Id | Trigger | Consequence |
|---|---|---|
| K0 | Any of G1-G12 fails for any locale or seed | No GPU job. Relay's code is repaired and the full gate rerun; thresholds never change. The same gate item failing in three full runs ends Phase 0 with the failure recorded |
| K1 | Gate verdict FAIL_POWER or FAIL_COST | Infrastructure exit: the localized Relay, the gate record and the pilot's English base rates are published; Phase 1 on Relay stops. Routes R1 (a Relay template factory of 50 or more informative tasks, S3's prerequisite) and R2 (a LibreOffice 2x2 on S1a's harness, below) each need their own proposal and gauntlet |
| K2 | pi_hat outside [0.15, 0.85] or K_inf < 12 (FAIL_FLOOR, FAIL_TASKS) | The pixel arm is uninformative on Relay for this model; the mirror claim is dropped; infrastructure exit as K1 |
| K3 | In Stage 1b, an episode's step-0 render hash or role/test-id tree hash differs from Phase 0's for its (task, seed, locale) | The episode is invalid. More than 2% invalid in any cell: INCOMPLETE, no decision |
| K4 | D and T both SMALL and neither PRESENT | Publish the robustness null (chrome localization moves success by less than 5 pp on this app and model) and drop the locale arm from WS3-R |
| K5 | Neither D nor T PRESENT | No reasoning-language arm. zh, ja and pseudo-locales stay deferred until Relay has at least 100 templates in any case |
| K6 | Stage 1b spend reaches its cap | Stop at the last complete task block; analyse if at least 12 tasks are complete, else INCOMPLETE |

Route R2, recorded for a successor and not registered here: LibreOffice's
`SAL_RTL_ENABLED` environment variable forces a mirrored UI with English
strings, and the `UIMirroring` configuration key can hold an Arabic UI
left-to-right (LibreOffice core `vcl/source/app/settings.cxx` at commit
`08f5d410`), which gives a full 2x2 on OSWorld LibreOffice tasks under S1a's
certified harness. About 31-37 of S1a's roughly 72 LibreOffice-like tasks are
informative for 4B or 9B (cross-domain cell, heuristic domain mapping). The
key must not be set through `registrymodifications.xcu`, which at least one
checker reads. The OSWorld VM image's offline Arabic language pack is
unverified.

## Predictions and falsifiers

| | Prediction | Falsifier |
|---|---|---|
| P1 | Phase 0 passes every gate | any gate item fails three full runs (K0) |
| P2 | English pixel success on Relay lies in [15%, 85%] with at least 12 informative tasks | K2 fires |
| P3 | If Stage 1b runs: D < 0 | D is SMALL (90% interval inside +/-5 pp) |
| P4 | If Stage 1b runs: T < 0 | T is SMALL |
| P5 | If Stage 1b runs: the T_t slope on lexical overlap is negative | 95% CR2 interval of the slope lies above 0 |
| P6 | If Stage 1b runs: the D_t slope on the share of targets changing screen half is negative | 95% CR2 interval lies above 0 |

## Reported regardless of outcome

Phase 0: every gate item's result and counts; the chrome share by screen and
locale; catalog size; back-translation and native-speaker verdict counts;
the mirror specification; moderator codings; CPU time. Stage 1a: per-task
English success; pi_hat; K_inf; D_w,Relay; between-seed variance;
sigma2_hat and its bound; p_hat; steps; invalid-action, truncation and
infrastructure rates; the gate's inputs, arithmetic and verdict. Stage 1b (if
run): per-task successes in every cell; D, T, I, Delta, M_ar and G with 95%
and 90% intervals; the sign-flip p; TOST; shares; required-change
completion; process metrics; moderator slopes; tau2_hat (the variance of D_t
minus its sampling part); the selection check (pilot against Stage 1b English
success on the informative tasks); cost per cell.

## Statistics, sample sizes and simulation

- Analytic MDEs (80% power, two-sided 0.05, paired t on task means, exact
  noncentral t; `power-gate.json` `B_analytic_mde_grid`). Dossier design
  (conditional contrast, n = 8, K = 18): 7.3-8.8 pp at tau2 = 0 and 8.1-9.4 pp
  at tau2 = 0.0025 for sigma2 = 0.043-0.0625. 2x2 direction main effect at
  K = 18, tau2 = 0.0025: n = 16 gives 5.05-5.61 pp, n = 32 gives 4.34-4.68 pp,
  n -> infinity gives 3.50 pp. At tau2 = 0.005 the infinite-n floor is 4.95 pp.
- TOST power at a true D of 0 (margin 5 pp, tau2 = 0.0025): 0.86 and 0.77
  at K = 18, n = 24 for sigma2 = 0.043 and 0.0625; 0.76 and 0.63 at n = 16.
- Monte Carlo operating characteristics of the whole staged design (pilot
  selection, gate, main study; four assumed base-rate scenarios, three
  heterogeneity patterns, true D of 0, -3, -5 and -8 pp; 1,500 replicates per
  cell over seeds 42, 43 and 44; `power-gate.json` `D_monte_carlo`). The gate
  passes with probability 0.000 when S1a's cells are transported (93-95% stop
  at FAIL_TASKS), when base rates are mid-range (87-91% FAIL_COST) and near
  the floor (87-89% FAIL_FLOOR), and 0.024-0.039 in the most favourable,
  near-deterministic scenario (0.005-0.012 at the high price). Given a PASS
  there, a true -5 pp effect is called PRESENT in 0.42 (uniform logit shift),
  0.19 (half the tasks) or 0.02 (a quarter) of runs, and a null is called
  SMALL in 0.92-0.97 of runs, with a false PRESENT (always alongside SMALL)
  in at most 0.04. The dossier's fixed design
  on the same draws calls PRESENT in 0.02-0.06 of runs with no effect and in
  0.02-0.16 with a -5 pp effect.
- Every interval in Stage 1b reports K (tasks, the clusters), n and the
  number of episodes. Missing episodes: a task enters only if each of its
  four cells has at least n - 1 valid episodes; cell means use the valid
  episodes.

## Seeds

Random-number seeds: [42, 43, 44] for simulation; 42 for the reported
bootstrap and sign-flip enumeration (exact when K <= 20) and for episode
order. Fixture seeds: gates 42, 43, 44; pilot 101-104 (analysed) and 105
(smoke); Stage 1b 201 onward. vLLM request seed 42 (greedy decoding makes it
inert; vLLM is not batch-invariant, so reruns are not assumed identical).

## Compute caps (D22 counting)

| Job | Cap (GPU-h) | Arithmetic |
|---|---:|---|
| Phase 0, E1-E6 | 0 | CPU only (Mac; host CPU jobs for E4 and E5) |
| Stage 1a | 2.0 | 1.2 x (144 x 36 x 0.000292 + 162 x 0.000292) + 0.10 = 1.97 |
| Stage 1b | at most 15.0 | 4 x K_inf x n x 1.5 x p_hat + 0.10, gate-enforced; for example K_inf = 18, n = 24 and the S1a-realized central p_hat = 0.0054: 18 x 4 x 24 x 0.0081 + 0.10 = 14.1 |
| Registered total | 17.0 | over 8 GPU-h: D24 ruling |

The gauntlet's reviewer budget (0.3 GPU-h) is separate.

## Infrastructure failures and exclusions

Infrastructure failure: the observation is not delivered, the browser or app
crashes, the engine returns HTTP 5xx or times out through the bridge, or the
container is killed. A failed episode is re-queued once at the end of its
task block; a second failure makes it missing. Model behaviour (invalid
actions, truncation at 40 steps, wrong state) is never an infrastructure
failure. Stage 1a: more than 5% of analysed episodes missing makes the pilot
INCOMPLETE and the gate does not run.

## Data rights

Relay: MIT, Kevin's; fixtures and portraits synthetic. Lato: OFL. Camber:
proprietary to Relay's live site; never copied or redistributed.
Noto Sans Arabic: OFL 1.1 (public download, D1). i18next and react-i18next:
MIT. Tesseract and tessdata: Apache-2.0. Playwright: Apache-2.0. Chromium:
BSD-style. Qwen3.5-9B: Apache-2.0. The Arabic catalog is authored in-project
(MIT with Relay); the native-speaker reviewer is credited with consent.
Relay's `.env.local` (never read) and its 5.3 GB `.runtime` directory are
never copied. Public cotcodec artefacts are metrics, hashes, codings and
per-episode records; screenshots and trajectories stay on the host and in
the private archive unless Kevin decides otherwise.

## Integrity gate (the seven failure modes)

1. Implementation bug passing self-review: G1-G12 are independent of the
   code under test where possible (test-id recipes, geometric checks, OCR,
   pixel A/A against the pre-extraction build); Phase 0 is reviewed by a
   fresh agent before the freeze.
2. Hallucinated citation: every source in the proposal is snapshotted with
   its HTTP status and hash; abstract-only sources are labelled.
3. Hallucinated result: no Relay measurement exists yet; every number marked
   simulated is from `power-gate.py` with seeds and inputs hashed.
4. Shortcut reliance: the agent's success could come from English content
   that stays on screen; that is the registered estimand (chrome
   localization), and the chrome share is reported.
5. Bug reframed as insight: a half-mirrored layout or bidi artefact would
   look like a mirror effect; G5, G8 and K3 exist to catch it.
6. Methodology fabrication: the gate rule, estimands and decisions are fixed
   here before any Relay data.
7. Frame-lock: the gate's likely outcome is an infrastructure exit, and that
   exit is written as a first-class result with routes R1 and R2.

## Owner's prior forecast (not a decision input)

Phase 0 passes after repair: 0.8. Stage 1a has pi_hat in band and K_inf of
at least 12: 0.25 (S1a's 9B floor pattern and the frontier pixel results on
Relay point low). Gate PASS given that: 0.3 (above the simulation's 0.05 for
scenario D because a browser app under greedy decoding may be closer to
deterministic than any simulated scenario, which shrinks sigma2). Stage 1b
reached overall, including the native-speaker check and a D24 ruling: about
0.07. If it runs, D PRESENT: 0.35; T PRESENT: 0.5. The expected outcome of
this registration is the infrastructure exit with a measured Relay pixel
floor.

## Freeze procedure

Phase 0 is built and its gate run (CPU); a fresh agent's pre-freeze audit
checks the registration against the code; then
`uv run python scripts/preregister.py freeze s2-arabic-cua-locale-v1 program/preregistrations/s2-arabic-cua-locale-v1.md`
and `verify`; then the D24 ruling for the GPU stages.

## Design decisions (for the owner's acceptance)

1. Split Stage 1a into its own registration (`s2-relay-pixel-floor-v1`,
   cap 2.0 GPU-h, under 8 GPU-h: a registration and a pre-freeze audit, not a
   gauntlet, under D66's rule), leaving this registration with Phase 0, the
   gate and Stage 1b. Recommended.
2. The en-RTL cell and the 2x2 main effect D as primary (the dossier had
   ar-RTL minus ar-LTR).
3. No a11y GPU arm; G2b replaces it.
4. Qwen3.5-9B only (lower S1a rerun floor than 4B: D_w 8.6% against 16.4%).
5. Greedy decoding, thinking on, 2,048 output tokens, as in S1a.
6. Step cap 40 for every task.
7. The pilot design 18 x 4 x 2 and the informative-task rule k_t >= 2 of 8.
8. Floor band [15%, 85%] (dossier) and K_inf >= 12.
9. Gate heterogeneity tau2_gate = max(0.0025, tau2_logit). The alternative
   considered is a fixed 0.006 (the simulated uniform-logit value), under
   which no design with K of 18 or fewer passes; choosing it closes Phase 1 on
   Relay now and leaves Phase 0 plus route R2.
10. sigma2's one-sided 80% upper bound in the gate.
11. Cap price 1.5 x the pilot-measured English price.
12. The 15.0 GPU-h ceiling for Stage 1b.
13. The n grid and the reruns-or-seeds allocation rule.
14. MDE line 5.0 pp (dossier) at 80% power, two-sided 0.05.
15. TOST margin +/-5 pp.
16. Paired t primary, exact sign flip as sensitivity.
17. Held-fixed numerals, dates and times (en-US formatting in every cell).
18. Playwright context locale `en-US` in every cell; `<html lang>` follows
    the catalog.
19. `dir="auto"` on user content and inputs as part of the treatment's
    realism.
20. Noto Sans Arabic, after Lato in the stack.
21. The mirror specification (Firefox RTL guidelines) frozen with Phase 0.
22. Test-id recipes; English-name recipes as an en-only cross-check.
23. Gate seeds 42-44; pilot 101-105; Stage 1b 201 onward.
24. G4's tolerance: 0 differing pixels unless a same-build repeat shows
    nondeterminism.
25. G5's 4 px and 98% lines; G7's 0.05 CER margin against a control render.
26. The native-speaker check as a precondition of the Stage 1b freeze, not
    of Phase 0.
27. Smoke episodes capped at 3 steps, never analysed.
28. One serving session and interleaved task blocks for Stage 1b.
29. Relay's Phase 0 branch stays local until Kevin approves a push.
30. Screenshots and trajectories kept private by default.
