#!/usr/bin/env bash
# am3-nonabstain-generality-v1: submit the post-build CPU selftest (no GRES) of one population on
# the image built from commit $2. Its result lands in $R/selftest-<population>-<short>/exits.txt,
# which am3g-submit.sh requires. The held-out population's selftest refuses before the freeze.
# Usage: am3g-selftest.sh dev|reg <commit short id> <image id> <population>
set -Eeuo pipefail
source "$(dirname "$0")/am3g-env.sh" "${1:?mode}"
SHORT="${2:?commit short id}"; IMAGE="${3:?image id}"; POP="${4:?population}"
check_checkout "$SHORT"
ART=$(artifact_for "$POP")
OUT="$R/selftest-${POP}-${SHORT}"
j=$(sbatch --parsable --output="$R/ops/slurm-selftest-%j.out" \
  --export=ALL,AM3G_OUT="$OUT",AM3G_IMAGE="$IMAGE",AM3G_POP="$POP",AM3G_ARTIFACT="$ART",AM3G_ARTIFACT_SHA256="$(sha256sum "$ART" | cut -d" " -f1)" \
  "$C/ops/am3g/am3g-selftest-cpu.sbatch")
log_job "post-build CPU selftest $j submitted (population ${POP}, image ${IMAGE:7:8}, git ${SHORT}, no GRES)"
