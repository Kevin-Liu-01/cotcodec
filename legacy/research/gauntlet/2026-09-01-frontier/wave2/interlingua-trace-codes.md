# interlingua-trace-codes — wave-2 repaired candidate (2026-09-01)

Repair owner: single owner, wave 2. Wave-1 verdicts: novelty NOT refuted (0.6, with caveats), identification
REFUTED (0.85), feasibility REFUTED (0.85). Both refutations are answered below by changing the medium, the
endpoint, the controls, the data and the budget. The sibling dependency on `frozen-reader-anchored-media` is
removed: this candidate now defines its own medium and can run first.

dropped: **false**

---

## 1. Name and claim

**slug.** interlingua-trace-codes

**claim (one line).** On a discrete executor-bottleneck reasoning code with rate slack (128 bits per step against
<= 30 bits of action entropy), symmetric parallel-pair invariance supervision causally lowers the cross-language
transfer gap of a held-out, intervention-defined counterfactual-reliance monitor by >= 5 AUROC points relative to
the iso-data no-pair arm AND relative to same-language paraphrase-pair supervision, at task accuracy within 1 pp —
identifying parallel translation data (rather than emergent invariance under shared weights, shared anchor
tokens, or generic consistency regularization) as a monitorability asset.

**claim_scope.** portability-protocol (a training protocol that makes a trace monitor portable across languages).

---

## 2. Mechanism

