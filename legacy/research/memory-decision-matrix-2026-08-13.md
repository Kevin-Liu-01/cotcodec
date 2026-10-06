# Agent Memory Decision Matrix — 2026-08-13

**Cutoff:** 2026-08-13  
**Source ledger:** `research/memory-sources.yaml`  
**Portfolio:** `research/memory-experiment-portfolio.yaml`  
**Matrix SHA-256:** `7a2404c85c53cea216b980a832c7c715ad497ae71a993ab419ca4e11dbd1786b`

## Decision

There is no single “memory solution.” The 126-source landscape separates into
residency, representation, maintenance, service, learning, evaluation, and
safety choices. A graph can organize evidence but cannot decide when memory
should become active. An active/archive split can save context but does not
guarantee correct retrieval. A learned controller can choose operations but may
learn reward or benchmark shortcuts. A portable strap-on layer can transport
these choices but is not itself a scientific mechanism.

The research program therefore tests components and transitions, not brand
leaderboards. The primary unresolved question remains whether prospective,
known-propensity first-service trials produce a better past-only service policy
than matched noncausal and learned controls.

## Reproducibility state

| Evidence property | Current count | Interpretation |
| --- | ---: | --- |
| Primary-source records | 126 | Papers, official repositories, benchmarks, and system documentation. |
| Immutable repository records | 97 across 91 sources | Code provenance only; not proof that results reproduce. |
| Paper/page-only sources | 35 | Mechanism or collision evidence; no reusable implementation pinned. |
| Unresolved repository licenses | 29 | Code/data reuse remains blocked. |
| Explicit benchmark claims | 7 | Separately graded; none labeled locally reproduced. |
| Locally/externally reproduced source results | 0 | Interface and transport doctors do not become scientific reproductions. |

Regenerate the evidence views with:

```bash
uv run python scripts/validate_memory_sources.py --audit-json
uv run python scripts/compile_memory_landscape.py --format markdown --lane active-inactive
uv run python scripts/compile_memory_landscape.py --format markdown --lane temporal-graph
uv run python scripts/validate_memory_portfolio.py
```

## What the layers mean

| Lane | Sources | Meaning | What it does not establish |
| --- | ---: | --- | --- |
| Active context | 24 | Memory is directly visible or immediately actionable. | That active content is useful, safe, or worth its token cost. |
| Active + inactive | 21 | A system can move or coordinate information between prompt-resident and external states. | A new architecture; this pattern is already occupied. |
| Inactive archive | 81 | Information persists outside the current prompt. | That it will be found or activated at the right time. |
| Episodic | 106 | Events, traces, turns, or experiences are retained. | Correct abstraction, consolidation, or transfer. |
| Semantic profile | 89 | Facts, preferences, entities, or summaries are maintained. | Temporal validity or source authority. |
| Temporal graph | 40 | Evidence is related through entities, events, time, or typed edges. | A gain over flat retrieval at matched construction and service cost. |
| Procedural | 28 | Past experience becomes plans, policies, skills, or action templates. | Generalization outside matching task structure. |
| Latent state | 4 | Memory lives inside model/KV/recurrent state. | Portability to external agent memory or semantic CRUD. |
| Controller | 119 | Some policy chooses memory operations or retrieval. | A meaningful taxonomy by itself; nearly the whole field has a controller. |
| Benchmark | 24 | Released tasks or evaluation harnesses. | Correct causal identification or unbiased system comparison. |
| Safety | 14 | Authority, poisoning, isolation, deletion, or governance is tested. | Overall memory quality. |

## Notable active/inactive systems

### MemGPT / Letta

The clearest operating-system analogy: a small editable active core remains in
context while recall and archival data live outside it. It is the baseline for
self-managed paging, not a novelty candidate. The decisive test is whether the
model spends fewer tokens without losing task state or corrupting its own core.
Official Apache-2.0 code is pinned in the ledger.

### LightMem

Separates online active memory from offline consolidation. It is useful because
it makes the timing boundary explicit: immediate writes serve the live task,
while background work compresses history. Match construction calls, active
bytes, consolidation latency, and staleness before comparing quality.

### RecMem

Uses recurrence to trigger consolidation rather than consolidating every turn.
It is the right heuristic control for “move this from active to inactive now.”
Compare it with fixed-frequency consolidation and the proposed causal service
gate under identical evidence and costs.

