# Memory research handoff

Snapshot: 2026-08-31

This is the exact continuation point for CoTCodec's memory-policy program. It
separates executed evidence from source-derived hypotheses so the next operator
does not accidentally convert a code-reading observation into a result.

## Authoritative state

| Surface | Current value |
|---|---|
| Source ledger | 229 sources, 182 pinned repositories, 7 pinned artifacts |
| Reproduction ledger | 1 scientific, 3 conformance, 38 negative findings |
| Portfolio | 6 waves, 93 candidates, 13 license-blocked candidates |
| Maximum registered H100 budget | 84 H100-hours across the portfolio |
| Portfolio matrix | `a0cb79fb0e80aee8e0efd106150fb9ac94bdc85262e4570a60d97b204a7e193f` |
| New memory H100 admission | None; every next actor requires a new passing CPU gate |

The authoritative machine-readable owners are
[`research/memory-sources.yaml`](../research/memory-sources.yaml) and
[`research/memory-experiment-portfolio.yaml`](../research/memory-experiment-portfolio.yaml).
Run both validators before trusting the counts.

## Latest sealed result

Legacy Letta V1 revision
`ff19ffeafeb54bd2a7dc5d4a552f10191732a235`, tree
`675c06071568dd48ca9b16b755041937286b7d95`, is blocked from an actor run.
Slurm job 351 is the only decision-bearing run. Jobs 348–350 are retained
pre-result diagnostics and must not be relabeled.

Job 351 used 4 CPUs, 16 GiB RAM, zero GPUs, network disabled, and zero provider
or model calls. Both fresh PostgreSQL states passed provider-free construction,
normal core/archive CRUD, organization isolation, restart, and logical deletion.
Both also reproduced a durable partial core update, payload-equivalent archival
duplication, agent-delete resource retention, and plaintext residue in stopped
PostgreSQL heap and WAL.

- Portable receipt:
  [`research/evidence/memory/memgpt-letta-native-lifecycle-negative-v1.json`](../research/evidence/memory/memgpt-letta-native-lifecycle-negative-v1.json)
- Audit:
  [`research/memgpt-letta-native-lifecycle-audit-2026-08-31.md`](../research/memgpt-letta-native-lifecycle-audit-2026-08-31.md)
- Ignored local raw run:
  `data/results/memgpt-letta-lifecycle/2026-08-31-slurm-cpu-v4/`
- Remote raw run:
  `/home/kevin/cotcodec-runs/memgpt-letta-lifecycle/2026-08-31-slurm-cpu-v4/`

Do not rerun the legacy revision or reinterpret this as semantic memory-quality,
autonomous paging, managed-cloud, concurrency, or secure-media-erasure evidence.

## Exact next gate: current Letta Code MemFS

Current Letta Code is a separate mechanism, not a repair arm for legacy Letta:

| Field | Bound value |
|---|---|
| Repository | `https://github.com/letta-ai/letta-code` |
| Revision | `a575e11753943d9a4e18373a8817eb16a5b76b47` |
| Tree | `9bb2cadf097f522bdcbc09fe0268dd6dd82bb410` |
| Source archive SHA-256 | `d81b210456b049a09d1a98618846273c7f41aadd63e4873fa796ecab20db9bd9` |
| Source archive bytes | 50,759,680 |
| Local archive | `data/results/memgpt-letta-lifecycle/2026-08-31-slurm-cpu-v4/letta-code-source.tar` |
| Remote checkout | `/home/kevin/cotcodec-build-inputs/memgpt-letta/letta-code-source` |
| Remote archive | `/home/kevin/cotcodec-build-inputs/memgpt-letta/letta-code-source-a575e11.tar` |

No lifecycle result exists for this mechanism yet. The following are
source-derived preregistration inputs, not findings:

- `resolveScopedMemoryDir()` maps agent IDs to local roots and accepts an
  explicit memory-directory fallback.
- the public `memory()` tool mutates a Markdown file before
  `commitMemoryWrite()` attempts its Git commit;
