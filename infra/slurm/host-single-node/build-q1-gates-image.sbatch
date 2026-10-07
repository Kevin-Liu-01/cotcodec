#!/usr/bin/env bash
#SBATCH --job-name=cotcodec-build-q1-gates
#SBATCH --partition=research
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=01:00:00
#SBATCH --output=/home/kevin/cotcodec-runs/builds/slurm-%x-%j.out

# Build the derived Q1 gate image (infra/q1-gates/Dockerfile) from a clean,
# committed checkout with host networking (PyPI), check it in a GPU-less
# container, and write a build receipt. CPU-only: no GPU is requested, no model
# runs, nothing is pushed. COTCODEC_REPO must name a clean clone that is not
# the shared operator checkout.
set -Eeuo pipefail
umask 022

: "${SLURM_JOB_ID:?Run this build through Slurm}"
: "${COTCODEC_REPO:?Set COTCODEC_REPO to a clean clone}"
repo="$(cd "${COTCODEC_REPO}" && pwd -P)"
if [[ "${repo}" == "/home/kevin/cotcodec" ]]; then
  echo "refusing to build from the shared operator checkout" >&2
  exit 2
fi
cd "${repo}"
if [[ -n "$(git status --porcelain)" ]]; then
  echo "checkout is dirty; commit before building" >&2
  exit 2
fi
git_sha="$(git rev-parse HEAD)"
source_sha="$(git archive --format=tar "${git_sha}" | sha256sum | cut -d' ' -f1)"
base_id="sha256:3804466639c13f132be4b0369de4d3395b9d5ea2d3dc100cd38884c75197fe29"
if [[ "$(docker image inspect --format '{{.Id}}' "127.0.0.1:5000/cotcodec-research@sha256:02965f3d696d4e516a7cd6d5c03434e9098139738748ae778ed967215db7be6d")" != "${base_id}" ]]; then
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
  --build-arg "GIT_SHA=${git_sha}" \
  -f infra/q1-gates/Dockerfile \
  -t "${tag}" \
  . >"${build_root}/docker-build.log" 2>&1

image_id="$(docker image inspect --format '{{.Id}}' "${tag}")"
docker run --rm --network=none -e NVIDIA_VISIBLE_DEVICES=void --entrypoint bash "${tag}" -c \
  'test ! -e /dev/nvidiactl && cat /opt/q1/SHA256SUMS && python -c "import importlib.metadata as m; print({p: m.version(p) for p in [\"torch\", \"triton\", \"pyarrow\", \"ninja\", \"python-dotenv\", \"tomli\", \"pydantic-settings\", \"pytest\"]})"' \
  >"${build_root}/versions.txt" 2>&1

cat >"${build_root}/receipt.json" <<JSON
{
  "job_id": "${SLURM_JOB_ID}",
  "git_sha": "${git_sha}",
  "source_tar_sha256": "${source_sha}",
  "tag": "${tag}",
  "image_id": "${image_id}",
  "base_image_id": "${base_id}",
  "network_during_build": true,
  "pushed": false,
  "evidence_grade": "infrastructure-only"
}
JSON
cat "${build_root}/receipt.json" "${build_root}/versions.txt"
