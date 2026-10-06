#!/usr/bin/env bash
#SBATCH --job-name=cotcodec-hermes-om-lifecycle
#SBATCH --partition=research
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=64G
#SBATCH --gres=gpu:h100:1
#SBATCH --time=00:30:00
#SBATCH --output=/home/kevin/cotcodec-runs/hermes-observational-memory/slurm-%j.out

set -euo pipefail
umask 077

run_root="${COTCODEC_RUN_ROOT:?COTCODEC_RUN_ROOT is required}"
input_root="${COTCODEC_INPUT_ROOT:?COTCODEC_INPUT_ROOT is required}"
source_archive="${COTCODEC_SOURCE_ARCHIVE:?COTCODEC_SOURCE_ARCHIVE is required}"
source_receipt="${COTCODEC_SOURCE_RECEIPT:?COTCODEC_SOURCE_RECEIPT is required}"
source_extractor="${COTCODEC_SOURCE_EXTRACTOR:?COTCODEC_SOURCE_EXTRACTOR is required}"
source_sha256="${COTCODEC_SOURCE_SHA256:?COTCODEC_SOURCE_SHA256 is required}"
source_git_sha="${COTCODEC_GIT_SHA:?COTCODEC_GIT_SHA is required}"
source_git_tree="${COTCODEC_GIT_TREE:?COTCODEC_GIT_TREE is required}"
extractor_sha256="${COTCODEC_SOURCE_EXTRACTOR_SHA256:?COTCODEC_SOURCE_EXTRACTOR_SHA256 is required}"
python_bin="${COTCODEC_PYTHON:-/usr/bin/python3}"

if [[ ! $source_sha256 =~ ^[0-9a-f]{64}$ \
   || ! $source_git_sha =~ ^[0-9a-f]{40}$ \
   || ! $source_git_tree =~ ^[0-9a-f]{40}$ \
   || ! $extractor_sha256 =~ ^[0-9a-f]{64}$ ]]; then
  echo "invalid source or extractor identity" >&2
  exit 64
fi
for required in "$input_root" "$run_root"; do
  if [[ ! -d $required || -L $required ]]; then
    echo "required root is not a real directory: $required" >&2
    exit 65
  fi
done
for required in "$source_archive" "$source_receipt" "$source_extractor"; do
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
   || $(sha256sum "$source_extractor" | awk '{print $1}') != "$extractor_sha256" ]]; then
  echo "source or extractor digest drifted" >&2
  exit 66
fi

gpu_inventory="$run_root/gpu-inventory-${SLURM_JOB_ID}.txt"
nvidia-smi -i "${CUDA_VISIBLE_DEVICES:?Slurm did not assign a GPU}" \
  --query-gpu=name,uuid,driver_version \
  --format=csv,noheader >"$gpu_inventory"
if [[ ! -s $gpu_inventory ]] || grep -qv H100 "$gpu_inventory"; then
  echo "the registered cell requires exactly an H100 allocation" >&2
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

archived_batch="$source_root/infra/slurm/host-single-node/hermes-observational-memory-lifecycle.sbatch"
archived_extractor="$source_root/scripts/extract_discovery_source_archive.py"
active_batch_sha256=$(sha256sum "$0" | awk '{print $1}')
if [[ $(sha256sum "$archived_batch" | awk '{print $1}') != "$active_batch_sha256" \
   || $(sha256sum "$archived_extractor" | awk '{print $1}') != "$extractor_sha256" ]]; then
  echo "active batch or extractor differs from the archived source" >&2
  exit 68
fi

context="$run_root/context-${SLURM_JOB_ID}"
"$python_bin" "$source_root/scripts/prepare_hermes_observational_memory_context.py" \
  --hermes-archive "$input_root/hermes.tar" \
  --plugin-archive "$input_root/plugin.tar" \
  --core-archive "$input_root/core.tar" \
  --observational-memory-wheel "$input_root/observational_memory-0.10.0-py3-none-any.whl" \
  --rank-bm25-wheel "$input_root/rank_bm25-0.2.2-py3-none-any.whl" \
  --numpy-wheel "$input_root/numpy-2.4.3-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl" \
  --pyyaml-wheel "$input_root/pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl" \
  --dockerfile "$source_root/infra/memory-baselines/hermes-observational-memory/Dockerfile" \
  --doctor "$source_root/infra/memory-baselines/hermes-observational-memory/doctor.py" \
  --output-dir "$context" >"$run_root/context-${SLURM_JOB_ID}.receipt.stdout.json"

image="cotcodec-hermes-om-lifecycle:90d83c1-job-${SLURM_JOB_ID}"
base_image='cotcodec-research:8c51687b-architecture'
base_image_id='sha256:ba360ea13ea50e77e4900cb258c4dc73156060295abd381899f90f9991cedd10'
if [[ $(docker image inspect --format '{{.Id}}' "$base_image") != "$base_image_id" ]]; then
  echo "exact cached discovery substrate is unavailable or drifted" >&2
  exit 69
