#!/usr/bin/env bash
# Queue an experiment for the Mac Mini to run.
# Usage: ./scripts/queue-experiment.sh experiments/pilot_01_tau_bench.yaml
#
# Copies the experiment YAML to the queue directory.
# The Mac Mini's experiment runner picks it up and processes it.

set -euo pipefail

if [ $# -eq 0 ]; then
  echo "Usage: $0 <experiment.yaml>"
  echo "Available experiments:"
  ls -1 experiments/*.yaml 2>/dev/null || echo "  (none)"
  exit 1
fi

EXPERIMENT="$1"
QUEUE_DIR="data/queue"
mkdir -p "$QUEUE_DIR"

BASENAME=$(basename "$EXPERIMENT")
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
QUEUED="${QUEUE_DIR}/${TIMESTAMP}_${BASENAME}"

cp "$EXPERIMENT" "$QUEUED"
echo "Queued: $QUEUED"
echo "The Mac Mini experiment runner will pick this up on its next cycle."
