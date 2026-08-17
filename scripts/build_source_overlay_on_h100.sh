#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

: "${SLURM_JOB_ID:?Run this build through Slurm}"
: "${COTCODEC_SOURCE_ARCHIVE:?Set the retained source archive path}"
: "${COTCODEC_SOURCE_RECEIPT:?Set the retained source receipt path}"
: "${COTCODEC_SOURCE_EXTRACTOR:?Set the retained source extractor path}"
: "${COTCODEC_SOURCE_EXTRACTOR_SHA256:?Set the retained source extractor SHA-256}"
: "${COTCODEC_SOURCE_BUILDER_SHA256:?Set the retained source builder SHA-256}"
: "${COTCODEC_SOURCE_SHA256:?Set the source archive SHA-256}"
: "${COTCODEC_GIT_SHA:?Set the embedded source revision}"
: "${COTCODEC_GIT_TREE:?Set the embedded source tree}"
: "${COTCODEC_BASE_IMAGE_TAG:?Set the verified local base tag}"
: "${COTCODEC_BASE_IMAGE_ID:?Set the verified local base image ID}"
: "${COTCODEC_BUILD_ROOT:?Set persistent build artifact storage}"

if [[ ! "${COTCODEC_SOURCE_SHA256}" =~ ^[0-9a-f]{64}$ \
  || ! "${COTCODEC_SOURCE_EXTRACTOR_SHA256}" =~ ^[0-9a-f]{64}$ \
  || ! "${COTCODEC_SOURCE_BUILDER_SHA256}" =~ ^[0-9a-f]{64}$ \
  || ! "${COTCODEC_GIT_SHA}" =~ ^[0-9a-f]{40}$ \
  || ! "${COTCODEC_GIT_TREE}" =~ ^[0-9a-f]{40}$ \
  || ! "${COTCODEC_BASE_IMAGE_TAG}" =~ ^[^[:space:]@]+@sha256:[0-9a-f]{64}$ \
  || ! "${COTCODEC_BASE_IMAGE_ID}" =~ ^sha256:[0-9a-f]{64}$ ]]; then
  echo "invalid source-overlay provenance digest" >&2
  exit 2
fi
if [[ ! -f "${COTCODEC_SOURCE_EXTRACTOR}" || -L "${COTCODEC_SOURCE_EXTRACTOR}" \
  || ! -f "$0" || -L "$0" ]]; then
  echo "source builder and extractor must be regular non-symlink files" >&2
  exit 2
fi
actual_builder="$(sha256sum "$0" | cut -d' ' -f1)"
actual_extractor="$(sha256sum "${COTCODEC_SOURCE_EXTRACTOR}" | cut -d' ' -f1)"
if [[ "${actual_builder}" != "${COTCODEC_SOURCE_BUILDER_SHA256}" \
  || "${actual_extractor}" != "${COTCODEC_SOURCE_EXTRACTOR_SHA256}" ]]; then
  echo "source builder or extractor digest mismatch" >&2
  exit 2
fi
if [[ ! "${CUDA_VISIBLE_DEVICES:-}" =~ ^[0-7](,[0-7])*$ ]] \
  || nvidia-smi -i "${CUDA_VISIBLE_DEVICES}" \
    --query-gpu=name --format=csv,noheader | grep -qv H100; then
  echo "source-overlay build requires a Slurm-owned H100 allocation" >&2
  exit 2
fi

actual_source="$(sha256sum "${COTCODEC_SOURCE_ARCHIVE}" | cut -d' ' -f1)"
actual_base="$(docker image inspect --format '{{.Id}}' "${COTCODEC_BASE_IMAGE_TAG}")"
if [[ "${actual_source}" != "${COTCODEC_SOURCE_SHA256}" \
  || "${actual_base}" != "${COTCODEC_BASE_IMAGE_ID}" ]]; then
  echo "source archive or base image provenance mismatch" >&2
  exit 2
fi

if [[ -e "${COTCODEC_BUILD_ROOT}" || -L "${COTCODEC_BUILD_ROOT}" ]]; then
  echo "refusing to reuse source-overlay build root" >&2
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

source_tag="cotcodec-research:${COTCODEC_SOURCE_SHA256:0:8}-architecture-overlay"
docker build \
  --pull=false \
  --network=none \
  --progress=plain \
  --build-arg "BASE_IMAGE=${COTCODEC_BASE_IMAGE_TAG}" \
  --build-arg "BASE_IMAGE_ID=${COTCODEC_BASE_IMAGE_ID}" \
  --build-arg "GIT_SHA=${COTCODEC_GIT_SHA}" \
  --build-arg "GIT_TREE=${COTCODEC_GIT_TREE}" \
  --build-arg "SOURCE_TREE_SHA256=${COTCODEC_SOURCE_SHA256}" \
  --build-arg UV_EXTRA=architecture \
  --build-arg INCLUDE_DEV=false \
  -f "${context}/infra/research/Dockerfile.source-overlay" \
  -t "${source_tag}" \
  "${context}" >"${COTCODEC_BUILD_ROOT}/source-overlay.log" 2>&1

docker image inspect "${source_tag}" >"${COTCODEC_BUILD_ROOT}/image-inspect.json"
docker image inspect --format '{{.Id}}' "${source_tag}" \
  | tee "${COTCODEC_BUILD_ROOT}/image-id.txt"
