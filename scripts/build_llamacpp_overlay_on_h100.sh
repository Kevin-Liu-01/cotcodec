#!/usr/bin/env bash
# Build the discovery-only llama.cpp serving overlay (infra/research/Dockerfile.llamacpp-overlay)
# from a retained source capsule, inside a CPU-only Slurm allocation, with no network and no pull.
# Modeled on scripts/build_vllm_overlay_on_h100.sh, with one difference: the vLLM builder holds
# one H100 for its minute, while nothing here touches a GPU (the overlay only adds the cotcodec
# source and provenance), so this builder requests no GPU and refuses to run when one is visible.
# The base is the stock llama.cpp CUDA image built by build-llamacpp-image.sbatch, pinned by its
# local-registry manifest digest and asserted by local image ID before the build. Writes a build
# receipt.
set -Eeuo pipefail
umask 077

: "${SLURM_JOB_ID:?Run this build through Slurm}"
: "${COTCODEC_SOURCE_ARCHIVE:?Set the retained source archive path}"
: "${COTCODEC_SOURCE_RECEIPT:?Set the retained source receipt path}"
: "${COTCODEC_SOURCE_EXTRACTOR:?Set the retained source extractor path}"
: "${COTCODEC_SOURCE_EXTRACTOR_SHA256:?Set the retained source extractor SHA-256}"
: "${COTCODEC_SOURCE_BUILDER_SHA256:?Set the retained llama.cpp overlay builder SHA-256}"
: "${COTCODEC_SOURCE_SHA256:?Set the source archive SHA-256}"
: "${COTCODEC_GIT_SHA:?Set the embedded source revision}"
: "${COTCODEC_GIT_TREE:?Set the embedded source tree}"
: "${COTCODEC_BUILD_ROOT:?Set persistent build artifact storage}"

llama_release="b11669"
llama_commit="620d2225cc436ab0b001e3200e590e3b286ef9ab"
base_ref="127.0.0.1:5000/cotcodec-llamacpp@sha256:d445e09f9f0167cbce65be9fecd0f38c539b243ea321ee281ebeea259e904131"
base_id="sha256:fb8600d96560412d65ec9c269b555c8db6ed4bcfd86a3556658b1c108073e848"

if [[ ! "${COTCODEC_SOURCE_SHA256}" =~ ^[0-9a-f]{64}$ \
  || ! "${COTCODEC_SOURCE_EXTRACTOR_SHA256}" =~ ^[0-9a-f]{64}$ \
  || ! "${COTCODEC_SOURCE_BUILDER_SHA256}" =~ ^[0-9a-f]{64}$ \
  || ! "${COTCODEC_GIT_SHA}" =~ ^[0-9a-f]{40}$ \
  || ! "${COTCODEC_GIT_TREE}" =~ ^[0-9a-f]{40}$ ]]; then
  echo "invalid llama.cpp overlay provenance digest" >&2
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
for name in SLURM_JOB_GPUS SLURM_STEP_GPUS SLURM_GPUS SLURM_GPUS_ON_NODE CUDA_VISIBLE_DEVICES; do
  if [[ -n "${!name:-}" ]]; then
    echo "${name} is set; the llama.cpp overlay build must hold no GPU" >&2
    exit 2
  fi
done

actual_source="$(sha256sum "${COTCODEC_SOURCE_ARCHIVE}" | cut -d' ' -f1)"
actual_base="$(docker image inspect --format '{{.Id}}' "${base_ref}")"
base_commit="$(docker image inspect --format \
  '{{index .Config.Labels "org.opencontainers.image.cotcodec-llama-cpp-commit"}}' "${base_ref}")"
if [[ "${actual_source}" != "${COTCODEC_SOURCE_SHA256}" \
  || "${actual_base}" != "${base_id}" \
  || "${base_commit}" != "${llama_commit}" ]]; then
  echo "source archive or llama.cpp base image provenance mismatch" >&2
  exit 2
fi

if [[ -e "${COTCODEC_BUILD_ROOT}" || -L "${COTCODEC_BUILD_ROOT}" ]]; then
  echo "refusing to reuse llama.cpp overlay build root" >&2
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

overlay_tag="cotcodec-llamacpp:${COTCODEC_SOURCE_SHA256:0:8}-${llama_release}-overlay"
docker build \
  --pull=false \
  --network=none \
  --progress=plain \
  --build-arg "LLAMACPP_BASE_IMAGE=${base_ref}" \
  --build-arg "BASE_IMAGE_ID=${base_id}" \
  --build-arg "GIT_SHA=${COTCODEC_GIT_SHA}" \
  --build-arg "GIT_TREE=${COTCODEC_GIT_TREE}" \
  --build-arg "SOURCE_TREE_SHA256=${COTCODEC_SOURCE_SHA256}" \
  -f "${context}/infra/research/Dockerfile.llamacpp-overlay" \
  -t "${overlay_tag}" \
  "${context}" >"${COTCODEC_BUILD_ROOT}/llamacpp-overlay.log" 2>&1

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
  || "$(label org.opencontainers.image.cotcodec-llama-cpp-commit)" != "${llama_commit}" \
  || ( "${entrypoint}" != "null" && "${entrypoint}" != "[]" ) \
  || "${workdir}" != "/workspace/cotcodec" ]]; then
  echo "llama.cpp overlay labels, entrypoint or workdir are wrong" >&2
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
  "${overlay_id}" python scripts/run_lm1_smoke.py check-plan \
  --plan experiments/lm1/lm1-host-smoke-v1.json \
  >"${COTCODEC_BUILD_ROOT}/plan-check.json"
docker run --rm --network none --read-only --tmpfs /tmp:rw,nosuid,nodev,size=1g \
  --cap-drop ALL --security-opt no-new-privileges --user "$(id -u):$(id -g)" \
  "${overlay_id}" llama-server --version \
  >"${COTCODEC_BUILD_ROOT}/llama-server-version.txt" 2>&1
grep -q "(build ${llama_release#b}, commit ${llama_commit:0:8})" \
  "${COTCODEC_BUILD_ROOT}/llama-server-version.txt" || {
  echo "the overlay's llama-server is not build ${llama_release}" >&2
  exit 2
}

python3 - "${COTCODEC_BUILD_ROOT}" "${overlay_id}" "${overlay_tag}" "${base_ref}" "${base_id}" \
  "${llama_release}" "${llama_commit}" <<'PY'
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
    "kind": "llamacpp-overlay-build",
    "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "slurm_job_id": os.environ["SLURM_JOB_ID"],
    "overlay_image_id": sys.argv[2],
    "overlay_tag": sys.argv[3],
    "base_image": sys.argv[4],
    "base_image_id": sys.argv[5],
    "llama_cpp_release": sys.argv[6],
    "llama_cpp_commit": sys.argv[7],
    "git_sha": os.environ["COTCODEC_GIT_SHA"],
    "git_tree": os.environ["COTCODEC_GIT_TREE"],
    "source_sha256": os.environ["COTCODEC_SOURCE_SHA256"],
    "builder_sha256": os.environ["COTCODEC_SOURCE_BUILDER_SHA256"],
    "extractor_sha256": os.environ["COTCODEC_SOURCE_EXTRACTOR_SHA256"],
    "gpu": "none",
    "artifacts": {
        name: digest(root / name)
        for name in (
            "image-inspect.json",
            "image-id.txt",
            "source-validation.json",
            "provenance-verification.json",
            "plan-check.json",
            "llama-server-version.txt",
        )
    },
}
(root / "build-receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
print(json.dumps({"overlay_image_id": receipt["overlay_image_id"], "status": "PASS"}))
PY
