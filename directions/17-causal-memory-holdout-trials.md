# Direction 17: Causal Memory Holdout Trials

**Status:** frontier candidate; novelty audit passed narrowly; real-model pilot blocked
**Priority:** first new-mechanism pilot after the executable loop
**Claim scope:** prospective first-service effect estimation for one retained memory item,
not generic memory credit assignment, a causal write/eviction effect, a database, or a harness
**Experiment contract:** `experiments/architectures/causal-memory-holdout.yaml`

## Research question

Can prospective, known-propensity randomization of a retained candidate at its
first eligible service opportunity produce prefix-predictable effect targets
that learn a better service gate than recency, future-use prediction,
observational value backfilling, or policy-gradient memory training at the same
memory and rollout budget?

The new object is the **causal holdout trial**, not the storage layer. A candidate
memory is retained in an immutable, non-serving holdout ledger. At a preregistered
retrieval opportunity, a propensity-logged random assignment decides whether it
is exposed to the agent. The outcome is task utility, not attention mass or an
LLM reflection score. Cross-fitted causal pseudo-outcomes train a gate that sees
only information available when the memory is written.

The randomized treatment begins after retention. It therefore identifies a
first-service effect, not the effect of writing, retaining, or evicting the item.
Those are separate treatments and require separate prospective assignments.

Portable capsules may carry the intervention across harnesses, but they are
instrumentation. If an ordinary in-process implementation gives the same trial,
the scientific claim is unchanged.

## Why this may be new

Future-aware eviction and joint memory policies are already occupied by
ForesightKV, KVP, AgeMem, MemexRL, and MSCE. Memory-R2 combines global
trajectory reward with local group-relative rerollouts anchored at identical
intermediate memory snapshots; sampled manager actions include INSERT, UPDATE,
DELETE, and NOOP. VerMem
combines executable local transition verification with global verification and
hierarchical credit across long-term, active-context, and episodic memory.
AttriMem uses post-hoc query-and-answer-conditioned randomized masks for local
attribution, RoMeRL separates co-retrieved utility, Retain-or-Consolidate trains
a query-observable pre-generation packing router from replacement effects, and
Causal Memory Intervention performs controlled interventions at query time.
Those works invalidate a generic
"causal memory credit" claim. The closest work found in the current audit still
does not combine:

1. known-propensity longitudinal assignment to serving versus a holdout ledger;
2. downstream executable agent-task utility as the outcome;
3. a paired replay oracle that audits the causal estimator;
4. a past-only gate trained from cross-fitted randomized-trial targets.

This is a narrow absence-of-direct-prior result under the recorded primary-source
and official-code search through 2026-08-14 UTC, not proof of
global novelty. The admissible statement is "no direct prior found under the
recorded search coverage," never "globally novel."

ForesightKV now has an official pinned training/evaluation repository, so it is
an executable latent-eviction control once its missing software license is
resolved. The pin changes reproducibility, not the collision analysis.

### Closest-work collision ledger

- **MemRL** is the mandatory outcome-updated episodic-utility control. It updates
  every selected top-k memory with executable episode reward, so outcome-trained
  memory utility is occupied; its shared bundle reward does not identify an item.
- **U-Mem** is the closest stochastic service-and-credit collision. It uses
  Thompson sampling plus a paired memory-bundle-versus-base advantage, but applies
  that bundle effect to utilized memories rather than identifying one item.
- **AEL and epsilon-MemEvo** are mandatory stochastic service-policy controls.
  They learn no-memory/serve intensity from later outcomes, but their treatments
  are policy or retrieved-memory bundles rather than one prospective item.
- **QCR** is the matched downstream memory-support control: no memory, generic
  summary, full trajectory, and query-conditioned reuse under matched execution.
- **Tidemark** is the mandatory observational item-credit control. Its receipts
  bind recalled items to later success or blame, but exposure and reported use are
  selected rather than randomized.
