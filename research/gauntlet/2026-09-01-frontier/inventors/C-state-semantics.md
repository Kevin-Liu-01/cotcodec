# Angle C — sequence-operator state semantics (inventor: C-state-semantics) — 2026-09-01

Angle: recurrent state with explicit provenance, ordered recall, edit/delete/undo or confidence guarantees.
Not Coded Delta (parked as a negative cell). Mandatory baselines where relevant: QED (2608.13668), MARCH
(2608.12435), SANE (2608.22354), SWA+sinks (2608.28444), Tail-Replay (2608.30310). Targets synthesis gaps
G2 (language/script-controlled recurrent state) and G7 (verifiable reset/rollback/deletion of test-time state,
poisoning), plus the Axis-C remnant "confidence inside recurrent state" and the Diag-B remnant (non-suffix edits).

Honesty: no candidate below is "completely novel". Every "not found" is "no direct prior art found through
2026-09-01 under the coverage in §5". All 2026 numbers quoted from priors are first-party unless a venue is named.

## 0. One algebraic fact all three candidates lean on (phase-0 doctor already run on CPU)

Every production linear-attention layer in 2026 hybrids has a *state-independent* affine transition
S_t = S_{t-1} A_t + b_t with (A_t, b_t) functions of x_t only:

- GDN:     A_t = alpha_t (I - beta_t k_t k_t^T),        b_t = beta_t v_t k_t^T
- KDA:     A_t = Diag(alpha_t)(I - beta_t k_t k_t^T),   b_t = beta_t v_t k_t^T
- GDN-2:   A_t = alpha_t (I - k_t (b_t ⊙ k_t)^T),       b_t = v_t k_t^T  (channel-wise erase gate b_t)
- Mamba-2: A_t = alpha_t I,                             b_t = v_t k_t^T
- RWKV-7:  A_t = Diag(w_t) - k_t (a_t ⊙ k_t)^T,         b_t = v_t k_t^T

Consequences (all checked in fp64 by `design/c_state_doctor.py` and a follow-up snippet, 2026-09-01):

1. Segment transport. For a contiguous tagged segment p = [j, j+L): D_p := S_{j+L-1} - S_{j-1}; transport
   D_p(t) = D_p(t-1) A_t for t >= j+L. Then S_t - D_p(t) equals the state the layer would hold had the segment
   been skipped with all later (k, v, alpha, beta) unchanged. Residual <= 7.5e-16 relative for GDN, KDA, GDN-2,
   Mamba-2, RWKV-7. This is Proposition 1 ("frozen-input transport") of arXiv:2607.27539; it is NOT new.
2. Write-only ledger. r_{i,t} = beta_i (A_{i+1} ... A_t)^T k_i, maintained at O(d_k) per step
   (r <- alpha_t (r - beta_t k_t (k_t · r)) for GDN). S_t = sum_i v_i r_{i,t}^T exactly (6.7e-16).
3. Token unwrite. With u_j = v_j - alpha_j S_{j-1} k_j (the delta / pseudo-value at write time),
   S_t - u_j r_{j,t}^T equals the state with token j's write AND erase removed but its decay kept (8.9e-16).
4. Failure for nonlinear fast weights. For a one-hidden-layer TTT-MLP (SGD on ||f_W(k) - v||^2) the analogous
   subtract-delta residual is 3.0e-01: the transition depends on the state, so no exact unwrite exists.
   Exact O(d) unwrite is therefore a property of the linear-transition family (DeltaNet/GDN/GDN-2/KDA/Mamba/
   RWKV-7) and not of TTT-MLP/E²-TTT/Titans/MoNe-class memories.

