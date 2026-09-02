# Inventor H — cross-domain import (2026-09-01)

Angle: wildcard import from control theory, coding/information theory, distributed systems, compilers, or
neuroscience that has no LM analog yet, testable at <= 135M parameters.

Inputs read in order: `context.md`, `design/brief.md`, `sweep/synthesis.md` (all 1,456 lines: occupied map A–Y,
gaps G1–G22, kill-shot verdicts), then `sweep/ttt-fastweights.md`, `sweep/seq-operators.md`,
`sweep/killshot-current.md`, plus grep of every cell note for my domain keywords, the repo's
`research/frontier-systems-program-2026-08-10.md` occupied/rejected tables and `models/registry.yaml`.

Honesty rules applied: no "completely novel" anywhere; every gap statement reads "no direct prior art found
through 2026-09-01 under the coverage in §5"; first-party vs peer-reviewed status is stated per prior; every
prior below was opened at arxiv.org/abs (or GitHub) in this session unless marked "not opened".

## 0. Three candidates (one line each)

| # | slug | domain imported | scope | role | GPU-h |
|---|---|---|---|---|---|
| C1 | `coded-provenance-shadow-state` | coding theory (superimposed codes / compressed-sensing sketches) + forward sensitivity | attachment-capability | cheap-decisive | 3 |
| C2 | `contraction-certified-fast-weights` | control theory (contraction analysis, incremental ISS, sigma-modification) | architecture-causal | medium | 14 |
| C3 | `tag-and-capture-delta-memory` | neuroscience (synaptic tagging & capture; three-factor rules) | architecture-causal | moonshot | 15 |

