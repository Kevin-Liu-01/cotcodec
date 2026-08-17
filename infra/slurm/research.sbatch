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
memory_bundle_host=""
memory_bundle_mount=""
if [[ -n "${COTCODEC_MEMORY_BUNDLE_HOST_HEX:-}" \
  || -n "${COTCODEC_MEMORY_BUNDLE_SHA256:-}" ]]; then
  if [[ ! "${COTCODEC_MEMORY_BUNDLE_HOST_HEX:-}" =~ ^[0-9a-f]+$ ]] \
    || (( ${#COTCODEC_MEMORY_BUNDLE_HOST_HEX} % 2 != 0 )); then
    echo "COTCODEC_MEMORY_BUNDLE_HOST_HEX must be nonempty even-length hex" >&2
    exit 2
  fi
  if [[ ! "${COTCODEC_MEMORY_BUNDLE_SHA256:-}" =~ ^[0-9a-f]{64}$ ]]; then
    echo "COTCODEC_MEMORY_BUNDLE_SHA256 must be a 64-hex digest" >&2
    exit 2
  fi
  memory_bundle_host="$(python - "${COTCODEC_MEMORY_BUNDLE_HOST_HEX}" <<'PY'
import sys

try:
    value = bytes.fromhex(sys.argv[1]).decode("utf-8")
except (ValueError, UnicodeDecodeError) as exc:
    raise SystemExit("memory bundle host path is not valid UTF-8 hex") from exc
print(value, end="")
PY
)"
  if [[ ! "${memory_bundle_host}" =~ ^/[A-Za-z0-9._/-]{1,511}$ ]] \
    || [[ "/${memory_bundle_host}/" == *"/../"* ]]; then
    echo "decoded memory bundle host path is unsafe" >&2
    exit 2
  fi
  if [[ ! -f "${memory_bundle_host}" || -L "${memory_bundle_host}" ]]; then
    echo "memory bundle must be a regular non-symlink file" >&2
    exit 2
  fi
  actual_memory_bundle_sha256="$(sha256sum "${memory_bundle_host}" | cut -d' ' -f1)"
  if [[ "${actual_memory_bundle_sha256}" != "${COTCODEC_MEMORY_BUNDLE_SHA256}" ]]; then
    echo "memory bundle digest mismatch" >&2
    exit 2
  fi
  memory_bundle_mount=",${memory_bundle_host}:/inputs/memory-selection-bundle.json:ro"
fi
if ! srun --help 2>&1 | grep -q -- '--container-image'; then
  echo "Slurm Pyxis support is required to run the OCI image" >&2
  exit 2
fi

run_dir="${COTCODEC_RUN_ROOT}/${SLURM_JOB_ID}"
hf_cache="${COTCODEC_HF_CACHE:-${COTCODEC_RUN_ROOT}/hf-cache}"
mkdir -p "${run_dir}" "${hf_cache}"

if [[ -n "${COTCODEC_PREDECESSOR_JOB_ID:-}" ]]; then
  if [[ ! "${COTCODEC_PREDECESSOR_JOB_ID}" =~ ^[1-9][0-9]{0,19}$ ]]; then
    echo "COTCODEC_PREDECESSOR_JOB_ID must be a positive Slurm job id" >&2
    exit 2
  fi
  if [[ ! "${COTCODEC_RESUME_SUBPATH:-}" =~ ^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$ ]] \
    || [[ "/${COTCODEC_RESUME_SUBPATH}/" == *"/../"* ]]; then
    echo "COTCODEC_RESUME_SUBPATH must be a safe relative directory" >&2
    exit 2
  fi
  python - "${COTCODEC_RUN_ROOT}" "${run_dir}" \
    "${COTCODEC_PREDECESSOR_JOB_ID}" "${COTCODEC_RESUME_SUBPATH}" <<'PY'
import json
import os
import pathlib
import shutil
import sys

run_root = pathlib.Path(sys.argv[1]).resolve()
run_dir = pathlib.Path(sys.argv[2]).resolve()
predecessor_id = sys.argv[3]
subpath = pathlib.Path(sys.argv[4])
predecessor = (run_root / predecessor_id).resolve()
if predecessor.parent != run_root or run_dir.parent != run_root:
    raise SystemExit("resume directories escaped the registered run root")
job_env = predecessor / "job.env"
if not job_env.is_file():
    raise SystemExit("predecessor job.env is missing")
receipt = {}
for line in job_env.read_text(encoding="utf-8").splitlines():
    key, separator, value = line.partition("=")
    if separator and value != "none" and key in {
        "git_sha",
        "source_sha256",
        "image",
        "memory_bundle_sha256",
    }:
        receipt[key] = value
expected = {
    "git_sha": os.environ["COTCODEC_GIT_SHA"],
    "source_sha256": os.environ["COTCODEC_SOURCE_SHA256"],
    "image": os.environ["COTCODEC_IMAGE"],
}
if bundle_sha256 := os.environ.get("COTCODEC_MEMORY_BUNDLE_SHA256"):
    expected["memory_bundle_sha256"] = bundle_sha256
if receipt != expected:
    raise SystemExit("predecessor provenance does not match this job")
source_candidate = predecessor / subpath
destination_candidate = run_dir / subpath
if source_candidate.is_symlink():
    raise SystemExit("resume artifact source must not be a symbolic link")
source = source_candidate.resolve()
destination = destination_candidate.resolve()
if predecessor not in source.parents or run_dir not in destination.parents:
    raise SystemExit("resume artifact path escaped its job directory")
if not source.is_dir() or destination.exists():
    raise SystemExit("resume artifact source is missing or destination already exists")
if any(path.is_symlink() for path in source.rglob("*")):
    raise SystemExit("resume artifact tree must not contain symbolic links")
destination.parent.mkdir(parents=True, exist_ok=True)
shutil.copytree(source, destination)
resume_receipt = {
    "schema_version": 1,
    "predecessor_job_id": predecessor_id,
    "resume_subpath": subpath.as_posix(),
    **expected,
}
(run_dir / "resume-receipt.json").write_text(
    json.dumps(resume_receipt, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
PY
fi

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
  echo "memory_bundle_sha256=${COTCODEC_MEMORY_BUNDLE_SHA256:-none}"
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
  --container-mounts="${run_dir}:/outputs,${hf_cache}:/cache/huggingface${memory_bundle_mount}" \
  --container-workdir=/workspace/cotcodec \
  bash -lc 'python scripts/verify_compute_provenance.py > /outputs/provenance-verification.txt && bash scripts/check_compute_env.sh container && exec python scripts/exec_research_workload.py' &
child_pid="$!"
wait "${child_pid}"
