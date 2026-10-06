# Adapter-portability sweep (cell: adapter-portability) — 2026-09-01

**Question.** What is the next factorization after PorTAL that nobody has published?
Specifically: porting adapters across architecture *families* (transformer → linear/hybrid,
diffusion, byte-level), across *tokenizers*, or porting update *rules* rather than weights.

**Prior cutoff.** research/frontier-systems-program-2026-08-10.md. Everything dated after
2026-08-10 is flagged **[post-cutoff]**. "Train once, port a LoRA" was *deprioritized* there
(collisions: PorTAL, Trans-LoRA, Cross-LoRA, CAST, LoRAGen); Direction 8 (Geometry-Compiled
Base Alignment) and Direction 16 (Portable Sidecar Update Dynamics) were the surviving adjacent ideas.
This note re-tests both against post-cutoff evidence.

**Honesty conventions.** First-party = blog/README/model card/preprint by the authors, not independently
replicated. Peer-reviewed = accepted venue stated on the primary page. Every number below was read from
the primary URL listed (abs page, HTML full text, model card, issue, tweet via fxtwitter API), not from memory.
Novelty statements are bounded: "No direct prior art found through 2026-09-01 under the coverage in §6."

---

## 1. Bounded summary

1. **PorTAL is frozen but scrutinized.** `ramp-public/portallib`: 0 commits since 2026-07-27, last release
   v0.2.1 (2026-07-25), 116 stars, 7 forks, 4 open issues; **no arXiv paper exists as of 2026-09-01**
   (arXiv API `ti:PorTAL OR abs:"portable task adaptation"` returns no such paper). The single post-cutoff
   event is **issue #28 (filed 2026-09-01)**: TruthfulQA and SciQ in `RampPublic/portallib-tasks` have the gold
   answer at choice index 0 on 100% of rows; PorTAL's length-normalized log-prob metric is position-independent
   so published numbers are "most likely unaffected", but any method with a per-choice-index degree of freedom gets
   truthfulqa 0.338→0.990 and sciq 0.858→0.997 from the artifact alone (Qwen3-8B-Base).
2. **"Cross-family" is already occupied *within softmax-attention transformers*, including MoE, local/global
   hybrid attention, and multimodal wrappers.** Ramp's own refits (one seed each): Inkling (66-layer MoE,
   hybrid local/global attention, multimodal) retains 104.4% of rank-16 LoRA lift; Gemma-4-E2B (alternating
   sliding/full attention, KV reuse) 120.6%; Mistral-7B +0.1787 macro acc_norm. An independent
   re-implementation (`robbym-dev/portal-vlm`, 2026-08-02) ports a GUI-grounding hypernet from Qwen2.5-VL-3B to
   Gemma-3-4B-it: 29.6% vs 15.8% fresh LoRA at 1k examples vs 1.6% untuned (single A40, ~30 GPU-h, one seed).
3. **Not found (under §6 coverage):** any port of a *task adapter* onto a linear-attention/SSM hybrid
   (KDA/GDN/Mamba), a diffusion LM, or a byte-level model; any label-free / task-blind base alignment;
   any explicit tokenizer-invariant adapter representation; any transfer of an *update rule* in the LLM setting.
   Base-weight conversion across families exists (Attention-to-Mamba distillation, HyLo upcycling,
   REPR-ALIGN AR→DLM) but none of it carries adapters or fine-tunes.
4. **The adjacent literature moved fast and mostly toward *training-free transport* and *negative results*:**
   Theseus (ICML 2026) transports task vectors across widths with Procrustes on activations; Transport-and-Merge
   merges Qwen2.5-7B into LLaMA-3-1B via optimal transport on 2,000 inputs; Cross-Architecture Steering Transfer
   (posted 2026-08) bridges SAE features across 5 transformers; UpgradeBench (2026-08-21) shows direct adapter
   copying retains R=0.88–0.99 across a 46B-token continuation but 0 at 2.9T tokens and *explicitly defers*
   learned mappings/hypernetworks as unmeasured "extension points".
