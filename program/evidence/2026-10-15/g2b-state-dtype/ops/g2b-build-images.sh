#!/usr/bin/env bash
# Build the two g2b-state-dtype-v1 images from one commit (program route: retained source
# capsule, offline overlay builds, one Slurm-owned H100 each for a few minutes), as the G2 pilot
# did (program/evidence/2026-10-14/g2-pilot/ops/g2-build-images-307fa7ed.sh).
# Usage: g2b-build-images.sh <short-sha>
set -Eeuo pipefail
S="${1:?short sha}"
R=/home/kevin/cotcodec-runs/stage0/g2b-state-dtype
C="$R/checkout-$S"
A="$R/capsule/source-$S.tar.gz"
REC="$R/capsule/source-receipt-$S.json"
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
j1=$(sbatch --parsable --job-name=g2b-vllm-overlay --partition=research --nodes=1 --ntasks=1 \
  --gres=gpu:h100:1 --cpus-per-task=8 --mem=32G --time=00:05:00 --no-requeue \
  --output="$R/ops/slurm-vllm-overlay-%j.out" \
  --export=ALL,$common,COTCODEC_SOURCE_BUILDER_SHA256=$(sha256sum "$BU" | cut -d" " -f1),COTCODEC_BUILD_ROOT=$R/overlay-build-vllm-$S,COTCODEC_VLLM_VARIANT=cu129 "$BU")
echo "$(date -u +%FT%TZ) vLLM overlay build job $j1 submitted (git $S, archive $(sha256sum "$A" | cut -c1-8), 1 H100, limit 5 min)" | tee -a "$R/ops/jobs.log"
BS="$C/scripts/build_source_overlay_on_h100.sh"
BASE_TAG="127.0.0.1:5000/cotcodec-research@sha256:13a9de831cff50461d8ecee3c2794f0c6d6bcffe9d602968fe2ee06e5a1096e9"
BASE_ID="sha256:500f3b027173a2d772b7d6ea00ea667dbe1bc956df51e3c2c4455d9c08a2714b"
j2=$(sbatch --parsable --job-name=g2b-research-overlay --partition=research --nodes=1 --ntasks=1 \
  --gres=gpu:h100:1 --cpus-per-task=8 --mem=32G --time=00:05:00 --no-requeue \
  --output="$R/ops/slurm-research-overlay-%j.out" \
  --export=ALL,$common,COTCODEC_SOURCE_BUILDER_SHA256=$(sha256sum "$BS" | cut -d" " -f1),COTCODEC_BASE_IMAGE_TAG=$BASE_TAG,COTCODEC_BASE_IMAGE_ID=$BASE_ID,COTCODEC_BUILD_ROOT=$R/overlay-build-research-$S "$BS")
echo "$(date -u +%FT%TZ) research source-overlay build job $j2 submitted (base cotcodec-research ed5d5a93 500f3b02, 1 H100, limit 5 min)" | tee -a "$R/ops/jobs.log"
