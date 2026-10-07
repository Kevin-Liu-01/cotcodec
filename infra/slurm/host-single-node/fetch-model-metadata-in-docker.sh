#!/usr/bin/env bash
# Fetch only the registered metadata_files of one model (config, tokenizer, processor,
# license; no weights) and write a metadata-mode receipt. Used for dummy-weight engines
# (vLLM --load-format dummy) in serving-throughput-probe-v1.
#
# Differences from fetch-model-in-docker.sh: runs `fetch --metadata-only`, attaches no
# GPU to the container, refuses to overwrite an existing receipt for the same model id,
# and requires an image whose ENTRYPOINT is empty (the vLLM overlay resets vLLM's
# `vllm serve` entrypoint; a stock vLLM image would otherwise swallow the command).
set -Eeuo pipefail
umask 077

model_id="${1:?usage: fetch-model-metadata-in-docker.sh MODEL_ID}"
image_id="${COTCODEC_IMAGE_ID:?Set the exact local overlay image ID (sha256:...)}"
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
  echo "metadata fetch must run inside a Slurm job step" >&2
  exit 2
fi
gpu_devices="${CUDA_VISIBLE_DEVICES:-}"
if [[ ! "${gpu_devices}" =~ ^[0-7]$ ]]; then
  echo "metadata fetch requires exactly one Slurm-mapped H100 (lane convention)" >&2
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
entrypoint="$(docker image inspect --format '{{json .Config.Entrypoint}}' "${image_id}")"
if [[ "${entrypoint}" != "null" && "${entrypoint}" != "[]" ]]; then
  echo "image entrypoint ${entrypoint} would swallow the fetch command" >&2
  exit 2
fi
receipt="${cache_root}/cotcodec-receipts/${model_id}.json"
snapshot="${cache_root}/cotcodec-models/${model_id}"
if [[ -e "${receipt}" || -L "${receipt}" || -e "${snapshot}" || -L "${snapshot}" ]]; then
  echo "refusing to overwrite an existing receipt or snapshot for ${model_id}" >&2
  exit 2
fi
mkdir -p "${cache_root}/cotcodec-receipts" "${cache_root}/cotcodec-models"

docker run --rm \
  --network host \
  --read-only \
  --tmpfs /tmp:rw,nosuid,nodev,size=1g \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  --pids-limit 1024 \
  --user "$(id -u):$(id -g)" \
  --workdir /workspace/cotcodec \
  --env USER=cotcodec \
  --env LOGNAME=cotcodec \
  --env HOME=/tmp/home \
  --env HF_HOME=/cache/huggingface/hub-cache \
  --env XDG_CACHE_HOME=/cache/xdg \
  --env HF_HUB_DISABLE_TELEMETRY=1 \
  --volume "${cache_root}:/cache/huggingface:rw" \
  "${image_id}" \
  python scripts/fetch_open_model.py \
    --model-root /cache/huggingface/cotcodec-models \
    --receipt-root /cache/huggingface/cotcodec-receipts \
    fetch "${model_id}" --metadata-only

python3 - "${receipt}" "${model_id}" <<'PY'
import hashlib
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
receipt = json.loads(path.read_text(encoding="utf-8"))
if receipt.get("model_id") != sys.argv[2] or receipt.get("mode") != "metadata":
    raise SystemExit("metadata receipt identity or mode is wrong")
if receipt.get("publication_eligible") is not False:
    raise SystemExit("a metadata receipt must never be publication-eligible")
if any(item["path"].endswith((".safetensors", ".bin", ".pt")) for item in receipt["files"]):
    raise SystemExit("metadata snapshot contains weight files")
print(
    json.dumps(
        {
            "model_id": receipt["model_id"],
            "revision": receipt["revision"],
            "receipt_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "artifact_root_sha256": receipt["artifact_root_sha256"],
            "total_bytes": receipt["total_bytes"],
            "files": len(receipt["files"]),
        },
        sort_keys=True,
    )
)
PY
