# CoTCodec handoff

Updated: 2026-09-01

This file is a stable continuation pointer, not a duplicate operating manual.

## Read order

1. [`wiki/SOUL.md`](wiki/SOUL.md), [`wiki/USER.md`](wiki/USER.md), and
   [`wiki/HEARTBEAT.md`](wiki/HEARTBEAT.md)
2. [`memory.json`](memory.json)
3. [`docs/current-state.md`](docs/current-state.md)
4. [`docs/memory-handoff.md`](docs/memory-handoff.md) for memory work,
   [`docs/h100-operator-runbook.md`](docs/h100-operator-runbook.md) for compute, or
   [`research/frontier-systems-program-2026-09-01.md`](research/frontier-systems-program-2026-09-01.md)
   and [`docs/local-model-lab.md`](docs/local-model-lab.md) for the architecture program
5. [`AGENTS.md`](AGENTS.md) and the nearest directory `SKILL.md`
6. The exact experiment, evidence bundle, and validator for the next queue item

## Current continuation

- The 2026-09-01 frontier sweep and five research-gauntlet waves are sealed (exit 5 fired at 66 → 65 → 65):
  scan `research/scans/2026-09-01.md`, program
  `research/frontier-systems-program-2026-09-01.md`, ledgers
  `research/gauntlet/2026-09-01-frontier/`, audit
  `data/research-gauntlet/2026-09-01-frontier.jsonl`. Four preregistered
  directions (19–22) exist with proposals, validator-passing contracts, and
  executable CPU phase-0 doctors (`scripts/run_*_doctor.py`); none is
  pilot-ready (best 66/100; doctor FAIL by construction). The next executable
  step is the compiled `qwen3.5-4b-base` discovery manifest (see the program's
  "Next executable steps"). Follow
  `.claude/rules/research-gauntlet-loop.md`.
- Inputs resolved or re-scoped 2026-09-01: the parallel-corpus inventory is
  sealed (`research/data/gt-parallel-corpus-inventory-2026-09-01.md`; customer
  translation memory excluded by ToS §3.1; pilots run on public corpora);
  `MOONSHOT_API_KEY` is set locally (kimi-k2.6 served; balance 0 → recharge
  before any Kimi cell); `TINKER_API_KEY`/`HF_TOKEN` still need Kevin's clicks
  (`~/.config/cotcodec/secrets.env`); root for the Slurm/Pyxis upgrade still
  needs a password.
- Stage 0 on `fal-h100-01`: image `cotcodec-research:999f5583-architecture`
  (fla 0.5.2) built; ten pilot checkpoints fetched with receipts; measured
  eager throughput 282k tok/s (134M) / 73k tok/s (422M) on the tilelang image
  `0b3ecef0-architecture` (`research/evidence/infrastructure/fla-throughput-h100-2026-09-01.json`).
  Entry points: `infra/slurm/host-single-node/{build-architecture-image,fla-throughput-doctor,fetch-pilot-models}.sbatch`.
- Before any GPU-hour on directions 19–22: rebuild and digest-pin the image
  with `flash-linear-attention` 0.5.2, register the pilot checkpoints, compile
  job manifests, write and pass the CPU phase-0 doctors twice, and run one
  throughput job to replace the assumed MFU.

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
