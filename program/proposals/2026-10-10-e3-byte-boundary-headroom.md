# Research Direction: E3 Stage-0 headroom probe, cross-lingual boundary correspondence of released learned-boundary byte models against rate calibration (backfill E3, legacy direction 18)

**Status:** draft for gauntlet wave 1 (program decision D67); synthesis by the single owner on 2026-10-10 from four independent discovery cells (frontier, kill-shot, cross-domain, asset and cost) of workflow gauntlet-e3-wave1; the blind closest-prior critic, the refute-first triad and the two provider-distinct reviewers have not run; the registration `program/preregistrations/e3-byte-boundary-headroom-v1.md` is a DRAFT, not frozen or admitted, with no ledger row; no executable pilot exists for this probe; a score of 100 cannot be certified in this repository (D24)
**Owner:** Kevin Liu (program owner); synthesis, mechanism statement, identification design, simulations and draft registration written by a Claude agent acting as the gauntlet's single synthesis owner
**Source cutoff:** 2026-10-10
**Coverage limits:** orx 0.2.2 only for literature search (alphaXiv keyword and embedding search, OpenAlex; the build reports itself outdated against 0.2.18; alphaXiv indexing lags by 2 to 3 days, newest ids seen 2610.12xxx); 118 counted orx discover calls by the cells (frontier 62, kill-shot 24, cross-domain 27, asset 5; two failed with OpenAlex HTTP 429) and none by synthesis; 11 OpenReview API searches and one failed note fetch (note pages returned a 403 browser challenge, so every OpenReview item is abstract-only, UNVERIFIABLE_ACCESS for full text); 5 web searches, 1 web fetch and read-only Hugging Face, GitHub, Nature and ACL Anthology metadata reads; arXiv abstract pages and version histories through arxiv.org and export.arxiv.org; full texts read by targeted section, not end to end; not searched: Semantic Scholar and the arXiv API (unreachable from the development Mac; the host relay was not used), citation-graph traversal beyond OpenAlex, patents, X, Reddit, Hacker News, Chinese- and Korean-language venues; the ACL Anthology only through OpenAlex DOIs and two direct pages (EMNLP 2026 proceedings are not yet in the Anthology, so EMNLP 2026 acceptances are self-reported arXiv comments); classical statistics and neuroscience sources partly at abstract or title level (listed in the claim registry); no FLORES+ text, checkpoint or aligner was downloaded or run, so every statement about real data is metadata-based and every number about the instrument comes from synthetic simulation.
**Budgets:** queries=150; wall_minutes=600; tokens=8000000; dollars=150; waves=3; gpu_hours=0.3
**Novelty verdict:** NO_DIRECT_PRIOR_FOUND
**Safety verdict:** PASS
**Evidence bundle:** evidence/2026-10-10-e3-byte-boundary-headroom/bundle.json

The novelty verdict field uses the doctor's vocabulary. The merged discovery
verdict is NARROWED (frontier, kill-shot and cross-domain cells; none returned
OCCUPIED), and narrower than the dossier stated: an auxiliary loss on a learned
byte-boundary head is published (SOMBRERO, steering toward next-byte surprisal),
translation-supervised segmentation is published for subword tokenizers
(Conditional Unigram Tokenization), translation-supervised alignment of discrete
compute-allocation decisions is published for MoE routers, and a FLORES-200
segmentation-correspondence measure is published for subword tokenizers (token
alignability). This proposal claims no method novelty. Its residual is a
measurement on released learned-boundary byte models, with a chance-corrected,
budget-matched instrument, read as a go or no-go for E3's later training stage.

The gauntlet's GPU budget (0.3 GPU-h) is for reviewer inference only. The
probe's own compute (registered caps summing to 0.8 GPU-h under D22) is separate
and runs only after a freeze. No host job was run for this proposal; synthesis
made one read-only `squeue` (empty queue, 21:22 UTC).

## Scope and what changed from the dossier

This proposal covers only E3's Stage 0 headroom probe: aligned-span boundary
correspondence on FLORES+ for released byte-level checkpoints, as the dossier
states (`program/evidence/2026-10-06/question-dossier.md`, section 11). It
trains nothing. The Stage 1 screen (about 16 GPU-h, four arms by three seeds at
about 40M parameters) is out of scope and needs its own gauntlet, plus the four
prerequisites the dossier names (a licensed parallel corpus, a terminology and
tool-schema evaluation set, a differentiable torch loss, H-Net-style training
code), none of which exists.

"D18" in E3's name is legacy direction 18
(`legacy/directions/18-translation-equivariant-byte-boundaries.md`), not
decision D18 in `program/decisions.md`, which is a serving-probe decision.

The four cells were merged by mechanism, not wording. Seventeen mechanisms
change the probe as the dossier wrote it. Each was re-checked by synthesis
against a primary source, by simulation S1 (`compute/instrument_sim.py`,
synthetic pairs, seeds 42, 43 and 44), by a re-run of the legacy doctor, or by
more than one of these.

