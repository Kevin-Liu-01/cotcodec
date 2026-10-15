#!/usr/bin/env bash
# AM5: build the ablated development artifact once on the host CPU (pool texts; host only, made
# read-only) and its text-free summary, from the clean checkout at commit $1. Refuses to overwrite.
# Usage: am5-prepare.sh <commit short id>
set -Eeuo pipefail
source "$(dirname "$0")/am5-env.sh"
SHORT="${1:?commit short id}"
check_checkout "$SHORT"
mkdir -p "$R/inputs" "$R/prepare"
uv run --locked --offline python scripts/memcredit_am5.py prepare --source "$DATASET" \
  --split-file experiments/am1/memcredit-split-v1.json --dev-artifact "$DEV_ART" \
  --artifact "$ABL_ART" --summary "$ABL_SUM" > "$R/prepare/prepare-${SHORT}.json"
chmod a-w "$ABL_ART" "$R/inputs"
sed -i "s#$HOME#~#g" "$R/prepare/prepare-${SHORT}.json"
cat "$R/prepare/prepare-${SHORT}.json"
log_job "prepare at ${SHORT}: artifact $(sha256sum "$ABL_ART" | cut -c1-16), summary $(sha256sum "$ABL_SUM" | cut -c1-16)"
