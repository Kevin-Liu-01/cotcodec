#!/usr/bin/env bash
# AM3 (EXPLORATORY): host CPU steps after the GPU job, from the clean checkout at commit $1 in the
# host's uv environment: extract (joins replies to both judges' labels, flags abstentions,
# compares the anchor with the pilot's committed tables and its raw passes 1411 and 1441; writes
# text-free features to a host-only private directory), analyze twice (the outputs must be
# byte-identical), and the AM3 tests. Reply texts never leave the host.
# Usage: am3-analyze.sh <commit short id> <job id>
set -Eeuo pipefail
SHORT="${1:?commit short id}"; JOB="${2:?job id}"
R=/home/kevin/cotcodec-runs/stage0/am3-reader-replication
P=/home/kevin/cotcodec-runs/stage0/am1-study/runs
RUN="$R/runs/main/${JOB}/am3"
PRIV="$R/private-${SHORT}"
cd "$R/checkout"
[[ -z "$(git status --porcelain)" ]] || { echo dirty; exit 2; }
[[ "$(git rev-parse --short=8 HEAD)" == "${SHORT}" ]] || { echo "checkout is not at ${SHORT}"; exit 2; }
{
  echo "start $(date -u +%FT%TZ) commit $(git rev-parse HEAD)"
  uv run --locked --offline python scripts/memcredit_am3.py extract --run-dir "$RUN" \
    --evidence "$P/main/1411/study-artifact.json" --private-dir "$PRIV" \
    --pilot-run-dir "$P/main/1411/am1" --pilot-eager-run-dir "$P/eager/1441/am1" \
    > "$R/extract-${SHORT}.json" 2> "$R/extract-${SHORT}.stderr"
  echo "extract exit $?"
  for x in a b; do
    uv run --locked --offline python scripts/memcredit_am3.py analyze \
      --features "$PRIV/features.json.gz" --output-dir "$R/out-${SHORT}-$x" \
      > "$R/analyze-${SHORT}-$x.json" 2> "$R/analyze-${SHORT}-$x.stderr"
    echo "analyze $x exit $?"
  done
  cmp "$R/out-${SHORT}-a/results.json" "$R/out-${SHORT}-b/results.json" && \
    cmp "$R/out-${SHORT}-a/per-table.json.gz" "$R/out-${SHORT}-b/per-table.json.gz" && \
    cmp "$R/out-${SHORT}-a/tables.md" "$R/out-${SHORT}-b/tables.md" && echo "analyze outputs byte-identical"
  (cd "$R/out-${SHORT}-a" && sha256sum results.json per-table.json.gz tables.md)
  sha256sum "$PRIV/features.json.gz" | sed "s#$HOME#~#"
  uv run --locked --offline --extra dev pytest -q -p no:cacheprovider tests/test_memcredit_am3.py \
    > "$R/pytest-${SHORT}.log" 2>&1
  echo "pytest exit $? ($(tail -1 "$R/pytest-${SHORT}.log"))"
  echo "end $(date -u +%FT%TZ)"
} > "$R/analyze-${SHORT}.log" 2>&1 || true
cat "$R/analyze-${SHORT}.log"
