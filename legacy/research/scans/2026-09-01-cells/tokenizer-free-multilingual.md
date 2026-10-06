# Research cell: tokenizer-free-multilingual — sweep note (2026-09-01)

Cell: `tokenizer-free-multilingual`
Scope: byte-level / tokenizer-free compute allocation (BLT successors, H-Net dynamic chunking and
follow-ups, SpaceByte, MrT5, entropy patching), 2026 tokenizer-fertility inequity, parallel-data-
supervised architecture (boundaries, routing, depth, experts), translation equivariance/invariance in
LMs, cross-lingual compute allocation.
Prior sweep cutoff: 2026-08-10. Sources dated after that are marked **[post-cutoff]**.
Honesty: every claim below was read at the primary source (arXiv abstract page, arXiv HTML full text,
GitHub API, Hugging Face API, or the AI2 blog). "First-party" = author blog/README/abstract claim with
no independent replication found. Peer-review status is taken from arXiv comment fields (self-reported
acceptance) unless an anthology URL is given. No claim of "completely novel" is made anywhere.

---

## 1. Verdict in one paragraph

Byte-level modeling in 2026 is a busy, maturing axis: Meta (Fast BLT), Google (Scratchpad Patching),
Ai2 (Bolmo), Aleph Alpha (SOMBRERO), Cornell (Efficiency Gap) and several university groups have
occupied compute-within-patch allocation, boundary steering toward surprisal, compression-rate
scheduling, RL boundary learning, retrofit "byteification", and byte-level evaluation protocols.
Tokenizer-fertility auditing is saturated (five 2026 "tax" papers plus a pre-tokenizer bug census).
Multilingual MoE routing is analyzed with parallel data by four 2026 papers, but only for post-hoc
steering/adaptation. **No source found through 2026-09-01 under the coverage below uses parallel
translations as a training-time signal for where a tokenizer-free model places boundaries or spends
global compute**, so Direction 18 (translation-aligned byte boundary transport) is not collided —
but three post-08-10 or 2026 results change its required controls: (a) Scratchpad Patching's finding
that patchifier choice stops mattering once within-patch compute is redistributed, (b) Equity-with-
Efficiency's 1.5B result that BLT underperforms parity-aware BPE in low-resource Southeast Asian
languages, and (c) Leino & Tiedemann's negative result that parallel data barely changes cross-lingual
representation alignment (which argues for dropping or ablating Direction 18's patch-state transport
term and keeping only the boundary term). The closest new collision is "When Tokenizers Fail"
(EMNLP 2026, 2026-08-27): supervised dynamic-chunk boundaries on a frozen subword LM — but its
supervision is monolingual POS + subword targets, with zero use of parallel data in the full text.

---

## 2. Findings (every item opened at its primary source)

Format: **Title** — URL — date — source type / review status
Claim · Occupies · Relevance for Kevin · Confidence

### 2.1 Post-cutoff (after 2026-08-10) — highest priority

1. **Nested Byte-Level Vocabularies Are Cheap to Deploy and Expensive to Share: A Pre-Registered
   Negative Result** — https://arxiv.org/abs/2608.28151 — 2026-08-28 — arXiv, first-party, single
   author. **[post-cutoff]**
   Claim: 30 models (3.1M and 10.6M bodies, 200M tokens each) under five pre-registered claims with
   margins, seeds and a stop rule. Slicing a prefix-nested byte-BPE model is bit-exact (76 checks,
   removes 66% of deployed weights) but the shared model trails a fixed-cap specialist by 3.64% BPB at
   32k (1% margin) and 2.96% at 8k (2% margin). Control token effect +0.07% to +0.13% (CIs cross zero);
   output restriction costs +0.47% to +1.19%. Multi-cap training degrades 12.5-15.4 points less under
   typographical noise, but a control with neither cap token nor output restriction is equally robust,
   attributing robustness to multi-granularity exposure.
   Occupies: nested / multi-cap byte-BPE vocabularies; multi-granularity robustness.
   Relevance: a pre-registered negative with explicit margins is exactly the evidentiary format Kevin's
   harness enforces; the multi-granularity confound must be controlled in any multi-resolution byte pilot.
   Confidence 0.85.

2. **When Tokenizers Fail: Byte-Level Chunking for Zero-Shot Transfer to Low-Resource Languages** —
   https://arxiv.org/abs/2608.27658 — 2026-08-27 — arXiv; "Accepted to EMNLP 2026" (self-reported);
   code github.com/snjev310/ByteChunk. **[post-cutoff]**
   Claim: adapts H-Net onto a frozen subword LM: byte embeddings initialized from the base model's
   subword embeddings; a *chunk alignment loss* projects dynamically grouped byte chunks onto
   precomputed subword targets; lightweight POS supervision is interleaved to guide boundary detection.
   Six languages; up to 13.3% improvement on POS tagging over a subword baseline. Full-text grep: 0
   occurrences of "parallel"; conclusion lists "Compute asymmetry" and "Efficiency" as limitations.
   Occupies: externally supervised dynamic-chunk boundaries (monolingual POS + subword targets) on a
   frozen subword LM; cheap H-Net retrofits for low-resource zero-shot transfer.
   Relevance: closest new collision to Direction 18. It proves boundary supervision on a frozen LM is
   trainable cheaply, but the supervisory signal is monolingual; cross-lingual boundary transport stays
   unclaimed. Kevin's pilot must add a POS/subword-target boundary arm as a control.
   Confidence 0.9.

3. **What Tokens are Learned when Tokenization is Optimized Jointly with Language Modeling?** —
   https://arxiv.org/abs/2608.17325 — 2026-08-18 — arXiv, first-party. **[post-cutoff]**
   Claim: across 18 typologically and script-diverse languages (9 agglutinative, 6 fusional, 3
   analytic/introflexive), H-Nets "prioritize byte-level efficiency, producing longer tokens with very
   low overlap with standard subword vocabularies"; agglutinative languages show more dynamic
   segmentation during learning; SSLM-based pretokenization consistently reduces perplexity with
   competitive downstream BERT results.
   Occupies: cross-typology analysis of jointly learned segmentations vs fixed tokenizers.
   Relevance: supplies the measurement protocol (and the baseline fact that learned boundaries diverge by
   typology and from subword vocabularies) that Kevin's per-language patch analysis must reproduce before
   any "aligned boundaries" claim.
   Confidence 0.8.

