# Direction 19: Portable In-Context Write-Rule Distillation

**Status:** SPEC on 2026-09-01 — wave-2 judged 62/62; wave-3 identification repair applied; not pilot-ready (Compute FAIL, no signed reviews, no evidence bundle)
**Priority:** CPU regime/causality doctors, then a 4 GPU-hour source kill screen before any port
**Experiment contract:** `experiments/architectures/icl-rule-distillation-port.yaml`
**Proposal:** `research/proposals/2026-09-01-icl-rule-distillation-port.md`

## Research question

Is the object worth porting between sequence-operator families the *write rule*
— how a context item becomes a state update — rather than weights (Generative
Adapter, Doc-to-LoRA) or state (Cache-to-Cache, KV translation)? Concretely:
can a frozen softmax transformer's content-dependent in-context update be
distilled into an explicit rank-8 fast-weight write rule at a canonical 64-d
interface that reproduces the teacher's own held-out 8-shot predictions more
faithfully than a dense-preconditioned-GD superset rule trained at the same
interface, episode mix and compute; and does that frozen rule keep a measurable
fraction of its fidelity when ported through label-free maps to DeltaNet, GLA,
RetNet, HGRN2, GSA and Mamba bases trained on the same corpus, tokenizer and
token budget?

Claim scope is **portability-protocol** (rescoped in wave 3 from
architecture-causal: every arm is a frozen retrofit; no from-scratch matched arm
is budgeted). The pre-registered collapse is explicit: if the distilled rule ties
a label-trained sibling rule at the same interface, the result is a Fast Weight
Layers / SRWM instance and is reported as such.

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
           base-specific parameters. R_theta: 2-layer MLP, width 256, ~1e5 parameters, shared.
Superset control R_GD at the same interface:
  u_i = W e_i,  w_i = k_i,  eta_i = eta_0 (i+1)^(-gamma) / (||k_i||^2 + eps)^beta,  rho_i = rho_0
  (contains delta, Kaczmarz, OSDN-diagonal, Falcon and FAAST rules as special cases)
Distillation (source only, distillation families only, gold AND teacher shuffled-label episodes 2:1):
  L_dist = sum_i sum_q KL( p_T(. | q, c_(<=i)) || p_(T,M_i)(. | q) )      truncated BPTT through 8 writes
Cross-lingual stage only (training pairs en-de/es/zh):
  L_eq = || Delta M(c_i) - Delta M(c_i^B) ||_F^2       evaluated write-en / read-B on held-out languages
Port: freeze the rule; fit P_b' by ridge regression of target residuals onto source canonical keys and
      Q_b' by functional matching of next-token log-prob shifts under a fixed bank of 8 random rank-1 M's,
      both on 2k x 512-token FineWeb-Edu sequences with no task family.
