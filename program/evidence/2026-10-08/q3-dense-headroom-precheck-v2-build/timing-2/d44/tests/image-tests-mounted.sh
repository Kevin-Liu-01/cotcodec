#!/usr/bin/env bash
# D44 (no image rebuild, no GPU): in the latest image (Slurm build 825, from 8c3f076), with the
# scratch clone of the new head's harness/, scripts/, tests/, experiments/ and program/ mounted
# read-only over /workspace/cotcodec (the image's .venv stays the image's), CPU only, network none:
# (1) the torch-dependent dense tests (the list of timing-2/tests/image-tests.sh; pytest, pure
#     Python, mounted from ../torch-tests-776/pylib since the image has no pytest);
# (2) the v2 CPU doctor on the mounted code.
# Usage: image-tests-mounted.sh SHA   (clone at ~/cotcodec-scratch/q3v2-suite-SHA)
set -uo pipefail
sha=$1
build=825
base=$HOME/cotcodec-runs/stage0/q3-dense-v2
clone=$HOME/cotcodec-scratch/q3v2-suite-$sha
out=$base/ops/timing-2/d44/tests
mkdir -p "$out"
img=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["image_id"])' $HOME/cotcodec-runs/builds/*-architecture-$build/receipt.json)
w=/workspace/cotcodec
mounts=()
for d in harness scripts tests experiments program; do mounts+=(-v "$clone/$d:$w/$d:ro"); done
{
echo "start=$(date -u +%Y-%m-%dT%H:%M:%SZ) image=$img build=$build mounted=$(git -C "$clone" rev-parse HEAD) dirty=$(git -C "$clone" status --porcelain --untracked-files=no | wc -l)"
timeout 1800 srun --partition=research --nodes=1 --ntasks=1 --cpus-per-task=16 --mem=64G --time=00:30:00 \
  --job-name=dense-v2-torch-tests-d44 \
  docker run --rm --network none --user "$(id -u):$(id -g)" -e USER=cotcodec -e LOGNAME=cotcodec \
    -e HOME=/tmp -e HF_HUB_OFFLINE=1 -e PYTHONDONTWRITEBYTECODE=1 -e OMP_NUM_THREADS=8 \
    "${mounts[@]}" -e PYTHONPATH=/pylib -v "$base/ops/torch-tests-776/pylib:/pylib:ro" \
    --entrypoint python "$img" \
    -m pytest -q -p no:cacheprovider tests/test_dense_headroom_v2_torch.py tests/test_dense_headroom_torch.py \
    tests/test_run_dense_headroom_precheck.py tests/test_dense_headroom_data.py \
    tests/test_dense_headroom_v2_timing.py tests/test_dense_headroom_v2_signals.py \
    tests/test_dense_headroom_v2_prereg.py tests/test_dense_headroom_v2_manifests.py
echo "exit=$?"
echo "end=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} > "$out/pytest-torch-image-$build-mounted-$sha.log" 2>&1
tail -3 "$out/pytest-torch-image-$build-mounted-$sha.log"
{
echo "start=$(date -u +%Y-%m-%dT%H:%M:%SZ) image=$img build=$build mounted=$(git -C "$clone" rev-parse HEAD)"
timeout 3000 srun --partition=research --nodes=1 --ntasks=1 --cpus-per-task=32 --mem=96G \
  --time=00:50:00 --job-name="dense-v2-cpu-doctor-d44" \
  docker run --rm --network none --user "$(id -u):$(id -g)" -e USER=cotcodec -e LOGNAME=cotcodec \
    -e HOME=/tmp -e HF_HUB_OFFLINE=1 -e PYTHONDONTWRITEBYTECODE=1 -e OMP_NUM_THREADS=8 \
    "${mounts[@]}" -v "$out:/out" --entrypoint python "$img" \
    scripts/run_dense_headroom_precheck_v2_doctor.py --output "/out/doctor-cpu-image-$build-mounted-$sha.json"
echo "exit=$?"
echo "end=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} > "$out/doctor-cpu-image-$build-mounted-$sha.log" 2>&1
tail -3 "$out/doctor-cpu-image-$build-mounted-$sha.log" | cut -c1-400
