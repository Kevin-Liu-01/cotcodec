# Variable 3: Memory Policy

**Status:** contract and transport build; not claim-ready. Landscape and
collision audit searched through 2026-08-15 and is recorded in
`research/scans/2026-08-15.md`. Runtime
transport is approximately 65/100; the executable scientific study is
approximately 25/100. The surviving hypothesis is the narrower Causal Memory
Holdout design in `directions/17-causal-memory-holdout-trials.md`; a storage
backend, graph, learned CRUD policy, paired deletion effect, or generic
interference study is not the contribution.

The current generated environment intentionally remains an engine/estimator
doctor. Its policy target is encoded in generated source-quality,
contradiction, and future-use fields; it does not establish a deployable memory
policy. Registered split families, control arms, update/delete metrics, and
most safety cases are not yet executed by the runner. Existing H100 artifacts
come from a source hash whose archive was not retained and are discovery-only.
No Research Gauntlet PASS or memory-policy result is claimed from this state.

## The variable

Memory policy is not one choice between “vector store” and “knowledge graph.”
It is a policy over state transitions:

```text
π_memory(prefix, task state, memory state, budget)
  -> {write, activate, retrieve, inject, update, consolidate, expire, forget, no-op}
```

The optimization target is executable agent utility, with every memory byte,
model call, injected token, and safety failure charged:

```text
U = TaskSuccess
    - λ_token * InjectedTokens
    - λ_read * RetrievalCalls
    - λ_write * IngestionCalls
    - λ_time * WallTime
    - λ_storage * StoredBytes
    - λ_safety * SafetyRisk
```

## Memory layers

| Layer | What it contains | When the model sees it | Primary risk |
| --- | --- | --- | --- |
| Active/core memory | Current goals, constraints, recent facts, live plan | Every relevant turn | Token cost and distraction |
| Inactive/archive | Full events, documents, old facts, tool results | Only after retrieval or proactive injection | Retrieval miss |
| Episodic log | What happened, when, with provenance and outcome | Replayed or summarized on demand | Noise and duplicated experience |
| Semantic/profile | Consolidated facts, preferences, entities | Retrieved or kept in a small profile | Staleness and false consolidation |
| Temporal graph | Entities, relations, valid time, transaction time | Traversed or rendered into context | Extraction cost and wrong edges |
| Procedural memory | Skills, rules, policies, successful workflows | Invoked as instructions or tools | Self-reinforcing bad procedures |
| Latent state | KV cache, recurrent state, fast weights | Internal to model execution | Opaque failure and architecture lock-in |
| Controller | Decides write/read/activate/update/forget | Runs at each eligible transition | Credit assignment and policy cost |

“Active” and “inactive” describe residency, not importance. A critical item can
remain inactive until the moment it is useful; an active item can be harmful if
it is stale, poisoned, or irrelevant.

The comparison taxonomy therefore has six independent axes: representation
(raw, episodic, semantic, graph, procedural, latent); residency (always-active,
active core, inactive archive); write operations (append, extract, update,
delete, consolidate, reflect); read timing (passive, agentic, proactive);
controller/credit (heuristic, supervised, RL, rerollout, randomized causal); and
lifecycle/governance (durability, restart, TTL, purge, tenancy, authority).
Calling a system “active/inactive memory” without specifying all six hides the
actual intervention.

## Executable lifecycle boundary

`memory-system-v1` remains the frozen request-to-selection comparison surface.
The additive `memory-lifecycle-v1` contract now covers the stateful mechanisms
that surface cannot identify: ordered write/update/delete/access events,
residency transitions, maintenance/consolidation, outcome feedback,
checkpoint/restore, purge, and residue inspection. The engine owns operation
order, branch creation, budgets, and receipts; a native adapter must declare
capabilities and fail closed when it cannot implement one.

The 2026-08-14 reference matrix completed 192 cases across active/archive,
update/delete, consolidation, and feedback families at K={2,4,8}. A
network-disabled, read-only container run and an independent host run produced
byte-identical plans, traces, restored suffixes, outcomes, checkpoint and purge
audits, and phase-cost ledgers. Their sealed manifests are
`92a062233cc173a16a022e8c2d99edccec8db90272a10b53a40f8fb03a8a0d90`
and `2ac7a67c05f4b88540d86361413201438d996ec174f22c4c98bf0ffd947624ac`;
comparison receipt
`906c900abaa5a5814cacc104ed582c90f24784f98ac3325ed6490e3837799d61`
passes. This proves only the reference contract and determinism spine. It is
not native-system, model-quality, or publication evidence; the tree is dirty
and externally trusted Slurm attestation is absent.

The immediate mechanism ladder is therefore CPU-first. Total Recall was the
first native promotion/demotion candidate, but its pinned v4.0.4 path failed
the restart gate: automatic hot-to-warm compaction preserved the content row
without a vector, and the next startup deleted the row during orphan cleanup.
The same two-run Docker doctor retained a vector-preserving control row. The
canonical self-contained evidence bundle is
`research/evidence/memory/total-recall-restart-v3.json` at SHA-256
`b1bc7c003584d6b089da91bafef4ac0ba77452557fc358d97e40b2a16418422d`;
this is a reproduced negative lifecycle invariant, not a memory-quality result.
Total Recall is blocked from H100 work at this pin.

The pinned Mem0 2.0.18 backend now has a separate additive native-lifecycle
doctor rather than being inferred from the older request-to-selection smoke.
Two fresh non-root, network-disabled, read-only Docker repetitions pass every
registered non-crash CRUD, inactive-archive, restart-verification,
branch-isolation, lineage, idempotency, and ordinary-scope purge gate with the
same stable projection. A forced crash after native mutation but before
lifecycle-journal commit leaves an ambiguous pending operation; the adapter
fails closed and cannot continue. The interrupted scope also retains the
plaintext canary in `history.db` and Qdrant `storage.sqlite`. The self-contained
evidence is `research/evidence/memory/mem0-lifecycle-adapter-v6.json` at SHA-256
`99edcd00d042361c998d9ba9aa18d67c5963534aedcd922d7ef831f7428a2880`.
It includes self-verifying bounded byte windows for both retained plaintext hits.
This is a CoTCodec adapter recovery defect, not an upstream Mem0 database defect
or a memory-quality result. H100 admission is blocked until exact interrupted-
operation recovery and residue clearance pass twice in fresh contained state.

Hippo Memory `4aeb04c...` also fails admission, for a different reason. It is
not an active/inactive pager: its hard-coded 20-item working-memory overflow and
flush delete entries rather than moving them to an archive. Two independent
network-disabled Docker states reproduced host-wide sleep consolidation of
tenant-A and tenant-B episodes into one semantic record owned and retrievable
by the default tenant, without complete transitive source lineage. Logical
deletion reached zero rows, but all canaries remained as plaintext in SQLite.
The self-contained evidence bundle is
`research/evidence/memory/hippo-retention-cross-tenant-v1.json` at SHA-256
`50449ae3afa9b639a7e5ef992b607c6f9fbb36d2f7dfc9fe914e6eff32410cd1`.
This revision remains useful only as a fixed observational-retention/status
negative control and is blocked from H100 work.

