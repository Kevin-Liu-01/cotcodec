# Research Direction: Translation-Supervised Sparse Indexer

**Status:** draft; wave-3 identification re-registration applied; not pilot-ready
**Owner:** Kevin Liu
**Source cutoff:** 2026-09-01
**Coverage limits:** WebSearch budget exhausted mid-sweep; arXiv API, Semantic Scholar and Jina blocked from this Mac (arXiv reached only through the H100-host relay, and 10 of 13 boolean queries returned HTTP 429); OpenReview forums behind browser verification (4 hits unread); no ACL Anthology full text, patents or Chinese-language sources beyond the verification pass; full text of QSA, GLM-5.3 and SpotAttention not read for per-language indexer tables; nothing executed on the H100 node or on Tinker; no parallel corpus exists in the repository; TED usage-policy page, NVIDIA H100 datasheet and TyDi QA dataset card not fetched in this session
**Budgets:** queries=60; wall_minutes=600; tokens=900000; dollars=40; waves=4; gpu_hours=16
**Novelty verdict:** NO_DIRECT_PRIOR_FOUND
**Safety verdict:** PASS
**Evidence bundle:** evidence/translation-supervised-sparse-indexer/bundle.json

## Claim and Research Question

Learned sparse-attention indexers of the DSA/QSA class, distilled only from full
attention onto frozen released checkpoints, are claimed to carry an **excess
cross-lingual selection gap** beyond the gap of their own distillation target —
measured, after the wave-3 repair, with both legs of the gap being non-literal
semantic queries, so that literal-versus-semantic retrieval fragility cannot
masquerade as a cross-lingual effect. Supervising the *detached* indexer with
corpus-given sentence alignments from bilingual document pairs (a training view
that never touches main attention; inference unchanged) is claimed to remove
most of the residual gap that the **strongest label-free target aggregation**
leaves behind, on **held-out languages** at **matched achieved token budget**,
with the fix visible in generation exact match rather than only in
selection-recall proxies.

Research question. Given a frozen decoder-only LM with a KL-distilled top-k
indexer, (RQ1) does the indexer lose more cross-script selection recall than its
own target when monolingual and cross-lingual queries are equally non-literal;
(RQ2) is that excess gap an artifact of the target aggregation (head-sum versus
max-pool versus retrieval-head-weighted), removable with zero labels; and (RQ3)
conditional on a residual gap after the best label-free target, does alignment
content — not bilingual exposure, not the loss form, not generic monolingual
semantic sharpening — recover it, on languages never seen by the alignment loss?

claim_scope: **attachment-capability.** The pilot tests a detachable indexer on
frozen checkpoints, the setting SpotAttention reports reaches English dense
parity. The architecture-causal version (indexer objective inside QSA-style
continued pretraining, or from-scratch hybrids with a parity tokenizer) is a
gated Phase 2 outside the 16 GPU-hour contract. The load-bearing new content is
the diagnostic (RQ1/RQ2); the alignment loss is a recognizable transfer of NMT
guided attention to a new object.

## Strategic Fit and Why Now

Every production sparse-attention lab now ships a learned indexer: DeepSeek-V3.2
trains its lightning indexer by KL to head-summed attention; Qwen3.8-Next trains
a compressed-block indexer against a max-pooled target; GLM-5.3-Flash ships a
32-head DSA indexer; SpotAttention shows a frozen-backbone KL selector reaching
dense parity in English. None of them reports per-language selection behaviour,
and the only cross-lingual audit of a learned selector (Lost in Compression)
covers prompt compressors, not attention indexers. The 2026-09-01 sweep found
the axis "learned indexer selection across translations" empty in every cell
(synthesis G13, seq-operators G6, benchmarks-eval G2). The VERIFICATION PASS
CORRECTIONS require MLNeedle and OneRuler as the cross-lingual NIAH baselines;
both are dense-softmax results and neither touches selection.

Why Kevin, why now: the pilot needs no private asset, but a mature Docker/Slurm
harness that can train many detached indexers in one shared frozen-teacher
stream is exactly what the repository already does, and the instrument this
proposal delivers (per-language achieved-token ledger plus indexer-versus-target
selection recall) is the kind of receipt the program exists to produce. General
Translation's document-level parallel pairs are an optional upgrade for
low-resource cross-script pairs and the Phase-2 continued-pretraining corpus,
not a dependency. The deployment interest — cross-lingual long-context retrieval
over translation memories under a sparse indexer — is real and unstated by any
sparse-attention lab.

## Primary-Source Evidence

Indexer class and its training recipes (all first-party technical reports):

- DeepSeek-V3.2 / DSA — https://arxiv.org/abs/2512.02556 (2025-12-02). Lightning
  indexer trained by KL to head-summed, L1-normalized dense attention; a
  2.1B-token frozen warm-up followed by 943.7B tokens with the backbone
  unfrozen; no per-language analysis.
- On the Design of Qwen3.8-Next (QSA) — https://arxiv.org/abs/2608.30320
  (2026-08-31). Compressed-block indexer with a max-pooled KL target chosen to
  preserve salient token-level signal; QSA beats full attention on RULER
  512K–1M (90.08 → 93.00) and MRCR 512K (30.66 → 40.53); only aggregate MMMLU is
  reported for multilinguality.
- SpotAttention — https://arxiv.org/abs/2606.22874 (2026-06). Frozen Qwen3/Qwen3.5
  backbones, a 4 × 128 KL-distilled selector trained on 100M tokens at 16K (763
  steps) on every full-attention layer, dual top-p budgets, English dense parity
  to 128K on 4B–32B bases; non-English untested; no public code found.
- Oracle-Guided Sparse Prefill — https://arxiv.org/abs/2606.07703 (2026-06).
  Frozen-backbone, head-collapsed indexer KL-distilled from dense attention mass
  on Qwen3.5-0.8B/9B, plus an attention-mass top-k oracle that separates
  sparse-budget feasibility from indexer error. This is the monolingual
  precursor of the ξ decomposition used here; it was missing from the wave-2
  closest-prior list and is added by the wave-3 repair.
- Released indexer configurations read from Hugging Face on 2026-09-01:
  GLM-5.3-Flash https://huggingface.co/zai-org/GLM-5.3-Flash/blob/main/config.json
  (index_n_heads 32, index_head_dim 128, index_topk 2048, index_kpool 4; 321.3B
  total parameters; FP8 weights); Qwen3.8-Flash-Next
  https://huggingface.co/Qwen/Qwen3.8-Flash-Next/blob/de4b8e4d43b917e7706784d8bb445c9af86a3540/config.json
  (indexer_n_heads 4, indexer_kv_heads 1, indexer_head_dim 128,
  indexer_compress_ratio 4, indexer_budget 2048; 48 layers, 512 experts top-10,
  QSA at 12 layers; model_type qwen4_exp_text; license qwen-community-1.0).

Why literalness must be separated from language (the wave-3 repair's evidence):

- NoLiMa — https://arxiv.org/abs/2502.05167 (2025-02). Removing literal overlap
  between query and needle collapses retrieval monolingually (GPT-4o 99.3 → 69.7
  at 32K); the wave-2 ξ compared a verbatim-copy monolingual query with a
  zero-overlap cross-lingual query and therefore conflated the two effects.
- RULER — https://arxiv.org/abs/2404.06654 (2024-04): vanilla NIAH is near-saturated
  by literal matching; induction heads — https://arxiv.org/abs/2209.11895 (2022-09).
- Retrieval heads — https://arxiv.org/abs/2404.15574 (2024-04): fewer than 5% of
  heads perform copy-retrieval, motivating the retrieval-head-weighted target.
- RTPurbo — https://arxiv.org/abs/2605.16928 (2026-05): long-range retrieval is
  governed by a low-dimensional subspace and a 16-dimensional indexer suffices
  once the target is the retrieval heads rather than the head sum; fixed top-k
  is reported inferior to top-p. The wave-2 note cited RTPurbo under the id
  2608.26449, which is the Vowel Signs abugida-tokenizer paper; corrected here.
- Semantic Hub — https://arxiv.org/abs/2411.04986 (2024-11) and Wendler et al. —
  https://arxiv.org/abs/2402.10588 (2024-02): frozen LMs place translations
  close in intermediate layers, so monolingual semantic supervision could
  transfer cross-lingually; this motivates the information-matched arm (i).

Cross-lingual long-context baselines and audit protocol:

- MLNeedle — https://arxiv.org/abs/2408.10151 (2024-08, NAACL 2025): 7–8B instruct
  models score about 0.30 (zh), 0.24 (ar), 0.25 (hi) versus 0.68 (en) at 4K on
  cross-lingual needles. OneRuler — https://arxiv.org/abs/2503.01996 (2025-03):
  instruction language alone moves results by up to 20 points. Both are
  mandatory dense baselines per the verification-pass corrections.
- Lost in Compression — https://arxiv.org/abs/2608.26175 (2026-08-28): the
  cross-lingual selection gap of learned extractive compressors tracks the
  supervision data, with budgets matched in the target tokenizer; its
  achieved-budget protocol is adopted.
- MGAL — https://arxiv.org/abs/2608.20853 (2026-08-21): multilingual
  granularity-aware long-context benchmark on UN reports in 6 languages; an
  endpoint candidate with no sparse-attention component.
- Two-forward-pass prefix-invariance audit — https://arxiv.org/abs/2608.22876;
  counterfactual sparse-attention audit — https://arxiv.org/abs/2608.01676;
  SWA plus attention sinks — https://arxiv.org/abs/2608.28444 (control).

Prior art for the loss form (the mechanism is a transfer, not an invention):
Liu et al. 2016 — https://arxiv.org/abs/1609.04186; Chen et al. 2016 —
https://arxiv.org/abs/1607.01628; Garg et al. 2019 — https://arxiv.org/abs/1909.02074
(supervised/guided NMT attention with aligner labels on the *main* attention);
AlignAtt4LLM — https://arxiv.org/abs/2606.03967 (post-hoc head selection with
model-generated alignments); Routing Absorption — https://arxiv.org/abs/2603.02227
(post-hoc frozen gating avoids co-adaptation; supports the frozen setting).
Training-free selection controls: PIVOT — https://arxiv.org/abs/2607.24593;
NSA pooled-key selection — https://arxiv.org/abs/2502.11089; LongCat LSA —
https://arxiv.org/abs/2608.01662 (cross-layer index distillation).