What 2607.27539 (Ramesh, v1 2026-07-30, v2 2026-08-13; single author; Kimi-Linear-48B, inference only) already
established, read in full text: transport reproduces a deliberately frozen suffix to 6.1e-6 max relative error;
on native omission the later (A_t, b_t) change ("forcing"), median forcing-to-difference norm ratio 0.84; the
corpus-pooled raw recurrent contribution changes by 12–49% with the suffix (8–49% after a diagonal-decay
correction); conclusion "checkpoint replay is the only evaluated recomputation path"; NO behavioral or task-level
fidelity of transport was reported and nothing was trained. That leaves two things open that the candidates
below take: (a) the behavioral question — does bounded-cost per-layer unwrite recover the model-level replay
counterfactual on tasks, and does the exact two-view read give a usable monitor — and (b) whether the forcing
residual is trainable away (2607.27539 says the mismatch is "structural" within its frozen frame).

State-size arithmetic for a shadow matrix per tagged segment: Kimi-Linear-48B-A3B-Base config (fetched
2026-09-01): 27 layers, 20 KDA layers, 32 heads × head_dim 128 → 1 MiB per KDA layer in bf16, 20 MiB per tagged
segment per sequence. Qwen3.5-4B (text_config fetched 2026-09-01): 32 layers = 24 GDN + 8 full attention
(interval 4), GDN 16 key heads × 128 and 32 value heads × 128 → 1 MiB per GDN layer in bf16, 24 MiB per tagged
segment per sequence; attention 16 q heads / 4 KV heads, head_dim 256.

---

## Candidate 1 (cheap-decisive) — `provenance-ledger-reads`

**Claim.** Maintaining one exactly transported shadow matrix per tagged segment in every linear-transition layer
gives 2026 hybrids three quantities they did not have — exact per-segment read influence, exact per-segment
retention, and a zero-parameter unwrite — and the question of how much of the replay counterfactual the unwrite
recovers on tasks (not on state norms) is decidable in ≤ 8 GPU-hours on pinned checkpoints.

**claim_scope.** attachment-capability.

