#!/bin/bash
# am1-keepset-search-v1 development selftest (development data only), host CPU.
set -euo pipefail
C=ff935a86
B=~/cotcodec-runs/stage0/am1ks-dev-selftest-ff935a86
R=~/cotcodec-runs/stage0/am1-study/runs
P=$B/private-$C
cd $B/export-$C
uv run --offline --python 3.14.6 python scripts/memcredit_keepset_search.py extract --split development \
  --run-dir $R/main/1411/am1 --evidence $R/main/1411/study-artifact.json --private-dir $P \
  > $B/extract-$C.log 2>&1
for x in a b; do
  uv run --offline --python 3.14.6 python scripts/memcredit_keepset_search.py analyze --split development \
    --features $P/features-development-1411.json.gz --output-dir $B/out-$C-$x \
    > $B/analyze-$C-$x.log 2>&1
done
uv run --offline --python 3.14.6 python scripts/memcredit_keepset_search.py selftest \
  --analysis-dir $B/out-$C-a --features $P/features-development-1411.json.gz \
  --am1d-features ~/cotcodec-runs/stage0/am1d-label-free/private-5a31db61/features-1411.json.gz \
  --output $B/selftest-$C.json > $B/selftest-$C.log 2>&1 || true
uv run --offline --python 3.14.6 python scripts/memcredit_keepset_search.py power \
  --analysis-dir $B/out-$C-a --output $B/power-$C.json > $B/power-$C.log 2>&1
uv run --offline --python 3.14.6 --extra dev pytest -q tests/ \
  \
  > $B/pytest-$C.log 2>&1 || true
(cd $B && sha256sum out-$C-a/* out-$C-b/* $P/* selftest-$C.json power-$C.json) > $B/sha256-$C.txt
echo done > $B/done-$C