Data sources (licenses as stated on the cited pages; see Safety):
ParaDocs — https://huggingface.co/datasets/jhu-clsp/paradocs (card apache-2.0;
ParaCrawl text CC0 per https://paracrawl.eu; paper
https://aclanthology.org/2024.findings-acl.589/); TED2020 v1 via OPUS —
https://opus.nlpl.eu/TED2020; FineWeb-2 —
https://huggingface.co/datasets/HuggingFaceFW/fineweb-2/tree/af9c13333eb981300149d5ca60a8e9d659b276b9
(ODC-By 1.0); Belebele —
https://huggingface.co/datasets/facebook/belebele/tree/7899cdfa4e1e0d733fd77c848e2c273cb1d32be2
(CC-BY-SA 4.0); WMT24++ —
https://huggingface.co/datasets/google/wmt24pp/tree/fd7405c06494bc66a57b25f55d217a72f96e60dc
(apache-2.0); FLORES+ — https://huggingface.co/datasets/openlanguagedata/flores_plus
(CC-BY-SA 4.0, gated); TyDi QA GoldP —
https://huggingface.co/datasets/google-research-datasets/tydiqa (arm (i) only;
card not fetched this session).

Kernels and throughput reference points: flash-linear-attention —
https://github.com/fla-org/flash-linear-attention/blob/main/fla/ops/nsa/parallel.py
(parallel_nsa / parallel_nsa_topk with block_indices of shape [B, TQ, H, S];
asserts HQ/H at least 16), https://github.com/fla-org/flash-linear-attention/tree/main/fla/ops/dsa
(only naive.py), https://github.com/fla-org/flash-linear-attention#benchmarks
(GB200 first-party table: chunk_gdn 3.616 ms versus flash_attn 19.960 ms at
B=2, T=16384, H=16, D=128, forward plus backward); llm.c —
https://github.com/karpathy/llm.c/discussions/481 (GPT-2 124M, 10B tokens in
about 90 minutes on 8 × A100 80GB, about 60% MFU, first-party).

### Claim registry

Protocol followed: scratchpad ext/ars/academic-pipeline/references/claim_verification_protocol.md
(E1 registry, E2 tracing, E3 cross-reference; statuses VERIFIED = independently
re-read from the primary page in this gauntlet, FIRST_PARTY = author/lab claim
read from its own page or config, UNVERIFIABLE_ACCESS = page not fetched in this
session or blocked). Pre-registered thresholds and budgets are our own design
parameters and are registered as such (R38–R40).

