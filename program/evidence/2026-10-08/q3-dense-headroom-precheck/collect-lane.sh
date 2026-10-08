#!/usr/bin/env bash
# collect-lane.sh LANE_DIR JOB OUT: stage a lane job's small text records in OUT (on the host) and list
# SHA-256 digests of every other file in the job directory (not copied: bundle copy, development artifact,
# chunk files, docker inspect records, system.txt, the batch script copy, the model receipt).
set -euo pipefail
lane=$1; job=$2; out=$3
d="$lane/$job"
mkdir -p "$out"
for f in job.env termination.env gpu-prolog.env; do cp "$d/$f" "$out/$f.txt"; done
for f in manifest.json command.json provenance-verification.txt model-verification.txt container-doctor.txt container.log; do
  cp "$d/$f" "$out/$f"; done
[[ -f "$d/hard-stop.env" ]] && cp "$d/hard-stop.env" "$out/hard-stop.env.txt"
[[ -f "$d/resume-receipt.json" ]] && cp "$d/resume-receipt.json" "$out/resume-receipt.json"
cp "$lane/slurm-$job.out" "$out/slurm-$job.out"
[[ -f "$d/dense-precheck/receipt.json" ]] && cp "$d/dense-precheck/receipt.json" "$out/receipt.json"
[[ -f "$d/dense-precheck/receipt-interrupted.json" ]] && cp "$d/dense-precheck/receipt-interrupted.json" "$out/receipt-interrupted.json"
( cd "$d" && find . -type f ! -name job.env ! -name termination.env ! -name gpu-prolog.env ! -name manifest.json \
    ! -name command.json ! -name provenance-verification.txt ! -name model-verification.txt ! -name container-doctor.txt \
    ! -name container.log ! -name hard-stop.env ! -name resume-receipt.json -print0 | sort -z | xargs -0 sha256sum \
    | sed 's#  \./#  #' ) > "$out/host-files-sha256.txt"
echo "staged $(ls "$out" | wc -l) files; $(wc -l < "$out/host-files-sha256.txt") digests"
