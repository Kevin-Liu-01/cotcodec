#!/usr/bin/env bash
#SBATCH --job-name=g3-prelim-cpu
#SBATCH --partition=research
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=00:30:00
#SBATCH --no-requeue
# G3 preliminary scoring (CPU, no GRES): score the main workers and analyze without judge labels
# (math results and the 9B long-context containment check). Not the final analysis.
set -Eeuo pipefail
R=/home/kevin/cotcodec-runs/stage0/g3-state-precision-accuracy
C=$R/checkout-274a2a99; O=$R/analysis-prelim-274a2a99
LME=/home/kevin/cotcodec-runs/inputs/longmemeval/98d7416c24c778c2fee6e6f3006e7a073259d48f/longmemeval_s_cleaned.json
[[ -z "${CUDA_VISIBLE_DEVICES:-}" && -z "${SLURM_JOB_GPUS:-}" ]] || { echo "GPU allocated" >&2; exit 2; }
mkdir -p $O; cd $C; [[ -z "$(git status --porcelain)" ]] || { echo dirty; exit 2; }
runs="$R/runs/main/1517/g3 $R/runs/main/1519/g3 $R/runs/main/1521/g3 $R/runs/main/1523/g3 $R/runs/main/1525/g3 $R/runs/main/1527/g3"
workers=(); for r in $runs; do for w in "$r"/*/; do [[ -f "$w/records.json" ]] && workers+=("${w%/}"); done; done
A="uv run --locked python scripts/analyze_g3_accuracy.py"
$A score --workers "${workers[@]}" --lme "$LME" --output $O/scored.jsonl.gz
$A analyze --scored $O/scored.jsonl.gz --summaries $runs --output-dir $O
echo done
