# Research Compute Contract

All GPU experiments run from one digest-pinned OCI image and are scheduled by
Slurm. Laptop and direct-host runs are smoke tests only; they do not count as
publication runs.

## Current hardware audit (2026-08-10)

The provided host `fal-h100-01` exposes 8 NVIDIA H100 80GB GPUs, 1.7 TiB RAM,
208 CPU threads, and 22 TB local storage. Docker and Podman are installed.
The `kevin` account cannot currently open `/var/run/docker.sock` and noninteractive
`sudo` requires a password; rootless Podman is reachable and is the current OCI
builder. A rootless smoke build completed as
`localhost/cotcodec:smoke-20260810` (local image ID
`4c4f881a42e70ae27d749f3248a7e0e7183083271f84a8ba142e4e776fb397b6`). Its
CPU/container doctor, embedded-provenance verifier, and persistent-output
harness smoke passed. That local ID
is not a registry digest and is not eligible for a publication manifest.

GPU passthrough into rootless Podman is still blocked: Podman 3.4.4 has neither
an NVIDIA CDI device nor an installed OCI hook, so `--device nvidia.com/gpu=all`
failed. An administrator must configure CDI/OCI hooks for direct Podman GPU
smokes; Pyxis/Enroot is the preferred Slurm path.
`sbatch`, `srun`, `sinfo`, Apptainer, and Enroot were not present in the user's
`PATH`, so the host is **not Slurm-ready yet**. This repo does not silently
emulate a scheduler; the Slurm doctor fails until the cluster control plane and
Pyxis/Enroot integration are installed by the host administrator.

## tmux and checkpoint durability

Start or reattach the cluster control session from the repository:

```bash
bash scripts/tmux-research-session.sh cotcodec
```

Use it for editing, `sbatch`, `squeue`/`sacct`, logs, and interactive allocation
clients. It protects work from an SSH or laptop disconnect, like a persistent
terminal—not from a login-node reboot, cluster shutdown, node drain, time limit,
or job cancellation. Batch jobs submitted with `sbatch` are owned by Slurm and
do not need `tmux` to remain alive.

Actual recovery comes from atomic checkpoints on persistent storage. Each
training checkpoint must include model/adapter, optimizer, scheduler, scaler,
all RNG states, data cursor, step, config, source/model hashes, and predecessor
job ID. Keep at least two generations and prove restore/continuation in a fresh
job before scaling. Never put the only checkpoint under node-local `/tmp`.

## Build and publish

```bash
uv lock --check
test -z "$(git status --porcelain)"
source_sha256="$(git archive --format=tar HEAD | shasum -a 256 | cut -d' ' -f1)"
build_context_dir="$(mktemp -d /tmp/cotcodec-build.XXXXXX)"
trap 'rm -rf -- "${build_context_dir}"' EXIT
git archive HEAD | tar -x -C "${build_context_dir}"
podman build \
  --file "${build_context_dir}/infra/research/Dockerfile" \
  --build-arg GIT_SHA="$(git rev-parse HEAD)" \
  --build-arg SOURCE_TREE_SHA256="${source_sha256}" \
  --tag registry.example/cotcodec:"$(git rev-parse --short HEAD)" \
  "${build_context_dir}"
podman push registry.example/cotcodec:"$(git rev-parse --short HEAD)"
podman inspect registry.example/cotcodec:"$(git rev-parse --short HEAD)"
```

Record the resulting `@sha256:` reference in the experiment manifest. Mutable
tags such as `latest` are rejected by the Slurm job.

The CUDA base is digest-pinned and Python dependencies are locked. Ubuntu
packages are not version-pinned, so the resulting image digest and SBOM—not the
Dockerfile alone—are the executable provenance. Generate and retain an SBOM in
the run evidence bundle. Publication images build only from a clean committed
archive; a dirty-worktree smoke image cannot claim the commit SHA.

Pass `--build-arg UV_EXTRA=architecture` for the locked
Torch/Transformers/Accelerate profile, or `--build-arg UV_EXTRA=diffusion` for
the locked Diffusers profile. The selected profile is embedded as an OCI label.
Contained test/validator images additionally pass `--build-arg
INCLUDE_DEV=true`; this is default-off and recorded in the
`org.opencontainers.image.cotcodec-dev-dependencies` label. Never install test
tools interactively into an already sealed image.