**Mechanism.** In each linear layer keep D_p(t) for every tagged segment p (tool result, retrieved passage,
user turn), updated with the layer's own transition, D_p(t) = D_p(t-1) A_t (cost O(d_v d_k) per step per
segment, identical to the state update; 1 MiB/layer/segment on Kimi-Linear-48B). Expose per step:
influence pi_p(t) = ||D_p(t) q_t|| / ||S_t q_t|| (share of this read attributable to p; a two-view read
y_t vs y_t^{-p} = (S_t - D_p(t)) q_t); retention rho_p(t) = ||D_p(t)||_F / ||D_p(j+L-1)||_F (how much of the
segment survives decay and erasure — an exact per-item analogue of DASC's weight-derived retention horizon);
unwrite S_t <- S_t - D_p(t) applied together with masking p's KV entries in the 1-in-4 global attention
layers. The per-token refinement (u_j, r_{j,t}) at O(d_k) per step removes a single token's write and erase
while keeping its decay. The tested claim is behavioral: recovery fraction R(g) = (EM_unwrite - EM_poisoned) /
(EM_replay - EM_poisoned) as a function of gap g since the segment, layer type (transport-only vs KV-mask-only vs
both), and segment type; and AUROC of pi_p(t) as an injection monitor for the 3/4 of layers that have no
attention weights.

**What is new (against the three closest priors).**
- vs Subtract/Transport/Replay (2607.27539): the transport identity is theirs; we add the behavioral fidelity
  curve R(g) with a paired replay oracle, the two-view influence monitor, and the per-segment retention
  certificate, on the same registered Kimi-Linear-48B plus Qwen3.5-4B and Mamba-130M.
- vs DeltaLog (2608.15533): DeltaLog keeps a bounded log of recent rank-1 updates to defer materialisation and
  never removes anything; the ledger transports a segment's delta forward so that it can be removed or attributed.
- vs Tail-Replay (2608.30310): Tail-Replay approximates the state from a 5–10% suffix and cannot delete a
  specific interior segment; it is our cheap "forget-everything-old" control, and its 92.8–99.9% retention
  result predicts that unwrite of old segments is nearly free while recent segments are where R(g) matters.
- Adjacent (opened): WriteSAE (2605.12770) does cache-level rank-1 write replacement in GDN/Mamba-2/RWKV-7 but
  does not attribute state to past segments; AttnTrace (2508.03793, IEEE S&P 2026) and Attention Tracker
  (2411.00348) attribute injections through softmax attention weights only; Naju (2607.21000) decouples
  retention and write gains but offers no deletion or provenance.

**Falsifiable predictions.**
1. Qwen3.5-4B, 256-token poisoned tool result, 500 paired episodes per cell: R(g=512) >= 0.60 for the full
   unwrite (transport + KV-mask) and R(g=8K) >= 0.30; transport-only recovers < 0.20 at every gap (retrieval
   lives in the global layers, 2606.15378), KV-mask-only recovers >= 50% of what the full unwrite recovers.
   Embarrassing if R(512) < 0.30 on both Qwen3.5-4B and Kimi-Linear (then the primitive is behaviorally useless
   and 2607.27539's negative extends to behavior).
2. Injection monitor: pi_p(t) from linear layers alone reaches AUROC >= 0.85 on an InjecAgent/AgentDojo-style
   tool-result injection set on Qwen3.5-4B, within 0.05 of Attention-Tracker-style scores from the 8 global
   layers, and the union improves AUROC by >= 0.02 over attention-only.
3. Retention certificate: rho_p(t) predicts per-fact recall failure on a 16-fact TP-style recall probe with
   AUROC >= 0.80, versus <= 0.70 for DASC's static horizon proxy and for SANE's norm-anomaly statistic.
4. Exactness: per-layer unwrite versus a kernel-level shadow (fla kernel re-run from S_before with cached
   projections) agrees to <= 1e-5 relative in bf16 and passes the two-forward-pass prefix-invariance audit
   (2608.22876) with zero flagged layers.

**Kill conditions.** (a) Prediction 1 fails on both models (R(512) < 0.30) → publish the behavioral negative and
hand the forcing residual to Candidate 3. (b) pi_p AUROC < 0.75 or no gain over attention-only attribution.
(c) Any prefix-invariance leak in the ledger path (implementation, not science; fix before reporting).

**Cheapest decisive pilot.** Phase 0 (CPU, done): fp64 identities above; extend the doctor with the
two-forward-pass audit and a retrieval-impossible control corpus (SR-TTT lesson). Phase 1 (frozen checkpoints,
inference only): registry `qwen3.5-4b` (GDN 3:1, native transformers), `mamba-130m-hf` (Mamba-1 selective
scan, exogenous), `kimi-linear-48b-a3b-base` (KDA; bf16 on 2–4 H100; the exact model of 2607.27539);
synthetic retraction suite (fact / tool-result / poison segments of 64–512 tokens; gaps 128, 512, 2K, 8K;
500 paired episodes per cell; McNemar), injection set for the monitor, 16-fact recall probe for retention.
≈ 8 GPU-hours total (Kimi-Linear dominates).

**Controls.** Paired checkpoint replay (oracle); KV-mask-only; transport-only; Tail-Replay-style suffix
restart excluding p; "do nothing"; ICUL-style in-context "ignore the previous tool result" instruction;
Attention-Tracker/AttnTrace-style attention attribution on global layers (monitor); DASC weight-derived
retention horizon and SANE norm-anomaly statistic (retention/confidence); two-forward-pass prefix-invariance
audit on every path; generation exact match with paired McNemar; all seeds and negative cells reported.

**Kevin advantage.** The pinned Kimi-Linear-48B-A3B-Base is the model behind the published negative;
Qwen3.5-4B and Mamba-130M are pinned; the harness already has the deterministic paired-replay oracle and
hash-chained receipts; 8×H100 makes the 48B bf16 runs routine. No unique data asset — honest "moderate".

**Collision risk.** medium. Searches run (hostsearch, 2026-09-01): arXiv `(abs:"linear attention" OR
abs:"delta rule" OR abs:"recurrent state") AND (abs:unlearning OR abs:deletion OR abs:retraction OR
abs:rollback)` → 0 entries; arXiv `(deletion|unlearning|forgetting|"right to be forgotten") AND
(Kimi|"Gated DeltaNet"|"linear attention"|"state space model"|Mamba) AND "language model"` → 16 hits, only
2607.27539 on deletion (others: GDN-2, WriteSAE, Naju, Kaczmarz, Forgetting Transformer); arXiv `"prompt
injection" AND (attention|attribution) AND detect*` → 23 hits, all softmax-attention or harness level
(AttnTrace, Attention Tracker, BASIS, Attnlocate 2608.24022, GIF 2606.23277 Jacobian bounds); DDG queries
returned empty (bot challenge). The algebra is published (2607.27539 Prop. 1; DeltaLog, TreeWY, WriteSAE work on
the same objects), so the remaining delta is the behavioral/monitor evaluation — medium.

**Monitorability and safety.** Increases monitorability: an exact per-segment influence signal exists for
layers that previously had none, and it does not touch the CoT. Retraction of injected tool output is a
safety-positive capability; restrict erasable spans to typed tool/retrieval segments (never system prompts) and
log every unwrite. Data: synthetic suites plus public injection benchmarks; no MIMIC-class data needed.

**Negative-result value.** If R(g) is small, the forcing term dominates behavior, not only norms — a
deployment-relevant fact for every DASC/Tail-Replay/DeltaLog user and the motivation for Candidate 3. If
pi_p fails, recurrent reads carry little injection signal and monitors can stay attention-only in hybrids.

**Targets.** G7; Axis-C remnant "confidence inside recurrent state"; Diag-B remnant (non-suffix edits).

---

## Candidate 2 (moonshot) — `translation-equivariant-state-writes`

**Claim.** A fixed-size recurrent state that stores *meaning* should write the same segment delta for two
translations of the same span; supervising that on parallel data in half the heads of a GDN/KDA hybrid
closes the cross-lingual recall gap (key written in language A, queried in language B) at equal monolingual
recall, and the same delta object is the instrument that first measures whether 2026 hybrids store meaning or
surface.

**claim_scope.** architecture-causal.

**Mechanism.** In a 3:1 GDN (or KDA) hybrid, for an aligned parallel span pair (a^A, a^B) placed after a shared
prefix c, the per-head state contribution of the span is the exact segment delta D^{(l,h)}(a) = S_after -
S_before (S_before is identical for both languages because the prefix is shared). Designate a head subset E
(half the heads of every linear layer). Loss: L = L_LM + lambda [ L_eq + L_nce ], with
L_eq = mean_{l, h in E} (1 - cos(vec D^{(l,h)}(a^A), vec D^{(l,h)}(a^B))) and
L_nce = -log( exp(s(D^A, D^B)/tau) / sum_{B' in batch} exp(s(D^A, D^{B'})/tau) ), s = cosine over the
concatenated E-head deltas, negatives = deltas of non-parallel spans (prevents the D -> 0 collapse);
lambda in {0.1, 0.3}, tau = 0.07; heads outside E receive no alignment term and may keep language-specific
surface information. This supervises WHAT THE STATE WRITES — the object that later reads S_t q_t consume —
rather than residual-stream token representations (PreAlign 2407.16222, Middle-Layer alignment 2502.14830),
sentence embeddings (LaBSE/InfoXLM line), or byte boundaries (dir 18). Instrument: translation-paired MQAR
(TP-MQAR): N facts written as natural sentences in language A among distractors, queried in language B,
generation exact match, key-language × query-language matrix, N in {4, 16, 64}, context 1K–16K (4× training
length), per-script decay curves (recall vs distance for Latin vs high-fertility scripts at matched semantic
content); functional swap at inference: replace D^A by D^B in E heads and re-read (GI-SAE's interchangeability
criterion, 2608.23809). Frozen screen first (hybrid vs dense sibling), then from-scratch 60–135M bilingual arms.

