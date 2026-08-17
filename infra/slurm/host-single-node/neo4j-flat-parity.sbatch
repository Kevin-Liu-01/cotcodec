#!/usr/bin/env bash
#SBATCH --job-name=cotcodec-neo4j-flat-parity
#SBATCH --partition=research
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=64G
#SBATCH --gres=gpu:h100:1
#SBATCH --time=00:30:00
#SBATCH --output=/home/kevin/cotcodec-runs/neo4j-flat-parity/slurm-%j.out

set -euo pipefail
umask 077

run_root="${COTCODEC_RUN_ROOT:?COTCODEC_RUN_ROOT is required}"
source_archive="${COTCODEC_SOURCE_ARCHIVE:?COTCODEC_SOURCE_ARCHIVE is required}"
source_receipt="${COTCODEC_SOURCE_RECEIPT:?COTCODEC_SOURCE_RECEIPT is required}"
source_extractor="${COTCODEC_SOURCE_EXTRACTOR:?COTCODEC_SOURCE_EXTRACTOR is required}"
client_image_archive="${COTCODEC_CLIENT_IMAGE_ARCHIVE:?COTCODEC_CLIENT_IMAGE_ARCHIVE is required}"
client_sbom="${COTCODEC_CLIENT_SBOM:?COTCODEC_CLIENT_SBOM is required}"
source_sha256="${COTCODEC_SOURCE_SHA256:?COTCODEC_SOURCE_SHA256 is required}"
source_receipt_sha256="${COTCODEC_SOURCE_RECEIPT_SHA256:?COTCODEC_SOURCE_RECEIPT_SHA256 is required}"
source_git_sha="${COTCODEC_GIT_SHA:?COTCODEC_GIT_SHA is required}"
source_git_tree="${COTCODEC_GIT_TREE:?COTCODEC_GIT_TREE is required}"
extractor_sha256="${COTCODEC_SOURCE_EXTRACTOR_SHA256:?COTCODEC_SOURCE_EXTRACTOR_SHA256 is required}"
client_image_archive_sha256="${COTCODEC_CLIENT_IMAGE_ARCHIVE_SHA256:?COTCODEC_CLIENT_IMAGE_ARCHIVE_SHA256 is required}"
client_sbom_sha256="${COTCODEC_CLIENT_SBOM_SHA256:?COTCODEC_CLIENT_SBOM_SHA256 is required}"
expected_client_image_id="${COTCODEC_CLIENT_IMAGE_ID:?COTCODEC_CLIENT_IMAGE_ID is required}"
python_bin="${COTCODEC_PYTHON:-/home/kevin/cotcodec/.venv/bin/python}"

for digest in \
  "$source_sha256" "$source_receipt_sha256" "$extractor_sha256" \
  "$client_image_archive_sha256" "$client_sbom_sha256"; do
  if [[ ! $digest =~ ^[0-9a-f]{64}$ ]]; then
    echo "invalid SHA-256 identity" >&2
    exit 64
  fi
done
if [[ ! $source_git_sha =~ ^[0-9a-f]{40}$ \
   || ! $source_git_tree =~ ^[0-9a-f]{40}$ \
   || ! $expected_client_image_id =~ ^sha256:[0-9a-f]{64}$ ]]; then
  echo "invalid Git or image identity" >&2
  exit 64
fi
if [[ ! -d $run_root || -L $run_root ]]; then
  echo "run root is not a real directory" >&2
  exit 65
fi
for required in \
  "$source_archive" "$source_receipt" "$source_extractor" \
  "$client_image_archive" "$client_sbom"; do
  if [[ ! -f $required || -L $required ]]; then
    echo "required input is not a regular file: $required" >&2
    exit 65
  fi
done
if [[ ! -x $python_bin ]]; then
  echo "configured Python is unavailable" >&2
  exit 65
fi
if [[ $(sha256sum "$source_archive" | awk '{print $1}') != "$source_sha256" \
   || $(sha256sum "$source_receipt" | awk '{print $1}') != "$source_receipt_sha256" \
   || $(sha256sum "$source_extractor" | awk '{print $1}') != "$extractor_sha256" \
   || $(sha256sum "$client_image_archive" | awk '{print $1}') != "$client_image_archive_sha256" \
   || $(sha256sum "$client_sbom" | awk '{print $1}') != "$client_sbom_sha256" ]]; then
  echo "input digest drifted" >&2
  exit 66
fi

gpu_inventory="$run_root/gpu-inventory-${SLURM_JOB_ID}.txt"
nvidia-smi -i "${CUDA_VISIBLE_DEVICES:?Slurm did not assign a GPU}" \
  --query-gpu=name,uuid,driver_version --format=csv,noheader >"$gpu_inventory"
