#!/usr/bin/env bash
#SBATCH --partition=research
#SBATCH --job-name=mempalace-sbom
#SBATCH --gres=gpu:h100:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=01:00:00

set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo "usage: $0 RECEIPT_DIR IMAGE_REPO_DIGEST IMAGE_ID" >&2
  exit 64
fi

receipt_dir=$1
image_repo_digest=$2
image_id=$3
syft_image='anchore/syft@sha256:41f8289664101d6ebab30a97ac8df6b6f86b92d8343285ca90f428e2bc353106'
syft_image_id='sha256:e6ff5da240b940ab010282f502ae688019379cdee51578f76374ed9b29ef03e6'
syft_version='1.51.0'

repo_digest_re='^[A-Za-z0-9][A-Za-z0-9._:/-]*@sha256:[0-9a-f]{64}$'
image_id_re='^sha256:[0-9a-f]{64}$'
version_re='^[0-9]+\.[0-9]+\.[0-9]+$'

if [[ ! $image_repo_digest =~ $repo_digest_re ]]; then
  echo "image repository digest must be immutable" >&2
  exit 65
fi
if [[ ! $image_id =~ $image_id_re ]]; then
  echo "image ID must be immutable" >&2
  exit 65
fi
if [[ ! $syft_version =~ $version_re ]]; then
  echo "Syft version must be semantic x.y.z" >&2
  exit 65
fi
if [[ ! -d $receipt_dir || -L $receipt_dir ]]; then
  echo "receipt directory must be an existing non-symlink directory" >&2
  exit 66
