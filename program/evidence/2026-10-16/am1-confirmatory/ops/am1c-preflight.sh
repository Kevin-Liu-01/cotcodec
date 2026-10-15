#!/usr/bin/env bash
# am1-memory-credit-v1 (CONFIRMATORY; frozen, ledger row 23): log the queue, Slurm's GPU
# allocation and the GPU state. Exit 3 when a GPU job of this program is queued or running
# (every GPU job not named transcreate-*; those are D110's other project, which holds its own
# GPUs and does not block submission, registration section 11). Exit 4 when fewer than the
# needed H100s are free in Slurm. Usage: am1c-preflight.sh <label> [gpus needed, default 2]
set -Eeuo pipefail
R=/home/kevin/cotcodec-runs/stage0/am1-memory-credit-v1
NEED="${2:-2}"
total=$(scontrol show nodes -d | sed -n 's/^ *Gres=gpu:h100:\([0-9]*\).*/\1/p' | head -1)
used=$(scontrol show nodes -d | sed -n 's/^ *GresUsed=gpu:h100:\([0-9]*\).*/\1/p' | head -1)
{ echo "== ${1:?label} at $(date -u +%FT%TZ)"; echo "-- squeue"; squeue -h -o "%i %j %T %M %b";
  echo "-- slurm gres"; scontrol show nodes -d | grep -E "^ *Gres(Used)?=";
  echo "-- gpus"; nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader; } \
  | tee -a "$R/ops/preflight.log"
if squeue -h -o "%j %b" | awk '$1 !~ /^transcreate-/ && $2 ~ /gpu/' | grep -q .; then
  echo "a GPU job of this program is queued or running; not submitting" | tee -a "$R/ops/preflight.log" >&2; exit 3; fi
free=$(( ${total:-0} - ${used:-0} ))
if (( free < NEED )); then
  echo "only ${free} H100 free in Slurm (need ${NEED}); not submitting" | tee -a "$R/ops/preflight.log" >&2; exit 4; fi
echo "no GPU job of this program; ${free} of ${total} H100 free in Slurm (need ${NEED})" | tee -a "$R/ops/preflight.log"
