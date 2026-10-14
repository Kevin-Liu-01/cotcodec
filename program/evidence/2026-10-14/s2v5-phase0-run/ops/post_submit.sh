#!/usr/bin/env bash
# postsubmit.sh JOB MANIFEST: start the background watcher and record submit-JOB.txt.
set -u
J="$1"; M="$2"
S=/private/tmp/claude-501/-Users-kevinliu-repos-cotcodec/122e47b9-8f46-4266-97af-e75214712991/scratchpad/s2v5-ops
EV=/Users/kevinliu/repos/cotcodec-wt-ops-s2v5/program/evidence/2026-10-14/s2v5-phase0-run
nohup bash $EV/ops/watch_job.sh "$J" > $S/host-logs/watch-$J.stdout 2>&1 &
mkdir -p $EV/k1-jobs/$J
perl -e 'alarm shift; exec @ARGV' 60 ssh -o BatchMode=yes fal-h100-01 "L=~/cotcodec-runs/stage0/s2v5/k1/ops; cat \$L/pre-submit-$M.txt \$L/submit-$M.out; grep ' submitted $M ' \$L/ops.log" > $EV/k1-jobs/$J/submit-$J.txt
grep -E '"job_id"|submitted' $EV/k1-jobs/$J/submit-$J.txt
