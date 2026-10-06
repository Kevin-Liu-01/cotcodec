# Inventor D — monitorable reasoning media (2026-09-01)

Angle: latent/abstract reasoning media that a weaker monitor can decode **by construction**, tool-use
compatible, ideally translation-equivariant. Targets synthesis gaps G14, G15 (and G16 as controls, G20 as
instruments); the latent-reasoning cell's open items 1, 2, 4, 5, 6; the triage's "monitorability of what a
loop computes" and "cross-lingual monitorability" axes.

Inputs read in full: `context.md`, `design/brief.md` (including the 2026-09-01 verification-pass
corrections), `sweep/synthesis.md` (all sections), `sweep/latent-reasoning.md`,
`sweep/arxiv-triage-adapt-reason-diff.md`, `directions/15-interpretable-abstract-reasoning.md`, the
reasoning-media rows of `research/frontier-systems-program-2026-08-10.md`, and the sibling notes' candidate
lists (F candidate C `language-invariant-latent-length`, C note §"meaning-level state", G note's
provenance-mass monitor channel) to avoid internal duplication.

Honesty rules: every prior below carries a URL and a date; "opened" means I read the arXiv abstract page
through WebFetch during this session; "cell-read" means the latent-reasoning cell read it (abstract or HTML)
and I rely on its extraction; body-level numbers taken from cell notes come from WebFetch summaries and may
carry transcription error. Novelty wording is always "No direct prior art found through 2026-09-01 under
<coverage>".

---

## 0. Verdict in six lines

1. Every *medium* in Direction 15 is occupied at ≤ 8B on math/QA (Abstract-CoT, Coconut/CODI lineage,
   SIM-CoT/SELR/LatentGuard/ALCA decoders, MUX/J-CoT/DiscoLoop/Thinking-States/SWITCH, looped LMs). What
   no source does is make the medium legible to a monitor that was **fixed before training and is weaker
   than the policy**, bound the code's hidden capacity, and test it on tool-use tasks under obfuscation.
2. The three legibility-by-training lines that exist (Prover-Verifier Games and its decoupled successor,
   Markovian Transformers, TELLME) all co-train or self-decode in **natural language**; the steganography
   lines (Skaf et al. NeurIPS 2025, NEST, Conceptual Steganography) measure hidden channels in NL CoT and
   defend with paraphrasers, never with a rate bound. A low-rate abstract code anchored to a frozen reader
   is the one design that admits an explicit slack bound — and it is untested.
3. Cross-lingual monitorability has one n=8 case study; the only "invariance" result for latent media is
   an emergent claim about CODI (2603.08177), with no parallel supervision, no decoder and no monitor.
   Parallel data as supervision for a *decodable* trace with a monitor trained in one language and tested in
   others is unclaimed under this coverage; 2603.08177 becomes the mandatory "emergent invariance" control.
4. Recurrent-depth LMs now cover compositional tool calling (2608.18171) but nobody reads or bounds what
   the loop carries between iterations; DiffusionGemma's token-bottleneck result (28.6× → 1.1× opaque serial
   depth at no loss) is the existence proof that a legible bottleneck can be free — for diffusion only.
5. Three candidates: **C1 `frozen-reader-anchored-codes`** (cheap decisive, ≤ 14 GPU-h, 135M, synthetic
   tool world); **C2 `interlingua-trace-codes`** (moonshot, Kevin's parallel-data asset, 14 GPU-h screen →
   Tinker stage); **C3 `metered-opaque-channel-recurrence`** (architecture-causal, 15 GPU-h screen).
   C2 and C3 reuse C1's frozen-reader anchoring and slack instrument; that shared machinery is stated, not
   hidden.
6. Collision is medium for all three: the monitorability field is filling weekly (FACE-Eval, HCDS,
   Intent-as-a-Tool, ALCA, weak-to-strong legibility all landed in 2026), and GDM's transparency group is
   one paper away from applying its bottleneck to looped models.

---

## 1. Occupied map for angle D (mechanism-merged; URLs and dates)

