# Research Direction: Causal Memory Holdout Trials

**Status:** draft; narrow novelty delta found; not pilot-ready
**Owner:** Kevin Liu
**Source cutoff:** 2026-08-10
**Coverage limits:** no authenticated global X/Reddit search; FieldTheory covered Kevin-selected bookmarks through 2026-08-02; no citation-index guarantee
**Budgets:** queries=24; wall_minutes=180; tokens=120000; dollars=1; waves=2; gpu_hours=8
**Novelty verdict:** NARROW_DELTA_FOUND_PENDING_SIGNED_REVIEW
**Safety verdict:** FAIL_PENDING_RUNTIME_EVIDENCE
**Evidence bundle:** evidence/causal-memory-holdout-trials/bundle.json

## Claim and Research Question

At a fixed memory budget, can a past-only policy trained from randomized
serving-versus-holdout trials improve executable agent success over recency,
next-use prediction, observational future-utility labels, query-time
interventions, and matched-rollout policy-gradient training?

The candidate contribution is a causal credit-assignment method for memory
decisions. It is not a graph-memory product, a universal sidecar, a new
retriever, or an additive per-item theory of memory value.

## Strategic Fit and Why Now

Memory is an orchestration variable that existing agents optimize with
heuristics, reflections, attention scores, or end-to-end RL. Those signals are
confounded by the policy that generated the trajectory. CoTCodec's deterministic
trace and replay harness can turn memory serving into a randomized intervention
and measure task utility directly.

This also uses the available model ladder honestly. A symbolic and frozen-Qwen
screen can reject the idea cheaply. Tinker can later train a Qwen or Kimi
discrete controller from the causal targets. Portable capsules may implement the
same intervention across harnesses, but are enabling infrastructure rather than
the research claim.

## Primary-Source Evidence

