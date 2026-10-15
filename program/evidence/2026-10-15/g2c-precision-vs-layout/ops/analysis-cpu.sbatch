#!/usr/bin/env bash
#SBATCH --job-name=g2c-analysis-cpu
#SBATCH --partition=research
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --time=00:30:00
#SBATCH --no-requeue
# CPU-only (no GRES) analysis of g2c-precision-layout-v1 from a clean checkout (G2C_CHECKOUT):
# pack (join and token checks) per model, the rollout records, then the four-arm tables and the
# figure. G2b's arms come from G2b's full per-token files on the host (SHA-256 checked against
# the config) and G2b's committed throughput.json and analysis.json.
# G2C_JOBS: "model:rollout_job:tf_job ..."; G2C_SMOKE_JOB: the smoke rollout job (probe record).
set -Eeuo pipefail
: "${G2C_CHECKOUT:?}"; : "${G2C_ANALYSIS:?}"; : "${G2C_JOBS:?}"
[[ -z "${CUDA_VISIBLE_DEVICES:-}" && -z "${SLURM_JOB_GPUS:-}" ]] || { echo "GPU allocated" >&2; exit 2; }
R=/home/kevin/cotcodec-runs/stage0/g2c-precision-layout/runs
G2B=/home/kevin/cotcodec-runs/stage0/g2b-state-dtype/analysis-5be81bf5
E=program/evidence/2026-10-15/g2b-state-dtype/analysis
mkdir -p "$G2C_ANALYSIS"
cd "$G2C_CHECKOUT"
[[ -z "$(git status --porcelain)" ]] || { echo dirty; exit 2; }
git rev-parse HEAD > "$G2C_ANALYSIS/analysis-git-sha.txt"
per_token=(); g2b=(); rs=()
for spec in $G2C_JOBS; do
  IFS=: read -r model rsj tfj <<< "$spec"
  out="$G2C_ANALYSIS/per-token-$model.npz"
  uv run --locked python scripts/analyze_g2c_precision_layout.py pack --model "$model" \
    --rollouts "$R/rs/$rsj/g2c" --teacher-force "$R/tf/$tfj/g2ctf" --output "$out"
  per_token+=("$out"); g2b+=("$G2B/per-token-$model.npz"); rs+=("$R/rs/$rsj/g2c")
done
[[ -n "${G2C_SMOKE_JOB:-}" ]] && rs+=("$R/smoke-rs/$G2C_SMOKE_JOB/g2c")
uv run --locked python scripts/analyze_g2c_precision_layout.py rollouts --rollout-jobs "${rs[@]}" \
  --output "$G2C_ANALYSIS/rollouts.json"
uv run --locked python scripts/analyze_g2c_precision_layout.py analyze --per-token "${per_token[@]}" \
  --g2b-per-token "${g2b[@]}" --check-g2b-sha256 --rollouts "$G2C_ANALYSIS/rollouts.json" \
  --g2b-throughput "$E/throughput.json" --g2b-analysis "$E/analysis.json" --output-dir "$G2C_ANALYSIS"
sha256sum "$G2C_ANALYSIS"/* > "$G2C_ANALYSIS/SHA256SUMS.txt" 2>/dev/null || true
echo done
