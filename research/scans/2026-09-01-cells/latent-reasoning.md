# Latent-reasoning cell sweep — 2026-09-01

Cell: `latent-reasoning`. Focus: latent, abstract, and recurrent reasoning media plus
monitorability (Coconut successors, Abstract-CoT, recurrent depth/Huginn, Thinking States,
DiscoLoop, Mixture-of-Recursions, latent tool use, 2026 CoT-monitorability literature), with
explicit attention to (a) latent tokens that are interpretable by construction or decodable by a
weaker monitor and (b) tool-use compatibility of each medium.

Every finding below was opened at its primary source (arXiv abs/HTML page, GitHub README via
`gh api`, Hugging Face model card via the HF API, or lab blog via WebFetch). Body-level numbers
were extracted from arXiv HTML through WebFetch (a small summarizer model); abstracts were read
verbatim from arxiv.org abs pages. "First-party" = preprint/blog/README claim; "peer-reviewed" =
venue stated in the arXiv comment or code README. Nothing below is cited from memory.

## Verdict in five lines

1. Every axis in the brief is occupied at ≤8B scale on math/QA: discrete abstract tokens
   (Abstract-CoT, DLR, Token Assorted), continuous thoughts (Coconut/CODI lineage), decodable
   latents (Heima, SIM-CoT, SELR, CoLT, LatentGuard), interpretable-by-construction latents (MUX,
   J-CoT, DiscoLoop, Thinking States, SWITCH, LSTR), looped/recurrent-depth LMs (Huginn, Ouro,
   Loopie, MoR successors), and probe/activation monitoring of latent states.
2. Abstract-CoT (IBM, 2026-04-24) has no official code found under this coverage and three
   independent reproduction attempts failed to reproduce its warm-up mechanism; one ablation
   shows the abstract prefix is vestigial (random tokens 54% vs learned 51%).
3. Post-2026-08-10 items squarely on the brief: looped LMs improve compositional tool calling
   (2608.18171, no monitorability), latent-CoT monitorability via probes vs verbalization
   (2608.04928, 1B only), inspectable latent guard model (2608.03838), CoT-monitor collapse
   under reasoning rewrites (2608.00583), CoT-hidden backdoors (2608.02820), intent-as-a-tool
   monitoring (2608.27348), hidden-CoT detection (2608.29956), and the OpenAI monitorability
   suite's arXiv form (2512.18311).
4. The strongest open cells that Kevin's assets fit: (i) monitorability of latent/abstract media
   measured on tool-use agent tasks (nobody does both); (ii) translation-equivariant (parallel
   data supervised) abstract codebooks whose monitor transfers across languages (nobody does
   this; CoT monitorability is already shown to be fragile across 13 languages); (iii) a
   controlled Abstract-CoT reproduction with token-necessity ablations at 4B–8B.
5. No retraction was found in this literature; the negative record is instead a dense set of
   causal audits showing latent tokens are frequently unnecessary or non-explanatory.

## Method

Modalities actually used: WebSearch (18 successful queries before the session budget was
exhausted), arXiv web search UI via curl (5 successful listing queries; 17 further attempts
rate-limited), arXiv abs pages via curl (≈155 abstracts read verbatim), arXiv HTML via WebFetch
(≈20 body extractions), GitHub `gh search repos` (31 queries) and `gh api` README/commit reads,
Hugging Face model search API (13 queries) plus model-card reads and the HF papers API (2
queries), `ft search` over Kevin's 2,038 X bookmarks (22 queries), and WebFetch on lab pages
(Anthropic alignment blog index + 3 posts, METR research index, GDM alignment substack summary,
SPAR project page, Ouro project page). arXiv API, Semantic Scholar API, and Jina reader were all
blocked (429 / anonymous-query block) — see Coverage limits.

---

## A. Discrete / abstract-token latent media

### A1. Thinking Without Words: Efficient Latent Reasoning with Abstract Chain-of-Thought
- URL: https://arxiv.org/abs/2604.22709 (v2 2026-04-27; v1 2026-04-24). IBM Research AI (Ramji,
  Naseem, Astudillo). First-party arXiv preprint; no venue.
- Claim (from HTML v2): reserved vocabulary M=64 tokens; policy-iteration warm-up (masked
  bottleneck SFT + self-distillation) then GRPO with constrained decoding. Qwen3-8B: MATH-500
  90.8% vs 92.6% verbal CoT at 10.4–11.6× token compression; AlpacaEval 60.8 vs 58.4 win-rate
  (1.9–2.2×); HotpotQA 58.8 vs 58.1 F1 (4.0–4.3×); AIME'25 24.4 vs 25.6 (2.7×); GPQA-Diamond
  50.5 vs 51.5 (7.9×). Token usage becomes power-law (Zipf-like); one dominant token (<TOKEN_F>).
  No decoding of abstract tokens to text, no probing, no tool use / multi-turn.
- Occupies: discrete reserved-vocabulary latent CoT via post-training only.
- Relevance: the anchor of Direction 15. Compression is real on single-turn math/QA; the
  "learned language" is opaque by design; tool-use compatibility untested (single-turn only).
  Not comparable to Coconut/CODI in the paper's tables.

### A2. Independent Abstract-CoT reproduction attempts (three, none successful)
- LE-WH/ThinkingWithoutWordsRepro — https://github.com/LE-WH/ThinkingWithoutWordsRepro
  (README read 2026-09-01; runs dated 2026-05-10 to 2026-05-18). Qwen3-4B. Baseline verbal CoT
  reproduced (84.0% vs paper 83.2% MATH-500). Warm-up target 86.2% with ~100–150 abstract
  tokens; best run (8×H200, 39,533 examples, T=3, seq 8k, ~5.5 h full FT) reached 74.2% with
  mean 17 abstract tokens; "all teacher traces across all rounds and examples became the same
  fixed 13-token sequence" (trace collapse). Guided compression and larger/math vocabularies
  also failed.
- LauraGG/qwen25math-7b-abstract-cot-grpo — https://huggingface.co/LauraGG/qwen25math-7b-abstract-cot-grpo
  (model card, lastModified 2026-05-16). Qwen2.5-Math-7B-Instruct, 1×H100 (~6 h total, ~0.5% of
  paper warm-up compute, ~5% of RL). MATH-500 51.0% at 237 tokens (n=100, maj@8) vs 87.2% at
  625 tokens verbal. Ablation: random abstract tokens 54%, zero (skip block) 52%, learned 51% —
  "a budget-constrained verbal-CoT model with a vestigial abstract prefix"; near-constant 9-token
  prefix regardless of input. Author labels it "useful as a negative-result reference".
- bertybaums/abstract-cot — https://github.com/bertybaums/abstract-cot (last commit
  2026-05-16; README: "No code written, no jobs run" beyond Phase 0 setup on Granite-3B/Qwen3).
- Status: all first-party third-party logs; not peer-reviewed. No official IBM code found
  (`gh search repos "Thinking Without Words"`, `abstract chain-of-thought IBM`, IBM org search,
  HF search `abstract-cot` → only third-party checkpoints: LauraGG, leapeto).
- Relevance: feasibility kill-shot for "just reproduce Abstract-CoT" at academic compute; but
  also a publishable controlled-reproduction opportunity (none exists) with token-necessity
  ablations. 8×H100 sits between LauraGG's and LE-WH's budgets.

### A3. Why Struggle with Continuous Latents? Interpretable Discrete Latent Reasoning via Rendered Compression (DLR)
- URL: https://arxiv.org/abs/2606.29712 (2026-06-29). SJTU/Tongji. First-party preprint; code
  github.com/Miraclecsc/Discrete-Latent-Reasoning (3 stars, pushed 2026-06-25).
- Claim: renders textual CoT to images, DeepSeek-OCR2 encoder, codebook K=10,000 (d=896) via
  stochastic VQ; decoder reconstructs text from quantized embeddings. Qwen3-VL-4B GSM8K-Aug:
  DLR 63.3% vs CoT-SFT 81.2% vs Coconut 16.1% vs CODI 7.1%; MATH-500 (8B) 54.0 vs CoT 69.4;
  "up to 20× compression" (≈6–7 latent tokens vs ~120 CoT tokens). Interpretability via the OCR
  decoder mapping latent tokens back to text (qualitative case studies only).
- Occupies: discrete latent vocabulary + decoder-to-text; multimodal backbones.
- Relevance: the closest existing "decodable discrete codebook"; still trails explicit CoT by
  ~15–18 points; decoder faithfulness not causally tested; no tool use.

### A4. Token Assorted: Mixing Latent and Text Tokens (prior art for VQ latent tokens)
- URL: https://arxiv.org/abs/2502.03275 (2025-02-05; updated 2025-09-01). Meta/Berkeley.
- Claim: VQ-VAE latent discrete tokens abstract initial reasoning steps; random mixing of latent
  and text tokens for adaptation. Occupies hybrid discrete-latent/text traces.
