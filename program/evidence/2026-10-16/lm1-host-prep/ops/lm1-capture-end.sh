#!/usr/bin/env bash
# LM1 host prep: wait (polling every 30 s, at most 14 h) until Slurm reports a job in a final
# state, then save `scontrol show job` before Slurm forgets it (MinJobAge 300 s; accounting storage
# is off on this host) and log the end in ops/jobs.log. Exits by itself (kimi-capture-end.sh).
# Usage: nohup lm1-capture-end.sh <job id> <label> &
set -Eeuo pipefail
source "$(dirname "$0")/lm1-env.sh"
J="${1:?job id}"; L="${2:?label}"
scontrol show job "$J" > "$R/ops/scontrol-$J-start.txt" 2>/dev/null || true
for _ in $(seq 1 1680); do
  st=$(scontrol show job "$J" 2>/dev/null | tr ' ' '\n' | sed -n 's/^JobState=//p' || true)
  case "$st" in
    PENDING|RUNNING|CONFIGURING|COMPLETING|"") sleep 30 ;;
    *) scontrol show job "$J" > "$R/ops/scontrol-$J-end.txt"
       rt=$(tr ' ' '\n' < "$R/ops/scontrol-$J-end.txt" | sed -n 's/^RunTime=//p')
       ec=$(tr ' ' '\n' < "$R/ops/scontrol-$J-end.txt" | sed -n 's/^ExitCode=//p')
       tres=$(tr ' ' '\n' < "$R/ops/scontrol-$J-end.txt" | sed -n 's/^AllocTRES=//p')
       log_job "${L} job $J JobState=$st ExitCode=$ec RunTime=$rt AllocTRES=$tres"
       exit 0 ;;
  esac
done
log_job "capture-end gave up waiting for job $J (${L})"
