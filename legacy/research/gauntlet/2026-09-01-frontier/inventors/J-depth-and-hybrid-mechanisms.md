# Inventor J — depth and hybrid mechanisms (design note, 2026-09-01)

Angle: mechanism questions the 2026 production hybrids ship without understanding — NoPE global layers
(Kimi K3 / Solar Open 2 keep them, Qwen3.8-Next dropped them after post-training "endless generation"),
depth-axis operators (AttnRes vs mHC vs Gated Residual), MTP heads on small hybrids — framed as causal
architecture experiments at 125M–350M on a shared 3:1 hybrid substrate (the K3-stack small reference of
G12 is the substrate, not the claim). Targets synthesis gaps G9, G10, G11, G12 (+ G2, G20 secondarily).

Read in order: context.md; design/brief.md; sweep/synthesis.md (all 1,455 lines: occupied map A–Y, gaps
G1–G22, kill-shot verdicts, post-cutoff table, coverage limits, synthesis path); sweep/seq-operators.md
(F1–F30, G1–G6, exact queries); sweep/arxiv-triage-arch.md; sweep/local-model-ecosystem.md (F1–F28, G1–G5,
node feasibility table); bookmarks.md (G2–G4 grep); benchmarks-eval.md (F1/F7/G1 grep); killshot-current.md
(grep); research/frontier-systems-program-2026-08-10.md "occupies" + "Rejected" tables; models/registry.yaml;
research/proposals/_template.md.

Honesty: no candidate below is called novel. Wording used: "No direct prior art found through 2026-09-01
under <coverage>". Every quoted number is a first-party author claim from the abstract page opened with
WebFetch unless a cell note is cited. Coverage limits are at the end.

---

## Shared substrate and shared controls (apply to all three candidates)

- Substrate: from-scratch 125M (phase 1) and 350M (phase 2) 3:1 hybrids copying the Qwen3.5-0.8B layout
  (18 linear + 6 global, interval 4; seq-operators F4) with GDN (fla `chunk_gated_delta_rule`) or KDA-LB
  (fla `chunk_kda`, `gate_lower_bound -5`, full-rank output gate as in K3; F1). Dense twins copy
  `smollm2-135m` (registry id) layout and tokenizer. Tokens: 2.5B (20N) at 125M, fixed multilingual mix
  (FineWeb-Edu + open multilingual slices; parallel corpora used only for probes). This is G12's "open
  ≤1B K3-stack reference" built as a by-product; the recipe is released with every run.
- Believability bar (synthesis §0.7; benchmarks-eval F1/F7): per-arm LR/batch search at the two smallest
  rungs (2608.11859), ≥2 seeds in pilots and ≥5 at confirmation with paired clustered SEs, generation-based
  evaluation with permutation controls (Stuck-on-A 2608.02689; When Perplexity Lies 2603.26556), early
  context-extension probe at 25%/50% of training (Cracks in the Foundation 2608.10296, COLM 2026),
  two-forward-pass prefix-invariance audit of every fla kernel path (2608.22876), SWA(128)+sinks hybrid twin
  (2608.28444), startlux 340M/1.3B 3:1 GDN hybrids (2608.12149) as released pre-norm references.
- Known hazards: transformers' pure-PyTorch chunked-KDA fallback gives NaN gradients (PR #48455) — use the
  fla/FlashKDA kernel path only; kernels are opt-in since transformers v5.15 (local-model F15/F21).
- Compute arithmetic (est., benchmarks-eval G1: "a 125M model to 20N tokens is ~1 GPU-hour"): I budget
  1.3–1.5 GPU-hours per 125M/2.5B-token run to be safe.

---

## Candidate 1 (cheap decisive) — `nope-hybrid-clock-tiebreak`

**Claim.** The post-training "endless generation" of NoPE hybrids is a positional tie-breaking failure among
repeated spans that appears once generation length exceeds the recurrent state's clock horizon; per-channel
decay (KDA) supplies a longer clock than per-head scalar decay (GDN), which is a testable reconciliation of
Kimi/Solar (NoPE, fine) with Qwen3.8-Next (GDN, NoPE dropped).

**claim_scope:** architecture-causal.

