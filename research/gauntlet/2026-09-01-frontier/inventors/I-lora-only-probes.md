# Design note — inventor I-lora-only-probes (2026-09-01)

Angle I: what can be learned ABOUT architecture through Tinker LoRA/RL access to Kimi-K2.6 / GLM-5.3 / Qwen3.5 hybrids
(shared-outer MoE LoRA and routing, ported adapters onto hybrids) and a two-tier hosted-vs-local protocol.
Targets: synthesis G3, G22, G19, G2, G13; tinker-rl G1/G4/G5.

Honesty conventions: [1P] first-party (vendor docs/code/blog), [PR] peer-reviewed venue stated on the primary page,
[arXiv] preprint, [GH] GitHub/HF artifact read directly, [derived] my own arithmetic. Every prior below carries a URL and
date; "opened" means I fetched the abstract/page myself in this session, otherwise I say so. No phrase "completely novel"
appears; gaps are stated as "no direct prior art found through 2026-09-01 under the coverage in §6".

---

## 0. New facts established in this session (these shape all three candidates)

F1. **Tinker's shared-outer MoE LoRA layout, read from exported tensors.** [GH, 2026-08-19 artifact]
`barbonara/corin-kimi-k26-pro-sft` (base `moonshotai/Kimi-K2.6`, r=8, `lora_alpha` 32, `target_modules: all-linear`,
1,092 tensors): `experts.w1.lora_A` [1, 8, 7168] and `experts.w3.lora_A` [1, 8, 7168] are shared across the 384 routed
experts; `experts.w1.lora_B` / `w3.lora_B` [384, 2048, 8] are per-expert; `experts.w2.lora_A` [384, 8, 2048] is per-expert
and `experts.w2.lora_B` [1, 7168, 8] shared. Shared expert and the dense layer-0 MLP get ordinary LoRA. Attention LoRA sits
on `q_a_proj`, `kv_a_proj_with_mqa`, `o_proj` only (not `q_b_proj`/`kv_b_proj`). **The router (`mlp.gate`) is not adapted.**
[derived] rank-8 param count from these shapes = 1,172,191,744 = cookbook (mlp 144,583,680 + attn 1,940,288) × 8 exactly;
the cookbook's unembed 171,008 × 8 is the missing remainder. The same layout appears on Qwen3.5-397B-A17B
(`allura-forge/Qwen3.5-397B-A17B-Secret-LoRA-Tinker`, r=64: `w1.lora_A` [1,64,4096], `w1.lora_B` [512,1024,64],
`w2.lora_A` [512,64,1024], `w2.lora_B` [1,4096,64]). Per-expert factors are therefore 3·d_e·r numbers per expert per layer
(Kimi-K2.6: 6,144 per expert-layer at r=1; 384 × 60 = 23,040 expert-layers).
URLs: https://huggingface.co/barbonara/corin-kimi-k26-pro-sft · https://huggingface.co/allura-forge/Qwen3.5-397B-A17B-Secret-LoRA-Tinker ·
https://github.com/thinking-machines-lab/tinker-cookbook/blob/main/tinker_cookbook/hyperparam_utils.py (docstring: "For MoE
expert layers, Tinker uses a shared-outer LoRA scheme: the LoRA factor connected to the model hidden dimension is shared
across experts, while the other factor remains expert-specific.") [1P]

F2. **What Tinker adapts inside a GDN hybrid — the decay pathway is excluded.** [GH]
Two Tinker-exported Qwen3.5-9B adapters (`lucabaroni/qwen3.5-9b-rlvr-reward-hacking`, r=32, 2026-08-27, tag `tinker`;
`fforz/kiana-qwen3.5-9b-lora-1`, r=16, 2026-08-05, tags `tinker`, `tinker-cookbook`) show `linear_attn.in_proj_q`,
`in_proj_k`, `in_proj_v`, `in_proj_z`, `out_proj` on the 24 GDN layers and `self_attn.q/k/v/o_proj` on the 8 full-attention
layers; `mlp.gate/up/down_proj` on all 32; `unembed_tokens` when `train_unembed`. **Absent: `in_proj_a`, `in_proj_b`,
`conv1d`, `A_log`, `dt_bias`, `norm`.** In transformers' `modeling_qwen3_5.py` the decay is
`g = -exp(A_log) * softplus(in_proj_a(x) + dt_bias)` and the write strength `beta = sigmoid(in_proj_b(x))`, so through
Tinker the recurrent state's forgetting and write-strength functions are frozen while its keys/values/output gate are
adaptable. Tinker's `train_attn` group covers BOTH the GDN projections and the softmax-attention projections; it cannot
separate them. Locally (open weights) both splits are available. This makes the hosted/local difference an identification
variable, not merely a scale check.
URLs: https://huggingface.co/lucabaroni/qwen3.5-9b-rlvr-reward-hacking · https://huggingface.co/fforz/kiana-qwen3.5-9b-lora-1 ·
https://github.com/huggingface/transformers/blob/main/src/transformers/models/qwen3_5/modeling_qwen3_5.py (lines 489–575 at fetch)

