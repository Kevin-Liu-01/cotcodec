#!/usr/bin/env bash
#SBATCH --job-name=cotcodec-build-llamacpp
#SBATCH --partition=research
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=64
#SBATCH --mem=128G
#SBATCH --time=02:00:00
#SBATCH --no-requeue
#SBATCH --output=/home/kevin/cotcodec-runs/builds/slurm-%x-%j.out
#
# Build the stock llama.cpp CUDA base image (infra/research/Dockerfile.llamacpp) for LM1 (D125).
#
# CPU only: compiling CUDA code needs nvcc, not a GPU, so this job requests no GRES, refuses to
# start when Slurm or the environment shows a GPU, and runs no container with a GPU. The image is
# exercised on GPUs only by the lane's smoke test.
#
# Inputs are pinned here and checked before anything is built:
#   - the llama.cpp source: `git archive --prefix=llama.cpp/` of upstream commit 620d2225 (release
#     b11669 = v0.7.0), by SHA-256;
#   - the two NVIDIA CUDA 12.8.1 Ubuntu 24.04 bases, by linux/amd64 manifest digest. They are
#     pulled anonymously by digest if absent, and Docker's resolved image IDs are recorded;
#   - the Dockerfile, from an exported source tree of a cotcodec commit (`git archive`).
# The build uses host networking for apt only (the bridge network has no DNS on this host; the
# llama.cpp configuration downloads nothing). The image is tagged cotcodec-llamacpp:b11669-cu128,
# pushed to the host's local registry (127.0.0.1:5000) for a repository digest, checked without a
# GPU or a network, and described by a build receipt in the build root.
#
# Inputs (sbatch --export):
#   COTCODEC_BUILD_SOURCE      exported cotcodec tree under /home/kevin/cotcodec-runs (read-only)
#   COTCODEC_LLAMACPP_SOURCE   the llama.cpp source archive (tar)
#   COTCODEC_BUILD_ROOT        new directory for the build records (must not exist)
set -Eeuo pipefail
umask 022
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

: "${SLURM_JOB_ID:?Run this build through sbatch}"
: "${COTCODEC_BUILD_SOURCE:?Set the exported source tree}"
: "${COTCODEC_LLAMACPP_SOURCE:?Set the llama.cpp source archive}"
: "${COTCODEC_BUILD_ROOT:?Set a new build root}"

llama_commit="620d2225cc436ab0b001e3200e590e3b286ef9ab"
llama_tree="6868e0a538a05e9a253a0b86ccb71b4e06a64684"
llama_release="b11669"
llama_stable_tag="v0.7.0"
llama_source_sha256="622f13ebf8a733003c9ae70ffe96a55c5d09bf2e0e6212ed212efcaca71bf066"
devel_ref="docker.io/nvidia/cuda@sha256:4b9ed5fa8361736996499f64ecebf25d4ec37ff56e4d11323ccde10aa36e0c43"
runtime_ref="docker.io/nvidia/cuda@sha256:828c4d878adcaa4265d80c95d8ec877149b49bb2419a4cf3bb6aa889bbb7ca2e"
devel_tag="nvidia/cuda:12.8.1-devel-ubuntu24.04"
runtime_tag="nvidia/cuda:12.8.1-runtime-ubuntu24.04"
image_tag="cotcodec-llamacpp:${llama_release}-cu128"
registry="127.0.0.1:5000"

fail() {
  echo "build-llamacpp-image: $*" >&2
  exit 2
}

# --- No GPU, by construction and by assertion ---------------------------------------------
for name in SLURM_JOB_GPUS SLURM_STEP_GPUS SLURM_GPUS SLURM_GPUS_ON_NODE CUDA_VISIBLE_DEVICES \
  GPU_DEVICE_ORDINAL; do
  [[ -z "${!name:-}" ]] || fail "${name} is set; the image build must hold no GPU"
done
job_tres="$(scontrol show job "${SLURM_JOB_ID}" \
  | tr ' ' '\n' | grep -E '^(TRES|TresPerNode|TresPerJob|TresPerTask|TresPerSocket)=' || true)"
if grep -qiE 'gres/gpu|gpu:' <<<"${job_tres}"; then
  fail "this job was allocated a GPU; refusing to build"
fi
default_runtime="$(docker info --format '{{.DefaultRuntime}}')"
[[ "${default_runtime}" == "runc" ]] || fail "Docker default runtime is ${default_runtime}, not runc"

# --- Inputs -------------------------------------------------------------------------------
[[ "${COTCODEC_BUILD_SOURCE}" =~ ^/home/kevin/cotcodec-runs/[A-Za-z0-9._/-]+$ \
  && "${COTCODEC_BUILD_SOURCE}" != *..* && -d "${COTCODEC_BUILD_SOURCE}" ]] \
  || fail "source tree must be an existing directory under /home/kevin/cotcodec-runs"
dockerfile="${COTCODEC_BUILD_SOURCE}/infra/research/Dockerfile.llamacpp"
[[ -f "${dockerfile}" && ! -L "${dockerfile}" ]] || fail "source tree lacks Dockerfile.llamacpp"
[[ -f "${COTCODEC_LLAMACPP_SOURCE}" && ! -L "${COTCODEC_LLAMACPP_SOURCE}" ]] \
  || fail "llama.cpp source archive is missing or a symlink"
