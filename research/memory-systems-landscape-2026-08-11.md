# Agent Memory Systems Landscape — 2026-08-11

## Decision

Do not build another opaque “memory layer.” The open-source field already has
strong implementations of core/archive paging, temporal graphs, profiles,
reflection, and learned CRUD. Build an instrumented memory-transition harness
that can compare these mechanisms under one frozen agent, budget, task stream,
and safety contract.

The first scientific question is not “which database wins?” It is:

> When should a specific memory be written, activated, retrieved, injected,
> updated, consolidated, expired, or forgotten, and how do we identify the
> downstream value of that transition without future leakage?

The authoritative machine-readable inventory is `research/memory-sources.yaml`.
Run `uv run python scripts/validate_memory_sources.py` before using it.

## Terminology

- **Active/core:** visible to the agent now; small and expensive in tokens.
- **Inactive/archive:** retained outside the prompt; cheap to store, risky to miss.
- **Episodic:** events and outcomes with time and provenance.
- **Semantic/profile:** consolidated facts, preferences, entities, and relations.
- **Temporal graph:** facts and relations with validity and transaction time.
- **Procedural:** reusable skills, policies, or workflows distilled from experience.
- **Latent:** KV, recurrent, or fast-weight state internal to a model.
- **Controller:** the policy deciding memory transitions and exposure.

Residency, content, substrate, controller, topology, and trust are independent
axes. A graph can be inactive, a profile can be active, and a procedural memory
can be private or shared.

## Open-source systems worth reproducing