| Axis | Taken by | Status | What remains |
|---|---|---|---|
| Discrete abstract-token media | Abstract-CoT https://arxiv.org/abs/2604.22709 (2026-04-24; cell-read; no code, three failed reproductions); Token Assorted 2502.03275; iCLP 2512.24014; DLR 2606.29712; Heima 2501.19201 (ICML 2026) | occupied | replication with token-necessity ablations (G16); monitor legibility; tool argument fidelity |
| Decoders for latents | SIM-CoT https://arxiv.org/abs/2509.20317 (2025-09-24; opened: auxiliary decoder trained jointly, removed at inference, no monitoring); SELR 2608.13570 (ICML 2026; same-model decoding); LatentGuard https://arxiv.org/abs/2608.03838 (2026-08-04; opened: isolated audit decoder, training regime unspecified in abstract); ALCA https://aclanthology.org/2026.acl-long.1570/ (ACL 2026; opened: continuous latent safety deliberation + "restricted Self-Decoding", no tool use/obfuscation/cross-lingual in abstract) | occupied for co-trained / self decoders | a **frozen, weaker, pre-committed** reader; held-out-monitor evaluation; obfuscation pressure; tool-use tasks |
| Interpretable-by-construction latents | MUX https://arxiv.org/abs/2607.18264 (2026-05-19; opened: lossless multiplexing by geometric weights; probing shows interpretable tokens; no monitor/obfuscation/tool use); J-CoT 2607.21981; DiscoLoop https://arxiv.org/abs/2607.00341 (2026-07-01; opened); Thinking States 2602.08332; SWITCH 2606.13106; LSTR 2602.01695; DiffusionGemma bottleneck https://arxiv.org/abs/2606.20560 (2026-06-18/08-17; opened) | occupied as mechanisms | any evaluation as a monitor channel under attack; capacity accounting; tool use |
| Legibility by training (NL) | Prover-Verifier Games https://arxiv.org/abs/2407.13692 (2024-07-18; opened: small verifiers trained iteratively/jointly); Decoupled PVG https://arxiv.org/abs/2602.23248 (2026-02-26; opened: translator turns a fixed solver's solution into a checkable form; names the "legibility tax"); Markovian Transformers https://arxiv.org/abs/2404.18988 (2024-04-29, v8 2026-03-10; opened: bounded-length NL CoT bottleneck, same model answers from CoT alone, KL to pretrained prior "discourages steganographic encoding"); TELLME https://arxiv.org/abs/2502.05242 (2025-02-07; opened, method not in abstract); Measuring Weak-to-Strong Legibility https://arxiv.org/abs/2603.20508 (2026-03-20; opened: measurement only) | occupied for NL media | the same move for **abstract/latent** media, where no NL prior exists to discourage steganography |
| Steganography / hidden channels in CoT | Skaf et al. https://arxiv.org/abs/2506.01926 (NeurIPS 2025; opened); NEST https://arxiv.org/abs/2602.14095 (2026-02-15; opened: frontier models cannot sustain joint reason-and-embed; filler baseline dominates); Conceptual Steganography https://arxiv.org/abs/2605.26537 (2026-05-26; opened: behavior-level channel survives paraphrase; defense = strategy-aware paraphraser); Not All Reasoning Visible 2607.22925; Reading Between the Dots 2607.03502 | occupied for NL | a **rate bound by construction** (T·log2 K − H(m)) and a collusion-probe measurement for latent media |
| Monitorability of latent vs explicit | Out-of-Sight https://arxiv.org/abs/2608.04928 (2026-08-05; opened: CODI/SIM-CoT on Llama-3.2-1B, math/QA, induced hints; access to internals matters more than mode); Ulterior Motives 2604.23460; Are Latent Reasoning Models Easily Interpretable? 2604.04902 (COLM 2026) | occupied at 1B math/QA | tool-use agent tasks; a *training* constraint that makes the medium monitorable; held-out weak monitors |
| Cross-lingual monitorability / invariance | Fragility across 13 languages https://arxiv.org/abs/2605.27901 (2026-05-27; opened: 95.9% unfaithfulness, no medium proposed); En/Ta/Tanglish case study 2608.15392 (n=8); Not-yet-multilingual latent reasoners https://arxiv.org/abs/2601.02996 (ACL 2026 Findings; opened: diagnostic, English-centered pathway); SOLAR https://arxiv.org/abs/2606.26466 (2026-06-25; opened: continuous soft tokens aligned to an English pivot for accuracy); Is continuous CoT better suited for multilingual reasoning? https://arxiv.org/abs/2603.08177 (2026-03-09; opened: CODI shows emergent language invariance, 29–50× compression, no parallel data, no monitor); UL-XCoT https://arxiv.org/abs/2604.20090 (2026-04-22; opened: inference-time language-invariant logic space for pruning explicit XCoT); ReasonXL https://arxiv.org/abs/2604.12378 (2026-04-14; opened: 2M aligned reasoning traces per language in 5 European languages; language shifting, no monitor); audio multilingual workspace 2608.24958 (cell-read) | measurement + accuracy only | a **parallel-supervised, decodable, discrete** trace evaluated by monitor transfer against a translate-then-monitor baseline |
| Recurrent depth × tools | Looped LMs improve compositional tool calling https://arxiv.org/abs/2608.18171 (2026-08-17; opened: API-Bank/BFCL/NESTful, no probing of loop state); GRT 2608.15062; Ouro 2510.25741; iso-depth law φ=0.46 2604.21106; Opaque serial depth https://arxiv.org/abs/2603.09786 (2026-03-10; opened: defines/upper-bounds depth; no bandwidth notion, no constraint proposed) | occupied for capability | what the loop carries between iterations, its bandwidth, and its legibility on multi-turn tool tasks |

Re-confirmed rejections honored: no generic latent loop with halting (C3 uses fixed R and claims
monitorability bandwidth, not efficiency); no verbal-checkpoint hybrid (SELR/ALCA hold it); no
"parallel data → consistent routing" (SARA/RA-MoE per the verification pass; C2 constrains the *trace*).

---

## 2. Shared machinery (stated once)

**Frozen-reader anchoring.** A reader R_φ (weaker than the policy) is fixed *before* policy training:
its embedding table is extended by K rows initialized from the mean-pooled embeddings of K seed gloss
phrases g_k (the gloss dictionary G), a linear head H is fitted once on (gloss-rendered explicit CoT →
monitor variables m), then φ, E_C, H are frozen. m is always read from the **environment log** (executed
tool, argument-source slots, causal hint intervention, constraint check), never from the model. The
policy receives −log p_{R_φ}(m | z) as a reward/loss term. Because φ never moves, the policy cannot
negotiate a private code with its reader (the failure mode of joint prover–verifier training and of
same-model decoding); the only way to raise the term is to use the codebook in the reader's pre-existing
gloss semantics.

**Rate ledger and slack bound.** For a discrete trace z of T tokens over K symbols, C_z = T·log2 K bits.
Set C_z = H(m) + ε. Then for any side-information s independent of the task,
I(z; s) ≤ H(z) − I(z; m) ≤ T·log2 K − H(m) + H(m | z) = ε + H(m | z).
ε is the designed slack; H(m | z) is the reader's residual uncertainty (reported, not assumed). The
bound is checked empirically with a **collusion probe**: a secret s ∈ {0,1}^32 is injected into the
input, the policy is rewarded (in a separate run) for letting a colluder D_col recover s from z; recovered
bits above ε + H(m | z) + 2 falsify tightness. This is the instrument NL CoT cannot have (its rate is
unbounded), which yields the counter-intuitive prediction that a low-rate anchored code has *less*
steganographic slack than explicit CoT.