[[ "$(sha256sum "${COTCODEC_LLAMACPP_SOURCE}" | cut -d' ' -f1)" == "${llama_source_sha256}" ]] \
  || fail "llama.cpp source archive SHA-256 differs from the pin"
[[ ! -e "${COTCODEC_BUILD_ROOT}" && ! -L "${COTCODEC_BUILD_ROOT}" ]] \
  || fail "refusing to reuse build root ${COTCODEC_BUILD_ROOT}"
mkdir -m 0755 -p "${COTCODEC_BUILD_ROOT}"
source_git_sha="$(cat "${COTCODEC_BUILD_SOURCE}/.git_sha" 2>/dev/null || echo unknown)"
[[ "${source_git_sha}" =~ ^[0-9a-f]{40}$ ]] || fail "source tree has no .git_sha"
builder_sha256="$(sha256sum "$0" | cut -d' ' -f1)"
dockerfile_sha256="$(sha256sum "${dockerfile}" | cut -d' ' -f1)"
build_jobs="${SLURM_CPUS_PER_TASK:-32}"
[[ "${build_jobs}" =~ ^[1-9][0-9]*$ ]] || fail "unusable SLURM_CPUS_PER_TASK"

# --- Bases, by digest -----------------------------------------------------------------------
for ref in "${devel_ref}" "${runtime_ref}"; do
  if ! docker image inspect "${ref}" >/dev/null 2>&1; then
    docker pull "${ref}" >>"${COTCODEC_BUILD_ROOT}/docker-pull.log" 2>&1 \
      || fail "could not pull ${ref}"
  fi
done
devel_id="$(docker image inspect --format '{{.Id}}' "${devel_ref}")"
runtime_id="$(docker image inspect --format '{{.Id}}' "${runtime_ref}")"
docker image inspect "${devel_ref}" >"${COTCODEC_BUILD_ROOT}/base-devel-inspect.json"
docker image inspect "${runtime_ref}" >"${COTCODEC_BUILD_ROOT}/base-runtime-inspect.json"
for pair in "${devel_ref}|CUDA_VERSION=12.8.1" "${runtime_ref}|CUDA_VERSION=12.8.1"; do
  docker image inspect --format '{{json .Config.Env}}' "${pair%%|*}" | grep -q "${pair#*|}" \
    || fail "${pair%%|*} is not CUDA 12.8.1"
done

# --- Build ---------------------------------------------------------------------------------
context="${COTCODEC_BUILD_ROOT}/context"
mkdir -m 0755 "${context}"
cp --reflink=never --no-preserve=mode,ownership,timestamps "${dockerfile}" "${context}/Dockerfile"
cp --reflink=never --no-preserve=mode,ownership,timestamps "${COTCODEC_LLAMACPP_SOURCE}" \
  "${context}/llama.cpp-source.tar"
chmod -R a+rX "${context}"
started_at="$(date -u +%FT%TZ)"
docker build \
  --pull=false \
  --network=host \
  --progress=plain \
  --build-arg "CUDA_DEVEL_IMAGE=${devel_ref}" \
  --build-arg "CUDA_RUNTIME_IMAGE=${runtime_ref}" \
  --build-arg "LLAMA_CPP_COMMIT=${llama_commit}" \
  --build-arg "LLAMA_CPP_COMMIT_SHORT=${llama_commit:0:8}" \
  --build-arg "LLAMA_CPP_BUILD_NUMBER=${llama_release#b}" \
  --build-arg "LLAMA_CPP_SOURCE_SHA256=${llama_source_sha256}" \
  --build-arg "CUDA_ARCHITECTURES=90" \
  --build-arg "BUILD_JOBS=${build_jobs}" \
  --build-arg "COTCODEC_GIT_SHA=${source_git_sha}" \
  -f "${context}/Dockerfile" \
  -t "${image_tag}" \
  "${context}" >"${COTCODEC_BUILD_ROOT}/docker-build.log" 2>&1
finished_at="$(date -u +%FT%TZ)"
rm -f "${context}/llama.cpp-source.tar"

image_id="$(docker image inspect --format '{{.Id}}' "${image_tag}")"
printf '%s\n' "${image_id}" >"${COTCODEC_BUILD_ROOT}/image-id.txt"
docker image inspect "${image_tag}" >"${COTCODEC_BUILD_ROOT}/image-inspect.json"
label() {
  docker image inspect --format "{{index .Config.Labels \"$1\"}}" "${image_id}"
}
[[ "$(label org.opencontainers.image.revision)" == "${llama_commit}" \
  && "$(label org.opencontainers.image.cotcodec-llama-cpp-source-sha256)" == "${llama_source_sha256}" \
  && "$(label org.opencontainers.image.cotcodec-cuda-runtime-image)" == "${runtime_ref}" \
  && "$(label org.opencontainers.image.cotcodec-dockerfile-git-sha)" == "${source_git_sha}" ]] \
  || fail "image labels do not match the pins"

