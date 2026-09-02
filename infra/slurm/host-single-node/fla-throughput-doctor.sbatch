#!/usr/bin/env bash
#SBATCH --job-name=cotcodec-fla-throughput
#SBATCH --partition=research
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:h100:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --time=00:40:00
#SBATCH --output=/home/kevin/cotcodec-runs/throughput/slurm-%x-%j.out

# Stage-0 infrastructure evidence: measured tokens/s and MFU for the registered
# small hybrid shapes inside the rebuilt architecture image. Requires the image
# ID from build-architecture-image.sbatch. No pretrained weights, no claim.
set -Eeuo pipefail
umask 022
: "${SLURM_JOB_ID:?Run through Slurm}"
: "${CUDA_VISIBLE_DEVICES:?Slurm did not map a GPU}"
: "${COTCODEC_IMAGE_ID:?Set the exact local image ID (sha256:...)}"
if [[ ! "${COTCODEC_IMAGE_ID}" =~ ^sha256:[0-9a-f]{64}$ ]]; then
  echo "COTCODEC_IMAGE_ID must be an exact image ID" >&2; exit 2
fi
out="/home/kevin/cotcodec-runs/throughput/${SLURM_JOB_ID}"
mkdir -m 0755 -p "${out}"
for shape in gdn-hybrid-125m gdn-hybrid-350m; do
  docker run --rm --network=none \
    --gpus "\"device=${CUDA_VISIBLE_DEVICES}\"" \
    -v "${out}:/outputs" \
    "${COTCODEC_IMAGE_ID}" \
    python scripts/fla_throughput_doctor.py --shape "${shape}" --seq-len 2048 --batch 16 \
      --output "/outputs/${shape}.json" | tail -20
done
nvidia-smi -i "${CUDA_VISIBLE_DEVICES}" --query-gpu=name,uuid,driver_version --format=csv,noheader > "${out}/gpu.txt"
ls -la "${out}"
