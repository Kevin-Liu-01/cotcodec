#!/usr/bin/env bash
# AM3 (EXPLORATORY): submit the cotcodec-vllm cu129 overlay build (vLLM 0.31.0) from the retained
# source capsule of commit $1 (program route: offline build, one Slurm-owned H100 for a few
# minutes; the pinned scripts/build_vllm_overlay_on_h100.sh, as AM1 built its images).
# Usage: am3-build-vllm-overlay.sh <commit short id>
set -Eeuo pipefail
SHORT="${1:?commit short id}"
R=/home/kevin/cotcodec-runs/stage0/am3-reader-replication
C="$R/checkout"
A="$R/capsule/source-${SHORT}.tar.gz"
REC="$R/capsule/source-receipt-${SHORT}.json"
EX="$C/scripts/extract_discovery_source_archive.py"
cd "$C"
[[ -z "$(git status --porcelain)" ]] || { echo dirty; exit 2; }
[[ "$(git rev-parse --short=8 HEAD)" == "${SHORT}" ]] || { echo "checkout is not at ${SHORT}"; exit 2; }
bash "$R/ops/am3-preflight.sh" "build ${SHORT}" 1
common="COTCODEC_SOURCE_ARCHIVE=$A,COTCODEC_SOURCE_RECEIPT=$REC,COTCODEC_SOURCE_EXTRACTOR=$EX,COTCODEC_SOURCE_EXTRACTOR_SHA256=$(sha256sum "$EX" | cut -d" " -f1),COTCODEC_SOURCE_SHA256=$(sha256sum "$A" | cut -d" " -f1),COTCODEC_GIT_SHA=$(git rev-parse HEAD),COTCODEC_GIT_TREE=$(git rev-parse "HEAD^{tree}")"
BU="$C/scripts/build_vllm_overlay_on_h100.sh"
j=$(sbatch --parsable --job-name=am3-vllm-overlay --partition=research --nodes=1 --ntasks=1 \
  --gres=gpu:h100:1 --cpus-per-task=8 --mem=32G --time=00:05:00 --no-requeue \
  --output="$R/ops/slurm-vllm-overlay-%j.out" \
  --export=ALL,$common,COTCODEC_SOURCE_BUILDER_SHA256=$(sha256sum "$BU" | cut -d" " -f1),COTCODEC_BUILD_ROOT=$R/overlay-build-vllm-${SHORT},COTCODEC_VLLM_VARIANT=cu129 "$BU")
echo "$(date -u +%FT%TZ) vLLM overlay build job $j submitted (git ${SHORT}, archive $(sha256sum "$A" | cut -c1-8), 1 H100, limit 5 min)" | tee -a "$R/ops/jobs.log"
