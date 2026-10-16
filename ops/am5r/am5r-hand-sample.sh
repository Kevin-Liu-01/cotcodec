#!/usr/bin/env bash
# am5-ablated-cost-v2: draw the blind hand-check sample (registration section 8) from the job the
# rerun rule kept: per reader, every switched reply the judge calls correct (K = 70), every
# switched reply at K = 8 the judge calls wrong, a seeded half of those it calls wrong beyond
# K = 8, every BM25 top-4 reply that does not abstain, and as many seeded distractors, in one
# seeded order. The sample, the instructions, the chunks of 60 items and their launch prompts and
# the text-free plan go to $R/hand/, a directory of their own: the labeller never sees
# $R/private/, which holds the features and every judge label. The files are made read-only;
# only counts and digests are printed.
# Usage: am5r-hand-sample.sh dev|reg <commit short id> <job id the rerun rule kept>
set -Eeuo pipefail
source "$(dirname "$0")/am5r-env.sh" "${1:?mode}"
SHORT="${2:?commit short id}"; JOB="${3:?job id the rerun rule kept}"
check_checkout "$SHORT"
POP=heldout; [[ "$AM5R_MODE" == dev ]] && POP=development
OUT="$R/hand-sample-${SHORT}.json"
[[ ! -e "$OUT" ]] || { echo "the sample was drawn already ($OUT)" >&2; exit 2; }
rm -f "$OUT.tmp"
uv run --locked --offline python scripts/memcredit_am5r.py hand-sample --population "$POP" \
  --run-dir "$R/runs/${POP}/${JOB}/am5r" --evidence "$(artifact_for "$POP")" \
  --features "$R/private/features-${POP}.json.gz" --hand-dir "$R/hand" > "$OUT.tmp"
mv "$OUT.tmp" "$OUT"
chmod a-w "$R"/hand/*
cat "$OUT"
log_job "hand-check sample at ${SHORT}: $(python3 -c "import json,sys;d=json.load(open(sys.argv[1]));print(d['items'],'items in',d['chunks'],'chunks, sample',d['sample_sha256'][:16],'plan',d['plan_sha256'][:16])" "$OUT")"