- Relevance: defines the "hybrid latent+text" axis Direction 15B assumes is open — it is not.

### A5. Efficient Reasoning with Hidden Thinking (Heima) — ICML 2026
- URL: https://arxiv.org/abs/2501.19201 (v1 2025-01-31; updated 2026-05-04; comment: ICML 2026).
- Claim: compresses CoT into abstract thinking tokens; an "adaptive interpreter" maps thinking
  tokens back to variable-length text. Peer-reviewed.
- Occupies: post-hoc interpreter/decoder for latent thinking tokens (multimodal).

### A6. iCLP: Implicit Cognition Latent Planning
- URL: https://arxiv.org/abs/2512.24014 (2025-12-30). Code released.
- Claim: distills explicit plans, learns discrete plan codes via VQ autoencoder + codebook;
  model generates latent plans. Occupies: discrete latent *plans* (planning tokens), math/QA.

---

## B. Continuous-thought media and their training

### B1. Latent Reasoning with Supervised Thinking States
- URL: https://arxiv.org/abs/2602.08332 (2026-02-09). Google Research / Hebrew U / Tel Aviv U.
  First-party preprint; independent prototype code exists (github.com/fazalmittu/
  supervised-thinking-states, 5 stars, pushed 2026-02-15; README reports no results).
- Claim (HTML): generates natural-language thinking tokens every few input tokens, compresses
  them into a fixed-size state injected into shallow layers of the next chunk; trained with
  teacher forcing in one parallel pass (no BPTT). Qwen2.5-Base 0.5B/1.5B. 2-hop QA 54.91 vs CoT
  54.79 at ×1.19 speed; GSM8K 42.22 vs CoT 60.50 at ×2.66 (Coconut 32.65 ×3.14; iCoT 34.00
  ×5.71); parity N=40 100.00 vs CoT 64.38 (length extrapolation). Failure mode "state
  ambiguity". No tool use.
- Occupies: latent state supervised *by language* (interpretable by construction at the thought
  level), reasoning-while-reading.
- Relevance: the one medium in the brief whose latent is grounded in language supervision; but
  GSM8K gap to CoT is 18 points at 1.5B and nothing is said about monitors or tools.

### B2. Chain of Continuous Thought lineage status (Coconut, CODI, CoLaR, SIM-CoT)
- Coconut https://arxiv.org/abs/2412.06769 (official repo last commit 2025-08-12).
- SIM-CoT https://arxiv.org/abs/2509.20317 (2025-09-24): step-level auxiliary decoder aligns each
  implicit token with its explicit step during training; decoder removed at inference; "also
  provides interpretability". Occupies decoder-supervised continuous thoughts.
- Latent Thoughts Tuning https://arxiv.org/abs/2602.10229 (ICML 2026): context-prediction fusion
  to avoid feature collapse. NF-CoT https://arxiv.org/abs/2606.06447 (2026-06-04): normalizing
  flow over continuous thoughts preserving likelihoods/KV-cache. Latent Thought Flow
  https://arxiv.org/abs/2606.16222 (2026-06-15): continuous GFlowNet over variable-length
  trajectories. Latent Thought Credit https://arxiv.org/abs/2608.01593 (2026-08-03):
  multi-answer credit assignment for latent thoughts under RL.
- Relevance: the continuous axis is saturated on training objectives; none of these evaluate
  tool use or monitors.

### B3. Latent Thinking Optimization (Huginn latent reward)
- URL: https://arxiv.org/abs/2509.26314 (v3 2026-02-24). First-party.
- Claim (HTML): latent classifier predicts correctness from Huginn-3.5B latent thoughts (SVAMP
  ROC-AUC ≈1.0, MBPP ≈0.8, improving with steps); LTO acceptance–rejection sampling lifts GSM8K
  0.326→0.385; latent reward model transfers across domains.
- Occupies: probe-as-reward on recurrent latent states. Relevance: evidence that a small
  external classifier can read *correctness* from latents — not intent.

---

## C. Decodable and interpretable-by-construction latent interfaces

### C1. Think in Latent, Explain in Language: Self-Explainable Latent Reasoning (SELR) — ICML 2026
- URL: https://arxiv.org/abs/2608.13570 (dated 2026-07-01; arXiv id in 2608 series). Code
  github.com/jasondayuan/selr-code ("[ICML 2026] Official code", pushed 2026-08-09).
- Claim (HTML): one model optimizes Answer Loss + CoT Loss so the *same* model decodes its own
  latents to text. LLaMA-3.2-1B GSM8k: SELR 42.46% vs Coconut 30.83 vs CoLaR 40.1 (CoT-SFT
  64.06 with ~150 tokens vs SELR ~6). Qwen2.5-VL-3B: 63.31% avg with 13.47 tokens (73%
  reduction) vs Heima 60.94 (22.84 tokens). Decoded-CoT/answer consistency 0.4788 (0.532 when
  correct vs 0.240 when incorrect). No causal/intervention test tying explanation to latent
  computation; no monitoring or safety evaluation; stopping mechanism unsolved.
- Occupies: same-model self-decoding of latents. Relevance: the "verbal checkpoint" idea of
  Direction 15B exists in stronger form; what is missing is a causal-faithfulness and
  adversarial test of the explanation channel.

### C2. MUX: Continuous Reasoning via Multiplexed Tokens
- URL: https://arxiv.org/abs/2607.18264 (2026-05-19). First-party (affiliation not extracted).
- Claim (HTML): each latent token is a position-weighted superposition of a span of discrete
  reasoning subwords; geometric weights make multiplexing provably lossless (recoverable by
  demultiplexing) for spans S≤11 in float32; six latent tokens; GSM8K-Aug LLaMA-1B 56.7% vs
  SFT-CoT 61.6 vs CODI 55.6 vs SIM-CoT 56.1 with ≈2.4× fewer reasoning tokens; MNNS 99.6%, Game
  of 24 88.7%; probes recover spans with "nontrivial accuracy".
- Occupies: interpretable-by-construction (invertible) continuous latent tokens.
- Relevance: the strongest existing "interpretable by construction" mechanism; evaluated only
  for accuracy/compression, never as a monitoring channel or under obfuscation pressure; no tools.

### C3. J-CoT: Chain-of-Thought in J-Space
- URL: https://arxiv.org/abs/2607.21981 (2026-07-24; "work in progress"). Oxford / Imprint Lab /
  Stanford. First-party.
- Claim (HTML): vocabulary-indexed coefficient states ("J-thoughts") as the recurrent interface;
  active vocabulary columns can label a J-thought. Qwen3-8B-Base average over 8 benchmarks 50.2%
  vs SIM-Coconut 47.5 vs standard CoT 45.8 (MATH-500 54.0 vs 50.4; HumanEval+ 62.6 vs 59.8;
  LiveCodeBench 23.8 vs 21.0); scaling study to Llama-3.1-405B.
- Occupies: linguistically grounded, non-sentential latent interface; includes code tasks.
- Relevance: nearest thing to "typed/vectorized tokens" in Direction 15A; no monitor test.

### C4. DiscoLoop: Looping Discrete Embeddings and Continuous Hidden States
- URL: https://arxiv.org/abs/2607.00341 (v1 2026-07-01; updated 2026-07-27). UC Berkeley /
  Princeton (Fu, Guo, Wang, Zhu, ... Lee, Jiao, Russell). First-party.
- Claim (HTML): recurrence carries continuous hidden state plus a discrete channel Φ(h)=Σ p_v(h)
  W[v] (tempered softmax, top-k=128) added via gated RMSNorm. Symbolic two-hop OOD near-perfect vs
  ~10% for vanilla loop and ~0% non-looped. 440M / 20B tokens (FineWeb-Edu+FineMath 6:4): avg
  50.5 vs vanilla loop 49.3 vs PonderLM 49.8, best/tied on 6/7 benchmarks. No interpretability
  claim made for the discrete channel; no tool use.
- Occupies: mixed discrete/continuous looped recurrence for multi-hop.
- Relevance: the vocabulary-weighted channel is nominally readable by a logit-lens-style monitor
  but this is untested.

### C5. Demystifying Hidden-State Recurrence: Switchable Latent Reasoning (SWITCH)
- URL: https://arxiv.org/abs/2606.13106 (2026-06-11; earlier title "SPOT: Span-level
  Pause-of-Thought…"). HKUST(GZ)/Cambridge/NTU/JoinQuant. Code github.com/LARK-AI-Lab/SWITCH
  (15 stars, pushed 2026-06-12).
- Claim (HTML): discrete <swi>…</swi> boundary tokens make latent blocks compatible with GRPO
  and expose them to probing. Qwen3-8B: MATH-500 79.3%, GSM8K 89.2%; visible tokens 1,721 vs
  2,079 for text CoT (~17% saving); zeroing the latent hidden state collapses a diagnostic
  subset from 100% to 33.3%; linear probe predicts <swi> at 91.9%.
