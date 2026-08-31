# CoTCodec handoff

Updated: 2026-08-31

This file is a stable continuation pointer, not a duplicate operating manual.

## Read order

1. [`wiki/SOUL.md`](wiki/SOUL.md), [`wiki/USER.md`](wiki/USER.md), and
   [`wiki/HEARTBEAT.md`](wiki/HEARTBEAT.md)
2. [`memory.json`](memory.json)
3. [`docs/current-state.md`](docs/current-state.md)
4. [`docs/memory-handoff.md`](docs/memory-handoff.md) for memory work or
   [`docs/h100-operator-runbook.md`](docs/h100-operator-runbook.md) for compute
5. [`AGENTS.md`](AGENTS.md) and the nearest directory `SKILL.md`
6. The exact experiment, evidence bundle, and validator for the next queue item

## Current continuation

- The deterministic OrchVar execution, tool-error transport, full runner
  integration, and resume gates are admitted. Frozen live job 341 remains an
  incomplete negative and must not be repaired or backfilled in place.
- The memory-system queue is CPU-first and revision-specific. MemForest,
  Infini-memory, Mnemo Cortex, and legacy Letta V1 have sealed lifecycle
  negatives.
- Legacy Letta V1 job 351 is the complete two-state result. Jobs 348-350 remain
  pre-result diagnostics and must not be relabeled or overwritten. The receipt
  is `research/evidence/memory/memgpt-letta-native-lifecycle-negative-v1.json`.
- The next native gate is a distinct exact-source CPU lifecycle contract for
  current Letta Code MemFS. It is not a repair arm for the legacy V1 server.
- No memory lifecycle result admits semantic quality, autonomous paging, or H100.
- No new memory H100 job is admitted. The eight-GPU host is reachable and idle,
  but its current Slurm 21.08.5/cgroup-v2 configuration is discovery-only and
  lacks the Pyxis interface required by the publication batch contract.

## Exact operator routes

- Memory evidence and the next falsifiers:
  [`docs/memory-handoff.md`](docs/memory-handoff.md)
- Current H100 state, discovery submission, and publication upgrade work:
  [`docs/h100-operator-runbook.md`](docs/h100-operator-runbook.md)
- Raw-data retention and portable-evidence boundaries:
  [`docs/data-policy.md`](docs/data-policy.md)

## Before changing anything

```bash
git status --short --branch
uv run python scripts/check_harness_env.py
uv run python scripts/validate_memory_experiments.py
```

Do not reset, restore, or delete work you did not create. Local `data/` contains
large ignored models, source trees, databases, and build artifacts; it is not a
Git staging target.

## Writeback

When a result changes project truth:

1. Seal the portable evidence and validate it independently.
2. Update `research/memory-sources.yaml` and the portfolio when applicable.
3. Update compiled state in `memory.json`.
4. Append the immutable observation to `wiki/log.md`.
5. Refresh `docs/current-state.md` and Agent-Docs.
6. Report exactly what passed, failed, and remains out of scope.