### Unified Memory Agent and AgeMem

Both learn memory operations rather than using fixed rules. They occupy broad
learned active/inactive CRUD novelty. Their official repositories have unresolved
licenses, so the portfolio blocks code reuse until licensing is clarified.

### TiMem

TiMem makes time an explicit five-level hierarchy: factual segments are written
online, while session/day/week/profile memories consolidate on scheduled
boundaries. Query complexity controls which levels are searched and an LLM gate
filters recalled leaves and ancestors. It is now a mandatory scheduled-hierarchy
control, but its two benchmark scores and recall-length reduction remain
paper-reported; model-call cost and durable forgetting are unresolved.

### MemForest, Infini Memory, and DeltaMem

These occupy three different maintenance representations. MemForest refreshes
only dirty paths in temporal trees; Infini Memory rewrites buffered evidence into
readable topic documents; DeltaMem stores residual task/environment changes below
generalized roots. Compare them as localized-tree, topic-document, and residual
experience controls. DeltaMem code reuse is license-blocked. None decides the
prospective downstream value of making one memory active.

### MemPalace, ReMe, and agentmemory

MemPalace is the immediate raw-history/no-write-model falsifier: if a costly
extraction or consolidation system cannot beat its verbatim archive under the
same actor and judge, the transformation has no empirical case. ReMe adds a
readable Markdown authority layer, scheduled digests, wikilinks, and hybrid
graph search. agentmemory supplies the broad working-memory, consolidation,
decay, and forgetting lifecycle control. Only MemPalace enters the first wave;
the other two remain component controls until their locks, construction calls,
and coupled mechanisms are isolated.

The pinned MemPalace raw runner is narrower than its product: it joins only user
turns into one document per session and performs stateless MiniLM/Chroma
retrieval. Its released 483/500 headline is custom `recall_any@5`, not official
LongMemEval `recall_all@5`, and the artifact predates the current lock. The
source-derived mechanism port and artifact auditor now exist. The hash-verified
historical audit recomputes custom any-hit@5/10 as 96.6/98.2% and official
non-abstention all-hit@5/10 as 85.7447/93.4043% (NDCG 87.4322/89.0094%) over
470 tasks. Two identical current-lock runs and contained 500-task port
equivalence are now complete as discovery evidence. Promotion instead requires
a clean externally attested source/image/SBOM/runtime capsule and a single-load
500-task matched actor/judge matrix. It is not evidence for
paging, CRUD, graph, consolidation, persistence, or QA quality.

### PM-Bench

Tests the missing behavioral transition: an inactive intention must become
active at the correct time or event, sometimes only after proactively querying
a hidden channel; completed, canceled, and superseded intentions must stop
firing. Its deterministic runtime is ideal methodologically, but the repository
currently has no detected root license, so adapter work is blocked.

## Notable graph systems

### Graphiti

Incrementally builds a temporal entity/relation graph with episodes, provenance,
and validity intervals. It is the practical temporal-graph baseline already in
the interface-smoke ladder. Construction-model quality and graph retrieval must
be separated.

### SodaMem

