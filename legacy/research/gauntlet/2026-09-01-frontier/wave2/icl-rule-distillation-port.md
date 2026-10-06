# icl-rule-distillation-port — wave-2 repair (2026-09-01)

Repair owner note. Wave-1 verdicts: novelty NOT refuted (0.6, with caveats), identification REFUTED (0.82),
feasibility REFUTED (0.80). Every objection is mapped to a fix or an accepted limitation in §12. The mechanism's
delta (the object ported is the WRITE RULE distilled from a transformer's in-context behaviour, not weights or state)
is kept; everything around it — endpoint, scale, substrates, controls, data, budget — is rebuilt.

## 1. Claim (one line)

On matched iso-corpus / iso-tokenizer / iso-token-budget ladders of frozen >= 1.3B bases, the *content-dependent*
part of a softmax transformer's in-context update — measured as label-dependent in-context gain on task families the
training loss never sees — can be distilled into an explicit rank-8 fast-weight write rule at a canonical 64-d
interface that (i) beats the strongest derived rule (dense-preconditioned GD with learned schedule) at the *same
learned interface and compute*, and (ii) frozen, attached strictly after recurrent sublayers through label-free maps,
reproduces a measurable fraction of the native content-dependent in-context gain of pure-recurrent bases with no
demonstrations in the window; a within-hybrid site-type factor and a same-family port separate "ports across
operators" from "works where softmax exists"; a held-out-language write-A/read-B probe measures whether the rule's
writes carry content beyond the frozen encoder's own language invariance.

**claim_scope.** architecture-causal.

## 2. Mechanism

Frozen source transformer T. Episode = demonstrations c_1..c_8 (formatted (x_i, y_i)) and probe queries q in Q_i
(held-out queries of the same task). Two structurally separated passes make causality a property of the code, not a
penalty:

- Pass W (write). Demonstration c_i is encoded alone by the frozen base; pooled residuals at K = 4 sites
  (depth fractions 0.25/0.5/0.75/1.0, always the residual stream *after a recurrent sublayer* on non-transformer
  bases) give hbar^k(x_i), hbar^k(y_i). Canonical key/value: k_i = P_b^k hbar^k(x_i), v_i = P_b^k hbar^k(y_i),
  error e_i = v_i - M_i^k k_i. The shared rule R_theta (2-layer MLP, width 256, ~1e5 params, shared across sites and
  bases) emits (rho_i in [0,1], eta_i >= 0, u_i, w_i in R^64) from (k_i, v_i, e_i, M_i k_i, ||k_i||, i, pooled
  statistics of M_i); update M_{i+1}^k = Pi_8[rho_i M_i^k + eta_i u_i w_i^T] (Pi_8 = rank-8 truncation).
- Pass R (read). Probes are processed with M_i frozen: h^k <- h^k + Q_b^k M_i^k P_b^k h^k at each site. Probes never
  enter Pass W, so no read can depend on a probe's own tokens; the two-forward-pass prefix-invariance audit
  (read with the probe present vs absent from the write stream, fp32 tolerance) runs as a CI gate on every arm.
- Interface. M^k in R^{64x64} rank-8; P_b^k in R^{64 x d_b} and Q_b^k in R^{d_b x 64}, both rank-8 factorized,
  the only base-specific parameters (about 2.7e5 at d_b = 2048 over four sites).
- Derived-rule superset at the same interface (R_GD): u_i = W e_i, w_i = k_i, eta_i = eta_0 (i+1)^{-gamma} /
  (||k_i||^2 + eps)^beta, rho_i = rho_0, with learned W in R^{64x64} and scalars (eta_0, gamma, beta, rho_0). It
  contains the delta rule (W = I, beta = gamma = 0), Kaczmarz normalisation (beta = 1; 2605.08587), OSDN diagonal
  preconditioning (W diagonal; 2605.13473) and the Falcon normalised rules (2608.27763) as special cases and is
  trained with the same loss, the same P/Q co-fitting and the same compute as R_theta.
- Distillation (source only, distillation families D only): L_dist = sum_i sum_{q in Q_i}
  KL( p_T(.|q, c_{<=i}) || p_{T,M_i}(.|q) ), truncated BPTT through the 8 writes, over theta (or W and the four
  scalars), P_T, Q_T. No causality penalty: causality is structural (above).
- Cross-lingual equivariance (Stage D only): for human-translated parallel demonstrations (c_i, c_i^B),
  L_eq = ||Delta M(c_i) - Delta M(c_i^B)||_F^2 on TRAINING language pairs only; evaluation is behavioural on
  HELD-OUT languages (write in English, read in language B).
- Port to target b': freeze the rule; fit P_b', Q_b' label-free on FineWeb-Edu text containing no task family:
  P_b' by ridge regression of span-pooled target residuals onto the source's canonical keys
  (min sum_s ||P_b' hbar_b'(s) - P_T hbar_T(s)||^2 + lambda ||P||^2, 2k sequences x 512 tokens); Q_b' by functional
  matching — inject a fixed bank of random rank-1 M's at the sites of both models and fit Q_b' so the target's
  next-token log-prob shift matches the source's (KL over a 256-token window). Every rule (R_theta, R_GD, random-theta)
  gets its own source distillation and its own port by the identical procedure.
- Logged per write: effective step s_i = eta_i ||u_i|| ||w_i||, rho_i, hash-chained write log, reset attestation.

## 3. Endpoints (held-out; the training loss never sees them)

Per base b and family F in the held-out set H (task categories and formats disjoint from D):
- G_native(b,F) = acc(gold 8-shot) - acc(zero-shot with contextual calibration, 2102.09690)
- G_TL(b,F) = acc(gold 8-shot) - acc(random-label 8-shot)   [content-dependent gain; the TR/TL decomposition of
  2305.09731 / 2202.12837; for binding and function tasks "random-label" = outputs shuffled across inputs]
- r_TL(rule; b,F) = [acc(rule, gold writes, no context) - acc(rule, shuffled writes, no context)] / G_TL(b,F)
- r_native(rule; b,F) = [acc(rule, gold writes, no context) - acc(calibrated zero-shot)] / G_native(b,F)
Primary endpoint: mean r_TL over ELIGIBLE held-out families, paired cluster bootstrap over families x seeds.
Eligibility gate (pre-registered): G_TL(T,F) >= 10 points with the 95% CI excluding +5 on >= 400 queries; ineligible
families are reported, not averaged. Accuracy and random-label episodes appear nowhere in any training objective.

## 4. What is new (downgraded to a recombination statement)

Every component has a prior: context -> per-model weight updates (Generative Adapter, Doc-to-LoRA, Can GD Simulate
Prompting), analytic ICL-as-low-rank-patch (Learning without training), state transfer between frozen LMs
(Cache-to-Cache, XKV, KV translation, Latent Cache Flow), learned or derived fast-weight rules within one family
(TTT, Modular TTT, Falcon, Fast Weight Layers, SRWM), cross-architecture WEIGHT distillation (Attention to Mamba).
The delta is the transferred OBJECT — the write rule (HOW), distilled from one transformer's in-context behaviour,
frozen, and attached to bases of other operator families that have no KV cache to receive state — plus two tests with
no located precedent: the head-to-head against a preconditioned-GD superset at the same learned interface, and the
write-A/read-B held-out-language probe. No direct prior art found through 2026-09-01 under the coverage in §11.
Pre-registered collapse: if R_theta ties a label-trained sibling rule at the same interface, the result collapses into
Fast Weight Layers / SRWM ("a small learned fast-weight sidecar helps in-context adaptation") and is reported as such.

## 5. Closest priors (all opened; URL, date, delta)

1. Can Gradient Descent Simulate Prompting? — https://arxiv.org/abs/2506.20989 — 2025-06-26 — meta-trained
   same-model gradient step emulates conditioning; not externalised, not ported. Here: externalised rule, canonical
   interface, ported frozen, compared with a preconditioned-GD superset at equal interface and compute.
2. Learning without training: the implicit dynamics of ICL — https://arxiv.org/abs/2507.16003 — 2025-07-21 (v4
   2026-06-02) — analytic low-rank MLP patch inside one block; single model. Here: learned rule by behavioural
   distillation, cross-family test.
