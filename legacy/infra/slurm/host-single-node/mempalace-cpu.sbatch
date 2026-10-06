#!/usr/bin/env bash
#SBATCH --job-name=mempalace-cpu
#SBATCH --partition=research
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --signal=B:USR1@180
#SBATCH --output=slurm-%x-%j.out

set -Eeuo pipefail
umask 077

: "${COTCODEC_MEMPALACE_MANIFEST_HEX:?Set the validated manifest}"
: "${COTCODEC_IMAGE_ID:?Set an exact local Docker image ID}"
: "${COTCODEC_IMAGE_REPO_DIGEST_HEX:?Set the immutable image repository digest}"
: "${COTCODEC_IMAGE_SBOM_HOST_HEX:?Set the image-bound SBOM path}"
: "${COTCODEC_IMAGE_SBOM_SHA256:?Set the image-bound SBOM digest}"
: "${COTCODEC_BASE_IMAGE_REF_HEX:?Set the immutable base reference}"
: "${COTCODEC_MINILM_ROOT:?Set the prepared MiniLM artifact root}"
: "${COTCODEC_DATASET_HOST_HEX:?Set the pinned dataset host path}"
: "${COTCODEC_DATASET_SHA256:?Set the pinned dataset digest}"
: "${COTCODEC_DATASET_SIZE:?Set the pinned dataset size}"
: "${COTCODEC_RUNTIME_RECEIPT_HOST_HEX:?Set the runtime receipt host path}"
: "${COTCODEC_RUNTIME_RECEIPT_SHA256:?Set the runtime receipt digest}"
: "${COTCODEC_RUN_ROOT_HEX:?Set the persistent run root}"
: "${COTCODEC_STUDY_ID:?Set the immutable study ID}"
: "${COTCODEC_BATCH_SHA256:?Set the audited batch digest}"

if [[ ! "${COTCODEC_IMAGE_ID}" =~ ^sha256:[0-9a-f]{64}$ ]]; then
  echo "image ID must be one exact local SHA-256 identity" >&2
  exit 2
fi
for value in \
  "${COTCODEC_IMAGE_SBOM_SHA256}" \
  "${COTCODEC_MINILM_ROOT}" \
  "${COTCODEC_DATASET_SHA256}" \
  "${COTCODEC_RUNTIME_RECEIPT_SHA256}" \
  "${COTCODEC_BATCH_SHA256}"; do
  if [[ ! "${value}" =~ ^[0-9a-f]{64}$ ]]; then
    echo "all digest fields must be lowercase 64-hex" >&2
    exit 2
  fi
done
if [[ ! "${COTCODEC_DATASET_SIZE}" =~ ^[1-9][0-9]{0,11}$ ]]; then
  echo "dataset size must be a positive integer" >&2
  exit 2
fi
if [[ ! "${COTCODEC_STUDY_ID}" =~ ^[a-z0-9][a-z0-9-]{0,39}$ ]]; then
  echo "study ID is unsafe" >&2
  exit 2
fi
actual_batch_sha256="$(sha256sum "$0" | cut -d' ' -f1)"
if [[ "${actual_batch_sha256}" != "${COTCODEC_BATCH_SHA256}" ]]; then
  echo "active batch script differs from the submitted digest" >&2
  exit 2
fi

decode_path() {
  python - "$1" <<'PY'
import pathlib
import re
import sys

try:
    value = bytes.fromhex(sys.argv[1]).decode("utf-8")
except (ValueError, UnicodeDecodeError) as exc:
    raise SystemExit("path is not valid UTF-8 hex") from exc
if re.fullmatch(r"/[A-Za-z0-9._/-]{1,511}", value) is None:
    raise SystemExit("path is outside the allowlist")
if ".." in pathlib.Path(value).parts:
    raise SystemExit("path contains traversal")
print(value, end="")
PY
}

