#!/usr/bin/env bash
# am5-ablated-cost-v1: print one Slurm job's state once (it never waits; poll it at most every
# 120 s while the job runs). When the job has ended, save `scontrol show job` to
# $R/ops/scontrol-<job>.txt (once) and log it: Slurm accounting is disabled on the node and
# scontrol forgets a job 300 s after it ends (MinJobAge), so this runs right after each job ends.
# If scontrol has already forgotten a job that was never recorded, and the lane's termination
# record of that job exists ($R/runs/*/<job>/termination.env: the lane writes it as the job's
# workload ends), the job ended: a "forgotten" record is saved instead (its run time is then the
# lane's), which am5r-rerun-decision.sh accepts like any other (registration section 8). Exit 0
# when ended (a terminal Slurm state: COMPLETED, FAILED, CANCELLED, TIMEOUT, OUT_OF_MEMORY,
# NODE_FAIL, PREEMPTED, BOOT_FAIL or DEADLINE, or forgotten with a termination record), 1 in any
# other state (running or unknown), 2 when scontrol does not know the job, it was never recorded
# and no termination record exists (a GPU job in that state cannot be decided: VOID, V2).
# Reads Slurm and records only; it runs no repository code.
# Usage: am5r-job-state.sh dev|reg <job id>
set -Eeuo pipefail
source "$(dirname "$0")/am5r-env.sh" "${1:?mode}"
J="${2:?job id}"
[[ "$J" =~ ^[0-9]+$ ]] || { echo "not a job id: '$J'" >&2; exit 2; }
out=$(scontrol show job "$J" 2>/dev/null || true)
state=$(sed -n 's/.*JobState=\([A-Z_]*\).*/\1/p' <<<"$out" | head -1)
case "$state" in
  COMPLETED|FAILED|CANCELLED|TIMEOUT|OUT_OF_MEMORY|NODE_FAIL|PREEMPTED|BOOT_FAIL|DEADLINE) ;;
  "")
    [[ -f "$R/ops/scontrol-$J.txt" ]] && { cat "$R/ops/scontrol-$J.txt"; exit 0; }
    shopt -s nullglob
    T=("$R"/runs/*/"$J"/termination.env)
    if [[ ${#T[@]} -eq 1 ]]; then
      { printf 'JobId=%s JobState=FORGOTTEN Reason=scontrol_forgot_the_job\n' "$J"
        printf '   RecordedBy=am5r-job-state.sh At=%s: scontrol no longer knew the job (MinJobAge) and it was never recorded; the lane'"'"'s termination record exists, so the job ended\n' "$(date -u +%FT%TZ)"
        printf '   TerminationRecord=%s sha256=%s\n' "${T[0]#"$R"/}" "$(sha256sum "${T[0]}" | cut -d" " -f1)"
        sed 's/^/   Lane_/' "${T[0]}"; } > "$R/ops/scontrol-$J.txt"
      log_job "job $J forgotten by scontrol; recorded from the lane's termination record (${T[0]#"$R"/})"
      cat "$R/ops/scontrol-$J.txt"; exit 0
    fi
    echo "job $J unknown to scontrol, never recorded, and no termination record" >&2; exit 2 ;;
  *) echo "job $J $state (running or unknown)"; exit 1 ;;
esac
if [[ ! -f "$R/ops/scontrol-$J.txt" ]]; then
  printf '%s\n' "$out" > "$R/ops/scontrol-$J.txt"   # the full record (no text is in it)
  log_job "job $J ended: $(grep -o 'JobState=[A-Z_]* Reason=[^ ]*' "$R/ops/scontrol-$J.txt") $(grep -o 'RunTime=[^ ]*' "$R/ops/scontrol-$J.txt")"
fi
cat "$R/ops/scontrol-$J.txt"
