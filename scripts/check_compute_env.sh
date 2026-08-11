#!/usr/bin/env bash
set -Eeuo pipefail

mode="${1:-builder}"
failures=0

case "${mode}" in
  docker) mode="builder" ;;
  slurm) mode="login" ;;
  builder|login|allocation|container) ;;
  *)
    echo "usage: $0 [builder|login|allocation|container]" >&2
    exit 2
    ;;
esac

check_command() {
  local name="$1"
  if command -v "${name}" >/dev/null 2>&1; then
    echo "PASS command ${name}: $(command -v "${name}")"
  else
    echo "FAIL command ${name}: missing"
    failures=$((failures + 1))
  fi
}

check_gpu_visibility() {
  local expected_gpus="$1"
  check_command nvidia-smi
  if ! command -v nvidia-smi >/dev/null 2>&1; then
    return
  fi
  local gpu_count
  local gpu_names
  gpu_count="$(nvidia-smi --query-gpu=name --format=csv,noheader | wc -l | tr -d ' ')"
  gpu_names="$(nvidia-smi --query-gpu=name --format=csv,noheader | paste -sd: -)"
  echo "INFO visible_gpus=${gpu_count} names=${gpu_names}"
  if [[ "${gpu_count}" -ne "${expected_gpus}" ]]; then
    echo "FAIL visible GPU count does not exactly match COTCODEC_EXPECTED_GPUS"
    failures=$((failures + 1))
  fi
  if nvidia-smi --query-gpu=name --format=csv,noheader | grep -qv 'H100'; then
    echo "FAIL at least one visible GPU is not an H100"
    failures=$((failures + 1))
  fi
  if [[ -n "${SLURM_GPUS_ON_NODE:-}" && "${SLURM_GPUS_ON_NODE}" != "${expected_gpus}" ]]; then
    echo "FAIL SLURM_GPUS_ON_NODE does not match the manifest"
    failures=$((failures + 1))
  fi
  if [[ -n "${CUDA_VISIBLE_DEVICES:-}" ]]; then
    local cuda_visible_count
    cuda_visible_count="$(awk -F, '{print NF}' <<< "${CUDA_VISIBLE_DEVICES}")"
    if [[ "${cuda_visible_count}" -ne "${expected_gpus}" ]]; then
      echo "FAIL CUDA_VISIBLE_DEVICES does not expose exactly the requested count"
      failures=$((failures + 1))
    fi
  fi
}

if [[ "${mode}" == "builder" ]]; then
  builder_ready=false
  if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
    echo "PASS Docker builder is reachable"
    builder_ready=true
  fi
  if command -v podman >/dev/null 2>&1 && podman info >/dev/null 2>&1; then
    echo "PASS rootless Podman builder is reachable"
    builder_ready=true
  fi
  if [[ "${builder_ready}" != true ]]; then
    echo "FAIL neither Docker nor Podman builder is reachable by user $(id -un)"
    failures=$((failures + 1))
  fi
fi

if [[ "${mode}" == "login" ]]; then
  check_command tmux
  check_command sbatch
  check_command srun
  check_command sinfo
  if command -v srun >/dev/null 2>&1 && ! srun --help 2>&1 | grep -q -- '--container-image'; then
    echo "FAIL Slurm lacks Pyxis --container-image support"
    failures=$((failures + 1))
  fi
  if command -v sinfo >/dev/null 2>&1 && ! sinfo --noheader >/dev/null 2>&1; then
    echo "FAIL Slurm controller is not reachable"
    failures=$((failures + 1))
  fi
  if [[ -n "${COTCODEC_RUN_ROOT:-}" ]]; then
    if [[ -d "${COTCODEC_RUN_ROOT}" && -w "${COTCODEC_RUN_ROOT}" ]]; then
      echo "PASS run root is writable: ${COTCODEC_RUN_ROOT}"
    else
      echo "FAIL run root is not a writable directory: ${COTCODEC_RUN_ROOT}"
      failures=$((failures + 1))
    fi
  else
    echo "INFO COTCODEC_RUN_ROOT not set; shared-storage write check skipped"
  fi
fi

if [[ "${mode}" == "allocation" ]]; then
  check_gpu_visibility "${COTCODEC_EXPECTED_GPUS:-1}"
fi

if [[ "${mode}" == "container" ]]; then
  check_command python
  if [[ -z "${COTCODEC_OUTPUT_DIR:-}" || ! -d "${COTCODEC_OUTPUT_DIR}" || ! -w "${COTCODEC_OUTPUT_DIR}" ]]; then
    echo "FAIL COTCODEC_OUTPUT_DIR is not a writable mounted directory"
    failures=$((failures + 1))
  else
    echo "PASS output mount is writable: ${COTCODEC_OUTPUT_DIR}"
  fi
  if command -v python >/dev/null 2>&1; then
    python scripts/check_harness_env.py || failures=$((failures + 1))
  fi
  if [[ -n "${COTCODEC_EXPECTED_GPUS:-}" ]]; then
    check_gpu_visibility "${COTCODEC_EXPECTED_GPUS}"
  fi
fi

if [[ "${failures}" -gt 0 ]]; then
  echo "STATUS FAIL mode=${mode} failures=${failures}"
  exit 1
fi

echo "STATUS PASS mode=${mode}"