3. Generative Adapter — https://arxiv.org/abs/2411.05877 — 2024-11-08; Doc-to-LoRA — https://arxiv.org/abs/2602.15902
   — 2026-02-13 — context -> weight-update generators for one model (WHAT, per model). Here: the object is the rule,
   the state is base-independent.
4. Cache-to-Cache — https://arxiv.org/abs/2510.03215 — 2025-10-03; XKV — https://arxiv.org/abs/2608.20617 — 2026-08;
   KV translation — https://arxiv.org/abs/2608.30963 — 2026-08 — transfer of KV/latent STATE between frozen LMs.
   Here: the rule is transferred; the targets have no KV cache.
5. Modular TTT — https://arxiv.org/abs/2608.07110 — 2026-08-07; Falcon rules — https://arxiv.org/abs/2608.27763 —
   2026-08 — learned/derived inner rules within one family, not distilled from a transformer, not transferred.
6. Fast Weight Layers — https://arxiv.org/abs/2212.02475 — 2022-12-05; SRWM — https://arxiv.org/abs/2202.05780 —
   2022-02-11 — learned fast-weight sidecars on a base (the weaker occupied claim we collapse into if the sibling ties).
7. Algorithm Distillation — https://arxiv.org/abs/2210.14215 — 2022-10-25 — algorithm INTO a sequence model
   (reverse direction).

