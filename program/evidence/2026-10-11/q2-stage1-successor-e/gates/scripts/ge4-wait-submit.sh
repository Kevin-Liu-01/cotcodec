#!/usr/bin/env bash
# Submit G-E4 (E's development smoke) only when the whole Slurm queue is empty; poll every 2 s for at most ~220 s.
set -u
X=/home/kevin/cotcodec-runs/stage0/q2-stage1e/src/8a23a483dc39f6e34aa52dca75a9a5e106b18375
G=/home/kevin/cotcodec-runs/stage0/q2-stage1e/gates
OUT=$G/ge4-submit.json
mkdir -p $G
if [ -e "$OUT" ]; then echo "already submitted:"; cat "$OUT" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("job_id"))'; squeue -h -o "%i %j %T %M %l"; exit 0; fi
for i in $(seq 1 105); do
  q=$(squeue -h -o "%i")
  if [ -z "$q" ]; then
    t=$(date -u +%FT%TZ)
    cd $X && python3 -E -s -B -m harness.q2_stage1e.lane submit experiments/manifests/q2-stage1e/dev-smoke-v1.json --source-dir . > "$OUT.tmp"
    rc=$?
    mv "$OUT.tmp" "$OUT"
    echo "queue empty at $t; submit rc=$rc"
    python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print("job_id", d.get("job_id"), "manifest", d.get("manifest_sha256"))' "$OUT"
    sleep 3
    squeue -h -o "%i %j %u %T %M %l %C"
    exit 0
  fi
  sleep 2
done
date -u +%T; echo "still busy:"; squeue -h -o "%i %j %T %M %l"
