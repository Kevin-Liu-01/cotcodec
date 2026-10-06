# Local model ecosystem sweep (open weights + local serving/training), June–September 2026

Cell: `local-model-ecosystem` · Run date: 2026-09-01 · Prior sweep cutoff: 2026-08-10
Owner context: 8x H100 80GB single node (640 GB HBM), Docker+Slurm, Tinker managed LoRA, HF revision-pinned snapshots.

Honesty conventions used below: **[1P]** = first-party (model card / README / vendor blog / vendor repo / vendor arXiv report, not peer-reviewed); **[3P]** = third-party (community thread, blog, independent repo); **[peer]** = peer-reviewed (none found in this window for these models); **[est]** = my own arithmetic from first-party parameter counts, not a sourced measurement. No claim in this note is written as "completely novel"; gaps are stated as "no direct prior art found through 2026-09-01 under the coverage listed at the end".

---

## 1. Findings

Each finding: title · URL · date · source type · claim · what it occupies · relevance to Kevin · confidence.

### F1. Kimi K3 open weights and architecture [1P]
- URL: https://huggingface.co/moonshotai/Kimi-K3 · report: https://arxiv.org/abs/2607.24653 (v1 2026-07-27, v2 2026-08-07)
- Date: weights public 2026-07-27 (GitHub repo created 2026-07-27T08:01Z); HF revision `a590ce090cb049c93a33dfe8c208ec652aa20503` (2026-08-20, `encoding_k3.py` fix).
- Claim: 2.8T total / 104B activated; 93 layers (1 dense) = 69 KDA + 24 gated MLA (KDA:global = 3:1, full-attention layers at 4,8,…,92,93 per `config.json`); Stable LatentMoE with 896 routed experts, top-16, 2 shared, latent MoE dim 3584, expert hidden 3072; SiTU-GLU activation; vocab 160K; context 1,048,576; MoonViT-V2 vision encoder 401M; MXFP4 weights / MXFP8 activations via quantization-aware training from the SFT stage; first-party claim of "approximate 2.5× improvement in overall scaling efficiency over Kimi K2".
- Occupies: KDA + gated-MLA 3:1 interleave at 3T scale; Attention Residuals (AttnRes); latent-space MoE routing; native MXFP4 QAT.
- Relevance: the reference point for "production KDA hybrid"; completely infeasible locally (see F4). Architecture ideas (AttnRes, latent MoE) are now occupied at scale.
- Confidence: 0.95 (numbers from card + arXiv abstract; scaling-efficiency claim unreplicated).

### F2. Kimi K3 License (bespoke MIT-plus-thresholds) [1P]
- URL: https://huggingface.co/moonshotai/Kimi-K3/blob/main/LICENSE
- Date: 2026-07-27
- Claim: MIT-style grant with two conditions: (2) a "Model as a Service" business with aggregate revenue > US$20M over any 12 months must sign a separate agreement before commercial use; (3) products with > 100M MAU or > US$20M monthly revenue must display "Kimi K3" in the UI; (4) internal use and use via Moonshot's official products/certified partners are exempt. Not OSI open source; Moonshot uses "open weight".
- Occupies: the "MIT + MaaS revenue threshold" license pattern (also Qwen Community 1.0, Qwen3.8-Max, GLM-5.3).
- Relevance: research/academic use is unrestricted; publication reproducibility is fine.
- Confidence: 0.98.

### F3. Kimi K3 (and Kimi Linear) still require `trust_remote_code=True` in transformers 5.16.1 [1P + GitHub]
- URLs: HF API for `moonshotai/Kimi-K3` (py files: `configuration_kimi_k3.py`, `modeling_kimi_k3.py`, `modeling_kimi_linear.py`, `encoding_k3.py`, …; `config.json` `transformers_version: 4.56.2`, `auto_map` present); transformers models dir at v5.16.1 (no `kimi_k3`, no `kimi_linear`); PR "Add K3" https://github.com/huggingface/transformers/pull/47670 (draft, open since 2026-07-31); PR "Kimi linear" https://github.com/huggingface/transformers/pull/48250 (open since 2026-08-24).
- Date: checked 2026-09-01
- Claim: both K3 and `moonshotai/Kimi-Linear-48B-A3B-Base` (rev `3b171c17bfc4ee348599b6781a2ca8715c21c8dc`, 2026-01-30, MIT) load only via remote code; Kimi-K2.6/K2.7-Code (`kimi_k25`) do have a native transformers module (`kimi_k25`) even though the repos ship custom files.
- Occupies: n/a (status).
- Relevance: Kevin's registered Kimi-Linear base is a mutable-remote-code dependency; pin the 40-hex revision and vendor the modeling files into the digest-pinned image.
- Confidence: 0.95.

### F4. Kimi K3 hardware floor rules out 8x H100 for serving and training [1P + 3P]
- URLs: vLLM recipe https://recipes.vllm.ai/moonshotai/Kimi-K3 ("At least 8x GB300" or "at least 8x MI355X/MI350X"; TP8 / TEP16 / TP8xPP2 profiles; CUDA 13 only); Unsloth https://unsloth.ai/docs/models/kimi-k3 (UD-IQ1_S 594 GB needs ~610 GB RAM+VRAM; Q8 1.56 TB); SGLang day-0 blog https://www.lmsys.org/blog/2026-07-27-kimi-k3-day0-support (benchmarks on 2×4 GB300; RL on 16 nodes × 4 GB300).
- Date: 2026-07-27 … 2026-08-25
- Claim: the native MXFP4 checkpoint is ~1.56 TB (HF safetensors total 2.78T params, U8-packed) and no vendor or serving-engine documentation lists any H100/H200 configuration. Community thread https://huggingface.co/moonshotai/Kimi-K3/discussions/180 claiming "8× H100 80GB (tensor+expert)" is inconsistent with the checkpoint size and should be treated as unreliable [3P].
- Relevance: kill-shot for any local K3 experiment; K3 is not on Tinker either (F25). Only K3 *ideas* are usable, not K3 weights.
- Confidence: 0.95.

### F5. KDA serving stack matured fast (vLLM v0.27/v0.28, SGLang v0.5.17/v0.5.18) [1P vendor release notes]
- URLs: https://github.com/vllm-project/vllm/releases/tag/v0.27.0 (2026-08-10) · https://github.com/vllm-project/vllm/releases/tag/v0.28.0 (2026-08-26) · https://github.com/sgl-project/sglang/releases/tag/v0.5.17 (2026-08-08) · https://github.com/sgl-project/sglang/releases/tag/v0.5.18 (2026-08-22) · vLLM PR #50000 merged 2026-07-30 · SGLang PR #32541 merged 2026-08-04.
- Claim: vLLM v0.27.0 shipped K3 "with a full stack landing in one release" (model, AttnRes kernels, DeepGEMM, compressed-tensors, DSpark AR fusion); v0.28.0 added Decode Context Parallel, fused FlashKDA decode/prefill kernels, adaptive speculative budget (~60% better DSpark TTFT), shared-expert sharding (~17 GiB/GPU saved), ROCm. SGLang v0.5.17 had day-0 K3 (DCP, DSpark, KDA-aware prefix caching, LoRA on quantized weights); v0.5.18 tuned MI355X (1.37–1.77x throughput, 1.45–2.42x ITL). vLLM v0.28.0 also made prefix caching default for Mamba models and bumped Transformers to 5.15.0.
- Occupies: production KDA/Mamba kernels and hybrid P/D disaggregation (NIXL for hybrid MLA+SSM in v0.27.0).
- Relevance: any KDA/GDN/Mamba hybrid Kevin trains at small scale is now servable with mature kernels; DSpark/MTP self-speculation is a standard bundled feature.
- Confidence: 0.95.

### F6. FlashKDA kernels are open and auto-dispatched from flash-linear-attention [1P]
- URLs: https://github.com/MoonshotAI/FlashKDA (created 2026-04-20, pushed 2026-09-01, 1,242 stars) · X: https://x.com/Kimi_Moonshot/status/2081762799202746420 (2026-07-27, claims 1.72×–2.22× prefill speedup; first-party) · fla integration https://github.com/fla-org/flash-linear-attention/pull/852
- Claim: CUTLASS KDA kernels; `pip install flash-linear-attention>=0.5.0` then `fla.ops.kda.chunk_kda` auto-dispatches to FlashKDA (`FLA_FLASH_KDA=0` opts out).
- Occupies: KDA kernel engineering.
- Relevance: makes small-scale KDA pretraining/fine-tuning on H100 practical; also the fix path for F15.
- Confidence: 0.85 (speedup figure is a tweet-level claim; not independently measured).

