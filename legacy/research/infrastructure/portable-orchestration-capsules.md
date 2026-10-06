# Research Infrastructure: Portable Orchestration Capsules

**Status:** prototype enabling infrastructure; not a research direction
**Priority:** conformance pilot after the executable agent loop
**Reference implementation:** `harness/capsules/`
**Archived direction audit:** `research/proposals/2026-08-10-portable-orchestration-capsules.md`

## The useful infrastructure

Strap memory, verification, retry, compaction, routing, safety, or checkpoint
logic onto an agent without rewriting that logic for every harness.

The initial intuition is right as an engineering direction but not as a broad
novelty claim. AgentHarnessProtocol already separates runtime events from
policy decisions. Agent Control Specification does portable guardrail
interventions. HarnessX has typed substitutable processors. Natural-Language
Agent Harnesses externalize executable harness policy. Vercel HarnessAgent
normalizes multiple established harnesses. Agent Lightning decouples agent
execution from training. Portable Agent Memory transfers memory itself.

The defensible research question is narrower:

> Which orchestration behaviors can be transferred across heterogeneous agent
> hook systems without semantic drift, what host capabilities are necessary,
> and when is a native harness implementation still required?

The artifact is a **capsule**: versioned event-to-action policy plus state
schema, capability requirements, budgets, tests, and provenance. It is a
research object for measuring orchestration portability, not another universal
agent protocol.

## Scope: conformant hosts, not “all agents”

No sidecar can control a lifecycle point a host does not expose. A telemetry-only
framework cannot enforce a pre-tool block. A harness without a pre-final hook
cannot guarantee verify-before-submit. Provider-private compaction state cannot
be recovered from a public transcript.

Portability therefore means:

1. the host adapter advertises hooks and effects in a capability manifest;
2. the capsule declares every required hook, effect, state boundary, and budget;
3. compilation refuses any missing semantic requirement;
4. canonical replay yields the same normalized actions across adapters;
5. live enforcement produces a retained task-level effect under matched inputs.

Silent degradation from enforcement to observation is a failure, not partial
support.

## Minimal contract

The reference ABI exposes only framework-visible lifecycle events:

```text
session_start
before_model -> after_model
before_tool  -> after_tool
before_final
session_end
```

Capsules may request only bounded effects:

```text
annotate | inject_context | emit_memory_delta | rewrite_tool_args
request_verification | retry | block | checkpoint
```

For harness `h`, native trace `x`, adapter `A_h`, capsule state `s_t`, capsule
`C`, and native effect compiler `B_h`:

```text
e_t       = A_h(x_t)
(s_t+1,a) = C(s_t,e_t)
native_a  = B_h(a)
```

`A_h` and `B_h` are task-blind. An adapter may normalize field names and call
native hooks; it may not encode benchmark answers, recovery procedures, memory
ranking, or capsule-specific task semantics.

The current Python prototype includes:

- immutable event, capability, capsule, action, and dispatch schemas;
- strict capability compilation;
- event idempotency and ordered per-session delivery;
- conflict rejection for exclusive effects with staged-state rollback;
- a session-scoped provenance memory graph;
- verify-before-final enforcement;
- replay parity, isolation, injection-framing, and conflict tests.

It does not yet implement AHP, LangChain, OpenAI Agents SDK, AG2, or Vercel
adapters. Passing unit tests is not evidence of live portability.

## Capsule 1: provenance memory graph

The initial memory capsule observes `after_tool`, appends a content-addressed
node with parent and source provenance, then performs bounded recall at
`before_model`. Recalled tool content is labeled `untrusted-data` with
`instruction_authority: none`; the host must quote/frame it as data rather than
instructions. State is namespace-isolated by session and deleted at
`session_end` in the prototype.

This deliberately does not claim a new memory architecture. Graphiti, Mem0,
Letta, Portable Agent Memory, and other systems cover sophisticated graph,
temporal, editable, and transferable memory. The capsule tests whether one
memory policy can preserve its decisions and value across harness boundaries.

