#!/usr/bin/env bash
# AM5: host CPU analysis from the clean checkout at commit $1: analyze twice (the outputs must be
# byte-identical), joining the receipted hand labels; then the memcredit tests of AM3-AM5.
# RECEIPT_COMMIT (the commit that holds $R/hand-check) is logged.
# Usage: RECEIPT_COMMIT=<full id> am5-analyze.sh <commit short id>
set -Eeuo pipefail
source "$(dirname "$0")/am5-env.sh"
SHORT="${1:?commit short id}"
check_checkout "$SHORT"
[[ "${RECEIPT_COMMIT:-}" =~ ^[0-9a-f]{40}$ ]] || { echo "set RECEIPT_COMMIT" >&2; exit 2; }
HS="$R/hand-check/hand-labels.sha256.txt"; HP="$R/hand-check/hand-plan.sha256.txt"
for x in a b; do [[ ! -e "$R/out-${SHORT}-$x" ]] || { echo "out-${SHORT}-$x exists" >&2; exit 2; }; done
{
  echo "start $(date -u +%FT%TZ) commit $(git rev-parse HEAD); hand-label receipt commit ${RECEIPT_COMMIT}"
  for x in a b; do
    uv run --locked --offline python scripts/memcredit_am5.py analyze \
      --features "$R/private/features-dev-ablated.json.gz" --hand-labels "$R/hand/hand-labels.jsonl" \
      --hand-labels-sha256 "$(cat "$HS")" --hand-plan-sha256 "$(cat "$HP")" \
      --output-dir "$R/out-${SHORT}-$x" > "$R/analyze-${SHORT}-$x.json" 2> "$R/analyze-${SHORT}-$x.stderr"
    echo "analyze $x exit $?"
  done
  cmp "$R/out-${SHORT}-a/results.json" "$R/out-${SHORT}-b/results.json" && \
    cmp "$R/out-${SHORT}-a/per-table.json.gz" "$R/out-${SHORT}-b/per-table.json.gz" && \
    cmp "$R/out-${SHORT}-a/tables.md" "$R/out-${SHORT}-b/tables.md" && echo "analyze outputs byte-identical"
  (cd "$R/out-${SHORT}-a" && sha256sum results.json per-table.json.gz tables.md)
  sha256sum "$R/private/features-dev-ablated.json.gz" | sed "s#$HOME#~#"
  uv run --locked --offline --extra dev pytest -q -p no:cacheprovider tests/test_memcredit_am5.py \
    tests/test_memcredit_am4.py tests/test_memcredit_am3g.py tests/test_memcredit_am3.py > "$R/pytest-${SHORT}.log" 2>&1
  echo "pytest exit $? ($(tail -1 "$R/pytest-${SHORT}.log"))"
  echo "end $(date -u +%FT%TZ)"
} > "$R/analyze-${SHORT}.log" 2>&1 || true
cat "$R/analyze-${SHORT}.log"
log_job "analyze at ${SHORT}: $(grep -c ' exit 0' "$R/analyze-${SHORT}.log") commands exited 0; $(grep -m1 'byte-identical' "$R/analyze-${SHORT}.log" || echo 'outputs differ or missing')"
