#!/usr/bin/env bash
# v1 K1 doctor and v2 K1 doctor in the probe image (commit 4b9d6c4), network none, no GPU,
# each inside its own Slurm step (srun), CPU only. Mirrors ops/q3-k1/run-doctor-imageB.sh.
set -uo pipefail
ops=/home/kevin/cotcodec-runs/stage0/k1-v2/probe-ops
img=sha256:e59d9cc18c0db05fa0ae20a0f65492268112d07fef20f00af799323ae02ce6d3
run_one() {
  local tag=$1 script=$2 out=$3
  {
    echo "start=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    srun --partition=research --nodes=1 --ntasks=1 --cpus-per-task=16 --mem=64G --time=00:30:00 \
      --job-name="k1-probe-$tag" \
      docker run --rm --network none --user "$(id -u):$(id -g)" \
        -e USER=cotcodec -e HOME=/tmp -e TORCHINDUCTOR_CACHE_DIR=/tmp/torchinductor -e HF_HUB_OFFLINE=1 \
        -v "$ops/$tag:/out" --entrypoint python "$img" \
        "$script" --output "/out/$out" \
        > "$ops/$tag/doctor.log" 2>&1
    echo "exit=$?"
    echo "end=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  } > "$ops/$tag/run.env" 2>&1
}
run_one doctor-v1 scripts/run_sparse_indexer_k1_doctor.py k1-doctor-probe-image.json
run_one doctor-v2 scripts/run_sparse_indexer_k1_v2_doctor.py k1-v2-doctor-probe-image.json
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) doctors wrapper finished" >> "$ops/operator-log.txt"
