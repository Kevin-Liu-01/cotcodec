#!/usr/bin/env bash
# Operator script: submit one registered E pair (q2-stage1-successor-e-v1 sections 5.3, 6),
# S1a's submit-pair.sh adapted to E's lane, renderer and quiet-host rule (section 6.4).
# The VM manifest ($P/$N-vm.json) is rendered from E's plan with scripts/render_q2e_manifest.py
# beforehand; gpu-values.json holds the GPU template's host fills (the OE overlay, the freeze
# commit, OE's source archive, the size's model receipt and artifact root).
# Order: verify + check-chain in the export; lane validate; lane submit --dry-run; a GPU half
# rendered with a placeholder VM id through the submitter's --dry-run (nothing submitted yet);
# then wait (2 s polls, at most about 180 s per invocation) until the whole Slurm queue is
# empty; VM job first (lane submit); the GPU half rendered from the validated VM manifest with
# the VM job's id; the submitter's dry run; sbatch --test-only of the same argv; a foreign-queue
# check; the GPU job (--dependency=after:VM); its id into gpu_job_id for the lane; end-state and
# 15-second queue watchers.
# Usage: submit-pair-e.sh NAME   (exit 7: the queue stayed busy, nothing submitted; rerun)
set -euo pipefail
N="$1"
F=f6144d6bf745d944cb016cfc2b9894e1dbf7eb66
R=/home/kevin/cotcodec-runs/stage0/q2-stage1e
X=$R/src/$F
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
  echo "\$ python3.12 -E -s -B scripts/preregister.py verify q2-stage1-successor-e-v1"
  "$PY312" -E -s -B scripts/preregister.py verify q2-stage1-successor-e-v1
  echo "\$ python3.12 -E -s -B scripts/preregister.py check-chain"
  "$PY312" -E -s -B scripts/preregister.py check-chain
  echo "sha256 registration: $(sha256sum program/preregistrations/q2-stage1-successor-e-v1.md | cut -d' ' -f1)"
} >"$P/preregister-verify.txt" 2>&1 || { log "verify/check-chain FAILED; nothing submitted"; exit 4; }
log "preregister verify and check-chain PASS in $X"

python3 -E -s -B -m harness.q2_stage1e.lane validate "$P/$N-vm.json" --source-dir "$X" \
  >"$P/lane-validate.json"
log "lane validate: $(cat "$P/lane-validate.json")"
python3 -E -s -B -m harness.q2_stage1e.lane submit "$P/$N-vm.json" --source-dir "$X" --dry-run \
  >"$P/vm-submit-dry-run.json"
log "lane submit --dry-run: $(python3 -E -s -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d["manifest_sha256"], " ".join(a for a in d["argv"] if not a.startswith("--export")))' "$P/vm-submit-dry-run.json")"
PRE=$(mktemp -d)
trap 'rm -rf "$PRE"' EXIT
python3 -E -s -B scripts/render_q2e_manifest.py gpu --vm-manifest "$P/$N-vm.json" \
  --vm-job-id 1 --values "$P/gpu-values.json" --out "$PRE/placeholder-gpu.yaml" >/dev/null
python3 -E -s -B scripts/submit_docker_research_job.py "$PRE/placeholder-gpu.yaml" --dry-run \
  >"$P/gpu-dry-run-placeholder.json"
log "GPU half with a placeholder VM id passed the submitter's --dry-run"

Q=x
for i in $(seq 1 90); do
  Q="$(q)"
  [ -z "$Q" ] && break
  sleep 2
done
log "squeue-before-$N-VM: [$Q]"
nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader >>"$L"
[ -z "$Q" ] || { log "queue not empty; nothing submitted"; exit 7; }

python3 -E -s -B -m harness.q2_stage1e.lane submit "$P/$N-vm.json" --source-dir "$X" \
  >"$P/vm-submit.json"
VM=$(python3 -E -s -c 'import json,sys; print(json.load(open(sys.argv[1]))["job_id"])' \
  "$P/vm-submit.json")
log "$N VM job submitted: $VM"

python3 -E -s -B scripts/render_q2e_manifest.py gpu --vm-manifest "$P/$N-vm.json" \
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
nohup timeout 14400 "$X/scripts/record_slurm_end_states.sh" "$P/slurm-state" "$VM" "$GPU" \
  >"$P/end-states.log" 2>&1 </dev/null &
nohup timeout 14400 bash -c '
  P="$1"; VM="$2"; GPU="$3"
  while :; do
    echo "$(date -u +%FT%TZ) $(squeue -a -h -o "%i|%u|%j|%T|%M|%C|%b" | tr "\n" ";")" >>"$P/squeue-watch.log"
    for j in "$VM" "$GPU"; do
      s="$(scontrol show job -o "$j" 2>/dev/null)" && [ -n "$s" ] && printf "%s\n" "$s" >"$P/scontrol-$j.last.txt"
    done
    squeue -a -h -o "%i" 2>/dev/null | grep -qE "^($VM|$GPU)\$" || break
    sleep 15
  done' _ "$P" "$VM" "$GPU" >/dev/null 2>&1 </dev/null &
log "watchers started for $VM and $GPU"
echo "VM=$VM GPU=$GPU"