**Mechanism.** In a 3:1 hybrid whose global layers have no positional encoding, position reaches a global
attention layer only through (i) the causal-softmax denominator, whose resolution decays like 1/t
(Ruscio et al. 2606.06160), (ii) the BOS/sink residual trajectory, and (iii) the recurrent layers' states.
For a delta-rule layer with per-step decay a_t (scalar per head in GDN; per channel in KDA),
S_t = sum_{i<=t} (prod_{j=i+1}^{t} a_j) beta_i v_i k_i^T. For a stationary stream with constant a,
|S_t| ~ (1 - a^t)/(1 - a): the state is a usable clock only for t < T_clock = 1/(1 - a) and saturates beyond
it; the Fisher information about t carried by S_t under fixed read noise scales as a^{2t} ln(a)^2 -> 0.
When generation repeats an earlier span, a NoPE global layer sees identical keys at both copies; the only
tie-breaker is the difference of state-derived features between copies, which is O(a^Delta) for copy
distance Delta. Past T_clock the copies are indistinguishable, the induction read averages over copies, the
span is re-emitted and the trajectory falls into a periodic attractor (the "endless generation" Qwen saw).
RoPE breaks the tie by construction. Post-training does not create the failure; it exposes it by moving the
model from teacher-forced natural text (few exact repeats) to long self-generated chat answers (many).
Because KDA's decay is per channel, a few channels can sit near a = 1 (long clock) while the rest forget;
GDN's per-head scalar must serve all channels, so at equal parameters its longest clock is shorter. The
clock horizon is computable from weights exactly as DASC's retention horizon (2608.30386):
T_clock(unit) = 1/(1 - E_x[a(x)]) over a calibration stream.

**What is new (deltas vs three closest priors).**
1. On the Design of Qwen3.8-Next (2608.30320, 2026-08-31, opened): reports NoPE ~ RoPE in pretraining but
   "substantially higher rate of endless generation after post-training" and keeps RoPE — an observation
   with no mechanism, at 25B-A3B, single arm. Delta: a stated mechanism (clock-horizon tie-breaking), a
   pre-registered repetition signature, a weight-derived predictor, and a decay-parameterization factor.
2. Rethinking the Role of Efficient Attention in Hybrid Architectures (2606.15378, 2026-06-13, opened):
   NoPE on the full-attention layers of a small-window SWA hybrid "substantially improves long-context
   performance"; retrieval carried by full attention. Delta: that paper measures retrieval, not termination
   or repetition; it uses SWA locals, not delta-rule states, so it cannot see a clock horizon.
3. Where does Absolute Position come from in decoder-only Transformers? (2606.06160, 2026-06-04, opened):
   traces absolute position to the causal-mask denominator and the BOS residual trajectory in dense RoPE
   models; "Replacing the BOS embedding ... removes 40% of the residual-stream component". Delta: adds the
   recurrent-state channel, quantifies its horizon from decay weights, and links it to a behaviour
   (termination) rather than to attention patterns.
Also opened/cited: Kimi K3 (2607.24653; NoPE MLA, "1-million-token context window"; F1 says position is
carried by KDA gating), Solar Open 2 (2607.20062; 3:1 NoPE with negative-eigenvalue delta rule, 1M),
Kazemnejad et al. NeurIPS 2023 (2305.19466; NoPE "mostly resembles T5's relative PE"), Wang et al. 2024
(2404.12224; NoPE failure = "distraction of attention distributions", fixed by head temperature) — this
dispersion mechanism is the main rival hypothesis and gets its own arm. Canon layers (2512.17351 v2,
NeurIPS 2025; "lift weak architectures like NoPE to match RoPE") — the short conv in GDN/KDA is a Canon-like
local mixer and is ablated. ZetaGPT (2608.09432) is a reference implementation of SSM-before-attention as
implicit position with no quantitative results.

**Falsifiable predictions.**
- P1. 125M 3:1 hybrids, identical 2.5B-token pretraining and identical 20M-token EOS-terminated SFT,
  greedy decoding on 2,000 held-out prompts with a 4,096-token cap: NoPE-GDN non-termination rate >= 3x
  RoPE-GDN (expected >= 15% vs <= 5%), and >= 80% of NoPE non-terminating outputs are periodic with period
  <= 64 tokens (autocorrelation detector).
- P2. NoPE-KDA's non-termination rate <= 0.5x NoPE-GDN's at matched params/tokens, and the weight-derived
  maximum clock horizon is >= 4x longer in the trained KDA than in the trained GDN checkpoints.
- P3. A "most-recent-copy induction" probe (k = 3..8 repeated n-grams with distinct continuations; target =
  continuation after the most recent copy) shows a NoPE-vs-RoPE accuracy gap >= 20 points at 4x the
  training context, and per-run probe error predicts per-run non-termination with Spearman rho >= 0.7.
- P4. Pretrain-only NoPE checkpoints, sampled greedily for 4,096 tokens from natural prefixes, already show
  >= 2x the RoPE loop rate — post-training reveals, not creates, the failure.
- P5 (intervention). A "sticky" decay subset (KDA: 8 channels/head initialised at log a = -1e-4, i.e.
  T_clock ~ 1e4; GDN: one head per layer) or partial RoPE on 1/8 of the global-layer dims closes >= 70% of
  the NoPE–RoPE non-termination gap while moving pretraining loss by <= 0.005 nats.