If the pinned Ubuntu/NVIDIA package indexes are temporarily unavailable, the
discovery-only `Dockerfile.source-overlay` may copy an exact retained source
archive onto an already sealed architecture image without rerunning `apt`. The
caller must resolve and verify the local base image ID, pass it as
`BASE_IMAGE_ID`, preserve the overlay Dockerfile and build log, and keep the
result labeled `<profile>-source-overlay`. An overlay may preserve development
dependencies only when its verified base image already contains them and the
build explicitly sets `INCLUDE_DEV=true`; it cannot install missing operating-
system or runtime packages. This can run compile and validator doctors, but it
cannot claim a clean publication rebuild.
Kimi Linear additionally requires a reviewed, pinned custom-code/kernel layer;
the generic architecture profile must not enable `trust_remote_code` at run
time.

## Open checkpoint import profiles

Keep the base research image small. Build experiment-specific overlay images
for imported open models:

| Profile | Runtime | Intended use |
|---|---|---|
| Local smoke | Ollama or MLX | Fast behavior checks and harness debugging |
| Language training | Hugging Face Transformers + Accelerate | Fine-tuning, adapters, and architecture surgery |
| Diffusion | Hugging Face Diffusers | Stable Diffusion-family, video, and plan-repair backbones |
| Serving | vLLM, SGLang, or TGI | Batched OpenAI-compatible inference |

Cache model weights below the persistent Hugging Face mount, but record and
verify the exact repository revision, file hashes, tokenizer/processor,
generation config, license, and modeling-code hash in the run manifest. Reject
mutable tags and unreviewed remote code for publication jobs. Imported
checkpoints reduce training cost; they do not weaken matched-baseline or
provenance requirements.

## Managed Tinker profile

Tinker is a separate managed-training backend for LoRA experiments, including
the registered Kimi K2.6 capsule-policy cell. Tinker's remote service owns the
GPU work; the deterministic client still runs from the digest-pinned
`UV_EXTRA=tinker` image in a CPU-only Slurm/Pyxis job. Use
`scripts/submit_tinker_job.py` and `infra/slurm/tinker.sbatch`, not the local-GPU
manifest. Credentials must come from the cluster secret mechanism and are
forbidden in manifests and receipts. Full details are in
`infra/tinker/README.md`.

## Submit from a bounded manifest

```bash
cp infra/slurm/job-manifest.example.yaml /tmp/cotcodec-job.yaml
# Edit the copy with the real digest, committed archive hash, command, budget,
# seeds, and smallest sufficient resource request.
uv run python scripts/submit_research_job.py /tmp/cotcodec-job.yaml --dry-run
uv run python scripts/submit_research_job.py /tmp/cotcodec-job.yaml --test-only
uv run python scripts/submit_research_job.py /tmp/cotcodec-job.yaml
```

The cluster contract is Slurm + Pyxis/Enroot so the exact Docker/OCI image runs
without privileged Docker inside the allocation. The submitter validates full
OCI and source digests, at least three seeds, resource bounds, and requested
GPU-hours ≤ both the declared ceiling and a 64 GPU-hour single-job safety cap.
Commands are JSON argv arrays, not shell strings. It exports only a fixed
allowlist—never the caller's entire environment. Provider credentials must use
the cluster's secret mechanism, not manifest fields or `--export`.

For the registered open memory-model ladder, stage the full pinned snapshots and
receipts below the persistent Hugging Face mount, then compile a model-specific
manifest instead of editing resource counts by hand:

```bash
uv run python scripts/compile_memory_open_job.py \
  --model-id qwen3.6-35b-a3b \
  --image registry.example/cotcodec@sha256:<64-hex-digest> \
  --run-root /shared/cotcodec/runs \
  --git-sha <40-hex-commit> \
  --source-sha256 <64-hex-archive-digest> \
  --memory-bundle-path /shared/cotcodec/inputs/frozen-memory.json \
  --memory-bundle-sha256 <64-hex-file-digest> \
  --output /tmp/memory-qwen35.yaml
uv run python scripts/submit_research_job.py /tmp/memory-qwen35.yaml --dry-run
```

The compiler covers Qwen3.5 4B/9B, Qwen3.6 35B-A3B, and GPT-OSS 120B with
four-to-eight-GPU-hour discovery ceilings. It intentionally rejects Kimi Linear
until its custom code is reviewed and vendored.

