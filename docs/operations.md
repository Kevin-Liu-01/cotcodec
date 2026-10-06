# Research operations

The operator path from a question to durable evidence. Host facts and the
admin list are in [`h100-node.md`](h100-node.md).

## Session start

```bash
git status --short --branch
uv run python scripts/check_harness_env.py
uv run python scripts/validate_architecture_experiments.py
```

Read `program/PROGRAM.md` and `program/state.json`. Report stale or failed
gates before changing anything.

## The loop

```
question -> preregistered contract (YAML) -> CPU doctor -> unit and tamper tests
  -> orx node -> Slurm dry-run -> fresh versioned run -> receipts -> state writeback
```

The contract names positive controls, falsifiers, budgets, seeds, stop
conditions and the claim boundary before execution. A failed prerequisite is a
pre-result diagnostic. A completed negative is a result when its falsifier and
controls are valid. Any new mechanism or any run over 8 GPU-hours first goes
through the gauntlet in `.claude/rules/research-gauntlet-loop.md`.

## Synchronize the host checkout

```bash
ssh <h100-alias>
cd ~/cotcodec
git status --short --branch
git fetch origin main
git merge --ff-only origin/main
```

Stop if the checkout is dirty or cannot fast-forward. Never reset or delete
remote run directories to make it pass.

## Submit a GPU job

Write a new manifest beside the experiment, filled from measured artifacts and
never from copied hashes. It needs the exact local image ID, the committed
revision and source-capsule SHA-256, model revision and receipt hashes,
persistent cache and run roots, exact argv, declared seeds, GPU count, and a
maximum GPU-hour budget.

```bash
uv run python scripts/submit_docker_research_job.py experiments/<manifest>.yaml --dry-run
uv run python scripts/submit_docker_research_job.py experiments/<manifest>.yaml --test-only
uv run python scripts/submit_docker_research_job.py experiments/<manifest>.yaml
```

Monitor without attaching the workload to SSH:

```bash
squeue -j <job-id>
scontrol show job <job-id>
```

Leaving the queue is not success. A run succeeds only with terminal
`JobState=COMPLETED` and `ExitCode=0:0`. Memory workloads from the old program
are archived; the submitter rejects them.

## Checkpoints

Every long workload checkpoints atomically to persistent storage: model and
optimizer state, scheduler, scaler, RNG states, data cursor, step, config,
source and model hashes, and parent job ID. Keep two validated generations. A
workload is not ready to scale until a fresh job restores the checkpoint and
reproduces the uninterrupted continuation (`resume_from_job_id`,
`resume_subpath`).

Run the operator session in tmux; Slurm owns the workload after submission.

```bash
bash scripts/tmux-research-session.sh cotcodec
```

## Experiment tree: OpenResearch (`orx`)

`orx` v0.2.2 is built from source at `~/.cargo/bin/orx` and sends no analytics.
Every node runs the single fixed command
`uv run --locked python scripts/orx_run.py` over the committed
`experiments/orx/node.yaml` on its own `orx/<slug>` branch. Two node kinds are
admitted: `cpu-doctor` (a registered `scripts/run_*_doctor.py`) and
`slurm-manifest` (submitted through the Docker submitter). Never launch GPU
work with `--backend slurm`; it bypasses the pinned image and receipts.

```bash
orx up --no-browser --no-agent
orx project view <projectId>
orx create-experiment <projectId> --title "<question> <stage>" --baseline
orx exp run <expId> --backend local
orx exp wait <expId> && orx logs <runId>
```

A node that has answered is frozen. A repair is a new node.

## Closeout

1. Verify every manifest member and code hash.
2. Update `program/state.json` and append to `program/log.md`.
3. Refresh `HANDOFF.md`.
4. Run `uv run ruff check .` and `uv run pytest -q tests`.
5. Inspect the staged diff for secrets, host addresses, employer-internal
   material, caches and large files before committing.