4. **Vowel Signs Are Not Letters: A Pre-tokenization Ceiling on Multilingual Tokenizer Fertility** —
   https://arxiv.org/abs/2608.26449 — 2026-08-26 — arXiv, first-party; harness released
   (github: sajalregmi/arkios-tokenizer, updated 2026-08-26). **[post-cutoff]**
   Claim: the GPT-2 `\p{L}+` word regex in HF ByteLevel pre-tokenizers splits abugida words at every
   vowel sign, a training-free fertility floor. In a 26-language parallel corpus all 17 abugidas are hit
   (1.47x Tibetan to 9.02x Thai); Latin/Cyrillic/Hangul/Han exactly 1.00x. Matched 268M models: the
   fixed tokenizer gets 4.43% lower Nepali BPB at equal compute and still leads at 1.59x compute for the
   broken one. Census: 63.3% of the most-downloaded HF text-generation repos carry the letters-only
   class (72.5% of downloads).
   Occupies: pre-tokenization fertility ceiling; tokenizer-bug audits.
   Relevance: any BPE/parity control arm in a multilingual byte pilot must patch this regex or the
   tokenizer baseline is a strawman. Cheap kill-shot check for fertility-based claims.
   Confidence 0.85.

5. **Measuring the Tokenization Premium: A Cost Audit for Underserved Language Communities (TEA)** —
   https://arxiv.org/abs/2608.09046 — 2026-08-10 — arXiv; IJCAI 2026 workshop (self-reported).
   Claim: 120-item Python-debugging corpus translated into Bengali, Hindi, Arabic, Tamil, Yoruba.
   Bengali needs 1.56x GPT-4o (o200k) tokens (128k window -> 82k English-equivalent) and up to 4.5x with
   Qwen2.5-7B / Mistral-7B tokenizers; Yoruba 2.37x on GPT-4o despite Latin script.
   Occupies: tokenization-premium cost audits. Relevance: saturated axis; quantifies the inequity a
   compute-parity metric would target. Confidence 0.8.

6. **Disentangling Language Modeling and Boundaries** — https://arxiv.org/abs/2608.03599 — 2026-08-04
   — arXiv position paper, first-party, single author.
   Claim: byte-level models share an exact output space, so knowledge transfer between them is
   tokenizer-independent; hypothesizes the next-byte distribution and the boundary distribution can be
   changed almost independently ("absorb a teacher's capability while keeping its own boundaries, or
   change how it places boundaries while keeping its capabilities"); lays out two experiments with
   preliminary measurements only. Notes UTF-8 spends more bytes per character on non-Latin scripts.
   Occupies: conceptual framing of boundary/capability disentanglement in byte LMs.
   Relevance: Direction 18 is an instance of "reshape boundaries, keep capability". The framing is now
   published but unvalidated, so Kevin's matched pilot would be the first empirical test of the
   disentanglement, not a first framing.
   Confidence 0.8.

7. **Goomba Lab / Cartesia H-Net lineage status** — https://github.com/goombalab/hnet ;
   https://github.com/goombalab/raven ; https://huggingface.co/cartesia-ai — checked 2026-09-01 —
   GitHub/HF API, first-party metadata. **[post-cutoff check]**
   Claim: `goombalab/hnet` last pushed 2025-11-20 (878 stars); Cartesia H-Net checkpoints
   (`hnet_1stage_L/XL`, `hnet_2stage_L/XL`, `_chinese`, `_code`) last modified 2025-07-11. Goomba's
   newest repos are **Raven** (routing-memory linear model on Flash Linear Attention, pushed 2026-08-19)
   and Mohawk (Transformer->SSM distillation, 2026-07-02). Cartesia's 2026 repos are voice SDKs.
   Occupies: nothing new on H-Net from the original group.
   Relevance: multilingual H-Net extensions are being done by outside groups (H-Net++, ATDC, SOMBRERO,
   When Tokenizers Fail); the codebase is stable but unmaintained — a feasibility plus and a support risk.
   Confidence 0.85.

8. **BLT upstream in Hugging Face transformers** —
   https://github.com/huggingface/transformers/tree/main/src/transformers/models/blt — latest fix
   2026-08-26 ("fix bug for blt model parallel bug (#48327)") — GitHub API. **[post-cutoff]**
   Claim: `modeling_blt.py`, `modular_blt.py`, `configuration_blt.py`, weight converter present and
   patched in Aug 2026; `facebookresearch/blt` itself last committed 2025-11-03; `facebook/blt-1b` /
   `blt-7b` / `blt-entropy` HF weights last modified 2025-05-01.
   Occupies: reference BLT implementation. Relevance: Kevin's yaml assumes a reviewed HF BLT
   implementation; it exists and is actively patched, lowering integration risk for a boundary head.
   Confidence 0.85.

### 2.2 2026 sources before the cutoff that were not in the 2026-08-10 sweep

9. **Scratchpad Patching: Decoupling Compute from Patch Size in Byte-Level Language Models** —
   https://arxiv.org/abs/2605.09630 — 2026-05-10 — arXiv (Google authors), first-party.
   Claim: identifies *patch lag*; entropy-triggered within-patch scratchpads let 16-byte patches match or
   closely approach the byte-level baseline with a 16x smaller patch KV cache and 3-4x less inference
   compute. Section 4.3: with SP, fixed-size, SpaceByte, entropy and H-Net patchifiers "cluster in
   performance-FLOPs space, indicating that the primary bottleneck may be insufficient compute rather
   than suboptimal boundary placement." Section 5.2 (FLORES-200, 200 languages, BPB rank): pure
   byte-level model strongest and most consistent, tokenizer-based model worst on average, SP narrows
   patch-based models' gap.
   Occupies: within-patch compute allocation decoupled from patch size; multilingual patchifier ranking.
   Relevance: **kill-shot risk for Direction 18** — if boundary rule is irrelevant once compute is
   redistributed, translation-aligned boundaries may show nothing. An SP-style compute-matched arm is a
   required control. Also the strongest published evidence that byte models are the most
   language-robust encoding on FLORES-200.
   Confidence 0.9.

10. **Fast Byte Latent Transformer** — https://arxiv.org/abs/2605.08044 — 2026-05-08 — arXiv (Meta:
    Kallini, Pagnoni, Limisiewicz, Ghosh), first-party.
    Claim: BLT-D (auxiliary block-wise diffusion), BLT-S (self-speculation), BLT-DV (diffusion +
    verification) at 1B/3B; >50% lower estimated memory-bandwidth cost than BLT, up to 92% with quality
    loss, BLT-DV up to 81%; evaluated on FLORES-101 fr->en and de->en (4-shot, spBLEU), HumanEval,
    MBPP. 3B table: ARC-Easy 74.33 (BLT) vs 72.39/70.95/66.89 (BLT-D-4/8/16).
    Occupies: byte-level generation speed.
    Relevance: removes the "byte LMs are too slow to serve" objection; translation is already its
    headline eval, so the FLORES protocol is reusable. Confidence 0.85.