# --- Checks without a GPU or a network ------------------------------------------------------
check_run() {
  docker run --rm --network none --read-only --tmpfs /tmp:rw,nosuid,nodev,size=1g \
    --cap-drop ALL --security-opt no-new-privileges --user "$(id -u):$(id -g)" \
    --entrypoint /bin/sh "${image_id}" -c "$1"
}
check_run 'for t in llama-server llama-cli llama-bench llama-perplexity; do echo "== $t"; "$t" --version 2>&1; done' \
  >"${COTCODEC_BUILD_ROOT}/versions.txt"
check_run 'cat /opt/llama.cpp/MANIFEST.sha256 && cd /opt/llama.cpp && sha256sum -c MANIFEST.sha256 >/dev/null && echo MANIFEST_OK' \
  >"${COTCODEC_BUILD_ROOT}/manifest.txt"
check_run 'for f in /opt/llama.cpp/llama-* /opt/llama.cpp/*.so; do echo "== $f"; ldd "$f" | grep -E "not found" || true; done' \
  >"${COTCODEC_BUILD_ROOT}/ldd-missing.txt"
check_run 'python3 -c "import sys, yaml; print(sys.version.split()[0], yaml.__version__)"; cat /etc/os-release | grep -E "^(VERSION_ID|PRETTY_NAME)="; echo "CUDA_VERSION=${CUDA_VERSION}"; ls /opt/llama.cpp' \
  >"${COTCODEC_BUILD_ROOT}/runtime-env.txt"
grep -q MANIFEST_OK "${COTCODEC_BUILD_ROOT}/manifest.txt" || fail "binary manifest does not verify"
# libcuda.so.1 comes from the driver at run time (NVIDIA container toolkit); anything else missing
# is a broken image.
if grep "not found" "${COTCODEC_BUILD_ROOT}/ldd-missing.txt" | grep -qv "libcuda.so.1"; then
  fail "a shared library other than the driver's libcuda.so.1 is missing"
fi
# Each tool prints "version: ... (build 11669, commit 620d2225)".
n_versions="$(grep -c "(build ${llama_release#b}, commit ${llama_commit:0:8})" "${COTCODEC_BUILD_ROOT}/versions.txt" || true)"
[[ "${n_versions}" == 4 ]] || fail "expected 4 tools reporting build ${llama_release}, found ${n_versions}"

# --- Local registry, for a repository digest ------------------------------------------------
registry_ref="${registry}/${image_tag}"
repo_digest=""
if docker tag "${image_tag}" "${registry_ref}" \
  && docker push "${registry_ref}" >"${COTCODEC_BUILD_ROOT}/docker-push.log" 2>&1; then
  repo_digest="$(docker image inspect --format '{{range .RepoDigests}}{{println .}}{{end}}' "${image_id}" \
    | grep "^${registry}/cotcodec-llamacpp@" | head -1)"
fi

python3 - "${COTCODEC_BUILD_ROOT}" <<PY
import hashlib
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


receipt = {
    "schema_version": 1,
    "kind": "llamacpp-base-build",
    "slurm_job_id": "${SLURM_JOB_ID}",
    "started_at": "${started_at}",
    "finished_at": "${finished_at}",
    "image_tag": "${image_tag}",
    "image_id": "${image_id}",
    "registry_repo_digest": "${repo_digest}" or None,
    "llama_cpp": {
        "repository": "https://github.com/ggml-org/llama.cpp",
        "release": "${llama_release}",
        "stable_tag": "${llama_stable_tag}",
        "commit": "${llama_commit}",
        "tree": "${llama_tree}",
        "source_archive_sha256": "${llama_source_sha256}",
        "patches": [],
        "cuda_architectures": "90",
        "tools": ["llama-server", "llama-cli", "llama-bench", "llama-perplexity"],
    },
    "cuda_devel_image": "${devel_ref}",
    "cuda_devel_image_tag": "${devel_tag}",
    "cuda_devel_image_id": "${devel_id}",
    "cuda_runtime_image": "${runtime_ref}",
    "cuda_runtime_image_tag": "${runtime_tag}",
    "cuda_runtime_image_id": "${runtime_id}",
    "cotcodec_git_sha": "${source_git_sha}",
    "dockerfile_sha256": "${dockerfile_sha256}",
    "builder_sha256": "${builder_sha256}",
    "build_jobs": int("${build_jobs}"),
    "gres_requested": "none",
    "job_tres": "$(tr '\n' ' ' <<<"${job_tres}")".strip(),
    "network_during_build": "host (apt only)",
    "artifacts": {
        name: digest(root / name)
        for name in (
            "image-inspect.json",
            "image-id.txt",
            "versions.txt",
            "manifest.txt",
            "ldd-missing.txt",
            "runtime-env.txt",
            "base-devel-inspect.json",
            "base-runtime-inspect.json",
            "docker-build.log",
        )
    },
}
(root / "build-receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
print(json.dumps({"image_id": receipt["image_id"], "repo_digest": receipt["registry_repo_digest"],
                  "status": "PASS"}))
PY
