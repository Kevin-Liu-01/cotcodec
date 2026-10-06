#!/usr/bin/env bash
set -euo pipefail

readonly alpine_image="docker.io/library/alpine@sha256:14358309a308569c32bdc37e2e0e9694be33a9d99e68afb0f5ff33cc1f695dce"
export PATH="${HOME}/.local/bin:${PATH}"

: "${SLURM_JOB_ID:?doctor must run inside a Slurm allocation}"
: "${SLURM_STEP_GPUS:?Slurm omitted the step GPU allocation}"
: "${SLURM_GPUS_ON_NODE:?Slurm omitted the node GPU count}"
: "${CUDA_VISIBLE_DEVICES:?Slurm omitted CUDA_VISIBLE_DEVICES}"

if [[ ${SLURM_GPUS_ON_NODE} != 1 ]]; then
  echo "expected exactly one allocated GPU, got ${SLURM_GPUS_ON_NODE}" >&2
  exit 10
fi
if [[ ${CUDA_VISIBLE_DEVICES} == *,* ]]; then
  echo "expected one visible CUDA ordinal, got ${CUDA_VISIBLE_DEVICES}" >&2
  exit 11
fi

echo "SLURM_ALLOCATION_JOB_ID=${SLURM_JOB_ID}"
echo "SLURM_STEP_GPUS=${SLURM_STEP_GPUS}"
echo "SLURM_GPUS_ON_NODE=${SLURM_GPUS_ON_NODE}"
echo "CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES}"

smolvm machine run \
  --net \
  --unprivileged \
  --cpus 2 \
  --mem 2048 \
  --image "${alpine_image}" \
  -e "SLURM_JOB_ID=${SLURM_JOB_ID}" \
  -e "SLURM_STEP_GPUS=${SLURM_STEP_GPUS}" \
  -e "CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES}" \
  -- sh -ec '
    test -n "$SLURM_JOB_ID"
    test -n "$SLURM_STEP_GPUS"
    test -n "$CUDA_VISIBLE_DEVICES"
    echo SCHEDULER_VM_BOUNDARY_PASS
    echo "guest_job_id=$SLURM_JOB_ID"
    echo "guest_step_gpus=$SLURM_STEP_GPUS"
    echo "guest_cuda_visible=$CUDA_VISIBLE_DEVICES"
    uname -a
  '
