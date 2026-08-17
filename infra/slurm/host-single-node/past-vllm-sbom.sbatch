#!/usr/bin/env bash
#SBATCH --job-name=past-vllm-sbom
#SBATCH --partition=research
#SBATCH --gres=gpu:h100:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=01:00:00
#SBATCH --output=/home/kevin/cotcodec-runs/past-bench/vllm-sbom-slurm-%j.out
#SBATCH --error=/home/kevin/cotcodec-runs/past-bench/vllm-sbom-slurm-%j.err

set -Eeuo pipefail
umask 077

if [[ $# -ne 6 ]]; then
  echo "usage: $0 ACQUISITION_RECEIPT RECEIPT_SHA OUTPUT_ROOT TOOLS_ROOT TOOLS_ROOT_SHA BATCH_SHA" >&2
  exit 2
fi

acquisition_receipt=$1
acquisition_receipt_sha256=$2
output_root=$3
tools_root=$4
tools_root_sha256=$5
expected_batch_sha256=$6

expected_upstream_digest='docker.io/vllm/vllm-openai@sha256:f0b9a0dc75a9fca3b6811e3279367b2d6a448055a000bfd13859587d74cef268'
expected_image_id='sha256:f26809eb13339cbc59c3d0cc972f8c4997830dc8d2121cf18089cb122834e10d'
expected_acquisition_sha256='ae800444ba8a1912cbe8932d2e6d54d68266a0dc6c6166739eae58b0db7c485b'
expected_archive_sha256='aecb8b90cd6378c1440c60efd3eef1d98d189e47110539350858dfde2ec9d0f4'
expected_doctor_sha256='ea2525af9f350fd6620a95337c8cb989029fac8efc34690d8e9f3c2dcdf8f284'
expected_inspect_sha256='8a90f1d29afe7bbbef64f3107912d77e8864c2fd70ce3b28a10b3cc4efdab3d1'
verifier_image_id='sha256:ebcf7eea7f1977f03e5e007edf265fcd120edadcd6d48e81f63df70715783150'
verifier_archive='/home/kevin/cotcodec-runs/past-bench/build-20260814-checkpoint-d4945b33-v1/image.tar'
verifier_archive_sha256='2f97fa8c18528eff8fd2e335e851255be280a20d2a3a81f74eab7485c0db285b'
annotator_sha256='e98593fb3ef6873e5a722de97310cba0e9f111a47c961d5a9043cedadc7b5399'
generic_sealer_sha256='df7b026ac90b897952786485b114b8e4931c9c6e8580344d6523576c72c05cea'
vllm_sealer_sha256='c9a04ef491ea7e5dd0fc2104ddb9af72a534f8d2d35628ed976af0665bb19de6'
syft_image='anchore/syft@sha256:41f8289664101d6ebab30a97ac8df6b6f86b92d8343285ca90f428e2bc353106'
syft_image_id='sha256:e6ff5da240b940ab010282f502ae688019379cdee51578f76374ed9b29ef03e6'
syft_version='1.51.0'

: "${SLURM_JOB_ID:?vLLM SBOM generation must execute inside Slurm}"
: "${CUDA_VISIBLE_DEVICES:?Slurm did not map the allocated H100}"
: "${SLURM_JOB_GPUS:?Slurm did not expose the allocated physical GPU}"
runtime_uid=$(id -u)
runtime_gid=$(id -g)
runtime_identity="${runtime_uid}:${runtime_gid}"
if [[ ${runtime_uid} == 0 || ${runtime_gid} == 0 \
  || ${acquisition_receipt_sha256} != ${expected_acquisition_sha256} \
  || ! ${tools_root_sha256} =~ ^[0-9a-f]{64}$ \
  || ! ${expected_batch_sha256} =~ ^[0-9a-f]{64}$ \
  || ! ${acquisition_receipt} =~ ^/home/kevin/cotcodec-runs/past-bench/vllm-acquire-[a-z0-9._-]{1,96}/acquisition-receipt[.]json$ \
  || ! ${output_root} =~ ^/home/kevin/cotcodec-runs/past-bench/vllm-sbom-[a-z0-9._-]{1,96}$ \
  || ! ${tools_root} =~ ^/home/kevin/cotcodec-runs/past-bench/inputs/vllm-sbom-tools-[0-9a-f]{64}$ ]]; then
  echo "unsafe PAST vLLM SBOM argument or identity" >&2
  exit 2
fi
if [[ ${CUDA_VISIBLE_DEVICES} == *,* \
  || ${SLURM_GPUS_ON_NODE:-} != 1 \
  || ! -f ${acquisition_receipt} \
  || -L ${acquisition_receipt} \
  || ! -d ${tools_root} \
  || -L ${tools_root} \
  || -e ${output_root} \
  || -L ${output_root} ]]; then
  echo "invalid PAST vLLM SBOM input, allocation, or output root" >&2
  exit 2
fi
gpu_uuid=$(nvidia-smi -i "${SLURM_JOB_GPUS}" --query-gpu=uuid --format=csv,noheader)
gpu_name=$(nvidia-smi -i "${SLURM_JOB_GPUS}" --query-gpu=name --format=csv,noheader)
if [[ ${gpu_name} != *H100* || ! ${gpu_uuid} =~ ^GPU-[A-Fa-f0-9-]{16,80}$ ]]; then
  echo "PAST vLLM SBOM cell requires one Slurm-owned H100" >&2
  exit 2
fi

registered_batch="${tools_root}/infra/slurm/host-single-node/past-vllm-sbom.sbatch"
if [[ ! -f ${registered_batch} || -L ${registered_batch} \
  || $(sha256sum "${registered_batch}" | cut -d' ' -f1) != ${expected_batch_sha256} \
  || $(sha256sum "$0" | cut -d' ' -f1) != ${expected_batch_sha256} ]]; then
  echo "PAST vLLM SBOM batch digest drifted" >&2
  exit 2
fi

actual_tools_root=$(python3 - "${tools_root}" "${expected_batch_sha256}" \
  "${annotator_sha256}" "${generic_sealer_sha256}" "${vllm_sealer_sha256}" <<'PY'
import hashlib
import json
import pathlib
import sys
root = pathlib.Path(sys.argv[1])
expected = {
    "infra/slurm/host-single-node/past-vllm-sbom.sbatch": sys.argv[2],
    "scripts/annotate_image_sbom.py": sys.argv[3],
    "scripts/seal_mempalace_sbom_job_receipt.py": sys.argv[4],
    "scripts/seal_past_vllm_sbom_job_receipt.py": sys.argv[5],
}
rows = []
for path in sorted(root.rglob("*")):
    if path.is_symlink() or (not path.is_file() and not path.is_dir()):
        raise SystemExit("vLLM SBOM tool bundle contains an unsupported entry")
    if path.is_file():
        payload = path.read_bytes()
        relative = path.relative_to(root).as_posix()
        digest = hashlib.sha256(payload).hexdigest()
        if expected.get(relative) != digest:
            raise SystemExit(f"unregistered vLLM SBOM tool: {relative}")
        rows.append({"path": relative, "sha256": digest, "size": len(payload)})
if {row["path"] for row in rows} != set(expected):
    raise SystemExit("vLLM SBOM tool bundle roster is incomplete")
print(hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest())
PY
)
if [[ ${actual_tools_root} != ${tools_root_sha256} ]]; then
  echo "PAST vLLM SBOM tool bundle drifted" >&2
  exit 2
fi

acquisition_root=$(dirname "${acquisition_receipt}")
image_archive="${acquisition_root}/image.tar"
import_doctor="${acquisition_root}/contained-import-doctor.json"
acquisition_inspect="${acquisition_root}/image-inspect.json"
if [[ ! -f ${image_archive} || -L ${image_archive} \
  || ! -f ${import_doctor} || -L ${import_doctor} \
  || ! -f ${acquisition_inspect} || -L ${acquisition_inspect} \
  || ! -f ${verifier_archive} || -L ${verifier_archive} \
  || $(sha256sum "${acquisition_receipt}" | cut -d' ' -f1) != ${expected_acquisition_sha256} \
  || $(sha256sum "${image_archive}" | cut -d' ' -f1) != ${expected_archive_sha256} \
  || $(sha256sum "${import_doctor}" | cut -d' ' -f1) != ${expected_doctor_sha256} \
  || $(sha256sum "${acquisition_inspect}" | cut -d' ' -f1) != ${expected_inspect_sha256} \
  || $(sha256sum "${verifier_archive}" | cut -d' ' -f1) != ${verifier_archive_sha256} ]]; then
  echo "PAST vLLM acquisition evidence drifted" >&2
  exit 2
fi
python3 - "${acquisition_receipt}" "${import_doctor}" <<'PY'
import json
import sys
receipt = json.load(open(sys.argv[1], encoding="utf-8"))
doctor = json.load(open(sys.argv[2], encoding="utf-8"))
expected = {
    "schema_version": 1,
    "status": "PAST_VLLM_DISCOVERY_IMAGE_ACQUIRED_NOT_SCIENTIFIC_RESULT",
    "scientific_result": False,
    "publication_ready": False,
    "image_id": "sha256:f26809eb13339cbc59c3d0cc972f8c4997830dc8d2121cf18089cb122834e10d",
    "image_repo_digest": "docker.io/vllm/vllm-openai@sha256:f0b9a0dc75a9fca3b6811e3279367b2d6a448055a000bfd13859587d74cef268",
    "platform": "linux/amd64",
}
for key, value in expected.items():
    if receipt.get(key) != value:
        raise SystemExit(f"vLLM acquisition field {key!r} drifted")
if doctor.get("vllm") != "0.25.1" or "H100" not in str(doctor.get("cuda")) or not doctor.get("gpu_uuid"):
    raise SystemExit("vLLM acquisition import doctor drifted")
PY

mkdir -m 0700 "${output_root}"
docker load --input "${verifier_archive}" >"${output_root}/verifier-image-load.txt"
if [[ $(docker image inspect --format '{{.Id}}' "${verifier_image_id}") != ${verifier_image_id} \
  || $(docker image inspect --format '{{.Id}}' "${syft_image}") != ${syft_image_id} ]]; then
  echo "PAST verifier or Syft image drifted" >&2
  exit 2
fi

work_dir="${output_root}/work"
mkdir -m 0700 "${work_dir}"
mkdir -m 0700 "${work_dir}/syft-tmp"
target_repo_digest=${expected_upstream_digest}
cp --reflink=never --no-preserve=mode,ownership,timestamps \
  "${acquisition_inspect}" "${work_dir}/target-image-inspect.json"
docker image inspect "${syft_image}" >"${work_dir}/syft-image-inspect.json"
nvidia-smi -i "${SLURM_JOB_GPUS}" --query-gpu=name,uuid,driver_version --format=csv,noheader \
  >"${work_dir}/gpu-inventory.txt"

docker run --rm --pull=never \
  --network none --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,nodev,mode=1777,size=2g \
  --cap-drop ALL --security-opt no-new-privileges --pids-limit 4096 \
  --user "${runtime_identity}" \
  --env GOMAXPROCS=8 --env HOME=/tmp --env TMPDIR=/output/syft-tmp \
  --env SYFT_CHECK_FOR_APP_UPDATE=false \
  --volume "${image_archive}:/input/image.tar:ro" \
  --volume "${work_dir}:/output:rw" \
  "${syft_image}" docker-archive:/input/image.tar \
  --output spdx-json=/output/sbom.raw.staged.spdx.json

common_target_args=(
  run --rm --pull=never --network none --read-only
  --tmpfs /tmp:rw,noexec,nosuid,nodev,mode=1777,size=1g
  --cap-drop ALL --security-opt no-new-privileges --pids-limit 512
  --user "${runtime_identity}" --env USER=cotcodec --env LOGNAME=cotcodec
  --env HOME=/tmp --env PYTHONPATH=/tools
  --volume "${tools_root}:/tools:ro"
  --entrypoint /opt/past-bench-venv/bin/python
)
docker "${common_target_args[@]}" \
  --volume "${work_dir}:/staged:ro" \
  --volume "${output_root}:/artifacts:rw" \
  "${verifier_image_id}" /tools/scripts/annotate_image_sbom.py \
  --raw-sbom /staged/sbom.raw.staged.spdx.json \
  --publish-raw /artifacts/sbom.raw.spdx.json \
  --output /artifacts/sbom.spdx.json \
  --receipt /artifacts/sbom-annotation-receipt.json \
  --image-id "${expected_image_id}" \
  --repo-digest "${target_repo_digest}" \
  --syft-version "${syft_version}" \
  --syft-image "${syft_image}" \
  --scanner-target docker-archive:/input/image.tar

docker "${common_target_args[@]}" \
  --volume "${work_dir}:/staged:ro" \
  --volume "${output_root}:/artifacts:rw" \
  --volume "${image_archive}:/input/image.tar:ro" \
  --volume "${registered_batch}:/batch/past-vllm-sbom.sbatch:ro" \
  "${verifier_image_id}" /tools/scripts/seal_past_vllm_sbom_job_receipt.py \
  --target-inspect /staged/target-image-inspect.json \
  --syft-inspect /staged/syft-image-inspect.json \
  --publish-target-inspect /artifacts/target-image-inspect.json \
  --publish-syft-inspect /artifacts/syft-image-inspect.json \
  --target-image-id "${expected_image_id}" \
  --target-repo-digest "${target_repo_digest}" \
  --image-archive /input/image.tar \
  --raw-sbom /artifacts/sbom.raw.spdx.json \
  --sealed-sbom /artifacts/sbom.spdx.json \
  --annotation-receipt /artifacts/sbom-annotation-receipt.json \
  --batch-script /batch/past-vllm-sbom.sbatch \
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
    raise SystemExit("final vLLM SBOM receipt repository digest drifted")
summary = {
    "status": "PAST_VLLM_DISCOVERY_SBOM_PASS_NOT_PUBLICATION_ATTESTATION",
    "scientific_result": False,
    "external_attestation": False,
    "upstream_repo_digest": "docker.io/vllm/vllm-openai@sha256:f0b9a0dc75a9fca3b6811e3279367b2d6a448055a000bfd13859587d74cef268",
    "acquisition_receipt_sha256": "ae800444ba8a1912cbe8932d2e6d54d68266a0dc6c6166739eae58b0db7c485b",
    "target_repo_digest": sys.argv[2],
    "tools_root_sha256": sys.argv[3],
    "sbom_job_receipt_sha256": hashlib.sha256((root / "sbom-job-receipt.json").read_bytes()).hexdigest(),
    "sealed_sbom_sha256": hashlib.sha256((root / "sbom.spdx.json").read_bytes()).hexdigest(),
}
(root / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

echo "PAST_VLLM_DISCOVERY_SBOM_PASS digest=${target_repo_digest} root=${output_root}"