| # | Mechanism (cells that found it) | What it does to the dossier's probe | Where handled |
|---:|---|---|---|
| M1 | **The dossier's instrument is nearly blind to the alignment.** The legacy UOT evaluator transports boundary mass inside each linked span with span-normalized positions, so with word-level links every span pair holding one edge boundary costs zero whichever span it is linked to. Kill-shot toy demo: aligned over permuted loss 0.88 to 1.04 for every rule, 0.91 to 0.96 for the oracle. S1 reproduces it on 240 synthetic pairs: 0.86 to 1.02 for every system, and 0.94 to 1.00 for the perfect-correspondence system, against the legacy doctor's own gate of 0.80 | The UOT cost is demoted to a registered secondary that cannot decide. The primary instrument is a projected boundary Dice (PBD) over consistent cuts of the alignment, which S1 shows is alignment-sensitive by construction (permuted-alignment PBD at most 0.027 against 0.82 to 0.91 for the true-cut system) | S1 parts 1-2; registration section 7 |
| M2 | **The UOT loss is rate-confounded and its ceiling is circular** (cross-domain cell: random boundaries' loss falls about 3x from rate 0.05 to 0.5; the aligner-span oracle scores 0 by construction). S1: with budget-matched floors and ceilings, normalized UOT is undefined (ceiling not below floor) in 10 of 24 ZH-like cells and ranges from -3.00 to 9.64 on PL-like cells; the perfect-correspondence system scores worse (loss 0.35 to 0.41) than boundaries at every word gap (0.19 to 0.24) | The decision quantity is S = (D - D_floor) / (D_ceiling - D_floor) on PBD, with a rate- and spacing-preserving floor (circular shift within the sentence) and a ceiling at the system's own per-sentence boundary budget. S1: Bernoulli boundaries give absolute S at most 0.019 at every rate from 0.05 to 0.5 in all three profiles and seeds | S1 part 1; registration section 7 |
| M3 | **The span-edge double penalty and the one-byte convention hazard** (cross-domain cell: one side shifted by one byte scores 0.44, worse than count-matched random 0.32; kill-shot: a chunk-start convention raises loss from 0.10 to 0.86 to 0.95). S1: a chunk-start convention on one side raises the UOT loss 1.06 to 3.97 times on PL-like pairs | Every boundary is snapped to a canonical character gap (whitespace runs collapsed, a boundary inside a multi-byte character moved to the character's start) before scoring. S1: the round trip through either convention is the identity on every pair, and S does not move (difference 0.0000) | S1 part 1 convention gate; registration section 5 |
| M4 | **Bolmo-1B's boundaries are its tokenizer's** (kill-shot and frontier cells; synthesis re-read Bolmo Sec. 3.2.1: the predictor "quickly achieves" more than 99% accuracy emulating subword patch ends; the boundary loss is kept in Stage 2; 2608.03599 reports Bolmo barely differs from the OLMo tokenizer, without numbers) | The Bolmo GPU arm is replaced by its source tokenizer (OLMo-2) on CPU, and Bwen-8B by its source tokenizer (Qwen3) on CPU, as tokenizer references. No Bolmo forward pass is run; the residual between Bolmo and its tokenizer is not measured, which is disclosed | Controls; registration section 3 |
| M5 | **Every released H-Net is monolingual** (all four cells; synthesis read the goombalab/hnet README): English FineWeb-Edu for L and XL, Chinese FineWeb-Edu-Chinese-V2.1 for `hnet_2stage_XL_chinese`. No released Korean, Polish or multilingual learned-boundary checkpoint was found (asset cell's Hugging Face scan and orx queries a1, a2) | The decision pair is EN-ZH, with an in-distribution model on each side (English 2-stage XL on English, Chinese 2-stage XL on Chinese). EN-KO and EN-PL run the English model out of distribution and are descriptive only. Same-model-both-sides variants of EN-ZH are reported. The claim is scoped to these released monolingual checkpoints and does not transfer to a multilingual model trained from scratch | Claim; registration sections 1 and 3 |
| M6 | **Orthography and UTF-8 width dominate raw scores** (kill-shot: one whitespace rule scores 0.105, 0.147 and 0.439 on EN-PL, EN-KO and EN-ZH; H-Net's fixed byte-ratio target makes Chinese stage-1 chunks about one character) | Results are reported per pair only, never as a cross-pair macro; S is normalized at each system's own budget per pair; per-script raw rates are reported beside S | Evaluation |
| M7 | **The metric can be reached by monolingual segmentation** (kill-shot: the score measures each side's agreement with the aligner's monolingual span edges). S1: in the synthetic world, boundaries at every monolingual word gap reach S of 0.99 to 1.00 at their own budget | A guard line M: a word-segmentation reference (whitespace words, eojeol, a Chinese word segmenter) is scored at its own budget. If its S is at least 0.90, any headroom is relabelled monolingually reachable and is not evidence for a translation-specific delta | Registration "Line M" |
| M8 | **Aligner spans cannot be validated on two of three pairs** (kill-shot, cross-domain, asset cells: OmniAlign reports zh-en AER 8.5 but ja-en 29.6 and has no ko-en or pl-en gold; CTFAlign has gold for en-zh but not ko or pl; XL-WA's en-ko and en-zh sets are on request under CC BY-NC-SA 4.0; no en-pl gold found) | Two aligners from different families (CTFAlign with LaBSE; SimAlign with XLM-R) must agree on the verdict; an inter-aligner cut-agreement gate sets whether a verdict is allowed. S1 shows aligner noise, not sampling, drives the decision error: S under the aligner's own ceiling is attenuated by about 0.02 at cut agreement 0.88 and about 0.06 at 0.77 | S1 part 3; registration sections 6, 8 and 10 |
| M9 | **The headroom ratio needs a defined normalization** (all cells: the dossier's 90% line has none; under the floor-to-ceiling reading on UOT it never fires) | The line is registered on S with numbers chosen from S1's operating characteristics (Evaluation section): NO_HEADROOM needs a point estimate of at least 0.88 and a lower 90% bound of at least 0.85 under both aligners; HEADROOM needs an upper 90% bound below 0.85 (below 0.80 when the aligners' cut agreement is between 0.75 and 0.85); no verdict below agreement 0.75 | S1 part 3; registration section 10 |
| M10 | **Token alignability already measures segmentation correspondence on FLORES-200 for subword tokenizers** (frontier, kill-shot and cross-domain cells; synthesis re-read Sec. 3.2) | It is the closest prior for the measurement. Its one-to-one share is reported raw as a secondary; S1 shows its budget-normalized form is ill-conditioned (values from -0.18 to 13.96), so it cannot be the decision quantity | Closest Prior Work; S1 part 1 |
| M11 | **An auxiliary loss on a learned byte-boundary head is published** (frontier cell: SOMBRERO; synthesis re-read Secs. 3.4-3.5) | The training-stage residual narrows to the translation-span target itself. SOMBRERO's rate-matched circular-shift null is adopted as the floor | Closest Prior Work; Normalization |
| M12 | **Chance correction at matched rate is a solved problem elsewhere** (cross-domain cell: the spike time tiling coefficient, rate leakage of Victor-Purpura distances, the R-value, the point-adjust artefact and affiliation metrics, unbalanced-OT forecast verification's mass versus transport split, gamma's shuffle-corrected agreement, regioneR's lag profile) | The floor is spacing-preserving; the ceiling is budget-matched; native versus rate-calibrated S separates what equalizing the budget fixes from placement; a lag profile is a registered secondary | Evaluation |
| M13 | **Data rights and gating** (asset, frontier and kill-shot cells; synthesis read the dataset API): FLORES+ is CC-BY-SA-4.0, gated by an automatic click-through whose terms forbid crawler-reachable re-hosting and training use; revision e707e62e of 2026-10-01 differs from the legacy pin; Belebele carries the same passages and Q3 seals 366 of its 488 passages | Accepting the gate is Kevin's action. The public repository receives aggregates and hashes only; no sentence text, per-sentence boundary or alignment file. Belebele is not used to get around the gate. The Q3 overlap is disclosed and a reserved sign-off | Safety |
| M14 | **No pinned image runs H-Net, and its weights are pickles** (asset cell; synthesis checked uv.lock: no mamba, causal-conv1d, flash-attn or xlstm entries; upstream `generate.py` loads with `weights_only=False`) | A new overlay on the pinned research image (host CPU build), `torch.load(weights_only=True)` in a network-off container failing closed, and a sign-off that the pinned upstream H-Net and Mamba code is a trusted input under D7 and D29 | Compute |
| M15 | **Cost** (asset cell, rebuilt as S2 `compute/cost_model.py`): three checkpoints, overhead-dominated, no host throughput measured | Caps: smoke 0.2 GPU-h plus probe 0.6 GPU-h, sum 0.8 GPU-h under D22; central estimate 0.26 GPU-h, high 0.56 | Compute |
| M16 | **Correspondence headroom does not imply downstream benefit** (kill-shot: Conditional Unigram's parallel-supervised segmentation gave no MT gain; parallel-data share barely moves representation alignment, 2603.29026; NMT-learned segmentation converges to characters, 1810.01480) | A HEADROOM verdict licenses only building Stage 1's prerequisites, not training or any claim about terminology or tool-schema exactness | Negative-Result Value |
| M17 | **The legacy evaluator only runs from its legacy path** (asset cell; synthesis re-ran the doctor on 2026-10-10: REFERENCE_OBJECTIVE_DOCTOR_PASS, payload SHA-256 6d8c24be..., identical to the 2026-08-10 output) | Restoring it into `harness/` and `scripts/` with a fresh doctor output is a prerequisite for the UOT secondary. A passing legacy doctor does not establish validity at word-level link granularity (its permuted case is hand-built; M1) | Compute |

Six corrections to the frozen dossier, recorded here because the dossier is not
edited:

1. "The existing NumPy UOT cost as an evaluator": as specified it fails
   alignment sensitivity, rate robustness and convention invariance in S1 (M1 to
   M3), so it cannot decide; it stays a secondary.
2. "Bolmo-1B boundaries": an arm equivalent to the OLMo-2 tokenizer up to a
   residual that Bolmo's paper reports only as per-byte accuracy (M4).
3. "Released H-Net checkpoints" on EN-KO and EN-PL: out of distribution (M5).
4. "At least 90% of the correspondence ceiling": no normalization was defined;
   the registered line is on S with simulated operating characteristics (M9).
5. "Frozen aligner spans": unvalidated for Korean and Polish (M8).
6. "Bolmo's non-causal predictor conflicts with the causal-head requirement":
   true for Stage 1's training contract; irrelevant to a Stage 0 measurement.

## Claim and Research Question

**Question.** On FLORES+ devtest (revision `e707e62e`, 1,012 sentences per
language), for released learned-boundary byte-level language models, how much
of the cross-lingual boundary correspondence achievable at a matched boundary
budget do rate-calibrated boundaries already reach, and is any shortfall
translation-specific?

- **Decision pair:** English-Chinese (Simplified), with the English 2-stage XL
  H-Net reading English and the Chinese 2-stage XL H-Net reading Chinese, stage-1
  boundaries primary and stage-2 secondary.
- **Descriptive pairs:** English-Korean and English-Polish with the English model
  on both sides (out of distribution on the non-English side), and English-Chinese
  with one model on both sides.
- **Variable:** the boundary source (native H-Net, rate-calibrated H-Net,
  tokenizer references, word segmentation, every character gap, random at
  matched rate).

**Primary quantity.** S_rate, the normalized projected boundary Dice of the
rate-calibrated boundaries on EN-ZH devtest, under each of two aligners, with a
90% sentence-cluster bootstrap interval.

**Claim scope.** A measurement on released monolingual checkpoints. Not
`architecture-causal`, not a method claim, and no claim about terminology,
tool-schema exactness or bits per byte. It can license only "E3's Stage 1
prerequisites are (not) worth building" or "E3 stops with a recorded negative".

**Hypothesis under test (H_room).** On EN-ZH, the upper 90% bound of S_rate is
below the registered HEADROOM line under both aligners, and the word-segmentation
reference's S is below 0.90 (headroom that monolingual segmentation does not
already reach). The registered kill is the dossier's: if rate-calibrated
boundaries already reach the budget-matched ceiling (point estimate at least
0.88 and lower bound at least 0.85 under both aligners), E3 stops.

## Strategic Fit and Why Now

E3 is item 6 of the backfill queue (`program/backlog.md`). D67 restarted every
remaining line after Q2 S1a's result (D66). E3's first step is the cheapest
item in the queue (caps sum to 0.8 GPU-h) and gates a large, expensive build:
the parallel corpus, the evaluation set, the torch loss and the training code
that Stage 1 needs. A no-headroom verdict saves that build; a headroom verdict
says it has a measured target.

Why now:

- The substrates moved. Bolmo now has a Nature version (2026-10-07) and
  byteified 8B models (Bwen-8B from Qwen3, Blama-8B from Llama 3), whose
  boundaries are distilled from their source tokenizers; those tokenizers are
  CPU-computable references for the first time at multilingual-tokenizer scale.
- The neighbours moved. SOMBRERO (2026-01-30) published a boundary-steering
  loss and a null-calibrated boundary metric; cross-lingual MoE router alignment
  (2026-10-01) published translation-supervised alignment of discrete
  compute-allocation decisions; the Multi-Level Transformer and B-Net
  submissions (ICLR 2027 cycle) report learned boundaries that converge on
  tokenizer-like positions. A measurement of whether learned byte boundaries
  already correspond across translations is the missing piece between them.
- The instrument problem is now understood. Three cells independently found
  that the dossier's instrument cannot decide (M1 to M3), and S1 gives a
  replacement with measured gates and operating characteristics, before any GPU
  is spent.

## Primary-Source Evidence

Claim registry (ARS claim-verification protocol: claim, source, locator, read
depth, status). Read depth: F = full text read by targeted section; S = re-read
by synthesis; A = abstract or search payload only; M = metadata or API record;
R = repository evidence; X = first-party (single source, unreplicated).

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

## Closest Prior Work

| Work | What it does | Delta from this probe |
|---|---|---|
| Token alignability ([2502.06468](https://arxiv.org/abs/2502.06468); NAACL 2025) | Runs a statistical aligner on subword-tokenized FLORES-200 and reports the one-to-one token share and the aligner score as tokenizer-quality metrics that predict transfer | Closest prior for the measurement. It measures a shared subword vocabulary with no rate correction, no chance floor and no ceiling. This probe measures learned byte boundaries with a frozen word alignment projected onto them, normalized at each system's own budget, and splits budget equalization from placement |
| SOMBRERO ([2601.22805](https://arxiv.org/abs/2601.22805)) | Auxiliary confidence-alignment loss on an H-Net-style chunker, plus boundary enrichment against a rate-matched circular-shift null | Closest prior for the training mechanism's form (a loss on a learned boundary head) and for the floor. Its target is monolingual next-byte surprisal; E3's target is translation-aligned spans |
| MAGNET ([2407.08818](https://arxiv.org/abs/2407.08818)) | Per-script boundary priors for parity across nine languages | Owns parity by rate calibration. This probe asks what remains after rate calibration, and MAGNET covers none of ZH, KO or PL |
| When Tokenizers Fail ([2608.27658](https://arxiv.org/abs/2608.27658)) | Monolingual boundary supervision (POS and frozen subword targets) on byte chunking | Owns monolingual supervision; line M tests whether monolingual segmentation already reaches the ceiling |
| Conditional Unigram Tokenization ([2507.07824](https://arxiv.org/abs/2507.07824)) | Parallel-data-supervised subword segmentation | Translation-supervised segmentation exists for subwords with mixed results; E3's residual is a learned byte head, and this probe trains nothing |
| Cross-lingual MoE router alignment ([2610.01921](https://arxiv.org/abs/2610.01921)) | Translation-supervised alignment of sequence-pooled expert routing | The nearest translation-supervised compute-allocation loss; span-level boundary placement in a byte model is not sequence-pooled routing |
| CAROT ([2609.06381](https://arxiv.org/abs/2609.06381)) | Unbalanced OT over parallel hidden states at fixed boundaries | Owns state alignment; no boundary term |
| Disentangling Language Modeling and Boundaries ([2608.03599](https://arxiv.org/abs/2608.03599)) | Position paper: boundary divergence as 1 - F1; boundaries retrainable with the LM fixed | Untested proposals; its metric is not chance-corrected or budget-matched |
| Bolmo ([2512.15586](https://arxiv.org/abs/2512.15586); Nature 2026) and H-Net ([2507.07955](https://arxiv.org/abs/2507.07955)) | Tokenizer-distilled non-causal boundaries; end-to-end learned chunk starts | Substrates and references, not competitors |

Other relevant work: B-Net and the Multi-Level Transformer (rate control and
tokenizer-like convergence, abstracts only), 2608.17325 (per-language H-Nets
favour long tokens), 2610.11790 (placement at fixed rate changes exactness,
first-party), H-Net++ (morphology tracking), 2610.05978 (implicit segmentation),
Parallel Tokenizers (vocabulary level), 1810.01480 and 2603.29026 (null priors
for translation pressure on segmentation and alignment).

## Novelty Ledger

| Proposed component | Closest prior | Same | Delta | Confidence |
|---|---|---|---|---|
| Segmentation correspondence across translations measured on FLORES | Token alignability (2502.06468) | Measures how well two languages' units correspond on FLORES with a word aligner | Learned byte boundaries rather than a subword vocabulary; a frozen word alignment projected onto boundaries rather than an aligner run on the units | High that the measurement idea is shared; medium that the delta is worth a paper |
| Chance correction by a rate-matched circular-shift null | SOMBRERO (2601.22805), regioneR, event coincidence analysis | Spacing-preserving shift null | Applied to cross-lingual cut agreement, not to surprisal enrichment | High (adopted, not claimed) |
| Budget-matched ceiling and the split of native against rate-calibrated S | Forecast verification's mass versus transport split (2412.16063); R-value (2009) | Separates frequency bias from displacement | Applied to translation boundary correspondence with an aligner-defined ceiling | Medium |
| Projected boundary Dice over consistent cuts | Boundary F1 and boundary divergence 1 - F1 (2608.03599); phrase-pair consistency from phrase-based MT | Boundary agreement counts | Agreement across translations through alignment-consistent cuts, with canonical character gaps that remove the one-byte convention | Medium |
| Headroom question for learned byte boundaries beyond rate calibration | MAGNET (parity); When Tokenizers Fail (monolingual supervision); MLT and B-Net (convergence and rate control) | Rate calibration and monolingual supervision of byte boundaries | Whether placement beyond rate corresponds across translations, with a monolingual guard line | Medium |
| Later training stage: a translation-span boundary loss | SOMBRERO (loss on a boundary head); MoE router alignment (translation-supervised allocation); Conditional Unigram (translation-supervised subword segmentation) | Each half is published | Out of scope; residual narrowed to the translation-span target on a learned byte head | Medium |

Novelty wording: No direct prior art found through 2026-10-10 under the
coverage recorded in `evidence/2026-10-10-e3-byte-boundary-headroom/query-log.json`
for either (a) measuring aligned-span boundary correspondence of learned
byte-level boundaries across translations or (b) supervising a learned
byte-level boundary head with translation-aligned spans. That coverage is 118
counted orx discover calls (74 keyword, 21 embedding, 23 OpenAlex, two of which
failed with HTTP 429), 11 OpenReview API searches, 5 web searches, and full-text
reads of every closest prior (each read with `orx paper --full` by at least one
cell, and the five gate priors re-read by synthesis). Representative queries:
keyword "translation supervised boundaries byte-level language model"
(returned 2608.15454, 2609.00463, 2610.05978, 2608.03599, ...); keyword
"Improving the Multilingual Fairness of Language Models with Adaptive
Gradient-Based Tokenization" (2407.08818 among the top ten); keyword
"Cross-Lingual Representation Alignment by Token-Level Optimal Transport in a
Language-Agnostic Space" (2609.06381 first); keyword "SOMBRERO boundary
placement hierarchical sequence models" (2601.22805 first); keyword "token
alignability multilinguality literal token overlap" (2502.06468 first);
embedding "auxiliary loss that pushes the learned chunk boundaries of a
hierarchical tokenizer-free byte-level language model onto corresponding spans
of translation pairs using word alignments" (2610.01921, 2608.27658, ...,
2601.22805); embedding "measuring whether learned dynamic chunk boundaries of
byte-level language models correspond across translations of the same
sentence" (no direct match in 15); OpenAlex "cross-lingual consistent
tokenization parallel data" (2507.07824 first). Every query and every returned
id is in the query log. Coverage limits are in the header.

## Mechanism and Falsifiable Predictions

**Hypothesized mechanism.** A learned boundary head trained only by next-byte
loss and a per-language ratio target places boundaries where monolingual
prediction changes: at whitespace and word onsets in English, and roughly every
character in Chinese (C03, C04). Across a translation, such boundaries
correspond only where monolingual units happen to coincide with
alignment-consistent cuts. Rate calibration (per-language thresholds that
equalize chunks per sentence) fixes the budget mismatch but cannot move a
boundary onto an aligned cut that the monolingual signal does not mark. If this
is right, rate-calibrated boundaries fall measurably short of the
budget-matched ceiling, and the shortfall is not closed by monolingual word
segmentation either; a translation-span boundary loss would then have a target.
The competing account (null) is that once budgets are equal, learned boundaries
already sit near the ceiling, because learned boundaries converge on
tokenizer-like units (C07, C10, C19) and word units mostly align one to one.

**Predictions and falsifiers (all on FLORES+ devtest, registered numbers).**

- **P1, headroom.** On EN-ZH stage-1 boundaries, the upper 90% bound of S_rate is
  below the HEADROOM line (0.85 when the two aligners' cut agreement is at least
  0.85; 0.80 when it is in [0.75, 0.85)) under both aligners. *Falsifier and kill
  criterion:* point S_rate of at least 0.88 with a lower 90% bound of at least
  0.85 under both aligners is NO_HEADROOM: E3 stops and the negative is
  recorded. Anything else is INDETERMINATE (no verdict either way).
- **P2, translation-specificity (line M).** The word-segmentation reference
  (whitespace words for English; a pinned Chinese word segmenter) has S below
  0.90 at its own budget under both aligners. *Falsifier:* S of at least 0.90
  relabels a P1 HEADROOM as HEADROOM_MONOLINGUAL: the shortfall is reachable by
  monolingual supervision, the existing control's territory, and is not
  evidence for E3's translation delta.
- **P3, rate calibration helps but does not finish.** S_rate exceeds S_native on
  EN-ZH (equalizing budgets removes count mismatch). *Falsifier:* S_rate not
  above S_native means the native budgets were already matched or calibration
  is mis-specified; reported, not a kill.
- **P4, instrument validity on real data.** On FLORES+ dev, the registered
  instrument gates I1 to I6 pass (registration): alignment sensitivity, rate
  robustness of Bernoulli boundaries at the systems' own rates, convention
  invariance, aligner agreement, achieved rate matching, and no in-character
  boundary left after canonicalization. *Falsifier:* any gate failing is
  INSTRUMENT_INVALID for the affected pair: no verdict, recorded, and no repair
  inside this registration.
- **P5, the dossier's instrument.** The legacy UOT cost, run as a registered
  secondary on a 300-pair devtest subset per pair, fails alignment sensitivity
  (aligned over permuted loss above 0.80 for the rate-calibrated system), as S1
  predicts. *Falsifier:* a ratio at or below 0.80 on real data would show the
  defect is synthetic-only; reported, and it would not change the decision.

## Cheapest Decisive Pilot

The decisive experiment is the probe itself, because it is already the
cheapest step (caps 0.8 GPU-h) and trains nothing:

1. **CPU, before any GPU:** restore the evaluator and the new PBD scorer into
   `harness/` with unit tests on hand-built cases (both conventions, multi-byte
   characters, crossing alignments, unaligned tokens); run S1's gates against the
   restored code as an orx `cpu-doctor` node.
2. **Host CPU:** build the H-Net overlay image; fetch the three checkpoints at
   pinned revisions with full receipts (D1).
3. **Smoke job (cap 0.2 GPU-h):** imports, `weights_only=True` loads of all three
   checkpoints, a forward pass of the 2-stage XL model on 64 synthetic byte
   strings (no FLORES text), a determinism check and a kill-and-resume check.
4. **Probe job (cap 0.6 GPU-h):** boundary probabilities of the three
   checkpoints on FLORES+ dev and devtest in four languages, and both aligners on
   the three pairs, written as per-checkpoint files with hashes.
5. **Mac CPU analysis, in a fixed order:** instrument gates I1 to I6 on dev;
   rate-calibration thresholds fitted on dev; only then the devtest decision
   (one scripted run, no re-runs with changed settings).

What exists today is CPU design evidence, not a pilot: S1
(`compute/instrument_sim.py`, 31 process runs totalling about 89 CPU-minutes, at most 5.6 minutes of wall time each, on the development Mac) and S2
(`compute/cost_model.py`). Neither is an orx node, so the executable-pilot cap
(79) applies.

## Controls, Baselines, and Ablations

Boundary systems, all scored by the same instrument on the same sentences:

- **Treatment-side systems (H-Net):** native boundaries (the code's argmax rule)
  and rate-calibrated boundaries (English threshold fixed at the native rule;
  the Chinese threshold fitted on dev so mean chunks per sentence match English;
  a symmetric variant fitting both sides to the pair's geometric-mean count as a
  sensitivity), at stage 1 (primary) and stage 2.
- **Floors:** the circular-shift null (20 shifts per sentence, seed 42), and a
  permuted-alignment control (side-b token indices relabelled before cutting).
- **Random at matched rate:** Bernoulli boundaries at each H-Net system's
  per-side rate (instrument gate I2).
- **Monolingual references:** word segmentation (English whitespace words with
  punctuation split; Chinese by a pinned segmenter), every character gap.
- **Tokenizer references (CPU):** OLMo-2's tokenizer (Bolmo-1B's source), Qwen3's
  tokenizer (Bwen-8B's source), at their own budgets. They emit hard boundaries
  with no probability, so they have no rate-calibrated version.
- **Same-model variants:** English H-Net on both EN-ZH sides; Chinese H-Net on
  both EN-ZH sides.
- **Secondaries that cannot decide:** the legacy UOT cost (300-pair subset);
  the raw one-to-one chunk share (token alignability's form); a lag profile
  (side b shifted by -3 to +3 canonical gaps); boundary similarity B.

Ablations of the instrument (reported): self against cross-fit ceilings, the
two aligners separately, stage 1 against stage 2, dev against devtest.

## Evaluation, Statistics, and Leakage Checks

**Estimand.** S_rate on EN-ZH devtest, stage 1, computed from pooled per-sentence
counts (cut hits on both sides, boundaries per side, floor hits, ceiling hits)
under aligner A and under aligner B, each with its own self ceiling.

**Intervals.** 90% percentile intervals from a cluster bootstrap over FLORES+
source documents when the release carries a document identifier, otherwise over
sentences (disclosed), B = 2,000, seed 42. Floors and ceilings are resampled
with the system (same sentences).

**Operating characteristics (S1 part 3).** Synthetic EN-ZH-like, PL-like and
KO-like pools of 5,000 pairs, 1,012 pairs drawn per replicate, 200 replicates
per cell and seed, B = 1,000, seeds 42, 43, 44. True S was varied by displacing
a fraction of a perfect system's side-b boundaries. Sampling error is small:
the standard deviation of the S estimate is 0.002 to 0.007 at 1,012 pairs, so
the decision risk is the attenuation of S under aligner noise, which grows as
the two aligners' cut agreement falls.

Probability of each verdict under the registered rule, means over seeds 42, 43
and 44 (NH = NO_HEADROOM, H = HEADROOM, I = INDETERMINATE, INV =
INSTRUMENT_INVALID). Columns are true S (scored against the generative truth);
rows are synthetic profiles and aligner-noise levels with the resulting
inter-aligner cut agreement (Dice).

| Profile, noise (cut agreement) | true S about 0.97 | about 0.93 | about 0.90 | about 0.86 | about 0.83 | about 0.76 |
|---|---|---|---|---|---|---|
| ZH-like, low (0.935) | NH 1.00 | NH 1.00 | NH 0.97, I 0.03 (true 0.897) | I 1.00 | H 1.00 | H 1.00 |
| ZH-like, base (0.877) | NH 1.00 | NH 1.00 | I 0.97, NH 0.03 (true 0.897) | H 0.44, I 0.56 | H 1.00 | H 1.00 |
| PL-like, base (0.793) | NH 1.00 | NH 1.00 (0.932 and 0.910) | I 0.83, NH 0.17 (true 0.887) | I 1.00 (true 0.842) | no grid point | H 1.00 (true 0.776) |
| ZH-like, high (0.770) | NH 1.00 | I 0.99, NH 0.01 | I 1.00 | I 0.99, H 0.01 | H 1.00 | H 1.00 |
| KO-like, base (0.720) | INV 1.00 | INV 1.00 | INV 1.00 | INV 1.00 | INV 1.00 | INV 1.00 |
| KO-like, high (0.531) | INV 1.00 | INV 1.00 | INV 1.00 | INV 1.00 | INV 1.00 | INV 1.00 |

Read-out:

- **HEADROOM is never declared when true S is 0.90 or more** in any condition.
- **The only wrong-side calls are NO_HEADROOM with true S between 0.887 and
  0.90**: probability 0.97 at true 0.897 with low aligner noise, 0.17 at true
  0.887 (PL-like) and 0.03 at true 0.897 (ZH-like, base). The registered line
  therefore tolerates up to 0.013 below the dossier's 0.90, disclosed.
- **The dossier-literal rule** (NO_HEADROOM at a point estimate of at least 0.90
  with a lower bound of at least 0.85; HEADROOM at an upper bound below 0.90)
  declares HEADROOM wrongly with probability 1.00 at true S 0.933 (ZH-like, high
  noise) and 1.00 at true 0.921 (KO-like, high noise), because aligner noise
  attenuates S. This is why the registered rule moves the lines and adds the
  agreement gate.
- **Korean-like pairs give no verdict** at the simulated agreement levels
  (0.53 to 0.72), consistent with EN-KO being descriptive.
- These are synthetic profiles with assumed aligner noise; the real
  inter-aligner agreement is measured on dev (gate I4) before any verdict.

The per-condition values, the first operating-characteristics run (superseded)
and every intermediate file are in `compute/instrument-sim.json`.

**Multiplicity.** One primary quantity on one pair and one stage; the verdict
needs both aligners. Stage 2, the descriptive pairs, the references and every
secondary are reported without verdicts.

**Leakage and researcher degrees of freedom.** Nothing is trained, so there is
no train-test leakage. The degrees of freedom are instrument choices: every one
(canonicalization, the cut rule, the budget rule, the shift count, the
thresholds, the aligners and their settings, the Chinese segmenter, the
calibration target) is fixed in the registration and tuned on nothing; the
calibration thresholds are fitted on dev only; the devtest analysis runs once
from a frozen script whose digest is in the ledger row. Memorization of FLORES
by the checkpoints cannot change a boundary-correspondence measurement's
validity in a way that favours either verdict, but FLORES passages may be in
FineWeb-Edu; this is disclosed.

**Missing data.** Sentences on which an aligner returns no links, or which have
no consistent cut, are counted and dropped from that aligner's pooled counts;
if more than 2% of devtest pairs drop for either aligner, the pair is
INSTRUMENT_INVALID.

## Compute and Reproducibility

- Base image: `127.0.0.1:5000/cotcodec-research@sha256:13a9de831cff50461d8ecee3c2794f0c6d6bcffe9d602968fe2ee06e5a1096e9`
  (the pinned architecture image used by the E4 and C3 registrations; torch
  2.11.0+cu128, triton 3.6.0, transformers 5.15.0). The probe needs an overlay
  with the hnet package at commit 3673fe12, mamba-ssm, causal-conv1d and
  flash-attn at the versions upstream pins; its digest is pinned after the host
  CPU build and before freeze.
- Launch: the smoke and probe jobs each go through
  `scripts/submit_docker_research_job.py` (dry run, test-only, then submit),
  which wraps `sbatch infra/slurm/host-single-node/docker-research.sbatch` with a
  filled manifest; one GPU each; network off inside the container.
- seeds: [42, 43, 44] (bootstrap seed 42; circular shifts and oracle draws use
  42, with 43 and 44 as registered replications of the stochastic parts of the
  instrument, reported as a range).
- gpu_hours: 0.8 (sum of registered caps under D22: smoke 0.2 plus probe 0.6;
  central estimate 0.26, high 0.56, S2).
- Checkpoints and outputs: per-checkpoint boundary files and aligner files are
  written atomically to the persistent run directory with SHA-256; a killed job
  resumes by skipping files whose hashes verify; the smoke tests this.
- Artifacts: aggregates, hashes and the code to the public repository; boundary,
  alignment and sentence-level files to the private archive only.
- Determinism: fp32 with TF32 disabled for the boundary computation; the smoke
  requires two runs to agree bit for bit on the synthetic batch.
- Cost ceiling: 0.8 GPU-h; a job reaching its cap is killed and recorded as
  INCOMPLETE, with no extension under this registration.

## Safety, Data Rights, and Monitorability

- **Data.** FLORES+ is CC-BY-SA-4.0 behind an automatic click-through whose terms
  forbid re-hosting where crawlers can reach it and use as training data.
  Accepting it, and creating a read token, is Kevin's action. This repository is
  public, so it receives aggregates, revisions and hashes only: no sentence
  text, no per-sentence boundary or alignment file, nothing from which sentences
  could be reconstructed. Belebele, which carries the same passages ungated, is
  not used to get around the gate.
- **Q3 overlap.** Q3 never reads 366 of Belebele's 488 passages (C47), and those
  passages are FLORES text. E3 trains nothing and reports aggregates, and its
  pipeline writes no sentence text to logs; whether E3 may read those sentences
  at all is a reserved sign-off for Kevin.
- **Models.** H-Net weights declare no licence, so they are recorded with an
  undeclared licence and are not publication-eligible; nothing derived from them
  is released beyond aggregates. Bolmo and Bwen are used only through their
  source tokenizers (Apache-2.0).
- **Untrusted code.** H-Net checkpoints are pickles: they are loaded with
  `weights_only=True` in a network-off container and the job fails closed on any
  load error. The pinned upstream H-Net, Mamba, causal-conv and flash-attn code
  is human-written library code, not code produced during an experiment; that it
  counts as a trusted input under D7 and D29 is a reserved sign-off. No
  model-generated code runs on GPUs.
- **Host rule.** No host job ran for this proposal. The probe's jobs run only
  after a freeze and only while no Q2 job runs.
- **Monitorability and misuse.** A boundary-correspondence measurement has no
  direct misuse path; no model is trained or deployed.

## Negative-Result Value

- **NO_HEADROOM** kills E3 at 0.8 GPU-h of caps instead of the corpus,
  evaluation set, loss and training code that Stage 1 needs, and is reportable
  as a measured negative: once budgets are equal, released learned byte
  boundaries already correspond across EN-ZH translations near the ceiling.
- **HEADROOM_MONOLINGUAL** redirects any boundary work to monolingual
  supervision (2608.27658's control) and removes E3's translation delta.
- **INSTRUMENT_INVALID** is still informative: it says the aligners cannot
  certify correspondence for that pair, which bounds any later translation-span
  loss on that pair, and it documents the failure of the dossier's UOT
  instrument on real data.
- **Recorded either way:** S1's finding that the dossier's instrument cannot
  decide (M1 to M3) stands as a methods result for anyone measuring boundary
  correspondence across languages.
- **HEADROOM** licenses only building Stage 1's prerequisites; correspondence
  headroom did not predict downstream gains in the nearest prior (C16), so
  Stage 1's own gauntlet must test the downstream endpoint directly.

## Preflight Doctors

| Doctor | Status | Evidence | Remediation |
|---|---|---|---|
| Source | PASS | orx 0.2.2 (alphaXiv keyword and embedding, OpenAlex) reachable from the Mac; arXiv abstract pages, Hugging Face and GitHub APIs and aclanthology.org reachable; 118 counted orx discover calls with returned ids and raw-output SHA-256 in query-log.json; OpenReview limited to search payloads; degraded coverage listed (doctors/source.json) | After the host is quiet, Semantic Scholar forward citations for 2502.06468 and 2601.22805 through the host relay |
| Citation | PASS | Claim registry C01 to C52 with locators and read depth; every cited primary URL snapshotted (snapshots/); first-party numbers labelled; four OpenReview items UNVERIFIABLE_ACCESS for full text (doctors/citation.json) | Read the Bolmo Supplementary and the ICLR 2027 submissions when accessible |
| Novelty | FAIL | NARROWED from three cells; no direct prior for the measurement on learned byte boundaries; blind critic and novelty refuter not run (doctors/novelty.json) | Run the blind critic on blind/ and the refute-first triad |
| Design | FAIL | Instrument gates, decision rule and line M registered with simulated operating characteristics (S1); but all evidence is synthetic, the scorer is not yet in harness/, and the aligners' real agreement is unknown (doctors/design.json) | Restore the scorer with unit tests as an orx cpu-doctor node; pre-freeze audit |
| Compute | FAIL | No overlay image, no fetched weights, no smoke, no Slurm dry run, no compute attestation; caps 0.8 GPU-h from S2 (doctors/compute.json) | Build the overlay and fetch on host CPU after freeze approval; dry run; smoke as an orx slurm-manifest node |
| Safety | PASS | FLORES+ licence and gate, public-repo hygiene, pickle handling, trusted-code sign-off, Q3 overlap disclosed (doctors/safety.json) | none beyond the reserved sign-offs |

## Independent Adversarial Reviews

Reviewer A: NOT_RUN | provider=anthropic (planned, Claude subagent through the agent harness under D25) | model=not yet assigned | run_id=none | artifact=none

Reviewer B: NOT_RUN | provider=open-weight self-hosted (planned, the reviewer lane job on the idle host) | model=not yet assigned | run_id=none | artifact=none

The blind closest-prior critic, the refute-first triad and both reviewers run
after this synthesis. Their outputs, prompts and hashes go into the evidence
bundle and the wave row; no trusted Ed25519 store exists, so neither review can
be signed (D24).

## Scorecard

| Dimension | Reviewer A | Reviewer B | Defect/evidence |
|---|---:|---:|---|
| Question and strategic fit | 0 | 0 | not yet reviewed (wave 1 synthesis only) |
| Primary-source evidence | 0 | 0 | not yet reviewed (wave 1 synthesis only) |
| Defensible novelty delta | 0 | 0 | not yet reviewed (wave 1 synthesis only) |
| Mechanism and falsifiability | 0 | 0 | not yet reviewed (wave 1 synthesis only) |
| Controls and causal identification | 0 | 0 | not yet reviewed (wave 1 synthesis only) |
| Evaluation and statistics | 0 | 0 | not yet reviewed (wave 1 synthesis only) |
| Feasibility and information per GPU-hour | 0 | 0 | not yet reviewed (wave 1 synthesis only) |
| Reproducibility and artifact contract | 0 | 0 | not yet reviewed (wave 1 synthesis only) |
| Safety, data rights, and monitorability | 0 | 0 | not yet reviewed (wave 1 synthesis only) |
| Independent adversarial review quality | 0 | 0 | not yet reviewed (wave 1 synthesis only) |
| **Total** | **0** | **0** | Lower total is authoritative |

## Iteration Log

| Wave | Score | Highest-impact defect | Change | Result |
|---:|---:|---|---|---|
| 1 (synthesis) | not scored | The dossier's instrument cannot decide: alignment-blind, rate-confounded, convention-fragile, with a circular ceiling and an undefined 90% normalization (M1 to M3, M9) | Primary instrument replaced by projected boundary Dice with a spacing-preserving floor and a budget-matched ceiling; decision rule and aligner-agreement gate chosen from simulated operating characteristics; Bolmo replaced by its tokenizer; decision pair narrowed to EN-ZH; line M added | Awaiting the blind critic, the triad and both reviewers |

The evidence bundle follows `program/proposals/evidence/_schema.json`. All
source snapshots, the query log, doctor outputs and simulation outputs live
below the bundle directory with their SHA-256 hashes. Review receipts and the
hash-chained audit row do not exist yet (D24), and no compute attestation
exists, so the deterministic doctor reports FAIL.