## 6. Falsifiable predictions

- P1 (identifiability, Stage B, source only, held-out families): mean r_TL(R_theta) >= 0.60; r_TL(R_theta) -
  r_TL(R_GD) >= 0.15 with the paired 95% cluster-bootstrap CI excluding 0; r_TL(random-theta with fitted P/Q) <= 0.20;
  and R_theta exceeds the label-trained sibling by >= 0.10 (else the collapse in §4 applies). Embarrassing if R_GD ties.
- P2 (port, Stage C): on >= 4 of the 6 pure-recurrent 1.3B-100B targets, ported r_TL(R_theta) >= 0.40 and exceeds
  ported R_GD by >= 0.10; the same-family port transformer-1.3B -> transformer-2.7B gives r_TL >= 0.60 (upper
  reference); inside startlux gdn-1.3b-isp-hybrid-3to1-50b, after-GDN sites recover >= 0.7x the after-attention sites
  (if <= 0.5x, "works only where softmax exists" wins).
- P3 (content vs surface, Stage D, held-out languages sw/hi/th/ar/tr/id/vi/ja): with lambda_eq = 0 the write-en/read-B
  gap of R_theta (r_TL(A/A) - r_TL(A/B)) is within 0.10 of R_GD's gap (the encoder's own invariance explains it); with
  lambda_eq > 0 trained on en-{de, es, zh} only, the held-out-language gap shrinks by >= 0.15 at <= 0.05 monolingual
  r_TL cost. If the lambda_eq = 0 gap is already <= 0.05, P3 is declared null (encoder already invariant).
- P4 (dynamics signature, held-out episodes): s_i decays with i (Spearman rho <= -0.5 over i = 1..8) and on
  key-collision episodes (same key, new value) the emitted rho_i for the colliding direction falls below 0.7 — a
  content-conditional forgetting policy that R_GD (constant rho) cannot express. Embarrassing if s_i is flat or rho_i
  is content-blind.

## 7. Kill conditions

- K1: Stage B r_TL(R_theta) - r_TL(R_GD) < 0.05 or CI includes 0 -> at a 64-d rank-8 interface the transformer's
  content-dependent in-context update is preconditioned GD; publish as a behavioural ICL-as-preconditioned-GD
  confirmation on an iso-ladder at 1.3B and stop.
- K2: no held-out family passes the eligibility gate on the source -> unmeasurable at this scale; report, stop
  (escalation to the Moonlight -> Kimi-Linear pair is a new proposal, not a continuation).
- K3: ported R_theta <= ported R_GD on every pure-recurrent target, or after-recurrent sites <= 0.5x after-attention
  sites in the hybrid -> the rule does not port across operators.
- K4: any audit failure — prefix-invariance audit non-identical, a poisoned demonstration persisting after the declared
  reset, or random-theta >= 0.5 x R_theta (reservoir explains it).
- K5: lambda_eq costs > 0.10 monolingual r_TL or fails to shrink the held-out-language gap.

## 8. Cheapest decisive pilot (public data only; GT data optional upgrade)

**Stage A (CPU, fp64, 0 GPU-h) — algebra, causality and regime doctors.** (a) Synthetic ICL in the FINITE-task-prior
regime of Raventós et al. (2306.15063): a 2-layer softmax transformer pretrained on a small task set behaves as the
discrete Bayesian (dMMSE) predictor, not ridge/GD, so delta/Kaczmarz/preconditioned-GD rules are provably not the
implicit algorithm; distil R_theta with a 16-d state and check it tracks dMMSE while R_GD tracks ridge; if R_theta
cannot beat R_GD here the parameterisation is inadequate — kill before any GPU. (b) Prefix-invariance and
probe-absence audits on the two-pass code path. (c) Tokenizer doctor: assert piece-id identity across all fla-hub
1.3B-100B and startlux tokenizers (tokenizer.model blob dadfd56d7667 identical; tokenizer.json serialisations differ).
(d) Rank/algebra doctor for Pi_8 and the P/Q factorisation. (e) Pythia-160m/Mamba-130m are a loader smoke test only.