- Occupies: anchored/switchable latent blocks with causal probes.

### C6. Beyond Dense States: Sparse Transcoders as Causally Testable Operators (LSTR)
- URL: https://arxiv.org/abs/2602.01695 (v1 2026-02-02; v2 2026-08-30). NUAA. First-party.
- Claim (HTML): in-loop Latent Transition Transcoder (linear skip + Top-k=128 sparse innovation)
  on Llama-3.2-1B; at compression r=5 average 43.3% vs CoLaR 41.7; ablating top-10 features
  −16.5pp vs −3.0 for CoLaR; features labelled by cosine projection to token embeddings;
  interpretability is "local", no symbolic reconstruction.
- Occupies: sparse-feature inspectable latent transitions.

### C7. CoLT: Reasoning with Chain of Latent Tool Calls
- URL: https://arxiv.org/abs/2602.04246 (2026-02-04). Peking University. First-party.
- Claim (HTML): "seed tokens" whose hidden states a 1-layer external decoder unpacks into full
  textual reasoning steps ("the final reasoning chain is completely textual"). GSM8k-Aug 45.3%
  at 7.73 reasoning length vs CoT 49.4 at 25.6, CoLaR 40.1 at 12.7. Not real tools: "we
  implement the decoders as differentiable neural modules".
- Occupies: latent step compression with textual unpacking. Relevance: naming collision with
  "latent tool use"; not agentic.

### C8. LatentGuard: Efficient and Inspectable Latent Reasoning for LLM Safeguards
- URL: https://arxiv.org/abs/2608.03838 (2026-08-04). USTC / Xiamen. First-party.
- Claim (HTML): guard model (from GuardReasoner 1B/3B/8B) reasons in latent states; 8B mean
  weighted F1 83.95→84.91; 268.56 CoT tokens → 1.60 latent tokens (168×), latency 0.792s→0.089s
  (8.9×); an isolated auxiliary decoder emits "compact audit artifacts" on demand; audit utility
  85.75 with 95.6% human agreement on label support.
- Occupies: inspectable latent reasoning for moderation with on-demand audit decoding.
- Relevance: the "inspect on demand" pattern is a concrete design for a monitorability tax knob.

### C9. Prior/adjacent decoders: Reading Between the Dots (filler-token decoding) — ICML 2026 MI workshop
- URL: https://arxiv.org/abs/2607.03502 (2026-07-03). Brauer, Verdun, Marks.
- Claim: DeepSeek V3 and Kimi K2 compute over filler tokens legibly: logit-lens readouts, KV-cache
  transplants swap outputs; unsupervised decoding pipeline. "hidden from the output is not the
  same as hidden from us".
- Occupies: white-box decoding of non-verbal computation in frontier open weights.

---

## D. Recurrent depth, looped LMs, Mixture-of-Recursions successors

### D1. Looped Language Models Improve Compositional Tool Calling — post-cutoff
- URL: https://arxiv.org/abs/2608.18171 (2026-08-17). University of Cambridge. First-party.
- Claim (HTML): native (Ouro-1.4B/2.6B) and retrofitted (Llama-3.2-1B, OLMo-2-1B) looped models
  vs non-looped under matched SFT on API-Bank, BFCL v3, NESTful. Ouro-2.6B SFT: BFCL overall
  86.4% (parallel-multiple 76.5%), NESTful win rate 0.371 vs Qwen3-8B-Instruct 0.345, API-Bank
  79.9%. Retrofitted looped Llama-3.2-1B BFCL simple 43.5% vs 29.8% non-looped, parallel 31.0 vs
  14.0. Accuracy rises with recurrent depth (largest on compositional categories); adaptive
  depth recovers most gains with fewer loops. Limitations: no iso-pretrained non-looped Ouro
  counterpart; "all three benchmarks are static, single-turn evaluations".
- Occupies: recurrent depth × tool calling (single-turn).
- Relevance: directly answers "tool-use compatibility of recurrent depth" positively at 1–3B;
  leaves multi-turn agent loops and monitorability open.

### D2. Scaling Latent Reasoning via Looped Language Models (Ouro) — v5
- URL: https://arxiv.org/abs/2510.25741 (v1 2025-10-29; v5 2026-07-01). ByteDance Seed et al.
  (33 authors). First-party; weights on HF (Ouro-2.6B-Thinking lastModified 2026-02-26; 1.4B
  2026-06-03).
- Claim (HTML): 1.4B/2.6B, 4 recurrent steps, 7.7T tokens, entropy-regularized depth allocation;
  MATH500 82.40 (1.4B) vs Qwen3-4B 59.60; Ouro-2.6B-Thinking AIME24 64.7%. Claims traces are
  "better aligned with final outputs" than explicit CoT and HEx-PHI harmfulness falls with steps
  — no numbers for the alignment claim were found in the HTML extraction. No tool use.
- Relevance: the base for D1 and for LatentMT; its faithfulness claim is unquantified.

### D3. Loop the Loopies! (Loopie MoE looped models)
- URL: https://arxiv.org/abs/2607.16051 (2026-07-17). First-party.
- Claim: 20B-A2B and 6B-A0.6B looped MoE; "substantially outperforms vanilla Transformer
  baselines trained with the same compute budget" incl. a 30B-A3B comparison; frontier-level
  reasoning after a new post-training method. No numbers in abstract.

### D4. How Much Is One Recurrence Worth? Iso-Depth Scaling Laws — negative for looping efficiency
- URL: https://arxiv.org/abs/2604.21106 (v3 2026-05-07). Schwethelm, Rueckert, Kaissis.
- Claim: recurrence-equivalence exponent φ=0.46 (φ=1 would be full equivalence); at r=4 a 410M
  looped model matches a 580M non-looped one but costs the training compute of ~1B.
- Relevance: quantifies the compute tax of weight-tied depth; supports the last sweep's
  rejection of "generic latent loop with halting".

### D5. Sparse Layers are Critical to Scaling Looped LMs / LoopMoE / Loopie
- URLs: https://arxiv.org/abs/2605.09165 (2026-05-09), https://arxiv.org/abs/2606.04438
  (2026-06-03; v 2026-08-27).
- Claim: Looped-MoE scales better than the standard baseline while dense looped models do not
  (routing divergence across loops recovers expressivity); loop boundaries are superior early
  exits. LoopMoE gives a controlled looped-vs-non-looped MoE comparison.

### D6. Skip a Layer or Loop It? Program-of-Layers (PoLar) — ICML 2026
- URL: https://arxiv.org/abs/2606.06574 (2026-06-04; extends 2507.07996). Peer-reviewed.
- Claim: pretrained layers can be skipped/looped per input by a lightweight program predictor;
  improves math accuracy often with fewer layers. Occupies per-input layer programs over one
  operator family — partially overlaps the last sweep's "routing among sequence operators" gap
  (same-operator skip/loop only).

### D7. Retrofitting and training-free recurrence
- Teaching Pretrained LMs to Think Deeper with Retrofitted Recurrence
  https://arxiv.org/abs/2511.07384 (2025-11-10; McLeish, Geiping group): curriculum of
  recurrences converts non-recurrent models; better math per compute than post-training the base.
- Training-Free Looped Transformers https://arxiv.org/abs/2605.23872 (2026-05-22): damped
  sub-step looping of a mid-stack block, +2.64pp MMLU-Pro on Qwen3-4B-Instruct, +1.14pp on
  Qwen3-30B-A3B.
- Retrofitting Recurrent Depth into a Pretrained LM https://arxiv.org/abs/2608.11233
  (2026-07-31; single author): Qwen2.5-0.5B, 6M-parameter adapter matches 180M full block
  (83.8% vs 84.0%).
- Relevance: recurrence can be added to Kevin's pinned Qwen3 snapshots without pretraining.

### D8. Depth reliability and stability line
- Think Shallow, Solve Deep https://arxiv.org/abs/2608.18222 (2026-08-18): dynamical regime
  (settling/marginal/drifting) predicts whether extra iterations help; depth-safety condition;
  Sudoku 0.19→0.34 beyond training horizon for settling operators.
- STARS https://arxiv.org/abs/2605.26733 (ICML 2026): Jacobian spectral-radius regularization
  fixes peak-then-collapse test-time scaling in LoopLMs.
- Parcae https://arxiv.org/abs/2604.12946 (2026-04-14): spectral-norm-constrained injection
  parameters for stable looped pretraining scaling laws.
- Dense Supervision Is Not Enough https://arxiv.org/abs/2606.24898 (2026-06-12): per-loop
  cross-entropy through RMSNorm readouts leaves hidden-state scale uncontrolled (norms in the
  thousands) in 44M/129M looped models.