5. **Kill-shot candidates for the hypernetwork route:** Override Gap (Doc-to-LoRA collapses to 46.4% on deep
   knowledge conflicts); Model of Models (emitted adapters recover only 14.0±0.9% / 11.2±0.5% of the in-context gain
   on sequence modeling, plateauing at 21% under a rank sweep); hypernetwork scaling laws (the hypernetwork can
   approach the target model's size, 2.5B vs 1.5B). These bound what a PorTAL-successor can promise.

---

## 2. Findings (every one opened at the primary URL)

Format: **Title** — URL — date — source type / status — claim — occupies — relevance.

### 2.1 PorTAL primary artifacts and post-cutoff events

**F1. portallib issue #28: TruthfulQA and SciQ gold answer is always at choice index 0** —
https://github.com/ramp-public/portallib/issues/28 — 2026-09-01 **[post-cutoff]** — GitHub, first-party external
reproducer (MatteoCarrabba), unanswered at fetch time.
Claim: at pinned dataset revision `d35f1e8a…`, truthfulqa (204 val / 613 train rows) and sciq (1,000 / 11,679) have
`gold_idx == 0` on 100% of rows; cause is `scripts/prepare_dataset.py` never shuffling choices. A labels-only per-index
prior with no adapter scores truthfulqa 0.338→0.990 and sciq 0.858→0.997 on Qwen3-8B-Base. Author states PorTAL's
acc_norm metric is position-independent, so published results are "most likely unaffected".
Occupies: evaluation hygiene of the only public PorTAL benchmark.
Relevance: any PorTAL reproduction or extension in this program must shuffle choices or drop these two tasks; also a
second independent reproduction effort exists (this reporter says "found while reproducing PorTAL in an external harness").

**F2. portallib repository state** — https://github.com/ramp-public/portallib — pushed 2026-07-27; releases v0.1.0
(2026-07-15) … v0.2.1 (2026-07-25) — GitHub, first-party.
Claim: 0 commits after 2026-07-27; 116 stars; 7 forks (latest fork 2026-08-28, none pushed after 2026-08-04); open
items: #28 (above), #27 (HellaSwag evaluated only on ActivityNet prefix), PR #25 (reject empty-token choices), PR #20
(inspect command). README (line 201–211): "PorTAL supports Qwen3 and cross-family refitting to Mistral, Gemma 3, Gemma 4,
and Inkling… It does not infer architecture mappings." REPRODUCING.md pins 8 base revisions and 5 artifact SHA-256s;
target modules q/v only, rank 8/alpha 16, task latent 256, layer embedding 32, hidden 512, canonical width 1024; source
training 12 epochs × 500 balanced rounds on Qwen3-1.7B + Qwen3-4B, up to 2,000 examples/task; "Each base uses its own
tokenizer."
Occupies: the released factorization (shared task latent + canonical core + per-base alignment) and its supported topology
(explicit q/v projection paths).
Relevance: no arXiv paper as of 2026-09-01 (arXiv API check), so all quantitative claims remain first-party.

**F3. Ramp Labs blog "PorTAL: Portable Task Adaptation for LoRA"** —
https://labs.ramp.com/research/portal-portable-task-adaptation/ — 2026-07-01 (author Ben Geist) — lab blog, first-party,
3-seed mean ± sd internally.
Claim: task latent dz=256; per-base FiLM decoder; alignment = learned per-layer embeddings + linear maps P_in/P_out; unseen
Qwen3-8B recovers ~98% of per-task LoRA lift (0.792 ± 0.004), cross-family Gemma-3-4B ~94%; ~2× less calibration data to
reach the strongest from-scratch LoRA's ~0.77 max; Cross-LoRA baseline recovers ~14% on Qwen3-8B; underfit cluster
OpenBookQA ~42%, WinoGrande ~57%, HellaSwag ~61% of LoRA lift ("rank-8 decoder's gradient competition"). All portability
experiments use gold-labeled calibration (8–2,000 examples/task). No label-free refitting. Tokenizer handling for Gemma is
not discussed. Stated future work: replace the free per-task latent with an encoder over a task description (zero-shot new
tasks); larger models; generation tasks.
Occupies: calibration-refit portability across softmax-attention transformer families.
Relevance: the reference factorization; its own future-work list points at *task-description encoders*, not at new
architecture families, tokenizers, or update rules.

**F4. RampLabs X posts (via fxtwitter API)** — https://x.com/RampLabs/status/2081819550329327689 (2026-07-27) and
https://x.com/RampLabs/status/2072383322940957115 (2026-07-01) — x-bookmark, first-party.
Claim (Jul 27): "It now spans from hybrid attention models to multimodal systems including Gemma 4 E2B, Mistral 7B &
@thinkymachines' Inkling." Claim (Jul 1): "This matches per task LoRA accuracy in both settings, using half the data and
half the cost."
Occupies: Ramp's own framing of "hybrid attention" = local/global (sliding/full) softmax attention, not linear attention.
Relevance: the word "hybrid" in Ramp's marketing does **not** cover KDA/GDN/Mamba-style operators — verified against
Inkling's config (F5).

**F5. HF model cards: portal-inkling, portal-mistral-7b, portal-gemma-4-e2b** —
https://huggingface.co/RampPublic/portal-inkling, https://huggingface.co/RampPublic/portal-mistral-7b,
https://huggingface.co/RampPublic/portal-gemma-4-e2b — 2026-07-23/25 — huggingface, first-party, **one seed each**.
Claim: Inkling refit (latent+core frozen from Qwen3-1.7B/4B; 132 exact q/v targets with heterogeneous dims; 5 epochs,
alignment LR 2e-5, norm-equalized task gradients, choice-loss weight 3): frozen 0.6767 → PorTAL 0.8692 (+0.1925); rank-16
full-target LoRA baselines averaged 0.8610 → "retained 104.4% of their aggregate lift". Gemma-4-E2B: 0.5729 → 0.7363
(+0.1634) vs LoRA 0.7084 → 120.6%. Mistral-7B-v0.3: 0.6127 → 0.7914 (+0.1787), no LoRA baseline on the card. Inkling per
its config.json (https://huggingface.co/thinkingmachines/Inkling/raw/main/config.json): 66 layers, hidden 6144, MoE 6-of-256
routed + 2 shared experts, `local_layer_ids` sliding-window (512) layers interleaved with global layers, `use_sconv`,
multimodal (vision hMLP encoder, dMel audio), 8 MTP layers — a **softmax-attention transformer** throughout.
Occupies: PorTAL refits onto MoE, local/global attention, multimodal-wrapper, and different-tokenizer (Gemma, Mistral,
Inkling vocab 201,024) bases — all still softmax attention.
Relevance: the "different tokenizer" cell is *already exercised* by Ramp (Qwen→Gemma/Mistral/Inkling) but never analyzed
as a variable; >100% lift retention on one seed with epoch selection on the same validation split is not iso-capacity
evidence.

**F6. portal-vlm: independent PorTAL re-implementation on VLMs** — https://github.com/robbym-dev/portal-vlm (adapters at
https://huggingface.co/manihani4/portal-vlm-gemma3-lora-1k etc.) — 2026-08-02 — GitHub, first-party (independent of Ramp;
"written before the official code released"), 0 stars, one seed, single A40, ~30 GPU-h.
Claim: source Qwen2.5-VL-3B-Instruct on GUI grounding (ScreenSpot-v2, n=1,272): untuned 51.5%, LoRA LM-only 77.1%,
LoRA LM+vision 82.6%, PorTAL-hypernet r8 LM-only 82.8%. Converter-only ports: Qwen3-VL-4B 91.4% (fresh LoRA 92.5%,
untuned 92.6%, saturated); Gemma-3-4B-it 29.6% vs fresh LoRA (1k) 15.8% vs untuned 1.6% ("19× the untuned floor and
roughly 2× a fresh LoRA"). Negative result: SFT toward a canonical 0–1000 coordinate format collapses Qwen2.5-VL to 18.6%
(vs 77.1% native dialect).
Occupies: PorTAL mechanism on vision-language bases, vision-tower adapter sites, cross-generation and cross-family ports.
Relevance: shows the factorization is cheap to reproduce (~$50) and that the *output-format prior* of the target is a
first-order failure mode — directly relevant to porting onto bases with different generation media (diffusion, bytes).

### 2.2 Post-cutoff papers on the adapter-portability axes

**F7. UpgradeBench: A Decision-Centric Benchmark for Upgrading Fine-Tuned LLM Specialists** —
https://arxiv.org/abs/2608.20918 (HTML https://arxiv.org/html/2608.20918v1) — 2026-08-21 **[post-cutoff]** — arXiv,
first-party preprint; code "will be released publicly upon publication".
Claim: Qwen 7–8B lineage (1.5/2/2.5/3) + 1.5–1.8B track + OLMo continued-pretraining checkpoints (46B vs 2.9T tokens);
six tasks (Banking77, CLINC150, Spider, FinQA, xLAM-FC, glaive-FC). **Only direct LoRA weight copying is measured**;
"shape-incompatible hops admit no weight-space method at all"; learned mappings and distillation are "extension points…
not measured here". Copy across independently pretrained checkpoints of identical architecture collapses (Banking77
92.8%→42.9%, R=−0.551); copy onto a 46B-token continuation retains R=0.88–0.99; retention → floor at 2.9T tokens.
Linear-CKA probe over 256 prompts rank-correlates with retention at Spearman ρ=0.74 across 8 pairs but "no single probe is
decision-grade at n=8". Fixed policy: 0.37pp mean regret, zero regressions, one-third of retraining compute/labels over 33
episodes. Limitations: single 24GB GPU, QLoRA r16 only, English only.
Occupies: the *decision* framing of adapter upgrade; the copy-retention-vs-pretraining-distance law.
Relevance: the field's first upgrade benchmark leaves learned portability (PorTAL-class) *unmeasured* and has no
non-transformer or cross-tokenizer target — a benchmark gap Kevin's harness can fill.

**F8. Cross-Architecture Steering Transfer in Language Models: A Systematic Empirical Study** —
https://arxiv.org/abs/2608.05164 (HTML v1) — arXiv id 2608 (posted 2026-08; page shows submitted 2026-05-26)
**[post-cutoff posting]** — arXiv, first-party preprint, single author, no code.
Claim: GPT-2-large (0.8B), Gemma-2-2B, LLaMA-3.1-8B, Mistral-7B, DeepSeek-7B; two lineages (GPT-2 absolute-positional MHA
vs LLaMA-family RoPE MHA/GQA/SWA); SAEs over 15 domains; B3-TI = per-directed-pair MLP bridge trained on 98,000 passages
(MSE + Pearson penalty) between SAE feature spaces. ≥1.7B: 47–49% of feature pairs validate (Pearson r≥0.60, Procrustes
cosines 0.895–0.956); cross-model steering 71.0% win rate vs 68.0% native; unsupervised universal vectors 67.3% in 4/5
models. Failures: GPT-2-large 29.9–33.3% pass; DeepSeek repetition collapse at scale ≥2; QA and biomedical domains <8%.
No SSM/hybrid models.
Occupies: steering-direction transfer across *transformer* lineages via learned feature bridges.
Relevance: "cross-architecture" here means positional-encoding/attention-variant differences only; the bridge needs a
98k-passage paired corpus per pair — a place where parallel translation data is a natural, semantically aligned stimulus set.

**F9. ACTD: Anchor-Based Cross-Tokenizer Distillation with Residual Regularization** — https://arxiv.org/abs/2608.29662 —
2026-08-30 **[post-cutoff]** — arXiv; **peer-reviewed (EMNLP 2026 main)**.
Claim: cross-tokenizer distillation via vocabulary + sequence alignment with an anchor loss and residual regularization;
extends to multi-teacher. Numbers not on abs page.
Occupies: cross-tokenizer *knowledge* transfer by distillation (not adapter transfer).
Relevance: with F27/F28 it shows the cross-tokenizer axis is being solved at the logit/distillation level, not at the
adapter-representation level.

**F10. When Do Task Vectors Interfere? Mapping the Validity Boundaries of Weight-Space Composition** —
https://arxiv.org/abs/2608.09490 — v1 2026-08-10, v2 2026-08-31 **[post-cutoff]** — arXiv, first-party preprint.
Claim: five model sizes 0.5B–8B, LoRA and full FT; composition non-additivity is seed-stable and *prompt/format
conditioned*: wrapping in the instruction template collapses a +6.9-point interaction contrast to +0.3; an untrained chat
template preserves +12.5; training-format evaluations are blind to it (contradicting preregistered predictions).
Occupies: limits of weight-space task arithmetic.
Relevance: any portability metric read on the training prompt format can hide interference — argues for held-out-format
evaluation in a PorTAL-successor.

**F11. Activation Steering Transfer to Agents: One Gain Ratio Does Not Identify Potency and Efficacy** —
https://arxiv.org/abs/2607.09156 — v1 2026-07-10, v3 2026-08-29 **[post-cutoff revision]** — arXiv, first-party, includes
errata; "pre-registered forecaster refuted".
Claim: across eight family×arm dose-response cells over six models, the gain ratio T=Δ_agent/Δ_chat contains 1 in 5/5
scorable cells, moves with dose in 4/5; proposes dEC50 (curve-location shift) instead; dEC50 spans +1.013 to −886.066.
Occupies: methodology for steering-vector transfer across deployment contexts (negative result on the standard estimator).
Relevance: portability claims stated as a single "percent of lift recovered" (PorTAL's headline metric) inherit the same
dose/format non-identifiability.

**F12. Omni2LoRA: Coherence-Preserving Parametric Memory for Efficient Omni Language Models** —
https://arxiv.org/abs/2608.09227 — 2026-08-10 (cutoff day) — arXiv, first-party preprint.
Claim: Perceiver hypernetwork emits LoRA as parametric memory for audio-visual context; GRPO allocates ranks under a
sub-linear budget; at 30% rank budget +8–12% over OmniZip/OMAC/O-MARC on four AV-QA benchmarks; up to 12× faster TTFT.
Three omni backbones (unnamed on abs page). No cross-base transfer.
Occupies: context→LoRA hypernetworks for omnimodal bases.
Relevance: confirms the "X-to-LoRA" template keeps spreading to new *modalities* while staying single-base.

**F13. MoEGen: Mixture-of-Experts for Instance-Adaptive LoRA Generation** — https://arxiv.org/abs/2608.03275 —
2026-08-04 — arXiv, first-party preprint.
Claim: replaces stored LoRA experts with learnable "expert codes" conditioning a hypernetwork; consistent gains over
static/MoE-PEFT baselines across three backbones on eight commonsense benchmarks (numbers not on abs page).
Occupies: instance-adaptive LoRA generation on a fixed base.
Relevance: another single-base hypernetwork; the expert-code idea is the closest sibling to PorTAL's task latent.

**F14. SHINE repository activity** — https://github.com/MuLabPKU/SHINE (paper https://arxiv.org/abs/2602.06358, v3
2026-07-04) — repo pushed 2026-08-18 **[post-cutoff]** — GitHub, first-party.
Claim: only post-cutoff commit is "Create LICENSE" (2026-08-18); 110 stars. Paper: in-context hypernetwork that reuses the
frozen LLM's own parameters to map context→LoRA in one pass; pretraining + instruction-tuning pipeline; no cross-base claim.
Occupies: single-pass context→LoRA on a fixed base.
Relevance: no movement toward portability; SHINE's "reuse the frozen LLM as the hypernetwork" is base-specific by
construction.

### 2.3 Pre-cutoff work new to this program (transport, merging, stitching)

**F15. Transporting Task Vectors across Different Architectures without Training (Theseus)** —
https://arxiv.org/abs/2602.12952 (HTML v3 2026-07-30) — v1 2026-02-13 — arXiv; **peer-reviewed (ICML 2026)**; code
https://github.com/apanariello4/merge-and-rebase.
Claim: training-free transport of task updates across *widths* by characterizing updates through their effect on
intermediate representations and solving orthogonal Procrustes; needs only B∈{1,…,20} unlabeled forward-pass batches of
32. T5-3B→T5-Large on GLUE: target zero-shot 57.87% → Theseus 76.78% (fine-tuned target 87.92%). ViT-B/16→ViT-B/16+
(8-vision): 58.76% → 69.08% (FT 90.39%). ViT-B→ViT-L (depth+width): +6.61. All pairs same family, transformer only;
depth alignment is "heuristic and intentionally naive".
Occupies: training-free, label-free width/depth transport of task vectors *within a family*.
Relevance: this is the closest existing answer to "label-free base alignment" (Direction 8) — but it transports a
*single* update per task with a gap of ~11–21 points to fine-tuning, and has no cross-family or cross-operator case.

**F16. Transport and Merge: Cross-Architecture Merging for Large Language Models** — https://arxiv.org/abs/2602.05495
(HTML v2 2026-02-22) — v1 2026-02-05 — arXiv, first-party preprint; code linked from paper.
Claim: optimal transport on activations (2,000 sampled inputs per dataset) infers cross-neuron correspondences, then
direct weight-space fusion from large source to small heterogeneous target: LLaMA-3-8B → Malaysian/Indonesian/Thai/
Cantonese LLaMA-3-1B variants; **Qwen2.5-7B → LLaMA-3-1B-finance (cross-family, different tokenizers)**. Gains: MalayMMLU
+3.3 to +6.5 per category; Indonesian 38.43→39.30; CMMLU Cantonese 25.26→27.44; medical 46.30→47.87; finance 0.32→0.35.
All transformers.
Occupies: cross-family, cross-tokenizer *weight-level* transfer of general knowledge via OT on activations.
Relevance: proves activation-OT alignment survives a tokenizer change at the weight level, with small gains; nobody has
used the same alignment to carry a *task adapter* or a hypernetwork core.

**F17. Can Heterogeneous Language Models Be Fused? (HeteroFusion)** — https://arxiv.org/abs/2604.01674 (v2 2026-05-16);
code https://github.com/ECNU-ICALK/HeteroFusion (pushed 2026-09-01, 5 stars) — v1 2026-04-02 — arXiv, first-party preprint.
Claim: fuses Llama/Qwen/Mistral experts via topology-based alignment + conflict-aware denoising; identifies
"architectural mismatch, latent basis misalignment, and amplified cross-source conflict" as the failure sources. Numbers
not on abs page.
Occupies: heterogeneous-family model fusion.
Relevance: independent confirmation that cross-family weight alignment is being attacked by merging groups; code is live.

**F18. Bilinear Coordinate Alignment for Training-Free Task-Vector Transfer (BiCo)** — https://arxiv.org/abs/2605.28444 —
2026-05-27 — arXiv, first-party preprint.
Claim: task vectors reformulated as accumulated bilinear interactions between input activations and output gradients;
orthogonal Procrustes in both spaces from one forward-backward pass on a small calibration set; transfers across models
differing in "width, depth, and pre-training configuration". Numbers not on abs page.
Occupies: training-free task-vector transport across model versions (second entrant after Theseus).
Relevance: two groups converged on Procrustes-based transport in 2026; both stay inside transformer families.

**F19. The Master Key Hypothesis: Unlocking Cross-Model Capability Transfer via Linear Subspace Alignment (UNLOCK)** —
https://arxiv.org/abs/2604.06377 (v3 2026-05-05); code https://github.com/rishabbala/Steering-Vector-Transfer (19 stars)
— v1 2026-04-07 — arXiv, first-party preprint.
Claim: contrast activations of capability-present vs -absent source variants, align via low-rank linear map, inject at
inference: Qwen1.5-14B→7B CoT +12.1% on MATH; Qwen3-4B-Base→Qwen3-14B-Base AGIEval-Math 61.1%→71.3% (above the
post-trained 14B's 67.8%). "Transfer depends on capabilities learned during pre-training."
Occupies: within-family activation-level capability transfer.
Relevance: activation-space transfer is a competitor to weight-space porting for *behavioral* capabilities; none of it
crosses operator families.

**F20. Transferring Linear Features Across Language Models With Model Stitching** — https://arxiv.org/abs/2506.06609
(latest 2025-11-01) — v1 2025-06-07 — arXiv; **peer-reviewed (NeurIPS 2025 per Semantic Scholar venue field)**.
Claim: affine maps between residual streams transfer SAEs, probes and steering vectors small→large; SAE training on the
larger model becomes ~50% cheaper when initialized from transferred SAEs; "semantic and structural features transfer
noticeably differently".
Occupies: affine residual-stream stitching as the baseline alignment primitive.
Relevance: the cheapest alignment primitive; PorTAL's P_in/P_out maps are of this kind.

**F21. Signed-Permutation Coordinate Transport for RMSNorm Transformers** — https://arxiv.org/abs/2606.31963 —
2026-06-30 — arXiv, first-party preprint, single author.
Claim: RMSNorm models need signed-permutation (not permutation-only) gauge alignment to move coordinate-indexed objects
(steering vectors, SAEs, merge alignments) across checkpoints; cross-run coordinate recovery 91.1% at 1,500 steps vs 60.3%
endpoint matching; steering-effect preservation 95.8% under signed-permutation vs 17.2% under permutation-only.
Occupies: gauge-aware transport of coordinate objects across checkpoints of one base.
Relevance: any alignment learned across bases must be gauge-aware; a concrete pitfall for Procrustes-style alignments on
RMSNorm bases (Qwen, Llama, Kimi).

### 2.4 Pre-cutoff hypernetwork / X-to-LoRA family (all single-base)

**F22. Text-to-LoRA: Instant Transformer Adaption** — https://arxiv.org/abs/2506.06105 — v2 2025-06-09 — arXiv;
**peer-reviewed (ICML 2025)**; repo https://github.com/SakanaAI/text-to-lora (0 commits since 2026-08-10).
Claim: hypernetwork trained on 9 LoRAs builds LoRAs from a task description in one forward pass; matches task-specific
adapters; zero-shot to unseen tasks; compresses hundreds of LoRAs. Single base per hypernetwork.
Occupies: description→LoRA on a fixed base.

**F23. Doc-to-LoRA: Learning to Instantly Internalize Contexts** — https://arxiv.org/abs/2602.15902 — 2026-02-13 —
arXiv, first-party preprint (Sakana).
Claim: single-pass context distillation into LoRA; near-perfect zero-shot NIAH at >4× native context; beats standard
context distillation on QA with lower peak memory. No cross-base transfer.
Occupies: context→LoRA on a fixed base.

**F24. The Override Gap: A Magnitude Account of Knowledge Conflict Failure in Hypernetwork-Based Instant LLM Adaptation**
— https://arxiv.org/abs/2604.23750 (v2 2026-05-11) — v1 2026-04-26 — arXiv, first-party preprint. **Negative result.**
Claim: Doc-to-LoRA-style adaptation collapses to 46.4% on the deepest conflicting facts because the adapter margin is
roughly constant while the pretrained margin grows with training frequency; 68%→16% from weak- to strong-prior
questions; proposed fixes reach 71.0% (Gemma-2B) and 72.5% (Mistral-7B); +18 points over vanilla RAG on medium conflicts.
Occupies: a structural failure law for generated adapters.
Relevance: a PorTAL-successor that ports *knowledge* rather than *skills* inherits this ceiling.

**F25. Scaling Laws for Hypernetwork-Based Knowledge Injection in Large Language Models** —
https://arxiv.org/abs/2607.19604 (HTML v1) — 2026-07-21 — arXiv, first-party preprint; data
https://huggingface.co/collections/nace-ai/hypernetwork-datasets.
Claim: Qwen2.5 0.5B–14B targets; hypernetworks 167M–2.8B; power-law exponents (loss = a·x^b): HN width −0.096 ID /
−0.100 OOD; HN depth −0.088 / −0.096; target size −0.226 ID / −0.184 OOD-nonrephrased / −0.107 OOD-rephrased vs LoRA
−0.250 / −0.151 / −0.083 and full FT −0.249 / −0.183 / −0.069 — "substantially steeper OOD generalization scaling" for
hypernetworks, widening with target size. Limitation: the hypernetwork "can become nearly as large as the target model"
(2.5B vs 1.5B).
Occupies: scaling behaviour of train-time hypernetwork injection on one family.
Relevance: gives the first exponents to budget a portable-hypernetwork program; also a warning that the "thin" story
breaks as knowledge load grows.

**F26. Model of Models: When Does Emitting a Specialist Beat Attending, Adapting, or Tuning?** —
https://arxiv.org/abs/2608.21386 — 2026-07-20 (arXiv 2608 posting) — arXiv, first-party preprint, single author.
**Negative result for emission on sequence modeling.**
Claim: four-way comparison (zero-shot, in-context, test-time gradients, hypernetwork emission) over six tasks; emission ties
TabPFN on clinical few-shot and reaches noise-floor shape generation with a 132-float program, but on high-dimensional
sequence modeling a one-pass adapter recovers only 14.0±0.9% (5M) / 11.2±0.5% (15M) of the in-context gain; LoRA-rank sweep
lifts capture 5%→21% then plateaus; emitted specialists compose by interpolation.
Occupies: the operating-regime map for weight emission vs attention.
Relevance: bounds what a portable emitted adapter can carry for language tasks; the composition-by-interpolation result is
a testable property for a shared task latent.

**F27. Program-as-Weights: A Programming Paradigm for Fuzzy Functions (PAW)** — https://arxiv.org/abs/2607.02512;
compilers https://huggingface.co/programasweights/paw-4b-qwen3-0.6b and https://huggingface.co/programasweights/paw-4b-gpt2;
org https://github.com/programasweights (pushed 2026-09-01) — 2026-07-02 — arXiv, first-party; card states "AIware 2026"
acceptance (not independently verified).
Claim: a Qwen3-4B-Instruct compiler + `lora_mapper` (trunk + coefficient head + 64 learnable LoRA basis matrices, r64,
64 prefix tokens) emits a LoRA "program" (~22 MB) for a Qwen3-0.6B interpreter; a **separate** compiler emits ~5 MB
programs for a GPT-2-124M interpreter (stock GPT-2 BPE, context extended to 2048). 0.6B interpreter reaches parity with
Qwen3-32B prompting at ~1/50 memory, 30 tok/s on M3. FuzzyBench 10M examples. paw-programs dataset: 16,099 downloads;
`claudish` repo 250 stars; `rules-as-programs` active 2026-09-01.
Occupies: spec→LoRA compilation onto small fixed interpreters, one compiler per interpreter.
Relevance: two interpreters with different tokenizers exist, but portability is achieved by *retraining the compiler*,
not by a shared program representation — the exact seam PorTAL's canonical core is meant to close.

**F28. X-to-LoRA siblings (all single-base, 2026):** Compliance2LoRA https://arxiv.org/abs/2607.27594 (v3 2026-08-05;
policy→LoRA for reasoning models); Code2LoRA https://arxiv.org/abs/2606.06492 (2026-06-04; repo→LoRA, GRU state per diff;
63.8% cross-repo EM static, 60.3% evolution, +5.2pp); Parametric Skills https://arxiv.org/abs/2606.30015 (2026-06-29;
skill text→LoRA, +6.44 judge points over ICL on six SWE subtasks); LatentSkill https://arxiv.org/abs/2606.06087 (v3
2026-08-26; ALFWorld +21.4 seen / +13.4 unseen, −63.9% prefill tokens); SkillSmith https://arxiv.org/abs/2607.27497
(2026-07-29; prefix-weight synthesis from weights+text); "Good Agentic Friends… Can Update Your Weights"
https://arxiv.org/abs/2605.13839 (2026-05-13; sender activations → transient LoRA on receiver, three Qwen3-4B agents,
+8.5 acc, −83.27% tokens, 4.6× faster); HypeLoRA https://arxiv.org/abs/2603.19278 (v2 2026-03-29; RoBERTa/GLUE
calibration study, not portability). — arXiv, all first-party preprints.
Occupies: every input modality → LoRA on a *fixed* base (policy, repo, skill, peer activations).
Relevance: none ports across bases; the "sender→receiver weight perturbation" paper is the only one whose generator
conditions on *another model's* activations — same-architecture only.