F3. **Kimi-K2.6 and Kimi-Linear-48B-A3B-Base share a byte-identical tokenizer.** [GH]
`tiktoken.model` sha256 `b6c497a7469b33ced9c38afb1ad6e47f03f5e5dc05f15930799210ec050c5103` (2,795,286 bytes) in both repos;
both `vocab_size` 163,840. Kimi-K2.6 text config: `kimi_k2`, 61 layers, 384 routed + 1 shared experts, top-8, hidden 7168,
`moe_intermediate_size` 2048, MLA (`q_lora_rank` 1536, `kv_lora_rank` 512). Kimi-Linear-48B-A3B-Base: `kimi_linear`, 27
layers, hidden 2304, 256 experts, `moe_intermediate_size` 1024, KDA:MLA 3:1. So a K2.6 → Kimi-Linear hop changes the operator
family (dense MLA → KDA hybrid) with the tokenizer held exactly fixed. Qwen3 → Qwen3.5 changes the vocabulary
(151,936 → 248,320). Qwen3.5-4B/9B-Base: 32 layers = 24 `linear_attention` + 8 `full_attention` (interval 4);
Qwen3.5-35B-A3B-Base: 40 layers = 30 + 10, 256 experts top-8, `moe_intermediate_size` 512, hidden 2048.
URLs: https://huggingface.co/api/models/moonshotai/Kimi-K2.6?blobs=true · https://huggingface.co/api/models/moonshotai/Kimi-Linear-48B-A3B-Base?blobs=true ·
https://huggingface.co/Qwen/Qwen3.5-35B-A3B-Base/raw/main/config.json

