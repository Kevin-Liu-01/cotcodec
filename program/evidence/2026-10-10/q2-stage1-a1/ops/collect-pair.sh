#!/usr/bin/env bash
# Operator script: after an S1a A1 pair has left the queue, run DR0 on the VM lane's records
# (rules.job_dr0 via `python -m harness.q2_stage1.rules dr0`, the frozen plan), list every
# file of both run directories with SHA-256, and write a tar of the evidence subset to
# stdout. Step logs, replies, captures and the engine log stay on the host (section 16).
# Usage: collect-pair.sh NAME VM_JOB GPU_JOB > NAME.tar
set -euo pipefail
N="$1"; VM="$2"; GPU="$3"
R=/home/kevin/cotcodec-runs/stage0/q2-stage1
X=$R/src/d5f57988ab94e0c098feddb744b78b73b5ad88ca
P=$R/pairs/$N
PLAN=program/evidence/2026-10-09/q2-stage1-prefreeze/plan/plan-a0a.json
cd "$X"
if [ ! -e "$P/dr0.json" ]; then
  set +e
  python3 -E -s -B -m harness.q2_stage1.rules dr0 --run-dir "$R/runs/$VM" --plan "$X/$PLAN" \
    >"$P/dr0.json" 2>"$P/dr0.stderr"
  echo "exit=$?" >"$P/dr0.exit"
  set -e
fi
(cd "$R/runs/$VM" && find . -type f -print0 | sort -z | xargs -0 sha256sum) >"$P/vm-raw-sha256sums.txt"
(cd "$R/gpu/$GPU" && find . -type f -print0 | sort -z | xargs -0 sha256sum) >"$P/gpu-raw-sha256sums.txt"
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
  [ -f "$R/gpu/$GPU/$f" ] && cp "$R/gpu/$GPU/$f" "$stage/gpu-$GPU/$f"
done
cp "$R/slurm/slurm-s1a-$N-$VM.out" "$stage/vm-$VM/" 2>/dev/null || true
cp "$R/gpu/slurm-$GPU.out" "$stage/gpu-$GPU/" 2>/dev/null || true
mv "$P/vm-raw-sha256sums.txt" "$stage/vm-$VM/raw-sha256sums.txt"
mv "$P/gpu-raw-sha256sums.txt" "$stage/gpu-$GPU/raw-sha256sums.txt"
for f in ops.log host.json gpu-values.json "$N-vm.json" "$N-gpu.yaml" "$N-gpu.yaml.sha256" \
  vm-submit.json gpu-dry-run.json gpu-test-only-argv.json gpu-test-only.txt lane-validate.json \
  preregister-verify.txt squeue-watch.log end-states.log dr0.json dr0.stderr dr0.exit \
  "scontrol-$VM.last.txt" "scontrol-$GPU.last.txt"; do
  [ -f "$P/$f" ] && cp "$P/$f" "$stage/pair/$f"
done
[ -d "$P/slurm-state" ] && cp -r "$P/slurm-state" "$stage/pair/slurm-state"
tar -C "$stage" -cf - .
