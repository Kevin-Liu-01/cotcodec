#!/usr/bin/env bash
# AM5: host CPU extract of the GPU job, from the clean checkout at commit $1: joins every reply to
# the judge's label, flags abstentions and writes text-free features to the host-only $R/private.
# Usage: am5-extract.sh <commit short id> <job id>
set -Eeuo pipefail
source "$(dirname "$0")/am5-env.sh"
SHORT="${1:?commit short id}"; JOB="${2:?job id}"
check_checkout "$SHORT"
RUN="$R/runs/dev-ablated/${JOB}/am5"
{
  echo "start $(date -u +%FT%TZ) commit $(git rev-parse HEAD) job ${JOB}"
  uv run --locked --offline python scripts/memcredit_am5.py extract --run-dir "$RUN" \
    --evidence "$ABL_ART" --summary "$ABL_SUM" --private-dir "$R/private" \
    > "$R/extract-${SHORT}.json" 2> "$R/extract-${SHORT}.stderr"
  echo "extract exit $?"
  sha256sum "$R/private/features-dev-ablated.json.gz" | sed "s#$HOME#~#"
  echo "end $(date -u +%FT%TZ)"
} > "$R/extract-${SHORT}.log" 2>&1 || true
cat "$R/extract-${SHORT}.log"
log_job "extract job ${JOB} at ${SHORT}: $(grep -m1 '^extract exit' "$R/extract-${SHORT}.log")"
