#!/usr/bin/env bash
#SBATCH --job-name=am3-selftest-cpu
#SBATCH --partition=research
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=48G
#SBATCH --time=00:20:00
#SBATCH --no-requeue
# AM3 (EXPLORATORY): CPU-only (no GRES) check of scripts/memcredit_am3.py in a cotcodec-vllm cu129
# overlay (vLLM 0.31.0). With AM3_SRC set, the committed source tree (the clean clone) is mounted
# read-only at /src (pre-image check, in an existing overlay); without it the image's baked copy
# runs (post-build check). Renders every request with each reader's tokenizer and chat template
# (Qwen3-8B, OLMo-2-1124-7B-Instruct, Qwen3.5-9B) and the judge items with both judges'; checks
# lengths, the thinking-off marker, stop tokens, and that vLLM 0.31.0 resolves each architecture.
# The development study artifact is mounted read-only. No GPU, no network.
set -Eeuo pipefail
: "${AM3_OUT:?}"; : "${AM3_IMAGE:?}"; : "${AM3_ARTIFACT:?}"; : "${AM3_ARTIFACT_SHA256:?}"
[[ -z "${CUDA_VISIBLE_DEVICES:-}" && -z "${SLURM_JOB_GPUS:-}" ]] || { echo "GPU allocated" >&2; exit 2; }
[[ "$(docker info --format "{{.DefaultRuntime}}")" == runc ]] || { echo "runtime not runc" >&2; exit 2; }
mkdir -p "${AM3_OUT}"
src=(--workdir /workspace/cotcodec)
if [[ -n "${AM3_SRC:-}" ]]; then src=(--volume "${AM3_SRC}:/src:ro" --workdir /src); fi
common=(--rm --network none --read-only --tmpfs /tmp:rw,nosuid,nodev,size=8g --cap-drop ALL
  --security-opt no-new-privileges --user "$(id -u):$(id -g)" --env HOME=/tmp/home
  --env NVIDIA_VISIBLE_DEVICES=void --env CUDA_VISIBLE_DEVICES= --env HF_HUB_OFFLINE=1
  --env TRANSFORMERS_OFFLINE=1 --env USER=cotcodec --env LOGNAME=cotcodec
  --env TORCHINDUCTOR_CACHE_DIR=/tmp/inductor --env TRITON_CACHE_DIR=/tmp/triton
  --env OMP_NUM_THREADS=16 --cpus 16
  --label "cotcodec.slurm_job=${SLURM_JOB_ID}" "${src[@]}")
nodes="$(docker run "${common[@]}" --entrypoint /bin/sh "${AM3_IMAGE}" -c "ls -1 /dev/nvidia* 2>/dev/null || true")"
[[ -z "${nodes}" ]] || { echo "container sees ${nodes}" >&2; exit 2; }
echo "image ${AM3_IMAGE} src ${AM3_SRC:-baked}" > "${AM3_OUT}/exits.txt"
set +e
docker run "${common[@]}" --volume /home/kevin/cotcodec-runs/hf-cache:/model-cache:ro \
  --volume "${AM3_ARTIFACT}:/inputs/study-artifact.json:ro" \
  "${AM3_IMAGE}" python scripts/memcredit_am3.py selftest \
  --evidence /inputs/study-artifact.json --expected-evidence-sha256 "${AM3_ARTIFACT_SHA256}" \
  > "${AM3_OUT}/am3-selftest.json" 2> "${AM3_OUT}/am3-selftest.stderr"
echo "am3 selftest exit $?" | tee -a "${AM3_OUT}/exits.txt"
docker run "${common[@]}" --volume "${AM3_ARTIFACT}:/inputs/study-artifact.json:ro" \
  "${AM3_IMAGE}" python scripts/memcredit_am3.py plan --evidence /inputs/study-artifact.json \
  > "${AM3_OUT}/am3-plan.json" 2> "${AM3_OUT}/am3-plan.stderr"
echo "am3 plan exit $?" | tee -a "${AM3_OUT}/exits.txt"
