#!/usr/bin/env bash
# AM5: after the build job ended, print the image id it built (one line) after checking its record
# against the pins: provenance PASS for this commit and capsule; a receipt naming the image, the
# commit, the capsule, vLLM 0.31.0 at db9527a4 and the pinned base image. Reads records only.
# Usage: IMAGE=$(bash ops/am5/am5-image.sh <commit short id>)
set -Eeuo pipefail
source "$(dirname "$0")/am5-env.sh"
SHORT="${1:?commit short id}"
B="$R/overlay-build-vllm-${SHORT}"
[[ -f "$B/image-id.txt" && -f "$B/provenance-verification.json" && -f "$B/build-receipt.json" ]] \
  || { echo "no complete build record in $B" >&2; exit 2; }
IMAGE=$(tr -d ' \n' < "$B/image-id.txt")
check_image "$IMAGE"
GIT=$(git -C "$C" rev-parse HEAD)
python3 - "$B" "$IMAGE" "$(sha256sum "$R/capsule/source-${SHORT}.tar.gz" | cut -d" " -f1)" "$GIT" >&2 <<'PY'
import json, sys
b, image, capsule, git = sys.argv[1:]
prov = json.load(open(f"{b}/provenance-verification.json"))
receipt = json.load(open(f"{b}/build-receipt.json"))
base = ("docker.io/vllm/vllm-openai@sha256:"
        "b18abb2df97b8f798e81862bd93f872ea18613372e2c3adc0cc2ac21e66ac12f")
checks = {
    "provenance PASS": prov.get("status") == "PASS",
    "provenance names the commit": prov.get("git_sha") == git,
    "provenance names the capsule": prov.get("source_sha256") == capsule,
    "receipt names the image": receipt.get("overlay_image_id") == image,
    "receipt names the commit": receipt.get("git_sha") == git,
    "receipt names the capsule": receipt.get("source_sha256") == capsule,
    "vLLM 0.31.0": receipt.get("vllm_version") == "0.31.0",
    "vLLM commit db9527a4": receipt.get("vllm_commit") == "db9527a46873454610df6dbedf79a36d6bf1a7f6",
    "base image pinned": receipt.get("base_image") == base,
}
bad = [k for k, ok in checks.items() if not ok]
if bad:
    sys.exit(f"build record fails: {bad}")
print("build record checks pass:", ", ".join(checks))
PY
log_job "image ${IMAGE} for ${SHORT}: provenance and receipt checked against the pins"
echo "$IMAGE"
