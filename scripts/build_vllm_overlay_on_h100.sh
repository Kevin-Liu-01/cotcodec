#!/usr/bin/env bash
# Build the discovery-only vLLM serving overlay (infra/research/Dockerfile.vllm-overlay)
# from a retained source capsule, inside a Slurm allocation, with no network and no pull.
# The base is one of two allowlisted vLLM v0.31.0 images, pinned by manifest digest
# and asserted by local image ID before the build. Writes a build receipt.
set -Eeuo pipefail
umask 077

: "${SLURM_JOB_ID:?Run this build through Slurm}"
: "${COTCODEC_SOURCE_ARCHIVE:?Set the retained source archive path}"
: "${COTCODEC_SOURCE_RECEIPT:?Set the retained source receipt path}"
: "${COTCODEC_SOURCE_EXTRACTOR:?Set the retained source extractor path}"
: "${COTCODEC_SOURCE_EXTRACTOR_SHA256:?Set the retained source extractor SHA-256}"
: "${COTCODEC_SOURCE_BUILDER_SHA256:?Set the retained vLLM overlay builder SHA-256}"
: "${COTCODEC_SOURCE_SHA256:?Set the source archive SHA-256}"
: "${COTCODEC_GIT_SHA:?Set the embedded source revision}"
: "${COTCODEC_GIT_TREE:?Set the embedded source tree}"
: "${COTCODEC_BUILD_ROOT:?Set persistent build artifact storage}"
variant="${COTCODEC_VLLM_VARIANT:-cu129}"

vllm_version="0.31.0"
vllm_commit="db9527a46873454610df6dbedf79a36d6bf1a7f6"
case "${variant}" in
  cu129)
    base_ref="docker.io/vllm/vllm-openai@sha256:b18abb2df97b8f798e81862bd93f872ea18613372e2c3adc0cc2ac21e66ac12f"
    base_id="sha256:423783aac4fefebfe6b67d6fc2810b88a1d4dc08ed8bba587c80b0d8973e0b8b"
    ;;
  cu130)
    base_ref="docker.io/vllm/vllm-openai@sha256:a4a4c0437bf7240089da5f08aa370c4aee17ae5290f7a3b468825ee26c4c3a6b"
    base_id="sha256:c76d0e2225a4b1cb1e2109ace39639f55e714abd1a7a427acc8b0bbd7f6a83b3"
    ;;
  *)
    echo "COTCODEC_VLLM_VARIANT must be cu129 or cu130" >&2
    exit 2
    ;;
esac

if [[ ! "${COTCODEC_SOURCE_SHA256}" =~ ^[0-9a-f]{64}$ \
  || ! "${COTCODEC_SOURCE_EXTRACTOR_SHA256}" =~ ^[0-9a-f]{64}$ \
  || ! "${COTCODEC_SOURCE_BUILDER_SHA256}" =~ ^[0-9a-f]{64}$ \
  || ! "${COTCODEC_GIT_SHA}" =~ ^[0-9a-f]{40}$ \
  || ! "${COTCODEC_GIT_TREE}" =~ ^[0-9a-f]{40}$ ]]; then
  echo "invalid vLLM overlay provenance digest" >&2
  exit 2
fi
if [[ ! -f "${COTCODEC_SOURCE_EXTRACTOR}" || -L "${COTCODEC_SOURCE_EXTRACTOR}" \
  || ! -f "$0" || -L "$0" ]]; then
  echo "overlay builder and extractor must be regular non-symlink files" >&2
  exit 2
fi
actual_builder="$(sha256sum "$0" | cut -d' ' -f1)"
actual_extractor="$(sha256sum "${COTCODEC_SOURCE_EXTRACTOR}" | cut -d' ' -f1)"
if [[ "${actual_builder}" != "${COTCODEC_SOURCE_BUILDER_SHA256}" \
  || "${actual_extractor}" != "${COTCODEC_SOURCE_EXTRACTOR_SHA256}" ]]; then
  echo "overlay builder or extractor digest mismatch" >&2
  exit 2
