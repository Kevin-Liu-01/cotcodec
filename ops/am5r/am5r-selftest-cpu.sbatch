#!/usr/bin/env bash
#SBATCH --job-name=am5r-selftest-cpu
#SBATCH --partition=research
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=48G
#SBATCH --time=00:20:00
#SBATCH --no-requeue
# am5-ablated-cost-v1: CPU-only (no GRES) check of scripts/memcredit_am5r.py baked in a
# cotcodec-vllm cu129 overlay (vLLM 0.31.0). Renders every request of one population with each
# reader's tokenizer and chat template (Qwen3-8B, OLMo-2-1124-7B-Instruct, Qwen3.5-9B) and the
# judge items with the Qwen3-32B judge's (LongMemEval's answer-check prompt); checks lengths, the
# thinking-off marker, stop tokens, and that vLLM 0.31.0 resolves each architecture. The
# population's study artifact is mounted read-only. No GPU, no network, no model output: the
# held-out population's selftest may run before the freeze.
set -Eeuo pipefail
: "${AM5R_OUT:?}"; : "${AM5R_IMAGE:?}"; : "${AM5R_POP:?}"; : "${AM5R_ARTIFACT:?}"; : "${AM5R_ARTIFACT_SHA256:?}"
[[ -z "${CUDA_VISIBLE_DEVICES:-}" && -z "${SLURM_JOB_GPUS:-}" ]] || { echo "GPU allocated" >&2; exit 2; }
[[ "$(docker info --format "{{.DefaultRuntime}}")" == runc ]] || { echo "runtime not runc" >&2; exit 2; }
mkdir -p "${AM5R_OUT}"
common=(--rm --network none --read-only --tmpfs /tmp:rw,nosuid,nodev,size=8g --cap-drop ALL
  --security-opt no-new-privileges --user "$(id -u):$(id -g)" --env HOME=/tmp/home
  --env NVIDIA_VISIBLE_DEVICES=void --env CUDA_VISIBLE_DEVICES= --env HF_HUB_OFFLINE=1
  --env TRANSFORMERS_OFFLINE=1 --env USER=cotcodec --env LOGNAME=cotcodec
  --env TORCHINDUCTOR_CACHE_DIR=/tmp/inductor --env TRITON_CACHE_DIR=/tmp/triton
  --env OMP_NUM_THREADS=16 --cpus 16
  --label "cotcodec.slurm_job=${SLURM_JOB_ID}" --workdir /workspace/cotcodec)
nodes="$(docker run "${common[@]}" --entrypoint /bin/sh "${AM5R_IMAGE}" -c "ls -1 /dev/nvidia* 2>/dev/null || true")"
[[ -z "${nodes}" ]] || { echo "container sees ${nodes}" >&2; exit 2; }
echo "image ${AM5R_IMAGE} population ${AM5R_POP}" > "${AM5R_OUT}/exits.txt"
set +e
docker run "${common[@]}" --volume "$HOME/cotcodec-runs/hf-cache:/model-cache:ro" \
  --volume "${AM5R_ARTIFACT}:/inputs/study-artifact.json:ro" \
  "${AM5R_IMAGE}" python scripts/memcredit_am5r.py selftest --population "${AM5R_POP}" \
  --evidence /inputs/study-artifact.json --expected-evidence-sha256 "${AM5R_ARTIFACT_SHA256}" \
  > "${AM5R_OUT}/am5r-selftest.json" 2> "${AM5R_OUT}/am5r-selftest.stderr"
echo "am5r selftest exit $?" | tee -a "${AM5R_OUT}/exits.txt"
docker run "${common[@]}" --volume "${AM5R_ARTIFACT}:/inputs/study-artifact.json:ro" \
  "${AM5R_IMAGE}" python scripts/memcredit_am5r.py plan --population "${AM5R_POP}" \
  --evidence /inputs/study-artifact.json \
  > "${AM5R_OUT}/am5r-plan.json" 2> "${AM5R_OUT}/am5r-plan.stderr"
echo "am5r plan exit $?" | tee -a "${AM5R_OUT}/exits.txt"
