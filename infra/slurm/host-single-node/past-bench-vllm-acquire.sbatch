#!/usr/bin/env bash
#SBATCH --job-name=past-vllm-acquire
#SBATCH --partition=research
#SBATCH --gres=gpu:h100:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=00:30:00
#SBATCH --output=/home/kevin/cotcodec-runs/past-bench/slurm-%j.out
#SBATCH --error=/home/kevin/cotcodec-runs/past-bench/slurm-%j.err

set -Eeuo pipefail
umask 077

if [[ $# -ne 2 ]]; then
  echo "usage: $0 VLLM_IMAGE_REPO_DIGEST OUTPUT_ROOT" >&2
  exit 2
fi

image_repo_digest=$1
output_root=$2

: "${SLURM_JOB_ID:?vLLM acquisition must execute inside Slurm}"
: "${CUDA_VISIBLE_DEVICES:?Slurm did not map the allocated H100}"
: "${SLURM_JOB_GPUS:?Slurm did not expose the allocated physical GPU}"

if [[ ! ${image_repo_digest} =~ ^docker\.io/vllm/vllm-openai@sha256:[0-9a-f]{64}$ \
  || ! ${output_root} =~ ^/home/kevin/cotcodec-runs/past-bench/vllm-acquire-[a-z0-9._-]{1,96}$ ]]; then
  echo "unsafe vLLM acquisition argument" >&2
  exit 2
fi
IFS=, read -r -a slurm_job_gpus <<<"${SLURM_JOB_GPUS}"
if [[ ${#slurm_job_gpus[@]} -ne 1 \
  || ${SLURM_GPUS_ON_NODE:-} != 1 \
  || -e ${output_root} \
  || -L ${output_root} ]]; then
  echo "invalid vLLM acquisition allocation or output root" >&2
  exit 2
fi
if [[ $(nvidia-smi -i "${SLURM_JOB_GPUS}" --query-gpu=name --format=csv,noheader) != *H100* ]]; then
  echo "vLLM acquisition requires a Slurm-owned H100" >&2
  exit 2
fi
allocated_gpu_uuid=$(nvidia-smi -i "${SLURM_JOB_GPUS}" --query-gpu=uuid --format=csv,noheader)
if [[ ! ${allocated_gpu_uuid} =~ ^GPU-[A-Fa-f0-9-]{16,80}$ ]]; then
  echo "Slurm-owned H100 UUID is unavailable" >&2
  exit 2
fi

mkdir -m 0700 "${output_root}"
sha256sum "$0" >"${output_root}/batch-script.sha256"
nvidia-smi -i "${SLURM_JOB_GPUS}" \
  --query-gpu=uuid,name,driver_version \
  --format=csv,noheader >"${output_root}/gpu.csv"

docker pull --platform linux/amd64 "${image_repo_digest}" \
  >"${output_root}/docker-pull.log" 2>&1
docker image inspect "${image_repo_digest}" >"${output_root}/image-inspect.json"
image_id=$(docker image inspect --format '{{.Id}}' "${image_repo_digest}")
if [[ ! ${image_id} =~ ^sha256:[0-9a-f]{64}$ ]]; then
  echo "resolved vLLM image ID is invalid" >&2
  exit 2
fi
if ! docker image inspect --format '{{json .RepoDigests}}' "${image_repo_digest}" \
  | python3 -c 'import json,sys; canonical=lambda value: value.removeprefix("docker.io/"); expected=canonical(sys.argv[1]); values=[canonical(value) for value in json.load(sys.stdin)]; raise SystemExit(0 if expected in values else 1)' \
      "${image_repo_digest}"; then
  echo "pulled vLLM image does not retain the requested repository digest" >&2
  exit 2
fi

docker_gpu_request="device=${allocated_gpu_uuid}"
docker run --rm --pull=never \
  --gpus "${docker_gpu_request}" \
  --network none \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,nodev,size=2g \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  --pids-limit 2048 \
  --ulimit core=0 \
  --env COTCODEC_EXPECTED_GPU_UUID="${allocated_gpu_uuid}" \
  --entrypoint python3 \
  "${image_id}" \
  -c 'import json,os,subprocess,torch,vllm; uuids=subprocess.check_output(["nvidia-smi","--query-gpu=uuid","--format=csv,noheader"],text=True).strip().splitlines(); assert torch.cuda.device_count() == 1 and uuids == [os.environ["COTCODEC_EXPECTED_GPU_UUID"]]; print(json.dumps({"cuda": torch.cuda.get_device_name(0), "gpu_uuid": uuids[0], "torch": torch.__version__, "vllm": vllm.__version__}, sort_keys=True))' \
  >"${output_root}/contained-import-doctor.json"

docker run --rm --pull=never \
  --gpus "${docker_gpu_request}" \
  --network none \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,nodev,size=2g \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  --pids-limit 512 \
  --ulimit core=0 \
  --entrypoint vllm \
  "${image_id}" serve --help=all \
  >"${output_root}/vllm-serve-help.txt"

for required_flag in \
  --enable-auto-tool-choice \
  --tool-call-parser \
  --served-model-name \
  --tensor-parallel-size \
  --default-chat-template-kwargs; do
  if ! grep -F -- "${required_flag}" "${output_root}/vllm-serve-help.txt" >/dev/null; then
    echo "vLLM image is missing required server flag ${required_flag}" >&2
    exit 2
  fi
done

docker save "${image_id}" --output "${output_root}/image.tar"
sha256sum "${output_root}/image.tar" >"${output_root}/image.tar.sha256"

python3 - "${output_root}" "${image_id}" "${image_repo_digest}" "${SLURM_JOB_ID}" <<'PY'
import hashlib
import json
import os
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
image_id, image_repo_digest, job_id = sys.argv[2:]
artifacts = {}
for name in (
    "batch-script.sha256",
    "contained-import-doctor.json",
    "docker-pull.log",
    "gpu.csv",
    "image-inspect.json",
    "image.tar",
    "image.tar.sha256",
    "vllm-serve-help.txt",
):
    path = root / name
    artifacts[name] = {
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "size": path.stat().st_size,
    }
receipt = {
    "schema_version": 1,
    "status": "PAST_VLLM_DISCOVERY_IMAGE_ACQUIRED_NOT_SCIENTIFIC_RESULT",
    "scientific_result": False,
    "publication_ready": False,
    "slurm_job_id": job_id,
    "cuda_visible_devices": os.environ["CUDA_VISIBLE_DEVICES"],
    "image_id": image_id,
    "image_repo_digest": image_repo_digest,
    "platform": "linux/amd64",
    "artifacts": artifacts,
    "remaining_gates": [
        "scanner-produced image-bound SBOM",
        "same-job internal-network model transport doctor",
        "native Qwen XML-to-OpenAI tool-call doctor",
        "fresh-job PAST checkpoint continuation equivalence",
    ],
}
payload = json.dumps(receipt, indent=2, sort_keys=True).encode() + b"\n"
temporary = root / f".acquisition-receipt.{os.getpid()}.tmp"
with temporary.open("xb") as stream:
    stream.write(payload)
    stream.flush()
    os.fsync(stream.fileno())
os.link(temporary, root / "acquisition-receipt.json")
temporary.unlink()
PY

echo "PAST_VLLM_DISCOVERY_IMAGE_ACQUISITION_PASS image=${image_id} root=${output_root}"
