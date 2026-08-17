#!/usr/bin/env bash
#SBATCH --job-name=cotcodec-docker
#SBATCH --partition=research
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:h100:1
#SBATCH --cpus-per-task=16
#SBATCH --mem=64G
#SBATCH --time=02:00:00
#SBATCH --signal=B:USR1@180
#SBATCH --output=slurm-%x-%j.out

set -Eeuo pipefail
umask 077

: "${COTCODEC_IMAGE_ID:?Set an exact local Docker sha256 image ID}"
: "${COTCODEC_COMMAND_JSON_HEX:?Set the hex-encoded JSON argv}"
: "${COTCODEC_MANIFEST_JSON_HEX:?Set the hex-encoded validated manifest}"
: "${COTCODEC_RUN_ROOT_HEX:?Set the hex-encoded persistent job storage path}"
: "${COTCODEC_GIT_SHA:?Set the embedded 40-hex source revision}"
: "${COTCODEC_SOURCE_SHA256:?Set the embedded source archive digest}"
: "${COTCODEC_BATCH_SHA256:?Set the audited batch script digest}"
: "${COTCODEC_MODEL_CACHE_HOST_HEX:?Set the hex-encoded model cache path}"
: "${COTCODEC_MODEL_ID:?Set the reviewed model registry id}"
: "${COTCODEC_MODEL_REVISION:?Set the pinned model revision}"
: "${COTCODEC_MODEL_RECEIPT_SHA256:?Set the model receipt digest}"
: "${COTCODEC_MODEL_ARTIFACT_ROOT:?Set the model artifact root}"
: "${COTCODEC_EXPECTED_GPUS:?Set the requested H100 count}"
: "${COTCODEC_RANDOMNESS_CONTRACT:?Set the validated randomness contract}"
: "${COTCODEC_SEEDS:?Set the colon-delimited assignment seeds}"

if [[ ! "${COTCODEC_IMAGE_ID}" =~ ^sha256:[0-9a-f]{64}$ ]]; then
  echo "COTCODEC_IMAGE_ID must be an exact local Docker image ID" >&2
  exit 2
fi
for value in \
  "${COTCODEC_SOURCE_SHA256}" \
  "${COTCODEC_BATCH_SHA256}" \
  "${COTCODEC_MODEL_RECEIPT_SHA256}" \
  "${COTCODEC_MODEL_ARTIFACT_ROOT}"; do
  if [[ ! "${value}" =~ ^[0-9a-f]{64}$ ]]; then
    echo "all SHA-256 values must be lowercase 64-hex digests" >&2
    exit 2
  fi
done
for value in "${COTCODEC_GIT_SHA}" "${COTCODEC_MODEL_REVISION}"; do
  if [[ ! "${value}" =~ ^[0-9a-f]{40}$ ]]; then
    echo "git and model revisions must be lowercase 40-hex commits" >&2
    exit 2
  fi
done
if [[ ! "${COTCODEC_MODEL_ID}" =~ ^[a-z0-9][a-z0-9.-]{0,79}$ ]]; then
  echo "COTCODEC_MODEL_ID is unsafe" >&2
  exit 2
fi
if [[ ! "${COTCODEC_EXPECTED_GPUS}" =~ ^[1-8]$ ]]; then
  echo "COTCODEC_EXPECTED_GPUS must be in [1,8]" >&2
  exit 2
fi
python - "${COTCODEC_COMMAND_JSON_HEX}" "${COTCODEC_SEEDS}" "${COTCODEC_RANDOMNESS_CONTRACT}" <<'PY'
import json
import sys

try:
    command = json.loads(bytes.fromhex(sys.argv[1]))
except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
    raise SystemExit("command is not valid hex-encoded JSON") from exc
if not isinstance(command, list) or not all(isinstance(arg, str) for arg in command):
    raise SystemExit("command must be a JSON argv list")
randomness_contract = sys.argv[3]
if randomness_contract == "deterministic-all-serve":
    if sys.argv[2] != "none":
        raise SystemExit("deterministic all-SERVE jobs cannot declare seeds")
    declared = []
    if any(option in command for option in ("--assignment-seed", "--assignment-seeds", "--seeds")):
        raise SystemExit("deterministic all-SERVE jobs cannot execute seed options")
    if "scripts/run_memory_model_screen.py" in command and not (
        "--evaluation-mode" in command
        and command[command.index("--evaluation-mode") + 1] == "all-serve-benchmark"
    ):
        raise SystemExit("deterministic model jobs must execute all-SERVE mode")
elif randomness_contract == "assignment-seed-matrix":
    try:
        declared = [int(value) for value in sys.argv[2].split(":")]
    except ValueError as exc:
        raise SystemExit("declared seeds must be colon-delimited integers") from exc
    if len(declared) < 3 or len(declared) != len(set(declared)):
        raise SystemExit("at least three distinct declared seeds are required")
else:
    raise SystemExit("unsupported randomness contract")
seed_contracts = {
    "scripts/run_memory_model_screen.py": "--assignment-seeds",
    "scripts/run_memory_trials.py": "--assignment-seeds",
    "scripts/run_memory_model_replay_doctor.py": "--seeds",
}
active = [
    (script, option)
    for script, option in seed_contracts.items()
    if script in command
]
if active and randomness_contract == "assignment-seed-matrix":
    if len(active) != 1:
        raise SystemExit("command contains multiple seeded memory workloads")
    _, seed_option = active[0]
    forbidden = {"--assignment-seed", "--assignment-seeds", "--seeds"} - {
        seed_option
    }
    if command.count(seed_option) != 1 or any(option in command for option in forbidden):
        raise SystemExit(
            f"memory command does not execute declared seeds via {seed_option}"
        )
    start = command.index(seed_option) + 1
    executed = []
    for argument in command[start:]:
        if argument.startswith("--"):
            break
        try:
            executed.append(int(argument))
        except ValueError as exc:
            raise SystemExit("executed seed is not an integer") from exc
    if executed != declared:
        raise SystemExit("executed seeds do not exactly match declared seeds")