### F7. Kimi-K2.6: native transformers arch, but 8x H100 not a documented serving target; training path is Tinker LoRA [1P]
- URLs: https://huggingface.co/moonshotai/Kimi-K2.6 (rev `7eb5002f6aadc958aed6a9177b7ed26bb94011bb`, 2026-05-19, license `modified-mit`, `kimi_k25` arch, 1.03T params INT4 compressed-tensors) · vLLM recipe https://recipes.vllm.ai/moonshotai/Kimi-K2.6 (INT4: "8× H200 GPUs (verified), or equivalent aggregate VRAM (~640 GB)"; B300 NVFP4 4×; vLLM ≥ 0.25.0) · Tinker lineup https://tinker-docs.thinkingmachines.ai/tinker/models/ (Kimi-K2.6 32K/128K).
- Claim: 8x H100 = exactly 640 GB, so INT4 K2.6 leaves no KV headroom locally; Tinker is the only realistic training route.
- Occupies: n/a.
- Relevance: keep K2.6 as a Tinker-only adaptation target.
- Confidence: 0.9.

### F8. Qwen3.8-27B: Apache-2.0 dense GDN hybrid, natively supported everywhere, trainable on one node [1P + est]
- URLs: https://huggingface.co/Qwen/Qwen3.8-27B (rev `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`, 2026-08-14; weights uploaded 2026-08-13; initial commit 2026-08-05) · vLLM recipe https://recipes.vllm.ai/Qwen/Qwen3.8-27B (vLLM ≥ 0.17.0, transformers ≥ 5.8.0) · Ollama https://ollama.com/library/qwen3.8 (`27b`, `27b-mlx`; 1.3M downloads).
- Claim: 27.78B params, `model_type qwen3_5` (no custom code); 64 layers laid out 16 × (3 × Gated DeltaNet→FFN → 1 × Gated Attention→FFN) (48 linear + 16 full); GDN 48 V-heads/16 QK-heads, head dim 128; gated attention 24 Q / 4 KV heads, head dim 256; hidden 5120; FFN 17,408; MTP head; context 262,144 native, 1M via YaRN override. Tinker lists Qwen3.8-27B (64K/256K). Full fine-tuning at 16 B/param ≈ 445 GB before activations [est] — fits 8x H100 with activation checkpointing; LoRA trivially.
- Occupies: GDN + gated-attention 3:1 dense hybrid (Qwen3.5 lineage).
- Relevance: the strongest natively supported, permissively licensed, locally trainable hybrid in the window; best "real model" testbed for adapter/operator experiments.
- Confidence: 0.92.

### F9. Qwen3.8-Flash-Next: GDN + Qwen Sparse Attention + Gated Residual + n-gram embeddings; vLLM 0.29+ only; no H100 recipe [1P]
- URLs: https://huggingface.co/Qwen/Qwen3.8-Flash-Next (rev `de4b8e4d43b917e7706784d8bb445c9af86a3540`, 2026-08-27; uploaded 2026-08-26; license `qwen-community-1.0`) · tech report PDF https://github.com/QwenLM/Qwen3.8-Flash-Next/blob/main/tech_report.pdf (2.37 MB) · vLLM recipe https://recipes.vllm.ai/Qwen/Qwen3.8-Flash-Next · SGLang cookbook https://docs.sglang.io/cookbook/autoregressive/Qwen/Qwen3.8-Flash-Next · transformers v5.16.0 release (adds Qwen4-Exp) https://github.com/huggingface/transformers/releases/tag/v5.16.0
- Claim: "125B with 6B activated, plus 51B n-gram embedding and 4B MTP" (HF safetensors 180.0B); hidden 2560; 48 layers = 12 × (3 × GDN→MoE → 1 × QSA→MoE) (36 linear + 12 full); QSA indexer: MQA with 4 query heads and 1 shared key head, budget 512 blocks / 2048 tokens; 512 experts, 10 routed + 1 shared, expert dim 640; Gated Residual: 4 branches, bottleneck rank 320; n-gram embedding 20M bigrams/trigrams at layer 2; context 262,144 (1M extensible). `model_type qwen4_exp` is native in transformers ≥ 5.16.0 (released 2026-08-26). vLLM recipe requires "vLLM 0.29.0+" (unreleased as of 2026-09-01; newest tag `v0.28.1rc0`), documents only GB300 and H200 (TEP8 FP8), FP8 checkpoint 172.78 GiB, BF16 335.28 GiB, PLE/n-gram CPU offload ≥ 51 GB host RAM; SGLang cookbook is pinned to a `qwen4-main` branch. Ollama has only a `125b-mlx` tag. Not on Tinker.
- Occupies: hybrid of linear (GDN) + block-sparse attention (QSA); multi-stream gated residual (hyper-connection family); embedding-axis parameter scaling via n-grams.
- Relevance: architecture "preview of Qwen4"; the residual/embedding axes Kevin might target are now occupied by a vendor. Locally: inference-only realistic (FP8 ~173 GiB fits; BF16 LoRA ≈ 396 GB before activations [est] is tight); training path undocumented.
- Confidence: 0.9.

### F10. Qwen team ablation paper on Qwen3.8-Next (efficiency and negative results on n-gram scaling) [1P arXiv, not peer-reviewed]
- URL: https://arxiv.org/abs/2608.30320 (2026-08-31) "On the Design of Qwen3.8-Next Architecture: Evaluation, Efficiency, and Training Stability" (Qiu, Wang, Li, … 35 authors, Qwen team).
- Claim: Qwen3.8-Flash-Next "leads the 397B-A17B predecessor on eight [benchmarks] and trails it on the rest by at most 2.6 points, at 1/3 the activated parameters, 1/3 the training tokens, and roughly 1/9 the training FLOPs"; "enlarging the n-gram vocabulary lowers loss monotonically while downstream accuracy saturates"; Muon plus the architecture "shift the optimal learning rate and batch size upwards" and "render batch-size warmup unnecessary".
- Occupies: design-space ablations for GDN+QSA+GR+n-gram; loss-vs-downstream divergence for embedding scaling.
- Relevance: a first-party negative result (loss improves, accuracy saturates) directly relevant to any "scale the embedding axis" proposal; training-stability findings for hybrid+Muon.
- Confidence: 0.85 (abstract-level; PDF not read).

### F11. Negative: no Qwen3.8 base checkpoints and no sub-27B Qwen3.8 [HF API]
- URLs: HF org listing https://huggingface.co/api/models?author=Qwen (only `Qwen3.8-27B(-FP8)`, `Qwen3.8-Flash-Next(-FP8)`, `Qwen3.8-2.4T-A95B(-FP8)`); `Qwen/Qwen3.8-{2B,4B,9B}`, `Qwen3.8-27B-Base`, `Qwen3.8-Flash-Next-Base` → HTTP 401 (nonexistent/private); community request https://huggingface.co/Qwen/Qwen3.8-Flash-Next/discussions (2026-08-29 "Request 9B, 35B A3B, 4B qwen 3.8 models").
- Claim: Qwen3.8 ships post-trained weights only; Qwen3.8-2.4T-A95B (rev `207bd685a7e3696cfaff12ded7c6a7ea0f88c996`, 2026-08-12, license `qwen3.8-max`, MaaS threshold US$50M) is 2.45T params and irrelevant locally. The newest Qwen *bases* remain Qwen3.5-{0.8B,2B,4B,9B,35B-A3B}-Base (2026-04-23).
- Relevance: base-model experiments must use Qwen3.5 bases (F26).
- Confidence: 0.9.

### F12. Field-reported defects in Qwen3.8-27B (hybrid serving and tokenizer tail) [3P]
- URLs: https://huggingface.co/Qwen/Qwen3.8-27B/discussions/175 (2026-08-27, undertrained tokens: min embedding norm 0.001 vs vocab mean 0.899; deterministic silent substitution, worst tokens fail 16/16 at T=0.7; strongest in the Chinese web-boilerplate tail) · /discussions/178 (2026-08-27, 20k–55k-token thinking loops; `reasoning_effort: low` is a soft prompt only) · /discussions/169 (2026-08-25, vLLM prefix-cache blocks are 1,584 tokens because attention page size must align with the GDN page; prompts < ~5K tokens never hit cache; cache materializes lazily on the second request).
- Claim: as stated per thread; none are vendor-confirmed.
- Relevance: (a) glitch-token tail matters for multilingual/translation work; (b) hybrid page alignment is a real serving cost of GDN hybrids; (c) reasoning-budget control is weak.
- Confidence: 0.7 (single-reporter threads).

