#!/usr/bin/env bash
# LM1 host prep: log the queue, Slurm's GPU allocation, the GPUs, the disk and the absence of any
# Hugging Face token before a CPU-only job is submitted (kimi-preflight.sh's checks). Refuses when
# a token is present (none may be used), when the model cache has under 1 TB free, or, for a fetch,
# when a receipt or snapshot of a requested id already exists (nothing earlier is overwritten).
# Usage: lm1-preflight.sh <label> [model ids to be fetched...]
set -Eeuo pipefail
source "$(dirname "$0")/lm1-env.sh"
L="${1:?label}"; shift || true
{ echo "== ${L} at $(date -u +%FT%TZ)"; echo "-- squeue"; squeue -h -o "%i %j %T %M %b";
  echo "-- slurm gres"; scontrol show nodes -d | grep -E "^ *Gres(Used)?=";
  echo "-- gpus"; nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader;
  echo "-- disk (model cache)"; df -B1 --output=avail,size "$C" | tail -1; } | tee -a "$R/ops/preflight.log"
tok=0
[[ -n "${HF_TOKEN:-}${HUGGING_FACE_HUB_TOKEN:-}" ]] && tok=1
for f in ~/.cache/huggingface/token ~/.huggingface/token "$C/token" "$C/hub-cache/token"; do
  [[ -e "$f" ]] && tok=1; done
if (( tok )); then echo "a Hugging Face token is present; not submitting" | tee -a "$R/ops/preflight.log" >&2; exit 3; fi
avail=$(df -B1 --output=avail "$C" | tail -1 | tr -d ' ')
if (( avail < 1000000000000 )); then echo "under 1 TB free; not submitting" | tee -a "$R/ops/preflight.log" >&2; exit 4; fi
for id in "$@"; do
  if [[ -e "$RECEIPTS/$id.json" || -e "$MODELS/$id" ]]; then
    echo "$id already has a receipt or snapshot; not submitting" | tee -a "$R/ops/preflight.log" >&2; exit 5
  fi
done
echo "no Hugging Face token in the environment or the known token files; $((avail / 1000000000)) GB free" | tee -a "$R/ops/preflight.log"
