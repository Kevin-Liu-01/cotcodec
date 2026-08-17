# Single-node Slurm bootstrap

This directory configures the dedicated `fal-h100-01` host for a first
scheduler-owned SmolVM doctor. It is deliberately host-specific and fails on a
different hostname, Slurm version, or NVIDIA device count.

The Ubuntu package is Slurm 21.08.5. It has only `cgroup_v1.so`, while the host
uses unified cgroup v2. Consequently this bootstrap uses `proctrack/linuxproc`,
`task/affinity`, manual GRES device mapping, and file job completion records.
It is acceptable only for a dedicated single-user infrastructure doctor and
bounded discovery. It is **not** sufficient for multi-user isolation or a
publication run. Upgrade Slurm and enable cgroup-v2 core, memory, and device
constraints before either use.

SmolVM supplies the per-workload VM and guest-kernel boundary. Its `--cuda`
mode remotes CUDA calls to a host process; it is process-level GPU isolation,
not PCI passthrough. The scheduler doctor must prove that a one-GPU allocation
exposes exactly one logical CUDA device inside the guest.

On this host, SmolVM 1.7.7 exposed the H100 identity but both its exact checked-
in PyTorch 2.9.0/CUDA 13 fixture and PyTorch 2.9.1 failed the first CUDA kernel
with `invalid device pointer`. Jobs 8–10 are retained as negative infrastructure
evidence. Docker job 11 then proved that the host driver supports CUDA 12.8, not
the fixture's CUDA 13 runtime. The permitted fallback is
`docker-cuda-doctor.sh`, launched only by a one-H100 Slurm allocation. It uses
the digest-pinned PyTorch 2.9.0/CUDA 12.8 image, no network, a read-only root
filesystem, no host mounts, no Linux capabilities, and one GPU device. Job 14
passed allocation/copy and BF16 matrix multiplication and sealed the receipt at
`data/results/infrastructure/docker-cuda-doctor-job-14.json` with SHA-256
`4f1e30d01705d3fe58392a11d0d974bf6432fec7258e113702fd8b0a3090a422`.

`docker-research.sbatch` is the bounded discovery fallback for real model
cells on this dedicated host. Submit it only through
`scripts/submit_docker_research_job.py`. The manifest binds the local Docker
image ID and embedded source labels, the audited batch-script hash, model
snapshot revision/artifact-root/receipt hashes, optional frozen-memory input,
resource ceiling, and exact JSON argv. Runtime networking is disabled, the
root filesystem is read-only, Linux capabilities are dropped, the Slurm GPU
list is mapped explicitly, and only the persistent output plus read-only model
inputs are mounted. Signals are forwarded to the container and the workload's
episode-boundary checkpoint marker is recorded.

This remains **discovery-only** because Slurm 21.08.5 on this host cannot
provide cgroup-v2 scheduler isolation. It does not replace the digest-pinned
Pyxis publication contract in `infra/slurm/research.sbatch`. The checked-in
`qwen35-4b-interface-smoke.yaml` is a four-episode loader/protocol smoke, not a
memory-policy result.

Open-checkpoint downloads are a separate, networked acquisition phase. Run
`fetch-model-in-docker.sh MODEL_ID` only inside a one-H100 `srun`/`sbatch`
step. It rejects missing or multiple GPU mappings and allows network access
only for the public Hub fetch. Every resulting snapshot must subsequently pass
`fetch_open_model.py verify` in a fresh `--network none` job before inference.

Installation is intentionally two-stage:

1. Copy this directory to the host and inspect it.
2. Kevin runs `sudo bash configure-as-root.sh` from the copied directory.

The script refuses to replace an existing different Slurm configuration.
