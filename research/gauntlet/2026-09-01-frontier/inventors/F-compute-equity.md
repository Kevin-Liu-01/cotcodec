# Design note F — cross-lingual compute equity inside the model (inventor F-compute-equity, 2026-09-01)

Angle. Make the model's compute-bearing knobs tick in units of meaning rather than tokens: the recurrent
state's decay/write clock, the per-token depth (or expert-count) router, and the latent sequence length the
deep trunk operates on. Parallel translations are used only as the source of "same meaning" supervision
(sentence- or span-level totals must match), never as a representation-alignment target (that route is
pre-killed by Leino & Tiedemann 2603.29026). Every mechanism is judged on a FLOPs-per-aligned-sentence
ledger plus per-language non-inferiority, so cost equity cannot be bought by quality loss in the languages it
claims to help. Targets: synthesis G19 (routing consistency + compute-per-semantic-unit parity), G2
(language/script-controlled recurrent-state probes), G20 (missing 0.1–1B instruments), G1 (sharpening dir 18).

Honesty. No "completely novel" claim anywhere. Where a gap is asserted the wording is "no direct prior art
found through 2026-09-01 under the coverage in §5". Every prior below was opened at its arXiv abstract page
with WebFetch on 2026-09-01 unless marked "(not opened; cited from cell note)". All 2026 numbers quoted are
first-party unless a venue is named. Compute arithmetic assumes ~55 TFLOPS effective per H100 for 60M-class
models with fla/Triton kernels (conservative); nothing was executed on fal-h100-01 except the curl relay.

Inputs read in full: context.md; design/brief.md; sweep/synthesis.md (§0–§4, §6; §7 bibliography skimmed);
sweep/tokenizer-free-multilingual.md; sweep/seq-operators.md; sweep/benchmarks-eval.md G2 section;
experiments/architectures/translation-equivariant-byte-patches.yaml; directions/18 grep; models/registry.yaml
ids; research/frontier-systems-program-2026-08-10.md rejected table grep.

Occupancy I must not re-propose (and why each candidate escapes it): fertility audits (saturated — used only
as inputs to the ledger); MAGNET per-script parity (a control arm in C, not the mechanism); parity-aware BPE
(a control arm in B and C — the "tokenizer vs inside-the-model" comparison is the point); adaptive depth
MoR/GRT/MixerLoop/CDB/RouteSparse (mandatory iso-FLOP baselines in B; none conditions on cross-lingual parity
or reports per-language cost); delta-rule gate geometry (A adds no new gate geometry — it reparameterizes the
existing gates through a shared clock and, before any training, measures whether released gates already
compensate for fertility); surprise-gated memory (A's clock is a causal feed-forward function of h_t with no
loss gradient and no write-time surprise, supervised only by parity of totals); dir 18 (C constrains trunk
compute per aligned unit on a subword substrate; dir 18 transports byte-boundary mass — different substrate,
different constrained quantity, and C is retrofit-able onto a pinned subword checkpoint).

Feasibility facts checked 2026-09-01: fla `chunk_gated_delta_rule(q,k,v,g,beta,...)` and `chunk_kda(q,k,v,g,
beta,...)` take per-token per-head `g` (log-decay) and `beta` tensors, so candidate A's reparameterization is a
pure PyTorch change (gh api, fla-org/flash-linear-attention main). `openlanguagedata/flores_plus` is
CC-BY-SA-4.0 (HF API, lastModified 2026-07-27). Registry ids: smollm2-135m (Apache-2.0), qwen3-0.6b-base
(Apache-2.0), qwen3.5-4b (Apache-2.0; 24 GDN + 8 full-attention layers per the seq-operators cell),
mamba-130m-hf (Apache-2.0), delta-net-1.3b-8k (fla-hub, licence unresolved — measurement only), blt-1b
(CC-BY-NC-4.0 — measurement only, no training).

---

## Candidate A (cheap-decisive) — `meaning-clocked-delta-rule`

**Claim.** In gated delta-rule / SSM hybrids, route the per-token decay and write gates through a shared
learned content clock c_t whose total over aligned translation spans is constrained to be equal, so the
recurrent state advances per unit of meaning rather than per token; the fertility-induced recall gap (same
facts, 2–4x more tokens) closes, at equal parameters and FLOPs. Phase 0 is a training-free measurement of
whether released gates already do this.

