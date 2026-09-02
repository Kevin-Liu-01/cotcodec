# translation-supervised-sparse-indexer — wave-2 repair (2026-09-01)

Repair owner: single owner, wave 2. Inputs: candidates.md §2 (A2), wave1-verdicts.json (novelty not refuted at
0.6; identification refuted 0.8; feasibility refuted 0.75), brief.md incl. VERIFICATION PASS CORRECTIONS.
Status after repair: **kept, dropped=false**, claim_scope downgraded to **attachment-capability**, "exceeds the
dense teacher" removed from the claim, pilot split into a <= 4 GPU-h phase-0 kill screen (the cheapest decisive
pilot) + a gated <= 8 GPU-h phase 1 + an optional <= 4 GPU-h production-indexer probe (total <= 16 GPU-h), and the
pilot runs entirely on named public, license-cleared corpora. General Translation data is an optional upgrade only.

---

## 1. Claim (one line)

Learned sparse-attention indexers of the DSA/QSA class, distilled only from full attention, carry an **excess
cross-lingual selection gap** beyond the gap of their own distillation target; supervising the *detached* indexer
with **corpus-given sentence alignments** from bilingual document pairs (a training view that never touches main
attention; inference unchanged) removes most of that excess gap on **held-out languages** at **matched achieved
token budget**, and the fix shows up in generation exact match, not only in selection-recall proxies.

## 2. claim_scope

**attachment-capability.** The pilot tests a detachable indexer attached to frozen released checkpoints (the exact
setting SpotAttention 2606.22874 shows reaches dense parity in English). The architecture-causal version (indexer
objective inside QSA-style continued pretraining, or from-scratch hybrids with a parity tokenizer) is Phase 2,
gated and outside the 16 GPU-h contract. Wave-1 was right that nothing in a <= 16 GPU-h frozen-base pilot is
"architecture-causal"; the scope now says so.

## 3. Mechanism (repaired)

Indexer (DSA form, token level; QSA form, compressed block level with compress ratio 4; both as in the released
configs of GLM-5.3-Flash `index_n_heads 32, index_head_dim 128, index_topk 2048, index_kpool 4` and
Qwen3.8-Flash-Next `indexer_n_heads 4, indexer_kv_heads 1, indexer_head_dim 128, indexer_compress_ratio 4,
indexer_budget 2048`, both read from the HF configs on 2026-09-01):

    I_t(s) = sum_{j=1..H_I} w_{t,j} * ReLU(q^I_{t,j} . k^I_s),   s <= t   (block form sums over the block)
    S_t    = Top-k_s I_t(s);  the sparse layer attends over S_t only.

Distillation (unchanged, = DSA/QSA/SpotAttention): L_I = KL(P_t || softmax_s I_t(s)) with P_t a fixed aggregation
of the frozen layer's full-attention distribution. Three aggregations are arms, not assumptions: head-sum (DSA),
max-pool over heads (QSA), retrieval-head-weighted (heads ranked by copy score, 2404.15574). No gradient reaches
the backbone.

Translation view (repaired: **no external word aligner**). From a document pair (D_a, D_b) with the corpus's own
sentence alignment {(u_i, v_i)} build C = [D_b ; <sep> ; D_a] and the reverse order. For a query token t in
sentence u_i of D_a define the aligned key set A(t) = tokens of v_i in D_b, mapped to indexer granularity N(A(t)).

    L_x  = -(1/|Q|) sum_{t in Q} log sum_{s in N(A(t))} softmax_s(I_t(s)),    L_I' = L_I + lambda_x L_x

Q = content tokens of D_a whose sentence has an alignment; lambda_x in {0.25, 0.5}. The label is a property of the
training corpus (ParaDocs / TED2020 sentence alignment), symmetric across scripts, and is never used by any
evaluation metric. The wave-1 L_eq (unbalanced-Sinkhorn) arm is **dropped**: no differentiable implementation
exists in the repo (harness/translation_boundaries.py is a NumPy reference) and it is not needed for the claim.

Two alternative-mechanism arms with the same loss form: L_perm (alignment labels permuted within the document —
same loss, wrong content; a negative control, not a "placebo") and L_half (log-mass on the whole other-language
half of C, no sentence alignment — tests whether merely pushing mass across the language boundary suffices).

Why an excess gap is plausible: production indexers are rank-128 ReLU scorers with 1–4 query heads, trained on
aggregated attention mass that is dominated by same-language, same-script matches; the low-rank scorer need not
preserve the cross-script semantic subspace that the 16–64-head teacher uses. Whether this is true is exactly
P1; nobody has measured it (novelty refuter, wave 1).

## 4. What is new (downgraded per the novelty refuter's caveats)