decode_reference() {
  python - "$1" <<'PY'
import re
import sys

try:
    value = bytes.fromhex(sys.argv[1]).decode("utf-8")
except (ValueError, UnicodeDecodeError) as exc:
    raise SystemExit("base image reference is not valid UTF-8 hex") from exc
if re.fullmatch(
    r"[A-Za-z0-9][A-Za-z0-9._:/-]*@sha256:[0-9a-f]{64}", value
) is None:
    raise SystemExit("base image reference is not immutable")
print(value, end="")
PY
}

dataset_host="$(decode_path "${COTCODEC_DATASET_HOST_HEX}")"
runtime_receipt_host="$(decode_path "${COTCODEC_RUNTIME_RECEIPT_HOST_HEX}")"
run_root="$(decode_path "${COTCODEC_RUN_ROOT_HEX}")"
sbom_host="$(decode_path "${COTCODEC_IMAGE_SBOM_HOST_HEX}")"
base_image_reference="$(decode_reference "${COTCODEC_BASE_IMAGE_REF_HEX}")"
image_repo_digest="$(decode_reference "${COTCODEC_IMAGE_REPO_DIGEST_HEX}")"

if [[ ! -d "${run_root}" || -L "${run_root}" ]]; then
  echo "run root must be an existing non-symlink directory" >&2
  exit 2
fi
study_dir="${run_root}/studies/${COTCODEC_STUDY_ID}"
job_dir="${run_root}/jobs/${SLURM_JOB_ID}"
mkdir -p "${study_dir}" "${job_dir}"
chmod 700 "${study_dir}" "${job_dir}"

write_preflight_termination() {
  local exit_code="$?"
  if [[ "${exit_code}" -eq 0 || -e "${job_dir}/termination.json" ]]; then
    return
  fi
  python - \
    "${job_dir}/termination.json" \
    "${exit_code}" \
    "${COTCODEC_STUDY_ID}" \
    "${COTCODEC_PREDECESSOR_JOB_ID:-}" <<'PY'
import json
import os
import pathlib
import sys

payload = {
    "schema_version": 1,
    "job_id": os.environ["SLURM_JOB_ID"],
    "study_id": sys.argv[3],
    "predecessor_job_id": sys.argv[4] or None,
    "exit_code": int(sys.argv[2]),
    "termination_reason": "preflight_failed",
}
path = pathlib.Path(sys.argv[1])
with path.open("xb", buffering=0) as handle:
    handle.write((json.dumps(payload, indent=2, sort_keys=True) + "\n").encode())
    os.fsync(handle.fileno())
PY
}
trap write_preflight_termination EXIT
exec 9>"${study_dir}/study.lock"
if ! flock -n 9; then
  echo "another job owns this study ID" >&2
  exit 2
fi
checkpoint_marker="${study_dir}/checkpoint.ready"
rm -f "${checkpoint_marker}"

for input_path in "${dataset_host}" "${runtime_receipt_host}" "${sbom_host}"; do
  if [[ ! -f "${input_path}" || -L "${input_path}" ]]; then
    echo "input must be a regular non-symlink file: ${input_path}" >&2
    exit 2
  fi
done
if [[ "$(sha256sum "${dataset_host}" | cut -d' ' -f1)" != "${COTCODEC_DATASET_SHA256}" ]]; then
  echo "dataset digest drifted on the execution host" >&2
  exit 2
fi
if [[ "$(stat -c '%s' "${dataset_host}")" != "${COTCODEC_DATASET_SIZE}" ]]; then
  echo "dataset size drifted on the execution host" >&2
  exit 2
fi
if [[ "$(sha256sum "${runtime_receipt_host}" | cut -d' ' -f1)" != "${COTCODEC_RUNTIME_RECEIPT_SHA256}" ]]; then
  echo "runtime receipt drifted on the execution host" >&2
  exit 2
fi
if [[ "$(sha256sum "${sbom_host}" | cut -d' ' -f1)" != "${COTCODEC_IMAGE_SBOM_SHA256}" ]]; then
  echo "image SBOM drifted on the execution host" >&2
  exit 2
fi