Magic Context `13e1d4c...` is also narrowed by execution rather than promoted.
Two clean, network-disabled Docker states reproduced deterministic chronological
prompt paging and restart-stable projections for supported text and tool fields.
They also reproduced that expansion depends on the host raw-message database,
strips reasoning and unsupported metadata, aliases the same session identifier
across harnesses, and leaves plaintext in both plugin and host SQLite files after
logical clearing. The self-contained evidence bundle is
`research/evidence/memory/magic-context-paging-v1.json` at SHA-256
`638a5c563ee22305e9cfaa7ca9f09f6fbd459dc5d875b5dfea5dbf6eb0b543d4`.
This is a useful host-backed chronological rendering boundary, not a reversible
raw archive, semantic memory, or bidirectional active/inactive pager. Portable
lifecycle and secure purge are blocked, so this mechanism has no H100 memory
admission at the pinned revision.

The Neo4j Agent Memory preference-supersession lifecycle doctor now passes two
clean-volume local arm64 Docker repetitions over identical pre-extracted tuples
with no LLM or embedding calls. It preserves native `SUPERSEDED_BY` and
`valid_until` semantics, current and historical views, retained-volume restart,
user isolation, lineage, idempotent retry, and purge. Its self-contained
evidence bundle is
`research/evidence/memory/neo4j-preference-lifecycle-local-arm64-v1.json` at
SHA-256 `98a21ee7fcb19d40d9fe55992da80c7fa8e9ebc9b7d858827e545a3a443dcb35`.
The exact cluster-amd64 Docker-under-Slurm confirmation also passes in job 303:
two more clean repetitions preserved restart state, supersession, historical
views, isolation, idempotency, and zero-residue purge. The batch allocated one
H100 for scheduler provenance but passed no GPU into either container and made
zero model or embedding calls. Its self-contained evidence is
`research/evidence/memory/neo4j-preference-lifecycle-h100-v1.json`
(`dfeaf750...`). Slurm job 304 then passed the registered designed
identical-tuple parity gate twice with the same exact client image and SBOM.
True traversal and an exact flat SQLite join ceiling each recovered 48/48
targets, while flat BM25+dense retrieval and an object-degree-preserving
shuffled topology recovered 0/48. The scheduler allocated one H100 for
provenance, but neither container received a GPU and the component made zero
model or embedding calls. Its evidence is
`research/evidence/memory/neo4j-identical-tuple-flat-parity-h100-v1.json`
(`e09d1638...`). This isolates traversal on a designed fixture while explicitly
refuting a unique graph-store claim: an exact relational join ties the graph.
The next cheap gate then killed the escalation before any actor spend. Two
byte-identical, network-disabled Docker repetitions froze 64 natural
LongMemEval knowledge-update and temporal-reasoning questions. Flat
BM25+dense recall-all@4 was 0.34375; chronological neighbor expansion fell to
0.203125, for a paired stratified-bootstrap true-minus-flat interval of
[-0.234375, -0.046875], and did not beat three per-node-degree-preserving
shuffled chains. The evidence is
`research/evidence/memory/longmemeval-natural-session-topology-negative-v1.json`
(`2d2849d1...`). The planned Neo4j natural actor cell is forbidden. This result
tests a deterministic chronology-expansion rule, not native Neo4j extraction,
general graph memory, or answer quality. A contained GAAMA
matched-component doctor has now passed twice at
revision `2d992f7`: true graph retrieved the target in 24/24 synthetic cases,
while flat and degree/type-shuffled graph retrieved 0/24; PPR weight zero was
an exact A/A control, and model, embedding, and network calls were zero. The
sealed evidence is `research/evidence/memory/gaama-graph-component-v1.json`
(`cf903e2b...`). This is component-contract conformance, not natural-data graph
efficacy or GAAMA quality. It also reproduces a useful negative: GAAMA's hub
dampening is canceled by subsequent row normalization. A separate two-repeat
natural LoCoMo component now passes: dev-selected structural PPR improves
conversation-equal evidence recall-all@10 by 2.04 points over flat BM25 (95% CI
[1.25, 2.96]) and 2.17 points over three typed per-node-degree-preserving
shuffled controls (95% CI [1.30, 3.20]); both one-sided sign tests have
`p=0.0078`. The fully rerunnable v5 evidence is
`research/evidence/memory/gaama-natural-graph-v5.json` (`011a2191...`). This is
still retrieval-component evidence, not generated-node, answer, agent, or
publication evidence. The registered actor-translation screen has now run to
completion on H100. Docker-under-Slurm jobs 295 and 297 used the pinned
Qwen3.5-4B actor for 1,000 matched cases, checkpointed at case 656, and resumed
in a fresh Slurm job with a byte-identical prediction prefix. True graph
evidence retained a small retrieval advantage over flat (0.385 versus 0.375
recall-all@10), but reduced answer token F1 (0.2741 versus 0.2831; clustered
difference -0.0088, 95% CI [-0.0267, 0.0053]) and failed to beat the mean of
three topology shuffles. The machine-validated negative is
`research/evidence/memory/gaama-h100-actor-negative-v1.json` (`7ca80f0a...`).
The registered graph-to-answer hypothesis is killed and larger-model GAAMA
escalation is forbidden. The earlier retrieval positive remains a component
result only.
Graphiti then tests graph state/retrieval, and ReasoningBank tests procedural
state. A newer or explicitly patched Hippo arm must first fix
tenant partitioning, lineage, physical purge, configurable K, and true movement.
Each surviving candidate must pass
applicable lineage, branch isolation, fresh-process restart, purge/residue,
and phase-cost gates before it can enter an H100 actor comparison.

The bundled Hermes Holographic provider is also now closed as a portable
lifecycle negative at commit `a90d536...`. Two fresh network-disabled Docker
volumes reproduced restart-stable SQLite/FTS state, idempotent add, and
persistent update/feedback, but a fresh logical session could retrieve another
session's facts and the provider exposes no native per-session purge. The
sealed receipt is `research/evidence/memory/hermes-holographic-lifecycle-v1.json`
(`a532c646...`). This is compatible with a documented single-user local store,
but it fails the task-blind multi-session harness boundary. It remains off the
H100 path until an explicit scoped wrapper or newer upstream pin passes; HRR
quality is a separate dependency-pinned experiment.

The bundled Hermes ByteRover provider is likewise closed at CLI v3.16.1 as an
offline provider-boundary negative. The registered doctor separately binds the
annotated tag object `68ef7f9...`, peeled commit `1f4609c...`, npm package and
integrity, and Hermes adapter source. In two fresh non-root, network-disabled
Docker volumes, native `brv search`, Hermes `brv query`, and Hermes `brv curate`
all failed at daemon startup because the daemon required network access. The
local canary survived restart, so this is not volume loss. The adapter also uses
a profile-global directory and supplies no native session purge. Sealed evidence
`research/evidence/memory/hermes-byterover-offline-v1.json` (`4b51e2f1...`)
blocks that revision from H100 admission; this is not a ByteRover quality claim.

The bundled Hermes OpenViking path is now closed at upstream revision
`eeff5a4...` as a secure-purge negative. Two independent internal-network,
read-only-root Docker runs through the exact provider passed direct CRUD, two
fresh backend restarts, logical two-tenant isolation, and restart-stable logical
deletion. After the final restart, however, both deleted plaintext canaries
remained in retained LevelDB files. The sealed receipt is
`research/evidence/memory/hermes-openviking-lifecycle-v3.json`
(`a946df0c...`) and includes byte-level residue proof windows. The result does
not test OpenViking memory quality or L0/L1/L2 progressive disclosure. The pin
is excluded from H100 quality work until native purge or cryptographic erasure
passes the same retained-state doctor.

### Post-cutoff architecture and provider delta

