#!/usr/bin/env bash
#SBATCH --job-name=cotcodec-s1a-vm
#SBATCH --partition=research
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --time=01:00:00
#SBATCH --signal=B:USR1@120
#SBATCH --output=/home/kevin/cotcodec-runs/stage0/q2-stage1/slurm/slurm-%x-%j.out
#
# CPU-only VM job of q2-stage1-rescoped-v1 (S1a): episodes, the offline setup check and the
# development smoke (decisions D12, D13; registration sections 3.1 items 3-5, 5.5-5.7, 14).
# There is deliberately no --gres line. Submit only through
#   python3 -m harness.q2_stage1.lane submit MANIFEST.json
# from the exported source tree, which validates the manifest, writes it canonically under the
# run root and passes its path (hex-encoded) and SHA-256 here with this file's SHA-256.
# The guards are vm-campaign.sbatch's:
#   * this is the audited file (digest check) running under Slurm;
#   * the job holds no GPU (no GRES in its TRES, no GPU environment);
#   * the manifest is byte-identical to the validated one (digest check);
#   * the exported source tree is the reviewed one (tree digest over harness/);
#   * Docker's default runtime is runc (no NVIDIA runtime injection).
# USR1 (120 s before the limit) reaches the lane, which dispatches nothing new, cuts the
# episodes in flight (recorded cap_truncated) and exits; TERM stops it. On exit every
# container labelled with this job's id, and only those, is removed.

set -Eeuo pipefail
umask 077
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
HOME="$(getent passwd "$(id -un)" | cut -d: -f6)"
export HOME
unset PYTHONPATH PYTHONHOME PYTHONSTARTUP

: "${SLURM_JOB_ID:?s1a-vm.sbatch must run under Slurm}"
: "${COTCODEC_S1A_MANIFEST_PATH_HEX:?Set the hex-encoded path of the validated manifest}"
: "${COTCODEC_S1A_MANIFEST_SHA256:?Set the canonical manifest digest}"
: "${COTCODEC_BATCH_SHA256:?Set the audited batch script digest}"
: "${COTCODEC_SOURCE_HOST_HEX:?Set the hex-encoded exported source directory}"
: "${COTCODEC_SOURCE_TREE_SHA256:?Set the source tree digest}"
: "${COTCODEC_RUN_ROOT_HEX:?Set the hex-encoded persistent run root}"

fail() {
  echo "s1a-vm: $*" >&2
  exit 2
}

for value in "${COTCODEC_S1A_MANIFEST_SHA256}" "${COTCODEC_BATCH_SHA256}" \
  "${COTCODEC_SOURCE_TREE_SHA256}"; do
  [[ "${value}" =~ ^[0-9a-f]{64}$ ]] || fail "digests must be lowercase 64-hex"
done
[[ "${SLURM_JOB_ID}" =~ ^[1-9][0-9]{0,19}$ ]] || fail "unexpected job id"

actual_batch_sha256="$(sha256sum "$0" | cut -d' ' -f1)"
[[ "${actual_batch_sha256}" == "${COTCODEC_BATCH_SHA256}" ]] \
  || fail "batch script digest does not match the submitted manifest"

# --- No GPU, by construction and by assertion -------------------------------
for name in SLURM_JOB_GPUS SLURM_STEP_GPUS CUDA_VISIBLE_DEVICES GPU_DEVICE_ORDINAL \
  SLURM_GPUS SLURM_GPUS_ON_NODE; do
  [[ -z "${!name:-}" ]] || fail "${name} is set; S1a VM jobs must hold no GPU"
done
job_tres="$(scontrol show job "${SLURM_JOB_ID}" \
  | tr ' ' '\n' | grep -E '^(TRES|TresPerNode|TresPerJob|TresPerTask|TresPerSocket)=' || true)"
if grep -qiE 'gres/gpu|gpu:' <<<"${job_tres}"; then
  fail "this job was allocated a GPU; refusing to start VMs"
fi
default_runtime="$(docker info --format '{{.DefaultRuntime}}')"
[[ "${default_runtime}" == "runc" ]] || fail "Docker default runtime is ${default_runtime}, not runc"

decode_host_path() {
  python3 -E -s - "$1" <<'PY'
import pathlib
import re
import sys

try:
    value = bytes.fromhex(sys.argv[1]).decode("utf-8")
except (ValueError, UnicodeDecodeError) as exc:
    raise SystemExit("host path is not valid UTF-8 hex") from exc
path = pathlib.PurePosixPath(value)
root = pathlib.PurePosixPath("/home/kevin/cotcodec-runs")
if not re.fullmatch(r"/[A-Za-z0-9._/-]{1,511}", value) or ".." in path.parts:
    raise SystemExit("decoded host path is outside the allowlist")
if path != root and root not in path.parents:
    raise SystemExit("decoded host path is outside the run root")
print(value, end="")
PY
}

