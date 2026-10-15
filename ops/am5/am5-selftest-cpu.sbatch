#!/usr/bin/env bash
#SBATCH --job-name=am5-selftest-cpu
#SBATCH --partition=research
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=48G
#SBATCH --time=00:15:00
#SBATCH --no-requeue
# AM5: CPU-only (no GRES) check of scripts/memcredit_am5.py baked in a cotcodec-vllm cu129 overlay.
# Renders every request of the ablated population with each reader's tokenizer and chat template
# and the judge items with the judge's; checks lengths, the thinking-off marker, stop tokens and
# that vLLM resolves each architecture. The artifact is mounted read-only. No GPU, no network, no
# model output.
set -Eeuo pipefail
: "${AM5_OUT:?}"; : "${AM5_IMAGE:?}"; : "${AM5_ARTIFACT:?}"; : "${AM5_ARTIFACT_SHA256:?}"
[[ -z "${CUDA_VISIBLE_DEVICES:-}" && -z "${SLURM_JOB_GPUS:-}" ]] || { echo "GPU allocated" >&2; exit 2; }
[[ "$(docker info --format "{{.DefaultRuntime}}")" == runc ]] || { echo "runtime not runc" >&2; exit 2; }
mkdir -p "${AM5_OUT}"
common=(--rm --network none --read-only --tmpfs /tmp:rw,nosuid,nodev,size=8g --cap-drop ALL
  --security-opt no-new-privileges --user "$(id -u):$(id -g)" --env HOME=/tmp/home
  --env NVIDIA_VISIBLE_DEVICES=void --env CUDA_VISIBLE_DEVICES= --env HF_HUB_OFFLINE=1
  --env TRANSFORMERS_OFFLINE=1 --env USER=cotcodec --env LOGNAME=cotcodec
  --env TORCHINDUCTOR_CACHE_DIR=/tmp/inductor --env TRITON_CACHE_DIR=/tmp/triton
  --env OMP_NUM_THREADS=16 --cpus 16
  --label "cotcodec.slurm_job=${SLURM_JOB_ID}" --workdir /workspace/cotcodec)
nodes="$(docker run "${common[@]}" --entrypoint /bin/sh "${AM5_IMAGE}" -c "ls -1 /dev/nvidia* 2>/dev/null || true")"
[[ -z "${nodes}" ]] || { echo "container sees ${nodes}" >&2; exit 2; }
echo "image ${AM5_IMAGE}" > "${AM5_OUT}/exits.txt"
set +e
docker run "${common[@]}" --volume "$HOME/cotcodec-runs/hf-cache:/model-cache:ro" \
  --volume "${AM5_ARTIFACT}:/inputs/study-artifact.json:ro" \
  "${AM5_IMAGE}" python scripts/memcredit_am5.py selftest \
  --evidence /inputs/study-artifact.json --expected-evidence-sha256 "${AM5_ARTIFACT_SHA256}" \
  > "${AM5_OUT}/am5-selftest.json" 2> "${AM5_OUT}/am5-selftest.stderr"
echo "am5 selftest exit $?" | tee -a "${AM5_OUT}/exits.txt"
docker run "${common[@]}" --volume "${AM5_ARTIFACT}:/inputs/study-artifact.json:ro" \
  "${AM5_IMAGE}" python scripts/memcredit_am5.py plan --evidence /inputs/study-artifact.json \
  > "${AM5_OUT}/am5-plan.json" 2> "${AM5_OUT}/am5-plan.stderr"
echo "am5 plan exit $?" | tee -a "${AM5_OUT}/exits.txt"
