#!/usr/bin/env bash
# am3-nonabstain-generality-v1: host CPU extract of one population's GPU job, from the clean
# checkout at commit $2 in the host's uv environment. It joins every reply to both judges' labels,
# flags abstentions and runs the anchor checks (held-out: job 1458 and AM1's committed tables;
# development: AM3's job 1466), and writes text-free features to the host-only private directory
# $R/private. Reply texts never leave the host. The held-out and abstention populations refuse
# before the freeze.
# Usage: am3g-extract.sh dev|reg <commit short id> <population> <job id>
set -Eeuo pipefail
source "$(dirname "$0")/am3g-env.sh" "${1:?mode}"
SHORT="${2:?commit short id}"; POP="${3:?population}"; JOB="${4:?job id}"
allowed_population "$POP"
check_checkout "$SHORT"
RUN="$R/runs/${POP}/${JOB}/am3g"
case "$POP" in
  heldout) REF=(--reference-run-dir "$REF_1458") ;;
  development) REF=(--reference-run-dir "$REF_1466") ;;
  *) REF=() ;;
esac
{
  echo "start $(date -u +%FT%TZ) commit $(git rev-parse HEAD) population ${POP} job ${JOB}"
  uv run --locked --offline python scripts/memcredit_am3g.py extract --population "$POP" \
    --run-dir "$RUN" --evidence "$(artifact_for "$POP")" --private-dir "$R/private" "${REF[@]}" \
    > "$R/extract-${POP}-${SHORT}.json" 2> "$R/extract-${POP}-${SHORT}.stderr"
  echo "extract exit $?"
  sha256sum "$R/private/features-${POP}.json.gz" | sed "s#$HOME#~#"
  echo "end $(date -u +%FT%TZ)"
} > "$R/extract-${POP}-${SHORT}.log" 2>&1 || true
cat "$R/extract-${POP}-${SHORT}.log"
