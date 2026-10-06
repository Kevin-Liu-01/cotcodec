#!/usr/bin/env bash
#SBATCH --job-name=past-runtime-build
#SBATCH --partition=research
#SBATCH --gres=gpu:h100:1
#SBATCH --cpus-per-task=16
#SBATCH --mem=64G
#SBATCH --time=01:00:00
#SBATCH --output=/home/kevin/cotcodec-runs/past-bench/slurm-%j.out
#SBATCH --error=/home/kevin/cotcodec-runs/past-bench/slurm-%j.err

set -Eeuo pipefail
umask 077

if [[ $# -ne 7 ]]; then
  echo "usage: $0 CONTEXT_TAR CONTEXT_SHA CONTEXT_RECEIPT SOURCE_RECEIPT RUNTIME_RECEIPT IMAGE_TAG BUILD_ROOT" >&2
  exit 2
fi

context_tar=$1
context_sha256=$2
context_receipt_sha256=$3
source_receipt_sha256=$4
runtime_receipt_sha256=$5
image_tag=$6
build_root=$7

: "${SLURM_JOB_ID:?PAST build must execute inside Slurm}"
: "${CUDA_VISIBLE_DEVICES:?Slurm did not map the allocated H100}"

if [[ ! ${context_sha256} =~ ^[0-9a-f]{64}$ \
  || ! ${context_receipt_sha256} =~ ^[0-9a-f]{64}$ \
  || ! ${source_receipt_sha256} =~ ^[0-9a-f]{64}$ \
  || ! ${runtime_receipt_sha256} =~ ^[0-9a-f]{64}$ \
  || ! ${image_tag} =~ ^[a-z0-9][a-z0-9._:/-]{0,127}$ \
  || ! ${build_root} =~ ^/home/kevin/cotcodec-runs/past-bench/[a-z0-9._-]{1,96}$ \
  || ! ${context_tar} =~ ^/home/kevin/cotcodec-runs/past-bench/inputs/[a-z0-9._-]{1,128}\.tar\.gz$ ]]; then
  echo "unsafe PAST build argument" >&2
  exit 2
fi
if [[ ${CUDA_VISIBLE_DEVICES} == *,* \
  || ${SLURM_GPUS_ON_NODE:-} != 1 \
  || ! -f ${context_tar} \
  || -L ${context_tar} \
  || -e ${build_root} \
  || -L ${build_root} ]]; then
  echo "invalid PAST allocation, context archive, or output root" >&2
  exit 2
fi
if [[ $(nvidia-smi -i "${CUDA_VISIBLE_DEVICES}" --query-gpu=name --format=csv,noheader) != *H100* ]]; then
  echo "PAST build requires a Slurm-owned H100" >&2
  exit 2
fi

mkdir -m 0700 "${build_root}"
snapshot="${build_root}/context.tar.gz"
cp --reflink=never --no-preserve=mode,ownership,timestamps "${context_tar}" "${snapshot}"
chmod 0400 "${snapshot}"
if [[ $(sha256sum "${snapshot}" | cut -d' ' -f1) != ${context_sha256} ]]; then
  echo "PAST context archive digest mismatch" >&2
  exit 2
fi

context="${build_root}/context"
mkdir -m 0700 "${context}"
python3 - "${snapshot}" "${context}" <<'PY'
import os
import pathlib
import stat
import sys
import tarfile

archive = pathlib.Path(sys.argv[1])
output = pathlib.Path(sys.argv[2])
seen: set[str] = set()
root_seen = False
with tarfile.open(archive, "r:gz") as bundle:
    for member in bundle:
        path = pathlib.PurePosixPath(member.name)
        if path.parts == ("context",):
            if root_seen or not member.isdir():
                raise SystemExit("context archive root must be one directory")
            root_seen = True
            continue
        if (
            path.is_absolute()
            or len(path.parts) < 2
            or path.parts[0] != "context"
            or any(part in {"", ".", ".."} for part in path.parts)
        ):
            raise SystemExit(f"unsafe context member: {member.name!r}")
        relative = pathlib.PurePosixPath(*path.parts[1:])
        name = relative.as_posix()
        if name in seen:
            raise SystemExit(f"duplicate context member: {name}")
        seen.add(name)
        destination = output.joinpath(*relative.parts)
        if member.isdir():
            destination.mkdir(mode=0o755, parents=True, exist_ok=True)
            continue
        if not member.isfile():
            raise SystemExit(f"unsupported context member: {name}")
        destination.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
        source = bundle.extractfile(member)
        if source is None:
            raise SystemExit(f"cannot read context member: {name}")
        descriptor = os.open(
            destination,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o755 if member.mode & stat.S_IXUSR else 0o644,
        )
        with os.fdopen(descriptor, "wb") as target:
            while chunk := source.read(1024 * 1024):
                target.write(chunk)
            target.flush()
            os.fsync(target.fileno())
if not root_seen:
    raise SystemExit("context archive root directory is missing")
PY

read -r observed_context observed_source observed_runtime < <(
  python3 - "${context}/.cotcodec/source-context-receipt.json" \
    "${build_root}/context-verification.json" <<'PY'
import hashlib
import json
import sys
receipt = json.load(open(sys.argv[1], encoding="utf-8"))
unsigned = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
canonical = json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
if receipt.get("receipt_sha256") != hashlib.sha256(canonical.encode()).hexdigest():
    raise SystemExit("context receipt self-digest is invalid")
with open(sys.argv[2], "x", encoding="utf-8") as stream:
    json.dump(
        {
            "status": "HOST_STDLIB_RECEIPT_PRECHECK_ONLY",
            "full_context_verification": "runs in the exact Docker build environment",
            "receipt": receipt,
        },
        stream,
        indent=2,
        sort_keys=True,
    )
    stream.write("\n")
print(receipt["receipt_sha256"], receipt["source_receipt_sha256"], receipt["runtime_receipt_sha256"])
PY
)
if [[ ${observed_context} != ${context_receipt_sha256} \
  || ${observed_source} != ${source_receipt_sha256} \
  || ${observed_runtime} != ${runtime_receipt_sha256} ]]; then
  echo "PAST compiled-context receipt mismatch" >&2
  exit 2
fi

docker buildx build \
  --load \
  --platform linux/amd64 \
  --network host \
  --build-arg "PAST_RUNTIME_CONTRACT_SHA256=${runtime_receipt_sha256}" \
  --build-arg "PAST_SOURCE_RECEIPT_SHA256=${source_receipt_sha256}" \
  --file "${context}/.cotcodec/Dockerfile" \
  --tag "${image_tag}" \
  "${context}" >"${build_root}/docker-build.log" 2>&1

docker image inspect "${image_tag}" >"${build_root}/image-inspect.json"
image_id=$(docker image inspect --format '{{.Id}}' "${image_tag}")
read -r label_source label_runtime label_publication < <(
  docker image inspect --format '{{index .Config.Labels "org.opencontainers.image.cotcodec-past-source-receipt-sha256"}} {{index .Config.Labels "org.opencontainers.image.cotcodec-past-runtime-contract-sha256"}} {{index .Config.Labels "org.opencontainers.image.cotcodec-publication-ready"}}' "${image_tag}"
)
if [[ ${label_source} != ${source_receipt_sha256} \
  || ${label_runtime} != ${runtime_receipt_sha256} \
  || ${label_publication} != false ]]; then
  echo "built PAST image labels drifted" >&2
  exit 2
fi

docker run --rm --pull=never \
  --network none \
  --read-only \
  --tmpfs /state:rw,noexec,nosuid,nodev,size=1g \
  --tmpfs /tmp:rw,noexec,nosuid,nodev,size=1g \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  --pids-limit 512 \
  --user 65534:65534 \
  --entrypoint /opt/past-bench-venv/bin/python \
  "${image_id}" \
  -c 'import importlib.metadata as m; assert m.version("past-bench") == "1.0.0"; assert m.version("hermes-plus") == "0.4.0"; print("PAST_CONTAINED_IMPORT_DOCTOR_PASS")' \
  >"${build_root}/contained-doctor.txt"

docker run --rm --pull=never \
  --network none \
  --read-only \
  --tmpfs /state:rw,noexec,nosuid,nodev,size=1g \
  --tmpfs /tmp:rw,noexec,nosuid,nodev,size=1g \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  --pids-limit 512 \
  --user 65534:65534 \
  --entrypoint /opt/past-bench-venv/bin/python \
  "${image_id}" \
  /opt/past-bench/source/.cotcodec/checkpoint_runtime_selftest.py \
  >"${build_root}/checkpoint-selftest.txt"

docker run --rm --pull=never \
  --network none \
  --read-only \
  --tmpfs /state:rw,noexec,nosuid,nodev,size=1g \
  --tmpfs /tmp:rw,noexec,nosuid,nodev,size=1g \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  --pids-limit 512 \
  --user 65534:65534 \
  "${image_id}" \
  evolve --help >"${build_root}/checkpoint-cli-help.txt"

docker run --rm --pull=never \
  --network none \
  --read-only \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  --pids-limit 64 \
  --user 65534:65534 \
  --entrypoint /bin/sh \
  "${image_id}" \
  -c 'cat /opt/past-bench-lock/checkpoint-overlay.txt' \
  >"${build_root}/checkpoint-overlay.txt"

docker run --rm --pull=never \
  --network none \
  --read-only \
  --tmpfs /state:rw,noexec,nosuid,nodev,size=1g \
  --tmpfs /tmp:rw,noexec,nosuid,nodev,size=1g \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  --pids-limit 512 \
  --user 65534:65534 \
  --entrypoint /opt/past-bench-venv/bin/python \
  "${image_id}" \
  -c 'import sys; sys.stdout.buffer.write(open("/opt/past-bench-lock/upstream-tests.xml", "rb").read())' \
  >"${build_root}/upstream-tests.xml"

docker save "${image_id}" --output "${build_root}/image.tar"
sha256sum "${build_root}/image.tar" >"${build_root}/image.tar.sha256"
nvidia-smi -i "${CUDA_VISIBLE_DEVICES}" \
  --query-gpu=uuid,name,driver_version \
  --format=csv,noheader >"${build_root}/gpu.csv"
sha256sum "$0" >"${build_root}/batch-script.sha256"

python3 - "${build_root}" "${image_id}" "${image_tag}" "${SLURM_JOB_ID}" <<'PY'
import hashlib
import json
import os
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
image_id, image_tag, job_id = sys.argv[2:]
files = {}
for name in (
    "batch-script.sha256",
    "checkpoint-cli-help.txt",
    "checkpoint-overlay.txt",
    "checkpoint-selftest.txt",
    "contained-doctor.txt",
    "context-verification.json",
    "docker-build.log",
    "gpu.csv",
    "image-inspect.json",
    "image.tar",
    "image.tar.sha256",
    "upstream-tests.xml",
):
    path = root / name
    files[name] = {
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "size": path.stat().st_size,
    }
receipt = {
    "schema_version": 1,
    "status": "PAST_DISCOVERY_IMAGE_BUILT_NOT_SCIENTIFIC_RESULT",
    "scientific_result": False,
    "publication_ready": False,
    "slurm_job_id": job_id,
    "cuda_visible_devices": os.environ["CUDA_VISIBLE_DEVICES"],
    "image_id": image_id,
    "image_tag": image_tag,
    "artifacts": files,
    "remaining_gates": [
        "scanner-produced image-bound SBOM",
        "real SM01 stop/resume equivalence across fresh Slurm jobs",
        "same-job no-external-egress model transport and model receipt",
        "bounded SM01 persistence-on/off run",
    ],
}
payload = json.dumps(receipt, indent=2, sort_keys=True).encode() + b"\n"
temporary = root / f".build-receipt.{os.getpid()}.tmp"
with temporary.open("xb") as stream:
    stream.write(payload)
    stream.flush()
    os.fsync(stream.fileno())
os.link(temporary, root / "build-receipt.json")
temporary.unlink()
PY

echo "PAST_DISCOVERY_IMAGE_BUILD_PASS image=${image_id} root=${build_root}"
