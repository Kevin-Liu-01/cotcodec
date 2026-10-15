#!/usr/bin/env bash
# am3-nonabstain-generality-v1: host CPU analysis from the clean checkout at commit $2. analyze
# runs twice and the outputs must be byte-identical; then the tests of this registration and
# AM3's. dev mode: the development dry run's analysis, its comparison with AM3's committed
# outputs, and the operating characteristics (power.json). reg mode: the registered analysis of
# both populations; with ABSTENTION_VOID set (the failing error line, registration section 8) the
# H2 void path replaces the abstention features.
# Usage: am3g-analyze.sh dev|reg <commit short id>
set -Eeuo pipefail
source "$(dirname "$0")/am3g-env.sh" "${1:?mode}"
SHORT="${2:?commit short id}"
check_checkout "$SHORT"
P="$R/private"
if [[ "$AM3G_MODE" == dev ]]; then
  IN=(--development-features "$P/features-development.json.gz")
elif [[ -n "${ABSTENTION_VOID:-}" ]]; then
  IN=(--heldout-features "$P/features-heldout.json.gz" --abstention-void "$ABSTENTION_VOID")
else
  IN=(--heldout-features "$P/features-heldout.json.gz" --abstention-features "$P/features-abstention.json.gz")
fi
{
  echo "start $(date -u +%FT%TZ) commit $(git rev-parse HEAD) mode ${AM3G_MODE}"
  for x in a b; do
    uv run --locked --offline python scripts/memcredit_am3g.py analyze "${IN[@]}" \
      --output-dir "$R/out-${SHORT}-$x" > "$R/analyze-${SHORT}-$x.json" 2> "$R/analyze-${SHORT}-$x.stderr"
    echo "analyze $x exit $?"
  done
  cmp "$R/out-${SHORT}-a/results.json" "$R/out-${SHORT}-b/results.json" && \
    cmp "$R/out-${SHORT}-a/per-table.json.gz" "$R/out-${SHORT}-b/per-table.json.gz" && \
    cmp "$R/out-${SHORT}-a/tables.md" "$R/out-${SHORT}-b/tables.md" && echo "analyze outputs byte-identical"
  (cd "$R/out-${SHORT}-a" && sha256sum results.json per-table.json.gz tables.md)
  sha256sum "$P"/features-*.json.gz | sed "s#$HOME#~#"
  if [[ "$AM3G_MODE" == dev ]]; then
    uv run --locked --offline python scripts/memcredit_am3g.py dryrun-compare \
      --development-features "$P/features-development.json.gz" --output-dir "$R/out-${SHORT}-a" \
      > "$R/dryrun-compare-${SHORT}.json" 2> "$R/dryrun-compare-${SHORT}.stderr"
    echo "dryrun-compare exit $? ($(tr -d '\n ' < "$R/dryrun-compare-${SHORT}.json"))"
    uv run --locked --offline python scripts/memcredit_am3g.py power --am3-features "$AM3_FEATURES" \
      --am3-features-sha256 "$(sha256sum "$AM3_FEATURES" | cut -d" " -f1)" \
      --output "$R/out-${SHORT}-a/power.json" > "$R/power-${SHORT}.json" 2> "$R/power-${SHORT}.stderr"
    echo "power exit $?"
  fi
  uv run --locked --offline --extra dev pytest -q -p no:cacheprovider tests/test_memcredit_am3g.py \
    tests/test_memcredit_am3.py > "$R/pytest-${SHORT}.log" 2>&1
  echo "pytest exit $? ($(tail -1 "$R/pytest-${SHORT}.log"))"
  echo "end $(date -u +%FT%TZ)"
} > "$R/analyze-${SHORT}.log" 2>&1 || true
cat "$R/analyze-${SHORT}.log"
