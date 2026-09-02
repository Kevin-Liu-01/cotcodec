# Canonical candidates after dedup (2026-09-01)

Dedup owner note. Inputs: 30 raw candidates from angles A–J (design/A-…J-*.md). Rule applied: merge by
MECHANISM (same object intervened on, same objective) — not by wording; drop what the brief lists as
occupied unless the candidate says why occupancy no longer holds; drop strap-on harness layers. Output:
16 canonical candidates, 13 merges, 1 drop. Slugs are neutral. GPU-hours are for the decisive pilot only;
conditional stages are named but not budgeted. No candidate is called novel; every gap is "no direct prior
art found through 2026-09-01 under <coverage>" as recorded in the source notes.

## Merged / dropped ledger (nothing silently lost)

| raw slug | fate | canonical | reason |
|---|---|---|---|
| semantic-clock-decay-parity (A1) | merged | semantic-clock-gate-parity | same object (GDN/KDA decay+write gates), same objective (cross-translation parity of cumulative gate mass); A1 supplies the span-level gate-statistic loss and identification arms |
| meaning-clocked-delta-rule (F1) | merged | semantic-clock-gate-parity | same object and objective as A1; F1 supplies the shared content-clock parameterization arm, the R_D/F phase-0 ledger and the content-distance probe |
| parallel-view-expert-routing-agreement (A3) | merged (half) / dropped (half) | meaning-indexed-compute-allocation | agreement half is OCCUPIED (SARA 2606.25821, RA-MoE 2605.28306 per verification pass); the per-semantic-unit load-balancing half is the expert-count instantiation of the same compute-parity penalty as F2 |
| parity-budgeted-mixture-of-depths (F2) | merged | meaning-indexed-compute-allocation | base statement of the canonical (depth-router instantiation, FLOPs-per-aligned-sentence ledger) |
| language-invariant-latent-length (F3) | merged | meaning-indexed-compute-allocation | same objective (trunk compute per aligned sentence language-invariant), same supervision (log-count parity of parallel pairs), same ledger and 60M 7-language substrate; pooling rate is the third allocation knob |
| task-latent-operator-port (B1) | merged | cross-family-adapter-port | base statement (label-free functional alignment, attention-fraction dose-response) |
| byte-span-anchored-adapter-port (B3) | merged | cross-family-adapter-port | same transport machinery (A^T = A^S R, functional B matching), same object (task adapter) and objective (lift retention across bases); differs only in the anchor set — kept as the segmentation/tokenizer axis arm |
| cross-operator-family-adapter-port (I3) | merged | cross-family-adapter-port | same object and objective; contributes the Mantel identifiability screen, the Tinker adapter zoo at 9B–1T, and the tokenizer-fixed Kimi-K2.6 -> Kimi-Linear hop |
| pathway-localized-lora-amnesia-ladder (I2) | merged | cross-family-adapter-port | same object (LoRA factor groups at hybrid attention vs recurrent sites); its leave-one-group-out/Shapley attribution is the site prior the port needs and is already a listed control (2604.22127 placement + 2606.11052 recall regression) — kept as the site-attribution/amnesia-surgery arm |
| provenance-ledger-reads (C1) | merged | hybrid-state-provenance-ledger | base statement (transported segment delta: influence, retention, zero-parameter unwrite with behavioral R(g)) |
| coded-provenance-shadow-state (H1) | merged | hybrid-state-provenance-ledger | same object (native linear-transition state on released checkpoints), same objective (training-free per-segment provenance of reads); the random-code shadow is the O(m d_k) compressed form of C1's per-segment influence — kept as the attribution-sketch arm |
| trainable-erasure-hybrid-state (C3) | merged | hybrid-state-provenance-ledger | same object and objective (behavioral erasure of a typed span from hybrid state) as C1's unwrite; C1's kill hands off to C3 — kept as the conditional trained-corrector stage |
| exclusive-composition-deletion-ledger (E1) | merged | read-free-record-blocked-memory | frozen-base retrofit of the same mechanism as E2 (read-free, record-blocked writes -> associative per-record factors -> exact O(log N) exclusion); E1's kill hands off to E2 |
| read-free-memory-band-hybrid (E2) | merged | read-free-record-blocked-memory | from-scratch stage of the same mechanism; the architecture-causal claim of the canonical |
| typed-influence-ledger (E3) | merged | read-free-record-blocked-memory | same object (write path of the read-free band); the influence bound is a corollary of the same exclusive-composition algebra — kept as the typed-write poisoning arm |
| contraction-certified-fast-weights (H2) | merged | read-free-record-blocked-memory | its linear-case bound coincides with the read-free band's non-expansive influence bound; the nonlinear TTT-MLP contraction certificate (open-loop only) is kept as an optional certificate arm; the synthesis marks the stabiliser axis "closed for one more gate" (SANE, Falcon, E2-TTT) |
| commit-gated-observation-state (G1) | merged | commit-gated-observation-state | base statement |
| predictive-observation-commit (G3) | merged | commit-gated-observation-state | intervenes on the same object (the boundary commit of G1) and depends on G1's checkpoints; kept as the predictive-residual arm with the SR-TTT position-bias kill pre-registered |
| frozen-reader-anchored-codes (D1) | merged | frozen-reader-anchored-media | base statement (explicit-trace substrate) |
| metered-opaque-channel-recurrence (D3) | merged | frozen-reader-anchored-media | same frozen weaker reader, same rate/slack bound, same ToyTools oracle world and collusion probe; the looped inter-iteration state is the second substrate and the metered C-bit channel is its knob |
| state-read-mtp-drafts (J3) | dropped | — | high collision with an active systems line (SpecLA, TreeWY, Windowed-MTP, Mamba Drafters, KVBuffer) and the brief's occupied "hybrid serving state algebra"; the only architecture remnant (does MTP shape retention horizons at <=1B, G11) is folded as MTP-on/off arms into the shared 125M hybrid substrate of global-anchor-skip-read-depth-operators |

Kept as their own canonical (no merge): translation-supervised-sparse-indexer (A2), icl-rule-distillation-port (B2),
translation-equivariant-state-writes (C2), interlingua-trace-codes (D2), provenance-typed-attention (G2),
tag-and-capture-delta-memory (H3), lora-footprint-routing-probe (I1), nope-hybrid-clock-tiebreak (J1),
global-anchor-skip-read-depth-operators (J2).

Occupancy check against the brief: none of the 16 proposes another hybrid ratio, generic linear attention,
static operator mixtures, a latent loop with halting, diffusion+MoE, graph RAG, same-family LoRA porting, Coded
Delta, or a harness layer. Where a canonical touches a rejected axis it states the delta: cross-family-adapter-port
crosses operator families and tokenizers (PorTAL/Trans-LoRA/Cross-LoRA are same-family; UpgradeBench defers
learned mappings on shape-incompatible hops); tag-and-capture and the predictive-commit arm gate at capture
time on a later signal, not at write time on prediction error, with Titans as a control and SR-TTT self-tests as
kills; frozen-reader-anchored-media fixes R (no halting) and claims monitorability bandwidth, not efficiency.

Angle mix: A/F (1, 2, 3), B/I (4, 5, 14), C/H (6, 7, 13), E (8), G (9, 10), D (11, 12), J (15, 16).
Cheap-decisive (<= 12 GPU-h or phase-0 kill before training): 1, 6, 8, 10, 14, 15. Moonshots with an
identifiability screen: 3, 4, 5, 9, 12, 13.

---

## 1. semantic-clock-gate-parity  (A1 + F1)

**Claim.** In gated delta-rule / SSM layers (GDN, KDA, Mamba) forgetting and writing are applied once per
token, so equal content costs a high-fertility language proportionally more forgetting and write mass
(faster decay, less state per meaning); a training-time parallel-translation view that equalizes cumulative
log-decay and write mass over aligned spans — either as an auxiliary loss on the existing gate statistics or
through a shared learned content clock whose totals are constrained to parity — removes the inequity and
equalizes translation-paired recall across scripts at unchanged per-language bits per byte with no inference
change; a training-free phase 0 first measures whether released gates already self-normalize.

**claim_scope.** architecture-causal.

**Mechanism.** GDN (transformers qwen3_5 parameterization): S_t = alpha_t S_{t-1}(I - beta_t k_t k_t^T) +
beta_t v_t k_t^T, log alpha_t = g_t = -exp(A_log) softplus(a_t + dt_bias) (scalar per head; vector per channel in
KDA), beta_t = sigmoid(b_t). For an aligned span s (frozen aligner: OmniAlign 2608.18474 / CTFAlign 2608.21023)
define forgetting mass F(s) = -sum_{t in s} g_t and write mass W(s) = sum_{t in s} beta_t; under per-token clocks
F(s_b)/F(s_a) ~ |s_b|/|s_a| = fertility ratio. Arm (i) gate-statistic parity: L = L_LM + lambda_F sum_{(s_a,s_b)}
sum_{layers,heads} (F(s_a) - F(s_b))^2/(F(s_a)+F(s_b)+eps) + lambda_W (same for W); only gate parameters receive the
auxiliary gradient; each translation is processed monolingually, coupled only through span sums; the loss is causal
and vanishes at inference. Arm (ii) content clock: c_t = softplus(w_c . h_t + b_c) shared across heads, log alpha_t =
-c_t softplus(a_t), beta_t = 1 - exp(-c_t softplus(b_t)), with L = L_LM + lambda (log sum_{t in A} c_t - log sum_{t in B}
c_t)^2 + mu (mean_en c_t - 1)^2 (scale fixed on English); fla chunk_gated_delta_rule / chunk_kda signatures unchanged.
Identification arms: static fertility-scaled gate g_t' = g_t / f_L with oracle language ID; information clock g_t' =
g_t stopgrad(h(x_t)/hbar) with h surprisal under a frozen small LM; heuristic byte clock c_t = bytes(token)/mean_bytes;
shuffled-pair placebo. Phase-0 ledger on released checkpoints: D(x) = -(1/H) sum_{t,h} log alpha_{t,h}, W(x) = (1/H)
sum_{t,h} beta_{t,h} per FLORES-plus / NTREX sentence; R_D(L) = D(x_L)/D(x_en) vs fertility F(L) = n_L/n_en. R_D ~ F
means the clock ticks per token (room for the mechanism); R_D ~ 1 kills the training stage. Probe: translation-paired
recall (K templated facts in language L, queried after d intervening facts; recall vs content distance d, replotted
against token distance) plus a secondary store-in-A/query-in-B readout.

**What is new.** GDN and KDA train gates by LM loss only with a per-token clock and report no per-language behavior;
Mamba's selective step is already a learned per-token clock but its totals are never supervised across translations;
Liquid Gated Attention clocks decay by observed time intervals for time series, whereas here the unobserved semantic
interval for text is supplied by translation alignment at training time only; MAGNET and parity-aware BPE enforce
parity on segmentation/vocabulary while here the tokenizer is fixed and parity is enforced inside the recurrent
operator; Titans gates writes by gradient surprise (rejected axis) whereas the clock here is a causal feed-forward
function with no loss gradient. No new gate is proposed. No direct prior art found through 2026-09-01 under the
coverage in A-translation-supervised.md §5 and F-compute-equity.md §5 for a cross-lingually supervised state clock
or per-language decay ledger (seq-operators G1 names the missing instrument).

**Closest priors.**
- Gated Delta Networks (ICLR 2025) — https://arxiv.org/abs/2412.06464 — 2024-12-09 — gates trained by LM loss only, per-token clock, no per-language analysis.
- Kimi Linear (KDA) — https://arxiv.org/abs/2510.26692 — 2025-10-30 — channel-wise decay in a 3:1 production hybrid, no per-language analysis.
- Mamba — https://arxiv.org/abs/2312.00752 — 2023-12-01 — selective step Delta_t is a learned per-token clock; totals never supervised across translations.
- Liquid Gated Attention — https://arxiv.org/abs/2608.30695 — 2026-08-31 — decay clocked by observed time intervals (time series), no LM.
- MAGNET — https://arxiv.org/abs/2407.08818 — 2024-07-11 — parity on segmentation granularity per script; here segmentation fixed, parity inside the operator.
- Adaptive Memory Decay for Log-Linear Attention — https://arxiv.org/abs/2605.06946 — 2026-05-07 — content-adaptive decay from an MLP, monolingual.
- On the limited utility of parallel data (Leino & Tiedemann) — https://arxiv.org/abs/2603.29026 — 2026-03-30 — parallel data barely moves representation alignment; gate statistics are a different observable and the nil result is pre-registered.
- Titans — https://arxiv.org/abs/2501.00663 — 2024-12-31 — surprise gating at write time (control arm, rejected axis).

**Falsifiable predictions.**
- P1 (phase 0, frozen qwen3.5-4b, mamba-130m-hf, delta-net-1.3b-8k [beta ledger], startlux gdn-340m/1.3b 3:1, kimi-linear-48b-a3b-base if custom-code review clears; NTREX-128 / FLORES-plus in {en, pl, zh, ko, th, sw, bn}): forgetting-mass ratio R_D(L) >= 0.8 x fertility ratio for every language with fertility >= 1.5; R_D within 15% of 1.0 while F >= 2 kills the training stage.
- P2 (100M pure GDN, 6 languages at equal bytes, 3 seeds): translation-paired recall after 8 sentences of matched-content distractors differs by >= 10 exact-match points between highest- and lowest-fertility language at baseline; either parity arm cuts the gap to <= 4 points with per-language BPB within +1%; the shuffled-pair placebo closes < 15%.
- P3 (identification): the same English corpus tokenized coarse vs 2x finer reproduces the gap (>= 8 points at matched semantic distance) and the parity arm merges the curves (<= 2 points).
- P4 (localization): in the 3:1 GDN hybrid the baseline gap is at most half the pure-GDN gap; an equal effect in the hybrid falsifies the recurrent-clock story.
- P5 (view necessity): the fertility-scaled-gate oracle recovers >= 70% and the information/byte clocks >= 50% of the parity arm's gap reduction; >= 95% by any monolingual arm means the parallel view is unnecessary (publish as a normalization recipe).

**Kill conditions.** Phase-0 self-normalization (R_D within 15% of 1 for fertility >= 1.5); parity arms reduce the gap by < 50% relative over 3 seeds (paired clustered SEs) or any language loses > 1% BPB; a monolingual proxy matches the parity arm within noise; SWA+sinks at equal state bytes shows no cross-lingual gap and matches the parity arm; the two-forward-pass prefix-invariance audit (2608.22876) finds leakage in the parity loss or clock path.

