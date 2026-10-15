#!/usr/bin/env bash
#SBATCH --job-name=am3g-selftest-cpu
#SBATCH --partition=research
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=48G
#SBATCH --time=00:20:00
#SBATCH --no-requeue
# am3-nonabstain-generality-v1: CPU-only (no GRES) check of scripts/memcredit_am3g.py baked in a
# cotcodec-vllm cu129 overlay (vLLM 0.31.0). Renders every request of one population with each
# reader's tokenizer and chat template (Qwen3-8B, OLMo-2-1124-7B-Instruct, Qwen3.5-9B) and the
# judge items with both judges' (the abstention template for _abs questions); checks lengths,
# the thinking-off marker, stop tokens, and that vLLM 0.31.0 resolves each architecture. The
# population's study artifact is mounted read-only. No GPU, no network, no model output.
set -Eeuo pipefail
: "${AM3G_OUT:?}"; : "${AM3G_IMAGE:?}"; : "${AM3G_POP:?}"; : "${AM3G_ARTIFACT:?}"; : "${AM3G_ARTIFACT_SHA256:?}"
[[ -z "${CUDA_VISIBLE_DEVICES:-}" && -z "${SLURM_JOB_GPUS:-}" ]] || { echo "GPU allocated" >&2; exit 2; }
[[ "$(docker info --format "{{.DefaultRuntime}}")" == runc ]] || { echo "runtime not runc" >&2; exit 2; }
mkdir -p "${AM3G_OUT}"
common=(--rm --network none --read-only --tmpfs /tmp:rw,nosuid,nodev,size=8g --cap-drop ALL
  --security-opt no-new-privileges --user "$(id -u):$(id -g)" --env HOME=/tmp/home
  --env NVIDIA_VISIBLE_DEVICES=void --env CUDA_VISIBLE_DEVICES= --env HF_HUB_OFFLINE=1
  --env TRANSFORMERS_OFFLINE=1 --env USER=cotcodec --env LOGNAME=cotcodec
  --env TORCHINDUCTOR_CACHE_DIR=/tmp/inductor --env TRITON_CACHE_DIR=/tmp/triton
  --env OMP_NUM_THREADS=16 --cpus 16
  --label "cotcodec.slurm_job=${SLURM_JOB_ID}" --workdir /workspace/cotcodec)
nodes="$(docker run "${common[@]}" --entrypoint /bin/sh "${AM3G_IMAGE}" -c "ls -1 /dev/nvidia* 2>/dev/null || true")"
[[ -z "${nodes}" ]] || { echo "container sees ${nodes}" >&2; exit 2; }
echo "image ${AM3G_IMAGE} population ${AM3G_POP}" > "${AM3G_OUT}/exits.txt"
set +e
docker run "${common[@]}" --volume "$HOME/cotcodec-runs/hf-cache:/model-cache:ro" \
  --volume "${AM3G_ARTIFACT}:/inputs/study-artifact.json:ro" \
  "${AM3G_IMAGE}" python scripts/memcredit_am3g.py selftest --population "${AM3G_POP}" \
  --evidence /inputs/study-artifact.json --expected-evidence-sha256 "${AM3G_ARTIFACT_SHA256}" \
  > "${AM3G_OUT}/am3g-selftest.json" 2> "${AM3G_OUT}/am3g-selftest.stderr"
echo "am3g selftest exit $?" | tee -a "${AM3G_OUT}/exits.txt"
docker run "${common[@]}" --volume "${AM3G_ARTIFACT}:/inputs/study-artifact.json:ro" \
  "${AM3G_IMAGE}" python scripts/memcredit_am3g.py plan --population "${AM3G_POP}" \
  --evidence /inputs/study-artifact.json \
  > "${AM3G_OUT}/am3g-plan.json" 2> "${AM3G_OUT}/am3g-plan.stderr"
echo "am3g plan exit $?" | tee -a "${AM3G_OUT}/exits.txt"