- **Memory Worth / When to Forget** is the cheapest mandatory observational
  value and forgetting control. Its two counters converge to conditional
  success given retrieval; the paper explicitly states that this is association,
  not causal contribution.
- **CoEvo-Mem** occupies alternating joint evolution of a retrieval router and
  outcome-updated memory values and graph relations. It is a coupled learned
  controller control, not a prospective item-service estimator.
- **Memory-R2** is the mandatory same-state rerollout control; it kills broad
  counterfactual memory-credit novelty but lacks a prospective persistent-item
  first-service propensity and population estimand.
- **VerMem** is the mandatory executable verifier-credit control; it kills
  broad local/global memory-credit and active/inactive-controller novelty but
  does not estimate a randomized retained-item service effect.
- **Retain or Consolidate?** is the mandatory query-time packing-router control;
  a past-only version would be a separate restricted reimplementation.
- **AttriMem and RoMeRL** are mandatory post-hoc attribution and
  interference-aware credit controls.
- **MemCon and AgeMem** are mandatory learned operation/controller controls.
- **Causal Memory Intervention** remains a query-time audit/oracle control, not
  the prospective longitudinal estimand.
- **MemHarness and MemState** cover state-conditioned experience reconstruction
  and governed trajectory-level CRUD correctness, respectively; neither joins
  the four required causal components above.
- **SMSR** is the mandatory randomized-ablation safety control; it kills any
  first-randomized-holdout wording but does not estimate a logged first-service
  population ATE/CATE or train a write-time gate.
- **Unified Memory Agent, RecMem, and Remember When It Matters** are mandatory
  active/inactive, consolidation, and proactive-service controls.
- **MindMemOS** occupies active/archive residency, temporal graphs, learned CRUD,
  feedback repair, dreaming/consolidation, and skill evolution. It is currently
  literature-only because the official repository has no resolved code license.
- **UnifiedMem, MAGMA, and CompassMem** require graph arms to face aligned flat,
  multi-graph, and active event-graph controls rather than a weak vector baseline.
- **ReFind** makes agentic search over raw logs the mandatory simple retrieval
  floor; **ProGraph** is the mandatory graph-free multi-hop control.
- **Router-Mem and ERSkill** occupy shallow/deep memory routing and learned
  retrieval programs; they are controller controls, not parts of the novelty claim.
- **MemGuide** occupies intent-conditioned, missing-slot-guided proactive
  retrieval. It is a task-oriented-dialogue control rather than a general
  write-time causal service policy.
- **LycheeMemory V2 and ScrubJay-MEM** occupy segment consolidation and
  type-conditioned decay; both are required when the treatment includes
  consolidation, expiry, or active/inactive movement.
- **PMMC** occupies predicted-future-question memory compilation; future-question
  prediction cannot be novelty wording for the past-only gate.
- **memorywire and ToolAtlas** occupy backend and provider-side tool-memory
  portability. Capsules and strap-on adapters remain experimental transport.
- **LiveMem** is an intrinsic state-continuity boundary reference, not an
  external semantic-memory comparator.
- **ReasoningBank** is the procedural-memory and success/failure consolidation
  control; **MemAudit/Antivenom** is the post-harm leave-one-memory-out replay and
  repair control. Neither supplies the prospective population estimand.
- **Reliable Post-Retrieval Assembly** separates evidence extraction from
  final policy execution and reports a LongMemEval null. It requires every
  trial to distinguish retrieval, evidence assembly, and answer-policy failure.
- **PAST-Bench** is the required longitudinal external pathway benchmark. Its
  persistence-on/off sequences test later improvement and intended save,
  retrieve, reuse, and update paths; they evaluate the deployed policy but do
  not replace the randomized item-level estimand.

The exact admissible novelty statement is: under that recorded search, no direct
prior was found combining (i) prospective logged known-propensity assignment of
one retained item at its first eligible service opportunity, (ii) executable
downstream task utility, (iii) an independent paired continuation from the same
pre-service state, and (iv) a cross-fitted service policy restricted to write-time
covariates. Randomized exposure, downstream utility learning, active/archive
movement, graphs, CRUD, consolidation, replay, safety holdouts, and portability
are explicitly outside the novelty claim.

