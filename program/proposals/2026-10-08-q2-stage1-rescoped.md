# Research Direction: Q2 Stage 1 Rescoped (rerun-noise floor and harness screen on the certified pair, then a gated scale ladder)

**Status:** draft; gauntlet wave 0. This is the single-owner synthesis of the Q2 Stage 1 design panel (three designs, two judges). Blind closest-prior discrimination, the refute-first triad and the two provider-distinct reviews have not run. Stage S1a is at most 8 GPU-h by registered caps (7.967), so it does not itself need the gauntlet. It waits on the action-path acceptance (C1-C3, A1-A6 and the ladder's N*), the G0 engineering items and a freeze. Stage S1b exceeds 8 GPU-h, so it needs this gauntlet and, under D24, Kevin's trust store or admission ruling. A score of 100 cannot be certified in this repository yet (D24).
**Owner:** Kevin Liu (program owner); synthesis written by a Claude agent acting as the gauntlet's single synthesis owner
**Source cutoff:** 2026-10-08
**Coverage limits:** Retrieval this wave: orx 0.2.2 only (10 discover queries: alphaXiv keyword and embedding, OpenAlex), plus full texts of 2610.01618, 2609.32459 and 2610.00917 through `orx paper --full`. The remaining closest priors are inherited from the 2026-10-06 dossier audit (102 URLs; 95 OK, 7 fixed) and were not re-read in full in this wave. Not used: the arXiv API, Semantic Scholar or the H100-host relay, so there was no forward or backward citation-graph expansion. Not searched: OpenReview, X, Reddit, blogs, patents and Chinese-language sources. The alphaXiv index may lag for papers posted on 2026-10-07 and 2026-10-08. Model-card benchmark numbers (Qwen3.5, OpenCUA) are first-party and were not replicated. The design panel's simulations were re-run in this wave by the synthesis owner with new code (bundle `analysis/`); the panel's scratch scripts are not in the bundle.
**Budgets:** queries=60; wall_minutes=600; tokens=6000000; dollars=100; waves=3; gpu_hours=1
**Novelty verdict:** NO_DIRECT_PRIOR_FOUND
**Safety verdict:** PASS
**Evidence bundle:** evidence/2026-10-08-q2-stage1-rescoped/bundle.json

## Claim and Research Question

**Question (Q2, Stage 1, rescoped).** On web-free OSWorld-Verified desktop
tasks, with the two harnesses the action-path suite certifies, how large is
plain rerun noise, between and within serving sessions? How much do the
harnesses differ:

- as a main effect;
- task by task, as a share of within-task outcome variance;

at Qwen3.5-4B and 9B? And is the harness share large enough that a scale
ladder could detect it shrinking?

**Experiment under review.** The rescoped Stage 1 has two stages:

- **S1a.** `q2-stage1-rescoped-v1`, a DRAFT preregistration:
  `program/preregistrations/q2-stage1-rescoped-v1.md`.
  - 4B and 9B; H-OSW-fixed and H-GA; screenshot only; thinking on with 2,048
    output tokens; T = 15; greedy decoding.
  - A base of 32 web-free confirm-split tasks, with an outcome-blind fill
    rule up to 116.
  - Two serving sessions per size, at least 12 h apart, with two reruns
    each.
  - An OpenCUA-7B 15-step runtime anchor against its three public runs.
  - Registered caps of 7.967 GPU-h.
- **S1b.** Gated, over 8 GPU-h. A replay-only serving probe v3 and then,
  depending on S1a's DR2 and DR5, either:
  - the harness scale ladder (27B-FP8 and 35B-A3B-FP8 added); or
  - an observation-factor study on a certified accessibility-tree variant.

**Claim scope:** `systems-pipeline`. This is a measurement-instrument
calibration; nothing here is an architecture claim.

What the proposal claims:

1. The design answers the noise-floor and harness-screen part of Q2 inside 8
   GPU-h, on the harnesses that will actually run, priced by the measured
   cost card. Every exit is a reportable result.
2. S1a turns the question file's underived "paired MDE about 7-8 pp" kill
   line into a computable admission rule for the scale ladder (DR5). That
   rule says whether the shrinkage question is answerable at an affordable
   size before any ladder GPU-hour is spent.

What it does not claim, stated before the evidence:

1. That S1a answers the scale question or the observation question. It does
   not (Claim boundary: preregistration section 2).
2. That the harness contrast is broad. The certified pair shares its layout,
   template lineage and thinking default, so a null is the likely result
   (prediction P3).
3. That the anchor certifies the runtime. It catches only gross defects (DR-A
   operating characteristics).

## Strategic Fit and Why Now

**For running it now:**

- **Q2 is the program's spine.** Its noise floor is the prerequisite for
  every later computer-use claim (`program/PROGRAM.md`). Stage 0 is nearly
  done:
  - the checker-mutation study is frozen and analysed;
  - the Holo3 audit is confirmatory;
  - the action-path suite v2 is frozen (ledger rows 13-15), and its
    acceptance campaigns are next.
- **Stage 1 as designed is not runnable.** The measured cost card projects it
  to 431.5 GPU-h (job 466). The card's own rule says "rescope before
  gauntlet".
- **The design inherited from the dossier priced the wrong profile.** The
  pinned upstream sources show that both certified harnesses fold history and
  think by default. Every Stage 1 budget so far has priced one of them as the
  cheap window-4, non-thinking profile (E2). The rescope corrects the basis
  before any money is spent.
- **Scoop pressure is real.** Since the dossier (2026-10-06), at least three
  closely related preprints have appeared:
  - harness x model rank reversals: https://arxiv.org/abs/2610.00917 (2026-10-01);
  - run-to-run noise as 54% of outcome variance in configurable agents:
    https://arxiv.org/abs/2610.01618 (2026-10-01);
  - harness gains shrinking with model capability on coding agents:
    https://arxiv.org/abs/2609.32459 (2026-09-26).
  None measures a desktop noise floor across sessions.

**Against, stated with the same weight:**

- The harness pair is narrow, so the most likely S1a outcome is "near-
  equivalent". That is informative (it redirects S1b to the observation
  factor) but not a headline.
- S1a cannot start before the action-path acceptance passes. That needs about
  98 VM-h of CPU campaigns and can fail on a real defect, after which a
  repair attempt is a new executor addendum.
