#!/usr/bin/env bash
#SBATCH --job-name=lm2-score
#SBATCH --partition=research
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=00:30:00
#SBATCH --no-requeue
#SBATCH --output=/home/kevin/cotcodec-runs/stage0/lm2-resident-eval/ops/slurm-lm2-score-%j.out
# LM2 (D129): CPU-only scoring on the host. Mode "prepare" reads every responses-*.jsonl of the
# main jobs (model text, host only) and writes text-free grade rows plus the code sandbox input;
# mode "finalize" merges the sandbox's verdicts. Runs scripts/lm2_score.py from a clean checkout.
# Inputs (sbatch --export): LM2_SRC, LM2_MODE (prepare|finalize), LM2_OUT (grading dir),
# LM2_RUNS (space-separated run directories, prepare only).
set -Eeuo pipefail
: "${SLURM_JOB_ID:?run through sbatch}"; : "${LM2_SRC:?}"; : "${LM2_MODE:?}"; : "${LM2_OUT:?}"
for name in SLURM_JOB_GPUS SLURM_STEP_GPUS SLURM_GPUS CUDA_VISIBLE_DEVICES; do
  [[ -z "${!name:-}" ]] || { echo "$name is set; refusing"; exit 2; }
done
cd "$LM2_SRC"
[[ -z "$(git status --porcelain)" ]] || { echo "source tree is not clean"; exit 2; }
echo "source $(git rev-parse HEAD)"
DATA=/home/kevin/cotcodec-runs/hf-cache/cotcodec-datasets/lm2
mkdir -p "$LM2_OUT"
if [[ "$LM2_MODE" == prepare ]]; then
  # shellcheck disable=SC2086
  /home/kevin/.local/bin/uv run --locked python scripts/lm2_score.py prepare --data "$DATA" \
    --runs $LM2_RUNS --out "$LM2_OUT"
else
  /home/kevin/.local/bin/uv run --locked python scripts/lm2_score.py finalize \
    --pre "$LM2_OUT/grades-pre.jsonl" --verdicts "$LM2_OUT/code-verdicts.jsonl" --out "$LM2_OUT/grades.jsonl"
fi
sha256sum "$LM2_OUT"/*.jsonl
