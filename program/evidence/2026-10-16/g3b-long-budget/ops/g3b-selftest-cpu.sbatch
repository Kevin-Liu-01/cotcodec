#!/usr/bin/env bash
#SBATCH --job-name=g3b-selftest-cpu
#SBATCH --partition=research
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=00:15:00
#SBATCH --no-requeue
# CPU-only (no GRES) check of the g3b-long-budget-v1 driver in the vLLM overlay image (its own
# baked source): config, pinned questions, prompt rendering and lengths with the tokenizer,
# EngineArgs for every arm, SamplingParams, the fit check at G3's block pools, the metrics parser,
# truncated decoding; then each phase's plan. No GPU, no network, no model weights read. G3's
# ops/g3-selftest-cpu.sbatch, adapted.
set -Eeuo pipefail
: "${G3B_OUT:?}"; : "${G3B_VLLM_IMAGE:?}"
[[ -z "${CUDA_VISIBLE_DEVICES:-}" && -z "${SLURM_JOB_GPUS:-}" ]] || { echo "GPU allocated" >&2; exit 2; }
[[ "$(docker info --format "{{.DefaultRuntime}}")" == runc ]] || { echo "runtime not runc" >&2; exit 2; }
mkdir -p "${G3B_OUT}"
common=(--rm --network none --read-only --tmpfs /tmp:rw,nosuid,nodev,size=4g --cap-drop ALL
  --security-opt no-new-privileges --user "$(id -u):$(id -g)" --env HOME=/tmp/home
  --env NVIDIA_VISIBLE_DEVICES=void --env CUDA_VISIBLE_DEVICES= --env HF_HUB_OFFLINE=1
  --env TRANSFORMERS_OFFLINE=1 --env USER=cotcodec --env LOGNAME=cotcodec --env OMP_NUM_THREADS=8
  --env TORCHINDUCTOR_CACHE_DIR=/tmp/inductor --env TRITON_CACHE_DIR=/tmp/triton
  --label "cotcodec.slurm_job=${SLURM_JOB_ID}" --workdir /workspace/cotcodec)
nodes="$(docker run "${common[@]}" --entrypoint /bin/sh "${G3B_VLLM_IMAGE}" -c "ls -1 /dev/nvidia* 2>/dev/null || true")"
[[ -z "${nodes}" ]] || { echo "container sees ${nodes}" >&2; exit 2; }
set +e
docker run "${common[@]}" --volume /home/kevin/cotcodec-runs/hf-cache:/model-cache:ro \
  "${G3B_VLLM_IMAGE}" python scripts/run_g3b_long_budget.py selftest \
  > "${G3B_OUT}/selftest.json" 2> "${G3B_OUT}/selftest.stderr"
echo "selftest exit $?" | tee -a "${G3B_OUT}/exits.txt"
for phase in ${G3B_PHASES:-pilot}; do
  docker run "${common[@]}" "${G3B_VLLM_IMAGE}" python scripts/run_g3b_long_budget.py plan --phase "$phase" \
    > "${G3B_OUT}/plan-$phase.json" 2> "${G3B_OUT}/plan-$phase.stderr"
  echo "plan $phase exit $?" | tee -a "${G3B_OUT}/exits.txt"
done
