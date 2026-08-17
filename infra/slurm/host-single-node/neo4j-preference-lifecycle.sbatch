#!/usr/bin/env bash
#SBATCH --job-name=cotcodec-neo4j-preference-lifecycle
#SBATCH --partition=research
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=64G
#SBATCH --gres=gpu:h100:1
#SBATCH --time=00:30:00
#SBATCH --output=/home/kevin/cotcodec-runs/neo4j-preference-lifecycle/slurm-%j.out

set -euo pipefail
umask 077

run_root="${COTCODEC_RUN_ROOT:?COTCODEC_RUN_ROOT is required}"
source_archive="${COTCODEC_SOURCE_ARCHIVE:?COTCODEC_SOURCE_ARCHIVE is required}"
source_receipt="${COTCODEC_SOURCE_RECEIPT:?COTCODEC_SOURCE_RECEIPT is required}"
source_extractor="${COTCODEC_SOURCE_EXTRACTOR:?COTCODEC_SOURCE_EXTRACTOR is required}"
client_image_archive="${COTCODEC_CLIENT_IMAGE_ARCHIVE:?COTCODEC_CLIENT_IMAGE_ARCHIVE is required}"
source_sha256="${COTCODEC_SOURCE_SHA256:?COTCODEC_SOURCE_SHA256 is required}"
source_git_sha="${COTCODEC_GIT_SHA:?COTCODEC_GIT_SHA is required}"
source_git_tree="${COTCODEC_GIT_TREE:?COTCODEC_GIT_TREE is required}"
extractor_sha256="${COTCODEC_SOURCE_EXTRACTOR_SHA256:?COTCODEC_SOURCE_EXTRACTOR_SHA256 is required}"
client_image_archive_sha256="${COTCODEC_CLIENT_IMAGE_ARCHIVE_SHA256:?COTCODEC_CLIENT_IMAGE_ARCHIVE_SHA256 is required}"
expected_client_image_id="${COTCODEC_CLIENT_IMAGE_ID:?COTCODEC_CLIENT_IMAGE_ID is required}"
python_bin="${COTCODEC_PYTHON:-/home/kevin/cotcodec/.venv/bin/python}"

if [[ ! $source_sha256 =~ ^[0-9a-f]{64}$ \
   || ! $source_git_sha =~ ^[0-9a-f]{40}$ \
   || ! $source_git_tree =~ ^[0-9a-f]{40}$ \
   || ! $extractor_sha256 =~ ^[0-9a-f]{64}$ \
   || ! $client_image_archive_sha256 =~ ^[0-9a-f]{64}$ \
   || ! $expected_client_image_id =~ ^sha256:[0-9a-f]{64}$ ]]; then
  echo "invalid source or extractor identity" >&2
  exit 64
fi
if [[ ! -d $run_root || -L $run_root ]]; then
  echo "run root is not a real directory" >&2
  exit 65
fi
for required in \
  "$source_archive" "$source_receipt" "$source_extractor" "$client_image_archive"; do
  if [[ ! -f $required || -L $required ]]; then
    echo "required source input is not a regular file: $required" >&2
    exit 65
  fi
done
if [[ ! -x $python_bin ]]; then
  echo "configured Python is unavailable" >&2
  exit 65
fi
if [[ $(sha256sum "$source_archive" | awk '{print $1}') != "$source_sha256" \
   || $(sha256sum "$source_extractor" | awk '{print $1}') != "$extractor_sha256" \
   || $(sha256sum "$client_image_archive" | awk '{print $1}') \
      != "$client_image_archive_sha256" ]]; then
  echo "source or extractor digest drifted" >&2
  exit 66
fi

gpu_inventory="$run_root/gpu-inventory-${SLURM_JOB_ID}.txt"
nvidia-smi -i "${CUDA_VISIBLE_DEVICES:?Slurm did not assign a GPU}" \
  --query-gpu=name,uuid,driver_version \
  --format=csv,noheader >"$gpu_inventory"
if [[ ! -s $gpu_inventory ]] || grep -qv H100 "$gpu_inventory"; then
  echo "the registered confirmation requires exactly an H100 allocation" >&2
  exit 67
fi

source_root="$run_root/source-${SLURM_JOB_ID}"
if [[ -e $source_root ]]; then
  echo "job source output already exists" >&2
  exit 67
fi
mkdir -m 700 "$source_root"
"$python_bin" "$source_extractor" \
  --archive "$source_archive" \
  --receipt "$source_receipt" \
  --output-dir "$source_root" \
  --expected-archive-sha256 "$source_sha256" \
  --expected-git-sha "$source_git_sha" \
  --expected-git-tree "$source_git_tree"

archived_batch="$source_root/infra/slurm/host-single-node/neo4j-preference-lifecycle.sbatch"
archived_extractor="$source_root/scripts/extract_discovery_source_archive.py"
active_batch_sha256=$(sha256sum "$0" | awk '{print $1}')
if [[ $(sha256sum "$archived_batch" | awk '{print $1}') != "$active_batch_sha256" \
   || $(sha256sum "$archived_extractor" | awk '{print $1}') != "$extractor_sha256" ]]; then
  echo "active batch or extractor differs from the archived source" >&2
  exit 68
