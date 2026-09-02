#!/usr/bin/env bash
#SBATCH --job-name=cotcodec-build-arch-image
#SBATCH --partition=research
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=64G
#SBATCH --time=03:00:00
#SBATCH --output=/home/kevin/cotcodec-runs/builds/slurm-%x-%j.out

# Rebuild the sealed architecture base image from the committed checkout with
# network enabled (uv sync needs PyPI), record provenance, and push to the
# host's local registry so downstream jobs can pin the repo digest. CPU-only:
# no GPU is requested and no model runs. Discovery lane only.
set -Eeuo pipefail
umask 022

: "${SLURM_JOB_ID:?Run this build through Slurm}"
repo="${COTCODEC_REPO:-/home/kevin/cotcodec}"
registry="${COTCODEC_LOCAL_REGISTRY:-127.0.0.1:5000}"
cd "${repo}"
if [[ -n "$(git status --porcelain)" ]]; then
  echo "checkout is dirty; commit or stash before building" >&2
  exit 2
fi
git_sha="$(git rev-parse HEAD)"
git_tree="$(git rev-parse HEAD^{tree})"
source_sha="$(git archive --format=tar "${git_sha}" | sha256sum | cut -d' ' -f1)"
tag="cotcodec-research:${git_sha:0:8}-architecture"
build_root="/home/kevin/cotcodec-runs/builds/${git_sha:0:8}-architecture-${SLURM_JOB_ID}"
mkdir -m 0755 -p "${build_root}"

# The host's default bridge network has no DNS; BuildKit RUN steps need host networking.
docker build \
  --pull=false \
  --network=host \
  --progress=plain \
  --build-arg "GIT_SHA=${git_sha}" \
  --build-arg "SOURCE_TREE_SHA256=${source_sha}" \
  --build-arg UV_EXTRA=architecture \
  --build-arg INCLUDE_DEV=false \
  -f infra/research/Dockerfile \
  -t "${tag}" \
  . >"${build_root}/docker-build.log" 2>&1

image_id="$(docker image inspect --format '{{.Id}}' "${tag}")"
docker tag "${tag}" "${registry}/${tag}"
docker push "${registry}/${tag}" >"${build_root}/docker-push.log" 2>&1
repo_digest="$(docker image inspect --format '{{index .RepoDigests 0}}' "${tag}")"
docker run --rm --network=none "${tag}" python -c \
  'import importlib.metadata as m, sys; print({p: m.version(p) for p in ["torch","transformers","flash-linear-attention","fla-core","triton"]})' \
  >"${build_root}/versions.txt" 2>&1 || true

cat >"${build_root}/receipt.json" <<JSON
{
  "job_id": "${SLURM_JOB_ID}",
  "git_sha": "${git_sha}",
  "git_tree": "${git_tree}",
  "source_tar_sha256": "${source_sha}",
  "tag": "${tag}",
  "image_id": "${image_id}",
  "repo_digest": "${repo_digest}",
  "uv_extra": "architecture",
  "network_during_build": true,
  "evidence_grade": "infrastructure-only"
}
JSON
cat "${build_root}/receipt.json" "${build_root}/versions.txt"
