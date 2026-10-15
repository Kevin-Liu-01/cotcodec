#!/usr/bin/env bash
# am5-ablated-cost-v1: host CPU analysis from the clean checkout at commit $2. analyze runs twice
# and the outputs must be byte-identical; then the memcredit tests of am3g, AM5 and this
# registration. dev mode: the development dry run's analysis (the registered machinery on AM5's
# pools; it decides nothing), its comparison with AM5's committed outputs (dryrun-compare, with
# AM5's host-only features and receipted hand labels) and the operating characteristics
# (power.json). reg mode: the registered analysis of the held-out job. The blind hand check's
# final labels ($R/hand/hand-labels.jsonl) are joined with the digests receipted by
# am5r-hand-receipt.sh ($R/hand-check/hand-labels.sha256.txt and hand-plan.sha256.txt), which are
# committed to the repository before this runs; reg mode refuses to run without them and without
# RECEIPT_COMMIT (that commit's id, logged so a verifier can check its time precedes this log);
# dev mode joins them if present. analyze runs once per input set and never overwrites an output
# directory.
# Usage: [RECEIPT_COMMIT=<full id>] am5r-analyze.sh dev|reg <commit short id>
set -Eeuo pipefail
source "$(dirname "$0")/am5r-env.sh" "${1:?mode}"
SHORT="${2:?commit short id}"
check_checkout "$SHORT"
P="$R/private"
POP=heldout; [[ "$AM5R_MODE" == dev ]] && POP=development
IN=(--population "$POP" --features "$P/features-${POP}.json.gz")
HL="$R/hand/hand-labels.jsonl"; HS="$R/hand-check/hand-labels.sha256.txt"; HP="$R/hand-check/hand-plan.sha256.txt"
if [[ -f "$HL" && -f "$HS" && -f "$HP" ]]; then
  IN+=(--hand-labels "$HL" --hand-labels-sha256 "$(cut -d" " -f1 "$HS")"
       --hand-plan-sha256 "$(cut -d" " -f1 "$HP")")
elif [[ "$AM5R_MODE" == reg ]]; then
  echo "no receipted hand labels ($HL, $HS, $HP): run am5r-hand-receipt.sh and commit its receipt first" >&2
  exit 2
fi
if [[ "$AM5R_MODE" == reg ]]; then
  [[ "${RECEIPT_COMMIT:-}" =~ ^[0-9a-f]{40}$ ]] \
    || { echo "set RECEIPT_COMMIT to the commit that holds the hand-label receipt" >&2; exit 2; }
fi
for x in a b; do
  [[ ! -e "$R/out-${SHORT}-$x" ]] || { echo "out-${SHORT}-$x exists: analyze runs once per input set" >&2; exit 2; }
done
{
  echo "start $(date -u +%FT%TZ) commit $(git rev-parse HEAD) mode ${AM5R_MODE} population ${POP}"
  echo "hand-label receipt commit ${RECEIPT_COMMIT:-none}; labels $(cut -c1-16 "$HS" 2>/dev/null || echo none); plan $(cut -c1-16 "$HP" 2>/dev/null || echo none)"
  for x in a b; do
    uv run --locked --offline python scripts/memcredit_am5r.py analyze "${IN[@]}" \
      --output-dir "$R/out-${SHORT}-$x" > "$R/analyze-${SHORT}-$x.json" 2> "$R/analyze-${SHORT}-$x.stderr"
    echo "analyze $x exit $?"
  done
  cmp "$R/out-${SHORT}-a/results.json" "$R/out-${SHORT}-b/results.json" && \
    cmp "$R/out-${SHORT}-a/per-table.json.gz" "$R/out-${SHORT}-b/per-table.json.gz" && \
    cmp "$R/out-${SHORT}-a/tables.md" "$R/out-${SHORT}-b/tables.md" && echo "analyze outputs byte-identical"
  (cd "$R/out-${SHORT}-a" && sha256sum results.json per-table.json.gz tables.md)
  sha256sum "$P/features-${POP}.json.gz" | sed "s#$HOME#~#"
  if [[ "$AM5R_MODE" == dev ]]; then
    uv run --locked --offline python scripts/memcredit_am5r.py dryrun-compare \
      --features "$P/features-development.json.gz" --am5-features "$AM5_FEATURES" \
      --am5-hand-labels "$AM5_LABELS" --output-dir "$R/out-${SHORT}-a" \
      > "$R/dryrun-compare-${SHORT}.json" 2> "$R/dryrun-compare-${SHORT}.stderr"
    echo "dryrun-compare exit $? ($(tr -d '\n ' < "$R/dryrun-compare-${SHORT}.json"))"
    uv run --locked --offline python scripts/memcredit_am5r.py power \
      --output "$R/out-${SHORT}-a/power.json" > "$R/power-${SHORT}.json" 2> "$R/power-${SHORT}.stderr"
    echo "power exit $?"
  fi
  uv run --locked --offline --extra dev pytest -q -p no:cacheprovider tests/test_memcredit_am5r.py \
    tests/test_memcredit_am5.py tests/test_memcredit_am3g.py tests/test_memcredit_am3.py > "$R/pytest-${SHORT}.log" 2>&1
  echo "pytest exit $? ($(tail -1 "$R/pytest-${SHORT}.log"))"
  echo "end $(date -u +%FT%TZ)"
} > "$R/analyze-${SHORT}.log" 2>&1 || true
cat "$R/analyze-${SHORT}.log"
log_job "analyze ${AM5R_MODE} at ${SHORT}: $(grep -c ' exit 0' "$R/analyze-${SHORT}.log") commands exited 0; $(grep -m1 'byte-identical' "$R/analyze-${SHORT}.log" || echo 'outputs differ or missing')"
