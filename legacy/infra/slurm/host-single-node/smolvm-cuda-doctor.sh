#!/usr/bin/env bash
set -euo pipefail

readonly pytorch_image="docker.io/pytorch/pytorch@sha256:1ba3f20399f5e4f9835cde308a4de86c3e63ba098caee367e490ec5455afc02a"
export PATH="${HOME}/.local/bin:${PATH}"

: "${SLURM_JOB_ID:?doctor must run inside a Slurm allocation}"
: "${SLURM_STEP_GPUS:?Slurm omitted the step GPU allocation}"
: "${SLURM_GPUS_ON_NODE:?Slurm omitted the node GPU count}"
: "${CUDA_VISIBLE_DEVICES:?Slurm omitted CUDA_VISIBLE_DEVICES}"

if [[ ${SLURM_GPUS_ON_NODE} != 1 ]]; then
  echo "expected exactly one allocated GPU, got ${SLURM_GPUS_ON_NODE}" >&2
  exit 10
fi
if [[ ${CUDA_VISIBLE_DEVICES} == *,* ]]; then
  echo "expected one visible CUDA ordinal, got ${CUDA_VISIBLE_DEVICES}" >&2
  exit 11
fi

echo "SLURM_ALLOCATION_JOB_ID=${SLURM_JOB_ID}"
echo "SLURM_STEP_GPUS=${SLURM_STEP_GPUS}"
echo "SLURM_GPUS_ON_NODE=${SLURM_GPUS_ON_NODE}"
echo "CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES}"
nvidia-smi \
  --id="${CUDA_VISIBLE_DEVICES}" \
  --query-gpu=index,uuid,name,memory.total \
  --format=csv,noheader

smolvm machine run \
  --cuda \
  --net \
  --cpus 4 \
  --mem 16384 \
  --image "${pytorch_image}" \
  -e "SLURM_JOB_ID=${SLURM_JOB_ID}" \
  -e "SLURM_STEP_GPUS=${SLURM_STEP_GPUS}" \
  -e "CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES}" \
  -e "CUDA_LAUNCH_BLOCKING=1" \
  -- python -c '
import json
import torch

def phase(name, **values):
    print(json.dumps({"phase": name, **values}, sort_keys=True), flush=True)

phase("import", torch_version=torch.__version__, torch_cuda_version=torch.version.cuda)
assert torch.__version__.startswith("2.9.0"), torch.__version__
assert torch.cuda.is_available(), "CUDA unavailable through SmolVM"
assert torch.cuda.device_count() == 1, torch.cuda.device_count()
name = torch.cuda.get_device_name(0)
assert "H100" in name, name
properties = torch.cuda.get_device_properties(0)
phase(
    "device",
    device_count=torch.cuda.device_count(),
    device_name=name,
    device_total_memory=properties.total_memory,
)

allocated = torch.ones(1024, device="cuda", dtype=torch.float32)
torch.cuda.synchronize()
phase("allocate")
copied = allocated.cpu()
assert float(copied.sum()) == 1024.0
phase("device_to_host_copy")

left = torch.arange(256 * 256, device="cuda", dtype=torch.bfloat16).reshape(256, 256)
right = torch.eye(256, device="cuda", dtype=torch.bfloat16)
result = left @ right
torch.cuda.synchronize()
assert torch.equal(result, left)
phase("bf16_matmul")

print(
    json.dumps(
        {
            "status": "SMOLVM_CUDA_DOCTOR_PASS",
            "slurm_job_id": int(__import__("os").environ["SLURM_JOB_ID"]),
            "slurm_step_gpus": __import__("os").environ["SLURM_STEP_GPUS"],
            "cuda_visible_devices": __import__("os").environ["CUDA_VISIBLE_DEVICES"],
            "torch_version": torch.__version__,
            "torch_cuda_version": torch.version.cuda,
            "device_count": torch.cuda.device_count(),
            "device_name": name,
            "device_total_memory": properties.total_memory,
            "bf16_matmul": True,
        },
        sort_keys=True,
    )
)
'
