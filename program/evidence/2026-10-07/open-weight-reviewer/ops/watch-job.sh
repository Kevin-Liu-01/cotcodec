#!/usr/bin/env bash
# Follow one Slurm job to its terminal state, keeping the last `scontrol show job`
# record (accounting is off, so it is the only one), logging each state change,
# then sampling GPU compute processes and the job's lane container once a second
# for 20 s. Read-only: it never signals, stops or removes anything.
set -uo pipefail
job="$1"
ops=/home/kevin/cotcodec-runs/stage0/open-weight-reviewer/ops
last="$ops/scontrol-$job.last.txt"
log="$ops/postjob-$job.log"
prev=""
state=""
while true; do
  out="$(timeout 10 scontrol show job "$job" 2>&1)" || true
  if grep -q "JobState=" <<<"$out"; then
    printf '%s\n' "$out" >"$last.tmp" && mv "$last.tmp" "$last"
    state="$(grep -o 'JobState=[A-Z_]*' <<<"$out" | cut -d= -f2)"
  else
    state="GONE"
  fi
  if [[ "$state" != "$prev" ]]; then
    echo "state $(date -u +%FT%T.%3NZ) $state" >>"$log"
    prev="$state"
  fi
  case "$state" in
    PENDING|CONFIGURING|RUNNING|COMPLETING|SUSPENDED) sleep 1 ;;
    *) break ;;
  esac
done
{
  echo "terminal job=$job state=$state detected_at=$(date -u +%FT%T.%3NZ)"
  for i in $(seq 0 20); do
    echo "-- sample $i at $(date -u +%FT%T.%3NZ)"
    echo "compute-apps: $(timeout 10 nvidia-smi --query-compute-apps=gpu_uuid,pid,process_name,used_memory --format=csv,noheader | tr '\n' ';')"
    echo "gpu-memory: $(timeout 10 nvidia-smi --query-gpu=index,memory.used --format=csv,noheader | tr '\n' ';')"
    echo "docker: $(timeout 10 docker ps -a --filter "name=cotcodec-$job" --format '{{.Names}} {{.Status}}' | tr '\n' ';')"
    sleep 1
  done
  echo "done $(date -u +%FT%T.%3NZ)"
} >>"$log" 2>&1
