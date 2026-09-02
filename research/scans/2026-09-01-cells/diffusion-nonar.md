# Frontier sweep — Diffusion and non-autoregressive language models (cell: diffusion-nonar)

Date: 2026-09-01. Previous sweep cutoff: 2026-08-10. Owner brief: `scratchpad/context.md`.
Question asked: where do repeated refinement passes beat autoregression at equal wall
time, which claims are first-party only, and what is still open for Kevin.

## Decision summary

1. The "refinement beats AR at equal wall time" claim is still almost entirely
   first-party and batch-1. Every headline speed number (LLaDA2.2 519–704 TPS,
   DiffusionGemma 1,000–1,288 tok/s, Mercury 2/2.5 1,000–1,107 tok/s, Gemini Diffusion
   1,479 tok/s, Seed Diffusion 2,146 tok/s, Nemotron-TwoTower 2.42x, Nemotron tri-mode
   4x) comes from the model's authors. The single independent measurement found
   (Artificial Analysis, Mercury 2) reads 684 tok/s output with a 4.01 s TTFT, well below
   the 1,000+ first-party figure. Google itself states DiffusionGemma has "diminishing
   returns under high-QPS cloud workloads" and lower quality than Gemma 4 on every listed
   benchmark.
2. Quality at equal size still favors AR on agentic tasks. Peer-reviewed (ACL 2026)
   evidence: LLaDA-8B 7.5% and Dream-7B 3.4% AgentBoard success vs 45.0% for Qwen-8B;
   BFCL-v3 multi-turn 0% for all tested dLLMs. First-party 100B evidence (LLaDA2.2-flash
   vs its AR sibling Ling-2.6-flash): AR wins SWE-bench Verified 61.2 vs 49.3 and
   BFCL-V4 66.8 vs 60.8; diffusion wins τ²-Bench 80.3 vs 76.4 and MCP-Atlas 46.2 vs 41.1
   at 1.7–2.1x TPS. The AR baseline ran with 4-token MTP, and SWE-bench used different
   scaffolds, so this is not a clean iso-wall-time comparison.
3. The design space Kevin's last sweep left open ("a use case where repeated passes
   beat AR at equal wall time") has been heavily colonised since: edit-based decoding
   (LLaDA2.1/2.2 Levenshtein editing), variable-length canvases (DreamOn, Entropy-Valley,
   CARVE), block/multi-block and hybrid block-SSM architectures, learned generation
   order, refinement-aware MoE routing, linear-attention retrofits, and "diffusion drafts,
   AR verifies" speculative hybrids are all occupied. Diffusion+MoE remains rejected
   (LLaDA MoE v2, 23.5T tokens from scratch).
4. Four gaps survive explicit searching (below): a controlled iso-wall-time dLLM-vs-AR
   comparison on agent tasks with CPU overhead charged; language-dependent serial depth
   of denoising measured with translation-equivalent inputs; a bilingual joint-canvas
   dLLM trained on parallel corpora; and localized re-denoising of partially executed
   typed plans (Kevin's candidate #5), which now needs three new deltas to survive the
   LLaDA2.2 collision.
5. Negative results and re-evaluations are accumulating: answer-first commitment order
   hurts accuracy (2608.05687); bidirectionality gives no robustness guarantee and dLLMs
   are systematically overconfident (2607.27386); confidence remasking (WINO) gives
   little-to-no benefit under standard settings (2606.12232); parallel decoding degrades
   sharply when token dependencies are strong (ParallelBench, ICLR 2026); MDLMs lag AR
   on 58 benchmarks with 8 models up to 100B (2601.15593). No retraction or withdrawal of
   a dLLM paper was found.

## Method and coverage

Modalities that produced results: arXiv export API (2 successful queries before rate
limiting), WebSearch (16 queries), Hugging Face model search API (11), Hugging Face
papers API (6 searches plus 18 abstract lookups), GitHub (`gh search repos` x3,
`gh api` commits/readme x16), OpenAlex (5 searches, 2 record lookups), DBLP (6 lookups,
3 returned), `ft` X-bookmark search (18 queries), WebFetch on primary pages (about 40
arXiv abstracts, model cards, lab blogs). Failed modalities are listed under coverage
limits. Every quantitative claim below was read from the primary page named in the
finding; nothing is cited from memory.

Legend for source status: FP = first-party (authors' arXiv preprint, README, model
card, or lab blog); PR = peer-reviewed venue stated on the primary page; PR* = venue
independently confirmed (DBLP); IND = independent third-party measurement.

## Findings

Ordered by date, newest first. "Occupies" names the design axis the work takes.

### F1. LLaDA2.2-flash model card and technical report (Ant Group inclusionAI)
- URL: https://huggingface.co/inclusionAI/LLaDA2.2-flash ; report:
  https://github.com/inclusionAI/LLaDA2.X/blob/main/LLaDA2_2_tech_report.pdf ;
  abstract mirror: https://cspaper.org/openprint/20260728.0007v1
- Date: report 2026-07-22 (GitHub commit); model card last modified 2026-08-20. FP.
- Claim: 100B (non-embedding) MoE dLLM, 128K context, "Levenshtein Editing" with
  DELETE/INSERT control tokens (KEEP/SUBSTITUTE/DELETE/INSERT with LCS-derived labels),
  Block Routing (expert activation bounded per diffusion block), L-EBPO agentic RL.
  Versus AR sibling Ling-2.6-flash: SWE-bench Verified 49.28 vs 61.20 (Claude Code vs
  OpenHands scaffold), SWE-bench Pro 30.10 vs 31.88, SWE-bench Multilingual 25.00 vs
  33.73, τ²-Bench 80.33 vs 76.36, Claw-Eval 64.22 vs 64.56, PinchBench 81.66 vs 81.30,
  MCP-Atlas 46.21 vs 41.12, BFCL-V4 60.78 vs 66.81; TPS 519.0 vs 303.2 (SWE-V), 592.8 vs
  334.9 (τ²), 703.8 vs 331.5 (BFCL-V4), with AR using MTP and 4 draft tokens; five-run
  averages; block_length=32, threshold=0.5, editing_threshold=0.0, temperature=1.0.
- Occupies: edit-based dLLM decoding for agents; agentic RL for dLLMs; block-level MoE
  routing; the "dLLM as agent backbone" claim at 100B.
- Relevance: the closest collision with Kevin's candidate #5 (error correction during
  multi-turn tool use is now a shipped, first-party mechanism). Also shows AR still wins
  the two hardest structured benchmarks (SWE-bench, BFCL). Confidence 0.85 that the
  numbers are as stated; 0.4 that they would replicate under one scaffold and no MTP.

### F2. CARVE: Verified Expansion for Variable-Length Generation in DLMs
- URL: https://arxiv.org/abs/2608.30922 — 2026-08-31 — PR (EMNLP 2026 Findings, stated).
- Claim: training-free canvas growth by inserting [MASK] positions, kept only when the
  Jensen-Shannon divergence on aligned unresolved positions is low; improves over
  fixed-length decoding across all evaluated families on code and math, "reaching half
  the FLOPs of fixed-length decoding in some settings".