11. **SOMBRERO: Measuring and Steering Boundary Placement in End-to-End Hierarchical Sequence Models**
    — https://arxiv.org/abs/2601.22805 — 2026-01-30 — arXiv (Aleph Alpha Research), first-party.
    Claim: router-agnostic *boundary enrichment* metric B (how strongly chunk starts concentrate on
    high next-byte-surprisal positions); confidence-alignment boundary loss plus input-level
    confidence-weighted smoothing; at 1B on English, German, code and math, improves the
    accuracy-efficiency trade-off.
    Occupies: steering learned boundaries toward surprisal; boundary-quality metric.
    Relevance: provides the diagnostic Kevin must report; its steering target is monolingual surprisal,
    not cross-lingual correspondence. Confidence 0.85.

12. **Adaptive Targeted Dynamic Chunking for Tokenization-Free Hierarchical Model (ATDC)** —
    https://arxiv.org/abs/2605.30080 — 2026-05-28 — arXiv, first-party.
    Claim: curriculum on target compression ratio (low->high), tracked via Bytes-Per-Innermost-Chunk;
    on FineWeb-Edu 100B, competitive BPB with byte- and token-level baselines, more stable training and
    better downstream than fixed ratios.
    Occupies: compression-ratio scheduling in H-Net-style models.
    Relevance: defines the patch-rate control Kevin's yaml already lists; shows fixed ratios confound.
    Confidence 0.8.

13. **You Can Learn Tokenization End-to-End with Reinforcement Learning** —
    https://arxiv.org/abs/2602.13940 — 2026-02-15 (v updated 2026-08-25, "ICML 2026 camera-ready",
    self-reported) — arXiv/peer-reviewed.
    Claim: score-function (time-discounted) boundary estimators beat straight-through boundary learning
    qualitatively and quantitatively at 100M parameters.
    Occupies: discrete boundary learning via RL vs STE.
    Relevance: a relaxation-free route to add a boundary reward (e.g., cross-lingual agreement) and a
    stronger router baseline than H-Net's STE. Confidence 0.8.

14. **Dynamic Tokenization via Reinforcement Patching (ReinPatch)** — https://arxiv.org/abs/2603.26097
    — 2026-03-27 — arXiv, first-party.
    Claim: GRPG-optimized patching policy with strict compression-rate enforcement; evaluated on
    time-series forecasting; patcher extractable as a standalone module. Full text: 0 hits for
    "languages"/"multilingual".
    Occupies: RL patching with hard compression rate (time series only). Relevance: no text or
    multilingual claim; the mechanism is portable. Confidence 0.75.

15. **Equity with Efficiency: An Empirical Study of Tokenizers for Multilingual LLMs** —
    https://arxiv.org/abs/2606.15044 — 2026-06-13 — arXiv (NUS), first-party.
    Claim: 11 Southeast Asian languages, controlled 1.5B decoder training on identical data:
    Parity-aware BPE on the efficiency-equity Pareto frontier; MYTE best semantic reasoning at higher
    cost; **Byte Latent Transformer underperforms on downstream tasks**, "possibly because its
    architectural assumptions misalign with the constraints of limited low-resource training data."
    Limitations: 1.5B only; BLT has no matched-vocabulary comparison; base models only.
    Occupies: head-to-head equitable-tokenizer benchmark at 1.5B.
    Relevance: **negative signal for BLT in Kevin's exact regime** (low-resource multilingual, limited
    data). The 20M-50M pilot must show entropy-BLT beats parity-BPE before boundary transport is
    credited; Direction 18's control #5 (parity-aware SentencePiece/BPE) is therefore load-bearing.
    Confidence 0.85.

16. **The Efficiency Gap in Byte Modeling** — https://arxiv.org/abs/2605.12928 — 2026-05-13 — arXiv
    (Cornell), first-party.
    Claim: compute-matched scaling: byte-level penalty is worse for masked diffusion than AR; AR byte
    predictive entropy aligns with BPE boundaries (emergent segmentation); permutation controls attribute
    MDM failure to context fragility.
    Occupies: byte-level x diffusion scaling (negative). Relevance: kills "byte diffusion for free";
    confirms entropy patching rediscovers BPE-like boundaries, so Kevin must test whether
    translation-aligned boundaries differ from BPE at all. Confidence 0.85.

17. **Beyond Perplexity: UTF-8 Validity in Byte-aware Language Models** —
    https://arxiv.org/abs/2606.14122 — 2026-06-12 — "ICML 2026" (self-reported).
    Claim: 355M model, 80B tokens balanced En/Ja/Ko/Zh: perplexity stabilizes after 2.1B tokens but
    UTF-8 validity needs 4.2B; rare characters more structurally valid than common ones.
    Occupies: byte-level evaluation protocol. Relevance: Kevin's Chinese/Korean pilots must report
    UTF-8 validity separately from BPB. Confidence 0.85.

18. **Bolmo: Byteifying the Next Generation of Language Models** — https://arxiv.org/abs/2512.15586 ;
    https://allenai.org/blog/bolmo ; https://github.com/allenai/bolmo-core ;
    https://huggingface.co/allenai/Bolmo-7B — paper 2025-12-17 (v2 2026-02-09); blog 2025-12-15; HF
    weights modified 2026-06-17; repo pushed 2026-08-28 (last default-branch commit 2026-03-13) —
    arXiv + lab blog, first-party.
    Claim (blog): stage 1 freezes the Olmo 3 7B transformer and trains local encoder/decoder/boundary
    predictor/head on 9.8B tokens (~43B bytes); stage 2 unfreezes for 39.3B tokens (~173B bytes).
    Character-aggregate accuracy up "nearly twenty points" vs Olmo 3; IFEval base 31.1% vs 35.4%
    (67.4% vs 66.9% after weight merging); ~125 bytes/s vs ~150 for subword; "strongest overall" vs BLT
    7B, TFree-HAT 7B, EvaByte 6.5B. 1B variant from Olmo 2 1B.
    Occupies: retrofit byteification of subword LMs with a learned boundary predictor.
    Relevance: fully open lineage (Olmo, Apache-style) vs BLT-1B's CC-BY-NC gate recorded in
    memory.json; the stage-1 recipe is the cheapest place to insert a parallel-data boundary objective
    on 8xH100. Confidence 0.75 (first-party numbers).