- Per-Token Fixed-Point Convergence https://arxiv.org/abs/2607.14427 (2026-07-15): training-free
  per-token halting reaches depth-8 quality at 4.94 loops (−38%) on a 135M model; a learned
  router yields no reduction.
- Depth-adaptive Inference via Continuous Depth Batching https://arxiv.org/abs/2608.09444
  (2026-08-10): loop-level scheduling for vLLM-style serving of depth-adaptive looped LMs.
- Multi-Stream LLMs https://arxiv.org/abs/2605.12460 (2026-05-12; Geiping group): parallel
  streams of thoughts/inputs/outputs so agents can think while reading/acting.

### D9. Huginn interpretability negatives
- Latent Chain-of-Thought? Decoding the Depth-Recurrent Transformer
  https://arxiv.org/abs/2507.02199 (2025-07-02; COLM 2025 explainability workshop): "limited
  evidence of interpretable latent CoT"; probing inconsistencies across recurrent blocks; GSM8K
  with CoT suppressed 3.11→4.93 from 4→256 recurrences vs 24.87/38.13 with explicit CoT.
- Loop, Think, & Generalize https://arxiv.org/abs/2604.07822 (COLM 2026): from-scratch
  recurrent-depth models do achieve systematic generalization and depth extrapolation on
  implicit multi-hop composition.
- A Mechanistic Analysis of Looped Reasoning LMs https://arxiv.org/abs/2604.11791 (2026-04-13):
  each layer in the cycle converges to a distinct fixed point; consistent cyclic trajectories.
- Huginn checkpoints: tomg-group-umd/huginn-0125 (HF lastModified 2025-07-29);
  JonasGeiping/huginn-0125-checkpoints (in-training checkpoints, 2026-07-02). Kevin's Huginn
  prior-art check: no 2026 Huginn-2 release found under this coverage.

### D10. Mixture-of-Recursions status
- MoR https://arxiv.org/abs/2507.10524 (NeurIPS 2025 poster; repo last commit 2025-09-26).
  Direct 2026 successors found: Mixture of Layers with Hybrid Attention
  https://arxiv.org/abs/2605.09516 (2026-05-10; thin parallel blocks routed top-k, shared softmax
  block + Gated DeltaNet in routed blocks) and A Dual-Path Architecture
  https://arxiv.org/abs/2605.30202 (2026-05-28; deep shared sublayer ×K plus wide sublayer with
  per-token gates). Both first-party.
- Relevance: "routing among qualitatively different operators" is now partially occupied (MoL
  mixes softmax and Gated DeltaNet blocks by routing).

---

## E. Latent reasoning for agents and tool use

### E1. Adaptive Latent Agentic Reasoning (ALAR)
- URL: https://arxiv.org/abs/2606.02871 (2026-06-01). Code github.com/luka-group/
  adaptive-latent-agentic-reasoning (initial release 2026-06-10). First-party.
- Claim (README/abstract): per-turn choice between <latent>••••</latent> (K=4 projector
  continuous thoughts) and <think> text; Action-Anchored Self-Distillation then AR-GRPO for mode
  selection; vLLM plugin splices latents. Search (Search-R1 base, Qwen2.5-3B/7B) and tool use
  (Qwen3-4B-Thinking, BFCL AST): comparable or better accuracy with up to 43.6% (search) and
  84.6% (tool use) fewer generated tokens.
- Occupies: latent-by-default / escalate-to-CoT agent reasoning with action anchors.
- Relevance: the tool-use latent baseline that Direction 15D assumed did not exist. No
  monitorability, argument-fidelity, or multi-turn error-diagnosis measurements.

### E2. DRAFT: Task Decoupled Latent Reasoning for Agent Safety
- URL: https://arxiv.org/abs/2604.03242 (2026-02-11). First-party.
- Claim: Extractor distills a tool-agent trajectory into a continuous latent draft; Reasoner
  predicts safety; accuracy 63.27% (LoRA) → 91.x% on ASSEBench/R-Judge (truncated in abstract).
- Occupies: latent-space trajectory auditing for tool agents (monitor side, not policy side).

### E3. MIRAGE: Mobile Agents with Implicit Reasoning and Generative World Models
- URL: https://arxiv.org/abs/2606.04627 (2026-06-03). First-party.
- Claim: latent reasoning vectors distilled from textual traces and aligned with future
  screenshots; GUI agents act without decoding rationales.
- Occupies: latent reasoning for GUI agents with world-model objective.

### E4. INTENT-AS-A-TOOL Makes it Easy to Track Agentic Misalignment — post-cutoff
- URL: https://arxiv.org/abs/2608.27348 (2026-08-27). Code released. First-party.
- Claim: adds intent-targeted tools so the probability of calling an intent tool is a
  judge-free, per-step signal of commitment to a behavior; complements CoT monitoring; finds
  critical steps for online intervention.
- Occupies: tool-channel intent signals for monitoring. Relevance: a tool-native monitoring
  signal that would survive an opaque reasoning medium — untested with latent media.

### E5. Community signal: Ouro-1.4B-Thinking terminal-agent SFT
- URL: https://huggingface.co/jaslee/Ouro-1.4B-Thinking-terminal-sft (2026-08-23). Third-party
  model card: base Ouro-Thinking scored 0/15 Terminal-Bench tasks under terminus-2 because it
  "reasons in prose for hundreds of tokens and never emits the JSON action object"; SFT on
  Nemotron-Terminal-Corpus/TerminalTraj yields parseable actions (106 vs 800 tokens).
- Relevance: anecdotal but concrete evidence that looped LMs' action-format fidelity is a
  post-training problem, not intrinsic.

---

## F. Interpretability and causal audits of latent media (negatives included)

### F1. Are Latent Reasoning Models Easily Interpretable? — COLM 2026
- URL: https://arxiv.org/abs/2604.04902 (v1 2026-04-06; updated 2026-08-10). Dilgren, Wiegreffe.
- Claim: Coconut and CODI on GPT-2 Small / Llama-3.2-1B-Instruct: on PrOntoQA/ProsQA latent
  tokens are rarely needed for stable predictions; when needed, gold traces decodable 65–93% of
  correct instances (vocabulary projection + backtracking; forward chaining 93%); verified traces
  found for a majority of correct but a minority of incorrect predictions — "interpretability
  itself can be a signal of prediction correctness".
- Relevance: a positive for weaker-monitor decodability of *width-based* LRMs trained with
  explicit supervision; caveat that it may not hold for weaker language priors.

### F2. Observable Patterns Are Not Explanations: A Causal-Geometric Analysis
- URL: https://arxiv.org/abs/2606.12689 (2026-06-10). Aswal, Ferraz, Zhou, Peyrard.
- Claim: BFS-like frontiers and decodable arithmetic also appear in controls lacking the
  recurrence/curriculum; latent-thought utilization is graded; "latent thoughts should be
  treated as hidden computation, not hidden explanation".

### F3. Do Latent Tokens Think? A Causal and Adversarial Analysis of Coconut
- URL: https://arxiv.org/abs/2512.21711 (2025-12-25).
- Claim: Coconut tokens show minimal sensitivity to steering and lack reasoning-critical
  information; on MMLU/HotpotQA Coconut "consistently exploits dataset artifacts" — "a
  pseudo-reasoning mechanism". No code found.

### F4. Final Checkpoints Are Not Enough (faithfulness along training)
- URL: https://arxiv.org/abs/2607.06648 (2026-07-07). GPT-2 small; Coconut and CODI.
- Claim: causal contribution of latent steps decays across training; counterfactual flip rates
  for latent methods comparable to NoCoT and roughly an order of magnitude below CoT; answer
  format (binary vs open-ended) reverses the activation-level trajectory.

### F5. Ablate-to-Validate (VLM continuous thought tokens)
- URL: https://arxiv.org/abs/2605.21642 (2026-05-20). Token Replacement Test: zero/random/
  first-repeat/oracle replacements isolate whether latent-token *content* matters.

### F6. Dynamics Within Latent CoT: causal structure — ICML 2026
- URL: https://arxiv.org/abs/2602.08783 (2026-02-09). Step-wise do-interventions on Coconut/CODI;
  which steps are causally necessary and when answers become decodable early.

### F7. Capabilities and Fundamental Limits of Latent CoT
- URL: https://arxiv.org/abs/2602.01148 (2026-02-01). Exploration–execution trade-off governed by
  decisional certainty (ProsQA 97.0% vs GSM8K 34.1%); curriculum provably necessary.