**claim_scope.** architecture-causal.

**Mechanism.** Baseline GDN layer (Yang, Kautz, Hatamizadeh 2412.06464): S_t = alpha_t (I - beta_t k_t
k_t^T) S_{t-1} + beta_t v_t k_t^T, o_t = S_t q_t, with alpha_t = exp(-softplus(a_t)) in (0,1) and beta_t =
sigmoid(b_t), a_t = W_a h_t, b_t = W_b h_t per head. Proposed: a scalar content clock c_t = softplus(w_c . h_t +
b_c) >= 0, shared across heads (and across the GDN layers of one block), with
  log alpha_t = - c_t * softplus(a_t)            (decay applied in proportion to content passed),
  beta_t      = 1 - exp(- c_t * softplus(b_t))    (write mass scales with content; beta stays in (0,1)).
Both g_t = log alpha_t and beta_t remain per-token per-head tensors, so fla's chunk_gated_delta_rule /
chunk_kda kernels are unchanged. Parity objective on parallel pairs (x_A, x_B):
  L_par = ( log sum_{t in A} c_t  -  log sum_{t in B} c_t )^2 ,   L = L_LM + lambda L_par + mu (mean_en c_t - 1)^2,
the last term pinning the clock's scale on the English reference so c and a are identifiable. Optional
span-level parity uses frozen aligned spans (OmniAlign/CTFAlign links, as in dir 18). Inference: unchanged;
one extra dot product per token. Phase-0 ledger on released checkpoints (no training): per FLORES-plus
sentence x in language L, D(x) = -(1/H) sum_t sum_h log alpha_{t,h} (total decay) and W(x) = (1/H) sum_t
sum_h beta_{t,h} (total write mass); R_D(L) = D(x_L)/D(x_en), R_W(L) likewise, compared with fertility F(L) =
n_L/n_en. If R_D ~ F the state clock ticks per token (no compensation) and the mechanism has room; if R_D ~ 1
the gates already clock in meaning and the training stage is killed before it starts. Probe (G2 instrument):
K templated facts (entity–value) rendered in language L from one template set, queried in L after d
intervening facts; recall vs content distance d per language, plus token-distance replots; secondary
cross-lingual readout (fact stored in A, queried in B).

**what_is_new.** (1) vs Gated DeltaNet — https://arxiv.org/abs/2412.06464 (2024-12-09, ICLR 2025): GDN gives
input-dependent alpha_t/beta_t per token; the delta is tying both to one content clock supervised by
cross-lingual parity of totals, plus the first measurement of whether learned gates compensate for fertility.
(2) vs Mamba — https://arxiv.org/abs/2312.00752 (2023-12-01): Mamba's selective Delta_t already is a learned
per-token step size; the delta is supervising the step total across translations and reporting a
per-language decay/recall ledger, which Mamba/Mamba-3 never do. (3) vs Titans — https://arxiv.org/abs/2501.00663
(2024-12-31): Titans gates writes by gradient surprise (the rejected family; SR-TTT v2 causality failure); the
delta is a causal feed-forward clock with no loss gradient that modulates decay as well as writes and is
evaluated on translation-paired probes. No direct prior art found through 2026-09-01 under §5 coverage for a
cross-lingually supervised state clock or for per-language decay ledgers on hybrids.

**falsifiable_predictions.**
P1 (phase 0): on qwen3.5-4b GDN layers and mamba-130m-hf, R_D(L)/F(L) lies in [0.85, 1.15] for L in {bn, ta,
th, ja, ko} vs en on FLORES-plus devtest — the gates do not compensate for fertility (embarrassing if R_D is
within 15% of 1.0 while F >= 2).
P2 (baseline 60M 3:1 GDN hybrid): monolingual content-distance recall at d = 32 facts is >= 15 points lower in
the two highest-fertility languages than in English; replotted against token distance the curves collapse
within 5 points.
P3: the meaning-clock parity arm closes >= 50% of the P2 gap with per-language BPB within 0.5% of baseline at
identical parameters and FLOPs; the shuffled-pair placebo closes < 15%.
P4 (pre-registered null): cross-lingual readout (store in A, query in B) stays < 25% for every arm at 60M —
the fixed-size state stores surface form; > 40% for the clock arm would be a surprise worth its own contract.

