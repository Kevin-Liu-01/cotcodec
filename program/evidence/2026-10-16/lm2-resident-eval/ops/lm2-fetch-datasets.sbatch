#!/usr/bin/env bash
#SBATCH --job-name=lm2-fetch-datasets
#SBATCH --partition=research
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:30:00
#SBATCH --no-requeue
#SBATCH --output=/home/kevin/cotcodec-runs/stage0/lm2-resident-eval/ops/slurm-lm2-fetch-%j.out
# LM2 (D129): CPU-only fetch of the pinned evaluation sets (scripts/fetch_lm2_datasets.py).
# Holds no GPU: refuses to start if Slurm or the environment shows one. pyarrow comes from an
# ephemeral uv environment on a uv-managed Python 3.12 (no system site-packages); the script runs
# isolated (python -I) from a copy outside the data dir.
set -Eeuo pipefail
: "${SLURM_JOB_ID:?run through sbatch}"
: "${LM2_FETCH_SCRIPT:?path to fetch_lm2_datasets.py}"
for name in SLURM_JOB_GPUS SLURM_STEP_GPUS SLURM_GPUS CUDA_VISIBLE_DEVICES GPU_DEVICE_ORDINAL; do
  [[ -z "${!name:-}" ]] || { echo "$name is set; refusing"; exit 2; }
done
if scontrol show job "$SLURM_JOB_ID" | tr ' ' '\n' | grep -qiE '^(TRES|TresPerNode|TresPerJob)=.*gpu'; then
  echo "allocated a GPU; refusing"; exit 2
fi
OUT=/home/kevin/cotcodec-runs/hf-cache/cotcodec-datasets/lm2
mkdir -p "$OUT"
cd /home/kevin/cotcodec-runs/stage0/lm2-resident-eval/ops
sha256sum "$LM2_FETCH_SCRIPT"
/home/kevin/.local/bin/uv run --isolated --no-project --managed-python --python 3.12 --with pyarrow==17.0.0 \
  python -I "$LM2_FETCH_SCRIPT" fetch --out "$OUT"
chmod -R a-w "$OUT"
ls -la "$OUT"