Imports considered and dropped (with the collision that killed them): CRDT / join-semilattice merge of
independently prefilled recurrent states → PICASO (ICLR 2025, https://arxiv.org/abs/2502.17605, 2025-02-24)
already composes SSM states of retrieved contexts permutation-invariantly; write-back "spill-on-overwrite"
exact store for displaced delta-rule content → the interference-control axis is occupied (QED 2608.13668,
MARCH 2608.12435, SWA+sinks 2608.28444) and MARCH's anchor bank is the near neighbour; anti-windup
(back-calculation) for integrator channels vs SANE's tanh clamp → an incremental stabiliser on axis C, which
the synthesis marks "closed for one more gate"; exact per-write deletion by propagated-key audit vectors →
already a published negative (2607.27539: 12–49% drift because downstream keys change); adaptive-control
persistent-excitation / bursting diagnosis of TTT divergence → folded into C2's Phase 1 as telemetry rather
than a separate candidate; theta–gamma phase coding for ordered recall → collides with complex/rotational
decay (Semidirect Fourier Delta Attention 2607.11897, RetNet/xPos); Coded Delta Memory → rejected by the brief.

---

## 1. C1 — `coded-provenance-shadow-state` (cheap-decisive)

**Claim.** For every sequence operator whose recurrent state is linear in the value stream (DeltaNet, Gated
DeltaNet, KDA, Mamba-2/SSD, Mamba-1, RetNet), a training-free auxiliary "shadow state" driven by the
operator's own keys and gates but fed random ±1 *segment fingerprints* instead of values returns, at every
read position, an exact random-code sketch of that read's implicit attention row. Decoding the sketch gives
streaming, O(m·d_k)-per-token, per-segment (or per-token) attribution for recurrent layers — the missing
"attention map" for linear-attention/SSM layers — exact for up to m segments and sparse-recoverable beyond,
on released checkpoints without any training.

**claim_scope.** attachment-capability.

**Mechanism.** Gated delta-rule head: S_t = a_t * S_{t-1} (I - b_t k_t k_t^T) + b_t v_t k_t^T, read
o_t = S_t q_t. Because the recurrence is linear in v, S_t = sum_{j<=t} b_j v_j r_j(t)^T with the vector
recurrence r_j(t) = a_t (I - b_t k_t k_t^T) r_j(t-1), r_j(j) = k_j (the matrices (I - b k k^T) are
symmetric, so the right factor propagates as a vector). Hence o_t = sum_j A_tj v_j with the implicit
attention row A_tj = b_j r_j(t)^T q_t. Define the shadow state P_t in R^{m x d_k} by the same recurrence
with values replaced by codes: P_t = a_t * P_{t-1} (I - b_t k_t k_t^T) + b_t f_{g(t)} k_t^T, where g(t) in
{1..n} is the segment id of token t and F = [f_1 ... f_n] in {+-1/sqrt(m)}^{m x n} is a fixed random code
(Bernoulli). Then P_t q_t = sum_j A_tj f_{g(j)} = F u_t, where u_t in R^n, u_t[s] = sum_{j in s} A_tj, is the
per-segment attribution vector — exact by the same linearity, at O(m d_k) per token per head. Decode: if
n <= m and F has full column rank, u_t = F^+ (P_t q_t) exactly; if n >> m, u_t is recovered by OMP/LASSO,
with exact recovery of s-sparse u_t guaranteed when m >= C s log(n/s) (restricted isometry, Bernoulli
matrices w.h.p.; Candes & Tao 2005, https://arxiv.org/abs/math/0502327, classical, not re-opened). Token
level: g(t) = t, n = T — a streaming count-sketch of the whole implicit-attention row. Mamba-2/SSD: identical
(state linear in x). Mamba-1 per channel c: P_t[c] = A_t[c] (.) P_{t-1}[c] + B_t f_{g(t)}^T (N x m per
channel), read C_t^T P_t[c]. Nonlinear fast weights (TTT-MLP, E2-TTT-swiglu) are *not* linear in v, so the
identity fails there; forward-mode JVP seeds give an approximate analogue (out of scope, stated as a limit).
The coding-theory content is the compression: one-hot indicators (m = n) give exact attribution trivially;
random codes give m << n with recovery guarantees and let the same shadow attribute to 4,096 sentences or
every token with m = 64.

**what_is_new (delta vs three closest priors).**
1. Zimerman, Ali & Wolf, "A Unified Implicit Attention Formulation for Gated-Linear Recurrent Sequence
   Models" — https://arxiv.org/abs/2405.16504 — 2024-05-26 — arXiv (venue not stated on abs page;
   abstract-level read): computes full implicit attention matrices for Mamba/RWKV/gated RNNs offline for
   attribution. Delta: we compute a random-code *sketch* of the same row in streaming O(m d_k) per token, exact
   for <= m segments and sparse-recoverable beyond, extended to erase-type delta-rule operators (GDN/KDA/
   DeltaNet), and we validate it against a leave-one-out causal oracle and across translations.
2. Ali, Zimerman & Wolf, "The Hidden Attention of Mamba Models" — https://arxiv.org/abs/2403.01590 —
   2024-03-03 — arXiv (abstract-level): attention view of Mamba used for explainability. Delta: Mamba-only and
   offline there; operator-agnostic, streaming, provenance-decodable here, evaluated on 2026 3:1 hybrids.
3. Pitorro & Treviso, "LaTIM: Measuring Latent Token-to-Token Interactions in Mamba Models" —
   https://arxiv.org/abs/2502.15612 — 2025-02-21 — arXiv (abstract-level; PDF not read): token-level
   decomposition for Mamba-1/2 evaluated on MT, copying, retrieval-based generation — the closest in purpose.
   Delta: LaTIM is a per-model decomposition without a streaming sketch, code-based compression, or delta-rule
   coverage; ours adds segment/document provenance with recovery guarantees, causal-faithfulness measurement
   (leave-one-out), and the translation-paired invariance probe.
Also positioned against: Bhattacharya, "An Exact Instrument for State Usage in Selective SSMs"
(https://arxiv.org/abs/2607.11796, v1 2026-07-13, v2 2026-08-11; per-(layer, channel, window) *mode* usage
via Gram tensors — attributes to state modes, not to past sources); TwinKV
(https://arxiv.org/abs/2608.27128, 2026-08-27; leave-one-out probe, attention magnitude vs causal
contribution Spearman rho = -0.004 in KV caches — our faithfulness comparator); PICASO
(https://arxiv.org/abs/2502.17605, ICLR 2025; state composition, no attribution); FlashTrace
(https://arxiv.org/abs/2602.01914, ICML 2026 Oral; transformer multi-token attribution); "The Mask Is Not
the Model" prefix-invariance audit (https://arxiv.org/abs/2608.22876, 2026-08-24) as the mandatory doctor.

**falsifiable_predictions.**
- P1 (exactness, embarrassing if wrong): on the GDN layers of `qwen3.5-4b` with n = 16 passages and m = 64,
  the decoded u_t equals the O(T^2) implicit-attention aggregation to relative error < 1e-3 (fp32) at 100% of
  read positions; with n = 1,024 sentence segments and m = 64, OMP recovers the top-5 support at >= 90% of
  read positions whose true row carries >= 80% of its mass in its top 5.
- P2 (mechanism): at answer positions of 32-passage QA, >= 50% of recurrent heads in the top third of layers
  have concentrated rows (top-5 mass >= 0.5), and aggregated recurrent-layer attribution identifies the gold
  passage top-1 >= 60% on correctly answered items (chance 3.1%).
- P3 (faithfulness): Spearman rho between recurrent-layer attribution mass and leave-one-out passage-removal
  effect >= 0.5 (TwinKV reports rho = -0.004 for softmax attention magnitude in transformers).
- P4 (cross-lingual, Kevin's asset): with the passages translated and content held fixed, the Jensen–Shannon
  divergence between attribution distributions over passages is < 0.1 for en<->de/fr and >= 2x larger for
  en<->th/hi (abugida fertility gap, 2608.26449), i.e., recurrent reads track surface when fertility differs.

**kill_conditions.** Median top-5 mass < 0.2 in every recurrent layer of all three families → recurrent
layers do not perform source-selective recall (instrument exact but uninformative; publish as mechanistic
support for 2606.15378 "retrieval is carried by full attention"). rho < 0.2 against leave-one-out → exact
linear contribution is not causal effect (kills the instrument's faithfulness claim). Support recovery
< 50% because rows are incompressible → restrict to the n <= m regime.

**cheapest_decisive_pilot.** Phase 0 (CPU, NumPy fp64, ~1 h): synthetic GDN recurrence with random keys and
gates; assert P_t q_t = F u_t to 1e-12 under erase and decay; RIP recovery curves over m in {16,32,64,128},
n in {64..4096}, sparsity s in {1..16}; adversarial correlated-key streams. Phase 1 (frozen checkpoints,
<= 3 GPU-h on 8xH100): `qwen3.5-4b` (registry; GDN hybrid), `mamba-130m-hf` (registry; Mamba-1),
`delta-net-1.3b-8k` (registry; pure DeltaNet), `kimi-linear-48b-a3b-base` (registry; KDA, 2 GPUs bf16), plus
`startlux-models/gdn-1.3b-isp-hybrid-3to1-50b` (open control, 2026-08-13). Tasks: 16/32/64-passage
distractor QA with one gold passage; the same items with passages machine-translated (FLORES-style or GT
parallel sets under licence); leave-one-out oracle on 200 items (n forward passes each). Hooks read
(a_t, b_t, k_t, q_t) from the fla kernels' inputs.

**controls.** O(T^2) implicit attention (2405.16504) as the exact oracle; LaTIM decomposition
(2502.15612); input x gradient and integrated gradients; softmax attention mass in the same hybrid's global
layers; a linear probe for passage identity trained on the readout (must be beaten with zero supervision);
leave-one-out causal oracle (TwinKV protocol); two-forward-pass prefix-invariance audit (2608.22876) as
doctor; SWA+sinks hybrids (2608.28444) as a model-family control. This is not a recall claim, so QED/MARCH
are cited as neighbours rather than arms.

**kevin_advantage.** Parallel translation data makes P4 buildable — the content-fixed cross-lingual attribution
probe is exactly the "language as a controlled variable inside architecture" region the synthesis found
empty (G2, G13); pinned registry checkpoints and the deterministic-replay harness run the leave-one-out
oracle. The instrument itself needs none of Kevin's assets (honest).

**collision_risk.** medium-low. Searches run: relay arXiv Q5 (implicit/hidden attention x Mamba/SSM/linear
attention → 4 unrelated), Q7 (SSM/linear-attention x attribution/provenance → 2607.11796 per-mode instrument,
2606.00926 layerwise probing; nothing per-source), Q6 HF papers (→ PICASO, attribution surveys), Q8 DDG
(empty), local HF papers ("implicit attention attribution SSM" → 2405.16504, 2403.01590, 2502.15612;
"streaming attribution linear attention" → transformer-only methods), `gh search repos` (0). No streaming or
code-sketched per-source attribution for delta-rule/KDA/SSM operators found through 2026-09-01 under this
coverage.

**monitorability_and_safety.** Strictly increases monitorability: a per-read provenance channel for recurrent
layers, where attention maps do not exist; enables poison-source attribution in hybrids (attribution, not
defence — 2608.21230 shows provenance *screening* does not defend). No effect on CoT. Data rights: public QA
sets and FLORES; General Translation parallel data only under its licence terms, customer data excluded.

**negative_result_value.** Diffuse rows → mechanistic evidence that 3:1 hybrids' recurrent layers do not do
source-selective recall (sharpens 2606.15378 and the K3/Qwen3.8 design rationale). Unfaithful rows → even
exactly linear reads are not causal effects, a caution for the whole implicit-attention interpretability
line. Either way, the sketch identity and its doctor remain as harness instruments for G2/G13.

**pilot_gpu_hours.** 3. **targets_gaps.** G2, G13, G20.

---

## 2. C2 — `contraction-certified-fast-weights` (medium; identifiability screen included)

**Claim.** Fast-weight layers (delta-rule and nonlinear TTT-MLP) can be built or instrumented so that the
per-token state map is a certified contraction (incremental input-to-state stability). The certificate is a
computable upper bound on the residual influence of any single write — a deletion/poison horizon that paired
replay must respect — and it is informative (within 10x of measured drift) at a within-horizon recall cost
under 3 points.

**claim_scope.** architecture-causal.

**Mechanism.** Fast weights W_t (matrix or MLP parameters) update as W_t = Phi_t(W_{t-1}) with
Phi_t(W) = W - eta_t * grad_W L(W; k_t, v_t) - sigma_t * (W - Wbar), L = ||f_W(k_t) - v_t||^2, Wbar the slow
anchor (initial fast weights), sigma_t in [sigma_min, 1) the leakage (sigma-modification of robust adaptive
control; Ioannou & Kokotovic 1983, classical, not re-opened), eta_t = eta / (eps + ||k_t||^2) the normalised
step (NLMS; identical to Falcon-1). Linear f_W recovers the gated delta rule with decay (1 - sigma_t).
Per-step contraction factor: q_t = ||d Phi_t / d W||_2 = ||(1 - sigma_t) I - eta_t H_t||_2, H_t the Hessian of
L at W_{t-1}. Linear case: H_t = k_t k_t^T (x) I, so q_t <= 1 - sigma_t whenever eta_t ||k_t||^2 <= 2(1 -
sigma_t) — the known contractive regime of decayed delta rules. Nonlinear case: with H_t eigenvalues in
[-lam_minus, lam_plus], q_t = max(1 - sigma_t + eta_t lam_minus, |1 - sigma_t - eta_t lam_plus|), so
contraction needs eta_t lam_minus < sigma_t. Two routes: (a) *design certificate* — bound lam_minus a priori
with Lipschitz-bounded fast-weight networks (spectrally normalised layers or a REN-style direct
parameterisation, Revay et al. 2104.05942) and a step cap; (b) *runtime certificate* — estimate lam_minus,
lam_plus per step with 3–5 power iterations on Hessian-vector products (cheap relative to the TTT gradient)
and log q_t. Theorem used (contraction analysis, Lohmiller & Slotine 1998, classical, not re-opened;
incremental ISS => fading memory, Bainier et al. https://arxiv.org/abs/2603.23814, 2026-03-25): for two runs
identical except a perturbation Delta W_s at time s (a write, a poisoned token) and the same later inputs,
||W_t - W'_t|| <= (prod_{r=s+1..t} q_r) ||Delta W_s|| <= (1 - sigma_min)^{t-s} ||Delta W_s||, and the output
influence is at most L_read times that; the eps-deletion horizon is n_eps = ln(||Delta W_s|| / eps) /
sigma_min. Honest scope: the bound is open-loop (later keys held fixed). Closed-loop drift — later hidden
states change because the model *read* the perturbed state — is measured by paired replay, not certified;
"open-loop dominates" is an empirical prediction (P2) and its failure is a kill condition.

**what_is_new (delta vs three closest priors).**
1. Zubic & Scaramuzza, "Regularity and Stability Properties of Selective SSMs with Discontinuous Gating" —
   https://arxiv.org/abs/2505.11602 — v1 2025-05-16, revised 2026-07-07 — TMLR 2026 (peer-reviewed): ISS
   bounds, exponential forgetting and a training-time LMI regulariser for the *trained* selective-SSM
   recurrence. Delta: we certify the *test-time fast-weight inner loop* (nonlinear TTT-MLP included) per
   realised step, and convert the certificate into per-write deletion/poison influence bounds checked by
   paired replay.
2. momentwo — https://github.com/v-code01/momentwo — 2026-07-22 — unreviewed, 0 stars, fp64 proof: exact
   second-order recurrence for Titans' delta rule with momentum and the ceiling theta*c < (1 + eta)(2 -
   alpha)/2, single fixed key, linear memory only ("deep-MLP memory" named as future work). Delta: multi-key
   streams and nonlinear fast weights via a runtime/design contraction certificate; target is influence
   bounds, not learning-rate ceilings.
3. Ramesh, "Subtract, Transport, or Replay? Auditable Deletion from Language-Model Memory" —
   https://arxiv.org/abs/2607.27539 — v1 2026-07-30, v2 2026-08-13 — arXiv, single author: native KDA
   deletion receipts fail ("the corpus-pooled raw recurrent contribution changes by 12-49% with the suffix and
   remains 8-49% after a decay-ledger correction"); only checkpoint replay verifies. Delta: we do not claim
   exact subtraction; we claim a certified *upper bound* with a horizon and test whether replay-measured drift
   respects it, turning the negative into a bounded-forgetting result in either direction.
Also positioned against: SANE (https://arxiv.org/abs/2608.22354, 2026-08-23; tanh compression, 3 <= alpha
<= 5, 100M-token prefix, "capacity–stability trade-off", no formal guarantee stated); Falcon rules
(https://arxiv.org/abs/2608.27763, 2026-08-27; normalised NLMS updates, read-after-write semantics, no
stability certificate stated); LaCET (https://arxiv.org/abs/2604.07350, 2026-04-08; EWC anchor); In-Place
TTT issue #7 (paper tau = 1e-5 clipping absent from code; ||F z||/||W z|| reached 62.5; NLL 1.86 → 10.81);
E2-TTT (https://arxiv.org/abs/2608.21308, 2026-08-21; exact chunk-end dynamics, no causality or stability
telemetry); StableSSM (https://arxiv.org/abs/2311.14495, ICML 2024; slow-weight reparameterisation);
Controller Design for SSMs via Contraction Theory (https://arxiv.org/abs/2604.07069, ECC 2026; slow weights,
no LM).

**falsifiable_predictions.**
- P1 (tightness): median ratio (replay-measured open-loop drift) / (certified bound) >= 0.1 at 1K tokens after
  a single-write injection on a 125M certified TTT-MLP hybrid — the bound is informative within 10x.
- P2 (closed loop): 95th percentile of (closed-loop drift) / (open-loop drift) < 2 over 1,000 injections; if
  the median exceeds 10 the certificate is behaviourally vacuous.
- P3 (stability): 0 divergence episodes (||F_prefix z|| / ||W z|| > 10, the In-Place TTT issue #7 statistic)
  in 100M streamed tokens for the certified arm vs >= 1 per 10M tokens for the matched unconstrained TTT-MLP at
  equal learning rate.
- P4 (cost): LM loss within 0.02 nats and S-NIAH-1 within-horizon recall within 3 points of the unconstrained
  arm at 125M / 5B tokens; beyond the horizon recall decays at a rate within 2x of the certified rate.
- P5 (poison): an instruction injected into a tool-result segment has downstream KL < 1e-3 nats after n_eps
  tokens in >= 90% of cases (certified) vs > 1e-2 nats in >= 50% of cases (unconstrained).

**kill_conditions.** P2 median ratio > 10 → certificate uninformative about behaviour (publish: persistence
of context-borne influence lives in the residual stream/keys, not in fast weights). A useful horizon
(>= 4K tokens) forces sigma_min so small that P5 separation vanishes → the Pareto curve has no certified
region worth having. Unconstrained arm shows 0 divergence and no recall gap → stability motivation moot
(still reportable as "certified at zero cost", but not as a fix).

**cheapest_decisive_pilot.** Phase 0 (CPU, fp64 NumPy, ~2 h): linear and 2-layer-MLP fast weights on
synthetic key/value streams; verify the bound inequality against exact replay in 1e4 trials; exhibit
counterexamples where Frobenius clipping (In-Place), tanh compression (SANE) and EWC anchoring (LaCET) admit
drift above any bound they imply; tightness curves vs sigma. Phase 1 (frozen-checkpoint screen, <= 2 GPU-h):
`zeyun-zhong/e2-ttt-swiglu-340M-15B` and `e2-ttt-mlp-340M-15B` (HF, 2026-08-30) on held-out text; estimate
q_t per step via HVP power iteration; report the fraction of non-contractive steps and its correlation with
norm-ratio spikes and with low key-excitation windows (the adaptive-control "bursting" diagnosis). Phase 2
(from scratch, <= 12 GPU-h): 125M 3:1 hybrids, 3 arms x 3 seeds (unconstrained TTT-MLP, certified TTT-MLP,
GDN control), 5B FineWeb-Edu tokens, SWA 512 / chunk 512 (E2-TTT recipe scaled down); probes: S-NIAH-1 to
8x training length with needles outside the window, paired-replay injections, poison segments, divergence
telemetry, SR-TTT causality self-tests. Total ~14 GPU-h.

**controls.** Unconstrained TTT-MLP (E2-TTT recipe); GDN with KDA-style lower-bounded decay (the already
contractive linear case); SANE tanh; LaCET EWC anchor; In-Place clipping tau; Falcon-1 NLMS without leakage;
SWA+sinks (2608.28444, mandatory); QED and MARCH for any recall number; two-forward-pass prefix-invariance
audit (2608.22876); SR-TTT startup causality self-tests (2603.06642v2); Beyond Perplexity D-level battery
(2607.00368); 3 seeds with paired clustered SEs.

**kevin_advantage.** The harness's deterministic replay and hash-chained logs *are* the certificate's
validation oracle; the fp64 CPU oracle pattern already exists; E2-TTT checkpoints are pinned-able; parallel
data adds an optional cross-lingual poison-persistence probe (poison written in language A, reads in B — G2).
Moderate: Phase 1 is doable by any lab with one GPU.

**collision_risk.** medium. Searches run: relay arXiv Q1 (TTT/fast weights x contraction/ISS/Lyapunov → 0
relevant), Q2 (linear attention/delta rule/SSM x contraction/ISS → only slow-weight SSM theory: 2604.07069,
2603.23814, 2505.11602, 2505.03069 BiLipREN, 2605.13473 OSDN), Q9 (persistent excitation x TTT/LM → 0), Q12
(certified forgetting/unlearning x recurrent/fast weights/TTT → 0 relevant), Q11 OpenReview (forums returned
without titles; API redirects to a browser challenge — not resolvable), local HF papers ("contraction
stability certificate test-time training" → certified-training papers only), `gh` (0). Control theorists are
visibly moving onto SSMs in 2026 (three of the Q2 hits), hence medium rather than low.

**monitorability_and_safety.** No CoT effect. Adds a logged per-step certificate (a monitorable stability
channel) and a bounded-persistence property for context-borne poison — a safety positive — at the price of
forced forgetting beyond the horizon (by design). Data rights: public corpora only.

**negative_result_value.** If certificates are behaviourally vacuous, that reframes fast-weight poisoning:
persistence is carried by the residual stream rather than the memory, so fast-weight-level defences cannot
work. If the certificate costs too much recall, it quantifies the capacity–stability trade-off that SANE only
names. If unconstrained layers never diverge at 125M, it bounds how much of the In-Place TTT collapse reports
is scale- or recipe-specific.

**pilot_gpu_hours.** 14. **targets_gaps.** G7, G8, G6.

---

## 3. C3 — `tag-and-capture-delta-memory` (moonshot)

**Claim.** A two-store delta-rule state in which every write lands in a fast-decaying *tag* store and is
transferred to a long-retention store only by a later, sparse, scalar *capture* signal (synaptic tagging and
capture; three-factor neuromodulated plasticity) gives retroactive selection of what persists: higher
long-range recall of items followed by a capture event, certified bounded persistence of uncaptured content
(a poison horizon), and an explicit monitorable consolidation channel — at LM-loss parity with GDN at 125M.

**claim_scope.** architecture-causal.

**Mechanism.** Per head, two matrices S_tag, S_slow in R^{d_v x d_k}. Tag write (delta rule with fast decay
rho = exp(-1/tau), tau in [128, 2048], learned per head within bounds):
S_tag_t = rho * S_tag_{t-1} (I - b_t k_t k_t^T) + b_t v_t k_t^T. Capture (third factor): a scalar
c_t = sigmoid(w_c^T h_t + b_c) in [0, 1] per (layer, head), computed from the current hidden state, with a
budget sum_{t in window W} c_t <= B enforced by an L1 penalty (or hard top-B per window). Transfer:
S_slow_t = alpha_t * S_slow_{t-1} + c_t * S_tag_t ;  S_tag_t <- (1 - c_t) * S_tag_t. Read:
o_t = (S_slow_t + S_tag_t) q_t (optionally separate output gates). Properties: (i) certificate — a write at
time s that is never captured has residual at most rho^{t-s} * b_s ||v_s|| ||k_s|| in S_tag and exactly 0 in
S_slow; (ii) retroactivity — content written in the last ~tau tokens is consolidated by an event *after* it
(the neuroscience prediction "behavioural tagging": a salient event rescues weak memories nearby in time);
(iii) monitorability — c_t is a logged scalar per head per token. Chunkwise form: [S_slow; S_tag] follows a
block-upper-triangular linear recurrence with token-dependent coefficients; S_slow_t = sum_{s<=t}
(prod_{r=s+1..t} alpha_r) c_s S_tag_s is a gated cumulative sum of a GDN-type state — the same algebra as the
momentum accumulator whose exact chunk-end form E2-TTT derives — so WY-style chunk kernels exist; at 125M a
PyTorch chunk-16 reference suffices. Why the "surprise-gated memory" rejection does not apply: the gate acts
at *capture* time on a later global signal (three-factor rule), not at write time on prediction error; the
SR-TTT failure was an evaluation-causality failure that the mandatory doctors pre-empt; Titans-style
surprise gating is a mandatory control arm, not the proposal. Neuroscience sources: Frey & Morris 1997
(synaptic tagging), Moncada & Viola 2007 (behavioural tagging), Fremaux & Gerstner 2015 and Gerstner et al.
2018 (three-factor rules, eligibility traces) — classical, not opened this session; Backpropamine's reference
list (read) cites the same lineage.

**what_is_new (delta vs three closest priors).**
1. Miconi, Rawal, Clune & Stanley, "Backpropamine: training self-modifying neural networks with
   differentiable neuromodulated plasticity" — https://arxiv.org/abs/2002.10585 — arXiv 2020-02-24; ICLR 2019
   (peer-reviewed; PDF read): Section 3.2.2 defines retroactive neuromodulation with eligibility traces,
   Hebb(t+1) = Clip(Hebb(t) + M(t) E(t)), E(t+1) = (1 - eta) E(t) + eta x_i(t-1) x_j(t); PTB test perplexity
   104.26 (baseline LSTM) → 102.48 (retroactive), 4.8M parameters, 16 runs; large 24.2M model 62.48 → 61.44
   (simple modulation only). Delta: the trace lives inside a normalised-key *delta-rule* associative state
   (erase, not clipped Hebbian outer products) in a 3:1 GDN hybrid at >= 125M with a chunk-parallel form, a
   capture budget, a certified persistence bound, and evaluation on recall / poison / monitorability rather
   than perplexity alone.
2. Behrouz, Zhong & Mirrokni, "Titans: Learning to Memorize at Test Time" — https://arxiv.org/abs/2501.00663
   — 2024-12-31 — NeurIPS 2025 per the ttt-fastweights cell's search record (abs page does not state venue):
   surprise-driven gradient writes with momentum and forgetting — the decision is made at write time. Delta:
   retroactive capture by a later signal, with the uncaptured store certified to decay; Titans-style gating is
   our control.
3. Trappe, "Phasor Agents: Oscillatory Graphs with Three-Factor Plasticity and Sleep-Staged Learning" —
   https://arxiv.org/abs/2601.04362 — 2026-01-07 — arXiv, single author: eligibility traces gated by sparse
   global modulators with sleep-staged consolidation in oscillator graphs (agent level, no language model,
   no scale stated). Delta: an LM sequence-operator instantiation trained with the LM loss on hybrid kernels
   and evaluated with the 2026 memory protocol.
Also positioned against: Mela (https://arxiv.org/abs/2605.10537, 2026-05-11; two update frequencies blended
by a context-dependent combination, no gated transfer, no retroactive trigger); Nested Learning / HOPE
continuum memory system (https://arxiv.org/abs/2512.24695, NeurIPS 2025; multi-frequency updates, no
retroactive gate in the abstract, no code); Adaptive Memory Crystallization (https://arxiv.org/abs/2604.13085,
2026-04-02; STC-*inspired* agent-harness store for continual RL, no operator); Hindsight Memory-PRM
(https://arxiv.org/abs/2608.29605, 2026-08-30; harness-level retroactive credit at answer time); Irie &
Gershman FWP–neurobiology primer (https://arxiv.org/abs/2508.08435, TMLR 2025; abstract does not mention a
retroactive LM-scale implementation); SleepGate (https://arxiv.org/abs/2603.14517, 2026-03-15; KV-level).

**falsifiable_predictions.**
- P1 (behavioural tagging, the signature): in an MQAR variant with capture events (a query about *any* key),
  items written within tau before a capture event are recalled at 8K delay with >= 30 points higher accuracy
  than matched items with no nearby capture; a two-rate GDN (fast + slow heads, no transfer) shows < 5 points
  difference.
- P2 (parity): LM loss within 0.01 nats of GDN at 125M / 5B tokens at iso-parameters (the second matrix
  costs state memory and ~1.5x recurrent compute, no parameters).
- P3 (recall/poison Pareto): at equal state bytes, S-NIAH-1 at 4x training length improves by >= 5 points when
  the needle is followed within tau by a natural capture (a question), and paired-replay influence of an
  uncaptured injected instruction measured 4K tokens after injection is >= 3x lower than GDN.
- P4 (monitorability, Kevin's asset): logged c_t predicts which context items are later recalled with
  AUC >= 0.75 (random gate 0.5); on parallel documents the per-sentence capture mass aligns across
  translations with Spearman >= 0.6 (consolidation is translation-equivariant), or the failure localises to
  high-fertility scripts.

**kill_conditions.** c_t collapses to a constant (entropy < 0.1 bits or budget always saturated) under LM
loss despite the penalty → the operator degenerates into two-rate GDN. Two-rate GDN matches P1/P3 → the
transfer has no value beyond multi-timescale decay. Titans-style write-time surprise gating matches P3 →
retroactivity adds nothing. Recall cost > 3 points at matched bytes on standard S-NIAH.

**cheapest_decisive_pilot.** Phase 0 (CPU, fp64, ~3 h): linear two-store dynamics; verify the persistence
bound; capacity analysis (captured items S_slow holds before interference) vs single-store GDN at equal d;
behavioural-tagging synthetic with an oracle capture policy (upper bound) and a learned linear gate
(identifiability). Phase 1 (GPU, <= 15 GPU-h): 20M MQAR-capture screens (minutes each) for identifiability,
then 125M 3:1 hybrids (12 layers: 9 recurrent + 3 global), 5B FineWeb-Edu tokens plus a synthetic
tool-result/question mixture; arms GDN, two-rate GDN, Titans-style surprise-gated GDN, tag-and-capture;
3 seeds; probes as above with generation exact match and paired McNemar.

**controls.** GDN single-rate (iso-parameter); GDN two-rate heads (iso-parameter); Titans/MIRAS surprise gate
(write time); KDA lower-bounded decay; QED (2608.13668), MARCH (2608.12435), SWA+sinks (2608.28444) —
mandatory 2026 recall/interference baselines; Hindsight Memory-PRM as a conceptual harness comparator, not an
arm; doctors: SR-TTT self-tests, prefix-invariance audit (2608.22876), Beyond Perplexity D-level battery; an
adversarial capture-trigger attack arm.

**kevin_advantage.** Parallel translation data gives the content-fixed cross-lingual capture probe (P4) and an
optional translation-equivariance regulariser on c_t; 8xH100 covers the 125M grid; harness paired replay
measures poison influence. Moderate.

**collision_risk.** medium. Searches run: relay arXiv Q3 (abs:"synaptic tagging" → six neuroscience models
plus two agent-harness papers 2601.04362, 2604.13085), Q4 (eligibility/neuromodulated/three-factor x LM/linear
attention/fast weights/transformer → 0 relevant; 2605.05965 is RLVR credit assignment), Q10
(retroactive/behavioural tagging x memory x LM → 0 relevant), local HF papers ("eligibility trace fast weights
language model neuromodulated plasticity" → Backpropamine 2002.10585, Irie & Gershman 2508.08435), `gh`
"synaptic tagging capture" (0). The Titans/HOPE line is the closest live program and could add a retroactive
gate at any time.

**monitorability_and_safety.** Adds an explicit logged consolidation channel (what the model chose to keep,
and when) — a monitorability positive — and a certified poison horizon for uncaptured content. Risk: a
learned capture gate can be attacked by capture-triggering tokens inside tool results, so an adversarial
capture-trigger arm is mandatory. Data rights: public corpora plus licensed parallel data.

**negative_result_value.** Two-rate GDN matching → "retroactive selection adds nothing beyond multi-timescale
decay", directly informative for the Titans/HOPE continuum-memory line. Gate collapse → the LM loss does not
supervise consolidation timing, the operator-level analogue of the reward-SNR floor (2608.10441). In both
cases the capture-probe instrument and the certified tag decay survive as harness assets.

**pilot_gpu_hours.** 15. **targets_gaps.** G7, G2, G15.

---

## 4. Search log (relay budget: 12 of 12 calls, >= 4 s spacing; plus local routes)

Relay (`tools/hostsearch.sh`, curl on fal-h100-01):
- Q1 arxiv `(abs:"test-time training" OR abs:"fast weights" OR abs:"fast weight") AND (abs:contraction OR abs:"incremental stability" OR abs:"input-to-state stability" OR abs:Lyapunov)` → 2 hits, 0 relevant.
- Q2 arxiv `(abs:"linear attention" OR abs:"delta rule" OR abs:"state space model") AND (abs:"input-to-state stability" OR abs:contraction OR abs:contractive OR abs:"incremental stability")` → 25 hits; slow-weight SSM theory only (2604.07069, 2603.23814, 2505.11602, 2505.03069, 2605.13473).
- Q3 arxiv `abs:"synaptic tagging"` → 8 hits; 2601.04362, 2604.13085 (agent-level), rest neuroscience.
- Q4 arxiv `(abs:"eligibility trace" OR abs:"eligibility traces" OR abs:"neuromodulated plasticity" OR abs:"three-factor") AND (abs:"language model" OR abs:"linear attention" OR abs:"fast weights" OR abs:transformer)` → 25 hits, 0 relevant.
- Q5 arxiv `(abs:"implicit attention" OR abs:"hidden attention") AND (abs:Mamba OR abs:"state space" OR abs:"linear attention" OR abs:"gated linear")` → 4 hits, 0 relevant (the known 2403.01590 did not surface; found via HF papers).
- Q6 hfpapers `attribution state space model recurrent provenance retrieved documents` → PICASO 2502.17605, attribution surveys, TRACE watermark 2607.08400.
- Q7 arxiv `(abs:Mamba OR abs:"state space model" OR abs:"linear attention" OR abs:DeltaNet OR abs:"gated linear") AND (abs:attribution OR abs:provenance)` → 25 hits; 2607.11796 (per-mode instrument), 2606.00926, 2606.11052; nothing per-source.
- Q8 ddg `implicit attention attribution Mamba "state space" retrieved documents provenance linear attention 2026` → empty.
- Q9 arxiv `abs:"persistent excitation" AND (abs:"test-time" OR abs:"fast weights" OR abs:"in-context learning" OR abs:"language model" OR abs:transformer)` → 13 hits, all classical adaptive control.
- Q10 arxiv `(abs:retroactive OR abs:"behavioral tagging" OR abs:"tag-and-capture" OR abs:"tagging and capture") AND abs:memory AND (abs:"language model" OR abs:transformer OR abs:"linear attention" OR abs:"fast weights")` → 4 hits, 0 relevant.
- Q11 openreview `test-time training contraction stability certificate fast weights` → 10 forums, 8 without title metadata; API follow-up redirected to a browser challenge (unresolved).
- Q12 arxiv `(abs:certified OR abs:provable OR abs:guarantee) AND (abs:forgetting OR abs:unlearning OR abs:deletion) AND (abs:"recurrent state" OR abs:"fast weights" OR abs:"linear attention" OR abs:"state space model" OR abs:"test-time training")` → 6 hits; Locas 2602.05085, Mamba-CL 2411.15469, 2505.11602; no certified per-write forgetting for fast weights.

Local (allowed from this Mac): HF papers API x4 (implicit attention attribution SSM; eligibility trace fast
weights LM; contraction certificate TTT; streaming attribution linear attention); `gh search repos` x3 (0
results each); HF model API for `zeyun-zhong` (e2-ttt-{mlp,swiglu}-{340M,1.3B}-15B, StreamTTT-4B) and
`startlux-models` (gdn-340m/1.3b isp-hybrid-3to1 and pas-fa variants); grep of all 17 cell notes for
contraction/Lyapunov/ISS/anti-windup, synaptic/eligibility/neuromodulation/retroactive, implicit
attention/attribution/provenance/sketch (no prior hits beyond the cells' own "not found" records).

Primary pages opened this session (WebFetch abs unless noted): 2311.14495, 2607.27539, 2608.22354,
2002.10585 (abs + PDF pp. 1–10 via Read), 2605.10537, 2512.24695, 2403.01590, 2405.16504, 2608.27128,
2608.12435, 2104.05942, github.com/v-code01/momentwo, 2604.07069, 2603.23814, 2601.04362, 2604.13085,
2502.17605, 2602.01914, 2505.11602, 2608.27763, 2501.00663, 2607.11796, 2502.15612, 2508.08435.

## 5. Coverage limits (honest)

- Relay budget capped at 12 arXiv/DDG/OpenReview/HF calls; exact-phrase `abs:` matching misses paraphrased
  titles; results capped at 25 newest per query.
- OpenReview: titles not returned by the search endpoint; the notes API redirects to a browser challenge, so
  ICLR/NeurIPS 2026 submissions on these topics were not checked.
- Semantic Scholar, Google Scholar, ACL Anthology, Chinese-language sources, live X, and Papers with Code were
  not searched. WebSearch budget was exhausted before this cell started.
- Abstract-level only for 2405.16504, 2403.01590, 2502.15612, 2607.11796, 2508.08435, 2501.00663, 2512.24695,
  2605.10537, 2604.13085, 2601.04362, 2505.11602, 2603.23814, 2604.07069; full text read only for Backpropamine
  (pp. 1–10). LaTIM's exact decomposition and Zimerman et al.'s complexity were therefore not verified beyond
  their abstracts — C1's delta over them is stated at the level of what those abstracts claim.
- Classical control/neuroscience/coding sources (Lohmiller & Slotine 1998; Ioannou & Kokotovic 1983; Candes &
  Tao 2005; Frey & Morris 1997; Moncada & Viola 2007; Fremaux & Gerstner 2015) were cited from memory and not
  re-opened; their attributions should be verified before any proposal is written.
- No code was executed and nothing was measured; all GPU-hour figures are estimates scaled from E2-TTT's
  340M/15B-token runs and the seq-operators cell's 350M/15B-token day-scale precedent.
- Venue statuses: Backpropamine ICLR 2019 (PDF header), Zubic & Scaramuzza TMLR 2026 (abs comments), PICASO
  ICLR 2025 (abs comments), FlashTrace ICML 2026 Oral (abs comments), Titans NeurIPS 2025 (cell search record,
  not the abs page), Nested Learning NeurIPS 2025 (abs). Everything else is a first-party preprint or repo.
