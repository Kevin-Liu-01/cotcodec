#!/usr/bin/env bash
# AM5: print one Slurm job's state once (poll it; it never waits). When the job has ended, save
# `scontrol show job` to $R/ops/scontrol-<job>.txt once (accounting is disabled on the node).
# Exit 0 when ended, 1 in any other state, 2 when scontrol does not know the job and it was
# never recorded.
# Usage: am5-job-state.sh <job id>
set -Eeuo pipefail
source "$(dirname "$0")/am5-env.sh"
J="${1:?job id}"
out=$(scontrol show job "$J" 2>/dev/null || true)
state=$(sed -n 's/.*JobState=\([A-Z_]*\).*/\1/p' <<<"$out" | head -1)
case "$state" in
  COMPLETED|FAILED|CANCELLED|TIMEOUT|OUT_OF_MEMORY|NODE_FAIL|PREEMPTED|BOOT_FAIL|DEADLINE) ;;
  "")
    [[ -f "$R/ops/scontrol-$J.txt" ]] && { grep -o 'JobState=[A-Z_]* Reason=[^ ]*\|RunTime=[^ ]*' "$R/ops/scontrol-$J.txt"; exit 0; }
    echo "job $J unknown to scontrol and never recorded" >&2; exit 2 ;;
  *) echo "job $J $state (running or unknown)"; exit 1 ;;
esac
if [[ ! -f "$R/ops/scontrol-$J.txt" ]]; then
  printf '%s\n' "$out" > "$R/ops/scontrol-$J.txt"
  log_job "job $J ended: $(grep -o 'JobState=[A-Z_]* Reason=[^ ]*' "$R/ops/scontrol-$J.txt") $(grep -o 'RunTime=[^ ]*' "$R/ops/scontrol-$J.txt")"
fi
grep -o 'JobState=[A-Z_]* Reason=[^ ]*\|RunTime=[^ ]*' "$R/ops/scontrol-$J.txt"
