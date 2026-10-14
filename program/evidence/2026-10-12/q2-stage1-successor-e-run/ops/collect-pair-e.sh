#!/usr/bin/env bash
# Operator script: after an E pair has left the queue, run DR0 on the VM lane's records (the
# registered command, q2-stage1-successor-e-v1 section 18 (iii) step 1:
# `python -m harness.q2_stage1e.analysis dr0 --run-dir RUN --plan PLAN`, exit 3 when DR0
# fires), list every file of both run directories with SHA-256, and write a tar of the
# evidence subset to stdout. Step logs, replies, captures and the engine log stay on the host
# (section 20). S1a's collect-pair.sh adapted to E's paths and DR0 command.
# Usage: collect-pair-e.sh NAME VM_JOB GPU_JOB > NAME.tar
set -euo pipefail
N="$1"; VM="$2"; GPU="$3"
F=f6144d6bf745d944cb016cfc2b9894e1dbf7eb66
R=/home/kevin/cotcodec-runs/stage0/q2-stage1e
G=/home/kevin/cotcodec-runs/stage0/q2-stage1/gpu
S=/home/kevin/cotcodec-runs/stage0/q2-stage1/slurm
X=$R/src/$F
P=$R/pairs/$N
PLAN=program/evidence/2026-10-11/q2-stage1-successor-e/plan/plan-e.json
cd "$X"
if [ ! -e "$P/dr0.json" ]; then
  set +e
  python3 -E -s -B -m harness.q2_stage1e.analysis dr0 --run-dir "$R/runs/$VM" --plan "$X/$PLAN" \
    >"$P/dr0.json" 2>"$P/dr0.stderr"
  echo "exit=$?" >"$P/dr0.exit"
  set -e
fi
(cd "$R/runs/$VM" && find . -type f -print0 | sort -z | xargs -0 sha256sum) >"$P/vm-raw-sha256sums.txt"
(cd "$G/$GPU" && find . -type f -print0 | sort -z | xargs -0 sha256sum) >"$P/gpu-raw-sha256sums.txt"
files_vm=(manifest.json episodes.jsonl lane-receipt.json preflight.txt)
files_gpu=(bridge/ready.json bridge/stopped.json bridge/first_request.json bridge/gpu.jsonl
  bridge/usr1.json command.json container-doctor.txt gpu-prolog.env job.env manifest.json
  model-receipt.json model-verification.txt provenance-verification.txt termination.env)
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
mkdir -p "$stage/vm-$VM" "$stage/gpu-$GPU/bridge" "$stage/pair"
for f in "${files_vm[@]}"; do
  [ -f "$R/runs/$VM/$f" ] && cp "$R/runs/$VM/$f" "$stage/vm-$VM/$f"
done
for f in "${files_gpu[@]}"; do
  [ -f "$G/$GPU/$f" ] && cp "$G/$GPU/$f" "$stage/gpu-$GPU/$f"
done
cp "$S/slurm-q2e-$N-$VM.out" "$stage/vm-$VM/" 2>/dev/null || true
cp "$G/slurm-$GPU.out" "$stage/gpu-$GPU/" 2>/dev/null || true
mv "$P/vm-raw-sha256sums.txt" "$stage/vm-$VM/raw-sha256sums.txt"
mv "$P/gpu-raw-sha256sums.txt" "$stage/gpu-$GPU/raw-sha256sums.txt"
for f in ops.log host.json gpu-values.json "$N-vm.json" "$N-vm.json.sha256" "$N-gpu.yaml" \
  "$N-gpu.yaml.sha256" vm-submit.json vm-submit-dry-run.json gpu-dry-run-placeholder.json \
  gpu-dry-run.json gpu-test-only-argv.json gpu-test-only.txt lane-validate.json \
  preregister-verify.txt squeue-watch.log end-states.log dr0.json dr0.stderr dr0.exit \
  job-checks.json "scontrol-$VM.last.txt" "scontrol-$GPU.last.txt"; do
  [ -f "$P/$f" ] && cp "$P/$f" "$stage/pair/$f"
done
[ -d "$P/slurm-state" ] && cp -r "$P/slurm-state" "$stage/pair/slurm-state"
tar -C "$stage" -cf - .
