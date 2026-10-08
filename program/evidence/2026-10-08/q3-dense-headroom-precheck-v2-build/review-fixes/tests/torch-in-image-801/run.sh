#!/usr/bin/env bash
# Torch-dependent dense tests inside the image built from b8977d9 (Slurm 801), CPU only, network none.
# pytest (pure Python) is mounted read-only from ../torch-tests-776/pylib, since the image has no pytest.
set -uo pipefail
here=$(cd "$(dirname "$0")" && pwd)
img=$(python3 -c "import json; print(json.load(open(\"$here/../image-build-receipt-801.json\"))[\"image_id\"])")
echo "start=$(date -u +%Y-%m-%dT%H:%M:%SZ) image=$img"
srun --partition=research --nodes=1 --ntasks=1 --cpus-per-task=16 --mem=64G --time=00:30:00 \
  --job-name=dense-v2-torch-tests \
  docker run --rm --network none --user "$(id -u):$(id -g)" -e USER=cotcodec -e LOGNAME=cotcodec \
    -e HOME=/tmp -e HF_HUB_OFFLINE=1 -e PYTHONDONTWRITEBYTECODE=1 -e OMP_NUM_THREADS=8 \
    -e PYTHONPATH=/pylib -v "$here/../torch-tests-776/pylib:/pylib:ro" --entrypoint python "$img" \
    -m pytest -q -p no:cacheprovider tests/test_dense_headroom_v2_torch.py tests/test_dense_headroom_torch.py \
    tests/test_run_dense_headroom_precheck.py tests/test_dense_headroom_data.py \
    tests/test_dense_headroom_v2_timing.py tests/test_dense_headroom_v2_signals.py \
    tests/test_dense_headroom_v2_prereg.py tests/test_dense_headroom_v2_manifests.py
echo "exit=$?"
echo "end=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
