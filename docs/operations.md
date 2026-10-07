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
`JobState=COMPLETED` and `ExitCode=0:0`.

Memory workloads from the old program are archived. Both submitters and the
batch script split each argv element on shell and Python punctuation, also try
a value glued to a short option (`python -mpkg.mod`), and refuse it when any
path or dotted-module component is:

- `legacy`, the archive root (so `legacy/...`, `legacy.x.y`,
  `PYTHONPATH=legacy/scripts`, `env --chdir=legacy/scripts` and a bare
  `legacy` are all refused, including the word inside free text; pass prose
  such as prompts through a file);
- one of the 109 memory-named entry points archived from `legacy/scripts`,
  `legacy/harness` and `legacy/infra` (every name there containing `mem` or
  `letta`, such as `run_memorybank_decay_container`, `causal_memory_trials` and
  `memory_trials`), wherever it appears, which also covers pre-restart images
  that still hold these files under `scripts/`;
- a match for `run_memory_*`, `run_letta*`, `*memory_model*` or `memory_trials`.

They also refuse the flags `--memory-bundle`, `--memory-treatment-mode` and
`--expected-memory-system-id` or any argparse abbreviation of them, and any
non-null `memory_source_admission` or `memory_bundle`. Other arguments that
mention memory, such as vLLM's `--gpu-memory-utilization 0.9` or
`/outputs/memory.json`, are admitted. Because an argv check cannot see a path
assembled at run time (inside `python -c`, say), every container also gets an
empty read-only tmpfs over `/workspace/cotcodec/legacy`: archived code is not
present at run time even when an argv hides it.

### Manifest options

Each option is opt-in. The submitter validates it and fails closed; the batch
script checks it again against the hex-encoded manifest. A manifest that uses
none of them produces the same sbatch argv and export list as before the
options existed; its container flags differ only by the `legacy/` mask above.

| Field | Effect |
|---|---|
| `seed_binding: {flag: --seeds \| --seed \| --assignment-seeds}` | Required whenever `seeds` is non-empty. The argv must contain that flag once, followed by exactly the declared seeds in order as separate decimal elements, ended by the next `--` option or the end of argv. No other seed option (`--seed`, `--seeds`, `--assignment-seed`, `--assignment-seeds`), no `--option=value` form and no abbreviation of a seed option (`--see`, `--assign`; argparse would expand it) may appear. Parse it with `allow_abbrev=False` and give the seed option no short alias: the lane cannot see a short alias such as `-s 7`. |
| `randomness_contract: deterministic` | For a job with no randomness: `seeds: []`, no `seed_binding`, no seed option or abbreviation of one in argv. The older `deterministic-all-serve` is accepted with the same meaning. |
| `container_profile` | `default` (also when absent), `vllm` or `large-cpu-mem`; see below. |
| `resources.memory_gb` | Slurm gets `--mem=<memory_gb>G` and the container gets `--memory` and `--memory-swap` of exactly that size. The job exits 2 if Slurm does not export `SLURM_MEM_PER_NODE` or it differs. |
| `model: {kind: none, reason: "..."}` | For jobs that load no checkpoint (kernel-gate validation, CPU doctors on GPUs, VM suites). `reason` is 20-500 characters on one line. No model cache is mounted, no receipt is verified, and `COTCODEC_MODEL_ID=none`. A missing `model` block is still rejected; it never implies `none`. |
| `allow_shared_gpu: true` with `shared_gpu_reason: "..."` | Skips the refusal in the GPU prolog below. The reason follows the same rule as `model.reason`. |

Container profiles:

| Profile | `/tmp` tmpfs | `--shm-size` | `--pids-limit` |
|---|---|---|---|
| `default` | `rw,nosuid,nodev,size=8g`, **noexec** | Docker default (64 MB) | 4096 |
| `vllm` | `rw,exec,nosuid,nodev,size=32g` | `16g` | 8192 |
| `large-cpu-mem` | `rw,exec,nosuid,nodev,size=8g` | Docker default (64 MB) | 4096 |

Under `default`, Docker mounts `/tmp` noexec. JIT caches that load compiled
objects (Triton, TorchInductor) fail there, and `HOME=/tmp/home` puts Triton's
default cache on `/tmp`. Point them at `/outputs` before importing torch (for
example, prefix the argv with `env TRITON_CACHE_DIR=/outputs/cache/triton
TORCHINDUCTOR_CACHE_DIR=/outputs/cache/inductor`), or choose a profile with an
exec `/tmp`.

### GPU prolog

Slurm 21.08 on this host has no device cgroups, so an allocation does not prove
the GPUs are idle. Just before `docker create`, the batch script lists compute
processes with `nvidia-smi --query-compute-apps` and matches them to the UUIDs
of the allocated GPUs. If any process holds an allocated GPU, the job exits
**75** with `reason=foreign_gpu_process`; resubmit when the GPU is idle. If the
list cannot be read, the job exits 2 with `reason=gpu_prolog_unavailable`.
`gpu-prolog.env` and `gpu-compute-apps-prolog.csv` in the run directory record
the result. This is a check at one moment, not isolation.

### Signal checkpoint contract

Slurm sends SIGUSR1 to the batch script 180 s before the time limit. The
script forwards it to the running container at once (and forwards SIGTERM the
same way). The workload must:

1. On SIGUSR1, finish a complete checkpoint save to `/outputs`.
2. Only after that save is complete, write `/outputs/checkpoint.ready`
   atomically: write a temporary file in `/outputs`, then rename it over the
   marker. The marker must contain the line `trigger=SIGUSR1` (for a save
   triggered by SIGTERM, `trigger=SIGTERM`); other lines, such as the step,
   are free.
3. Then exit, or keep running until SIGTERM.

`checkpoint.ready` is reserved for the signal-triggered save. Periodic saves
must never write it; give them their own marker name.

Just before it sends the signal, the batch script records the marker's device,
inode, size and nanosecond mtime, and the time. It confirms only a marker that
differs from that record, has an mtime no earlier than that time, and contains
the `trigger=` line for the signal it sent. A stale marker, a periodic save that
lands in the same window, or a marker without the trigger line never confirms.
It waits up to 120 s or until the container exits, then sends SIGTERM if the
container is still running. `termination.env` records the outcome as
`reason=signal_USR1_checkpoint_confirmed`, `_missing` (container exited
without a confirming marker), `_timeout` or `_not_forwarded` (container not
running). Other reasons are `completed`, `workload_failed`,
`foreign_gpu_process` and `gpu_prolog_unavailable`. `checkpoint_ready=true`
means a signal-triggered checkpoint was confirmed in this job;
`checkpoint_marker_present` only says whether the file exists at the end.

### Open-weight reviewer jobs

A gauntlet review by the self-hosted open-weight model (D23, D24) is one lane
job of `scripts/run_open_weight_review.py run` in the cu129 vLLM overlay:
`container_profile: vllm`, seeds `[42, 43, 44]` bound with `--seeds`, the model
receipt bound by digest and the request bundle (prompt and schema) mounted as
the study artifact. `run_open_weight_review.py manifest` renders the manifest;
the commands and output files are in `experiments/reviewer/README.md`. A review
has no training state, so no resume test applies; a signal ends it as
`INTERRUPTED` with a receipt and the marker, and it is resubmitted.

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
