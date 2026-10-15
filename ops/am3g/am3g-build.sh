#!/usr/bin/env bash
# am3-nonabstain-generality-v1: submit the cotcodec-vllm cu129 overlay build (vLLM 0.31.0) from
# the retained source capsule of commit $2 (the program's offline build, one Slurm-owned H100 for
# a few minutes, 5-minute limit; the pinned scripts/build_vllm_overlay_on_h100.sh, as AM1 and AM3
# built their images). In reg mode the commit is the freeze commit.
# "rebuild" is the one rebuild section 8 allows after a failed build: it writes to
# overlay-build-vllm-<short>-r2 (the builder refuses an existing build root) and refuses a third
# attempt. The attempts are counted from their submitted job ids, recorded in
# $R/ops/build-attempts-<short>.txt as each sbatch succeeds, not from the build roots, which the
# builder creates only once it runs.
# Usage: am3g-build.sh dev|reg <commit short id> [build|rebuild]
set -Eeuo pipefail
source "$(dirname "$0")/am3g-env.sh" "${1:?mode}"
SHORT="${2:?commit short id}"; ACT="${3:-build}"
N=$(build_attempts "$SHORT")
case "$ACT" in
  build) ROOT="$R/overlay-build-vllm-${SHORT}"
         [[ "$N" == 0 ]] || { echo "a build was submitted already; a second attempt is 'rebuild'" >&2; exit 2; } ;;
  rebuild) [[ "$N" == 1 ]] || { echo "rebuild follows exactly one submitted build ($N recorded)" >&2; exit 2; }
           ROOT="$R/overlay-build-vllm-${SHORT}-r2" ;;
  *) echo "action is build or rebuild" >&2; exit 2 ;;
esac
[[ ! -e "$ROOT" ]] || { echo "$ROOT exists" >&2; exit 2; }
A="$R/capsule/source-${SHORT}.tar.gz"
REC="$R/capsule/source-receipt-${SHORT}.json"
EX="$C/scripts/extract_discovery_source_archive.py"
check_checkout "$SHORT"
bash "$(dirname "$0")/am3g-preflight.sh" "$AM3G_MODE" "build ${SHORT}" 1
common="COTCODEC_SOURCE_ARCHIVE=$A,COTCODEC_SOURCE_RECEIPT=$REC,COTCODEC_SOURCE_EXTRACTOR=$EX,COTCODEC_SOURCE_EXTRACTOR_SHA256=$(sha256sum "$EX" | cut -d" " -f1),COTCODEC_SOURCE_SHA256=$(sha256sum "$A" | cut -d" " -f1),COTCODEC_GIT_SHA=$(git rev-parse HEAD),COTCODEC_GIT_TREE=$(git rev-parse "HEAD^{tree}")"
BU="$C/scripts/build_vllm_overlay_on_h100.sh"
j=$(sbatch --parsable --job-name=am3g-vllm-overlay --partition=research --nodes=1 --ntasks=1 \
  --gres=gpu:h100:1 --cpus-per-task=8 --mem=32G --time=00:05:00 --no-requeue \
  --output="$R/ops/slurm-vllm-overlay-%j.out" \
  --export=ALL,$common,COTCODEC_SOURCE_BUILDER_SHA256=$(sha256sum "$BU" | cut -d" " -f1),COTCODEC_BUILD_ROOT=$ROOT,COTCODEC_VLLM_VARIANT=cu129 "$BU")
[[ "$j" =~ ^[0-9]+$ ]] || { echo "sbatch printed no job id: '$j'" >&2; exit 2; }
echo "$j" >> "$R/ops/build-attempts-${SHORT}.txt"
log_job "vLLM overlay ${ACT} job $j submitted (git ${SHORT}, archive $(sha256sum "$A" | cut -c1-8), root $(basename "$ROOT"), 1 H100, limit 5 min)"
echo "$j"
