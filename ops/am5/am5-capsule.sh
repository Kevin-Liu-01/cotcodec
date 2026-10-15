#!/usr/bin/env bash
# AM5: the retained discovery source capsule (a git archive) of the checkout's HEAD.
# Usage: am5-capsule.sh <commit short id>
set -Eeuo pipefail
source "$(dirname "$0")/am5-env.sh"
SHORT="${1:?commit short id}"
check_checkout "$SHORT"
mkdir -p "$R/capsule"
uv run --locked --offline python scripts/create_source_archive.py --discovery \
  --output "$R/capsule/source-${SHORT}.tar.gz" --receipt "$R/capsule/source-receipt-${SHORT}.json" \
  > "$R/capsule/create-stdout-${SHORT}.json" 2> "$R/capsule/create-stderr-${SHORT}.txt"
log_job "capsule $(sha256sum "$R/capsule/source-${SHORT}.tar.gz" | cut -d" " -f1) (git ${SHORT})"