[SodaMem](https://arxiv.org/abs/2608.08055) stores typed FactEvents with source
spans, mention/occurrence/validity time, and UPDATE/CONTRADICT/SUPERSEDE edges.
It retrieves citable evidence through hybrid lexical, dense, and graph search.
The Apache-2.0 repository is pinned at `b182c1a` and publishes LongMemEval
answers/evidence rows. Its reported 92.8% is still first-party, best-of-three,
self-judged with the same model, and excludes ingest/judge cost. Regrade the
frozen artifacts before any live comparison.

### MAGMA

Splits semantic, temporal, causal, and entity relationships into orthogonal
graphs with adaptive traversal. This is the multi-graph control. Construction,
router, traversal, and actor effects need separate ablations.

### ProGraph / MemHop

The critical graph-free control: profiles and residual evidence support
multi-hop traversal without a conventional graph database. A graph arm that
cannot beat it at matched bytes, calls, and wall time has no graph-specific case.

### MemGraphRAG

[MemGraphRAG](https://arxiv.org/abs/2606.00610) coordinates graph-construction
agents with shared schema, fact, and source-passage memory. It is useful for
testing memory during corpus graph construction, but it is not longitudinal
per-user agent memory. Keep it as a boundary diagnostic, not a primary system.

### UnifiedMem / “Does Memory Need Graphs?”

The mandatory controlled graph-versus-flat framework. Its repository license is
unresolved, so the official code cannot yet be imported. The experiment design
still governs every graph claim: align representation, maintenance, indexing,
retrieval, answering, and cost.

## Learned and procedural controls

- **LangMem:** agent-managed hot-path/background memory and procedural memory;
  already has an interface smoke, but its background manager needs a matched cell.
- **Memory-R1:** RL-trained ADD/UPDATE/DELETE/NOOP manager.
- **Memory-R2:** same-state local rerollout plus global reward; the closest open
  counterfactual CRUD-credit control.
- **MemCon:** online UCB over retrieve/inject/consolidate/forget/no-op; license-blocked.
- **Verifiable Memory:** executable local/global verification and hierarchical
  credit; license-blocked and not a turnkey reproduction.
- **MSCE:** converts selected experience into callable skills; important
  procedural collision, but paper claims remain unreproduced.
- **Acontext and memU:** editable procedural-skill files and portable shared
  Markdown skills; mandatory no-vector and cross-agent portability controls.
- **ReMemR1:** a learned callback/revisit ceiling for non-linear memory and
  active-state updates; not an item-level causal estimator.
- **Honcho and TencentDB Agent Memory:** multi-party representation and
  access-controlled multi-asset systems, relevant only when the claim expands
  to personalization, teams, or changing profiles.

## External validity and safety

Run external tasks in increasing-confound order:

1. LongMemEval with its official semantic judge, because the source adapter exists.
2. PM-Bench after license resolution, for activation/deactivation.
3. Mem2ActBench after license resolution, for exact tool and argument execution.
4. StreamMemBench after EgoLife terms are cleared, for feedback and later reuse.
5. EvoMemBench after license resolution, for task-scope/content heterogeneity and
   a strong long-context floor.

Safety is a separate wave: GateMem for multi-principal authorization/deletion,
TMA-NM for origin-bound authority, SMSR for randomized poison certificates, and
the sleeper-memory suite for delayed write-to-action attacks. An accuracy gain
cannot average away a safety red line.

## Bounded experiment portfolio

| Wave | Candidates | Maximum H100-hours | Stop rule |
| --- | ---: | ---: | --- |
| Native system spine | 10 | 32 | Stop after two candidate failures. |
| Active/inactive controls | 6 | 16 | Stop after two candidate failures. |
| Graph mechanism controls | 6 | 16 | Stop after two candidate failures. |
| Learned-controller controls | 4 | 16 | Stop after two candidate failures. |
| External validity | 4 | 16 | Stop after two candidate failures. |
| Safety and governance | 4 | 12 | Stop after two candidate failures. |
| **Total ceiling** | **34** | **108** | Blocked-license candidates consume zero until resolved. |

Every model-bearing screen is Docker-under-Slurm on H100, capped at eight
GPU-hours per candidate, and checkpointed. `tmux` is only the operator console.
No wave starts from a dirty or unretained source tree. The clean git archive,
dependency lock, OCI digest, SBOM, model receipt, task/split hash, exact argv,
allocation receipt, and checkpoint lineage must be retained.

## Discovery provenance

FieldTheory bookmark searches surfaced Hindsight, memory-to-skill interest, and
the production debate around temporal validity, proactive injection, and cost.
Local Search surfaced TiMem, MemForest, Infini Memory, DeltaMem, and H-Mem in
addition to SodaMem and MemGraphRAG. Independent official-repository discovery
added MemPalace, ReMe, agentmemory, Honcho, Acontext, memU, ReMemR1, and TencentDB
Agent Memory. Social posts and search snippets
were used only to find candidates. All promoted mechanism, result, repository,
revision, and license statements were checked against primary papers or official
repositories before entering the ledger.

## Immediate next decision

Do not launch the whole portfolio. First create clean source/image provenance,
replicate the strict Qwen 35B replay doctor, and run the existing frozen
LongMemEval controls through one identical actor. Run MemPalace as the raw-log
floor, then cheap lifecycle and released-artifact doctors for SodaMem, MemForest,
Infini Memory, and TiMem before
selecting at most one additional native actor cell. A null or failed system cell
is a stopping signal, not a reason to widen the sweep.
