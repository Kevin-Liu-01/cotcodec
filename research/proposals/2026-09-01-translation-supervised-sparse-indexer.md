# Research Direction: Translation-Supervised Sparse Indexer

**Status:** draft; wave-5 executable Phase-0 doctor (NumPy, PASS) plus decision-rule, partition and lambda_x re-registration applied; not pilot-ready
**Owner:** Kevin Liu
**Source cutoff:** 2026-09-01
**Coverage limits:** WebSearch budget exhausted mid-sweep; arXiv API, Semantic Scholar and Jina blocked from this Mac (arXiv reached only through the H100-host relay, and 10 of 13 boolean queries returned HTTP 429); OpenReview forums behind browser verification (4 hits unread); no ACL Anthology full text, patents or Chinese-language sources beyond the verification pass; QSA full text (arxiv.org/html/2608.30320) read in wave 4 only through §3.2 where the fetched page truncated, GLM-5.3 and SpotAttention full text still not read for per-language indexer tables; nothing executed on the H100 node or on Tinker by this direction (the NumPy Phase-0 doctor ran on the Mac only, on synthetic cases); no parallel corpus exists in the repository (the governance inventory research/data/gt-parallel-corpus-inventory-2026-09-01.md now exists and excludes customer translation memory); the TED usage-policy page, the TyDi QA dataset card and the NVIDIA H100 product page were fetched on 2026-09-01 in wave 4 (previously unfetched); the host's Docker image inventory and the checkpoint-fetch receipts were not re-audited from this Mac, so image and receipt provenance rest on repository records (docs/local-model-lab.md, research/frontier-systems-program-2026-09-01.md, memory.json) and the wave-5 brief; the fla issue 640 page was not fetched (quoted from the repository record of the fla 0.5.2 error message)
**Budgets:** queries=60; wall_minutes=600; tokens=900000; dollars=40; waves=5; gpu_hours=16
**Novelty verdict:** NO_DIRECT_PRIOR_FOUND
**Safety verdict:** PASS
**Evidence bundle:** evidence/translation-supervised-sparse-indexer/bundle.json

## Claim and Research Question

Learned sparse-attention indexers of the DSA/QSA class, distilled only from full
attention onto frozen released checkpoints (a retrofit population until Phase 0b
or Phase 2 speaks), are claimed to carry an **excess cross-lingual selection
gap** beyond the gap of their own distillation target — measured with both legs
of the gap being non-literal semantic queries, so that literal-versus-semantic
retrieval fragility cannot masquerade as a cross-lingual effect. Supervising the
*detached* indexer with corpus-given sentence alignments from bilingual document
pairs (a training view that never touches main attention; inference unchanged)
is claimed to raise **absolute cross-script selection recall** on **held-out
languages** at **matched achieved token budget** by at least 6 recall points
over the strongest label-free target aggregation — where "strongest" is now
operationalised on absolute cross-script recall against one fixed reference,
not on the excess statistic — with the fix visible in generation exact match
rather than only in selection-recall proxies.

Research question. Given a frozen decoder-only LM with a KL-distilled top-k
indexer, (RQ1) does the indexer lose more cross-script selection recall than its
own target when monolingual and cross-lingual queries are equally non-literal;
(RQ2) is that loss a recipe artifact — does a label-free target aggregation
(head-sum versus max-pool versus retrieval-head-weighted) recover most of the
head-sum indexer's cross-script shortfall from a fixed reference with zero
labels; and (RQ3) conditional on a residual shortfall after the best label-free
target, does alignment content — not bilingual exposure, not the loss form, not
generic monolingual semantic sharpening — add absolute cross-script recall, on
languages never seen by the alignment loss?

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
dense parity in English. None of them reports per-language selection behaviour
in the text read so far (the QSA report's only multilingual number is an
aggregate MMMLU, 81.8 full attention versus 81.1 QSA, Table 2), and the only
cross-lingual audit of a learned selector (Lost in Compression) covers prompt
compressors, not attention indexers. The 2026-09-01 sweep found the axis
"learned indexer selection across translations" empty in every cell (synthesis
G13, seq-operators G6, benchmarks-eval G2). The VERIFICATION PASS CORRECTIONS
require MLNeedle and OneRuler as the cross-lingual NIAH baselines; both are
dense-softmax results and neither touches selection.

Why Kevin, why now: the pilot needs no private asset, but a mature Docker/Slurm
harness that can train many detached indexers in one shared frozen-teacher
stream is exactly what the repository already does, and the instrument this
proposal delivers (per-language achieved-token ledger plus indexer-versus-target
and indexer-versus-fixed-reference selection recall) is the kind of receipt the
program exists to produce. General Translation's document-level parallel pairs
are an optional upgrade for low-resource cross-script pairs and the Phase-2
continued-pretraining corpus, not a dependency. The deployment interest —
cross-lingual long-context retrieval over translation memories under a sparse
indexer — is real and unstated by any sparse-attention lab.

## Primary-Source Evidence

Indexer class and its training recipes (all first-party technical reports):

- DeepSeek-V3.2 / DSA — https://arxiv.org/abs/2512.02556 (2025-12-02). Lightning
  indexer trained by KL to head-summed, L1-normalized dense attention; a
  2.1B-token frozen warm-up followed by 943.7B tokens with the backbone
  unfrozen; no per-language analysis.
- On the Design of Qwen3.8-Next (QSA) — https://arxiv.org/abs/2608.30320
  (2026-08-31); full text https://arxiv.org/html/2608.30320 read in wave 4
  through §3.2 (page truncated there). Compressed-block indexer trained against
  a max-pooled teacher distribution (§2.1.2, Eq. 17); QSA beats full attention
  on RULER 512K–1M (90.08 → 93.00) and MRCR 512K (30.66 → 40.53) (Table 3);
  the only multilingual number is aggregate MMMLU 81.8 → 81.1 (Table 2); no
  per-language indexer or selection table in the portion read.
- SpotAttention — https://arxiv.org/abs/2606.22874 (2026-06). Frozen Qwen3/Qwen3.5
  backbones, a 4 × 128 KL-distilled selector trained on 100M tokens at 16K (763
  steps) on every full-attention layer, dual top-p budgets, English dense parity
  to 128K on 4B–32B bases; non-English untested; no public code found.
- Oracle-Guided Sparse Prefill — https://arxiv.org/abs/2606.07703 (2026-06).
  Frozen-backbone, head-collapsed indexer KL-distilled from dense attention mass
  on Qwen3.5-0.8B/9B, plus an attention-mass top-k oracle that separates
  sparse-budget feasibility from indexer error. This is the monolingual
  precursor of the ξ decomposition used here.
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
  heads perform copy-retrieval, motivating the retrieval-head-weighted target —
  and, because retrieval heads are literal copy heads, the wave-3 reviewer's
  warning that a retrieval-head target is itself cross-lingually weak, which is
  why T* is no longer selected on the excess statistic.
- RTPurbo — https://arxiv.org/abs/2605.16928 (2026-05): long-range retrieval is
  governed by a low-dimensional subspace and a 16-dimensional indexer suffices
  once the target is the retrieval heads rather than the head sum; fixed top-k
  is reported inferior to top-p. The wave-2 note cited RTPurbo under the id
  2608.26449, which is the Vowel Signs abugida-tokenizer paper; corrected in
  wave 3.
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
https://opus.nlpl.eu/TED2020 (TED text under CC BY-NC-ND 4.0 per the TED usage
policy https://www.ted.com/about/our-organization/our-policies-terms/ted-talks-usage-policy,
fetched 2026-09-01: non-commercial, no derivative works, sharing with
attribution and link); FineWeb-2 —
https://huggingface.co/datasets/HuggingFaceFW/fineweb-2/tree/af9c13333eb981300149d5ca60a8e9d659b276b9
(ODC-By 1.0); Belebele —
https://huggingface.co/datasets/facebook/belebele/tree/7899cdfa4e1e0d733fd77c848e2c273cb1d32be2
(CC-BY-SA 4.0); WMT24++ —
https://huggingface.co/datasets/google/wmt24pp/tree/fd7405c06494bc66a57b25f55d217a72f96e60dc
(apache-2.0); FLORES+ — https://huggingface.co/datasets/openlanguagedata/flores_plus
(CC-BY-SA 4.0, gated); TyDi QA GoldP —
https://huggingface.co/datasets/google-research-datasets/tydiqa (arm (i) only;
card fetched 2026-09-01: configs primary_task and secondary_task, 11 languages,
license field in the card body reads "More Information Needed" while the page
metadata tag says apache-2.0 — treated as unconfirmed).

