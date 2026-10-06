# Direction 19: Portable In-Context Write-Rule Distillation

**Status:** SPEC on 2026-09-01 — wave-2 judged 62/62; wave-3 identification repair judged 61/57 (lower authoritative 57, a 5-point dip recorded); wave-4 identification repair judged 66/65 (lower authoritative 65); wave-5 executability repair applied (CPU phase-0 doctor implemented, tested and executed on a synthetic regime; attribution tree re-tiered with CLASS_UNRESOLVED and a 4-family class minimum; contract arms synced to the registered direction-19 ids; rebuilt fla 0.5.2 image and fetched checkpoint receipts cited); not pilot-ready (Compute FAIL: no model loop, container smoke or sbatch dry-run attested; no signed provider-distinct reviews; no evidence bundle)
**Priority:** CPU phase-0 doctor (executed in wave 5), then the model-side Stage-A doctors and MFU smoke inside the rebuilt image, then a ≤ 6 GPU-hour source kill screen before any port
**Experiment contract:** `experiments/architectures/icl-rule-distillation-port.yaml`
**Proposal:** `research/proposals/2026-09-01-icl-rule-distillation-port.md`

## Research question

Is the object worth porting between sequence-operator families the *write rule*
— how a context item becomes a state update — rather than weights (Generative
Adapter, Doc-to-LoRA) or state (Cache-to-Cache, KV translation)? Concretely:
can a frozen softmax transformer's content-dependent in-context update be
distilled into an explicit rank-8 fast-weight write rule at a canonical 64-d
interface that reproduces the teacher's own held-out 8-shot predictions more
faithfully than an **iso-parameter gradient-form rule** (same MLP width and
parameter count within 1%, update direction constrained to the key, w_i = k_i)
trained at the same interface, episode mix, hyperparameter-search budget and
compute — with the win carried by the free write direction under a post-hoc
clamp ablation — and does that frozen rule keep a measurable fraction of its
fidelity when ported through label-free maps to the licensed GLA, RetNet, HGRN2
and GSA bases trained on the same corpus, tokenizer and token budget?

Claim scope is **portability-protocol** (rescoped in wave 3 from
architecture-causal: every arm is a frozen retrofit; no from-scratch matched arm
is budgeted). The pre-registered collapse is explicit: if the distilled rule ties
a sibling rule distilled by the same KL objective from a *different* transformer
teacher, the fidelity is not teacher-specific and the result is reported as a
Fast Weight Layers / SRWM-class learned ICL rule.

The residual interface (rank-8 64×64 state at four sites with base-specific
rank-8 P/Q) is Direction 16's own (`directions/16-portable-learning-dynamics.md`,
`experiments/architectures/portable-sidecar-update.yaml`), reused deliberately so
that a result here is directly a test of that direction's premise; the interface
is not part of the claimed delta.

## Mechanism

Frozen source transformer `T`. Episode = eight demonstrations `c_1..c_8 = (x_i, y_i)`
plus probe queries `q` of the same task. Two structurally separated passes:

