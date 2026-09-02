# semantic-clock-gate-parity — wave-2 repaired candidate (2026-09-01)

Repair owner note. Wave 1: novelty NOT refuted (0.6, with caveats), identification REFUTED (0.8),
feasibility REFUTED (0.66). Every objection is mapped to a fix or an accepted limitation in §12.
The decisive pilot is now a <= 4 GPU-h training-free phase 0 on a released base hybrid; the
from-scratch stage is re-costed honestly (~55 GPU-h) and gated on phase 0. No General Translation
data is required anywhere in the pilot.

## 0. Claim

In gated delta-rule / SSM layers (Gated DeltaNet, KDA; Mamba as a comparison family) the forgetting
gate and the write gate are applied once per token, so equal content costs a high-fertility language
proportionally more cumulative forgetting and write mass in semantic time. Claim, split into the
three testable parts the pilot addresses in order: (C1, measurement) released GDN/KDA gates do NOT
self-normalize this away — cumulative log-decay over a translated sentence scales with its token
count; (C2, causal) intervening on the clock alone (rescaling per-token log-decay for the text of
language L by 1/r) on a frozen base hybrid moves translation-paired recall with an optimum near
r = fertility(L), and the effect is fertility-specific (Thai/Chinese, non-Latin but low-fertility on
this tokenizer, behave like English); (C3, training-time mechanism) a scale-invariant, anchored
span-parity auxiliary loss on the existing gate statistics, supervised by sentence-aligned parallel
text at training time only, closes the recall gap at unchanged per-language bits-per-byte with no
inference change — and is pre-registered to be compared for EQUIVALENCE against a per-language
constant gate rescale, because the measured within-language span-ratio CV (0.17–0.24) bounds what
span-level supervision can add over a constant.

claim_scope: architecture-causal (phase 0 = measurement + within-model causal intervention on
released checkpoints; phase 1 = matched from-scratch arms).

## 1. Mechanism (equations in plain text)

Gated DeltaNet as implemented in transformers `qwen3_5` / fla `gated_deltanet` (Yang, Kautz,
Hatamizadeh 2412.06464): S_t = alpha_t S_{t-1} (I - beta_t k_t k_t^T) + beta_t v_t k_t^T, with
g_t = log alpha_t = -exp(A_log) * softplus(a_t + dt_bias) (scalar per head; per-channel vector in KDA)
and beta_t = sigmoid(b_t). For a span s (sentence-aligned in the pilot; sub-sentence alignments are a
GT-enabled upgrade) define forgetting mass F(s) = -sum_{t in s} g_t and write mass
W(s) = sum_{t in s} beta_t. Under a per-token clock F(s_L)/F(s_en) ~ |s_L|/|s_en| = fertility ratio.
Tallec & Ollivier (1804.11188) prove that learnable gates give recurrent models quasi-invariance to
input time warps; a fertility ratio is exactly such a warp, so "the LM loss already learned the warp"
(R_F ~ 1) is the live null that phase 0 tests first.

Phase-0 interventions (training-free, hooks on the 24 GDN layers of Qwen3.5-4B-Base):
- decay surgery, constant: g'_t = g_t / r for every token of the L-language episode, r on a log2 grid;
- decay surgery, span oracle: g'_t = g_t / r_s with r_s = |s_L|/|s_en| for each aligned sentence span s
  (NTREX is n-way parallel, so r_s is known per sentence);
- write surgery: beta'_t = 1 - (1 - beta_t)^{1/r}, chosen so the compounded write over r tokens
  equals one baseline token's write ((1-beta')^r = 1-beta). Because beta also scales the erase term
  k_t k_t^T, write surgery is reported with that coupling caveat (GDN-2, 2605.22791, decouples them;
  fla ships `gdn2.py`, used in phase 1 to ablate F- and W-parity separately).

Phase-1 training-time mechanism (arm b), on parallel-view batches where both translations are
present and each is processed monolingually (coupling only through span sums):
  L = L_LM + lambda * sum_{(s_a,s_b)} sum_{layers,heads} ( log(F(s_a)+eps) - log(F(s_b)+eps) )^2
           + lambda_W * (same with W)
           + kappa * ( mean_{t in en} g_t  -  anchor_en )^2 .
