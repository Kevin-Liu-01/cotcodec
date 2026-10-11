# Research Direction: E3 Stage-0 headroom probe, v2: do the strongest learned byte boundaries already fall at alignment-consistent places across EN-ZH translations? (backfill E3, legacy direction 18)

**Status:** repaired under program decision D68 for a fresh gauntlet run, after gauntlet wave 1 (score 52, the lower of 52 and 57; all three refuters refuted; honest exit on the query budget, `program/gauntlet/2026-10-10-e3-byte-boundary-headroom.jsonl`, row hash `13d97526...`); repair by the single owner on 2026-10-10 on the Mac CPU (no GPU, no host job); the draft registration is now `program/preregistrations/e3-byte-boundary-headroom-v2.md` (new experiment id; v1 superseded and left unedited), a DRAFT, not frozen or admitted; the blind critic, the refute-first triad and the two reviewers of this run have not run; no executable pilot exists for this probe; a score of 100 cannot be certified in this repository (D24)
**Owner:** Kevin Liu (program owner); wave-1 synthesis and the D68 repair (instrument, identification design, error model, simulations, draft registration) written by a Claude agent acting as the gauntlet's single owner
**Source cutoff:** 2026-10-10
**Coverage limits:** wave 1's coverage (orx 0.2.2 alphaXiv keyword and embedding search and OpenAlex; 122 recounted orx discover calls by the cells, 15 by the refuters; 11 OpenReview API searches; full texts by targeted section; see wave 1's header and record) plus this run's repair: 20 counted orx discover queries (keyword, embedding and OpenAlex; listed in `evidence/2026-10-10-e3-byte-boundary-headroom/query-log-run2.json` with raw-output SHA-256), 5 uncounted full-text or report reads (`orx paper`), OpenAlex metadata lookups for seven classical works, and read-only GitHub, Hugging Face and raw-file reads of the pinned upstream code and model cards; the TsinghuaAligner site returned HTTP 502, so the only Chinese-English gold set used by the published aligner evaluations could not be checked; OpenAlex returns no forward-citation lists through orx, so forward citations of 2502.06468 and 2601.22805 were approximated by title and embedding searches; not searched: Semantic Scholar and the arXiv API (unreachable from the Mac; the host is reserved for the reviewer lane), patents, X, Reddit, Hacker News, Chinese-language venues; no FLORES+ text, checkpoint, aligner or parser was downloaded or run, so every statement about real data is metadata-based and every number about the instrument is from synthetic simulation.
**Budgets:** queries=80; wall_minutes=600; tokens=8000000; dollars=150; waves=1; gpu_hours=0.3
**Novelty verdict:** NO_DIRECT_PRIOR_FOUND
**Safety verdict:** PASS
**Evidence bundle:** evidence/2026-10-10-e3-byte-boundary-headroom/bundle.json

The budgets are this fresh run's (D68), cumulative over the repair, the triad,
the reviewers and the recorder; at least 30 of the 80 queries are reserved for
the three refuters (six orx discover queries each at minimum). The repair used
20, leaving 60. The gauntlet's GPU budget (0.3 GPU-h)
is for the open-weight reviewer's lane job only; the probe's own registered caps
(0.9 GPU-h under D22) run only after a freeze. The novelty verdict field uses
the doctor's vocabulary; the merged verdict is NARROWED, and this proposal claims
no method novelty (Novelty Ledger).

## Changes after wave 1

Wave 1 (proposal sha256 `782cbf31...`, registration v1 sha256 `30f1fe76...`)
scored 52: reviewer 1 (claude-opus-5-5) 52, reviewer 2 (qwen3.6-35b-a3b, Slurm
1085) 57. Blind discrimination against 2502.06468 passed by the rule's letter
(the critic judged the prior the stronger contribution, not strictly dominant).
All three refuters refuted. The largest defect was identification: at the
registered operating point (EN-ZH stage 1, Chinese rate-calibrated to the
English count) the Chinese side covers about 85-100% of its character gaps, the
floor shifted only that side and collapsed, and S read Chinese density and the
English word-end miss rate; a 3% English miss moved S by about 0.2 against a
0.03 gap between the decision lines. Second, feasibility: at the published
Chinese-English error rates of the registered aligners (AER about 0.18-0.27, and
CTFAlign is SimAlign with another encoder) NO_HEADROOM never fired, and the
pinned stack could not run (fp32 against hnet's bf16 attention asserts;
mamba_ssm importing names transformers 5.15 removed). Third, novelty: kappa_M
and the SMT bilingual-segmentation lineage were uncited. D68 ordered one CPU
repair by a single owner and a fresh run; D60's stop line applies (below 60, or
the same largest defect, ends E3). This section is the repair. Each row names
who found the defect, what changed, where it lives in registration v2, and the
CPU check that sizes it (bundle `compute/repair-run2/`: E = the registered
estimator as code, `e3_estimator_v2.py`; S1v2 = simulations,
`instrument_sim_v2.py`; S2v2 = cost, `cost_model_v2.py`).

| # | Wave-1 defect (named by) | Repair | Registration v2 | Evidence |
|---:|---|---|---|---|
| 1 | Density collapse at the operating point: dense Chinese stage-1 side, side-b-only circular-shift floor, S driven by Chinese density and English word-end misses (identification refuter; reviewer 1's largest defect, reproduced; reviewer 2) | The decision moves to one common per-sentence budget k of at most half of either side's word gaps (and at most the number of disjoint allowed pairs), where each side's k strongest word gaps are selected by the model's score. Neither side can saturate; the ceiling is exactly 1 | Secs. 4, 7 | S1v2 ident (seeds 42-44): a binary Chinese side at density 0.54, 0.85, 0.92 and 0.99 with English word-end misses of 0, 3% and 10% moves S by at most 0.02 within a density; graded scores read 0.38-0.41 at every density; the selected density never exceeds 0.50 |
| 2 | The floor collapsed on the dense side (identification refuter, reviewer 1) | Two-sided floor: expected hits of k word gaps drawn at random on each side independently, so it conditions on the budget and on both sides' word structure; pooled 1 - floor/k is 0.68 on the consensus target, far from collapse | Sec. 7 | S1v2 gates: random selections read S between -0.004 and 0.010 under every target (seeds 42-44) |
| 3 | Line M scored at its own budget and saturated trivially; the statistic rewarded word-end detection (identification refuter, reviewer 1) | Selection is confined to word gaps, which removes word-end detection: a system that knows only where words end reads S 0.00 (S1v2: -0.010 to 0.004). Line M becomes a monolingual syntactic reference (dependency parses) selected the same way at the treatment's budget | Secs. 4, 10 | S1v2 linem: the synthetic syntactic ranker reads S_truth 0.88 with isomorphic trees and 0.67-0.76 under side-specific tree divergence, so line M can fire and can fail |
| 4 | Consistent cuts excluded inverted phrases, the regions a translation loss targets (identification refuter) | Target = allowed pairs: splits of any alignment-consistent phrase pair into two consistent halves, straight or inverted (ITG-style), with maximum-matching hits | Sec. 6 | S1v2 gates: 52-55% of true allowed pairs are nested or inverted; a selection on true pairs scored on v1's monotone cuts alone reads S 0.37-0.40. The vectorized target matches a brute-force definition on 700 noisy synthetic alignments (0 mismatches) |
| 5 | I1 could not fail: a permuted alignment leaves about 0.05 cuts (identification refuter, reviewer 1) | I1 is cut-count preserving: the oracle's selection scored against a same-shape donor sentence's target | Sec. 8 | S1v2 gates: 0.048-0.061 against a donor, 1.000 against its own target |
| 6 | Aligner noise three to six times below the published Chinese-English rates and independent between aligners, so the thresholds were tuned in the wrong regime (feasibility refuter; both reviewers) | An error model calibrated to link AER 0.05-0.25 with balanced, precision-heavy and recall-heavy splits, and a correlation parameter c from 0 (independent) to 1 (identical errors) between the two aligners. It showed that a single aligner's target loses about 0.3 of S at AER 0.085 (alpha 0.66-0.70), so the decision target is the consensus of two aligner families (links both produce) | Secs. 6, 9 | S1v2 calibration and attenuation map: consensus alpha 0.92-0.96 at the published rates with independent errors, 0.86-0.91 at c = 0.5, 0.68-0.79 at c = 1 |
| 7 | NO_HEADROOM unreachable at the published error rates (feasibility refuter; both reviewers) | New aligners with published zh-en AER 0.048-0.090 (OmniAlign 8.5; BinaryAlign 4.8 supervised, 9.0 zero-shot), replacing CTFAlign and SimAlign (0.18-0.27). The remaining attenuation is handled on a registered band (largest and smallest consensus alpha with each aligner's AER at most 0.15 and any correlation, the smallest indexed by the measured pair agreement) or, if R5 is granted, measured on 300 XL-WA en-zh gold pairs and divided out | Secs. 9, 11 | S1v2 OC (Evaluation): with the gold sample, NO_HEADROOM with probability 1.00 at true S 1.00 and 0.16-0.23 at true S 0.91-0.92, HEADROOM 0.99-1.00 at true S 0.75 or less, no wrong decisive verdict in the band (at most 0.02 with a shifted gold sample); without it, the band path never errs in the band and decides at the extremes |
| 8 | fp32 with TF32 off against hnet's bf16-only attention; mamba_ssm at a6a1dae imports names transformers 5.15 removed (feasibility refuter; reviewer 1 verified) | bf16 (the checkpoints' native dtype), router probabilities recomputed in fp32 by the driver; a separate overlay environment with torch 2.7.1+cu128, the flash-attn 2.8.0.post2 wheel for torch 2.7, mamba_ssm a6a1dae and causal_conv1d e940ead from source, and transformers 4.57.1 (which still exports both names); encoder-only extraction (the main network is never run) | Sec. 14 | Static checks of the pinned files (C57-C63); the container smoke is still a prerequisite |
| 9 | NO_HEADROOM on monolingual released checkpoints was registered to stop E3 although they do not transfer to Stage 1's from-scratch multilingual model (feasibility refuter, reviewer 1) | The kill is narrowed and scoped in the record: "independently trained learned-boundary predictors already correspond at the decision budget"; reopening E3 needs evidence specific to multilingual learned-boundary models. A wider search found no released multilingual learned-boundary checkpoint | Sec. 1 | R10 query (no such checkpoint) |
| 10 | kappa_M and the SMT bilingual-segmentation lineage uncited; delta over token alignability and SOMBRERO overstated (novelty refuter; both reviewers) | Both credited: S is kappa_M's form; segmentation from alignment has an SMT lineage (Xu et al. 2008; Ma and Way 2009; Chung and Gildea 2009; Zeng et al. 2014; Chang, Galley and Manning 2008). Rows added for ITG and phrase-consistency (Wu 1997; Och and Ney 2003; Wellington et al. 2006), phrasal cohesion (Fox 2002) and misclassification correction (Rogan and Gladen 1978). Differentiation from 2502.06468 and 2601.22805 rewritten, and fresh anonymized packets written for both | Proposal only | Closest Prior Work; Novelty Ledger; `blind/` |
| 11 | The identification refuter ran no queries; the triad's reserve was breached; synthesis did not meter (process defects) | This run declares 80 queries with at least 30 reserved for the triad; the repair used 20 and logged every call | Header | `query-log-run2.json` |

Not repaired, and why:

- No harness, adapter, overlay, container smoke or Slurm dry run exists
  (Compute FAIL, cap 79). They come after a scored package and a freeze; the
  only host job allowed in this run is the open-weight reviewer's lane job.
- The stack fix is static: the pins were checked against the pinned upstream
  source files and release assets, not built. The smoke job is the proof.
- The aligners' error rates and error correlation on FLORES+ are unknown. The
  band path assumes each aligner's link AER is at most 0.15 there (published
  supervised rates 0.048-0.090, with headroom for the shift from news to
  Wikipedia text). It makes no assumption about correlation (the smallest alpha
  is indexed by the measured agreement), but if both aligners are worse than the
  band and their errors are shared, the band path can return a false HEADROOM;
  only the gold path (R5, an outward action reserved for Kevin) removes that
  assumption.