Kernels and throughput reference points: flash-linear-attention —
https://github.com/fla-org/flash-linear-attention/blob/main/fla/ops/nsa/parallel.py
(parallel_nsa / parallel_nsa_topk with block_indices of shape [B, TQ, H, S];
asserts HQ/H at least 16), https://github.com/fla-org/flash-linear-attention/tree/main/fla/ops/dsa
(only naive.py), https://github.com/fla-org/flash-linear-attention#benchmarks
(GB200 first-party table: chunk_gdn 3.616 ms versus flash_attn 19.960 ms at
B=2, T=16384, H=16, D=128, forward plus backward); llm.c —
https://github.com/karpathy/llm.c/discussions/481 (GPT-2 124M, 10B tokens in
about 90 minutes on 8 × A100 80GB, about 60% MFU, first-party); NVIDIA H100
product page — https://www.nvidia.com/en-us/data-center/h100/ (fetched
2026-09-01: BF16 Tensor Core 1,979 TFLOPS with sparsity, 80GB, 3.35 TB/s; the
dense 989 TFLOPS figure used below is the conventional half and is not printed
on the page).

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
| R02 | Qwen3.5-4B @ 851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a: 32 layers, full attention at layers 3, 7, …, 31 (8 layers), 16 Q / 4 KV × 256, GDN elsewhere, 4.66B parameters, apache-2.0; this is the post-trained checkpoint; the Base (R51) is now registered and used instead, its layer_types not yet re-read | https://huggingface.co/Qwen/Qwen3.5-4B/blob/851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a/config.json — layer_types | FIRST_PARTY (re-read by the wave-2 feasibility refuter) |
| R03 | Qwen3.8-Flash-Next @ de4b8e4d43b917e7706784d8bb445c9af86a3540: 180B total parameters (125B + 51B n-gram + 4B MTP in safetensors metadata), 48 layers, 512 experts top-10, QSA at 12 layers, indexer_n_heads 4, indexer_kv_heads 1, indexer_head_dim 128, indexer_compress_ratio 4, indexer_budget 2048, model_type qwen4_exp_text, license qwen-community-1.0 | https://huggingface.co/Qwen/Qwen3.8-Flash-Next/blob/de4b8e4d43b917e7706784d8bb445c9af86a3540/config.json | FIRST_PARTY |
| R04 | GLM-5.3-Flash: index_n_heads 32, index_head_dim 128, index_topk 2048, index_kpool 4; 321.3B total parameters; FP8 weights on HF (about 321 GB) | https://huggingface.co/zai-org/GLM-5.3-Flash/blob/main/config.json | FIRST_PARTY |
| R05 | DSA indexer trained by KL to head-summed L1-normalized attention; 2.1B-token frozen warm-up then 943.7B tokens unfrozen | https://arxiv.org/abs/2512.02556 — §2 (DSA training) | FIRST_PARTY |
| R06 | QSA indexer trained against a max-pooled teacher distribution (MaxPool over the block, Eq. 17); RULER 512K–1M 90.08 → 93.00 and MRCR 512K 30.66 → 40.53 for QSA versus full attention (Table 3) | https://arxiv.org/html/2608.30320 — §2.1.2 Training Details Eq. 17; §2.1.2 Table 3 | VERIFIED (full-text HTML read 2026-09-01 in wave 4; page truncated in §3.2, later tables unread) |
| R07 | SpotAttention: 4 × 128 selector, 100M tokens at 16K (763 steps), every full-attention layer, dual top-p, English dense parity to 128K on frozen 4B–32B Qwen3/Qwen3.5; non-English untested; no public code | https://arxiv.org/abs/2606.22874 — setup and results | FIRST_PARTY (code absence checked via GitHub/HF search 2026-09-01) |
| R08 | Oracle-Guided Sparse Prefill: frozen-backbone head-collapsed indexer KL-distilled from dense attention mass on Qwen3.5-0.8B/9B, plus an attention-mass top-k oracle; no multilingual evaluation | https://arxiv.org/abs/2606.07703 — abstract | FIRST_PARTY (abstract read by the wave-2 novelty refuter and by wave-3 reviewer A) |
| R09 | NoLiMa: GPT-4o 99.3 → 69.7 at 32K when literal overlap is removed | https://arxiv.org/abs/2502.05167 — abstract and main table | FIRST_PARTY (quoted by the wave-2 identification refuter) |
| R10 | Fewer than 5% of attention heads are retrieval heads | https://arxiv.org/abs/2404.15574 — abstract | FIRST_PARTY |
| R11 | RTPurbo: retrieval governed by a low-dimensional subspace; 16-dimensional indexer suffices with a retrieval-head target; fixed top-k inferior to top-p | https://arxiv.org/abs/2605.16928 — abstract | FIRST_PARTY (abstract quoted by the wave-2 identification refuter and confirmed by wave-3 reviewer A; full text unread) |
| R12 | MLNeedle: 7–8B instruct models about 0.30 (zh), 0.24 (ar), 0.25 (hi) versus 0.68 (en) at 4K | https://arxiv.org/html/2408.10151 — per-language table | FIRST_PARTY (quoted by the wave-2 identification refuter) |
| R13 | OneRuler: instruction language moves results by up to 20 points | https://arxiv.org/abs/2503.01996 — abstract | FIRST_PARTY |
| R14 | Lost in Compression: the cross-lingual selection gap tracks supervision data, not architecture; budgets matched in the target tokenizer | https://arxiv.org/abs/2608.26175 — abstract | FIRST_PARTY |
| R15 | MGAL: 6 languages, UN reports, position-aware long-context benchmark | https://arxiv.org/abs/2608.20853 — abstract | FIRST_PARTY |
| R16 | ParaDocs: 18 data dirs en-{cs,de,es,fr,hi,hu,id,it,km,lo,my,ne,nl,pl,pt,sv,th,vi}; release filters minimum_size 2, frequency_cutoff 100, lid_cutoff 0.5; card license apache-2.0 | https://huggingface.co/datasets/jhu-clsp/paradocs/tree/main/data and README.md | VERIFIED (dirs and filters re-read by the wave-2 feasibility refuter 2026-09-01) |
| R17 | ParaCrawl text is CC0 | https://paracrawl.eu — license statement | FIRST_PARTY |
| R18 | TED2020 v1 via OPUS: en–zh_cn 3,827 documents / 399,092 pairs / 8,050,948 en tokens; en–ru 3,699 / 386,316; en–ar 3,879 / 403,716; en–ja 3,493 documents; en–ko 3,753 documents | https://opus.nlpl.eu/opusapi/?corpus=TED2020&source=en&target=zh_cn&preprocessing=xml&version=v1 (and sibling queries) | VERIFIED (OPUS API counts re-read by the wave-2 feasibility refuter) |
| R19 | TED Talks content is licensed CC BY-NC-ND 4.0 International: no commercial use, no derivative works (no editing, remixing or modifying the talks), sharing permitted with attribution and a link to the talk; educational use encouraged | https://www.ted.com/about/our-organization/our-policies-terms/ted-talks-usage-policy — license section | VERIFIED (page fetched 2026-09-01 in wave 4; previously UNVERIFIABLE_ACCESS) |
| R20 | FineWeb-2 @ af9c13333eb981300149d5ca60a8e9d659b276b9 is ODC-By 1.0 and holds all 12 held-out and 7 training language dirs | https://huggingface.co/datasets/HuggingFaceFW/fineweb-2/tree/af9c13333eb981300149d5ca60a8e9d659b276b9 | VERIFIED (wave-2 feasibility refuter) |
| R21 | Belebele @ 7899cdfa4e1e0d733fd77c848e2c273cb1d32be2: CC-BY-SA 4.0; 488 FLORES-200 passages × 122 language variants; 900 questions per variant | https://huggingface.co/datasets/facebook/belebele/tree/7899cdfa4e1e0d733fd77c848e2c273cb1d32be2/data and card | FIRST_PARTY (card) |
| R22 | WMT24++ @ fd7405c06494bc66a57b25f55d217a72f96e60dc: apache-2.0; 55 en→xx document-level human translations with document_id; no Georgian | https://huggingface.co/datasets/google/wmt24pp/tree/fd7405c06494bc66a57b25f55d217a72f96e60dc | VERIFIED (wave-2 feasibility refuter) |
| R23 | FLORES+ is CC-BY-SA 4.0, gated with automatic approval | https://huggingface.co/datasets/openlanguagedata/flores_plus | FIRST_PARTY |
| R24 | TyDi QA card: configs primary_task (186k rows) and secondary_task (GoldP, 55k rows); 11 typologically diverse languages, of which ar, bn, en, fi, id, ja, sw, te, th were visible in the viewer excerpt (ko, ru not shown); the card body's License field reads "More Information Needed" while the page metadata tag says apache-2.0 | https://huggingface.co/datasets/google-research-datasets/tydiqa — card and viewer | VERIFIED as fetched 2026-09-01 in wave 4; the license itself remains UNCONFIRMED (conflicting fields) and gates arm (i) |
| R25 | fla v0.5.2 ships only fla/ops/dsa/naive.py for DSA; parallel_nsa and parallel_nsa_topk take block_indices [B, TQ, H, S] and assert HQ/H at least 16; chunk_gdn is exported | https://github.com/fla-org/flash-linear-attention/blob/main/fla/ops/nsa/parallel.py ; https://github.com/fla-org/flash-linear-attention/tree/main/fla/ops/dsa | VERIFIED (source read via GitHub API by the wave-2 feasibility refuter) |
| R26 | fla GB200 benchmark: chunk_gdn 3.616 ms versus flash_attn 19.960 ms at B=2, T=16384, H=16, D=128 (forward plus backward) | https://github.com/fla-org/flash-linear-attention#benchmarks — README table | FIRST_PARTY |
| R27 | llm.c: GPT-2 124M on 10B tokens in about 90 minutes on 8 × A100 80GB, about 60% MFU | https://github.com/karpathy/llm.c/discussions/481 | FIRST_PARTY |
| R28 | H100 SXM: BF16 Tensor Core 1,979 TFLOPS with sparsity, 80GB, 3.35 TB/s; the dense figure 989 TFLOPS used in the budget is the conventional half of the with-sparsity number and is not printed on the page | https://www.nvidia.com/en-us/data-center/h100/ — specifications table | VERIFIED (page fetched 2026-09-01 in wave 4; previously from memory) |
| R29 | Discovery image (provenance anchor only after wave 5; no longer the pilot image): Image ID sha256:ca32b5c26b92fbe2a7054ae96543cd62928b0493896ec355b869b612022aa9a2; repo digest 127.0.0.1:5000/cotcodec-research@sha256:15d6abc06fa53ab466087a92107da9c58e469615e2f56a683fefd0a7600277f3; labels revision 581ded8df71564b0212d8af5dcd401257aa6a28f, source-tree-sha256 2d960d1a5cf6fd64cdd0baba0a2c752ad6216b8443d741cb7deef9e07d031322, runtime-profile architecture-source-overlay, created 2026-08-16; contents CUDA 12.8.1, torch 2.11.0+cu128, transformers 5.15.0, accelerate, triton; no vllm/peft/fla/flash-attn | fal-h100-01 local registry, docker inspect on 2026-09-01 (spec brief) | VERIFIED (on the host by the spec-phase brief author; no public URL) |
| R30 | fal-h100-01: 8 × H100 80GB, 208 CPUs, 1.7 TB RAM, 21 TB free disk, Docker 28, Slurm 21.08.5 single node, no Pyxis/Enroot | context brief 2026-09-01 (operator inventory) | FIRST_PARTY (operator's own inventory; not re-audited in this session) |
| R31 | Wave-2 feasibility re-derivation of Phase 0a (wave-2 design): 1.88 GPU-h base, 2.35 with 25% reserve, about 18 minutes wall-clock on 8 GPUs at 297 TFLOPS/GPU and 2.0 TB/s | research/gauntlet/2026-09-01-frontier/wave2-result.json — feasibility vote | VERIFIED (independent re-derivation inside this gauntlet from R01–R03, R25–R28) |
| R32 | Phase 0a cost after the wave-5 re-derivation (E1 at 2,000/1,200/800 prompts per length per base = 6.2e7 tokens per base, with parameter, causal attention-score and indexer-scoring FLOPs: about 1.4e18 FLOP, 1.40 GPU-h): 2.64 GPU-h base, 3.3 with reserve, cap 4.0 (one 30-minute 8-GPU job); adequacy-extension job 1.04 base, 1.3 with reserve, cap 1.5, conditional, displaces Phase 0b; the wave-4 figures 2.37/3.0 rested on an E1 row of 1.13 that excluded attention FLOPs | this proposal, Cheapest Decisive Pilot table, derived from R01–R02, R27–R28 at an assumed 30% MFU | FIRST_PARTY (derivation; MFU assumed, not measured) |
| R33 | Phase 1 cost after the wave-5 λ_x pre-step (65 block-form plus 6 token-form plus 2 pre-step indexers on 0.6B; E2 at seeds 42–44 only): 7.74 GPU-h base, 9.7 with reserve, cap 10.0 | this proposal, Phase 1 table, same inputs | FIRST_PARTY (derivation) |
| R34 | Phase 0b probe: 120 prompts at 8K with a 6 s per-prompt abort threshold on 8 GPUs is 1.6 GPU-h plus at most 0.4 GPU-h weight loading, cap 2.0 | this proposal, derived from R03 (about 360 GB bf16) | FIRST_PARTY (derivation) |
| R35 | Wave-1 novelty search: 9 arXiv, 4 HF-papers, 7 WebSearch queries plus DSA and QSA full text; wave-2 recheck: arXiv query on indexer AND sparse attention AND multilingual/cross-lingual/translation returned MiniMax MSA 2606.13392, FlashMemory 2606.09079, Dynamic Sparse Attention 2603.13430 (none multilingual); HF-papers query returned MGAL only; wave-2 refuter: 13 hostsearch calls, 10 WebSearch, 10 WebFetch | research/gauntlet/2026-09-01-frontier/wave1-verdicts.json and wave2-result.json | VERIFIED (gauntlet records) |
| R36 | Wave-2 judge scores: Reviewer A total 64/100, Reviewer B total 61/100; refuter votes novelty not refuted (0.6), identification refuted (0.72), feasibility not refuted (0.8); blind discrimination different mechanism, prior does not dominate (0.8) | research/gauntlet/2026-09-01-frontier/wave2-result.json — ranked[2] | VERIFIED (gauntlet record) |
| R37 | Wave-1 outcome: killed before judging; novelty not refuted (0.6), identification refuted (0.8), feasibility refuted (0.8) | research/gauntlet/2026-09-01-frontier/wave1-ledger.md — row 2 | VERIFIED (gauntlet record) |
| R38 | Pre-registered design parameters (this proposal): achieved-budget fraction ρ ∈ {6.25%, 12.5%, 25%} with 12.5% primary; fixed k ∈ {512, 1024, 2048}; contexts 8K/16K/32K; λ_x ∈ {0.25, 0.5}; indexer learning rate ∈ {3e-4, 1e-3, 3e-3} selected on development languages; indexer dims 64/128/256; LoRA rank 16; 50M Phase-0 and 100M Phase-1 training tokens (6,104 and 12,208 sequences of 8,192); LoRA controls 60M tokens × 2 seeds; fixed reference R^U = union of per-head top-k of the frozen layer's full attention at the indexer's k per head | this proposal and experiments/architectures/translation-supervised-sparse-indexer.yaml | FIRST_PARTY (design parameter) |
| R39 | Pre-registered thresholds: adequacy gate 5 points; ξ_T confirm 10, kill 5; T* selection MN band 2 points; K2a evaluability S_hs ≥ 3 and kill at 80% recovery of S_hs; primary absolute effect D ≥ 6 points; K2b at D ≤ κ with κ = max(0, min(3, 6 − 2·σ̂·√(2/5))); inertness 1 point; L_perm/L_half kill 80% of D; L_sem kill 50% of D; training-free kill 80%; LoRA-specific kill 80%; P3 gain 8 EM points, monolingual within 2, E3 within 0.5; per-language floor 2 points; headroom gates dense cross-lingual EM 40% and sparse floor R^T − 5; 3 needle positions; 3,000/600/1,200/4,000/5,300/2,700/1,500 prompt counts | this proposal, Mechanism and Evaluation sections; the contract YAML | FIRST_PARTY (design parameter) |
| R40 | Power inputs (assumed, not measured) and the wave-5 rule: seed-to-seed SD of E1 recall at most 2 points with 6 df (three 0.6B block-form configurations × 3 seeds); prompt-level paired passage-cluster SE about 1.3 points; α = 0.01 two-sided; power 0.8; σ_up = 2·√(6/χ²_{0.20,6}) ≈ 2.80; se_seed_up = σ_up·√(2/5) ≈ 1.77; se_D_up ≈ 2.20; κ ≈ 1.6; separation 4.4; MDE ≈ 7.5 points (confirm threshold therefore max(6, MDE)); κ = 0 at se_D_up ≥ 3; the wave-4 seed-only figures (SE 1.26, MDE 4.3, κ = 3 for σ̂ ≤ 2.37) are withdrawn; E2: unpaired Bernoulli SE 1.83 points at 1,500 prompts, combined SE ≈ 2.45, MDE ≈ 8.4 EM points | this proposal, Evaluation section; computed by harness.translation_supervised_indexer.derive_decision_rule and recorded in the doctor receipt case decision_rule_from_stated_noise_model | FIRST_PARTY (assumption; no published seed-variance prior for indexer recall exists under the stated coverage; σ̂ and se_prompt are measured in Phase 0a) |
| R41 | QSA aggregate MMMLU 81.8 (full attention) versus 81.1 (QSA), the only multilingual number in the portion of the report read; Chinese C-Eval/CMMLU appear in Table 9 for n-gram vocabulary scales, not for QSA per language | https://arxiv.org/html/2608.30320 — §2.1.2 Table 2; Table 9 | FIRST_PARTY (read 2026-09-01 in wave 4; page truncated in §3.2) |
| R42 | A second real image is recorded in repository receipts: repo digest 127.0.0.1:5000/cotcodec-research@sha256:3f58e5256dff74ed3017a00af125e6ee2b6e4745208b9ea8a3668633760dfb00, Image ID sha256:785f16e880d8c38acef02254adaccfb48dfd3a374af12115ec88590f036bf81a, used by Slurm jobs 335, 336, 337 (orchvar-qwen35-4b-live-smoke-negative-v1.json), 338 (orchvar-qwen35-4b-live-v2-safety-negative.json), 339, 340 and 341; creation date not recorded in those receipts; nine further cotcodec-research digests (526cefa44807…, 91cf5c50d646…, 66e25dbb3ea1…, ff389e0f2111…, 9db4c59521c8…, d37cb58767b0…, 2eeb387ccb41…, 270d3ba3a08e…, 1946d7b0e69e…) appear in repository receipts | research/evidence/harness/orchvar-*.json; grep of research/, experiments/, docs/ on 2026-09-01 | VERIFIED as repository records; presence on the host was not re-audited from this Mac |
| R43 | Wave-3 fresh reviewer scores: Reviewer A 66/100 (6,7,5,8,8,7,6,5,8,6), Reviewer B 66/100 (7,7,5,8,7,7,6,6,8,5); fatal defects: (A) confirm and kill regions of the Phase-1 decision rule 3 points apart inside a 5.6-point MDE; (B) T* selected on the excess statistic, so a cross-lingually weaker target shrinks ξ without improving indexer CX recall; wrapper dry-run rejected the contract ("runtime must be docker-single-node-discovery-v1") | research/gauntlet/2026-09-01-frontier/wave3-result.json — item with spec.slug translation-supervised-sparse-indexer | VERIFIED (gauntlet record) |
| R44 | scripts/submit_docker_research_job.py --dry-run on the wave-4 contract exits 1 with "image_id must be an exact local Docker sha256 image ID" (after the wave-4 runtime and resource fields are accepted); the wave-3 contract was rejected earlier at "runtime must be docker-single-node-discovery-v1" | this repository, command run 2026-09-01 on the Mac; wrapper source validate_manifest() | VERIFIED (run in this session) |
| R45 | Rebuilt architecture image cotcodec-research:999f5583-architecture: Image ID sha256:9d832a59fe348d149d2e4587ac6af90223e2956ebb646d7b19295298954ca5ad; repo digest 127.0.0.1:5000/cotcodec-research@sha256:bde90daa78c26cd2fb9d05036b0c9f9613c2386b9d7561816b541d2736c79f5d; Slurm job 353 from commit 999f5583 via build-architecture-image.sbatch with host networking; torch 2.11.0+cu128, transformers 5.15.0, flash-linear-attention 0.5.2, fla-core 0.5.2, triton 3.6.0; no tilelang, no peft, predates this contract's code | docs/local-model-lab.md image table; research/frontier-systems-program-2026-09-01.md "Stage-0 execution"; memory.json fla_image; wave-5 brief | VERIFIED as repository records (docker inspect on the host by the Stage-0 operator; not re-audited from this Mac) |
| R46 | Ten pilot checkpoints fetched with receipts by Slurm job 356 under /home/kevin/cotcodec-runs/hf-cache/cotcodec-receipts/ on fal-h100-01: qwen3.5-4b-base (1001bb4d…, artifact root c7fbfd6bd1c73b9a…, 9.34 GB), qwen3-1.7b-base, transformer-1.3b-100b, gla-1.3b-100b, transformer-340m-10b, gla-340m-15b, gdn-1.3b-isp-hybrid-3to1-50b, gdn-340m-isp-hybrid-3to1-10b, e2-ttt-mlp-1.3b-15b, rwkv7-1.5b-world; qwen3-0.6b-base is not in the batch | research/frontier-systems-program-2026-09-01.md receipt table; HANDOFF.md; wave-5 brief | VERIFIED as repository records (receipt files not read from this Mac; digests not copied into the contract) |
| R47 | Phase-0 CPU doctor receipt: data/results/translation-supervised-sparse-indexer/phase0-doctor.json, status PHASE0_DOCTOR_PASS, 10 cases PASS, 25.4 s CPU, seeds 42–44, 8 prompt families per direction; implementation sha256 dee5318d254d962380e2de051eed227a97db10bfaa40eb0c12467e9a289e0cd5; payload sha256 3a50150c3c3c0145…; evidence_grade EXECUTABILITY_AND_GATE_SEMANTICS_ONLY; synthetic numbers: ξ_hs 52.2/80.0/46.5, D 51.0/80.5/46.5, D_perm −42.5/−13.8/−50.0, D_half 12.0/29.0/6.8, D_shifted −0.5/−6.8/−1.5, T* = hs at every seed, λ_x* 0.25/0.25/0.5, adequacy shortfall 2.0/0.5/0.0, R^U(CX) = 100, gradient relative error 5.6e-9, union reference 20 of 20 brute-force matches, bootstrap SE 0.198 versus analytic 0.199 | this repository, run 2026-09-01 on the Mac with uv run python scripts/run_translation_supervised_indexer_doctor.py; tests/test_translation_supervised_indexer_doctor.py 16 passed | VERIFIED (run in this session; synthetic-case numbers, not measurements of any model) |
| R48 | scripts/submit_docker_research_job.py --dry-run on the wave-5 contract still exits 1 with "image_id must be an exact local Docker sha256 image ID" (image_id deliberately left absent) | this repository, command run 2026-09-01 (wave 5) on the Mac | VERIFIED (run in this session) |
| R49 | Wave-4 fresh reviewer scores: Reviewer A 62/100 (6,7,5,8,7,6,6,5,7,5), Reviewer B 69/100 (7,8,6,8,8,7,6,5,8,6); fatal defects: (A) decision rule from a contradicted noise model (6 df not 12; seed-only SE; gates on the primary prompts), (B) λ_x without a producing step and an ambiguous E1 FLOP row | research/gauntlet/2026-09-01-frontier/wave4-result.json — item with repair.slug translation-supervised-sparse-indexer | VERIFIED (gauntlet record) |
| R50 | fla 0.5.2 refuses the gated GDN backward on Hopper under Triton 3.4.0 to 3.7.0: "produces incorrect results for gated chunk_bwd_dqkwg (see fla #640); upgrade Triton to at least 3.7.1 or install tilelang"; torch 2.11.0 pins triton 3.6.0, so tilelang is being added to the architecture extra | research/frontier-systems-program-2026-09-01.md (Slurm job 354 log quoted); pyproject.toml architecture extra (tilelang at least 0.1.13); https://github.com/fla-org/flash-linear-attention/issues/640 | FIRST_PARTY as quoted in the repository record; the issue page itself UNVERIFIABLE_ACCESS in this session |
| R51 | qwen3.5-4b-base is registered: repo Qwen/Qwen3.5-4B-Base, revision 1001bb4d826a52d1f399e183466143f4da7b741b, apache-2.0, gated-deltanet-attention-hybrid, roles include direction-21-subject | models/registry.yaml; https://huggingface.co/Qwen/Qwen3.5-4B-Base | VERIFIED as repository record (config.json not re-read for layer_types) |

## Closest Prior Work

The mechanism sits between two literatures that have never met. On one side,
every learned-indexer paper surfaced (DSA, QSA, SpotAttention, Oracle-Guided
Sparse Prefill, LongCat LSA, MISA, PIVOT, RTPurbo, Self-Indexing KVCache) trains
or replaces the indexer by KL or an oracle derived from the model's own full
attention and evaluates on English-centric long-context suites; none supervises
selection with any external signal and none reports per-language selection in
the text read (QSA: only aggregate MMMLU through §3.2; GLM-5.3 and MiniMax MSA
2606.13392 / FlashMemory 2606.09079 bodies unread). On the other side,
supervised and guided attention in NMT (Liu 2016, Chen 2016, Garg 2019) and
AlignAtt4LLM supervise or select *main* attention heads with alignment labels;
none touches a detached top-k selector of a decoder-only LM.

Oracle-Guided Sparse Prefill (2606.07703) is the closest single object: a
frozen-backbone KL indexer and an attention-mass top-k oracle that separates
budget feasibility from indexer error. That is exactly the monolingual form of
the R^T-versus-indexer decomposition used here; the wave-3 repair cites it as
the precursor and leaves the cross-lingual axis, the literalness control and
the fixed-reference target comparison as the only new content of the
diagnostic. SpotAttention publishes the frozen KL-only selector arm (b) at
English parity, so the pilot's baseline arm is a re-implementation of a
published method whose non-English behaviour is the open question. Lost in
Compression supplies the audit protocol (achieved-budget matching in the target
tokenizer) but studies prompt compressors. MLNeedle and OneRuler establish the
cross-lingual needle gap on dense softmax transformers and are the mandatory
dense baselines; neither has a selection component to localize the gap to.

What this leaves open, and what the pilot measures: whether a low-rank ReLU
indexer trained on aggregated attention mass loses the cross-script semantic
subspace that the many-head teacher uses — beyond what the teacher itself
loses, beyond what a literal-versus-semantic query difference explains, and,
after wave 4, beyond what the best label-free aggregation recovers when every
aggregation is judged against the same fixed reference.

## Novelty Ledger

| Proposed component | Closest prior | Same | Delta | Confidence |
|---|---|---|---|---:|
| Detached top-k indexer with KL distillation from frozen full attention (arms a, b) | DSA https://arxiv.org/abs/2512.02556 ; SpotAttention https://arxiv.org/abs/2606.22874 ; Oracle-Guided Sparse Prefill https://arxiv.org/abs/2606.07703 | yes | none claimed; this is the re-implemented baseline | 0.95 |
| Indexer-versus-own-target excess gap ξ as the localization statistic, with a fixed union-top-k reference R^U for cross-aggregation comparison | Oracle-Guided Sparse Prefill https://arxiv.org/abs/2606.07703 (attention-mass top-k oracle versus indexer error, monolingual) | partly | cross-lingual axis; both legs non-literal (Belebele question-as-query), literal copy reported as a ceiling; per-language achieved-budget ledger; one reference shared by every aggregation | 0.60 |
| Target-aggregation ladder (head-sum, max-pool, retrieval-head-weighted) as the label-free counterfactual, ranked on absolute cross-script recall within a monolingual band | DSA head-sum https://arxiv.org/abs/2512.02556 ; QSA max-pool https://arxiv.org/abs/2608.30320 ; retrieval heads https://arxiv.org/abs/2404.15574 ; RTPurbo https://arxiv.org/abs/2605.16928 | yes (each aggregation exists) | measuring their per-language selection recall against each other and against a fixed reference is not reported by any source | 0.55 |
| Sentence-alignment log-mass loss L_x on the detached indexer, corpus-given labels, main attention untouched | Guided NMT attention https://arxiv.org/abs/1609.04186 , https://arxiv.org/abs/1607.01628 , https://arxiv.org/abs/1909.02074 ; AlignAtt4LLM https://arxiv.org/abs/2606.03967 | partly (loss form) | object (selection indexer of a decoder-only sparse LM), label (corpus sentence alignment on concatenated bilingual documents, no aligner), inference unchanged | 0.60 |
| Information-matched controls: L_perm, L_half, L_sem (monolingual question-to-passage supervision), LM-only and LM+L_x LoRA, with inertness preconditions | Lost in Compression https://arxiv.org/abs/2608.26175 (supervision-data explanation) ; Semantic Hub https://arxiv.org/abs/2411.04986 | no | a pre-registered identification battery for alignment content versus loss form, cross-language mass push, generic semantic sharpening and dense fine-tuning | 0.65 |
| Per-language selection-recall instrument for any DSA/QSA checkpoint, including an inference-only probe of a production QSA indexer | MLNeedle https://arxiv.org/abs/2408.10151 ; OneRuler https://arxiv.org/abs/2503.01996 ; MGAL https://arxiv.org/abs/2608.20853 (behavioural, dense) | no | localizes the cross-lingual long-context gap to the selection component or exonerates it | 0.65 |

Novelty wording: No direct prior art found through 2026-09-01 under the
wave-1 novelty triad (9 arXiv API queries, 4 HF-papers queries, 7 WebSearch
queries, full text of DSA and QSA), the wave-2 rechecks (one arXiv API query,
one HF-papers query), the wave-2 novelty refuter's 13 hostsearch, 10 WebSearch
and 10 WebFetch calls, and the wave-4 read of the QSA HTML through §3.2, for an
alignment-supervised detached selection indexer or for any per-language
selection audit of a learned sparse indexer. Coverage holes: 10 of 13 arXiv
boolean queries returned HTTP 429; 4 OpenReview hits unread; Semantic Scholar
unavailable; QSA tables after §3.2, GLM-5.3, MiniMax MSA and FlashMemory bodies
not read for per-language indexer tables; no PRISMA-style identified/screened/
included counts were kept in waves 1–3. This is a bounded statement, not a
global novelty claim, and it awaits a signed provider-distinct novelty review.

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
Belebele passage), a position p, and a query Q in language l_Q. Four conditions
share (H, N, p) and differ only in Q. Held-out cross-script pairs are (l_N = X,
l_Q = en) and (l_N = en, l_Q = X) for X ∈ {ja, ko, bn, ta, el, he, ka} — 14
pairs, both query directions; held-out same-script pairs are the same two
directions for X ∈ {id, tr, sw, nl, it}; pairs among two non-English held-out
languages are descriptive.