### F13. GLM-5.3: same 744B-A40B base as GLM-5.2, post-training-only gains, staged weights after safety review [1P + 3P]
- URLs: https://huggingface.co/zai-org/GLM-5.3 (rev `187fb9fff6319062325ff825627ef6db084d9bc6`, 2026-08-31; "Initial commit 0828" 2026-08-27; license `glm-5.3`) · GitHub https://github.com/zai-org/GLM-5 · LICENSE https://huggingface.co/zai-org/GLM-5.3/blob/main/LICENSE · delay write-up [3P] https://explainx.ai/blog/glm-5-3-open-weights-delay-zai-august-2026
- Claim: "GLM-5.3 uses the same base model as GLM-5.2 — every gain comes from post-training"; 744B-A40B, `glm_moe_dsa` (native transformers; config `transformers_version 5.15.0`), 78 layers, 256 experts top-8 + 1 shared, DSA `index_topk 2048`, FP8 checkpoint 753B safetensors; API launch 2026-08-14, weights ~2 weeks later after a "rigorous safety evaluation" (HF placeholder date 2026-08-28 per [3P]; HF commits show 2026-08-27/28). License: MIT-like; only MaaS businesses with > US$10B revenue over 12 months must pass a Z.AI security review. First-party claim of emergent cyber capability (CyberGym 84.5, "more than doubles GLM-5.2 on exploitation benchmarks"). Tinker lists GLM-5.3 (256K). Ollama `glm-5.3` is cloud-only.
- Occupies: post-training-only version bumps on a fixed DSA base.
- Relevance: 753 GB FP8 > 640 GB → not servable locally; adaptation only via Tinker.
- Confidence: 0.9 (delay narrative is third-party; dates corroborated by HF commits).

### F14. GLM-5.3-Flash: first open KDA + DeepSeek-Sparse-Attention hybrid with mHC; MIT; 320B-A18B [1P]
- URLs: https://huggingface.co/zai-org/GLM-5.3-Flash (rev `03eb5366286afd40d2221b1d9c63a6dd1ba4832e`, 2026-08-31; weights 2026-08-26; MIT) · config.json (fetched) · transformers `modeling_glm5_next.py` at v5.16.1 (class `Glm5NextTextLinearAttention`: "Kimi-style KDA (Kimi Linear Attention) for GLM-5.3-Flash") · vLLM recipe https://recipes.vllm.ai/zai-org/GLM-5.3-Flash · SGLang cookbook https://docs.sglang.io/cookbook/autoregressive/GLM/GLM-5.3-Flash
- Claim: "320B total parameters and just 18B active"; `glm5_next` text config: 45 layers = 34 `linear_attention` (KDA) + 11 `deepseek_sparse_attention` (`index_topk 2048`, 32 indexer heads), 288 routed experts top-8 + 1 shared, Manifold-Constrained Hyper-Connections `hc_mult 4`, MTP 1 layer, context 1,048,576; "newly trained base model", "30T-token multimodal pre-training corpus"; base not released (`GLM-5.3-Flash-Base` → 401). vLLM: "about 306 GiB for the default native FP8 checkpoint", Hopper supported at TP4, but "vLLM 0.29.0 or newer" — the native vLLM PR https://github.com/vllm-project/vllm/pull/53906 was still open on 2026-09-01 and a nightly user reports a load crash (https://huggingface.co/zai-org/GLM-5.3-Flash/discussions/26). SGLang cookbook exists (AMD recipes reverted 2026-09-01, PR #37380). llama.cpp support PR https://github.com/ggml-org/llama.cpp/pull/27773 open. Ollama cloud-only. Not on Tinker.
- Occupies: KDA + DSA hybrid (~3:1), mHC residuals, natively multimodal MoE at 320B.
- Relevance: the one frontier KDA hybrid whose FP8 weights fit 8x H100 for inference; training locally is undemonstrated (F15, F3-style kernel dependence; BF16 weights 643 GB do not fit).
- Confidence: 0.92.

### F15. Negative (training-relevant): transformers' pure-PyTorch chunked-KDA fallback yields NaN gradients and blows up memory (GLM-5.3-Flash) [GitHub, open PR]
- URL: https://github.com/huggingface/transformers/pull/48455 (opened 2026-09-01, open)
- Claim: with per-channel KDA decay, the fallback materializes a `[B,H,N,C,C,D]` decay tensor and applies the causal mask after `exp()`; non-causal differences reach 5×63 = 315 > float32 exp limit ≈ 88.7, so backward evaluates `0 * inf` → NaN gradients. Forward outputs stay finite, so inference is unaffected.
- Relevance: any LoRA/full fine-tune of a KDA model in transformers must use the `fla`/FlashKDA kernel path (kernels became opt-in for linear-attention models in transformers v5.15.0, see F21); a silent training-time hazard for hybrid experiments on the node.
- Confidence: 0.9 (PR description; fix unmerged at run time).

### F16. DeepSeek-V4 family: MIT, natively supported, DSpark bundled; V4-Flash-Base exists; local training unrealistic [1P]
- URLs: https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731 (rev `7872f01b1d1fe23eabc4c98b48bffcef5a386062`, 2026-08-01) · https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813 (rev `72e1d3230f6c080a530b0a1d46f8eb4602340597`, 2026-08-13) · https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-Vision-Exp (rev `6821d6ad3681a4b137b066b76094fa82ebd0a380`, 2026-09-01) · https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-Base (rev `8855555deef230a27a21a8d6f294b7b7497759b6`, 2026-04-27) · report https://arxiv.org/abs/2606.19348 (arXiv `published` 2026-04-26) · API changelog https://api-docs.deepseek.com/updates/
- Claim: V4-Flash 284B total / 13B active (config: 43 layers, 256 experts top-6 + 1 shared, `index_topk 512`, hyper-connection `hc_mult`, `compress_ratios`, DSpark keys; safetensors 304B incl. INT8 experts and DSpark module); V4-Pro 1.6T / 49B (61 layers, 384 experts, `index_topk 1024`); context 1,048,576; hybrid "Compressed Sparse Attention and Heavily Compressed Attention" + mHC + Muon; 32T+ training tokens; Pro at 1M context "only 27% of single-token inference FLOPs and 10% of KV cache compared with DeepSeek-V3.2". 0731/0813 releases bundle a DSpark speculative module; no Jinja chat template (Python `encoding/` scripts). README serving example: "single 4×GB300 node". `deepseek_v4` is native in transformers/vLLM/SGLang. Ollama cloud-only (`0731-cloud`, `0813-cloud`). Not on Tinker (only DeepSeek-V3.1). Unsloth documents GGUF sizes only (UD-IQ3_XXS 103 GB / ≥110 GB RAM), no fine-tuning guidance.
- Occupies: compressed/sparse attention at 1M context; mHC; bundled self-speculative decoding; released 284B base.
- Relevance: FP8/INT8 304 GB fits 8x H100 for inference (tight at long context); training is out of reach (LoRA on BF16 ≈ 669 GB [est]).
- Confidence: 0.9.

### F17. Gemma 4: Apache-2.0, native, five sizes with released bases, PLE small models, MTP drafters [1P]
- URLs: https://huggingface.co/google/gemma-4-E4B (rev `411aa17b749aa952df1359d2dcea73917a544d9a`) · E2B `d29ff6b45f081a49ee2733a859c9c9c2d95d1a6f` · 12B `023679ed352de9bb66cc873c9009ce3482585c08` · 26B-A4B `24548b62aa021d562695c04aaf7758a1ea47990b` · 31B `5bbc2fb1c1b2c611d06e3d9f23c170ba21659d89` (all base revs 2026-07-15) · tech report https://arxiv.org/abs/2607.02770 (2026-07-02, v2 2026-07-24) · model card https://ai.google.dev/gemma/docs/core/model_card_4 · MTP drafters https://huggingface.co/google/gemma-4-12B-it-assistant (2026-08-20, 423M params) · Ollama https://ollama.com/library/gemma4 (24M downloads; e2b–31b local tags)
- Claim: release 2026-04-02 (HF commit "Preparing for release!"); E2B 2.3B effective / 5.1B total, E4B 4.5B / 8B (Per-Layer Embeddings: per-layer vocab 262,144 × 256 in E4B config), 12B Unified encoder-free (11.95B), 26B-A4B MoE 25.2B / 3.8B active (128 experts, 8 active), 31B dense 30.7B; sliding 512/1024 + global interleave (E4B: 35 sliding : 7 full attention; 18 KV-shared layers); contexts 128K/256K; 140+ pretraining languages, 35+ out-of-box; QAT w4a16/q4_0 variants 2026-07-20; `-assistant` repos are MTP draft models ("up to 3x" decoding speedups, first-party). `gemma4`/`gemma4_unified` native; vLLM v0.28.0 has `gemma4_dspark`/`gemma4_mtp`. Not on Tinker.
- Occupies: PLE embedding scaling; sliding/global hybrid; unified encoder-free multimodality; vendor-shipped MTP drafters.
- Relevance: E2B/E4B/12B bases are the cleanest sub-12B permissive bases for full fine-tuning on the node (E4B full FT ≈ 128 GB, 12B ≈ 191 GB [est]).
- Confidence: 0.93.

