#!/usr/bin/env bash
# AM5: submit the cotcodec-vllm cu129 overlay build (vLLM 0.31.0) from the retained source capsule
# of commit $1 (one Slurm-owned H100, 5-minute limit; the program's scripts/build_vllm_overlay_on_h100.sh,
# as am3g built its images). Once per commit. Prints only the job id on stdout.
# Usage: am5-build.sh <commit short id>
set -Eeuo pipefail
source "$(dirname "$0")/am5-env.sh"
SHORT="${1:?commit short id}"
ROOT="$R/overlay-build-vllm-${SHORT}"
[[ ! -e "$ROOT" && ! -e "$R/ops/build-${SHORT}.txt" ]] || { echo "a build of ${SHORT} was submitted already" >&2; exit 2; }
A="$R/capsule/source-${SHORT}.tar.gz"
REC="$R/capsule/source-receipt-${SHORT}.json"
EX="$C/scripts/extract_discovery_source_archive.py"
check_checkout "$SHORT"
bash "$(dirname "$0")/am5-preflight.sh" "build ${SHORT}" 1
common="COTCODEC_SOURCE_ARCHIVE=$A,COTCODEC_SOURCE_RECEIPT=$REC,COTCODEC_SOURCE_EXTRACTOR=$EX,COTCODEC_SOURCE_EXTRACTOR_SHA256=$(sha256sum "$EX" | cut -d" " -f1),COTCODEC_SOURCE_SHA256=$(sha256sum "$A" | cut -d" " -f1),COTCODEC_GIT_SHA=$(git rev-parse HEAD),COTCODEC_GIT_TREE=$(git rev-parse "HEAD^{tree}")"
BU="$C/scripts/build_vllm_overlay_on_h100.sh"
j=$(sbatch --parsable --job-name=am5-vllm-overlay --partition=research --nodes=1 --ntasks=1 \
  --gres=gpu:h100:1 --cpus-per-task=8 --mem=32G --time=00:05:00 --no-requeue \
  --output="$R/ops/slurm-vllm-overlay-%j.out" \
  --export=ALL,$common,COTCODEC_SOURCE_BUILDER_SHA256=$(sha256sum "$BU" | cut -d" " -f1),COTCODEC_BUILD_ROOT=$ROOT,COTCODEC_VLLM_VARIANT=cu129 "$BU")
[[ "$j" =~ ^[0-9]+$ ]] || { echo "sbatch printed no job id: '$j'" >&2; exit 2; }
echo "$j" > "$R/ops/build-${SHORT}.txt"
log_job "vLLM overlay build job $j submitted (git ${SHORT}, archive $(sha256sum "$A" | cut -c1-8), 1 H100, limit 5 min)"
echo "$j"
