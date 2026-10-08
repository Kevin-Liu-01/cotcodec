#!/usr/bin/env bash
# Pre-check (development only): the doctor's timing_profile case with the 87242fa entry point,
# doctor and lanes module mounted over image 801 (b8977d9), CPU only, network none.
set -uo pipefail
base=$HOME/cotcodec-runs/stage0/q3-dense-v2
repo=$base/timing2-repo
out=$base/ops/timing-2/precheck
mkdir -p "$out"
img=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["image_id"])' "$base/ops/image-build-receipt-801.json")
w=/workspace/cotcodec
{
echo "start=$(date -u +%Y-%m-%dT%H:%M:%SZ) image=$img (801, b8977d9) mounted from $(git -C $repo rev-parse HEAD)"
timeout 1500 srun --partition=research --nodes=1 --ntasks=1 --cpus-per-task=16 --mem=64G \
  --time=00:25:00 --job-name="dense-v2-timing-precheck" \
  docker run --rm --network none --user "$(id -u):$(id -g)" -e USER=cotcodec -e LOGNAME=cotcodec \
    -e HOME=/tmp -e HF_HUB_OFFLINE=1 -e PYTHONDONTWRITEBYTECODE=1 -e OMP_NUM_THREADS=8 \
    -v "$repo/scripts/run_dense_headroom_precheck_v2.py:$w/scripts/run_dense_headroom_precheck_v2.py:ro" \
    -v "$repo/scripts/run_dense_headroom_precheck_v2_doctor.py:$w/scripts/run_dense_headroom_precheck_v2_doctor.py:ro" \
    -v "$repo/harness/dense_headroom_v2_lanes.py:$w/harness/dense_headroom_v2_lanes.py:ro" \
    -v "$out:/out" --entrypoint python "$img" -c '
import json, pathlib, sys, tempfile
sys.path.insert(0, ".")
from harness import dense_headroom_data as dhd
dhd.block_gpu_only_kernels()
from scripts import run_dense_headroom_precheck_v2_doctor as d
r = d.case_timing_profile(pathlib.Path(tempfile.mkdtemp()) / "timing")
pathlib.Path("/out/timing-profile-case.json").write_text(json.dumps(r, indent=1, default=str))
print(json.dumps({k: r[k] for k in ("status", "failures", "signal_sent", "exit", "units")}))
print(json.dumps(r.get("attention_backend_check"))[:800])
'
echo "exit=$?"
echo "end=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} > "$out/precheck.log" 2>&1
tail -6 "$out/precheck.log"
