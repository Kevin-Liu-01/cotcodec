#!/usr/bin/env bash
# Usage: watch_job.sh JOBID  -- saves the last `scontrol show job` while Slurm still knows the job
J="$1"; D=/private/tmp/claude-501/-Users-kevinliu-repos-cotcodec/122e47b9-8f46-4266-97af-e75214712991/scratchpad/s2v4-ops/host-logs
for i in $(seq 1 2000); do
  out="$(perl -e 'alarm shift; exec @ARGV' 40 ssh -o BatchMode=yes fal-h100-01 "scontrol show job $J 2>&1" 2>/dev/null)"
  if echo "$out" | grep -q "JobId=$J"; then
    echo "$out" > "$D/scontrol-$J.last.txt"
    st=$(echo "$out" | grep -oE 'JobState=[A-Z_]+' | head -1)
    echo "$(date -u +%FT%TZ) $st" >> "$D/watch-$J.log"
    case "$st" in JobState=COMPLETED|JobState=FAILED|JobState=CANCELLED|JobState=TIMEOUT|JobState=NODE_FAIL|JobState=OUT_OF_MEMORY) echo "ENDED $st"; exit 0;; esac
  elif [ -z "$out" ]; then
    echo "$(date -u +%FT%TZ) no-reply (ssh failed or timed out; retrying)" >> "$D/watch-$J.log"
  else
    echo "$(date -u +%FT%TZ) gone" >> "$D/watch-$J.log"; echo GONE; exit 0
  fi
  sleep 30
done
