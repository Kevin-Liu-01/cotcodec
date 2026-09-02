# Inventor A — translation-supervised compute allocation (2026-09-01)

Angle: parallel translations as a training VIEW that supervises where/how compute is spent
(boundaries, routing, depth, experts, attention span, indexers) — beyond Direction 18's boundary
transport. Targets synthesis gaps G2, G13, G19, G20 (plus seq-operators G1, tokenizer-free G3,
learned-update-rules G4 as supporting cell gaps).

Inputs read in full: context.md, design/brief.md, sweep/synthesis.md (all sections), the gap/occupied
sections of seq-operators.md, tokenizer-free-multilingual.md, learned-update-rules.md,
benchmarks-eval.md, bookmarks.md, killshot-current.md (D18 section), arxiv-triage-arch.md (adaptive
depth/routing rows), the repo's directions/18-*.md (including the 2026-09-01 kill-shot update that
landed while I was reading), experiments/architectures/translation-equivariant-byte-patches.yaml,
research/frontier-systems-program-2026-08-10.md ("occupies" and "Rejected" tables), models/registry.yaml.

Honesty rules applied: no "completely novel"; every prior below has a URL and a date; "opened" means I
read the arXiv abstract page through WebFetch on 2026-09-01; first-party status is noted; coverage
limits are in §5.

Organizing idea shared by all three candidates: every modern LM contains discrete or soft
*compute-allocation devices* — patch boundaries (D18), the forgetting/writing gates of delta-rule
state, the top-k selector of a learned sparse indexer, the expert router. All of them are clocked and
trained per token, and token counts for the same meaning differ by 1.5–9x across languages (fertility;
Vowel Signs 2608.26449 gives a training-free 1.47x–9.02x floor on 17 abugidas). Parallel translations
are the only instrument that holds meaning fixed while surface changes, so they let us (a) *measure*
whether each device allocates by meaning or by surface and (b) *supervise* it toward meaning without
touching the tokenizer. Leino & Tiedemann (2603.29026, opened) show parallel data barely moves
*representation* alignment; none of the candidates below targets representations — each targets a
compute-allocation statistic (gate mass, selection distribution, routing distribution), which is a
different observable, and each pre-registers "extends 2603.29026 to allocation" as its negative.

---

## Candidate 1 (cheap-decisive) — `semantic-clock-decay-parity`

**Claim.** In Gated-DeltaNet/KDA layers, forgetting (decay) and writing (beta) are applied once per
token, so the same content costs a high-fertility language proportionally more state capacity and
proportionally faster forgetting; a parallel-translation training view that equalizes the cumulative
log-decay and write mass over aligned spans ("semantic clock") removes this inequity and equalizes
translation-paired recall across scripts at unchanged bits per byte, with no change to the inference
architecture.

**claim_scope.** architecture-causal (phase 0 is a frozen-checkpoint *measurement*, not a claim; the
causal claim needs the matched from-scratch arms in phase 1).

**Mechanism.** Gated DeltaNet state (transformers `qwen3_next` parameterization, lines 719–721 of
`modeling_qwen3_next.py`, confirmed 2026-09-01):
`S_t = alpha_t * S_{t-1} * (I - beta_t * k_t k_t^T) + beta_t * v_t k_t^T`, with
`log alpha_t = g_t = -exp(A_log) * softplus(a_t + dt_bias)` (one scalar per head in GDN; a vector per
channel in KDA) and `beta_t = sigmoid(b_t)`. For an aligned span `s` (sentence or phrase link from a
frozen aligner such as OmniAlign 2608.18474 / CTFAlign 2608.21023) define the *forgetting mass*
`F(s) = -sum_{t in s} g_t` (nats of decay applied to everything stored before `s`) and the *write mass*
`W(s) = sum_{t in s} beta_t`. Under per-token clocks `F(s_b)/F(s_a) ~ |s_b|/|s_a|` = the fertility
ratio, so content stored before a Thai paragraph is forgotten up to several times faster (in semantic
time) than before its English translation. The semantic-clock view adds, on parallel-view batches (both
translations present, each processed monolingually; the loss couples them only through span sums):
`L = L_LM + lambda_F * sum_{(s_a,s_b)} sum_{layers,heads} (F(s_a) - F(s_b))^2 / (F(s_a) + F(s_b) + eps)
     + lambda_W * sum_{(s_a,s_b)} sum_{layers,heads} (W(s_a) - W(s_b))^2 / (W(s_a) + W(s_b) + eps)`.