### F18. Nemotron 3.5 Lightning 30B-A3B: Mamba-2 + MoE + attention hybrid with open base, open post-training data, OpenMDW-1.1, no custom code [1P]
- URLs: https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16 (rev `a9904d24bcc1d289a1950fa9d2b978c47cf903b9`, 2026-08-24; release 2026-08-11) · Base https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-Base-BF16 (rev `434456c9a6753f29d24e23c95d622aaf17111b3b`, 2026-08-11) · NVFP4 rev `cc84af2fe71647d87f4486c064f320e1e7535243` · license https://openmdw.ai/license/1-1/ · data collection https://huggingface.co/collections/nvidia/nemotron-post-training-v3-6939b7b93382bac738eebd17 (49 datasets, all `gated: false`, updated 2026-08-11) · recipes https://github.com/NVIDIA-NeMo/Gym/tree/main/nemotron_recipes/lightning-3.5 · Ollama https://ollama.com/library/nemotron-3.5-lightning (`30b`, 144.9K downloads) · Tinker lineup (64K/256K)
- Claim: "30B parameters in total", "3B active" (safetensors 31.58B); `nemotron_h` native (no `.py` files, `auto_map` absent — unlike the Nemotron-3-Nano repo which ships custom code); 52 layers, hidden 2688, 128 routed experts top-6 + 1 shared, Mamba-2 (64 heads × 64 dim, state 128, 8 groups), select attention layers, MTP layers; pre-trained "over 20T tokens" with an NVFP4 recipe in Megatron-LM; context up to 1M ("8×, TP8 + EP" H100 validated at 1M; single H100 80GB serves 256K); card states BF16/Base releases are "intended primarily for customization: post-training (SFT, RL, distillation)" via NeMo RL / NeMo Gym; post-training languages EN + FR/DE/IT/JA/ES/ZH; OpenMDW-1.1 is permissive with a patent-litigation termination clause. llama.cpp merged DFlash (2026-08-11) and DSpark (2026-08-27) support. Unsloth supports post-training and warns to size hardware as a 30B-total model. No arXiv tech report found (only Content Safety and ASR papers, F19).
- Occupies: Mamba-2/MoE/attention hybrid with fully open data + recipes; NVFP4-native pretraining.
- Relevance: the most training-ready hybrid on 8x H100 (LoRA trivial; full FT ≈ 505 GB [est], borderline) and the only 2026 hybrid whose *base* checkpoint and post-training data are both open; Tinker cross-check available.
- Confidence: 0.93.