**Kill conditions.** (a) No NoPE-vs-RoPE termination gap at 125M–350M after SFT (Qwen's effect is scale- or
RL-specific) — negative published, G10 narrowed to "not reproducible below 1B". (b) Gap exists but
non-terminating outputs are aperiodic and the copy probe does not predict it (rho < 0.3) — tie-break
hypothesis dead. (c) KDA ~ GDN in gap and horizon — the decay-parameterization reconciliation is dead.
(d) Head-temperature tuning (2404.12224) removes the gap while sticky channels do not — the dispersion
mechanism, not the clock, dominates.

**Cheapest decisive pilot.**
- Phase 0 (CPU, no LM): NumPy clock-horizon calculator — Fisher information of t from a decayed delta-rule
  state under Gaussian read noise for decay distributions read from released weights
  (`kimi-linear-48b-a3b-base` KDA decay projections vs `qwen3.5-4b` GDN decay projections; registry ids);
  a synthetic tie-break simulation (uniform NoPE keys + state features; copy distinguishability ~ a^Delta);
  a periodicity-detector doctor validated on synthetic loops; an off-by-one/causality doctor for the probe.
- Phase 0b (frozen, ~1 GPU-hour): copy probe + 4K greedy loop rate on `kimi-linear-48b-a3b-base`
  (NoPE MLA + KDA, the only local NoPE hybrid) vs `qwen3.5-4b` (partial RoPE 0.25 + GDN). Directional only —
  confounded by everything else.
- Phase 1 (<= 14 GPU-hours on 8xH100): {RoPE, NoPE} x {GDN, KDA} x 2 seeds = 8 runs x ~1.4 GPU-h = ~11
  GPU-h; identical SFT ~0.5 GPU-h total; probes and decoding ~1.5 GPU-h; early extension probe included.
- Phase 2 (only if P1/P2 hold): intervention arms P5 (6 runs, ~8 GPU-h), partial-RoPE-0.25 arm, 350M scale,
  5 seeds; Tinker post-training of Qwen3.5-4B/9B (partial RoPE) as the production-scale loop-rate control.

**Controls.** RoPE arm (Qwen3.8 production choice) and partial-RoPE-0.25 arm (Qwen3.5); SWA(128)+sinks
hybrid twin with NoPE/RoPE globals (2606.15378, 2608.28444 — mandatory 2026 baseline); dense-transformer
NoPE vs RoPE twin (`smollm2-135m` layout) with the head-temperature fix of 2404.12224 as the
rival-mechanism arm; short-conv on/off (Canon-layer control, 2512.17351); early context-extension probe
(2608.10296); two-forward-pass prefix-invariance audit (2608.22876); per-arm HP search (2608.11859);
generation-based evaluation with permutation controls; paired clustered SEs; iso-parameter and iso-token
across all arms (PE choice changes no parameter count; sticky channels change none).

**Kevin advantage.** Modest and stated honestly: the 8-run grid is one day on the node; the registered
Kimi-Linear-48B-A3B-Base is the only locally runnable NoPE KDA hybrid for the frozen screen; parallel
translation data gives a length-controlled multilingual termination probe (same content in N languages;
if loop rate tracks token count rather than semantic length, that supports the token clock); Tinker's
Qwen3.5-4B/9B (partial RoPE) supply a production-scale post-training control. Any lab with 8 GPUs can run
the core experiment.

**Collision risk: medium.** Searches run (hostsearch, 2026-09-01): arXiv `abs:NoPE AND (abs:hybrid OR
abs:"linear attention" OR abs:"state space") AND (abs:termination OR abs:"endless generation" OR
abs:"post-training" OR abs:"fine-tuning")` -> 1 result (Canon layers, not on this); arXiv
`abs:"positional information" AND (state space|linear attention|delta rule|Mamba) AND (probe|probing|counter)`
-> 1 irrelevant result; DuckDuckGo `NoPE hybrid linear attention "endless generation" post-training
mechanism 2026` -> no results returned; HF papers `NoPE hybrid attention linear` -> 20 results, none on
termination (closest 2606.15378, 2507.06457, 2602.01763). Plus seq-operators cell queries (`all:NoPE AND
(hybrid OR "linear attention")` -> 7, none on termination; `all:NoPE AND ("endless generation" OR
termination ...)` -> 1 unrelated). No direct prior art found through 2026-09-01 under this coverage. Qwen
has the motive and data to publish the mechanism; the Ruscio group could extend 2606.06160 to hybrids.

