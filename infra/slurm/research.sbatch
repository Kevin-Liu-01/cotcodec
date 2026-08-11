#!/usr/bin/env bash
#SBATCH --job-name=cotcodec
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gres=gpu:h100:1
#SBATCH --cpus-per-task=16
#SBATCH --mem=64G
#SBATCH --time=02:00:00
#SBATCH --signal=B:USR1@180
#SBATCH --output=slurm-%x-%j.out

set -Eeuo pipefail
umask 077

: "${COTCODEC_IMAGE:?Set an immutable OCI reference ending in @sha256:<64 hex>}"
: "${COTCODEC_COMMAND_JSON_HEX:?Set the hex-encoded JSON argv}"
: "${COTCODEC_MANIFEST_JSON_HEX:?Set the hex-encoded validated manifest}"
: "${COTCODEC_RUN_ROOT:?Set persistent job storage}"
: "${COTCODEC_GIT_SHA:?Set the committed 40-hex source revision}"
: "${COTCODEC_SOURCE_SHA256:?Set the 64-hex source archive digest}"

if [[ ! "${COTCODEC_IMAGE}" =~ ^[A-Za-z0-9][A-Za-z0-9._:/-]*@sha256:[0-9a-f]{64}$ ]]; then
  echo "COTCODEC_IMAGE must contain a full immutable OCI digest" >&2
  exit 2
fi
if [[ ! "${COTCODEC_GIT_SHA}" =~ ^[0-9a-f]{40}$ ]]; then
  echo "COTCODEC_GIT_SHA must be a committed 40-hex revision" >&2
  exit 2
fi
if [[ ! "${COTCODEC_SOURCE_SHA256}" =~ ^[0-9a-f]{64}$ ]]; then
  echo "COTCODEC_SOURCE_SHA256 must be a 64-hex archive digest" >&2
  exit 2
fi
if ! srun --help 2>&1 | grep -q -- '--container-image'; then
  echo "Slurm Pyxis support is required to run the OCI image" >&2
  exit 2
fi

run_dir="${COTCODEC_RUN_ROOT}/${SLURM_JOB_ID}"
hf_cache="${COTCODEC_HF_CACHE:-${COTCODEC_RUN_ROOT}/hf-cache}"
mkdir -p "${run_dir}" "${hf_cache}"

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
  slurm_log="${COTCODEC_RUN_ROOT}/slurm-${SLURM_JOB_ID}.out"
  if [[ -f "${slurm_log}" ]]; then
    cp "${slurm_log}" "${run_dir}/slurm.out" || true
  fi
}

trap 'forward_signal USR1' USR1
trap 'forward_signal TERM' TERM
trap on_exit EXIT

{
  echo "job_id=${SLURM_JOB_ID}"
  echo "predecessor_job_id=${COTCODEC_PREDECESSOR_JOB_ID:-none}"
  echo "git_sha=${COTCODEC_GIT_SHA}"
  echo "source_sha256=${COTCODEC_SOURCE_SHA256}"
  echo "image=${COTCODEC_IMAGE}"
  echo "command_sha256=$(printf %s "${COTCODEC_COMMAND_JSON_HEX}" | sha256sum | cut -d' ' -f1)"
  echo "started_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "nodelist=${SLURM_JOB_NODELIST}"
  echo "seeds=${COTCODEC_SEEDS:-unknown}"
} > "${run_dir}/job.env"

python - "${run_dir}" <<'PY'
import json
import os
import pathlib
import sys

run_dir = pathlib.Path(sys.argv[1])
for name, environment_key in (
    ("command.json", "COTCODEC_COMMAND_JSON_HEX"),
    ("manifest.json", "COTCODEC_MANIFEST_JSON_HEX"),
):
    value = json.loads(bytes.fromhex(os.environ[environment_key]))
    (run_dir / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
PY

{
  uname -a
  nvidia-smi --query-gpu=index,name,uuid,memory.total,driver_version --format=csv,noheader
  nvidia-smi
} > "${run_dir}/system.txt" 2>&1

srun --kill-on-bad-exit=1 bash scripts/check_compute_env.sh allocation \
  > "${run_dir}/allocation-doctor.txt" 2>&1

image_ref="${COTCODEC_IMAGE#docker://}"
termination_reason="running"

export HF_HOME=/cache/huggingface
export COTCODEC_OUTPUT_DIR=/outputs
export COTCODEC_CHECKPOINT_MARKER=/outputs/checkpoint.ready
export PYTHONUNBUFFERED=1

srun \
  --kill-on-bad-exit=1 \
  --container-image="docker://${image_ref}" \
  --container-mounts="${run_dir}:/outputs,${hf_cache}:/cache/huggingface" \
  --container-workdir=/workspace/cotcodec \
  bash -lc 'python scripts/verify_compute_provenance.py > /outputs/provenance-verification.txt && bash scripts/check_compute_env.sh container && exec python scripts/exec_research_workload.py' &
child_pid="$!"
wait "${child_pid}"
