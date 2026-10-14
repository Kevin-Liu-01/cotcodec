#!/usr/bin/env bash
# Read-only poll of the host: time, queue, E4 pair markers. One line per poll.
n=${1:-6}; every=${2:-290}
for i in $(seq 1 "$n"); do
  out="$(perl -e 'alarm shift; exec @ARGV' 60 ssh -o BatchMode=yes -o ConnectTimeout=20 -o LogLevel=ERROR fal-h100-01 '
    t=$(date -u +%FT%TZ); q=$(squeue -a -h -o "%i:%j:%T" | tr "\n" " ");
    p=$HOME/cotcodec-runs/stage0/q2-stage1e/pairs;
    m9=$(ls $p/e-9b-e4 2>/dev/null | grep -E "scontrol|collect|dr0.json|job_id" | tr "\n" ",");
    m4=$(ls $p/e-4b-e4 2>/dev/null | grep -E "scontrol|collect|dr0.json|job_id" | tr "\n" ",");
    c=$(ls $p | grep -c "e4-collect.tar");
    echo "$t q=[$q] 9b-e4={$m9} 4b-e4={$m4} e4_collect_tars=$c"' 2>&1 | sed -E 's/([0-9]{1,3}\.){3}[0-9]{1,3}/<ip>/g' | tr '\n' ' ')"
  echo "${out:-no-reply}"
  if [ "$i" -lt "$n" ]; then sleep "$every"; fi
done
