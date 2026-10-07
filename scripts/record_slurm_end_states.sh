#!/usr/bin/env bash
# Record the Slurm end state of each job as soon as it leaves the queue.
#
# Slurm accounting is off on the H100 host and scontrol forgets a finished job within
# minutes, so q2-action-path's acceptance analysis (harness/q2/action_path/acceptance.py)
# reads each campaign's end state from the batch script's own last record and, when this
# watcher caught it, from `scontrol show job`. Run it on the host right after submitting:
#
#     nohup timeout 86400 scripts/record_slurm_end_states.sh RUN_ROOT/slurm-state JOB... &
#
# It writes OUT_DIR/<job>.txt (the full `scontrol show job` text) once the job is in a
# final state, polls every 20 s, and exits when every job is recorded. A job Slurm has
# already forgotten is recorded as `forgotten` so the analysis can tell the two apart.
set -euo pipefail

[[ $# -ge 2 ]] || { echo "usage: $0 OUT_DIR JOB_ID..." >&2; exit 2; }
out_dir="$1"
shift
for job in "$@"; do
  [[ "${job}" =~ ^[1-9][0-9]{0,19}$ ]] || { echo "not a job id: ${job}" >&2; exit 2; }
done
mkdir -p "${out_dir}"

while :; do
  pending=0
  for job in "$@"; do
    target="${out_dir}/${job}.txt"
    [[ -s "${target}" ]] && continue
    pending=1
    if ! info="$(timeout 20 scontrol show job "${job}" 2>&1)"; then
      if grep -q "Invalid job id" <<<"${info}"; then
        printf 'forgotten: %s\n' "${info}" >"${target}.tmp" && mv "${target}.tmp" "${target}"
      fi
      continue
    fi
    state="$(grep -o 'JobState=[A-Z_]*' <<<"${info}" | head -1 || true)"
    case "${state}" in
      JobState=PENDING | JobState=RUNNING | JobState=CONFIGURING | JobState=COMPLETING | \
        JobState=SUSPENDED | JobState=REQUEUED | "") ;;
      *) printf '%s\n' "${info}" >"${target}.tmp" && mv "${target}.tmp" "${target}" ;;
    esac
  done
  [[ ${pending} -eq 0 ]] && exit 0
  sleep 20
done
