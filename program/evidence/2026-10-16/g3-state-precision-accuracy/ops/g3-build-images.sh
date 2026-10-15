#!/usr/bin/env bash
# Build the g3-state-precision-accuracy-v1 vLLM overlay image from one commit (program route:
# retained source capsule, offline overlay build, one Slurm-owned H100 for about a minute), as
# G2c did (program/evidence/2026-10-15/g2c-precision-vs-layout/ops/g2c-build-images.sh). G3 needs
# only the vLLM overlay (no trainer path).
# Usage: g3-build-images.sh <short-sha>
set -Eeuo pipefail
S="${1:?short sha}"
R=/home/kevin/cotcodec-runs/stage0/g3-state-precision-accuracy
C="$R/checkout-$S"
A="$R/capsule/source-$S.tar.gz"
REC="$R/capsule/source-receipt-$S.json"
mkdir -p "$R/capsule" "$R/ops"
cd "$C"
[[ -z "$(git status --porcelain)" ]] || { echo dirty; exit 2; }
[[ "$(git rev-parse --short=8 HEAD)" == "$S" ]] || { echo "checkout is not $S"; exit 2; }
if [[ ! -f "$A" ]]; then
  uv run --locked python scripts/create_source_archive.py --discovery --output "$A" --receipt "$REC" \
    > "$R/capsule/create-stdout-$S.json" 2> "$R/capsule/create-stderr-$S.txt"
fi
EX="$C/scripts/extract_discovery_source_archive.py"
common="COTCODEC_SOURCE_ARCHIVE=$A,COTCODEC_SOURCE_RECEIPT=$REC,COTCODEC_SOURCE_EXTRACTOR=$EX,COTCODEC_SOURCE_EXTRACTOR_SHA256=$(sha256sum "$EX" | cut -d" " -f1),COTCODEC_SOURCE_SHA256=$(sha256sum "$A" | cut -d" " -f1),COTCODEC_GIT_SHA=$(git rev-parse HEAD),COTCODEC_GIT_TREE=$(git rev-parse "HEAD^{tree}")"
BU="$C/scripts/build_vllm_overlay_on_h100.sh"
j1=$(sbatch --parsable --job-name=g3-vllm-overlay --partition=research --nodes=1 --ntasks=1 \
  --gres=gpu:h100:1 --cpus-per-task=8 --mem=32G --time=00:05:00 --no-requeue \
  --output="$R/ops/slurm-vllm-overlay-%j.out" \
  --export=ALL,$common,COTCODEC_SOURCE_BUILDER_SHA256=$(sha256sum "$BU" | cut -d" " -f1),COTCODEC_BUILD_ROOT=$R/overlay-build-vllm-$S,COTCODEC_VLLM_VARIANT=cu129 "$BU")
echo "$(date -u +%FT%TZ) vLLM overlay build job $j1 submitted (git $S, archive $(sha256sum "$A" | cut -c1-8), 1 H100, limit 5 min)" | tee -a "$R/ops/jobs.log"
