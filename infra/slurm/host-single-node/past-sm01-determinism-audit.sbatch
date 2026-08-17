#!/usr/bin/env bash
#SBATCH --job-name=past-sm01-audit
#SBATCH --partition=research
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:10:00
#SBATCH --output=/home/kevin/cotcodec-runs/past-bench/sm01-audit-%j.out
#SBATCH --error=/home/kevin/cotcodec-runs/past-bench/sm01-audit-%j.err

set -Eeuo pipefail
umask 077

if [[ $# -ne 7 ]]; then
  echo "usage: $0 TOOLS_ROOT TOOLS_SHA OUTPUT_ROOT BATCH_SHA CONTINUOUS RESUMED ARCHIVE_SHA" >&2
  exit 2
fi
tools_root=$1
expected_tools_sha256=$2
output_root=$3
expected_batch_sha256=$4
continuous_root=$5
resumed_root=$6
expected_archive_sha256=$7
image_id='sha256:ebcf7eea7f1977f03e5e007edf265fcd120edadcd6d48e81f63df70715783150'
image_archive='/home/kevin/cotcodec-runs/past-bench/build-20260814-checkpoint-d4945b33-v1/image.tar'

: "${SLURM_JOB_ID:?determinism audit must execute inside Slurm}"
if [[ ! ${tools_root} =~ ^/home/kevin/cotcodec-runs/past-bench/inputs/past-sm01-audit-tools-[0-9a-f]{64}$ \
  || ! ${output_root} =~ ^/home/kevin/cotcodec-runs/past-bench/sm01-determinism-audit-[a-z0-9._-]{1,96}$ \
  || ! ${continuous_root} =~ ^/home/kevin/cotcodec-runs/past-bench/sm01-uninterrupted-[a-z0-9._-]{1,96}$ \
  || ! ${resumed_root} =~ ^/home/kevin/cotcodec-runs/past-bench/sm01-recovery-[a-z0-9._-]{1,96}$ \
  || ! ${expected_tools_sha256} =~ ^[0-9a-f]{64}$ \
  || ! ${expected_batch_sha256} =~ ^[0-9a-f]{64}$ \
  || ! ${expected_archive_sha256} =~ ^[0-9a-f]{64}$ \
  || -e ${output_root} || -L ${output_root} \
  || ! -d ${continuous_root} || -L ${continuous_root} \
  || ! -d ${resumed_root} || -L ${resumed_root} ]]; then
  echo "unsafe determinism-audit argument" >&2
  exit 2
fi
mkdir -m 0700 "${output_root}"

registered_batch="${tools_root}/infra/slurm/host-single-node/past-sm01-determinism-audit.sbatch"
if [[ ! -f ${registered_batch} || -L ${registered_batch} \
  || $(sha256sum "$0" | cut -d' ' -f1) != ${expected_batch_sha256} \
  || $(sha256sum "${registered_batch}" | cut -d' ' -f1) != ${expected_batch_sha256} \
  || $(sha256sum "${image_archive}" | cut -d' ' -f1) != ${expected_archive_sha256} ]]; then
  echo "determinism-audit evidence drifted" >&2
  exit 2
fi

actual_tools_sha256=$(python3 - "${tools_root}" <<'PY'
import hashlib,json,pathlib,sys
root=pathlib.Path(sys.argv[1]); rows=[]
expected={
 "infra/research/past-bench/audit_sm01_determinism_failure.py",
 "infra/research/past-bench/sm01_job_doctor.py",
 "infra/slurm/host-single-node/past-sm01-determinism-audit.sbatch",
}
for path in sorted(root.rglob("*")):
 if path.is_symlink() or (not path.is_file() and not path.is_dir()): raise SystemExit("unsafe audit tool")
 if path.is_file():
  relative=path.relative_to(root).as_posix()
  if relative not in expected: raise SystemExit("unregistered audit tool")
  payload=path.read_bytes(); rows.append({"path":relative,"sha256":hashlib.sha256(payload).hexdigest(),"size":len(payload)})
if {row["path"] for row in rows} != expected: raise SystemExit("incomplete audit tools")
print(hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(",",":")).encode()).hexdigest())
PY
)
if [[ ${actual_tools_sha256} != ${expected_tools_sha256} ]]; then
  echo "determinism-audit tool bundle drifted" >&2
  exit 2
fi

docker load --input "${image_archive}" >/dev/null
if [[ $(docker image inspect --format '{{.Id}}' "${image_id}") != ${image_id} ]]; then
  echo "PAST image ID drifted during determinism audit" >&2
  exit 2
fi
runtime_identity="$(id -u):$(id -g)"
docker run --rm --pull=never --network none --read-only \
  --tmpfs /tmp:rw,exec,nosuid,nodev,size=2g --cap-drop ALL \
  --security-opt no-new-privileges --pids-limit 1024 --user "${runtime_identity}" \
  --env HOME=/tmp/home --env PYTHONPATH=/tools/infra/research/past-bench \
  --volume "${tools_root}:/tools:ro" \
  --volume "${continuous_root}:/continuous:ro" \
  --volume "${resumed_root}:/resumed:ro" \
  --volume "${output_root}:/audit:rw" \
  --entrypoint /opt/past-bench-venv/bin/python "${image_id}" \
  /tools/infra/research/past-bench/audit_sm01_determinism_failure.py \
  --continuous-root /continuous --resumed-root /resumed \
  --output /audit/determinism-falsification.json >"${output_root}/audit.stdout"

python3 - "${output_root}/determinism-falsification.json" <<'PY'
import json,sys
report=json.load(open(sys.argv[1],encoding="utf-8"))
assert report["status"] == "PAST_SM01_RESTART_EQUIVALENCE_FALSIFIED"
assert report["registered_kill_triggered"] is True
assert report["score_mismatch_count"] > 0
assert report["pass_mismatch_count"] > 0
assert report["trace_mismatch_count"] > 0
print("PAST_SM01_DETERMINISM_AUDIT_PASS")
PY