PY
actual_batch_sha256="$(sha256sum "$0" | cut -d' ' -f1)"
if [[ "${actual_batch_sha256}" != "${COTCODEC_BATCH_SHA256}" ]]; then
  echo "batch script digest does not match the submitted manifest" >&2
  exit 2
fi

decode_host_path() {
  local encoded="$1"
  python - "${encoded}" <<'PY'
import pathlib
import re
import sys

try:
    value = bytes.fromhex(sys.argv[1]).decode("utf-8")
except (ValueError, UnicodeDecodeError) as exc:
    raise SystemExit("host path is not valid UTF-8 hex") from exc
if not re.fullmatch(r"/[A-Za-z0-9._/-]{1,511}", value):
    raise SystemExit("decoded host path is outside the allowlist")
if ".." in pathlib.Path(value).parts:
    raise SystemExit("decoded host path contains traversal")
print(value, end="")
PY
}

model_cache_host="$(decode_host_path "${COTCODEC_MODEL_CACHE_HOST_HEX}")"
run_root_host="$(decode_host_path "${COTCODEC_RUN_ROOT_HEX}")"
run_dir="${run_root_host}/${SLURM_JOB_ID}"
mkdir -p "${run_dir}"
chmod 700 "${run_dir}"
if [[ ! -d "${model_cache_host}" || -L "${model_cache_host}" ]]; then
  echo "model cache must be a regular non-symlink directory" >&2
  exit 2
fi
model_snapshot="${model_cache_host}/cotcodec-models/${COTCODEC_MODEL_ID}"
model_receipt="${model_cache_host}/cotcodec-receipts/${COTCODEC_MODEL_ID}.json"
if [[ ! -d "${model_snapshot}" || -L "${model_snapshot}" ]]; then
  echo "pinned model snapshot is missing or is a symlink" >&2
  exit 2
fi
if [[ ! -f "${model_receipt}" || -L "${model_receipt}" ]]; then
  echo "pinned model receipt is missing or is a symlink" >&2
  exit 2
fi
actual_receipt_sha256="$(sha256sum "${model_receipt}" | cut -d' ' -f1)"
if [[ "${actual_receipt_sha256}" != "${COTCODEC_MODEL_RECEIPT_SHA256}" ]]; then
  echo "model receipt digest mismatch" >&2
  exit 2
fi
python - "${model_receipt}" \
  "${COTCODEC_MODEL_ID}" \
  "${COTCODEC_MODEL_REVISION}" \
  "${COTCODEC_MODEL_ARTIFACT_ROOT}" <<'PY'
import json
import pathlib
import sys

receipt = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
expected = {
    "model_id": sys.argv[2],
    "revision": sys.argv[3],
    "artifact_root_sha256": sys.argv[4],
    "mode": "full",
    "publication_eligible": True,
    "trust_remote_code": False,
}
for key, value in expected.items():
    if receipt.get(key) != value:
        raise SystemExit(f"model receipt field {key!r} does not match the manifest")
PY

memory_bundle_host=""
memory_bundle_mount=()
if [[ -n "${COTCODEC_MEMORY_BUNDLE_HOST_HEX:-}" \
  || -n "${COTCODEC_MEMORY_BUNDLE_SHA256:-}" ]]; then
  if [[ -z "${COTCODEC_MEMORY_BUNDLE_HOST_HEX:-}" \
    || ! "${COTCODEC_MEMORY_BUNDLE_SHA256:-}" =~ ^[0-9a-f]{64}$ ]]; then
    echo "both memory bundle path and digest are required" >&2
    exit 2
  fi
  memory_bundle_host="$(decode_host_path "${COTCODEC_MEMORY_BUNDLE_HOST_HEX}")"
  if [[ ! -f "${memory_bundle_host}" || -L "${memory_bundle_host}" ]]; then
    echo "memory bundle must be a regular non-symlink file" >&2
    exit 2
  fi
  actual_bundle_sha256="$(sha256sum "${memory_bundle_host}" | cut -d' ' -f1)"
  if [[ "${actual_bundle_sha256}" != "${COTCODEC_MEMORY_BUNDLE_SHA256}" ]]; then
    echo "memory bundle digest mismatch" >&2
    exit 2
  fi
  memory_bundle_mount=(
    --volume "${memory_bundle_host}:/inputs/memory-selection-bundle.json:ro"
  )
fi