19. **KazByte: Adapting Qwen models to Kazakh via Byte-level Adapter** —
    https://arxiv.org/abs/2603.27859 — 2026-03-29 — arXiv "technical announcement", first-party.
    Claim: byte adapter into frozen Qwen2.5-7B then attention-only fine-tuning on Kazakh; "Empirical
    validation is ongoing; this version stakes the design and hypotheses for the record."
    Occupies: single-language byte adapter on a frozen subword LM (design only).
    Relevance: the adapter route is claimed but unvalidated; Tinker LoRA cannot reach byte interfaces,
    so this remains a local-H100 lane for Kevin. Confidence 0.7.

20. **On the limited utility of parallel data for learning shared multilingual representations** —
    https://arxiv.org/abs/2603.29026 — 2026-03-30 — arXiv (Leino & Tiedemann, Helsinki), first-party.
    Claim: reference models with varying parallel-data proportions show "only a minimal effect on the
    cross-lingual alignment", limited to accelerating early representation sharing and reducing
    language-specific neurons; alignment emerges similarly without the signal.
    Occupies: parallel data as a representation-alignment signal (negative).
    Relevance: **kill-shot for any Kevin direction whose mechanism is representation alignment from
    parallel data**; supports restricting Direction 18's delta to boundary formation and dropping or
    ablating the `lambda_z` patch-state transport term. Confidence 0.8.

21. **The Role of Mixed-Language Documents for Multilingual LLM Pretraining** —
    https://arxiv.org/abs/2601.00364 — 2026-01-01 (v 2026-01-23, under review) — arXiv, first-party.
    Claim: removing the 2% bilingual documents drops translation BLEU 56% while cross-lingual QA and
    reasoning are unchanged; reintroducing parallel documents restores 91% of translation, code-switching
    restores little.
    Occupies: what parallel data buys in pretraining. Relevance: parallel data's causal payoff is
    token-level alignment for translation, so a boundary objective should be judged on
    translation/terminology fidelity where the signal demonstrably matters. Confidence 0.8.

22. **Multilingual Routing in Mixture-of-Experts** — https://arxiv.org/abs/2510.04694 — 2025-10-06
    (v2 2026-02-17; "ICLR 2026", self-reported) — peer-reviewed.
    Claim: using FLORES-200 parallel text on Qwen3-30B-A3B, Phi-3.5-MoE and others, routing is
    language-specific in early/late layers and cross-lingually aligned in middle layers; steering routers
    toward English-activated middle-layer task experts gives consistent 1-2% gains across 3 models and
    15+ languages; interventions elsewhere degrade.
    Occupies: parallel-data analysis and inference-time steering of MoE routing.
    Relevance: parallel data is used only to analyze/steer routers post hoc; training-time
    cross-lingual routing consistency remains unclaimed (Gap G2). Confidence 0.85.

23. **Unveiling Language Routing Isolation in Multilingual MoE Models (RISE)** —
    https://arxiv.org/abs/2604.03592 — 2026-04-04 — "Findings of EMNLP 2026" (self-reported).
    Claim: high- and low-resource languages activate largely disjoint expert sets; training only
    routing-selected subnetworks gives up to 10.85% target-language F1 gain across 10 languages.
    Related: 2601.14050 (routing aligns with language families; middle layers as language-agnostic
    hubs; routing-guided steering) and 2605.29714 (continual pretraining diffuses early/middle routing;
    <2% parameter adaptation of final-layer experts).
    Occupies: routing-isolation-guided subnetwork adaptation. Relevance: the MoE adaptation lane is
    crowded; a Tinker LoRA on Qwen3.5-35B-A3B would be a weaker version. Confidence 0.75.

24. **Rate-Utility Frontiers for Language Encodings** — https://arxiv.org/abs/2607.16117 — 2026-07-17
    — arXiv, first-party (already cited in Direction 18).
    Claim: 13 languages, 5 scripts, verified parallel sentences, swept bottleneck: bytes preserve
    cross-lingual sentence alignment best (especially same-script), pixels surface form, tokens topic.
    Occupies: encoding comparison under controlled content. Relevance: motivates byte interfaces for
    cross-lingual work. Confidence 0.8.

25. **Cross-lingual Self-Consistency for Multilingual Reasoning** — https://arxiv.org/abs/2606.01464
    — 2026-05-31 — arXiv, under review, first-party.
    Claim: unsupervised RL enforcing same final answer across languages, no gold answers or parallel
    data; up to 21.7% average MGSM gain over 10 languages, 18.2% on unseen languages.
    Occupies: answer-level translation invariance via RL without parallel data.
    Relevance: shows invariance can be induced at the output level without parallel data or
    architectural change — lowers expected value of an equivariance *architecture* (Gap G4).
    Confidence 0.8.

26. **The Tokenizer Tax ... for Indian Languages** — https://arxiv.org/abs/2607.24276 — 2026-07-27 —
    arXiv, first-party. Claim: FLORES-200, 6 tokenizers, 14 languages; cl100k_base average 8.0x tax,
    13.0x Malayalam, effective context down to 12%; merge failure correlates r=0.89 with tax; XLM-R and
    o200k cut the average Indic tax 73%. Occupies: fertility audits. Relevance: saturated; useful
    numbers for a compute-parity target. Confidence 0.8.

27. **The African Language Tax** — https://arxiv.org/abs/2606.24460 — 2026-06-23 — arXiv,
    first-party. Claim: 20 African languages, 11 tokenizers, FLORES-200+/SIB-200 (r=0.9998 across
    corpora); median premium 1.88x on o200k, up to 8.92x for N'Ko; Ethiopic/N'Ko 7-9x; as little as
    11% effective context; Gemma 4 best at 2.38x mean vs 3.31x for cl100k. Occupies: fertility audits.
    Confidence 0.8. (See also 2605.24718 — 25 European languages, 2.5x span, Ukrainian 15-18% penalty;
    2608.21384 — Cyrillic, Ukrainian 68-121% overhead, balanced 200K BPE cuts UK/EN ratio 2.22x->1.30x.)

