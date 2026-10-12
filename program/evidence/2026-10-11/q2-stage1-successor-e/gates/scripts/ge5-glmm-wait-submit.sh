#!/usr/bin/env bash
# G-E5: the unchanged glmm.R on E-shaped synthetic rows (113 tasks, seed 42, 200 refits) in the
# pinned GLMM container, one CPU-only s1a-cpu.sbatch run, submitted only when the whole Slurm
# queue is empty; poll every 2 s for at most ~220 s.
set -u
X=/home/kevin/cotcodec-runs/stage0/q2-stage1e/src/8a23a483dc39f6e34aa52dca75a9a5e106b18375
G=/home/kevin/cotcodec-runs/stage0/q2-stage1e/gates
OUT=$G/ge5-glmm-submit.json
if [ -e "$OUT" ]; then echo "already submitted:"; cat "$OUT"; squeue -h -o "%i %j %T %M %l"; exit 0; fi
IMAGE=sha256:b15584f3954f1c83fc3e5067e29c57c5c55e3b2a50ef28e4e68a394e595aabed
ARGV='["sh","-c","cp /opt/q2/r-packages.json /opt/q2/r-packages.sha256 /out/ || exit 90; Rscript /src/harness/q2_stage1/glmm.R /inputs/synthetic-e-k113.csv /out/glmm-synthetic-e-k113.json 200 42 >/out/glmm.log 2>&1; rc=$?; echo $rc >/out/glmm.exit; exit $rc"]'
HEX=$(python3 -c 'import json,sys; print(json.dumps(json.loads(sys.argv[1])).encode().hex())' "$ARGV")
test "$(sha256sum $G/glmm-inputs/synthetic-e-k113.csv | cut -d' ' -f1)" = 41d87779d26d280e98fc5ec672a87ee7a075a9b2cd07d5669360797d7c83b707 || { echo "input digest differs"; exit 2; }
test ! -e $G/glmm-out || { echo "$G/glmm-out exists"; exit 2; }
CMD=(sbatch --parsable --time=02:00:00 --job-name=q2e-ge5-glmm --output=$G/logs/%x-%j.out
  "--export=ALL,Q2M_MODE=run,Q2M_IMAGE_ID=$IMAGE,Q2M_ARGV_JSON_HEX=$HEX,Q2M_SOURCE=$X,Q2M_RUN_DIR=$G/glmm-out,Q2M_INPUTS=$G/glmm-inputs"
  $X/infra/slurm/host-single-node/s1a-cpu.sbatch)
for i in $(seq 1 105); do
  q=$(squeue -h -o "%i")
  if [ -z "$q" ]; then
    t=$(date -u +%FT%TZ)
    mkdir -p $G/logs $G/glmm-out
    id=$(cd $G && "${CMD[@]}")
    rc=$?
    python3 -c 'import json,sys; print(json.dumps({"submitted_at": sys.argv[1], "rc": int(sys.argv[2]), "job_id": sys.argv[3], "command": sys.argv[4:]}, indent=1))' "$t" "$rc" "$id" "${CMD[@]}" > "$OUT"
    echo "queue empty at $t; sbatch rc=$rc job $id"
    sleep 3
    squeue -h -o "%i %j %u %T %M %l %C"
    exit 0
  fi
  sleep 2
done
date -u +%T; echo "still busy:"; squeue -h -o "%i %j %T %M %l"
