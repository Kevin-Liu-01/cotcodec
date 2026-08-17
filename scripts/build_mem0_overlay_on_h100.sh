#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

: "${SLURM_JOB_ID:?Run this build through Slurm}"
: "${COTCODEC_SOURCE_ARCHIVE:?Set the retained source archive path}"
: "${COTCODEC_SOURCE_SHA256:?Set the source archive SHA-256}"
: "${COTCODEC_GIT_SHA:?Set the embedded source revision}"
: "${COTCODEC_BASE_IMAGE_TAG:?Set the verified local base tag}"
: "${COTCODEC_BASE_IMAGE_ID:?Set the verified local base image ID}"
: "${COTCODEC_MEM0_WHEELHOUSE:?Set the locked Mem0 wheelhouse path}"
: "${COTCODEC_MEM0_WHEELHOUSE_SHA256:?Set the wheelhouse manifest SHA-256}"
: "${COTCODEC_BUILD_ROOT:?Set persistent build artifact storage}"

if [[ ! "${COTCODEC_SOURCE_SHA256}" =~ ^[0-9a-f]{64}$ \
  || ! "${COTCODEC_MEM0_WHEELHOUSE_SHA256}" =~ ^[0-9a-f]{64}$ \
  || ! "${COTCODEC_GIT_SHA}" =~ ^[0-9a-f]{40}$ \
  || ! "${COTCODEC_BASE_IMAGE_ID}" =~ ^sha256:[0-9a-f]{64}$ ]]; then
  echo "invalid build provenance digest" >&2
  exit 2
fi
if [[ ! "${CUDA_VISIBLE_DEVICES:-}" =~ ^[0-7](,[0-7])*$ ]] \
  || nvidia-smi -i "${CUDA_VISIBLE_DEVICES}" \
    --query-gpu=name --format=csv,noheader | grep -qv H100; then
  echo "build requires a Slurm-owned H100 allocation" >&2
  exit 2
fi

actual_source="$(sha256sum "${COTCODEC_SOURCE_ARCHIVE}" | cut -d' ' -f1)"
actual_base="$(docker image inspect --format '{{.Id}}' "${COTCODEC_BASE_IMAGE_TAG}")"
actual_wheelhouse="$({
  cd "${COTCODEC_MEM0_WHEELHOUSE}"
  sha256sum -- ./*.whl \
    | sed 's#  \./#  #' \
    | LC_ALL=C sort \
    | sha256sum \
    | cut -d' ' -f1
})"
if [[ "${actual_source}" != "${COTCODEC_SOURCE_SHA256}" \
  || "${actual_base}" != "${COTCODEC_BASE_IMAGE_ID}" \
  || "${actual_wheelhouse}" != "${COTCODEC_MEM0_WHEELHOUSE_SHA256}" ]]; then
  echo "source, base image, or wheelhouse provenance mismatch" >&2
  exit 2
fi

mkdir -p "${COTCODEC_BUILD_ROOT}"
context="${COTCODEC_BUILD_ROOT}/context"
if [[ ! -d "${context}" ]]; then
  mkdir "${context}"
  tar -xzf "${COTCODEC_SOURCE_ARCHIVE}" -C "${context}"
fi
chmod -R a+rX "${context}"

source_tag="cotcodec-research:${COTCODEC_SOURCE_SHA256:0:8}-architecture"
final_tag="cotcodec-research:${COTCODEC_SOURCE_SHA256:0:8}-memory-mem0"
container_name="cotcodec-mem0-install-${SLURM_JOB_ID}"
cleanup() {
  if docker container inspect "${container_name}" >/dev/null 2>&1; then
    docker rm -f "${container_name}" >/dev/null
  fi
}
trap cleanup EXIT

docker build \
  --network=none \
  --progress=plain \
  --build-arg "BASE_IMAGE=${COTCODEC_BASE_IMAGE_TAG}" \
  --build-arg "BASE_IMAGE_ID=${COTCODEC_BASE_IMAGE_ID}" \
  --build-arg "GIT_SHA=${COTCODEC_GIT_SHA}" \
  --build-arg "SOURCE_TREE_SHA256=${COTCODEC_SOURCE_SHA256}" \
  --build-arg UV_EXTRA=architecture \
  --build-arg INCLUDE_DEV=false \
  -f "${context}/infra/research/Dockerfile.source-overlay" \
  -t "${source_tag}" \
  "${context}" >"${COTCODEC_BUILD_ROOT}/source-overlay.log" 2>&1

docker run \
  --name "${container_name}" \
  --network none \
  --entrypoint /bin/sh \
  --volume "${COTCODEC_MEM0_WHEELHOUSE}:/wheel:ro" \
  "${source_tag}" \
  -lc 'uv pip install --python /workspace/cotcodec/.venv/bin/python --no-deps /wheel/*.whl && /workspace/cotcodec/.venv/bin/python -c "import importlib.metadata as m; print(m.version(\"mem0ai\"), m.version(\"qdrant-client\"))"' \
  >"${COTCODEC_BUILD_ROOT}/mem0-install.log" 2>&1

docker commit \
  --change "LABEL org.opencontainers.image.cotcodec-wheelhouse-sha256=${COTCODEC_MEM0_WHEELHOUSE_SHA256}" \
  --change "LABEL org.opencontainers.image.cotcodec-runtime-profile=architecture-memory-mem0-source-overlay" \
  "${container_name}" "${final_tag}" >"${COTCODEC_BUILD_ROOT}/final-image-id.txt"
docker rm "${container_name}" >"${COTCODEC_BUILD_ROOT}/install-container-removed.txt"
trap - EXIT

docker image inspect "${final_tag}" >"${COTCODEC_BUILD_ROOT}/image-inspect.json"
docker image inspect --format '{{.Id}}' "${final_tag}"