**What is new (against the three closest priors).**
- vs MLNeedle (2408.10151, 2024-08-19): cross-lingual needle retrieval exists for 2024 transformers (needle and
  question in different languages); nothing tests recurrent-state operators, capacity curves (N facts), decay
  vs script, or intervenes; no MQAR-style paired design.
- vs Leino & Tiedemann (2603.29026, 2026-03-30): parallel data in the pretraining MIXTURE barely moves
  representation alignment; we do not rely on mixture effects — we put an explicit equivariance loss on the
  recurrent write, and their result is our pre-registered null for the bitext-only arm.
- vs Middle-Layer Representation Alignment (2502.14830, ACL 2025; and PreAlign 2407.16222): alignment
  objectives act on residual-stream token/word representations of transformers; ours acts on the matrix-shaped
  state delta of linear layers and is evaluated on recall from state, not on transfer accuracy.
- Adjacent: FAAST (2605.04651) uses MT pairs as fast-weight labels, not as a write-equivariance target;
  Skill Issue (2608.25832) is a language-invariance instrument for skills, not memory; GI-SAE (2608.23809) gives
  the swap methodology and the warning that geometric similarity ≠ functional interchangeability.

**Falsifiable predictions.**
1. Frozen screen: on TP-MQAR (N=16, 8K context, En↔De and En↔Zh), Qwen3.5-4B (24 GDN + 8 attention) shows a
   cross-lingual gap (A≠B minus A=B) >= 10 exact-match points that exceeds the dense Qwen3-4B sibling's gap by
   >= 5 points; Kimi-Linear-48B-A3B-Base (KDA) shows a gap >= 8 points. Embarrassing if the hybrid gap is
   within 3 points of the dense model (fixed-size state already stores meaning → kill the intervention,
   publish the instrument).
