#!/usr/bin/env bash
#SBATCH --job-name=g3-selftest-cpu
#SBATCH --partition=research
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --time=00:20:00
#SBATCH --no-requeue
# CPU-only (no GRES) check of the g3-state-precision-accuracy-v1 driver in the vLLM overlay image
# (its own baked source): config, plans, math and long-context prompt rendering and lengths with
# each model's tokenizer (every long-context question in the selection order), EngineArgs for
# every arm and task, SamplingParams, the judge prompt with the judge's tokenizer, the parsers.
# No GPU, no network, no model weights read (tokenizer and config files only).
set -Eeuo pipefail
: "${G3_OUT:?}"; : "${G3_VLLM_IMAGE:?}"
[[ -z "${CUDA_VISIBLE_DEVICES:-}" && -z "${SLURM_JOB_GPUS:-}" ]] || { echo "GPU allocated" >&2; exit 2; }
[[ "$(docker info --format "{{.DefaultRuntime}}")" == runc ]] || { echo "runtime not runc" >&2; exit 2; }
LME=/home/kevin/cotcodec-runs/inputs/longmemeval/98d7416c24c778c2fee6e6f3006e7a073259d48f/longmemeval_s_cleaned.json
mkdir -p "${G3_OUT}"
common=(--rm --network none --read-only --tmpfs /tmp:rw,nosuid,nodev,size=4g --cap-drop ALL
  --security-opt no-new-privileges --user "$(id -u):$(id -g)" --env HOME=/tmp/home
  --env NVIDIA_VISIBLE_DEVICES=void --env CUDA_VISIBLE_DEVICES= --env HF_HUB_OFFLINE=1
  --env TRANSFORMERS_OFFLINE=1 --env USER=cotcodec --env LOGNAME=cotcodec --env OMP_NUM_THREADS=8
  --env TORCHINDUCTOR_CACHE_DIR=/tmp/inductor --env TRITON_CACHE_DIR=/tmp/triton
  --label "cotcodec.slurm_job=${SLURM_JOB_ID}" --workdir /workspace/cotcodec)
nodes="$(docker run "${common[@]}" --entrypoint /bin/sh "${G3_VLLM_IMAGE}" -c "ls -1 /dev/nvidia* 2>/dev/null || true")"
[[ -z "${nodes}" ]] || { echo "container sees ${nodes}" >&2; exit 2; }
set +e
docker run "${common[@]}" --volume /home/kevin/cotcodec-runs/hf-cache:/model-cache:ro \
  --volume "${LME}:/inputs/longmemeval_s_cleaned.json:ro" \
  "${G3_VLLM_IMAGE}" python scripts/run_g3_accuracy.py selftest \
  > "${G3_OUT}/selftest.json" 2> "${G3_OUT}/selftest.stderr"
echo "selftest exit $?" | tee -a "${G3_OUT}/exits.txt"
for phase in ${G3_PHASES:-pilot}; do
  docker run "${common[@]}" "${G3_VLLM_IMAGE}" python scripts/run_g3_accuracy.py plan --phase "$phase" \
    > "${G3_OUT}/plan-$phase.json" 2> "${G3_OUT}/plan-$phase.stderr"
  echo "plan $phase exit $?" | tee -a "${G3_OUT}/exits.txt"
done