public_benchmark_host=""
public_benchmark_mount=()
if [[ -n "${COTCODEC_PUBLIC_BENCHMARK_HOST_HEX:-}" \
  || -n "${COTCODEC_PUBLIC_BENCHMARK_SHA256:-}" \
  || -n "${COTCODEC_PUBLIC_BENCHMARK_SIZE:-}" \
  || -n "${COTCODEC_PUBLIC_BENCHMARK_ID:-}" \
  || -n "${COTCODEC_PUBLIC_BENCHMARK_REVISION:-}" \
  || -n "${COTCODEC_PUBLIC_BENCHMARK_LICENSE:-}" ]]; then
  if [[ -z "${COTCODEC_PUBLIC_BENCHMARK_HOST_HEX:-}" \
    || ! "${COTCODEC_PUBLIC_BENCHMARK_SHA256:-}" =~ ^[0-9a-f]{64}$ \
    || ! "${COTCODEC_PUBLIC_BENCHMARK_SIZE:-}" =~ ^[1-9][0-9]*$ \
    || ! "${COTCODEC_PUBLIC_BENCHMARK_ID:-}" =~ ^[a-z0-9][a-z0-9.-]{0,79}$ \
    || ! "${COTCODEC_PUBLIC_BENCHMARK_REVISION:-}" =~ ^[0-9a-f]{40}$ \
    || ! "${COTCODEC_PUBLIC_BENCHMARK_LICENSE:-}" =~ ^[A-Za-z0-9][A-Za-z0-9.+-]{0,63}$ ]]; then
    echo "all public benchmark provenance fields are required" >&2
    exit 2
  fi
  public_benchmark_host="$(decode_host_path \
    "${COTCODEC_PUBLIC_BENCHMARK_HOST_HEX}")"
  if [[ ! -f "${public_benchmark_host}" || -L "${public_benchmark_host}" ]]; then
    echo "public benchmark must be a regular non-symlink file" >&2
    exit 2
  fi
  actual_benchmark_sha256="$(sha256sum "${public_benchmark_host}" | cut -d' ' -f1)"
  if [[ "${actual_benchmark_sha256}" != "${COTCODEC_PUBLIC_BENCHMARK_SHA256}" ]]; then
    echo "public benchmark digest mismatch" >&2
    exit 2
  fi
  actual_benchmark_size="$(stat -c '%s' "${public_benchmark_host}")"
  if [[ "${actual_benchmark_size}" != "${COTCODEC_PUBLIC_BENCHMARK_SIZE}" ]]; then
    echo "public benchmark size mismatch" >&2
    exit 2
  fi
  public_benchmark_mount=(
    --volume "${public_benchmark_host}:/inputs/longmemeval_s_cleaned.json:ro"
  )
fi

study_artifact_host=""
study_artifact_mount=()
if [[ -n "${COTCODEC_STUDY_ARTIFACT_HOST_HEX:-}" \
  || -n "${COTCODEC_STUDY_ARTIFACT_SHA256:-}" \
  || -n "${COTCODEC_STUDY_ARTIFACT_SIZE:-}" \
  || -n "${COTCODEC_STUDY_ARTIFACT_ID:-}" \
  || -n "${COTCODEC_STUDY_ARTIFACT_REVISION:-}" \
  || -n "${COTCODEC_STUDY_ARTIFACT_LICENSE:-}" ]]; then
  if [[ -z "${COTCODEC_STUDY_ARTIFACT_HOST_HEX:-}" \
    || ! "${COTCODEC_STUDY_ARTIFACT_SHA256:-}" =~ ^[0-9a-f]{64}$ \
    || ! "${COTCODEC_STUDY_ARTIFACT_SIZE:-}" =~ ^[1-9][0-9]*$ \
    || ! "${COTCODEC_STUDY_ARTIFACT_ID:-}" =~ ^[a-z0-9][a-z0-9.-]{0,79}$ \
    || ! "${COTCODEC_STUDY_ARTIFACT_REVISION:-}" =~ ^[0-9a-f]{40}$ \
    || ! "${COTCODEC_STUDY_ARTIFACT_LICENSE:-}" =~ ^[A-Za-z0-9][A-Za-z0-9.+-]{0,63}$ ]]; then
    echo "all study artifact provenance fields are required" >&2
    exit 2
  fi
  study_artifact_host="$(decode_host_path \
    "${COTCODEC_STUDY_ARTIFACT_HOST_HEX}")"
  if [[ ! -f "${study_artifact_host}" || -L "${study_artifact_host}" ]]; then
    echo "study artifact must be a regular non-symlink file" >&2
    exit 2
  fi
  if [[ "$(sha256sum "${study_artifact_host}" | cut -d' ' -f1)" \
      != "${COTCODEC_STUDY_ARTIFACT_SHA256}" ]]; then
    echo "study artifact digest mismatch" >&2
    exit 2
  fi
  if [[ "$(stat -c '%s' "${study_artifact_host}")" \
      != "${COTCODEC_STUDY_ARTIFACT_SIZE}" ]]; then
    echo "study artifact size mismatch" >&2
    exit 2
  fi
  study_artifact_mount=(
    --volume "${study_artifact_host}:/inputs/study-artifact.json:ro"
  )
fi

