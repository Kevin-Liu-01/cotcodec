#!/usr/bin/env bash
#SBATCH --job-name=cotcodec-build-q1-gates
#SBATCH --partition=research
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=01:00:00
#SBATCH --output=/home/kevin/cotcodec-runs/builds/slurm-%x-%j.out

# Build the lane-ready Q1 gate image (infra/q1-gates/Dockerfile) from a clean,
# committed clone with host networking (PyPI), in the style of
# build-architecture-image.sbatch: the committed source is embedded and labelled
# with its revision and `git archive` SHA-256, the image is checked in a GPU-less
# container, pushed to the host's private local registry so jobs can pin its
# content digest, and a build receipt is written. CPU-only: no GPU is requested
# and no model runs. COTCODEC_REPO must name a clean clone that is not the shared
# operator checkout.
set -Eeuo pipefail
umask 022

: "${SLURM_JOB_ID:?Run this build through Slurm}"
: "${COTCODEC_REPO:?Set COTCODEC_REPO to a clean clone}"
registry="${COTCODEC_LOCAL_REGISTRY:-127.0.0.1:5000}"
repo="$(cd "${COTCODEC_REPO}" && pwd -P)"
if [[ "${repo}" == "/home/kevin/cotcodec" ]]; then
  echo "refusing to build from the shared operator checkout" >&2
  exit 2
fi
cd "${repo}"
if [[ -n "$(git status --porcelain --ignored)" ]]; then
  echo "checkout is dirty or holds ignored files; build from a fresh clone" >&2
  exit 2
fi
git_sha="$(git rev-parse HEAD)"
git_tree="$(git rev-parse 'HEAD^{tree}')"
source_sha="$(git archive --format=tar "${git_sha}" | sha256sum | cut -d' ' -f1)"
base_ref="127.0.0.1:5000/cotcodec-research@sha256:02965f3d696d4e516a7cd6d5c03434e9098139738748ae778ed967215db7be6d"
base_id="sha256:3804466639c13f132be4b0369de4d3395b9d5ea2d3dc100cd38884c75197fe29"
if [[ "$(docker image inspect --format '{{.Id}}' "${base_ref}")" != "${base_id}" ]]; then
  echo "base image digest does not resolve to the pinned image ID" >&2
  exit 2
fi
tag="cotcodec-q1-gates:${git_sha:0:8}"
build_root="/home/kevin/cotcodec-runs/builds/q1-gates-${git_sha:0:8}-${SLURM_JOB_ID}"
mkdir -m 0755 -p "${build_root}"

docker build \
  --pull=false \
  --network=host \
  --progress=plain \
  --build-arg "BASE_IMAGE=${base_ref}" \
  --build-arg "BASE_IMAGE_ID=${base_id}" \
  --build-arg "GIT_SHA=${git_sha}" \
  --build-arg "GIT_TREE=${git_tree}" \
  --build-arg "SOURCE_TREE_SHA256=${source_sha}" \
  -f infra/q1-gates/Dockerfile \
  -t "${tag}" \
  . >"${build_root}/docker-build.log" 2>&1

image_id="$(docker image inspect --format '{{.Id}}' "${tag}")"
label_git="$(docker image inspect --format \
  '{{index .Config.Labels "org.opencontainers.image.revision"}}' "${tag}")"
label_source="$(docker image inspect --format \
  '{{index .Config.Labels "org.opencontainers.image.source-tree-sha256"}}' "${tag}")"
if [[ "${label_git}" != "${git_sha}" || "${label_source}" != "${source_sha}" ]]; then
  echo "image labels do not match the clone's revision and source digest" >&2
  exit 2
fi
docker run --rm --network=none -e NVIDIA_VISIBLE_DEVICES=void --entrypoint bash "${tag}" -c \
  'test ! -e /dev/nvidiactl && cat /etc/cotcodec-provenance.json /opt/q1/SHA256SUMS && python -c "import importlib.metadata as m; print({p: m.version(p) for p in [\"torch\", \"triton\", \"pyarrow\", \"ninja\", \"python-dotenv\", \"tomli\", \"pydantic-settings\", \"pytest\"]})"' \
  >"${build_root}/versions.txt" 2>&1
docker tag "${tag}" "${registry}/${tag}"
docker push "${registry}/${tag}" >"${build_root}/docker-push.log" 2>&1
repo_digest="$(docker image inspect --format '{{range .RepoDigests}}{{println .}}{{end}}' "${tag}" \
  | grep -m1 "^${registry}/cotcodec-q1-gates@sha256:" || true)"
if [[ ! "${repo_digest}" =~ ^${registry}/cotcodec-q1-gates@sha256:[0-9a-f]{64}$ ]]; then
  echo "push did not yield a registry digest" >&2
  exit 2
fi
if [[ "$(docker image inspect --format '{{.Id}}' "${repo_digest}")" != "${image_id}" ]]; then
  echo "registry digest does not resolve to the built image ID" >&2
  exit 2
fi

cat >"${build_root}/receipt.json" <<JSON
{
  "job_id": "${SLURM_JOB_ID}",
  "git_sha": "${git_sha}",
  "git_tree": "${git_tree}",
  "source_tar_sha256": "${source_sha}",
  "tag": "${tag}",
  "image_id": "${image_id}",
  "repo_digest": "${repo_digest}",
  "base_image": "${base_ref}",
  "base_image_id": "${base_id}",
  "lane_ready": true,
  "network_during_build": true,
  "pushed": "private local registry only",
  "evidence_grade": "infrastructure-only"
}
JSON
cat "${build_root}/receipt.json" "${build_root}/versions.txt"
