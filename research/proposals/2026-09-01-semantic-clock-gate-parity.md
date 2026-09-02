# Research Direction: Semantic-Clock Gate Parity

**Status:** draft
**Owner:** Kevin Liu
**Source cutoff:** 2026-09-01
**Coverage limits:** WebSearch budget exhausted; arXiv API, Semantic Scholar and Jina blocked from the Mac (arXiv reached only through the H100 host at abstract level; 20 of 22 refuter arXiv queries returned 429); no OpenReview, ACL Anthology, patent or Chinese-language sweep beyond the 2026-09-01 verification pass; nothing executed on the H100 node or Tinker; no parallel corpus in the repository; Common Crawl language shares read from the public statistics page only; fertility and span-ratio figures are owner and refuter measurements, not published numbers.
**Budgets:** queries=60; wall_minutes=480; tokens=600000; dollars=20; waves=4; gpu_hours=14
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
  1/r on a frozen checkpoint moves translation-paired recall that is carried by
  the recurrent state, with an optimum r*(L) that rises with fertility after
  partialling out training-resource share; low-fertility non-Latin languages and
  low-fertility low-resource Malay behave like English.
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
wave-3 repair recorded in the Iteration Log.

## Strategic Fit and Why Now

Kevin's assets fit phase 0 exactly: a Docker and Slurm harness with hooks,
seeded episodes, exact-match generation and checkpoint-resume, and enough GPUs
to run the full 16-language by 4-distance by 8-setting grid in one node-day.
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
digits singly, so a 4-digit code is exactly 4 tokens. The transformers
[qwen3_5 modeling file](https://github.com/huggingface/transformers/blob/main/src/transformers/models/qwen3_5/modeling_qwen3_5.py)
computes beta_t = sigmoid(b_t) and g_t = -exp(A_log) * softplus(a_t + dt_bias)
in Python before the chunked delta-rule kernel, so g and beta surgery is a
function wrapper. The reference kernel is
[fla gated_deltanet.py](https://github.com/fla-org/flash-linear-attention/blob/main/fla/layers/gated_deltanet.py);
[fla v0.5.2](https://github.com/fla-org/flash-linear-attention/releases/tag/v0.5.2)
(2026-07-27) ships `gdn2.py`, `kda` and `rwkv7` ops. The second base is
[moonshotai/Kimi-Linear-48B-A3B-Base](https://huggingface.co/moonshotai/Kimi-Linear-48B-A3B-Base/tree/3b171c17bfc4ee348599b6781a2ca8715c21c8dc)
(MIT, custom code). The attention-free multilingual subject is
[fla-hub/rwkv7-2.9B-world](https://huggingface.co/fla-hub/rwkv7-2.9B-world)
and its 1.5B sibling (registration pending).

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
reason the attention-blind readout exists. Cross-lingual needle baselines on
softmax transformers: MLNeedle ([2408.10151](https://arxiv.org/abs/2408.10151))
and ONERULER ([2503.01996](https://arxiv.org/abs/2503.01996)). Tokenizer-side
parity and fertility: Parity-aware BPE ([2508.04796](https://arxiv.org/abs/2508.04796)),
MAGNET ([2407.08818](https://arxiv.org/abs/2407.08818)), Vowel Signs Are Not
Letters ([2608.26449](https://arxiv.org/abs/2608.26449)). Leino and Tiedemann
([2603.29026](https://arxiv.org/abs/2603.29026)) find parallel data barely moves
representations; gate statistics are a different observable. Leakage audit:
two-forward-pass prefix invariance ([2608.22876](https://arxiv.org/abs/2608.22876)).

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
| CR-05 | Fertility on the Qwen3.5-4B-Base tokenizer over NTREX-128: pol 1.605, fin 1.627, hun 1.706, ukr 1.792, hin 2.073, ell 2.119, ben 2.164, tam 2.744, kor 1.284, tha 1.174, zho-CN 0.931, mya 4.18, rus 1.423, tur 1.429, msa 1.157; English 26.5 tokens per sentence | Owner measurement (tokenizers library, tokenizer.json above, NTREX commit 468c6b69), independently reproduced by the identification and feasibility refuters (fert.py, fert2.py); scripts to be archived in the bundle | FIRST_PARTY |
| CR-06 | Within-language per-sentence span-ratio CV 0.17-0.24 (owner) and 0.19-0.25 (refuter re-measurement); within-language sentence-length CV 0.50-0.53 | Same measurement as CR-05 (fert3.py for the length CV) | FIRST_PARTY |
| CR-07 | Log fertility and log Common Crawl page share (CC-MAIN-2026-34) correlate at Pearson -0.85 and Spearman -0.71 across the 8 high-fertility languages and -0.78 across 11 phase-0 languages | https://commoncrawl.github.io/cc-crawl-statistics/plots/languages joined to CR-05 by the identification refuter (fert2.py) | FIRST_PARTY |
| CR-08 | Common Crawl page shares: rus 6.9 percent, tur 1.4 percent, hun 0.53 percent, fin 0.38 percent, tha 0.37 percent, msa 0.086 percent; hin, ben and tam sit in the 0.2 percent or lower tier | https://commoncrawl.github.io/cc-crawl-statistics/plots/languages (CC-MAIN-2026-34 row); read by the identification refuter, snapshot pending in the bundle | VERIFIED |
| CR-09 | NTREX-128 at commit 468c6b69 has 1,997 sentences per language and is CC-BY-SA-4.0 | https://github.com/MicrosoftTranslator/NTREX/tree/468c6b69c7f6a75d31d4743d9daba2af566cc18d (NTREX-128 directory, LICENSE) | VERIFIED |
| CR-10 | 1.3B Gated DeltaNet scores 100 / 99.8 / 92.2 on S-NIAH-2 at 1K / 2K / 4K | https://arxiv.org/abs/2412.06464 (Table 2), read by the feasibility refuter | VERIFIED |
| CR-11 | fla v0.5.2 was released 2026-07-27 with gdn2.py, kda and rwkv7 ops | https://github.com/fla-org/flash-linear-attention/releases/tag/v0.5.2 | VERIFIED |
| CR-12 | Hirschi (2026-04) rescales LSTM time constants by a known time-warp factor for transfer across timescales | https://arxiv.org/abs/2604.02474 (abstract), read by the novelty refuter | VERIFIED |
| CR-13 | Discovery image contents: CUDA 12.8.1, torch 2.11.0+cu128, transformers 5.15.0, accelerate, triton, no fla, vllm, peft or flash-attn; created 2026-08-16 | Host inspection on fal-h100-01 recorded in the spec brief (image ID sha256:ca32b5c2..., repo digest 15d6abc0...) | FIRST_PARTY |
| CR-14 | Budget arithmetic: 16 languages, 600 episodes per cell, English episode tokens 96 + 26.5 d, mean fertility 1.78, 6.42e8 prefix tokens, 5.98e18 FLOPs, 8.4 GPU-h at 20 percent of 989 TFLOP/s; rwkv7 1.45 GPU-h; KDA 1.0 GPU-h; ledger and BPB 0.5 GPU-h; core 11.35 GPU-h; ceiling 14 | Owner arithmetic shown in Cheapest Decisive Pilot; assumptions marked | FIRST_PARTY |
| CR-15 | Statistical planning: per-cell paired EM SE about 1.9 points at EM 0.7 and within-episode correlation 0.5; pooled TOST SE about 0.5 points over 9,000 pairs; partial-slope SE about 0.20 under residual SD 0.25, SD(log f) 0.38 and VIF 1.33 | Owner closed-form derivations in Evaluation, Statistics, and Leakage Checks; noise parameters marked assumed | FIRST_PARTY |
| CR-16 | Wave-2 internal judge totals 61 and 64; refuter confidences novelty 0.6 (not refuted), identification 0.8 (refuted), feasibility 0.72 (not refuted); blind discrimination confidence 0.9, different mechanism | research/gauntlet/2026-09-01-frontier/wave2-result.json (ranked entry semantic-clock-gate-parity) | FIRST_PARTY |
| CR-17 | Phase-1 owner cost estimate 55 GPU-h at 200k tokens per second per GPU for 60M models, anchored to a first-party model card reporting 15.03B tokens in about 9.3 h on 8 A100-40GB | https://huggingface.co/puigde/gated-deltanet-360M-15B-slimpajama (model card); owner scaling | FIRST_PARTY |
| CR-18 | NVIDIA US20260105282A1 "Gated delta networks" is pending; Google WO2025230701A1 covers compressive memory | Design-brief verification pass 2026-09-01; no patent database reachable from this cell | UNVERIFIABLE_ACCESS |
| CR-19 | Licenses: NTREX and FLORES+ CC-BY-SA-4.0; NLLB-200-distilled-600M CC-BY-NC-4.0; Qwen3.5 apache-2.0; Kimi-Linear MIT with custom code; rwkv7 world card license unconfirmed | Repository and model-card pages linked above; feasibility refuter | VERIFIED |
| CR-20 | Kimi-Linear-48B-A3B-Base at 3b171c17 is registered as kimi-linear-48b-a3b-base, MIT, trust_remote_code, publication_eligible false | models/registry.yaml ; https://huggingface.co/moonshotai/Kimi-Linear-48B-A3B-Base/tree/3b171c17bfc4ee348599b6781a2ca8715c21c8dc | VERIFIED |

## Closest Prior Work

- Gated DeltaNet ([2412.06464](https://arxiv.org/abs/2412.06464)): the
  substrate; gates trained by LM loss with a per-token clock and no per-language
  analysis. Blind discrimination (confidence 0.9): different mechanism, prior does
  not dominate.
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
  attention-blind readout rather than competing with it.
- Leino and Tiedemann ([2603.29026](https://arxiv.org/abs/2603.29026)):
  parallel data barely moves representations; pre-registered as a plausible
  outcome for C3 and a reason phase 1 is gated.

## Novelty Ledger

| Proposed component | Closest prior | Same | Delta | Confidence |
|---|---|---|---|---|
| Per-language cumulative forgetting and write ledger on released GDN and KDA checkpoints | Gated DeltaNet https://arxiv.org/abs/2412.06464 ; Kimi Linear https://arxiv.org/abs/2510.26692 | no | Gates are analysed per language and per translated sentence; neither paper reports gate statistics by language | 0.60 |
| Fertility-predicted constant clock-surgery dose-response on a frozen model | Hirschi https://arxiv.org/abs/2604.02474 ; Tallec and Ollivier https://arxiv.org/abs/1804.11188 | partly (same operation g' = g / r) | Object is a language-model gate, the warp factor is tokenizer fertility, and the test is a partial slope over 15 languages with resource share partialled out | 0.55 |
| Attention-blind and attention-free readout that attributes recall to the recurrent state | Hybrid localization https://arxiv.org/abs/2606.15378 ; MLNeedle https://arxiv.org/abs/2408.10151 | no | Query-time key mask on the full-attention layers plus an attention-free multilingual subject as the replication requirement for every kill | 0.60 |
| Translation-paired recall probe with script-neutral codes and n-way matched-content distractors | ONERULER https://arxiv.org/abs/2503.01996 | no | Distractors are the same sentences in every language, answers carry no morphology, episodes are paired by id across languages and settings | 0.60 |
| Fertility-resourcedness decorrelated language grid (Russian, Turkish, Malay added) | Vowel Signs https://arxiv.org/abs/2608.26449 | no | Grid is chosen to break the -0.85 correlation and the estimand is the partial fertility slope | 0.50 |
| Anchored log-ratio span-parity loss on gate statistics (phase 1, gated) | Parity-aware BPE https://arxiv.org/abs/2508.04796 ; MAGNET https://arxiv.org/abs/2407.08818 ; Leino and Tiedemann https://arxiv.org/abs/2603.29026 | no | Parity is enforced inside the operator on existing gate sums, invariant to global rescale, with an English anchor and a length-matched placebo | 0.50 |

Novelty wording: No direct prior art found through 2026-09-01 under the
coverage stated in the header (abstract-level arXiv via the H100 host, HF
Papers, OpenReview, Crossref, 6 WebSearch sweeps, 15 WebFetch abstract checks,
15 pre-pulled arXiv feeds, X bookmarks and GitHub; no full-text, ACL Anthology,
patent or Chinese-language sweep). The novelty refuter did not refute at
confidence 0.6 and blind discrimination against GDN returned a different
mechanism at 0.9; the idea is a recombination (new observable plus new
supervision target), not a new gate or operator.

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
attention-blind readout:  at query time the 8 full_attention layers may not attend to any
                          fact or distractor position; GDN state and KV cache are shared
                          with the as-written readout from one prefix pass
```

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
- P2 (calibration and baseline gap): attention-blind EM(en) at d = 128 is at
  most 95 (off ceiling; hold K7 otherwise), and EM(en) minus EM(L) at d = 128
  is at least 10 points for tam, ben, hin and ell while tha, kor, zho-CN and msa
  are within 5 points of English. Kill K4 if the low-fertility controls show the
  Tamil and Bengali gap.
- P3 (primary, C2): in the two-regressor fit of log r*(L) minus log r*(en) on
  log f_L and log Common Crawl share across the 15 non-English languages, the
  fertility coefficient's 95 percent interval excludes 0.2 on both readouts and
  the attention-blind sign replicates on the attention-free subject. Kill K2 if
  the interval's upper bound is below 0.5 on both readouts with replication;
  reclassify K2b if the dose-response exists as written but vanishes
  attention-blind; kill K8 if the marginal slope excludes 0.2 but the partial
  slope's interval includes 0.
- P4 (interaction, anti-shortcut): the EM gain at r = f_L in language L exceeds
  the gain from the same r applied to English by at least 5 points. Kill K3 if
  the interaction is at most 2 points for every high-fertility language.
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
exists, so the clock-free bound comes from the attention-blind readout and the
attention-free subject rather than from a matched transformer; the attention-free
subject has its own tokenizer, so fertility is re-measured per subject and only
slopes, never levels, are compared across subjects; Common Crawl share is a
proxy for a training mix that Qwen has not disclosed; alignments are
sentence-level; the state-size ladder is deferred.

## Cheapest Decisive Pilot

Phase 0 is training-free and runs entirely on public data. Subjects: Qwen3.5-4B-Base
(GDN hybrid, primary), the same checkpoint under the attention-blind query mask,
fla-hub/rwkv7-1.5B-world (attention-free multilingual replication subject),
Kimi-Linear-48B-A3B-Base (KDA portability, ledger plus the r grid at d = 32,
two GPUs). Ledger only: Qwen3.5-0.8B-Base and Qwen3.5-2B-Base.

Languages (16). Reference en. High-fertility set H = {pol, fin, hun, ukr, hin,
ell, ben, tam}. Resource-corner additions from the wave-3 repair: rus (f 1.423,
6.9 percent CC share) and tur (1.429, 1.4 percent) at the high-fertility
high-resource corner, msa (1.157, 0.086 percent) at the low-fertility
low-resource corner where hin, ben and tam sit. Low-fertility non-Latin controls
tha (1.174), kor (1.284), zho-CN (0.931). Stress: mya (4.18). Fertility and CC
share are frozen covariates measured before any recall run.

Components:

- 0a CPU doctors (no GPU): NumPy GDN simulator (r = 1 reproduces baseline;
  token duplication x k scales F x k and lowers recall at fixed semantic
  distance); attention-blind mask doctor (no attention path from query tokens
  to fact or distractor positions, verified by gradient of the query logits
  with respect to masked keys being exactly zero); log-ratio loss gradient check
  and rescale-invariance tests; causality doctor.
- 0b Ledger: F and W per layer and head for every NTREX sentence in the 16
  languages on the three Qwen3.5 Base sizes and Kimi-Linear; R_F(L) and R_W(L)
  with sentence-clustered intervals against f_L; per-sentence span-ratio CV.
- 0c Probe. Episode = K = 8 facts in language L ("the password of [NP] is
  [CODE]", 12 templates x 300 noun phrases, translated with NLLB-200), then d
  consecutive NTREX sentences in L (same sentence run for every language of the
  same episode id), then a query for one fact (position permuted), greedy 4-token
  decode, exact match on the code. d in {8, 32, 64, 128}; 600 episodes per
  (language, d) cell as 3 seeds x 200. Two readouts per prefix pass: as written
  and attention-blind.
- 0d Surgery dose-response at d in {32, 128}: constant r in {0.5, 2, 4} and
  r = f_L, span-oracle, write at f_L, decay plus write at f_L (7 settings; r = 1
  is the calibration run). Quadratic fit of EM(log r) over the 5 constant points
  gives r*(L) with a bootstrap interval; the primary estimand is the partial
  fertility slope (P3). Per-language BPB on NTREX under every setting.
- 0e Equivalence: span-oracle versus constant at r = f_L, paired within episodes,
  pooled TOST with margin 3 EM points; per-language TOSTs descriptive.
- 0f Attention-free replication: rwkv7-1.5B-world with calibration at all four
  d and r in {0.5, 2, f_L} at d in {32, 128}; the RWKV World tokenizer's
  fertility is re-measured and the partial-slope test is run per subject.

Budget arithmetic (owner, CR-14). English episode tokens 96 + 26.5 d give 308,
944, 1,792 and 3,488 tokens at d = 8, 32, 64, 128; mean fertility across the 16
languages is 1.78; the longest episode is mya at d = 128 at about 14.6k tokens.
GDN prefix forwards: calibration 16 x 4 x 600 = 38,400 (1.12e8 tokens); surgery
7 x 16 x 600 = 67,200 at d = 32 (1.13e8 tokens) and 67,200 at d = 128 (4.17e8
tokens); total 6.42e8 tokens. Query continuations (two per prefix, about 20
tokens each) add about 1 percent. FLOPs 2 x 4.66e9 x 6.42e8 = 5.98e18; at 20
percent of the 989 TFLOP/s dense BF16 peak (HF eager plus hooks, chunked fla
kernel) that is 8.4 GPU-h. rwkv7: 96,000 forwards, about 3.4e8 tokens, 1.03e18
FLOPs, 1.45 GPU-h. Kimi-Linear ledger plus r grid at d = 32 on two GPUs: 1.0
GPU-h. Ledger and BPB under surgery: 0.5 GPU-h. Core 11.35 GPU-h; ceiling with
reserve gpu_hours 14. Throughput is measured in the first ten minutes; if it is
below budget the pre-registered degradation ladder drops, in order, the d = 64
calibration cell, the write and decay-plus-write settings at d = 128, the r = 4
point at d = 128, and the rwkv7 d = 32 cells. Nothing in the primary endpoint is
cut before those.

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
- Attention-blind query mask on the same prefix state (attributes recall to the
  recurrent state); attention-free multilingual subject rwkv7-1.5B-world (kills
  must replicate in sign there).
- English under the same r (interaction control against a uniform "forget less"
  effect); BPB under every surgery setting (a rescale that wrecks LM competence
  is not a fix).
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

Endpoints. Primary: the partial fertility slope (P3) from attention-blind EM at
d = 128 on the sealed NTREX half. Secondary families: P1 ledger ratios, P2
calibration and baseline gap, P4 interaction, P5 equivalence, each Holm-corrected
within family. Gate parity R_F is a manipulation check, never an endpoint.

Minimum worthwhile effects. P3: fertility coefficient at least 0.5 (half of the
value 1.0 implied by a pure per-token clock), interval excluding 0.2. P4:
interaction at least 5 EM points. P5: equivalence margin 3 EM points. P1: R_F at
least 0.8 f_L. These are the smallest effects that would change the phase-1
decision.

Noise model and power (owner closed form, CR-15; noise parameters are assumed
and will be replaced by the development-half estimates). Per cell of 600 paired
episodes with EM near 0.7 and within-episode correlation 0.5 between two
settings, the paired EM difference has SE about 1.9 points (2.2 at correlation
0.3, 1.4 at 0.7). P4 per language: 5 points at SE 1.9 gives power about 0.75 at
two-sided alpha 0.05; pooled over the 8 H languages, SE 0.67, power near 1.
Pooled TOST for P5 over 15 languages x 600 pairs: SE about 0.5 points, power
near 1 to declare equivalence at a true zero difference; the per-cell TOST at
SE 1.9 has power about 0.47 and is therefore descriptive only. Partial slope:
15 languages, SD(log f) 0.38 from the fertility table, assumed residual
correlation with log CC share of -0.5 after the corner languages are added
(VIF 1.33), assumed residual SD 0.25 in log r*; SE(beta_f) about 0.20. Under
beta_f = 1 the interval excludes 0.2 with probability about 0.98; under
beta_f = 0 the K2 upper-bound-below-0.5 kill fires with probability about 0.71;
between 0.3 and 0.6 the result is pre-registered as inconclusive and a second
pre-registered episode block is run before any phase-1 decision. Effect sizes
are reported as EM-point differences with 95 percent intervals, slope
coefficients with intervals, and the R_F ratio with sentence-clustered
intervals; assumption checks are the residual plot of the two-regressor fit
and the quadratic fit residuals per language.

Randomization and blocking. Seeds 42, 43, 44 each generate 200 episodes per
cell (template and noun-phrase sampling, code assignment, fact-position
permutation, distractor-run offset). Episode ids are paired across all 16
languages and all settings, so every comparison is within episode. Arm
scheduling on the node is blocked by episode: all settings and both readouts for
one (episode id, language) run in the same job segment, languages are
interleaved round-robin rather than run sequentially, and the r grid order is
permuted per episode, so driver, kernel and thermal drift cannot align with a
language or a setting. Data order is fixed by episode id and identical across
subjects. Analysis uses episode-clustered bootstrap (2,000 resamples); languages
are the unit for the slope.

Leakage checks. Codes are drawn fresh per seed and grepped against all NTREX
and FLORES+ text; development and sealed halves are sentence-id disjoint with
disjoint templates and noun phrases; the two-forward-pass prefix-invariance
audit runs on 200 episodes per subject; the r = 1 identity check bounds hook
error; the attention-blind mask is verified by zero gradient from query logits
to masked keys. The phase-1 training loss never sees the FLORES+ endpoint.

## Compute and Reproducibility

Discovery image (verified on fal-h100-01, 2026-09-01; the only image that
exists): repo digest
`127.0.0.1:5000/cotcodec-research@sha256:15d6abc06fa53ab466087a92107da9c58e469615e2f56a683fefd0a7600277f3`
with image ID `sha256:ca32b5c26b92fbe2a7054ae96543cd62928b0493896ec355b869b612022aa9a2`,
labels org.opencontainers.image.revision=581ded8df71564b0212d8af5dcd401257aa6a28f,
source-tree-sha256=2d960d1a5cf6fd64cdd0baba0a2c752ad6216b8443d741cb7deef9e07d031322,
runtime-profile=architecture-source-overlay, created 2026-08-16. Contents:
CUDA 12.8.1, torch 2.11.0+cu128, transformers 5.15.0, accelerate, triton; no
fla, vllm, peft or flash-attn. This image can run the CPU doctors and the
pure-torch GDN fallback but not the budgeted pilot: the pilot needs a rebuilt
image from the new code with fla 0.5.2 or newer (chunked GDN, KDA and rwkv7
kernels) and any other new dependency, re-pinned by digest before enablement.

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
gpu_hours: 14
gpus: 2 (Kimi-Linear needs two H100 80GB; every other subject fits on one)
checkpoint_interval_minutes: 10
```

Checkpoints: episode-level results are appended atomically to
/home/kevin/cotcodec-runs/semantic-clock-gate-parity/ with a resume manifest
every 10 minutes; SIGUSR1 triggers a checkpoint and the fresh-job resume test
must reproduce the interrupted cell's results exactly. Artifacts: the ledger,
episode manifest, both readouts, dose-response tables, slope fits, BPB tables,
doctor outputs and the continuation equivalence report, all hashed into the
evidence bundle. Cost ceiling: 14 GPU-h at the node's discovery rate; the
degradation ladder in Cheapest Decisive Pilot is the only permitted cut.
Nothing has been executed on the node or on Tinker for this proposal; the
Compute doctor is therefore FAIL by construction.

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
Kimi-Linear is MIT with custom code (non-publication lane); the rwkv7 world
card license is unconfirmed and is a blocker. The parallel-data license for
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

- Mode 1 (implementation bug passing self-review): CLEAR by design, not by
  evidence. The r = 1 identity check, the NumPy simulator, the zero-gradient mask
  doctor and the prefix-invariance audit are pre-registered; every reported
  number must trace to a logged run with exit code 0 in the bundle.
- Mode 2 (hallucinated citation): CLEAR. Every URL was resolved by a wave-2
  refuter or the verification pass and is listed in the claim registry; no DOI
  is asserted.
- Mode 3 (hallucinated experimental result): CLEAR. No experimental result is
  claimed; fertility, CV and correlation figures are owner and refuter
  measurements with scripts to be archived.
- Mode 4 (shortcut reliance): SUSPECTED by default and addressed. The
  "forget less" shortcut has the English interaction control; the attention
  bypass has the attention-blind readout and the attention-free subject;
  resourcedness has the partial slope over a decorrelated grid; script has the
  Thai, Korean and Chinese controls.
- Mode 5 (bug reframed as insight): CLEAR by rule. A flat dose-response or a
  surprising negative R_F is reported as K1 or K2 only after the identity
  check passes and the sign replicates on the attention-free subject.
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
explanations. K2b (effect present as written, absent attention-blind) is a
hybrid-localization result: recall in a 3:1 hybrid is attention-carried for
these distances. K5 (span-oracle equivalent to a constant) yields a
training-free per-language gate normalization recipe plus the ledger, a
publishable systems result across GDN and KDA. In every branch the
translation-paired recall instrument with script-neutral answers and n-way
matched-content distractors is delivered.

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
| Source | PASS-candidate | Cell notes: wave-2 novelty refuter (32 hostsearch calls, 6 WebSearch, 15 WebFetch, 15 pre-pulled feeds), identification refuter (config.json, tokenizer.json, NTREX, Common Crawl statistics), feasibility refuter (HF API and GitHub revision checks), design-brief verification pass; all URLs in Primary-Source Evidence resolve | Snapshot every primary URL with HTTP 200 receipts into the evidence bundle |
| Citation | PASS-candidate | Claim registry CR-01 to CR-20 covers every number; first-party and owner measurements marked FIRST_PARTY; patents marked UNVERIFIABLE_ACCESS; protocol claim_verification_protocol.md followed | Independent line-by-line audit against the snapshots |
| Novelty | PASS-candidate | Refuter did not refute (0.6); blind discrimination different mechanism (0.9); Hirschi and Tallec-Ollivier cited as ancestors; wording bounded to coverage | Signed provider-distinct novelty review after full-text and ACL sweep |
| Design | PASS-candidate | experiments/architectures/semantic-clock-gate-parity.yaml passes scripts/validate_architecture_experiments.py; experimental-design and statistical-power skills applied; randomization and blocking stated | Implement the CPU doctors and the episode builder; replace assumed noise with development-half estimates |
| Compute | FAIL | No real model loop, no container smoke, no Slurm dry run, no rebuilt image with fla; discovery image lacks fla; Qwen3.5-4B-Base and rwkv7 unregistered | Build and pin the image, register the checkpoints, write the job manifest, pass the dry run and the resume test |
| Safety | PASS-candidate | Monitorability, data rights (parallel-data and rwkv7 licenses unresolved and said so), IP and red lines addressed; integrity gate answered per mode | Runtime evidence for the g_t clamp and adversarial-suffix report |

## Independent Adversarial Reviews

Reviewer A: FAIL | provider=anthropic | model=claude | run_id=wave2-judge-A-2026-09-01 | artifact=research/gauntlet/2026-09-01-frontier/wave2-result.json (internal preliminary, NOT provider-distinct, unsigned)

Reviewer B: FAIL | provider=anthropic | model=claude | run_id=wave2-judge-B-2026-09-01 | artifact=research/gauntlet/2026-09-01-frontier/wave2-result.json (internal preliminary, NOT provider-distinct, unsigned)

Both scorecards below are the wave-2 internal judges. They are not the
provider-distinct, Ed25519-signed reviews the Gauntlet requires, so the accepted
score is capped at 89 and the proposal is NOT pilot-ready. Reviewer A's fatal
defect: C2 not identified (fertility confounded with resourcedness; EM readout
bypassable by the 8 full-attention layers and on ceiling; K5 pre-decided by the
owner's arithmetic; retrofit carried as architecture-causal). Reviewer B's fatal
defect: the phase-0 readout is not a readout of the GDN clock (same two
confounds; placebo not inert; per-cell TOST underpowered; Hirschi uncited).
Judges also filled the ARS criterion-bound form (quality_rubrics.md) with
calibration NOT_CALIBRATED.

## Scorecard

| Dimension | Reviewer A | Reviewer B | Defect/evidence |
|---|---:|---:|---|
| Question and strategic fit | 6 | 7 | Phase-0 deliverable is a retrofit recipe; scope now relabelled portability-protocol |
| Primary-source evidence | 8 | 8 | Substrate and numbers reproduce; Hirschi 2604.02474 was uncited, now cited |
| Defensible novelty delta | 6 | 6 | Recombination of Tallec-Ollivier and Hirschi with a new observable; coverage incomplete |
| Mechanism and falsifiability | 7 | 7 | Predictions explicit; K5 expected by arithmetic |
| Controls and causal identification | 3 | 4 | Fertility-resourcedness confound and attention bypass; wave-3 repair adds partial slope, attention-blind and attention-free readouts |
| Evaluation and statistics | 6 | 5 | Per-cell TOST underpowered; now pooled with per-cell descriptive; probe pushed off ceiling |
| Feasibility and information per GPU-hour | 7 | 7 | Arithmetic reproduced by the feasibility refuter; expanded grid re-costed at 14 GPU-h |
| Reproducibility and artifact contract | 5 | 6 | No image with fla, no registered Base, no execution |
| Safety, data rights, and monitorability | 8 | 8 | Licenses named; parallel-data and rwkv7 licenses unresolved |
| Independent adversarial review quality | 5 | 6 | Internal same-provider judges only; unsigned |
| **Total** | **61** | **64** | Lower total is authoritative: 61; capped at 89 by unsigned reviews |

## Iteration Log

| Wave | Score | Highest-impact defect | Change | Result |
|---:|---:|---|---|---|
| 1 | 0 | Killed before judging: identification refuted (0.8, parity loss collapses onto a per-language constant; placebo not inert) and feasibility refuted (0.7, 27B tokens in 14.4 GPU-h under-costed); see research/gauntlet/2026-09-01-frontier/wave1-ledger.md | Repair owner rewrote the pilot as a 4 GPU-h training-free phase 0 with equivalence as the primary comparison, log-ratio anchored loss, uniform-decay control, mark-aware tokenizer, Thai and Chinese controls | Advanced to wave 2 as a novelty survivor |
| 2 | 61 | C2 not identified: log fertility correlated -0.85 with Common Crawl share across the language set; EM readout on a 3:1 hybrid at d at most 32 is bypassable by the 8 full-attention layers and on ceiling; retrofit deliverable carried as architecture-causal | Judged only; both judges converged on one highest-impact fix | Ranked; lower total 61 |
| 3 | 61 | Same as wave 2 (the judges' agreed highest-impact identification fix) | ONE repair, the union of both judges' fixes: (a) language grid decorrelated with rus, tur, msa and C2 pre-registered as the partial fertility slope controlling for log CC share (interval excluding 0.2); (b) attention-blind query mask on every dose-response cell from a shared prefix pass plus the attention-free rwkv7 subject as the replication requirement for kills; d extended to 128 with an off-ceiling hold (K7) and the baseline EM(en) curve reported first; (c) claim scope relabelled portability-protocol for phase 0 with architecture-causal reserved for the gated phase 1; Hirschi 2604.02474 cited as mechanism ancestor; (d) length-matched placebo replaces the same-language random-pair placebo; (e) TOST pooled across languages with per-cell descriptive; budget re-costed 4 to 14 GPU-h | Not yet re-judged; Compute doctor FAIL by construction; not pilot-ready |

The evidence bundle follows `research/proposals/evidence/_schema.json`. All
source snapshots, query logs, reviewer outputs, doctor outputs, container and
Slurm attestations, and the hash-chained audit JSONL must live below the bundle
directory and match their recorded SHA-256 hashes. The bundle
evidence/semantic-clock-gate-parity/bundle.json does not exist yet. A prose
PASS without those artifacts is a deterministic FAIL. Each review receipt must
be Ed25519-signed by a provider-specific key loaded from the external read-only
path configured as `COTCODEC_TRUSTED_ATTESTORS_PATH` in trusted CI; proposal
authors cannot add a trust root inside the repository or their evidence bundle.
