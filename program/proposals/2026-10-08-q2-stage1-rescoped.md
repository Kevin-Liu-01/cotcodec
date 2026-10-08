# Research Direction: Q2 Stage 1 Rescoped (rerun-noise floor and harness screen on the certified pair, then a gated scale ladder)

**Status:** draft; gauntlet wave 0, revised after three adversarial pre-freeze reviews of the S1a draft (2026-10-08; every blocking item fixed, preregistration section 22). This is the single-owner synthesis of the Q2 Stage 1 design panel (three designs, two judges). Blind closest-prior discrimination, the refute-first triad and the two provider-distinct reviews have not run. Stage S1a is at most 8 GPU-h by registered caps (at most 7.967 in every branch), so it does not itself need the gauntlet. It waits on the action-path acceptance (C1-C4, A1-A6 on one attempt and the ladder's N* of at least 16), the G0 engineering items, the A0 constants, Kevin's sign-offs on three items and a freeze. Stage S1b exceeds 8 GPU-h; under D47 it runs only on S1a's DR5 GO, and then needs this gauntlet and, under D24, Kevin's trust store or admission ruling. A score of 100 cannot be certified in this repository yet (D24).
**Owner:** Kevin Liu (program owner); synthesis written by a Claude agent acting as the gauntlet's single synthesis owner
**Source cutoff:** 2026-10-08
**Coverage limits:** Retrieval this wave: orx 0.2.2 only (10 discover queries: alphaXiv keyword and embedding, OpenAlex), plus full texts of 2610.01618, 2609.32459 and 2610.00917 through `orx paper --full`. The remaining closest priors are inherited from the 2026-10-06 dossier audit (102 URLs; 95 OK, 7 fixed) and were not re-read in full in this wave. Not used: the arXiv API, Semantic Scholar or the H100-host relay, so there was no forward or backward citation-graph expansion. Not searched: OpenReview, X, Reddit, blogs, patents and Chinese-language sources. The alphaXiv index may lag for papers posted on 2026-10-07 and 2026-10-08. Model-card benchmark numbers (Qwen3.5, OpenCUA) are first-party and were not replicated. The design panel's simulations were re-run in this wave by the synthesis owner with new code (bundle `analysis/`); the panel's scratch scripts are not in the bundle. After the pre-freeze review the operating characteristics were re-run with the registered estimators (`analysis/sim_s1a_v2.py`).
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
  - A base of 24 or 32 web-free confirm-split tasks (an A0-derived rule; 24
    when the anchor runs), with a cost-based fill rule whose extension blocks
    enter only a secondary analysis set.
  - Two serving sessions per size, at least 12 h apart, with two reruns
    each.
  - An OpenCUA-7B 15-step runtime anchor against its three public runs.
  - Registered caps of at most 7.967 GPU-h.
- **S1b.** Gated, over 8 GPU-h: the harness scale ladder (27B-FP8 and
  35B-A3B-FP8 added) after a replay-only serving probe v3, only if S1a's DR5
  says GO (D47). After NO-GO or INCONCLUSIVE no S1b runs; an observation-factor
  study on a certified accessibility-tree variant, or more sessions at 4B and
  9B, would each be a new proposal with its own gauntlet.

**Claim scope:** `systems-pipeline`. This is a measurement-instrument
calibration; nothing here is an architecture claim.

What the proposal claims:

1. The design answers the noise-floor and harness-screen part of Q2 inside 8
   GPU-h, for the two realized serving sessions per size, on the harnesses
   that will actually run, priced by the measured cost card. Every exit is a
   reportable result.
2. S1a turns the question file's underived "paired MDE about 7-8 pp" kill
   line into a computable admission rule for the scale ladder (DR5, with the
   ladder's detectable share frozen before any data). That rule says whether
   the shrinkage question is answerable at an affordable size before any
   ladder GPU-hour is spent. Replacing the kill line is Kevin's decision.

What it does not claim, stated before the evidence:

1. That S1a answers the scale question or the observation question. It does
   not (Claim boundary: preregistration section 2).
2. That the harness contrast is broad. The certified pair shares its layout,
   template lineage and thinking default, so a null is the likely result
   (prediction P3).
3. That the anchor certifies the runtime. It catches only gross defects (DR-A
   operating characteristics).
4. That the noise floor generalises to the population of serving sessions.
   With two sessions per size, every estimand is conditional on the sessions
   that ran.

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

The rows above are the card's. With VM setup (central 90 s, high 180 s) and
the 80 s of OSWorld settle that S1a applies to both harnesses inside the slot
(pre-freeze review; `cost_s1a.json` key `s1a_v2`), the S1a prices are 0.009020
central and 0.011274 high at V = 20 (the engine binds) and 0.010948 and
0.012901 at V = 16.

**E4. Thinking pass-back bound.** The card models every history entry at 300
tokens. Both harnesses pass full replies back, and the template keeps the
reasoning (the `serving-throughput-probe-v2` registration, section 4 item 7,
states this caveat). With 2,048-token history entries:

- the mean modelled prompt over 15 steps is 32,272 tokens;
- the largest context including output is 62,950 tokens, below 131,072;
- the open-loop ratio is unchanged (6.827), so the central price stands;
- scaling every step latency by the prompt ratio (an upper bound) raises the
  V = 16 high price to 0.01331 GPU-h; at V = 20, the A1 concurrency at
  N* >= 24, the open-loop bound still binds (0.011274). A0a measures the real
  cost, and the K-rule uses the larger of the card's high price and 1.25 times
  A0a's (preregistration section 6.2).

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
| C03 | Per-episode prices 0.009020 / 0.011512 (card); S1a slot prices 0.009020 / 0.011274 at V = 20 | E3 | RECOMPUTED |
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
| C16 | Power figures | `analysis/sim_s1a_v2.json` (registered estimators; the draft's `sim_s1a.json` and `sim_signflip.json` kept for the record) | SIMULATED (seeded) |

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
| Harness variance share of a certified harness pair (mean squared per-task harness effect over the between-session floor), with a session-aware estimator and a sign-flip test valid under session structure | 2610.00651; 2610.01618; 2609.40284 | Variance decomposition of agent outcomes | Harness implementations certified identical at the action layer (within the certified keysym set), so the share is about prompting and layout, not input bugs; estimator robust to session-specific harness effects; stated for the realized sessions | Medium |
| Admission rule tying the S1a share to the ladder's detectable shrinkage (DR5) | none found | | A pre-specified go/no-go for a scale study, with the ladder's detectable share frozen on the estimator's own scale | Medium-low (procedure, not a finding) |
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
  are treated. Within the certified action set (action-path v2: the 33
  certified keysyms and the certified typing classes), a harness effect cannot
  come from dropped or wrong input events. Key actions naming other keysyms
  are uncertified; S1a counts them per episode and harness and reports δ by
  exposure stratum.

**Predictions** (preregistered in S1a, preregistration section 12, each with its falsifier and the interval or rule that reads it; every reading is for the realized sessions):

| | Prediction | Basis | Falsified if |
|---|---|---|---|
| P1 | Session excess is positive: D_b − D_w > 0 | E5 | The one-sided 95% upper bound of pooled D_b − D_w (task-cluster bootstrap, seed 42) is below 1 pp. The within-session floor would then suffice for these sessions, and Holo3's shift would not generalise to this stack |
| P2 | The pooled between-session floor D_b lies between 6% and 20% | X5 12-14%; X7 13%; E8 7.5-9.7% | Its 95% interval lies wholly outside [6%, 20%] |
| P3 | The pair is not "Present" under DR2 | Shared layout and thinking default (E2) | DR2 (Holm over the δ test and the X sign-flip test, family-wise 5%) classifies the pair as Present |
| P4 | 4B is not at the floor: at least 10% pooled success under at least one harness | X1 35.6% first-party; T = 15 lowers it | DR1 fires |
| P5 | Realized GPU-h per episode is at most the card's high price at its V | Continuous dispatch, early terminations | Some A1 job exceeds it (DR4: 0.011274 at V = 20, 0.012901 at V = 16) |

**Kill criteria** (registered):

- **ANCHOR-FAIL.** OpenCUA-7B lands more than 2 paired SE outside the public
  runs' range on the anchor's reading set. A1 does not start, and S1a ends.
- **DR0 (A1 jobs).** Infrastructure loss above 5% of a cell's first-attempt
  episodes (agent-caused `IRError`s and metric exceptions excluded), or an
  incomplete base. Stop, debug without reading outcomes, and take a new id.
- **Pre-freeze.** If K_base < 24 at the A0-measured price, truncation
  exceeds 20% of steps, or A0a's step p95 exceeds twice the action-path A1
  p95, the draft is rejected and goes back to review. If N* < 16, S1a does
  not start.

## Cheapest Decisive Pilot

**The pilot is A0a** (pre-freeze, development split only, cap 25 minutes,
0.417 GPU-h): Qwen3.5-9B, V/4 dev tasks x 2 harnesses x 2 reruns = V
episodes in one wave at A1's V (20 at N* >= 24), through the real engine,
bridge, VMs, executor and checker. It is decisive for S1a's feasibility on
four counts:

1. **Cost.** Its slot occupancy (dispatch to teardown, boot and setup
   included) gives c_A0a; c_proj = max(the card's high price at A1's V,
   1.25 x c_A0a). Under the registered rule, K_base = min(32, 8 x floor(((T_A1
   − 3 − L_A0a)/60) / (4 x 1.05 x c_proj) / 8)), with the USR1 lead, the
   measured launch L_A0a and a 5% re-queue allowance. If that falls below 24,
   S1a as drafted is rejected. It is also the re-probe the serving probe's
   thinking pass-back rule requires.
2. **Truncation.** The truncation rate at 2,048 tokens decides whether greedy
   thinking under this budget works at all (gate: 20% of steps).
3. **Concurrency.** Its step p95 must stay within twice the action-path A1
   step p95, since N* was qualified with no engine running.
4. **Plumbing.** It is the first end-to-end run of the certified pair. Any
   defect is fixed before the freeze, and a fix repeats the A0 job.

**A0b** (cap 26 minutes) is the same for the OpenCUA anchor: 4 dev episodes.
Its launch time and longest slot set the anchor's size n; if n < 58 the
anchor is not run.

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
| Within-session harness contrast | Both harness clients interleave on one engine in random order in every block. Harness is never confounded with session, engine state or host load; a harness x session effect common to a session's tasks is not separable from δ, so δ is stated for the realized sessions |
| Between-session floor | Two sessions per size, each a fresh engine and VM pool, at least 12 h apart. Sessions, not just reruns, carry the floor (E5) |
| External runtime anchor (D11) | OpenCUA-7B on the upstream action path against three public runs on the same tasks. Read before A1 |
| Action path | Only certified harness and executor layers (action-path v2 C1-C4 and A1-A6 on one attempt), with the guard's warm-up once per boot. Uncertified keysym exposure is counted per episode. The anchor's upstream path is deliberate and disclosed |
| Infrastructure | Per-episode loss definition (VM, setup, guest-server restart under D30/D33, engine error or a non-context H-GA fallback, executor device, transport, runner), one replacement, DR0 at 5%. Agent-caused `IRError`s and checker metric exceptions are not losses: the first follows each harness's unparseable-reply rule, the second scores 0 (missing in a sensitivity) |
| Engine identity | Engine flags identical to the cost card. Prompt token-id digests are logged, so any reread or replay can check prompt identity |
| Host load | Quiet-host rule, sizes one after the other, co-running S1a CPUs at most 200 of 208, host snapshots per block |
| Checkers | Raw verdicts primary. Secondary: z-order-corrected `compare_pptx_files` validated on the 29 confirmed mutants. K1 gold failures excluded. Seven tasks flagged (P1 flips, confirmed false positives, contradicted labels) for a sensitivity |
| Truncation | Per-cell truncation rate; a size above 20% has its δ labelled truncation-confounded; δ without truncated episodes is a mediator description only |
| Estimator robustness | Sign-flip tests primary for X and the session shift (valid under a session excess); label permutation and Bernoulli forms as sensitivities; GLMM with harness x session terms and a homogeneity LR test |

**Not controlled, and why:**

- Step budget, thinking budget, sampling and settle are held equal (T = 15,
  2,048 tokens, greedy, OSWorld's 60 s and 20 s) instead of each harness's
  native setting. The harness factor is therefore "prompt, layout and action
  handling under a matched budget", as in design C. Greedy decoding is imposed
  on H-GA, whose agent samples at temperature 1.0 by default.

**Baselines.** There is no model baseline: S1a compares harnesses within
models. The anchor is the external baseline for the runtime.

## Evaluation, Statistics, and Leakage Checks

**Estimands** (preregistration section 9), all on the base fixed at the
freeze and all **conditional on the realized sessions** (two per size; the
bootstrap resamples tasks, never sessions):

- D_b, D_w and D_b − D_w per size and pooled; D_b on same-block and
  cross-block pairs;
- δ pooled and per size, and per size and session (a heterogeneity check);
- X = mean_t d_t1 d_t2, the mean squared per-task harness effect (δ² plus the
  task-by-harness variance), and X_c, its task-specific part;
- π = (X⁺/4) / (X⁺/4 + D_b/2) with X⁺ = max(X, 0) and 0/0 = 0, and π_small;
- the scale screens δ_4B − δ_9B and π_4B − π_9B;
- the session shift, and the share of the session excess common to both
  harnesses (reported for S1b);
- the anchor contrasts;
- the realized cost card, uncertified action-path exposure, first-divergence
  and checker-noise counts.

**Inference** (registered code: `harness/q2_stage1/estimators.py`,
`rules.py`, `analysis.py`, tested on CPU):

- Task-cluster percentile bootstrap, 10,000 resamples, seed 42.
- δ: paired t, two-sided 5%, with the 90% t interval.
- X: **sign-flip test** on the per-task products, one-sided, 10,000 flips.
  Flipping d_ts swaps whole harness cells, so it holds its size under any
  session structure. A rejection supports only "a harness effect is present".
  The within-task-session label permutation is a sensitivity.
- Session shift: two-sided sign-flip test over tasks, per size.
- DR2: Holm over the δ test and the X test at family-wise 5%.
- GLMM secondary, with (1|harness:session) and (1|task:harness:session).

**Operating characteristics** (`analysis/sim_s1a_v2.py`, seeded, 2,000 data
sets per point, every estimator and test imported from the registered
module). The review showed that the draft's permutation tests lose their size
when there is the session excess P1 predicts; the new primary tests do not
(K = 24 / 32, literature scenario):

| Session noise (D_b − D_w at K = 32, 4B / 9B) | δ paired t | X sign flip | X label permutation (draft) | Session sign flip | Session-label permutation (draft) |
|---|---|---|---|---|---|
| base (0.2 / 0.3 pp) | 0.055 / 0.058 | 0.013 / 0.018 | 0.034 / 0.023 | ≤ 0.039 | ≤ 0.048 |
| σ_f 1.5 (3.8 / 5.9 pp) | 0.051 / 0.048 | 0.021 / 0.025 | 0.073 / 0.091 | ≤ 0.035 | ≤ 0.090 |
| σ_f 3.0 (11.8 / 15.6 pp) | 0.054 / 0.047 | 0.025 / 0.042 | 0.130 / 0.157 | ≤ 0.047 | ≤ 0.127 |
| σ_e 1.5 (3.8 / 5.5 pp) | 0.052 / 0.052 | 0.006 / 0.011 | 0.016 / 0.023 | ≤ 0.043 | ≤ 0.140 |
| σ_e 3.0 (11.4 / 15.5 pp) | 0.052 / 0.044 | 0.002 / 0.006 | 0.012 / 0.027 | ≤ 0.042 | ≤ 0.224 |

The full table (12 noise settings, including a harness x session effect
common to a session's tasks) is in the preregistration, section 10.2.

| Quantity (literature, base noise) | K = 24 | K = 32 | K = 64 | K = 116 |
|---|---:|---:|---:|---:|
| δ pooled MDE (80%, two-sided 5%) | 8.8 pp | 7.2 pp | 5.1 pp | 3.6 pp |
| δ per size (4B / 9B) | > 15 / 13.6 pp | 10.1 / 11.4 pp | 6.5 / 7.9 pp | 4.7 / 5.8 pp |
| δ_4B − δ_9B screen MDE | > 20 pp | 16.8 pp | | |
| D_b pooled 95% half-width | ±6.5 pp | ±5.7 pp | ±3.9 pp | ±2.9 pp |
| D_b − D_w 95% half-width | ±4.0 pp | ±3.4 pp | ±2.5 pp | ±1.8 pp |
| X sign flip, power at RMS per-task effect 15 / 22 pp | 0.14 / 0.43 | 0.23 / 0.56 | | |
| π_small at the null: mean; SD | 0.029; 0.034 | 0.027; 0.030 | 0.019; 0.020 | 0.014; 0.015 |
| Holo3-sized session shift (3.7 pp), power per size | 0.05-0.10 | 0.08-0.14 | | |

**Other scenarios** (pooled δ MDE at K = 24 / 32): high noise 9.6 / 8.2 pp,
low base 8.0 / 6.5 pp, OpenCUA-calibrated 7.4 / 5.9 pp. With a session excess
of about 4-6 pp: 8.5-10.6 pp at K = 24 and 7.1-9.1 pp at K = 32.

**Ladder planning value for DR5, now frozen.** M is the smallest share of the
4B and 9B rungs whose full shrinkage a harness-only ladder (60 tasks x 4
sessions x 1 rerun per rung, 4B, 9B, 27B and 35B-A3B) detects with 80% power,
one-sided 5% against the simulated null critical value, on the scale the
registered estimator targets (D_b including session variance), with the larger
rungs pinned at 40% (literature) or 35% (OpenCUA-calibrated) success. Over two
scenarios and three session-noise settings it is 0.06-0.13 for π_small and
0.08-0.18 for π_9B (the DR1 case). The registration freezes the largest
values, **M = 0.13** and **0.18**, so a GO means the ladder is powered in every
planning cell. The draft's 0.21 and 0.27 compared a single rung with a normal
approximation at the alternative's spread and put the truth in units that left
out session variance; the review showed that this inflated NO-GO.

DR5 on S1a's side (literature, 300 data sets, bootstrap bounds):

| π° of the small rungs | K = 24: GO / NO-GO | K = 32: GO / NO-GO |
|---:|---|---|
| 0 | 0.00 / 0.78 | 0.00 / 0.86 |
| 0.07 | 0.01 / 0.36 | 0.00 / 0.34 |
| 0.14 | 0.05 / 0.09 | 0.08 / 0.09 |
| 0.21 | 0.29 / 0.01 | 0.29 / 0.02 |
| 0.27 | 0.50 / 0.00 | 0.57 / 0.00 |
| 0.33 | 0.72 / 0.00 | 0.86 / 0.00 |

NO-GO is the expected exit for a near-equivalent pair; GO needs a share well
above M. Under D47 only GO leads to S1b.

**Anchor operating characteristics** (OpenCUA-calibrated, 4,000 data sets;
false kill about 1% at every size, also with a per-run logit shift of SD 0.15):

| Runtime deficit | n = 58 | n = 64 | n = 96 | n = 116 |
|---|---:|---:|---:|---:|
| 4.2 pp | 0.08 | 0.09 | 0.16 | 0.19 |
| 6.1 pp | 0.20 | 0.22 | 0.38 | 0.48 |
| 7.9 pp | 0.36 | 0.41 | 0.63 | 0.74 |

**Leakage checks:**

- No model episode and no checker run on agent state touches a confirm task
  before the freeze; G0's setup-only check is the sole contact; A0 uses dev
  tasks.
- The base is fixed at the freeze and is the primary set for every estimand
  and rule. The fill rule reads cost, which follows episode lengths and so
  outcomes; its extension blocks enter only a secondary set.
- The K-rule reads A0's cost only, and can only lower K.
- The anchor's size is set from A0b's dev episodes; its reading is the longest
  dispatch-order prefix whose episodes all completed, so episodes cut at the
  cap (more often long failures) cannot bias it.
- The public anchor results are external and fixed (dataset revision
  `5473c39e`).
- Mutation-study labels do not depend on agent outcomes.
- The task draw and orders are seeded and written by a committed, tested
  renderer before the freeze.

**Red flags checked:**

- No outcome-dependent stopping of the primary analysis. The fill rule is
  sequential and outcome-correlated, and is confined to the secondary set.
- No post-hoc metric choice: raw verdicts are primary and the alternatives
  are listed.
- A null δ is read through the registered equivalence class, not as "no
  effect".
- Agent-caused exceptions are not infrastructure losses, so DR0 cannot stop
  the stage on the agents' behaviour and no outcome-dependent episode is
  dropped.

## Compute and Reproducibility

**Ceiling.** S1a registered caps: gpu_hours: 8. At most 478 minutes of one
H100 (7.967 GPU-h) in every branch, counted under D22; the A1 cap is set by a
remainder rule that shares out 478 minutes after every other cap.

| Job | Cap | Central GPU-h | High GPU-h |
|---|---:|---:|---:|
| O1 overlay build (pre-freeze) | 3 min | 0.012 | 0.050 |
| A0a 9B dev pilot, V episodes in one wave at A1's V | 25 min | 0.225 | 0.306 |
| A0b OpenCUA dev smoke, 4 episodes | 26 min | 0.238 | 0.319 |
| O2 overlay build (post-freeze), plus one pre-funded retry | 3 + 3 min | 0.012 | 0.100 |
| ANC anchor, n tasks (96 at N* >= 32), only if n >= 58 | 52 min | 0.615 | 0.758 |
| A1, 4 jobs (9B, 4B) x (S1, S2) | 4 x 91 min | 3.664 (K = 24) | 4.946 (K = 24) |
| **Total, anchor runs** | 476 min | **4.766** | **6.479** |

| Branch | A1 cap | Total | K_base at the card's high price |
|---|---:|---:|---:|
| Anchor runs | 91 min | 476 min (7.933 GPU-h) | 24 |
| Anchor unavailable after A0b | 104 min | 476 min | 32 |
| Anchor unavailable before A0b | 111 min | 478 min (7.967 GPU-h) | 32 |

All figures are derived from the cost card with the frozen budget module
(`analysis/cost_s1a.py`, key `s1a_v2`). The pre-freeze review corrected four
things the draft left out:

- **The slot.** VM setup (central 90 s, high 180 s) and OSWorld's 60 s settle
  after reset and 20 s before evaluation, which S1a now applies to both
  harnesses, sit in every slot. At V = 20 the engine still binds: central
  0.009020 and high 0.011274 GPU-h per episode. At V = 16: 0.010948 and
  0.012901.
- **The K-rule.** It counts the 3-minute USR1 lead, A0a's measured launch time
  and a 5% re-queue allowance. A 100-minute job at the draft's V = 16 high
  price holds 24 base tasks, not 32.
- **The anchor.** The pinned OpenCUA runner sleeps 60 s after reset, 20 s
  before evaluation and 5 s after each step: the slot is 11.3 minutes central
  and 13.2 high. The draft's 32-minute ANC cap could not reach 58 tasks below
  V = 32; ANC now gets 52 minutes and its size is set from A0b (64 or 96 tasks
  at N* >= 32, 48 or 72 at N* = 24, no anchor at N* = 16).
- **CPUs.** The host has 208 CPUs; a GPU job takes 32 and a VM job 4V plus
  half a CPU per runner. Two sizes at once (244) and ANC at V = 40 (212) do
  not fit, so the sizes run one after the other at V = 20 (122 CPUs), ANC at
  V = min(32, N*) (176). Each GPU job waits for its VM job to start
  (`--dependency=after:`, the docker submitter's new `start_after_job_id`).

The fill rule turns slack into extension tasks inside the caps (secondary
analysis set only). Expected spend is 5-7.5 GPU-h.

**VM time** (CPU-only lane, D12):

- A1 at K = 24, V = 20: 69 VM-h central, 87 high, 135 reservation bound; at
  K = 32 (anchor unavailable): 92, 115, 161.
- A0a: 4 VM-h; A0b: 1; ANC: at most 33.
- The action-path suite (98.4 VM-h) comes first.
- Wall-clock: about 3.5 h per session (two A1 jobs in turn), plus the 12-hour
  gap.

**Stage S1b projection** (card rule; unmeasured multipliers until probe v3;
runs only on DR5's GO):

- **Harness ladder.** 35B-A3B-FP8 and 27B-FP8 at 60 tasks x 2 harnesses x 4
  sessions, plus two more sessions of 4B and 9B on 60 tasks: 31.9 GPU-h
  central, 41.3 high at the draft's prices. 27B alone is 19.5 / 24.9 at the
  x4.5 rule.
- **Observation study** (not S1b under D47; a separate proposal; one rung, 60
  tasks x 2 harnesses x 2 observations x 4 sessions): 9.1 central, 13.0 high.
  It needs a certified accessibility-tree harness variant and A7.
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
  - Runner: GPU-less, `sha256:ac2b5815bcc2ed193116aa2d4bdee773b5a457c545453a6c91956768634a6002`,
    locked in `infra/q2-vm-runner/image-lock.json`.
- **Engines.** S1a: the card's argv (`harness/q2_stage1/plan.py`
  `CARD_ENGINE_FLAGS`, equal to job 466's). Anchor: the same with
  `--max-model-len 32768`, at most 4 images and `--trust-remote-code`
  (OpenCUA-7B derives 128,000 and vLLM refuses 131,072).
- **Launch.**
  - Each VM job goes first, through `scripts/submit_vm_campaign.py` on the
    CPU-only lane (`infra/slurm/host-single-node/vm-campaign.sbatch`), with a
    limit of the GPU cap plus 10 minutes.
  - Its GPU job goes through `scripts/submit_docker_research_job.py` (dry-run,
    test-only, submit) with the vllm container profile and
    `start_after_job_id` set to the VM job. The A1 form (the 9B session-1 job
    when the anchor runs) is
    `sbatch --parsable --partition=research --nodes=1 --ntasks=1 --job-name=q2s1a-a1-9b-s1 --gres=gpu:h100:1 --cpus-per-task=32 --mem=160G --time=01:31:00 --signal=B:USR1@180 --no-requeue ... --dependency=after:VMJOBID infra/slurm/host-single-node/docker-research.sbatch`.
  - The plan file (draw, orders, constants, jobs) is written by
    `scripts/render_q2_stage1_plan.py`.
  - Each A0 or A1 GPU job will be an orx `slurm-manifest` node run with the
    project's single fixed command.
- **Seeds:** seeds: [42, 43, 44].
  - 42: task draw, extension order, dev and anchor orders, size order,
    engine seed, bootstrap and sign flips.
  - 43 and 44: the two sessions' episode orders.
  - Decoding is greedy.
- **Checkpoints and preemption.** There is no training state. The record
  files are append-only. On USR1 (180 s before the limit) the driver
  dispatches nothing new, and in-flight episodes are recorded as
  cap-truncated. A job is never rerun to improve an outcome.
- **Artifacts.**
  - On the host run root (never `program/evidence/`): per-step token logs,
    prompt-id digests, IR actions, raw replies, screenshots, final-state
    captures and host snapshots.
  - In `program/evidence/`: summaries, receipts, counts, hashes and analyses
    with SHA-256 indexes; GPU UUIDs hashed.
- **Cost ceiling.** The caps above. An amendment that would raise them is
  not made; the design would go to the gauntlet instead.

**Known mismatches with the deterministic doctor:**

- The doctor's real-model-loop check reads `harness/runner.py`, which does
  not exist. S1a's analysis, plan and decision rules now exist and are tested
  (`harness/q2_stage1/`); its episode driver is still a G0 item.
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
  (preregistration section 18, item 22). Before any anchor GPU job, a CPU-only
  container loads its config and tokenizer with `trust_remote_code` and checks
  the anchor's engine arguments (G0 item 9).

**Isolation:**

- No new Docker network (D13). The engine binds 127.0.0.1, and runners
  reach it through a bind-mounted Unix-domain socket.
- VMs run with `--network none`.
- No host reconfiguration, no sudo, and `~/cotcodec` is untouched.

**Data rights:**

- OSWorld task configs: Apache-2.0. The file cache's documents contain
  third-party content; final-state captures, screenshots and raw replies stay
  on the host run root (or the private archive), and only metadata, verdicts,
  counts and hashes are released (preregistration section 16).
- Qwen3.5: Apache-2.0. OpenCUA-7B: MIT. Gym-anything: MIT. Public
  trajectories: MIT; only per-task `result.txt` members are read.
- The OpenCUA-7B weight download (about 16 GB) is a public research download
  under D1, recorded with revision and SHA-256, made in a GPU-less fetch lane
  (the existing fetch lanes request a GPU, whose time D22 would have to count).
- Snapshots in this bundle keep metadata extracts and hashes, not page
  bodies.

**Public repository.** No host IP, secret or private dataset is committed.
Host run paths already public in earlier evidence are reused. GPU UUIDs are
hashed before NVML samples are committed.

**Monitorability.**

- Every step logs tokens, IR and prompt-id digests, `IRError`s and context
  fallbacks.
- Every episode logs restarts, checker inputs, metric exceptions and
  uncertified action-path exposure.
- Infrastructure losses and cap truncations are listed, never dropped.
- Every deviation is reported.

**Red lines:** none crossed.

**Integrity gate (seven AI-research failure modes; the list follows the
gauntlet rule, the ARS file was not opened):**

1. **Implementation bug passing self-review.** Possible in the new episode
   driver and bridge. Mitigations: CPU fake-engine tests, the A0 pilot, and
   the action-path certification of everything below the IR. The analysis,
   decision rules and plan renderer exist and are tested on CPU before the
   freeze; three adversarial reviews of the draft found 21 blocking items
   (19 distinct), all fixed (preregistration section 22).
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
   by simulation with the registered code, including session excesses of
   0-16 pp that break the draft's permutation tests and a scenario that breaks
   the Bernoulli correction.
7. **Frame-lock.** Three designs were compared by two judges. The losing
   designs' best parts were grafted, and the observation factor is kept as
   the follow-up a NO-GO points to.

## Negative-Result Value

Every S1a exit is publishable within Q2:

- **ANCHOR-FAIL.** Our runtime does not reproduce public OpenCUA runs. That
  is a debugging result, and it saves every later Stage 1 GPU-hour from a
  broken stack.
- **Near-equivalent pair (P3 holds, DR5 NO-GO).** "Two upstream Qwen3.5
  harnesses whose action paths are certified identical within a 33-keysym set
  do not differ beyond X pp on desktop tasks in these sessions". This
  redirects the harness question to the observation factor and is a useful
  counterpoint to rank-reversal results (2610.00917).
- **D_b − D_w at or near 0 (P1 fails).** The Holo3 session shift does not
  appear in these two controlled self-hosted sessions per size. Within-session
  reruns might then suffice for this configuration, which would halve later
  costs (two sessions cannot rule out a rarer session shift).
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
| Design | PASS | Synthesis owner's self-check, not an independent review. Design-panel judges scored the winning design 30 and 31 with no fatal flaw. Three adversarial pre-freeze reviews of the S1a draft found 21 blocking items (19 distinct); all are fixed (preregistration section 22): sign-flip tests replace the permutation tests that lose their size under a session excess, M is frozen on the estimator's own scale, estimands are conditional on the realized sessions, agent-caused events are kept out of infrastructure loss, and the base is the primary set. Operating characteristics re-run with the registered code (`analysis/sim_s1a_v2.json`). Decision rules DR0-DR5 and DR-A fixed and coded (`harness/q2_stage1/rules.py`) before any confirm episode | Refute-first identification lens in the gauntlet; a fresh pre-freeze audit of the revised draft |
| Compute | FAIL | Caps of at most 7.967 GPU-h in every branch (remainder rule), derived from the card with the frozen budget module, with setup, settle, USR1 lead, launch and re-queues now priced and CPU feasibility checked against the host's 208 CPUs; the plan renderer, analysis and decision rules exist and are tested on CPU; but no S1a image, manifest, dry-run, container smoke or orx node exists; the episode driver and engine bridge are not built (G0); action-path acceptance and N* are pending | Build G0; run A0a as an orx slurm-manifest node with dry-run, test-only and provenance attested |
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
| Mechanism and falsifiability | 0 | 0 | Not yet reviewed. Synthesis note: P1-P5 registered in S1a, each with a falsifier; ANCHOR-FAIL and DR0 kill criteria |
| Controls and causal identification | 0 | 0 | Not yet reviewed. Synthesis note: within-session interleaving; between-session floor; matched budgets make the harness factor narrow |
| Evaluation and statistics | 0 | 0 | Not yet reviewed. Synthesis note: δ MDE 8.8 / 7.2 pp at K = 24 / 32; sign-flip X power 0.14-0.23 at RMS 15 pp; session shift weakly powered; M frozen |
| Feasibility and information per GPU-hour | 0 | 0 | Not yet reviewed. Synthesis note: at most 7.967 GPU-h caps; K = 24 when the anchor runs; gated on the action-path acceptance and N* >= 16 |
| Reproducibility and artifact contract | 0 | 0 | Not yet reviewed. Synthesis note: pinned images, seeds, task draw; no S1a image or orx node yet |
| Safety, data rights, and monitorability | 0 | 0 | Not yet reviewed. Synthesis note: OpenCUA remote code needs a decision |
| Independent adversarial review quality | 0 | 0 | No review exists; no trust store (D24) |
| **Total** | **0** | **0** | Unreviewed. Caps 74, 79 and 89 apply |

## Iteration Log

| Wave | Score | Highest-impact defect | Change | Result |
|---:|---:|---|---|---|
| 0 | 0 (unreviewed) | The inherited design priced H-OSW as the card's cheap window-4, non-thinking profile. The pinned source shows it folds and thinks, as H-GA does, so every Stage 1 budget so far was mispriced. Neither certified harness reads an accessibility tree, so the observation factor cannot run on them | Rescoped to S1a (design A) with grafts: the OpenCUA anchor and sessions 12 h apart (design C); continuous dispatch and the GLMM homogeneity test (design B); the DR5 admission rule (C, both judges); a session-aware X, truncation handling and an A0-derived K-rule (judge 2); a serving probe v3 for S1b (B, both judges) | Pending blind discrimination, triad and reviewers |
| 0 (rev) | 0 (unreviewed by the gauntlet) | Three pre-freeze reviews of the S1a draft: the X and session permutation tests lose their size under the session excess P1 predicts; M was in other units than π_small; the concurrency plan needed more CPUs than the host has; the anchor could not start (max_model_len) or finish (cap); agent exceptions counted as infrastructure; the freeze guard accepted unfilled slots | Sign-flip tests primary; M frozen on π°; estimands conditional on sessions; sizes in turn at V = 20 with GPU jobs after their VM jobs; anchor argv, CPU validation and an A0b-sized anchor; agent events kept out of DR0; base primary; unfilled slots that the freeze guard refuses; P1-P5 registered; analysis, rules and plan renderer built and tested | 21 blocking items (19 distinct) fixed (preregistration section 22); a fresh pre-freeze audit is next |

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
