#!/usr/bin/env bash
# LM1 host prep (D125): shared host paths for the operator scripts. Sourced, not run.
R=/home/kevin/cotcodec-runs/stage0/lm1-host-prep
C=/home/kevin/cotcodec-runs/hf-cache
MODELS="$C/cotcodec-models"
# The lane's model receipt root, so any candidate can be a lane job's pinned model later.
RECEIPTS="$C/cotcodec-receipts"
LM1_IDS="kimi-k2.5-ud-tq1-0-gguf deepseek-v4-flash-0731-ds4-q2-gguf deepseek-v4-flash-0731-ud-iq3-xxs-gguf deepseek-v4-flash-0731-ud-q8-k-xl-gguf qwen3-235b-a22b-instruct-2507-ud-q3-k-xl-gguf gpt-oss-120b-mxfp4-gguf"
mkdir -p "$R/ops"
log_job() { local line; line="$(date -u +%FT%TZ) $*"; echo "$line" >> "$R/ops/jobs.log"; echo "$line" >&2; }
# Expected bytes per model (the Hub listing of the allowed files at the pinned revision).
expected_bytes() {
  case "$1" in
    kimi-k2.5-ud-tq1-0-gguf) echo 239537678077 ;;
    deepseek-v4-flash-0731-ds4-q2-gguf) echo 86720115016 ;;
    deepseek-v4-flash-0731-ud-iq3-xxs-gguf) echo 104207853858 ;;
    deepseek-v4-flash-0731-ud-q8-k-xl-gguf) echo 161869621346 ;;
    qwen3-235b-a22b-instruct-2507-ud-q3-k-xl-gguf) echo 104152938929 ;;
    gpt-oss-120b-mxfp4-gguf) echo 63387346665 ;;
    *) echo 0 ;;
  esac
}