```text
Pass W (write): c_i encoded alone; pooled residuals at K = 4 sites (depth 0.25/0.5/0.75/1.0;
                after a recurrent sublayer on non-transformer bases)
  k_i = P_b^k hbar^k(x_i)        v_i = P_b^k hbar^k(y_i)        e_i = v_i - M_i^k k_i
  (rho_i, eta_i, u_i, w_i) = R_theta(k_i, v_i, e_i, M_i^k k_i, ||k_i||, i, stats(M_i^k))
  M_(i+1)^k = Pi_8[ rho_i M_i^k + eta_i u_i w_i^T ]              (rank-8 truncation)
Pass R (read): probes never enter Pass W
  h^k <- h^k + Q_b^k M^k P_b^k h^k
Interface: M^k in R^(64x64) rank 8; P_b^k (64 x d_b), Q_b^k (d_b x 64) rank-8 factorised — the only
           base-specific parameters. R_theta: 2-layer MLP, 266 inputs, hidden 256, 130 outputs,
           ~1.02e5 parameters, shared.
Gradient-form ladder at the same interface (wave 4); every rung writes in the key direction, w_i = k_i:
  R_lin   (linear preconditioned GD, ~4.1e3 params; the wave-3 R_GD):
          u_i = W e_i,  eta_i = eta_0 (i+1)^(-gamma) / (||k_i||^2 + eps)^beta,  rho_i = rho_0
          (contains delta, Kaczmarz, OSDN-diagonal, Falcon and FAAST rules as special cases)
  R_adapt (content-adaptive preconditioned GD, iso-parameter; wave-3 Reviewer A's arm):
          (rho_i, eta_i, d_i) = MLP_psi(same inputs),  u_i = (W_0 + diag(d_i)) e_i,  hidden ~293
  R_gf    (nonlinear gradient-form rule, iso-parameter; wave-3 Reviewer B's arm; DECISIVE CONTROL):
          (rho_i, eta_i, u_i) = MLP_phi(same inputs),  w_i = k_i,  hidden ~305
  R_theta = R_gf + a free write direction w_i (the only degree of freedom outside gradient form)
  Nesting: R_lin ⊂ R_adapt (exact) ⊂ R_gf (up to shared width) ⊂ R_theta (exact)
Post-hoc clamp ablations on the trained R_theta (evaluation only):
  w-clamp: w_i := k_i      rho-clamp: rho_i := mean_i rho_i      eta-clamp: eta_i := mean_i eta_i
Distillation (source only, distillation families only, gold AND teacher shuffled-label episodes 2:1):
  L_dist = sum_i sum_q KL( p_T(. | q, c_(<=i)) || p_(T,M_i)(. | q) )      truncated BPTT through 8 writes
  every rule family: same written 4-point search (lr in {1e-4, 3e-4, 1e-3, 3e-3}) at equal dev budget
Cross-teacher sibling S_x: same student, interface, episodes, budget; KL target = transformer-2.7B-100B's ICL
Cross-lingual stage only (training pairs en-de/es/zh):
  L_eq = || Delta M(c_i) - Delta M(c_i^B) ||_F^2       evaluated write-en / read-B on held-out languages
Port: freeze the rule; fit P_b' by ridge regression of target residuals onto source canonical keys and
      Q_b' by functional matching of next-token log-prob shifts under a fixed bank of 8 random rank-1 M's,
      both on 2k x 512-token FineWeb-Edu sequences with no task family.
```