- The anchor needs a decision on third-party model code on a GPU
  (`--trust-remote-code`, R570). Without it, S1a is not externally anchored.

## Primary-Source Evidence

### In-repository measurements (no new GPU job ran in this wave)

**E1. Cost card.** `serving-throughput-probe-v2`, Slurm 466,
`program/evidence/2026-10-07/serving-throughput-probe-v2/`.

- The frozen `harness/serving_probe/budget.py` (SHA-256 `cdb75646...`) on job
  466's points reproduces the card's 9B cells exactly (`analysis/cost_s1a.py`,
  `analysis/cost_s1a.json`):

  | Cell | GPU-h per 360 episodes |
  |---|---:|
  | H1 screenshot | 0.7522 |
  | H1 accessibility tree | 1.1289 |
  | H2-thinking screenshot | 24.1054 |
  | H2-thinking accessibility tree | 29.2954 |

- Total 431.51 GPU-h. 4B and 9B alone come to 110.56, above the 90 GPU-h
  rescope line. The 27B (x4.5) and 35B-A3B (x1.5) multipliers are rules, not
  measurements.

**E2. The certified harnesses' real profile.** Upstream files were re-fetched
on 2026-10-08 from GitHub raw URLs. Their SHA-256 equal
`harness/q2/action_path/upstream/PROVENANCE.json`:

- OSWorld `bfd62bdc` `mm_agents/qwen35vl_agent.py`: `1f39be92...`.
- gym-anything `aae6f7607` `agents/agents/qwen35vl.py`: `93666f27...`.
- OSWorld `bfd62bdc` `scripts/python/run_multienv_qwen35vl.py`: `a3bf2a63...`.

What they show:

