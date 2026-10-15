#!/usr/bin/env bash
# Kimi-K2.6 reference checkpoint: fetch moonshotai/Kimi-K2.6 at its pinned revision through the
# GPU-less fetch lane (infra/slurm/host-single-node/fetch-model-cpu.sbatch; no GRES, no
# credentials: the host has no Hugging Face token and none is passed), from a git archive of the
# commit that registered it. The lane writes the full-snapshot receipt (every file's SHA-256 and
# the artifact root) to hf-cache/cotcodec-receipts-cpu-lane/kimi-k2.6.json and the snapshot to
# hf-cache/cotcodec-models/kimi-k2.6/. The snapshot is 595.2 GB, so the lane's 4 h limit is
# raised to 12 h on the sbatch command line; the batch script itself is unchanged.
# Usage: kimi-fetch.sh <commit short id>
set -Eeuo pipefail
SHORT="${1:?commit short id}"
R=/home/kevin/cotcodec-runs/stage0/kimi-k26-fetch
SRC="$R/src/${SHORT}"
[[ "$(cut -c1-8 "$SRC/.git_sha")" == "${SHORT}" ]] || { echo "source is not ${SHORT}"; exit 2; }
grep -q "^  kimi-k2.6:" "$SRC/models/registry.yaml" || { echo "no registry entry"; exit 2; }
"$R/ops/kimi-preflight.sh" "fetch ${SHORT}"
j=$(sbatch --parsable --time=12:00:00 --export=ALL,COTCODEC_FETCH_SOURCE="$SRC",COTCODEC_MODEL_IDS=kimi-k2.6 \
  "$SRC/infra/slurm/host-single-node/fetch-model-cpu.sbatch")
echo "$(date -u +%FT%TZ) Kimi-K2.6 fetch job $j submitted (CPU lane, no GRES, limit 12 h; source ${SHORT})" | tee -a "$R/ops/jobs.log"
