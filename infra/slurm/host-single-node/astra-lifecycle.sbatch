#!/usr/bin/env bash
#SBATCH --job-name=cotcodec-astra-lifecycle
#SBATCH --partition=research
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=64G
#SBATCH --gres=gpu:h100:1
#SBATCH --time=00:30:00
#SBATCH --signal=B:USR1@120
#SBATCH --output=/home/kevin/cotcodec-runs/astra-native-lifecycle/slurm-%j.out

set -euo pipefail
umask 077

run_root="${COTCODEC_RUN_ROOT:?COTCODEC_RUN_ROOT is required}"
expected_source_sha256="${COTCODEC_SOURCE_SHA256:?COTCODEC_SOURCE_SHA256 is required}"
expected_git_sha="${COTCODEC_GIT_SHA:?COTCODEC_GIT_SHA is required}"
expected_git_tree="${COTCODEC_GIT_TREE:?COTCODEC_GIT_TREE is required}"
source_archive="${COTCODEC_SOURCE_ARCHIVE:?COTCODEC_SOURCE_ARCHIVE is required}"
source_receipt="${COTCODEC_SOURCE_RECEIPT:?COTCODEC_SOURCE_RECEIPT is required}"
source_extractor="${COTCODEC_SOURCE_EXTRACTOR:?COTCODEC_SOURCE_EXTRACTOR is required}"
expected_extractor_sha256="${COTCODEC_SOURCE_EXTRACTOR_SHA256:?COTCODEC_SOURCE_EXTRACTOR_SHA256 is required}"
app_image_archive="${COTCODEC_APP_IMAGE_ARCHIVE:?COTCODEC_APP_IMAGE_ARCHIVE is required}"
expected_app_image_archive_sha256="${COTCODEC_APP_IMAGE_ARCHIVE_SHA256:?COTCODEC_APP_IMAGE_ARCHIVE_SHA256 is required}"
python_bin="${COTCODEC_PYTHON:?COTCODEC_PYTHON is required}"

if [[ ! "${expected_source_sha256}" =~ ^[0-9a-f]{64}$ ]]; then
  echo "invalid COTCODEC_SOURCE_SHA256" >&2
  exit 2
fi
if [[ ! "${expected_git_sha}" =~ ^[0-9a-f]{40}$ \
   || ! "${expected_git_tree}" =~ ^[0-9a-f]{40}$ \
   || ! "${expected_extractor_sha256}" =~ ^[0-9a-f]{64}$ \
   || ! "${expected_app_image_archive_sha256}" =~ ^[0-9a-f]{64}$ ]]; then
  echo "invalid Git, extractor, or app-image identity" >&2
  exit 2
fi
for required in \
  "${source_archive}" \
  "${source_receipt}" \
  "${source_extractor}" \
  "${app_image_archive}"; do
  if [[ ! -f "${required}" || -L "${required}" ]]; then
    echo "missing regular input: ${required}" >&2
    exit 2
  fi
done
if [[ ! -x "${python_bin}" ]]; then
  echo "configured Python is not executable" >&2
  exit 2
fi
if [[ "$(sha256sum "${source_archive}" | awk '{print $1}')" != "${expected_source_sha256}" \
   || "$(sha256sum "${source_extractor}" | awk '{print $1}')" != "${expected_extractor_sha256}" \
   || "$(sha256sum "${app_image_archive}" | awk '{print $1}')" != "${expected_app_image_archive_sha256}" ]]; then
  echo "source, extractor, or app-image archive digest drifted" >&2
  exit 2
fi
mkdir -p "${run_root}"
source_root="${run_root}/source-${SLURM_JOB_ID}"
if [[ -e "${source_root}" ]]; then
  echo "job source output already exists" >&2
  exit 2
fi
mkdir -m 700 "${source_root}"
"${python_bin}" "${source_extractor}" \
  --archive "${source_archive}" \
  --receipt "${source_receipt}" \
  --output-dir "${source_root}" \
  --expected-archive-sha256 "${expected_source_sha256}" \
  --expected-git-sha "${expected_git_sha}" \
  --expected-git-tree "${expected_git_tree}"

archived_extractor="${source_root}/scripts/extract_discovery_source_archive.py"
archived_batch="${source_root}/infra/slurm/host-single-node/astra-lifecycle.sbatch"
active_batch_sha256="$(sha256sum "$0" | awk '{print $1}')"
if [[ "$(sha256sum "${archived_extractor}" | awk '{print $1}')" != "${expected_extractor_sha256}" \
   || "$(sha256sum "${archived_batch}" | awk '{print $1}')" != "${active_batch_sha256}" ]]; then
  echo "active extractor or Slurm batch differs from the archived source" >&2
  exit 2
fi
export COTCODEC_BATCH_SHA256="${active_batch_sha256}"

cd "${source_root}"
exec "${python_bin}" scripts/run_astra_lifecycle_doctor.py \
  --experiment experiments/memory/stage3-astra-native-lifecycle-doctor.yaml \
  --output "${run_root}/astra-lifecycle-v1" \
  --app-image-archive "${app_image_archive}" \
  --resume
