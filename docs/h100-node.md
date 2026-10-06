# The H100 node

Observed read-only on 2026-10-06. Host address and credentials are not kept in
this public repository; connect with your local SSH alias for `fal-h100-01`.

## What is there

| Item | Observed state | Consequence |
|---|---|---|
| Machine | Lambda KVM virtual machine, 8 x H100 80GB HBM3 SXM, NVLink (NV18), fabric manager running | Full NVLink bandwidth inside one node |
| Driver | 570.148.08 (R570 branch, end of life) | No model-generated code with GPU access until upgraded |
| Container stack | Docker 28.3.1, NVIDIA Container Toolkit 1.17.8 | Discovery lane works; bridge network has no DNS, so builds use `--network=host` |
| Scheduler | Slurm 21.08.5, `research` partition | Discovery only: no Pyxis, no cgroup device isolation, accounting off |
| Virtualization | `/dev/kvm` present, nested virtualization on | Desktop VMs for computer-use tasks can run under userspace QEMU |
| Research account | No root; `sudo` asks for a password | Every item in the admin list below needs the host administrator |
| Persistent storage | `~/cotcodec-runs` on the host | Never write results to node-local `/tmp` |
| Utilization | Under 10 recorded GPU-hours in about six weeks | The constraint is admission and safety, not capacity |

Measured throughput in the current image (`cotcodec-research:0b3ecef0-architecture`,
flash-linear-attention 0.5.2 with tilelang):

| Model | Tokens per second | MFU |
|---|---:|---:|
| 134M Gated DeltaNet hybrid | 282,501 | 24.6% |
| 422M Gated DeltaNet hybrid | 73,045 | not recorded |

No inference throughput has been measured on this node yet. A 0.5 GPU-h vLLM
probe on one VLM and one LLM comes before any budget is frozen.

## Rules for using it

- Workloads run only as Slurm jobs, inside a digest-pinned image, through
  `scripts/submit_docker_research_job.py`. See `operations.md`.
- No model-generated code (kernels, agent-written programs) runs with GPU
  access on the R570 stack. Deterministic mutants of benchmark code are not
  model-generated and may run.
- Membership in the `docker` group is root-equivalent. Never use it to change
  host configuration, read other users' data, or work around the admin list.
- The Docker/Slurm 21.08.5 lane is for discovery. Results meant for
  publication need the publication lane below.

## Admin list (needs the host administrator)

In priority order. Nothing here has been executed.

1. **Driver upgrade to R580** (580.178.04 or the current R580 point release)
   with the matching fabric manager. Lambda's apt repository pins its own
   driver packages at priority 1001, so the upgrade goes through Lambda's
   packages or support. This unblocks Q1's on-policy audit.
2. **Slurm upgrade** from 21.08.5 to a supported release with cgroup v2:
   `proctrack/cgroup`, `task/cgroup,task/affinity`, core, RAM and device
   constraints, GPU GRES with NVML autodetection, and accounting.
3. **Pyxis and Enroot** built against that Slurm release, so
   `srun --container-image` works and `infra/slurm/research.sbatch` can run.
4. **Isolation proof:** two simultaneous one-GPU jobs cannot see each other's
   device files, processes, mounts or output roots.
5. **Docker bridge DNS**, so image builds stop needing host networking.
6. **Container image refresh:** a compatibility-free image on torch 2.13.0
   with CUDA 12.9 and Triton 3.7.1, which removes the fla Hopper guard
   workaround.

The earlier researched version pins and the ordered upgrade recipe are in
`legacy/research/infrastructure/h100-publication-upgrade-2026-09-01.md`.
The earlier operator runbook is `legacy/docs/h100-operator-runbook.md`.

## References

- [Slurm cgroup v2](https://slurm.schedmd.com/cgroup_v2.html)
- [Slurm GRES/GPU configuration](https://slurm.schedmd.com/gres.html)
- [NVIDIA Pyxis](https://github.com/NVIDIA/pyxis/blob/main/README.md)
- [NVIDIA Enroot requirements](https://github.com/NVIDIA/enroot/blob/main/doc/requirements.md)
- [NVIDIA HGX H100 components](https://docs.nvidia.com/enterprise-reference-architectures/hgx-ai-factory-h100-h200-b200/latest/components.html)
