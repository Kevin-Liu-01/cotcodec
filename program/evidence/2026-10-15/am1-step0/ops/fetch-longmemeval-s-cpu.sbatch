#!/usr/bin/env bash
#SBATCH --job-name=am1-fetch-lme-s
#SBATCH --partition=research
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=00:20:00
#SBATCH --no-requeue
# AM1 Step 0 (EXPLORATORY): CPU-only (no GRES) fetch of LongMemEval-S under D1.
# xiaowu0162/longmemeval-cleaned @ 98d7416c, longmemeval_s_cleaned.json (277,383,467 bytes,
# Git LFS oid d6f21ea9...; MIT per the dataset card). Runs the committed
# scripts/memcredit_fetch_dataset.py from the clean checkout (AM1_SRC) with its locked env.
set -Eeuo pipefail
: "${AM1_SRC:?}"; : "${AM1_RECEIPT:?}"
[[ -z "${CUDA_VISIBLE_DEVICES:-}" && -z "${SLURM_JOB_GPUS:-}" ]] || { echo "GPU allocated" >&2; exit 2; }
cd "${AM1_SRC}"
[[ -z "$(git status --porcelain)" ]] || { echo "checkout dirty" >&2; exit 2; }
echo "git $(git rev-parse HEAD)"
uv run --locked --offline python scripts/memcredit_fetch_dataset.py fetch \
  --repo xiaowu0162/longmemeval-cleaned \
  --revision 98d7416c24c778c2fee6e6f3006e7a073259d48f \
  --filename longmemeval_s_cleaned.json \
  --expected-sha256 d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442 \
  --expected-size 277383467 \
  --license MIT \
  --dest-root /home/kevin/cotcodec-runs/inputs/longmemeval \
  --receipt "${AM1_RECEIPT}"
