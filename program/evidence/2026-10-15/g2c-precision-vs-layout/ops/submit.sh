#!/usr/bin/env bash
# Dry-run and test-only one manifest through the lane's submitter (from the checkout of the
# images' commit), then, with "submit", record queue and GPU state and submit it (G2b's
# ops/submit.sh, split so the checks can be read before submitting).
# Usage: submit.sh <manifest> <label> [check|submit]
set -Eeuo pipefail
M="$(realpath "${1:?manifest}")"; L="${2:?label}"; MODE="${3:-check}"
R=/home/kevin/cotcodec-runs/stage0/g2c-precision-layout
S="$(sed -n 's/^git_sha: "\(.\{8\}\).*/\1/p' "$M")"
B="${M%.yaml}"
cd "$R/checkout-$S"
uv run --locked python scripts/submit_docker_research_job.py "$M" --dry-run > "$B.dry-run.json" 2>&1 || { echo "dry-run failed"; tail -5 "$B.dry-run.json"; exit 2; }
uv run --locked python scripts/submit_docker_research_job.py "$M" --test-only > "$B.test-only.txt" 2>&1 || { echo "test-only failed"; tail -5 "$B.test-only.txt"; exit 2; }
if [[ "$MODE" != submit ]]; then echo "checks passed: $(tail -1 "$B.test-only.txt")"; exit 0; fi
{ echo "== $L at $(date -u +%FT%TZ)"; squeue -h -o "%i %j %T %M %b"; nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader; } >> "$R/ops/preflight.log"
uv run --locked python scripts/submit_docker_research_job.py "$M" > "$B.submit.txt" 2>&1 || { echo "submit failed"; tail -5 "$B.submit.txt"; exit 2; }
J="$(tail -1 "$B.submit.txt")"
echo "$(date -u +%FT%TZ) $L submitted: $J ($(basename "$M"))" | tee -a "$R/ops/jobs.log"
