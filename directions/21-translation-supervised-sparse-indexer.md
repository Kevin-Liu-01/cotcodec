# Direction 21: Translation-Supervised Sparse Indexer

**Status:** OPEN on 2026-09-01 — wave-3 identification re-registration applied; judged 61/100 in wave 2 (cap 89); not pilot-ready
**Priority:** CPU doctors and a ≤ 4 GPU-h Phase-0 kill screen before any identification run
**Experiment contract:** `experiments/architectures/translation-supervised-sparse-indexer.yaml`
**Proposal:** `research/proposals/2026-09-01-translation-supervised-sparse-indexer.md`

## Research question

Do the learned top-k indexers that DeepSeek-V3.2 (DSA), Qwen3.8-Next (QSA),
GLM-5.3-Flash and SpotAttention attach to sparse-attention layers lose more
cross-script selection recall than the full-attention target they are distilled
from — once monolingual and cross-lingual queries are equally non-literal — and,
if a residual gap survives the strongest label-free target aggregation, does
corpus-given sentence-alignment supervision of the *detached* indexer close it
on languages the alignment loss never saw?

The claim scope is **attachment-capability**: a detachable indexer on frozen
released checkpoints. The load-bearing new content is the diagnostic, not the
loss. The architecture-causal version (indexer objective inside QSA-style
continued pretraining, or from-scratch hybrids with a parity tokenizer) is a
gated Phase 2 under a separate contract.

## Mechanism

```text
Indexer (DSA token form; QSA block form with compress ratio 4), per sparse layer:
  I_t(s) = sum_{j=1..H_I} w_{t,j} * ReLU(q^I_{t,j} . k^I_s),   s <= t
  S_t    = Top-k_s I_t(s);  the sparse layer attends over S_t only
Distillation from the frozen layer (no gradient into the backbone):
  L_I    = KL( P^T_t || softmax_s I_t(s) ),  T in {head-sum (DSA), max-pool (QSA),
           retrieval-head-weighted};  T* = argmin_T xi_T on development languages
Translation view on a bilingual document pair with the corpus's own sentence
alignment {(u_i, v_i)}, C = [D_b ; SEP ; D_a] and the reverse:
  A(t)   = tokens of v_i for a query token t in u_i, mapped to indexer granularity
  L_x    = -(1/|Q|) sum_{t in Q} log sum_{s in N(A(t))} softmax_s I_t(s)
  L_I'   = L_I + lambda_x L_x,   lambda_x in {0.25, 0.5}
Same-form controls: L_perm (labels permuted within document), L_half (whole
other-language half), L_sem (monolingual TyDi QA question -> gold passage, no
parallel data, iso-token).
Evaluation (never uses alignment labels); four query conditions share (H, N, p):
  ML mono-literal (verbatim needle sentence)        -> ceiling row only
  MN mono-non-literal (Belebele question in l_N)    -> reference leg
  CS cross same-script, CX cross cross-script (same question, human-translated)
  Delta_ind = R_ind(MN) - R_ind(CX);  Delta_T = R_T(MN) - R_T(CX)
  xi_T = Delta_ind - Delta_T   (excess gap; both legs non-literal)
  Lambda = R(ML) - R(MN)       (literalness gap; reported separately)
  rho_x = [xi_T* - xi_T*+x] / xi_T*   (recovery over the best label-free target)
```

Inference is unchanged. The label is a corpus property (ParaDocs, TED2020),
symmetric across scripts, and no external word aligner is used.

## Closest work and delta

