#!/usr/bin/env bash
# G3b partial A/A gate (declared in the config's aa phase before job 1576 ended): once the main
# bf16 job has left the queue, read its Slurm RunTime and submit the A/A job (25-min limit) only
# if the 2.5 GPU-h cap still leaves at least its limit plus 60 s; otherwise log that it is not run.
# Usage: setsid nohup aa-gate.sh <main bf16 job id> <GPU-seconds used by every other job> &
set -uo pipefail
J="${1:?job}"; USED="${2:?gpu seconds used}"
R=/home/kevin/cotcodec-runs/stage0/g3b-long-budget
CAP=9000; NEED=$((25 * 60 + 60))
cd "$R"
while squeue -h -j "$J" 2>/dev/null | grep -q .; do sleep 10; done
sleep 5
scontrol show job "$J" > "ops/scontrol-$J.final.txt" 2>&1
rt="$(sed -n 's/.*RunTime=\([0-9:-]*\).*/\1/p' "ops/scontrol-$J.final.txt" | head -1)"
[[ -n "$rt" ]] || rt="$(sed -n 's/.*RunTime=\([0-9:-]*\).*/\1/p' "ops/scontrol-$J.txt" | head -1)"
IFS=: read -r h m s <<< "$rt"
secs=$((10#$h * 3600 + 10#$m * 60 + 10#$s))
left=$((CAP - USED - secs))
if (( left >= NEED )); then
  echo "$(date -u +%FT%TZ) aa gate: $J RunTime $rt ($secs s); used $USED + $secs = $((USED + secs)) of $CAP GPU-s, $left left >= $NEED: submitting the partial A/A" | tee -a ops/jobs.log ops/guard.log
  bash ops/submit.sh manifests/aa-q35-4b-fp32aa.yaml aa-q35-4b-fp32aa submit >> ops/guard.log 2>&1
  A="$(tail -1 manifests/aa-q35-4b-fp32aa.submit.txt)"
  [[ "$A" =~ ^[0-9]+$ ]] && ops/capture-scontrol.sh "$A" "ops/scontrol-$A.txt"
else
  echo "$(date -u +%FT%TZ) aa gate: $J RunTime $rt ($secs s); used $USED + $secs = $((USED + secs)) of $CAP GPU-s, $left left < $NEED: the partial A/A is not run" | tee -a ops/jobs.log ops/guard.log
fi
