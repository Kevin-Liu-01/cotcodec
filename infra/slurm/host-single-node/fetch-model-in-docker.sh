#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

model_id="${1:?usage: fetch-model-in-docker.sh MODEL_ID}"
image_id="${COTCODEC_IMAGE_ID:-sha256:ba360ea13ea50e77e4900cb258c4dc73156060295abd381899f90f9991cedd10}"
cache_root="${COTCODEC_MODEL_CACHE_ROOT:-/home/kevin/cotcodec-runs/hf-cache}"

if [[ ! "${model_id}" =~ ^[a-z0-9][a-z0-9.-]{0,79}$ ]]; then
  echo "model id is unsafe" >&2
  exit 2
fi
if [[ ! "${image_id}" =~ ^sha256:[0-9a-f]{64}$ ]]; then
  echo "image must be an exact local Docker ID" >&2
  exit 2
fi
if [[ ! "${cache_root}" =~ ^/[A-Za-z0-9._/-]{1,511}$ \
  || "/${cache_root}/" == *"/../"* \
  || ! -d "${cache_root}" \
  || -L "${cache_root}" ]]; then
  echo "model cache root is unsafe or unavailable" >&2
  exit 2
fi
if [[ "${SLURM_JOB_ID:-}" == "" || "${SLURM_STEP_ID:-}" == "" ]]; then
  echo "model fetch must run inside a Slurm job step" >&2
  exit 2
fi
gpu_devices="${CUDA_VISIBLE_DEVICES:-}"
if [[ ! "${gpu_devices}" =~ ^[0-7]$ ]]; then
  echo "model fetch requires exactly one Slurm-mapped H100" >&2
  exit 2
fi
if [[ "$(nvidia-smi -i "${gpu_devices}" --query-gpu=name --format=csv,noheader)" \
  != *H100* ]]; then
  echo "the allocated device is not an H100" >&2
  exit 2
fi
if [[ "$(docker image inspect --format '{{.Id}}' "${image_id}")" != "${image_id}" ]]; then
  echo "Docker resolved a different image" >&2
  exit 2
fi

docker run --rm \
  --gpus "device=${gpu_devices}" \
  --network host \
  --read-only \
  --tmpfs /tmp:rw,nosuid,nodev,size=8g \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  --pids-limit 4096 \
  --user "$(id -u):$(id -g)" \
  --env USER=cotcodec \
  --env LOGNAME=cotcodec \
  --env HOME=/tmp/home \
  --env HF_HOME=/cache/huggingface/hub-cache \
  --env XDG_CACHE_HOME=/cache/xdg \
  --volume "${cache_root}:/cache/huggingface:rw" \
  "${image_id}" \
  python scripts/fetch_open_model.py \
    --model-root /cache/huggingface/cotcodec-models \
    --receipt-root /cache/huggingface/cotcodec-receipts \
    fetch "${model_id}"