```

Wave-3 identification repair (both judges' highest-impact fix, applied as one
change): (a) teacher shuffled-label episodes in every rule's distillation
stream plus a TR-fidelity CI gate (each rule's shuffled-write gain must match
the teacher's random-label gain within 0.05 before its r_TL is admitted);
(b) **teacher fidelity** — agreement with the teacher's own 8-shot argmax on
held-out families, minus the M = 0 agreement — is the primary endpoint, with
error-agreement kappa, per-step curve distance and order-sensitivity agreement
as secondaries; (c) the G_TL ≥ 10-point eligibility gate is applied per base,
including every recurrent target; (d) claim rescoped to portability-protocol;
(e) the inert adjacent-layer site-type factor on the startlux hybrid is replaced
by a **downstream-attention read-path ablation** (patch every attention sublayer
downstream of an after-GDN injection to its M = 0 output, so the injection can
propagate only through GDN/MLP sublayers); (f) five judge-named priors added.

## Closest work and delta

| Prior | Source | What it does | Delta here |
|---|---|---|---|
| Can GD Simulate Prompting? | [2506.20989](https://arxiv.org/abs/2506.20989) | Meta-trained same-model gradient step emulates conditioning | Rule externalised at a canonical interface, frozen, ported across operator families, compared with a GD superset |
| Learning without training | [2507.16003](https://arxiv.org/abs/2507.16003) | Analytic low-rank MLP patch inside one block | Learned rule by behavioural distillation; cross-family test |
| Generative Adapter / Doc-to-LoRA | [2411.05877](https://arxiv.org/abs/2411.05877), [2602.15902](https://arxiv.org/abs/2602.15902) | Context to per-model weight update (WHAT); Doc-to-LoRA must retrain its hypernetwork per target LLM | The object is the write rule (HOW); state is base-independent |
| Cache-to-Cache / XKV / KV translation | [2510.03215](https://arxiv.org/abs/2510.03215), [2608.20617](https://arxiv.org/abs/2608.20617), [2608.30963](https://arxiv.org/abs/2608.30963) | Transfer KV or latent state between frozen LMs | The rule is transferred; targets have no KV cache |
| Modular TTT / Falcon rules | [2608.07110](https://arxiv.org/abs/2608.07110), [2608.27763](https://arxiv.org/abs/2608.27763) | Learned or derived inner rules within one family | Used as the derived-rule control family; never distilled from a transformer or transferred |
| Fast Weight Layers / SRWM | [2212.02475](https://arxiv.org/abs/2212.02475), [2202.05780](https://arxiv.org/abs/2202.05780) | Learned fast-weight sidecars on a base | The pre-registered collapse target |
| Trained Persistent Memory (Jeong) | [2603.22329](https://arxiv.org/abs/2603.22329), [2603.16413](https://arxiv.org/abs/2603.16413) | "Universal write rule shared across backbones + architecture-specific read paths"; fixed Hebbian aggregation, LM loss, GPT-2-124M and Flan-T5-XL only | Closest framing prior: here the rule is distilled from ICL behaviour, compared with GD, ported frozen across operators, scored on teacher fidelity |
| FAAST | [2605.04651](https://arxiv.org/abs/2605.04651) | Closed-form pseudoinverse fast weights on frozen states, model-agnostic | Fixed rule; added as a special case in the derived-rule grid |
| Language Models Need Sleep | [2605.26099](https://arxiv.org/abs/2605.26099) | Learned local rule into SSM-block fast weights inside one trained model | Not distilled, not ported |
| Cross-model Control | [2410.17599](https://arxiv.org/abs/2410.17599) | Portable logit-shift tiny LM across tokenizers/architectures | Transfers a delta LM, not an update rule; no write/read state |
| ICLCA | [2406.02847](https://arxiv.org/abs/2406.02847) | Exact ICL-to-bias conversion in linearized transformers | Analytic, single model, no port |

No direct prior art found through 2026-09-01 under the recorded coverage
(H100-host arXiv relay, HF papers, Crossref, OpenReview titles, WebFetch
abstract pages, GitHub and Hugging Face metadata; Semantic Scholar, OpenReview
bodies, ACL Anthology, patents and Chinese venues not searched). Wave-2 novelty
refuter: not refuted (0.6); blind discrimination: different mechanism (0.88).
Collision risk **high**; pending a signed provider-distinct audit.

## Cheapest decisive pilot

Public data only (Function Vectors MIT; in-repo binding generator;
Super-NaturalInstructions Apache-2.0; SIB-200 CC-BY-SA-4.0; MASSIVE CC-BY-4.0;
FineWeb-Edu ODC-By). General Translation parallel data is an optional upgrade
whose research-use license is unknown and must be cleared first.

1. **Stage A (CPU, 0 GPU-h).** dMMSE-regime synthetic distillation
   ([2306.15063](https://arxiv.org/abs/2306.15063)): kill if R_theta cannot beat
   R_GD where the implicit predictor is provably not GD. Prefix-invariance,
   probe-absence, TR-gate, tokenizer piece-id and rank/algebra doctors; loader
   smoke on registered `smollm2-135m`, `qwen3-0.6b-base`, `mamba-130m-hf`; a
   10-minute throughput smoke measuring MFU.
2. **Stage B (≤ 4 GPU-h) — the kill screen.** Source
   `fla-hub/transformer-1.3B-100B` (d6f66f4181fa669e5863327815b44533e3a395e7,
   MIT). Denominator audit on 14 families; distillation runs of 6k episodes × 2
   epochs (2:1 gold:shuffled): R_theta ×3 seeds, R_GD ×3, random-theta ×2,
   label-trained sibling ×2; derived-rule scalar grid; held-out fidelity, TR
   gate, r_TL, per-step curves, three demonstration permutations.
3. **Stage C (≤ 2.5 GPU-h, gated on B).** Port to `fla-hub/{delta_net, gla,
   retnet, hgrn2, gsa, mamba}-1.3B-100B` (b4dcbbaf…, 46b15820…, 7fddefc4…,
   2f413dd9…, 1e4ffdae…, 49d177ea…), same-family reference
   `fla-hub/transformer-2.7B-100B` (e29b06c9…), read-path ablation inside
   `startlux-models/gdn-1.3b-isp-hybrid-3to1-50b` (0ced446e…, attention at
   0-based layers 2,5,…,23). Per-base eligibility gate on every target.
4. **Stage D (≤ 3.3 GPU-h, gated on B).** `Qwen/Qwen3-1.7B-Base` (ea980cb0…):
   R_theta and R_GD each with lambda_eq in {0, lambda} on SIB-200 + MASSIVE;
   write-en / read-B on sw/hi/th/ar/tr/id/vi/ja and on the held-out dataset.
5. **Stage E (≤ 3.3 GPU-h, gated on C).** Pile 300B triplet
   `state-spaces/transformerpp-2.7b` → `mamba2-2.7b`, `mamba2attn-2.7b`
   (attention at 0-based layers 9,18,27,36,45,56), `EleutherAI/pythia-2.8b`
   reference.

Decisive pilot A + B + C ≤ 6 GPU-h; program 12.3 of 16 GPU-h at an assumed 25%
MFU (anchor: llm.c 381,690 tok/s at 47.4% MFU on 8×H100,
[discussion #677](https://github.com/karpathy/llm.c/discussions/677)); halve
episodes and drop Stage E if the Stage-A smoke measures MFU below 12.5%.

Primary endpoint: F(R_theta) − F(R_GD) ≥ 0.10 on eligible held-out families,
paired family-clustered bootstrap 95% CI excluding 0. Power (simulated, assumed
SDs 0.08 family / 0.06 seed / 0.035 query): 0.77 at 8 families × 3 seeds, 0.88
at 10 families, 0.98 at a 0.15 effect. At least 8 eligible families are required.

## Controls

- native ICL with gold and with shuffled labels; contextual-calibration zero-shot;
- R_GD superset at the same interface, loss, episode mix, compute (decisive control) plus derived special cases on a scalar grid;
- label-trained sibling rule (same interface and episodes, cross-entropy on labels);
- random-theta reservoir with fitted P/Q (0.5× kill);
- same-family ports (transformer-1.3B → 2.7B; transformerpp-2.7b → pythia-2.8b) as port-fidelity upper references;
- downstream-attention read-path ablation on the two hybrids (replaces the inert site-type factor);
- iso-corpus / iso-tokenizer / iso-budget ladders by construction; the two ladders as mutual replication;
- M = 0 code-path check; R_GD with lambda_eq = 0 and with lambda_eq as encoder-invariance controls;
- audits on every arm: two-forward-pass prefix invariance, TR-fidelity gate, hash-chained write log, reset attestation, single-adversarial-demonstration poisoning probe.

## Falsifiers

- fidelity gap below 0.05 or CI including 0 on the source (behaviourally preconditioned GD at this interface; bounded negative, reported per family class);
- fewer than 8 eligible held-out families on the source (unmeasurable at 1.3B);
- ported R_theta fails to beat ported R_GD on every pure-recurrent target, or the downstream-attention patch removes ≥ 0.5 of after-recurrent fidelity;
- any audit failure: prefix invariance, poisoning persistence, reservoir ≥ 0.5×, TR-gate failure on more than half of eligible families;
- lambda_eq costs more than 0.10 monolingual fidelity or does not shrink the held-out-language gap;
- R_theta ties the label-trained sibling within 0.05 (collapse to Fast Weight Layers / SRWM).

## Compute

Discovery image on fal-h100-01 (verified 2026-09-01):
`127.0.0.1:5000/cotcodec-research@sha256:15d6abc06fa53ab466087a92107da9c58e469615e2f56a683fefd0a7600277f3`
(image ID sha256:ca32b5c2…, revision 581ded8d…, created 2026-08-16; CUDA 12.8.1,
torch 2.11.0+cu128, transformers 5.15.0; **no fla**). The pilot needs a rebuilt
image with flash-linear-attention 0.5.2 (commit 9c8e42e762fce087c27b673af4922795d9edb85e)
pinned, plus mamba_ssm and causal-conv1d for Stage E, re-pinned by digest.
Submit through `scripts/submit_docker_research_job.py` (`--dry-run` first), which
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

K1 → a bounded behavioural result: at a 64-d rank-8 interface and on the
eligible held-out families, the transformer's content-dependent in-context
update is not distinguishable from preconditioned GD by fidelity to its own
predictions and errors; reported per family class it says which task classes
admit a GD description, and it empties Direction 16's premise for a few
GPU-hours. K2 → a measured floor: at 1.3B–1.7B, label-dependent ICL is confined
to binding and function-induction families. K3 → the first cross-family
behavioural measurement of in-context update portability, with the read-path
ablation saying whether softmax carried it. P3 null → the frozen encoder's
language invariance alone explains cross-lingual memory readout. K6 → a clean
replication of Fast Weight Layers on modern bases.

Strongest counter-argument: even a positive result may be "a better associative
rule at a convenient interface" rather than "the transformer's update"; only
fidelity on teacher-wrong queries and order sensitivity separate the two, and a
from-scratch matched arm (deferred by the rescope) would be needed to close the
gap.

## Wave record

| Wave | Outcome | Record |
|---:|---|---|
| 1 | killed before judging: identification and feasibility REFUTED (0.8), novelty not refuted (0.6) | `research/gauntlet/2026-09-01-frontier/wave1-ledger.md` row 5 |
| 2 | judged 62/62; identification 3/10; blind discrimination: different mechanism (0.88) | `research/gauntlet/2026-09-01-frontier/wave2-result.json`, `wave2/icl-rule-distillation-port.md` |
| 3 | one identification repair applied (matched placebo, fidelity endpoint, per-base gate, rescope, read-path ablation, priors); not re-judged | this file, the proposal and the contract |
