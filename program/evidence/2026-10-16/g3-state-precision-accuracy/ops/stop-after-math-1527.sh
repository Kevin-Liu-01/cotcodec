#!/usr/bin/env bash
# G3 budget guard for job 1527 (4B bf16): once its math worker has saved (done.json), send the
# lane's USR1 so the driver skips the long-context worker (the long-context task runs on the 9B
# only; ops/jobs.log 19:06:14Z).
set -u
R=/home/kevin/cotcodec-runs/stage0/g3-state-precision-accuracy
d=$R/runs/main/1527/g3/qwen3.5-4b-bf16-math/done.json
until [[ -f $d ]] || ! squeue -h -j 1527 2>/dev/null | grep -q .; do sleep 1; done
if [[ -f $d ]] && squeue -h -j 1527 2>/dev/null | grep -q .; then
  scancel --batch --signal=USR1 1527
  echo "$(date -u +%FT%TZ) budget guard: 1527 qwen3.5-4b-bf16 math saved ($(tr -d '\n' < $d)); USR1 sent so the driver skips the long-context worker" >> $R/ops/jobs.log
else
  echo "$(date -u +%FT%TZ) budget guard: 1527 left the queue before its math done.json" >> $R/ops/jobs.log
fi