The FieldTheory bookmark scan adds an important negative prior: memory and
compaction are often inseparable because the harness owns the information-loss
boundary. It also highlights dual-memory conflicts, proactive injection cost,
forgetting, and cross-agent portability. Those become explicit stress tests.

## Capsule 2: verify before final

At `before_final`, the capsule requires structured passed verification evidence
with a check identifier and artifact hash. Without it, the capsule requests
verification and blocks finalization. This capsule immediately exposes a real
portability boundary: hosts that expose only model/tool callbacks but no
pre-final enforcement hook must be declared incompatible.

## Tinker cell: train the model to speak to the capsule

Tinker provides a useful but distinct intervention. It can LoRA-finetune Qwen
and Kimi while the capsule remains external and unchanged. It cannot establish
that LoRA weights themselves transfer across architectures, and its managed API
does not expose arbitrary graph-memory or sequence-operator surgery.

The registered contract is
`experiments/tinker/capsule-policy-kimi.yaml`. It first runs a cheap
`Qwen/Qwen3.5-4B` interface smoke, then a `moonshotai/Kimi-K2.6` target cell.
Each base gets a separate rank-16 LoRA trained on the same frozen capsule
event/action protocol. The paired arms are base, prompt-only, capsule-only,
LoRA-only, capsule-aware LoRA, and a matched native-host policy. The primary
endpoint is executable episode success for capsule-aware LoRA versus capsule
only; 100% agreement on block, verification, and session-isolation decisions
is a hard gate.

This tests whether post-training makes models better *clients* of a portable
policy. It does not change the portability claim: only the external capsule and
its conformance behavior cross model and harness boundaries.

## Closest prior work and remaining delta