fi
if [[ ! "${CUDA_VISIBLE_DEVICES:-}" =~ ^[0-7](,[0-7])*$ ]] \
  || nvidia-smi -i "${CUDA_VISIBLE_DEVICES}" \
    --query-gpu=name --format=csv,noheader | grep -qv H100; then
  echo "vLLM overlay build requires a Slurm-owned H100 allocation" >&2
  exit 2
fi

actual_source="$(sha256sum "${COTCODEC_SOURCE_ARCHIVE}" | cut -d' ' -f1)"
actual_base="$(docker image inspect --format '{{.Id}}' "${base_ref}")"
base_commit="$(docker image inspect --format \
  '{{index .Config.Labels "ai.vllm.build.commit"}}' "${base_ref}")"
if [[ "${actual_source}" != "${COTCODEC_SOURCE_SHA256}" \
  || "${actual_base}" != "${base_id}" \
  || "${base_commit}" != "${vllm_commit}" ]]; then
  echo "source archive or vLLM base image provenance mismatch" >&2
  exit 2
fi

if [[ -e "${COTCODEC_BUILD_ROOT}" || -L "${COTCODEC_BUILD_ROOT}" ]]; then
  echo "refusing to reuse vLLM overlay build root" >&2
  exit 2
fi
mkdir -m 0700 "${COTCODEC_BUILD_ROOT}"
context="$(mktemp -d "${COTCODEC_BUILD_ROOT}/context.${SLURM_JOB_ID}.XXXXXX")"
extractor_snapshot="${COTCODEC_BUILD_ROOT}/source-extractor.py"
cp --reflink=never --no-preserve=mode,ownership,timestamps \
  "${COTCODEC_SOURCE_EXTRACTOR}" "${extractor_snapshot}"
chmod 0500 "${extractor_snapshot}"
if [[ -L "${extractor_snapshot}" \
  || "$(sha256sum "${extractor_snapshot}" | cut -d' ' -f1)" \
    != "${COTCODEC_SOURCE_EXTRACTOR_SHA256}" ]]; then
  echo "private source extractor snapshot drifted" >&2
  exit 2
fi
python3 "${extractor_snapshot}" \
  --archive "${COTCODEC_SOURCE_ARCHIVE}" \
  --receipt "${COTCODEC_SOURCE_RECEIPT}" \
  --output-dir "${context}" \
  --expected-archive-sha256 "${COTCODEC_SOURCE_SHA256}" \
  --expected-git-sha "${COTCODEC_GIT_SHA}" \
  --expected-git-tree "${COTCODEC_GIT_TREE}" \
  >"${COTCODEC_BUILD_ROOT}/source-validation.json"
chmod -R a+rX "${context}"

overlay_tag="cotcodec-vllm:${COTCODEC_SOURCE_SHA256:0:8}-${variant}-overlay"
docker build \
  --pull=false \
  --network=none \
  --progress=plain \
  --build-arg "VLLM_BASE_IMAGE=${base_ref}" \
  --build-arg "BASE_IMAGE_ID=${base_id}" \
  --build-arg "GIT_SHA=${COTCODEC_GIT_SHA}" \
  --build-arg "GIT_TREE=${COTCODEC_GIT_TREE}" \
  --build-arg "SOURCE_TREE_SHA256=${COTCODEC_SOURCE_SHA256}" \
  --build-arg "VLLM_VERSION=${vllm_version}" \
  --build-arg "VLLM_COMMIT=${vllm_commit}" \
  -f "${context}/infra/research/Dockerfile.vllm-overlay" \
  -t "${overlay_tag}" \
  "${context}" >"${COTCODEC_BUILD_ROOT}/vllm-overlay.log" 2>&1

docker image inspect "${overlay_tag}" >"${COTCODEC_BUILD_ROOT}/image-inspect.json"
overlay_id="$(docker image inspect --format '{{.Id}}' "${overlay_tag}")"
printf '%s\n' "${overlay_id}" >"${COTCODEC_BUILD_ROOT}/image-id.txt"

