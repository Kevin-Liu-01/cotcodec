# Archived Direction Audit: Portable Orchestration Capsules

**Status:** rejected as a research direction; retained as enabling infrastructure
**Owner:** Kevin Liu
**Source cutoff:** 2026-08-10
**Coverage limits:** live X/Reddit unavailable; Exa free quota exhausted; no exhaustive patent search
**Budgets:** queries=40; wall_minutes=240; tokens=80000; dollars=20; waves=3; gpu_hours=8
**Novelty verdict:** REJECT
**Safety verdict:** FAIL
**Evidence bundle:** evidence/portable-orchestration-capsules/bundle.json

## Claim and Research Question

Do fixed, stateful orchestration capsules preserve decision semantics and
task-level utility when compiled into heterogeneous agent harness hook systems,
and can declared host capabilities predict where transfer fails?

The proposal does not claim a new agent protocol, middleware abstraction,
memory graph, harness optimizer, or universal compatibility. Its surviving
conformance work lives at
`research/infrastructure/portable-orchestration-capsules.md`; it must not be
presented as Direction 17 or as the scientific contribution.

## Strategic Fit and Why Now

CoTCodec studies orchestration choices as explicit variables. Capsules make one
choice implementation portable enough to vary harness, model, task, and capsule
factorially rather than confounding them. The current ecosystem is converging on
events, middleware, harness adapters, portable skills, and portable memory, but
semantic portability is usually asserted from API compatibility rather than
measured under replay and live enforcement.

## Primary-Source Evidence