- Both default to history_n 100, image_max 20 and fold_size 10.
- Neither sends `chat_template_kwargs`, so both think by the Qwen3.5
  template default. The Qwen3.5-9B card states that thinking is the default
  (https://huggingface.co/Qwen/Qwen3.5-9B).
- Both wrap every later turn in a tool-response wrapper and pass the full reply
  back into history.
- OSWorld's agent raises `ValueError` unless `observation_type ==
  "screenshot"`. Gym-anything's agent has no accessibility path.
- The OSWorld runner defaults are max_steps 50, temperature 0.0, top_p 0.9
  and max_tokens 32,768. Gym-anything's agent defaults to max_tokens 2,048.

The card's cheap H1 profile (window 4, 300 output tokens) therefore prices
neither certified harness. Both must be priced as H2-thinking.

**E3. Prices for the certified pair** (H2-thinking-screenshot profile,
`analysis/cost_s1a.json`):

| Setting | Closed loop | Open loop | Price per episode |
|---|---:|---:|---:|
| T = 15, V = 20, central | 460.6 s per wave (0.006397 GPU-h) | 0.009020 GPU-h; mean modelled prompt 20,036 tokens; ratio max(2.44, 6.827) = 6.827 | **0.009020** (open loop binds) |
| T = 15, V = 16, high (180 s GPU idle per wave, t_env 4 s) | 0.011512 | | **0.011512** |
| T = 15, slowest A1 seed (2.523 req/s) | | 0.011274 | |
| T = 15, V = 8 | central 0.015994; high 0.023025 | | |
| T = 100 (the card's own) | | | 0.06696 |

At T = 100 the original 5,760-episode plan costs about 386 GPU-h for 4B and
9B alone, which is unaffordable.

**E4. Thinking pass-back bound.** The card models every history entry at 300
tokens. Both harnesses pass full replies back, and the template keeps the
reasoning (the `serving-throughput-probe-v2` registration, section 4 item 7,
states this caveat). With 2,048-token history entries:

- the mean modelled prompt over 15 steps is 32,272 tokens;
- the largest context including output is 62,950 tokens, below 131,072;
- the open-loop ratio is unchanged (6.827), so the central price stands;
- scaling every step latency by the prompt ratio (an upper bound) raises the
  V = 16 high price to 0.01331 GPU-h. The S1a K-rule then lowers the base
  from 32 to 24 tasks (preregistration section 6.2).

**E5. Session shift** (`q2-holo3-rerun-audit-v2`, confirmatory,
`program/evidence/2026-10-07/holo3-v2/RESULTS.md`). Two same-day
maintainer runs of Holo3-35B-A3B (82.56 and 78.15) differ by a session shift.
It is not explained by checker time-dependence (p = 0.156), step counts
(p = 0.94) or visible environment failures (12 of 14 run2-unique failures
have no signature). A within-session floor would understate the noise
between sessions.

**E6. Checker defects** (`q2-evaluator-mutation-v1`, descriptive under D35,
`program/evidence/2026-10-08/q2-mutation-confirm/results/README.md`):

- K1 70/74. The four raw-gold failures `0a0faba3`, `15aece23`, `ac1b39ff`
  and `ed43c15f` are excluded from the S1a pool.
- `compare_pptx_files` fails 35 of 36 equivalent non-overlapping z-order
  edits (30 confirmed by both raters, 6 unresolved). Family false-negative
  candidate share 40.2% (32.9-46.3%).
- A GUI-faithful save flips 3 of 92 golds (confirmed). Two of them,
  `9ec204e4` and `b8adbc24`, are confirm tasks whose saved gold is accepted
  by both raters.
- κ = 0.343. Kevin's adjudication of 34 items and the 25-item spot check are
  pending.

**E7. Action path.**

- `q2-action-path-v1` is invalid on C2 (job 768). Its cause was a tap-record
  artifact of GNOME Shell's synchronous grab, not delivery (D43).
- `q2-action-path-v2` and its addenda are frozen (ledger rows 13-15,
  2026-10-08). C2 (seed 45), C1, C3, A1-A6, the ladder (which sets N*), A4
  and A7 are not yet run. Total 98.4 VM-h, CPU only.

**E8. OpenCUA-7B public 15-step runs** (holo3-v2
`receipt-v2-final.json`, external_reference, labelled exploratory):

- three runs: 93.95/359 (26.2%), 86.08/360 (23.9%), 82.72/360 (23.0%);
- pairwise discordance 8.9%, 9.7% and 7.5%;
- member manifest SHA-256 `55d03377...`;
- archive LFS SHA-256 `b642e121...` at dataset revision `5473c39e`.

**E9. Splits** (`program/evidence/q2-mutation/splits.json`, SHA-256
`2099792e...`):

- confirm 120, dev 32, reserve 53;
- the S1a pool of 116 by domain: gimp 8, calc 28, impress 24, writer 12,
  multi_apps 24, thunderbird 7, vlc 6, vs_code 7;
- draft draw: `analysis/task-draw-K32.json`, with K = 24 and K = 16 nested.

### External sources (fetched 2026-10-08, HTTP 200, hashed under `snapshots/`)

**Models and runtime:**

- **X1. Qwen3.5 model cards.**
  https://huggingface.co/Qwen/Qwen3.5-9B and
  https://huggingface.co/Qwen/Qwen3.5-4B (revision `851bf6e8`).
  - OSWorld-Verified 41.8 (9B) and 35.6 (4B). First-party; the evaluation
    harness and step budget are not stated.
  - Thinking mode by default. The recommended thinking sampling is
    temperature 0.6-1.0, which S1a does not use.
- **X2. OpenCUA-7B.** https://huggingface.co/xlangai/OpenCUA-7B (MIT,
  revision `a2efb7d2`; Qwen2.5-VL-7B base). OSWorld-Verified 24.3% at 15
  steps (first-party). vLLM serving needs `--trust-remote-code` (vLLM 0.12.0
  or later). Paper: https://arxiv.org/abs/2508.09123 (2025-08-12).
- **X3. Public trajectories.**
  https://huggingface.co/datasets/xlangai/ubuntu_osworld_verified_trajs
  (MIT, revision `5473c39e`).
- **X4. Runtime sources.**
  - OSWorld paper: https://arxiv.org/abs/2404.07972 (2024-04-11).
  - OSWorld repository: https://github.com/xlang-ai/OSWorld (fetched 2026-10-08).
  - Gym-anything repository: https://github.com/cmu-l3/gym-anything (fetched
    2026-10-08).
  - vLLM v0.31.0 release: https://github.com/vllm-project/vllm/releases/tag/v0.31.0
    (fetched 2026-10-08).

**Related studies:**

- **X5.** https://arxiv.org/abs/2608.06171 (2026-08-06). Rerunning the same
  observation mode on the same tasks "changes 12-14% of outcomes" (web;
  dossier-verified, abstract).
- **X6.** https://arxiv.org/abs/2610.01618 (2026-10-01; full text read).
  About 54% of score variance among genuine attempts is run-to-run noise.
  432 configurations x 5 runs, 4 scientific coding tasks; not a desktop
  study.
- **X7.** https://arxiv.org/abs/2610.04433 (2026-10-03). A harness swap and
  a rerun each flip 13% of SWE-bench Verified tasks (dossier-verified).
- **X8.** https://arxiv.org/abs/2609.07925 (2026-09-07). Qwen3.5-4B scores
  8.3% vs 37.2% across two coding harnesses; a large model is unchanged
  (dossier-verified, full-text reading).
- **X9.** https://arxiv.org/abs/2609.32459 (2026-09-26; full text read).
  Harness gains diminish as model capability improves on SWE-style repair:
  ten Qwen and DeepSeek models, temperature 0. Coding only; no rerun-noise
  measurement.
- **X10.** https://arxiv.org/abs/2610.00917 (2026-10-01; full text read).
  66 model-harness configurations; rankings reverse across harnesses. Its
  section 7 notes "one counted run per task" and that "run-to-run variance is
  not measured".
- **X11.** https://arxiv.org/abs/2610.00651 (2026-09-30). G-theory
  decomposition over 22 benchmarks; repeated cells "rare"
  (dossier-verified).
- **X12.** https://arxiv.org/abs/2609.40284 (2026-09-30). cua-speedrun:
  harness x model x five seeds on OSWorld, screenshot-only, action-path
  suite App. I.1 (dossier-verified, full text).
- **X13.** https://arxiv.org/abs/2607.28367 (2026-07-30). 15.3% of audited
  FAIL verdicts wrong; 17.5% on the 57 OSWorld-Verified items
  (dossier-verified).
- **X14.** https://arxiv.org/abs/2609.22220 (2026-09-02). Mutation analysis
  of kernel-benchmark oracles (dossier-verified).
- **X15.** https://arxiv.org/abs/2609.09218 (2026-09-06). Scaffold ownership
  as an uncontrolled measurement axis in agent benchmarks (abstract).

### Claim registry (status this wave)

| id | Claim | Locator | Status |
|---|---|---|---|
| C01 | Card cells and total | E1, `cost_s1a.json` | RECOMPUTED |
| C02 | Both harnesses fold, think, screenshot-only | E2, raw files hashed | VERIFIED (source, hash-matched) |
| C03 | Per-episode prices 0.009020 / 0.011512 | E3 | RECOMPUTED |
| C04 | Thinking pass-back bound 0.01331 | E4 | RECOMPUTED (upper bound by construction) |
| C05 | Holo3 session shift | E5 | IN-REPO CONFIRMATORY |
| C06 | z-order false negatives; P1; K1 | E6 | IN-REPO DESCRIPTIVE (adjudication pending) |
| C07 | OpenCUA public runs 23.0-26.2%, discordance 7.5-9.7% | E8 | IN-REPO EXPLORATORY |
| C08 | Qwen3.5 OSWorld-Verified 35.6 / 41.8 | X1 | FIRST-PARTY |
| C09 | OpenCUA-7B 24.3% at 15 steps; trust-remote-code | X2 | FIRST-PARTY |
| C10 | 12-14% web rerun flips | X5 | DOSSIER-VERIFIED (abstract) |
| C11 | 54% run-to-run variance | X6 | VERIFIED (full text, section 4.2) |
| C12 | Harness gains shrink with capability (coding) | X9 | VERIFIED (full text, sections 1, 5) |
| C13 | One run per task; variance not measured | X10 | VERIFIED (full text, section 7) |
| C14 | 13% harness and rerun flips | X7 | DOSSIER-VERIFIED |
| C15 | FrogNano 8.3% vs 37.2% | X8 | DOSSIER-VERIFIED (full text) |
| C16 | Power figures | `analysis/sim_s1a.json`, `sim_signflip.json` | SIMULATED (seeded) |

## Closest Prior Work

| Prior | Date | What it does | Delta to this design |
|---|---|---|---|
| cua-speedrun, https://arxiv.org/abs/2609.40284 | 2026-09-30 | Harness x model x five seeds on OSWorld, runtime/harness/model error separation, the action-path suite this program ported | No between-session floor, no task x harness variance share, no checker correction, screenshot only, no scale screen |
| Routing Is Least Learnable..., https://arxiv.org/abs/2608.06171 | 2026-08-06 | Observation modes x two backbone sizes with a rerun band | Web only; band measured in 2 of 8 cells; one session |
| Agents Are Systems, Not Models, https://arxiv.org/abs/2610.01618 | 2026-10-01 | Five configuration axes x 5 reruns; 54% of variance is rerun noise | Scientific coding tasks, no desktop, no harness-implementation factor, no session structure, no checker audit |
| Finding the Right Fit, https://arxiv.org/abs/2610.00917 | 2026-10-01 | 66 model-harness configurations; rank reversals | One counted run per task; no noise floor; terminal and coding only |
| Beyond the Model, https://arxiv.org/abs/2609.32459 | 2026-09-26 | Harness gains shrink with model capability (coding, ten models) | Coding only; temperature 0 with no measured rerun noise; this design defers shrinkage to S1b and makes no claim in S1a |
| Agent Evaluation Reliability, https://arxiv.org/abs/2610.00651 | 2026-09-30 | G-theory model x scaffold decomposition | Repeated cells rare, so rerun variance is not identified; no desktop factor |
| What Does a Harness Buy?, https://arxiv.org/abs/2610.04433 | 2026-10-03 | Harness swap vs rerun flips (13% each) on SWE-bench Verified | Coding; one session; no checker mutation |
| How Benchmarks Mis-Score CUAs, https://arxiv.org/abs/2607.28367 | 2026-07-30 | Hand audit of FAIL verdicts | False negatives only, no mutation testing; S1a uses this program's mutation-tested correction |

## Novelty Ledger

| Proposed component | Closest prior | Same | Delta | Confidence |
|---|---|---|---|---|
| Between- vs within-session rerun floor for desktop CUAs, with infrastructure loss removed per episode | 2608.06171; Holo3 v2 (this program) | Rerun discordance as the noise unit | Desktop tasks; sessions as a registered factor (fresh engine and VM pool, 12 h apart); certified action path; D_b − D_w estimated | Medium |
| Task x harness variance share of a certified harness pair, with a session-aware unbiased estimator | 2610.00651; 2610.01618; 2609.40284 | Variance decomposition of agent outcomes | Harness implementations certified identical at the action layer, so the share is about prompting and layout, not input bugs; estimator robust to session-specific harness effects | Medium |
| Admission rule tying the S1a share to the ladder's detectable shrinkage (DR5) | none found | | A pre-specified go/no-go for a scale study, from measured components | Medium-low (procedure, not a finding) |
| Checker-corrected verdicts from mutation testing | 2607.28367 (hand audit) | Correcting benchmark verdicts | Correction from this program's mutation study, a sensitivity only | Medium |
| Harness share vs scale | 2609.32459; 2609.07925 | Harness effect vs model capability | Desktop computer use, measured noise floor; S1a only screens it, S1b would test it | Low for S1a; NARROWED for S1b |
| External runtime anchor (OpenCUA reruns) | standard practice | Reproducing public runs | Control, not a contribution | n/a |

Kill-shot verdicts: the desktop noise floor with session structure is
`STILL_OPEN`; the variance-share decomposition is `NARROWED` (2610.01618,
2610.00651); harness shrinkage with scale is `NARROWED` (2609.32459 for
coding).

No direct prior art found through 2026-10-08 under orx 0.2.2 coverage (10
discover queries, listed with returned ids in `query-log.json`: embedding and
keyword queries on rerun noise of computer-use agents, OSWorld harness rerun
variance, variance decomposition with repeated runs, harness sensitivity
versus model scale, OSWorld-Verified reproducibility, accessibility-tree
observation with Qwen3.5, an OpenAlex query on agent evaluation reliability,
and a cua-speedrun follow-up query), plus the dossier's 2026-10-06 coverage.
Excluded from that coverage: OpenReview, social media, patents, Chinese-
language sources and citation-graph expansion.

## Mechanism and Falsifiable Predictions

**Mechanism.**

- For a fixed model, task and harness, an agent's outcome is a Bernoulli draw
  from p_zth.
- Reruns differ because:
  - the desktop's timing and rendering vary;
  - batched serving is not bit-deterministic even under greedy decoding;
  - each session has its own engine state and VM pool.
- The harness acts by what it shows the model and how it turns replies into
  actions: tool spec, wait and terminate handling, how unparseable replies
  are treated. Because the action path is certified (action-path v2), a
  harness effect cannot come from dropped or wrong input events.

**Predictions** (preregistered in S1a; each with its falsifier):

| | Prediction | Basis | Falsified if |
|---|---|---|---|
| P1 | Session excess is positive: D_b − D_w > 0 | E5 | The one-sided 95% upper bound of pooled D_b − D_w is below 1 pp. The within-session floor would then suffice, and Holo3's shift would not generalise to this stack |
| P2 | The pooled between-session floor D_b lies between 6% and 20% | X5 12-14%; X7 13%; E8 7.5-9.7% | Its 95% interval lies wholly outside [6%, 20%] |
| P3 | The pair is near-equivalent (DR2): \|δ\| small and π_small below 0.12 | Shared layout and thinking default (E2) | DR2 classifies the pair as present |
| P4 | 4B is not at the floor: at least 10% pooled success under at least one harness | X1 35.6% first-party; T = 15 lowers it | DR1 fires |
| P5 | Realized GPU-h per episode is at most the central price 0.009020 | Continuous dispatch, early terminations | It exceeds the high price 0.011512 (DR4) |

**Kill criteria** (registered):

- **ANCHOR-FAIL.** OpenCUA-7B lands more than 2 paired SE outside the public
  runs' range. A1 does not start.
- **DR0.** Infrastructure loss above 5% in any cell, or an incomplete base.
  Stop, debug without reading outcomes, and take a new id.
- **Pre-freeze.** If K_base < 16 at the A0-measured price, or truncation
  exceeds 20% of steps, the draft is rejected and goes back to review.

## Cheapest Decisive Pilot

**The pilot is A0a** (pre-freeze, development split only, cap 22 minutes,
0.367 GPU-h): Qwen3.5-9B, 4 dev tasks x 2 harnesses x 2 reruns = 16
episodes, through the real engine, bridge, VMs, executor and checker. It is
decisive for S1a's feasibility on three counts:

1. **Cost.** Its measured GPU-h per episode sets c_proj. Under the
   registered rule, K_base = min(K_N*, 8 x floor(0.375 / c_proj / 8)). If
   that falls below 16, S1a as drafted is rejected.
2. **Truncation.** The truncation rate at 2,048 tokens decides whether greedy
   thinking under this budget works at all (gate: 20% of steps).
3. **Plumbing.** It is the first end-to-end run of the certified pair. Any
   defect is fixed before the freeze.

**A0b** (cap 18 minutes) is the same for the OpenCUA anchor: 4 dev episodes.

**S1a itself is the cheapest decisive experiment for S1b.** For about 6-8
GPU-h, DR5 decides whether the harness scale ladder (32-41 GPU-h projected,
below) can detect anything. The alternative of running the ladder blind
risks a full ladder with an MDE larger than the effect.

**Orx pilot status.** No orx experiment node has run for this design, so the
executable-pilot cap (79) applies until A0a runs as an orx `slurm-manifest`
node through the project's fixed run command.

## Controls, Baselines, and Ablations

| Control | Implementation |
|---|---|
| Within-session harness contrast | Both harness clients interleave on one engine in random order in every block. Harness is never confounded with session, engine state or host load |
| Between-session floor | Two sessions per size, each a fresh engine and VM pool, at least 12 h apart. Sessions, not just reruns, carry the floor (E5) |
| External runtime anchor (D11) | OpenCUA-7B on the upstream action path against three public runs on the same tasks. Read before A1 |
| Action path | Only certified harness and executor layers (action-path v2 A1-A6). The anchor's upstream path is deliberate and disclosed |
| Infrastructure | Per-episode loss definition (VM, guest-server restart under D30/D33, engine error, executor, runner, checker), one replacement, DR0 at 5% |
| Engine identity | Engine flags identical to the cost card. Prompt token-id digests are logged, so any reread or replay can check prompt identity |
| Host load | Quiet-host rule, with host snapshots per block |
| Checkers | Raw verdicts primary. Secondary: z-order-corrected comparator validated on the confirm mutants. K1 gold failures excluded. P1 save-flip tasks flagged |
| Truncation | Per-cell truncation rate; δ with truncation-hit episodes removed |
| Estimator robustness | Session-aware X primary; sign-flip and Bernoulli forms as sensitivities; GLMM with a homogeneity LR test |

**Not controlled, and why:**

- Step budget and thinking budget are held equal at T = 15 and 2,048 tokens
  instead of each harness's native setting. The harness factor is therefore
  "prompt, layout and action handling under a matched budget", as in design C.
- Sampling is greedy for both.

**Baselines.** There is no model baseline: S1a compares harnesses within
models. The anchor is the external baseline for the runtime.

## Evaluation, Statistics, and Leakage Checks

**Estimands** (preregistration section 9):

- D_b, D_w and D_b − D_w per size and pooled;
- δ pooled and per size;
- X, the session-aware U-statistic mean_t d_t1 d_t2;
- π = (X/4) / (X/4 + D_b/2), and π_small;
- the scale screens δ_4B − δ_9B and π_4B − π_9B;
- the session shift;
- the anchor contrasts;
- the realized cost card.

**Inference:**

- Task-cluster percentile bootstrap, 10,000 resamples, seed 42.
- δ: paired t, two-sided 5%.
- X: one-sided within-task-session permutation, 10,000 permutations.
- Session shift: permutation of session labels within (task, harness).
- GLMM secondary.

**Operating characteristics.** Seeded Monte Carlo
(`analysis/sim_s1a.py`, 2,000 data sets per point;
`analysis/sim_signflip.py`, 1,000). Literature scenario: base success 15% and
30%, task SD 3.5 logit, true discordance 12% and 18%.

| Quantity | K = 32 | K = 64 | K = 116 |
|---|---:|---:|---:|
| δ pooled MDE (80%, two-sided 5%) | 7.4 pp | 5.1 pp | 3.6 pp |
| δ per size (4B / 9B) | 10.3 / 11.4 pp | 6.6 / 7.9 pp | 4.8 / 5.8 pp |
| δ_4B − δ_9B screen MDE | 16.6 pp | 10.8 pp | |
| D_b pooled 95% half-width | ±5.6 pp | ±4.0 pp | ±3.0 pp |
| D_b − D_w 95% half-width | ±3.4 pp | ±2.5 pp | ±1.8 pp |
| X permutation test: size (null; σ_f = 0.5) | 0.022; 0.052 | 0.046; 0.040 | |
| X power at RMS per-task harness effect 15 / 22 pp | 0.38 / 0.76 | 0.57 / 0.96 | |
| π_small SD (null; π = 0.14) | 0.048; 0.067 | 0.034; 0.046 | 0.026; 0.035 |
| Holo3-sized session shift (3.6 pp), power per size | 0.10-0.16 | 0.23-0.33 | |

**Other scenarios at K = 32:**

| Scenario | δ pooled MDE | Notes |
|---|---:|---|
| High noise (task SD 2.5) | 8.1 pp | X power 0.49 at RMS 18 pp; Bernoulli-statistic size 0.07-0.09 with σ_f = 0.5 |
| Low base (8% and 20%) | 6.5 pp | the 4B-only MDE is not reached: floor tasks carry no information |
| OpenCUA-calibrated (task SD 6.9, bimodal; 18% and 24.3%) | 5.9 pp | per size 9.8 / 9.8 pp; X power 0.79 at RMS 20 pp |

**Estimator check.** With task x harness x session noise σ_f = 0.5 and no
true interaction:

| Statistic | Mean | Permutation size |
|---|---:|---:|
| Design A's Bernoulli-corrected X | +0.0024 | 0.072 |
| Session-aware X | +0.0009 | 0.052 |

The session-aware form is primary. The sign-flip test (size 0.010-0.046 in
every scenario) is the conservative sensitivity.

**Ladder planning value for DR5.** A harness-only ladder with 60 tasks x 4
sessions x 1 rerun per rung detects full shrinkage from a 4B share of about
0.21 (literature scenario; 0.27 under the OpenCUA calibration, on a grid of
about 0.06). Design
C's figure for its 2x2 design is 0.20. Under the S1a null, π_small's upper
bound sits near 0.08, so NO-GO is the expected exit if the pair is
near-equivalent.

**Anchor operating characteristics** (OpenCUA-calibrated, 4,000 data sets):

| Runtime deficit | P(kill) |
|---|---:|
| none (false kill) | 0.008 |
| 4.2 pp | 0.19 |
| 6.1 pp | 0.48 |
| 7.9 pp | 0.74 |
| 11.2 pp | 0.97 |

With only the minimum 58 tasks completed, a 7.9 pp deficit is caught with
probability 0.35.

**Leakage checks:**

- No confirm-split task is touched before the freeze; A0 uses dev tasks.
- The fill rule reads cost only.
- The K-rule reads A0's cost only, and can only lower K.
- The public anchor results are external and fixed (dataset revision
  `5473c39e`).
- Mutation-study labels do not depend on agent outcomes.
- The task draw and orders are seeded and committed before the freeze.

**Red flags checked:**

- No outcome-dependent stopping. The only sequential element is the
  cost-based fill rule.
- No post-hoc metric choice: raw verdicts are primary and the alternatives
  are listed.
- A null δ is read through the registered equivalence class, not as "no
  effect".

## Compute and Reproducibility

**Ceiling.** S1a registered caps: gpu_hours: 8. Precisely 7.967 GPU-h =
478 minutes of one H100, counted under D22.

| Job | Cap | GPU-h | Central | High |
|---|---:|---:|---:|---:|
| O1 overlay build (pre-freeze) | 3 min | 0.050 | 0.012 | 0.050 |
| A0a 9B dev pilot, 16 episodes | 22 min | 0.367 | 0.244 | 0.351 |
| A0b OpenCUA dev smoke, 4 episodes | 18 min | 0.300 | 0.220 | 0.287 |
| O2 overlay build (post-freeze) | 3 min | 0.050 | 0.012 | 0.050 |
| ANC anchor, up to 116 episodes | 32 min | 0.533 | 0.449 | 0.533 |
| A1, 4 jobs (4B, 9B) x (S1, S2) | 4 x 100 min | 6.667 | 5.018 | 6.561 |
| **Total** | 478 min | **7.967** | **5.955** | **7.832** |

All figures are derived from the cost card with the frozen budget module
(`analysis/cost_s1a.py`):

- A1 base: 512 episodes at K = 32.
  - central 512 x 0.009020 + 4 launches x 6 min = 5.02 GPU-h;
  - high 512 x 0.011512 + 4 x 10 min = 6.56 GPU-h;
  - per job, high: 128 x 0.011512 h = 88.4 min + 10 = 98.4 min, against
    100 min.
- At N* = 8 (V = 8): K = 16, 256 episodes, high 6.56 GPU-h, 98.4 min per
  job.
- Anchor: the card's H1-screenshot profile at the unmeasured-rung multiplier
  1.5 is 432.6 s per wave. That gives 0.36 GPU-h for 116 episodes at V = 40,
  and about 66 episodes inside the 22 usable minutes at V = 20 (the minimum
  for a reading is 58).
- The fill rule turns any slack into tasks inside the caps. Expected spend
  is 6-8 GPU-h.

**VM time** (CPU-only lane, D12):

- A1: 105 VM-h central, 120 high, 133 reservation bound.
- A0a: 4 VM-h. Anchor: at most 21 VM-h.
- The action-path suite (98.4 VM-h) comes first.

**Stage S1b projection** (card rule; unmeasured multipliers until probe v3):

- **Harness ladder.** 35B-A3B-FP8 and 27B-FP8 at 60 tasks x 2 harnesses x 4
  sessions, plus two more sessions of 4B and 9B on 60 tasks: 31.9 GPU-h
  central, 41.3 high. 27B alone is 19.5 / 24.9 at the x4.5 rule.
- **Observation branch** (one rung, 60 tasks x 2 harnesses x 2 observations
  x 4 sessions): 9.1 central, 13.0 high. It needs a certified
  accessibility-tree harness variant and A7.
- **Serving probe v3**, its own registration, at most 1 GPU-h, replay only.
  It measures:
  - the 27B and 35B-A3B multipliers;
  - TPOT against V up to 40;
  - the front-end fix suggested by r3: 711 of 5,200 multimodal cache hits,
    API server at 107% CPU, and TTFT rising from about 2.1 s at steps 4-9 to
    28.8 s at step 16. The fix would be checked with an identity check on
    prompt token ids.

**Reproducibility contract:**

- **Images.**
  - Engine: `docker.io/vllm/vllm-openai@sha256:b18abb2df97b8f798e81862bd93f872ea18613372e2c3adc0cc2ac21e66ac12f`
    plus the cu129 overlay, rebuilt from the draft commit (O1) and the
    freeze commit (O2); image IDs are recorded in the build receipts.
  - VM: `happysixd/osworld-docker@sha256:0e6497a9295647cf05bf2b2af522fdd79bdeba2737595259cab310a3bcf6baa9`.
  - Runner: GPU-less, `sha256:ac2b5815...`, locked in
    `infra/q2-vm-runner/image-lock.json`.
- **Launch.**
  - GPU jobs go through `scripts/submit_docker_research_job.py` (dry-run,
    test-only, submit) with the vllm container profile. The A1 form of the
    argv (shown for the 9B session-1 job) is
    `sbatch --parsable --partition=research --nodes=1 --ntasks=1 --job-name=q2s1a-a1-9b-s1 --gres=gpu:h100:1 --cpus-per-task=32 --mem=160G --time=01:40:00 --signal=B:USR1@180 infra/slurm/host-single-node/docker-research.sbatch`.
  - VM jobs go through `scripts/submit_vm_campaign.py` on the CPU-only lane
    (`infra/slurm/host-single-node/vm-campaign.sbatch`).
  - Each A0 or A1 GPU job will be an orx `slurm-manifest` node run with the
    project's single fixed command.
- **Seeds:** seeds: [42, 43, 44].
  - 42: task draw, extension order, anchor order, engine seed, bootstrap and
    permutations.
  - 43 and 44: the two sessions' episode orders.
  - Decoding is greedy.
- **Checkpoints and preemption.** There is no training state. The record
  files are append-only. On USR1 (180 s before the limit) the driver
  dispatches nothing new, and in-flight episodes are recorded as
  cap-truncated. A job is never rerun to improve an outcome.
- **Artifacts.**
  - On the host run root: per-step token logs, prompt-id digests, IR
    actions, checker inputs (hashed) and host snapshots.
  - In `program/evidence/`: summaries, receipts and analyses with SHA-256
    indexes.
- **Cost ceiling.** The caps above. An amendment that would raise them is
  not made; the design would go to the gauntlet instead.

**Known mismatches with the deterministic doctor:**

- The doctor's real-model-loop check reads `harness/runner.py`, which does
  not exist. S1a's loop will be `harness/q2/stage1/`, not yet built (G0).
- No compute attestation exists for S1a. The bundle records job 466's lane
  as the cost basis only.

## Safety, Data Rights, and Monitorability

**Untrusted code and R570:**

- S1a serves model weights on GPUs. Model-chosen actions execute only inside
  GPU-less VMs and runners (D7, D12); no model-generated code touches a GPU.
- The OpenCUA-7B anchor needs `--trust-remote-code`, i.e. its repository's
  model code inside the GPU container. That is third-party code, not code
  under study. It is admissible only by a D29-style decision (pinned by
  revision and file hashes, reviewed). Without the decision the anchor is
  UNAVAILABLE and S1a is labelled "not externally anchored"
  (preregistration decision 21).

**Isolation:**

- No new Docker network (D13). The engine binds 127.0.0.1, and runners
  reach it through a bind-mounted Unix-domain socket.
- VMs run with `--network none`.
- No host reconfiguration, no sudo, and `~/cotcodec` is untouched.

**Data rights:**

- OSWorld task configs: Apache-2.0. The file cache's documents contain
  third-party content; only metadata, verdicts and hashes are released.
- Qwen3.5: Apache-2.0. OpenCUA-7B: MIT. Gym-anything: MIT. Public
  trajectories: MIT; only per-task `result.txt` members are read.
- The OpenCUA-7B weight download (about 16 GB) is a public research download
  under D1, recorded with revision and SHA-256.
- Snapshots in this bundle keep metadata extracts and hashes, not page
  bodies.

**Public repository.** No host IP, secret or private dataset is committed.
Host run paths already public in earlier evidence are reused.

**Monitorability.**

- Every step logs tokens, IR and prompt-id digests.
- Every episode logs restarts and checker inputs.
- Infrastructure losses and cap truncations are listed, never dropped.
- Every deviation is reported.

**Red lines:** none crossed.

**Integrity gate (seven AI-research failure modes; the list follows the
gauntlet rule, the ARS file was not opened):**

1. **Implementation bug passing self-review.** Possible in the new episode
   driver and bridge. Mitigations: CPU fake-engine tests, the A0 pilot, and
   the action-path certification of everything below the IR.
2. **Hallucinated citation.** Every URL was fetched on 2026-10-08 with HTTP
   200 and hashed. Numbers not read this wave are labelled dossier-verified
   or first-party.
3. **Hallucinated result.** No result is claimed. Every number is from a
   committed record or a seeded simulation in the bundle.
4. **Shortcut reliance.** Cost uses the frozen budget module, not new
   assumptions. Departures (high price, thinking bound) are labelled.
5. **Bug reframed as insight.** The card's mispricing of H-OSW was checked
   against hash-verified sources before it changed the design.
6. **Methodology fabrication.** The estimators' bias and size were checked
   by simulation, including a scenario that breaks the Bernoulli correction.
7. **Frame-lock.** Three designs were compared by two judges. The losing
   designs' best parts were grafted, and the observation factor is kept as
   S1b's alternative branch.

## Negative-Result Value

Every S1a exit is publishable within Q2:

- **ANCHOR-FAIL.** Our runtime does not reproduce public OpenCUA runs. That
  is a debugging result, and it saves every later Stage 1 GPU-hour from a
  broken stack.
- **Near-equivalent pair (P3 holds).** "Two upstream Qwen3.5 harnesses whose
  action paths are certified identical do not differ beyond X pp on desktop
  tasks". This redirects the harness question to the observation factor and
  is a useful counterpoint to rank-reversal results (2610.00917).
- **D_b − D_w at or near 0 (P1 fails).** The Holo3 session shift does not
  generalise to a controlled self-hosted stack. Within-session reruns would
  then suffice for this configuration, which halves later costs.
- **4B at the floor (P4 fails).** A ladder decision, and evidence that 15
  steps are too few for 4B on web-free LibreOffice-heavy tasks.
- **Cost above the high price (P5 fails).** The synthetic card under-prices
  real episodes, which bounds every later projection.

Even with no S1b, S1a delivers the first measured desktop noise floor with a
session factor, and the per-episode cost card the question file required
("the first 10 GPU-h must log real per-episode costs").

## Preflight Doctors

| Doctor | Status | Evidence | Remediation |
|---|---|---|---|
| Source | PASS | orx 0.2.2 reachable; 10 discover queries and 3 full texts this wave (`query-log.json`); 26 cited pages fetched 2026-10-08 with HTTP 200 and hashed (`snapshots/`); raw upstream harness files hash-equal to PROVENANCE.json; coverage limits recorded in the header | Use the host relay for Semantic Scholar and arXiv-API citation expansion of 2610.01618, 2610.00917 and 2609.32459 in wave 1 |
| Citation | PASS | Claim registry C01-C16 with locator and status; three new priors verified in full text; inherited numbers labelled dossier-verified; first-party model-card numbers labelled | Independent line-by-line audit; re-read cua-speedrun and 2608.06171 in full for the delta rows |
| Novelty | FAIL | Bounded no-direct-prior wording with listed queries, but the blind closest-prior discrimination and the novelty refuter have not run, and only 10 queries were spent this wave | Run the blind discrimination against 2610.01618 and 2609.40284; expand queries (OpenReview, citation graph) |
| Design | PASS | Synthesis owner's self-check, not an independent review. Design-panel judges scored the winning design 30 and 31 with no fatal flaw. Power re-derived by seeded simulation (`analysis/sim_s1a.json`, `analysis/sim_signflip.json`). Estimator bias checked under task x harness x session noise. Decision rules DR0-DR5 and DR-A fixed before any confirm episode | Refute-first identification lens; review DR5's planning value M against a full-likelihood estimator |
| Compute | FAIL | Caps of 7.967 GPU-h derived from the card with the frozen budget module, but no S1a image, manifest, dry-run, container smoke or orx node exists; the episode driver and engine bridge are not built (G0); action-path acceptance and N* are pending | Build G0; run A0a as an orx slurm-manifest node with dry-run, test-only and provenance attested |
| Safety | PASS | R570 respected (model weights only on GPU; actions in GPU-less VMs; D7, D12, D13); OpenCUA remote code gated on a D29-style decision; licences per source; no host address or private data committed; integrity gate answered | Kevin or the program decides the OpenCUA remote-code admission |

Deterministic doctor output (`uv run python scripts/research_direction_doctor.py program/proposals/2026-10-08-q2-stage1-rescoped.md`):

Exit status 1 (FAIL), output verbatim from the run on this file and its bundle.
The Novelty and Compute FAIL rows, the missing reviews, trust store, compute
attestations and audit row are the expected wave-0 state described above.

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
    "compute lacks container_smoke attestation",
    "compute lacks slurm_test attestation",
    "compute lacks provenance_verification attestation",
    "doctor artifact 2 did not pass",
    "doctor artifact 4 did not pass",
    "evidence bundle lacks audit_log artifact"
  ],
  "path": "/Users/kevinliu/repos/cotcodec-wt-q2-stage1/program/proposals/2026-10-08-q2-stage1-rescoped.md",
  "remediation": [
    "Novelty doctor lacks PASS plus concrete evidence"
  ],
  "reviewerTotals": {
    "A": 0,
    "B": 0
  },
  "sourceCounts": {
    "allUrls": 20,
    "recognizedPrimaryUrls": 20
  },
  "status": "FAIL"
}
```

## Independent Adversarial Reviews

Reviewer A: NOT_RUN | provider=none-yet | model=none-yet | run_id=none-yet | artifact=none-yet

Reviewer B: NOT_RUN | provider=none-yet | model=none-yet | run_id=none-yet | artifact=none-yet

Wave 0 produced only the synthesis. The loop's next steps are the blind
closest-prior discrimination, the refute-first triad, and two
provider-distinct reviewers. No review can count toward a 100 yet:

- That needs Ed25519-signed receipts whose keys come from an external trust
  store pinned by protected CI. Only Kevin can create it (D24).
- Per D23 and D26, the second provider would be self-hosted open-weight
  inference (Qwen3.6-35B-A3B) inside the declared 1 GPU-h.

The accepted score is capped:

- at 89 by the missing independent review;
- at 79 by the missing executable orx pilot;
- at 74 until the blind discrimination and the novelty coverage are complete.

## Scorecard

| Dimension | Reviewer A | Reviewer B | Defect/evidence |
|---|---:|---:|---|
| Question and strategic fit | 0 | 0 | Not yet reviewed (0 means unreviewed). Synthesis note: spine question; the rescope is forced by the 431.5 GPU-h card |
| Primary-source evidence | 0 | 0 | Not yet reviewed. Synthesis note: 16-claim registry; upstream harness files hash-verified; three new priors read in full |
| Defensible novelty delta | 0 | 0 | Not yet reviewed. Synthesis note: desktop session-structured floor STILL_OPEN; share decomposition NARROWED |
| Mechanism and falsifiability | 0 | 0 | Not yet reviewed. Synthesis note: P1-P5 each with a falsifier; ANCHOR-FAIL and DR0 kill criteria |
| Controls and causal identification | 0 | 0 | Not yet reviewed. Synthesis note: within-session interleaving; between-session floor; matched budgets make the harness factor narrow |
| Evaluation and statistics | 0 | 0 | Not yet reviewed. Synthesis note: δ MDE 7.4 pp at K = 32; X power 0.38 at RMS 15 pp; session shift weakly powered |
| Feasibility and information per GPU-hour | 0 | 0 | Not yet reviewed. Synthesis note: 7.967 GPU-h caps; gated on the action-path acceptance |
| Reproducibility and artifact contract | 0 | 0 | Not yet reviewed. Synthesis note: pinned images, seeds, task draw; no S1a image or orx node yet |
| Safety, data rights, and monitorability | 0 | 0 | Not yet reviewed. Synthesis note: OpenCUA remote code needs a decision |
| Independent adversarial review quality | 0 | 0 | No review exists; no trust store (D24) |
| **Total** | **0** | **0** | Unreviewed. Caps 74, 79 and 89 apply |

## Iteration Log

| Wave | Score | Highest-impact defect | Change | Result |
|---:|---:|---|---|---|
| 0 | 0 (unreviewed) | The inherited design priced H-OSW as the card's cheap window-4, non-thinking profile. The pinned source shows it folds and thinks, as H-GA does, so every Stage 1 budget so far was mispriced. Neither certified harness reads an accessibility tree, so the observation factor cannot run on them | Rescoped to S1a (design A) with grafts: the OpenCUA anchor and sessions 12 h apart (design C); continuous dispatch and the GLMM homogeneity test (design B); the DR5 admission rule (C, both judges); a session-aware X, truncation handling and an A0-derived K-rule (judge 2); a serving probe v3 for S1b (B, both judges) | Pending blind discrimination, triad and reviewers |

**Design panel record** (Design and Judge phases, before this synthesis; the
repository was not edited in those phases):

| Design | Judge 1 total | Judge 2 total | Fatal flaws named |
|---|---:|---:|---|
| A: 4B and 9B certified pair, T = 15, 2 sessions x 2 reruns, 7.68 GPU-h | 30 | 31 | none |
| B: four sizes, L-shaped 2x2, 34.6 central / 76.2 high GPU-h main stage | 14 | 14 | H-OSW mispriced; accessibility-tree cells cannot run on the certified harnesses; harness confounded with the step cap (15 vs 50); over 8 GPU-h |
| C: 4B 2x2 with sequential sessions and an OpenCUA anchor | 25 | 25 | The accessibility-tree half cannot run on the certified harnesses; H-OSW mispriced, so S_max falls to 2 or less |

Both judges chose A and named grafts. The graft that adds the anchor cost
A one base task block (K from 36 to 32) to stay under 8 GPU-h with the
anchor and its smoke inside the caps.

**Score dips:** none yet (wave 0). The evidence bundle
(`evidence/2026-10-08-q2-stage1-rescoped/bundle.json`) holds:

- source snapshots;
- the query log;
- six doctor records;
- the analyses with their scripts (cost, simulations, task draw);
- the compute note;
- the deterministic doctor's output.

It holds no review receipt and no audit row. Those are appended to
`program/gauntlet/` after reviewers score.