label() {
  docker image inspect --format "{{index .Config.Labels \"$1\"}}" "${overlay_id}"
}
entrypoint="$(docker image inspect --format '{{json .Config.Entrypoint}}' "${overlay_id}")"
workdir="$(docker image inspect --format '{{.Config.WorkingDir}}' "${overlay_id}")"
if [[ "$(label org.opencontainers.image.revision)" != "${COTCODEC_GIT_SHA}" \
  || "$(label org.opencontainers.image.source-tree-sha256)" != "${COTCODEC_SOURCE_SHA256}" \
  || "$(label org.opencontainers.image.cotcodec-base-image-id)" != "${base_id}" \
  || ( "${entrypoint}" != "null" && "${entrypoint}" != "[]" ) \
  || "${workdir}" != "/workspace/cotcodec" ]]; then
  echo "vLLM overlay labels, entrypoint or workdir are wrong" >&2
  exit 2
fi

# CPU-only post-build checks in the lane's container hardening (no GPU, no network).
docker run --rm --network none --read-only --tmpfs /tmp:rw,nosuid,nodev,size=1g \
  --cap-drop ALL --security-opt no-new-privileges --user "$(id -u):$(id -g)" \
  --env COTCODEC_GIT_SHA="${COTCODEC_GIT_SHA}" \
  --env COTCODEC_SOURCE_SHA256="${COTCODEC_SOURCE_SHA256}" \
  "${overlay_id}" python scripts/verify_compute_provenance.py \
  >"${COTCODEC_BUILD_ROOT}/provenance-verification.json"
docker run --rm --network none --read-only --tmpfs /tmp:rw,nosuid,nodev,size=1g \
  --cap-drop ALL --security-opt no-new-privileges --user "$(id -u):$(id -g)" \
  "${overlay_id}" python scripts/run_vllm_throughput_probe.py plan --job a \
  >"${COTCODEC_BUILD_ROOT}/plan-job-a.json"
docker run --rm --network none --read-only --tmpfs /tmp:rw,nosuid,nodev,size=1g \
  --cap-drop ALL --security-opt no-new-privileges --user "$(id -u):$(id -g)" \
  --env HOME=/tmp/home \
  "${overlay_id}" python scripts/run_vllm_throughput_probe.py vllm-args-doctor \
  >"${COTCODEC_BUILD_ROOT}/vllm-args-doctor.json"
docker run --rm --network none --read-only --tmpfs /tmp:rw,nosuid,nodev,size=1g \
  --cap-drop ALL --security-opt no-new-privileges --user "$(id -u):$(id -g)" \
  "${overlay_id}" cat /etc/cotcodec-vllm-overlay-fixups.json \
  >"${COTCODEC_BUILD_ROOT}/vllm-overlay-fixups.json"

python3 - "${COTCODEC_BUILD_ROOT}" "${overlay_id}" "${overlay_tag}" "${base_ref}" "${base_id}" \
  "${variant}" "${vllm_version}" "${vllm_commit}" <<'PY'
import hashlib
import json
import os
import pathlib
import sys
from datetime import datetime, timezone

root = pathlib.Path(sys.argv[1])


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


receipt = {
    "schema_version": 1,
    "kind": "vllm-overlay-build",
    "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "slurm_job_id": os.environ["SLURM_JOB_ID"],
    "overlay_image_id": sys.argv[2],
    "overlay_tag": sys.argv[3],
    "base_image": sys.argv[4],
    "base_image_id": sys.argv[5],
    "variant": sys.argv[6],
    "vllm_version": sys.argv[7],
    "vllm_commit": sys.argv[8],
    "git_sha": os.environ["COTCODEC_GIT_SHA"],
    "git_tree": os.environ["COTCODEC_GIT_TREE"],
    "source_sha256": os.environ["COTCODEC_SOURCE_SHA256"],
    "builder_sha256": os.environ["COTCODEC_SOURCE_BUILDER_SHA256"],
    "extractor_sha256": os.environ["COTCODEC_SOURCE_EXTRACTOR_SHA256"],
    "overlay_fixups": json.loads((root / "vllm-overlay-fixups.json").read_text()),
    "artifacts": {
        name: digest(root / name)
        for name in (
            "image-inspect.json",
            "image-id.txt",
            "source-validation.json",
            "provenance-verification.json",
            "plan-job-a.json",
            "vllm-overlay-fixups.json",
            "vllm-args-doctor.json",
        )
    },
}
(root / "build-receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
print(json.dumps({"overlay_image_id": receipt["overlay_image_id"], "status": "PASS"}))
PY