The log-ratio form is exactly invariant to a global rescale of all g (dL/dc = 0 for F -> cF), which
removes the wave-1 "forget less" shortcut (the chi-square form (F_a-F_b)^2/(F_a+F_b) had dL/dc > 0).
anchor_en is the detached EMA of the model's own English per-token mean log-decay at the end of
warm-up, so the English forgetting budget is pinned and only the RELATIVE clock can move. Only gate
parameters (a-projection, b-projection, A_log, dt_bias) receive the auxiliary gradient. The loss uses
span sums only (causal by construction; within-span permutation leaves it unchanged); it vanishes at
inference. Arm (ii) of wave 1 (a shared content clock c_t) is demoted to an optional confirmation
parameterization: as the novelty refuter noted it is Mamba's Delta_t (2312.00752) recombined with GDN
gating, and its only new element is the parity-constrained totals loss already carried by arm b.

## 2. What is new (downgraded per the novelty caveats)

- Gated DeltaNet — https://arxiv.org/abs/2412.06464 (2024-12-09): gates trained by LM loss only,
  clocked per token, no per-language analysis. Delta: a per-language cumulative forgetting/write
  ledger, a training-free clock-surgery dose-response as a causal test, and a scale-invariant
  span-parity supervision of the EXISTING gate statistics.
- Kimi Linear / KDA — https://arxiv.org/abs/2510.26692 (2025-10-30): channel-wise decay in a 3:1
  production hybrid, no per-language analysis. Delta: the same ledger and surgery per channel (optional
  arm; custom code).
- Tallec & Ollivier, "Can recurrent neural networks warp time?" — https://arxiv.org/abs/1804.11188
  (2018-03-23): gates provide quasi-invariance to time warps; chrono-init. Delta: they neither measure
  nor supervise the warp across languages; we test whether LM-trained gates realized the invariance
  for the fertility warp (phase 0) and, if not, supply the warp at training time from parallel text.
- Mamba — https://arxiv.org/abs/2312.00752 (2023-12-01): Delta_t is a learned per-token step size;
  totals never supervised across translations (arm (ii) is acknowledged as a recombination).
- Gated DeltaNet-2 — https://arxiv.org/abs/2605.22791 (2026-05): decouples erase and write; used here
  only as the substrate that makes F- and W-parity separately ablatable.
- MAGNET — https://arxiv.org/abs/2407.08818 (2024-07-11) and H-Net — https://arxiv.org/abs/2507.07955
  (2025-07): equitable / learned semantic granularity at the segmentation level (H-Net is an
  end-to-end semantic clock that changes the inference path). Delta: tokenizer fixed, parity enforced
  inside the recurrent operator, inference unchanged.
- Parity-aware BPE — https://arxiv.org/abs/2508.04796 (ACL 2026) and "Equity with Efficiency" —
  https://arxiv.org/abs/2606.15044 (2026-06-13): tokenizer-side parity. Used as a mandatory arm (h).
- "Vowel Signs Are Not Letters" — https://arxiv.org/abs/2608.26449 (2026-08-26): abugida
  pre-tokenization floor 1.47x–9.02x from the `\p{L}+` word class. Delta: the phase-0 subject tokenizer
  is already mark-aware (verified regex `[\p{L}\p{M}]+`, vocab 248,044), so this floor does not enter
  the measurement; all phase-1 tokenizers use the mark-aware class.
- Adaptive Memory Decay for Log-Linear Attention — https://arxiv.org/abs/2605.06946 (2026-05-07):
  content-adaptive decay, monolingual.
- Leino & Tiedemann — https://arxiv.org/abs/2603.29026 (2026-03-30): parallel data barely moves
  representations; gate statistics are a different observable and the nil result is pre-registered.
Honest statement: no direct prior art found through 2026-09-01, under the coverage in §11, for (a) a
per-language cumulative decay/write ledger on released GDN/KDA checkpoints, (b) a fertility-predicted
clock-surgery dose-response, (c) a translation-paired recall probe with script-neutral answers and
n-way matched-content distractors, or (d) cross-lingually supervised gate statistics. The idea is a
recombination (new observable + new supervision target), not a new operator or gate.

## 3. Phase 0 — the cheapest decisive pilot (<= 4 GPU-h, no GT data)