"Holdout ledger" is used here instead of "shadow memory" because MAGE already
uses the latter term for a different mechanism.

## Implemented reference path (updated 2026-08-13)

`harness/causal_memory_trials.py` now implements the Stage-0 causal spine:
content-addressed prefix events and direct feature lineage, deterministic
known-propensity assignment, an `fsync` assignment journal written before
continuation, serve/holdout exposure, same-arm A/A replay, common RNG/tool/
exogenous receipts, immutable raw and analysis manifests, group cross-fitting,
AIPW pseudo-outcomes, and a ridge effect policy. Paired-audit episodes are
excluded from every nuisance and policy fit. Estimator-to-oracle ATE gap,
pseudo-outcome correlation, and policy-to-oracle correlation are separate gates.
The only environment seam is `TrialWorld.prepare/continue_from`.

The executable memory-study path now also has a versioned generated source and
noncausal learned comparator. `memory-events-v3` scopes every entity, value,
graph node, and distractor namespace to one cross-stratum family. The split
compiler binds all task hashes and source provenance, realizes exactly
1,440/480/480 tasks, and rejects any family crossing train/dev/test. The
`learned-next-use` control labels future support records on TRAIN only, selects
its fixed logistic regularizer on DEV only, and freezes an immutable artifact
before TEST. Its serving-time features contain only prefix record age, access,
frequency, length, recency, event-kind, and trust fields. Query text, oracle,
candidate identity, source quality, contradiction annotations, stratum, suffix,
and TEST labels are forbidden.

The v3 source also contains plain, supersession, and delete-then-recreate
histories without changing the randomized candidate treatment. UPDATE
invalidates the previous record in both direct and memory-system materializers,
and invalidated records are excluded from actor-visible frames.

This comparator is intentionally not the proposed causal gate. Its generated
labels are a baseline for falsification, and the generated source still shares
one structural episode template across partitions. A template-family or
out-of-generator claim remains blocked on additional sealed source families.
The complete CPU receipt contains 39,804 TRAIN record rows and 13,241 DEV rows;
it is implementation evidence, not a policy result.

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
estimator-to-oracle plumbing, replay-receipt consistency, feature-lineage
self-consistency, and artifact integrity against a known symbolic treatment
effect. It does **not** yet prove live-environment replay or leakage rejection:
the symbolic suffix-permutation path does not rerun feature extraction from a
new suffix. It also does **not** yet satisfy
the full Stage-0 claim below: the
symbolic adapter is not the specified 20–40-step tool environment, the ridge
models are reference nuisances rather than the registered GBDT/MLP comparison,
and its prefix/replay receipts are still adapter-provided rather than derived by
an engine-owned live environment. A real-model result remains blocked on a
frozen-model `TrialWorld` adapter and the executable tool episode generator.

## Exact estimand

The pilot allows exactly one randomized candidate per episode. Let `S_q` be the
complete agent and environment snapshot immediately before the candidate's first
preregistered retrieval opportunity, `Z_i` indicate serving (`1`) or holdout
(`0`), and `U` be executable episode utility:

```text
tau_pair(S_q) = E[U(Y_i(1)) - U(Y_i(0)) | S_q]
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

The paired audit estimates `tau_pair(S_q)` conditional on the full pre-service
state. The deployed service gate cannot observe that state or a future query.
It learns the coarser projection
`tau_write(x) = E[U(Y(1)) - U(Y(0)) | X_write=x]`, where `X_write` contains only
features available when the retained item was written: source, semantic type,
provenance, contradiction status, current budget, and completed trial history.
Future query text, use time, suffix outcome, branch identity, and oracle deltas
are forbidden inputs. A later write/evict claim is allowed only after writing
or eviction itself is randomized.

## Cheapest decisive methodology

### Stage 0 — symbolic identifiability doctor (CPU, less than two hours)

Generate deterministic 20–40-step tool episodes with facts, corrections,
deletes, high-surprise distractors, near-duplicate keys, and one- to three-hop
future queries. For one retained candidate per episode:

1. hash the prefix and environment state;
2. assign serve/holdout with `p=0.5` from a committed seed;
3. at first eligibility, fork paired continuations from the identical snapshot;
4. assert the two runs differ only in framed memory visibility;
5. compute exact success, tool-error, token, latency, and safety deltas;
6. discard all future fields before fitting the past-only gate.

Run at least 2,000 episodes. The current v2 doctor splits by a cross-stratum
generator family whose identifier and value namespaces are disjoint; it does
not yet hold out structural templates, composition mechanisms, correction
families, or use-delay generators. Those require separately implemented source
families and sealed manifests before any out-of-generator claim.

### Stage 1 — frozen open-model screen (one GPU, at most eight GPU-hours)

Use a pinned 1–4B Hugging Face checkpoint and deterministic tool simulator.
Freeze the language model. Compare a small gradient-boosted/MLP gate before any
LoRA so that a gain cannot be attributed to changing the base model. Memory
budgets are `K={2,4,8}`; `K=4` is primary. Every arm receives identical candidate
records, retrieval calls, metadata bytes, tuning trials, and rollout budget.

The primary endpoint is paired executable success for the learned holdout-trial
gate versus the strongest non-randomized learned control selected on validation
data and frozen before sealed-test evaluation at `K=4`. Require a
point gain of at least three percentage points with a paired 95% interval that
excludes zero. Diagnostic gates are:

- cross-fitted pseudo-outcome Spearman correlation at least `0.20` with the
  sealed paired oracle;
- calibration error and policy value stable across propensities `0.25`, `0.5`,
  and an operational `0.1` holdout rate;
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
external propensity logger, holdout ledger, split manifest, and evaluator remain
unchanged.

This tests whether causal trial targets improve a strong agent memory policy.
It does not claim portable LoRA weights or a new Kimi architecture.

### External-validity ladder (after the generated kill screen)

Run public tasks without training or selecting thresholds on their sealed
evaluation partitions:

1. **PM-Bench** first, because its released deterministic simulator directly
   tests inactive intentions becoming active at time/event cues, proactive
   state monitoring, and deactivation after completion, cancellation, or
   supersession. Preserve native action/F1 scoring and add cost/safety ledgers.
2. **Mem2ActBench** for exact memory-grounded tool name and argument execution.
3. **StreamMemBench** for observation-to-action, feedback incorporation, and
   later reuse, only after separately validating the EgoLife-derived data terms.
4. **EvoMemBench** as the heterogeneity and long-context falsifier across
   in/cross-episode and knowledge/execution settings.

These are external tests, not interchangeable training pools. PM-Bench scores a
complete monitoring scaffold; StreamMemBench introduces multimodal and feedback
simulation factors; EvoMemBench's published fifteen-system ranking is not a
matched CoTCodec result. None identifies the first-service estimand by itself.

## Controls

- FIFO, LRU, LFU, reservoir, and random retention;
- surprise/novelty and semantic-dedup gates;
- learned next-reference or reuse-hazard predictor with the same capacity;
- observational history-utility and reflection/value-backfilling controls;
- Memory-R2 same-state rerollout and VerMem verifier-guided credit;
- paper-faithful reimplementations of Retain-or-Consolidate and AttriMem, plus
  RoMeRL and MemCon/AgeMem controls; neither former paper has official public
  code under the recorded cutoff;
- policy-gradient/GRPO memory controller with the same environment rollouts;
- query-time controlled intervention without longitudinal propensity logging;
- ReFind-style raw-log agentic BM25 and ProGraph graph-free profile traversal;
- Router-Mem shallow/deep routing and ERSkill retrieval-program controls;
- Lychee-style segment consolidation and ScrubJay type-conditioned decay;
- the implemented unmatched full-prefix ceiling, plus a paired leave-one-out
  oracle; the ceiling is charged its actual context and excluded from the
  matched primary comparison;
- a fake holdout label and label-permutation negative control;
- SMSR randomized-ablation majority voting for the poisoning/safety endpoint;
- UnifiedMem matched graph-versus-flat configurations for every graph claim;
- Unified Memory Agent, RecMem, and proactive-memory-agent controls for
  active/inactive residency, consolidation, and pre-action reminder injection.
- PM-Bench native no-ledger, todo-ledger, heartbeat, and hierarchical scaffold
  configurations for prospective activation; these are benchmark controls and
  never candidates for the strongest matched item-retention arm.
- EvoMemBench's long-context floor and method-family grouping as an external
  heterogeneity check, rerun with pinned code rather than copied paper scores.

All controls match state bytes, metadata, read/write calls, model tokens,
environment evidence, search trials, and wall time. Trial-generation cost is
reported both per decision and amortized across downstream episodes.
The in-tree `raw-log-rrf` and `profile-expansion` controls isolate retrieval
mechanisms only; their hash-bound receipts forbid reporting them as complete
ReFind or ProGraph reproductions.
The in-tree `full-prefix-ceiling` emits every ordered raw prefix event as one
attributed, untruncated block. On the pinned LongMemEval-32 panel it requires at
most 20,303 estimated tokens; the registered actor diagnostic must use a
separate 32,768-token budget class and cannot be selected as the strongest
matched control.

## Falsifiers

Reject the direction if any of the following occurs:

- randomized estimates fail to recover the deterministic paired oracle;
- the estimator is unstable across propensities or effective sample size is
  below 400;
- prefix-only predictions have sealed correlation below `0.20`;
- next-use, observational utility, or matched-rollout RL ties the learned gate;
- ReFind-style raw-log search or ProGraph ties a more expensive structured
  memory arm at matched bytes, calls, tokens, and wall time;
- the learned gate fails the three-point task-success threshold;
- multiple-memory interference erases the one-candidate result under the first
  saturation experiment;
- holdout storage, extra rollouts, or latency cost more than the context saved;
- any future field leaks into the policy or holdout content crosses sessions;
- a first-service estimate is required to support a write, retain, or eviction claim.
- a gain disappears on PM-Bench activation/deactivation, Mem2Act executable
  action, or the registered EvoMemBench scope/content stratum that matches the
  claimed deployment setting.

## Safety and data rights

Holdout-ledger memory is still retained data. The ledger must be session-scoped,
encrypted at rest, provenance-labeled, TTL-bound, deletion-capable, and excluded
from prompts unless assigned to serve. It stores framework-visible records, not
hidden chain-of-thought. Prompt injections in candidate memories are framed as
untrusted data. Report safety failure, tool-schema correctness, and refusal
consistency by arm; the project red lines still apply.
Authority must be origin-bound per the TMA-NM control rather than inferred from
ordinary provenance strings. Delayed sleeper-poison activation must be measured
through the write, retrieval, and action chain, and SMSR supplies the certified
randomized-ablation comparison.

## Negative-result value

A null result would show that randomized causal memory effects are too sparse,
too interactive, or too expensive to predict from write-time information. That
would directly constrain future memory-policy papers and favor query-time
retrieval, deterministic eviction, or RL over causal backfilling.

## Queue gate

No GPU job may run until the symbolic paired-replay oracle, propensity logger,
positive prefix-feature contract, exact split hashes, immutable model receipt,
clean retained source archive, SBOM-bearing digest-pinned container, Slurm
manifest, atomic checkpoint, and fresh-job resume test all pass. A denylist is
defense in depth and never substitutes for the positive feature schema.
Public benchmark code and data licenses must be resolved independently; an
open repository or paper link is not authorization to reuse derived data.