```text
ML  mono-literal      Q = a verbatim needle sentence in l_N        (ceiling row only)
MN  mono-non-literal  Q = the Belebele question about N, in l_N    (reference leg)
CS  cross same-script Q = the same question in l_Q, script(l_Q) = script(l_N)
CX  cross cross-script Q = the same question in l_Q, script(l_Q) differs
R_A(cond) = mean over content tokens t of Q and sparse layers of |S^A_t ∩ N| / |N|
            A in {ind^T (indexer trained to T), T (the target's own top-k),
                  U (fixed reference: union over heads h of Top-k P^h_t, the
                     frozen layer's full attention, same k per head; a superset
                     budget of at most H*k keys, identical for every T)}
            k = rho * |H| in the model tokenizer
Delta_A   = R_A(MN) - R_A(CX)                     (cross-lingual gap of A)
xi_T      = Delta_ind^T - Delta_T                 (own-target excess; K1's uniform null;
                                                   descriptive per T and language)
xi^U_T    = Delta_ind^T - Delta_U                 (excess over the fixed reference;
                                                   the residual L_x is asked to recover)
S_T       = R^U(CX) - R_ind^T(CX)                 (absolute cross-script shortfall of the
                                                   T-indexer from the fixed reference)
Lambda    = R(ML) - R(MN)                         (literalness gap; reported, not in xi)
T*        = argmax_T R_ind^T(CX) on development languages at rho = 12.5 percent,
            subject to R_ind^T(MN) at least max_T' R_ind^T'(MN) - 2 points;
            frozen before any held-out number is read
D         = R_c(CX) - R_b(CX),  c = (T*)+L_x, b = (T*) KL-only   (PRIMARY, absolute points)
rho_x     = D / xi^U_T*                            (secondary, descriptive; both terms
                                                   carry passage-cluster intervals)
lambda_x* = argmax over {0.25, 0.5} of R_c(CX) on development languages within the
            2-point MN band  (registered Phase-1 pre-step, block form, seed 42, 0.6B;
            frozen and recorded before the five-seed arms are submitted)
se_D_up^2 = 2 sigma_up^2 / 5 + se_prompt^2         (wave-5 noise model; sigma_up = upper
            80 percent chi-square bound of the pooled Phase-0a seed SD at its honest df;
            se_prompt = paired passage-cluster bootstrap SE of a null two-arm contrast
            on the audit partition at the primary prompt count)
kappa     = max(0, min(3, 6 - 2 se_D_up))          (K2b threshold; fixed before Phase 1)
```

