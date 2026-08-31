#!/usr/bin/env bash
#SBATCH --job-name=orchvar-qwen35-two-stage
#SBATCH --partition=research
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:h100:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --time=00:30:00
#SBATCH --signal=B:USR1@120
#SBATCH --output=/home/kevin/cotcodec-runs/orchvar-live-smoke/slurm-%j.out
#SBATCH --error=/home/kevin/cotcodec-runs/orchvar-live-smoke/slurm-%j.err

set -Eeuo pipefail
umask 077

if [[ $# -ne 4 ]]; then
  echo "usage: $0 SOURCE_ROOT SOURCE_SHA256 OUTPUT_ROOT BATCH_SHA256" >&2
  exit 2
fi
source_root=$1
expected_source_sha256=$2
output_root=$3
expected_batch_sha256=$4
image_id='sha256:785f16e880d8c38acef02254adaccfb48dfd3a374af12115ec88590f036bf81a'
image_registry_digest='127.0.0.1:5000/cotcodec-research@sha256:3f58e5256dff74ed3017a00af125e6ee2b6e4745208b9ea8a3668633760dfb00'
model_cache='/home/kevin/cotcodec-runs/hf-cache'
model_id='qwen3.5-4b'
model_receipt_sha256='75ebfc531acdcbc0c39bbf83ee7bf5267a3ddf02c4fafdf6181624612a0d3082'
model_revision='851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a'
model_artifact_root='3b8a075149bffe4dea784db5b4b37bc0896688cba0b3de7d8d0f6e8ae6157b9e'

: "${SLURM_JOB_ID:?live smoke must execute inside Slurm}"
if [[ ! ${source_root} =~ ^/home/kevin/cotcodec-runs/orchvar-live-smoke/inputs/[0-9a-f]{64}$ \
  || ! ${expected_source_sha256} =~ ^[0-9a-f]{64}$ \
  || ${source_root##*/} != ${expected_source_sha256} \
  || ! ${output_root} =~ ^/home/kevin/cotcodec-runs/orchvar-live-smoke/runs/[a-z0-9._-]{1,96}$ \
  || ! ${expected_batch_sha256} =~ ^[0-9a-f]{64}$ \
  || ! -d ${source_root} || -L ${source_root} \
  || -e ${output_root} || -L ${output_root} ]]; then
  echo "unsafe live-smoke argument" >&2
  exit 2
fi
mkdir -m 0700 "${output_root}"
mkdir -m 0700 "${output_root}/evidence"

registered_batch="${source_root}/infra/slurm/host-single-node/orchvar-live-smoke.sbatch"
if [[ ! -f ${registered_batch} || -L ${registered_batch} \
  || $(sha256sum "$0" | cut -d' ' -f1) != ${expected_batch_sha256} \
  || $(sha256sum "${registered_batch}" | cut -d' ' -f1) != ${expected_batch_sha256} ]]; then
  echo "live-smoke batch script drifted" >&2
  exit 2
fi

python3 - "${source_root}" "${expected_source_sha256}" <<'PY'
import hashlib,json,pathlib,sys
root=pathlib.Path(sys.argv[1]); expected=sys.argv[2]
manifest=json.loads((root/"CAPSULE-MANIFEST.json").read_text(encoding="utf-8"))
rows=[]
for path in sorted(root.rglob("*")):
    if path.is_symlink() or (not path.is_file() and not path.is_dir()):
        raise SystemExit("unsafe capsule entry")
    if path.is_file() and path.name != "CAPSULE-MANIFEST.json":
        payload=path.read_bytes()
        rows.append({"path":path.relative_to(root).as_posix(),"sha256":hashlib.sha256(payload).hexdigest(),"size":len(payload)})
canonical=json.dumps(rows,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
actual=hashlib.sha256(canonical).hexdigest()
if manifest != {"schema_version":1,"capsule_type":"orchvar-live-smoke-source-v1","source_root_sha256":expected,"files":rows,"claim_status":"NON_SCIENTIFIC_LIVE_SMOKE"}:
    raise SystemExit("capsule manifest differs from extracted source")
if actual != expected:
    raise SystemExit("capsule source root drifted")
print(actual)
PY

model_snapshot="${model_cache}/cotcodec-models/${model_id}"
model_receipt="${model_cache}/cotcodec-receipts/${model_id}.json"
if [[ ! -d ${model_snapshot} || -L ${model_snapshot} \
  || ! -f ${model_receipt} || -L ${model_receipt} \
  || $(sha256sum "${model_receipt}" | cut -d' ' -f1) != ${model_receipt_sha256} ]]; then
  echo "pinned model snapshot or receipt drifted" >&2
  exit 2
fi
python3 - "${model_receipt}" "${model_revision}" "${model_artifact_root}" <<'PY'
import json,pathlib,sys
receipt=json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
expected={"model_id":"qwen3.5-4b","repo_id":"Qwen/Qwen3.5-4B","revision":sys.argv[2],"artifact_root_sha256":sys.argv[3],"mode":"full","publication_eligible":True,"trust_remote_code":False}
for key,value in expected.items():
    if receipt.get(key) != value: raise SystemExit(f"model receipt field {key} drifted")
PY

if ! command -v docker >/dev/null || ! docker info >/dev/null 2>&1; then
  echo "Docker is unavailable to the Slurm job user" >&2
  exit 2
fi
if [[ $(docker image inspect --format '{{.Id}}' "${image_id}") != ${image_id} ]]; then
  echo "Docker image ID drifted" >&2
  exit 2
fi
docker image inspect "${image_id}" >"${output_root}/evidence/image-inspect.json"
python3 - "${output_root}/evidence/image-inspect.json" "${image_registry_digest}" <<'PY'
import json,sys
payload=json.load(open(sys.argv[1],encoding="utf-8"))
if len(payload)!=1 or sys.argv[2] not in payload[0].get("RepoDigests",[]):
    raise SystemExit("registered image digest is absent from the exact image")
PY

gpu_devices="${CUDA_VISIBLE_DEVICES:-${SLURM_JOB_GPUS:-}}"
if [[ ! ${gpu_devices} =~ ^[0-7]$ ]] \
  || nvidia-smi -i "${gpu_devices}" --query-gpu=name --format=csv,noheader \
    | grep -qv 'H100'; then
  echo "Slurm did not allocate exactly one H100" >&2
  exit 2
fi
nvidia-smi -i "${gpu_devices}" -q >"${output_root}/evidence/nvidia-smi-q.txt"
env | LC_ALL=C sort >"${output_root}/evidence/slurm-environment.txt"

container_name="orchvar-live-${SLURM_JOB_ID}"
container_created=false
termination_reason=running

forward_signal() {
  termination_reason=usr1_checkpoint
  if [[ ${container_created} == true ]] \
    && [[ $(docker inspect --format '{{.State.Running}}' "${container_name}" 2>/dev/null || echo false) == true ]]; then
    docker kill --signal USR1 "${container_name}" >/dev/null 2>&1 || true
  fi
}

on_exit() {
  local exit_code=$?
  if [[ ${container_created} == true ]]; then
    docker inspect "${container_name}" >"${output_root}/evidence/container-final-inspect.json" 2>/dev/null || true
    docker logs "${container_name}" >"${output_root}/evidence/container.log" 2>&1 || true
    docker rm --force "${container_name}" >/dev/null 2>&1 || true
  fi
  if [[ ${termination_reason} == running ]]; then
    if [[ ${exit_code} -eq 0 ]]; then termination_reason=completed; else termination_reason=workload_failed; fi
  fi
  python3 - "${output_root}/evidence/termination.json" "${exit_code}" "${termination_reason}" <<'PY'
import json,pathlib,sys
pathlib.Path(sys.argv[1]).write_text(json.dumps({"schema_version":1,"exit_code":int(sys.argv[2]),"reason":sys.argv[3]},sort_keys=True,separators=(",",":"))+"\n",encoding="utf-8")
PY
}

trap forward_signal USR1
trap on_exit EXIT

runtime_identity="$(id -u):$(id -g)"
docker create \
  --name "${container_name}" \
  --entrypoint /bin/bash \
  --gpus "device=${gpu_devices}" \
  --network none \
  --read-only \
  --tmpfs /tmp:rw,exec,nosuid,nodev,size=8g \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  --pids-limit 4096 \
  --user "${runtime_identity}" \
  --workdir /workspace/capsule \
  --env HOME=/tmp/home \
  --env USER=cotcodec \
  --env LOGNAME=cotcodec \
  --env XDG_CACHE_HOME=/tmp/cache \
  --env HF_HOME=/tmp/huggingface \
  --env TORCH_HOME=/tmp/torch \
  --env TORCHINDUCTOR_CACHE_DIR=/tmp/torchinductor \
  --env HF_HUB_OFFLINE=1 \
  --env TRANSFORMERS_OFFLINE=1 \
  --env CUBLAS_WORKSPACE_CONFIG=:4096:8 \
  --env PYTHONUNBUFFERED=1 \
  --env PYTHONPATH=/workspace/capsule \
  --env COTCODEC_OUTPUT_DIR=/outputs \
  --env COTCODEC_MODEL_ROOT=/model-cache/cotcodec-models \
  --env COTCODEC_MODEL_RECEIPT_ROOT=/model-cache/cotcodec-receipts \
  --env COTCODEC_SOURCE_CAPSULE_ROOT="${expected_source_sha256}" \
  --env COTCODEC_IMAGE_ID="${image_id}" \
  --env SLURM_JOB_ID="${SLURM_JOB_ID}" \
  --env CUDA_VISIBLE_DEVICES=0 \
  --volume "${source_root}:/workspace/capsule:ro" \
  --volume "${model_cache}:/model-cache:ro" \
  --volume "${output_root}:/outputs:rw" \
  "${image_id}" \
  -c 'mkdir -p "$HOME" "$XDG_CACHE_HOME" "$HF_HOME" "$TORCH_HOME" "$TORCHINDUCTOR_CACHE_DIR" && exec /workspace/cotcodec/.venv/bin/python -m harness.two_stage_live_runner experiments/orchvar_qwen35_two_stage_live_smoke.yaml' \
  >"${output_root}/evidence/container-id.txt"
container_created=true
docker inspect "${container_name}" >"${output_root}/evidence/container-created-inspect.json"
set +e
docker start --attach "${container_name}"
workload_exit_code=$?
set -e
exit "${workload_exit_code}"