Subject checkpoints (exact repos, revisions):
- Qwen/Qwen3.5-4B-Base, revision 1001bb4d826a52d1f399e183466143f4da7b741b (apache-2.0; 32 layers =
  24 `linear_attention` GDN + 8 `full_attention`, full_attention_interval 4, 16 linear key heads x 32
  value heads, head dims 128; tokenizer vocab 248,044, mark-aware pre-tokenizer). Registry currently
  pins the post-trained Qwen/Qwen3.5-4B (851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a); the Base must be
  registered (same architecture, same tokenizer).
- Size ladder for the ledger only (cheap): Qwen/Qwen3.5-0.8B-Base dc7cdfe2ee4154fa7e30f5b51ca41bfa40174e68,
  Qwen/Qwen3.5-2B-Base b1485b2fa6dfa1287294f269f5fb618e03d52d7c.
- Optional (+1.5 GPU-h on 2 GPUs, outside the 4 GPU-h): moonshotai/Kimi-Linear-48B-A3B-Base
  3b171c17bfc4ee348599b6781a2ca8715c21c8dc (registry kimi-linear-48b-a3b-base; KDA channel-wise decay;
  trust_remote_code; publication_eligible false) — ledger + constant surgery only.
- DROPPED from the ledger (wave-1 feasibility): fla-hub/delta_net-1.3B-8K-100B (ungated DeltaNet,
  no alpha_t), state-spaces/mamba-130m-hf (Pile/English only), startlux-models/* (undisclosed
  training-language composition).

Corpora (public, license-named):
- NTREX-128, GitHub MicrosoftTranslator/NTREX @ 468c6b69c7f6a75d31d4743d9daba2af566cc18d,
  CC-BY-SA-4.0; 1,997 n-way parallel news sentences. Used for the ledger, the span-ratio CV, and as the
  matched-content distractor pool.
- FLORES+ (HF openlanguagedata/flores_plus @ 5fec6c13f9e5a4db2f745d4ec0d7c9721ddc4f06, CC-BY-SA-4.0,
  gated auto-approve): SEALED for the phase-1 held-out endpoint; not touched in phase 0.
- Probe facts: 12 English templates x 300 entity noun phrases ("the password of <NP> is <4 digits>"),
  translated into the 11 non-English languages with NLLB-200-distilled-600M (facebook/nllb-200-distilled-600M,
  CC-BY-NC-4.0, research use). Answers are 4-digit codes — identical across languages, so exact match
  carries no morphology variance. Human spot-check of 20 items/language is optional (GT upgrade).

Languages (fertility measured on the Qwen3.5-4B-Base tokenizer over NTREX-128 on 2026-09-01 by this
owner; bytes ratio vs English in parentheses; within-language per-sentence ratio CV last):
  en 1.00 (1.00) | pol 1.61 (1.20) 0.22 | fin 1.63 (1.14) 0.19 | hun 1.71 (1.24) 0.20 | ukr 1.79 (1.93) 0.20
  | hin 2.07 (2.71) 0.19 | ell 2.12 (2.18) 0.20 | ben 2.17 (2.63) 0.19 | tam 2.75 (3.42) 0.21
  | mya 4.18 (3.50) 0.24 (stress) | low-fertility non-Latin CONTROLS: tha 1.17 (2.64) 0.22, kor 1.28,
  zho-CN 0.93 (0.96) 0.22.
High-fertility set H = {pol, fin, hun, ukr, hin, ell, ben, tam} (+ mya as stress); control set
C = {tha, zho-CN}; reference en. The Thai/Chinese controls separate "non-Latin script / data
disparity" from "fertility": under the clock hypothesis they behave like English.

Components:
0a. CPU doctors (no LM): NumPy GDN simulator with token duplication x k verifying F scales x k and
    recall at fixed semantic distance falls; gradient check of the log-ratio loss and exact
    verification that (i) it is invariant to a global rescale of g, (ii) the same-language pair loss is
    invariant to a per-language rescale (gradient projection on the between-language mean is zero);
    causality doctor (within-span permutation invariance; injected future-token leak detected).
0b. Ledger: per NTREX sentence x in language L, F(x) and W(x) per layer/head; R_F(L) = F(x_L)/F(x_en)
    and R_W(L), pooled over sentences with sentence-clustered CIs, plotted against fertility f_L. Also
    the per-sentence ratio CV (above) as the bound on span-level information.
0c. Translation-paired recall probe. Episode = K = 8 facts in language L, then d consecutive NTREX
    sentences in L (same sentence run for every language of the same episode id), then a query for one
    fact (position permuted, 1 of 8), greedy decode 4 tokens, exact match on the 4-digit code.
    d in {8, 32} sentences (content distance; token distance = d * 26 * f_L approx). 600 episodes per
    (language, d). Paired by episode id across languages; episode-clustered bootstrap (2,000 resamples).
0d. Surgery dose-response (the causal test): for each language incl. English, constant decay surgery
    at r in {0.5, 0.71, 1, 1.41, 2, 2.83, 4} plus r = f_L exactly; span-oracle decay surgery; write
    surgery at r = f_L; decay + write at r = f_L. Per language fit EM(log r) with a quadratic, take
    r*(L) with bootstrap CI. Clock signature = slope of [log r*(L) - log r*(en)] on log f_L across the
    12 languages. Also per-language BPB on NTREX under each r (surgery must not be reported as a
    "fix" if it wrecks LM competence).
0e. Equivalence test (view necessity, training-free): span-oracle vs constant surgery at r = f_L,
    paired within episodes; pre-registered equivalence margin 3 EM points (TOST, alpha 0.05).

Budget (arithmetic shown): forwards = 12 languages x 2 d x 600 episodes x 11 settings = 158k;
mean episode length ~1.3k tokens (at d=32: (8x12 + 32x26) x f_L, f_L up to 2.75) -> 2.1e8 tokens;
FLOPs ~ 2 x 4e9 x 2.1e8 = 1.7e18; at a deliberately low 20% MFU on H100 (HF eager + hooks, bf16;
200 TFLOP/s) = 2.4 GPU-h; ledger + BPB-under-surgery 0.5 GPU-h; total 2.9 GPU-h; +25% reserve = 3.6
GPU-h -> pilot_gpu_hours = 4. If measured MFU is lower, the r-grid drops to 5 points before anything
else is cut. Kimi-Linear optional +1.5 GPU-h is outside this number.

## 4. Falsifiable predictions (phase 0 unless marked)

- P1 (ledger, C1): on Qwen3.5-4B-Base GDN layers, R_F(L) >= 0.8 f_L for every L in H (f_L >= 1.5);
  R_W(L) >= 0.8 f_L likewise. Embarrassing if R_F is within 15% of 1.0 while f_L >= 2 (gates already
  warp-invariant; Tallec-Ollivier null holds).
- P2 (baseline gap): at d = 32, EM(en) - EM(L) >= 10 points for tam, ben, hin, ell, and EM(tha),
  EM(zho) within 5 points of EM(en). Embarrassing if Thai/Chinese show the same gap as Tamil (gap is
  script/data, not fertility).
- P3 (dose-response, C2): r*(L)/r*(en) lies in [0.7 f_L, 1.4 f_L] for >= 6 of the 8 languages in H, and
  the clock-signature slope is >= 0.5 (95% CI excluding 0.2). Embarrassing if r*(L) ~ r*(en) for all L.
- P4 (interaction, anti-shortcut): the EM gain at r = f_L in L exceeds the EM gain at the same r in
  English by >= 5 points (uniform "forget less" is not the explanation).
- P5 (equivalence, honest): span-oracle surgery beats constant surgery by <= 3 EM points (expected,
  given span-ratio CV ~0.2). If it beats by > 3 points the parallel view carries information a
  language constant cannot, and the phase-1 treatment arm b stays; otherwise arm b is replaced by the
  constant-rescale recipe (arm c) and the deliverable is the ledger + recipe.
- P6 (phase 1, C3, gated): 60M pure GDN, 5 seeds: arm b (span parity) reduces the FLORES+-based
  translation-paired recall gap by >= 50% relative to arm a with per-language BPB within +1%; the
  full-attention arm f shows a gap <= 30% of arm a's; the uniform-decay arm d recovers < 25% of arm b's
  reduction; the same-language placebo e recovers < 15%.

## 5. Kill conditions

Phase 0 (each kills before any training):
- K1 self-normalization: R_F within 15% of 1 for all L with f_L >= 1.5.
- K2 clock not the bottleneck: signature slope < 0.2 (CI excludes 0.5); or no interior optimum for any L.
- K3 uniform effect: interaction (P4) <= 2 points for all L in H — "forget less" helps everyone equally.
- K4 script/data, not fertility: EM(tha), EM(zho) gaps within 3 points of the Tamil/Bengali gap.
- K5 view unnecessary: span-oracle <= constant + 3 points (TOST passes) -> demote to normalization
  recipe (candidate survives as measurement + recipe; the parallel-view TRAINING mechanism is dropped).
- K6 leakage: two-forward-pass prefix-invariance audit (2608.22876) finds the probe or hooks leak.
Phase 1: arm b < 50% relative gap reduction over 5 seeds (paired, episode-clustered SE); b equivalent to
c under TOST (margin 2 points) -> recipe, not view; d matches b within noise -> shortcut; f shows >= 70%
of a's gap -> gap is not clock-specific; h alone closes >= 80% -> tokenizer-side fix suffices; any
language loses > 1% BPB.

## 6. Phase 1 (separately gated; NOT the pilot) — honest re-cost

Substrate: 60M-parameter models (12 layers, d = 512, 8 heads, 32k vocab), fla >= 0.5.2
(released 2026-07-27) `gated_deltanet` / `gdn2` / `attn` layers, T = 2048, 600M tokens (10N) per run.
Throughput assumption, cited: puigde/gated-deltanet-360M-15B-slimpajama model card (first-party):
357.8M params, 15.03B tokens in ~9.3 h on 8x A100-SXM4-40GB, T = 2048 -> ~56k tok/s/GPU (~39% of
A100 dense-BF16 peak by 6ND). Wave-1 also read NVlabs/GatedDeltaNet's 0.4B script (~33k tok/s/GPU)
and 2412.06464's ~40k tok/s/GPU at 1.3B on H100 (~31.5% MFU); fla's README benchmark shows chunk_gdn
loses to FlashAttention-2 at small shapes. Naive scaling 358M -> 60M (6x fewer FLOPs) and A100 -> H100
(~2x) would give ~670k tok/s/GPU; we budget 200k tok/s/GPU (30% of naive) and re-measure in the first
10 minutes of the first run. Per run: 600M / 200k = 3,000 s = 0.83 GPU-h.
Arms (all consume the identical token stream and data order):
  a GDN baseline (data-only control: parallel pairs present, no auxiliary term)
  b GDN + anchored log-ratio span parity (treatment)          [5 seeds]
  c GDN + learned per-language constant gate rescale (language-ID scalar on g and beta) [5 seeds]
  d GDN + uniform decay regularizer matched to arm b's realized mean shift in g (iso-forgetting budget)
  e GDN + same-language random-pair log-ratio loss (provably inert placebo, see §12)
  f full-attention transformer, same tokenizer/data/params (clock-free bound)
  g SWA(512) + sinks at matched state bytes (2608.28444) — a token-window clock, not the clock-free bound
  h GDN baseline with Parity-aware BPE tokenizer (2508.04796) at 32k
  i synthetic fertility (mechanism, not view): English-only corpus, coarse 32k vs 2x-finer tokenizer;
    fine + constant oracle rescale (3 runs) — tests fertility -> gap -> decay-normalization with content
    held exactly constant; with near-constant span ratio it is explicitly NOT a test of the view
  j 3:1 GDN:attention hybrid, baseline and treatment (localization, 2606.15378)
  k GDN-2 (fla gdn2.py) baseline + F-only + W-only parity (decoupled erase/write; 3 runs) [confirmation]
Seeds: 5 for a–d (equivalence block), 3 for e–j; k in confirmation. Runs: 20 + 27 = 47 -> 39 GPU-h;
per-arm LR sweep at a 30M rung (4 LRs x 5 arms x 0.15 GPU-h) = 3 GPU-h; evaluation 2 GPU-h; total 44
GPU-h; +25% reserve = 55 GPU-h (~7 node-hours on 8xH100). A 16-GPU-h "lite" variant exists (40M/400M
tokens, arms a–d,f x 3 seeds = 13.6 GPU-h incl. reserve) but cannot resolve the b-vs-c equivalence at
the pre-registered margin and is not called decisive.
Data (equal-CONTENT, not equal-byte): content per language is measured in English-equivalent tokens:
for parallel pairs, the English side's token count; for monolingual documents, bytes divided by the
language's bytes-per-English-token ratio measured on NTREX (§3). Mixture 60% FineWeb-2 documents
(HF HuggingFaceFW/fineweb-2 @ af9c13333eb981300149d5ca60a8e9d659b276b9, ODC-BY) at equal estimated
content + 40% parallel pairs packed as blocks of 8–16 consecutive pairs (parallel-view batches carry
both sides as separate sequences). Parallel sources: ParaCrawl release 9 (paracrawl.eu, CC0 — "We
license the actual packaging of these parallel data under the Creative Commons CC0 license"; en-pl
40.1M, en-fi 31.3M, en-hu 36.4M, en-el 21.4M pairs; South/East Asian bonus release Nov 2024 incl.
en-hi, en-th, en-ko, en-my; bicleaner score >= 0.7; OPUS mirror Helsinki-NLP/opus_paracrawl),
NLLB-mined (HF allenai/nllb @ c36967abb45f06ff7659849372ab41e01838193e, ODC-BY; eng_Latn-ben_Beng,
eng_Latn-tam_Taml, eng_Latn-ukr_Cyrl, eng_Latn-hin_Deva), Europarl v7 (statmt.org, "not aware of any
copyright restrictions"; en-pl 632k, en-fi 1.92M, en-hu 625k, en-el 1.24M) as a clean-domain EU slice;
Samanantar (HF ai4bharat/samanantar @ ead34c5b22a0354d350e7dfdd6aece7df5a48f37, CC-BY-NC-4.0) only as
a research-only fallback for bn/ta. Tokenizers: 32k byte-level BPE with the mark-aware word class
`[\p{L}\p{M}]+` trained on the equal-content mix; Parity-aware BPE at 32k for arm h. Held-out endpoint:
translation-paired recall episodes built from FLORES+ devtest (sealed) with a disjoint fact-template set,
d in {8, 16, 32, 64}; per-language BPB on FLORES+ devtest. The training loss sees only ParaCrawl/NLLB
gate sums; the endpoint is never seen -> no metric-equals-objective circularity. Gate parity (R_F) is a
manipulation check, never an endpoint.

## 7. Controls (matched)

Within-model surgery (phase 0) holds tokenizer, data, parameters and everything but the clock fixed;
Thai/Chinese low-fertility non-Latin controls; English under the same r (interaction control); constant
vs span-oracle (equivalence); write-only and decay+write surgery (interference/write-count alternative);
BPB under surgery. Phase 1: data-only control (a); iso-parameter / iso-FLOP / iso-wall-time (auxiliary
cost < 2% train FLOPs, reported); full-attention arm (f); SWA+sinks (g); Parity-aware BPE arm (h);
uniform decay regularizer at matched forgetting budget (d); provably inert same-language placebo (e);
learned per-language constant rescale (c) as the primary comparator with TOST; synthetic-fertility
English (i); hybrid localization (j); GDN-2 decoupled F/W (k); QED (2608.13668) and MARCH (2608.12435)
measured with the same instrument in confirmation; MLNeedle (2408.10151) and ONERULER (2503.01996)
cited as the softmax-transformer cross-lingual retrieval baselines; per-arm LR sweep at 30M; generation
exact match with permuted fact positions; two-forward-pass prefix-invariance audit (2608.22876);
DASC-style per-head retention horizons per language as a free diagnostic.

## 8. Kevin advantage (honest)

Phase 0 needs only public NTREX and a released base checkpoint — any lab can run it; the advantage
there is the harness (hooks, seeded episodes, exact-match generation, checkpoint/resume) and the
compute to run the full 11-setting grid in an afternoon. General Translation data is an OPTIONAL
upgrade: sub-sentence span alignments (turning the sentence-level view into a phrase-level one, which
is where span-ratio variance is largest), terminology/named-entity stress sets, human-verified probe
templates, and production language coverage for confirmation. 8xH100 makes the 55 GPU-h phase 1 a
one-day job.

## 9. Collision risk

low–medium. Searches: wave-1 coverage in A-translation-supervised.md §5 and F-compute-equity.md §5;
novelty refuter's arXiv x4 / HF papers x2 / OpenReview x1 / WebFetch x10; this repair's fresh arXiv
query `(linear attention OR state space OR delta rule OR mamba) AND (multilingual OR fertility OR
cross-lingual) AND (decay OR gate OR forgetting)` -> 1 result (RWKV-7, known, no per-language gate
analysis). Risk driver: the delta-rule gate axis is dense (GDN-2, QED, Preconditioned DeltaNet), so a
content-scaled gate could appear without the cross-lingual framing; the phase-0 ledger + surgery is
publishable within weeks and is the first-mover claim.

## 10. Monitorability and safety

No CoT or action channel is touched. The per-language forgetting/write ledger and the surgery
dose-response are new interpretability handles. Training arms add a "clock injection" surface
(adversarial text driving g_t toward 0 pins state; toward large negative flushes it): pre-register a
g_t clamp and report the g_t distribution under adversarial suffixes. Data rights: NTREX-128 and
FLORES+ CC-BY-SA-4.0; ParaCrawl CC0; NLLB-mined and FineWeb-2 ODC-BY (bound by source terms);
Europarl no known restrictions; Samanantar CC-BY-NC-4.0 (research only, fallback); NLLB-200 MT outputs
CC-BY-NC-4.0 (probe generation, research only); Qwen3.5 apache-2.0; Kimi-Linear MIT (custom code,
non-publication lane). IP note: NVIDIA US20260105282A1 "Gated delta networks" (pending) — no kernel-level
delta-rule contribution is made here; the contribution is a measurement, an intervention and a loss.

## 11. Coverage limits

Abstract-level reading for priors (arxiv abs pages via the H100 host and WebFetch); full texts of
Kimi Linear, GDN-2, RWKV-7 multilingual sections not read for incidental per-language gate analyses.
DDG blocked; Semantic Scholar unavailable; WebSearch budget exhausted; no Google Scholar / ACL
Anthology full search; grey literature after 2026-08-10 under-covered. Fertility numbers were measured
by this owner (Qwen3.5-4B-Base tokenizer.json @ 1001bb4d…, NTREX @ 468c6b6…, tokenizers library) — the
CV figures are per-sentence, not per-phrase. Throughput is an assumption anchored to the cited puigde
card and must be re-measured; nothing was executed on the node.

## 12. Repairs made (wave-1 objection -> fix or accepted limitation)

Identification (refuted 0.8):
1. "Aligned parity loss is satisfied to first order by a per-language constant rescale (= the
   monolingual oracle), so the strongest control collapses onto the treatment; P3's synthetic arm
   cannot evidence the view; 70–95% window unresolvable with 3 seeds." -> The equivalence question is
   now the pre-registered PRIMARY comparison and is answered training-free in phase 0 (span-oracle vs
   constant surgery, paired within 600 episodes/cell, SE ~1.3 points, TOST margin 3) and in phase 1
   (arm b vs arm c, 5 seeds, TOST margin 2). The measured within-language span-ratio CV (0.17–0.24)
   is reported as the a-priori bound on what span-level supervision can add. The synthetic-fertility
   arm is relabelled a mechanism test (fertility -> gap -> decay normalization), explicitly not a view
   test. Accepted limitation: P5 expects equivalence at sentence granularity; if K5 fires the training
   mechanism is demoted to a per-language normalization recipe and the candidate survives as ledger +
   surgery + recipe (dropped = false because the measurement and causal claims C1–C2 stand on their own).
2. "Shuffled-pair placebo is not inert (preserves language marginals, equalizes cross-language means
   through the same channel)." -> Dropped. Replaced by a same-language random-pair loss in log-ratio
   form: each per-language term is exactly invariant to a per-language rescale of F, so its gradient
   has zero projection on the between-language log-mean difference (verified numerically in doctor 0a).
   It controls only for within-language variance shrinkage, which is what a placebo should isolate.
3. "Chi-square parity loss has dL/dc > 0 -> 'forget less' regularizer; no anchor; no uniform-decay
   control; +1% BPB absorbs the cost." -> Loss changed to squared log-ratio (dL/dc = 0 exactly), plus an
   English forgetting-budget anchor (detached EMA at end of warm-up), plus arm d (uniform decay
   regularizer at matched realized mean shift), plus the phase-0 interaction test (same r on English).
4. "Baseline gap is a tokenizer effect with no clock-free bound; GPT-2 regex abugida breakage;
   parity-aware BPE absent; SWA+sinks is itself a per-token clock; EM across morphologically rich
   languages adds surface-form variance." -> Phase-0 subject tokenizer verified mark-aware
   (`[\p{L}\p{M}]+`), so the 2608.26449 floor does not apply; Thai (f = 1.17) and Chinese (0.93)
   added as non-Latin low-fertility controls; the within-model surgery is the clock-only intervention
   at fixed tokenizer/data; phase 1 adds a full-attention arm (f) at matched tokenizer/data/params and a
   Parity-aware BPE arm (h); SWA+sinks (g) is retained but relabelled a token-window clock; answers are
   4-digit codes so EM has no morphology component. Accepted limitation: no same-tokenizer pure-attention
   sibling of Qwen3.5-4B-Base exists (Qwen3-4B-Base uses a different 151k `\p{L}+` tokenizer), so the
   phase-0 clock-free bound comes from the dose-response (a gap unchanged under every r is non-clock),
   not from a separate model.
5. "Recall bounded by state size / key interference scaling with token count; beta couples erase and
   write so F- and W-parity are not independent; phase-0 recall on released checkpoints is causally
   uninterpretable." -> Surgery decomposed into decay-only, write-only (closed-form beta' = 1-(1-beta)^{1/r})
   and both; the residual gap after the best decay rescale is pre-registered as the write-count /
   interference share; phase 1 arm k uses GDN-2 (fla gdn2.py) to ablate F- and W-parity separately;
   phase-0 recall is interpreted only through within-model differences (episode-paired, same content),
   never as absolute cross-language levels. State-size ladder deferred to confirmation (accepted).
6. (implicit) metric-equals-objective -> primary endpoint is held-out translation-paired recall on
   FLORES+ devtest episodes + per-language BPB; gate parity is a manipulation check only.
Feasibility (refuted 0.66):
7. "27B tokens in 14.4 GPU-h needs 521k tok/s/H100 at a 100M GDN; realistic 130–450k; omits LR sweep,
   eval, tokenizer training, P3 and P4 arms." -> The decisive pilot is now phase 0 at <= 4 GPU-h with
   explicit arithmetic and a 25% reserve; phase 1 is re-costed at 55 GPU-h (200k tok/s/GPU assumption
   anchored to the puigde card's 56k tok/s/GPU on A100-40GB and the fla small-shape caveat; LR sweep,
   eval, all arms and reserve included) and is separately gated on P1–P4.
8. "P3 is the only thing separating the tokenization clock from per-language competence and is
   unbudgeted; equal-byte mixing gives high-fertility languages less content (hin 2.71x bytes)." ->
   P3 (arm i) is inside the phase-1 budget; phase 0 uses n-way NTREX so content is identical across
   languages by construction; phase-1 mixing is equal-CONTENT (English-equivalent tokens; monolingual
   documents normalized by the measured bytes-per-English-token ratio), not equal-byte.
9. "Three of five phase-0 checkpoints cannot support R_D (ungated / English-only / undisclosed)." ->
   Dropped; ledger runs on Qwen3.5-4B-Base (+0.8B/2B-Base ladder) and optionally Kimi-Linear.
10. "P2 endpoint not operationalized; 6 languages unnamed; 150M-token parallel source unnamed." ->
   Full grid specified (languages, d, K, episodes, decoding, EM, pairing, bootstrap); 12 languages named
   with measured fertility; parallel sources named with licenses, sizes and revisions (ParaCrawl v9 CC0,
   NLLB-mined ODC-BY, Europarl v7, Samanantar CC-BY-NC fallback, FineWeb-2 ODC-BY).
Novelty caveats (not refuted, 0.6):
11. "Cite Tallec & Ollivier 1804.11188 and Mamba Delta as direct ancestors; downgrade arm (ii)." ->
   Done: 1804.11188 is now the theoretical null that phase 0 tests; arm (ii) demoted to an optional
   confirmation parameterization; GDN-2 cited for erase/write decoupling; what_is_new stated as a
   recombination (new observable + supervision target), not a new gate.