### 2.5 Cross-tokenizer, cross-family base conversion, hybrids, weight-space learning

**F29. Cross-tokenizer transfer by distillation / logit translation** — Universal Cross-Tokenizer Distillation via
Approximate Likelihood Matching https://arxiv.org/abs/2503.20083 (v4 2025-10-24; **NeurIPS 2025**; includes
"embedding prediction hypernetworks for training-free tokenizer transfer" and subword→byte transfer);
Cross-Tokenizer On-Policy Distillation via Byte-Prefix Marginalization https://arxiv.org/abs/2607.22334 (2026-07-24;
teachers Qwen3-32B, GLM-Z1-9B, MiniMax-M2.7; +3.7–6.6 avg@8 over strongest baselines; exact byte-prefix marginal at >99%
of positions); ALIGNBEAM https://arxiv.org/abs/2606.12342 (2026-06-10; token-by-token logit translation across
vocabularies for safety transfer); HYPEROFA https://arxiv.org/abs/2504.21018 (ACL SRW 2025; hypernetwork embedding init
for new-language tokens); Hyper-X https://arxiv.org/abs/2205.12148 (**EMNLP 2022**; one hypernetwork generating adapters
conditioned on task × language embeddings, zero-shot to unseen languages, single base).
Occupies: cross-tokenizer *knowledge* transfer (distillation, logit mixing) and tokenizer *extension* (embedding init);
task×language-conditioned adapter generation on one base.
Relevance: the byte space is already the accepted common coordinate for cross-tokenizer probability transfer; nobody has
used it as the anchor for cross-tokenizer *adapter* alignment. Hyper-X is the 2022 precedent for language-conditioned
adapter hypernetworks — Kevin's multilingual angle must cite and exceed it.