- Occupies: variable-length generation for full-canvas and blockwise MDLMs.
- Relevance: length is one of the two levers that separate dLLM MT from AR MT (see F8);
  the axis is now crowded (DreamOn, Entropy-Valley, natively-length-aware, CARVE).

### F3. Trajectory-Level Speculative Decoding for DLMs
- URL: https://arxiv.org/abs/2608.27514 — 2026-08-27 — FP.
- Claim: confidence-stratified tree exploration of draft denoising trajectories verified
  blockwise; 7–14x over vanilla dLLM decoding, 1.3x over Fast-dLLM, tokens/step 2.6 to
  4.3, denoising iterations −30–40%, <1% accuracy change.
- Occupies: speculation inside dLLM decoding (on top of Fast-dLLM caches).

### F4. Conditional Total Correlation and the Serial Depth of Adaptive Parallel Sampling
- URL: https://arxiv.org/abs/2608.25505 — 2026-08-26 — FP (theory).
- Claim: the divergence of adaptive parallel sampling from the optimal sampler equals the
  expected conditional total correlation accumulated over reveal rounds; serial depth
  (minimum rounds meeting an error budget) scales with Markov order times log n for
  Markov chains; left-to-right vs hierarchical reveal orders separate linearly vs
  logarithmically; validated with an MDLM, and the pseudo-cost ranks deployed decoding
  rules consistently with output quality.
- Occupies: a principled answer to "when can parallel refinement beat serial decoding".
- Relevance: gives Kevin a measurable quantity (conditional total correlation per reveal
  round) to test per language and per task, which nobody has done (gap G2).

### F5. Serving Masked Diffusion LLMs: Characterization and Design Principles from Real Hardware
- URL: https://arxiv.org/abs/2608.23807 — 2026-08-24 — FP.
- Claim: LLaDA-8B-Instruct with a D2F LoRA on one H200, GSM8K/HumanEval: only 24% of
  single-request wall-clock is GPU compute; batching gives 16.0x throughput at batch 16,
  mostly by amortizing CPU dispatch; per-request denoising step counts fall at 11 fixed
  levels and are unpredictable beforehand (best R² = 0.150); generation budgets under 320
  tokens understate serving variance; accuracy 74–76% GSM8K unchanged by batching.
- Occupies: systems characterization of MDLM serving.
- Relevance: any equal-wall-time claim at batch 1 in current stacks is dominated by
  non-GPU overhead; Kevin's wall-time ledgers must charge it (see F1, G1).

### F6. SelFusion: Self-distillation for DLMs
- URL: https://arxiv.org/abs/2608.22898 — 2026-08-24 — FP.
- Claim: conventional KD gives marginal or negative gains for dLLMs; two-pass
  hard/easy-mask self-distillation with bidirectional token-level KD beats external LLM
  and DLM teachers on instruction following, sometimes surpassing the LLM teacher.
- Occupies: distillation recipes for dLLM quality.

### F7. Length-Adaptive Decoding for Masked Diffusion Machine Translation (Entropy-Valley)
- URL: https://arxiv.org/abs/2608.22274 ; adapters
  https://huggingface.co/YanZhanPKU/Entropy-Valley-LLaDA-8B-En2De (and En2Zh, Zh2En) ;
  code https://github.com/Entropy-Valley/Entropy-Valley
- Date: 2026-08-23 (paper), 2026-08-25 (adapters). PR (EMNLP 2026 main, stated).
- Claim: masked-diffusion MT needs a target canvas length before denoising; EV scores
  candidate lengths by mean predictive entropy from all-mask forward passes and decodes
  the minimum. LLaDA-8B-Base LoRA (r=64, α=128, q/k/v/o + FFN) on 200k WMT19 pairs, 3
  epochs, 8×H20; MED schedule, T=32 steps. EV recovers 64.9% / 65.3% / 33.0% of the
  COMET-22 gap to oracle length on En→Zh / Zh→En / En→De; ties a LLaMA-3-8B AR model
  trained on identical data on En→Zh and leads on Zh→En. WMT22 En→De COMET-22: fixed
  ratio 1.8 = 0.7170, EV = 0.7240, oracle = 0.7382; sacreBLEU 20.73 / 21.55 / 22.55.
  The model card states the En→De gains are smaller "and the paper documents why".
- Occupies: dLLM MT at 8B; decoding-time length selection; per-direction LoRA adapters.
- Relevance: directly on Kevin's translation asset. No wall-time comparison against the
  AR baseline is given on the abstract page; the language-pair asymmetry (De far weaker
  than Zh) is unexplained at the mechanism level and is the seed of gap G2.

### F8. CForce: Consistency Forcing for parallel decoding (inclusionAI dFactory)
- URL: https://arxiv.org/abs/2608.13925 ; code https://github.com/inclusionAI/dFactory
- Date: 2026-08-14. FP.
- Claim: distills early-stage mask predictions toward later-stage predictions on
  self-rollout trajectories with a confidence-adaptive KL; applies to mask-to-token and
  edit-capable decoding; better speed-quality trade-offs on LLaDA models at high
  parallelism budgets.
- Occupies: training-inference alignment for aggressive parallel decoding.

### F9. Continuous Interaction Diffusion: a diffusion-native runtime for asynchronous tool use
- URL: https://arxiv.org/abs/2608.10438 — 2026-08-11 — FP position paper, single author.
- Claim: tool reads are launched from "perceptual bindings" that emerge mid-denoising and
  their results are projected back into the evolving thought state; the paper states it
  "makes no empirical performance claims".
- Occupies (conceptually): asynchronous tool interaction inside denoising.
- Relevance: the idea is now published; any Kevin proposal on tool calls during denoising
  must cite it, but it leaves all measurements open.

### F10. Reducing Pretraining-Generation Mismatch in DLMs (Prefix-Conditioned Diffusion)
- URL: https://arxiv.org/abs/2608.09424 — 2026-08-10 — FP.
- Claim: native dLLM pretraining corrupts prompt and continuation together; PCD applies AR
  supervision to clean prefixes and denoising only to continuations; +2.56 points (4.2%
  relative) on a six-benchmark average for LLaDA2-Mini and +4.86 (14.2%) in a Qwen-1.7B
  mechanism study, with no inference change.
- Occupies: pretraining objective fixes for prompt-conditioned generation.

### F11. Answer First, Reason Later: commitment order costs accuracy (negative result)
- URL: https://arxiv.org/abs/2608.05687 — 2026-08-06, revised 2026-08-24 — FP.
- Claim: for LLaDA-8B, LLaDA-1.5 and Dream-7B on GSM8K (1,069 items), MATH-500 and a
  controlled four-option task, unrestricted decoding produces more answer-first
  commitment trajectories and these lower accuracy; delaying answer positions works best,
  but the authors caution that generality is limited.
- Occupies: commitment-order analysis. Relevance: a concrete failure mode of "revise
  anywhere" decoding that a plan-repair method must control for.

