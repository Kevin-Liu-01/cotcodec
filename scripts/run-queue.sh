#!/usr/bin/env bash
# Process the experiment queue (runs on Mac Mini via cron or manually).
# Picks up queued experiments, runs them, moves to completed.

set -euo pipefail

QUEUE_DIR="data/queue"
DONE_DIR="data/queue/completed"
mkdir -p "$QUEUE_DIR" "$DONE_DIR"

PENDING=$(ls -1 "$QUEUE_DIR"/*.yaml 2>/dev/null || true)
if [ -z "$PENDING" ]; then
  echo "No experiments in queue."
  exit 0
fi

echo "Processing experiment queue..."
for YAML in $QUEUE_DIR/*.yaml; do
  NAME=$(basename "$YAML")
  echo "→ Running: $NAME"

  if python3 -m harness.runner "$YAML"; then
    mv "$YAML" "$DONE_DIR/$NAME"
    echo "  ✓ Completed, moved to $DONE_DIR"
  else
    echo "  ✗ Failed, leaving in queue for retry"
  fi
done

echo "Queue processing complete."

# Auto-push results if in a git repo
if git rev-parse --git-dir > /dev/null 2>&1; then
  git add data/results/ data/queue/completed/
  git commit -m "data: experiment queue batch $(date +%Y-%m-%d)" 2>/dev/null || true
  git push 2>/dev/null || true
fi
