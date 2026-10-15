#!/usr/bin/env bash
# Kimi-K2.6 fetch: log the queue, Slurm's GPU allocation, the disk and the absence of any Hugging
# Face token before the CPU-only fetch is submitted. The fetch requests no GPU, so this refuses only
# when a token is present (none may be used) or the model cache has under 1 TB free.
# Usage: kimi-preflight.sh <label>
set -Eeuo pipefail
R=/home/kevin/cotcodec-runs/stage0/kimi-k26-fetch
C=/home/kevin/cotcodec-runs/hf-cache
{ echo "== ${1:?label} at $(date -u +%FT%TZ)"; echo "-- squeue"; squeue -h -o "%i %j %T %M %b";
  echo "-- slurm gres"; scontrol show nodes -d | grep -E "^ *Gres(Used)?=";
  echo "-- disk (model cache)"; df -B1 --output=avail,size "$C" | tail -1; } | tee -a "$R/ops/preflight.log"
tok=0
[[ -n "${HF_TOKEN:-}${HUGGING_FACE_HUB_TOKEN:-}" ]] && tok=1
for f in ~/.cache/huggingface/token ~/.huggingface/token "$C/token" "$C/hub-cache/token"; do
  [[ -e "$f" ]] && tok=1; done
if (( tok )); then echo "a Hugging Face token is present; not submitting" | tee -a "$R/ops/preflight.log" >&2; exit 3; fi
avail=$(df -B1 --output=avail "$C" | tail -1 | tr -d ' ')
if (( avail < 1000000000000 )); then echo "under 1 TB free; not submitting" | tee -a "$R/ops/preflight.log" >&2; exit 4; fi
echo "no Hugging Face token in the environment or the known token files; $((avail / 1000000000)) GB free" | tee -a "$R/ops/preflight.log"
