#!/usr/bin/env bash
#SBATCH --job-name=cotcodec-vm
#SBATCH --partition=research
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --time=01:00:00
#SBATCH --signal=B:USR1@120
#SBATCH --output=slurm-%x-%j.out
#
# CPU-only VM campaign (decision D12). There is deliberately no --gres line:
# desktop VMs need no GPU, and the GPU device files on this host are
# world-writable, so nothing this job starts may see one. Submit only through
# scripts/submit_vm_campaign.py, which validates the manifest and passes it
# here hex-encoded together with this file's SHA-256.
#
# What this script guarantees before any container starts:
#   * it is the audited file (digest check) running under Slurm;
#   * the job holds no GPU (no GRES in its TRES, no GPU environment);
#   * the manifest is byte-identical to the validated one (digest check);
#   * the exported source tree is the reviewed one (tree digest check);
#   * Docker's default runtime is runc (no NVIDIA runtime injection).
# On exit, signal or failure it removes every container labelled with this
# job's id, and only those.

set -Eeuo pipefail
umask 077
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
HOME="$(getent passwd "$(id -un)" | cut -d: -f6)"
export HOME
unset PYTHONPATH PYTHONHOME PYTHONSTARTUP

: "${SLURM_JOB_ID:?vm-campaign.sbatch must run under Slurm}"
: "${COTCODEC_VM_MANIFEST_JSON_HEX:?Set the hex-encoded validated manifest}"
: "${COTCODEC_VM_MANIFEST_SHA256:?Set the canonical manifest digest}"
: "${COTCODEC_BATCH_SHA256:?Set the audited batch script digest}"
: "${COTCODEC_SOURCE_HOST_HEX:?Set the hex-encoded exported source directory}"
: "${COTCODEC_SOURCE_TREE_SHA256:?Set the source tree digest}"
: "${COTCODEC_RUN_ROOT_HEX:?Set the hex-encoded persistent run root}"

fail() {
  echo "vm-campaign: $*" >&2
  exit 2
}

for value in "${COTCODEC_VM_MANIFEST_SHA256}" "${COTCODEC_BATCH_SHA256}" \
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
  [[ -z "${!name:-}" ]] || fail "${name} is set; VM campaigns must hold no GPU"
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

# --- Source tree digest (must equal harness.q2.vm.manifest.source_tree_sha256) ---
actual_tree_sha256="$(python3 -E -s - "${source_dir}" <<'PY'
import hashlib
import os
import sys

source_dir = sys.argv[1]
root = os.path.join(source_dir, "harness")
if not os.path.isdir(root) or os.path.islink(root):
    raise SystemExit("source subtree harness is missing or a symlink")
entries = []
for dirpath, dirnames, filenames in os.walk(root):
    dirnames[:] = sorted(d for d in dirnames if d != "__pycache__")
    for filename in filenames:
        if filename.endswith((".pyc", ".pyo")):
            continue
        path = os.path.join(dirpath, filename)
        if os.path.islink(path):
            raise SystemExit(f"source tree contains a symlink: {path}")
        relative = os.path.relpath(path, source_dir).replace(os.sep, "/")
        digest = hashlib.sha256()
        with open(path, "rb") as handle:
            for chunk in iter(lambda h=handle: h.read(1 << 20), b""):
                digest.update(chunk)
        entries.append((relative, digest.hexdigest()))
entries.sort()
outer = hashlib.sha256()
for relative, digest_hex in entries:
    outer.update(f"{relative}\0{digest_hex}\n".encode())
print(outer.hexdigest(), end="")
PY
)"
[[ "${actual_tree_sha256}" == "${COTCODEC_SOURCE_TREE_SHA256}" ]] \
  || fail "source tree digest mismatch (${actual_tree_sha256})"

run_dir="${run_root}/${SLURM_JOB_ID}"
mkdir -p "${run_dir}"
chmod 700 "${run_dir}"

python3 -E -s - "${COTCODEC_VM_MANIFEST_JSON_HEX}" "${COTCODEC_VM_MANIFEST_SHA256}" \
  "${run_dir}/manifest.json" <<'PY'
import hashlib
import json
import pathlib
import sys

try:
    manifest = json.loads(bytes.fromhex(sys.argv[1]))
except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
    raise SystemExit("manifest is not valid hex-encoded JSON") from exc
canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
if hashlib.sha256(canonical.encode("utf-8")).hexdigest() != sys.argv[2]:
    raise SystemExit("manifest digest mismatch")
pathlib.Path(sys.argv[3]).write_text(json.dumps(manifest, indent=2, sort_keys=True))
PY

{
  echo "job_id=${SLURM_JOB_ID}"
  echo "batch_sha256=${actual_batch_sha256}"
  echo "manifest_sha256=${COTCODEC_VM_MANIFEST_SHA256}"
  echo "source_tree_sha256=${actual_tree_sha256}"
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
driver_pid=""
on_signal() {
  echo "vm-campaign: signal received; stopping the driver and cleaning up" >&2
  if [[ -n "${driver_pid}" ]]; then
    kill -TERM "${driver_pid}" 2>/dev/null || true
    wait "${driver_pid}" 2>/dev/null || true
  fi
  cleanup
  exit 143
}
trap cleanup EXIT
trap on_signal USR1 TERM INT

cd "${source_dir}"
python3 -E -s -m harness.q2.vm.driver \
  --manifest "${run_dir}/manifest.json" \
  --run-dir "${run_dir}" \
  --source-dir "${source_dir}" \
  --job-id "${SLURM_JOB_ID}" &
driver_pid=$!
set +e
wait "${driver_pid}"
rc=$?
set -e
driver_pid=""

cleanup
left="$(docker ps -aq --filter "label=cotcodec.slurm_job=${SLURM_JOB_ID}" | wc -l)"
echo "driver_exit=${rc} labelled_containers_left=${left}" >>"${run_dir}/preflight.txt"
if [[ "${left}" != "0" ]]; then
  fail "labelled containers survived cleanup"
fi
exit "${rc}"
