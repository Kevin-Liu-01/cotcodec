#!/usr/bin/env bash
#SBATCH --job-name=cotcodec-verify-cpu
#SBATCH --partition=research
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=32G
#SBATCH --time=01:00:00
#SBATCH --no-requeue
#SBATCH --output=/home/kevin/cotcodec-runs/model-fetch/slurm-%x-%j.out
#
# GPU-less receipt verification lane (LM1, D125). For each registry id it re-hashes every file of
# the local snapshot and compares the result with the model's receipt (scripts/fetch_open_model.py
# verify: same file list, sizes and SHA-256, and the same artifact root). The models are verified
# in parallel, one process each, in the fetch lane's image with no network and no GPU. Reading
# every byte also leaves the files in the host's page cache, so a GPU job that starts right after
# loads from memory rather than from disk.
#
# Inputs (sbatch --export):
#   COTCODEC_FETCH_SOURCE   exported source tree under /home/kevin/cotcodec-runs (read-only)
#   COTCODEC_MODEL_IDS      space-separated registry ids
#   COTCODEC_RECEIPT_DIR    optional; receipt directory name under the model cache root
#   COTCODEC_IMAGE_ID       optional; exact local image with PyYAML (default: the fetch lane's)
set -Eeuo pipefail
umask 022
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

: "${SLURM_JOB_ID:?Run this script through sbatch}"
: "${COTCODEC_FETCH_SOURCE:?Set the exported source tree}"
: "${COTCODEC_MODEL_IDS:?Set the registry ids to verify}"
image_id="${COTCODEC_IMAGE_ID:-sha256:ba360ea13ea50e77e4900cb258c4dc73156060295abd381899f90f9991cedd10}"
cache_root="/home/kevin/cotcodec-runs/hf-cache"
receipt_dir="${COTCODEC_RECEIPT_DIR:-cotcodec-receipts}"
run_dir="/home/kevin/cotcodec-runs/model-fetch/verify-${SLURM_JOB_ID}"

fail() {
  echo "verify-models-cpu: $*" >&2
  exit 2
}

for name in SLURM_JOB_GPUS SLURM_STEP_GPUS SLURM_GPUS SLURM_GPUS_ON_NODE CUDA_VISIBLE_DEVICES \
  GPU_DEVICE_ORDINAL; do
  [[ -z "${!name:-}" ]] || fail "${name} is set; the verification lane must hold no GPU"
done
job_tres="$(scontrol show job "${SLURM_JOB_ID}" \
  | tr ' ' '\n' | grep -E '^(TRES|TresPerNode|TresPerJob|TresPerTask|TresPerSocket)=' || true)"
if grep -qiE 'gres/gpu|gpu:' <<<"${job_tres}"; then
  fail "this job was allocated a GPU; refusing to verify"
fi
default_runtime="$(docker info --format '{{.DefaultRuntime}}')"
[[ "${default_runtime}" == "runc" ]] || fail "Docker default runtime is ${default_runtime}, not runc"
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
mkdir -p "${run_dir}"
source_git_sha="$(cat "${COTCODEC_FETCH_SOURCE}/.git_sha" 2>/dev/null || echo unknown)"

common=(
  --rm
  --network none
  --read-only
  --tmpfs /tmp:rw,nosuid,nodev,size=1g
  --cap-drop ALL
  --security-opt no-new-privileges
  --pids-limit 512
  --user "$(id -u):$(id -g)"
  --env CUDA_VISIBLE_DEVICES=
  --env NVIDIA_VISIBLE_DEVICES=void
  --env HOME=/tmp/home
  --label "cotcodec.slurm_job=${SLURM_JOB_ID}"
)
cleanup() {
  local ids
  ids="$(docker ps -aq --filter "label=cotcodec.slurm_job=${SLURM_JOB_ID}" || true)"
  if [[ -n "${ids}" ]]; then
    # shellcheck disable=SC2086
    docker rm --force ${ids} >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT TERM INT

pids=()
for model_id in ${COTCODEC_MODEL_IDS}; do
  (
    started="$(date -u +%s.%N)"
    set +e
    docker run "${common[@]}" \
      --volume "${COTCODEC_FETCH_SOURCE}:/src:ro" \
      --volume "${cache_root}/cotcodec-models:/models:ro" \
      --volume "${cache_root}/${receipt_dir}:/receipts:ro" \
      --workdir /src \
      "${image_id}" \
      python /src/scripts/fetch_open_model.py --registry /src/models/registry.yaml \
        --model-root /models --receipt-root /receipts verify "${model_id}" \
      >"${run_dir}/${model_id}.json" 2>"${run_dir}/${model_id}.err"
    status=$?
    set -e
    finished="$(date -u +%s.%N)"
    receipt_sha256="$(sha256sum "${cache_root}/${receipt_dir}/${model_id}.json" 2>/dev/null \
      | cut -d' ' -f1 || true)"
    printf '{"model_id": "%s", "exit_status": %d, "receipt_sha256": "%s", "seconds": %s}\n' \
      "${model_id}" "${status}" "${receipt_sha256:-missing}" \
      "$(awk -v a="${started}" -v b="${finished}" 'BEGIN{printf "%.1f", b - a}')" \
      >"${run_dir}/${model_id}.summary.json"
  ) &
  pids+=("$!")
done
for pid in "${pids[@]}"; do
  wait "${pid}" || true
done
cat "${run_dir}"/*.summary.json >"${run_dir}/summary.jsonl"
cat >"${run_dir}/receipt.json" <<JSON
{
  "job_id": "${SLURM_JOB_ID}",
  "lane": "verify-models-cpu",
  "batch_sha256": "$(sha256sum "$0" | cut -d' ' -f1)",
  "image_id": "${image_id}",
  "source_dir": "${COTCODEC_FETCH_SOURCE}",
  "source_git_sha": "${source_git_sha}",
  "fetch_script_sha256": "$(sha256sum "${COTCODEC_FETCH_SOURCE}/scripts/fetch_open_model.py" | cut -d' ' -f1)",
  "registry_sha256": "$(sha256sum "${COTCODEC_FETCH_SOURCE}/models/registry.yaml" | cut -d' ' -f1)",
  "model_ids": "${COTCODEC_MODEL_IDS}",
  "receipt_dir": "${receipt_dir}",
  "gres_requested": "none",
  "network": "none",
  "finished_at": "$(date -u +%FT%TZ)"
}
JSON
cat "${run_dir}/summary.jsonl"
expected_count="$(wc -w <<<"${COTCODEC_MODEL_IDS}" | tr -d ' ')"
if [[ "$(grep -c . "${run_dir}/summary.jsonl")" != "${expected_count}" ]] \
  || grep -q '"exit_status": [1-9]' "${run_dir}/summary.jsonl"; then
  exit 1
fi
