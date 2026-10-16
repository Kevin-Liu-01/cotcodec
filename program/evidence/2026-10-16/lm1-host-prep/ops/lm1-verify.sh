#!/usr/bin/env bash
# LM1 host prep: re-hash every candidate snapshot against its receipt in the GPU-less verification
# lane (infra/slurm/host-single-node/verify-models-cpu.sbatch; no GRES, no network), from the git
# archive of commit $1. Reading every byte also warms the page cache for the smoke test.
# Usage: lm1-verify.sh <commit short id> [model ids... (default: all LM1 ids)]
set -Eeuo pipefail
source "$(dirname "$0")/lm1-env.sh"
SHORT="${1:?commit short id}"; shift
IDS="${*:-$LM1_IDS}"
SRC="$R/src/${SHORT}"
[[ "$(cut -c1-8 "$SRC/.git_sha")" == "${SHORT}" ]] || { echo "source is not ${SHORT}"; exit 2; }
j=$(sbatch --parsable --job-name=lm1-verify --output="$R/ops/slurm-lm1-verify-%j.out" \
  --export=ALL,COTCODEC_FETCH_SOURCE="$SRC",COTCODEC_MODEL_IDS="$IDS",COTCODEC_RECEIPT_DIR=cotcodec-receipts \
  "$SRC/infra/slurm/host-single-node/verify-models-cpu.sbatch")
[[ "$j" =~ ^[0-9]+$ ]] || { echo "sbatch printed no job id: '$j'"; exit 2; }
log_job "LM1 receipt verification job $j submitted (CPU only, no GRES, no network; source ${SHORT}; ids: $IDS)"
echo "$j"
