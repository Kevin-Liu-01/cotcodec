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

## Experiment tree and retrieval: OpenResearch (`orx`)

[alphaXiv/OpenResearch](https://github.com/alphaXiv/OpenResearch) (MIT) is
installed as `~/.cargo/bin/orx`, built from source at tag `v0.2.2`
(`cargo build --release --locked`; source builds send no analytics —
`orx telemetry status` reports "off (development build)"). Rebuild from a newer
tag deliberately; never use the `curl | sh` installer on a research machine.

What it is here:

- **Retrieval modality.** `orx discover keyword|embedding|openalex` and
  `orx paper <id> [--full]` reach alphaXiv, OpenAlex, and arXiv PDFs from the
  development Mac, where the arXiv API and Semantic Scholar are blocked. The
  gauntlet rule requires them for every novelty ledger.
- **Experiment-tree ledger.** The repository is registered as an orx project
  (`orx projects`). Every node runs the single fixed command
  `uv run --locked python scripts/orx_run.py` over the committed
  `experiments/orx/node.yaml` on its own `orx/<slug>` branch. Runs execute an
  immutable snapshot of the recorded commit; uncommitted files never run. The
  run log (`orx logs <runId>`) is the evidence channel.
- **Not a bypass.** `node.yaml` admits two kinds only: `cpu-doctor`
  (a registered `scripts/run_*_doctor.py`) and `slurm-manifest` (a committed
  `experiments/**.yaml` submitted through `scripts/submit_docker_research_job.py`
  with dry-run, test-only, then submit). GPU work is never launched with
  `--backend slurm`, which stages a plain checkout outside the digest-pinned
  image and the receipt contract.

Daily use:

```bash
orx up --no-browser --no-agent          # local server + dashboard at http://127.0.0.1:4791
orx projects                             # project id
orx project view <projectId>             # tree, experiment ids
orx create-experiment <projectId> --title "<direction> phase-0 doctor" --baseline
git worktree add /tmp/orx-wt/<slug> orx/<slug> && $EDITOR /tmp/orx-wt/<slug>/experiments/orx/node.yaml
git -C /tmp/orx-wt/<slug> commit -am "orx node: <what this node tests>"
orx exp run <expId> --backend local      # CPU doctors; --backend ssh --host kevin@207.241.191.91 for slurm-manifest nodes
orx exp wait <expId> && orx logs <runId>
```

Cardinal rules (from the tool, adopted verbatim): never edit a node once a run
has answered it; the run command and environment are a fixed contract; vary
committed code, not knobs in the command; grow the tree downward onto winners.

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