- [AgentHarnessProtocol 2.4](https://github.com/A3S-Lab/AgentHarnessProtocol)
  typed event/decision specification.
- [Agent Control Specification](https://github.com/responsibleai/AgentControlSpecification)
  and Microsoft agent-governance policy runtime.
- [HarnessX v3](https://arxiv.org/abs/2606.14249) typed processors and AEGIS.
- [Natural-Language Agent Harnesses](https://arxiv.org/abs/2603.25723) and IHR.
- [Life-Harness](https://arxiv.org/abs/2605.22166) interface interventions.
- [Agent Lightning](https://arxiv.org/abs/2508.03680) unified training traces.
- [Portable Agent Memory](https://arxiv.org/abs/2605.11032) protocol.
- [Vercel HarnessAgent](https://github.com/vercel/ai/tree/main/packages/harness)
  adapter architecture.
- [SkillOpt](https://arxiv.org/abs/2605.23904) portable optimized skills.
- [OpenTelemetry semantic conventions](https://github.com/open-telemetry/semantic-conventions)
  and [OpenInference](https://github.com/Arize-ai/openinference) instrumentation.

FieldTheory bookmark discovery highlighted memory/compaction coupling, portable
memory demand, Vercel harness portability, and cross-agent SkillOpt transfer.
Bookmarks are hypothesis signals, not validation.

## Closest Prior Work

The broad idea is directly occupied. AHP already provides cross-runtime policy
events and typed memory/context/planning decisions. ACS covers portable
enforcement and transforms. HarnessX provides typed, composable processors and
harness evolution. NLAH/IHR externalizes executable harness policy. Portable
Agent Memory moves graph/provenance-backed memory across agents. Vercel
HarnessAgent normalizes established agent products.

## Novelty Ledger

| Proposed component | Closest prior | Same | Delta | Confidence |
|---|---|---|---|---:|
| Canonical lifecycle events | AHP, OTel, HarnessX | Yes | None; reuse/profile existing semantics | 0.98 |
| Capability negotiation | AHP, Vercel adapters | Yes | Per-effect fail-closed compile check | 0.35 |
| Portable memory graph | Portable Agent Memory, Graphiti, Mem0 | Mostly | Policy decision parity, not graph format | 0.30 |
| Typed capsule composition | HarnessX | Yes | Foreign-runtime compilation and parity | 0.45 |
| Harness-independent policy | NLAH/IHR, Life-Harness, SkillOpt | Partly | Fixed capsule across different hook runtimes | 0.45 |
| Portability evaluation | Harness variance work | Partly | Replay parity + retained-lift capability matrix | 0.60 |

Novelty wording: No direct prior art found through 2026-08-10 for the exact
combination of fail-closed capability compilation, cross-adapter event/action
replay parity, and paired retained-lift measurement for fixed stateful
orchestration policies. This is not yet sufficient for promotion.

## Mechanism and Falsifiable Predictions

A capsule maps canonical framework-visible lifecycle events and namespaced
state to bounded effects. A task-blind adapter normalizes native events and
enforces effects. Compilation rejects missing hooks/effects. Prediction: on
advertised common capabilities, fixed capsules achieve ≥99% replay decision
parity and retain most of the matched native module's task lift. Prediction:
capability loss and capsule×host interaction, not wrapper syntax, explain
transfer failures.

**Falsifier.** Reject the claim if adapters need task/capsule-specific logic,
advertised safety-critical decisions differ under replay, portable capsules
retain less than half the matched native lift, prompt-only skills transfer as
well, capability manifests do not predict failure, or p95 overhead exceeds 10%.

## Cheapest Decisive Pilot

CPU-only deterministic replay across CoTCodec, AHP, LangChain, and one of OpenAI
Agents SDK/AG2/Vercel, using memory-graph and verify-before-final capsules. Then
shadow mode, then paired live enforcement on one deterministic canary and one
non-stub tool benchmark.

## Controls, Baselines, and Ablations

No capsule, telemetry only, no-op serialization, native host module,
prompt/skill-only equivalent, common state backend without policy, provenance
and session-reset ablations, deliberate missing-hook manifests, and an invalid
task-aware adapter oracle.

## Evaluation, Statistics, and Leakage Checks

Primary conformance endpoint is ≥99% canonical action parity and 100% agreement
for safety-critical effects. Primary live outcome is raw paired utility change;
retained lift versus native is secondary when the native denominator is stable.
Use identical tasks and seeds, paired bootstrap intervals, and a mixed-effects
model over capsule, host, model, task family, and capsule×host interaction.
Adapters see conformance fixtures/anchor tasks only, freeze before sealed target
evaluation, and must contain no benchmark-specific logic.

## Compute and Reproducibility

Compute doctor is FAIL. The deterministic prototype is CPU-only, while a live
pilot requires the still-missing real agent loop, non-stub benchmark, protected
CI, and Slurm/Pyxis path. No immutable publication image or valid sbatch receipt
exists for this proposal. Planned seeds: [42, 43, 44]. gpu_hours: 8.

Every run will store capsule, adapter, capability, event, action, enforcement,
state, trace, model, benchmark, image, source, seed, and checkpoint hashes. Long
runs use persistent atomic checkpoints and a fresh-job continuation test.

## Safety, Data Rights, and Monitorability

Hidden chain-of-thought is out of scope. Tool/memory content stays untrusted
data. Safety-critical enforcement fails closed. State requires complete
tenant/user/workspace/session ownership. Persistent deployment additionally
requires signed capsules, resource and egress ceilings, retention/deletion
policy, prompt-injection tests, and cross-session bleed tests. Safety remains
FAIL until live adapter enforcement and attack tests exist.

## Negative-Result Value

Failure quantifies which orchestration choices are intrinsically coupled to
harness lifecycle semantics and produces a reusable capability matrix,
conformance corpus, and warning against universal-wrapper claims.

## Preflight Doctors

| Doctor | Status | Evidence | Remediation |
|---|---|---|---|
| Source | FAIL | Exa quota exhausted; live X/Reddit unavailable | Complete academic and implementation audit |
| Citation | FAIL | Primary sources manually inspected; no hashed bundle | Build source/query artifacts |
| Novelty | FAIL | Broad claim directly collides with AHP/ACS/HarnessX/NLAH | Audit exact portability-evaluation delta |
| Design | PASS | Direction 17 and eight prototype conformance tests | Add four live adapters and frozen corpus |
| Compute | FAIL | Agent loop, benchmark, protected CI, Slurm/Pyxis unavailable | Resolve existing project blockers |
| Safety | FAIL | Schema framing and isolation tests only | Run live fail-closed and injection suite |

## Independent Adversarial Reviews

Reviewer A: FAIL | provider=unassigned | model=unassigned | run_id=none | artifact=none

Reviewer B: FAIL | provider=unassigned | model=unassigned | run_id=none | artifact=none

## Scorecard

| Dimension | Reviewer A | Reviewer B | Defect/evidence |
|---|---:|---:|---|
| Question and strategic fit | 0 | 0 | No independent review |
| Primary-source evidence | 0 | 0 | Sources not snapshotted or hashed |
| Defensible novelty delta | 0 | 0 | Broad idea directly occupied |
| Mechanism and falsifiability | 0 | 0 | Only synthetic manifests run |
| Controls and causal identification | 0 | 0 | Live native controls absent |
| Evaluation and statistics | 0 | 0 | Sealed corpus not built |
| Feasibility and information per GPU-hour | 0 | 0 | Real loop and adapters absent |
| Reproducibility and artifact contract | 0 | 0 | Evidence bundle absent |
| Safety, data rights, and monitorability | 0 | 0 | Live enforcement untested |
| Independent adversarial review quality | 0 | 0 | Reviewers unassigned |
| **Total** | **0** | **0** | Lower total is authoritative |

No score is claimed before independent review and the evidence bundle. The
proposal is capped below 75 by incomplete novelty coverage and below 80 by the
missing executable live pilot.

## Iteration Log

| Wave | Score | Highest-impact defect | Change | Result |
|---:|---:|---|---|---|
| 0 | 0 | “Universal sidecar protocol” already exists | Reframed around semantic portability measurement | Prototype only; promotion rejected |
