#!/usr/bin/env bash
# am3-nonabstain-generality-v1: print one Slurm job's state once (it never waits; poll it). When
# the job has ended, save `scontrol show job` to $R/ops/scontrol-<job>.txt (once) and log it:
# Slurm accounting is disabled on the node and scontrol forgets a job a few minutes after it
# ends, so this runs right after each job ends. Exit 0 when ended, 1 while pending or running.
# Reads Slurm only; it runs no repository code.
# Usage: am3g-job-state.sh dev|reg <job id>
set -Eeuo pipefail
source "$(dirname "$0")/am3g-env.sh" "${1:?mode}"
J="${2:?job id}"
out=$(scontrol show job "$J" 2>/dev/null || true)
state=$(sed -n 's/.*JobState=\([A-Z_]*\).*/\1/p' <<<"$out" | head -1)
case "$state" in
  PENDING|RUNNING|CONFIGURING|COMPLETING|SUSPENDED|"")
    if [[ -z "$state" ]]; then
      [[ -f "$R/ops/scontrol-$J.txt" ]] && { cat "$R/ops/scontrol-$J.txt"; exit 0; }
      echo "job $J unknown to scontrol and never recorded" >&2; exit 2
    fi
    echo "job $J $state"; exit 1 ;;
esac
if [[ ! -f "$R/ops/scontrol-$J.txt" ]]; then
  printf '%s\n' "$out" > "$R/ops/scontrol-$J.txt"   # the full record (no text is in it)
  log_job "job $J ended: $(grep -o 'JobState=[A-Z_]* Reason=[^ ]*' "$R/ops/scontrol-$J.txt") $(grep -o 'RunTime=[^ ]*' "$R/ops/scontrol-$J.txt")"
fi
cat "$R/ops/scontrol-$J.txt"
