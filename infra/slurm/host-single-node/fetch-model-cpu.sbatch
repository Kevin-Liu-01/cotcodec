#!/usr/bin/env bash
#SBATCH --job-name=cotcodec-fetch-cpu
#SBATCH --partition=research
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --time=04:00:00
#SBATCH --output=/home/kevin/cotcodec-runs/model-fetch/slurm-%x-%j.out
#
# GPU-less model fetch lane (q2-stage1-rescoped-v1, G0 item 2; decisions D1, D12, D13).
#
# The older fetch lanes (fetch-pilot-models.sbatch, fetch-model-in-docker.sh) map one H100
# into the fetch container. A download needs no GPU, and the GPU device files on this host are
# world-writable, so this lane requests no GRES, refuses to start when Slurm or the
# environment shows a GPU, and asserts that its container sees no /dev/nvidia* node.
#
# It runs the committed scripts/fetch_open_model.py and models/registry.yaml from an exported
# source tree (never the image's baked copy), writes the model under the shared model root
# (an existing snapshot at the same revision is re-verified, not changed) and writes each
# receipt into a separate receipt root, so no earlier receipt is overwritten. For a model whose
# registry entry sets trust_remote_code, the remote-code files (*.py at the snapshot root) are
# listed with their SHA-256 in the job summary; nothing in the snapshot is imported or run here.
#
# Inputs (sbatch --export):
#   COTCODEC_FETCH_SOURCE   exported source tree under /home/kevin/cotcodec-runs (read-only)
#   COTCODEC_MODEL_IDS      space-separated registry ids
#   COTCODEC_IMAGE_ID       optional; exact local image with huggingface_hub and PyYAML
#   COTCODEC_RECEIPT_DIR    optional; receipt directory name under the model cache root
set -Eeuo pipefail
umask 022
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
unset PYTHONPATH PYTHONHOME PYTHONSTARTUP

: "${SLURM_JOB_ID:?Run this script through sbatch}"
: "${COTCODEC_FETCH_SOURCE:?Set the exported source tree}"
: "${COTCODEC_MODEL_IDS:?Set the registry ids to fetch}"
image_id="${COTCODEC_IMAGE_ID:-sha256:ba360ea13ea50e77e4900cb258c4dc73156060295abd381899f90f9991cedd10}"
cache_root="/home/kevin/cotcodec-runs/hf-cache"
receipt_dir="${COTCODEC_RECEIPT_DIR:-cotcodec-receipts-cpu-lane}"
run_dir="/home/kevin/cotcodec-runs/model-fetch/cpu-${SLURM_JOB_ID}"

fail() {
  echo "fetch-model-cpu: $*" >&2
  exit 2
}

# --- No GPU, by construction and by assertion ---------------------------------------------
for name in SLURM_JOB_GPUS SLURM_STEP_GPUS SLURM_GPUS SLURM_GPUS_ON_NODE CUDA_VISIBLE_DEVICES \
  GPU_DEVICE_ORDINAL; do
  [[ -z "${!name:-}" ]] || fail "${name} is set; the fetch lane must hold no GPU"
done
job_tres="$(scontrol show job "${SLURM_JOB_ID}" \
  | tr ' ' '\n' | grep -E '^(TRES|TresPerNode|TresPerJob|TresPerTask|TresPerSocket)=' || true)"
if grep -qiE 'gres/gpu|gpu:' <<<"${job_tres}"; then
  fail "this job was allocated a GPU; refusing to fetch"
fi
default_runtime="$(docker info --format '{{.DefaultRuntime}}')"
[[ "${default_runtime}" == "runc" ]] || fail "Docker default runtime is ${default_runtime}, not runc"

# --- Inputs -------------------------------------------------------------------------------
[[ "${image_id}" =~ ^sha256:[0-9a-f]{64}$ ]] || fail "image must be an exact local image ID"
[[ "$(docker image inspect --format '{{.Id}}' "${image_id}")" == "${image_id}" ]] \
  || fail "Docker resolved a different image"
[[ "${COTCODEC_FETCH_SOURCE}" =~ ^/home/kevin/cotcodec-runs/[A-Za-z0-9._/-]+$ \
  && "${COTCODEC_FETCH_SOURCE}" != *..* && -d "${COTCODEC_FETCH_SOURCE}" ]] \
  || fail "source tree must be an existing directory under /home/kevin/cotcodec-runs"
[[ -f "${COTCODEC_FETCH_SOURCE}/scripts/fetch_open_model.py" \
  && -f "${COTCODEC_FETCH_SOURCE}/models/registry.yaml" ]] || fail "source tree lacks the fetch script"
[[ "${receipt_dir}" =~ ^[A-Za-z0-9._-]{1,64}$ ]] || fail "unsafe receipt directory name"
for model_id in ${COTCODEC_MODEL_IDS}; do
  [[ "${model_id}" =~ ^[a-z0-9][a-z0-9.-]{0,79}$ ]] || fail "unsafe model id ${model_id}"
