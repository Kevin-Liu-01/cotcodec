#!/usr/bin/env bash
# LM1 host prep: fetch registered GGUF candidates at their pinned revisions through the GPU-less
# fetch lane (infra/slurm/host-single-node/fetch-model-cpu.sbatch: no GRES, anonymous, no
# credentials), from a git archive of the commit that registered them. Each entry's
# allow_patterns limits the download to its own quantization. The receipts go to the lane's model
# receipt root (COTCODEC_RECEIPT_DIR=cotcodec-receipts), so a lane job can pin any candidate; the
# preflight refuses an id that already has a receipt or snapshot. The lane's 4 h limit is raised to
# 8 h on the sbatch command line; the batch script itself is unchanged.
# Usage: lm1-fetch.sh <commit short id> <label> <model id>...
set -Eeuo pipefail
source "$(dirname "$0")/lm1-env.sh"
SHORT="${1:?commit short id}"; LABEL="${2:?label}"; shift 2
(( $# > 0 )) || { echo "no model ids"; exit 2; }
SRC="$R/src/${SHORT}"
[[ "$(cut -c1-8 "$SRC/.git_sha")" == "${SHORT}" ]] || { echo "source is not ${SHORT}"; exit 2; }
for id in "$@"; do
  grep -q "^  ${id}:" "$SRC/models/registry.yaml" || { echo "no registry entry for $id"; exit 2; }
done
"$(dirname "$0")/lm1-preflight.sh" "fetch ${LABEL} ${SHORT}" "$@"
j=$(sbatch --parsable --time=08:00:00 --job-name="lm1-fetch-${LABEL}" \
  --export=ALL,COTCODEC_FETCH_SOURCE="$SRC",COTCODEC_MODEL_IDS="$*",COTCODEC_RECEIPT_DIR=cotcodec-receipts \
  "$SRC/infra/slurm/host-single-node/fetch-model-cpu.sbatch")
[[ "$j" =~ ^[0-9]+$ ]] || { echo "sbatch printed no job id: '$j'"; exit 2; }
log_job "LM1 fetch ${LABEL} job $j submitted (CPU lane, no GRES, limit 8 h; source ${SHORT}; ids: $*)"
echo "$j"