### F19. Negative: no Nemotron 3.5 Lightning technical report on arXiv [arXiv API]
- URL: arXiv API `ti:Nemotron` (39 results; newest: https://arxiv.org/abs/2608.27548 Content Safety Moderator 2026-08-27; https://arxiv.org/abs/2607.18912 ASR adaptation 2026-07-21; Nemotron-Labs papers); `all:"Nemotron 3.5"` → 2 results, neither is the LLM report.
- Claim: Lightning's documentation is the HF card + NeMo Gym recipes only.
- Relevance: architecture details must be taken from `config.json`/card; no peer-reviewed or preprint source.
- Confidence: 0.85 (arXiv API was rate-limited for most of the session; two clean queries succeeded).

### F20. Negative: gpt-oss received no new weights in June–September 2026 [HF API]
- URLs: https://huggingface.co/openai/gpt-oss-20b (rev `6cee5e81ee83917806bbde320786a8fb61efebee`, last modified 2025-08-26) · https://huggingface.co/openai/gpt-oss-120b (rev `b5c939de8f754692c1647ca79fbf85e8c1e70f8a`, 2025-08-26) · org listing (newest: `openai/privacy-filter` 2026-04-22, `gpt-oss-safeguard-20b` 2026-01-14)
- Claim: Apache-2.0, MXFP4, native `gpt_oss`; Tinker offers GPT-OSS-120B/20B; Ollama local `20b`/`120b`. SGLang v0.5.17 reports DWDP MoE prefill "1.92x over DEP4" on 4×B200 for gpt-oss-120b (first-party SGLang).
- Relevance: stable, unchanged baseline; 20B full FT ≈ 335 GB [est] fits the node.
- Confidence: 0.95.

### F21. transformers v5.16.1 native-model registry and the v5.15 kernels-opt-in break [1P GitHub]
- URLs: https://github.com/huggingface/transformers/releases/tag/v5.16.0 (2026-08-26; adds Qwen4-Exp, Step3p7, GraniteSpeech5, CohereCompass, ESMC) · https://github.com/huggingface/transformers/releases/tag/v5.15.0 (2026-08-10; "Kernels are now opt-in rather than mandatory for linear attention models (Mamba, GDN, Conv-only, etc.)"; Gemma 4 `per_layer_config`) · models dir at v5.16.1
- Claim: native (no `trust_remote_code`) modules present for `deepseek_v4`, `glm5_next`, `glm_moe_dsa`, `qwen4_exp`, `qwen3_5`, `qwen3_5_moe`, `kimi_k25`, `nemotron_h`, `gemma4(_unified/_assistant)`, `gpt_oss`, `inkling`, `olmo_hybrid`, `falcon_h1`, `smollm3`, `step3p7`; absent: `kimi_k3`, `kimi_linear`.
- Relevance: defines the publication-lane model set (trust_remote_code=False) and a training hazard (kernels must be enabled explicitly for GDN/KDA/Mamba; see F15).
- Confidence: 0.95.

### F22. vLLM v0.28.0 registry: which hybrids are in the release vs. main-only [1P GitHub]
- URL: https://raw.githubusercontent.com/vllm-project/vllm/v0.28.0/vllm/model_executor/models/registry.py · open PRs https://github.com/vllm-project/vllm/pull/53906 (GLM-5.3-Flash), https://github.com/vllm-project/vllm/pull/54371 and /54517 (Qwen4Exp PLE offload/fusion)
- Claim: v0.28.0 registers `DeepseekV4ForCausalLM`, `GlmMoeDsaForCausalLM`, `KimiK3ForConditionalGeneration`, `KimiK25ForConditionalGeneration`, `KimiLinearForCausalLM`, `NemotronHForCausalLM`, `Gemma4*`, `Qwen3_5*`, `GptOssForCausalLM`, `InklingForCausalLM`, `OlmoHybridForCausalLM`, `FalconH1ForCausalLM`, DSpark/MTP drafters; it does not register `Qwen4Exp*` or `Glm5Next*` (both documented as "vLLM 0.29.0+"). Newest tag on 2026-09-01: `v0.28.1rc0`.
- Relevance: pin `vllm/vllm-openai:v0.28.0` for everything except Qwen3.8-Flash-Next and GLM-5.3-Flash.
- Confidence: 0.95.

### F23. SGLang v0.5.18 coverage and AMD quantization result [1P release notes]
- URL: https://github.com/sgl-project/sglang/releases/tag/v0.5.18 (2026-08-22)
- Claim: cookbooks for the Qwen3.8 family, Nemotron 3.5 Lightning, Dots3-Note, Ling-3.0 and DeepSeek-V4-Pro-0813; `--quantization quark_mxfp4` dequantizes NVFP4 checkpoints to MXFP4 on AMD with "97.5–100.2% GSM8K recovery" across MiniMax-M2.7, GLM-5.1, Kimi-K2.6, Qwen3.5-397B, DeepSeek-R1; unified-memory support for MLA-hybrid-Mamba (Kimi-Linear) on the Triton backend (v0.5.17). Models dir includes `kimi_k3.py`, `kimi_linear.py`, `deepseek_v4*.py`, `nemotron_h*.py`, `gemma4_*.py`, `inkling*`.
- Relevance: SGLang is the only release-tagged engine with Kimi-Linear + K3 + hybrid unified memory; DSpark/DFlash/EAGLE options are first-class.
- Confidence: 0.9.

### F24. Ollama v0.33.x and local-vs-cloud availability map [1P release notes + library pages]
- URLs: https://github.com/ollama/ollama/releases/tag/v0.33.2 (2026-08-27) · v0.33.1 (2026-08-26, "MLX: Qwen3.8 Flash Next support") · v0.33.0 (2026-08-21, Claude Desktop gateway; prefill restore points on recurrent-layer models) · v0.32.15 (2026-08-19, Qwen 3.8 system-message normalization) · library pages fetched 2026-09-01
- Claim: local tags exist for `qwen3.8:27b`, `gemma4:{e2b,e4b,12b,26b,31b}`, `nemotron-3.5-lightning:30b`, `gpt-oss:{20b,120b}`; cloud-only for `kimi-k3`, `kimi-k2.6`, `glm-5.3`, `glm-5.3-flash`, `deepseek-v4-flash` (`0731-cloud`), `deepseek-v4-pro` (`0813-cloud`); `qwen3.8-flash-next` has only `125b-mlx`.
- Relevance: consistent with Kevin's rule that Ollama tags are discovery aliases, not publication artifacts.
- Confidence: 0.85 (tags parsed from HTML).

### F25. Tinker lineup as of 2026-09-01 [1P]
- URLs: https://thinkingmachines.ai/tinker/ · https://tinker-docs.thinkingmachines.ai/tinker/models/
- Claim: Kimi-K2.6 (32K/128K), GLM-5.3 (256K), Nemotron-3.5-Lightning-30B-A3B (64K/256K), Nemotron-3 Nano/Super/Ultra, Qwen3.8-27B (64K/256K), Qwen3.6-35B-A3B, Qwen3.6-27B (retiring 2026-09-02), Qwen3.5-397B-A17B, Qwen3.5-35B-A3B-Base, Qwen3.5-9B, Qwen3.5-9B-Base, Qwen3.5-4B, Qwen3-8B, GPT-OSS-120B/20B, DeepSeek-V3.1, Inkling/Inkling-Small ("Model-agnostic LoRA training from 1B to 1T+ parameters"). Not listed: Kimi-K3, GLM-5.3-Flash, DeepSeek-V4, Gemma 4, Qwen3.8-Flash-Next.
- Relevance: the brief's Tinker list is confirmed except that Qwen3.5-9B/-Base and 35B-A3B-Base are the only Qwen bases; nothing KDA-based is on Tinker.
- Confidence: 0.9 (WebFetch summaries of two first-party pages).

### F26. Research-friendly bases under 10B that load with `trust_remote_code=False` [HF API]
- Claim (all Apache-2.0 unless noted, all native in transformers 5.16.1):
  - `Qwen/Qwen3.5-9B-Base` rev `68c46c4b3498877f3ef123c856ecfde50c39f404` (9.65B, GDN hybrid, VL) · `Qwen3.5-4B-Base` `1001bb4d826a52d1f399e183466143f4da7b741b` (4.66B) · `Qwen3.5-2B-Base` `b1485b2fa6dfa1287294f269f5fb618e03d52d7c` (2.27B) · `Qwen3.5-0.8B-Base` `dc7cdfe2ee4154fa7e30f5b51ca41bfa40174e68` (0.87B), all 2026-04-23; Qwen also released residual SAEs (`Qwen/SAE-Res-Qwen3.5-{9B,2B}-Base-*`, 2026-05-13).
  - `google/gemma-4-E2B` (5.12B total, PLE) · `google/gemma-4-E4B` (8.0B total) — sliding/global.
  - `allenai/Olmo-Hybrid-7B` rev `4f1cc566f9fdf3ce68da2ab6a788a83d89896dcf` (2026-05-26, `olmo_hybrid`, 7.43B) · `allenai/Olmo-3-7B-*` (`olmo3`).
  - `HuggingFaceTB/SmolLM3-3B-Base` rev `d78a42f79198603e614095753484a04c10c2b940`.
  - `tiiuae/Falcon-H1-{0.5B,1.5B,3B,7B}-Base` (`falcon_h1`, Mamba hybrid; Falcon license) · `nvidia/NVIDIA-Nemotron-3-Nano-4B-BF16` (`nemotron_h`).
  - Excluded: `allenai/Bolmo-7B` (custom code), `moonshotai/Kimi-Linear-48B-A3B-Base` (custom code, > 10B total).
- Relevance: the controlled-experiment ladder; note there is no sub-10B KDA base (Gap G1).
- Confidence: 0.9.

### F27. Attention Residuals (the residual-axis move behind K3) [1P arXiv]
- URL: https://arxiv.org/abs/2603.15031 (2026-03-16, Kimi Team)
- Claim: replaces fixed unit-weight residual accumulation with softmax attention over preceding layer outputs (Block AttnRes attends over block-level representations to cut memory); on Kimi Linear 48B/3B trained on 1.4T tokens it gives more uniform output magnitudes and gradients across depth and improved downstream performance; scaling-law experiments claimed consistent across sizes.
- Occupies: learned depth-wise aggregation of residual stream (alongside mHC and Qwen Gated Residual).
- Relevance: the residual axis is now crowded (AttnRes, mHC, GR); a proposal here needs a new factorization, not another gate.
- Confidence: 0.85 (abstract-level).

### F28. First-party benchmark caveats that make cross-vendor tables non-comparable [1P]
- URLs: Kimi K3 card footnotes (SWE-Marathon run on an "H20-calibrated branch"; PostTrainBench on H20 instead of H100; "Claude Fable 5 hit fallbacks on 35% of the tasks") · Qwen3.8 cards ("Problematic tasks were corrected and all baseline models were re-evaluated on the refined benchmark") · GLM-5.3 card (removed pattern-matching anti-cheat checks for PostTrainBench and SWE-Marathon, replaced by LLM inspection) · HF thread https://huggingface.co/zai-org/GLM-5.3/discussions/6 asks whether GLM-5.3 evals used FP8 or BF16 (unanswered).
- Claim: vendors modify harnesses/benchmarks and report competitor numbers under differing conditions.
- Relevance: use only self-run, digest-pinned evals in proposals.
- Confidence: 0.9.

---

## 2. Current HF revision pins (40-hex, as of 2026-09-01)

| Repo | Revision | lastModified | License | Native in transformers 5.16.1? |
|---|---|---|---|---|
| moonshotai/Kimi-K3 | `a590ce090cb049c93a33dfe8c208ec652aa20503` | 2026-08-20 | Kimi K3 License | No (PR #47670 draft) |
| moonshotai/Kimi-K2.6 | `7eb5002f6aadc958aed6a9177b7ed26bb94011bb` | 2026-05-19 | modified-MIT | Yes (`kimi_k25`) |
| moonshotai/Kimi-K2.7-Code | `74797c9c62378b951a1f6fcf5c4631024e9b8bef` | 2026-06-15 | modified-MIT | Yes (`kimi_k25`) |
| moonshotai/Kimi-Linear-48B-A3B-Base | `3b171c17bfc4ee348599b6781a2ca8715c21c8dc` | 2026-01-30 | MIT | No (PR #48250 open) |
| Qwen/Qwen3.8-27B | `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0` | 2026-08-14 | Apache-2.0 | Yes (`qwen3_5`) |
| Qwen/Qwen3.8-Flash-Next | `de4b8e4d43b917e7706784d8bb445c9af86a3540` | 2026-08-27 | Qwen Community 1.0 | Yes (`qwen4_exp`, ≥5.16.0) |
| Qwen/Qwen3.8-2.4T-A95B | `207bd685a7e3696cfaff12ded7c6a7ea0f88c996` | 2026-08-12 | Qwen3.8-Max | Yes (`qwen3_5_moe_text`) |
| Qwen/Qwen3.5-9B-Base / 4B / 2B / 0.8B | `68c46c4b…f404` / `1001bb4d…741b` / `b1485b2f…2d7c` / `dc7cdfe2…4e68` | 2026-04-23 | Apache-2.0 | Yes |
| zai-org/GLM-5.3 | `187fb9fff6319062325ff825627ef6db084d9bc6` | 2026-08-31 | GLM-5.3 License | Yes (`glm_moe_dsa`) |
| zai-org/GLM-5.3-Flash | `03eb5366286afd40d2221b1d9c63a6dd1ba4832e` | 2026-08-31 | MIT | Yes (`glm5_next`) |
| deepseek-ai/DeepSeek-V4-Flash-0731 | `7872f01b1d1fe23eabc4c98b48bffcef5a386062` | 2026-08-01 | MIT | Yes (`deepseek_v4`) |
| deepseek-ai/DeepSeek-V4-Pro-0813 | `72e1d3230f6c080a530b0a1d46f8eb4602340597` | 2026-08-13 | MIT | Yes |
| deepseek-ai/DeepSeek-V4-Flash-Vision-Exp | `6821d6ad3681a4b137b066b76094fa82ebd0a380` | 2026-09-01 | MIT | Yes |
| deepseek-ai/DeepSeek-V4-Flash-Base | `8855555deef230a27a21a8d6f294b7b7497759b6` | 2026-04-27 | (none in card) | Yes |
| google/gemma-4-E2B / E4B / 12B / 26B-A4B / 31B (bases) | `d29ff6b4…1d6f` / `411aa17b…544d9a` / `023679ed…5c08` / `24548b62…990b` / `5bbc2fb1…9d89` | 2026-07-15 | Apache-2.0 | Yes |
| nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16 | `a9904d24bcc1d289a1950fa9d2b978c47cf903b9` | 2026-08-24 | OpenMDW-1.1 | Yes (`nemotron_h`) |
| nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-Base-BF16 | `434456c9a6753f29d24e23c95d622aaf17111b3b` | 2026-08-11 | OpenMDW-1.1 | Yes |
| nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4 | `cc84af2fe71647d87f4486c064f320e1e7535243` | 2026-08-24 | OpenMDW-1.1 | Yes |
| openai/gpt-oss-20b / 120b | `6cee5e81ee83917806bbde320786a8fb61efebee` / `b5c939de8f754692c1647ca79fbf85e8c1e70f8a` | 2025-08-26 | Apache-2.0 | Yes |
| allenai/Olmo-Hybrid-7B | `4f1cc566f9fdf3ce68da2ab6a788a83d89896dcf` | 2026-05-26 | Apache-2.0 | Yes |
| HuggingFaceTB/SmolLM3-3B-Base | `d78a42f79198603e614095753484a04c10c2b940` | 2025-08-14 | Apache-2.0 | Yes |

Serving-stack versions on 2026-09-01: transformers v5.16.1 (2026-08-26), vLLM v0.28.0 (2026-08-26; `v0.28.1rc0` tagged), SGLang v0.5.18 (2026-08-22), Ollama v0.33.2 (2026-08-27).

## 3. Serving support matrix (release-tagged, not nightly)

| Model | transformers 5.16.1 (no remote code) | vLLM 0.28.0 | SGLang 0.5.18 | Ollama local tag | Tinker |
|---|---|---|---|---|---|
| Kimi K3 | no | yes | yes | cloud-only | no |
| Kimi K2.6 | yes | yes | yes | cloud-only | yes |
| Qwen3.8-27B | yes | yes | yes | yes | yes |
| Qwen3.8-Flash-Next | yes (≥5.16.0) | no (0.29+) | branch only | mlx only | no |
| GLM-5.3 | yes | yes (`GlmMoeDsa`) | yes | cloud-only | yes |
| GLM-5.3-Flash | yes | no (0.29+, PR #53906 open) | cookbook yes | cloud-only | no |
| DeepSeek-V4 Flash/Pro | yes | yes | yes | cloud-only | no |
| Gemma 4 (all) | yes | yes | yes | yes | no |
| Nemotron 3.5 Lightning | yes | yes | yes | yes | yes |
| gpt-oss 20B/120B | yes | yes | yes | yes | yes |

## 4. What can be trained on one 8x H100 node (640 GB)

Arithmetic [est]: full FT ≈ 16 B/param (bf16 weights+grads, fp32 Adam m/v) before activations; LoRA ≈ frozen bf16 weights × 1.1 before activations; "serve" = native checkpoint bytes before KV cache. First-party statements are cited where they exist.

| Model | Params (HF safetensors) | Full FT [est] | LoRA bf16 [est] | Serve native | Verdict | First-party support for training |
|---|---|---|---|---|---|---|
| Qwen3.5-0.8B/2B/4B/9B-Base | 0.87–9.65B | 14–154 GB | ≤ 21 GB | ≤ 19 GB | full FT easy | Tinker has 9B-Base/35B-A3B-Base; native transformers |
| Gemma-4-E2B/E4B/12B | 5.1/8.0/12.0B | 82/128/191 GB | ≤ 26 GB | ≤ 24 GB | full FT easy | 12B "allowing the entire model to be fine-tuned in one pass" (card) |
| Olmo-Hybrid-7B, SmolLM3-3B, Falcon-H1 ≤7B | 3–7.6B | ≤ 122 GB | ≤ 17 GB | ≤ 15 GB | full FT easy | native |
| gpt-oss-20b | 20.9B | 335 GB | 46 GB | 10 GB (MXFP4) | full FT ok | Tinker LoRA |
| Qwen3.8-27B | 27.8B | 445 GB | 61 GB | 56 GB | full FT feasible (tight), LoRA easy | Tinker LoRA (64K/256K) |
| Gemma-4-26B-A4B | 26.5B | 425 GB | 58 GB | 53 GB | full FT feasible, LoRA easy | none beyond native |
| Nemotron-3.5-Lightning-30B-A3B(-Base) | 31.6B | 505 GB | 69 GB | 63 GB | full FT borderline (8-bit optimizer/offload), LoRA easy | card: BF16/Base intended for SFT/RL/distillation; NeMo RL/Gym; Tinker LoRA; Unsloth |
| Gemma-4-31B | 32.7B | 523 GB | 72 GB | 65 GB | full FT borderline, LoRA easy | none beyond native |
| gpt-oss-120b | 116.8B | no | 257 GB | 58 GB | LoRA feasible | Tinker LoRA |
| Qwen3.8-Flash-Next | 180.0B | no | 396 GB (tight) | 173 GiB FP8 / 335 GiB BF16 | inference FP8 only; training undocumented | none (no H100 recipe; not on Tinker) |
| GLM-5.3-Flash | 321.3B (FP8) | no | no (bf16 643 GB) | ~306 GiB FP8 | inference only; FP8-frozen LoRA undemonstrated; KDA fallback NaN (F15) | none (not on Tinker) |
| DeepSeek-V4-Flash-0731 | 304.2B (INT8/FP8) | no | no | 304 GB | inference only (tight) | none |
| Kimi-K2.6 | 1.03T (INT4) | no | no | ~513 GB + KV → vendor says 8×H200 | not viable locally | Tinker LoRA only |
| Kimi-K3 | 2.78T (MXFP4) | no | no | 1.56 TB | impossible (≥ 8× GB300) | none |
| GLM-5.3, Qwen3.8-2.4T, DeepSeek-V4-Pro | 0.75–2.45T | no | no | > 640 GB | impossible locally | Tinker LoRA for GLM-5.3 only |

## 5. Occupied axes (do not re-propose without a new delta)

| Axis | What is taken (with who) | URLs |
|---|---|---|
| KDA-based hybrid attention at scale | 3:1 KDA:global interleave (Kimi Linear 48B-A3B; Kimi K3 69 KDA + 24 gated MLA at 2.8T); KDA + DeepSeek Sparse Attention (GLM-5.3-Flash 34:11); FlashKDA kernels | https://huggingface.co/moonshotai/Kimi-K3 · https://huggingface.co/zai-org/GLM-5.3-Flash · https://github.com/MoonshotAI/FlashKDA · https://arxiv.org/abs/2510.26692 |
| Gated DeltaNet + (gated or block-sparse) attention hybrids | Qwen3.5/3.8-27B GDN + gated attention 3:1; Qwen3.8-Flash-Next GDN + QSA (micro-block indexer, 512-block budget) | https://huggingface.co/Qwen/Qwen3.8-27B · https://huggingface.co/Qwen/Qwen3.8-Flash-Next · https://arxiv.org/abs/2608.30320 |
| Multi-stream / learned residual aggregation | Attention Residuals (Kimi); Manifold-Constrained Hyper-Connections (DeepSeek-V4, GLM-5.3-Flash `hc_mult 4`); Qwen Gated Residual (4 branches, rank 320) | https://arxiv.org/abs/2603.15031 · https://arxiv.org/abs/2606.19348 · https://huggingface.co/Qwen/Qwen3.8-Flash-Next |
| Embedding-axis parameter scaling | Per-Layer Embeddings (Gemma 4 E2B/E4B/12B); 51B hashed n-gram embeddings with CPU offload (Qwen3.8-Flash-Next); latent-space MoE (Kimi K3, 3584-dim) | https://huggingface.co/google/gemma-4-E4B · https://huggingface.co/Qwen/Qwen3.8-Flash-Next · https://huggingface.co/moonshotai/Kimi-K3 |
| Compressed/sparse attention for 1M context | DSA (GLM-5/5.2/5.3), Compressed Sparse + Heavily Compressed Attention (DeepSeek-V4), QSA (Qwen) | https://arxiv.org/abs/2606.19348 · https://huggingface.co/zai-org/GLM-5.3 |
| Native low-precision pretraining / QAT checkpoints | MXFP4 weights + MXFP8 activations QAT (Kimi K3); NVFP4 pretraining recipe (Nemotron 3.5); MXFP4 (gpt-oss); FP8 natives (GLM-5.3, DeepSeek-V4) | https://huggingface.co/moonshotai/Kimi-K3 · https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16 |
| Bundled self-speculative decoding | DSpark modules shipped inside checkpoints (DeepSeek-V4 0731/0813, Nemotron NVFP4-DSpark); MTP heads (Qwen3.8, GLM, Gemma 4 `-assistant` drafters); DFlash/DFlash2 in vLLM/SGLang/llama.cpp | https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731 · https://huggingface.co/google/gemma-4-12B-it-assistant |
| Mamba-2 + MoE + attention hybrids with open data/recipes | Nemotron 3.5 Lightning (20T+ tokens, open post-training collection, NeMo Gym recipes); Nemotron 3 Nano/Super/Ultra; Olmo-Hybrid-7B; Falcon-H1 | https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-Base-BF16 · https://huggingface.co/collections/nvidia/nemotron-post-training-v3-6939b7b93382bac738eebd17 |
| Managed LoRA post-training of frontier MoEs | Tinker: Kimi-K2.6, GLM-5.3, Nemotron-3.5-Lightning, Qwen3.8-27B, GPT-OSS, DeepSeek-V3.1, Inkling | https://tinker-docs.thinkingmachines.ai/tinker/models/ |
| License regimes | MIT+MaaS-threshold bespoke licenses (Kimi K3 US$20M; Qwen Community 1.0; Qwen3.8-Max US$50M; GLM-5.3 US$10B) vs pure MIT (GLM-5.3-Flash, DeepSeek-V4) vs Apache-2.0 (Qwen3.8-27B, Gemma 4, gpt-oss) vs OpenMDW-1.1 (Nemotron) | see F2, F9, F13, F14, F16, F17, F18 |

## 6. Open gaps (searched, not found; "no direct prior art found through 2026-09-01 under the coverage in §9")

**G1. A sub-10B open-weight KDA (or KDA+sparse) base checkpoint with native transformers support.**
- Evidence: HF `filter=kimi_linear` → only `moonshotai/Kimi-Linear-48B-A3B-{Base,Instruct}` are official (custom code, 48B total); `filter=glm5_next` → only GLM-5.3-Flash(-BF16) at 320B; `moonshotai`/`zai-org` org listings show no smaller KDA release; transformers 5.16.1 has no `kimi_linear`/`kimi_k3` module (PRs #48250, #47670 open).
- Why open: vendors have only shipped KDA at 48B-A3B and above; the small-scale, native, permissive KDA base that controlled experiments need does not exist.
- Kevin advantage: 8x H100 + digest-pinned Docker/Slurm harness + FlashKDA/fla kernels can pretrain or distill a ≤1B–3B KDA:global hybrid from parallel-corpus-augmented data; Kimi-Linear-48B-A3B-Base (already registered) is a natural teacher; SGLang/vLLM already serve `KimiLinearForCausalLM`.

**G2. Released *base* checkpoints for any 2026 KDA/QSA hybrid.**
- Evidence: `moonshotai/Kimi-K3-Base`, `zai-org/GLM-5.3-Flash-Base`, `Qwen/Qwen3.8-27B-Base`, `Qwen/Qwen3.8-Flash-Next-Base` all return HTTP 401 (nonexistent); GLM-5.3-Flash card says "newly trained base model" but only the post-trained weights are public. Open bases in the window are Mamba-2 (Nemotron-3.5-Lightning-Base), sparse-attention (DeepSeek-V4-Flash-Base, 284B, April), sliding/global (Gemma 4), GDN (Qwen3.5-*-Base, April).
- Why open: vendors are withholding hybrid bases; base-level studies of KDA/QSA (scaling, adaptation from scratch) cannot be run on vendor weights.
- Kevin advantage: Tinker exposes Qwen3.5-9B-Base and 35B-A3B-Base for LoRA; locally, Qwen3.5-9B-Base and Nemotron-3.5-Lightning-Base can be fully fine-tuned; the harness can produce base-level KDA results that no vendor base enables.

**G3. A reproducible LoRA / full-FT memory-and-throughput report for the 2026 hybrids on H100-class nodes.**
- Evidence: Unsloth pages for deepseek-v4, qwen3.8, gemma-4, kimi-k3 contain no fine-tuning requirements (only the Nemotron page has generic guidance); vLLM/SGLang recipes for Qwen3.8-Flash-Next and Kimi K3 document no H100 configurations; the Kimi/Qwen/GLM/DeepSeek model cards contain zero fine-tuning guidance (grep: 0–2 hits, all incidental); transformers' KDA fallback has an open NaN-gradient PR (#48455); HF discussions for these repos have no training reports.
- Why open: everyone is publishing serving recipes; nobody has published pinned, reproducible training-side numbers for GDN/KDA/Mamba-2 hybrids at the 27B–30B scale.
- Kevin advantage: 8x H100 with SIGUSR1-checkpoint/resume discipline can produce the first digest-pinned LoRA and full-FT report for Qwen3.8-27B (GDN), Nemotron-3.5-Lightning (Mamba-2), Gemma-4-26B-A4B (MoE), and FP8-frozen LoRA on GLM-5.3-Flash (KDA), cross-checked against Tinker's GLM-5.3/Qwen3.8-27B LoRA.

**G4. Text-translation (FLORES/WMT-style) evaluation or translation fine-tuning of the 2026 open hybrids.**
- Evidence: grep of the ten first-party cards (Kimi K3, Qwen3.8-27B, Qwen3.8-Flash-Next, GLM-5.3, GLM-5.3-Flash, DeepSeek-V4-Flash/Pro, Nemotron 3.5 BF16/Base, Gemma 4 E4B) for `FLORES|WMT|translat` → 0 hits in the Kimi/Qwen/GLM/DeepSeek cards; Nemotron's card lists translation *training data* (TAUS 1,618,055 rows; 389.9B-token Qwen-translated synthetic crawl; MT of News Commentary) and 7 post-training languages but reports no MT benchmark; Gemma 4 reports only speech-to-translated-text; Qwen3.8-Flash-Next thread reports Russian regressions (https://huggingface.co/Qwen/Qwen3.8-Flash-Next/discussions, 2026-08-28).
- Why open: 2026 hybrid releases are benchmarked on coding/agentic suites; translation quality across attention families (KDA vs GDN vs Mamba-2 vs sliding/global) at matched size is unmeasured.
- Kevin advantage: General Translation's parallel multilingual data enables the first controlled MT benchmark and translation-aware adaptation study across the attention families; Qwen3.5 bases (0.8B–9B), Gemma-4 E2B/E4B, Olmo-Hybrid-7B, Falcon-H1 provide a matched-size ladder that fully fits the node.

**G5. Independent (non-vendor) replication of the headline architecture-efficiency claims (Kimi K3 "2.5× scaling efficiency"; Qwen3.8-Next "1/9 training FLOPs") at any scale.**
- Evidence: arXiv `all:"Kimi K3"` (15 results) are all third-party application/benchmark papers; `all:"Qwen3.8"` (10 results) contains only the Qwen team's own design paper as architectural work; Semantic Scholar was unavailable (429 throughout); no independent ablation of AttnRes/GR/n-gram embeddings found in HF discussions or GitHub.
- Why open: claims are first-party only, less than six weeks old, and made at scales nobody can replicate.
- Kevin advantage: 8x H100 suffices for ≤1B-scale replications with Qwen3.5-0.8B/2B-Base controls; fla/FlashKDA and transformers' native `qwen4_exp`/`glm5_next` modules provide reference implementations of GR, QSA, mHC and KDA to ablate.

## 7. Negative results, retractions, and caveats found
- No retractions found for any of the target models in the window (coverage limited; see §9).
- Qwen team's own paper: n-gram vocabulary scaling lowers loss but downstream accuracy saturates (F10).
- transformers KDA fallback NaN gradients (F15); v5.15 made linear-attention kernels opt-in (F21).
- Qwen3.8-27B glitch tokens, thinking loops, 1,584-token prefix-cache granularity (F12) [3P].
- GLM-5.3 weights delayed ~2 weeks for safety review; "More refusals than 5.2" and FP8-vs-BF16 eval ambiguity threads (F13, F28) [3P].
- GLM-5.3-Flash vLLM nightly load crash and `pe_dim must be 64 for fp8_ds_mla` on RTX PRO 6000 (HF discussions #26, #19) [3P].
- Kimi K3 community "8× H100" deployment claim contradicted by checkpoint size (F4) [3P]; K3 eval footnotes disclose H20 hardware and 35% competitor fallbacks (F28).
- gpt-oss: no new weights since 2025-08-26 (F20). Nemotron 3.5 Lightning: no technical report (F19). Qwen3.8: no bases, no sub-27B (F11).
- HF discussion "Useless for coding" on Nemotron 3.5 (2026-08-14) is opinion; NVIDIA's own card shows SWE-bench Multilingual 39.33 vs Qwen 3.6 35B A3B 63.40 (first-party table), i.e., the vendor itself reports the coding gap.

## 8. Exact queries run (modalities: HF API, GitHub API, arXiv API, Semantic Scholar API, X bookmarks via `ft`, WebSearch, WebFetch/Jina page opens)

HF model search (`/api/models?search=`): `Kimi-K2.6`, `Kimi-K3`, `moonshotai`, `Qwen3.8`, `Qwen/Qwen3.8`, `Qwen3.5`, `GLM-5.3`, `zai-org/GLM-5`, `gpt-oss`, `openai/gpt-oss`, `Nemotron-3.5`, `nvidia/Nemotron-3`, `DeepSeek-V4`, `deepseek-ai/DeepSeek-V4`, `gemma-4`, `google/gemma-4`, `Lightning-1.4B`, `author=nvidia&search=3.5`, `author=Qwen&search=3.8`.
HF org listings (`?author=`): Qwen, moonshotai, zai-org, deepseek-ai, google, nvidia, openai, allenai, HuggingFaceTB, tiiuae.
HF tag filters (`?filter=`): kimi_linear, glm5_next, qwen4_exp, nemotron_h, olmo_hybrid, falcon_h1.
HF per-repo metadata/config/README/LICENSE/commits/discussions for the ~40 repos named in §1–§2; existence probes for `Qwen/Qwen3.8-{9B,4B,2B}`, `Qwen3.8-27B-Base`, `Qwen3.8-Flash-Next-Base`, `nvidia/NVIDIA-Nemotron-3.5-Lightning-1.4B-A0.1B`, `nvidia/Nemotron-3.5-Nano`, `moonshotai/Kimi-K3-Base`, `zai-org/GLM-5.3-Flash-Base`, `google/gemma-4-E4B-text`; datasets `nvidia/Nemotron-Post-Training-*`, collections `owner=nvidia`.
GitHub API: releases for vllm-project/vllm, sgl-project/sglang, ollama/ollama, huggingface/transformers; release bodies vLLM v0.27.0/v0.28.0, SGLang v0.5.17/v0.5.18, Ollama v0.32.15–v0.33.2, transformers v5.14.0–v5.16.0; models-dir listings (transformers v5.16.1, vLLM v0.28.0, SGLang v0.5.18), vLLM `registry.py` @v0.28.0, SGLang tree @v0.5.18; PR searches: transformers "Kimi K3", "Kimi Linear"; vLLM "Qwen4Exp"/"Qwen3.8-Flash-Next", "GLM-5.3", "Nemotron 3.5"; SGLang "GLM-5.3-Flash", "Qwen3.8-Flash-Next"/"Qwen4Exp"; llama.cpp "Kimi K3", "GLM-5.3-Flash", "Qwen3.8", "Nemotron 3.5"; PRs #47670, #48250, #48455 (transformers), #50000 (vLLM), #32541 (SGLang); repos MoonshotAI/Kimi-K3, MoonshotAI/FlashKDA, QwenLM/Qwen3.8-Flash-Next, QwenLM/Qwen3.8, zai-org/GLM-5, NVIDIA-NeMo/Gym.
arXiv API (22 attempts, 7 succeeded after 429s): `all:"open-weight" AND all:"hybrid" AND all:attention`; `ti:"Kimi" OR ti:"Qwen3" OR ti:"GLM-5" OR ti:"DeepSeek-V4" OR ti:"Nemotron" OR ti:"Gemma"`; `ti:"Kimi K3"…`; `ti:"Qwen3.8"…`; `ti:"GLM-5"…`; `ti:"DeepSeek-V4"…`; `ti:"Gemma 4"…`; `ti:"Nemotron 3.5"…`; `abs:"open-weight" AND abs:"hybrid" AND abs:"linear attention"`; `all:"Kimi K3"` ✓; `all:"Qwen3.8"` ✓; `all:"DeepSeek-V4"`; `all:"Gemma 4"`; `all:"Nemotron 3.5"` ✓; `all:"GLM-5.3"`; `ti:"Kimi K3" OR ti:"Kimi-K3"` ✓; `au:"Kimi Team"` ✓; `ti:Nemotron` ✓; `id_list=2607.24653,2606.19348,2602.15763,2607.02770,2608.30320,2603.15031,2510.26692` ✓.
Semantic Scholar (13 attempts, all HTTP 429): "Kimi K3 technical report", "Qwen3.8 technical report", "DeepSeek-V4 technical report", "Gemma 4 technical report", "Nemotron 3.5 hybrid Mamba transformer", "GLM-5 technical report", "gpt-oss model card", "Kimi K3", "Qwen3.8", "DeepSeek-V4", "Nemotron 3.5 Lightning", "Gemma 4", "Kimi K3 technical report Moonshot".
X bookmarks (`ft search`, 38 queries): "Kimi K3", "Qwen3.8"(rejected), "GLM-5.3"(rejected), "DeepSeek V4", "Gemma 4", "Nemotron 3.5"(rejected), "gpt-oss"(rejected), "vLLM", Kimi, Qwen, GLM, Nemotron, "gpt oss", DeepSeek, Gemma, Ollama, SGLang, Tinker, LoRA, "fine-tune", H100, transformers, Unsloth, "open weights", KDA, FlashKDA, 27B, "hybrid attention", "sparse attention", MXFP4, PorTAL, Inkling, DSpark, speculative, "Gated DeltaNet", Moonshot, Zhipu, benchmark.
WebSearch (10 ran; 8 more refused after the session budget hit 200/200): "Kimi K3 open weights release license Moonshot August 2026"; "Qwen3.8 release blog Qwen3.8-27B Qwen3.8-Flash-Next architecture"; "GLM-5.3 Zhipu Z.ai release open weights GLM-5.3-Flash"; "DeepSeek V4 Pro 0813 release Flash-Vision-Exp DSpark"; "Gemma 4 release Google DeepMind 26B-A4B 31B E4B open weights"; "Nemotron 3.5 Lightning 30B-A3B NVIDIA release hybrid Mamba"; "transformers v5 trust_remote_code custom code policy 2026 modular models"; "Tinker Thinking Machines supported models list Kimi K3 Qwen3.8 GLM-5.3 LoRA"; refused: Kimi K3 contamination/overfit; Qwen3.8-27B fine-tune 8xH100; Nemotron 3.5 fine-tuning recipe; Kimi K2.6 8xH100; Gemma 4 26B-A4B fine-tuning; Qwen3.8-27B regression/dispute; transformers Kimi K3 native PR; DeepSeek V4 LoRA H100.
WebFetch page opens (33): lmsys Kimi K3 day-0 blog; qwen.ai blog (JS, empty); explainx GLM-5.3 delay; DeepSeek API changelog; Tinker marketing + docs (2 pages + 404 slug); OpenMDW-1.1; Gemma 4 model card; arXiv abs 2606.19348, 2602.15763, 2607.02770, 2608.30320, 2607.24653, 2603.15031; arXiv search UI ×3 (429); vLLM recipes Kimi-K3, Kimi-K2.6, Qwen3.8-27B, Qwen3.8-Flash-Next, GLM-5.3-Flash; SGLang cookbooks Nemotron3.5-Lightning, Qwen3.8-Flash-Next; Unsloth deepseek-v4, qwen3.8, nemotron-3.5, gemma-4, kimi-k3; kimi.com/kimi.ai blog; z.ai GLM-5.3-Flash blog (JS, empty). Jina reader: 4 attempts, all blocked (anonymous queries refused for this network).

## 9. Coverage limits (honest)
- WebSearch budget for the session was exhausted (200/200) after this cell's 10th query; 8 planned searches — including all dedicated "contamination/retraction/regression" searches — were not run. Negative-result coverage therefore rests on HF discussions, GitHub PRs and first-party footnotes only.
- Semantic Scholar returned HTTP 429 on all 13 attempts; no citation-count or peer-review status could be pulled from it. No peer-reviewed venue publication was identified for any target model; all architecture claims are first-party preprints/cards.
- arXiv API was rate-limited for most of the session; 7 of 22 queries succeeded (late in the run), so arXiv coverage is title/author-level for Kimi K3, Qwen3.8, Nemotron, plus the six abs pages listed. Full PDFs of the Kimi K3, Qwen3.8-Next, Gemma 4 and DeepSeek-V4 reports were not read (abstract/README level only).
- Jina reader refused anonymous requests from this network (AS7018), and the qwen.ai and z.ai blogs are JS-rendered; architecture facts for Qwen3.8 and GLM-5.3(-Flash) come from HF READMEs and `config.json`, not the blogs.
- Tinker, vLLM-recipe, SGLang-cookbook, Unsloth and OpenMDW pages were read through WebFetch summaries, not raw HTML; model lists/flags may be incomplete.
- Ollama tags were parsed heuristically from library HTML.
- Nemotron 3.5 Lightning HF API metadata required a bearer header (empty token worked); the `Nemotron-Post-Training-v3` umbrella dataset ids return 401 (gated), while the 49 collection member datasets report `gated: false` — I did not verify downloadability.
- Memory/feasibility numbers in §4 are my arithmetic from HF safetensors totals; nothing was measured on the node. Whether Kimi K3's remote code (config `transformers_version 4.56.2`) still imports under transformers 5.x was not tested.
- X-bookmark coverage is thin for Qwen3.8, GLM-5.3, Nemotron, DeepSeek-V4 (Kevin's bookmarks skew to Kimi K3, PorTAL, agents).
- Date basis: all "as of" statements are 2026-09-01 UTC; vLLM `v0.28.1rc0` and open PRs may have merged since.