Why the wave-4 re-registration: wave 3 chose T* = argmin_T ξ_T and killed on
ξ_T*/ξ_hs. Because ξ_T subtracts the target's own gap, an aggregation whose
target is itself cross-lingually weak (the retrieval-head-weighted target, whose
heads are literal copy heads) shrinks ξ without improving the indexer's absolute
CX recall, so K2a could fire and the recovery ratio could move for the wrong
reason. T* is now the aggregation whose *indexer* selects the needle best on
cross-script queries within a monolingual band; K2a is stated on the absolute
cross-script shortfall from one reference shared by every aggregation; the
Δ_T-per-aggregation sanity row is reported so a reader can see whether a small
ξ came from a good indexer or a bad target; ξ_T stays as the localization
statistic (K1 tests every T, a uniform null) and as a descriptive table.

The wave-2 ξ used ML as the monolingual leg, so the NoLiMa-style literalness
gap Λ was inside it; the wave-3 repair moved the reference to MN and reports Λ
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
  language changed; R^T and R^U on the same prompts.
- **P2 (primary identification contrast; absolute points).** On the 14
  held-out cross-script pairs at ρ = 12.5% and 8K, block form on
  qwen3-0.6b-base over five seeds: D = R_c(CX) − R_b(CX) ≥ 6 recall points with
  the 99% paired passage-cluster bootstrap interval excluding zero, MN recall
  within 1 point of (T*) KL-only and E3 within 0.5 points; given the inertness
  preconditions |R_d(MN) − R_b(MN)| ≤ 1 and |R_e(MN) − R_b(MN)| ≤ 1, the
  absolute gains of (T*)+L_perm and (T*)+L_half are each below half of D; the
  absolute gain of (T*)+L_sem is below half of D. The relative recovery
  ρ_x = D / ξ^U_T* is reported as a secondary with the denominator's own
  interval propagated through a paired bootstrap of the ratio and carries no
  decision. (c′) = head-sum + L_x versus (b′) = head-sum KL-only is the
  DSA-style secondary contrast; token-form and 4B arms are descriptive.
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
  shows in production). A needle-absent control bounds parametric recall. The
  dense model's E2 EM is the fixed reference on this endpoint.
- **P4 (exploratory, not load-bearing).** Sparse-with-L_x minus dense on
  cross-lingual E2 ≥ 0 with oracle-selection and random-plus-needle controls.
- **P5 (Phase 2, outside this contract).** From-scratch 60–125M 3:1 GDN plus
  sparse-global hybrid with a fertility-balanced BPE shows a cross-script gap
  ≥ 2× the same-script gap for KL-only and ≤ 1.3× with L_x at equal BPB.

Kill conditions (falsifiers; each ends or re-frames the line as stated):

1. **K1 localization negative.** With the adequacy gate passed, ξ_T ≤ 5 points
   for every T on both bases and both indexer forms: the indexer adds no
   cross-lingual bottleneck beyond its target; publish and stop.
2. **K2a target-aggregation artifact (re-registered on absolute recall).** Let
   S_hs = R^U(CX) − R_ind^hs(CX) on held-out cross-script pairs at matched
   achieved budget. K2a is evaluable only if S_hs ≥ 3 points (otherwise the
   head-sum indexer already sits at the reference and K1 reasoning applies).
   Kill the alignment line if R_ind^T*(CX) − R_ind^hs(CX) ≥ 0.8 · S_hs: a
   label-free aggregation recovers the head-sum indexer's cross-script
   shortfall for free; published as a recipe finding with the Δ_T row.
3. **K2b weak alignment effect (re-registered in wave 5 on a fully specified
   noise model).** D, read exactly once on the Phase-1 primary passage
   partition, is ≤ κ, where κ = max(0, min(3, 6 − 2·se_D_up)) and
   se_D_up² = 2·σ_up²/5 + se_prompt². Here σ̂ is the pooled
   within-configuration seed SD of block-form CX recall across the three
   Phase-0a block-form configurations on qwen3-0.6b-base at three seeds, so
   its honest degrees of freedom are 6 (the wave-4 text said 12; 12 applies
   only if the 4B base's three configurations are pooled under a declared
   homogeneity assumption); σ_up = σ̂·√(df / χ²_{0.20, df}) is its one-sided
   upper 80 percent bound; se_prompt is the paired passage-cluster bootstrap
   SE (seeds as fixed blocks, passages resampled) of a null two-arm block-form
   contrast (hs versus mp KL-only at matched seeds) measured on the Phase-0
   audit partition at the Phase-1 primary prompt count. κ, σ̂, df, σ_up and
   se_prompt are recorded in the evidence bundle before Phase 1 is submitted.
   Under the assumed inputs σ̂ = 2 (df 6) and se_prompt = 1.3, the doctor's
   implementation gives σ_up ≈ 2.80, se_D_up ≈ 2.20, κ ≈ 1.6 and a
   confirm–kill separation of 4.4 = 2·se_D_up (assumed inputs, not
   measurements). The band κ under D under 6 is pre-registered as
   **inconclusive**: reported in full, no claim, no promotion, no re-run
   inside this contract. If κ = 0 (se_D_up ≥ 3), Phase 1 is withheld and the
   noise model is the finding. The confirm threshold itself is fixed before
   Phase 1 as max(6, MDE(se_D_up)) rounded up to the nearest half point, so
   a confirm can never sit below the design's own detectable effect.
4. **K3 loss form, not content.** Inertness holds and the absolute gain of
   (T*)+L_perm or (T*)+L_half reaches ≥ 80% of D: re-frame as a
   mass-concentration regularizer paper or stop. If inertness fails, the
   loss-form question is reported as unresolved, not as a pass.
5. **K4 generic semantic sharpening.** The absolute gain of (T*)+L_sem reaches
   ≥ 50% of D on held-out cross-script pairs: parallel data is not the active
   ingredient; redirect to monolingual semantic supervision.
6. **K5 training-free parity.** Any training-free control at matched achieved
   budget recovers ≥ 80% of the E2 gain.
7. **K6 not selection-specific.** (k) − (j) ≥ 80% of (T*)+L_x − (T*) on E2.
8. **K7 proxy-only (re-registered in wave 5).** Kill if gains are confined to
   in-training languages. "E1 gains without E2 gains" is demoted from kill to
   pre-registered **inconclusive**: the E2 line (P3, 8 EM points, 3 seeds,
   1,500 prompts) has a closed-form MDE of about 8.4 EM points under an
   assumed 2-point seed SD (unpaired Bernoulli SE 1.83 points at p ≈ 0.5
   combined with the seed component), so an absent E2 gain cannot be told
   from an underpowered read and carries no kill.
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
not a result to report. Per-arm tuning: the indexer learning rate is chosen
from {3e-4, 1e-3, 3e-3} on development languages for the block-form head-sum
KL-only indexer at seed 42 and then applied to every arm; λ_x ∈ {0.25, 0.5} is
chosen on development languages in the registered Phase-1 pre-step (wave 5:
the wave-4 text declared λ_x frozen in Phase 0a, where no L_x indexer is
trained — Reviewer B's fatal defect — so the pre-step now exists, is
budgeted and is recorded); no threshold or hyperparameter is chosen on
held-out data. Gate statistics (adequacy, K1, K2a, σ̂, se_prompt) read only
the Phase-0 audit partition of the sealed passages; D reads only the Phase-1
primary partition, once; reads outside the declared partition fail closed in
the harness (assert_reads_within).

