#!/usr/bin/env bash
# am3-nonabstain-generality-v1: after the image build job has ended (am3g-job-state.sh), print the
# image id it built, after checking the build's provenance verification is PASS and its receipt
# names that image, the commit and the capsule. A failed build is rebuilt once from the same
# capsule (registration section 8); a second failure stops the run before any GPU job.
# Usage: IMAGE=$(am3g-image.sh dev|reg <commit short id>)
set -Eeuo pipefail
source "$(dirname "$0")/am3g-env.sh" "${1:?mode}"
SHORT="${2:?commit short id}"
B="$R/overlay-build-vllm-${SHORT}"
[[ -f "$B/image-id.txt" && -f "$B/provenance-verification.json" && -f "$B/build-receipt.json" ]] \
  || { echo "no complete build record in $B" >&2; exit 2; }
IMAGE=$(tr -d ' \n' < "$B/image-id.txt")
python3 - "$B" "$IMAGE" "$(sha256sum "$R/capsule/source-${SHORT}.tar.gz" | cut -d" " -f1)" "$SHORT" <<'PY'
import json, sys
b, image, capsule, short = sys.argv[1:]
prov = json.load(open(f"{b}/provenance-verification.json"))
receipt = json.load(open(f"{b}/build-receipt.json"))
checks = {
    "provenance PASS": prov.get("status") == "PASS",
    "receipt names the image": receipt.get("overlay_image_id") == image,
    "receipt names the commit": str(receipt.get("git_sha", "")).startswith(short),
    "receipt names the capsule": receipt.get("source_sha256") == capsule,
    "vLLM 0.31.0": receipt.get("vllm_version") == "0.31.0",
}
bad = [k for k, ok in checks.items() if not ok]
if bad:
    sys.exit(f"build record fails: {bad}")
PY
log_job "image ${IMAGE} for ${SHORT}: provenance PASS, receipt checked"
echo "$IMAGE"
