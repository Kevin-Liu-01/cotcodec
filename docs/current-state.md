# Current research state

Snapshot: 2026-08-31

## Program status

CoTCodec remains in the foundation and falsification phase. The harness is the
primary instrument; Paper 1 still studies language as an explicit orchestration
variable, while the memory program supplies revision-specific lifecycle and
mechanism controls. No lower-level pass is promoted into a semantic or
publication claim.

| Surface | Current state | Consequence |
|---|---|---|
| Paper 1 harness | Deterministic canary and two-stage CPU runner gates admitted | Live comparative H100 work remains closed |
| Frozen OrchVar live job 341 | Incomplete at 2/6, 0/2 completed-cell success, safety unreached | Never resume, rerun, or backfill |
| Memory source ledger | 229 sources, 182 pinned repositories, 1 scientific reproduction, 3 conformance reproductions, 38 reproduced negatives | Matrix `a0cb79fb…` is current |
| Memory portfolio | 93 candidates, six waves, 84 maximum H100-hours | Killed revisions are excluded from execution order |
| Frontier radar | Last durable scan predates this checkpoint | Run the next dated scan before revising the proposal landscape |

## Latest completed gate: legacy Letta V1

Legacy Letta V1 revision
`ff19ffeafeb54bd2a7dc5d4a552f10191732a235` / tree
`675c06071568dd48ca9b16b755041937286b7d95` is actor-blocked.

Slurm job `351` ran two fresh PostgreSQL states in the digest-pinned official
0.16.8 image with four CPUs, 16 GiB, network disabled, zero GPUs, and zero model
or provider calls. The image's tested `/app` files hash-matched the exact source.
Provider-free construction, normal core/archive CRUD, organization isolation,
fresh-process restart, and explicit logical deletion passed. The same two states
reproduced:

- HTTP 500 after a core block mutation had become durable but before the
  compiled prompt reflected it;
- two durable passages after a payload-equivalent archival retry;
- archive, passage, and block retention after deleting their agent; and
- every deleted canary in stopped PostgreSQL heap and WAL after public logical
  deletion reduced current passage and block counts to zero.

The stable projection is
`25b09cf3288e045afcb71908b03af97f898dab2ea8921e64506ba8d5234a8f3a`.
The portable receipt is
[`research/evidence/memory/memgpt-letta-native-lifecycle-negative-v1.json`](../research/evidence/memory/memgpt-letta-native-lifecycle-negative-v1.json)
and the interpretation is
[`research/memgpt-letta-native-lifecycle-audit-2026-08-31.md`](../research/memgpt-letta-native-lifecycle-audit-2026-08-31.md).

Jobs `348`–`350` remain pre-result launch or instrumentation diagnostics. They
are not included in the decision.

## Recent memory gates

| System and pin | Result | H100 admission |
|---|---|---|
| MemForest `fb4320a` | Unconfined tenant paths and torn multi-file snapshot | Forbidden |
| Infini Memory `ddac08e` | Unconfined/destructive user path plus non-atomic Markdown/index lifecycle | Forbidden |
| Mnemo Cortex `8a0cff9` | Partial Passport writes, duplicate retry, no native primary-memory purge, unlocked upstream | Forbidden |
| Legacy Letta V1 `ff19ffe` | Split core update, duplicate archive retry, agent-delete retention, stopped-PostgreSQL residue | Forbidden |

These are lifecycle, storage, and component observations. None measures semantic
memory quality, autonomous paging value, live-model behavior, or secure media
erasure.

## Active next gates

1. Preregister a separate exact-source CPU lifecycle doctor for current Letta
   Code `a575e11753943d9a4e18373a8817eb16a5b76b47` and its local MemFS mechanism.
   Do not treat it as a legacy-server repair. Bind construction, scope/isolation,
   restart, retry/idempotency, delete/purge/residue, and matched cost surfaces
   before considering an actor.
2. Preserve the closed OrchVar H100 state. A CPU repair does not rescue frozen
   job 341; the next live hypothesis requires a new preregistered contract.
3. Run the overdue dated frontier scan and brief the advisor on material August
   changes before revising Paper 1 settings.
4. Before any larger claim wave, replace dirty discovery provenance with a clean
   source archive, immutable OCI image and SBOM, complete controls, protected
   external attestation, and validated checkpoint/resume.

## Refresh commands

```bash
uv run python scripts/validate_memory_experiments.py
uv run python scripts/validate_memory_sources.py
uv run python scripts/validate_memory_portfolio.py
uv run python scripts/seal_memgpt_letta_lifecycle_evidence.py --validate-only
uv run pytest -q
uv run ruff check harness scripts tests
node scripts/run-agent-docs.ts doctor .
```

Compiled machine state lives in [`memory.json`](../memory.json); chronological
observations live in [`wiki/log.md`](../wiki/log.md). This page is rewritten
when either changes.
