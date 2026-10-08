#!/usr/bin/env bash
# collect-lane.sh LANE_DIR JOB OUT: stage a lane job's small text records in OUT (on the host) and list
# SHA-256 digests of every other file in the job directory except the Triton cache (counted). Not copied:
# bundle copy, development artifact, chunk files, docker inspect records, system.txt, the batch script copy,
# the model receipt, the Triton cache. (v1's collect-lane.sh plus v2's interrupted receipt, marker,
# dev-artifact digest and hard-stop/resume records.)
set -euo pipefail
lane=$1; job=$2; out=$3
d="$lane/$job"
mkdir -p "$out"
for f in job.env termination.env gpu-prolog.env; do cp "$d/$f" "$out/$f.txt"; done
for f in manifest.json command.json provenance-verification.txt model-verification.txt container-doctor.txt container.log; do
  cp "$d/$f" "$out/$f"; done
if [[ -f "$d/hard-stop.env" ]]; then cp "$d/hard-stop.env" "$out/hard-stop.env.txt"; fi
if [[ -f "$d/resume-receipt.json" ]]; then cp "$d/resume-receipt.json" "$out/resume-receipt.json"; fi
if [[ -f "$d/checkpoint.ready" ]]; then cp "$d/checkpoint.ready" "$out/checkpoint.ready"; fi
cp "$lane/slurm-$job.out" "$out/slurm-$job.out"
if [[ -f "$d/dense-precheck/receipt.json" ]]; then cp "$d/dense-precheck/receipt.json" "$out/receipt.json"; fi
if [[ -f "$d/dense-precheck/receipt-interrupted.json" ]]; then
  cp "$d/dense-precheck/receipt-interrupted.json" "$out/receipt-interrupted.json"; fi
if [[ -f "$d/dense-precheck/checkpoints/dev-artifact.sha256" ]]; then
  cp "$d/dense-precheck/checkpoints/dev-artifact.sha256" "$out/dev-artifact.sha256"; fi
( cd "$d" && find . -type f ! -path "./dense-precheck/cache/*" ! -name job.env ! -name termination.env \
    ! -name gpu-prolog.env ! -name manifest.json ! -name command.json ! -name provenance-verification.txt \
    ! -name model-verification.txt ! -name container-doctor.txt ! -name container.log ! -name hard-stop.env \
    ! -name resume-receipt.json -print0 | sort -z | xargs -0 sha256sum | sed "s#  \./#  #" ) > "$out/host-files-sha256.txt"
echo "$(find "$d/dense-precheck/cache" -type f 2>/dev/null | wc -l) files under dense-precheck/cache (Triton), not listed" \
  >> "$out/host-files-sha256.txt"
echo "staged $(ls "$out" | wc -l) files; $(wc -l < "$out/host-files-sha256.txt") digest lines"
