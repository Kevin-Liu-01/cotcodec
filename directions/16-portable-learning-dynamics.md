# Direction 16: Portable Sidecar Update Dynamics

**Status:** architecture-adjacent hypothesis; 43/100 then 66/100 in adversarial review
**Priority:** formal collision/interface work before a claim pilot
**Detailed program:** `research/frontier-systems-program-2026-08-10.md`
**Executable methodology:** `research/architecture-experiment-methodologies.md`

## Narrow question

Can one task-conditioned, episode-scoped low-rank **sidecar state update** port
to a held-out task–base pairing through task-blind, capacity-capped base
alignments?

This is deliberately narrower than the original “portable update dynamics”
idea. It does not conflate fast weights, native retention gates, and learned
optimizers. It does not claim to transfer the native update operation of a
Transformer versus DeltaNet. The object being ported is a sidecar update rule
attached to a residual-stream interface shared by both.

## Mechanism

The frozen base exposes four evenly spaced residual-stream attachment layers.
For base `b`, layer `l`, action step `j`, pooled residual `h_j^l`, task latent
`e_τ`, and structured outcome `o_j`:

```text
z_j^l       = P_b^l h_j^l
h'_j^l      = h_j^l + Q_b^l M_j^l z_j^l
M_(j+1)^l   = Π_r[ρ_j^l M_j^l + η_j^l u_j^l (v_j^l)ᵀ]
```

`M_j^l ∈ R^(64×64)` is the only online-updated tensor and is stored in rank-8
factorized form. `Π_r` truncates the update back to rank eight. The portable
network consumes `(e_τ, z_j^l, o_j)` and emits scalar `ρ_j^l ∈ [0,1]`, scalar
`η_j^l`, and vectors `u_j^l,v_j^l ∈ R^64`. Each layer owns separate state;
there is no implicit state sharing. `P_b^l ∈ R^(64×d_b)` and
`Q_b^l ∈ R^(d_b×64)` are rank-8 factorizations, not dense trainable matrices.
Their factors are the only base-specific parameters and use
`64(d_b+64)` trainable parameters across four layers (about 266K at
`d_b=4096`). The registered cap is `min(1,000,000, 0.1% of base parameters)`;
alignment rank must be reduced below eight if needed to satisfy it.

The causal event order is fixed: read all `M_j^l` while generating action `j`,
emit the action, receive its structured outcome `o_j`, and write `M_(j+1)^l`
once between action steps. No token may read outcome-derived state in the same
step that produced the outcome. State persists for one episode, resets at the
declared boundary, and uses about 8 KiB of bf16 factor storage at the registered
four-layer, rank-8, width-64 setting, excluding fixed projections.

The first implementation must freeze one feedback encoding—such as a typed tool
outcome or supervised streaming label—before the proposal names a primary
claim. It cannot mix feedback regimes in that claim.

## Why this belongs near CoTCodec

CoTCodec makes orchestration policies explicit. This direction moves one
boundary inward: the framework chooses an update budget, evidence stream,
reset policy, and state lifetime. It can use the same deterministic trace,
safety, and Pareto-analysis contract without claiming hidden cognition.

This is not Variable 16 in the original orchestration taxonomy. It is an
architecture-adjacent program.

## Closest work and candidate delta under review

