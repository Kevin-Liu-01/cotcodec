# Sequence-operator frontier sweep (cell: seq-operators) — 2026-09-01

Scope: attention and sequence operators after the 2026-08-10 sweep, prioritising sources after 2026-06.
Focus list from the brief: Kimi K3 (KDA + AttnRes), FlashKDA, Gated DeltaNet successors, Qwen3.5/3.6/3.8
hybrid layouts, GLM-5.3, Nemotron-3.5, Mamba-3, log-linear attention, DSA/NSA/MoBA, multi-token
prediction, attention sinks, positional-encoding alternatives, hybrid-ratio and layer-placement studies.

Honesty notes. Every quantitative claim below was read in the primary source listed (arXiv abstract page or
HTML/PDF full text, Hugging Face `config.json`/README, GitHub README/benchmark file, or the X post itself).
"First-party" marks claims made by the lab that built the system and not independently replicated.
No claim of "completely novel" is made anywhere. Where a search came back empty the exact query is recorded.
Prior-sweep collisions: the 2026-08-10 program's Rejected table already excludes "better generic linear
attention" and "static attention/SSM mixture"; this sweep confirms both and additionally finds that the
ranked item "6. Budgeted Mixture of Sequence Operators" is now heavily occupied (see Occupied axis E).

---

## 1. Findings (primary source opened for each)

### A. Production hybrids and their exact layouts (from released configs and reports)

**F1. Kimi K3 technical report** — arXiv 2607.24653 (v1 2026-07-27, v2 2026-08-07), Kimi Team (402 authors); first-party.
https://arxiv.org/abs/2607.24653 · HF config: https://huggingface.co/moonshotai/Kimi-K3 (lastModified 2026-08-20)
- 2.8T total / 104B activated MoE, 1M context, 16 of 896 routed experts (Stable LatentMoE), 93 layers.
- Hybrid attention: each block = 3 KDA layers then 1 Gated MLA (3:1), plus an extra Gated MLA at the end of the backbone; config `kda_layers` (69) and `full_attn_layers` = [4,8,…,92,93] (24). Report Table 1: K2 61 MLA layers → K3 69 KDA + 24 MLA; total params 1.04T → 2.78T; activated 32.6B → 104.2B; hidden 7168 unchanged; context 128K → 1M; MTP 1 layer in both.
- KDA changes vs Kimi Linear: (i) *lower-bounded decay* so all causal tiles use dense tensor-core matmuls (Kimi Linear instead computed relative decay in log space); config `gate_lower_bound: -5.0`; (ii) output gate changed from low-rank to input-dependent *full-rank* projection; MLA also gets an input-dependent channel-wise full-rank output gate.
- Positional encoding: NoPE on all MLA layers; position is carried by KDA gating/decay; report states the model "extrapolates directly to 1M-token contexts without any positional-encoding modification".
- Depth: Block AttnRes with 8 blocks of 12 layers (9 sources counting the embedding).
- MTP: pretrained with one MTP layer mirroring a backbone block, later fine-tuned into an EAGLE-3-style draft. Released config reports `num_nextn_predict_layers: 0`.
- Scaling claim: held-out OOD scaling-law curves give "approximately 2.5×" overall scaling efficiency vs K2 (architecture + data + recipe jointly; no per-component attribution in the text I read). Cosine decay beat WSD in their scaling-law search.
- Occupies: production 3:1 linear/global hybrid with NoPE global layers, channel-wise delta rule, depth attention residual, MTP-as-draft.
- Relevance: the K3 stack (KDA-LB + full-rank gate, NoPE-MLA, Block AttnRes, MTP) has no open ≤1B from-scratch reference (see Gap G5); K3-style models are on Tinker (Kimi-K2.6, not K3) and Kimi-Linear-48B-A3B is pinned locally.

**F2. Attention Residuals (AttnRes)** — arXiv 2603.15031 (2026-03-16), Kimi Team; first-party tech report; code https://github.com/MoonshotAI/Attention-Residuals (pushed 2026-03-17).
https://arxiv.org/abs/2603.15031
- Replaces additive residual accumulation with softmax attention over preceding layer outputs using one learned pseudo-query per layer; Block AttnRes attends over N≈8 block summaries (O(Ld) → O(Nd)).
- Scaling law (fit L = A·C^−α): Baseline 1.891·C^−0.057, Full AttnRes 1.865·C^−0.057, Block AttnRes 1.870·C^−0.058; Block AttnRes matches a baseline trained with 1.25× more compute (1.692 vs 1.714 at the largest plotted budget).
- Table 2 vs mHC(-lite), validation loss at 194M/38.7B tokens: baseline 1.931, Block 1.909, Full 1.899, mHC-lite 1.906; at 436M/87.9B: 1.766 / 1.746 / 1.737 / 1.747 (first-party single runs).
- Integrated into Kimi Linear 48B-A3B (Block AttnRes, 6 layers per block → 9 blocks + embedding) pretrained on 1.4T tokens (4096 ctx, Muon, WSD); inference latency overhead <2%, pipeline-parallel overhead <4%.
- Occupies: depth-axis selective read (see also F12 for the Qwen comparison).

**F3. On the Design of Qwen3.8-Next Architecture** — arXiv 2608.30320 (2026-08-31), Qwen Team; first-party.
https://arxiv.org/abs/2608.30320 · model card https://huggingface.co/Qwen/Qwen3.8-Flash-Next (released 2026-08-26)
- Qwen3.8-Flash-Next: 125B total / 6B active MoE + 51B n-gram embedding tables held off-accelerator (+4B MTP per card). Leads the 397B-A17B predecessor on 8 of 14 pretraining benchmarks, trails by ≤2.6 points, at 1/3 active params, 1/3 tokens, ~1/9 FLOPs.
- Layout (config): 48 layers, `full_attention_interval: 4`, layer_types 36 linear_attention / 12 full_attention; card: "12 × (3 × (Gated DeltaNet → MoE) → 1 × (Qwen Sparse Attention → MoE))"; GDN 16 key heads × 128, 48 value heads × 128, conv 4; 512 experts top-10; attention 24 q heads / 2 KV heads, head_dim 256, partial_rotary_factor 0.25; MTP 1 layer (full_attention type, hybrid); indexer budget 2048, compress ratio 4, MQA indexer 4 q heads + 1 shared key head, dim 128.
- Architecture ablation (Table 1; 28-layer 25B-A3B, 400B tokens @4K + 80B @32K; one full-attention layer in four; SWA window 128): 9-benchmark average full attention 49.87, SWA hybrid 51.15, GDN hybrid 53.81 (GDN hybrid beats Transformer on 8/9, SWA hybrid on 7/9). MMMLU (the only multilingual number): 47.74 / 51.33 / 54.83.
- Positional encoding: RoPE kept in full-attention layers because "RoPE and a NoPE variant … show little difference during pretraining, but the NoPE variant exhibits a substantially higher rate of endless generation after post-training". (Contrast with F1/F14 NoPE at scale.)
- GDN details: sigmoid output gate beats SiLU; zero-centered RMSNorm everywhere; FlashQLA kernels.
- QSA: full-attention layers are replaced by micro-block sparse attention with a compressed learned indexer at continued-pretraining time; final QSA stage 8,000 steps × 256K-token sequences ≈ 200B tokens; QSA vs full attention on 8 short benchmarks avg 75.9 → 76.8; RULER 512K–1M 90.08 → 93.00; 8-needle MRCR 512K 30.66 → 40.53, 1M 20.71 → 26.44; 35B-A3B ablation: QSA matches full attention at relative indexer latency 0.25 while IndexShare stays below baseline at 0.5; reusing QSA top-k indices across MTP steps leaves mean accepted length unchanged (4.06 vs 4.07).
- Residual (Table 5; 25B-A3B, 560B tokens; loss / 9-bench avg): pre-norm 1.617 / 50.91; mHC static 1.596 / 52.49; mHC dynamic 1.594 / 54.47; Gated Residual 1.590 / 54.66. Table 6: pre-norm 1.789; Block AttnRes 1.773 and 1.770 (two block sizes); Full AttnRes 1.762; GR 1.762 — "Full AttnRes … lands level with GR". Branch analysis: one of four branches preserves early attention outputs across many layers; restricting to the two highest-gated branches is "almost free in pre-training loss yet degrades with further training".
- Stability: with Muon the production run had no loss spike and no qk-clip/SwiGLU-clip; AdamW baseline spikes under stress tests.
- Explicit loss-vs-benchmark disagreements are reported (n-gram vocab lowers loss monotonically while accuracy saturates; dynamic gates give small loss gain but +1.98 benchmark points).
- Occupies: hybrid ratio choice (1-in-4), sparse global layer with compressed indexer, widened gated residual, MTP index reuse.

