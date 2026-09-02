# Cell `tinker-rl` — Thinking Machines Tinker as a research substrate for 1T-parameter LoRA/RL (sweep 2026-09-01)

Scope: what Tinker actually exposes (models, LoRA surface, RL/custom-loss primitives, context, pricing, checkpoint export/expiry, known limitations, first-party case studies), how it compares with Together / Fireworks / Modal / Prime Intellect, and — the question that matters for CoTCodec — which architecture-adjacent experiments are *possible* through LoRA-only access to a 1T model (Kimi-K2.6) and which are *impossible*.

Honesty conventions used below: **[1P]** = first-party claim (vendor docs/blog/README); **[PR]** = peer-reviewed; **[arXiv]** = preprint, not peer-reviewed; **[GH]** = GitHub source/issue; **[derived]** = my arithmetic from a cited table. Docs pages are undated; "fetched 2026-09-01" is recorded where the page carries no date. Every numeric claim has a URL. Prior sweep cutoff was 2026-08-10; items after that date are marked **[post-08-10]**.

---

## 1. Findings (30)

### A. What Tinker exposes (primary docs + SDK source)

**F1. Model lineup, contexts, and per-token prices (Kimi-K2.6 at 32K/128K; GLM-5.3 only at 256K).** [1P, docs, fetched 2026-09-01]
- URL: https://tinker-docs.thinkingmachines.ai/tinker/models/ ; machine-readable: https://tinker-docs.thinkingmachines.ai/tinker/models.json (29 entries)
- Claim (USD per 1M tokens, prefill / sample / train): `moonshotai/Kimi-K2.6` 32K context: $2.205 / $5.49 / $4.84; `moonshotai/Kimi-K2.6:peft:131072` 128K: $5.15 / $12.81 / $15.40; `zai-org/GLM-5.3:peft:262144` (753B/40B active, the only GLM-5.3 entry) 256K: $4.86 / $12.15 / $14.58; `deepseek-ai/DeepSeek-V3.1` 32K: $1.695 / $4.215 / $3.718; `thinkingmachines/Inkling` (975B/41B) 64K: $1.87 / $4.68 / $5.61 (50% limited-time discount, list $3.74 / $9.36 / $11.22); `Qwen/Qwen3.5-397B-A17B` 64K: $3.00 / $7.50 / $6.60; `nvidia/NVIDIA-Nemotron-3-Ultra-550B-A55B-BF16` 64K: $2.49 / $6.225 / $5.478 (discounted). Cached prefill gets an 80% discount. Checkpoint storage $0.10/GB-month. Serverless inference (beta) exists only for Inkling/Inkling-Small at NVFP4.
- Retirements: Kimi-K2.5 retired 2026-07-12; Kimi-K2-Thinking, all Llama, Qwen3-32B/30B/235B, DeepSeek-V3.1-Base retired 2026-06-12; Qwen3.6-27B retiring 2026-09-02 (https://tinker-docs.thinkingmachines.ai/tinker/model-deprecations/).
- Occupies: managed LoRA post-training on 400B–1T MoEs (Kimi-K2.6, GLM-5.3, DeepSeek-V3.1, Inkling, Nemotron Ultra).
- Relevance: the repo's `experiments/tinker/*.yaml` prices (verified 2026-08-10: 2.205/5.49/4.84 for Kimi-K2.6; 0.33/1.005/0.737 for Qwen3.5-4B) are still current. Kimi-K2.6's native 256K context is *not* available on Tinker (32K or 128K only); GLM-5.3 arrived on Tinker within ~6 days of its HF release (HF `createdAt` 2026-08-25). Confidence 0.95.

**F2. The whole LoRA configuration surface is five fields; no per-module targeting, no alpha, no documented rank cap.** [1P, GH SDK source + docs]
- URLs: https://github.com/thinking-machines-lab/tinker/blob/main/src/tinker/types/lora_config.py ; https://tinker-docs.thinkingmachines.ai/tinker/api-reference/serviceclient/ ; https://tinker-docs.thinkingmachines.ai/tinker/lora-primer/
- Claim: `LoraConfig(rank: int, seed: Optional[int], train_unembed=True, train_mlp=True ["including MoE layers"], train_attn=True)`. `create_lora_training_client(base_model, rank=32, seed=None, train_mlp=True, train_attn=True, train_unembed=True)`. Default rank 32. The LoRA primer states "LoRA performs equivalently to FullFT for reinforcement learning even with small ranks" and "the optimal learning rate does not depend on the LoRA rank". No maximum rank is documented anywhere in the 154 non-API sitemap pages I fetched; ranks up to 128 appear in first-party recipes (distillation) and the SFT sweep.
- Exported adapters carry `lora_alpha: 32` fixed and `target_modules: "all-linear"` (third-party Kimi-K2.6 export: https://huggingface.co/barbonara/corin-kimi-k26-pro-sft/blob/main/adapter_config.json , r=8, 2026-08-19 **[post-08-10]**).
- Occupies: the "which modules get LoRA" design axis is fixed by the vendor at three coarse groups.
- Relevance: module-level ablations (single layer, single expert, q-only) and LoRA-structure variants (DoRA, PiSSA/MiLoRA init, rank patterns) are impossible on Tinker. Confidence 0.9.

**F3. Tinker's MoE LoRA is a "shared-outer" scheme; Kimi-K2.6 rank-1 adapter = 146.7M params, rank-32 ≈ 4.69B (≈0.47% of 1T).** [1P, GH]
- URL: https://github.com/thinking-machines-lab/tinker-cookbook/blob/main/tinker_cookbook/hyperparam_utils.py
- Claim (verbatim docstring): "For MoE expert layers, Tinker uses a shared-outer LoRA scheme: the LoRA factor connected to the model hidden dimension is shared across experts, while the other factor remains expert-specific." Per-rank counts for `moonshotai/Kimi-K2.6`: mlp 144,583,680; attn 1,940,288; unembed 171,008. **[derived]** rank 8 → 1,173,564,928 params; the third-party r=8 Kimi-K2.6 adapter on HF is 4,688,923,008 bytes = exactly 4 bytes/param (fp32 storage), which cross-validates the table. Inkling per-rank mlp 154,705,920; DeepSeek-V3.1 mlp 94,307,328; Nemotron-3-Ultra mlp 254,529,536.
- Occupies: a specific factorization of MoE LoRA (one shared hidden-dim factor, per-expert other factor). This is the single most architecture-relevant fact about Tinker: on Kimi-K2.6, 98.6% of trainable LoRA parameters sit in the (expert-specific) MoE MLP factors.
- Relevance: it defines what "adaptation" means on Tinker at 1T: expert-side low-rank deltas with a shared projection. Nothing I could find measures how this scheme interacts with routing or expert specialization (Gap G1). Confidence 0.9.

**F4. Custom losses see only target-token log-probs; `forward_backward_custom` = forward + surrogate weighted cross-entropy (1.5× FLOPs, up to 3× wall).** [1P, docs + SDK]
- URLs: https://tinker-docs.thinkingmachines.ai/tinker/losses/custom/ ; https://tinker-docs.thinkingmachines.ai/tinker/losses/ ; https://tinker-docs.thinkingmachines.ai/tinker/api-reference/trainingclient/ ; https://github.com/thinking-machines-lab/tinker/blob/main/src/tinker/types/loss_fn_type.py
- Claim: built-in `LossFnType = {"cross_entropy","importance_sampling","ppo","cispo","dro"}`; RL losses accept exactly `target_tokens, logprobs, advantages` ("passing an extra key such as weights is rejected by the server"); losses are summed over tokens, no KL term inside (KL can be folded into the reward). `forward_backward_custom(data, loss_fn, loss_type_input='logprobs')` — "Currently the only supported value is 'logprobs'"; the client-side torch function receives per-datum logprob tensors `[N]` or `[N,K]` (multi-target candidate sets), Tinker "does NOT pickle your function", it computes `dLoss/dLogprobs` client-side and replays a linear surrogate `sum(logprobs × grad_outputs)` server-side. Cost: "1.5x as many FLOPs ... up to 3x as long (wall time)". The SDFT recipe states plainly: "The Tinker API does not expose full-vocabulary logits." (https://tinker-docs.thinkingmachines.ai/cookbook/recipes/sdft/)
- Occupies: any objective that is a differentiable function of selected-token log-probs (DPO, Bradley–Terry, renormalized multiple-choice CE, top-K distillation, arbitrary RL surrogates).
- Relevance: exact full-vocabulary KL, entropy bonuses over the full distribution, and representation-level losses are impossible; top-K (K user-chosen, example K=20) approximations are the ceiling. Confidence 0.95.

**F5. No hidden states, activations, or gradients are exposed; the only interpretability-adjacent telemetry is MoE expert-balance metrics.** [1P docs + GH issue]
- URLs: https://tinker-docs.thinkingmachines.ai/cookbook/recipes/true-thinking-score/ ("This requires residual-stream access which Tinker does not expose"); https://github.com/thinking-machines-lab/tinker/blob/main/src/tinker/types/forward_backward_output.py ; https://github.com/thinking-machines-lab/tinker-feedback/issues/141 (2026-08-16, open, no maintainer reply as of 2026-09-01) **[post-08-10]**; https://github.com/thinking-machines-lab/tinker-feedback/issues/96 (gradient norm metric request, 2026-03-25, open)
- Claim: `ForwardBackwardOutput.metrics` records, during MoE training only: `e_frac_with_tokens:mean`, `e_frac_oversubscribed:mean`, `e_max_violation:mean/max`, `e_min_violation:mean` ("Decreasing over time is concerning (routing collapse)"). Issue #141 asks for "literal hidden-state tensors" and "native LoRA parameter-to-activation tangents" (JVP/VJP) — unanswered.
- Occupies: nothing new; documents an absence.
- Relevance: probes, steering vectors, activation patching, representation-similarity losses, and latent-reasoning (continuous thought) experiments cannot run on Tinker. The expert-balance metrics are, however, a free routing-health signal for Kimi-K2.6 runs (Gap G5). Confidence 0.95.

**F6. Optimizer is fixed: AdamW only (`learning_rate, betas, eps, weight_decay`, default wd 0.0).** [1P docs]
- URL: https://tinker-docs.thinkingmachines.ai/tinker/api-reference/trainingclient/ ("The Adam optimizer used by tinker is identical to torch.optim.AdamW")
- Occupies: nothing new. Relevance: learned optimizers, Muon-style updates, per-parameter-group LRs, and any "portable update rule" test (repo direction 16) are impossible on Tinker itself. Confidence 0.9.

**F7. Inputs are token ids, images, or Inkling audio "dmel" tensors — no raw embedding injection.** [1P GH SDK]
- URL: https://github.com/thinking-machines-lab/tinker/blob/main/src/tinker/types/model_input_chunk.py (`EncodedTextChunk | ImageAssetPointerChunk | ImageChunk | DmelChunk`)
- Relevance: soft prompts, prefix-tuning with learned embeddings, and Coconut-style continuous-thought feedback are impossible; only discrete tokens (and images/audio for VLM/Inkling) can be fed. Confidence 0.85.

**F8. External adapters cannot be imported; weights load only from `tinker://` paths.** [1P GH SDK + issue]
- URLs: https://github.com/thinking-machines-lab/tinker/blob/main/src/tinker/types/load_weights_request.py ; https://github.com/thinking-machines-lab/tinker/blob/main/src/tinker/types/create_model_request.py ; https://github.com/thinking-machines-lab/tinker-feedback/issues/104 (2026-04-22, open, no reply)
- Claim: `LoadWeightsRequest.path`: "A tinker URI for model weights at a specific step"; `CreateModelRequest` accepts only `base_model`, `user_metadata`, `lora_config`. A user asking how to import a PEFT `adapter_model.safetensors` has no answer; the merged-model workaround was "rejected ... as an unsupported base_model".
- Relevance: PorTAL/Text-to-LoRA-style *generated* adapters cannot be evaluated or continued on Tinker; the adapter flow is one-way (export only). Confidence 0.85.

**F9. Checkpoint lifecycle: optional TTL (default never expires), $0.10/GB-month, signed-URL tar download, PEFT or merged export; Kimi-K2.6 merge = INT4 dequant → merge → requant over 595 GB–1 TB, ~30–60 min on NFS; vLLM 0.18 cannot serve Kimi-K2.6 LoRA.** [1P docs + GH]
- URLs: https://tinker-docs.thinkingmachines.ai/tutorials/core-concepts/weights/ ; https://tinker-docs.thinkingmachines.ai/tinker/cli/checkpoint/ ; https://tinker-docs.thinkingmachines.ai/tutorials/deployment/lora-adapter/ ; https://github.com/thinking-machines-lab/tinker-cookbook/blob/main/tinker_cookbook/weights/README.md
- Claim: `save_state`/`save_weights_for_sampler(name, ttl_seconds=None)`; `tinker checkpoint set-ttl --ttl 604800`; deletion "permanent and cannot be undone" (optional org backup feature). Export: `adapter_config.json` + `adapter_model.safetensors`; merged `W_merged = W_base + (B @ A) * (alpha / rank)`. Weights README: Kimi-K2.6 "Merge ✅ Adapter ✅ INT4 pack-quantized ... vLLM LoRA not yet supported"; "For Kimi K2.6 (595 GB–1 TB), always use the default shard strategy"; DeepSeek-V3.1 adapter export ❌ ("vLLM/SGLang don't support DeepSeek LoRA"). Recommended Kimi-K2.6 LR "~5e-4 LoRA / ~5e-5 full; Not yet calibrated in get_lr".
- Occupies: the standard PEFT interchange format for 1T adapters.
- Relevance: Kevin *can* pull Kimi-K2.6 adapters (1.2–4.7B params) to the H100 node for weight-space analysis (per-expert ΔW SVD) without hosting the 1T base; he *cannot* cheaply serve a Kimi LoRA locally (595 GB INT4 base > 8×80 GB HBM; vLLM LoRA unsupported). Confidence 0.9.

**F10. Multi-tenant "clock cycle" execution; latency not guaranteed; official advice is to never wrap requests in client timeouts/retries.** [1P docs, dated 2026-08-03 in changelog]
- URLs: https://tinker-docs.thinkingmachines.ai/tinker/under-the-hood/ ; https://tinker-docs.thinkingmachines.ai/changelog/
- Claim: a worker pool runs forward-backward + optimizer steps "in lock-step" shared across users; "even if training with a small batch, you'll still see the same step time as a large batch"; "Tinker is optimized for throughput rather than latency"; "A request that normally takes a minute can legitimately take much longer".
- Relevance: wall-clock is not a controllable or reportable experimental variable on Tinker; the repo's SIGUSR1-checkpoint/resume discipline must assume unbounded step latency. Confidence 0.9.

**F11. Extended-context and resume mechanics: `:peft:<ctx>` model ids; `base_model` override on resume (SDK 0.24.1, 2026-08-06); cookbook 0.5.4 (2026-08-11) adds Nemotron-3.5-Lightning; cookbook 0.5.5 on PyPI 2026-08-22; SDK 0.27.0 on PyPI 2026-09-01.** [1P changelog + PyPI] **[post-08-10]**
- URLs: https://tinker-docs.thinkingmachines.ai/changelog/ ; https://pypi.org/pypi/tinker/json ; https://pypi.org/pypi/tinker-cookbook/json ; https://github.com/thinking-machines-lab/tinker-cookbook/commits/main (Qwen3.8 support 2026-08-20; forecasting recipe 2026-08-31)
- Relevance/kill-shot for the repo: `memory.json` pins `tinker==0.23.3`; tinker-feedback #120 (2026-06-08) shows the server rejects out-of-date SDKs with HTTP 400 "SDK version no longer supported". A digest-pinned client image will rot; the harness needs an SDK-version doctor. Confidence 0.85.

### B. First-party evidence about LoRA at scale on Tinker

**F12. "LoRA Without Regret" (Schulman et al., TML blog, 2025-09-29): RL matches FullFT at rank 1; attention-only LoRA underperforms; LoRA LR ≈ 10× FullFT; batch-size penalty not fixed by rank; ~2/3 FLOPs.** [1P blog]
- URL: https://thinkingmachines.ai/blog/lora/
- Claim (quotes): "LoRA fully matches the learning performance of FullFT when running policy gradient algorithms for RL, even with ranks as low as 1"; "Attention-only LoRA significantly underperforms MLP-only LoRA"; "For datasets that exceed LoRA capacity, LoRA underperforms FullFT"; "This penalty is not mitigated by increasing LoRA rank"; optimizer found "a multiplier of 9.8 for LoRA over FullFT". Authors state "Our theoretical understanding of LoRA learning rates and training dynamics is limited" and that MoE-LoRA variants remain underexplored.
- Independent status: a Hugging Face TRL reproduction and the `michaelbzhu/lora-without-regret` repo were surfaced by search but not opened here (see coverage limits).
- Occupies: "low-rank suffices for RL" axis. Relevance: the information-theoretic argument (O(1) bits/episode) is exactly why a 1T model can be RL-tuned with a ~147M-parameter rank-1 adapter. Confidence 0.85 (first-party; replication unverified by me).

**F13. TML's own SFT sweep swept Kimi-K2.6 only at ranks 1/2/4; best rank 2, lr 3e-4, test NLL 0.5578 on tulu3 (batch 128, 780 steps); 303–528 min wall per run; lr 3e-3 diverges.** [1P GH]
- URL: https://github.com/thinking-machines-lab/tinker-cookbook/blob/main/tinker_cookbook/recipes/chat_sl/results/sft_sweep.md
- Claim: every ≥235B model (Kimi-K2.6, Kimi-K2.5, DeepSeek-V3.1, Qwen3.5-397B, Nemotron-3-Ultra, Llama-70B) was swept at ranks {1,2,4} only; ≤35B models at {1,4,16,64} or {4,16,64,128}. Key finding quoted: "Large models (small ranks 1–4) tend to prefer moderate LRs (1e-4 to 3e-4)".
- Relevance: rank sensitivity above 4 on 1T models is *unmeasured* by the vendor (Gap G6); the rank-32 defaults used in the text-to-SQL and harbor recipes are untuned. Confidence 0.9.

**F14. Harbor RL recipe on Kimi-K2.6 (rank 32, lr 1e-5, 4×8 groups, 8K max tokens, 32K context): baseline eval SWE-Bench Verified 29.0% pass with 60.6% ERROR (context overflow), Terminal-Bench 2.0 15.7%; 7/89 TB tasks silently zeroed by a fixture bug (issue #889, 2026-08-14).** [1P GH + community bug] **[post-08-10]**
- URLs: https://github.com/thinking-machines-lab/tinker-cookbook/blob/main/tinker_cookbook/recipes/harbor_rl/README.md ; https://github.com/thinking-machines-lab/tinker-cookbook/blob/main/tinker_cookbook/recipes/harbor_rl/train.py ; https://github.com/thinking-machines-lab/tinker-cookbook/issues/889
- Claim: "All ERRORs are context window overflow (prompt_tokens + max_tokens > 32768)"; `context_overflow_reward = -0.1`; hyperparams table lists "Multi-turn RL | Kimi-K2.6 | 1e-5 | 8x4 | 32" (https://github.com/thinking-machines-lab/tinker-cookbook/blob/main/skills/research/references/hyperparams.md).
- Relevance: the 32K default context is the binding constraint for agentic RL on Kimi-K2.6 on Tinker; the 128K tier costs ~3× per token. Confidence 0.85.

**F15. TML news 2026-08-27 (UIUC + Bridgewater AIA Labs + TML): Kimi-K2.6, LoRA rank 32 on Tinker, CISPO; Arcwise-Plat-SQL 91.37% greedy / 92.97% SC-16 vs 92.96% human; $0.035/query; execution-match rewards had 32.8% false positives; 61.1% of BIRD Train had annotation errors.** [1P news] **[post-08-10]**
- URL: https://thinkingmachines.ai/news/putting-task-expertise-into-rl/
- Occupies: task-expert RL on a 1T model via LoRA; reward-cleaning as the lever.
- Relevance: the strongest public evidence that rank-32 LoRA RL on Kimi-K2.6 reaches human-level on a hard structured task; also a warning that reward false positives dominate. Confidence 0.85.

**F16. TML news 2026-06-30 (Bridgewater AIA Labs): Qwen3-235B on Tinker with GRPO + interleaved batching + CISPO asymmetric clipping + on-policy distillation with dynamic teacher promotion: 84.7% vs 78.2% best frontier model; 13.8× cheaper; ablations +12.1 / +10.1 / +3.1 points.** [1P news]
- URL: https://thinkingmachines.ai/news/learning-to-replicate-expert-judgment-in-financial-tasks/
- Occupies: interleaved multi-task RL + on-policy distillation recipe on Tinker. Confidence 0.8.

**F17. Tinker homepage case studies (undated, fetched 2026-09-01): Glean "Waldo" 50% lower latency / 25% fewer tokens; Chroma Context-1 from gpt-oss-20b up to 10× tokens/s; Lightning Rod calibration error −70%, Brier skill 0%→27%; Mantic gpt-oss-120b on ~10k forecasting questions; Trajectory 25% on APEX-Agents ("nine points beyond unaugmented SDPO"); MIT SDFT 70.6% vs 63.2% tool use; Stanford monitors +35 points; Axiom 12/12 Putnam (Dec 2025).** [1P marketing page]
- URL: https://thinkingmachines.ai/tinker/
- Relevance: all are LoRA results; none reports rank, and none is an architecture change. Confidence 0.7 (marketing summaries; underlying pages not opened).

**F18. Inkling (TML, 2026-07-15) and Inkling-Small (2026-07-30): 975B/41B active, 66 layers, 6-of-256 routed + 2 shared experts, interleaved sliding-window:global 5:1, relative positions (no RoPE), 1M context, Apache-2.0; Small 276B/12B, 42 layers; on Tinker at 64K/256K.** [1P news + HF card]
- URLs: https://thinkingmachines.ai/news/introducing-inkling/ ; https://huggingface.co/thinkingmachines/Inkling (lastModified 2026-07-23) ; https://huggingface.co/thinkingmachines/Inkling-Small (created 2026-07-27) ; https://thinkingmachines.ai/blog/a-safe-path-to-open-weights/ (2026-07-31)
- Relevance: an Apache-2.0 975B hybrid-attention MoE whose vendor also runs the LoRA service; "A Safe Path" frames Tinker as a stage "between inference API access and full open weights" and announces Tinker safety grants (news 2026-08-24). Confidence 0.85.

### C. Independent / adversarial literature on LoRA capacity and RL (what could kill a LoRA-only claim)

**F19. "Procedural Knowledge Is Not Low-Rank" (arXiv 2607.21612, submitted 2026-05-23): LoRA r=16–128 fails uniformly on multi-step procedural tasks (task success ≤2.54 vs 4.11 FullFT, p<0.001); FullFT update effective rank 761–1,026; rank 128 captures only 43–51% of squared Frobenius norm; gap persists at 8B across three domains.** [arXiv]
- URL: https://arxiv.org/abs/2607.21612
- Occupies/negative: direct counterexample to "LoRA without regret" for agentic procedural SFT. Relevance: any CoTCodec experiment that needs Kimi-K2.6 to *internalize a multi-step protocol* via SFT on Tinker is at risk; RL objectives are the safer route. Confidence 0.85.

**F20. Hybrid-LoRA (arXiv 2605.18822, 2026-05-12): LoRA "often suffer[s] from a noticeable performance gap compared to full fine-tuning in post-training for complex reasoning" under RLVR; full-FT on a 10% module budget closes it.** [arXiv]
- URL: https://arxiv.org/abs/2605.18822
- Relevance: the fix (selective full-FT of sensitive modules) is exactly what Tinker cannot do. Confidence 0.8.

**F21. "Rethinking RL for LLM Reasoning: It's Sparse Policy Selection, Not Capability Learning" (arXiv 2605.06241, v2 2026-05-08): RL changes 1–3% of token positions at high-entropy points; promoted token always in base top-5; correction is low-dimensional; ReasonMaxxer (RL-free contrastive loss at entropy-gated positions) matches RL.** [arXiv]
- URL: https://arxiv.org/abs/2605.06241
- Relevance: mechanistic reason rank-1 RL works, and a warning that RL-on-Tinker mostly re-weights existing behaviors rather than creating new capability. Confidence 0.8.

**F22. "How Many Bits Can an Adapter Write?" (arXiv 2607.21351, 2026-07-23): adapters store "a couple of bits per trainable parameter"; MLP placement holds ~2× attention; adapters trained on verifiable rewards do not record verbatim secrets that SFT copies.** [arXiv]
- URL: https://arxiv.org/abs/2607.21351
- Relevance: quantitative capacity prior for choosing rank on Kimi-K2.6 (147M params/rank ≈ hundreds of Mbit per rank); supports MLP-heavy placement (which Tinker already uses). Confidence 0.8.

**F23. Geometry-Preserving Orthonormal Initialization for LoRA in RLVR (arXiv 2606.31813, accepted ICML 2026): PiSSA/MiLoRA can underperform standard LoRA and destabilize RLVR; orthonormal init minimizes the LoRA–FullFT gap.** [PR]
- URL: https://arxiv.org/abs/2606.31813
- Relevance: initialization is a live research axis for LoRA-RL, but Tinker exposes only `seed`, not the init scheme — untestable there. Confidence 0.85.

**F24. Rollout Routing Replay / R3 (arXiv 2510.11370, 2025-10): MoE RL is destabilized by train–inference router mismatch; replaying inference routing fixes collapse. Tinker has no routing replay (tinker-feedback #77, open since 2026-02-13, no maintainer reply).** [arXiv + GH issue]
- URLs: https://arxiv.org/abs/2510.11370 ; https://github.com/thinking-machines-lab/tinker-feedback/issues/77
- Relevance: RL on 1T MoEs via Tinker runs without the known stabilizer; the only observable is the expert-balance telemetry in F5 (Gap G5). Confidence 0.8.

**F25. MinT (arXiv 2605.13779, v2 2026-05-26, Mind Lab): managed LoRA RL infra "validated beyond 1T total parameters" incl. MLA/DSA; rank-1 adapters "under 1% of base-model size"; adapter-only handoff 18.3× faster step on 4B dense, 2.85× on 30B MoE; packed MoE LoRA tensors 8.5–8.7× faster loading; 10^6-scale adapter catalogs.** [arXiv]
- URL: https://arxiv.org/abs/2605.13779
- Occupies: the systems axis "many LoRA policies over one resident 1T base" — independent of TML, so the infra idea itself is not novel to Tinker. Confidence 0.8.

**F26. SDFT (arXiv 2601.19897, v2 2026-08-07) and the Tinker recipe's forced deviations: top-K KL instead of full-vocab, static teacher instead of EMA, because Tinker lacks full-vocabulary logits; SDPO ("Reinforcement Learning via Self-Distillation", arXiv 2601.20802, v2 2026-02-16: feedback-conditioned self-teacher distilled back into the policy, no external teacher or reward model) integrated in OpenClaw-RL (Tinker-supported, 5.6k stars).** [arXiv + 1P recipe + GH] 
- URLs: https://arxiv.org/abs/2601.19897 ; https://tinker-docs.thinkingmachines.ai/cookbook/recipes/sdft/ ; https://github.com/Gen-Verse/OpenClaw-RL ; https://arxiv.org/abs/2601.20802
- Occupies: on-policy self-distillation on Tinker. Relevance: shows concretely how the logprob-only API reshapes methods (approximation is the price of scale). Confidence 0.8.

### D. Competitors and the local-compute alternative

**F27. Fireworks: managed training is LoRA-only; Kimi K2.6 SFT/DPO LoRA with max training context 65,536; Kimi K3 (2.8T total / 104B active, 896 experts, KDA & Gated MLA, 1M context; HF created 2026-06-13) LoRA training since 2026-07-26 (~$65 for ~20 steps / 860K tokens; 8 concurrent jobs in preview); RFT via API mainly on older/smaller models (DeepSeek V3.1); full-parameter training on dedicated shapes for some models (Kimi K2.7 Code, DeepSeek V4-Flash-0731, GLM 5.2, Qwen3.5-27B).** [1P docs/blog via WebFetch summaries]
- URLs: https://docs.fireworks.ai/fine-tuning/models ; https://docs.fireworks.ai/fine-tuning/managed-finetuning-intro ; https://fireworks.ai/blog/K3-LoRA-Training ; https://huggingface.co/moonshotai/Kimi-K3
- Occupies: LoRA on a 2.8T model (K3) is Fireworks-only among the four; Tinker does not list K3.
- Relevance: if a CoTCodec cell needs >32K training context on Kimi-K2.6, Fireworks offers 64K at unknown price; but Fireworks exposes reward functions, not custom losses. Confidence 0.7 (summaries; rows should be re-verified before citation).

**F28. Together: LoRA max rank 16 for Kimi K2.6 / K2.7 Code / GLM 5.1 / 5.2 / DeepSeek V3.1 (64 for others); Kimi K2.6 SFT context 32,768, DPO 16,384; no full FT for those; SFT/DPO only, no RL.** [1P docs via WebFetch summary]
- URL: https://docs.together.ai/docs/fine-tuning-models
- Relevance: strictly less than Tinker for research (no custom loss, no RL, rank ≤16 on Kimi). Confidence 0.75.

**F29. Prime Intellect Hosted Training (Lab, GA 2026-05-07): LoRA-only, models ≤35B (largest: Qwen3.6-35B-A3B at $0.25 in / $0.75 out / $1.00 train per 1M; Nemotron-3.5-Lightning-30B $0.15/$0.45/$0.60); full fine-tuning in closed beta with default limits 64 GPUs/run and 10 queued runs; environments via `verifiers`; no Kimi/DeepSeek/GLM.** [1P docs]
- URLs: https://docs.primeintellect.ai/hosted-training/models-and-pricing.md ; https://docs.primeintellect.ai/hosted-training/full-finetuning.md ; https://www.primeintellect.ai/blog/lab-is-open
- Relevance: the only managed option with (gated) full FT, but no 1T models; its `verifiers` environments run on Tinker via the cookbook recipe (https://tinker-docs.thinkingmachines.ai/cookbook/recipes/verifiers-rl/). Confidence 0.9.

**F30. Modal is raw serverless compute (H100 $3.95/h, H200 $4.54/h, B200 $6.25/h, A100-80GB $2.50/h; 10–50 GPU concurrency by plan), no managed post-training API. Local 8×H100 cannot host Kimi-K2.6 for training: the HF repo is 595.2 GB INT4 pack-quantized (64 shards) versus 640 GB total HBM; the only public local-LoRA path converts to ~2 TB BF16 for KTransformers CPU-offload (xianhanglin/kimi-k2.6-int4-to-bf16, 2026-07-24, 0 stars). SkyRL (`skyrl-tx`, v0.3.0 2026-07-16) and `calpt/open-tinker` re-implement the Tinker API locally.** [1P pricing + HF API + GH]
- URLs: https://modal.com/pricing ; https://huggingface.co/api/models/moonshotai/Kimi-K2.6?blobs=true ; https://github.com/xianhanglin/kimi-k2.6-int4-to-bf16 ; https://github.com/NovaSky-AI/SkyRL ; https://github.com/calpt/open-tinker
- Relevance: for Kevin, "Tinker for the 1T cell, SkyRL-tx/open-tinker on fal-h100-01 for mechanism work with the same scripts" is the realistic two-tier design. Confidence 0.85.

---

## 2. Occupied-axes table

| Axis / mechanism | What is already taken | Primary sources |
|---|---|---|
| Managed LoRA post-training on 400B–1T MoEs | Tinker (Kimi-K2.6 1T, Inkling 975B, GLM-5.3 753B, DeepSeek-V3.1 671B, Nemotron Ultra 550B, Qwen3.5-397B); Fireworks (Kimi K3 2.8T LoRA); MinT infra paper validated >1T | F1, F27, F25 |
| "Low rank suffices for RL" and its limits | LoRA Without Regret (rank-1 RL = FullFT); Sparse Policy Selection (1–3% token positions); adapter bit-capacity; counter-results: Procedural Knowledge Is Not Low-Rank, Hybrid-LoRA | F12, F21, F22, F19, F20 |
| MoE LoRA factorization | Tinker's shared-outer scheme (shared hidden-dim factor, expert-specific other factor); MinT packed MoE LoRA tensors | F3, F25 |
| On-policy / self-distillation through top-K logprobs | TML on-policy distillation recipe; SDFT recipe (top-K, static teacher); SDPO; Bridgewater dynamic-teacher promotion; OpenClaw-RL OPD | F26, F16 |
| Agentic multi-turn RL harnesses on Tinker | harbor_rl (Terminal-Bench/SWE-Bench), verifiers/Environments Hub, Atropos, SkyRL, OpenClaw-RL, text-to-SQL (UIUC/Bridgewater) | F14, F15, F29, F30 |
| MoE-RL stabilization via routing replay | R3 (method exists) — but unavailable on Tinker (#77 open) | F24 |
| LoRA initialization geometry for RLVR | Orthonormal init (ICML 2026) vs PiSSA/MiLoRA — untestable on Tinker (seed only) | F23 |
| Local re-implementations of the Tinker API | SkyRL `skyrl-tx`, `calpt/open-tinker` | F30 |
| Cross-model adapter portability | PorTAL/Trans-LoRA/Cross-LoRA (prior sweep: deprioritized); Tinker cannot import adapters at all | F8, prior sweep |

---

## 3. Possible vs impossible: architecture-adjacent experiments through LoRA-only access to Kimi-K2.6

**Possible on Tinker (Kimi-K2.6, 32K or 128K):**
1. Any training objective that is a differentiable function of *selected-token* log-probs: RL surrogates (importance sampling, PPO, CISPO, DRO, custom), DPO/Bradley–Terry, renormalized candidate-set CE, top-K soft distillation (K chosen by user), KL-as-reward. (F4)
2. Multi-turn, tool-using, sandboxed RL with custom environments, group-relative advantages, multi-agent self-play, bounded off-policy staleness (`max_steps_off_policy`). (F14, cookbook `rl/`)
3. Coarse module-group ablations (`train_mlp` / `train_attn` / `train_unembed`), rank sweeps (ranks 1–128 observed in first-party use), seeded init, LR/batch schedules. (F2, F13)
4. Using Kimi-K2.6 as a 1T *teacher* (sampling client with `topk_prompt_logprobs`) for a small student with the same tokenizer, or Kimi→Kimi self-distillation. (F4, F26)
5. Observational MoE routing-health telemetry during LoRA training (expert idle/oversubscription fractions). (F5)
6. Exporting adapters (r·146.7M params) for offline weight-space analysis on the H100 node without the base model: per-expert vs shared-factor norms, ΔW spectra across tasks/languages. (F3, F9)
7. 128K-context training/sampling at ~3× the 32K price; prompt-cache discounts for shared prefixes. (F1)

**Impossible on Tinker (must use local open weights, e.g. Qwen3.5-4B/9B, GPT-OSS-20B, Kimi-Linear-48B-A3B on fal-h100-01):**
1. Anything that reads or shapes internal representations: probes, steering vectors, activation patching, representation losses, TTS-style causal steering, continuous latent reasoning (Coconut), learned soft prompts. (F5, F7)
2. Full-vocabulary logits: exact KL/entropy objectives, logit-lens diagnostics. (F4)
3. Architecture changes of any kind: new sequence operators/attention variants, SSM hybrids, byte patching (direction 18), adaptive depth, router/gate modification, expert freezing/dropping/pruning, added heads (value/classification), tokenizer or embedding changes. (F2, F5, tinker-feedback #18)
4. Full fine-tuning, selective full-FT of sensitive modules (Hybrid-LoRA), per-layer/per-module LoRA, LoRA structure variants (DoRA, PiSSA/MiLoRA/orthonormal init, rank patterns, alpha), custom optimizers or update rules, gradient inspection/surgery. (F2, F6, F20, F23)
5. Importing externally generated adapters (PorTAL-style hypernetwork outputs) or continuing from non-Tinker checkpoints. (F8)
6. Router-aware RL (routing replay), expert-level interventions, or measuring anything about routing beyond the balance metrics. (F24, F5)
7. Deterministic/replayable step timing or bit-exact reproducibility guarantees (multi-tenant clock cycles; open issues #127 optimizer-state resume and #143 inconsistent weight states). (F10, F11)
8. Kimi-K2.6 at its native 256K context (Tinker caps at 128K); Kimi K3 at all (Fireworks only). (F1, F27)

**Cost sanity check [derived from F1 prices]:** the harbor default (4 rollouts × 8 groups × 8,192 max tokens ≈ 262K sampled tokens/step) costs ≈ $1.44 sample + ≈ $1.27 train per step plus prompt prefill at 32K prices — order $3/step, ≈ $300 per 100 steps; the 128K tier is 2.3–3.2× per token. The repo's $6 Qwen→Kimi smoke contract (`experiments/tinker/capsule-policy-kimi.yaml`) is consistent with these rates.

**Repo-facing corrections (kill-shots, not brainstorms):**
- `memory.json` pins `tinker==0.23.3`; PyPI is at 0.27.0 (2026-09-01) and the server rejects unsupported SDK versions with HTTP 400 (#120). Add an SDK-version doctor before any paid run. (F11)
- Direction 17's "Tinker/Kimi scale-up" and the capsule contract assume `context_tokens: 32768`; the harbor recipe shows 60.6% of SWE-Bench episodes overflow at 32K with 8K generation budgets. Budget the 128K tier or cap episode length explicitly. (F14)
- Any plan to compare LoRA against full fine-tuning at 1T cannot be executed on any managed provider surveyed (Prime Intellect's closed-beta full-FT stops at ≤35B models). (F29)

---

## 4. Open gaps (searched, not found; see coverage limits)

**G1. Effect of Tinker's shared-outer MoE LoRA scheme on expert specialization/routing at 1T.**
- Why open: the scheme is documented only in a cookbook docstring; no measurement exists of how a shared hidden-dim factor plus expert-specific factors changes routing entropy, expert utilization, or per-expert delta norms on Kimi-K2.6 (or any 1T MoE).
- Evidence: GitHub code search `"shared-outer"` in the cookbook → only the docstring; arXiv HTML search "LoRA mixture of experts adapter shared across experts" → 0 bytes/429 (blocked); WebSearch on MoE-LoRA router literature → budget exhausted; tinker-feedback search "router"/"Kimi" → only #77.
- Kevin advantage: Tinker access to Kimi-K2.6 plus the free expert-balance metrics (F5) and adapter export (F9) make a rank-{1,4,32} × {train_mlp on/off} sweep with per-expert ΔW analysis feasible for hundreds of dollars; 8×H100 handles the offline adapter analysis. No direct prior art found through 2026-09-01 under the coverage below.

**G2. Rank sensitivity above 4 on 1T-class models under a fixed protocol.**
- Why open: TML's own sweep stops at rank 4 for every ≥235B model (F13) while its recipes default to rank 32 (F14, F15); nobody reports rank {8,32,128} curves on Kimi-K2.6.
- Evidence: `sft_sweep.md`, `hyperparams.md`, harbor README, text-to-SQL post all read; HF adapter filter `base_model:adapter:moonshotai/Kimi-K2.6` → 9 adapters (r=8 observed), no rank studies.
- Kevin advantage: Tinker + the harness's seeded, receipt-hashed runs can reproduce TML's tulu3 protocol at higher ranks; the result is publishable as infrastructure knowledge whether positive or negative.

**G3. Verifiable-reward translation/multilingual RL on a 1T model via Tinker.**
- Why open: the cookbook has a language-ID prompt-distillation tutorial (13 codes) and a chat-SFT sweep, but no translation-quality RL recipe; the only multilingual Tinker repo found is a Romanian SFT on Llama-3.1-8B (dandinu/romanian-llm-tinker, 2026-02).
- Evidence: sitemap recipe list (17 recipes) read; `gh search repos tinker thinking-machines` (15 results); bookmark searches "Kimi", "GRPO", "RLVR" → no translation RL.
- Kevin advantage: General Translation's parallel data supplies reference-based and round-trip rewards; 8×H100 hosts local reward/QE models; Tinker supplies the Kimi-K2.6 policy at ~$3/step. This is a use of Tinker, not an architecture claim — keep it as evidence-generation for direction 18, not as the novelty.

**G4. A two-tier protocol that keeps one Tinker-API training script while swapping the *backend* between hosted Kimi-K2.6 and a local open-Tinker server with full access (optimizer, hidden states, full-FT).**
- Why open: SkyRL `skyrl-tx` and `open-tinker` implement the API locally (F30), but no public project reports running the same experiment on both tiers to separate "mechanism" (needs internals) from "does it hold at 1T" (needs Tinker).
- Evidence: `gh search code tinker --repo NovaSky-AI/SkyRL` (backend exists, AMD/CI scripts); `gh search repos tinker GRPO` (10 repos, all hosted-only); no arXiv hits (API blocked).
- Kevin advantage: Docker/Slurm harness + 8×H100 can run skyrl-tx for ≤35B models with digest-pinned images; the identical script then targets Tinker for the 1T cell, giving the "portable across models" flavour Kevin wants without a new primitive claim.

**G5. Routing stability of LoRA-RL on a 1T MoE without routing replay.**
- Why open: R3 shows router mismatch collapses MoE RL (F24); Tinker lacks replay (#77) and reports no data; the balance metrics (F5) have never been published for a Kimi-K2.6 RL run.
- Evidence: tinker-feedback issues #77/#141/#96 read; cookbook code search "router" → no training-side router code; arXiv search blocked after one query.
- Kevin advantage: the metrics come back free with every `forward_backward`; logging them across a seeded Kimi-K2.6 RL run is a near-zero-cost negative/positive result that his receipt-hashed harness can seal.

---

## 5. Exact queries run (successful distinct search queries = 51; attempted ≈ 72)

**WebSearch (11 executed; 5 blocked by the session budget cap of 200):**
1. `Tinker Thinking Machines "Kimi-K2.6" LoRA fine-tuning 2026`
2. `tinker-docs.thinkingmachines.ai forward_backward_custom custom loss logits limitation`
3. `Tinker API checkpoint export download LoRA weights expiry retention limitations`
4. `Thinking Machines blog 2026 Tinker new models Kimi K2.6 GLM-5.3 Qwen3.8 announcement`
5. `"Tinker" Thinking Machines case study paper arXiv 2026 "trained with Tinker" OR "using Tinker" LoRA RL results`
6. `Prime Intellect managed RL fine-tuning API 2026 prime-rl hosted LoRA pricing Kimi`
7. `Fireworks AI reinforcement fine-tuning RFT supported models LoRA rank limits 2026 DeepSeek Kimi`
8. `Together AI fine-tuning API 2026 LoRA rank limit supported models DeepSeek-V3 Kimi K2 full fine-tuning pricing`
9. `Modal fine-tuning managed post-training service LoRA RL 2026 "Modal" GPU serverless fine-tune Kimi K2 pricing`
10. `"LoRA Without Regret" replication OR reproduction OR "does not hold" OR failure 2026 arXiv LoRA reinforcement learning rank capacity`
11. `Tinker Thinking Machines rate limits outage "known issues" OR "limitations" max context length training tokens per request 2026`
- Blocked (budget): Prime Intellect docs pricing; thinkymachines Kimi-K2.6 announcement date; SkyRL Tinker backend; MoE LoRA router literature; SDPO/Trajectory case study.

**arXiv API (export.arxiv.org, 7 queries, all returned empty bodies — blocked/unavailable from this network):** `all:"Tinker" AND all:"Thinking Machines"`; `abs:"Tinker" AND (abs:LoRA OR abs:"post-training" OR abs:"reinforcement learning")`; `all:LoRA AND all:"reinforcement learning" AND all:"mixture of experts"`; `all:Tinker`; `all:LoRA AND all:MoE AND all:reinforcement`; `ti:LoRA` (sanity, empty); UA-retry sanity (empty).

**arXiv HTML search (1 successful, 6 blocked):** `LoRA reinforcement learning rank full fine-tuning` (15 results, 2024–2026); blocked: `LoRA mixture-of-experts router expert-specific adapter`, `Tinker Thinking Machines fine-tuning API`, `Self-Distillation Enables Continual Learning`, `SDPO self-distillation policy optimization`, `on-policy distillation LoRA 1T MoE trillion parameter fine-tuning`, `"Tinker" "Thinking Machines"` (429).

**arXiv abstract pages fetched directly (10):** 2605.13779, 2607.21612, 2605.18822, 2604.21905, 2605.06241, 2607.21351, 2606.31813, 2601.19897, 2510.11370, 2601.20802.

**Semantic Scholar (3 attempts, all HTTP 429):** `LoRA reinforcement learning capacity rank full fine-tuning equivalence`; `LoRA reinforcement learning matches full fine-tuning low rank`; `LoRA policy gradient rank one matches full fine-tuning`.

**GitHub (18 searches + ~30 API reads):** repos: `tinker thinking-machines`, `tinker GRPO`, `"Kimi-K2" fine-tuning`, `"Kimi-K2" LoRA`; code: `moonshotai/Kimi-K2.6` (global), `Kimi-K2.6` (cookbook), `router` (cookbook), `shared-outer` (cookbook), `"full fine-tuning"` (cookbook), `tinker` (NovaSky-AI/SkyRL), `off_policy` (cookbook), `Kimi-K2` (unslothai/unsloth); issues: `rank`, `Kimi`, `logits` (tinker-feedback), `Kimi-K2.6` (cookbook); API reads of tinker SDK types (lora_config, loss_fn_type, forward_backward_output, model_input_chunk, dmel_chunk, image_chunk, datum, sampling_params, create_model_request, load_weights_request, copy_weights_request, save_weights_request, get_server_capabilities_response), cookbook files (README, model_info, hyperparam_utils, weights/README, harbor_rl README+train.py, hyperparams.md, sft_sweep.md, distillation README, eval/_types.py), tinker-feedback issues #77 #103 #104 #127 #141 #143 and cookbook #889, tinker-atropos, OpenClaw-RL, autoresearch-rl, kimi-k2.6-int4-to-bf16, idanshen/Self-Distillation.

**Hugging Face API (8):** `search=Kimi-K2.6`; `models/moonshotai/Kimi-K2.6` (+config, README, blobs); `models/thinkingmachines/Inkling` (+README); `models/thinkingmachines/Inkling-Small`; `models/zai-org/GLM-5.3` (+README, config); `filter=base_model:adapter:moonshotai/Kimi-K2.6`; `search=tinker`; `search=Kimi-K3&author=moonshotai` (+README); `barbonara/corin-kimi-k26-pro-sft` adapter_config/README/blobs.

**Kevin's X bookmarks (`ft search`, 13 valid):** `Tinker`, `thinkymachines`, `tinkerapi`, `LoRA`, `Inkling`, `Kimi`, `GRPO`, `RLVR`, `Schulman`, `Fireworks`, `PrimeIntellect`, `Together`, `Unsloth` (rejected by the tool: `"Kimi K2.6"`, `on-policy distillation`, `fine-tuning API`, `post-training`). Hits: Inkling launch/playground (@frank_ 2026-07-16), PorTAL (@RampLabs 2026-07-01/27), Kimi K3 "open weights coming soon" + FlashKDA/MoonEP/AgentENV (@Kimi_Moonshot 2026-07-27), ml-intern (@akseljoonas 2026-04-21). No bookmark mentions Tinker RL results, Fireworks, or Prime Intellect.

**Primary pages fetched (curl / WebFetch):** Tinker docs sitemap (154 non-API pages fetched; read: models, lora-primer, under-the-hood, changelog, model-deprecations, losses/{custom,cross-entropy}, api-reference/{trainingclient, serviceclient, samplingclient, restclient, types/*}, tutorials/{weights, export-hf, lora-adapter, sequence-extension, rl-hyperparams, prompt-distillation, multi-agent}, cookbook/{rl, recipes/*, inkling}, compatible-apis/anthropic, support, session-metrics, data-model); thinkingmachines.ai/{tinker, blog, blog/lora, blog/a-safe-path-to-open-weights, news, news/tinker-general-availability, news/putting-task-expertise-into-rl, news/introducing-inkling, news/learning-to-replicate-expert-judgment-in-financial-tasks}; docs.together.ai/docs/fine-tuning-models; docs.fireworks.ai/fine-tuning/{models, managed-finetuning-intro}; fireworks.ai/blog/K3-LoRA-Training; primeintellect.ai/blog/lab-is-open; docs.primeintellect.ai/{llms.txt, hosted-training/getting-started, models-and-pricing.md, full-finetuning.md}; modal.com/pricing; github.com/NovaSky-AI/SkyRL; PyPI JSON for tinker and tinker-cookbook.

---

## 6. Coverage limits (honest)

- **WebSearch budget:** the session-wide cap (200 calls) was hit after this cell's 11th query; five planned searches (Prime Intellect pricing via search, the Kimi-K2.6-on-Tinker announcement date, SkyRL–Tinker, MoE-LoRA/router literature, SDPO/Trajectory) were replaced by direct fetches or left open.
- **arXiv:** the API returned empty bodies for every query (with and without a User-Agent); the HTML search worked once then returned 429/empty. Only ten abstract pages were fetched directly. The MoE-LoRA-routing literature and any 2026 papers that mention Tinker in their abstracts are therefore **under-covered**; G1 and G5 should be re-checked when arXiv access returns.
- **Semantic Scholar:** three 429s, no API key — no citation counts or venue confirmation beyond what the arXiv pages state (only 2606.31813 self-reports ICML 2026 acceptance).
- **Jina reader:** blocked (anonymous ban on this network); replaced by curl + an mkdocs article extractor and WebFetch.
- **Competitor tables (Together, Fireworks):** read through WebFetch summaries of the docs pages, not raw HTML; individual rows (e.g., "Kimi K2.6 max rank 16", "K2.6 max training context 65,536") should be re-verified from the live pages before appearing in a paper.
- **No Tinker API key:** rate limits, `max_batch_size`, any undocumented rank cap, and actual step latency could not be probed live; `GetServerCapabilitiesResponse` fields (model_name, max_context_length, trainable, sampleable) come from SDK source only.
- **Not opened:** the HF TRL and michaelbzhu reproductions of LoRA Without Regret; individual case-study pages behind the Tinker homepage (Glean, Chroma, Trajectory, Axiom); the SkyRL tinker docs page; Inkling's full benchmark tables; the Together/Fireworks pricing pages.
- **Dating:** Tinker docs pages are undated except the changelog; all docs facts are "as fetched 2026-09-01". Kimi-K2.6's public release date is taken from the HF `createdAt` (2026-04-14), not from a Moonshot announcement.
- **Bookmarks:** `ft search` rejects hyphenated multi-word queries, so several natural phrasings could not be searched.