Honest framing: the mechanism is a recognizable transfer of **supervised / guided attention from NMT** — Liu et
al. 2016 (https://arxiv.org/abs/1609.04186, 2016-09-14), Chen et al. 2016 guided alignment
(https://arxiv.org/abs/1607.01628, 2016-07-06), Garg et al. 2019 (https://arxiv.org/abs/1909.02074, 2019-09-04) —
which supervise the *main* encoder–decoder attention with aligner labels. The delta is (i) the object: a
*detached* top-k selection indexer of a decoder-only sparse-attention LM, whose main attention never sees the
signal; (ii) the label: corpus-given sentence alignment on concatenated bilingual documents (no aligner);
(iii) the instrument: a cross-lingual **selection-recall** measurement with the indexer's own distillation
target as the reference, on held-out languages at matched achieved budget. The load-bearing new claim is the
diagnostic P1, not the loss.

Deltas against the three closest priors:
- DeepSeek-V3.2 / DSA — https://arxiv.org/abs/2512.02556 — 2025-12-02 — lightning indexer trained by KL to
  head-summed attention (2.1B-token frozen warm-up then 943.7B tokens unfrozen); no per-language analysis. Ours
  adds an alignment-supervised selection term and measures per-language selection.
- On the Design of Qwen3.8-Next (QSA) — https://arxiv.org/abs/2608.30320 — 2026-08-31 — compressed-block indexer
  with max-pooled KL target at CPT; only aggregate MMMLU reported. Ours is a drop-in objective for that indexer;
  the QSA recipe (KL, max-pool) is the baseline arm, not the proposal.
- SpotAttention — https://arxiv.org/abs/2606.22874 — 2026-06 — the frozen-Qwen3/Qwen3.5 KL-distilled selector with
  dual top-p budgets, dense parity in English up to 128K, non-English untested. Ours is its cross-lingual audit
  plus a fix; SpotAttention's top-p rule is a mandatory control. (No public code or checkpoints found via GitHub
  and HF search 2026-09-01; we re-implement the KL-only selector.)

Also opened / cited: LongCat LSA https://arxiv.org/abs/2608.01662 (2026-08-03; cross-layer index distillation);
PIVOT https://arxiv.org/abs/2607.24593 (2026-07-27; training-free indexer replacement — control); NSA
https://arxiv.org/abs/2502.11089 (2025-02-16; pooled-key selection without a learned indexer — control); Lost in
Compression https://arxiv.org/abs/2608.26175 (2026-08-28; cross-lingual selection gap in learned compressors
"tracks supervision data, not architecture", budget-matched in the target tokenizer — its protocol is adopted);
MLNeedle https://arxiv.org/abs/2408.10151 (2024-08-19), OneRuler https://arxiv.org/abs/2503.01996 (2025-03-03),
MGAL https://arxiv.org/abs/2608.20853 (2026-08-21; multilingual granularity/position-aware long-context benchmark
on UN reports, 6 languages — endpoint candidate, opened today, no sparse-attention component); Retrieval heads
https://arxiv.org/abs/2404.15574 (2024-04-24; <5% of heads do retrieval — motivates the retrieval-head-weighted
target arm). Not opened by me, taken from the wave-1 identification verdict: RTPurbo (top-k vs top-p shifts
RULER-64K 70.5 -> 85.5; 2608.26449 as cited there), FlashMemory-DeepSeek-V4 https://arxiv.org/abs/2606.09079,
counterfactual sparse audit 2608.01676, prefix-invariance audit 2608.22876.