python - \
  "${runtime_receipt_host}" \
  "${COTCODEC_IMAGE_ID}" \
  "${image_repo_digest}" \
  "${COTCODEC_IMAGE_SBOM_SHA256}" \
  "${base_image_reference}" \
  "${COTCODEC_MINILM_ROOT}" <<'PY'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
try:
    receipt = json.loads(path.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError) as exc:
    raise SystemExit("runtime receipt is unreadable") from exc
status = receipt.get("status")
if status not in {
    "VERIFIED_OFFLINE_MEMPALACE_RUNTIME",
    "SELF_ATTESTED_DISCOVERY_MEMPALACE_RUNTIME",
}:
    raise SystemExit("runtime receipt field 'status' drifted")
if status == "SELF_ATTESTED_DISCOVERY_MEMPALACE_RUNTIME" and (
    receipt.get("external_attestation") is not False
    or receipt.get("publication_ready") is not False
    or receipt.get("scientific_result") is not False
):
    raise SystemExit("self-attested discovery runtime is mislabeled")
expected = {
    "schema_version": 1,
    "repository_revision": "906b918a7c6ebb2a9198a6bf5a78f30a173fea56",
    "repository_tree": "98789ad017781f52550b511fcedd9e00c3346761",
    "source_archive_sha256": "efbc106cb344a1c5031268909adc2fb5c11cc783ec61adccbe3da0867b4d25c7",
    "runner_sha256": "c4b4ba3da9e2d7e0e3f27bc93918877fe5f46e202be9ff98b1e90c7e0124628d",
    "uv_lock_sha256": "9cea6756cee6b4a4c24d03c23e92116e62479d0d062c1cd3af8da806d1aeb4da",
    "chromadb_version": "1.5.7",
    "embedding_model": "all-MiniLM-L6-v2",
    "embedding_archive_sha256": "913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3",
    "execution_provider": "CPUExecutionProvider",
    "network_policy": "none",
    "image_id": sys.argv[2],
    "image_repo_digest": sys.argv[3],
    "image_sbom_sha256": sys.argv[4],
    "cotcodec_base_image_reference": sys.argv[5],
    "embedding_artifact_root_sha256": sys.argv[6],
}
for field, value in expected.items():
    if receipt.get(field) != value:
        raise SystemExit(f"runtime receipt field {field!r} drifted")
PY

memory_limit_mb="${SLURM_MEM_PER_NODE:-}"
if [[ ! "${memory_limit_mb}" =~ ^[1-9][0-9]*$ ]]; then
  echo "Slurm memory limit is unavailable" >&2
  exit 2
fi
slurm_time_limit="$(
  scontrol show job "${SLURM_JOB_ID}" -o \
    | tr ' ' '\n' \
    | awk -F= '$1 == "TimeLimit" {print $2; exit}'
)"
allocated_minutes="$(python - "${slurm_time_limit}" <<'PY'
import math
import re
import sys

value = sys.argv[1]
match = re.fullmatch(r"(?:(\d+)-)?(\d+):(\d+):(\d+)", value)
if match is None:
    raise SystemExit("Slurm TimeLimit is missing or unsupported")
days, hours, minutes, seconds = (int(part or 0) for part in match.groups())
print(days * 1440 + hours * 60 + minutes + math.ceil(seconds / 60), end="")
PY
)"

python - \
  "${COTCODEC_MEMPALACE_MANIFEST_HEX}" \
  "${job_dir}/manifest.json" \
  "${COTCODEC_IMAGE_ID}" \
  "${image_repo_digest}" \
  "${sbom_host}" \
  "${COTCODEC_IMAGE_SBOM_SHA256}" \
  "${base_image_reference}" \
  "${COTCODEC_MINILM_ROOT}" \
  "${dataset_host}" \
  "${COTCODEC_DATASET_SHA256}" \
  "${COTCODEC_DATASET_SIZE}" \
  "${runtime_receipt_host}" \
  "${COTCODEC_RUNTIME_RECEIPT_SHA256}" \
  "${run_root}" \
  "${COTCODEC_STUDY_ID}" \
  "${COTCODEC_BATCH_SHA256}" \
  "${allocated_minutes}" \
  "${memory_limit_mb}" <<'PY'
