# H100 operator runbook

Verified live state: 2026-08-31 21:29 PDT

## What is available now

| Item | Observed state | Consequence |
|---|---|---|
| Host | `kevin@207.241.191.91` / `fal-h100-01` | Reachable over SSH |
| GPUs | 8 × NVIDIA H100 80GB HBM3 | Idle at verification time |
| Scheduler | Slurm 21.08.5, `research` partition | Scheduler owns jobs |
| Containers | Docker 28.3.1 | Discovery lane works |
| Host cgroups | Unified cgroup v2 | Current Slurm package cannot enforce it |
| Pyxis | Absent; `srun --container-image` unavailable | Generic publication lane fails closed |
| Remote repo | `/home/kevin/cotcodec`, clean but stale at `581ded8` when checked | Fast-forward before use |
| Persistent runs | `/home/kevin/cotcodec-runs` | Never use node-local `/tmp` for results |

The hardware is usable today only for bounded, single-user, discovery-only
jobs through `scripts/submit_docker_research_job.py`. It is not currently a
publication-grade multi-user Slurm runtime.

## First: synchronize the exact repository

Run this only after the handoff commit has reached `origin/main`:

```bash
ssh kevin@207.241.191.91
cd /home/kevin/cotcodec
git status --short --branch
git fetch origin main
git merge --ff-only origin/main
git status --short --branch
git rev-parse HEAD
```

Stop if the remote checkout is dirty or cannot fast-forward. Do not reset or
delete remote run directories to make it pass.

## Second: prove that a job is admitted

For memory work, run:

```bash
uv run python scripts/validate_memory_experiments.py
uv run python scripts/validate_memory_sources.py
uv run python scripts/validate_memory_portfolio.py
```

Then verify all of the following:

- the exact source revision is in the source ledger;
- it is not in `killed_revisions` or a blocked lifecycle contract;
- its own CPU lifecycle doctor passed twice;
- the H100 experiment is a new immutable YAML, not a modified prior result;
- the GPU identifies a model-dependent quantity that CPU cannot answer;
- the manifest has a frozen task/control bundle, model receipt, source capsule,
  image identity, seeds, budget, safety gates, and checkpoint contract; and
- the output root is new and persistent.

There is no newly admitted memory H100 job at this handoff. Finish the current
Letta Code MemFS CPU gate—or admit a different candidate through its registered
CPU gate—before creating one.

## Discovery-only submission lane

Do not use
`infra/slurm/host-single-node/qwen35-4b-interface-smoke.yaml` as a template: it
is historical and no longer passes the current seed validator.

Create a new manifest beside the exact experiment. Populate it from measured
artifacts, never by copying stale hashes. Required fields include:

- runtime `docker-single-node-discovery-v1`;
- exact local Docker image ID and embedded Git/source labels;
- current 40-hex committed repository revision and source-capsule SHA-256;
- pinned model revision, receipt SHA-256, and artifact-root SHA-256;
- persistent model cache and run-root paths;
- exact argv and all declared seeds;
- one to eight H100s, CPU/RAM/time, and a maximum GPU-hour budget; and
- `memory_source_admission` plus a frozen memory bundle for memory workloads.

Validate without submitting:

```bash
uv run python scripts/submit_docker_research_job.py \
  experiments/<new-h100-manifest>.yaml --dry-run
```

Ask Slurm to validate the request without running it:

```bash
uv run python scripts/submit_docker_research_job.py \
  experiments/<new-h100-manifest>.yaml --test-only
```

Submit only after both pass:

```bash
uv run python scripts/submit_docker_research_job.py \
  experiments/<new-h100-manifest>.yaml
```

The command prints the job ID. Monitor without attaching the workload to SSH:

```bash
squeue -j <job-id>
scontrol show job <job-id>
tail -F <registered-run-root>/slurm-<job-id>.out
```

The job must record allocation identity, one visible logical GPU per requested
GPU, image/model/source receipts, exact argv, output manifest, and termination
state. A SIGUSR1 checkpoint is not enough: submit a fresh successor job using
`resume_from_job_id` and `resume_subpath`, then compare it with an uninterrupted
continuation before scaling.

## Stage-0 entry points added 2026-09-01 (discovery lane, no root)