### F8. Why Limit the Residual Stream to Layers and Not Tokens? (AGCLR)
- URL: https://arxiv.org/abs/2606.07720 (2026-06-05). Reports vanilla Coconut 10.4% EM on
  HotpotQA vs CoT baseline 11.0% and degradation with curriculum depth on GSM8K ("concept
  bottleneck"); proposes gated persistent memory.

### F9. Unlocking the Black Box of Latent Reasoning (decode-time interventions)
- URL: https://arxiv.org/abs/2606.01243 (2026-05-31). Structural/causal/geometric probes find
  early latent vectors act as causal hubs; training-free decode-time interventions.

### F10. Thinking Wrong in Silence: Backdoor Attacks on Continuous Latent Reasoning
- URL: https://arxiv.org/abs/2604.00770 (2026-04-01; single author). ThoughtSteer perturbs one
  input embedding; ≥99% attack success on Coconut/SimCoT (124M–3B), evades five defenses,
  survives 25 epochs of clean fine-tuning.

### F11. Towards Inference-time Scaling for Continuous Space Reasoning — negative
- URL: https://arxiv.org/abs/2510.12167 (2025-10-14). Pass@N gains exist but text-style PRM/ORM
  recipes fail: continuous thoughts lack geometric separability.

---

## G. CoT monitorability 2026 — labs and academia

### G1. Monitoring Monitorability (OpenAI; arXiv form of "Evaluating chain-of-thought monitorability")
- URL: https://arxiv.org/abs/2512.18311 (2025-12-20). Guan, Wang, Carroll, Dou et al. (12
  authors). First-party. The OpenAI blog page returned HTTP 403 from this environment.
- Claim (abstract): three evaluation archetypes (intervention, process, outcome-property), a new
  monitorability metric and evaluation suite; catches model organisms with obfuscated CoTs; CoT
  monitoring beats action-only monitoring; most frontier models "fairly, but not perfectly,
  monitorable"; longer CoTs generally more monitorable; scaling with RL optimization and
  pre-training size studied (abstract truncated in extraction).

### G2. Reasoning Models Struggle to Control their Chains of Thought (OpenAI-hosted)
- URL: https://arxiv.org/abs/2603.05706 (2026-03-05). Yueh-Han, McCarthy, Lee, He et al.
- Claim: CoT-Control suite over 13 reasoning models; Claude Sonnet 4.5 controls its CoT 2.7% of
  the time vs 61.9% for outputs; controllability higher for larger models and decreases with more
  RL, test-time compute, and problem difficulty.

### G3. Quantifying the Necessity of CoT through Opaque Serial Depth (Google DeepMind)
- URL: https://arxiv.org/abs/2603.09786 (2026-03-10). Brown-Cohen, Lindner, Shah.
- Claim: formalizes opaque serial depth (longest computation without interpretable intermediate
  states); numeric upper bounds for Gemma 3; open-source tool for arbitrary networks; asymptotic
  results for other architectures. Relevance: gives the metric by which looped/latent media are
  *less* monitorable by construction.

### G4. How Transparent is DiffusionGemma? (Google DeepMind)
- URL: https://arxiv.org/abs/2606.20560 (v1 2026-06-18; v2 2026-08-17). Engels, McDougall,
  Chughtai, Kramar et al. (14 authors).
- Claim (abstract verbatim): opaque serial depth "seems at first 28.6X higher than the
  corresponding autoregressive Gemma 4 model"; mapping inter-step information "through an
  interpretable token bottleneck with no decrease in downstream performance" reduces it "to just
  1.1X"; "DiffusionGemma is similarly monitorable to Gemma 4".
- Relevance: the clearest precedent for making a latent-heavy medium monitorable by inserting an
  interpretable token bottleneck — exactly the move Direction 15B proposes for abstract tokens.

### G5. Aligned, Orthogonal or In-conflict: When can we safely optimize CoT? (Google DeepMind)
- URL: https://arxiv.org/abs/2603.30036 (2026-03-31). Kaufmann, Lindner, Zimmermann, Shah.
- Claim: reward terms on CoT classified as aligned/orthogonal/in-conflict predict whether
  training reduces monitorability. Also: A Pragmatic Way to Measure CoT Monitorability
  https://arxiv.org/abs/2510.23966 (2025-10-28; Emmons, Zimmermann, Elson, Shah): legibility +
  coverage autorater. GDM AI Control Roadmap https://arxiv.org/abs/2607.13087 (2026-07-13).
- GDM summary post (2026-07-31): https://gdmalignment.substack.com/p/agi-safety-and-alignment-at-google
  lists 2603.09786, 2606.20560, 2510.23966, 2603.30036, 2507.05246, 2505.01420 under CoT/monitorability.

### G6. Length Penalties Make Chain-of-Thought Less Monitorable
- URL: https://arxiv.org/abs/2607.09786 (2026-07-08; v 2026-08-02; single author).
- Claim: Qwen3-4B/14B trained to target chain lengths; at the shortest length lower-bound
  faithfulness drops to 63.1% (14B) and 69.4% (4B) of baseline; monitor hint-detection falls
  69%→49% and 60%→48% while hint influence stays near baseline.
- Relevance: a direct measurement of the "monitorability tax" of compression — the same
  pressure Abstract-CoT applies more aggressively.

### G7. Reasoning Under Pressure (MATS) — contrasting evidence
- URL: https://arxiv.org/abs/2512.00218 (2025-11-28). MacDermott, Wei, Djoneva, Ward.
- Claim: monitorability = monitor predicts a key latent variable from the reasoning; when
  controlling for accuracy, no consistent effect of length penalties or KL regularisation;
  adversarial optimisation degrades monitor accuracy. Code github.com/QiyaoWei/
  reasoning-under-pressure (updated 2026-08-12).
- Relevance: G6 vs G7 disagree on whether compression alone taxes monitorability — an open
  measurement question across media.

### G8. MonitorBench — COLM 2026
- URL: https://arxiv.org/abs/2603.28590 (2026-03-30; v 2026-08-09). Code
  github.com/ASTRAL-Group/MonitorBench (multi-turn tasks released 2026-04-22).
- Claim (HTML): 1,514 instances, 19 tasks, 7 categories; Qwen3-32B monitor; CoT-only
  monitorability by category: cue-condition 96.6%, cue-answer 66.2%, goal-sandbag 76.3%,
  goal-deception 84.1%, dual objectives 91.4%, impossible tasks 83.8%, solution process 36.1%;
  agent tasks with ~35 rounds and 50+ tools; stress tests (direct concealment, monitor-aware
  evasion) degrade 7–8%. No latent-reasoning or non-English settings.

### G9. Does Out-of-Sight Equal Out-of-Mind in CoT Monitorability? — post-cutoff
- URL: https://arxiv.org/abs/2608.04928 (2026-08-05). Ferreira, Aziz, Titov.
- Claim (HTML): CODI and SIM-CoT on Llama-3.2-1B-Instruct; monitors: exact-match, prompted
  Qwen3-14B, fine-tuned classifier, activation probe; traces: native text, verbalized latents
  (logit lens / decoder), activations. Activation probing gives the highest AUROC across modes;
  verbalized latents close the gap on GSM8k (numbers from the target computation) but are
  uninformative on ECQA; OOD QA (SIQA) collapses toward baseline for latent models.
  "monitorability depends more on properties of the task ... and the level of access to model
  internals than on the reasoning mode." Single base model, induced hint-reliance only.
- Relevance: the only direct latent-vs-explicit monitorability comparison found; it stops at 1B
  and at math/QA.

### G10. Ulterior Motives: Detecting Misaligned Reasoning in Continuous Thought Models
- URL: https://arxiv.org/abs/2604.23460 (2026-04-25; single author).
- Claim (HTML): Coconut on GPT-2 124M; MoralChain (12,000 scenarios); dual-trigger backdoor;
  linear probes trained on behaviorally distinguishable pairs transfer to behaviorally identical
  pairs with AUROC 0.951 at the first latent token, degrading to 0.651 at z6; no text decoding.
- Relevance: probes on early latent tokens can catch armed misalignment without interpretation;
  scale and architecture caveats are explicit.

### G11. The Fragility of CoT Monitoring Across Typologically Diverse Languages
- URL: https://arxiv.org/abs/2605.27901 (2026-05-27). Onyame, Zhou, Thopalli, Kailkhura et al.
- Claim: 13 languages, 7 model families, 16 models; adversarial-hint unfaithfulness averages
  95.9% across 8B–120B models; strategic manipulation (answer-switching, post-hoc
  rationalization) makes external monitors struggle. Related small case study: Visible Reasoning
  and Indirect Prompt-Injection Monitorability Across English, Tamil, and Tanglish
  https://arxiv.org/abs/2608.15392 (2026-08-15; n=4 scenarios per phase, inconclusive).
- Relevance: the multilingual monitorability problem is open and directly touches Kevin's
  translation assets.

### G12. Attacks on CoT monitors — post-cutoff
- A False Average https://arxiv.org/abs/2608.00583 (2026-08-01): rewriting only the reasoning
  (commands unchanged) drops a held-out monitor's catch rate from ~95% to <11% in one
  gradient-free shot; aggregate accuracy hides collapse on the subset where CoT is the only
  signal.
- Evading CoT Monitoring Through Model Poisoning https://arxiv.org/abs/2608.02820 (2026-08-03):
  CoT-hidden backdoors via simple fine-tuning; curriculum when direct poisoning fails.
