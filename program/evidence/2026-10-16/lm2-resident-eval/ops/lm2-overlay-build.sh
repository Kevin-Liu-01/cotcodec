#!/usr/bin/env bash
# LM2 (D129): the retained discovery source capsule of the checkout's HEAD (commit $1), then the
# llama.cpp lane overlay build from it (scripts/build_llamacpp_overlay_on_h100.sh; CPU only, no
# GRES, 10-minute limit). Usage: lm2-overlay-build.sh <commit short id>
set -Eeuo pipefail
source "$(dirname "$0")/lm2-env.sh"
S="${1:?commit short id}"
C="$R/checkout"
A="$R/capsule/source-$S.tar.gz"
REC="$R/capsule/source-receipt-$S.json"
ROOT="$R/builds/llamacpp-overlay-$S"
mkdir -p "$R/capsule" "$R/builds"
cd "$C"
[[ -z "$(git status --porcelain)" ]] || { echo dirty; exit 2; }
[[ "$(git rev-parse --short=8 HEAD)" == "$S" ]] || { echo "checkout is not $S"; exit 2; }
[[ ! -e "$ROOT" ]] || { echo "$ROOT exists"; exit 2; }
if [[ ! -f "$A" ]]; then
  uv run --locked python scripts/create_source_archive.py --discovery --output "$A" --receipt "$REC" \
    > "$R/capsule/create-stdout-$S.json" 2> "$R/capsule/create-stderr-$S.txt"
fi
log_job "capsule $(sha256sum "$A" | cut -d' ' -f1) (git $S)"
EX="$C/scripts/extract_discovery_source_archive.py"
BU="$C/scripts/build_llamacpp_overlay_on_h100.sh"
common="COTCODEC_SOURCE_ARCHIVE=$A,COTCODEC_SOURCE_RECEIPT=$REC,COTCODEC_SOURCE_EXTRACTOR=$EX,COTCODEC_SOURCE_EXTRACTOR_SHA256=$(sha256sum "$EX" | cut -d" " -f1),COTCODEC_SOURCE_SHA256=$(sha256sum "$A" | cut -d" " -f1),COTCODEC_GIT_SHA=$(git rev-parse HEAD),COTCODEC_GIT_TREE=$(git rev-parse "HEAD^{tree}")"
j=$(sbatch --parsable --job-name=lm2-llamacpp-overlay --partition=research --nodes=1 --ntasks=1 \
  --cpus-per-task=8 --mem=32G --time=00:10:00 --no-requeue \
  --output="$R/ops/slurm-llamacpp-overlay-%j.out" \
  --export=ALL,$common,COTCODEC_SOURCE_BUILDER_SHA256=$(sha256sum "$BU" | cut -d" " -f1),COTCODEC_BUILD_ROOT=$ROOT "$BU")
[[ "$j" =~ ^[0-9]+$ ]] || { echo "sbatch printed no job id: '$j'"; exit 2; }
log_job "llama.cpp overlay build job $j submitted (git $S, archive $(sha256sum "$A" | cut -c1-8), CPU only, no GRES, limit 10 min)"
echo "$j"