**Held-out monitor.** Legibility is never scored with the training reader. A fresh monitor M (135M
classifier) is trained post hoc on (z, m) from disjoint task templates; humans get the dictionary
rendering G(z). Attacks: reasoning-rewrite/re-encoder (2608.00583-style; a re-encoder trained to keep
task reward while minimizing M's AUROC) and monitor-awareness pressure (2605.15257-style synthetic
documents). Baker-style check: monitor-flagged violations vs environment-logged violations across
training; divergence = performative legibility, a pre-registered kill.

**Oracle world.** "ToyTools": 8 typed tools (lookup, arithmetic, compare, filter, write, …), tasks
needing 2–4 dependent calls, argument values copied from numbered context fields, a hint channel with
randomized presence × randomized correctness (so hint-use is causally identified), injected tool
failures requiring diagnosis, and a full execution log. Generated in English and, for C2, rendered in
de/zh through General Translation MT with glossary checks plus one synthetic-language transform.
Multi-turn variant for C3 (3-hop compositions across turns). Borrowed from the inverted-IFEval oracle
idea (2608.11095) and the 30M oracle-world protocol (2608.16085).

---

## 3. Candidate C1 — `frozen-reader-anchored-codes` (cheap decisive)

**Claim.** An abstract discrete reasoning medium trained under a frozen, weaker, pre-committed reader
with a rate-matched codebook is decodable by a held-out weak monitor at ≥ 90% of explicit-CoT
monitorability while compressing reasoning ≥ 3×, resists reasoning-rewrite attacks that collapse both
co-trained-decoder latents and explicit CoT, and carries provably and measurably less steganographic
slack than natural-language CoT.

**claim_scope.** attachment-capability (a post-training medium + frozen reader attachable to any base).

**Mechanism.** Policy π_θ (smollm2-135m at the screen; qwen3-0.6b-base / qwen3.5-4b at confirmation)
emits, between observation o_t and action a_t, a trace z_t = (z_{t,1..T}) over a reserved codebook C,
|C| = K, then the action in explicit text (tool name and JSON arguments are never abstracted). Reader R_φ
is a from-scratch 20M LM (or frozen smollm2-135m) with the extended embedding rows E_C and head H,
frozen after a one-off fit on gloss-rendered teacher traces. Warm-up: SFT with straight-through
Gumbel-softmax on z toward gloss-rendered teacher traces (≈ 50M tokens). RL: GRPO with
r = r_task + λ_R · log p_{R_φ}(m_t | z_t) − λ_len · T, where m_t = (next tool id, argument-source slots,
hint-use flag, constraint-violation flag) from the environment log. Rate matching: (K, T) chosen so that
T·log2 K = H(m) + ε with ε ∈ {4, 64}; K = 64, T = 8 gives 48 bits against H(m) ≈ 40–44 bits in ToyTools
(computed by the phase-0 doctor from the generator's label distribution). Reader-strength ladder as arms:
dictionary (zero-parameter gloss lookup) → frozen 20M → frozen 135M → co-trained 135M (SIM-CoT-style) →
same-model (SELR/ALCA-style). Evaluation: held-out monitor M; collusion probe; re-encoder attack;
monitor-awareness pressure; Baker-style flagged-vs-logged check; token-necessity ablations
(random/zero/shuffled prefix, the LauraGG protocol).

**what_is_new.**
- vs Prover-Verifier Games — https://arxiv.org/abs/2407.13692 (2024-07-18; opened): PVG iteratively
  trains small verifiers *jointly* with helpful and sneaky provers so NL solutions become checkable; the
  delta is a reader frozen before policy training (no co-adaptation), a low-rate abstract code instead of
  NL, environment-logged action variables instead of solution correctness, and a measured slack bound.
- vs Markovian Transformers — https://arxiv.org/abs/2404.18988 (v1 2024-04-29, v8 2026-03-10; opened):
  forces question→answer information through a bounded-length NL CoT read by the same model and relies on
  the KL-to-pretrained prior to discourage steganography; the delta is that an abstract code has no NL
  prior, so legibility is enforced by an external frozen weaker reader plus explicit rate matching, and
  the consumer is that reader, not the policy.
- vs LatentGuard — https://arxiv.org/abs/2608.03838 (2026-08-04; opened, abstract-level) and its
  siblings SIM-CoT https://arxiv.org/abs/2509.20317 (2025-09-24; opened) / SELR 2608.13570 / ALCA
  https://aclanthology.org/2026.acl-long.1570/ (ACL 2026; opened): decoders are co-trained, isolated-but-
  trained, or the model itself, and are scored by audit utility or accuracy; the delta is a frozen weaker
  reader, a held-out monitor, obfuscation attacks, tool-use tasks and a capacity ledger.
- vs Decoupled PVG — https://arxiv.org/abs/2602.23248 (2026-02-26; opened): a translator makes a fixed
  solver's NL solution checkable; the delta is constraining the medium itself (no translator, no second
  pass) and measuring the legibility tax on an abstract medium.
- vs R-Capsule — https://arxiv.org/abs/2509.22131 (2025-09-26; opened): IB-style low-capacity plan
  capsules with a same-model plan-reconstruction loss and no monitor; the delta is external frozen
  decodability and the explicit ε accounting.
No direct prior art found through 2026-09-01 under §7 coverage for a frozen weaker reader + rate-matched
abstract code + collusion-probe slack measurement on tool-use tasks.

**falsifiable_predictions.**
- P1 (ToyTools, 135M policy, frozen 20M reader, K = 64, T = 8, ε ≈ 4 bits): held-out weak-monitor AUROC
  for (next tool, hint-use) ≥ 0.85 and ≥ 90% of the explicit-CoT monitor's AUROC, at ≥ 3× fewer reasoning
  tokens; the matched-(K, T) co-trained-decoder arm scores ≤ 0.70 with the same held-out monitor (gap ≥ 0.15).
- P2 (slack): the collusion probe recovers ≤ ε + H(m | z) + 2 bits of a 32-bit secret on C1, ≥ 16 bits on
  the unconstrained reserved-vocabulary arm, and ≥ 12 bits on explicit NL CoT at matched task accuracy.