done
mkdir -p "${run_dir}" "${cache_root}/${receipt_dir}" "${cache_root}/cotcodec-models"

batch_sha256="$(sha256sum "$0" | cut -d' ' -f1)"
script_sha256="$(sha256sum "${COTCODEC_FETCH_SOURCE}/scripts/fetch_open_model.py" | cut -d' ' -f1)"
registry_sha256="$(sha256sum "${COTCODEC_FETCH_SOURCE}/models/registry.yaml" | cut -d' ' -f1)"
source_git_sha="$(cat "${COTCODEC_FETCH_SOURCE}/.git_sha" 2>/dev/null || echo unknown)"

common=(
  --rm
  --network host
  --read-only
  --tmpfs /tmp:rw,nosuid,nodev,size=8g
  --cap-drop ALL
  --security-opt no-new-privileges
  --pids-limit 4096
  --user "$(id -u):$(id -g)"
  --env CUDA_VISIBLE_DEVICES=
  --env NVIDIA_VISIBLE_DEVICES=void
  --env USER=cotcodec
  --env LOGNAME=cotcodec
  --env HOME=/tmp/home
  --env HF_HOME=/cache/huggingface/hub-cache
  --env XDG_CACHE_HOME=/cache/xdg
  --env HF_HUB_DISABLE_TELEMETRY=1
  --label "cotcodec.slurm_job=${SLURM_JOB_ID}"
)

# D12 guard: the container must see no NVIDIA device node.
nvidia_nodes="$(docker run "${common[@]}" --entrypoint /bin/sh "${image_id}" \
  -c 'ls -1 /dev/nvidia* 2>/dev/null || true')"
[[ -z "${nvidia_nodes}" ]] || fail "container sees NVIDIA device nodes: ${nvidia_nodes}"

cleanup() {
  local ids
  ids="$(docker ps -aq --filter "label=cotcodec.slurm_job=${SLURM_JOB_ID}" || true)"
  if [[ -n "${ids}" ]]; then
    # shellcheck disable=SC2086
    docker rm --force ${ids} >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT TERM INT

summary="${run_dir}/summary.jsonl"
for model_id in ${COTCODEC_MODEL_IDS}; do
  started="$(date -u +%FT%TZ)"
  set +e
  docker run "${common[@]}" \
    --volume "${COTCODEC_FETCH_SOURCE}:/src:ro" \
    --volume "${cache_root}:/cache/huggingface:rw" \
    --workdir /src \
    "${image_id}" \
    python /src/scripts/fetch_open_model.py \
      --registry /src/models/registry.yaml \
      --model-root /cache/huggingface/cotcodec-models \
      --receipt-root "/cache/huggingface/${receipt_dir}" \
      fetch "${model_id}" >"${run_dir}/${model_id}.log" 2>&1
  status=$?
  set -e
  receipt="${cache_root}/${receipt_dir}/${model_id}.json"
  receipt_sha256="null"
  if [[ "${status}" == "0" && -f "${receipt}" ]]; then
    receipt_sha256="\"$(sha256sum "${receipt}" | cut -d' ' -f1)\""
  fi
  remote_code="$(python3 -E -s - "${cache_root}/cotcodec-models/${model_id}" <<'PY'
import hashlib
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
files = []
if root.is_dir():
    for path in sorted(root.glob("*.py")):
        files.append({"path": path.name, "bytes": path.stat().st_size,
                      "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
print(json.dumps(files, sort_keys=True))
PY
)"
  cat >>"${summary}" <<JSON
{"job_id": "${SLURM_JOB_ID}", "model_id": "${model_id}", "exit_status": ${status}, "receipt": "${receipt_dir}/${model_id}.json", "receipt_sha256": ${receipt_sha256}, "remote_code_files": ${remote_code}, "started_at": "${started}", "finished_at": "$(date -u +%FT%TZ)"}
JSON
done

cat >"${run_dir}/receipt.json" <<JSON
{
  "job_id": "${SLURM_JOB_ID}",
  "lane": "fetch-model-cpu",
  "batch_sha256": "${batch_sha256}",
  "image_id": "${image_id}",
  "source_dir": "${COTCODEC_FETCH_SOURCE}",
  "source_git_sha": "${source_git_sha}",
  "fetch_script_sha256": "${script_sha256}",
  "registry_sha256": "${registry_sha256}",
  "model_ids": "${COTCODEC_MODEL_IDS}",
  "receipt_dir": "${receipt_dir}",
  "gres_requested": "none",
  "job_tres": "$(tr '\n' ' ' <<<"${job_tres}")",
  "docker_default_runtime": "${default_runtime}",
  "container_dev_nvidia": [],
  "network": "host (download only)",
  "finished_at": "$(date -u +%FT%TZ)"
}
JSON
cat "${summary}"
if grep -q '"exit_status": [1-9]' "${summary}"; then
  exit 1
fi