| System | Main mechanism | Active/inactive behavior | Why include | Caveat |
| --- | --- | --- | --- | --- |
| [Letta/MemGPT](https://github.com/letta-ai/letta) | Agent-managed virtual context | Small editable core plus recall/archive tools | Canonical paging and self-management baseline | Full agent runtime; memory calls consume model budget |
| [Graphiti](https://github.com/getzep/graphiti) | Incremental temporal KG | Graph stays inactive until hybrid search/render | Best temporal validity and provenance control | DB, extraction model, embeddings, and graph construction cost |
| [Hindsight](https://github.com/vectorize-io/hindsight) | Retain, recall, reflect | Facts/episodes/mental models live in banks and are recalled or reflected | Broad graph-plus-profile system with public benchmark code | First-party results need matched independent reruns |
| [Mem0](https://github.com/mem0ai/mem0) | Extract/update/delete facts and profiles | Compact selected memories injected into prompt | Low-burden production-style baseline | Managed and OSS algorithms/results are not interchangeable |
| [LangMem](https://github.com/langchain-ai/langmem) | Hot-path tools plus background consolidation | Agent can write now; manager can consolidate later | Transparent policy-library control | LangGraph is an execution graph, not a temporal KG |
| [Cognee](https://github.com/topoteretes/cognee) | Graph plus vector representations and consolidation | Session and durable stores with recall/forget operations | Rich secondary graph/vector system | Many backend and extraction choices must be frozen |
| [Supermemory](https://github.com/supermemoryai/supermemory) | Dynamic/static profiles, contradiction, expiry, forgetting | Profiles can be automatically retrieved and updated | Useful forgetting/profile arm | Cloud/local parity and benchmark configuration need proof |
| [MemOS](https://github.com/MemTensor/MemOS) | Text/tool/persona/multimodal memory and skills | Scheduler and feedback can update memory in background | Broad exploratory system | High integration burden and first-party evidence |
| [A-MEM](https://github.com/WujiangXu/A-mem) | Zettelkasten-style note evolution and links | Incoming notes actively reorganize neighbors | Mechanism ablation for evolving graph organization | Research prototype, weak operational controls |
| [HippoRAG](https://github.com/OSU-NLP-Group/HippoRAG) | OpenIE graph plus personalized PageRank | Static index retrieved on demand | Strong graph-retrieval control | Not an online memory controller |
| [GraphRAG](https://github.com/microsoft/graphrag) | Entity/community graph over a corpus | Batch index queried on demand | Static graph summarization control | Expensive and not conversational CRUD |

Mandatory simple controls remain no memory, full transcript, sliding window,
FIFO/LRU/LFU/random, BM25 top-k, dense top-k, hybrid top-k, and hierarchical
summary. A complicated system must beat the strongest simple control at equal
tokens, bytes, calls, latency, and tuning budget.

## Learned-controller work that occupies obvious ideas

- [AgeMem](https://arxiv.org/abs/2601.01885) learns store, retrieve, update,
  summarize, and discard actions.
- [MemexRL](https://arxiv.org/abs/2603.04257) keeps summaries and stable indices
  active while storing full experiences externally, then learns archive/index/
  dereference decisions.
- [Memory-R1](https://aclanthology.org/2026.acl-long.583/) uses RL for memory
  ADD/UPDATE/DELETE/NOOP and answer-side selection.
- [MemRL](https://arxiv.org/abs/2601.03192) learns feedback-based Q-values for
  episodic retrieval with a frozen base model.
- [PRIME](https://arxiv.org/abs/2604.07645) and
  [Remember When It Matters](https://arxiv.org/abs/2607.08716) study proactive
  memory injection.
- [ForesightKV](https://arxiv.org/abs/2602.03203) and
  [Learning to Evict](https://arxiv.org/abs/2602.10238) learn latent-cache
  eviction using future-derived utility targets.
- [Causal Memory Intervention](https://arxiv.org/abs/2605.17641) performs
  query-time inclusion/exclusion interventions over candidate memories.

Consequently, “learn a memory policy,” “predict future use,” “proactively inject
memories,” and “estimate which retrieved item helped” are not novel on their own.

## Benchmarks

| Benchmark | What it is useful for | What it does not prove |
| --- | --- | --- |
| [LongMemEval](https://github.com/xiaowu0162/LongMemEval) | extraction, cross-session synthesis, temporal reasoning, updates, abstention | deterministic tool success or low-cost controller value |
| [MemoryAgentBench](https://github.com/HUST-AI-HYZ/MemoryAgentBench) | retrieval, test-time learning, long-range understanding, selective forgetting | a single end-to-end policy ranking without decomposition |
| [Mem2ActBench](https://aclanthology.org/2026.acl-long.370/) | memory-dependent tool name and argument exactness | general conversational memory quality |
| [LongMemEval-V2](https://github.com/xiaowu0162/LongMemEval-V2) | very long-horizon external validity and accuracy/latency frontier | a cheap initial causal pilot |
| [LoCoMo](https://snap-research.github.io/locomo/) | legacy comparability | a reliable sole endpoint; it is judge-heavy and has documented ambiguity |
| [Agent Memory Benchmark](https://github.com/vectorize-io/agent-memory-benchmark) | open ingest/retrieve/answer/judge pipeline and cost tracking | vendor-neutral evidence |

Public benchmark leaderboards are descriptive. System results cannot be compared
across papers unless the base model, extractor, embedding model, answer prompt,
judge, top-k, token cap, and index cost are matched.

## Safety is part of memory utility

Persistent memory creates delayed and cross-session attack surfaces:

- [AgentPoison](https://arxiv.org/abs/2407.12784) poisons persistent memory or
  knowledge bases so trigger queries retrieve attacker content.
- [Memory Injection Attacks](https://arxiv.org/abs/2503.03704) demonstrates
  query-only durable-memory injection.
- [Hidden in Memory](https://arxiv.org/abs/2605.15338) studies sleeper poison
  that activates in later sessions.
- [Memory Poisoning systematic study](https://arxiv.org/abs/2606.04329) finds
  severe true-positive/false-positive tradeoffs in defenses.

Every experiment therefore needs save-time and serve-time attack arms, untrusted
memory framing, provenance, user/session isolation, deletion, supersession,
permission changes, PII canaries, and delayed activation. Estimate task benefit
and later safety harm jointly.

## Surviving research gaps

### 1. Prospective first-use causal credit

At an item's first eligible use, randomize serve versus holdout with a known,
logged propensity; measure executable downstream task utility; audit a subset
with paired deterministic replay; fit a cross-fitted estimator; and train a gate
that sees write-time/past-only fields. No direct prior located in this scan
combines all five requirements.

This is the narrow surviving claim for Causal Memory Holdout Trials. It is not a
claim to have invented causal memory selection or learned memory management.

### 2. Store, serve, and retain decomposition

Most systems conflate three decisions:

1. whether an item is stored at all;
2. whether it is exposed now;
3. whether it remains available for later use.

A factorial or staged design can estimate these separately. Query-time
interventions identify exposure value, not necessarily write or retention value.

### 3. Interference between memories

One-item effects are not additive. Items can be redundant, complementary, or
contradictory. After the one-candidate pilot is valid, test small preregistered
sets with factorial assignments and explicit positivity diagnostics.

### 4. Policy transport

Train under one frozen model, retriever, or harness and test the item-effect
ranking under another. A portable controller is scientifically stronger than a
new backend, but failure to transport is also informative.

### 5. Safety-valued memory

An item can improve the immediate task yet enlarge later poisoning or leakage
risk. Define a vector outcome or shadow price for both utility and delayed harm.

## Recommended build

Create one deep `harness/memory_trials/` module. Its caller supplies a task
source, frozen model, and memory policy; the module owns deterministic event
order, memory budgets, assignment, snapshot/restore, tool tape, trace hashes,
checkpoint/resume, and artifacts.

Public contract:

```python
source = GeneratedMemoryTasks.from_manifest(...)
model = FrozenModel.from_receipt(...)
policy = MemoryPolicy.from_spec(...)
study = compile_memory_study(spec, source=source, model=model, policy=policy)
receipt = study.run(output_dir)
```

The four initial task strata are active core, inactive archive, temporal graph,
and proactive memory-to-tool action. Causal holdout is an overlay across all
four, not a separate synthetic benchmark.

Keep `harness/runner.py` unchanged until this memory path executes real frozen
model calls correctly. Then adapt the generic runner to the proven model/task
interface rather than duplicating inference.

Implementation status at the cutoff: the first public slice now exists. It
generates active-core, inactive-archive, two-hop temporal-graph, and proactive-
tool episodes; implements an engine-owned replayable world; persists raw prompt,
memory frame, model action, tool evaluation, and full trace with hash bindings;
and runs through the existing randomized assignment and AIPW analyzer. The full
registered CPU contract passed at all three propensities with aggregate manifest
SHA-256 `a5c4e6471f57752f9fc2772efd329fdd1198837cda17c403305d351d67d19c80`.
It stopped after 500 episodes and finished through a fresh-process resume. A
strict JSON completion actor and local-only Transformers loader seam now exist,
but no language model has completed a memory task. Public-data importers and
real memory-system adapters remain incomplete.

## Execution ladder

1. CPU oracle: 2,400 deterministic episodes per propensity cell, exact tool
   evaluator, no judge.
2. SmolLM2-135M: loader, constrained output, replay, isolation, and resume smoke.
3. Qwen3-0.6B Base: first decisive frozen-model cell, initially 100 episodes and
   at most eight H100-hours.
4. Common 200-task transport screen across pinned Qwen3.5 4B/9B, Qwen3.6
   35B-A3B, GPT-OSS 120B, and five provider-distinct frontier services.
5. Eligible 2,400-task model confirmations, then sealed LongMemEval-V2,
   MemoryAgentBench, and Mem2ActBench external tests.
6. Tinker-trained external controller only if the frozen model cells pass.
7. Kimi confirmation after Qwen, with the open Kimi Linear 48B checkpoint kept
   as a separate reviewed 8×H100 diagnostic.

Hosted APIs use prospective randomized serve/holdout assignment and AIPW as
their primary causal evidence because provider hidden state and RNG cannot be
restored. Paired replay remains a self-hosted open-checkpoint audit. See
`research/memory-model-transport-2026-08-11.md` for the current roster,
model-by-policy analysis, eligibility gates, and finite budgets.

All long jobs run in a digest-pinned container through Slurm, checkpoint to
persistent storage, and restore in a fresh job before scientific promotion.
Tmux keeps the operator shell alive; it is not a recovery mechanism.

## Immediate kill criteria

- A simple BM25 or LRU arm matches the complicated system at equal cost.
- The graph gain disappears after charging construction, serialization, and retrieval.
- Proactive injection fails to beat random injection and reactive recall at equal tokens.
- The causal gate cannot beat next-use or observational utility by three points
  with a family-clustered confidence interval excluding zero.
- Paired replay differs anywhere except the registered memory exposure.
- Policy lift vanishes on held-out generator families or model transport.
- Any safety red line, deletion, or cross-session isolation test fails.
- Trial, reflection, or consolidation cost exceeds saved context/retrieval cost.

## Reproducibility notes

- Repository pins and detected licenses are in `research/memory-sources.yaml`.
- “Vendor-reported” and “paper-reported” claims are deliberately not labeled reproduced.
- Reproduction requires raw tasks, exact prompts, model and judge receipts,
  embeddings, system configuration, complete traces, storage growth, latency,
  token/call cost, and immutable result manifests.
- The SR-TTT correction—[zero exact matches in 2,250 corrected paired trials](https://arxiv.org/abs/2603.06642)—is the warning case: test startup causality, future leakage,
  exact generation, storage, addressing, and readout independently.
