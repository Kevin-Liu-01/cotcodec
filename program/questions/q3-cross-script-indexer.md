# Q3: Cross-script sparse-indexer recall

Status: Stage 0 (prerequisites). Role: preemptible backfill, first in the
backfill queue. Dossier entry: `E6-d21-translation-supervised-indexer`, rank 3,
BACKFILL. Carried over from direction D21; its premises all held.

## Question

In frozen open models fitted with KL-distilled top-k sparse-attention indexers
(the selector family used by DeepSeek's DSA and Qwen's QSA), does the indexer
miss more of the relevant passage than the dense model's own top-k attention
when the question is in a different script from the passage, at the same token
budget? Only if such a cross-script shortfall survives label-free fixes, test
whether a parallel-document alignment loss on the indexer improves recall on
languages it never saw.

Claims are limited to frozen retrofits, because production indexers were
co-trained with their backbones.

## Closest priors

| Paper | Date | Delta |
|---|---|---|
| [Cross-Lingual Alignment with MoE Routers](https://arxiv.org/abs/2610.01921) | 2026-10-01 | Same remedy on expert choice, not in-context token selection |
| [Lost in Compression](https://arxiv.org/abs/2608.26175) | 2026-08-28 | Cross-lingual audit of selectors outside the model |
| [Multilinguality in Hybrid Attention LLMs](https://arxiv.org/abs/2609.35378) | 2026-09-28 | Efficient-attention hybrids lose more non-English NIAH; recurrent hybrids only |
| [Oracle-Guided Sparse Prefill](https://arxiv.org/abs/2606.07703) | 2026-06 | Frozen KL indexers, monolingual |

Baseline recipes: DeepSeek-V3.2 DSA (2512.02556), Qwen3.8-Next QSA
(2608.30320).

## Live code

- Contract: `experiments/architectures/translation-supervised-sparse-indexer.yaml`
- Proposal (2026-09-01 gauntlet record): `program/proposals/2026-09-01-translation-supervised-sparse-indexer.md`
- CPU doctor: `harness/translation_supervised_indexer.py` and
  `scripts/run_translation_supervised_indexer_doctor.py`. It proves the Phase-0
  objects run and gates fire on synthetic cases only.

## Prerequisites before K1

1. GPU entry point `scripts/run_sparse_indexer_phase0a.py`.
2. Rebuilt image with tilelang and peft, re-pinned by digest after a smoke run.
3. A `qwen3-0.6b-base` checkpoint receipt.
4. Frozen ParaDocs and TED2020 manifests with pair hashes and a three-way
   passage-id partition.

## First experiment: K1 localization screen (about 1.5 GPU-h)

Frozen Qwen3-0.6B-Base. Fit block-form indexers (compress ratio 4) on all 28
layers with two target aggregations (head-sum, max-pool) x 3 seeds, in one
shared frozen-teacher stream of 20M tokens at 8K. Evaluate 1,200 Belebele
prompts at 8K: same-language question vs human-translated cross-script question,
for 7 held-out scripts {ja, ko, bn, ta, el, he, ka} in both directions with
English, plus a 200-prompt literal ceiling. Read recall at a matched achieved
budget of 12.5%. No sparse kernel is needed: the indexer is scored offline
against captured dense attention. Under 8 GPU-h, so no gauntlet for K1.

## Kill criteria (pre-registered)

- Shortfall at least 10 points for some target, with a 99% passage-cluster
  bootstrap interval excluding 0: go to the label-free remedy arms.
- Shortfall at most 5 points for both targets: publish the localization
  negative and stop.
- Dense cross-script baseline near floor: the shortfall is uninterpretable.
  Move to Qwen3.5-4B-Base at 3-5x cost, or stop.
- Report seed SD before any parallel-loss arm runs.