**F4. Qwen3.8-27B and Qwen3.5 small hybrids (configs)** — Hugging Face official repos; first-party artifacts.
https://huggingface.co/Qwen/Qwen3.8-27B (2026-08-14) · https://huggingface.co/Qwen/Qwen3.5-0.8B · https://huggingface.co/Qwen/Qwen3.5-4B · https://huggingface.co/Qwen/Qwen3.5-9B-Base
- Qwen3.8-27B: dense, 64 layers = 48 linear_attention + 16 full_attention (interval 4), hidden 5120, MTP 1 layer, partial rotary 0.25, 256K context.
- Qwen3.5-0.8B: 24 layers = 18 GDN + 6 full attention; 4B: 32 = 24 + 8; 9B-Base: 32 = 24 + 8; all interval 4, MTP 1 layer, rope_theta 1e7, mRoPE interleaved.
- Relevance: open GDN-hybrid checkpoints exist from 0.8B upward (also on Tinker: Qwen3.5-4B/9B/9B-Base/35B-A3B-Base, Qwen3.8-27B). Any retrofit or post-training experiment on hybrids has a substrate; from-scratch pilots can copy these exact layouts.

**F5. GLM-5.3-Flash card + config** — https://huggingface.co/zai-org/GLM-5.3-Flash (lastModified 2026-08-31; blog https://z.ai/blog/glm-5.3-flash is JS-only and could not be read); first-party.
- Card: 320B total / 18B active, first natively multimodal GLM-5 model, "for the first time in the GLM series … a hybrid architecture combining sparse and linear attention", plus Manifold-Constrained Hyper-Connections (mHC), 30T-token corpus. Cites the GLM-5 report (arXiv 2602.15763, 2026-02-17) which covers DSA but predates the hybrid.
- Config (`glm5_next`): 45 layers; `linear_attn_config.kda_layers` = 34 layers, `full_attn_layers` = [3,7,11,…,43] (11 layers, every fourth); layer_types = linear_attention / deepseek_sparse_attention; linear layers: 64 heads × 128, short conv 4, `gate_lower_bound -5.0` (KDA parameterisation); DSA: `index_topk 2048`, `index_kpool 4` (IndexPool compression of indexer keys), 32 indexer heads × 128; `qk_rope_head_dim 0` for the sparse layers (no RoPE dims); `mhc: true`, `hc_sinkhorn_iters 20`; 288 routed experts top-8 + 1 shared; MLP dense for first 3 layers; `num_nextn_predict_layers 1`; 1,048,576 max positions.
- Occupies: KDA-style linear + DSA sparse hybrid at 3:1 with mHC — a third independent lab converging on 3 linear : 1 global.

