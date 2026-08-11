# Direction 17: Causal Memory Holdout Trials

**Status:** frontier candidate; novelty audit passed narrowly; real-model pilot blocked
**Priority:** first new-mechanism pilot after the executable loop
**Claim scope:** causal credit assignment for agent memory, not a new database or harness
**Experiment contract:** `experiments/architectures/causal-memory-holdout.yaml`

## Research question

Can randomized serving of candidate memories produce causal, prefix-predictable
training targets that learn a better write/evict policy than recency, future-use
prediction, observational value backfilling, or policy-gradient memory training
at the same memory and rollout budget?

The new object is the **causal holdout trial**, not the storage layer. A candidate
memory is retained in an immutable, non-serving holdout ledger. At a preregistered
retrieval opportunity, a propensity-logged random assignment decides whether it
is exposed to the agent. The outcome is task utility, not attention mass or an
LLM reflection score. Cross-fitted causal pseudo-outcomes train a gate that sees
only information available when the memory is written.

Portable capsules may carry the intervention across harnesses, but they are
instrumentation. If an ordinary in-process implementation gives the same trial,
the scientific claim is unchanged.

## Why this may be new

Future-aware eviction and joint memory policies are already occupied by
ForesightKV, KVP, AgeMem, MemexRL, and MSCE. They use future attention,
observational feedback, reflection, or RL. Causal Memory Intervention performs
controlled interventions at query time. The closest work found in the current
audit does not combine:

1. known-propensity longitudinal assignment to serving versus shadow memory;
2. downstream executable agent-task utility as the outcome;
3. a paired replay oracle that audits the causal estimator;
4. a past-only gate trained from cross-fitted randomized-trial targets.

This is a narrow absence-of-direct-prior result through 2026-08-10, not proof of
global novelty.

## Implemented reference path (2026-08-10)

`harness/causal_memory_trials.py` now implements the Stage-0 causal spine:
content-addressed prefix events and direct feature lineage, deterministic
known-propensity assignment, an `fsync` assignment journal written before
continuation, serve/holdout exposure, same-arm A/A replay, common RNG/tool/
exogenous receipts, immutable raw and analysis manifests, group cross-fitting,
AIPW pseudo-outcomes, and a ridge effect policy. Paired-audit episodes are
excluded from every nuisance and policy fit. Estimator-to-oracle ATE gap,
pseudo-outcome correlation, and policy-to-oracle correlation are separate gates.
The only environment seam is `TrialWorld.prepare/continue_from`.

Run the executable symbolic doctor with:

```bash
uv run python scripts/run_causal_memory_sensitivity.py \
  --episodes 2000 \
  --world-seed 7 \
  --assignment-seed 42 \
  --audit-fraction 0.25 \
  --folds 5 \
  --output-dir data/results/causal-memory-holdout/stage0-seed42 \
  --require-gates
```

Success is named `SYMBOLIC_SENSITIVITY_PLUMBING_PASS`, not scientific `PASS`.
The three registered propensity cells currently exercise intervention ordering,
estimator-to-oracle plumbing, replay receipts, leakage rejection, and artifact
integrity against a known symbolic treatment effect. It does **not** yet satisfy
the full Stage-0 claim below: the
symbolic adapter is not the specified 20–40-step tool environment, the ridge
models are reference nuisances rather than the registered GBDT/MLP comparison,
and its prefix/replay receipts are still adapter-provided rather than derived by
an engine-owned live environment. A real-model result remains blocked on a
frozen-model `TrialWorld` adapter and the executable tool episode generator.

## Exact estimand

The pilot allows exactly one randomized candidate per episode. Let `S_q` be the
complete agent and environment snapshot immediately before the candidate's first
preregistered retrieval opportunity, `Z_i` indicate serving (`1`) or shadow
(`0`), and `U` be executable episode utility:

```text
tau_i(S_q) = E[U(Y_i(1)) - U(Y_i(0)) | S_q]
```

This is the effect of serving one retained item at its first eligible use. It is
not the globally additive value of a memory item and it does not identify all
effects of retaining many interacting memories. The one-candidate restriction is
removed only after a randomized saturation design measures interference.

For deterministic environments, fork two continuations from the same hashed
`S_q`, differing only in `Z_i`, with common RNG and tool responses. Their paired
difference is the audit oracle. Separately hide one branch and estimate the
effect from the logged randomized stream using cross-fitted augmented inverse
propensity weighting. The estimator must recover the paired oracle before it is
allowed on non-replayable tasks.

The deployed write/evict gate receives only prefix features available at the
write: source, semantic type, provenance, contradiction status, current budget,
and causal history. Future query text, use time, suffix outcome, branch identity,
and oracle deltas are forbidden inputs.