### 2.3 Pre-2026 anchors that the prior sweep's collision list lacks

28. **MAGNET: Improving the Multilingual Fairness of LMs with Adaptive Gradient-Based Tokenization** —
    https://arxiv.org/abs/2407.08818 — 2024-07-11 — arXiv (NeurIPS 2024 per reproduction repo
    mohamad-755/magnet-african-tokenization, updated 2026-08-27).
    Claim: routes byte sequences through language-script-specific boundary predictors to enforce
    equitable segmentation granularity across scripts, versus single-predictor gradient tokenizers that
    still over-segment non-Latin scripts.
    Occupies: script-specific boundary predictors for compute parity.
    Relevance: **missing from Direction 18's collision list**; it is the closest prior for cross-lingual
    compute parity via boundaries (parity by script routing, not by translation alignment). Must be
    cited and preferably run as a control. Confidence 0.8.

29. **FLEXITOKENS** — https://arxiv.org/abs/2507.12720 — 2025-07-17 (v4 2026-05-13, "ACL Findings
    2026", self-reported); code skai-research/flexitokens (2 stars, pushed 2025-09-29).
    Claim: replaces the fixed-compression auxiliary loss of gradient-based byte tokenizers with a
    flexible objective; up to 10-point gains on token classification/generation across multilingual
    benchmarks and scales. Occupies: adaptive compression rate in learned byte tokenizers.
    Relevance: Kevin's fixed target patch-rate grid should include a free-rate arm. Confidence 0.8.