- Every number about the instrument is synthetic. The generator's synchronous
  tree makes monolingual syntax unusually predictive of alignment, so the line M
  rows are illustrative, not a forecast.
- Signed, provider-distinct reviews cannot exist here (D24, cap 89).
- The deterministic doctor parses `gpu_hours=0.3` as 0 and reports "all declared
  budgets must be positive"; the declared budget is honest and is not rounded up
  to pass (rule 3).

**Decisiveness after the repair** (S1v2 operating characteristics, the whole
registered decision path per replicate: consensus target, budget, floor, the
band or gold correction, the three-way rule; 100 replicates of 1,012 pairs per
condition and seed, 600 bootstrap resamples; `compute/repair-run2/oc-summary.md`).
Scenario systems are selections on true allowed pairs with a share f of each
side's gaps displaced to random or adjacent word gaps, giving true S from about
-0.07 to 1.00 (16 systems). A verdict is wrong if it is NO_HEADROOM with true S
below 0.85 or HEADROOM with true S of 0.90 or more.

| Condition (aligner link AER, error correlation c; seeds) | Path | P(NO_HEADROOM) at true S 1.00 / 0.91-0.92 | P(HEADROOM) at true S 0.74-0.75 / 0.42-0.44 | Mean P(decisive) over the 16 systems | Largest P(wrong decisive) |
|---|---|---|---|---:|---:|
| published rates 0.085 and 0.05, c 0-0.5 (42-44) | gold (R5) | 1.00 / 0.23 | 1.00 / 1.00 | 0.81 | 0.00 (0.01 with the gold sample's AER 0.03 worse than the test set's) |
| same | band | 1.00 / 0.00 | 0.00 / 1.00 | 0.51 | 0.00 |
| published rates, identical errors c 1 (42-44) | gold | 1.00 / 0.21 | 1.00 / 1.00 | 0.78 | 0.00 (0.02 with the shifted gold sample) |
| same | band | INSTRUMENT_INVALID (pair agreement 0.91 is at or above 0.85) | | 0.00 | 0.00 |
| band, AER 0.085-0.15, c 0-0.5 (10 runs) | gold | 1.00 / 0.16 | 0.99 / 1.00 | 0.77 | 0.00 (0.005 shifted) |
| same | band | 0.23 / 0.00 | 0.11 / 1.00 | 0.50 | 0.00 |
| band edge 0.15, c 1 (42-44) | both | INSTRUMENT_INVALID (gold alpha_hat below 0.70; agreement 1.00) | | 0.00 | 0.00 |
| beyond the band: 0.20 at c 0.5; 0.25 at c 1 (42) | band | 0.00 / 0.00 | 0.50 / 0.50 | 0.38 | 0.09 (false HEADROOM at true S 0.92, AER 0.20, c 0.5) |
| same | gold | 0.41 / 0.00 | 0.46 / 0.46 | 0.32 | 0.00 |

Read-out: with the gold sample (R5) the probe reaches a verdict for 77-81% of
the scenario systems at the published error rates, NO_HEADROOM is reachable
(probability 1.00 at true S 1.00, 0.16-0.23 at true S 0.91-0.92) and HEADROOM
fires whenever true S is 0.75 or less; no wrong decisive verdict occurs anywhere
inside the band (at most 0.02 when the gold sample's aligner error is 0.03 worse
than FLORES+'s, against 0.64 before the registered transfer margin of 0.03 on
alpha was added). Without the gold sample, the band path never errs inside the
band but decides only at the extremes: NO_HEADROOM only for true S near 1.00 and
only when errors are independent to mildly correlated, HEADROOM for true S of
about 0.45 or less (and up to 0.63-0.75 when the measured agreement is low,
because the registered alpha_min then rises); it refuses when the aligners agree
too much (shared errors). The regime the mechanism predicts for released
monolingual H-Nets (true S of about 0.45 or less) reads HEADROOM with probability
0.95-1.00 on both paths at the published rates. Every number is
conditional on the synthetic generator and the error model; the gates are
assumed to pass.

## Scope and what changed from the dossier

This proposal covers only E3's Stage 0 headroom probe on FLORES+ for released
byte-level checkpoints, as the dossier states
(`program/evidence/2026-10-06/question-dossier.md`, section 11). It trains
nothing. The Stage 1 screen (about 16 GPU-h) is out of scope and needs its own
gauntlet plus the four prerequisites the dossier names (a licensed parallel
corpus, a terminology and tool-schema evaluation set, a differentiable torch
loss, H-Net-style training code), none of which exists. "D18" in E3's name is
legacy direction 18 (`legacy/directions/18-translation-equivariant-byte-boundaries.md`),
not decision D18.

