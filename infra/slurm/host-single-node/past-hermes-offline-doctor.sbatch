#!/usr/bin/env bash
#SBATCH --job-name=past-hermes-offline
#SBATCH --partition=research
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:05:00
#SBATCH --output=/home/kevin/cotcodec-runs/past-bench/hermes-offline-%j.out
#SBATCH --error=/home/kevin/cotcodec-runs/past-bench/hermes-offline-%j.err

set -Eeuo pipefail
umask 077

if [[ $# -ne 5 ]]; then
  echo "usage: $0 TOOLS_ROOT TOOLS_SHA OUTPUT_ROOT BATCH_SHA IMAGE_ARCHIVE_SHA" >&2
  exit 2
fi
tools_root=$1
expected_tools_sha256=$2
output_root=$3
expected_batch_sha256=$4
expected_archive_sha256=$5
image_id='sha256:ebcf7eea7f1977f03e5e007edf265fcd120edadcd6d48e81f63df70715783150'
image_archive='/home/kevin/cotcodec-runs/past-bench/build-20260814-checkpoint-d4945b33-v1/image.tar'

: "${SLURM_JOB_ID:?offline Hermes doctor must execute inside Slurm}"
if [[ ! ${tools_root} =~ ^/home/kevin/cotcodec-runs/past-bench/inputs/past-hermes-offline-tools-[0-9a-f]{64}$ \
  || ! ${output_root} =~ ^/home/kevin/cotcodec-runs/past-bench/hermes-offline-[a-z0-9._-]{1,96}$ \
  || ! ${expected_tools_sha256} =~ ^[0-9a-f]{64}$ \
  || ! ${expected_batch_sha256} =~ ^[0-9a-f]{64}$ \
  || ! ${expected_archive_sha256} =~ ^[0-9a-f]{64}$ \
  || -e ${output_root} || -L ${output_root} ]]; then
  echo "unsafe offline Hermes doctor argument" >&2
  exit 2
fi
mkdir -m 0700 "${output_root}"
mkdir -m 0700 "${output_root}/state" "${output_root}/evidence"

registered_batch="${tools_root}/infra/slurm/host-single-node/past-hermes-offline-doctor.sbatch"
if [[ ! -f ${registered_batch} || -L ${registered_batch} \
  || $(sha256sum "$0" | cut -d' ' -f1) != ${expected_batch_sha256} \
  || $(sha256sum "${registered_batch}" | cut -d' ' -f1) != ${expected_batch_sha256} \
  || $(sha256sum "${image_archive}" | cut -d' ' -f1) != ${expected_archive_sha256} ]]; then
  echo "offline Hermes doctor evidence drifted" >&2
  exit 2
fi

actual_tools_sha256=$(python3 - "${tools_root}" <<'PY'
import hashlib,json,pathlib,sys
root=pathlib.Path(sys.argv[1]); rows=[]
expected={
 "infra/research/past-bench/prepare_hermes_offline_bootstrap.py",
 "infra/research/past-bench/sm01-runtime.yaml",
 "infra/slurm/host-single-node/past-hermes-offline-doctor.sbatch",
}
for path in sorted(root.rglob("*")):
 if path.is_symlink() or (not path.is_file() and not path.is_dir()): raise SystemExit("unsafe tool entry")
 if path.is_file():
  relative=path.relative_to(root).as_posix()
  if relative not in expected: raise SystemExit("unregistered tool")
  payload=path.read_bytes(); rows.append({"path":relative,"sha256":hashlib.sha256(payload).hexdigest(),"size":len(payload)})
if {row["path"] for row in rows} != expected: raise SystemExit("incomplete tool bundle")
print(hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(",",":")).encode()).hexdigest())
PY
)
if [[ ${actual_tools_sha256} != ${expected_tools_sha256} ]]; then
  echo "offline Hermes doctor tool root drifted" >&2
  exit 2
fi

docker load --input "${image_archive}" >"${output_root}/evidence/image-load.txt"
if [[ $(docker image inspect --format '{{.Id}}' "${image_id}") != ${image_id} ]]; then
  echo "PAST image ID drifted" >&2
  exit 2
fi
docker image inspect "${image_id}" >"${output_root}/evidence/image-inspect.json"
runtime_identity="$(id -u):$(id -g)"
docker run --rm --pull=never --network none --read-only \
  --tmpfs /tmp:rw,exec,nosuid,nodev,size=2g --cap-drop ALL \
  --security-opt no-new-privileges --pids-limit 1024 --user "${runtime_identity}" \
  --env HOME=/state/home --env PYTHONPATH=/tools --workdir /opt/past-bench/source \
  --volume "${tools_root}:/tools:ro" --volume "${output_root}/state:/state:rw" \
  --volume "${output_root}/evidence:/evidence:rw" \
  --entrypoint /opt/past-bench-venv/bin/python "${image_id}" \
  /tools/infra/research/past-bench/prepare_hermes_offline_bootstrap.py \
  --config /tools/infra/research/past-bench/sm01-runtime.yaml \
  --cache-dir /state/runtime_cache --output /evidence/offline-bootstrap.json

python3 - "${output_root}/evidence/offline-bootstrap.json" <<'PY'
import json,sys
report=json.load(open(sys.argv[1],encoding="utf-8"))
assert report["status"] == "PAST_HERMES_PLUS_OFFLINE_BOOTSTRAP_PASS"
assert report["network_required"] is False
print("PAST_HERMES_OFFLINE_CPU_DOCTOR_PASS")
PY