| Closest work | Source | Same | Delta |
|---|---|---|---|
| DSA lightning indexer (KL to head-summed attention; 2.1B-token frozen warm-up, 943.7B unfrozen) | [2512.02556](https://arxiv.org/abs/2512.02556) | indexer and KL recipe | alignment-supervised selection term; per-language selection audit against the target |
| QSA compressed-block indexer with max-pooled KL target | [2608.30320](https://arxiv.org/abs/2608.30320) | block form, max-pool target (arm) | drop-in objective for that indexer; QSA recipe is the label-free counterfactual, not the proposal |
| SpotAttention frozen-backbone KL selector, dual top-p, English dense parity | [2606.22874](https://arxiv.org/abs/2606.22874) | frozen KL-only arm (re-implemented; no public code) | its cross-lingual audit plus a fix; its top-p rule is a mandatory control |
| Oracle-Guided Sparse Prefill: frozen KL indexer plus attention-mass top-k oracle separating budget feasibility from indexer error | [2606.07703](https://arxiv.org/abs/2606.07703) | monolingual precursor of the indexer-versus-target decomposition | cross-lingual axis; literalness control; added in wave 3 |
| Guided/supervised NMT attention (Liu 2016, Chen 2016, Garg 2019); AlignAtt4LLM | [1609.04186](https://arxiv.org/abs/1609.04186), [1607.01628](https://arxiv.org/abs/1607.01628), [1909.02074](https://arxiv.org/abs/1909.02074), [2606.03967](https://arxiv.org/abs/2606.03967) | loss form on main attention | object is a detached selection indexer of a decoder-only sparse LM; corpus sentence labels; inference unchanged |
| Lost in Compression (cross-lingual gap of learned compressors tracks supervision data) | [2608.26175](https://arxiv.org/abs/2608.26175) | achieved-budget protocol adopted | attention indexers, not prompt compressors |
| NoLiMa, RULER, induction heads (literal-match retrieval is easy; non-literal collapses) | [2502.05167](https://arxiv.org/abs/2502.05167), [2404.06654](https://arxiv.org/abs/2404.06654), [2209.11895](https://arxiv.org/abs/2209.11895) | motivates the non-literal reference leg | none claimed; these are why the wave-2 statistic was not identified |
| Retrieval heads; RTPurbo (low-dimensional retrieval subspace, 16-dim indexer, top-k inferior to top-p) | [2404.15574](https://arxiv.org/abs/2404.15574), [2605.16928](https://arxiv.org/abs/2605.16928) | retrieval-head-weighted target (arm) | measured per language against the other aggregations |
| MLNeedle, OneRuler, MGAL (dense cross-lingual long-context behaviour) | [2408.10151](https://arxiv.org/abs/2408.10151), [2503.01996](https://arxiv.org/abs/2503.01996), [2608.20853](https://arxiv.org/abs/2608.20853) | mandatory dense baselines and endpoints | localizes the gap to the selection component or exonerates it |

No direct prior art found through 2026-09-01 under the wave-1 novelty triad,
the wave-2 rechecks and the wave-2 novelty refuter's coverage (13 hostsearch,
10 WebSearch, 10 WebFetch; 10 of 13 arXiv boolean queries returned HTTP 429; 4
OpenReview hits unread) for an alignment-supervised detached selection indexer
or a per-language selection audit of a learned sparse indexer. Pending a signed
provider-distinct novelty review.

## Cheapest decisive pilot

CPU doctors first (no GPU): concatenation builder with L_x mass accounting and
permutation sensitivity; four-condition TR-NIAH builder with a per-prompt
achieved-token ledger and exact 50-gram plus MinHash dedup; a synthetic
permuted-vocabulary toy; a 20-prompt indexer-versus-target smoke run in the
rebuilt pinned container under a Slurm dry-run; a Q-head padding or gather path
for fla `parallel_nsa` (both bases fail its HQ/H ≥ 16 assertion).

Phase 0a (≤ 4 GPU-h, one job, the pilot of record): frozen `qwen3-0.6b-base`
(indexers on all 28 layers) and `qwen3.5-4b` (indexers on its 8 full-attention
layers; post-trained checkpoint — Qwen/Qwen3.5-4B-Base is the preferred,
unregistered base); three target aggregations × two indexer forms × 3 seeds
per base, all in one frozen-teacher stream on 50M tokens (half bilingual
concatenations from ParaDocs/TED2020, half FineWeb-2); E1 and R^T on 4,000
sealed Belebele prompts in held-out languages across the four conditions at
8K/16K/32K; adequacy gate (English literal recall within 5 points of R^T);
dense monolingual and cross-lingual TR-NIAH headroom on 1,200 prompts per base.
Decision: ξ_T ≥ 10 for some T and base → Phase 1; ξ_T ≤ 5 everywhere → publish
the localization negative and stop.

Phase 1 (≤ 10 GPU-h, gated): arms (a) KL-T* monolingual, (b) KL-T* bilingual
[primary counterfactual], (b′)/(b″) the other aggregations, (c) KL-T* + L_x
[primary treatment], (c′) head-sum + L_x [DSA-style secondary], (d) L_perm,
(e) L_half, (i) L_sem, (h) dim ladder 64/256; 4B replicate of (b), (c), (d),
(i) × 2 seeds; dense LoRA pair (j) LM-only and (k) LM + L_x; training-free
controls at eval only. Primary endpoint: (c) − (b) ≥ 6 recall points and ≥ 60%
of ξ_T* on held-out cross-script pairs at ρ = 12.5%.

Phase 0b (optional, ≤ 2 GPU-h, descriptive): inference-only probe of the
production QSA indexer in Qwen3.8-Flash-Next on 120 prompts with a 6 s abort
threshold. Total ≤ 16 GPU-h; Phase 2 is a separate contract.

## Controls

Strongest label-free target T* (primary) and the DSA head-sum recipe
(secondary); full aggregation ladder for the artifact test; L_perm and L_half
with inertness preconditions (|d − b| ≤ 1, |e − b| ≤ 1); information-matched
L_sem; dense LoRA pair (LM-only, LM + L_x); achieved-budget ρ, fixed k,
fertility-scaled k, SpotAttention dual top-p; larger k at matched measured
latency, PIVOT-style re-scoring, NSA pooled-key selection, SWA plus sinks at
matched KV bytes; oracle needle-block with random fill, random-plus-needle,
needle-absent; MLNeedle and OneRuler dense baselines; literal-copy ceiling and
Λ; indexer dim ladder; iso-token and iso-order in one teacher stream; held-out
languages never seen by any supervised loss; both query directions; prefix-
invariance audit; per-language floor and English E3 non-regression.

## Falsifiers

- K1: ξ_T ≤ 5 for every aggregation on both bases (adequacy gate passed).
- K2a: a de-diluted label-free target recovers ≥ 80% of the head-sum gap.
- K2b: L_x recovers under 30% of the residual ξ_T*.
- K3: with inertness holding, L_perm or L_half reaches ≥ 80% of L_x's recovery.
- K4: L_sem reaches ≥ 50% of L_x's recovery on held-out cross-script pairs.
- K5: a training-free control at matched budget recovers ≥ 80% of the E2 gain.
- K6: the L_x-specific dense LoRA gain reaches ≥ 80% of the sparse E2 gain.
- K7: E1 gains without E2 gains, or gains confined to in-training languages.
- K8: any held-out language loses over 2 recall points or English E3 loses
  over 0.5.
- K9: dense cross-lingual TR-NIAH EM under 40% on both bases withdraws the E2
  claim; a sparse floor under R^T − 5 makes E2 contrasts on that base
  floor-bound. Any E2 score above dense counts only with oracle-sign agreement.

## Compute

Phase 0a ≤ 4, Phase 1 ≤ 10, Phase 0b ≤ 2 GPU-h on the 8 × H100 node; assumed
30% MFU (297 TFLOPS/GPU, 2.0 TB/s effective), measured by the first job and
re-verified before Phase 1. The only real image
(`127.0.0.1:5000/cotcodec-research@sha256:15d6abc06fa53ab466087a92107da9c58e469615e2f56a683fefd0a7600277f3`,
created 2026-08-16) lacks fla, peft and flash-attn; the pilot needs a rebuilt
image with fla ≥ 0.5.2, peft and the new code, re-pinned by digest. Seeds
42/43/44 with pre-registered escalation to five seeds for block-form arms if
the Phase-0 seed SD of ξ exceeds 2 points (closed-form MDE about 5.6 points at
three seeds under an assumed 2-point seed SD). Launch through
`scripts/submit_docker_research_job.py` (dry-run, then submit); SIGUSR1
checkpoints every 15 minutes; fresh-job resume test per phase. Tinker is not
used (no indexer access; key absent).

## Kevin advantage

The pilot depends on no private asset. What makes it easy here: a Docker/Slurm
harness that trains many detached indexers in one shared frozen-teacher stream
under one sbatch; a repository whose product is exactly this instrument
(per-language achieved-token ledger, indexer-versus-target selection recall,
sealed receipts); General Translation's document-level parallel pairs with
alignment QA as an optional upgrade for low-resource cross-script pairs and as
the Phase-2 continued-pretraining corpus; and a genuine deployment interest —
cross-lingual long-context retrieval over translation memories under a sparse
indexer — that no sparse-attention lab has stated.

## Negative-result value

K1 localizes the cross-lingual long-context gap to attention mass rather than
selection — the first component-level answer to what MLNeedle, OneRuler and
MGAL only describe — and leaves a portable selection-recall instrument. K2a is a
free recipe finding comparing the DSA and QSA target choices per language. K2b
says bilingual exposure alone repairs indexers. K3 says a mass-concentration
regularizer is what indexers need. K4 says parallel data is not the active
ingredient, redirecting the program away from its unique asset early. K6 says
alignment supervision is a generic attention fix. The literalness gap Λ is
publishable alone as the first literal-versus-semantic decomposition for
learned selectors. Phase 0b reports whether a production indexer agrees either
way.

## 2026-09-01 wave-3 identification re-registration

Wave 1 killed the candidate (identification 0.8, feasibility 0.8; novelty not
refuted). Wave 2 repaired it to attachment-capability with sealed non-label
endpoints and public data and scored 64/61 (lower authoritative; cap 89), with
identification still refuted (0.72) because the counterfactual for every L_x
claim was the head-sum KL arm and the kill statistic compared a verbatim-copy
monolingual query with a zero-overlap cross-lingual query. Wave 3 applies the
judges' union highest-impact fix as one repair: non-literal ξ with the Belebele
question-as-query reference and a literal ceiling row; T* as the primary
counterfactual with K2a/K2b; inertness preconditions; L_sem and LM-only LoRA
arms; G1/G2 headroom gates, oracle-sign rule and needle-absent control on the
generation endpoint; 2606.07703 cited; RTPurbo id corrected to 2605.16928;
adequacy gate; parallel_nsa head-padding; Phase 0b at 6 s and 120 prompts;
qwen3.5-4b relabelled post-trained. Budget re-derived to 4 + 10 + 2 = 16 GPU-h.
Pending re-judging.
