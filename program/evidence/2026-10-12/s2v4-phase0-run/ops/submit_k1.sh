#!/usr/bin/env bash
# Usage (on the host, via ssh bash -s): submit_k1.sh MANIFEST_BASENAME DEADLINE_EPOCH
# Snapshot the host, refuse unless the whole queue is empty and now + limit < deadline, then submit.
set -euo pipefail
M="$1"; DEADLINE="$2"
SRC=/home/kevin/cotcodec-runs/stage0/s2v4/k1/src/cf17405026ca2aa20f528b39bdaaff3b257a6610
MIN=/home/kevin/cotcodec-runs/stage0/s2v4/k1/manifests-in
LOG=/home/kevin/cotcodec-runs/stage0/s2v4/k1/ops
mkdir -p "$LOG"
cd "$SRC"
now=$(date -u +%s)
limit=$(python3 -E -s -B -c 'import json,sys; m=json.load(open(sys.argv[1])); print(m["slurm"]["minutes"])' "$MIN/$M")
end=$((now + limit*60 + 60))
echo "now=$(date -u +%FT%TZ) limit_min=$limit limit_end=$(date -u -d @$end +%FT%TZ) deadline=$(date -u -d @$DEADLINE +%FT%TZ)"
if [ "$DEADLINE" != "0" ] && [ "$end" -ge "$DEADLINE" ]; then echo "REFUSE: limit ends after the deadline"; exit 9; fi
q="$(squeue -a -h -o '%i|%j|%T|%M|%l|%C')"
if [ -n "$q" ]; then echo "REFUSE: queue not empty: $q"; exit 8; fi
{
  echo "snapshot_utc=$(date -u +%FT%TZ)"
  echo "loadavg=$(cat /proc/loadavg)"
  echo "nproc=$(nproc)"
  echo "mem_avail_kb=$(grep MemAvailable /proc/meminfo | awk '{print $2}')"
  echo "squeue_all=[$q]"
  echo "docker_running=$(docker ps -q | wc -l)"
  echo "docker_labelled_cotcodec=$(docker ps -q --filter label=cotcodec.slurm_job | wc -l)"
  echo "e_pairs=$(ls /home/kevin/cotcodec-runs/stage0/q2-stage1e/pairs | tr '\n' ' ')"
} > "$LOG/pre-submit-$M.txt"
cat "$LOG/pre-submit-$M.txt"
PYTHONDONTWRITEBYTECODE=1 python3 -E -s -B -m harness.s2_locale.ap_delta submit "$MIN/$M" --source-dir . > "$LOG/submit-$M.out"
cat "$LOG/submit-$M.out" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("JOB", d["job_id"], d["manifest_sha256"], d["minutes"])'
echo "$(date -u +%FT%TZ) submitted $M" >> "$LOG/ops.log"
