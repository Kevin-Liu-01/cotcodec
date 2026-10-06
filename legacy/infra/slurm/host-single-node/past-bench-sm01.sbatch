#!/usr/bin/env bash
#SBATCH --job-name=past-sm01
#SBATCH --partition=research
#SBATCH --gres=gpu:h100:2
#SBATCH --cpus-per-task=32
#SBATCH --mem=160G
#SBATCH --time=01:30:00
#SBATCH --signal=B:USR1@180
#SBATCH --output=/home/kevin/cotcodec-runs/past-bench/sm01-slurm-%j.out
#SBATCH --error=/home/kevin/cotcodec-runs/past-bench/sm01-slurm-%j.err

set -Eeuo pipefail
umask 077

if [[ $# -ne 8 ]]; then
  echo "usage: $0 MANIFEST FILE_SHA SEMANTIC_SHA OUTPUT MODE TOOLS_ROOT TOOLS_SHA BATCH_SHA" >&2
  exit 2
fi

manifest_source=$1
manifest_file_sha256=$2
manifest_sha256=$3
output_root=$4
mode=$5
tools_root=$6
tools_root_sha256=$7
expected_batch_sha256=$8

past_image_id='sha256:ebcf7eea7f1977f03e5e007edf265fcd120edadcd6d48e81f63df70715783150'
past_archive='/home/kevin/cotcodec-runs/past-bench/build-20260814-checkpoint-d4945b33-v1/image.tar'
past_archive_sha256='2f97fa8c18528eff8fd2e335e851255be280a20d2a3a81f74eab7485c0db285b'
past_sbom='/home/kevin/cotcodec-runs/past-bench/sbom-20260814-checkpoint-ebcf7eea-v2/sbom.spdx.json'
past_sbom_sha256='37f7eb4eab884c7d924e718f9ed8389102a61fe43b36d48e29249996bf857fff'
vllm_image_id='sha256:f26809eb13339cbc59c3d0cc972f8c4997830dc8d2121cf18089cb122834e10d'
vllm_archive='/home/kevin/cotcodec-runs/past-bench/vllm-acquire-v0251-f0b9-v5/image.tar'
vllm_archive_sha256='aecb8b90cd6378c1440c60efd3eef1d98d189e47110539350858dfde2ec9d0f4'
vllm_sbom='/home/kevin/cotcodec-runs/past-bench/vllm-sbom-v0251-f0b9-v3/sbom.spdx.json'
vllm_sbom_sha256='3b87e628da75256fa7cfc0c33377af62707775a3606cf9be8c044e81952dcb48'
vllm_sbom_receipt='/home/kevin/cotcodec-runs/past-bench/vllm-sbom-v0251-f0b9-v3/sbom-job-receipt.json'
vllm_sbom_receipt_sha256='49ec867957af7c538eab7174e9e18698ff872adaf00936d5461f986ed6ab35ef'
model_root='/home/kevin/cotcodec-runs/past-bench/model-transport-qwen36-35b-c46153-v4/model-snapshot'
model_receipt='/home/kevin/cotcodec-runs/hf-cache/cotcodec-receipts/qwen3.6-35b-a3b.json'
model_receipt_sha256='18c2a12881bf613c7110439b8e765ff89a4c060a1fb60aee62bb7250890ce1f9'
model_snapshot_receipt='/home/kevin/cotcodec-runs/past-bench/model-transport-qwen36-35b-c46153-v4/private-model-snapshot-receipt.json'
model_snapshot_receipt_sha256='cf207899913f7efe2250599a9672fa6e9b8cec1e574c90d61372583cb2679910'

: "${SLURM_JOB_ID:?PAST SM01 must execute inside Slurm}"
: "${CUDA_VISIBLE_DEVICES:?Slurm did not map the H100s}"
: "${SLURM_JOB_GPUS:?Slurm did not expose the physical H100s}"
runtime_uid=$(id -u)
runtime_gid=$(id -g)
runtime_identity="${runtime_uid}:${runtime_gid}"
if [[ ${runtime_uid} == 0 || ${runtime_gid} == 0 \
  || ! ${manifest_file_sha256} =~ ^[0-9a-f]{64}$ \
  || ! ${manifest_sha256} =~ ^[0-9a-f]{64}$ \
  || ! ${tools_root_sha256} =~ ^[0-9a-f]{64}$ \
  || ! ${expected_batch_sha256} =~ ^[0-9a-f]{64}$ \
  || ! ${manifest_source} =~ ^/home/kevin/cotcodec-runs/past-bench/inputs/past-sm01-[a-z0-9._/-]{1,300}[.]json$ \
  || ! ${output_root} =~ ^/home/kevin/cotcodec-runs/past-bench/sm01-[a-z0-9._-]{1,96}$ \
  || ! ${tools_root} =~ ^/home/kevin/cotcodec-runs/past-bench/inputs/past-sm01-tools-[0-9a-f]{64}$ \
  || ! ${mode} =~ ^(uninterrupted|stop-after-episode-three|fresh-job-resume)$ ]]; then
  echo "unsafe PAST SM01 argument" >&2
  exit 2
fi
IFS=, read -r -a allocated_gpus <<<"${SLURM_JOB_GPUS}"
if [[ ${#allocated_gpus[@]} -ne 2 || ${SLURM_GPUS_ON_NODE:-} != 2 \
  || ! -f ${manifest_source} || -L ${manifest_source} \
  || ! -d ${tools_root} || -L ${tools_root} ]]; then
  echo "invalid PAST SM01 allocation or input" >&2
  exit 2
fi
if [[ ${mode} == fresh-job-resume ]]; then
  if [[ ! -d ${output_root} || -L ${output_root} ]]; then
    echo "resume output root is missing or unsafe" >&2
    exit 2
  fi
else
  if [[ -e ${output_root} || -L ${output_root} ]]; then
    echo "new PAST SM01 output root already exists" >&2
    exit 2
  fi
  mkdir -m 0700 "${output_root}"
fi

mapfile -t allocated_gpu_uuids < <(
  nvidia-smi -i "${SLURM_JOB_GPUS}" --query-gpu=uuid --format=csv,noheader
)
mapfile -t allocated_gpu_names < <(
  nvidia-smi -i "${SLURM_JOB_GPUS}" --query-gpu=name --format=csv,noheader
)
if [[ ${#allocated_gpu_uuids[@]} -ne 2 || ${#allocated_gpu_names[@]} -ne 2 \
  || ${allocated_gpu_uuids[0]} == "${allocated_gpu_uuids[1]}" \
  || ${allocated_gpu_names[0]} != *H100* || ${allocated_gpu_names[1]} != *H100* ]]; then
  echo "PAST SM01 requires exactly two Slurm-owned H100s" >&2
  exit 2
fi
allocated_gpu_uuid_csv=$(IFS=,; echo "${allocated_gpu_uuids[*]}")
allocation_line=$(scontrol show job -o "${SLURM_JOB_ID}")
expected_time_limit='01:30:00'
if [[ ${mode} == stop-after-episode-three ]]; then
  expected_time_limit='00:30:00'
fi
if [[ ${allocation_line} != *"TimeLimit=${expected_time_limit}"* ]]; then
  echo "PAST SM01 Slurm time limit exceeds or differs from its registered budget" >&2
  exit 2
fi
printf '%s\n' "${allocation_line}" >"${output_root}/allocation-${mode}.txt"

registered_batch="${tools_root}/infra/slurm/host-single-node/past-bench-sm01.sbatch"
if [[ ! -f ${registered_batch} || -L ${registered_batch} \
  || $(sha256sum "${registered_batch}" | cut -d' ' -f1) != ${expected_batch_sha256} \
  || $(sha256sum "$0" | cut -d' ' -f1) != ${expected_batch_sha256} ]]; then
  echo "active PAST SM01 batch drifted" >&2
  exit 2
fi

actual_tools_root=$(python3 - "${tools_root}" <<'PY'
import hashlib
import json
import pathlib
import sys
root = pathlib.Path(sys.argv[1])
expected = {
    "infra/research/past-bench/model_transport_doctor.py",
    "infra/research/past-bench/prepare_hermes_offline_bootstrap.py",
    "infra/research/past-bench/sm01-runtime.yaml",
    "infra/research/past-bench/sm01_job_doctor.py",
    "infra/research/past-bench/verify_model_snapshot.py",
    "infra/slurm/host-single-node/past-bench-sm01.sbatch",
}
rows = []
for path in sorted(root.rglob("*")):
    if path.is_symlink() or (not path.is_file() and not path.is_dir()):
        raise SystemExit("unsupported PAST SM01 tool entry")
    if path.is_file():
        relative = path.relative_to(root).as_posix()
        if relative not in expected:
            raise SystemExit(f"unregistered PAST SM01 tool: {relative}")
        payload = path.read_bytes()
        rows.append({"path": relative, "sha256": hashlib.sha256(payload).hexdigest(), "size": len(payload)})
if {row["path"] for row in rows} != expected:
    raise SystemExit("PAST SM01 tool roster is incomplete")
print(hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest())
PY
)
if [[ ${actual_tools_root} != ${tools_root_sha256} ]]; then
  echo "PAST SM01 tool bundle drifted" >&2
  exit 2
fi

verify_regular_digest() {
  local path=$1
  local expected=$2
  if [[ ! -f ${path} || -L ${path} \
    || $(sha256sum "${path}" | cut -d' ' -f1) != ${expected} ]]; then
    echo "PAST SM01 evidence drifted: ${path}" >&2
    exit 2
  fi
}
verify_regular_digest "${manifest_source}" "${manifest_file_sha256}"
verify_regular_digest "${past_archive}" "${past_archive_sha256}"
verify_regular_digest "${past_sbom}" "${past_sbom_sha256}"
verify_regular_digest "${vllm_archive}" "${vllm_archive_sha256}"
verify_regular_digest "${vllm_sbom}" "${vllm_sbom_sha256}"
verify_regular_digest "${vllm_sbom_receipt}" "${vllm_sbom_receipt_sha256}"
verify_regular_digest "${model_receipt}" "${model_receipt_sha256}"
verify_regular_digest "${model_snapshot_receipt}" "${model_snapshot_receipt_sha256}"
if [[ ! -d ${model_root} || -L ${model_root} ]]; then
  echo "retained model snapshot is missing or unsafe" >&2
  exit 2
fi

evidence_root="${output_root}/evidence"
run_root="${output_root}/run"
state_root="${output_root}/state"
for directory in "${evidence_root}" "${run_root}" "${state_root}"; do
  if [[ -L ${directory} ]]; then
    echo "PAST SM01 output subdirectory cannot be a symlink" >&2
    exit 2
  fi
  mkdir -p -m 0700 "${directory}"
  if [[ $(realpath "${directory}") != "${output_root}"/* ]]; then
    echo "PAST SM01 output subdirectory escapes its run root" >&2
    exit 2
  fi
done
manifest="${evidence_root}/manifest-${mode}.json"
if [[ -e ${manifest} || -L ${manifest} ]]; then
  echo "refusing to overwrite PAST SM01 manifest evidence" >&2
  exit 2
fi
cp --reflink=never --no-preserve=mode,ownership,timestamps "${manifest_source}" "${manifest}"
chmod 0400 "${manifest}"

docker load --input "${past_archive}" >"${evidence_root}/past-image-load-${mode}.txt"
docker load --input "${vllm_archive}" >"${evidence_root}/vllm-image-load-${mode}.txt"
if [[ $(docker image inspect --format '{{.Id}}' "${past_image_id}") != ${past_image_id} \
  || $(docker image inspect --format '{{.Id}}' "${vllm_image_id}") != ${vllm_image_id} ]]; then
  echo "PAST or vLLM live image ID drifted" >&2
  exit 2
fi
docker image inspect "${past_image_id}" >"${evidence_root}/past-image-inspect-${mode}.json"
docker image inspect "${vllm_image_id}" >"${evidence_root}/vllm-image-inspect-${mode}.json"
nvidia-smi -i "${SLURM_JOB_GPUS}" --query-gpu=name,uuid,driver_version --format=csv,noheader \
  >"${evidence_root}/gpu-inventory-${mode}.txt"

doctor_common=(
  run --rm --pull=never --read-only
  --tmpfs /tmp:rw,exec,nosuid,nodev,size=2g
  --cap-drop ALL --security-opt no-new-privileges --pids-limit 1024
  --user "${runtime_identity}" --env USER=cotcodec --env LOGNAME=cotcodec
  --env HOME=/tmp/home --env PYTHONPATH=/tools
  --volume "${tools_root}:/tools:ro"
)
docker "${doctor_common[@]}" --network none \
  --volume "${manifest}:/input/manifest.json:ro" \
  --volume "${evidence_root}:/evidence:rw" \
  --volume "${run_root}:/run:rw" \
  --entrypoint /opt/past-bench-venv/bin/python \
  "${past_image_id}" /tools/infra/research/past-bench/sm01_job_doctor.py preflight \
  --manifest /input/manifest.json --manifest-sha256 "${manifest_sha256}" \
  --mode "${mode}" --run-root /run --evidence-root /evidence \
  --slurm-job-id "${SLURM_JOB_ID}"

docker "${doctor_common[@]}" --network none \
  --volume "${state_root}:/state:rw" \
  --workdir /opt/past-bench/source \
  --entrypoint /opt/past-bench-venv/bin/python "${past_image_id}" -c \
  'import json,pathlib; from past_bench.config import load_config; c=load_config("/tools/infra/research/past-bench/sm01-runtime.yaml"); assert c.runtime.mode=="local" and c.runtime.cache_dir=="/state/runtime_cache" and c.runtime.registry_path=="configs/agents.yaml"; p=pathlib.Path(c.runtime.cache_dir); p.mkdir(parents=True,exist_ok=True); q=p/".cotcodec-write-probe"; q.write_text("ok"); q.unlink(); print(json.dumps({"cache_dir":str(p),"mode":c.runtime.mode,"registry_path":c.runtime.registry_path,"status":"PAST_SM01_RUNTIME_CONFIG_PASS"},sort_keys=True))' \
  >"${evidence_root}/runtime-config-doctor-${mode}.json"

docker "${doctor_common[@]}" --network none \
  --volume "${state_root}:/state:rw" --volume "${evidence_root}:/evidence:rw" \
  --workdir /opt/past-bench/source \
  --entrypoint /opt/past-bench-venv/bin/python "${past_image_id}" \
  /tools/infra/research/past-bench/prepare_hermes_offline_bootstrap.py \
  --config /tools/infra/research/past-bench/sm01-runtime.yaml \
  --cache-dir /state/runtime_cache \
  --output "/evidence/hermes-offline-bootstrap-${mode}.json"

docker "${doctor_common[@]}" --network none \
  --volume "${model_root}:/model:ro" \
  --volume "${model_receipt}:/input/model-receipt.json:ro" \
  --volume "${model_snapshot_receipt}:/input/snapshot-receipt.json:ro" \
  --volume "${evidence_root}:/evidence:rw" \
  --entrypoint python3 "${vllm_image_id}" \
  /tools/infra/research/past-bench/verify_model_snapshot.py \
  --root /model --receipt /input/model-receipt.json \
  --snapshot-receipt /input/snapshot-receipt.json \
  --output "/evidence/model-snapshot-verification-${mode}.json"

network_name="past-sm01-${SLURM_JOB_ID}"
server_name="past-qwen-${SLURM_JOB_ID}"
past_name="past-sm01-client-${SLURM_JOB_ID}"
network_created=false
server_created=false
past_created=false
past_log_pid=''
termination_reason=running
signal_requested=false

cleanup() {
  local exit_code=$?
  trap - EXIT USR1 TERM
  if [[ -n ${past_log_pid} ]]; then
    wait "${past_log_pid}" >/dev/null 2>&1 || true
  fi
  if ${past_created}; then
    docker rm --force "${past_name}" >/dev/null 2>&1 || true
  fi
  if ${server_created}; then
    docker logs "${server_name}" >"${evidence_root}/server-${mode}.log" 2>&1 || true
    docker rm --force "${server_name}" >/dev/null 2>&1 || true
  fi
  if ${network_created}; then
    docker network rm "${network_name}" >/dev/null 2>&1 || true
  fi
  printf 'exit_code=%s\ntermination_reason=%s\nsignal_requested=%s\n' \
    "${exit_code}" "${termination_reason}" "${signal_requested}" \
    >"${evidence_root}/termination-${mode}.txt"
  exit "${exit_code}"
}
checkpoint_signal() {
  signal_requested=true
  termination_reason=slurm_signal_checkpoint_requested
  if ${past_created}; then
    docker kill --signal=USR1 "${past_name}" >/dev/null
  fi
}
trap cleanup EXIT
trap checkpoint_signal USR1 TERM

docker network create --internal "${network_name}" >"${evidence_root}/network-id-${mode}.txt"
network_created=true
docker network inspect "${network_name}" >"${evidence_root}/network-inspect-${mode}.json"

cpu_list=$(python3 - <<'PY'
import os
print(",".join(str(item) for item in sorted(os.sched_getaffinity(0))))
PY
)
docker_gpu_request="\"device=${allocated_gpu_uuid_csv}\""
docker run --rm --pull=never --gpus "${docker_gpu_request}" --network none \
  --read-only --tmpfs /tmp:rw,exec,nosuid,nodev,size=2g \
  --cap-drop ALL --security-opt no-new-privileges --pids-limit 2048 \
  --cpuset-cpus "${cpu_list}" --ulimit core=0 \
  --user "${runtime_identity}" --env COTCODEC_EXPECTED_GPU_UUIDS="${allocated_gpu_uuid_csv}" \
  --entrypoint python3 "${vllm_image_id}" -c \
  'import json,os,subprocess,torch; u=subprocess.check_output(["nvidia-smi","--query-gpu=uuid","--format=csv,noheader"],text=True).strip().splitlines(); assert torch.cuda.device_count()==2 and u==os.environ["COTCODEC_EXPECTED_GPU_UUIDS"].split(","); print(json.dumps({"count":2,"names":[torch.cuda.get_device_name(i) for i in range(2)],"uuids":u},sort_keys=True))' \
  >"${evidence_root}/container-gpu-doctor-${mode}.json"

mapfile -d '' -t server_argv < <(
  python3 - "${manifest}" <<'PY'
import json
import sys
for item in json.load(open(sys.argv[1], encoding="utf-8"))["server_argv"]:
    sys.stdout.buffer.write(item.encode() + b"\0")
PY
)
server_command=("${server_argv[@]:1}")
docker create --name "${server_name}" --hostname past-qwen \
  --network "${network_name}" --network-alias past-qwen \
  --entrypoint vllm --gpus "${docker_gpu_request}" --read-only \
  --tmpfs /tmp:rw,exec,nosuid,nodev,size=16g --shm-size 16g \
  --cap-drop ALL --security-opt no-new-privileges --pids-limit 8192 \
  --cpuset-cpus "${cpu_list}" --memory 150g --memory-swap 150g --ulimit core=0 \
  --user "${runtime_identity}" --workdir /tmp \
  --env USER=cotcodec --env LOGNAME=cotcodec --env HOME=/tmp/home \
  --env XDG_CACHE_HOME=/tmp/cache --env TORCHINDUCTOR_CACHE_DIR=/tmp/torchinductor \
  --env HF_HUB_OFFLINE=1 --env TRANSFORMERS_OFFLINE=1 \
  --env CUBLAS_WORKSPACE_CONFIG=:4096:8 --env PYTHONHASHSEED=42 \
  --volume "${model_root}:/models/qwen3.6-35b-a3b:ro" \
  --volume "${model_receipt}:/model-receipt.json:ro" \
  "${vllm_image_id}" "${server_command[@]}" >"${evidence_root}/server-container-id-${mode}.txt"
server_created=true
docker start "${server_name}" >/dev/null

ready=false
for _attempt in $(seq 1 180); do
  if docker run --rm --pull=never --network "${network_name}" --read-only \
    --tmpfs /tmp:rw,noexec,nosuid,nodev,size=64m --cap-drop ALL \
    --security-opt no-new-privileges --pids-limit 64 --user "${runtime_identity}" \
    --entrypoint /opt/past-bench-venv/bin/python "${past_image_id}" -c \
    'import json,urllib.request; r=urllib.request.Request("http://past-qwen:8000/v1/models",headers={"Authorization":"Bearer cotcodec-internal-transport"}); x=json.load(urllib.request.urlopen(r,timeout=5)); assert [i["id"] for i in x["data"]]==["qwen3.6-35b-a3b"]' \
    >/dev/null 2>&1; then
    ready=true
    break
  fi
  sleep 2
done
if ! ${ready}; then
  echo "PAST Qwen server did not become ready" >&2
  exit 2
fi

docker "${doctor_common[@]}" --network "${network_name}" \
  --volume "${evidence_root}:/evidence:rw" \
  --entrypoint /opt/past-bench-venv/bin/python "${past_image_id}" \
  /tools/infra/research/past-bench/model_transport_doctor.py \
  --base-url http://past-qwen:8000/v1 --api-key cotcodec-internal-transport \
  --model qwen3.6-35b-a3b --output "/evidence/model-transport-doctor-${mode}.json"

docker exec "${server_name}" python3 -c \
  'import socket; targets=[("1.1.1.1",443),("8.8.8.8",53)]; s=lambda: socket.socket(); sockets=[s() for _ in targets]; [x.settimeout(1) for x in sockets]; assert all(x.connect_ex(t)!=0 for x,t in zip(sockets,targets)); [x.close() for x in sockets]' \
  >"${evidence_root}/server-egress-doctor-${mode}.txt"

mapfile -d '' -t workload_argv < <(
  python3 - "${manifest}" <<'PY'
import json
import sys
x=json.load(open(sys.argv[1], encoding="utf-8"))
for item in x["logical_workload_argv"][1:] + x["actual_control_argv_suffix"]:
    sys.stdout.buffer.write(item.encode() + b"\0")
PY
)
docker create --name "${past_name}" --hostname past-sm01 \
  --network "${network_name}" --read-only \
  --tmpfs /tmp:rw,exec,nosuid,nodev,size=4g --shm-size 2g \
  --cap-drop ALL --security-opt no-new-privileges --pids-limit 4096 \
  --cpuset-cpus "${cpu_list}" --memory 8g --memory-swap 8g --ulimit core=0 \
  --user "${runtime_identity}" --workdir /opt/past-bench/source \
  --env USER=cotcodec --env LOGNAME=cotcodec --env HOME=/state/home \
  --env PYTHONHASHSEED=42 --env HF_HUB_OFFLINE=1 --env TRANSFORMERS_OFFLINE=1 \
  --env NO_PROXY=localhost,127.0.0.1,past-qwen --env no_proxy=localhost,127.0.0.1,past-qwen \
  --env COTCODEC_CHECKPOINT_MARKER=/outputs/checkpoint.ready \
  --volume "${tools_root}:/tools:ro" \
  --volume "${run_root}:/outputs:rw" --volume "${state_root}:/state:rw" \
  --volume "${evidence_root}/execution-identity.json:/inputs/execution-identity.json:ro" \
  "${past_image_id}" "${workload_argv[@]}" >"${evidence_root}/past-container-id-${mode}.txt"
past_created=true
docker start -a "${past_name}" >"${evidence_root}/past-${mode}.stdout" \
  2>"${evidence_root}/past-${mode}.stderr" &
past_log_pid=$!
set +e
while kill -0 "${past_log_pid}" >/dev/null 2>&1; do
  wait "${past_log_pid}"
  wait_status=$?
  if kill -0 "${past_log_pid}" >/dev/null 2>&1; then
    continue
  fi
  break
done
set -e
past_log_pid=''
past_exit=$(docker inspect --format '{{.State.ExitCode}}' "${past_name}")
if [[ ${past_exit} -ne 0 ]]; then
  termination_reason=past_workload_failed
  echo "PAST SM01 workload exited ${past_exit}" >&2
  exit "${past_exit}"
fi

termination_reason=artifact_finalization_failed
docker "${doctor_common[@]}" --network none \
  --volume "${evidence_root}:/evidence:rw" --volume "${run_root}:/run:rw" \
  --entrypoint /opt/past-bench-venv/bin/python "${past_image_id}" \
  /tools/infra/research/past-bench/sm01_job_doctor.py finalize \
  --mode "${mode}" --run-root /run --evidence-root /evidence \
  --slurm-job-id "${SLURM_JOB_ID}"

termination_reason=completed_discovery_cell
echo "PAST_SM01_DISCOVERY_CELL_PASS mode=${mode} root=${output_root}"
