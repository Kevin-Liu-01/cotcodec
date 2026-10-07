#!/usr/bin/env bash
#SBATCH --job-name=cotcodec-k1-bundle
#SBATCH --partition=research
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=128G
#SBATCH --time=04:00:00
#SBATCH --output=/home/kevin/cotcodec-runs/translation-supervised-sparse-indexer/builds/slurm-%x-%j.out

# Build the Q3 K1 study bundle with image A. CPU only: no GPU is requested and
# no model runs. Stage 1 (fetch-raw) downloads pinned Belebele, FineWeb-2 and
# FineWeb files and streams ParaDocs through the reimplemented filter; it needs
# the network, so it runs with host networking (the bridge has no DNS) and
# writes only to the raw directory. Stage 2 (build) runs with no network, the
# raw directory and the model snapshot read-only, and writes the bundle and its
# sidecar. Usage:
#   COTCODEC_IMAGE_ID=sha256:<image A> COTCODEC_BUNDLE_COMMIT=<commit A> \
#     sbatch infra/slurm/host-single-node/build-k1-bundle.sbatch
set -Eeuo pipefail
umask 022

: "${SLURM_JOB_ID:?Run this build through Slurm}"
: "${COTCODEC_IMAGE_ID:?set COTCODEC_IMAGE_ID to image A (sha256:...)}"
: "${COTCODEC_BUNDLE_COMMIT:?set COTCODEC_BUNDLE_COMMIT to commit A}"
if [[ ! "${COTCODEC_IMAGE_ID}" =~ ^sha256:[0-9a-f]{64}$ ]]; then
  echo "COTCODEC_IMAGE_ID must be a local sha256 image id" >&2
  exit 2
fi
if [[ ! "${COTCODEC_BUNDLE_COMMIT}" =~ ^[0-9a-f]{40}$ ]]; then
  echo "COTCODEC_BUNDLE_COMMIT must be a 40-hex commit" >&2
  exit 2
fi
label="$(docker image inspect --format '{{ index .Config.Labels "org.opencontainers.image.revision" }}' "${COTCODEC_IMAGE_ID}")"
if [[ "${label}" != "${COTCODEC_BUNDLE_COMMIT}" ]]; then
  echo "image revision label ${label} differs from COTCODEC_BUNDLE_COMMIT" >&2
  exit 2
fi

base=/home/kevin/cotcodec-runs/translation-supervised-sparse-indexer
raw="${base}/raw/k1-v1"
out="${base}/inputs"
model=/home/kevin/cotcodec-runs/hf-cache/cotcodec-models/qwen3-0.6b-base
receipt=/home/kevin/cotcodec-runs/hf-cache/cotcodec-receipts/qwen3-0.6b-base.json
mkdir -m 0755 -p "${raw}" "${out}" "${base}/builds"
expected_tokenizer="$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print([f["sha256"] for f in d["files"] if f["path"]=="tokenizer.json"][0])' "${receipt}")"
actual_tokenizer="$(sha256sum "${model}/tokenizer.json" | cut -d' ' -f1)"
if [[ "${expected_tokenizer}" != "${actual_tokenizer}" ]]; then
  echo "tokenizer.json differs from the model receipt" >&2
  exit 2
fi

common=(--rm --read-only --tmpfs /tmp:rw,nosuid,nodev,size=8g --cap-drop ALL
  --security-opt no-new-privileges --user "$(id -u):$(id -g)"
  --env HOME=/tmp/home --env USER=cotcodec --env LOGNAME=cotcodec
  --env HF_HOME=/tmp/huggingface --env HF_HUB_DISABLE_TELEMETRY=1
  --env PYTHONUNBUFFERED=1 --volume "${model}:/model:ro")

if [[ ! -f "${raw}/raw-manifest.json" ]]; then
  docker run "${common[@]}" --network host --volume "${raw}:/raw" "${COTCODEC_IMAGE_ID}" \
    python scripts/build_sparse_indexer_k1_bundle.py fetch-raw \
      --raw-dir /raw --tokenizer /model/tokenizer.json
fi

docker run "${common[@]}" --network none --volume "${raw}:/raw:ro" --volume "${out}:/out" \
  "${COTCODEC_IMAGE_ID}" \
  python scripts/build_sparse_indexer_k1_bundle.py build \
    --raw-dir /raw --model-dir /model --output /out/k1-bundle-v1.json \
    --git-sha "${COTCODEC_BUNDLE_COMMIT}"

sha256sum "${out}/k1-bundle-v1.json" "${raw}/raw-manifest.json"
cat "${out}/k1-bundle-v1.json.manifest.json"
