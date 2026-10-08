#!/usr/bin/env bash
# Run analyse_timing2.py in image 806 (CPU only, network none) on job 810's files.
set -uo pipefail
job=${1:-810}
base=$HOME/cotcodec-runs/stage0/q3-dense-v2/ops/timing-2
run=$HOME/cotcodec-runs/q3-dense-headroom-precheck-v2/timing-2-qwen3.5-4b-base/$job
img=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["image_id"])' "$base/images/image-build-receipt-806.json")
timeout 900 srun --partition=research --nodes=1 --ntasks=1 --cpus-per-task=4 --mem=16G --time=00:10:00 \
  --job-name="dense-v2-timing2-analysis" \
  docker run --rm --network none --user "$(id -u):$(id -g)" -e HOME=/tmp -e PYTHONDONTWRITEBYTECODE=1 \
    -e ANALYSIS_OUT=/out/analysis.json \
    -v "$base/analyse_timing2.py:/tmp/analyse_timing2.py:ro" -v "$run:/run810:ro" -v "$base/timing-$job:/out" \
    --entrypoint python "$img" /tmp/analyse_timing2.py /run810/dense-precheck/timing-receipt.json \
    /run810/dense-precheck/dev-artifact.json /run810/job.env /run810/termination.env /out/scontrol-$job.txt \
  > "$base/timing-$job/analysis.txt" 2>&1
echo "exit=$?"
