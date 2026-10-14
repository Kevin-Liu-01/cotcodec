#!/usr/bin/env bash
#SBATCH --job-name=am1-selftest-cpu
#SBATCH --partition=research
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=00:15:00
#SBATCH --no-requeue
# AM1 Step 0 (EXPLORATORY): CPU-only (no GRES) check of scripts/memcredit_step0.py in a
# cotcodec-vllm cu129 overlay (vLLM 0.31.0). With AM1_SRC set, the committed source tree (a clean
# clone) is mounted read-only at /src (pre-image check); without it the image's baked copy runs
# (post-build check). Renders all 4,096 requests with the Qwen3-8B chat template (tokenizer files
# only), checks the parsers and the analysis on a synthetic run, and hashes the vLLM source files
# the README cites. The study artifact is mounted read-only. No GPU, no network, no weights read.
set -Eeuo pipefail
: "${AM1_OUT:?}"; : "${AM1_IMAGE:?}"; : "${AM1_ARTIFACT:?}"; : "${AM1_ARTIFACT_SHA256:?}"
[[ -z "${CUDA_VISIBLE_DEVICES:-}" && -z "${SLURM_JOB_GPUS:-}" ]] || { echo "GPU allocated" >&2; exit 2; }
[[ "$(docker info --format "{{.DefaultRuntime}}")" == runc ]] || { echo "runtime not runc" >&2; exit 2; }
mkdir -p "${AM1_OUT}"
src=(--workdir /workspace/cotcodec)
if [[ -n "${AM1_SRC:-}" ]]; then src=(--volume "${AM1_SRC}:/src:ro" --workdir /src); fi
common=(--rm --network none --read-only --tmpfs /tmp:rw,nosuid,nodev,size=4g --cap-drop ALL
  --security-opt no-new-privileges --user "$(id -u):$(id -g)" --env HOME=/tmp/home
  --env NVIDIA_VISIBLE_DEVICES=void --env CUDA_VISIBLE_DEVICES= --env HF_HUB_OFFLINE=1
  --env TRANSFORMERS_OFFLINE=1 --env USER=cotcodec --env LOGNAME=cotcodec
  --env TORCHINDUCTOR_CACHE_DIR=/tmp/inductor --env TRITON_CACHE_DIR=/tmp/triton
  --label "cotcodec.slurm_job=${SLURM_JOB_ID}" "${src[@]}")
nodes="$(docker run "${common[@]}" --entrypoint /bin/sh "${AM1_IMAGE}" -c "ls -1 /dev/nvidia* 2>/dev/null || true")"
[[ -z "${nodes}" ]] || { echo "container sees ${nodes}" >&2; exit 2; }
echo "image ${AM1_IMAGE} src ${AM1_SRC:-baked}" > "${AM1_OUT}/exits.txt"
set +e
docker run "${common[@]}" --volume /home/kevin/cotcodec-runs/hf-cache:/model-cache:ro \
  --volume "${AM1_ARTIFACT}:/inputs/study-artifact.json:ro" \
  "${AM1_IMAGE}" python scripts/memcredit_step0.py selftest \
  --evidence /inputs/study-artifact.json --expected-evidence-sha256 "${AM1_ARTIFACT_SHA256}" \
  > "${AM1_OUT}/step0-selftest.json" 2> "${AM1_OUT}/step0-selftest.stderr"
echo "step0 selftest exit $?" | tee -a "${AM1_OUT}/exits.txt"
docker run "${common[@]}" --volume "${AM1_ARTIFACT}:/inputs/study-artifact.json:ro" \
  "${AM1_IMAGE}" python scripts/memcredit_step0.py plan --evidence /inputs/study-artifact.json \
  > "${AM1_OUT}/step0-plan.json" 2> "${AM1_OUT}/step0-plan.stderr"
echo "step0 plan exit $?" | tee -a "${AM1_OUT}/exits.txt"