- P3 (obfuscation): under the re-encoder attack with task accuracy held within 1 pp, C1's held-out
  monitor AUROC drops ≤ 0.10, versus ≥ 0.30 for the co-trained-decoder arm and ≥ 0.40 for explicit-CoT
  paraphrase (2608.00583 reports ~95% → < 11% catch rate under reasoning rewrites).
- P4 (legibility tax and necessity): task accuracy within 2 pp of explicit CoT; random/zero/shuffled
  prefix ablation costs ≥ 10 pp (the code is load-bearing, unlike the LauraGG negative where random tokens
  matched learned ones, 54% vs 51%).

**kill_conditions.** Held-out monitor AUROC < 0.70 for C1 while explicit CoT ≥ 0.85 at matched
accuracy (frozen anchoring does not transfer to a reader that was not the training reader); legibility tax
> 5 pp versus explicit CoT at 135M and again at qwen3-0.6b-base; collusion slack not reduced versus the
unconstrained code because H(m | z) stays large (the policy will not saturate the reader term); Baker-style
divergence between monitor-flagged and environment-logged violations (performative legibility).

**cheapest_decisive_pilot.** Phase 0 (CPU, 0 GPU-h, ~2 days): ToyTools generator with execution log;
H(m) and the (K, T, ε) table; doctors — reader sees only z, monitor split disjoint by task template, labels
from the log, secret s independent of task; dictionary-decoder null on random codes (AUROC 0.50 ± 0.02);
straight-through gradient check. Phase 1 (~14 GPU-h on 8×H100): frozen 20M reader fit on gloss sequences
(1 GPU-h); arms × 2 seeds on smollm2-135m — explicit CoT, length-penalized CoT at matched tokens,
unconstrained reserved-vocab code, C1 with ε = 4 and ε = 64, SIM-CoT-style co-trained decoder (6 arms × 2
seeds × ~1 GPU-h = 12 GPU-h: SFT warm-up ≈ 50M tokens + GRPO ≈ 30k episodes each); held-out monitors,
collusion probes, re-encoder attacks (~1 GPU-h). Confirmation (separate contract): qwen3-0.6b-base, then
qwen3.5-4b on BFCL-multi-turn / τ²-style tasks; Tinker Qwen3.5-4B LoRA RL for the escalation policy
(≈ 100M tokens), evaluation-only for legibility (Tinker exposes no internals).

**controls.** Explicit CoT on the same base with the same held-out monitor; length-penalized CoT at
matched tokens (2607.09786); Abstract-CoT-style unconstrained code at identical (K, T) (2604.22709);
SIM-CoT-style co-trained decoder (2509.20317); SELR/ALCA-style self-decoding (2608.13570; ACL 2026);
ALAR-style latent/think switching at matched tokens (2606.02871); Markovian NL bottleneck at matched CoT
length (2404.18988); activation-probe monitor as the access ceiling (2608.04928); reader-strength ladder;
random/zero/shuffled prefix ablations; iso-parameter, iso-token, paired McNemar; contamination disclosure.

**kevin_advantage.** Modest: none unique at the 135M screen (any lab can run it). The harness's
agent-loop, oracle, trace and paired-regression contracts plus SIGUSR1-resumable RL make the many-arm
design cheap; 8×H100 and Tinker Qwen3.5-4B carry the confirmation; parallel data enters only through C2.

**collision_risk.** medium. Searches (hostsearch on the H100 host, 4 s spacing, log in
`design/D-search/collision.log`): arXiv `(steganography|steganographic) AND (CoT|latent reasoning|
continuous thought)` → 7 (NEST, Conceptual Steganography, Skaf et al., Markovian Transformers, Illegible CoT
2510.27338, safety-case roadmap 2510.19476, ImF) — all NL, none bounds capacity by construction; arXiv
`"information bottleneck" AND (CoT|latent reasoning) AND (monitor|monitorability|interpretable)` → 4
(R-Capsule the only relevant); arXiv `prover-verifier` → PVG, DPVG, Neural Interactive Proofs 2412.08897,
Neural Concept Verifier 2507.07532; arXiv `(legibility|legible) AND (CoT|latent reasoning) AND
(monitor|verifier|monitorability)` → 9 (2603.20508 measurement; 2510.23966; 2607.03502; 2608.24958); arXiv
`("frozen decoder"|"frozen monitor"|"weak monitor"|"weaker monitor"|"trusted monitor") AND (latent|CoT)` →
Bootstrapped Monitoring 2606.11998, CoT Red-Handed 2505.23575, Monitoring Monitorability 2512.18311; HF
papers `latent reasoning monitorability` → 20 (2604.04902, 2606.12689, TELLME 2502.05242, ThinkRouter
2602.11683, none with a frozen reader); OpenReview `latent reasoning steganography monitor` → 10 unlabeled
notes (not opened); ddg route bot-blocked; `ft search` legibility / prover verifier / steganography /
weak monitor → 0 relevant bookmarks. Drivers: OpenAI's legibility line, GDM's aligned-reward and
opaque-serial-depth groups, Ferreira–Aziz–Titov (a training constraint is their natural next step), ALCA's
authors, and the Skaf/Lindner steganography group.

**monitorability_and_safety.** Monitorability-positive by design. The reader term is "aligned" in the
2603.30036 sense (it rewards accurate exposure of environment-logged variables and never penalizes
content), but the Baker-style flagged-vs-logged check is pre-registered because any CoT reward can be
gamed; the frozen reader defines the set m, so anything outside m is protected only by ε — ε and H(m | z)
are reported as first-class quantities; the dictionary gloss keeps humans in the loop. Data: synthetic
ToyTools; public BFCL/τ²-style tasks; Apache-2.0 bases; no customer data.

**negative_result_value.** A clean negative shows that a frozen weaker reader cannot anchor a learned
low-rate code without a > 5 pp legibility tax — "monitorable by construction" abstract media are not free
and monitoring must rely on activations (2608.04928) or NL; the slack instrument (rate ledger + collusion
probe) and the ToyTools oracle world transfer to any medium including explicit CoT; a mixed result
(anchoring works, bound loose) quantifies where hidden bits go (H(m | z)) — a number no NL study can give.

