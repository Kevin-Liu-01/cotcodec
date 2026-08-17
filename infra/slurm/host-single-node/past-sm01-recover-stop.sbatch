#!/usr/bin/env bash
#SBATCH --job-name=past-sm01-recover
#SBATCH --partition=research
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:10:00
#SBATCH --output=/home/kevin/cotcodec-runs/past-bench/sm01-recover-%j.out
#SBATCH --error=/home/kevin/cotcodec-runs/past-bench/sm01-recover-%j.err

set -Eeuo pipefail
umask 077

if [[ $# -ne 7 ]]; then
  echo "usage: $0 TOOLS_ROOT TOOLS_SHA OUTPUT_ROOT BATCH_SHA WORKLOAD_JOB IMAGE_ARCHIVE_SHA MODE" >&2
  exit 2
fi
tools_root=$1
expected_tools_sha256=$2
output_root=$3
expected_batch_sha256=$4
workload_slurm_job_id=$5
expected_archive_sha256=$6
mode=$7
image_id='sha256:ebcf7eea7f1977f03e5e007edf265fcd120edadcd6d48e81f63df70715783150'
image_archive='/home/kevin/cotcodec-runs/past-bench/build-20260814-checkpoint-d4945b33-v1/image.tar'

: "${SLURM_JOB_ID:?SM01 recovery must execute inside Slurm}"
if [[ ! ${tools_root} =~ ^/home/kevin/cotcodec-runs/past-bench/inputs/past-sm01-recovery-tools-[0-9a-f]{64}$ \
  || ! ${output_root} =~ ^/home/kevin/cotcodec-runs/past-bench/sm01-[a-z0-9._-]{1,96}$ \
  || ! ${expected_tools_sha256} =~ ^[0-9a-f]{64}$ \
  || ! ${expected_batch_sha256} =~ ^[0-9a-f]{64}$ \
  || ! ${expected_archive_sha256} =~ ^[0-9a-f]{64}$ \
  || ! ${workload_slurm_job_id} =~ ^[1-9][0-9]*$ \
  || ! ${mode} =~ ^(stop-after-episode-three|fresh-job-resume)$ \
  || ! -d ${output_root} || -L ${output_root} ]]; then
  echo "unsafe SM01 recovery argument" >&2
  exit 2
fi
evidence_root="${output_root}/evidence"
run_root="${output_root}/run"
receipt_name="run-receipt-${mode}.json"
projection_name="trace-projection-${mode}.json"
if [[ ! -d ${evidence_root} || -L ${evidence_root} \
  || ! -d ${run_root} || -L ${run_root} \
  || -e ${evidence_root}/${receipt_name} \
  || -L ${evidence_root}/${receipt_name} \
  || -e ${evidence_root}/${projection_name} \
  || -L ${evidence_root}/${projection_name} ]]; then
  echo "SM01 recovery target is missing, unsafe, or already finalized" >&2
  exit 2
fi

registered_batch="${tools_root}/infra/slurm/host-single-node/past-sm01-recover-stop.sbatch"
if [[ ! -f ${registered_batch} || -L ${registered_batch} \
  || $(sha256sum "$0" | cut -d' ' -f1) != ${expected_batch_sha256} \
  || $(sha256sum "${registered_batch}" | cut -d' ' -f1) != ${expected_batch_sha256} \
  || $(sha256sum "${image_archive}" | cut -d' ' -f1) != ${expected_archive_sha256} ]]; then
  echo "SM01 recovery evidence drifted" >&2
  exit 2
fi

actual_tools_sha256=$(python3 - "${tools_root}" <<'PY'
import hashlib,json,pathlib,sys
root=pathlib.Path(sys.argv[1]); rows=[]
expected={
 "infra/research/past-bench/sm01_job_doctor.py",
 "infra/slurm/host-single-node/past-sm01-recover-stop.sbatch",
}
for path in sorted(root.rglob("*")):
 if path.is_symlink() or (not path.is_file() and not path.is_dir()): raise SystemExit("unsafe recovery tool")
 if path.is_file():
  relative=path.relative_to(root).as_posix()
  if relative not in expected: raise SystemExit("unregistered recovery tool")
  payload=path.read_bytes(); rows.append({"path":relative,"sha256":hashlib.sha256(payload).hexdigest(),"size":len(payload)})
if {row["path"] for row in rows} != expected: raise SystemExit("incomplete recovery tools")
print(hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(",",":")).encode()).hexdigest())
PY
)
if [[ ${actual_tools_sha256} != ${expected_tools_sha256} ]]; then
  echo "SM01 recovery tool bundle drifted" >&2
  exit 2
fi

docker load --input "${image_archive}" >/dev/null
if [[ $(docker image inspect --format '{{.Id}}' "${image_id}") != ${image_id} ]]; then
  echo "PAST image ID drifted during SM01 recovery" >&2
  exit 2
fi
runtime_identity="$(id -u):$(id -g)"
recovery_stdout="${evidence_root}/recovery-validation-${SLURM_JOB_ID}.json"
if [[ -e ${recovery_stdout} || -L ${recovery_stdout} ]]; then
  echo "SM01 recovery stdout already exists" >&2
  exit 2
fi
recovery_command='recover-stop'
expected_status='PAST_SM01_CONTROLLED_STOP_CHECKPOINT_RECOVERED_AFTER_DOCTOR_FIX'
if [[ ${mode} == fresh-job-resume ]]; then
  recovery_command='recover-complete'
  expected_status='PAST_SM01_FRESH_RESUME_RECOVERED_AFTER_DOCTOR_FIX'
fi
docker run --rm --pull=never --network none --read-only \
  --tmpfs /tmp:rw,exec,nosuid,nodev,size=2g --cap-drop ALL \
  --security-opt no-new-privileges --pids-limit 1024 --user "${runtime_identity}" \
  --env HOME=/tmp/home --env PYTHONPATH=/tools \
  --volume "${tools_root}:/tools:ro" --volume "${output_root}:/outputs:rw" \
  --entrypoint /opt/past-bench-venv/bin/python "${image_id}" \
  /tools/infra/research/past-bench/sm01_job_doctor.py "${recovery_command}" \
  --run-root /outputs/run --evidence-root /outputs/evidence \
  --workload-slurm-job-id "${workload_slurm_job_id}" \
  --validation-slurm-job-id "${SLURM_JOB_ID}" >"${recovery_stdout}"

python3 - "${evidence_root}/${receipt_name}" "${workload_slurm_job_id}" \
  "${SLURM_JOB_ID}" "${expected_status}" <<'PY'
import json,sys
receipt=json.load(open(sys.argv[1],encoding="utf-8"))
assert receipt["status"] == sys.argv[4]
assert receipt["slurm_job_id"] == int(sys.argv[2])
assert receipt["validation_slurm_job_id"] == int(sys.argv[3])
print("PAST_SM01_RECOVERY_PASS", receipt["mode"])
PY