**Stage B (<= 4 GPU-h incl. reserve) — identifiability on the source; the kill screen.** Source
fla-hub/transformer-1.3B-100B (sha d6f66f41…, MIT, SlimPajama-627B, 100B tokens, 24 x 2048, 32k vocab).
B0 denominator audit (gold / random-label / calibrated zero-shot) on 14 candidate families. B1 distillation runs
(6k episodes x 2 epochs each): R_theta x3 seeds, R_GD x3, random-theta x2, label-trained sibling (same interface,
same episodes, cross-entropy on labels) x2. B2 special-case derived rules (delta, Kaczmarz, OSDN-diag, Falcon) on
R_GD's fitted interface with a 16-point scalar grid on D. B3 held-out evaluation. Stop here if K1/K2 fire.

**Stage C (<= 2.5 GPU-h) — port on the iso-ladder.** Targets fla-hub/{delta_net, gla, retnet, hgrn2, gsa,
mamba}-1.3B-100B (sites strictly after recurrent sublayers); same-family reference fla-hub/transformer-2.7B-100B;
site-type factor inside startlux-models/gdn-1.3b-isp-hybrid-3to1-50b (attention at 0-based layers 2,5,8,11,14,17,20,23;
site set A after layers 5/11/17/23 = attention, site set G after 4/10/16/22 = GDN, matched depth). Label-free P/Q on
FineWeb-Edu sample-10BT; evaluation on H with gold vs shuffled writes.

**Stage D (<= 2.5 GPU-h, gated on B) — content vs surface within one multilingual base.** Qwen/Qwen3-1.7B-Base (sha
ea980cb0…, Apache-2.0); distil with lambda_eq in {0, lambda} on SIB-200 + MASSIVE English demonstrations and en-{de,
es, zh} parallel pairs; evaluate write-en/read-B on held-out languages and on the held-out dataset (train L_eq on
SIB-200 topics, test on MASSIVE scenarios, and vice versa). No port, so no same-lineage-port confound.

**Stage E (<= 3.5 GPU-h, gated on C) — independent-ladder replication.** Pile 300B / GPT-NeoX triplet from the
Mamba-2 paper, all Apache-2.0: state-spaces/transformerpp-2.7b (source) -> state-spaces/mamba2-2.7b (SSD),
state-spaces/mamba2attn-2.7b (attention at 0-based layers 9,18,27,36,45,56 of 64; second site-type test),
EleutherAI/pythia-2.8b (independent transformer, same tokenizer/corpus, different recipe: same-family reference).
Needs pinned mamba_ssm / causal-conv1d wheels; original-format checkpoints.

Full program <= 11.1 GPU-h (ledger §9); the decisive pilot (A+B+C) <= 6 GPU-h; the kill screen alone (A+B) <= 4.

## 9. Budget ledger (cited throughput, 25% reserve per stage)