2. From-scratch 60–135M bilingual hybrids (3 seeds): the equivariance arm cuts the cross-lingual gap by >= 50%
   relative to the baseline at monolingual recall within 2 points and LM loss within 0.5%; the middle-layer
   hidden-state alignment control closes <= 25% of the gap at the same lambda and data.
3. Functional swap: replacing D^A by D^B in E heads preserves >= 80% of recall in the equivariance arm and
   <= 40% in the baseline.
4. Script effect: baseline recall half-life (tokens) for facts written in Thai/Bengali is <= 0.7× that for
   Latin at matched semantic content; the equivariance arm raises the ratio to >= 0.9.

**Kill conditions.** (a) Prediction 1 fails (no hybrid-specific gap). (b) Equivariance arm does not beat the
hidden-state-alignment control by >= 5 points (generic representation alignment suffices; state-level
supervision redundant). (c) Collapse or a tax: LM loss > 1% worse, or ||D|| shrinks > 30% in E heads.
(d) The SWA+sinks arm shows the same cross-lingual gap → the gap is not about recurrent state.

**Cheapest decisive pilot.** Phase 0 (CPU): TP-MQAR generator with span alignment from General Translation
corpora (or OPUS/FLORES where licences require), leakage checks (retrieval-impossible control; first-token
perturbation; exclusive causal writes), fp64 check that D^A, D^B are the exact span deltas. Phase 1 (frozen,
<= 2 GPU-h): `qwen3.5-4b` vs Qwen3-4B dense sibling (add to registry), `kimi-linear-48b-a3b-base`, startlux
340M/1.3B GDN hybrids as English-only sanity controls. Phase 2 (from scratch, <= 12 GPU-h): 60M 3:1 GDN hybrids,
1B tokens of En + {De, Zh, Th} monolingual + parallel data, 5 arms × 3 seeds, per-arm LR sweep of 4 values at
the smallest rung (2608.11859), fla >= 0.5.2 kernels, SIGUSR1-resumable Slurm jobs. ≈ 14 GPU-hours total.

**Controls.** No-alignment baseline (iso-params/tokens/FLOPs); middle-layer hidden-state alignment with
identical data and lambda; bitext-in-mixture only (Leino & Tiedemann null); SWA+sinks hybrid (2608.28444);
QED- and MARCH-equipped linear layers as the mandatory recall baselines; dense sibling in the frozen screen;
romanized-input control for the script prediction (2608.25904); generation exact match, 4× OOD length,
paired clustered SEs over >= 3 seeds, early context-extension probe (2608.10296).

