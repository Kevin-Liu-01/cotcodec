#!/usr/bin/env bash
# am5-ablated-cost-v2: after the image build job has ended (am5r-job-state.sh), print the
# image id it built, and nothing else on stdout (one line, sha256:<64 hex>), after checking the
# latest submitted attempt's record (the rebuild's, overlay-build-vllm-<short>-r2, once submitted)
# against the pins: provenance PASS for this commit and capsule; a receipt that names the image,
# the commit, the capsule, vLLM 0.31.0 at commit db9527a4 and the pinned base image. A failed
# build is rebuilt once from the same capsule (am5r-build.sh ... rebuild; registration section 8);
# a second failure stops the run before any GPU job. Reads records only; it runs no repository
# code.
# Usage: IMAGE=$(bash ops/am5r/am5r-image.sh dev|reg <commit short id>)
set -Eeuo pipefail
source "$(dirname "$0")/am5r-env.sh" "${1:?mode}"
SHORT="${2:?commit short id}"
B=$(build_root "$SHORT")
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
log_job "image ${IMAGE} for ${SHORT} from $(basename "$B"): provenance and receipt checked against the pins"
echo "$IMAGE"