**kill_conditions.** Phase 0 shows R_D within 15% of 1 (already compensating) — stop before training; parity
arm <= placebo + 5 points at every d; any language's BPB regresses > 1%; an iso-parameter SWA(512)+sinks hybrid
beats both GDN arms by > 10 points at all d (the fix is SWA, not the clock); the two-forward-pass
prefix-invariance audit (2608.22876) localizes leakage in the probe or the clock path.

**cheapest_decisive_pilot.** Phase 0 (~1.5 GPU-h, one H100; mamba-130m on CPU): FLORES-plus devtest (997
sentences x 7 languages) through qwen3.5-4b, mamba-130m-hf, delta-net-1.3b-8k (beta only — W ledger) with
forward hooks; compute D, W, F, R_D, R_W; build the content-distance probe (200 templated facts translated via
General Translation's pipeline with human spot-check, 7 languages) and run it on the same checkpoints. Phase 1
(~14 GPU-h): from-scratch 60M 3:1 GDN hybrid (12 layers = 9 GDN + 3 GQA global, d = 512, fla kernels), 1B
tokens of a fixed 7-language balanced mix with 10% parallel pairs (GT-cleared + OPUS), one 32k byte-BPE with
the `\p{L}+` regex fixed (2608.26449) for all arms. Arms: (a) baseline GDN; (b) meaning clock + L_par; (c)
meaning clock + shuffled-pair placebo; (d) heuristic clock c_t = bytes(token)/mean_bytes (rule-based); 2 seeds
each = 8 runs x ~1.6 GPU-h; (e) SWA(512)+sinks hybrid, 1 seed. Endpoints: per-language BPB; content-distance
recall at d in {8,16,32,64}; R_D/F ledger; paired McNemar on generation exact match. Total ~15.5 GPU-h.

**controls.** Iso-parameter/iso-FLOP GDN baseline; shuffled-pair placebo (same loss, wrong pairs); heuristic
byte clock; SWA+sinks iso-parameter hybrid (2608.28444, mandatory); QED-style query-derived erase if code is
released, otherwise MARCH-style anchors as the recall baseline (2608.13668, 2608.12435 — mandatory for any
recall/interference claim); two-forward-pass prefix-invariance audit (2608.22876); token-distance vs
content-distance replots; generation-based exact match; 2 seeds in the screen, >= 3 in confirmation; FLORES
contamination disclosure (four-field JSON, 2608.29463).

**kevin_advantage.** Parallel data supplies both the parity pairs and the "only the language changes" probe
(templated facts with terminology control through GT's pipeline); 8xH100 for the from-scratch arms; the
harness's exact-match generation and leakage doctors. Phase 0 needs only public FLORES-plus and released
checkpoints — the advantage there is modest and is stated as such.

**collision_risk.** low–medium. hostsearch arXiv `(abs:"linear attention" OR abs:"state space" OR abs:"delta
rule") AND abs:decay AND (abs:multilingual OR abs:"cross-lingual")` -> 0; seq-operators cell `("Gated DeltaNet"
OR "delta rule" OR "state space model") AND (multilingual OR "cross-lingual")` -> 8, none relevant;
benchmarks-eval G2: no translation-paired MQAR/NIAH exists. Risk driver: the delta-rule gate axis is dense
(GDN-2, FG2-GDN, QED, CARVE, Preconditioned DeltaNet), so a content-scaled gate could appear without the
cross-lingual framing; the phase-0 ledger is publishable on its own within weeks.

**monitorability_and_safety.** No CoT or action channel touched. New attack surface: "clock injection" — an
adversarial suffix with large c_t flushes state (accelerated forgetting) or small c_t pins it; pre-register a
c_t clamp and report the c_t distribution under adversarial suffixes. Data rights: FLORES-plus CC-BY-SA-4.0;
GT production pairs need licence clearance and PII scrub; delta-net-1.3b-8k licence unresolved (measurement
only); blt-1b not used.

**negative_result_value.** If R_D ~ 1 on released hybrids, learned gates already clock in meaning — a clean
measurement answering half of G2 and extending 2603.29026 ("parallel data adds little") to state dynamics. If
the fertility recall gap is real but the clock does not move it, the gap comes from write fragmentation and
key interference, redirecting effort to key-side mechanisms (QED/MARCH) rather than decay. The
content-distance probe becomes the G20/G2 instrument either way.

**targets_gaps.** G2, G19, G20.  **pilot_gpu_hours.** 15.5

---

## Candidate B (medium) — `parity-budgeted-mixture-of-depths`

**Claim.** A per-token depth router trained with a parallel-pair compute-parity penalty allocates layers so
that FLOPs per translated sentence are equal across languages; at iso-total-FLOPs this removes most of the
fertility cost premium without per-language quality loss, because the skipped mass is the low-entropy
within-word continuation tokens that inflate fertility (the tokens early layers spend on "detokenization",
Kaplan et al. 2410.05864).

**claim_scope.** architecture-causal.

**Mechanism.** Base transformer, L blocks. Each block l has a causal router r_{t,l} = sigmoid(w_l . h_t^{(l-1)} +
b_l). Training (soft MoD): h_t^{(l)} = h_t^{(l-1)} + r_{t,l} * Block_l(h^{(l-1)})_t. Inference: token t skips block
l when r_{t,l} < tau_l, tau_l set to hit the capacity (MoD-style causal decision). Expected cost per sentence
x: C(x) = sum_{t in x} sum_l r_{t,l} c_l, where c_l is block l's FLOPs per token (attention charged at routed
length). Objective:
  L = L_LM + lambda_b ( Cbar / B - 1 )^2 + lambda_p E_pairs[ ( log C(x_A) - log C(x_B) )^2 ],
with Cbar the batch-mean per-token cost, B the global budget (50% of dense), pairs = aligned translations.
Rule-based control: r_{t,l} = 0 on a fixed skip set for within-word continuation tokens (no word-initial
marker), else 1. Tokenizer-level control: parity-aware BPE (swiss-ai/parity-aware-bpe) with the `\p{L}+`
regex fixed, dense compute. Ledger: rho(L) = mean_pairs C(x_L)/C(x_en); quality: per-language BPB at
iso-total-FLOPs, FLORES en->{de, ja} chrF (generation-based, relative at 60M); "effective depth" = mean sum_l
r_{t,l} for word-initial vs continuation tokens per language. Variable-k experts is the second instantiation
(same penalty on expert FLOPs) once the depth version passes.

**what_is_new.** (1) vs Mixture-of-Depths — https://arxiv.org/abs/2404.02258 (2024-04-02): top-k token routing
under a static global capacity; the delta is a meaning-indexed budget via the parallel-pair parity penalty and
per-language cost/quality reporting, which MoD never gives. (2) vs Gated Recurrent Transformers —
https://arxiv.org/abs/2608.15062 (2026-08-15; beats MoR 2507.10524): adaptive recurrent depth with no
language variable; the delta is the cross-lingual parity objective and the ledger, with GRT/MoR as
mandatory iso-FLOP baselines. (3) vs Multilingual Routing in Mixture-of-Experts —
https://arxiv.org/abs/2510.04694 (2025-10-06, v2 2026-02-17, ICLR 2026): parallel data used to analyze and
steer expert routing at inference (+1–2%); the delta is a training-time parity objective on a
compute-bearing router aimed at cost parity, not accuracy steering. Supporting priors opened: MAGNET
2407.08818 (per-script parity at byte boundaries), Petrov et al. 2305.15425 (NeurIPS 2023; up to 15x token
disparity), Ahia et al. 2305.13707 (overcharged and poorer results), TEA 2608.09046 (Bengali 1.56x GPT-4o
tokens, up to 4.5x on Qwen2.5-7B; cited from the tokenizer-free cell), Shani et al. 2601.07220 (survey: gaps
shrink when segmentation/encoding/exposure are normalized). No direct prior art found through 2026-09-01
under §5 coverage for a language-parity-constrained depth or expert router.

**falsifiable_predictions.**
P1 (phase 0, qwen3-0.6b-base and smollm2-135m on FLORES-plus): within-word continuation tokens are >= 50% of
tokens in bn/ta/th vs <= 25% in en, and their median next-token entropy is <= 0.6 bits vs >= 2.5 bits for
word-initial tokens (embarrassing if continuation entropy >= 1.5 bits — the "wasted compute" premise fails).
P2: at 60M, capacity 50%, PC-MoD lowers rho(bn), rho(ta), rho(th) from the tokenizer fertility ratio (2.0–3.5
under a balanced 32k byte-BPE, to be measured) to <= 1.4 with per-language BPB within 1% of uniform MoD at
iso-total-FLOPs.
P3: the fertility-heuristic router achieves <= 60% of PC-MoD's rho reduction at equal BPB.
P4: on the (macro BPB, max rho) Pareto front, PC-MoD on the base tokenizer is not dominated by parity-BPE +
dense; parity-BPE + PC-MoD reaches rho <= 1.2.

**kill_conditions.** Any language loses > 3% BPB at rho <= 1.4; heuristic router reaches >= 80% of the gain
(preprocessing suffices); parity-BPE dense strictly dominates the Pareto front (the fix belongs in the
tokenizer — a clean answer to the angle's premise); iso-FLOP dense beats every MoD arm by > 2% BPB at 60M and
again at a single 135M rerun (adaptive depth not viable at this scale).

**cheapest_decisive_pilot.** Phase 0 (<= 1 GPU-h): FLORES-plus devtest through qwen3-0.6b-base and
smollm2-135m — per-token entropy by word position and language, fertility per language, plus blt-1b patch
counts per aligned sentence as the byte-level ledger row (CC-BY-NC: measurement only). Phase 1 (~14 GPU-h):
60M (12 layers, d = 512), 1B tokens, 7-language balanced mix + 10% parallel pairs; arms: dense iso-total-FLOP
(narrowed to the 50%-capacity FLOP count), MoD-uniform 50%, PC-MoD 50%, heuristic-skip 50%, parity-BPE dense
(own tokenizer); 2 seeds each = 10 runs x ~1.3–1.5 GPU-h; GRT-style recurrent-depth arm, 1 seed, as the 2026
adaptive-depth baseline. Endpoints: rho(L) ledger; per-language BPB; FLORES en->{de, ja} chrF sanity;
effective-depth histograms by word position. Total ~15 GPU-h.

**controls.** Dense iso-FLOP; MoD-uniform (2404.02258); GRT/MoR recurrent-depth arm (2608.15062, 2507.10524 —
mandatory 2026 adaptive-depth baselines); fertility-heuristic router; parity-aware BPE with the regex fix
(2606.15044, 2608.26449); shuffled-pair placebo for L_par; romanized-input arm (2608.25904) in confirmation;
generation-based evaluation; contamination disclosure; per-language (not macro) reporting.

**kevin_advantage.** Parallel pairs for L_par and the aligned-sentence FLOPs ledger; the repo's fertility
harness (`data/tokens/{model}_fertility.json`) extends directly to FLOPs per aligned sentence; 8xH100; GT's
terminology-heavy domain pairs give a second, production-relevant test set. Honest: the mechanism is
buildable by anyone with FLORES; the paired ledger at volume and the domain test set are the edge.

**collision_risk.** medium. hostsearch arXiv `abs:"mixture of depths" AND abs:multilingual` -> 0;
`abs:fertility AND abs:"language model" AND (abs:"early exit" OR abs:"mixture of depths" OR abs:"adaptive
computation" OR abs:"compute allocation")` -> 0; `abs:"early exit" AND abs:multilingual AND abs:"language
model"` -> 1 (2407.10795, contrastive decoding by skipping language-agnostic layers — not compute);
`abs:equitable AND abs:compute AND abs:languages AND abs:"language model"` -> only tokenizer audits
(2510.12389, 2509.05486, 2606.15044); WebFetch arXiv search `"mixture of depths" multilingual` -> 0 and
`fertility depth languages "language model" adaptive` -> 0; openreview `mixture of depths multilingual` ->
MoD-Attention / MoDification only; hfpapers `multilingual adaptive computation fertility` -> adjacent only
(Duo-LLM 2410.10846, Learning How Hard to Think 2410.04707, Understanding Dynamic Compute Allocation in
Recurrent Transformers 2602.08864 — none per-language); gh repos -> 0. Risk driver: adaptive depth is crowded
(MoR, GRT, MixerLoop, CDB, RouteSparse), so a "language-aware MoD" could appear; the ledger endpoint and the
tokenizer-vs-model comparison are the defensible parts.

**monitorability_and_safety.** No CoT effect. Fairness risk that a cost-parity objective degrades the
languages it targets: per-language non-inferiority (BPB, chrF) is a pre-registered gate, never a macro
average. Data rights: FLORES-plus CC-BY-SA-4.0; blt-1b CC-BY-NC used for measurement only; GT pairs cleared.

**negative_result_value.** Separates "inside the model" from "in the tokenizer" for cost equity on one matched
ledger: if parity-BPE dominates, the field should fix tokenizers (supports 2606.15044); if continuation tokens
are not low-entropy, the premise that fertility is wasted compute is false; the FLOPs-per-aligned-sentence
ledger across dense / MoD / BLT is the G19 measurement regardless of sign.

**targets_gaps.** G19, G20.  **pilot_gpu_hours.** 15

---

## Candidate C (moonshot) — `language-invariant-latent-length`

**Claim.** Insert a learned pool/unpool pair inside a subword LM so the deep trunk runs on K semantic units
per sentence, with K supervised by parallel pairs to be equal across translations (K(x_A) = K(x_B)); trunk
compute per meaning becomes language-invariant by construction and high-fertility languages gain effective
depth because the trunk sees words and phrases instead of fragments. Sharpens dir 18 along Scratchpad
Patching's lesson: constrain the compute count per aligned unit, not boundary positions.

**claim_scope.** architecture-causal.

**Mechanism.** Layers 1..L1 token-level (L1 = 3) -> boundary head p_t = sigmoid(u . h_t^{(L1)}) (token t ends a
unit; causal), hard boundaries by straight-through or Nawrot-style stochastic reparameterization -> unit
states z_j = sum_{t in seg_j} softmax_t(s_t) h_t (or last-token state) -> trunk layers L1+1..L1+L2 (L2 = 6)
causal over z_1..z_K -> unpool: token t in segment j receives u_t = Trunk(z)_{j-1} (shift by one unit to
preserve autoregression, as in dynamic token pooling) added to h_t -> layers L1+L2+1..L token-level (L3 = 3)
-> LM head. Compute: C(x) = n (L1+L3) c_tok + K(x) L2 c_trunk (+ attention at n and at K). Losses:
  L = L_LM + lambda_r ( Kbar_en / nbar_en - r_en )^2 + lambda_p E_pairs[ ( log K(x_A) - log K(x_B) )^2 ]
     (+ optional span-level: | sum_{t in span_A} p_t - sum_{t in span_B} p_t | over frozen aligned spans),
with the compression target anchored only on English (r_en = 1/3); every other language's rate is free and is
pulled to r_en / F(L) by parity. If parity holds, trunk FLOPs per sentence are language-invariant and the
fertility premium is confined to the shallow token layers. Retrofit variant (stretch, separate contract):
freeze qwen3-0.6b-base, insert pool/unpool after layer 4 and before layer 24 with LoRA, Bolmo-stage-1 style.

**what_is_new.** (1) vs Efficient Transformers with Dynamic Token Pooling — https://arxiv.org/abs/2211.09761
(2022-11-17; ACL 2023): pools characters in middle layers with learned/whitespace/entropy boundaries at a
fixed target rate on morphologically diverse languages; the delta is a subword substrate, a per-language free
rate anchored by cross-lingual count parity from parallel pairs, and compute-per-meaning as the endpoint.
(2) vs MrT5 — https://arxiv.org/abs/2410.20771 (2024-10-28): a delete gate in a byte encoder learns
language-specific compression rates emergently; the delta is supervising the rate to equalize units per
meaning rather than per orthography, a decoder-only design with causal unpooling, and parity measured against
translations rather than observed post hoc. (3) vs MAGNET — https://arxiv.org/abs/2407.08818 (2024-07-11):
per-script byte boundary predictors equalize segmentation granularity per script; the delta is parity per
meaning via parallel pairs with no script routing, inside a subword model, with MAGNET-style per-script rates
demoted to a control. Sibling: dir 18 (byte-boundary mass transport; own repo) and When Tokenizers Fail
2608.27658 (monolingual POS/subword-target chunking on a frozen LM; EMNLP 2026) as the supervised-boundary
control; H-Net 2507.07955 ratio-loss chunking as the unsupervised control; Scratchpad Patching 2605.09630 as
the reason the constrained quantity is compute count, not boundary position. No direct prior art found
through 2026-09-01 under §5 coverage for parity-count pooling above a subword tokenizer.

**falsifiable_predictions.**
P1 (phase 0, CPU): with a word aligner (CTFAlign/OmniAlign class, or the repo's UOT doctor on span links)
over FLORES-plus pairs, aligned-unit counts per sentence vary across the 7 languages with CV <= 10% while
token counts vary with CV >= 35%; implied pooling rates r(L) = r_en / F(L) put th/bn at <= 1/8 when r_en = 1/3.
P2: at 60M / 1B tokens, parity-count pooling reaches per-language BPB within 3% of the iso-total-FLOP dense
baseline while the trunk-FLOPs-per-sentence ratio across languages is <= 1.3 (from 2.0–3.5).
P3: unsupervised ratio-loss pooling (H-Net/MrT5-style, no parity) equalizes < 50% of the trunk-cost gap;
MAGNET-style per-script fixed rates equalize cost but lose >= 2% more BPB on the highest-fertility language
than the parity arm (meaning beats script).
P4: FLORES en->{de, ja} greedy chrF (relative) is within 1 point of dense; the unpool shift causes no
exact-match regression on a copy/NIAH probe, and the two-forward-pass prefix-invariance audit finds no
within-segment future leakage.

**kill_conditions.** BPB loss > 5% on any language at ratio <= 1.3; parity arm <= unsupervised pooling on the
ratio (MrT5-style emergent rates suffice — parallel signal unnecessary); per-script control >= parity arm
(script suffices; MAGNET occupies); dense iso-FLOP beats every pooled arm by > 3% BPB at 60M and at a single
135M rerun (pooling not viable at this scale, consistent with the Equity-with-Efficiency BLT negative at 1.5B
— stop); any leakage in the unpool path.

**cheapest_decisive_pilot.** Phase 0: 0 GPU-h (aligner counts and implied rates on CPU; reuse the repo's UOT
doctor for span links). Phase 1 (~14 GPU-h): 60M (L1 = 3, L2 = 6, L3 = 3, d = 512), 1B tokens, 7-language mix
+ 10% pairs, 32k byte-BPE with the regex fix; arms: dense iso-total-FLOP; Nawrot fixed-rate pooling (1/3 for
all languages); H-Net-style ratio-loss free boundaries (no parity); parity-count pooling; MAGNET-style
per-script fixed rates (1/(3 F(script))); 2 seeds each = 10 runs x ~1.4 GPU-h; parity-BPE dense, 1 seed, as
the tokenizer-level alternative. Retrofit onto qwen3-0.6b-base only after passage under a new contract.

**controls.** Dense iso-FLOP; fixed-rate pooling (2211.09761); unsupervised ratio-loss pooling (2507.07955);
MAGNET-style per-script rates (2407.08818); parity-aware BPE with the regex fix (2606.15044, 2608.26449);
shuffled-pair placebo; When-Tokenizers-Fail POS/subword-target boundary arm (2608.27658) in confirmation;
Scratchpad compute-matched framing (trunk compute is the controlled variable); two-forward-pass
prefix-invariance audit (2608.22876) on the unpool shift; per-language copy-task exact match; contamination
disclosure; 2 seeds screen -> >= 3 confirmation.

**kevin_advantage.** Parallel pairs with span alignment and the dir 18 tooling already in the repo (UOT
doctor, named aligners); 8xH100; leakage doctors in the harness. Honest: FLORES alone supports the
sentence-level parity term; GT data adds domain/terminology pairs and the volume for the 10% mix.

**collision_risk.** medium. hostsearch arXiv `(abs:hourglass OR abs:"dynamic pooling" OR abs:"token merging")
AND abs:multilingual AND abs:"language model"` -> 1 unrelated (2407.16607); `abs:"token pooling" AND
abs:"language model"` -> 9, none about middle-layer pooling; WebFetch arXiv search on dynamic token pooling ->
nothing in scope; gh repos `dynamic token pooling transformer` -> 0; the tokenizer-free cell's 41 arXiv queries
found no parallel-supervised dynamic units. Risk drivers: dir 18 itself (own repo — coordinate, do not
duplicate), the Nawrot/Ponti group (a multilingual hourglass would be a natural follow-up), When Tokenizers
Fail's frozen-LM chunking line, and MrT5's language-specific rates.

**monitorability_and_safety.** Pooled units reduce token-level attribution inside the trunk (an
interpretability tax, not a CoT effect); the unpool shift is a leakage risk and gets the causality doctor
before any quality claim. Data rights: FLORES-plus CC-BY-SA-4.0; GT pairs cleared; no CC-BY-NC weights.

**negative_result_value.** Tells dir 18 whether unit-count parity is the right target at all — if pooled
parity loses quality on subwords, boundary-count parity at the byte level will too; if unsupervised rates
already equalize, parallel supervision of dynamic units is unnecessary (extends 2603.29026 to compute
allocation); the aligned-unit-count CV measurement and the trunk-FLOPs ledger are reusable instruments.

**targets_gaps.** G19, G1.  **pilot_gpu_hours.** 14

---

## §4 Sequencing and how the three relate

Run A's phase 0 and B's phase 0 first (both are measurements on pinned checkpoints, ~2.5 GPU-h together);
they produce the G19 ledger (decay-per-meaning, FLOPs-per-aligned-sentence, BLT patches-per-sentence) that all
three candidates and dir 18 need. Fund exactly one 60M screen next, chosen by phase-0 sign: if R_D ~ F (gates
tick per token) -> A; if continuation-token entropy is low and fertility high -> B; C only after either A or B
passes, because it is the most expensive to get right (leakage audit) and shares the parity term. All three
share one tokenizer, one 7-language mix, one parallel-pair set and one ledger script, so controls are reused.

## §5 Searches run (this note) and coverage limits

hostsearch (12 calls, 4 s spacing, 2026-09-01): arxiv `abs:"mixture of depths" AND abs:multilingual` (0);
arxiv `abs:"token pooling" AND abs:"language model"` (9, none in scope); arxiv `abs:fertility AND abs:"language
model" AND (abs:"early exit" OR abs:"mixture of depths" OR abs:"adaptive computation" OR abs:"compute
allocation")` (0); arxiv `(abs:"linear attention" OR abs:"state space" OR abs:"delta rule") AND abs:decay AND
(abs:multilingual OR abs:"cross-lingual")` (0); arxiv `abs:"information density" AND abs:multilingual AND
(abs:compute OR abs:"inference cost" OR abs:"language model")` (3; 2601.07220 opened); arxiv `(abs:hourglass OR
abs:"dynamic pooling" OR abs:"token merging") AND abs:multilingual AND abs:"language model"` (1 unrelated); ddg
x2 (empty returns — likely CAPTCHA); hfpapers `multilingual adaptive computation fertility` (20, adjacent only);
openreview `mixture of depths multilingual` (10, none multilingual); arxiv `abs:equitable AND abs:compute AND
abs:languages AND abs:"language model"` (25, audits only); arxiv `abs:"early exit" AND abs:multilingual AND
abs:"language model"` (1). WebFetch arXiv search UI: 3 queries (all 0 in scope). gh search repos x3 (0), gh
search code x1 (notes only). Abstracts opened with WebFetch (22): 2404.02258, 2608.15062, 2510.04694,
2412.06464, 2312.00752, 2501.00663, 2211.09761, 2507.07955, 2407.08818, 2410.20771, 2605.09630, 2305.15425,
2601.07220, 2602.08864, 2407.10795, 2410.04707, 2305.13707, 2507.10524, 2410.05864, 2603.29026, 2608.13668,
2608.28444. Cited from cell notes without re-opening: 2608.09046, 2608.26449, 2606.15044, 2608.27658,
2608.22876, 2608.12435, 2608.25904, 2608.29463, 2608.28151.

Limits: arXiv `abs:` matching is exact-phrase; paraphrased titles ("adaptive depth", "layer skipping",
"conditional computation") were covered only through the fertility/multilingual conjunctions; no Semantic
Scholar, Google Scholar, ACL Anthology or OpenReview full search; DuckDuckGo returned nothing (CAPTCHA
likely); WebSearch budget exhausted for the session; grey literature after 2026-08-10 under-covered; no code
executed; all GPU-hour figures are estimates at an assumed 55 TFLOPS effective per H100 for 60M-class models
and must be re-measured in the first run; peer-review status taken from abstract pages only.