30. **Parallel Tokenizers** (https://arxiv.org/abs/2510.06128, 2025-10-07, v 2026-07-27) and
    **Conditional Unigram Tokenization with Parallel Data** (https://arxiv.org/abs/2507.07824,
    2025-07-10, TokShop) — arXiv, first-party.
    Claims: Parallel Tokenizers aligns monolingual vocabularies via bilingual dictionaries / word
    translation for 13 low-resource languages and beats multilingual encoder baselines on four tasks.
    Conditional Unigram conditions target token probabilities on source tokens: **no MT improvement**
    on four pairs, consistent LM perplexity reduction; authors blame quadratic vocab scaling.
    Occupies: parallel-data-supervised *static* tokenization / vocabulary alignment.
    Relevance: confirms parallel data has been used for vocabularies but not for dynamic compute units;
    the Conditional Unigram mixed result warns that segmentation supervision can lower BPB without
    helping translation, so the primary endpoint must be task fidelity. Confidence 0.8.

Other items opened and judged tangential: H-Net++ (2508.05628, Persian, 73.8% F1 on gold morphological
boundaries without supervision); Zonkey (2601.21768, differentiable Segment Splitter inside a
hierarchical diffusion LM); Dynamic Chunking for Diffusion LMs (2605.15676, content-defined chunks up to
1.5B); ByteSpan (2506.18639, byte-LM-surprisal-driven static subwords, 25 languages); Phonemes to the
Rescue (2606.20993, IPA tokenizers, 24 languages); WWHO/SGPE (2603.25309, Sinhala TWR 1.274, 61.7%
fewer tokens than o200k); Reducing Tokenization Premiums (2601.13328, post-hoc vocabulary coalescing on
Llama 3.2 1B); Trans-Tokenization (2408.04303, COLM 2024); Multi-way parallel TED2025 (2505.14045,
EMNLP 2025 oral); LINK lexical substitution (2605.23885); DAMA (2602.01008, speech ASR depth-aware
adaptation, U-shaped layer adaptability, 80% fewer trainable parameters); TIDE (2603.21365, per-token
early exit, no language conditioning); Kathleen Writes (2608.04678, attention-free byte LM at <1M
params, single author).

---

## 3. Occupied axes

| Axis | What is taken (with dates) | Representative primary URLs | Remaining room |
|---|---|---|---|
| Dynamic byte patching at scale | Entropy patches (BLT, ACL 2025), learned routers (H-Net 2025-07), byteified boundary predictors (Bolmo 2025-12), speed (Fast BLT 2026-05), within-patch compute (Scratchpad 2026-05), ratio curricula (ATDC 2026-05) | https://arxiv.org/abs/2412.09871 https://arxiv.org/abs/2507.07955 https://arxiv.org/abs/2512.15586 https://arxiv.org/abs/2605.08044 https://arxiv.org/abs/2605.09630 https://arxiv.org/abs/2605.30080 | Boundaries defined by anything other than next-byte statistics or compression rate |
| Boundary steering / learning objective | Surprisal-aligned boundary loss + metric B (SOMBRERO 2026-01), free compression rate (FlexiTokens ACL-F 2026), RL score-function boundaries (ICML 2026), RL patching w/ hard rate (ReinPatch 2026-03), POS/subword-target chunk alignment on frozen LM (When Tokenizers Fail, EMNLP 2026) | https://arxiv.org/abs/2601.22805 https://arxiv.org/abs/2507.12720 https://arxiv.org/abs/2602.13940 https://arxiv.org/abs/2603.26097 https://arxiv.org/abs/2608.27658 | Cross-lingual (parallel-view) boundary supervision |
| Retrofit byteification / byte adapters on frozen subword LMs | Bolmo two-stage (2025-12), KazByte design (2026-03), When Tokenizers Fail (2026-08), Disentangling position paper (2026-08) | https://arxiv.org/abs/2512.15586 https://arxiv.org/abs/2603.27859 https://arxiv.org/abs/2608.27658 https://arxiv.org/abs/2608.03599 | Retrofit stage supervised by parallel data |
| Parallel-data-supervised static tokenization | Parallel Tokenizers (2025-10), Conditional Unigram (2025-07, mixed), Trans-Tokenization (COLM 2024), Parity-Aware BPE (ACL 2026), LINK (2026-05) | https://arxiv.org/abs/2510.06128 https://arxiv.org/abs/2507.07824 https://arxiv.org/abs/2408.04303 https://github.com/swiss-ai/parity-aware-bpe https://arxiv.org/abs/2605.23885 | Dynamic (inference-time) units rather than vocabularies |
| Tokenizer fertility / tax audits | Indian (2026-07), European (2026-05), African (2026-06), Cyrillic (2026-07), TEA (2026-08), Vowel-sign ceiling (2026-08), Equity-with-Efficiency 1.5B (2026-06), NeurIPS 2025 inequities | https://arxiv.org/abs/2607.24276 https://arxiv.org/abs/2605.24718 https://arxiv.org/abs/2606.24460 https://arxiv.org/abs/2608.21384 https://arxiv.org/abs/2608.09046 https://arxiv.org/abs/2608.26449 https://arxiv.org/abs/2606.15044 https://arxiv.org/abs/2510.21909 | Saturated; only compute-per-meaning ledgers for dynamic models remain |
| Multilingual MoE routing analysis and steering | ICLR 2026 routing analysis + steering (1-2%), family-aligned routing (2026-01), RISE subnetworks (EMNLP-F 2026), continual-pretraining routing dynamics (2026-05) | https://arxiv.org/abs/2510.04694 https://arxiv.org/abs/2601.14050 https://arxiv.org/abs/2604.03592 https://arxiv.org/abs/2605.29714 | Training-time routing objectives from parallel views |
| Script-specific boundary predictors for parity | MAGNET (2024), H-Net++ Persian (2025-08) | https://arxiv.org/abs/2407.08818 https://arxiv.org/abs/2508.05628 | Parity measured per semantic unit rather than per script |
| Byte-level x diffusion | Efficiency Gap negative (2026-05), BLT-D (2026-05), DCDM (2026-05), Zonkey (2026-01) | https://arxiv.org/abs/2605.12928 https://arxiv.org/abs/2605.08044 https://arxiv.org/abs/2605.15676 https://arxiv.org/abs/2601.21768 | Prior sweep already rejects diffusion+MoE; nothing new for Kevin |
| Byte-level evaluation protocols | UTF-8 validity (ICML 2026), boundary enrichment B (2026-01), FLORES-200 BPB rank (2026-05) | https://arxiv.org/abs/2606.14122 https://arxiv.org/abs/2601.22805 https://arxiv.org/abs/2605.09630 | Compute-per-semantic-unit metric across translations |

---

## 4. Open gaps (searched for and not found; not brainstorms)

**G1. Parallel-translation supervision of dynamic byte/patch boundaries (Direction 18 remains open,
with new required controls).**
Why open: every 2026 boundary objective found targets monolingual signals (surprisal, compression
rate, POS/subword targets); every parallel-data tokenization work targets static vocabularies.
Evidence searched: arXiv `"byte-level" AND "word alignment"` (1 hit: When Tokenizers Fail — no parallel
data), `"dynamic chunking" AND "cross-lingual"` (0), `boundary AND translation AND byte AND aligned AND
"language model"` (0), `"parallel sentences" AND "byte-level" AND "language model"` (0), `"byte-level"
AND "parallel corpus"` (4, none relevant), `"chunk alignment"` (no cross-lingual hit); GitHub code
search `"byte latent" alignment translation`, `"dynamic chunking" translation aligned`, `hnet boundary
supervision` (0 each); S2 `translation-aligned boundary supervision byte-level patches parallel corpus`
(irrelevant Kibajuni NMT hits); WebSearch on parallel supervision of boundaries/routing (only MoE
routing analysis returned).
New kill-shot controls: Scratchpad-style compute-matched arm (2605.09630), parity-aware BPE arm with
the `\p{L}+` bug fixed (2606.15044, 2608.26449), POS/subword-target boundary arm (2608.27658),
UTF-8 validity endpoint (2606.14122), and an ablation of the patch-state transport term given
2603.29026.
Kevin advantage: production parallel data with terminology/error categories; 8xH100 suffices for the
20M-125M grid; BLT is upstream in HF transformers (fix 2026-08-26) and Bolmo-1B offers an open-license
alternative to the CC-BY-NC BLT-1B; the NumPy UOT doctor already exists in the repo.

**G2. Training-time cross-lingual routing consistency in MoE from parallel views.**
Why open: all four 2026 MoE-multilingual papers use parallel data to *analyze* or *steer at inference*
(1-2% gains) or to pick subnetworks for adaptation; none add a training objective that makes parallel
sentences route through the same middle-layer experts.
Evidence searched: arXiv `"mixture of experts" AND "parallel corpus" AND routing` (0); `"parallel data"
AND "mixture of experts" AND multilingual` (2 NMT-specific: FuxiMT, task-level MoE for NMT);
`"language-specific" AND experts AND routing AND multilingual AND 2026` (4 analysis/adaptation papers,
none training-time from parallel data); S2 parallel-routing queries (429 x2); WebSearch #4 (only
2510.04694).
Caveat: 2603.29026 finds parallel data barely moves *representation* alignment; whether it moves
*routing* alignment is untested, so this gap could close as a negative result — still publishable
under Kevin's standards.
Kevin advantage: parallel data at scale; 8xH100 for a from-scratch small MoE (routers are not
reachable through Tinker LoRA on Qwen3.5-35B-A3B / Nemotron-3.5-Lightning-30B-A3B unless router
weights are exposed — unverified).

**G3. Compute-per-semantic-unit parity for dynamic-patching models, measured on translations.**
Why open: fertility audits count tokens per word per language for static tokenizers; Scratchpad
Patching ranks BPB across 200 FLORES languages but does not report global-model FLOPs per aligned
sentence; MAGNET enforces parity per *script*, not per meaning; no paper measures how many BLT/H-Net
global-compute units the same sentence costs across languages at matched quality.
Evidence searched: arXiv `"patch size" AND byte AND language` (1: Scratchpad), `"language model" AND
"bytes per patch"` (1: Scratchpad), `"cross-lingual" AND "compute allocation"` (0), `disparities AND
"byte-level" AND patch` (0), `"compute-matched" AND "byte-level" AND multilingual` (0), `"tokenizer" AND
"inference cost" AND languages AND "bytes per token"` (0); S2 patch-length-per-language queries (429);
WebSearch on per-language patch length refused (budget).
Kevin advantage: the repo already has a fertility benchmark harness (`data/tokens/{model}_fertility.json`
in memory.json) and FLORES-style parallel data; extending it to patch counts on `facebook/blt-1b`,
Cartesia H-Net and Bolmo-1B is a CPU/1-GPU measurement, not a training run.