fi

client_image='cotcodec-neo4j-preference-doctor:231d60e-cluster-amd64-slurm-v1'
docker image load --input "$client_image_archive"
if [[ $(docker image inspect --format '{{.Id}}' "$client_image") \
      != "$expected_client_image_id" ]]; then
  echo "prebuilt client image identity drifted" >&2
  exit 69
fi

lifecycle_root="$run_root/lifecycle-${SLURM_JOB_ID}"
"$python_bin" "$source_root/scripts/run_neo4j_preference_lifecycle_doctor.py" \
  --lane cluster-amd64-slurm \
  --prebuilt-client-image "$client_image" \
  --expected-client-image-id "$expected_client_image_id" \
  --output-dir "$lifecycle_root" \
  >"$run_root/lifecycle-${SLURM_JOB_ID}.stdout.json"

neo4j_image='neo4j:5.26.29-community@sha256:865213f53381e8d2ef3eec08b11741a6722d388a5e70b134135186a9b5cb27a6'
client_image_id=$(docker image inspect --format '{{.Id}}' "$client_image")
neo4j_image_id=$(docker image inspect --format '{{.Id}}' "$neo4j_image")
if [[ ! $client_image_id =~ ^sha256:[0-9a-f]{64}$ \
   || ! $neo4j_image_id =~ ^sha256:[0-9a-f]{64}$ ]]; then
  echo "Docker returned a non-immutable image ID" >&2
  exit 69
fi

client_inspect="$run_root/client-image-inspect-${SLURM_JOB_ID}.json"
neo4j_inspect="$run_root/neo4j-image-inspect-${SLURM_JOB_ID}.json"
client_archive="$run_root/client-image-${SLURM_JOB_ID}.tar"
docker image inspect "$client_image" >"$client_inspect"
docker image inspect "$neo4j_image" >"$neo4j_inspect"
docker image save --output "$client_archive" "$client_image"

syft_image='anchore/syft@sha256:41f8289664101d6ebab30a97ac8df6b6f86b92d8343285ca90f428e2bc353106'
syft_id='sha256:e6ff5da240b940ab010282f502ae688019379cdee51578f76374ed9b29ef03e6'
docker pull "$syft_image"
if [[ $(docker image inspect --format '{{.Id}}' "$syft_image") != "$syft_id" ]]; then
  echo "exact Syft image is unavailable or drifted" >&2
  exit 70
fi
sbom_dir="$run_root/sbom-${SLURM_JOB_ID}"
syft_tmp="$run_root/syft-tmp-${SLURM_JOB_ID}"
mkdir -m 700 "$sbom_dir" "$syft_tmp"
docker run --rm --pull=never \
  --network none \
  --read-only \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  --user "$(id -u):$(id -g)" \
  --env HOME=/tmp \
  --env SYFT_CHECK_FOR_APP_UPDATE=false \
  --volume "$client_archive:/input/image.tar:ro" \
  --volume "$sbom_dir:/output:rw" \
  --volume "$syft_tmp:/tmp:rw" \
  "$syft_image" \
  docker-archive:/input/image.tar \
  --output spdx-json=/output/client.spdx.json
if [[ ! -s $sbom_dir/client.spdx.json ]]; then
  echo "Syft did not produce a client SBOM" >&2
  exit 71
fi

"$python_bin" - \
  "$run_root" "$SLURM_JOB_ID" "$client_image" "$client_image_id" \
  "$neo4j_image" "$neo4j_image_id" "$active_batch_sha256" <<'PY'
import hashlib
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
job = sys.argv[2]
payload = {
    "schema_version": 1,
    "slurm_job_id": int(job),
    "slurm_job_name": "cotcodec-neo4j-preference-lifecycle",
    "client_image": sys.argv[3],
    "client_image_id": sys.argv[4],
    "neo4j_image": sys.argv[5],
    "neo4j_image_id": sys.argv[6],
    "batch_sha256": sys.argv[7],
    "gpu_inventory_sha256": hashlib.sha256(
        (root / f"gpu-inventory-{job}.txt").read_bytes()
    ).hexdigest(),
    "client_image_inspect_sha256": hashlib.sha256(
        (root / f"client-image-inspect-{job}.json").read_bytes()
    ).hexdigest(),
    "neo4j_image_inspect_sha256": hashlib.sha256(
        (root / f"neo4j-image-inspect-{job}.json").read_bytes()
    ).hexdigest(),
    "client_image_archive_sha256": hashlib.sha256(
        (root / f"client-image-{job}.tar").read_bytes()
    ).hexdigest(),
    "client_sbom_sha256": hashlib.sha256(
        (root / f"sbom-{job}/client.spdx.json").read_bytes()
    ).hexdigest(),
    "report_sha256": hashlib.sha256(
        (root / f"lifecycle-{job}/report.json").read_bytes()
    ).hexdigest(),
    "manifest_sha256": hashlib.sha256(
        (root / f"lifecycle-{job}/manifest.json").read_bytes()
    ).hexdigest(),
}
(root / f"job-{job}.receipt.json").write_text(
    json.dumps(payload, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
PY
