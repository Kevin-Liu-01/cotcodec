#!/usr/bin/env bash
#SBATCH --job-name=past-bench-sbom
#SBATCH --partition=research
#SBATCH --gres=gpu:h100:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=01:00:00
#SBATCH --output=/home/kevin/cotcodec-runs/past-bench/sbom-slurm-%j.out
#SBATCH --error=/home/kevin/cotcodec-runs/past-bench/sbom-slurm-%j.err

set -Eeuo pipefail
umask 077

if [[ $# -ne 9 ]]; then
  echo "usage: $0 BUILD_ROOT BUILD_RECEIPT_SHA IMAGE_ID IMAGE_ARCHIVE_SHA OUTPUT_ROOT TARGET_TAG TOOLS_ROOT TOOLS_ROOT_SHA BATCH_SHA" >&2
  exit 2
fi

build_root=$1
build_receipt_sha256=$2
image_id=$3
image_archive_sha256=$4
output_root=$5
target_tag=$6
tools_root=$7
tools_root_sha256=$8
expected_batch_sha256=$9

syft_image='anchore/syft@sha256:41f8289664101d6ebab30a97ac8df6b6f86b92d8343285ca90f428e2bc353106'
syft_image_id='sha256:e6ff5da240b940ab010282f502ae688019379cdee51578f76374ed9b29ef03e6'
syft_version='1.51.0'

: "${SLURM_JOB_ID:?SBOM generation must execute inside Slurm}"
: "${CUDA_VISIBLE_DEVICES:?Slurm did not map the allocated H100}"
if [[ ! ${build_receipt_sha256} =~ ^[0-9a-f]{64}$ \
  || ! ${image_archive_sha256} =~ ^[0-9a-f]{64}$ \
  || ! ${tools_root_sha256} =~ ^[0-9a-f]{64}$ \
  || ! ${expected_batch_sha256} =~ ^[0-9a-f]{64}$ \
  || ! ${image_id} =~ ^sha256:[0-9a-f]{64}$ \
  || ! ${build_root} =~ ^/home/kevin/cotcodec-runs/past-bench/build-[a-z0-9._-]{1,96}$ \
  || ! ${output_root} =~ ^/home/kevin/cotcodec-runs/past-bench/sbom-[a-z0-9._-]{1,96}$ \
  || ! ${tools_root} =~ ^/home/kevin/cotcodec-runs/past-bench/inputs/sbom-tools-[0-9a-f]{64}$ \
  || ! ${target_tag} =~ ^127[.]0[.]0[.]1:5000/cotcodec-past:[a-z0-9._-]{1,80}$ ]]; then
  echo "unsafe PAST SBOM argument" >&2
  exit 2
fi
if [[ ${CUDA_VISIBLE_DEVICES} == *,* \
  || ${SLURM_GPUS_ON_NODE:-} != 1 \
  || ! -d ${build_root} \
  || -L ${build_root} \
  || ! -d ${tools_root} \
  || -L ${tools_root} \
  || -e ${output_root} \
  || -L ${output_root} ]]; then
  echo "invalid PAST SBOM input, allocation, or output root" >&2
  exit 2
fi
if [[ $(nvidia-smi -i "${CUDA_VISIBLE_DEVICES}" --query-gpu=name --format=csv,noheader) != *H100* ]]; then
  echo "PAST SBOM cell requires a Slurm-owned H100" >&2
  exit 2
fi

batch_path=$(realpath -e -- "$0")
if [[ $(sha256sum "${batch_path}" | cut -d' ' -f1) != ${expected_batch_sha256} ]]; then
  echo "PAST SBOM batch script digest mismatch" >&2
  exit 2
fi
if [[ $(sha256sum "${build_root}/build-receipt.json" | cut -d' ' -f1) != ${build_receipt_sha256} \
  || $(sha256sum "${build_root}/image.tar" | cut -d' ' -f1) != ${image_archive_sha256} \
  || $(docker image inspect --format '{{.Id}}' "${image_id}") != ${image_id} \
  || $(docker image inspect --format '{{.Id}}' "${syft_image}") != ${syft_image_id} ]]; then
  echo "PAST build, image archive, target image, or Syft image drifted" >&2
  exit 2
fi

actual_tools_root=$(python3 - "${tools_root}" <<'PY'
import hashlib
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
rows = []
for path in sorted(root.rglob("*")):
    if path.is_symlink() or not path.is_file():
        if path.is_dir() and not path.is_symlink():
            continue
        raise SystemExit("SBOM tool bundle contains an unsupported entry")
    relative = path.relative_to(root).as_posix()
    payload = path.read_bytes()
    rows.append({"path": relative, "sha256": hashlib.sha256(payload).hexdigest(), "size": len(payload)})
print(hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest())
PY
)
if [[ ${actual_tools_root} != ${tools_root_sha256} ]]; then
  echo "PAST SBOM tool bundle drifted" >&2
  exit 2
fi

python3 - "${build_root}/build-receipt.json" "${image_id}" <<'PY'
import json
import sys
receipt = json.load(open(sys.argv[1], encoding="utf-8"))
if (
    receipt.get("status") != "PAST_DISCOVERY_IMAGE_BUILT_NOT_SCIENTIFIC_RESULT"
    or receipt.get("publication_ready") is not False
    or receipt.get("image_id") != sys.argv[2]
):
    raise SystemExit("PAST build receipt does not admit this discovery image")
PY

mkdir -m 0700 "${output_root}"
work_dir="${output_root}/work"
mkdir -m 0700 "${work_dir}"

docker tag "${image_id}" "${target_tag}"
docker push "${target_tag}" >"${output_root}/registry-push.log"
target_repo_digest=$(
  docker image inspect --format '{{range .RepoDigests}}{{println .}}{{end}}' "${target_tag}" \
    | grep -E '^127[.]0[.]0[.]1:5000/cotcodec-past@sha256:[0-9a-f]{64}$' \
    | sort -u
)
if [[ ! ${target_repo_digest} =~ ^127[.]0[.]0[.]1:5000/cotcodec-past@sha256:[0-9a-f]{64}$ ]]; then
  echo "PAST registry push did not produce one immutable repository digest" >&2
  exit 2
fi

docker image inspect "${target_repo_digest}" >"${work_dir}/target-image-inspect.json"
docker image inspect "${syft_image}" >"${work_dir}/syft-image-inspect.json"
nvidia-smi -i "${CUDA_VISIBLE_DEVICES}" \
  --query-gpu=name,uuid,driver_version \
  --format=csv,noheader >"${work_dir}/gpu-inventory.txt"

docker run --rm --pull=never \
  --network none \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,nodev,mode=1777,size=2g \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  --pids-limit 4096 \
  --user "$(id -u):$(id -g)" \
  --env GOMAXPROCS=8 \
  --env HOME=/tmp \
  --env SYFT_CHECK_FOR_APP_UPDATE=false \
  --volume "${build_root}/image.tar:/input/image.tar:ro" \
  --volume "${work_dir}:/output:rw" \
  "${syft_image}" \
  docker-archive:/input/image.tar \
  --output spdx-json=/output/sbom.raw.staged.spdx.json

common_target_args=(
  run --rm --pull=never
  --network none
  --read-only
  --tmpfs /tmp:rw,noexec,nosuid,nodev,mode=1777,size=1g
  --cap-drop ALL
  --security-opt no-new-privileges
  --pids-limit 512
  --user "$(id -u):$(id -g)"
  --env HOME=/tmp
  --env PYTHONPATH=/tools
  --volume "${tools_root}:/tools:ro"
)

docker "${common_target_args[@]}" \
  --volume "${work_dir}:/staged:ro" \
  --volume "${output_root}:/artifacts:rw" \
  --entrypoint /opt/past-bench-venv/bin/python \
  "${image_id}" \
  /tools/scripts/annotate_image_sbom.py \
  --raw-sbom /staged/sbom.raw.staged.spdx.json \
  --publish-raw /artifacts/sbom.raw.spdx.json \
  --output /artifacts/sbom.spdx.json \
  --receipt /artifacts/sbom-annotation-receipt.json \
  --image-id "${image_id}" \
  --repo-digest "${target_repo_digest}" \
  --syft-version "${syft_version}" \
  --syft-image "${syft_image}" \
  --scanner-target docker-archive:/input/image.tar

docker "${common_target_args[@]}" \
  --volume "${work_dir}:/staged:ro" \
  --volume "${output_root}:/artifacts:rw" \
  --volume "${build_root}/image.tar:/input/image.tar:ro" \
  --volume "${batch_path}:/batch/past-bench-sbom.sbatch:ro" \
  --entrypoint /opt/past-bench-venv/bin/python \
  "${image_id}" \
  /tools/scripts/seal_past_bench_sbom_job_receipt.py \
  --target-inspect /staged/target-image-inspect.json \
  --syft-inspect /staged/syft-image-inspect.json \
  --publish-target-inspect /artifacts/target-image-inspect.json \
  --publish-syft-inspect /artifacts/syft-image-inspect.json \
  --target-image-id "${image_id}" \
  --target-repo-digest "${target_repo_digest}" \
  --image-archive /input/image.tar \
  --raw-sbom /artifacts/sbom.raw.spdx.json \
  --sealed-sbom /artifacts/sbom.spdx.json \
  --annotation-receipt /artifacts/sbom-annotation-receipt.json \
  --batch-script /batch/past-bench-sbom.sbatch \
  --expected-batch-sha256 "${expected_batch_sha256}" \
  --gpu-inventory /staged/gpu-inventory.txt \
  --slurm-job-id "${SLURM_JOB_ID}" \
  --slurm-job-name "${SLURM_JOB_NAME}" \
  --slurm-partition "${SLURM_JOB_PARTITION}" \
  --slurm-cpus-per-task "${SLURM_CPUS_PER_TASK}" \
  --slurm-memory-mb "${SLURM_MEM_PER_NODE}" \
  --cuda-visible-devices "${CUDA_VISIBLE_DEVICES}" \
  --output /artifacts/sbom-job-receipt.json

python3 - "${output_root}" "${target_repo_digest}" "${tools_root_sha256}" <<'PY'
import hashlib
import json
import pathlib
import sys
root = pathlib.Path(sys.argv[1])
receipt = json.loads((root / "sbom-job-receipt.json").read_text(encoding="utf-8"))
if receipt.get("target_repo_digest") != sys.argv[2]:
    raise SystemExit("final SBOM receipt repository digest drifted")
summary = {
    "status": "PAST_DISCOVERY_SBOM_PASS_NOT_PUBLICATION_ATTESTATION",
    "scientific_result": False,
    "external_attestation": False,
    "target_repo_digest": sys.argv[2],
    "tools_root_sha256": sys.argv[3],
    "sbom_job_receipt_sha256": hashlib.sha256((root / "sbom-job-receipt.json").read_bytes()).hexdigest(),
    "sealed_sbom_sha256": hashlib.sha256((root / "sbom.spdx.json").read_bytes()).hexdigest(),
}
(root / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

echo "PAST_DISCOVERY_SBOM_PASS digest=${target_repo_digest} root=${output_root}"
