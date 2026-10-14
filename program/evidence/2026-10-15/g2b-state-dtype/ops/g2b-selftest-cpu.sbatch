#!/usr/bin/env bash
#SBATCH --job-name=g2b-selftest-cpu
#SBATCH --partition=research
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=00:15:00
#SBATCH --no-requeue
# CPU-only (no GRES) check of the g2b-state-dtype-v1 scripts in the two images. With G2B_SRC set
# (a clean checkout) it is mounted read-only over the source (pre-image check in the G2 pilot's
# images); without it, the images' own baked source runs (post-build check). vLLM image:
# prompt rendering with each model tokenizer, EngineArgs and SamplingParams construction, the
# parsers. Research image: tiny random Qwen3.5 on CPU (packed vs unpacked, leak checks).
# No GPU, no network, no model weights read (tokenizer and config files only).
set -Eeuo pipefail
: "${G2B_OUT:?}"; : "${G2B_VLLM_IMAGE:?}"; : "${G2B_RESEARCH_IMAGE:?}"
[[ -z "${CUDA_VISIBLE_DEVICES:-}" && -z "${SLURM_JOB_GPUS:-}" ]] || { echo "GPU allocated" >&2; exit 2; }
[[ "$(docker info --format "{{.DefaultRuntime}}")" == runc ]] || { echo "runtime not runc" >&2; exit 2; }
mkdir -p "${G2B_OUT}"
src=(--workdir /workspace/cotcodec)
if [[ -n "${G2B_SRC:-}" ]]; then src=(--volume "${G2B_SRC}:/src:ro" --workdir /src); fi
common=(--rm --network none --read-only --tmpfs /tmp:rw,nosuid,nodev,size=4g --cap-drop ALL
  --security-opt no-new-privileges --user "$(id -u):$(id -g)" --env HOME=/tmp/home
  --env NVIDIA_VISIBLE_DEVICES=void --env CUDA_VISIBLE_DEVICES= --env HF_HUB_OFFLINE=1
  --env TRANSFORMERS_OFFLINE=1 --env USER=cotcodec --env LOGNAME=cotcodec
  --env TORCHINDUCTOR_CACHE_DIR=/tmp/inductor --env TRITON_CACHE_DIR=/tmp/triton
  --label "cotcodec.slurm_job=${SLURM_JOB_ID}" "${src[@]}")
for image in "${G2B_VLLM_IMAGE}" "${G2B_RESEARCH_IMAGE}"; do
  nodes="$(docker run "${common[@]}" --entrypoint /bin/sh "${image}" -c "ls -1 /dev/nvidia* 2>/dev/null || true")"
  [[ -z "${nodes}" ]] || { echo "container sees ${nodes}" >&2; exit 2; }
done
set +e
docker run "${common[@]}" --volume /home/kevin/cotcodec-runs/hf-cache:/model-cache:ro \
  "${G2B_VLLM_IMAGE}" python scripts/run_g2b_rollouts.py selftest \
  > "${G2B_OUT}/rollouts-selftest.json" 2> "${G2B_OUT}/rollouts-selftest.stderr"
echo "rollouts selftest exit $?" | tee -a "${G2B_OUT}/exits.txt"
docker run "${common[@]}" --env OMP_NUM_THREADS=8 "${G2B_RESEARCH_IMAGE}" \
  python scripts/run_g2b_teacher_force.py selftest \
  > "${G2B_OUT}/teacher-force-selftest.json" 2> "${G2B_OUT}/teacher-force-selftest.stderr"
echo "teacher-force selftest exit $?" | tee -a "${G2B_OUT}/exits.txt"
docker run "${common[@]}" "${G2B_VLLM_IMAGE}" python scripts/run_g2b_rollouts.py plan \
  > "${G2B_OUT}/rollouts-plan.json" 2> "${G2B_OUT}/rollouts-plan.stderr"
echo "rollouts plan exit $?" | tee -a "${G2B_OUT}/exits.txt"
