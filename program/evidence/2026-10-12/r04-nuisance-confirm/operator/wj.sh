#!/bin/sh
# Block up to $2 s (default 220) while Slurm job $1 is in the queue; print its last state.
end=$(( $(date +%s) + ${2:-220} ))
while :; do
  s=$(perl -e 'alarm shift; exec @ARGV' 30 ssh -o BatchMode=yes fal-h100-01 "squeue -h -j $1 -o '%T %M' 2>/dev/null; echo OK" 2>/dev/null | tr '\n' ' ')
  case "$s" in "OK ") echo "$(date -u +%T) job $1 left the queue"; exit 0;; esac
  [ $(( $(date +%s) + 30 )) -gt $end ] && { echo "$(date -u +%T) job $1: $s"; exit 1; }
  sleep 30
done