Anchor: llm.c GPT-2 1.6B on 8xH100 trains at 381,690 tok/s at 47.4% bf16 MFU (karpathy/llm.c discussion #677;
~47.7k tok/s/GPU; ~469 TFLOPS/GPU effective). Our passes are HF/fla eager code with residual hooks, short sequences
and small batches, so we assume 25% MFU = 247 TFLOPS/GPU (about half the anchor). The Gated DeltaNet paper's Fig. 3
(https://arxiv.org/abs/2412.06464) puts DeltaNet/GDN training throughput slightly below Mamba2 with Transformer++
(FlashAttention-2) fastest at 2K, so recurrent targets get no speed credit. FLOPs/token: teacher forward 2N;
frozen-base forward + activation-backward 4N (no weight gradients); evaluation forward 2N. Episode = 384 demonstration
tokens + 8 steps x 8 probes x 28 tokens = 2,176 tokens.

| Stage | Item | FLOPs | GPU-h |
|---|---|---|---|
| B0 | 14 fam x 3 cond x 400 q x 700 tok x 2N(1.3e9) | 3.1e16 | 0.035 |
| B1 | 10 runs x 12k episode-passes x 2,176 tok x 6N | 10 x 2.0e17 | 2.30 |
| B2 | 4 rules x 16 grid x 6 fam x 200 q x 500 tok x 2N | 1.0e17 | 0.11 |
| B3 | 23 passes x 8 fam x 400 q x 600 tok x 2N | 1.2e17 | 0.13 |
| **B total** | x1.25 reserve | | **3.2** |
| C-align | 72 fits (9 target-configs x 8 rule-seeds) x 1.05e6 tok x (4N_t + 2N_s) | 7.0e17 | 0.79 |
| C-eval | 10 target-configs x 19 passes x 8 fam x 400 q x 500 tok x 2N | 8e17 | 0.89 |
| **C total** | x1.25 | | **2.1** |
| D0 | 2 sets x 9 langs x 3 cond x 400 q x 600 tok x 2N(1.7e9) | 4.4e16 | 0.05 |
| D1 | 6 runs x 12k passes x 2,176 tok x 6N(1.7e9) | 6 x 2.7e17 | 1.80 |
| D2 | 6 x 2 x 2 x 9 x 300 q x 500 tok x 2N | 1.1e17 | 0.12 |
| **D total** | x1.25 | | **2.5** |
| E-distil | 4 runs x 12k passes x 2,176 tok x 6N(2.7e9) | 4 x 4.2e17 | 1.90 |
| E-align + eval | 16 fits + 4 configs x 11 passes | 6.5e17 | 0.73 |
| **E total** | x1.25 | | **3.3** |
| **Program** | | | **11.1 <= 16** |

Assumption to verify on the node in Stage A's throughput smoke (one 10-minute job): if measured MFU < 12.5%, halve
episodes (3k x 2) and drop Stage E before touching C/D; the SIGUSR1 checkpoint + fresh-job resume applies to every
truncated-BPTT run.

## 10. Controls

- Native ICL with gold demonstrations; native ICL with random/shuffled labels (task-recognition-only reference,
  2305.09731, 2202.12837); contextual-calibration zero-shot (2102.09690) as the zero-shot reference; held-out formats.
- R_GD superset at the same learned interface and compute (contains delta, Kaczmarz 2605.08587, OSDN 2605.13473,
  Falcon 2608.27763) — the decisive control; special cases with scalar grids.
- Label-trained sibling rule at the same interface (D16-style, cross-entropy on labels; separates "distilled HOW" from
  "any learned rule") — Stage B, head-to-head.
- Random-theta reservoir with fitted P/Q (randomly initialised transformers already do in-context recall, 2410.04368).
- Same-family ports (transformer-1.3B -> transformer-2.7B; transformerpp-2.7b -> pythia-2.8b) as port-fidelity upper
  references; within-hybrid site-type factor (after-attention vs after-recurrent, matched depth) on two hybrids.
- Iso-corpus / iso-tokenizer / iso-budget ladder by construction (fla-hub 1.3B-100B; Pile 2.7B triplet); the two
  ladders differ in corpus, tokenizer and recipe, so agreement across them is the replication test.
- No-update (M = 0) and alignment-only arms (inert by construction: with M = 0 the read adds exactly 0; included as a
  code-path check, not as a placebo).
- Encoder-invariance baseline for P3: R_GD with lambda_eq = 0; held-out languages and held-out dataset.
- Audits: two-forward-pass prefix-invariance (CI gate on every arm), hash-chained write log, reset attestation,
  single-adversarial-demonstration poisoning probe with persistence check across reset.
- Statistics: 3 seeds (B, C main arms), 2 seeds (random-theta, sibling, D, E); paired cluster bootstrap over
  families x seeds; Holm correction for secondary comparisons; per-arm hyperparameter search on D families only.
- Not budgeted, named: MentorPulse live mentor (2608.20927; teacher present at inference; transformers only) and
  Engram reader transfer (2608.17050) / KV translation (2608.30963) as state-transfer references — applicable only to
  same-family ports; listed as optional upper references.

## 11. Collision search (this wave) and coverage

hostsearch.sh, >= 4 s spacing, 6 calls: arXiv `abs:"in-context" AND abs:"fast weight" AND (distill*)` -> 2 hits,
neither relevant (2606.04536 parametric agent memory; 2310.12713 adversarial defense); HF papers "distill transformer
in-context learning into explicit fast-weight update rule ported across recurrent architectures" -> REFINE 2602.16704,
looped-transformer GD 2410.11268, Attention to Mamba 2604.14191, KV-Distill, Doc-to-LoRA 2602.15902, Test-Time
Training Provably Improves ICL 2503.11842, GDN — none distils an in-context update into a portable rule; arXiv
`"task recognition" AND "task learning" AND "in-context"` -> 2509.24164 (TR/TL heads via TSLA), 2406.14022, 2305.09731
(protocol sources, not collisions); arXiv `"in-context learning" AND distill* AND (state space|Mamba|linear
attention|DeltaNet) AND ("update rule"|"learning rule"|"fast weights")` -> 0 hits; OpenReview "distilling in-context
learning into fast weight update rule" -> 10 notes, 9 untitled/unreadable from this network; abs 2608.12149 (startlux
paper; controls only). Plus the wave-1 novelty refuter's 16 arXiv / 9 DDG / 5 HF / 1 OpenReview queries and 15
abstracts. Limits: Semantic Scholar unavailable; OpenReview bodies unreadable; ICLR 2027 submissions invisible;
Chinese venues not searched; several arXiv boolean queries return empty (parser/coverage gaps).
**collision_risk: high** (crowded C2C/XKV x Generative-Adapter x TTT intersection; a 2026 paper under different
vocabulary could exist).

## 12. Repairs made (wave-1 objection -> fix or accepted limitation)

