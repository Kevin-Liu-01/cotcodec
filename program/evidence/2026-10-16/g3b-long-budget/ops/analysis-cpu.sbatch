#!/usr/bin/env bash
#SBATCH --job-name=g3b-analysis-cpu
#SBATCH --partition=research
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=00:30:00
#SBATCH --no-requeue
# CPU-only (no GRES) scoring and analysis of g3b-long-budget-v1 from a clean checkout
# (G3B_CHECKOUT), on the host where the model outputs stay. G3B_RUNS: the run directories
# (<run_root>/<job>/g3b); the workers are their */records.json dirs. G3's
# ops/analysis-cpu.sbatch, adapted.
set -Eeuo pipefail
: "${G3B_CHECKOUT:?}"; : "${G3B_OUT:?}"; : "${G3B_RUNS:?}"
[[ -z "${CUDA_VISIBLE_DEVICES:-}" && -z "${SLURM_JOB_GPUS:-}" ]] || { echo "GPU allocated" >&2; exit 2; }
mkdir -p "$G3B_OUT"
cd "$G3B_CHECKOUT"
[[ -z "$(git status --porcelain)" ]] || { echo dirty; exit 2; }
git rev-parse HEAD > "$G3B_OUT/analysis-git-sha.txt"
workers=()
for r in $G3B_RUNS; do for w in "$r"/*/; do [[ -f "$w/records.json" ]] && workers+=("${w%/}"); done; done
printf '%s\n' "${workers[@]}" > "$G3B_OUT/workers.txt"
A="uv run --locked python scripts/analyze_g3b_long_budget.py"
$A score --workers "${workers[@]}" --output "$G3B_OUT/scored.jsonl.gz"
if [[ "${G3B_MODE:-analyze}" == analyze ]]; then
  $A analyze --scored "$G3B_OUT/scored.jsonl.gz" --summaries $G3B_RUNS --output-dir "$G3B_OUT" \
    ${G3B_TIMING_WINDOWS:+--timing-windows "$G3B_TIMING_WINDOWS"}
fi
sha256sum "$G3B_OUT"/* > "$G3B_OUT/SHA256SUMS.txt" 2>/dev/null || true
echo done