**F30. Base-weight conversion across architecture families (no adapters carried)** — Attention to Mamba: A Recipe for
Cross-Architecture Distillation https://arxiv.org/abs/2604.14191 (2026-04-01; Pythia-1B → Mamba, ppl 14.11 vs teacher
13.86 on 10B tokens); Long-Context Aware Upcycling https://arxiv.org/abs/2604.24715 (2026-04-27; Llama/Qwen 1–3B →
MLA + Mamba2/Gated-DeltaNet hybrids on 10B tokens, up to 32× context, >90% KV reduction, HyLo-Qwen-1.7B beats
JetNemotron on GSM8K); Don't Retrain, Align: AR→DLM via Representation Alignment https://arxiv.org/abs/2605.06885
(2026-05-07; cosine alignment of every layer to the frozen AR model, identical architecture, up to 4× faster DLM training).
— arXiv, first-party preprints.
Occupies: porting *base* capability transformer→SSM/hybrid and AR→diffusion.
Relevance: the substrate for cross-family adapter porting exists (aligned pairs of transformer and hybrid/diffusion
checkpoints), but every paper asks whether the *base* survives, never whether its *fine-tunes* do.

**F31. Adapting hybrid models is its own hazard** — Where Should LoRA Go? Component-Type Placement in Hybrid Language
Models https://arxiv.org/abs/2604.22127 (2026-04-24; Qwen3.5-0.8B [GatedDeltaNet + softmax attention, sequential] and
Falcon-H1-0.5B [Mamba-2 + attention, parallel]; attention-pathway LoRA uses 5–10× fewer parameters; recurrent-pathway
adaptation −14.8pp GSM8K on the sequential hybrid but +8.6pp on the parallel hybrid; "parallel hybrids exhibit positive
cross-task transfer while sequential hybrids suffer catastrophic forgetting"); Attention Amnesia in Hybrid LLMs
https://arxiv.org/abs/2606.11052 (v2 2026-08-30; **EMNLP 2026 main**; CoT SFT drops HypeNet-9B NIAH-S2@256K from 67.2% to
9.4%; QK-Restore fixes by restoring pre-SFT W_Q/W_K). No adapter is ported from a transformer in either.
Occupies: *where* to place adapters inside hybrids, and a documented long-range-recall failure of fine-tuning hybrids.
Relevance: defines the target-side constraints (attention-pathway sites, recall-preserving) that any transformer→hybrid
adapter port must satisfy; also supplies the natural adapter-site choice (attention pathway) that PorTAL's q/v-only
topology already matches.