fi
receipt_dir=$(realpath -e -- "$receipt_dir")
case "$receipt_dir" in
  /home/kevin/cotcodec-research-receipts/mempalace/*) ;;
  *)
    echo "receipt directory is outside the registered MemPalace root" >&2
    exit 66
    ;;
esac

raw_sbom="$receipt_dir/sbom.raw.spdx.json"
sealed_sbom="$receipt_dir/sbom.spdx.json"
annotation_receipt="$receipt_dir/sbom-annotation-receipt.json"
target_inspect_receipt="$receipt_dir/target-image-inspect.json"
syft_inspect_receipt="$receipt_dir/syft-image-inspect.json"
job_receipt="$receipt_dir/sbom-job-receipt.json"
for output in \
  "$raw_sbom" \
  "$sealed_sbom" \
  "$annotation_receipt" \
  "$target_inspect_receipt" \
  "$syft_inspect_receipt" \
  "$job_receipt"; do
  if [[ -e $output || -L $output ]]; then
    echo "refusing to overwrite SBOM artifact: $output" >&2
    exit 67
  fi
done

run_as_docker_group() {
  local quoted
  printf -v quoted '%q ' "$@"
  sg docker -c "$quoted"
}

scratch_root=/home/kevin/cotcodec-scratch
mkdir -p -- "$scratch_root"
scratch_dir=$(mktemp -d "$scratch_root/mempalace-syft.${SLURM_JOB_ID:?}.XXXXXX")
case "$scratch_dir" in
  /home/kevin/cotcodec-scratch/mempalace-syft.*) ;;
  *)
    echo "Syft scratch directory escaped its registered root" >&2
    exit 68
    ;;
esac
work_dir="$scratch_dir/work"
mkdir "$work_dir"
chmod 0700 -- "$work_dir"
cleanup_scratch() {
  rm -rf -- "$scratch_dir"
}
trap cleanup_scratch EXIT

target_inspect="$scratch_dir/target-image-inspect.json"
syft_inspect="$scratch_dir/syft-image-inspect.json"
image_archive="$scratch_dir/image.tar"
gpu_inventory="$scratch_dir/gpu-inventory.txt"
batch_path=$(realpath -e -- "$0")
batch_sha256=$(sha256sum "$batch_path" | cut -d' ' -f1)
actual_target_id=$(run_as_docker_group \
  docker image inspect --format '{{.Id}}' "$image_repo_digest")
actual_syft_id=$(run_as_docker_group \
  docker image inspect --format '{{.Id}}' "$syft_image")
if [[ $actual_target_id != "$image_id" || $actual_syft_id != "$syft_image_id" ]]; then
  echo "target or Syft image ID differs from the registered immutable image" >&2
  exit 69
fi
run_as_docker_group docker image inspect "$image_repo_digest" \
  | tee "$target_inspect" >/dev/null
run_as_docker_group docker image inspect "$syft_image" \
  | tee "$syft_inspect" >/dev/null
run_as_docker_group docker image save --output "$image_archive" "$image_repo_digest"
nvidia-smi -i "${CUDA_VISIBLE_DEVICES:?}" \
  --query-gpu=name,uuid,driver_version \
  --format=csv,noheader \
  | tee "$gpu_inventory" >/dev/null
if [[ ! -s $gpu_inventory ]] || grep -qv H100 "$gpu_inventory"; then
  echo "SBOM cell requires a Slurm-owned H100 allocation" >&2
  exit 69
fi
chmod 0444 -- "$image_archive" "$target_inspect" "$syft_inspect" "$gpu_inventory"

run_as_docker_group \
  docker run --rm --pull=never \
  --network none \
  --read-only \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  --user "$(id -u):$(id -g)" \
  --env HOME=/tmp \
  --env SYFT_CHECK_FOR_APP_UPDATE=false \
  --volume "$image_archive:/input/image.tar:ro" \
  --volume "$work_dir:/tmp:rw" \
  --volume "$work_dir:/output:rw" \
  "$syft_image" \
  docker-archive:/input/image.tar \
  --output spdx-json=/output/sbom.raw.spdx.json

test -s "$work_dir/sbom.raw.spdx.json"

run_as_docker_group \
  docker run --rm --pull=never \
  --network none \
  --read-only \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  --user "$(id -u):$(id -g)" \
  --volume "$work_dir:/staged:ro" \
  --volume "$receipt_dir:/artifacts:rw" \
  --entrypoint /opt/mempalace/source/.venv/bin/python \
  "$image_repo_digest" \
  /workspace/cotcodec/scripts/annotate_image_sbom.py \
  --raw-sbom /staged/sbom.raw.spdx.json \
  --publish-raw /artifacts/sbom.raw.spdx.json \
  --output /artifacts/sbom.spdx.json \
  --receipt /artifacts/sbom-annotation-receipt.json \
  --image-id "$image_id" \
  --repo-digest "$image_repo_digest" \
  --syft-version "$syft_version" \
  --syft-image "$syft_image" \
  --scanner-target docker-archive:/input/image.tar

run_as_docker_group \
  docker run --rm --pull=never \
  --network none \
  --read-only \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  --user "$(id -u):$(id -g)" \
  --volume "$scratch_dir:/staged:ro" \
  --volume "$receipt_dir:/artifacts:rw" \
  --volume "$batch_path:/batch/mempalace-sbom.sbatch:ro" \
  --entrypoint /opt/mempalace/source/.venv/bin/python \
  "$image_repo_digest" \
  /workspace/cotcodec/scripts/seal_mempalace_sbom_job_receipt.py \
  --target-inspect /staged/target-image-inspect.json \
  --syft-inspect /staged/syft-image-inspect.json \
  --publish-target-inspect /artifacts/target-image-inspect.json \
  --publish-syft-inspect /artifacts/syft-image-inspect.json \
  --target-image-id "$image_id" \
  --target-repo-digest "$image_repo_digest" \
  --image-archive /staged/image.tar \
  --raw-sbom /artifacts/sbom.raw.spdx.json \
  --sealed-sbom /artifacts/sbom.spdx.json \
  --annotation-receipt /artifacts/sbom-annotation-receipt.json \
  --batch-script /batch/mempalace-sbom.sbatch \
  --expected-batch-sha256 "$batch_sha256" \
  --gpu-inventory /staged/gpu-inventory.txt \
  --slurm-job-id "${SLURM_JOB_ID:?}" \
  --slurm-job-name "${SLURM_JOB_NAME:?}" \
  --slurm-partition "${SLURM_JOB_PARTITION:?}" \
  --slurm-cpus-per-task "${SLURM_CPUS_PER_TASK:?}" \
  --slurm-memory-mb "${SLURM_MEM_PER_NODE:?}" \
  --cuda-visible-devices "${CUDA_VISIBLE_DEVICES:?}" \
  --output /artifacts/sbom-job-receipt.json

python3 - \
  "$raw_sbom" \
  "$sealed_sbom" \
  "$annotation_receipt" \
  "$target_inspect_receipt" \
  "$syft_inspect_receipt" \
  "$job_receipt" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

for value in sys.argv[1:]:
    path = Path(value)
    payload = path.read_bytes()
    json.loads(payload)
    print(f"{path.name} sha256={hashlib.sha256(payload).hexdigest()} bytes={len(payload)}")
PY