Wave 1 merged four discovery cells into seventeen mechanisms (M1-M17; the table
is in the wave-1 record and in this file's git history at `9d79644`). Their
status after the repair:

- **Kept:** M4 (Bolmo-1B and Bwen-8B boundaries are their tokenizers'; the
  tokenizers stand in), M5 (every released H-Net is monolingual; EN-ZH is the
  decision pair with an in-distribution model per side; EN-KO and EN-PL are
  descriptive), M6 (orthography dominates raw scores; per-pair reporting only),
  M10-M13 (token alignability, SOMBRERO, chance-correction lineages, data rights),
  M16 (correspondence headroom does not imply downstream gains), M17 (the legacy
  evaluator runs only from its legacy path; secondary only).
- **Kept and extended:** M1-M3 (the dossier's UOT instrument cannot decide; it
  stays a secondary) and the canonical-gap rule of M3, now re-checked under v2.
- **Replaced by this repair:** M2's floor and ceiling (rows 1-2), M7 line M
  (row 3), M8 aligners (rows 6-7), M9 thresholds (row 7 and Evaluation), M14 the
  stack (row 8), M15 cost (S2v2: caps 0.2 + 0.7 = 0.9 GPU-h, central 0.26, high
  0.63).

Six corrections to the frozen dossier, recorded because the dossier is not
edited: (1) the NumPy UOT cost cannot decide (S1, wave 1); (2) Bolmo-1B is its
tokenizer up to an unmeasured residual; (3) EN-KO and EN-PL have no
in-distribution learned-boundary model; (4) "90% of the correspondence ceiling"
had no normalization; v2 defines it at a common budget with an exact ceiling and
an attenuation correction; (5) frozen aligner spans are now a two-family
consensus with an error model; (6) Bolmo's non-causal predictor is irrelevant to
a Stage 0 measurement.

## Claim and Research Question

**Question.** On FLORES+ devtest (revision `e707e62e`, 1,012 sentences per
language), EN-ZH, with an in-distribution H-Net on each side: at one common
per-sentence budget k (half of the smaller side's word gaps, capped by the number
of disjoint allowed pairs), do the model's k strongest word gaps on each side
already form alignment-consistent split pairs at, or near, the rate of an oracle
on the two aligners' consensus target, once attenuation by aligner error is
corrected? And if not, does a monolingual syntactic reference already close the
gap?

- **Decision pair:** EN-ZH; English side `hnet_2stage_XL`, Chinese side
  `hnet_2stage_XL_chinese`.
- **Primary system:** the hierarchical stage-2 score (stage-2 router probability
  at gaps carrying a native stage-1 boundary; every other gap ranked below them by
  its stage-1 probability). Stage 2 is the level that sets where the main network
  spends compute, and the only level coarser than the words of both languages:
  at stage 1 the boundaries are finer than the alignment's words on both sides,
  so every consistent split is already marked by any word segmentation and the
  question is trivial there (wave 1's defect).
- **Descriptive:** stage-1 scores; native boundary sets; same-model variants;
  EN-KO and EN-PL with the English model on both sides; tokenizer references in
  the unrestricted form.

**Primary quantity.** S_C, the chance-corrected, budget-matched agreement of the
primary system's selections with the consensus target, corrected for aligner
attenuation on the band path (S_lo, S_hi) or the gold path (S*), with a 90%
document-cluster bootstrap interval.

**Claim scope.** A measurement on released monolingual checkpoints. Not
`architecture-causal`, not a method claim, and no claim about terminology,
tool-schema exactness or bits per byte. It licenses only "E3's Stage 1
prerequisites are (not) worth building" or "E3 stops with a recorded, scoped
negative".

**Hypothesis under test (H_room).** The primary system's corrected S is below
0.85 (upper bound), and so is the monolingual reference's: the strongest learned
boundaries do not already correspond across translations, and monolingual syntax
does not close the gap. **Kill (the dossier's):** corrected S of at least 0.90
with a lower bound of at least 0.88 is NO_HEADROOM and stops E3 as scoped.

## Strategic Fit and Why Now

E3 is item 6 of the backfill queue (`program/backlog.md`). D67 restarted every
remaining line after Q2 S1a's result (D66); D68 gave E3 one repair run. E3's
first step is the cheapest item in the queue (caps 0.9 GPU-h) and gates a large,
expensive build: the parallel corpus, the evaluation set, the torch loss and the
training code Stage 1 needs. A no-headroom verdict saves that build; a headroom
verdict gives Stage 1 a measured effect prior (the shortfall and the monolingual
reference's share of it).

Why now:

- The substrates moved: Bolmo's Nature version (2026-10-07) and byteified 8B
  models whose boundaries are distilled from their tokenizers; H-Net's English
  and Chinese 2-stage checkpoints remain the only released learned-boundary
  models with an in-distribution model per side of a language pair (R10 found no
  multilingual one).
- The neighbours moved: SOMBRERO (2026-01-30) measures and steers learned
  boundary placement against monolingual next-byte surprisal; cross-lingual MoE
  router alignment (2026-10-01) supervises a discrete compute-allocation decision
  with translations; the Multi-Level Transformer and B-Net submissions report
  learned boundaries that converge on tokenizer-like units. Whether learned
  boundaries already correspond across translations at a compute-relevant budget
  is the missing measurement between them.
- Aligners moved: supervised Chinese-English aligners now report AER 0.048-0.090
  (2407.12881, 2608.18474) against 0.18-0.27 for the embedding-similarity
  aligners wave 1 used, which is what makes a consensus target with small
  attenuation possible.

## Primary-Source Evidence

Claim registry (ARS claim-verification protocol: claim, source, locator, read
depth, status). Read depth: F = full text read by targeted section; S = re-read
by synthesis; A = abstract or search payload only; M = metadata or API record;
R = repository evidence; X = first-party (single source, unreplicated). C01-C52
are wave 1's (C24-C26 describe the wave-1 aligners CTFAlign and SimAlign, which
v2 replaces; C32 is wave 1's simulation S1, kept as it was); C53-C74 were added
by this repair.

| ID | Claim | Source and date | Locator | Depth | Status |
|---|---|---|---|---|---|
| C01 | H-Net's routing module sets p_t = (1 - cos(q_t, k_t-1)) / 2 with p_1 = 1, a boundary marks a chunk start at t | [2507.07955](https://arxiv.org/abs/2507.07955), v2 2025-07-15 | Sec. 2.2, Eq. 4 | F, S | VERIFIED |
| C02 | The released code selects a boundary by argmax over (1 - p, p), so a boundary needs p above 0.5; the first position is padded with probability 1 | [goombalab/hnet](https://github.com/goombalab/hnet) `hnet/modules/dc.py`, main 3673fe12 | lines 92-104 | R, S | VERIFIED |
| C03 | H-Net 1-stage places boundaries predominantly at whitespace; stage 1 of the 2-stage model combines spacelike boundaries with the first few characters of each word | [2507.07955](https://arxiv.org/abs/2507.07955) | Sec. 3, visualization bullets (Fig. 4) | F, S | VERIFIED |
| C04 | The Chinese 2-stage XL model was trained on a 46B-token FineWeb-Edu-Chinese-V2.1 subset with the same target downsampling ratio (N0 = N1 = 3) | [2507.07955](https://arxiv.org/abs/2507.07955) | Sec. 3, "Experimental setup for Chinese and code" | F, S | VERIFIED |
| C05 | Released checkpoints: 1-stage and 2-stage L and XL on English FineWeb-Edu 100B; 2-stage XL Chinese and code | [goombalab/hnet](https://github.com/goombalab/hnet) README | "Pretrained Models" | R, S | VERIFIED |
| C06 | Each H-Net repository holds one pickle `.pt` file (2-stage XL 6,414,086,360 B; Chinese 7,021,270,658 B; 1-stage XL 5,083,413,223 B) and declares no licence; the code is MIT; upstream `generate.py` loads with `weights_only=False` | [hnet_2stage_XL](https://huggingface.co/cartesia-ai/hnet_2stage_XL), [hnet_2stage_XL_chinese](https://huggingface.co/cartesia-ai/hnet_2stage_XL_chinese), [hnet_1stage_XL](https://huggingface.co/cartesia-ai/hnet_1stage_XL); checked 2026-10-10 | model API (revisions c56e23e0, 01db28db, 68f11d72); `generate.py` line 45 | M, S | VERIFIED |
| C07 | Bolmo's boundary predictor is non-causal with one byte of future context; in Stage 1 it is trained to emulate the source tokenizer's patch ends and "quickly achieves" more than 99% accuracy; Stage 2 keeps the boundary loss; non-causal boundaries are not trained end to end | [2512.15586](https://arxiv.org/abs/2512.15586), v2 2026-02-09 | Secs. 3.1.1, 3.2.1, 3.2.2 | F, S | VERIFIED |
| C08 | Bolmo's Nature version (2026-10-07) adds Bwen 8B (from Qwen3 8B Base) and Blama 8B (from Llama 3 8B); code allenai/bolmo-core is Apache-2.0 | [Nature s41586-026-11111-4](https://www.nature.com/articles/s41586-026-11111-4); [allenai/bolmo-core](https://github.com/allenai/bolmo-core) | HTML text; GitHub API | F (HTML), M | VERIFIED (HTML only; Supplementary not read) |
| C09 | Bolmo-1B (Apache-2.0, revision 452690a8, modified 2026-10-07) and Bwen-8B (Apache-2.0, b2644f78) are ungated | [Bolmo-1B](https://huggingface.co/allenai/Bolmo-1B), [Bwen-8B](https://huggingface.co/allenai/Bwen-8B) | model API, 2026-10-10 | M, S | VERIFIED |
| C10 | Boundary divergence between two models is defined as 1 - F1 over per-byte labels; Bolmo's boundaries "barely differ" from the OLMo tokenizer (no numbers); both experiments are only proposed | [2608.03599](https://arxiv.org/abs/2608.03599), v1 2026-08-04 | Secs. 2-3 | F | VERIFIED; X for the Bolmo statement |
| C11 | MAGNET sets per-script binomial boundary priors from byte-to-word ratios, pretrains on nine languages (en, es, fr, ru, uk, be, te, bn, hi) and measures parity as segment counts on FLORES-200 | [2407.08818](https://arxiv.org/abs/2407.08818), v2 2024-11-17; NeurIPS 2024 | Sec. 2.2; pretraining data; Sec. 4.1 | F | VERIFIED |
| C12 | CAROT aligns parallel hidden states with token-level unbalanced Sinkhorn OT (mass penalty 0.5) over fixed subword boundaries; its comment reports EMNLP 2026 main | [2609.06381](https://arxiv.org/abs/2609.06381), v1 2026-09-06 | method; appendix; arXiv comment | F | VERIFIED; venue self-reported |
| C13 | When Tokenizers Fail adds POS supervision every 10 steps and a chunk-alignment loss toward frozen subword targets on top of the H-Net ratio loss; its Table 1 reports chunk-to-word ratio and the share of chunks covering exactly one word for six Indic languages | [2608.27658](https://arxiv.org/abs/2608.27658), v1 2026-08-27 | Sec. 3.2; Table 1 | F | VERIFIED; EMNLP 2026 self-reported |
| C14 | SOMBRERO's confidence-alignment loss is (1 - sg[P_t+1] - p_t)^2; its boundary enrichment B is tested against a rate-matched circular-shift null with a Z-score; data are English, German, code and math | [2601.22805](https://arxiv.org/abs/2601.22805), v1 2026-01-30 | Secs. 3.4, 3.5, 4.1 | F, S | VERIFIED |
| C15 | Token alignability runs eflomal (priors from up to 300k OPUS-100 pairs) for one iteration on FLORES-200 and reports the per-direction share of one-to-one subword alignments and the eflomal score; the score predicts transfer better than token overlap, especially across scripts | [2502.06468](https://arxiv.org/abs/2502.06468), 2025-02-10; [NAACL 2025](https://aclanthology.org/2025.naacl-short.63/) | Secs. 3.2, 4.1, 5 | F, S | VERIFIED |
| C16 | Conditional Unigram Tokenization conditions a target-language unigram tokenizer on source tokens of parallel data; MT does not improve, perplexity falls; a data-efficiency bottleneck is named | [2507.07824](https://arxiv.org/abs/2507.07824), 2025-07-10; [TokShop OpenReview](https://openreview.net/forum?id=lnWJWNA8YW) | abstract; Secs. 5.2-5.3 | F | VERIFIED |
| C17 | Cross-lingual MoE router alignment adds a KL loss over mean-pooled routing weights across parallel sequences during continual pretraining of four MoEs and improves multilingual performance | [2610.01921](https://arxiv.org/abs/2610.01921), v1 2026-10-01, v2 2026-10-02; [OpenReview](https://openreview.net/forum?id=67SF8nq4EN) | abstract; Sec. 1 | F, S | VERIFIED |
| C18 | B-Net pairs a causal boundary scorer with an adaptive threshold controller that hits a requested patch rate and reports ratio-loss rate drift | [OpenReview fMymbXoq9T](https://openreview.net/forum?id=fMymbXoq9T), ICLR 2027 submission | abstract (search payload) | A | UNVERIFIABLE_ACCESS (full text) |
| C19 | The Multi-Level Transformer's learned chunk boundaries closely match trained tokenizers' on English and Chinese | [OpenReview SUsOuZ5Opq](https://openreview.net/forum?id=SUsOuZ5Opq), ICLR 2027 submission | abstract (search payload) | A | UNVERIFIABLE_ACCESS (full text) |
| C20 | In BLT-1B at a 10% patch rate, entropy patching gets 19.0% of computed GSM8K results exactly right, a boundary after each '=' 51.8%, and entropy plus a boundary-dependence signal 67.1% | [2610.11790](https://arxiv.org/abs/2610.11790), v1 2026-10-08 | abstract | F | X (single author, unreplicated) |
| C21 | Small per-language H-Nets on 18 languages favour byte efficiency, with long tokens and low overlap with subword vocabularies | [2608.17325](https://arxiv.org/abs/2608.17325), 2026-08-18 | abstract; Secs. 3.1-3.4 | F | VERIFIED |
| C22 | Varying the parallel-data share in pretraining has minimal effect on cross-lingual representation alignment | [2603.29026](https://arxiv.org/abs/2603.29026), 2026-03-30 | abstract; Sec. 1 | F | VERIFIED |
| C23 | Input segmentation learned from the NMT objective converges to near-character level | [1810.01480](https://arxiv.org/abs/1810.01480), 2018-10-02 | abstract | F | VERIFIED |
| C24 | OmniAlign (Apache-2.0) reports zh-en AER 8.5 and ja-en 29.6, with no ko-en or pl-en gold test | [2608.18474](https://arxiv.org/abs/2608.18474), 2026-08-19; [MilkDargon/OmniAlign](https://github.com/MilkDargon/OmniAlign) | Table 4; GitHub API | F, M | VERIFIED |
| C25 | CTFAlign (MIT) is gold-evaluated on en-de, en-fr, en-ro, en-ja, en-zh and en-cs, with a bring-your-own embedder | [2608.21023](https://arxiv.org/abs/2608.21023) ("Scaling Unsupervised Word Alignment to Documents via Structural Constraints", v1 2026-08-21); [ZurichNLP/CTFAlign](https://github.com/ZurichNLP/CTFAlign) | Table 1, Fig. 4; GitHub API (pushed 2026-10-07) | F, M | VERIFIED |
| C26 | SimAlign is MIT; awesome-align is BSD-3-Clause; LaBSE is Apache-2.0; XLM-R base is MIT | [cisnlp/simalign](https://github.com/cisnlp/simalign), [neulab/awesome-align](https://github.com/neulab/awesome-align), [LaBSE](https://huggingface.co/sentence-transformers/LaBSE), [xlm-roberta-base](https://huggingface.co/FacebookAI/xlm-roberta-base) | GitHub and HF APIs, 2026-10-10 | M, S | VERIFIED |
| C27 | XL-WA has 90 dev and 210 test manually aligned sentences for en-ko and en-zh, obtainable on request; its licence file is CC BY-NC-SA 4.0; it has no en-pl | [SapienzaNLP/XL-WA](https://github.com/SapienzaNLP/XL-WA) | README table; LICENSE | R | VERIFIED |
| C28 | FLORES+ is CC-BY-SA-4.0, gated with automatic approval, revision e707e62e modified 2026-10-01 | [openlanguagedata/flores_plus](https://huggingface.co/datasets/openlanguagedata/flores_plus) | dataset API, 2026-10-10 | M, S | VERIFIED |
| C29 | The legacy NumPy evaluator's doctor still passes all six gates from its legacy path with payload SHA-256 6d8c24be... | `legacy/scripts/run_boundary_transport_doctor.py` | re-run by synthesis 2026-10-10 | R, S | VERIFIED |
| C30 | On hand-written toy pairs the legacy evaluator's aligned over permuted ratio is 0.88 to 1.04 for every rule and the chunk-start convention raises loss to 0.86 to 0.95 | kill-shot cell scratch demo (`confound_demo.py`, seed 42) | output rows | R | VERIFIED (toy, illustrative) |
| C31 | On synthetic spans a one-byte offset on one side scores 0.44, worse than count-matched random 0.32; Bernoulli loss falls from about 0.46 to 0.14 between rates 0.05 and 0.5 | cross-domain cell scratch (`rate_confound*.py`, seeds 42-44) | outputs | R | VERIFIED (synthetic) |
| C32 | S1 results quoted in this proposal (UOT and PBD gates, operating characteristics, calibration decomposition) | `compute/instrument_sim.py`, `compute/instrument-sim.json` | parts 1-4 | R, S | VERIFIED (synthetic) |
| C33 | A coincidence index for spike trains is unbounded and confounded by firing rate; the spike time tiling coefficient corrects it | [Cutts and Eglen 2014](https://doi.org/10.1523/jneurosci.2767-14.2014) | abstract | A | VERIFIED (abstract) |
| C34 | Spike-resolved distances (Victor-Purpura, van Rossum) always carry rate information | [1708.07508](https://arxiv.org/abs/1708.07508), 2017-08-23 | abstract | A | VERIFIED (report) |
| C35 | The debiased unbalanced Sinkhorn divergence is robust to the double penalty in forecast verification and splits into transport cost and marginal mass imbalance | [2412.16063](https://arxiv.org/abs/2412.16063), v3 2025-07-25 | Secs. 2, 5 | F | VERIFIED |
| C36 | The unbalanced Sinkhorn divergence includes the term (eps/2)(m(alpha) - m(beta))^2, which the legacy evaluator implements per block | [1910.12958](https://arxiv.org/abs/1910.12958), 2019-10-28 | divergence definition | F | VERIFIED |
| C37 | 1-D unbalanced OT can be solved exactly by Frank-Wolfe with 1-D OT oracles | [2201.00730](https://arxiv.org/abs/2201.00730), 2022-01-03 | abstract | F | VERIFIED |
| C38 | OT word-alignment F1 falls as the null-alignment rate rises, and thresholding regularized plans is vital | [2306.04116](https://arxiv.org/abs/2306.04116), ACL 2023 | Sec. 1, Sec. 7 | F | VERIFIED |
| C39 | Significant AER reductions have not been shown to give significant translation gains | [Fraser and Marcu 2007](https://doi.org/10.1162/coli.2007.33.3.293) | abstract | A | VERIFIED (abstract) |
| C40 | Gamma computes disorder from an optimal alignment of units and corrects it against shuffled corpora | [Mathet et al. 2015](https://doi.org/10.1162/coli_a_00227) | abstract | A | VERIFIED (abstract); shuffling detail from known method |
| C41 | Boundary edit distance credits near misses separately from additions and deletions (boundary similarity B) | [Fournier 2013](https://aclanthology.org/P13-1167/) | ACL 2013 long paper | A | VERIFIED (landing page snippet) |
| C42 | Boundary hit rate rises with over-segmentation; the R-value corrects for it | [Rasanen et al. 2009](https://www.isca-archive.org/interspeech_2009/rasanen09b_interspeech.html) | abstract | A | VERIFIED (snippet) |
| C43 | In dialogue segmentation, threshold sweeps move window-tolerant F1 more than switching methods | [2512.17083](https://arxiv.org/abs/2512.17083), v1 2025-12-18, v3 2025-12-31 | abstract | F | X (single author, under review) |
| C44 | Under point adjustment a random anomaly score can reach F1 near 1; affiliation metrics give a random predictor about 0.5 precision and recall | [2109.05257](https://arxiv.org/abs/2109.05257); [2206.13167](https://arxiv.org/abs/2206.13167) | Sec. 3.2; report | A | VERIFIED (report) |
| C45 | regioneR tests region-set association by permutation and checks local specificity by shifting one set | [Gel et al. 2015](https://doi.org/10.1093/bioinformatics/btv562) | abstract | A | VERIFIED (abstract) |
| C46 | The pinned research image (torch 2.11, triton 3.6, transformers 5.15) has no mamba-ssm, causal-conv1d, flash-attn or xlstm | `uv.lock` (0 matches), asset cell's Dockerfile read | grep by synthesis | R, S | VERIFIED |
| C47 | Q3 splits 488 Belebele passages into development 122, audit 122 and primary 244 links and never reads the audit and primary partitions | `program/preregistrations/q3-dense-headroom-precheck-v2.md` | "Data (development partition only)" | R, S | VERIFIED |
| C48 | UBE has a v2 (2026-10-02) and reports NeurIPS 2026 in its comment; BLT's boundaries come from a separately trained entropy model with no gradient | [2610.01984](https://arxiv.org/abs/2610.01984); [2412.09871](https://arxiv.org/abs/2412.09871) | version history; dossier anchor | F, M | VERIFIED; venue self-reported |
| C49 | H-Net++'s learned chunks reach 73.8% F1 against gold Persian morphological boundaries | [2508.05628](https://arxiv.org/abs/2508.05628), 2025-08-07 | abstract | F | VERIFIED |
| C50 | Flat byte Transformers develop segmentation-like positions without a boundary head | [2610.05978](https://arxiv.org/abs/2610.05978), 2026-10-05 | abstract | F | VERIFIED |
| C51 | Parallel Tokenizers aligns monolingual vocabularies with bilingual dictionaries so equivalent words share embeddings; v3 reports EMNLP 2026 main | [2510.06128](https://arxiv.org/abs/2510.06128), v3 2026-09-26 | abstract; comment | F | VERIFIED; venue self-reported |
| C52 | In Chinese word-boundary recovery by character-alignment projection, boundary drift is 1.3% to 2.3% of errors; most errors are split or merge decisions | [2605.28128](https://arxiv.org/abs/2605.28128), 2026-05-27 | Sec. 5.4, Table 3 | F | VERIFIED |
| C53 | OmniAlign reports zh-en AER 8.5 on the 450-sentence Tsinghua test set after supervised fine-tuning on 40.7K Chinese-English pairs from the TsinghuaAligner website, 14.3 without that stage; the same table lists SimAlign 21.6, AwesomeAlign 13.3, AccAlign 11.5, WSPAlign (bilingual) 13.1 and BinaryAlign (bilingual) 4.8 | [2608.18474](https://arxiv.org/abs/2608.18474), 2026-08-19 | Sec. 3.1, Table 3, Table 4, Table 6 | F (re-read this run) | VERIFIED |
| C54 | OmniAlign's model (`WPS-Qingqiu/OmniAlign`, revision eaeeb279, Apache-2.0) is an mGTE encoder whose config was written with transformers 4.56.1 and whose model card loads custom modelling code (`modeling.py`, `configuration.py`) | [WPS-Qingqiu/OmniAlign](https://huggingface.co/WPS-Qingqiu/OmniAlign) | model API and `config.json`, 2026-10-10 | M, R | VERIFIED |
| C55 | BinaryAlign reformulates alignment as per-source-word binary sequence labelling on mDeBERTa-v3; zh-en AER 9.0 zero-shot from a model trained on six other pairs (Table 1), 6.7 few-shot and 4.8 fully supervised (Table 2); eflomal 28.7 and SimAlign 21.6 zero-shot | [2407.12881](https://arxiv.org/abs/2407.12881), ACL 2024 | Tables 1, 2, 4 | F (read this run) | VERIFIED |
| C56 | BinaryAlign's repository (commit 5acb6e7f, 2024-08-08) releases checkpoints for Align6, de-en, ro-en, fr-en, zh-en and ja-en (`models/zhen/model.safetensors`, LFS SHA-256 615c9001..., 1,110,146,980 bytes) under CC BY-NC-ND 4.0; its requirements pin torch 2.1.0 and transformers 4.43.0 | [ubisoft/ubisoft-laforge-binaryalign](https://github.com/ubisoft/ubisoft-laforge-binaryalign) | README, `license.txt`, `requirements.txt`, LFS pointer, GitHub API | R | VERIFIED |
| C57 | hnet at 3673fe12 pins `mamba_ssm` at a6a1dae, `flash_attn==2.8.0.post2`, `causal_conv1d` at e940ead, torch at least 2.5.1 and triton at least 3.2.0 | [goombalab/hnet](https://github.com/goombalab/hnet) `pyproject.toml` | dependencies | R (read this run) | VERIFIED |
| C58 | mamba_ssm at a6a1dae (version 2.2.4, committed 2025-06-26) imports `GreedySearchDecoderOnlyOutput`, `SampleDecoderOnlyOutput` and `TextStreamer` from `transformers.generation` (`mamba_ssm/utils/generation.py` line 14) and its package `__init__` imports the module chain that reaches it; mamba main (2.3.2.post1) imports `GenerateDecoderOnlyOutput` instead | [state-spaces/mamba](https://github.com/state-spaces/mamba) | files at a6a1dae and main; GitHub commits API | R | VERIFIED |
| C59 | transformers v5.15.0's `generation/__init__.py` contains no `GreedySearchDecoderOnlyOutput` or `SampleDecoderOnlyOutput` (0 matches each) while v4.57.1's contains them (4 and 8 matches); v4.57.1 requires torch at least 2.2 | [huggingface/transformers](https://github.com/huggingface/transformers) | `src/transformers/generation/__init__.py` at both tags; `setup.py` at v4.57.1 | R | VERIFIED |
| C60 | flash-attn v2.8.0.post2 ships 38 wheels, for torch 2.4, 2.5, 2.6 and 2.7 only, including `cu12torch2.7cxx11abiTRUE` and `cxx11abiFALSE` for cp312 | [flash-attention release v2.8.0.post2](https://github.com/Dao-AILab/flash-attention/releases/tag/v2.8.0.post2) | release assets (GitHub API) | M | VERIFIED |
| C61 | hnet's `RoutingModule` computes p = clamp((1 - cos(q_t-1, k_t)) / 2) and selects boundaries by argmax; `HNet.forward` runs encoder, routing, chunking, then the main network; `generate.py` builds the model in bf16 (line 38) | [goombalab/hnet](https://github.com/goombalab/hnet) `hnet/modules/dc.py`, `hnet/models/hnet.py`, `generate.py` at 3673fe12 | as cited | R | VERIFIED |
| C62 | causal-conv1d e940ead is a 2025-06-23 merge commit | [Dao-AILab/causal-conv1d](https://github.com/Dao-AILab/causal-conv1d) | GitHub commits API | M | VERIFIED |
| C63 | The research base image is built from `nvidia/cuda:12.8.1-cudnn-devel-ubuntu24.04` (nvcc available for source builds) | `infra/research/Dockerfile` | line 2 | R | VERIFIED |
| C64 | spaCy's `en_core_web_sm` and `zh_core_web_sm` are MIT; `zh_core_web_sm` 3.8.0 (released 2024-09-30) is trained on OntoNotes 5 with the CoreNLP UD converter | [spacy/zh_core_web_sm](https://huggingface.co/spacy/zh_core_web_sm), [spacy-models release](https://github.com/explosion/spacy-models/releases/tag/zh_core_web_sm-3.8.0) | model API; release notes | M | VERIFIED |
| C65 | Cohen's kappa is chance-corrected agreement; its maximum at fixed marginals (kappa_M) scales it, the form S takes here | [Cohen 1960](https://doi.org/10.1177/001316446002000104); modern treatment in Psychometrika 2022 ([10.1007/s11336-022-09844-y](https://doi.org/10.1007/s11336-022-09844-y)) | metadata (OpenAlex); wave-1 novelty refuter's sources | M, A | VERIFIED (metadata; kappa_M attribution from secondary sources) |
| C66 | An apparent rate measured with an imperfect instrument is corrected by the instrument's error rates estimated on validation data (Rogan-Gladen) | [Rogan and Gladen 1978](https://doi.org/10.1093/oxfordjournals.aje.a112510); [BMC Public Health 2020](https://doi.org/10.1186/s12889-020-09177-4) | metadata | M, A | VERIFIED (metadata) |
| C67 | Phrases in one language tend to stay contiguous (cohere) in a translation (English-French) | [Fox 2002](https://doi.org/10.3115/1118693.1118732), EMNLP 2002 | metadata | M | VERIFIED (metadata) |
| C68 | Inversion transduction grammars split bilingual phrases in straight or inverted order | [Wu 1997](https://openalex.org/W2158388102), Computational Linguistics 23(3) | metadata | M | VERIFIED (metadata) |
| C69 | Empirical lower bounds on the complexity of translational equivalence (how much real alignment needs beyond binary ITG splits) | [Wellington, Waxmonsky and Melamed 2006](https://doi.org/10.3115/1220175.1220298), ACL 2006 | metadata | M | VERIFIED (metadata) |
| C70 | Segmenting Chinese with bilingual or MT signals is an SMT-era line: Bayesian semi-supervised segmentation for SMT (Xu et al. 2008), bilingually motivated segmentation (Ma and Way 2009), unsupervised tokenization for MT (Chung and Gildea 2009), segmentation optimized for MT (Chang, Galley and Manning 2008), word boundaries learned by bilingual character alignment (Zeng et al. 2014) | [10.3115/1599081.1599209](https://doi.org/10.3115/1599081.1599209); [10.3115/1609067.1609128](https://doi.org/10.3115/1609067.1609128); [D09-1075](https://aclanthology.org/D09-1075/); [10.3115/1626394.1626430](https://doi.org/10.3115/1626394.1626430); [P14-1128](https://aclanthology.org/P14-1128/) | metadata; P14-1128 text read by the wave-1 novelty refuter | M, F (P14-1128) | VERIFIED (metadata) |
| C71 | Intersecting two directional or system alignments gives high precision and lower recall (symmetrization) | [Och and Ney 2003](https://doi.org/10.1162/089120103321337421), Computational Linguistics 29(1) | metadata | M | VERIFIED (metadata) |
| C72 | S1v2 results quoted in this proposal (calibration, attenuation, identification, gates, line M, operating characteristics) | `compute/repair-run2/` outputs | files named in the Evidence column | R | VERIFIED (synthetic) |
| C73 | TokEval (COLM 2026) evaluates tokenizers with intrinsic metrics including cross-lingual parity and fairness from line counts on parallel text; no alignment-based correspondence measure | [2608.18062](https://arxiv.org/abs/2608.18062) | abstract; Sec. 3 | F (report) | VERIFIED |
| C74 | The TsinghuaAligner site (source of the zh-en gold sets these aligners were evaluated on) returned HTTP 502 on 2026-10-10; BinaryAlign notes that the zh-en data WSPAlign used is not publicly available | TsinghuaAligner page; [2407.12881](https://arxiv.org/abs/2407.12881) Appendix A.2 | fetch log; appendix | R, F | VERIFIED (access failure recorded) |

## Closest Prior Work

| Work | What it does | Delta from this probe |
|---|---|---|
| Token alignability ([2502.06468](https://arxiv.org/abs/2502.06468); NAACL 2025) | Runs a statistical aligner (eflomal, one iteration, priors from up to 300k OPUS pairs) on FLORES-200 already split into a tokenizer's subword tokens; reports the per-direction share of one-to-one token alignments and the aligner's link score, and correlates them with cross-lingual transfer | **Closest prior for the measurement; the question is shared.** It asks how well a segmentation corresponds across translations, on the same corpus family, with a word aligner; its future-work section proposes the score as a criterion for building tokenizers. This probe differs in what it can claim, not in the idea: (1) the object is a learned byte-level boundary score, not a fixed vocabulary; (2) the aligner never sees the evaluated units: alignment is fixed on words and the units are scored against it, whereas aligning the units themselves entangles aligner behaviour with segmentation (the paper notes its one-to-one share falls when the source is over-segmented); (3) a common budget, a chance floor and an exact maximum (kappa_M form) separate placement from rate, where the prior's scores have no chance level or maximum; (4) nested and inverted splits count; (5) aligner attenuation is modelled and corrected (consensus target, band or gold path); (6) the output is a pre-registered go or no-go, not a correlational predictor. The prior is the stronger finding (validated against transfer across many models); wave 1's blind critic said so, and this proposal does not claim otherwise |
| SOMBRERO ([2601.22805](https://arxiv.org/abs/2601.22805)) | Measures where an H-Net-style router places chunk starts by boundary enrichment (mean next-byte surprisal at boundaries over the mean), tested against a rate-matched circular-shift null; steers the router with a confidence-alignment loss toward one minus the next-byte probability; English, German, code, math | **Closest prior for measuring learned boundary placement against a null, and for Stage 1's loss form.** Its target is monolingual (a sequence's own prediction difficulty); this probe's is cross-lingual and paired (a selected English gap counts only with a matching Chinese gap). Its statistic is a ratio with a z-score; this one is chance-corrected agreement with an exact maximum at a common budget. Wave 1 adopted SOMBRERO's circular-shift null and it collapsed on the dense side; v2 replaces it with a two-sided random word-gap floor. E3's Stage 1 would change SOMBRERO's loss target from surprisal to translation spans (out of scope here) |
| SMT bilingual and MT-driven segmentation (Xu et al. 2008; Ma and Way 2009; Chung and Gildea 2009; Chang, Galley and Manning 2008; Zeng et al. 2014) | Learns or tunes Chinese word segmentation from word alignment or MT quality | Owns translation-supervised segmentation for SMT-era segmenters; it narrows E3's Stage 1 residual further (a translation signal shaping segmentation is old). None measures whether a learned byte-level model's boundaries already correspond across translations |
| Consistent phrase pairs and ITG splits (Och and Ney 2003; Wu 1997; Wellington et al. 2006) | Phrase-pair consistency with an alignment; binary straight or inverted bilingual splits; how much real alignment exceeds binary splits | The target definition is theirs; this probe uses it as the yardstick for boundaries |
| Cohen's kappa and kappa_M (Cohen 1960) | Chance-corrected agreement scaled by its maximum at fixed marginals | S is this form at a common budget; credited, not claimed |
| Phrasal cohesion (Fox 2002) | Monolingual phrases tend to cohere across translations | The premise line M tests: if monolingual syntax already reaches the criterion, translation supervision is unnecessary at this budget |
| Rogan-Gladen correction (1978) | Corrects an apparent rate with an instrument's error rates from validation data | The gold path's correction has this form |
| MAGNET ([2407.08818](https://arxiv.org/abs/2407.08818)) | Per-script boundary priors for parity | Owns parity by rate calibration; this probe equalizes rate exactly per sentence and asks about placement |
| When Tokenizers Fail ([2608.27658](https://arxiv.org/abs/2608.27658)) | Monolingual boundary supervision (POS, frozen subword targets) on byte chunking | Owns monolingual supervision; line M is its measurement-side counterpart |
| Conditional Unigram Tokenization ([2507.07824](https://arxiv.org/abs/2507.07824)); cross-lingual MoE router alignment ([2610.01921](https://arxiv.org/abs/2610.01921)) | Translation-supervised subword segmentation; translation-supervised alignment of pooled routing | Each half of Stage 1's idea is published; this probe trains nothing |
| CAROT ([2609.06381](https://arxiv.org/abs/2609.06381)); Disentangling LM and boundaries ([2608.03599](https://arxiv.org/abs/2608.03599)) | State alignment at fixed boundaries; boundary divergence as 1 - F1 between models | No boundary correspondence across translations; 1 - F1 is not chance-corrected or budget-matched |
| Bolmo ([2512.15586](https://arxiv.org/abs/2512.15586)); H-Net ([2507.07955](https://arxiv.org/abs/2507.07955)) | Tokenizer-distilled boundaries; end-to-end learned chunk starts | Substrates and references |
| OmniAlign ([2608.18474](https://arxiv.org/abs/2608.18474)); BinaryAlign ([2407.12881](https://arxiv.org/abs/2407.12881)); TokEval ([2608.18062](https://arxiv.org/abs/2608.18062)) | Supervised aligners; a tokenizer metric suite with count-based cross-lingual parity | Instruments and a neighbour; TokEval has no alignment-based correspondence measure |

## Novelty Ledger

| Proposed component | Closest prior | Same | Delta | Confidence |
|---|---|---|---|---|
| Correspondence of segmentation across translations measured on FLORES with an aligner | Token alignability (2502.06468) | The question and the corpus | Learned byte boundary scores; alignment fixed on words, never on the evaluated units; budget, chance and maximum controlled | High that the idea is shared; medium-low that the delta is worth a paper |
| Chance correction with an exact maximum at a common budget | Cohen's kappa_M (1960); SOMBRERO's rate-matched null; R-value and forecast verification (wave 1) | Chance-corrected agreement | Applied to paired cross-lingual boundary selections with a two-sided random word-gap floor | High (adopted, not claimed) |
| Target of straight and inverted splits of consistent phrase pairs | Och and Ney 2003; Wu 1997 | The definitions | Used as a yardstick for model boundaries | High (adopted) |
| Word-gap restriction and budget rule that remove word-end detection and saturation | none found as such; the R-value's over-segmentation correction and boundary F1 at matched counts are relatives | Matching counts before comparing | Restricting selection to word gaps and capping the budget below both sides' word counts so that monolingual segmentation scores zero | Medium-low (an instrument choice) |
| Consensus target and attenuation correction for aligner error | Och and Ney 2003 (intersection); Rogan-Gladen correction | High-precision combined alignments; correcting an apparent rate | Calibrated by simulation to published error rates with an error-correlation parameter, indexed by measured agreement | Medium-low |
| Line M as a monolingual syntactic reference at the treatment's budget | Fox 2002; When Tokenizers Fail (POS supervision) | Monolingual syntax predicts cross-lingual phrase structure | A guard that can relabel headroom as monolingually reachable | Medium-low |
| Later training stage: a translation-span boundary loss | SOMBRERO (loss on a boundary head); SMT bilingual segmentation; Conditional Unigram; MoE router alignment | Each half is published | Out of scope; the residual is the translation-span target on a learned byte head | Low-medium |

No method novelty is claimed. The decision value of the probe does not depend on
novelty; the instrument is an assembly of credited parts whose properties
(alignment sensitivity, rate and density robustness, word-end removal,
attenuation bounds) S1v2 checks.

Novelty wording: No direct prior art found through 2026-10-10 under the coverage
recorded in `evidence/2026-10-10-e3-byte-boundary-headroom/query-log.json`
(wave 1) and `query-log-run2.json` (this run) for measuring whether learned
byte-level boundaries fall at alignment-consistent split pairs across
translations at a common budget. That coverage is wave 1's 137 counted orx
discover calls, 11 OpenReview searches and full-text reads of every closest
prior, plus this run's 20 counted orx discover calls (R01-R20)
and 5 paper reads. This run's queries: R01 keyword "Chinese-English word alignment AER supervised" (returned 2608.18474, 2608.28508, 2605.28128, 2608.21023, ...); R02 keyword "BinaryAlign: Word Alignment as Binary Sequence Labeling" (returned 2407.12881, 2608.18474, 2610.11695, 2608.21023, ...); R03 openalex "maximum attainable kappa given marginal distributions kappa max Cohen" (returned 10.1007/s11336-022-09844-y, 2605.05428, 10.1007/s10342-020-01309-0, 10.1016/j.foreco.2013.12.032, ...); R04 openalex "bilingually motivated word segmentation statistical machine translation" (returned 10.1145/1526252.1526255, 10.3115/1609067.1609128, W2555559948, 10.1007/978-3-540-78135-6_38, ...); R05 openalex "phrasal cohesion and statistical machine translation" (returned 10.3115/1118693.1118732, 10.1162/tacl_a_00107, 10.3115/1220175.1220241, W2142632103, ...); R06 keyword "token alignability" --published-after 2025-03-01 (returned 2610.05816, 2609.35232, 2610.00575, 2609.12303, ...); R07 embedding "word alignment of subword tokens across translations measures tokenizer cross-lingual alignability and predicts transfer" --published-after 2025-03-01 (returned 2610.01921, 2608.27115, 2608.21023, 2608.18474, ...); R08 keyword "SOMBRERO boundary placement hierarchical sequence models" (returned 2601.22805, 2609.39749, 2610.09531, 2608.01150, ...); R09 embedding "selecting the same number of strongest word boundaries in a sentence and its translation and counting how many form alignment-consistent split points, corrected for chance, to test whether a byte-level model's learned chunk boundaries correspond across languages" (returned 2609.30167, 2610.03827, 2609.33691, 2609.13725, ...); R10 keyword "multilingual dynamic chunking byte-level model learned boundaries many languages released weights" --published-after 2026-05-01 (returned 2608.27658, 2610.01984, 2609.29828, 2605.30080, ...); R11 openalex "inversion transduction grammar empirical coverage word alignments binarizable translational equivalence" (returned 10.2478/pralin-2014-0003); R12 openalex "Stochastic inversion transduction grammars and bilingual parsing of parallel corpora" (returned W2158388102, 10.5555/972705.972707, W74075037, 10.63317/25hhw4ac87kw, ...); R13 openalex "Empirical lower bounds on the complexity of translational equivalence" (returned 10.3115/1220175.1220298, 10.3115/1626344.1626347, 10.1214/19-aos1876, W3109167026, ...); R14 openalex "Estimating prevalence from the results of a screening test Rogan Gladen" (returned 10.14709/barbj.15.1.2022.09, 10.3109/08958378.2014.955932, 10.1371/journal.pcbi.1012749, 10.1186/s12889-020-09177-4, ...); R15 embedding "manually annotated gold word alignment test set for English and Chinese, publicly available, used to evaluate neural word aligners" (returned 2608.18474, 2606.08673, 2603.15227, 2601.09648, ...); R16 keyword "Straight to the Tree: Constituency Parsing with Neural Syntactic Distance" (returned 2609.29855, 2608.27035, 2609.06070, 2610.11520, ...); R17 openalex "SOMBRERO: Measuring and Steering Boundary Placement in End-to-End Hierarchical Sequence Models" (returned 2601.22805, 10.34660/inf.2020.18.73.001, 10.34660/inf.2020.46.36.002, 10.34660/inf.2020.56.96.001, ...); R18 openalex "Beyond Literal Token Overlap: Token Alignability for Multilinguality" (returned 10.18653/v1/2025.naacl-short.63, 2502.06468, 10.18653/v1/2026.findings-acl.1632, 2406.17378, ...); R19 openalex "combining word alignments intersection union symmetrization high precision alignment" (returned 10.3115/1219840.1219897, 10.1162/coli.2007.33.3.293, 10.1162/089120103321337421, 10.3115/1220175.1220240, ...); R20 openalex "Optimizing Chinese word segmentation for machine translation performance" (returned 10.3115/1626394.1626430, W2188581170, 10.1007/978-3-642-37256-8_21, 10.1145/1526252.1526255, ...). Coverage limits
are in the header.

## Mechanism and Falsifiable Predictions

**Hypothesized mechanism.** A learned boundary head trained only by next-byte
loss and a per-language ratio target places its boundaries where monolingual
prediction changes. At stage 1 that is at or below the word level on both sides,
so every alignment-consistent split is already marked; at stage 2, which sets
where the main network spends compute, the head must choose among word gaps, and
nothing in its objective rewards choosing the gaps that correspond across a
translation. If this is right, the model's strongest word gaps at a budget of
half the words form consistent split pairs well below the oracle rate, and a
monolingual syntactic reference does not close the gap either; a translation-span
loss would then have a target. The competing account is that monolingual
predictability and phrase structure coincide across languages strongly enough
(phrasal cohesion) that the strongest learned boundaries already correspond.

**Predictions and falsifiers (FLORES+ devtest, registered numbers).**

- **P1, headroom.** The primary system's corrected S has an upper 90% bound below
  0.85 (S_hi on the band path, S* on the gold path). *Falsifier and kill
  criterion:* corrected S of at least 0.90 with a lower bound of at least 0.88
  (S_lo or S*) is NO_HEADROOM: E3 stops as scoped and the negative is recorded.
  Anything else is INDETERMINATE.
- **P2, translation-specificity (line M).** The monolingual syntactic reference's
  corrected S has an upper bound below 0.85. *Falsifier:* if it meets the
  NO_HEADROOM criterion, a HEADROOM on P1 becomes HEADROOM_MONOLINGUAL.
- **P3, instrument validity on real data.** Gates I1-I7 pass on FLORES+ dev
  (cut-count-preserving alignment sensitivity, random selections at zero,
  convention invariance, aligner agreement inside the band, budget and drop
  limits, completeness, estimator reproduction). *Falsifier:* any failure is
  INSTRUMENT_INVALID for the pair, recorded, with no repair inside this id.
- **P4, rate calibration is not placement.** The native-set statistic and the
  calibrated statistic differ, and native densities on word gaps are reported;
  reported, not a kill.
- **P5, the dossier's instrument.** The legacy UOT cost, run as a secondary on
  300 devtest pairs, fails alignment sensitivity as S1 predicted; reported, not a
  kill.

## Cheapest Decisive Pilot

The probe itself is the cheapest decisive step (caps 0.9 GPU-h) and trains
nothing:

1. **CPU, before any GPU:** port `e3_estimator_v2.py`, the canonicalization and
   the byte and word-gap mappings into `harness/` with unit tests (including the
   brute-force cross-check of the target), and pass I7 (reproduce S1v2's planted
   verdicts) as an orx `cpu-doctor` node.
2. **Host CPU:** build the v2 overlay (section 14 of the registration); fetch the
   three checkpoints, both aligners, the spaCy pipelines and FLORES+ with
   receipts (D1), after R2-R4 and R6.
3. **Smoke job (cap 0.2 GPU-h):** imports; `weights_only=True` loads;
   encoder-only stage-1 and stage-2 extraction on 64 synthetic byte strings,
   equal to a full upstream forward's masks; determinism; kill and resume; both
   aligners on 8 synthetic pairs.
4. **Probe job (cap 0.7 GPU-h):** scores on dev and devtest in four languages;
   aligners on the pairs (and on XL-WA en-zh if R5 is granted).
5. **Mac CPU, in a fixed order:** segmentation and parses; gates on dev; then the
   single devtest decision run from the frozen script.

What exists today is CPU design evidence, not a pilot: S1v2 (about 80
process runs on the development Mac, seeds 42/43/44) and S2v2. Neither is an orx
node, so the executable-pilot cap (79) applies.

## Controls, Baselines, and Ablations

All systems are scored by the same estimator on the same sentences and budgets:

- **Treatment:** H-Net hierarchical stage-2 scores (primary); stage-1 scores.
- **Floor:** random word gaps on both sides at the same budget (inside S);
  random-selection system (gate I2).
- **Alignment sensitivity:** cut-count-preserving transplant control (I1).
- **Monolingual references:** dependency-parse ranker (line M); punctuation-only
  ranker; the word-end-only system (equal scores on every word gap, S 0 by
  construction under v2).
- **Uncalibrated comparison:** native boundary sets (native-set form).
- **Tokenizer references:** OLMo-2 and Qwen3 tokenizers in the unrestricted form.
- **Same-model variants:** each EN-ZH model on both sides.
- **Instrument ablations (reported):** per-aligner targets against the
  consensus; monotone-only target; budget profile rho 0.25, 0.5, 0.75; second
  Chinese segmenter (jieba); stage 1 against stage 2; dev against devtest; band
  path against gold path when both are available.

## Evaluation, Statistics, and Leakage Checks

**Estimand.** S_true, the S of the primary system's selections under the true
alignment at the registered budget. Estimator: S_C on the consensus target,
corrected for attenuation (band path: S_lo = S_C / 0.97 for the kill and
S_hi = S_C / alpha_min(agreement) for headroom; gold path: S* = S_C / alpha_hat,
judged on S_C / (alpha_hat + 0.03) for the kill and S_C / (alpha_hat - 0.03) for
headroom, valid only if alpha_hat is at least 0.70).
Intervals: 90% percentile cluster bootstrap over FLORES+ documents, B = 2,000,
seed 42.

**Error model (S1v2 calibration).** Link-level AER against the true links,
sure links only, at 0.05-0.25, by dropping true links and adding spurious links
one or two words from the partner; balanced (precision about equal to recall),
precision-heavy and recall-heavy splits; correlation c between the two aligners'
error events from 0 to 1. At AER 0.085 the balanced split has precision 0.920 and
recall 0.911 (`compute/repair-run2/calib.json`).

**Attenuation (S1v2 attenuation map, seed 42, 500 pairs per cell;
`atten-consensus.json`, `atten-single-aligner.json`).** Alpha is the S of a
selection made exactly on true allowed pairs.

Consensus target, balanced errors: alpha_C (pair agreement). Columns are the two aligners' link AER.

| correlation c | 0.05/0.05 | 0.085/0.05 | 0.085/0.085 | 0.12/0.12 | 0.15/0.15 | 0.2/0.2 | 0.25/0.25 |
|---|---|---|---|---|---|---|---|
| 0.0 | 0.96 (0.77) | 0.94 (0.71) | 0.92 (0.66) | 0.89 (0.57) | 0.86 (0.50) | 0.80 (0.40) | 0.74 (0.34) |
| 0.25 | 0.94 (0.79) | 0.92 (0.72) | 0.90 (0.68) | 0.86 (0.59) | 0.84 (0.52) | 0.78 (0.42) | 0.73 (0.36) |
| 0.5 | 0.91 (0.82) | 0.90 (0.76) | 0.86 (0.73) | 0.81 (0.66) | 0.77 (0.59) | 0.70 (0.50) | 0.62 (0.42) |
| 0.75 |  |  | 0.78 (0.84) | 0.71 (0.77) | 0.66 (0.73) |  |  |
| 0.9 |  |  | 0.72 (0.92) | 0.64 (0.89) | 0.58 (0.87) |  |  |
| 1.0 | 0.79 (1.00) | 0.78 (0.91) | 0.68 (1.00) | 0.59 (1.00) | 0.54 (1.00) | 0.45 (1.00) | 0.39 (1.00) |

Other splits, correlations and profiles (consensus alpha_C, agreement; both aligners at the stated AER): ko balanced c 0.5 AER 0.15: 0.70 (0.54); pl balanced c 0.5 AER 0.15: 0.80 (0.64); zh precision heavy c 0.0 AER 0.05: 0.94 (0.80); zh precision heavy c 0.0 AER 0.15: 0.82 (0.56); zh precision heavy c 0.5 AER 0.15: 0.78 (0.63); zh recall heavy c 0.0 AER 0.05: 0.96 (0.75); zh recall heavy c 0.0 AER 0.15: 0.89 (0.46); zh recall heavy c 0.5 AER 0.15: 0.75 (0.56); zh recall heavy c 0.75 AER 0.085: 0.74 (0.81); zh recall heavy c 0.75 AER 0.12: 0.67 (0.75); zh recall heavy c 0.75 AER 0.15: 0.61 (0.69); zh recall heavy c 0.9 AER 0.085: 0.67 (0.91); zh recall heavy c 0.9 AER 0.12: 0.59 (0.88); zh recall heavy c 0.9 AER 0.15: 0.53 (0.85).

Single-aligner target (wave-1 style target from one aligner; alpha_A, balanced, c = 0): AER 0.05: 0.80, AER 0.085: 0.69, AER 0.12: 0.59, AER 0.15: 0.51, AER 0.2: 0.44, AER 0.25: 0.37; recall-heavy at AER 0.15: c 0.0: 0.46, c 1.0: 0.45.

Band constants (`band-registered.json`, by `band_envelope.py`): ALPHA_MAX 0.97
(largest consensus alpha with each AER at most 0.15, any c and split, rounded
up); alpha_min by measured pair agreement: below 0.55, 0.754; below 0.65, 0.651;
below 0.75, 0.576; below 0.85, 0.521 (each the worst band condition consistent
with that agreement, at recall-heavy errors with AER 0.15, rounded down);
agreement must lie in [0.448, 0.85).

**Operating characteristics (S1v2 OC; `oc-merged.json`, verdicts by
`oc_decide.py` from raw replicate statistics).** Conditions: aligner link AER 0.085 and 0.05 (the published rates) at c 0, 0.5
and 1 (seeds 42, 43, 44); AER 0.15 and 0.15 (the band edge) at c 0, 0.5 and 1
(seeds 42-44); AER 0.085/0.085 at c 0.25, 0.12/0.12 at c 0 and 0.5, 0.15/0.15
recall-heavy at c 0.5, 0.20/0.20 at c 0.5 and 0.25/0.25 at c 1 (seed 42). Each:
a population of 800 synthetic EN-ZH-like pairs (replicates draw 1,012 with
replacement), 100 replicates, 600 bootstrap resamples, floor with 32 draws per
sentence (64 in the registration; fewer draws only add Monte Carlo noise to the
floor), a gold population of 400 longer pairs (10 instead of 8 units on average)
from which 300 are drawn per replicate, post-stratified by length; for seed 42 at
the published rates and the band edge, gold samples with the aligners' AER
shifted by -0.03 and +0.03 against the test pairs. The first launch (populations
of 1,200) was stopped for time before any output and is not used. Verdicts are
recomputed from the stored replicate statistics with the registered constants by
`oc_decide.py`; tables (random displacement rows; adjacent-gap rows in
`oc-summary.md` behave the same) by `oc_summary.py`.

**G1: published rates (AER 0.085 and 0.05), c 0-0.5** (6 condition-seed runs)

| scenario system | mean S_true | band: P(NH) / P(H) / P(no verdict) | gold: P(NH) / P(H) / P(no verdict) |
|---|---:|---|---|
| random f = 0.0 | 1.00 | 1.00 / 0.00 / 0.00 | 1.00 / 0.00 / 0.00 |
| random f = 0.03 | 0.91 | 0.00 / 0.00 / 1.00 | 0.23 / 0.00 / 0.77 |
| random f = 0.06 | 0.84 | 0.00 / 0.00 / 1.00 | 0.00 / 0.01 / 0.99 |
| random f = 0.1 | 0.74 | 0.00 / 0.00 / 1.00 | 0.00 / 1.00 / 0.00 |
| random f = 0.15 | 0.62 | 0.00 / 0.00 / 1.00 | 0.00 / 1.00 / 0.00 |
| random f = 0.25 | 0.42 | 0.00 / 1.00 / 0.00 | 0.00 / 1.00 / 0.00 |
| random f = 0.4 | 0.18 | 0.00 / 1.00 / 0.00 | 0.00 / 1.00 / 0.00 |
| random f = 0.7 | -0.07 | 0.00 / 1.00 / 0.00 | 0.00 / 1.00 / 0.00 |

Summary: band path mean P(decisive) 0.509, mean P(correct) outside the tolerance zone 0.543, largest P(wrong decisive) 0.0; gold path 0.805, 0.859, 0.0. Gold sample with aligner AER shifted by +0.03 (seed 42 only): 0.842, 0.842, 0.01. Gold sample with aligner AER shifted by -0.03 (seed 42 only): 0.768, 0.768, 0.0.

**G2: published rates, identical errors (c 1)** (3 condition-seed runs)

| scenario system | mean S_true | band: P(NH) / P(H) / P(no verdict) | gold: P(NH) / P(H) / P(no verdict) |
|---|---:|---|---|
| random f = 0.0 | 1.00 | 0.00 / 0.00 / 1.00 | 1.00 / 0.00 / 0.00 |
| random f = 0.03 | 0.91 | 0.00 / 0.00 / 1.00 | 0.21 / 0.00 / 0.79 |
| random f = 0.06 | 0.83 | 0.00 / 0.00 / 1.00 | 0.00 / 0.02 / 0.98 |
| random f = 0.1 | 0.73 | 0.00 / 0.00 / 1.00 | 0.00 / 1.00 / 0.00 |
| random f = 0.15 | 0.62 | 0.00 / 0.00 / 1.00 | 0.00 / 1.00 / 0.00 |
| random f = 0.25 | 0.42 | 0.00 / 0.00 / 1.00 | 0.00 / 1.00 / 0.00 |
| random f = 0.4 | 0.18 | 0.00 / 0.00 / 1.00 | 0.00 / 1.00 / 0.00 |
| random f = 0.7 | -0.07 | 0.00 / 0.00 / 1.00 | 0.00 / 1.00 / 0.00 |

Summary: band path mean P(decisive) 0.0, mean P(correct) outside the tolerance zone 0.0, largest P(wrong decisive) 0.0; gold path 0.78, 0.832, 0.0. Gold sample with aligner AER shifted by +0.03 (seed 42 only): 0.054, 0.053, 0.02. Gold sample with aligner AER shifted by -0.03 (seed 42 only): 0.769, 0.769, 0.0.

**G3: band (AER 0.085-0.15), c 0-0.5** (10 condition-seed runs)

| scenario system | mean S_true | band: P(NH) / P(H) / P(no verdict) | gold: P(NH) / P(H) / P(no verdict) |
|---|---:|---|---|
| random f = 0.0 | 1.00 | 0.23 / 0.00 / 0.77 | 1.00 / 0.00 / 0.00 |
| random f = 0.03 | 0.92 | 0.00 / 0.00 / 1.00 | 0.16 / 0.00 / 0.84 |
| random f = 0.06 | 0.85 | 0.00 / 0.00 / 1.00 | 0.00 / 0.00 / 1.00 |
| random f = 0.1 | 0.75 | 0.00 / 0.11 / 0.89 | 0.00 / 0.99 / 0.01 |
| random f = 0.15 | 0.63 | 0.00 / 0.77 / 0.23 | 0.00 / 1.00 / 0.00 |
| random f = 0.25 | 0.44 | 0.00 / 1.00 / 0.00 | 0.00 / 1.00 / 0.00 |
| random f = 0.4 | 0.21 | 0.00 / 1.00 / 0.00 | 0.00 / 1.00 / 0.00 |
| random f = 0.7 | -0.03 | 0.00 / 1.00 / 0.00 | 0.00 / 1.00 / 0.00 |

Summary: band path mean P(decisive) 0.502, mean P(correct) outside the tolerance zone 0.535, largest P(wrong decisive) 0.0; gold path 0.765, 0.816, 0.0. Gold sample with aligner AER shifted by +0.03 (seed 42 only): 0.522, 0.553, 0.005. Gold sample with aligner AER shifted by -0.03 (seed 42 only): 0.753, 0.802, 0.0.

**G4: band edge (AER 0.15), identical errors (c 1)** (3 condition-seed runs)

| scenario system | mean S_true | band: P(NH) / P(H) / P(no verdict) | gold: P(NH) / P(H) / P(no verdict) |
|---|---:|---|---|
| random f = 0.0 | 1.00 | 0.00 / 0.00 / 1.00 | 0.00 / 0.00 / 1.00 |
| random f = 0.03 | 0.92 | 0.00 / 0.00 / 1.00 | 0.00 / 0.00 / 1.00 |
| random f = 0.06 | 0.84 | 0.00 / 0.00 / 1.00 | 0.00 / 0.00 / 1.00 |
| random f = 0.1 | 0.74 | 0.00 / 0.00 / 1.00 | 0.00 / 0.00 / 1.00 |
| random f = 0.15 | 0.63 | 0.00 / 0.00 / 1.00 | 0.00 / 0.00 / 1.00 |
| random f = 0.25 | 0.43 | 0.00 / 0.00 / 1.00 | 0.00 / 0.00 / 1.00 |
| random f = 0.4 | 0.19 | 0.00 / 0.00 / 1.00 | 0.00 / 0.00 / 1.00 |
| random f = 0.7 | -0.05 | 0.00 / 0.00 / 1.00 | 0.00 / 0.00 / 1.00 |

Summary: band path mean P(decisive) 0.0, mean P(correct) outside the tolerance zone 0.0, largest P(wrong decisive) 0.0; gold path 0.0, 0.0, 0.0. Gold sample with aligner AER shifted by +0.03 (seed 42 only): 0.0, 0.0, 0.0. Gold sample with aligner AER shifted by -0.03 (seed 42 only): 0.0, 0.0, 0.0.

**G5: beyond the band (AER 0.20 at c 0.5; 0.25 at c 1)** (2 condition-seed runs)

| scenario system | mean S_true | band: P(NH) / P(H) / P(no verdict) | gold: P(NH) / P(H) / P(no verdict) |
|---|---:|---|---|
| random f = 0.0 | 1.00 | 0.00 / 0.00 / 1.00 | 0.41 / 0.00 / 0.58 |
| random f = 0.03 | 0.92 | 0.00 / 0.04 / 0.95 | 0.00 / 0.00 / 1.00 |
| random f = 0.06 | 0.85 | 0.00 / 0.50 / 0.50 | 0.00 / 0.01 / 0.98 |
| random f = 0.1 | 0.76 | 0.00 / 0.50 / 0.50 | 0.00 / 0.46 / 0.54 |
| random f = 0.15 | 0.63 | 0.00 / 0.50 / 0.50 | 0.00 / 0.46 / 0.54 |
| random f = 0.25 | 0.45 | 0.00 / 0.50 / 0.50 | 0.00 / 0.46 / 0.54 |
| random f = 0.4 | 0.22 | 0.00 / 0.50 / 0.50 | 0.00 / 0.46 / 0.54 |
| random f = 0.7 | -0.02 | 0.00 / 0.50 / 0.50 | 0.00 / 0.46 / 0.54 |

Summary: band path mean P(decisive) 0.376, mean P(correct) outside the tolerance zone 0.367, largest P(wrong decisive) 0.045; gold path 0.323, 0.344, 0.0.

**Multiplicity.** One primary quantity on one pair and one stage, on one target;
line M is a guard that can only relabel HEADROOM. Every secondary is reported
without a verdict.

**Leakage and researcher degrees of freedom.** Nothing is trained. The
instrument's choices (segmenters, aligners and settings, consensus rule, budget
fraction, floor draws, band constants, lines, the stage-2 score definition) are
fixed in the registration and tuned on nothing real; the band constants and
lines come from S1v2 before any data. dev is read only for gates; the devtest
decision runs once from a frozen script. FLORES passages may be in FineWeb-Edu
(disclosed); memorization could lower surprisal and move boundary rates, but the
budget is set per sentence by word counts and target size, not by the model's
rate, so a rate shift between dev and devtest cannot move the budget.

**Missing data.** Pairs with no consistent split under the consensus target, a
segmentation failure or no links are dropped and counted; more than 2% is
INSTRUMENT_INVALID (I6). S1v2: no synthetic pair had k = 0.

## Compute and Reproducibility

- Base image: `127.0.0.1:5000/cotcodec-research@sha256:13a9de831cff50461d8ecee3c2794f0c6d6bcffe9d602968fe2ee06e5a1096e9`
  (CUDA 12.8.1 cudnn-devel base). The probe needs a separate overlay environment
  (registration section 14): Python 3.12, torch 2.7.1+cu128, flash-attn
  2.8.0.post2 (torch 2.7 wheel), mamba_ssm a6a1dae and causal_conv1d e940ead from
  source, transformers 4.57.1, hnet 3673fe12, plus the aligners' and spaCy's
  pinned packages. Its digest is pinned after the host CPU build and before
  freeze. The pins were checked statically against the pinned source files and
  release assets (C57-C63); nothing was built.
- Launch: the smoke and probe jobs each through
  `scripts/submit_docker_research_job.py` (dry run, test-only, then submit),
  which wraps `sbatch infra/slurm/host-single-node/docker-research.sbatch` with a
  filled manifest; one GPU each; network off inside the container.
- seeds: [42, 43, 44] (bootstrap, floor draws, tie keys and oracle draws use 42
  for the decision; 43 and 44 repeat the stochastic parts and the range is
  reported).
- gpu_hours: 0.9 (sum of registered caps under D22: smoke 0.2 plus probe 0.7;
  S2v2 central 0.26, high 0.63 with full-forward FLOPs at 20 TFLOPS; the probe
  cap is 1.11 times the high estimate).
- Precision and determinism: bf16 (the checkpoints' dtype), router probabilities
  recomputed in fp32; two smoke runs bit-identical.
- Encoder-only extraction: the driver composes the upstream encoder, router and
  chunk modules and never runs the main network or decoders; the smoke checks the
  masks against a full forward.
- Checkpoints and outputs: per-checkpoint score files and aligner files written
  atomically with SHA-256; a killed job resumes by skipping verified files.
- Artifacts: aggregates, hashes and code to the public repository; scores,
  alignments and sentence-level files to the private archive only.
- Simulation reproducibility: S1v2 is seeded; every process's argv, input
  hashes and outputs are in `compute/repair-run2/` (README lists the commands).
- Cost ceiling: 0.9 GPU-h; a job reaching its cap is killed and recorded as
  INCOMPLETE, with no extension under this registration.

## Safety, Data Rights, and Monitorability

- **Data.** FLORES+ is CC-BY-SA-4.0 behind an automatic click-through whose terms
  forbid crawler-reachable re-hosting and training use; accepting it and a read
  token are Kevin's (R2). XL-WA en-zh (optional) is CC BY-NC-SA 4.0 and obtained
  on request, an outward action (R5). The public repository receives aggregates,
  revisions and hashes only: no sentence text, no per-sentence scores, links or
  alignments. Belebele is not used to get around the gate.
- **Q3 overlap.** Q3 never reads 366 of Belebele's 488 passages, which are FLORES
  text; whether E3 may read those sentences is reserved sign-off R1.
- **Models and code.** H-Net weights declare no licence (R4; not
  publication-eligible). BinaryAlign is CC BY-NC-ND 4.0: non-commercial research
  inference, no redistribution, aggregates only (R6). OmniAlign is Apache-2.0
  but its model card executes custom modelling code; that code, hnet, mamba-ssm,
  causal-conv1d, flash-attn and BinaryAlign's code count as trusted inputs only
  after sign-off R3 (D7, D29: human-written library code, not code produced during
  an experiment). spaCy pipelines are MIT.
- **Untrusted code.** H-Net checkpoints are pickles: `weights_only=True` in a
  network-off container, failing closed. No model-generated code runs on GPUs.
- **Host rule.** No host job ran for this repair (no ssh at all). The probe's jobs
  run only after a freeze and only while no Q2 job runs.
- **Monitorability and misuse.** A boundary-correspondence measurement has no
  direct misuse path; nothing is trained or deployed.

## Negative-Result Value

- **NO_HEADROOM** stops E3 for 0.9 GPU-h of caps instead of the corpus,
  evaluation set, loss and training code Stage 1 needs, with a scoped record:
  independently trained learned-boundary predictors already correspond across
  EN-ZH translations at a compute-relevant budget.
- **HEADROOM_MONOLINGUAL** redirects boundary work to monolingual syntactic
  supervision (When Tokenizers Fail's control) and removes E3's translation
  delta.
- **HEADROOM** licenses only building Stage 1's prerequisites, and hands Stage 1
  a measured shortfall and the monolingual reference's share of it as its effect
  prior. Correspondence headroom did not predict downstream gains in the nearest
  prior (C16), so Stage 1 must test its downstream endpoint directly.
- **INSTRUMENT_INVALID** bounds what any translation-span loss could be trained
  against on this pair (the aligners cannot certify correspondence) and documents
  where the instrument fails on real data.
- **Recorded either way:** S1 (wave 1: the dossier's UOT instrument cannot
  decide) and S1v2 (a single aligner's consistency target loses about 0.3 of S at
  the published zh-en error rates; a two-family consensus keeps most of it) are
  methods results for anyone scoring segmentation against word alignments.

## Preflight Doctors

| Doctor | Status | Evidence | Remediation |
|---|---|---|---|
| Source | PASS | orx 0.2.2 reachable from the Mac; 20 counted queries this run with raw-output SHA-256 in query-log-run2.json; GitHub, Hugging Face, OpenAlex and raw-file reads logged; TsinghuaAligner HTTP 502 recorded; degraded coverage listed in the header and doctors/source.json | Semantic Scholar forward citations of 2502.06468 and 2601.22805 through the host relay when the host is free |
| Citation | PASS | Claim registry C01-C74 with locators and read depth; new claims for the aligners' published error rates, the pinned upstream code and the classical lineages; first-party numbers labelled; doctors/citation.json | Read Cohen 1960 and Rogan and Gladen 1978 in full when accessible |
| Novelty | FAIL | NARROWED; no direct prior for measuring learned byte boundaries against alignment-consistent split pairs; kappa_M, the SMT segmentation lineage and ITG lineage now credited; the blind critic and the novelty refuter of this run have not run (doctors/novelty.json) | Run the blind critic on both fresh packets and the refute-first triad |
| Design | FAIL | Estimator as code, gates and decision rule with simulated operating characteristics at the published error rates (S1v2); but every number is synthetic, the band path rests on an AER assumption, and the estimator is not yet in harness/ (doctors/design.json) | Port the estimator with unit tests as an orx cpu-doctor node passing I7; pre-freeze audit; R5 for the gold path |
| Compute | FAIL | No overlay, fetched weights, smoke, Slurm dry run or compute attestation; the stack is fixed only statically; caps 0.9 GPU-h from S2v2 (doctors/compute.json) | Build the overlay and run the smoke as an orx slurm-manifest node after freeze approval |
| Safety | PASS | FLORES+ and XL-WA terms, public-repo hygiene, pickle handling, BinaryAlign NC-ND, OmniAlign remote code and trusted-input sign-off, Q3 overlap disclosed (doctors/safety.json) | none beyond reserved sign-offs R1-R6 |

## Independent Adversarial Reviews

Reviewer A: NOT_RUN | provider=anthropic (planned, Claude subagent through the agent harness under D25) | model=not yet assigned | run_id=none | artifact=none

Reviewer B: NOT_RUN | provider=open-weight self-hosted (planned, the reviewer lane job on the idle host) | model=not yet assigned | run_id=none | artifact=none

Wave 1's reviews (52 and 57), blind critic and refuters are in the first row of
`program/gauntlet/2026-10-10-e3-byte-boundary-headroom.jsonl`. This run's blind
critic (one call per prior packet: token alignability and SOMBRERO), triad and
reviewers run after this repair; no trusted Ed25519 store exists, so no review
can be signed (D24).

## Scorecard

| Dimension | Reviewer A | Reviewer B | Defect/evidence |
|---|---:|---:|---|
| Question and strategic fit | 0 | 0 | not yet reviewed in this run (wave 1: 6 and 8) |
| Primary-source evidence | 0 | 0 | not yet reviewed in this run (wave 1: 7 and 7) |
| Defensible novelty delta | 0 | 0 | not yet reviewed in this run (wave 1: 4 and 4) |
| Mechanism and falsifiability | 0 | 0 | not yet reviewed in this run (wave 1: 4 and 7) |
| Controls and causal identification | 0 | 0 | not yet reviewed in this run (wave 1: 3 and 5) |
| Evaluation and statistics | 0 | 0 | not yet reviewed in this run (wave 1: 4 and 7) |
| Feasibility and information per GPU-hour | 0 | 0 | not yet reviewed in this run (wave 1: 5 and 5) |
| Reproducibility and artifact contract | 0 | 0 | not yet reviewed in this run (wave 1: 6 and 2) |
| Safety, data rights, and monitorability | 0 | 0 | not yet reviewed in this run (wave 1: 8 and 7) |
| Independent adversarial review quality | 0 | 0 | not yet reviewed in this run (wave 1: 5 and 5) |
| **Total** | **0** | **0** | Lower total is authoritative |

## Iteration Log

| Wave | Score | Highest-impact defect | Change | Result |
|---:|---:|---|---|---|
| 1 | 52 (52 and 57) | Identification at the operating point: dense Chinese stage-1 side, collapsing one-sided floor, S driven by density and English word-end misses; then NO_HEADROOM unreachable at published aligner error and a stack that could not import | Wave-1 synthesis: PBD with a circular-shift floor and a budget-matched ceiling; rule from S1 at small, independent aligner noise | Honest exit (query budget; triad 0 of 3); D68 ordered one repair run |
| 2 (repair, before review) | not scored | (wave-1 defects, rows 1-11 above) | Common word-gap budget with top-k selection, two-sided random floor, straight and inverted split pairs, two-family consensus target, error model at published rates, band and gold attenuation paths, monolingual syntactic line M, bf16 and a working stack, scoped kill, credited lineages | Awaiting the blind critic, the triad and both reviewers; D60's stop line applies |

The evidence bundle follows `program/proposals/evidence/_schema.json`. Source
snapshots, both query logs, doctor outputs and simulation outputs live below the
bundle directory with their SHA-256 hashes. No review receipt, compute
attestation or audit row for this run exists yet (D24), so the deterministic
doctor reports FAIL.
