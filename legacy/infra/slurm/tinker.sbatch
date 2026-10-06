#!/usr/bin/env bash
#SBATCH --job-name=cotcodec-tinker
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --signal=B:USR1@180
#SBATCH --output=slurm-%x-%j.out

set -Eeuo pipefail
umask 077

: "${COTCODEC_IMAGE:?Set an immutable OCI digest}"
: "${COTCODEC_COMMAND_JSON_HEX:?Set the hex-encoded JSON argv}"
: "${COTCODEC_MANIFEST_JSON_HEX:?Set the hex-encoded validated manifest}"
: "${COTCODEC_RUN_ROOT:?Set persistent job storage}"
: "${COTCODEC_GIT_SHA:?Set the committed source revision}"
: "${COTCODEC_SOURCE_SHA256:?Set the committed source archive digest}"
: "${COTCODEC_TINKER_CONTRACT:?Set the repository-relative Tinker contract}"
: "${COTCODEC_TINKER_CONTRACT_SHA256:?Set the Tinker contract digest}"
: "${COTCODEC_TRAIN_JSONL:?Set the persistent rendered-prefix training JSONL}"
: "${COTCODEC_TRAIN_SHA256:?Set the training JSONL digest}"
: "${TINKER_API_KEY:?TINKER_API_KEY must be injected by the cluster secret mechanism}"

if [[ ! "${COTCODEC_IMAGE}" =~ ^[A-Za-z0-9][A-Za-z0-9._:/-]*@sha256:[0-9a-f]{64}$ ]]; then
  echo "COTCODEC_IMAGE must contain a full immutable OCI digest" >&2
  exit 2
fi
if [[ ! "${COTCODEC_TINKER_CONTRACT}" =~ ^experiments/tinker/[a-z0-9][a-z0-9-]{0,63}\.yaml$ ]]; then
  echo "invalid Tinker contract path" >&2
  exit 2
fi
if ! srun --help 2>&1 | grep -q -- '--container-image'; then
  echo "Slurm Pyxis support is required" >&2
  exit 2
fi

run_dir="${COTCODEC_RUN_ROOT}/${SLURM_JOB_ID}"
mkdir -p "${run_dir}"
checkpoint_marker="${run_dir}/checkpoint.ready"
termination_file="${run_dir}/termination.env"
child_pid=""
termination_reason="starting"

write_termination() {
  local exit_code="$1"
  {
    echo "job_id=${SLURM_JOB_ID}"
    echo "predecessor_job_id=${COTCODEC_PREDECESSOR_JOB_ID:-none}"
    echo "reason=${termination_reason}"
    echo "exit_code=${exit_code}"
    echo "finished_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "checkpoint_ready=$([[ -f "${checkpoint_marker}" ]] && echo true || echo false)"
  } > "${termination_file}"
}

forward_signal() {
  local signal_name="$1"
  termination_reason="signal_${signal_name}_checkpoint_requested"
  if [[ -n "${child_pid}" ]] && kill -0 "${child_pid}" 2>/dev/null; then
    kill -s "${signal_name}" "${child_pid}" 2>/dev/null || true
  fi
  local waited=0
  while [[ ! -f "${checkpoint_marker}" && "${waited}" -lt 120 ]]; do
    sleep 2
    waited=$((waited + 2))
  done
  if [[ -f "${checkpoint_marker}" ]]; then
    termination_reason="signal_${signal_name}_checkpoint_confirmed"
  else
    termination_reason="signal_${signal_name}_checkpoint_timeout"
  fi
  if [[ -n "${child_pid}" ]] && kill -0 "${child_pid}" 2>/dev/null; then
    kill -TERM "${child_pid}" 2>/dev/null || true
  fi
}

on_exit() {
  local exit_code="$?"
  if [[ "${termination_reason}" == "running" ]]; then
    if [[ "${exit_code}" -eq 0 ]]; then
      termination_reason="completed"
    else
      termination_reason="workload_failed"
    fi
  fi
  write_termination "${exit_code}"
}

trap 'forward_signal USR1' USR1
trap 'forward_signal TERM' TERM
trap on_exit EXIT

python - "${run_dir}" <<'PY'
import json
import os
import pathlib
import sys

run_dir = pathlib.Path(sys.argv[1])
for name, key in (
    ("command.json", "COTCODEC_COMMAND_JSON_HEX"),
    ("manifest.json", "COTCODEC_MANIFEST_JSON_HEX"),
):
    value = json.loads(bytes.fromhex(os.environ[key]))
    (run_dir / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
PY

actual_contract_sha="$(sha256sum "${COTCODEC_TINKER_CONTRACT}" | cut -d' ' -f1)"
if [[ "${actual_contract_sha}" != "${COTCODEC_TINKER_CONTRACT_SHA256}" ]]; then
  echo "Tinker contract hash mismatch" >&2
  exit 2
fi
actual_train_sha="$(sha256sum "${COTCODEC_TRAIN_JSONL}" | cut -d' ' -f1)"
if [[ "${actual_train_sha}" != "${COTCODEC_TRAIN_SHA256}" ]]; then
  echo "Tinker training data hash mismatch" >&2
  exit 2
fi

{
  echo "job_id=${SLURM_JOB_ID}"
  echo "git_sha=${COTCODEC_GIT_SHA}"
  echo "source_sha256=${COTCODEC_SOURCE_SHA256}"
  echo "image=${COTCODEC_IMAGE}"
  echo "contract=${COTCODEC_TINKER_CONTRACT}"
  echo "contract_sha256=${actual_contract_sha}"
  echo "train_sha256=${actual_train_sha}"
  echo "started_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "nodelist=${SLURM_JOB_NODELIST}"
  echo "seeds=${COTCODEC_SEEDS:-unknown}"
  echo "run_seed=${COTCODEC_RUN_SEED:-unknown}"
} > "${run_dir}/job.env"
uname -a > "${run_dir}/system.txt"

image_ref="${COTCODEC_IMAGE#docker://}"
termination_reason="running"
export COTCODEC_OUTPUT_DIR=/outputs
export COTCODEC_CHECKPOINT_MARKER=/outputs/checkpoint.ready
export PYTHONUNBUFFERED=1

srun \
  --kill-on-bad-exit=1 \
  --container-image="docker://${image_ref}" \
  --container-mounts="${run_dir}:/outputs,${COTCODEC_TRAIN_JSONL}:/inputs/train.jsonl:ro" \
  --container-workdir=/workspace/cotcodec \
  bash -lc 'python scripts/verify_compute_provenance.py > /outputs/provenance-verification.txt && bash scripts/check_compute_env.sh container && python scripts/tinker_doctor.py "${COTCODEC_TINKER_CONTRACT}" --online --output /outputs/tinker-capabilities.json && exec python scripts/exec_research_workload.py' &
child_pid="$!"
wait "${child_pid}"
