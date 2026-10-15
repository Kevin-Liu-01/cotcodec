#!/usr/bin/env bash
# AM1 development pilot: log the queue and GPU state; exit 3 when a G2c GPU job is queued or
# running (GPU jobs of this study are submitted only when none is). Usage: am1s-preflight.sh <label>
set -Eeuo pipefail
R=/home/kevin/cotcodec-runs/stage0/am1-study
{ echo "== ${1:?label} at $(date -u +%FT%TZ)"; echo "-- squeue"; squeue -h -o "%i %j %T %M %b";
  echo "-- gpus"; nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader; } \
  | tee -a "$R/ops/preflight.log"
if squeue -h -o "%j %b" | awk '$1 ~ /^g2c/ && $2 ~ /gpu/' | grep -q .; then
  echo "a G2c GPU job is queued or running; not submitting" | tee -a "$R/ops/preflight.log" >&2; exit 3; fi
echo "no G2c GPU job" | tee -a "$R/ops/preflight.log"