| Prior work | Already establishes | What remains measurable here |
|---|---|---|
| [AgentHarnessProtocol](https://github.com/A3S-Lab/AgentHarnessProtocol) | Cross-runtime typed events and policy decisions, including memory/context/planning | Cross-adapter decision parity and task-effect retention for fixed policy capsules |
| [Agent Control Specification](https://github.com/responsibleai/AgentControlSpecification) | Portable guardrail intervention, transforms, enforcement adapters | Non-guardrail orchestration policies and empirical capability-loss mapping |
| [HarnessX](https://arxiv.org/abs/2606.14249) | Typed processors, substitution algebra, trace-driven harness evolution | Transfer of the *same fixed processor behavior* across foreign runtimes |
| [Natural-Language Agent Harnesses](https://arxiv.org/abs/2603.25723) | External executable harness policies under one shared runtime | Deterministic cross-runtime semantic conformance rather than one interpreter |
| [Life-Harness](https://arxiv.org/abs/2605.22166) | Structured interface interventions transferred across model backbones | Transfer across harness implementations while model/task are factorial controls |
| [Agent Lightning](https://arxiv.org/abs/2508.03680) | Framework-agnostic traces for agent RL/optimization | Portable inference-time orchestration effects, not model training |
| [Portable Agent Memory](https://arxiv.org/abs/2605.11032) | Provenance-verified memory transfer across agents | Portability of the read/write/injection *policy* and its live effect |
| [Vercel HarnessAgent](https://github.com/vercel/ai/tree/main/packages/harness) | Uniform application-facing API for multiple harnesses | Behavioral middleware portability inside heterogeneous lifecycles |
| [SkillOpt](https://arxiv.org/abs/2605.23904) | Optimized textual skills can transfer between agent products | Typed stateful/enforcing capsules versus prompt/skill artifacts |
| OpenTelemetry/OpenInference | Cross-framework observation and trace semantics | Enforceable actions and equivalence, not observability alone |

No claim of a new protocol, middleware abstraction, graph memory, or harness
optimizer survives this audit. The candidate delta is a controlled portability
study plus fail-closed semantic conformance suite. That delta remains pending a
full literature audit.

## Cheapest decisive pilot

### Phase 0 — deterministic conformance, CPU only

Implement adapters for:

1. CoTCodec's native Python loop;
2. AgentHarnessProtocol;
3. LangChain v1 middleware;
4. one structurally different host: OpenAI Agents SDK, AG2, or Vercel AI SDK.

Each adapter must pass the same frozen trace corpus containing normal calls,
tool errors, prompt injection in tool output, duplicate delivery, reordering,
compaction, cancellation, retry, and finalization. Compare normalized actions
byte-for-byte after canonical JSON serialization. Unsupported cells must fail
compilation before execution.

Primary conformance endpoint: at least 99% decision/action parity over events
whose required capabilities are advertised, with 100% agreement for `block`,
tool-argument rewrites, session boundaries, and verification gates.

### Phase 1 — shadow mode

Run capsules in evaluation-only shadow mode beside native host modules. The
sidecar observes exactly the same events but does not affect execution. Compare:

- intervention opportunity recall;
- decision agreement;
- adapter information loss;
- policy latency p50/p95/p99;
- state namespace and reset behavior.

Freeze adapters after shadow conformance. Adapter authors may see conformance
fixtures and anchor tasks but not sealed target outcomes.

### Phase 2 — paired live enforcement

Use one deterministic canary suite and one real tool benchmark after both are
non-stub. Cross at least two models, four hosts, two capsules, three seeds, and
the same task IDs. Each task is paired under:

1. no capsule;
2. telemetry-only capsule;
3. portable capsule;
4. native host implementation of the same behavior;
5. prompt/skill-only equivalent where expressible.

For host `h` and capsule `c`, define retained lift against the native module:

```text
R(c,h) = [U(portable c,h) - U(no capsule,h)]
         / [U(native c,h) - U(no capsule,h)]
```

Report the ratio only when the native denominator is positive and stable;
always report raw paired differences. The provisional success screen is median
retained lift ≥0.8 across compatible hosts, no host below 0.5, ≥99% replay
parity, and ≤10% p95 latency overhead. These are pilot thresholds, not proof of
universal portability.

Use paired task bootstrap intervals and a mixed-effects model with fixed capsule,
host, model, and task-family effects plus capsule×host interaction. The primary
scientific result is the interaction and capability-loss map, not only aggregate
success.

## Controls and ablations

- native host implementation of identical behavior;
- telemetry-only observer to separate measurement from enforcement;
- no-op adapter with identical serialization overhead;
- prompt/skill-only version;
- common memory backend without portable retrieval/injection policy;
- event normalization without the capsule;
- no provenance, no session reset, and no injection framing ablations;
- capability manifest with one hook deliberately removed;
- adapter written with target-task access as an explicitly invalid oracle.

## Falsifiers

Reject the portable-behavior claim if any of the following holds:

- adapters require capsule- or benchmark-specific logic rather than task-blind
  field and effect mappings;
- replay parity falls below 99% on advertised capabilities or any safety-critical
  block differs;
- native modules consistently beat the capsule after matching state, evidence,
  model calls, and latency;
- a prompt/skill artifact transfers just as well without the new runtime;
- host capability declarations fail to predict transfer failure;
- serialization/IPC adds more than 10% p95 latency or materially increases cost;
- state crosses users/sessions, memory injection changes instruction authority,
  or fail-open behavior bypasses verification.

## Safety and monitorability

- Never capture hidden chain-of-thought. Only framework-visible messages,
  lifecycle metadata, tool calls/results, and declared state are permitted.
- Tool and recalled memory content remains untrusted data with provenance.
- Every enforcement action records capsule/version, input event hash, output
  action hash, host capability manifest, and final enforcement receipt.
- State keys are tenant, user, workspace, and session scoped; incomplete owner
  tuples disable persistent writes.
- Safety-critical capsules fail closed. Non-critical enrichment may fail open
  only when the manifest declares that behavior.
- Capsule signatures, resource ceilings, egress scopes, deletion/export, and
  data-retention policies are required before deployment outside benchmarks.

## Negative-result value

A clean failure is useful. It would establish that orchestration policy is tied
to lifecycle semantics rather than portable syntax, quantify which hooks cause
the coupling, and prevent “works with every agent” claims based only on wrappers
or telemetry. The resulting capability matrix and conformance corpus would
still be a valuable evaluation artifact for AHP, ACS, Vercel, and framework
middleware authors.