### F12. Retrofitting Linear Attention into DLMs (LLaDA-Hybrid)
- URL: https://arxiv.org/abs/2608.06628 — 2026-08-06 — FP.
- Claim: block-hybrid attention (exact softmax inside the active block, linear attention
  over previous blocks) in 6 of 20 layers of LLaDA2.1 (16B) after ~60 h post-training:
  up to 1.7x decoding throughput; HumanEval 72.0 vs 75.6, MBPP+ 63.0 vs 57.7, CMATH 86.7
  vs 88.3.
- Occupies: linear-attention retrofits for dLLMs.

### F13. LLaDA MoE v2: Scaling MoE DLMs
- URL: https://arxiv.org/abs/2608.03457 ; weights
  https://huggingface.co/GSAI-ML/LLaDA-MoE-v2-30B-A3B-Instruct (2026-08-19)
- Date: 2026-08-04. FP.
- Claim: 30B-A3B trained from scratch on 23.5T tokens (~65% of Qwen3's budget)
  "approaches Qwen3 on several knowledge, reasoning, and coding benchmarks"; after SFT
  alone it beats SDAR Chat on 7 of 8 reasoning/coding benchmarks; scaling laws: bigger
  expert pools at fixed activation, optimal batch size grows faster than AR, optimal LR
  decays faster with compute.
- Occupies: diffusion+MoE scaling (already in Kevin's Rejected table; still rejected).

### F14. REFLEX: refinement-aware expert allocation in MoE DLMs
- URL: https://arxiv.org/abs/2608.01784 — 2026-08-03 — FP.
- Claim: training-free coarse-to-fine expert reallocation driven by a Frontier-Progress
  Score cuts allocated expert compute by 15% on LLaDA-MoE and LLaDA2.0-mini while
  preserving or improving quality on most benchmarks.
- Occupies: MoE routing conditioned on denoising progress.

### F15. DiffusionGemma (Google DeepMind): blog, model card, docs, technical report, vLLM
- URLs: https://blog.google/innovation-and-ai/technology/developers-tools/diffusion-gemma-faster-text-generation/
  (2026-06-10) ; https://huggingface.co/google/diffusiongemma-26B-A4B-it ;
  https://ai.google.dev/gemma/docs/diffusiongemma ; report https://arxiv.org/abs/2608.00146
  (2026-07-31) ; https://vllm.ai/blog/2026-06-10-diffusion-gemma (2026-06-10). FP.
- Claim: 25.2B total / 3.8B active MoE (8 of 128 experts + 1 shared), 30 layers, 256K
  context, 256-token canvas, AR encoder that prefills and caches the prompt plus a
  bidirectional decoder over the canvas (block-autoregressive multi-canvas sampling);
  obtained by fine-tuning Gemma 4 with under 10% of the AR model's compute in two stages
  (SFT for bidirectional denoising, then RL plus sampler distillation); ~20 tokens per
  forward pass; 1,000+ tok/s on one H100 and 700+ on an RTX 5090 (blog), 1,288 tok/s
  (H200 FP8) and 1,008 tok/s (H100 FP8) at batch 1 in vLLM, "~5–6x" an unnamed AR
  baseline. Quality vs Gemma 4 26B A4B: MMLU Pro 77.6 vs 82.6, AIME 2026 69.1 vs 88.3,
  LiveCodeBench v6 69.1 vs 77.1, Codeforces 1429 vs 1718, GPQA Diamond 73.2 vs 82.3,
  Tau2 56.2 vs 68.2, HLE no tools 11.0 vs 8.7, BigBench Extra Hard 47.6 vs 64.8, MMMLU
  81.5 vs 86.3, MRCR v2 128k 32.0 vs 44.1. Google states quality is lower than Gemma 4
  and that the speedup is for local, low-concurrency inference with "diminishing returns
  under high-QPS cloud workloads". Recommended sampler: entropy-bounded denoising, max
  48 steps, typically 12–16 with adaptive stopping. The technical report abstract
  (2608.00146) states "roughly 1,500 output tokens per second on a single NVIDIA H100",
  "substantially faster than AR models even with state-of-the-art speculative decoding",
  and that the model "remains capable of AR generation with only minor performance
  degradation". Three first-party-adjacent H100 numbers therefore coexist: 1,000+ (blog),
  ~1,500 (report, suite average), 1,008 (vLLM, FP8, batch 1).
- Occupies: AR-encoder/diffusion-decoder factorization from an AR checkpoint at 26B; the
  low-concurrency speed niche; native vLLM dLLM support.
- Relevance: the strongest public admission that the wall-time win is regime-specific.
  Also the first frontier-lab open dLLM with tool calling; a candidate backbone for
  Kevin's pilots (vLLM-servable; Apache 2.0).

### F16. Beyond the Bidirectional Promise: re-evaluating DLM robustness (negative result)
- URL: https://arxiv.org/abs/2607.27386 — 2026-07-29 — FP.
- Claim: LLaDA-8B vs LLaMA-3-8B and Dream-7B vs Qwen2.5-7B under 32 natural
  perturbations, gradient attacks and hidden-state analysis: stochastic dLLM loss
  landscapes resist gradient-based adversarial suffixes but give "no guaranteed defense
  against natural noise"; dLLMs are systematically overconfident; failures are "decoder
  routing" failures despite correctly encoded inputs.
- Occupies: dLLM robustness claims. Relevance: robustness must be built into iterative
  decoding, not assumed from bidirectionality.

### F17. From Interface to Inference: eliciting any-order inference (insertion and latent MDMs)
- URL: https://arxiv.org/abs/2607.26504 — 2026-07-29, v2 2026-08-09 — FP (Harvard group).
- Claim: masked diffusion offers an any-order interface but not any-order inference;
  insertion-based MDM (7B FlexMDM, Python) and latent-space MDM (125M, GSM8K) search over
  semantic generation orders and improve downstream performance (numbers not on the
  abstract page).
- Occupies: any-order inference beyond token order.

### F18. Nemotron-Labs-Diffusion: tri-mode AR / diffusion / self-speculation (NVIDIA)
- URL: https://arxiv.org/abs/2607.05722 — 2026-07-07 — FP.
- Claim: one model trained with a joint AR-diffusion objective switches between AR,
  diffusion and self-speculation (diffusion drafts, AR verifies) modes; 3B/8B/14B; the 8B
  decodes 6x more tokens per forward than Qwen3-8B at comparable accuracy, 4x throughput
  on SPEED-Bench with SGLang on a GB200; self-speculation beats MTP in acceptance rate;
  "speed-of-light" analysis gives up to 76.5% more tokens per forward pass under an
  optimal sampler.
- Occupies: AR/diffusion mode-switching in a single network; concurrency-adaptive serving.

### F19. Training Hybrid Block Diffusion LMs with Partial Bidirectionality (BDLM Mamba-H)
- URL: https://arxiv.org/abs/2607.02805 ; code https://github.com/pc0618/block-diffusion-hybrids
- Date: 2026-07-02. FP (Modal academic grant).
- Claim: forward Mamba state as prefix cache over completed blocks, reverse Mamba scan
  restricted to the active denoising block; best 87M validation perplexity in a DCLM LR
  sweep, competitive with BDLM attention at 350M; 19.7x throughput of full-sequence
  DiffuMamba-H at 65K generated tokens and 3.7x of BDLM attention at 262K.
- Occupies: block diffusion × SSM hybrids with a native prefix cache. Relevance: this is
  the diffusion analogue of Kevin's "mixture of sequence operators" idea; the operator mix
  is again statically wired.

### F20. Set Diffusion: interpolating token orderings between AR and diffusion
- URL: https://arxiv.org/abs/2607.01775 — 2026-07-02 — PR (ICML 2026, stated; DBLP shows
  CoRR only).
- Claim: factorizes over flexible-position, flexible-length token sets with KV caching;
  better speed-quality trade-offs than prior DLMs on math, summarization and
  unconditional generation and stronger infilling than block diffusion (numbers not on
  the abstract page).
- Occupies: the AR-to-diffusion ordering continuum (with A3, F27).

### F21. Multi-Block Diffusion Language Models (SJTU)
- URL: https://arxiv.org/abs/2606.29215 ; code https://github.com/SJTU-DENG-Lab/mbd-lms
- Date: 2026-06-28. PR (EMNLP 2026, stated in repo).
- Claim: decode a bounded running set of consecutive blocks concurrently with multi-block
  teacher forcing and a static-shape Block Buffer; LLaDA2-Mini tokens-per-forward 3.47 to
  6.19 with average accuracy 79.95% to 81.03%; with DMax TPF 9.34 at a 1.02-point drop.
- Occupies: inter-block parallelism for block-diffusion LMs.

### F22. Nemotron-TwoTower: diffusion denoiser over a frozen AR context tower (NVIDIA)
- URL: https://arxiv.org/abs/2606.26493 — 2026-06-25 — FP, open weights.
- Claim: frozen AR context tower plus trainable bidirectional-block denoiser tower with
  cross-attention, built on Nemotron-3-Nano-30B-A3B (hybrid Mamba-Transformer MoE),
  ~2.1T tokens; retains 98.7% of AR quality at 2.42x wall-clock generation throughput.
- Occupies: two-tower AR-context/diffusion-decoder factorization (same family as F15).

### F23. Improved Large Language Diffusion Models (iLLaDA)
- URL: https://arxiv.org/abs/2606.25331 — 2026-06-24 — FP (Renmin/GSAI).
- Claim: 8B fully bidirectional MDLM from scratch on 12T tokens plus 25B instruction
  tokens over 12 epochs; vs LLaDA: BBH +21.6 and ARC-C +14.9 (base), MATH +14.5 and
  HumanEval +16.5 (instruct); competitive with Qwen2.5-7B on several benchmarks.
- Occupies: from-scratch dLLM recipe at 8B. Relevance: the LLaDA-8B checkpoint Kevin has
  registered is now two generations old (LLaDA-1.5, iLLaDA, LLaDA2.x).

### F24. Scheduling Thoughts: learning the order of thought (Self-Aware Scheduling)
- URL: https://arxiv.org/abs/2606.23567 — 2026-06-22 — FP.
- Claim: GRPO-trained lightweight ordering policy with a frozen denoiser; Sudoku 82.0% to
  91.8% (97.5% with fine-tuning) on a 1B MDM; LLaDA-8B GSM8K 64% to 76% and MBPP 39.5% to
  41% pass@1.
- Occupies: learned generation order as a separate policy.

### F25. Re-evaluating Confidence Remasking in MDLMs (negative re-evaluation)
- URL: https://arxiv.org/abs/2606.12232 — 2026-06-10 — FP (Amsterdam/UCL group).
- Claim: WINO-style post-hoc remasking gives "little-to-no benefit over confidence-based
  unmasking alone" at standard short block lengths and worsens diversity collapse under
  non-greedy decoding; benefits are highly setting-dependent.
- Occupies: self-correction-by-remasking claims. Relevance: "revise already committed
  tokens" is exactly the mechanism a plan-repair method leans on; its benefit is not
  established in general.

### F26. Don't Retrain, Align: AR-to-DLM conversion via representation alignment
- URL: https://arxiv.org/abs/2605.06885 — 2026-05-07 — FP.
- Claim: aligning every DLM layer's hidden states to a frozen AR twin (cosine) during
  masked-denoising training, no adapters, yields up to 4x training acceleration; frames
  conversion as "relearning the decoding path rather than language representations".
- Occupies: cheap AR-to-dLLM conversion (with LLaDA2.0 block-WSD, DiffusionGemma <10%
  budget, SDAR, Stable-DiffCoder).

### F27. Autoregressive Models Rival Diffusion Models at Any-Order Generation (A3)
- URL: https://arxiv.org/abs/2601.13228 — 2026-01-19 — FP (Peking University group).
- Claim: any-order any-subset AR with two-stream attention and progressive adaptation
  "outperforms diffusion-based models while maintaining flexible decoding" on QA,
  commonsense reasoning and story infilling; no speed comparison on the abstract page.
- Occupies: any-order AR as an alternative to masked diffusion.

### F28. Parallelism and Generation Order in MDLMs: Limits Today, Potential Tomorrow
- URL: https://arxiv.org/abs/2601.15593 — 2026-01-22, revised 2026-04-11 — FP (17 authors).
- Claim: eight MDLMs up to 100B on 58 benchmarks; MDLMs underperform comparable AR models
  because parallel probabilistic modeling weakens inter-token dependencies; parallelism
  and order vary by domain and reasoning stage; MDLMs win on backward-information tasks
  (Sudoku); proposes generate-then-edit.
- Occupies: the empirical map of where parallelism pays.

### F29. The Bitter Lesson of DLMs for Agentic Workflows (DiffuAgent)
- URL: https://arxiv.org/abs/2601.12979 (v3 2026-04-24) — PR* ACL 2026 main (DBLP).
- Claim: AgentBoard success (AlfWorld / ScienceWorld / BabyAI / avg): Qwen-8B 76.1 /
  26.7 / 32.1 / 45.0; LLaDA-8B 5.2 / 1.1 / 16.1 / 7.5; Dream-7B 0.7 / 0.6 / 8.9 / 3.4;
  FdLLM-7B 3.1 avg despite >150 tok/s. BFCL-v3 overall: Qwen-8B 57.8, LLaDA-8B 19.4,
  Dream-7B 13.6, DVar-8B 28.0; multi-turn 0.0 for every dLLM. dLLMs "fail to maintain
  symbolic precision (e.g. strict JSON schemas) under diffusion noise"; DiffuAgent adds a
  memory compressor, early-exit verifier, tool selector and JSON format editor.
- Occupies: peer-reviewed dLLM agent baselines and the JSON-editor patch.
- Relevance: the strongest published negative for 7–8B dLLM agents; any pilot must start
  from LLaDA2.x/DiffusionGemma-class checkpoints, not LLaDA-8B.

### F30. DLLM Agent: See Farther, Run Faster (controlled dLLM vs AR agents)
- URL: https://arxiv.org/abs/2602.07451 — 2026-02-07 — FP.
- Claim: same DeepDiver workflow and matched agent fine-tuning on the same trajectories;
  at comparable accuracy dLLM agents are on average over 30% faster end to end, some cases
  over 8x, with fewer interaction rounds and tool calls; naive dLLM policies are more
  prone to structured tool-call failures and need tool-call-specific training; for
  multi-turn inputs interleaving context and action spans, "diffusion-style span
  corruption requires aligned attention masking to avoid spurious context-action
  information flow; without such alignment, performance degrades".
- Occupies: matched-supervision dLLM-vs-AR agent comparison; context/action-aligned
  masking for multi-turn dLLM training (directly relevant to the typed-DAG masks in
  Kevin's candidate #5).
- Relevance: the only found study close to "refinement beats AR at equal accuracy on wall
  time" for agents; it conflicts in spirit with F29 and is unreplicated.

### F31. DLLM-Searcher: adapting dLLMs for search agents
- URL: https://arxiv.org/abs/2602.07035 — 2026-02-03 — FP.
- Claim: agentic SFT/VRPO plus Parallel-Reasoning-and-Acting (decode tool_call first,
  keep reasoning while the tool runs) gives ~15% inference acceleration and performance
  comparable to mainstream LLM search agents.
- Occupies: tool-call-first decoding order for dLLM agents.

### F32. Speculative hybrids: DEER, DFlash, D²SD
- URLs: https://arxiv.org/abs/2512.15176 (DEER, 2025-12-17, FP) ;
  https://arxiv.org/abs/2602.06036 (DFlash, 2026-02-05, ICML 2026 stated; DBLP CoRR) ;
  https://arxiv.org/abs/2606.04446 (D²SD, 2026-06-03, FP).
- Claim: DEER drafts with a dLLM and verifies with AR: acceptance lengths up to 32 tokens
  vs 10 for EAGLE-3; 5.54x on HumanEval with Qwen3-30B-A3B vs 2.41x for EAGLE-3. DFlash:
  block-diffusion drafter conditioned on target features, lossless, over 6x, up to 2.5x
  higher than EAGLE-3. D²SD: dual diffusion drafters in a confidence-guided prefix tree
  with cascade attention.
- Occupies: "diffusion drafts, AR verifies" — crowded, lossless, and already at frontier
  speedups.

### F33. Stable-DiffCoder (ByteDance Seed) and SDAR (JetLM)
- URLs: https://arxiv.org/abs/2601.15892 (2026-01-22, FP) ;
  https://huggingface.co/JetLM/SDAR-4B-Chat-b16 (README; repo active to 2026-07-29, FP).
- Claim: Stable-DiffCoder — block-diffusion continual pretraining (warmup, block-wise
  clipped noise schedule) on the Seed-Coder architecture and data outperforms the AR
  counterpart and "a wide range of ~8B ARs and DLLMs" on code. SDAR — AR-to-block-diffusion
  conversion; "on-par general task performance" with Qwen3 AR-SFT under controlled
  comparison (block_length 4, 4 steps) and gains on GPQA/ChemBench/Physics.
- Occupies: controlled same-data quality comparisons (not wall time). Note the name
  collision: "SDAR" is also Self-Distilled Agentic RL (arXiv 2605.15155), an AR method;
  `wckwan/Search-R1-Qwen3-8B-SDAR` on HF is the AR method, not a dLLM.

### F34. Mercury 2 and Mercury 2.5 Preview (Inception Labs) with independent measurement
- URLs: https://www.inceptionlabs.ai/ ; https://www.inceptionlabs.ai/models ;
  https://www.inceptionlabs.ai/blog/mercury-2-on-pinchbench (2026-09-01) ;
  https://openrouter.ai/inception/mercury-2.5-preview (2026-08-31) ;
  https://artificialanalysis.ai/models/mercury-2 (IND).
- Claim (FP): Mercury 2 "over 1000 tokens/sec" on commercial NVIDIA GPUs, 128K context,
  tool calling, $0.25/$0.75 per 1M; PinchBench 78% vs GPT-5 Mini 75%, Gemini 2.5 Flash
  71%, DeepSeek Chat 72%, GPT-4o 71% (run by Inception). Mercury 2.5 Preview (2026-08-31):
  1,107 tok/s claimed, 260K context, parallel tool calls, schema-aligned JSON, "10+ point
  jump in intelligence over Mercury 2". Claim (IND, Artificial Analysis): Mercury 2 output
  speed 684.0 tok/s, TTFT 4.01 s, Intelligence Index 22.
- Occupies: commercial closed dLLM APIs for agents. No open weights, no Mercury 2 technical
  report (only the Mercury v1 preprint, arXiv 2506.17298).
- Relevance: the only case where an independent measurement exists, and it is well below
  the first-party figure; TTFT of 4 s is at odds with the "sub-300 ms TTFT" site claim.

### F35. Gemini Diffusion status (Google DeepMind)
- URL: https://deepmind.google/models/gemini-diffusion/ — page read 2026-09-01 — FP.
- Claim: still "an experimental demo"; 1,479 tok/s sampling speed excluding 0.84 s
  overhead; AIME 2025 23.3% vs 20.0% for Gemini 2.0 Flash-Lite; HumanEval 89.6% vs
  90.2%; underperforms Flash-Lite on reasoning and multilingual benchmarks.
- Occupies: nothing new since 2025; DiffusionGemma is the shipped descendant.

### F36. Supporting systems and smaller items opened
- Seed Diffusion (ByteDance): https://arxiv.org/abs/2508.02193 (2025-08-04, FP) — 2,146
  tok/s on H20 GPUs, "significantly faster than contemporary Mercury and Gemini
  Diffusion", code-focused. Pre-cutoff context.
- ParallelBench: https://arxiv.org/abs/2510.04767 (ICLR 2026, stated) — parallel decoding
  "can suffer dramatic quality degradation" when dependencies are strong; strategies fail
  to adapt parallelism to difficulty.
- Diffusion LMs are natively length-aware: https://arxiv.org/abs/2603.06123 (2026-03-06)
  — zero-shot context cropping from prompt latents cuts FLOPs on GSM8K/HumanEval/IfEval/
  LongFormQA without significant degradation.
- x-Prediction Flow: https://arxiv.org/abs/2606.29066 (HF 2026-08-17) — continuous
  decoding retains 83–97% of full-budget accuracy with under 15% of steps on LLaDA.
- Self-Generated Error Training for token editing: https://arxiv.org/abs/2606.17175
  (2026-06-15) — LoRA on LLaDA2.1-mini trained on the model's own draft errors.
- TDAR: https://arxiv.org/abs/2602.09555 (v3 2026-08-22) — 2.38x speedup and +3.4%
  accuracy over TraDo-8B on six reasoning benchmarks; no AR wall-time control.
- Lost in Interpolation: https://arxiv.org/abs/2608.06529 (2026-08-06) — LERP soft-mask
  feedback fails because mask/token embeddings sit at ~73° on a hypersphere (169M MDLM).
- Diffutron: https://arxiv.org/abs/2603.20466 (2026-03-20) — a Turkish MDLM via LoRA
  continual pretraining of a multilingual encoder; the only single-language dLLM found.
- OoO-Spec: https://arxiv.org/abs/2608.00814 (2026-08-01) — a Qwen3-0.6B AR sidecar
  predicts all schema-defined tool-call slots in one wave while the target decodes; target
  remains sole verifier; sidecar trained once and reused across Qwen2.5/Qwen3/Llama.
  Not diffusion, but it occupies target-agnostic parallel tool-call speculation.
- vLLM: native DiffusionGemma support (2026-06-10) and
  https://github.com/vllm-project/dllm-plugin (LLaDA2.0 support, last commit 2026-05-25).
- Awesome lists: https://github.com/VILA-Lab/Awesome-DLMs (1,202 stars) and
  https://github.com/MessiX77/Awesome-Efficient-dLLMs (EMNLP 2026 survey).
- Repo activity: inclusionAI/LLaDA2.X last commit 2026-07-22; ML-GSAI/LLaDA 2026-07-15
  (iLLaDA eval); DreamLM/Dream code unchanged since 2025-11-21 (DreamOn/Dream-Coder repos
  touched Aug 2026, DreamReasoner-8B 2026-07-19); inclusionAI/dInfer 2026-02-11;
  NVlabs/Fast-dLLM 2026-05-30; JetAstra/SDAR 2026-07-29 (QR code only).

## Occupied-axes table

| Axis | What is taken | Primary URLs |
|---|---|---|
| AR-to-dLLM conversion and AR-context/diffusion-decoder factorizations at scale | Block-WSD conversion to 100B (LLaDA2.0), <10%-budget fine-tune of Gemma 4 with AR encoder + bidirectional decoder (DiffusionGemma), frozen AR tower + denoiser tower (Nemotron-TwoTower), representation-aligned conversion (REPR-ALIGN), SDAR and Stable-DiffCoder block-diffusion CPT | https://arxiv.org/abs/2512.15745 ; https://arxiv.org/abs/2608.00146 ; https://arxiv.org/abs/2606.26493 ; https://arxiv.org/abs/2605.06885 ; https://arxiv.org/abs/2601.15892 |
| Diffusion + MoE and refinement-aware routing | 30B-A3B from scratch on 23.5T tokens with scaling laws (LLaDA MoE v2); block-level expert routing (LLaDA2.2); progress-aware expert reallocation (REFLEX) | https://arxiv.org/abs/2608.03457 ; https://huggingface.co/inclusionAI/LLaDA2.2-flash ; https://arxiv.org/abs/2608.01784 |
| Speculative hybrids and mode switching | Diffusion drafts / AR verifies (DEER, DFlash, D²SD), single-network AR+diffusion+self-speculation (Nemotron tri-mode), trajectory-level speculation inside dLLMs | https://arxiv.org/abs/2512.15176 ; https://arxiv.org/abs/2602.06036 ; https://arxiv.org/abs/2606.04446 ; https://arxiv.org/abs/2607.05722 ; https://arxiv.org/abs/2608.27514 |
| Edit-based decoding and error-correction training | Token editing (LLaDA2.1), Levenshtein KEEP/SUBSTITUTE/DELETE/INSERT with agentic RL (LLaDA2.2), self-generated error training, consistency forcing, JSON format editor (DiffuAgent) | https://github.com/inclusionAI/LLaDA2.X ; https://arxiv.org/abs/2606.17175 ; https://arxiv.org/abs/2608.13925 ; https://arxiv.org/abs/2601.12979 |
| Variable-length and length-adaptive canvases | [expand]/[delete] tokens (DreamOn), entropy-valley length selection for MT, JS-verified canvas growth (CARVE), zero-shot cropping from prompt latents | https://arxiv.org/abs/2602.01326 ; https://arxiv.org/abs/2608.22274 ; https://arxiv.org/abs/2608.30922 ; https://arxiv.org/abs/2603.06123 |
| Generation order and the AR–diffusion ordering continuum | Learned ordering policy (SAS), any-order AR (A3), set diffusion, insertion/latent any-order inference, block/multi-block/adaptive-block decoding (BD3-LM, MBD, TDAR), commitment-order analysis | https://arxiv.org/abs/2606.23567 ; https://arxiv.org/abs/2601.13228 ; https://arxiv.org/abs/2607.01775 ; https://arxiv.org/abs/2607.26504 ; https://arxiv.org/abs/2606.29215 ; https://arxiv.org/abs/2602.09555 ; https://arxiv.org/abs/2608.05687 |
| dLLM agents and tool use | Peer-reviewed negative baselines and DiffuAgent (ACL 2026), matched-supervision speed study (DLLM Agent), tool-call-first decoding (DLLM-Searcher), agentic RL at 100B (LLaDA2.2), asynchronous-tool position paper (CID), commercial agent APIs (Mercury 2/2.5, DiffusionGemma function calling) | https://arxiv.org/abs/2601.12979 ; https://arxiv.org/abs/2602.07451 ; https://arxiv.org/abs/2602.07035 ; https://arxiv.org/abs/2608.10438 ; https://www.inceptionlabs.ai/blog/mercury-2-on-pinchbench |
| Serving and hardware characterization | Native vLLM support, dllm-plugin, CPU-bound batch-1 profile on H200, linear-attention retrofit, block-diffusion×Mamba prefix cache | https://vllm.ai/blog/2026-06-10-diffusion-gemma ; https://arxiv.org/abs/2608.23807 ; https://arxiv.org/abs/2608.06628 ; https://arxiv.org/abs/2607.02805 |
| Theory and limits of parallel sampling | Conditional total correlation / serial depth bounds; ParallelBench; 58-benchmark parallelism map | https://arxiv.org/abs/2608.25505 ; https://arxiv.org/abs/2510.04767 ; https://arxiv.org/abs/2601.15593 |

## Negative results, re-evaluations, retractions

- Commitment order: answer-first trajectories lower accuracy (F11).
- Robustness: no guaranteed defense from bidirectionality; systematic overconfidence (F16).
- Remasking self-correction: little-to-no benefit under standard settings; worsens
  diversity collapse (F25).
- Parallel decoding: dramatic degradation under strong dependencies (ParallelBench, ICLR
  2026); MDLMs lag AR across 58 benchmarks (F28).
- Agents: 0% multi-turn BFCL for 7–8B dLLMs; speed does not translate to success (F29).
- Distillation: conventional KD is marginal or harmful for dLLMs (F6).
- Soft-mask feedback: LERP fails geometrically (Lost in Interpolation).
- Vendor admissions: DiffusionGemma quality below Gemma 4 on all listed benchmarks and
  "diminishing returns under high-QPS" (F15); Gemini Diffusion still experimental and
  weaker on multilingual (F35); Artificial Analysis measures Mercury 2 at 684 tok/s vs the
  1,000+ first-party claim (F34).
- Retractions/withdrawals: none found (WebSearch "withdrawn OR retracted", arXiv version
  histories of the opened papers, OpenAlex). Coverage here is limited to titles and
  abstract pages.

## Open gaps (each was searched and came back empty or adjacent-only)

### G1. Controlled iso-wall-time dLLM-vs-AR comparison on agent tool-use tasks
- Why open: every reported wall-time win is batch-1, first-party, and either uses a
  different scaffold or gives the AR arm MTP (F1), or reports end-to-end speed without
  a matched-latency accuracy curve (F30). The serving paper (F5) shows 76% of batch-1
  wall-clock is CPU overhead, so no published comparison has charged it. No study fixes
  data, architecture family, verifier and p95 latency and then compares success.
- Evidence: arXiv Q8 (wall-clock/latency/throughput) rate-limited; OpenAlex GAP-A returned
  only F5 and a Cornell thesis; HF-papers "diffusion autoregressive latency wall-clock"
  returned only Nemotron-TwoTower and Nemotron tri-mode (first-party throughput, no agent
  tasks); WebSearch negative-result query returned only 2025 statements that dLLM
  inference is slower.
- Kevin advantage: the Docker/Slurm harness already specifies TTFT/TPOT/p50-p99, batch
  1/8/32, prefill/decode split and "total network evaluations for diffusion"; 8xH100 can
  host DiffusionGemma-26B-A4B (vLLM native) next to a Qwen3.5 AR sibling served the same
  way; Tinker gives matched LoRA on the AR arm. This is the kill-shot experiment for
  candidate #5 and for any dLLM direction.

### G2. Language-dependent serial depth of denoising
- Why open: F4 defines the quantity (conditional total correlation per reveal round) and
  F7 shows a large unexplained language-pair asymmetry (En→De recovers 33% of the oracle
  gap vs 65% for Zh); DiffusionGemma's MMMLU gap (81.5 vs 86.3) and Gemini Diffusion's
  "underperforms on multilingual" are reported without analysis. No paper measures
  tokens-per-step, steps-to-convergence or total correlation as a function of language or
  script with content held fixed, nor asks whether an ordering/sampler policy can be made
  invariant across translation-equivalent inputs.
- Evidence: OpenAlex GAP-B (multilingual + parallel decoding + denoising steps) returned
  only F7 and a PLoS ONE continuous-diffusion MT paper; HF-papers "multilingual diffusion
  language model" returned Diffutron (Turkish) and TTS work; arXiv Q9 rate-limited;
  WebSearch budget exhausted before the direct query.
- Kevin advantage: General Translation's parallel data supplies translation-equivalent
  prompt sets so language is the only varied factor; LLaDA-8B, LLaDA2.x-mini and
  DiffusionGemma run on one H100; ties to direction 18 (translation-equivariant
  boundaries). Architecture-level angle: a language-conditioned or language-invariant
  denoising schedule as a portable object, in the PorTAL spirit.

### G3. Bilingual joint-canvas dLLM trained on parallel corpora
- Why open: the only LLM-scale dLLM MT work found (F7) uses one LoRA adapter per
  direction on 200k pairs with the source as a clean prefix. No work trains a dLLM on a
  joint [source ; target] canvas where either side can be masked, so one model translates
  both ways, infills either side and can be evaluated for direction-symmetric parallelism.
  Classical iterative-refinement NAT (Mask-Predict, Levenshtein Transformer, 2019) is
  prior art for target-side refinement at small encoder-decoder scale and must be cited;
  those pages were not opened in this sweep.
- Evidence: OpenAlex GAP-C ("masked diffusion language model machine translation", 2026)
  returned nothing on-topic beyond F7; HF-papers "diffusion language model translation"
  returned F7, AR-Diffusion (2023) and vision work; arXiv Q6/Q9 rate-limited.
- Kevin advantage: production parallel corpora across many pairs; F7's recipe (8×H20, 200k
  pairs, 3 epochs) fits well inside 16 GPU-hours on 8xH100 for LoRA and inside the 100–150M
  pilot budget for a from-scratch bilingual canvas model. Risk: MT quality at 8B still
  trails AR on typologically distant pairs (F7).

### G4. Localized re-denoising of partially executed typed plans at equal wall time (candidate #5)
- Why open: no text-diffusion work repairs only the affected subgraph of a partially
  executed plan while holding executed nodes byte-identical and comparing against
  AR-replan-plus-verifier at matched p95 latency. The closest collisions are now
  LLaDA2.2's whole-sequence Levenshtein editing trained with tool-use rewards (F1),
  DiffuAgent's JSON editor (F29), DreamOn/CARVE insertion (F2), and 2023 continuous
  trajectory-diffusion replanning in robotics (NeurIPS 2023, adjacent domain).
- Evidence: WebSearch "diffusion language model plan repair replanning partial
  re-denoising" returned only the robotics paper, the Bitter Lesson and a PDDL
  orchestrator with deterministic repair; OpenAlex GAP-D returned nothing on-topic; arXiv
  GAP-D rate-limited.
- Kevin advantage: `experiments/architectures/bidirectional-plan-repair.yaml` already
  specifies the typed-DAG serializer, executed-node invariance and matched controls. New
  deltas required to survive the F1/F25 collisions: (i) locality mask over a typed DAG
  rather than a token sequence; (ii) AR+verifier control at matched wall time with CPU
  overhead charged (F5); (iii) start from a LLaDA2.x-mini/DiffusionGemma-class checkpoint,
  since 7–8B dLLMs score 0% on multi-turn BFCL (F29); (iv) show remasking benefit exists in
  this setting, which F25 says is not general.

### G5. Diffusion drafter specialised to tool-call structure (narrow)
- Why open: speculative hybrids draft free text (F32); OoO-Spec drafts tool-call slots
  with an AR sidecar (target-agnostic, trained once); nobody drafts the structured call
  with a dLLM whose parallel canvas matches the schema's slot structure.
- Evidence: OpenAlex GAP-E returned OoO-Spec, JetSpec, WhiFlash and generic surveys;
  HF-papers "diffusion agent tool" returned only dLLM-as-agent work.
- Kevin advantage: modest (AR targets via Tinker, drafters on H100). The portability angle
  is already taken by OoO-Spec, so this is an inference-systems move, not the
  architecture-level novelty Kevin wants. Listed for completeness; low priority.

## Implications for the existing candidate (directions/16-18, architectures/bidirectional-plan-repair.yaml)

- Keep the falsifiers; add the CPU-overhead charge from F5 and a batch-8 arm.
- Replace `llada-8b-base` as the primary arm with a LLaDA2.x-mini (16B) or
  DiffusionGemma-26B-A4B checkpoint; keep LLaDA-8B only as a scale ablation.
- Cite F1, F25, F29, F30 and the 2023 diffusion replanning paper in the novelty ledger.
- The "Diffusion plus MoE" rejection stands (F13).

## Exact queries run

arXiv export API (successful, 2): `all:"diffusion language model"` sorted by submittedDate
desc, 40 results; `all:LLaDA` sorted by submittedDate desc, 40 results.
arXiv export API (returned empty/HTTP 429, 14): `"speculative decoding" AND diffusion AND
language`; `"block diffusion" AND language`; `"any-order" AND autoregressive`;
`"non-autoregressive" AND translation`; `diffusion AND "language model" AND (agentic OR
"tool use" OR "tool calling" OR "function calling")`; `diffusion AND autoregressive AND
("wall-clock" OR latency OR throughput) AND "language model"`; `diffusion AND "language
model" AND ("machine translation" OR multilingual)`; `SDAR OR "LLaDA2.2" OR (Levenshtein
AND diffusion AND language)`; two `id_list` abstract batches (20 ids); four gap queries
(matched latency; multilingual denoising steps; "parallel corpus"; "plan repair" OR
replanning).
WebSearch (16): LLaDA 2.0 diffusion language model 2026; Inception Labs Mercury diffusion
LLM 2026 tokens per second; Gemini Diffusion 2026 benchmark speed; diffusion LLM agent
tool calling function calling 2026 arxiv; DiffusionGemma Google diffusion Gemma model
release; Dream 7B HKU diffusion language model 2026 update DreamOn Dream-Coder; diffusion
language model negative result "no speedup" OR "slower than autoregressive" equal compute
2026; Mercury 2 Inception Labs agentic coding diffusion model benchmark independent
evaluation; LLaDA2.2 "Levenshtein" editing agentic diffusion language model technical
report; Inception Labs Mercury 2.5 preview September 2026; SDAR diffusion language model
agent Search-R1 WebShop reinforcement learning 2026; Seed Diffusion ByteDance 2026
diffusion code model update; vLLM diffusion language model support dLLM serving 2026
release; diffusion language model paper withdrawn OR retracted OR "results do not hold"
2026; "any-order" autoregressive language model 2026 arxiv generation order; block
diffusion language model 2026 arxiv hybrid partial bidirectionality test-time scaling TDAR
multi-block; speculative decoding diffusion draft model autoregressive verifier hybrid
2026 arxiv lossless; diffusion language model machine translation 2026 arxiv multilingual
parallel decoding latency COMET; diffusion language model plan repair replanning agent
partial re-denoising executed actions 2026; Artificial Analysis Mercury 2 output speed
tokens per second measured independent diffusion. (Four further queries were refused when
the session's shared 200-search budget was exhausted: matched-latency comparison;
per-language denoising steps; bilingual joint canvas; natively length-aware.)
Hugging Face model search (11): LLaDA; Dream-v; dLLM; LLaDA2; Mercury (API error); SDAR;
Seed-Diffusion; DiffusionGemma; Dream-Coder; DiffuCoder; diffusion-llm.
Hugging Face papers search (6): diffusion language model translation; multilingual
diffusion language model; diffusion language model agent tool; diffusion autoregressive
latency wall-clock; DiffusionGemma Technical Report; OoO-Spec out-of-order speculation
tool calling. Plus 18 `api/papers/<id>` abstract lookups (6 not indexed).
GitHub (`gh search repos --sort updated`, 3): "diffusion language model"; "dLLM"; "block
diffusion language". `gh api` commits/readme on inclusionAI/LLaDA2.X, HKUNLP/Dream,
DreamLM/Dream and org repos, ML-GSAI/LLaDA, inclusionAI/dInfer, NVlabs/Fast-dLLM,
JetAstra/SDAR, vllm-project/dllm-plugin, SJTU-DENG-Lab/mbd-lms, LuLuLuyi/TDAR,
pc0618/block-diffusion-hybrids.
OpenAlex (5 searches, from_publication_date 2026-01-01): diffusion language model
autoregressive matched latency wall-clock; multilingual diffusion language model parallel
decoding denoising steps; masked diffusion language model machine translation; diffusion
language model agent plan repair replanning; speculative decoding diffusion draft tool
calling agent. Record lookups W7172558355, W7172558484.
DBLP (6): Bitter Lesson (ACL 2026 confirmed); DFlash (CoRR); Set Diffusion (CoRR);
Entropy-Valley, MBD, A3 (no JSON returned).
`ft search` (18, all zero on-topic hits): diffusion; LLaDA; Mercury; dLLM; parallel
decoding; Gemini Diffusion; non-autoregressive (FTS syntax error on hyphen); Inception
Labs; text diffusion; Dream 7B; masked diffusion; Mercury 2; Inception; LLaDA2;
DiffusionGemma; Gemma diffusion; diffusion model text; tokens per second.
Semantic Scholar (6 attempts, all HTTP 429). Jina reader (3 attempts, blocked: "bad
network reputation (AS7018)"). arXiv search HTML via WebFetch (3, HTTP 429).

## Coverage limits

- arXiv export API rate-limited after two queries (HTTP 429, empty bodies); 14 queries
  and 20 abstract ids failed; late in the session arxiv.org abstract and search pages also
  returned 429. Six August-2026 abstracts were therefore not opened: 2608.08791 (Unsure but
  Certain), 2608.20123 (nested SMC control), 2608.26374 (survival-guided length control),
  2608.25311 (prefix-denoising consistency), 2607.04206 (Sangam), 2607.17652 (FlowBlock).
- The session-wide WebSearch budget (200, shared across cells) ran out before the direct
  gap queries for G1–G3; those gaps rest on OpenAlex, HF-papers and the earlier WebSearch
  results only.
- Semantic Scholar unusable without an API key (429 on every call); Jina reader blocked
  for this network; DBLP returned JSON for only 3 of 6 lookups, so EMNLP 2026 / ICML 2026
  acceptances (Entropy-Valley, MBD, CARVE, DFlash, Set Diffusion) are the authors' own
  statements. Only the Bitter Lesson's ACL 2026 status is independently confirmed.
- Kevin's X bookmarks contain no diffusion-LM signal (18 queries, zero on-topic hits).
- Full PDFs were not read: LLaDA2.2 technical report (numbers from the model card),
  DiffusionGemma technical report (OpenAlex abstract), Mercury 2 (no report exists),
  DLLM Agent and Stable-DiffCoder result tables (abstract pages only).
- Speed numbers are first-party except Artificial Analysis for Mercury 2 and the vLLM
  blog for DiffusionGemma (a partner's measurement, not a neutral one).
- Not searched: Qwen/Kimi/GLM diffusion efforts by name; Chinese-language sources beyond
  the MBD Zhihu link; Reddit/HN; classical NAT literature (Mask-Predict, Levenshtein
  Transformer) that is prior art for G3.
- Where a summary tool (WebFetch) read a page, numbers were taken only when the tool
  quoted them; abstract pages rarely carry affiliations, so affiliations are given only
  when visible.
