#!/usr/bin/env bash
# G3 budget guard (operator script): when a main job's math worker has saved (done.json), send
# the lane's USR1 to that job so the driver skips its long-context worker. The math phases took
# about twice the sized time; the in-job long-context phase (100 questions) no longer fits the
# 4.0 GPU-h cap. Logs every action to ops/jobs.log.
set -u
R=/home/kevin/cotcodec-runs/stage0/g3-state-precision-accuracy
declare -A W=([1517]=qwen3.5-9b-fp32 [1519]=qwen3.5-9b-fp16 [1521]=qwen3.5-9b-bf16 [1523]=qwen3.5-4b-fp32 [1525]=qwen3.5-4b-fp16 [1527]=qwen3.5-4b-bf16)
declare -A DONE=()
while [[ ${#DONE[@]} -lt 6 ]]; do
  for j in "${!W[@]}"; do
    [[ -n "${DONE[$j]:-}" ]] && continue
    d="$R/runs/main/$j/g3/${W[$j]}-math/done.json"
    if [[ -f "$d" ]]; then
      if squeue -h -j "$j" 2>/dev/null | grep -q .; then
        scancel --batch --signal=USR1 "$j"
        echo "$(date -u +%FT%TZ) budget guard: $j ${W[$j]} math saved ($(cat "$d" | tr -d '\n')); USR1 sent so the driver skips the long-context worker" >> "$R/ops/jobs.log"
      else
        echo "$(date -u +%FT%TZ) budget guard: $j ${W[$j]} math saved; job already gone" >> "$R/ops/jobs.log"
      fi
      DONE[$j]=1
    elif ! squeue -h -j "$j" 2>/dev/null | grep -q .; then
      echo "$(date -u +%FT%TZ) budget guard: $j ${W[$j]} left the queue without a math done.json" >> "$R/ops/jobs.log"
      DONE[$j]=1
    fi
  done
  sleep 2
done