Wave-3 identification repair (both wave-2 judges' highest-impact fix, retained):
(a) teacher shuffled-label episodes in every rule's distillation stream plus a
TR-fidelity CI gate; (b) **teacher fidelity** — agreement with the teacher's own
8-shot argmax on held-out families, minus the M = 0 agreement — as the primary
endpoint, with error-agreement kappa, per-step curve distance and
order-sensitivity agreement as secondaries; (c) the G_TL ≥ 10-point eligibility
gate applied per base; (d) claim rescoped to portability-protocol; (e) the inert
site-type factor replaced by a **downstream-attention read-path ablation**;
(f) five judge-named priors added.

Wave-4 identification repair (union of both wave-3 reviewers' highest-impact
fix). Both found that R_GD (~4.1e3 params, linear in the error) against R_theta
(~1e5 params, free write) under the same KL loss could not separate "not GD"
from "not linear". Reviewer A asked for a content-adaptive preconditioned-GD arm
at iso-parameter count; Reviewer B for an iso-parameter nonlinear gradient-form
arm. Both are added as a nested ladder; **R_gf is the decisive control** because
it is the larger gradient-form class at matched capacity, so a win over it
isolates the single remaining non-GD degree of freedom (the free write
direction), which the w-clamp ablation then tests directly; R_adapt is the
attribution rung. Further: (g) a **pre-registered attribution tree** — CONFIRMED
(gap ≥ 0.10, CI excludes 0, also on the function-induction class, w-clamp costs
≥ 0.05, sibling and reservoir gates pass), UNATTRIBUTED (gap without the clamp
co-condition), INCONCLUSIVE (gap 0.05–0.10), else K1; (h) K1 redefined against
R_gf; (i) the CE-trained sibling (inert on a fidelity endpoint) replaced by the
cross-teacher KL sibling S_x with a ≥ 0.10 teacher-disagreement precondition so
K6 is live; (j) P2/K3 closed on the **four licensed targets** (3 of 4 pass,
exactly 2 MIXED, below 2 kill); (k) a written per-arm search grid at equal dev
budget; (l) the two-sided 95% t-interval on family means is decision-bearing
(re-simulated: power 0.78 at 8 families, one-directional Type-I 0.028; the
8-cluster percentile bootstrap's 0.060 demoted to a sensitivity); (m) Direction
16 discriminated; the ICL-as-GD lineage, MIRAS, test-time regression, Schlag 2021
and context distillation added after opening each abstract.

Wave-5 executability repair (union of both wave-4 reviewers' highest-impact
fix; judged 66/65 before it). Both reviewers named the same fatal defect:
nothing executable after four waves. Reviewer 2 added that the tree's stated
power (0.78) belonged to one leaf of a conjunction whose class co-condition
had power 0.21–0.48 at 3–5 class families and routed a miss to K1. Repair:
(n) Stage A(a), (b), (e), (g) are real code — `harness/icl_rule_distillation.py`
(interface, rule ladder with hand-written truncated-BPTT gradients, dMMSE regime,
exact key-span ceiling, clamp ablations, two-pass causality audit,
parameter-count and Pi_8 doctors, attribution tree and its power simulation),
executed by `scripts/run_icl_rule_distillation_doctor.py` on CPU with
NumPy/SciPy only (receipt `data/results/icl-rule-distillation-port/phase0-doctor.json`,
PHASE0_DOCTOR_PASS, 66/66 gates, ~15 s; `tests/test_icl_rule_distillation_doctor.py`,
17 tests incl. two tamper cases); (o) the class co-condition is re-tiered
(class point estimate ≥ 0.10 with a one-sided 80% lower bound above 0, at least
4 eligible function-induction families) and a miss routes to the non-kill
**CLASS_UNRESOLVED** instead of K1; the full-tree Monte-Carlo replaces the
single-leaf power statement; (p) contract arms name the registered
direction-19 ids; (q) the rebuilt fla 0.5.2 image and checkpoint receipts are
cited. Not done (needs the node or a model): tokenizer, loader, MFU and
TR-fidelity doctors on real episodes, container smoke, sbatch dry-run, bundle.

## Closest work and delta

| Prior | Source | What it does | Delta here |
|---|---|---|---|
| Can GD Simulate Prompting? | [2506.20989](https://arxiv.org/abs/2506.20989) | Meta-trained same-model gradient step emulates conditioning | Rule externalised at a canonical interface, frozen, ported across operator families, compared with an iso-capacity gradient-form ladder |
| Learning without training | [2507.16003](https://arxiv.org/abs/2507.16003) | Analytic low-rank MLP patch inside one block | Learned rule by behavioural distillation; cross-family test |
| Generative Adapter / Doc-to-LoRA | [2411.05877](https://arxiv.org/abs/2411.05877), [2602.15902](https://arxiv.org/abs/2602.15902) | Context to per-model weight update (WHAT); Doc-to-LoRA must retrain its hypernetwork per target LLM | The object is the write rule (HOW); state is base-independent |
| Cache-to-Cache / XKV / KV translation | [2510.03215](https://arxiv.org/abs/2510.03215), [2608.20617](https://arxiv.org/abs/2608.20617), [2608.30963](https://arxiv.org/abs/2608.30963) | Transfer KV or latent state between frozen LMs | The rule is transferred; targets have no KV cache |
| Modular TTT / Falcon rules | [2608.07110](https://arxiv.org/abs/2608.07110), [2608.27763](https://arxiv.org/abs/2608.27763) | Learned or derived inner rules within one family | Used as R_lin's derived special cases; never distilled from a transformer or transferred |
| Fast Weight Layers / SRWM | [2212.02475](https://arxiv.org/abs/2212.02475), [2202.05780](https://arxiv.org/abs/2202.05780) | Learned fast-weight sidecars on a base | The pre-registered collapse target (K6) |
| Trained Persistent Memory (Jeong) | [2603.22329](https://arxiv.org/abs/2603.22329), [2603.16413](https://arxiv.org/abs/2603.16413) | "Universal write rule shared across backbones + architecture-specific read paths"; fixed Hebbian aggregation, LM loss, GPT-2-124M and Flan-T5-XL only | Closest framing prior: here the rule is distilled from ICL behaviour, compared with a gradient-form ladder, ported frozen across operators, scored on teacher fidelity |
| FAAST | [2605.04651](https://arxiv.org/abs/2605.04651) | Closed-form pseudoinverse fast weights on frozen states, model-agnostic | Fixed rule; a special case in R_lin's derived-rule grid |
| Language Models Need Sleep | [2605.26099](https://arxiv.org/abs/2605.26099) | Learned local rule into SSM-block fast weights inside one trained model | Not distilled, not ported |
| Cross-model Control | [2410.17599](https://arxiv.org/abs/2410.17599) | Portable logit-shift tiny LM across tokenizers/architectures | Transfers a delta LM, not an update rule; no write/read state |
| ICLCA | [2406.02847](https://arxiv.org/abs/2406.02847) | Exact ICL-to-bias conversion in linearized transformers | Analytic, single model, no port |
| ICL-as-GD lineage (wave 4) | [2212.07677](https://arxiv.org/abs/2212.07677), [2211.15661](https://arxiv.org/abs/2211.15661), [2212.10559](https://arxiv.org/abs/2212.10559), [2309.05858](https://arxiv.org/abs/2309.05858), [2310.08540](https://arxiv.org/abs/2310.08540) | Same-model ICL ⇔ GD constructions and tests; Shen et al. give negative evidence (order sensitivity, output-distribution change) | Defines the null; none distils the update into an external rule, none uses an iso-capacity gradient-form ladder, none ports; Shen's discriminators become secondaries here |
| Write-rule taxonomies (wave 4) | MIRAS [2504.13173](https://arxiv.org/abs/2504.13173), Test-time regression [2501.12352](https://arxiv.org/abs/2501.12352) | Classify sequence models by memory, bias, retention gate, optimiser / regressor class | Name the ladder's cells; here the question is which cell a frozen transformer's behaviour occupies, measured by distillation |
| Delta-rule FWP (wave 4) | Schlag et al. [2102.11174](https://arxiv.org/abs/2102.11174) | Linear transformers as fast weight programmers with a delta-rule update | Origin of R_lin's delta-rule special case; trained end to end, not distilled |
| Context distillation (wave 4) | Snell et al. [2209.15189](https://arxiv.org/abs/2209.15189); Askell et al. [2112.00861](https://arxiv.org/abs/2112.00861) (attribution by wave-3 Reviewer B; abstract does not mention it, body not opened) | Student without context matches the teacher with context | Writes context into one model's weights; here the object is a base-independent external rule |
| In-repo Direction 16 (wave 4) | `directions/16-portable-learning-dynamics.md`, `experiments/architectures/portable-sidecar-update.yaml` | Identical rank-8 64×64 four-site interface; task-conditioned online sidecar trained on prequential outcome loss | Interface shared by design and not claimed; here KL distillation from ICL, iso-capacity ladder, fidelity endpoint, six operator families; K1 here is Direction 16's premise test |

No direct prior art found through 2026-09-01 under the recorded coverage
(H100-host arXiv relay, HF papers, Crossref, OpenReview titles, WebFetch
abstract pages, GitHub and Hugging Face metadata; wave-4: 10 abstract pages and
the HF API license re-check; Semantic Scholar, OpenReview bodies, ACL Anthology,
patents and Chinese venues not searched). Wave-2 novelty refuter: not refuted
(0.6); blind discrimination: different mechanism (0.88). PRISMA-style counts are
partial (wave-1 identified/screened unknown; wave 2: 5/5/5; wave 4: 10/10/9 + 1
caveat). Collision risk **high**; pending a signed provider-distinct audit.

## Cheapest decisive pilot

Public data only (Function Vectors MIT; in-repo binding generator;
Super-NaturalInstructions Apache-2.0; SIB-200 CC-BY-SA-4.0; MASSIVE CC-BY-4.0;
FineWeb-Edu ODC-By). General Translation parallel data is an optional upgrade
whose research-use license is unknown and must be cleared first.

Pilot checkpoints (40-hex revisions and license fields re-read through the
Hugging Face API on 2026-09-02 UTC). Registry state (wave 5): the first three
rows, `delta_net`, `mamba`, the hybrid and `Qwen3-1.7B-Base` are registered in
`models/registry.yaml` (commit 53773c3) as `transformer-1.3b-100b`,
`transformer-2.7b-100b`, `gla-1.3b-100b`, `delta-net-1.3b-100b`,
`mamba-1.3b-100b`, `gdn-1.3b-isp-hybrid-3to1-50b`, `qwen3-1.7b-base`; fetched
receipts exist on fal-h100-01 under `/home/kevin/cotcodec-runs/hf-cache/cotcodec-receipts/`
for `transformer-1.3b-100b`, `gla-1.3b-100b`, `gdn-1.3b-isp-hybrid-3to1-50b`
and `qwen3-1.7b-base` (reported by the wave-5 brief; not opened by this cell);
`retnet`, `hgrn2`, `gsa`, the state-spaces triplet and `pythia-2.8b` are not
registered, so Stages C and E cannot be enabled:

| Role | Checkpoint | Revision | License |
|---|---|---|---|
| Source (Stage B) | `fla-hub/transformer-1.3B-100B` | `d6f66f4181fa669e5863327815b44533e3a395e7` | MIT |
| Same-family reference; S_x teacher | `fla-hub/transformer-2.7B-100B` | `e29b06c913e05827bfb534844267c8d9f673feda` | MIT |
| Licensed target (P2/K3) | `fla-hub/gla-1.3B-100B` | `46b15820a4df269e99aed9d709e017677c15d24b` | MIT |
| Licensed target (P2/K3) | `fla-hub/retnet-1.3B-100B` | `7fddefc4d5e196a8d1f076bb7612d54321b3effe` | MIT |
| Licensed target (P2/K3) | `fla-hub/hgrn2-1.3B-100B` | `2f413dd9b63591b9b177bbf940942ea7eb70abfe` | MIT |
| Licensed target (P2/K3) | `fla-hub/gsa-1.3B-100B` | `1e4ffdae4fcff8c78ec06c47cd2330fcece61200` | MIT |
| Discovery-only target (never counted) | `fla-hub/delta_net-1.3B-100B` | `b4dcbbafd4fde802717bdec3008d4aba9cb3a1f8` | none stated |
| Discovery-only target (never counted) | `fla-hub/mamba-1.3B-100B` | `49d177eaa9fedd6ff74aab256a02140299df5e99` | none stated |
| Hybrid read-path ablation | `startlux-models/gdn-1.3b-isp-hybrid-3to1-50b` (attention at 0-based layers 2,5,…,23) | `0ced446e767709a15cbe2004948eac1fdea443db` | Apache-2.0 |
| Stage D base | `Qwen/Qwen3-1.7B-Base` | `ea980cb0a6c2ae4b936e82123acc929f1cec04c1` | Apache-2.0 |
| Stage E source | `state-spaces/transformerpp-2.7b` | `15a431b71c40c284138c379d07d4008a28fea397` | Apache-2.0 |
| Stage E target | `state-spaces/mamba2-2.7b` | `99b226cc377d131cccc610ed4346db564f381f1e` | Apache-2.0 |
| Stage E hybrid (attention at 0-based layers 9,18,27,36,45,56) | `state-spaces/mamba2attn-2.7b` | `5e0f47f0003095d6bdda3ad6fd7f3f41f274accb` | Apache-2.0 |
| Stage E same-family reference | `EleutherAI/pythia-2.8b` | `2a259cdd96a4beb1cdf467512e3904197345f6a9` | Apache-2.0 |

1. **Stage A (CPU, 0 GPU-h).** *Executed in wave 5:*
   `uv run python scripts/run_icl_rule_distillation_doctor.py --output data/results/icl-rule-distillation-port/phase0-doctor.json`
   (NumPy/SciPy only, ~15 s, PHASE0_DOCTOR_PASS, 66/66 gates, evidence grade
   SYNTHETIC_EXECUTABILITY_AND_GATE_SEMANTICS_ONLY; all numbers below are
   synthetic-case numbers). dMMSE-regime synthetic distillation
   ([2306.15063](https://arxiv.org/abs/2306.15063); 16-d state, 4 tasks,
   sigma 0.25, 8 demos): teacher differs from ridge by 0.55 of its variance; the
   exact key-span ceiling caps every w = k rule at 0.50 fidelity and is realised
   through the write code path by an oracle rule; after the written 4-point
   search at equal budget, R_theta reaches 0.94 fidelity to dMMSE while R_gf
   0.38, R_adapt 0.38, R_lin 0.37 track ridge (0.84/0.84/0.82); D(R_theta, R_gf)
   0.56; the w-clamp costs 5.2 and confines the readout to the key span;
   Gaussian-prior negative control (teacher = ridge, inside the key span) is
   flagged non-separating and its 0.094 trained gap is reported as
   optimisation-only, never attributed; permuted-teacher fidelity ≤ −0.28 for
   every rule; two-pass probe-absence / prefix-invariance / zero-state / reset
   audit passes and detects a leaked probe; Pi_8 inert for 8 writes, active on a
   9th; **parameter-count doctor** R_theta 101,762, R_gf h=305 (−0.13%),
   R_adapt h=293 (−0.03%), R_lin 4,100; attribution-tree routing and power; 18
   degenerate inputs rejected. *Still owed before Stage B (needs a model or the
   node):* TR-gate on real gold-plus-shuffled episodes, tokenizer piece-id
   identity across the fla-hub ladder, P/Q factorisation on real residuals,
   loader smoke on the registered ids, a 10-minute throughput smoke measuring
   MFU inside the rebuilt image.
2. **Stage B (≤ 6 GPU-h ceiling, 5.6 estimated) — the kill screen.** Source
   `fla-hub/transformer-1.3B-100B`. Denominator audit on 14 families; per-arm
   search (4 configs × 1.5k dev episodes × 1 epoch per rule family, selection by
   dev KL); distillation runs of 6k episodes × 2 epochs (2:1 gold:shuffled):
   R_theta ×3 seeds, R_gf ×3, R_adapt ×2, R_lin ×2, random-theta ×2, S_x ×2
   (2.7B teacher); derived-rule scalar grid on R_lin; held-out fidelity, clamp
   ablations, TR gate, r_TL, per-step curves, three demonstration permutations,
   teacher-teacher agreement; apply the attribution tree.
3. **Stage C (≤ 2.5 GPU-h, gated on P1 CONFIRMED).** Port R_theta ×3, R_gf ×3,
   R_lin ×2 to the four licensed targets (P2/K3) and the two discovery-only
   targets (reported, never counted); same-family reference
   `transformer-2.7B-100B`; read-path ablation inside the startlux hybrid.
   Per-base eligibility gate on every target.
4. **Stage D (≤ 3.3 GPU-h, gated on P1 CONFIRMED).** `Qwen/Qwen3-1.7B-Base`:
   R_theta and R_gf each with lambda_eq in {0, lambda} at Stage-B selected
   hyperparameters (no re-search) on SIB-200 + MASSIVE; write-en / read-B on
   sw/hi/th/ar/tr/id/vi/ja and on the held-out dataset.
5. **Stage E (≤ 3.3 GPU-h, gated on C).** Pile 300B triplet
   `transformerpp-2.7b` (R_theta ×2, R_gf ×2) → `mamba2-2.7b`, `mamba2attn-2.7b`,
   `pythia-2.8b` reference.

Decisive pilot A + B + C: 8.0 GPU-h estimated (8.5 by ceilings); kill screen
A + B 5.6 (6.0 ceiling); program 14.6 of 16 GPU-h at an assumed 25% MFU
(anchor: llm.c 381,690 tok/s at 47.4% MFU on 8×H100,
[discussion #677](https://github.com/karpathy/llm.c/discussions/677)); the wave-4
ladder, sibling teacher, search and clamp passes add 2.3 GPU-h to B. If the
Stage-A smoke measures MFU below 12.5%: halve B1/D1 episodes, run R_adapt and
R_lin at one seed, drop Stage E.

Primary endpoint: D(R_theta, R_gf) = F(R_theta) − F(R_gf) ≥ 0.10 on eligible
held-out families with the two-sided 95% t-interval on family-level means
excluding 0, accepted only through the attribution tree. Power (4,000-draw
simulation, assumed SDs 0.08 family / 0.06 seed / 0.035 query, numpy 2.5.2 /
scipy 1.18.0, seed 42): 0.78 at 8 families × 3 seeds, 0.89 at 10, 0.95 at 12,
0.98 at a 0.15 effect; one-directional Type-I 0.028. The wave-3 8-cluster
percentile bootstrap has Type-I 0.060 in the same simulation and is a
sensitivity only. At least 8 eligible families are required. Full tree (wave 5,
`simulate_attribution_tree_power`, 4,000 draws, seed 42, same assumed SDs, clamp
/ sibling / audit gates assumed to pass), true 0.10 effect, 8 families, 4
function-induction families: CONFIRMED 0.39, CLASS_UNRESOLVED 0.12,
INCONCLUSIVE 0.28, K1 0.21; at 0.15: CONFIRMED 0.85, K1 0.02; null: CONFIRMED
0.001, K1 0.978. The 0.78 is the primary leaf's CI-excludes-0 probability, not
the CONFIRMED probability.

## Controls

- native ICL with gold and with shuffled labels; contextual-calibration zero-shot;
- **R_gf** iso-parameter nonlinear gradient-form rule at the same interface, loss, episode mix, search budget, compute (decisive control);
- **R_adapt** iso-parameter content-adaptive preconditioned GD (attribution rung) and **R_lin** linear preconditioned GD with derived special cases on a scalar grid (secondary);
- **cross-teacher KL sibling S_x** (2.7B teacher), live only where the teachers disagree on ≥ 0.10 of queries;
- **post-hoc clamp ablations** of the trained R_theta (w := k is a required co-condition of P1; rho and eta clamps secondary);
- random-theta reservoir with fitted P/Q (0.5× kill);
- same-family ports (transformer-1.3B → 2.7B; transformerpp-2.7b → pythia-2.8b) as port-fidelity upper references;
- downstream-attention read-path ablation on the two hybrids;
- iso-corpus / iso-tokenizer / iso-budget ladders by construction; the two ladders as mutual replication;
- M = 0 code-path check; R_gf with lambda_eq = 0 and with lambda_eq as encoder-invariance controls;
- per-arm written hyperparameter search at equal dev budget (an undertuned baseline is a kill-shot);
- audits on every arm: two-forward-pass prefix invariance, TR-fidelity gate, parameter-count doctor, hash-chained write log, reset attestation, single-adversarial-demonstration poisoning probe.

## Falsifiers

- K1 (primary leaf only; a class-level miss is CLASS_UNRESOLVED, never K1): D(R_theta, R_gf) below 0.05 or CI including 0 on the source (at this interface and capacity the update is a gradient-form rule; the ladder readings D(R_gf, R_lin) and D(R_gf, R_adapt) give the bounded sub-reading; reported per family class);
- K2: fewer than 8 eligible held-out families on the source (unmeasurable at 1.3B);
- K3: ported D(R_theta, R_gf) ≥ 0.05 on fewer than 2 of the 4 licensed targets (exactly 2 = MIXED, not a kill); K3b: the downstream-attention patch removes ≥ 0.5 of after-recurrent fidelity;
- K4: any audit failure: prefix invariance, poisoning persistence, reservoir ≥ 0.5×, TR-gate failure on more than half of eligible families, parameter-count doctor outside 1%;
- K5: lambda_eq costs more than 0.10 monolingual fidelity or does not shrink the held-out-language gap;
- K6: R_theta ties S_x within 0.05 where the teachers disagree on ≥ 0.10 of queries (collapse to a Fast Weight Layers / SRWM-class learned ICL rule); UNINFORMATIVE if the teachers agree everywhere.

Pre-registered non-kill outcomes: UNATTRIBUTED (gap ≥ 0.10 but w-clamp costs
below 0.05 — no port, investigation), INCONCLUSIVE (gap 0.05–0.10 — no port) and,
since wave 5, CLASS_UNRESOLVED (primary leaf, clamp, sibling and reservoir pass
but the function-induction class point estimate is below 0.10, its one-sided 80%
lower bound is not above 0, or fewer than 4 class families are eligible — no
port, per-class report; the only follow-up is extending the family pool).
Decision order as implemented: K2, K4, K1, K6, INCONCLUSIVE, UNATTRIBUTED, class.

## Compute

Pilot image (rebuilt, exists on fal-h100-01; built by Slurm job 353 from commit
999f5583): tag `cotcodec-research:999f5583-architecture`,
`127.0.0.1:5000/cotcodec-research@sha256:bde90daa78c26cd2fb9d05036b0c9f9613c2386b9d7561816b541d2736c79f5d`
(image ID sha256:9d832a59fe348d149d2e4587ac6af90223e2956ebb646d7b19295298954ca5ad;
torch 2.11.0+cu128, transformers 5.15.0, flash-linear-attention 0.5.2, fla-core
0.5.2, triton 3.6.0). tilelang is being added because fla guards the gated GDN
backward on Hopper under Triton below 3.7.1 (fla issue 640); mamba_ssm and
causal-conv1d for Stage E are not in it; no container smoke, sbatch dry-run or
resume receipt exists for this contract yet. The older discovery image
(`…@sha256:15d6abc0…`, no fla) is superseded for pilots. Checkpoint receipts
exist on fal-h100-01 for `transformer-1.3b-100b`, `gla-1.3b-100b`,
`gdn-1.3b-isp-hybrid-3to1-50b`, `qwen3-1.7b-base` (and six ids used by other
directions); not yet for `transformer-2.7b-100b`, `delta-net-1.3b-100b`,
`mamba-1.3b-100b`. The phase-0 doctor needs no image or GPU:
`uv run python scripts/run_icl_rule_distillation_doctor.py --output data/results/icl-rule-distillation-port/phase0-doctor.json`.
Submit GPU stages through `scripts/submit_docker_research_job.py` (`--dry-run` first), which
wraps `sbatch infra/slurm/host-single-node/docker-research.sbatch`; one GPU per
job; checkpoints every 10 minutes to `/home/kevin/cotcodec-runs/icl-rule-distillation-port/`;
SIGUSR1 checkpoint plus fresh-job resume equivalence on every truncated-BPTT run.
Seeds 42/43/44; `execution.enabled: false` until the blockers in the contract
are cleared. Publication lane (cgroup-v2 Slurm + Pyxis) is unavailable; results
are discovery-grade.

## Kevin advantage

Honest and partial. The pilot substrate (fla-hub ladder, Pile triplet,
SIB-200/MASSIVE) is public. Unique pieces: (i) the 8×H100 node with a
residual-hook harness and the SIGUSR1-resumable truncated-BPTT lane; (ii) the
already-registered `kimi-linear-48b-a3b-base` makes the Moonlight-16B-A3B →
Kimi-Linear multilingual iso-tokenizer cross-operator pair runnable as a gated
upgrade (identical tiktoken blob, both MIT, iso-active 3B); (iii) General
Translation's span-aligned parallel demonstration sets as additional lambda_eq
pairs and held-out languages, under GT's own terms, never redistributed;
(iv) the SR-TTT-derived causality doctors. Tinker cannot help (no hidden states,
no optimizer access).

## Negative-result value

K1 → a bounded behavioural result with two readings the ladder separates: at a
64-d rank-8 interface and matched capacity, the transformer's content-dependent
in-context update is not distinguishable from a gradient-form rule by fidelity
to its own predictions and errors, and either a linear preconditioner suffices
or a learned content-dependent (possibly nonlinear) preconditioner is needed;
reported per family class it says which task classes admit which GD description,
a quantitative input to the ICL-as-GD debate at a scale Shen et al. tested only
with order and output-distribution probes, and it empties Direction 16's
premise for a few GPU-hours. K2 → a measured floor: at 1.3B–1.7B,
label-dependent ICL is confined to binding and function-induction families.
K3/MIXED → the first cross-family behavioural measurement of in-context update
portability on licensed iso-ladder bases, with the read-path ablation saying
whether softmax carried it. P3 null → the frozen encoder's language invariance
alone explains cross-lingual memory readout. K6 → a clean replication of Fast
Weight Layers on modern bases plus the fact that a KL-distilled ICL rule is not
teacher-specific at this granularity. UNATTRIBUTED → an iso-capacity gap that no
named degree of freedom carries points at optimisation rather than structure.

Strongest counter-argument: even a positive result may be "a better associative
rule at a convenient interface" rather than "the transformer's update"; the
ladder and the w-clamp locate the win in a named structural degree of freedom,
but only fidelity on teacher-wrong queries, order sensitivity and the
cross-teacher sibling tie the rule to *this* teacher, all noisy at 400 queries;
a from-scratch matched arm (deferred by the rescope) and measured noise SDs
would be needed to close the gap.

## Wave record

| Wave | Outcome | Record |
|---:|---|---|
| 1 | killed before judging: identification and feasibility REFUTED (0.8), novelty not refuted (0.6) | `research/gauntlet/2026-09-01-frontier/wave1-ledger.md` row 5 |
| 2 | judged 62/62; identification 3/10; blind discrimination: different mechanism (0.88) | `research/gauntlet/2026-09-01-frontier/wave2-result.json`, `wave2/icl-rule-distillation-port.md` |
| 3 | one identification repair applied (matched placebo, fidelity endpoint, per-base gate, rescope, read-path ablation, priors); judged 61/57 (lower authoritative 57; a 5-point dip from wave 2, recorded) | `research/gauntlet/2026-09-01-frontier/wave3-result.json`, `wave3-ledger.md` |
| 4 | one identification repair applied (iso-parameter gradient-form ladder with R_gf decisive, attribution tree with w-clamp co-condition, cross-teacher sibling, licensed-target P2/K3, written per-arm search, t-interval decision rule, C24/C25 corrected, Direction 16 and ICL-as-GD/taxonomy priors); judged 66/65 (lower authoritative 65); both reviewers: fatal defect = nothing executable after four waves; Reviewer 2: tree power mis-stated (class co-condition 0.21–0.48, miss routed to K1) | `research/gauntlet/2026-09-01-frontier/wave4-result.json` |
| 5 | one executability repair applied: `harness/icl_rule_distillation.py` + `scripts/run_icl_rule_distillation_doctor.py` + `tests/test_icl_rule_distillation_doctor.py` written and executed (PHASE0_DOCTOR_PASS 66/66, synthetic-case numbers only); attribution tree re-tiered (CLASS_UNRESOLVED, ≥ 4 class families, one-sided 80% class bound) with full-tree power reported; contract arms synced to registered ids; rebuilt fla 0.5.2 image and receipts cited; `reference_doctor` added to the contract; not re-judged; score history 62 → 62 → 57 → 65 → pending | this file, the proposal, the contract, `data/results/icl-rule-distillation-port/phase0-doctor.json` |
