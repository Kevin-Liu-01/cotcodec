#!/usr/bin/env bash
# Usage (on the host, via `ssh fal-h100-01 bash -s -- MANIFEST_BASENAME < submit_k1.sh`):
# refuse unless the whole queue is empty, no labelled cotcodec container exists and this manifest
# was never submitted (its canonical digest has no stored copy under the K1 run root, which only
# a real `ap_delta_v5 submit` writes); snapshot the host; then submit through `ap_delta_v5.py
# submit --no-e-deadline` (successor E is finished) from the freeze export.
set -euo pipefail
M="$1"
SRC=/home/kevin/cotcodec-runs/stage0/s2v5/k1/src/7c963f51ad5a634c74c7ac2dff43f75a502656de
MIN=/home/kevin/cotcodec-runs/stage0/s2v5/k1/manifests-in
RUNS=/home/kevin/cotcodec-runs/stage0/s2v5/k1/runs
LOG=/home/kevin/cotcodec-runs/stage0/s2v5/k1/ops
mkdir -p "$LOG"
cd "$SRC"
[ -f "$MIN/$M" ] || { echo "REFUSE: no manifest $M"; exit 7; }
digest=$(python3 -E -s -B -c 'import hashlib,json,sys; m=json.load(open(sys.argv[1])); print(hashlib.sha256(json.dumps(m,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest())' "$MIN/$M")
if [ -e "$RUNS/manifests/$digest.json" ]; then echo "REFUSE: $M ($digest) was submitted before"; exit 6; fi
if grep -q " submitted $M " "$LOG/ops.log" 2>/dev/null; then echo "REFUSE: $M is in ops.log"; exit 6; fi
q="$(squeue -a -h -o '%i|%j|%T|%M|%l|%C|%u')"
if [ -n "$q" ]; then echo "REFUSE: queue not empty: $q"; exit 8; fi
lab=$(docker ps -aq --filter label=cotcodec.slurm_job | wc -l)
if [ "$lab" != "0" ]; then echo "REFUSE: $lab labelled cotcodec containers exist"; exit 5; fi
{
  echo "snapshot_utc=$(date -u +%FT%TZ)"
  echo "manifest=$M canonical_sha256=$digest"
  echo "loadavg=$(cat /proc/loadavg)"
  echo "nproc=$(nproc)"
  echo "mem_avail_kb=$(grep MemAvailable /proc/meminfo | awk '{print $2}')"
  echo "squeue_all=[$q]"
  echo "docker_running=$(docker ps -q | wc -l)"
  echo "docker_labelled_cotcodec=$lab"
  echo "k1_runs=$(ls "$RUNS" 2>/dev/null | tr '\n' ' ')"
} > "$LOG/pre-submit-$M.txt"
cat "$LOG/pre-submit-$M.txt"
PYTHONDONTWRITEBYTECODE=1 python3 -E -s -B -m harness.s2_locale.ap_delta_v5 submit "$MIN/$M" --source-dir . --no-e-deadline > "$LOG/submit-$M.out"
job=$(python3 -E -s -B -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d["job_id"])' "$LOG/submit-$M.out")
python3 -E -s -B -c 'import json,sys; d=json.load(open(sys.argv[1])); print("JOB", d["job_id"], d["manifest_sha256"], d["minutes"])' "$LOG/submit-$M.out"
echo "$(date -u +%FT%TZ) submitted $M job=$job" >> "$LOG/ops.log"
