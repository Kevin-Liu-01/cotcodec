#!/bin/sh
# CPU-only driver for alt_algorithms.py: one process per problem, three at a time,
# the heavy problems first. Usage: PY=/path/to/python sh run_alt.sh [outdir]
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=${1:-$HERE/alt}
PY=${PY:-python}
mkdir -p "$OUT/logs"
for p in L2/77 L2/59 L2/52 L2/100 L2/87 L2/46 L2/60 L1/18 L1/15 L2/95 L1/10 L1/47; do echo "$p"; done |
  xargs -P 3 -L 1 sh -c '"$0" "'"$HERE"'/alt_algorithms.py" "$1" --threads 6 --out "'"$OUT"'" >> "'"$OUT"'/logs/$(echo $1 | tr / -).log" 2>&1' "$PY"
echo finished