**Monitorability and safety.** Positional-encoding choice does not touch CoT or action monitorability;
runaway generation is itself a controllability/cost failure, so the result improves it. Data: open
pretraining/SFT corpora only; parallel data used for probes, not training.

**Negative-result value.** If no gap appears at <= 350M, G10 is narrowed to "scale- or RL-specific" and small
labs learn they cannot study it locally; if the gap is not tie-break-driven, the periodicity/probe dataset
is still the first mechanistic record of NoPE termination; the clock-horizon calculator is reusable for
DASC-style compression and for E2-TTT/fast-weight audits.

**Targets gaps:** G10, G12, G20, G2.

---

## Candidate 2 — `global-anchor-skip-read-depth-operators`

**Claim.** In 3:1 linear/global hybrids, depth-axis operators (AttnRes, mHC, Gated Residual) earn most of
their gain by letting later linear layers read the sparse global-attention layers' outputs directly (an
"anchor skip-read"); a restricted operator that routes only global-layer outputs recovers most of the gain
at a fraction of the depth memory, and the gain is larger in hybrids than in dense transformers at
iso-parameters.

**claim_scope:** architecture-causal.

**Mechanism.** Pre-norm: h_{l+1} = h_l + f_l(norm(h_l)); a global-attention output written at layer 4k is
diluted by three linear-layer writes before the next global layer and by ~L/4 writes overall, so late
linear layers see full-rank token interactions only through an attenuated sum. AttnRes reads
h_in^l = sum_{i<l} alpha_{i->l} u_i with alpha = softmax_i(w_l . norm(u_i)) over sublayer outputs u_i
(2603.15031). The hypothesis is that in hybrids alpha concentrates on i in G (global layers) well beyond
their 1/4 share: sum_{i in G} alpha_{i->l} >= 0.5 for linear layers l. Test operator G-AttnRes: sources =
{u_{l-1}} union {u_i : i in G, i < l} — O(L/4) sources, memory O((L/4) d) vs Block AttnRes O(N d) with
N ~ 8, and the same one d-vector per layer. Gated-Residual analogue: reserve one of the four branches to be
written only by global layers (GR-anchor). mHC analogue: constrain the Sinkhorn mixing so one stream
receives only global writes. Interaction statistic: Delta_hyb = loss(pre-norm) - loss(Block AttnRes) in the
3:1 hybrid vs Delta_dense in an iso-parameter dense twin trained on the same tokens; the hypothesis
predicts Delta_hyb > Delta_dense. Secondary probe on the same runs: depth-routing equivariance across
translations — Jensen–Shannon divergence between the alpha distributions of aligned tokens in parallel
sentences vs random token pairs at matched position (bookmarks G2; synthesis G2).

**What is new (deltas vs three closest priors).**
1. Attention Residuals (2603.15031, 2026-03-16, opened): mechanism, Block AttnRes, scaling laws, Kimi Linear
   48B/3B integration; Table 2 vs "mHC-lite" at 194M/436M is first-party single runs (seq-operators F2).
   Delta: no analysis of which layers are read in a hybrid, no restricted-source causal test, no
   hybrid-vs-dense interaction, single seed.