| Job | Script | Needs | Produces |
|---|---|---|---|
| Rebuild the architecture base image with `flash-linear-attention` 0.5.2 | `infra/slurm/host-single-node/build-architecture-image.sbatch` (CPU, network on) | clean checkout at the target commit; local registry `127.0.0.1:5000` | `cotcodec-research:<sha8>-architecture`, receipt with image ID and repo digest under `/home/kevin/cotcodec-runs/builds/` |
| Measure training throughput / MFU for the small hybrid shapes | `infra/slurm/host-single-node/fla-throughput-doctor.sbatch` (1 H100) | `COTCODEC_IMAGE_ID` | JSON receipts under `/home/kevin/cotcodec-runs/throughput/<job>/` |
| Fetch pilot checkpoints with receipts | `infra/slurm/host-single-node/fetch-pilot-models.sbatch` (1 H100, network on) | `COTCODEC_IMAGE_ID`, `COTCODEC_MODEL_IDS` | artifacts and receipts under `/home/kevin/cotcodec-runs/hf-cache/` |

```bash
sbatch infra/slurm/host-single-node/build-architecture-image.sbatch
COTCODEC_IMAGE_ID=sha256:<id> sbatch infra/slurm/host-single-node/fla-throughput-doctor.sbatch
COTCODEC_IMAGE_ID=sha256:<id> COTCODEC_MODEL_IDS="qwen3.5-4b-base gla-1.3b-100b"   sbatch infra/slurm/host-single-node/fetch-pilot-models.sbatch
```

These are infrastructure receipts. They do not admit any contract; a pilot
still needs its compiled manifest, CPU doctors passing twice, and the checks in
`.claude/rules/research-gauntlet-loop.md`.

## Publication-grade lane: administrator work still required

Researched pins and an ordered upgrade recipe (Slurm 25.11.7 with cgroup/v2
device constraints, Pyxis 0.24.0, Enroot 4.2.1, NVIDIA Container Toolkit
1.20.0, syft 1.51.1, vLLM v0.28.0 digest) are in
[`research/infrastructure/h100-publication-upgrade-2026-09-01.md`](../research/infrastructure/h100-publication-upgrade-2026-09-01.md).
Commands marked (U) there are assembled, not verified in official docs; none
has been executed on the host. Known open questions: SIGUSR1 propagation through
Pyxis/Enroot is undocumented, and Slurm 25.11.x + Pyxis 0.24.0 compatibility
has unresolved issue reports (#175, #176).

Do not submit through `scripts/submit_research_job.py` yet. Its batch contract
requires Pyxis and exits when `srun --container-image` is unavailable.

The host administrator must:

1. upgrade Slurm from 21.08.5 to a currently supported build with cgroup-v2
   support, keeping controller and node versions aligned;
2. configure `proctrack/cgroup`, `task/cgroup,task/affinity`, cgroup-v2
   autodetection, core constraints, RAM constraints, and device constraints;
3. configure GPU GRES with NVML autodetection, verify all eight H100 device
   mappings, and enable GPU accounting as appropriate;
4. install Enroot and run its official requirements checker;
5. build Pyxis against that exact Slurm release, register its SPANK plugin, and
   verify `srun --help` exposes `--container-image`;
6. prove two simultaneous one-GPU jobs cannot observe or access each other's
   GPU device files, processes, mounts, or output roots;
7. rerun the digest-pinned CUDA allocation/BF16 doctor inside Pyxis with network
   disabled and a read-only container root; and
8. make `bash scripts/check_compute_env.sh login` and the allocation/container
   doctors pass before using `infra/slurm/research.sbatch`.

Official references:

- [Slurm cgroup v2](https://slurm.schedmd.com/cgroup_v2.html)
- [Slurm cgroup constraints](https://slurm.schedmd.com/cgroup.conf.html)
- [Slurm GRES/GPU configuration](https://slurm.schedmd.com/gres.html)
- [NVIDIA Pyxis](https://github.com/NVIDIA/pyxis/blob/main/README.md)
- [NVIDIA Enroot requirements](https://github.com/NVIDIA/enroot/blob/main/doc/requirements.md)

## Hard stops

Do not use an H100 when any of these is true:

- the exact revision is killed or its CPU gate is incomplete;
- the source/image/model receipt is mutable or missing;
- the contract changes after treatment output was observed;
- the task/control bundle is not frozen and hash-bound;
- safety evaluation is absent;
- checkpoint recovery has not been reproduced in a fresh allocation;
- the job would overwrite an existing output directory; or
- the result is intended for publication while running on the discovery-only
  Docker/Slurm 21.08.5 lane.
