#!/usr/bin/env bash
# Stage the second timing job's run directory for the evidence bundle (small text files copied;
# large or derived files listed with their SHA-256 only). Usage: collect-timing2.sh JOB_ID
set -euo pipefail
job=$1
root="$HOME/cotcodec-runs/q3-dense-headroom-precheck-v2/timing-2-qwen3.5-4b-base"
src="$root/$job"
dst="$HOME/cotcodec-runs/stage0/q3-dense-v2/ops/timing-2/timing-$job"
mkdir -p "$dst"
for f in job.env termination.env gpu-prolog.env hard-stop.env manifest.json command.json \
         provenance-verification.txt model-verification.txt container-doctor.txt container.log \
         checkpoint.ready dense-precheck/timing-receipt.json dense-precheck/timing-progress.json \
         dense-precheck/checkpoints/dev-artifact.sha256; do
  if [[ -f "$src/$f" ]]; then
    name=$(echo "$f" | tr '/' '_')
    case "$name" in *.env) name="$name.txt" ;; esac
    cp "$src/$f" "$dst/$name"
  fi
done
cp "$root/slurm-$job.out" "$dst/" 2>/dev/null || true
cp -r "$root/fill-claims" "$dst/" 2>/dev/null || true
(cd "$src" && find . -type f ! -path './dense-precheck/cache/*' -printf '%P\n' | sort | xargs -r sha256sum) \
  > "$dst/host-files-sha256.txt"
echo "$(find "$src/dense-precheck/cache" -type f 2>/dev/null | wc -l) files under dense-precheck/cache (Triton)" \
  >> "$dst/host-files-sha256.txt"
scontrol show job "$job" > "$dst/scontrol-$job.txt" 2>/dev/null || true
ls -la "$dst"
