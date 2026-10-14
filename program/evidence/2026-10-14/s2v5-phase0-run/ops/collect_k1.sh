#!/usr/bin/env bash
# Usage (Mac): collect_k1.sh JOBID -- copy one finished K1 job from the host to the Mac scratch
# copy (GNU tar on the host, Python's tarfile on the Mac), run check_job.py on it, and copy its
# committed records (no cycles, no VM logs) into the evidence.
set -euo pipefail
J="$1"
S=/private/tmp/claude-501/-Users-kevinliu-repos-cotcodec/122e47b9-8f46-4266-97af-e75214712991/scratchpad/s2v5-ops
EV=/Users/kevinliu/repos/cotcodec-wt-ops-s2v5/program/evidence/2026-10-14/s2v5-phase0-run
mkdir -p "$S/jobs" "$EV/k1-jobs/$J"
rm -rf "$S/jobs/$J"
perl -e 'alarm shift; exec @ARGV' 220 ssh -o BatchMode=yes fal-h100-01 \
  "cd ~/cotcodec-runs/stage0/s2v5/k1/runs && tar -cf - $J" > "$S/jobs/$J.tar"
python3 -I -c 'import sys,tarfile; tarfile.open(sys.argv[1]).extractall(sys.argv[2], filter="data")' "$S/jobs/$J.tar" "$S/jobs"
rm -f "$S/jobs/$J.tar"
perl -e 'alarm shift; exec @ARGV' 60 ssh -o BatchMode=yes fal-h100-01 \
  "cat ~/cotcodec-runs/stage0/s2v5/slurm/slurm-s2v5-apd-*-$J.out" > "$EV/k1-jobs/$J/slurm-$J.out"
(cd "$S/export-7c963f51" && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. \
  perl -e 'alarm shift; exec @ARGV' 220 /Users/kevinliu/repos/cotcodec/.venv/bin/python \
  "$EV/check_job.py" "$S/jobs/$J" "$S/export-7c963f51") > "$EV/k1-jobs/$J/check-$J.json"
cp "$S/jobs/$J/preflight.txt" "$S/jobs/$J/apdelta-receipt.json" "$S/jobs/$J/manifest.json" "$EV/k1-jobs/$J/"
for d in "$S/jobs/$J"/[0-9][0-9]-*/; do
  b=$(basename "$d"); mkdir -p "$EV/k1-jobs/$J/$b"
  for f in apdelta.json manifest.json preflight.txt receipt.json session_plan.json cells_override.json; do
    [ -f "$d/$f" ] && cp "$d/$f" "$EV/k1-jobs/$J/$b/"
  done
done
for f in "scontrol-$J.last.txt" "watch-$J.log"; do
  [ -f "$S/host-logs/$f" ] && cp "$S/host-logs/$f" "$EV/k1-jobs/$J/"
done
echo "collected $J"
