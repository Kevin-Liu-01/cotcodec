#!/usr/bin/env bash
# Read-only observations of the second timing job every 2 s until it leaves the queue: Slurm state,
# the job's own GPU (index from its job.env) utilisation and memory, the workload's CPU and thread
# count, and the progress file. Usage: observe-timing2.sh JOB_ID
job=$1
run=$HOME/cotcodec-runs/q3-dense-headroom-precheck-v2/timing-2-qwen3.5-4b-base/$job
out=$HOME/cotcodec-runs/stage0/q3-dense-v2/ops/timing-2/observe-$job.txt
: > "$out"
for i in $(seq 1 400); do
  st=$(squeue -h -j "$job" -o %T 2>/dev/null)
  idx=$(sed -n 's/^gpu_devices=//p' "$run/job.env" 2>/dev/null | head -1)
  gpu=""
  [ -n "$idx" ] && gpu=$(nvidia-smi -i "$idx" --query-gpu=utilization.gpu,memory.used --format=csv,noheader 2>/dev/null)
  prog=$(tr -d '\n ' < "$run/dense-precheck/timing-progress.json" 2>/dev/null | cut -c1-200)
  pid=$(pgrep -f run_dense_headroom_precheck_v2.py | head -1)
  cpu=$( [ -n "$pid" ] && ps -o %cpu=,nlwp= -p "$pid" | tr -s ' ')
  echo "$(date -u +%H:%M:%S) state=$st gpu$idx=[$gpu] workload_cpu_nlwp=[$cpu] progress=$prog" >> "$out"
  if [ -z "$st" ] && [ "$i" -gt 3 ]; then break; fi
  sleep 2
done