publication_capsule_host=""
publication_attestation_host=""
publication_trust_store_host=""
control_matrix_host=""
publication_wave_host=""
claim_admission_mounts=()
if [[ -n "${COTCODEC_PUBLICATION_CAPSULE_HOST_HEX:-}" \
  || -n "${COTCODEC_PUBLICATION_CAPSULE_FILE_SHA256:-}" \
  || -n "${COTCODEC_PUBLICATION_CAPSULE_SHA256:-}" \
  || -n "${COTCODEC_PUBLICATION_ATTESTATION_HOST_HEX:-}" \
  || -n "${COTCODEC_PUBLICATION_ATTESTATION_FILE_SHA256:-}" \
  || -n "${COTCODEC_PUBLICATION_TRUST_STORE_HOST_HEX:-}" \
  || -n "${COTCODEC_PUBLICATION_TRUST_STORE_SHA256:-}" \
  || -n "${COTCODEC_CONTROL_MATRIX_HOST_HEX:-}" \
  || -n "${COTCODEC_CONTROL_MATRIX_FILE_SHA256:-}" \
  || -n "${COTCODEC_CONTROL_MATRIX_SHA256:-}" \
  || -n "${COTCODEC_TASK_MANIFEST_SHA256:-}" \
  || -n "${COTCODEC_CLAIM_WAVE_SHA256:-}" \
  || -n "${COTCODEC_CLAIM_WAVE_HOST_HEX:-}" \
  || -n "${COTCODEC_CLAIM_WAVE_FILE_SHA256:-}" \
  || -n "${COTCODEC_MEMORY_CONTROL_ID:-}" \
  || -n "${COTCODEC_MEMORY_SYSTEM_ID:-}" ]]; then
  for value in \
    "${COTCODEC_PUBLICATION_CAPSULE_FILE_SHA256:-}" \
    "${COTCODEC_PUBLICATION_CAPSULE_SHA256:-}" \
    "${COTCODEC_PUBLICATION_ATTESTATION_FILE_SHA256:-}" \
    "${COTCODEC_PUBLICATION_TRUST_STORE_SHA256:-}" \
    "${COTCODEC_CONTROL_MATRIX_FILE_SHA256:-}" \
    "${COTCODEC_CONTROL_MATRIX_SHA256:-}" \
    "${COTCODEC_TASK_MANIFEST_SHA256:-}" \
    "${COTCODEC_CLAIM_WAVE_SHA256:-}" \
    "${COTCODEC_CLAIM_WAVE_FILE_SHA256:-}"; do
    if [[ ! "${value}" =~ ^[0-9a-f]{64}$ ]]; then
      echo "claim admission digests must be lowercase 64-hex values" >&2
      exit 2
    fi
  done
  if [[ -z "${COTCODEC_PUBLICATION_CAPSULE_HOST_HEX:-}" \
    || -z "${COTCODEC_PUBLICATION_ATTESTATION_HOST_HEX:-}" \
    || -z "${COTCODEC_PUBLICATION_TRUST_STORE_HOST_HEX:-}" \
    || -z "${COTCODEC_CONTROL_MATRIX_HOST_HEX:-}" \
    || -z "${COTCODEC_CLAIM_WAVE_HOST_HEX:-}" \
    || ! "${COTCODEC_MEMORY_CONTROL_ID:-}" =~ ^[a-z0-9][a-z0-9.-]{0,79}$ \
    || ! "${COTCODEC_MEMORY_SYSTEM_ID:-}" =~ ^[a-z0-9][a-z0-9.-]{0,79}$ \
    || -z "${memory_bundle_host}" ]]; then
    echo "claim admission requires every capsule, matrix, control, and bundle field" >&2
    exit 2
  fi
  publication_capsule_host="$(decode_host_path \
    "${COTCODEC_PUBLICATION_CAPSULE_HOST_HEX}")"
  publication_attestation_host="$(decode_host_path \
    "${COTCODEC_PUBLICATION_ATTESTATION_HOST_HEX}")"
  publication_trust_store_host="$(decode_host_path \
    "${COTCODEC_PUBLICATION_TRUST_STORE_HOST_HEX}")"
  if [[ "${publication_trust_store_host}" \
      != "/etc/cotcodec/trust/publication-attestors.json" ]]; then
    echo "publication trust store must use the administrator-owned fixed path" >&2
    exit 2
  fi
  control_matrix_host="$(decode_host_path "${COTCODEC_CONTROL_MATRIX_HOST_HEX}")"
  publication_wave_host="$(decode_host_path "${COTCODEC_CLAIM_WAVE_HOST_HEX}")"
  for path in \
    "${publication_capsule_host}" \
    "${publication_attestation_host}" \
    "${publication_trust_store_host}" \
    "${control_matrix_host}" \
    "${publication_wave_host}"; do
    if [[ ! -f "${path}" || -L "${path}" ]]; then
      echo "claim admission inputs must be regular non-symlink files" >&2
      exit 2
    fi
  done
  if [[ "$(sha256sum "${publication_capsule_host}" | cut -d' ' -f1)" \
      != "${COTCODEC_PUBLICATION_CAPSULE_FILE_SHA256}" \
    || "$(sha256sum "${publication_attestation_host}" | cut -d' ' -f1)" \
      != "${COTCODEC_PUBLICATION_ATTESTATION_FILE_SHA256}" \
    || "$(sha256sum "${publication_trust_store_host}" | cut -d' ' -f1)" \
      != "${COTCODEC_PUBLICATION_TRUST_STORE_SHA256}" \
    || "$(sha256sum "${control_matrix_host}" | cut -d' ' -f1)" \
      != "${COTCODEC_CONTROL_MATRIX_FILE_SHA256}" \
    || "$(sha256sum "${publication_wave_host}" | cut -d' ' -f1)" \
      != "${COTCODEC_CLAIM_WAVE_FILE_SHA256}" ]]; then
    echo "claim admission file digest mismatch" >&2
    exit 2
  fi
  python - \
    "${publication_capsule_host}" \
    "${control_matrix_host}" \
    "${publication_wave_host}" \
    "${COTCODEC_PUBLICATION_CAPSULE_SHA256}" \
    "${COTCODEC_CONTROL_MATRIX_SHA256}" \
    "${COTCODEC_TASK_MANIFEST_SHA256}" \
    "${COTCODEC_MEMORY_CONTROL_ID}" \
    "${COTCODEC_MEMORY_SYSTEM_ID}" \
    "${COTCODEC_MEMORY_BUNDLE_SEMANTIC_SHA256}" \
    "${COTCODEC_IMAGE_ID}" \
    "${COTCODEC_GIT_SHA}" \
    "${COTCODEC_SOURCE_SHA256}" <<'PY'
import hashlib
import json
import pathlib
import sys


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


capsule = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
matrix = json.loads(pathlib.Path(sys.argv[2]).read_text(encoding="utf-8"))
wave = json.loads(pathlib.Path(sys.argv[3]).read_text(encoding="utf-8"))
capsule_root = capsule.pop("capsule_sha256", None)
if capsule_root != sys.argv[4] or hashlib.sha256(canonical(capsule).encode()).hexdigest() != capsule_root:
    raise SystemExit("publication capsule semantic root is invalid")
