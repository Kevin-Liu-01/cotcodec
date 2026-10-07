#!/bin/sh
# Build gold and do-nothing control jobs for one split inside the metric container.
# Usage: make_jobs.sh <split> <out.jsonl>
set -eu
cd /src
/opt/venv-lock/bin/python -m harness.q2_mutation.controls make-jobs \
  --osworld /inputs/OSWorld --file-cache /inputs/file_cache_1e112283/files \
  --splits program/evidence/q2-mutation/splits.json --split "$1" --out "$2"
