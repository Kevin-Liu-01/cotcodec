#!/usr/bin/env bash
#SBATCH --job-name=g3b-posthoc-cpu
#SBATCH --partition=research
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:15:00
#SBATCH --no-requeue
set -Eeuo pipefail
[[ -z "${CUDA_VISIBLE_DEVICES:-}" && -z "${SLURM_JOB_GPUS:-}" ]] || { echo "GPU allocated" >&2; exit 2; }
R=/home/kevin/cotcodec-runs/stage0/g3b-long-budget
sha256sum $R/ops/posthoc_repetition.py
$R/checkout-b066babd/.venv/bin/python -I $R/ops/posthoc_repetition.py $R/runs/main/1574/g3b/qwen3.5-4b-fp32-math $R/runs/main/1576/g3b/qwen3.5-4b-bf16-math > $R/analysis-b066babd/posthoc-repetition.json
echo done
