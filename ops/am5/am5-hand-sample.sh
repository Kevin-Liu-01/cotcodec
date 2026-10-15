#!/usr/bin/env bash
# AM5: the blind hand-check sample (every switched reply at K = 70 and every non-abstaining BM25
# top-4 reply on the ablated pools), its instructions, chunk and text-free manifest, written once
# to $R/hand (host only; it holds texts). Prints counts and digests only.
# Usage: am5-hand-sample.sh <commit short id> <job id>
set -Eeuo pipefail
source "$(dirname "$0")/am5-env.sh"
SHORT="${1:?commit short id}"; JOB="${2:?job id}"
check_checkout "$SHORT"
[[ ! -e "$R/hand" ]] || { echo "$R/hand exists: the sample is drawn once" >&2; exit 2; }
uv run --locked --offline python scripts/memcredit_am5.py hand-sample \
  --run-dir "$R/runs/dev-ablated/${JOB}/am5" --evidence "$ABL_ART" \
  --features "$R/private/features-dev-ablated.json.gz" --hand-dir "$R/hand" \
  > "$R/hand-sample-${SHORT}.json"
mkdir -p "$R/hand-check"
cp "$R/hand-sample-${SHORT}.json" "$R/hand/hand-manifest.json" "$R/hand/hand-plan.json" "$R/hand-check/"
cat "$R/hand-sample-${SHORT}.json"
log_job "hand-sample at ${SHORT}: $(python3 -c "import json,sys;d=json.load(open(sys.argv[1]));print(d['items'],'items, plan',d['plan_sha256'][:16])" "$R/hand-sample-${SHORT}.json")"