**F32. Weight-space learning and parameter generation for unseen architectures** — Position: Weight Space Should Be a
First-Class Generative AI Modality https://arxiv.org/abs/2605.18632 (2026-05-18; lists cross-architecture weight
generation and adapter-scale conditional generation as open); WeightCLIP https://arxiv.org/abs/2607.03551 (**ICML 2026**;
dataset↔weights contrastive alignment); NNiT https://arxiv.org/abs/2603.00180 (v2 2026-06-20; width-agnostic weight
generation via GHN + CNN-decoder-aligned weight patches; >85% success on unseen MLP topologies, MLPs only); LoGAH
https://arxiv.org/abs/2405.16287 (2024-05-25; graph hypernetwork predicts 774M-parameter GPT-2/ViT *initializations* with
1/100 parameters). — arXiv.
Occupies: architecture-conditioned weight generation for initialization (GHN family) and weight-space representation
learning.
Relevance: Direction 8's "predict the base alignment from topology + sketches" has GHN/LoGAH as the mechanism precedent,
but no work generates *adapter alignments* for LLMs from architecture graphs.

**F33. Legacy LoRA-transfer baselines (for the baseline table)** — Cross-LoRA https://arxiv.org/abs/2508.05232
(2025-08-07; data-free SVD subspace alignment + projection; "up to 5.26%" relative over base; PorTAL reports it recovers
~14% of LoRA lift on Qwen3-8B); Trans-LoRA https://arxiv.org/abs/2405.17258 (2024-05-27; NeurIPS 2024; synthetic data
transfer within/across Llama and Gemma families, "lossless (mostly improved)"); LoRA-X https://arxiv.org/abs/2501.16559
(**ICLR 2025**; training-free, SD1.5↔SDXL, subspace-similarity gated); TiTok https://arxiv.org/abs/2510.04682 (**ICLR 2026**;
token-wise contrastive excess filters synthetic data, +4–10% over baselines, no discriminator); Exploring Data-Free LoRA
Transferability for Video Diffusion Models (CASA) https://arxiv.org/abs/2605.01929 (**ICML 2026**; LoRAs across step-/causal-
distilled video diffusion variants fail by "spectral interference within shared functional clusters"; CASA arbitrates by
spectral density).
Occupies: training-free and synthetic-data LoRA transfer between transformer LMs and between diffusion variants.
Relevance: the mandatory baseline set; CASA is the only paper that *diagnoses* why weight-level transfer breaks
(conflicting singular-subspace routing), a diagnostic a cross-family study should reuse.

