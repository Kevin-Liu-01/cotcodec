#!/usr/bin/env bash
# observe-lane.sh LANE_ROOT JOB OUT: read-only samples every 30 s until JOB leaves the queue: Slurm state,
# the job's own GPU (index from its job.env) utilisation and memory, and the chunk files per stage.
lane=$1; job=$2; out=$3
run="$lane/$job"
: > "$out"
for i in $(seq 1 200); do
  st=$(squeue -h -j "$job" -o %T 2>/dev/null)
  idx=$(sed -n 's/^gpu_devices=//p' "$run/job.env" 2>/dev/null | head -1)
  gpu=""
  if [ -n "$idx" ]; then
    gpu=$(nvidia-smi -i "$idx" --query-gpu=utilization.gpu,memory.used --format=csv,noheader 2>/dev/null)
  fi
  chunks=""
  for s in "$run"/dense-precheck/checkpoints/eval/*; do
    [ -d "$s" ] && chunks="$chunks $(basename "$s")=$(ls "$s" | wc -l)"
  done
  echo "$(date -u +%H:%M:%S) state=$st gpu$idx=[$gpu] chunks=[${chunks# }]" >> "$out"
  if [ -z "$st" ] && [ "$i" -gt 1 ]; then break; fi
  sleep 30
done