| claim_id | claim text | source URL + locator | status |
|---|---|---|---|
| R01 | Qwen3-0.6B-Base @ da87bfb608c14b7cf20ba1ce41287e8de496c0cd: 28 layers, 16 Q / 8 KV heads, head dim 128, hidden 1024, 32K context, 596M parameters, apache-2.0 | https://huggingface.co/Qwen/Qwen3-0.6B-Base/tree/da87bfb608c14b7cf20ba1ce41287e8de496c0cd — config.json | FIRST_PARTY (config re-read by the wave-2 feasibility refuter 2026-09-01) |
| R02 | Qwen3.5-4B @ 851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a: 32 layers, full attention at layers 3, 7, …, 31 (8 layers), 16 Q / 4 KV × 256, GDN elsewhere, 4.66B parameters, apache-2.0; this is the post-trained checkpoint, Qwen3.5-4B-Base is a separate unregistered repo | https://huggingface.co/Qwen/Qwen3.5-4B/blob/851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a/config.json — layer_types | FIRST_PARTY (re-read by the wave-2 feasibility refuter) |
| R03 | Qwen3.8-Flash-Next @ de4b8e4d43b917e7706784d8bb445c9af86a3540: 180B total parameters (125B + 51B n-gram + 4B MTP in safetensors metadata), 48 layers, 512 experts top-10, QSA at 12 layers, indexer_n_heads 4, indexer_kv_heads 1, indexer_head_dim 128, indexer_compress_ratio 4, indexer_budget 2048, model_type qwen4_exp_text, license qwen-community-1.0 | https://huggingface.co/Qwen/Qwen3.8-Flash-Next/blob/de4b8e4d43b917e7706784d8bb445c9af86a3540/config.json | FIRST_PARTY |
| R04 | GLM-5.3-Flash: index_n_heads 32, index_head_dim 128, index_topk 2048, index_kpool 4; 321.3B total parameters; FP8 weights on HF (about 321 GB) | https://huggingface.co/zai-org/GLM-5.3-Flash/blob/main/config.json | FIRST_PARTY |
| R05 | DSA indexer trained by KL to head-summed L1-normalized attention; 2.1B-token frozen warm-up then 943.7B tokens unfrozen | https://arxiv.org/abs/2512.02556 — §2 (DSA training) | FIRST_PARTY |
| R06 | QSA uses a max-pooled KL target; RULER 512K–1M 90.08 → 93.00 and MRCR 512K 30.66 → 40.53 for QSA versus full attention | https://arxiv.org/abs/2608.30320 — architecture and long-context tables | FIRST_PARTY |
| R07 | SpotAttention: 4 × 128 selector, 100M tokens at 16K (763 steps), every full-attention layer, dual top-p, English dense parity to 128K on frozen 4B–32B Qwen3/Qwen3.5; non-English untested; no public code | https://arxiv.org/abs/2606.22874 — setup and results | FIRST_PARTY (code absence checked via GitHub/HF search 2026-09-01) |
| R08 | Oracle-Guided Sparse Prefill: frozen-backbone head-collapsed indexer KL-distilled from dense attention mass on Qwen3.5-0.8B/9B, plus an attention-mass top-k oracle | https://arxiv.org/abs/2606.07703 — abstract | FIRST_PARTY (abstract read by the wave-2 novelty refuter) |
| R09 | NoLiMa: GPT-4o 99.3 → 69.7 at 32K when literal overlap is removed | https://arxiv.org/abs/2502.05167 — abstract and main table | FIRST_PARTY (quoted by the wave-2 identification refuter) |
| R10 | Fewer than 5% of attention heads are retrieval heads | https://arxiv.org/abs/2404.15574 — abstract | FIRST_PARTY |
| R11 | RTPurbo: retrieval governed by a low-dimensional subspace; 16-dimensional indexer suffices with a retrieval-head target; fixed top-k inferior to top-p | https://arxiv.org/abs/2605.16928 — abstract | FIRST_PARTY (abstract quoted by the wave-2 identification refuter; full text unread) |
| R12 | MLNeedle: 7–8B instruct models about 0.30 (zh), 0.24 (ar), 0.25 (hi) versus 0.68 (en) at 4K | https://arxiv.org/html/2408.10151 — per-language table | FIRST_PARTY (quoted by the wave-2 identification refuter) |
| R13 | OneRuler: instruction language moves results by up to 20 points | https://arxiv.org/abs/2503.01996 — abstract | FIRST_PARTY |
| R14 | Lost in Compression: the cross-lingual selection gap tracks supervision data, not architecture; budgets matched in the target tokenizer | https://arxiv.org/abs/2608.26175 — abstract | FIRST_PARTY |
| R15 | MGAL: 6 languages, UN reports, position-aware long-context benchmark | https://arxiv.org/abs/2608.20853 — abstract | FIRST_PARTY |
| R16 | ParaDocs: 18 data dirs en-{cs,de,es,fr,hi,hu,id,it,km,lo,my,ne,nl,pl,pt,sv,th,vi}; release filters minimum_size 2, frequency_cutoff 100, lid_cutoff 0.5; card license apache-2.0 | https://huggingface.co/datasets/jhu-clsp/paradocs/tree/main/data and README.md | VERIFIED (dirs and filters re-read by the wave-2 feasibility refuter 2026-09-01) |
| R17 | ParaCrawl text is CC0 | https://paracrawl.eu — license statement | FIRST_PARTY |
| R18 | TED2020 v1 via OPUS: en–zh_cn 3,827 documents / 399,092 pairs / 8,050,948 en tokens; en–ru 3,699 / 386,316; en–ar 3,879 / 403,716; en–ja 3,493 documents; en–ko 3,753 documents | https://opus.nlpl.eu/opusapi/?corpus=TED2020&source=en&target=zh_cn&preprocessing=xml&version=v1 (and sibling queries) | VERIFIED (OPUS API counts re-read by the wave-2 feasibility refuter) |
| R19 | TED Talks text is under CC BY-NC-ND 4.0 (research use, no redistribution of modified text) | https://www.ted.com/about/our-organization/our-policies-terms/ted-talks-usage-policy | UNVERIFIABLE_ACCESS (page not fetched; confirm before the run) |
| R20 | FineWeb-2 @ af9c13333eb981300149d5ca60a8e9d659b276b9 is ODC-By 1.0 and holds all 12 held-out and 7 training language dirs | https://huggingface.co/datasets/HuggingFaceFW/fineweb-2/tree/af9c13333eb981300149d5ca60a8e9d659b276b9 | VERIFIED (wave-2 feasibility refuter) |
| R21 | Belebele @ 7899cdfa4e1e0d733fd77c848e2c273cb1d32be2: CC-BY-SA 4.0; 488 FLORES-200 passages × 122 language variants; 900 questions per variant | https://huggingface.co/datasets/facebook/belebele/tree/7899cdfa4e1e0d733fd77c848e2c273cb1d32be2/data and card | FIRST_PARTY (card) |
| R22 | WMT24++ @ fd7405c06494bc66a57b25f55d217a72f96e60dc: apache-2.0; 55 en→xx document-level human translations with document_id; no Georgian | https://huggingface.co/datasets/google/wmt24pp/tree/fd7405c06494bc66a57b25f55d217a72f96e60dc | VERIFIED (wave-2 feasibility refuter) |
| R23 | FLORES+ is CC-BY-SA 4.0, gated with automatic approval | https://huggingface.co/datasets/openlanguagedata/flores_plus | FIRST_PARTY |
| R24 | TyDi QA GoldP covers ar, bn, en, fi, id, ja, ko, ru, sw, te, th under Apache-2.0 | https://huggingface.co/datasets/google-research-datasets/tydiqa — card | UNVERIFIABLE_ACCESS (not fetched this session; verify language list and license before arm (i) is built) |
| R25 | fla v0.5.2 ships only fla/ops/dsa/naive.py for DSA; parallel_nsa and parallel_nsa_topk take block_indices [B, TQ, H, S] and assert HQ/H at least 16; chunk_gdn is exported | https://github.com/fla-org/flash-linear-attention/blob/main/fla/ops/nsa/parallel.py ; https://github.com/fla-org/flash-linear-attention/tree/main/fla/ops/dsa | VERIFIED (source read via GitHub API by the wave-2 feasibility refuter) |
| R26 | fla GB200 benchmark: chunk_gdn 3.616 ms versus flash_attn 19.960 ms at B=2, T=16384, H=16, D=128 (forward plus backward) | https://github.com/fla-org/flash-linear-attention#benchmarks — README table | FIRST_PARTY |
| R27 | llm.c: GPT-2 124M on 10B tokens in about 90 minutes on 8 × A100 80GB, about 60% MFU | https://github.com/karpathy/llm.c/discussions/481 | FIRST_PARTY |
| R28 | H100 SXM: 989 TFLOPS dense BF16, 3.35 TB/s HBM3 | https://www.nvidia.com/en-us/data-center/h100/ — datasheet | UNVERIFIABLE_ACCESS (values from memory; not fetched) |
| R29 | Discovery image: Image ID sha256:ca32b5c26b92fbe2a7054ae96543cd62928b0493896ec355b869b612022aa9a2; repo digest 127.0.0.1:5000/cotcodec-research@sha256:15d6abc06fa53ab466087a92107da9c58e469615e2f56a683fefd0a7600277f3; labels revision 581ded8df71564b0212d8af5dcd401257aa6a28f, source-tree-sha256 2d960d1a5cf6fd64cdd0baba0a2c752ad6216b8443d741cb7deef9e07d031322, runtime-profile architecture-source-overlay, created 2026-08-16; contents CUDA 12.8.1, torch 2.11.0+cu128, transformers 5.15.0, accelerate, triton; no vllm/peft/fla/flash-attn | fal-h100-01 local registry, docker inspect on 2026-09-01 (spec brief) | VERIFIED (on the host by the spec-phase brief author; no public URL) |
| R30 | fal-h100-01: 8 × H100 80GB, 208 CPUs, 1.7 TB RAM, 21 TB free disk, Docker 28, Slurm 21.08.5 single node, no Pyxis/Enroot | context brief 2026-09-01 (operator inventory) | FIRST_PARTY (operator's own inventory; not re-audited in this session) |
| R31 | Wave-2 feasibility re-derivation of Phase 0a (wave-2 design): 1.88 GPU-h base, 2.35 with 25% reserve, about 18 minutes wall-clock on 8 GPUs at 297 TFLOPS/GPU and 2.0 TB/s | research/gauntlet/2026-09-01-frontier/wave2-result.json — feasibility vote | VERIFIED (independent re-derivation inside this gauntlet from R01–R03, R25–R28) |
| R32 | Phase 0a cost after the wave-3 additions (three target aggregations, fourth E1 condition, cross-lingual dense headroom): 2.33 GPU-h base, 2.9 with reserve, cap 4.0 | this proposal, Cheapest Decisive Pilot table, derived from R01–R02, R27–R28 at an assumed 30% MFU | FIRST_PARTY (derivation; MFU assumed, not measured) |
| R33 | Phase 1 cost after the wave-3 additions: 7.1 GPU-h base, 8.9 with reserve, cap 10.0 | this proposal, Phase 1 table, same inputs | FIRST_PARTY (derivation) |
| R34 | Phase 0b probe: 120 prompts at 8K with a 6 s per-prompt abort threshold on 8 GPUs is 1.6 GPU-h plus at most 0.4 GPU-h weight loading, cap 2.0 | this proposal, derived from R03 (about 360 GB bf16) | FIRST_PARTY (derivation) |
| R35 | Wave-1 novelty search: 9 arXiv, 4 HF-papers, 7 WebSearch queries plus DSA and QSA full text; wave-2 recheck: arXiv query on indexer AND sparse attention AND multilingual/cross-lingual/translation returned MiniMax MSA 2606.13392, FlashMemory 2606.09079, Dynamic Sparse Attention 2603.13430 (none multilingual); HF-papers query returned MGAL only; wave-2 refuter: 13 hostsearch calls, 10 WebSearch, 10 WebFetch | research/gauntlet/2026-09-01-frontier/wave1-verdicts.json and wave2-result.json | VERIFIED (gauntlet records) |
| R36 | Wave-2 judge scores: Reviewer A total 64/100, Reviewer B total 61/100; refuter votes novelty not refuted (0.6), identification refuted (0.72), feasibility not refuted (0.8); blind discrimination different mechanism, prior does not dominate (0.8) | research/gauntlet/2026-09-01-frontier/wave2-result.json — ranked[2] | VERIFIED (gauntlet record) |
| R37 | Wave-1 outcome: killed before judging; novelty not refuted (0.6), identification refuted (0.8), feasibility refuted (0.8) | research/gauntlet/2026-09-01-frontier/wave1-ledger.md — row 2 | VERIFIED (gauntlet record) |
| R38 | Pre-registered design parameters (this proposal): achieved-budget fraction ρ ∈ {6.25%, 12.5%, 25%} with 12.5% primary; fixed k ∈ {512, 1024, 2048}; contexts 8K/16K/32K; λ_x ∈ {0.25, 0.5}; indexer dims 64/128/256; LoRA rank 16; 50M Phase-0 and 100M Phase-1 training tokens (6,104 and 12,208 sequences of 8,192); LoRA controls 60M tokens × 2 seeds | this proposal and experiments/architectures/translation-supervised-sparse-indexer.yaml | FIRST_PARTY (design parameter) |
| R39 | Pre-registered thresholds: adequacy gate 5 points; ξ confirm 10, kill 5; primary recovery 60% of residual ξ_T*; kill K2a 80%, K2b 30%; inertness 1 point; L_perm/L_half kill 80%; L_sem kill 50%; training-free kill 80%; LoRA-specific kill 80%; P3 gain 8 EM points, monolingual within 2, E3 within 0.5; per-language floor 2 points; headroom gates dense cross-lingual EM 40% and sparse floor R^T − 5; 3 needle positions; 3,000/600/1,200/4,000/5,300/2,700/1,500 prompt counts | this proposal, Mechanism and Evaluation sections; the contract YAML | FIRST_PARTY (design parameter) |
| R40 | Power inputs (assumed, not measured): seed-to-seed SD of E1 recall at most 2 points; prompt-level Bernoulli SE at p ≈ 0.5 with 2,000 matched pairs about 1.6 points unpaired, about 1.3 paired; α = 0.01 two-sided; power 0.8; resulting MDE for a two-arm, three-seed contrast about 5.6 points; seed escalation to 5 seeds pre-registered | this proposal, Evaluation section (closed-form normal approximation) | FIRST_PARTY (assumption; no published seed-variance prior for indexer recall exists under the stated coverage) |

## Closest Prior Work

The mechanism sits between two literatures that have never met. On one side,
every learned-indexer paper surfaced (DSA, QSA, SpotAttention, Oracle-Guided
Sparse Prefill, LongCat LSA, MISA, PIVOT, RTPurbo, Self-Indexing KVCache) trains
or replaces the indexer by KL or an oracle derived from the model's own full
attention and evaluates on English-centric long-context suites; none supervises
selection with any external signal and none reports per-language selection.
On the other side, supervised and guided attention in NMT (Liu 2016, Chen 2016,
Garg 2019) and AlignAtt4LLM supervise or select *main* attention heads with
alignment labels; none touches a detached top-k selector of a decoder-only LM.

Oracle-Guided Sparse Prefill (2606.07703) is the closest single object: a
frozen-backbone KL indexer and an attention-mass top-k oracle that separates
budget feasibility from indexer error. That is exactly the monolingual form of
the R^T-versus-indexer decomposition used here; the wave-3 repair cites it as
the precursor and leaves the cross-lingual axis — and the literalness control —
as the only new content of the diagnostic. SpotAttention publishes the frozen
KL-only selector arm (b) at English parity, so the pilot's baseline arm is a
re-implementation of a published method whose non-English behaviour is the open
question. Lost in Compression supplies the audit protocol (achieved-budget
matching in the target tokenizer) but studies prompt compressors. MLNeedle and
OneRuler establish the cross-lingual needle gap on dense softmax transformers
and are the mandatory dense baselines; neither has a selection component to
localize the gap to.

What this leaves open, and what the pilot measures: whether a low-rank ReLU
indexer trained on aggregated attention mass loses the cross-script semantic
subspace that the many-head teacher uses — beyond what the teacher itself
loses, and beyond what a literal-versus-semantic query difference explains.

## Novelty Ledger

| Proposed component | Closest prior | Same | Delta | Confidence |
|---|---|---|---|---:|
| Detached top-k indexer with KL distillation from frozen full attention (arms a, b) | DSA https://arxiv.org/abs/2512.02556 ; SpotAttention https://arxiv.org/abs/2606.22874 ; Oracle-Guided Sparse Prefill https://arxiv.org/abs/2606.07703 | yes | none claimed; this is the re-implemented baseline | 0.95 |
| Indexer-versus-own-target excess gap ξ as the kill statistic | Oracle-Guided Sparse Prefill https://arxiv.org/abs/2606.07703 (attention-mass top-k oracle versus indexer error, monolingual) | partly | cross-lingual axis; both legs non-literal (Belebele question-as-query), literal copy reported as a ceiling; per-language achieved-budget ledger | 0.60 |
| Target-aggregation ladder (head-sum, max-pool, retrieval-head-weighted) as the label-free counterfactual | DSA head-sum https://arxiv.org/abs/2512.02556 ; QSA max-pool https://arxiv.org/abs/2608.30320 ; retrieval heads https://arxiv.org/abs/2404.15574 ; RTPurbo https://arxiv.org/abs/2605.16928 | yes (each aggregation exists) | measuring their per-language selection recall against each other and against the target is not reported by any source | 0.55 |
| Sentence-alignment log-mass loss L_x on the detached indexer, corpus-given labels, main attention untouched | Guided NMT attention https://arxiv.org/abs/1609.04186 , https://arxiv.org/abs/1607.01628 , https://arxiv.org/abs/1909.02074 ; AlignAtt4LLM https://arxiv.org/abs/2606.03967 | partly (loss form) | object (selection indexer of a decoder-only sparse LM), label (corpus sentence alignment on concatenated bilingual documents, no aligner), inference unchanged | 0.60 |
| Information-matched controls: L_perm, L_half, L_sem (monolingual question-to-passage supervision), LM-only and LM+L_x LoRA, with inertness preconditions | Lost in Compression https://arxiv.org/abs/2608.26175 (supervision-data explanation) ; Semantic Hub https://arxiv.org/abs/2411.04986 | no | a pre-registered identification battery for alignment content versus loss form, cross-language mass push, generic semantic sharpening and dense fine-tuning | 0.65 |
| Per-language selection-recall instrument for any DSA/QSA checkpoint, including an inference-only probe of a production QSA indexer | MLNeedle https://arxiv.org/abs/2408.10151 ; OneRuler https://arxiv.org/abs/2503.01996 ; MGAL https://arxiv.org/abs/2608.20853 (behavioural, dense) | no | localizes the cross-lingual long-context gap to the selection component or exonerates it | 0.65 |

Novelty wording: No direct prior art found through 2026-09-01 under the
wave-1 novelty triad (9 arXiv API queries, 4 HF-papers queries, 7 WebSearch
queries, full text of DSA and QSA), the wave-2 rechecks (one arXiv API query,
one HF-papers query) and the wave-2 novelty refuter's 13 hostsearch, 10
WebSearch and 10 WebFetch calls, for an alignment-supervised detached selection
indexer or for any per-language selection audit of a learned sparse indexer.
Coverage holes: 10 of 13 arXiv boolean queries returned HTTP 429; 4 OpenReview
hits unread; Semantic Scholar unavailable; QSA and GLM-5.3 full text not read
for per-language indexer tables. This is a bounded statement, not a global
novelty claim, and it awaits a signed provider-distinct novelty review.

## Mechanism and Falsifiable Predictions

Indexer (token form as DSA; block form as QSA with compress ratio 4), attached
to each sparse layer of a frozen backbone:

```text
I_t(s) = sum_{j=1..H_I} w_{t,j} * ReLU(q^I_{t,j} . k^I_s),   s at most t
S_t    = Top-k_s I_t(s);   the sparse layer attends over S_t only
L_I    = KL( P^T_t || softmax_s I_t(s) ),   P^T_t = aggregation T of the frozen
         layer's full-attention rows;  T in {hs = head-sum (DSA), mp = max-pool
         (QSA), rh = retrieval-head-weighted (heads ranked by copy score)}
```

No gradient reaches the backbone. Translation view: for a document pair
(D_a, D_b) with the corpus's own sentence alignment {(u_i, v_i)}, build
C = [D_b ; SEP ; D_a] and the reverse; for a query token t in sentence u_i define
the aligned key set A(t) = tokens of v_i, mapped to indexer granularity N(A(t)).

```text
L_x   = -(1/|Q|) sum_{t in Q} log sum_{s in N(A(t))} softmax_s I_t(s)
L_I'  = L_I + lambda_x L_x,    lambda_x in {0.25, 0.5}
L_perm: same form, alignment labels permuted within the document
L_half: same form, N(A(t)) replaced by the whole other-language half of C
L_sem : same form, N(A(t)) replaced by the gold passage of a monolingual
        question (TyDi QA GoldP, en/ar/ru/th only), no parallel data, iso-token
```

Evaluation quantities never use alignment labels. Each prompt π = (H, N, p, Q)
has a haystack H in language l_N (FineWeb-2), a needle passage N in l_N (sealed
Belebele passage), a position p, and a query Q. Four conditions share (H, N, p)
and differ only in Q:

```text
ML  mono-literal      Q = a verbatim needle sentence in l_N        (ceiling row only)
MN  mono-non-literal  Q = the Belebele question about N, in l_N    (reference leg)
CS  cross same-script Q = the same question in l_Q, script(l_Q) = script(l_N)
CX  cross cross-script Q = the same question in l_Q, script(l_Q) differs
R_A(cond) = mean over content tokens t of Q and sparse layers of |S_t ∩ N| / |N|,
            A in {indexer, target T};  k = rho * |H| in the model tokenizer
Delta_ind = R_ind(MN) - R_ind(CX);   Delta_T = R_T(MN) - R_T(CX)
xi_T      = Delta_ind - Delta_T            (excess gap, non-literal on both legs)
Lambda    = R(ML) - R(MN)                  (literalness gap; reported, not in xi)
T*        = argmin_T xi_T on development languages, frozen before test
rho_x     = [xi_T* - xi_T*+x] / xi_T*      (recovery by L_x over the best label-free target)
```

The wave-2 ξ used ML as the monolingual leg, so the NoLiMa-style literalness
gap Λ was inside it; the wave-3 repair moves the reference to MN and reports Λ
separately. Because the cross-lingual questions are the human translations of
the same Belebele question, matched pairs differ only in query language.

Why an excess gap is plausible: production indexers are rank-128 ReLU scorers
with 1–4 query heads trained on aggregated attention mass dominated by
same-language matches; the low-rank scorer need not preserve the cross-script
semantic subspace the 16–64-head teacher uses. Whether that is true beyond the
target's own loss and beyond literalness is P1; nobody has measured it.

Falsifiable predictions (each names its counterfactual):

- **P1 (Phase-0 kill screen).** For KL-only indexers (token and block form on
  frozen qwen3-0.6b-base; block form on the 8 full-attention layers of frozen
  qwen3.5-4b), on held-out cross-script pairs at 8K and ρ = 12.5%, after the
  indexer-adequacy gate passes: Δ_ind ≥ 15 points and ξ_T ≥ 10 points for at
  least one target aggregation T and one base, with both legs non-literal.
  Reference: the same indexer on identical prompts with only the question
  language changed; R^T on the same prompts.
- **P2 (primary identification contrast).** On held-out language pairs at
  ρ = 12.5%, (T*)+L_x recovers ρ_x ≥ 60% of the residual ξ_T*, with monolingual
  MN recall within 1 point of (T*) KL-only and E3 within 0.5 points; given the
  inertness preconditions |R_d(MN) − R_b(MN)| ≤ 1 and |R_e(MN) − R_b(MN)| ≤ 1,
  (T*)+L_x beats (T*)+L_perm and (T*)+L_half by at least half of its own
  recovery; and (T*)+L_x beats (T*)+L_sem by at least half of its own recovery
  on held-out cross-script pairs. (c) = head-sum + L_x versus (b) = head-sum
  KL-only is reported as the DSA-style secondary contrast only.
- **P3 (generation endpoint; gated).** Gates: G1 dense cross-lingual TR-NIAH
  exact match ≥ 40% at 8K on the base in question; G2 sparse (T*) KL-only MN
  recall ≥ R^T(MN) − 5 (the sparse floor is not saturated). Given the gates:
  TR-NIAH EM ("output the sentence that follows the sentence whose translation
  is: …", gold answer in l_N) on held-out cross-script pairs at 8K–16K,
  (T*)+L_x − (T*) ≥ 8 points; monolingual within 2 points; no training-free
  control at matched achieved budget (SpotAttention dual top-p, larger k at
  matched measured latency, PIVOT-style re-scoring, NSA pooled-key selection,
  SWA plus sinks at matched KV bytes) recovers ≥ 50% of that gain; the
  L_x-specific dense gain (k) − (j) recovers under 50%; and any (T*)+L_x score
  above dense is claimed only if the oracle needle-block arm shows the same
  sign (otherwise it is generic forced-selection denoising, as QSA already
  shows in production). A needle-absent control bounds parametric recall.
- **P4 (exploratory, not load-bearing).** Sparse-with-L_x minus dense on
  cross-lingual E2 ≥ 0 with oracle-selection and random-plus-needle controls.
- **P5 (Phase 2, outside this contract).** From-scratch 60–125M 3:1 GDN plus
  sparse-global hybrid with a fertility-balanced BPE shows a cross-script gap
  ≥ 2× the same-script gap for KL-only and ≤ 1.3× with L_x at equal BPB.

Kill conditions (falsifiers; each ends or re-frames the line as stated):

1. **K1 localization negative.** With the adequacy gate passed, ξ_T ≤ 5 points
   for every T on both bases and both indexer forms: the indexer adds no
   cross-lingual bottleneck beyond its target; publish and stop.
2. **K2a target-aggregation artifact (Judge B form).** A label-free de-diluted
   target recovers ≥ 80% of the head-sum gap, ξ_T* ≤ 0.2 · ξ_hs: the gap is a
   DSA-recipe artifact that QSA-style or retrieval-head targets remove for
   free; the L_x line stops and the result is published as a recipe finding.
3. **K2b weak alignment effect (Judge A form).** ρ_x under 30% on held-out
   pairs: alignment content adds little beyond the best label-free target.
4. **K3 loss form, not content.** Inertness holds and (T*)+L_perm or
   (T*)+L_half reaches ≥ 80% of (T*)+L_x's recovery: re-frame as a
   mass-concentration regularizer paper or stop. If inertness fails, the
   loss-form question is reported as unresolved, not as a pass.
5. **K4 generic semantic sharpening.** (T*)+L_sem reaches ≥ 50% of (T*)+L_x's
   recovery on held-out cross-script pairs: parallel data is not the active
   ingredient; redirect to monolingual semantic supervision.
6. **K5 training-free parity.** Any training-free control at matched achieved
   budget recovers ≥ 80% of the E2 gain.
7. **K6 not selection-specific.** (k) − (j) ≥ 80% of (T*)+L_x − (T*) on E2.
8. **K7 proxy-only.** E1 gains without E2 gains, or gains confined to
   in-training languages.
9. **K8 language harm.** Any held-out language's MN or CX recall drops over 2
   points versus (T*), or E3 drops over 0.5 points.
10. **K9 headroom.** G1 fails on both bases: the E2 claim is withdrawn, not
    rescued by a larger model inside this contract; only E1/ξ are reported. G2
    fails on a base: E2 arm contrasts on that base are reported as floor-bound
    and carry no claim.

Adequacy gate (bug detector and false-kill guard): English ML indexer recall
within 5 points of R^T(ML) on each base; if it fails, extend Phase-0 training
once to 100M tokens inside the cap; if it still fails, Phase 0 is inconclusive
and is reported as such, never as K1. Indexer recall above its own target on ML
(ξ under 0 on the literal leg) is pre-registered as a bug tell to investigate,
not a result to report.

Strongest counter-argument (devil's advocate, checkpoint 1). The cross-lingual
gap, wherever it lives, is a property of the frozen model's attention mass; a
KL-distilled indexer is a lossy compression of that mass, and every compression
loses the diffuse tail first. So ξ is a compression artifact that the right
target (max-pool, retrieval heads, or simply a wider indexer) removes with no
labels, and alignment supervision is a costly way of buying what a better
distillation target buys for free — while the labs that matter train their
indexers inside continued pretraining on about a trillion multilingual tokens,
where a 50M-token frozen retrofit says nothing. The design answers by making
that argument an arm and a kill condition (K2a, the dim ladder, Phase 0b) rather
than a footnote: if it is right, the pilot says so cheaply.

What's missing. No production indexer is measured except in the optional
120-prompt probe; no continued-pretraining arm; QSA/DSA/GLM per-language tables
unread; no independent replication of SpotAttention's parity; no seed-variance
prior for indexer recall; TyDi QA language list and license unverified this
session; the TED usage-policy page unread; the H100 datasheet values from
memory; the "class" in the claim is a retrofit population until Phase 0b or
Phase 2 speaks.

## Cheapest Decisive Pilot

Phase 0 CPU doctors (no GPU; attested before any job is submitted): (i)
bilingual-concatenation builder from ParaDocs/TED2020 with the sentence-alignment
map, L_x mass accounting (label mass per query in (0, 1]) and permutation
sensitivity (L_x on true versus permuted labels differs on synthetic data);
(ii) NIAH/TR-NIAH builder for the four conditions with a per-prompt
achieved-token ledger (Qwen tokenizer), balanced needle positions, and exact
50-gram plus MinHash (Jaccard ≥ 0.8) dedup of FineWeb-2 haystacks and training
documents against Belebele/WMT24++/FLORES+ texts with removal counts logged;
(iii) synthetic bilingual toy (two vocabularies related by a fixed permutation;
random rank-32 ReLU indexer versus a full softmax teacher) reproducing an excess
cross-vocabulary gap and its repair by L_x — a sanity check, not evidence;
(iv) a 20-prompt indexer-versus-target recall smoke run in the rebuilt pinned
container under a Slurm dry-run, and a Q-head padding or gather path for fla
parallel_nsa (both bases fail its HQ/H ≥ 16 assertion; token-form selection
needs the gather path regardless).

Phase 0a GPU kill screen (the pilot of record; one Slurm job; ≤ 4 GPU-h):

- Bases (frozen): qwen3-0.6b-base = Qwen/Qwen3-0.6B-Base @
  da87bfb608c14b7cf20ba1ce41287e8de496c0cd (indexers on all 28 layers);
  qwen3.5-4b = Qwen/Qwen3.5-4B @ 851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a
  (indexers on the 8 full-attention layers 3, 7, …, 31 — the production
  placement). The registry id qwen3.5-4b is the post-trained checkpoint; the
  preferred base is Qwen/Qwen3.5-4B-Base, which is not registered, so the
  contract uses qwen3.5-4b and relabels it as post-trained in every receipt
  until the Base is registered.
- Indexers: three target aggregations (hs, mp, rh) × two forms (token 4 × 128;
  block 4 × 128, 1 kv head, compress 4) × 3 seeds = 18 per base, all trained in
  one forward stream of the frozen teacher (no gradient into the backbone, so
  all arms share one teacher pass).
- Data: 50M tokens = 6,104 sequences × 8,192; half bilingual concatenations,
  half monolingual FineWeb-2 in the training languages.
- Eval: E1 and R^T on 4,000 sealed prompts (Belebele needles in held-out
  languages, four conditions, 3 positions) at 8K/16K/32K with dense rows
  computed only for query tokens; adequacy gate on English ML; dense E2
  headroom, monolingual and cross-lingual, on 1,200 prompts per base (G1).
- T* is chosen on development languages (in-training cross-script pairs th, hi,
  km, zh, ar) and frozen before any held-out number is read.

Budget arithmetic (H100 SXM 989 TFLOPS dense BF16 and 3.35 TB/s from the
datasheet; **assumed 30% MFU = 297 TFLOPS and 2.0 TB/s effective**, half the
about 60% MFU llm.c reports; MFU is measured by the first job and the budget is
re-verified before Phase 1 is submitted):

| item | work | GPU-h |
|---|---|---:|
| teacher forward, 0.6B, 50M tokens at 8K | 1.4e17 FLOP | 0.13 |
| attention-probability materialization for the KL targets, 28 layers | 7.3e14 B | 0.10 |
| teacher forward, 4B hybrid, 50M tokens (8 dense-attention layers plus fla chunk_gdn) | 4.0e17 FLOP | 0.37 |
| materialization, 8 layers | 2.1e14 B | 0.03 |
| 18 indexers per base, forward plus backward, plus score-matrix traffic | about 2.2e17 FLOP + 1.5e15 B | 0.37 |
| E1 eval, 4,000 prompts × {8K, 16K, 32K}, both bases, all indexers attached | about 1.2e18 FLOP | 1.13 |
| dense E2 headroom, monolingual plus cross-lingual, 1,200 prompts × 2 bases | 2e17 FLOP | 0.20 |
| **subtotal** | | **2.33** |
| × 1.25 reserve | | **2.9** |
| **cap (Slurm/IO overhead, one rerun)** | | **4.0** |

Decision: P1 holds (ξ_T ≥ 10 for some T and base, adequacy gate passed) →
Phase 1. K1 → stop and publish the localization negative. In between →
Phase 1 with the recovery denominator set to the observed ξ_T* (pre-registered
rule; ρ_x is relative by construction).

Phase 1 identification (gated on P1; ≤ 10 GPU-h including reserve; same
shared-teacher design; 0.6B at 100M tokens = 12,208 × 8K, block form unless
noted, 3 seeds): (a) KL-T*, monolingual contexts; (b) KL-T*, bilingual
concatenations — **primary label-free counterfactual**; (b′) KL-hs bilingual
and (b″) the remaining aggregation, completing the label-free ladder for K2a;
(c) KL-T* + L_x — **primary treatment**; (c′) KL-hs + L_x (DSA-style
secondary); (d) KL-T* + L_perm; (e) KL-T* + L_half; (i) KL-T* + L_sem
(TyDi QA GoldP question-to-passage supervision in en/ar/ru/th only, iso-token,
excluding every held-out evaluation language); (h) indexer dim ladder 64/256
for (b) and (c); token form for (b) and (c) only. Replicate (b), (c), (d), (i)
× 2 seeds on qwen3.5-4b's 8 full-attention layers. Separate small jobs on
qwen3-0.6b-base: (j) dense + LM-loss-only LoRA (rank 16 on q, k of all layers,
bilingual concatenations, 2 seeds × 60M tokens) and (k) dense + LM loss +
λ L_x on the head-summed main attention (same budget) — (k) − (j) is the
L_x-specific dense effect. Training-free controls at eval only: SpotAttention
dual top-p, larger k at matched measured latency (fla kernel timing with
warm-up), PIVOT-style query-group re-scoring, NSA pooled-key selection, SWA
plus sinks at matched KV bytes, oracle needle-block inclusion with random fill,
random-plus-needle, needle-absent.

| item | GPU-h |
|---|---:|
| teacher stream 0.6B, 100M tokens, plus materialization | 0.5 |
| 6 token-form plus 39 block-form indexers, forward plus backward plus score traffic | 0.7 |
| qwen3.5-4b replicate, arms (b), (c), (d), (i) × 2 seeds, 100M tokens | 0.9 |
| (k) dense + LM + L_x LoRA, 2 seeds × 60M tokens, with materialization | 1.2 |
| (j) dense + LM-only LoRA, 2 seeds × 60M tokens, no materialization | 0.8 |
| E1 eval, 5,300 (0.6B) plus 2,700 (4B) prompts, four conditions, shared forward | 1.1 |
| E2 eval, 27 configurations (18 learned, 7 training-free, 2 LoRA) × 1,500 prompts ≤ 16K, sparse kernel | 1.9 |
| subtotal 7.1; × 1.25 = 8.9; **cap 10.0** | |

Phase 0b (optional; hard cap 2 GPU-h; runs whether Phase 0a passes or kills;
external validity only, descriptive): inference-only probe of the production
QSA indexer in Qwen/Qwen3.8-Flash-Next @ de4b8e4d43b917e7706784d8bb445c9af86a3540
(about 360 GB bf16 across 8 × H100 with transformers device_map); hook the
indexer scores and the same layer's dense rows for the query tokens; E1/R^T on
120 sealed prompts at 8K across the four conditions; a 20-prompt timing probe
must show ≤ 6 s per prompt or the job aborts and records throughput. At 120
prompts the recall SE is about 4.5 points, so the probe is descriptive and
never promotes or kills. GLM-5.3-Flash ships FP8 (about 321 GB) and would fit
the node; it is a future option, not part of this contract.

Phase 0a (4) + Phase 1 (10) + Phase 0b (2) = **16 GPU-h**. Phase 2 (new
contract): from-scratch 60–125M 3:1 GDN plus QSA-style sparse-global hybrid
with a fertility-balanced BPE, about 30 GPU-h; QSA-style continued pretraining
of qwen3.5-4b, about 170 GPU-h. Tinker is not used (no indexer access; key
absent).

## Controls, Baselines, and Ablations

- Dense full-attention teacher as reference bound; R^T measured directly for
  each aggregation (hs, mp, rh) — the KL ceiling; T* frozen on development
  languages.
- Strongest label-free counterfactual (T*) KL-only on the identical bilingual
  concatenations (primary), with the DSA head-sum recipe as the secondary
  counterfactual and the full aggregation ladder for K2a.
- Same-loss-form controls with inertness preconditions: L_perm (permuted
  labels), L_half (other-language half); pre-registered inertness |d − b| ≤ 1
  and |e − b| ≤ 1 on MN before either comparison counts.
- Information-matched monolingual semantic supervision L_sem (TyDi QA GoldP,
  training languages only, iso-token).
- Dense LoRA pair: LM-only (j) and LM + L_x (k), rank 16, matched tokens and
  data; (k) − (j) isolates the L_x-specific dense effect.
- Budget matching: achieved-budget fraction ρ in the model tokenizer (primary),
  fixed absolute k, needle-fertility-scaled k; SpotAttention dual top-p
  (mass-matched); per-prompt achieved-token ledger; haystack language equals
  needle language.
- Training-free selection at matched achieved budget: larger k at matched
  measured latency, PIVOT-style re-scoring, NSA pooled-key selection, SWA plus
  sinks at matched KV bytes.
- Attribution and leakage: oracle needle-block selection with random fill,
  random-plus-needle, needle-absent (parametric recall), two-forward-pass
  prefix-invariance audit, needle-position stratification, per-language
  floor, English RULER-style E3 non-regression, permutation-controlled MC
  scoring for the Belebele secondary.
- Cross-lingual dense baselines: MLNeedle and OneRuler protocols on both bases
  (mandatory per the verification-pass corrections).
- Literalness: ML ceiling row and Λ reported for indexer and target.
- Capacity: indexer dim ladder 64/128/256, iso-parameter otherwise; token
  versus block form.
- Iso-token and iso-order across all arms (one teacher stream), held-out
  languages never seen by L_x or L_sem, both query directions primary.

## Evaluation, Statistics, and Leakage Checks

Protocols followed: .claude/skills/experimental-design/SKILL.md,
.claude/skills/statistical-power/SKILL.md, and the ARS statistical reporting
standards (effect sizes with intervals, paired/clustered errors, multiplicity,
assumption checks).

Endpoints. E1: needle-token selection recall R_A(cond) per condition, base,
indexer, layer and language, with R^T; ξ_T, Λ, ρ_x as defined. E2: TR-NIAH exact
match (gold answer, answer language fixed to l_N in every condition so
answer-language effects cancel), plus Belebele cross-lingual MC
(permutation-controlled, chance 25%) as a descriptive secondary. E3: English
RULER-style NIAH/multi-key at the same k, and each language's own MN condition.
Primary endpoint of record: the E1 recall gain of (T*)+L_x over (T*) on
held-out cross-script pairs at ρ = 12.5%, in points, required to be ≥ 6 points
and ≥ 60% of ξ_T*.

Minimum worthwhile effect. The confirmatory effect is 60% of the residual gap;
with the P1 gate at ξ_T* ≥ 10 that is ≥ 6 recall points, which is also the
smallest per-language repair a deployment would notice at k = 12.5% of an 8K
haystack (about 60 selected needle tokens of a Belebele passage). Three points
is the reporting floor for secondary contrasts, not the decision threshold.

Noise estimate (assumed, marked unknown). No source reports seed variance of
indexer selection recall. Assumption: seed-to-seed SD of E1 recall ≤ 2 points
(SpotAttention and DSA report single runs). Prompt-level noise: Bernoulli with
p ≈ 0.5 gives SE ≈ 1.6 points for an unpaired difference of two 2,000-prompt
means and ≈ 1.3 points paired, well below the seed component.

Resulting sample and seed count (closed form, normal approximation). Seed-level
SE of an arm mean = 2/√3 ≈ 1.15 points; SE of a two-arm difference ≈ 1.63
points; MDE at α = 0.01 two-sided and power 0.8 = (2.576 + 0.842) × 1.63 ≈ 5.6
points. The 6-point primary effect is therefore at the edge of detectability
with three seeds, and a 3-point effect is not detectable — which is why the
decision threshold is 6, not 3. Pre-registered seed escalation: if the Phase-0
seed SD of ξ exceeds 2 points, Phase 1 runs block-form arms with seeds
[42, 43, 44, 45, 46] (each block-form indexer costs about 0.02 GPU-h) and the
4B replicate stays at 2 seeds and is reported as descriptive. The ξ kill screen
itself needs only to separate ≤ 5 from ≥ 10: with SE(ξ) ≈ 1.15 points the 99%
half-width is about 3 points, leaving the two decision regions disjoint; the
in-between band is pre-registered as inconclusive.

Randomization and blocking. Seeds 42/43/44 set indexer initialization, LoRA
initialization and the seeded shuffle that assigns haystack documents and
needle positions to prompts; the same assignment is used for every arm (blocked
by prompt). All indexers of one base train in one job from one teacher stream,
so data order and wall-clock are identical across arms (blocked by design; no
arm-versus-time confound). The 4B replicate, (j) and (k) are separate Slurm
jobs whose submission order is drawn by a seeded coin and recorded. Needle
positions are balanced within language and condition. Evaluation prompt order
is reshuffled per seed; MC option order is permuted per prompt.

Analysis and reporting. Unit of analysis: the matched prompt (same H, N, p;
query language varied), clustered by Belebele passage id (every language
variant of a passage shares one cluster and one split) and by seed. Effects in
recall or EM points with 99% (primary) and 95% (secondary) paired
passage-cluster bootstrap intervals; per-seed values and per-language values
always reported; assumption check by comparing bootstrap and normal intervals
and reporting the passage ICC. Multiplicity: one primary contrast; Holm within
the kill-condition family and within per-language secondaries; the ML ceiling,
Λ, Belebele MC and Phase 0b are descriptive. Non-significant results are
reported in full.

Leakage. Belebele passage ids are split once (25% development, 75% sealed test)
before any run; held-out languages (ja, ko, bn, ta, el, he, ka cross-script;
id, tr, sw, nl, it same-script) never appear in L_x, L_sem or LoRA training;
TyDi QA's bn/ja/ko/sw/id portions are excluded; exact 50-gram plus MinHash
dedup of all training and haystack text against all evaluation text with
counts in the run receipt; needle-absent control bounds parametric recall;
prefix-invariance audit; the achieved-token ledger is published per prompt and
per language.

## Compute and Reproducibility

Immutable discovery image (the only real image; exists on fal-h100-01 as of
2026-09-01): repo digest
`127.0.0.1:5000/cotcodec-research@sha256:15d6abc06fa53ab466087a92107da9c58e469615e2f56a683fefd0a7600277f3`
; Image ID sha256:ca32b5c26b92fbe2a7054ae96543cd62928b0493896ec355b869b612022aa9a2;
labels org.opencontainers.image.revision=581ded8df71564b0212d8af5dcd401257aa6a28f,
source-tree-sha256=2d960d1a5cf6fd64cdd0baba0a2c752ad6216b8443d741cb7deef9e07d031322,
runtime-profile=architecture-source-overlay, created 2026-08-16. Contents: CUDA
12.8.1, torch 2.11.0+cu128, transformers 5.15.0, accelerate, triton; **no vllm,
peft, fla or flash-attn**. The pilot cannot run in this image: it needs a
rebuilt image containing the new harness code (concatenation and TR-NIAH
builders, indexer trainer, selection-recall probe), fla ≥ 0.5.2 (Triton
parallel_nsa, chunk_gdn), peft for the LoRA controls, datasets, and the
Q-head padding or gather path, re-pinned by digest and recorded in the
contract's execution.container_image before enablement. The discovery digest is
cited so that the provenance chain has a real anchor; it must not be used for
the pilot as-is.

Launch (the wrapper validates the manifest and emits the `sbatch` call):

```text
uv run python scripts/submit_docker_research_job.py \
  experiments/architectures/translation-supervised-sparse-indexer.yaml --dry-run
uv run python scripts/submit_docker_research_job.py \
  experiments/architectures/translation-supervised-sparse-indexer.yaml
# emitted: sbatch --gpus=8 --time=04:00:00 --signal=USR1@300 --job-name=tssi-phase0a ...
```

seeds: [42, 43, 44]
gpu_hours: 16

Phase caps: Phase 0a 4, Phase 1 10, Phase 0b 2 GPU-h on 8 × H100 80GB (one
node; Slurm 21.08.5, single node, no Pyxis — the publication lane needs
cgroup-v2 Slurm plus Pyxis, so results from this node are pilot receipts, not
publication receipts). Checkpoints: atomic writes every 15 minutes to
/home/kevin/cotcodec-runs/translation-supervised-sparse-indexer/phase-{0a,1,0b}/seed-{42,43,44}/;
SIGUSR1 triggers a checkpoint and clean exit; every phase must pass a fresh-job
continuation equivalence test (resume from checkpoint reproduces the next
logged metric to tolerance) before its numbers count. Artifacts: model and data
license receipts with immutable revisions; passage-id split manifest, dedup
report and achieved-token ledger; indexer weights per arm and seed; E1/E2/E3
receipts per prompt; kernel timing logs; the K2a aggregation ladder; MFU
measurement from the first job; the dry-run JSON; the container smoke and Slurm
attestations. Cost ceiling: 16 GPU-h on the owned node; dollars=40 covers
Hugging Face and OPUS transfer and storage only; no API spend. Preemption: the
node is not preemptible, but jobs must still survive SIGUSR1 plus fresh-job
resume because the harness requires it.

## Safety, Data Rights, and Monitorability

Monitorability. The selection set S_t is an inspectable retrieval trace;
per-language selection recall becomes an audit instrument for sparse models,
including detection of cross-lingual prompt injection carried by a
foreign-script block that the indexer over- or under-selects. There is no
chain-of-thought effect. Monitored failure modes (K8): under-selection of any
language and over-selection of the other-language half in bilingual prompts
(E3 regression and a bilingual-distractor test in which the other-language
half is irrelevant).

Data rights. ParaCrawl text CC0 with ParaDocs annotations apache-2.0; TED2020
text under TED's CC BY-NC-ND 4.0 usage policy (non-commercial research, no
redistribution of modified text; the policy page was not fetched this session
and must be confirmed before the run); FineWeb-2 ODC-By 1.0; Belebele and
FLORES+ CC-BY-SA 4.0; WMT24++ apache-2.0; TyDi QA reportedly Apache-2.0
(unverified this session); Qwen3-0.6B-Base and Qwen3.5-4B apache-2.0;
Qwen3.8-Flash-Next qwen-community-1.0 (non-standard; review before publishing
probe numbers). General Translation document pairs are under client contract,
not redistributable, and not required by any prediction; the license of any
such parallel data used as an upgrade is unknown to this proposal and must be
recorded per pair before use. No kernel-level delta-rule contribution, so the
NVIDIA gated-delta-network and Google compressive-memory patent flags do not
apply.

Red lines (stop and report): any evaluation quantity computed from alignment
labels; any held-out language entering training data; publication of TED- or
GT-derived text; over 5% regression on E3 or any per-language recall floor
breach that is not reported; any Phase 0b number published before the
qwen-community-1.0 review.

### Integrity gate

Protocol: scratchpad ext/ars/academic-pipeline/references/ai_research_failure_modes.md
(seven modes; status per mode for this proposal at the spec stage).

1. Implementation bug passing self-review — INSUFFICIENT EVIDENCE by
   construction (nothing has run). Mitigations pre-registered: CPU doctors
   (mass accounting, permutation sensitivity, synthetic toy), the adequacy
   gate (a broken indexer fails English ML recall), the bug tell (indexer above
   its own target), receipts with exit code and warning count for every number.
2. Hallucinated citation — CLEAR at this stage: every source in the claim
   registry has a URL and a status; two ids were corrected in wave 3 (RTPurbo
   2608.26449 → 2605.16928) or added (2606.07703); unopened items are marked.
3. Hallucinated experimental result — CLEAR: no experimental number is
   reported; all numbers are sourced facts, design parameters or derivations
   labelled as such.
4. Shortcut reliance — the wave-3 repair exists for this mode: literalness
   (MN reference, Λ), target aggregation (T*, K2a), loss form (L_perm/L_half
   with inertness), semantic sharpening (L_sem), bilingual exposure (b),
   token budget (achieved-budget ρ), parametric recall (needle-absent),
   forced-selection denoising (oracle-sign rule). Flagged for Stage-3 review.
5. Bug reframed as insight — the only pre-registered "surprise" is ξ_T ≥ 10;
   it counts only if the adequacy gate, the synthetic toy and the aggregation
   ladder are mutually consistent, and never on the literal leg alone.
6. Methodology fabrication — CLEAR: methods are stated in the future tense;
   run configs, revisions and split hashes are receipts, not prose; every
   configuration number comes from a Hugging Face config, not from a run.
7. Frame-lock — SUSPECTED and managed: the wave-1 frame ("alignment supervision
   fixes indexers") has been demoted twice; the load-bearing claim is now the
   diagnostic, K2a can end the alignment line, and the negative-result section
   commits to publishing the localization negative or the recipe finding.

## Negative-Result Value

K1 (ξ ≤ 5 everywhere): the cross-lingual long-context gap in sparse models is
inherited from attention mass, not from the selection component — the first
component-level localization of the gap MLNeedle, OneRuler and MGAL describe,
plus a portable per-language selection-recall instrument for any DSA/QSA
checkpoint. K2a: a de-diluted target aggregation closes the gap without labels —
a free recipe finding for every sparse-attention lab and a direct comparison of
the DSA and QSA target choices on a dimension neither reports. K2b or
(b) ≈ (c): bilingual document exposure alone repairs indexers. K3: a
mass-concentration regularizer, not alignment content, is what indexers need.
K4: monolingual semantic supervision does the work — parallel data is not the
active ingredient, which redirects the program away from its unique asset and
is worth knowing early. K6: alignment supervision is a generic attention fix,
not selection-specific. The Λ row is publishable on its own as the first
literalness-versus-language decomposition for learned selectors. Phase 0b
reports whether a production QSA indexer agrees with the retrofit result
either way. Every branch yields a receipt the field lacks; the pilot is
information-dense per GPU-hour precisely because most branches end the line.

## Preflight Doctors

| Doctor | Status | Evidence | Remediation |
|---|---|---|---|
| Source | PASS-candidate | Cell notes: research/gauntlet/2026-09-01-frontier/wave1-candidates.md (inventor merge), wave1-verdicts.json, wave1-ledger.md row 2, wave2/translation-supervised-sparse-indexer.md (repair note), wave2-result.json ranked[2] (refuter votes, blind discrimination, two judges), wave2-ledger.md row 3; sweep synthesis §1 A–H and §5 coverage; 44 URLs in this proposal, 40 on primary domains | Archive hashed source snapshots and query logs in the evidence bundle; the bundle does not exist yet |
| Citation | PASS-candidate | Claim registry R01–R40 per ext/ars/academic-pipeline/references/claim_verification_protocol.md; every number has a URL or a labelled derivation; first-party items marked; two UNVERIFIABLE_ACCESS licence rows (R19, R24) and one datasheet row (R28) flagged | Fetch the TED policy page, TyDi QA card and H100 datasheet before enablement; run an independent line-by-line audit |
| Novelty | PASS-candidate | Wave-2 refuter did not refute (0.6); blind discrimination: different mechanism, prior does not dominate (0.8); ledger with bounded wording; 2606.07703 added as the monolingual precursor | Signed provider-distinct novelty review; read the 4 unread OpenReview hits and the QSA/GLM full text |
| Design | PASS-candidate | Contract experiments/architectures/translation-supervised-sparse-indexer.yaml passes validate_architecture_experiments.py; wave-3 identification re-registration (non-literal ξ, T* counterfactual, inertness, L_sem, LoRA pair, headroom gates, oracle sign) | Re-judge after the re-registration; implement the CPU doctors |
| Compute | FAIL | No real model loop, benchmark adapter, container smoke run or Slurm dry-run is attested; the only real image lacks fla/peft; MFU assumed; fla parallel_nsa head-count assertion unresolved | Build the harness code, rebuild and re-pin the image, run the 20-prompt smoke and the dry-run, measure MFU, then set execution.enabled |
| Safety | PASS-candidate | Monitorability, data rights (including unknown licence for any GT parallel data and unverified TED/TyDi QA statements) and red lines stated; integrity gate answered for all seven modes | Runtime evidence: bilingual-distractor test, per-language floor receipts, licence confirmations |

## Independent Adversarial Reviews

Reviewer A: FAIL | provider=anthropic | model=claude | run_id=wave2-judge-A-2026-09-01 | artifact=research/gauntlet/2026-09-01-frontier/wave2-result.json (internal preliminary, NOT provider-distinct, unsigned; preliminary total 64/100)

Reviewer B: FAIL | provider=anthropic | model=claude | run_id=wave2-judge-B-2026-09-01 | artifact=research/gauntlet/2026-09-01-frontier/wave2-result.json (internal preliminary, NOT provider-distinct, unsigned; preliminary total 61/100)

Both reviews are internal gauntlet judges from the same provider and are not
Ed25519-signed by a trusted attestor; the accepted score is therefore capped
at 89 and the proposal is not pilot-ready regardless of content. Judges also
completed the ARS criterion-bound form (calibration NOT_CALIBRATED); their
fatal_defect and highest_impact_fix texts are recorded in wave2-result.json and
are the sole source of the wave-3 change.

## Scorecard

| Dimension | Reviewer A | Reviewer B | Defect/evidence |
|---|---:|---:|---|
| Question and strategic fit | 7 | 7 | Empty axis confirmed by every sweep cell; class claim still reads a retrofit population until Phase 0b or Phase 2 |
| Primary-source evidence | 8 | 8 | 44 URLs; 2606.07703 was missing in wave 2 (added); QSA/GLM per-language tables unread |
| Defensible novelty delta | 5 | 5 | Loss is a transfer of guided NMT attention; delta rests on the untested diagnostic; coverage cap 74 until OpenReview and full texts are read |
| Mechanism and falsifiability | 7 | 6 | Wave-2 ξ conflated literalness with language; wave 3 moved the reference leg to MN and reports Λ |
| Controls and causal identification | 4 | 4 | Wave-2 counterfactual was the weakest target (head-sum); wave 3 re-registers T*, inertness, L_sem, LoRA pair, headroom gates, oracle sign — unjudged |
| Evaluation and statistics | 5 | 5 | Wave 2 had no power/CI/paired-SE specification; wave 3 adds a closed-form MDE (5.6 points at 3 seeds) and seed escalation |
| Feasibility and information per GPU-hour | 8 | 7 | Independently re-derived 1.88 GPU-h base for wave-2 Phase 0a; parallel_nsa head-count assertion, 0b threshold and post-trained 4B label fixed in wave 3 |
| Reproducibility and artifact contract | 6 | 6 | No container smoke, Slurm dry-run or model-loop attestation; only image lacks fla/peft; cap 79 |
| Safety, data rights, and monitorability | 8 | 7 | TED and TyDi QA licence statements unverified this session; GT data licence unknown and stated |
| Independent adversarial review quality | 6 | 6 | Two internal same-provider judges, unsigned; cap 89 |
| **Total** | **64** | **61** | Lower total (61) is authoritative; caps 74 (coverage), 79 (compute attestation), 89 (no provider-distinct signed review) apply |

## Iteration Log

| Wave | Score | Highest-impact defect | Change | Result |
|---:|---:|---|---|---|
| 1 | 0 (killed) | Identification refuted (0.8): aligned-block recall equalled the training label; retrofit-versus-architecture and token-budget confounds; external aligner asymmetry. Feasibility refuted (0.8): no parallel data in the repo, NumPy-only doctor, uncosted evaluation. See research/gauntlet/2026-09-01-frontier/wave1-ledger.md row 2 | None in wave 1 (killed before judging) | Killed; novelty not refuted (0.6), so admitted to wave 2 with a repair owner |
| 2 | 61 | Judges' shared fatal defect: the pre-registered counterfactual for every L_x claim was the head-sum KL arm, the weakest target aggregation in the class the candidate claims to fix, while ξ compared a verbatim-copy monolingual query with a zero-overlap cross-lingual query | Ten identification and five feasibility repairs (sealed non-label endpoints, attachment-capability scope, achieved-budget k, R^T and ξ, corpus-given labels, no aligner, public data plan, shared-teacher budget, Tinker removed) per wave2/translation-supervised-sparse-indexer.md | Judged 64/61 (lower authoritative 61), ranked 3 of 4, cap 89; identification still refuted (0.72) |
| 3 | 61 (unjudged since the change) | Same defect, as the judges' union highest_impact_fix | One repair — identification re-registration: (1) both ξ legs non-literal (Belebele question-as-query in l_N as the reference; literal copy is a ceiling row; Λ reported); (2) strongest label-free target T* chosen in Phase 0 on development languages becomes the primary counterfactual; K2a (de-diluted target recovers ≥ 80% of ξ_hs) and K2b (L_x recovers under 30% of residual ξ_T*) registered; (c) versus (b) demoted to a DSA-style secondary; (3) inertness preconditions |d − b| ≤ 1 and |e − b| ≤ 1 before L_perm/L_half count; (4) information-matched L_sem arm, LM-only LoRA arm (j) so (k) − (j) isolates the dense L_x effect, headroom gates G1 (dense cross-lingual EM ≥ 40%) and G2 (sparse floor ≥ R^T − 5), oracle-sign rule and needle-absent control on P3; (5) 2606.07703 cited as the monolingual precursor of the ξ decomposition, RTPurbo id corrected to 2605.16928, indexer-adequacy gate, Q-head padding or gather path for parallel_nsa, Phase 0b threshold 6 s with 120 prompts at a 2 GPU-h cap, qwen3.5-4b relabelled post-trained with Qwen3.5-4B-Base named as the unregistered preferred base; budget re-derived to 4 + 10 + 2 = 16 GPU-h | Pending re-judging; not pilot-ready (Compute FAIL, no evidence bundle, no signed reviews) |

The evidence bundle evidence/translation-supervised-sparse-indexer/bundle.json
does not exist yet. Until the hashed source snapshots, query logs, container and
Slurm attestations, two Ed25519-signed provider-distinct reviews and the
hash-chained audit JSONL exist below that directory and match their recorded
SHA-256 hashes, the deterministic doctor returns FAIL and the accepted score is
0; a prose PASS cannot score itself upward.
