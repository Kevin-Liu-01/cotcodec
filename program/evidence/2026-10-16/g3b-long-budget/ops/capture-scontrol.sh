#!/usr/bin/env bash
# Keep the latest `scontrol show job` record of a job until it has ended (Slurm accounting is off
# and finished records expire within minutes), so its RunTime can be read for the GPU-hours
# ledger. A failed query is retried; the loop ends on a terminal state or after 40 failures in a
# row (the record is gone).
# Usage: setsid nohup capture-scontrol.sh <job id> <output file> &
set -uo pipefail
J="${1:?job}"; OUT="${2:?out}"; fails=0
while (( fails < 40 )); do
  if rec="$(scontrol show job "$J" 2>/dev/null)" && [[ -n "$rec" ]]; then
    fails=0
    printf '%s\n' "$rec" > "$OUT.tmp" && mv "$OUT.tmp" "$OUT"
    state="$(sed -n 's/.*JobState=\([A-Z_]*\).*/\1/p' "$OUT" | head -1)"
    case "$state" in COMPLETED|FAILED|CANCELLED|TIMEOUT|NODE_FAIL|OUT_OF_MEMORY|PREEMPTED|DEADLINE) exit 0 ;; esac
  else
    fails=$((fails + 1))
  fi
  sleep 10
done