import json
import math
import os
import pathlib
import sys

try:
    manifest = json.loads(bytes.fromhex(sys.argv[1]))
except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
    raise SystemExit("manifest is not valid hex-encoded JSON") from exc
if not isinstance(manifest, dict):
    raise SystemExit("manifest must be one object")
expected_scalars = {
    "schema_version": 1,
    "runtime": "docker-cpu-mempalace-reproduction-v1",
    "name": os.environ["SLURM_JOB_NAME"],
    "study_id": sys.argv[15],
    "run_root": sys.argv[14],
    "batch_script_sha256": sys.argv[16],
    "network_policy": "none",
    "gpu_count": 0,
    "scientific_result": False,
}
for field, value in expected_scalars.items():
    if manifest.get(field) != value:
        raise SystemExit(f"manifest field {field!r} differs from the batch export")
expected_image = {
    "id": sys.argv[3],
    "repo_digest": sys.argv[4],
    "cotcodec_base_image_reference": sys.argv[7],
    "minilm_artifact_root_sha256": sys.argv[8],
}
image = manifest.get("image")
if not isinstance(image, dict) or any(
    image.get(field) != value for field, value in expected_image.items()
):
    raise SystemExit("manifest image contract differs from the batch export")
sbom = image.get("sbom")
if not isinstance(sbom, dict) or any(
    sbom.get(field) != value
    for field, value in {"host_path": sys.argv[5], "sha256": sys.argv[6]}.items()
):
    raise SystemExit("manifest SBOM differs from the batch export")
dataset = manifest.get("dataset")
if not isinstance(dataset, dict) or any(
    dataset.get(field) != value
    for field, value in {
        "host_path": sys.argv[9],
        "sha256": sys.argv[10],
        "size_bytes": int(sys.argv[11]),
        "revision": "98d7416c24c778c2fee6e6f3006e7a073259d48f",
    }.items()
):
    raise SystemExit("manifest dataset contract differs from the batch export")
if manifest.get("runtime_receipt") != {
    "host_path": sys.argv[12],
    "sha256": sys.argv[13],
}:
    raise SystemExit("manifest runtime receipt differs from the batch export")
resources = manifest.get("resources")
allocated_minutes = int(sys.argv[17])
memory_limit_mb = int(sys.argv[18])
if not isinstance(resources, dict) or resources != {
    "cpus": int(os.environ["SLURM_CPUS_PER_TASK"]),
    "memory_gb": memory_limit_mb // 1024,
    "minutes": allocated_minutes,
} or memory_limit_mb % 1024:
    raise SystemExit("manifest resources differ from the Slurm allocation")
budget = manifest.get("budget")
if not isinstance(budget, dict):
    raise SystemExit("manifest budget is missing")
max_cpu_hours = budget.get("max_cpu_hours")
if (
    not isinstance(max_cpu_hours, (int, float))
    or isinstance(max_cpu_hours, bool)
    or not math.isfinite(float(max_cpu_hours))
    or not 0 < float(max_cpu_hours) <= 512
    or resources["cpus"] * allocated_minutes / 60 > float(max_cpu_hours)
    or budget.get("max_wall_minutes") != allocated_minutes
):
    raise SystemExit("manifest budget differs from the Slurm allocation")
predecessor = os.environ.get("COTCODEC_PREDECESSOR_JOB_ID")
if manifest.get("resume_from_job_id") != predecessor:
    raise SystemExit("manifest predecessor differs from the batch export")
