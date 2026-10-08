#!/usr/bin/env bash
# snap.sh NAME: record the time, squeue, per-GPU utilisation and memory, and compute processes in OPS/NAME.txt.
OPS=$HOME/cotcodec-runs/stage0/q3-dense-v2/lanes-ops
{ date -u +%FT%TZ; squeue; nvidia-smi --query-gpu=index,utilization.gpu,memory.used --format=csv,noheader
  echo "compute-apps:"; nvidia-smi --query-compute-apps=gpu_uuid,pid,used_memory --format=csv,noheader; } > "$OPS/$1.txt" 2>&1
cat "$OPS/$1.txt"
