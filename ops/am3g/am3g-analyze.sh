#!/usr/bin/env bash
# am3-nonabstain-generality-v1: host CPU analysis from the clean checkout at commit $2. analyze
# runs twice and the outputs must be byte-identical; then the tests of this registration and
# AM3's. dev mode: the development dry run's analysis, its comparison with AM3's committed
# outputs, and the operating characteristics (power.json). reg mode: the registered analysis of
# both populations. With ABSTENTION_VOID set (the failing error line, registration section 8)
# the H2 void path replaces the abstention features and writes to out-<short>-void-{a,b} and
# analyze-<short>-void.log, so the failing attempt's outputs and logs are kept: analyze runs once
# per input set, and an output directory that exists is never overwritten. The blind hand
# check's labels ($R/private/hand-labels.jsonl) are joined with the digest receipted by
# am3g-hand-receipt.sh ($R/hand-check/hand-labels.sha256.txt), which is committed to the
# repository before this runs; reg mode refuses to run without them, dev mode joins them if
# present.
# Usage: am3g-analyze.sh dev|reg <commit short id>
set -Eeuo pipefail
source "$(dirname "$0")/am3g-env.sh" "${1:?mode}"
SHORT="${2:?commit short id}"
check_checkout "$SHORT"
P="$R/private"
TAG="$SHORT"
if [[ "$AM3G_MODE" == dev ]]; then
  IN=(--development-features "$P/features-development.json.gz")
elif [[ -n "${ABSTENTION_VOID:-}" ]]; then
  IN=(--heldout-features "$P/features-heldout.json.gz" --abstention-void "$ABSTENTION_VOID")
  TAG="${SHORT}-void"
else
  IN=(--heldout-features "$P/features-heldout.json.gz" --abstention-features "$P/features-abstention.json.gz")
fi
HL="$P/hand-labels.jsonl"; HS="$R/hand-check/hand-labels.sha256.txt"
if [[ -f "$HL" && -f "$HS" ]]; then
  IN+=(--hand-labels "$HL" --hand-labels-sha256 "$(cut -d" " -f1 "$HS")")
elif [[ "$AM3G_MODE" == reg ]]; then
  echo "no receipted hand labels ($HL, $HS): run am3g-hand-receipt.sh and commit its receipt first" >&2
  exit 2
fi
for x in a b; do
  [[ ! -e "$R/out-${TAG}-$x" ]] || { echo "out-${TAG}-$x exists: analyze runs once per input set" >&2; exit 2; }
done
{
  echo "start $(date -u +%FT%TZ) commit $(git rev-parse HEAD) mode ${AM3G_MODE} tag ${TAG}"
  for x in a b; do
    uv run --locked --offline python scripts/memcredit_am3g.py analyze "${IN[@]}" \
      --output-dir "$R/out-${TAG}-$x" > "$R/analyze-${TAG}-$x.json" 2> "$R/analyze-${TAG}-$x.stderr"
    echo "analyze $x exit $?"
  done
  cmp "$R/out-${TAG}-a/results.json" "$R/out-${TAG}-b/results.json" && \
    cmp "$R/out-${TAG}-a/per-table.json.gz" "$R/out-${TAG}-b/per-table.json.gz" && \
    cmp "$R/out-${TAG}-a/tables.md" "$R/out-${TAG}-b/tables.md" && echo "analyze outputs byte-identical"
  (cd "$R/out-${TAG}-a" && sha256sum results.json per-table.json.gz tables.md)
  sha256sum "$P"/features-*.json.gz | sed "s#$HOME#~#"
  if [[ "$AM3G_MODE" == dev ]]; then
    uv run --locked --offline python scripts/memcredit_am3g.py dryrun-compare \
      --development-features "$P/features-development.json.gz" --output-dir "$R/out-${TAG}-a" \
      > "$R/dryrun-compare-${TAG}.json" 2> "$R/dryrun-compare-${TAG}.stderr"
    echo "dryrun-compare exit $? ($(tr -d '\n ' < "$R/dryrun-compare-${TAG}.json"))"
    uv run --locked --offline python scripts/memcredit_am3g.py power --am3-features "$AM3_FEATURES" \
      --am3-features-sha256 "$(sha256sum "$AM3_FEATURES" | cut -d" " -f1)" \
      --output "$R/out-${TAG}-a/power.json" > "$R/power-${TAG}.json" 2> "$R/power-${TAG}.stderr"
    echo "power exit $?"
  fi
  uv run --locked --offline --extra dev pytest -q -p no:cacheprovider tests/test_memcredit_am3g.py \
    tests/test_memcredit_am3.py > "$R/pytest-${TAG}.log" 2>&1
  echo "pytest exit $? ($(tail -1 "$R/pytest-${TAG}.log"))"
  echo "end $(date -u +%FT%TZ)"
} > "$R/analyze-${TAG}.log" 2>&1 || true
cat "$R/analyze-${TAG}.log"
log_job "analyze ${AM3G_MODE} at ${TAG}: $(grep -c ' exit 0' "$R/analyze-${TAG}.log") commands exited 0; $(grep -m1 'byte-identical' "$R/analyze-${TAG}.log" || echo 'outputs differ or missing')"
