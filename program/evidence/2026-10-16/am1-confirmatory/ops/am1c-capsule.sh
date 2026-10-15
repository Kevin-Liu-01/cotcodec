#!/usr/bin/env bash
# am1-memory-credit-v1 (CONFIRMATORY): the retained discovery source capsule (a git archive) of
# the freeze commit 9ad36b10, from the clean clone on the host. Carries the ledger row the
# driver checks.
set -Eeuo pipefail
FREEZE=9ad36b10dcbd324647e4a98c3a150f954f7123f6
SHORT=${FREEZE:0:8}
R=/home/kevin/cotcodec-runs/stage0/am1-memory-credit-v1
cd "$R/checkout"
[[ -z "$(git status --porcelain)" ]] || { echo dirty; exit 2; }
[[ "$(git rev-parse HEAD)" == "${FREEZE}" ]] || { echo "checkout is not at the freeze commit"; exit 2; }
uv run --locked --offline python scripts/create_source_archive.py --discovery \
  --output "$R/capsule/source-${SHORT}.tar.gz" --receipt "$R/capsule/source-receipt-${SHORT}.json" \
  > "$R/capsule/create-stdout-${SHORT}.json" 2> "$R/capsule/create-stderr-${SHORT}.txt"
sha256sum "$R/capsule/source-${SHORT}.tar.gz" | tee -a "$R/ops/jobs.log"
