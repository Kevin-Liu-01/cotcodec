#!/usr/bin/env bash
# am1-memory-credit-v1 (CONFIRMATORY): the registered hand-sample command (registration section
# 17) on the host CPU, from the clean clone at the freeze commit: the seeded sample (seed 44) of
# 120 judged reader items for G2's blind hand check, written WITHOUT any judge label to
# HOST_DIR/hand-check-sample.jsonl (texts stay on the host). Prints only the item count; the file
# is made read-only and its SHA-256 logged. Nothing is labelled here. Usage: am1c-hand-sample.sh <job id>
set -Eeuo pipefail
FREEZE=9ad36b10dcbd324647e4a98c3a150f954f7123f6
ARTIFACT_SHA256=f23bca047dc7246c5a8db12f67a76a2ea36304d8669dc5c62ae6c42821f73eb7
JOB="${1:?job id}"
R=/home/kevin/cotcodec-runs/stage0/am1-memory-credit-v1
RUN_DIR=$R/runs/main/$JOB
cd "$R/checkout"
[[ -z "$(git status --porcelain)" ]] || { echo dirty; exit 2; }
[[ "$(git rev-parse HEAD)" == "${FREEZE}" ]] || { echo "checkout is not at the freeze commit"; exit 2; }
[[ "$(sha256sum "$R/study-artifact.json" | cut -d" " -f1)" == "${ARTIFACT_SHA256}" ]] || { echo "artifact digest"; exit 2; }
[[ ! -e "$R/hand-check-sample.jsonl" ]] || { echo "the sample exists; not redrawn"; exit 2; }
uv run --locked --offline python scripts/memcredit_analyze.py hand-sample \
  --config experiments/am1/am1-memory-credit-v1.yaml --run-dir "$RUN_DIR/am1" \
  --evidence "$R/study-artifact.json" --expected-evidence-sha256 "${ARTIFACT_SHA256}" \
  --output "$R/hand-check-sample.jsonl" > "$R/ops/hand-sample-stdout.json" 2> "$R/ops/hand-sample-stderr.txt"
chmod a-w "$R/hand-check-sample.jsonl"
cat "$R/ops/hand-sample-stdout.json"
echo "$(date -u +%FT%TZ) hand-check sample drawn (registered command, job ${JOB}, no labels): $(cd "$R" && sha256sum hand-check-sample.jsonl)" | tee -a "$R/ops/jobs.log"