Strongest counter-argument (devil's advocate, checkpoint 1). The cross-lingual
gap, wherever it lives, is a property of the frozen model's attention mass; a
KL-distilled indexer is a lossy compression of that mass, and every compression
loses the diffuse tail first. So ξ is a compression artifact that the right
target (max-pool, retrieval heads, or simply a wider indexer) removes with no
labels, and alignment supervision is a costly way of buying what a better
distillation target buys for free — while the labs that matter train their
indexers inside continued pretraining on about a trillion multilingual tokens,
where a 50M-token frozen retrofit says nothing. The design answers by making
that argument an arm and a kill condition (K2a on absolute shortfall, the dim
ladder, Phase 0b) rather than a footnote: if it is right, the pilot says so
cheaply.

Strongest counter-argument (devil's advocate, checkpoint 2, wave 4). The fixed
reference R^U is a superset-budget ceiling (up to H·k keys), so S_hs is inflated
by a pure budget effect, K2a's 80% bar becomes hard to reach, and the
re-registration quietly protects the alignment line it was meant to expose.
Rebuttal, scored before the objection is dropped: (i) the K2a statistic is a
*ratio* of two shortfalls from the same reference, so a common inflation of
S_hs and S_T* by the budget effect leaves the ratio's meaning intact when the
head-sum and T* indexers select comparably many needle tokens under the
matched achieved budget — which the achieved-token ledger checks per prompt;
(ii) a budget-matched sensitivity reference U_k (each head keeps k/H keys, at
most k in total) is pre-registered as a descriptive row, and if the K2a verdict
flips between R^U and U_k the recipe question is reported as unresolved rather
than decided; (iii) the residual objection — that no budget-matched reference
is a true ceiling — is conceded and is exactly why the primary endpoint is the
absolute paired gain D with no reference in it.

What's missing. No production indexer is measured except in the optional
120-prompt probe (SE about 4.5 points); no continued-pretraining arm; QSA
tables after §3.2, GLM-5.3 and DSA per-language sections unread; no
independent replication of SpotAttention's parity; no measured seed-variance
prior for indexer recall (σ̂ is measured in Phase 0a, so κ is fixed by data,
but the pre-registered κ = 3 rests on the 2-point assumption); the TyDi QA
license is unconfirmed despite the card fetch (conflicting fields), so arm (i)
is gated; the NumPy Phase-0 doctor exists and passes but is synthetic-case
evidence only, while the GPU code path, an image containing it and the
evidence bundle do not exist; the "class" in the claim is a retrofit
population until Phase 0b or Phase 2 speaks.

## Cheapest Decisive Pilot

Phase 0 CPU doctor (exists; executed 2026-09-01; no GPU). The executable
pilot object of this direction is `harness/translation_supervised_indexer.py`
(NumPy/SciPy only; typed dataclasses with input validation; the indexer
I_t(s), the hs/mp/rh targets and KL, the fixed reference R^U with a brute-force
check and the budget-matched U_k row, per-condition selection recall, Δ, ξ_T,
ξ^U_T, S_T, Λ, the T* rule, the λ_x rule, D, the alignment loss L_x with
label-mass accounting and its L_perm/L_half controls, the bilingual
concatenation builder, the development/audit/primary passage split with
fail-closed reads, the noise model and κ, and every registered gate as a pure
function), exercised by

```text
uv run python scripts/run_translation_supervised_indexer_doctor.py \
  --output data/results/translation-supervised-sparse-indexer/phase0-doctor.json
# 2026-09-01: status PHASE0_DOCTOR_PASS; 10 registered cases PASS; 25 s CPU;
# tests/test_translation_supervised_indexer_doctor.py: 16 passed
```

The receipt's `evidence_grade` string says what it proves: executability and
gate semantics only. Its registered cases: (a) a synthetic bilingual toy — two
scripts related by one fixed symmetric reflection of a shared semantic
subspace, an eight-head softmax teacher (six same-language heads, one
cross-script hub head, one literal-copy head), a rank-16 four-head ReLU
indexer trained by analytic gradients (checked against finite differences to
6e-9 relative error) on a half-bilingual, half-monolingual stream; T* and λ_x
frozen on development-language prompts; the held-out language never enters
L_x — positive control at seeds 42, 43, 44; (b) L_perm and L_half same-form
controls with inertness; (c) a shifted-script negative control (a different
reflection); (d) R^U against brute force on 20 prompts and random selection
at chance; (e) L_x mass accounting and true-versus-permuted sensitivity; (f)
the decision rule on assumed inputs including the withheld regime and a
passage-cluster bootstrap check; (g) the passage split and read separation;
(h) leakage/causality perturbations; (i) 28 degenerate inputs; (j) gate
semantics on hand-made tables. **Synthetic-case numbers** (they describe the
toy, not any model): the KL-only head-sum indexer reached ML/MN recall
98–100 with adequacy shortfall 0.0–2.0 points and CX recall 19–54 on the
held-out language while R^T(CX) and R^U(CX) were 100, so ξ_hs was 52.2, 80.0
and 46.5 points at seeds 42, 43, 44 (P1 fires; K1 does not); the development
ladder excluded max-pool from T* because its MN recall (78–89) fell outside
the 2-point band despite the best CX, so T* = hs and K2a's recovery
statistic was 0 with S_hs 46–81 (evaluable, not fired); λ_x* was 0.25, 0.25
and 0.5; D = R_c(CX) − R_b(CX) was 51.0, 80.5 and 46.5 points on the
held-out language with MN within 2 points; the permuted-label gain was
−42.5, −13.8 and −50.0 and the other-half gain 12.0, 29.0 and 6.8 (both
under half of D; inertness failed for L_perm, so K3 is unresolved in the
toy, as registered); under a different script map the gain collapsed to
−0.5, −6.8 and −1.5 while the shifted teacher stayed at 100. U_k is
degenerate in the toy (k = 15 over eight heads keeps one key per head) and is
reported as such. Still open on the CPU side: the tokenizer-based TR-NIAH
builder with the per-prompt achieved-token ledger (Qwen tokenizer) and exact
50-gram plus MinHash (Jaccard ≥ 0.8) dedup of FineWeb-2 haystacks and
training documents against Belebele/WMT24++/FLORES+ with removal counts; a
20-prompt indexer-versus-target smoke run on real hidden states in the
re-pinned container under a Slurm dry-run the wrapper accepts; and the
Q-head padding or gather path for fla parallel_nsa (both bases fail its
HQ/H ≥ 16 assertion).

Phase 0a GPU kill screen (the pilot of record; one Slurm job; ≤ 4 GPU-h):

- Bases (frozen): qwen3-0.6b-base = Qwen/Qwen3-0.6B-Base @
  da87bfb608c14b7cf20ba1ce41287e8de496c0cd (indexers on all 28 layers);
  qwen3.5-4b-base = Qwen/Qwen3.5-4B-Base @
  1001bb4d826a52d1f399e183466143f4da7b741b (indexers on its full-attention
  layers — the production placement). Wave 5: the Base is now registered in
  models/registry.yaml and was fetched with a receipt on fal-h100-01 (job 356),
  so it replaces the post-trained qwen3.5-4b used through wave 4; its
  full-attention layer placement (3, 7, …, 31 in the post-trained config,
  R02) has not been re-read from the Base config and must be before
  enablement.
- Indexers: three target aggregations (hs, mp, rh) × two forms (token 4 × 128;
  block 4 × 128, 1 kv head, compress 4) × 3 seeds = 18 per base, plus two
  learning-rate-sweep block-form hs indexers at seed 42 on the 0.6B base (lr
  3e-4 and 3e-3 beside the default 1e-3), all trained in one forward stream of
  the frozen teacher (no gradient into the backbone, so all arms share one
  teacher pass).
- Data: 50M tokens = 6,104 sequences × 8,192; half bilingual concatenations,
  half monolingual FineWeb-2 in the training languages.
- Eval: E1 for indexer, target and fixed reference (R^U, U_k) on 4,000 sealed
  prompts **per base in total, split 2,000 at 8K, 1,200 at 16K and 800 at
  32K** (wave 5: the wave-4 row read as 4,000 at each length; the count is
  now unambiguous), all drawn from the Phase-0 audit partition (Belebele
  needles in held-out languages, four conditions, 3 positions), with dense
  rows computed only for query tokens; adequacy gate on English ML; dense E2
  headroom, monolingual and cross-lingual, on 1,200 prompts per base (G1).
- Selection and freezing on development languages (in-training cross-script
  pairs th, hi, km, zh, ar): learning rate; T* by the argmax-CX rule within the
  2-point MN band (λ_x is no longer frozen here — no L_x indexer exists in
  Phase 0a; it is frozen in the Phase-1 pre-step). Then, on the audit
  partition of the held-out pairs: ξ_T per aggregation (K1), Δ_T and S_T
  sanity rows, K2a. Then the noise model: σ̂ (pooled within-configuration seed
  SD of block-form CX recall over the three 0.6B block-form configurations, 6
  df), σ_up, se_prompt (paired passage-cluster bootstrap of the hs-versus-mp
  KL-only null contrast at the primary prompt count) and κ are computed and
  recorded. All of this happens before Phase 1 is submitted.

Budget arithmetic (H100 SXM 989 TFLOPS dense BF16 — the conventional half of
the 1,979 with-sparsity figure on the product page — and 3.35 TB/s; **assumed
30% MFU = 297 TFLOPS and 2.0 TB/s effective**, half the about 60% MFU llm.c
reports; MFU is measured by the first job and the budget is re-verified before
Phase 1 is submitted):

| item | work | GPU-h |
|---|---|---:|
| teacher forward, 0.6B, 50M tokens at 8K | 1.4e17 FLOP | 0.13 |
| attention-probability materialization for the KL targets, 28 layers | 7.3e14 B | 0.10 |
| teacher forward, 4B hybrid, 50M tokens (8 dense-attention layers plus fla chunk_gdn) | 4.0e17 FLOP | 0.37 |
| materialization, 8 layers | 2.1e14 B | 0.03 |
| 18 indexers per base plus 2 learning-rate-sweep indexers, forward plus backward, plus score-matrix traffic | about 2.3e17 FLOP + 1.5e15 B | 0.41 |
| E1 eval, 4,000 prompts per base (2,000 at 8K, 1,200 at 16K, 800 at 32K = 6.2e7 tokens per base), both bases: parameter FLOPs 7.4e16 (0.6B) + 5.8e17 (4B); causal attention-score FLOPs 1.5e17 (28 layers × 16 × 128) + 8.6e16 (8 full-attention layers × 16 × 256); indexer scoring 3.8e17 (20 indexers × 28 layers × 4 × 128) + 9.7e16 (18 × 8 layers); R^U and U_k from the stored query-token dense rows plus 10 percent IO | about 1.4e18 FLOP | 1.40 |
| dense E2 headroom, monolingual plus cross-lingual, 1,200 prompts × 2 bases | 2e17 FLOP | 0.20 |
| **subtotal** (wave 5 re-derivation; was 2.37 with the E1 row at 1.13) | | **2.64** |
| × 1.25 reserve | | **3.3** |
| **cap (Slurm/IO overhead; = 8 GPUs × 30 minutes)** | | **4.0** |
| adequacy-extension job (once, +50M tokens: teacher streams, materialization and indexers again; registered as a second Slurm job because 3.3 + 1.3 does not fit the 30-minute window) | 1.04 base, 1.3 with reserve | **cap 1.5, conditional; displaces Phase 0b** |

Decision: P1 holds (ξ_T ≥ 10 for some T and base, adequacy gate passed), K2a
does not fire, and κ is above 0 → Phase 1. K1 → stop and publish the
localization negative. K2a → stop the alignment line and publish the recipe
finding with the Δ_T row. κ = 0 → withhold Phase 1 and publish the seed
variance. ξ_T between 5 and 10 everywhere → pre-registered inconclusive
localization; Phase 1 runs only if K2a is evaluable and not fired, and D is
then judged on the same absolute rule.

Phase 1 identification (gated on P1; ≤ 10 GPU-h including reserve; same
shared-teacher design; 0.6B at 100M tokens = 12,208 × 8K; block form unless
noted; **five seeds [42, 43, 44, 45, 46] unconditional for every block-form
0.6B arm**). Pre-step (wave 5, Reviewer B's fix): (T*)+L_x is trained at
λ_x = 0.25 and 0.5 on development languages only (block form, seed 42, 0.6B,
about 0.04 GPU-h under the shared teacher stream); λ_x is frozen by the
highest development-language CX recall within the 2-point MN band and the
freeze is recorded in the evidence bundle before the five-seed arms are
submitted. Then: (a) KL-T*, monolingual contexts; (b) KL-T*, bilingual
concatenations — **primary label-free counterfactual**; (b′) KL-hs bilingual
and (b″) the remaining aggregation, completing the label-free ladder for the
K2a Δ_T row; (c) KL-T* + L_x — **primary treatment**; (c′) KL-hs + L_x
(DSA-style secondary); (d) KL-T* + L_perm; (e) KL-T* + L_half; (i) KL-T* +
L_sem (TyDi QA GoldP question-to-passage supervision in en/ar/ru/th only,
iso-token, excluding every held-out evaluation language; gated on the license
confirmation); (h) indexer dim ladder 64/256 for (b) and (c). That is 13
block-form configurations × 5 seeds = 65 block-form indexers, plus the 2
pre-step indexers. The primary D is read exactly once on the Phase-1 primary
passage partition (about 244 Belebele passages; 5,300 prompts on the 0.6B
base), which no Phase-0 gate touched. Token form for
(b) and (c) at seeds 42–44 (6 indexers; descriptive). Replicate (b), (c), (d),
(i) × 2 seeds on qwen3.5-4b-base's full-attention layers (descriptive). Separate
small jobs on qwen3-0.6b-base: (j) dense + LM-loss-only LoRA (rank 16 on q, k
of all layers, bilingual concatenations, 2 seeds × 60M tokens) and (k) dense +
LM loss + λ L_x on the head-summed main attention (same budget) — (k) − (j) is
the L_x-specific dense effect. Training-free controls at eval only:
SpotAttention dual top-p, larger k at matched measured latency (fla kernel
timing with warm-up), PIVOT-style query-group re-scoring, NSA pooled-key
selection, SWA plus sinks at matched KV bytes, oracle needle-block inclusion
with random fill, random-plus-needle, needle-absent. E1 is evaluated for all
five seeds (the primary endpoint); E2 (generation) is evaluated for seeds
42–44 only, keeping the E2 line unchanged.

| item | GPU-h |
|---|---:|
| teacher stream 0.6B, 100M tokens, plus materialization | 0.5 |
| 6 token-form plus 65 block-form indexers plus 2 λ_x pre-step indexers, forward plus backward plus score traffic (0.7 for the wave-3 count of 45, plus 28 block-form indexers at about 0.02 each) | 1.24 |
| qwen3.5-4b-base replicate, arms (b), (c), (d), (i) × 2 seeds, 100M tokens | 0.9 |
| (k) dense + LM + L_x LoRA, 2 seeds × 60M tokens, with materialization | 1.2 |
| (j) dense + LM-only LoRA, 2 seeds × 60M tokens, no materialization | 0.8 |
| E1 eval, 5,300 (0.6B) plus 2,700 (4B) prompts, four conditions, shared forward, indexer key projections for 71 indexers, R^U rows from stored dense rows | 1.2 |
| E2 eval, 27 configurations (18 learned at seeds 42–44, 7 training-free, 2 LoRA) × 1,500 prompts ≤ 16K, sparse kernel | 1.9 |
| subtotal 7.74; × 1.25 = 9.7; **cap 10.0** | |

Phase 0b (optional; hard cap 2 GPU-h; runs whether Phase 0a passes or kills,
unless the adequacy-extension job ran, in which case Phase 0b is dropped so
the contract total stays at 16 GPU-h; external validity only, descriptive): inference-only probe of the production
QSA indexer in Qwen/Qwen3.8-Flash-Next @ de4b8e4d43b917e7706784d8bb445c9af86a3540
(about 360 GB bf16 across 8 × H100 with transformers device_map); hook the
indexer scores and the same layer's dense rows for the query tokens; E1/R^T/R^U
on 120 sealed prompts at 8K across the four conditions; a 20-prompt timing
probe must show ≤ 6 s per prompt or the job aborts and records throughput. At
120 prompts the recall SE is about 4.5 points, so the probe is descriptive and
never promotes or kills. GLM-5.3-Flash ships FP8 (about 321 GB) and would fit
the node; it is a future option, not part of this contract.

Phase 0a (4, or 4 + 1.5 with the conditional extension job) + Phase 1 (10) +
Phase 0b (2, dropped if the extension ran) ≤ **16 GPU-h**. Phase 2 (new
contract): from-scratch 60–125M 3:1 GDN plus QSA-style sparse-global hybrid
with a fertility-balanced BPE, about 30 GPU-h; QSA-style continued pretraining
of qwen3.5-4b-base, about 170 GPU-h. Tinker is not used (no indexer access;
key absent).

## Controls, Baselines, and Ablations

- Dense full-attention teacher as reference bound; R^T measured directly for
  each aggregation (hs, mp, rh) — the KL ceiling; one fixed reference R^U
  (union of per-head top-k, same k per head) and its budget-matched
  sensitivity row U_k shared by every aggregation; T* frozen on development
  languages by absolute CX recall within the MN band.
- Strongest label-free counterfactual (T*) KL-only on the identical bilingual
  concatenations (primary), with the DSA head-sum recipe as the secondary
  counterfactual and the full aggregation ladder with the Δ_T and S_T sanity
  rows for K2a.
- Per-arm tuning on development languages: indexer learning rate from
  {3e-4, 1e-3, 3e-3} in Phase 0a; λ_x from {0.25, 0.5} in the registered
  Phase-1 pre-step (block form, seed 42, 0.6B).
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
- Literalness: ML ceiling row and Λ reported for indexer, target and reference.
- Capacity: indexer dim ladder 64/128/256, iso-parameter otherwise; token
  versus block form.
- Iso-token and iso-order across all arms (one teacher stream), held-out
  languages never seen by L_x or L_sem, both query directions primary; five
  seeds for every block-form Phase-1 arm on the 0.6B base.

## Evaluation, Statistics, and Leakage Checks

Protocols followed: .claude/skills/experimental-design/SKILL.md,
.claude/skills/statistical-power/SKILL.md, and the ARS statistical reporting
standards (effect sizes with intervals, paired/clustered errors, multiplicity,
assumption checks).

Endpoints. E1: needle-token selection recall R_A(cond) per condition, base,
indexer, layer and language, with R^T and R^U; ξ_T, ξ^U_T, S_T, Δ_T, Λ and ρ_x
as defined. E2: TR-NIAH exact match (gold answer, answer language fixed to l_N
in every condition so answer-language effects cancel), plus Belebele
cross-lingual MC (permutation-controlled, chance 25%) as a descriptive
secondary. E3: English RULER-style NIAH/multi-key at the same k, and each
language's own MN condition. Primary endpoint of record: D, the absolute paired
E1 recall gain of (T*)+L_x over (T*) on the 14 held-out cross-script pairs at
ρ = 12.5% and 8K, block form on qwen3-0.6b-base, five seeds, in points;
confirm at D ≥ 6 with a 99% interval excluding zero; K2b at D ≤ κ; inconclusive
between. No ratio enters the decision.

Minimum worthwhile effect. Six recall points is the smallest per-language
repair a deployment would notice at k = 12.5% of an 8K haystack (about 60
selected needle tokens of a Belebele passage), and it equals 60% of the
ξ_T ≥ 10 localization gate that motivates Phase 1. Three points is the
reporting floor for secondary contrasts and the upper edge of the K2b kill
region, not a confirm threshold.

Noise estimate (assumed, marked unknown; measured in Phase 0a). No source
reports seed variance of indexer selection recall (SpotAttention and DSA report
single runs). Assumption: seed-to-seed SD of block-form E1 recall ≤ 2 points.
Prompt-level noise: Bernoulli with p ≈ 0.5 gives SE ≈ 1.6 points for an
unpaired difference of two 2,000-prompt means and ≈ 1.3 points paired. Wave 5
(Reviewer A's fix): the two components are combined, not chosen between.
Phase 0a measures σ̂ as the pooled within-configuration seed SD across the
three block-form configurations on qwen3-0.6b-base (3 seeds each, **6 df**;
the wave-4 "12 df" counted both bases and is withdrawn — 12 df applies only
under a declared cross-base homogeneity assumption), takes its one-sided
upper 80 percent chi-square bound σ_up, and measures se_prompt directly as
the paired passage-cluster bootstrap SE (seeds as fixed blocks, Belebele
passages resampled) of a null two-arm block-form contrast — hs versus mp
KL-only at matched seeds — on the audit partition at the primary prompt
count. se_D_up² = 2·σ_up²/5 + se_prompt² is recorded before Phase 1 is
submitted.

Resulting decision regions (closed form, normal approximation; implemented
and exercised in the doctor's `derive_decision_rule`). The wave-4 seed-only
figures (SE 1.26, MDE 4.3 at five seeds) are withdrawn: they ignored the
stated prompt component and rested on a variance estimate with 6, not 12, df.
Confirm at D ≥ max(6, MDE(se_D_up)) with the 99% interval excluding zero; kill
at D ≤ κ = max(0, min(3, 6 − 2·se_D_up)); the separation 6 − κ is at least
2·se_D_up whenever κ is above 0, and κ = 0 (se_D_up ≥ 3) withholds Phase 1.
Under the **assumed** inputs σ̂ = 2 (6 df) and se_prompt = 1.3 the rule gives
σ_up ≈ 2.80, se_seed_up = σ_up·√(2/5) ≈ 1.77, se_D_up ≈ 2.20, κ ≈ 1.6,
separation 4.4 and MDE(α = 0.01 two-sided, power 0.8) ≈ 7.5 points — above
the registered 6, which is why the confirm threshold is now max(6, MDE) fixed
from the measured noise model rather than 6 unconditionally; had 12 df been
claimed, σ_up would read 2.48 and κ 1.9, understating the noise. Both σ̂ and
se_prompt are measured, so κ and the confirm threshold are fixed by data
before Phase 1; the pre-registered fallbacks if 6 − κ under 2·se_D_up cannot
be met at the planned prompt count are (in order) more primary prompts per
held-out pair (the primary partition holds about 10,000 candidate prompts
for 5,300 planned), then seven seeds (se_seed shrinks by √(5/7)), then a
raised confirm threshold; each fallback is recorded before submission. The
band between κ and the confirm threshold is pre-registered as inconclusive
(reported, no claim, no promotion, no optional re-run). Five seeds are
unconditional for every block-form 0.6B arm; token-form (3 seeds), the 4B
replicate (2 seeds) and the LoRA pair (2 seeds) are descriptive. The ξ kill
screen needs only to separate ≤ 5 from ≥ 10: with SE(ξ) ≈ 1.15 points at
three seeds the 99% half-width is about 3 points, leaving the two regions
disjoint; the in-between band is pre-registered as inconclusive
localization. E2 MDE: at 1,500 prompts, 3 seeds and an assumed 2-point seed
SD the E2 SE is √(1.83² + 2·2²/3) ≈ 2.45 EM points and the MDE ≈ 8.4 EM
points, above the registered 8-point P3 effect, so K7's "E1 without E2"
clause is inconclusive, not a kill.

Ratio propagation. ρ_x = D / ξ^U_T* is reported with the denominator's own
passage-cluster interval and the ratio's interval from a paired bootstrap
(prompt clusters resampled once, both terms recomputed per replicate); with
ξ^U_T* near 10 and SE about 1.15, the denominator alone moves ρ_x by about
±0.12, which is why ρ_x carries no decision.

Randomization and blocking. Seeds 42–46 set indexer initialization, LoRA
initialization and the seeded shuffle that assigns haystack documents and
needle positions to prompts; the same assignment is used for every arm (blocked
by prompt). All indexers of one base train in one job from one teacher stream,
so data order and wall-clock are identical across arms (blocked by design; no
arm-versus-time confound). The 4B replicate, (j) and (k) are separate Slurm
jobs whose submission order is drawn by a seeded coin and recorded. Needle
positions are balanced within language and condition. Evaluation prompt order
is reshuffled per seed; MC option order is permuted per prompt. Learning rate
and T* are frozen on development languages in Phase 0a and λ_x in the Phase-1
pre-step, each before any held-out number is read; κ and the confirm
threshold are frozen from the measured Phase-0a noise model before Phase 1 is
submitted.

Analysis and reporting. Unit of analysis: the matched prompt (same H, N, p;
query language varied), clustered by Belebele passage id (every language
variant of a passage shares one cluster and one split); seed is a paired
blocking factor (each seed contributes a full arm pair), not a cluster to be
resampled. Effects in recall or EM points with 99% (primary) and 95%
(secondary) paired passage-cluster bootstrap intervals; per-seed and
per-language values always reported; assumption check by comparing bootstrap
and normal intervals and reporting the passage ICC and the per-seed spread.
Multiplicity: one primary contrast; Holm within the kill-condition family and
within per-language secondaries; the ML ceiling, Λ, Δ_T and S_T rows, U_k, ρ_x,
Belebele MC and Phase 0b are descriptive. Non-significant and inconclusive
results are reported in full.

Leakage. Belebele passage ids are split once by deterministic hash order
(seed 42) into 25% development, 25% Phase-0 audit and 50% Phase-1 primary
(the audit and primary partitions together are the sealed 75%) before any run;
K1, K2a, the adequacy gate, σ̂ and se_prompt read the audit partition only and
D reads the primary partition once, so no gate conditions the primary read on
its own prompts (wave 5, Reviewer A's fix; `split_passage_ids` and
`assert_reads_within` in the harness fail closed on a cross-partition read); held-out languages (ja, ko, bn, ta, el, he, ka cross-script;
id, tr, sw, nl, it same-script) never appear in L_x, L_sem or LoRA training;
TyDi QA's bn/ja/ko/sw/id portions are excluded; exact 50-gram plus MinHash
dedup of all training and haystack text against all evaluation text with
counts in the run receipt; needle-absent control bounds parametric recall;
prefix-invariance audit; the achieved-token ledger is published per prompt and
per language; the fixed reference uses only the dense rows already stored for
query tokens, never the alignment labels.

## Compute and Reproducibility

Image provenance (wave 5; repository records and the wave-5 brief; host not
re-audited from this Mac). The pilot image of record is the rebuilt
architecture image **cotcodec-research:999f5583-architecture** — Image ID
sha256:9d832a59fe348d149d2e4587ac6af90223e2956ebb646d7b19295298954ca5ad, repo
digest
`127.0.0.1:5000/cotcodec-research@sha256:bde90daa78c26cd2fb9d05036b0c9f9613c2386b9d7561816b541d2736c79f5d`,
built by Slurm job 353 from commit 999f5583 with
infra/slurm/host-single-node/build-architecture-image.sbatch (host networking,
because the bridge has no DNS); contents torch 2.11.0+cu128, transformers
5.15.0, flash-linear-attention 0.5.2, fla-core 0.5.2, triton 3.6.0 (R45). It
is the first real image containing fla, so the older discovery image
`127.0.0.1:5000/cotcodec-research@sha256:15d6abc06fa53ab466087a92107da9c58e469615e2f56a683fefd0a7600277f3`
(Image ID sha256:ca32b5c26b92fbe2a7054ae96543cd62928b0493896ec355b869b612022aa9a2,
created 2026-08-16, no fla) and the jobs 335–341 image
`127.0.0.1:5000/cotcodec-research@sha256:3f58e5256dff74ed3017a00af125e6ee2b6e4745208b9ea8a3668633760dfb00`
(Image ID sha256:785f16e880d8c38acef02254adaccfb48dfd3a374af12115ec88590f036bf81a)
remain provenance anchors only and are no longer cited for pilots. **The
rebuilt image still cannot run this pilot**: it predates this contract's code
(the NumPy doctor and the not-yet-written GPU entry point), lacks peft, and
lacks tilelang, which is being added to the `architecture` extra because fla
0.5.2 refuses the gated GDN backward on Hopper under Triton below 3.7.1
("Triton ≥ 3.4.0 and under 3.7.1 on Hopper GPUs produces incorrect results for
gated chunk_bwd_dqkwg (see fla #640); upgrade Triton to ≥ 3.7.1 or install
tilelang" — quoted from the repository's record of Slurm job 354; torch
2.11.0 pins triton 3.6.0). Any GDN number produced with fla 0.5.2 on H100
without tilelang is invalid, so the image must be rebuilt with tilelang, peft
and this contract's code, re-pinned by digest, and its Image ID entered as
the manifest's image_id only after a smoke run inside it attests the code
path. Checkpoint receipts (wave 5, R46): Slurm job 356 fetched ten pilot
checkpoints with receipts under /home/kevin/cotcodec-runs/hf-cache/cotcodec-receipts/
on fal-h100-01 — registry ids qwen3.5-4b-base (revision 1001bb4d…, artifact
root c7fbfd6bd1c73b9a…, 9.34 GB), qwen3-1.7b-base, transformer-1.3b-100b,
gla-1.3b-100b, transformer-340m-10b, gla-340m-15b,
gdn-1.3b-isp-hybrid-3to1-50b, gdn-340m-isp-hybrid-3to1-10b,
e2-ttt-mlp-1.3b-15b and rwkv7-1.5b-world (per
research/frontier-systems-program-2026-09-01.md). This contract's 4B arms
therefore use qwen3.5-4b-base; qwen3-0.6b-base, the manifest model, is not in
that batch and needs its own receipt, and no receipt digest has been copied
into the manifest, so model.receipt_sha256 and model.artifact_root_sha256
stay absent.

Launch. The wrapper `scripts/submit_docker_research_job.py` validates the
whole contract YAML as a job manifest (`validate_manifest`) and only then
renders the `sbatch` argv. The wave-3 contract carried none of the manifest
fields and was rejected at the first check; the wave-4 contract declares the
truthful subset (runtime docker-single-node-discovery-v1; resources gpu_type
h100, gpus 8, cpus 64, memory_gb 512, minutes 30 = 4.0 GPU-h, matching the
Phase-0a cap; budget.max_gpu_hours 4.0; randomness_contract
assignment-seed-matrix with the three Phase-0a seeds; run_root under
/home/kevin/cotcodec-runs/translation-supervised-sparse-indexer/phase-0a;
model qwen3-0.6b-base @ da87bfb608c14b7cf20ba1ce41287e8de496c0cd; the
not-yet-written command argv) and deliberately omits image_id, git_sha,
source_sha256, model.cache_host_path, model.receipt_sha256 and
model.artifact_root_sha256, because no image or model-fetch receipt exists for
this contract and any value would be an invented digest. Both dry-runs were
executed on 2026-09-01 and are recorded verbatim:

```text
# wave-3 contract
uv run python scripts/submit_docker_research_job.py \
  experiments/architectures/translation-supervised-sparse-indexer.yaml --dry-run
runtime must be docker-single-node-discovery-v1

# wave-4 contract
uv run python scripts/submit_docker_research_job.py \
  experiments/architectures/translation-supervised-sparse-indexer.yaml --dry-run
image_id must be an exact local Docker sha256 image ID
exit=1

# wave-5 contract (this proposal; re-run 2026-09-01 after the wave-5 edits)
uv run python scripts/submit_docker_research_job.py \
  experiments/architectures/translation-supervised-sparse-indexer.yaml --dry-run
image_id must be an exact local Docker sha256 image ID
exit=1

# Phase-0 CPU doctor (executed 2026-09-01; exit 0; synthetic-case numbers only)
uv run python scripts/run_translation_supervised_indexer_doctor.py \
  --output data/results/translation-supervised-sparse-indexer/phase0-doctor.json

# after the rebuilt image and model receipt exist (not yet run):
uv run python scripts/submit_docker_research_job.py \
  experiments/architectures/translation-supervised-sparse-indexer.yaml --dry-run \
  --dry-run-output evidence/translation-supervised-sparse-indexer/phase-0a-dry-run.json
uv run python scripts/submit_docker_research_job.py \
  experiments/architectures/translation-supervised-sparse-indexer.yaml
# argv shape rendered by sbatch_argv() in the wrapper source (read, not yet emitted):
#   sbatch --parsable --partition=research --nodes=1 --ntasks=1
#     --job-name=translation-supervised-sparse-indexer --gres=gpu:h100:8
#     --cpus-per-task=64 --mem=512G --time=00:30:00 --signal=B:USR1@180
#     --output=/home/kevin/cotcodec-runs/translation-supervised-sparse-indexer/phase-0a/slurm-%j.out
#     --export=COTCODEC_IMAGE_ID=...,COTCODEC_MANIFEST_JSON_HEX=...,COTCODEC_SEEDS=42:43:44,...
#     infra/slurm/host-single-node/docker-research.sbatch
```

The Launch block is therefore true as written: the dry-run still exits 1 at
image_id (image_id is deliberately not filled from the rebuilt image, which
would make the dry-run pass without a runnable job), and the accepted dry-run
JSON is a required artifact that does not exist. No sbatch command has been
emitted for this contract. The CPU doctor's receipt exists
(data/results/translation-supervised-sparse-indexer/phase0-doctor.json,
status PHASE0_DOCTOR_PASS, implementation sha256 dee5318d254d9623…, payload
sha256 3a50150c3c3c0145…) and is executability evidence only.

seeds: [42, 43, 44, 45, 46]
gpu_hours: 16

Seed usage: Phase 0a and the manifest above use the first three seeds; Phase-1
block-form arms on qwen3-0.6b-base use all five unconditionally; token-form
arms use three, the 4B replicate and the LoRA pair two (descriptive). Phase
caps: Phase 0a 4, Phase 1 10, Phase 0b 2 GPU-h on 8 × H100 80GB (one node;
Slurm 21.08.5, single node, no Pyxis — the publication lane needs cgroup-v2
Slurm plus Pyxis, so results from this node are pilot receipts, not publication
receipts). Checkpoints: atomic writes every 15 minutes to
/home/kevin/cotcodec-runs/translation-supervised-sparse-indexer/phase-{0a,0a-ext,1,0b}/seed-{42,43,44,45,46}/;
the batch script delivers SIGUSR1 180 s before the time limit
(`--signal=B:USR1@180`), which triggers a checkpoint and clean exit; every
phase must pass a fresh-job continuation equivalence test (resume from
checkpoint reproduces the next logged metric to tolerance) before its numbers
count. Artifacts: model and data license receipts with immutable revisions;
passage-id partition manifest (development / audit / primary), dedup report
and achieved-token ledger; indexer weights per arm and seed; the
learning-rate, T*, λ_x, noise-model (σ̂, df, σ_up, se_prompt) and κ freeze
records; the Phase-0 CPU doctor receipt; E1
(indexer, target, R^U, U_k), E2 and E3 receipts per prompt; kernel timing
logs; the K2a aggregation ladder with Δ_T and S_T rows; MFU measurement from
the first job; the accepted dry-run JSON; the container smoke and Slurm
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
text under TED's CC BY-NC-ND 4.0 usage policy, fetched 2026-09-01: no
commercial use, no derivative works, sharing only with attribution and a link.
Consequences adopted: TED2020 text is used for training only inside this
non-commercial research pilot; the bilingual concatenations built from it are
derivative artifacts and are never released — only their hashes and the
builder code are — and no TED-derived text appears in any receipt, prompt dump
or paper table (prompts use Belebele/FLORES+/WMT24++/FineWeb-2 only).
FineWeb-2 ODC-By 1.0; Belebele and FLORES+ CC-BY-SA 4.0; WMT24++ apache-2.0;
TyDi QA: the card's body license field reads "More Information Needed" while
its metadata tag says apache-2.0 (fetched 2026-09-01), so the license is
unconfirmed and arm (i) is gated on checking the original TyDi QA release
license before any TyDi text is loaded; Qwen3-0.6B-Base and Qwen3.5-4B
apache-2.0; Qwen3.8-Flash-Next qwen-community-1.0 (non-standard; review before
publishing probe numbers). General Translation document pairs are under client
contract, not redistributable, and not required by any prediction; the license
of any such parallel data used as an upgrade is unknown to this proposal and
must be recorded per pair before use. No kernel-level delta-rule contribution,
so the NVIDIA gated-delta-network and Google compressive-memory patent flags do
not apply.

Red lines (stop and report): any evaluation quantity computed from alignment
labels; any held-out language entering training data; publication or release
of TED-derived or GT-derived text, including the bilingual concatenation
artifacts; over 5% regression on E3 or any per-language recall floor breach
that is not reported; any Phase 0b number published before the
qwen-community-1.0 review; any TyDi QA text loaded before its license is
confirmed.

### Integrity gate

Protocol: scratchpad ext/ars/academic-pipeline/references/ai_research_failure_modes.md
(seven modes; status per mode for this proposal at the spec stage).

1. Implementation bug passing self-review — PARTIAL (wave 5): the NumPy
   Phase-0 objects ran under 16 tests with an analytic-gradient check against
   central finite differences, a brute-force check of the fixed-reference
   builder, fail-closed leak and causality checks and a tamper test on the
   doctor's own output path; nothing has run on a model, so the GPU code path
   is still unreviewed by execution. Mitigations pre-registered for the GPU
   side: the adequacy gate (a broken indexer fails English ML recall), the bug
   tell (indexer above its own target), receipts with exit code and warning
   count for every number.
2. Hallucinated citation — CLEAR at this stage: every source in the claim
   registry has a URL and a status; two ids were corrected in wave 3 (RTPurbo
   2608.26449 → 2605.16928) or added (2606.07703); wave 4 fetched the three
   previously unopened pages (R19, R24, R28) and read the QSA HTML through
   §3.2 (R06, R41); remaining unopened items are marked.
3. Hallucinated experimental result — CLEAR: no model-derived experimental
   number is reported; the only executed numbers are the CPU doctor's
   synthetic-case numbers, labelled as such here and in the receipt's
   evidence_grade string; all other numbers are sourced facts, design
   parameters or derivations labelled as such; the three wrapper dry-run
   outputs are quoted verbatim from runs on this Mac.
4. Shortcut reliance — the wave-3 and wave-4 repairs exist for this mode:
   literalness (MN reference, Λ), target aggregation judged on the excess
   statistic (wave-3 shortcut, replaced by absolute CX recall against a fixed
   reference), loss form (L_perm/L_half with inertness), semantic sharpening
   (L_sem), bilingual exposure (b), token budget (achieved-budget ρ),
   parametric recall (needle-absent), forced-selection denoising (oracle-sign
   rule), superset-budget reference (U_k sensitivity row). Flagged for Stage-3
   review.
5. Bug reframed as insight — the only pre-registered "surprise" is ξ_T ≥ 10;
   it counts only if the adequacy gate, the synthetic toy and the aggregation
   ladder are mutually consistent, and never on the literal leg alone. An
   inconclusive D is reported as inconclusive, never as a trend.
6. Methodology fabrication — CLEAR: methods are stated in the future tense;
   run configs, revisions and split hashes are receipts, not prose; every
   configuration number comes from a Hugging Face config, not from a run; the
   wave-3 claim that the wrapper "emits the sbatch call" was false and has
   been replaced by the verbatim rejection.
7. Frame-lock — SUSPECTED and managed: the wave-1 frame ("alignment supervision
   fixes indexers") has been demoted three times; the load-bearing claim is
   now the diagnostic, K2a on absolute shortfall can end the alignment line,
   the primary endpoint is an absolute gain with a pre-registered inconclusive
   band, and the negative-result section commits to publishing the
   localization negative, the recipe finding or the seed-variance finding.

## Negative-Result Value

K1 (ξ_T ≤ 5 everywhere): the cross-lingual long-context gap in sparse models is
inherited from attention mass, not from the selection component — the first
component-level localization of the gap MLNeedle, OneRuler and MGAL describe,
plus a portable per-language selection-recall instrument for any DSA/QSA
checkpoint. K2a: a label-free target aggregation recovers ≥ 80% of the
head-sum indexer's cross-script shortfall from the fixed reference — a free
recipe finding for every sparse-attention lab, a direct comparison of the DSA
and QSA target choices on a dimension neither reports, and (via the Δ_T row)
the first statement of which aggregation's *target* is itself cross-lingually
weak. K2b (D ≤ κ) or (b) ≈ (c): bilingual document exposure alone repairs
indexers. Inconclusive band (κ under D under 6): the honest outcome that the
wave-3 design would have mislabelled; it is published with the measured seed
variance, which no indexer paper reports. κ = 0: indexer recall is too
seed-noisy for any two-arm contrast at this scale — a finding about the
instrument. K3: a mass-concentration regularizer, not alignment content, is
what indexers need. K4: monolingual semantic supervision does the work —
parallel data is not the active ingredient, which redirects the program away
from its unique asset and is worth knowing early. K6: alignment supervision is
a generic attention fix, not selection-specific. The Λ row is publishable on
its own as the first literalness-versus-language decomposition for learned
selectors. Phase 0b reports whether a production QSA indexer agrees with the
retrofit result either way. Every branch yields a receipt the field lacks; the
pilot is information-dense per GPU-hour precisely because most branches end
the line.

## Preflight Doctors

| Doctor | Status | Evidence | Remediation |
|---|---|---|---|
| Source | PASS-candidate | Cell notes: research/gauntlet/2026-09-01-frontier/wave1-candidates.md (inventor merge), wave1-verdicts.json, wave1-ledger.md row 2, wave2/translation-supervised-sparse-indexer.md (repair note), wave2-result.json ranked[2], wave2-ledger.md row 3, wave3-result.json (two fresh reviewers, criterion forms); sweep synthesis §1 A–H and §5 coverage; wave-4 fetches of TED policy, TyDi QA card, H100 page and QSA HTML; 56 URLs in this proposal, 49 on primary domains (doctor sourceCounts, wave 5) | Archive hashed source snapshots and query logs in the evidence bundle; the bundle does not exist yet |
| Citation | PASS-candidate | Claim registry R01–R51 per ext/ars/academic-pipeline/references/claim_verification_protocol.md (R45–R51 added in wave 5 for the rebuilt image, the checkpoint receipts, the doctor receipt, the wave-5 dry-run, the wave-4 scores, the fla guard and the registered 4B base); every number has a URL or a labelled derivation; first-party items marked; the three wave-3 UNVERIFIABLE_ACCESS rows (R19, R24, R28) were fetched in wave 4 and re-statused; R24's license stays unconfirmed because the card's fields conflict | Confirm the TyDi QA release license at its origin; read QSA tables after §3.2; run an independent line-by-line audit |
| Novelty | PASS-candidate | Wave-2 refuter did not refute (0.6); blind discrimination: different mechanism, prior does not dominate (0.8); ledger with bounded wording; 2606.07703 the monolingual precursor; wave-4 QSA read through §3.2 found no per-language indexer table (R41); both wave-3 reviewers PARTLY_MEETS on Originality (coverage hole and transferred loss) | Signed provider-distinct novelty review; read the 4 unread OpenReview hits, QSA tables after §3.2 and the GLM-5.3 report; keep PRISMA counts |
| Design | PASS-candidate | Contract experiments/architectures/translation-supervised-sparse-indexer.yaml passes validate_architecture_experiments.py (2026-09-01, wave 5, with a reference_doctor block naming harness/translation_supervised_indexer.py and scripts/run_translation_supervised_indexer_doctor.py); wave-5 re-registration: audit/primary passage partition, noise model with honest df and combined seed plus prompt SE, κ and confirm threshold fixed from measured noise, λ_x pre-step, K7 demotion, E1 prompt counts unambiguous; wave-4 items retained (T* on absolute CX recall within an MN band, K2a on absolute shortfall against R^U, inconclusive band, five seeds); the CPU doctor exercises every gate function on synthetic controls; K-Dense experimental-design and statistical-power protocols followed | Re-judge after the re-registration; measure σ̂, se_prompt and κ in Phase 0a |
| Compute | FAIL | The NumPy Phase-0 doctor exists and passes (R47; executability and gate semantics only, synthetic numbers) but no real model loop, benchmark adapter, container smoke run or accepted Slurm dry-run is attested; `scripts/submit_docker_research_job.py --dry-run` re-run in wave 5 still exits 1 with "image_id must be an exact local Docker sha256 image ID" (R48); the rebuilt image with fla 0.5.2 (R45) predates this code and lacks tilelang and peft; checkpoint receipts exist on the host for qwen3.5-4b-base and nine others (R46) but not for qwen3-0.6b-base and none is copied into the manifest; MFU assumed; the throughput doctor is blocked on the tilelang rebuild; fla parallel_nsa head-count assertion unresolved | Write the GPU entry point and the tokenizer-based builders, rebuild the image with tilelang, peft and the code, re-pin it, fill image_id/git_sha/source_sha256 and the model receipts from real artifacts, run the 20-prompt smoke and an accepted dry-run with --dry-run-output, measure MFU, then set execution.enabled |
| Safety | PASS-candidate | Monitorability, data rights (TED CC BY-NC-ND 4.0 fetched, with the no-derivative consequence adopted; TyDi QA license unconfirmed and gating arm (i); unknown licence for any GT parallel data) and red lines stated; integrity gate answered for all seven modes | Runtime evidence: bilingual-distractor test, per-language floor receipts, licence confirmations hashed into the bundle |

## Independent Adversarial Reviews

Reviewer A: FAIL | provider=anthropic | model=claude | run_id=wave4-judge-A-2026-09-01 | artifact=research/gauntlet/2026-09-01-frontier/wave4-result.json (internal preliminary, NOT provider-distinct, unsigned; total 62/100; fatal defect: the wave-4 decision rule rested on a noise model the text contradicted — σ̂ had 6 df on the 0.6B base, not 12; the seed-only SE 1.26 ignored the stated paired prompt SE of about 1.3, so the combined MDE was near 6.2 rather than 4.3 and the confirm–kill separation about 1.7 SE; and the Phase-0a gates read the same sealed prompts on which D was later judged)

Reviewer B: FAIL | provider=anthropic | model=claude | run_id=wave4-judge-B-2026-09-01 | artifact=research/gauntlet/2026-09-01-frontier/wave4-result.json (internal preliminary, NOT provider-distinct, unsigned; total 69/100; fatal defect: λ_x, the primary treatment arm's only hyperparameter, was declared frozen on development languages in Phase 0a where no L_x indexer is trained and Phase 1 contained no λ_x sweep, exposing the primary contrast to a post-hoc choice; secondary: the E1 FLOP row was reproducible only under a favourable reading of the prompt count with attention FLOPs excluded)

Both reviews are internal gauntlet judges from the same provider and are not
Ed25519-signed by a trusted attestor; the accepted score is therefore capped
at 89 and the proposal is not pilot-ready regardless of content. Both reviewers
completed the ARS criterion-bound form (calibration NOT_CALIBRATED):
Originality, Methodological Rigor, Evidence Sufficiency and Significance
PARTLY_MEETS and decision-bearing for Reviewer A; Originality and
Methodological Rigor PARTLY_MEETS for Reviewer B; Writing Quality and
Literature Integration MEETS; no criterion was DOES_NOT_MEET. Their
fatal_defect and highest_impact_fix texts are recorded in wave4-result.json and
are the sole source of the wave-5 change; the wave-3 judges (66/66) remain
recorded in wave3-result.json and the wave-2 judges (64/61) in
wave2-result.json and in the Iteration Log. Both wave-4 reviewers named the
missing executable pilot as the binding cap (79); the wave-5 CPU doctor is
the first executable object of this direction and lifts nothing by itself
until a fresh review reads it.

## Scorecard

| Dimension | Reviewer A | Reviewer B | Defect/evidence |
|---|---:|---:|---|
| Question and strategic fit | 6 | 7 | Empty axis confirmed by every sweep cell; retrofit-population qualifier carried; attachment-capability is a diagnostic plus a detached-indexer loss, not the architecture-level move the brief prefers |
| Primary-source evidence | 7 | 8 | 56 URLs, 49 on primary domains (doctor count, wave 5); claim registry R01–R44 in wave 4, R45–R51 added in wave 5; QSA later tables, GLM-5.3, MSA and FlashMemory bodies unread |
| Defensible novelty delta | 5 | 6 | Loss is a transfer of guided NMT attention; delta rests on the untested diagnostic; coverage cap 74 until OpenReview and full texts are read |
| Mechanism and falsifiability | 8 | 8 | Non-literal ξ with Λ; T* on absolute CX recall; K2a on absolute shortfall; wave 5: κ from a fully specified noise model, K7 demoted where underpowered |
| Controls and causal identification | 7 | 8 | Wave 4 closed the T* excess-statistic hole; wave-4 reviewers found λ_x without a producing step (fixed in wave 5 by the registered pre-step) and gates reading the primary prompts (fixed by the audit/primary partition) |
| Evaluation and statistics | 6 | 7 | Wave-4 rule derived from a contradicted noise model (df 6 not 12; seed-only SE); wave 5 combines seed and prompt components at an upper confidence bound, fixes the confirm threshold at max(6, MDE) and measures se_prompt by cluster bootstrap |
| Feasibility and information per GPU-hour | 6 | 6 | E1 FLOP row ambiguous in wave 4; wave 5 states 2,000/1,200/800 prompts per length per base, includes attention-score and indexer-scoring FLOPs (E1 1.40 GPU-h, Phase 0a 2.64/3.3/cap 4) and registers the adequacy extension as a second job |
| Reproducibility and artifact contract | 5 | 5 | No container smoke, accepted dry-run or model-loop attestation; wave 5 adds the executable CPU doctor with a receipt, cites the rebuilt fla image and the checkpoint receipts; dry-run still exits at image_id; cap 79 |
| Safety, data rights, and monitorability | 7 | 8 | TED policy fetched (no-derivative consequence adopted); TyDi QA license unconfirmed and gating; GT parallel data now governed by the sealed inventory (customer TM excluded) |
| Independent adversarial review quality | 5 | 6 | Two internal same-provider judges, unsigned; wave-5 design unjudged; cap 89 |
| **Total** | **62** | **69** | Lower total (62) is authoritative for the wave-4 text — a dip from 66, recorded; the wave-5 text is unjudged; caps 74 (coverage), 79 (no executable GPU pilot; the CPU doctor is executability evidence only), 89 (no provider-distinct signed review) apply |

## Iteration Log

| Wave | Score | Highest-impact defect | Change | Result |
|---:|---:|---|---|---|
| 1 | 0 (killed) | Identification refuted (0.8): aligned-block recall equalled the training label; retrofit-versus-architecture and token-budget confounds; external aligner asymmetry. Feasibility refuted (0.8): no parallel data in the repo, NumPy-only doctor, uncosted evaluation. See research/gauntlet/2026-09-01-frontier/wave1-ledger.md row 2 | None in wave 1 (killed before judging) | Killed; novelty not refuted (0.6), so admitted to wave 2 with a repair owner |
| 2 | 61 | Judges' shared fatal defect: the pre-registered counterfactual for every L_x claim was the head-sum KL arm, the weakest target aggregation in the class the candidate claims to fix, while ξ compared a verbatim-copy monolingual query with a zero-overlap cross-lingual query | Ten identification and five feasibility repairs (sealed non-label endpoints, attachment-capability scope, achieved-budget k, R^T and ξ, corpus-given labels, no aligner, public data plan, shared-teacher budget, Tinker removed) per wave2/translation-supervised-sparse-indexer.md | Judged 64/61 (lower authoritative 61), ranked 3 of 4, cap 89; identification still refuted (0.72) |
| 3 | 66 | Same defect, as the wave-2 judges' union highest_impact_fix | One repair — identification re-registration: (1) both ξ legs non-literal (Belebele question-as-query in l_N as the reference; literal copy is a ceiling row; Λ reported); (2) strongest label-free target T* chosen in Phase 0 on development languages becomes the primary counterfactual; K2a (de-diluted target recovers ≥ 80% of ξ_hs) and K2b (L_x recovers under 30% of residual ξ_T*) registered; (c) versus (b) demoted to a DSA-style secondary; (3) inertness preconditions |d − b| ≤ 1 and |e − b| ≤ 1 before L_perm/L_half count; (4) information-matched L_sem arm, LM-only LoRA arm (j) so (k) − (j) isolates the dense L_x effect, headroom gates G1 (dense cross-lingual EM ≥ 40%) and G2 (sparse floor ≥ R^T − 5), oracle-sign rule and needle-absent control on P3; (5) 2606.07703 cited as the monolingual precursor of the ξ decomposition, RTPurbo id corrected to 2605.16928, indexer-adequacy gate, Q-head padding or gather path for parallel_nsa, Phase 0b threshold 6 s with 120 prompts at a 2 GPU-h cap, qwen3.5-4b relabelled post-trained with Qwen3.5-4B-Base named as the unregistered preferred base; budget re-derived to 4 + 10 + 2 = 16 GPU-h | Judged by two fresh reviewers 66/66 (up from 61; lower authoritative 66); controls scored 8/7 versus 4/4 in wave 2; two new fatal defects found — (A) confirm and kill regions of the Phase-1 rule 3 points apart inside the 5.6-point MDE, ratio denominator without an interval, wrapper dry-run rejects the contract, "only real image" stale; (B) T* = argmin ξ_T can select a cross-lingually weaker target and K2a on ξ_T*/ξ_hs can fire for the wrong reason; Originality, Rigor, Significance PARTLY_MEETS (both), Evidence Sufficiency and Coherence PARTLY_MEETS (B); no DOES_NOT_MEET |
| 4 | 62 (judged 62/69 after the change; lower total authoritative; a recorded dip from 66); history 0 → 61 → 66 → 62 | Union of the wave-3 reviewers' highest_impact_fix texts (compatible; no conflict required a choice): (A) decision rule not decisive at registered power; (B) T* and K2a operationalised on the excess statistic | One repair with two compatible parts. From Reviewer B: T* = argmax_T R_ind^T(CX) on development languages within a 2-point MN band; one fixed reference R^U (union of per-head top-k of the frozen layer's full attention, same k per head) shared by every aggregation, with a budget-matched U_k sensitivity row; K2a re-registered as "best label-free indexer recovers ≥ 80% of the head-sum indexer's cross-script shortfall S_hs from R^U", evaluable only when S_hs ≥ 3; ξ_T kept as K1's uniform null and as a descriptive table; Δ_T-per-aggregation sanity row. From Reviewer A: primary endpoint stated as the absolute paired gain D = R_c(CX) − R_b(CX) ≥ 6 points; five seeds [42, 43, 44, 45, 46] unconditional for every block-form Phase-1 arm on the 0.6B base (MDE about 4.3 points versus 5.6), token-form and 4B arms descriptive; K2b at D ≤ κ with κ = max(0, min(3, 6 − 2·σ̂·√(2/5))) fixed from the Phase-0a pooled seed SD so confirm and kill regions are at least two measured SEs apart; the band between κ and 6 pre-registered as inconclusive; Phase 1 withheld if κ = 0; ρ_x demoted to descriptive with the denominator's interval propagated; contract given the wrapper's manifest fields that can be declared truthfully (runtime, resources, budget, randomness contract, seeds, run_root, model id and revision, command) and the dry-run re-run — it now exits 1 at "image_id must be an exact local Docker sha256 image ID", recorded verbatim; image provenance corrected to name both recorded real images (15d6abc0…/ca32b5c2… and 3f58e525…/785f16e8…, jobs 335–341) plus nine further recorded digests, with the false "only real image" and "emitted sbatch" claims withdrawn; the SIGUSR1 offset corrected to the batch script's 180 s. Also, addressing decision-bearing PARTLY_MEETS rows without inventing evidence: TED policy, TyDi QA card and H100 page fetched (R19, R24, R28 re-statused; TyDi QA license found conflicting and now gates arm (i); TED no-derivative consequence adopted in Safety); QSA HTML read through §3.2 (R06 VERIFIED, R41 added: only aggregate MMMLU); per-arm learning-rate sweep added on development languages; held-out cross-script pairs enumerated (14 pairs, both directions); budgets re-derived to Phase 0a 2.37/3.0/cap 4 and Phase 1 7.7/9.6/cap 10 | Judged by two fresh reviewers 62/69 (lower authoritative 62 — a dip from 66, recorded, not erased); new fatal defects: (A) the decision rule rested on a noise model the text contradicted (σ̂ has 6 df on the 0.6B base, not 12; seed-only SE 1.26 ignored the stated prompt SE 1.3, combined MDE near 6.2 not 4.3, separation about 1.7 SE) and the Phase-0a gates read the same sealed prompts as D; (B) λ_x had no producing step (declared frozen in Phase 0a where no L_x indexer exists; no Phase-1 sweep) and the E1 FLOP row was reproducible only with attention FLOPs excluded; both named the missing executable pilot as the binding cap (79); validator PASS, doctor FAIL as expected |
| 5 | 62 (unjudged since the change); history 0 → 61 → 66 → 62 → pending; waves budget raised 4 → 5 by the wave-5 orchestrator brief and recorded here | Reviewer A (authoritative lower total): decision rule from an unmeasured, self-contradicted noise model and gate prompts not separated from primary prompts; Reviewer B (compatible, applied in the same repair): λ_x without a registered producing step; E1 FLOP row ambiguous | One registered repair with two compatible parts plus the executable pilot. From Reviewer A: the sealed 75 percent split partitioned by passage id into a Phase-0 audit partition (K1, K2a, adequacy, σ̂, se_prompt) and a Phase-1 primary partition read exactly once for D, with fail-closed reads in code; σ̂ declared at its honest 6 df (12 only under a declared cross-base homogeneity assumption); se_prompt measured by a paired passage-cluster bootstrap (seeds as blocks) of a null hs-versus-mp KL-only contrast at the primary prompt count; se_D_up² = 2·σ_up²/5 + se_prompt² with σ_up the upper 80 percent chi-square bound; κ = max(0, min(3, 6 − 2·se_D_up)); confirm threshold max(6, MDE(se_D_up)) fixed before Phase 1; fallbacks (more primary prompts, seven seeds, raised threshold) pre-registered; E2 MDE stated (about 8.4 EM points) and K7's "E1 without E2" demoted to inconclusive. From Reviewer B: a budgeted Phase-1 pre-step training (T*)+L_x at λ_x 0.25 and 0.5 on development languages (block form, seed 42, 0.6B, about 0.04 GPU-h), λ_x frozen by development CX recall within the 2-point MN band and recorded, removed from the Phase-0a freeze list; the E1 row re-derived with 2,000/1,200/800 prompts per length per base and attention-score plus indexer-scoring FLOPs (1.40 GPU-h; Phase 0a 2.64 base, 3.3 with reserve, cap 4.0 = one 30-minute 8-GPU job) and the adequacy extension registered as a second conditional 1.5 GPU-h job that displaces Phase 0b. Executable pilot: harness/translation_supervised_indexer.py, scripts/run_translation_supervised_indexer_doctor.py and tests/test_translation_supervised_indexer_doctor.py (16 tests) written; the doctor ran to PHASE0_DOCTOR_PASS in 25 s CPU on 10 registered synthetic cases (positive control at seeds 42–44 with ξ_hs 52.2/80.0/46.5 and D 51.0/80.5/46.5 points on a held-out language; permuted-label, other-half and shifted-script negative controls; brute-force reference check; gradient check; leakage, causality and 28 degenerate-input rejections; gate semantics), receipt data/results/translation-supervised-sparse-indexer/phase0-doctor.json with an evidence_grade stating executability and gate semantics only; reference_doctor block added to the contract (validator PASS). Provenance: the rebuilt image cotcodec-research:999f5583-architecture (fla 0.5.2, triton 3.6.0; tilelang being added per fla #640) cited as the pilot image with what it still lacks; the ten checkpoint receipts cited; the 4B arms moved to the now-registered qwen3.5-4b-base; dry-run re-run (still exits at image_id, recorded verbatim) | Pending re-judging; not pilot-ready (Compute FAIL — no GPU entry point, no image with this code, dry-run exits at image_id; no evidence bundle; no signed reviews); validator PASS and pytest 16 passed on 2026-09-01 |

The evidence bundle evidence/translation-supervised-sparse-indexer/bundle.json
does not exist yet. Until the hashed source snapshots, query logs, container and
Slurm attestations, two Ed25519-signed provider-distinct reviews and the
hash-chained audit JSONL exist below that directory and match their recorded
SHA-256 hashes, the deterministic doctor returns FAIL and the accepted score is
0; a prose PASS cannot score itself upward.
