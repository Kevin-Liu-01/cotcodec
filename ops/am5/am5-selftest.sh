#!/usr/bin/env bash
# AM5: submit the post-build CPU selftest (no GRES) on the image built from commit $1. Its result
# lands in $R/selftest-<short>/exits.txt, which am5-submit.sh requires.
# Usage: am5-selftest.sh <commit short id> <image id>
set -Eeuo pipefail
source "$(dirname "$0")/am5-env.sh"
SHORT="${1:?commit short id}"; IMAGE="${2:?image id}"
check_image "$IMAGE"
check_checkout "$SHORT"
OUT="$R/selftest-${SHORT}"
j=$(sbatch --parsable --output="$R/ops/slurm-selftest-%j.out" \
  --export=ALL,AM5_OUT="$OUT",AM5_IMAGE="$IMAGE",AM5_ARTIFACT="$ABL_ART",AM5_ARTIFACT_SHA256="$(sha256sum "$ABL_ART" | cut -d" " -f1)" \
  "$C/ops/am5/am5-selftest-cpu.sbatch")
log_job "post-build CPU selftest $j submitted (image ${IMAGE:7:8}, git ${SHORT}, no GRES)"
echo "$j"