**F6. GLM-5.3 (non-Flash) config** — https://huggingface.co/zai-org/GLM-5.3 (lastModified 2026-08-31); first-party artifact.
- `glm_moe_dsa`, 78 layers all DSA (no linear layers), `index_topk 2048`, `index_topk_freq 4`, indexer_types 21 "full" / 57 "shared" (indexer computed every 4th layer and shared), MTP 1, 256 routed experts top-8, rope_theta 8e6, 1M positions.
- Occupies: cross-layer indexer sharing in production (cf. LongCat LSA F20, Qwen's IndexShare baseline in F3).

**F7. DeepSeek-V4** — arXiv 2606.19348 (2026-04-26), DeepSeek-AI (319 authors); first-party.
https://arxiv.org/abs/2606.19348
- Hybrid of Compressed Sparse Attention (CSA: KV compressed 4× along sequence, FP4 lightning indexer selects top-k compressed entries, shared-KV MQA) and Heavily Compressed Attention (HCA: 128× compression, dense over compressed entries); both add a sliding-window branch (window 128) and *learnable per-head sink logits added to the softmax denominator*; partial RoPE on the last 64 dims of queries and KV entries, also applied to outputs to keep relative position; mHC (expansion 4, 20 Sinkhorn iterations); MTP depth 1; Muon.
- V4-Flash: 43 layers, hidden 4096, first two layers pure SWA then CSA/HCA interleaved, top-k 512, 256 routed experts top-6, 284B-A13B. V4-Pro: 61 layers, hidden 7168, first two HCA, top-k 1024, 384 routed experts, 1.6T-A49B. >32T pretraining tokens.
- Occupies: compressed + sparse global attention, learned sinks, mHC, partial RoPE.

**F8. NVIDIA Nemotron 3.5 Lightning 30B-A3B** — model cards https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16 and …-Base-BF16 (release date 2026-08-11); first-party cards; no separate technical report located.
- `NemotronHForCausalLM`, 52 layers = 23 Mamba-2 + 23 MoE + 6 attention (GQA, 32 q heads / 2 KV heads, head_dim 128); hidden 2688; Mamba head dim 64, state 128, 8 groups, conv 4; 128 routed experts + 1 shared, top-6; MTP block types [attention, moe], `num_nextn_predict_layers 1`; MTP trained in a dedicated continued-pretraining stage; NVFP4 pretraining recipe; >20T tokens; card claims 1M context (config max_position 262144).
- Occupies: Mamba-2 hybrid MoE with MTP at 30B-A3B; also the smallest official hybrid MoE on Tinker (Nemotron-3.5-Lightning-30B-A3B is in Kevin's Tinker list).

**F9. Solar Open 2** — arXiv 2607.20062 (2026-07-22), Upstage; first-party report.
https://arxiv.org/abs/2607.20062
- 250B-A15B; 1M context via "one softmax layer among every three linear-attention layers, using no positional encoding and a gated delta rule extended to negative eigenvalues"; initialised from Solar Open 1.
- Occupies: another 3:1 NoPE hybrid and negative-eigenvalue delta rule in production.

**F10. MiMo-V2-Flash** — arXiv 2601.02780 (2026-01-06), Xiaomi; first-party. https://arxiv.org/abs/2601.02780
- 309B-A15B; SWA (128-token window) interleaved with global attention at 5:1; pretrained with MTP on 27T tokens.
- Occupies: SWA/global hybrid ratio 5:1 with MTP (contrast with GDN hybrids; Qwen's Table 1 shows GDN hybrid > SWA hybrid at 25B-A3B).

### B. Kernels and small open checkpoints (feasibility)

**F11. FlashKDA** — GitHub https://github.com/MoonshotAI/FlashKDA (README; BENCHMARK_H20.md generated 2026-04-22; X post 2026-07-27 in Kevin's bookmarks: https://x.com/Kimi_Moonshot/status/2081762799202746420); first-party.
- CUTLASS KDA kernels, SM90+, CUDA ≥12.9; auto-dispatched from `flash-linear-attention ≥0.5.0` `chunk_kda` **under `torch.inference_mode()` only** (forward path).
- H20, T=8192, H=96, D=128: 1.85× (fixed) / 2.06× / 2.29× (varlen) vs fla `chunk_kda`; 1.22× / 1.30× / 1.43× vs fla `chunk_gated_delta_rule`. H=64: 1.95× / 1.91× / 2.31× and 1.24× / 1.17× / 1.40×. X post: "1.72×–2.22× prefill speedup over the flash-linear-attention baseline on H20".
- FlashQLA (QwenLM, TileLang) README: 2–3× forward and 2× backward over fla Triton GDN on Hopper/Blackwell; fla GDN backend since 2026-07 (v0.1.2).
- fla releases: v0.5.1 (2026-06-18) adds Mamba3, AttnRes operator (+ fused RMSNorm), YOCO; v0.5.2 (2026-07-27) adds NSA cached inference, a sparse-attention design-space note, DSA naive reference, Gluon backend for AttnRes, a Mamba-3 decay fix (PR #1012), FlashQLA dispatch. README news: GDN-2 (2026-05), Preconditioned GDN/KDA (2026-06), context parallel for KDA/GDN (2026-03).
- Relevance: training-side kernels for GDN/KDA/GDN-2/Mamba-3/AttnRes exist in one library; 8×H100 pretraining of 0.1–1.5B hybrids is kernel-feasible today. FlashKDA speeds only inference.

**F12. Mamba-3 and released checkpoints** — arXiv 2603.15569 (2026-03-16; ICLR 2026, peer-reviewed), Lahoti, Li, Chen, Wang, Bick, Kolter, Dao, Gu. https://arxiv.org/abs/2603.15569 · https://huggingface.co/state-spaces/mamba3-siso-1.5b (2026-07-28)
- Three changes: a more expressive discretisation-derived recurrence, complex-valued state update for state tracking, and a MIMO formulation "without increasing decode latency"; claims gains on retrieval, state tracking and downstream LM (numbers not verified here).
- Checkpoints: mamba3-siso-187m/443m/893m/1.5b and mamba3-mimo-894m; the 1.5B card: 24 layers, d=2048, state 128, head dim 64, 64 heads, no MIMO, chunk 64, 2K context, 100B FineWeb-Edu tokens, Llama-3.1-8B tokenizer, BF16.
- Negative result on edge efficiency: *The Hyperscale Lottery* (arXiv 2604.07935, 2026-04-09, ECML-PKDD ITEM workshop) reports Mamba-3's changes add 28% latency at 880M and 48% at 15M parameters on edge hardware.
- Occupies: SSM line with retrieval/state-tracking improvements; attention-free 0.2–1.5B checkpoints available for controls.

**F13. Small open hybrid checkpoints (third-party)** — https://huggingface.co/startlux-models/gdn-1.3b-isp-hybrid-3to1-50b (2026-08-13; config: 24-layer GDN with attention at layers [2,5,…,23], 8 heads × 256, 50B tokens; companions at 340M/10B tokens) released with F19; https://huggingface.co/Ethangou/attention-residuals-0.6B-full (2026-04-27; Qwen3-style dense AttnRes 28 layers, from scratch on Chinese FineWeb-Edu) and 100M variants; https://huggingface.co/jaisidhsingh/SignedKDA-kda (2026-08-24; pure KDA, 28 layers, hidden 768, no card); https://huggingface.co/shiershuihesaixiliya/qingyi-kda-0.6b (conversion, F24); 72 open models at 340M/20B and 1.3B/100B tokens across six linear variants × five hybrid ratios from *A Systematic Analysis of Hybrid Linear Attention* (arXiv 2507.06457, v2 2026-06-24).
- Relevance: GDN hybrids and dense AttnRes exist as small open artifacts; no combined K3-style stack was found (Gap G5).

### C. Delta-rule successors

**F14. Gated DeltaNet-2** — arXiv 2605.22791 (2026-05-21), Hatamizadeh, Choi, Kautz (NVIDIA tech report); in fla since 2026-05. https://arxiv.org/abs/2605.22791
- Separates the scalar tie between erase and write: channel-wise erase gate b_t and write gate w_t; reduces to KDA when both collapse to one scalar and to GDN when decay also collapses; chunkwise WY algorithm with asymmetric erase factors.
- Occupies: the "one more gate" axis of the delta rule. Independent third-party comparison at 350M (F16) places KDA+Muon lowest in loss within its sweep.

**F15. Post-GDN-2 delta-rule variants (2026)** — the design space is dense: QED query-derived second erase direction (arXiv 2608.13668, 2026-08-13; "about doubles the usable context length on S-NIAH-1"); FG²-GDN channel-wise β and decoupled key/value scaling (2604.19021, v3 2026-08-31); CARVE content-aware key-axis gating with megakernel (2606.27229); Preconditioned DeltaNet/KDA (2604.21100, 2026-04-22; in fla); Q-Delta query-aware delta rule (2606.08804, ICML 2026); Curvature-Conditioned Query read-side contraction (2606.01294, EMNLP 2026); Bayesian Layer covariance-propagating design model (2605.31163); Sparse Delta Memory with sparse addressing into a large explicit memory, Meta (2607.07386, 2026-07-08); KATA symmetric-cone feature maps (2607.17419); Semidirect Fourier Delta Attention with complex block-rotational decay (2607.11897); Solar Open 2 negative eigenvalues (F9).
- URL for the structured record: https://arxiv.org/abs/2608.13668
- Occupies: erase/write/read/decay factorisations, curvature/preconditioning, state sparsification, complex/negative eigenvalues. Kevin's prior "Coded Delta Memory" (fixed 4+2 parity shards with syndrome-guided correction) is not among these; no coding-theoretic state protection was seen in this sweep (searched "delta rule" 2026 listings; adjacent only: SDM sparse addressing, Bayesian covariance).

**F16. Linear Attention Architectures: Mechanisms, Trade-offs, and Cross-Layer Routing** — arXiv 2607.07953 (2026-07-08), Cerruti et al.; third-party, code released. https://arxiv.org/abs/2607.07953
- Common recurrent-memory notation for DeltaNet, GDN, KDA, GDN-2; 350M / 15B-token sweep with optimizer comparisons, hybrid-vs-pure stacks, 1.3B and 3B DeltaNet runs; within the sweep KDA with Muon reaches the lowest validation loss, pure GDN with AdamW the highest normalised training throughput; no inference-speed benchmark.
- Relevance: the closest existing independent 350M bake-off; Kevin's 8×H100 can extend it (seeds, GDN-2 vs KDA-LB, cross-lingual data).

### D. Hybrid ratio, placement, component roles

**F17. Rethinking the Role of Efficient Attention in Hybrid Architectures** — arXiv 2606.15378 (2026-06-13), Qiao et al.; third-party. https://arxiv.org/abs/2606.15378
- Efficient-attention design "primarily affects how fast long-context capability emerges, while different hybrids eventually converge to comparable long-context performance under sufficient training"; long-range retrieval is carried by full attention; *Large-Window Laziness*: larger SWA windows delay retrieval-head formation; NoPE applied only to the full-attention layers of a small-window SWA hybrid improves long context.
- Partial negative for operator-choice claims at convergence; supports "placement + PE of the global layers" as the live variable.

**F18. Morphing into Hybrid Attention Models (FlashMorph)** — arXiv 2606.30562 (2026-06-29). https://arxiv.org/abs/2606.30562
- Layer selection for Transformer→hybrid conversion cast as budget-constrained subset optimisation; morphable model with a linear branch per layer; frozen weights; layerwise gates optimised on synthetic long-context retrieval with a linearisation regulariser; gates discretised under a preset full-attention budget.
- Related occupancy: NAtS-L token-level routing between linear and softmax within a layer (2602.03681, v2 2026-06-02); Mixture of Layers with one shared softmax block + GDN in routed thin blocks (2605.09516); HydraHead head-level FA/LA hybridisation (2606.20097); Super Apriel 15B supernet with FA/SWA/KDA/GDN per layer switchable at serving, 2.9–10.7× decode throughput at 96–77% quality retention (2604.19877, 2026-04-21); KL-guided layer selection (2512.20569); Component Ablation on Qwen3.5-0.8B and Falcon-H1-0.5B showing position-dependent component importance (2603.22473, v2 2026-06-05).
- Collision: the 2026-08-10 program's item 6 (Budgeted Mixture of Sequence Operators) is now occupied on the layer axis (FlashMorph, KL-guided), token axis (NAtS-L), head axis (HydraHead), block axis (MoL) and serving-time axis (Super Apriel). Only counterfactual per-operator utility training remains un-taken, and 2606.15378 suggests convergence washes out much of the gain.

**F19. Massive Activations in Hybrid Linear Attention LLMs** — arXiv 2608.12149 (2026-08-12, v2 08-24), Su et al.; third-party with released checkpoints (F13). https://arxiv.org/abs/2608.12149
- Massive activations spike immediately before full-attention layers (pre-attention spikes) and persist through linear layers (inter-spike plateaus); established across five linear architectures, six hybridisation configs, five data domains, open hybrids 1.2B–397B; controlled GDN hybrids up to 1.3B show both morphologies emerge early and respond asymmetrically to output gating.
- Occupies: sink/outlier phenomenology in hybrids (removes an earlier candidate gap).

### E. Sparse attention

**F20. LongCat Sparse Attention** — arXiv 2608.01662 (2026-08-03, v2 08-04), Meituan; first-party. https://arxiv.org/abs/2608.01662
- Streaming-aware indexing (hardware-aligned KV layouts), cross-layer indexing (one layer's indices reused across consecutive layers with cross-layer distillation), hierarchical coarse-to-fine scoring; scaling experiments 69B-A3B to 560B-A27B "on par with full attention".
- Adjacent: PIVOT query-group indexing, training-free DSA indexer replacement (2607.24593, 2026-07-27); MiniCPM-SALA 9B sparse (InfLLM-V2) + linear (Lightning) at 1:3 with HyPE (2602.11761, 2026-02-12); HySparse oracle token selection from the preceding full-attention layer with KV sharing, 80B MoE with 5 of 49 full-attention layers (2602.03560); Gated Sparse Attention 1.7B/400B tokens (2601.15305); FlashMemory-DeepSeek-V4 lookahead sparse attention, KV footprint 13.5% (2606.09079).
- fla design note (GitHub `fla/ops/dsa/README.md`, first-party docs): natively-trainable sparse attention is a 2×2 of granularity {token, block} × scoring proxy {pooled keys, learned indexer}: NSA/MoBA = block/pooled; MSA = block/indexer; DSA = token/indexer; QSA (F3) adds micro-block + compressed indexer; CSA (F7) adds sequence compression before token-level top-k.
- Occupies: indexer design, sharing, granularity; sparse+linear hybrids.

### F. Multi-token prediction

**F21. AdaMTP** — arXiv 2608.00434 (2026-08-01), Cui et al. https://arxiv.org/abs/2608.00434
- Entropy-based segmentation assigns each token an adaptive prediction depth; masked MTP loss suppresses predictions across high-entropy boundaries (claimed to reduce gradient interference with the backbone).
- Adjacent 2026 MTP work: LoopMTP aligns loop-t hidden state with the token t steps ahead, up to +8.1% relative accuracy, stable to 15 loops (2608.03624); Hierarchical Latent Prediction (2608.05806); MTP-D self-distillation +7.5% acceptance and looped head extension (2603.23911); production: one MTP layer in K3, Qwen3.8 (with QSA index reuse), DeepSeek-V4, GLM-5.3, Nemotron 3.5, Motif 3 (2608.09119), MiMo-V2-Flash, Nemotron 3 Ultra (2606.15007).
- Occupies: MTP as default head and MTP objective shaping.

**F22. Windowed-MTP** — arXiv 2607.21535 (2026-07-23), single author. https://arxiv.org/abs/2607.21535
- At million-token context the MTP draft head's full-attention read grows linearly and can make speculation net-negative; "sharpens under hybrid/linear-attention targets, where cheaper verification leaves the draft's full-attention read exposed"; fix: StreamingLLM-style window + sink on the draft only, lossless by construction.
- Negative/systems finding relevant to any hybrid + MTP design at long context.

### G. Attention sinks and positional encoding

**F23. Attention-sink mechanisms** — *A Unifying View of Attention Sinks: Two Algorithms, Two Solutions*, arXiv 2606.08105 (2026-06-06): sinks implement either adaptive no-op (gating fixes it) or broadcast (registers fix it), with distinct diagnostics (negligible value norms vs low-rank outputs). https://arxiv.org/abs/2606.08105
- Companions: *What Makes Position Zero Special?* (2603.06591, v2 2026-08-03) identifies a two-block P0-sink circuit and shows two parameter-free methods that accelerate sink formation improve from-scratch pretraining, comparable to Gated Attention; Qwen's *A Unified View of Attention and Residual Sinks* (2601.22966, 2026-01-30) frames sinks as outlier-driven rescaling that normalisation needs; *Where does Absolute Position come from* (2606.06160) traces absolute-position leakage to the causal-mask denominator and the BOS residual trajectory; Hybrid Gated Attention adds learnable sinks and multi-source gates (2608.11805, 2026-08-12); DeepSeek-V4 ships learnable per-head sink logits (F7).
- Occupies: sink mechanism, learned sinks, gating.

**F24. Positional encoding alternatives (2026)** — *Why Do Accumulated Transformations Extrapolate?* arXiv 2606.24975 (2026-06-23): proves accumulated orthogonal transformations (PaTH-like) become incoherent after finitely many steps, creating a finite mixing window that extrapolates then degrades. https://arxiv.org/abs/2606.24975
- Companions: Möbius/anti-periodic RoPE on 25% of heads, 48 models at 160M/410M with 6 seeds, NIAH 90.3±5.7% vs 63.3±31.4% at unchanged perplexity (2607.21405, 2026-07-23); Random Float Sampling positions (2602.14050, EACL 2026); Randomized YaRN (2606.23687, EMNLP 2026 Findings); Jet-Long bifocal RoPE (2607.07740); "Relative Positions Generalize, Absolute Positions Memorize" implicit-bias account (2607.18759); sliding-window transformers without PE remain Turing complete (2606.01532); HyPE hybrid PE in HALO/HypeNet (2601.22156) and MiniCPM-SALA.
- Occupies: RoPE variants, data-dependent rotations, NoPE theory. The NoPE-in-hybrids disagreement (F1/F9 vs F3 vs F17) is not resolved by any of these (Gap G3).

**F25. Cracks in the Foundation** — arXiv 2608.10296 (2026-08-10; COLM 2026, peer-reviewed), Bertsch, Soldaini, Gormley, Neubig. https://arxiv.org/abs/2608.10296
- Four minor dense-Transformer choices (normalisation, GQA, pretraining context length, sliding-window attention), each made by Olmo/Llama/Qwen, compound to up to −47% downstream long-context performance; undetectable from short-context loss; detectable by applying context extension early in pretraining; OlmPool = 26 comparable 7B models, >170,000 GPU-hours.
- Negative/cautionary: short-context loss is not a proxy for long-context extensibility — any hybrid pilot needs early extension probes.

### H. Conversion and negative results

**F26. Stuck on "A": Interface Injury in Attention-to-KDA Linearization of a 0.6B model** — arXiv 2608.02689 (2026-08-03), single author, code https://github.com/Sisyphbaous-DT-Project/open-qingyi. https://arxiv.org/abs/2608.02689
- 21 of 28 layers of Qwen3-0.6B-Base converted to KDA on one 32 GB GPU with tens of millions of tokens; hidden-state alignment cuts CE 9.48 → 4.13 while C-Eval stays at 25%; end-to-end KL closes validation CE to +0.128 nats yet accuracy is 28.8% vs teacher 50.6%; four-permutation diagnostic shows label stickiness ("A" 81%); a 1,000-step format-targeted KL stage recovers +12.48 C-Eval; reports an FP32-master failure mode where bf16 optimizer updates are swallowed.
- Companion negative: *When Perplexity Lies* / GenDistill (2603.26556, v2 2026-07-17): a 7B distilled hybrid within 0.2 pp of teacher under log-likelihood scoring is −20.8 pp when it must generate. Conversion recipes: Taylor-Calibrate initialisation for GDN students (2606.16429), HALO/HypeNet (2601.22156), distillation to hybrid xLSTM (2603.15590).
- Relevance: Kevin has Qwen3-0.6B-Base pinned; any conversion pilot must use generation-based evaluation and the exact-match/permutation controls already required by the CoTCodec evaluation contract.

**F27. Component-Aware Self-Speculative Decoding in Hybrid LMs** — arXiv 2605.01106 (2026-05-01). https://arxiv.org/abs/2605.01106
- Using the SSM/linear subgraph as an internal draft works for parallel hybrids (Falcon-H1: acceptance α=0.68 at k=2) but not for sequential interleaved hybrids (Qwen3.5: α=0.038).
- Negative result: in 3:1 interleaved hybrids the linear layers alone do not approximate the model's next-token distribution.

**F28. Serving-side consequences of recurrent state (Aug 2026)** — DAMP, arXiv 2608.27513 (2026-08-27): uniform INT8/FP8 quantisation of GDN/KDA recurrent states already degrades complex reasoning, INT4/NVFP4 collapse it to near zero; error energy concentrates in few channels whose decay-based persistence is stable across prompts. https://arxiv.org/abs/2608.27513
- Companions: DASC retention-horizon state compression for prefix caching (2608.30386, 2026-08-31); Tail-Replay approximating a prefix's recurrent state by replaying a short suffix (2608.30310); TreeWY snapshot-free speculative verification for GDN hybrids (2608.20961); HYPIC position-independent caching for hybrids (2607.01299); HARTS RL over rollout trees for hybrid-attention models (2608.28158, 2026-08-28); SANE tanh state compression at chunk boundaries keeps RWKV-7 functional after a 100M-token prefix (2608.22354).
- Relevance: state channels have heterogeneous retention horizons and precision sensitivity — a measurable substrate for any "state hygiene" experiment, and a warning that recurrent-state quantisation is not free.

**F29. Auditable deletion from KDA memory — negative** — arXiv 2607.27539 (v2 2026-08-13), single author. https://arxiv.org/abs/2607.27539
- Native KDA gives a negative result for the tested deletion-receipt interface: the corpus-pooled raw recurrent contribution changes by 12–49% with the suffix and 8–49% after a decay-ledger correction; checkpoint replay is the only verified path. Constructive part retrofits a support-vector memory into frozen Gemma 3 (1.85% perplexity overhead at 4B).
- Relevance to the prior program's memory-deletion interest: exact deletion is not addressable in native delta-rule state without replay.

### I. Methodology at academic scale

**F30. Physics of Language Models 4.1 — Canon layers** — arXiv 2512.17351 (v2 2026-07-28 adds GDN experiments; NeurIPS 2025 v1). https://arxiv.org/abs/2512.17351
- Controlled synthetic pretraining isolates capabilities at academic scale (1.3B/100B tokens is "dominated by noise"); Canon layers (weighted sums of nearby token representations) lift weak architectures and compose with linear attention/SSMs.
- Relevance: the recommended methodology for any 0.1–1B operator claim — synthetic capability probes plus real-data loss, not either alone (consistent with F3's loss-vs-benchmark disagreements and F25).

---

## 2. Occupied-axes table

| # | Axis | What is taken (primary evidence) | Remaining opening at 0.1–8B |
|---|---|---|---|
| A | Layer-wise linear/global hybrid at a fixed ratio | 3:1 in K3 (69 KDA + 24 MLA), Qwen3.5/3.8 (interval 4), GLM-5.3-Flash (34 KDA-style + 11 DSA), Solar Open 2 (3:1 NoPE); Nemotron 3.5 (23 Mamba-2 / 6 attention); MiMo-V2-Flash SWA 5:1; ratio sweeps in 2507.06457 (72 models); component roles in 2603.22473; convergence result 2606.15378 | Ratio is settled around 1-in-4; what is not settled is *which* capabilities the ratio trades across languages/scripts (Gap G1) |
| B | Global layer → sparse/compressed attention with learned indexer | DSA (GLM-5.x, DeepSeek-V3.2), QSA micro-block + compressed indexer (Qwen3.8), CSA/HCA (DeepSeek-V4), LongCat LSA cross-layer/hierarchical, GLM-5.3 shared indexers, MiniCPM-SALA, HySparse, MSA; fla 2×2 design note | Cross-lingual behaviour of learned indexers untested (Gap G6) |
| C | Delta-rule gate/erase/write/read factorisation | KDA-LB + full-rank gate, GDN-2, FG²-GDN, QED, CARVE, Preconditioned DeltaNet, Q-Delta, CCQ, Bayesian Layer, SDM, KATA, SFDA, negative eigenvalues (Solar Open 2) | Generic new gates: closed. Coding-theoretic state protection not seen (prior-program Coded Delta Memory still unclaimed but must be tested against SDM/Bayesian-layer baselines) |
| D | Residual stream / depth-axis operators | AttnRes + Block AttnRes (Kimi), RD-AttnRes, HC/mHC/xHC/TEMPER/go-mHC, Qwen Gated Residual, mHC in DeepSeek-V4, GLM-5.3-Flash, Motif 3; stream-collapse diagnosis (2606.03483) | Independent iso-compute multi-seed comparison at ≤1B absent (Gap G2) |
| E | Learned / dynamic operator placement or routing | FlashMorph (layer gates under budget), NAtS-L (token), HydraHead (head), MoL (block), Super Apriel (per-layer FA/SWA/KDA/GDN supernet at serving), KL-guided selection | Prior program item 6 is largely occupied; only counterfactual per-operator-utility training is untaken, and 2606.15378 lowers the expected ceiling |
| F | Positional encoding in hybrids | NoPE global layers (Kimi Linear, K3, Solar Open 2); RoPE kept by Qwen3.8 after NoPE termination failures; partial RoPE 0.25 (Qwen3.5), partial RoPE 64 dims (DeepSeek-V4); HyPE; PaTH theory; Möbius RoPE; RFS; Randomized YaRN | The NoPE-hybrid disagreement has no mechanistic small-scale study (Gap G3) |
| G | Attention sinks / massive activations | Learned sink logits (DeepSeek-V4, HyGA), gated attention (Qwen), nop-vs-broadcast theory, P0-sink circuit, outlier-driven rescaling, massive activations in hybrids up to 397B | Largely closed as a phenomenology axis |
| H | Multi-token prediction | 1 MTP layer standard (K3, Qwen3.5/3.8, DeepSeek-V4, GLM-5.3, Nemotron 3.5, Motif 3, MiMo-V2-Flash); AdaMTP, LoopMTP, HiLP, MTP-D; Windowed-MTP and TreeWY caveats for hybrids | Controlled MTP ablation on ≤1B linear/hybrid backbones absent (Gap G4) |
| I | Transformer → hybrid conversion | HALO/HypeNet, Taylor-Calibrate, KL-guided selection, FlashMorph, GenDistill, xLSTM distillation; negatives: Stuck-on-A, When Perplexity Lies | Recipes exist; generation-based evaluation is the live requirement, not a new method |
| J | Hybrid serving and RL systems | DASC, DAMP, Tail-Replay, HYPIC, TreeWY, HARTS, component-aware self-spec (negative for sequential hybrids) | Systems, not architecture; useful as measurement substrate |

## 3. Open gaps (each was searched; evidence recorded)

**G1. Script/language-controlled evaluation of hybrid recurrent-state recall and ratio.**
- Why open: every production hybrid reports one multilingual aggregate at most (Qwen3.8-Next Table 1 reports only MMMLU: full 47.74 / SWA hybrid 51.33 / GDN hybrid 54.83); no study asks whether a fixed-size recurrent state, channel-wise decay, or the 1-in-4 global layer degrade unevenly across scripts or tokenisation fertility when the *content* is held fixed.
- Evidence: arXiv API `all:"linear attention" AND (multilingual OR "cross-lingual" OR translation)` → 14 results, none on hybrid-LLM state/ratio across languages (closest: 2022 document-level translation with linear attention; Mamba ASR for South African languages); `("Gated DeltaNet" OR "delta rule" OR "state space model") AND (multilingual OR "cross-lingual")` → 8, none relevant (Falcon-H1 mentions multilinguality only as a training set).
- Kevin advantage: parallel translation data lets him build recall/state probes where only language changes (same facts, N renderings), which no lab paper above does; 8×H100 trains 0.1–1B GDN/KDA hybrids at fixed data; Tinker Qwen3.5-4B/9B (hybrids) for the post-training stage; the Docker/Slurm harness already enforces exact-match generation evals.

**G2. Independent, iso-compute, multi-seed comparison of depth-axis operators (pre-norm vs Block/Full AttnRes vs mHC vs Gated Residual) at 0.1–1B with released code.**
- Why open: the only head-to-head numbers are first-party single runs (Qwen Table 5/6; AttnRes Table 2 vs "mHC-lite"); the two labs use different baselines, optimisers and scales; RD-AttnRes (2608.01075, 5 seeds at 120M/343M) compares only within the AttnRes family.
- Evidence: arXiv API `all:"attention residuals" AND ("hyper-connections" OR mHC)` → 1 result (DeRes, CTR prediction, unrelated); HF search "attnres"/"attention-residual" finds third-party 100M–600M reproductions (Ethangou; aspect-ratio-scaling raw OLMo-core checkpoints, 2026-08) but no cross-family comparison; Semantic Scholar unavailable (429).
- Kevin advantage: 8×H100 can run 120M–350M × 5 seeds × 4 residual designs in days; fla ≥0.5.1 ships the AttnRes operator (Gluon backend in 0.5.2); the harness's seed/checkpoint contract fits a sweep; result is publishable whether positive or negative.

**G3. Mechanism of the NoPE-in-hybrids disagreement (extrapolation vs termination).**
- Why open: Kimi Linear/K3 and Solar Open 2 ship NoPE global layers and claim direct 1M extrapolation; Qwen3.8-Next found NoPE indistinguishable in pretraining but "substantially higher rate of endless generation after post-training" and kept RoPE; 2606.15378 finds NoPE on full-attention layers *helps* small-window SWA hybrids. No study isolates what in post-training breaks NoPE hybrids, or whether KDA's decay (vs GDN's) supplies enough position for termination.
- Evidence: arXiv API `all:NoPE AND (hybrid OR "linear attention")` → 7 results, none on termination/post-training failure; `all:NoPE AND ("endless generation" OR termination OR "fail to terminate" OR "post-training")` → 1 result (Canon layers, unrelated).
- Kevin advantage: 8×H100 pretrain + SFT/RL of 0.1–1B hybrids with RoPE/NoPE/partial-RoPE global layers under identical data; Tinker post-training on Qwen3.5 hybrids (partial RoPE 0.25) as a production-scale control; parallel data adds a length-controlled multilingual termination probe.

**G4. Controlled study of MTP heads on ≤1B linear/hybrid backbones.**
- Why open: MTP is standard in production hybrids (including Qwen3.5-0.8B with `mtp_num_hidden_layers 1`) but no ablation shows whether the MTP objective helps or hurts a small hybrid backbone, or how a draft head should read recurrent state; Windowed-MTP shows the draft's full-attention read dominates for hybrid targets at long context.
- Evidence: arXiv API `all:"multi-token prediction" AND (hybrid OR "linear attention" OR "state space")` → 11 results, all production reports or serving papers; `all:"multi-token prediction" AND ("small models" OR "smaller models" OR "model size" OR "scale")` → 42 results, none a controlled small-hybrid ablation.
- Kevin advantage: 8×H100 and the harness; Qwen3.5-0.8B (hybrid, with MTP head) as an open reference; Tinker for post-training checks. Moderate architectural novelty; high value as a negative/positive result.

**G5. Open, reproducible ≤1B from-scratch reference of the K3 stack (KDA with lower-bounded decay + full-rank gate, NoPE global attention, Block AttnRes, MTP).**
- Why open: the pieces exist separately (GDN hybrids at 340M/1.3B from 2608.12149 and 2507.06457; dense AttnRes 100M/0.6B reproductions; pure-KDA tiny checkpoints without cards; a 0.6B *conversion* to KDA), but no combined small reference with a training recipe was found, so every K3-architecture claim at small scale rests on Moonshot's own runs.
- Evidence: HF API searches "KDA", "kimi-linear", "attnres", "attention-residual", "gated-deltanet", "GDN-hybrid"; arXiv API `all:hybrid AND all:"linear attention" AND all:"from scratch" AND ("350M" OR "1B" OR "small-scale")` → 0 results; `all:"Kimi Linear"` → 6 results, none a small reproduction.
- Kevin advantage: fla ≥0.5.2 provides KDA, GDN-2, Mamba3 and AttnRes kernels plus FlashQLA training backend; 8×H100 trains 350M/15B-token models in about a day (2607.07953 scale); Docker/Slurm checkpoint-resume harness. This is infrastructure-shaped, but it is the prerequisite for G1–G4 and for testing Coded Delta Memory against real KDA baselines.

**G6. Translation-equivariance of learned sparse indexers (DSA/QSA/CSA).**
- Why open: indexers are trained by KL to full attention on mostly English/Chinese/code; nobody has asked whether the selected blocks correspond across translations of the same document, or whether parallel data can supervise an indexer to be language-invariant.
- Evidence: arXiv API `all:"sparse attention" AND (multilingual OR "cross-lingual") AND "language model"` → 1 result (mGPT, 2022, unrelated).
- Kevin advantage: parallel corpora with span alignment (already assumed by Direction 18); fla ships NSA/MoBA/DSA reference implementations, so 0.1–1B sparse-attention models are trainable on 8×H100; GLM-5.3 (DSA) is on Tinker for behavioural probes. Feasibility caveat: indexer internals are not exposed through Tinker; the mechanistic part must be done on local small models.

## 4. Exact queries run

WebSearch (11 executed; 6 further queries refused when the session budget of 200 was exhausted):
1. Kimi K3 technical report Kimi Delta Attention Attention Residuals architecture
2. Qwen3.8 architecture hybrid Gated DeltaNet layer layout 2026
3. GLM-5.3 architecture attention sparse hybrid Z.ai technical report
4. Nemotron 3.5 hybrid Mamba Transformer architecture technical report NVIDIA
5. Mamba-3 paper state space model 2026 arXiv
6. DeepSeek V4 sparse attention DSA lightning indexer architecture 2026
7. Nemotron 3.5 Lightning 30B-A3B technical report architecture Mamba attention layers
8. Qwen3.8-Flash-Next "Qwen Sparse Attention" QSA Gated DeltaNet technical report
9. arXiv 2026 hybrid architecture study "attention layers" placement ratio linear attention which layers should be full attention
10. arXiv 2026 positional encoding alternatives NoPE PaTH stick-breaking attention hybrid rope-free length generalization
11. 2026 linear attention hybrid negative result "does not" reproduce OR withdrawn OR retracted DeltaNet Mamba arXiv
(refused: MiniMax M3 architecture; "Attention Residuals" 2603.15031 results; mHC 2026 GLM-5 DeepSeek; Nemotron 3.5 technical report arXiv; MTP small models hurts ablation; GDN hybrid ratio 3:1 OR 7:1 small-scale study)

arXiv API (export.arxiv.org; 22 successful queries, 2 failed with HTTP 429, 4 returned zero entries during a rate-limit window):
- all:"Kimi Delta Attention" OR all:"attention residuals" OR all:"Kimi K3"
- all:"gated deltanet" OR all:"gated delta net" OR all:"delta rule" AND cat:cs.LG
- all:"Mamba-3" OR all:"Mamba 3" OR all:"log-linear attention"
- all:"sparse attention" AND (DeepSeek OR "lightning indexer" OR "native sparse attention" OR MoBA)
- all:"multi-token prediction" AND cat:cs.CL
- all:"attention sink" OR all:"attention sinks"
- (hybrid AND ("linear attention" OR "state space" OR Mamba OR DeltaNet)) AND ("layer placement" OR "which layers" OR "attention ratio" OR "hybridization ratio" OR interleaving) [0 entries]
- ("positional encoding" OR NoPE OR rotary OR RoPE) AND ("length generalization" OR "length extrapolation") AND cat:cs.CL [0 entries]
- ti:"attention residuals" OR ti:"attention residual" [0 entries]
- ("negative result" OR "negative results" OR "does not improve" OR "fails to") AND ("linear attention" OR "hybrid attention" OR "state space model" OR DeltaNet) [0 entries]
- all:"linear attention" AND (multilingual OR "cross-lingual" OR translation) [14]
- ("Gated DeltaNet" OR "delta rule" OR "state space model") AND (multilingual OR "cross-lingual") [8]
- all:"multi-token prediction" AND (hybrid OR "linear attention" OR "state space") [11]
- all:"attention sink" AND (hybrid OR "linear attention" OR DeltaNet) [11]
- all:NoPE AND (hybrid OR "linear attention") [7]
- all:"hyper-connections" [82]
- all:"linear attention" AND hybrid AND (ratio OR placement OR interleaving) AND cat:cs.CL [13]
- all:"positional encoding" AND all:"length generalization" [29]
- all:"linear attention" AND ("negative result" OR fails OR "does not") [57]
- all:"Kimi Delta Attention" [17]
- all:"sparse attention" AND (multilingual OR "cross-lingual") AND "language model" [1]
- all:"attention residuals" AND ("hyper-connections" OR mHC) [1]
- all:NoPE AND ("endless generation" OR termination OR "fail to terminate" OR "post-training") [1]
- all:"multi-token prediction" AND ("small models" OR "smaller models" OR "model size" OR scale) [42]
- all:"Kimi Linear" [6]
- hybrid AND "linear attention" AND "from scratch" AND ("350M" OR "1B" OR "small-scale") [0]
Plus 98 arXiv abstract pages fetched directly (title/date/authors/abstract parsed) and full text of 2607.24653 (HTML), 2603.15031 (PDF via pdftotext), 2608.30320 (HTML), 2606.19348 (HTML), 2608.02689 (HTML).

arxiv.org/search HTML endpoint: 10 queries (mHC; attention residuals; multilingual linear attention hybrid; MTP hybrid; sink hybrid; NoPE hybrid; hybrid ratio ablation; Qwen3.8; Nemotron 3.5; translation SSM recall) — all returned 0 parsed results (blocked or markup change); re-run through the API above.

Semantic Scholar: 13 queries (Kimi Delta Attention; attention residuals transformer depth; hybrid linear attention layer placement ratio; multi-token prediction pretraining; attention sink softmax; Gated DeltaNet; + 7 retries with 3–12 s spacing) — 12 returned HTTP 429 or empty; 1 (MTP pretraining, year=2026) returned data with no relevant hits.

GitHub (gh): `search repos FlashKDA`, `search repos "Kimi-K3"`, `search repos "mamba3 OR mamba-3"`; API reads of MoonshotAI/{FlashKDA README + BENCHMARK_H20.md, Attention-Residuals README, Kimi-K3 README}, MoonshotAI org repo list, fla-org/flash-linear-attention {README, releases v0.5.1/v0.5.2, git tree, fla/ops/dsa/README.md}, QwenLM/{FlashQLA README, Qwen3.8-Flash-Next README + file list}, Sisyphbaous-DT-Project/open-qingyi.

Hugging Face API: model searches Kimi-K3, Qwen3.8, Qwen3.6, GLM-5.3, Nemotron-3.5, Mamba-3, Qwen3.5, author=Qwen "Qwen3.8", author=nvidia "Nemotron-3.5", author=moonshotai, author=zai-org, author=MiniMaxAI, author=fla-hub, KDA, kimi-linear, gated-deltanet, gated_deltanet, GDN-hybrid, deltanet, attnres, attention-residual; raw config.json/README for zai-org/GLM-5.3-Flash, zai-org/GLM-5.3, Qwen/Qwen3.8-Flash-Next, Qwen/Qwen3.8-27B, Qwen/Qwen3.5-{0.8B,4B,9B-Base}, nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-{BF16,Base-BF16}, moonshotai/Kimi-K3, state-spaces/mamba3-siso-1.5b, MiniMaxAI/MiniMax-M3, startlux-models/gdn-1.3b-isp-hybrid-3to1-50b, jaisidhsingh/SignedKDA-kda, Ethangou/attention-residuals-0.6B-full, arianraje/mimo-7b-gdn-hybrid-1B-OPD, aspect-ratio-scaling/block-attnres-lr2e-3-llama-400M-L24-pretrain.

X bookmarks (ft, 2,038 bookmarks synced 2026-09-01): ~37 searches — Kimi K3; attention residual; FlashKDA; Gated DeltaNet; Mamba-3 (query error) / "Mamba 3" / Mamba; sparse attention; Qwen3.8 (error) / "Qwen3.8" / Qwen / "Qwen3.6" / "Qwen 3.5"; GLM-5.3 (error) / "GLM-5.3" / GLM; Nemotron 3.5 (error) / "Nemotron 3.5" / Nemotron; multi-token prediction (error) / "multi token" / MTP; attention sink; NoPE; hybrid attention / "hybrid"; "DeepSeek V4"; "MiniMax M3"; "linear attention"; "positional"; DeltaNet; SSM; "1M context"; speculative; residual. Hits of substance: Moonshot K3 (2026-07-16) and FlashKDA (2026-07-27) posts, MiniMax M3 launch (2026-06-01, "MiniMax Sparse Attention scales context to 1M"), RampLabs PorTAL update (2026-07-27, "now spans from hybrid attention models to multimodal systems"). No bookmarks on GDN/Mamba/MTP/sinks/PE.

Jina reader: 2 attempts (arXiv HTML, HF card) — blocked with HTTP 401 "bad network reputation (AS7018)".

## 5. Coverage limits
- WebSearch budget exhausted after 11 queries (shared session cap); MiniMax M3 architecture (HF config shows `MiniMaxM3SparseForConditionalGeneration`, weights 2026-07-23; tech report not examined), mHC ecosystem beyond arXiv, and any Nemotron 3.5 technical report were not web-searched.
- Semantic Scholar rate-limited (HTTP 429) on 12/13 queries without an API key: citation counts and citation-graph novelty checks are missing.
- Jina reader blocked; z.ai and qwen.ai blogs are JS-rendered and unreadable via curl — GLM-5.3-Flash and Qwen3.8 claims come from HF cards/configs, GitHub READMEs and arXiv, not the blogs. The Qwen3.8-Flash-Next `tech_report.pdf` on GitHub was not parsed (arXiv 2608.30320 used instead).
- arXiv API 429s forced abstract-page scraping; arxiv.org/search HTML parsing failed for all queries, so listing-based discovery relied on the API only. Only five papers were read in full text; all others via abstract (plus README/config where applicable).
- Peer-review status: most items are 2026 preprints or lab reports. Peer-reviewed: Mamba-3 (ICLR 2026), Q-Delta (ICML 2026), CCQ (EMNLP 2026), Cracks in the Foundation (COLM 2026), RFS (EACL 2026), Randomized YaRN (EMNLP 2026 Findings), Hyperscale Lottery (ECML-PKDD ITEM workshop), Canon layers (NeurIPS 2025 v1).
- Retractions: no retraction database was searchable; arXiv withdrawal comments are not surfaced by the queries used; no retraction in this area was found through 2026-09-01 under this coverage (the SR-TTT v2 retraction from the prior sweep remains the only known one).
- Not covered: Gemma 4 / GPT-OSS / Llama architecture updates, MiniMax M3 report, closed-lab systems, Chinese-language sources (Zhihu), NeurIPS/ICLR 2027 submissions not yet on arXiv.
- Quantities quoted from WebSearch snippets were re-verified in the primary source before inclusion; Mamba-3's per-benchmark deltas and GLM-5.3-Flash's "3× attention compute / 4.4× smaller KV cache" serving claims (seen only in secondary summaries) are deliberately omitted.

## 6. Bottom line for Kevin
- Generic operator design (new gates, new decays, new ratios, learned placement) is saturated by at least eight labs plus a dense 2026 preprint stream; the prior program's rejections stand and item 6 (budgeted operator mixture) should be reframed or dropped.
- The frontier's *unmeasured* dimensions are the ones his assets touch: language/script-controlled behaviour of recurrent state and of learned indexers (parallel data), independent multi-seed replication of depth-axis operators and NoPE-hybrid termination at 0.1–1B (8×H100 + harness), and MTP on small hybrids. Each is cheap, falsifiable, and publishable as a negative.
- Any small-scale claim must use generation-based evaluation and early long-context extension probes (Stuck-on-A, When Perplexity Lies, Cracks in the Foundation), which the CoTCodec evaluation contract already requires.