source_dir="$(decode_host_path "${COTCODEC_SOURCE_HOST_HEX}")"
run_root="$(decode_host_path "${COTCODEC_RUN_ROOT_HEX}")"
[[ -d "${source_dir}" && ! -L "${source_dir}" ]] || fail "source directory is missing"

cd "${source_dir}"
actual_tree_sha256="$(python3 -E -s -c \
  'import sys; from harness.q2.vm.manifest import source_tree_sha256 as t; print(t(sys.argv[1]), end="")' \
  "${source_dir}")"
[[ "${actual_tree_sha256}" == "${COTCODEC_SOURCE_TREE_SHA256}" ]] \
  || fail "source tree digest mismatch (${actual_tree_sha256})"

run_dir="${run_root}/${SLURM_JOB_ID}"
mkdir -p "${run_dir}"
chmod 700 "${run_dir}"

manifest_src="$(decode_host_path "${COTCODEC_S1A_MANIFEST_PATH_HEX}")"
[[ -f "${manifest_src}" && ! -L "${manifest_src}" ]] || fail "manifest file is missing"
python3 -E -s - "${manifest_src}" "${COTCODEC_S1A_MANIFEST_SHA256}" \
  "${run_dir}/manifest.json" <<'PY'
import hashlib
import json
import pathlib
import sys

try:
    manifest = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
    raise SystemExit("manifest is not valid JSON") from exc
canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
if hashlib.sha256(canonical.encode("utf-8")).hexdigest() != sys.argv[2]:
    raise SystemExit("manifest digest mismatch")
pathlib.Path(sys.argv[3]).write_text(json.dumps(manifest, indent=2, sort_keys=True))
PY

{
  echo "job_id=${SLURM_JOB_ID}"
  echo "batch_sha256=${actual_batch_sha256}"
  echo "manifest_sha256=${COTCODEC_S1A_MANIFEST_SHA256}"
  echo "source_tree_sha256=${actual_tree_sha256}"
  echo "source_git_sha=$(cat "${source_dir}/.git_sha" 2>/dev/null || echo unknown)"
  echo "docker_default_runtime=${default_runtime}"
  echo "job_tres=$(tr '\n' ' ' <<<"${job_tres}")"
} >"${run_dir}/preflight.txt"

# --- Cleanup: only containers carrying this job's label -----------------------
cleanup() {
  local ids
  ids="$(docker ps -aq --filter "label=cotcodec.slurm_job=${SLURM_JOB_ID}" || true)"
  if [[ -n "${ids}" ]]; then
    # shellcheck disable=SC2086
    docker rm --force --volumes ${ids} >/dev/null 2>&1 || true
  fi
}
lane_pid=""
on_usr1() {
  echo "s1a-vm: USR1; the lane stops dispatching" >&2
  if [[ -n "${lane_pid}" ]]; then
    kill -USR1 "${lane_pid}" 2>/dev/null || true
  fi
}
on_term() {
  echo "s1a-vm: TERM; stopping the lane and cleaning up" >&2
  if [[ -n "${lane_pid}" ]]; then
    kill -TERM "${lane_pid}" 2>/dev/null || true
    wait "${lane_pid}" 2>/dev/null || true
  fi
  cleanup
  exit 143
}
trap cleanup EXIT
trap on_usr1 USR1
trap on_term TERM INT

python3 -E -s -m harness.q2_stage1.lane run \
  --manifest "${run_dir}/manifest.json" \
  --run-dir "${run_dir}" \
  --source-dir "${source_dir}" \
  --job-id "${SLURM_JOB_ID}" &
lane_pid=$!
set +e
while true; do
  wait "${lane_pid}"
  rc=$?
  # A trapped USR1 interrupts wait (status > 128) while the lane keeps running.
  if ! kill -0 "${lane_pid}" 2>/dev/null; then
    break
  fi
done
set -e
lane_pid=""

cleanup
left="$(docker ps -aq --filter "label=cotcodec.slurm_job=${SLURM_JOB_ID}" | wc -l)"
echo "lane_exit=${rc} labelled_containers_left=${left}" >>"${run_dir}/preflight.txt"
if [[ "${left}" != "0" ]]; then
  fail "labelled containers survived cleanup"
fi
exit "${rc}"
