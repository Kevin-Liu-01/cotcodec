#!/usr/bin/env bash
# Read-only observations of timing job 766 every 10 s: progress file, GPU utilisation, workload CPU.
run=$HOME/cotcodec-runs/q3-dense-headroom-precheck-v2/timing-qwen3.5-4b-base/766
out=$HOME/cotcodec-runs/stage0/q3-dense-v2/ops/observe-766.txt
for i in $(seq 1 50); do
  st=$(squeue -h -j 766 -o %T 2>/dev/null)
  gpu=$(nvidia-smi -i 0 --query-gpu=utilization.gpu,memory.used --format=csv,noheader 2>/dev/null)
  prog=$(cat $run/dense-precheck/timing-progress.json 2>/dev/null | tr -d '\n ' | cut -c1-200)
  pid=$(pgrep -f run_dense_headroom_precheck_v2.py | head -1)
  cpu=$( [ -n "$pid" ] && ps -o %cpu=,nlwp= -p $pid | tr -s ' ')
  echo "$(date -u +%H:%M:%S) state=$st gpu0=[$gpu] workload_cpu_nlwp=[$cpu] progress=$prog" >> $out
  [ -z "$st" ] && break
  sleep 10
done
