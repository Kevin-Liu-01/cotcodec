#!/usr/bin/env bash
# am5-ablated-cost-v1: log the queue, Slurm's GPU allocation and the GPU state. Exit 3
# when a GPU job of this program is queued or running (every GPU job not named transcreate-*;
# those are D110's other project, which holds its own GPUs and is never touched). Exit 4 when
# fewer than the needed H100s are free in Slurm. Slurm allocates the GPUs. Everything it prints
# goes to stderr (and the log), so the scripts that call it (am5r-build.sh, am5r-submit.sh)
# print only the job id they submit on stdout.
# Usage: am5r-preflight.sh dev|reg <label> [gpus, default 1]
set -Eeuo pipefail
source "$(dirname "$0")/am5r-env.sh" "${1:?mode}"
LABEL="${2:?label}"; NEED="${3:-1}"
total=$(scontrol show nodes -d | sed -n 's/^ *Gres=gpu:h100:\([0-9]*\).*/\1/p' | head -1)
used=$(scontrol show nodes -d | sed -n 's/^ *GresUsed=gpu:h100:\([0-9]*\).*/\1/p' | head -1)
{ echo "== ${LABEL} at $(date -u +%FT%TZ)"; echo "-- squeue"; squeue -h -o "%i %j %T %M %b";
  echo "-- slurm gres"; scontrol show nodes -d | grep -E "^ *Gres(Used)?=";
  echo "-- gpus"; nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader; } \
  | tee -a "$R/ops/preflight.log" >&2
if squeue -h -o "%j %b" | awk '$1 !~ /^transcreate-/ && $2 ~ /gpu/' | grep -q .; then
  echo "a GPU job of this program is queued or running; not submitting" | tee -a "$R/ops/preflight.log" >&2; exit 3; fi
free=$(( ${total:-0} - ${used:-0} ))
if (( free < NEED )); then
  echo "only ${free} H100 free in Slurm (need ${NEED}); not submitting" | tee -a "$R/ops/preflight.log" >&2; exit 4; fi
echo "no GPU job of this program; ${free} of ${total} H100 free in Slurm (need ${NEED})" | tee -a "$R/ops/preflight.log" >&2