fi
docker build \
  --build-arg BASE_IMAGE="$base_image" \
  --build-arg HERMES_GIT_SHA=a90d5369f76c87c98547d2e283aa26d5cfabf322 \
  --build-arg HERMES_GIT_TREE=963eb136bfb21fd0b296a40529cbb3575c610874 \
  --build-arg HERMES_ARCHIVE_SHA256=2a2934d3c8379816b2e3919f4cf1191f04e93f136da6f2128246d368644a9514 \
  --build-arg PLUGIN_GIT_SHA=90d83c1ff768d80f99f4e3ef4d76269f90e1c808 \
  --build-arg PLUGIN_GIT_TREE=5cf00ebd8f4d57673469e2e45f3954ac37d875af \
  --build-arg PLUGIN_ARCHIVE_SHA256=33d6bc75ff850fdf9140d225bc6636c3cc22f0c015f897c546ce226b7cc551c4 \
  --build-arg CORE_GIT_SHA=6bbc16e81ad1258ee1e8ba37c9efcc6ce36a0208 \
  --build-arg CORE_GIT_TREE=96f4288c19b78b0bdda8568efa0c5b1435d64552 \
  --build-arg CORE_ARCHIVE_SHA256=0d103be2c781b0ac546a5fa16cb81c1f877513675b83ca33b06cd7fa4d8312f0 \
  --tag "$image" \
  "$context"

image_id=$(docker image inspect --format '{{.Id}}' "$image")
if [[ ! $image_id =~ ^sha256:[0-9a-f]{64}$ ]]; then
  echo "Docker returned a non-immutable image ID" >&2
  exit 69
fi
image_inspect="$run_root/image-inspect-${SLURM_JOB_ID}.json"
image_archive="$run_root/image-${SLURM_JOB_ID}.tar"
docker image inspect "$image" >"$image_inspect"
docker image save --output "$image_archive" "$image"

syft_image='anchore/syft@sha256:41f8289664101d6ebab30a97ac8df6b6f86b92d8343285ca90f428e2bc353106'
syft_id='sha256:e6ff5da240b940ab010282f502ae688019379cdee51578f76374ed9b29ef03e6'
if [[ $(docker image inspect --format '{{.Id}}' "$syft_image") != "$syft_id" ]]; then
  echo "exact cached Syft image is unavailable or drifted" >&2
  exit 70
fi
sbom_dir="$run_root/sbom-${SLURM_JOB_ID}"
mkdir -m 700 "$sbom_dir"
syft_tmp="$run_root/syft-tmp-${SLURM_JOB_ID}"
mkdir -m 700 "$syft_tmp"
docker run --rm --pull=never \
  --network none \
  --read-only \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  --user "$(id -u):$(id -g)" \
  --env HOME=/tmp \
  --env SYFT_CHECK_FOR_APP_UPDATE=false \
  --volume "$image_archive:/input/image.tar:ro" \
  --volume "$sbom_dir:/output:rw" \
  --volume "$syft_tmp:/tmp:rw" \
  "$syft_image" \
  docker-archive:/input/image.tar \
  --output spdx-json=/output/sbom.spdx.json
if [[ ! -s "$sbom_dir/sbom.spdx.json" ]]; then
  echo "Syft did not produce an SBOM" >&2
  exit 71
fi

"$python_bin" "$source_root/scripts/run_hermes_observational_memory_doctor.py" \
  --image "$image" \
  --expected-image-id "$image_id" \
  --image-archive "$image_archive" \
  --sbom "$sbom_dir/sbom.spdx.json" \
  --output-dir "$run_root/lifecycle-${SLURM_JOB_ID}" \
  >"$run_root/lifecycle-${SLURM_JOB_ID}.stdout.json"

"$python_bin" - "$run_root" "$SLURM_JOB_ID" "$image" "$image_id" "$active_batch_sha256" <<'PY'
import hashlib, json, pathlib, sys
root = pathlib.Path(sys.argv[1])
job = sys.argv[2]
payload = {
    "schema_version": 1,
    "slurm_job_id": int(job),
    "slurm_job_name": "cotcodec-hermes-om-lifecycle",
    "image": sys.argv[3],
    "image_id": sys.argv[4],
    "gpu_inventory_sha256": hashlib.sha256((root / f"gpu-inventory-{job}.txt").read_bytes()).hexdigest(),
    "image_inspect_sha256": hashlib.sha256((root / f"image-inspect-{job}.json").read_bytes()).hexdigest(),
    "image_archive_sha256": hashlib.sha256((root / f"image-{job}.tar").read_bytes()).hexdigest(),
    "sbom_sha256": hashlib.sha256((root / f"sbom-{job}/sbom.spdx.json").read_bytes()).hexdigest(),
    "report_sha256": hashlib.sha256((root / f"lifecycle-{job}/report.json").read_bytes()).hexdigest(),
    "batch_sha256": sys.argv[5],
}
(root / f"job-{job}.receipt.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
PY