matrix_root = matrix.pop("matrix_sha256", None)
if matrix_root != sys.argv[5] or hashlib.sha256(canonical(matrix).encode()).hexdigest() != matrix_root:
    raise SystemExit("control matrix semantic root is invalid")
wave_root = wave.pop("wave_sha256", None)
if wave_root != __import__("os").environ["COTCODEC_CLAIM_WAVE_SHA256"] or hashlib.sha256(canonical(wave).encode()).hexdigest() != wave_root:
    raise SystemExit("publication wave semantic root is invalid")
if (
    wave.get("publication_capsule_sha256") != capsule_root
    or wave.get("control_matrix_sha256") != matrix_root
    or wave.get("batch_script_sha256") != __import__("os").environ["COTCODEC_BATCH_SHA256"]
    or wave.get("model_id") != __import__("os").environ["COTCODEC_MODEL_ID"]
    or wave.get("model_revision") != __import__("os").environ["COTCODEC_MODEL_REVISION"]
    or wave.get("model_receipt_sha256") != __import__("os").environ["COTCODEC_MODEL_RECEIPT_SHA256"]
    or wave.get("model_artifact_root_sha256") != __import__("os").environ["COTCODEC_MODEL_ARTIFACT_ROOT"]
):
    raise SystemExit("publication wave differs from the submitted runtime")
if (
    capsule.get("status") != "SEALED_PUBLICATION_CAPSULE_CANDIDATE"
    or capsule.get("publication_ready") is not False
    or capsule.get("runtime", {}).get("batch_script_sha256")
    != __import__("os").environ["COTCODEC_BATCH_SHA256"]
):
    raise SystemExit("publication capsule does not bind the active batch script")
source = capsule.get("source", {})
image = capsule.get("image", {})
if (
    image.get("image_id") != sys.argv[10]
    or source.get("git_sha") != sys.argv[11]
    or source.get("archive_sha256") != sys.argv[12]
):
    raise SystemExit("publication capsule differs from the submitted job")
task_source = matrix.get("task_source", {})
if task_source.get("task_manifest_sha256") != sys.argv[6]:
    raise SystemExit("control matrix task manifest differs from the submitted job")
matches = [
    row
    for row in matrix.get("controls", [])
    if isinstance(row, dict) and row.get("control_id") == sys.argv[7]
]
if len(matches) != 1:
    raise SystemExit("claim control is absent or duplicated in the matrix")
control = matches[0]
if (
    control.get("system_id") != sys.argv[8]
    or control.get("bundle_semantic_sha256") != sys.argv[9]
    or control.get("bundle_sha256") != sys.argv[9]
    or control.get("bundle_file_sha256") != __import__("os").environ[
        "COTCODEC_MEMORY_BUNDLE_SHA256"
    ]
    or control.get("eligible_for_primary") is not True
):
    raise SystemExit("claim control identity or eligibility differs from the matrix")
PY
  claim_admission_mounts=(
    --volume "${publication_capsule_host}:/inputs/publication-capsule.json:ro"
    --volume "${publication_attestation_host}:/inputs/publication-capsule-attestation.json:ro"
    --volume "${publication_trust_store_host}:/etc/cotcodec/trust/publication-attestors.json:ro"
    --volume "${control_matrix_host}:/inputs/control-matrix-manifest.json:ro"
    --volume "${publication_wave_host}:/inputs/publication-wave-contract.json:ro"
  )
fi

if ! command -v docker >/dev/null 2>&1 || ! docker info >/dev/null 2>&1; then
  echo "Docker is unavailable to the Slurm job user" >&2
  exit 2
fi
if [[ -n "${publication_capsule_host}" ]]; then
  docker run --rm --network none --read-only --cap-drop ALL \
    --security-opt no-new-privileges --user 65534:65534 \
    --volume "${publication_capsule_host}:/inputs/publication-capsule.json:ro" \
    --volume "${publication_attestation_host}:/inputs/publication-capsule-attestation.json:ro" \
    --volume "${publication_trust_store_host}:/etc/cotcodec/trust/publication-attestors.json:ro" \
    --volume "${control_matrix_host}:/inputs/control-matrix-manifest.json:ro" \
    --volume "${publication_wave_host}:/inputs/publication-wave-contract.json:ro" \
    "${COTCODEC_IMAGE_ID}" \
    python scripts/verify_publication_attestation.py \
      --capsule /inputs/publication-capsule.json \
      --matrix /inputs/control-matrix-manifest.json \
      --experiment experiments/memory/stage1-longmemeval-screen.yaml \
      --wave /inputs/publication-wave-contract.json \
      --batch-script infra/slurm/host-single-node/docker-research.sbatch \
      --attestation /inputs/publication-capsule-attestation.json \
      --trust-store /etc/cotcodec/trust/publication-attestors.json \
      --expected-trust-store-sha256 "${COTCODEC_PUBLICATION_TRUST_STORE_SHA256}" \
    > "${run_dir}/publication-attestation-verification.json"
fi
actual_image_id="$(docker image inspect --format '{{.Id}}' "${COTCODEC_IMAGE_ID}")"
if [[ "${actual_image_id}" != "${COTCODEC_IMAGE_ID}" ]]; then
  echo "Docker resolved a different image ID" >&2
  exit 2
fi
image_git="$(docker image inspect --format \
  '{{index .Config.Labels "org.opencontainers.image.revision"}}' "${COTCODEC_IMAGE_ID}")"
image_source="$(docker image inspect --format \
  '{{index .Config.Labels "org.opencontainers.image.source-tree-sha256"}}' \
  "${COTCODEC_IMAGE_ID}")"
if [[ "${image_git}" != "${COTCODEC_GIT_SHA}" \
  || "${image_source}" != "${COTCODEC_SOURCE_SHA256}" ]]; then
  echo "Docker image labels do not match the submitted source provenance" >&2
  exit 2
