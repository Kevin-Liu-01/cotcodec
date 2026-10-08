#!/usr/bin/env bash
# Freeze step 3 of q3-dense-headroom-precheck-v1: the CPU doctor in the image built from the
# freeze commit a369e6d (Slurm build job given as $1), on CPU only (no GPU, no network) inside
# a Slurm step. Flags as program/evidence/2026-10-07/q3-dense-headroom-precheck/run-in-image.sh,
# except that no worktree is mounted: the doctor runs the source baked into the image
# (/workspace/cotcodec at a369e6d), so this exercises the image itself.
# Usage: run-doctor-in-image.sh BUILD_JOB_ID
set -uo pipefail
build_job=$1
base="$HOME/cotcodec-runs/stage0/q3-dense"
receipt=$(ls "$HOME"/cotcodec-runs/builds/a369e6d2-architecture-"$build_job"/receipt.json)
img=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["image_id"])' "$receipt")
out="$base/ops/doctor"
mkdir -p "$out"
{
  echo "start=$(date -u +%Y-%m-%dT%H:%M:%SZ) image=$img build_receipt=$receipt"
  timeout 3000 srun --partition=research --nodes=1 --ntasks=1 --cpus-per-task=32 --mem=96G \
    --time=00:50:00 --job-name="dense-cpu-doctor-a369e6d" \
    docker run --rm --network none --user "$(id -u):$(id -g)" -e USER=cotcodec -e HOME=/tmp \
      -e HF_HUB_OFFLINE=1 -e PYTHONDONTWRITEBYTECODE=1 -e OMP_NUM_THREADS=8 \
      -v "$out:/out" --entrypoint python "$img" \
      scripts/run_dense_headroom_precheck_doctor.py --output /out/doctor-cpu-image.json
  echo "exit=$?"
  echo "end=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} > "$out/log.txt" 2>&1
tail -5 "$out/log.txt"
