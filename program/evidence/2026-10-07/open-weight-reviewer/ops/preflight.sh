#!/usr/bin/env bash
# Append a pre-submission record of the shared node state.
set -euo pipefail
out="$HOME/cotcodec-runs/stage0/open-weight-reviewer/ops/preflight.log"
{
  echo "== $1 at $(date -u +%FT%TZ)"
  echo "-- squeue -h -o \"%i %j %T %M %b\""
  timeout 30 squeue -h -o "%i %j %T %M %b"
  echo "-- nvidia-smi --query-gpu=index,utilization.gpu,memory.used --format=csv"
  timeout 30 nvidia-smi --query-gpu=index,utilization.gpu,memory.used --format=csv
  echo "-- nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv"
  timeout 30 nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv
} | tee -a "$out"