**targets_gaps.** G14 (tool-use monitorability, cross-medium tax curve, by-construction latents under
obfuscation), G16 (token-necessity ablations as controls), G20 (instrument).  **pilot_gpu_hours.** 14.

---

## 4. Candidate C2 — `interlingua-trace-codes` (moonshot; Kevin's asset)

**Claim.** Supervising the anchored abstract trace with parallel problem pairs so that semantically
equivalent inputs in any language induce the same discrete trace (a decodable reasoning interlingua) lets
a monitor trained on English traces transfer to other languages with ≤ 5-point catch-rate loss where
explicit-CoT monitors lose ≥ 20 points and translate-then-monitor stalls — converting parallel translation
data into a monitorability asset rather than an accuracy aid.

**claim_scope.** portability-protocol (the monitor ports across languages by construction of the code).

**Mechanism.** Same medium and frozen reader as C1. Parallel pairs P = {(x^A, x^B)} share one ToyTools
instance, hence one execution log m and one answer up to language (JSON tool calls are language-neutral;
final answers follow the input language, so the *output* stays equivariant while the *trace* is made
invariant). Objective:
L = L_task + λ_R · L_reader + λ_inv · L_inv,
L_inv = E_{(A,B)∈P} Σ_{i=1}^{T} JS( q_θ(z_i | x^A, z_{<i}) , q_θ(z_i | x^B, z_{<i}) ),
computed with teacher forcing on a shared sampled prefix z_{<i} (symmetric — no pivot language is
privileged), optionally with a sequence-level REINFORCE term L_seq = 1 − EM(z^A, z^B). Alternative
invariance arm: a language-ID adversary on z through gradient reversal. Data: (i) ToyTools rendered in
en/de/zh by General Translation MT with glossary checks, plus one synthetic-language transform as a
controlled third language; (ii) at confirmation, FLORES-plus / GT-translated MGSM and BFCL-style prompts,
with ReasonXL's parallel traces as the explicit-CoT control corpus. Monitor-transfer protocol: train
M_en on (z, m) from English episodes only; test on every other language; report Δ_L = AUROC_en − AUROC_L
and catch rates for hint-use and constraint violations; the gloss decoder G renders any trace to an
English gloss for humans. Baselines that must be beaten: explicit CoT in language L with M_en;
**translate-then-monitor** (GT MT of the L-language CoT into English, then M_en) — the practical
alternative; SOLAR-style English-pivot soft-token alignment; a CODI-style continuous arm with no parallel
data (2603.08177's emergent invariance); a random-pair placebo for L_inv; per-language monitors as the
ceiling.

**what_is_new.**
- vs SOLAR — https://arxiv.org/abs/2606.26466 (2026-06-25; opened): aligns non-English *continuous*
  soft-token summaries to an English pivot to raise accuracy; the delta is symmetric invariance of a
  *discrete*, frozen-reader-decodable trace and cross-language monitor transfer on tool-use tasks as the
  endpoint.
- vs "Is continuous CoT better suited for multi-lingual reasoning?" — https://arxiv.org/abs/2603.08177
  (2026-03-09; opened): reports that CODI continuous latents *emergently* show language invariance
  (zero-shot to unseen languages, 29–50× compression) with no parallel data, decoder or monitor; the delta
  is explicit parallel-pair supervision on a decodable code, a placebo that tests whether parallel data
  adds anything over emergent invariance, and monitorability as the measured quantity.
- vs The Fragility of CoT Monitoring Across Typologically Diverse Languages —
  https://arxiv.org/abs/2605.27901 (2026-05-27; opened): measures 95.9% unfaithfulness and monitor
  fragility across 13 languages and proposes no medium; the delta is a medium designed so that a monitor
  trained in one language transfers, evaluated on their language set against translate-then-monitor.
- vs ReasonXL — https://arxiv.org/abs/2604.12378 (2026-04-14; opened): a 5-language parallel corpus of
  *explicit* reasoning traces used to shift the reasoning language; the delta is using pairs to make a
  latent trace language-*independent* and to port a monitor, with ReasonXL demoted to a control corpus.
Also positioned against 2601.02996 (diagnostic; English-centered latent pathway; opened), UL-XCoT
2604.20090 (inference-time language-invariant logic space for pruning; opened), 2608.24958 (language-
agnostic readable workspace; cell-read), and the Leino–Tiedemann negative 2603.29026 (parallel data barely
moves representation alignment; cell-read) which motivates the placebo arm. No direct prior art found
through 2026-09-01 under §7 coverage for parallel-supervised invariance of a discrete decodable reasoning
trace evaluated by cross-language monitor transfer.

**falsifiable_predictions.**
- P1 (screen, 60M bilingual from-scratch or smollm2-135m continued on en/de + synthetic, ToyTools): trace
  exact-match agreement across translated pairs ≥ 70% with L_inv vs ≤ 25% without and ≤ 30% with the
  random-pair placebo, at task accuracy within 1 pp; M_en transfer gap Δ ≤ 3 AUROC points vs ≥ 15 for
  explicit CoT read by M_en.
- P2 (confirmation, qwen3-0.6b-base → qwen3.5-4b, 8 languages incl. 3 non-Latin scripts): M_en's
  hint-use / constraint-violation catch rate on non-English traces ≥ 85% of its English catch rate;
  translate-then-monitor on explicit CoT ≤ 70% (MT of manipulative traces loses cues; 2605.27901's
  answer-switching and post-hoc rationalization persist).
- P3: the CODI-style no-parallel continuous arm shows partial emergent invariance (Δ 5–10 points) but is
  beaten on Δ by ≥ 5 points and is not decodable by the frozen reader (AUROC ≤ 0.65).
- P4: silhouette-by-language of trace embeddings falls from ≥ 0.40 to ≤ 0.10 under L_inv.

**kill_conditions.** Trace agreement cannot exceed 40% without > 3 pp task loss (interlingua
unlearnable); translate-then-monitor matches invariant-code transfer at equal cost (the cheap alternative
suffices — kills the architecture claim); placebo pairs ≈ real pairs (parallel signal unnecessary,
extending 2603.29026 to traces); the no-parallel continuous arm already reaches Δ ≤ 3 (emergent invariance
suffices; 2603.08177 wins); high agreement with Δ ≥ 10 (invariant but uninformative — collapse).

**cheapest_decisive_pilot.** Phase 0 (CPU): bilingual ToyTools renderer (en/de/zh + synthetic
language); pair-semantics doctor (identical execution logs for both members); monitor-split doctor;
metric doctor (a hand-built canonical code gives Δ = 0 and 100% agreement; random codes give AUROC 0.50).
Phase 1 (~14 GPU-h): 60M from-scratch bilingual policy (or smollm2-135m + 200M tokens of de/zh continued
pretraining, ~2 GPU-h) with C1's frozen 20M reader; arms × 2 seeds — no L_inv, L_inv, placebo L_inv,
language-ID adversary, SOLAR-style pivot alignment, CODI-style continuous, explicit CoT per language
(7 × 2 × ~0.8 GPU-h ≈ 11 GPU-h); monitors, transfer evaluation and translate-then-monitor via GT MT
(~1 GPU-h). Confirmation (separate contract): qwen3-0.6b-base full FT (~40 GPU-h); Tinker Qwen3.5-4B / 9B
LoRA RL with parallel prompts (≈ 300M tokens) on the 13-language fragility set (loss functions must be
logprob-only, so L_inv on Tinker is implemented through the sampled-trace EM reward, not JS).

**controls.** Explicit CoT + M_en; translate-then-monitor (production MT); SOLAR (2606.26466); CODI-style
continuous without parallel data (2603.08177); random-pair placebo; language-ID adversary; cross-lingual
self-consistency RL without parallel data (2606.01464); ReasonXL-trained target-language explicit CoT
(2604.12378) read by M_en; per-language monitors (ceiling); activation probes (2608.04928); iso-token,
iso-parameter, paired McNemar over pairs; FLORES contamination probe and four-field disclosure.

**kevin_advantage.** Strong but not exclusive. General Translation supplies (a) production-grade MT for
the translate-then-monitor baseline, (b) translated *tool-use* task suites with terminology control and
identical environments — the scarce object; ReasonXL covers only five European languages and math/general
traces — and (c) low-resource and non-Latin coverage; 8×H100 for 0.6B–4B; Tinker for 9B RL. Honest limit:
for en/de/fr/it/es explicit-CoT controls, ReasonXL is public and equivalent.

**collision_risk.** medium. Searches: arXiv `(interlingua|language-agnostic|language-invariant) AND
(CoT|latent reasoning|reasoning traces)` → 11 (2608.24958, Layer Swap 2605.26735, UL-XCoT 2604.20090,
2603.08177, AdaMCoT 2501.16154, rest unrelated); arXiv `cross-lingual AND (monitorability|monitor|
faithfulness) AND CoT` → 2 (UL-XCoT, ToxiFrench) — no monitor-transfer paper exists; arXiv `("parallel
data"|"parallel corpus"|translation) AND (latent reasoning|reasoning trace|CoT) AND (invariant|
consistency|aligned) AND multilingual` → 15 (ReasonXL, xCoT 2401.07037, question-translation training
2401.07817 / 2405.01345, Cross-lingual Collapse 2506.05850, Learn Globally Speak Locally 2507.05418 — all
explicit-CoT accuracy); the latent-reasoning cell's five arXiv listings and 18 WebSearch queries; `ft`
interlingua → 0. Drivers: 2603.08177's group (a parallel-supervised follow-up is obvious), SOLAR's
authors (Ritter lab), the ReasonXL consortium, and the 2605.27901 authors (who call for robust
cross-lingual monitors).

**monitorability_and_safety.** Positive: monitor portability across languages. Risks: invariance may
erase language-specific cues a monitor needs (an injection written in the input language) — per-language
injection detection is reported alongside Δ; an English gloss for humans risks English-centric review (the
code is symmetric; gloss fidelity is reported per language). Data rights: FLORES-plus CC-BY-SA-4.0;
ReasonXL license to be checked before use; GT corpora cleared for research only; never customer content;
no CC-BY-NC weights in publication runs.

**negative_result_value.** If traces cannot be made invariant without task loss, reasoning codes are
surface-bound — supports 2601.02996 and extends 2603.29026 to the trace level — and translate-then-monitor
becomes the recommended practice with a measured cost curve; if emergent invariance suffices, parallel
supervision is unnecessary (cheap, useful, and a check on 2603.08177); the bilingual oracle world and the
monitor-transfer instrument remain reusable for the G2/G13 translation-paired probes.

**targets_gaps.** G15, G14 (cross-lingual clause), G20.  **pilot_gpu_hours.** 14.

---

## 5. Candidate C3 — `metered-opaque-channel-recurrence` (architecture-causal)

**Claim.** In a recurrent-depth LM for multi-turn tool use, factor the inter-iteration state into a
frozen-reader-anchored register file plus an opaque residual passed through a channel of metered capacity
C bits per slot per iteration; this replaces the latent-vs-explicit dichotomy with a one-dimensional knob
and yields a designed monitorability-tax curve accuracy(C), catch-rate(C), with the prediction that most of
the recurrence gain on compositional tool calling survives at C ≤ 32 bits while opaque serial depth stays
at one core pass.

**claim_scope.** architecture-causal.

**Mechanism.** Prelude P, core f_ψ iterated R times (fixed R, no halting), coda Q (Huginn/GRT layout).
The only inter-iteration and inter-turn state lives in T scratch positions appended after each
observation; ordinary positions are recomputed from embeddings every iteration and carry no state (a
per-position statefulness doctor enforces this). Slot j at iteration r holds s_{r,j} = (g_{r,j}, u_{r,j}):
g_{r,j} ∈ V_reg^S is a tuple of S register tokens from a fixed 2k-word reader vocabulary, produced by S
readout heads with straight-through Gumbel-softmax; u_{r,j} ∈ {1, …, 2^C} is an opaque code produced by
vector quantization of the continuous readout against a codebook of 2^C entries (straight-through,
commitment loss β). The next iteration receives only embeddings,
h_{r+1} = f_ψ( E(x), E_reg(g_r), E_u(u_r) ),
and the continuous h_r is discarded (DiscoLoop passes both channels; here the continuous channel is
replaced by the metered code). Registers are anchored to the frozen weaker reader as in C1:
L = L_task + λ_R · Σ_r −log p_{R_φ}(m_t | g_{r,·}) + β · L_commit,
with m_t the environment-logged (next tool, argument slots, retained facts, hint-use) at turn t. By
construction the opaque serial *bandwidth* per iteration is ≤ T·C bits and GDM's opaque serial *depth* is
one core pass; C is the knob (C = 0: fully legible loop; continuous pass-through: Ouro/Huginn). Register
slack is bounded as in C1, ε_reg = T·S·log2|V_reg| − H(m) + H(m | g); the total hidden budget T·C + ε_reg is
measured with the collusion probe. Scratch slots persist across turns, so the monitor reads a running,
human-renderable working memory — evaluated for tool-argument fidelity and retained-fact recall.

**what_is_new.**
- vs DiscoLoop — https://arxiv.org/abs/2607.00341 (v1 2026-07-01; opened): a looping architecture whose
  recurrence carries a discrete embedding channel *and* a continuous channel, capacity unbounded and
  unmeasured, no monitor or tool use; the delta is replacing the continuous channel by a metered C-bit
  code, anchoring registers to a frozen weaker reader, and claiming a designed accuracy(C)/catch-rate(C)
  curve on multi-turn tool tasks.
- vs How Transparent is DiffusionGemma? — https://arxiv.org/abs/2606.20560 (v1 2026-06-18, v2 2026-08-17;
  opened): routing inter-step information through an interpretable token bottleneck reduces opaque serial
  depth 28.6× → 1.1× "with no decrease in downstream performance" in a diffusion model; the delta is the
  same move for recurrent-depth agents with a metered residual (bandwidth, not only depth), a frozen
  weaker reader instead of post-hoc interpretation, and multi-turn tool feedback.