- [Causal Memory Intervention](https://arxiv.org/abs/2605.17641) performs
  controlled query-time memory interventions, establishing intervention-based
  memory attribution but not longitudinal randomized eligibility or a learned
  write-time policy.
- [Xiong et al., ACL 2026](https://aclanthology.org/2026.acl-long.27/) learns
  future-task utility for deletion from observational trajectories.
- [ForesightKV](https://arxiv.org/abs/2602.03203) distills future-attention
  eviction targets; [Learning to Evict/KVP](https://arxiv.org/abs/2602.10238)
  learns future-decoding utility with RL.
- [AgeMem](https://arxiv.org/abs/2601.01885) and
  [MemexRL](https://arxiv.org/abs/2603.04257) jointly optimize memory lifecycle
  actions with RL under context budgets.
- [MSCE](https://arxiv.org/abs/2607.16621) uses reflection-weighted value
  backfilling to govern trace, policy, and skill retention.
- [MAGE](https://arxiv.org/abs/2605.03228) uses “shadow memory” terminology in a
  different setting; this proposal therefore uses the name *causal memory
  holdout trials*.

FieldTheory surfaced MSCE before synthesis. Local `lsearch` resolved the paper
and recent primary collisions. These discovery tools generated candidates; only
the primary sources above support the ledger.

## Closest Prior Work

The closest cluster already covers future-aware eviction, observational utility,
query-time interventions, and RL memory policies. The remaining gap is not
“predict which memory will matter.” It is using known-propensity serving
assignments to estimate downstream executable-task effects, auditing those
estimates against paired deterministic replay, then training a strictly
past-only policy from cross-fitted causal targets.

Randomization does not solve interacting memories automatically. The pilot
therefore intervenes on exactly one eligible item per episode. Multi-item value
requires a later saturation design and is outside the first claim.

## Novelty Ledger

| Proposed component | Closest prior | Same | Delta | Confidence |
|---|---|---|---|---:|
| Known-propensity memory eligibility | CMI | Query-time intervention | Randomized serving trajectory with logged propensity | 0.65 |
| Downstream memory-value target | Xiong, ForesightKV, KVP | Future utility signal | Executable task utility under randomized treatment | 0.65 |
| Past-only learned memory policy | AgeMem, MemexRL, MSCE | Learned memory control | Cross-fitted causal pseudo-outcomes with feature-time audit | 0.60 |
| Paired replay audit | CMI and leave-one-out evaluation | Counterfactual comparison | Validates single-arm estimator from the identical pre-retrieval snapshot | 0.70 |
| Multi-item causal value | None claimed | Memory items interact | Explicitly out of scope until saturation trial | 0.95 |

Novelty wording: No direct prior art found through 2026-08-10 under the stated
FieldTheory, local-search, arXiv, ACL, and primary-lab coverage that combines
randomized longitudinal
memory eligibility, propensity-based downstream agent-task estimation, paired
replay audit, and a learned past-only policy was found through 2026-08-10 under
the stated coverage. This is not a global-priority or global-novelty claim.

## Mechanism and Falsifiable Predictions

For one eligible candidate item `i`, snapshot the full agent/environment state
`S_q` immediately before its first preregistered retrieval opportunity. Commit
`Z_i ~ Bernoulli(p)` before model inference: serving when `Z_i=1`, non-serving
holdout when `Z_i=0`. The estimand is:

```text
tau_i(S_q) = E[U(Y_i(1)) - U(Y_i(0)) | S_q]
```

On a replayable audit subset, restore the same hashed `S_q` and run the opposite
treatment with common RNG and deterministic tool responses. Separately conceal
one branch and recover effects from the single-arm stream with cross-fitted
augmented inverse propensity weighting. Only after that estimator matches the
paired oracle may its pseudo-outcomes train a policy.

Prediction 1: pseudo-outcome rankings correlate at least `0.20` with sealed
paired effects. Prediction 2: the learned gate raises executable success by at
least three points over the strongest non-randomized learned control at memory
budget `K=4`. Prediction 3: estimates and policy value remain stable at
propensities `0.25`, `0.5`, and operational `0.1` after overlap diagnostics.

**Falsifier.** Kill the claim if the randomized estimator fails to recover the
paired oracle, if sealed rank correlation is below `0.20`, or if the learned
policy fails to beat the strongest matched control by three success points.

The gate sees only write-time provenance, semantic type, contradiction status,
current occupancy/cost, and causal prefix features. Future queries, use times,
suffix outcomes, assignment identity, and oracle effects are denied by schema
and audited feature lineage.

## Cheapest Decisive Pilot

First run a CPU symbolic doctor on 2,000 deterministic 20–40-step episodes with
facts, corrections, deletes, high-surprise distractors, near-duplicate keys, and
one- to three-hop queries. Freeze generator-family, namespace, composition,
correction, and delay splits. Require byte-identical snapshots and paired runs
that differ only in framed memory visibility.

Then freeze pinned `Qwen/Qwen3-0.6B-Base` for a one-GPU screen. Train only a
small gradient-boosted or MLP conditional-effect head. `K={2,4,8}` with `K=4`
primary. Three seeds are a kill screen; five seeds are used only after passing.
The detailed executable contract is
`experiments/architectures/causal-memory-holdout.yaml`.

After the frozen-model result passes, Tinker may train a discrete controller or
model-specific LoRA on `Qwen/Qwen3.5-4B`, followed by a separately trained
`moonshotai/Kimi-K2.6` confirmation cell. The external assignment, ledger,
estimator, splits, budgets, and evaluator remain frozen. Tinker does not test a
new attention or recurrent-state kernel, and no LoRA weight portability is
claimed.

## Controls, Baselines, and Ablations

- FIFO, LRU, LFU, reservoir, and random retention;
- surprise/novelty and semantic deduplication;
- learned next-reference/reuse hazard with identical capacity and tuning;
- observational history utility and reflection/value backfilling;
- matched-rollout policy-gradient/GRPO controller;
- CMI-style query-time intervention without longitudinal propensity logging;
- paired leave-one-out oracle and unlimited-memory ceiling;
- label permutation, fake assignment, forbidden-feature, and suffix-permutation
  negative controls.

Every arm matches candidate records, memory and metadata bytes, retrieval calls,
model tokens, environment evidence, search trials, and wall-time accounting.
Report trial-generation cost before and after amortization.

## Evaluation, Statistics, and Leakage Checks

Primary endpoint: paired executable episode-success difference between the
causal gate and strongest non-randomized learned control at `K=4`, minimum three
points, 95% paired family-stratified bootstrap interval excluding zero.

Diagnostics: paired-oracle rank correlation, calibration, effective sample size,
overlap, policy-value stability by propensity, memory-budget frontier, tokens,
latency, safety, and per-family effect heterogeneity. Episodes clustered within
generator family are the unit; individual memory decisions are not independent.
Use randomization inference and report every seed. Holm-correct secondary policy
and budget cells.

Leakage tests hash every prefix, enforce a typed allowed-feature projection,
permute suffixes while holding prefixes fixed, split generator and ontology
families, commit treatment before inference, and replay successes and failures.
The first multi-item extension must use randomized saturation to measure
interference rather than summing item effects.

## Compute and Reproducibility

`seeds: [42, 43, 44]`
`gpu_hours: 8` maximum for the frozen-model screen
`immutable image: MISSING — Compute doctor FAIL`
`sbatch command: MISSING — Slurm/Pyxis is not installed on the audited host`

The queue contract requires a clean committed source archive, digest-pinned OCI
image, verified embedded provenance, one measured 100-episode timing cell,
atomic checkpoints every ten minutes to persistent storage, `USR1` checkpoint
handling, two validated generations, and a fresh-job continuation equivalence
test. `tmux` is only the login-host operator session; scheduler-owned `sbatch`
jobs and persistent checkpoints provide durability.

Publication runs pin model revision, tokenizer, generation config, task generator,
split hashes, container digest, source hash, CUDA/kernel versions, and every
assignment/outcome record. Ollama tags are smoke-only. The first Tinker run is
the Qwen interface cell; Kimi is forbidden until its data, cost, checkpoint,
and resume receipts pass.

## Safety, Data Rights, and Monitorability

Holdout memory is retained data even when it is not served. Encrypt it, isolate
it by session/user, attach provenance and TTL, support deletion, and never expose
it without treatment assignment. Store framework-visible records only, not
hidden chain-of-thought. Frame memory and tool content as untrusted data.

Collect refusal consistency, prompt-injection resistance, schema fidelity,
semantic fidelity, and cross-session leakage. Stop on the project red lines:
more than 5% safety regression, more than 10% tool-argument degradation, any
language-mixing injection bypass, or any session bleed.

## Negative-Result Value

A clean null shows that causal memory effects are too sparse, interactive,
expensive, or unpredictable from write-time information. That would favor
query-time retrieval, deterministic eviction, or end-to-end RL and would
invalidate a broad class of value-backfilling claims. Estimator failure despite
paired replay would expose an overlap or interference problem rather than being
reported as a model failure.

## Preflight Doctors

| Doctor | Status | Evidence | Remediation |
|---|---|---|---|
| Source | PASS | Primary CMI, Xiong, ForesightKV, KVP, AgeMem, MemexRL, MSCE sources resolved | Archive query/source artifacts in the evidence bundle |
| Citation | PASS | Mechanism claims linked to primary papers | Independent line-by-line citation audit |
| Novelty | FAIL | Narrow delta found, but no signed provider-distinct novelty review | Run protected external reviews after proposal freeze |
| Design | PASS | One-item estimand, paired oracle, controls, leakage tests, falsifiers, registered YAML | Implement symbolic doctor and audit output |
| Compute | FAIL | No real agent loop, digest-pinned image, Slurm/Pyxis run, or resume receipt | Build and attest the frozen-Qwen cell before queueing |
| Safety | FAIL | Protocol specified; no runtime isolation or poisoning evidence | Pass synthetic and real-model safety suites |

## Independent Adversarial Reviews

Reviewer A: FAIL | provider=missing | model=missing | run_id=missing | artifact=missing

Reviewer B: FAIL | provider=missing | model=missing | run_id=missing | artifact=missing

Local subagents performed discovery and kill review, but they are not accepted
as the provider-distinct, signed, pre-trusted reviews required by the Gauntlet.

## Scorecard

| Dimension | Reviewer A | Reviewer B | Defect/evidence |
|---|---:|---:|---|
| Question and strategic fit | 0 | 0 | Signed reviews absent |
| Primary-source evidence | 0 | 0 | Signed reviews absent |
| Defensible novelty delta | 0 | 0 | Signed reviews absent |
| Mechanism and falsifiability | 0 | 0 | Signed reviews absent |
| Controls and causal identification | 0 | 0 | Signed reviews absent |
| Evaluation and statistics | 0 | 0 | Signed reviews absent |
| Feasibility and information per GPU-hour | 0 | 0 | Compute evidence absent |
| Reproducibility and artifact contract | 0 | 0 | Evidence bundle absent |
| Safety, data rights, and monitorability | 0 | 0 | Runtime evidence absent |
| Independent adversarial review quality | 0 | 0 | Both required reviews absent |
| **Total** | **0** | **0** | **Accepted Gauntlet score: 0; scientific draft is not pilot-ready** |

## Iteration Log

| Wave | Score | Highest-impact defect | Change | Result |
|---:|---:|---|---|---|
| 1 | 0 | Portable capsule was being mistaken for the research contribution | Demoted capsules/Tinker to infrastructure and generated mechanism candidates | Broad sidecar claim rejected |
| 2 | 0 | Future-use, transactional state, operator routing, and coded memory had direct collisions or fatal confounds | Killed those broad claims; narrowed to randomized causal memory eligibility with one-item estimand | Candidate survives discovery, not Gauntlet |

The accepted score remains zero until the hashed evidence bundle, protected
trust root, signed independent reviews, real-model container receipt, Slurm dry
run, safety output, and final audit chain exist. A prose proposal cannot score
itself upward.
