#!/usr/bin/env bash
# AM3 (EXPLORATORY): fetch allenai/OLMo-2-1124-7B-Instruct at its pinned revision through the
# GPU-less fetch lane (infra/slurm/host-single-node/fetch-model-cpu.sbatch; no GRES, no
# credentials: the host has no Hugging Face token and none is passed), from a git archive of the
# commit that registered it. The lane writes the full-snapshot receipt (every file's SHA-256 and
# the artifact root) to hf-cache/cotcodec-receipts-cpu-lane/olmo-2-1124-7b-instruct.json.
# Usage: am3-fetch-olmo2.sh <commit short id>
set -Eeuo pipefail
SHORT="${1:?commit short id}"
R=/home/kevin/cotcodec-runs/stage0/am3-reader-replication
SRC="$R/src/${SHORT}"
[[ "$(cut -c1-8 "$SRC/.git_sha")" == "${SHORT}" ]] || { echo "source is not ${SHORT}"; exit 2; }
grep -q "^  olmo-2-1124-7b-instruct:" "$SRC/models/registry.yaml" || { echo "no registry entry"; exit 2; }
j=$(sbatch --parsable --export=ALL,COTCODEC_FETCH_SOURCE="$SRC",COTCODEC_MODEL_IDS=olmo-2-1124-7b-instruct \
  "$SRC/infra/slurm/host-single-node/fetch-model-cpu.sbatch")
echo "$(date -u +%FT%TZ) OLMo-2-1124-7B-Instruct fetch job $j submitted (CPU lane, no GRES; source ${SHORT})" | tee -a "$R/ops/jobs.log"