**G4. Explicit translation-equivariance/invariance constraint in LM architecture (open, low expected
value).**
Why open: no LM architecture paper frames boundaries, routing or depth as equivariant to translation.
Evidence searched: arXiv `"translation equivariance" AND "language model"` (1: Equi-mRNA, biology);
`"equivariant" AND translation AND multilingual AND "language model"` (0); `"semantic hub" AND
multilingual` (0 via API); `"language-agnostic" AND "byte-level" AND "language model"` (0); WebSearch on
language-agnostic / translation-invariant representations refused (budget).
Why low value: 2603.29026 shows alignment emerges without parallel data, and 2606.01464 induces
answer-level invariance with RL and no parallel data or architecture change. An equivariance
*constraint* would need to beat both as controls.
Kevin advantage: parallel data makes the equivariance test cheap; nothing else is unique.

**G5. Parallel-supervised byteification stage on an open lineage.**
Why open: Bolmo's stage 1 trains the boundary predictor on monolingual bytes; KazByte is unvalidated
and single-language; When Tokenizers Fail supervises with POS/subword targets. No work trains a
retrofit boundary predictor with a cross-lingual objective.
Evidence searched: arXiv `all:Bolmo OR all:"byteifying" OR all:"byteify"` (only Bolmo); `byte AND frozen
AND subword AND adapter AND multilingual` (0); `"boundary predictor" AND byte` (FlexiTokens, MAGNET
only); HF search `bolmo` (only Ai2 and a ru->en lyric SFT hobby fork); GitHub `allenai/bolmo-core`
commits (no multilingual branch).
Kevin advantage: Bolmo-1B stage-1 scale (~43B bytes on a frozen 1B) is within an 8xH100 weekend; Olmo
lineage avoids the BLT CC-BY-NC licensing decision recorded in memory.json; parallel data is on hand.

---

## 5. Exact queries run

### arXiv export API (`search_query=...`, sortBy=submittedDate) — 41
1. all:"byte latent transformer"
2. all:"dynamic chunking" AND all:tokenizer
3. all:"H-Net" OR all:"hierarchical network" AND all:"byte-level"
4. all:"entropy patching" OR all:"entropy-based patching"
5. all:SpaceByte OR all:MrT5 OR all:"byte-level language model"
6. all:tokenizer AND all:fertility AND all:multilingual
7. all:"tokenization premium" OR all:"tokenizer inequity" OR all:"token tax"
8. all:"parallel data" AND all:"mixture of experts" AND all:multilingual
9. all:"translation equivariance" AND all:"language model"
10. all:"cross-lingual" AND all:"compute allocation"
11. all:"tokenizer-free" AND all:multilingual
12. all:"byte-level" AND all:"parallel corpus"
13. all:"byte-level" AND all:"word alignment"
14. all:"patch" AND all:"byte" AND all:"multilingual" AND all:"languages"
15. all:"language-agnostic" AND all:"byte-level" AND all:"language model"
16. all:"semantic hub" AND all:multilingual
17. all:"multilingual" AND all:"early exit" AND all:"language model"
18. all:"tokenization" AND all:"reinforcement learning" AND all:"end-to-end"
19. all:"boundary" AND all:"supervision" AND all:"byte" AND all:"hierarchical"
20. all:"cross-lingual" AND all:"latent" AND all:"patch"
21. all:"parallel data" AND all:"tokenizer" AND all:"cross-lingual" AND all:"vocabulary"
22. all:"H-Net" AND all:multilingual
23. all:Bolmo OR all:"byteifying" OR all:"byteify"
24. all:"boundary predictor" AND all:byte
25. all:"mixture of experts" AND all:"parallel corpus" AND all:routing
26. all:"language-specific" AND all:experts AND all:routing AND all:multilingual AND all:2026
27. all:"patch size" AND all:byte AND all:language
28. all:"tokenizer" AND all:"inference cost" AND all:languages AND all:"bytes per token"
29. all:"morphologically rich" AND all:"byte-level" AND all:"language model"
30. all:"equivariant" AND all:translation AND all:multilingual AND all:"language model"
31. all:"cross-lingual" AND all:"knowledge transfer" AND all:"parallel data" AND all:2026
32. all:"chunk alignment"
33. all:byte AND all:frozen AND all:subword AND all:adapter AND all:multilingual
34. all:"dynamic chunking" AND all:"cross-lingual"
35. all:boundary AND all:translation AND all:byte AND all:aligned AND all:"language model"
36. all:disparities AND all:"byte-level" AND all:patch
37. all:MAGNET AND all:tokenization AND all:multilingual
38. all:"compute-matched" AND all:"byte-level" AND all:multilingual
39. all:"language model" AND all:"bytes per patch"
40. all:"parallel sentences" AND all:"byte-level" AND all:"language model"
41. all:"tokenizer-free" AND all:"low-resource" AND all:2026
Plus id_list / abs-page fetches for 50 IDs and HTML full-text greps for 15 IDs (not counted as queries).

### Semantic Scholar graph API — 14 attempted, 3 returned (HTTP 429 on the rest)
byte latent transformer patches scale better than tokens (429) · H-Net dynamic chunking hierarchical
sequence modeling end-to-end tokenization (OK) · tokenizer fertility multilingual inequity cost 2026
(429) · parallel translation data supervise routing mixture of experts language-specific (429) ·
translation invariance language model representations cross-lingual alignment parallel sentences
(429) · tokenizer fertility multilingual inequity (429) · parallel corpus supervision mixture of
experts routing language-agnostic experts (429) · cross-lingual consistency of representations
parallel sentences language models translation invariance (429) · adaptive compute per language early
exit multilingual language model (OK) · bilingual parallel data joint tokenization boundaries alignment
(429) · translation-aligned boundary supervision byte-level patches parallel corpus (OK, irrelevant) ·
byte latent transformer multilingual patch length analysis (429) · byte-level language model
multilingual patch length across languages compute (429) · learned tokenization boundaries bilingual
parallel data cross-lingual consistency (429)

