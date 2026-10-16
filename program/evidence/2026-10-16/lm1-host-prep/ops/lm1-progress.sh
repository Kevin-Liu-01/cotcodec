#!/usr/bin/env bash
# LM1 host prep: one short progress line per model id (bytes on disk under the snapshot, including
# the hub client's incomplete files, against the Hub listing's bytes) and the state of the given
# jobs. Appends to ops/progress.log. Usage: lm1-progress.sh <job id>...
set -Eeuo pipefail
source "$(dirname "$0")/lm1-env.sh"
{
  for id in $LM1_IDS; do
    b=$(du -sb "$MODELS/$id" 2>/dev/null | cut -f1 || true); b=${b:-0}
    t=$(expected_bytes "$id")
    r="-"; [[ -f "$RECEIPTS/$id.json" ]] && r="receipt"
    printf '%s %-46s %14s / %14s (%5.1f%%) %s\n' "$(date -u +%FT%TZ)" "$id" "$b" "$t" \
      "$(awk -v b="$b" -v t="$t" 'BEGIN{print (t>0)?100*b/t:0}')" "$r"
  done
  for j in "$@"; do
    st=$(squeue -h -j "$j" -o "%T %M" 2>/dev/null || true); echo "  job $j [${st:-not in queue}]"
  done
} | tee -a "$R/ops/progress.log"