F4. **Occupancy correction for the sweep (axis T / G19).** SARA (https://arxiv.org/abs/2606.25821, 2026-06-24, opened) adds a
training-time symmetric-JS routing-alignment objective across languages on Qwen3-30B-A3B and Phi-3.5-MoE-instruct
(+0.8 / +1.2 Global-MMLU). The synthesis says "a training-time objective making parallel sentences route through the same
experts is untested" — that statement no longer holds in its general form; what remains open is the *observational*
question at 1T under a content-fixed language intervention (candidate 1), and SARA's use of parallel sentences specifically
is not confirmed from the abstract.

F5. **What LoRA-only access can and cannot tell us about architecture (refined from tinker-rl §3).**
Can: (i) which experts a 1T MoE trains on given data, via per-expert factor deltas (F1) — a routing readout that needs no
hidden states; (ii) behavioural recall/length curves before and after adaptation on six operator families under one API,
with coarse module-group causal toggles; (iii) weight-space geometry of task adapters across families (exported ΔW);
(iv) expert-balance telemetry as a routing-health co-signal. Cannot: anything on decay/gate/conv parameters of GDN
(F2), router weights, hidden states, full-vocabulary logits, optimizer choice, adapter import, or bit-exact timing.

---

## 1. Candidate 1 (cheap-decisive) — `lora-footprint-routing-probe`

**Claim.** Differencing a Tinker-exported shared-outer MoE LoRA against its step-0 export yields per-expert "footprints"
that are a calibrated, monotone readout of how often each expert of Kimi-K2.6 was routed the training tokens; with content
held fixed and only the language varied, the footprints measure cross-lingual routing consistency at 1T, and along an RL
run they measure routing drift without routing replay — all without hidden-state or router access.

**claim_scope:** architecture-causal (the intervention is on the input language with content fixed, and on RL-without-replay;
the probe itself is observational and is calibrated against ground truth on an open twin).

**Mechanism.** For MoE layer l, routed expert e, Tinker's LoRA is ΔW1_{l,e} = B1_{l,e} A1_l and ΔW3_{l,e} = B3_{l,e} A3_l
(shared A ∈ R^{r×d}, per-expert B ∈ R^{d_e×r}) and ΔW2_{l,e} = B2_l A2_{l,e} (shared B2 ∈ R^{d×r}, per-expert A2 ∈ R^{r×d_e});
the router g_l is frozen (F1). The per-expert gradient at step s is
dL/dB1_{l,e} = sum_t 1[e in TopK_l(x_t)] · g_{l,e}(x_t) · delta_{l,e,t} · (A1_l x_t)^T,
identically zero for tokens not routed to e. Under AdamW (weight decay 0, Tinker default), a parameter whose gradient is
non-zero in a fraction p of steps with magnitude G and directional consistency c moves per step by
≈ lr · (p G c) / sqrt(p G^2) = lr · c · sqrt(p), so the total displacement after S steps is ≈ lr · S · c_{l,e} · sqrt(p_{l,e}):
monotone in routing frequency, with the consistency term c to be absorbed by calibration.
Footprint: f_{l,e} = || [B1_{l,e}, B3_{l,e}, A2_{l,e}^T](S) − [same](0) ||_F, using a step-0 export (so init is removed even if
the per-expert factor is not zero-initialised). Calibration model: rank(f_{l,e}) ≈ rank(n_{l,e}), n_{l,e} = routed-token
count, fitted on the open twin Qwen3.5-35B-A3B-Base (on Tinker AND local; shared-outer LoRA re-implemented locally so
n_{l,e} is observable). Language intervention: parallel corpus C rendered in languages ℓ (content fixed), one rank-1 LoRA
per ℓ with the same Tinker `seed`; per-layer similarity rho_l(ℓ,ℓ') = Spearman over experts e not in the standing-committee
set K_l (top-m experts of a neutral-corpus footprint; 2601.03425), contrasted with cross-content same-language
rho_l(C, C'). RL drift: footprints f(k) at checkpoints k of a CISPO LoRA-RL run; D_l(k) = 1 − Spearman(f(k), f(k−1)),
read alongside Tinker's `e_min_violation`/`e_frac_with_tokens` telemetry.

**What is new (delta vs three closest priors, all opened).**
1. Multilingual Routing in Mixture-of-Experts — https://arxiv.org/abs/2510.04694 — v1 2025-10-06, v2 2026-02-17, ICLR 2026 [PR].
   They read routers directly on open ≤30B MoEs over parallel text (language-specific early/late layers, cross-lingual
   alignment in middle layers, steering +1–2%). Delta: a readout at 1T from training-gradient footprints in exported
   adapters, on a model whose routers and hidden states are unreachable; footprints measure what adaptation *trains*, not
   what inference *routes*, and the two are compared on the open twin.
2. SARA — https://arxiv.org/abs/2606.25821 — 2026-06-24 [arXiv]. Training-time JS routing alignment across languages
   (Qwen3-30B-A3B, Phi-3.5-MoE). Delta: no objective is added; SARA is the reason the "training objective" form of G19 is now
   occupied, and the observational 1T measurement is what remains.
3. ESFT (Let the Expert Stick to His Last) — https://arxiv.org/abs/2407.01906 — 2024-07-02 [arXiv]. Selects experts to
   fine-tune from routing statistics (task routing is concentrated). Delta: the inverse direction — infer the routing
   statistics from the fine-tune when routing statistics cannot be observed.
   Also adjacent: R3 (https://arxiv.org/abs/2510.11370, 2025-10-13, opened) routing mismatch destabilises MoE RL — no data
   for LoRA-RL on Tinker; The Illusion of Specialization (https://arxiv.org/abs/2601.03425, 2026-01-06, ACL 2026, opened)
   standing committee — motivates committee removal; Tinker cookbook docstring (first-party, fetched 2026-09-01).
   No source found that reads expert usage from adapter deltas (search log §6).

**Falsifiable predictions.**
P1 (calibration, local twin): on Qwen3.5-35B-A3B-Base with shared-outer rank-1 LoRA (300 steps, batch 64 × 4K tokens),
per-layer Spearman(f_{l,e}, n_{l,e}) ≥ 0.80 in ≥ 90% of MoE layers; the same job on Tinker gives hosted-vs-local footprint
Spearman ≥ 0.90 per layer (same seed, LR, batch).
P2 (language intervention, Kimi-K2.6, 6 languages × 2 seeds, rank 1, 0.5M tokens each): middle-third layers (l = 21–40 of
61) rho(EN, ℓ) ≥ 0.70 for de/fr/es/zh/ja after committee removal, first 8 and last 8 layers rho ≤ 0.40; cross-content
same-language rho in middle layers ≤ 0.45; seed ceiling rho ≥ 0.90.
P3: per-language middle-layer similarity to English predicts sampling-only per-language accuracy (Belebele-class, 12
languages) with Spearman ≥ 0.6 — the 1T analogue of 2510.04694's correlation.
P4 (RL drift): 100-step rank-32 CISPO on a verifiable task without routing replay keeps D_l < 0.10 in ≥ 90% of layers and
`e_min_violation` within 10% of its start; the alternative outcome (D_l > 0.30 in ≥ 20% of layers) is the R3 instability
observed for the first time at 1T through LoRA.

**Kill conditions.** Local calibration Spearman < 0.60 in most layers (AdamW normalisation erases usage information) → the
probe is dead; hosted-vs-local Spearman < 0.70 → not usable as a two-tier instrument; |rho_language − rho_content| < 0.10 in
middle layers with overlapping 2-seed intervals → no language-invariance finding at 1T (publish as a scale-dependent
negative against 2510.04694).

**Cheapest decisive pilot.** Phase 0 (CPU, no LM): (a) pull the public r=8 Kimi-K2.6 adapter (4.69 GB), verify the shape
algebra of F1, compute per-expert factor norms and their Gini per layer (uniform norms would mean init dominates and force
the step-0 differencing); (b) NumPy AdamW simulation on sparse-gradient toys to fix the sqrt(p) calibration curve and its
sensitivity to beta2 and consistency c. Phase 1 (local, 8×H100, ≈ 8 GPU-h): Qwen3.5-35B-A3B-Base (pin the 40-hex revision)
with a custom shared-outer LoRA module; 4 runs (EN/DE renderings of FLORES-200 dev+devtest plus an OPUS slice, 2 seeds)
logging n_{l,e}; one per-expert (non-shared) LoRA run for contrast (tinker-rl G1). Phase 2 (hosted): the same 4 runs on
Tinker Qwen3.5-35B-A3B-Base (~$10) for P1; Kimi-K2.6 rank-1: 6 languages × 2 seeds × 0.5M tokens ≈ 6M train tokens
(≈ $30 at $4.84/M) + step-0 exports; 4 English tasks × 2 seeds for the content contrast; offline analysis on the node.
Phase 3 (hosted, optional): 100-step rank-32 CISPO with exports every 25 steps (≈ $150–300). Total ≤ 20M Tinker train
tokens, ≤ $600; registry ids: qwen3.6-35b-a3b is registered, Qwen3.5-35B-A3B-Base must be added with its revision.
pilot_gpu_hours: 10.

**Controls.** Seed-noise ceiling; cross-content same-language contrast; standing-committee removal (2601.03425) from a
neutral-corpus footprint; ground-truth routing on the open twin; hosted-vs-local same-seed equivalence; rank robustness
{1, 4, 32} (G22 rank-sensitivity item); shared-outer vs per-expert LoRA locally; Tinker expert-balance telemetry as
co-signal; the 2510.04694 layer pattern as the reference; 2 seeds with paired clustered SEs; token/dollar ledger.

**Kevin advantage.** Tinker is the only route that trains and exports weights on Kimi-K2.6; parallel translation data
supplies the content-fixed language intervention (General Translation for development; FLORES-200 / OPUS for the published
artifact); 8×H100 holds the 35B-A3B open twin for ground-truth calibration; the harness seals seeds and receipts.

**Collision risk: medium.** Searches (§6): arXiv `LoRA AND "mixture of experts" AND routing AND (multilingual|cross-lingual|
translation)` → 1 unrelated; `LoRA AND MoE AND shared AND "expert-specific"` → 0; `"mixture of experts" AND ("expert
routing"|"routing patterns") AND (parallel|translation|cross-lingual)` → 2510.04694, 2604.03592 (RISE), nothing on adapter
readouts; HF papers LoRA-MoE → 20 mixture-of-LoRA papers, none reading usage from weights; DDG `"shared-outer"` → 0 (DDG
output may have been blocked); local grep of August cs.CL/LG/AI titles → 0. The trick is simple and Tinker has many users,
hence medium rather than low.

**Monitorability and safety.** No effect on CoT. Dual use: the probe extracts routing internals of a closed-serving model
from a permitted export — disclose to Thinking Machines before publication; "exported adapters leak routing" is itself a
provider-relevant finding. Data rights: FLORES-200 (CC-BY-SA 4.0) and OPUS for publication; General Translation production
text only with client consent and never in the released artifact. Tinker ToS permits adapter export.

**Negative-result value.** If AdamW erases usage → exported LoRAs do not leak routing (privacy-positive) and telemetry is
the only routing channel on Tinker; if hosted ≠ local → documents Tinker/open-tinker non-equivalence (G22 two-tier); if 1T
routing is language-specific in middle layers → a scale-dependent reversal of 2510.04694.

**Targets gaps:** G22, G19 (observational remnant after SARA), tinker-rl G1/G4/G5.

---

## 2. Candidate 2 (architecture-causal, medium) — `pathway-localized-lora-amnesia-ladder`

**Claim.** In 3:1 GDN/Mamba hybrids, the long-range-recall damage caused by low-rank reasoning post-training is carried by
the q/k LoRA factors on the minority softmax-attention layers rather than by the recurrent-pathway factors; dropping those
factors from the exported adapter restores recall while keeping the reasoning gain; dense-MLA (Kimi-K2.6) and learned
sparse-indexer (GLM-5.3) models show measurably different damage profiles — identifiable across six operator families at
9B–1T through Tinker's module-group toggles plus offline surgery on exported adapters, with translation-paired recall as
the instrument.

**claim_scope:** architecture-causal.

**Mechanism.** Post-training adds ΔW_g for factor groups g ∈ {attn-qk, attn-vo, gdn-qkvz-out, mlp, unembed}; Tinker
exposes only the coarse toggles {attn = attn-qk ∪ attn-vo ∪ gdn-qkvz-out, mlp, unembed} (F2), local weights expose all
five plus a decay arm {in_proj_a, in_proj_b} that Tinker never touches. Recall R(A, L, ℓ_A→ℓ_B) is generation-based NIAH-S2/
S3 and translation-paired recall (key stored in language ℓ_A, queried in ℓ_B; same-language control) at lengths
L ∈ {4K, 8K, 16K, 32K, 64K, 128K}. Long-range retrieval in hybrids is carried by the full-attention layers (2606.15378, cited
from the seq-operators cell, not opened here); a q/k LoRA changes the score bilinear form by
delta_s(x, y) = x^T (ΔW_q^T W_k + W_q^T ΔW_k) y + O(||Δ||^2), and CoT-SFT gradients bias it toward short-range patterns
(2606.11052). H1: R(base) − R(base + ΔW \ attn-qk) ≤ 0.3 · [R(base) − R(base + ΔW)], i.e. dropping attn-qk factors recovers
≥ 70% of the loss; H2: dropping gdn-qkvz-out recovers ≤ 20%. Group contributions are estimated by leave-one-group-out and
5-group Shapley values (32 evaluations per adapter) on exported adapters, run locally for ≤ 35B bases; for Kimi-K2.6 and
GLM-5.3 only the hosted toggles are available (group-level attribution). The decay arm tests whether re-tuning retention
(the only thing Tinker cannot reach) matters for recall: predicted null beyond 8K on NIAH (attention-carried), possible
effect on within-window MQAR.

**What is new (delta vs three closest priors, all opened).**
1. Attention Amnesia in Hybrid LLMs — https://arxiv.org/abs/2606.11052 — v1 2026-06-09, v2 2026-08-30, EMNLP 2026 main [PR].
   Full CoT-SFT on HypeNet-9B/5B and Jet-Nemotron: NIAH-S2@256K 67.2% → 9.4%; QK-Restore. Delta: LoRA instead of full SFT
   (its low-rank q/k perturbation may or may not break retrieval heads), six operator families at 9B–1T through one API
   including two that cannot be trained locally, causal adapter surgery (drop factors) instead of weight restoration,
   Shapley attribution across five factor groups, and a translation-paired probe.
2. Where Should LoRA Go? — https://arxiv.org/abs/2604.22127 — 2026-04-24 [arXiv]. Qwen3.5-0.8B and Falcon-H1-0.5B;
   attention-pathway LoRA best with 5–10× fewer parameters; recurrent adaptation −14.8 pp GSM8K on the sequential hybrid.
   Delta: 9B–35B and 1T, long-range recall rather than accuracy, decay-projection arm (which they do not isolate), the
   hosted/local identification of Tinker's group boundaries.
3. Sliding-window beats linear attention — https://arxiv.org/abs/2608.28444 — 2026-08-28 [arXiv]. Post-trained linear
   attention loses to SWA+sinks 2–10× on NIAH/BABILong. Delta: not a retrofit; we measure how adaptation of already-trained
   hybrids damages recall and where; SWA+sinks becomes the interpretive control for "recall lives in the attention path".
   Adjacent decay-side priors (opened): LongMamba https://arxiv.org/abs/2504.16053 (2025-04-22, ICLR 2025) and Mamba
   Modulation https://arxiv.org/abs/2509.19633 (2025-09-23, NeurIPS 2025) — training-free receptive-field / A-spectrum changes
   in pure Mamba; delta: LoRA on the decay projection inside production hybrids.

**Falsifiable predictions.**
P1: rank-32 CoT-SFT (2M tokens, `train_attn`+`train_mlp`) on Qwen3.5-9B-Base, Qwen3.8-27B and Qwen3.5-35B-A3B-Base lowers
NIAH-S2 at 32K by ≥ 15 pp (200 probes, generation exact match, paired McNemar p < 0.01) while Kimi-K2.6 (dense MLA) drops
≤ 5 pp at matched SFT-loss reduction.
P2: `train_attn=False` limits the hybrid drop to ≤ 5 pp (≥ 70% of the damage removed).
P3: offline surgery on the exported Qwen3.8-27B / Qwen3.5-35B-A3B adapters: dropping only `self_attn.q/k_proj` factors
recovers ≥ 70% of lost recall and keeps ≥ 80% of the GSM8K gain; dropping all GDN factors recovers ≤ 20%.
P4: translation-paired recall (key in de/zh, query in en) degrades ≥ 1.5× more, in pp, than same-language recall under the
same adapter.
P5 (conditional on the phase-0 export): if GLM-5.3's exported adapter covers the DSA indexer projections, recall at 128K
drops ≥ 10 pp after the same SFT; if not, ≤ 3 pp.

**Kill conditions.** No hybrid shows ≥ 5 pp recall loss at 32K under LoRA CoT-SFT (publish "LoRA does not exhibit Attention
Amnesia" as the negative and stop the architecture story); or attribution is diffuse (no factor group carries > 40% of the
damage) → the pathway-localisation claim dies.

**Cheapest decisive pilot.** Phase 0 (CPU / ≈ $30 hosted): export a 1-step adapter for each Tinker family (Qwen3.5-9B-Base,
Qwen3.8-27B, Qwen3.5-35B-A3B-Base, Nemotron-3.5-Lightning-Base, Kimi-K2.6, GLM-5.3, Inkling) and enumerate covered modules
— itself a G22 deliverable and the decider for P5; build translation-paired NIAH/MQAR generators (span-aligned FLORES-200
sentences as needles) and the two-forward-pass prefix-invariance audit (2608.22876) on CPU. Phase 1 (local, ≈ 8 GPU-h):
Qwen3.5-4B (registry `qwen3.5-4b`) and Qwen3.5-9B-Base, rank 32, eight factor-group arms including the decay arm, 3 seeds,
recall curves 4K–32K. Phase 2 (hosted, ≤ $800): 7 models × {attn on, attn off}, 2M SFT tokens each; recall via the sampling
client at 32K (Kimi), 64K (Qwen3.8-27B, Nemotron), 128K (GLM-5.3, ≈ $62 per condition of prefill); export all adapters.
Phase 3 (local, ≈ 4 GPU-h): Shapley surgery evaluations on the exported 27B / 35B-A3B adapters. pilot_gpu_hours: 12.

**Controls.** Unadapted base with 3 evaluation seeds (noise floor); iso-token, iso-data SFT across all models with Δloss
reported; ranks {8, 32}; MLP-only arm; drop-q/k surgery (LoRA analogue of QK-Restore) and its Procrustes variant; the
2604.22127 placement arms locally; the decay-projection arm locally; length-stratified curves (2608.10296); generation-based
exact match with permutation-controlled needles and all-3-of-3 reliability; the two-forward-pass causality audit on every
local hybrid (2608.22876); Kimi-K2.6 (dense MLA), GLM-5.3 (DSA), Inkling (SWA:global 5:1) as architecture controls;
QED (2608.13668), MARCH (2608.12435) and SWA+sinks (2608.28444) cited as the interference/recall baselines; token/dollar
ledger; model+adapter reported as the tested object.

**Kevin advantage.** Tinker exposes six operator families under one API, two of which (GLM-5.3 753B, Kimi-K2.6 1T) cannot
be trained locally; parallel data makes the translation-paired recall probe; 8×H100 runs the fine local split at 4B/9B and
the surgery evaluations at 27–35B; the harness already enforces generation-based exact-match evaluation.

**Collision risk: medium.** Searches: arXiv `(LoRA|fine-tuning) AND (GDN|linear attention|Mamba|state space) AND (decay|
forgetting|retention) AND "long context"` → 0; `(Mamba|SSM) AND (receptive field|length extrapolation) AND (decay|
discretization|training-free)` → LongMamba, Mamba Modulation, no LoRA/hybrid item; DDG on LoRA-hybrid recall degradation
→ empty (possibly blocked); local August title grep for Mamba/SSM/hybrid × LoRA/fine-tune → only DASC. The Attention
Amnesia authors are the obvious group to extend to LoRA.

**Monitorability and safety.** Standard CoT-SFT only; the measured property (long-instruction recall after post-training)
is a reliability/safety property for agents, so the result is safety-positive; adapter surgery is a defensive tool. Data:
open CoT-SFT corpora, synthetic NIAH, FLORES-200 needles.

**Negative-result value.** "LoRA is immune to Attention Amnesia" is a practical positive for hybrid post-training and a
mechanistic clue (rank-32 q/k perturbations cannot destroy retrieval heads); diffuse attribution would say recall in
hybrids is distributed rather than attention-carried, contradicting 2606.15378 at scale; the module-coverage table from
phase 0 is publishable infrastructure knowledge regardless.

**Targets gaps:** G22, G2 (translation-paired recall instrument at 9B–1T), G13 (GLM-5.3 indexer behavioural probe).

---

## 3. Candidate 3 (moonshot, portability-protocol) — `cross-operator-family-adapter-port`

**Claim.** A task adapter's identity can be factored out of its operator family: a shared task latent learned by
reconstruction over a Tinker-built multi-family adapter zoo (softmax-dense, MLA-MoE at 1T, GDN hybrid, Mamba-2 hybrid)
ports onto KDA / GDN / Mamba / diffusion targets through a thin attention-pathway alignment, recovering ≥ 60% of fresh-LoRA
lift — and a weight-space identifiability screen kills the port in advance if task geometry is family-specific.

**claim_scope:** portability-protocol.

**Mechanism.** Zoo: seen bases b ∈ B = {Qwen3-8B-Base (softmax dense), Kimi-K2.6 (MLA-MoE, 1T), Qwen3.5-9B-Base (GDN
hybrid), Qwen3.5-35B-A3B-Base (GDN-MoE hybrid), Nemotron-3.5-Lightning-Base (Mamba-2-MoE hybrid)}, tasks t ∈ T (|T| = 16;
8 multiple-choice with shuffled gold index, 8 generative incl. 4 translation directions and 2 tool-schema tasks), LoRA(b,t)
at rank r = 8 with Tinker `seed` fixed per base so ΔW(0) = 0 and inits coincide across tasks; export; ΔW_{b,t,l,s} = B A at
common site types s (q, k/kv, v, o; for MLA: q_a, kv_a, o). Task geometry per base:
S_b[t,t'] = mean_{l,s} <ΔW_{b,t,l,s}, ΔW_{b,t',l,s}>_F / (||ΔW_{b,t,l,s}|| ||ΔW_{b,t',l,s}||).
Identifiability screen: Mantel correlation M(b,b') = corr(vec S_b, vec S_b') against a 10^4-permutation null over task
labels. Port: hypernetwork H_theta(z_t, e_{b,l}, s) → (Â_c ∈ R^{r×w}, B̂_c ∈ R^{w×r}) at canonical width w = 1024; per-base,
per-site alignment P^in_b ∈ R^{w×d_b}, P^out_b ∈ R^{d_b×w}; ΔŴ = P^out_b B̂_c Â_c P^in_b. Training:
L = sum_{b,t,l,s} ||ΔŴ − ΔW||_F^2 / ||ΔW||_F^2 + lambda · sum_{b local} KL(p_{b+ΔW} || p_{b+ΔŴ}) on calibration text
(reconstruction is required because the 1T seen base offers no gradient path and no adapter import). New target b*: freeze
z_t and theta; fit P_{b*} on attention-pathway sites only (Kimi-Linear's 1-in-4 MLA layers; Qwen3.5-0.8B's 1-in-4
full-attention layers; Falcon-H1's attention branch; LLaDA's attention) either (i) by labelled refit with k ∈ {64, 256, 1000}
examples per task (PorTAL protocol) or (ii) label-free: P^in_{b*} = argmin_P ||X_{b*} P − X_{b_src} P^in_{b_src}||_F over the
residual-stream activations X of a local seen base and the target on the same parallel sentences (content-anchored,
language-diverse, label-free; signed-permutation gauge per 2606.31963). Lift recovery
LR = (acc(b* + ΔŴ) − acc(b*)) / (acc(b* + fresh LoRA) − acc(b*)).

**What is new (delta vs three closest priors, all opened).**
1. PorTAL: Portable Task Adaptation for LoRA — https://labs.ramp.com/research/portal-portable-task-adaptation/ — 2026-07-01
   [1P blog]. Task latent 256-d, canonical core, per-base alignment; ~98% lift on unseen Qwen3-8B, ~94% on Gemma-3-4B,
   Cross-LoRA ~14%; trained by gradients through the seen bases; labelled refit; softmax-attention targets only (blog states
   no state-space/linear-attention base; Inkling's config confirms local/global softmax). Delta: seen bases include a 1T
   model reachable only through Tinker (reconstruction training over exported adapters instead of gradients through the
   base), targets cross operator families (KDA/GDN/Mamba-2/diffusion), alignment restricted to attention-pathway sites, a
   label-free parallel-sentence alignment arm, tokenizer crossing as a controlled variable (K2.6 → Kimi-Linear identical
   tokenizer; Qwen3 → Qwen3.5 vocab 151,936 → 248,320), generative tasks, and shuffled choices (portallib issue #28).
2. UpgradeBench — https://arxiv.org/abs/2608.20918 — 2026-08-21 [arXiv]. Direct-copy retention law on Qwen/OLMo
   transformer lineages; "shape-incompatible hops admit no weight-space method"; learned mappings deferred; no
   non-transformer targets. Delta: fills exactly the deferred cells — learned mappings, non-transformer and cross-tokenizer
   targets — with a pre-registered identifiability screen and the same decision framing.
3. Theseus — https://arxiv.org/abs/2602.12952 — v1 2026-02-13, v3 2026-07-30, ICML 2026 [PR]. Training-free Procrustes
   transport of one task update across widths within a family. Delta: cross-operator-family targets, a learned shared
   latent over many tasks and bases rather than one static vector; Procrustes survives only as the label-free alignment
   arm, and Theseus is a control on the within-family hop.
   Constraints and comparators (cited, from the adapter-portability cell unless marked opened): Where Should LoRA Go
   (2604.22127, opened) for the site choice; Attention Amnesia (2606.11052, opened) for the recall regression check;
   Cross-LoRA https://arxiv.org/abs/2508.05232 (2025-08-07, not opened here); Engram reader transfer
   https://arxiv.org/abs/2608.17050 (2026-08-17, not opened here); Attention to Mamba https://arxiv.org/abs/2604.14191
   (2026-04-01, surfaced by my search, not opened) converts bases, never fine-tunes; Override Gap / Model of Models /
   hypernetwork scaling laws as ceilings.

**Falsifiable predictions.**
P1 (screen): M(Qwen3-8B, Qwen3.5-9B-Base) ≥ 0.60 and M(Kimi-K2.6, Kimi-Linear-48B-A3B-Base [local LoRAs]) ≥ 0.50 with the
permutation-null 95th percentile ≤ 0.25; within-family M(Qwen3.5-9B, Qwen3.5-35B-A3B) ≥ 0.75.
P2 (tiny port, local): sources {qwen3-0.6b-base, smollm2-135m} → Qwen3.5-0.8B-Base (GDN hybrid, different tokenizer):
LR ≥ 0.60 at k = 256 labelled examples/task vs Cross-LoRA ≤ 0.20 and vs a fresh LoRA trained on the same k = 256 budget
≤ 0.45; → mamba-130m-hf LR ≥ 0.40.
P3 (label-free arm): parallel-sentence Procrustes alignment reaches ≥ 70% of the labelled-refit LR at zero labels.
P4 (tokenizer-controlled hop): Kimi-K2.6 → Kimi-Linear-48B-A3B-Base LR ≥ 0.50 and exceeds the Qwen3-8B → Qwen3.5-9B LR by
≥ 0.10, isolating the tokenizer cost.

**Kill conditions.** Screen: M < 0.30 for every cross-family pair while within-family ≥ 0.70 → task geometry is
operator-family-specific; stop before any hypernetwork training. Port: tiny-port LR < 0.30 while the within-family PorTAL
replication reaches ≥ 0.90 → cross-family porting dead in weight space. Label-free arm < 30% of the labelled LR → G4 arm
dead.

**Cheapest decisive pilot.** Phase 0 (CPU): PorTAL within-family recipe re-run with shuffled choices (issue #28 hygiene);
Mantel-screen algebra on synthetic ΔW; hosted zoo at rank 8 with fixed seeds: 16 tasks × ≈ 0.3M tokens on Qwen3-8B,
Qwen3.5-9B-Base, Qwen3.5-35B-A3B-Base, Nemotron-3.5-Lightning-Base, Kimi-K2.6 (Kimi ≈ 4.8M tokens ≈ $25; others ≈ $10
total); CPU Mantel analysis on exported ΔW (Kimi: 61 layers × 3 sites; 7168 × 1536 matrices). Phase 1 (local, ≈ 14 GPU-h):
tiny zoo (qwen3-0.6b-base, smollm2-135m: 16 tasks × 3 seeds), fresh-LoRA ceilings on Qwen3.5-0.8B-Base (rev
dc7cdfe2ee4154fa7e30f5b51ca41bfa40174e68), mamba-130m-hf, Falcon-H1-0.5B-Base; hypernetwork reconstruction training;
labelled and label-free refits; held-out-format evaluation. Phase 2 (after a positive screen, outside the pilot):
kimi-linear-48b-a3b-base and llada-8b-base targets. pilot_gpu_hours: 14.

**Controls.** Fresh LoRA ceiling at iso-rank/iso-data; untuned floor; fresh LoRA at the calibration budget k; direct copy
where shapes allow (UpgradeBench protocol); Cross-LoRA; Theseus on the same-width hop; PorTAL within-family positive
control (Qwen3-1.7B/4B → Qwen3-8B, shuffled choices); Engram-style frozen object + thin reader comparator (2608.17050);
held-out prompt formats (2608.09490); attention-pathway vs full placement on hybrids (2604.22127) with a NIAH regression
check (2606.11052); permuted-task null for the Mantel screen; seed-matched inits per base; WikiSkill text-space transfer
comparator (2608.27454); 3 seeds with paired clustered SEs; token/dollar ledger.

**Kevin advantage.** Registered local targets across operator families with pinned revisions (kimi-linear-48b-a3b-base
[KDA], mamba-130m-hf, llada-8b-base, blt-1b, qwen3.5-4b/9b); Tinker as the adapter-zoo factory at 9B–1T under one fixed
seed/rank protocol, including the tokenizer-identical Kimi-K2.6 → Kimi-Linear hop; parallel sentences as the label-free
alignment stimulus; 8×H100 and the Slurm harness for the task × base grid.

**Collision risk: medium.** Searches: arXiv `(LoRA|adapter|fine-tuned) AND transformer AND (Mamba|linear attention|hybrid)
AND (port|cross-architecture|across architectures)` → only base conversion (2604.14191, 2502.15130, 2506.17671, Mamba4Net);
OpenReview `cross-architecture adapter transfer Mamba transformer LoRA` → titles unreadable in the API response (no
usable result); pre-pulled portable_adapters feed → only Engram reader transfer; the adapter-portability cell's 30 arXiv
queries found no cross-operator-family adapter port. Ramp's stated roadmap is description encoders; merging groups
(HeteroFusion, Transport-and-Merge) have live code for cross-family alignment, hence medium.

**Monitorability and safety.** Ported adapters can carry behaviours, including backdoors, silently across families —
include a poisoned-source-task transfer measurement as a safety deliverable and report it; no CoT impact. Data rights:
portallib-tasks licence to be checked and choices shuffled; FLORES-200 CC-BY-SA; Kimi-Linear MIT; Kimi-K2.6 modified-MIT;
Tinker export permitted.

**Negative-result value.** A failed Mantel screen bounds every PorTAL successor — task geometry is not family-invariant, so
cross-family porting must go through function (distillation), closing G3 as a weight-space gap and extending
UpgradeBench's "no weight-space method" from shape mismatch to operator mismatch; a failed label-free arm bounds G4; the
multi-family sealed task × base benchmark remains a deliverable either way.

**Targets gaps:** G3, G4, G22.

---

## 4. Why these three and not the obvious alternatives

- "Probe/steer KDA state through adapters" on Kimi-K2.6 is impossible: K2.6 is `kimi_k2` (dense MLA + MoE), not a KDA
  hybrid; the KDA hybrids (Kimi-Linear, K3, GLM-5.3-Flash) are not on Tinker; and Tinker never adapts the GDN decay path
  (F2). The angle's example is therefore re-cast as candidate 2's decay arm (local) and coverage table (hosted).
- "Teaching new operators via adapters" collapses into distillation through top-K logprobs (Tinker SDFT/on-policy
  recipes, ALM/BPM/ACTD cross-tokenizer distillation) — occupied; not proposed.
- Porting FROM Kimi-K2.6 by activation alignment is impossible (no hidden states); candidate 3 therefore uses exported
  adapters (weight space) and moves alignment to the local target side.
- The two-tier protocol (tinker-rl G4) is not proposed as a standalone deliverable (infrastructure); it is the
  identification device inside candidates 1 and 2 (hosted-vs-local same-seed equivalence; hosted coarse toggles vs local
  fine split).

## 5. Coverage limits (honest)

- WebSearch budget was exhausted before this cell; I used WebFetch on arxiv.org/abs pages (12 opened: 2510.04694,
  2407.01906, 2604.22127, 2606.11052, 2608.28444, 2608.20918, 2602.12952, 2510.11370, 2406.14528, 2504.16053, 2509.19633,
  2601.03425, 2606.25821) and the Ramp blog; the H100-proxied arXiv API (6 queries), DuckDuckGo (3 queries; empty output,
  possibly blocked), HF papers (1), OpenReview (1, unusable), plus free local greps of the August cs.CL/LG/AI title listing
  and the pre-pulled feeds. Semantic Scholar and Jina remain blocked from this Mac; no citation-graph check.
- Full texts were not read for any paper; numbers come from abstracts as returned by the WebFetch summariser and may carry
  transcription error. 2606.15378, 2508.05232, 2608.17050, 2604.14191 are cited from cell notes or search titles without
  opening.
- Tinker facts are from exported artifacts and cookbook source, not from a live API key: the step-0 export, the exact
  init of per-expert factors, `seed` semantics across runs, and whether GLM-5.3's DSA indexer projections are adapted are
  unverified and are phase-0 doctors in candidates 1–2.
- Adapter tensor names may reflect the exporter's naming rather than Tinker's internal implementation (e.g. `in_proj_qkv`
  is fused in transformers but exported as separate q/k/v); the *set* of adapted modules is what matters here.
- No code was run on the H100 node; GPU-hour estimates are arithmetic from model sizes and prior runs.

## 6. Exact searches run this session

Host-proxied (hostsearch.sh, 12 calls, ≥ 5 s apart):
1. arxiv `abs:LoRA AND abs:"mixture of experts" AND abs:routing AND (abs:multilingual OR abs:"cross-lingual" OR abs:translation)` → 1 (2511.23321, unrelated)
2. arxiv `abs:LoRA AND (abs:"mixture-of-experts" OR abs:"mixture of experts") AND abs:shared AND abs:"expert-specific"` → 0
3. arxiv `(abs:LoRA OR abs:"fine-tuning") AND (abs:"Gated DeltaNet" OR abs:"linear attention" OR abs:Mamba OR abs:"state space") AND (abs:decay OR abs:forgetting OR abs:retention) AND abs:"long context"` → 0
4. arxiv `(abs:Mamba OR abs:"state space model") AND (abs:"receptive field" OR abs:"length extrapolation" OR abs:"length generalization") AND (abs:decay OR abs:discretization OR abs:"training-free")` → 10 (LongMamba 2504.16053, Mamba Modulation 2509.19633, 2510.17196; rest unrelated)
5. arxiv `(abs:LoRA OR abs:adapter OR abs:"fine-tuned") AND abs:transformer AND (abs:Mamba OR abs:"linear attention" OR abs:"hybrid") AND (abs:port OR abs:"cross-architecture" OR abs:"across architectures")` → 12 (only base conversion: 2604.14191, 2502.15130, 2506.17671, 2510.17147)
6. ddg `"shared-outer" LoRA mixture of experts adapter` → 0 (possibly blocked)
7. ddg `LoRA adapter weights reveal which experts were used ...` → 0 (possibly blocked)
8. hfpapers `expert specialized fine-tuning mixture of experts routing LoRA` → 20 (ESFT 2407.01906, 2601.03425, mixture-of-LoRA papers)
9. openreview `cross-architecture adapter transfer Mamba transformer LoRA` → 10 notes, titles unreadable
10. arxiv `abs:"in-context" AND (abs:Mamba OR abs:"state space" OR abs:"linear attention" OR abs:hybrid) AND (abs:recency OR abs:"order sensitivity" OR abs:forgetting OR abs:"effective context") AND abs:"language model"` → 17 (2607.02303, 2605.22791, 2503.02130; none on adaptation)
11. arxiv `abs:"mixture of experts" AND (abs:"expert routing" OR abs:"routing patterns") AND (abs:"parallel" OR abs:translation OR abs:"cross-lingual") AND abs:"language"` → 14 (2510.04694, 2604.03592)
12. ddg `LoRA fine-tuning hybrid Mamba Gated DeltaNet long-context recall degradation attention layers decay projection` → 0 (possibly blocked)
Local, free: grep of sweep/listing_titles.tsv (August cs.CL/LG/AI) for LoRA×{expert,routing,mixture} and {Mamba,SSM,linear
attention,DeltaNet,hybrid}×{LoRA,fine-tune,decay,length}; grep of arxiv/{hypernetwork_lora,portable_adapters,hybrid_archs,
attention_operators,multilingual_compute}.xml → SARA 2606.25821 surfaced from multilingual_compute.xml.
HF API: adapters filtered by base_model for Qwen3.5-4B/9B/9B-Base, Qwen3.8-27B, Nemotron-3.5-Lightning, Qwen3.5-35B-A3B-Base,
GLM-5.3 (0 adapters), Kimi-K2.6 (8 Tinker-tagged adapters), gpt-oss-120b; `search=tinker`; safetensors headers via HTTP range
reads for 4 adapters; config.json for Kimi-K2.6, Kimi-Linear-48B-A3B-Base, Qwen3.5-4B/9B-Base/35B-A3B-Base, Qwen3-8B-Base;
tokenizer blob hashes for the two Kimi repos. GitHub: tinker-cookbook hyperparam_utils.py; transformers modeling_qwen3_5.py.
