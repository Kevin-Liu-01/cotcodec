#!/usr/bin/env bash
set -euo pipefail

readonly pytorch_image="docker.io/pytorch/pytorch@sha256:f0ca81b440e252399d9954a45b616ee2540959466aacf3dfc3f856691eee66e8"
readonly script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

: "${SLURM_JOB_ID:?doctor must run inside a Slurm allocation}"
: "${SLURM_STEP_GPUS:?Slurm omitted the step GPU allocation}"
: "${SLURM_GPUS_ON_NODE:?Slurm omitted the node GPU count}"
: "${CUDA_VISIBLE_DEVICES:?Slurm omitted CUDA_VISIBLE_DEVICES}"
: "${COTCODEC_DOCTOR_RECEIPT_DIR:?Set a persistent receipt directory below the user home}"

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

doctor_json="$(docker run \
  --rm \
  --network none \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=1g \
  --shm-size 1g \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  --pids-limit 512 \
  --user 65534:65534 \
  --gpus "device=${CUDA_VISIBLE_DEVICES}" \
  -e "HOME=/tmp" \
  -e "SLURM_JOB_ID=${SLURM_JOB_ID}" \
  -e "SLURM_STEP_GPUS=${SLURM_STEP_GPUS}" \
  -e "CUDA_VISIBLE_DEVICES=0" \
  -e "CUDA_LAUNCH_BLOCKING=1" \
  "${pytorch_image}" \
  python -c '
import json
import os
import torch

assert torch.__version__.startswith("2.9.0"), torch.__version__
assert torch.cuda.is_available(), "CUDA unavailable in Docker"
assert torch.cuda.device_count() == 1, torch.cuda.device_count()
name = torch.cuda.get_device_name(0)
assert "H100" in name, name

allocated = torch.ones(1024, device="cuda", dtype=torch.float32)
torch.cuda.synchronize()
assert float(allocated.cpu().sum()) == 1024.0

left = torch.arange(256 * 256, device="cuda", dtype=torch.bfloat16).reshape(256, 256)
right = torch.eye(256, device="cuda", dtype=torch.bfloat16)
result = left @ right
torch.cuda.synchronize()
assert torch.equal(result, left)

properties = torch.cuda.get_device_properties(0)
print(
    json.dumps(
        {
            "status": "DOCKER_CUDA_DOCTOR_PASS",
            "slurm_job_id": int(os.environ["SLURM_JOB_ID"]),
            "slurm_step_gpus": os.environ["SLURM_STEP_GPUS"],
            "cuda_visible_devices": os.environ["CUDA_VISIBLE_DEVICES"],
            "torch_version": torch.__version__,
            "torch_cuda_version": torch.version.cuda,
            "device_count": torch.cuda.device_count(),
            "device_name": name,
            "device_total_memory": properties.total_memory,
            "allocation_and_copy": True,
            "bf16_matmul": True,
        },
        sort_keys=True,
    )
)
'
)"
printf '%s\n' "${doctor_json}"

python3 "${script_dir}/seal-docker-cuda-receipt.py" \
  --doctor-json "${doctor_json}" \
  --doctor-script "${BASH_SOURCE[0]}" \
  --image "${pytorch_image}" \
  --output-dir "${COTCODEC_DOCTOR_RECEIPT_DIR}"