- vs Quantifying the Necessity of CoT through Opaque Serial Depth — https://arxiv.org/abs/2603.09786
  (2026-03-10; opened): defines and upper-bounds opaque serial *depth* for existing architectures and
  proposes no constraint; the delta is an architecture that bounds opaque serial *bandwidth* by
  construction and measures its accuracy price.
- vs Looped Language Models Improve Compositional Tool Calling — https://arxiv.org/abs/2608.18171
  (2026-08-17; opened): establishes the capability (API-Bank/BFCL/NESTful gains with depth) without any
  reading of the loop state; the delta is the legibility and bandwidth of what the loop carries.
Also positioned against Thinking States 2602.08332 (language-supervised fixed-size state for reading, not
looped; cell-read), GRT 2608.15062 (strongest adaptive-depth baseline), the iso-depth law 2604.21106
(φ = 0.46; compute accounting), 2606.24898 (uncontrolled looped hidden-state norms) and 2608.18222
(settling regimes). Rejection note: the brief rejects "generic latent loop with halting" on efficiency
grounds; C3 has fixed R and claims monitorability bandwidth, not efficiency — the loop is the substrate.
No direct prior art found through 2026-09-01 under §7 coverage for a recurrent-depth agent whose
inter-iteration state is a frozen-reader-anchored register file plus a metered opaque code.

