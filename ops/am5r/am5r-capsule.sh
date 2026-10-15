#!/usr/bin/env bash
# am5-ablated-cost-v2: the retained discovery source capsule (a git archive) of the
# checkout's HEAD, from which the image is built.
# Usage: am5r-capsule.sh dev|reg <commit short id>
set -Eeuo pipefail
source "$(dirname "$0")/am5r-env.sh" "${1:?mode}"
SHORT="${2:?commit short id}"
check_checkout "$SHORT"
mkdir -p "$R/capsule"
uv run --locked --offline python scripts/create_source_archive.py --discovery \
  --output "$R/capsule/source-${SHORT}.tar.gz" --receipt "$R/capsule/source-receipt-${SHORT}.json" \
  > "$R/capsule/create-stdout-${SHORT}.json" 2> "$R/capsule/create-stderr-${SHORT}.txt"
log_job "capsule $(sha256sum "$R/capsule/source-${SHORT}.tar.gz" | cut -d" " -f1) (git ${SHORT})"
