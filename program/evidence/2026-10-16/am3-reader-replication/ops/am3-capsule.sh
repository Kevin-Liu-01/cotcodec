#!/usr/bin/env bash
# AM3 (EXPLORATORY): the retained discovery source capsule (a git archive) of the checkout's HEAD.
# Usage: am3-capsule.sh <commit short id>
set -Eeuo pipefail
SHORT="${1:?commit short id}"
R=/home/kevin/cotcodec-runs/stage0/am3-reader-replication
cd "$R/checkout"
[[ -z "$(git status --porcelain)" ]] || { echo dirty; exit 2; }
[[ "$(git rev-parse --short=8 HEAD)" == "${SHORT}" ]] || { echo "checkout is not at ${SHORT}"; exit 2; }
mkdir -p "$R/capsule"
uv run --locked --offline python scripts/create_source_archive.py --discovery \
  --output "$R/capsule/source-${SHORT}.tar.gz" --receipt "$R/capsule/source-receipt-${SHORT}.json" \
  > "$R/capsule/create-stdout-${SHORT}.json" 2> "$R/capsule/create-stderr-${SHORT}.txt"
echo "$(date -u +%FT%TZ) capsule $(sha256sum "$R/capsule/source-${SHORT}.tar.gz" | cut -d" " -f1) (git ${SHORT})" | tee -a "$R/ops/jobs.log"
