#!/usr/bin/env bash
# q3-dense-headroom-precheck-v2: the v2 CPU doctor in the image built from the branch (Slurm build
# job $1), CPU only (no GPU, network none) inside a Slurm step, on the source baked into the image
# (/workspace/cotcodec at the build commit; no worktree is mounted). Flags as v1's
# program/evidence/2026-10-08/q3-dense-headroom-precheck/doctor/run-doctor-in-image.sh.
# Usage: run-doctor-in-image.sh BUILD_JOB_ID OUTPUT_NAME
set -uo pipefail
build_job=$1
name=$2
base="$HOME/cotcodec-runs/stage0/q3-dense-v2"
receipt=$(ls "$HOME"/cotcodec-runs/builds/*-architecture-"$build_job"/receipt.json)
img=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["image_id"])' "$receipt")
out="$base/ops/doctor"
mkdir -p "$out"
{
  echo "start=$(date -u +%Y-%m-%dT%H:%M:%SZ) image=$img build_receipt=$receipt"
  timeout 3000 srun --partition=research --nodes=1 --ntasks=1 --cpus-per-task=32 --mem=96G \
    --time=00:50:00 --job-name="dense-v2-cpu-doctor" \
    docker run --rm --network none --user "$(id -u):$(id -g)" -e USER=cotcodec -e LOGNAME=cotcodec \
      -e HOME=/tmp -e HF_HUB_OFFLINE=1 -e PYTHONDONTWRITEBYTECODE=1 -e OMP_NUM_THREADS=8 \
      -v "$out:/out" --entrypoint python "$img" \
      scripts/run_dense_headroom_precheck_v2_doctor.py --output "/out/$name.json"
  echo "exit=$?"
  echo "end=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} > "$out/$name.log" 2>&1
tail -5 "$out/$name.log"