Identification lens:
- I1 "few-shot gain is task recognition; a parameterised rule memorises the label/format prior; no random-label,
  held-out-format, or head-to-head label-trained control; distillation/eval family disjointness unstated" ->
  primary endpoint is r_TL (gold minus shuffled-label gain) on held-out task categories and formats; calibrated
  zero-shot reference; eligibility gate on the teacher's G_TL; label-trained sibling head-to-head in Stage B;
  distillation families D and held-out families H are disjoint by task and format and listed in §13.
- I2 "Pythia-160m's few-shot gain is within noise; P1 unmeasurable" -> bases moved to 1.3B-2.7B iso-ladders;
  families chosen where content-dependent gains are large and cited at this scale (phone-book lookup: Pythia >= 410M
  near-perfect, Mamba degrades only at >= 70 entries, 2402.01032; function-induction ICL: Mamba-2.8B on par with
  Pythia/GPT-J on 27 tasks, 2402.03170; Function Vectors suite 2310.15213); 160m/130m demoted to a loader smoke test.
- I3 "derived rules undertuned; Phase 0 linear regression is the provably-GD regime" -> R_GD superset with learned
  dense preconditioner and per-step schedule at the same interface, loss and compute is the decisive control; Stage A
  moved to the finite-task-prior regime (2306.15063) where the implicit predictor is dMMSE, not ridge/GD.
- I4 "flagship 'cross-operator' sites land on attention layers; bases unmatched (10B vs 15B tokens, tokenizers);
  Mamba prediction baseless" -> primary targets are six pure-recurrent 1.3B-100B bases on one corpus, tokenizer and
  token budget; sites strictly after recurrent sublayers; within-hybrid site-type factor (attention vs GDN sites,
  matched depth) on startlux 1.3B and mamba2attn-2.7b; same-family port as upper reference; the Mamba-specific
  ordering prediction is withdrawn (Mamba is one of six targets; binding k <= 16 stays inside its retrieval range).
- I5 "P3 is circular (lambda_eq minimises the measured quantity), encoder already language-shared, same-lineage
  pair" -> lambda_eq trained on three language pairs and one dataset, evaluated behaviourally on eight held-out
  languages and the other dataset; R_GD (no lambda_eq) is the encoder-invariance baseline; the probe runs inside one
  multilingual base (no port); the null (encoder already invariant) is pre-registered.
- I6 "random rule is a reservoir; L_cause is a soft penalty" -> random-theta arm kept with the 0.5x kill; L_cause
  dropped — probes are excluded from the write stream by construction and the two-forward-pass audit is a CI gate on
  every arm (per 2603.06642 / 2608.22876).
Feasibility lens:
- F1 "no data named" -> §13 names every dataset with URL, license and split.
- F2 "70% vs 40% of a 1-4 point gain is inside the SE" -> eligibility gate (G_TL >= 10, CI excludes 5, >= 400 queries)
  and effect sizes of 0.15 on a ratio whose denominator is >= 10 points; cluster bootstrap over families x seeds.
