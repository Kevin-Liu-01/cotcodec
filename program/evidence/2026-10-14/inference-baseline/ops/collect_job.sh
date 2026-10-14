#!/usr/bin/env bash
# Copy one inference-baseline job's lane receipts and driver outputs (not the JIT caches) from
# the host into this evidence directory, with a SHA-256 list of the host run directory.
# Usage: collect_job.sh JOB_LETTER SLURM_JOB_ID
set -euo pipefail
job="$1"; jid="$2"
here="$(cd "$(dirname "$0")/.." && pwd)"
remote="/home/kevin/cotcodec-runs/stage0/inference-baseline/runs/${job}"
dest="${here}/jobs/${job}-${jid}"
mkdir -p "${dest}"
ssh -o BatchMode=yes fal-h100-01 "cd ${remote}/${jid} && find . -path ./ib/cache -prune -o -type f -print0 | sort -z | xargs -0 sha256sum" > "${dest}/host-run-dir.sha256"
rsync -a -e "ssh -o BatchMode=yes" \
  --include='command.json' --include='container-doctor.txt' --include='gpu-compute-apps-prolog.csv' \
  --include='gpu-prolog.env' --include='job.env' --include='manifest.json' \
  --include='model-receipt.json' --include='model-verification.txt' \
  --include='provenance-verification.txt' --include='termination.env' \
  --include='ib/' --exclude='ib/cache/' --include='ib/**' --exclude='*' \
  "fal-h100-01:${remote}/${jid}/" "${dest}/"
rsync -a -e "ssh -o BatchMode=yes" "fal-h100-01:${remote}/slurm-${jid}.out" "${dest}/"
ssh -o BatchMode=yes fal-h100-01 "scontrol show job ${jid}" > "${dest}/scontrol-${jid}.txt" 2>/dev/null || true
du -sh "${dest}"
