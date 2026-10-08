#!/usr/bin/env bash
# In the image built from the branch head (Slurm build job $1, clone sha $2):
# (1) the torch-dependent dense tests inside the image (CPU only, network none; pytest, pure Python,
#     mounted read-only from ../torch-tests-776/pylib since the image has no pytest);
# (2) the PID-1 SIGUSR1 test from the host checkout at the same commit against that image.
set -uo pipefail
build=$1
sha=$2
base=$HOME/cotcodec-runs/stage0/q3-dense-v2
out=$base/ops/timing-2/tests
mkdir -p "$out/torch-in-image-$build" "$out/pid1-image-$build"
img=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["image_id"])' $HOME/cotcodec-runs/builds/*-architecture-$build/receipt.json)
{
echo "start=$(date -u +%Y-%m-%dT%H:%M:%SZ) image=$img build=$build"
timeout 1800 srun --partition=research --nodes=1 --ntasks=1 --cpus-per-task=16 --mem=64G --time=00:30:00 \
  --job-name=dense-v2-torch-tests \
  docker run --rm --network none --user "$(id -u):$(id -g)" -e USER=cotcodec -e LOGNAME=cotcodec \
    -e HOME=/tmp -e HF_HUB_OFFLINE=1 -e PYTHONDONTWRITEBYTECODE=1 -e OMP_NUM_THREADS=8 \
    -e PYTHONPATH=/pylib -v "$base/ops/torch-tests-776/pylib:/pylib:ro" --entrypoint python "$img" \
    -m pytest -q -p no:cacheprovider tests/test_dense_headroom_v2_torch.py tests/test_dense_headroom_torch.py \
    tests/test_run_dense_headroom_precheck.py tests/test_dense_headroom_data.py \
    tests/test_dense_headroom_v2_timing.py tests/test_dense_headroom_v2_signals.py \
    tests/test_dense_headroom_v2_prereg.py tests/test_dense_headroom_v2_manifests.py
echo "exit=$?"
echo "end=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} > "$out/torch-in-image-$build/pytest-torch-image-$build.log" 2>&1
tail -3 "$out/torch-in-image-$build/pytest-torch-image-$build.log"
cd "$HOME/cotcodec-scratch/q3v2-suite-$sha"
{
echo "start=$(date -u +%Y-%m-%dT%H:%M:%SZ) image=$img head=$(git rev-parse HEAD)"
COTCODEC_USR1_PID1_IMAGE=$img timeout 900 srun --partition=research --nodes=1 --ntasks=1 --cpus-per-task=8 \
  --mem=32G --time=00:15:00 --job-name=dense-v2-pid1 \
  uv run --locked --extra dev pytest -q -rA -p no:cacheprovider tests/test_dense_headroom_v2_usr1_pid1.py
echo "exit=$?"
echo "end=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} > "$out/pid1-image-$build/pytest-usr1-pid1.log" 2>&1
tail -3 "$out/pid1-image-$build/pytest-usr1-pid1.log"
