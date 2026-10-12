#!/usr/bin/env bash
# Operator script: poll the whole Slurm queue every 2 s for at most about 200 s; once it is
# empty, run submit-pair-e.sh NAME (which re-runs its checks and its own empty-queue wait
# before it submits anything). Exits 8 when the queue stayed busy (nothing run; rerun it).
# Keeps one line per invocation in the pair's wait.log.
# Usage: wait-then-submit-pair-e.sh NAME
set -u
N="$1"
P=/home/kevin/cotcodec-runs/stage0/q2-stage1e/pairs/$N
for i in $(seq 1 100); do
  if [ -z "$(squeue -a -h -o '%i')" ]; then
    echo "$(date -u +%FT%TZ) queue empty; running submit-pair-e.sh $N" >>"$P/wait.log"
    exec "$(dirname "$0")/submit-pair-e.sh" "$N"
  fi
  sleep 2
done
echo "$(date -u +%FT%TZ) still busy: $(squeue -a -h -o '%i|%j|%T|%M|%C' | tr '\n' ';')" | tee -a "$P/wait.log"
exit 8
