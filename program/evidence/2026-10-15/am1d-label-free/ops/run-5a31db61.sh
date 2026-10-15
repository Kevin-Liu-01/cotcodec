#!/bin/bash
set -euo pipefail
B=~/cotcodec-runs/stage0/am1d-label-free
R=~/cotcodec-runs/stage0/am1-study/runs
P=$B/private-5a31db61
cd $B/export-5a31db61
uv run --offline python scripts/memcredit_label_free.py extract --run-dir $R/main/1411/am1 --evidence $R/main/1411/study-artifact.json --private-dir $P --eager-run-dir $R/eager/1441/am1 > $B/extract-5a31db61.log 2>&1
for x in a b; do
  uv run --offline python scripts/memcredit_label_free.py analyze --features $P/features-1411.json.gz --eager-features $P/features-1441.json.gz --output-dir $B/out-5a31db61-$x > $B/analyze-5a31db61-$x.log 2>&1
done
uv run --offline --extra dev pytest -q tests/test_memcredit_label_free.py tests/test_memcredit_cost_curve.py > $B/pytest-5a31db61.log 2>&1 || true
echo done > $B/done-5a31db61
