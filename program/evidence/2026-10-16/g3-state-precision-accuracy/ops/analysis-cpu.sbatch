#!/usr/bin/env bash
#SBATCH --job-name=g3-analysis-cpu
#SBATCH --partition=research
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=00:30:00
#SBATCH --no-requeue
# CPU-only (no GRES) scoring and analysis of g3-state-precision-accuracy-v1 from a clean checkout
# (G3_CHECKOUT), on the host where the model outputs stay. G3_MODE:
#   pilot        score the pilot workers, then the sizing report (pilot.json)
#   judge-input  score the main workers, then build the judge job's input (judge-input.json)
#   analyze      score the main workers, then results.json and tables.md (with the judge labels)
# G3_RUNS: the run directories (<run_root>/<job>/g3); the workers are their */records.json dirs.
set -Eeuo pipefail
: "${G3_CHECKOUT:?}"; : "${G3_OUT:?}"; : "${G3_MODE:?}"; : "${G3_RUNS:?}"
[[ -z "${CUDA_VISIBLE_DEVICES:-}" && -z "${SLURM_JOB_GPUS:-}" ]] || { echo "GPU allocated" >&2; exit 2; }
LME=/home/kevin/cotcodec-runs/inputs/longmemeval/98d7416c24c778c2fee6e6f3006e7a073259d48f/longmemeval_s_cleaned.json
mkdir -p "$G3_OUT"
cd "$G3_CHECKOUT"
[[ -z "$(git status --porcelain)" ]] || { echo dirty; exit 2; }
git rev-parse HEAD > "$G3_OUT/analysis-git-sha.txt"
workers=()
for r in $G3_RUNS; do for w in "$r"/*/; do [[ -f "$w/records.json" ]] && workers+=("${w%/}"); done; done
printf '%s\n' "${workers[@]}" > "$G3_OUT/workers.txt"
A="uv run --locked python scripts/analyze_g3_accuracy.py"
$A score --workers "${workers[@]}" --lme "$LME" --output "$G3_OUT/scored.jsonl.gz"
case "$G3_MODE" in
  pilot) $A pilot --scored "$G3_OUT/scored.jsonl.gz" --summaries $G3_RUNS --output "$G3_OUT/pilot.json" ;;
  judge-input) $A judge-input --scored "$G3_OUT/scored.jsonl.gz" --workers "${workers[@]}" --lme "$LME" \
                 --output "$G3_OUT/judge-input.json" ;;
  analyze) : "${G3_JUDGE_LABELS:?}"; : "${G3_JUDGE_INPUT:?}"
           $A analyze --scored "$G3_OUT/scored.jsonl.gz" --judge-labels "$G3_JUDGE_LABELS" \
             --judge-input "$G3_JUDGE_INPUT" --summaries $G3_RUNS --output-dir "$G3_OUT" ;;
  *) echo "unknown mode" >&2; exit 2 ;;
esac
sha256sum "$G3_OUT"/* > "$G3_OUT/SHA256SUMS.txt" 2>/dev/null || true
echo done