2. On the Design of Qwen3.8-Next (2608.30320, 2026-08-31, opened): Gated Residual ("widened to four branches
   and read through an elementwise gate"); Table 5/6 at 25B-A3B; branch analysis says one branch preserves
   early attention outputs across many layers and Full AttnRes "lands level with GR" (seq-operators F3).
   Delta: Qwen observes the anchor branch but does not restrict writes to global layers, compare against
   a dense twin, or use multiple seeds; the restricted operators here are the causal test of their
   observation.
3. SANA-Video 2.0 (2607.21553, 2026-07-23, opened): a 3:1 gated-linear/gated-softmax video DiT with Block
   AttnRes that "route[s] completed block summaries into later linear layers, enabling anchor-feature reuse
   and boosting deep-layer effective rank by ~12%". This is the closest statement of the mechanism — as a
   first-party interpretation in a bidirectional diffusion model. Delta: causal LMs; the interpretation is
   turned into a falsifiable restricted-source operator, an alpha-mass measurement, and an interaction test
   with multi-seed statistics.
Also opened/cited: mHC (2512.24880, "projects the residual connection space of HC onto a specific manifold";
no numbers in abstract); RD-AttnRes (2608.01075; 5 matched seeds at 120M/343M, 2.0B tokens; -0.0301/-0.0247
NLL vs Block AttnRes; "persistent divergence between the query-key and value depth distributions");
Delta Attention Residuals (2605.18855; routing collapse "max weight ~0.2" in deep layers, deltas raise it to
~0.6; 1.7–8.2% ppl gains at 220M–7.6B); Multi-Head Attention Residuals (2607.27230; -0.061/-0.149/-0.140
loss at 100M/350M/1B, dense); When Does Routing Become Interpretable? (2606.13168; 0.6B Qwen3-based
checkpoints; "the largest mass slice is not the largest causal contribution" — so alpha mass alone is not
enough; the restricted-operator arm is the causal test); Stream collapse in HC (2606.03483; mixing stays
near identity, dominant stream); Attention Sinks and Outliers in AttnRes (2605.17887); mHC-lite (2601.05732).
All of these are dense-transformer studies; none isolates global-layer sources in a hybrid or measures the
hybrid-vs-dense interaction.

**Falsifiable predictions.**
- P1. 125M/2.5B tokens, 3:1 GDN hybrid: Block AttnRes gains >= 0.015 nats over pre-norm (paired, 2 seeds),
  and G-AttnRes recovers >= 80% of that gain with <= 30% of Block AttnRes's depth-source memory.
- P2. In the trained hybrid Block/Full AttnRes, depth-attention mass on global-layer outputs from linear
  layers averages >= 0.5 (uniform share 0.25); in the dense twin a matched random 25% layer subset receives
  <= 0.35.
- P3. Interaction: Delta_hyb - Delta_dense >= 0.008 nats at iso-parameters/tokens across 5 seeds (paired).
- P4. In hybrid mHC and GR twins, the dominant stream/branch (2606.03483 diagnostics) is the one carrying
  global-attention outputs, and restricting that stream/branch to global-layer writes costs <= 0.005 nats.
- P5 (secondary, parallel data). JSD over depth between alpha of aligned tokens in translation pairs is
  <= 0.5x the JSD between random token pairs at matched position; if so, depth routing is a free
  cross-lingual probe (bookmarks G2).

**Kill conditions.** G-AttnRes recovers < 50% of the gain or alpha mass on G <= 0.30 (near uniform) —
skip-read hypothesis dead; Delta_hyb <= Delta_dense — no hybrid-specific mechanism (depth operators fix
pre-norm dilution generically); Block AttnRes gain <= 2x the seed SD from the same grid — depth operators
unresolvable at 125M (report the seed-variance atlas, G20).

**Cheapest decisive pilot.**
- Phase 0 (CPU): exact-equivalence doctors (G-AttnRes with all layers as sources == Full AttnRes to 1e-6;
  Block AttnRes with block size 1 == Full AttnRes; nano-k3 already reports the latter); a dilution
  calculator giving the effective weight of layer-4k outputs in h_l under pre-norm from measured update
  norms; two-forward-pass causality audit of the fla AttnRes (Gluon) kernel.
- Phase 1 (<= 15 GPU-hours): 125M 3:1 GDN hybrid arms {pre-norm, Block AttnRes N=6, G-AttnRes} + dense twin
  arms {pre-norm, Block AttnRes} (`smollm2-135m` layout) x 2 seeds = 10 runs x ~1.3 GPU-h = ~13 GPU-h;
  alpha-mass and JSD probes on parallel sentences ~1 GPU-h; matched-random-subset AttnRes arm if budget
  remains.
- Phase 2 (the G9 comparison, ~40 GPU-h): 350M, 5 seeds, add Full AttnRes, mHC + mHC-lite, Gated Residual,
  GR-anchor, RD-AttnRes, Delta AttnRes, MHAR; SWA+sinks hybrid twin to test whether anchor skip-read
  appears with sliding-window locals.

**Controls.** Mandatory 2026 depth operators: Qwen Gated Residual (2608.30320), mHC (2512.24880) and
mHC-lite (2601.05732); Block/Full AttnRes (2603.15031); strongest published variants RD-AttnRes
(2608.01075, its 5-seed paired protocol adopted), Delta AttnRes (2605.18855), MHAR (2607.27230);
iso-parameter and iso-FLOP twins (AttnRes adds one d-vector per layer; mHC/GR add branch parameters — match
by width); dense-transformer twin for the interaction; matched-random-25%-subset AttnRes ("any sparse source
set works" control); stream-collapse diagnostics (2606.03483); startlux 340M/1.3B pre-norm hybrids
(2608.12149) as released references; two-forward-pass audit (2608.22876); SWA+sinks hybrid twin
(2608.28444); per-arm HP search (2608.11859); generation-based evaluation; early extension probe.

**Kevin advantage.** fla >= 0.5.2 ships AttnRes (Gluon backend) plus GDN/KDA in one library; the harness's
seed/checkpoint contract fits a 5-seed grid; parallel translation data makes P5 (depth-routing
equivariance) a probe no one else has framed. Honest: the core interaction test is runnable by any
academic lab; the advantage is the parallel-data probe and the willingness to publish the seed atlas.

**Collision risk: medium.** SANA-Video 2.0's authors already state the anchor-reuse interpretation for a
video DiT; Kimi and Qwen have the compute; the AttnRes-variant stream (RD, Delta, MHAR, Dual, Low-Rank,
Multi-Gate, two probe papers) publishes monthly. Searches run (hostsearch, 2026-09-01): arXiv
`(abs:"attention residuals" OR abs:"hyper-connections" OR abs:"gated residual") AND (abs:hybrid OR
abs:"linear attention" OR abs:"Gated DeltaNet")` -> 21 results, relevant only Qwen3.8-Next, DeepSeek-V4,
SANA-Video 2.0 (none isolates global-layer sources or a dense interaction); arXiv `abs:"attention
residuals" OR ti:"attention residual"` -> 25 newest incl. RD/Delta/MHAR/Dual/Low-Rank/Multi-Gate variants and
two probe papers, all dense; HF papers `attention residuals hyper-connections gated residual` -> 20 (same
set + mHC-lite, JPmHC, xHC, Frac-Connections); DuckDuckGo `"attention residuals" OR "hyper-connections"
hybrid linear attention global layers depth routing ablation 2026` -> no results returned. No direct prior
art found through 2026-09-01 under this coverage for the restricted-source causal test or the hybrid-vs-dense
interaction.

**Monitorability and safety.** Depth-attention weights are an inspectable routing tensor; 2606.13168 warns
routing mass is not causal contribution, which is why the restricted operator, not the weights, carries the
claim. No CoT/action-monitorability effect. Open data only.

**Negative-result value.** If the gain is not anchor-driven, the grid still delivers G9's first independent
iso-compute multi-seed comparison and a seed-variance atlas (G20); a null interaction tells hybrid builders
that AttnRes/GR/mHC are generic dilution fixes, not hybrid-specific ones, which changes where to spend the
depth-memory budget.

**Targets gaps:** G9, G2, G12, G20.

---

## Candidate 3 (moonshot) — `state-read-mtp-drafts`

**Claim.** An MTP head that reads the backbone's recurrent states directly (no attention of its own) gives
an O(1)-per-token draft whose acceptance approaches the shipped full-attention MTP head at short context
and beats windowed drafts at long context, and joint MTP training through such a head shapes the linear
layers' state toward longer retention horizons — MTP as state-shaping, not only a draft.

**claim_scope:** architecture-causal.

**Mechanism.** Backbone: 3:1 hybrid with linear layers l in Lin holding per-head states S_t^l in
R^{d_k x d_v} (GDN/KDA) and global layers holding KV caches. Standard MTP head (K3, Qwen3.5/3.8): a full
block taking [h_t^L ; e(x_{t+1})] and predicting x_{t+2}; its attention read costs O(T) per draft step at
context T, which Windowed-MTP (2607.21535) shows dominates draft cost at 1M and "sharpens under
hybrid/linear-attention targets". State-read head: z_t = MLP([h_t^L ; e(x_{t+1}) ; r_t]) with
r_t = concat_l ( q_l(x_{t+1})^T S_t^l ), a query-projected read of every linear layer's state using the
just-drafted token's embedding as query; cost O(|Lin| d_k d_v) per token, independent of T. For k-step
drafts the read uses a one-step delta-rule roll-forward S~ = a S_t^l (I - beta k k^T) + beta v k^T on the
drafted token (exact by the same algebra TreeWY uses for verification). Training objective
L = L_NTP + lambda L_MTP(state-read): the MTP gradient flows into S_t through the read, pressuring decay and
erase gates to retain information useful two tokens ahead ("state shaping"), measured as the DASC retention
horizon T_ret = 1/(1 - E[a]) per unit (2608.30386) and as MQAR accuracy at long lag. The state summarises
the whole context, whereas a StreamingLLM window discards it, so acceptance should hold at long context
where windowed drafts lose recall-dependent proposals.

**What is new (deltas vs three closest priors).**
1. Windowed-MTP (2607.21535, 2026-07-23, opened): applies a sliding window + sink to the draft's attention
   only; training-free, lossless; "+28% to +44%" lower per-decode-step cost at 1M on Qwen GDN-MoE 35B/122B
   and a Mamba2-hybrid NoPE 120B. Delta: the draft still attends; here the draft has no attention and reads
   the recurrent state instead, so its cost is O(1) and its context view is the full state, not a window.
2. Component-Aware Self-Speculative Decoding in Hybrid LMs (2605.01106, 2026-05-01, opened): the untrained
   linear/SSM subgraph as a zero-cost draft gives alpha = 0.68 (k=2) in parallel hybrids (Falcon-H1) but
   alpha = 0.038 in sequential hybrids (Qwen3.5), "an 18x gap". Delta: a trained head that reads the state,
   with the causal control that the 0.038 negative predicts failure if the state is not readable — this is
   the pre-registered kill.
3. SpecLA (2607.16673, 2026-07-18, opened): speculative runtime for stateful linear-attention targets with
   topology-aware verification, compact factors to recover accepted states, and "a target-aligned
   EAGLE-style drafter"; 1.70x on GDN-1.3B. Delta: SpecLA is a runtime with an EAGLE-style (attention-bearing)
   drafter; the state-read head is a different draft interface, and the state-shaping claim (MTP changes
   retention horizons) is a training-time architecture claim, not a serving claim.
Also opened/cited: Mamba Drafters (2506.01206; external Mamba drafter, cross-target); TreeWY (2608.20961;
exact branch-structured WY verification for GDN hybrids — used for k>1 verification); DART (2608.02032;
attention over KV pairs decoded from Mamba-2 chunk states inside the backbone — evidence that recurrent
states are decodable, not a draft head); AdaMTP (2608.00434; dense 7–12B backbones; MTP gradients "interfere
with the model's core capabilities" — the interference risk the iso-FLOP MTP-off arm tests); MTP-D
(2603.23911; +7.5% acceptance, looped extension); DASC (2608.30386; retention horizons derived from weights,
2.63x checkpoint compression). Synthesis axis H names exactly this gap: "how a draft should read recurrent
state at long context is open".

**Falsifiable predictions.**
- P1 (frozen screen). On `qwen3.5-4b` (registry id; frozen backbone; shipped MTP head as comparator), a
  state-read head trained on <= 1B tokens reaches mean accepted length >= 0.9x the shipped MTP head at 4K
  context (greedy, k=3); a Medusa-style MLP head on h_t^L alone reaches <= 0.75x.
- P2 (long context). At 64K–128K on the same model, state-read acceptance >= Windowed-MTP acceptance + 5%
  relative, with per-draft-step cost flat in T (<= 1.05x its 4K cost) while the full-attention MTP head's
  cost grows linearly.
- P3 (state shaping, from scratch). 125M 3:1 hybrids, MTP-on (state-read) vs MTP-off at iso-tokens: median
  retention horizon of linear-layer units rises >= 1.5x; MQAR at lag 1K improves >= 5 points; NTP loss within
  +/- 0.005 nats (no AdaMTP-style interference at this scale).
- P4 (causal control). Replacing the state read with a permuted or other-sequence state at inference
  collapses acceptance to <= 0.5x the full MTP head, showing the acceptance comes from state content.

**Kill conditions.** P1 fails (< 0.75x the shipped head) — trained state reads carry too little next-token
information and 2605.01106's negative generalises; publish the negative. P3 fails with MTP-on shortening
horizons or costing >= 0.01 nats — MTP is a tax on small hybrids (an answer to G11 either way). Acceptance
at 128K below Windowed-MTP — the state does not preserve draft-relevant context.

**Cheapest decisive pilot.**
- Phase 0 (CPU): exactness doctor for the one-step roll-forward read (recurrent vs chunkwise state equal to
  1e-6); off-by-one leakage doctor guaranteeing the head never sees S_{t+1} (the SR-TTT lesson) via the
  two-forward-pass audit (2608.22876); acceptance-length estimator validated on synthetic draft/target
  distributions.
- Phase 1 (frozen, <= 6 GPU-hours): `qwen3.5-4b` frozen; train three heads on 1B tokens (state-read,
  Medusa-MLP, EAGLE-style one-layer attention), ~1.5–2 GPU-h each; evaluate acceptance at 4K/32K/128K against
  the shipped MTP head and a Windowed-MTP variant of it.
- Phase 2 (from scratch, <= 10 GPU-hours): 125M 3:1 GDN hybrids {MTP-off, MTP full-block, MTP state-read} x 2
  seeds ~ 8 GPU-h + retention-horizon and MQAR probes. Total <= 16 GPU-hours.
- Phase 3 (if P1–P3 hold): `kimi-linear-48b-a3b-base` (KDA, NoPE) state-read head at 48B for a scale check;
  350M x 5 seeds; TreeWY-verified k=4 trees.

**Controls.** Shipped Qwen3.5 MTP head; Windowed-MTP draft (2607.21535); Medusa-style and EAGLE-style heads;
component-aware self-speculation (2605.01106) and LayerSkip; SpecLA drafter (2607.16673); TreeWY exact
verification for k>1 (2608.20961); MTP-off iso-token and iso-FLOP arms (head FLOPs matched by a wider MLP);
retention-horizon measurement per DASC (2608.30386); for the MQAR/recall claim the mandatory baselines
QED (2608.13668) and MARCH (2608.12435) on MTP-off backbones and the SWA+sinks hybrid (2608.28444);
two-forward-pass causality audit; generation-based acceptance (not perplexity); per-arm HP search.

**Kevin advantage.** Registered `qwen3.5-4b` (native transformers, GDN hybrid with MTP head) for the
frozen screen and `kimi-linear-48b-a3b-base` for a KDA-state read at scale (bf16 fits one node for head
training); 8xH100 for the from-scratch grid. Tinker exposes no hidden states (tinker-feedback #141), so there
is no Tinker lane — honest limit. Any lab with one H100 can run Phase 1; the advantage is modest.

**Collision risk: high.** Speculative decoding for linear-attention targets is an active systems area
(SpecLA, KVBuffer 2605.19049, TreeWY, Windowed-MTP, Mamba Drafters, SpecMamba) and MTP variants publish
monthly (AdaMTP, LoopMTP, MTP-D); a state-read head is an obvious next step for the SpecLA/TreeWY groups.
Searches run (hostsearch, 2026-09-01): arXiv `abs:"multi-token prediction" AND (abs:"linear attention" OR
abs:"state space" OR abs:"recurrent state" OR abs:hybrid OR abs:DeltaNet)` -> 11 results, none a state-read
head (Windowed-MTP, Nemotron 3 Ultra, Nemotron-Labs Puzzle, MiMo-V2-Flash, Mellum2, AngelSpec); arXiv
`abs:"speculative decoding" AND (abs:"recurrent state" OR abs:"linear attention" OR abs:"Gated DeltaNet" OR
abs:Mamba) AND (abs:draft OR abs:drafter)` -> 9 results, none reading the target's recurrent state as draft
input; DuckDuckGo `multi-token prediction draft head reads recurrent state hybrid linear attention long
context 2026` -> no results returned; OpenReview `multi-token prediction hybrid linear attention draft` ->
ids unresolved (titles not returned). No direct prior art found through 2026-09-01 under this coverage for a
recurrent-state-read MTP head or for MTP-induced retention-horizon change.

**Monitorability and safety.** Speculative decoding is lossless with respect to the verified target
distribution, so no change to CoT or action monitorability; the state-read head doubles as a probe of what
the recurrent state encodes (a positive for interpretability). Open data only.

**Negative-result value.** Settles G11 (does MTP help or hurt <= 1B hybrids) either way; a failed state read
shows that trained heads cannot linearly decode next-token information from delta-rule states, strengthening
2605.01106 and informing DASC/Tail-Replay-style compression about what the state actually carries; the
frozen-head recipe is reusable for any hybrid.

**Targets gaps:** G11, G12, G20.

---

## Occupancy check against the brief

- Not re-proposing: hybrid ratios, sparse-for-global substitution, another delta-rule gate, another depth
  operator variant as a product, generic MTP objective shaping, NoPE as a design choice. G-AttnRes and the
  sticky-decay subset are test instruments (restrictions/initialisations of shipped operators) whose payoff
  is the mechanism answer; their memory/design benefits are secondary.
- Rejected table (08-10): none of the three touches "better generic linear attention", static mixtures,
  surprise-gated memory, latent loops, diffusion+MoE, graph RAG, LoRA porting, Coded Delta, or harness layers.

## Coverage limits for this note

- WebSearch budget exhausted before this cell; discovery relied on 12 hostsearch calls (arXiv API via the
  H100 host, HF papers, OpenReview, DuckDuckGo — DDG returned no parsed results for all three queries,
  OpenReview returned unresolved ids), the cell notes' recorded queries, and 28 WebFetch abstract pages.
- Abstract-level only for every prior opened here; full texts of the K3, Qwen3.8-Next, AttnRes, mHC and
  SANA-Video 2.0 reports were not read by this cell (seq-operators read K3/AttnRes/Qwen3.8 full text and is
  cited for table numbers). Semantic Scholar unavailable (429); no citation-graph check.
- Not searched: Chinese-language sources, Google Scholar, ACL Anthology, ICLR 2027 submissions, closed-lab
  systems, the MiniMax M3 report, the Qwen3.8-Flash-Next GitHub tech_report.pdf.
- GPU-hour figures are estimates from the benchmarks-eval cell's "~1 GPU-hour per 125M/20N-token run"; nothing
  was executed on the node. The Kimi-Linear-48B-A3B-Base NoPE attribution is taken from the seq-operators
  note (F1/F24), not re-verified against the Kimi Linear paper by this cell.
- Collision log: design/J-collision-search.log (raw hostsearch output, 12 calls, 4 s spacing).
