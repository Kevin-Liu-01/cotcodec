#!/usr/bin/env bash
#SBATCH --job-name=cotcodec-fetch-model-metadata
#SBATCH --partition=research
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:h100:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:10:00
#SBATCH --output=/home/kevin/cotcodec-runs/model-fetch/slurm-%x-%j.out

# Fetch metadata-only snapshots (config, tokenizer, processor, license; no weights) for
# the dummy-weight engines of serving-throughput-probe-v1, one srun step per model,
# through fetch-model-metadata-in-docker.sh. Network is needed for the Hub; nothing runs
# on the GPU and the container gets no GPU. The allocation time counts toward the probe's
# GPU-hour accounting. COTCODEC_REPO must be a clean checkout (never ~/cotcodec).
set -Eeuo pipefail
umask 022
: "${SLURM_JOB_ID:?Run through Slurm}"
: "${COTCODEC_IMAGE_ID:?Set the exact local vLLM overlay image ID (sha256:...)}"
: "${COTCODEC_MODEL_IDS:?Space-separated registry ids to fetch metadata for}"
: "${COTCODEC_REPO:?Set the clean checkout that holds this script}"
export COTCODEC_MODEL_CACHE_ROOT="${COTCODEC_MODEL_CACHE_ROOT:-/home/kevin/cotcodec-runs/hf-cache}"
if [[ "${COTCODEC_REPO}" == "/home/kevin/cotcodec" ]]; then
  echo "refusing the shared ~/cotcodec checkout" >&2
  exit 2
fi
summary="/home/kevin/cotcodec-runs/model-fetch/${SLURM_JOB_ID}-metadata-summary.jsonl"
mkdir -p "$(dirname "${summary}")"
status=0
for model_id in ${COTCODEC_MODEL_IDS}; do
  echo "== metadata ${model_id} =="
  if srun --ntasks=1 bash "${COTCODEC_REPO}/infra/slurm/host-single-node/fetch-model-metadata-in-docker.sh" \
    "${model_id}" | tail -n 1 | tee -a "${summary}"; then
    :
  else
    echo "{\"model_id\": \"${model_id}\", \"status\": \"FAILED\"}" | tee -a "${summary}"
    status=1
  fi
done
cat "${summary}"
exit "${status}"
