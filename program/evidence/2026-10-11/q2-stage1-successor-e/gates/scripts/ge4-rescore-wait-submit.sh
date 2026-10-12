#!/usr/bin/env bash
# G-E4's offline rescoring (rescore.py capture, unchanged) of the smoke's captured states: one
# CPU-only s1a-cpu.sbatch run in the metric image, submitted only when the whole Slurm queue is
# empty; poll every 2 s for at most ~220 s.
set -u
X=/home/kevin/cotcodec-runs/stage0/q2-stage1e/src/8a23a483dc39f6e34aa52dca75a9a5e106b18375
G=/home/kevin/cotcodec-runs/stage0/q2-stage1e/gates
OUT=$G/ge4-rescore-submit.json
VM=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["job_id"])' "$G/ge4-submit.json")
RUN=/home/kevin/cotcodec-runs/stage0/q2-stage1e/runs/$VM
[[ "$VM" =~ ^[0-9]+$ && -f $RUN/lane-receipt.json ]] || { echo "no finished run directory for $VM"; exit 2; }
if [ -e "$OUT" ]; then echo "already submitted:"; cat "$OUT"; squeue -h -o "%i %j %T %M %l"; exit 0; fi
METRIC=sha256:2006c1a9247e4911a82508cd22e9d9a7efc5c13e35a20e8a03baac7112876230
ARGV='["/opt/venv-lock/bin/python","-m","harness.q2_stage1.rescore","capture","--run-dir","/ro/run","--osworld","/inputs/OSWorld","--file-cache","/inputs/file_cache_1e112283/files","--out","/out/rescored.jsonl"]'
HEX=$(python3 -c 'import json,sys; print(json.dumps(json.loads(sys.argv[1])).encode().hex())' "$ARGV")
mkdir -p $G/logs $G/rescore-$VM
CMD=(sbatch --parsable --time=01:00:00 --job-name=q2e-ge4-rescore-$VM --output=$G/logs/%x-%j.out
  "--export=ALL,Q2M_MODE=run,Q2M_IMAGE_ID=$METRIC,Q2M_ARGV_JSON_HEX=$HEX,Q2M_SOURCE=$X,Q2M_RUN_DIR=$G/rescore-$VM,Q2M_INPUTS=/home/kevin/cotcodec-runs/stage0/q2-evaluator-mutation/inputs,Q2M_EXTRA_RO=$RUN:/ro/run"
  $X/infra/slurm/host-single-node/s1a-cpu.sbatch)
for i in $(seq 1 105); do
  q=$(squeue -h -o "%i")
  if [ -z "$q" ]; then
    t=$(date -u +%FT%TZ)
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