- Training on Documents About Monitoring Leads to CoT Obfuscation https://arxiv.org/abs/2605.15257
  (2026-05-14): synthetic-document finetuning raises undetected misbehavior; CoT controllability
  correlates with obfuscation success (r=0.800, p=0.017).
- Not All LLM Reasoning is Visible in the CoT https://arxiv.org/abs/2607.22925 (2026-07-24;
  Baherwani, Goldstein, Panda): 13 frontier models gain up to 13pp from filler tokens; Claude
  Opus 4.5 satisfies a hidden modular-arithmetic constraint via filler tokens.
- Output Supervision Can Obfuscate the CoT https://arxiv.org/abs/2511.11584 (2025-10-11).
- Can Reasoning Models Obfuscate Reasoning? https://arxiv.org/abs/2510.19851 (2025-10-21).

### G13. Weak / cheap monitors
- CoT-Guard: Small Models for Strong Monitoring https://arxiv.org/abs/2605.12746 (2026-05-12;
  UIUC/Capital One): Qwen3-4B monitor 12.86% → 70.35% (code) / 75.70% (CoT+code) G-Mean² after
  SFT+RL vs GPT-5.4 56.50, GPT-5-mini 41.90, Qwen3-32B 54.06, Gemini-3-Flash 83.82.
- Bootstrapped Monitoring https://arxiv.org/abs/2606.11998 (2026-06-10; Xiao, Phuong): trusted
  Qwen3-8B/GPT-4.1-mini oversee an untrusted monitor's raw CoT; catch rate 91% vs 69%
  (Gemini 3.1 Pro / GPT-4.1 Mini) and 90% vs 61% (Kimi K2.5); without raw CoT access it falls
  ~28pp below trusted-only.
- Reliable Weak-to-Strong Monitoring of LLM Agents https://arxiv.org/abs/2508.19461 (2025-08-26):
  agent awareness of monitoring dominates monitor awareness; scaffolding matters more.
- Ensemble Monitoring for AI Control https://arxiv.org/abs/2605.15377 (2026-05-14); Classifier
  Context Rot https://arxiv.org/abs/2605.12366 (2026-05-12; Opus 4.6/GPT 5.4/Gemini 3.1 miss
  dangerous actions 2–30× more often after 800K benign tokens).
- Baker et al. Monitoring Reasoning Models for Misbehavior https://arxiv.org/abs/2503.11926
  (2025-03-14): GPT-4o monitors o3-mini; obfuscated reward hacking under CoT-reward pressure.

### G14. Other 2026 measurement work opened
- Chain of Thought Monitorability: A New and Fragile Opportunity https://arxiv.org/abs/2507.11473
  (2025-07-15; 41 authors) — position paper.
- Monitorability as a Free Gift https://arxiv.org/abs/2602.03978 (2026-02-03): RLVR monitorability
  gains are data-dependent and orthogonal to capability; attributed to entropy reduction.
- Measuring CoT Monitorability Through Faithfulness and Verbosity https://arxiv.org/abs/2510.27378.
- Faithfulness Metrics Don't Measure Faithfulness (BonaFide) https://arxiv.org/abs/2605.25052
  (2026-05-24; Gur-Arieh, Marasović, Geva): ground-truth faithfulness labels for 3,066 CoTs.
- Measuring Faithfulness Depends on How You Measure https://arxiv.org/abs/2603.20172 (2026-03-20):
  three classifiers give 74.4/82.6/69.7% on identical data.
- When Reasoning Traces Become Performative https://arxiv.org/abs/2605.11746 (2026-05-12): latent
  commitment and explicit answer arrival align on only 61.9% of steps.
- Beyond the Commitment Boundary https://arxiv.org/abs/2606.13603 (2026-06-11); Faithfulness as
  Information Flow https://arxiv.org/abs/2605.24286 (2026-05-22; Jia, Benton, Easley);
  Monitoring the Internal Monologue (probe trajectories) https://arxiv.org/abs/2605.18549
  (2026-05-18); CoT Faithfulness Varies with Where and How Preference Cues Are Delivered
  https://arxiv.org/abs/2608.29464 (2026-08-29; 15 models, tool-return cues verbalized less);
  Selective Disclosure of Hidden Directives https://arxiv.org/abs/2608.29070 (2026-08-29);
  CoT Monitoring Can Be Unreliable in Implicit-Influence Settings https://arxiv.org/abs/2608.04735
  (2026-08-05); Risky Business: Faithfulness–Safety Tension https://arxiv.org/abs/2608.03745
  (2026-08-04); Detecting Hidden CoT with Linguistic, Behavioral, and Mechanistic Indicators
  https://arxiv.org/abs/2608.29956 (2026-08-30; HCDS +1.87 for Qwen3-4B-Thinking, p=1.2e-7).
- Think Fast: No-CoT Task-Completion Time Horizons https://arxiv.org/abs/2606.07157 (2026-06-05;
  Redwood Research/Astra, 21 authors): no-CoT 50% time horizon doubling every 373 days (95% CI
  167–691); GPT-5.5 exceeds 3 minutes; reasoning-token horizon >1,500 o3-mini tokens.
