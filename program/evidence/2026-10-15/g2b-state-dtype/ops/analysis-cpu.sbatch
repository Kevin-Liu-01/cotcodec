#!/usr/bin/env bash
#SBATCH --job-name=g2b-analysis-cpu
#SBATCH --partition=research
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --time=00:30:00
#SBATCH --no-requeue
# CPU-only (no GRES) analysis of g2b-state-dtype-v1 from a clean checkout (G2B_CHECKOUT):
# pack (join and token checks) per model, the throughput summary, then tables and the figure.
# Inputs are the jobs' run directories; outputs go to G2B_ANALYSIS.
set -Eeuo pipefail
: "${G2B_CHECKOUT:?}"; : "${G2B_ANALYSIS:?}"; : "${G2B_JOBS:?}"
[[ -z "${CUDA_VISIBLE_DEVICES:-}" && -z "${SLURM_JOB_GPUS:-}" ]] || { echo "GPU allocated" >&2; exit 2; }
# G2B_JOBS: "model:fp32_rollout_job:bf16_rollout_job:prefill_job:tf_job ..." plus G2B_RS_JOBS (all
# rollout job dirs for the throughput table).
R=/home/kevin/cotcodec-runs/stage0/g2b-state-dtype/runs
mkdir -p "$G2B_ANALYSIS"
cd "$G2B_CHECKOUT"
[[ -z "$(git status --porcelain)" ]] || { echo dirty; exit 2; }
git rev-parse HEAD > "$G2B_ANALYSIS/analysis-git-sha.txt"
per_token=()
for spec in $G2B_JOBS; do
  IFS=: read -r model f32 b16 pre tf <<< "$spec"
  out="$G2B_ANALYSIS/per-token-$model.npz"
  uv run --locked python scripts/analyze_g2b_state_dtype.py pack --model "$model" \
    --rollouts "$R/rs/$f32/g2b/$model-fp32" "$R/rs/$b16/g2b/$model-bf16" \
    --prefill "$R/prefill/$pre/g2bp" --teacher-force "$R/tf/$tf/g2btf" --output "$out"
  per_token+=("$out")
done
rs=()
for j in $G2B_RS_JOBS; do rs+=("$R/rs/$j/g2b"); done
uv run --locked python scripts/analyze_g2b_state_dtype.py throughput --rollout-jobs "${rs[@]}" \
  --output "$G2B_ANALYSIS/throughput.json"
uv run --locked python scripts/analyze_g2b_state_dtype.py analyze --per-token "${per_token[@]}" \
  --throughput "$G2B_ANALYSIS/throughput.json" --output-dir "$G2B_ANALYSIS"
sha256sum "$G2B_ANALYSIS"/* > "$G2B_ANALYSIS/SHA256SUMS.txt" 2>/dev/null || true
echo done