if [[ ! -s $gpu_inventory ]] || grep -qv H100 "$gpu_inventory"; then
  echo "the registered component job requires exactly an H100 allocation" >&2
  exit 67
fi

source_root="$run_root/source-${SLURM_JOB_ID}"
if [[ -e $source_root ]]; then
  echo "job source output already exists" >&2
  exit 67
fi
mkdir -m 700 "$source_root"
"$python_bin" "$source_extractor" \
  --archive "$source_archive" \
  --receipt "$source_receipt" \
  --output-dir "$source_root" \
  --expected-archive-sha256 "$source_sha256" \
  --expected-git-sha "$source_git_sha" \
  --expected-git-tree "$source_git_tree"

archived_batch="$source_root/infra/slurm/host-single-node/neo4j-flat-parity.sbatch"
archived_extractor="$source_root/scripts/extract_discovery_source_archive.py"
active_batch_sha256=$(sha256sum "$0" | awk '{print $1}')
if [[ $(sha256sum "$archived_batch" | awk '{print $1}') != "$active_batch_sha256" \
   || $(sha256sum "$archived_extractor" | awk '{print $1}') != "$extractor_sha256" ]]; then
  echo "active batch or extractor differs from the archived source" >&2
  exit 68
fi

client_image='cotcodec-neo4j-preference-doctor:231d60e-cluster-amd64-slurm-v1'
docker image load --input "$client_image_archive"
if [[ $(docker image inspect --format '{{.Id}}' "$client_image") \
      != "$expected_client_image_id" ]]; then
  echo "prebuilt client image identity drifted" >&2
  exit 69
fi

parity_root="$run_root/parity-${SLURM_JOB_ID}"
"$python_bin" "$source_root/scripts/run_neo4j_flat_parity_doctor.py" \
  --client-image "$client_image" \
  --expected-client-image-id "$expected_client_image_id" \
  --parity-doctor "$source_root/infra/memory-baselines/neo4j-agent-memory/parity_doctor.py" \
  --fixture-module "$source_root/harness/memory_trials/neo4j_flat_parity.py" \
  --output-dir "$parity_root" \
  >"$run_root/parity-${SLURM_JOB_ID}.stdout.json"

client_inspect="$run_root/client-image-inspect-${SLURM_JOB_ID}.json"
neo4j_inspect="$run_root/neo4j-image-inspect-${SLURM_JOB_ID}.json"
docker image inspect "$client_image" >"$client_inspect"
docker image inspect \
  'neo4j:5.26.29-community@sha256:865213f53381e8d2ef3eec08b11741a6722d388a5e70b134135186a9b5cb27a6' \
  >"$neo4j_inspect"

sacct_output="$run_root/sacct-${SLURM_JOB_ID}.txt"
if command -v sacct >/dev/null 2>&1; then
  sacct -j "$SLURM_JOB_ID" --format=JobID,State,ExitCode,Elapsed,AllocTRES \
    >"$sacct_output" 2>&1 || true
else
  printf '%s\n' 'sacct unavailable' >"$sacct_output"
fi

"$python_bin" - \
  "$run_root" "$SLURM_JOB_ID" "$client_image" "$expected_client_image_id" \
  "$active_batch_sha256" "$source_sha256" "$client_image_archive_sha256" \
  "$client_sbom_sha256" <<'PY'
import hashlib
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
job = sys.argv[2]

def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

payload = {
    "schema_version": 1,
    "slurm_job_id": int(job),
    "slurm_job_name": "cotcodec-neo4j-flat-parity",
    "client_image": sys.argv[3],
    "client_image_id": sys.argv[4],
    "batch_sha256": sys.argv[5],
    "source_archive_sha256": sys.argv[6],
    "client_image_archive_sha256": sys.argv[7],
    "client_sbom_sha256": sys.argv[8],
    "gpu_inventory_sha256": digest(root / f"gpu-inventory-{job}.txt"),
    "client_image_inspect_sha256": digest(
        root / f"client-image-inspect-{job}.json"
    ),
    "neo4j_image_inspect_sha256": digest(
        root / f"neo4j-image-inspect-{job}.json"
    ),
    "report_sha256": digest(root / f"parity-{job}/report.json"),
    "manifest_sha256": digest(root / f"parity-{job}/manifest.json"),
    "sacct_sha256": digest(root / f"sacct-{job}.txt"),
    "container_gpu_count": 0,
    "model_calls": 0,
}
(root / f"job-{job}.receipt.json").write_text(
    json.dumps(payload, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
PY