### WebSearch — 6 executed, 6 refused (session budget 200/200 exhausted)
Executed: "Byte Latent Transformer" 2026 scaling follow-up patches · H-Net dynamic chunking follow-up
2026 hierarchical tokenizer-free Goomba Cartesia · Bolmo byteifying language models AI2 byte-level 2026
· parallel translation data supervise patch boundaries OR routing OR experts cross-lingual architecture
2026 arXiv · byte-level language model negative result limitations does not scale 2026 · multilingual
adaptive compute per language "mixture of depths" OR "early exit" OR "compute allocation" low-resource
2026.
Refused: "Nested Byte-Level Vocabularies" pre-registered negative result 2026 · "When Tokenizers Fail"
byte-level chunking zero-shot transfer low-resource languages 2026 · byte latent transformer OR H-Net
patch length per language ... compute parity across languages · language-agnostic OR
translation-invariant representations LLM parallel sentences 2026 "semantic hub" OR "concept space" ·
"Fast Byte Latent Transformer" OR "Scratchpad Patching" byte-level 2026 arXiv · "dynamic chunking" OR
"byte patch" boundaries supervised with parallel translations OR word alignment OR bilingual 2026.

### GitHub — 17 repo searches, 4 code searches, 14 API inspections
`gh search repos`: byte latent transformer · dynamic chunking hnet · tokenizer-free language model ·
entropy patching bytes · SpaceByte · MrT5 byte · bolmo · boundary placement hierarchical ·
reinforcement patching · parity-aware bpe · tokenizer fertility multilingual · byte-level adapter ·
dynamic tokenization reinforcement · cross-lingual tokenizer parallel · multilingual tokenizer
fairness · token fertility · byte-level llm multilingual.
`gh search code`: "byte latent" alignment translation · "dynamic chunking" translation aligned ·
"entropy patch" multilingual · hnet boundary supervision (all 0 results).
`gh api`: facebookresearch/blt, goombalab/hnet, kjslag/spacebyte, jkallini/mrt5, allenai/bolmo (404),
allenai/bolmo-core, allenai/OLMo-core, goombalab repos (raven README, mohawk README), sukjunhwang repos,
cartesia-ai repos, huggingface/transformers models/blt (+ hnet 404), swiss-ai/parity-aware-bpe,
skai-research/flexitokens.

### Hugging Face model API — 18 searches
blt · byte-latent · hnet · h-net · bytelevel · byte-level · tokenizer-free · spacebyte · mrt5 · bolmo ·
byte-level-adapter · kazbyte · facebook/blt · cartesia-ai/hnet · goombalab · swiss-ai parity ·
author=cartesia-ai · author=facebook&search=blt.

### Kevin's X bookmarks (`ft search`) — 14 queries, 0 relevant hits
"byte latent transformer" · "H-Net dynamic chunking" (FTS5 syntax error on hyphen) · "tokenizer free
bytes" · "tokenization multilingual fertility" · bytes · BLT · hnet · tokenizer · tokenization ·
patches · "Albert Gu" · Cartesia · multilingual · translation. The only related item is General
Translation's own grant post (@generaltxn 2026-08-19), not architecture content.

### Primary pages opened
arXiv abstract pages for 50 IDs (meta-tag scrape), arXiv HTML full text for 2608.27658, 2608.03599,
2605.08044, 2605.12928, 2510.04694, 2507.07824, 2601.22805, 2603.26097, 2605.09630, 2605.30080,
2606.15044, 2608.17325; Goomba Lab "H-Nets — the Past/Future" blog posts (direct curl); Cartesia
hierarchical-modeling post (direct curl); Ai2 Bolmo blog (WebFetch).

Total distinct search queries executed: 114 (41 arXiv + 14 S2 + 6 WebSearch + 21 GitHub search +
18 HF + 14 ft); 6 further WebSearch queries were refused by the session budget.

---

## 6. Coverage limits (honest)

- Semantic Scholar returned HTTP 429 on 11 of 14 queries even at 30-60 s pacing; citation-graph
  discovery (who cites BLT/H-Net in 2026) was therefore not done.
- The Jina reader (r.jina.ai) rejected every request from this network ("bad network reputation,
  AS7018"); primary pages were fetched by direct curl or WebFetch instead. OpenReview (API 403 and a
  verification wall) could not be read, so the BLT camera-ready revision note (search snippet says
  "last modified 2026-05-29") is unverified.
- The session's WebSearch budget was exhausted after six queries in this cell; six planned searches
  (listed above) did not run, so grey literature (blogs, X threads, talks) after 2026-08-10 is
  under-covered except via GitHub/HF metadata.
- The arXiv export API rate-limited bursts (429); abstracts were obtained by scraping arxiv.org/abs
  meta tags. arXiv `all:` matching is exact-phrase; paraphrased titles may be missed. No ACL
  Anthology, Google Scholar or OpenReview search; EMNLP/ICML/ICLR 2026 acceptances are self-reported
  in arXiv comments except BLT (ACL Anthology URL seen in WebSearch results).
- Graphcore's BLT research post returned 404 via WebFetch; not read.
- Full PDFs were not read; claims come from abstracts plus HTML full-text greps of 12 papers.
  Per-language tables inside Scratchpad Patching, Equity-with-Efficiency and When Tokenizers Fail were
  not extracted number-by-number.
- Hugging Face search is by model-name substring; byte-level models without blt/hnet/bolmo/byte in the
  name were missed. Kevin's X bookmarks contain nothing on this topic, so that modality contributed
  zero evidence.
- Non-English-language venues and Chinese lab reports were not searched.
- No independent replication of any 2026 result was found; all quantitative claims above are
  first-party unless marked peer-reviewed, and peer review does not imply replication.

---

## 7. Implications for the existing Direction 18 contract (not a new proposal)

- Add MAGNET (2407.08818) and When Tokenizers Fail (2608.27658) to the collision list; add MAGNET-style
  per-script predictors and a POS/subword-target boundary arm as controls.
- Add a Scratchpad-Patching compute-matched arm; the falsifier "gains vanish after matching FLOPs"
  should explicitly include within-patch compute redistribution.
- Add UTF-8 validity (2606.14122) as a required secondary endpoint for Chinese/Korean.
- Fix the `\p{L}+` pre-tokenizer bug in the parity-aware BPE control (2608.26449) or the control is
  invalid for any abugida language later added.
- Consider dropping or explicitly ablating the `lambda_z` patch-state transport term given 2603.29026;
  the defensible delta is boundary mass only.
- Consider Bolmo-1B (open license, HF weights 2026-06-17) as the retrofit base instead of the gated
  CC-BY-NC BLT-1B recorded in memory.json; BLT stays as the from-scratch code lineage (upstream in
  transformers, patched 2026-08-26).
