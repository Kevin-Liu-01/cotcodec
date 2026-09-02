# Research Direction: Semantic-Clock Gate Parity

**Status:** draft
**Owner:** Kevin Liu
**Source cutoff:** 2026-09-01
**Coverage limits:** WebSearch budget exhausted; arXiv API, Semantic Scholar and Jina blocked from the Mac (arXiv reached only through the H100 host at abstract level; 20 of 22 refuter arXiv queries returned 429); no OpenReview, ACL Anthology, patent or Chinese-language sweep beyond the 2026-09-01 verification pass; nothing executed on the H100 node or Tinker; no parallel corpus in the repository; Common Crawl language shares read from the public statistics page only; fertility and span-ratio figures are owner and refuter measurements, not published numbers (the measurement scripts exist only in the session scratchpad, SHA-256 recorded in the claim registry, not yet archived); the RWKV World tokenizer's fertility and the rwkv7-1.5B-world checkpoint's coverage of the 16-language grid are unmeasured; blind discrimination was run against the Gated DeltaNet substrate only, not against the mechanism ancestors Hirschi 2604.02474 and DeciMamba 2406.14528; the rebuilt image identity and the checkpoint receipts on fal-h100-01 were read from repository records (docs/local-model-lab.md, research/frontier-systems-program-2026-09-01.md) and the orchestration handoff, not re-inspected on the host by this cell; the phase-0 object doctor ran on this Mac's CPU only and every number it produced is synthetic.
**Budgets:** queries=60; wall_minutes=480; tokens=600000; dollars=20; waves=5; gpu_hours=16
**Novelty verdict:** NO_DIRECT_PRIOR_FOUND
**Safety verdict:** PASS
**Evidence bundle:** evidence/semantic-clock-gate-parity/bundle.json

## Claim and Research Question

In gated delta-rule and selective-SSM layers (Gated DeltaNet in Qwen3.5, KDA in
Kimi-Linear) the forgetting gate and the write gate are applied once per token.
Equal content therefore costs a high-fertility language proportionally more
cumulative forgetting and write mass in semantic time. Three ordered claims:

- C1 (measurement): released GDN and KDA gates do not self-normalize this away.
  The cumulative log-decay over a translated sentence scales with its token
  count (R_F(L) = F(x_L) / F(x_en) tracks fertility f_L rather than 1).
- C2 (within-model causal): rescaling the per-token log-decay of language L by
  1/r on a frozen checkpoint moves translation-paired recall that is forced
  through the recurrent state (prefix-blind readout: no attention hop crosses a
  sentence boundary anywhere in the episode), and the common-dose gain
  G_L = EM_L(r = 2) minus EM_L(r = 1) rises with log fertility after
  partialling out training-resource share, on two co-primary subjects
  (Qwen3.5-4B-Base prefix-blind and the attention-free rwkv7-1.5B-world), and
  the same dose-response is reproduced by English re-segmented to each
  language's token count (wave-5 repair: the headroom-invariant within-tokenizer
  warp reference; a cross-language slope that token count does not reproduce is
  language identity or headroom, K11); low-fertility non-Latin languages and
  low-fertility low-resource Malay behave like English. The argmax r*(L) is
  descriptive only (wave-4 repair: it degenerates to the grid boundary under a
  monotone dose-response).
- C3 (training-time mechanism, deferred to a separately contracted phase 1): a
  scale-invariant, English-anchored span-parity auxiliary loss on the existing
  gate statistics, supervised by sentence-aligned parallel text at training time
  only, closes the recall gap at unchanged per-language bits per byte with no
  inference change. It is pre-registered for equivalence against a per-language
  constant gate rescale.

Research question for this contract: on two released hybrid bases, is the
per-token clock a measurable, fertility-specific and recurrent-state-borne cost,
and does a per-language clock rescale port across GDN and KDA? Scope of this
contract is portability-protocol (ledger plus normalization recipe on released
checkpoints). The architecture-causal label is reserved for phase 1 and is only
earned if the phase-0 partial-slope gate passes. This relabelling is the
wave-3 repair recorded in the Iteration Log; the wave-4 repair (prefix-blind
primary readout, floor hold, common-dose estimand, probe-translation QA,
attention-free co-primary subject) and the wave-5 repair (synthetic-fertility
English comparator, K11, K10b, registered subjects, executable phase-0 object
doctor) are recorded there too.

## Strategic Fit and Why Now

Kevin's assets fit phase 0 exactly: a Docker and Slurm harness with hooks,
seeded episodes, exact-match generation and checkpoint-resume, and enough GPUs
to run the full 16-language grid with two prefix passes and three readouts per
cell in one node-day.
General Translation data is an optional upgrade (sub-sentence alignments,
terminology stress sets, human-verified templates), never a dependency: phase 0
runs entirely on public n-way parallel NTREX-128.

Why now: production hybrids with per-token gates are the 2026 default (Qwen3.5
3:1 GDN hybrids, Kimi-Linear KDA, Gated DeltaNet-2 released 2026-05), and the
2026-09-01 sweep found the delta-rule gate axis dense (GDN-2, QED, Preconditioned
DeltaNet) but nobody has measured or supervised the gate clock per language.
The frontier program's occupied table covers routing supervised by parallel data
(SARA, RA-MoE) and tokenizer-side parity (Parity-aware BPE, MAGNET); the
operator-internal clock is unoccupied. The phase-0 ledger and surgery are
publishable within weeks and form the first-mover claim; a negative C1 (gates
already warp-invariant) is itself the first measurement answering the
sequence-operators G1 gap.

## Primary-Source Evidence