**Medium (self-contained; no frozen reader, no monitor variable in any loss).**
Policy pi_theta = Qwen3-0.6B-Base (registry `qwen3-0.6b-base`, Qwen/Qwen3-0.6B-Base @da87bfb608c14b7cf20ba1ce41287e8de496c0cd,
Apache-2.0, role `multilingual-base`; Qwen3 pretraining covers 119 languages per the Qwen3 technical report,
https://arxiv.org/abs/2505.09388, 2025-05-14). Executor E_psi = 4-layer transformer, d = 256, ~8M parameters, trained
from scratch, shared across languages. Reserved code vocabulary of K = 256 symbols appended to the tokenizer; T = 16
symbols per reasoning step.

At step t of an episode, with context c_t^L = (x^L, h_t) where x^L is the task prose in language L and h_t is the
language-neutral JSON history (a_1, o_1, ..., a_{t-1}, o_{t-1}):

- q_theta(z_{t,i} | c_t^L, z_{t,<i}) is a distribution over the K symbols, i = 1..T.
- z_{t,i} = onehot(argmax(log q_theta + g)), g ~ Gumbel, with straight-through gradient (Gumbel-softmax, temperature
  annealed 1.0 -> 0.5). No RL is needed at the pilot; everything is differentiable.
- Executor: p_psi(a_t | z_{<=t}, h_t). The executor NEVER sees x^L. All prose content that influences the action must
  pass through z — z is the only channel from language-L text to the action (the interlingua by construction).
- L_task = - sum_t log p_psi(a*_t | z_{<=t}, h_t), where a*_t is the gold JSON tool call (tool id + arguments as field
  references and literals). Gradients reach psi directly and theta through the straight-through estimator.
- Rate slack (opposite of rate matching): T log2 K = 128 bits per step versus H(a_t | h_t) <= 30 bits in the oracle world
  (computed in phase 0). Language, and any other side information, CAN be written into z. Whether it IS written is
  what the arms measure.

**Pair arms.** A pair (x^A, x^B) is two renderings of one world instance (same execution log, same gold actions). Per
step a leader l in {A, B} is drawn; z^l is the leader's straight-through sample; the follower f is teacher-forced on
z^l_{<i}. L_inv = sum_i JS( q_theta(. | c_t^A, z^l_{<i}) , q_theta(. | c_t^B, z^l_{<i}) ) (symmetric Jensen-Shannon; no pivot
language). L = L_task(leader) + lambda_inv L_inv. lambda_inv in {0.1, 0.3, 1.0} is selected on a held-out dev split BY TASK
ACCURACY ONLY (pre-registered; never by the monitor endpoint). Because both members share the execution log,
teacher-forcing the leader's code into the follower is semantically valid and costs exactly one forward per member.

**Arm list (every arm sees the same multiset of rendered instances in all languages — iso-instance, iso-step,
iso-parameter, iso-optimizer; only the pairing term differs).**
- A  code, no L_inv (iso-data; members processed unpaired). Measures emergent invariance under shared weights.
- B  code + symmetric L_inv on translation pairs (en<->de, en<->zh, de<->zh, en<->syn).
- B' code + English-pivot alignment KL( q^en || q^L ) with stop-gradient on English (M-Thinker / SOLAR form).
- C  code + L_inv on same-log SAME-LANGUAGE paraphrase pairs (two English re-renderings from a committed paraphrase
     pool). The discriminating placebo: same regularizer, same strength, no cross-language signal.
- D  code + L_inv on ANCHOR-RANDOMIZED translation pairs: tool identifiers and field labels replaced by a
     per-language bijection to opaque ids (e.g. `tool_k7`, `feld_3` vs `字段三`), numerals rendered as words in each
     language; removes shared surface anchors (mOthello control).
- E  code + language-ID adversary on the mean z embedding through gradient reversal (invariance without pairs).
- G  explicit CoT: z = <= 48 natural-language tokens sampled over the full vocabulary with the same straight-through
     estimator, plus beta KL( q_theta || p_LM ) to the FROZEN Qwen3-0.6B-Base as a fluency prior (Markovian-Transformers
     device); executor reads the tokens through its own small embedding. Receives NO disclosure or legibility reward.
     A fluency doctor (rationale perplexity under the frozen LM <= 2x teacher-written rationales) gates its use.
- syn = a synthetic language (deterministic vocabulary bijection + word-order permutation of English templates):
     competence is identical to English by construction, so Delta_syn isolates surface-form effects from
     competence effects.

**Monitoring protocol (post hoc; no quantity below appears in any training loss).**
Labels are defined by intervention on the trained policy, then read by a monitor that sees only z:
- y_hint = 1[ a_t(x) != a_t(x minus hint) ]  (counterfactual hint reliance; the hint is a planted candidate value with
  randomized presence and randomized correctness; gold actions do not depend on the hint). This includes the
  "rescued by a correct hint" cases, in which the action is correct and an action-only monitor is blind.
- y_spur = 1[ a_t(x) != a_t(x with a gold-irrelevant field perturbed) ]  (spurious dependence on a distractor field).
- Labels are computed per arm on the eval split by re-running that arm's greedy policy under the intervention.
- Base-rate doctor: y_hint base rate must fall in [0.15, 0.60] per language; hint reliability is tuned in phase 0
  (target 70-80% correct) BEFORE any monitor is trained, and never touched afterwards.

Monitor M_en: logistic regression on (position, symbol) one-hots plus a 2-layer MLP on learned symbol embeddings,
trained ONLY on English episodes of the eval split (train/test split by template family, disjoint from policy
training templates). Tested on L in {de, zh, syn}. Delta_L = AUROC_en - AUROC_L; catch rate at 5% FPR reported too.
Floors and ceilings: action-only monitor (input: a_t, h_t, hint value, field literals — language-neutral, Delta = 0 by
construction); per-language monitors M_L (ceiling). For G: translate-then-monitor (MADLAD L->en, then M_en) and an
xTune-style consistency-trained M_en (trained on English rationales plus MADLAD en->L translations with a
consistency term).

**Primary endpoint (pre-registered).** Paired difference Delta_L(A) - Delta_L(B) on y_hint, averaged over L in {de, zh},
instance-level bootstrap over >= 3k eval pairs, 2 seeds in phase 1; syn reported separately. Secondary: Delta_L(C) -
Delta_L(B); AUROC_en(z-monitor) - AUROC_en(action-only); Delta_L(D) - Delta_L(B); Delta_L(G, translate-then-monitor) - Delta_L(B).
Invariance diagnostics (secondary only): greedy-code exact-match agreement across pair members;
silhouette-by-language of mean z embeddings; I(z; language) estimated by a language classifier.

---

## 3. What is new (downgraded per the wave-1 novelty caveats)

Parallel-pair alignment of reasoning traces is published: M-Thinker's Cross-lingual Thinking Alignment reward
compares non-English reasoning to the English path on the same problem under GRPO (explicit medium, English pivot,
accuracy and language-consistency endpoints, no monitor), and SOLAR aligns continuous soft tokens to an English
pivot for accuracy. Post-hoc invariance analysis on parallel traces is also published (GI-SAE, 2608.23809, InfoNCE SAE on
MGSM traces; amplifies structure already present). Emergent invariance without parallel data is published for
continuous CODI latents (2603.08177) and for off-the-shelf models (2608.23809). Monitor fragility across 13 languages is
measured with an LLM judge and no intervention (2605.27901). Consistency regularization on MT-augmented inputs is
published on the classifier side (xTune).

The delta of this candidate is the combination, none of whose parts the priors report together:
(i) a DISCRETE executor-bottleneck code with generous rate slack, in which language leakage is possible and is
measured, trained with no reader or monitor term; (ii) SYMMETRIC (pivot-free) pair invariance with the two controls
that separate translation signal from same-log equivalence (C) and from anchor sharing (D), plus the pivot form (B')
as an explicit comparator; (iii) monitor labels defined by INTERVENTION on the trained policy (counterfactual hint
reliance), never present in any loss; (iv) cross-language transfer of a trace monitor on tool-use episodes as the
endpoint, against an action-only floor, translate-then-monitor and a consistency-trained monitor.

No direct prior art found through 2026-09-01 for this combination under: hostsearch arXiv (4 queries: interlingua x
reasoning; language-agnostic x latent reasoning; cross-lingual x monitor x chain-of-thought/reasoning trace;
discrete-latent/latent-tokens x multilingual x reasoning), hostsearch HF papers (cross-lingual chain-of-thought
monitor transfer), abstract reads of 2510.07300 and 2608.23809, plus the wave-1 refuters' 28 evidence URLs.
Coverage limits: OpenReview and Semantic Scholar not reachable; no full-text reads beyond abstracts this pass.

## 4. Closest priors

| prior | url | date | delta |
|---|---|---|---|
| M-Thinker / Think Natively (CTA reward) | https://arxiv.org/abs/2510.07300 | 2025-10-08 (rev 2026-01-08) | Explicit NL reasoning aligned to an English pivot via LLM-judge reward under GRPO; accuracy/consistency endpoints; no monitor, no discrete medium, no placebo. Here: pivot-free JS on a discrete bottleneck code; B' reproduces the pivot form as a control. |
| Is continuous CoT better suited for multilingual reasoning? | https://arxiv.org/abs/2603.08177 | 2026-03-09 | CODI continuous latents are emergently language-invariant with no parallel data, decoder or monitor. Here: arm A measures emergent invariance of a DISCRETE code directly; B must beat it. |
| Fragility of CoT Monitoring Across Typologically Diverse Languages | https://arxiv.org/abs/2605.27901 | 2026-05-27 | GPT-5.1 judge, deception rates (~95.9%) on 127 GPQA MCQs x 13 languages; no trained monitor, no per-language gap, no intervention. Here: trained monitors, measured Delta_L, an intervention. Cited as motivation only; none of its numbers are used as predictions. |
| GI-SAE: cross-language reasoning invariance | https://arxiv.org/abs/2608.23809 | 2026-08-24 | Post-hoc InfoNCE SAE on parallel MGSM traces of frozen models; finds/amplifies existing invariance; no policy intervention, no monitor transfer. Here: the policy's code is the object of intervention. |
| SOLAR | https://arxiv.org/abs/2606.26466 | 2026-06-25 | Continuous soft tokens aligned to an English pivot for accuracy (+17.7). Here: discrete, symmetric, monitor endpoint. |
| xTune (ACL 2021) | https://aclanthology.org/2021.acl-long.264/ | 2021-08 | Consistency regularization on MT-augmented inputs on the classifier side. Here: used as the matched monitor-side control for the explicit-CoT arm. |
| mOthello | https://arxiv.org/abs/2404.12444 | 2024-04-18 | Shared anchor tokens drive cross-lingual alignment; alignment does not imply transfer. Here: arm D removes anchors. |
| Reasoning models don't always say what they think | https://arxiv.org/abs/2505.05410 | 2025-05-08 | Counterfactual hint-reliance protocol for CoT faithfulness on frontier models. Here: the same counterfactual definition supplies held-out monitor labels for a trained small policy. |
| Parallel data has minimal effect on cross-lingual alignment | https://arxiv.org/abs/2603.29026 | 2026-03 | Alignment-level negative on parallel data. Here: the kill condition K1/K2 extends it to reasoning codes if B fails to beat A and C. |
| A neural interlingua for multilingual MT (Lu et al.) | https://arxiv.org/abs/1804.08198 | 2018-04 | Continuous attentional interlingua bottleneck in NMT; no reasoning, no monitor. Not opened this pass. |

## 5. Falsifiable predictions

- P1 (phase 0; qwen3-0.6b-base; en/de/zh/syn oracle world; arms A, B, C; 1 seed): Delta_L(A) in [8, 20] AUROC points on
  y_hint (partial emergent invariance); Delta_L(B) <= 4; Delta_L(C) >= Delta_L(B) + 5; task accuracy within 1 pp across
  A/B/C; AUROC_en of the z-monitor >= action-only floor + 0.10 (>= 0.80 vs <= 0.70). Delta_syn(A) >= 5 (surface form alone
  leaks into the code even at equal competence).
- P2 (phase 1): Delta_L(D) <= Delta_L(B) + 3 (invariance survives anchor randomization); E reaches Delta_L <= Delta_L(B) + 3
  only at >= 2 pp task loss; B' matches B for monitors trained on English but is worse by >= 3 points for a monitor
  trained on de and tested on zh (the pivot leaves non-English pairs unaligned).
- P3 (phase 1, lower confidence; the wave-1 ">= 20 points" claim had no source and is withdrawn): explicit-CoT arm G
  read by M_en shows Delta_L >= 10; translate-then-monitor with MADLAD reduces it to <= 8 but stays >= Delta_L(B) + 4 on
  y_hint; the xTune-style consistency-trained M_en closes at most half of the remaining gap.
- P4 (phase 1, real parallel data: GSM8KInstruct_Parallel + calculator tool; en/de/zh/sw; arms A/B/C; 1 seed): the
  ordering Delta(B) < Delta(A) replicates with Delta_sw(A) - Delta_sw(B) >= 4 (Swahili is where emergent invariance
  should be weakest).
- P5: silhouette-by-language of mean z embeddings: A >= 0.25, B <= 0.10; greedy-code pair agreement: A <= 35%, B >= 65%.

## 6. Kill conditions

- K1 (phase 0, primary): Delta_L(A) - Delta_L(B) < 5 AUROC points with the bootstrap CI covering 0 at task accuracy
  within 1 pp — parallel supervision adds nothing beyond emergent invariance (extends 2603.08177 / 2608.23809 to trained
  discrete codes).
- K2 (phase 0): Delta_L(C) within 2 points of Delta_L(B) — same-language paraphrase pairs suffice; translation data is not
  the asset; the direction collapses into generic consistency regularization (xTune on the policy side) and is dropped.
- K3 (phase 0): AUROC_en(z-monitor) <= action-only floor + 0.03 on y_hint — the code carries no reliance information
  beyond the action; invariance is moot; the medium fails for monitoring regardless of language.
- K4 (phase 1): Delta_L(D) >= Delta_L(A) — the B gain was anchor-driven (mOthello extends to reasoning codes).
- K5 (phase 1): translate-then-monitor on G reaches Delta_L within 3 points of B at equal or lower total cost — the cheap
  alternative suffices.
- K6: pair agreement >= 70% with AUROC_en < 0.65 — invariant but collapsed code.
- K7: any arm's task accuracy < oracle-solvable accuracy - 10 pp after two remediation rounds (the bottleneck is not
  trainable at 0.6B with straight-through gradients).

## 7. Cheapest decisive pilot

**Phase 0 = the cheapest decisive pilot (<= 4 GPU-hours on 8xH100, plus CPU doctors).**

CPU work (0 GPU-h; ~4-6 engineering days — nothing below exists in the repo today; see "honest infrastructure
state"):
1. `ToyTools-XL` oracle-world generator: 8 typed tools, 2-4 dependent calls, argument values copied from numbered
   context fields, hint channel with randomized presence x randomized correctness (reliability tuned to 70-80%), gold-
   irrelevant distractor fields, full execution log. ~300 English template strings.
2. Renderers: de and zh templates produced ONCE by google/madlad400-3b-mt @fa184c675da0b5c9e1c8694fccd4e12e2d422094
   (Apache-2.0) with round-trip back-translation check (chrF >= 60, else hand-fixed), committed as JSON so rendering
   is deterministic and pinned; syn transform; anchor-randomized renderer (arm D); English paraphrase pool (5 per
   template) produced by Qwen/Qwen3.5-4B @851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a (Apache-2.0), committed.
3. Doctors: pair-semantics (identical logs and gold actions across members); rate (H(a_t | h_t) <= 30 bits measured;
   slack >= 98 bits); leakage (executor input ids contain no x^L tokens; monitor sees only z — asserted on the graph);
   label-intervention (gold action invariant to hint removal; distractor perturbation leaves gold unchanged);
   monitor-metric (a hand-built canonical code that encodes plan + reliance bit gives Delta = 0 and AUROC 1.0; random
   codes give AUROC 0.50 +/- 0.02); base-rate doctor for y_hint; Qwen3 tokenizer fertility for de/zh/syn measured and
   disclosed (controls are iso-instance/iso-step; token counts reported, not assumed equal).
4. Training loop: plain PyTorch 2.11 + transformers (+ accelerate, already in pyproject), straight-through Gumbel,
   leader/follower pairing, executor; SIGUSR1 checkpoint/resume through the existing harness runner contract.

GPU work (phase 0): arms A, B, C at 1 seed on qwen3-0.6b-base; 30k world instances x 4 renderings (en, de, zh, syn),
~900 tokens per instance across steps, 2 epochs = ~108M tokens per arm (every arm processes both members of every
pair, so A is iso-data). Counterfactual labeling by vLLM-served greedy generation (2 interventions x 3k eval instances x
4 languages x 3 arms). Monitors on CPU/one GPU.

**Phase 1 (separately gated on phase 0 passing K1-K3; <= 12 GPU-hours):** arms D, E, G, B' (1 seed), second seeds for
A, B, C, D, G; labeling for all new runs; MADLAD translate-then-monitor and consistency-trained monitors for G;
real-data replication of A/B/C (1 seed) on GSM8KInstruct_Parallel + calculator tool (en/de/zh/sw), evaluated on MGSM and
MSVAMP with an n-gram contamination probe for qwen3-0.6b-base.

**Confirmation (separate contract, not budgeted here):** qwen3.5-4b full FT (~40 GPU-h); Tinker Qwen3.5-4B/9B LoRA RL
with the sequence-level EM reward 1 - EM(z^A, z^B) on sampled parallel traces (the only L_inv form compatible with
Tinker's logprob-only losses), training data GSM8KInstruct_Parallel / ReasonXL (toroe/ReasonXL-SFT @321da71a, Apache-2.0),
evaluation MGSM/MSVAMP; 5 seeds. The 13-language GPQA set of 2605.27901 is an evaluation benchmark and is NOT used
for training.

### Budget (cited throughput anchor, conservative de-rating, 25% reserve)

Anchor: the llm.c GPT-2 124M reproduction on 8xH100 "needed 45 minutes" for its 10B-token run, as documented in the
modded-nanogpt README (https://github.com/KellerJordan/modded-nanogpt, fetched 2026-09-01; the 10B-token count is
from llm.c discussion #481, https://github.com/karpathy/llm.c/discussions/481, not re-opened this pass) = ~3.7M
tokens/s total = 6 x 124e6 x 3.7e6 / 8 = ~344 TFLOP/s per GPU = ~35% of H100 dense BF16 peak (989 TFLOP/s, NVIDIA H100
datasheet). A HF-transformers full fine-tune of a 0.6B model with a straight-through code, an executor and pair
bookkeeping will not reach that; the budget uses 150 TFLOP/s per GPU (~15% MFU, a 2.3x de-rating).

- FLOPs per token (fwd+bwd, full FT, N = 0.6e9 incl. LM head): 6N = 3.6e9. Executor (8M) negligible.
- Per arm: 1.08e8 tokens x 3.6e9 = 3.9e17 FLOP / 1.5e14 FLOP/s = 2,600 s = 0.72 GPU-h (~5.4 min wall clock on 8 GPUs).
  Arm G: <= 48-token traces + a frozen-LM forward for the KL: ~1.2 GPU-h.
- Phase 0: 3 arms x 0.72 = 2.2 GPU-h; labeling (~72k episodes, ~13M generated tokens via vLLM at >= 10k tok/s/GPU) 0.4;
  monitors 0.1. Subtotal 2.7; x 1.25 reserve = **3.4 GPU-h (<= 4)**.
- Phase 1: D, E, B' (3 x 0.72) + G (1.2) + second seeds A, B, C, D (4 x 0.72) + G (1.2) = 8.2; labeling 1.0; MADLAD MT +
  consistency monitors 0.3; real-data A/B/C (7.3k x 4 languages x 2 epochs x ~400 tokens = ~23M tokens; 3 x 0.15) 0.5 +
  labeling 0.3. Subtotal 10.3; x 1.25 = **12.9 GPU-h**; trimmed to <= 12 by running E and B' at 1 epoch if needed.
- Total <= 16 GPU-h. LoRA (r = 64) would cut per-arm cost by roughly a third; the budget uses the full-FT upper bound.

**pilot_gpu_hours.** 4 (phase 0, the decisive kill screen). Phase 1 is separately gated at <= 12.

### Honest infrastructure state
grep of /Users/kevinliu/repos/cotcodec finds no oracle world, no straight-through/Gumbel code, no policy training loop
(harness/training/tinker_backend.py is a pydantic contract; torch appears in memory_trials/models.py, smoke scripts
and CUDA doctors). The Slurm/Docker/SIGUSR1 checkpoint contract, agent-loop and receipt/ledger machinery exist and
are reused. First GPU hour is ~4-6 engineering days away; this is accepted and stated, not hidden.

## 8. Controls

- Iso-data no-pair arm A (the counterfactual reference for the primary endpoint; sees the same rendered instances).
- Same-log same-language paraphrase pairs C (discriminating placebo; the random-pair placebo of wave 1 is DROPPED
  because it is not inert — it forces identical codes on instances with different actions and conflicts with L_task).
- Anchor-randomized translation pairs D (mOthello control).
- English-pivot alignment B' (M-Thinker / SOLAR form; stop-gradient on English).
- Language-ID adversary E (invariance without pairs).
- Synthetic language syn (competence-equal control) in every arm.
- Explicit CoT G on the SAME multilingual base with the SAME task loss and no disclosure reward; fluency doctor;
  additionally a non-iso prompted Qwen3.5-4B zero-shot CoT reference, labeled non-iso.
- Monitor-side: action-only monitor (Delta = 0 floor); per-language monitors (ceiling); translate-then-monitor with
  pinned MADLAD-400-3B-MT; xTune-style consistency-trained M_en; activation-probe monitor on the policy's residual
  stream (2608.04928 style) reported alongside.
- lambda_inv selected by task accuracy only; all lambda values reported. Monitor train/test split by template family,
  disjoint from policy training templates. Instance-level paired bootstrap; McNemar over pairs for catch rates.
- Strongest published baselines named: 2603.08177 (emergent invariance), M-Thinker (pivot alignment), xTune
  (consistency-trained classifier), translate-test (Artetxe et al. 2023, https://arxiv.org/abs/2305.14240).
- Disclosure: token counts per language, label base rates per arm and language, contamination probe for MGSM.

## 9. Kevin advantage

Modest at the pilot, by design: every phase-0/phase-1 input is public and pinned, so any lab could run it. Assets
that matter: 8xH100 with the Slurm/Docker/checkpoint harness makes a 9-arm x 2-seed x 4-language design routine;
Tinker Qwen3.5-4B/9B carries the RL confirmation with the EM-reward form. General Translation is an OPTIONAL upgrade
only: professionally translated tool-use suites with terminology control (the scarce object; ReasonXL covers five
European languages of math/general traces), low-resource and non-Latin-script coverage (abugidas, RTL), and
production MT as one more translate-then-monitor arm. No pre-registered endpoint requires GT data or customer content.

## 10. Collision risk

medium. Searches run this pass: hostsearch arXiv x4 and HF papers x1 (queries listed in section 3), abstract reads of
2510.07300 and 2608.23809; wave-1 refuters' 28 URLs re-used. Active groups that could add a monitor endpoint: M-Thinker,
SOLAR, GI-SAE (2608.23809), and the 2605.27901 authors (public code + 13-language set).

## 11. Monitorability and safety

Positive: monitor portability across languages; the executor bottleneck guarantees a decoded plan is always
available to a human or a weak model. Risks: (a) invariance can erase language-specific cues a monitor needs (an
injection written in the input language) — per-language injection detection is reported alongside Delta_L; (b) a
128-bit code with slack can carry steganographic content and cannot expose misbehaviors outside what the monitor was
trained on (the VFT-style objection) — the monitor's held-out labels and I(z; language) are reported, and this is
stated as a limitation, not a solved problem; (c) no English gloss is used any more, so English-centric review is not
introduced. Data rights: Qwen3-0.6B-Base, Qwen3.5-4B, MADLAD-400-3B-MT, GSM8KInstruct_Parallel, MSVAMP, ReasonXL all
Apache-2.0; MGSM CC-BY-SA-4.0; MathOctopus code MIT (https://github.com/microsoft/MathOctopus); generated templates and
translations committed under the repo license; no customer data.

## 12. Negative-result value

- K1 (A ~ B): emergent invariance suffices for trained discrete codes at 0.6B — extends 2603.08177 and 2608.23809 to an
  intervention setting and confirms 2603.29026 at the reasoning-code level; parallel supervision is unnecessary.
- K2 (C ~ B): any same-log equivalence class suffices; translation data is not the asset; cheaper paraphrase pairs
  become the recommended regularizer.
- K3 (z-monitor <= action floor): executor-bottleneck plan codes carry no reliance information beyond actions —
  bounds the monitorability of discrete plan codes for the whole D-angle.
- K4 (D fails): invariance was anchor-driven; mOthello extends to reasoning codes.
- K5: translate-then-monitor with open MT is the recommended practice, with a measured cost curve.
- In every case the bilingual oracle world, the intervention-defined label instrument and the monitor-transfer
  protocol remain reusable for the G2/G13 translation-paired probes and for latent-reasoning gap 2.

## 13. targets_gaps

G15, G14, G20 (as in wave 1); latent-reasoning gap 2 (translation-equivariant abstract reasoning codes, monitor
trained in one language tested in others); benchmarks-eval G2 (cross-lingual translation-paired probes).

## 14. Public data plan (no General Translation data required)

| role | source | license | pinned |
|---|---|---|---|
| Policy base (all arms) | Qwen/Qwen3-0.6B-Base (registry `qwen3-0.6b-base`) | Apache-2.0 | da87bfb608c14b7cf20ba1ce41287e8de496c0cd |
| Paraphrase pool; non-iso explicit reference | Qwen/Qwen3.5-4B (registry `qwen3.5-4b`) | Apache-2.0 | 851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a |
| Template translation en->de/zh; translate-then-monitor; consistency-monitor augmentation | google/madlad400-3b-mt (to be added to registry) | Apache-2.0 | fa184c675da0b5c9e1c8694fccd4e12e2d422094 |
| Oracle world `ToyTools-XL` (templates, renderers, logs) | generated; committed to repo | repo license | commit hash at phase-0 seal |
| Real parallel training data (phase 1 / confirmation) | https://huggingface.co/datasets/Mathoctopus/GSM8KInstruct_Parallel (7,473 GSM8K train problems x 10 languages: en zh es fr th sw ja bn de ru) | Apache-2.0 | dd8076b83bacd7c6ade2829317e8a500c6ffbec4 |
| Real parallel evaluation | https://huggingface.co/datasets/juletxara/mgsm (250 x 10, human-translated) | CC-BY-SA-4.0 | b2f13d426afe3be8d69a7e739b36724db8b66bbc |
| Real parallel evaluation (OOD) | https://huggingface.co/datasets/Mathoctopus/MSVAMP (10 languages) | Apache-2.0 | 301e2b3b168be70058c89c21c2fbdc9262102add |
| Explicit-CoT parallel corpus (confirmation warm-start) | https://huggingface.co/datasets/toroe/ReasonXL-SFT (en de fr es it) | Apache-2.0 | 321da71a81762dd28b3462e25cde4be3e7103840 |

Dropped from wave 1: FLORES-plus as a test set (sentence pairs, no tasks or logs); the 13-language GPQA set as
training data; SmolLM2-135M as a policy (English-only pretraining, 2502.02737); General Translation MT as a pipeline
dependency. GT data enters only as the optional upgrade in section 9.

## 15. Repairs made (each wave-1 objection -> fix or accepted limitation)

Identification lens
1. Mechanism redundancy (reader anchoring on language-neutral m forces an invariant code; L_inv acts only on eps
   slack) -> FIXED: the reader term is removed; the medium is an executor-bottleneck code with 128 bits of capacity
   against <= 30 bits of action entropy, so language leakage is possible; the no-L_inv arm A is iso-data and its
   Delta_L is the pre-registered primary counterfactual reference (Delta_L(A) - Delta_L(B)).
2. Label leakage / trained-to-disclose (catch-rate targets were components of the RL target) -> FIXED: no monitor
   variable appears in any loss; labels are intervention-defined counterfactuals (y_hint, y_spur) computed on the
   trained policy after training, including "rescued-by-correct-hint" cases invisible to action-only monitors; the
   action-only monitor floor is added (K3); the explicit-CoT arm receives the same task loss and no disclosure reward.
3. Anchor shortcut (shared tool ids / field numbers drive alignment) -> FIXED: arm D with per-language opaque
   bijections of tool ids and field labels and numerals-as-words; K4 and P2 pre-registered.
4. Undertuned comparators (English-only SmolLM2 cannot produce de/zh CoT; unsourced ">= 20 points" and
   "translate-then-monitor stalls") -> FIXED: all arms on the multilingual Qwen3-0.6B-Base; syn as competence-equal
   control; xTune-style consistency-trained M_en and translate-test added as matched monitor-side controls; the
   unsourced numbers are withdrawn from the claim and replaced by measured secondary predictions (P3) with stated
   lower confidence; 2605.27901 is cited as motivation only.
5. Placebo mismatch (random-pair placebo conflicts with L_task) -> FIXED: dropped as non-inert; replaced by same-log
   same-language paraphrase pairs (C) as the discriminating placebo (K2), plus anchor-randomized pairs (D).

Feasibility lens
1. Hidden prerequisite on candidate 11 and zero infrastructure -> FIXED: decoupled; the medium is self-contained
   and differentiable (no RL, no frozen reader, no adversary in phase 0); the missing infrastructure is inventoried
   and costed (~4-6 engineering days) rather than hidden. ACCEPTED LIMITATION: the first GPU hour is not immediate.
2. GPU-hour count on/over ceiling -> FIXED: re-budgeted with a first-party throughput anchor (llm.c 124M on 8xH100 via
   modded-nanogpt README), a 2.3x de-rating to 150 TFLOP/s per GPU, pair processing counted explicitly, 25% reserve;
   phase 0 = 3.4 GPU-h decisive on K1-K3; phase 1 <= 12 GPU-h separately gated; total <= 16.
3. Unnamed / unregistered data (200M de/zh tokens, GT MT, SmolLM2 fertility, FLORES/MGSM misuse) -> FIXED: no
   continued pretraining needed (multilingual base); MADLAD-400-3B-MT pinned with committed outputs replaces GT MT;
   SmolLM2 dropped; tokenizer fertility measured and disclosed with iso-instance/iso-step controls; FLORES dropped;
   MGSM/MSVAMP used only with the calculator-tool wrapper and a contamination probe.
4. Cannot attribute the endpoint to parallel data -> FIXED: the A/B/C/D factorial identifies the pairing term
   specifically; K1 and K2 make the attribution failure modes explicit kills.
5. Baseline contrast without a source -> FIXED as in identification item 4.
6. Confirmation inputs not concrete (13-language GPQA as RL training data) -> FIXED: confirmation trains on
   GSM8KInstruct_Parallel / ReasonXL and evaluates on MGSM/MSVAMP; GPQA-13 is evaluation-only if used at all.

Novelty lens (not refuted; caveats)
- M-Thinker (2510.07300) added to closest priors and as arm B' (English-pivot alignment) -> DONE.
- "No direct prior art" narrowed to the discrete-medium + symmetric-pair + intervention-label + monitor-transfer
  combination; the loss FORM is acknowledged as published -> DONE.

Accepted limitations
- The oracle world is templated; real-language richness is limited (mitigated by the GSM8KInstruct_Parallel
  replication and the confirmation stage).
- Arm G (straight-through NL tokens + KL fluency prior) approximates natural CoT; a non-iso prompted Qwen3.5-4B
  reference is reported alongside and labeled as such.
- Counterfactual labels are policy-specific (each arm's labels come from its own policy); within-arm transfer is the
  question, and label base rates are reported per arm and language for cross-arm reading.
- 0.6B scale; 1 seed in phase 0 (2 in phase 1, 5 at confirmation) — below the benchmarks-eval G1 norm; effect sizes
  are pre-registered at >= 5 AUROC points with >= 3k paired instances so the phase-0 screen is powered for the
  primary contrast but not for small secondary effects.