- F3 "Mamba-130m retrieval is weak" -> Mamba-1.3B-100B with k <= 16 entries (well inside 2402.01032's range); it is
  one of six targets, and its result is reported per family rather than as a headline.
- F4 "no calibration / label-prior arm" -> contextual-calibration zero-shot added as the zero-shot reference and the
  shuffled-label arm subtracts label-prior effects directly.
- F5 "no parallel ICL benchmark; MT translationese" -> SIB-200 and MASSIVE are human-translated parallel datasets
  (FLORES-200 sentences; SLURP utterances), no MT in the pilot; the design is symmetric across conditions; GT data
  only as an optional upgrade.
- F6 "~15 arms x 3 seeds x 4 targets plus a live mentor and a 4B hybrid in 16 GPU-h is not credible" -> FLOP ledger
  with a cited H100 anchor, 25% MFU assumption, 25% reserve per stage, staged gates (B 3.2, C 2.1, D 2.5, E 3.3 =
  11.1 GPU-h); live mentor and state-transfer references unbudgeted and named optional; Qwen3.5-4B dropped (not
  iso-tokenizer with Qwen3: tokenizer.json blobs 5f9e4d49… vs 443909a6…, 248k vs 152k vocab); one kernel package
  (fla) for Stages B-C, mamba_ssm only in gated Stage E; Docker + Slurm sbatch lane suffices for the pilot (the
  Pyxis publication-lane caveat is unchanged and stated).
Novelty lens (not refuted; caveats): what_is_new rewritten as a recombination with the transferred object as the
delta; Generative Adapter, Doc-to-LoRA, Cache-to-Cache, XKV, KV translation, Memory Decoder, Fast Weight Layers and
SRWM added to the prior list; the collapse-to-FWL/SRWM condition is pre-registered; collision risk stays high.
Accepted limitations: cross-lingual x cross-operator is only in the optional upgrade (Moonlight-16B-A3B ->
Kimi-Linear-48B-A3B-Base); fla-hub delta_net/mamba cards state no license (discovery-only until confirmed); 2 seeds on
secondary arms and in Stages D/E; the SlimPajama corpus for delta_net/mamba 1.3B is inferred from the DeltaNet paper,
not card-stated; OpenReview bodies unreadable.

## 13. Public data plan (no General Translation data required)

- Function-induction families — Function Vectors suite, https://github.com/ericwtodd/function_vectors (MIT; ICLR 2024,
  https://arxiv.org/abs/2310.15213): 29 abstractive + 28 extractive tasks. Distillation D (examples): antonym,
  present-past, english-french, capitalize_first_letter, country-currency, person-occupation, product-company,
  choose_first_of_3, animal_v_object_3. Held-out H (examples): singular-plural, synonym, english-spanish,
  country-capital, lowercase_first_letter, landmark-country, person-sport, next_item, choose_last_of_5,
  alphabetically_first_5; split fixed by task before any run; formats (separator, template) disjoint between D and H.
- Binding/lookup family — generated in-repo (phone-book style, 2402.01032 format; names/products/codes from
  combinatoric generators, no external data): D uses name->number and product->code with ":" and "->" formats; H uses
  city->zip, word->colour and a natural-sentence template, k in {8, 16}, plus key-collision episodes for P4.
- Classification (audited; expected ineligible at 1.3B per 2305.09731's ~3-5 point gold-random gap at OPT-2.7B) —
  Super-NaturalInstructions, https://github.com/allenai/natural-instructions (Apache-2.0 for task files; instance
  licenses recorded per task; HF mirror Muennighoff/natural-instructions), held-out categories only; SIB-200 English;
  MASSIVE English scenarios (18-way).
- Cross-lingual parallel demonstrations (Stage D) — SIB-200, https://huggingface.co/datasets/Davlan/sib200
  (CC-BY-SA-4.0; 205 languages; 7 topics; 701/99/204 per language; parallel FLORES-200 sentences) and MASSIVE,
  https://huggingface.co/datasets/AmazonScience/massive (CC-BY-4.0; 51 languages; 18 scenarios / 60 intents;
  ~11.5k/2k/3k per language; human translations of SLURP). Training pairs en-{de, es, zh}; held-out sw, hi, th, ar,
  tr, id, vi, ja.
- Label-free alignment stream — HuggingFaceFW/fineweb-edu sample-10BT (ODC-By 1.0), 2k x 512-token sequences per fit;
  fineweb-2 (ODC-By) reserved for any multilingual port in the upgrade.
- Optional upgrade (not budgeted): General Translation parallel demonstration sets (domain-diverse, span-aligned) as
  additional L_eq training pairs and held-out languages, under GT's own terms, never redistributed; Moonlight-16B-A3B
  (MIT, 5.7T tokens, DeepSeek-V3-style MLA MoE) -> Kimi-Linear-48B-A3B-Base (MIT, 5.7T tokens, KDA 3:1; registered)
  as the multilingual iso-tokenizer cross-operator pair (identical tiktoken.model blob b6c497a7469b; iso-active 3B).

## 14. Substrate registry (to register; 40-hex revisions from the HF API, 2026-09-01)

