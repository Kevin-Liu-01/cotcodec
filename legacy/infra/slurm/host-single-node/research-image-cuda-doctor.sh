#!/usr/bin/env bash
set -euo pipefail

: "${SLURM_JOB_ID:?doctor must run inside a Slurm allocation}"
: "${SLURM_STEP_GPUS:?Slurm omitted the step GPU allocation}"
: "${SLURM_GPUS_ON_NODE:?Slurm omitted the node GPU count}"
: "${CUDA_VISIBLE_DEVICES:?Slurm omitted CUDA_VISIBLE_DEVICES}"
: "${COTCODEC_RESEARCH_IMAGE_ID:?Set the immutable local Docker image id}"
: "${COTCODEC_GIT_SHA:?Set the embedded base Git revision}"
: "${COTCODEC_SOURCE_SHA256:?Set the embedded source archive digest}"

if [[ ! ${COTCODEC_RESEARCH_IMAGE_ID} =~ ^sha256:[0-9a-f]{64}$ ]]; then
  echo "COTCODEC_RESEARCH_IMAGE_ID must be a Docker content-addressed image id" >&2
  exit 2
fi
if [[ ! ${COTCODEC_GIT_SHA} =~ ^[0-9a-f]{40}$ ]]; then
  echo "COTCODEC_GIT_SHA must be 40 lowercase hex characters" >&2
  exit 2
fi
if [[ ! ${COTCODEC_SOURCE_SHA256} =~ ^[0-9a-f]{64}$ ]]; then
  echo "COTCODEC_SOURCE_SHA256 must be 64 lowercase hex characters" >&2
  exit 2
fi
if [[ ${SLURM_GPUS_ON_NODE} != 1 || ${CUDA_VISIBLE_DEVICES} == *,* ]]; then
  echo "doctor requires exactly one Slurm-allocated GPU" >&2
  exit 2
fi

read -r inspected_id label_git label_source label_profile < <(
  docker image inspect "${COTCODEC_RESEARCH_IMAGE_ID}" \
    --format '{{.Id}} {{index .Config.Labels "org.opencontainers.image.revision"}} {{index .Config.Labels "org.opencontainers.image.source-tree-sha256"}} {{index .Config.Labels "org.opencontainers.image.cotcodec-runtime-profile"}}'
)
if [[ ${inspected_id} != "${COTCODEC_RESEARCH_IMAGE_ID}" \
  || ${label_git} != "${COTCODEC_GIT_SHA}" \
  || ${label_source} != "${COTCODEC_SOURCE_SHA256}" \
  || ${label_profile} != architecture ]]; then
  echo "research image labels do not match the requested provenance" >&2
  exit 3
fi

common_args=(
  run
  --rm
  --network none
  --read-only
  --tmpfs /tmp:rw,noexec,nosuid,size=1g
  --shm-size 1g
  --cap-drop ALL
  --security-opt no-new-privileges
  --pids-limit 512
  --user 65534:65534
  --gpus "device=${CUDA_VISIBLE_DEVICES}"
  -e HOME=/tmp
  -e UV_CACHE_DIR=/tmp/uv-cache
  -e CUDA_VISIBLE_DEVICES=0
  -e "COTCODEC_GIT_SHA=${COTCODEC_GIT_SHA}"
  -e "COTCODEC_SOURCE_SHA256=${COTCODEC_SOURCE_SHA256}"
)

docker "${common_args[@]}" "${COTCODEC_RESEARCH_IMAGE_ID}" \
  /usr/local/bin/uv lock --check
docker "${common_args[@]}" "${COTCODEC_RESEARCH_IMAGE_ID}" \
  python scripts/verify_compute_provenance.py
docker "${common_args[@]}" "${COTCODEC_RESEARCH_IMAGE_ID}" python -c '
import json

import torch
import transformers

assert torch.__version__ == "2.11.0+cu128", torch.__version__
assert torch.version.cuda == "12.8", torch.version.cuda
assert torch.cuda.is_available(), "CUDA unavailable in research image"
assert torch.cuda.device_count() == 1, torch.cuda.device_count()
name = torch.cuda.get_device_name(0)
assert "H100" in name, name
left = torch.arange(256 * 256, device="cuda", dtype=torch.bfloat16).reshape(256, 256)
right = torch.eye(256, device="cuda", dtype=torch.bfloat16)
result = left @ right
torch.cuda.synchronize()
assert torch.equal(result, left)
print(
    json.dumps(
        {
            "status": "RESEARCH_IMAGE_CUDA_PASS",
            "torch": torch.__version__,
            "cuda": torch.version.cuda,
            "transformers": transformers.__version__,
            "device_count": torch.cuda.device_count(),
            "device": name,
            "bf16_matmul": True,
        },
        sort_keys=True,
    )
)
'