Substrate. Qwen/Qwen3.5-4B-Base at revision 1001bb4d826a52d1f399e183466143f4da7b741b
([config.json](https://huggingface.co/Qwen/Qwen3.5-4B-Base/blob/1001bb4d826a52d1f399e183466143f4da7b741b/config.json))
is apache-2.0 with 24 `linear_attention` and 8 `full_attention` layers and a
vocab_size of 248,320; its tokenizer.json pre-tokenizer is mark-aware and splits
digits singly, so a 4-digit code is exactly 4 tokens. It is registered as
`qwen3.5-4b-base` in models/registry.yaml (registered 2026-09-01) and an
artifact receipt is reported under /home/kevin/cotcodec-runs/hf-cache/cotcodec-receipts/
on fal-h100-01 (Slurm job 356; CR-32). The transformers
[qwen3_5 modeling file](https://github.com/huggingface/transformers/blob/main/src/transformers/models/qwen3_5/modeling_qwen3_5.py)
computes beta_t = sigmoid(b_t) and g_t = -exp(A_log) * softplus(a_t + dt_bias)
in Python before the chunked delta-rule kernel, so g and beta surgery is a
function wrapper. The reference kernel is
[fla gated_deltanet.py](https://github.com/fla-org/flash-linear-attention/blob/main/fla/layers/gated_deltanet.py);
[fla v0.5.2](https://github.com/fla-org/flash-linear-attention/releases/tag/v0.5.2)
(2026-07-27) ships `gdn2.py`, `kda` and `rwkv7` ops. The second base is
[moonshotai/Kimi-Linear-48B-A3B-Base](https://huggingface.co/moonshotai/Kimi-Linear-48B-A3B-Base/tree/3b171c17bfc4ee348599b6781a2ca8715c21c8dc)
(MIT, custom code). The attention-free co-primary subject is
[fla-hub/rwkv7-1.5B-world](https://huggingface.co/fla-hub/rwkv7-1.5B-world/tree/004140baad7a62d49a26d97508ef19cf09672328)
at revision 004140baad7a62d49a26d97508ef19cf09672328 (card data read through
the Hugging Face API on 2026-09-01: license apache-2.0, base_model
BlinkDL/rwkv-7-world, custom_code, card languages en, zh, ja, ko, fr, ar, es,
pt; registered as `rwkv7-1.5b-world` with trust_remote_code and a receipt
reported by the same job, CR-32; custom-code review pending). RWKV-7 "Goose" ([2503.14456](https://arxiv.org/abs/2503.14456))
defines its recurrence as a generalized delta rule with vector-valued gating and
reports four models of 0.19B to 2.9B parameters trained on a 3.1T-token
multilingual corpus (first-party claim in the abstract); the constant surgery
maps onto its per-channel decay w_t as log w'_t = log w_t / r. Its coverage of
the 16 grid languages is unverified (the card lists 8 languages, none in the
high-fertility set), so per-language floors (K10) gate its use.

Corpora. [NTREX-128](https://github.com/MicrosoftTranslator/NTREX/tree/468c6b69c7f6a75d31d4743d9daba2af566cc18d)
at commit 468c6b69 (CC-BY-SA-4.0) has 1,997 n-way parallel sentences in every
language used here. [FLORES+](https://huggingface.co/datasets/openlanguagedata/flores_plus/tree/5fec6c13f9e5a4db2f745d4ec0d7c9721ddc4f06)
is sealed for phase 1. Probe translations use
[facebook/nllb-200-distilled-600M](https://huggingface.co/facebook/nllb-200-distilled-600M)
(CC-BY-NC-4.0, research use). Resource share comes from the
[Common Crawl language statistics](https://commoncrawl.github.io/cc-crawl-statistics/plots/languages).

Theory and mechanism ancestors. Gated DeltaNet
([2412.06464](https://arxiv.org/abs/2412.06464)) defines the recurrence and
reports S-NIAH-2 for 1.3B GDN at 100 / 99.8 / 92.2 for 1K / 2K / 4K contexts
(Table 2), which is why the old d = 32 regime was on ceiling. Tallec and Ollivier
([1804.11188](https://arxiv.org/abs/1804.11188)) prove learnable gates give
quasi-invariance to time warps; Hirschi ([2604.02474](https://arxiv.org/abs/2604.02474),
2026-04) rescales LSTM time constants by a known warp factor, the same operation
as the constant surgery g' = g / r on a different object. Kimi Linear
([2510.26692](https://arxiv.org/abs/2510.26692)) and GDN-2
([2605.22791](https://arxiv.org/abs/2605.22791)) supply channel-wise decay and
decoupled erase and write. Hybrid long-range retrieval is carried by the
attention layers ([2606.15378](https://arxiv.org/abs/2606.15378)), which is the
reason the prefix-blind readout, its floor hold and the attention-free
co-primary subject exist. Cross-lingual needle baselines on
softmax transformers: MLNeedle ([2408.10151](https://arxiv.org/abs/2408.10151))
and ONERULER ([2503.01996](https://arxiv.org/abs/2503.01996)). Tokenizer-side
parity and fertility: Parity-aware BPE ([2508.04796](https://arxiv.org/abs/2508.04796)),
MAGNET ([2407.08818](https://arxiv.org/abs/2407.08818)), Vowel Signs Are Not
Letters ([2608.26449](https://arxiv.org/abs/2608.26449)). Leino and Tiedemann
([2603.29026](https://arxiv.org/abs/2603.29026)) find parallel data barely moves
representations; gate statistics are a different observable. Leakage audit:
two-forward-pass prefix invariance ([2608.22876](https://arxiv.org/abs/2608.22876)).

Lineage added in wave 4 (requested by both wave-3 reviewers; every page opened
on 2026-09-01). Tokenizer-cost unfairness: Petrov et al.
([2305.15425](https://arxiv.org/abs/2305.15425), v2 2023-10-20) show that the
same text translated across languages differs in tokenization length by up to
15 times and that byte-level models still show over 4 times for some pairs;
Ahia et al. ([2305.13707](https://arxiv.org/abs/2305.13707), 2023-05-23) show
across 22 typologically diverse languages that token-based API pricing
overcharges speakers of many supported languages while returning poorer
results. Both locate the cost at the tokenizer and the bill; this proposal
traces the same fertility ratio into the recurrent operator's forgetting and
write clock. Training-free manipulation of a frozen recurrent clock: DeciMamba
([2406.14528](https://arxiv.org/abs/2406.14528), v3 2025-04-09) exploits a
hidden filtering mechanism inside the S6 layer at inference time to extend
Mamba's context without additional training; it is the closest relative of the
constant surgery (frozen SSM, inference-time change to the selective
recurrence) and differs in target (length extrapolation, not cross-language
parity), warp factor (none; here tokenizer fertility) and test (no
cross-language dose-response).

### Claim registry

Protocol followed: scratchpad `ext/ars/academic-pipeline/references/claim_verification_protocol.md`.
Status vocabulary: VERIFIED (source read and matches), FIRST_PARTY (model card,
owner or refuter measurement, internal record), UNVERIFIABLE_ACCESS (source
exists, not reachable from this cell). Every number in this proposal is listed.

| claim_id | Claim text | Source URL and locator | Status |
|---|---|---|---|
| CR-01 | Qwen3.5-4B-Base has 24 linear_attention and 8 full_attention layers, vocab_size 248,320, apache-2.0 | https://huggingface.co/Qwen/Qwen3.5-4B-Base/blob/1001bb4d826a52d1f399e183466143f4da7b741b/config.json (layer_types, vocab_size); read by both wave-2 refuters | VERIFIED |
| CR-02 | Qwen3.5-4B-Base is 4.66B parameters in BF16 | https://huggingface.co/Qwen/Qwen3.5-4B-Base (model card, HF API safetensors metadata) | FIRST_PARTY |
| CR-03 | Its tokenizer splits digits singly, so a 4-digit code is 4 tokens; pre-tokenizer is mark-aware | https://huggingface.co/Qwen/Qwen3.5-4B-Base/resolve/1001bb4d826a52d1f399e183466143f4da7b741b/tokenizer.json (pre_tokenizer regex); feasibility refuter | VERIFIED |
| CR-04 | Qwen3-4B-Base uses a 151,936-vocab tokenizer with the letters-only word class, so no same-tokenizer attention sibling exists | https://huggingface.co/Qwen/Qwen3-4B-Base/resolve/main/config.json ; feasibility refuter | VERIFIED |
| CR-05 | Fertility on the Qwen3.5-4B-Base tokenizer over NTREX-128: pol 1.605, fin 1.627, hun 1.706, ukr 1.792, hin 2.073, ell 2.119, ben 2.164, tam 2.744, kor 1.284, tha 1.174, zho-CN 0.931, mya 4.18, rus 1.423, tur 1.429, msa 1.157; English 26.5 tokens per sentence | Owner measurement (tokenizers library, tokenizer.json above, NTREX commit 468c6b69), independently reproduced by the identification and feasibility refuters; the scripts exist in the session scratchpad with SHA-256 fert.py 0ed5a139a22d41c01fbbf9f89b684f898c39fd9606a6e60b5a7da0bc681af906, fert2.py e86582478faf95cbee18dc0e807160faa5335d27e8b204ffac783bbcf9dec17b, fert3.py 26dd09f927c8029dd30fdf15e60574b32f345b13702ca237ae0d67978ac3476d, feasibility fert.py 4d88fb0c1223fb7f75b0b6a897c83217f24514d3b0adb4ff5909c686720e5a99 (hashed 2026-09-01); NOT yet archived in the bundle, so these numbers are not yet re-derivable from the repository | FIRST_PARTY |
| CR-06 | Within-language per-sentence span-ratio CV 0.17-0.24 (owner) and 0.19-0.25 (refuter re-measurement); within-language sentence-length CV 0.50-0.53 | Same measurement as CR-05 (fert3.py, hash above, for the length CV); not yet archived | FIRST_PARTY |
| CR-07 | Log fertility and log Common Crawl page share (CC-MAIN-2026-34) correlate at Pearson -0.85 and Spearman -0.71 across the 8 high-fertility languages and -0.78 across 11 phase-0 languages | https://commoncrawl.github.io/cc-crawl-statistics/plots/languages joined to CR-05 by the identification refuter (fert2.py, hash above, which hard-codes the per-language page shares it read: pol 2.0638, fin 0.3823, hun 0.5341, ukr 0.8371, hin 0.2144, ell 0.5490, ben 0.1084, tam 0.0449, tha 0.3740, kor 0.8500, zho 4.3829, mya 0.0164 percent); the page snapshot itself is not archived | FIRST_PARTY |
| CR-08 | Common Crawl page shares: rus 6.9 percent, tur 1.4 percent, hun 0.53 percent, fin 0.38 percent, tha 0.37 percent, msa 0.086 percent; hin, ben and tam sit in the 0.2 percent or lower tier | https://commoncrawl.github.io/cc-crawl-statistics/plots/languages (CC-MAIN-2026-34 row); read by the identification refuter; no HTTP receipt or snapshot in the repository yet, so this is read-once evidence until archived | VERIFIED |
| CR-09 | NTREX-128 at commit 468c6b69 has 1,997 sentences per language and is CC-BY-SA-4.0 | https://github.com/MicrosoftTranslator/NTREX/tree/468c6b69c7f6a75d31d4743d9daba2af566cc18d (NTREX-128 directory, LICENSE) | VERIFIED |
| CR-10 | 1.3B Gated DeltaNet scores 100 / 99.8 / 92.2 on S-NIAH-2 at 1K / 2K / 4K | https://arxiv.org/abs/2412.06464 (Table 2), read by the feasibility refuter | VERIFIED |
| CR-11 | fla v0.5.2 was released 2026-07-27 with gdn2.py, kda and rwkv7 ops | https://github.com/fla-org/flash-linear-attention/releases/tag/v0.5.2 | VERIFIED |
| CR-12 | Hirschi (2026-04) rescales LSTM time constants by a known time-warp factor for transfer across timescales | https://arxiv.org/abs/2604.02474 (abstract), read by the novelty refuter | VERIFIED |
| CR-13 | Discovery image contents: CUDA 12.8.1, torch 2.11.0+cu128, transformers 5.15.0, accelerate, triton, no fla, vllm, peft or flash-attn; created 2026-08-16 | Host inspection on fal-h100-01 recorded in the spec brief (image ID sha256:ca32b5c2..., repo digest 15d6abc0...) | FIRST_PARTY |
| CR-14 | Budget arithmetic (wave 4): English episode tokens 96 + 26.5 d, mean fertility 1.78; one Qwen3.5-4B prefix pass over 16 languages x 600 episodes costs 5.96e7 tokens (0.78 GPU-h) at d = 128 and 8.10e7 tokens (1.06 GPU-h) for the d in {8, 32, 128} calibration, at 20 percent of 989 TFLOP/s; Qwen core 9.56 GPU-h (calibration on both passes 2.12, r = 2 on both passes 1.56, six descriptive settings on pass B 4.69, English at every f_L 0.41, r = f_L on pass A 0.78); rwkv7-1.5B-world 1.73; Kimi-Linear 1.08; ledger and BPB 0.5; probe round-trip QA 0.3; core 13.17 GPU-h; optional 2.10; reserve 0.73; ceiling 16 | Owner arithmetic shown in Cheapest Decisive Pilot; assumptions marked; rwkv7 fertility is a planning number | FIRST_PARTY |
| CR-15 | Statistical planning (wave 4): the per-language paired gain G_L has SE about 1.9 EM points at EM 0.7, 600 episodes and within-episode correlation 0.5; an assumed between-language residual SD of 2.0 points gives a total residual of 2.8; SD(log f) 0.375 over the 16 languages (sum of squared deviations 2.24) and VIF 1.33 give SE(beta_f) about 2.2 EM points per unit log fertility per subject and about 1.6 pooled; pooled TOST SE about 0.5 points over 9,000 pairs | Owner closed-form derivations in Evaluation, Statistics, and Leakage Checks; noise parameters marked assumed | FIRST_PARTY |
| CR-16 | Wave-2 internal judge totals 61 and 64; refuter confidences novelty 0.6 (not refuted), identification 0.8 (refuted), feasibility 0.72 (not refuted); blind discrimination confidence 0.9, different mechanism | research/gauntlet/2026-09-01-frontier/wave2-result.json (ranked entry semantic-clock-gate-parity) | FIRST_PARTY |
| CR-17 | Phase-1 owner cost estimate 55 GPU-h at 200k tokens per second per GPU for 60M models, anchored to a first-party model card reporting 15.03B tokens in about 9.3 h on 8 A100-40GB | https://huggingface.co/puigde/gated-deltanet-360M-15B-slimpajama (model card); owner scaling | FIRST_PARTY |
| CR-18 | NVIDIA US20260105282A1 "Gated delta networks" is pending; Google WO2025230701A1 covers compressive memory | Design-brief verification pass 2026-09-01; no patent database reachable from this cell | UNVERIFIABLE_ACCESS |
| CR-19 | Licenses: NTREX and FLORES+ CC-BY-SA-4.0; NLLB-200-distilled-600M CC-BY-NC-4.0; Qwen3.5 apache-2.0; Kimi-Linear MIT with custom code; rwkv7 world card license unconfirmed | Repository and model-card pages linked above; feasibility refuter | VERIFIED |
| CR-20 | Kimi-Linear-48B-A3B-Base at 3b171c17 is registered as kimi-linear-48b-a3b-base, MIT, trust_remote_code, publication_eligible false | models/registry.yaml ; https://huggingface.co/moonshotai/Kimi-Linear-48B-A3B-Base/tree/3b171c17bfc4ee348599b6781a2ca8715c21c8dc | VERIFIED |
| CR-21 | fla-hub/rwkv7-1.5B-world exists at revision 004140baad7a62d49a26d97508ef19cf09672328 (last modified 2025-05-07), card license apache-2.0, base_model BlinkDL/rwkv-7-world, custom_code, card languages en zh ja ko fr ar es pt | https://huggingface.co/api/models/fla-hub/rwkv7-1.5B-world (cardData, sha), read 2026-09-01; license inheritance from the base model unconfirmed | FIRST_PARTY |
| CR-22 | Tokenization length of the same text differs across languages by up to 15 times; byte-level models still show over 4 times for some pairs | https://arxiv.org/abs/2305.15425 (abstract, v2 2023-10-20), opened 2026-09-01 | VERIFIED |
| CR-23 | Across 22 typologically diverse languages, token-based API pricing overcharges speakers of many supported languages while returning poorer results | https://arxiv.org/abs/2305.13707 (abstract, v1 2023-05-23), opened 2026-09-01 | VERIFIED |
| CR-24 | DeciMamba manipulates a hidden filtering mechanism inside the S6 layer at inference time to extend Mamba context length without additional training | https://arxiv.org/abs/2406.14528 (abstract, v3 2025-04-09), opened 2026-09-01 | VERIFIED |
| CR-25 | RWKV-7 generalizes the delta rule with vector-valued gating and in-context learning rates; four models from 0.19B to 2.9B trained on a 3.1T-token multilingual corpus; the 2.9B model claims a 3B multilingual state of the art | https://arxiv.org/abs/2503.14456 (abstract, v2 2025-03-30), opened 2026-09-01; corpus and state-of-the-art statements are the authors' first-party claims | VERIFIED |
| CR-26 | Wave-3 fresh reviewer totals 65 (reviewer 1) and 64 (reviewer 2); lower total 64; both marked Originality, Methodological Rigor, Evidence Sufficiency and Literature Integration PARTLY_MEETS and decision-bearing | research/gauntlet/2026-09-01-frontier/wave3-result.json (entry semantic-clock-gate-parity) | FIRST_PARTY |
| CR-27 | Pre-registered owner thresholds: K7b floor 60 EM points at d = 8; probe redraw if round-trip chrF is below 50 or the code does not survive; a language is translation-limited above a 25 percent redraw rate; at least 12 of 16 languages required per subject; minimum worthwhile slope 3 EM points per unit log fertility; pure-clock reference value about 7 | Owner choices with rationale in Evaluation, Statistics, and Leakage Checks; not taken from any source | FIRST_PARTY |
| CR-28 | A second episode block for an inconclusive primary costs about 3.6 GPU-h (Qwen 4 setting-passes x 5.96e7 tokens = 3.1 GPU-h; rwkv7 0.5 GPU-h) and exceeds the 16 GPU-h ceiling, so it needs a contract amendment | Owner arithmetic, same assumptions as CR-14 | FIRST_PARTY |
| CR-29 | scripts/validate_architecture_experiments.py accepts max_gpu_hours up to 64, but the 2026-09-01 spec brief caps this lane's pilot ceiling at 16 GPU-h, so the wave-3 reviewer's 22 GPU-h alternative is outside the lane's rules | scripts/validate_architecture_experiments.py (execution.max_gpu_hours check) and the spec brief (gpu_hours at most 16), both read 2026-09-01 | VERIFIED |
| CR-30 | Wave-4 fresh reviewer totals 63 (reviewer 1) and 65 (reviewer 2); lower total 63; both name the headroom-entangled EM-point estimand as the surviving defect and the missing executable pilot as the binding cap (79) | research/gauntlet/2026-09-01-frontier/wave4-result.json (entry semantic-clock-gate-parity, score 63) | FIRST_PARTY |
| CR-31 | Rebuilt pilot image cotcodec-research:999f5583-architecture: image ID sha256:9d832a59fe348d149d2e4587ac6af90223e2956ebb646d7b19295298954ca5ad, repo digest 127.0.0.1:5000/cotcodec-research@sha256:bde90daa78c26cd2fb9d05036b0c9f9613c2386b9d7561816b541d2736c79f5d, built by Slurm job 353 from commit 999f5583; torch 2.11.0+cu128, transformers 5.15.0, flash-linear-attention 0.5.2, fla-core 0.5.2, triton 3.6.0 | docs/local-model-lab.md (image table) and research/frontier-systems-program-2026-09-01.md (Stage-0 execution), both read 2026-09-01; host record, not re-inspected by this cell | FIRST_PARTY |
| CR-32 | Artifact receipts for qwen3.5-4b-base (revision 1001bb4d, artifact root c7fbfd6bd1c73b9a..., 9.34 GB) and rwkv7-1.5b-world (revision 004140ba, artifact root 8c662db05dedb86a..., 3.06 GB) exist under /home/kevin/cotcodec-runs/hf-cache/cotcodec-receipts/ on fal-h100-01 (Slurm job 356), alongside eight other pilot checkpoints; the kimi-linear-48b-a3b-base receipt is not among them | research/frontier-systems-program-2026-09-01.md (receipt table), read 2026-09-01; receipts not opened by this cell | FIRST_PARTY |
| CR-33 | fla issue 640 "[Bug] GDN precision error in triton3.5 and h20" was opened 2025-11-12 and is closed; fla 0.5.2 refuses the gated GDN backward on Hopper under Triton at least 3.4.0 and below 3.7.1 (the guard reports incorrect results for gated chunk_bwd_dqkwg and asks for Triton at least 3.7.1 or tilelang); torch 2.11.0 pins triton 3.6.0, so tilelang was added to the architecture extra (commit 0b3ecef) and the image is being rebuilt; the guard binds phase-1 training, not the forward-only phase 0 | https://github.com/fla-org/flash-linear-attention/issues/640 (issue metadata read through the GitHub API on 2026-09-01); guard text from the job-354 log as recorded in research/frontier-systems-program-2026-09-01.md; pyproject.toml | VERIFIED (issue), FIRST_PARTY (guard log) |
| CR-34 | Phase-0 object doctor: `uv run python scripts/run_semantic_clock_gate_parity_doctor.py --output data/results/semantic-clock-gate-parity/phase0-doctor.json` returned PHASE0_OBJECT_DOCTOR_PASS on 17 registered cases in 5.44 s on this Mac (Python 3.13.14, numpy 2.5.2, scipy 1.18.0, macOS arm64), payload SHA-256 907a80d2180ac907933a5e2930244da3206944c845d358dce75d0f8bd4e39145, implementation SHA-256 fb935bc1bb222262b9002ebb57bb8b4cc20a5464d2b9c042f1ab99df16b0ca81. Synthetic-case numbers (not measurements): r = 1 identity gap 2.7e-15; ledger R_F(tam) 2.75 for a per-token clock and 1.000 for self-normalizing gates; span-parity gradient error 1.5e-10; simulator EM(en, r = 1) 87.5 and EM(tam, r = 1) 37.8 with EM-point slope 14.09 [3.43, 24.75] and logit slope -0.07 [-0.61, 0.40]; simulator identity-noise control EM slope 4.40 [0.04, 8.25] refused by a tracking residual of -9.67 [-16.18, -3.15]; parametric clock world 15.97 [9.29, 22.65] with synthetic English 16.64 [12.27, 21.01] and residual 2.08 [-1.21, 5.99] (CLAIM; 4 CLAIM and 1 inconclusive over five extra seeds); headroom world 8.72 [3.11, 14.32] with residual 10.76 [4.97, 16.55] (K11, 5 of 5 seeds); identity world 12.33 [8.14, 16.52] with logit slope 0.63 [0.42, 0.85] and residual 12.00 [8.02, 15.98] (K11, 5 of 5); null world -0.69 [-4.66, 3.21] (K2, 5 of 5); permuted fertility -1.99 (no claim) | data/results/semantic-clock-gate-parity/phase0-doctor.json; tests/test_semantic_clock_gate_parity_doctor.py (12 tests pass) | FIRST_PARTY (synthetic; executability and gate semantics only) |
| CR-35 | Wave-5 re-cost: synthetic-fertility English on Qwen pass B at r in {1, 2}, d = 128, all 15 non-English fertilities = 2 x 600 x 3,488 x 27.408 = 1.15e8 tokens = 1.50 GPU-h; on rwkv7 at f in {1.5, 2.0, 2.7} = 2.6e7 tokens x (1.5/4.66) = 0.11 GPU-h; core 13.17 + 1.61 = 14.78 GPU-h; optional 0.54 (Kimi-Linear r in {0.5, 4}); reserve 0.68; the optional pass-A r in {0.5, 4} cells (1.56 GPU-h) are dropped to fund it; ceiling 16 | Owner arithmetic on the CR-14 unit costs (5.96e7 tokens per 0.78 GPU-h) | FIRST_PARTY |
| CR-36 | Reported-sensitivity logit minimum 0.15 per unit log fertility is the logit-scale image of 3 EM points at an English baseline of EM 0.70 (logit 0.73 minus logit 0.70 = 0.147) | Owner derivation; used only for the reported logit sensitivity, never for a kill | FIRST_PARTY |
| CR-37 | Tracking power (owner closed form): with 600 episodes, EM near 0.7 and correlation 0.3 between G_L and G_syn(f_L), SE(D_L) is about 2.25 EM points and the residual slope SE about 1.5 over the 16-point grid, so P(estimate inside (-3, 3) given no residual) is about 0.95 and a residual of 10 points per log unit (the headroom and identity worlds) has a lower bound above 3 with probability above 0.99; the doctor's clock world reproduced this at 4 CLAIM and 1 inconclusive over five extra seeds | Owner derivation in Evaluation, Statistics, and Leakage Checks; doctor tally in CR-34 | FIRST_PARTY |

## Closest Prior Work

- Gated DeltaNet ([2412.06464](https://arxiv.org/abs/2412.06464)): the
  substrate; gates trained by LM loss with a per-token clock and no per-language
  analysis. Blind discrimination (confidence 0.9): different mechanism, prior does
  not dominate. That discrimination was run against this substrate, not against
  the mechanism ancestors below, and is not transferred to them (wave-4
  caveat; a blind rerun is a listed novelty remediation).
- Tallec and Ollivier ([1804.11188](https://arxiv.org/abs/1804.11188)): the
  theoretical ancestor; time-warp quasi-invariance is now the explicit null that
  phase 0 tests first (R_F near 1).
- Hirschi ([2604.02474](https://arxiv.org/abs/2604.02474)): the mechanism
  ancestor of the constant surgery (time-constant rescale by a known warp
  factor) on LSTMs for dynamical systems, with no language, tokenizer, recall
  probe or auxiliary loss. Cited as required by both wave-2 judges.
- Kimi Linear ([2510.26692](https://arxiv.org/abs/2510.26692)) and GDN-2
  ([2605.22791](https://arxiv.org/abs/2605.22791)): channel-wise decay and
  decoupled erase and write; substrates, not competitors.
- MLNeedle ([2408.10151](https://arxiv.org/abs/2408.10151)) and ONERULER
  ([2503.01996](https://arxiv.org/abs/2503.01996)): cross-lingual needle
  retrieval on softmax transformers; cited as the readout baselines, and the
  reason the phase-0 claim is stated as recurrent-state behaviour with content
  fixed across translations.
- Parity-aware BPE ([2508.04796](https://arxiv.org/abs/2508.04796)), MAGNET
  ([2407.08818](https://arxiv.org/abs/2407.08818)) and Vowel Signs
  ([2608.26449](https://arxiv.org/abs/2608.26449)): parity at the segmentation
  level; here the tokenizer is fixed and parity lives inside the operator.
- Hybrid localization ([2606.15378](https://arxiv.org/abs/2606.15378)): shows
  attention carries long-range retrieval in hybrids, which motivates the
  prefix-blind readout and its floor hold rather than competing with it.
- Leino and Tiedemann ([2603.29026](https://arxiv.org/abs/2603.29026)):
  parallel data barely moves representations; pre-registered as a plausible
  outcome for C3 and a reason phase 1 is gated.
- Petrov et al. ([2305.15425](https://arxiv.org/abs/2305.15425)) and Ahia et
  al. ([2305.13707](https://arxiv.org/abs/2305.13707)): the tokenizer-cost
  lineage (up to 15 times length disparity; 22-language pricing unfairness).
  The cost is located at the tokenizer and the bill, never inside the sequence
  operator's clock. Added in wave 4 at both reviewers' request.
- DeciMamba ([2406.14528](https://arxiv.org/abs/2406.14528)): inference-time
  manipulation of the S6 filtering mechanism on a frozen Mamba for length
  extrapolation; the closest training-free relative of the constant surgery.
  Delta: the warp factor is fertility, the manipulation is a uniform
  per-language decay rescale, the test is a cross-language partial slope.
  Blind discrimination against it and against Hirschi is pending.
- RWKV-7 "Goose" ([2503.14456](https://arxiv.org/abs/2503.14456)): the
  attention-free co-primary subject's recurrence (vector-valued decay w_t,
  generalized delta rule); cited so the surgery on a different gate object is
  defined, not as a competitor.

## Novelty Ledger

| Proposed component | Closest prior | Same | Delta | Confidence |
|---|---|---|---|---|
| Per-language cumulative forgetting and write ledger on released GDN and KDA checkpoints | Gated DeltaNet https://arxiv.org/abs/2412.06464 ; Kimi Linear https://arxiv.org/abs/2510.26692 | no | Gates are analysed per language and per translated sentence; neither paper reports gate statistics by language | 0.60 |
| Fertility-predicted constant clock-surgery dose-response on a frozen model | Hirschi https://arxiv.org/abs/2604.02474 ; Tallec and Ollivier https://arxiv.org/abs/1804.11188 ; DeciMamba https://arxiv.org/abs/2406.14528 (training-free change to a frozen S6 clock) | partly (same operation g' = g / r; same frozen-model inference-time family as DeciMamba) | Object is a language-model gate, the warp factor is tokenizer fertility, the dose is common across languages (r = 2) and the test is a partial slope over 16 languages with resource share partialled out; binding row for the novelty verdict, non-blind owner delta | 0.50 |
| Prefix-blind (within-sentence attention window) and attention-free readouts that force recall through the recurrent state | Hybrid localization https://arxiv.org/abs/2606.15378 ; MLNeedle https://arxiv.org/abs/2408.10151 ; RWKV-7 https://arxiv.org/abs/2503.14456 | no | Every cross-sentence attention hop is removed for the whole episode, not only at the query, with a floor hold and an attention-free co-primary subject carrying the same estimand | 0.60 |
| Translation-paired recall probe with script-neutral codes and n-way matched-content distractors | ONERULER https://arxiv.org/abs/2503.01996 | no | Distractors are the same sentences in every language, answers carry no morphology, episodes are paired by id across languages and settings | 0.60 |
| Fertility-resourcedness decorrelated language grid (Russian, Turkish, Malay added) | Petrov et al. https://arxiv.org/abs/2305.15425 ; Ahia et al. https://arxiv.org/abs/2305.13707 ; Vowel Signs https://arxiv.org/abs/2608.26449 | no | Grid is chosen to break the -0.85 correlation and the estimand is the partial fertility slope | 0.50 |
| Anchored log-ratio span-parity loss on gate statistics (phase 1, gated) | Parity-aware BPE https://arxiv.org/abs/2508.04796 ; MAGNET https://arxiv.org/abs/2407.08818 ; Leino and Tiedemann https://arxiv.org/abs/2603.29026 | no | Parity is enforced inside the operator on existing gate sums, invariant to global rescale, with an English anchor and a length-matched placebo | 0.50 |

Novelty wording: No direct prior art found through 2026-09-01 under the
coverage stated in the header (abstract-level arXiv via the H100 host, HF
Papers, OpenReview, Crossref, 6 WebSearch sweeps, 15 WebFetch abstract checks,
15 pre-pulled arXiv feeds, X bookmarks and GitHub; no full-text, ACL Anthology,
patent or Chinese-language sweep). The novelty refuter did not refute at
confidence 0.6 and blind discrimination against GDN returned a different
mechanism at 0.9; that 0.9 was obtained against the substrate and is not
transferred to the mechanism ancestors (Hirschi, DeciMamba), for which only the
owner's non-blind delta at confidence 0.50 is recorded in the ledger. The
header verdict rests on the brief's two mechanical conditions and is flagged: a
blind rerun against Hirschi 2604.02474 and DeciMamba 2406.14528 is a listed
remediation before the Novelty doctor can PASS. The idea is a recombination
(new observable plus new supervision target), not a new gate or operator.

## Mechanism and Falsifiable Predictions

Gated DeltaNet as implemented in transformers qwen3_5 and fla gated_deltanet:

```text
S_t   = alpha_t S_{t-1} (I - beta_t k_t k_t^T) + beta_t v_t k_t^T
g_t   = log alpha_t = -exp(A_log) * softplus(a_t + dt_bias)   (scalar per head; per channel in KDA)
beta_t = sigmoid(b_t)
F(s)  = -sum_{t in s} g_t        forgetting mass over span s
W(s)  =  sum_{t in s} beta_t     write mass over span s
Per-token clock: F(s_L) / F(s_en) tracks |s_L| / |s_en| = fertility ratio
```

Phase-0 interventions (training-free hooks on frozen checkpoints):

```text
constant decay surgery:   g'_t = g_t / r          r in {0.5, 1, 2, 4} and r = f_L
span-oracle surgery:      g'_t = g_t / r_s        r_s = |s_L| / |s_en| per aligned NTREX sentence
write surgery:            beta'_t = 1 - (1 - beta_t)^(1/r)    ((1 - beta')^r = 1 - beta)
prefix-blind readout (pass B, PRIMARY):
                          for every token of the episode (fact block, each distractor
                          sentence, query) the 8 full_attention layers attend only within
                          the token's own sentence; no attention hop crosses a sentence
                          boundary, so every cross-sentence dependency, including any
                          rehearsal of a fact during the distractor span, must pass
                          through the 24 GDN layers' recurrent state
query-only mask (pass A, secondary):
                          at query time the 8 full_attention layers may not attend to any
                          fact or distractor position; shares the as-written prefix pass
common-dose gain:         G_L = EM_L(r = 2) - EM_L(r = 1), paired within episode, d = 128
primary estimand:         G_L = a + beta_f log f_L + beta_c log CCshare_L + e   (16 languages)
synthetic-fertility English (wave 5, pass B, r in {1, 2}, d = 128, never cut):
                          the same English episodes re-segmented so the token count equals
                          f_L x the canonical English count for every non-English f_L
                          (forced sub-word or character splitting of a pre-registered fraction
                          of words); content, language, tokenizer, resource share and
                          translation quality fixed, token count the only manipulated variable
                          G_syn(f) = EM_syn(f; r = 2) - EM_syn(f; r = 1)
tracking residual:        D_L = G_L - G_syn(f_L) = c + delta_f log f_L + e   (16 languages)
decision (P3):            beta_f clears (lower bound above 0, at least 3) AND the slope of
                          G_syn on log f clears the same minimum AND |delta_f| below 3;
                          K11 if beta_f clears but token count does not reproduce it
reported, never a kill:   the same three slopes on the smoothed logit scale (headroom
                          sensitivity); baseline token-count cost = slope of logit
                          EM_syn(f; r = 1) on log f (expected negative under the clock)
```

Why token count, not the logit scale, is the decision-bearing headroom
control (wave-5 repair of both wave-4 reviewers' fatal defect). The reviewers
asked for the logit-scale partial slope as the decision-bearing conjunct. The
executable NumPy simulator (CR-34) shows why that is unsafe as a kill: with a
Gated DeltaNet scan whose recall is an argmax over stored values, a pure
per-token clock (fertility changes token count and nothing else) yields an
EM-point slope of 14 points per unit log fertility while the logit slope's
interval covers 0, because the logit of recall is roughly linear in the
retained signal exp(-F), whose change under F to F/2 is nearly flat over the
grid's F range; the logit gain of a true clock is therefore form-dependent and
a logit conjunct would refuse it. The synthetic-fertility comparator does not
depend on the readout's functional form: whatever shape the dose-response has,
re-segmented English at f_L must show the same G as language L if token count
is the cause, and it cannot if language identity, translation quality or
saturation is. The logit slopes stay in the report as headroom sensitivity.

Why a within-sentence window rather than masking only the fact keys (wave-4
repair of reviewer 1's fatal defect): with only fact keys masked, a distractor
token can still read fact content that the GDN state has deposited in an
earlier distractor position's residual stream and re-write it into the state,
so attention would relay state-carried content across long ranges with a hop
count that scales with token count, that is with fertility, against the
clock's sign. The within-sentence window closes every cross-sentence hop, so
the pass-B GDN state is the only long-range carrier by construction, at the
price of a second prefix pass and an operating regime the checkpoint was not
trained for, which the floor hold K7b guards.

Phase-1 mechanism (separate contract), for parallel-view batches processed
monolingually and coupled only through span sums:

```text
L = L_LM + lambda   * sum_{(s_a, s_b)} sum_{layers, heads} ( log(F(s_a) + eps) - log(F(s_b) + eps) )^2
         + lambda_W * (same with W)
         + kappa    * ( mean_{t in en} g_t - anchor_en )^2
```

The log-ratio form is exactly invariant to a global rescale of g, removing the
"forget less" shortcut; anchor_en is the detached EMA of the model's own English
per-token mean log-decay at the end of warm-up. Only gate parameters receive the
auxiliary gradient. The placebo is length-matched (pairs within 5 percent in
token count), so it cannot install a per-sentence content clock.

Falsifiable predictions (phase 0 unless marked). Each is a kill criterion if it
fails as stated.

- P1 (ledger, C1): R_F(L) is at least 0.8 f_L and R_W(L) is at least 0.8 f_L
  for every high-fertility language (f_L at least 1.5). Kill K1 if R_F is within
  15 percent of 1 for all of them.
- P2 (calibration, floor, ceiling and baseline gap): prefix-blind EM(en) at
  d = 8 is at least 60 (floor; hold K7b otherwise: the Qwen prefix-blind cells
  become secondary and rwkv7 is the sole primary subject) and at d = 128 is at
  most 95 (ceiling; hold K7 otherwise); EM(en) minus EM(L) at d = 128 is at
  least 10 points for tam, ben, hin and ell while tha, kor, zho-CN and msa are
  within 5 points of English. Kill K4 if the low-fertility controls show the
  Tamil and Bengali gap. Every language must clear the same 60-point floor at
  d = 8 on a subject to enter that subject's slope (K10).
- P3 (primary, C2, wave-5 form): (a) in the two-regressor fit of the
  common-dose gain G_L on log f_L and log Common Crawl share across the 16
  languages (English at log f = 0), the fertility coefficient beta_f has a 95
  percent interval whose lower bound is above 0 and a point estimate of at
  least 3 EM points per unit log fertility; (b) the slope of G_syn on log f
  over English re-segmented to each grid fertility clears the same minimum
  with its lower bound above 0; (c) the tracking residual slope delta_f of
  D_L = G_L - G_syn(f_L) on log f_L has a point estimate inside (-3, 3); all
  three on the prefix-blind readout of Qwen3.5-4B-Base and on the
  attention-free rwkv7-1.5B-world (conjunction; both co-primary; rwkv7's
  synthetic cell runs at f in {1.5, 2.0, 2.7}). Under a pure per-token clock
  and the P2 gap of 10 points, beta_f is about 7 (derivation in Evaluation)
  and delta_f is 0. Kill K2 if the inverse-variance pooled slope across the
  two subjects has an upper bound below 3 and neither subject's own interval
  excludes 0 with a positive estimate; reclassify K2b if the as-written slope
  excludes 0 but the prefix-blind pooled upper bound is below 3; kill K8 if
  the marginal slope excludes 0 but the partial slope's interval includes 0;
  no-claim K9 if the two subjects' intervals exclude 0 with opposite signs;
  kill K11 if (a) holds but (b) fails or the interval of delta_f lies entirely
  outside (-3, 3) (language identity or headroom, not the clock); hold
  (inconclusive tracking band) if (a) and (b) hold and the delta_f estimate is
  outside (-3, 3) with an interval that still reaches the band, resolved only
  by the second episode block (CR-28). The logit-scale versions of all three
  slopes and the baseline token-count cost slope are reported as headroom
  sensitivity and never decide.
  Descriptive only: the quadratic argmax r*(L) over the 5 constant points,
  reported with the boundary rule (non-negative curvature or an argmax outside
  [0.5, 4] is censored at the nearer boundary and never enters a slope).
- P4 (interaction, anti-shortcut): prefix-blind, the EM gain at r = f_L in
  language L exceeds the gain from the same r applied to English (English is
  run at every non-English f_L) by at least 5 points, and G_L minus G_en at the
  common dose r = 2 is at least 5 points, for the high-fertility set. Kill K3
  if both interactions are at most 2 points for every high-fertility language.
- P5 (equivalence, honest): span-oracle surgery beats constant surgery at
  r = f_L by at most 3 EM points in the pooled TOST (expected, given span-ratio
  CV about 0.2). If it beats by more, the parallel view carries information a
  constant cannot and phase-1 arm b stays; otherwise K5 demotes the training
  mechanism to a normalization recipe.
- P6 (phase 1, C3, gated): the span-parity arm reduces the FLORES+ held-out gap
  by at least 50 percent relative to the data-only baseline at per-language BPB
  within 1 percent, is not equivalent to the learned constant under TOST margin
  2, and the length-matched placebo recovers at most 15 percent of it.
- K6 (leakage): the two-forward-pass prefix-invariance audit finds no
  dependence of any readout on hook or mask internals beyond the intended one.

Strongest counter-argument (devil's advocate checkpoint 1). Even a clean partial
fertility slope is consistent with the per-token clock being the right design:
the LM loss optimized forgetting per token, so equalizing forgetting per meaning
trades away within-language optimality, and a surgery that lifts recall may cost
bits per byte. By the owner's own arithmetic the span-oracle and the constant
differ by about 0.1 in log r against a grid step of 0.7, so K5 is the expected
outcome and the surviving deliverable is an inference-time knob plus a ledger.
That is why this contract claims portability of a recipe, not architecture.

What's missing. No same-tokenizer pure-attention sibling of Qwen3.5-4B-Base
exists, so the clock-free bound comes from the prefix-blind readout and the
attention-free co-primary subject rather than from a matched transformer; the attention-free
subject has its own tokenizer, so fertility is re-measured per subject and only
slopes, never levels, are compared across subjects; Common Crawl share is a
proxy for a training mix that Qwen has not disclosed; alignments are
sentence-level; the state-size ladder is deferred; baseline headroom (a
language with lower baseline EM has more room to gain from any helpful
perturbation) is entangled with the cross-language EM-point slope by
construction, which is why the wave-5 claim requires re-segmented English at
matched token count to reproduce the dose-response (P3 b and c, K11) and reads
the logit-scale fits and the r = 0.5 (forget more) cells as sensitivity; the
functional form linking retained state to exact match is unknown, so the
minimum worthwhile slope and the tracking band are stated in EM points, the
decision unit of phase 1, and the simulator's flat logit gain (CR-34) is an
illustration, not a prediction about the checkpoint; the re-segmented English
is out of distribution for the tokenizer, so its BPB is reported and a large
OOD cost would itself be a caveat on (b); the co-primary rwkv7 subject's
coverage of the grid languages is unverified and its World-tokenizer fertility
is unmeasured.

## Cheapest Decisive Pilot

Phase 0 is training-free and runs entirely on public data. Co-primary subjects
for the primary estimand: Qwen3.5-4B-Base (GDN hybrid, registered
`qwen3.5-4b-base`, receipt reported, CR-32) read prefix-blind (pass B), and
fla-hub/rwkv7-1.5B-world at revision 004140ba (registered `rwkv7-1.5b-world`,
receipt reported; attention-free; one pass suffices because it has no
attention layers). Secondary readouts on Qwen: as
written and query-only mask, both from pass A. Kimi-Linear-48B-A3B-Base (KDA
portability, two GPUs): ledger plus d = 32 at r in {1, 2} on both passes;
portability is scored as (i) P1 replicating on KDA and (ii) the sign of beta_f
prefix-blind at d = 32 agreeing with Qwen; levels are never compared across
subjects. Ledger only: Qwen3.5-0.8B-Base and Qwen3.5-2B-Base.

Languages (16). Reference en. High-fertility set H = {pol, fin, hun, ukr, hin,
ell, ben, tam}. Resource-corner additions from the wave-3 repair: rus (f 1.423,
6.9 percent CC share) and tur (1.429, 1.4 percent) at the high-fertility
high-resource corner, msa (1.157, 0.086 percent) at the low-fertility
low-resource corner where hin, ben and tam sit. Low-fertility non-Latin controls
tha (1.174), kor (1.284), zho-CN (0.931). Stress: mya (4.18). Fertility and CC
share are frozen covariates measured before any recall run.

Components:

- 0a CPU doctors (no GPU). Executable since wave 5:
  `harness/semantic_clock_gate_parity.py` implements every phase-0 object as
  typed, input-validated NumPy/SciPy code (gate parametrization g_t and beta_t,
  constant, span-oracle and write surgery, a batched Gated DeltaNet scan, the
  F/W ledger with R_F and R_W, the prefix-blind within-sentence window and the
  query-only mask with an analytic per-pair gradient audit, the anchored
  log-ratio span-parity loss with analytic gradient, the common-dose estimand
  on the EM-point and logit scales with the two-regressor partial slope and an
  episode-clustered paired bootstrap, the synthetic-fertility English tracking
  residual, and every decision rule P1, K1, P3, K2, K3, K4, K7, K7b, K8, K9,
  K10, K10b, K11 as functions). The doctor
  `uv run python scripts/run_semantic_clock_gate_parity_doctor.py --output
  data/results/semantic-clock-gate-parity/phase0-doctor.json` runs 17
  registered cases and writes a hashed receipt whose `evidence_grade` states
  that it proves executability and gate semantics only: r = 1 identity with a
  future-token causality perturbation; token duplication x k scales F x k
  exactly and r = k restores it, and doubling the token count at fixed content
  lowers simulator recall; ledger positive control (per-token clock: P1 holds,
  K1 silent) and warp-invariant negative control (K1 fires); prefix-blind
  window zero gradient (every out-of-window key and value gradient exactly 0.0
  and outputs bitwise unchanged under out-of-window perturbation); the wave-3
  query-only mask shown NOT prefix-blind; a single leaked cross-sentence pair
  detected; span-parity gradient check, global-rescale invariance,
  per-language constant rescale zeroing the term at constant span ratio and
  leaving a residual at span-ratio CV 0.2; mechanistic recall positive control
  on the simulator (CLAIM) and identity-noise negative control (K11);
  parametric clock, headroom, identity and null worlds (CLAIM, K11, K11, K2,
  with a five-seed tally); permuted fertility (no claim); kill, hold and
  exclusion semantics; degenerate-input rejection. Status
  PHASE0_OBJECT_DOCTOR_PASS in 5.44 s on this Mac, payload SHA-256
  907a80d2...9145 (CR-34); tests in
  `tests/test_semantic_clock_gate_parity_doctor.py` (12 pass); bound to the
  contract's `reference_doctor`. Not yet done and still blocking: the same
  objects on the real checkpoints (hook path on the transformers qwen3_5 and
  rwkv7 modeling code, pass-B window on one d = 8 episode, episode builder,
  re-segmentation rule with its BPB, round-trip QA pipeline).
- 0b Ledger: F and W per layer and head for every NTREX sentence in the 16
  languages on the three Qwen3.5 Base sizes and Kimi-Linear; R_F(L) and R_W(L)
  with sentence-clustered intervals against f_L; per-sentence span-ratio CV.
- 0c Probe. Episode = K = 8 facts in language L ("the password of [NP] is
  [CODE]", 12 templates x 300 noun phrases, translated with NLLB-200), then d
  consecutive NTREX sentences in L (same sentence run for every language of the
  same episode id), then a query for one fact (position permuted), greedy 4-token
  decode, exact match on the code. d in {8, 32, 128} (the d = 64 cell is
  dropped in wave 4 to pay for pass B); 600 episodes per (language, d) cell as
  3 seeds x 200. Three readouts per cell: as written and query-only mask from
  pass A, prefix-blind from pass B. Probe-translation manipulation check (wave
  4, both reviewers): every translated fact is back-translated to English with
  the same NLLB checkpoint; a fact is redrawn if its round-trip chrF against
  the English source is below 50 or the 4-digit code does not survive
  verbatim; the per-language redraw rate is reported and a language above 25
  percent is marked translation-limited (K10); the 12 templates per language
  (180 translations) are held for human verification before the sealed run
  (General Translation is the optional resource; not done, a blocker); the
  per-language mean round-trip chrF is the third covariate in a pre-registered
  sensitivity fit.
- 0d Surgery dose-response at d = 128 (d = 32 surgery dropped except on
  Kimi-Linear): r = 2 on both passes (primary cell, with the r = 1 calibration
  cell); r in {0.5, 4}, r = f_L, span-oracle, write at f_L, decay plus write
  at f_L on pass B; r = f_L also on pass A (as-written interaction and K2b);
  English additionally at r equal to every non-English f_L on pass B (P4).
  Primary estimand: partial fertility slope of G_L (P3). Descriptive: quadratic
  fit of EM(log r) over the 5 constant points with the boundary rule; linear
  dEM/dlog r over the interior points {0.5, 1, 2}. Per-language BPB on NTREX
  under every setting.
- 0e Equivalence: span-oracle versus constant at r = f_L, paired within episodes,
  pooled TOST with margin 3 EM points; per-language TOSTs descriptive.
- 0f Attention-free co-primary subject: rwkv7-1.5B-world with calibration at
  d in {8, 32, 128} and r in {0.5, 2, 4, f_L} plus span-oracle at d = 128,
  English at every f_L; the RWKV World tokenizer's fertility is re-measured
  (unmeasured today; 1.78 is a planning number) and the partial-slope test is
  run per subject with its own covariates; languages below the 60-point floor
  at d = 8 on this subject are excluded with the count reported (K10); if
  fewer than 12 remain while Qwen clears K7b, Qwen prefix-blind is the sole
  primary (K10b).
- 0g Synthetic-fertility English (wave 5, never cut): the same English
  episodes (fact block and NTREX distractors, episode ids fixed) re-segmented
  so the token count equals f_L x the canonical English count for every
  non-English grid fertility, by forced sub-word or character splitting of a
  pre-registered fraction of words (the rule, and the achieved token counts on
  both subject tokenizers, are frozen in the evidence bundle before the first
  GPU job); pass B, r in {1, 2}, d = 128, all 15 f_L on Qwen3.5-4B-Base and
  f in {1.5, 2.0, 2.7} on rwkv7-1.5B-world; BPB of the re-segmented text
  reported so the OOD cost is visible. Delivers G_syn(f), the baseline
  token-count cost slope of logit EM(r = 1) on log f, and the tracking
  residual D_L against G_L (P3 b and c, K11, inconclusive band).

Budget arithmetic (owner, CR-14; wave-4 re-cost). English episode tokens
96 + 26.5 d give 308, 944 and 3,488 tokens at d = 8, 32, 128; mean fertility
across the 16 languages is 1.78 (mya at d = 128 is about 14.6k tokens). Unit
costs on Qwen3.5-4B-Base (2 x 4.66e9 FLOPs per token at 20 percent of the 989
TFLOP/s dense BF16 peak, HF eager plus hooks and the chunked fla kernel): one
prefix pass over 16 languages x 600 episodes is 5.96e7 tokens and 0.78 GPU-h at
d = 128, and 8.10e7 tokens and 1.06 GPU-h for the d in {8, 32, 128}
calibration; query continuations add about 1 percent. Qwen: calibration on
both passes 2.12; r = 2 on both passes 1.56; six pass-B settings at d = 128
(r in {0.5, 4}, r = f_L, span-oracle, write, decay plus write) 4.69; English at
the 15 non-English f_L values 0.41; r = f_L on pass A 0.78; synthetic-fertility
English at r in {1, 2} on pass B 1.50 (CR-35: 1,200 episode-passes x 3,488
tokens x the fertility sum 27.408 = 1.15e8 tokens); Qwen core 11.06 GPU-h.
rwkv7-1.5B-world (2 x 1.5e9 FLOPs per token, one pass): calibration 0.34, five
d = 128 settings 1.26, English at every f_L 0.13, synthetic English at three
fertilities 0.11; 1.84 GPU-h. Kimi-Linear (about 3e9 active parameters, 10
percent of peak assumed for the MoE dispatch, two GPUs): ledger plus d = 32 at
r in {1, 2} on both passes, 6.45e7 tokens, 1.08 GPU-h. Ledger and BPB 0.5.
Probe round-trip QA on NLLB-200-distilled-600M (108,000 short translations,
latency-bound) 0.3. Core 14.78 GPU-h; optional cells 0.54 (Kimi-Linear r in
{0.5, 4} on pass B); reserve 0.68; ceiling gpu_hours 16. The wave-5 cell is
funded by dropping the formerly optional pass-A r in {0.5, 4} cells (1.56
GPU-h), as reviewer 2 proposed.

Reviewer 1's alternative of a 22 GPU-h ceiling is not available: the spec
brief caps this lane's pilot at 16 GPU-h (CR-29), so pass B is paid for by
dropping the d = 64 calibration cell and the d = 32 Qwen surgery, not by
cutting rwkv7, which is promoted to co-primary. Throughput is measured in the
first ten minutes; if it is below budget the pre-registered degradation ladder
drops, in order: (1) Kimi-Linear r in {0.5, 4}; (2) write and decay-plus-write
at d = 128; (3) mya from the descriptive settings (r in {0.5, 4},
span-oracle); (4) rwkv7 r in {0.5, 4}; (5) rwkv7 synthetic English. Never cut:
calibration (K7, K7b), r in {1, 2} at d = 128 on both passes and both
co-primary subjects, r = f_L and span-oracle on pass B (P5), English at every
f_L (P4), synthetic-fertility English on Qwen pass B (P3 b and c), Kimi-Linear
ledger and r in {1, 2}. A second episode block for an inconclusive primary or
an inconclusive tracking band costs about 3.6 GPU-h (CR-28) and requires a
contract amendment.

Phase 1 (separately contracted; not this pilot): 60M pure GDN models with fla
0.5.2 or newer, arms a data-only baseline, b span parity, c learned per-language
constant rescale, d uniform decay regularizer at matched mean shift, e
length-matched placebo, f full attention, g SWA plus sinks (a token-window
clock), h Parity-aware BPE, i synthetic-fertility English, j 3:1 hybrid, k GDN-2
decoupled erase and write; owner estimate 55 GPU-h (CR-17). It is funded only
if P1, P3 and P4 pass.

## Controls, Baselines, and Ablations

- r = 1 identity surgery on the same checkpoint (the hook path must reproduce
  the unhooked model to tolerance; the manipulation check for every other cell).
- Prefix-blind readout (pass B: within-sentence attention window for the whole
  episode, so the recurrent state is the only cross-sentence carrier) as the
  primary readout, with the query-only mask (pass A) demoted to secondary;
  attention-free rwkv7-1.5B-world as co-primary subject carrying the same
  estimand (the claim requires both; K7b falls back to rwkv7 alone).
- Probe-translation round-trip QA (chrF threshold, code survival, redraw log,
  human-verified templates, chrF covariate sensitivity fit) so translation
  quality cannot masquerade as a clock effect.
- English under the same r (interaction control against a uniform "forget less"
  effect); BPB under every surgery setting (a rescale that wrecks LM competence
  is not a fix).
- Synthetic-fertility English at matched token count (wave 5): language,
  tokenizer, script, resource share, translation quality and episode ids
  fixed, token count manipulated; the headroom-invariant comparator whose
  dose-response the cross-language slope must reproduce (P3 b and c, K11); the
  logit-scale fits are reported as sensitivity next to it.
- Language grid decorrelating fertility from resourcedness: rus and tur
  (high-fertility, high-resource), msa (low-fertility, low-resource), tha, kor,
  zho-CN (low-fertility, non-Latin), mya (stress); partial slope, not marginal.
- Span-oracle versus per-language constant rescale at matched mean log-decay
  shift (pooled TOST, margin 3).
- Write-only and decay-plus-write surgery (write-count and interference
  alternative); the residual gap after the best decay rescale is pre-registered
  as the write-count or interference share; GDN-2 decoupling deferred to
  confirmation.
- Softmax cross-lingual retrieval baselines MLNeedle and ONERULER cited for the
  needle format and language coverage; SWA plus sinks retained in phase 1 as a
  token-window clock, not a clock-free bound; QED and MARCH with the same
  instrument in confirmation.
- Phase-1 matched controls: data-only baseline, learned per-language constant
  (primary comparator), uniform-decay regularizer at matched realized mean shift,
  length-matched placebo, full-attention arm at matched tokenizer, data and
  parameters, Parity-aware BPE arm at 32k, per-arm LR sweep at a 30M rung,
  iso-parameter, iso-FLOP and iso-wall-time accounting with the auxiliary cost
  reported.

## Evaluation, Statistics, and Leakage Checks

Protocols followed: `.claude/skills/experimental-design/SKILL.md`,
`.claude/skills/statistical-power/SKILL.md`, and the ARS statistical reporting
standard (effect sizes with intervals, paired and clustered errors,
multiplicity, assumption checks).

Endpoints. Primary: the partial fertility slope beta_f of the common-dose gain
G_L = EM_L(r = 2) minus EM_L(r = 1) (P3 a) from the prefix-blind readout at
d = 128 on the sealed NTREX half, together with its reproduction by
re-segmented English at matched token count (P3 b: slope of G_syn on log f;
P3 c: tracking residual slope delta_f of D_L = G_L - G_syn(f_L)), tested as a
conjunction on the two co-primary subjects. Every slope's decision interval is
the union of the analytic OLS t-interval over languages (which carries
between-language scatter) and the 2,000-resample episode-clustered paired
bootstrap interval (which carries within-language sampling noise), as
implemented in `fit_partial_fertility_slope` and `fit_tracking_slope`.
Secondary families: P1 ledger ratios, P2 calibration, floor, ceiling and
baseline gap, P4 interactions, P5 equivalence, each Holm-corrected within
family. Reported sensitivity, never decision-bearing: the logit-scale versions
of the three P3 slopes and the baseline token-count cost slope (headroom
sensitivity), quadratic r*(L) with the boundary rule, linear dEM/dlog r over
{0.5, 1, 2}, the query-only-mask readout, d = 32 cells, leave-one-out over
mya, and the chrF third-covariate fit. Gate parity R_F is a manipulation
check, never an endpoint.

Minimum worthwhile effects. P3: beta_f at least 3 EM points per unit log
fertility with the interval's lower bound above 0. Reference value under a
pure per-token clock: if the English EM curve falls s points per unit log
effective fertility and the P2 gap threshold gives s about 10, then halving
the clock (r = 2) recovers about s log 2, about 7 points, for every language
with f_L at least 2 and less for lower-fertility languages, so G_L is a
saturating increasing function of log f_L whose least-squares slope over this
grid is about 7; the test is therefore a monotone-trend test, and 3 is the
slope below which the highest-fertility language gains under 3 points more
than English, too small to justify phase 1. P4: interaction at least 5 EM
points. P5: equivalence margin 3 EM points. P1: R_F at least 0.8 f_L. K7b
floor 60: the lowest baseline at which a 10-point gap and a 7-point gain are
both resolvable at SE 1.9 without floor compression (owner choice, CR-27).
P3 b: the same 3 EM points per unit log fertility for the synthetic-English
slope. P3 c: |delta_f| below 3 (the residual dose-response that token count
does not reproduce must itself be below the minimum worthwhile slope); an
interval of delta_f entirely outside (-3, 3) is K11 and an estimate outside
the band with an interval reaching it is the inconclusive band. Reported
logit minimum 0.15 per unit log fertility (CR-36) for the sensitivity fits
only. These are the smallest effects that would change the phase-1 decision.

Noise model and power (owner closed form, CR-15; noise parameters are assumed
and will be replaced by the development-half estimates). Per language, G_L is
a paired difference over 600 episodes at EM near 0.7 with within-episode
correlation 0.5 between the two settings: SE about 1.9 EM points (2.2 at
correlation 0.3, 1.4 at 0.7). The between-language residual SD after the two
covariates is unknown and assumed 2.0 points, giving a total residual SD of
about 2.8. Over the 16 languages log f has SD 0.375 (sum of squared deviations
2.24; mya is the high-leverage point, hence the leave-one-out report) and the
assumed residual correlation with log CC share of -0.5 gives VIF 1.33, so
SE(beta_f) is about 2.2 per subject and about 1.6 for the inverse-variance
pooled slope. Under beta_f = 7 each subject's lower bound clears 0 with
probability about 0.89 and the conjunction about 0.79; under beta_f = 0 the
false-claim rate is 0.025 per subject, the pooled K2 kill (upper bound below
3) fires with probability about 0.49, and the remainder is the pre-registered
inconclusive band that triggers the second episode block (CR-28, contract
amendment). Heterogeneity between the two subjects is reported with Cochran's
Q; if Q rejects at 0.1 the pooled kill reverts to per-subject. Tracking (CR-37):
with correlation about 0.3 between G_L and G_syn(f_L) through shared episode
ids, SE(D_L) is about 2.25 EM points and the residual slope SE about 1.5, so
under no residual the estimate lies inside (-3, 3) with probability about
0.95, while a residual of 10 points per log unit (what the headroom and
identity worlds produce) has a lower bound above 3 with probability above
0.99; the executable doctor's parametric clock world reproduced this at 4
CLAIM and 1 inconclusive over five extra seeds (synthetic, CR-34). P4 per
language: 5 points at SE 1.9 gives power about 0.75 at two-sided alpha 0.05;
pooled over the 8 H languages, SE 0.67, power near 1. Pooled TOST for P5 over
15 languages x 600 pairs: SE about 0.5 points, power near 1 at a true zero
difference; the per-cell TOST at SE 1.9 has power about 0.47 and is
descriptive only. Effect sizes are reported as EM-point differences with 95
percent intervals, slope coefficients with intervals, and the R_F ratio with
sentence-clustered intervals; assumption checks are the residual plot and
leverage of the two-regressor fit, the same fit on the logit-EM scale, and
the quadratic-fit curvature sign per language (boundary rule).

Randomization and blocking. Seeds 42, 43, 44 each generate 200 episodes per
cell (template and noun-phrase sampling, code assignment, fact-position
permutation, distractor-run offset). Episode ids are paired across all 16
languages and all settings, so every comparison is within episode. Arm
scheduling on the node is blocked by episode: all settings, both passes and all
three readouts for one (episode id, language) run in the same job segment, languages are
interleaved round-robin rather than run sequentially, and the r grid order is
permuted per episode, so driver, kernel and thermal drift cannot align with a
language or a setting. Data order is fixed by episode id and identical across
subjects. Analysis uses episode-clustered bootstrap (2,000 resamples); languages
are the unit for the slope.

Leakage checks. Codes are drawn fresh per seed and grepped against all NTREX
and FLORES+ text; development and sealed halves are sentence-id disjoint with
disjoint templates and noun phrases; the two-forward-pass prefix-invariance
audit runs on 200 episodes per subject; the r = 1 identity check bounds hook
error; the prefix-blind window and the query-only mask are verified by zero
gradient from every token's logits to keys and values outside the permitted
window; probe facts pass the round-trip chrF and code-survival check before
use and the redraw log is archived. The phase-1 training loss never sees the FLORES+ endpoint.

## Compute and Reproducibility

Pilot image (CR-31; built on fal-h100-01 by Slurm job 353 from commit
999f5583, recorded in docs/local-model-lab.md and
research/frontier-systems-program-2026-09-01.md): tag
`cotcodec-research:999f5583-architecture`, image ID
`sha256:9d832a59fe348d149d2e4587ac6af90223e2956ebb646d7b19295298954ca5ad`, repo
digest
`127.0.0.1:5000/cotcodec-research@sha256:bde90daa78c26cd2fb9d05036b0c9f9613c2386b9d7561816b541d2736c79f5d`.
Contents: torch 2.11.0+cu128, transformers 5.15.0, flash-linear-attention
0.5.2, fla-core 0.5.2, triton 3.6.0. tilelang is being added to the
architecture extra (commit 0b3ecef) because fla 0.5.2 guards the gated GDN
backward on Hopper under Triton below 3.7.1 (fla issue 640, CR-33); the guard binds
the phase-1 training kernels, not the forward-only phase 0. The older
discovery image (`127.0.0.1:5000/cotcodec-research@sha256:15d6abc06fa53ab466087a92107da9c58e469615e2f56a683fefd0a7600277f3`,
no fla) is no longer cited for the pilot. The 999f5583 image predates every
hook in this proposal, so the run image must be rebuilt from the code that
contains them and re-pinned by digest before enablement. Checkpoints:
`qwen3.5-4b-base` and `rwkv7-1.5b-world` are registered at the pinned
revisions with artifact receipts reported under
/home/kevin/cotcodec-runs/hf-cache/cotcodec-receipts/ (job 356, CR-32); the
Kimi-Linear receipt is pending.

Executed so far (CPU, this Mac, 2026-09-01): the phase-0 object doctor,
`uv run python scripts/run_semantic_clock_gate_parity_doctor.py --output
data/results/semantic-clock-gate-parity/phase0-doctor.json`, status
PHASE0_OBJECT_DOCTOR_PASS, payload SHA-256
907a80d2180ac907933a5e2930244da3206944c845d358dce75d0f8bd4e39145 (CR-34), with
`uv run pytest -q tests/test_semantic_clock_gate_parity_doctor.py` (12 pass)
and `uv run ruff check` clean on the three files. Its numbers are synthetic;
it is not a model loop, container smoke or Slurm dry run.

Launch. Dry run first, then the real submit; both wrap
`infra/slurm/host-single-node/docker-research.sbatch` through the discovery
runtime and require a docker-single-node-discovery-v1 job manifest (name,
image_id, git_sha, source_sha256, resources, budget) derived from the contract:

```text
uv run python scripts/submit_docker_research_job.py experiments/architectures/semantic-clock-gate-parity.yaml --dry-run
uv run python scripts/submit_docker_research_job.py experiments/architectures/semantic-clock-gate-parity.yaml
sbatch infra/slurm/host-single-node/docker-research.sbatch   (issued by the script, never by hand)
```

Machine fields:

```text
seeds: [42, 43, 44]
gpu_hours: 16
gpus: 2 (Kimi-Linear needs two H100 80GB; every other subject fits on one)
checkpoint_interval_minutes: 10
```

Checkpoints: episode-level results are appended atomically to
/home/kevin/cotcodec-runs/semantic-clock-gate-parity/ with a resume manifest
every 10 minutes; SIGUSR1 triggers a checkpoint and the fresh-job resume test
must reproduce the interrupted cell's results exactly. Artifacts: the ledger,
episode manifest, all three readouts, probe QA table, dose-response tables, slope fits, BPB tables,
doctor outputs and the continuation equivalence report, all hashed into the
evidence bundle. Cost ceiling: 16 GPU-h at the node's discovery rate; the
degradation ladder in Cheapest Decisive Pilot is the only permitted cut.
Nothing has been executed on the node or on Tinker for this proposal; the CPU
doctor above is the only execution and it is not compute evidence, so the
Compute doctor is FAIL by construction.

## Safety, Data Rights, and Monitorability

Monitorability. No chain-of-thought or action channel is touched. The
per-language forgetting and write ledger and the surgery dose-response are new
interpretability handles for hybrid recurrent state. Training arms (phase 1)
add a clock-injection surface: adversarial text driving g_t toward 0 pins the
state and toward large negative values flushes it. Pre-registered mitigations: a
g_t clamp, reporting the g_t distribution under adversarial suffixes, and the
prefix-invariance audit.

Data rights. NTREX-128 and FLORES+ are CC-BY-SA-4.0; NLLB-200-distilled-600M
outputs are CC-BY-NC-4.0 (research only; probe generation must stay in the
research lane or be replaced by human translation); Qwen3.5 is apache-2.0;
Kimi-Linear is MIT with custom code (non-publication lane); the rwkv7-1.5B-world card
declares apache-2.0 (CR-21, first-party card data) but its inheritance from
BlinkDL/rwkv-7-world is unconfirmed and stays a blocker until recorded. The parallel-data license for
phase-1 training corpora (ParaCrawl, NLLB-mined, Europarl, Samanantar) is
unresolved in this repository and General Translation data has no recorded
license decision; neither is used in phase 0.

IP. NVIDIA US20260105282A1 "Gated delta networks" is pending and Google
WO2025230701A1 covers compressive memory (CR-18); no kernel-level delta-rule
contribution is made here; the contribution is a measurement, an intervention
and a loss.

Red lines. Stop if any surgery setting is reported as a fix while raising BPB
by more than 1 percent in any language; stop if the adversarial-suffix g_t
distribution shows state pinning; never enable execution without the rebuilt
digest-pinned image, the registered Base checkpoint and the passed CPU doctors.

### Integrity gate

Protocol followed: scratchpad `ext/ars/academic-pipeline/references/ai_research_failure_modes.md`
(seven modes). Status per mode for this pre-registration:

- Mode 1 (implementation bug passing self-review): partly by evidence since
  wave 5. The r = 1 identity check, the NumPy simulator, the zero-gradient mask
  audit, the span-parity gradient check and the decision rules exist as tested
  code with a passing doctor (CR-34), including a leaky-mask tamper case and a
  degenerate-input case; the real-checkpoint hooks are not written and every
  reported number must trace to a logged run with exit code 0 in the bundle.
- Mode 2 (hallucinated citation): CLEAR. Every URL was resolved by a wave-2
  refuter or the verification pass and is listed in the claim registry; no DOI
  is asserted.
- Mode 3 (hallucinated experimental result): CLEAR. No experimental result is
  claimed; fertility, CV and correlation figures are owner and refuter
  measurements with scripts to be archived.
- Mode 4 (shortcut reliance): SUSPECTED by default and addressed. The
  "forget less" shortcut has the common-dose design and the English
  interaction control; the attention bypass, including prefix-time rehearsal
  of a fact into the state, has the prefix-blind readout and the attention-free
  co-primary subject; resourcedness has the partial slope over a decorrelated
  grid; translation quality has the round-trip chrF check and covariate;
  script has the Thai, Korean and Chinese controls; headroom and language
  identity have the synthetic-fertility English comparator (P3 b and c, K11),
  the logit-scale sensitivity fits and the ceiling hold; the doctor's headroom
  and identity worlds show the wave-4 EM-only rule would have claimed and the
  wave-5 rule refuses.
- Mode 5 (bug reframed as insight): CLEAR by rule. A flat dose-response or a
  surprising negative R_F is reported as K1 or K2 only after the identity
  check passes and the pooled kill statistic fires; a prefix-blind EM collapse
  is a floor hold (K7b), never a result; a boundary argmax is censored, never
  a kill; a flat logit slope is reported, never a kill, because the simulator
  shows a true clock can produce it.
- Mode 6 (methodology fabrication): CLEAR. This document is a pre-registration
  in the future tense; the run config is the contract YAML plus the job manifest
  and any deviation must be logged in the audit chain.
- Mode 7 (frame-lock): addressed. The claim scope was downgraded from
  architecture-causal to portability-protocol in wave 3; K1, K5 and K2b each
  define a valued alternative deliverable, and phase 1 is not funded until the
  partial-slope gate passes.

## Negative-Result Value

K1 (gates already warp-invariant) is the first measurement answering the
sequence-operators G1 gap and extends Leino and Tiedemann from representations
to gate statistics, confirming Tallec-Ollivier invariance is realized by LM
training. K2 or K8 (no fertility-specific clock effect after partialling out
resourcedness) localizes the cross-lingual recall gap outside the decay clock
and hands the question to write-count, key-interference or data-exposure
explanations. K2b (effect present as written, absent prefix-blind) is a
hybrid-localization result: recall in a 3:1 hybrid is attention-carried for
these distances, now with rehearsal during the distractor span excluded. K7b
(prefix-blind floor failure) is itself a finding: the GDN state of a 3:1
hybrid does not carry 8-fact recall over 8 sentences without attention. K9
(opposite signs on GDN and RWKV-7) is a gate-object difference worth
reporting on its own. K11 (wave 5: the cross-language slope exists but
re-segmented English at matched token count does not reproduce it) is a
headroom-or-language-identity result that retires the per-token-clock
explanation of the cross-lingual recall gap on these subjects; its mirror
(token count reproduces a dose-response the languages do not show) says the
clock is real inside a language but is not what separates languages. K5
(span-oracle equivalent to a constant) yields a training-free per-language
gate normalization recipe plus the ledger, a publishable systems result across
GDN and KDA. In every branch the translation-paired recall instrument with
script-neutral answers and n-way matched-content distractors is delivered,
and since wave 5 the phase-0 objects themselves (ledger, masks, estimand,
decision rules) are reusable tested code.

Strongest counter-argument (devil's advocate checkpoint 3). "The phase-0
deliverable is a per-language knob on a released checkpoint; per-token gating
is what the training objective asked for, and a fertility slope is a
description of tokenizer cost, not a discovery about recurrence." Answer: the
contract already concedes the scope; the knob is only claimed if it moves
recall through the recurrent state at unchanged BPB, and the architecture
claim waits for phase 1.

What's missing. A same-tokenizer attention sibling; a state-size ladder; a
disclosed training mix for the resourcedness covariate; sub-sentence
alignments; any execution evidence.

## Preflight Doctors

| Doctor | Status | Evidence | Remediation |
|---|---|---|---|
| Source | PASS-candidate | Cell notes: wave-2 novelty refuter (32 hostsearch calls, 6 WebSearch, 15 WebFetch, 15 pre-pulled feeds), identification refuter (config.json, tokenizer.json, NTREX, Common Crawl statistics), feasibility refuter (HF API and GitHub revision checks), design-brief verification pass; wave-4 repair owner opened arXiv 2305.15425, 2305.13707, 2406.14528, 2503.14456 and the rwkv7-1.5B-world HF API record; fert script SHA-256 recorded (CR-05); all URLs in Primary-Source Evidence resolve | Snapshot every primary URL with HTTP 200 receipts into the evidence bundle; copy fert.py, fert2.py, fert3.py and the feasibility fert.py into the bundle at the recorded hashes with the Common Crawl page snapshot |
| Citation | PASS-candidate | Claim registry CR-01 to CR-29 covers every number; first-party and owner measurements marked FIRST_PARTY; patents marked UNVERIFIABLE_ACCESS; protocol claim_verification_protocol.md followed | Independent line-by-line audit against the snapshots |
| Novelty | PASS-candidate | Refuter did not refute (0.6); blind discrimination different mechanism (0.9) against the GDN substrate only; Hirschi, Tallec-Ollivier, DeciMamba, Petrov, Ahia and RWKV-7 cited; wording bounded to coverage with the substrate-only caveat stated | Blind discrimination rerun against Hirschi 2604.02474 and DeciMamba 2406.14528; signed provider-distinct novelty review after full-text and ACL Anthology sweep |
| Design | PASS-candidate | experiments/architectures/semantic-clock-gate-parity.yaml passes scripts/validate_architecture_experiments.py with a reference_doctor bound to harness/semantic_clock_gate_parity.py; the phase-0 objects and every decision rule are executable, tested code and the doctor passes its 17 registered synthetic cases (CR-34), including the headroom and identity negative controls the wave-4 reviewers asked for; experimental-design and statistical-power skills applied; randomization and blocking stated; prefix-blind primary readout with floor and ceiling holds; common-dose estimand with the synthetic-fertility comparator, boundary, pooled-kill, disagreement (K9, K11) and fallback (K7b, K10b) rules; probe-translation QA pre-registered | Run the same objects on the real checkpoints (hooks, pass-B window, episode builder, re-segmentation rule, QA pipeline); replace assumed noise with development-half estimates |
| Compute | FAIL | No real model loop, no container smoke, no Slurm dry run; the fla-bearing image exists (CR-31) but predates the hooks; qwen3.5-4b-base and rwkv7-1.5b-world registered with receipts reported (CR-32) but not opened by this cell; Kimi-Linear receipt pending; rwkv7 World-tokenizer fertility unmeasured; the CPU doctor's numbers are synthetic and are not compute evidence | Rebuild and pin the image from the hook code, open the receipts, measure rwkv7 fertility, write the job manifest, pass the dry run and the resume test |
| Safety | PASS-candidate | Monitorability, data rights (parallel-data and rwkv7 licenses unresolved and said so), IP and red lines addressed; integrity gate answered per mode | Runtime evidence for the g_t clamp and adversarial-suffix report |

## Independent Adversarial Reviews

Reviewer A: FAIL | provider=anthropic | model=claude | run_id=wave4-reviewer-1-2026-09-01 | artifact=research/gauntlet/2026-09-01-frontier/wave4-result.json (internal preliminary, NOT provider-distinct, unsigned)

Reviewer B: FAIL | provider=anthropic | model=claude | run_id=wave4-reviewer-2-2026-09-01 | artifact=research/gauntlet/2026-09-01-frontier/wave4-result.json (internal preliminary, NOT provider-distinct, unsigned)

Both scorecards below are the wave-4 fresh internal reviewers (CR-30; the
wave-2 judges' 61 and 64 and the wave-3 reviewers' 65 and 64 are kept in the
Iteration Log). They are not the provider-distinct, Ed25519-signed reviews
the Gauntlet requires, so the accepted score is capped at 89 and the proposal
is NOT pilot-ready. Reviewer A (wave-4 reviewer 1, total 63) surviving
defect: the decision-bearing estimand G_L on the raw EM-point scale is
headroom-entangled by construction (P2 itself predicts high-fertility
languages start 10 or more points lower, so any uniformly helpful perturbation
yields larger EM-point gains for them), with the only remedy demoted to a
descriptive re-fit; secondary: rwkv7's card covers none of the high-fertility
set with no fallback when it fails K10, and the contract still pointed at
placeholder model ids although the registry held both subjects. Reviewer B
(wave-4 reviewer 2, total 65) surviving defect: no phase-0 cell manipulated
token count with language and content fixed on the frozen model, so a clean
P3 could not distinguish the clock from headroom; secondary: the K2 kill fires
only half the time under the null, covariate scripts unarchived. Both bound
the score at the missing executable pilot (cap 79) and the pending blind
discrimination (cap 74). Both filled the ARS criterion-bound form
(quality_rubrics.md) with calibration NOT_CALIBRATED; Originality,
Methodological Rigor, Evidence Sufficiency, Literature Integration and
Significance were PARTLY_MEETS and decision-bearing for both. The wave-5
repair addresses the union of both highest-impact fixes and makes the phase-0
objects executable.

## Scorecard

| Dimension | Reviewer A | Reviewer B | Defect/evidence |
|---|---:|---:|---|
| Question and strategic fit | 6 | 7 | Phase-0 deliverable is a ledger plus an inference-time knob on released checkpoints; the architecture payoff is deferred to the gated phase 1 |
| Primary-source evidence | 7 | 7 | CR-05 to CR-08 rest on unarchived owner scripts (hashes recorded, archive pending); registry and receipts now cited (CR-31, CR-32) |
| Defensible novelty delta | 5 | 5 | Blind discrimination ran against the substrate, not Hirschi or DeciMamba; caveat stated, rerun pending; no ACL Anthology sweep |
| Mechanism and falsifiability | 8 | 7 | Predictions explicit; wave 5 adds the token-count comparator (P3 b, c), K11 and the inconclusive band as executable rules |
| Controls and causal identification | 6 | 6 | EM-point estimand was headroom-entangled; wave 5 adds synthetic-fertility English at matched token count as the headroom-invariant control and shows in the doctor that the wave-4 rule would have claimed on the headroom and identity worlds |
| Evaluation and statistics | 7 | 7 | Logit re-fit was descriptive only; wave 5 pre-registers the tracking residual with its band, power (CR-37) and the logit fits as reported sensitivity, with the simulator's form-dependence caveat |
| Feasibility and information per GPU-hour | 6 | 7 | Synthetic-fertility English funded within the 16 GPU-h cap by dropping the optional pass-A r in {0.5, 4} cells (CR-35) |
| Reproducibility and artifact contract | 5 | 5 | Wave 5: phase-0 objects executable and tested, doctor receipt hashed, reference_doctor bound; still no evidence bundle, no real-checkpoint hooks, image predates the code |
| Safety, data rights, and monitorability | 8 | 8 | Licenses named; rwkv7 card apache-2.0 is first-party with inheritance unconfirmed; parallel-data license unresolved |
| Independent adversarial review quality | 5 | 6 | Internal same-provider reviewers only; unsigned |
| **Total** | **63** | **65** | Lower total is authoritative: 63; capped at 89 by unsigned reviews, 79 until the real-checkpoint pilot is attested, 74 until the blind discrimination rerun |

## Iteration Log

| Wave | Score | Highest-impact defect | Change | Result |
|---:|---:|---|---|---|
| 1 | 0 | Killed before judging: identification refuted (0.8, parity loss collapses onto a per-language constant; placebo not inert) and feasibility refuted (0.7, 27B tokens in 14.4 GPU-h under-costed); see research/gauntlet/2026-09-01-frontier/wave1-ledger.md | Repair owner rewrote the pilot as a 4 GPU-h training-free phase 0 with equivalence as the primary comparison, log-ratio anchored loss, uniform-decay control, mark-aware tokenizer, Thai and Chinese controls | Advanced to wave 2 as a novelty survivor |
| 2 | 61 | C2 not identified: log fertility correlated -0.85 with Common Crawl share across the language set; EM readout on a 3:1 hybrid at d at most 32 is bypassable by the 8 full-attention layers and on ceiling; retrofit deliverable carried as architecture-causal | Judged only; both judges converged on one highest-impact fix | Ranked; lower total 61 |
| 3 | 61 | Same as wave 2 (the judges' agreed highest-impact identification fix) | ONE repair, the union of both judges' fixes: (a) language grid decorrelated with rus, tur, msa and C2 pre-registered as the partial fertility slope controlling for log CC share (interval excluding 0.2); (b) attention-blind query mask on every dose-response cell from a shared prefix pass plus the attention-free rwkv7 subject as the replication requirement for kills; d extended to 128 with an off-ceiling hold (K7) and the baseline EM(en) curve reported first; (c) claim scope relabelled portability-protocol for phase 0 with architecture-causal reserved for the gated phase 1; Hirschi 2604.02474 cited as mechanism ancestor; (d) length-matched placebo replaces the same-language random-pair placebo; (e) TOST pooled across languages with per-cell descriptive; budget re-costed 4 to 14 GPU-h | Re-judged by two fresh reviewers at 65 and 64 (lower 64, up from 61); both found a new fatal defect: the query-time-only mask left prefix rehearsal open, there was no floor hold, and the argmax estimand degenerates at the grid boundary; Compute doctor FAIL by construction; not pilot-ready |
| 4 | 64 | Score history 61 (wave 2) to 64 (wave 3, plus 3). Reviewer 1: the attention-blind mask was query-time only, so the 8 attention layers could rehearse the fact into the GDN state during the distractor span with a hop count scaling with fertility; reviewer 2: no floor hold on the attention-blind readout and an argmax estimand that degenerates to the grid boundary, producing a false K2 kill; both: NLLB probe translations without quality control and unarchived covariate scripts | Union of both highest-impact fixes: (a) primary readout made prefix-blind for the whole episode (within-sentence window on the 8 attention layers in a second prefix pass; chosen over fact-key masking because that leaves an attention relay path), query-only mask demoted to secondary; (b) floor hold K7b (prefix-blind EM(en) at d = 8 at least 60) with fallback to rwkv7 as sole primary; (c) primary estimand replaced by the common-dose paired gain G_L = EM(r = 2) minus EM(r = 1) regressed on log fertility with log CC share partialled out, minimum slope 3 EM points per log unit, quadratic r*(L) demoted to descriptive with a boundary rule, pooled kill statistic and disagreement rule K9; (d) rwkv7-1.5B-world promoted to co-primary (revision 004140ba, card apache-2.0), fertility to be re-measured on its tokenizer, per-language floors K10; (e) probe-translation QA: round-trip chrF threshold 50 with code survival, redraw cap 25 percent, human verification of 180 templates as a blocker, chrF covariate sensitivity fit; (f) fert.py, fert2.py, fert3.py and the feasibility fert.py hashed (SHA-256 in CR-05) with archive and Common Crawl snapshot listed as blockers; (g) Petrov 2305.15425, Ahia 2305.13707, DeciMamba 2406.14528 and RWKV-7 2503.14456 opened and cited; blind discrimination against Hirschi and DeciMamba recorded as pending, not claimed; (h) re-cost: the second prefix pass is paid for by dropping d = 64 and d = 32 Qwen surgery, ceiling 14 to 16 GPU-h (the 22 GPU-h alternative exceeds the lane cap), rwkv7 not cut | Re-judged by two fresh reviewers at 63 and 65 (lower 63, down from 64; dip recorded); both found the surviving defect to be the headroom-entangled EM-point estimand with no phase-0 cell that manipulates token count on the frozen model, plus stale model ids and no executable pilot (cap 79); Compute doctor FAIL by construction; not pilot-ready |
| 5 | 63 | Score history 61 (wave 2), 64 (wave 3), 63 (wave 4). Reviewer 1: the decision-bearing estimand G_L on the raw EM scale is headroom-entangled, the remedy was descriptive, rwkv7 has no K10 fallback and the contract points at placeholder ids; reviewer 2: no phase-0 cell varies token count with language and content fixed on the frozen model, the CPU duplication test ran only on a simulator, K2 fires half the time under the null; both: no executable pilot exists (cap 79) | Single registered repair, the union of both highest-impact fixes: (a) synthetic-fertility English moved from phase-1 arm i into phase 0 as a never-cut pass-B cell (all 15 f_L on Qwen at r in {1, 2}, d = 128; f in {1.5, 2.0, 2.7} on rwkv7), 1.61 GPU-h funded by dropping the optional pass-A r in {0.5, 4} cells (CR-35); (b) P3 now requires the cross-language slope, the synthetic-English slope and a tracking residual inside (-3, 3), with K11 and an inconclusive band pre-registered; (c) the logit-scale slopes are reported sensitivity rather than the proposed co-primary conjunct, because the executable simulator shows a pure per-token clock can have a flat logit gain (CR-34), stated as a functional-form caveat; (d) contract drift repaired: arms point at the registered qwen3.5-4b-base and rwkv7-1.5b-world, blockers rewritten as receipt-reported (CR-32), K10b fallback symmetric to K7b; (e) phase-0 objects implemented as tested CPU code (harness/semantic_clock_gate_parity.py, scripts/run_semantic_clock_gate_parity_doctor.py, tests/test_semantic_clock_gate_parity_doctor.py) bound to the contract's reference_doctor, 17 registered synthetic cases passing including the headroom and identity worlds on which the wave-4 rule would have claimed; (f) rebuilt fla image and receipts cited (CR-31 to CR-33) | Validator PASS (9 of 9 contracts); doctor status PHASE0_OBJECT_DOCTOR_PASS (synthetic numbers only, CR-34); research_direction_doctor.py still FAIL by construction (no evidence bundle, Compute FAIL, unsigned same-provider reviews); not yet re-judged; not pilot-ready |

The evidence bundle follows `research/proposals/evidence/_schema.json`. All
source snapshots, query logs, reviewer outputs, doctor outputs, container and
Slurm attestations, and the hash-chained audit JSONL must live below the bundle
directory and match their recorded SHA-256 hashes. The bundle
evidence/semantic-clock-gate-parity/bundle.json does not exist yet. A prose
PASS without those artifacts is a deterministic FAIL. Each review receipt must
be Ed25519-signed by a provider-specific key loaded from the external read-only
path configured as `COTCODEC_TRUSTED_ATTESTORS_PATH` in trusted CI; proposal
authors cannot add a trust root inside the repository or their evidence bundle.
