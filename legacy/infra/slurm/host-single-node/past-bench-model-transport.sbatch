#!/usr/bin/env bash
#SBATCH --job-name=past-qwen-transport
#SBATCH --partition=research
#SBATCH --gres=gpu:h100:2
#SBATCH --cpus-per-task=32
#SBATCH --mem=160G
#SBATCH --time=02:00:00
#SBATCH --signal=B:USR1@180
#SBATCH --output=/home/kevin/cotcodec-runs/past-bench/slurm-%j.out
#SBATCH --error=/home/kevin/cotcodec-runs/past-bench/slurm-%j.err

set -Eeuo pipefail
umask 077

if [[ $# -ne 4 ]]; then
  echo "usage: $0 MANIFEST MANIFEST_FILE_SHA256 MANIFEST_SHA256 OUTPUT_ROOT" >&2
  exit 2
fi

manifest_source=$1
manifest_file_sha256=$2
manifest_sha256=$3
output_root=$4

: "${SLURM_JOB_ID:?PAST model transport must execute inside Slurm}"
: "${CUDA_VISIBLE_DEVICES:?Slurm did not map the allocated H100s}"
: "${SLURM_JOB_GPUS:?Slurm did not expose the allocated physical GPUs}"
runtime_uid=$(id -u)
runtime_gid=$(id -g)
if [[ ! ${runtime_uid} =~ ^[0-9]+$ \
  || ! ${runtime_gid} =~ ^[0-9]+$ \
  || ${runtime_uid} == 0 \
  || ${runtime_gid} == 0 ]]; then
  echo "PAST model transport requires a non-root Slurm identity" >&2
  exit 2
fi
runtime_identity="${runtime_uid}:${runtime_gid}"

if [[ ! ${manifest_source} =~ ^/home/kevin/cotcodec-runs/past-bench/inputs/[a-z0-9._/-]{1,384}\.json$ \
  || ! ${manifest_file_sha256} =~ ^[0-9a-f]{64}$ \
  || ! ${manifest_sha256} =~ ^[0-9a-f]{64}$ \
  || ! ${output_root} =~ ^/home/kevin/cotcodec-runs/past-bench/model-transport-[a-z0-9._-]{1,96}$ ]]; then
  echo "unsafe PAST transport argument" >&2
  exit 2
fi
IFS=, read -r -a allocated_gpus <<<"${SLURM_JOB_GPUS}"
if [[ ${#allocated_gpus[@]} -ne 2 \
  || ${SLURM_GPUS_ON_NODE:-} != 2 \
  || ! -f ${manifest_source} \
  || -L ${manifest_source} \
  || -e ${output_root} \
  || -L ${output_root} ]]; then
  echo "invalid PAST transport allocation, manifest, or output root" >&2
  exit 2
fi
while IFS= read -r gpu_name; do
  if [[ ${gpu_name} != *H100* ]]; then
    echo "PAST transport requires exactly two Slurm-owned H100s" >&2
    exit 2
  fi
done < <(nvidia-smi -i "${SLURM_JOB_GPUS}" --query-gpu=name --format=csv,noheader)
mapfile -t allocated_gpu_uuids < <(
  nvidia-smi -i "${SLURM_JOB_GPUS}" --query-gpu=uuid --format=csv,noheader
)
if [[ ${#allocated_gpu_uuids[@]} -ne 2 \
  || ! ${allocated_gpu_uuids[0]} =~ ^GPU-[A-Fa-f0-9-]{16,80}$ \
  || ! ${allocated_gpu_uuids[1]} =~ ^GPU-[A-Fa-f0-9-]{16,80}$ \
  || ${allocated_gpu_uuids[0]} == "${allocated_gpu_uuids[1]}" ]]; then
  echo "Slurm-owned H100 UUID roster is invalid" >&2
  exit 2
fi
allocated_gpu_uuid_csv=$(IFS=,; echo "${allocated_gpu_uuids[*]}")

mkdir -m 0700 "${output_root}"
manifest="${output_root}/transport-manifest.json"
cp --reflink=never --no-preserve=mode,ownership,timestamps "${manifest_source}" "${manifest}"
chmod 0400 "${manifest}"
if [[ $(sha256sum "${manifest}" | cut -d' ' -f1) != ${manifest_file_sha256} ]]; then
  echo "transport manifest file digest mismatch" >&2
  exit 2
fi

mapfile -t fields < <(
  python3 - "${manifest}" "${manifest_sha256}" "${output_root}/server-argv.json" <<'PY'
import hashlib
import json
import pathlib
import re
import sys

path = pathlib.Path(sys.argv[1])
expected_semantic = sys.argv[2]
argv_output = pathlib.Path(sys.argv[3])
manifest = json.loads(path.read_text(encoding="utf-8"))
stored_semantic = manifest.pop("manifest_sha256", None)
canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
actual_semantic = hashlib.sha256(canonical.encode()).hexdigest()
if stored_semantic != expected_semantic or actual_semantic != expected_semantic:
    raise SystemExit("transport manifest semantic digest mismatch")
expected_top = {
    "schema_version": 1,
    "status": "COMPILED_PAST_QWEN_INTERNAL_TRANSPORT_DISCOVERY_ONLY",
    "scientific_result": False,
    "publication_ready": False,
}
for key, value in expected_top.items():
    if manifest.get(key) != value:
        raise SystemExit(f"transport manifest field {key!r} is invalid")
containment = manifest.get("containment") or {}
expected_containment = {
    "scheduler": "slurm",
    "gpu_type": "H100",
    "gpus": 2,
    "docker_network": "internal-only-no-host-port",
    "external_egress": False,
    "pull_at_runtime": False,
    "model_mount": "read-only",
    "past_rootfs": "read-only",
    "vllm_rootfs": "read-only",
}
if containment != expected_containment:
    raise SystemExit("transport containment contract drifted")
if manifest.get("budget") != {"minutes": 120, "max_gpu_hours": 4}:
    raise SystemExit("transport budget drifted")

past = manifest.get("past") or {}
vllm = manifest.get("vllm") or {}
model = manifest.get("model") or {}
server = manifest.get("server") or {}
tools = manifest.get("execution_tools") or {}
expected_past = {
    "image_id": "sha256:ebcf7eea7f1977f03e5e007edf265fcd120edadcd6d48e81f63df70715783150",
    "image_repo_digest": "127.0.0.1:5000/cotcodec-past@sha256:fd26757a9c5915a6059f8016235a7bdb587e67234e8c739b9a8fb310843b8bb4",
    "image_archive_sha256": "2f97fa8c18528eff8fd2e335e851255be280a20d2a3a81f74eab7485c0db285b",
    "sbom_sha256": "37f7eb4eab884c7d924e718f9ed8389102a61fe43b36d48e29249996bf857fff",
    "source_receipt_sha256": "5e686206db8d1447d1b18d27bfffdd792f45c9d3418aedc7c15a5d134d6a6a5c",
    "runtime_receipt_sha256": "27fb11233ecb18bbdc60ca1c7c0100284b93c87b9fb5d07eb461d028bfd4a64d",
}
expected_vllm = {
    "image_id": "sha256:f26809eb13339cbc59c3d0cc972f8c4997830dc8d2121cf18089cb122834e10d",
    "image_repo_digest": "docker.io/vllm/vllm-openai@sha256:f0b9a0dc75a9fca3b6811e3279367b2d6a448055a000bfd13859587d74cef268",
    "image_archive_sha256": "aecb8b90cd6378c1440c60efd3eef1d98d189e47110539350858dfde2ec9d0f4",
    "receipt_sha256": "ae800444ba8a1912cbe8932d2e6d54d68266a0dc6c6166739eae58b0db7c485b",
    "import_doctor_sha256": "ea2525af9f350fd6620a95337c8cb989029fac8efc34690d8e9f3c2dcdf8f284",
    "version": "0.25.1",
}
expected_model = {
    "model_id": "qwen3.6-35b-a3b",
    "repo_id": "Qwen/Qwen3.6-35B-A3B",
    "revision": "995ad96eacd98c81ed38be0c5b274b04031597b0",
    "receipt_sha256": "18c2a12881bf613c7110439b8e765ff89a4c060a1fb60aee62bb7250890ce1f9",
    "artifact_root_sha256": "8ac6d764b84034f4ed0df3f2388c9180afceab806f7e75f5d1e43a73bdd2736b",
    "trust_remote_code": False,
}
for name, actual, expected in (
    ("PAST", past, expected_past),
    ("vLLM", vllm, expected_vllm),
    ("model", model, expected_model),
):
    for key, value in expected.items():
        if actual.get(key) != value:
            raise SystemExit(f"{name} registered binding {key!r} drifted")
argv = server.get("argv")
if not isinstance(argv, list) or not argv or not all(isinstance(item, str) for item in argv):
    raise SystemExit("server argv is invalid")
required_args = {
    "vllm", "serve", "--tensor-parallel-size", "2", "--enforce-eager",
    "--enable-auto-tool-choice", "--tool-call-parser", "qwen3_xml",
}
if not required_args.issubset(set(argv)) or "--trust-remote-code" in argv:
    raise SystemExit("server argv violates the registered Qwen contract")
if server.get("api_base") != "http://past-qwen:8000/v1":
    raise SystemExit("server API base drifted")
if server.get("tool_call_parser") != "qwen3_xml" or server.get("enable_thinking") is not False:
    raise SystemExit("server parser/thinking contract drifted")

path_pattern = re.compile(r"/home/kevin/cotcodec-runs/[A-Za-z0-9._/-]{1,511}")
digest_pattern = re.compile(r"[0-9a-f]{64}")
image_pattern = re.compile(r"sha256:[0-9a-f]{64}")
values = [
    past.get("image_id"), past.get("image_repo_digest"), past.get("image_archive_path"),
    past.get("image_archive_sha256"), past.get("sbom_path"), past.get("sbom_sha256"),
    past.get("source_receipt_sha256"), past.get("runtime_receipt_sha256"),
    vllm.get("image_id"), vllm.get("image_repo_digest"), vllm.get("image_archive_path"),
    vllm.get("image_archive_sha256"), vllm.get("receipt_path"),
    vllm.get("receipt_sha256"), vllm.get("import_doctor_path"),
    vllm.get("import_doctor_sha256"), model.get("root"), model.get("receipt_path"),
    model.get("receipt_sha256"), model.get("artifact_root_sha256"),
    model.get("revision"), model.get("model_id"), server.get("api_base"),
    tools.get("transport_doctor_path"), tools.get("transport_doctor_sha256"),
    tools.get("batch_script_path"), tools.get("batch_script_sha256"),
]
if not all(isinstance(value, str) and "\n" not in value for value in values):
    raise SystemExit("transport manifest contains a non-string or multiline binding")
if not image_pattern.fullmatch(values[0]) or not image_pattern.fullmatch(values[8]):
    raise SystemExit("transport image ID is invalid")
for index in (2, 4, 10, 12, 14, 16, 17, 23, 25):
    if not path_pattern.fullmatch(values[index]):
        raise SystemExit(f"transport path binding {index} is invalid")
for index in (3, 5, 6, 7, 11, 13, 15, 18, 19, 24, 26):
    if not digest_pattern.fullmatch(values[index]):
        raise SystemExit(f"transport digest binding {index} is invalid")
if not re.fullmatch(r"[0-9a-f]{40}", values[20]):
    raise SystemExit("model revision is invalid")
if values[21] != "qwen3.6-35b-a3b":
    raise SystemExit("model id drifted")
argv_output.write_text(json.dumps(argv, separators=(",", ":")) + "\n", encoding="utf-8")
for value in values:
    print(value)
PY
)
if [[ ${#fields[@]} -ne 27 ]]; then
  echo "transport manifest did not emit the exact binding roster" >&2
  exit 2
fi

past_image_id=${fields[0]}
past_repo_digest=${fields[1]}
past_image_archive=${fields[2]}
past_image_archive_sha256=${fields[3]}
past_sbom=${fields[4]}
past_sbom_sha256=${fields[5]}
past_source_receipt_sha256=${fields[6]}
past_runtime_receipt_sha256=${fields[7]}
vllm_image_id=${fields[8]}
vllm_repo_digest=${fields[9]}
vllm_image_archive=${fields[10]}
vllm_image_archive_sha256=${fields[11]}
vllm_acquisition_receipt=${fields[12]}
vllm_acquisition_receipt_sha256=${fields[13]}
vllm_import_doctor=${fields[14]}
vllm_import_doctor_sha256=${fields[15]}
model_root=${fields[16]}
model_receipt=${fields[17]}
model_receipt_sha256=${fields[18]}
model_artifact_root=${fields[19]}
model_revision=${fields[20]}
model_id=${fields[21]}
api_base=${fields[22]}
transport_doctor=${fields[23]}
transport_doctor_sha256=${fields[24]}
registered_batch=${fields[25]}
registered_batch_sha256=${fields[26]}

if [[ ! -f ${registered_batch} \
  || -L ${registered_batch} \
  || $(sha256sum "${registered_batch}" | cut -d' ' -f1) != ${registered_batch_sha256} \
  || $(sha256sum "$0" | cut -d' ' -f1) != ${registered_batch_sha256} ]]; then
  echo "active batch script does not match the compiled transport manifest" >&2
  exit 2
fi

verify_regular_digest() {
  local path=$1
  local digest=$2
  if [[ ! -f ${path} || -L ${path} \
    || $(sha256sum "${path}" | cut -d' ' -f1) != ${digest} ]]; then
    echo "transport evidence file mismatch: ${path}" >&2
    exit 2
  fi
}
verify_regular_digest "${past_sbom}" "${past_sbom_sha256}"
verify_regular_digest "${past_image_archive}" "${past_image_archive_sha256}"
verify_regular_digest "${vllm_image_archive}" "${vllm_image_archive_sha256}"
verify_regular_digest "${vllm_acquisition_receipt}" "${vllm_acquisition_receipt_sha256}"
verify_regular_digest "${vllm_import_doctor}" "${vllm_import_doctor_sha256}"
verify_regular_digest "${model_receipt}" "${model_receipt_sha256}"
verify_regular_digest "${transport_doctor}" "${transport_doctor_sha256}"
if [[ ! -d ${model_root} || -L ${model_root} ]]; then
  echo "model root must be a regular non-symlink directory" >&2
  exit 2
fi

verify_docker_archive() {
  local archive=$1
  local image_id=$2
  local output=$3
  python3 - "${archive}" "${image_id}" "${output}" <<'PY'
import hashlib
import json
import pathlib
import sys
import tarfile

archive = pathlib.Path(sys.argv[1])
expected_id = sys.argv[2]
output = pathlib.Path(sys.argv[3])
seen: set[str] = set()
regular: dict[str, tarfile.TarInfo] = {}
with tarfile.open(archive, "r") as bundle:
    for member in bundle:
        path = pathlib.PurePosixPath(member.name)
        if (
            path.is_absolute()
            or any(part in {"", ".", ".."} for part in path.parts)
            or member.name in seen
        ):
            raise SystemExit(f"unsafe Docker archive member: {member.name!r}")
        seen.add(member.name)
        if member.isfile():
            regular[member.name] = member
        elif not member.isdir():
            raise SystemExit(f"unsupported Docker archive member: {member.name!r}")
    if "manifest.json" not in regular:
        raise SystemExit("Docker archive manifest.json is missing")
    manifest_stream = bundle.extractfile(regular["manifest.json"])
    if manifest_stream is None:
        raise SystemExit("cannot read Docker archive manifest")
    manifest = json.load(manifest_stream)
    if not isinstance(manifest, list) or len(manifest) != 1:
        raise SystemExit("Docker archive must contain exactly one image manifest")
    entry = manifest[0]
    config_name = entry.get("Config")
    layers = entry.get("Layers")
    if not isinstance(config_name, str) or config_name not in regular:
        raise SystemExit("Docker archive config binding is invalid")
    if not isinstance(layers, list) or not layers or any(layer not in regular for layer in layers):
        raise SystemExit("Docker archive layer roster is invalid")
    config_stream = bundle.extractfile(regular[config_name])
    if config_stream is None:
        raise SystemExit("cannot read Docker archive config")
    config_bytes = config_stream.read()
    observed_id = "sha256:" + hashlib.sha256(config_bytes).hexdigest()
    if observed_id != expected_id:
        raise SystemExit("Docker archive config digest does not match the image ID")
receipt = {
    "status": "DOCKER_SAVE_ARCHIVE_VERIFIED",
    "image_id": observed_id,
    "config": config_name,
    "layer_count": len(layers),
    "repo_tags": entry.get("RepoTags") or [],
}
output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
}
verify_docker_archive "${past_image_archive}" "${past_image_id}" \
  "${output_root}/past-image-archive-verification.json"
verify_docker_archive "${vllm_image_archive}" "${vllm_image_id}" \
  "${output_root}/vllm-image-archive-verification.json"
docker load --input "${past_image_archive}" >"${output_root}/past-image-load.txt"
docker load --input "${vllm_image_archive}" >"${output_root}/vllm-image-load.txt"

docker image inspect "${past_image_id}" >"${output_root}/past-image-inspect.json"
docker image inspect "${vllm_image_id}" >"${output_root}/vllm-image-inspect.json"
python3 - "${output_root}/past-image-inspect.json" "${past_image_id}" \
  "${past_source_receipt_sha256}" \
  "${past_runtime_receipt_sha256}" <<'PY'
import json
import sys
image = json.load(open(sys.argv[1], encoding="utf-8"))[0]
if image.get("Id") != sys.argv[2]:
    raise SystemExit("PAST live image identity drifted")
labels = image.get("Config", {}).get("Labels") or {}
expected = {
    "org.opencontainers.image.cotcodec-past-source-receipt-sha256": sys.argv[3],
    "org.opencontainers.image.cotcodec-past-runtime-contract-sha256": sys.argv[4],
    "org.opencontainers.image.cotcodec-checkpoint-runtime": "episode-boundary-v1",
    "org.opencontainers.image.cotcodec-publication-ready": "false",
}
for key, value in expected.items():
    if labels.get(key) != value:
        raise SystemExit(f"PAST live image label {key!r} drifted")
PY
python3 - "${output_root}/vllm-image-inspect.json" "${vllm_image_id}" <<'PY'
import json
import sys
image = json.load(open(sys.argv[1], encoding="utf-8"))[0]
if image.get("Id") != sys.argv[2]:
    raise SystemExit("vLLM live image identity drifted")
if image.get("Architecture") != "amd64" or image.get("Os") != "linux":
    raise SystemExit("vLLM live image platform drifted")
PY

cpu_list=$(awk '/Cpus_allowed_list/ {print $2}' /proc/self/status)
if [[ -z ${cpu_list} ]]; then
  echo "could not determine Slurm CPU affinity" >&2
  exit 2
fi
private_model_root="${output_root}/model-snapshot"
client_output="${output_root}/client-output"
mkdir -m 0700 "${private_model_root}" "${client_output}"

model_snapshot_code=$(cat <<'PY'
import hashlib
import json
import os
import pathlib

source_root = pathlib.Path("/source-model")
target_root = pathlib.Path("/snapshot")
receipt = json.loads(pathlib.Path("/model-receipt.json").read_text(encoding="utf-8"))
expected_files = receipt.get("files")
if not isinstance(expected_files, list) or not expected_files:
    raise SystemExit("model receipt file roster is missing")
expected_paths = {item["path"] for item in expected_files}
observed_paths = set()
for path in sorted(source_root.rglob("*")):
    relative = path.relative_to(source_root)
    if relative.parts[:2] == (".cache", "huggingface"):
        continue
    if path.is_symlink():
        raise SystemExit(f"source model contains a symlink: {relative}")
    if path.is_file():
        observed_paths.add(relative.as_posix())
if observed_paths != expected_paths:
    raise SystemExit("source model file roster drifted before snapshot")

actual = []
for item in expected_files:
    relative = pathlib.PurePosixPath(item["path"])
    if (
        relative.is_absolute()
        or any(part in {"", ".", ".."} for part in relative.parts)
        or not isinstance(item.get("bytes"), int)
        or not isinstance(item.get("sha256"), str)
    ):
        raise SystemExit(f"unsafe model receipt entry: {item!r}")
    source = source_root.joinpath(*relative.parts)
    target = target_root.joinpath(*relative.parts)
    target.parent.mkdir(mode=0o500, parents=True, exist_ok=True)
    source_fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW)
    target_fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o400)
    digest = hashlib.sha256()
    copied = 0
    try:
        while chunk := os.read(source_fd, 1024 * 1024):
            digest.update(chunk)
            copied += len(chunk)
            view = memoryview(chunk)
            while view:
                written = os.write(target_fd, view)
                view = view[written:]
        os.fsync(target_fd)
    finally:
        os.close(source_fd)
        os.close(target_fd)
    if copied != item["bytes"] or digest.hexdigest() != item["sha256"]:
        raise SystemExit(f"model bytes drifted while snapshotting: {relative}")
    actual.append({"path": relative.as_posix(), "bytes": copied, "sha256": digest.hexdigest()})
for directory in sorted((path for path in target_root.rglob("*") if path.is_dir()), reverse=True):
    directory.chmod(0o500)
target_root.chmod(0o500)
artifact_root = hashlib.sha256(
    json.dumps(actual, separators=(",", ":"), sort_keys=True).encode()
).hexdigest()
if actual != expected_files or artifact_root != receipt.get("artifact_root_sha256"):
    raise SystemExit("private model snapshot does not match the receipt")
print(json.dumps({
    "status": "PRIVATE_MODEL_SNAPSHOT_VERIFIED",
    "file_count": len(actual),
    "total_bytes": sum(item["bytes"] for item in actual),
    "artifact_root_sha256": artifact_root,
}, sort_keys=True))
PY
)
docker run --rm --pull=never \
  --network none \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,nodev,size=2g \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  --pids-limit 1024 \
  --cpuset-cpus "${cpu_list}" \
  --ulimit core=0 \
  --user "${runtime_identity}" \
  --volume "${model_root}:/source-model:ro" \
  --volume "${private_model_root}:/snapshot:rw" \
  --volume "${model_receipt}:/model-receipt.json:ro" \
  --entrypoint python3 \
  "${vllm_image_id}" -c "${model_snapshot_code}" \
  >"${output_root}/private-model-snapshot-receipt.json"

model_verify_code=$(cat <<'PY'
import hashlib
import json
import os
import pathlib
receipt_path = pathlib.Path("/model-receipt.json")
root = pathlib.Path("/models/qwen3.6-35b-a3b")
receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
expected = {
    "schema_version": 1,
    "model_id": "qwen3.6-35b-a3b",
    "backend": "huggingface",
    "repo_id": "Qwen/Qwen3.6-35B-A3B",
    "revision": "995ad96eacd98c81ed38be0c5b274b04031597b0",
    "mode": "full",
    "publication_eligible": True,
    "trust_remote_code": False,
    "artifact_root_sha256": "8ac6d764b84034f4ed0df3f2388c9180afceab806f7e75f5d1e43a73bdd2736b",
}
for key, value in expected.items():
    if receipt.get(key) != value:
        raise SystemExit(f"model receipt field {key!r} drifted")
actual = []
for path in sorted(root.rglob("*")):
    relative = path.relative_to(root)
    if relative.parts[:2] == (".cache", "huggingface"):
        continue
    if path.is_symlink():
        raise SystemExit(f"model artifact contains a symlink: {relative}")
    if not path.is_file():
        continue
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    actual.append({"path": relative.as_posix(), "bytes": path.stat().st_size, "sha256": digest.hexdigest()})
if actual != receipt.get("files"):
    raise SystemExit("model artifact file roster or bytes drifted")
artifact_root = hashlib.sha256(json.dumps(actual, separators=(",", ":"), sort_keys=True).encode()).hexdigest()
if artifact_root != receipt["artifact_root_sha256"]:
    raise SystemExit("model artifact root drifted")
print(json.dumps({"status": "FULL_MODEL_RECEIPT_VERIFIED", "file_count": len(actual), "total_bytes": sum(item["bytes"] for item in actual), "artifact_root_sha256": artifact_root}, sort_keys=True))
PY
)
docker run --rm --pull=never \
  --network none \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,nodev,size=2g \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  --pids-limit 1024 \
  --ulimit core=0 \
  --user "${runtime_identity}" \
  --volume "${private_model_root}:/models/${model_id}:ro" \
  --volume "${model_receipt}:/model-receipt.json:ro" \
  --entrypoint python3 \
  "${vllm_image_id}" -c "${model_verify_code}" \
  >"${output_root}/full-model-verification.json"

docker_gpu_request="\"device=${allocated_gpu_uuid_csv}\""
docker run --rm --pull=never \
  --gpus "${docker_gpu_request}" \
  --network none \
  --read-only \
  --tmpfs /tmp:rw,nosuid,nodev,size=2g \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  --pids-limit 2048 \
  --cpuset-cpus "${cpu_list}" \
  --ulimit core=0 \
  --env COTCODEC_EXPECTED_GPU_UUIDS="${allocated_gpu_uuid_csv}" \
  --entrypoint python3 \
  "${vllm_image_id}" \
  -c 'import json,os,subprocess,torch; uuids=subprocess.check_output(["nvidia-smi","--query-gpu=uuid","--format=csv,noheader"],text=True).strip().splitlines(); assert torch.cuda.device_count() == 2 and uuids == os.environ["COTCODEC_EXPECTED_GPU_UUIDS"].split(","); print(json.dumps({"count": 2, "names": [torch.cuda.get_device_name(i) for i in range(2)], "uuids": uuids}, sort_keys=True))' \
  >"${output_root}/container-gpu-doctor.json"

network_name="past-transport-${SLURM_JOB_ID}"
server_name="past-qwen-${SLURM_JOB_ID}"
client_name="past-client-${SLURM_JOB_ID}"
network_created=false
server_created=false
client_created=false
termination_reason=running

cleanup() {
  local exit_code=$?
  trap - EXIT USR1 TERM
  if ${server_created}; then
    docker logs "${server_name}" >"${output_root}/server.log" 2>&1 || true
  fi
  if ${client_created}; then
    docker rm --force "${client_name}" >/dev/null 2>&1 || true
  fi
  if ${server_created}; then
    docker rm --force "${server_name}" >/dev/null 2>&1 || true
  fi
  if ${network_created}; then
    docker network rm "${network_name}" >/dev/null 2>&1 || true
  fi
  printf 'exit_code=%s\ntermination_reason=%s\n' \
    "${exit_code}" "${termination_reason}" >"${output_root}/termination.txt"
  exit "${exit_code}"
}
stop_for_signal() {
  termination_reason=signal_no_scientific_work_started
  exit 75
}
trap cleanup EXIT
trap stop_for_signal USR1 TERM

docker network create --internal "${network_name}" >"${output_root}/network-id.txt"
network_created=true
docker network inspect "${network_name}" >"${output_root}/network-inspect.json"
python3 - "${output_root}/network-inspect.json" "${network_name}" <<'PY'
import json
import sys
network = json.load(open(sys.argv[1], encoding="utf-8"))[0]
if network.get("Name") != sys.argv[2] or network.get("Internal") is not True:
    raise SystemExit("Docker network is not internal-only")
PY

mapfile -d '' -t server_argv < <(
  python3 - "${output_root}/server-argv.json" <<'PY'
import json
import sys
argv = json.load(open(sys.argv[1], encoding="utf-8"))
for item in argv:
    sys.stdout.buffer.write(item.encode() + b"\0")
PY
)
if [[ ${#server_argv[@]} -lt 4 || ${server_argv[0]} != vllm || ${server_argv[1]} != serve ]]; then
  echo "server argv does not begin with vllm serve" >&2
  exit 2
fi
server_command=("${server_argv[@]:1}")

docker create \
  --name "${server_name}" \
  --hostname past-qwen \
  --network "${network_name}" \
  --network-alias past-qwen \
  --entrypoint vllm \
  --gpus "${docker_gpu_request}" \
  --read-only \
  --tmpfs /tmp:rw,exec,nosuid,nodev,size=16g \
  --shm-size 16g \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  --pids-limit 8192 \
  --cpuset-cpus "${cpu_list}" \
  --memory 150g \
  --memory-swap 150g \
  --ulimit core=0 \
  --user "${runtime_identity}" \
  --workdir /tmp \
  --env USER=cotcodec \
  --env LOGNAME=cotcodec \
  --env HOME=/tmp/home \
  --env XDG_CACHE_HOME=/tmp/cache \
  --env TORCHINDUCTOR_CACHE_DIR=/tmp/torchinductor \
  --env HF_HUB_OFFLINE=1 \
  --env TRANSFORMERS_OFFLINE=1 \
  --env CUBLAS_WORKSPACE_CONFIG=:4096:8 \
  --env PYTHONHASHSEED=42 \
  --env COTCODEC_EXPECTED_GPU_UUIDS="${allocated_gpu_uuid_csv}" \
  --volume "${private_model_root}:/models/${model_id}:ro" \
  --volume "${model_receipt}:/model-receipt.json:ro" \
  "${vllm_image_id}" "${server_command[@]}" \
  >"${output_root}/server-container-id.txt"
server_created=true
docker inspect "${server_name}" >"${output_root}/server-created-inspect.json"
python3 - "${output_root}/server-created-inspect.json" "${network_name}" \
  "${private_model_root}" "${model_receipt}" "${allocated_gpu_uuid_csv}" \
  "${runtime_identity}" <<'PY'
import json
import pathlib
import sys

container = json.load(open(sys.argv[1], encoding="utf-8"))[0]
host = container.get("HostConfig") or {}
configured_user = str((container.get("Config") or {}).get("User") or "")
if configured_user != sys.argv[6] or configured_user.split(":", 1)[0] == "0":
    raise SystemExit("model server configured user is not the registered non-root identity")
if host.get("NetworkMode") != sys.argv[2] or host.get("PortBindings"):
    raise SystemExit("model server network or host-port contract drifted")
if host.get("ReadonlyRootfs") is not True or host.get("Privileged") is not False:
    raise SystemExit("model server rootfs/privilege contract drifted")
if (host.get("Tmpfs") or {}).get("/tmp") != "rw,exec,nosuid,nodev,size=16g":
    raise SystemExit("model server executable scratch tmpfs contract drifted")
if "ALL" not in (host.get("CapDrop") or []):
    raise SystemExit("model server capabilities were not dropped")
if not any(
    item.startswith("no-new-privileges") for item in (host.get("SecurityOpt") or [])
):
    raise SystemExit("model server no-new-privileges contract drifted")
environment = set((container.get("Config") or {}).get("Env") or [])
required_environment = {
    "USER=cotcodec",
    "LOGNAME=cotcodec",
    "HOME=/tmp/home",
    "XDG_CACHE_HOME=/tmp/cache",
    "TORCHINDUCTOR_CACHE_DIR=/tmp/torchinductor",
    "HF_HUB_OFFLINE=1",
    "TRANSFORMERS_OFFLINE=1",
}
if not required_environment.issubset(environment):
    raise SystemExit("model server identity/cache environment drifted")
mounts = {item["Destination"]: item for item in container.get("Mounts") or []}
expected_mounts = {
    "/models/qwen3.6-35b-a3b": pathlib.Path(sys.argv[3]).resolve(),
    "/model-receipt.json": pathlib.Path(sys.argv[4]).resolve(),
}
for destination, source in expected_mounts.items():
    mount = mounts.get(destination)
    if (
        mount is None
        or pathlib.Path(mount.get("Source", "")).resolve() != source
        or mount.get("RW") is not False
    ):
        raise SystemExit(f"model server mount {destination!r} drifted")
requested = (host.get("DeviceRequests") or [{}])[0].get("DeviceIDs") or []
if requested != sys.argv[5].split(","):
    raise SystemExit("model server Docker GPU UUID request drifted")
PY
docker start "${server_name}" >/dev/null

ready=false
for _ in $(seq 1 180); do
  if docker exec "${server_name}" python3 -c \
    'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=2).read()' \
    >/dev/null 2>&1; then
    ready=true
    break
  fi
  if [[ $(docker inspect --format '{{.State.Running}}' "${server_name}") != true ]]; then
    break
  fi
  sleep 2
done
if ! ${ready}; then
  termination_reason=model_server_not_ready
  echo "vLLM server failed to become healthy" >&2
  exit 2
fi
docker inspect "${server_name}" >"${output_root}/server-ready-inspect.json"

docker exec "${server_name}" python3 -c "${model_verify_code}" \
  >"${output_root}/running-server-model-verification.json"
docker exec "${server_name}" python3 -c \
  'import json,os,subprocess,torch; uuids=subprocess.check_output(["nvidia-smi","--query-gpu=uuid","--format=csv,noheader"],text=True).strip().splitlines(); assert torch.cuda.device_count() == 2 and uuids == os.environ["COTCODEC_EXPECTED_GPU_UUIDS"].split(","); print(json.dumps({"count": 2, "uuids": uuids},sort_keys=True))' \
  >"${output_root}/running-server-gpu-verification.json"

docker exec "${server_name}" python3 -c \
  'import json,socket; blocked=[]
for target in (("1.1.1.1",443),("8.8.8.8",53)):
    try:
        socket.create_connection(target,timeout=1).close()
    except OSError as exc:
        blocked.append({"target":f"{target[0]}:{target[1]}","error":type(exc).__name__})
    else:
        raise SystemExit(f"external egress unexpectedly reached {target}")
print(json.dumps({"external_egress_blocked":blocked},sort_keys=True))' \
  >"${output_root}/server-egress-doctor.json"

docker create \
  --name "${client_name}" \
  --network "${network_name}" \
  --read-only \
  --tmpfs /state:rw,noexec,nosuid,nodev,size=2g \
  --tmpfs /tmp:rw,noexec,nosuid,nodev,size=2g \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  --pids-limit 1024 \
  --cpuset-cpus "${cpu_list}" \
  --memory 8g \
  --memory-swap 8g \
  --ulimit core=0 \
  --user "$(id -u):$(id -g)" \
  --env HOME=/state/home \
  --env PYTHONDONTWRITEBYTECODE=1 \
  --env PYTHONUNBUFFERED=1 \
  --volume "${transport_doctor}:/doctor/model_transport_doctor.py:ro" \
  --volume "${client_output}:/outputs:rw" \
  --entrypoint /opt/past-bench-venv/bin/python \
  "${past_image_id}" \
  /doctor/model_transport_doctor.py \
  --base-url "${api_base}" \
  --api-key cotcodec-internal-transport \
  --model "${model_id}" \
  --output /outputs/model-transport-doctor.json \
  >"${output_root}/client-container-id.txt"
client_created=true
docker inspect "${client_name}" >"${output_root}/client-created-inspect.json"
docker start --attach "${client_name}" >"${output_root}/client.log" 2>&1
if [[ $(docker inspect --format '{{.State.ExitCode}}' "${client_name}") != 0 ]]; then
  termination_reason=client_transport_doctor_failed
  echo "PAST client transport doctor failed" >&2
  exit 2
fi

docker logs "${server_name}" >"${output_root}/server.log" 2>&1
python3 - "${output_root}" "${SLURM_JOB_ID}" "${manifest_sha256}" \
  "${past_image_id}" "${vllm_image_id}" "${model_artifact_root}" \
  "${model_revision}" "${SLURM_JOB_GPUS}" "${allocated_gpu_uuid_csv}" <<'PY'
import hashlib
import json
import os
import pathlib
import sys
root = pathlib.Path(sys.argv[1])
(
    job_id, manifest_sha, past_image, vllm_image, model_root, model_revision,
    slurm_job_gpus, allocated_gpu_uuid_csv,
) = sys.argv[2:]
required = (
    "client-created-inspect.json", "client.log", "container-gpu-doctor.json",
    "client-output/model-transport-doctor.json", "full-model-verification.json",
    "network-inspect.json", "private-model-snapshot-receipt.json",
    "past-image-inspect.json", "past-image-load.txt", "server-created-inspect.json",
    "server-egress-doctor.json",
    "running-server-gpu-verification.json", "running-server-model-verification.json",
    "server-ready-inspect.json", "server.log", "transport-manifest.json",
    "vllm-image-archive-verification.json", "vllm-image-inspect.json",
    "vllm-image-load.txt",
    "past-image-archive-verification.json",
)
artifacts = {}
for name in required:
    path = root / name
    if not path.is_file() or path.is_symlink():
        raise SystemExit(f"required transport artifact is missing: {name}")
    artifacts[name] = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "size": path.stat().st_size}
doctor = json.loads(
    (root / "client-output/model-transport-doctor.json").read_text(encoding="utf-8")
)
if doctor.get("status") != "PAST_QWEN_INTERNAL_MODEL_TRANSPORT_DOCTOR_PASS":
    raise SystemExit("model transport doctor status is not PASS")
if not all(doctor.get(key) is True for key in ("semantic_aa_equal", "native_nonstream_tool_call", "native_stream_tool_call")):
    raise SystemExit("model transport doctor gates are incomplete")
receipt = {
    "schema_version": 1,
    "status": "PAST_QWEN_INTERNAL_MODEL_TRANSPORT_DISCOVERY_PASS",
    "scientific_result": False,
    "publication_ready": False,
    "slurm_job_id": job_id,
    "manifest_sha256": manifest_sha,
    "past_image_id": past_image,
    "vllm_image_id": vllm_image,
    "model_artifact_root_sha256": model_root,
    "model_revision": model_revision,
    "cuda_visible_devices": os.environ["CUDA_VISIBLE_DEVICES"],
    "slurm_job_gpus": slurm_job_gpus,
    "allocated_gpu_uuids": allocated_gpu_uuid_csv.split(","),
    "artifacts": artifacts,
    "remaining_gates": [
        "scanner-produced vLLM image SBOM",
        "one real SM01 episode with exact task receipt",
        "forced stop after episode three and fresh-job resume",
        "uninterrupted-versus-resumed suffix equivalence",
        "bounded persistence-on versus persistence-off SM01 pilot",
    ],
}
payload = json.dumps(receipt, indent=2, sort_keys=True).encode() + b"\n"
temporary = root / f".transport-receipt.{os.getpid()}.tmp"
with temporary.open("xb") as stream:
    stream.write(payload)
    stream.flush()
    os.fsync(stream.fileno())
os.link(temporary, root / "transport-receipt.json")
temporary.unlink()
PY

termination_reason=completed
echo "PAST_QWEN_INTERNAL_MODEL_TRANSPORT_DISCOVERY_PASS root=${output_root}"