- [PorTAL](https://labs.ramp.com/research/portal-portable-task-adaptation/):
  task-conditioned static LoRA generation through a canonical core and base
  alignment.
- [TTT layers](https://arxiv.org/abs/2407.04620) and
  [Titans](https://arxiv.org/abs/2501.00663): online model/state updates inside
  sequence models.
- [Meta-Learning Bidirectional Update Rules](https://proceedings.mlr.press/v139/sandler21a.html):
  a low-dimensional genome of update rules that transfers to unseen tasks.
- [Metz et al.](https://arxiv.org/abs/2009.11243),
  [ALFA](https://arxiv.org/abs/2011.00209),
  [VeLO](https://arxiv.org/abs/2211.09760),
  [Celo2](https://arxiv.org/abs/2602.19142), and
  [Meta-TTL](https://arxiv.org/abs/2604.00830): task- or architecture-general
  learned optimizers and transferable test-time adaptation.
- Differentiable plasticity, fast-weight programmers, Meta-SGD, HINT,
  HyperTuning, and continual-learning hypernetworks remain required audit axes.

These precedents invalidate the broad “portable learning rule” novelty claim.
No direct prior was found through 2026-08-10 for the narrower conjunction:
task-conditioned online sidecar update, task-blind cross-operator alignment,
and held-out task–base pairing evaluation. This is a bounded search statement,
not proof of global novelty, and collision risk remains high.

## Identification split

Use five disjoint roles:

1. `T_meta × B_source`: meta-train the canonical rule on at least one Transformer
   and one recurrent/hybrid operator. Optimize prequential next-action/tool loss
   after online updates with truncated backpropagation through eight action
   steps, plus state-norm and reset-consistency penalties.
2. `T_anchor × B_source`: fit anchor-task latents on source bases only, then
   freeze those latents.
3. `T_anchor × b_target`: fit only the target base alignment using the frozen
   anchor latents. The alignment never sees `τ_new`.
4. A disjoint `T_dev × B_dev`: select rank, horizon, checkpoint, thresholds,
   and the exact feedback encoding. Neither these tasks nor pairings appear in
   the sealed target cell.
5. `τ_new × b_source`: fit the new task latent, freeze rule/latent/alignment,
   then evaluate the missing cell `τ_new × b_target` with zero target-cell
   calibration or training data. The preregistered causal online outcome stream
   remains available during evaluation, identically for every dynamic method.

Pre-register all seen/unseen task × seen/unseen base cells. Tool-schema tasks
must split generator/template family, namespace, argument ontology, and
transformation family. Composition tasks train primitives and seal composed
test structures. Calibration labels, online feedback, validation outcomes, and
test outcomes are separate.

## Baselines and accounting

- static PorTAL plus matched LoRA target-module/rank sweeps;
- ordinary SGD, RLS/delta, and native TTT/DeltaNet update rules;
- a direct per-base learned updater and oracle task-specific updater;
- common sidecar without portability;
- same task latent with a static delta;
- same portable rule without task conditioning;
- in-context adaptation and no-update controls.

For the decisive missing-cell comparison, every dynamic method receives the
same preregistered causal outcome stream and no target-cell pretraining. A
direct target updater or target-trained LoRA that sees target-cell labels is
reported only as an oracle with extra information, never as a matched control.

Match trainable parameters, state bytes, observed evidence, update count,
persistence lifetime, reset frequency, inference FLOPs, hyperparameter trials,
early-stopping access, and wall time. Amortize source meta-training and report
the break-even number of tasks/bases.

## Primary outcomes and falsifiers

Use prequential accuracy/regret before the first write and after every write,
adaptation half-life, reset recovery, deletion accuracy, poisoning persistence,
cross-request bleed, and static final accuracy. The task family, feedback
encoding, multiple held-out tasks and bases, one primary statistic, and a
task/base-level power analysis must be frozen in the Gauntlet proposal.
Episodes are repeated measurements, not the generalization unit.

Reject if:

- alignment-only, latent-swap, rule-swap, or anchor-permutation controls recover
  the task;
- the held-out task–base pairing does not beat common-sidecar and fresh-optimizer
  controls under matched information and compute;
- gains disappear under equal hyperparameter search;
- the amortized break-even task count is impractical;
- reset, isolation, deletion, or poisoning tests cross project red lines.

## Compute gate

The first ≤16 H100-hours are only an interface and throughput contract test:
one cell, three seeds, measured seconds/step, unroll length, peak HBM, episode
throughput, checkpoint overhead, and output integrity. There is no approved
150–300-hour matrix until that timing evidence exists and a Gauntlet proposal
with a hashed evidence bundle passes all doctors.

The discovery pair is the pinned Qwen3-0.6B Base plus Mamba-130M HF. The
official Kimi Linear 48B-A3B Base checkpoint is a later scale-only target base
after the small-base missing-cell result passes. It requires reviewed/vendored
custom code and a measured 8-H100 tensor-parallel load/checkpoint/restore test;
it is not part of the cheap discovery claim.
