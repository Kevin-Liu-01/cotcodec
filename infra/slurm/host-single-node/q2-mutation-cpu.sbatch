#!/usr/bin/env bash
#SBATCH --job-name=cotcodec-q2-mutation-cpu
#SBATCH --partition=research
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=96G
#SBATCH --time=06:00:00
#SBATCH --output=/home/kevin/cotcodec-runs/stage0/q2-evaluator-mutation/slurm/slurm-%x-%j.out

# CPU-only Slurm entry point for the Q2 evaluator-mutation harness (decision D12).
#
# * No GRES is requested; the job refuses to start if Slurm assigned a GPU.
# * Containers are launched without --gpus and without --device. A preflight
#   container run asserts that no /dev/nvidia* node is visible, and the result
#   goes into the receipt. GPU device files are world-writable on this host, so
#   this assertion is the guard, not a formality.
# * Runtime containers use --network=none (D13: no new Docker networks), a
#   read-only root filesystem, no Linux capabilities, the caller's uid:gid, and
#   only the mounts named below.
# * Image builds use --network=host because the default bridge has no DNS
#   (docs/h100-node.md); build receipts record the Dockerfile and context hashes.
#
# Modes (Q2M_MODE):
#   build  Q2M_CONTEXT=<dir with Dockerfile>  Q2M_TAG=<name:tag>
#   run    Q2M_IMAGE_ID=sha256:<64 hex>  Q2M_ARGV_JSON_HEX=<hex of JSON argv>
#          Q2M_SOURCE=<code dir, ro at /src>  Q2M_RUN_DIR=<output dir, rw at /out>
#          optional Q2M_INPUTS=<dir, ro at /inputs>
#          optional Q2M_EXTRA_RO="<host>:<container>[,<host>:<container>...]"
#          optional Q2M_TMPFS_SIZE (default 32g)
set -Eeuo pipefail
umask 022

: "${SLURM_JOB_ID:?Run this script through sbatch}"
: "${Q2M_MODE:?Set Q2M_MODE to build or run}"

run_root="/home/kevin/cotcodec-runs/stage0/q2-evaluator-mutation"
receipt_dir="${run_root}/receipts"
mkdir -p "${receipt_dir}"

for var in SLURM_JOB_GPUS SLURM_STEP_GPUS SLURM_GPUS SLURM_GPUS_ON_NODE CUDA_VISIBLE_DEVICES; do
  value="${!var:-}"
  if [[ -n "${value}" && "${value}" != "0" ]]; then
    echo "refusing: ${var}=${value}; this job must hold no GPU" >&2
    exit 2
  fi
done

check_path() {
  local value="$1"
  if [[ ! "${value}" =~ ^/home/kevin/cotcodec-runs/stage0/[A-Za-z0-9._/-]+$ ]] || [[ "${value}" == *..* ]]; then
    echo "path outside the stage0 run root or unsafe: ${value}" >&2
    exit 2
  fi
}

started_at="$(date -u +%FT%TZ)"
batch_sha256="$(sha256sum "$0" | cut -d' ' -f1)"

if [[ "${Q2M_MODE}" == "build" ]]; then
  : "${Q2M_CONTEXT:?}" "${Q2M_TAG:?}"
  check_path "${Q2M_CONTEXT}"
  if [[ ! "${Q2M_TAG}" =~ ^cotcodec-q2-[a-z0-9.-]+:[A-Za-z0-9._-]+$ ]]; then
    echo "tag must be cotcodec-q2-<name>:<tag>" >&2
    exit 2
  fi
  dockerfile_sha256="$(sha256sum "${Q2M_CONTEXT}/Dockerfile" | cut -d' ' -f1)"
  context_sha256="$(cd "${Q2M_CONTEXT}" && find . -type f ! -name '*.log' -print0 | LC_ALL=C sort -z \
    | xargs -0 sha256sum | sha256sum | cut -d' ' -f1)"
  log="${receipt_dir}/build-${SLURM_JOB_ID}.log"
  docker build --pull=false --network=host --progress=plain \
    -t "${Q2M_TAG}" "${Q2M_CONTEXT}" >"${log}" 2>&1
  image_id="$(docker image inspect --format '{{.Id}}' "${Q2M_TAG}")"
  cat >"${receipt_dir}/build-${SLURM_JOB_ID}.json" <<JSON
{
  "job_id": "${SLURM_JOB_ID}",
  "mode": "build",
  "tag": "${Q2M_TAG}",
  "image_id": "${image_id}",
  "dockerfile_sha256": "${dockerfile_sha256}",
  "context_files_sha256": "${context_sha256}",
  "batch_sha256": "${batch_sha256}",
  "network_during_build": "host",
  "started_at": "${started_at}",
  "finished_at": "$(date -u +%FT%TZ)"
}
JSON
  cat "${receipt_dir}/build-${SLURM_JOB_ID}.json"
  exit 0
