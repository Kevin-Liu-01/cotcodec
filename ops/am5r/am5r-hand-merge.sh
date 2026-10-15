#!/usr/bin/env bash
# am5-ablated-cost-v1: merge one labelling stage of the blind hand check, whatever its
# chunks hold (scripts/memcredit_am5r.py hand-merge; registration section 8), after auditing each
# chunk's transcript (a chunk without one, or with any call other than the Reads of its two inputs
# and the Write of its output, has its rows dropped). first: if items lack a valid label, it
# writes the one repair stage's sample and chunks; otherwise the final labels.
# repair: the final labels ($R/hand/hand-labels.jsonl), complete or not; there is no third
# stage. Then receipt the stage with am5r-hand-receipt.sh before anything else.
# Usage: am5r-hand-merge.sh dev|reg <commit short id> first|repair
set -Eeuo pipefail
source "$(dirname "$0")/am5r-env.sh" "${1:?mode}"
SHORT="${2:?commit short id}"; STAGE="${3:?first or repair}"
check_checkout "$SHORT"
OUT="$R/hand-merge-${STAGE}-${SHORT}.json"
[[ ! -e "$OUT" ]] || { echo "stage $STAGE was merged already ($OUT)" >&2; exit 2; }
chmod u+w "$R/hand/hand-manifest.json"
rm -f "$OUT.tmp"
uv run --locked --offline python scripts/memcredit_am5r.py hand-merge --hand-dir "$R/hand" \
  --stage "$STAGE" > "$OUT.tmp"
mv "$OUT.tmp" "$OUT"
chmod a-w "$R"/hand/*.jsonl "$R"/hand/*.json "$R"/hand/*.txt "$R"/hand/*.sha256 \
  "$R"/hand/transcripts/* 2>/dev/null || true
cat "$OUT"
log_job "hand labels merged, stage ${STAGE}: $(python3 -c "import json,sys;d=json.load(open(sys.argv[1]));print({k:d[k] for k in ('launch','labelling_attempts','valid_rows','malformed_rows','repeated_items') if k in d}, 'chunks failing the transcript audit', len(d['chunks_failing_the_transcript_audit']), d.get('items_lacking_a_valid_row', d.get('final_rows')), d.get('void', ''))" "$OUT")"
