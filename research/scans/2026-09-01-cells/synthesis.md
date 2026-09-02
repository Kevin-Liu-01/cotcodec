# CoTCodec frontier sweep — synthesis (2026-09-01)

Owner: synthesis cell. Inputs: `context.md` and 17 cell notes in `scratchpad/sweep/` (seq-operators, ttt-fastweights, learned-update-rules, adapter-portability, latent-reasoning, tokenizer-free-multilingual, diffusion-nonar, benchmarks-eval, harness-ecosystem, tinker-rl, local-model-ecosystem, infra-slurm, bookmarks, killshot-current, arxiv-triage-arch, arxiv-triage-adapt-reason-diff, arxiv-triage-agents-eval-ml; `srttt_v2.md` is an empty Jina 401 stub). Prior sweep cutoff: 2026-08-10. Everything dated after that is marked **[post-cutoff]**.

Honesty rules applied throughout: "first-party" = lab/author claim not independently replicated; "peer-reviewed" only where a venue is stated on the primary page; gaps are stated as "no direct prior art found through 2026-09-01 under the coverage in §6", never as novelty claims. Cells were merged by **mechanism**, not wording: two cells naming the same move under different labels are one axis below.

---

## 0. Executive verdict (ten lines)

1. Generic sequence-operator design is closed to Kevin: 3:1 linear/global hybrids, learned sparse indexers, delta-rule gate geometry, depth-axis residuals, MTP heads, learned sinks and per-token operator routing are each held by two or more production labs plus a dense 2026 preprint stream (§1 A–H). The prior program's Rejected table stands and its ranked item "Budgeted Mixture of Sequence Operators" is now occupied on the layer, token, head, block and serving axes.
2. The one region every cell independently found empty is **language/script as a controlled variable inside architecture**: recurrent-state recall and hybrid-ratio behaviour with content held fixed across translations; learned indexer selection across translations; parallel-data-supervised byte boundaries; translation-equivariant abstract reasoning codes and cross-language monitor transfer; cross-lingual fast-weight readout; cross-lingual harness effects. This is where General Translation's parallel data is the defining input rather than an aid.
3. Portability (PorTAL's move) is occupied among softmax transformers, including MoE, local/global attention, multimodal wrappers and different tokenizers, and the "frozen object + thin target-side reader" variant is now doubly occupied for memory (Engram reader transfer) and KV state. What no source ports is a task adapter onto a **different operator family** (KDA/GDN/Mamba hybrid, masked-diffusion LM, byte-level model), a **label-free** base alignment, or an **update rule**.
4. Direction 16 is NARROWED to update-rule portability; Direction 17 is NARROWED to prospective randomized identification (post-hoc deletion credit is taken by Hindsight Memory-PRM); Direction 18 is STILL_OPEN but now needs five extra control arms; Coded Delta Memory survives only as a negative-result cell; Bidirectional Plan Repair has a novelty-level collision (CID) and needs four new deltas.
5. Test-time training moved to drop-in fast weights on released checkpoints and chunk-parallel exactness; exact recall beyond the attention window remains contested (TTT-E2E 0.06 pass-key at 128K; SR-TTT v2 retraction 0% exact match in 2,250 trials) and no causality-verified independent replication of any 2026 beyond-window claim exists.
6. Diffusion LMs: every equal-wall-time win is first-party and batch-1; the only independent measurement (Artificial Analysis, Mercury 2: 684 tok/s, 4.01 s TTFT) sits well below the 1,000+ first-party claim; 76% of batch-1 wall-clock is CPU dispatch on current stacks.
7. The believability bar for a 0.1–1B architecture claim in 2026 is explicit: ≥256 tuned configurations per scale at the smallest rungs, ≥3 sizes spanning ≥10× compute, token budgets to ~1000N, ≥3–5 seeds with paired clustered SEs, length-dependent curves, generation-based evaluation, early context-extension probes, SWA+sinks and tail-replay controls, and a two-forward-pass causality audit.
8. Compute reality: Kimi K3 (1.56 TB MXFP4) and Kimi-K2.6 (595 GB INT4) are not local objects; Tinker exposes LoRA-only, logprob-only custom losses, AdamW-only, no adapter import, 32K/128K context on Kimi-K2.6. Architecture work runs locally on Qwen3.5 0.8B–9B bases, Gemma-4 E2B/E4B/12B, Nemotron-3.5-Lightning-Base, Olmo-Hybrid-7B, Falcon-H1, Kimi-Linear-48B-A3B (custom code), and from-scratch 0.1–1.5B hybrids with fla ≥0.5.2 kernels.
9. Infrastructure blocker: Slurm 21.08.5 cannot enforce cgroup v2 device isolation; the publication lane needs Slurm 25.11.7 + Pyxis 0.24.0 + Enroot 4.2.1 built from source, and `memory.json` pins a Tinker SDK (0.23.3) the server may already reject (PyPI 0.27.0; HTTP 400 on unsupported versions).
10. Retractions/negatives found this window: Impossibility Triangle (2605.05066) withdrawn 2026-08-06; Mamba-2 state-sink paper self-corrected v2 (2606.00930); pre-registered negative on nested byte vocabularies (2608.28151); SWA-with-sinks beats post-trained linear attention (2608.28444); harness evolution does not beat matched-budget parallel sampling (2607.12227 v2); reward-SNR floor for learned acquisition routing (2608.10441); nano-K3 toy reports SiTU-GLU/LatentMoE hurt at nano scale (1-star, unverified).

---

## 1. Occupied map — design axes merged by mechanism

Columns: what is taken (representative primary URLs, dates), and the precise remaining gap per axis. "Closed" means no delta is visible for Kevin's assets.

| # | Axis (mechanism) | What is taken | Representative primary URLs | Remaining gap |
|---|---|---|---|---|
| A | Fixed-ratio linear/global hybrid layouts | 1-in-4 global layers in Kimi K3 (69 KDA + 24 gated MLA, 2.8T), Qwen3.5/3.8 (GDN, interval 4 from 0.8B to 2.4T), GLM-5.3-Flash (34 KDA + 11 DSA), Solar Open 2 (3:1 NoPE); Nemotron 3.5 (23 Mamba-2 / 6 attention / 23 MoE); MiMo-V2-Flash SWA 5:1; 72-model ratio sweep; Meta FLOP-matched 1:1–1:12 study; convergence result: operator choice sets speed of emergence, not the asymptote | https://arxiv.org/abs/2607.24653 · https://arxiv.org/abs/2608.30320 · https://huggingface.co/zai-org/GLM-5.3-Flash · https://arxiv.org/abs/2607.20062 · https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16 · https://arxiv.org/abs/2507.06457 · https://arxiv.org/abs/2510.04800 · https://arxiv.org/abs/2606.15378 · https://arxiv.org/abs/2604.03444 | Ratio is settled; what no source measures is which capabilities the fixed-size recurrent state and the 1-in-4 placement trade across scripts/languages with content held fixed. No sub-10B open KDA base exists (only 48B-A3B custom-code). |
| B | Sparse/compressed global attention with a learned indexer | DSA (GLM-5.x, DeepSeek-V3.2), QSA micro-block + compressed indexer (Qwen3.8-Flash-Next), CSA/HCA compression + top-k (DeepSeek-V4), LongCat LSA cross-layer indexing, GLM-5.2/5.3 IndexShare/IndexCache, MiniMax MSA, A.X K2 Sparse Gated Attention with indexer warmup, MiniCPM-SALA, HySparse; fla 2×2 design note (granularity × scoring proxy) | https://arxiv.org/abs/2608.30320 · https://arxiv.org/abs/2606.19348 · https://arxiv.org/abs/2608.01662 · https://arxiv.org/abs/2603.12201 · https://arxiv.org/abs/2606.13392 · https://arxiv.org/abs/2608.30181 · https://github.com/fla-org/flash-linear-attention/blob/main/fla/ops/dsa/README.md | Cross-lingual behaviour of learned indexers (do selected blocks correspond across translations; can parallel data supervise a language-invariant indexer) — no source. Indexer internals are not reachable through Tinker; local ≤1B only. |
| C | Delta-rule state-update geometry (erase/write/read/decay/step-size/preconditioning) | KDA lower-bounded decay + full-rank gate; GDN-2 channel-wise erase/write; FG²-GDN; EDA; QED query-derived erase [post-cutoff]; Q-Delta; CCQ; Kaczmarz step; OSDN online preconditioning; Preconditioned DeltaNet; Gated KalmaNet; Bayesian Layer covariance; SDM sparse addressing; KATA feature maps; Fourier/complex decay (theory only); negative-eigenvalue rule (Solar Open 2); SANE extreme-context stabilisation [post-cutoff]; MARCH content-routed anchors [post-cutoff]; 350M third-party bake-off (KDA+Muon lowest loss) | https://arxiv.org/abs/2605.22791 · https://arxiv.org/abs/2608.13668 · https://arxiv.org/abs/2606.26560 · https://arxiv.org/abs/2604.19021 · https://arxiv.org/abs/2606.08804 · https://arxiv.org/abs/2605.13473 · https://arxiv.org/abs/2604.21100 · https://arxiv.org/abs/2605.31163 · https://arxiv.org/abs/2607.07386 · https://arxiv.org/abs/2607.17419 · https://arxiv.org/abs/2607.11897 · https://arxiv.org/abs/2608.22354 · https://arxiv.org/abs/2608.12435 · https://arxiv.org/abs/2607.07953 | Closed for "one more gate". Coding-theoretic state protection with an explicit syndrome is unclaimed (searched by two cells) but SANE's norm-anomaly statistic, QED's query-side interference measure and the Bayesian layer are free baselines it must beat; expected value low. LM-scale test of complex/rotational decay with fused kernels is unclaimed. |
| D | Depth-axis / residual-stream operators | AttnRes + Block AttnRes (Kimi; 1.25× compute-equivalent, in K3), Role-Decoupled AttnRes, Hyper-Connections/mHC/xHC (DeepSeek-V4, GLM-5.3-Flash, Motif 3), Qwen Gated Residual (4 branches; Full AttnRes = GR at 25B-A3B), Deep Delta Learning, stream-collapse diagnosis | https://arxiv.org/abs/2603.15031 · https://arxiv.org/abs/2608.01075 · https://arxiv.org/abs/2512.24880 · https://arxiv.org/abs/2608.30320 · https://arxiv.org/abs/2608.09119 · https://arxiv.org/abs/2601.00417 · https://arxiv.org/abs/2606.03483 | Only first-party single-run head-to-heads exist (Qwen Tables 5/6; AttnRes Table 2 vs "mHC-lite"). An independent iso-compute, multi-seed comparison at 0.1–1B is absent; depth-attention weights have never been used as a probe (e.g., do translation pairs route through the same depths). |
| E | Learned or dynamic operator placement/routing under a budget | Layer: FlashMorph, KL-guided selection; token: NAtS-L, LoGo [post-cutoff], Switch Attention (EMNLP 2026); head: HydraHead; block: Mixture of Layers; serving: Super Apriel supernet; prefill patterns: RouteSparse with error certificate [post-cutoff]; identification limit: routers need pairwise comparison, segment-level routing reaches 15–29% of token-level; negatives: SWA+sinks beats post-trained linear attention; BRANCH dominates operator choice in agentic reasoning; a matched-interface GRU ties homeostatic governors | https://arxiv.org/abs/2606.30562 · https://arxiv.org/abs/2602.03681 · https://arxiv.org/abs/2608.29539 · https://arxiv.org/abs/2603.26380 · https://arxiv.org/abs/2606.20097 · https://arxiv.org/abs/2605.09516 · https://arxiv.org/abs/2604.19877 · https://arxiv.org/abs/2608.29058 · https://arxiv.org/abs/2603.20997 · https://arxiv.org/abs/2608.28444 · https://arxiv.org/abs/2608.23956 · https://arxiv.org/abs/2608.24319 | Only "value the full stateful continuation under measured latency/HBM" is untaken; two structural results (pairwise-compute requirement; convergence) cap the expected gain. MixerLoop's marginal ITR is a candidate value signal. High collision, feasibility-constrained. |
| F | Positional encoding in hybrids | NoPE global layers (Kimi Linear, K3, Solar Open 2: direct 1M extrapolation claimed); RoPE kept by Qwen3.8-Next after NoPE showed endless generation post-training; partial RoPE 0.25 (Qwen3.5) / 64 dims (DeepSeek-V4); HyPE; PaTH incoherence theory; Möbius RoPE; RFS; Randomized YaRN; ZetaGPT SSM-before-attention as implicit position [post-cutoff]; Cracks in the Foundation (COLM 2026): minor choices compound to −47% long-context | https://arxiv.org/abs/2607.24653 · https://arxiv.org/abs/2608.30320 · https://arxiv.org/abs/2606.24975 · https://arxiv.org/abs/2607.21405 · https://arxiv.org/abs/2601.22156 · https://arxiv.org/abs/2608.09432 · https://arxiv.org/abs/2608.10296 | The three primary sources disagree on NoPE in hybrids and no study isolates what post-training breaks (KDA channel-wise vs GDN scalar decay as positional signal; termination). Mechanistic small-scale study absent. |
| G | Attention sinks and massive activations | Learned per-head sink logits (DeepSeek-V4, Hybrid Gated Attention), gated attention (Qwen), nop-vs-broadcast unification, P0-sink circuit, outlier rescaling view, BOS absolute-position leakage, massive activations in hybrids 1.2B–397B with released 340M/1.3B GDN hybrids [post-cutoff] | https://arxiv.org/abs/2606.19348 · https://arxiv.org/abs/2608.11805 · https://arxiv.org/abs/2606.08105 · https://arxiv.org/abs/2603.06591 · https://arxiv.org/abs/2601.22966 · https://arxiv.org/abs/2606.06160 · https://arxiv.org/abs/2608.12149 | Closed as a phenomenology axis. |
| H | Multi-token prediction heads | One MTP layer standard (K3 → EAGLE-3 draft, Qwen3.5/3.8 with QSA index reuse, DeepSeek-V4, GLM-5.3, Nemotron 3.5 dedicated CPT stage, Motif 3, MiMo-V2-Flash, Inkling 8 layers); AdaMTP, LoopMTP, HiLP, MTP-D; Windowed-MTP and TreeWY caveats for hybrids | https://arxiv.org/abs/2607.24653 · https://arxiv.org/abs/2608.30320 · https://arxiv.org/abs/2608.00434 · https://arxiv.org/abs/2608.03624 · https://arxiv.org/abs/2603.23911 · https://arxiv.org/abs/2607.21535 · https://arxiv.org/abs/2608.20961 | No controlled MTP-on/off ablation on ≤1B linear/hybrid backbones; how a draft should read recurrent state at long context is open. |
| I | Transformer→hybrid conversion and distillation | HALO/HypeNet, Taylor-Calibrate, Priming (<0.5% tokens, GKA-32B), FlashMorph, Attention-to-Mamba, HyLo upcycling, GenDistill, xLSTM distillation, DiD interface distillation (vision); negatives: Stuck-on-A (0.6B KDA conversion, C-Eval 28.8 vs 50.6 at +0.128 nats KL), When Perplexity Lies (−20.8 pp generating), SWA beats linear retrofits | https://arxiv.org/abs/2601.22156 · https://arxiv.org/abs/2606.16429 · https://arxiv.org/abs/2605.08301 · https://arxiv.org/abs/2604.14191 · https://arxiv.org/abs/2604.24715 · https://arxiv.org/abs/2608.22368 · https://arxiv.org/abs/2608.02689 · https://arxiv.org/abs/2603.26556 · https://arxiv.org/abs/2608.28444 | Recipes exist; the live requirement is generation-based, permutation-controlled evaluation. No conversion paper asks whether the base's fine-tunes or adapters survive (see N). |
| J | Hybrid serving state algebra (compression, replay, branching, quantization, RL trees) | DASC retention-horizon compression (2.63×), Tail-Replay suffix reconstruction (92.8–99.9% quality at 5–10% budget), DeltaLog bounded update logs, TreeWY branch-structured WY, DAMP mixed-precision states (INT4 collapses reasoning), HARTS tree-RL, HYPIC, SANE; component-aware self-speculation negative for sequential hybrids (α=0.038) | https://arxiv.org/abs/2608.30386 · https://arxiv.org/abs/2608.30310 · https://arxiv.org/abs/2608.15533 · https://arxiv.org/abs/2608.20961 · https://arxiv.org/abs/2608.27513 · https://arxiv.org/abs/2608.28158 · https://arxiv.org/abs/2607.01299 · https://arxiv.org/abs/2605.01106 | Diag B (rank-adaptive edit summaries) is largely occupied at the serving layer; only non-suffix edits on long-retention units with rank analysis remain. Channel-level retention/precision heterogeneity is a free measurement substrate. |
| K | Test-time-training layers and fast-weight memory | Chunk-parallel design space (E²-TTT exact chunk-end states [post-cutoff], Modular TTT DAG ablations, LaCT, MesaNet CG solve, Falcon NLMS rules [post-cutoff], TTT-KVB ≡ linear attention); drop-in fast weights on released checkpoints (In-Place TTT ICLR 2026 Oral, TTT-NTP EMNLP 2026 Findings, TTCD, MoNe [post-cutoff], FAAST, Locas, targeted context updates); Google neural memory (Titans, MIRAS, Atlas, Trellis, HOPE; no code); sparse-slot memory (FwPKM); stability by regularizers (Muon+norm, EWC anchors, clipping); write selection (S-TTT, EASE, SCoL, REFINE); serving isolation (RW-TTT); security (LoRA-TTT jailbreaks) | https://arxiv.org/abs/2608.21308 · https://arxiv.org/abs/2608.07110 · https://arxiv.org/abs/2505.23884 · https://arxiv.org/abs/2506.05233 · https://arxiv.org/abs/2608.27763 · https://arxiv.org/abs/2602.21204 · https://arxiv.org/abs/2604.06169 · https://arxiv.org/abs/2606.21803 · https://arxiv.org/abs/2608.01672 · https://arxiv.org/abs/2608.17616 · https://arxiv.org/abs/2605.04651 · https://arxiv.org/abs/2602.05085 · https://arxiv.org/abs/2501.00663 · https://arxiv.org/abs/2504.13173 · https://arxiv.org/abs/2505.23735 · https://arxiv.org/abs/2512.24695 · https://arxiv.org/abs/2601.00671 · https://arxiv.org/abs/2605.28053 · https://arxiv.org/abs/2605.22984 | Exact recall beyond the window is contested (TTT-E2E pass-key 0.06 at 128K; issue #8 unanswered; SR-TTT v2 retraction); no causality-verified independent replication of E²-TTT/FwPKM/MoNe; no stability theory for nonlinear fast weights (momentwo covers linear Titans only); no reset/rollback/deletion attestation; no poisoning study of fast-weight layers; no cross-lingual write/readout. |
| L | Learned optimizers and update-rule portability | Celo2 (ICLR 2026; 4.5 GPU-h meta-training, to 1.3B), ELO (<7 H100-h, beats AdamW on GPT-2/ViT/ResNet), μLO (horizon divergence), PyLO (MLSys 2026); toy architecture-agnostic rules (MetaNCA, UNF, UHN); self-modifying sequence models (Nested Learning/HOPE, FedNL, SRWM, ACL); model-directed recipes (SEAL, self-edit search, CaMeLS, "Can GD simulate prompting"); optimizer–model entanglement (Optimizer-Model Consistency, spectral scaling laws, Survey of Optimizers [post-cutoff]); DeltaMomentum [post-cutoff]; per-architecture ICL-as-optimization theory (transformer GD vs Mamba online GD vs SSM Bayes filter) | https://arxiv.org/abs/2602.19142 · https://arxiv.org/abs/2607.06772 · https://arxiv.org/abs/2406.00153 · https://arxiv.org/abs/2506.10315 · https://arxiv.org/abs/2607.07743 · https://arxiv.org/abs/2402.05232 · https://arxiv.org/abs/2604.02215 · https://arxiv.org/abs/2512.24695 · https://arxiv.org/abs/2605.16350 · https://arxiv.org/abs/2506.10943 · https://arxiv.org/abs/2305.15076 · https://arxiv.org/abs/2506.20989 · https://arxiv.org/abs/2605.06654 · https://arxiv.org/abs/2608.28557 · https://arxiv.org/abs/2608.19491 · https://arxiv.org/abs/2509.23779 · https://arxiv.org/abs/2602.17744 | Cross-operator-family transfer of a learned inner-loop rule at LM scale; learned optimizers evaluated on SSM/DeltaNet/diffusion targets; a meta-learned LoRA optimizer for LLMs; distilling a transformer's implicit ICL update into a recurrent rule — all searched, none found. Theory predicts the implicit rule differs by family, so the result is uncertain in either direction. Tinker exposes AdamW only. |
| M | Evaluation protocol for memory/TTT claims | SR-TTT v2 causality self-tests and storage/addressing/readout decomposition; Beyond Perplexity S/B/D ladder (24-paper audit; 0.0% free-form recall after one-step LoRA writes); write-in vs read-out dissociation; two-forward-pass prefix-invariance audit for hybrids (192/192 faults localized) [post-cutoff]; LongVU-TTT: fast weights aggregate rather than remember [post-cutoff] | https://arxiv.org/abs/2603.06642v2 · https://arxiv.org/abs/2607.00368 · https://github.com/sxewc/ttt-knowledge-writein-readout · https://arxiv.org/abs/2608.22876 · https://arxiv.org/abs/2608.25729 | Protocol exists; applying it to delta-rule/TTT update-rule variants (GDN-2/QED/E²-TTT) is unclaimed and is Kevin's cheapest publishable methods contribution. |
| N | Adapter and knowledge portability across bases | Single-base X→LoRA hypernetworks (T2L, Doc-to-LoRA, SHINE, Compliance2LoRA, Code2LoRA, LatentSkill, Omni2LoRA [post-cutoff], MoEGen, PAW); cross-base LoRA among softmax transformers (Cross-LoRA, LoRA-X, Trans-LoRA, TiTok, PorTAL refits to Gemma-3/4, Mistral, Inkling MoE+local/global+multimodal, portal-vlm); training-free transport (Theseus ICML 2026, BiCo, Transport-and-Merge cross-tokenizer, HeteroFusion); activation/steering transfer (model stitching, UNLOCK, Cross-Architecture Steering [post-cutoff], signed-permutation gauge); cross-tokenizer distillation (ALM, BPM, ACTD EMNLP 2026 [post-cutoff], ALIGNBEAM, HYPEROFA, Hyper-X); frozen memory + target-side reader (Engram transfer: cross-model 38.5 = same-model 38.5 on Mistral-7B) [post-cutoff]; MentorPulse refreshed latent guidance [post-cutoff]; cross-model KV translation layers [post-cutoff]; UpgradeBench direct-copy law (R=0.88–0.99 at 46B-token continuation, 0 at 2.9T; learned mappings deferred) [post-cutoff]; text-space transfer (WikiSkill) | https://arxiv.org/abs/2506.06105 · https://arxiv.org/abs/2602.15902 · https://arxiv.org/abs/2608.09227 · https://arxiv.org/abs/2607.02512 · https://arxiv.org/abs/2508.05232 · https://labs.ramp.com/research/portal-portable-task-adaptation/ · https://huggingface.co/RampPublic/portal-inkling · https://github.com/robbym-dev/portal-vlm · https://arxiv.org/abs/2602.12952 · https://arxiv.org/abs/2605.28444 · https://arxiv.org/abs/2602.05495 · https://arxiv.org/abs/2604.01674 · https://arxiv.org/abs/2506.06609 · https://arxiv.org/abs/2608.05164 · https://arxiv.org/abs/2606.31963 · https://arxiv.org/abs/2503.20083 · https://arxiv.org/abs/2607.22334 · https://arxiv.org/abs/2608.29662 · https://arxiv.org/abs/2205.12148 · https://arxiv.org/abs/2608.17050 · https://arxiv.org/abs/2608.20927 · https://arxiv.org/abs/2608.30963 · https://arxiv.org/abs/2608.03893 · https://arxiv.org/abs/2608.20918 · https://arxiv.org/abs/2608.27454 | Not found: porting a task adapter across operator families (transformer→KDA/GDN/Mamba, →dLLM, →byte-level); label-free/task-blind base alignment; tokenizer-invariant adapter representation measured as a controlled variable; update-rule porting; a sealed task×base benchmark with non-transformer targets and learned mappings; a language×task×base shared latent identified from parallel data. PorTAL's own task suite has a gold-index-0 defect on TruthfulQA/SciQ (issue #28, 2026-09-01). |
| O | Laws bounding generated/portable adapters | Override Gap (Doc-to-LoRA 46.4% on deep conflicts), Model of Models (emission recovers 11–14% of in-context gain on sequence modeling), hypernetwork scaling laws (HN approaches target size), task-vector interference is prompt-format conditioned [post-cutoff], gain-ratio non-identifiability [post-cutoff], Procedural Knowledge Is Not Low-Rank, adapter bit capacity (~2 bits/param), Hybrid-LoRA RLVR gap, Where Should LoRA Go (attention-pathway sites in hybrids), Attention Amnesia (EMNLP 2026) | https://arxiv.org/abs/2604.23750 · https://arxiv.org/abs/2608.21386 · https://arxiv.org/abs/2607.19604 · https://arxiv.org/abs/2608.09490 · https://arxiv.org/abs/2607.09156 · https://arxiv.org/abs/2607.21612 · https://arxiv.org/abs/2607.21351 · https://arxiv.org/abs/2605.18822 · https://arxiv.org/abs/2604.22127 · https://arxiv.org/abs/2606.11052 | Published ceilings; every portability proposal must cite them, restrict to procedural/format skills, evaluate on held-out prompt formats, and use attention-pathway sites in hybrids. |
| P | Latent / abstract / recurrent reasoning media | Discrete abstract tokens (Abstract-CoT, Token Assorted, iCLP, DLR, Heima); continuous thoughts (Coconut/CODI lineage, SIM-CoT, LT-Tuning, NF-CoT, flows, credit assignment); decodable latents (SELR ICML 2026, CoLT, LatentGuard); interpretable-by-construction (MUX, J-CoT, DiscoLoop, Thinking States, SWITCH, LSTR, DiffusionGemma token bottleneck); looped LMs and MoR heirs (Huginn, Ouro, Loopie, MoL, GRT [post-cutoff], PoLar, retrofits, φ=0.46 scaling law, stability regimes [post-cutoff], MixerLoop [post-cutoff], CDB serving [post-cutoff]); agents (ALAR, looped tool calling [post-cutoff], MIRAGE, DRAFT); causal audits (tokens often unnecessary; observable patterns not explanations; Huginn probing negative); Abstract-CoT has no official code and three failed reproductions | https://arxiv.org/abs/2604.22709 · https://arxiv.org/abs/2502.03275 · https://arxiv.org/abs/2606.29712 · https://arxiv.org/abs/2501.19201 · https://arxiv.org/abs/2412.06769 · https://arxiv.org/abs/2608.13570 · https://arxiv.org/abs/2608.03838 · https://arxiv.org/abs/2607.18264 · https://arxiv.org/abs/2607.21981 · https://arxiv.org/abs/2607.00341 · https://arxiv.org/abs/2602.08332 · https://arxiv.org/abs/2606.13106 · https://arxiv.org/abs/2606.20560 · https://arxiv.org/abs/2510.25741 · https://arxiv.org/abs/2608.15062 · https://arxiv.org/abs/2604.21106 · https://arxiv.org/abs/2608.18222 · https://arxiv.org/abs/2608.18230 · https://arxiv.org/abs/2606.02871 · https://arxiv.org/abs/2608.18171 · https://arxiv.org/abs/2604.04902 · https://arxiv.org/abs/2606.12689 · https://arxiv.org/abs/2507.02199 · https://github.com/LE-WH/ThinkingWithoutWordsRepro · https://huggingface.co/LauraGG/qwen25math-7b-abstract-cot-grpo | Nobody measures monitorability of a latent medium on tool-use agent tasks; no cross-medium monitorability-tax curve at matched accuracy; interpretable-by-construction latents never evaluated as a monitor channel under obfuscation; no multi-turn agent loop for looped LMs; no controlled Abstract-CoT replication with token-necessity ablations; no translation-equivariant abstract code. |
| Q | CoT monitorability measurement, incentives, attacks, weak monitors | OpenAI suite; CoT-Control (2.7% vs 61.9%); MonitorBench (COLM 2026; 50+-tool agent tasks, explicit CoT only); opaque serial depth (GDM); length-penalty tax vs no-consistent-effect (contested); CoT-Guard 4B monitors; bootstrapped monitoring; reasoning-rewrite collapse 95%→<11%; CoT-hidden backdoors; monitor-awareness obfuscation; filler-token computation; FACE-Eval tool-return cues [post-cutoff]; hidden-directive asymmetry [post-cutoff]; HCDS [post-cutoff]; fragility across 13 languages (95.9% unfaithful) | https://arxiv.org/abs/2512.18311 · https://arxiv.org/abs/2603.05706 · https://arxiv.org/abs/2603.28590 · https://arxiv.org/abs/2603.09786 · https://arxiv.org/abs/2607.09786 · https://arxiv.org/abs/2512.00218 · https://arxiv.org/abs/2605.12746 · https://arxiv.org/abs/2606.11998 · https://arxiv.org/abs/2608.00583 · https://arxiv.org/abs/2608.02820 · https://arxiv.org/abs/2605.15257 · https://arxiv.org/abs/2607.22925 · https://arxiv.org/abs/2608.29464 · https://arxiv.org/abs/2608.29070 · https://arxiv.org/abs/2608.29956 · https://arxiv.org/abs/2605.27901 · https://arxiv.org/abs/2608.04928 | Cross-lingual monitorability is nearly empty (one n=8 case study); the only latent-vs-explicit comparison is 1B/math/QA/induced hints. |
| R | Byte-level dynamic patching and boundary objectives | Entropy patches (BLT), learned routers (H-Net; lineage dormant since 2025-11), byteified frozen LMs (Bolmo), Fast BLT, Scratchpad Patching (boundary rule stops mattering once within-patch compute is redistributed; byte model best on FLORES-200), SOMBRERO surprisal steering, ATDC ratio curricula, FlexiTokens, RL boundaries (ICML 2026), ReinPatch, MAGNET per-script predictors, When Tokenizers Fail (POS/subword-target chunk alignment on a frozen LM, EMNLP 2026) [post-cutoff], Autocompleting Tokenizers (byte pruning evaluated on MT) [post-cutoff], MBP multi-byte decoding [post-cutoff], EntropyMoE, nested-vocab pre-registered negative [post-cutoff], Efficiency Gap (byte diffusion worse; entropy patches rediscover BPE), UTF-8 validity protocol (ICML 2026), Disentangling position paper | https://arxiv.org/abs/2412.09871 · https://arxiv.org/abs/2507.07955 · https://arxiv.org/abs/2512.15586 · https://arxiv.org/abs/2605.08044 · https://arxiv.org/abs/2605.09630 · https://arxiv.org/abs/2601.22805 · https://arxiv.org/abs/2605.30080 · https://arxiv.org/abs/2507.12720 · https://arxiv.org/abs/2602.13940 · https://arxiv.org/abs/2603.26097 · https://arxiv.org/abs/2407.08818 · https://arxiv.org/abs/2608.27658 · https://arxiv.org/abs/2608.15080 · https://arxiv.org/abs/2608.15454 · https://arxiv.org/abs/2608.06398 · https://arxiv.org/abs/2608.28151 · https://arxiv.org/abs/2605.12928 · https://arxiv.org/abs/2606.14122 · https://arxiv.org/abs/2608.03599 | No source uses parallel translations as a training-time signal for where boundaries fall or where global compute is spent; no compute-per-semantic-unit parity measurement across translations; no parallel-supervised byteification stage on an open lineage. |
| S | Tokenizer fertility audits; parallel data as a representation signal | Five 2026 tax audits (Indic 8.0×, African 1.88× median, European, Cyrillic, TEA) plus the `\p{L}+` pre-tokenizer ceiling (17/17 abugidas; 4.43% BPB at equal compute) [post-cutoff]; parity-aware BPE and MYTE beat BLT at 1.5B on 11 SEA languages; parallel-data static tokenizers (Parallel Tokenizers, Conditional Unigram mixed result, Trans-Tokenization); parallel data barely moves cross-lingual representation alignment (Leino & Tiedemann); bilingual documents drive translation BLEU (56% drop when removed) but not cross-lingual QA; cross-lingual self-consistency RL needs no parallel data; romanized pretraining as transfer lever (EMNLP 2026) [post-cutoff]; GI-SAE: geometric similarity does not imply functional interchangeability [post-cutoff] | https://arxiv.org/abs/2607.24276 · https://arxiv.org/abs/2606.24460 · https://arxiv.org/abs/2608.09046 · https://arxiv.org/abs/2608.26449 · https://arxiv.org/abs/2606.15044 · https://arxiv.org/abs/2510.06128 · https://arxiv.org/abs/2507.07824 · https://arxiv.org/abs/2603.29026 · https://arxiv.org/abs/2601.00364 · https://arxiv.org/abs/2606.01464 · https://arxiv.org/abs/2608.25904 · https://arxiv.org/abs/2608.23809 | Audits are saturated. Any direction whose mechanism is "parallel data aligns representations" is pre-killed by 2603.29026; parallel data's demonstrated causal payoff is token-level alignment for translation, so boundary/compute objectives must be judged on translation fidelity. |
| T | Multilingual MoE routing | Parallel-text routing analysis and inference-time steering (ICLR 2026, 1–2% gains), family-aligned routing, RISE subnetworks (EMNLP 2026 Findings), continual-pretraining routing dynamics; Tinker's shared-outer MoE LoRA | https://arxiv.org/abs/2510.04694 · https://arxiv.org/abs/2601.14050 · https://arxiv.org/abs/2604.03592 · https://arxiv.org/abs/2605.29714 · https://github.com/thinking-machines-lab/tinker-cookbook/blob/main/tinker_cookbook/hyperparam_utils.py | A training-time objective making parallel sentences route through the same experts is untested (may close as a negative given 2603.29026); routers are not reachable through Tinker LoRA. |
| U | Diffusion / non-autoregressive LMs | AR→dLLM conversion and AR-encoder/diffusion-decoder factorizations (LLaDA2.0, DiffusionGemma <10% compute, Nemotron-TwoTower, REPR-ALIGN, SDAR); diffusion+MoE (LLaDA MoE v2 23.5T tokens; REFLEX; LLaDA2.2 block routing); speculative hybrids and tri-mode (DEER, DFlash, D²SD, Nemotron-Labs); edit-based decoding (LLaDA2.1/2.2 Levenshtein editing with agentic RL; error training; CForce [post-cutoff]); variable length (DreamOn, Entropy-Valley MT [post-cutoff], CARVE [post-cutoff], survival length control [post-cutoff]); generation order (SAS, A3, Set Diffusion, insertion MDM, MBD, TDAR, answer-first negative); agents (Bitter Lesson ACL 2026: 0% multi-turn BFCL at 7–8B; DLLM Agent; DLLM-Searcher; CID position paper [post-cutoff]); repair (DCGC, SRD, DiffPDE [post-cutoff]); serving (vLLM native; 24% GPU share at batch 1 [post-cutoff]); theory (conditional total correlation/serial depth [post-cutoff]; ParallelBench ICLR 2026; 58-benchmark map); commercial APIs (Mercury 2/2.5; independent 684 tok/s) | https://huggingface.co/inclusionAI/LLaDA2.2-flash · https://arxiv.org/abs/2608.00146 · https://arxiv.org/abs/2606.26493 · https://arxiv.org/abs/2605.06885 · https://arxiv.org/abs/2608.03457 · https://arxiv.org/abs/2608.01784 · https://arxiv.org/abs/2512.15176 · https://arxiv.org/abs/2602.06036 · https://arxiv.org/abs/2607.05722 · https://arxiv.org/abs/2608.13925 · https://arxiv.org/abs/2608.22274 · https://arxiv.org/abs/2608.30922 · https://arxiv.org/abs/2608.26374 · https://arxiv.org/abs/2606.23567 · https://arxiv.org/abs/2601.13228 · https://arxiv.org/abs/2608.05687 · https://arxiv.org/abs/2601.12979 · https://arxiv.org/abs/2602.07451 · https://arxiv.org/abs/2608.10438 · https://arxiv.org/abs/2608.25428 · https://arxiv.org/abs/2608.22090 · https://arxiv.org/abs/2608.30532 · https://arxiv.org/abs/2608.23807 · https://arxiv.org/abs/2608.25505 · https://arxiv.org/abs/2606.12232 · https://artificialanalysis.ai/models/mercury-2 | No controlled iso-wall-time dLLM-vs-AR comparison on agent tasks with CPU overhead charged; no language-dependent serial-depth measurement with content held fixed; no bilingual joint-canvas dLLM on parallel corpora; localized re-denoising of executed typed plans needs four new deltas to survive CID/LLaDA2.2/remasking-negative collisions. |
| V | Agent memory admission, credit and causal analysis | Hindsight Memory-PRM intervention-calibrated per-entry credit (post-hoc deletion-and-reanswer) [post-cutoff]; SCM pathway tracing [post-cutoff]; MemGauge stage-wise exposure [post-cutoff]; AdmitOR calibrated-FDR admission gate (pre-registered criterion failed on wild stream) [post-cutoff]; Recuris validation-gated writes [post-cutoff]; ContextPilot RL (EMNLP 2026); reward-SNR floor: learned acquisition routing never beat random; noise placebo reproduces oracle gain [post-cutoff]; credit-routed budgets no better than uniform [post-cutoff]; provenance screening fails against poisoning [post-cutoff]; catastrophic remembering with inverted-IFEval oracle world [post-cutoff] | https://arxiv.org/abs/2608.29605 · https://arxiv.org/abs/2608.30198 · https://arxiv.org/abs/2608.30177 · https://arxiv.org/abs/2608.15565 · https://arxiv.org/abs/2608.24876 · https://arxiv.org/abs/2608.28476 · https://arxiv.org/abs/2608.10441 · https://arxiv.org/abs/2608.28011 · https://arxiv.org/abs/2608.21230 · https://arxiv.org/abs/2608.11095 | Prospective, known-propensity randomization of one retained item at first eligible service with write-time-only covariates and a paired replay oracle — not found; but the reward-SNR floor says the paired oracle may show a true average effect that no deployable gate can learn. |
| W | Harness science | Harness-effect measurement (5–24 pt same-model spreads; TB2.1 benchmark defects worth up to 12 pp); automatic harness evolution and its negatives (no consistent win over matched-budget parallel sampling, +0.6 held-out; non-compounding; task-order fragility) [post-cutoff]; harness-in-the-loop RL (Agent Lightning v1.0, AC2, Co-Harness) [post-cutoff]; portability protocols (AI SDK HarnessAgent/ACP, UHP, Agent Plugins, dsh/Cordis calculus); safety (HarnessRisk, Hack-Verifiable TB) [post-cutoff]; StateM harness scaling (95.3% TB2.1) [post-cutoff]; StarHarness cross-family transfer [post-cutoff] | https://arxiv.org/abs/2605.27922 · https://arxiv.org/abs/2607.03691 · https://arxiv.org/abs/2607.12227 · https://arxiv.org/abs/2607.14004 · https://arxiv.org/abs/2608.18066 · https://arxiv.org/abs/2608.17528 · https://arxiv.org/abs/2607.22688 · https://arxiv.org/abs/2608.15089 · https://arxiv.org/abs/2608.24804 · https://arxiv.org/abs/2608.17597 · https://arxiv.org/abs/2608.22103 · https://github.com/deepseek-ai/deepseek-harness · https://arxiv.org/abs/2608.25512 · https://www.tbench.ai/news/leaderboard-integrity-update | Natural-language-multilingual harness effects; harness-invariance as a trained property; heavy→minimal harness distillation with a parity endpoint; randomized factorial attribution with real models (Thaki's factorial uses simulated tiers). All are harness-layer, not architecture. |
| X | Evaluation methodology and instrument integrity | Small-Scale Experiments (≥256 configs/scale; HP sensitivity) [post-cutoff]; iso-depth law φ=0.46; 3-seed asymptote floor 0.02; Anthropic error bars; resolution diagnostics q=N/N*; Sober Look (COLM 2025); ATLAS length profiling; PredicateLongBench; LongCA-bench kernels (ICLR 2026); Zoology stacked/continuous MQAR; KATA evidence bundle; contamination taxonomy + JSON disclosure [post-cutoff]; SA-PPG; scale-aware memorization probes [post-cutoff]; SWE-bench Verified retired and Pro ~30% broken; Terminal-Bench 3.0/4.0 integrity protocol [post-cutoff]; tau2 golden-replay defect [post-cutoff]; Gaia2 3-run SEs; OmnilingualGAIA2 scale-invariant 8.8–18.4 pt gap [post-cutoff]; Cultivar FLORES contamination probe [post-cutoff]; evaluation scores as perishable claims; Impossibility Triangle withdrawn; Mamba-2 state-sink self-correction [post-cutoff] | https://arxiv.org/abs/2608.11859 · https://arxiv.org/abs/2604.21106 · https://arxiv.org/abs/2509.14786 · https://arxiv.org/abs/2411.00640 · https://arxiv.org/abs/2605.30315 · https://arxiv.org/abs/2504.07086 · https://arxiv.org/abs/2605.28079 · https://arxiv.org/abs/2607.08284 · https://github.com/HazyResearch/zoology · https://arxiv.org/abs/2608.29463 · https://arxiv.org/abs/2608.07341 · https://arxiv.org/abs/2608.12771 · https://www.tbench.ai/news/terminal-bench-4-0 · https://github.com/sierra-research/tau2-bench/issues/499 · https://arxiv.org/abs/2509.17158 · https://arxiv.org/abs/2608.08775 · https://arxiv.org/abs/2608.09766 · https://arxiv.org/abs/2607.26191 · https://arxiv.org/abs/2605.05066 · https://arxiv.org/abs/2606.00930 | No seed-variance atlas for 0.1–1B architecture arms; no translation-paired recall probes; no sub-1B from-scratch length-profiled suite; no instrument separating environment stochasticity from agent effects; no standardized iso-wall-time bench including recurrent kernels. |
| Y | Compute substrate (constraints, not research axes) | Tinker: LoRA-only (rank/seed/3 module groups), shared-outer MoE LoRA (98.6% of Kimi-K2.6 LoRA params in expert MLP factors), logprob-only custom losses, AdamW-only, token-id inputs, no adapter import, no hidden states, 32K/128K on Kimi-K2.6, multi-tenant clock cycles, server rejects old SDKs; local: K3 needs ≥8×GB300, K2.6 INT4 = 640 GB exactly, no Qwen3.8 bases or sub-27B, no released 2026 KDA/QSA base, transformers KDA fallback yields NaN gradients (PR #48455), kernels opt-in since v5.15; infra: Slurm 21.08 has no cgroup/v2; target Slurm 25.11.7 + Pyxis 0.24.0 + Enroot 4.2.1 | https://tinker-docs.thinkingmachines.ai/tinker/models/ · https://tinker-docs.thinkingmachines.ai/tinker/losses/custom/ · https://github.com/thinking-machines-lab/tinker-feedback/issues/141 · https://recipes.vllm.ai/moonshotai/Kimi-K3 · https://huggingface.co/api/models?author=Qwen · https://github.com/huggingface/transformers/pull/48455 · https://slurm.schedmd.com/cgroup_v2.html · https://github.com/NVIDIA/pyxis/releases | Feasibility knowledge nobody has published: H100 FlashKDA fwd/bwd numbers; a pinned LoRA/full-FT memory-throughput report for 2026 hybrids on H100; effect of Tinker's shared-outer scheme on routing; rank>4 sensitivity at 1T; a Slurm 25.11 + Pyxis 0.24 + Enroot 4.2 compatibility receipt; SIGUSR1 propagation through Pyxis. |


---

## 2. Open gaps — deduplicated, each searched by at least one cell and not found

Every entry below was the target of an explicit search in at least one cell (queries are recorded in the cell notes) and came back empty or adjacent-only. Collision risk is a judgment of how likely another group publishes the same thing within ~6 months given how crowded the surrounding axes are. "Supporting cells" names the cell notes whose gap lists merge into the entry.

### G1. Parallel-translation supervision of dynamic byte/patch boundaries (Direction 18, with five new mandatory controls)
- **Mechanism hint.** Transport boundary mass across aligned spans of a parallel corpus (unbalanced OT on span alignments from OmniAlign/CTFAlign) as an auxiliary loss on the BLT/H-Net boundary head or Bolmo's stage-1 boundary predictor; keep the delta to boundary formation only and drop or ablate the patch-state transport term.
- **Why open.** Every 2026 boundary objective targets monolingual signals (surprisal, compression rate, POS/subword targets); every parallel-data tokenization work targets static vocabularies; Disentangling (2608.03599) frames "reshape boundaries, keep capability" but reports no experiment. When Tokenizers Fail (EMNLP 2026) has zero uses of parallel data in its full text.
- **New required controls.** Scratchpad-style compute-matched arm (2605.09630: patchifier choice stops mattering once within-patch compute is redistributed); parity-aware BPE with the `\p{L}+` regex fixed (2606.15044, 2608.26449); POS/subword-target boundary arm (2608.27658); entropy/predictability byte-pruning arm on the same MT pairs (2608.15080); romanized-input arm (2608.25904); MAGNET per-script predictors (2407.08818); UTF-8 validity endpoint for CJK (2606.14122); ablate λ_z given 2603.29026; pre-register a BPB margin against the −3.64%/−2.96% nested-vocab negative (2608.28151).
- **Kevin advantage.** Production parallel data with terminology/error categories; BLT upstream in transformers (patched 2026-08-26); Bolmo-1B as an Apache-licensed retrofit base instead of CC-BY-NC BLT-1B; 8×H100 covers the 20M–125M matched grid; the NumPy UOT doctor already exists in the repo.
- **Collision risk.** Low–medium (the framing is published; the mechanism is not).
- **Supporting cells.** tokenizer-free-multilingual G1/G5; killshot-current #2; arxiv-triage-agents-eval-ml; benchmarks-eval G2.

### G2. Language/script-controlled probes of recurrent state: does a fixed-size state store meaning or surface?
- **Mechanism hint.** Translation-paired MQAR/NIAH where the key is stored in language A and queried in language B with semantically equivalent spans; per-script recall/decay curves for GDN/KDA hybrids at the 1-in-4 ratio; cross-lingual readout of fast-weight writes (TTT-NTP, E²-TTT, FwPKM checkpoints); depth-attention weights (AttnRes) as a routing probe on translation pairs.
- **Why open.** Production hybrids report at most one multilingual aggregate (Qwen3.8-Next Table 1: MMMLU 47.74 / 51.33 / 54.83); no MQAR/RULER artifact is cross-lingual (BABILong-ITA translates the haystack, not the key/query pair); FAAST is the only fast-weight paper touching translation and uses parallel data as labels only; no source asks whether a memory written in one language is readable in another.
- **Kevin advantage.** Parallel corpora with span alignment make the probe buildable today; open controls exist (startlux GDN hybrids 340M/1.3B, Mamba-3 checkpoints, E²-TTT 340M/1.3B, FwPKM l12, Qwen3.5-0.8B–9B bases); the harness already enforces exact-match generation evaluation; 8×H100 trains 0.1–1B hybrids on fixed multilingual data.
- **Collision risk.** Low.
- **Supporting cells.** seq-operators G1; ttt-fastweights G4; learned-update-rules G4; benchmarks-eval G2; bookmarks G2; local-model-ecosystem G4.

### G3. Porting a task adapter across operator families (softmax transformer → KDA/GDN/Mamba hybrid, masked-diffusion LM, byte-level model), with tokenizer crossing measured as a controlled variable
- **Mechanism hint.** PorTAL's factorization (shared task latent + canonical core + per-base alignment) with the alignment restricted to the attention-pathway sites 2604.22127 identifies as safe in hybrids; byte- or meaning-anchored alignment (parallel sentences as the shared coordinate) so the same latent ports across tokenizers and languages (Hyper-X ×PorTAL: language × task × base).
- **Why open.** PorTAL's "hybrid attention" targets are local/global softmax attention (Inkling config.json); base-conversion papers move weights, never fine-tunes; hybrid-adaptation papers adapt natively; UpgradeBench states shape-incompatible hops admit no weight-space method and measures none; cross-tokenizer transfer lives at the logit/distillation level (ALM, BPM, ACTD), never at the adapter level; frozen-memory reader transfer (Engram) and KV translation port state, not task adapters.
- **Kevin advantage.** Kimi-Linear-48B-A3B (KDA), Mamba-130M, Qwen3.5-0.8B–9B (GDN hybrids), LLaDA-8B, BLT-1B/Bolmo-1B are registered locally; Tinker supplies source adapters on Kimi-K2.6/Qwen3.5/GLM-5.3; portallib is reproducible for ~$50 but its task suite needs shuffled choices (issue #28).
- **Collision risk.** Medium (Ramp's roadmap points at description encoders, not new families; but merging groups have live code for cross-family alignment).
- **Supporting cells.** adapter-portability G1/G3/G6; bookmarks G3; killshot-current #3.

### G4. Label-free / task-blind base alignment for a portable hypernetwork, calibrated on parallel data (Direction 8 restated)
- **Mechanism hint.** Activation-OT or Procrustes alignment (Theseus, Transport-and-Merge, model stitching) fitted on parallel sentences as a paired, label-free, semantically anchored stimulus set that exists in the same meaning space for every base; signed-permutation gauge handling for RMSNorm bases.
- **Why open.** PorTAL refits use 8–2,000 gold-labeled examples per task; Theseus/BiCo are label-free but transport one static task vector within a family with an 11–21 point gap to fine-tuning; Cross-Architecture Steering needs a 98k-passage bridge per pair; UpgradeBench's CKA probe predicts copy retention (ρ=0.74, n=8) but produces no alignment.
- **Kevin advantage.** Parallel data as the calibration stream; 8×H100 for a 12–20-model meta-training grid.
- **Collision risk.** Medium–high (two groups converged on Procrustes transport in 2026).
- **Supporting cells.** adapter-portability G2.

### G5. Porting an update rule rather than weights (Direction 16, narrowed)
- **Mechanism hint.** Meta-learn the fast-weight step-size/preconditioner/erase-write policy as a small network on one operator family (TTT-MLP or GDN layer), freeze it, evaluate on a different family (softmax-window TTT, KDA, masked-diffusion denoiser) on a sealed held-out task × base cell; controls: Modular TTT primitives, derived rules (Kaczmarz, OSDN, P-DeltaNet), Falcon family, static frozen-memory + reader (Engram), MentorPulse, KV translation, PorTAL static adapters.
- **Why open.** Modular TTT factorizes but never transfers; MetaNCA/UNF transfer only on ≤2M-parameter feedforward nets; FedNL shares rules across clients of one architecture; Celo2/ELO transfer MLP→transformer only; ICL theory predicts the implicit rule differs by family (GD emulation vs online GD vs Bayes filter), so the outcome is informative either way.
- **Kevin advantage.** 340M–1.3B / 15–100B-token regime fits one node; SIGUSR1-resumable harness suits long truncated-BPTT meta-training; parallel data gives a paired "same content, different surface" probe of what a ported rule preserves. Caveat: Tinker exposes AdamW only, so the 1T tier is evaluation-only.
- **Collision risk.** High (learned-optimizer and TTT literatures are large and fast).
- **Supporting cells.** learned-update-rules G1/G2/G3/G6; adapter-portability G4; killshot-current #3; arxiv-triage-arch/adr.

### G6. Causality-verified independent replication of beyond-window TTT recall, plus behavioral (D-level) evaluation of update-rule variants
- **Mechanism hint.** Run E²-TTT (93.6% S-NIAH-1 at 16K), FwPKM (4K→128K) and MoNe under SR-TTT-style startup causality self-tests, needle-outside-window stratification, generation exact match with paired McNemar, and Beyond Perplexity's recall/paraphrase/delay/locality battery; extend to GDN-2/QED/E²-TTT/Modular-TTT variants; add the two-forward-pass prefix-invariance audit (2608.22876).
- **Why open.** SR-TTT v2 showed such gains can be off-by-one and non-causal artifacts; TTT-E2E's own table gives 0.06 pass-key at 128K and issue #8 is unanswered; the 2026 papers report kernel equivalence but no leakage checks; nobody outside the author groups has audited them.
- **Kevin advantage.** Released 340M/1.3B checkpoints run on one H100; the CMHT CPU-oracle design and hash-chained receipts already exist.
- **Collision risk.** Low (methodology; negative result equally publishable).
- **Supporting cells.** ttt-fastweights G1; learned-update-rules G5; benchmarks-eval.

### G7. Verifiable reset/rollback/deletion of test-time-learned state, and poisoning of fast-weight layers
- **Mechanism hint.** Bitwise rollback attestation of a request's fast-weight writes via deterministic replay and hash-chained logs; context-borne poison persistence in Titans/TTT/In-Place/E²-TTT layers with a LoRA-TTT control arm.
- **Why open.** RW-TTT isolates request-owned state for throughput only; TTT-E2E avoids boundary resets by discarding short documents; native KDA deletion receipts are a negative (12–49% drift; only checkpoint replay verifies); the only TTT security papers attack LoRA-TTT (ASR@10 95%/93%) and TTRL.
- **Kevin advantage.** Deterministic replay, audit log and checkpoint/resume contract are the required machinery; small TTT layers fit the node.
- **Collision risk.** Low.
- **Supporting cells.** ttt-fastweights G2/G3; seq-operators F29.

### G8. Stability theory for nonlinear fast weights; partial independent replication of the Google neural-memory line
- **Mechanism hint.** Extend the momentwo second-order recurrence (linear Titans) to MLP/SwiGLU fast weights; measure safe (lr, decay, momentum, clipping) regions against Modular TTT divergence and In-Place TTT's 62.5× output ratios; replicate Titans/Atlas/HOPE at 340M–760M on 15–30B tokens.
- **Why open.** Only the linear case has a closed form; all Google headline numbers are first-party with no code; the most-starred reproduction targets mechanism fidelity, not parity.
- **Kevin advantage.** fp64 CPU oracle plus tiny pinned models for sweeps; digest-pinned images for an auditable partial replication.
- **Collision risk.** Low; value moderate (Google-scale claims stay out of reach).
- **Supporting cells.** ttt-fastweights G5/G6; benchmarks-eval F42.

### G9. Independent, iso-compute, multi-seed comparison of depth-axis operators (pre-norm vs Block/Full AttnRes vs mHC vs Gated Residual) at 0.1–1B
- **Mechanism hint.** 120M–350M × 5 seeds × 4 residual designs with per-arm HP search, plus the depth-attention weights as a probe on parallel data (do translation pairs share depth routing).
- **Why open.** Only first-party single runs exist (Qwen Tables 5/6 at 25B-A3B; AttnRes Table 2 vs "mHC-lite"); different baselines, optimizers and scales; RD-AttnRes compares within the AttnRes family only; third-party HF reproductions exist but no cross-family comparison.
- **Kevin advantage.** fla ≥0.5.1 ships the AttnRes operator (Gluon backend in 0.5.2); the seed/checkpoint contract fits the sweep.
- **Collision risk.** Medium (any academic lab could run it).
- **Supporting cells.** seq-operators G2; bookmarks G2; local-model-ecosystem G5.

### G10. Mechanism of the NoPE-in-hybrids disagreement (1M extrapolation vs post-training endless generation)
- **Mechanism hint.** Pretrain + SFT/RL 0.1–1B hybrids with RoPE / NoPE / partial-RoPE global layers on identical data, KDA channel-wise vs GDN scalar decay, with early context-extension probes (Cracks in the Foundation) and a length-controlled multilingual termination probe; Tinker post-training on Qwen3.5 hybrids (partial RoPE 0.25) as production-scale control.
- **Why open.** Kimi Linear/K3 and Solar Open 2 ship NoPE and claim direct 1M extrapolation; Qwen3.8-Next found NoPE indistinguishable in pretraining but with "substantially higher rate of endless generation after post-training"; 2606.15378 finds NoPE helps small-window SWA hybrids; no source isolates the mechanism.
- **Collision risk.** Medium.
- **Supporting cells.** seq-operators G3.

### G11. Controlled MTP ablation on ≤1B linear/hybrid backbones
- **Mechanism hint.** Iso-compute MTP-on/off on GDN/KDA hybrids; draft-head designs that read recurrent state (Windowed-MTP caveat); Qwen3.5-0.8B (MTP head present) as open reference.
- **Why open.** MTP is standard in every production hybrid, but every source is a production report or a serving paper; no controlled small-hybrid ablation found (arXiv `"multi-token prediction" AND (hybrid OR "linear attention" OR "state space")` → 11 results, none).
- **Collision risk.** Medium; moderate architectural novelty, high value as a clean positive or negative.
- **Supporting cells.** seq-operators G4.

### G12. Open, reproducible ≤1B reference of the K3 stack and the training-side numbers nobody publishes
- **Mechanism hint.** From-scratch 350M/15B-token KDA-LB + full-rank gate, NoPE global attention, Block AttnRes, MTP with a released recipe; H100 (SM90) FlashKDA fwd/bwd benchmarks; a digest-pinned LoRA/full-FT memory-throughput report for Qwen3.8-27B (GDN), Nemotron-3.5-Lightning-Base (Mamba-2), Gemma-4-26B-A4B, FP8-frozen LoRA on GLM-5.3-Flash (KDA); Slurm 25.11.7 + Pyxis 0.24.0 + Enroot 4.2.1 compatibility receipt with SIGUSR1-through-Pyxis and eBPF device-constraint proofs.
- **Why open.** Pieces exist separately (GDN hybrids at 340M/1.3B, dense AttnRes reproductions, pure-KDA tiny checkpoints without cards, a 0.6B conversion) but no combined small reference; FlashKDA publishes H20 numbers only and accelerates inference only; vendor cards contain zero fine-tuning guidance; no sub-10B KDA base and no 2026 KDA/QSA base checkpoint is released; transformers' KDA fallback yields NaN gradients (PR #48455); no public Pyxis/Enroot/Slurm-25.11 version matrix exists.
- **Kevin advantage.** fla ≥0.5.2 kernels plus FlashQLA training backend; the node; root on a dedicated host with an existing doctor framework. Infrastructure-shaped, but the prerequisite for G2, G9–G11 and for any Coded-Delta negative.
- **Collision risk.** Low for the receipts; medium for the reference model.
- **Supporting cells.** seq-operators G5; bookmarks G1; local-model-ecosystem G1/G2/G3/G5; infra-slurm G1–G5; tinker-rl G4.

### G13. Cross-lingual behaviour of learned sparse indexers (DSA/QSA/CSA)
- **Mechanism hint.** Measure whether selected blocks correspond across translations of the same document; supervise an indexer with parallel data toward language-invariant selection; 0.1–1B sparse-attention models via fla's NSA/MoBA/DSA references; GLM-5.3 on Tinker for behavioural probes only.
- **Why open.** Indexers are KL-distilled to full attention on mostly English/Chinese/code; LongCat LSA, Qwen3.8-Next and DeepSeek-V4 sections contain no per-language analysis (arXiv `"sparse attention" AND (multilingual OR "cross-lingual") AND "language model"` → 1 unrelated 2022 result).
- **Collision risk.** Low.
- **Supporting cells.** seq-operators G6.

### G14. Monitorability of latent/abstract reasoning media on tool-use agent tasks, a cross-medium monitorability-tax curve, and interpretable-by-construction latents as a monitor channel
- **Mechanism hint.** One fixed monitor across verbose CoT → length-penalized CoT → hybrid checkpoints → abstract tokens → continuous thoughts at matched accuracy; replay the reasoning-rewrite attack (2608.00583) and monitor-awareness pressure (2605.15257) against MUX/J-CoT/DiscoLoop/SWITCH; multi-turn agent loops for Ouro/Huginn with real tool feedback; tool-call argument fidelity per medium.
- **Why open.** Latent-medium papers for agents (ALAR, 2608.18171, MIRAGE) report tokens and accuracy only; monitorability papers (OpenAI suite, MonitorBench) cover explicit CoT only; the single latent-vs-explicit comparison is 1B/math/QA/induced hints; the compressed-CoT tax evidence is contradictory (2607.09786 vs 2512.00218); all four interpretable-by-construction papers report accuracy/compression only.
- **Kevin advantage.** Harness carries agent-loop, oracle, trace and paired-regression contracts; 8×H100 covers 4B–8B; Tinker RL on Qwen3.5-4B/9B for the escalation policy; GDM's opaque-serial-depth tool is open.
- **Collision risk.** Medium (monitorability is filling fast).
- **Supporting cells.** latent-reasoning G1/G4/G5/G6; arxiv-triage-adapt-reason-diff.

### G15. Translation-equivariant abstract reasoning codes and cross-language monitor transfer
- **Mechanism hint.** Parallel data as the supervision forcing one abstract trace for semantically equivalent problems across languages (abstract tokens or J-space states); train the monitor in one language, test in others; the 13-language fragility benchmark (2605.27901) defines the evaluation; the audio-LLM language-agnostic middle-layer workspace (2608.24958) is the existence proof for a readable shared code.
- **Why open.** LatentMT treats MT as the task; SOLAR aligns soft tokens to an English pivot for accuracy; 2601.02996 only diagnoses an English-centered pathway; cross-lingual self-consistency RL uses no parallel data; cross-lingual CoT monitorability has one n=8 case study.
- **Collision risk.** Low–medium.
- **Supporting cells.** latent-reasoning G2; arxiv-triage-adapt-reason-diff #6; tokenizer-free G4 (equivariance constraint; low expected value on its own).

### G16. Controlled Abstract-CoT reproduction with token-necessity ablations at 4B–8B
- **Mechanism hint.** Reproduce the masked-bottleneck warm-up on Qwen3.5-4B/9B-Base with random/zero abstract-prefix ablations, trace-collapse reporting and paired regressions.
- **Why open.** No official IBM code found; LE-WH (8×H200) reached 74.2% vs the 86.2% target with trace collapse to one 13-token sequence; LauraGG (1×H100) found random tokens 54% vs learned 51%; bertybaums stalled.
- **Collision risk.** Medium (a reproduction; publishable either way).
- **Supporting cells.** latent-reasoning G3.

### G17. Diffusion LMs: iso-wall-time agent comparison, language-dependent serial depth, bilingual joint canvas
- **Mechanism hint.** DiffusionGemma-26B-A4B (vLLM native) vs a Qwen3.5 AR sibling served identically with TTFT/TPOT/p50–p99 at batch 1/8/32 and CPU dispatch charged; measure conditional total correlation per reveal round (2608.25505) and steps-to-convergence per language on translation-equivalent prompts; a [source ; target] joint-canvas dLLM on parallel corpora (cite Mask-Predict/Levenshtein Transformer as prior art).
- **Why open.** Every wall-time win is first-party/batch-1 or gives the AR arm MTP; 76% of batch-1 wall-clock is CPU overhead; Entropy-Valley's En→De vs Zh asymmetry (33% vs 65% of oracle gap) is unexplained; the only dLLM MT work uses one LoRA per direction.
- **Collision risk.** Medium.
- **Supporting cells.** diffusion-nonar G1/G2/G3.

### G18. Prospective randomized identification of per-item memory value (Direction 17 residual)
- **Mechanism hint.** Known-propensity randomization of one retained item at its first eligible service, write-time-only covariates, paired deterministic replay oracle; mandatory controls: Hindsight Memory-PRM post-hoc deletion credit, AdmitOR agreement gate, matched-moment noise placebo and a reward-SNR estimate as pre-registered gates.
- **Why open.** Hindsight Memory-PRM intervenes at answer time (query-conditioned deletion) and its critic is operation-conditioned; SCM tracing and MemGauge analyze rather than randomize; no source randomizes eligibility or estimates propensities.
- **Collision risk.** Medium–high; kill-risk from the reward-SNR floor.
- **Supporting cells.** killshot-current #1; arxiv-triage-agents-eval-ml; arxiv-triage-adapt-reason-diff.

### G19. Training-time cross-lingual MoE routing consistency and compute-per-semantic-unit parity
- **Mechanism hint.** A routing objective making parallel sentences activate the same middle-layer experts in a from-scratch small MoE; a ledger of BLT/H-Net/Bolmo global-compute units per aligned sentence across languages at matched quality.
- **Why open.** Four 2026 MoE-multilingual papers analyze or steer routing post hoc; fertility audits count tokens for static tokenizers; Scratchpad ranks BPB across FLORES-200 but reports no FLOPs per aligned sentence.
- **Collision risk.** Medium; the routing objective may close as a negative given 2603.29026; routers are not reachable through Tinker.
- **Supporting cells.** tokenizer-free G2/G3.

### G20. Evaluation instruments missing at 0.1–1B
- **Mechanism hint.** A seed-variance atlas (10 seeds × 3 sizes × 3 mixers), a sub-1B from-scratch length-profiled and axis-controlled long-context suite, an instrument separating environment stochasticity from agent effects (tau2 shows 57.9–64.9% of first user-sim messages differ at temperature 0), an iso-wall-time bench including recurrent kernels.
- **Why open.** Small-Scale Experiments covers HP configurations, not seeds; ATLAS/PredicateLongBench are frontier-only; LongCA-bench covers attention kernels only; no leaderboard reports an environment noise floor.
- **Collision risk.** Low; methodology that protects Kevin's own claims.
- **Supporting cells.** benchmarks-eval G1/G3/G4/G6.

### G21. Harness-layer gaps (recorded, not recommended as architecture work)
- Natural-language-multilingual harness effects; harness-invariance as a trained property; heavy→minimal harness distillation with a parity endpoint (naming hazard: "harness distillation" already means extraction attacks); randomized factorial attribution with real models. Kevin's parallel data and uniform drivers (AI SDK HarnessAgent/ACP, UHP, dsh plugins) make these cheap, but they are measurement contributions.
- **Supporting cells.** harness-ecosystem G1–G4.

### G22. Tinker-specific knowledge gaps (infrastructure evidence)
- Effect of the shared-outer MoE LoRA scheme on expert specialization/routing at 1T; rank sensitivity above 4 on Kimi-K2.6 (TML swept ranks 1/2/4 only); routing stability of LoRA-RL without routing replay (expert-balance telemetry is free); verifiable-reward translation RL on a 1T policy; a two-tier protocol (skyrl-tx locally, Tinker hosted) with one script.
- **Supporting cells.** tinker-rl G1–G5.

**Re-confirmed occupied (do not re-propose without a delta):** better generic linear attention or delta-rule gate; static or learned operator ratio/placement; "train once, port a LoRA" among softmax transformers; task-description→LoRA hypernetworks; surprise-gated memory; diffusion+MoE; automatic harness evolution; strap-on memory layers and portable-memory protocols; sink phenomenology; fertility audits.

---

## 3. Kill-shot verdicts for the current repo directions

Vocabulary: STILL_OPEN (mechanism unclaimed; controls may have changed), NARROWED (part of the claimed delta is now taken; a smaller delta survives), OCCUPIED (the mechanism as written exists), UNKNOWN. The five directions with `experiments/architectures/*.yaml` come first; two ranked-portfolio items without a yaml follow.

### D16 — Portable Sidecar Update Dynamics (`portable-sidecar-update.yaml`) — NARROWED
- The "portable object + thin target-side alignment" factorization is now occupied twice for state: Cross-Model Memory Transfer freezes an Engram memory and adapts only a reader (Mistral-7B target: cross-model 38.5 = same-model 38.5 vs no-memory 32.1; 2608.17050, 2026-08-17) and MentorPulse ports refreshed latent guidance from a frozen mentor (52.2% of the mentor–student gap; 2608.20927, 2026-08-21); cross-model KV translation layers (2608.30963, 2608.03893) port activations. Fast-weight update-rule families are systematized (Falcon 2608.27763; Modular TTT 2608.07110), so rule-family novelty is gone. UpgradeBench (2608.20918) shows direct copying retains R=0.88–0.99 only across a 46B-token continuation and defers learned mappings. PorTAL's task suite has a gold-index-0 defect on two tasks (issue #28, 2026-09-01).
- Surviving delta: a task-conditioned **online update rule** ported with task-blind alignment onto a held-out task × base cell, ideally across operator families. Feasibility caveat: Tinker's optimizer is AdamW-only, so any rule-level experiment is local.
- Evidence: https://arxiv.org/abs/2608.17050 · https://arxiv.org/abs/2608.20927 · https://arxiv.org/abs/2608.30963 · https://arxiv.org/abs/2608.03893 · https://arxiv.org/abs/2608.27763 · https://arxiv.org/abs/2608.07110 · https://arxiv.org/abs/2608.20918 · https://github.com/ramp-public/portallib/issues/28 · https://arxiv.org/abs/2608.17616 · https://tinker-docs.thinkingmachines.ai/tinker/api-reference/trainingclient/

### D17 — Causal Memory Holdout Trials (`causal-memory-holdout.yaml`) — NARROWED
- Hindsight Memory-PRM (2608.29605, 2026-08-30) occupies intervention-calibrated per-entry memory credit ("one controlled deletion-and-reanswer per probe", no per-operation labels, no Monte-Carlo replay) as a proxy reward (8B policy 77.5% LoCoMo vs API teacher 65.1%); SCM pathway tracing (2608.30198) and MemGauge stage-wise exposure (2608.30177) occupy causal analysis; AdmitOR (2608.15565), Recuris (2608.24876), HarnessLens, OpsHarness occupy "memory/skill admission gate" (four entries in three weeks). Kill-risk: the reward-SNR floor (2608.10441) finds learned per-instance acquisition routing never beat random and a matched-moment noise placebo reproduced ≥100% of the oracle's apparent gain; credit-routed budgets no better than uniform (2608.28011); provenance screening fails against poisoning (2608.21230).
- Surviving delta: prospective known-propensity randomization at first service with write-time-only covariates and a paired replay oracle — described as randomized identification, not as "a gate" — with Hindsight-PRM, AdmitOR, noise-placebo and reward-SNR controls pre-registered.
- Evidence: https://arxiv.org/abs/2608.29605 · https://arxiv.org/abs/2608.30198 · https://arxiv.org/abs/2608.30177 · https://arxiv.org/abs/2608.15565 · https://arxiv.org/abs/2608.24876 · https://arxiv.org/abs/2608.10441 · https://arxiv.org/abs/2608.28011 · https://arxiv.org/abs/2608.21230 · https://arxiv.org/abs/2608.11095

### D18 — Translation-Equivariant Byte Boundaries (`translation-equivariant-byte-patches.yaml`) — STILL_OPEN
- No source transports boundary probability across translation alignments (four cells searched independently). Nearest neighbors: When Tokenizers Fail (EMNLP 2026; POS/subword-target chunk alignment on a frozen subword LM, monolingual; 2608.27658), Autocompleting Tokenizers (monolingual byte pruning evaluated on MT; 2608.15080), MAGNET per-script predictors (2407.08818, missing from the collision list), Disentangling position paper (2608.03599). Kill-shot risks: Scratchpad Patching shows patchifier choice stops mattering once within-patch compute is redistributed (2605.09630); parity-aware BPE beats BLT at 1.5B on 11 SEA languages (2606.15044); Leino & Tiedemann show parallel data barely moves representation alignment (2603.29026) — drop or ablate λ_z; nested-vocab negative gives a pre-registered BPB margin (2608.28151); the `\p{L}+` regex bug invalidates any unpatched BPE control on abugidas (2608.26449); romanized pretraining is a cheap parity baseline (2608.25904).
- Verdict stands as STILL_OPEN because the mechanism is unclaimed; the contract needs five extra arms and a boundary-only delta.
- Evidence: https://arxiv.org/abs/2608.27658 · https://arxiv.org/abs/2608.15080 · https://arxiv.org/abs/2407.08818 · https://arxiv.org/abs/2608.03599 · https://arxiv.org/abs/2605.09630 · https://arxiv.org/abs/2606.15044 · https://arxiv.org/abs/2603.29026 · https://arxiv.org/abs/2608.28151 · https://arxiv.org/abs/2608.26449 · https://arxiv.org/abs/2608.25904 · https://arxiv.org/abs/2608.17325 · https://arxiv.org/abs/2608.18474

### Coded Delta Memory (diagnostic A, `coded-delta-memory.yaml`) — NARROWED (keep only as a negative-result cell)
- No parity/erasure code with an explicit syndrome inside DeltaNet state was found before or after the cutoff (three cells searched). But the "detect and repair recurrent-state trouble" axis is now dense: QED measures read interference through the query and erases it (about 2× usable S-NIAH-1 context; 2608.13668); SANE's norm-anomaly statistic and tanh compression stabilize RWKV-7 to 100M tokens and expose the failure geometry (few channels accumulate extreme values — exactly the correlated-multi-block regime that breaks a single-erasure code; 2608.22354); MARCH adds content-routed anchors (2608.12435); Bayesian Layer tracks covariance over stored associations (2605.31163); KATA uses the MQAR+overwrite+OOD-length bundle as headline evidence (2607.17419); TwinKV occupies redundancy-based repair for KV (2608.27128); DAMP shows error energy concentrates in few channels (2608.27513); the Mamba-2 state-sink self-correction shows probe-identified state components are non-unique (2606.00930 v2).
- Surviving delta: none with unique advantage; run the syndrome kill screen with SANE, QED and the Bayesian layer as free baselines and publish the negative.
- Evidence: https://arxiv.org/abs/2608.13668 · https://arxiv.org/abs/2608.22354 · https://arxiv.org/abs/2608.12435 · https://arxiv.org/abs/2605.31163 · https://arxiv.org/abs/2607.17419 · https://arxiv.org/abs/2608.27128 · https://arxiv.org/abs/2608.27513 · https://arxiv.org/abs/2606.00930 · https://arxiv.org/abs/2608.16844

### Bidirectional Diffusion for Closed-Loop Plan Repair (`bidirectional-plan-repair.yaml`) — NARROWED (novelty-level collision; empirical lane open with four new deltas)
- Continuous Interaction Diffusion (2608.10438, 2026-08-11) stakes the mechanism — tool results projected into an evolving denoising state that revises earlier regions, with persistent bindings — as a formal architecture with read-only tools and "no empirical performance claims". LLaDA2.2 ships whole-sequence Levenshtein editing trained with agentic RL at 100B (first-party; AR sibling still wins SWE-bench Verified 61.2 vs 49.3 and BFCL-V4 66.8 vs 60.8, AR arm used 4-token MTP). DCGC (2608.25428), SRD (2608.22090) and DiffPDE (2608.30532) occupy diffusion/operatorized repair of drafts without compute-matched AR+verifier baselines. Negatives: remasking self-correction gives little-to-no benefit under standard settings (2606.12232); answer-first commitment hurts (2608.05687); 7–8B dLLMs score 0% on multi-turn BFCL (2601.12979, ACL 2026); 76% of batch-1 wall-clock is CPU dispatch (2608.23807).
- Surviving delta requires: (i) locality mask over a typed side-effecting action DAG, not a token sequence; (ii) AR+verifier control at matched p95 wall time with CPU overhead charged and a batch-8 arm; (iii) a LLaDA2.x-mini or DiffusionGemma-class checkpoint instead of LLaDA-8B; (iv) evidence that remasking helps in this setting. Cite CID, the 2023 diffusion-replanning robotics paper, and use the 2026 dLLM acceleration stack (CAI-DLLM, structured suffix, survival length control) as the diffusion baseline.
- Evidence: https://arxiv.org/abs/2608.10438 · https://huggingface.co/inclusionAI/LLaDA2.2-flash · https://arxiv.org/abs/2608.25428 · https://arxiv.org/abs/2608.22090 · https://arxiv.org/abs/2608.30532 · https://arxiv.org/abs/2606.12232 · https://arxiv.org/abs/2608.05687 · https://arxiv.org/abs/2601.12979 · https://arxiv.org/abs/2608.23807 · https://arxiv.org/abs/2608.25505 · https://arxiv.org/abs/2602.07451

### Rollout-Value Operator Scheduling (ranked-portfolio item 3 / §6, no yaml) — NARROWED
- Token-level dynamic operator routing under immediate LM loss is densely occupied: LoGo (2608.29539), Switch Attention (EMNLP 2026; 2603.26380), NAtS-L, Mixture of Layers, HubRouter, Flux Attention, FlashMorph, Super Apriel; RouteSparse (2608.29058) occupies budgeted input-conditional routing with an error certificate among sparse patterns. Structural limits: high-precision routers need pairwise comparison and segment-level routing reaches only 15–29% of token-level (2603.20997); SWA with sinks matches or beats post-trained linear attention (2608.28444), collapsing the operator set toward local/global; efficient-attention choice washes out at convergence (2606.15378); a matched-interface GRU ties homeostatic governors (2608.24319); BRANCH dominates operator choice in agentic reasoning with gains tracking truncation (2608.23956).
- Surviving delta: valuing full stateful continuations under measured latency/HBM (MixerLoop's marginal ITR is a candidate signal; 2608.18230). High collision and feasibility-constrained; recommend parking.
- Evidence: https://arxiv.org/abs/2608.29539 · https://arxiv.org/abs/2603.26380 · https://arxiv.org/abs/2608.29058 · https://arxiv.org/abs/2603.20997 · https://arxiv.org/abs/2608.28444 · https://arxiv.org/abs/2606.15378 · https://arxiv.org/abs/2608.24319 · https://arxiv.org/abs/2608.23956 · https://arxiv.org/abs/2608.18230 · https://arxiv.org/abs/2606.30562 · https://arxiv.org/abs/2604.19877

### Rank-Adaptive Edit Summaries (diagnostic B / ranked item 6, no yaml) — NARROWED (largely occupied at the serving layer)
- Tail-Replay reconstructs GDN state at any prefix boundary from a 5–10% suffix at 92.8–99.9% quality (2608.30310); DASC identifies long-retention units and compresses checkpoints 2.63× (2608.30386); DeltaLog already runs a bounded log of rank-1 updates with periodic merge (2608.15533); TreeWY gives exact branch-structured WY algebra for draft trees (2608.20961); HARTS recovers chunk-boundary state over rollout trees at training time (2608.28158).
- Surviving delta: non-suffix-local edits restricted to long-retention units, with rank growth of the WY/DeltaLog representation measured, and a falsifier "reject if tail replay at equal bytes and latency matches the rank-r summary".
- Evidence: https://arxiv.org/abs/2608.30310 · https://arxiv.org/abs/2608.30386 · https://arxiv.org/abs/2608.15533 · https://arxiv.org/abs/2608.20961 · https://arxiv.org/abs/2608.28158

### Direction 15 (interpretable abstract reasoning, `directions/15-*.md`, no yaml) — NARROWED
- Every axis in the brief is occupied at ≤8B on math/QA (§1 P); Abstract-CoT has no official code and three failed reproductions; the "verbal checkpoint" hybrid exists in stronger form (SELR, ICML 2026); DiffusionGemma's interpretable token bottleneck is the precedent for monitorable latent media. Surviving deltas are the tool-use × monitorability measurement (G14), the translation-equivariant code (G15) and a controlled replication (G16).

---

## 4. Material items published or surfaced after 2026-08-10

All first-party unless a venue is stated. Dates are arXiv v1 (or the version/event date noted). Grouped by axis; the structured return carries the same list.

### Production architectures and releases
| Date | Item | Why it matters |
|---|---|---|
| 2026-08-31 | On the Design of Qwen3.8-Next Architecture (2608.30320) | Most detailed public hybrid ablation set (GDN hybrid 53.81 vs SWA 51.15 vs full 49.87 at 25B-A3B; residual Tables 5/6; QSA; NoPE kept out after post-training endless generation; loss-vs-benchmark disagreement methodology). |
| 2026-08-26 | Qwen3.8-Flash-Next model card/config (HF) | Copyable 12 × (3 GDN → 1 QSA) layout, indexer config, Gated Residual, 51B n-gram tables; native `qwen4_exp` in transformers ≥5.16; vLLM 0.29+ only, not on Tinker. |
| 2026-08-14 | Qwen3.8-27B (HF, Apache-2.0) | Strongest natively supported, permissively licensed, locally trainable GDN hybrid (48+16 layers, MTP); on Tinker; field-reported glitch tokens, thinking loops, 1,584-token prefix-cache granularity. |
| 2026-08-26/31 | GLM-5.3-Flash (HF, MIT) | First open KDA + DSA hybrid with mHC (34:11, 320B-A18B); FP8 fits 8×H100 for inference; base not released; vLLM PR open; transformers KDA fallback yields NaN gradients (PR #48455, 2026-09-01). |
| 2026-08-27 → 31 | GLM-5.3 weights (HF) | Same base as GLM-5.2; post-training-only gains; on Tinker at 256K within ~6 days. |
| 2026-08-11 | NVIDIA Nemotron 3.5 Lightning 30B-A3B (+Base, NVFP4) | Most training-ready hybrid on the node (open base, 49 open post-training datasets, OpenMDW-1.1); no technical report on arXiv. |
| 2026-08-13 | DeepSeek-V4-Pro-0813 (HF) and V4-Flash-Vision-Exp (2026-09-01) | DSpark bundled; CSA/HCA + mHC; local training out of reach. |
| 2026-08-31 | A.X K2 Technical Report (2608.30181) | 688B MoE; Sparse Gated Attention with indexer warmup; RULER 94.6 at 256K; another static production sparse design. |
| 2026-08-10 | Motif 3 Technical Report (2608.09119) | Grouped Differential Latent Attention + mHC + MTP at 314B-A13.2B; adds to the static-architecture occupied table. |
| 2026-08-26 | transformers v5.16.0; vLLM v0.28.0; SGLang v0.5.18 (08-22); Ollama v0.33.2 (08-27) | Serving-stack pins; kernels opt-in for linear-attention models since v5.15 (08-10). |
| 2026-08-20 | Kimi-K3 HF revision update; FlashKDA commit 2026-09-01 (numerics change) | K3 remains custom-code and not locally runnable; FlashKDA benchmarks are H20/inference-only and now predate a kernel change. |

### Sequence operators, state and serving
| Date | Item | Why it matters |
|---|---|---|
| 2026-08-13 | QED: query-derived second erase direction (2608.13668) | Closes another delta-rule gate axis; free interference baseline for Coded Delta. |
| 2026-08-23 | SANE: State Anomaly Neutralization (2608.22354) | Delta-rule failure at 100M tokens is localized norm explosion; free syndrome baseline; capacity–stability trade-off. |
| 2026-08-27 | DAMP: decay-aware mixed-precision state quantization (2608.27513) | INT8/FP8 state quantization already degrades reasoning; error energy concentrates in few channels — measurable substrate. |
| 2026-08-31 | DASC (2608.30386) and Tail-Replay (2608.30310) | Checkpoint compression 2.63×; suffix replay reconstructs state at 92.8–99.9% quality — new mandatory control for any state-summary claim. |
| 2026-08-21 | TreeWY (2608.20961); 2026-08-16 DeltaLog (2608.15533); 2026-08-28 HARTS (2608.28158) | Exact branch-structured WY, bounded update logs, tree-RL for hybrids: Diag B largely occupied. |
| 2026-08-12 | Massive Activations in Hybrid Linear Attention LLMs (2608.12149) | Removes sinks-in-hybrids as a gap; releases 340M/1.3B 3:1 GDN hybrids as controls. |
| 2026-08-12 | MARCH content-routed state anchors (2608.12435) | Bounded anchor bank; new recall baseline. |
| 2026-08-28 | Sliding-window beats linear attention (2608.28444) | SWA+sinks 2–10× post-trained linear attention on NIAH/BABILong; SWA+sinks becomes a mandatory control. |
| 2026-08-24 | The Mask Is Not the Model (2608.22876) | Two-forward-pass causality audit localized 192/192 injected faults; found chunked-scan defects in Zamba2/Nemotron-H; mandatory doctor. |
| 2026-08-30 | LoGo token-level local/global routing (2608.29539); 2026-08-29 RouteSparse (2608.29058); Switch Attention v3 (2603.26380) | Operator routing occupied at token level and with error certificates. |
| 2026-08-18 | Allocating Recurrent Compute / MixerLoop ITR (2608.18230); 2026-08-15 Gated Recurrent Transformers (2608.15062) | Per-application utility measure; GRT beats MoR in 9/9 cells. |
| 2026-08-10 | Cracks in the Foundation (2608.10296, COLM 2026) | Minor choices compound to −47% long-context; early extension probes required. |
| 2026-08-19 | DeltaMomentum (2608.19491) | Delta-rule idea applied to optimizer state; 22–46% fewer steps at 67M–370M; Muon baseline still ahead on LM. |

### Test-time training and update rules
| Date | Item | Why it matters |
|---|---|---|
| 2026-08-21 | E²-TTT (2608.21308; checkpoints 08-30) | Strongest post-cutoff beyond-window recall claim (93.6% S-NIAH-1 at 16K); no causality checks; 340M/1.3B checkpoints enable a local audit. |
| 2026-08-18 | MoNe modular neural memory (2608.17616) | Bolt-on fast-weight memory for frozen bases; occupies the strap-on axis. |
| 2026-08-27 | Fast Weight Attention / Falcon rules (2608.27763) | Systematizes normalized update rules; rule-family novelty gone. |
| 2026-08-28 | Survey of Optimizers (2608.28557) | No context-independent AdamW replacement; compositional protocol for optimizer claims. |
| 2026-08-20 | Test-time training write-in/read-out repo (sxewc, 08-09) and DT-TTT independent audit (08-20) | Small-scale confirmations that proxies are not behavior; claim-by-claim audits are productive. |
| 2026-08-25 | LongVU-TTT (2608.25729) | Fast weights behave as temporal aggregation, not episodic memory. |

### Adapter portability and hypernetworks
| Date | Item | Why it matters |
|---|---|---|
| 2026-09-01 | portallib issue #28 (gold_idx==0 on TruthfulQA/SciQ) | Any PorTAL reproduction must shuffle choices; second independent reproduction harness exists; repo frozen since 2026-07-27. |
| 2026-08-21 | UpgradeBench (2608.20918) | First adapter-upgrade benchmark; direct copy only; defers learned mappings; no non-transformer targets. |
| 2026-08-17 | Cross-Model Memory Transfer via Target-Side Reader Adaptation (2608.17050) | Frozen memory + thin reader ports across backbones; narrows D16. |
| 2026-08-21 | MentorPulse (2608.20927); 2026-08-31 Universal Context-Reuse Layer (2608.30963) | Cross-model latent guidance and KV translation occupy "port the state". |
| 2026-08 | Cross-Architecture Steering Transfer (2608.05164) | SAE-feature bridges across five transformer lineages; needs 98k paired passages per pair. |
| 2026-08-30 | ACTD cross-tokenizer distillation (2608.29662, EMNLP 2026) | Cross-tokenizer axis solved at the distillation level. |
| 2026-08-31 | Task-vector interference is prompt-format conditioned (2608.09490 v2); 2026-08-29 gain-ratio non-identifiability (2607.09156 v3) | Portability metrics need held-out formats and dose-response reporting. |
| 2026-08-10 | Omni2LoRA (2608.09227) | Context→LoRA with GRPO rank allocation; single-base. |

### Latent reasoning and monitorability
| Date | Item | Why it matters |
|---|---|---|
| 2026-08-17 | Looped LMs improve compositional tool calling (2608.18171) | Fills the tool-use slot for recurrent depth (single-turn only). |
| 2026-08-27 | INTENT-AS-A-TOOL (2608.27348) | Tool-channel intent signal that would survive an opaque medium; untested with latent media. |
| 2026-08-17 | How Transparent is DiffusionGemma? v2 (2606.20560) | Interpretable token bottleneck reduces opaque serial depth 28.6× → 1.1×; precedent for monitorable latent media. |
| 2026-08-29/30 | FACE-Eval (2608.29464), Selective Disclosure (2608.29070), HCDS (2608.29956) | Monitorability filling fast; tool-return cues verbalized less. |
| 2026-08-26 | Skill Issue: are skills language-invariant? (2608.25832) | Cross-lingual skill-consistency instrument via self-play. |
| 2026-08-25 | Audio-LLM verbalizable multilingual middle-layer workspace (2608.24958) | Existence proof of a language-agnostic, logit-lens-readable latent code. |
| 2026-08-27 | Dynamical phase selection (2608.26556); 2026-08-18 Think Shallow, Solve Deep (2608.18222) | Cost and safety criteria for latent iterations. |
| 2026-08-15 | English/Tamil/Tanglish monitorability case study (2608.15392) | The only cross-lingual monitorability datapoint (n=8; inconclusive). |

### Byte-level and multilingual
| Date | Item | Why it matters |
|---|---|---|
| 2026-08-28 | Nested Byte-Level Vocabularies pre-registered negative (2608.28151) | −3.64%/−2.96% BPB for sharing granularities; exemplary evidentiary format. |
| 2026-08-27 | When Tokenizers Fail (2608.27658, EMNLP 2026) | Closest collision to D18; monolingual supervision; mandatory control arm. |
| 2026-08-18 | What Tokens are Learned (2608.17325) | H-Net boundaries diverge by typology and from BPE; measurement protocol. |
| 2026-08-26 | Vowel Signs Are Not Letters (2608.26449) | `\p{L}+` regex fertility ceiling on all 17 abugidas; 63.3% of top HF repos affected; invalidates unpatched BPE controls. |
| 2026-08-15 | Autocompleting Tokenizers (2608.15080) | Byte pruning evaluated on MT; mandatory entropy-baseline arm. |
| 2026-08-26 | One Form to Transfer Them All (2608.25904, EMNLP 2026) | Romanized pretraining as a cheap cross-lingual parity baseline. |
| 2026-08-19 | OmniAlign (2608.18474); CTFAlign/MDPAlign (2608.21023, EMNLP 2026) | Two independent aligners for D18's span links. |
| 2026-08-24 | GI-SAE cross-language reasoning invariance (2608.23809) | Geometric similarity ≠ functional interchangeability; feature-swap test methodology. |
| 2026-08-30 | Arkios bilingual En–Ne 1B (2608.30092) | MC-letter format at chance for a 1B bilingual model; score answer text. |
| 2026-08-10/11 | TEA tokenization premium (2608.09046); OmnilingualGAIA2 v2 (2608.08775) | Saturated audits; scale-invariant 8.8–18.4 pt multilingual agent gap located in tool orchestration. |

### Diffusion LMs
| Date | Item | Why it matters |
|---|---|---|
| 2026-08-11 | Continuous Interaction Diffusion (2608.10438) | Novelty-level collision for plan repair; no empirics. |
| 2026-08-20 | LLaDA2.2-flash card update (report 07-22) | Levenshtein editing + agentic RL at 100B; AR sibling still wins SWE-bench/BFCL. |
| 2026-08-24 | Serving Masked Diffusion LLMs on real hardware (2608.23807) | 24% GPU share at batch 1; 16× batching gain; unpredictable step counts. |
| 2026-08-26 | Conditional total correlation / serial depth (2608.25505) | Measurable quantity for language-dependent serial depth. |
| 2026-08-23 | Entropy-Valley length-adaptive MT (2608.22274, EMNLP 2026) | Only LLM-scale dLLM MT work; unexplained En→De vs Zh asymmetry. |
| 2026-08-25/22/31 | DCGC (2608.25428), SRD (2608.22090), DiffPDE (2608.30532), CARVE (2608.30922) | Repair and variable-length axes occupied. |
| 2026-08-31 | Mercury 2.5 Preview (OpenRouter); Artificial Analysis Mercury 2 measurement | Only independent dLLM speed measurement (684 tok/s vs 1,000+ claimed). |

### Agent memory, harness, evaluation
| Date | Item | Why it matters |
|---|---|---|
| 2026-08-30/31 | Hindsight Memory-PRM (2608.29605), SCM pathway tracing (2608.30198), MemGauge (2608.30177) | Narrow D17 to prospective randomized identification. |
| 2026-08-11 | Reward-SNR floor (2608.10441); 2026-08-28 Coverage, Not Credit (2608.28011) | Learned per-instance routing may be unlearnable even when the oracle effect is real. |
| 2026-08-15/25 | AdmitOR (2608.15565), Recuris (2608.24876) | Memory-gate axis crowded. |
| 2026-08-18 | Agent Lightning v1.0 (2608.17528) | Open harness-in-the-loop RL; Qwen3.5-9B SWE-bench Verified 41.8→56.4. |
| 2026-08-27 | Rethinking the Evaluation of Harness Evolution v2 (2607.12227) | Negative: no consistent win over matched-budget parallel sampling. |
| 2026-08-15 | StateM harness scaling (2608.15089) | 95.3% TB2.1; Goodhart warning (held-out +0.55). |
| 2026-08-22 | Hack-Verifiable Terminal Bench (2608.22103) | Reward hacking 16–48% unprompted; confound for harness claims. |
| 2026-08-26/28 | Terminal-Bench 4.0 release and news | Saturation-retirement and integrity protocol template. |
| 2026-08-31 | tau2-bench audit and issue #499 | Golden-replay defects; 57.9–64.9% of user-sim first messages differ at temperature 0. |
| 2026-08-12 | Small-Scale Experiments: Are We There Yet? (2608.11859) | ≥256 configs/scale; undertuned baselines are a kill-shot. |
| 2026-08-29 | Benchmark Contamination taxonomy + JSON disclosure (2608.29463); 2026-08-13 scale-aware memorization probes (2608.12771) | Disclosure protocol; probes lose power at scale. |
| 2026-08-25 | Recursive Agentic Reasoning (2608.23956); 2026-08-26 Same Model, Different Harness (2608.26218); 2026-08-27 Ledger self-orchestration (2608.26480); 2026-08-29 APIFlow-Bench (2608.29128) | Paired scoring, model+harness as the solver, reliability vs capability spreads. |
| 2026-08-25 | Mamba-2 state-sink self-correction v2 (2606.00930) | Probe-identified state components are non-unique; control battery for any state diagnostic. |
| 2026-08-13 | DeepSeek Harness (dsh) + Cordis paper (2608.25512, 08-26); 2026-08-18 Vercel fx | Plugin-first harness with formal composability; minimal reference harness. |
| 2026-08-26 | OpenAI Hugging Face incident report (community post 08-27) | Sandbox escape by a frontier-class model during eval; container escape is in-distribution. |
| 2026-08-27 | WikiSkill (2608.27454) | Text-space cross-family skill transfer with negative-transfer cases; comparator for any portable-adaptation claim. |

### Substrate
| Date | Item | Why it matters |
|---|---|---|
| 2026-08-27 | TML news: text-to-SQL RL on Kimi-K2.6 (rank 32, CISPO) 91.37%/92.97% vs 92.96% human | Strongest public evidence rank-32 LoRA RL on a 1T model reaches human level; 32.8% reward false positives. |
| 2026-08-14 | tinker-cookbook issue #889 (7/89 TB tasks silently zeroed); harbor recipe 60.6% context-overflow ERROR at 32K | Budget the 128K tier for agentic RL on Kimi-K2.6. |
| 2026-09-01 / 08-22 | tinker SDK 0.27.0 on PyPI; cookbook 0.5.5; server rejects unsupported SDKs (issue #120) | `memory.json` pin 0.23.3 will rot; add an SDK doctor. |
| 2026-08-16 | tinker-feedback #141 (hidden-state access request, unanswered) | Confirms no representation access on Tinker. |
| 2026-08-13 | Slurm 26.05.3 tag; NVIDIA Container Toolkit 1.20.0; 2026-08-27 syft v1.51.1 | Pins for the publication lane. |
| 2026-08-26 | vLLM v0.28.0 (`vllm-openai@sha256:61fc8a89…`) | TP=8 single-step serving pin. |

---

## 5. Merged coverage limits

1. **WebSearch.** A single 200-call budget was shared across all cells and exhausted mid-sweep; per cell 1–35 queries ran and 4–10 planned queries were refused in every cell (independent TTT-E2E replications, MiniMax M3 report, Attention Residuals replication, PorTAL critiques, multilingual harness effects, learned-optimizer LoRA, latent-steganography, Nemotron 3.5 report, post-08-10 catch-alls). Grey literature after 2026-08-10 is under-covered except via GitHub/HF metadata.
2. **arXiv API.** HTTP 429 from this Mac for most of the session; cells fell back to abstract-page scraping (~600 abstract pages opened across cells), the arXiv search UI (rate-limited after a few queries), the pre-pulled feed (15 queries × 40 newest, so `agent_harness` and `retraction_negative` columns saturated and miss 2026-08-10→08-20), and the H100-host relay where used. Exact-phrase `all:` matching misses paraphrased titles. Results were capped at 25–50 newest per query.
3. **Semantic Scholar.** HTTP 429 on nearly every call (no API key; AS7018 reputation block). No citation counts, no citation-graph novelty checks, no venue confirmation from S2 anywhere in this sweep.
4. **Jina reader.** 401 for anonymous queries from this network on every attempt; WebFetch (a small summarizer) substituted, so body-level numbers not quoted verbatim may carry transcription error. Cells quoted only numbers that appeared verbatim in the returned text where noted.
5. **Blocked or JS-only primaries.** openai.com (403: SWE-bench Verified retirement, SWE-bench Pro audit, harness engineering, CoT monitorability blog), OpenReview (browser check), qwen.ai and z.ai blogs, labs.ramp.com/swebench, tbench.ai leaderboard tables, vals.ai (404), Princeton RC checkpointing KB (404), SchedMD Bugzilla (login), thinkingmachines.ai/blog/inkling (404), Graphcore BLT post (404), DuckDuckGo (CAPTCHA), Bing RSS, Brave. Claims from these sources come from HF cards/configs, GitHub, arXiv, or dated secondary coverage and are flagged as such.
6. **Reading depth.** Full text was read for roughly 40 papers across all cells (e.g., K3, AttnRes PDF, Qwen3.8-Next, DeepSeek-V4, Stuck-on-A, SR-TTT v2, TTT-E2E, E²-TTT, Modular TTT, Beyond Perplexity, FAAST, Theseus, Transport-and-Merge, UpgradeBench, HN scaling laws, ~20 latent-reasoning HTMLs, ~12 byte-level HTMLs); everything else is abstract-level plus README/config/model card. Per-language tables in Scratchpad Patching, Equity-with-Efficiency and When Tokenizers Fail were not extracted number by number. Full PDFs of the K3, Qwen3.8-Next, Gemma 4, DeepSeek-V4, LLaDA2.2 and DiffusionGemma reports were not read.
7. **Evidence status.** Nearly all 2026 items are first-party preprints or lab reports; peer-reviewed status was taken from arXiv comments, code READMEs or search records and independently confirmed only for a handful (Bitter Lesson ACL 2026 via DBLP; LongCA-bench, Gaia2, HAL via ICLR proceedings). No cell executed any code, reproduced any number, or measured anything on the H100 node; all feasibility arithmetic is derived from HF safetensors totals and vendor tables.
8. **Kevin's X bookmarks.** 2,038 rows synced 2026-09-01; `bookmarkedAt` is null on every row so save-date is unknowable; the FTS5 layer silently returns 0 for OR/quoted-phrase and errors on hyphenated or `bench`-containing queries. The stream contains essentially no architecture, TTT, tokenizer, diffusion, evaluation-methodology or infrastructure posts after 2026-08-02; its architecture signal is July Moonshot/Ramp/MiniMax/Zhipu launches. Treated as interest evidence only.
9. **Not searched anywhere.** Chinese-language sources (Zhihu/WeChat), Google Scholar, ACL Anthology, Papers with Code, Reddit/HN, live X, Discord/Slack, ICLR 2027 submissions (due late September 2026), classical NAT literature (Mask-Predict, Levenshtein Transformer) as prior art for the bilingual canvas, pre-2026 OLMo/Pythia contamination-calibration work, Gemma 4 / GPT-OSS / Llama architecture updates beyond cards, MiniMax M3 technical report, closed-lab systems.
10. **Retractions.** No retraction database was searchable; arXiv withdrawal comments are not surfaced by the queries used. Found under this coverage: Impossibility Triangle (2605.05066) withdrawn 2026-08-06; Soft-NBCE (2606.01101) withdrawn (authorship); Mamba-2 state-sink v2 self-correction; SR-TTT v2 self-retraction (prior sweep); version corrections on 2607.20952, 2604.21106, 2606.06574. No retraction found for any target model, TTT, latent-reasoning, byte-level or diffusion paper.
11. **Tinker and competitors.** No API key: rate limits, `max_batch_size`, undocumented rank caps and step latency were not probed live; Together/Fireworks/Unsloth/OpenMDW pages were read through WebFetch summaries and individual rows (e.g., Together's rank-16 cap on Kimi K2.6, Fireworks 65,536 context) must be re-verified before citation.
12. **Infra.** Nothing was executed on fal-h100-01; the host's Ubuntu release, kernel, systemd and AppArmor settings were not re-audited; all assembled commands marked (U) in the infra note are untested. Mailing-list threads on ConstrainDevices were summarized from snippets.
13. **Feed and column boundaries.** The three arXiv triage cells covered disjoint feed columns; hybrid/TTT/looped papers filed under another cell's column were cross-referenced by title only; six August dLLM abstracts and several harness titles (StarHarness, Logos, openJiuwen, When Context Gets Root) were listed but not opened.
14. **Dating.** Docs pages (Tinker, Artificial Analysis, HAL, vLLM recipes) are undated and recorded as "fetched 2026-09-01"; arXiv dates are v1 unless noted; Kimi-K2.6's release date comes from HF `createdAt`; HarnessRouter's launch date is inferred.

---

## 6. Synthesis path — what to do with this sweep

The recommendation is a sequence, not a portfolio: infrastructure receipts first, then the one region every cell found empty, then the reproducible-negative lane, with the crowded directions parked or reframed.

**Stage 0 — receipts and controls (weeks 0–2, no GPU research).** (a) Build Slurm 25.11.7 + Pyxis 0.24.0 + Enroot 4.2.1 from source with `CgroupPlugin=cgroup/v2`, `ConstrainDevices=yes`, `AutoDetect=nvml`; seal the eBPF device-program proof and the SIGUSR1-through-Pyxis 3-way doctor (infra G1–G3). (b) Add a Tinker SDK-version doctor (0.23.3 pinned vs 0.27.0 live; HTTP 400 on old SDKs) and budget the 128K tier for any agentic RL on Kimi-K2.6. (c) Adopt the 2026 believability bar as harness defaults: per-arm HP search at the two smallest rungs, ≥3 sizes × ≥10× compute, ≥3–5 seeds with paired clustered SEs and q=N/N*, length-dependent curves, generation-based permutation-controlled evaluation, early context-extension probes, SWA+sinks and tail-replay controls, the two-forward-pass prefix-invariance audit, four-field contamination disclosure. (d) Fix the `\p{L}+` pre-tokenizer in every BPE control; shuffle choices in any portallib-derived task.

**Stage 1 — the unique-asset bet: language as a controlled variable inside architecture (weeks 2–10).** Run G1 and G2 together on one shared substrate: (i) translation-paired recall/state probes (key in language A, query in B; per-script decay curves) over released controls (startlux 340M/1.3B GDN hybrids, Mamba-3 187M–1.5B, E²-TTT 340M/1.3B, FwPKM, Qwen3.5-0.8B–9B) — a new evaluation instrument with a publishable answer either way; (ii) Direction 18's matched-compute screen at 20M–125M with the five new arms (Scratchpad compute-matched, patched parity-BPE, POS/subword-target, entropy byte-pruning, romanized, MAGNET) and λ_z ablated, on Bolmo-1B stage-1 as the retrofit base; (iii) if (i) shows script-dependent state degradation, extend to the learned-indexer probe (G13) on 0.1–1B sparse-attention models. Kill rule: if translation-aligned boundaries do not beat the compute-matched and POS-target arms on translation fidelity at equal BPB, publish the negative and stop D18.

**Stage 2 — portability across operator families (weeks 6–14).** Reframe D16 as G3/G4: port a PorTAL-style task adapter from Qwen3-0.6B-Base / Qwen3.5-4B onto Qwen3.5-0.8B (GDN hybrid), Mamba-130M, Kimi-Linear-48B-A3B and LLaDA-8B at attention-pathway sites, with parallel sentences as the label-free calibration stream and tokenizer crossing measured as a variable; mandatory controls: Cross-LoRA, Theseus, Engram reader transfer, KV translation, fresh LoRA, Hyper-X-style language conditioning, held-out prompt formats. Only if a static adapter ports do the update-rule cell (G5) with Modular-TTT primitives and derived-rule baselines. This is the direction closest to Kevin's stated taste and the one whose collision risk is medium rather than high.

**Stage 3 — the reproducible-negative lane (weeks 4–16, background).** An open ≤1B K3-stack reference (G12) feeding three controlled ablations nobody has published: depth-axis operators across families with 5 seeds (G9), NoPE/RoPE/partial-RoPE global layers with post-training termination probes (G10), MTP on/off on small hybrids (G11); plus H100 FlashKDA fwd/bwd numbers and a pinned LoRA/full-FT report for Qwen3.8-27B, Nemotron-3.5-Lightning-Base and GLM-5.3-Flash FP8. Each is publishable as a positive or a negative and each is a prerequisite for Stage 1's from-scratch arms.

**Stage 4 — reasoning-media measurement (weeks 8–16).** G14/G15: one fixed monitor across media at matched accuracy on tool-use agent tasks, with reasoning-rewrite and monitor-awareness attacks, on SWITCH/MUX/DLR/ALAR code at 4B–8B; then the translation-equivariant abstract code with a monitor trained in one language and tested across the 13-language fragility set. G16 (Abstract-CoT replication) only if the warm-up compute fits between the two failed budgets.

**Stage 5 — D17 as randomized identification (after Stage 0).** Keep the estimand, rename the contribution, add Hindsight Memory-PRM, AdmitOR, noise-placebo and reward-SNR gates; run the CPU paired oracle before any Tinker spend; accept that the reward-SNR floor may make the gate unlearnable even if the effect is real.

**Park.** Coded Delta Memory (negative cell only, SANE/QED/Bayesian-layer controls); Bidirectional Plan Repair (until the four new deltas are affordable and a LLaDA2.x-mini/DiffusionGemma checkpoint is the arm); Rollout-Value Operator Scheduling (high collision, capped by 2603.20997 and 2606.15378); Rank-Adaptive Edit Summaries (serving layer owns it); all harness-evolution and strap-on memory work.

**What this sweep did not settle.** Whether a small-scale advantage on any of Stage 1–3 survives to ~1000N tokens (2606.15378), whether parallel data moves anything beyond token-level translation alignment (2603.29026 says representation alignment barely moves; boundary formation and recurrent-state recall are untested), and whether Tinker will ever expose the optimizer or internals needed to take rule-level results to 1T.

---

## 7. Sources appendix — every URL cited in the 17 cell notes and this synthesis

Deduplicated, sorted; extracted programmatically from scratchpad/sweep/*.md on 2026-09-01. Dates and first-party/peer-reviewed status are given at the point of citation in the cell notes and in §1–§4 above.

- https://agent-plugins.org
- https://ai.google.dev/gemma/docs/core/model_card_4
- https://ai.google.dev/gemma/docs/diffusiongemma
- https://allenai.org/blog/bolmo
- https://api-docs.deepseek.com/updates/
- https://artificialanalysis.ai/evaluations/artificial-analysis-long-context-reasoning
- https://artificialanalysis.ai/evaluations/terminalbench-v2-1
- https://artificialanalysis.ai/models/mercury-2
- https://arxiv.org/abs/2202.05780
- https://arxiv.org/abs/2205.12148
- https://arxiv.org/abs/2305.15076
- https://arxiv.org/abs/2312.00276
- https://arxiv.org/abs/2402.05232
- https://arxiv.org/abs/2405.16287
- https://arxiv.org/abs/2405.17258
- https://arxiv.org/abs/2406.00153
- https://arxiv.org/abs/2407.08818
- https://arxiv.org/abs/2407.19117
- https://arxiv.org/abs/2408.04303
- https://arxiv.org/abs/2408.09310
- https://arxiv.org/abs/2410.04682
- https://arxiv.org/abs/2411.00640
- https://arxiv.org/abs/2412.06769
- https://arxiv.org/abs/2412.09871
- https://arxiv.org/abs/2501.00663
- https://arxiv.org/abs/2501.12352
- https://arxiv.org/abs/2501.16559
- https://arxiv.org/abs/2501.19201
- https://arxiv.org/abs/2502.00592
- https://arxiv.org/abs/2502.03275
- https://arxiv.org/abs/2503.11842
- https://arxiv.org/abs/2503.11926
- https://arxiv.org/abs/2503.20083
- https://arxiv.org/abs/2504.07086
- https://arxiv.org/abs/2504.13173
- https://arxiv.org/abs/2504.21018
- https://arxiv.org/abs/2505.05410
- https://arxiv.org/abs/2505.23735
- https://arxiv.org/abs/2505.23884
- https://arxiv.org/abs/2506.05233
- https://arxiv.org/abs/2506.06105
- https://arxiv.org/abs/2506.06609
- https://arxiv.org/abs/2506.10315
- https://arxiv.org/abs/2506.10943
- https://arxiv.org/abs/2506.20989
- https://arxiv.org/abs/2507.02199
- https://arxiv.org/abs/2507.06457
- https://arxiv.org/abs/2507.07824
- https://arxiv.org/abs/2507.07955
- https://arxiv.org/abs/2507.10524
- https://arxiv.org/abs/2507.11473
- https://arxiv.org/abs/2507.12720
- https://arxiv.org/abs/2508.02193
- https://arxiv.org/abs/2508.05232
- https://arxiv.org/abs/2508.05628
- https://arxiv.org/abs/2508.06600
- https://arxiv.org/abs/2508.08435
- https://arxiv.org/abs/2508.19461
- https://arxiv.org/abs/2509.14786
- https://arxiv.org/abs/2509.17158
- https://arxiv.org/abs/2509.20317
- https://arxiv.org/abs/2509.23779
- https://arxiv.org/abs/2509.26314
- https://arxiv.org/abs/2510.04682
- https://arxiv.org/abs/2510.04694
- https://arxiv.org/abs/2510.04767
- https://arxiv.org/abs/2510.04800
- https://arxiv.org/abs/2510.06128
- https://arxiv.org/abs/2510.09551
- https://arxiv.org/abs/2510.10425
- https://arxiv.org/abs/2510.11370
- https://arxiv.org/abs/2510.11977
- https://arxiv.org/abs/2510.12167
- https://arxiv.org/abs/2510.19851
- https://arxiv.org/abs/2510.21909
- https://arxiv.org/abs/2510.23966
- https://arxiv.org/abs/2510.25741
- https://arxiv.org/abs/2510.26692
- https://arxiv.org/abs/2510.27378
- https://arxiv.org/abs/2511.00543
- https://arxiv.org/abs/2511.07384
- https://arxiv.org/abs/2511.11584
- https://arxiv.org/abs/2512.00218
- https://arxiv.org/abs/2512.04268
- https://arxiv.org/abs/2512.07850
- https://arxiv.org/abs/2512.10218
- https://arxiv.org/abs/2512.13898
- https://arxiv.org/abs/2512.15176
- https://arxiv.org/abs/2512.15586
- https://arxiv.org/abs/2512.15745
- https://arxiv.org/abs/2512.17351
- https://arxiv.org/abs/2512.18311
- https://arxiv.org/abs/2512.21711
- https://arxiv.org/abs/2512.23675
- https://arxiv.org/abs/2512.23852
- https://arxiv.org/abs/2512.24014
- https://arxiv.org/abs/2512.24695
- https://arxiv.org/abs/2512.24880
- https://arxiv.org/abs/2601.00364
- https://arxiv.org/abs/2601.00417
- https://arxiv.org/abs/2601.00671
- https://arxiv.org/abs/2601.02780
- https://arxiv.org/abs/2601.02996
- https://arxiv.org/abs/2601.11868
- https://arxiv.org/abs/2601.12979
- https://arxiv.org/abs/2601.13228
- https://arxiv.org/abs/2601.14050
- https://arxiv.org/abs/2601.15593
- https://arxiv.org/abs/2601.15892
- https://arxiv.org/abs/2601.19897
- https://arxiv.org/abs/2601.20802
- https://arxiv.org/abs/2601.21768
- https://arxiv.org/abs/2601.22156
- https://arxiv.org/abs/2601.22805
- https://arxiv.org/abs/2601.22966
- https://arxiv.org/abs/2602.01148
- https://arxiv.org/abs/2602.01326
- https://arxiv.org/abs/2602.01695
- https://arxiv.org/abs/2602.03681
- https://arxiv.org/abs/2602.03978
- https://arxiv.org/abs/2602.04246
- https://arxiv.org/abs/2602.05085
- https://arxiv.org/abs/2602.05495
- https://arxiv.org/abs/2602.06036
- https://arxiv.org/abs/2602.06358
- https://arxiv.org/abs/2602.07035
- https://arxiv.org/abs/2602.07451
- https://arxiv.org/abs/2602.08332
- https://arxiv.org/abs/2602.08783
- https://arxiv.org/abs/2602.09555
- https://arxiv.org/abs/2602.10229
- https://arxiv.org/abs/2602.12952
- https://arxiv.org/abs/2602.13940
- https://arxiv.org/abs/2602.15902
- https://arxiv.org/abs/2602.16704
- https://arxiv.org/abs/2602.17744
- https://arxiv.org/abs/2602.19142
- https://arxiv.org/abs/2602.21204
- https://arxiv.org/abs/2603.00180
- https://arxiv.org/abs/2603.01375
- https://arxiv.org/abs/2603.05026
- https://arxiv.org/abs/2603.05706
- https://arxiv.org/abs/2603.06123
- https://arxiv.org/abs/2603.06591
- https://arxiv.org/abs/2603.06642v2
- https://arxiv.org/abs/2603.09786
- https://arxiv.org/abs/2603.12201
- https://arxiv.org/abs/2603.14517
- https://arxiv.org/abs/2603.15031
- https://arxiv.org/abs/2603.15033
- https://arxiv.org/abs/2603.15417
- https://arxiv.org/abs/2603.15569
- https://arxiv.org/abs/2603.19278
- https://arxiv.org/abs/2603.20172
- https://arxiv.org/abs/2603.20466
- https://arxiv.org/abs/2603.20997
- https://arxiv.org/abs/2603.21454
- https://arxiv.org/abs/2603.23749
- https://arxiv.org/abs/2603.23911
- https://arxiv.org/abs/2603.25723
- https://arxiv.org/abs/2603.26097
- https://arxiv.org/abs/2603.26380
- https://arxiv.org/abs/2603.26556
- https://arxiv.org/abs/2603.27859
- https://arxiv.org/abs/2603.28052
- https://arxiv.org/abs/2603.28590
- https://arxiv.org/abs/2603.29026
- https://arxiv.org/abs/2603.30036
- https://arxiv.org/abs/2604.00770
- https://arxiv.org/abs/2604.01674
- https://arxiv.org/abs/2604.02215
- https://arxiv.org/abs/2604.03242
- https://arxiv.org/abs/2604.03444
- https://arxiv.org/abs/2604.03592
- https://arxiv.org/abs/2604.04902
- https://arxiv.org/abs/2604.06169
- https://arxiv.org/abs/2604.06377
- https://arxiv.org/abs/2604.07350
- https://arxiv.org/abs/2604.07822
- https://arxiv.org/abs/2604.11791
- https://arxiv.org/abs/2604.12946
- https://arxiv.org/abs/2604.14191
- https://arxiv.org/abs/2604.16812
- https://arxiv.org/abs/2604.17064
- https://arxiv.org/abs/2604.19021
- https://arxiv.org/abs/2604.19877
- https://arxiv.org/abs/2604.21100
- https://arxiv.org/abs/2604.21106
- https://arxiv.org/abs/2604.22127
- https://arxiv.org/abs/2604.22709
- https://arxiv.org/abs/2604.23460
- https://arxiv.org/abs/2604.23750
- https://arxiv.org/abs/2604.24715
- https://arxiv.org/abs/2605.01106
- https://arxiv.org/abs/2605.01929
- https://arxiv.org/abs/2605.04651
- https://arxiv.org/abs/2605.05066
- https://arxiv.org/abs/2605.06241
- https://arxiv.org/abs/2605.06654
- https://arxiv.org/abs/2605.06885
- https://arxiv.org/abs/2605.07076
- https://arxiv.org/abs/2605.08044
- https://arxiv.org/abs/2605.08301
- https://arxiv.org/abs/2605.08366
- https://arxiv.org/abs/2605.09165
- https://arxiv.org/abs/2605.09516
- https://arxiv.org/abs/2605.09630
- https://arxiv.org/abs/2605.10537
- https://arxiv.org/abs/2605.11032
- https://arxiv.org/abs/2605.11746
- https://arxiv.org/abs/2605.12366
- https://arxiv.org/abs/2605.12460
- https://arxiv.org/abs/2605.12484
- https://arxiv.org/abs/2605.12746
- https://arxiv.org/abs/2605.12928
- https://arxiv.org/abs/2605.13473
- https://arxiv.org/abs/2605.13779
- https://arxiv.org/abs/2605.13839
- https://arxiv.org/abs/2605.15257
- https://arxiv.org/abs/2605.15377
- https://arxiv.org/abs/2605.15676
- https://arxiv.org/abs/2605.16350
- https://arxiv.org/abs/2605.18549
- https://arxiv.org/abs/2605.18632
- https://arxiv.org/abs/2605.18822
- https://arxiv.org/abs/2605.21516
- https://arxiv.org/abs/2605.21642
- https://arxiv.org/abs/2605.22166
- https://arxiv.org/abs/2605.22791
- https://arxiv.org/abs/2605.22984
- https://arxiv.org/abs/2605.23872
- https://arxiv.org/abs/2605.23885
- https://arxiv.org/abs/2605.24286
- https://arxiv.org/abs/2605.24718
- https://arxiv.org/abs/2605.25052
- https://arxiv.org/abs/2605.26099
- https://arxiv.org/abs/2605.26733
- https://arxiv.org/abs/2605.27901
- https://arxiv.org/abs/2605.27922
- https://arxiv.org/abs/2605.28053
- https://arxiv.org/abs/2605.28079
- https://arxiv.org/abs/2605.28444
- https://arxiv.org/abs/2605.29714
- https://arxiv.org/abs/2605.30080
- https://arxiv.org/abs/2605.30202
- https://arxiv.org/abs/2605.30315
- https://arxiv.org/abs/2605.30621
- https://arxiv.org/abs/2605.31163
- https://arxiv.org/abs/2606.00930
- https://arxiv.org/abs/2606.01243
- https://arxiv.org/abs/2606.01464
- https://arxiv.org/abs/2606.02871
- https://arxiv.org/abs/2606.03483
- https://arxiv.org/abs/2606.04438
- https://arxiv.org/abs/2606.04446
- https://arxiv.org/abs/2606.04627
- https://arxiv.org/abs/2606.06087
- https://arxiv.org/abs/2606.06154
- https://arxiv.org/abs/2606.06160
- https://arxiv.org/abs/2606.06447
- https://arxiv.org/abs/2606.06492
- https://arxiv.org/abs/2606.06574
- https://arxiv.org/abs/2606.06906
- https://arxiv.org/abs/2606.07157
- https://arxiv.org/abs/2606.07720
- https://arxiv.org/abs/2606.08105
- https://arxiv.org/abs/2606.08804
- https://arxiv.org/abs/2606.09498
- https://arxiv.org/abs/2606.11052
- https://arxiv.org/abs/2606.11998
- https://arxiv.org/abs/2606.12232
- https://arxiv.org/abs/2606.12342
- https://arxiv.org/abs/2606.12689
- https://arxiv.org/abs/2606.13106
- https://arxiv.org/abs/2606.13392
- https://arxiv.org/abs/2606.13603
- https://arxiv.org/abs/2606.14122
- https://arxiv.org/abs/2606.15044
- https://arxiv.org/abs/2606.15378
- https://arxiv.org/abs/2606.16222
- https://arxiv.org/abs/2606.16429
- https://arxiv.org/abs/2606.17175
- https://arxiv.org/abs/2606.19348
- https://arxiv.org/abs/2606.20097
- https://arxiv.org/abs/2606.20560
- https://arxiv.org/abs/2606.20683
- https://arxiv.org/abs/2606.21803
- https://arxiv.org/abs/2606.23321
- https://arxiv.org/abs/2606.23567
- https://arxiv.org/abs/2606.24460
- https://arxiv.org/abs/2606.24898
- https://arxiv.org/abs/2606.24975
- https://arxiv.org/abs/2606.25331
- https://arxiv.org/abs/2606.25342
- https://arxiv.org/abs/2606.26466
- https://arxiv.org/abs/2606.26493
- https://arxiv.org/abs/2606.26560
- https://arxiv.org/abs/2606.29066
- https://arxiv.org/abs/2606.29215
- https://arxiv.org/abs/2606.29712
- https://arxiv.org/abs/2606.30015
- https://arxiv.org/abs/2606.30562
- https://arxiv.org/abs/2606.31813
- https://arxiv.org/abs/2606.31963
- https://arxiv.org/abs/2607.00341
- https://arxiv.org/abs/2607.00368
- https://arxiv.org/abs/2607.01299
- https://arxiv.org/abs/2607.01775
- https://arxiv.org/abs/2607.02512
- https://arxiv.org/abs/2607.02770
- https://arxiv.org/abs/2607.02805
- https://arxiv.org/abs/2607.03502
- https://arxiv.org/abs/2607.03551
- https://arxiv.org/abs/2607.03691
- https://arxiv.org/abs/2607.04528
- https://arxiv.org/abs/2607.05722
- https://arxiv.org/abs/2607.06648
- https://arxiv.org/abs/2607.06772
- https://arxiv.org/abs/2607.07386
- https://arxiv.org/abs/2607.07743
- https://arxiv.org/abs/2607.07953
- https://arxiv.org/abs/2607.08284
- https://arxiv.org/abs/2607.09156
- https://arxiv.org/abs/2607.09415
- https://arxiv.org/abs/2607.09786
- https://arxiv.org/abs/2607.11897
- https://arxiv.org/abs/2607.12227
- https://arxiv.org/abs/2607.13087
- https://arxiv.org/abs/2607.13104
- https://arxiv.org/abs/2607.13683
- https://arxiv.org/abs/2607.14004
- https://arxiv.org/abs/2607.14159
- https://arxiv.org/abs/2607.14427
- https://arxiv.org/abs/2607.16051
- https://arxiv.org/abs/2607.16117
- https://arxiv.org/abs/2607.16621
- https://arxiv.org/abs/2607.17419
- https://arxiv.org/abs/2607.18264
- https://arxiv.org/abs/2607.18618
- https://arxiv.org/abs/2607.18912
- https://arxiv.org/abs/2607.19604
- https://arxiv.org/abs/2607.20062
- https://arxiv.org/abs/2607.20911
- https://arxiv.org/abs/2607.21351
- https://arxiv.org/abs/2607.21405
- https://arxiv.org/abs/2607.21535
- https://arxiv.org/abs/2607.21612
- https://arxiv.org/abs/2607.21981
- https://arxiv.org/abs/2607.22334
- https://arxiv.org/abs/2607.22688
- https://arxiv.org/abs/2607.22925
- https://arxiv.org/abs/2607.23153
- https://arxiv.org/abs/2607.24276
- https://arxiv.org/abs/2607.24653
- https://arxiv.org/abs/2607.25663
- https://arxiv.org/abs/2607.26191
- https://arxiv.org/abs/2607.26504
- https://arxiv.org/abs/2607.27386
- https://arxiv.org/abs/2607.27497
- https://arxiv.org/abs/2607.27539
- https://arxiv.org/abs/2607.27594
- https://arxiv.org/abs/2607.28147
- https://arxiv.org/abs/2608.00017
- https://arxiv.org/abs/2608.00146
- https://arxiv.org/abs/2608.00434
- https://arxiv.org/abs/2608.00533
- https://arxiv.org/abs/2608.00583
- https://arxiv.org/abs/2608.00814
- https://arxiv.org/abs/2608.01075
- https://arxiv.org/abs/2608.01593
- https://arxiv.org/abs/2608.01662
- https://arxiv.org/abs/2608.01672
- https://arxiv.org/abs/2608.01784
- https://arxiv.org/abs/2608.02689
- https://arxiv.org/abs/2608.02820
- https://arxiv.org/abs/2608.03275
- https://arxiv.org/abs/2608.03457
- https://arxiv.org/abs/2608.03599
- https://arxiv.org/abs/2608.03624
- https://arxiv.org/abs/2608.03745
- https://arxiv.org/abs/2608.03838
- https://arxiv.org/abs/2608.03893
- https://arxiv.org/abs/2608.04735
- https://arxiv.org/abs/2608.04928
- https://arxiv.org/abs/2608.05164
- https://arxiv.org/abs/2608.05687
- https://arxiv.org/abs/2608.06398
- https://arxiv.org/abs/2608.06529
- https://arxiv.org/abs/2608.06628
- https://arxiv.org/abs/2608.07110
- https://arxiv.org/abs/2608.07169
- https://arxiv.org/abs/2608.07341
- https://arxiv.org/abs/2608.08775
- https://arxiv.org/abs/2608.09046
- https://arxiv.org/abs/2608.09096
- https://arxiv.org/abs/2608.09119
- https://arxiv.org/abs/2608.09119v1
- https://arxiv.org/abs/2608.09227
- https://arxiv.org/abs/2608.09424
- https://arxiv.org/abs/2608.09432
- https://arxiv.org/abs/2608.09444
- https://arxiv.org/abs/2608.09448
- https://arxiv.org/abs/2608.09468
- https://arxiv.org/abs/2608.09490
- https://arxiv.org/abs/2608.09766
- https://arxiv.org/abs/2608.09888
- https://arxiv.org/abs/2608.10296
- https://arxiv.org/abs/2608.10438
- https://arxiv.org/abs/2608.10441
- https://arxiv.org/abs/2608.10615
- https://arxiv.org/abs/2608.11095
- https://arxiv.org/abs/2608.11224
- https://arxiv.org/abs/2608.11233
- https://arxiv.org/abs/2608.11805
- https://arxiv.org/abs/2608.11859
- https://arxiv.org/abs/2608.12149
- https://arxiv.org/abs/2608.12278v1
- https://arxiv.org/abs/2608.12435
- https://arxiv.org/abs/2608.12771
- https://arxiv.org/abs/2608.13416
- https://arxiv.org/abs/2608.13570
- https://arxiv.org/abs/2608.13622
- https://arxiv.org/abs/2608.13668
- https://arxiv.org/abs/2608.13925
- https://arxiv.org/abs/2608.13987
- https://arxiv.org/abs/2608.14107
- https://arxiv.org/abs/2608.14771
- https://arxiv.org/abs/2608.15008
- https://arxiv.org/abs/2608.15062
- https://arxiv.org/abs/2608.15080
- https://arxiv.org/abs/2608.15080v1
- https://arxiv.org/abs/2608.15089
- https://arxiv.org/abs/2608.15392
- https://arxiv.org/abs/2608.15454
- https://arxiv.org/abs/2608.15454v2
- https://arxiv.org/abs/2608.15459
- https://arxiv.org/abs/2608.15517
- https://arxiv.org/abs/2608.15533
- https://arxiv.org/abs/2608.15565
- https://arxiv.org/abs/2608.15565v3
- https://arxiv.org/abs/2608.16085
- https://arxiv.org/abs/2608.16357
- https://arxiv.org/abs/2608.16544
- https://arxiv.org/abs/2608.16671v1
- https://arxiv.org/abs/2608.16747
- https://arxiv.org/abs/2608.16844
- https://arxiv.org/abs/2608.17050
- https://arxiv.org/abs/2608.17269v1
- https://arxiv.org/abs/2608.17325
- https://arxiv.org/abs/2608.17325v1
- https://arxiv.org/abs/2608.17528
- https://arxiv.org/abs/2608.17597
- https://arxiv.org/abs/2608.17616
- https://arxiv.org/abs/2608.18066
- https://arxiv.org/abs/2608.18171
- https://arxiv.org/abs/2608.18222
- https://arxiv.org/abs/2608.18230
- https://arxiv.org/abs/2608.18474
- https://arxiv.org/abs/2608.19491
- https://arxiv.org/abs/2608.19669
- https://arxiv.org/abs/2608.19758
- https://arxiv.org/abs/2608.19920
- https://arxiv.org/abs/2608.20123
- https://arxiv.org/abs/2608.20427
- https://arxiv.org/abs/2608.20670
- https://arxiv.org/abs/2608.20839
- https://arxiv.org/abs/2608.20918
- https://arxiv.org/abs/2608.20927
- https://arxiv.org/abs/2608.20960v1
- https://arxiv.org/abs/2608.20961
- https://arxiv.org/abs/2608.21023
- https://arxiv.org/abs/2608.21230
- https://arxiv.org/abs/2608.21308
- https://arxiv.org/abs/2608.21384
- https://arxiv.org/abs/2608.21386
- https://arxiv.org/abs/2608.21693
- https://arxiv.org/abs/2608.22090
- https://arxiv.org/abs/2608.22103
- https://arxiv.org/abs/2608.22274
- https://arxiv.org/abs/2608.22354
- https://arxiv.org/abs/2608.22368
- https://arxiv.org/abs/2608.22631
- https://arxiv.org/abs/2608.22631v2
- https://arxiv.org/abs/2608.22646
- https://arxiv.org/abs/2608.22767
- https://arxiv.org/abs/2608.22830v1
- https://arxiv.org/abs/2608.22876
- https://arxiv.org/abs/2608.22898
- https://arxiv.org/abs/2608.23075v1
- https://arxiv.org/abs/2608.23167
- https://arxiv.org/abs/2608.23658v1
- https://arxiv.org/abs/2608.23807
- https://arxiv.org/abs/2608.23809
- https://arxiv.org/abs/2608.23809v1
- https://arxiv.org/abs/2608.23953
- https://arxiv.org/abs/2608.23956
- https://arxiv.org/abs/2608.23956v1
- https://arxiv.org/abs/2608.24174
- https://arxiv.org/abs/2608.24252v1
- https://arxiv.org/abs/2608.24302v1
- https://arxiv.org/abs/2608.24319
- https://arxiv.org/abs/2608.24790
- https://arxiv.org/abs/2608.24804
- https://arxiv.org/abs/2608.24804v1
- https://arxiv.org/abs/2608.24876
- https://arxiv.org/abs/2608.24876v1
- https://arxiv.org/abs/2608.24958
- https://arxiv.org/abs/2608.24979v1
- https://arxiv.org/abs/2608.25311
- https://arxiv.org/abs/2608.25428
- https://arxiv.org/abs/2608.25505
- https://arxiv.org/abs/2608.25512
- https://arxiv.org/abs/2608.25593
- https://arxiv.org/abs/2608.25661v1
- https://arxiv.org/abs/2608.25729
- https://arxiv.org/abs/2608.25832
- https://arxiv.org/abs/2608.25904
- https://arxiv.org/abs/2608.26086v2
- https://arxiv.org/abs/2608.26218v1
- https://arxiv.org/abs/2608.26374
- https://arxiv.org/abs/2608.26449
- https://arxiv.org/abs/2608.26449v1
- https://arxiv.org/abs/2608.26480v1
- https://arxiv.org/abs/2608.26530v1
- https://arxiv.org/abs/2608.26556
- https://arxiv.org/abs/2608.26779
- https://arxiv.org/abs/2608.26958
- https://arxiv.org/abs/2608.27128
- https://arxiv.org/abs/2608.27299
- https://arxiv.org/abs/2608.27311v1
- https://arxiv.org/abs/2608.27348
- https://arxiv.org/abs/2608.27448
- https://arxiv.org/abs/2608.27454
- https://arxiv.org/abs/2608.27513
- https://arxiv.org/abs/2608.27514
- https://arxiv.org/abs/2608.27548
- https://arxiv.org/abs/2608.27658
- https://arxiv.org/abs/2608.27658v1
- https://arxiv.org/abs/2608.27763
- https://arxiv.org/abs/2608.28011
- https://arxiv.org/abs/2608.28151
- https://arxiv.org/abs/2608.28151v1
- https://arxiv.org/abs/2608.28158
- https://arxiv.org/abs/2608.28363
- https://arxiv.org/abs/2608.28444
- https://arxiv.org/abs/2608.28476
- https://arxiv.org/abs/2608.28557
- https://arxiv.org/abs/2608.29058
- https://arxiv.org/abs/2608.29070
- https://arxiv.org/abs/2608.29093
- https://arxiv.org/abs/2608.29128v1
- https://arxiv.org/abs/2608.29305
- https://arxiv.org/abs/2608.29463
- https://arxiv.org/abs/2608.29464
- https://arxiv.org/abs/2608.29539
- https://arxiv.org/abs/2608.29543v1
- https://arxiv.org/abs/2608.29583
- https://arxiv.org/abs/2608.29605
- https://arxiv.org/abs/2608.29622v1
- https://arxiv.org/abs/2608.29641
- https://arxiv.org/abs/2608.29641v1
- https://arxiv.org/abs/2608.29662
- https://arxiv.org/abs/2608.29897v1
- https://arxiv.org/abs/2608.29953v1
- https://arxiv.org/abs/2608.29956
- https://arxiv.org/abs/2608.30092v1
- https://arxiv.org/abs/2608.30177
- https://arxiv.org/abs/2608.30181
- https://arxiv.org/abs/2608.30198
- https://arxiv.org/abs/2608.30300v1
- https://arxiv.org/abs/2608.30310
- https://arxiv.org/abs/2608.30320
- https://arxiv.org/abs/2608.30386
- https://arxiv.org/abs/2608.30413v1
- https://arxiv.org/abs/2608.30439
- https://arxiv.org/abs/2608.30532
- https://arxiv.org/abs/2608.30635
- https://arxiv.org/abs/2608.30695
- https://arxiv.org/abs/2608.30922
- https://arxiv.org/abs/2608.30963
- https://arxiv.org/abs/2608.31017v1
- https://arxiv.org/abs/2608.31067
- https://arxiv.org/abs/2608.31111v1
- https://arxiv.org/abs/2608.31157
- https://arxiv.org/html/2603.06642v2
- https://arxiv.org/html/2608.11859
- https://arxiv.org/html/2608.20918v1
- https://arxiv.org/html/2608.27454v1
- https://ask.cyberinfrastructure.org/t/slurm-gpu-cgroups-constraindevices/1745
- https://aws.amazon.com/blogs/opensource/aws-supports-agent-plugins-an-open-standard-for-portable-agent-extensions/
- https://benchlm.ai/benchmarks/longBenchV2
- https://blog.google/innovation-and-ai/technology/developers-tools/diffusion-gemma-faster-text-generation/
- https://blog.pebblous.ai/blog/swe-bench-verified-retired/en/
- https://claude.com/blog/building-with-claude-managed-agents
- https://claude.com/blog/claude-managed-agents
- https://community.openai.com/t/the-hugging-face-incident-and-the-road-ahead/1393041
- https://cspaper.org/openprint/20260728.0007v1
- https://debugml.github.io/cheating-agents/
- https://deepmind.google/models/gemini-diffusion/
- https://docs.docker.com/build/metadata/attestations/sbom/
- https://docs.docker.com/engine/containers/gpu/
- https://docs.docker.com/engine/containers/runmetrics/
- https://docs.docker.com/engine/release-notes/28/
- https://docs.docker.com/engine/release-notes/29/
- https://docs.docker.com/reference/cli/docker/container/run/
- https://docs.docker.com/reference/cli/docker/image/pull/
- https://docs.fireworks.ai/fine-tuning/managed-finetuning-intro
- https://docs.fireworks.ai/fine-tuning/models
- https://docs.nesi.org.nz/Interactive_Computing/Slurm_Interactive_Sessions/
- https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/cdi-support.html
- https://docs.primeintellect.ai/hosted-training/full-finetuning.md
- https://docs.primeintellect.ai/hosted-training/models-and-pricing.md
- https://docs.sglang.io/cookbook/autoregressive/GLM/GLM-5.3-Flash
- https://docs.sglang.io/cookbook/autoregressive/Qwen/Qwen3.8-Flash-Next
- https://docs.together.ai/docs/fine-tuning-models
- https://docs.vllm.ai/en/latest/serving/parallelism_scaling/
- https://docs.vllm.ai/en/latest/usage/troubleshooting/
- https://download.schedmd.com/slurm/slurm-24.11.7.tar.bz2
- https://download.schedmd.com/slurm/slurm-25.11.7.tar.bz2
- https://download.schedmd.com/slurm/slurm-26.05.3.tar.bz2
- https://epoch.ai/benchmarks/swe-bench-verified
- https://evalevalai.com/research/2026/04/29/eval-costs-bottleneck/
- https://explainx.ai/blog/glm-5-3-open-weights-delay-zai-august-2026
- https://fireworks.ai/blog/K3-LoRA-Training
- https://gdmalignment.substack.com/p/agi-safety-and-alignment-at-google
- https://github.com/A3S-Lab/AgentHarnessProtocol
- https://github.com/ByteDance-Seed/In-Place-TTT
- https://github.com/ByteDance-Seed/Modular-TTT
- https://github.com/ECNU-ICALK/HeteroFusion
- https://github.com/Entropy-Valley/Entropy-Valley
- https://github.com/Gen-Verse/OpenClaw-RL
- https://github.com/HarnessRouter/harnessrouter
- https://github.com/HazyResearch/zoology
- https://github.com/JoelNiklaus/harness-optimization
- https://github.com/KatherLab/LLM-Scheduler
- https://github.com/LE-WH/ThinkingWithoutWordsRepro
- https://github.com/Lightning-AI/pytorch-lightning/issues/21406
- https://github.com/Lightning-AI/pytorch-lightning/pull/21407
- https://github.com/MachineLearning-Nerd/icml26-decision-theoretic-test-time-training
- https://github.com/Maverick-Ansh/nano-k3
- https://github.com/MessiX77/Awesome-Efficient-dLLMs
- https://github.com/MoonshotAI/Attention-Residuals
- https://github.com/MoonshotAI/FlashKDA
- https://github.com/MoonshotAI/Kimi-K3
- https://github.com/MoonshotAI/MoonEP
- https://github.com/MuLabPKU/SHINE
- https://github.com/NVIDIA-NeMo/Gym/tree/main/nemotron_recipes/lightning-3.5
- https://github.com/NVIDIA/enroot/blob/master/conf/hooks/98-nvidia.sh
- https://github.com/NVIDIA/enroot/blob/master/doc/cmd/import.md
- https://github.com/NVIDIA/enroot/blob/master/doc/installation.md
- https://github.com/NVIDIA/enroot/blob/master/doc/requirements.md
- https://github.com/NVIDIA/enroot/blob/master/src/docker.sh
- https://github.com/NVIDIA/enroot/commit/8b3a130
- https://github.com/NVIDIA/enroot/issues/265
- https://github.com/NVIDIA/enroot/releases
- https://github.com/NVIDIA/enroot/releases/download/v4.2.1/enroot-check_4.2.1_$(uname
- https://github.com/NVIDIA/libnvidia-container/releases
- https://github.com/NVIDIA/nvidia-container-toolkit/releases
- https://github.com/NVIDIA/pyxis
- https://github.com/NVIDIA/pyxis/blob/main/README.md
- https://github.com/NVIDIA/pyxis/issues/161
- https://github.com/NVIDIA/pyxis/issues/175
- https://github.com/NVIDIA/pyxis/issues/176
- https://github.com/NVIDIA/pyxis/issues/180
- https://github.com/NVIDIA/pyxis/releases
- https://github.com/NVIDIA/pyxis/wiki/Frequently-asked-questions
- https://github.com/NVIDIA/pyxis/wiki/Installation
- https://github.com/NVIDIA/pyxis/wiki/Setup
- https://github.com/NVIDIA/pyxis/wiki/Usage
- https://github.com/NVlabs/GatedDeltaNet-2
- https://github.com/NicolasSchuler/hpc-compose
- https://github.com/NousResearch/hermes-agent/releases/tag/v2026.8.31
- https://github.com/NovaSky-AI/SkyRL
- https://github.com/QwenLM/Qwen3.8-Flash-Next/blob/main/tech_report.pdf
- https://github.com/SJTU-DENG-Lab/mbd-lms
- https://github.com/SakanaAI/fast-weight-product-key-memory
- https://github.com/SakanaAI/text-to-lora
- https://github.com/SchedMD/slurm/blob/master/CHANGELOG/slurm-25.05.md
- https://github.com/SchedMD/slurm/blob/master/CHANGELOG/slurm-25.11.md
- https://github.com/SchedMD/slurm/blob/master/CHANGELOG/slurm-26.05.md
- https://github.com/SchedMD/slurm/blob/slurm-22-05-11-1/RELEASE_NOTES
- https://github.com/SchedMD/slurm/blob/slurm-24-11-7-1/RELEASE_NOTES
- https://github.com/SchedMD/slurm/blob/slurm-25-05-8-1/RELEASE_NOTES.md
- https://github.com/SchedMD/slurm/blob/slurm-25-11-7-1/RELEASE_NOTES.md
- https://github.com/SchedMD/slurm/blob/slurm-25-11-7-1/debian/control
- https://github.com/SchedMD/slurm/blob/slurm-26-05-3-1/RELEASE_NOTES.md
- https://github.com/SchedMD/slurm/tags
- https://github.com/Sisyphbaous-DT-Project/open-qingyi
- https://github.com/VILA-Lab/Awesome-DLMs
- https://github.com/VectorInstitute/vector-inference
- https://github.com/adobe-research/NoLiMa
- https://github.com/agentmemoryprotocol/agentmemoryprotocol
- https://github.com/allenai/bolmo-core
- https://github.com/anchore/syft/blob/main/README.md
- https://github.com/anchore/syft/releases/tag/v1.51.1
- https://github.com/anthropics/claude-code
- https://github.com/apanariello4/merge-and-rebase
- https://github.com/baoguangsheng/faast
- https://github.com/bertybaums/abstract-cot
- https://github.com/booydar/babilong
- https://github.com/brayans7/tau2-bench-audit
- https://github.com/calpt/open-tinker
- https://github.com/deepseek-ai/Engram
- https://github.com/deepseek-ai/deepseek-harness
- https://github.com/devchaitanya/ARC-AGI-1
- https://github.com/fla-org/flash-linear-attention/blob/main/fla/ops/dsa/README.md
- https://github.com/fla-org/flash-linear-attention/pull/852
- https://github.com/fractale-lm/fractale
- https://github.com/ggml-org/llama.cpp/pull/27773
- https://github.com/goombalab/hnet
- https://github.com/goombalab/raven
- https://github.com/harbor-framework/terminal-bench/releases/tag/v3.0.0
- https://github.com/huggingface/transformers/pull/47670
- https://github.com/huggingface/transformers/pull/48250
- https://github.com/huggingface/transformers/pull/48455
- https://github.com/huggingface/transformers/releases/tag/v5.15.0
- https://github.com/huggingface/transformers/releases/tag/v5.16.0
- https://github.com/huggingface/transformers/tree/main/src/transformers/models/blt
- https://github.com/igeniusai/domyn-swarm
- https://github.com/inclusionAI/LLaDA2.X
- https://github.com/inclusionAI/LLaDA2.X/blob/main/LLaDA2_2_tech_report.pdf
- https://github.com/inclusionAI/dFactory
- https://github.com/kkuette/thought-bank
- https://github.com/kmccleary3301/nested_learning
- https://github.com/kvcache-ai/AgentENV
- https://github.com/microsoft/SWE-bench-Live
- https://github.com/ollama/ollama/releases/tag/v0.33.2
- https://github.com/openai/codex/releases/tag/rust-v0.152.0
- https://github.com/pc0618/block-diffusion-hybrids
- https://github.com/princeton-nlp/HELMET
- https://github.com/princeton-pli/LongProc
- https://github.com/programasweights
- https://github.com/ramp-public/portallib
- https://github.com/ramp-public/portallib/issues/28
- https://github.com/rishabbala/Steering-Vector-Transfer
- https://github.com/robbym-dev/portal-vlm
- https://github.com/saml212/matrix-states
- https://github.com/sgl-project/sglang/releases/tag/v0.5.17
- https://github.com/sgl-project/sglang/releases/tag/v0.5.18
- https://github.com/sierra-research/tau2-bench/issues/499
- https://github.com/swamynathanvp/Surprisal-Aware-Residual-Test-Time-Training
- https://github.com/swiss-ai/parity-aware-bpe
- https://github.com/sxewc/ttt-knowledge-writein-readout
- https://github.com/test-time-training/e2e/issues/8
- https://github.com/texttron/BrowseComp-Plus
- https://github.com/thinking-machines-lab/tinker-cookbook/blob/main/skills/research/references/hyperparams.md
- https://github.com/thinking-machines-lab/tinker-cookbook/blob/main/tinker_cookbook/hyperparam_utils.py
- https://github.com/thinking-machines-lab/tinker-cookbook/blob/main/tinker_cookbook/recipes/chat_sl/results/sft_sweep.md
- https://github.com/thinking-machines-lab/tinker-cookbook/blob/main/tinker_cookbook/recipes/harbor_rl/README.md
- https://github.com/thinking-machines-lab/tinker-cookbook/blob/main/tinker_cookbook/recipes/harbor_rl/train.py
- https://github.com/thinking-machines-lab/tinker-cookbook/blob/main/tinker_cookbook/weights/README.md
- https://github.com/thinking-machines-lab/tinker-cookbook/commits/main
- https://github.com/thinking-machines-lab/tinker-cookbook/issues/889
- https://github.com/thinking-machines-lab/tinker-feedback/issues/104
- https://github.com/thinking-machines-lab/tinker-feedback/issues/141
- https://github.com/thinking-machines-lab/tinker-feedback/issues/77
- https://github.com/thinking-machines-lab/tinker-feedback/issues/96
- https://github.com/thinking-machines-lab/tinker/blob/main/src/tinker/types/create_model_request.py
- https://github.com/thinking-machines-lab/tinker/blob/main/src/tinker/types/forward_backward_output.py
- https://github.com/thinking-machines-lab/tinker/blob/main/src/tinker/types/load_weights_request.py
- https://github.com/thinking-machines-lab/tinker/blob/main/src/tinker/types/lora_config.py
- https://github.com/thinking-machines-lab/tinker/blob/main/src/tinker/types/loss_fn_type.py
- https://github.com/thinking-machines-lab/tinker/blob/main/src/tinker/types/model_input_chunk.py
- https://github.com/v-code01/momentwo
- https://github.com/vercel-labs/agent-browser/releases
- https://github.com/vercel-labs/fx
- https://github.com/vercel/ai/releases
- https://github.com/vllm-project/FlashKDA
- https://github.com/vllm-project/dllm-plugin
- https://github.com/vllm-project/vllm/pull/53906
- https://github.com/vllm-project/vllm/pull/54371
- https://github.com/vllm-project/vllm/releases
- https://github.com/vllm-project/vllm/releases/tag/v0.27.0
- https://github.com/vllm-project/vllm/releases/tag/v0.28.0
- https://github.com/vllm-project/vllm/tree/main/docs/deployment/frameworks
- https://github.com/wfrederick7/cluster-llm-server
- https://github.com/xianhanglin/kimi-k2.6-int4-to-bf16
- https://github.com/xiaol827/ELO
- https://github.com/yancyou/TTT-NTP
- https://github.com/yifanzhang-pro/fast-weight-attention
- https://github.com/zai-org/GLM-5
- https://github.com/zeyun-zhong/E2-TTT
- https://groups.google.com/g/slurm-users/c/96Pp2b6stA8
- https://groups.google.com/g/slurm-users/c/Fv2cgq80GmU
- https://groups.google.com/g/slurm-users/c/nFsu33ep9eY
- https://hal.cs.princeton.edu/
- https://hub.docker.com/v2/repositories/vllm/vllm-openai/tags/v0.28.0
- https://huggingface.co/Ethangou/attention-residuals-0.6B-full
- https://huggingface.co/GSAI-ML/LLaDA-MoE-v2-30B-A3B-Instruct
- https://huggingface.co/JetLM/SDAR-4B-Chat-b16
- https://huggingface.co/LauraGG/qwen25math-7b-abstract-cot-grpo
- https://huggingface.co/MiniMaxAI/MiniMax-M3
- https://huggingface.co/Qwen/Qwen3.5-0.8B
- https://huggingface.co/Qwen/Qwen3.5-4B
- https://huggingface.co/Qwen/Qwen3.5-9B-Base
- https://huggingface.co/Qwen/Qwen3.8-27B
- https://huggingface.co/Qwen/Qwen3.8-27B/discussions/175
- https://huggingface.co/Qwen/Qwen3.8-Flash-Next
- https://huggingface.co/Qwen/Qwen3.8-Flash-Next/discussions
- https://huggingface.co/RampPublic
- https://huggingface.co/RampPublic/portal-gemma-4-e2b
- https://huggingface.co/RampPublic/portal-inkling
- https://huggingface.co/RampPublic/portal-mistral-7b
- https://huggingface.co/YanZhanPKU/Entropy-Valley-LLaDA-8B-En2De
- https://huggingface.co/allenai/Bolmo-7B
- https://huggingface.co/api/models/moonshotai/Kimi-K2.6?blobs=true
- https://huggingface.co/api/models?author=Qwen
- https://huggingface.co/barbonara/corin-kimi-k26-pro-sft/blob/main/adapter_config.json
- https://huggingface.co/blog/agent-intrusion-technical-timeline
- https://huggingface.co/cartesia-ai
- https://huggingface.co/collections/nace-ai/hypernetwork-datasets
- https://huggingface.co/collections/nvidia/nemotron-post-training-v3-6939b7b93382bac738eebd17
- https://huggingface.co/datasets/facebook/omnilingual-gaia2
- https://huggingface.co/datasets/gyung/gdn2-ruler-niah-eval-data
- https://huggingface.co/datasets/mkairov/mqar_N8_V8192_L24_noise0.9
- https://huggingface.co/datasets/thaki-AI/daily-paper-2026-08-27-harness-leverage-model-harness-attribution
- https://huggingface.co/datasets/thaki-AI/daily-paper-2026-08-29-goodhart-shift-self-evolving-harness
- https://huggingface.co/datasets/zai-org/terminal-bench-2-verified
- https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731
- https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-Base
- https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-Vision-Exp
- https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813
- https://huggingface.co/google/diffusiongemma-26B-A4B-it
- https://huggingface.co/google/gemma-4-12B-it-assistant
- https://huggingface.co/google/gemma-4-E4B
- https://huggingface.co/inclusionAI/LLaDA2.2-flash
- https://huggingface.co/jaisidhsingh/SignedKDA-kda
- https://huggingface.co/jaslee/Ouro-1.4B-Thinking-terminal-sft
- https://huggingface.co/manihani4/portal-vlm-gemma3-lora-1k
- https://huggingface.co/moonshotai/Kimi-K2.6
- https://huggingface.co/moonshotai/Kimi-K3
- https://huggingface.co/moonshotai/Kimi-K3/blob/main/LICENSE
- https://huggingface.co/moonshotai/Kimi-K3/discussions/180
- https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16
- https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-Base-BF16
- https://huggingface.co/openai/gpt-oss-120b
- https://huggingface.co/openai/gpt-oss-20b
- https://huggingface.co/papers/2210.14215
- https://huggingface.co/papers/2212.04458
- https://huggingface.co/papers/2305.15076
- https://huggingface.co/papers/2402.05232
- https://huggingface.co/papers/2405.16845
- https://huggingface.co/papers/2501.00663
- https://huggingface.co/papers/2504.13173
- https://huggingface.co/papers/2505.23735
- https://huggingface.co/papers/2505.23884
- https://huggingface.co/papers/2509.24510
- https://huggingface.co/papers/2511.21016
- https://huggingface.co/papers/2512.22768
- https://huggingface.co/papers/2601.14532
- https://huggingface.co/papers/2602.06358
- https://huggingface.co/papers/2602.15902
- https://huggingface.co/papers/2602.16093
- https://huggingface.co/papers/2604.00830
- https://huggingface.co/papers/2604.06169
- https://huggingface.co/papers/2604.12128
- https://huggingface.co/papers/2604.19295
- https://huggingface.co/papers/2604.23750
- https://huggingface.co/papers/2605.00702
- https://huggingface.co/papers/2605.06609
- https://huggingface.co/papers/2605.08587
- https://huggingface.co/papers/2605.21803
- https://huggingface.co/papers/2605.29157
- https://huggingface.co/papers/2606.08804
- https://huggingface.co/papers/2606.16899
- https://huggingface.co/papers/2606.21803
- https://huggingface.co/papers/2606.25342
- https://huggingface.co/papers/2606.26560
- https://huggingface.co/papers/2607.02303
- https://huggingface.co/papers/2607.07953
- https://huggingface.co/papers/2607.09415
- https://huggingface.co/papers/2607.19604
- https://huggingface.co/papers/2607.27945
- https://huggingface.co/papers/2608.06216
- https://huggingface.co/papers/2608.07110
- https://huggingface.co/papers/2608.12307
- https://huggingface.co/papers/2608.20061
- https://huggingface.co/programasweights/paw-4b-gpt2
- https://huggingface.co/programasweights/paw-4b-qwen3-0.6b
- https://huggingface.co/shiershuihesaixiliya/qingyi-kda-0.6b
- https://huggingface.co/startlux-models/gdn-1.3b-isp-hybrid-3to1-50b
- https://huggingface.co/state-spaces/mamba3-siso-1.5b
- https://huggingface.co/thinkingmachines/Inkling
- https://huggingface.co/thinkingmachines/Inkling-Small
- https://huggingface.co/thinkingmachines/Inkling/raw/main/config.json
- https://huggingface.co/zai-org/GLM-5.2
- https://huggingface.co/zai-org/GLM-5.3
- https://huggingface.co/zai-org/GLM-5.3-Flash
- https://huggingface.co/zai-org/GLM-5.3-Flash/discussions/26
- https://huggingface.co/zai-org/GLM-5.3/blob/main/LICENSE
- https://huggingface.co/zai-org/GLM-5.3/discussions/6
- https://huggingface.co/zeyun-zhong/e2-ttt-swiglu-1.3B-15B
- https://labs.ramp.com/research/portal-portable-task-adaptation/
- https://lists.schedmd.com/mailman3/hyperkitty/list/slurm-users@lists.schedmd.com/thread/UX6GRHJDLVHORVA6H6V37HPAKLCDQVLQ/
- https://longbench2.github.io/
- https://modal.com/pricing
- https://ollama.com/library/gemma4
- https://ollama.com/library/nemotron-3.5-lightning
- https://ollama.com/library/qwen3.8
- https://openai.com/index/harness-engineering/
- https://openai.com/index/separating-signal-from-noise-coding-evaluations/
- https://openai.com/index/unrolling-the-codex-agent-loop/
- https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/
- https://openmdw.ai/license/1-1/
- https://openrouter.ai/inception/mercury-2.5-preview
- https://oss.anchore.com/docs/guides/sbom/scan-targets/
- https://packages.ubuntu.com/jammy/amd64/slurm-wlm-basic-plugins/filelist
- https://packages.ubuntu.com/jammy/slurm-wlm
- https://packages.ubuntu.com/noble/amd64/slurm-wlm-basic-plugins/filelist
- https://packages.ubuntu.com/noble/slurm-wlm
- https://packages.ubuntu.com/resolute/amd64/slurm-wlm-basic-plugins/filelist
- https://packages.ubuntu.com/resolute/slurm-wlm
- https://proceedings.iclr.cc/paper_files/paper/2026/file/7df69dbf39705c7a39b40f2d70e806c1-Paper-Conference.pdf
- https://pypi.org/pypi/tinker-cookbook/json
- https://pypi.org/pypi/tinker/json
- https://raw.githubusercontent.com/vllm-project/vllm/v0.28.0/vllm/model_executor/models/registry.py
- https://recipes.vllm.ai/Qwen/Qwen3.8-27B
- https://recipes.vllm.ai/Qwen/Qwen3.8-Flash-Next
- https://recipes.vllm.ai/moonshotai/Kimi-K2.6
- https://recipes.vllm.ai/moonshotai/Kimi-K3
- https://recipes.vllm.ai/zai-org/GLM-5.3-Flash
- https://research.google/blog/introducing-nested-learning-a-new-ml-paradigm-for-continual-learning/
- https://researchcomputing.princeton.edu/support/knowledge-base/checkpointing
- https://researchcomputing.princeton.edu/support/knowledge-base/slurm
- https://researchcomputing.princeton.edu/systems/della
- https://researchcomputing.princeton.edu/systems/tiger
- https://scienceit-docs.lbl.gov/hpc/software/llms/vllm/
- https://selfimproving-agent.github.io/
- https://slurm.schedmd.com/cgroup.conf.html
- https://slurm.schedmd.com/cgroup_v2.html
- https://slurm.schedmd.com/containers.html
- https://slurm.schedmd.com/gres.conf.html
- https://slurm.schedmd.com/gres.html
- https://slurm.schedmd.com/quickstart_admin.html
- https://slurm.schedmd.com/release_notes.html
- https://slurm.schedmd.com/sbatch.html
- https://slurm.schedmd.com/scancel.html
- https://slurm.schedmd.com/scontrol.html
- https://slurm.schedmd.com/slurm.conf.html
- https://slurm.schedmd.com/slurmd.html
- https://slurm.schedmd.com/upgrades.html
- https://supabase.com/evals
- https://support.ceci-hpc.be/doc/_contents/SubmittingJobs/SlurmInteractive.html
- https://thinkingmachines.ai/blog/a-safe-path-to-open-weights/
- https://thinkingmachines.ai/blog/lora/
- https://thinkingmachines.ai/news/introducing-inkling/
- https://thinkingmachines.ai/news/learning-to-replicate-expert-judgment-in-financial-tasks/
- https://thinkingmachines.ai/news/putting-task-expertise-into-rl/
- https://thinkingmachines.ai/tinker/
- https://tinker-docs.thinkingmachines.ai/changelog/
- https://tinker-docs.thinkingmachines.ai/cookbook/recipes/sdft/
- https://tinker-docs.thinkingmachines.ai/cookbook/recipes/true-thinking-score/
- https://tinker-docs.thinkingmachines.ai/cookbook/recipes/verifiers-rl/
- https://tinker-docs.thinkingmachines.ai/tinker/api-reference/serviceclient/
- https://tinker-docs.thinkingmachines.ai/tinker/api-reference/trainingclient/
- https://tinker-docs.thinkingmachines.ai/tinker/cli/checkpoint/
- https://tinker-docs.thinkingmachines.ai/tinker/lora-primer/
- https://tinker-docs.thinkingmachines.ai/tinker/losses/
- https://tinker-docs.thinkingmachines.ai/tinker/losses/custom/
- https://tinker-docs.thinkingmachines.ai/tinker/model-deprecations/
- https://tinker-docs.thinkingmachines.ai/tinker/models.json
- https://tinker-docs.thinkingmachines.ai/tinker/models/
- https://tinker-docs.thinkingmachines.ai/tinker/under-the-hood/
- https://tinker-docs.thinkingmachines.ai/tutorials/core-concepts/weights/
- https://tinker-docs.thinkingmachines.ai/tutorials/deployment/lora-adapter/
- https://ttu-iclr2026.github.io/
- https://unsloth.ai/docs/models/kimi-k3
- https://vercel.com/blog/ai-sdk-7
- https://vercel.com/changelog/deepagents-and-opencode-harness-adapters
- https://vercel.com/changelog/fx-ai-sdk-harness-adapter
- https://vercel.com/changelog/program-agent-harnesses-with-ai-sdk
- https://vercel.com/changelog/use-acp-compatible-harnesses-with-the-ai-sdk-harness-layer
- https://vllm.ai/blog/2026-06-10-diffusion-gemma
- https://www.alphaxiv.org/abs/2508.12270
- https://www.alphaxiv.org/abs/2508.17550
- https://www.alphaxiv.org/abs/2509.23779
- https://www.alphaxiv.org/abs/2601.06100
- https://www.alphaxiv.org/abs/2602.17744
- https://www.alphaxiv.org/abs/2603.06642
- https://www.alphaxiv.org/abs/2605.16350
- https://www.alphaxiv.org/abs/2607.00368
- https://www.alphaxiv.org/abs/2607.07743
- https://www.alphaxiv.org/abs/2607.20792
- https://www.alphaxiv.org/abs/2607.23925
- https://www.alphaxiv.org/abs/2608.01672
- https://www.alphaxiv.org/abs/2608.13668
- https://www.alphaxiv.org/abs/2608.22354
- https://www.anthropic.com/engineering/april-23-postmortem
- https://www.anthropic.com/engineering/eval-awareness-browsecomp
- https://www.appliedcompute.com/
- https://www.appliedcompute.com/case-studies/harvey-review-table
- https://www.docs.arc.vt.edu/ai/030_vllm.html
- https://www.faros.ai/blog/openai-swe-bench-pro-audit
- https://www.inceptionlabs.ai/
- https://www.inceptionlabs.ai/blog/mercury-2-on-pinchbench
- https://www.inceptionlabs.ai/models
- https://www.kimi.com/blog/kimi-k3
- https://www.langchain.com/blog/improving-deep-agents-with-harness-engineering
- https://www.lmsys.org/blog/2026-07-27-kimi-k3-day0-support
- https://www.primeintellect.ai/blog/lab-is-open
- https://www.tbench.ai/news
- https://www.tbench.ai/news/leaderboard-integrity-update
- https://www.tbench.ai/news/terminal-bench-2-1
- https://www.tbench.ai/news/terminal-bench-3-0
- https://www.tbench.ai/news/terminal-bench-4-0
- https://www.vals.ai/benchmarks/terminal-bench-2-1
- https://www.w3.org/community/ai-agent-memory-interop/
- https://www.ycombinator.com/launches/Sv6-harnessrouter-open-sourcing-the-world-s-first-unified-interface-for-agent-harnesses-and-the-unified-harness-protocol
- https://x.com/0xSero/status/2083292412211028440
- https://x.com/AYi_AInotes/status/2084522269745820010
- https://x.com/ClaudeDevs/status/2085817074816070014
- https://x.com/Hesamation/status/2087917006448173519
- https://x.com/Kimi_Moonshot/status/2081762799202746420
- https://x.com/OpenAI/status/2074972179385720836
- https://x.com/OpenAIDevs/status/2085398373511918022
- https://x.com/RampLabs/status/2065485806605619304
- https://x.com/RampLabs/status/2072383322940957115
- https://x.com/RampLabs/status/2081819550329327689
- https://x.com/_lopopolo/status/2078602904861319520
- https://x.com/appliedcompute/status/2085495826638672109
- https://x.com/arafatkatze/status/2083236726676615535
- https://x.com/ctatedev/status/2078889282404569267
- https://x.com/deepseek_ai/status/2087887408440164663
- https://x.com/martin_casado/status/2081087412378505609
- https://x.com/mitchellh/status/2077788454860316915
- https://x.com/shawn_pana/status/2085953331751776745
- https://x.com/supabase/status/2083282155170340898
- https://x.com/swyx/status/2083073422410821846
- https://x.com/vercel_dev/status/2065509970775519569
- https://x.com/vercel_dev/status/2086520817169666488
- https://x.com/vercel_dev/status/2089828083415355806
- https://x.com/ycombinator/status/2083243960684908768
- https://z.ai/blog/glm-5.3-flash