fi

if [[ "${Q2M_MODE}" != "run" ]]; then
  echo "unknown Q2M_MODE ${Q2M_MODE}" >&2
  exit 2
fi

: "${Q2M_IMAGE_ID:?}" "${Q2M_ARGV_JSON_HEX:?}" "${Q2M_SOURCE:?}" "${Q2M_RUN_DIR:?}"
if [[ ! "${Q2M_IMAGE_ID}" =~ ^sha256:[0-9a-f]{64}$ ]]; then
  echo "Q2M_IMAGE_ID must be an exact local image ID" >&2
  exit 2
fi
check_path "${Q2M_SOURCE}"
check_path "${Q2M_RUN_DIR}"
mkdir -p "${Q2M_RUN_DIR}"

mapfile -d '' -t argv < <(python3 - "${Q2M_ARGV_JSON_HEX}" <<'PY'
import json
import sys

argv = json.loads(bytes.fromhex(sys.argv[1]))
if not isinstance(argv, list) or not argv or not all(isinstance(a, str) for a in argv):
    raise SystemExit("argv must be a non-empty JSON list of strings")
sys.stdout.write("\0".join(argv) + "\0")
PY
)

mounts=(-v "${Q2M_SOURCE}:/src:ro" -v "${Q2M_RUN_DIR}:/out:rw")
mount_log="${Q2M_SOURCE}:/src:ro ${Q2M_RUN_DIR}:/out:rw"
if [[ -n "${Q2M_INPUTS:-}" ]]; then
  check_path "${Q2M_INPUTS}"
  mounts+=(-v "${Q2M_INPUTS}:/inputs:ro")
  mount_log+=" ${Q2M_INPUTS}:/inputs:ro"
fi
if [[ -n "${Q2M_EXTRA_RO:-}" ]]; then
  IFS=',' read -r -a extra <<<"${Q2M_EXTRA_RO}"
  for pair in "${extra[@]}"; do
    host="${pair%%:*}"
    target="${pair#*:}"
    check_path "${host}"
    if [[ ! "${target}" =~ ^/ro/[A-Za-z0-9._-]+$ ]]; then
      echo "extra mounts go under /ro/<name>: ${target}" >&2
      exit 2
    fi
    mounts+=(-v "${host}:${target}:ro")
    mount_log+=" ${host}:${target}:ro"
  done
fi

common=(
  --rm --init
  --network=none
  --user "$(id -u):$(id -g)"
  --cap-drop=ALL
  --security-opt=no-new-privileges
  --read-only
  --tmpfs "/tmp:rw,exec,size=${Q2M_TMPFS_SIZE:-32g}"
  --tmpfs /var/tmp:rw,size=1g
  --pids-limit=8192
  --cpus="${SLURM_CPUS_PER_TASK:-32}"
  --memory="$(( ${SLURM_MEM_PER_NODE:-98304} ))m"
  -e HOME=/tmp/home
  -e Q2M_SLURM_JOB_ID="${SLURM_JOB_ID}"
)

# D12 guard: the container must see no NVIDIA device node.
nvidia_nodes="$(docker run "${common[@]}" --entrypoint /bin/sh "${Q2M_IMAGE_ID}" \
  -c 'ls -1 /dev/nvidia* 2>/dev/null || true')"
if [[ -n "${nvidia_nodes}" ]]; then
  echo "refusing: container sees NVIDIA device nodes: ${nvidia_nodes}" >&2
  exit 3
fi

set +e
docker run "${common[@]}" "${mounts[@]}" -w /src \
  -e Q2M_RUN_DIR=/out \
  "${Q2M_IMAGE_ID}" "${argv[@]}"
status=$?
set -e

argv_sha256="$(printf '%s' "${Q2M_ARGV_JSON_HEX}" | sha256sum | cut -d' ' -f1)"
cat >"${receipt_dir}/run-${SLURM_JOB_ID}.json" <<JSON
{
  "job_id": "${SLURM_JOB_ID}",
  "mode": "run",
  "image_id": "${Q2M_IMAGE_ID}",
  "argv_json_hex_sha256": "${argv_sha256}",
  "argv_json_hex": "${Q2M_ARGV_JSON_HEX}",
  "mounts": "${mount_log}",
  "network": "none",
  "gpus_requested": 0,
  "container_dev_nvidia": [],
  "batch_sha256": "${batch_sha256}",
  "exit_status": ${status},
  "started_at": "${started_at}",
  "finished_at": "$(date -u +%FT%TZ)"
}
JSON
cp "${receipt_dir}/run-${SLURM_JOB_ID}.json" "${Q2M_RUN_DIR}/receipt-${SLURM_JOB_ID}.json"
exit "${status}"
