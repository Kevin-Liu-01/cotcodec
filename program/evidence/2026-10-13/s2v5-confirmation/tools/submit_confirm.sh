#!/usr/bin/env bash
# Usage (on the host, via ssh bash -s -- PART): snapshot the host, refuse unless the whole queue
# is empty and E4's 4B pair has ended (both of its jobs recorded final by E's own watcher), then
# submit PART (p1 or p2) through ap_delta_v5 submit --no-e-deadline (E4 is E's last session) and
# start harness q2's own Slurm end-state watcher on the job.
set -euo pipefail
P="$1"
C=/home/kevin/cotcodec-runs/stage0/s2v5/confirm
SRC=$C/src/f24557aa555987157b5b75049ec1cb1b8e0a81a2
MAN=$C/src/26a9477cfa12da43f82e5fc78314804089cc0949/experiments/manifests/s2v5/confirm-a6-v1-$P.json
E=/home/kevin/cotcodec-runs/stage0/q2-stage1e/pairs
OPS=$C/ops
mkdir -p "$OPS"
cd "$SRC"
q="$(squeue -a -h -o '%i|%j|%T|%M|%l|%C')"
if [ -n "$q" ]; then echo "REFUSE: queue not empty: $q"; exit 8; fi
n4=0
for f in "$E"/e-4b-e4/scontrol-*.last.txt; do
  [ -f "$f" ] || continue
  st=$(grep -oE 'JobState=[A-Z_]+' "$f" | head -1)
  case "$st" in
    JobState=COMPLETED|JobState=FAILED|JobState=CANCELLED|JobState=TIMEOUT|JobState=NODE_FAIL|JobState=OUT_OF_MEMORY) n4=$((n4 + 1));;
    *) echo "REFUSE: $(basename "$f") reads $st"; exit 7;;
  esac
done
[ "$n4" -ge 2 ] || { echo "REFUSE: E4's 4B pair has $n4 final end-state records"; exit 7; }
{
  echo "snapshot_utc=$(date -u +%FT%TZ)"
  echo "loadavg=$(cat /proc/loadavg)"
  echo "nproc=$(nproc)"
  echo "mem_avail_kb=$(grep MemAvailable /proc/meminfo | awk '{print $2}')"
  echo "squeue_all=[$q]"
  echo "docker_running=$(docker ps -q | wc -l)"
  echo "docker_labelled_cotcodec=$(docker ps -q --filter label=cotcodec.slurm_job | wc -l)"
  echo "e_pairs=$(ls "$E" | tr '\n' ' ')"
  for f in "$E"/e-9b-e4/scontrol-*.last.txt "$E"/e-4b-e4/scontrol-*.last.txt; do
    echo "e4_end $(basename "$(dirname "$f")")/$(basename "$f"): $(grep -oE 'JobId=[0-9]+|JobState=[A-Z_]+|StartTime=[^ ]+|EndTime=[^ ]+' "$f" | tr '\n' ' ')"
  done
  echo "manifest_file_sha256=$(sha256sum "$MAN" | cut -d' ' -f1)"
  echo "source_git_sha=$(cat "$SRC/.git_sha")"
} > "$OPS/pre-submit-$P.txt"
cat "$OPS/pre-submit-$P.txt"
PYTHONDONTWRITEBYTECODE=1 python3 -E -s -B -m harness.s2_locale.ap_delta_v5 submit "$MAN" \
  --source-dir "$SRC" --no-e-deadline > "$OPS/submit-$P.json"
J=$(python3 -E -s -B -c 'import json,sys; print(json.load(open(sys.argv[1]))["job_id"])' "$OPS/submit-$P.json")
echo "$(date -u +%FT%TZ) submitted $P job $J" >> "$OPS/ops.log"
nohup setsid timeout 86400 "$SRC/scripts/record_slurm_end_states.sh" "$C/runs/$J/slurm-state" "$J" \
  > "$OPS/watcher-$J.log" 2>&1 < /dev/null &
echo "JOB $J"
python3 -E -s -B -c 'import json,sys; d=json.load(open(sys.argv[1])); print({k: d[k] for k in d if k != "argv"})' "$OPS/submit-$P.json"
