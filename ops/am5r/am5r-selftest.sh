#!/usr/bin/env bash
# am5-ablated-cost-v2: submit the post-build CPU selftest (no GRES) of one population on the image
# built from commit $2: tokenizers only, no model output (registration section 8), so the held-out
# population's selftest may run before the freeze. Its result lands in
# $R/selftest-<population>-<short>/exits.txt, which am5r-submit.sh requires.
# Usage: am5r-selftest.sh dev|reg <commit short id> <image id> <population>
set -Eeuo pipefail
source "$(dirname "$0")/am5r-env.sh" "${1:?mode}"
SHORT="${2:?commit short id}"; IMAGE="${3:?image id}"; POP="${4:?population}"
check_image "$IMAGE"
check_checkout "$SHORT"
ART=$(artifact_for "$POP")
OUT="$R/selftest-${POP}-${SHORT}"
j=$(sbatch --parsable --output="$R/ops/slurm-selftest-%j.out" \
  --export=ALL,AM5R_OUT="$OUT",AM5R_IMAGE="$IMAGE",AM5R_POP="$POP",AM5R_ARTIFACT="$ART",AM5R_ARTIFACT_SHA256="$(sha256sum "$ART" | cut -d" " -f1)" \
  "$C/ops/am5r/am5r-selftest-cpu.sbatch")
[[ "$j" =~ ^[0-9]+$ ]] || { echo "sbatch printed no job id: '$j'" >&2; exit 2; }
log_job "post-build CPU selftest $j submitted (population ${POP}, image ${IMAGE:7:8}, git ${SHORT}, no GRES)"
echo "$j"
