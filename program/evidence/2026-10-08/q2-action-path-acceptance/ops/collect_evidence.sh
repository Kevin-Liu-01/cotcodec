#!/usr/bin/env bash
# Collect the small files of each run directory for the evidence bundle, and the
# SHA-256 of every raw file that stays on the host.
#   collect_evidence.sh OUT_DIR JOB...
set -euo pipefail
B="$HOME/cotcodec-runs/q2-action-path-v1"
out="$1"
shift
mkdir -p "$out/runs" "$out/slurm-state"
for job in "$@"; do
  run="$B/runs/$job"
  dest="$out/runs/$job"
  mkdir -p "$dest"
  for f in manifest.json preflight.txt receipt.json session_plan.json; do
    [[ -f "$run/$f" ]] && cp "$run/$f" "$dest/$f"
  done
  [[ -f "$B/runs/slurm-$job.out" ]] && cp "$B/runs/slurm-$job.out" "$dest/slurm-$job.out"
  [[ -f "$B/runs/slurm-state/$job.txt" ]] && cp "$B/runs/slurm-state/$job.txt" "$out/slurm-state/$job.txt"
  (cd "$B/runs" && find "$job" -type f -print0 | sort -z | xargs -0 sha256sum) >"$dest/raw-sha256sums.txt"
done