Native memory construction runs once before the actor wave with
`scripts/freeze_memory_system_outputs.py`. The compiler requires that sealed
bundle, and the batch script verifies its SHA-256 before mounting the regular,
non-symlink file read-only at `/inputs/memory-selection-bundle.json`. The model
runner rejects a bundle whose source seed, episode count, memory budget, or
treatment mode differs. This makes every open actor consume byte-identical
evidence instead of silently rerunning a stochastic memory constructor.

## Native memory-system images

Mem0, Graphiti, LangMem, Hindsight, and deterministic controls communicate over
the task-blind `memory-system-v1` protocol. Each native implementation uses a
separate OCI image and receives no oracle, suffix, candidate flag, assignment,
outcome, or generator annotation. The registered contract is
`experiments/memory/stage2-oss-baselines.yaml`; source and image details are in
`infra/memory-baselines/README.md`.

The Mem0 image is the first implemented native cell. It derives from the
digest-pinned CoTCodec research image, resolves the exact `memory-mem0` lock,
and installs the reviewed local Mem0 archive with `--no-deps`. Prepare the named
source context from the exact commit before building:

```bash
uv run python scripts/verify_memory_baseline_sources.py
uv run python scripts/prepare_memory_baseline_context.py \
  mem0 /persistent/build-contexts/mem0-71f2ebef
docker buildx build \
  --build-arg COTCODEC_IMAGE=registry.example/cotcodec@sha256:<digest> \
  --build-context mem0_source=/persistent/build-contexts/mem0-71f2ebef \
  -f infra/memory-baselines/mem0/Dockerfile \
  -t registry.example/cotcodec-mem0:<tag> .
```

Graphiti, LangMem, and Hindsight now follow reviewed named-context contracts in
`infra/memory-baselines/README.md`; historical CPU interface smokes exist for
all four systems, but the task-blind request-schema patch requires a fresh
contained rerun. Hindsight uses an isolated lock because its Protobuf
requirement conflicts with Mem0. None has a publication image or Slurm
attestation yet.

The local deterministic embedding server and `run_memory_system_smoke.py` are
CPU interface doctors only. Their artifacts always set
`scientific_evidence=false`. Publication cells use the pinned common BGE service,
digest-pinned images, and scheduler-owned GPU model services.

Run the environment doctors at the environment they describe:

```bash
bash scripts/check_compute_env.sh builder
bash scripts/check_compute_env.sh login
srun bash scripts/check_compute_env.sh allocation
# The image entrypoint runs the container doctor with /outputs mounted.
```

`COTCODEC_OUTPUT_DIR=/outputs` is honored by the harness runner, so traces and
summaries land on the persistent Slurm mount rather than the container layer.

## Required run artifacts

Each job stores the validated manifest, git SHA, OCI digest, Slurm job ID, exact command,
seeds, stdout/stderr, checkpoints, raw immutable traces, metrics, GPU model,
driver/CUDA versions, and termination reason. The batch script forwards `USR1`
and `TERM`, waits up to 120 seconds for `/outputs/checkpoint.ready`, and records
whether checkpoint confirmation arrived. A resumed job sets
`COTCODEC_PREDECESSOR_JOB_ID` and uses a new output directory rather than
overwriting its predecessor. For the memory screen, recompile with
`--predecessor-job-id <job-id>`: the batch job verifies that predecessor image,
git, and source digests match, rejects symlinks and traversal, copies only the
declared `screen/` artifact tree, and then executes `--resume`. Automatic
requeue is intentionally disabled until each workload proves its
checkpoint/resume contract.

`PersistentSubprocessMemorySystem` is the transport primitive for multi-call
native lifecycle studies. Its reference doctor proves one process handles
handshake, repeated selection, purge framing, and shutdown. It does not prove
native backend persistence or deletion; each native image must still pass the
CRUD/restart/isolation/poisoning doctor with backend inspection.

The image embeds `/etc/cotcodec-provenance.json` at build time. Before the
workload starts, the container verifies its git SHA and committed-archive hash
against the validated manifest and persists the result under the job directory.

The current harness runner still contains a placeholder agent loop and the
external benchmark adapters remain stubs. The Research Gauntlet therefore
forces Compute to fail even when this infrastructure smoke succeeds; zero-rate
smoke summaries are wiring evidence, not scientific results.