The late 2026-08-14 primary-source sweep adds two useful architecture priors
without creating a new persistent-memory claim. [Consolidator](https://arxiv.org/abs/2608.11701)
learns a small slot-local STM-to-LTM transform with router feedback;
[MARCH](https://arxiv.org/abs/2608.12435) retrieves cumulative recurrent-state
anchors by content. Both are paper-only and architecture-coupled. They belong
beside Kimi/linear-state experiments, not in the active/archive systems wave.

The strongest new systems controls are [Palimpsest](https://github.com/joe51111jwd/palimpsest/tree/0f83e166b0512a5ca9f38c2559f68749b35e994d)
for bitemporal stale-state handling and [Mnemosyne OSS](https://github.com/mnemosyne-oss/mnemosyne/tree/a0e14243e04dbe3fc29287e58126ff5dc0e02b35)
for one-way working-to-episodic consolidation plus a standalone Hermes provider.
Palimpsest has now failed its exact two-repeat contained lifecycle falsifier:
valid-time, pre-restart transaction cutoffs, and cardinality voting passed, but
native restart lost transaction closures and per-key cardinality state. Logical
correction left plaintext in SQLite and no native purge exists. The sealed result
is `research/evidence/memory/palimpsest-bitemporal-negative-v1.json`
(`c0fa0f98...`); H100 actor work is forbidden for this revision. Mnemosyne also
failed its exact two-repeat contained lifecycle
falsifier: consolidation, isolation, and fresh-process recall passed, but recall
did not reactivate archived state and documented forget left the episodic summary
logically recallable and physically resident. The sealed result is
`research/evidence/memory/mnemosyne-one-way-consolidation-negative-v1.json`
(`3b516fa5...`); H100 actor work is forbidden for this revision.
Icarus `6e34870...` is now also closed as a manual-lifecycle negative rather
than a pager candidate. Two clean contained runs reproduced explicit
working-to-private-archive-to-shared-wiki promotion, isolation, supersession,
non-destructive rollback, and restart, but replaying `end_session` created an
extra private summary and shared-wiki link. The pin exposes no native delete,
forget, or scoped purge API, and all private/shared/superseded/replacement
plaintext canaries remained resident. The sealed result is
`research/evidence/memory/icarus-manual-lifecycle-negative-v1.json`
(`9d476930...`); its H100 actor is forbidden. Palimpsest, Mnemosyne, and Icarus
do not demonstrate autonomous bidirectional active/inactive residency.
Standalone HyperspaceDB, DSH Gate, Mneme, and human-gated Unified Agent Memory
are admission or boundary controls, not additions to the official eight-provider
Hermes roster. This delta preserved the negative conclusion at its August 14
cutoff: no verified new open implementation supplied true bidirectional item
paging.

The 2026-08-15 repository delta adds three further boundaries. JordanMcCann
agentmemory V4 commits a complete 481/500 result, but its run uses the
answer-session-only LongMemEval oracle artifact and forty-six optimization
cycles over the same questions; it is answer-context assembly and an overfit
warning, not full-haystack retrieval evidence. Agentra AgenticMemory is a
locked event-sourced causal-graph candidate, but its append path flushes without
`fsync` and its open path silently accepts an incomplete tail as a valid prefix;
crash, truncation, erasure, branch, and same-record flat doctors precede any
H100 actor cell. Experience OS Lab's archive, promote, demote, and refresh calls
only recompute lifecycle labels; they do not durably move records, and its only
experiment is a deterministic four-train/ten-test flight toy. None is evidence
for active/inactive paging or a new research direction.

The GAAMA Qwen3.5-4B true-graph-versus-flat actor cell is compiled and sealed
for Docker-under-Slurm discovery execution. It was not launched on 2026-08-15
because the dedicated H100 host failed before SSH with `Network is unreachable`.
No CPU inference substitute or bare-host workload is admissible. On reconnect,
run read-only Slurm/Docker/GPU doctors, verify every source/model/evidence hash,
then dry-run, `--test-only`, and submit the one-H100 cell.

Two late same-day controls sharpen the orchestration boundary without adding a
new direction. DSH Memory System's hot and cold layers are two prompt views over
one Markdown vault, so it belongs in a matched push-versus-pull injection cell,
not the active/inactive pager lane. Longform Memory is a deterministic four-way
context allocator with no persistent store, so it belongs in the compaction and
context-allocation matrix. Both require CPU contract doctors first; any actor
quality comparison remains contained Docker-under-Slurm H100 work.

A second bounded same-day repository wave adds five controls, not a new
direction. E²-Mem supplies the strongest new episode-to-child-event hierarchy
but publishes no immutable result bundle, model revision, or dependency lock;
the first valid comparison freezes identical extracted records and isolates
flat, episode-only, and full hierarchy retrieval. Canon is manual decision
approval, supersession, and provenance governance rather than autonomous
paging. Vector897 Palimpsest's decay path marks cold rows archived while every
normal retrieval excludes archived rows and no reverse promotion exists, so it
is a one-way archive negative. The unlicensed lgoyal6 memharness demonstrates
matched prompts and construction-token metering over only twenty tasks, not a
reusable system ranking. EvolveBank preserves an important procedural-memory
null: its raw apparent gain disappears after removing four control-only network
errors, leaving both arms at 0.768 and seven paired wins each, although the raw
task logs and frozen bank are not committed. Every model confirmation remains
H100-only after CPU provenance and lifecycle gates.

A third same-day source wave changes the intake boundary without changing the
research direction. [ASTRA](https://github.com/cyh7789/astra/tree/644f9d4e65f4e725996025834c91531592ab6166)
implements a count- and character-bounded active `MemoryWindow` over durable
memories, evicts unpinned residents without deleting their backing records,
persists the active set, and allows later retrieval to admit a nonresident
record again. Two fresh network-disabled, read-only ARM64 containers reproduced
the same 26/26 pure window, retrieval, and guard assertions; the tracked receipt
is `research/evidence/memory/astra-working-set-core-v1.json` (`3a310140...`).
This made ASTRA a credible bidirectional pager **candidate**, but not yet an
actor-admissible pager result. The native lifecycle contract then executed as
the registered one-H100 Docker-under-Slurm doctor
`experiments/memory/stage3-astra-native-lifecycle-doctor.yaml`; it forces a
CockroachDB process kill between acknowledged state and a fresh-container
restore and tests eviction-to-repromotion, user isolation, duplicate retry,
soft-delete residue, and all-pinned saturation twice. Slurm job 269 passed every
registered boolean lifecycle check in both clean stores, but failed the
preregistered cross-repeat projection gate: the same total recall accesses were
assigned to different tied records (four differences before restart and ten
after restart). The source orders equal vector/fused scores without a stable
secondary key, so persistent access reinforcement is nondeterministic. The
sealed negative is
`data/results/astra-native-lifecycle/2026-08-15-job269-v11/analysis.json`
(`adf6c861...`). Frozen ASTRA actor frames are forbidden until a newer or
explicit repair arm closes deterministic tie-breaking, physical purge,
idempotency, and hard pinned-capacity gates.

A fourth source wave adds orthogonal controls without producing a new
architecture direction. [Memoria](https://github.com/matrixorigin/Memoria/tree/efd3d6515969971dfa894737272b8317bcb643e7)
occupies native branch/snapshot/diff/merge/rollback memory lifecycle, but not
active/inactive paging. [Agent Recall](https://github.com/mnardit/agent-recall/tree/dcf21b5cc9691e1371299917e2e474fb82e07cab)
occupies scoped bitemporal slots and inherited briefings; its tiers are
visibility levels rather than residency. [MemoryGraph](https://github.com/memory-graph/memory-graph/tree/4f834c01765dc52b66c621fa42928fb0b52208cb)
is a typed graph and CLI control whose traversal benefit remains unmeasured
against identical flat nodes. [TokenMizer](https://github.com/Shweta-Mishra-ai/tokenmizer/tree/131e3d1569de3e8f70c198ade4e791b47f63dc41)
occupies session-graph checkpointing and context compaction; its claimed result
JSON is absent from both the evaluated tag and current tree, so its evidence is
paper-reported only. All four require CPU provenance/lifecycle doctors before
H100 actor admission. ASTRA's one-H100 native falsifier ran first and did kill
actor admission before model-quality spending.

A fifth source wave sharpens the same boundary. [Active Graph](https://github.com/yoheinakajima/activegraph/tree/8aedb1866cf5dce056af97529152ffd6f468a1ed)
is an event-sourced execution-graph, deterministic-replay, and SQLite-fork
substrate, not a semantic-memory efficacy result. [MemForge](https://github.com/salishforge/memforge/tree/16e2f15c5881a38911f64ca81b3dc0b25d6207ec)
implements hot-to-warm consolidation, cold archival, and explicit cold-to-warm
restore with lineage, but restore is a manual operation and hot is a write
buffer rather than bounded actor-visible context. Its own README retracts the
earlier LongMemEval retrieval headline after finding that the scorer ignored
`k`; raw task receipts are absent, so no quality number is admitted.
[agenticow](https://github.com/ruvnet/agenticow/tree/dd4f437b92d2dbbc1f40dfa00023eed6e9c3bd84)
adds copy-on-write vector branches, checkpoints, tombstones, rollback, and
promotion as a paired-state substrate without active/inactive residency.
[Hermes Observational Memory](https://github.com/intertwine/hermes-observational-memory/tree/90d83c1ff768d80f99f4e3ef4d76269f90e1c808)
adds a standalone startup-push/retrieval-pull/consolidation provider in a
separate cohort from the sealed eight bundled Hermes providers plus Memori.
Docker-under-Slurm H100 job 291 reproduced real discovery, explicit-note
restart persistence, isolation, budget refusal, and operator-root cleanup twice,
then correctly returned `BLOCKED_NO_PROVIDER_NATIVE_DELETE_OR_ERASURE`. The
provider has no native delete/forget tool or physical-erasure contract, so this
revision is actor-blocked; the result is lifecycle-negative evidence, not memory
quality. These systems are controls and admission targets, not a new direction. ASTRA
remains the only credible bounded automatic pager mechanism found in this wave,
but its H100 lifecycle result now blocks the revision on nondeterministic recall
state as well as purge, idempotency, and pinned-capacity defects.

## What existing systems establish

The machine-checked source and code ledger is
`research/memory-sources.yaml`. Important occupied families are:

- [MemGPT/Letta](https://arxiv.org/abs/2310.08560): agent-managed paging
  between a small core and external recall/archive.
- [Graphiti](https://github.com/getzep/graphiti): incremental temporal graph
  with provenance, validity intervals, contradiction handling, and hybrid
  retrieval.
- [Hindsight](https://github.com/vectorize-io/hindsight): retain, recall, and
  reflect over facts, experiences, relations, and mental models.
- [Mem0](https://github.com/mem0ai/mem0): fact/profile extraction, CRUD, and
  retrieval, with an optional graph representation.
- [LangMem](https://github.com/langchain-ai/langmem): hot-path memory tools and
  background extraction/consolidation.
- [MemexRL](https://arxiv.org/abs/2603.04257),
  [AgeMem](https://arxiv.org/abs/2601.01885), and
  [Memory-R1](https://aclanthology.org/2026.acl-long.583/): learned memory
  operations and controllers.
- [ForesightKV](https://arxiv.org/abs/2602.03203) and
  [Learning to Evict](https://arxiv.org/abs/2602.10238): future-derived labels
  for learned latent-cache eviction.
- [Memory-R2](https://arxiv.org/abs/2605.21768): same-state local rerollouts
  over alternative INSERT, UPDATE, and DELETE actions plus global reward.
- [MemCon](https://arxiv.org/abs/2607.13591): online selection among retrieval,
  plan injection, consolidation, forgetting, and no-op actions.
- [TARL](https://arxiv.org/abs/2608.03699): typed accepted/pending/rejected
  ledgers and counterfactual execution against the next gold memory state.
- [MSCE](https://arxiv.org/abs/2607.16621): trace-to-policy-to-skill
  crystallization with a heuristic rather than causal policy-gain signal.
- [memorywire](https://arxiv.org/abs/2606.01138) and
  [Portable Agent Memory](https://arxiv.org/abs/2605.11032): portable memory
  protocol, provenance, export, and rehydration layers.
- [ReFind](https://arxiv.org/abs/2608.12888): agentic search over raw chat logs
  using lexical, session, local, and temporal expansion rather than a compiled
  memory structure.
- [Router-Mem](https://arxiv.org/abs/2608.01285) and
  [ERSkill](https://arxiv.org/abs/2608.12720): evidence-sufficiency routing and
  learned retrieval programs.
- [LycheeMemory V2](https://arxiv.org/abs/2608.12990) and
  [ScrubJay-MEM](https://arxiv.org/abs/2608.04746): segment-level consolidation
  and type-conditioned temporal decay.
- [ProGraph](https://arxiv.org/abs/2607.19359): graph-free profile traversal for
  multi-hop retrieval; a direct simple-control challenge to graph memory.
- [ToolAtlas](https://arxiv.org/abs/2607.11126): provider-side
  execution-verified tool memory reported to transfer across agent frameworks.
- [MemRL](https://arxiv.org/abs/2601.03192): semantic-then-utility retrieval
  whose per-memory values are updated from executable episode reward.
- [U-Mem](https://arxiv.org/abs/2602.22406): Thompson-sampled memory service
  plus paired bundle-level memory-versus-base advantage and consolidation.
- [AEL](https://arxiv.org/abs/2604.21725) and
  [epsilon-MemEvo](https://arxiv.org/abs/2608.12522): learned stochastic
  no-memory/serve-intensity policies driven by later outcomes.
- [MindMemOS](https://arxiv.org/abs/2608.12428): active/archive graph memory,
  learned CRUD, feedback repair, dreaming, and skill evolution.
- [QCR](https://arxiv.org/abs/2608.12847): matched no-memory, summary, full
  trajectory, and query-conditioned reuse evaluation.
- [ReasoningBank](https://arxiv.org/abs/2509.25140): success/failure trajectory
  distillation into reusable procedural reasoning memories.
- [PAST-Bench](https://arxiv.org/abs/2608.04003): longitudinal fresh-session
  persistence-on/off sequences that test later improvement and whether the
  intended save, retrieve, reuse, and update pathway actually occurred.
- [Reliable Post-Retrieval Assembly](https://arxiv.org/abs/2606.01435): a
  direct demonstration that evidence extraction and answer-policy execution
  can dominate the measured outcome even when retrieval is held fixed.
- [A-TMA](https://arxiv.org/abs/2607.01935): explicit current, historical, and
  transition roles plus separate bank, retrieval, and answer failure analysis.
- [MemGuide](https://arxiv.org/abs/2505.20231): intent-aligned retrieval and
  missing-slot marginal-gain reranking for proactive task-oriented dialogue.
- [CoEvo-Mem](https://arxiv.org/abs/2608.01739): alternating co-evolution of a
  retrieval router and outcome-updated memory values and graph relations.
- [When to Forget](https://arxiv.org/abs/2604.12007): the mandatory cheap
  observational value control, explicitly estimating association rather than
  item-level causal contribution.
- [LeanMem](https://arxiv.org/abs/2608.03463) and
  [HiGram](https://arxiv.org/abs/2608.05095): typed selective maintenance and
  hierarchical path-level graph rewriting, respectively.
- [GBrain](https://github.com/garrytan/gbrain) and
  [Claude-Mem](https://github.com/thedotmack/claude-mem): open harness controls
  for file-authoritative graph/consolidation and hook-driven observation
  capture/progressive disclosure.
- [SkillOpt](https://arxiv.org/abs/2605.23904),
  [Hermes Agent](https://github.com/NousResearch/hermes-agent), and
  [Memvid](https://github.com/memvid/memvid): held-out-gated procedural slow
  state, one-shot skill authoring, and event-sourced replay substrate. These are
  separate procedural/storage controls, not factual memory-policy results.
- [LightMem2](https://github.com/zjunlp/LightMem2): protected active context,
  archive-before-stub eviction, and explicit tool-output fault recovery. This
  was the strongest open active-context/inactive-archive runtime control found
  in the August 14 code scan, but the pinned `dfc67e8` runtime is now a negative
  control: two contained runs reproduced cross-session recovery through the
  actual MCP path, same-millisecond archive-path collision, and no native
  scoped purge. It manages completed tasks and tool payloads rather than a
  general semantic-memory pager, and this revision is barred from H100 actor
  evaluation.
- [JiuwenMemory](https://github.com/openJiuwen-ai/agent-memory): multi-level
  background consolidation; it does not demonstrate learned bidirectional
  promotion/demotion.
- [Mnemon](https://github.com/mnemon-dev/mnemon) with the separate
  [`dsh-mnemon`](https://github.com/omdsh-dev/dsh-mnemon) plugin: isolated named
  multi-graph stores plus a persistent, host-selected active-store registry.
  Two contained repetitions passed static selection, inactive-read rejection,
  targeted-write activation, and restart persistence, while also reproducing
  that item forget is soft and leaves plaintext in SQLite. This admits only a
  bounded static-space H100 control, not learned paging, ACLs, or secure erasure.
- [Shodh Memory](https://github.com/varun29ankuS/shodh-memory): deterministic
  graph, decay, and reinforcement reference, but not a disjoint tiered pager at
  pinned `98c6e48`. Two clean contained runs showed every fresh Working record
  already in RocksDB, active maps disappearing across restart while stale tier
  labels remain, and a 26-hour Session record stranded after fresh-process
  maintenance. Its H100 actor is barred at this revision.
- [ASTRA](https://github.com/cyh7789/astra): the first current open candidate
  with a genuinely bounded active working set, durable nonresident memories,
  and retrieval-driven re-admission. Its local evidence is component-only; it
  does not yet establish native lifecycle correctness or a learned pager.
- [Sage Wiki](https://github.com/xoai/sage-wiki) and
  [Fidelis](https://github.com/hermes-labs-ai/fidelis): file-authoritative
  evidence graphs and zero-write-LLM BM25/dense/RRF retrieval. Their committed
  partial or workload-specific artifacts are intake evidence, not matched full
  benchmark reproductions.

Therefore the following are not credible novelty claims: active plus archival
memory, a memory graph, learned CRUD operations, proactive injection, a
future-utility predictor, or RL-trained memory selection in isolation.

The 2026-08-13 delta adds direct precedents for paired deletion effects
([CommitKV](https://arxiv.org/abs/2608.07855)), generic interference
([Controlled Memory Interference](https://arxiv.org/abs/2608.07622)), adaptive
multi-structure routing ([MESA](https://arxiv.org/abs/2608.10108)),
prediction-error formation ([Nemori](https://aclanthology.org/2026.acl-long.1607/)),
and state-level evolving-memory CRUD
([GEM/MemState](https://arxiv.org/abs/2605.26252)). The admissible novelty
wording is only “under the recorded primary-source and official-code search
through 2026-08-14 UTC, no direct prior was found combining prospective logged
known-propensity assignment of one retained item at its first eligible service,
executable downstream utility, an independent paired continuation from the same
pre-service state, and a cross-fitted deployment gate restricted to write-time
covariates.”

Memory-R2 means paired or counterfactual memory-credit assignment in general is
not admissible novelty wording. MemCon, Router-Mem, and ERSkill make learned
operation and retrieval routing mandatory baselines. ReFind makes raw logs plus
agentic BM25 the simple floor for every compiled representation. memorywire and
ToolAtlas should be reused or explicitly contrasted for cross-backend and
tool-memory transport; portability remains experiment infrastructure rather
than the research direction.

## Research questions

1. **Residency:** When should an item move between inactive archive and the
   active context under a fixed token and read budget?
2. **Representation:** At equal serialized bytes and construction cost, when
   does a temporal graph beat a flat event log or BM25/vector retrieval?
3. **Timing:** When should memory be injected proactively rather than waiting
   for model-initiated retrieval?
4. **Forgetting:** Can expiry, supersession, and deletion improve executable
   success without suppressing rare but important evidence?
5. **Causal credit:** Can prospective randomized serve/holdout trials estimate
   downstream value well enough to train a strictly past-only gate?
6. **Transport:** Does a learned memory policy retain value across agent model,
   retriever, tool environment, and harness changes?
7. **Safety:** Does a useful memory item also increase poisoning, leakage, or
   cross-user exposure risk?

## Baseline matrix

Every comparison uses the same frozen model, prompt, tool tape, generation
settings, context cap, task set, seeds, tuning trials, and memory budget.

| Family | Required arms |
| --- | --- |
| No external memory | no-memory; full transcript ceiling; sliding window |
| Heuristic active memory | FIFO; LRU; LFU; random/reservoir; type-aware |
| Flat archive | lexical BM25 top-k; ReFind-style raw-log agentic search; dense top-k; hybrid top-k |
| Consolidated memory | extract-and-update facts; hierarchical summary; Lychee-style segment consolidation |
| Graph memory | temporal graph; static graph retrieval; graph-free ProGraph profile traversal; UnifiedMem matched flat configuration |
| Timing and depth | reactive recall; random proactive injection; learned proactive injection; oracle injection ceiling; Router-Mem shallow/deep routing; ERSkill retrieval program; LightMem2 protected-suffix eviction/recovery |
| Learned value | next-use predictor; observational utility; query-time causal intervention; prospective holdout gate |
| Governance value | Memory Worth two-counter association; Tidemark receipt-bound outcome credit; prospective holdout gate |
| Learned operations | Memory-R2 local rerollout; MemCon online controller; matched CRUD-policy RL |
| Procedural memory | Hermes one-shot skill; SkillOpt held-out-gated edits; MSCE skill crystallization; trace replay; no-skill control |
| Interoperability | native backend API; memorywire adapter; canonical frozen bundle |
| Expiry | fixed TTL; recency decay; ScrubJay type-conditioned decay; no-expiry control |
| Answer assembly | direct answer; structured evidence packet; deterministic policy executor; matched LLM executor |
| Longitudinal pathway | PAST-Bench persistence on/off; save/retrieve/update pathway evidence; later-task gain; MemoryStress secondary degradation diagnostic |
| Safety | untrusted-memory framing; save-time filter; serve-time filter; MAPLE lifecycle gates; MAFIA query-only poison; no-filter control |

Graph arms receive no free metadata. Charge canonical serialized node and edge
bytes, graph construction calls, traversal time, and rendered context. Do not
pad holdout prompts; measure actual token savings.

Two deterministic mechanism controls are now executable through the same
`MemorySystem` and frozen-bundle interface as BM25 and the temporal graph:
`raw-log-rrf` keeps every prefix event verbatim, performs BM25 plus archive-group
RRF and local expansion, and uses bounded rare bridge-token feedback;
`profile-expansion` concatenates exact valid records by entity and follows
substring entity mentions without constructing graph edges. Their receipts
explicitly say they are not paper-faithful ReFind or ProGraph reproductions:
the former lacks the LLM ReAct controller and calendar filter, while the latter
lacks LLM profile/residual co-extraction and embedding gates. They are matched
mechanism falsifiers; full external reproductions remain separate cells.
Contained H100 job 130 reproduced the local 16-task/four-control frozen matrix
byte-for-byte at content root `f143df12…` from dirty-tree archive `b4b0bca6…`
and image `sha256:b63cc96d…`. This proves transport and deterministic selection,
not actor quality, paper fidelity, or publication provenance.

`full-prefix-ceiling` is now implemented as a deliberately unmatched diagnostic
arm. It injects every ordered raw prefix event in one attributed block, charges
all bytes, estimated tokens, and writes, uses zero retrieval reads, and refuses
to truncate: an undersized diagnostic budget is a hard failure. On the pinned
32-task LongMemEval panel, the observed envelope is 6,721 estimated tokens at
the median and 20,303 at the maximum, so the future actor cell must register a
separate 32,768-token ceiling and remain ineligible for the matched primary
comparison. This is an implementation/measurement receipt; no actor has run it.

Contained job 132 froze the nine matched or bounded diagnostic controls on the
same public panel at matrix root `5f9001fb…`, including raw-log RRF, graph-free
profile expansion, BM25, and temporal graph. LRU was correctly marked
ineligible because LongMemEval supplies no explicit access events. This still
establishes selection/provenance only: the official semantic judge and actor
outcomes remain absent.

## Experiment ladder

### Stage 0 — deterministic memory-to-action environment

Generate unique 20–40-step episodes with exactly one registered candidate item
and four equal strata:

1. **Active core:** a recent fact, update, or deletion is needed within eight
   steps and no archive read is allowed.
2. **Archive:** evidence is at least sixteen steps old and forced out of core;
   one top-4 read is allowed.
3. **Temporal graph:** a two- or three-hop entity/event chain includes valid-time
   updates, supersession, deletion, or an abstention case.
4. **Proactive tool:** a tool argument learned earlier is omitted from the
   current request; memory may be proactively injected before the first action.

The deterministic oracle scores the final answer or exact tool name and JSON
arguments. There is no LLM judge. Generator families, namespaces, graph shapes,
update rules, and delay distributions are split as families, never random rows.

Registered primary setting:

```text
episodes per propensity cell: 2,400
train/dev/test: 1,440 / 480 / 480
propensity: 0.50, 0.25, 0.10
paired replay audit: 25%
active capacity K: 4 primary; 2 and 8 diagnostic
archive reads: <= 1 per opportunity, top-k <= 4
injected memory: <= 256 tokens
seeds: 42, 43, 44
```

Current implementation evidence: the registered seed-42 CPU contract executed
2,400 episodes at each propensity and returned
`ORACLE_ENGINE_CONTRACT_PASS`. It uses explicit active/archive/graph residency,
a two-hop temporal graph, exact answer/tool evaluation, compact untrusted-data
frames under the 256-token cap, raw prompt/frame/output/tool artifacts bound by
hashes, A/A replay, paired counterfactual replay, and cross-fitted analysis. The
run intentionally stopped after 500 episodes, then resumed in a fresh process
from durable assignment, episode, and checkpoint artifacts. Aggregate manifest
SHA-256:
`a5c4e6471f57752f9fc2772efd329fdd1198837cda17c403305d351d67d19c80`.
This validates deterministic environment, estimator, and process-recovery
plumbing only. Its target is engineered from generator annotations, it does not
run the YAML's full train/dev/test/control/safety matrix, and it is not evidence
about a memory policy, LLM, real memory backend, or public benchmark. Earlier
non-resumable and one-hop runs are retained as superseded audit evidence.

### Stage 1a — loader and replay smoke

Use the pinned `HuggingFaceTB/SmolLM2-135M` registry snapshot only to prove:

- deterministic load and completion;
- constrained action rendering;
- engine-owned snapshot and restore;
- identical A/A replay;
- branch traces differing only in the registered memory exposure;
- no cross-session memory bleed;
- atomic checkpoint and byte-identical resume.

This stage is interface evidence, not memory-quality evidence.

### Stage 1b — frozen open-model screen

Use the pinned `Qwen/Qwen3-0.6B-Base` snapshot, BF16 evaluation, greedy decoding,
and a constrained `{answer | tool, args}` renderer. Run exactly 100 episodes
first and keep total discovery spending at or below eight H100-hours. Expand
only if replay, safety, provenance, and task-competence gates pass.

The public external tests remain sealed during policy fitting:

- [LongMemEval](https://github.com/xiaowu0162/LongMemEval) for extraction,
  cross-session synthesis, temporal updates, and abstention;
- [Mem2ActBench](https://aclanthology.org/2026.acl-long.370/) for exact
  memory-dependent tool actions.

LoCoMo remains a legacy comparability cell, not the sole endpoint. Very large
LongMemEval-V2 cells are deferred until the small-model screen is stable.

### Stage 1c — model-scale and frontier-provider transport

The registered matrix in `experiments/memory/stage1-model-transport.yaml`
reuses one sealed task and assignment manifest across:

- pinned Qwen3.5 4B and 9B hybrid checkpoints;
- pinned Qwen3.6 35B-A3B and GPT-OSS 120B large open checkpoints;
- GPT-5.6 Sol, Claude Opus 5, Gemini 3.5 Flash, DeepSeek V4 Pro, and Kimi K2.6;
- the pinned Kimi Linear 48B-A3B Base only as a separate architecture
  diagnostic, never as an instruction-agent competence comparison.

Run 200 common tasks per model first. Only models with at least 80% oracle-
memory success, 95% valid action JSON, no isolation failure, and acceptable A/A
drift enter the 2,400-task confirmation. The primary analysis estimates the
within-model causal-policy lift and a categorical model-by-policy interaction.
Parameter-count monotonicity is exploratory because architecture, MoE active
parameters, post-training, and provider scaffolding are confounded.

Self-hosted checkpoints retain the paired replay audit. Hosted APIs use
prospective single-arm randomization and cross-fitted AIPW as primary evidence;
identical hosted calls are A/A drift probes, not exact counterfactual replay.
The full methodology and current official-source roster are in
`research/memory-model-transport-2026-08-11.md`.

Current exploratory GPT-5.6 Sol evidence is sealed but not publication-ready.
A 200-task hosted competence screen produced valid structured actions on all
tasks and bound all provider receipts. Of 97 tasks assigned to served memory,
94 succeeded. Active-core, archive, and proactive-tool service were 28/28,
23/23, and 25/25; temporal-graph service was 18/21. All three failures followed
a newer conflicting graph edge. Twenty repeated A/A tasks had zero action
disagreement. A separately sealed post-hoc analysis binds bundle manifest
`64f3f5da6a104bb8fa97c052f240985affa2a24e3e9728dbeb726a25d5c69329`.
This run predates exact source-tree receipts and cannot estimate a memory-policy
effect.

The registered 80-task safety screen found a serious generated-source warning:
hazardous memory was served in 33 tasks and caused 13 failures, versus zero in
47 holdouts. The risk difference was +39.4 points; the Newcombe 95% interval
was +17.1 to +56.3 points and Fisher's exact two-sided p-value was `1.82e-6`.
Stored prompt injection failed on all 6/6 served cases and PII canaries on 6/11.
One of eight repeated A/A prompts also changed action, so the A/A stability gate
failed. The run used a dirty source tree and a synthetic attack suite; it is a
red-line pilot requiring clean-image replication across provider families, not
a general claim about GPT-5.6 or production memory.

The open scale lane now accepts the same transport contract with an explicit
pinned model ID. Reviewed profiles cover Qwen3.5 4B and 9B on one H100 and
Qwen3.6 35B-A3B plus GPT-OSS 120B on two H100s, each capped at eight GPU-hours.
Every native system first emits a content-addressed frozen-selection bundle;
the open and hosted runners verify its source, budget, treatment mode, and
request hashes so all actors receive byte-identical evidence. The Slurm
compiler requires the bundle path and file digest and mounts it read-only after
host-side verification. The compiler emits validated digest-pinned Slurm
manifests, and a successor job
may copy only a provenance-matched `screen/` checkpoint tree from its declared
predecessor before `--resume`. Kimi Linear remains blocked from this generic
path because its custom code is not reviewed; Kimi K2.6 stays in the hosted and
Tinker lanes.

Contained discovery loaded Qwen3.5 4B/9B and Qwen3.6 35B-A3B from pinned local
artifacts. The 4B 200-task cell missed the 80% competence gate. The 9B cell
passed overall served competence but missed per-stratum and AIPW-to-paired
agreement gates. The 35B four-task interface cell loaded successfully, but its
200-task continuation failed same-arm A/A replay. A 4B recency cell failed the
same replay check. These are preserved negative transport results; none may
enter a 2,400-task confirmation wave until replay is fixed and a clean retained
source archive, SBOM, and contained test-suite receipt are bound. Discovery jobs
122 and 124 now bind retained dirty-tree archive `a3aa58e8…` and image
`sha256:51067ef7…`: job 122 proves Mem0 native persist/restart/divergence-
rejection/purge behavior, while job 124 passes compile, the 92-source ledger, all six memory
contracts, provider validation, and the reference transport doctor. They remain
discovery evidence, not publication provenance, because the source is not a
clean commit and the image has no SBOM.

The repair path is now executable but unrun. The strict replay doctor fixes
`CUBLAS_WORKSPACE_CONFIG`, deterministic Torch algorithms, eager attention,
TF32 and reduced-precision reductions; records prompt and completion token-ID
hashes plus the resolved device-map hash; and persists both outcomes before any
A/A abort. Its registered kill cell executes tasks 0, 4, 106, and 180 across
seeds 42/43/44, three repeats, and two cold model loads, bounded to 2×H100 for
two hours on Qwen3.6 35B-A3B. Passing local tests establish only the contract;
the doctor still requires a clean commit, retained archive, image, SBOM, and
Slurm receipt.

The public-source interface has also moved forward: the pinned LongMemEval
cleaned oracle converts all 500 tasks into 495 content-addressed groups with a
candidate rule that cannot read the future question, answer, `has_answer`, or
answer-session labels. The corrected oracle-context adapter manifest hashes to
`c8180436…`; its balanced 32-task transport panel hashes to `ad8bc80e…`. This is a
source-conversion receipt, not public-benchmark model evidence.

### Stage 1d — matched full-benchmark retrieval floor

Before any graph, active/inactive pager, consolidation manager, or learned
memory controller receives additional GPU time, run the same all-SERVE actor
and official semantic judge on the complete 500-task LongMemEval roster for:

1. no memory;
2. BM25 raw evidence;
3. dense BGE raw evidence;
4. raw-log RRF; and
5. MemPalace raw user-session MiniLM retrieval.

All arms use the same Qwen3.6-35B-A3B receipt, prompt, decoding, source/task
manifest, top-4 retrieval, 256 injected-token cap, and task order. The
full-prefix 32,768-token arm remains a separately labeled diagnostic ceiling.
The official semantic judge is run only after actor bundles are sealed, and the
comparison is task-paired with session-clustered uncertainty.

The current-lock MemPalace upstream reproduction is exact across two fresh
500-task runs: custom recall-any is 96.6% at five and 98.2% at ten; the official
non-abstention recall-all recomputation is 85.7447% at five and 93.4043% at ten.
A contained one-H100 direct-versus-port audit matched all 500 query/session
rosters, texts, full rankings, and top-k projections and a fresh resume
verification preserved every artifact hash. These are retrieval and transport
receipts only. They are discovery evidence because the source/runtime trust
chain is self-attested and the working tree is not publication-clean.

The next actor cell is therefore the full-500 MemPalace arm: CPU-only frozen
selection, then at most two H100s for four hours (eight H100-hours). Kill the
branch if direct/port equivalence or repeatability fails, or if its official
semantic accuracy does not beat the strongest flat comparator with a 95%
session-clustered interval excluding zero. A win establishes a required simple
floor, not evidence for paging, graphs, consolidation, procedural memory,
causal credit, or safety.

After the flat quality matrix, use PAST-Bench for longitudinal pathway claims.
Its persistence-on/off sequences and save/retrieve/reuse/update evidence are
the relevant external test for active/inactive paging and procedural reuse;
LongMemEval alone cannot support those claims.

The PAST-Bench source admission path is executable without importing upstream
code. `scripts/validate_past_bench_source.py` binds the Apache-2.0 checkout at
`f8223517…`, its Git tree/archive, 26 declared families, 204 ordered episodes,
task fixtures, reference manifests, fresh-session flags, persistence controls,
and the seven extra update-family task directories excluded from the runnable
roster. `scripts/prepare_past_bench_runtime.py` separately binds all 31 direct
PAST core/mock plus Hermes+ requirements to 106 locked packages, an exact
Linux/amd64 Python base manifest, the upstream-declared 36-file test roster,
and a complete 2,159-file source context. The locked CPU suite passes 376 tests
with two skips. Slurm discovery job 217 reproduced that roster inside candidate
image `sha256:6184c956…` and passed a network-none, read-only, non-root container
doctor. This remains runtime evidence only: the first model cell is still
blocked on an image-bound SBOM, atomic checkpoint/resume proof, and a contained
same-job model transport. Upstream's unsupported nested runtime-container mode
is not part of the design.

### Stage 2 — learned controller, only after Stage 1 passes

Train only discrete memory decisions using cross-fitted causal targets. Match
next-use and observational-label controls on examples, parameters, training
steps, and tokens. Tinker can train the external controller; it cannot test a
claim about mutable hidden state or a new sequence operator.

Kimi is a confirmation path, not the first run:

- use Tinker-supported Qwen for the interface and resume smoke;
- use a current Kimi target only after the Qwen cell passes;
- keep the open Kimi Linear 48B checkpoint as a separate 8×H100 long-context
  diagnostic after its custom code is reviewed and vendored.

## Causal Memory Holdout overlay

For each episode's single eligible item:

1. Freeze and hash the prefix, candidate, model state, memory state, and
   deterministic tool/RNG tape.
2. Compute a propensity from write-time/past-only fields.
3. Sample `SERVE` or `HOLDOUT` exactly once and durably commit the assignment
   before model continuation.
4. Execute the observed arm.
5. On the registered audit subset, restore the identical snapshot and execute
   the opposite arm.
6. Reject any paired trace with non-treatment divergence.
7. Fit cross-fitted AIPW targets, train the gate without audit or test rows,
   and evaluate on sealed task families.

The narrow novelty claim is prospective first-eligible-use assignment with
known propensity, executable downstream utility, paired replay audit, and a
strictly past-only deployment gate. Query-time inclusion/exclusion, learned
CRUD, and future-label distillation are explicit controls.

## Metrics and falsifiers

Primary outcome: paired executable success difference between the causal gate
and the strongest nonrandom learned control at `K=4`.

Promotion requires all of:

- at least 3.0 percentage points improvement;
- family-clustered paired 95% confidence interval excluding zero;
- AIPW-to-paired ATE gap at most 0.05;
- pseudo-outcome/oracle and policy/oracle Spearman at least 0.20;
- total effective sample size at least 400 and each arm at least 100;
- stable policy value and calibration at all three propensities;
- no replay, lineage, isolation, checkpoint, or safety failure.

Report exact task success, tool/schema correctness, update/delete and temporal
accuracy, abstention, evidence recall@4 and MRR, unnecessary-injection rate,
success per injected token, tokens, bytes, reads, writes, p50/p95 latency, cost,
and every safety failure.

Kill or narrow the direction if:

- `raw-log-rrf`, `profile-expansion`, or a paper-faithful ReFind/ProGraph cell
  ties the graph arm on
  temporal/update tasks at equal bytes, calls, tokens, and wall time;
- proactive injection fails to beat both random injection and reactive recall
  at equal mean injected tokens;
- next-use or observational utility matches the causal gate;
- the policy lift disappears under task-family or model transport;
- trial/replay cost exceeds saved context and retrieval cost;
- any prompt injection, PII canary, deletion, or cross-user isolation red line fails.

A clean null is publishable.

## Safety and leakage controls

- Treat every retrieved memory as untrusted data, never as a system instruction.
- Include stored prompt injections, malicious tool output, stale permissions,
  PII canaries, delayed activation, deletion, and cross-session probes.
- Counterfactually rename entities and swap answer values; require the answer to
  track the evidence and collapse when evidence is removed.
- The controller cannot see future query, suffix, answer, tool result, or
  corruption label.
- Hash complete rendered inputs and compare replay traces event by event.
- Evaluate both immediate utility and later attack surface; success alone is
  not sufficient.

## Reproducibility contract

Every run records dataset repository and file hashes, model receipt, source and
image digests, exact JSON argv, split manifest, rendered prompts/token IDs,
memory mutations and retrievals, durable assignments, model output, tool trace,
paired replay, nuisance folds, policy artifact, cost ledger, and safety report.

Checkpoint only at episode boundaries, at most every ten minutes, and on the
preemption signal. Persist completed task IDs, assignment RNG state, task and
split hashes, model/decode receipt, complete active/archive/graph state, policy
state, artifact offsets, and predecessor job ID. Keep two validated generations
and prove a fresh job produces a byte-identical continuation.

Use tmux only for operator durability. Publication jobs remain scheduler-owned,
containerized, digest-pinned, and checkpointed on persistent storage. Imported
models must be bound to `models/registry.yaml`; hosted models must pass the live
identity controls in `models/provider-registry.yaml` before every wave.

## Native open-source system reproduction

Mem0, Graphiti, LangMem, and Hindsight now have a shared registered comparison
contract at `experiments/memory/stage2-oss-baselines.yaml`. The harness owns a
versioned ordered event surface, requires exact source attribution, charges
construction and service costs, and refuses to pool the end-to-end
storage-plus-service effect with the narrower serve-only effect. The current
request still exposes benchmark stratum to sidecars, so it must not be called
task-blind until that field is removed or explicitly justified.
Deterministic recency, lexical, and temporal-graph implementations pass this
contract over both in-process and JSON subprocess transports.

Mem0 adapter v2 now maintains session-scoped Qdrant/SQLite state across sidecar
processes, uses an fsynced idempotency journal, rejects divergent prefixes, and
performs native delete/reset before removing only the hashed scope. Contained
Slurm job 122 verified 27 committed events, 26 native records, identical evidence
and journal hashes across restart, rejected a byte-divergent committed prefix
without changing the journal, and found zero live state after purge plus another
restart. Graphiti, LangMem, and Hindsight still reconstruct ephemeral stores,
and none of the four has passed the matched cross-tenant, poisoning, repair, or
200-task quality matrix. All remain `publication_ready=false`.

Exact clean-source/API/license preflight passes for all four systems. The first
real native execution used reviewed Mem0 2.0.18 source, Qdrant, raw `infer=False`
writes, and a deterministic embedding interface smoke. It ingested 32 archive
prefix events, returned four attributed records within 180 estimated injected
tokens, and matched normalized evidence across repeated A/A runs in all four
estimand/visibility cells. Its sealed artifact is
`63cdafdf5ac0fefe26c8b1b2a7873697cee763d9bc066370f31abb21180b74a5`.
This one-task artifact remains native API/protocol evidence only. The later
contained lifecycle pass adds Docker/Slurm restart and deletion conformance, but
still no semantic-quality or actor-outcome comparison. Full methodology and
source hashes are in `research/memory-oss-reproduction-2026-08-11.md`.

The second real native execution used reviewed Graphiti 0.29.3 with embedded
FalkorDBLite 0.10.0, explicit temporal triplets, deterministic embeddings, and
a deterministic deduplication fixture in place of the construction LLM. Both
estimands and their A/A repeats returned source-attributed edges within the
token budget. It also exposed a systems cost that must remain in the comparison:
171–180 embedding operations and 20.9–21.8 seconds full isolated-process
latency per selection. Artifact
`60aeb4c68f6809d2c8f4cc61553c827a468bd87be085d100140d9879d57da06f`
is interface evidence only, not a Graphiti quality result.

The third native execution used reviewed LangMem 0.0.30 and LangGraph's indexed
in-memory store through LangMem's public manage/search tool APIs. Native
create/update/delete/search operations retained exact source attribution and
passed both estimands, both arms, and all semantic A/A repeats. Candidate-
present cells made 33 embedding calls, returned four records within 233 tokens,
and took 2.87–3.62 seconds per full isolated-process selection. Artifact
`494903d6f797f28d1abc32d9a49a7dc53111bbc8b7b42c6224bff907bad39e4a`
is interface evidence only. The LLM background manager is deliberately deferred
to the matched common-construction-model cell.

The fourth native execution used reviewed Hindsight 0.9.0 in its LLM-free
chunk retain/recall mode with pg0-embedded 0.15.1 and RRF passthrough. Both
estimands, both arms, and all semantic/rank repeats passed. Candidate-present
cells used 33 embedding inputs, returned four records within 234 tokens, and
took 30.1–33.8 seconds per first isolated selection. Final scores exhibited
small time-based recency drift below `1.94e-7`, now recorded under a `1e-5`
A/A tolerance. Artifact
`6898f0e75c0da7ec6077217b283d78c2ed1dc19e0fb196c9bbac6489fedbde22`
is interface evidence only. Hindsight's full extraction, graph, consolidation,
and reflect path still requires the matched construction-model cell.
