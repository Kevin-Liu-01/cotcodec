#!/usr/bin/env bash
# Full host suite at the branch head in a fresh scratch clone (uv sync --locked --extra dev),
# inside a Slurm CPU step. Usage: host-suite.sh SHA
set -uo pipefail
sha=$1
dir=$HOME/cotcodec-scratch/q3v2-suite-$sha
out=$HOME/cotcodec-runs/stage0/q3-dense-v2/ops/timing-2/tests/host-suite-$sha
mkdir -p "$out"
cd "$dir"
{
echo "start=$(date -u +%Y-%m-%dT%H:%M:%SZ) head=$(git rev-parse HEAD) dirty=$(git status --porcelain | wc -l)"
uv sync --locked --extra dev --quiet 2>&1 | tail -3
timeout 1800 srun --partition=research --nodes=1 --ntasks=1 --cpus-per-task=16 --mem=64G --time=00:30:00 \
  --job-name=q3v2-host-suite uv run --locked --extra dev pytest -q -p no:cacheprovider tests
echo "exit=$?"
echo "end=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} > "$out/pytest-full-$sha.log" 2>&1
tail -4 "$out/pytest-full-$sha.log"