| id | repo | revision | license | role |
|---|---|---|---|---|
| fla-transformer-1.3b-100b | fla-hub/transformer-1.3B-100B | d6f66f4181fa669e5863327815b44533e3a395e7 | MIT | source (B, C) |
| fla-delta-net-1.3b-100b | fla-hub/delta_net-1.3B-100B | b4dcbbafd4fde802717bdec3008d4aba9cb3a1f8 | unstated | target (discovery) |
| fla-gla-1.3b-100b | fla-hub/gla-1.3B-100B | 46b15820a4df269e99aed9d709e017677c15d24b | MIT | target |
| fla-retnet-1.3b-100b | fla-hub/retnet-1.3B-100B | 7fddefc4d5e196a8d1f076bb7612d54321b3effe | MIT | target |
| fla-hgrn2-1.3b-100b | fla-hub/hgrn2-1.3B-100B | 2f413dd9b63591b9b177bbf940942ea7eb70abfe | MIT | target |
| fla-gsa-1.3b-100b | fla-hub/gsa-1.3B-100B | 1e4ffdae4fcff8c78ec06c47cd2330fcece61200 | MIT | target |
| fla-mamba-1.3b-100b | fla-hub/mamba-1.3B-100B | 49d177eaa9fedd6ff74aab256a02140299df5e99 | unstated | target (discovery; 48 layers) |
| fla-transformer-2.7b-100b | fla-hub/transformer-2.7B-100B | e29b06c913e05827bfb534844267c8d9f673feda | MIT | same-family reference |
| startlux-gdn-1.3b-hybrid | startlux-models/gdn-1.3b-isp-hybrid-3to1-50b | 0ced446e767709a15cbe2004948eac1fdea443db | Apache-2.0 | site-type factor (fla v0.5.2 pin 9c8e42e) |
| qwen3-1.7b-base | Qwen/Qwen3-1.7B-Base | ea980cb0a6c2ae4b936e82123acc929f1cec04c1 | Apache-2.0 | Stage D base |
| ss-transformerpp-2.7b | state-spaces/transformerpp-2.7b | 15a431b71c40c284138c379d07d4008a28fea397 | Apache-2.0 | Stage E source |
| ss-mamba2-2.7b | state-spaces/mamba2-2.7b | 99b226cc377d131cccc610ed4346db564f381f1e | Apache-2.0 | Stage E target |
| ss-mamba2attn-2.7b | state-spaces/mamba2attn-2.7b | 5e0f47f0003095d6bdda3ad6fd7f3f41f274accb | Apache-2.0 | Stage E site-type |
| pythia-2.8b | EleutherAI/pythia-2.8b | 2a259cdd96a4beb1cdf467512e3904197345f6a9 | Apache-2.0 | Stage E same-family reference |
| moonlight-16b-a3b | moonshotai/Moonlight-16B-A3B | 476b36a473d4467f94469414bef6cee75c9c8172 | MIT | upgrade source |
| kimi-linear-48b-a3b-base | moonshotai/Kimi-Linear-48B-A3B-Base | 3b171c17bfc4ee348599b6781a2ca8715c21c8dc | MIT | upgrade target (registered) |

Kernel pins: fla v0.5.2 (commit 9c8e42e762fce087c27b673af4922795d9edb85e) for all fla-hub and startlux models
(fla's Mamba path additionally needs mamba_ssm/causal_conv1d wheels); Stage E needs mamba_ssm for original-format
state-spaces checkpoints; Pythia/Qwen3 load natively in transformers.

## 15. Kevin advantage (honest)

The pilot substrate (fla-hub ladder, Pile triplet, SIB-200/MASSIVE) is public and not unique. Unique pieces:
(i) General Translation's parallel demonstration sets and span alignments for the L_eq upgrade beyond two template
datasets; (ii) the node plus the already-registered Kimi-Linear-48B-A3B-Base make the Moonlight -> Kimi-Linear
multilingual cross-operator pair runnable (few groups hold both the 8xH100 and a harness with residual hooks for a
48B-total KDA hybrid); (iii) the SR-TTT-derived causality doctors and the SIGUSR1-resumable truncated-BPTT harness.
Tinker cannot help (no hidden states, no optimizer access).

## 16. Monitorability and safety

A base-independent state lets one probe read the memory on every base (a monitorability gain over per-model opaque
fast weights), but hidden state replaces visible demonstrations: hash-chained write log, reset attestation, and a
single-adversarial-demonstration poisoning probe with a persistence red line are part of the protocol. Data rights:
licenses in §13-14; fla-hub delta_net/mamba cards without a license field are discovery-only until confirmed; SNI
instance licenses recorded per task; MASSIVE attribution; SIB-200 share-alike applies only if derived data were
redistributed (none is). IP: NVIDIA US20260105282A1 (gated delta networks, pending) is flagged; the sidecar rule is
not a kernel-level delta-rule contribution.

## 17. Negative-result value

K1 -> the first behavioural, causality-verified confirmation on an iso-ladder at 1.3B that the content-dependent
in-context update is preconditioned GD at a low-rank interface, which also empties D16's premise. K2 -> a measured
floor: at 1.3B-1.7B label-dependent ICL is confined to binding/function families (a quantitative addition to the TR/TL
literature on 2024-2026 bases). K3 -> the first cross-family behavioural measurement of in-context update
portability (GD emulation vs online GD vs Bayes filter). P3 null -> the frozen encoder's language invariance alone
explains cross-lingual memory readout, closing ttt-fastweights G4 cheaply.

**targets_gaps.** G5 (porting an update rule rather than weights), G2 (language-controlled probes of recurrent state
via write-A/read-B), G6 (behavioural evaluation of update-rule variants with causality audits), G7 (reset/deletion/
poisoning attestation).

**dropped: false.** The mechanism's delta (rule-as-object, cross-family port, superset-GD head-to-head, held-out-
language readout) survives the repairs without collapsing into an occupied prior; the collapse case is pre-registered.