For KDA the per-head `F` is a vector over channels and the numerator is a squared Euclidean distance.
Only the gate projections (`a_t`, `b_t`, `A_log`, `dt_bias`) receive the auxiliary gradient; the loss
uses span-level sums only (no cross-position or cross-language attention), so it is causal by
construction and vanishes at inference. Expected resolution: the LM loss decides whether parity is met by
slowing per-token forgetting in high-fertility tokens (alpha -> 1) or speeding it elsewhere.
Two monolingual-proxy arms are part of the design: (i) an *information clock*
`g_t' = g_t * stopgrad(h(x_t) / h_bar)` with `h(x_t)` the surprisal of `x_t` under a frozen small LM
(BLT's entropy-model idea applied to decay rather than patching), and (ii) a static *fertility-scaled
gate* `g_t' = g_t / f_L` using an oracle language ID (the MAGNET-style per-script analogue). If either
matches the parallel view, the *view* is unnecessary but the *finding* stands.

**what_is_new (delta vs closest priors, each opened 2026-09-01).**
- Gated DeltaNet, https://arxiv.org/abs/2412.06464 (2024-12-09; ICLR 2025): gates trained by the LM
  loss only, clocked per token; no per-language analysis. Ours supervises the cumulative gate statistics
  per semantic unit and changes nothing at inference.
- Kimi Linear / KDA, https://arxiv.org/abs/2510.26692 (2025-10-30; first-party): channel-wise decay in a
  3:1 production hybrid; no per-language analysis. Ours measures and equalizes its channel-wise
  forgetting mass across translations.
- Liquid Gated Attention, https://arxiv.org/abs/2608.30695 (2026-08-31): decay gating driven by observed
  time intervals for irregular time series (no language modeling). Ours supplies the unobserved
  "semantic interval" for text through the translation view, at training time only.
- MAGNET, https://arxiv.org/abs/2407.08818 (2024-07-11): per-script boundary predictors for equitable
  segmentation granularity. Ours leaves segmentation fixed and enforces parity inside the recurrent
  operator's forgetting/writing per meaning.
- Adaptive Memory Decay for Log-Linear Attention, https://arxiv.org/abs/2605.06946 (2026-05-07):
  content-adaptive per-level decay from a small MLP (monolingual). Ours constrains cumulative decay
  across translations rather than enriching the decay function.
- Leino & Tiedemann, https://arxiv.org/abs/2603.29026 (2026-03-30): parallel data barely moves
  representation alignment. Ours targets gate statistics, a different observable; a nil result is
  pre-registered as extending their negative to allocation.
Occupancy note: axis C of the synthesis ("delta-rule gate geometry — closed for one more gate") is not
re-proposed: no new gate, no new architecture; the delta is a supervision view over existing gates plus
the language-controlled instrument seq-operators G1 says nobody has built.

**falsifiable_predictions.**
- P1 (phase 0, released checkpoints, ~1.5 GPU-hours): on Qwen3.5-0.8B-Base (rev dc7cdfe2ee4154fa7e30f5b51ca41bfa40174e68, to register), startlux gdn-340m-isp-hybrid-3to1-10b and gdn-1.3b-isp-hybrid-3to1-50b (2608.12149 controls), and kimi-linear-48b-a3b-base (registered; custom-code review pending), the per-sentence forgetting-mass ratio DPR(L) = F_L / F_en on 2,000 aligned NTREX-128 sentences is >= 0.8 x fertility ratio f_L for every language with f_L >= 1.5 (the models do not self-normalize). If DPR(L) <= 1.15 for all such languages, the mechanism has nothing to fix — kill before any training.
- P2 (phase 1, 100M pure-GDN from scratch, 6 languages at equal bytes): translation-paired recall (keys stored in language A, queried after 8 sentences of *matched content* distractors) differs by >= 10 exact-match points between the highest- and lowest-fertility language at baseline; the semantic-clock arm cuts this gap to <= 4 points with per-language BPB within +1% of baseline.
- P3 (identification arm): the same English corpus tokenized twice, coarse vs deliberately 2x-finer BPE ("synthetic fertility", identical content), reproduces the recall gap at baseline (>= 8 points at matched semantic distance) and the semantic-clock arm merges the two curves (<= 2 points). This isolates token count from every other language difference.
- P4 (mechanism localization): in the 3:1 GDN hybrid the baseline gap is at most half the pure-GDN gap (retrieval is carried by full attention, 2606.15378) and the semantic-clock effect shrinks accordingly; an equal effect in the hybrid would falsify the "recurrent clock" story.
- P5 (view necessity): the fertility-scaled-gate oracle recovers >= 70% and the information clock >= 50% of the parity arm's gap reduction; if either recovers >= 95%, the parallel view is unnecessary.

**kill_conditions.** (1) P1 self-normalization (DPR <= 1.15 across fertile languages). (2) At 100M pure GDN, 3 seeds, paired clustered SE: the parity arm reduces the cross-language recall gap by < 50% relative, or any language loses > 1% BPB. (3) The static fertility-scaled gate or the information clock matches the parity arm within noise (view not needed; publish as a normalization recipe instead). (4) SWA + attention sinks at equal state bytes shows no cross-lingual recall gap and matches the parity arm (the token clock is a linear-operator artifact with a cheaper fix). (5) The two-forward-pass prefix-invariance audit (2608.22876) finds the parity loss leaking future or cross-language information.

**cheapest_decisive_pilot.** Phase 0 (CPU, no LM): NumPy GDN simulator with a fixed decay and token
duplication x k (fertility simulation) verifying F scales x k and recall at fixed semantic distance
drops accordingly; gradient check of the chi-square parity loss; causality doctor showing the loss
depends only on span sums (permute positions within a span -> identical loss; leak a future token ->
detected). Then frozen-checkpoint measurement (P1) on the three released GDN hybrids (+ KDA if the
custom-code review clears) over NTREX-128 sentences in {en, pl, zh, ko, th, sw}; FLORES-200 devtest
stays sealed for the endpoint. Phase 1 (<= 12.5 GPU-hours): 100M pure-GDN (fla `gated_deltanet`
layer, fla >= 0.5.2) trained on 1.5B tokens (~15N) of an equal-byte 6-language FineWeb-2 mixture plus
10% parallel-view batches (NLLB/OPUS + General Translation aligned sentences), 5 arms x 3 seeds
[42,43,44] on 1 H100 each (~0.8 GPU-hour per run): baseline / semantic clock / information clock /
fertility-scaled gate oracle / SWA+sinks at matched state bytes; all arms consume the identical token
stream and data order (only the auxiliary term differs). Phase 1b (conditional on P2, +5 GPU-hours):
3:1 GDN hybrid baseline vs parity, 3 seeds (P4). Tokenizer: SentencePiece with byte fallback trained on
the equal-byte corpus with the `\p{L}+` pre-tokenizer bug avoided (2608.26449). Total pilot
14 GPU-hours. Confirmation stage (new contract): 60M/125M/350M ladder, >= 5 seeds, length-dependent
recall curves, QED- and MARCH-equipped arms measured with the same instrument.

**pilot_gpu_hours.** 14

**controls.** iso-parameter (the view adds no parameters), iso-FLOP and iso-wall-time (inference
identical; auxiliary loss costs < 2% train FLOPs, reported); data-only control (identical batches
without the auxiliary term — mandatory, since parallel sentences are in every arm's stream); SWA +
attention sinks at matched state bytes (2608.28444, mandatory for any linear/hybrid claim); QED
(2608.13668) and MARCH (2608.12435) measured with the same cross-lingual instrument (they inherit the
per-token clock; predicted to show the same inequity); synthetic-fertility English arm (identification);
fertility-scaled-gate oracle and information clock (view necessity); pure-GDN vs 3:1 hybrid (mechanism
localization); per-arm LR sweep at the 30M rung (2608.11859); generation-based exact match with
permutation-controlled answer positions; two-forward-pass prefix-invariance audit (2608.22876); DASC-style
per-head retention horizons (2608.30386) reported per language as a free diagnostic.

**kevin_advantage.** Sentence- and span-aligned parallel data across many pairs including low-resource
and domain (terminology) sets is required for both the view and the probe; 8xH100 runs the 15-run grid
in a day; the harness already enforces exact-match generation, seeded runs and checkpoint/resume. Honest
caveat: phase 0 is cheap enough that any lab with FLORES could run it; the unique part is the production
aligned data and the terminology stress sets for the confirmation stage.

**collision_risk.** low. Searches run 2026-09-01 (hostsearch on the H100 host unless noted):
Q2 arXiv `(abs:"linear attention" OR abs:"gated deltanet" OR abs:"state space") AND abs:decay AND
(abs:multilingual OR abs:"cross-lingual" OR abs:fertility OR abs:tokenization)` -> 25 results, none
cross-lingual (nearest: Adaptive Memory Decay 2605.06946, DASC 2608.30386, DAMP 2608.27513, GDN-2
2605.22791 — all monolingual); Q12 arXiv `abs:surprisal AND abs:decay AND (linear attention OR state
space OR recurrent) AND "language model"` -> 0; Q7 DDG (decay gate fertility multilingual) -> empty page
(likely CAPTCHA); arXiv search UI (WebFetch) `"linear attention" decay multilingual` -> "no results";
seq-operators cell: `all:"linear attention" AND (multilingual OR "cross-lingual" OR translation)` -> 14,
none on state/decay across languages. No direct prior art found through 2026-09-01 under this coverage.

**monitorability_and_safety.** No effect on CoT or action monitorability (train-time auxiliary loss on
gate statistics; inference architecture unchanged). The per-language forgetting/write ledger is a new
interpretability handle. Data rights: NTREX-128 and FLORES-200 are CC-BY-SA 4.0; OPUS/NLLB-mined pairs
carry mixed licenses and must be filtered; General Translation data under its production data contract;
no PII in the probe sets. No dual-use concern identified.

**negative_result_value.** A phase-0 negative ("released hybrids already normalize forgetting per
meaning") is the first measurement answering seq-operators G1 and shows gates learn fertility compensation
unsupervised — extending 2603.29026 from representations to gate statistics. A phase-1 negative (parity
arm does not move recall) localizes the cross-lingual recall bottleneck outside the recurrent state and
hands the question to Candidate 2. Either way the translation-paired recall instrument (G20) is delivered.

**targets_gaps.** G2, G19, G20 (synthesis); seq-operators G1; learned-update-rules G4 (paired
"same content, different surface" probe of what a state write preserves).

---

## Candidate 2 (moonshot) — `translation-supervised-sparse-indexer`

**Claim.** Learned sparse-attention indexers (DSA/QSA class), distilled only from full attention on
mostly English/Chinese/code, are a cross-lingual retrieval bottleneck in sparse global layers;
supervising the indexer with aligned bilingual documents — a training view that never touches the main
attention — makes selection language-invariant, closes most of the cross-lingual needle gap at fixed
top-k, and can exceed the dense teacher on cross-lingual retrieval because selection forces mass onto the
aligned block that dense attention dilutes.

**claim_scope.** architecture-causal (frozen-base screen for identifiability; the from-scratch 125M
sparse-global arm carries the causal claim; the later 4B continued-pretraining stage is the moonshot).

**Mechanism.** DSA-class indexer (fla `ops/dsa/README.md`, first-party docs, read 2026-09-01):
`I_t(s) = sum_{j=1..H_I} w_{t,j} * ReLU(q^I_{t,j} . k^I_s)` for `s <= t` (token level; block level sums
over the block), `S_t = Top-k_s I_t(s)`, attention runs only over `S_t`. Because top-k is
non-differentiable and the indexer feeds only selection, it is trained by distillation
`L_I = KL(P_t^attn || softmax_s I_t(s))` with `P_t^attn` the head-summed full-attention distribution
(indexer = student, attention = teacher); the main model receives no indexer gradient. Translation view:
from aligned document pairs `(D_a, D_b)` build contexts `C = [D_b ; <sep> ; D_a]` (and the reverse order);
a frozen word/span aligner (OmniAlign 2608.18474 or CTFAlign 2608.21023) gives, for content tokens
`t in D_a` with alignment confidence `>= tau`, the aligned key set `A(t) subset D_b`, mapped to the
indexer's granularity `N(A(t))`. Add
`L_x = -(1/|Q|) * sum_{t in Q} log sum_{s in N(A(t))} softmax_s(I_t(s))`,  `L_I' = L_I + lambda_x * L_x`.
Ablation term for monolingual equivalence: for aligned positions `(t_a, t_b)` processed in *separate*
monolingual contexts, transport the two selection distributions through the alignment with the repo's
debiased unbalanced Sinkhorn (harness/translation_boundaries.py): `L_eq = UOT(softmax I_{t_a}, softmax
I_{t_b} | A)`. Inference is unchanged (same indexer architecture, same k); since main attention weights
never see the alignment gradient, any behavioral change is attributable to selection. Why the indexer
plausibly lags the teacher cross-lingually: production indexers are tiny and low-precision (Qwen3.8-
Flash-Next config: 4 MQA indexer q heads + 1 shared key head, dim 128, compress ratio 4, budget 2048;
GLM-5.3-Flash: 32 x 128, `index_kpool 4`; FP8/FP4 lightning indexers), and cross-script semantic matches
live in a subspace that a rank-128 ReLU scorer distilled on monolingual mass need not preserve.

**what_is_new (delta vs closest priors, each opened 2026-09-01).**
- DeepSeek-V3.2 / DSA, https://arxiv.org/abs/2512.02556 (2025-12-02; first-party): token-level
  lightning indexer distilled to attention; no per-language analysis. Ours adds an alignment-supervised
  selection term that never touches main attention.
- On the Design of Qwen3.8-Next Architecture (QSA), https://arxiv.org/abs/2608.30320 (2026-08-31;
  first-party): full-attention layers replaced by micro-block sparse attention with a compressed indexer
  at continued pretraining; no per-language long-context analysis. Ours is a drop-in indexer objective for
  exactly that CPT stage; the QSA/A.X-K2 recipe is the mandatory baseline, not the proposal.
- LongCat Sparse Attention, https://arxiv.org/abs/2608.01662 (2026-08-03; first-party): indexer indices
  reused across layers with cross-layer distillation. Ours distills from a cross-lingual alignment target
  rather than from another layer.
- PIVOT, https://arxiv.org/abs/2607.24593 (2026-07-27): training-free query-group replacement of the DSA
  indexer on DeepSeek-V3.2/GLM-5.1; no objective change, no multilingual evaluation. Used as a
  training-free control.
- MLNeedle, https://arxiv.org/abs/2408.10151 (2024-08-19); OneRuler, https://arxiv.org/abs/2503.01996
  (2025-03-03; 26 languages, up to 20% swing from instruction language); mLongRR,
  https://arxiv.org/abs/2409.18006 (2024-09-26; MRL 2024; 96% en -> 36% so): establish the cross-lingual
  long-context gap phenomenologically in dense models; none localizes it to a component or proposes a fix.
- Native Sparse Attention, https://arxiv.org/abs/2502.11089 (2025-02-16): pooled-key block selection,
  gradient-free proxy; no multilingual evaluation. Used as the "is a learned indexer even needed" control.
Occupancy note: "sparse-attention-for-global-layer substitution at CPT" is occupied (Qwen3.8-Next QSA,
A.X K2 SGA 2608.30181) and is used here as the mandatory baseline; the delta is the indexer's training
signal and the cross-lingual instrument (seq-operators G6 / synthesis G13: no source asks whether selected
blocks correspond across translations).

**falsifiable_predictions.**
- P1 (frozen-base screen, Qwen3-0.6B-Base): a KL-only indexer at k = 12.5% of an 8K context attains aligned-block recall@k that is >= 15 points lower when the query token and the needle document are in different scripts (en<->zh/ko/th) than when both are in the same language, while the dense teacher's own attention-mass recall drops by less than half that amount. If the indexer's cross-lingual drop is <= 5 points, the indexer is not the bottleneck — kill.
- P2: adding `L_x` (lambda_x ~ 0.5, tau = 0.6) recovers >= 70% of the cross-lingual indexer recall gap with <= 1 point loss in monolingual recall and <= 0.3 points on RULER-en at the same k.
- P3 (end-to-end, frozen base, global attention restricted to indexer top-k): cross-lingual NIAH exact match (needle language != question language, 6 languages, 8K–32K, needle position stratified) rises by >= 10 points over the KL-only indexer; monolingual NIAH within 2 points.
- P4 (moonshot): with `L_x`, sparse attention at k = 2048 exceeds the dense full-attention model on cross-lingual NIAH at 32K by >= 3 points (selection concentrates mass the dense softmax dilutes over distractors). Embarrassing if wrong; the mechanism predicts it.
- P5 (from-scratch 125M, 3:1 GDN + QSA-style global layers, 6-language corpus): the cross-lingual recall gap at 4K–16K is >= 2x the monolingual gap for KL-only indexers and <= 1.3x with `L_x`, at equal BPB (+/-0.5%).

**kill_conditions.** (1) P1 fails (indexer not the bottleneck). (2) `L_x` gains vanish when the KL-only
indexer is trained on the same bilingual concatenations (data-only control) — bilingual exposure alone
fixes selection. (3) A training-free fix at equal latency (PIVOT-Refine-style re-scoring, or a larger k
matched on measured latency) closes the gap. (4) RouteSparse-style pattern routing (2608.29058) at
matched budget closes it without any learned indexer. (5) NSA pooled-key selection (no indexer) shows no
cross-lingual gap at matched budget. (6) Gains appear only in attention-recall proxies and not in
generation-based, permutation-controlled exact match. (7) Per-language recall in any language drops by
> 2 points (a supervised selector must not learn to ignore a language).

**cheapest_decisive_pilot.** Phase 0 (CPU, no LM): a synthetic bilingual toy — two vocabularies related
by a fixed permutation "translation", a random low-rank ReLU indexer against a full softmax teacher —
showing that low-rank indexers lose cross-vocabulary matches faster than same-vocabulary matches and that
`L_x` repairs it; doctors for `L_x` (mass accounting, alignment sensitivity vs permuted alignment) and
`L_eq` (reuse the registered UOT doctor gates). Phase 1 (<= 9 GPU-hours): frozen qwen3-0.6b-base
(registry id; 28 dense layers) with a DSA-style indexer attached to every layer (4 heads x 128, ~18M
params total) trained for ~200M tokens of 8K contexts built from aligned document pairs (ParaCrawl /
WikiMatrix / General Translation document pairs) plus monolingual FineWeb-2, four arms x 3 seeds
[42,43,44] (~0.6 GPU-hour each): (a) KL-only, monolingual contexts; (b) KL-only on bilingual
concatenations (data control); (c) KL + `L_x`; (d) KL + `L_eq`; evaluation: indexer aligned-block recall,
end-to-end cross/mono NIAH with sparse global attention at k, RULER-en at k, generation exact match;
plus PIVOT-Refine, larger-k, SWA+sinks and NSA-pooled controls (~2 GPU-hours of evaluation). Second
screen on qwen3.5-4b (registry; 8 full-attention layers only, closer to production) if budget remains.
Phase 1b (conditional on P1–P3; +6 GPU-hours): from-scratch 125M 3:1 GDN + QSA-style sparse global
layers (fla `nsa`/`dsa` ops) on the 6-language corpus, KL-only vs KL + `L_x`, 3 seeds, 1.5B tokens.
Moonshot stage (new contract; ~170 GPU-hours at 4B x 10B tokens, 35% MFU): Qwen3.8-Next-style CPT of
qwen3.5-4b replacing its 8 full-attention layers with QSA-style sparse layers, KL-only vs KL + `L_x`
indexers; endpoints OneRuler (26 languages) and MLNeedle cross-lingual; Tinker cannot host this stage
(indexer internals unreachable), but GLM-5.3 (DSA) and Qwen3.5 on Tinker supply production-scale
*behavioral* cross-lingual NIAH baselines.

**pilot_gpu_hours.** 15

**controls.** Dense full-attention teacher (reference bound); KL-only indexer on identical bilingual data
(data control, mandatory); larger k at matched measured latency (budget control); PIVOT-Refine-style
training-free re-scoring (2607.24593); RouteSparse-style static pattern routing at matched budget
(2608.29058); SWA + attention sinks at matched KV bytes (2608.28444, mandatory); NSA pooled-key block
selection (2502.11089; gradient-free proxy); QSA/A.X-K2 CPT recipe with standard KL indexer as the
occupied-baseline arm for the moonshot stage; iso-parameter (indexer size fixed across arms), iso-FLOP
(same k), iso-wall-time (fla kernel timing per arm, warm-up and fallbacks reported); generation-based,
permutation-controlled scoring (Stuck-on-A lesson); needle-position stratification (MLNeedle: middle
positions worst); two-forward-pass prefix-invariance audit (2608.22876); per-language recall floor.

**kevin_advantage.** Document-level aligned bilingual data with span alignment in many directions
including low-resource pairs is the input no sparse-attention lab has used; 8xH100 covers the frozen-base
screen and the 125M arms in a day and the 4B CPT stage in about a day of wall time; the harness supplies
generation exact match and the UOT doctor for `L_eq`; Tinker access to GLM-5.3 (DSA) and Qwen3.5 gives
production-scale behavioral baselines (no indexer access — stated honestly).

**collision_risk.** low-medium. Searches run 2026-09-01: Q1 arXiv `abs:"sparse attention" AND
abs:indexer AND (abs:multilingual OR abs:"cross-lingual")` -> 0 results; arXiv search UI (WebFetch)
`"sparse attention" indexer multilingual` -> "no results"; Q4 HF-papers `cross-lingual needle in a
haystack long context retrieval language mismatch` -> phenomenology only (OneRuler 2503.01996, mLongRR
2409.18006, NoLiMa 2502.05167, MIMO 2605.31171, NeedleBench), no sparse-attention or indexer paper; arXiv
search UI `"needle" "cross-lingual" "long context"` -> 3 (MLNeedle, OneRuler, Agri-Query 2508.18093);
Q6 DDG -> empty page (likely CAPTCHA); Q9 arXiv (needle x multilingual x long context) -> 429/parse
error; seq-operators cell: `all:"sparse attention" AND (multilingual OR "cross-lingual") AND "language
model"` -> 1 unrelated (mGPT 2022). No direct prior art found through 2026-09-01 under this coverage.
Why not "low": every sparse-attention lab (DeepSeek, Qwen, Meituan, Zhipu, MiniMax, SK Telecom) holds the
data to run this within weeks once asked; through 2026-08-31 none of their reports contains a per-language
indexer analysis.

**monitorability_and_safety.** Selection is an inspectable retrieval trace (which blocks were read),
which improves auditability of what context influenced an answer — including detection of cross-lingual
prompt injections hidden in another language. No effect on CoT. Failure mode to monitor: a supervised
selector that learns to under-select some languages (kill condition 7). Data rights: ParaCrawl (CC0),
WikiMatrix (CC-BY-SA), General Translation document pairs under contract; OneRuler/MLNeedle/FLORES for
evaluation only, sealed.

**negative_result_value.** If P1 fails, the cross-lingual long-context gap is localized outside
selection (in the attention/value pathway) — the first component-level localization of a gap that
MLNeedle/OneRuler/mLongRR only describe. If `L_x` fails while the bilingual data-only arm succeeds, bilingual
document exposure alone repairs indexers — a free recipe for every DSA/QSA lab. Either way the
cross-lingual indexer-recall instrument (G13) is delivered and portable to any DSA/QSA checkpoint.

**targets_gaps.** G13, G2, G20 (synthesis); seq-operators G6; benchmarks-eval G2.

---

## Candidate 3 (medium; pre-registered likely-negative) — `parallel-view-expert-routing-agreement`

**Claim.** Expert routers allocate parametric capacity per token, so (i) load balancing is computed per
token and lets high-fertility languages consume expert capacity in proportion to token count rather than
meaning, and (ii) middle-layer routing of translation-equivalent content agrees only partially across
languages; a parallel-view objective that balances expert load per aligned semantic unit and maximizes
middle-layer routing agreement across translations improves low-resource-language modeling at equal
active FLOPs — or, if it does not, extends the 2603.29026 negative from representations to routing.

**claim_scope.** architecture-causal (from-scratch small MoE arms; phase 0 is a measurement on open MoEs).

**Mechanism.** Router `p_t = softmax(W_r h_t) in Delta^E`, top-k experts per token; standard Switch
balance `L_bal = E * sum_e f_e * P_e` with `f_e` the fraction of tokens routed to `e` and `P_e` the mean
router probability. Parallel view, on batches containing aligned sentence pairs `(s_a, s_b)`:
(i) *semantic-mass balancing* — replace token fractions by unit-normalized fractions
`f_e^sem = sum_t w_t * 1[e in topk(t)] / sum_t w_t`, `P_e^sem = sum_t w_t * p_t(e) / sum_t w_t`, with
`w_t = 1/|s(t)|` (every sentence contributes unit mass regardless of its token count), so a high-fertility
language cannot monopolize expert capacity by token count;
(ii) *middle-layer agreement* — with `u_l(s) = (1/|s|) * sum_{t in s} p_t^l` the sentence-mean routing
distribution at layer `l`, `L_agree = sum_{(s_a,s_b)} sum_{l in MID} JS(u_l(s_a) || u_l(s_b))`, applied
only to middle layers (early/late layers are legitimately language-specific per 2510.04694 and
2601.14050). Total `L = L_LM + lambda_bal * L_bal^sem + lambda_agree * L_agree`. Inference unchanged
(same router, same k). Instrument for phase 0 and for the endpoint: per-layer *cross-translation routing
agreement* = top-k Jaccard between aligned tokens mapped through word alignment, and the *expert-load
ledger per aligned sentence* (experts x tokens per meaning, per language).

**what_is_new (delta vs closest priors, each opened 2026-09-01).**
- Multilingual Routing in Mixture-of-Experts, https://arxiv.org/abs/2510.04694 (2025-10-06; ICLR 2026):
  parallel text used to *analyze* routing (middle layers align cross-lingually; performance correlates
  with routing similarity to English) and to *steer* at inference (+1–2%). Ours turns the observation into
  a training-time objective computed from parallel views and adds per-meaning load balancing.
- Understanding Multilingualism in MoE LLMs, https://arxiv.org/abs/2601.14050 (2026-01-20): routing
  aligns with language families; middle layers as language-agnostic hubs; inference-time steering only.
- RISE / Language Routing Isolation, https://arxiv.org/abs/2604.03592 (2026-04-04; Findings of EMNLP
  2026): exploits routing isolation to adapt language-specific subnetworks (+10.85% F1); no routing
  objective. Ours changes what the router learns during pretraining.
- Leveraging Routing Dynamics for Efficient Language Adaptation, https://arxiv.org/abs/2605.29714
  (2026-05-28): continual pretraining diffuses early/middle routing; adaptation of final-layer experts;
  no cross-lingual routing objective.
- Task-level MoE for multilingual NMT, https://arxiv.org/abs/2110.03742 (2021-09-24; EMNLP Findings 2021):
  deterministic routing by language pair (+1.0 BLEU vs token routing) — the opposite move (route *by*
  language, not invariant to it); Fixing MoE Over-Fitting on Low-Resource Languages,
  https://arxiv.org/abs/2212.07571 (2022-12-15): conditional routing and MoE dropout for low-resource
  pairs (+1 chrF++), NMT-specific, no parallel-view agreement.
- X-Mod, https://arxiv.org/abs/2205.06266 (2022-05-12; NAACL 2022): language-specific modules by
  construction — a fixed-routing baseline our shared-expert objective must beat at equal active parameters.
- The Illusion of Specialization ("standing committee"), https://arxiv.org/abs/2601.03425 (2026-01-06):
  a compact expert coalition captures most routing mass across domains — predicts limited headroom for
  agreement objectives; adopted as a phase-0 expectation.
- Synergistic Intra-/Cross-Layer Regularization for MoE, https://arxiv.org/abs/2602.14159 (2026-02-15):
  routing regularizers from activations and adjacent-layer top-k (monolingual); no parallel signal.
Occupancy note: axis T of the synthesis ("multilingual MoE routing analysis and steering") is occupied
post hoc; the training-time objective from parallel views is the named remaining room (G19), explicitly
flagged by the synthesis as "may close as a negative".

**falsifiable_predictions.**
- P1 (phase 0 instrument on open MoEs — qwen3.6-35b-a3b (registry), gpt-oss-20b, Nemotron-3.5-Lightning-30B-A3B — over NTREX-128 aligned sentences in 6 languages, <= 2 GPU-hours): middle-layer cross-translation top-k Jaccard is <= 0.5 for cross-script pairs (en<->zh/ko/th) vs >= 0.7 for same-script high-resource pairs (en<->pl), and the expert-load ledger per aligned sentence scales with fertility (1.5–3x). If middle-layer Jaccard is already >= 0.7 for cross-script pairs, the standing-committee prediction holds and the agreement term has nothing to add — kill the agreement half.
- P2 (from-scratch 8-expert top-2 MoE, ~150M total / ~40M active, imbalanced mixture en 50% + 5 languages 10% each, 1.5B tokens): the agreement arm raises middle-layer cross-translation Jaccard from ~0.4 to >= 0.7 with English BPB within +0.5%.
- P3: the two lowest-resource languages (th, sw) improve held-out BPB by >= 2% relative vs the token-balanced baseline at equal active parameters and tokens, and translation-paired cloze/recall improves by >= 3 points; a dense iso-active-parameter model and a language-upsampled data-mixture control do not match this.
- P4 (active-ingredient test): semantic-mass balancing alone yields >= 50% of the low-resource gain; if agreement alone yields < 25% of it, the "agreement" story is cosmetic and only balancing-by-meaning survives.

**kill_conditions.** (1) Phase-0 Jaccard already >= 0.7 for cross-script pairs in middle layers. (2) The
agreement arm raises Jaccard but low-resource BPB does not improve by >= 1% relative over 3 seeds (paired
clustered SE) — routing agreement is cosmetic; publish as extending 2603.29026 to routing. (3) A
language-upsampled token-balanced baseline matches both arms — the objective is a data-mixture proxy.
(4) English BPB worsens by > 0.5% or any language by > 1%. (5) The dense iso-active-parameter control
matches the MoE arms (MoE brings nothing at this scale, invalidating the substrate).

**cheapest_decisive_pilot.** Phase 0 (CPU, no LM): synthetic token streams with fertility-imbalanced
"languages" verifying that per-token balance statistics are dominated by the high-fertility stream while
the unit-normalized estimator is unbiased; gradient check of the JS agreement loss; then the routing
instrument (Jaccard through word alignment, load ledger) on the three open MoEs (P1, <= 2 GPU-hours).
Phase 1 (<= 8 GPU-hours): from-scratch 8-expert top-2 MoE (~150M total, ~40M active, single-GPU PyTorch
MoE, no expert parallelism), 1.5B tokens of the imbalanced 6-language mixture with 10% parallel-view
batches, arms x 3 seeds [42,43,44] (~0.5 GPU-hour each): token-balanced baseline / semantic-mass balance /
semantic-mass balance + middle-layer agreement / agreement only / dense iso-active-parameter control /
language-upsampled data control; all arms consume the identical token stream. Not runnable on Tinker
(routers unreachable through LoRA). Total pilot 10 GPU-hours.

**pilot_gpu_hours.** 10

**controls.** iso-active-parameter dense model; iso-FLOP and iso-wall-time (same k, same expert count;
auxiliary terms train-time only, cost reported); token-balanced Switch baseline on identical data (the
mandatory data control); language-upsampled mixture control (tests the data-mixture explanation); X-Mod-
style fixed language-specific experts at equal active parameters (the opposite design); standing-committee
audit (2601.03425 protocol) on every arm; per-arm LR/balance-coefficient sweep at the smallest rung
(2608.11859); paired clustered SEs over 3 seeds; generation-based cloze scoring; SWA + attention sinks is
not applicable (no sequence-operator claim) and is stated as such.

**kevin_advantage.** Modest and stated honestly: parallel sentences for the agreement view and the
alignment-level routing instrument, plus 8xH100 for the small-MoE grid; routers are not reachable through
Tinker, so the Kimi/GLM access adds nothing here; any academic lab with FLORES could run phase 0.

**collision_risk.** medium. Searches run 2026-09-01: Q3 arXiv `abs:"mixture of experts" AND abs:routing
AND (abs:"parallel sentences" OR abs:"parallel corpus" OR abs:"parallel data" OR abs:translations) AND
(abs:consistency OR abs:agreement OR abs:regularization)` -> 7 results, none a parallel-view routing
objective (nearest: THOR-MoE 2505.14173 task-guided routing for NMT; 2212.07571; 2602.14159); Q5 HF-papers
`language-invariant expert routing consistency parallel sentences mixture of experts` -> 2510.04694 plus
general MoE routing papers, none cross-lingual training-time; Q8 OpenReview `cross-lingual routing
consistency mixture of experts` -> 2510.04694 (ICLR 2026 poster) plus unlabeled forums not opened; Q10
arXiv `abs:expert AND abs:routing AND abs:"cross-lingual" AND (objective OR loss OR regularizer OR
regularization)` -> 1 unrelated (2608.13565); Q11 DDG -> empty page; arXiv search UI `"mixture of experts"
routing multilingual "parallel" consistency` -> 1 (2510.04694). No direct prior art found through
2026-09-01 under this coverage; the idea is the obvious training-time follow-up to 2510.04694 and
2601.14050, hence medium.

**monitorability_and_safety.** Routing traces are interpretable; forcing shared middle-layer experts could
reduce per-language controllability (for example language-specific safety behaviors living in
language-specific experts) — measured via per-language refusal/format probes in the confirmation stage; no
CoT effect. Data rights as in Candidate 1.

**negative_result_value.** A clean pre-registered negative ("training-time routing agreement is
cosmetic") closes the routing half of G19 and extends 2603.29026 from representations to routing; the
per-semantic-unit expert-load ledger and the alignment-level routing-agreement instrument stand regardless
and feed G19's compute-per-meaning parity ledger.

**targets_gaps.** G19, G20 (synthesis); tokenizer-free G2/G3.

---

## 4. Why these three and not the other allocation devices

- Boundaries: owned by Direction 18 (STILL_OPEN with five new arms); not re-proposed. Its patch-rate
  parity per aligned sentence (the "compute-per-semantic-unit" ledger of G19) is reused here as a shared
  instrument, not as a candidate.
- Depth / loops: "generic latent loop with halting" is rejected; MoR/GRT/MixerLoop/CDB occupy adaptive
  depth; a translation-equivariant halting objective has no positive prior (surface decoding may
  legitimately need more depth in some scripts) and the depth-attention probe on parallel data (G9
  remnant) is a measurement, not a mechanism — recorded as a diagnostic to attach to the G9 replication.
- Token-level operator routing (LoGo, NAtS-L, Switch Attention): NARROWED; a parallel view would be a
  new delta but the structural caps (2603.20997 pairwise-comparison requirement; 2606.15378 convergence)
  bound the gain; the indexer (Candidate 2) is the version of "who gets global compute" with the clearer
  bottleneck story and instrument.
- Attention span (semantic sliding window): a per-language static window scaling likely captures most of
  the benefit; parked as a control idea for Candidate 1's SWA+sinks arm (report SWA recall per language
  with windows in tokens vs windows scaled by fertility).

## 5. Coverage limits (honest)

- hostsearch budget: 12 calls used (Q1–Q12 above). DuckDuckGo via the host returned empty result pages
  on all three DDG queries (Q6, Q7, Q11; likely CAPTCHA HTML without result anchors). One arXiv API call
  (Q9) returned a parse error consistent with HTTP 429. OpenReview search (Q8) returned mostly unlabeled
  forum ids that I did not open.
- WebSearch: session budget exhausted before this cell; not used. Semantic Scholar: unavailable (429).
- Abstract-level reading only for all priors (WebFetch summaries of arxiv.org/abs pages); indexer training
  details come from fla's `ops/dsa/README.md` (first-party docs) and the seq-operators cell's config reads
  of Qwen3.8-Flash-Next and GLM-5.3-Flash, not from the full DeepSeek-V3.2 / Qwen3.8-Next PDFs.
- Not searched: Chinese-language sources, Google Scholar, ACL Anthology full text, live X, Reddit/HN,
  ICLR 2027 submissions (not visible until late September 2026), patents, classical NMT literature on
  language-specific routing beyond the two items opened.
- Fertility ratios for the Qwen tokenizer are not quoted numerically here; the repo's fertility ledger
  (`data/tokens/{model}_fertility.json`) must be re-read before pre-registering P1's thresholds.
- Feasibility arithmetic (GPU-hours) is derived from FLOP counts at 30–35% MFU on H100 and from the
  benchmarks-eval cell's "125M model to 20N tokens ~ 1 GPU-hour"; nothing was executed on the node.
- Qwen3.5-0.8B-Base, the startlux checkpoints, gpt-oss-20b and Nemotron-3.5-Lightning are not yet in
  models/registry.yaml; kimi-linear-48b-a3b-base is registered but blocked on custom-code review.

## 6. Sources opened on 2026-09-01 (abstract pages unless noted)

2412.06464 · 2510.26692 · 2608.30695 · 2603.29026 · 2608.30320 · 2502.11089 · 2608.01662 · 2607.24593 ·
2408.10151 · 2503.01996 · 2510.04694 · 2601.14050 · 2604.03592 · 2205.06266 · 2608.28444 · 2606.15378 ·
2312.00752 · 2407.08818 · 2606.19348 (DeepSeek-V4; CSA/HCA, not a lightning-indexer paper) · 2605.29714 ·
2110.03742 · 2606.15044 · 2512.02556 · 2605.06946 · 2602.14159 · 2601.03425 · 2212.07571 · 2409.18006;
fla-org/flash-linear-attention `fla/ops/dsa/README.md` and `fla/ops`, `fla/layers` listings (GitHub API);
huggingface/transformers `models/qwen3_next/modeling_qwen3_next.py` gate lines (GitHub API);
huggingface.co/api/models?author=startlux-models (11 GDN hybrid checkpoints, 340M/1.3B).
Search logs: design/A-search/results.md.