**Kevin advantage.** Parallel corpora with span alignment at General Translation make "only the language
changes" state probes buildable today (the defining asset per synthesis §0.2); two registered hybrid families
(GDN Qwen3.5-4B, KDA Kimi-Linear-48B); the from-scratch hybrid harness and 8×H100 for the 60M grid.

**Collision risk.** low. Searches (hostsearch, 2026-09-01): arXiv `(multilingual|"cross-lingual") AND
("linear attention"|"state space"|Mamba|DeltaNet) AND (recall|retrieval|needle)` → 1 irrelevant survey;
arXiv `("parallel data"|"parallel corpus"|translation) AND ("recurrent state"|"memory state"|"hidden state")
AND alignment AND ("linear attention"|"state space"|recurrent)` → 0; arXiv `(Mamba|"state space model"|
"linear attention") AND (multilingual|"cross-lingual") AND "language model"` → Falcon-H1 (training data only),
Mamba ASR; HF papers `cross-lingual alignment loss parallel sentences pretraining hidden representations` →
InfoXLM, PreAlign, Middle-Layer alignment, LaBSE-class sentence encoders (all residual-stream/embedding level);
DDG cross-lingual-needle query returned empty (bot challenge). benchmarks-eval G2 and seq-operators G1 report
the same emptiness. Caveat: MLNeedle is a real 2024 prior for the cross-lingual NIAH framing on transformers.

**Monitorability and safety.** CoT untouched. A meaning-level state may make monitors trained in one language
transfer better (positive, testable later against 2605.27901), but it may also remove surface cues a monitor
uses — report both. Data rights: use only licensed or open parallel corpora (OPUS, FLORES, GT-owned corpora
cleared for research), never customer content.

**Negative-result value.** If hybrids show no extra cross-lingual gap, the first instrument result on G2 is
"fixed-size states store meaning" — closes the question cheaply. If the state-level loss does not beat
hidden-state alignment, parallel supervision of writes is redundant, extending 2603.29026's family of
"limited utility of parallel data" results to recurrent state.

**Targets.** G2, G20 (translation-paired recall instrument); informs G13 and latent-reasoning G15 later.

---

## Candidate 3 (moonshot, medium cost) — `trainable-erasure-hybrid-state`

**Claim.** Erasability is a trainable property of hybrid state: exact per-layer transport plus a small learned
corrector for the forcing residual (and, in the stronger arm, an unwrite-consistent training objective on the
base) makes bounded-cost erasure of a typed context span behaviorally equivalent to full replay, giving 2026
GDN/KDA hybrids a deletion primitive whose cost does not grow with the suffix.

**claim_scope.** architecture-causal.

**Mechanism.** Hybrid Context Eraser (HCE). Given a processed context and a typed span p (tool result, retrieved
passage, injected instruction) to erase at time t: (i) linear layers: S_t <- S_t - D_p(t) with the exactly
transported segment delta (zero parameters; exact for fixed inputs); (ii) global-attention layers: drop p's KV
entries and insert m learned steering KV pairs (m = 4–16) emitted by a corrector network phi (the KVEraser move,
restricted to the 1-in-4 attention layers); (iii) for linear layers phi additionally emits a rank-r correction
Delta S^{(l)} = U^{(l)} V^{(l)T} (r <= 8) from features (pooled S_t^{(l)}, pooled D_p(t), a span summary, gap g)
to absorb the forcing residual — the part of the true counterfactual due to later tokens having been processed
with p present, which 2607.27539 measured as dominant (median 0.84 norm ratio) and which zero-parameter
transport cannot touch. Training: teacher = the same frozen model run on the context with p removed (paired
replay); loss = KL(p_teacher(x_{t+1..t+W}) || p_erased) over a window W = 512 after t, plus a residual-recall
penalty on probes about p's content; curriculum: generic spans → typed spans, gaps to 8K; phi <= 20M params,
shared across layers. Stronger arm (unwrite-consistent training): also update the base (LoRA on Qwen3.5-4B;
full parameters in a 135M from-scratch hybrid) with the same objective so downstream layers become robust to
exact per-layer unwrite. Cost per erase O(|p| + L_lin d_v d_k + m L_attn), independent of suffix length
(replay is O(suffix)). Certificate: F(g) = 1 - KL(teacher || erased) / KL(teacher || unerased) and exact-match
agreement vs g; the fixed-input exactness of the linear component is audited separately with the two-forward-pass
prefix-invariance test so that all residual error is attributable to forcing.