**F34. Localized Adaptation Reveals Distinct Learning Signatures in Transformers** — https://arxiv.org/abs/2607.25663 —
2026-07-28 — arXiv, first-party preprint.
Claim: five objectives (lexical binding, factual association, behavioral policy, causal mapping, procedural reasoning)
each have an "adaptation geometry" (acquisition/transfer/boundedness under early/middle/late/full-stack LoRA); "directional
contrasts replicate across five model families".
Occupies: cross-family regularities in *where* adaptation should land.
Relevance: evidence that some adaptation structure is family-invariant — the empirical premise a portable
alignment-predictor (Direction 8) needs.

---

## 3. Occupied-axes table

| # | Axis | What is taken (primary URLs) | Status |
|---|---|---|---|
| A1 | Task/context/spec → LoRA hypernetworks on a fixed base | T2L 2506.06105 (ICML'25), Doc-to-LoRA 2602.15902, SHINE 2602.06358, Compliance2LoRA 2607.27594, Code2LoRA 2606.06492, Parametric Skills 2606.30015, LatentSkill 2606.06087, Omni2LoRA 2608.09227, MoEGen 2608.03275, PAW 2607.02512 | Saturated; single-base by construction |
| A2 | Cross-base LoRA transfer among softmax-attention transformer LMs | Cross-LoRA 2508.05232, LoRA-X 2501.16559 (ICLR'25), Trans-LoRA 2405.17258, TiTok 2510.04682 (ICLR'26), PorTAL blog + HF refits (Qwen→Gemma-3/Gemma-4-E2B/Mistral/Inkling), portal-vlm (Qwen2.5-VL→Qwen3-VL/Gemma-3) | Occupied incl. MoE, local/global attention, multimodal wrappers, different tokenizers (untested as a variable) |
| A3 | Training-free transport of task vectors / weights across widths and heterogeneous transformers | Theseus 2602.12952 (ICML'26), BiCo 2605.28444, Transport-and-Merge 2602.05495, HeteroFusion 2604.01674 | Occupied within transformers; OT survives tokenizer change at weight level |
| A4 | Activation/steering-direction transfer across models | Model stitching 2506.06609 (NeurIPS'25), UNLOCK 2604.06377, Cross-Architecture Steering Transfer 2608.05164, Signed-Permutation Transport 2606.31963, steering-to-agents 2607.09156 | Occupied for transformers; methodology caveats published |
| A5 | Cross-tokenizer knowledge transfer and tokenizer extension | ALM 2503.20083 (NeurIPS'25), BPM 2607.22334, ACTD 2608.29662 (EMNLP'26), ALIGNBEAM 2606.12342, HYPEROFA 2504.21018, Hyper-X 2205.12148 (EMNLP'22) | Occupied at logit/distillation/embedding level, not at adapter level |
| A6 | Base-weight conversion across architecture families | Attention-to-Mamba 2604.14191, HyLo upcycling 2604.24715, REPR-ALIGN AR→DLM 2605.06885 (plus LoLCATs 2410.10254 in prior sweep) | Occupied for base capability; adapters/fine-tunes never carried |
| A7 | Adapter placement/failure modes inside hybrid LMs | Where Should LoRA Go? 2604.22127, Attention Amnesia 2606.11052 (EMNLP'26) | Occupied for *native* adaptation of hybrids |
| A8 | Architecture-conditioned weight generation / weight-space learning | GHN/LoGAH 2405.16287, NNiT 2603.00180, WeightCLIP 2607.03551 (ICML'26), position paper 2605.18632 | Occupied for init/MLP/ViT; cross-architecture LLM adapter generation explicitly listed as open by the position paper |
| A9 | Adapter-upgrade decision benchmarking | UpgradeBench 2608.20918 | Occupied for direct copying on Qwen/OLMo transformer lineages; learned mappings deferred |
| A10 | Negative-result laws bounding generated adapters | Override Gap 2604.23750, Model of Models 2608.21386, hypernetwork scaling 2607.19604, task-vector interference 2608.09490 | Published; must be cited as ceilings |

---

## 4. Open gaps (each was searched; each came back empty or adjacent-only)

**G1. Porting a task adapter across *operator* families (softmax transformer → KDA/GDN/Mamba hybrid, → masked-diffusion LM,
→ byte-level BLT).**
Why open: PorTAL's "hybrid attention" (Inkling, Gemma-4) is local/global softmax attention (verified in Inkling's
config.json); A6 papers convert *bases*, not fine-tunes; A7 papers adapt hybrids natively; UpgradeBench says
"shape-incompatible hops admit no weight-space method at all" and measures none.
Evidence: arXiv `(LoRA|adapter|fine-tuning) AND (Mamba|"state space"|"linear attention"|hybrid) AND (transfer|port|distill)
AND transformer AND pretrained` → only distillation/upcycling and LoLCATs; `hypernetwork AND (Mamba|"state space model"|
"linear attention"|"hybrid attention")` → 3 irrelevant; `("Kimi Linear"|"Gated DeltaNet"|"Qwen3-Next"|"Nemotron-H"|
"hybrid architecture"|"hybrid LLM") AND (LoRA|fine-tuning|adapter) AND (transfer|port|convert)` → only 2604.22127 and
2604.24715; `(LLaDA|"diffusion LLM") AND (LoRA|adapter) AND (transfer|port|"from autoregressive")` → 4 irrelevant;
`("byte latent"|"byte-level"|"tokenizer-free") AND (LoRA|adapter|fine-tuning) AND (transfer|port)` → 6 irrelevant;
Semantic Scholar "cross-architecture transfer transformer Mamba adapter" → 429 (not answered); GitHub repo searches
"lora transfer hypernetwork", "cross-model lora" → 0 relevant.
Kevin advantage: Kimi-Linear-48B-A3B (KDA hybrid), Mamba-130M, LLaDA-8B and BLT-1B are already registered locally with
pinned revisions; Tinker gives LoRA on Kimi-K2.6/Qwen3.5/GLM-5.3 for source-side adapters; 8×H100 covers alignment refits
at 48B-A3B scale; the Slurm/Docker checkpoint harness makes the task×base grid reproducible. The PorTAL q/v-only topology
already coincides with the attention pathway that 2604.22127 identifies as the safe LoRA site in hybrids.

**G2. Label-free / task-blind base alignment for a portable hypernetwork (Direction 8 restated).**
Why open: PorTAL refits use 8–2,000 *gold-labeled* examples per task; Theseus/BiCo are label-free but transport one static
task vector within a family with an 11–21 point gap to fine-tuning; Cross-Architecture Steering needs a per-pair MLP bridge
on 98k passages; UpgradeBench's CKA probe only *predicts* copy retention (ρ=0.74, n=8) and does not produce an alignment.
Evidence: arXiv `hypernetwork AND ("unseen architecture"|"arbitrary architecture"|"architecture-agnostic"|"graph
hypernetwork")` → GHN/LoGAH/NNiT (init only); `"canonical" AND hypernetwork AND "base model" AND LoRA` → 0;
`"weight space" AND (hypernetwork|…) AND (LoRA|adapter|"language model") AND generat*` → 0; Ramp blog: no label-free
refitting described.
Kevin advantage: parallel translation data is a *paired, label-free, semantically anchored* stimulus set that exists in the
same meaning space for every base regardless of tokenizer — the natural calibration stream for activation-OT/Procrustes
alignment (F15, F16, F20) without task labels; 8×H100 for the 12–20-model meta-training grid Direction 8 requires.

**G3. Tokenizer-invariant adapter representation (byte- or meaning-anchored alignment) with cross-tokenizer transfer
measured as a controlled variable.**
Why open: PorTAL crosses tokenizers (Qwen→Gemma/Mistral/Inkling) but "each base uses its own tokenizer" and the blog never
analyzes it; the byte space is the accepted coordinate for cross-tokenizer *probability* transfer (ALM, BPM) but no paper
uses byte or translation anchors to align *adapters*; Hyper-X conditions adapters on language embeddings on one base only.
Evidence: arXiv `(adapter|LoRA) AND (tokenizer|vocabulary|"cross-tokenizer") AND (transfer|port|transplant)` → 634 hits, none
on adapter alignment across tokenizers; `"tokenizer transfer" OR "cross-tokenizer" OR …` → distillation/embedding-init only;
Semantic Scholar "adapter transfer across tokenizers vocabulary" → FUSE (prompt optimization), TokAlign, Trans-Tokenization,
Franken-Adapter (embedding surgery), none on portable task adapters; `("parallel data"|"machine translation") AND LoRA AND
(transfer|"cross-lingual") AND ("across models"|hypernetwork|"different models")` → 0.
Kevin advantage: General Translation's production parallel corpora span scripts and tokenizer-fertility regimes; BLT-1B is
registered locally as a tokenizer-free control base; translation-equivariance is already Direction 18's framing.

**G4. Porting an *update rule* (online/test-time sidecar dynamics) rather than static adapter weights, evaluated on a
held-out task×base cell (Direction 16 restated).**
Why open: nothing in the LLM setting transfers a learned update rule across operator families; prior-sweep collisions
(VeLO, Celo2, Meta-TTL, learned optimizers) remain the closest; 2604.01170 (ORCA, COLM 2026) transfers a *calibration
module* across families, not a weight-update rule.
Evidence: arXiv `("test-time training"|"fast weight"|"update rule") AND ("across models"|"cross-model"|portable|"across
architectures") AND "language model"` → 1 hit (ORCA); `("learned optimizer"|"learned update rule"|"meta-learned update") AND
(transfer|portable|"across architectures"|"unseen architectures"|generalize)` → 535 hits, none LLM-cross-architecture in top 30;
`("plasticity rule"|"learning rule"|"update rule") AND (transfer|generalize) AND ("different architectures"|"unseen
architectures"|"across architectures"|"new architectures")` → 2 hits from 2018/2020.
Kevin advantage: the SIGUSR1-checkpoint/resume harness is built for long meta-training with truncated BPTT; Tinker's RL/LoRA
loop supplies a structured-outcome feedback stream; parallel data provides a supervised streaming-label regime that is
identical across bases.

**G5. A sealed task×base portability benchmark that includes non-transformer targets, cross-tokenizer pairs, generative
tasks, and learned-mapping methods.**
Why open: UpgradeBench (2026-08-21) is Qwen/OLMo, direct-copy only, QLoRA r16, six English tasks, and defers learned
mappings; portallib-tasks has two documented artifacts (#27 prefix slicing, #28 gold-index-0) and uses validation for both
selection and reporting; portal-vlm is one seed on one GPU.
Evidence: arXiv `(upgrade|upgrading) AND ("fine-tuned"|specialist|LoRA) AND ("base model"|"new model"|"model version")` → 7
hits, only UpgradeBench relevant; GitHub "upgradebench" → 0 repos (code unreleased).
Kevin advantage: the digest-pinned Docker/Slurm harness plus locally registered transformer, KDA-hybrid, SSM, diffusion and
byte-level bases make a multi-family sealed-cell benchmark a systems deliverable rather than a research risk.

**G6. Language×task×base shared latent: portable adapters whose task latent is learned from *parallel* data so that the
same latent ports across languages and bases.**
Why open: Hyper-X (2022) conditions on language and task on one base; PorTAL conditions on task across bases; no work
does both, and no work uses translation pairs as the identification signal for the task latent.
Evidence: arXiv `hypernetwork AND ("machine translation"|multilingual|"cross-lingual") AND (adapter|LoRA)` → 5 hits
(Hyper-X, HYPEROFA, TTS, FL), all single-base; `("parallel data"|"parallel corpus"|"machine translation") AND LoRA AND
(transfer|"cross-lingual") AND ("across models"|hypernetwork|"different models")` → 0.
Kevin advantage: this is the one gap where the parallel-translation asset is the *defining* input rather than an aid;
Tinker access to Kimi/Qwen/GLM gives multilingual bases with different tokenizers to port across.

**Not a gap (re-confirmed occupied, do not re-propose without delta):** "train once, port a LoRA" among softmax
transformers (A2); task-description→LoRA hypernetworks (A1); training-free task-vector transport within a family (A3);
steering-vector transfer among transformers (A4).

---

## 5. Exact queries run (81 distinct successful searches; primary-source opens not counted)

### arXiv API (`https://export.arxiv.org/api/query?search_query=…&sortBy=submittedDate&sortOrder=descending`) — 30
1. `id_list=2602.06358` (SHINE metadata)
2. `(abs:LoRA OR abs:adapter OR abs:fine-tuning) AND (abs:Mamba OR abs:"state space" OR abs:"linear attention" OR abs:hybrid) AND (abs:transfer OR abs:port OR abs:distill) AND abs:transformer AND abs:pretrained`
3. `(abs:"steering vector" OR abs:"activation steering" OR abs:"steering vectors") AND (abs:transfer OR abs:portable OR abs:"across models" OR abs:"cross-model")`
4. `(abs:"task arithmetic" OR abs:"task vector" OR abs:"task vectors" OR abs:"model merging") AND (abs:"different architectures" OR abs:heterogeneous OR abs:"across architectures" OR abs:"cross-architecture")`
5. `(abs:"weight space" OR abs:"weight-space" OR abs:"neural functional") AND (abs:LoRA OR abs:"language models") AND (abs:learning OR abs:generation)`
6. `(abs:"learned optimizer" OR abs:"learned optimizers" OR abs:"learned update rule" OR abs:"meta-learned update") AND (abs:transfer OR abs:portable OR abs:"across architectures" OR abs:"unseen architectures" OR abs:generalize)`
7. `abs:LoRA AND (abs:hypernetwork OR abs:hyper-network OR abs:hypernetworks)` (40 results)
8. `abs:LoRA AND abs:transfer AND (abs:"across models" OR abs:"cross-model" OR abs:"different base" OR abs:"new base model" OR abs:"base model updates")`
9. `(abs:adapter OR abs:LoRA) AND (abs:tokenizer OR abs:vocabulary OR abs:"cross-tokenizer") AND (abs:transfer OR abs:port OR abs:transplant)`
10. `ti:LoRA AND (ti:transfer OR ti:port OR ti:portable OR ti:transplant OR ti:"cross-model")`
11. `(abs:"diffusion language model" OR abs:"masked diffusion" OR abs:dLLM) AND (abs:LoRA OR abs:adapter) AND (abs:autoregressive) AND (abs:transfer OR abs:port OR abs:convert)`
12. `abs:hypernetwork AND (abs:"unseen architecture" OR abs:"unseen architectures" OR abs:"arbitrary architecture" OR abs:"arbitrary architectures" OR abs:"architecture-agnostic" OR abs:"graph hypernetwork")`
13. `(abs:"test-time training" OR abs:"fast weight" OR abs:"fast weights" OR abs:"update rule") AND (abs:"across models" OR abs:"cross-model" OR abs:portable OR abs:"across architectures") AND abs:"language model"`
14. `abs:hypernetwork AND (abs:Mamba OR abs:"state space model" OR abs:"linear attention" OR abs:"hybrid attention")`
15. `(abs:"parallel data" OR abs:"parallel corpus" OR abs:"machine translation") AND abs:LoRA AND (abs:transfer OR abs:"cross-lingual") AND (abs:"across models" OR abs:hypernetwork OR abs:"different models")` → 0
16. `abs:"weight space" AND (abs:hypernetwork OR abs:"neural network weights" OR abs:"parameter space") AND (abs:LoRA OR abs:adapter OR abs:"language model") AND abs:generat*` → 0
17. `(abs:upgrade OR abs:upgrading) AND (abs:"fine-tuned" OR abs:specialist OR abs:LoRA) AND (abs:"base model" OR abs:"new model" OR abs:"model version")`
18. `abs:"tokenizer transfer" OR abs:"cross-tokenizer" OR abs:"vocabulary transfer" OR abs:"tokenizer transplant"`
19. `abs:Procrustes AND (abs:LoRA OR abs:"task vector" OR abs:"task vectors" OR abs:adapter OR abs:"weight update")`
20. `(abs:"parameter generation" OR abs:"weight generation" OR abs:"generating neural network weights") AND (abs:LoRA OR abs:"language model" OR abs:"language models")`
21. `abs:hypernetwork AND (abs:"machine translation" OR abs:multilingual OR abs:"cross-lingual") AND (abs:adapter OR abs:LoRA)`
22. `(abs:"byte latent" OR abs:"byte-level" OR abs:"tokenizer-free") AND (abs:LoRA OR abs:adapter OR abs:"fine-tuning") AND (abs:transfer OR abs:port)`
23. `(abs:LLaDA OR abs:"diffusion LLM" OR abs:"diffusion large language model") AND (abs:LoRA OR abs:adapter) AND (abs:transfer OR abs:port OR abs:"from autoregressive")`
24. `abs:"canonical" AND abs:hypernetwork AND (abs:"base model" OR abs:"base models") AND abs:LoRA` → 0
25. `ti:"weight space" OR ti:"weight-space"`
26. `ti:PorTAL OR abs:"PorTAL" OR abs:"portable task adaptation" OR abs:"portable task adapters"` → no PorTAL paper
27. `(abs:"Kimi Linear" OR abs:"Gated DeltaNet" OR abs:"Qwen3-Next" OR abs:"Nemotron-H" OR abs:"hybrid architecture" OR abs:"hybrid LLM") AND (abs:LoRA OR abs:"fine-tuning" OR abs:adapter) AND (abs:transfer OR abs:port OR abs:convert)`
28. `(abs:"plasticity rule" OR abs:"plasticity rules" OR abs:"learning rule" OR abs:"learning rules" OR abs:"update rule") AND (abs:transfer OR abs:generalize OR abs:generalizes) AND (abs:"different architectures" OR abs:"unseen architectures" OR abs:"across architectures" OR abs:"new architectures")`
29. `abs:"task latent" AND (abs:LoRA OR abs:adapter OR abs:hypernetwork)`
30. `(abs:"function vector" OR abs:"function vectors" OR abs:"task vector") AND (abs:"across models" OR abs:"cross-model" OR abs:"different models" OR abs:"between models") AND abs:"language model"`

### Semantic Scholar (`/graph/v1/paper/search`) — 4 answered (13 more returned HTTP 429 after retries)
1. `hypernetwork generates LoRA from task description`
2. `transfer LoRA adapters between different base models`
3. `adapter transfer across tokenizers vocabulary`
4. `steering vector transfer across language models`
(429'd: cross-model LoRA adapter transfer hypernetwork; …new base model; model merging different architectures heterogeneous;
weight space learning hypernetwork adapters; learned update rule transfer architectures; hypernetwork LoRA diffusion language
model; cross-architecture transfer transformer Mamba adapter; PorTAL portable task adaptation Ramp; cross-architecture
transfer of task vectors LoRA heterogeneous width; upgrading fine-tuned specialists to new base model benchmark; and 3 duplicates.)

### GitHub (`gh search repos --sort updated`, `gh search code`, `gh search issues`) — 20
repos: `lora transfer hypernetwork`, `text-to-lora`, `cross-model lora`, `portallib`, `lora hypernetwork llm`, `adapter transfer
tokenizer`, `steering vector transfer`, `portal-vlm`, `portal hypernetwork lora`, `hypernetwork lora generation llm`, `lora-x
cross-model`, `trans-lora`, `theseus task vectors`, `upgradebench`, `transport merge cross-architecture`, `cross-architecture
steering`, `heterofusion`; code: `portallib`; issues: `portallib`, `PorTAL LoRA hypernetwork`.
Repo inspections (not counted): ramp-public/portallib (metadata, commits since 2026-08-10, releases, issues, forks, README,
REPRODUCING.md, issue #28 + comments), SakanaAI/text-to-lora commits, MuLabPKU/SHINE commits, robbym-dev/portal-vlm,
rishabbala/Steering-Vector-Transfer, programasweights org, ECNU-ICALK/HeteroFusion, MatteoCarrabba repos.

### Hugging Face API — 9
`models?author=RampPublic`, `datasets?author=RampPublic`, `models?search=` text-to-lora, hyperlora, lora-hypernetwork,
portal-lora, shine-lora, program-as-weights, fuzzybench. Cards read: RampPublic/portal-inkling, portal-mistral-7b,
portal-gemma-4-e2b; manihani4/portal-vlm-gemma3-lora-1k; programasweights/paw-4b-qwen3-0.6b, paw-4b-gpt2;
thinkingmachines/Inkling (README + config.json).

### Kevin's X bookmarks (`ft search`) — 17 valid
PorTAL, "portable LoRA", "hypernetwork LoRA", "LoRA transfer across models", "steering vector", "weight space", "model
merging", "SHINE hypernetwork", hypernetwork, Sakana, adapter, Ramp, Inkling, "task vector", LoRA, "Thinking Machines",
Tinker. (FTS syntax errors on: Text-to-LoRA, Program-as-Weights, Doc-to-LoRA, "fine-tune port", cross-model.) Relevant hits:
RampLabs 2072383318516187380, 2072383322940957115 (2026-07-01), 2081819550329327689 (2026-07-27); frank_ 2077804166966333455
(Inkling launch on Tinker, 2026-07-16). Full tweet text pulled via `api.fxtwitter.com`.

### WebSearch — 1 answered
`Ramp PorTAL portable task adaptation LoRA hypernetwork portallib`. Seven further queries were refused: the session's
WebSearch budget (200/200, shared across cells) was exhausted.

### Primary-source opens — ~55 (WebFetch on arXiv abs/HTML pages, Ramp blog ×2, GitHub READMEs/issues, HF cards, fxtwitter).

---

## 6. Coverage limits (honest)

- **WebSearch unavailable** after the first query (session cap 200/200 shared across cells). General-web and blog coverage
  after 2026-08-10 therefore rests on arXiv API, GitHub, Hugging Face, Kevin's bookmarks, and direct WebFetch of known URLs.
  Lab blogs other than Ramp's (e.g., Sakana, Thinking Machines) were not searched.
- **Jina reader blocked** for anonymous queries from this network (AS7018); WebFetch substituted.
- **arXiv API rate limiting (HTTP 429)** during the first parallel burst; all 30 listed queries succeeded after serializing
  with 6-s gaps, but several phrasing variants were not retried. Results capped at 30–40 newest per query.
- **Semantic Scholar heavily rate-limited**: 4 of 17 queries answered; citation-graph checks (who cites Cross-LoRA/T2L in
  2026) were not possible.
- **DuckDuckGo (CAPTCHA), Bing RSS (query mangling), Brave (JS-only)** were unusable as search fallbacks.
- **X/Twitter**: only Kevin's 2,038 bookmarks (synced 2026-09-01) plus two fxtwitter lookups; RampLabs' timeline after
  2026-07-27 was not enumerated.
- **Abstract-level only** (numbers unavailable without the PDF): HypeLoRA, Compliance2LoRA, ACTD, BiCo, WeightCLIP, Hyper-X,
  HYPEROFA, TiTok (headline only), Omni2LoRA backbones, MoEGen backbones, ALM. Full HTML was read for Theseus,
  Transport-and-Merge, Cross-Architecture Steering Transfer, UpgradeBench, hypernetwork scaling laws.
- **Not run**: any PorTAL code, portal-vlm eval, or UpgradeBench (code unreleased). No claim here is independently
  replicated by this cell.
- **Not searched**: OpenReview submissions, ACL Anthology, Papers with Code, non-English venues, Discord/Slack communities.
- **Venue labels** taken from the primary page; "PAW at AIware 2026" is the authors' statement on the HF card.
