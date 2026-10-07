#!/bin/sh
# Score a jobs JSONL under both metric venvs inside the metric container.
# Usage: score.sh <jobs.jsonl> <out-prefix> [workers] [repeat]
set -eu
jobs="$1"; prefix="$2"; workers="${3:-16}"; repeat="${4:-2}"
cd /src
for arm in lock scout; do
  case "$arm" in
    lock) req=/opt/q2/osworld-lock-export.txt ;;
    scout) req=/opt/q2/scout-venv-freeze.txt ;;
  esac
  /opt/venv-$arm/bin/python -m harness.q2_mutation.offline_eval \
    --jobs "$jobs" --out "${prefix}-verdicts-$arm.jsonl" --notes "${prefix}-notes-$arm.jsonl" \
    --osworld /inputs/OSWorld --file-cache /inputs/file_cache_1e112283/files \
    --requirements "$req" --dep-set "$arm" --workers "$workers" --repeat "$repeat" \
    --harness-revision "$(cat /src/.git_sha 2>/dev/null || echo unknown)"
done
cp /opt/q2/venv-lock.fingerprint.json /opt/q2/venv-scout.fingerprint.json "$(dirname "$prefix")/"
