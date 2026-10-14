#!/usr/bin/env bash
# Usage: collect.sh JOBID -- copy one finished confirmation job from the host into Mac scratch
# (records only: the job directory's files, without PNG screenshots), plus its Slurm output.
set -euo pipefail
J="$1"
S=/private/tmp/claude-501/-Users-kevinliu-repos-cotcodec/122e47b9-8f46-4266-97af-e75214712991/scratchpad/s2v5conf
mkdir -p "$S/jobs" "$S/host-logs"
perl -e 'alarm shift; exec @ARGV' 220 ssh -o BatchMode=yes -o ConnectTimeout=20 -o LogLevel=ERROR fal-h100-01 \
  "cd ~/cotcodec-runs/stage0/s2v5/confirm/runs && tar --exclude='*.png' -cf - $J" | tar -xf - -C "$S/jobs"
perl -e 'alarm shift; exec @ARGV' 60 ssh -o BatchMode=yes -o ConnectTimeout=20 -o LogLevel=ERROR fal-h100-01 \
  "cat ~/cotcodec-runs/stage0/s2v5/slurm/slurm-s2v5-apd-confirm-a6-v1-p*-$J.out" > "$S/host-logs/slurm-$J.out"
du -sh "$S/jobs/$J"; find "$S/jobs/$J" -type f | wc -l
echo "collected $J"
