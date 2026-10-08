#!/usr/bin/env bash
# Run a command in the research image on CPU only (no GPU, no network) inside a Slurm step,
# from the rsynced worktree mounted read-only. Usage: run-in-image.sh TAG python-args...
# With WITH_PYTEST=1 the lock-pinned pytest overlay built for the K1 v2 equivalence run
# (installed offline with hashes from uv.lock) is mounted read-only on PYTHONPATH.
set -uo pipefail
base="$HOME/cotcodec-runs/stage0/q3-dense-precheck"
img=sha256:e59d9cc18c0db05fa0ae20a0f65492268112d07fef20f00af799323ae02ce6d3
overlay="$HOME/cotcodec-runs/stage0/k1-v2/eq-run/pytest-overlay"
tag=$1; shift
mkdir -p "$base/ops/$tag"
extra=()
if [[ "${WITH_PYTEST:-0}" == 1 ]]; then
  extra=(-v "$overlay:/pytest-overlay:ro" -e PYTHONPATH=/pytest-overlay)
fi
{
  echo "start=$(date -u +%Y-%m-%dT%H:%M:%SZ) image=$img"
  timeout 3000 srun --partition=research --nodes=1 --ntasks=1 --cpus-per-task=32 --mem=96G \
    --time=00:50:00 --job-name="dense-cpu-$tag" \
    docker run --rm --network none --user "$(id -u):$(id -g)" -e USER=cotcodec -e HOME=/tmp \
      -e HF_HUB_OFFLINE=1 -e PYTHONDONTWRITEBYTECODE=1 -e OMP_NUM_THREADS=8 "${extra[@]}" \
      -v "$base/wt:/work:ro" -v "$base/ops/$tag:/out" -w /work --entrypoint python "$img" "$@"
  echo "exit=$?"
  echo "end=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} > "$base/ops/$tag/log.txt" 2>&1
tail -5 "$base/ops/$tag/log.txt"
