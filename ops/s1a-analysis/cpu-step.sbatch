#!/usr/bin/env bash
#SBATCH --job-name=s1a-analysis
#SBATCH --partition=research
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=01:00:00

# CPU-only Slurm wrapper for one S1a analysis step on the host's system python3 (D59 (iii);
# an operator script, not code of record). Slurm owns the workload (AGENTS.md); no GRES is
# requested and the job refuses to start if Slurm assigned a GPU. Accounting is off on the
# host, so the step's exit status is written as the last line of the job's output.
#
#   sbatch --parsable --job-name=<step> --output=<A>/logs/%x-%j.out cpu-step.sbatch \
#       <ops dir>/<script>.py [args ...]
set -Eeuo pipefail
umask 022

: "${SLURM_JOB_ID:?Run this script through sbatch}"
for var in SLURM_JOB_GPUS SLURM_STEP_GPUS SLURM_GPUS SLURM_GPUS_ON_NODE CUDA_VISIBLE_DEVICES; do
  value="${!var:-}"
  if [[ -n "${value}" && "${value}" != "0" ]]; then
    echo "refusing: ${var}=${value}; this job must hold no GPU" >&2
    echo "exit_status=2"
    exit 2
  fi
done
export CUDA_VISIBLE_DEVICES= NVIDIA_VISIBLE_DEVICES=void OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2

echo "started_at=$(date -u +%FT%TZ) job=${SLURM_JOB_ID} argv=$*"
set +e
python3 -E -s -B "$@"
status=$?
set -e
echo "finished_at=$(date -u +%FT%TZ)"
echo "exit_status=${status}"
exit "${status}"
