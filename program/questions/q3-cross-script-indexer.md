# Q3: Cross-script sparse-indexer recall

Status: Stage 0. The dense headroom pre-check
(`q3-dense-headroom-precheck-v1`) ran on 2026-10-08 and ended INCOMPLETE with
no combined read. Its successor `q3-dense-headroom-precheck-v2` (D36, D42,
D44) was frozen at `ed5d5a9` and operated the same day: both lanes completed.
Its combined read is NEGATIVE_CAPABLE_V3 on Qwen3.5-4B-Base, with seven
requirements (see the last section). A K1 v3 on that base needs a new
experiment id, the research gauntlet and the program owner's decision (D26).
Role: preemptible backfill, first in the backfill queue. Dossier entry:
`E6-d21-translation-supervised-indexer`, rank 3, BACKFILL. Carried over from
direction D21; its premises all held.

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
- Qwen3.5-4B-Base lane (job 730): no receipt. It evaluated 18 of 74
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

## Dense pre-check v2 built (2026-10-08): draft, not frozen

D36 asked for a successor with v1's design unchanged and three repairs.
Branch `stage0/q3-dense-v2`; registration
`program/preregistrations/q3-dense-headroom-precheck-v2.md` (draft); evidence
`program/evidence/2026-10-08/q3-dense-headroom-precheck-v2-build/README.md`.

- Job binding: receipts take their Slurm job from the `job.env` the batch
  script writes before the container starts (the batch script is unchanged).
  An end-to-end test runs the real batch script against stub host tools and
  feeds the receipt to the summariser's job check.
- SIGUSR1: job 730 ignored it because Triton's LLVM replaces CPython's
  process-wide signal handlers at the first kernel compile (shown in the
  image). v2 blocks SIGUSR1 and SIGTERM from process start and consumes them
  at chunk boundaries. Verified as a container's PID 1 with a real Triton
  compile (v2 answers, v1 does not) and live on the GPU: the timing job
  answered Slurm's SIGUSR1 with a confirmed checkpoint.
- CPU bottleneck: not the cache copy (5 ms per unit) or the selectors (43 ms).
  torch 2.11 sends Qwen3.5's head-dimension-256 attention to cuDNN, which
  builds a new graph for every new sequence length, about 0.7 s of CPU per
  forward with the GPU idle. Timing job (Slurm 766, 0.057 GPU-h): cold units
  3.6-4.1 s; a reused prefill length 0.11 s against 0.8 s; units re-evaluated
  with cached graphs 0.51 s. v2 turns cuDNN's attention off on the 4B lane
  (not bit-equal to cuDNN; the receipt reports the difference on the first
  unit), a departure from D36 (iii) that D42 (i) accepts.
- Second timing job (D42 (ii); Slurm 810, 0.045 GPU-h, image from `87242fa`):
  the fixed path runs on the GPU, starting with the lane's
  `attention_backend_check` (47.4 s with the first-use compiles; recall within
  1.15 points and option scores within 0.011 of cuDNN's on the first unit,
  same answer); memory-efficient attention; first evaluations 0.16-0.43 s per
  unit by stage (the same chunks took 6 s against 54-108 s in Slurm 766);
  v1's path bit-equal on five units; SIGUSR1 answered at a chunk boundary.
- Validity gate: v2's 0.6B lane must reproduce job 727's receipt statistics to
  1e-6 (every numeric leaf of report, decisions, coverage, counts) and smoke
  452; the 0.6B code path is unchanged.
- Limits and caps by D36's rule, both measured: 0.6B 12 minutes (job 727), 4B
  32 minutes (D44: the largest of three estimates from Slurm 810, stage-mean
  scaling 769 s / 30 minutes, a per-stage line fit 789 s / 31, the larger of
  the two per stage 824 s / 32; 79 s start-up; completes at up to 1.4 s per
  unit), two timing jobs of 6; cap 32/60 GPU-h for the 4B lane, 0.933 GPU-h
  of D36's 1.5 in all. v2 used 0.102 GPU-h physical so far.

Next: freeze with the status and lead-in naming D42 and D44 (simulated on a
scratch clone: check-chain PASS, frozen-mode tests pass), image from the
frozen commit, doctor, the 0.6B lane, then the 4B lane.

## Dense pre-check v2 operated (2026-10-08): NEGATIVE_CAPABLE_V3 on Qwen3.5-4B-Base

Freeze steps 3-5 ran on branch `ops/q3-dense-v2`
(`program/evidence/2026-10-08/q3-dense-headroom-precheck-v2/README.md`). The
image was built from the frozen commit `ed5d5a9` (Slurm 855, CPU only) and
passed the v2 CPU doctor 12/12 (Slurm 856).

- **Qwen3-0.6B-Base lane** (Slurm 859, 279 s of 12 minutes): complete. It
  reproduced v1's job-727 receipt exactly: 3,128 numeric leaves with a
  largest gap of 0.0, and the same development artifact. It also reproduced
  K1 smoke 452. Its decisions equal job 727's: NOT_VIABLE (H1_CX 12.25;
  `h2_status` FAIL).
- **Qwen3.5-4B-Base lane** (Slurm 862, 555 s of 32 minutes): complete. It
  ran 0.26-0.53 s per unit by stage, against job 730's roughly 3.8 s, with
  cuDNN's attention off. The descriptive `attention_backend_check` stayed
  within 1.15 recall points and 0.011 in an option score of cuDNN's, with
  the same answer. The signal guard repaired Triton's replaced handlers.
  Decisions:
  - NEGATIVE_CAPABLE: H1_CX 42.15 points on target hs, 99 percent interval
    35.76 to 48.20; MN minus CX only 2.23.
  - `h2_status` POINT_ONLY: CX accuracy 49.6; H2b 8.6 with lower bound -9.3.
  - Lexical confound PRESENT: the literal selector's xi_rel is 0.26-0.27 on
    all families and 0.24 on entity-controlled families.
  - Entity control INSUFFICIENT.
  - Null calibration CENTRED for both targets.
  - Floor VIABLE: a V1-adequate noisy copy losing 2.57 English ML points has
    a controlled G(MN) lower bound of 0.93, against 0.24 for the literal
    selector.
  - Fertility association STRONG (Spearman -0.89 over seven languages).
- **Combined read** (registered summariser, exit 0): NEGATIVE_CAPABLE_V3 on
  qwen3.5-4b-base. A K1 v3 on that base may register a NEGATIVE region. Its
  requirements are D26's four plus three from the flags:
  - a seen-script cross-script condition;
  - an entity-controlled question set;
  - the non-literal floor (99 percent lower bound of G(MN) on controlled
    families at least 0.5);
  - a new id and the gauntlet;
  - GO and NEGATIVE statistics computed on the entity-controlled set;
  - anchor masking or a lexical-overlap covariate;
  - H2 re-tested under K1's bounds on the audit read.
- **GPU time:** 0.232 GPU-h used and 0.283 charged for the two lanes. v2 in
  all: 0.334 used and 0.433 charged, against caps of 0.933 and D36's 1.5.

The read covers the development partition only (20 questions, 20 passage
clusters). It says which K1 v3 designs the dense headroom supports. It is not
a K1 result and says nothing about whether an indexer loses more cross-script
recall than its target. Next: the program owner decides on a K1 v3.