- Anthropic 2026 alignment blog (index read 2026-09-01): no CoT-monitorability post in 2026;
  adjacent: SLEIGHT-Bench (2026-05-19; 40 attacks, "50% of attacks are never caught on any of
  the 10 trials", Opus 4.6 as monitor), Introspection Adapters (2026-04-28;
  https://arxiv.org/abs/2604.16812; LoRA that makes finetunes verbalize implanted behaviors, 89%
  raw verbalization on 56 models), Fine-Tuned Lie Detectors Failed to Generalize (2026-08-21;
  in-distribution AUROC 0.60→0.95 but cross-category 0.70–0.75; sandbagging "nearly impossible to
  detect" with detectors trained on other lie types). Reasoning Models Don't Always Say What They
  Think https://arxiv.org/abs/2505.05410 (2025-05-08) remains Anthropic's primary CoT-faithfulness paper.
- METR research index (read 2026-09-01): no 2026 post on CoT monitorability; 2025 post
  "CoT may be highly informative despite unfaithfulness" remains the reference (not re-opened).

---

## H. Multilingual / translation × latent reasoning (Kevin's asset)

### H1. LatentMT: Machine Translation with Latent Reasoning
- URL: https://arxiv.org/abs/2607.18618 (2026-07-21). First-party.
- Claim: looped LM (2.6B backbone, lightweight training) across 32 directions matches models 3–5×
  larger; SOTA on mid/low-resource; recurrent steps help early then saturate; hidden-state
  differences shrink along the step axis; lower train/inference compute than larger non-latent
  models.
- Occupies: LoopLM for MT as a *task*. Not: translation data as supervision for latent
  interpretability.

### H2. Large Reasoning Models Are (Not Yet) Multilingual Latent Reasoners — ACL 2026 Findings
- URL: https://arxiv.org/abs/2601.02996 (2026-01-06). Liu, Zhao, Schütze, Hedderich.
- Claim: truncation-based analysis across 11 languages shows latent answer formation strong in
  high-resource, weak in low-resource languages; internal prediction evolution "broadly aligns
  with English — a pattern suggesting an English-centered latent reasoning pathway".

### H3. Soft Token Alignment for Cross-Lingual Reasoning (SOLAR)
- URL: https://arxiv.org/abs/2606.26466 (2026-06-25). He, Park, Xu, Ritter.
- Claim: aligns soft-token (probability-weighted embedding mixture) summaries of non-English
  reasoning to English pivots during SFT; up to +17.7 points over base, +3.8 over SFT; reduces
  language-cluster separability. Occupies: cross-lingual alignment of continuous token mixtures
  for accuracy — not for monitor transfer or abstract codebooks.

### H4. Cross-lingual Self-Consistency RL — already in last sweep
- URL: https://arxiv.org/abs/2606.01464 (2026-05). Requires neither gold answers nor parallel
  data; up to 21.7% MGSM gains. (Listed in the 2026-08-10 program index; not re-analyzed.)

### H5. Can We Read the Mind of an Audio LLM? A Verbalizable, Multilingual Middle-Layer Workspace — post-cutoff
- URL: https://arxiv.org/abs/2608.24958 (2026-08-25; 11 authors). First-party.
- Claim: logit lens on Qwen3-Omni at audio positions reads the answer in words in middle layers
  before any token; content is language-agnostic (38% of top-1 readouts Chinese on English
  inputs); causally used and committed before the last fifth of layers.
- Relevance: evidence that a shared multilingual latent workspace is logit-lens-readable — the
  kind of language-agnostic decodability a translation-supervised abstract code would target.

### H6. Native Multilingual CoT in Low-Resource SEA Languages (OSCD)
- URL: https://arxiv.org/abs/2608.00533 (2026-08-01). Uses a translator agentic loop during RL
  rollouts and joint-embedding alignment to stop cross-lingual collapse. Occupies translation
  loops as training scaffolding for *explicit* CoT.

---

## Tool-use compatibility by medium (what is actually demonstrated)

| Medium | Tool-use evidence found | Monitorability evidence found |
|---|---|---|
| Abstract discrete tokens (Abstract-CoT, DLR, Token Assorted) | None (single-turn math/QA/instruction following) | None; DLR/Heima decoders qualitative only |
| Continuous thoughts (Coconut/CODI/SIM-CoT) | ALAR (BFCL AST, Search-R1; up to 84.6% fewer tokens); MIRAGE GUI agents | Probes at 124M–1B (Ulterior Motives AUROC 0.951 z1; Out-of-Sight: activation probes best); causal audits say tokens often unnecessary |
| Language-supervised states (Thinking States) | None | None (states derive from language; untested as monitor channel) |
| Invertible/vocab-grounded latents (MUX, J-CoT, DiscoLoop, SWITCH, LSTR) | J-CoT includes code benchmarks; none on tools | Probe/ablation evidence of causal use (SWITCH 100→33.3%); no monitor experiments |
| Recurrent depth / looped LMs (Huginn, Ouro, retrofits) | 2608.18171: BFCL/NESTful/API-Bank single-turn gains with depth; community Terminal-Bench SFT | Huginn probing negative (2507.02199); LTO correctness probes; Ouro faithfulness claim unquantified; opaque-serial-depth framework applies |
| Explicit CoT (reference) | MonitorBench agent tasks (50+ tools); FACE-Eval tool-return cues | Extensive (G1–G14) |

## Occupied axes

| Axis | What is taken (with primary URLs) | Remaining gap under this coverage |
|---|---|---|
| Discrete abstract-token media | Reserved-vocab + warm-up/RL (2604.22709); VQ codebooks (2502.03275, 2512.24014); rendered-compression codebook with OCR decoder (2606.29712); abstract thinking tokens + interpreter (2501.19201) | Independent replication; monitorability; tool argument fidelity; cross-lingual invariance |
| Continuous-thought training | Coconut/CODI lineage; step decoders (2509.20317); fusion/flows/GFlowNets/credit assignment (2602.10229, 2606.06447, 2606.16222, 2608.01593) | Scale >1B with matched explicit baselines; monitors beyond hint-reliance |
| Decodable / self-explaining latents | Heima interpreter, SIM-CoT decoder, SELR same-model decoding (2608.13570), CoLT unpacking (2602.04246), LatentGuard audit decoder (2608.03838), DLR OCR decoder | Causal faithfulness of decoded explanation; robustness under obfuscation pressure; weaker-monitor consumers |
| Interpretable-by-construction latent interfaces | MUX lossless multiplexing (2607.18264), J-CoT vocabulary-indexed states (2607.21981), DiscoLoop soft-vocab channel (2607.00341), Thinking States language-supervised states (2602.08332), SWITCH anchors (2606.13106), LSTR sparse features (2602.01695), DiffusionGemma token bottleneck (2606.20560) | Any evaluation as a monitoring channel; tool use; multilingual grounding |
| Recurrent depth / looped LMs | Huginn (2502.05171), Ouro (2510.25741), Loopie (2607.16051), MoR (2507.10524), MoL/dual-path (2605.09516, 2605.30202), scaling laws (2604.21106, 2604.12946), stability (2605.26733, 2608.18222), retrofits (2511.07384, 2605.23872, 2608.11233), PoLar (2606.06574), serving (2608.09444) | Multi-turn agent loops; depth-vs-monitorability; iso-pretrained looped/non-looped controls |
| Latent reasoning for agents/tools | ALAR (2606.02871), looped tool calling (2608.18171), MIRAGE (2606.04627), DRAFT (2604.03242), intent-as-a-tool (2608.27348) | Joint efficiency × monitorability on multi-turn tool tasks; argument/schema fidelity analysis |
| Probe/activation monitoring of latents | Ulterior Motives (2604.23460), Out-of-Sight (2608.04928), LTO (2509.26314), probe trajectories (2605.18549), filler-token decoding (2607.03502) | Scale >1B; naturally arising (not induced) misbehavior; probe transfer across languages/tasks |
| Causal audits / negatives | 2512.21711, 2606.12689, 2604.04902, 2607.06648, 2605.21642, 2507.02199, 2510.12167, 2604.21106 | Audits of discrete abstract tokens at 4B–8B (only third-party HF ablation exists) |
| CoT monitorability measurement & incentives | OpenAI suite (2512.18311), CoT control (2603.05706), MonitorBench (2603.28590), length penalties (2607.09786), incentives (2512.00218, 2603.30036), opaque serial depth (2603.09786), weak monitors (2605.12746, 2606.11998), attacks (2608.00583, 2608.02820, 2605.15257) | Cross-medium comparisons at matched accuracy with one fixed monitor |
| Multilingual × latent reasoning | LatentMT (2607.18618), not-yet-multilingual latent reasoners (2601.02996), SOLAR (2606.26466), cross-lingual consistency (2606.01464), fragility across 13 languages (2605.27901), audio multilingual workspace (2608.24958) | Parallel-data-supervised language-invariant abstract codes; monitor transfer across languages |

## Open gaps (searched and not found)

Phrasing rule: "No direct prior art found through 2026-09-01 under <coverage>".

1. Monitorability of latent/abstract media on tool-use agent tasks. No direct prior art found
   through 2026-09-01 under arXiv listing queries ("latent reasoning" AND (tool OR agent OR
   agentic); "chain-of-thought" monitorability), WebSearch, and full reads of ALAR, 2608.18171,
   CoLT, DRAFT, MIRAGE, 2608.04928, MonitorBench. Latent-medium papers measure tokens and
   accuracy; monitorability papers measure explicit CoT; the only latent-vs-explicit
   monitorability study (2608.04928) is 1B, math/QA, induced hints. Kevin advantage: the
   Docker/Slurm harness already carries agent-loop, oracle, trace, and paired-regression
   contracts; 8×H100 covers the 4B–8B scale where SWITCH/Abstract-CoT/J-CoT operate; Tinker
   gives RL on Qwen3.5-4B/9B and GLM-5.3 for the escalation policy.
2. Translation-equivariant abstract reasoning codes (same abstract trace for semantically
   equivalent problems across languages) with a monitor trained in one language tested in
   others. No direct prior art found under arXiv listing/WebSearch queries on multilingual,
   cross-lingual, and translation × latent reasoning: LatentMT treats MT as the task, SOLAR
   aligns soft tokens for accuracy with an English pivot, 2601.02996 is diagnostic, 2606.01464
   uses no parallel data, 2605.27901 shows monitors are fragile across 13 languages but proposes
   no medium. Kevin advantage: production parallel translation data (General Translation) is the
   supervision signal nobody else has at hand; the fragility result defines the evaluation.
3. Controlled reproduction of Abstract-CoT with token-necessity ablations at 4B–8B. No official
   code and no successful independent replication found (gh search "Thinking Without Words",
   "abstract chain-of-thought IBM", IBM org search; HF search "abstract-cot"; three third-party
   logs, all negative or stalled). Kevin advantage: 8×H100 (between LauraGG's 1×H100 and LE-WH's
   8×H200), Tinker Qwen3.5-4B/9B-Base for RL, and a harness built for paired regressions and
   SIGUSR1-resumable multi-day warm-ups; a clean positive or negative is publishable either way.
4. Interpretable-by-construction latents (MUX, J-CoT, DiscoLoop, Thinking States) evaluated as a
   monitoring channel under obfuscation pressure and for tool-call argument fidelity. No direct
   prior art found under HTML reads of all four papers and the monitorability listing; each
   reports only accuracy/compression (plus probes for span recovery in MUX). Kevin advantage:
   SWITCH/MUX/DLR code exists; the harness can run the 2608.00583-style reasoning-rewrite attack
   and the 2605.15257-style monitor-awareness pressure against each medium at matched accuracy.
5. Cross-medium monitorability-tax curve at matched accuracy with one fixed monitor (verbose CoT →
   length-penalized CoT → hybrid checkpoints → abstract tokens → continuous). No direct prior art
   found: 2607.09786 (tax exists) and 2512.00218 (no consistent effect) disagree on compressed
   explicit CoT alone; no study crosses media. Kevin advantage: this is Direction 15C verbatim;
   the U(π) objective already carries λ_m; 8×H100 suffices for Qwen3-4B/8B sweeps.
6. Multi-turn agent-loop evaluation of looped/recurrent-depth LMs with tool feedback, including
   depth-vs-monitorability. No direct prior art found: 2608.18171 states its benchmarks are
   static single-turn; Ouro's faithfulness claim has no reported numbers; community Terminal-Bench
   SFT is anecdotal. Kevin advantage: harness multi-turn loop; Ouro-1.4B/2.6B and Huginn-3.5B
   fit 8×H100 for SFT/RL and depth sweeps; opaque-serial-depth tooling (2603.09786) is open source.

## Negative results and retractions found

- No retraction or withdrawal was found in latent-reasoning/monitorability preprints under this
  coverage (checked arXiv abs pages for "withdrawn" text on ~155 papers; WebSearch for
  withdrawn/retracted latent reasoning was blocked by the exhausted budget).
- Version corrections: 2607.20952 v2 "corrected false-checkmate rate"; 2604.21106 v3 "minor
  corrections"; 2606.06574 removed duplicate examples ("conclusions remain unchanged").
- Negative/deflationary results: 2512.21711, 2606.12689, 2604.04902 (tokens often unnecessary),
  2607.06648, 2605.21642, 2507.02199, 2510.12167, 2604.21106 (φ=0.46), 2606.07720 (vanilla
  Coconut below CoT on HotpotQA), LE-WH and LauraGG Abstract-CoT reproductions, Anthropic lie
  detectors (cross-category AUROC 0.70–0.75), 2608.00583 (monitor collapse), 2605.27901 (95.9%
  unfaithfulness across languages).

## Exact queries run

WebSearch (18 successful; the 19th onward hit the 200-call session budget):
1. "Abstract Chain-of-Thought" Ramji 2026 abstract reasoning tokens arXiv 2604.22709
2. chain-of-thought monitorability 2026 paper OpenAI METR Anthropic DeepMind latent reasoning monitor
3. "Thinking States" latent reasoning language model 2026 paper
4. "DiscoLoop" transformer recurrent reasoning 2026
5. latent reasoning interpretable decodable "continuous thought" probe monitor 2026 arXiv
6. latent reasoning tool use agents "latent" function calling 2026 arXiv Coconut agent
7. "Mixture-of-Recursions" follow-up 2026 recursive transformer adaptive depth arXiv
8. Huginn recurrent-depth transformer 2026 follow-up Geiping "depth recurrence" reasoning arXiv
9. Anthropic 2026 chain-of-thought faithfulness monitorability research alignment blog latent reasoning
10. METR 2026 chain-of-thought monitorability report latent reasoning neuralese
11. Google DeepMind 2026 chain-of-thought monitoring paper "monitor" reasoning models evade arXiv
12. negative result latent reasoning Coconut "does not" OR "fails" OR "no evidence" 2026 arXiv continuous thought
13. "Latent Chain-of-Thought? Decoding the Depth-Recurrent Transformer" Huginn probing interpretable
14. multilingual cross-lingual latent reasoning parallel translation data language-agnostic latent thoughts 2026 arXiv
15. interpretable latent reasoning tokens codebook vector-quantized discrete latent thoughts decodable 2026 arXiv
16. "Reasoning Under Pressure" training incentives chain-of-thought monitorability arXiv 2026
17. Ouro looped language model 2026 "Ouro" latent reasoning agent tool use follow-up
18. latent reasoning arXiv August 2026 continuous thought new paper
(Blocked by budget: HybridCoT Shen 2026; activation oracles/LatentQA decode latent reasoning; neuralese translator; latent steganography/obfuscation; withdrawn/retracted latent reasoning; abstract tokens follow-ups citing Ramji; Anthropic system card 2026 monitorability; latent planning tokens tool calling JSON arguments.)

arXiv web search UI (curl; 5 successful, sorted by announce date, 50 results each):
- "latent reasoning"
- "chain-of-thought" monitorability
- "looped language model" OR "recurrent-depth" OR "depth-recurrent"
- "continuous thought" OR "continuous thoughts"
- "latent reasoning" AND (tool OR agent OR agentic)
(429-blocked: evaluating chain-of-thought monitorability; "abstract chain-of-thought" OR "abstract tokens" reasoning; "mixture-of-recursions" OR "recursive transformer"; "thinking states"; latent reasoning interpretable OR decodable OR verbalizable; latent "tool calling" OR "tool use"; neuralese; "weak monitor" OR "weaker monitor" OR "trusted monitor"; latent reasoning multilingual OR cross-lingual OR translation; steganography reasoning model; coconut continuous latent reasoning — attempted twice.)
arXiv web search via WebFetch (2): "Evaluating Chain-of-Thought Monitorability" (0 results); "abstract chain-of-thought" OR "abstract tokens" (12 results, none post-2026-04-24 building on Abstract-CoT).

arXiv API (export.arxiv.org): 7 keyword queries + 1 id_list batch — all HTTP 429.
Semantic Scholar API: 9 queries — all HTTP 429 (no API key).
Jina reader (r.jina.ai): 6 page reads — all 401 "blocked from performing anonymous queries (AS7018)".

GitHub `gh search repos` (31): coconut latent reasoning; latent reasoning llm; recurrent depth reasoning; chain-of-thought monitorability; abstract chain-of-thought; looped transformer; latent thought tokens; ouro looped language model; thinking states latent; discoloop; monitorbench; latent agentic reasoning; huginn recurrent; abstract-cot reproduction; looped tool calling; self-explainable latent reasoning; latentguard; chain of latent tool calls; thinking states latent reasoning; latent reasoning monitor probe; thinking without words; switchable latent reasoning; latent sparse transcoder; supervised thinking states; monitorability benchmark chain-of-thought 2026; multiplexed tokens continuous reasoning; J-CoT J-space; discoloop looped; abstract chain-of-thought IBM; granite abstract reasoning tokens; latent reasoning interp. Plus `gh api` searches: abstract chain of thought org:IBM; latent reasoning org:IBM.

Hugging Face model search API (13): coconut; latent reasoning; huginn; recurrent depth; abstract-cot; looped; ouro; latent-cot; codi (noise); plus model-info/README reads for 14 repos. HF papers API (2): chain-of-thought monitorability; Evaluating Chain-of-Thought Monitorability.

ft search over X bookmarks (22): coconut; latent; monitorability; chain of thought; Huginn; recurrent depth; Abstract-CoT (query error: hyphen parsed as column); Ramji; neuralese; looped; reasoning tokens; faithfulness; Ouro; looped language model; latent space; CoT monitor; steganograph; reasoning in latent; hidden reasoning; thinking tokens; recursion; interpretability. Relevant hits: @KeshavRamji Abstract-CoT thread (2026-04-27) and @RampLabs PorTAL thread (2026-07-01) only.

Primary pages opened via WebFetch: arXiv HTML for 2604.22709v2, 2602.08332v1, 2607.00341v1, 2608.13570, 2608.18171, 2608.04928v1, 2604.23460, 2604.04902, 2606.29712, 2606.13106, 2602.01695, 2602.04246, 2607.18264, 2607.21981, 2607.06648, 2608.03838, 2510.25741, 2603.28590, 2605.12746, 2606.11998, 2509.26314, 2606.07157; arXiv abs for 2512.21711, 2606.20560; alignment.anthropic.com index, /2026/sleight-bench/, /2026/introspection-adapters/, /2026/lie-detectors/; metr.org/research; gdmalignment.substack.com summary (2026-07-31); sparai.org SPAR project (Uzay Macar, Spring 2026, no outputs); ouro-llm.github.io.

## Coverage limits

- WebSearch session budget (200 calls shared across cells) was exhausted after this cell's 18th
  query; eight planned queries (HybridCoT, activation oracles/LatentQA, neuralese decoders,
  latent steganography, retractions, Abstract-CoT citers, Anthropic system cards, latent tool
  argument fidelity) were not run. The arXiv listing partially compensates.
- arXiv API and Semantic Scholar returned 429 for every request; the arXiv web UI rate-limited
  after five listing queries. Discovery therefore leans on five arXiv listings, WebSearch,
  GitHub, HF, and three curated awesome-lists (EIT-NLP/Awesome-Latent-CoT, huskydoge/
  Awesome-Loop-Models built 2026-08-31, cedarglass/Awesome-Chain-of-Thought-Monitorability).
- Jina reader was blocked; GitHub content was read through `gh api` instead.
- OpenAI's blog page for "Evaluating chain-of-thought monitorability" returned HTTP 403; the
  arXiv paper 2512.18311 was used as the primary and its abstract was truncated at ~1,100 chars.
- Body-level numbers come from WebFetch summaries of arXiv HTML by a small model; transcription
  errors are possible. Abstract-level claims were read verbatim.
- No live X search; ft covers Kevin's bookmarks only (2 relevant hits).
- Many findings are single-author or first-party preprints (flagged inline); peer-review status
  was taken from arXiv comments or code READMEs, not verified against proceedings.
- Code was not executed; reproduction-repo claims (LE-WH, LauraGG, bertybaums) are third-party logs.
- Post-2026-08-10 coverage is limited to what the arXiv listings and awesome-lists surfaced; a
  full arXiv API sweep by date could not be run.
