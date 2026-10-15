#!/usr/bin/env bash
#SBATCH --job-name=am1c-selftest-cpu
#SBATCH --partition=research
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=48G
#SBATCH --time=00:20:00
#SBATCH --no-requeue
# am1-memory-credit-v1 (CONFIRMATORY): the post-build CPU selftest of registration section 16,
# CPU only (no GRES), on the cotcodec-vllm cu129 overlay built from the freeze commit's source
# capsule (the image's baked copy of the code runs), with the held-out study artifact mounted
# read-only: scripts/memcredit_study.py selftest and plan under the registration's config.
# The selftest renders every reader request (Qwen3-8B chat template) and the judge items
# (Qwen3-32B and Qwen3-8B templates), checks every memory span, runs the attention-signal code on
# CPU with Qwen3-0.6B-Base, and hashes the cited vLLM files. No GPU, no network. (The pilot's
# in-image pytest step is dropped: the image has no pytest; the tests run on the host clone.)
set -Eeuo pipefail
: "${AM1_OUT:?}"; : "${AM1_IMAGE:?}"; : "${AM1_ARTIFACT:?}"; : "${AM1_ARTIFACT_SHA256:?}"
CONFIG=experiments/am1/am1-memory-credit-v1.yaml
[[ -z "${CUDA_VISIBLE_DEVICES:-}" && -z "${SLURM_JOB_GPUS:-}" ]] || { echo "GPU allocated" >&2; exit 2; }
[[ "$(docker info --format "{{.DefaultRuntime}}")" == runc ]] || { echo "runtime not runc" >&2; exit 2; }
mkdir -p "${AM1_OUT}"
common=(--rm --network none --read-only --tmpfs /tmp:rw,nosuid,nodev,size=8g --cap-drop ALL
  --security-opt no-new-privileges --user "$(id -u):$(id -g)" --env HOME=/tmp/home
  --env NVIDIA_VISIBLE_DEVICES=void --env CUDA_VISIBLE_DEVICES= --env HF_HUB_OFFLINE=1
  --env TRANSFORMERS_OFFLINE=1 --env USER=cotcodec --env LOGNAME=cotcodec
  --env TORCHINDUCTOR_CACHE_DIR=/tmp/inductor --env TRITON_CACHE_DIR=/tmp/triton
  --env OMP_NUM_THREADS=16 --cpus 16
  --label "cotcodec.slurm_job=${SLURM_JOB_ID}" --workdir /workspace/cotcodec)
nodes="$(docker run "${common[@]}" --entrypoint /bin/sh "${AM1_IMAGE}" -c "ls -1 /dev/nvidia* 2>/dev/null || true")"
[[ -z "${nodes}" ]] || { echo "container sees ${nodes}" >&2; exit 2; }
echo "image ${AM1_IMAGE} src baked config ${CONFIG}" > "${AM1_OUT}/exits.txt"
set +e
docker run "${common[@]}" --volume /home/kevin/cotcodec-runs/hf-cache:/model-cache:ro \
  --volume "${AM1_ARTIFACT}:/inputs/study-artifact.json:ro" \
  "${AM1_IMAGE}" python scripts/memcredit_study.py selftest --config "${CONFIG}" \
  --evidence /inputs/study-artifact.json --expected-evidence-sha256 "${AM1_ARTIFACT_SHA256}" \
  > "${AM1_OUT}/study-selftest.json" 2> "${AM1_OUT}/study-selftest.stderr"
echo "study selftest exit $?" | tee -a "${AM1_OUT}/exits.txt"
docker run "${common[@]}" --volume "${AM1_ARTIFACT}:/inputs/study-artifact.json:ro" \
  "${AM1_IMAGE}" python scripts/memcredit_study.py plan --config "${CONFIG}" \
  --evidence /inputs/study-artifact.json \
  > "${AM1_OUT}/study-plan.json" 2> "${AM1_OUT}/study-plan.stderr"
echo "study plan exit $?" | tee -a "${AM1_OUT}/exits.txt"
