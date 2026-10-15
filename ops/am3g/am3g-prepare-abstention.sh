#!/usr/bin/env bash
# am3-nonabstain-generality-v1: build the abstention population's study artifact (host CPU, no
# model) from the pinned LongMemEval-S file, once, before the freeze, so its digest can be pinned
# in the config and the registration. The artifact (pool texts) stays on the host under
# $REG_ROOT/inputs/; the text-free summary is copied into the evidence. Also checks that the
# retrieved-arm builder reproduces the development artifact's retrieved pools.
# Usage: am3g-prepare-abstention.sh dev <commit short id>
set -Eeuo pipefail
source "$(dirname "$0")/am3g-env.sh" "${1:?mode}"
SHORT="${2:?commit short id}"
check_checkout "$SHORT"
mkdir -p "$REG_ROOT/inputs" "$R/prepare"
[[ ! -e "$ABS_ART" ]] || { echo "the abstention artifact exists; it is built once" >&2; exit 2; }
uv run --locked --offline python scripts/memcredit_am3g.py prepare-abstention \
  --source "$DATASET" --split-file experiments/am1/memcredit-split-v1.json \
  --artifact "$ABS_ART" --summary "$R/prepare/abstention-summary-${SHORT}.json" \
  --dev-artifact "$DEV_ART" > "$R/prepare/prepare-${SHORT}.json" 2> "$R/prepare/prepare-${SHORT}.stderr"
chmod a-w "$ABS_ART"
cat "$R/prepare/prepare-${SHORT}.json"
log_job "abstention artifact $(sha256sum "$ABS_ART" | cut -c1-16) built at ${SHORT} (CPU)"
