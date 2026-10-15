#!/bin/bash
# am1-keepset-search-v1 registered run (section 16), freeze commit 72d50162. Runs once.
set -u
B="$HOME/cotcodec-runs/stage0/am1-keepset-search-v1"
EXPORT_DIR="$B/export-72d50162"; PRIVATE_DIR="$B/private"; OUTPUT_DIR="$B/out"; LOG_DIR="$B/logs"
HELDOUT_RUN="$HOME/cotcodec-runs/stage0/am1-memory-credit-v1/runs/main/1458/am1"
HELDOUT_ARTIFACT="$HOME/cotcodec-runs/stage0/am1-memory-credit-v1/study-artifact.json"
date -u +%Y-%m-%dT%H:%M:%SZ > "$LOG_DIR/start.txt"
cd "$EXPORT_DIR"
uv run --offline --python 3.14.6 python scripts/memcredit_keepset_search.py extract \
  --split heldout --run-dir "$HELDOUT_RUN" --evidence "$HELDOUT_ARTIFACT" --private-dir "$PRIVATE_DIR" \
  > "$LOG_DIR/extract.log" 2>&1; echo "exit $?" >> "$LOG_DIR/extract.log"
uv run --offline --python 3.14.6 python scripts/memcredit_keepset_search.py analyze \
  --split heldout --features "$PRIVATE_DIR/features-heldout-1458.json.gz" --output-dir "$OUTPUT_DIR" \
  > "$LOG_DIR/analyze.log" 2>&1; echo "exit $?" >> "$LOG_DIR/analyze.log"
uv run --offline --python 3.14.6 --extra dev pytest -q tests/test_memcredit_keepset_search.py \
  > "$LOG_DIR/pytest.log" 2>&1; echo "exit $?" >> "$LOG_DIR/pytest.log"
date -u +%Y-%m-%dT%H:%M:%SZ > "$LOG_DIR/end.txt"
