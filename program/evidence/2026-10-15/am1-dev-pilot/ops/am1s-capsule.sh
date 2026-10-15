#!/usr/bin/env bash
# AM1 development pilot: the retained discovery source capsule of the checkout's HEAD.
# Usage: am1s-capsule.sh <commit short id>
set -Eeuo pipefail
SHORT="${1:?commit short id}"
R=/home/kevin/cotcodec-runs/stage0/am1-study
cd "$R/checkout"
[[ -z "$(git status --porcelain)" ]] || { echo dirty; exit 2; }
[[ "$(git rev-parse --short=8 HEAD)" == "${SHORT}" ]] || { echo "checkout is not at ${SHORT}"; exit 2; }
uv run --locked --offline python scripts/create_source_archive.py --discovery \
  --output "$R/capsule/source-${SHORT}.tar.gz" --receipt "$R/capsule/source-receipt-${SHORT}.json" \
  > "$R/capsule/create-stdout-${SHORT}.json" 2> "$R/capsule/create-stderr-${SHORT}.txt"
sha256sum "$R/capsule/source-${SHORT}.tar.gz"