fi

gpu_devices="${CUDA_VISIBLE_DEVICES:-${SLURM_JOB_GPUS:-}}"
if [[ ! "${gpu_devices}" =~ ^[0-7](,[0-7])*$ ]]; then
  echo "Slurm did not expose a simple physical GPU device list" >&2
  exit 2
fi
gpu_count="$(awk -F, '{print NF}' <<< "${gpu_devices}")"
if [[ "${gpu_count}" -ne "${COTCODEC_EXPECTED_GPUS}" ]]; then
  echo "Slurm GPU allocation does not match the manifest" >&2
  exit 2
fi
if [[ "$(tr ',' '\n' <<< "${gpu_devices}" | sort -u | wc -l | tr -d ' ')" \
  -ne "${gpu_count}" ]]; then
  echo "Slurm GPU device list contains duplicates" >&2
  exit 2
fi
if nvidia-smi -i "${gpu_devices}" --query-gpu=name --format=csv,noheader \
  | grep -qv 'H100'; then
  echo "the Slurm allocation contains a non-H100 GPU" >&2
  exit 2
fi

if [[ -n "${COTCODEC_PREDECESSOR_JOB_ID:-}" ]]; then
  if [[ ! "${COTCODEC_PREDECESSOR_JOB_ID}" =~ ^[1-9][0-9]{0,19}$ \
    || ! "${COTCODEC_RESUME_SUBPATH:-}" =~ ^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$ \
    || "/${COTCODEC_RESUME_SUBPATH}/" == *"/../"* ]]; then
    echo "resume job or subpath is unsafe" >&2
    exit 2
  fi
  python - "${run_root_host}" "${run_dir}" \
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
    raise SystemExit("resume directory escaped the registered run root")
job_env_path = predecessor / "job.env"
if not job_env_path.is_file():
    raise SystemExit("predecessor job.env is missing")
actual = {}
for line in job_env_path.read_text(encoding="utf-8").splitlines():
    key, separator, value = line.partition("=")
    if separator and key in {
        "git_sha",
        "source_sha256",
        "image_id",
        "batch_script_sha256",
        "model_receipt_sha256",
        "model_artifact_root",
        "memory_bundle_sha256",
        "memory_bundle_semantic_sha256",
        "public_benchmark_sha256",
        "public_benchmark_size",
        "public_benchmark_revision",
        "study_artifact_sha256",
        "study_artifact_size",
        "study_artifact_id",
        "study_artifact_revision",
        "study_artifact_license",
        "publication_capsule_sha256",
        "publication_attestation_file_sha256",
        "publication_trust_store_sha256",
        "control_matrix_sha256",
        "task_manifest_sha256",
        "claim_wave_sha256",
        "claim_wave_file_sha256",
        "memory_control_id",
        "memory_system_id",
    }:
        actual[key] = value
expected = {
    "git_sha": os.environ["COTCODEC_GIT_SHA"],
    "source_sha256": os.environ["COTCODEC_SOURCE_SHA256"],
    "image_id": os.environ["COTCODEC_IMAGE_ID"],
    "batch_script_sha256": os.environ["COTCODEC_BATCH_SHA256"],
    "model_receipt_sha256": os.environ["COTCODEC_MODEL_RECEIPT_SHA256"],
    "model_artifact_root": os.environ["COTCODEC_MODEL_ARTIFACT_ROOT"],
    "memory_bundle_sha256": os.environ.get("COTCODEC_MEMORY_BUNDLE_SHA256", "none"),
    "memory_bundle_semantic_sha256": os.environ.get(
        "COTCODEC_MEMORY_BUNDLE_SEMANTIC_SHA256", "none"
    ),
    "public_benchmark_sha256": os.environ.get(
        "COTCODEC_PUBLIC_BENCHMARK_SHA256", "none"
    ),
    "public_benchmark_size": os.environ.get("COTCODEC_PUBLIC_BENCHMARK_SIZE", "none"),
    "public_benchmark_revision": os.environ.get(
        "COTCODEC_PUBLIC_BENCHMARK_REVISION", "none"
    ),
    "study_artifact_sha256": os.environ.get(
        "COTCODEC_STUDY_ARTIFACT_SHA256", "none"
    ),
    "study_artifact_size": os.environ.get("COTCODEC_STUDY_ARTIFACT_SIZE", "none"),
    "study_artifact_id": os.environ.get("COTCODEC_STUDY_ARTIFACT_ID", "none"),
    "study_artifact_revision": os.environ.get(
        "COTCODEC_STUDY_ARTIFACT_REVISION", "none"
    ),
    "study_artifact_license": os.environ.get(
        "COTCODEC_STUDY_ARTIFACT_LICENSE", "none"
    ),
    "publication_capsule_sha256": os.environ.get(
        "COTCODEC_PUBLICATION_CAPSULE_SHA256", "none"
    ),
    "publication_attestation_file_sha256": os.environ.get(
        "COTCODEC_PUBLICATION_ATTESTATION_FILE_SHA256", "none"
    ),
    "publication_trust_store_sha256": os.environ.get(
        "COTCODEC_PUBLICATION_TRUST_STORE_SHA256", "none"
    ),
    "control_matrix_sha256": os.environ.get("COTCODEC_CONTROL_MATRIX_SHA256", "none"),
    "task_manifest_sha256": os.environ.get("COTCODEC_TASK_MANIFEST_SHA256", "none"),
    "claim_wave_sha256": os.environ.get("COTCODEC_CLAIM_WAVE_SHA256", "none"),
    "claim_wave_file_sha256": os.environ.get(
        "COTCODEC_CLAIM_WAVE_FILE_SHA256", "none"
    ),
    "memory_control_id": os.environ.get("COTCODEC_MEMORY_CONTROL_ID", "none"),
    "memory_system_id": os.environ.get("COTCODEC_MEMORY_SYSTEM_ID", "none"),
}
if actual != expected:
    raise SystemExit("predecessor provenance does not match this job")
