# Research operations

This is the operator path from a proposed intervention to durable evidence.
Project-specific invariants remain authoritative in [`AGENTS.md`](../AGENTS.md)
and the nearest `SKILL.md`.

## Session start

```bash
git status --short --branch
uv run python scripts/check_harness_env.py
uv run python scripts/validate_memory_experiments.py
```

Read `wiki/SOUL.md`, `wiki/USER.md`, `wiki/HEARTBEAT.md`, `memory.json`, and
[`current-state.md`](current-state.md) before changing the queue. Report stale
or failed gates first.

## Experimental loop

```mermaid
flowchart LR
  Q[Question] --> S[Exact source + revision]
  S --> C[Preregistered YAML]
  C --> V[Static validator]
  V --> T[Unit and tamper tests]
  T --> R[Fresh versioned run]
  R --> M[Manifest + receipts]
  M --> E[Portable evidence sealer]
  E --> W[Registry and state writeback]
```

The contract names positive controls, falsifiers, budgets, stop conditions, and
the claim boundary before execution. A failed prerequisite is retained as a
pre-result diagnostic. A completed negative is a scientific result when the
falsifier and controls are both valid.

## Local and remote execution

Use local CPU or container execution for validators, deterministic mechanisms,
and lifecycle falsification. Use the remote Slurm host only for a registered
resource class. Submit long work from a durable `tmux` operator session; Slurm,
not `tmux`, owns the workload after `sbatch`.

```bash
bash scripts/tmux-research-session.sh cotcodec
ssh <research-host>
sbatch infra/slurm/host-single-node/<contract>.sbatch
```

Every attempt gets a new stage directory and output directory. Never repair,
delete, or overwrite an older run in place. Preserve the command, job ID,
source receipt, code hashes, stdout/stderr, and whether failure occurred before
or after the scientific phase.

## Resource admission

- CPU doctors must not silently receive provider secrets, network access, GPUs,
  or unregistered dependencies.
- H100 work begins only after the exact revision passes all cheaper admission
  gates and the contract states why GPU execution identifies a new quantity.
- A GPU allocation with no model execution is infrastructure evidence, not a
  model-quality result.
- Publication claims require more than a completed job: provenance, restart,
  safety, and independent review remain separate gates.

## Checkpoint and restart

Long-running workloads checkpoint atomically to persistent project or scratch
storage. Retain at least two validated generations and bind model/adapter state,
optimizer, scheduler, scaler, RNG states, data cursor, step, config, source and
model hashes, and parent job ID. A workload is not queue-ready until a fresh job
restores the checkpoint and matches an uninterrupted continuation.

## Research skill packs

Two external packs back the research gauntlet's doctors (see
`.claude/rules/research-gauntlet-loop.md`, "External protocols"):

- **K-Dense scientific-agent-skills** (MIT/Apache-2.0) — a curated subset is
  vendored in `.claude/skills/` with provenance in `.claude/skills/README.md`
  and bridged from `.agents/skills/`. Re-vendor from upstream rather than
  editing in place.
- **Academic Research Skills** (Imbad0202, CC-BY-NC-4.0) — not vendored;
  enabled per user through the plugin marketplace declared in
  `.claude/settings.json`. First-time setup:

```bash
claude plugin marketplace add Imbad0202/academic-research-skills
```

```bash
claude plugin install academic-research-skills@academic-research-skills
```

  Modes used here: `/ars-fact-check` and `/ars-cite-check` for claim
  verification, `/ars-systematic-review` for PRISMA-style scans,
  `/ars-review-full` and `/ars-methodology` for proposal review.

## Closeout

1. Verify every manifest member and code hash.
2. Run the evidence sealer and its tamper tests.
3. Update the source and experiment ledgers.
4. Rewrite compiled state in `memory.json`.
5. Append the observation to `wiki/log.md`.
6. Refresh `docs/current-state.md` and `HANDOFF.md`.
7. Run the full checks in the nearest `SKILL.md`.
8. Inspect the staged diff for secrets, generated caches, and large files before
   committing and pushing.
