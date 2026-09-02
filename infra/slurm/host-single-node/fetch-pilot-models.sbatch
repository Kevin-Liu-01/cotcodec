#!/usr/bin/env bash
#SBATCH --job-name=cotcodec-fetch-pilot-models
#SBATCH --partition=research
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:h100:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --output=/home/kevin/cotcodec-runs/model-fetch/slurm-%x-%j.out

# Fetch registered pilot checkpoints with reproducibility receipts, one srun
# step per model, through infra/slurm/host-single-node/fetch-model-in-docker.sh
# (which requires a Slurm step, one mapped H100, and an exact image ID).
# Network is required for the download; nothing runs on the GPU. Infrastructure only.
set -Eeuo pipefail
umask 022
: "${SLURM_JOB_ID:?Run through Slurm}"
: "${COTCODEC_IMAGE_ID:?Set the exact local image ID (sha256:...)}"
: "${COTCODEC_MODEL_IDS:?Space-separated registry ids to fetch}"
export COTCODEC_MODEL_CACHE_ROOT="${COTCODEC_MODEL_CACHE_ROOT:-/home/kevin/cotcodec-runs/hf-cache}"
mkdir -p "${COTCODEC_MODEL_CACHE_ROOT}"
repo="${COTCODEC_REPO:-/home/kevin/cotcodec}"
summary="/home/kevin/cotcodec-runs/model-fetch/${SLURM_JOB_ID}-summary.txt"
mkdir -p "$(dirname "${summary}")"
for model_id in ${COTCODEC_MODEL_IDS}; do
  echo "== fetch ${model_id} =="
  if srun --ntasks=1 bash "${repo}/infra/slurm/host-single-node/fetch-model-in-docker.sh" "${model_id}"; then
    echo "${model_id} OK" | tee -a "${summary}"
  else
    echo "${model_id} FAILED" | tee -a "${summary}"
  fi
done
ls -la "${COTCODEC_MODEL_CACHE_ROOT}/cotcodec-receipts" 2>/dev/null || true
cat "${summary}"