source = (predecessor / subpath).resolve()
destination = (run_dir / subpath).resolve()
if predecessor not in source.parents or run_dir not in destination.parents:
    raise SystemExit("resume subpath escaped its job directory")
if not source.is_dir() or destination.exists():
    raise SystemExit("resume source is missing or destination already exists")
if any(path.is_symlink() for path in source.rglob("*")):
    raise SystemExit("resume source must not contain symbolic links")
destination.parent.mkdir(parents=True, exist_ok=True)
shutil.copytree(source, destination)
receipt = {
    "schema_version": 1,
    "predecessor_job_id": predecessor_id,
    "resume_subpath": subpath.as_posix(),
    **expected,
}
(run_dir / "resume-receipt.json").write_text(
    json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
PY
fi

python - "${run_dir}" <<'PY'
import json
import os
import pathlib
import sys

run_dir = pathlib.Path(sys.argv[1])
for filename, variable in (
    ("command.json", "COTCODEC_COMMAND_JSON_HEX"),
    ("manifest.json", "COTCODEC_MANIFEST_JSON_HEX"),
):
    payload = json.loads(bytes.fromhex(os.environ[variable]))
    (run_dir / filename).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
PY
cp "${model_receipt}" "${run_dir}/model-receipt.json"
cp "$0" "${run_dir}/docker-research.sbatch"
if [[ -n "${publication_capsule_host}" ]]; then
  cp "${publication_capsule_host}" "${run_dir}/publication-capsule.json"
  cp "${publication_attestation_host}" "${run_dir}/publication-capsule-attestation.json"
  cp "${publication_trust_store_host}" "${run_dir}/publication-trust-store.json"
  cp "${control_matrix_host}" "${run_dir}/control-matrix-manifest.json"
  cp "${publication_wave_host}" "${run_dir}/publication-wave-contract.json"
fi
if [[ -n "${study_artifact_host}" ]]; then
  cp "${study_artifact_host}" "${run_dir}/study-artifact.json"
fi
docker image inspect "${COTCODEC_IMAGE_ID}" > "${run_dir}/image-inspect.json"
{
  uname -a
  docker version
  docker info
  nvidia-smi -i "${gpu_devices}" \
    --query-gpu=index,name,uuid,memory.total,driver_version --format=csv,noheader
  scontrol show job "${SLURM_JOB_ID}"
} > "${run_dir}/system.txt" 2>&1
{
  echo "job_id=${SLURM_JOB_ID}"
  echo "predecessor_job_id=${COTCODEC_PREDECESSOR_JOB_ID:-none}"
  echo "git_sha=${COTCODEC_GIT_SHA}"
  echo "source_sha256=${COTCODEC_SOURCE_SHA256}"
  echo "image_id=${COTCODEC_IMAGE_ID}"
  echo "batch_script_sha256=${COTCODEC_BATCH_SHA256}"
  echo "model_id=${COTCODEC_MODEL_ID}"
  echo "model_revision=${COTCODEC_MODEL_REVISION}"
  echo "model_receipt_sha256=${COTCODEC_MODEL_RECEIPT_SHA256}"
  echo "model_artifact_root=${COTCODEC_MODEL_ARTIFACT_ROOT}"
  echo "memory_bundle_sha256=${COTCODEC_MEMORY_BUNDLE_SHA256:-none}"
  echo "memory_bundle_semantic_sha256=${COTCODEC_MEMORY_BUNDLE_SEMANTIC_SHA256:-none}"
  echo "public_benchmark_id=${COTCODEC_PUBLIC_BENCHMARK_ID:-none}"
  echo "public_benchmark_revision=${COTCODEC_PUBLIC_BENCHMARK_REVISION:-none}"
  echo "public_benchmark_license=${COTCODEC_PUBLIC_BENCHMARK_LICENSE:-none}"
  echo "public_benchmark_sha256=${COTCODEC_PUBLIC_BENCHMARK_SHA256:-none}"
  echo "public_benchmark_size=${COTCODEC_PUBLIC_BENCHMARK_SIZE:-none}"
  echo "study_artifact_id=${COTCODEC_STUDY_ARTIFACT_ID:-none}"
  echo "study_artifact_revision=${COTCODEC_STUDY_ARTIFACT_REVISION:-none}"
  echo "study_artifact_license=${COTCODEC_STUDY_ARTIFACT_LICENSE:-none}"
  echo "study_artifact_sha256=${COTCODEC_STUDY_ARTIFACT_SHA256:-none}"
  echo "study_artifact_size=${COTCODEC_STUDY_ARTIFACT_SIZE:-none}"
  echo "publication_capsule_sha256=${COTCODEC_PUBLICATION_CAPSULE_SHA256:-none}"
  echo "publication_attestation_file_sha256=${COTCODEC_PUBLICATION_ATTESTATION_FILE_SHA256:-none}"
  echo "publication_trust_store_sha256=${COTCODEC_PUBLICATION_TRUST_STORE_SHA256:-none}"
  echo "control_matrix_sha256=${COTCODEC_CONTROL_MATRIX_SHA256:-none}"
  echo "task_manifest_sha256=${COTCODEC_TASK_MANIFEST_SHA256:-none}"
  echo "claim_wave_sha256=${COTCODEC_CLAIM_WAVE_SHA256:-none}"
  echo "claim_wave_file_sha256=${COTCODEC_CLAIM_WAVE_FILE_SHA256:-none}"
  echo "memory_control_id=${COTCODEC_MEMORY_CONTROL_ID:-none}"
  echo "memory_system_id=${COTCODEC_MEMORY_SYSTEM_ID:-none}"
  echo "randomness_contract=${COTCODEC_RANDOMNESS_CONTRACT}"
  echo "seeds=${COTCODEC_SEEDS:-unknown}"
  echo "started_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "nodelist=${SLURM_JOB_NODELIST}"
  echo "gpu_devices=${gpu_devices}"
} > "${run_dir}/job.env"

checkpoint_marker="${run_dir}/checkpoint.ready"
termination_file="${run_dir}/termination.env"
container_name="cotcodec-${SLURM_JOB_ID}"
container_created=false
termination_reason="starting"

write_termination() {
  local exit_code="$1"
  {
    echo "job_id=${SLURM_JOB_ID}"
    echo "reason=${termination_reason}"
    echo "exit_code=${exit_code}"
    echo "finished_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "checkpoint_ready=$([[ -f "${checkpoint_marker}" ]] && echo true || echo false)"
  } > "${termination_file}"
}

forward_signal() {
  local signal_name="$1"
  termination_reason="signal_${signal_name}_checkpoint_requested"
  if [[ "${container_created}" == true ]] \
    && [[ "$(docker inspect --format '{{.State.Running}}' "${container_name}" 2>/dev/null \
      || echo false)" == true ]]; then
    docker kill --signal "${signal_name}" "${container_name}" >/dev/null 2>&1 || true
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
  if [[ "${container_created}" == true ]] \
    && [[ "$(docker inspect --format '{{.State.Running}}' "${container_name}" 2>/dev/null \
      || echo false)" == true ]]; then
    docker kill --signal TERM "${container_name}" >/dev/null 2>&1 || true
  fi
}

on_exit() {
  local exit_code="$?"
  if [[ "${container_created}" == true ]]; then
    docker inspect "${container_name}" > "${run_dir}/container-final-inspect.json" \
      2>/dev/null || true
    docker logs "${container_name}" > "${run_dir}/container.log" 2>&1 || true
    docker rm --force "${container_name}" >/dev/null 2>&1 || true
  fi
  if [[ "${termination_reason}" == running ]]; then
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

cpu_list="$(awk '/Cpus_allowed_list/ {print $2}' /proc/self/status)"
if [[ -z "${cpu_list}" ]]; then
  echo "could not determine the Slurm CPU affinity" >&2
  exit 2
fi
memory_limit_mb="${SLURM_MEM_PER_NODE:-65536}"
if [[ ! "${memory_limit_mb}" =~ ^[1-9][0-9]*$ ]]; then
  echo "Slurm memory limit is unavailable" >&2
  exit 2
fi
docker_gpu_request="device=${gpu_devices}"
if [[ "${gpu_count}" -gt 1 ]]; then
  # Docker's comma-separated device grammar requires the value itself to retain
  # quotes (the documented CLI form is --gpus '"device=0,1"').
  docker_gpu_request="\"device=${gpu_devices}\""
fi

docker create \
  --name "${container_name}" \
  --entrypoint /bin/bash \
  --gpus "${docker_gpu_request}" \
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
  --workdir /workspace/cotcodec \
  --env COTCODEC_COMMAND_JSON_HEX="${COTCODEC_COMMAND_JSON_HEX}" \
  --env COTCODEC_GIT_SHA="${COTCODEC_GIT_SHA}" \
  --env COTCODEC_SOURCE_SHA256="${COTCODEC_SOURCE_SHA256}" \
  --env COTCODEC_EXPECTED_GPUS="${COTCODEC_EXPECTED_GPUS}" \
  --env COTCODEC_OUTPUT_DIR=/outputs \
  --env COTCODEC_CHECKPOINT_MARKER=/outputs/checkpoint.ready \
  --env COTCODEC_MODEL_ID="${COTCODEC_MODEL_ID}" \
  --env USER=cotcodec \
  --env LOGNAME=cotcodec \
  --env HOME=/tmp/home \
  --env XDG_CACHE_HOME=/tmp/cache \
  --env TORCH_HOME=/tmp/torch \
  --env TORCHINDUCTOR_CACHE_DIR=/tmp/torchinductor \
  --env CUBLAS_WORKSPACE_CONFIG=:4096:8 \
  --env HF_HUB_OFFLINE=1 \
  --env TRANSFORMERS_OFFLINE=1 \
  --env HF_HOME=/tmp/huggingface \
  --env PYTHONUNBUFFERED=1 \
  --volume "${run_dir}:/outputs:rw" \
  --volume "${model_cache_host}:/model-cache:ro" \
  "${memory_bundle_mount[@]}" \
  "${public_benchmark_mount[@]}" \
  "${study_artifact_mount[@]}" \
  "${claim_admission_mounts[@]}" \
  "${COTCODEC_IMAGE_ID}" \
  -lc 'python scripts/verify_compute_provenance.py > /outputs/provenance-verification.txt && bash scripts/check_compute_env.sh container > /outputs/container-doctor.txt && python scripts/fetch_open_model.py --model-root /model-cache/cotcodec-models --receipt-root /model-cache/cotcodec-receipts verify "$COTCODEC_MODEL_ID" > /outputs/model-verification.txt && exec python scripts/exec_research_workload.py' \
  > "${run_dir}/container-id.txt"
container_created=true
docker inspect "${container_name}" > "${run_dir}/container-created-inspect.json"

termination_reason="running"
set +e
docker start --attach "${container_name}"
workload_exit_code="$?"
set -e
if [[ "${termination_reason}" == running ]]; then
  if [[ "${workload_exit_code}" -eq 0 ]]; then
    termination_reason="completed"
  else
    termination_reason="workload_failed"
  fi
fi
exit "${workload_exit_code}"
