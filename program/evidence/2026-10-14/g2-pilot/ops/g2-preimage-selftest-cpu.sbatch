#!/usr/bin/env bash
#SBATCH --job-name=g2-selftest-cpu
#SBATCH --partition=research
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=00:15:00
#SBATCH --no-requeue
# CPU-only (no GRES) pre-image check of the G2 pilot scripts: the committed source tree
# (G2_SRC, a clean clone) is mounted read-only into the two existing images. vLLM overlay:
# prompt rendering with each model tokenizer and the output parsers. Research image: tiny random
# Qwen3.5/Qwen3 models on CPU (GDN swap, chunked LM-head scorer, torch chunk vs recurrent).
# No GPU, no network, no model weights read (tokenizer and config files only).
set -Eeuo pipefail
: "${G2_SRC:?}"; : "${G2_OUT:?}"; : "${G2_VLLM_IMAGE:?}"; : "${G2_RESEARCH_IMAGE:?}"
[[ -z "${CUDA_VISIBLE_DEVICES:-}" && -z "${SLURM_JOB_GPUS:-}" ]] || { echo "GPU allocated" >&2; exit 2; }
[[ "$(docker info --format "{{.DefaultRuntime}}")" == runc ]] || { echo "runtime not runc" >&2; exit 2; }
mkdir -p "${G2_OUT}"
common=(--rm --network none --read-only --tmpfs /tmp:rw,nosuid,nodev,size=4g --cap-drop ALL
  --security-opt no-new-privileges --user "$(id -u):$(id -g)" --env HOME=/tmp/home
  --env NVIDIA_VISIBLE_DEVICES=void --env CUDA_VISIBLE_DEVICES= --env HF_HUB_OFFLINE=1
  --env TRANSFORMERS_OFFLINE=1 --env USER=cotcodec --env LOGNAME=cotcodec --env TORCHINDUCTOR_CACHE_DIR=/tmp/inductor --env TRITON_CACHE_DIR=/tmp/triton --label "cotcodec.slurm_job=${SLURM_JOB_ID}"
  --volume "${G2_SRC}:/src:ro" --workdir /src)
for image in "${G2_VLLM_IMAGE}" "${G2_RESEARCH_IMAGE}"; do
  nodes="$(docker run "${common[@]}" --entrypoint /bin/sh "${image}" -c "ls -1 /dev/nvidia* 2>/dev/null || true")"
  [[ -z "${nodes}" ]] || { echo "container sees ${nodes}" >&2; exit 2; }
done
set +e
docker run "${common[@]}" --volume /home/kevin/cotcodec-runs/hf-cache:/model-cache:ro \
  "${G2_VLLM_IMAGE}" python scripts/run_g2_rollouts.py selftest \
  > "${G2_OUT}/rollouts-selftest.json" 2> "${G2_OUT}/rollouts-selftest.stderr"
echo "rollouts selftest exit $?" | tee -a "${G2_OUT}/exits.txt"
docker run "${common[@]}" --env OMP_NUM_THREADS=8 "${G2_RESEARCH_IMAGE}" \
  python scripts/run_g2_teacher_force.py selftest \
  > "${G2_OUT}/teacher-force-selftest.json" 2> "${G2_OUT}/teacher-force-selftest.stderr"
echo "teacher-force selftest exit $?" | tee -a "${G2_OUT}/exits.txt"
