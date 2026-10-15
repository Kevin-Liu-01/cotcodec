#!/usr/bin/env bash
# am1-memory-credit-v1 (CONFIRMATORY): the registered analyze and aa commands (registration
# section 17) on the host CPU, from a `git archive` export of the freeze commit (extracted with
# GNU tar on the host), after the hand labels' SHA-256 was committed (receipt commit 9e641945).
# Checks the export's archive digest and the 19 section-17 pins, the artifact's and the hand
# labels' digests, then runs `analyze` (with --hand-labels and --hand-labels-sha256) and `aa`
# exactly as registered, once. Outputs are made read-only and their SHA-256 logged.
# Usage: am1c-analyze.sh <job id>   (pins: HOST_DIR/ops/pins.sha256, the committed ops/pins.sha256)
set -Eeuo pipefail
FREEZE=9ad36b10dcbd324647e4a98c3a150f954f7123f6
ARCHIVE_SHA256=8806cd7b6c78030e9a6f958cf6894ad549c8635f17f0d3bed4fd0d66c1112204
ARTIFACT_SHA256=f23bca047dc7246c5a8db12f67a76a2ea36304d8669dc5c62ae6c42821f73eb7
HAND_LABELS_SHA256=70a5f2ec5fb27391732481421288842f5669171397d8c7d21f260c2233670c66
JOB="${1:?job id}"
R=/home/kevin/cotcodec-runs/stage0/am1-memory-credit-v1
RUN_DIR=$R/runs/main/$JOB
E=$R/analysis/export-9ad36b10
ANALYSIS_DIR=$R/analysis/$JOB
LOGS=$R/analysis/logs-$JOB
HAND_LABELS=/home/kevin/cotcodec-runs/stage0/am1-confirmatory/hand-labels.jsonl
log() { echo "$(date -u +%FT%TZ) $*" | tee -a "$R/ops/jobs.log"; }

[[ "$(sha256sum "$R/archive/freeze-9ad36b10.tar" | cut -d" " -f1)" == "${ARCHIVE_SHA256}" ]] || { echo "archive digest"; exit 2; }
[[ "$(git -C "$R/checkout" rev-parse HEAD)" == "${FREEZE}" ]] || { echo "clone not at the freeze commit"; exit 2; }
(cd "$E" && sha256sum --quiet -c "$R/ops/pins.sha256") || { echo "pins"; exit 2; }
[[ "$(sha256sum "$R/study-artifact.json" | cut -d" " -f1)" == "${ARTIFACT_SHA256}" ]] || { echo "artifact digest"; exit 2; }
[[ "$(sha256sum "${HAND_LABELS}" | cut -d" " -f1)" == "${HAND_LABELS_SHA256}" ]] || { echo "hand labels digest"; exit 2; }
[[ ! -e "${ANALYSIS_DIR}" ]] || { echo "the analysis exists; not rerun"; exit 2; }
mkdir -p "${LOGS}"
log "analysis start (registered analyze then aa, job ${JOB}, export of ${FREEZE})"
cd "$E"
set +e
uv run --locked --offline python scripts/memcredit_analyze.py analyze \
  --config experiments/am1/am1-memory-credit-v1.yaml --run-dir "$RUN_DIR/am1" \
  --evidence "$R/study-artifact.json" --expected-evidence-sha256 "${ARTIFACT_SHA256}" \
  --output-dir "${ANALYSIS_DIR}" --hand-labels "${HAND_LABELS}" \
  --hand-labels-sha256 "${HAND_LABELS_SHA256}" \
  > "${LOGS}/analyze-stdout.json" 2> "${LOGS}/analyze-stderr.txt"
A=$?
log "analyze exit ${A}"
uv run --locked --offline python scripts/memcredit_analyze.py aa \
  --config experiments/am1/am1-memory-credit-v1.yaml --run run="$RUN_DIR/am1" \
  --pair run:reader-gpu0,run:reader-gpu1 --pair run:judge32-gpu0,run:judge32-gpu1 \
  --evidence "$R/study-artifact.json" --expected-evidence-sha256 "${ARTIFACT_SHA256}" \
  --output "${ANALYSIS_DIR}/aa.json" \
  > "${LOGS}/aa-stdout.jsonl" 2> "${LOGS}/aa-stderr.txt"
B=$?
log "aa exit ${B}"
set -e
echo "analyze ${A} aa ${B}" > "${LOGS}/exits.txt"
(cd "${ANALYSIS_DIR}" && sha256sum ./* > "${LOGS}/outputs.sha256")
chmod -R a-w "${ANALYSIS_DIR}"
log "analysis done (analyze ${A}, aa ${B}); outputs read-only"
