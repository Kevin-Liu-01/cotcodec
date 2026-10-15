#!/usr/bin/env bash
# am5-ablated-cost-v1: host CPU extract of one population's GPU job, from the clean checkout at
# commit $2 in the host's uv environment. It joins every reply to the judge's label, flags
# abstentions, splits the replay control off, replays it against AM5's job 1487 (V3; the
# development dry run replays every request), and writes text-free features to the host-only
# private directory $R/private. Reply texts never leave the host. The held-out population refuses
# before the freeze. JOB is the job the rerun rule kept (am5r-rerun-decision.sh): the rerun's id
# when a rerun ran.
# Usage: am5r-extract.sh dev|reg <commit short id> <population> <job id>
set -Eeuo pipefail
source "$(dirname "$0")/am5r-env.sh" "${1:?mode}"
SHORT="${2:?commit short id}"; POP="${3:?population}"; JOB="${4:?job id}"
allowed_population "$POP"
check_checkout "$SHORT"
RUN="$R/runs/${POP}/${JOB}/am5r"
{
  echo "start $(date -u +%FT%TZ) commit $(git rev-parse HEAD) population ${POP} job ${JOB}"
  uv run --locked --offline python scripts/memcredit_am5r.py extract --population "$POP" \
    --run-dir "$RUN" --evidence "$(artifact_for "$POP")" --summary "$(summary_for "$POP")" \
    --private-dir "$R/private" --reference-run-dir "$REF_1487" \
    > "$R/extract-${POP}-${SHORT}.json" 2> "$R/extract-${POP}-${SHORT}.stderr"
  echo "extract exit $?"
  sha256sum "$R/private/features-${POP}.json.gz" | sed "s#$HOME#~#"
  echo "end $(date -u +%FT%TZ)"
} > "$R/extract-${POP}-${SHORT}.log" 2>&1 || true
sed -i "s#$HOME#~#g" "$R/extract-${POP}-${SHORT}.json" "$R/extract-${POP}-${SHORT}.stderr" 2>/dev/null || true
cat "$R/extract-${POP}-${SHORT}.log"
log_job "extract ${POP} job ${JOB} at ${SHORT}: $(grep -m1 '^extract exit' "$R/extract-${POP}-${SHORT}.log")"