- failed Git commits unstage the path but the inspected source does not visibly
  roll the working-tree mutation back; and
- local `deleteAgent()` removes local agent records, while the inspected path
  does not visibly remove the agent's Git-backed memory root.

The doctor must test these facts rather than assume they are bugs.

### Required controls and falsifiers

Run two fresh local-backend states. Use the exported/public memory tool and
native agent lifecycle surfaces wherever possible.

1. Construction: initialize an empty agent-scoped Git memory repository.
2. Normal CRUD: create, replace, insert, rename, update description, delete,
   and verify one Git commit per effective operation.
3. Isolation: create two agent IDs and prove neither can read or mutate the
   other's root through relative, absolute, traversal, or alias paths.
4. Symlink confinement kill test: place a controlled symlink inside one memory
   root pointing to an outside canary. Public create/update/delete must reject
   the path and leave the outside bytes unchanged.
5. Restart: reconstruct the runtime in a fresh process and verify head, bytes,
   metadata, and visible memory are identical.
6. Commit-failure atomicity kill test: inject a deterministic Git-commit
   failure after the file operation. A rejected tool call must leave HEAD,
   index, working tree, and target bytes equal to the pre-call state.
7. Retry/idempotency: retry the identical logical operation after the injected
   failure and after success. It must not create an extra commit, strand a dirty
   tree, or make the requested state unrecoverable.
8. Agent deletion: delete the agent through the native local-backend surface,
   restart, and measure whether its memory root and plaintext remain.
9. Explicit purge/residue: if a documented purge exists, execute it and scan
   the stopped Git worktree, object database, reflogs, and adjacent local state
   for unique canaries. Logical deletion is not secure erasure.
10. Cost: record matched wall time, Git subprocess count, bytes written, commit
    count, and repository growth for every control and retry path.

### Files the next implementation should add

Use these names unless source inspection invalidates the boundary before any
treatment result is observed:

- `experiments/memory/stage3-letta-code-memfs-lifecycle-doctor.yaml`
- `infra/memory-baselines/letta-code-memfs/doctor.ts`
- `infra/slurm/host-single-node/letta-code-memfs-lifecycle.sbatch`
- `scripts/validate_letta_code_memfs_lifecycle_experiment.py`
- `scripts/run_letta_code_memfs_lifecycle_doctor.py`
- `scripts/seal_letta_code_memfs_lifecycle_evidence.py`
- `tests/test_letta_code_memfs_lifecycle_doctor.py`
- `tests/test_letta_code_memfs_lifecycle_evidence.py`

The contract must bind the source archive, Bun/Node runtime, lockfile, Git
binary, execution hashes, two fresh output roots, zero GPUs, zero provider
secrets, zero model calls, and terminal projection before execution.

### Admission rule

Any path escape, partial rejected write, non-idempotent retry, cross-agent
visibility, restart drift, undeclared residual ownership, missing purge, or
unstable matched-cost accounting blocks this exact revision from an H100 actor.
A passing lifecycle doctor only permits a separately preregistered quality
screen; it does not establish useful memory.

## Completed H100 memory work that stays closed

Prior H100 discovery screens for Mnemon, MemoryBank, GAAMA, and related cells
are historical results. Their receipts and portfolio rows own their terminal
decisions. Do not resume them, enlarge their models, or use a CPU repair to
reopen them. Frozen OrchVar job 341 is likewise closed and incomplete.

## Verification commands

```bash
uv run python scripts/validate_memory_experiments.py
uv run python scripts/validate_memory_sources.py
uv run python scripts/validate_memory_portfolio.py
uv run python scripts/seal_memgpt_letta_lifecycle_evidence.py --validate-only
uv run pytest -q tests/test_memory_sources.py tests/test_memory_portfolio.py \
  tests/test_memgpt_letta_lifecycle_evidence.py
```

If the ledger, matrix hash, source pin, or legacy receipt differs, stop and
resolve the drift before submitting anything.
