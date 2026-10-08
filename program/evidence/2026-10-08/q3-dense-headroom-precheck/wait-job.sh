#!/usr/bin/env bash
# wait-job.sh JOB MAXSEC: poll squeue every 15 s until JOB leaves the queue (or MAXSEC passes);
# keep the latest `scontrol show job -o` record in ops/scontrol-JOB.txt.
job=$1; max=${2:-600}
ops=$HOME/cotcodec-runs/stage0/q3-dense/ops
end=$(( $(date +%s) + max ))
while :; do
  rec=$(scontrol show job -o "$job" 2>/dev/null)
  [[ -n "$rec" ]] && printf '%s\n' "$rec" > "$ops/scontrol-$job.txt"
  state=$(squeue -h -j "$job" -o %T 2>/dev/null)
  [[ -z "$state" ]] && break
  if (( $(date +%s) >= end )); then echo "WAIT_TIMEOUT job=$job state=$state"; exit 9; fi
  sleep 15
done
rec=$(scontrol show job -o "$job" 2>/dev/null); [[ -n "$rec" ]] && printf '%s\n' "$rec" > "$ops/scontrol-$job.txt"
echo "JOB_LEFT_QUEUE job=$job at=$(date -u +%FT%TZ)"
tr ' ' '\n' < "$ops/scontrol-$job.txt" | grep -E '^(JobId|JobName|JobState|ExitCode|RunTime|TimeLimit|StartTime|EndTime|NumCPUs|TRES)='
