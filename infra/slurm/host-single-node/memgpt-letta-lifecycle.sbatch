#!/usr/bin/env bash
#SBATCH --job-name=memgpt-letta-cpu
#SBATCH --partition=research
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:40:00
#SBATCH --signal=B:USR1@120
#SBATCH --output=slurm-%x-%j.out

set -Eeuo pipefail
umask 077

: "${COTCODEC_STAGE_ROOT:?Set the staged project root}"
: "${COTCODEC_SOURCE_ROOT:?Set the exact Letta source checkout}"
: "${COTCODEC_SOURCE_ARCHIVE:?Set the exact Letta source archive}"
: "${COTCODEC_CONTEXT_ROOT:?Set the exact Letta Code context checkout}"
: "${COTCODEC_CONTEXT_ARCHIVE:?Set the exact Letta Code context archive}"
: "${COTCODEC_OUTPUT_ROOT:?Set a new persistent output directory}"
: "${COTCODEC_BATCH_SHA256:?Set the audited batch digest}"
: "${COTCODEC_RUNNER_SHA256:?Set the audited runner digest}"
: "${COTCODEC_VALIDATOR_SHA256:?Set the audited validator digest}"
: "${COTCODEC_DOCTOR_SHA256:?Set the audited doctor digest}"
: "${COTCODEC_EXPERIMENT_SHA256:?Set the audited experiment digest}"

for value in \
  "${COTCODEC_BATCH_SHA256}" \
  "${COTCODEC_RUNNER_SHA256}" \
  "${COTCODEC_VALIDATOR_SHA256}" \
  "${COTCODEC_DOCTOR_SHA256}" \
  "${COTCODEC_EXPERIMENT_SHA256}"; do
  if [[ ! "${value}" =~ ^[0-9a-f]{64}$ ]]; then
    echo "all digest fields must be lowercase 64-hex" >&2
    exit 2
  fi
done

if [[ "$(sha256sum "$0" | cut -d' ' -f1)" != "${COTCODEC_BATCH_SHA256}" ]]; then
  echo "active batch script differs from the submitted digest" >&2
  exit 2
fi
if [[ "$(sha256sum "${COTCODEC_STAGE_ROOT}/scripts/run_memgpt_letta_lifecycle_doctor.py" | cut -d' ' -f1)" != "${COTCODEC_RUNNER_SHA256}" ]]; then
  echo "runner digest drifted" >&2
  exit 2
fi
if [[ "$(sha256sum "${COTCODEC_STAGE_ROOT}/scripts/validate_memgpt_letta_lifecycle_experiment.py" | cut -d' ' -f1)" != "${COTCODEC_VALIDATOR_SHA256}" ]]; then
  echo "validator digest drifted" >&2
  exit 2
fi
if [[ "$(sha256sum "${COTCODEC_STAGE_ROOT}/infra/memory-baselines/memgpt-letta/doctor.py" | cut -d' ' -f1)" != "${COTCODEC_DOCTOR_SHA256}" ]]; then
  echo "doctor digest drifted" >&2
  exit 2
fi
if [[ "$(sha256sum "${COTCODEC_STAGE_ROOT}/experiments/memory/stage3-memgpt-letta-native-lifecycle-doctor.yaml" | cut -d' ' -f1)" != "${COTCODEC_EXPERIMENT_SHA256}" ]]; then
  echo "experiment digest drifted" >&2
  exit 2
fi
if [[ -e "${COTCODEC_OUTPUT_ROOT}" ]]; then
  echo "output directory already exists" >&2
  exit 2
fi
for path in \
  "${COTCODEC_SOURCE_ROOT}" \
  "${COTCODEC_CONTEXT_ROOT}"; do
  if [[ ! -d "${path}" || -L "${path}" ]]; then
    echo "source roots must be real directories" >&2
    exit 2
  fi
done
for path in \
  "${COTCODEC_SOURCE_ARCHIVE}" \
  "${COTCODEC_CONTEXT_ARCHIVE}"; do
  if [[ ! -f "${path}" || -L "${path}" ]]; then
    echo "source archives must be regular files" >&2
    exit 2
  fi
done
if [[ "${SLURM_CPUS_PER_TASK:-}" != "4" || "${SLURM_MEM_PER_NODE:-}" != "16384" ]]; then
  echo "Slurm CPU or memory allocation drifted" >&2
  exit 2
fi

cd "${COTCODEC_STAGE_ROOT}"
exec python3 scripts/run_memgpt_letta_lifecycle_doctor.py \
  --source-root "${COTCODEC_SOURCE_ROOT}" \
  --source-archive "${COTCODEC_SOURCE_ARCHIVE}" \
  --context-root "${COTCODEC_CONTEXT_ROOT}" \
  --context-archive "${COTCODEC_CONTEXT_ARCHIVE}" \
  --output "${COTCODEC_OUTPUT_ROOT}"