path = pathlib.Path(sys.argv[2])
with path.open("xb", buffering=0) as handle:
    handle.write((json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode())
    os.fsync(handle.fileno())
PY
cp "${runtime_receipt_host}" "${job_dir}/runtime-receipt.json"
cp "${sbom_host}" "${job_dir}/image-sbom.spdx.json"
sha256sum \
  "${dataset_host}" \
  "${runtime_receipt_host}" \
  "${sbom_host}" \
  > "${job_dir}/input-sha256s.txt"

actual_image_id="$(docker image inspect --format '{{.Id}}' "${COTCODEC_IMAGE_ID}")"
if [[ "${actual_image_id}" != "${COTCODEC_IMAGE_ID}" ]]; then
  echo "local Docker image ID drifted" >&2
  exit 2
fi
docker image inspect "${COTCODEC_IMAGE_ID}" > "${job_dir}/image-inspect.json"
python - \
  "${job_dir}/image-inspect.json" \
  "${base_image_reference}" \
  "${COTCODEC_MINILM_ROOT}" \
  "${image_repo_digest}" \
  "${sbom_host}" <<'PY'
import json
import pathlib
import re
import sys

payload = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
if not isinstance(payload, list) or len(payload) != 1:
    raise SystemExit("Docker inspect did not return one image")
image = payload[0]
repo_digests = image.get("RepoDigests") or []
if not isinstance(repo_digests, list) or sys.argv[4] not in repo_digests:
    raise SystemExit("Docker image does not expose the registered repository digest")
labels = image.get("Config", {}).get("Labels", {})
expected = {
    "org.opencontainers.image.revision": "906b918a7c6ebb2a9198a6bf5a78f30a173fea56",
    "org.opencontainers.image.mempalace-tree": "98789ad017781f52550b511fcedd9e00c3346761",
    "org.opencontainers.image.mempalace-source-archive-sha256": "efbc106cb344a1c5031268909adc2fb5c11cc783ec61adccbe3da0867b4d25c7",
    "org.opencontainers.image.mempalace-runner-sha256": "c4b4ba3da9e2d7e0e3f27bc93918877fe5f46e202be9ff98b1e90c7e0124628d",
    "org.opencontainers.image.mempalace-uv-lock-sha256": "9cea6756cee6b4a4c24d03c23e92116e62479d0d062c1cd3af8da806d1aeb4da",
    "org.opencontainers.image.minilm-archive-sha256": "913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3",
    "org.opencontainers.image.minilm-artifact-root-sha256": sys.argv[3],
    "org.opencontainers.image.cotcodec-base-reference": sys.argv[2],
    "org.opencontainers.image.cotcodec-publication-ready": "false",
}
for field, value in expected.items():
    if labels.get(field) != value:
        raise SystemExit(f"Docker image label {field!r} drifted")

sbom = json.loads(pathlib.Path(sys.argv[5]).read_text(encoding="utf-8"))
if not isinstance(sbom.get("spdxVersion"), str) or not sbom[
    "spdxVersion"
].startswith("SPDX-"):
    raise SystemExit("SBOM is not SPDX JSON")
scan = sbom.get("cotcodecScan")
if not isinstance(scan, dict):
    raise SystemExit("SBOM has no scan receipt")
scanner_version = scan.get("scanner_version")
expected_scan = {
    "scanner": "syft",
    "scanner_version": scanner_version,
    "target_repo_digest": sys.argv[4],
    "target_image_id": image["Id"],
    "argv": ["syft", sys.argv[4], "--output", "spdx-json"],
}
if scan != expected_scan or not isinstance(scanner_version, str) or re.fullmatch(
    r"[0-9]+\.[0-9]+\.[0-9]+", scanner_version
) is None:
    raise SystemExit("SBOM scan receipt does not bind the live image")
described = sbom.get("documentDescribes")
packages = sbom.get("packages")
if not isinstance(described, list) or not described or not isinstance(packages, list):
    raise SystemExit("SBOM has no described package")
subjects = [
    package
    for package in packages
    if isinstance(package, dict) and package.get("SPDXID") in described
]
values = set()
for subject in subjects:
    for field in ("name", "versionInfo", "packageFileName"):
        if isinstance(subject.get(field), str):
            values.add(subject[field])
    for reference in subject.get("externalRefs", []):
        if (
            isinstance(reference, dict)
            and reference.get("referenceCategory") == "PACKAGE-MANAGER"
            and reference.get("referenceType") == "purl"
            and isinstance(reference.get("referenceLocator"), str)
        ):
            values.add(reference["referenceLocator"])
if image["Id"] not in values or f"pkg:oci/{sys.argv[4]}" not in values:
    raise SystemExit("SBOM subject does not bind the live image and repository digest")
creators = sbom.get("creationInfo", {}).get("creators", [])
if "Organization: Anchore, Inc" not in creators or not any(
    isinstance(creator, str)
    and re.fullmatch(r"Tool: syft-[0-9]+\.[0-9]+\.[0-9]+", creator)
    for creator in creators
):
    raise SystemExit("SBOM does not bind a versioned Syft generator")
PY

container_name="cotcodec-mempalace-${SLURM_JOB_ID}"
container_created=false
termination_reason="preflight"
docker_wait_pid=""

write_termination() {
  local exit_code="$1"
  python - \
    "${job_dir}/termination.json" \
    "${exit_code}" \
    "${termination_reason}" \
    "${COTCODEC_STUDY_ID}" \
    "${COTCODEC_PREDECESSOR_JOB_ID:-}" <<'PY'
import json
import os
import pathlib
import sys

payload = {
    "schema_version": 1,
    "job_id": os.environ["SLURM_JOB_ID"],
    "study_id": sys.argv[4],
    "predecessor_job_id": sys.argv[5] or None,
    "exit_code": int(sys.argv[2]),
    "termination_reason": sys.argv[3],
}
path = pathlib.Path(sys.argv[1])
with path.open("xb", buffering=0) as handle:
    handle.write((json.dumps(payload, indent=2, sort_keys=True) + "\n").encode())
    os.fsync(handle.fileno())
PY
}

forward_signal() {
  local signal_name="$1"
  termination_reason="signal_${signal_name}_received"
  if [[ "${container_created}" == true ]] \
    && [[ "$(docker inspect --format '{{.State.Running}}' "${container_name}" 2>/dev/null || echo false)" == true ]]; then
    # The container can finish between inspect and kill. Signal forwarding is
    # therefore best-effort; checkpoint confirmation remains authoritative.
    docker kill --signal "${signal_name}" "${container_name}" >/dev/null 2>&1 || true
  fi
  local waited=0
  while [[ "${waited}" -lt 120 && ! -f "${checkpoint_marker}" ]]; do
    if [[ "${container_created}" == true ]] \
      && [[ "$(docker inspect --format '{{.State.Running}}' "${container_name}" 2>/dev/null || echo false)" != true ]]; then
      break
    fi
    sleep 2
    waited=$((waited + 2))
  done
  if [[ -f "${checkpoint_marker}" ]]; then
    termination_reason="signal_${signal_name}_checkpoint_confirmed"
    # The workload atomically publishes the marker before completing its
    # orderly exit. Give Docker a short grace period to surface exit 75 so a
    # valid checkpoint is not converted into a TERM/143 failure.
    local exit_waited=0
    while [[ "${exit_waited}" -lt 30 ]] \
      && [[ "${container_created}" == true ]] \
      && [[ "$(docker inspect --format '{{.State.Running}}' "${container_name}" 2>/dev/null || echo false)" == true ]]; do
      sleep 1
      exit_waited=$((exit_waited + 1))
    done
  else
    termination_reason="signal_${signal_name}_checkpoint_unconfirmed"
  fi
  if [[ "${container_created}" == true ]] \
    && [[ "$(docker inspect --format '{{.State.Running}}' "${container_name}" 2>/dev/null || echo false)" == true ]]; then
    docker kill --signal TERM "${container_name}" >/dev/null 2>&1 || true
  fi
}

on_exit() {
  local exit_code="$?"
  if [[ "${container_created}" == true ]]; then
    docker inspect "${container_name}" > "${job_dir}/container-final-inspect.json" \
      2>/dev/null || true
    docker logs "${container_name}" > "${job_dir}/container.log" 2>&1 || true
    docker rm --force "${container_name}" >/dev/null 2>&1 || true
  fi
  if [[ "${termination_reason}" == running ]]; then
    if [[ "${exit_code}" -eq 0 ]]; then
      termination_reason="completed"
    elif [[ "${exit_code}" -eq 75 && -f "${checkpoint_marker}" ]]; then
      termination_reason="checkpointed"
    else
      termination_reason="workload_failed"
    fi
  fi
  write_termination "${exit_code}" || true
}

trap 'forward_signal USR1' USR1
trap 'forward_signal TERM' TERM
trap on_exit EXIT

cpu_list="$(awk '/Cpus_allowed_list/ {print $2}' /proc/self/status)"
if [[ -z "${cpu_list}" ]]; then
  echo "could not determine Slurm CPU affinity" >&2
  exit 2
fi
docker create \
  --name "${container_name}" \
  --network none \
  --read-only \
  --tmpfs /tmp:rw,nosuid,nodev,size=8g \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  --pids-limit 4096 \
  --cpuset-cpus "${cpu_list}" \
  --memory "${memory_limit_mb}m" \
  --memory-swap "${memory_limit_mb}m" \
  --ulimit core=0 \
  --user "$(id -u):$(id -g)" \
  --env HOME=/data \
  --env ANONYMIZED_TELEMETRY=FALSE \
  --env PYTHONDONTWRITEBYTECODE=1 \
  --env PYTHONUNBUFFERED=1 \
  --env COTCODEC_CHECKPOINT_MARKER=/outputs/checkpoint.ready \
  --volume "${dataset_host}:/inputs/longmemeval_s_cleaned.json:ro" \
  --volume "${runtime_receipt_host}:/inputs/mempalace-runtime.json:ro" \
  --volume "${study_dir}:/outputs:rw" \
  "${COTCODEC_IMAGE_ID}" \
  --source-root /opt/mempalace/source \
  --dataset /inputs/longmemeval_s_cleaned.json \
  --runtime-receipt /inputs/mempalace-runtime.json \
  --output-dir /outputs/run \
  --resume \
  > "${job_dir}/container-id.txt"
container_created=true
docker inspect "${container_name}" > "${job_dir}/container-created-inspect.json"

termination_reason="running"
set +e
container_exit_code_path="${job_dir}/container-exit-code.txt"
if ! docker start "${container_name}" >/dev/null; then
  termination_reason="container_start_failed"
  echo "Docker failed to start the workload container" >&2
  exit 2
fi
docker wait "${container_name}" > "${container_exit_code_path}" &
docker_wait_pid="$!"

# A foreground external command prevents Bash from running a trapped Slurm
# signal until that command exits.  Waiting on a background ``docker wait``
# process keeps USR1/TERM traps responsive so they can forward the signal to
# the container and observe its durable checkpoint marker.
set +e
while kill -0 "${docker_wait_pid}" >/dev/null 2>&1; do
  wait "${docker_wait_pid}"
done
wait "${docker_wait_pid}" >/dev/null 2>&1
set -e
if [[ ! -s "${container_exit_code_path}" ]]; then
  termination_reason="container_wait_failed"
  echo "Docker did not record the workload exit code" >&2
  exit 2
fi
workload_exit_code="$(tr -d '[:space:]' < "${container_exit_code_path}")"
if [[ ! "${workload_exit_code}" =~ ^[0-9]{1,3}$ ]]; then
  termination_reason="container_wait_failed"
  echo "Docker returned an invalid workload exit code" >&2
  exit 2
fi
set -e
if [[ "${workload_exit_code}" -eq 0 ]]; then
  termination_reason="completed"
elif [[ "${workload_exit_code}" -eq 75 && -f "${checkpoint_marker}" ]]; then
  termination_reason="checkpointed"
else
  termination_reason="workload_failed"
fi
exit "${workload_exit_code}"