**What is new (against the three closest priors).**
- vs KVEraser (2606.17034, v1 2026-06-15; ICML 2026 workshop oral): learned steering KV states replace an erased
  span's KV in transformers (matches full recomputation on in-domain tasks at +24% latency vs 17.6×); nothing
  addresses layers without token-addressable state; HCE adds the exact transport component for linear layers,
  a rank-r state corrector, the fidelity certificate vs gap, and the unwrite-consistent training arm.
- vs Subtract/Transport/Replay (2607.27539): transport is zero-parameter and its forcing residual is declared
  "structural"; HCE tests whether that residual is learnable and reports task fidelity, which they did not.
- vs Dependency-Guided Rollback (2608.10502, 2026-08-11): rollback of poisoned memories at the harness /
  memory-store level with selective replay of affected computation; HCE erases inside the model's state and
  KV without replay.
- Adjacent (opened): VANE (2608.09448) isolate-then-commit reversible updates (robotics prompts); In-Context
  Unlearning (2310.07579, ICML 2024) removes training instances via contradicting labels in context, not
  context spans; Forget-to-Know (2510.17620) is weight-level.

**Falsifiable predictions.**
1. Frozen Qwen3.5-4B + phi (<= 20M params, ~50M tokens of synthetic retraction episodes): exact-match agreement
   with the replay teacher on post-erasure probes >= 90% at g = 2K, versus <= 60% for zero-parameter unwrite
   (Candidate 1) and <= 75% for a KVEraser-style attention-only eraser on the 8 global layers with linear
   states untouched. Embarrassing if phi beats attention-only by < 5 points (recurrent state carries little
   erasable influence).
