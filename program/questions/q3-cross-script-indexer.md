# Q3: Cross-script sparse-indexer recall

Status: Stage 0. The dense headroom pre-check
(`q3-dense-headroom-precheck-v1`) ran on 2026-10-08 and ended INCOMPLETE with
no combined read; the next step is the program owner's (see the last
section). Role: preemptible backfill, first in the backfill queue. Dossier
entry: `E6-d21-translation-supervised-indexer`, rank 3, BACKFILL. Carried
over from direction D21; its premises all held.

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

## Status after the K1 v2 gauntlet (D26)

K1 v1 stopped at its smoke gate; K1 v2 ended at an honest gauntlet exit
(score 45, triad 3 of 3 refuted): NEGATIVE needs 20 points of dense headroom
against about 14 measured at 0.6B, a selector flat on both non-literal legs
falls inside NEGATIVE, GO is confounded by literal anchors that Belebele keeps
in same-language questions, and cross-script is collinear with unseen scripts
and tokenizer fertility. Next is a dense-only headroom pre-check
(`program/preregistrations/q3-dense-headroom-precheck-v1.md`; frozen
2026-10-08 after D32): the
development partition of the K1 bundle only, Qwen3-0.6B-Base and
Qwen3.5-4B-Base, at most 0.5 GPU-h. Its combined read says whether any K1 v3
can register a NEGATIVE, on which base, and which controls it needs beyond
D26's, which always apply (an entity-controlled question set, a non-literal
floor, a seen-script cross-script condition): for example a null-calibrated
statistic or anchor masking. Any K1 v3 takes a new id and runs the gauntlet.

## Dense pre-check operated (2026-10-08): INCOMPLETE

Freeze steps 3-5 ran on branch `ops/q3-dense`
(`program/evidence/2026-10-08/q3-dense-headroom-precheck/README.md`). The
image built from `a369e6d` passed the CPU doctor (7/7).

- Qwen3-0.6B-Base lane (job 727, 4.6 minutes): complete. K1 smoke 452
  reproduced to within 1e-6 points (T:hs 26.45, T:mp 26.08, rand 12.48).
  Lane decisions: NOT_VIABLE (H1_CX 12.25 points, 99 percent lower bound
  8.98; H2b -3.93, so `h2_status` FAIL), lexical confound and entity control
  NOT_EVALUABLE, null calibration NOT_EVALUABLE, floor NOT_VIABLE, fertility
  association STRONG. Half of the 20 development questions are
  entity-anchored.
- Qwen3.5-4B-Base lane (job 730): no receipt. It evaluated 18 of 73
  chunks at about 61 s each (GPU idle when sampled, one CPU core busy) and reached
  its 21-minute limit; it did not act on SIGUSR1 and was killed by the hard
  stop. No minutes remain under the id, so the lane is INCOMPLETE.
- The registered summariser refused the 0.6B receipt: the receipt's
  `slurm_job_id` is null because the batch script does not pass
  `SLURM_JOB_ID` into the container, and the summariser requires it. Under
  the registration's rule the combined read is INCOMPLETE; it was not
  written. No base, design or stop is read.
- GPU time: 0.419 GPU-h used, 0.467 charged under the registration's rule.

Any successor takes a new experiment id and is the program owner's decision.