No direct prior art found through 2026-09-01 under: wave-1 novelty search (9 arXiv, 4 HF-papers, 7 WebSearch,
full text of DSA and QSA) plus today's arXiv API query `abs:indexer AND abs:"sparse attention" AND (multilingual
OR cross-lingual OR translation)` (3 hits: MiniMax MSA 2606.13392, FlashMemory 2606.09079, Dynamic Sparse
Attention 2603.13430 — none multilingual by title/abstract) and HF-papers `cross-lingual sparse attention indexer
multilingual long context selection` (MGAL, Milco, OneRuler, mLongRR; no indexer paper).

## 5. Endpoints (held-out; the training loss never sees them)

Prompt pi = (haystack H in language l_N from FineWeb-2, needle passage N in l_N from a sealed source at position
p in {begin, middle, end}, query Q in language l_Q). Haystack language == needle language, so a cross-lingual
needle is not the only foreign-script block. Conditions: monolingual (l_Q = l_N), cross-lingual same-script,
cross-lingual cross-script. Matched pairs differ only in the language of Q.

- **E1 needle-token selection recall** R = |S_t ∩ N| / |N| averaged over content tokens t of Q and over the
  sparse layers (also reported per layer). k is set three ways: achieved-budget fraction rho in {6.25%, 12.5%,
  25%} of |H| in the model's tokenizer (primary); fixed absolute k in {512, 1024, 2048}; k scaled by the needle's
  token count. Defined by the needle's position only; independent of any alignment label or aligner.
- **R^T**: the same statistic for the top-k of the KL target distribution (head-sum / max-pool /
  retrieval-head-weighted) — the KL-only ceiling.
- **Gaps**: Delta_ind = R(mono) - R(cross-script); Delta_T likewise; **excess gap xi = Delta_ind - Delta_T** is the
  kill statistic.
- **E2 generation exact match**, sparse attention restricted to S_t via fla `parallel_nsa` (block indices), two
  tasks with gold answers: (a) TR-NIAH — "output the sentence that immediately follows the sentence whose
  translation is: <sentence in l_Q>" scored by EM against the next sentence of the needle passage in l_N (answer
  language fixed = l_N in mono and cross conditions, so answer-language effects cancel); (b) Belebele cross-lingual
  MC (passage in l_N, question+options in l_Q), permutation-controlled over the 4 option orders (chance 25%).
- **E3 monolingual non-regression**: RULER-style English NIAH/multi-key at the same k, and E1/E2 in each
  language's monolingual condition.
- Audits: two-forward-pass prefix invariance (2608.22876), needle-position stratification, per-language floor,
  achieved-token ledger per prompt per language.

Held-out design: indexer training pairs en–{de, fr, es, pl, th, hi, km} (ParaDocs) and en–{zh_cn, ru, ar}
(TED2020). **Held-out eval languages never seen by L_x**: cross-script ja, ko, bn, ta, el, he, ka; same-script id,
tr, sw, nl, it (all in Belebele). In-training languages are reported separately as secondary. Both query
directions (en query / l_N needle, and l_N query / en needle) are primary; non-English pairs secondary.

Sample sizes and MDE: E1 with >= 2,000 matched prompt pairs per condition (SE of Delta < 1 point); E2 with 1,500
prompts per configuration (SE ~ 1.3 points at p = 0.5), 3 seeds per arm, paired-by-prompt tests, alpha = 0.01.
Pre-registered MDE: 3 points on E1 gaps, 5 points on E2 arm differences.

## 6. Falsifiable predictions (counterfactual reference named in each)

- **P1 (phase-0 kill screen).** For KL-only indexers (token form on qwen3-0.6b-base; block form on the 8
  full-attention layers of qwen3.5-4b), on held-out cross-script pairs at 8K, rho = 12.5%: Delta_ind >= 15 points
  and **xi >= 10 points** (the indexer loses more cross-script recall than its own target does). Reference: the
  same indexer's monolingual recall on identical prompts, and R^T on the same prompts.
- **P2.** Arm (c) KL + L_x versus arm (b) KL-only on the identical bilingual concatenations (the counterfactual for
  every L_x claim): (c) recovers >= 60% of xi on held-out language pairs at rho = 12.5% with monolingual E1 within 1
  point of (b) and E3 within 0.5 points; and (c) - (d, L_perm) >= 0.5 x [(c) - (b)], (c) - (e, L_half) >= 0.5 x
  [(c) - (b)].
- **P3.** E2 TR-NIAH EM on held-out cross-script pairs at 8K–16K: (c) - (b) >= 8 points; monolingual within 2
  points; no training-free control at matched achieved budget (SpotAttention-style top-p, larger k at matched
  measured latency, PIVOT-style query-group re-scoring, NSA pooled-key selection, SWA + sinks at matched KV bytes)
  recovers >= 50% of that gain; the dense + alignment-supervised LoRA control recovers < 50%.
- **P4 (exploratory, not load-bearing, removed from the claim).** With oracle-selection and random-plus-needle
  controls in place, sparse-with-L_x minus dense on cross-lingual E2 >= 0. Any positive result here is attributed
  to selection denoising only if the oracle arm shows the same sign; QSA's own dense-beating RULER numbers make
  this generic.
- **P5 (Phase 2, outside the pilot).** From-scratch 60–125M 3:1 GDN + sparse-global hybrid with a fertility-
  balanced BPE: cross-script gap >= 2x the same-script gap for KL-only and <= 1.3x with L_x at equal BPB (+/- 0.5%).

## 7. Kill conditions

1. Phase 0: xi <= 5 points on both bases for both indexer forms — the indexer is not a bottleneck beyond its
   target; publish the localization negative and stop.
2. (c) - (b) < 30% of xi on held-out pairs — bilingual exposure alone does the work.
3. (d) L_perm or (e) L_half achieves >= 80% of (c)'s recovery — the loss form / cross-language mass push, not
   alignment content, is the mechanism (re-frame as a regularizer paper or stop).
4. Any training-free control at matched achieved budget recovers >= 80% of (c) - (b).
5. The dense + alignment-LoRA control recovers >= 80% of the gain — the effect is not selection-specific.
6. E1 gains without E2 gains (proxy-only effect), or gains confined to in-training languages.
7. Any held-out language's E1 recall drops > 2 points versus (b), or E3 drops > 0.5 points (a supervised selector
   must not under- or over-select a language).
8. Phase-0 headroom gate fails on both bases (dense monolingual E2 < 60% at 8K) — then only E1/xi are reported
   and the E2 claim is withdrawn, not rescued by a larger model inside this contract.

## 8. Cheapest decisive pilot — Phase 0 (<= 4 GPU-h on 8x H100; the pilot of record)

Phase 0 CPU doctors (no GPU): (i) data builder for bilingual concatenations from ParaDocs/TED2020 with the
sentence-alignment map, mass accounting for L_x (sum of label mass per query in (0, 1]), permutation sensitivity
(L_x on true vs permuted labels differs on synthetic data); (ii) NIAH/TR-NIAH builder with the per-prompt
achieved-token ledger (Qwen tokenizer) and exact-50-gram + MinHash (Jaccard >= 0.8) dedup of FineWeb-2 haystacks
and training docs against Belebele/WMT24++/FLORES+ texts, with removal counts logged; (iii) synthetic
bilingual toy (two vocabularies related by a fixed permutation; random rank-32 ReLU indexer vs full softmax
teacher) reproducing an excess cross-vocabulary gap and its repair by L_x — a sanity check, not evidence.

Phase 0a GPU (kill screen for P1 + headroom gate), single Slurm job, shared-teacher multi-indexer training:
- Bases (frozen): `qwen3-0.6b-base` = Qwen/Qwen3-0.6B-Base @ da87bfb608c14b7cf20ba1ce41287e8de496c0cd (28 layers,
  16Q/8KV x 128, hidden 1024; indexers on all layers); `qwen3.5-4b` = Qwen/Qwen3.5-4B @
  851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a (32 layers, full attention at layers 3,7,...,31 = 8 layers, 16Q/4KV x
  256, GDN elsewhere; indexers on the 8 full-attention layers only — the production placement). Both registry
  ids; both apache-2.0.
- Indexers: token form (4 x 128, DSA) and block form (4 x 128, 1 kv head, compress 4, QSA) x 3 seeds = 6 per
  base, all trained in the same forward pass of the frozen teacher (no gradient into the backbone, so arms share
  one teacher stream — this is what makes the budget hold; wave-1 assumed one job per arm).
- Data: 50M tokens = 6,104 sequences x 8,192; half bilingual concatenations, half monolingual FineWeb-2 in the
  same languages.
- Eval: E1 and R^T on 3,000 sealed prompts (Belebele needles, held-out languages, 3 positions) at 8K/16K/32K,
  dense attention computed for the query tokens only; dense E2 headroom check on 600 prompts per base.

Budget (FLOP/byte arithmetic; H100 SXM 989 TFLOPS dense BF16 and 3.35 TB/s HBM3 from the NVIDIA datasheet, not
re-fetched today; **assumed 30% MFU = 297 TFLOPS and 2.0 TB/s effective**, i.e. half the ~60% MFU llm.c reports
for GPT-2 124M — https://github.com/karpathy/llm.c/discussions/481, 2024-05-28, "10B tokens ... ~90 minutes" on
8x A100 80GB, opened via Jina 2026-09-01):

| item | work | GPU-h |
|---|---|---|
| teacher fwd, 0.6B, 50M tok @8K (2.76 GFLOP/tok incl. 1.88 attention) | 1.4e17 FLOP | 0.13 |
| attention-probability materialization for the KL target, 28 layers (16 x 8192^2 x 2 B, write+read) | 7.3e14 B | 0.10 |
| teacher fwd, 4B hybrid, 50M tok (≈8 GFLOP/tok; 8 dense-attention layers + fla chunk_gdn) | 4.0e17 FLOP | 0.37 |
| materialization, 8 layers | 2.1e14 B | 0.03 |
| 12 indexers fwd+bwd (token form 34 GFLOP/layer/seq fwd; block form 16x cheaper) + score-matrix traffic | ≈1.5e17 FLOP + 1e15 B | 0.25 |
| E1 eval, 3,000 prompts x {8K,16K,32K}, both bases, all indexers attached | ≈9e17 FLOP | 0.85 |
| dense E2 headroom, 600 prompts x 2 bases | 1e17 FLOP | 0.10 |
| **subtotal** | | **1.85** |
| x1.25 reserve | | **2.3** |
| **cap (Slurm/IO overhead, one rerun)** | | **4.0** |

Decision: P1 holds (xi >= 10 on at least one base and form) -> Phase 1. xi <= 5 on both -> kill (condition 1) and
write the localization negative. In between -> Phase 1 with the E1 threshold re-registered to the observed xi.

Kernel reality (feasibility repair): fla ships only `fla/ops/dsa/naive.py` (einsum reference; confirmed via GitHub
API 2026-09-01), so the indexer score I_t(s) is computed by chunked PyTorch matmuls (per layer at 8K: 4 x 8192^2 x
2 B = 0.5 GB in bf16, chunked over query blocks); the sparse attention over S_t for E2 uses fla's Triton NSA
selection kernel `parallel_nsa` / `parallel_nsa_topk` (`block_indices: [B, TQ, H, S]`, `block_counts`,
`block_size`; signatures read from `fla/ops/nsa/parallel.py` 2026-09-01) with block size 32 or 64; at 32K the
dense teacher distribution is computed only for the query tokens (a few hundred rows), never as a full 32K^2
matrix. fla `chunk_gdn` handles Qwen3.5-4B's linear layers (GB200 first-party table: fwd+bwd B=2, T=16384, H=16,
D=128: chunk_gdn 3.616 ms vs flash_attn 19.960 ms; B=1, T=8192, H=96: 4.738 vs 15.371 ms — fla README, opened via
GitHub API 2026-09-01).

Phase 0b (optional, hard-capped 4 GPU-h, runs whether Phase 0a passes or kills — external validity of the
retrofit result): inference-only probe of the **production QSA indexer** in Qwen/Qwen3.8-Flash-Next @
de4b8e4d43b917e7706784d8bb445c9af86a3540 (180B total params per HF safetensors metadata, 512 experts top-10, 48
layers, QSA at 12 full-attention layers, `model_type qwen4_exp_text`, native `transformers/models/qwen4_exp`
confirmed 2026-09-01; license "qwen-community-1.0" — non-standard, review before publishing numbers). bf16
weights ≈ 360 GB across 8x H100 with transformers device_map; hook the indexer scores and the same layer's dense
scores for the query tokens; E1/R^T on ~300 sealed prompts at 8K. Gate: a 20-prompt timing probe must show
<= 8 s per 8K prompt or the job aborts and records the throughput. GLM-5.3-Flash (zai-org, MIT, DSA indexer) is
321B total params (≈642 GB bf16) and does not fit the node in bf16; excluded.

## 9. Phase 1 (gated on P1; <= 8 GPU-h incl. reserve; same shared-teacher design)

Arms on qwen3-0.6b-base, 100M tokens (12,208 x 8K), 3 seeds each unless noted, all indexers trained in one
teacher stream: (a) KL-only, monolingual contexts; (b) KL-only, bilingual concatenations [data control =
counterfactual]; (c) KL + L_x; (d) KL + L_perm; (e) KL + L_half; (f) KL with max-pooled target (QSA); (g) KL with
retrieval-head-weighted target; (h) indexer dim ladder 64 / 256 for (a) and (c); token form for (a),(c) only,
block form for all (token-form score matrices dominate cost). Replicate (a)–(d) x 2 seeds on qwen3.5-4b's 8
full-attention layers. Separate small job: dense + alignment-supervised LoRA control (rank-16 on q,k of all
layers of qwen3-0.6b-base; LM loss + lambda L_x applied to the head-summed main attention; 2 seeds x 60M tokens) —
the information-symmetric dense control demanded by wave 1. Training-free controls at eval only: SpotAttention
dual top-p, larger k at matched measured latency (fla kernel timing, warm-up reported), PIVOT-style query-group
re-scoring, NSA pooled-key selection (fla `nsa/compression.py`), SWA + sinks at matched KV bytes (2608.28444),
oracle needle-block inclusion + random fill, random-plus-needle.

| item | GPU-h |
|---|---|
| teacher stream 0.6B, 100M tok + materialization | 0.5 |
| 6 token-form + 27 block-form indexers, fwd+bwd + score traffic | 0.6 |
| qwen3.5-4b replicate, arms a–d x 2 seeds, 100M tok | 0.9 |
| dense + L_x LoRA control, 2 seeds x 60M tok (fwd+bwd + materialization) | 1.2 |
| E1 eval, 4,000 (0.6B) + 2,000 (4B) prompts, shared forward, all indexers | 0.8 |
| E2 eval, 22 configurations (15 learned + 7 training-free) x 1,500 prompts x <= 16K, sparse kernel | 1.5 |
| subtotal 5.5; x1.25 = 6.9; **cap 8.0** | |

Phase 0a (4) + Phase 1 (8) + optional Phase 0b (4) = **16 GPU-h**. Phase 2 (new contract, not in this budget):
from-scratch 60–125M 3:1 GDN + QSA-style sparse-global hybrid with a fertility-balanced BPE, KL-only vs KL + L_x, 3
seeds, ~1–2B tokens; using llm.c's 124M reference (10B tokens ≈ 12 A100-GPU-h at 1K context) and a 2x allowance
for 8K context, GDN layers and indexer overhead, ≈ 30 GPU-h — the arm that would carry an architecture-causal
claim, and the moonshot QSA-style CPT of qwen3.5-4b (~170 GPU-h) beyond it. Tinker is not used in the pilot (no
indexer access; API key absent per wave 1); GLM-5.3/Qwen3.5 behavioral baselines there are a future option.

## 10. Controls (complete list, mapped to wave-1 demands)

Dense full-attention teacher (reference bound) · KL-only on identical bilingual concatenations (data control; the
counterfactual for L_x) · L_perm negative control · L_half alternative-mechanism arm · max-pooled and
retrieval-head-weighted KL targets, and R^T measured directly (the KL ceiling) · indexer dim ladder 64/128/256
(iso-parameter otherwise) · dense + alignment-supervised LoRA at matched tokens (information-symmetric dense
control) · achieved-budget matching in the model tokenizer (rho), fixed absolute k, needle-fertility-scaled k
(Lost in Compression protocol) · SpotAttention dual top-p (mass-matched budget) · larger k at matched measured
latency · PIVOT-style training-free re-scoring · NSA pooled-key selection (no learned indexer) · SWA + sinks at
matched KV bytes · oracle needle-block selection and random-plus-needle (attribution of any dense-beating effect)
· iso-token across all arms (same 100M tokens, same order) · iso-wall-time kernel timing per arm · held-out
languages never seen by L_x · haystack language = needle language · permutation-controlled MC scoring ·
needle-position stratification · prefix-invariance audit · per-language recall floor and E3 non-regression ·
dedup ledger. Strongest published baselines: QSA/DSA KL recipes (arms a, f), SpotAttention (KL + top-p), PIVOT.

## 11. Public data plan (runs WITHOUT General Translation data)

Training contexts (indexer distillation + L_x):
- **ParaDocs** — https://huggingface.co/datasets/jhu-clsp/paradocs (dataset card license apache-2.0; underlying
  ParaCrawl text CC0 per https://paracrawl.eu; paper https://aclanthology.org/2024.findings-acl.589/). Document-
  level ParaCrawl with sentence alignment inside documents; `data/` dirs verified 2026-09-01: en-{cs, de, es, fr,
  hi, hu, id, it, km, lo, my, ne, nl, pl, pt, sv, th, vi}. Used pairs: same-script en–{de, fr, es, pl};
  cross-script en–{th, hi, km}. Filtered with the release's own `paradocs` filters (minimum_size 2,
  frequency_cutoff 100, lid_cutoff 0.5) — replaces the wave-1 aligner threshold tau.
- **TED2020 v1 (OPUS)** — https://opus.nlpl.eu/TED2020 ; XML with talk-level documents and sentence alignment,
  verified via the OPUS API 2026-09-01: en–zh_cn 3,827 docs / 399,092 pairs / 8.05M en tokens; en–ru 3,699 /
  386,316; en–ar 3,879 / 403,716; (held out from training but available for a secondary in-domain check: en–ja
  3,493 docs, en–ko 3,753 docs). Text license: TED Talks usage policy, CC BY-NC-ND 4.0
  (https://www.ted.com/about/our-organization/our-policies-terms/ted-talks-usage-policy) — research use, no
  redistribution of modified text; the OPUS legacy page could not be fetched from this Mac, so confirm the
  statement on the TED page before the run.
- **FineWeb-2** — https://huggingface.co/datasets/HuggingFaceFW/fineweb-2 @ af9c13333eb981300149d5ca60a8e9d659b276b9
  (ODC-By 1.0): monolingual filler and haystacks in every needle language, deduplicated against all eval texts.

Sealed evaluation sources (never in training; different provenance from ParaCrawl/TED):
- **Belebele** — https://huggingface.co/datasets/facebook/belebele @ 7899cdfa4e1e0d733fd77c848e2c273cb1d32be2
  (CC-BY-SA 4.0): 488 FLORES-200 passages (avg 4.1 sentences) x 122 language variants, 900 questions per variant —
  needles, TR-NIAH next-sentence answers, and cross-lingual MC.
- **WMT24++** — https://huggingface.co/datasets/google/wmt24pp @ fd7405c06494bc66a57b25f55d217a72f96e60dc
  (apache-2.0): 55 en->xx human-translated document-level sets with `document_id` — second, document-shaped
  TR-NIAH set (news/social/speech/literary domains).
- **FLORES+** — https://huggingface.co/datasets/openlanguagedata/flores_plus (CC-BY-SA 4.0, gated with automatic
  approval): optional extra sentence-level needles.
- Optional endpoints for the write-up only: MLNeedle, OneRuler, MGAL (UN reports, 6 languages) — sealed.

Contamination: Belebele/FLORES are Wikipedia-family text; ParaDocs/TED/FineWeb-2 are web/talk text; still, exact
50-gram and MinHash dedup of every training and haystack document against every eval text, with counts in the
run receipt (wave-1 objection 8).

General Translation upgrade (optional, not required for any prediction): document-level pairs with in-house
alignment QA for low-resource cross-script pairs (e.g. en–{my, lo, am}) as additional held-out or training
languages, and as the corpus for the Phase-2 CPT stage; under contract, not redistributable — reported as a
separate arm if used.

## 12. Kevin advantage (honest)

The pilot no longer depends on any private asset. What makes it easy here: 8x H100 with the Docker/Slurm/
checkpoint harness for the shared-teacher multi-indexer job (one sbatch, SIGUSR1-resumable); a repository whose
product is exactly the instrument this candidate delivers (per-language achieved-token ledger, selection-recall
probe, sealed eval receipts); General Translation's document-level parallel pairs and translation QA for the
low-resource upgrade and the Phase-2 CPT stage; and a real deployment interest (cross-lingual long-context
retrieval over translation memories) that no sparse-attention lab has stated.

## 13. collision_risk

**medium.** Searches: wave-1 novelty triad (9 arXiv API, 4 HF-papers, 7 WebSearch, full text of 2512.02556 and
2608.30320) found no per-language indexer analysis and no alignment-supervised indexer; today's rechecks (arXiv
API query and HF-papers query in §4) found only MGAL (a benchmark) as new since 2026-08-10. Why not low: every
DSA/QSA lab and the SpotAttention authors can run P1 in days; MGAL's authors have the multilingual long-context
benchmark and could add sparse models next.

## 14. Monitorability and safety

The selection set is an inspectable retrieval trace; per-language selection recall is an audit instrument for
sparse models, including detection of cross-lingual prompt injection that only a foreign-script block carries.
No CoT effect. Failure modes monitored as kill condition 7: under-selection of any language, and over-selection
of the other-language half in bilingual prompts (E3 monolingual regression, and a bilingual-distractor test where
the other-language half is irrelevant). Data rights: ParaCrawl CC0, ParaDocs annotations apache-2.0, TED CC
BY-NC-ND 4.0 (non-commercial research; no redistribution of derived text), FineWeb-2 ODC-By, Belebele/FLORES+
CC-BY-SA 4.0, WMT24++ apache-2.0; Qwen3-0.6B-Base and Qwen3.5-4B apache-2.0; Qwen3.8-Flash-Next
qwen-community-1.0 (review before publishing probe numbers). No IP exposure at kernel level (no delta-rule kernel
contribution; the NVIDIA GDN patent flag in the brief does not apply).

## 15. Negative-result value

xi <= 5: the cross-lingual long-context gap in sparse models is inherited from attention mass, not from the
selection component — the first component-level localization of the gap MLNeedle/OneRuler/MGAL describe, plus a
portable selection-recall instrument for any DSA/QSA checkpoint. (b) ≈ (c): bilingual document exposure alone
repairs indexers — a free recipe for every sparse-attention lab. (d) or (e) ≈ (c): a mass-concentration
regularizer, not alignment content, is what indexers need — a smaller but publishable finding. Dense+LoRA ≈ (c):
alignment supervision is a generic attention fix, not selection-specific — redirects the work. Phase 0b: whether a
production QSA indexer agrees with the retrofit result either way is reportable.

## 16. targets_gaps

synthesis G13 (cross-lingual behaviour of learned sparse indexers), G2 (recurrent/hybrid behaviour with content
fixed across translations — hybrid base qwen3.5-4b), G20 (evaluation instruments at 0.1–1B); seq-operators G6;
benchmarks-eval G2 (translation-paired NIAH probes); local-model G4 (translation-shaped evaluation of a 2026 open
hybrid).

## 17. Repairs made (wave-1 objection -> fix or accepted limitation)

Identification refuter:
1. Circular metric (aligned-block recall = training label) -> primary endpoints E1 (needle-token recall defined by
   needle position) and E2 (generation EM with gold answers) on sealed sources of different provenance and on
   languages never seen by L_x; no evaluation quantity is computed from alignment labels.
2. Retrofit vs architecture; SpotAttention already publishes the frozen KL-only arm -> claim_scope downgraded to
   attachment-capability; SpotAttention adopted as the named baseline whose non-English behaviour is the open
   question; production-like placement on qwen3.5-4b's full-attention layers; optional production-indexer probe
   (Phase 0b); from-scratch/CPT arms moved to a gated Phase 2 outside the 16 GPU-h.
3. Token-budget confound at fixed top-k -> achieved-budget fraction in the model tokenizer as primary k, plus fixed
   absolute k and needle-fertility-scaled k; top-p (SpotAttention/RTPurbo) control; per-prompt achieved-token
   ledger; haystack language = needle language; Phase-2 parity-BPE arm.
4. Head-summed target may itself be the bottleneck -> R^T measured directly; xi (excess gap over the target) is the
   kill statistic; max-pooled and retrieval-head-weighted target arms; indexer dim ladder.
5. Information asymmetry (L_x injects an external aligner) -> labels are corpus-given sentence alignments (no
   OmniAlign/CTFAlign); dense + alignment-supervised LoRA control at matched tokens; L_perm negative control; L_half
   alternative-mechanism arm; iso-token everywhere.
6. "Sparse exceeds dense" is generic denoising -> removed from the claim; exploratory P4 only, with oracle-selection
   and random-plus-needle attribution controls.
7. Label noise correlated with treatment (Ja/Ko/Th AER) -> no word aligner; sentence alignment quality is a
   corpus property applied uniformly; ParaDocs release filters replace tau; per-pair label mass reported.
8. Contamination (WikiMatrix vs MLQA/Wikipedia) -> WikiMatrix dropped; training/haystack sources are web and TED
   text; exact + MinHash dedup against all eval texts with logged counts; held-out languages.
9. Dense ceiling unknown for 0.6B -> Phase-0 headroom gate measured first on both bases; E1/xi does not need
   generation headroom; E2 claim withdrawn (not rescued) if the gate fails (kill condition 8).
10. Omitted NMT supervised-attention prior art -> Liu 2016, Chen 2016, Garg 2019 added; novelty statement
    downgraded to "transfer of guided attention to a detached selection indexer with an untested diagnostic".

Feasibility refuter:
1. Parallel data assumed, repo holds none; WikiMatrix/ParaCrawl not document-level; aligners unvalidated for
   ko/th -> ParaDocs (document-level, CC0 text, en–th/hi/km cross-script verified) + TED2020 (talk-level,
   en–zh_cn/ru/ar verified counts) named with URLs, licenses and revisions; no aligner needed; GT optional.
2. Harness pieces missing (UOT doctor is NumPy; no NIAH/RULER code; fla DSA only naive) -> L_eq arm dropped;
   NIAH/TR-NIAH builder and selection-recall instrument are declared Phase-0 CPU deliverables with doctors;
   indexer scores by chunked PyTorch; sparse attention via fla `parallel_nsa` (Triton, block-index API
   verified); dense distributions only for query rows at 32K.
3. Budget assumed shared teacher passes and omitted eval -> shared-teacher multi-indexer training made explicit
   (all arms in one stream, valid because no gradient reaches the backbone); FLOP/byte tables with cited
   reference points (llm.c ~60% MFU, fla kernel table) and an assumed 30% MFU plus 25% reserve; eval costed;
   Phase 0 <= 4, Phase 1 <= 8, optional 0b <= 4.
4. Frozen KL warm-up is never deployed as-is; sparse-shock confound -> accepted limitation, stated in scope; the
   kill statistic xi compares the indexer to its own target on the same frozen model (sparse shock cancels); E2
   compares sparse arms to each other at identical k, never sparse-vs-dense as the claim; Phase 0b probes a
   deployed indexer.
5. Tinker unavailable -> removed from the pilot.

Accepted limitations: results on frozen retrofits do not prove production CPT indexers have the gap (Phase 0b is
optional and inference-only); TED text is non-commercial and not redistributable; Qwen3.8-Flash-Next's license
is non-standard; MFU is assumed, not measured — the first job records tokens/s and the budget is re-verified
before Phase 1 is submitted.

## 18. Coverage limits (today)

Host calls used 8/10: abs 2608.12149 (throughput not in abstract; its GitHub README/reproduction.md have no
tokens/s or MFU lines), OPUS TED2020 page (404 on the new site; counts taken from the OPUS API instead), llm.c
#481, abs 2608.26175, abs 2606.22874, one arXiv API query, one HF-papers query, abs 2608.20853. Not opened:
RTPurbo, FlashMemory-DeepSeek-V4, 2608.01676, 2608.22876 (taken from the wave-1 verdict), the SpotAttention
full text, the TED usage-policy page, the NVIDIA datasheet (values from memory). WebSearch not used (budget
exhausted). No Chinese-language sources, ACL Anthology full text, or patents searched today.