**falsifiable_predictions.**
- P1 (30–60M from scratch, multi-turn ToyTools with 3-hop compositions, matched parameters and FLOPs):
  the continuous looped model beats the iso-FLOP non-looped model by ≥ 10 pp on 3-hop tasks (small-scale
  replication of 2608.18171's direction); metered arms retain ≥ 80% of that gain at C = 32 and ≥ 50% at
  C = 0.
- P2: frozen-reader monitor AUROC on registers for (next tool, hint-use, retained facts) ≥ 0.85 at every C;
  an activation probe on the continuous model also reaches ≥ 0.85, but under an obfuscation fine-tune
  (adversarial term against a copy of the probe, task accuracy held within 1 pp) the probe falls to ≤ 0.60
  while the register monitor falls ≤ 0.10.
- P3: collusion-probe secret recovery ≤ T·C + ε_reg + 2 bits at each C (tight; monotone in C).
- P4: accuracy(C) is concave with its knee between 8 and 32 bits.

**kill_conditions.** Metered arms at C ≤ 32 lose ≥ 80% of the loop gain at 40M and again at the
qwen3-0.6b-base retrofit (legible recurrence infeasible); register monitor AUROC < 0.70; slack bound
violated (recovered bits ≫ T·C + ε_reg — registers leak beyond the reader's semantics); no arm trains
stably after two remediation rounds (2606.24898-style norm blow-up).

**cheapest_decisive_pilot.** Phase 0 (CPU): channel-capacity doctor (VQ with 2^C codes → exact mutual
information by counting on synthetic inputs; straight-through gradient checks; commitment-loss sanity);
leakage doctor (the recurrence receives only E_reg(g), E_u(u); per-position statefulness test);
multi-turn ToyTools oracle world with tool failures; opaque-serial-depth tool (2603.09786) run on each
architecture graph. Phase 1 (~15 GPU-h): 40M models (prelude 2 layers, core 4 layers × R = 4, coda 2
layers), T = 8 slots, S = 4 registers, |V_reg| = 2k; arms × 2 seeds — non-looped iso-param (deeper),
non-looped iso-FLOP, looped continuous, DiscoLoop-style mixed, metered C ∈ {0, 32, 128} (7 × 2 × ~1 GPU-h
= 14 GPU-h); monitors, probes, obfuscation fine-tunes (~1 GPU-h). Confirmation (separate contract):
retrofit into qwen3-0.6b-base through a 2608.11233-style adapter on BFCL/NESTful-style multi-turn tasks
(~60 GPU-h); Ouro-1.4B/2.6B and GRT comparisons. Tinker cannot host custom recurrence (LoRA-only), so all
runs are local.

**controls.** Non-looped iso-param and iso-FLOP; continuous looped (Huginn/Ouro-style); GRT
(2608.15062); DiscoLoop (2607.00341); explicit-CoT non-looped at matched tokens; Thinking-States-style
language-supervised state (2602.08332); activation-probe monitor (2608.04928); opaque-serial-depth
measurement (2603.09786) per arm; iso-depth-law accounting (2604.21106); paired McNemar; 2 seeds at the
screen → 3–5 at confirmation; two-forward-pass causality audit on the recurrence (2608.22876-style).

**kevin_advantage.** Modest: the harness's multi-turn loop, oracle and trace contracts and 8×H100 for the
0.6B retrofits and Ouro runs; no unique data asset; no Tinker leverage.

**collision_risk.** medium. Searches: arXiv `(looped|"recurrent depth"|"recurrent-depth") AND
(monitorability|opaque|interpretable) AND reasoning` → 25 results, none in scope (agent frameworks,
VLA, robotics); arXiv `"information bottleneck" AND (CoT|latent reasoning) AND (monitor|interpretable)` →
R-Capsule only; HF papers `latent reasoning monitorability` → 20, none looped; the latent-reasoning
cell's `"looped language model" OR "recurrent-depth"` listing, the Huginn probing negative 2507.02199,
GDM's opaque-serial-depth and DiffusionGemma papers. Drivers: GDM's transparency group (Brown-Cohen,
Lindner, Shah, Nanda) is one paper from applying the bottleneck to looped models; the Geiping group
(Huginn, Multi-Stream LLMs); Cambridge (2608.18171); the DiscoLoop authors (Berkeley/Princeton).

**monitorability_and_safety.** Positive: registers are a persistent readable working memory across
turns and the opaque budget is explicit. Risks: registers can become performative (mitigated by
environment-logged labels and the Baker-style check); a small C may push computation into within-iteration
depth (bounded by one core pass, measured with 2603.09786's tool) or into ordinary positions' attention
(measured by the statefulness doctor). No known IP exposure; data synthetic/public.

**negative_result_value.** If the loop's tool-use gain needs high-bandwidth continuous state (C ≥ 128),
that is a quantitative statement of *why* latent recurrence resists monitoring (bits per iteration),
sharpening 2606.12689's "hidden computation, not hidden explanation"; the C-knob and collusion probe
transfer to any latent medium (Coconut, Ouro); the multi-turn ToyTools world with register readouts is a
reusable state-tracking monitor benchmark.

**targets_gaps.** G14, G20; latent-reasoning cell item 6 (multi-turn looped agents, depth vs
monitorability) and the triage axis "monitorability of what a loop computes".  **pilot_gpu_hours.** 15.

---

## 6. Sequencing and how the three relate

C1 is the identifiability screen for everything else: if a frozen weaker reader cannot anchor a learned
code at 135M without a > 5 pp tax, C2 and C3 inherit the kill. C2 adds one loss term and one data asset to
C1 and is the only candidate where General Translation's parallel data is the defining input; it is the
moonshot because the payoff (a monitor that ports across 13 languages) is large and the failure modes are
several (emergent invariance suffices; translate-then-monitor suffices; collapse). C3 moves the same
anchoring into a recurrent architecture and adds the bandwidth knob; it should start only after C1 P1–P3
pass, and it is the one whose confirmation cannot use Tinker. All three share the ToyTools oracle world,
the rate ledger, the collusion probe and the held-out-monitor protocol, so the fixed cost is paid once.

Relation to sibling notes: F's `language-invariant-latent-length` constrains *compute count* per aligned
unit in the trunk (G19/G1); C2 constrains the *reasoning trace* and measures monitors — different object,
same data asset, coordinate on the pair renderer. G's provenance-attention-mass monitor is a non-CoT
channel on hybrids; C1/C3 are medium designs — complementary, and G's channel is a natural extra monitor
arm for C3's multi-turn tasks. C's meaning-level state note anticipates that meaning-level media may help
monitor transfer; C2 is the direct test.

---

## 7. Search log and coverage limits

Host helper calls (12 total, ≥ 4 s apart; raw output in `design/D-search/collision.log`): 8 arXiv API
queries, 1 HF papers, 1 OpenReview, 1 DDG (bot-blocked, empty), 1 arXiv multilingual query — listed under
each candidate. WebFetch abstract reads from this Mac (25): 2407.13692, 2509.20317, 2608.03838,
2606.26466, 2605.27901, 2601.02996, 2607.00341, 2603.09786, 2606.20560, 2603.30036, 2608.04928,
2603.20508, 2602.23248, 2404.18988, 2502.05242, 2602.14095, 2605.26537, 2506.01926, 2509.22131,
2603.08177, 2604.20090, 2604.12378, 2608.18171, 2607.18264, ACL 2026.acl-long.1570. `ft search` (5):
legibility, prover verifier, steganography, interlingua, weak monitor → 0 relevant.

Not searched or not opened: OpenReview notes returned without titles (10, unopened); Semantic Scholar
(429, no key); WebSearch (session budget exhausted); Google Scholar, ACL Anthology search, Chinese-language
sources, ICLR 2027 submissions; full texts of any 2026 paper (abstract-level only for everything opened
this session; body numbers quoted from cell notes come from WebFetch summaries); the arXiv API's
exact-phrase matching misses paraphrased titles; LatentGuard's and ALCA's decoder training regimes are
unspecified in their abstracts and were not resolved from full text; TELLME's method was not resolved.
Retractions: none found for any cited paper under this coverage (no retraction database searchable).
