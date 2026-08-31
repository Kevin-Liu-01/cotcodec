#!/usr/bin/env bash
#SBATCH --job-name=mnemo-cortex-cpu
#SBATCH --partition=research
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:30:00
#SBATCH --signal=B:USR1@120
#SBATCH --output=slurm-%x-%j.out

set -Eeuo pipefail
umask 077

: "${COTCODEC_STAGE_ROOT:?Set the staged project root}"
: "${COTCODEC_SOURCE_ROOT:?Set the exact source checkout}"
: "${COTCODEC_WHEELHOUSE_ROOT:?Set the receipted offline wheelhouse}"
: "${COTCODEC_OUTPUT_ROOT:?Set a new persistent output directory}"
: "${COTCODEC_BATCH_SHA256:?Set the audited batch digest}"
: "${COTCODEC_RUNNER_SHA256:?Set the audited runner digest}"
: "${COTCODEC_DOCTOR_SHA256:?Set the audited doctor digest}"
: "${COTCODEC_EXPERIMENT_SHA256:?Set the audited experiment digest}"
: "${COTCODEC_WHEELHOUSE_MANIFEST_SHA256:?Set the audited wheelhouse manifest digest}"

for value in \
  "${COTCODEC_BATCH_SHA256}" \
  "${COTCODEC_RUNNER_SHA256}" \
  "${COTCODEC_DOCTOR_SHA256}" \
  "${COTCODEC_EXPERIMENT_SHA256}" \
  "${COTCODEC_WHEELHOUSE_MANIFEST_SHA256}"; do
  if [[ ! "${value}" =~ ^[0-9a-f]{64}$ ]]; then
    echo "all digest fields must be lowercase 64-hex" >&2
    exit 2
  fi
done

if [[ "$(sha256sum "$0" | cut -d' ' -f1)" != "${COTCODEC_BATCH_SHA256}" ]]; then
  echo "active batch script differs from the submitted digest" >&2
  exit 2
fi
if [[ "$(sha256sum "${COTCODEC_STAGE_ROOT}/scripts/run_mnemo_cortex_lifecycle_doctor.py" | cut -d' ' -f1)" != "${COTCODEC_RUNNER_SHA256}" ]]; then
  echo "runner digest drifted" >&2
  exit 2
fi
if [[ "$(sha256sum "${COTCODEC_STAGE_ROOT}/infra/memory-baselines/mnemo-cortex/doctor.py" | cut -d' ' -f1)" != "${COTCODEC_DOCTOR_SHA256}" ]]; then
  echo "doctor digest drifted" >&2
  exit 2
fi
if [[ "$(sha256sum "${COTCODEC_STAGE_ROOT}/experiments/memory/stage3-mnemo-cortex-native-lifecycle-doctor.yaml" | cut -d' ' -f1)" != "${COTCODEC_EXPERIMENT_SHA256}" ]]; then
  echo "experiment digest drifted" >&2
  exit 2
fi
if [[ "$(sha256sum "${COTCODEC_STAGE_ROOT}/infra/memory-baselines/mnemo-cortex/wheelhouse-manifest.json" | cut -d' ' -f1)" != "${COTCODEC_WHEELHOUSE_MANIFEST_SHA256}" ]]; then
  echo "staged wheelhouse manifest digest drifted" >&2
  exit 2
fi
if [[ "$(sha256sum "${COTCODEC_WHEELHOUSE_ROOT}/wheelhouse-manifest.json" | cut -d' ' -f1)" != "${COTCODEC_WHEELHOUSE_MANIFEST_SHA256}" ]]; then
  echo "transported wheelhouse manifest digest drifted" >&2
  exit 2
fi
if [[ -e "${COTCODEC_OUTPUT_ROOT}" ]]; then
  echo "output directory already exists" >&2
  exit 2
fi
if [[ ! -d "${COTCODEC_SOURCE_ROOT}" || -L "${COTCODEC_SOURCE_ROOT}" ]]; then
  echo "source root must be a real directory" >&2
  exit 2
fi
if [[ ! -d "${COTCODEC_WHEELHOUSE_ROOT}" || -L "${COTCODEC_WHEELHOUSE_ROOT}" ]]; then
  echo "wheelhouse root must be a real directory" >&2
  exit 2
fi
if [[ "${SLURM_CPUS_PER_TASK:-}" != "4" || "${SLURM_MEM_PER_NODE:-}" != "16384" ]]; then
  echo "Slurm CPU or memory allocation drifted" >&2
  exit 2
fi

cd "${COTCODEC_STAGE_ROOT}"
exec python3 scripts/run_mnemo_cortex_lifecycle_doctor.py \
  --source-root "${COTCODEC_SOURCE_ROOT}" \
  --wheelhouse-root "${COTCODEC_WHEELHOUSE_ROOT}" \
  --output "${COTCODEC_OUTPUT_ROOT}"