## Cheapest decisive methodology

### Stage 0 — symbolic identifiability doctor (CPU, less than two hours)

Generate deterministic 20–40-step tool episodes with facts, corrections,
deletes, high-surprise distractors, near-duplicate keys, and one- to three-hop
future queries. At one eligible candidate write per episode:

1. hash the prefix and environment state;
2. assign serve/shadow with `p=0.5` from a committed seed;
3. at first eligibility, fork paired continuations from the identical snapshot;
4. assert the two runs differ only in framed memory visibility;
5. compute exact success, tool-error, token, latency, and safety deltas;
6. discard all future fields before fitting the past-only gate.

Run at least 2,000 episodes. Split by generator family, namespace, composition
graph, correction type, and use-delay distribution, not by random rows.

### Stage 1 — frozen open-model screen (one GPU, at most eight GPU-hours)

Use a pinned 1–4B Hugging Face checkpoint and deterministic tool simulator.
Freeze the language model. Compare a small gradient-boosted/MLP gate before any
LoRA so that a gain cannot be attributed to changing the base model. Memory
budgets are `K={2,4,8}`; `K=4` is primary. Every arm receives identical candidate
records, retrieval calls, metadata bytes, tuning trials, and rollout budget.

The primary endpoint is paired executable success for the learned shadow-trial
gate versus the strongest non-randomized learned control at `K=4`. Require a
point gain of at least three percentage points with a paired 95% interval that
excludes zero. Diagnostic gates are:

- cross-fitted pseudo-outcome Spearman correlation at least `0.20` with the
  sealed paired oracle;
- calibration error and policy value stable across propensities `0.25`, `0.5`,
  and an operational `0.1` shadow rate;
- effective sample size at least 400;
- zero future-feature access and zero session bleed.

Use three training seeds for the kill screen and five only if the screen passes.
Bootstrap episodes within generator family; memory decisions are not independent
units. Report every seed and all negative strata.

### Stage 2 — Tinker/Kimi scale-up (only after Stage 1 passes)

Tinker can train a discrete memory controller or a model-specific LoRA that
emits `KEEP`, `EVICT`, and `RETRIEVE` actions. It cannot implement a new hidden
state or attention kernel. Run the Qwen interface cell first, then a separately
trained `moonshotai/Kimi-K2.6` cell on the same frozen trial protocol. The
external propensity logger, shadow ledger, split manifest, and evaluator remain
unchanged.

This tests whether causal trial targets improve a strong agent memory policy.
It does not claim portable LoRA weights or a new Kimi architecture.

## Controls

- FIFO, LRU, LFU, reservoir, and random retention;
- surprise/novelty and semantic-dedup gates;
- learned next-reference or reuse-hazard predictor with the same capacity;
- observational history-utility and reflection/value-backfilling controls;
- policy-gradient/GRPO memory controller with the same environment rollouts;
- query-time controlled intervention without longitudinal propensity logging;
- unlimited-memory ceiling and paired leave-one-out oracle;
- a fake shadow label and label-permutation negative control.

All controls match state bytes, metadata, read/write calls, model tokens,
environment evidence, search trials, and wall time. Trial-generation cost is
reported both per decision and amortized across downstream episodes.

## Falsifiers

Reject the direction if any of the following occurs:

- randomized estimates fail to recover the deterministic paired oracle;
- the estimator is unstable across propensities or effective sample size is
  below 400;
- prefix-only predictions have sealed correlation below `0.20`;
- next-use, observational utility, or matched-rollout RL ties the learned gate;
- the learned gate fails the three-point task-success threshold;
- multiple-memory interference erases the one-candidate result under the first
  saturation experiment;
- shadow storage, extra rollouts, or latency cost more than the context saved;
- any future field leaks into the policy or shadow content crosses sessions.

## Safety and data rights

Shadow memory is still retained data. The ledger must be session-scoped,
encrypted at rest, provenance-labeled, TTL-bound, deletion-capable, and excluded
from prompts unless assigned to serve. It stores framework-visible records, not
hidden chain-of-thought. Prompt injections in candidate memories are framed as
untrusted data. Report safety failure, tool-schema correctness, and refusal
consistency by arm; the project red lines still apply.

## Negative-result value

A null result would show that randomized causal memory effects are too sparse,
too interactive, or too expensive to predict from write-time information. That
would directly constrain future memory-policy papers and favor query-time
retrieval, deterministic eviction, or RL over causal backfilling.

## Queue gate

No GPU job may run until the symbolic paired-replay oracle, propensity logger,
future-feature denylist, split hashes, immutable model receipt, digest-pinned
container, Slurm manifest, atomic checkpoint, and fresh-job resume test all pass.
