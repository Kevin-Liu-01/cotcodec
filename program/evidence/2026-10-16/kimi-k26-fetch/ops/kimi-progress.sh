#!/usr/bin/env bash
# Kimi-K2.6 fetch: one short progress line (bytes on disk under the snapshot, including the hub
# client's incomplete files, against the Hub's 595,204,999,341 bytes; the job's state; the tail of
# the lane's progress log). Appends to ops/progress.log. Usage: kimi-progress.sh <job id>
set -Eeuo pipefail
J="${1:?job id}"
R=/home/kevin/cotcodec-runs/stage0/kimi-k26-fetch
M=/home/kevin/cotcodec-runs/hf-cache/cotcodec-models/kimi-k2.6
TOTAL=595204999341
b=$(du -sb "$M" 2>/dev/null | cut -f1); b=${b:-0}
st=$(squeue -h -j "$J" -o "%T %M" 2>/dev/null || true); st=${st:-"not in queue"}
last=$(tail -c 2000 "/home/kevin/cotcodec-runs/model-fetch/cpu-$J/kimi-k2.6.log" 2>/dev/null \
  | tr '\r' '\n' | grep -a "Fetching" | tail -1 | cut -c1-90 || true)
printf '%s job %s [%s] %s bytes (%.1f%%) | %s\n' "$(date -u +%FT%TZ)" "$J" "$st" "$b" \
  "$(awk -v b="$b" -v t="$TOTAL" 'BEGIN{print 100*b/t}')" "$last" | tee -a "$R/ops/progress.log"
