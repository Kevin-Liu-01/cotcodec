#!/usr/bin/env bash
# LM2 (D129) operator environment on the host. Sourced, not run.
R=/home/kevin/cotcodec-runs/stage0/lm2-resident-eval
C=/home/kevin/cotcodec-runs/hf-cache
MODELS="$C/cotcodec-models"
RECEIPTS="$C/cotcodec-receipts"
# The evaluation sets live under the model cache, which the lane mounts read-only at /model-cache.
DATA="$C/cotcodec-datasets/lm2"
mkdir -p "$R/ops"
log_job() { local line; line="$(date -u +%FT%TZ) $*"; echo "$line" >> "$R/ops/jobs.log"; echo "$line" >&2; }