**Cheapest decisive pilot.** Phase 0 (CPU): NumPy GDN simulator with token duplication x k verifying F scales x k and recall at fixed semantic distance drops accordingly; gradient check of the chi-square parity loss; causality doctor (within-span permutation invariance, future-token leak). Frozen ledger + content-distance probe on the registry checkpoints (~1.5 GPU-h; 200 templated facts translated through General Translation's pipeline, human spot-check). Phase 1 (~14.5 GPU-h): 100M pure GDN (fla >= 0.5.2) on 1.5B tokens of an equal-byte 6-language FineWeb-2 mixture with 10% parallel-view batches (NLLB/OPUS + GT aligned sentences), one 32k byte-BPE with the \p{L}+ regex fixed; 6 arms x seeds [42,43,44] (~0.8 GPU-h each): baseline, gate-statistic parity, content-clock parity, shuffled-pair placebo, fertility-scaled-gate oracle, SWA+sinks at matched state bytes; identical token stream in every arm. Phase 1b (conditional, +5 GPU-h): information/byte clocks and the 3:1 hybrid localization arm. Confirmation under a new contract: 60M/125M/350M ladder, >= 5 seeds, QED- and MARCH-equipped arms measured with the same instrument.

**pilot_gpu_hours.** 16.

**Controls.** Data-only control (identical batches, no auxiliary term); iso-parameter / iso-FLOP / iso-wall-time (auxiliary train cost < 2% reported); shuffled-pair placebo; SWA + attention sinks at matched state bytes (2608.28444); QED (2608.13668) and MARCH (2608.12435) with the same cross-lingual recall instrument; synthetic-fertility English arm; fertility-scaled-gate oracle, information clock, byte clock; pure-GDN vs 3:1 hybrid (2606.15378 localization); per-arm LR sweep at the 30M rung (2608.11859); generation-based permutation-controlled exact match; two-forward-pass prefix-invariance audit; DASC-style per-head retention horizons per language.

**Kevin advantage.** Sentence- and span-aligned parallel data across many pairs incl. low-resource and terminology stress sets (General Translation) is required for both the view and the "only the language changes" probe; 8xH100 runs the 18-run grid in a day; the harness enforces exact-match generation, seeds, checkpoint/resume. Phase 0 needs only public FLORES and released checkpoints (modest there).

**collision_risk.** low (searches in A §5 and F §5: arXiv abs queries on decay/gate x multilingual/fertility/parallel; HF papers; no cross-lingually supervised gate or per-language decay ledger found).

**Monitorability and safety.** No CoT/action effect; the per-language forgetting/write ledger is a new interpretability handle. New attack surface for the clock arm: "clock injection" (adversarial suffix with large c_t flushes state) — pre-register a c_t clamp and report c_t under adversarial suffixes. Data rights: NTREX-128 / FLORES CC-BY-SA 4.0; OPUS/NLLB license-filtered; GT data under its production contract with PII scrub; delta-net-1.3b-8k license unresolved (measurement only).

**Negative-result value.** A phase-0 negative (released gates already normalize per meaning) is the first measurement answering seq-operators G1 and extends 2603.29026 from representations to gate statistics; a phase-1 negative localizes the cross-lingual recall bottleneck outside the recurrent clock (write fragmentation / key interference -> QED/MARCH side) and hands the question to the indexer candidate; the translation-paired recall instrument (G20) is delivered either way.

**targets_gaps.** G2, G19, G20.

---

## 2. translation-supervised-sparse-indexer  (A2)

**Claim.** Learned sparse-attention indexers (DSA/QSA class), distilled only from full attention on mostly
English/Chinese/code, are a cross-lingual retrieval bottleneck in sparse global layers; supervising the indexer
with aligned bilingual documents — a training view that never touches the main attention — makes selection
language-invariant, closes most of the cross-lingual needle gap at fixed top-k, and can exceed the dense teacher
on cross-lingual retrieval because selection forces mass onto the aligned block that dense attention dilutes.

**claim_scope.** architecture-causal.

**Mechanism.** DSA-class indexer: I_t(s) = sum_{j<=H_I} w_{t,j} ReLU(q^I_{t,j} . k^I_s) for s <= t (block level sums
over the block); S_t = Top-k_s I_t(s); attention runs over S_t only. Top-k is non-differentiable and the indexer
feeds only selection, so it is trained by distillation L_I = KL(P_t^attn || softmax_s I_t(s)) with P_t^attn the
head-summed full-attention distribution; the main model receives no indexer gradient. Translation view: from
aligned document pairs (D_a, D_b) build contexts C = [D_b ; <sep> ; D_a] and the reverse; a frozen aligner gives
for content tokens t in D_a with confidence >= tau the aligned key set A(t) in D_b mapped to indexer granularity
N(A(t)); add L_x = -(1/|Q|) sum_{t in Q} log sum_{s in N(A(t))} softmax_s(I_t(s)); L_I' = L_I + lambda_x L_x.
Monolingual-equivalence ablation: L_eq = UOT(softmax I_{t_a}, softmax I_{t_b} | A) with the repo's debiased
unbalanced Sinkhorn (harness/translation_boundaries.py). Inference unchanged (same indexer, same k); since main
attention never sees the alignment gradient, any behavioral change is attributable to selection. Bottleneck
rationale: production indexers are tiny and low precision (Qwen3.8-Flash-Next: 4 MQA q heads + 1 shared key head,
dim 128, compress ratio 4, budget 2048; GLM-5.3-Flash: 32 x 128 with index_kpool 4; FP8/FP4), and cross-script
semantic matches live in a subspace a rank-128 ReLU scorer distilled on monolingual mass need not preserve.

**What is new.** DSA distills a lightning indexer with KL and reports no per-language behavior; Qwen3.8-Next QSA and
A.X K2 replace full-attention layers by indexer-based sparse layers at continued pretraining without per-language
long-context analysis (their recipe is the mandatory baseline; the delta is the indexer's training signal); LongCat
LSA distills indices across layers, here from a cross-lingual alignment target; MLNeedle, OneRuler and mLongRR
document the cross-lingual long-context gap in dense models without localizing it to a component or proposing a fix.
Nobody asked whether selected blocks correspond across translations (seq-operators G6 / synthesis G13). No direct
prior art found through 2026-09-01 under the coverage in A §5.

**Closest priors.**
- DeepSeek-V3.2 (DSA) — https://arxiv.org/abs/2512.02556 — 2025-12-02 — token-level lightning indexer distilled to attention, no per-language analysis.
- On the Design of Qwen3.8-Next (QSA) — https://arxiv.org/abs/2608.30320 — 2026-08-31 — micro-block sparse attention with compressed indexer at CPT; mandatory baseline recipe.
- LongCat Sparse Attention — https://arxiv.org/abs/2608.01662 — 2026-08-03 — cross-layer index distillation; here distillation from a cross-lingual alignment target.
- PIVOT — https://arxiv.org/abs/2607.24593 — 2026-07-27 — training-free query-group indexer replacement; the training-free control.
- MLNeedle — https://arxiv.org/abs/2408.10151 — 2024-08-19 — cross-lingual retrieval fails as context grows in dense models; no component localization.
- OneRuler — https://arxiv.org/abs/2503.01996 — 2025-03-03 — 26-language long-context benchmark; endpoint.
- Native Sparse Attention — https://arxiv.org/abs/2502.11089 — 2025-02-16 — pooled-key selection without a learned indexer; control.

**Falsifiable predictions.**
- P1 (frozen Qwen3-0.6B-Base screen): a KL-only indexer at k = 12.5% of an 8K context attains aligned-block recall@k >= 15 points lower when query and needle are in different scripts (en<->zh/ko/th) than same-language, while the dense teacher's own attention-mass recall drops by less than half that; an indexer drop <= 5 points kills the direction.
- P2: adding L_x (lambda_x ~ 0.5, tau = 0.6) recovers >= 70% of the cross-lingual indexer recall gap with <= 1 point monolingual recall loss and <= 0.3 points on RULER-en at the same k.
- P3 (end-to-end, global attention restricted to indexer top-k): cross-lingual NIAH exact match (6 languages, 8K–32K, position-stratified) rises >= 10 points over KL-only with monolingual NIAH within 2 points.
- P4 (moonshot): with L_x, sparse attention at k = 2048 exceeds dense full attention on cross-lingual NIAH at 32K by >= 3 points.
- P5 (from-scratch 125M 3:1 GDN + QSA-style global layers): cross-lingual recall gap at 4K–16K is >= 2x the monolingual gap for KL-only and <= 1.3x with L_x at equal BPB (+/-0.5%).

**Kill conditions.** P1 fails (indexer cross-lingual drop <= 5 points); L_x gains vanish when the KL-only indexer is trained on the same bilingual concatenations (data-only control); a training-free fix at equal measured latency (PIVOT-Refine re-scoring or larger k) closes the gap; RouteSparse-style pattern routing at matched budget or NSA pooled-key selection closes it without a learned indexer; gains appear only in attention-recall proxies and not in generation exact match; any language's recall drops > 2 points.

**Cheapest decisive pilot.** Phase 0 (CPU): synthetic bilingual toy (two vocabularies related by a fixed permutation, random low-rank ReLU indexer vs full softmax teacher) showing low-rank indexers lose cross-vocabulary matches faster and L_x repairs it; doctors for L_x (mass accounting, sensitivity vs permuted alignment) and L_eq (registered UOT doctor gates). Phase 1 (<= 9 GPU-h): frozen qwen3-0.6b-base with a DSA-style indexer on every layer (4 heads x 128, ~18M params) trained on ~200M tokens of 8K contexts from aligned document pairs (ParaCrawl, WikiMatrix, GT) plus FineWeb-2; four arms x seeds [42,43,44] (~0.6 GPU-h each): KL-only monolingual, KL-only on bilingual concatenations, KL + L_x, KL + L_eq; evaluate aligned-block recall, end-to-end cross/mono NIAH with sparse global attention, RULER-en, generation exact match; PIVOT-Refine, larger-k, SWA+sinks and NSA-pooled controls (~2 GPU-h). Phase 1b (conditional, +6 GPU-h): from-scratch 125M 3:1 GDN + QSA-style sparse layers (fla nsa/dsa ops), KL-only vs KL + L_x, 3 seeds, 1.5B tokens. Moonshot stage (new contract, ~170 GPU-h): Qwen3.8-Next-style CPT of qwen3.5-4b replacing its 8 full-attention layers with QSA-style sparse layers; endpoints OneRuler and MLNeedle cross-lingual; GLM-5.3 (DSA) and Qwen3.5 on Tinker as production behavioral baselines (no indexer access, stated honestly).

**pilot_gpu_hours.** 15.

**Controls.** Dense full-attention teacher (reference bound); KL-only indexer on identical bilingual data (mandatory data control); larger k at matched latency and PIVOT-Refine re-scoring (2607.24593); RouteSparse static pattern routing at matched budget (2608.29058) and NSA pooled-key selection (2502.11089); SWA + sinks at matched KV bytes (2608.28444); QSA / A.X K2 CPT recipe with standard KL indexer (occupied-baseline arm); iso-parameter (indexer size fixed), iso-FLOP (same k), iso-wall-time (fla kernel timing with warm-up); generation-based permutation-controlled scoring, needle-position stratification, two-forward-pass prefix-invariance audit (2608.22876), per-language recall floor.

**Kevin advantage.** Document-level aligned bilingual data with span alignment in many directions incl. low-resource pairs is the input no sparse-attention lab has used; 8xH100 covers the frozen screen and 125M arms in a day; the harness supplies generation exact match and the UOT doctor; Tinker access to GLM-5.3 (DSA) and Qwen3.5 gives production-scale behavioral baselines.

**collision_risk.** medium (A §5 searches: indexer x multilingual/translation/cross-lingual on arXiv/HF; none found; DSA/QSA labs could add per-language analysis at any time).

**Monitorability and safety.** Selection is an inspectable retrieval trace (which blocks were read), improving auditability incl. detection of cross-lingual prompt injections hidden in another language; no CoT effect. Failure mode to monitor: a supervised selector that under-selects some languages (kill condition). Data rights: ParaCrawl (CC0), WikiMatrix (CC-BY-SA), GT document pairs under contract; OneRuler/MLNeedle/FLORES sealed for evaluation.

**Negative-result value.** If P1 fails, the cross-lingual long-context gap is localized outside selection (attention/value pathway) — the first component-level localization of a gap MLNeedle/OneRuler only describe; if L_x fails while bilingual data alone succeeds, bilingual exposure repairs indexers for free (a recipe for every DSA/QSA lab); the cross-lingual indexer-recall instrument (G13) is portable to any DSA/QSA checkpoint.

**targets_gaps.** G13, G2, G20.

---

## 3. meaning-indexed-compute-allocation  (F2 + F3 + A3 load-balancing half)

**Claim.** Compute-bearing allocation knobs inside the model — a per-token depth router (Mixture-of-Depths), a
pool/unpool pair that sets the trunk's latent sequence length, and (once depth passes) per-token expert count or
per-meaning expert load — can be trained with one parallel-pair compute-parity penalty so that FLOPs per translated
sentence are equal across languages at iso-total-FLOPs; this removes most of the fertility cost premium without
per-language quality loss because the skipped/pooled mass is the low-entropy within-word continuation tokens that
inflate fertility, and a single FLOPs-per-aligned-sentence ledger decides whether the fix belongs inside the model
or in the tokenizer.

**claim_scope.** architecture-causal.

**Mechanism.** Shared penalty: for an allocation cost C(x) of a sentence x, L = L_LM + lambda_b (Cbar/B - 1)^2 +
lambda_p E_pairs[(log C(x_A) - log C(x_B))^2], pairs = aligned translations, B the global budget. Knob 1 (depth
router, primary): block l has a causal router r_{t,l} = sigmoid(w_l . h_t^{(l-1)} + b_l); soft MoD in training
h^{(l)}_t = h^{(l-1)}_t + r_{t,l} Block_l(h^{(l-1)})_t, hard skip at inference when r_{t,l} < tau_l set to the
capacity (50% of dense); C(x) = sum_{t in x} sum_l r_{t,l} c_l with attention charged at routed length. Knob 2
(latent length): layers 1..L1 token-level -> causal boundary head p_t = sigmoid(u . h_t^{(L1)}) with straight-through
or Nawrot-style stochastic boundaries -> unit states z_j = sum_{t in seg_j} softmax_t(s_t) h_t -> trunk layers
L1+1..L1+L2 causal over z_1..z_K -> unpool u_t = Trunk(z)_{j-1} (shift by one unit to preserve autoregression) added
to h_t -> token layers -> LM head; C(x) = n(L1+L3) c_tok + K(x) L2 c_trunk; compression anchored on English only
(lambda_r (Kbar_en/nbar_en - r_en)^2, r_en = 1/3) so every other language's rate is free and pulled to r_en/F(L) by
parity. Knob 3 (experts): unit-normalized load statistics f_e^sem = sum_t w_t 1[e in topk(t)] / sum_t w_t with
w_t = 1/|s(t)| so every sentence contributes unit mass regardless of token count (replaces Switch's per-token f_e,
P_e), or a variable-k router under the same penalty. Ledger: rho(L) = mean_pairs C(x_L)/C(x_en); quality: per-language
BPB at iso-total-FLOPs and FLORES en->{de,ja} chrF (generation-based, relative at 60M); effective depth / unit counts
by word position per language; the per-aligned-sentence expert-load ledger for knob 3. Rule-based control: skip
within-word continuation tokens by rule. Tokenizer-level control: parity-aware BPE with the \p{L}+ regex fixed, dense
compute.

**What is new.** Makes the MoD budget / pooling rate / expert load meaning-indexed through a training-time parallel-pair
parity penalty on a compute-bearing allocation and reports per-language cost and quality — which MoD, GRT/MoR, dynamic
token pooling (fixed rate), MrT5 (emergent rates), MAGNET (per-script predictors) and the multilingual-MoE routing
papers never do. The expert-ROUTING-agreement half of the original A3 is dropped: SARA (2606.25821) and RA-MoE
(2605.28306) already supervise routing consistency with parallel data; what survives per the verification pass is
the compute-per-semantic-unit allocation and its ledger, which is exactly this candidate. No direct prior art found
through 2026-09-01 under the coverage in F §5 for a language-parity-constrained depth/expert router or parity-count
pooling inside a subword LM.

**Closest priors.**
- Mixture-of-Depths — https://arxiv.org/abs/2404.02258 — 2024-04-02 — per-layer token routing under a static global capacity; no language variable.
- Gated Recurrent Transformers — https://arxiv.org/abs/2608.15062 — 2026-08-15 — adaptive recurrent depth beating MoR; mandatory iso-FLOP adaptive-depth baseline.
- Efficient Transformers with Dynamic Token Pooling — https://arxiv.org/abs/2211.09761 — 2022-11-17 — fixed-rate pooling in middle layers; here per-language rate free, anchored by parity.
- MrT5 — https://arxiv.org/abs/2410.20771 — 2024-10-28 — emergent language-specific deletion rates in a byte encoder; here rates supervised to equalize units per meaning.
- MAGNET — https://arxiv.org/abs/2407.08818 — 2024-07-11 — per-script boundary predictors; control arm.
- Multilingual Routing in Mixture-of-Experts (ICLR 2026) — https://arxiv.org/abs/2510.04694 — 2025-10-06 — parallel data used to analyze/steer routing at inference; here a training-time parity objective on a compute-bearing allocation.
- SARA — https://arxiv.org/abs/2606.25821 — 2026-06-24 — training-time routing alignment across languages; the reason the agreement half is dropped.
- Vowel Signs Are Not Letters — https://arxiv.org/abs/2608.26449 — 2026-08-26 — abugida fertility floors; supplies the fixed-regex tokenizer control and dose variable.

**Falsifiable predictions.**
- P1 (phase 0, qwen3-0.6b-base and smollm2-135m on FLORES-plus): within-word continuation tokens are >= 50% of tokens in bn/ta/th vs <= 25% in en, with median next-token entropy <= 0.6 bits vs >= 2.5 bits for word-initial tokens (embarrassing if continuation entropy >= 1.5 bits); aligned-unit counts per sentence vary across 7 languages with CV <= 10% while token counts vary with CV >= 35%.
- P2 (60M, capacity 50%): parity-MoD lowers rho(bn), rho(ta), rho(th) from the tokenizer fertility ratio (2.0–3.5 under a balanced 32k byte-BPE) to <= 1.4 with per-language BPB within 1% of uniform MoD at iso-total-FLOPs; the fertility-heuristic router achieves <= 60% of that rho reduction at equal BPB.
- P3 (latent length, conditional): parity-count pooling reaches per-language BPB within 3% of the iso-FLOP dense baseline at trunk-FLOP ratio <= 1.3; unsupervised ratio-loss pooling equalizes < 50% of the gap; MAGNET-style per-script rates lose >= 2% more BPB on the highest-fertility language.
- P4 (Pareto): on (macro BPB, max rho), parity-MoD on the base tokenizer is not dominated by parity-BPE + dense, and parity-BPE + parity-MoD reaches rho <= 1.2.

**Kill conditions.** Any language loses > 3% BPB at rho <= 1.4; the heuristic continuation-skip router reaches >= 80% of the learned gain (preprocessing suffices); parity-aware BPE + dense strictly dominates the Pareto front (the fix belongs in the tokenizer); iso-FLOP dense beats every adaptive arm by > 2% BPB at 60M and at a single 135M rerun; unsupervised (H-Net/MrT5-style) rates already equalize trunk cost (parallel signal unnecessary, extends 2603.29026 to compute allocation); any leakage in the unpool path under the two-forward-pass audit.

**Cheapest decisive pilot.** Phase 0 (<= 1 GPU-h + CPU): FLORES-plus devtest through qwen3-0.6b-base and smollm2-135m for per-token entropy by word position and fertility per language; aligner-derived unit counts and implied pooling rates (repo UOT doctor on span links); blt-1b patch counts per aligned sentence as the byte-level ledger row (CC-BY-NC, measurement only). Phase 1 (~14 GPU-h): 60M (12 layers, d = 512) on 1B tokens of a 7-language balanced mix + 10% parallel pairs, one 32k byte-BPE with the \p{L}+ regex fixed; arms: dense iso-total-FLOP, MoD-uniform 50%, parity-MoD 50%, heuristic-skip 50%, parity-aware-BPE dense (own tokenizer); 2 seeds each = 10 runs x ~1.4 GPU-h; GRT-style recurrent-depth arm, 1 seed. Phase 1b (conditional on P2, +14 GPU-h): pooling arms on the same substrate (fixed-rate 1/3, ratio-loss, parity-count, per-script). Phase 1c (conditional, +8 GPU-h): 8-expert top-2 MoE (~150M/40M active) token-balanced vs per-meaning-balanced vs language-upsampled data control vs dense iso-active. Endpoints: rho(L) ledger, per-language BPB, FLORES chrF sanity, effective-depth/unit histograms by word position.

**pilot_gpu_hours.** 15.

**Controls.** Dense iso-total-FLOP baseline; MoD-uniform at 50% capacity (2404.02258); GRT / MoR recurrent-depth arm (2608.15062, 2507.10524); fertility-heuristic router (no learning); parity-aware BPE with fixed regex, dense compute (2606.15044, 2608.26449); shuffled-pair placebo for the parity term; fixed-rate dynamic pooling (2211.09761), H-Net-style ratio-loss pooling (2507.07955), MAGNET-style per-script rates (2407.08818); token-balanced Switch baseline, dense iso-active-parameter and language-upsampled data-mixture controls for the expert arm; romanized-input arm (2608.25904) in confirmation; two-forward-pass prefix-invariance audit on the unpool shift; per-language (never macro) non-inferiority reporting; generation-based evaluation; contamination disclosure.

**Kevin advantage.** Parallel pairs supply L_par and the aligned-sentence FLOPs ledger at volume; the repo's fertility harness (data/tokens/{model}_fertility.json) and dir-18 tooling (UOT doctor, named aligners) extend directly; 8xH100; GT's terminology-heavy domain pairs give a production-relevant second test set. Honest: the mechanism is buildable by anyone with FLORES; the paired ledger at volume and the domain set are the edge.

**collision_risk.** medium (F §5 searches on MoD/pooling/routing x multilingual/parity/fertility; SARA/RA-MoE found and used to drop the agreement half; nothing on parity-constrained compute-bearing allocation).

**Monitorability and safety.** No CoT effect. Fairness risk that a cost-parity objective degrades the languages it targets: per-language non-inferiority is a pre-registered gate. Pooled units reduce token-level attribution inside the trunk (interpretability tax) and the unpool shift is a leakage risk (causality doctor before any quality claim). Data rights: FLORES-plus CC-BY-SA-4.0; blt-1b CC-BY-NC measurement only; GT pairs license-cleared.

**Negative-result value.** Separates "inside the model" from "in the tokenizer" for cost equity on one matched ledger: if parity-BPE dominates, fix tokenizers (supports 2606.15044); if continuation tokens are not low-entropy, the premise that fertility is wasted compute is false; if unsupervised rates equalize, parallel supervision of allocation is unnecessary (extends 2603.29026); the FLOPs-per-aligned-sentence ledger across dense/MoD/pooled/BLT is the G19 measurement regardless of sign and tells dir 18 whether unit-count parity is the right target.

**targets_gaps.** G19, G1, G20.

---

## 4. cross-family-adapter-port  (B1 + B3 + I3 + I2)

**Claim.** A PorTAL-class task latent (one core, many tasks) trained on softmax transformers ports onto
linear-attention, hybrid (GDN/KDA), TTT, SSM and byte-level bases through a label-free functional alignment at
attention-pathway q/v sites; retention of fresh-LoRA lift is (i) a monotone function of the fraction of the
target's sequence-mixing layers that are softmax attention and (ii) invariant to tokenizer fertility when the
alignment is anchored on byte spans linked across languages by parallel span alignments, but degrades linearly in
|log fertility ratio| under token-position anchoring; a weight-space identifiability screen (Mantel correlation of
task geometries across families, incl. a 1T MoE reachable only through Tinker) and a site-attribution arm (which
LoRA factor groups carry task vs long-range-recall damage in hybrids) decide in advance whether porting can work.

**claim_scope.** portability-protocol.

**Mechanism.** Source: task latent z_tau in R^256; shared core G emits rank-8 LoRA factors for q_proj/v_proj at every
source layer, dW^S(l) = B^S(l) A^S(l), trained with labels on the 12 balanced portallib tasks (shuffled choices per
issue #28) on fla-hub/transformer-340M-10B and transformer-1.3B-100B (byte-identical Llama-2 32k vocabulary with
fla-hub GLA, startlux GDN hybrids, E2-TTT; verified 2026-09-01). Label-free target alignment at depth-matched site
l_T: run N = 2,000 unlabeled calibration sequences through both frozen bases, record residual inputs h_S, h_T and fit
R_in = argmin_R sum ||R h_T - h_S||^2 + lambda ||R||^2 (ridge, or whitened Procrustes with the signed-permutation gauge
check of 2606.31963); transport A^T = A^S R_in; obtain B^T by functional matching B^T = argmin_B sum ||f^T_l(x; W_T +
B A^T) - f^T_l(x; W_T) - R_out delta_S(x,t)||^2 (<= 300 gradient steps on calibration text). Sites: attention pathway
only for hybrids; the operator's own q/v projections for GLA/DeltaNet/E2-TTT; in_proj/out_proj for Mamba. Anchor units
(cross-tokenizer arm): byte spans a with cross-lingual links l(a) from span alignments (OmniAlign / CTFAlign); anchor
representation r_b^l(a) = mean_{t : bytes(t) intersect a != empty} h_b^l(t) (byte-range intersection pooling, defined for
subwords, patches and raw bytes); R fitted over anchor classes {a, l(a)}; fertility distance D = |log(fert_T(L)/fert_S(L))|;
hypothesis retention_token = r_0 - kappa D (kappa > 0) vs retention_byte flat. Identifiability screen: per-base task
geometry S_b[t,t'] = mean_{l,s} cos(dW_{b,t,l,s}, dW_{b,t',l,s}) over a Tinker-built zoo (Qwen3-8B-Base, Kimi-K2.6 [MLA-MoE,
1T], Qwen3.5-9B-Base, Qwen3.5-35B-A3B-Base, Nemotron-3.5-Lightning-Base; rank 8, fixed seed so dW(0) = 0; 16 tasks) and
local small bases; Mantel correlation M(b,b') against a 10^4-permutation null; the K2.6 -> Kimi-Linear-48B-A3B-Base hop
holds the tokenizer byte-identical (sha256 verified) while changing operator family. Site-attribution arm: post-training
adds dW_g for factor groups g in {attn-qk, attn-vo, gdn-qkvz-out, mlp, unembed}; long-range recall R(A, L) by generation
NIAH and translation-paired recall; leave-one-group-out and 5-group Shapley on exported adapters (Tinker exposes only the
coarse {attn, mlp, unembed} toggles and never adapts in_proj_a/in_proj_b/A_log/dt_bias — verified from exported tensors);
H1: dropping attn-qk factors recovers >= 70% of the recall loss, dropping GDN factors <= 20%. Retention r = (acc_ported -
acc_base)/(acc_freshLoRA - acc_base), macro over tasks; dose f_attn in {1, 1/3, 1/24, 0}.

**What is new.** PorTAL fits a labeled per-base alignment onto softmax-attention bases only; Theseus transports one static
task vector across widths within a family; Where Should LoRA Go adapts hybrids natively (attention pathway is the safe
site) but transfers nothing; Transport-and-Merge aligns neurons by OT to fuse base weights; BLD/ACTD move knowledge
across tokenizers through output distillation with the teacher present; Attention Amnesia measures full-SFT damage on
9B hybrids without LoRA or group attribution; UpgradeBench states "shape-incompatible hops admit no weight-space method"
and defers learned mappings. Why the "train once, port a LoRA" rejection does not apply: every rejected system ports
within a family; the objects here are cross-operator-family and cross-tokenizer hops with the attention fraction and
fertility distance as measured dose variables, a pre-registered Mantel screen, and Engram/MentorPulse (frozen artifact +
thin labeled reader) as mandatory controls. No direct prior art found through 2026-09-01 under the coverage in B §5 and I
§6 for porting a task adapter onto a KDA/GDN/GLA/DeltaNet/TTT/Mamba or byte-level base, or for byte-span-anchored alignment.

**Closest priors.**
- PorTAL (Ramp Labs blog) — https://labs.ramp.com/research/portal-portable-task-adaptation/ — 2026-07-01 — labeled per-base alignment, softmax targets only (~98%/~94% retention; Cross-LoRA ~14%).
- Theseus (ICML 2026) — https://arxiv.org/abs/2602.12952 — 2026-02-13 — training-free Procrustes + functional transport within a family.
- Where Should LoRA Go? — https://arxiv.org/abs/2604.22127 — 2026-04-24 — native LoRA placement in hybrids; attention pathway wins; recurrent adaptation -14.8 pp GSM8K.
- Cross-Model Memory Transfer via Target-Side Reader Adaptation (Engram) — https://arxiv.org/abs/2608.17050 — 2026-08-17 — frozen artifact + thin labeled reader within transformers; mandatory control.
- UpgradeBench — https://arxiv.org/abs/2608.20918 — 2026-08-21 — direct-copy retention law; learned mappings on shape-incompatible hops deferred.
- Transport and Merge — https://arxiv.org/abs/2602.05495 — 2026-02-05 — OT neuron correspondences for cross-architecture base merging.
- Cross-Tokenizer LLM Distillation through a Byte-Level Interface — https://arxiv.org/abs/2604.07466 — 2026-04-08 — output-level transfer with the teacher present; alternative-route control (with ACTD 2608.29662).
- Attention Amnesia in Hybrid LLMs (EMNLP 2026) — https://arxiv.org/abs/2606.11052 — 2026-06-09 — full CoT-SFT destroys NIAH in hybrids; QK-Restore.
- Vowel Signs Are Not Letters — https://arxiv.org/abs/2608.26449 — 2026-08-26 — fertility floors as the dose variable.

**Falsifiable predictions.**
- P1 (dose-response, iso-tokenizer 340M ladder): retention monotone in f_attn — transformer control >= 0.85; GDN 3:1 hybrid (attention sites) >= 0.50; single-attention GDN 0.20–0.50; GLA / E2-TTT <= 0.30; Spearman rho(f_attn, retention) >= 0.8 over >= 6 targets x 12 tasks; adding GDN q/v sites to the hybrid port lowers retention by >= 0.10.
- P2 (label-free cost): label-free alignment reaches >= 70% of PorTAL's label-fitted alignment on the same target and beats Cross-LoRA and Theseus by >= 0.20 retention.
- P3 (tokenizer axis, from-scratch 60M triplet bytes / BPE-8k / BPE-32k on identical multilingual bytes, 10 languages): token-anchored retention falls >= 0.15 per unit D while byte-span-anchored slope |kappa'| <= 0.05 and mean retention >= 0.60; byte-span beats token anchoring by >= 0.15 on Hindi/Thai/Tamil and <= 0.05 on Latin scripts; Qwen3-0.6B-Base -> Bolmo-1B latent transformer recovers >= 0.40 vs <= 0.15 with patch-position anchoring.
- P4 (screen): M(Qwen3-8B, Qwen3.5-9B-Base) >= 0.60 and M(Kimi-K2.6, Kimi-Linear-48B-A3B-Base) >= 0.50 with permutation-null 95th percentile <= 0.25; the tokenizer-fixed K2.6 -> Kimi-Linear hop exceeds the Qwen3-8B -> Qwen3.5-9B hop by >= 0.10 retention.
- P5 (site attribution): rank-32 CoT-SFT on Qwen3.5-9B-Base / Qwen3.5-35B-A3B-Base lowers NIAH-S2 at 32K by >= 15 pp while Kimi-K2.6 (dense MLA) drops <= 5 pp at matched SFT-loss reduction; dropping only self_attn q/k factors recovers >= 70% of lost recall and keeps >= 80% of the GSM8K gain; translation-paired recall degrades >= 1.5x more than same-language recall.

**Kill conditions.** Hybrid attention-site retention <= 0.20 (no better than Cross-LoRA/Theseus); rho(f_attn, retention) < 0.3; random-latent or latent-swap controls recover >= 50% of the ported lift (alignment, not latent, carries the task); byte-span anchoring <= token anchoring or |kappa - kappa'| < 0.05 (tokenizer axis closed; PorTAL's silent crossing vindicated); Mantel M < 0.30 for every cross-family pair while within-family >= 0.70 (task geometry is family-specific: stop before hypernetwork training); fresh LoRA on 64 labeled target examples matches the label-free port; gains disappear on held-out prompt formats (2608.09490); LoRA CoT-SFT shows no >= 5 pp recall loss on any hybrid (site-attribution arm becomes a "LoRA is immune to Attention Amnesia" positive) or attribution is diffuse (no group > 40%).

**Cheapest decisive pilot.** Phase 0 (CPU): transport algebra on a random 2-layer transformer/DeltaNet pair (planted rotation recovered; signed-permutation invariance; closed-form B^T); tokenizer doctors (vocabulary diffs: 32,000 identical pairs across the fla-hub/startlux/E2-TTT ladder; 50,254 for Pythia-160M vs mamba-130m-hf); task-suite audit (shuffle choices, per-index prior at chance; fix rows[:1000] slicing per issue #27); gradient-access audit that alignment fits never read labels; byte-range intersection pooling for BPE/byte/patch segmentations and a synthetic two-tokenization identifiability test; Mantel-screen algebra on synthetic dW; enumerate covered modules of a 1-step Tinker export per family (a G22 deliverable); hosted zoo (16 tasks x ~0.3M tokens on 5 bases; Kimi ~4.8M tokens ~ $25). Phase 1 (<= 16 GPU-h, operator axis, decisive): core training on the two fla-hub transformers (~3 h); fresh per-task LoRA oracles for 12 tasks x 7 targets (~4 h); label-free alignments for gla-340M-15B, gdn-340m-isp-hybrid-3to1-10b, gdn-340m-pas-fa-layer12-10b, e2-ttt-swiglu-340M-15B, delta-net-1.3b-8k, gla-1.3B-100B, mamba-1.3B-100B (~2.5 h); Cross-LoRA and Theseus baselines (~1 h); PorTAL label-fitted reference on two targets (~1.5 h); qwen3-0.6b-base -> qwen3.5-4b meaning-class vs monolingual calibration (~3 h); 3 seeds on alignments/evaluations, core trained once (stated limit). Conditional stages (new contracts): tokenizer axis (three 60M from-scratch models ~6 h; Bolmo-1B sha 7a80d2e3db317282229afc34c5f24333a8ebe846 and qwen3.5-4b ports ~5 h; OT / greedy-token / BLD baselines ~2 h; ~16 h); site-attribution arm (local qwen3.5-4b / Qwen3.5-9B-Base rank-32 eight factor-group arms x 3 seeds ~8 h; hosted 7 models x {attn on, off} <= $800; Shapley surgery on exported 27B/35B-A3B adapters ~4 h); kimi-linear-48b-a3b-base and llada-8b-base targets after a positive screen.

**pilot_gpu_hours.** 16.

**Controls.** Fresh per-task LoRA on the target with labels (oracle; iso-rank r8 q/v and full-module r16 sweeps); Cross-LoRA (2508.05232) and Trans-LoRA-style synthetic-data transfer (2405.17258); Theseus (2602.12952); PorTAL label-fitted alignment (upper reference); Engram frozen artifact + thin labeled reader (2608.17050); KV-translation activation port (2608.30963); Hyper-X target-native language x task adapter (2205.12148); Transport-and-Merge OT alignment (2602.05495); token-position anchoring and greedy byte-prefix token alignment; BLD (2604.07466) / ACTD (2608.29662) output distillation at equal compute; parity-aware / \p{L}+-fixed tokenizer arm (2606.15044, 2608.26449) and romanized-input arm (2608.25904); random-latent, latent-swap and anchor-permutation probes; permuted-task null for the Mantel screen; seed-matched inits per base; direct copy where shapes allow (UpgradeBench protocol); unadapted base noise floor, MLP-only arm, drop-q/k surgery (LoRA analogue of QK-Restore), decay-projection arm locally, length-stratified curves (2608.10296); held-out prompt formats (2608.09490); two-forward-pass prefix-invariance audit on adapted hybrids (2608.22876); iso-parameter / iso-wall-time ledgers; 3 seeds with paired clustered SEs; token/dollar ledger; model+adapter as the tested object.

**Kevin advantage.** Honest split: the iso-tokenizer English ladder needs only the 8xH100 node and the sealed task x base harness. Unique pieces: parallel corpora with span alignment across abugida/CJK/Latin scripts as the anchor supply and fertility regimes; registered cross-family targets with pinned revisions (kimi-linear-48b-a3b-base [KDA], mamba-130m-hf, llada-8b-base, blt-1b [discovery only], qwen3.5-4b/9b; Bolmo-1B to register); Tinker as the adapter-zoo factory at 9B–1T incl. the tokenizer-identical Kimi-K2.6 -> Kimi-Linear hop and six operator families under one API (two not trainable locally); the harness for sealed task x base x language cells.

**collision_risk.** medium (B §5 and I §6 searches: arXiv/HF/OpenReview on adapter port x Mamba/linear attention/hybrid/cross-architecture -> only base conversion; Ramp's roadmap is description encoders; HeteroFusion / Transport-and-Merge groups have live cross-family alignment code; the Attention Amnesia authors are the obvious group to extend to LoRA).

**Monitorability and safety.** Weight-space adapters; the reasoning medium is unchanged. Ported adapters may carry source behaviours incl. backdoors across families: a refusal/harm regression and a poisoned-source-task transfer measurement on each target before and after porting are mandatory deliverables. Data rights: portallib-tasks public (license to check); fla-hub transformer/delta_net checkpoints have no stated license (publication requires resolution); startlux Apache-2.0, E2-TTT MIT, Bolmo-1B Apache-2.0, BLT-1B CC-BY-NC (non-publication), Kimi-Linear MIT, Kimi-K2.6 modified-MIT, Tinker export permitted; parallel corpora used only as unlabeled calibration stimulus, never redistributed.

**Negative-result value.** If f_attn does not govern portability, either task skills live in operator-agnostic residual directions (any base is a target; UpgradeBench's "no weight-space method" is refuted for learned mappings) or porting fails everywhere (confirmed for learned mappings too); a failed Mantel screen bounds every PorTAL successor (cross-family porting must go through function/distillation, closing G3 as a weight-space gap); if token anchoring is fertility-invariant, the tokenizer axis is closed with numbers; if byte-span anchoring fails on Bolmo, byte-level latent spaces are not adapter-compatible with subword models (bounds byteification retrofits and dir 18). The first sealed multi-family task x base portability cell with shuffled-choice hygiene, the Tinker module-coverage table, and "LoRA is/is not immune to Attention Amnesia" are deliverables either way.

**targets_gaps.** G3, G4, G22.

---

## 5. icl-rule-distillation-port  (B2)

**Claim.** A pretrained transformer's implicit in-context update can be distilled into an explicit canonical
fast-weight rule (a base-independent 64-dimensional associative state plus a learned write rule) that, frozen, ports
through label-free read/write maps onto bases of other operator families and reproduces a measurable fraction of
their in-context gains with no demonstrations in the window; parallel translations identify that the rule writes
content rather than surface form.

**claim_scope.** architecture-causal.

**Mechanism.** Frozen transformer T, demonstration stream c_1..c_n of formatted (x_i, y_i) pairs, probes q in Q; implicit
update Delta_i(q) = log p_T(.|q, c_{<=i}) - log p_T(.|q, c_{<i}). Canonical memory M^k in R^{64x64}, rank-8, at K = 4
residual sites (depth fractions 0.25..1.0); base b attaches through task-blind rank-8 maps P_b^k (read, 64 x d_b) and
Q_b^k (write, d_b x 64). Read at every query position: h^k <- h^k + Q_b^k M^k P_b^k h^k. Write once per demonstration,
strictly after the probe of step i-1: key k_i = P_b^k hbar^k(x_i), value v_i = P_b^k hbar^k(y_i), error e_i = v_i - M^k k_i;
shared rule R_theta emits (rho_i, eta_i, u_i, w_i) and M^k_{i+1} = Pi_8[rho_i M^k_i + eta_i u_i w_i^T]. Derived-rule
baselines at the same interface: delta rule, Kaczmarz step eta_i = eta/(||k_i||^2 + eps), OSDN diagonal preconditioning,
Falcon-1/2/3 normalized rules. Distillation (new step): with the source base T itself and demonstrations removed from
the window, minimize L_dist = sum_i sum_q KL(p_T(.|q, c_{<=i}) || p_{T,M_i}(.|q)) + lambda_cause L_cause over theta, P_T,
Q_T with truncated BPTT through 8 writes, L_cause penalizing any read of M_i by probes issued before write i (SR-TTT
startup-causality gate). Translation equivariance: L_eq = ||Delta M(c_i) - Delta M(c_i^(B))||_F^2; evaluation write-A/read-B.
Port: freeze R_theta; fit only P_b', Q_b' label-free by the functional alignment of candidate 4 on unlabeled text
containing no evaluation task family; evaluate b' with no context after i writes against native ICL, derived rules at
equal state bytes, a D16-style rule meta-trained on prequential loss, and a MentorPulse-style live mentor (upper
reference). Effective step size s_i = eta_i ||u_i|| ||w_i|| logged per write.

**What is new.** Can Gradient Descent Simulate Prompting? meta-trains the same LM so a gradient step mimics conditioning
(not externalized, not portable); Learning without training derives analytically that context equals a low-rank MLP
update inside one block (single model, no learned rule); Algorithm Distillation distills a learning algorithm INTO a
sequence model's in-context behaviour (reverse direction, no fast-weight rule); Attention-to-Mamba and HALO distill base
weights (WHAT), here bases stay frozen and only HOW moves; Modular TTT factorizes the inner rule but never transfers it.
No direct prior art found through 2026-09-01 under the coverage in B §5 for distilling a transformer's in-context update
into a portable explicit rule (learned-update-rules G6, G1, G4).

**Closest priors.**
- Can Gradient Descent Simulate Prompting? — https://arxiv.org/abs/2506.20989 — 2025-06-26 — meta-trained self-update emulating conditioning; not externalized.
- Learning without training: the implicit dynamics of ICL — https://arxiv.org/abs/2507.16003 — 2025-07-21 (v4 2026-06-02) — analytic low-rank update inside one block; no learned rule, no cross-architecture test.
- Algorithm Distillation — https://arxiv.org/abs/2210.14215 — 2022-10-25 (Mamba scaling 2506.13892, 2025-06-16) — algorithm -> sequence model; here the reverse.
- Attention to Mamba — https://arxiv.org/abs/2604.14191 — 2026-04-01 — cross-architecture base distillation (WHAT).
- Modular TTT — https://arxiv.org/abs/2608.07110 — 2026-08-07 — composable inner-rule DAG, never transferred; MentorPulse (2608.20927, 2026-08-21) as live-mentor upper reference.

**Falsifiable predictions.**
- P1 (identifiability on the source): on sealed held-out ICL task families with 8 demonstrations, the distilled rule with no context reproduces >= 70% of the transformer's few-shot-over-zero-shot gain, while the best derived rule (delta/Kaczmarz/OSDN/Falcon) at the same interface and state bytes reproduces <= 40%.
- P2 (port ordering): on the iso-tokenizer 340M targets with label-free P/Q, the ported rule recovers >= 0.50 of the GDN 3:1 hybrid's native in-context gain, 0.30–0.50 on GLA/E2-TTT/DeltaNet, <= 0.30 on Mamba, and beats the best derived rule by >= 0.10 on the hybrid and on DeltaNet.
- P3 (equivariance): with lambda_eq > 0, write-A/read-B accuracy on Qwen3-0.6B-Base -> Qwen3.5-4B is within 5 points of write-A/read-A; with lambda_eq = 0 the gap is >= 15 points.
- P4 (dynamics signature): logged effective step size follows s_i ~ i^(-gamma) with gamma = 1.0 +/- 0.3, which no fixed-eta derived rule reproduces.

**Kill conditions.** P1 fails (derived rule ~ distilled rule: the in-context HOW at this interface is GD/delta; publish as a behavioural ICL-as-GD confirmation and stop); the ported rule is <= the best derived rule on every target family; the startup-causality audit or the two-forward-pass prefix-invariance audit finds probe leakage or non-causal reads; a single adversarial demonstration persists in M across the declared reset, or lambda_eq > 0 costs > 10 points monolingual accuracy.

**Cheapest decisive pilot.** Phase 0 (CPU, fp64): synthetic ICL linear regression (d = 8); train a 2-layer softmax transformer, distill its implicit update into R_theta with a 16-d state; compare error curves with one-step GD and RLS; attach the frozen rule to a tiny DeltaNet trained on the same distribution; causality self-test. Phase 1 (<= 4 H100-h): EleutherAI/pythia-160m -> state-spaces/mamba-130m-hf (identical GPT-NeoX vocabulary; pythia-160m sha 50f5173d932e8e61f858120bcb800b97af589f46 to register): distill on Pythia, port to Mamba, derived-rule and native-ICL references; stop here if P1 fails. Phase 2 (<= 8 H100-h): fla-hub/transformer-340M-10B -> startlux gdn-340m-isp-hybrid-3to1-10b, fla-hub/gla-340M-15B, zeyun-zhong/e2-ttt-swiglu-340M-15B; D16-style prequential sibling and MentorPulse-style upper reference. Phase 3 (<= 4 H100-h): equivariance and write-A/read-B on qwen3-0.6b-base -> qwen3.5-4b with parallel demonstrations. 3 seeds on distillation and ports; SIGUSR1-resumable truncated BPTT.

**pilot_gpu_hours.** 16.

**Controls.** Native ICL with demonstrations in the window, per base; derived rules at the same interface and state bytes (delta, Kaczmarz 2605.08587, OSDN 2605.13473, Falcon 2608.27763); Modular-TTT-style rule trained natively with labels (oracle); E2-TTT and TTT-NTP drop-in fast weights; D16-style prequential-trained rule (sibling); MentorPulse live mentor (upper reference); Engram frozen memory + reader (2608.17050) and KV translation (2608.30963); sender-activation -> transient receiver LoRA (2605.13839); no-update, random-rule, alignment-only and iso-state-bytes / matched-update-count arms; two-forward-pass prefix-invariance audit; reset and deletion attestation with a hash-chained write log; >= 3 seeds; per-arm hyperparameter search.

**Kevin advantage.** Public substrates (iso-tokenizer ladder, Pythia/Mamba pair) are not unique; unique pieces are General Translation's parallel corpora for the equivariance loss and the write-A/read-B probe, the repo's causality gates and CPU paired oracle inherited from the SR-TTT retraction, and the SIGUSR1-resumable harness for long truncated-BPTT meta-training. Tinker cannot help (no hidden states, no optimizer access).

**collision_risk.** high (B §5 searches on ICL distillation / implicit update / fast-weight rule; ICL-as-GD is a crowded theory line and Modular TTT / D16-style rule learning could add a distillation objective at any time).

**Monitorability and safety.** A canonical base-independent state lets one probe read the memory on every base (monitorability gain over opaque per-model fast weights) but hidden state replaces visible demonstrations: every write is logged (hash-chained), reset attestation required, demonstration-poisoning persistence is a pre-registered red line. Data: Pythia Apache-2.0, fla-hub MIT/unstated, startlux Apache-2.0, E2-TTT MIT; parallel data as unlabeled paired stimulus only.

**Negative-result value.** If derived rules match the distilled rule, this is the first behavioural, causality-verified test at 160M–4B that a transformer's in-context update is functionally a GD/delta rule at a fixed low-rank interface, emptying Direction 16's premise for a few GPU-hours; if the rule distils but does not port, per-family ICL theory (GD emulation vs online GD vs Bayes filter) receives its first cross-family behavioural measurement.

**targets_gaps.** G5, G2, G7.

---

## 6. hybrid-state-provenance-ledger  (C1 + H1 + C3)

**Claim.** Because every production linear-attention layer has a state-independent affine transition, one exactly
transported shadow object per tagged segment gives 2026 GDN/KDA hybrids exact per-segment read influence, exact
per-segment retention, and a zero-parameter unwrite; a random-code shadow state driven by the layer's own keys and
gates compresses the same identity into a streaming O(m d_k) per-segment (or per-token) attribution sketch — the
missing attention map for linear layers; whether the zero-parameter unwrite recovers the replay counterfactual on
tasks (not on state norms), whether influence is a usable injection monitor and a causally faithful attribution, and
whether a small learned corrector for the forcing residual closes the remaining gap, are decidable on pinned
checkpoints in <= 16 GPU-hours.

**claim_scope.** attachment-capability.

**Mechanism.** Linear-transition family: S_t = S_{t-1} A_t + b_t with (A_t, b_t) functions of x_t only — GDN A_t =
alpha_t (I - beta_t k_t k_t^T), b_t = beta_t v_t k_t^T; KDA A_t = Diag(alpha_t)(I - beta_t k_t k_t^T); GDN-2, Mamba-2 (A_t =
alpha_t I), RWKV-7 (Diag(w_t) - k_t (a_t ⊙ k_t)^T) likewise. (a) Segment ledger: for a tagged segment p = [j, j+L),
D_p = S_{j+L-1} - S_{j-1}, transported as D_p(t) = D_p(t-1) A_t (cost identical to the state update; 1 MiB/layer/segment
bf16 on Kimi-Linear-48B and Qwen3.5-4B); S_t - D_p(t) is exactly the state had p been skipped with later (k, v, alpha,
beta) unchanged (Prop. 1 of 2607.27539; verified fp64 to <= 7.5e-16 for GDN/KDA/GDN-2/Mamba-2/RWKV-7 and shown to FAIL,
residual 3.0e-01, for an MLP fast-weight TTT rule — design/c_state_doctor.py). Token-level refinement: u_j = v_j - alpha_j
S_{j-1} k_j, r_{j,t} = beta_j (A_{j+1}...A_t)^T k_j gives S_t = sum_i v_i r_{i,t}^T and S_t - u_j r_{j,t}^T removes token j's write
and erase while keeping its decay. Exposed quantities: influence pi_p(t) = ||D_p(t) q_t|| / ||S_t q_t||; retention rho_p(t)
= ||D_p(t)||_F / ||D_p(j+L-1)||_F; full-stack unwrite S_t <- S_t - D_p(t) plus masking p's KV entries in the 1-in-4
global layers. (b) Coded shadow (compression): since the recurrence is linear in v, o_t = sum_j A_tj v_j with implicit
attention A_tj = b_j r_j(t)^T q_t; define P_t in R^{m x d_k} by the same recurrence with values replaced by codes,
P_t = a_t P_{t-1}(I - b_t k_t k_t^T) + b_t f_{g(t)} k_t^T, g(t) the segment id, F = [f_1..f_n] in {+-1/sqrt(m)}^{m x n} a fixed
Bernoulli code; then P_t q_t = F u_t with u_t[s] = sum_{j in s} A_tj the per-segment attribution vector — exact for n <= m
(u_t = F^+ P_t q_t), sparse-recoverable by OMP/LASSO for n >> m when m >= C s log(n/s); token level g(t) = t gives a
streaming count-sketch of the whole implicit-attention row; Mamba-1 per channel analogously. (c) Conditional trained
stage (Hybrid Context Eraser): keep (a) for linear layers; for global layers drop p's KV and insert m = 4–16 learned
steering KV pairs from a corrector phi (<= 20M params, shared across layers); for linear layers phi emits a rank-r
correction Delta S = U V^T (r <= 8) from (pooled S_t, pooled D_p(t), span summary, gap g) to absorb the forcing residual
(the part of the true counterfactual due to later tokens processed with p present — 2607.27539 median forcing ratio
0.84); teacher = the same frozen model run with p removed; loss = KL over a 512-token window + residual-recall penalty;
stronger arm: unwrite-consistent LoRA on the base (or full parameters in a 135M from-scratch hybrid). Certificate:
R(g) = (EM_unwrite - EM_poisoned)/(EM_replay - EM_poisoned) and F(g) = 1 - KL(teacher||erased)/KL(teacher||unerased)
versus gap g, layer type and segment type; the linear component's fixed-input exactness is audited separately by the
two-forward-pass prefix-invariance test so all residual error is attributable to forcing.

**What is new.** 2607.27539 (Subtract/Transport/Replay) proves the transport identity and reports norm-level exactness on
Kimi-Linear-48B only; here the behavioral fidelity curve R(g) against a paired replay oracle, the two-view influence
monitor and retention certificate, and the compressed attribution sketch are added on the same pinned model plus
Qwen3.5-4B and Mamba-130M, and the forcing residual — declared structural there — is tested for learnability. Zimerman
et al. and Hidden Attention of Mamba compute full implicit attention offline; LaTIM decomposes token interactions per
model; here the row is sketched in streaming O(m d_k) with recovery guarantees, on erase-type delta-rule operators, and
validated against a leave-one-out causal oracle (TwinKV protocol) and across translations. DeltaLog defers
materialisation and never removes or attributes; Tail-Replay reconstructs from a suffix and cannot excise an interior
segment (our forget-everything-old control); WriteSAE does cache-level write replacement without attribution;
KVEraser learns KV steering in transformers only; Dependency-Guided Rollback works at the harness level; AttnTrace /
Attention Tracker attribute injections through softmax weights only. No direct prior art found through 2026-09-01 under
the coverage in C-state-semantics.md and H §4/§5 for task-level unwrite fidelity, streaming code-sketched per-source
attribution, or a learned forcing-residual corrector for delta-rule/KDA/SSM operators.

**Closest priors.**
- Subtract, Transport, or Replay? Auditable Deletion from Language-Model Memory — https://arxiv.org/abs/2607.27539 — 2026-07-30 (v2 2026-08-13) — transport identity, norm-level metrics only, forcing residual declared structural.
- A Unified Implicit Attention Formulation for Gated-Linear Recurrent Sequence Models — https://arxiv.org/abs/2405.16504 — 2024-05-26 — full implicit attention offline; here a streaming sketch with recovery guarantees.
- LaTIM — https://arxiv.org/abs/2502.15612 — 2025-02-21 — token-to-token decomposition for Mamba; no sketch, no delta-rule coverage, no leave-one-out faithfulness.
- KVEraser — https://arxiv.org/abs/2606.17034 — 2026-06-15 — learned KV steering eraser, transformers only (+24% latency vs 17.6x); here extended to recurrent layers with a fidelity-vs-gap certificate.
- DeltaLog — https://arxiv.org/abs/2608.15533 — 2026-08-16 — bounded update log for decode throughput; no removal or attribution.
- Tail-Replay — https://arxiv.org/abs/2608.30310 — 2026-08-31 — suffix-replay state reconstruction (92.8–99.9%); mandatory control.
- WriteSAE — https://arxiv.org/abs/2605.12770 — 2026-05-12 — rank-1 write replacement in GDN/Mamba-2/RWKV-7; no attribution to past segments.
- TwinKV — https://arxiv.org/abs/2608.27128 — 2026-08-27 — leave-one-out shows attention magnitude vs causal contribution rho = -0.004; faithfulness comparator.
- Dependency-Guided Rollback Repair — https://arxiv.org/abs/2608.10502 — 2026-08-11 — harness-level rollback with selective replay.

**Falsifiable predictions.**
- P1 (unwrite fidelity, Qwen3.5-4B, 256-token poisoned tool result, 500 paired episodes per cell): full unwrite (transport + KV-mask) recovers R(g = 512) >= 0.60 and R(g = 8K) >= 0.30 of the replay oracle's exact-match gap; transport-only < 0.20 at every gap; KV-mask-only >= 50% of full. Embarrassing if R(512) < 0.30 on both Qwen3.5-4B and Kimi-Linear-48B.
- P2 (monitor): pi_p(t) from linear layers alone reaches AUROC >= 0.85 on an InjecAgent/AgentDojo-style tool-result injection set, within 0.05 of attention attribution from the 8 global layers, and the union improves AUROC >= 0.02; rho_p(t) predicts per-fact recall failure on a 16-fact probe with AUROC >= 0.80 vs <= 0.70 for DASC's static horizon and SANE's norm statistic.
- P3 (sketch exactness and faithfulness): on qwen3.5-4b GDN layers with n = 16 passages, m = 64, decoded u_t equals the O(T^2) aggregation to < 1e-3 relative at 100% of positions; with n = 1,024 sentences OMP recovers the top-5 support at >= 90% of positions whose row carries >= 80% mass in its top 5; aggregated recurrent-layer attribution identifies the gold passage top-1 >= 60% on correct items (chance 3.1%); Spearman rho between attribution mass and leave-one-out removal effect >= 0.5 (TwinKV: -0.004 for softmax magnitude).
- P4 (cross-lingual, Kevin's asset): with passages translated and content fixed, JSD between attribution distributions is < 0.1 for en<->de/fr and >= 2x larger for en<->th/hi.
- P5 (trained stage, conditional on R(2K) < 0.9): frozen Qwen3.5-4B + phi (~50M synthetic retraction tokens) reaches >= 90% exact-match agreement with the replay teacher at g = 2K vs <= 60% zero-parameter and <= 75% for an attention-only KVEraser-style eraser; erase latency <= 5% of recomputation at 16K; phi trained on generic spans loses <= 5 points on unseen injected-instruction spans.

**Kill conditions.** R(g = 512) < 0.30 on both hybrids AND phi never beats attention-only erasing by >= 5 points (the recurrent state carries little retractable influence in 3:1 hybrids; publish the behavioral extension of 2607.27539's negative); pi_p AUROC < 0.75 or no gain over attention-only attribution; median top-5 mass < 0.2 in every recurrent layer of all three families (instrument exact but uninformative; support for 2606.15378); rho < 0.2 against leave-one-out (exact linear contribution is not causal effect); F(2K) < 0.5 after training (forcing residual not compressible: hybrids must budget O(suffix) replay); erase cost not >= 3x cheaper than checkpoint replay at 16K; residual recall of erased content exceeds the teacher's by > 2 points (erasure hides rather than removes); any prefix-invariance leak.

**Cheapest decisive pilot.** Phase 0 (CPU, partly done 2026-09-01): fp64 doctor design/c_state_doctor.py certifies segment transport, write-only ledger and token unwrite for GDN/KDA/GDN-2/Mamba-2/RWKV-7 (<= 8.9e-16) and the TTT-MLP failure; extend with P_t q_t = F u_t to 1e-12 under erase and decay, RIP recovery curves over m in {16,32,64,128}, n in {64..4096}, adversarial correlated-key streams, the two-forward-pass audit and a retrieval-impossible control corpus; synthetic retraction-episode generator with the paired replay oracle. Phase 1 (frozen, inference only, ~11 GPU-h): registry qwen3.5-4b, mamba-130m-hf, delta-net-1.3b-8k, kimi-linear-48b-a3b-base (bf16, 2–4 H100), startlux gdn-1.3b-isp-hybrid-3to1-50b; synthetic retraction suite (fact / tool-result / poison segments 64–512 tokens, gaps 128/512/2K/8K, 500 paired episodes per cell, McNemar); injection set for the monitor; 16-fact recall probe; 16/32/64-passage distractor QA with one gold passage, the same items machine-translated, leave-one-out oracle on 200 items. Phase 2 (conditional, ~5 GPU-h): train phi on frozen qwen3.5-4b and evaluate F(g) and P5 against every control; the 135M unwrite-consistent from-scratch arm (2 arms x 3 seeds x 1B tokens, ~8 GPU-h) is a new contract.

**pilot_gpu_hours.** 16.

**Controls.** Paired checkpoint replay from the segment start (exact oracle, O(suffix)) and never-stored model; KV-mask-only and transport-only ablations; Tail-Replay suffix restart (5–10%) excluding the segment (2608.30310); do-nothing and ICUL-style "ignore the previous tool result" instruction; KVEraser-style attention-only learned eraser for the hybrid's global layers; Dependency-Guided Rollback as the harness-level baseline where the task allows; O(T^2) implicit attention (2405.16504) as the exact attribution oracle; LaTIM (2502.15612); input x gradient and integrated gradients; softmax attention mass in the same hybrid's global layers; a linear probe for passage identity trained on the readout (must be beaten with zero supervision); leave-one-out causal oracle (TwinKV protocol); Attention-Tracker / AttnTrace attribution on the global layers (monitor baseline); DASC weight-derived retention horizon and SANE norm-anomaly statistic; a 135M SWA+sinks model as the all-token-addressable erasability reference (2608.28444); equal-latency ledger with CPU overhead charged; two-forward-pass prefix-invariance audit on every path; generation exact match with paired McNemar; all seeds and negative cells reported.

**Kevin advantage.** Moderate: kimi-linear-48b-a3b-base (the exact model behind the published negative), qwen3.5-4b, mamba-130m-hf and delta-net-1.3b-8k are pinned; the harness's deterministic paired-replay oracle and hash-chained receipts are the estimand's machinery (harness/causal_memory_trials.py); 8xH100 makes the 48B bf16 runs routine; parallel data makes the content-fixed cross-lingual attribution probe (P4) buildable. The instrument itself needs none of these (honest).

**collision_risk.** medium (C and H §4 searches: arXiv/HF on deletion/unwrite/attribution x linear attention/SSM/delta rule; 2607.27539's author lists streaming certificates as future work; KVEraser group could extend to hybrids; 2607.11796 attributes to state modes, not sources).

**Monitorability and safety.** Strictly increases monitorability: an exact per-segment influence/provenance channel for the 3/4 of hybrid layers that have no attention weights, enabling poison-source attribution (attribution, not defence — 2608.21230 shows provenance screening does not defend); retraction of injected tool output is safety-positive; dual-use of a learned eraser (removing safety-relevant spans): restrict erasable spans to typed tool/retrieval segments, never system/developer messages, log every unwrite with its certificate, report residual recall and the prefix-invariance audit as first-class safety metrics. No CoT effect. Data: synthetic suites, public injection benchmarks, public QA sets, FLORES; GT parallel data only under license.

**Negative-result value.** If R(g) is small and phi cannot close it, the forcing term dominates behavior, not only state norms — deployment-relevant for every DASC/Tail-Replay/DeltaLog user and a systems-relevant negative (hybrid serving must budget O(suffix) replay for retraction); if pi_p fails, recurrent reads carry little injection signal and hybrid monitors can stay attention-only; diffuse rows give mechanistic evidence that 3:1 hybrids' recurrent layers do not do source-selective recall (sharpens 2606.15378); unfaithful rows caution the whole implicit-attention interpretability line. The sketch identity, transport doctor and paired-replay estimand remain as harness instruments for G2/G13.

**targets_gaps.** G7, G20, G2, G13.

---

## 7. translation-equivariant-state-writes  (C2)

**Claim.** A fixed-size recurrent state that stores meaning should write the same segment delta for two translations
of the same span; supervising that on parallel data in half the heads of a GDN/KDA hybrid closes the cross-lingual
recall gap (key written in language A, queried in language B) at equal monolingual recall, and the same delta object
is the instrument that first measures whether 2026 hybrids store meaning or surface.

**claim_scope.** architecture-causal.

**Mechanism.** In a 3:1 GDN (or KDA) hybrid, for an aligned parallel span pair (a^A, a^B) placed after a shared prefix c,
the per-head recurrent-state contribution of the span is the exact segment delta D^{(l,h)}(a) = S_after - S_before
(S_before identical for both languages). Designate a head subset E (half the heads of every linear layer). L = L_LM +
lambda [L_eq + L_nce], L_eq = mean_{l, h in E} (1 - cos(vec D(a^A), vec D(a^B))), L_nce = -log(exp(s(D^A, D^B)/tau) / sum_{B'
in batch} exp(s(D^A, D^{B'})/tau)) with s cosine over concatenated E-head deltas and negatives from non-parallel spans
(prevents D -> 0 collapse); lambda in {0.1, 0.3}, tau = 0.07; heads outside E receive no alignment term and may keep
surface information. This supervises what the state WRITES — the object later reads S_t q_t consume — not residual-stream
token representations (PreAlign, Middle-Layer alignment), sentence embeddings, or byte boundaries (dir 18). Instrument:
translation-paired MQAR (TP-MQAR): N facts written as natural sentences in language A among distractors and queried in
language B, generation exact match, key-language x query-language matrix, N in {4, 16, 64}, context 1K–16K (4x training
length), per-script decay curves at matched content, and a functional swap test (replace D^A by D^B in E heads and
re-read; GI-SAE's interchangeability criterion). Frozen-checkpoint screen (hybrid vs dense sibling), then from-scratch
60–135M bilingual arms.

**What is new.** MLNeedle establishes cross-lingual needle retrieval for 2024 transformers without recurrent operators,
capacity curves, per-script decay, or intervention on the write; Leino & Tiedemann show parallel data in the mixture
barely moves representation alignment — here an explicit loss acts on the recurrent write and their result is the
pre-registered null for the bitext-only arm; Middle-Layer Representation Alignment and PreAlign align residual/embedding
representations of transformers and measure transfer accuracy — here the matrix-shaped state delta of linear layers is
aligned and recall from state is measured; FAAST uses MT pairs as fast-weight labels, not as a write-equivariance target;
GI-SAE supplies the functional-swap methodology. No direct prior art found through 2026-09-01 under the coverage in
C-state-semantics.md for translation-equivariance of recurrent-state writes or a translation-paired MQAR (benchmarks-eval
G2, seq-operators G1).

**Closest priors.**
- MLNeedle — https://arxiv.org/abs/2408.10151 — 2024-08-19 — cross-lingual needle retrieval on 2024 transformers; baseline per verification pass (with OneRuler 2503.01996).
- On the limited utility of parallel data (Leino & Tiedemann) — https://arxiv.org/abs/2603.29026 — 2026-03-30 — mixture-level parallel data barely moves alignment; pre-registered null.
- Middle-Layer Representation Alignment (ACL 2025) — https://arxiv.org/abs/2502.14830 — 2025-02-20 — residual-stream alignment during task training; matched control.
- PreAlign — https://arxiv.org/abs/2407.16222 — 2024-07-23 — embedding-level alignment before pretraining; transformer-only.
- GI-SAE — https://arxiv.org/abs/2608.23809 — 2026 — functional interchangeability criterion (geometric similarity is not functional swap-ability).

**Falsifiable predictions.**
- P1 (frozen TP-MQAR, N = 16, 8K, En<->De and En<->Zh): Qwen3.5-4B shows a cross-lingual gap (A != B minus A = B) >= 10 exact-match points exceeding the dense Qwen3-4B sibling's gap by >= 5 points; Kimi-Linear-48B-A3B-Base shows >= 8 points. Embarrassing if the hybrid gap is within 3 points of the dense model.
- P2 (60–135M bilingual 3:1 GDN hybrids, 3 seeds): the equivariance arm cuts the cross-lingual gap by >= 50% relative at monolingual recall within 2 points and LM loss within 0.5%, while the middle-layer hidden-state alignment control at the same lambda and data closes <= 25%.
- P3 (functional swap): replacing D^A by D^B in E heads preserves >= 80% of recall in the equivariance arm vs <= 40% in the baseline.
- P4 (script): baseline recall half-life for facts written in Thai/Bengali is <= 0.7x Latin at matched content; the equivariance arm raises the ratio to >= 0.9.

**Kill conditions.** Frozen screen shows no hybrid-specific gap (within 3 points of the dense sibling: fixed-size states already store meaning; publish the instrument result); the equivariance arm does not beat the matched hidden-state control by >= 5 points (generic representation alignment suffices); LM loss > 1% worse or ||D|| in E heads shrinks > 30% (collapse/tax); the SWA+sinks hybrid arm shows the same cross-lingual gap (not a recurrent-state phenomenon).

**Cheapest decisive pilot.** Phase 0 (CPU): TP-MQAR generator with span alignment from GT corpora (OPUS/FLORES where licenses require), leakage checks (retrieval-impossible control, first-token perturbation, exclusive causal writes), fp64 check that D^A and D^B are exact span deltas. Phase 1 (frozen, <= 2 GPU-h): qwen3.5-4b vs the dense Qwen3-4B sibling (to register), kimi-linear-48b-a3b-base, startlux 340M/1.3B GDN hybrids as English-only sanity controls. Phase 2 (from scratch, <= 12 GPU-h): 60M 3:1 GDN hybrids on 1B tokens of En + {De, Zh, Th} monolingual plus parallel data, 5 arms x 3 seeds, per-arm LR sweep (4 values) at the smallest rung, fla >= 0.5.2 kernels, SIGUSR1-resumable jobs.

**pilot_gpu_hours.** 14.

**Controls.** No-alignment baseline matched on parameters, tokens and FLOPs; middle-layer hidden-state alignment (2502.14830-style) with identical data and lambda; bitext-in-mixture only (2603.29026 null); SWA+sinks hybrid arm (2608.28444); QED- and MARCH-equipped linear layers as mandatory recall baselines; dense transformer sibling (Qwen3-4B) in the frozen screen; romanized-input control for the script prediction (2608.25904); generation exact match, 4x OOD length, paired clustered SEs over >= 3 seeds, early context-extension probe (2608.10296).

**Kevin advantage.** Strong: parallel corpora with span alignment at General Translation make "only the language changes" state probes buildable today; two registered hybrid families (GDN qwen3.5-4b, KDA kimi-linear-48b-a3b-base); the from-scratch hybrid harness and 8xH100 for the 60M grid.

**collision_risk.** low (C-state-semantics.md searches: state write x translation/equivariance/parallel on arXiv/HF; every sweep cell found the "only the language changes" state-probe region empty).

**Monitorability and safety.** CoT untouched. A meaning-level state may make monitors trained in one language transfer better (testable later against the 13-language fragility set, 2605.27901) but may also remove surface cues monitors use — report both directions. Data rights: only licensed or open parallel corpora (OPUS, FLORES, GT corpora cleared for research); never customer content.

**Negative-result value.** If hybrids show no extra cross-lingual gap, the first instrument result on G2 is that fixed-size states store meaning — closes the question cheaply; if the state-level loss does not beat hidden-state alignment, parallel supervision of writes is redundant, extending 2603.29026's family of results to recurrent state; TP-MQAR remains the G2/G20 instrument.

**targets_gaps.** G2, G20.

---

## 8. read-free-record-blocked-memory  (E1 + E2 + E3 + H2)

**Claim.** If the write inputs of a delta-rule fast-weight memory come from a memory-free, record-blocked writer (no
path from the state back into the keys, values or gates), the state becomes an associative composition of per-record
affine maps: exact deletion and reset at O(log N), exact leave-one-out attribution at O(N), attestable hash-chained
receipts, and provable per-record / per-channel influence bounds (untrusted channels: additive, no-erase, norm-capped
writes) — properties native KDA/GDN state provably lacks (2607.27539). The empirical program prices the constraint: on a
frozen base (document-blocked encoding + TTT-NTP ridge write) and in a from-scratch hybrid whose only cross-record
channel is one such memory band, LM loss and cross-record recall are within a small margin of a GDN 3:1 hybrid at
iso-FLOP; the same pilot audits E2-TTT/FwPKM beyond-window recall under SR-TTT causality tests.

**claim_scope.** architecture-causal.

**Mechanism.** Delta rule S_t = S_{t-1} A_t + b_t, A_t = alpha_t (I - beta_t k_t k_t^T), b_t = beta_t v_t k_t^T; affine maps
compose associatively, (A, B) o (A', b') = (A A', B A' + b'), so with record-independent (k, v, alpha, beta) each record D
has factors (A_D, B_D) and S_N = S_0 A_{1:N} + B_{1:N}. Exact deletion of record j: S^{(-j)} = S_{j-1} A_{j+1:N} + B_{j+1:N}
from a segment tree of composed factors (O(log N) products of d_k x d_k and d_v x d_k; ~0.1 GFLOP for N = 1000, d = 128)
plus dropping D_j's blocked KV; reset S <- S_0; attribution by one suffix sweep giving every S^{(-j)}, I_j(q) = ||(S_N -
S^{(-j)}) q||; attestation r_j = H(r_{j-1} || H(A_j) || H(B_j) || meta_j) with a deletion certificate verified by a CPU fp64
oracle. Commutative alternative: ridge statistics (K^T K + lambda I, V^T K) summed over records, W = V K^T (K K^T + lambda
I)^{-1}, deletion by subtraction and re-solve in O(d_k^3). Substrate 1 (frozen retrofit, cheap-decisive): registry
qwen3-0.6b-base prefills each record under a document-blocked mask with APE-style shared-prefix/temperature/scale
alignment so hidden states are numerically independent of other records; a TTT-NTP-style write head maps them to unit
keys and next-position value targets; reads y_t = S phi(q_t) added to the MLP path. Substrate 2 (from scratch,
moonshot): writer stack (blocks 1..L_w) = record-blocked SWA + optional within-record GDN reset at record boundaries, no
path from the band; write head at L_w with H heads (k = norm(W_k h), v = W_v h, alpha = sigmoid(w_a . h)^{1/tau}, beta =
sigmoid(w_b . h)); reader stack (L_w+1..L) = record-blocked SWA + FFN + R >= 2 memory-read sublayers y_t = sum_h W_o^h
S^h_{<=t} phi(q_t^h) (read-after-write causal; verified by the two-forward-pass audit); training on packed documents chunked
into 512–1024-token segments with segment masks so the band is the only long-range channel. Typed writes (poisoning arm):
channel type c(D) in {system, user, tool, retrieved, other-agent}; trusted types use full gated delta factors; untrusted
types set A_t = I (no erase) and B_D = sum_t beta_t v_t k_t^T with per-record clip ||B_D||_F <= C_c and per-channel budget
sum_{D in c} ||B_D||_F <= Gamma_c (enforced by rescaling beta); since every later composition is non-expansive (||A||_2 <= 1),
for any read with ||q|| <= 1: ||y(S_N) - y(S_N^{(-c)})|| <= Gamma_c, and untrusted records cannot erase trusted content by
construction; detector score(D) = mean_{q in P} I_D(q) / median_{D'} I_{D'} over a benign probe set; flagged records are
quarantined and exactly deleted. Optional certificate arm (nonlinear fast weights): for TTT-MLP rules W_t = Phi_t(W_{t-1})
with sigma-modification leakage and NLMS step, per-step contraction factor q_t = ||(1 - sigma_t) I - eta_t H_t||_2 bounds
||W_t - W'_t|| <= prod q_r ||Delta W_s|| (open-loop; later keys fixed), giving an eps-deletion horizon n_eps = ln(||Delta
W_s||/eps)/sigma_min checked by paired replay — an incremental-ISS analogue of the linear band's exact bound.

**What is new.** 2607.27539 shows native KDA is non-addressable, retrofits an SVM memory whose decremental deletion falls
back to O(N) refit ~60% of the time, and lists segmented record-wise ingestion and streaming certificates as future work;
here Proposition 1's escape condition is enforced architecturally for the delta-rule family itself (O(log N) exclusion,
all-records attribution, receipts). TreeWY uses the same gated-delta affine algebra to reconstruct accepted speculative
branches, not to exclude committed records under a read-free precondition. Memorizing Transformers' kNN store is exactly
deletable but O(N) bytes with keys that see earlier segments (the iso-bytes control); MoNe is a frozen-base sidecar written
by order-dependent gradient updates with no deletion; Infini-attention writes and reads its memory in every block from the
same stream (non-addressable); Block-Attention encodes passages independently for KV reuse with no learned cross-record
state; APE independently encodes contexts for KV reuse and never mentions deletion. Utility Under Attack shows content
screens reject 0/360 plain-false poisons and provenance ranking is indistinguishable from no defense for text memory —
here the defense moves into the write path with a proof, and false facts are pre-registered as undetectable by
influence. Zubic & Scaramuzza give ISS bounds for trained selective SSMs; here the test-time inner loop is certified per
realised step. No direct prior art found through 2026-09-01 under the coverage in E-causal-fast-weights.md and H §4 for
exact sublinear deletion of delta-rule test-time state, a from-scratch hybrid with a memory-free writer designed for
deletability, typed write budgets with an influence proof, or certified per-write forgetting for fast weights.

**Closest priors.**
- Subtract, Transport, or Replay? — https://arxiv.org/abs/2607.27539 — 2026-07-30 (v2 2026-08-13) — native KDA non-addressable; SVM retrofit with ~60% fallback to O(N) refit; segmented ingestion and streaming certificates listed as future work.
- TreeWY — https://arxiv.org/abs/2608.20961 — 2026-08-21 — tree-structured WY form of the gated delta rule for speculative verification; same algebra, different use.
- Memorizing Transformers (ICLR 2022) — https://arxiv.org/abs/2203.08913 — 2022-03-16 — kNN memory, exactly deletable by removal but O(N) bytes; iso-bytes control.
- MoNe — https://arxiv.org/abs/2608.17616 — 2026-08-18 — frozen-base sidecar via order-dependent gradient updates; no deletion.
- Infini-attention — https://arxiv.org/abs/2404.07143 — 2024-04-10 — compressive memory read and written from the same stream in every block.
- APE (ICLR 2025) — https://arxiv.org/abs/2502.05431 — 2025-02-08 — independent context encoding for KV reuse; never mentions deletion.
- Certified Data Removal (ICML 2020) — https://arxiv.org/abs/1911.03030 — 2019-11-08 — (eps, delta)-certified removal for trained linear classifiers; here exact removal from test-time state.
- Utility Under Attack — https://arxiv.org/abs/2608.21230 — 2026-08-21 — content screening and provenance ranking fail against text-memory poisoning.
- Test-Time Training Undermines Safety Guardrails — https://arxiv.org/abs/2605.22984 — 2026-05-21 — LoRA-TTT jailbreak threat model; comparator arm.
- CaMeL — https://arxiv.org/abs/2503.18813 — 2025-03-24 — system-layer control/data separation; lossy exclusion comparator.
- Regularity and Stability of Selective SSMs (TMLR 2026) — https://arxiv.org/abs/2505.11602 — 2025-05-16 — ISS bounds for trained slow-weight SSMs; here the test-time inner loop.
- DeltaLog — https://arxiv.org/abs/2608.15533 — 2026-08-16 — bounded update log for throughput only.

**Falsifiable predictions.**
- P1 (algebra): on a CPU fp64 oracle with synthetic MQAR factor lists, exclusive composition equals replay-without-record to <= 1e-12 relative Frobenius for N <= 10,000 and <= 1e-5 in fp32; a control whose write factors read the state deviates >= 5% (2607.27539 measured 12–49%); the typed influence bound holds numerically incl. adversarially constructed erase records.
- P2 (frozen behavior): Qwen3-0.6B-Base with a blocked ridge memory over 200 TOFU-style records at 8–32K: after deleting record j, generated exact-match and paraphrase recall equal the never-stored model within 1 pt, locality changes <= 0.5 pt, next-token KL <= 1e-6 nats (fp64 memory arithmetic); matched-compute gradient-ascent unlearning of the same fast weights leaves >= 15% residual recall or >= 2 pt locality damage; document-blocked encoding with APE alignment loses <= 5 pts on RULER NIAH/QA at 8–32K vs sequential encoding (> 10 pts kills the frozen-base route).
- P3 (from-scratch price): at 60M/1.0B tokens (3 seeds) and 135M/1.5B tokens, the LM-loss gap between the read-free band model and the iso-FLOP GDN 3:1 hybrid is <= 0.02 nats; cross-segment S-NIAH-1 at 4x training length within 5 pts of the GDN hybrid and >= 60 pts above SWA+sinks; two-hop cross-segment chains within 8 pts with R = 2 and >= 20 pts worse with R = 1; the writer-reads-band ablation beats the read-free model by <= 3 pts MQAR and <= 0.01 nats (a gap >= 10 pts means deletability is expensive).
- P4 (poisoning): influence-detector AUROC >= 0.90 for trigger and erase/DoS poisons vs benign salient records and <= 0.60 for plain false facts; additive-capped untrusted mode with C_c = 0.1 x median benign ||B_D||_F cuts trigger ASR from >= 80% to <= 10%, trusted recall within 1 pt, <= 10 pts recall cost on benign untrusted records; exact deletion after a flag restores KL <= 1e-6 nats; cross-lingual X-ASR is either >= 50% of same-language ASR (memory stores meaning) or <= 10% (surface) — both bands pre-registered.
- P5 (audit half): E2-TTT's 93.6% S-NIAH-1 at 16K survives startup-causality and prefix-invariance self-tests at >= 90%; FwPKM's 4K -> 128K claim retains >= 60% under generation exact match with needles outside every non-parametric path.

**Kill conditions.** fp32 exclusive composition deviates > 1e-3 relative from replay at N = 1,000 (non-associativity too large for an fp32 ledger); document-blocking costs > 10 pts RULER on the frozen base and the ridge memory recovers none of it AND the from-scratch LM gap > 0.05 nats or cross-segment recall gap > 15 pts at both scales after per-arm HP search (deletable memory must be replay-cost); the exact kNN memory arm dominates the band at equal bytes (deletable memory should be an exact store, not compressive); the two-forward-pass audit finds a causality leak the design cannot remove; undefended trigger ASR < 10% (fast weights do not carry context-borne triggers: scoping negative consistent with LongVU-TTT) or the cap needed for ASR <= 10% costs > 30 pts benign recall; the 2607.27539 author publishes segmented ingestion with streaming certificates first (residual delta becomes a methods note).

**Cheapest decisive pilot.** Phase 0 (CPU, ~1 day): NumPy fp64 oracle for composition, exclusion, receipts and the influence bound; startup-causality self-tests (perturb position j, assert bit-identical state at positions < j); retrieval-impossible control corpus for the SR-TTT metric off-by-one; positive-control MQAR; 2-layer toy causality tests. Phase 1 (~12 GPU-h on 8xH100): (a) audit arm on zeyun-zhong/e2-ttt-{mlp,swiglu}-{340M,1.3B}-15B and SakanaAI/fwpkm-l12-* (verified on HF 2026-09-01): SR-TTT self-tests, two-forward-pass audit, needle-outside-window strata, generation exact match with paired McNemar, 2607.27539 static/transport receipts on their native states (2 GPU-h); (b) constructive arm on registry qwen3-0.6b-base with document-blocked encoding + TTT-NTP ridge write (yancyou/TTT-NTP, Apache-2.0): Beyond Perplexity D-level deletion battery (recall, paraphrase, delay, locality, conflict) vs sequential encoding, replay oracle, static-subtract receipt, gradient-ascent unlearning (4 GPU-h); (c) fast-weight poisoning benchmark on the same memory: 200 benign records, 20 poisons per type (T/F/E/X with FLORES-200 translations), defenses {none, LLM-judge screen, provenance down-weighting, typed budgets at C in {0.5, 0.1, 0.02} x median, influence flag + exact deletion, gradient-ascent unlearning, CaMeL-style exclusion}, ASR / benign recall / AUROC / post-deletion KL with validity-aware judging (4 GPU-h); (d) optional FLORES-200 cross-lingual deletion probe (delete the English record, test the German paraphrase). Conditional stage (new contract, ~16 GPU-h): 60M from-scratch arms x 3 seeds x 1.0B tokens — GDN 3:1 hybrid (fla 0.5.2), SWA+sinks, SWA + exact kNN memory at block L_w (iso-bytes), read-free delta band R = 2 and R = 1, read-free ridge band, writer-reads-band ablation — plus 135M x 1.5B tokens for the hybrid and the band (one seed) and a 48-config HP search at 20M; certificate arm on the E2-TTT checkpoints (HVP power-iteration q_t telemetry, ~2 GPU-h) and 125M certified-vs-unconstrained TTT-MLP hybrids if the arm is funded. Moonshot beyond: 340M/1.3B on 15B tokens, then a local retrofit of the band into qwen3.5-4b evaluated on LongMemEval/LoCoMo with right-to-be-forgotten deletion requests and receipts; optional Tinker LoRA-TTT attack comparator on Qwen3.5-4B (~20M tokens).

**pilot_gpu_hours.** 12.

**Controls.** Sequential (non-blocked) encoding on the same frozen base (prices the constraint); full replay oracle and never-stored model; static-subtract and frozen-transport receipts (2607.27539 classes); matched-compute gradient-ascent unlearning; GDN 3:1 hybrid at iso-params and iso-FLOP; SWA+sinks (2608.28444); SWA + exact kNN memory at the band position (iso-bytes); writer-reads-band (Infini-style) ablation; R = 1 vs R = 2 reader ablation; QED and MARCH as interference/recall baselines; Tail-Replay and DASC as state-summary comparators for any compact-state claim; startlux 340M/1.3B GDN hybrids as released references; no-defense arm; LLM-judge content screening and provenance ranking (2608.21230); MemGauge-style stage-wise exposure reporting (2608.30177); LoRA-TTT jailbreak arm (2605.22984) with validity-aware judging; CaMeL-style exclusion; unconstrained TTT-MLP (E2-TTT recipe), SANE tanh, LaCET EWC anchor, In-Place clipping tau, Falcon-1 NLMS without leakage as certificate-arm comparators; two-forward-pass prefix-invariance audit (2608.22876); SR-TTT startup self-tests; Beyond Perplexity S/B/D ladder (2607.00368); paired McNemar with disjoint seed pools; length-dependent curves; paired clustered SEs.

**Kevin advantage.** The harness's deterministic replay, digest-pinned images and hash-chained audit record are exactly the attestation machinery; 8xH100 with fla >= 0.5.2 kernels and the SIGUSR1-resumable Slurm harness for the from-scratch grid; parallel translation data makes the cross-lingual deletion/poison transfer arm cheap (FLORES-200 suffices for the pilot; GT data adds domain terminology). No unique data asset otherwise.

**collision_risk.** medium (E and H §4 searches: arXiv/HF on deletion/unlearning/certified x recurrent state/fast weights/TTT; delta rule x associative/segment tree; memory poisoning x fast weights; control theorists are visibly moving onto SSMs in 2026; 2607.27539's author has the obvious next step).

**Monitorability and safety.** Increases auditability: every read attributable to records, every deletion attestable, a logged per-step certificate in the nonlinear arm; no CoT effect. Scope must be stated as in 2607.27539: deletion covers test-time state (memory plus blocked KV), not pretrained weights or prior outputs. Typed budgets encode a policy in the architecture and may under-use legitimate tool facts (utility cost is a first-class metric); forced forgetting beyond a certified horizon is by design. Data: TOFU (MIT), RULER (synthetic), FLORES-200 (CC-BY-SA), FineWeb-Edu; synthetic poison texts with no real PII; a validity-aware judge ships with the benchmark; no production customer data.

**Negative-result value.** A quantified price of deletability (nats and recall points at 60M–135M) exists nowhere; if blocking is too costly on a frozen base, deletable memory must be designed in at training time; if the exact kNN store wins at equal bytes, deletable memory should not be compressive; if the constraint costs > 15 pts, right-to-be-forgotten for agent memory remains a replay-cost problem; if fp32 composition is unstable, it quantifies the precision a state ledger needs (DAMP/DASC-relevant); if fast weights carry no triggers, the TTT poisoning threat is scoped to LoRA-style TTT; if influence cannot separate triggers from salient benign facts, typed budgets are the only lever; the audit arm settles whether the strongest 2026 beyond-window TTT recall claims survive causality checks (G6); the cross-lingual arm answers G2's meaning-or-surface question for one memory class.

**targets_gaps.** G7, G8, G6, G12, G2, G20.

---

## 9. commit-gated-observation-state  (G1 + G3)

**Claim.** In GDN/KDA hybrids, forking the recurrent state at each tool-observation boundary and committing the
observation's aggregate state effect through a receipt-gated, logged commit gives by construction bitwise containment of
un-receipted observations, replay-free exact retraction of an observation's direct state contribution (the receipt class
native KDA fails in 2607.27539), and permutation invariance over concurrently returned tool results, at <= 0.5 pt
tool-world accuracy and <= +0.02 nats BPB cost at matched parameters; a predictive variant in which the actor forecasts
the observation's state effect at call time and commits only the residual yields a causally clean surprise receipt for
unexpected or poisoned tool outputs and permits bounded decoding on the forecast during tool latency.

**claim_scope.** architecture-causal.

**Mechanism.** Tokens carry provenance types tau_t in {sys, usr, rsn, act, obs, rcpt} assigned by the trace format (roles,
tool-call/result delimiters, a receipt token from the tool layer), never by content. Each gated-delta layer keeps a
persistent state P and, per open observation segment j, a scratch Q_j; transition A_t = alpha_t (I - beta_t k_t k_t^T), u_t
= beta_t k_t v_t^T. Non-observation token: P <- A_t P + u_t, read P^T q_t. obs-start(j): Q_j <- P (fork). Observation
token in j: Q_j <- A_t Q_j + u_t, read Q_j^T q_t, P unchanged. Receipt r_j (exit code, schema-validity bit, length, hash
prefix): Delta_j = Q_j - P; g_j = valid_j sigmoid(W_g h_{r_j} + b_g) in [0,1]^{d_v}; C_j = Delta_j diag(g_j); P <- P + C_j;
ledger of the K most recent commits; discard Q_j; obs-typed KV in the softmax layers truncated to a fixed budget B_obs
once the next act token is emitted. Concurrent results {j_1..j_m}: all Q_{j_i} fork from the same P, processed without
seeing siblings (shared start position id, sibling-to-sibling attention masked); P <- P + sum_i C_{j_i} in canonical
call-id order, so the next-action distribution is invariant to arrival order up to summation order. Ledger propagation
C_j <- A_t C_j for t > r_j (linearity in the state; O(d_k d_v) per entry per token). Retraction at T: P_T^{(-j)} = P_T -
C_j^{(T)}, exactly the state from g_j = 0 with later (k, v, alpha, beta) fixed; abort (valid_j = 0) leaves P bitwise
unchanged. Training: next-token loss on non-obs tokens + lambda_r sum_j ||C_j||_F^2 / ||Delta_j||_F^2. Predictive arm
(conditional): at the act token a_j issuing call j, forecast Dhat_j = F_j G_j^T (F_j = reshape(W_F h_{a_j}), G_j =
reshape(W_G h_{a_j}), rank 8), pre-commit P <- P + Dhat_j; on receipt, Q_j is forked from the pre-forecast P, eps_j =
Delta_j - Dhat_j, C_j = valid_j eps_j diag(g_j); ledger stores (Dhat_j, C_j) so both are retractable; surprise receipt s_j =
||eps_j||_F / (||Delta_j||_F + ||Dhat_j||_F + c); training adds lambda_f ||stopgrad(Delta_j) - Dhat_j||_F^2 / (||stopgrad(Delta_j)||_F^2
+ c) (stop-gradient blocks the "write nothing" collapse; ||Delta_j|| monitored, collapse is a kill); async mode (off by
default) decodes on P + Dhat_j between a_j and r_j and rolls back through the ledger if s_j exceeds a threshold. Why the
surprise-gated-memory rejection does not hold for the predictive arm: the forecast is action-conditioned and emitted
before any observation token exists (causality auditable by construction), computed on the aggregate state effect at a
typed boundary rather than per token (no burn-in; SR-TTT's position bias is a pre-registered kill), and used for commit
sparsity, monitoring and containment — no exact-recall claim. Scope: the guarantee covers the direct state contribution;
indirect effects through tokens already generated after reading the observation are measured against clean replay.

**What is new.** Versus Auditable Deletion (2607.27539): changes the recurrence so the observation's direct contribution
is one logged, forward-propagated object, making the subtract receipt satisfiable by construction and abort bitwise exact,
instead of auditing native KDA or retrofitting an external memory. Versus RW-TTT: types state within a request by
provenance and defines fork/commit/abort/set-commit inside the operator, where RW-TTT only tags request-owned state for
batched serving. Versus CommitKV: acts on the recurrent state of hybrids where token-addressable eviction is impossible,
is trained in, and yields exact retraction and order invariance rather than training-free KV eviction. Versus Titans /
MIRAGE / DreamGuard for the predictive arm: a boundary-level, action-conditioned forecast made before the observation
exists, whose residual is committed, logged and used as a monitor/poison signal in text tool loops, rather than token-level
gradient surprise gating retention, GUI-latent alignment without using the residual, or a separate runtime world model
gating actions. No direct prior art found through 2026-09-01 under the coverage in G-agent-native-architecture.md for
provenance-typed fork/commit of recurrent state or a forecast-residual commit at observation boundaries.

**Closest priors.**
- Subtract, Transport, or Replay? — https://arxiv.org/abs/2607.27539 — 2026-07-30 (v2 2026-08-13) — native KDA fails the subtract receipt (12–49% drift); replay is the only verified path.
- RW-TTT — https://arxiv.org/abs/2605.28053 — 2026-05-27 — request-owned TTT state tagging for batched serving; no reset/rollback/deletion semantics.
- CommitKV — https://arxiv.org/abs/2608.07855 — 2026-08-08 — training-free KV eviction around tool-call commits in transformers.
- Tail-Replay — https://arxiv.org/abs/2608.30310 — 2026-08-31 — suffix-replay prefix caching; mandatory deletion-fidelity control.
- Titans — https://arxiv.org/abs/2501.00663 — 2024-12-31 — token-level gradient-surprise writes; rejected axis, control arm.
- MIRAGE — https://arxiv.org/abs/2606.04627 — 2026-06-03 — GUI world-model latents aligned with future screenshots; residual unused.
- DreamGuard — https://arxiv.org/abs/2608.05695 — 2026-08-06 — separate runtime world model gating actions.
- SR-TTT Does Not Learn Retrieval — https://arxiv.org/abs/2603.06642 — 2026-02-26 (v2 2026-07-22) — retraction of surprise-gated recall; its self-tests are adopted as kills.

**Falsifiable predictions.**
- P1 (frozen, no training): permuting the arrival order of m = 3 concurrent tool results changes the next action at >= 10% of decision points for qwen3.5-4b and kimi-linear-48b-a3b-base on APIFlow-style worlds and BFCL parallel-call cases, and retracting one consumed observation shifts the recurrent contribution by >= 10% (2607.27539's 12–49% range); below 3% on both, the motivation collapses.
- P2 (CGOS-125M): abort leaves P bitwise identical to never-read in 100% of 10,000 audited observations; retraction vs replay-with-g_j = 0 has relative Frobenius error <= 1e-3 in bf16 and next-token KL <= 1e-4 nats, while the plain GDN control drifts >= 10% and Tail-Replay at 5–10% budget shows KL >= 1e-2; TV distance between next-action distributions under sibling permutation is 0 (bitwise) for set-commit and >= 0.05 mean for the plain hybrid trained on the same shuffled traces.
- P3 (cost): held-out tool-world accuracy within 0.5 pt (paired, 3 seeds, clustered SEs) of the plain 3:1 hybrid and natural-text BPB within +0.02 nats at matched parameters; at a 20K delivered-token budget on 20-subtask chains, CGOS with scratch discard (B_obs = 64) >= plain hybrid + the 2608.26218 mechanical-shortening policy at equal delivered tokens; adoption of content from an aborted poisoned observation is 0.0% vs >= 20% for the plain hybrid.
- P4 (predictive arm, conditional): s_j separates unexpected from routine observations with AUROC >= 0.90 in the oracle tool world; a weak monitor on (s_j, type) reaches >= 0.85 vs <= 0.70 for a text-only monitor of equal size; >= 60% of routine observations commit ||C_j|| <= 0.1 ||Delta_j|| with accuracy within 0.5 pt of CGOS; detection AUROC in the first vs last 10% of a trajectory differs by <= 0.05; the forecast is bitwise invariant to observation content in 100% of 10,000 audited calls; decoding on the pre-commit changes the next action in <= 2% of routine cases.

**Kill conditions.** P1 below thresholds on both frozen hybrids; P3 loss >= 1 pt or BPB >= +0.05 nats at matched params/FLOPs; the two-forward-pass prefix-invariance audit finds an unfixable leak in the fork/commit kernel; the commit gate saturates at g ~ 1 everywhere and the ledger costs more than checkpoint replay at equal fidelity (degenerates to GDN + DeltaLog); a data-only control (plain hybrid trained on all sibling permutations) reaches order invariance within 0.5 pt (set-commit unnecessary); predictive arm: AUROC < 0.7 or a position-bias gap > 0.1, collapse of ||Delta_j|| the stop-gradient does not prevent, an adaptive poison matching the forecast reaching >= 50% adoption with s_j below threshold, or accuracy loss >= 1 pt vs CGOS.

**Cheapest decisive pilot.** Phase 0 (CPU, ~1 day): NumPy fp64 reference of the GDN recurrence with fork/commit/ledger; doctors: retraction identity P_T - C_j^(T) == replay with g_j = 0 to 1e-12; set-commit permutation invariance bitwise; two-forward-pass prefix-invariance audit (2608.22876) on the fused chunkwise kernel with injected faults (must localize 100%); leakage check that pre-receipt logits are invariant to observation content; ledger cost vs checkpoint replay; forecast/residual algebra and a Gaussian-world identifiability screen for the predictive arm. Phase 1 (~2 GPU-h, frozen): order-sensitivity and retraction-drift probes on qwen3.5-4b, kimi-linear-48b-a3b-base (bf16, 8xH100) and delta-net-1.3b-8k, 500 decision points each. Phase 2 (~13 GPU-h): 125M 3:1 GDN/softmax hybrid (fla >= 0.5.2), 1.5B tokens per run (screen; promotion needs the 3-size >= 10x ladder): 60% synthetic long-horizon tool-world traces generated forward with oracle solvability (APIFlow-Bench recipe) with 20% poisoned/invalid-receipt observations and shuffled parallel-call batches, 40% FineWeb-Edu; arms x 3 seeds: plain hybrid, CGOS, CGOS lambda_r = 0, CGOS without set-commit, plain + SWA-with-sinks; evaluation-time harness arms on the plain hybrid (mechanical shortening 2608.26218, observation masking 2508.21433, CommitKV-style eviction); Tail-Replay 5%/10% and checkpoint replay as deletion controls; ~1 GPU-h per run. Conditional (~13 GPU-h, new contract): CGOS vs CGOS + predictive commit (3 seeds), a Titans-style token-gradient surprise gate on a matched-size TTT layer as the rejected-axis control, adaptive-attack evaluation, monitor training, position-bias stratification. Tinker stage (evaluation only, ~5M sampled tokens): Kimi-K2.6 and Qwen3.5-35B-A3B order-sensitivity probes via the sampling API. Seeds [42,43,44].

**pilot_gpu_hours.** 16.

**Controls.** Iso-parameter plain 3:1 GDN hybrid with per-arm HP search at the smallest rung (2608.11859); SWA + sinks (2608.28444); Tail-Replay 5%/10% (2608.30310) and checkpoint replay (2607.27539's verified path) as deletion controls; QED-GDN2 (2608.13668) and MARCH (2608.12435) on the same recall-interference probes; data-only control (plain hybrid trained with all sibling permutations); harness-layer controls at evaluation (mechanical shortening 2608.26218, observation masking 2508.21433/2606.00408, CommitKV-style boundary-keyed eviction); CGOS without the forecast head; plain hybrid with perplexity-based surprise over observation tokens (cheapest monitor); Titans-style gradient-surprise gate on a matched-size TTT layer; text-only weak monitor (smollm2-135m classifier) and a DreamGuard-style external recurrent predictor at equal parameters; SR-TTT startup causality self-tests and depth stratification; two-forward-pass prefix-invariance audit on every arm; paired scoring with token ledger, all-k-of-k reliability (APIFlow-Bench) and false-completion rate (FrontierChallenge).

**Kevin advantage.** The harness's deterministic replay, hash-chained receipts and SIGUSR1 checkpoint/resume are exactly the machinery for retraction/containment audits and the paired replay oracle (harness/causal_memory_trials.py already implements paired audits and assignment journals) and label "unexpected" observations without an LLM judge; 8xH100 covers the frozen probes on Kimi-Linear-48B-A3B-Base and the 125M grid in a day; Kimi-Linear-48B-A3B-Base and Qwen3.5-4B/9B are the only registered KDA/GDN hybrids where P1 can be measured today. Parallel translation data is secondary: translated task instructions with fixed observations give an optional language-controlled probe of the OmnilingualGAIA2 tool-orchestration gap.

**collision_risk.** medium (G note searches: arXiv/HF on typed state / fork-commit / tool observation x recurrent state / KDA; RW-TTT, CommitKV, Tail-Replay found as neighbours; agentic-serving groups could add typed boundaries).

**Monitorability and safety.** Auditability increases: per-observation commit ledger, receipt-gated writes, exact containment as a right-to-be-forgotten primitive for tool content at the recurrent layer, plus a non-CoT surprise receipt; CoT tokens untouched. Risks: scratch discard removes raw observation tokens from later attention, so later claims about tool outputs are checkable only against the persisted tool log; type assignment is a new trust boundary (HarnessRisk 2608.17597 finds harness configuration the most vulnerable phase — a mistyped-injection threat arm is mandatory); a model decoding on its own forecast can act on hallucinated tool results, so async mode stays off by default and the "acts before receipt" rate is reported; the forecast head is an internal world model that could reduce grounding. Data rights: synthetic worlds, FineWeb-Edu (ODC-By), APIFlow transcripts (license to verify), no proprietary traces.

**Negative-result value.** If typed fork/commit costs capability or the gate saturates, observation-boundary discipline belongs in the harness (supporting the 2026 harness-layer consensus) — and the pilot still delivers the first quantified order-sensitivity and retraction-drift numbers for open KDA/GDN hybrids plus a verified retraction doctor reusable for G7; if boundary-level, action-conditioned surprise is uninformative or position-biased, the rejection of surprise-gated designs extends to the boundary level, LongVU-TTT's "aggregation, not memory" finding gets a controlled agentic confirmation, and the CID-style asynchronous AR variant is shown not to be free.

**targets_gaps.** G7, G20, G21, G6, G14.

---

## 10. provenance-typed-attention  (G2)

**Claim.** Typing tokens by provenance at the attention level (per-head learned type-pair logit bias, a typed value path
for observation tokens, per-head type gates) lets a 135M–0.6B tool-using model separate data-to-copy from
instructions-to-follow better than embedding-level typing (ISE, ASIDE) at matched parameters, halving tool-output
injection success in multi-turn loops at <= 0.5 pt utility cost, and exposes a provenance attention-mass channel a weak
monitor can read to detect unverbalized tool-return influence (FACE-Eval's failure mode).

**claim_scope.** architecture-causal.

**Mechanism.** Types tau in T = {sys, usr, rsn, act, obs, rcpt} from the trace format. Layer l, head h: logit_ij = q_i . k_j
/ sqrt(d) + b^{l,h}[tau_i, tau_j] + causal mask, b a learned 6x6 table (36 parameters per head). Typed value path: v_j =
(W_V + D_{tau_j}) x_j with D_tau a rank-8 delta, zero for {sys, usr, rsn, act} and non-zero for obs and rcpt (data
provenance gets its own value subspace). Per-head type gate: p_ij <- gamma^{l,h}[tau_i, tau_j] softmax_j(logit_ij),
renormalized, gamma in [0,1] with an L1 penalty so heads specialize by provenance pair. PTA-hard: gamma[act, obs] = 0 on a
designated half of the heads in the top third of layers, so action queries read observations only through the remaining
heads whose value path is the typed D_obs subspace — the structural falsifier for "instruction-following from data can
be removed by construction while copying survives". Monitor channel: M_i[tau] = (1/H) sum_h sum_{j: tau_j = tau} p^h_ij at
every act/answer position; weak monitor = logistic regression on (M_i[obs], M_i[usr], M_i[sys]) with no text access.
Retrofit: add b, D_obs, D_rcpt, gamma (~0.5M params on qwen3-0.6b-base) and fine-tune on typed traces.

**What is new.** ISE adds BERT-style segment embeddings by priority (input level); ASIDE rotates data-token embeddings
orthogonally with one binary split; GW-DPO enforces a multi-level hierarchy through preference optimization only. Here
typing acts in attention logits and value paths with a per-head gate, covers six provenance types incl. receipts and
reasoning in multi-turn tool loops, admits a structural ablation embedding typing cannot express, and adds a monitor
channel evaluated against unverbalized tool-return adoption with cross-lingual instruction control. No direct prior art
found through 2026-09-01 under the coverage in G-agent-native-architecture.md for attention-level provenance typing.

**Closest priors.**
- Instructional Segment Embedding (ICLR 2025) — https://arxiv.org/abs/2410.09102 — 2024-10-09 — segment embeddings by priority; +15.75%/+18.68% robust accuracy on StruQ / Instruction Hierarchy.
- ASIDE (ICLR 2026) — https://arxiv.org/abs/2503.10566 — 2025-03-13 — orthogonal rotation of data-token embeddings; binary split.
- Gravity-Weighted DPO — https://arxiv.org/abs/2606.10860 — 2026-06-09 — five-level hierarchy via preference optimization; strongest training-only control.
- FACE-Eval — https://arxiv.org/abs/2608.29464 — 2026-08-29 — all 15 models verbalize tool-return cues less and adopt them unverbalized more.

**Falsifiable predictions.**
- P1: injection ASR on AgentDojo-style multi-turn tool tasks (0.6B retrofit) and synthetic tool worlds with injected instructions inside observations (135M): PTA <= 0.5x the ASR of ISE and ASIDE at matched utility (e.g., 40% -> <= 20%); PTA-hard <= 5% ASR with <= 2 pt utility drop.
- P2: unverbalized tool-return adoption (FACE-Eval protocol adapted to 0.6B): the weak monitor on M_i reaches AUROC >= 0.80 while the same monitor on an untyped model's attention mass over the tool-return span reaches <= 0.65.
- P3: tool-call and argument accuracy within 0.5 pt of the untyped control and BPB within +0.01 nats.
- P4 (Kevin arm): with task instructions translated into six languages and observations fixed, PTA's cross-language injection-ASR spread (max - min) is <= 0.5x the untyped model's spread.

**Kill conditions.** ISE or ASIDE at matched parameters within noise of PTA on P1 and P2 (a replication, not an architecture result); PTA-hard costs >= 2 pt utility; monitor AUROC < 0.7; the mistyping threat arm (harness assigns wrong types) breaks PTA worse than the baselines.

**Cheapest decisive pilot.** Phase 0 (CPU): typed attention in NumPy; doctors: type-pair bias equals an additive ALiBi-style bias numerically; PTA-hard gradient-flow check (zero gradient from obs keys to act queries in gated heads); type ids come only from delimiters (leakage check); monitor-channel algebra. Phase 1 (~8.5 GPU-h): 135M dense transformer (SmolLM2-135M shape; smollm2-135m as loader/tokenizer reference), 1B tokens (60% synthetic tool worlds with injected instructions, 40% FineWeb-Edu); arms: untyped + delimiters, ISE, ASIDE, PTA, PTA-hard; 3 seeds; ~0.56 GPU-h per run -> 15 runs. Phase 2 (~2 GPU-h): qwen3-0.6b-base + PTA parameters fine-tuned on 50M tokens of typed agent traces (APIFlow-Bench transcripts, SWE-smith/mini-swe-agent, Tmax), same five arms x 3 seeds; evaluate AgentDojo (97 tasks, 629 cases), FACE-Eval-style probes, the mistyping threat arm, and P4 with translated instructions. Tinker stage (control at scale, 30M tokens): Qwen3.5-4B LoRA with typed delimiters + GW-DPO-style preference data as the "training alone" control. Seeds [42,43,44].

**pilot_gpu_hours.** 11.

**Controls.** Iso-parameter untyped model with delimiter tokens (same data, seeds, HP search per 2608.11859); ISE segment embeddings and ASIDE rotation at matched parameters; GW-DPO-style preference training at 0.6B and StruQ-style structured queries (data-only controls); MemDecay-style typed KV eviction at inference; mistyping threat arm (HarnessRisk); 2026 evaluation mandates: paired passes with token ledger, all-k-of-k reliability (APIFlow-Bench), false-completion rate (FrontierChallenge).

**Kevin advantage.** qwen3-0.6b-base is registered for retrofit; the harness has agent-loop, oracle and paired-regression contracts; General Translation's parallel data yields the language-controlled injection probe (P4); 8xH100 covers everything in a day. Honest: the core mechanism needs none of Kevin's unique assets.

**collision_risk.** high (G note searches: instruction hierarchy x attention / typed attention / provenance; ISE/ASIDE lines are active and an attention-level extension is an obvious next step).

**Monitorability and safety.** Adds a non-CoT monitor channel (provenance attention mass) and leaves CoT untouched. Risks: type ids are a new trust boundary (mistyping attack); a typed value path could make the model ignore legitimate instructions embedded in data (README instructions in a repository) — under-following on a "legitimate instruction in tool output" set is measured alongside AgentDojo utility. Data rights: AgentDojo (MIT), SWE-smith (MIT), FineWeb-Edu (ODC-By), APIFlow transcripts (license to verify).

**Negative-result value.** If embedding-level typing suffices, the field learns attention-level typing is unnecessary; the pilot still delivers the first tool-loop, multi-turn, cross-lingual evaluation of ISE/ASIDE with a monitor-channel test and a mistyping threat measurement.

**targets_gaps.** G14, G21.

---

## 11. frozen-reader-anchored-media  (D1 + D3)

**Claim.** An abstract discrete reasoning medium trained under a frozen, weaker, pre-committed reader with a
rate-matched codebook is decodable by a held-out weak monitor at >= 90% of explicit-CoT monitorability while compressing
reasoning >= 3x, survives reasoning-rewrite attacks that collapse both co-trained-decoder latents and explicit CoT, and
carries provably and measurably less steganographic slack than natural-language CoT; the same frozen reader anchors the
register file of a recurrent-depth LM whose remaining inter-iteration state passes through a metered C-bit channel,
turning the latent-vs-explicit dichotomy into a one-dimensional knob with a designed monitorability-tax curve
accuracy(C), catch-rate(C) on multi-turn tool tasks — with the prediction that most of the recurrence gain on
compositional tool calling survives at C <= 32 bits per slot per iteration while opaque serial depth stays at one core
pass.

**claim_scope.** attachment-capability.

**Mechanism.** Substrate A (explicit trace): policy pi_theta (smollm2-135m at the screen; qwen3-0.6b-base / qwen3.5-4b at
confirmation) emits between observation o_t and action a_t a trace z_t = (z_{t,1..T}) over a reserved codebook C with |C|
= K, then the action in explicit text (tool name and JSON arguments never abstracted). Reader R_phi (from-scratch 20M LM or
frozen smollm2-135m) is fixed BEFORE policy training: its embedding table gets K rows initialized from mean-pooled
embeddings of K seed gloss phrases g_k (gloss dictionary G), a linear head H is fitted once on gloss-rendered explicit CoT
-> monitor variables m_t, then phi, E_C and H are frozen. m_t = (next tool id, argument-source slots, hint-use flag,
constraint-violation flag) read from the environment's execution log (hint presence and correctness randomized so
hint-use is causally identified), never from the model. Warm-up: SFT with straight-through Gumbel-softmax on z toward
gloss-rendered teacher traces (~50M tokens). RL (GRPO): r = r_task + lambda_R log p_{R_phi}(m_t | z_t) - lambda_len T. Because
phi never moves, the policy cannot negotiate a private code with its reader. Rate matching: choose (K, T) so C_z = T
log2(K) = H(m) + eps with eps in {4, 64} bits (K = 64, T = 8 gives 48 bits vs H(m) ~ 40–44 bits in ToyTools). Slack bound: for
side information s independent of the task, I(z; s) <= T log2(K) - H(m) + H(m|z) = eps + H(m|z); H(m|z) is measured;
tightness tested by a collusion probe (a 32-bit secret injected in the input; a separately trained colluder recovers s
from z; recovered bits above eps + H(m|z) + 2 falsify the bound). Legibility scored only by a held-out monitor M (fresh 135M
classifier trained post hoc on disjoint task templates) plus the dictionary rendering G(z); attacks: a re-encoder trained
to keep r_task while minimizing M's AUROC (2608.00583-style) and monitor-awareness pressure (2605.15257-style); a
Baker-style check compares monitor-flagged vs environment-logged violations. Reader-strength ladder: dictionary (0
params) -> frozen 20M -> frozen 135M -> co-trained 135M (SIM-CoT-style) -> same-model (SELR/ALCA-style). Substrate B
(recurrent depth): prelude P, core f_psi iterated R times (fixed R, no halting), coda Q; the only inter-iteration and
inter-turn state lives in T scratch positions appended after each observation; slot j at iteration r holds s_{r,j} =
(g_{r,j}, u_{r,j}) with g in V_reg^S register tokens from a fixed 2k-word reader vocabulary (S readout heads,
straight-through Gumbel-softmax) and u in {1..2^C} an opaque code from vector quantization against a 2^C codebook
(straight-through, commitment loss beta); h_{r+1} = f_psi(E(x), E_reg(g_r), E_u(u_r)) and the continuous h_r is discarded
(DiscoLoop passes a continuous channel; here it is replaced by the metered code). Registers anchored to R_phi as above: L
= L_task + lambda_R sum_r -log p_{R_phi}(m_t | g_{r,.}) + beta L_commit. Opaque serial BANDWIDTH per iteration <= T C bits;
opaque serial DEPTH (2603.09786) is one core pass; C is the knob (C = 0: fully legible loop; continuous pass-through:
Ouro/Huginn); register slack eps_reg = T S log2|V_reg| - H(m) + H(m|g) and total hidden budget T C + eps_reg measured with
the collusion probe; a per-position statefulness doctor enforces that ordinary positions carry no state.

**What is new.** Legibility-by-training exists only for natural-language CoT with a co-trained or same-model reader
(Prover-Verifier Games; Markovian Transformers rely on the KL-to-pretrained prior against steganography); latent decoders
(SIM-CoT, SELR, LatentGuard, ALCA) are co-trained or self-decoding and scored for accuracy/audit utility; steganography
papers measure NL hidden channels and defend with paraphrasers; recurrent-depth LMs now cover compositional tool calling
(2608.18171) but no source reads or bounds what the loop carries; DiscoLoop keeps an unbounded continuous channel and
reports no monitor or tool use; GDM's opaque-serial-depth work defines and bounds depth without proposing a constraint,
and DiffusionGemma shows an interpretable token bottleneck can be free for diffusion only. The delta: (i) a reader frozen
and weaker before policy training, (ii) an abstract code with no NL prior and hence an explicit rate bound, (iii) measured
collusion-probe slack, (iv) tool-use tasks with a held-out monitor under obfuscation, and (v) an architecture that bounds
opaque serial bandwidth per iteration by construction with a metered C-bit code. Occupancy: ALCA (ACL 2026) partly
occupies "interpretable-by-construction latents as a monitor channel"; the surviving clauses (tool use, obfuscation
pressure, external frozen weaker reader) are the ones tested. No direct prior art found through 2026-09-01 under the
coverage in D-monitorable-media.md (hostsearch arXiv/HF/OpenReview queries and 25 abstract reads).

**Closest priors.**
- Prover-Verifier Games improve legibility — https://arxiv.org/abs/2407.13692 — 2024-07-18 — small verifiers trained jointly with provers; NL only.
- Markovian Transformers — https://arxiv.org/abs/2404.18988 — 2024-04-29 (v8 2026-03-10) — bounded NL CoT read by the same model; KL prior against steganography.
- LatentGuard — https://arxiv.org/abs/2608.03838 — 2026-08-04 — auxiliary decoder emits audit artifacts for a latent guard model; decoder regime unspecified.
- ALCA (ACL 2026) — https://aclanthology.org/2026.acl-long.1570/ — 2026-07 — latent safety deliberation with restricted self-decoding.
- Mitigating Legibility Tax with Decoupled PVG — https://arxiv.org/abs/2602.23248 — 2026-02-26 — translator turns a fixed solver's solution into a checkable form.
- DiscoLoop — https://arxiv.org/abs/2607.00341 — 2026-07-01 — discrete + unbounded continuous channel in a loop; no monitor or tool use.
- How Transparent is DiffusionGemma? — https://arxiv.org/abs/2606.20560 — 2026-06-18 — interpretable token bottleneck cuts opaque serial depth 28.6x -> 1.1x at no loss (diffusion).
- Quantifying the Necessity of CoT through Opaque Serial Depth — https://arxiv.org/abs/2603.09786 — 2026-03-10 — defines and bounds opaque serial depth; no architectural constraint.
- Looped Language Models Improve Compositional Tool Calling — https://arxiv.org/abs/2608.18171 — 2026-08-17 — recurrent depth helps tool use; loop state unprobed.

**Falsifiable predictions.**
- P1 (ToyTools oracle world, 135M policy, frozen 20M reader, K = 64, T = 8, eps ~ 4 bits): held-out weak-monitor AUROC for (next tool, hint-use) >= 0.85 and >= 90% of the explicit-CoT monitor's AUROC at >= 3x fewer reasoning tokens; the matched-(K, T) co-trained-decoder arm scores <= 0.70 with the same held-out monitor (gap >= 0.15).
- P2 (slack): the collusion probe recovers <= eps + H(m|z) + 2 bits of a 32-bit secret on the anchored code, >= 16 bits on the unconstrained reserved-vocabulary code, and >= 12 bits on explicit NL CoT at matched task accuracy.
- P3 (obfuscation): under the re-encoder attack with task accuracy within 1 pp, the anchored code's held-out monitor AUROC drops <= 0.10 vs >= 0.30 for the co-trained-decoder arm and >= 0.40 for explicit-CoT paraphrase (2608.00583: ~95% -> < 11% catch rate under rewrites); task accuracy within 2 pp of explicit CoT at 135M; random/zero/shuffled abstract-prefix ablation costs >= 10 pp (load-bearing, unlike the LauraGG Abstract-CoT negative).
- P4 (looped substrate, 30–60M, multi-turn ToyTools with 3-hop compositions, matched parameters and FLOPs): the continuous looped model beats the iso-FLOP non-looped model by >= 10 pp on 3-hop tasks; metered arms retain >= 80% of that gain at C = 32 bits/slot/iteration and >= 50% at C = 0; frozen-reader monitor AUROC on registers >= 0.85 at every C; under an obfuscation fine-tune the activation probe on the continuous model falls to <= 0.60 while the register monitor falls <= 0.10; collusion-probe recovery <= T C + eps_reg + 2 bits at each C; accuracy(C) concave with its knee between 8 and 32 bits.

**Kill conditions.** Held-out monitor AUROC < 0.70 for the anchored code while explicit CoT >= 0.85 at matched accuracy (frozen anchoring does not transfer to a reader that was not the training reader); legibility tax > 5 pp vs explicit CoT at 135M and again at qwen3-0.6b-base; collusion slack not reduced because H(m|z) stays large; Baker-style divergence (monitor-flagged violations fall while logged violations do not); looped substrate: metered arms at C <= 32 lose >= 80% of the loop gain at 40M and at the 0.6B retrofit, register monitor AUROC < 0.70, slack bound violated (frozen anchoring fails inside a loop), or no arm trains stably after two remediation rounds (2606.24898-style norm blow-up).

**Cheapest decisive pilot.** Phase 0 (CPU, ~2 days): ToyTools generator (8 typed tools, 2–4 dependent calls, argument values copied from numbered context fields, randomized hint presence x correctness, injected tool failures, full execution log; multi-turn variant with 3-hop compositions); compute H(m) and the (K, T, eps) table; doctors: reader sees only z, monitor split disjoint by template, labels from the log, secret independent of task; dictionary-decoder null on random codes (AUROC 0.50 +/- 0.02); straight-through gradient check; channel-capacity doctor (VQ with 2^C codes -> exact mutual information by counting), leakage doctor (recurrence receives only E_reg(g) and E_u(u); per-position statefulness test); the open opaque-serial-depth tool run on each architecture graph. Phase 1 (~14 GPU-h): fit the frozen 20M reader on gloss sequences (1 GPU-h); arms x 2 seeds on smollm2-135m: explicit CoT, length-penalized CoT at matched tokens, unconstrained reserved-vocab code (Abstract-CoT-style), anchored code with eps = 4 and eps = 64, SIM-CoT-style co-trained decoder (6 arms x 2 seeds x ~1 GPU-h; SFT warm-up ~50M tokens + GRPO ~30k episodes each); held-out monitors, collusion probes, re-encoder attacks (~1 GPU-h). Conditional looped stage (~15 GPU-h, new contract): 40M models (prelude 2, core 4 x R = 4, coda 2), T = 8, S = 4, |V_reg| = 2k, same frozen reader; arms x 2 seeds: non-looped iso-param, non-looped iso-FLOP, looped continuous, DiscoLoop-style, metered C in {0, 32, 128}; monitors, probes, obfuscation fine-tunes. Confirmation (separate contract): qwen3-0.6b-base then qwen3.5-4b on BFCL-multi-turn / tau2-style tasks; Tinker Qwen3.5-4B LoRA RL (~100M tokens) for the escalation policy with legibility evaluated locally; a 2608.11233-style recurrence adapter retrofit of the looped substrate into qwen3-0.6b-base (~60 GPU-h); Ouro-1.4B/2.6B and GRT comparisons (Tinker cannot host custom recurrence).

**pilot_gpu_hours.** 14.

**Controls.** Explicit CoT on the same base scored by the same held-out monitor (iso-parameter); length-penalized CoT at matched reasoning tokens (2607.09786); Abstract-CoT-style unconstrained reserved-vocabulary code at identical (K, T) (2604.22709); SIM-CoT-style co-trained decoder (2509.20317); SELR / ALCA-style same-model or restricted self-decoding (2608.13570; ACL 2026); ALAR-style latent-by-default / escalate-to-think at matched tokens (2606.02871); Markovian NL bottleneck CoT at matched length (2404.18988); activation-probe monitor as the internals-access ceiling (2608.04928); reader-strength ladder; random / zero / shuffled abstract-prefix ablations; non-looped iso-parameter (deeper) and iso-FLOP transformers; continuous looped model (Huginn/Ouro-style); Gated Recurrent Transformer (2608.15062); DiscoLoop-style mixed channel (2607.00341); Thinking-States-style language-supervised fixed-size state (2602.08332); per-arm opaque-serial-depth measurement (2603.09786); iso-depth-law compute accounting phi = 0.46 (2604.21106); two-forward-pass causality audit on the recurrence and per-position statefulness doctor; paired McNemar over episodes; 2 seeds at the screen, >= 3 at confirmation; contamination disclosure.

**Kevin advantage.** Modest: none unique at the 135M screen (any lab can run it). The harness's agent-loop, oracle, trace and paired-regression contracts plus SIGUSR1-resumable RL make the many-arm design cheap; 8xH100 and Tinker Qwen3.5-4B carry the confirmation of the trace substrate; the parallel-data asset enters through interlingua-trace-codes.

**collision_risk.** medium (D-monitorable-media.md searches: frozen/weak reader x latent/abstract CoT; steganography x codebook; looped/recurrent depth x monitorability/opaque/information bottleneck on arXiv/HF/OpenReview; ALCA/LatentGuard/SIM-CoT and DiscoLoop/DiffusionGemma found as neighbours).

**Monitorability and safety.** Monitorability-positive by design. The reader term is "aligned" in the 2603.30036 sense (rewards accurate exposure of environment-logged variables, never penalizes content), but a Baker-style flagged-vs-logged check is pre-registered because any reward on the CoT can be gamed; the frozen reader defines the variable set m, so everything outside m is protected only by eps — eps, H(m|z), T C and eps_reg are reported as first-class quantities; the dictionary gloss keeps humans in the loop; registers are a persistent human-renderable working memory across turns and the opaque budget is explicit; a small C may push computation into within-iteration depth (bounded by one core pass, measured) or into ordinary positions' attention (statefulness doctor). Data: synthetic ToyTools; public BFCL/tau2/NESTful-style tasks; Apache-2.0 bases; no customer data.

**Negative-result value.** A clean negative shows that a frozen weaker reader cannot anchor a learned low-rate code without a > 5 pp legibility tax — "monitorable by construction" abstract media are not free and monitoring must rely on activations (2608.04928) or natural language; if the loop's tool-use gain requires high-bandwidth continuous state (C >= 128 bits), that is a quantitative statement of why latent recurrence resists monitoring (bits per iteration), sharpening 2606.12689's "hidden computation, not hidden explanation"; the slack instrument (rate ledger + collusion probe), the C-knob, and the ToyTools oracle worlds (single- and multi-turn with register readouts) transfer to any medium incl. explicit CoT, Coconut and Ouro; a mixed result quantifies where hidden bits go (H(m|z)), a number no NL study can produce.

**targets_gaps.** G14, G16, G20.

---

## 12. interlingua-trace-codes  (D2)

**Claim.** Supervising the frozen-reader-anchored abstract trace with parallel problem pairs so that semantically
equivalent inputs in any language induce the same discrete trace (a decodable reasoning interlingua) lets a monitor
trained on English traces transfer to other languages with <= 5-point catch-rate loss where explicit-CoT monitors lose
>= 20 points and translate-then-monitor stalls — turning parallel translation data into a monitorability asset rather
than an accuracy aid.

**claim_scope.** portability-protocol.

**Mechanism.** Same medium and frozen weaker reader R_phi as frozen-reader-anchored-media. Parallel pairs P = {(x^A, x^B)}
share one ToyTools instance, hence one execution log m and one answer up to language (JSON tool calls are language-neutral;
final answers follow the input language, so the output stays equivariant while the trace is made invariant). Objective:
L = L_task + lambda_R L_reader + lambda_inv L_inv, L_inv = E_{(A,B) in P} sum_{i=1..T} JS(q_theta(z_i | x^A, z_{<i}), q_theta(z_i | x^B,
z_{<i})) with teacher forcing on a shared sampled prefix (symmetric JS — no pivot language), optionally plus a sequence-level
REINFORCE term L_seq = 1 - EM(z^A, z^B) on sampled traces (the only form implementable on Tinker's logprob-only losses).
Alternative invariance arm: a language-ID adversary on z through gradient reversal. Data: ToyTools rendered in en/de/zh by
General Translation MT with glossary checks plus one synthetic-language transform (deterministic vocabulary and word-order
permutation) as a controlled third language; at confirmation, FLORES-plus / GT-translated MGSM and BFCL-style prompts with
ReasonXL's 5-language parallel traces as the explicit-CoT control corpus. Monitor-transfer protocol: train M_en on (z, m)
from English episodes only; test on every other language; report Delta_L = AUROC_en - AUROC_L and catch rates for hint-use
and constraint violations; the gloss decoder renders any trace to an English gloss for humans. Baselines that must be
beaten: explicit CoT in language L read by M_en; translate-then-monitor (production MT of the L-language CoT into English,
then M_en); SOLAR-style English-pivot soft-token alignment; a CODI-style continuous arm with no parallel data (emergent
invariance, 2603.08177); a random-pair placebo for L_inv (does parallel data add anything — the 2603.29026 worry);
per-language monitors as the ceiling. Invariance diagnosed by trace exact-match agreement across pairs and
silhouette-by-language of trace embeddings.

**What is new.** Cross-lingual work on reasoning traces either measures fragility (2605.27901: 95.9% unfaithfulness across
13 languages, no medium proposed), diagnoses an English-centered latent pathway (2601.02996), aligns continuous soft tokens
to an English pivot for accuracy (SOLAR), shifts the reasoning language with a parallel explicit-trace corpus (ReasonXL),
prunes explicit cross-lingual CoT in a language-invariant logic space at inference (UL-XCoT), or reports emergent language
invariance of CODI continuous latents without parallel data, decoder or monitor (2603.08177). The delta is symmetric
parallel-pair supervision of a DISCRETE trace a frozen weaker reader can decode, a placebo separating parallel supervision
from emergent invariance, and cross-language monitor transfer on tool-use tasks as the endpoint against a production
translate-then-monitor baseline. No direct prior art found through 2026-09-01 under the coverage in D-monitorable-media.md
(interlingua / language-invariant x CoT / latent reasoning; cross-lingual x monitor x CoT; parallel data x reasoning trace).

**Closest priors.**
- SOLAR — https://arxiv.org/abs/2606.26466 — 2026-06-25 — non-English soft tokens aligned to an English pivot for accuracy (+17.7).
- Is continuous CoT better suited for multi-lingual reasoning? — https://arxiv.org/abs/2603.08177 — 2026-03-09 — CODI latents emergently language-invariant; no decoder or monitor; mandatory control.
- The Fragility of CoT Monitoring Across Typologically Diverse Languages — https://arxiv.org/abs/2605.27901 — 2026-05-27 — 95.9% unfaithfulness across 13 languages; no medium proposed.
- ReasonXL — https://arxiv.org/abs/2604.12378 — 2026-04-14 — 5-language parallel corpus of 2M explicit reasoning traces; explicit-CoT control corpus.
- Large Reasoning Models Are (Not Yet) Multilingual Latent Reasoners (ACL 2026 Findings) — https://arxiv.org/abs/2601.02996 — 2026-01-06 — diagnostic: English-centered latent pathway.

**Falsifiable predictions.**
- P1 (screen, 60M bilingual from-scratch or smollm2-135m continued on en/de + synthetic language, ToyTools): trace exact-match agreement across translated pairs >= 70% with L_inv vs <= 25% without and <= 30% with the random-pair placebo, at task accuracy within 1 pp; M_en transfer gap Delta <= 3 AUROC points vs >= 15 for explicit CoT read by M_en.
- P2 (confirmation, qwen3-0.6b-base -> qwen3.5-4b, 8 languages incl. 3 non-Latin scripts): M_en's hint-use / constraint-violation catch rate on non-English traces >= 85% of its English catch rate; translate-then-monitor on explicit CoT <= 70%.
- P3: the CODI-style no-parallel-data continuous arm shows partial emergent invariance (Delta 5–10 points) but is beaten on Delta by >= 5 points and is not decodable by the frozen reader (AUROC <= 0.65).
- P4: silhouette-by-language of trace embeddings falls from >= 0.40 to <= 0.10 under L_inv.

**Kill conditions.** Trace agreement cannot exceed 40% without > 3 pp task loss (a discrete reasoning interlingua is unlearnable at this scale); translate-then-monitor matches invariant-code monitor transfer at equal cost (the cheap alternative suffices); random-pair placebo ~= real pairs on agreement and Delta (parallel signal unnecessary; extends 2603.29026 to reasoning traces); the no-parallel-data continuous arm already reaches Delta <= 3 (emergent invariance suffices; 2603.08177 wins); high trace agreement (>= 70%) with Delta >= 10 (invariant but uninformative — trace collapse).

**Cheapest decisive pilot.** Phase 0 (CPU): bilingual ToyTools renderer (en/de/zh via GT MT with glossary checks + one synthetic-language transform); pair-semantics doctor (identical execution logs for both members); monitor-split doctor; metric doctor (a hand-built canonical code gives Delta = 0 and 100% agreement; random codes give AUROC 0.50). Phase 1 (~14 GPU-h): 60M from-scratch bilingual policy (or smollm2-135m + 200M tokens of de/zh continued pretraining, ~2 GPU-h) with the frozen 20M reader from frozen-reader-anchored-media; arms x 2 seeds: no L_inv, L_inv, placebo L_inv, language-ID adversary, SOLAR-style pivot alignment, CODI-style continuous, explicit CoT per language (7 x 2 x ~0.8 GPU-h ~ 11 GPU-h); monitors, transfer evaluation and translate-then-monitor via GT MT (~1 GPU-h). Confirmation (separate contract): qwen3-0.6b-base full FT (~40 GPU-h); Tinker Qwen3.5-4B / 9B LoRA RL with parallel prompts (~300M tokens) on the 13-language fragility set, L_inv as the sampled-trace EM reward (Tinker losses are logprob-only).

**pilot_gpu_hours.** 14.

**Controls.** Explicit CoT in each language read by M_en (iso-parameter); translate-then-monitor with production MT; SOLAR-style English-pivot alignment (2606.26466); CODI-style continuous CoT with no parallel data (2603.08177); random-pair placebo for L_inv; language-ID adversary (gradient reversal); cross-lingual self-consistency RL without parallel data (2606.01464); ReasonXL-trained target-language explicit CoT (2604.12378) read by M_en; per-language monitors (upper bound) and activation-probe monitors (2608.04928); iso-token, iso-parameter, paired McNemar over pairs; FLORES contamination probe and four-field disclosure.

**Kevin advantage.** Strong but not exclusive: General Translation supplies (a) production-grade MT for the translate-then-monitor baseline, (b) translated tool-use task suites with terminology control and identical environments — the scarce object (ReasonXL covers five European languages and math/general traces), and (c) low-resource and non-Latin-script coverage; 8xH100 for the 0.6B–4B confirmation; Tinker Qwen3.5-9B for the RL stage. Honest limit: for en/de/fr/it/es explicit-CoT controls, ReasonXL is public and equivalent.

**collision_risk.** medium (D searches listed above; SOLAR/CODI-multilingual/ReasonXL groups are active and could add a monitor endpoint).

**Monitorability and safety.** Positive: monitor portability across languages. Risks: invariance may erase language-specific cues a monitor needs (e.g., an injection written in the input language) — per-language injection detection is reported alongside Delta; an English gloss for humans risks English-centric review (the code is symmetric; gloss fidelity reported per language). Data rights: FLORES-plus CC-BY-SA-4.0; ReasonXL license to be checked; GT corpora cleared for research only, never customer content; no CC-BY-NC weights in publication runs.

**Negative-result value.** If traces cannot be made invariant without task loss, reasoning codes are surface-bound — supporting 2601.02996 and extending 2603.29026 to the trace level — and translate-then-monitor becomes the recommended practice with a measured cost curve; if emergent invariance suffices, parallel supervision is unnecessary (a check on 2603.08177); the bilingual oracle world and monitor-transfer instrument remain reusable for the G2/G13 translation-paired probes.

**targets_gaps.** G15, G14, G20.

---

## 13. tag-and-capture-delta-memory  (H3)

**Claim.** A two-store delta-rule state in which every write lands in a fast-decaying tag store and is transferred to a
long-retention store only by a later, sparse, scalar capture signal (synaptic tagging and capture; three-factor rules)
gives retroactive selection of what persists: higher long-range recall of items followed by a capture event, certified
bounded persistence of uncaptured content (a poison horizon), and an explicit monitorable consolidation channel — at
LM-loss parity with GDN at 125M.

**claim_scope.** architecture-causal.

**Mechanism.** Per head, S_tag, S_slow in R^{d_v x d_k}. Tag write (delta rule with fast decay rho = exp(-1/tau), tau in [128,
2048] learned per head within bounds): S_tag_t = rho S_tag_{t-1}(I - b_t k_t k_t^T) + b_t v_t k_t^T. Capture (third factor):
scalar c_t = sigmoid(w_c^T h_t + b_c) per (layer, head) from the current hidden state, with a budget sum_{t in window W} c_t <=
B enforced by an L1 penalty (or hard top-B per window). Transfer: S_slow_t = alpha_t S_slow_{t-1} + c_t S_tag_t; S_tag_t <- (1
- c_t) S_tag_t. Read: o_t = (S_slow_t + S_tag_t) q_t (optionally separate output gates). Properties: (i) certificate — a write
at time s never captured has residual at most rho^{t-s} b_s ||v_s|| ||k_s|| in S_tag and exactly 0 in S_slow; (ii)
retroactivity — content written in the last ~tau tokens is consolidated by an event AFTER it (behavioural tagging); (iii)
monitorability — c_t is a logged scalar per head per token. Chunkwise form: [S_slow; S_tag] follows a block-upper-triangular
linear recurrence with token-dependent coefficients; S_slow_t = sum_{s<=t} (prod_{r=s+1..t} alpha_r) c_s S_tag_s is a gated
cumulative sum of a GDN-type state — the same algebra as the momentum accumulator whose exact chunk-end form E2-TTT derives,
so WY-style chunk kernels exist; at 125M a PyTorch chunk-16 reference suffices. Why the surprise-gated-memory rejection does
not apply: the gate acts at CAPTURE time on a later global signal (three-factor rule), not at write time on prediction
error; the SR-TTT failure was an evaluation-causality failure the mandatory doctors pre-empt; Titans-style surprise gating
is a mandatory control arm, not the proposal.

**What is new.** Backpropamine (ICLR 2019) defines retroactive neuromodulation with eligibility traces inside clipped Hebbian
outer products on PTB at 4.8M–24.2M parameters; here the trace lives inside a normalised-key delta-rule associative state
(erase, not clipped Hebbian) in a 3:1 GDN hybrid at >= 125M with a chunk-parallel form, a capture budget, a certified
persistence bound, and evaluation on recall / poison / monitorability. Titans decides at write time by gradient surprise;
here capture is retroactive and uncaptured content is certified to decay. Phasor Agents apply three-factor plasticity with
sleep-staged consolidation in oscillator graphs (no LM). Mela blends two update frequencies with no gated transfer; Nested
Learning / HOPE has multi-frequency updates with no retroactive gate; Adaptive Memory Crystallization and Hindsight
Memory-PRM are harness-level; SleepGate is KV-level. No direct prior art found through 2026-09-01 under the coverage in H
§4/§5 for a retroactive capture gate inside a delta-rule LM operator.

**Closest priors.**
- Backpropamine (ICLR 2019) — https://arxiv.org/abs/2002.10585 — 2020-02-24 — retroactive neuromodulated Hebbian plasticity; PTB 104.26 -> 102.48 at 4.8M params.
- Titans — https://arxiv.org/abs/2501.00663 — 2024-12-31 — write-time surprise gating; control arm.
- Phasor Agents — https://arxiv.org/abs/2601.04362 — 2026-01-07 — three-factor plasticity with sleep-staged consolidation in oscillator graphs; no LM.
- Mela — https://arxiv.org/abs/2605.10537 — 2026-05-11 — two update frequencies blended, no gated transfer.
- Nested Learning / HOPE (NeurIPS 2025) — https://arxiv.org/abs/2512.24695 — 2025-12 — continuum memory with multi-frequency updates, no retroactive gate.
- Hindsight Memory-PRM — https://arxiv.org/abs/2608.29605 — 2026-08-30 — harness-level retroactive credit; conceptual comparator.

**Falsifiable predictions.**
- P1 (behavioural tagging signature): in an MQAR variant with capture events (a query about any key), items written within tau before a capture event are recalled at 8K delay with >= 30 points higher accuracy than matched items with no nearby capture; a two-rate GDN (fast + slow heads, no transfer) shows < 5 points difference.
- P2 (parity): LM loss within 0.01 nats of GDN at 125M / 5B tokens at iso-parameters (the second matrix costs state memory and ~1.5x recurrent compute, no parameters).
- P3 (recall/poison Pareto): at equal state bytes, S-NIAH-1 at 4x training length improves >= 5 points when the needle is followed within tau by a natural capture (a question), and paired-replay influence of an uncaptured injected instruction 4K tokens after injection is >= 3x lower than GDN.
- P4 (monitorability, Kevin's asset): logged c_t predicts which context items are later recalled with AUC >= 0.75 (random gate 0.5); on parallel documents the per-sentence capture mass aligns across translations with Spearman >= 0.6, or the failure localises to high-fertility scripts.

**Kill conditions.** c_t collapses to a constant (entropy < 0.1 bits or budget always saturated) under LM loss despite the penalty (degenerates into two-rate GDN); two-rate GDN matches P1/P3 (transfer has no value beyond multi-timescale decay); Titans-style write-time surprise gating matches P3 (retroactivity adds nothing); recall cost > 3 points at matched bytes on standard S-NIAH.

**Cheapest decisive pilot.** Phase 0 (CPU, fp64, ~3 h): linear two-store dynamics; verify the persistence bound; capacity analysis (captured items S_slow holds before interference) vs single-store GDN at equal d; behavioural-tagging synthetic with an oracle capture policy (upper bound) and a learned linear gate (identifiability). Phase 1 (<= 15 GPU-h): 20M MQAR-capture screens (minutes each) for identifiability, then 125M 3:1 hybrids (12 layers: 9 recurrent + 3 global), 5B FineWeb-Edu tokens plus a synthetic tool-result/question mixture; arms GDN, two-rate GDN, Titans-style surprise-gated GDN, tag-and-capture; 3 seeds; probes as above with generation exact match and paired McNemar.

**pilot_gpu_hours.** 15.

**Controls.** GDN single-rate (iso-parameter); GDN two-rate heads (iso-parameter); Titans/MIRAS surprise gate (write time); KDA lower-bounded decay; QED (2608.13668), MARCH (2608.12435), SWA+sinks (2608.28444); Hindsight Memory-PRM as conceptual harness comparator; doctors: SR-TTT self-tests, prefix-invariance audit (2608.22876), Beyond Perplexity D-level battery; an adversarial capture-trigger attack arm.

**Kevin advantage.** Parallel translation data gives the content-fixed cross-lingual capture probe (P4) and an optional translation-equivariance regulariser on c_t; 8xH100 covers the 125M grid; harness paired replay measures poison influence. Moderate.

**collision_risk.** medium (H §4: arXiv abs "synaptic tagging" -> neuroscience + two agent-harness papers; eligibility/neuromodulated/three-factor x LM/linear attention -> 0 relevant; retroactive/behavioural tagging x memory x LM -> 0; the Titans/HOPE line could add a retroactive gate at any time).

**Monitorability and safety.** Adds an explicit logged consolidation channel (what the model chose to keep, and when) and a certified poison horizon for uncaptured content. Risk: a learned capture gate can be attacked by capture-triggering tokens inside tool results (adversarial arm mandatory). Data rights: public corpora plus licensed parallel data.

**Negative-result value.** Two-rate GDN matching -> "retroactive selection adds nothing beyond multi-timescale decay", directly informative for the Titans/HOPE continuum-memory line; gate collapse -> the LM loss does not supervise consolidation timing, the operator-level analogue of the reward-SNR floor (2608.10441); the capture-probe instrument and certified tag decay survive as harness assets.

**targets_gaps.** G7, G2, G15.

---

## 14. lora-footprint-routing-probe  (I1)

**Claim.** Differencing a Tinker-exported shared-outer MoE LoRA against its step-0 export yields per-expert "footprints"
that are a calibrated, monotone readout of how often each expert of Kimi-K2.6 was routed the training tokens; with content
held fixed and only the language varied, the footprints measure cross-lingual routing consistency at 1T, and along an RL
run they measure routing drift without routing replay — all without hidden-state or router access.

**claim_scope.** architecture-causal.

**Mechanism.** Tinker's shared-outer layout (read from exported tensors, 2026-08-19 artifact): for MoE layer l, expert e,
dW1_{l,e} = B1_{l,e} A1_l and dW3_{l,e} = B3_{l,e} A3_l (shared A in R^{r x d}, per-expert B in R^{d_e x r}) and dW2_{l,e} = B2_l A2_{l,e};
the router mlp.gate is not adapted. Per-expert gradient dL/dB1_{l,e} = sum_t 1[e in TopK_l(x_t)] g_{l,e}(x_t) delta_{l,e,t} (A1_l
x_t)^T is identically zero for tokens not routed to e. Under AdamW (weight decay 0), a parameter with non-zero gradient in a
fraction p of steps with magnitude G and directional consistency c moves ~ lr c sqrt(p) per step, so total displacement ~
lr S c_{l,e} sqrt(p_{l,e}): monotone in routing frequency, with c absorbed by calibration. Footprint f_{l,e} = ||[B1_{l,e},
B3_{l,e}, A2_{l,e}^T](S) - [same](0)||_F using a step-0 export. Calibration: rank(f_{l,e}) ~ rank(n_{l,e}) (routed-token count)
fitted on the open twin Qwen3.5-35B-A3B-Base (on Tinker AND local with a re-implemented shared-outer LoRA so n_{l,e} is
observable). Language intervention: parallel corpus C rendered in languages l (content fixed), one rank-1 LoRA per l with
the same Tinker seed; per-layer rho_l(l, l') = Spearman over experts outside the standing-committee set K_l (top-m experts
of a neutral-corpus footprint; 2601.03425), contrasted with cross-content same-language rho_l(C, C'). RL drift: footprints
f(k) at checkpoints of a CISPO LoRA-RL run; D_l(k) = 1 - Spearman(f(k), f(k-1)), read alongside Tinker's e_min_violation /
e_frac_with_tokens telemetry.

**What is new.** Multilingual Routing in MoE (ICLR 2026) reads routers directly on open <= 30B MoEs; here the readout is at
1T from training-gradient footprints in exported adapters on a model whose routers and hidden states are unreachable, and
footprints measure what adaptation trains, not what inference routes (compared on the open twin). SARA adds a training-time
routing-alignment objective — the reason the "training objective" form of G19 is occupied — so the observational 1T
measurement is what remains. ESFT selects experts to fine-tune from routing statistics; here the inverse direction. No
source found that reads expert usage from adapter deltas (I §6 search log).

**Closest priors.**
- Multilingual Routing in Mixture-of-Experts (ICLR 2026) — https://arxiv.org/abs/2510.04694 — 2025-10-06 — direct router reads on open MoEs over parallel text; middle-layer alignment; steering +1–2%.
- SARA — https://arxiv.org/abs/2606.25821 — 2026-06-24 — training-time JS routing alignment across languages (Qwen3-30B-A3B, Phi-3.5-MoE).
- ESFT — https://arxiv.org/abs/2407.01906 — 2024-07-02 — expert selection from routing statistics; inverse direction here.
- R3 — https://arxiv.org/abs/2510.11370 — 2025-10-13 — routing mismatch destabilises MoE RL; no LoRA-RL data.
- The Illusion of Specialization (ACL 2026) — https://arxiv.org/abs/2601.03425 — 2026-01-06 — standing committee; motivates committee removal.
- Tinker cookbook hyperparam_utils.py (first-party) — https://github.com/thinking-machines-lab/tinker-cookbook/blob/main/tinker_cookbook/hyperparam_utils.py — fetched 2026-09-01 — shared-outer LoRA scheme docstring.

**Falsifiable predictions.**
- P1 (calibration, local twin): on Qwen3.5-35B-A3B-Base with shared-outer rank-1 LoRA (300 steps, batch 64 x 4K tokens), per-layer Spearman(f_{l,e}, n_{l,e}) >= 0.80 in >= 90% of MoE layers; the same job on Tinker gives hosted-vs-local footprint Spearman >= 0.90 per layer.
- P2 (language intervention, Kimi-K2.6, 6 languages x 2 seeds, rank 1, 0.5M tokens each): middle-third layers (21–40 of 61) rho(EN, l) >= 0.70 for de/fr/es/zh/ja after committee removal, first 8 and last 8 layers rho <= 0.40; cross-content same-language rho in middle layers <= 0.45; seed ceiling >= 0.90.
- P3: per-language middle-layer similarity to English predicts sampling-only per-language accuracy (Belebele-class, 12 languages) with Spearman >= 0.6.
- P4 (RL drift): 100-step rank-32 CISPO on a verifiable task without routing replay keeps D_l < 0.10 in >= 90% of layers and e_min_violation within 10% of its start; the alternative (D_l > 0.30 in >= 20% of layers) is the R3 instability observed for the first time at 1T through LoRA.

**Kill conditions.** Local calibration Spearman < 0.60 in most layers (AdamW normalisation erases usage information); hosted-vs-local Spearman < 0.70 (not usable as a two-tier instrument); |rho_language - rho_content| < 0.10 in middle layers with overlapping 2-seed intervals (no language-invariance finding at 1T; publish as a scale-dependent negative against 2510.04694).

**Cheapest decisive pilot.** Phase 0 (CPU): pull the public r = 8 Kimi-K2.6 adapter (4.69 GB), verify the shape algebra, compute per-expert factor norms and Gini per layer (uniform norms would mean init dominates and force step-0 differencing); NumPy AdamW simulation on sparse-gradient toys to fix the sqrt(p) calibration curve and its sensitivity to beta2 and consistency c. Phase 1 (local, ~8 GPU-h): Qwen3.5-35B-A3B-Base (pin the 40-hex revision) with a custom shared-outer LoRA module; 4 runs (EN/DE renderings of FLORES-200 dev+devtest plus an OPUS slice, 2 seeds) logging n_{l,e}; one per-expert (non-shared) LoRA run for contrast (tinker-rl G1). Phase 2 (hosted): the same 4 runs on Tinker Qwen3.5-35B-A3B-Base (~$10) for P1; Kimi-K2.6 rank-1: 6 languages x 2 seeds x 0.5M tokens (~6M train tokens, ~$30) + step-0 exports; 4 English tasks x 2 seeds for the content contrast; offline analysis on the node. Phase 3 (hosted, optional): 100-step rank-32 CISPO with exports every 25 steps (~$150–300). Total <= 20M Tinker train tokens, <= $600; registry: qwen3.6-35b-a3b registered, Qwen3.5-35B-A3B-Base to add with revision.

**pilot_gpu_hours.** 10.

**Controls.** Seed-noise ceiling; cross-content same-language contrast; standing-committee removal (2601.03425) from a neutral-corpus footprint; ground-truth routing on the open twin; hosted-vs-local same-seed equivalence; rank robustness {1, 4, 32}; shared-outer vs per-expert LoRA locally; Tinker expert-balance telemetry as co-signal; the 2510.04694 layer pattern as reference; 2 seeds with paired clustered SEs; token/dollar ledger.

**Kevin advantage.** Tinker is the only route that trains and exports weights on Kimi-K2.6; parallel translation data supplies the content-fixed language intervention (GT for development; FLORES-200 / OPUS for the published artifact); 8xH100 holds the 35B-A3B open twin for ground-truth calibration; the harness seals seeds and receipts.

**collision_risk.** medium (I §6: arXiv LoRA x MoE x routing x multilingual -> 1 unrelated; LoRA x MoE x shared x expert-specific -> 0; HF papers LoRA-MoE -> 20 mixture-of-LoRA papers, none reading usage from weights; the trick is simple and Tinker has many users).

**Monitorability and safety.** No CoT effect. Dual use: the probe extracts routing internals of a closed-serving model from a permitted export — disclose to Thinking Machines before publication; "exported adapters leak routing" is itself a provider-relevant finding. Data rights: FLORES-200 (CC-BY-SA 4.0) and OPUS for publication; GT production text only with client consent and never in the released artifact; Tinker ToS permits adapter export.

**Negative-result value.** If AdamW erases usage -> exported LoRAs do not leak routing (privacy-positive) and telemetry is the only routing channel on Tinker; if hosted != local -> documents Tinker/open-tinker non-equivalence (G22 two-tier); if 1T routing is language-specific in middle layers -> a scale-dependent reversal of 2510.04694.

**targets_gaps.** G22, G19, G2.

---

## 15. nope-hybrid-clock-tiebreak  (J1)

**Claim.** The post-training "endless generation" of NoPE hybrids is a positional tie-breaking failure among repeated
spans that appears once generation length exceeds the recurrent state's clock horizon; per-channel decay (KDA) supplies a
longer clock than per-head scalar decay (GDN), a testable reconciliation of Kimi/Solar (NoPE, fine) with Qwen3.8-Next
(GDN, NoPE dropped).

**claim_scope.** architecture-causal.

**Mechanism.** In a 3:1 hybrid whose global layers have no positional encoding, position reaches a global attention layer
only through (i) the causal-softmax denominator (resolution ~ 1/t; 2606.06160), (ii) the BOS/sink residual trajectory, and
(iii) the recurrent layers' states. For a delta-rule layer with per-step decay a_t (scalar per head in GDN; per channel in
KDA), S_t = sum_{i<=t} (prod_{j=i+1}^t a_j) beta_i v_i k_i^T; for a stationary stream with constant a, |S_t| ~ (1 - a^t)/(1 - a)
is a usable clock only for t < T_clock = 1/(1 - a) and saturates beyond; Fisher information about t under fixed read noise
scales as a^{2t} ln(a)^2 -> 0. When generation repeats an earlier span, a NoPE global layer sees identical keys at both
copies; the only tie-breaker is the difference of state-derived features between copies, O(a^Delta) for copy distance Delta;
past T_clock the copies are indistinguishable, the induction read averages over copies, the span is re-emitted and the
trajectory falls into a periodic attractor. RoPE breaks the tie by construction. Post-training exposes rather than creates
the failure (long self-generated answers contain many exact repeats). KDA's per-channel decay lets a few channels sit near
a = 1 (long clock) while the rest forget; GDN's per-head scalar must serve all channels, so its longest clock is shorter at
equal parameters. T_clock(unit) = 1/(1 - E_x[a(x)]) is computable from weights exactly as DASC's retention horizon
(2608.30386). Intervention: a "sticky" decay subset (KDA: 8 channels/head initialised at log a = -1e-4; GDN: one head per
layer) or partial RoPE on 1/8 of global-layer dims.

**What is new.** Qwen3.8-Next reports NoPE ~ RoPE in pretraining but "substantially higher rate of endless generation after
post-training" with no mechanism (25B-A3B, single arm); Rethinking Efficient Attention in Hybrids shows NoPE globals help
long-context retrieval with SWA locals (measures retrieval, not termination; no delta-rule states); Where does Absolute
Position come from traces position to the causal denominator and BOS trajectory in dense RoPE models. Delta: a stated
clock-horizon tie-breaking mechanism, a pre-registered repetition signature, a weight-derived predictor, a
decay-parameterization factor, and a behaviour (termination) rather than attention patterns; the head-temperature
dispersion mechanism (2404.12224) is the rival hypothesis with its own arm. No direct prior art found through 2026-09-01
under the coverage in J §"Candidate 1" (arXiv NoPE x hybrid/linear attention x termination/post-training -> 1 unrelated;
HF papers -> none on termination).

**Closest priors.**
- On the Design of Qwen3.8-Next — https://arxiv.org/abs/2608.30320 — 2026-08-31 — NoPE endless generation after post-training, no mechanism.
- Rethinking the Role of Efficient Attention in Hybrid Architectures — https://arxiv.org/abs/2606.15378 — 2026-06-13 — NoPE globals improve long-context retrieval; SWA locals.
- Where does Absolute Position come from in decoder-only Transformers? — https://arxiv.org/abs/2606.06160 — 2026-06-04 — causal-denominator and BOS-trajectory position channels in dense models.
- Length Generalization of Causal Transformers without Position Encoding — https://arxiv.org/abs/2404.12224 — 2024-04-18 — NoPE failure as attention dispersion, fixed by head temperature; rival mechanism.
- Kimi K3 — https://arxiv.org/abs/2607.24653 — 2026-07 — NoPE MLA + KDA at 1M context; Solar Open 2 — https://arxiv.org/abs/2607.20062 — 2026-07 — 3:1 NoPE hybrid.
- Canon layers — https://arxiv.org/abs/2512.17351 — 2025-12 (NeurIPS 2025) — short conv lifts NoPE; the GDN/KDA short conv is ablated.

**Falsifiable predictions.**
- P1 (125M 3:1 hybrids, identical 2.5B-token pretraining and identical 20M-token EOS-terminated SFT, greedy decoding on 2,000 prompts, 4,096-token cap): NoPE-GDN non-termination rate >= 3x RoPE-GDN (expected >= 15% vs <= 5%), and >= 80% of NoPE non-terminating outputs are periodic with period <= 64 tokens.
- P2: NoPE-KDA's non-termination rate <= 0.5x NoPE-GDN's at matched params/tokens, and the weight-derived maximum clock horizon is >= 4x longer in the trained KDA than GDN checkpoints.
- P3: a "most-recent-copy induction" probe (k = 3..8 repeated n-grams with distinct continuations) shows a NoPE-vs-RoPE accuracy gap >= 20 points at 4x the training context, and per-run probe error predicts per-run non-termination with Spearman >= 0.7; pretrain-only NoPE checkpoints already show >= 2x the RoPE loop rate.
- P4 (intervention): sticky decay channels or partial RoPE on 1/8 of global dims closes >= 70% of the NoPE–RoPE non-termination gap while moving pretraining loss by <= 0.005 nats.

**Kill conditions.** No NoPE-vs-RoPE termination gap at 125M–350M after SFT (scale- or RL-specific; G10 narrowed to "not reproducible below 1B"); gap exists but non-terminating outputs are aperiodic and the copy probe does not predict it (rho < 0.3); KDA ~ GDN in gap and horizon (decay-parameterization reconciliation dead); head-temperature tuning (2404.12224) removes the gap while sticky channels do not (dispersion mechanism dominates).

**Cheapest decisive pilot.** Phase 0 (CPU): NumPy clock-horizon calculator (Fisher information of t from a decayed delta-rule state under Gaussian read noise for decay distributions read from kimi-linear-48b-a3b-base KDA vs qwen3.5-4b GDN decay projections); synthetic tie-break simulation; periodicity-detector doctor validated on synthetic loops; off-by-one/causality doctor for the probe. Phase 0b (frozen, ~1 GPU-h): copy probe + 4K greedy loop rate on kimi-linear-48b-a3b-base (NoPE MLA + KDA) vs qwen3.5-4b (partial RoPE 0.25 + GDN) — directional only. Phase 1 (<= 13 GPU-h): {RoPE, NoPE} x {GDN, KDA} x 2 seeds = 8 runs x ~1.4 GPU-h (125M, 2.5B tokens, Qwen3.5-0.8B layout 18 linear + 6 global, fla / FlashKDA kernel path only — the pure-PyTorch chunked-KDA fallback gives NaN gradients, PR #48455); identical SFT ~0.5 GPU-h; probes and decoding ~1.5 GPU-h; early extension probe included. Phase 2 (only if P1/P2 hold): intervention arms (6 runs, ~8 GPU-h), partial-RoPE-0.25 arm, 350M, 5 seeds; Tinker post-training of Qwen3.5-4B/9B as the production-scale loop-rate control.

**pilot_gpu_hours.** 14.

**Controls.** RoPE arm (Qwen3.8 production choice) and partial-RoPE-0.25 arm (Qwen3.5); SWA(128)+sinks hybrid twin with NoPE/RoPE globals (2606.15378, 2608.28444); dense-transformer NoPE vs RoPE twin (smollm2-135m layout) with the head-temperature fix of 2404.12224 as the rival-mechanism arm; short-conv on/off (Canon-layer control); early context-extension probe (2608.10296); two-forward-pass prefix-invariance audit (2608.22876); per-arm HP search (2608.11859); generation-based evaluation with permutation controls; paired clustered SEs; iso-parameter and iso-token across arms; startlux 340M/1.3B GDN hybrids (2608.12149) as released pre-norm references.

**Kevin advantage.** Modest: the 8-run grid is one day on the node; kimi-linear-48b-a3b-base is the only locally runnable NoPE KDA hybrid for the frozen screen; parallel translation data gives a length-controlled multilingual termination probe (same content in N languages: if loop rate tracks token count rather than semantic length, that supports the token clock); Tinker's Qwen3.5-4B/9B supply a production-scale post-training control. Any lab with 8 GPUs can run the core experiment.

**collision_risk.** medium (J searches above; Qwen has the motive and data to publish the mechanism; the Ruscio group could extend 2606.06160 to hybrids).

**Monitorability and safety.** Positional-encoding choice does not touch CoT or action monitorability; runaway generation is itself a controllability/cost failure, so the result improves it. Data: open pretraining/SFT corpora; parallel data for probes only.

**Negative-result value.** If no gap appears at <= 350M, G10 is narrowed to "scale- or RL-specific" and small labs learn they cannot study it locally; if the gap is not tie-break-driven, the periodicity/probe dataset is the first mechanistic record of NoPE termination; the clock-horizon calculator is reusable for DASC-style compression and E2-TTT/fast-weight audits; the 125M K3-stack substrate (KDA-LB + NoPE globals) is the G12 open reference as a by-product.

**targets_gaps.** G10, G12, G20, G2.

---

## 16. global-anchor-skip-read-depth-operators  (J2, with the MTP-on/off arm from J3)

**Claim.** In 3:1 linear/global hybrids, depth-axis operators (AttnRes, mHC, Gated Residual) earn most of their gain by
letting later linear layers read the sparse global-attention layers' outputs directly (an "anchor skip-read"); a
restricted operator that routes only global-layer outputs recovers most of the gain at a fraction of the depth memory, and
the gain is larger in hybrids than in dense transformers at iso-parameters; the same multi-seed substrate delivers the
first independent iso-compute depth-operator comparison at 125M–350M (G9) and settles whether an MTP objective helps or
taxes <= 1B hybrids (G11).

**claim_scope.** architecture-causal.

**Mechanism.** Pre-norm h_{l+1} = h_l + f_l(norm(h_l)): a global-attention output written at layer 4k is diluted by three
linear-layer writes before the next global layer and ~L/4 writes overall, so late linear layers see full-rank token
interactions only through an attenuated sum. AttnRes reads h_in^l = sum_{i<l} alpha_{i->l} u_i, alpha = softmax_i(w_l .
norm(u_i)) over sublayer outputs (2603.15031). Hypothesis: in hybrids alpha concentrates on i in G (global layers) well
beyond their 1/4 share, sum_{i in G} alpha_{i->l} >= 0.5 for linear layers l. Test operator G-AttnRes: sources = {u_{l-1}} union
{u_i : i in G, i < l} — O(L/4) sources, memory O((L/4) d) vs Block AttnRes O(N d), one d-vector per layer. Gated-Residual
analogue: reserve one of four branches to be written only by global layers (GR-anchor); mHC analogue: constrain the
Sinkhorn mixing so one stream receives only global writes. Interaction statistic: Delta_hyb = loss(pre-norm) - loss(Block
AttnRes) in the 3:1 hybrid vs Delta_dense in an iso-parameter dense twin on the same tokens; hypothesis Delta_hyb >
Delta_dense. Secondary probe on the same runs: depth-routing equivariance across translations — JSD between the alpha
distributions of aligned tokens in parallel sentences vs random token pairs at matched position (bookmarks G2). MTP arm
(from the dropped state-read-mtp-drafts): MTP-off vs MTP full-block at iso-tokens on the same substrate, measuring
retention horizon per DASC (2608.30386), MQAR at long lag and NTP loss (AdaMTP interference risk).

**What is new.** Attention Residuals gives mechanism, Block AttnRes, scaling laws and Kimi Linear integration with single
runs and no analysis of which layers are read in a hybrid; Qwen3.8-Next observes that one Gated-Residual branch preserves
early attention outputs but does not restrict writes to global layers, compare against a dense twin, or use multiple
seeds; SANA-Video 2.0 states the anchor-reuse interpretation for a bidirectional video DiT as a first-party reading. Delta:
a falsifiable restricted-source operator, an alpha-mass measurement, and a hybrid-vs-dense interaction test with
multi-seed statistics in causal LMs; 2606.13168 ("the largest mass slice is not the largest causal contribution") is why
the restricted operator, not the weights, carries the claim. No direct prior art found through 2026-09-01 under the
coverage in J §"Candidate 2" (arXiv attention residuals / hyper-connections / gated residual x hybrid / linear attention ->
21, none isolating global-layer sources; AttnRes variant stream all dense).

**Closest priors.**
- Attention Residuals — https://arxiv.org/abs/2603.15031 — 2026-03-16 — Block AttnRes, scaling laws, Kimi Linear integration; single runs.
- On the Design of Qwen3.8-Next — https://arxiv.org/abs/2608.30320 — 2026-08-31 — Gated Residual with four branches; anchor branch observed, not restricted.
- SANA-Video 2.0 — https://arxiv.org/abs/2607.21553 — 2026-07-23 — Block AttnRes routes block summaries into later linear layers (+~12% deep-layer effective rank), video DiT.
- mHC — https://arxiv.org/abs/2512.24880 — 2025-12 — manifold-constrained hyper-connections; mHC-lite 2601.05732.
- RD-AttnRes — https://arxiv.org/abs/2608.01075 — 2026-08 — 5-seed paired protocol at 120M/343M (adopted).
- When Does Routing Become Interpretable? — https://arxiv.org/abs/2606.13168 — 2026-06 — routing mass is not causal contribution.
- Windowed-MTP — https://arxiv.org/abs/2607.21535 — 2026-07-23 — and AdaMTP 2608.00434 (MTP interference) for the MTP arm.

**Falsifiable predictions.**
- P1 (125M / 2.5B tokens, 3:1 GDN hybrid): Block AttnRes gains >= 0.015 nats over pre-norm (paired, 2 seeds), and G-AttnRes recovers >= 80% of that gain with <= 30% of Block AttnRes's depth-source memory.
- P2: in the trained hybrid Block/Full AttnRes, depth-attention mass on global-layer outputs from linear layers averages >= 0.5 (uniform share 0.25); in the dense twin a matched random 25% layer subset receives <= 0.35.
- P3 (interaction): Delta_hyb - Delta_dense >= 0.008 nats at iso-parameters/tokens across 5 seeds (paired); in hybrid mHC and GR twins the dominant stream/branch is the one carrying global-attention outputs, and restricting it to global-layer writes costs <= 0.005 nats.
- P4 (secondary, parallel data): JSD over depth between alpha of aligned tokens in translation pairs is <= 0.5x the JSD between random token pairs at matched position; MTP arm: MTP-on changes the median retention horizon of linear-layer units by a factor outside [0.8, 1.25] or NTP loss by >= 0.005 nats (either direction answers G11).

**Kill conditions.** G-AttnRes recovers < 50% of the gain or alpha mass on G <= 0.30 (skip-read hypothesis dead); Delta_hyb <= Delta_dense (depth operators fix pre-norm dilution generically); Block AttnRes gain <= 2x the seed SD from the same grid (depth operators unresolvable at 125M; report the seed-variance atlas, G20).

**Cheapest decisive pilot.** Phase 0 (CPU): exact-equivalence doctors (G-AttnRes with all layers as sources == Full AttnRes to 1e-6; Block AttnRes with block size 1 == Full AttnRes); a dilution calculator giving the effective weight of layer-4k outputs in h_l under pre-norm from measured update norms; two-forward-pass causality audit of the fla AttnRes (Gluon) kernel. Phase 1 (<= 15 GPU-h): 125M 3:1 GDN hybrid arms {pre-norm, Block AttnRes N = 6, G-AttnRes} + dense twin arms {pre-norm, Block AttnRes} (smollm2-135m layout) x 2 seeds = 10 runs x ~1.3 GPU-h; alpha-mass and JSD probes on parallel sentences ~1 GPU-h; matched-random-subset AttnRes arm and MTP-on/off pair if budget remains. Phase 2 (the G9 comparison, ~40 GPU-h, new contract): 350M, 5 seeds, add Full AttnRes, mHC + mHC-lite, Gated Residual, GR-anchor, RD-AttnRes, Delta AttnRes, MHAR; SWA+sinks hybrid twin; MTP-off / full-block / state-read heads.

**pilot_gpu_hours.** 15.

**Controls.** Mandatory 2026 depth operators: Qwen Gated Residual (2608.30320), mHC (2512.24880) and mHC-lite (2601.05732); Block/Full AttnRes (2603.15031); RD-AttnRes (2608.01075, 5-seed paired protocol), Delta AttnRes (2605.18855), MHAR (2607.27230); iso-parameter and iso-FLOP twins (AttnRes adds one d-vector per layer; mHC/GR branch parameters matched by width); dense-transformer twin for the interaction; matched-random-25%-subset AttnRes ("any sparse source set works" control); stream-collapse diagnostics (2606.03483); startlux 340M/1.3B pre-norm hybrids (2608.12149); two-forward-pass audit (2608.22876); SWA+sinks hybrid twin (2608.28444); per-arm HP search (2608.11859); generation-based evaluation; early extension probe; MTP-off iso-token and iso-FLOP arms with retention-horizon measurement per DASC; QED/MARCH on MTP-off backbones for any recall number.

**Kevin advantage.** fla >= 0.5.2 ships AttnRes (Gluon backend) plus GDN/KDA in one library; the harness's seed/checkpoint contract fits a 5-seed grid; parallel translation data makes the depth-routing equivariance probe (P4) one nobody else has framed. Honest: the core interaction test is runnable by any academic lab; the advantage is the parallel-data probe and the willingness to publish the seed atlas.

**collision_risk.** medium (J searches above; SANA-Video 2.0's authors already state the interpretation; Kimi and Qwen have the compute; the AttnRes-variant stream publishes monthly).

**Monitorability and safety.** Depth-attention weights are an inspectable routing tensor; 2606.13168 warns mass is not causal contribution, which is why the restricted operator carries the claim. No CoT/action-monitorability effect. Open data only.

**Negative-result value.** If the gain is not anchor-driven, the grid still delivers G9's first independent iso-compute multi-seed comparison and a seed-variance atlas (G20); a null interaction tells hybrid builders that AttnRes/GR/mHC are generic dilution fixes, not hybrid-specific ones, which changes where to spend the depth-memory budget; the MTP arm answers G11 either way.

**targets_gaps.** G9, G11, G2, G12, G20.

---

## Coverage limits (inherited; honest)

All collision searches were run by the inventor cells on 2026-09-01 with WebSearch exhausted: host-proxied arXiv API
(exact-phrase abs queries, 25 newest per query), HF papers, OpenReview (titles often unreadable), DuckDuckGo (frequently
blocked), WebFetch of arxiv.org/abs pages, GitHub and HF model/adapter APIs. Semantic Scholar, Google Scholar, ACL
Anthology, Chinese-language sources, live X, ICLR 2027 submissions and closed-lab systems were not searched. Most priors
were read at abstract level; full texts were read for 2607.27539, Backpropamine (pp. 1–10), the Qwen3.8-Next report
(seq-operators cell), K3 and AttnRes (seq-operators cell). GPU-hour figures are estimates (~1–1.5 GPU-h per 125M / 20N-token
run on one H100); nothing was executed on the node except the fp64 c_state_doctor.py check for candidate 6. Classical
control/neuroscience/coding sources were cited from memory by the H cell and must be re-opened before proposal writing.
