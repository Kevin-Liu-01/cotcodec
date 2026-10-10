#!/usr/bin/env bash
# Operator script: submit one registered S1a A1 pair (q2-stage1-rescoped-v1 section 5.5).
# The VM manifest ($P/$N-vm.json) is rendered from the frozen plan and validated beforehand;
# gpu-values.json holds the GPU template's host fills (O2 overlay, freeze commit, O2 archive,
# the size's model receipt). Order: verify + check-chain in the export, lane validate, the
# whole queue empty, VM job first (lane submit), GPU half rendered from the validated VM
# manifest with the VM job's id, submitter dry-run, sbatch --test-only of the same argv,
# the GPU job (--dependency=after:VM), then its id into gpu_job_id for the lane.
# Usage: [WATCH_S=seconds] submit-pair.sh NAME (WATCH_S bounds the end-state and queue
# watchers; default 21600; a session-2 pair held by --begin needs the 12 h gap plus its run).
set -euo pipefail
N="$1"
W="${WATCH_S:-21600}"
[[ "$W" =~ ^[1-9][0-9]{0,5}$ ]] || { echo "WATCH_S must be seconds" >&2; exit 2; }
R=/home/kevin/cotcodec-runs/stage0/q2-stage1
X=$R/src/d5f57988ab94e0c098feddb744b78b73b5ad88ca
P=$R/pairs/$N
PY312=/home/kevin/.local/share/uv/python/cpython-3.12-linux-x86_64-gnu/bin/python3.12
L=$P/ops.log
log() { echo "$(date -u +%FT%TZ) $*" | tee -a "$L"; }
q() { squeue -a -h -o '%i|%u|%j|%T|%M|%C|%b' | tr '\n' ';'; }

test -f "$P/$N-vm.json" && test -f "$P/gpu-values.json"
test ! -e "$P/vm-submit.json" && test ! -e "$P/gpu_job_id" && test ! -e "$P/$N-gpu.yaml"
cd "$X"

{
  echo "== $X ($(date -u +%FT%TZ))"
  echo "\$ python3.12 -E -s -B scripts/preregister.py verify q2-stage1-rescoped-v1"
  "$PY312" -E -s -B scripts/preregister.py verify q2-stage1-rescoped-v1
  echo "\$ python3.12 -E -s -B scripts/preregister.py check-chain"
  "$PY312" -E -s -B scripts/preregister.py check-chain
} >"$P/preregister-verify.txt" 2>&1 || { log "verify/check-chain FAILED; nothing submitted"; exit 4; }
log "preregister verify and check-chain PASS in $X"

python3 -E -s -B -m harness.q2_stage1.lane validate "$P/$N-vm.json" --source-dir "$X" \
  >"$P/lane-validate.json"
log "lane validate: $(cat "$P/lane-validate.json")"

Q="$(q)"
log "squeue-before-$N-VM: [$Q]"
nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader >>"$L"
[ -z "$Q" ] || { log "queue not empty; nothing submitted"; exit 5; }

python3 -E -s -B -m harness.q2_stage1.lane submit "$P/$N-vm.json" --source-dir "$X" \
  >"$P/vm-submit.json"
VM=$(python3 -E -s -c 'import json,sys; print(json.load(open(sys.argv[1]))["job_id"])' \
  "$P/vm-submit.json")
log "$N VM job submitted: $VM"

python3 -E -s -B scripts/render_q2_stage1_manifest.py gpu --vm-manifest "$P/$N-vm.json" \
  --vm-job-id "$VM" --values "$P/gpu-values.json" --out "$P/$N-gpu.yaml" \
  >"$P/$N-gpu.yaml.sha256"
python3 -E -s -B scripts/submit_docker_research_job.py "$P/$N-gpu.yaml" --dry-run \
  >"$P/gpu-dry-run.json"
# The submitter's --test-only drops sbatch's stderr; run the identical argv
# (sbatch_argv(manifest, test_only=True)) here so the reply is kept.
python3 -E -s - "$P/gpu-dry-run.json" >"$P/gpu-test-only-argv.json" <<'PY'
import json, sys
argv = json.load(open(sys.argv[1]))["argv"]
print(json.dumps(argv[:-1] + ["--test-only", argv[-1]]))
PY
mapfile -t TARGV < <(python3 -E -s -c 'import json,sys; print("\n".join(json.load(open(sys.argv[1]))))' \
  "$P/gpu-test-only-argv.json")
set +e
"${TARGV[@]}" >"$P/gpu-test-only.txt" 2>&1
trc=$?
set -e
echo "exit=$trc" >>"$P/gpu-test-only.txt"
log "GPU half --test-only exit $trc: $(head -c 300 "$P/gpu-test-only.txt" | tr '\n' ' ')"
[ "$trc" = 0 ] || { log "GPU test-only failed; GPU job NOT submitted (VM $VM waits)"; exit 6; }

Q="$(squeue -a -h -o '%i|%u|%j|%T|%M|%C|%b' | grep -v "^$VM|" | tr '\n' ';' || true)"
log "squeue-before-$N-GPU (foreign): [$Q]"
GPU=$(python3 -E -s -B scripts/submit_docker_research_job.py "$P/$N-gpu.yaml")
printf '%s\n' "$GPU" >"$P/gpu_job_id.tmp"
mv "$P/gpu_job_id.tmp" "$P/gpu_job_id"
log "$N GPU job submitted: $GPU (after:$VM)"

mkdir -p "$P/slurm-state"
nohup timeout "$W" "$X/scripts/record_slurm_end_states.sh" "$P/slurm-state" "$VM" "$GPU" \
  >"$P/end-states.log" 2>&1 </dev/null &
nohup timeout "$W" bash -c '
  P="$1"; VM="$2"; GPU="$3"
  while :; do
    echo "$(date -u +%FT%TZ) $(squeue -a -h -o "%i|%u|%j|%T|%M|%C|%b" | tr "\n" ";")" >>"$P/squeue-watch.log"
    for j in "$VM" "$GPU"; do
      s="$(scontrol show job -o "$j" 2>/dev/null)" && [ -n "$s" ] && printf "%s\n" "$s" >"$P/scontrol-$j.last.txt"
    done
    squeue -a -h -o "%i" 2>/dev/null | grep -qE "^($VM|$GPU)\$" || break
    sleep 15
  done' _ "$P" "$VM" "$GPU" >/dev/null 2>&1 </dev/null &
log "watchers started for $VM and $GPU (timeout ${W} s)"
echo "VM=$VM GPU=$GPU"
