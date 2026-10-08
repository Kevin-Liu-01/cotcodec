#!/bin/sh
# CPU-only driver for cpu_study.py: (problem, channel) jobs, three at a time.
# Usage: PY=/path/to/python sh run_cpu_study.sh [outdir]
# L1/47 (8.6 GB fp32 input, no matmul) runs last and alone.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=${1:-$HERE/cpu}
PY=${PY:-python}
mkdir -p "$OUT/logs"
# third field: --batch-subset (0 = full batch). The large-output, batch-independent
# problems are evaluated on the leading samples of each registered draw.
jobs() {
  for ch in A1 A2 A3; do
    for p in "L1/10 0" "L1/18 0" "L1/15 0" "L2/95 0" "L2/59 0" "L2/77 0" "L2/52 0" "L2/60 32" "L2/46 32" "L2/87 32" "L2/100 4"; do
      set -- $p
      echo "$1 $ch $2"
    done
  done
}
# Draws per channel: A1 all five; A2 the sign-mixed distributions (randn 0, uniform8 1,
# ties 4, constrows 6) and spiky (3); A3 lead5 (1), inner37 (2) and allprime (4, where it
# exists). The same-sign A2 draws (samesign100 2, allneg 5) scale the A1 picture, and
# A3 lead1 / inner137 are the smallest and largest shapes (cost, not information).
ONLY="A2:0,1,3,4,6;A3:1,2,4"
jobs | xargs -P 3 -L 1 sh -c '"$0" "'"$HERE"'/cpu_study.py" "$1" --channels "$2" --batch-subset "$3" --only "'"$ONLY"'" --threads 6 --out "'"$OUT"'" >> "'"$OUT"'/logs/$(echo $1 | tr / -)-$2.log" 2>&1' "$PY"
"$PY" "$HERE/cpu_study.py" L1/47 --channels A1 --threads 12 --out "$OUT" >> "$OUT/logs/L1-47.log" 2>&1
echo finished
