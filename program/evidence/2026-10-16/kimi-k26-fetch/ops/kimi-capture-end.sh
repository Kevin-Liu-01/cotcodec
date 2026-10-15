#!/usr/bin/env bash
# Kimi-K2.6 fetch: wait (polling every 30 s, at most 14 h) until Slurm reports the fetch job in a
# final state, then save `scontrol show job` before Slurm forgets it (MinJobAge 300 s; accounting
# storage is off on this host) and log the end in ops/jobs.log. Exits by itself.
# Usage: nohup kimi-capture-end.sh <job id> &
set -Eeuo pipefail
J="${1:?job id}"
R=/home/kevin/cotcodec-runs/stage0/kimi-k26-fetch
for _ in $(seq 1 1680); do
  st=$(scontrol show job "$J" 2>/dev/null | tr ' ' '\n' | sed -n 's/^JobState=//p' || true)
  case "$st" in
    PENDING|RUNNING|CONFIGURING|COMPLETING|"") sleep 30 ;;
    *) scontrol show job "$J" > "$R/ops/scontrol-$J-end.txt"
       rt=$(tr ' ' '\n' < "$R/ops/scontrol-$J-end.txt" | sed -n 's/^RunTime=//p')
       ec=$(tr ' ' '\n' < "$R/ops/scontrol-$J-end.txt" | sed -n 's/^ExitCode=//p')
       echo "$(date -u +%FT%TZ) Kimi-K2.6 fetch job $J JobState=$st ExitCode=$ec RunTime=$rt (CPU lane, 0 GPU-h)" >> "$R/ops/jobs.log"
       exit 0 ;;
  esac
done
echo "$(date -u +%FT%TZ) capture-end gave up waiting for job $J" >> "$R/ops/jobs.log"