2. Poisoning retraction (plain false assertions in retrieved passages, 2608.21230's design): post-erasure
   accuracy within 3 points of the clean run at g <= 2K, with erase latency <= 5% of full recomputation at
   16K context, CPU overhead charged.
3. Unwrite-consistent 135M from-scratch hybrid: zero-parameter unwrite fidelity F(2K) rises from the baseline
   model's value to >= 0.80 at <= 0.5% LM-loss cost (3 seeds).
4. Transfer: phi trained on generic spans loses <= 5 points on unseen injected-instruction spans.

**Kill conditions.** (a) phi never beats the attention-only eraser by >= 5 points at any gap. (b) F(2K) < 0.5
even after training (forcing residual not compressible → hybrids must budget replay for retraction; publish).
(c) Erase cost is not >= 3× cheaper than checkpoint replay from the span start at 16K. (d) Unwrite-consistent
training costs > 1% LM loss. (e) Residual recall of erased content exceeds the replay teacher's by > 2 points
(erasure hides rather than removes).

**Cheapest decisive pilot.** Phase 0 (CPU): synthetic retraction-episode generator with the paired replay
oracle, leakage checks, retrieval-impossible control. Phase 1 (frozen `qwen3.5-4b`, <= 6 GPU-h): train phi on
~50M tokens of episodes; evaluate F(g) and predictions 1, 2, 4; compare all controls. Phase 2 (<= 8 GPU-h):
135M from-scratch 3:1 GDN hybrid, 2 arms (with/without the unwrite-consistent objective) × 3 seeds × 1B
tokens; Tinker not needed (local only). ≈ 14 GPU-hours.

**Controls.** Paired replay (oracle); checkpoint replay from the span start (exact, O(suffix)); zero-parameter
unwrite (Candidate 1); KV-mask-only; KVEraser-style attention-only learned eraser (strongest published
baseline, re-implemented for hybrid global layers); Tail-Replay suffix restart excluding p (2608.30310);
ICUL-style "ignore" instruction; Dependency-Guided Rollback as the harness-level system baseline where the
task allows; a 135M SWA+sinks model as the all-token-addressable reference for erasability; equal-latency
ledger with CPU overhead charged; two-forward-pass prefix-invariance audit; McNemar over paired episodes.

**Kevin advantage.** The CMHT causal-trial spine already produces paired deterministic episodes with poison
arms and hash-chained receipts (the replay oracle is the estimator's core); pinned hybrids across GDN and KDA;
8×H100. No unique data asset — "moderate", and Tinker adds nothing (no hidden-state access).

**Collision risk.** medium-high. Searches: HF papers `remove injected tool output from context without
recomputation KV cache counterfactual` → KVEraser (direct transformer analogue), RestoreKV, VeriCache (KV
fidelity), Tool Unlearning (weights); arXiv `abs:"in-context unlearning" OR ("KV cache" AND unlearning) OR
(context AND retraction AND "language model")` → ICUL and unrelated; HF papers `retract context segment training
objective counterfactual distillation ...` → nothing on context retraction training. KVEraser's group and
2607.27539's author are active on exactly this problem; extension to hybrids is an obvious next step for
either.

**Monitorability and safety.** Safety-positive (retraction of poisoned tool output without replay) but
dual-use: an eraser could remove safety-relevant spans — restrict to typed tool/retrieval spans, never system
or developer messages, and log every erase with its certificate. A learned eraser may hide rather than remove
influence: report residual recall of erased content and the prefix-invariance audit as first-class safety
metrics. CoT untouched. Data: synthetic and public injection/poisoning suites.

**Negative-result value.** If trained erasure cannot approach replay, the recurrent state's influence on later
inputs is not compressible — hybrid serving must budget O(suffix) replay for retraction (a systems-relevant
negative that DASC/Tail-Replay users need). If attention-only erasing suffices, recurrent layers carry little
retractable influence in 3:1 hybrids, consistent with 2606.15378.

**Targets.** G7 (deletion/rollback/poisoning of test-time state); Diag-B remnant (non-suffix edits on
long-retention units, measured with rank r of the learned correction).

---

## 4. Ordering and dependencies

Run Candidate 1 first (8 GPU-h, frozen models); its R(g) curve decides whether Candidate 3 is needed and
supplies the D_p machinery Candidate 2 reuses for the span deltas. Candidate 2's frozen screen (2 GPU-h) can run
in the same week; its from-scratch arms wait for the Stage-0 believability defaults (per-arm LR sweeps, seeds,
audits). Total for all three pilots ≈ 36 GPU-hours on 8×H100.

## 5. Coverage limits (honest)

- 12 host-relayed searches (arXiv API ×6, DDG ×2, HF papers ×4); both DDG calls returned empty (bot challenge),
  so general-web coverage is nil; OpenReview not queried; Semantic Scholar unavailable; WebSearch budget spent.
- Abstracts opened via WebFetch (small-model summaries; numbers quoted only where they appeared verbatim):
  2607.27539 (abs + full HTML, targeted extraction), 2608.15533, 2608.30310, 2603.29026, 2408.10151, 2608.23809,
  2310.07579, 2608.10502, 2608.09448, 2411.00348, 2605.31163, 2608.22876, 2606.17034, 2608.24022, 2606.23277,
  2407.16222, 2502.14830, 2607.21000, 2605.12770, 2508.03793. QED, MARCH, SANE, SWA+sinks, DASC, Falcon,
  E²-TTT, Modular TTT were taken from the cell notes' abstract records, not re-opened.
- Not searched: Chinese-language sources, Google Scholar, ACL Anthology, ICLR 2027 submissions, live X.
- Nothing was run on the H100 node; the fp64 doctor ran on this Mac (numpy). Model configs were read from the
  Hugging Face raw config.json (Qwen3.5-4B via text_config; Kimi-Linear-48B-A3B-Base top level).
- MLNeedle (2408.10151) contradicts benchmarks-eval G2's "no cross-lingual NIAH exists" for transformers; the
  gap survives only for recurrent-state operators and paired MQAR designs.
